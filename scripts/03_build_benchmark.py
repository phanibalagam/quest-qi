"""
03_build_benchmark.py -- build the QUEST-QI benchmark.

QUEST-QI (QUality Event Search and Traceability for Quality Investigations)
pairs investigator-style questions with an objectively defined gold evidence set:
every corpus event that satisfies the question's structured predicate.

Queries are phrased the way an investigator would ask, NOT with the FDA canonical
defect phrase, so a system cannot succeed by string-matching the category name.

Input :  data/processed/events_labeled.jsonl
Output:  data/processed/benchmark.jsonl
         results/benchmark_stats.json

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import json
import os
import random
import re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.join(ROOT, "data", "processed", "events_labeled.jsonl")
OUT = os.path.join(ROOT, "data", "processed", "benchmark.jsonl")
STATS = os.path.join(ROOT, "results", "benchmark_stats.json")

SEED = 20260906
MIN_GOLD, MAX_GOLD = 3, 75
PER_FAMILY = 45

# Investigator phrasings. Deliberately avoid the FDA canonical phrase.
PHRASING = {
    "STERILITY_ASSURANCE": "sterility of the finished product could not be assured",
    "MICROBIAL_NONSTERILE": "microbial counts exceeded limits in a product that is not required to be sterile",
    "CROSS_CONTAMINATION": "material from another product carried over into the batch",
    "PARTICULATE_FOREIGN_MATTER": "visible particles or foreign material were found in the product",
    "IMPURITY_DEGRADATION": "a degradant or impurity exceeded its acceptance criterion",
    "DISSOLUTION": "the batch did not meet its release testing profile for drug release rate",
    "POTENCY_CONTENT": "the amount of active ingredient was outside the labelled strength",
    "STABILITY_EXPIRY": "on-going stability data did not support the assigned shelf life",
    "APPEARANCE_PHYSICAL": "the product changed in appearance, colour or physical form",
    "CONTAINER_CLOSURE_DEVICE": "the container closure or delivery device did not perform correctly",
    "LABELING_PACKAGING": "the printed label or the packaging did not match the product inside",
    "UNAPPROVED_MARKETING": "the product was distributed without the required marketing authorisation",
    "STORAGE_DISTRIBUTION": "the product was held outside its permitted storage conditions",
    "GMP_DEVIATION": "manufacturing controls were not followed as required",
    "OTHER_SPECIFICATION": "a release specification other than potency or dissolution was not met",
}

DOSAGE_FORMS = {
    "sterile injectable": r"\b(injection|injectable|vial|ampule|ampoule|infusion|syringe|iv\b|intravenous)",
    "oral solid": r"\b(tablet|capsule|caplet|softgel)",
    "ophthalmic": r"\b(ophthalmic|eye drop|eye-drop|intraocular)",
    "topical": r"\b(cream|ointment|gel\b|lotion|topical|transdermal)",
    "oral liquid": r"\b(oral solution|oral suspension|syrup|elixir|oral liquid)",
}

SEVERITY = {
    "Class I": "with the most serious health consequences (Class I)",
    "Class II": "of moderate severity (Class II)",
    "Class III": "of the lowest severity (Class III)",
}


def matches_form(event, pattern):
    blob = " ".join(event.get("products", []))[:4000].lower()
    return re.search(pattern, blob) is not None


def make(qid, family, question, predicate, gold, note=""):
    return {
        "query_id": qid,
        "family": family,
        "question": question,
        "predicate": predicate,
        "gold_event_ids": sorted(gold),
        "n_gold": len(gold),
        "note": note,
    }


def main():
    rng = random.Random(SEED)
    events = [json.loads(l) for l in open(IN, encoding="utf-8")]
    by_cat = {}
    for e in events:
        by_cat.setdefault(e["defect_category"], []).append(e)

    candidates = []

    # Family A: defect x dosage form
    for cat, phrase in PHRASING.items():
        for form, pattern in DOSAGE_FORMS.items():
            gold = [e["event_id"] for e in by_cat.get(cat, []) if matches_form(e, pattern)]
            if MIN_GOLD <= len(gold) <= MAX_GOLD:
                candidates.append(make(
                    f"A-{cat}-{form.replace(' ', '_')}", "A_defect_form",
                    f"Find previous recall events for {form} products where {phrase}.",
                    {"defect_category": cat, "dosage_form": form}, gold))

    # Family B: defect x severity classification
    for cat, phrase in PHRASING.items():
        for cls, sev in SEVERITY.items():
            gold = [e["event_id"] for e in by_cat.get(cat, []) if e["classification"] == cls]
            if MIN_GOLD <= len(gold) <= MAX_GOLD:
                candidates.append(make(
                    f"B-{cat}-{cls.replace(' ', '')}", "B_defect_severity",
                    f"Which recalls {sev} were driven by a situation where {phrase}?",
                    {"defect_category": cat, "classification": cls}, gold))

    # Family C: firm history
    firm_counts = Counter(e["firm"] for e in events if e["firm"])
    for firm, n in firm_counts.items():
        if MIN_GOLD <= n <= MAX_GOLD:
            gold = [e["event_id"] for e in events if e["firm"] == firm]
            candidates.append(make(
                f"C-{re.sub(r'[^A-Za-z0-9]+', '_', firm)[:40]}", "C_firm_history",
                f"Summarise every recall event on record for the firm {firm}.",
                {"firm": firm}, gold))

    # Family D: defect x period
    periods = [("2013", "2015"), ("2016", "2018"), ("2019", "2021"), ("2022", "2026")]
    for cat, phrase in PHRASING.items():
        for lo, hi in periods:
            gold = [e["event_id"] for e in by_cat.get(cat, [])
                    if e["init_year"] and lo <= e["init_year"] <= hi]
            if MIN_GOLD <= len(gold) <= MAX_GOLD:
                candidates.append(make(
                    f"D-{cat}-{lo}_{hi}", "D_defect_period",
                    f"Between {lo} and {hi}, which recalls happened because {phrase}?",
                    {"defect_category": cat, "year_from": lo, "year_to": hi}, gold))
    # NOTE: the predicate uses the recall INITIATION year. Both dates are written
    # into the document text (`Recall initiated: 20110315. Reported: 20120620.`),
    # so this is not a question of which date is exposed; see Section 3.3. The
    # reason is that the metadata filter of Section 5.4 reads the initiation year,
    # and using the FDA report year in the predicate would silently have the
    # predicate and the filter measure different things -- a ~14% disagreement
    # rate -- making the Section 5.4 contrast unfair by construction. Neither date
    # gives a lexical channel any purchase: both are unsegmented eight-digit
    # tokens that the tokeniser keeps whole.

    # Family E: defect x manufacturing location outside the United States
    for cat, phrase in PHRASING.items():
        gold = [e["event_id"] for e in by_cat.get(cat, [])
                if e["country"] and e["country"] != "United States"]
        if MIN_GOLD <= len(gold) <= MAX_GOLD:
            candidates.append(make(
                f"E-{cat}-exUS", "E_defect_geography",
                f"Find recalls from firms located outside the United States where {phrase}.",
                {"defect_category": cat, "country_not": "United States"}, gold))

    # Family F: site country: the country field alone
    countries = Counter(e["country"] for e in events if e["country"])
    for country, n in countries.items():
        if country == "United States":
            continue
        gold = [e["event_id"] for e in events if e["country"] == country]
        if MIN_GOLD <= len(gold) <= MAX_GOLD:
            candidates.append(make(
                f"F-country-{re.sub(r'[^A-Za-z]+', '_', country)}", "F_site_country",
                f"What recall events involve product manufactured or recalled from a site in {country}?",
                {"country": country}, gold))

    # Sample a fixed number per family.
    by_family = {}
    for c in candidates:
        by_family.setdefault(c["family"], []).append(c)
    selected = []
    for fam in sorted(by_family):
        pool = sorted(by_family[fam], key=lambda c: c["query_id"])
        rng.shuffle(pool)
        selected.extend(pool[:PER_FAMILY])
    selected.sort(key=lambda c: c["query_id"])

    # Stratified dev/test split. Hyper-parameters are chosen on dev only;
    # every headline number is reported on test.
    for fam in sorted({c["family"] for c in selected}):
        pool = [c for c in selected if c["family"] == fam]
        rng.shuffle(pool)
        n_dev = max(1, round(0.3 * len(pool)))
        for i, c in enumerate(pool):
            c["split"] = "dev" if i < n_dev else "test"
    selected.sort(key=lambda c: c["query_id"])

    with open(OUT, "w", encoding="utf-8") as fh:
        for q in selected:
            fh.write(json.dumps(q, ensure_ascii=False) + "\n")

    sizes = sorted(q["n_gold"] for q in selected)
    stats = {
        "seed": SEED,
        "n_queries": len(selected),
        "n_candidates_before_sampling": len(candidates),
        "queries_per_family": dict(Counter(q["family"] for q in selected)),
        "split_counts": dict(Counter(q["split"] for q in selected)),
        "split_by_family": {f: dict(Counter(q["split"] for q in selected if q["family"] == f))
                            for f in sorted({q["family"] for q in selected})},
        "gold_set_size": {
            "min": sizes[0], "median": sizes[len(sizes) // 2],
            "mean": round(sum(sizes) / len(sizes), 1), "max": sizes[-1],
        },
        "total_gold_pairs": sum(sizes),
        "distinct_gold_events": len({g for q in selected for g in q["gold_event_ids"]}),
        "corpus_size": len(events),
    }
    with open(STATS, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
