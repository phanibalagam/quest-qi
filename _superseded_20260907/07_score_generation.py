"""
07_score_generation.py -- score the answer-synthesis study.

Everything scored here is checkable against the corpus. No answer is scored by
another language model, and no rubric judgement enters the numbers.

Metrics
  citation_index_validity fraction of [E#] citations whose index names an evidence
                          item that was actually supplied. This is an index-bounds
                          check, NOT a check that the cited item supports the claim.
  citation_precision      fraction of cited evidence items that are gold for the
                          question
  evidence_utilisation    fraction of the gold evidence items in the prompt that
                          the answer cited
  recall_numbers_verified fraction of D-nnnn-yyyy recall numbers in the answer
                          that exist in the corpus
  firms_verified          fraction of organization mentions that match a corpus
                          recalling firm
  firms_relevant          fraction of matched firms that have at least one gold
                          event for the question
  abstention              answered INSUFFICIENT EVIDENCE

Organisation mentions are found with a corporate-suffix regex; this is a
heuristic and is reported as such.

Input :  results/generation/prompts.json, answers_grounded_part*.json,
         answers_closed_book.json, data/processed/events_labeled.jsonl
Output:  results/generation_results.json

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import glob
import hashlib
import json
import os
import re
from collections import Counter

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, "results", "generation")
EVENTS = os.path.join(ROOT, "data", "processed", "events_labeled.jsonl")
OUT = os.path.join(ROOT, "results", "generation_results.json")

CITE = re.compile(r"\[E(\d{1,2})\]")
RECALL_NO = re.compile(r"\bD-?\d{3,4}-\d{4}\b")
SUFFIX = r"(?:Inc|Inc\.|LLC|L\.L\.C\.|Ltd|Ltd\.|Limited|Corp|Corp\.|Corporation|Company|Co\.|" \
         r"Pharma|Pharmaceuticals|Pharmaceutical|Laboratories|Labs|Therapeutics|Healthcare|" \
         r"Biotech|Bioscience|Biosciences|GmbH|AG|S\.A\.|SL|A/S|Pvt)"
ORG = re.compile(r"\b(?:[A-Z][\w&'\-\.]*\s+){0,4}" + SUFFIX + r"\b")
# Well-known single-token firm names that the suffix regex cannot catch.
EXTRA_ORG = re.compile(
    r"\b(Pfizer|Novartis|Sandoz|Teva|Mylan|Viatris|Apotex|Amneal|Hospira|Baxter|Akorn|Lupin|"
    r"Aurobindo|Wockhardt|Ranbaxy|Zydus|Torrent|Glenmark|Endo|Biogen|Amgen|AbbVie|Roche|"
    r"Perrigo|Altaire|Alcon|Fresenius|McKesson|Cardinal|Sesderma|Medichem|Marksans|Granules)\b")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def load_answers():
    grounded = {}
    for path in sorted(glob.glob(os.path.join(GEN, "answers_grounded_part*.json"))):
        grounded.update(json.load(open(path, encoding="utf-8")))
    closed = json.load(open(os.path.join(GEN, "answers_closed_book.json"),
                            encoding="utf-8"))["answers"]
    return grounded, closed


GENERIC = {"company", "corporation", "corp", "inc", "llc", "ltd", "limited",
           "laboratories", "labs", "pharma", "pharmaceuticals", "pharmaceutical",
           "therapeutics", "healthcare", "biotech", "co", "ag", "gmbh", "sl"}


def clean_mention(s):
    """Drop a sentence-final word that the regex swallowed ("...States. Attix Pharma")."""
    s = s.strip()
    if ". " in s:
        s = s.rsplit(". ", 1)[1]
    return s.strip()


def org_mentions(text):
    found = set()
    for m in ORG.finditer(text):
        s = clean_mention(m.group(0))
        if len(s) >= 5 and norm(s) not in GENERIC:
            found.add(s)
    for m in EXTRA_ORG.finditer(text):
        found.add(m.group(0))
    return found


def match_firm(mention, firm_index):
    """Return the corpus firm whose normalised name shares the mention's head."""
    n = norm(mention)
    if len(n) < 4:
        return None
    if n in firm_index:
        return firm_index[n]
    for key, firm in firm_index.items():
        if n in key or key in n:
            return firm
    return None


