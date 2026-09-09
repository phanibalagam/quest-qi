"""
09_dense_encode.py -- encode the corpus and the benchmark queries with pretrained
sentence encoders.

RUN THIS ON ANY HOST THAT CAN REACH huggingface.co. It is the only step in the
pipeline that touches the network.

The requirement is network egress to huggingface.co plus a working certificate
store. Python does not use the system trust store by default, so TLS verification
fails on hosts whose CAs live only there; `truststore.inject_into_ssl()` below
fixes that, and is why this script runs where a bare `pip`-installed Python does
not. That is a TLS-trust and egress matter, not a property of the analysis
environment and not a constraint a regulated deployment would face -- the weights
are downloaded once and every encoder then runs locally on CPU.

Runtime: about six minutes on CPU for the 4,652-document corpus and 171 queries.

    py -m pip install truststore sentence-transformers
    py scripts\09_dense_encode.py

Input : data/processed/events.jsonl
        data/processed/benchmark.jsonl
Output: data/processed/dense_embeddings.npz   (float32, L2-normalised)
        results/dense_manifest.json           (model, revision, dims, provenance)

The .npz is the only artifact the rest of the pipeline needs; scripts 04 and 05
read it and skip their dense channels if it is absent, so the pipeline still runs
end to end on a machine that cannot download a model.

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import json
import os
import sys
import time

# --- certificates first, before anything opens a socket ----------------------
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    print("WARNING: truststore not installed; TLS to huggingface.co will likely fail.\n"
          "         py -m pip install truststore", file=sys.stderr)

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS = os.path.join(ROOT, "data", "processed", "events.jsonl")
BENCH = os.path.join(ROOT, "data", "processed", "benchmark.jsonl")
OUT = os.path.join(ROOT, "data", "processed", "dense_embeddings.npz")
MANIFEST = os.path.join(ROOT, "results", "dense_manifest.json")

SEED = 20260906
BATCH = 64

# name -> (query prefix, passage prefix). BGE and E5 are trained with asymmetric
# instructions and lose several points if they are used without them.
MODELS = {
    "bge_base": ("BAAI/bge-base-en-v1.5",
                 "Represent this sentence for searching relevant passages: ", ""),
    "minilm":   ("sentence-transformers/all-MiniLM-L6-v2", "", ""),
}


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def main():
    from sentence_transformers import SentenceTransformer
    import torch

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.set_num_threads(max(1, (os.cpu_count() or 4) // 2))

    events = load_jsonl(EVENTS)
    queries = load_jsonl(BENCH)
    doc_ids = [e["event_id"] for e in events]
    doc_txt = [e["text"] for e in events]
    q_ids = [q["query_id"] for q in queries]
    q_txt = [q["question"] for q in queries]
    print(f"{len(doc_txt)} documents, {len(q_txt)} queries")

    payload, manifest = {}, {"seed": SEED, "models": {}}
    payload["doc_ids"] = np.array(doc_ids, dtype=object)
    payload["query_ids"] = np.array(q_ids, dtype=object)

    for key, (repo, q_prefix, d_prefix) in MODELS.items():
        print(f"\n=== {key}: {repo} ===")
        t0 = time.time()
        model = SentenceTransformer(repo, device="cpu")
        model.eval()
        load_s = time.time() - t0

        t0 = time.time()
        dv = model.encode([d_prefix + t for t in doc_txt], batch_size=BATCH,
                          normalize_embeddings=True, convert_to_numpy=True,
                          show_progress_bar=True).astype(np.float32)
        doc_s = time.time() - t0

        t0 = time.time()
        qv = model.encode([q_prefix + t for t in q_txt], batch_size=BATCH,
                          normalize_embeddings=True, convert_to_numpy=True,
                          show_progress_bar=False).astype(np.float32)
        q_s = time.time() - t0

        payload[f"{key}_docs"] = dv
        payload[f"{key}_queries"] = qv

        # Pin the exact weights, so "we used BGE" is a checkable statement.
        rev = None
        try:
            from huggingface_hub import model_info
            rev = model_info(repo).sha
        except Exception as exc:                                  # noqa: BLE001
            print(f"  (could not resolve revision: {exc})")
        manifest["models"][key] = {
            "repo": repo, "revision": rev, "dim": int(dv.shape[1]),
            "max_seq_length": int(model.max_seq_length),
            "query_prefix": q_prefix, "passage_prefix": d_prefix,
            "normalised": True, "device": "cpu",
            "n_docs": int(dv.shape[0]), "n_queries": int(qv.shape[0]),
            "seconds": {"load": round(load_s, 1), "encode_docs": round(doc_s, 1),
                        "encode_queries": round(q_s, 1)},
        }
        print(f"  dim={dv.shape[1]}  docs {doc_s:.0f}s  queries {q_s:.1f}s  rev={rev}")

    manifest["encoded_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    manifest["host"] = "windows (only host with huggingface.co reachable)"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    np.savez_compressed(OUT, **payload)
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    print(f"\nwrote {OUT} ({os.path.getsize(OUT) / 1e6:.1f} MB)")
    print(f"wrote {MANIFEST}")
    print("\nNow re-run, in order: scripts/04, scripts/05, figures/gen_figures.py, scripts/08")


if __name__ == "__main__":
    main()
