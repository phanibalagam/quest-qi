"""
05_taxonomy_aware_retrieval.py -- the proposed retriever, plus ablations.

Script 04 shows that surface-similarity retrieval answers entity questions
(which firm, which country) but fails on the defect-semantics questions that
dominate real quality investigations. The proposed retriever adds one channel:
a prior over the corpus defect taxonomy, inferred from the question, fused with
the text ranking.

Systems
  hybrid_rrf        text-only baseline carried over from script 04
  qir_clf           + defect prior from the taxonomy classifier applied
                    zero-shot to the question
  qir_centroid      + defect prior from LSA category centroids (no labelled
                    question data needed) -- the paper's residual result
  qir_oracle        + the true defect category
  qir_*_slots       the above + severity / period / country / dosage-form slot
                    filters read off the question

Controls (not systems -- they exist to size the circularity, see paper Sec 5.4)
  slots_only                 slot filters with no defect prior
  prefilter_hybrid           hard metadata prefilter then text ranking
  gold_downweight_control    multiplicative gold membership, matched to the
                             purely multiplicative soft filter. Capped by the
                             text channel: 0 x 0.5 = 0.
  gold_additive_control      additive gold membership over the same candidate
                             pool. Its score is essentially the pool's gold
                             recall, so it measures POOL as much as mechanism.
  gold_lookup_ceiling        the literal answer key.

Two facts this script computes and the paper reports as limitations: the priors
match against the same stored defect_category field the gold rule tests, so they
are noisy partial gold membership rather than predicate-free; and qir_oracle_slots
is per-family identical to gold_additive_control on every family whose predicate
is category x constraint.

Input :  data/processed/events_labeled.jsonl, data/processed/benchmark.jsonl
Output:  results/proposed_results.json

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import json
import os
import re

import numpy as np
from gensim.models import Word2Vec  # noqa: F401  (kept so the env matches 04)
from rank_bm25 import BM25Okapi
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import normalize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS = os.path.join(ROOT, "data", "processed", "events_labeled.jsonl")
BENCH = os.path.join(ROOT, "data", "processed", "benchmark.jsonl")
OUT = os.path.join(ROOT, "results", "proposed_results.json")
DENSE = os.path.join(ROOT, "data", "processed", "dense_embeddings.npz")

SEED = 20260906
KS = (10, 50, 100)
TOPK = 100
SVD_DIM = 300
RRF_K = 60
POOL = 300          # candidate pool, identical for every re-ranking system
BOOTSTRAP = 2000
LAMBDA = 1.0          # weight on the defect-prior channel (selected on dev)
LAMBDA_GRID = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
SLOT_PENALTY = 0.5    # multiplicative penalty for violating an extracted slot

TOKEN = re.compile(r"[a-z0-9][a-z0-9\-/]*")
DOSAGE_FORMS = {
    "sterile injectable": r"\b(injection|injectable|vial|ampule|ampoule|infusion|syringe|iv\b|intravenous)",
    "oral solid": r"\b(tablet|capsule|caplet|softgel)",
    "ophthalmic": r"\b(ophthalmic|eye drop|eye-drop|intraocular)",
    "topical": r"\b(cream|ointment|gel\b|lotion|topical|transdermal)",
    "oral liquid": r"\b(oral solution|oral suspension|syrup|elixir|oral liquid)",
}


def tok(t):
    return TOKEN.findall(t.lower())


def dcg(rels):
    return sum(r / np.log2(i + 2) for i, r in enumerate(rels))


def evaluate(ranked, gold):
    gold = set(gold)
    out = {}
    for k in KS:
        out[f"recall@{k}"] = sum(1 for d in ranked[:k] if d in gold) / len(gold)
    out["precision@10"] = sum(1 for d in ranked[:10] if d in gold) / 10
    rels = [1.0 if d in gold else 0.0 for d in ranked[:10]]
    idcg = dcg([1.0] * min(len(gold), 10))
    out["ndcg@10"] = dcg(rels) / idcg if idcg else 0.0
    out["mrr"] = next((1.0 / (i + 1) for i, d in enumerate(ranked) if d in gold), 0.0)
    return out


def rrf_scores(rank_lists, k=RRF_K):
    scores = {}
    for lst in rank_lists:
        for rank, doc in enumerate(lst):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank + 1)
    return scores


def cluster_ids(queries):
    """Queries built from the same defect category share most of their gold
    events, so an i.i.d. bootstrap over queries understates variance. Resample
    clusters instead: one cluster per defect category, and one per query for the
    entity families, which have near-disjoint gold sets."""
    keys, index = {}, []
    for q in queries:
        k = q["predicate"].get("defect_category") or q["query_id"]
        index.append(keys.setdefault(k, len(keys)))
    return np.asarray(index), len(keys)


_RESAMPLE_CACHE = {}


def cluster_resamples(clusters, n_clusters, rng, n=BOOTSTRAP):
    """One fixed set of cluster resamples, reused for every statistic, so that
    two estimates of the same quantity cannot differ by Monte-Carlo noise."""
    key = (id(clusters), n_clusters, n)
    if key not in _RESAMPLE_CACHE:
        members = [np.where(clusters == c)[0] for c in range(n_clusters)]
        _RESAMPLE_CACHE[key] = [
            np.concatenate([members[c] for c in rng.integers(0, n_clusters, size=n_clusters)])
            for _ in range(n)]
    return _RESAMPLE_CACHE[key]


def cluster_bootstrap(values, clusters, n_clusters, rng, n=BOOTSTRAP):
    """Return the resampled means of `values` under a cluster bootstrap."""
    v = np.asarray(values, float)
    return np.array([v[idx].mean() for idx in cluster_resamples(clusters, n_clusters, rng, n)])


def bootstrap_ci(values, rng, clusters=None, n_clusters=None, n=BOOTSTRAP):
    v = np.asarray(values, float)
    if clusters is None:
        m = v[rng.integers(0, len(v), size=(n, len(v)))].mean(axis=1)
    else:
        m = cluster_bootstrap(v, clusters, n_clusters, rng, n)
    return round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)


def holm(pvals):
    """Holm-Bonferroni adjusted p-values, order preserved."""
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m, adj, running = len(pvals), [0.0] * len(pvals), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = round(running, 4)
    return adj


def extract_slots(question):
    slots = {}
    m = re.search(r"\(Class (I{1,3})\)", question)
    if m:
        slots["classification"] = "Class " + m.group(1)
    m = re.search(r"[Bb]etween (\d{4}) and (\d{4})", question)
    if m:
        slots["year_from"], slots["year_to"] = m.group(1), m.group(2)
    m = re.search(r"site in ([A-Z][A-Za-z ]+?)\?", question)
    if m:
        slots["country"] = m.group(1).strip()
    if "outside the United States" in question:
        slots["country_not"] = "United States"
    for form, pat in DOSAGE_FORMS.items():
        if f"for {form} products" in question:
            slots["dosage_form"] = form
    return slots


def slot_ok(event, slots):
    if "classification" in slots and event["classification"] != slots["classification"]:
        return False
    if "year_from" in slots and not (slots["year_from"] <= (event["init_year"] or "0000") <= slots["year_to"]):
        return False
    if "country" in slots and event["country"] != slots["country"]:
        return False
    if "country_not" in slots and event["country"] == slots["country_not"]:
        return False
    if "dosage_form" in slots:
        blob = " ".join(event.get("products", []))[:4000].lower()
        if not re.search(DOSAGE_FORMS[slots["dosage_form"]], blob):
            return False
    return True


def load_dense(doc_ids, query_ids):
    """Pretrained-encoder embeddings from scripts/09_dense_encode.py, or None.

    Used only for the robustness check in Section 5.3: it re-runs the headline
    contrast on top of a stronger base, so the null cannot be dismissed as an
    artifact of weak corpus-trained retrieval. The main results deliberately keep
    the bm25+lsa base, which is the strongest configuration that needs no downloaded
    weights and so is the one a reader can reproduce offline.
    """
    if not os.path.exists(DENSE):
        return None
    z = np.load(DENSE, allow_pickle=True)
    if [str(x) for x in z["doc_ids"]] != list(doc_ids):
        raise SystemExit(f"{DENSE} is stale: document ids do not match this corpus "
                         "build. Re-run scripts/09_dense_encode.py after 01/02.")
    if [str(x) for x in z["query_ids"]] != list(query_ids):
        raise SystemExit(f"{DENSE} is stale: query ids do not match this benchmark "
                         "build. Re-run scripts/09_dense_encode.py after 03.")
    for key in ("bge_base", "bge", "e5_base", "minilm"):
        if f"{key}_docs" in z.files:
            return z[f"{key}_docs"], z[f"{key}_queries"]
    return None


def main():
    rng = np.random.default_rng(SEED)
    events = [json.loads(l) for l in open(EVENTS, encoding="utf-8")]
    queries = [json.loads(l) for l in open(BENCH, encoding="utf-8")]
    ids = [e["event_id"] for e in events]
    pos = {d: i for i, d in enumerate(ids)}
    corpus = [e["text"] for e in events]
    q_texts = [q["question"] for q in queries]
    cats = sorted({e["defect_category"] for e in events})
    cat_index = {c: i for i, c in enumerate(cats)}
    doc_cat = np.array([cat_index[e["defect_category"]] for e in events])

    # --- text channels ----------------------------------------------------
    tokenised = [tok(c) for c in corpus]
    bm25 = BM25Okapi(tokenised)
    bm25_rank = [[ids[i] for i in np.argsort(-bm25.get_scores(tok(q)))[:TOPK]] for q in q_texts]

    vec = TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=2,
                          max_features=300000, strip_accents="unicode",
                          stop_words="english")
    X = vec.fit_transform(corpus)
    svd = TruncatedSVD(n_components=SVD_DIM, random_state=SEED)
    D = normalize(svd.fit_transform(X))
    Ql = normalize(svd.transform(vec.transform(q_texts)))
    lsa_sims = Ql @ D.T
    lsa_rank = [[ids[i] for i in np.argsort(-row)[:TOPK]] for row in lsa_sims]

    # --- defect prior channels -------------------------------------------
    # (a) taxonomy classifier, trained on recall narratives, applied zero-shot
    #     to questions. Trained only on prefix-tier remainder text, as in 02.
    train = [(e["reason_remainder"], e["defect_category"]) for e in events
             if e["label_source"] == "prefix" and len(e.get("reason_remainder", "")) >= 15]
    keep = {c for c, n in
            zip(*np.unique([y for _, y in train], return_counts=True)) if n >= 25}
    Xt = [x for x, y in train if y in keep]
    yt = [y for _, y in train if y in keep]
    clf = make_pipeline(
        TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=2,
                        max_features=60000, strip_accents="unicode"),
        LogisticRegression(max_iter=3000, C=4.0, class_weight="balanced",
                           random_state=SEED))
    clf.fit(Xt, yt)
    proba = clf.predict_proba(q_texts)
    clf_prior = np.zeros((len(queries), len(cats)))
    for j, c in enumerate(clf.classes_):
        clf_prior[:, cat_index[c]] = proba[:, j]

    # (b) category centroids in LSA space (unsupervised at query time)
    cent = np.vstack([normalize(D[doc_cat == cat_index[c]].mean(axis=0, keepdims=True))[0]
                      for c in cats])
    cs = Ql @ cent.T
    cs = np.exp(cs * 8)
    centroid_prior = cs / cs.sum(axis=1, keepdims=True)

    # (c) oracle
    oracle_prior = np.zeros_like(clf_prior)
    for i, q in enumerate(queries):
        c = q["predicate"].get("defect_category")
        if c:
            oracle_prior[i, cat_index[c]] = 1.0

    # zero-shot query-classification accuracy, where the query has a category
    labelled = [(i, q["predicate"]["defect_category"]) for i, q in enumerate(queries)
                if "defect_category" in q["predicate"]]
    clf_top1 = np.mean([cats[int(clf_prior[i].argmax())] == c for i, c in labelled])
    cen_top1 = np.mean([cats[int(centroid_prior[i].argmax())] == c for i, c in labelled])

    def rank_prefilter():
        """Hard metadata prefilter, then the same text ranking. No defect prior.
        This is what a conventional SQL-filter-then-search system does."""
        ranked = []
        for i, q in enumerate(queries):
            slots = extract_slots(q["question"])
            keep = [d for d in ids if slot_ok(events[pos[d]], slots)] if slots else ids
            keepset = set(keep)
            base = rrf_scores([[d for d in bm25_rank[i] if d in keepset],
                               [d for d in lsa_rank[i] if d in keepset]])
            extra = [ids[j] for j in np.argsort(-lsa_sims[i])[:POOL] if ids[j] in keepset]
            order = [d for d, _ in sorted(base.items(), key=lambda x: (-x[1], x[0]))]
            order += [d for d in extra if d not in base]
            ranked.append(order[:TOPK])
        return ranked

    def rank_gold_downweight():
        """Control matched to the SOFT metadata filter: multiply the base score of
        every non-gold document by SLOT_PENALTY. Because a gold document the text
        channel never surfaced has base score 0, and 0 x 0.5 = 0, this control
        cannot promote anything the text channel missed -- it is therefore capped
        by the text retriever and is NOT an upper bound on the additive systems."""
        ranked = []
        for i, q in enumerate(queries):
            gold = set(q["gold_event_ids"])
            base = rrf_scores([bm25_rank[i], lsa_rank[i]])
            pool = set(base) | {ids[j] for j in np.argsort(-lsa_sims[i])[:POOL]}
            scored = [((base.get(d, 0.0) * (1.0 if d in gold else SLOT_PENALTY)), d)
                      for d in pool]
            scored.sort(key=lambda x: (-x[0], x[1]))
            ranked.append([d for _, d in scored[:TOPK]])
        return ranked

    def rank_gold_additive(lam, pool_size=POOL):
        """Control matched to the ADDITIVE prior systems: add lam/(RRF_K+1) to the
        base score of every gold document, over the same candidate pool. This is
        the mechanism-matched measure of what perfect predicate reconstruction is
        worth to a system built the way ours is."""
        ranked = []
        for i, q in enumerate(queries):
            gold = set(q["gold_event_ids"])
            base = rrf_scores([bm25_rank[i], lsa_rank[i]])
            pool = set(base) | {ids[j] for j in np.argsort(-lsa_sims[i])[:pool_size]}
            scored = [(base.get(d, 0.0) + (lam / (RRF_K + 1) if d in gold else 0.0), d)
                      for d in pool]
            scored.sort(key=lambda x: (-x[0], x[1]))
            ranked.append([d for _, d in scored[:TOPK]])
        return ranked

    def rank_gold_lookup():
        """The literal answer key: rank gold documents first. Ceiling, reported so
        that no reader mistakes either matched control for one."""
        ranked = []
        for i, q in enumerate(queries):
            gold = [g for g in q["gold_event_ids"]]
            rest = [d for d in rrf_scores([bm25_rank[i], lsa_rank[i]]) if d not in set(gold)]
            ranked.append((sorted(gold) + rest)[:TOPK])
        return ranked

    def rank_with_prior(prior, use_slots=False, pool_size=POOL, base_rank=None):
        ranked = []
        for i, q in enumerate(queries):
            base = rrf_scores(base_rank[i] if base_rank is not None
                              else [bm25_rank[i], lsa_rank[i]])
            pool = set(base) | set(ids[j] for j in np.argsort(-lsa_sims[i])[:pool_size])
            slots = extract_slots(q["question"]) if use_slots else {}
            scored = []
            for d in pool:
                j = pos[d]
                s = base.get(d, 0.0)
                if prior is not None:
                    s += LAMBDA * (prior[i, doc_cat[j]] / (RRF_K + 1))
                if slots and not slot_ok(events[j], slots):
                    s *= SLOT_PENALTY
                scored.append((s, d))
            scored.sort(key=lambda x: (-x[0], x[1]))
            ranked.append([d for _, d in scored[:TOPK]])
        return ranked

    # --- choose LAMBDA per system on the dev split only --------------------
    global LAMBDA
    dev_idx = [i for i, q in enumerate(queries) if q["split"] == "dev"]
    lam_sweep, lam_chosen = {}, {}
    variants = {
        "qir_clf": (clf_prior, False),
        "qir_centroid": (centroid_prior, False),
        "qir_oracle": (oracle_prior, False),
        "qir_clf_slots": (clf_prior, True),
        "qir_centroid_slots": (centroid_prior, True),
        "qir_oracle_slots": (oracle_prior, True),
    }
    systems = {
        "hybrid_rrf": [
            [d for d, _ in sorted(rrf_scores([b, l]).items(), key=lambda x: (-x[1], x[0]))][:TOPK]
            for b, l in zip(bm25_rank, lsa_rank)],
    }

    # Controls that isolate the constraint channel from the defect prior.
    LAMBDA = 0.0
    systems["slots_only"] = rank_with_prior(None, use_slots=True)
    systems["prefilter_hybrid"] = rank_prefilter()
    systems["gold_downweight_control"] = rank_gold_downweight()
    systems["gold_lookup_ceiling"] = rank_gold_lookup()

    # The additive gold control gets its lambda chosen on dev, exactly like the
    # additive prior systems it is meant to bound.
    sweep = {}
    for lam in LAMBDA_GRID:
        r = rank_gold_additive(lam)
        rows = [evaluate(r[i], queries[i]["gold_event_ids"]) for i in dev_idx]
        sweep[str(lam)] = round(float(np.mean([x["ndcg@10"] for x in rows])), 4)
    best_gold_lam = float(max(sweep, key=sweep.get))
    lam_sweep["gold_additive_control"] = sweep
    lam_chosen["gold_additive_control"] = best_gold_lam
    systems["gold_additive_control"] = rank_gold_additive(best_gold_lam)
    for name, (prior, slots) in variants.items():
        sweep = {}
        for lam in LAMBDA_GRID:
            LAMBDA = lam
            r = rank_with_prior(prior, use_slots=slots)
            rows = [evaluate(r[i], queries[i]["gold_event_ids"]) for i in dev_idx]
            sweep[str(lam)] = round(float(np.mean([x["ndcg@10"] for x in rows])), 4)
        best = float(max(sweep, key=sweep.get))
        lam_sweep[name], lam_chosen[name] = sweep, best
        LAMBDA = best
        systems[name] = rank_with_prior(prior, use_slots=slots)

    metrics = [f"recall@{k}" for k in KS] + ["precision@10", "ndcg@10", "mrr"]
    per_query_all = {s: [evaluate(r, q["gold_event_ids"]) for r, q in zip(rank, queries)]
                     for s, rank in systems.items()}
    keep_test = [q["split"] == "test" for q in queries]
    per_query = {s: [r for r, k in zip(rows, keep_test) if k]
                 for s, rows in per_query_all.items()}
    test_queries = [q for q in queries if q["split"] == "test"]

    clusters, n_clusters = cluster_ids(test_queries)
    fams_of = [q["family"] for q in test_queries]
    families_all = sorted(set(fams_of))

    summary = {}
    for s, rows in per_query.items():
        summary[s] = {}
        for m in metrics:
            vals = [r[m] for r in rows]
            summary[s][m] = {
                "mean": round(float(np.mean(vals)), 4),
                "ci95_cluster": list(bootstrap_ci(vals, rng, clusters, n_clusters)),
                "ci95_iid": list(bootstrap_ci(vals, rng)),
                "macro_over_families": round(float(np.mean(
                    [np.mean([v for v, f in zip(vals, fams_of) if f == fam])
                     for fam in families_all])), 4),
            }

    families = families_all
    by_family = {}
    for s, rows in per_query.items():
        by_family[s] = {}
        for f in families:
            sel = [r for r, q in zip(rows, test_queries) if q["family"] == f]
            cell = {"n_queries": len(sel)}
            for m in metrics:
                vals = [r[m] for r in sel]
                cell[m] = round(float(np.mean(vals)), 4)
            lo, hi = bootstrap_ci([r["ndcg@10"] for r in sel], rng)
            cell["ndcg@10_ci95_iid"] = [lo, hi]
            by_family[s][f] = cell

    # Systems under test. The Holm family is these eight only. The three gold
    # controls below are diagnostics of the benchmark, not candidate systems, and
    # including them in a multiple-comparison family over systems would be a
    # category error; they are contrasted and reported without entering the
    # correction. (Their raw p are all below the bootstrap's 0.001 resolution, so
    # this choice leaves every adjusted p in the manuscript unchanged.)
    contrast_systems = ["qir_clf", "qir_centroid", "qir_oracle", "slots_only",
                        "prefilter_hybrid", "qir_clf_slots", "qir_centroid_slots",
                        "qir_oracle_slots"]
    control_systems = ["gold_downweight_control", "gold_additive_control",
                       "gold_lookup_ceiling"]
    contrasts, raw_p = {}, []
    for s in contrast_systems + control_systems:
        a = np.array([r["ndcg@10"] for r in per_query[s]])
        b = np.array([r["ndcg@10"] for r in per_query["hybrid_rrf"]])
        diff = a - b
        boot = cluster_bootstrap(diff, clusters, n_clusters, rng)
        p = float(min(1.0, 2 * min((boot <= 0).mean(), (boot >= 0).mean())))
        raw_p.append(p)
        contrasts[f"{s} - hybrid_rrf"] = {
            "mean_diff_ndcg@10": round(float(diff.mean()), 4),
            "ci95_cluster": [round(float(np.percentile(boot, 2.5)), 4),
                             round(float(np.percentile(boot, 97.5)), 4)],
            "p_two_sided_raw": round(p, 4),
        }
    _sys_p = holm(raw_p[:len(contrast_systems)])
    for k, adj in zip(contrast_systems, _sys_p):
        contrasts[f"{k} - hybrid_rrf"]["p_holm"] = adj
    for k in control_systems:
        contrasts[f"{k} - hybrid_rrf"]["p_holm"] = None
        contrasts[f"{k} - hybrid_rrf"]["p_holm_note"] = (
            "not a system under test; excluded from the Holm family and reported "
            "with its raw p only")
    for k, v in contrasts.items():
        v["p_note"] = (f"two-sided p is 2*min(tail); with {BOOTSTRAP} resamples the "
                       f"smallest attainable non-zero value is {2 / BOOTSTRAP}, so a "
                       f"reported 0.0 means p < {2 / BOOTSTRAP}")

    # Ablation contrasts that isolate each channel.
    channel = {}
    for name, a_key, b_key in [
        ("constraint channel alone (slots_only - hybrid_rrf)", "slots_only", "hybrid_rrf"),
        ("defect prior on top of constraints (qir_centroid_slots - slots_only)",
         "qir_centroid_slots", "slots_only"),
        ("classifier prior on top of constraints (qir_clf_slots - slots_only)",
         "qir_clf_slots", "slots_only"),
        ("centroid vs classifier prior with constraints",
         "qir_centroid_slots", "qir_clf_slots"),
        ("down-weight gold control vs proposed",
         "gold_downweight_control", "qir_centroid_slots"),
        ("additive gold control vs proposed",
         "gold_additive_control", "qir_centroid_slots"),
    ]:
        diff = (np.array([r["ndcg@10"] for r in per_query[a_key]])
                - np.array([r["ndcg@10"] for r in per_query[b_key]]))
        boot = cluster_bootstrap(diff, clusters, n_clusters, rng)
        channel[name] = {
            "mean_diff_ndcg@10": round(float(diff.mean()), 4),
            "ci95_cluster": [round(float(np.percentile(boot, 2.5)), 4),
                             round(float(np.percentile(boot, 97.5)), 4)],
        }

    labelled_test = [(i, q["predicate"]["defect_category"])
                     for i, q in enumerate(queries)
                     if "defect_category" in q["predicate"] and q["split"] == "test"]
    def nd(sysname):
        return prop_summary[sysname]["ndcg@10"]["mean"]

    prop_summary = summary
    base_nd = nd("hybrid_rrf")
    recon = {
        "note": ("how much of the gain available from perfectly reconstructing the "
                 "gold predicate the proposed configuration recovers, measured "
                 "against the MECHANISM-MATCHED additive control rather than "
                 "against the literal answer key"),
        "text_only": round(base_nd, 4),
        "proposed_centroid_plus_metadata": round(nd("qir_centroid_slots"), 4),
        "matched_additive_gold_control": round(nd("gold_additive_control"), 4),
        "downweight_gold_control_matched_to_soft_filter": round(nd("gold_downweight_control"), 4),
        "oracle_category_plus_metadata": round(nd("qir_oracle_slots"), 4),
        "literal_gold_lookup_ceiling": round(nd("gold_lookup_ceiling"), 4),
        "fraction_of_matched_control_recovered": round(
            (nd("qir_centroid_slots") - base_nd)
            / (nd("gold_additive_control") - base_nd), 4),
    }

    # --- how uncertain is that fraction? -----------------------------------
    # It is a ratio of two differences, each of which has a wide interval. Resample
    # the ratio itself under the same cluster bootstrap rather than quoting it bare.
    def _pq(s_):
        return np.array([r["ndcg@10"] for r in per_query[s_]], float)

    _idx = cluster_resamples(clusters, n_clusters, rng)
    _base, _prop, _ctrl, _soft, _dw = (_pq("hybrid_rrf"), _pq("qir_centroid_slots"),
                                       _pq("gold_additive_control"), _pq("slots_only"),
                                       _pq("gold_downweight_control"))
    _ratio = np.array([(_prop[i].mean() - _base[i].mean())
                       / (_ctrl[i].mean() - _base[i].mean()) for i in _idx])
    recon["fraction_recovered_ci95_cluster"] = [
        round(float(np.percentile(_ratio, 2.5)), 4),
        round(float(np.percentile(_ratio, 97.5)), 4)]

    # The one pairing in which system and control share a scoring mechanism exactly:
    # the soft metadata filter is purely multiplicative, and so is its control.
    _ratio_mult = np.array([(_soft[i].mean() - _base[i].mean())
                            / (_dw[i].mean() - _base[i].mean()) for i in _idx])
    recon["mechanism_exact_pair"] = {
        "note": ("the proposed configuration scores additively AND multiplicatively "
                 "(prior added, then slot penalty applied), while the additive gold "
                 "control is additive only; the only exactly matched pair available "
                 "is the purely multiplicative soft filter against the purely "
                 "multiplicative down-weight control"),
        "system": "slots_only",
        "control": "gold_downweight_control",
        "fraction_recovered": round((nd("slots_only") - base_nd)
                                    / (nd("gold_downweight_control") - base_nd), 4),
        "ci95_cluster": [round(float(np.percentile(_ratio_mult, 2.5)), 4),
                         round(float(np.percentile(_ratio_mult, 97.5)), 4)],
    }

    # --- the additive control is a measurement of the candidate pool -------
    # Beyond a small lambda the control ranks every gold document in the pool above
    # every non-gold one, so its score is the pool's gold recall and the additive
    # constant stops mattering. POOL was fixed a priori and never swept, so the
    # recovered fraction inherits an unswept constant. Quantify that dependence.
    pool_grid = [100, POOL, 600, 1000, 2000, len(ids)]
    pool_rows = []
    for ps in pool_grid:
        sw_c = {}
        for lam in LAMBDA_GRID:
            r = rank_gold_additive(lam, pool_size=ps)
            sw_c[lam] = float(np.mean([evaluate(r[i], queries[i]["gold_event_ids"])["ndcg@10"]
                                       for i in dev_idx]))
        lam_c = max(sw_c, key=sw_c.get)
        r_c = rank_gold_additive(lam_c, pool_size=ps)
        ctrl_test = float(np.mean([evaluate(r_c[i], queries[i]["gold_event_ids"])["ndcg@10"]
                                   for i, q in enumerate(queries) if q["split"] == "test"]))
        sw_p = {}
        for lam in LAMBDA_GRID:
            LAMBDA = lam
            r = rank_with_prior(centroid_prior, use_slots=True, pool_size=ps)
            sw_p[lam] = float(np.mean([evaluate(r[i], queries[i]["gold_event_ids"])["ndcg@10"]
                                       for i in dev_idx]))
        lam_p = max(sw_p, key=sw_p.get)
        LAMBDA = lam_p
        r_p = rank_with_prior(centroid_prior, use_slots=True, pool_size=ps)
        prop_test = float(np.mean([evaluate(r_p[i], queries[i]["gold_event_ids"])["ndcg@10"]
                                   for i, q in enumerate(queries) if q["split"] == "test"]))
        pool_rows.append({
            "pool": ps,
            "lambda_control": lam_c, "lambda_proposed": lam_p,
            "matched_additive_gold_control": round(ctrl_test, 4),
            "proposed_centroid_plus_metadata": round(prop_test, 4),
            "fraction_recovered": round((prop_test - base_nd) / (ctrl_test - base_nd), 4),
        })
    recon["pool_sensitivity"] = {
        "note": ("both the control and the proposed system are re-run at each pool "
                 "size with lambda re-selected on dev; text-only baseline held fixed. "
                 "At the full corpus the matched control equals the literal ceiling, "
                 "which shows the 0.823-vs-1.000 gap is pool truncation, not scoring "
                 "mechanism."),
        "rows": pool_rows,
    }

    # --- robustness: does the null survive a pretrained-encoder base? ------
    # The corpus-trained base is the obvious way to dismiss a null result ("your
    # retriever was weak"). Re-run the headline contrast on bm25 + lsa + BGE.
    dense = load_dense(ids, [q["query_id"] for q in queries])
    if dense is not None:
        D_docs, D_q = dense
        d_sims = D_q @ D_docs.T
        d_rank = [[ids[j] for j in np.argsort(-row)[:TOPK]] for row in d_sims]
        base_dense = [[bm25_rank[i], lsa_rank[i], d_rank[i]] for i in range(len(queries))]

        dense_systems = {"hybrid_rrf_dense": rank_with_prior(
            None, use_slots=False, base_rank=base_dense)}
        LAMBDA = 0.0
        dense_systems["hybrid_rrf_dense"] = rank_with_prior(
            None, use_slots=False, base_rank=base_dense)
        for nm, prior in [("qir_centroid_dense", centroid_prior),
                          ("qir_clf_dense", clf_prior)]:
            sw = {}
            for lam in LAMBDA_GRID:
                LAMBDA = lam
                r = rank_with_prior(prior, base_rank=base_dense)
                sw[str(lam)] = round(float(np.mean(
                    [evaluate(r[i], queries[i]["gold_event_ids"])["ndcg@10"]
                     for i in dev_idx])), 4)
            best = float(max(sw, key=sw.get))
            lam_sweep[nm], lam_chosen[nm] = sw, best
            LAMBDA = best
            dense_systems[nm] = rank_with_prior(prior, base_rank=base_dense)

        d_pq = {k: [evaluate(r, q["gold_event_ids"])
                    for r, q, keep in zip(v, queries, keep_test) if keep]
                for k, v in dense_systems.items()}
        d_block = {"note": ("the headline contrast re-run on a base that fuses BM25, "
                            "LSA and a pretrained BGE encoder; reported so the null "
                            "cannot be attributed to a weak text channel. The main "
                            "results keep the bm25+lsa base because it needs no "
                            "downloaded weights and so reproduces offline."),
                   "summary": {}}
        for k, rows in d_pq.items():
            vals = [r["ndcg@10"] for r in rows]
            d_block["summary"][k] = {
                "ndcg@10": round(float(np.mean(vals)), 4),
                "ci95_cluster": list(bootstrap_ci(vals, rng, clusters, n_clusters)),
                "recall@50": round(float(np.mean([r["recall@50"] for r in rows])), 4)}
        d_block["by_family_hybrid_rrf_dense"] = {
            f: round(float(np.mean([r["ndcg@10"] for r, q in zip(d_pq["hybrid_rrf_dense"],
                                                                 test_queries)
                                    if q["family"] == f])), 4)
            for f in families}
        d_block["contrasts"], _draw = {}, []
        for nm in ("qir_centroid_dense", "qir_clf_dense"):
            diff = (np.array([r["ndcg@10"] for r in d_pq[nm]])
                    - np.array([r["ndcg@10"] for r in d_pq["hybrid_rrf_dense"]]))
            boot = cluster_bootstrap(diff, clusters, n_clusters, rng)
            d_block["contrasts"][f"{nm} - hybrid_rrf_dense"] = {
                "mean_diff_ndcg@10": round(float(diff.mean()), 4),
                "ci95_cluster": [round(float(np.percentile(boot, 2.5)), 4),
                                 round(float(np.percentile(boot, 97.5)), 4)],
                "p_two_sided_raw": round(float(min(1.0, 2 * min(
                    (boot <= 0).mean(), (boot >= 0).mean()))), 4)}
            _draw.append(d_block["contrasts"][f"{nm} - hybrid_rrf_dense"]
                         ["p_two_sided_raw"])
        # Holm within this pair, so the robustness check is corrected the same way
        # the main contrasts are and cannot look stronger merely by being untested.
        for (k_, v_), adj in zip(d_block["contrasts"].items(), holm(_draw)):
            v_["p_holm_within_robustness_pair"] = adj
        recon["dense_base_robustness"] = d_block
    else:
        recon["dense_base_robustness"] = None
        print("dense_embeddings.npz not found -- skipping the pretrained-encoder "
              "robustness check (run scripts/09_dense_encode.py)")

    # --- is the oracle configuration distinguishable from the gold control? -
    # On every family whose predicate is defect-category AND a metadata constraint,
    # boosting the true category and then penalising constraint violations selects
    # exactly the gold set, so the two are the same object.
    recon["oracle_vs_gold_control_by_family"] = {
        f: {"qir_oracle_slots": by_family["qir_oracle_slots"][f]["ndcg@10"],
            "gold_additive_control": by_family["gold_additive_control"][f]["ndcg@10"],
            "identical": bool(abs(by_family["qir_oracle_slots"][f]["ndcg@10"]
                                  - by_family["gold_additive_control"][f]["ndcg@10"]) < 1e-9)}
        for f in families}
    recon["n_families_where_oracle_equals_gold_control"] = sum(
        1 for f in families if recon["oracle_vs_gold_control_by_family"][f]["identical"])

    out = {
        "seed": SEED,
        "predicate_reconstruction": recon,
        "n_queries_total": len(queries),
        "n_queries_test": len(test_queries),
        "split": "headline metrics computed on the held-out test split",
        "lambda_selection": {"grid": LAMBDA_GRID, "dev_ndcg@10_by_system": lam_sweep,
                             "selected_per_system": lam_chosen,
                             "selected_on": "dev split, nDCG@10"},
        "config": { "slot_penalty": SLOT_PENALTY, "svd_dim": SVD_DIM,
                   "rrf_k": RRF_K, "bootstrap_resamples": BOOTSTRAP, "top_k": TOPK},
        "query_category_top1_accuracy": {
            "n_queries_with_category_all": len(labelled),
            "n_queries_with_category_test": len(labelled_test),
            "classifier_zero_shot_test": round(float(np.mean(
                [cats[int(clf_prior[i].argmax())] == c for i, c in labelled_test])), 4),
            "lsa_centroid_test": round(float(np.mean(
                [cats[int(centroid_prior[i].argmax())] == c for i, c in labelled_test])), 4),
            "classifier_zero_shot_all": round(float(clf_top1), 4),
            "lsa_centroid_all": round(float(cen_top1), 4),
            "chance": round(1 / len(cats), 4),
        },
        "summary": summary,
        "summary_all_queries": {
            s: {m: round(float(np.mean([r[m] for r in rows])), 4) for m in metrics}
            for s, rows in per_query_all.items()},
        "by_family": by_family,
        "n_bootstrap_clusters": n_clusters,
        "contrasts_vs_hybrid": contrasts,
        "channel_ablations": channel,
        "unswept_hyperparameters": {
            "note": "fixed a priori, NOT selected on dev; only lambda was swept",
            "slot_penalty": SLOT_PENALTY, "centroid_softmax_temperature": 8,
            "lsa_pool_expansion": POOL, "rrf_k": RRF_K, "svd_dim": SVD_DIM,
            "gold_set_size_window": [3, 75],
            "gold_set_size_window_note": (
                "MIN_GOLD/MAX_GOLD in scripts/03_build_benchmark.py; queries "
                "outside this window are dropped from the benchmark. Fixed a "
                "priori and never swept, but it shapes the evaluation as much as "
                "any ranking hyper-parameter and belongs in this list."),
        },
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    runs_path = os.path.join(ROOT, "results", "retrieval_runs_proposed.json")
    with open(runs_path, "w", encoding="utf-8") as fh:
        json.dump({s: {q["query_id"]: r for q, r in zip(queries, rank)}
                   for s, rank in systems.items()}, fh)

    print("lambda chosen on dev:", lam_chosen)
    print("query-category top-1:", out["query_category_top1_accuracy"])
    print(f"\n{'system':20s}" + "".join(f"{m:>13s}" for m in metrics))
    for s in systems:
        print(f"{s:20s}" + "".join(f"{summary[s][m]['mean']:13.4f}" for m in metrics))
    print("\ncontrasts (nDCG@10 vs hybrid_rrf):")
    for k, v in contrasts.items():
        print(f"  {k:40s} {v['mean_diff_ndcg@10']:+.4f} CI {v['ci95_cluster']} "
              f"p_raw={v['p_two_sided_raw']} p_holm={v['p_holm']}")
    print("\nchannel ablations:")
    for k, v in channel.items():
        print(f"  {k:56s} {v['mean_diff_ndcg@10']:+.4f} CI {v['ci95_cluster']}")


if __name__ == "__main__":
    main()
