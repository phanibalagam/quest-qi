"""
02_taxonomy.py -- defect taxonomy for pharmaceutical quality events.

openFDA reason-for-recall text usually opens with a canonical defect phrase
("CGMP Deviations:", "Lack of Assurance of Sterility;", "Labeling - ...").
Labels are assigned in three tiers:
  prefix     -- a delimiter-terminated canonical phrase matched by the rule set;
  short      -- no delimiter, but the whole reason is itself a short canonical
                phrase matched by the rule set;
  classifier -- free-text narrative, labelled by a linear model.

The classifier is trained and cross-validated ONLY on prefix-tier events, and
only on the text that FOLLOWS the canonical phrase. The seed evidence is never a
feature, so cross-validation measures the same task the model faces on the
free-text tail rather than a trivial phrase lookup.

Input :  data/processed/events.jsonl
Output:  data/processed/events_labeled.jsonl
         results/taxonomy_eval.json

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import json
import os
import re
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.join(ROOT, "data", "processed", "events.jsonl")
OUT = os.path.join(ROOT, "data", "processed", "events_labeled.jsonl")
EVAL = os.path.join(ROOT, "results", "taxonomy_eval.json")

SEED = 20260906
# A seed label is only taken from a *delimiter-terminated* leading phrase, so the
# remainder of the text is genuinely unseen when the classifier is trained on it.
LEAD = re.compile(r"^(.{3,90}?)\s*(?::|;| - )\s*(.*)$", re.S)
SHORT_FORM_MAX = 60   # a whole reason this short is itself a canonical phrase

# Ordered rules over the normalised leading phrase. First match wins.
RULES = [
    ("MICROBIAL_NONSTERILE",
     r"(microbial contamination of (a )?non-?steril|"
     r"microbial(ogical)? contamination of non-?steril|"
     r"microbial (growth|limits) in (a )?non-?steril)"),
    ("STERILITY_ASSURANCE",
     r"(lack of (assurance of )?steril|non-?sterility|sterility assurance|"
     r"microbial contamination of (a )?steril|loss of sterility|"
     r"microbial(ogical)? contamination|microbial (growth|limits))"),
    ("CROSS_CONTAMINATION",
     r"(cross ?-?contamination|penicillin|product mix ?-?up|chemical contamination|"
     r"presence of (an? )?undeclared (drug|active))"),
    ("PARTICULATE_FOREIGN_MATTER",
     r"(particulate matter|foreign (substance|material|tablet|capsule|matter)|"
     r"presence of foreign|glass particle)"),
    ("IMPURITY_DEGRADATION",
     r"(impurit|degradation|degradant|nitrosamine|azido|out of specification results? for .*impur)"),
    ("DISSOLUTION",
     r"dissolution"),
    ("POTENCY_CONTENT",
     r"(sub-?poten|super-?poten|potency|content uniformity|assay|incorrect product formulation|"
     r"short fill|overfill|strength)"),
    ("STABILITY_EXPIRY",
     r"(stability|expiry|expiration|shelf ?-?life)"),
    ("APPEARANCE_PHYSICAL",
     r"(discolo|crystalli|precipitate|odor|clumping|caking|hardness|friability|"
     r"tablet(s)? (are )?(broken|chipped)|separation)"),
    ("CONTAINER_CLOSURE_DEVICE",
     r"(defective (container|delivery system|seal|pump|closure)|container|closure|"
     r"leak|cracked|delivery system|child ?-?resistant)"),
    ("LABELING_PACKAGING",
     r"(label|mislabel|mispack|imprint|packag|carton|insert|undeclared excipient|"
     r"incorrect/?undeclared|out of sequence|barcode|expiration date print)"),
    ("UNAPPROVED_MARKETING",
     r"(without an? approved|unapproved|does not meet monograph|not fda ?-?approved|"
     r"marketed without)"),
    ("STORAGE_DISTRIBUTION",
     r"(temperature|cold chain|storage|shipping|frozen|refrigerat)"),
    ("GMP_DEVIATION",
     r"(c?gmp deviation|good manufacturing practice|lack of processing controls|"
     r"process(ing)? control|failure to|inadequate)"),
    ("OTHER_SPECIFICATION",
     r"(failed .*(specification|test|limit|requirement)|out of specification|"
     r"does not meet|ph specification|moisture|water content|weight variation|"
     r"viscosity|particle size)"),
]
COMPILED = [(name, re.compile(pat)) for name, pat in RULES]
CATEGORIES = [name for name, _ in RULES]


def normalise(phrase):
    phrase = phrase.lower().strip().rstrip(".,;:-")
    return re.sub(r"\s+", " ", phrase)


def match_rules(phrase):
    for name, pat in COMPILED:
        if pat.search(phrase):
            return name
    return None


def seed_label(reason):
    """Return (label, tier, remainder).

    tier 'prefix' : delimiter-terminated canonical phrase; remainder is the rest.
    tier 'short'  : no delimiter, but the whole reason is a short canonical phrase.
    tier None     : free-text narrative, left to the classifier.
    """
    reason = reason.strip()
    m = LEAD.match(reason)
    if m:
        label = match_rules(normalise(m.group(1)))
        if label:
            return label, "prefix", m.group(2).strip()
        return None, None, reason
    if len(reason) <= SHORT_FORM_MAX:
        label = match_rules(normalise(reason))
        if label:
            return label, "short", ""
    return None, None, reason


def main():
    events = [json.loads(l) for l in open(IN, encoding="utf-8")]

    seeded, unseeded = [], []
    for e in events:
        label, tier, remainder = seed_label(e["reason_for_recall"])
        e["_tier"] = tier
        e["_remainder"] = remainder
        if label:
            e["_seed"] = label
            seeded.append(e)
        else:
            unseeded.append(e)

    # Classifier training uses ONLY prefix-tier events, and only the text that
    # follows the canonical phrase, so no seed evidence leaks into the features.
    trainable = [e for e in seeded
                 if e["_tier"] == "prefix" and len(e["_remainder"]) >= 15]
    counts = Counter(e["_seed"] for e in trainable)
    keep = {c for c, n in counts.items() if n >= 25}
    dropped = {c: n for c, n in counts.items() if c not in keep}
    train = [e for e in trainable if e["_seed"] in keep]

    X = [e["_remainder"] for e in train]
    y = [e["_seed"] for e in train]

    clf = make_pipeline(
        TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=2,
                        max_features=60000, strip_accents="unicode"),
        LogisticRegression(max_iter=3000, C=4.0, class_weight="balanced",
                           random_state=SEED),
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    pred = cross_val_predict(clf, X, y, cv=cv, n_jobs=-1)
    macro_f1 = f1_score(y, pred, average="macro")
    micro_f1 = f1_score(y, pred, average="micro")
    report = classification_report(y, pred, output_dict=True, zero_division=0)

    # The remainder text often still echoes a rule cue, which flatters the CV
    # number. The classifier's real population is the free-text tail, where no
    # rule fires. Report both.
    rule_free = np.array([match_rules(normalise(x)) is None for x in X])
    echoes_own = np.array([match_rules(normalise(x)) == lab for x, lab in zip(X, y)])
    y_arr = np.array(y)
    tail = {
        "n_rule_free_remainders": int(rule_free.sum()),
        "pct_remainders_still_matching_a_rule": round(100 * float((~rule_free).mean()), 1),
        "pct_remainders_echoing_own_rule": round(100 * float(echoes_own.mean()), 1),
        "cv_macro_f1_rule_free_subset": round(float(
            f1_score(y_arr[rule_free], pred[rule_free], average="macro")), 4),
        "cv_micro_f1_rule_free_subset": round(float(
            f1_score(y_arr[rule_free], pred[rule_free], average="micro")), 4),
        "cv_macro_f1_rule_echoing_subset": round(float(
            f1_score(y_arr[~rule_free], pred[~rule_free], average="macro")), 4),
    }

    clf.fit(X, y)
    if unseeded:
        Xu = [e["_remainder"] or e["reason_for_recall"] for e in unseeded]
        proba = clf.predict_proba(Xu)
        classes = clf.classes_
        idx = proba.argmax(axis=1)
        for e, i, p in zip(unseeded, idx, proba):
            e["_silver"] = classes[i]
            e["_silver_conf"] = float(p[i])

    out = []
    for e in events:
        label = e.get("_seed") or e.get("_silver")
        out.append({
            **{k: v for k, v in e.items() if not k.startswith("_")},
            "defect_category": label,
            "label_source": e.get("_tier") or "classifier",
            "label_confidence": 1.0 if e.get("_seed") else round(e.get("_silver_conf", 0.0), 4),
            "reason_remainder": e.get("_remainder", ""),
        })

    with open(OUT, "w", encoding="utf-8") as fh:
        for e in out:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    tiers = Counter(e.get("_tier") or "classifier" for e in events)
    summary = {
        "seed_random_state": SEED,
        "n_events": len(events),
        "n_rule_labelled": len(seeded),
        "rule_coverage_pct": round(100 * len(seeded) / len(events), 1),
        "tier_counts": dict(tiers),
        "n_classifier_training_examples": len(train),
        "n_classifier_labelled": len(unseeded),
        "categories_kept": sorted(keep),
        "categories_dropped_too_small": dropped,
        "cv_macro_f1": round(float(macro_f1), 4),
        "cv_micro_f1": round(float(micro_f1), 4),
        "tail_estimate": tail,
        "per_category": {
            c: {"support": int(report[c]["support"]),
                "precision": round(report[c]["precision"], 3),
                "recall": round(report[c]["recall"], 3),
                "f1": round(report[c]["f1-score"], 3)}
            for c in sorted(keep)
        },
        "final_distribution": dict(Counter(e["defect_category"] for e in out).most_common()),
        "final_distribution_seed_only": dict(
            Counter(e["defect_category"] for e in out
                    if e["label_source"] in ("prefix", "short")).most_common()),
        "classifier_confidence_deciles": [
            round(float(x), 3) for x in np.percentile(
                [e["label_confidence"] for e in out if e["label_source"] == "classifier"],
                [10, 25, 50, 75, 90])
        ] if unseeded else [],
    }
    with open(EVAL, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("per_category", "final_distribution",
                                   "final_distribution_seed_only")}, indent=2))
    print("\nper-category CV:")
    for c, m in summary["per_category"].items():
        print(f"  {c:28s} n={m['support']:5d}  P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f}")


if __name__ == "__main__":
    main()