def main():
    events = [json.loads(l) for l in open(EVENTS, encoding="utf-8")]
    firms = sorted({e["firm"] for e in events if e["firm"]})
    firm_index = {norm(f): f for f in firms}
    firm_events = {}
    for e in events:
        firm_events.setdefault(e["firm"], set()).add(e["event_id"])
    corpus_recall_numbers = {r for e in events for r in e["recall_numbers"]}
    corpus_recall_numbers |= {r.replace("-", "", 1) for r in corpus_recall_numbers}

    pack = json.load(open(os.path.join(GEN, "prompts.json"), encoding="utf-8"))
    prompts = {p["query_id"]: p for p in pack["prompts"]}
    grounded, closed = load_answers()

    missing = set(prompts) - set(grounded), set(prompts) - set(closed)
    if any(missing):
        raise SystemExit(f"missing answers: grounded={missing[0]} closed={missing[1]}")

    stale = [p["query_id"] for p in pack["prompts"]
             if p.get("prompt_sha256") and p["prompt_sha256"] != hashlib.sha256(
                 p["prompt_grounded"].encode("utf-8")).hexdigest()]
    if stale:
        raise SystemExit(f"prompt hashes do not match their text: {stale}")

    rows = {"grounded": [], "closed_book": []}
    for qid, p in prompts.items():
        gold = set(p["gold_event_ids"])
        ev_ids = p["evidence_event_ids"]
        rel_in_ev = [i for i, e in enumerate(ev_ids, 1) if e in gold]

        for cond, text in (("grounded", grounded[qid]), ("closed_book", closed[qid])):
            abst = text.strip().upper().startswith("INSUFFICIENT EVIDENCE")
            cites = [int(x) for x in CITE.findall(text)]
            valid = [c for c in cites if 1 <= c <= len(ev_ids)]
            cited_events = {ev_ids[c - 1] for c in valid}

            rns = RECALL_NO.findall(text)
            rns_ok = [r for r in rns if r in corpus_recall_numbers
                      or r.replace("-", "", 1) in corpus_recall_numbers]

            mentions = org_mentions(text)
            matched = {m: match_firm(m, firm_index) for m in mentions}
            matched_ok = {m: f for m, f in matched.items() if f}
            relevant = {m: f for m, f in matched_ok.items()
                        if firm_events.get(f, set()) & gold}

            rows[cond].append({
                "query_id": qid, "family": p["family"], "abstained": abst,
                "words": len(text.split()),
                "n_citations": len(cites),
                "citation_index_validity": (len(valid) / len(cites)) if cites else None,
                "citation_precision": (len(cited_events & gold) / len(cited_events))
                                      if cited_events else None,
                "evidence_utilisation": (len(cited_events & gold) / len(rel_in_ev))
                                        if rel_in_ev else None,
                "n_recall_numbers": len(rns),
                "recall_numbers_verified": (len(rns_ok) / len(rns)) if rns else None,
                "n_org_mentions": len(mentions),
                "firms_verified": (len(matched_ok) / len(mentions)) if mentions else None,
                "firms_relevant": (len(relevant) / len(matched_ok)) if matched_ok else None,
                "n_firms_relevant": len(relevant),
                "unverified_orgs": sorted(m for m, f in matched.items() if not f),
            })

    def agg(rows_):
        out = {}
        for m in ["words", "n_citations", "citation_index_validity", "citation_precision",
                  "evidence_utilisation", "n_recall_numbers", "recall_numbers_verified",
                  "n_org_mentions", "firms_verified", "firms_relevant", "n_firms_relevant"]:
            vals = [r[m] for r in rows_ if r[m] is not None]
            out[m] = {"mean": round(float(np.mean(vals)), 4) if vals else None,
                      "n_questions_with_metric": len(vals)}
        out["abstention_rate"] = round(sum(r["abstained"] for r in rows_) / len(rows_), 4)
        out["n_answers_naming_any_organization"] = sum(
            1 for r in rows_ if r["n_org_mentions"] > 0)
        out["total_relevant_firm_mentions"] = sum(r["n_firms_relevant"] for r in rows_)
        out["n_questions"] = len(rows_)
        return out

    # Was abstention correct? A question is unanswerable from the prompt when no
    # gold event appears in the supplied evidence.
    unanswerable = {qid for qid, p in prompts.items() if p["n_relevant_in_evidence"] == 0}
    g = {r["query_id"]: r for r in rows["grounded"]}
    abstention_confusion = {
        "unanswerable_and_abstained": sum(1 for q in unanswerable if g[q]["abstained"]),
        "unanswerable_total": len(unanswerable),
        "answerable_and_abstained": sum(1 for q in prompts
                                        if q not in unanswerable and g[q]["abstained"]),
        "answerable_total": len(prompts) - len(unanswerable),
    }

    collisions = sum(1 for a in firm_index
                     for b in firm_index if a != b and (a in b or b in a))
    out = {
        "n_questions": len(prompts),
        "firm_matcher_note": (
            "organization mentions are found with a corporate-suffix regex and matched "
            "to corpus firms by normalised substring; the match is first-in-sorted-order "
            "and therefore ambiguous where firm names nest"),
        "n_firm_names": len(firm_index),
        "n_firm_names_colliding_by_substring": collisions,
        "evidence_system": pack["evidence_system"],
        "top_n_evidence": pack["top_n_evidence"],
        "grounded": agg(rows["grounded"]),
        "closed_book": agg(rows["closed_book"]),
        "abstention": abstention_confusion,
        "unverified_org_mentions": {
            "grounded": sorted({o for r in rows["grounded"] for o in r["unverified_orgs"]}),
            "closed_book": sorted({o for r in rows["closed_book"] for o in r["unverified_orgs"]}),
        },
        "per_question": rows,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    for cond in ("grounded", "closed_book"):
        print(f"--- {cond} ---")
        for k, v in out[cond].items():
            print(f"  {k}: {v}")
    print("\nabstention:", abstention_confusion)
    print("\nunverified orgs (closed book):",
          len(out["unverified_org_mentions"]["closed_book"]))
    print("unverified orgs (grounded):",
          len(out["unverified_org_mentions"]["grounded"]))


if __name__ == "__main__":
    main()
