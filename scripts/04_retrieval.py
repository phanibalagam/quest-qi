"""
04_retrieval.py -- retrieval baselines on QUEST-QI.

Corpus-trained systems run entirely inside the analysis host. The pretrained
encoders are the one exception: their weights are downloaded once by
scripts/09_dense_encode.py on a host that can reach huggingface.co, and this
script reads the resulting embeddings. If that file is absent every dense-encoder
system is skipped and the rest of the pipeline still runs.

Systems
  bm25              Okapi BM25 over the event text
  tfidf             TF-IDF cosine
  lsa               Truncated SVD over the TF-IDF matrix (corpus-trained)
  w2v               Mean word2vec embedding (corpus-trained)
  hybrid_rrf        Reciprocal rank fusion of bm25 + lsa
  bge / minilm      pretrained sentence encoders (from 09_dense_encode.py)
  hybrid_rrf_dense  Reciprocal rank fusion of bm25 + lsa + bge

hybrid_rrf, NOT hybrid_rrf_dense, stays the baseline that script 05 builds on,
because it is the strongest configuration that needs no downloaded weights and so
is the one a reader can reproduce offline. The dense fusion is reported alongside,
and script 05 re-runs the headline contrast on top of it to show the null is not an
artifact of a weak base.

Input :  data/processed/events_labeled.jsonl, data/processed/benchmark.jsonl
Output:  results/retrieval_results.json, results/retrieval_runs.json

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import json
import os
import re
import time

import numpy as np
from gensim.models import Word2Vec
from rank_bm25 import BM25Okapi
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS = os.path.join(ROOT, "data", "processed", "events_labeled.jsonl")
BENCH = os.path.join(ROOT, "data", "processed", "benchmark.jsonl")
RES = os.path.join(ROOT, "results", "retrieval_results.json")
RUNS = os.path.join(ROOT, "results", "retrieval_runs.json")
DENSE = os.path.join(ROOT, "data", "processed", "dense_embeddings.npz")
DENSE_MANIFEST = os.path.join(ROOT, "results", "dense_manifest.json")

SEED = 20260906
KS = (10, 50, 100)
TOPK = 100
SVD_DIM = 300
W2V_DIM = 200
RRF_K = 60
BOOTSTRAP = 2000

TOKEN = re.compile(r"[a-z0-9][a-z0-9\-/]*")


def tok(text):
    return TOKEN.findall(text.lower())


def dcg(rels):
    return sum(r / np.log2(i + 2) for i, r in enumerate(rels))


def ndcg_at_k(ranked, gold, k):
    rels = [1.0 if d in gold else 0.0 for d in ranked[:k]]
    ideal = [1.0] * min(len(gold), k)
    idcg = dcg(ideal)
    return dcg(rels) / idcg if idcg > 0 else 0.0


def evaluate(ranked, gold):
    gold = set(gold)
    out = {}
    for k in KS:
        hits = sum(1 for d in ranked[:k] if d in gold)
        out[f"recall@{k}"] = hits / len(gold)
    out["precision@10"] = sum(1 for d in ranked[:10] if d in gold) / 10
    out["ndcg@10"] = ndcg_at_k(ranked, gold, 10)
    rr = 0.0
    for i, d in enumerate(ranked):
        if d in gold:
            rr = 1.0 / (i + 1)
            break
    out["mrr"] = rr
    return out


def cluster_ids(queries):
    """One cluster per defect category; entity-family queries are their own
    cluster. Queries in a cluster share most of their gold events, so an i.i.d.
    bootstrap over queries would understate variance."""
    keys, index = {}, []
    for q in queries:
        k = q["predicate"].get("defect_category") or q["query_id"]
        index.append(keys.setdefault(k, len(keys)))
    return np.asarray(index), len(keys)


_RESAMPLE_CACHE = {}


def cluster_resamples(clusters, n_clusters, rng, n=BOOTSTRAP):
    """One fixed set of cluster resamples, reused for every statistic."""
    key = (id(clusters), n_clusters, n)
    if key not in _RESAMPLE_CACHE:
        members = [np.where(clusters == c)[0] for c in range(n_clusters)]
        _RESAMPLE_CACHE[key] = [
            np.concatenate([members[c] for c in rng.integers(0, n_clusters, size=n_clusters)])
            for _ in range(n)]
    return _RESAMPLE_CACHE[key]


def cluster_bootstrap(values, clusters, n_clusters, rng, n=BOOTSTRAP):
    v = np.asarray(values, dtype=float)
    return np.array([v[idx].mean() for idx in cluster_resamples(clusters, n_clusters, rng, n)])


def bootstrap_ci(values, rng, clusters=None, n_clusters=None, n=BOOTSTRAP):
    v = np.asarray(values, dtype=float)
    if clusters is None:
        means = v[rng.integers(0, len(v), size=(n, len(v)))].mean(axis=1)
    else:
        means = cluster_bootstrap(v, clusters, n_clusters, rng, n)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def holm(pvals):
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m, adj, running = len(pvals), [0.0] * len(pvals), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = round(running, 4)
    return adj


def rrf_fuse(rank_lists, k=RRF_K):
    scores = {}
    for lst in rank_lists:
        for rank, doc in enumerate(lst):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank + 1)
    return [d for d, _ in sorted(scores.items(), key=lambda x: (-x[1], x[0]))]


def load_dense(doc_ids, query_ids):
    """Read pretrained-encoder embeddings, or return {} if they were never made.

    The .npz is produced on a different host, so its alignment with the current
    corpus build is verified rather than assumed: a stale file is a silent
    correctness bug, not a missing feature.
    """
    if not os.path.exists(DENSE):
        print("dense_embeddings.npz not found -- skipping pretrained encoders.\n"
              "  run scripts/09_dense_encode.py on a host that can reach huggingface.co")
        return {}
    z = np.load(DENSE, allow_pickle=True)
    got_docs = [str(x) for x in z["doc_ids"]]
    got_queries = [str(x) for x in z["query_ids"]]
    if got_docs != list(doc_ids):
        raise SystemExit(f"{DENSE} is stale: it holds {len(got_docs)} document ids that "
                         f"do not match this corpus build ({len(doc_ids)} events). "
                         "Re-run scripts/09_dense_encode.py after 01/02.")
    if got_queries != list(query_ids):
        raise SystemExit(f"{DENSE} is stale: query ids do not match this benchmark "
                         "build. Re-run scripts/09_dense_encode.py after 03.")
    out = {}
    for name in z.files:
        if name.endswith("_docs"):
            key = name[:-len("_docs")]
            out[key] = (z[name], z[f"{key}_queries"])
    print(f"dense encoders loaded: {', '.join(sorted(out))}")
    return out


def main():
    rng = np.random.default_rng(SEED)
    events = [json.loads(l) for l in open(EVENTS, encoding="utf-8")]
    queries = [json.loads(l) for l in open(BENCH, encoding="utf-8")]
    ids = [e["event_id"] for e in events]
    corpus = [e["text"] for e in events]
    q_texts = [q["question"] for q in queries]

    timings = {}

    # --- BM25 -------------------------------------------------------------
    t0 = time.time()
    tokenised = [tok(c) for c in corpus]
    bm25 = BM25Okapi(tokenised)
    timings["bm25_index_s"] = round(time.time() - t0, 2)
    bm25_rank = []
    t0 = time.time()
    for qt in q_texts:
        s = bm25.get_scores(tok(qt))
        order = np.argsort(-s)[:TOPK]
        bm25_rank.append([ids[i] for i in order])
    timings["bm25_query_ms_per_query"] = round(1000 * (time.time() - t0) / len(q_texts), 1)

    # --- TF-IDF -----------------------------------------------------------
    t0 = time.time()
    vec = TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=2,
                          max_features=300000, strip_accents="unicode",
                          stop_words="english")
    X = vec.fit_transform(corpus)
    Xn = normalize(X)
    timings["tfidf_index_s"] = round(time.time() - t0, 2)
    Q = normalize(vec.transform(q_texts))
    t0 = time.time()
    sims = (Q @ Xn.T).toarray()
    tfidf_rank = [[ids[i] for i in np.argsort(-row)[:TOPK]] for row in sims]
    timings["tfidf_query_ms_per_query"] = round(1000 * (time.time() - t0) / len(q_texts), 1)

    # --- LSA --------------------------------------------------------------
    t0 = time.time()
    svd = TruncatedSVD(n_components=SVD_DIM, random_state=SEED)
    D = normalize(svd.fit_transform(X))
    timings["lsa_index_s"] = round(time.time() - t0, 2)
    timings["lsa_explained_variance"] = round(float(svd.explained_variance_ratio_.sum()), 4)
    Ql = normalize(svd.transform(vec.transform(q_texts)))
    t0 = time.time()
    sims = Ql @ D.T
    lsa_rank = [[ids[i] for i in np.argsort(-row)[:TOPK]] for row in sims]
    timings["lsa_query_ms_per_query"] = round(1000 * (time.time() - t0) / len(q_texts), 1)

    # --- word2vec ---------------------------------------------------------
    t0 = time.time()
    w2v = Word2Vec(sentences=tokenised, vector_size=W2V_DIM, window=8, min_count=3,
                   workers=1, sg=1, epochs=8, seed=SEED)  # workers=1 for determinism
    idf = dict(zip(vec.get_feature_names_out(), vec.idf_))

    def embed(tokens):
        vs, ws = [], []
        for t in tokens:
            if t in w2v.wv:
                vs.append(w2v.wv[t])
                ws.append(idf.get(t, 1.0))
        if not vs:
            return np.zeros(W2V_DIM, dtype=np.float32)
        return np.average(np.asarray(vs), axis=0, weights=ws)

    W = normalize(np.vstack([embed(t) for t in tokenised]))
    timings["w2v_index_s"] = round(time.time() - t0, 2)
    Qw = normalize(np.vstack([embed(tok(qt)) for qt in q_texts]))
    t0 = time.time()
    sims = Qw @ W.T
    w2v_rank = [[ids[i] for i in np.argsort(-row)[:TOPK]] for row in sims]
    timings["w2v_query_ms_per_query"] = round(1000 * (time.time() - t0) / len(q_texts), 1)

    # --- pretrained encoders ---------------------------------------------
    dense = load_dense(ids, [q["query_id"] for q in queries])
    dense_rank = {}
    for key, (D_docs, D_q) in dense.items():
        t0 = time.time()
        sims = D_q @ D_docs.T           # both sides are already L2-normalised
        dense_rank[key] = [[ids[i] for i in np.argsort(-row)[:TOPK]] for row in sims]
        timings[f"{key}_query_ms_per_query"] = round(
            1000 * (time.time() - t0) / len(q_texts), 1)

    # --- Hybrid -----------------------------------------------------------
    # hybrid_rrf is bm25+lsa and is the baseline script 05 builds on; it does
    # not change when a dense encoder is available.
    hybrid_rank = [rrf_fuse([b, l])[:TOPK] for b, l in zip(bm25_rank, lsa_rank)]

    systems = {
        "bm25": bm25_rank, "tfidf": tfidf_rank, "lsa": lsa_rank,
        "w2v": w2v_rank, "hybrid_rrf": hybrid_rank,
    }
    for key in sorted(dense_rank):
        systems[key] = dense_rank[key]
    # Fuse with the strongest available pretrained encoder (BGE if present).
    best_dense = next((k for k in ("bge_base", "bge", "e5_base", "minilm")
                       if k in dense_rank), None)
    if best_dense:
        systems["hybrid_rrf_dense"] = [
            rrf_fuse([b, l, d])[:TOPK]
            for b, l, d in zip(bm25_rank, lsa_rank, dense_rank[best_dense])]
        timings["dense_encoder_used_in_fusion"] = best_dense

    metrics = [f"recall@{k}" for k in KS] + ["precision@10", "ndcg@10", "mrr"]
    per_query_all = {s: [evaluate(r, q["gold_event_ids"]) for r, q in zip(rank, queries)]
                     for s, rank in systems.items()}
    # Headline numbers are reported on the held-out test split.
    test_mask = [q["split"] == "test" for q in queries]
    per_query = {s: [r for r, keep in zip(rows, test_mask) if keep]
                 for s, rows in per_query_all.items()}
    test_queries = [q for q in queries if q["split"] == "test"]

    clusters, n_clusters = cluster_ids(test_queries)
    fams_of = [q["family"] for q in test_queries]
    families_all = sorted(set(fams_of))

    def summarise(pq, clustered):
        out = {}
        for s, rows in pq.items():
            out[s] = {}
            for m in metrics:
                vals = [r[m] for r in rows]
                cell = {"mean": round(float(np.mean(vals)), 4)}
                if clustered:
                    lo, hi = bootstrap_ci(vals, rng, clusters, n_clusters)
                    cell["ci95_cluster"] = [round(lo, 4), round(hi, 4)]
                    lo2, hi2 = bootstrap_ci(vals, rng)
                    cell["ci95_iid"] = [round(lo2, 4), round(hi2, 4)]
                    cell["macro_over_families"] = round(float(np.mean(
                        [np.mean([v for v, f in zip(vals, fams_of) if f == fam])
                         for fam in families_all])), 4)
                out[s][m] = cell
        return out

    summary = summarise(per_query, True)
    summary_all_queries = summarise(per_query_all, False)

    families = families_all
    by_family = {}
    for s, rows in per_query.items():
        by_family[s] = {}
        for fam in families:
            sel = [r for r, q in zip(rows, test_queries) if q["family"] == fam]
            cell = {m: round(float(np.mean([r[m] for r in sel])), 4) for m in metrics}
            cell["n_queries"] = len(sel)
            lo, hi = bootstrap_ci([r["ndcg@10"] for r in sel], rng)
            cell["ndcg@10_ci95_iid"] = [round(lo, 4), round(hi, 4)]
            by_family[s][fam] = cell

    # Paired bootstrap: hybrid vs each other system, on nDCG@10.
    contrasts, raw_p = {}, []
    base_v = np.array([r["ndcg@10"] for r in per_query["hybrid_rrf"]])
    for s in systems:
        if s == "hybrid_rrf":
            continue
        diff = base_v - np.array([r["ndcg@10"] for r in per_query[s]])
        boot = cluster_bootstrap(diff, clusters, n_clusters, rng)
        p = float(min(1.0, 2 * min((boot <= 0).mean(), (boot >= 0).mean())))
        raw_p.append(p)
        contrasts[f"hybrid_rrf - {s}"] = {
            "mean_diff_ndcg@10": round(float(diff.mean()), 4),
            "ci95_cluster": [round(float(np.percentile(boot, 2.5)), 4),
                             round(float(np.percentile(boot, 97.5)), 4)],
            "p_two_sided_raw": round(p, 4),
        }
    for (k, v), adj in zip(contrasts.items(), holm(raw_p)):
        v["p_holm"] = adj
        v["p_note"] = (f"two-sided p is 2*min(tail); with {BOOTSTRAP} resamples the "
                       f"smallest attainable non-zero value is {2 / BOOTSTRAP}, so a "
                       f"reported 0.0 means p < {2 / BOOTSTRAP}")

    out = {
        "seed": SEED,
        "corpus_size": len(events),
        "n_queries_total": len(queries),
        "n_queries_test": len(test_queries),
        "n_bootstrap_clusters": n_clusters,
        "split": "headline metrics computed on the held-out test split",
        "top_k": TOPK,
        "config": {"svd_dim": SVD_DIM, "w2v_dim": W2V_DIM, "rrf_k": RRF_K,
                   "bootstrap_resamples": BOOTSTRAP},
        "timings": timings,
        "dense_encoders": (json.load(open(DENSE_MANIFEST, encoding="utf-8"))
                           if dense and os.path.exists(DENSE_MANIFEST) else None),
        "summary": summary,
        "summary_all_queries": summary_all_queries,
        "by_family": by_family,
        "contrasts_vs_hybrid": contrasts,
    }
    with open(RES, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    with open(RUNS, "w", encoding="utf-8") as fh:
        json.dump({s: {q["query_id"]: r[:TOPK] for q, r in zip(queries, rank)}
                   for s, rank in systems.items()}, fh)

    hdr = f"{'system':12s}" + "".join(f"{m:>14s}" for m in metrics)
    print(hdr)
    for s in systems:
        print(f"{s:12s}" + "".join(f"{summary[s][m]['mean']:14.4f}" for m in metrics))
    print("\ntimings:", json.dumps(timings))
    print("\ncontrasts (nDCG@10):")
    for k, v in contrasts.items():
        print(f"  {k:28s} {v['mean_diff_ndcg@10']:+.4f}  CI {v['ci95_cluster']}  "
              f"p_raw={v['p_two_sided_raw']} p_holm={v['p_holm']}")


if __name__ == "__main__":
    main()
