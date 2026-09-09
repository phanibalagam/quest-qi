"""
06_generation_harness.py -- build the answer-synthesis prompt pack.

No LLM endpoint is reachable from this environment, so generation is run through
a documented manual harness: this script writes the exact prompts, an operator
runs them once against a single frozen model, and the verbatim outputs are saved
to results/generation/answers.json for script 07 to score. Everything the scorer
uses is objective and checkable against the corpus.

Two conditions per question:
  grounded     the model sees the top-10 retrieved events and must cite them
  closed_book  the model sees only the question

Input :  data/processed/events_labeled.jsonl, data/processed/benchmark.jsonl
Output:  results/generation/prompts.json
         results/generation/prompt_pack.txt   (human-readable)

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import hashlib
import json
import os
import random

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS = os.path.join(ROOT, "data", "processed", "events_labeled.jsonl")
BENCH = os.path.join(ROOT, "data", "processed", "benchmark.jsonl")
RUNSDIR = os.path.join(ROOT, "results")
OUTDIR = os.path.join(ROOT, "results", "generation")

SEED = 20260906
N_QUESTIONS = 24
TOP_N_EVIDENCE = 10
SYSTEM_FOR_EVIDENCE = "hybrid_rrf"   # the text-only pipeline; the study this fed was Sec. 5.6, now WITHDRAWN

GROUNDED_INSTRUCTIONS = """You are supporting a pharmaceutical quality investigation.

Answer the question using ONLY the numbered evidence below. Rules:
1. Every sentence that states a fact must end with one or more citations in the
   form [E3] or [E3][E7], naming the evidence items that support it.
2. Do not state any fact that is not in the evidence. Do not add background
   knowledge, and do not name any firm, product, date or recall number that does
   not appear in the evidence.
3. If the evidence does not support an answer, reply exactly:
   INSUFFICIENT EVIDENCE
4. Keep the answer under 150 words. Do not add a preamble or a closing offer.
"""

CLOSED_BOOK_INSTRUCTIONS = """You are supporting a pharmaceutical quality investigation.

Answer the question from your own knowledge. Be specific: name the firms,
products, dates and recall numbers you believe are involved. Keep the answer
under 150 words. Do not add a preamble or a closing offer.
"""


def evidence_block(events_by_id, ids):
    lines = []
    for i, eid in enumerate(ids, 1):
        e = events_by_id[eid]
        products = "; ".join(e["products"][:3])
        if len(e["products"]) > 3:
            products += f"; (+{len(e['products']) - 3} more presentations)"
        lines.append(
            f"[E{i}] event_id={e['event_id']} | firm={e['firm']} | "
            f"location={', '.join(x for x in [e['city'], e['state'], e['country']] if x)} | "
            f"classification={e['classification']} | status={e['status']} | "
            f"recall_initiated={e['recall_initiation_date']} | "
            f"recall_numbers={', '.join(e['recall_numbers'][:3]) or 'n/a'}\n"
            f"      reason_for_recall: {e['reason_for_recall']}\n"
            f"      products: {products}"
        )
    return "\n".join(lines)


def main():
    rng = random.Random(SEED)
    events = [json.loads(l) for l in open(EVENTS, encoding="utf-8")]
    by_id = {e["event_id"]: e for e in events}
    queries = [json.loads(l) for l in open(BENCH, encoding="utf-8")]
    test = [q for q in queries if q["split"] == "test"]

    runs_path = os.path.join(RUNSDIR, "generation_runs.json")
    if not os.path.exists(runs_path):
        raise SystemExit("Run scripts/05_taxonomy_aware_retrieval.py first.")
    runs = json.load(open(runs_path, encoding="utf-8"))[SYSTEM_FOR_EVIDENCE]

    # Stratified sample of test questions.
    by_family = {}
    for q in test:
        by_family.setdefault(q["family"], []).append(q)
    chosen = []
    families = sorted(by_family)
    per = max(1, N_QUESTIONS // len(families))
    for fam in families:
        pool = sorted(by_family[fam], key=lambda q: q["query_id"])
        rng.shuffle(pool)
        chosen.extend(pool[:per])
    pool = [q for q in sorted(test, key=lambda q: q["query_id"]) if q not in chosen]
    rng.shuffle(pool)
    chosen.extend(pool[:max(0, N_QUESTIONS - len(chosen))])
    chosen = chosen[:N_QUESTIONS]
    chosen.sort(key=lambda q: q["query_id"])

    prompts = []
    for q in chosen:
        ev_ids = runs[q["query_id"]][:TOP_N_EVIDENCE]
        prompts.append({
            "query_id": q["query_id"],
            "family": q["family"],
            "question": q["question"],
            "n_gold": q["n_gold"],
            "gold_event_ids": q["gold_event_ids"],
            "evidence_event_ids": ev_ids,
            "n_relevant_in_evidence": len(set(ev_ids) & set(q["gold_event_ids"])),
            "prompt_grounded": (GROUNDED_INSTRUCTIONS + "\nEVIDENCE\n" +
                                evidence_block(by_id, ev_ids) +
                                f"\n\nQUESTION\n{q['question']}\n"),
            "prompt_closed_book": (CLOSED_BOOK_INSTRUCTIONS +
                                   f"\nQUESTION\n{q['question']}\n"),
        })

    # Hash each prompt so script 07 can refuse to score answers written against a
    # different version of the corpus, benchmark or retrieval run.
    for pr in prompts:
        pr["prompt_sha256"] = hashlib.sha256(
            pr["prompt_grounded"].encode("utf-8")).hexdigest()

    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "prompts.json"), "w", encoding="utf-8") as fh:
        json.dump({"seed": SEED, "evidence_system": SYSTEM_FOR_EVIDENCE,
                   "top_n_evidence": TOP_N_EVIDENCE, "prompts": prompts}, fh, indent=2)

    with open(os.path.join(OUTDIR, "prompt_pack.txt"), "w", encoding="utf-8") as fh:
        for p in prompts:
            fh.write("=" * 78 + f"\n{p['query_id']}  [{p['family']}]\n" + "=" * 78 + "\n")
            fh.write("--- GROUNDED ---\n" + p["prompt_grounded"] + "\n")
            fh.write("--- CLOSED BOOK ---\n" + p["prompt_closed_book"] + "\n\n")

    print(json.dumps({
        "n_prompts": len(prompts),
        "families": {f: sum(1 for p in prompts if p["family"] == f) for f in families},
        "mean_relevant_in_top10": round(
            float(np.mean([p["n_relevant_in_evidence"] for p in prompts])), 2),
        "questions_with_zero_relevant_evidence": sum(
            1 for p in prompts if p["n_relevant_in_evidence"] == 0),
    }, indent=2))


if __name__ == "__main__":
    main()
