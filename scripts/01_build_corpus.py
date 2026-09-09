"""
01_build_corpus.py -- build the event-level investigation corpus.

Input :  data/raw/drug-enforcement-0001-of-0001.json.zip  (openFDA bulk export)
Output:  data/processed/events.jsonl
         results/corpus_stats.json

An openFDA drug enforcement *record* is a product line. A recall *event*
(event_id) can span hundreds of product lines that share one firm, one reason
for recall and one classification. A quality investigator reasons about events,
not product lines, so the retrieval unit here is the event. Aggregating also
removes the massive duplication that would otherwise dominate every metric.

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import json
import os
import re
import zipfile
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The programme keeps one hard-linked copy of every download under Papers/_shared
# and links it into each paper's data/raw/<source>/<dataset>/ tree; older runs of
# this paper kept a flat copy. Accept either, canonical path first.
RAW_CANDIDATES = [
    os.path.join(ROOT, "data", "raw", "openfda", "drug_enforcement",
                 "drug-enforcement-0001-of-0001.json.zip"),
    os.path.join(ROOT, "data", "raw", "drug-enforcement-0001-of-0001.json.zip"),
]
OUT = os.path.join(ROOT, "data", "processed", "events.jsonl")
STATS = os.path.join(ROOT, "results", "corpus_stats.json")

MAX_PRODUCTS_IN_TEXT = 8


def resolve_raw():
    for path in RAW_CANDIDATES:
        if os.path.exists(path):
            return path
    raise SystemExit(
        "openFDA drug enforcement export not found. Expected one of:\n  "
        + "\n  ".join(RAW_CANDIDATES)
        + "\nSee data/raw/MANIFEST.json for the source URL and checksum.")


def load_records():
    with zipfile.ZipFile(resolve_raw()) as z:
        name = [n for n in z.namelist() if n.endswith(".json")][0]
        payload = json.loads(z.read(name))
    return payload["results"], payload["meta"]


def clean(value):
    if value is None:
        return ""
    value = re.sub(r"\s+", " ", str(value)).strip()
    return "" if value.upper() in {"N/A", "NA", "UNKNOWN", "NONE"} else value


def modal(values):
    values = [v for v in values if v]
    if not values:
        return ""
    return Counter(values).most_common(1)[0][0]


def longest(values):
    values = [v for v in values if v]
    return max(values, key=len) if values else ""


def build_events(records):
    groups = defaultdict(list)
    for r in records:
        groups[r.get("event_id") or f"norec-{id(r)}"].append(r)

    events = []
    for event_id, rows in groups.items():
        products = []
        for r in rows:
            p = clean(r.get("product_description"))
            if p and p not in products:
                products.append(p)

        reasons = [clean(r.get("reason_for_recall")) for r in rows]
        reason = longest(reasons)

        dates = sorted(clean(r.get("recall_initiation_date")) for r in rows)
        dates = [d for d in dates if d]
        reports = sorted(clean(r.get("report_date")) for r in rows)
        reports = [d for d in reports if d]

        firm = modal([clean(r.get("recalling_firm")) for r in rows])
        city = modal([clean(r.get("city")) for r in rows])
        state = modal([clean(r.get("state")) for r in rows])
        country = modal([clean(r.get("country")) for r in rows])
        classification = modal([clean(r.get("classification")) for r in rows])
        status = modal([clean(r.get("status")) for r in rows])
        distribution = longest([clean(r.get("distribution_pattern")) for r in rows])
        initiation_mode = modal([clean(r.get("voluntary_mandated")) for r in rows])
        notification = modal([clean(r.get("initial_firm_notification")) for r in rows])
        recall_numbers = sorted({clean(r.get("recall_number")) for r in rows} - {""})

        shown = products[:MAX_PRODUCTS_IN_TEXT]
        more = len(products) - len(shown)
        product_block = "; ".join(shown) + (f"; and {more} further product presentations." if more > 0 else "")

        location = ", ".join(x for x in [city, state, country] if x)
        text = (
            f"Recalling firm: {firm}. Location: {location}. "
            f"Classification: {classification}. Status: {status}. "
            f"Recall initiated: {dates[0] if dates else 'unknown'}. "
            f"Reported: {reports[0] if reports else 'unknown'}. "
            f"Reason for recall: {reason} "
            f"Products affected ({len(products)} distinct presentations): {product_block} "
            f"Distribution: {distribution}. Initiation: {initiation_mode}. "
            f"Initial firm notification: {notification}."
        )

        events.append({
            "event_id": str(event_id),
            "firm": firm,
            "city": city,
            "state": state,
            "country": country,
            "classification": classification,
            "status": status,
            "reason_for_recall": reason,
            "n_records": len(rows),
            "n_products": len(products),
            "products": products[:50],
            "distribution_pattern": distribution,
            "voluntary_mandated": initiation_mode,
            "initial_firm_notification": notification,
            "recall_numbers": recall_numbers[:50],
            "recall_initiation_date": dates[0] if dates else "",
            "report_date": reports[0] if reports else "",
            "year": (reports[0][:4] if reports else (dates[0][:4] if dates else "")),
            "init_year": (dates[0][:4] if dates else (reports[0][:4] if reports else "")),
            "text": re.sub(r"\s+", " ", text).strip(),
        })

    events.sort(key=lambda e: (e["report_date"], e["event_id"]))
    return events


def main():
    records, meta = load_records()
    events = build_events(records)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    os.makedirs(os.path.dirname(STATS), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    lens = [len(e["text"].split()) for e in events]
    lens.sort()
    stats = {
        "raw_export_path": os.path.relpath(resolve_raw(), ROOT).replace("\\", "/"),
        "openfda_export_date": meta.get("last_updated"),
        "n_records": len(records),
        "n_events": len(events),
        "n_firms": len({e["firm"] for e in events}),
        "n_countries": len({e["country"] for e in events if e["country"]}),
        "records_per_event": {
            "mean": round(len(records) / len(events), 2),
            "median": sorted(e["n_records"] for e in events)[len(events) // 2],
            "max": max(e["n_records"] for e in events),
        },
        "classification": dict(Counter(e["classification"] for e in events).most_common()),
        "status": dict(Counter(e["status"] for e in events).most_common()),
        "year_range": [min(e["year"] for e in events if e["year"]),
                       max(e["year"] for e in events if e["year"])],
        "events_per_year": dict(sorted(Counter(e["year"] for e in events if e["year"]).items())),
        "doc_length_words": {
            "mean": round(sum(lens) / len(lens), 1),
            "median": lens[len(lens) // 2],
            "p95": lens[int(0.95 * len(lens))],
            "max": lens[-1],
        },
    }
    with open(STATS, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)

    print(json.dumps(stats, indent=2)[:2000])


if __name__ == "__main__":
    main()
