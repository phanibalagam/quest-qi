"""
08_verify_manuscript.py -- check the quantitative claims in the manuscript against the
JSON in results/.

Three kinds of check:
  check()   a value in results/ equals the constant this script was told to expect
  states()  the manuscript text actually contains the value read from results/
  in_text() the manuscript contains a string it is supposed to contain

What this catches: a number that was edited in one place and not the other, a stale
figure left behind by a re-run, a claim whose value drifted from its source.

What this does NOT catch, and no amount of extending it would: whether the right
statistic was chosen in the first place, whether a sentence describing the method is
true, whether a novelty claim survives a literature search, or whether the shipped PDF
was built from the current source. Those need a reader. A passing run here means the
manuscript is internally consistent with results/, and nothing stronger.

Exit code 1 if anything disagrees.

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = lambda n: json.load(open(os.path.join(ROOT, "results", n), encoding="utf-8"))

corpus = R("corpus_stats.json")
tax = R("taxonomy_eval.json")
bench = R("benchmark_stats.json")
base = R("retrieval_results.json")
prop = R("proposed_results.json")
paper = open(os.path.join(ROOT, "paper.md"), encoding="utf-8").read()

fails = []
counts = {"check": 0, "states": 0, "in_text": 0, "cross_artifact": 0}

# Bindings compare against a whitespace-normalised copy: the manuscript is
# reflowed from time to time, and a binding should fail when a NUMBER changes,
# not when a line break moves.
paper_flat = re.sub(r"\s+", " ", paper)


def flat(t):
    return re.sub(r"\s+", " ", t)


# --- the three manuscript surfaces ------------------------------------------
# THIS is the structural fix. Every earlier version of this script bound numbers
# to paper.md and nothing else, and the paper has four surfaces: paper.md, the
# generated .tex, the compiled PDF and results/. A correction that lands in the
# Markdown and not in the artifact a reader receives passes silently. That is not
# hypothetical: the macro-average column added to the retrieval table to fix a
# finding about selective reporting overflowed the text block by 151pt, so LaTeX
# TRUNCATED it, the column was absent from the shipped PDF, and this script
# reported "0 failure(s)". Numbers are now checked in all three.

TEX_PATH = os.path.join(ROOT, "paper_lncs.tex")
PDF_PATH = os.path.join(ROOT, "paper_lncs.pdf")

# T1-encoded llncs carries ligatures as single glyphs that pdftotext emits as C0
# control characters, so plain substring matching fails on words containing them.
# T1 glyphs that pdftotext returns as C0 control bytes on this build. 0x15 is the
# EN-DASH in body prose: it is NOT covered by the dash normaliser, which only
# handles the Unicode forms, so "0.151--0.193" arrives as "0.151\x150.193". The
# \d+\.\d+ regex happens to split that correctly, but a range whose dash vanished
# entirely would merge two numbers into one wrong one, so map it explicitly.
# Round 7, N47: this build also emits \x16 for the em-dash and \x10/\x11 for
# curly quotes, which were unnormalised -- so any binding phrase spanning an
# em-dash or a quoted string could never match in the PDF artifact. With N47's
# every-artifact requirement below, an unmatchable phrase is now a failure
# rather than a silent pass, which is why these have to be right.
T1_LIGATURES = {"\x1b": "ff", "\x1c": "fi", "\x1d": "fl",
                "\x1e": "ffi", "\x1f": "ffl", "\x15": "-",
                # Round 8, N54: \x10 and \x11 are the DOUBLE quotes, not the
                # single ones -- the PDF carries \x10outside the United
                # States\x11 where paper.md has "outside the United States".
                # Mapping them to an apostrophe left three incompatible forms
                # across the artifacts, which, now that a phrase missing from
                # any one artifact is a hard failure (N47), would make the first
                # binding written over a quoted sentence fail on two surfaces
                # for a reason that is purely an extraction artifact.
                "\x16": "-", "\x10": '"', "\x11": '"'}


def pdf_text(path):
    try:
        import subprocess
        out = subprocess.run(["pdftotext", path, "-"], capture_output=True, timeout=180)
        if out.returncode == 0:
            return out.stdout.decode("utf-8", "replace")
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        pass
    for mod in ("pypdf", "PyPDF2"):
        try:
            PdfReader = __import__(mod, fromlist=["PdfReader"]).PdfReader
        except ImportError:
            continue
        try:
            return "\n".join((pg.extract_text() or "") for pg in PdfReader(path).pages)
        except Exception:
            return None
    return None


def normalise_dashes(t):
    """En/em dashes and minus signs vary by surface; fold them to a hyphen.

    This is defensive: with lmodern+cmap the en-dash now extracts from the PDF,
    but it did not before, and a range that merges ("0.46--0.53" becoming
    "0.460.53") would turn two numbers into one wrong one without any check
    noticing. Folding them means a range compares equal whichever surface it
    came from, and a range that has LOST its dash no longer matches.
    """
    for _d in ("\u2013", "\u2014", "\u2212", "\x15", "--"):
        t = t.replace(_d, "-")
    return t


def strip_markup(t):
    """Reduce Markdown or LaTeX to comparable running text.

    Emphasis is expressed three different ways across the surfaces (**x**,
    \\textbf{x}, and plain x in the PDF), so a value must be compared without it.
    Numbers, which is what these bindings are about, survive all three unchanged.
    """
    for c, s in T1_LIGATURES.items():
        t = t.replace(c, s)
    t = re.sub(r"\\(?:textbf|textit|texttt|emph|mathbf)\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\\[a-zA-Z]+\s*", " ", t)          # remaining control sequences
    # Round 9: LaTeX escapes the five specials, so the .tex carries "14.4\%" and
    # "dense\_embeddings" where paper.md and the PDF carry "14.4%" and
    # "dense_embeddings". The control-sequence rule above cannot remove them --
    # none of them is alphabetic -- so a binding phrase or value containing one
    # could never match the .tex artifact. Same class as N54's quotes.
    for _e, _p in (("\\%", "%"), ("\\&", "&"), ("\\#", "#"),
                   ("\\_", "_"), ("\\$", "$")):
        t = t.replace(_e, _p)
    t = t.replace("**", "").replace("*", "").replace("`", "")
    # Cell separators differ by surface: "|" in Markdown, "&" in LaTeX, plain
    # whitespace in extracted PDF text. Normalise all three to whitespace so a
    # table row reads the same way whichever artifact it came from.
    t = t.replace("{", "").replace("}", "").replace("&", " ").replace("|", " ")
    t = normalise_dashes(t)
    # Round 8, N54: the three surfaces spell the same quotation three ways --
    # Markdown "x", LaTeX ``x'', extracted PDF \x10x\x11 (folded above). Fold
    # every form to one so a binding phrase can span a quoted string.
    for _q in ("``", "''", "\u201c", "\u201d", "\u2018", "\u2019"):
        t = t.replace(_q, '"')
    return re.sub(r"\s+", " ", t)


ARTIFACTS = {"paper.md": strip_markup(paper)}
if os.path.exists(TEX_PATH):
    ARTIFACTS["paper_lncs.tex"] = strip_markup(open(TEX_PATH, encoding="utf-8").read())
else:
    fails.append("paper_lncs.tex is missing; run scripts/10_build_latex.py")
if os.path.exists(PDF_PATH):
    _pdf_raw = pdf_text(PDF_PATH)
    if _pdf_raw is None:
        fails.append("cannot extract text from paper_lncs.pdf (install pdftotext or "
                     "pypdf); the shipped PDF is UNVERIFIED")
    else:
        # Round 7: LNCS puts a running head and a page number between every
        # pair of pages, so a sentence spanning a page break extracts with
        # "When the Benchmark Answers Itself 17" wedged into the middle of it.
        # Any binding whose phrase happens to straddle a break could then never
        # match -- which, with N47's every-artifact requirement, is a failure
        # rather than a silent pass. Drop the furniture, keep the prose.
        def _strip_running_heads(t):
            # Round 8, N55: the first version dropped ANY bare integer on its own
            # line, which removed 57 lines of which only 25 were folios -- every
            # section number, both figures' bar labels and axis ticks, and a pool
            # size from Table 5. Fourteen integers that exist in the paper became
            # invisible to the PDF artifact. A folio is only a folio when it sits
            # next to a page boundary or a running head, so require that.
            # Round 9, M32: adjacency alone both under-stripped (two folios sat
            # next to a figure bar label instead of a running head) and could
            # over-strip (a legitimate bare integer landing beside a page
            # boundary). A folio is not merely a number near a page break: it is
            # THE number of the page it sits on. Count pages by form feed and
            # require the value to match, which makes both errors impossible.
            _lines = t.split("\n")
            _head = re.compile(r"^\s*(?:P\.\s*K\.\s*Balagam"
                               r"|When the Benchmark Answers Itself)\s*$")
            # Round 10, N69: the value test alone is necessary but not
            # sufficient -- a table cell "17" on page 17, or section 8 once it
            # reflows onto page 8, matches it. A folio also sits at a page
            # boundary, so require BOTH: the value equals the page number AND a
            # form feed or a running head is within three non-blank lines. The
            # two conditions together are what a folio is.
            _keep, _page = [], 1
            for _i, _ln in enumerate(_lines):
                _st = _ln.strip()
                if _head.match(_ln):
                    if "\f" in _ln:
                        _page += 1
                    continue                       # a running head
                if "\f" in _ln:
                    _page += 1
                if re.fullmatch(r"\d{1,3}", _st) and int(_st) == _page:
                    _seen = 0
                    # On a verso page pdftotext puts the form feed on the folio's
                    # own line ("\x0c22"), so the line itself can be the boundary.
                    _at_boundary = "\f" in _ln
                    for _j in list(range(_i - 1, -1, -1))[:12] + \
                            list(range(_i + 1, len(_lines)))[:12]:
                        if not _lines[_j].strip():
                            continue
                        _seen += 1
                        if "\f" in _lines[_j] or _head.match(_lines[_j]):
                            _at_boundary = True
                            break
                        if _seen >= 3:
                            break
                    if _at_boundary:
                        continue                   # this page's own folio
                _keep.append(_ln)
            return "\n".join(_keep)
        _pdf_raw = _strip_running_heads(_pdf_raw)
        ARTIFACTS["paper_lncs.pdf"] = strip_markup(_pdf_raw)
else:
    fails.append("paper_lncs.pdf is missing; build it before verifying")


def in_all_artifacts(claim, value):
    """A value the manuscript states must reach every surface a reader can open."""
    counts["cross_artifact"] += 1
    needle = strip_markup(str(value)).strip()
    for name, body in ARTIFACTS.items():
        if needle not in body:
            fails.append(f"{claim}: {needle!r} is in results/ and paper.md but NOT in "
                         f"{name} -- a correction that did not reach the artifact")


def check(claim, actual, expected, tol=0.0005):
    counts["check"] += 1
    ok = (abs(actual - expected) <= tol) if isinstance(expected, float) else (actual == expected)
    if not ok:
        fails.append(f"{claim}: manuscript {expected!r} vs results {actual!r}")


def in_text(s):
    counts["in_text"] += 1
    if flat(s) not in paper_flat:
        fails.append(f"string missing from paper.md: {s!r}")


# --- corpus -----------------------------------------------------------------
check("n records", corpus["n_records"], 17899)
check("n events", corpus["n_events"], 4652)
check("n firms", corpus["n_firms"], 1655)
check("n countries", corpus["n_countries"], 24)
check("records/event mean", corpus["records_per_event"]["mean"], 3.85)
check("records/event max", corpus["records_per_event"]["max"], 470)
check("class II", corpus["classification"]["Class II"], 2911)
check("class III", corpus["classification"]["Class III"], 1142)
check("class I", corpus["classification"]["Class I"], 598)
check("doc words mean", round(corpus["doc_length_words"]["mean"]), 117)
check("doc words median", corpus["doc_length_words"]["median"], 93)
check("doc words p95", corpus["doc_length_words"]["p95"], 263)
check("export date", corpus["openfda_export_date"], "2026-08-27")

# --- taxonomy ---------------------------------------------------------------
check("rule coverage", tax["rule_coverage_pct"], 96.1)
check("prefix tier", tax["tier_counts"]["prefix"], 3615)
check("short tier", tax["tier_counts"]["short"], 855)
check("classifier tier", tax["tier_counts"]["classifier"], 182)
check("classifier tier pct", round(100 * tax["tier_counts"]["classifier"] / tax["n_events"], 1), 3.9)
check("clf training examples", tax["n_classifier_training_examples"], 3559)
check("cv macro f1", tax["cv_macro_f1"], 0.717, tol=0.0006)
check("cv micro f1", tax["cv_micro_f1"], 0.783, tol=0.0006)
check("n categories", len(tax["final_distribution"]), 15)
t = tax["tail_estimate"]
check("rule-free n", t["n_rule_free_remainders"], 1266)
check("pct still matching a rule", t["pct_remainders_still_matching_a_rule"], 64.4)
check("pct echoing own rule", t["pct_remainders_echoing_own_rule"], 34.1)
check("rule-free macro f1", t["cv_macro_f1_rule_free_subset"], 0.609, tol=0.0006)
check("rule-free micro f1", t["cv_micro_f1_rule_free_subset"], 0.728, tol=0.0006)
check("overstatement", round(tax["cv_macro_f1"] - t["cv_macro_f1_rule_free_subset"], 2), 0.11)
for cat, f1 in [("UNAPPROVED_MARKETING", 0.93), ("LABELING_PACKAGING", 0.92),
                ("IMPURITY_DEGRADATION", 0.86), ("STABILITY_EXPIRY", 0.47),
                ("CROSS_CONTAMINATION", 0.56)]:
    check(f"f1 {cat}", round(tax["per_category"][cat]["f1"], 2), f1)

# --- benchmark --------------------------------------------------------------
check("n queries", bench["n_queries"], 171)
check("gold pairs", bench["total_gold_pairs"], 3646)
check("distinct gold events", bench["distinct_gold_events"], 2185)
check("gold median", bench["gold_set_size"]["median"], 15)
check("gold mean", bench["gold_set_size"]["mean"], 21.3)
check("gold max", bench["gold_set_size"]["max"], 71)
check("dev", bench["split_counts"]["dev"], 52)
check("test", bench["split_counts"]["test"], 119)
for fam, n in [("A_defect_form", 31), ("B_defect_severity", 18), ("C_firm_history", 31),
               ("D_defect_period", 25), ("E_defect_geography", 10), ("F_site_country", 4)]:
    check(f"test size {fam}", bench["split_by_family"][fam]["test"], n)

# --- Table 2, text-only retrieval ----------------------------------------------------------------
T1 = {"w2v": (0.147, 0.244, 0.286, 0.103, 0.159, 0.245),
      "bm25": (0.221, 0.342, 0.389, 0.164, 0.236, 0.333),
      "tfidf": (0.241, 0.362, 0.416, 0.166, 0.264, 0.364),
      "lsa": (0.257, 0.411, 0.484, 0.208, 0.299, 0.412),
      "hybrid_rrf": (0.260, 0.396, 0.457, 0.211, 0.302, 0.410)}
KEYS = ["recall@10", "recall@50", "recall@100", "precision@10", "ndcg@10", "mrr"]
for sysname, vals in T1.items():
    for k, v in zip(KEYS, vals):
        check(f"T1 {sysname} {k}", round(base["summary"][sysname][k]["mean"], 3), v, tol=0.0006)

c = base["contrasts_vs_hybrid"]
check("hybrid-bm25 diff", round(c["hybrid_rrf - bm25"]["mean_diff_ndcg@10"], 3), 0.066, tol=0.0006)
check("hybrid-tfidf diff", round(c["hybrid_rrf - tfidf"]["mean_diff_ndcg@10"], 3), 0.039, tol=0.0006)
check("hybrid-lsa diff", round(c["hybrid_rrf - lsa"]["mean_diff_ndcg@10"], 3), 0.003, tol=0.0006)
check("hybrid-lsa holm", c["hybrid_rrf - lsa"]["p_holm"], 1.0, tol=0.001)
check("hybrid-tfidf holm", c["hybrid_rrf - tfidf"]["p_holm"], 0.099, tol=0.001)
check("n contrasts in 04", len(c), 7)
check("hybrid-w2v diff", round(c["hybrid_rrf - w2v"]["mean_diff_ndcg@10"], 3), 0.143, tol=0.0011)
check("n clusters", base["n_bootstrap_clusters"], 50)
# Round 9, M36: Section 5.2's alternative anchoring quoted 0.182, 79% and 81%
# with only 0.143 bound. All four are arithmetic over Table 2, so all four are
# recomputed here rather than trusted.
_MINILM = base["summary"]["minilm"]["ndcg@10"]["mean"]
_W2V = base["summary"]["w2v"]["ndcg@10"]["mean"]
_RRF = base["summary"]["hybrid_rrf"]["ndcg@10"]["mean"]
_DENSE = base["summary"]["hybrid_rrf_dense"]["ndcg@10"]["mean"]
check("span above word2vec", round(_DENSE - _W2V, 3), 0.182, tol=0.0011)
check("share crossed by corpus-trained channels, word2vec-anchored (%)",
      round(100 * (_RRF - _W2V) / (_DENSE - _W2V)), 79)
check("share crossed by corpus-trained channels, MiniLM-anchored (%)",
      round(100 * (_RRF - _MINILM) / (_DENSE - _MINILM)), 81)
# Round 10, N64: the three checks above compare a recomputed value against a
# LITERAL TYPED HERE. They never read paper.md, so the manuscript could state two
# wrong percentages and stay green -- which the reviewer demonstrated by editing
# "79% rather than 81%" to "78% rather than 82%" for 0 failures. A check() proves
# the arithmetic; only a states() or in_text() proves the paper says it.
_SPAN_W2V = _DENSE - _W2V
_PCT_W2V = round(100 * (_RRF - _W2V) / (_DENSE - _W2V))
_PCT_MINILM = round(100 * (_RRF - _MINILM) / (_DENSE - _MINILM))
in_text(f"{_PCT_W2V}% rather than {_PCT_MINILM}%")

# --- Section 5.2 by family --------------------------------------------------
fam = base["by_family"]["hybrid_rrf"]
check("family C", round(fam["C_firm_history"]["ndcg@10"], 3), 0.759, tol=0.0006)
check("family F", round(fam["F_site_country"]["ndcg@10"], 3), 0.506, tol=0.0006)
check("family A", round(fam["A_defect_form"]["ndcg@10"], 3), 0.162, tol=0.0006)
check("family B", round(fam["B_defect_severity"]["ndcg@10"], 3), 0.135, tol=0.0006)
check("family D", round(fam["D_defect_period"]["ndcg@10"], 3), 0.121, tol=0.0006)
check("family E", round(fam["E_defect_geography"]["ndcg@10"], 3), 0.000)
check("doc-repr spread",
      round(base["summary"]["hybrid_rrf"]["ndcg@10"]["mean"]
            - base["summary"]["w2v"]["ndcg@10"]["mean"], 3), 0.143, tol=0.0011)

# --- Table 3 (non-circular query understanding) -----------------------------
T2 = {"hybrid_rrf": (0.260, 0.396, 0.211, 0.302, 0.410),
      "qir_clf": (0.259, 0.399, 0.210, 0.302, 0.409),
      "qir_centroid": (0.265, 0.448, 0.226, 0.317, 0.425)}
K2 = ["recall@10", "recall@50", "precision@10", "ndcg@10", "mrr"]
for sysname, vals in T2.items():
    for k, v in zip(K2, vals):
        check(f"T2 {sysname} {k}", round(prop["summary"][sysname][k]["mean"], 3), v, tol=0.0006)

pc = prop["contrasts_vs_hybrid"]
cen = pc["qir_centroid - hybrid_rrf"]
check("centroid delta", round(cen["mean_diff_ndcg@10"], 3), 0.014, tol=0.0006)
check("centroid CI lo", round(cen["ci95_cluster"][0], 3), -0.005, tol=0.0011)
check("centroid CI hi", round(cen["ci95_cluster"][1], 3), 0.033, tol=0.0011)
check("centroid holm", cen["p_holm"], 0.304, tol=0.001)
clf = pc["qir_clf - hybrid_rrf"]
check("clf delta", round(clf["mean_diff_ndcg@10"], 3), -0.001, tol=0.0006)
check("clf holm", clf["p_holm"], 0.834, tol=0.001)

qa = prop["query_category_top1_accuracy"]
check("clf top1", round(100 * qa["classifier_zero_shot_test"]), 31)
check("centroid top1", round(100 * qa["lsa_centroid_test"], 1), 58.3)
check("chance", round(100 * qa["chance"], 1), 6.7)
check("category accuracy gap points",
      round(100 * (qa["lsa_centroid_test"] - qa["classifier_zero_shot_test"])), 27)
lam = prop["lambda_selection"]["selected_per_system"]
for k, v in [("qir_clf", 0.25), ("qir_centroid", 2.0), ("qir_oracle", 2.0),
             ("gold_additive_control", 4.0),
             ("qir_clf_slots", 4.0), ("qir_centroid_slots", 8.0), ("qir_oracle_slots", 4.0)]:
    check(f"lambda {k}", lam[k], v)

# --- Table 4 (circularity) --------------------------------------------------
T3 = {"slots_only": 0.423, "prefilter_hybrid": 0.464, "qir_centroid_slots": 0.579,
      "qir_oracle_slots": 0.757, "gold_downweight_control": 0.581,
      "gold_additive_control": 0.823, "gold_lookup_ceiling": 1.000}
for sysname, v in T3.items():
    check(f"T3 {sysname}", round(prop["summary"][sysname]["ndcg@10"]["mean"], 3), v, tol=0.0006)
T3D = {"slots_only": (0.121, 0.074, 0.166), "prefilter_hybrid": (0.162, 0.101, 0.221),
       "qir_centroid_slots": (0.277, 0.145, 0.392), "qir_oracle_slots": (0.454, 0.340, 0.540),
       "gold_downweight_control": (0.278, 0.220, 0.336),
       "gold_additive_control": (0.520, 0.430, 0.594),
       "gold_lookup_ceiling": (0.698, 0.580, 0.775)}
for sysname, (d, lo, hi) in T3D.items():
    e = pc[f"{sysname} - hybrid_rrf"]
    check(f"T3 delta {sysname}", round(e["mean_diff_ndcg@10"], 3), d, tol=0.0006)
    check(f"T3 CI lo {sysname}", round(e["ci95_cluster"][0], 3), lo, tol=0.0011)
    check(f"T3 CI hi {sysname}", round(e["ci95_cluster"][1], 3), hi, tol=0.0011)
check("n contrasts in 05", len(pc), 11)

rec = prop["predicate_reconstruction"]
check("recovered fraction", round(100 * rec["fraction_of_matched_control_recovered"]), 53)
check("matched control", rec["matched_additive_gold_control"], 0.823, tol=0.0006)
check("downweight control", rec["downweight_gold_control_matched_to_soft_filter"], 0.581, tol=0.0006)
check("literal ceiling", rec["literal_gold_lookup_ceiling"], 1.0)
check("recovered fraction arithmetic",
      round((rec["proposed_centroid_plus_metadata"] - rec["text_only"])
            / (rec["matched_additive_gold_control"] - rec["text_only"]), 4),
      rec["fraction_of_matched_control_recovered"], tol=0.0002)

# --- Section 5.5 ------------------------------------------------------------
check("oracle category", round(prop["summary"]["qir_oracle"]["ndcg@10"]["mean"], 3), 0.410, tol=0.0006)
check("oracle category delta",
      round(pc["qir_oracle - hybrid_rrf"]["mean_diff_ndcg@10"], 3), 0.107, tol=0.0011)

check("family E lsa", round(base["by_family"]["lsa"]["E_defect_geography"]["ndcg@10"], 3),
      0.013, tol=0.0011)
ev = {json.loads(l)["event_id"]: json.loads(l)
      for l in open(os.path.join(ROOT, "data", "processed", "events_labeled.jsonl"),
                    encoding="utf-8")}
qs = [json.loads(l) for l in open(os.path.join(ROOT, "data", "processed", "benchmark.jsonl"),
                                  encoding="utf-8")]
FORM = {"sterile injectable": r"\b(injection|injectable|vial|ampule|ampoule|infusion|syringe|iv\b|intravenous)",
        "oral solid": r"\b(tablet|capsule|caplet|softgel)",
        "ophthalmic": r"\b(ophthalmic|eye drop|eye-drop|intraocular)",
        "topical": r"\b(cream|ointment|gel\b|lotion|topical|transdermal)",
        "oral liquid": r"\b(oral solution|oral suspension|syrup|elixir|oral liquid)"}
tot = inv = 0
for q in qs:
    if q["family"] != "A_defect_form" or q["split"] != "test":
        continue
    pat = FORM[q["predicate"]["dosage_form"]]
    for g in q["gold_event_ids"]:
        tot += 1
        shown = " ".join(ev[g]["products"][:8]).lower()
        if not re.search(pat, shown):
            inv += 1
check("family A invisible gold pairs pct", round(100 * inv / tot, 1), 3.1, tol=0.06)

# --- the manuscript must contain the headline numbers -----------------------
def states(claim, value, fmt="{:.3f}", context=None, all_artifacts=True):
    """Assert the manuscript contains `value` as the manuscript renders it.

    The exact formatted string is checked against paper.md, which is the tight
    binding. The bare value is then checked against the .tex and the PDF too,
    because a number can be correct in the Markdown and absent from the artifact
    (see the note on ARTIFACTS above). Pass all_artifacts=False only for a value
    that legitimately exists in one surface alone.
    """
    counts["states"] += 1
    # Round 9, M34: f3() had zero call sites, so its docstring asserted a
    # rounding convention the script did not apply -- documentation describing
    # behaviour that does not exist, which is this round's theme. It now has one.
    #
    # It is used to ACCEPT rather than to impose. Several stored values are exact
    # ties at the third decimal (0.2995, 0.3025, 0.2835, 0.4165, 0.4935) because
    # the scripts store four decimals, and at a tie both roundings are correct --
    # the same position the Table 2 binding takes by comparing numerically. Doing
    # otherwise here would have forced 0.302 to 0.303 in sixteen places to settle
    # a house style, which is not what a binding is for.
    txt = value if isinstance(value, str) else fmt.format(value)
    _alt = None
    if not isinstance(value, str) and fmt == "{:.3f}":
        _alt = f3(value)
        if _alt == txt:
            _alt = None
    _hay = paper_flat if context is None else flat(context)
    if flat(txt) not in _hay:
        if _alt and flat(_alt) in _hay:
            # Round 10, M39: this used to be an elif chain, so taking the
            # other-rounding branch skipped in_all_artifacts() entirely. The
            # accept-either path must still check that the value the paper
            # actually uses reaches every artifact -- that is the whole point.
            txt = _alt
        else:
            fails.append(f"paper.md does not state {claim} as {txt!r}"
                         + (f" (or {_alt!r}, the other correct rounding of this tie)"
                            if _alt else "") + " (from results/)")
            return
    if all_artifacts and context is None:
        in_all_artifacts(claim, txt)


def f3(x):
    """Three decimals, rounded half-up.

    Python rounds half-to-even, so 0.2835 formats as "0.283" while the manuscript
    (and every human) writes "0.284". Binding on the wrong convention produces a
    failure that looks like a data error and is not one.
    """
    from decimal import Decimal, ROUND_HALF_UP
    return str(Decimal(repr(float(x))).quantize(Decimal("0.001"),
                                                rounding=ROUND_HALF_UP))


def ci_str(ci, fmt="{:.3f}"):
    lo, hi = ci
    return "[" + fmt.format(lo).replace("-", "\u2212") + ", " + fmt.format(hi) + "]"


# --- Table 2 (text-only retrieval), bound to results/ numerically ---------------------------------
# These rows used to be hard-coded literals, which made the binding worthless for
# its actual purpose: if the macro-average were computed differently, the paper
# and the verifier would carry the same stale constant and the run would stay
# green. Each row is now PARSED out of the manuscript and its cells compared
# numerically to retrieval_results.json.
#
# Numeric comparison rather than string matching is deliberate. Several stored
# values are exact ties at the third decimal (0.2995, 0.3025, 0.2835, 0.4165,
# 0.4935), because the scripts store four decimals. At a tie both "0.302" and
# "0.303" are correct, so a string binding would enforce a rounding house style
# instead of catching a changed number. The tolerance below is half a display
# unit: it fails on any real change and passes on either rounding.
RETRIEVAL_ROWS = [
    ("MiniLM (pretrained)", "minilm"),
    ("word2vec (corpus-trained)", "w2v"),
    ("BM25", "bm25"),
    ("TF-IDF", "tfidf"),
    ("BGE-base (pretrained)", "bge_base"),
    ("LSA (corpus-trained)", "lsa"),
    ("Hybrid RRF (BM25 + LSA)", "hybrid_rrf"),
    ("Hybrid RRF + BGE", "hybrid_rrf_dense"),
]
RETRIEVAL_COLS = ["recall@10", "recall@50", "recall@100", "precision@10",
               "ndcg@10", "ci_lo", "ci_hi", "macro", "mrr"]

# Anchor on the table itself. A bare label search finds the first mention in the
# prose ("BM25", "TF-IDF") rather than the table row.
RETRIEVAL_BLOCK = {}
for _name, _body in ARTIFACTS.items():
    _h = _body.find("System R@10 R@50 R@100")
    if _h < 0:
        _h = _body.find("System")
    _end = _body.find("Text-only retrieval, 119 held-out", _h) if _h >= 0 else -1
    if _h >= 0:
        RETRIEVAL_BLOCK[_name] = _body[_h:_h + 1400 if _end < 0 else max(_end, _h + 900)]
    else:
        fails.append(f"retrieval-table header not found in {_name}")

for _label, _key in RETRIEVAL_ROWS:
    _d = base["summary"][_key]
    _n = _d["ndcg@10"]
    # Recompute the macro from by_family rather than trusting the summary field,
    # so a disagreement between the two surfaces here instead of silently.
    _fams = sorted(base["by_family"][_key])
    _macro = sum(base["by_family"][_key][_f]["ndcg@10"] for _f in _fams) / len(_fams)
    if abs(_macro - _n["macro_over_families"]) > 0.0006:
        fails.append(f"{_key}: summary macro_over_families {_n['macro_over_families']} "
                     f"disagrees with the mean over by_family ({_macro:.4f})")
    _want = [_d["recall@10"]["mean"], _d["recall@50"]["mean"], _d["recall@100"]["mean"],
             _d["precision@10"]["mean"], _n["mean"], _n["ci95_cluster"][0],
             _n["ci95_cluster"][1], _n["macro_over_families"], _d["mrr"]["mean"]]

    # Locate the row in each surface and read its numbers back out. The three
    # surfaces separate cells differently (| in Markdown, & in LaTeX, whitespace
    # in extracted PDF text), so match on the label and take the numbers that
    # follow it on that line.
    for _name, _body in ARTIFACTS.items():
        counts["cross_artifact"] += 1
        if _name == "paper_lncs.pdf":
            # pdftotext emits a resized table column-major, so a row's numbers are
            # not adjacent to its label. The .tex-to-PDF decimal diff below covers
            # the PDF; here we only require the label to have survived.
            if strip_markup(_label) not in _body:  # PDF: label presence only
                fails.append(f"retrieval table: row {_label!r} is missing from {_name}")
            continue
        _blk = RETRIEVAL_BLOCK.get(_name, "")
        _m = re.search(re.escape(strip_markup(_label)) + r"(.{0,180})", _blk)
        if not _m:
            fails.append(f"retrieval table: row {_label!r} is missing from {_name}")
            continue
        _got = [float(x) for x in re.findall(r"\d+\.\d+", _m.group(1))][:len(_want)]
        if len(_got) < len(_want):
            fails.append(f"retrieval table in {_name}: row {_label!r} has {len(_got)} numeric "
                         f"cells, expected {len(_want)}. A column is missing from this "
                         f"artifact -- if this is the PDF's source, the table is "
                         f"overflowing and LaTeX is truncating it.")
            continue
        for _col, _w, _g in zip(RETRIEVAL_COLS, _want, _got):
            if abs(_w - _g) > 0.0006:
                fails.append(f"retrieval table in {_name}: row {_label!r} column {_col} reads "
                             f"{_g} but results/ says {_w}")

for frag in [
    "reaches 0.193,\n0.151, 0.161 and **0.024**",
    "BGE, a pretrained\nretrieval encoder, reaches 0.010",
    "The point estimate moves from +0.014 to +0.020",
    "Neither encoder family dominates, and the aggregate decides which one looks better",
    "Under the macro-average\nover families the ordering reverses: BGE 0.296 against 0.280",
    "`C_firm_history`, where it reaches 0.759 against BGE's 0.658",
    "0.096\nafter Holm correction within the pair",
    "0.796 and 0.735",
    "spread across document representations here is 0.205 nDCG@10",
    "| *Control:* gold membership, down-weight form | 0.581 | +0.278 [0.220, 0.336] |",
    "| Centroid prior + metadata filter | 0.579 | +0.277 [0.145, 0.392] |",
    "| Hard metadata prefilter + RRF, no defect prior | 0.464 | +0.162 [0.101, 0.221] |",
    "| Soft metadata filter, no defect prior | 0.423 | +0.121 [0.074, 0.166] |",
    "**0.717\nmacro F1**",
    "λ selected on dev\nis 0.25",
    "cluster bootstrap over 50 clusters",
    "2,000 cluster-bootstrap resamples over 50\nclusters",
    "**0.609** (micro 0.728)",
    "**4,652 events**",
    "**171 queries**",
    "**52 dev and 119 test**",
    "**96.1%**",
    "31% top-1 category accuracy",
    "58.3%\ntop-1 accuracy",
    "recovers 53% of what\npredicate reconstruction is worth",
    "the fuller lesson is that a gold-membership\ncontrol measures the reachable candidate set as well as the scoring form",
    "reaches\n**0.823**, and simply ranking the gold set first reaches **1.000**",
    "| *Ceiling:* gold ranked first | 1.000 | +0.698 [0.580, 0.775] |",
    "| *Control:* gold membership, additive form | 0.823 | +0.520 [0.430, 0.594] |",
    "| Oracle defect category + metadata filter | 0.757 | +0.454 [0.340, 0.540] |",
    "reaches 0.410 nDCG@10",
]:
    in_text(frag)

# --- pretrained encoders ----------------------------------------------------
dm = base.get("dense_encoders")
if dm is None:
    fails.append("results/retrieval_results.json has no dense_encoders block: "
                 "run scripts/09_dense_encode.py, then 04 and 05")
else:
    check("BGE repo", dm["models"]["bge_base"]["repo"], "BAAI/bge-base-en-v1.5")
    check("BGE dim", dm["models"]["bge_base"]["dim"], 768)
    check("BGE max seq", dm["models"]["bge_base"]["max_seq_length"], 512)
    check("MiniLM repo", dm["models"]["minilm"]["repo"],
          "sentence-transformers/all-MiniLM-L6-v2")
    check("MiniLM dim", dm["models"]["minilm"]["dim"], 384)
    for k in ("bge_base", "minilm"):
        if not dm["models"][k].get("revision"):
            fails.append(f"dense manifest has no pinned commit hash for {k}")
    check("fusion uses BGE", base["timings"]["dense_encoder_used_in_fusion"], "bge_base")
    for nm, key in [("BGE nDCG", "bge_base"), ("MiniLM nDCG", "minilm"),
                    ("dense fusion nDCG", "hybrid_rrf_dense")]:
        if key not in base["summary"]:
            fails.append(f"{key} missing from retrieval_results.json summary")
    check("family E, BGE", base["by_family"]["bge_base"]["E_defect_geography"]["ndcg@10"],
          0.0095, tol=0.0006)
    check("family E, dense fusion",
          base["by_family"]["hybrid_rrf_dense"]["E_defect_geography"]["ndcg@10"],
          0.0236, tol=0.0006)
    check("family C, dense fusion",
          base["by_family"]["hybrid_rrf_dense"]["C_firm_history"]["ndcg@10"], 0.7956)
    check("family F, dense fusion",
          base["by_family"]["hybrid_rrf_dense"]["F_site_country"]["ndcg@10"], 0.7349)
    _spread = (base["summary"]["hybrid_rrf_dense"]["ndcg@10"]["mean"]
               - base["summary"]["minilm"]["ndcg@10"]["mean"])
    check("representation spread (recomputed)", round(_spread, 3), 0.205)

rob = prop["predicate_reconstruction"].get("dense_base_robustness")
if rob is None:
    fails.append("proposed_results.json has no dense_base_robustness block")
else:
    check("dense fusion in 05 matches 04", rob["summary"]["hybrid_rrf_dense"]["ndcg@10"],
          base["summary"]["hybrid_rrf_dense"]["ndcg@10"]["mean"])
    rc = rob["contrasts"]["qir_centroid_dense - hybrid_rrf_dense"]
    check("centroid on dense base", rc["mean_diff_ndcg@10"], 0.0203)
    check("centroid on dense base, raw p", rc["p_two_sided_raw"], 0.048, tol=0.001)
    check("centroid on dense base, Holm p", rc["p_holm_within_robustness_pair"],
          0.096, tol=0.001)
    check("classifier on dense base",
          rob["contrasts"]["qir_clf_dense - hybrid_rrf_dense"]["mean_diff_ndcg@10"],
          0.0006)
    # the paper must not report the robustness effect as significant
    if rc["p_holm_within_robustness_pair"] < 0.05:
        fails.append("the dense-base robustness contrast is now significant after "
                     "Holm; Section 5.3 states that it is not")

# --- manuscript <-> results binding -----------------------------------------
# check() above compares results/ against constants typed into this script: it
# detects a changed pipeline but not a manuscript that disagrees with results/.
# states() closes that gap -- it formats the value straight out of results/ and
# requires that exact string to appear in paper.md, so a number can only drift in
# both places at once.

bsum, psum = base["summary"], prop["summary"]
recon = prop["predicate_reconstruction"]

# Table 2 / Table 3 / Table 4 headline means must appear verbatim in the paper.
for name, key, src in [
        ("word2vec nDCG", "w2v", bsum), ("BM25 nDCG", "bm25", bsum),
        ("TF-IDF nDCG", "tfidf", bsum), ("LSA nDCG", "lsa", bsum),
        ("Hybrid RRF nDCG", "hybrid_rrf", bsum),
        ("BGE nDCG", "bge_base", bsum), ("MiniLM nDCG", "minilm", bsum),
        ("dense fusion nDCG", "hybrid_rrf_dense", bsum),
        ("classifier prior nDCG", "qir_clf", psum),
        ("centroid prior nDCG", "qir_centroid", psum),
        ("soft filter nDCG", "slots_only", psum),
        ("prefilter nDCG", "prefilter_hybrid", psum),
        ("centroid+metadata nDCG", "qir_centroid_slots", psum),
        ("oracle+metadata nDCG", "qir_oracle_slots", psum),
        ("oracle prior nDCG", "qir_oracle", psum),
        ("down-weight control nDCG", "gold_downweight_control", psum),
        ("additive control nDCG", "gold_additive_control", psum),
        ("gold lookup ceiling nDCG", "gold_lookup_ceiling", psum)]:
    states(name, src[key]["ndcg@10"]["mean"])

# Every confidence interval quoted in prose, rendered from results/.
for name, cs in [
        ("hybrid-bm25 CI", base["contrasts_vs_hybrid"]["hybrid_rrf - bm25"]["ci95_cluster"]),
        ("hybrid-tfidf CI", base["contrasts_vs_hybrid"]["hybrid_rrf - tfidf"]["ci95_cluster"]),
        ("hybrid-lsa CI", base["contrasts_vs_hybrid"]["hybrid_rrf - lsa"]["ci95_cluster"]),
        ("centroid prior CI", prop["contrasts_vs_hybrid"]["qir_centroid - hybrid_rrf"]["ci95_cluster"]),
        ("classifier prior CI", prop["contrasts_vs_hybrid"]["qir_clf - hybrid_rrf"]["ci95_cluster"])]:
    txt = ci_str(cs)
    if txt not in paper:
        fails.append(f"paper.md does not state {name} as {txt} (from results/)")

# Section 5.4: the recovered fraction, its interval, the mechanism-exact pair and
# every row of the pool-sensitivity table.
# Round 10, N64 (deferred to here because states() is defined above this point):
# the paper must actually contain the span, not merely agree with it arithmetically.
states("span above word2vec (Section 5.2)", _SPAN_W2V, "{:.3f}")

states("recovered fraction", recon["fraction_of_matched_control_recovered"], "{:.2f}")
lo, hi = recon["fraction_recovered_ci95_cluster"]
if f"[{lo:.2f}, {hi:.2f}]" not in paper:
    fails.append(f"paper.md does not state the recovered-fraction CI as "
                 f"[{lo:.2f}, {hi:.2f}] (from results/)")
mx = recon["mechanism_exact_pair"]
states("mechanism-exact fraction", mx["fraction_recovered"], "**{:.3f}**")
mlo, mhi = mx["ci95_cluster"]
if f"[{mlo:.2f}, {mhi:.2f}]" not in paper:
    fails.append(f"paper.md does not state the mechanism-exact CI as "
                 f"[{mlo:.2f}, {mhi:.2f}] (from results/)")
for row in recon["pool_sensitivity"]["rows"]:
    line = (f"| {row['pool']:,}" if row["pool"] >= 1000 else f"| {row['pool']}")
    want = (f"{row['matched_additive_gold_control']:.3f} | "
            f"{row['proposed_centroid_plus_metadata']:.3f} | "
            f"{row['fraction_recovered']:.2f} |")
    if want not in paper:
        fails.append(f"pool-sensitivity row for pool={row['pool']} not stated in "
                     f"paper.md as {want!r}")
# and the arithmetic behind the fraction, recomputed rather than trusted
_num = recon["proposed_centroid_plus_metadata"] - recon["text_only"]
_den = recon["matched_additive_gold_control"] - recon["text_only"]
check("recovered fraction arithmetic (recomputed)",
      round(_num / _den, 4), recon["fraction_of_matched_control_recovered"])
# Round 7, M25: the headline fraction (0.5318) and the pool-sensitivity row at
# pool = 300 (0.5317) differ by 1e-4. They are not the same computation: the
# pool sweep re-selects lambda on dev at every pool size, and at pool 300 that
# selection lands on a neighbouring grid point. Both round to 0.53, which is the
# only form either appears in. Bound so the gap cannot silently widen.
_pool300 = [r for r in recon["pool_sensitivity"]["rows"] if r["pool"] == 300]
if _pool300:
    counts["check"] += 1
    _gap = abs(_pool300[0]["fraction_recovered"]
               - recon["fraction_of_matched_control_recovered"])
    if _gap > 0.0005:
        fails.append(
            f"the headline recovered fraction "
            f"({recon['fraction_of_matched_control_recovered']}) and the "
            f"pool-sensitivity row at pool=300 ({_pool300[0]['fraction_recovered']}) "
            f"differ by {_gap:.4f}. They are computed differently (lambda is re-selected "
            "on dev in the sweep), but a gap this size would no longer round to the same "
            "two decimals the paper quotes.")
check("n families where oracle equals gold control",
      recon["n_families_where_oracle_equals_gold_control"], 4)

# Claims sourced from data/processed/ rather than results/, which check() cannot see.
_ev = [json.loads(l) for l in
       open(os.path.join(ROOT, "data", "processed", "events.jsonl"), encoding="utf-8")]
_iy = sorted({e["init_year"] for e in _ev if e["init_year"]})
check("earliest initiation year", _iy[0], "2006")
_ry = sorted({e["year"] for e in _ev if e["year"]})
check("report-year range", f"{_ry[0]}-{_ry[-1]}", "2012-2026")
check("events with no country", sum(1 for e in _ev if not e["country"]), 1)
_low = [e["text"].lower() for e in _ev]
check("docs saying 'outside the United States'",
      sum("outside the united states" in t for t in _low), 0)
check("docs containing 'United States'", sum("united states" in t for t in _low), 4462)
# Round 9, M36: the 14.4% in Section 3.3 was computed from events.jsonl and never
# bound, so nothing tied the paper's figure to the file it came from.
_both = [e for e in _ev if e.get("init_year") and e.get("year")]
_diff = sum(1 for e in _both if str(e["init_year"]) != str(e["year"]))
check("events whose initiation year differs from the report year (%)",
      round(100 * _diff / len(_both), 1), 14.4, tol=0.05)
states("initiation-vs-report-year disagreement", 100 * _diff / len(_both), "{:.1f}%")

_q = [json.loads(l) for l in
      open(os.path.join(ROOT, "data", "processed", "benchmark.jsonl"), encoding="utf-8")]
_dev = [x for x in _q if x["split"] == "dev"]
_test = [x for x in _q if x["split"] == "test"]
_gd = set().union(*[set(x["gold_event_ids"]) for x in _dev])
_gt = set().union(*[set(x["gold_event_ids"]) for x in _test])
check("dev gold events", len(_gd), 895)
check("test gold events", len(_gt), 1760)
check("dev/test gold overlap", len(_gd & _gt), 470)
check("categories on both sides of the split",
      len({x["predicate"].get("defect_category") for x in _dev if x["predicate"].get("defect_category")}
          & {x["predicate"].get("defect_category") for x in _test if x["predicate"].get("defect_category")}),
      14)
_ent = [x for x in _test if not x["predicate"].get("defect_category")]
_dfc = [x for x in _test if x["predicate"].get("defect_category")]
_ge = set().union(*[set(x["gold_event_ids"]) for x in _ent])
_gf = set().union(*[set(x["gold_event_ids"]) for x in _dfc])
check("entity gold also in defect clusters (pct)",
      round(100 * len(_ge & _gf) / len(_ge), 1), 44.9)
check("defect-family test queries", len(_dfc), 84)

check("channel ablations", len(prop["channel_ablations"]), 6)
check("contrasts reported in script 05", len(prop["contrasts_vs_hybrid"]), 11)
check("Holm family in script 05 excludes the gold controls",
      sum(1 for v in prop["contrasts_vs_hybrid"].values() if v.get("p_holm") is not None), 8)
check("Holm family size in script 04", len(base["contrasts_vs_hybrid"]), 7)

# --- integrity scan ---------------------------------------------------------
DISCLAIMER = "This work was carried out independently, on personal time and equipment, and is not connected to the author's employment. The views expressed are the author's own and do not represent the views, positions or policies of any current, former or future employer or client. No proprietary, confidential or internal data of any organization was used. All data is public: the openFDA drug enforcement bulk export (US federal public domain, export date 2026-08-27), and two pretrained sentence encoders downloaded from their public repositories with their commit hashes recorded."
if flat(DISCLAIMER) not in paper_flat:
    fails.append("paper.md is missing the programme's standard disclaimer, verbatim")

BANNED = ["johnson & johnson", "j&j", "moderna", "regeneron", "perkinelmer",
          "our internal", "proprietary taxonomy", "confidential"]
# The disclaimer legitimately names the categories it disclaims; scan the rest.
low = paper_flat.replace(flat(DISCLAIMER), "").lower()
for b in BANNED:
    if b in low:
        fails.append(f"possible employer/proprietary reference in paper.md: {b!r}")
# The paper may only mention the string when explaining why it is never claimed.
# The manuscript may mention p < 0.001 only where it also disclaims it. Checked on
# the normalised text, since the two halves can fall on different lines.
for m in re.finditer(r"p < 0\.001", paper_flat):
    window = paper_flat[max(0, m.start() - 400):m.end() + 400]
    if "we never claim more" not in window:
        fails.append("paper.md claims 'p < 0.001', which 2000 resamples cannot resolve")

bib = open(os.path.join(ROOT, "references.bib"), encoding="utf-8").read()
keys = set(re.findall(r"@\w+\{([^,]+),", bib))
used = set()
for grp in re.findall(r"\[@([^\]]+)\]", paper):
    for part in grp.split(";"):
        used.add(part.strip().lstrip("@"))
for u in sorted(used):
    if u and u not in keys:
        fails.append(f"citation key not in references.bib: {u!r}")

# --- the disclaimer must reach every artifact a reader can receive ----------
# A previous version of this script checked paper.md only. The LaTeX converter was
# silently dropping the Disclaimer section, so the .tex and the PDF shipped without
# it while this script reported a clean run. Check all three.

def _pdf_text(path):
    """Extract text from the built PDF. Returns None if no extractor is available."""
    try:
        import subprocess
        out = subprocess.run(["pdftotext", path, "-"], capture_output=True, timeout=120)
        if out.returncode == 0:
            return out.stdout.decode("utf-8", "replace")
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        pass
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            return None
    try:
        return "\n".join((pg.extract_text() or "") for pg in PdfReader(path).pages)
    except Exception:
        return None


# Sentences that must survive conversion into every artifact. Kept short so that
# LaTeX escaping and PDF line-breaking cannot defeat a substring match.
DISCLAIMER_MARKERS = [
    "carried out independently, on personal time and equipment",
    "do not represent the views, positions or policies",
    "No proprietary, confidential or internal data of any organization was used",
]

_tex_path = os.path.join(ROOT, "paper_lncs.tex")
_pdf_path = os.path.join(ROOT, "paper_lncs.pdf")

if not os.path.exists(_tex_path):
    fails.append("paper_lncs.tex is missing; run scripts/10_build_latex.py")
else:
    _tex = flat(open(_tex_path, encoding="utf-8").read())
    if "\\section*{Disclaimer}" not in _tex:
        fails.append("paper_lncs.tex has no Disclaimer section")
    for _m in DISCLAIMER_MARKERS:
        if flat(_m) not in _tex:
            fails.append(f"paper_lncs.tex is missing disclaimer text: {_m!r}")

if not os.path.exists(_pdf_path):
    fails.append("paper_lncs.pdf is missing; build it before verifying")
else:
    _txt = _pdf_text(_pdf_path)
    if _txt is None:
        fails.append("cannot extract text from paper_lncs.pdf (install pdftotext or "
                     "pypdf); the disclaimer in the shipped PDF is UNVERIFIED")
    else:
        # A T1-encoded llncs build carries fi/fl/ff as single ligature glyphs that
        # pdftotext emits as control characters or drops outright, so a literal
        # substring match on "confidential" fails on a PDF that plainly contains
        # the word. Compare on letters-only text instead, which is immune to
        # ligature handling, hyphenation and line breaking alike.
        # A T1-encoded build carries ligatures as single glyphs that pdftotext
        # emits as C0 control characters (0x1b-0x1f here). Expand them, then
        # compare on letters only, which is immune to hyphenation and line breaks.
        T1_LIGATURES = {"\x1b": "ff", "\x1c": "fi", "\x1d": "fl",
                        "\x1e": "ffi", "\x1f": "ffl"}

        def _letters(t):
            for _c, _s in T1_LIGATURES.items():
                t = t.replace(_c, _s)
            return re.sub(r"[^a-z0-9]+", "", t.lower())
        _txt_letters = _letters(_txt)
        _txt = flat(_txt)
        if "Disclaimer" not in _txt:
            fails.append("paper_lncs.pdf has no Disclaimer heading")
        for _m in DISCLAIMER_MARKERS:
            if _letters(_m) not in _txt_letters:
                fails.append(f"paper_lncs.pdf is missing disclaimer text: {_m!r}")

# Every script the reader runs carries the short code notice.
_notice = "No proprietary, confidential or internal data of any organization was used"
# _superseded_20260907 is withdrawn material, but it still ships, so its scripts
# carry the notice like any other. An earlier version of this loop covered only
# scripts/ and figures/, so nothing enforced it there.
for _d in ("scripts", "figures", "_superseded_20260907"):
    _dir = os.path.join(ROOT, _d)
    if not os.path.isdir(_dir):
        continue          # _superseded_20260907 is absent from a fresh checkout
    for _f in sorted(os.listdir(_dir)):
        if _f.endswith(".py"):
            if flat(_notice) not in flat(
                    open(os.path.join(_dir, _f), encoding="utf-8").read()):
                fails.append(f"{_d}/{_f} is missing the code disclaimer notice")

# The manuscript must not point at scripts or figures that no longer exist.
for _ref in set(re.findall(r"(?:scripts|figures)/[A-Za-z0-9_.\-]+\.(?:py|pdf|png)", paper)):
    if not os.path.exists(os.path.join(ROOT, _ref)):
        fails.append(f"paper.md references a file that does not exist: {_ref}")

# --- every number in the .tex must survive into the PDF, IN ITS OWN TABLE -----
# A LaTeX table that overflows the text block is truncated in the rendered PDF:
# pdflatex reports "Overfull \\hbox", exits 0, and the missing columns are invisible
# to anything reading the source.
#
# An earlier version of this check took a global set difference between the
# decimals in the .tex and those in the PDF. That is position-blind and therefore
# far weaker than it looked: 0.302 occurs sixteen times in this document, so a
# table could lose the column containing it and the check would still pass. Of the
# numeric cells across these tables, most are shadowed that way somewhere else in
# the prose. The check below locates each table's own region of the PDF, by its
# caption, and requires that table's numbers to be present THERE.
def _strip_tex(t):
    t = re.sub(r"\\(?:textbf|textit|texttt|emph)\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\\[a-zA-Z]+\s*", " ", t)
    return re.sub(r"[{}$\\]", " ", t)


def _tex_data_only(t):
    """Drop comments and typesetting lengths: neither is a claim in the paper."""
    t = re.sub(r"(?<!\\)%.*", " ", t)
    t = re.sub(r"[pmb]\{[0-9.]+\\linewidth\}", " ", t)
    t = re.sub(r"\\(?:setlength|hspace|vspace|resizebox)\s*\{[^{}]*\}", " ", t)
    return t


if "paper_lncs.tex" in ARTIFACTS and os.path.exists(PDF_PATH):
    _tex_raw = open(TEX_PATH, encoding="utf-8").read()

    # -layout preserves table structure, which the default extraction does not.
    try:
        import subprocess
        _lay = subprocess.run(["pdftotext", "-layout", PDF_PATH, "-"],
                              capture_output=True, timeout=180)
        _layout = _lay.stdout.decode("utf-8", "replace") if _lay.returncode == 0 else None
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        _layout = None
    if _layout is None:
        _layout = ARTIFACTS.get("paper_lncs.pdf", "")
    for _c, _s in T1_LIGATURES.items():
        _layout = _layout.replace(_c, _s)
    _layout_flat = re.sub(r"\s+", " ", _layout)

    _n_tables, _n_vacuous = 0, 0
    for _m in re.finditer(r"\\begin\{table\}(.*?)\\end\{table\}", _tex_raw, re.S):
        _blk = _m.group(1)
        _cap = re.search(r"\\caption\{(.*?)\}\s*(?:\n|\\)", _blk, re.S)
        _tab = re.search(r"\\begin\{tabular\}(.*?)\\end\{tabular\}", _blk, re.S)
        if not (_cap and _tab):
            fails.append("a table in paper_lncs.tex has no caption, so its contents "
                         "cannot be located in the PDF and cannot be checked")
            continue
        _captxt = re.sub(r"\s+", " ", _strip_tex(_cap.group(1))).strip()
        _anchor = _captxt[:45]
        _i = _layout_flat.find(_anchor)
        if _i < 0:
            fails.append(f"the caption {_anchor!r} does not appear in the PDF, so that "
                         "table did not typeset")
            continue

        # Bound the window at the LAST row of this table rather than at a fixed
        # character count. An earlier version used a flat 2400-character forward
        # window, which ran well past the table body into the following prose, so
        # any value recurring in that prose was unprotected -- and 0.302 occurs
        # sixteen times in this document. The end of the table is the last row's
        # own text, so find that row in the PDF and stop there.
        # Split header from body at \\midrule. The caption often repeats a row
        # label ("Hybrid RRF + BGE is the strongest…"), so the body search must
        # start after the header row, not at the caption.
        _parts = re.split(r"\\midrule", _tab.group(1))
        _head = _parts[0] if len(_parts) > 1 else ""
        _body_tex = _parts[-1]
        _rows = [r for r in _body_tex.split("\\\\") if "&" in r]
        _win = _layout_flat[_i:_i + 3000]
        _headtxt = re.sub(r"\s+", " ", _strip_tex(_head.replace("&", " "))).strip()
        _htail = _headtxt.split()[-1] if _headtxt.split() else ""
        _hpos = _win.find(_htail) if _htail else -1
        if _hpos > 0:
            _win = _win[_hpos + len(_htail):]
        if _rows:
            _last = re.sub(r"\s+", " ", _strip_tex(_rows[-1])).strip()
            _tail = _last.split()[-1] if _last.split() else ""
            _j = _win.rfind(_tail)
            if _j > 0:
                _win = _win[:_j + len(_tail)]

        # Anchor each value to its own row rather than checking set membership over
        # the whole table: a cell can be corrupted into a value that appears in a
        # different row and set membership would not notice.
        _checked, _cursor = 0, 0
        for _row in _rows:
            _cells = [re.sub(r"\s+", " ", _strip_tex(c)).strip()
                      for c in _row.split("&")]
            if not _cells:
                continue
            _label = _cells[0].strip()
            _nums = [n for c in _cells[1:] for n in re.findall(r"\d+\.\d+", c)]
            if not _nums or not _label:
                continue
            _checked += len(_nums)
            # Scan forward only, so an earlier occurrence of a label cannot
            # satisfy a later row.
            _k = _win.find(_label, _cursor)
            if _k < 0:
                _k = _win.find(_label)
            if _k >= 0:
                _cursor = _k + len(_label)
            if _k < 0:
                fails.append(f"row {_label!r} of the {_captxt[:22]!r} table is missing "
                             "from that table's region of the PDF")
                continue
            # The row's own span: from its label to the next row's label, or the
            # end of the table.
            _rowwin = _win[_k:_k + 260]
            _got = set(re.findall(r"\d+\.\d+", _rowwin))
            _lost = [n for n in _nums if n not in _got]
            if _lost:
                fails.append(f"in the {_captxt[:22]!r} table, row {_label!r} is missing "
                             f"{len(_lost)} of its {len(_nums)} value(s) from the PDF "
                             f"beside that row -- the table is truncated or a cell has "
                             f"drifted: {_lost[:8]}")
        if _checked == 0:
            # A table with no numeric cells cannot be checked this way. Say so
            # rather than counting it as covered: an earlier version incremented
            # the "tables checked" counter for the example-question table, which
            # contains no decimals at all.
            _n_vacuous += 1
        else:
            _n_tables += 1
    if _n_tables == 0:
        fails.append("no numeric tables were found in paper_lncs.tex to check "
                     "against the PDF")

    # Round 8, N51: name the defect directly rather than inferring it from a
    # truncated line. A page break inside a listing puts the running head and
    # the folio between two of its lines, which is a copy-editing reject at
    # LNCS and is invisible to every numeric check in this script.
    for _vb in re.findall(r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}", _tex_raw, re.S):
        _vlines = [l.rstrip() for l in _vb.split("\n") if l.strip()]
        if len(_vlines) < 2:
            continue
        counts["cross_artifact"] += 1
        # -layout re-spaces the columns inside a listing, so the needles and the
        # haystack have to be compared with whitespace collapsed; the furniture
        # markers are then looked for in that same collapsed text.
        def _flatten(_t):
            return re.sub(r"[ \t]+", " ", _t)
        # Round 9, M33: find() took the first occurrence document-wide, so a
        # first line that also appears in prose widened the window across an
        # unrelated page break; and both failure paths fell through to
        # `continue`, silently skipping a real split. Anchor on whole lines,
        # search for the last line FORWARD from the first, and say so out loud
        # when the window cannot be built.
        _lay_lines = [_flatten(l).strip() for l in (_layout or "").split("\n")]
        _first, _last = _flatten(_vlines[0]).strip(), _flatten(_vlines[-1]).strip()
        try:
            _ai = _lay_lines.index(_first)
            _bi = _lay_lines.index(_last, _ai)
        except ValueError:
            print(f"note: page-break check SKIPPED for the listing beginning "
                  f"{_first[:40]!r} -- its first or last line could not be located "
                  "as a whole line in the extracted text; the truncation check "
                  "above covers the same block.")
            continue
        _lay = "\n".join(_lay_lines)
        _a = sum(len(l) + 1 for l in _lay_lines[:_ai])
        _b = sum(len(l) + 1 for l in _lay_lines[:_bi])
        _between = _lay[_a:_b]
        _furniture = [l.strip() for l in _between.split("\n")
                      if re.search(r"P\.\s*K\.\s*Balagam"
                                   r"|When the Benchmark Answers Itself", l)]
        if _furniture:
            fails.append(
                f"a verbatim listing is split across a page break: the running head "
                f"{_furniture[0]!r} is set between its lines. Wrap the block so it "
                "cannot break (scripts/10_build_latex.py emits a minipage), or shorten "
                "it.")

    # The global set difference is kept as a backstop for numbers outside tables.
    _tex_nums = set(re.findall(r"\d+\.\d+", _tex_data_only(_tex_raw)))
    _pdf_nums = set(re.findall(r"\d+\.\d+", ARTIFACTS.get("paper_lncs.pdf", "")))
    _gone = sorted(_tex_nums - _pdf_nums, key=float)
    if _gone:
        fails.append(f"{len(_gone)} number(s) present in paper_lncs.tex do not appear "
                     f"anywhere in the compiled PDF: {_gone[:12]}")
    # Round 8, N56 added this reverse direction; round 9, N60 found it explaining
    # 16 of its 28 divergences with a cause that did not apply to them. The text a
    # reader sees comes from the .tex AND the .bbl -- N53 had already taught the
    # range check that, and this comparison was not told, which is the ninth
    # instance of a fix landing on one surface and not the other. Ask both files,
    # then attribute what is left to the cause it actually has rather than to an
    # assumed one.
    _src_nums = set(_tex_nums)
    _bblp = os.path.join(ROOT, "paper_lncs.bbl")
    if os.path.exists(_bblp):
        _src_nums |= set(re.findall(
            r"\d+\.\d+", _tex_data_only(open(_bblp, encoding="utf-8").read())))
    # The vector figures draw their own axis ticks and bar labels from results/;
    # those are checked in figures/gen_figures.py. Identify them, do not assume.
    _fig_nums = set()
    _fig_files = sorted(glob.glob(os.path.join(ROOT, "figures", "*.pdf")))
    _fig_read = 0
    for _fig in _fig_files:
        _ft = pdf_text(_fig)
        if _ft:
            _fig_read += 1
            _fig_nums |= set(re.findall(r"\d+\.\d+", _ft))
    _extra = sorted(_pdf_nums - _src_nums, key=float)
    _from_fig = [x for x in _extra if x in _fig_nums]
    _rest = [x for x in _extra if x not in _fig_nums]
    # A long DOI broken across a PDF line leaves a prefix of a source number.
    # Round 10, N67: the first version tested only `y.startswith(x)`, which labels
    # ANY divergence whose value happens to prefix a source number as a DOI
    # artifact -- 0.30 prefixes 0.302, 1.00 prefixes 1.000. The two genuine cases
    # here were right by luck. Require the number it prefixes to be DOI-shaped,
    # so the explanation is earned rather than assumed. That is the whole point
    # of N60, and this rule was breaking it in the same function.
    _doi_like = {y for y in _src_nums if y.startswith("10.") or len(y.split(".")[0]) > 5}
    _split = [x for x in _rest
              if any(y.startswith(x) and y != x for y in _doi_like)]
    _unexplained = [x for x in _rest if x not in _split]
    # If the figure PDFs could not be read, say so: reporting "0 figure labels"
    # and reclassifying every axis tick would be a false explanation, not a
    # finding.
    _figmsg = (f"{len(_from_fig)} figure label(s) ({_from_fig[:6]}), drawn by "
               "figures/gen_figures.py from results/ and checked there"
               if _fig_read else
               f"figure labels could not be identified ({len(_fig_files)} figure "
               "PDF(s) found, none readable), so any axis tick below is "
               "unclassified rather than unexplained")
    if _extra:
        print(f"note: {len(_extra)} number(s) appear in the compiled PDF but not in "
              f"paper_lncs.tex or paper_lncs.bbl: " + _figmsg
              + (f"; {len(_split)} DOI fragment(s) left by a PDF line break "
                 f"({_split[:4]})" if _split else "")
              + (f"; {len(_unexplained)} accounted for by no known cause "
                 f"({_unexplained[:6]}) -- worth a look" if _unexplained else "")
              + ".")

    # Round 7, N45: there was no paper.md <-> paper_lncs.tex comparison at all,
    # only tex -> PDF. So a number edited in the authored source and not
    # regenerated (or edited in the .tex by hand) passed, while README.md and
    # DATA_CARD.md both claimed this script catches exactly that. paper.md is
    # the authored source and the .tex is generated from it, so any decimal in
    # one and not the other means the two have diverged.
    # Section headings carry their own numbers in the Markdown ("### 5.1 ...")
    # and are auto-numbered by LaTeX, so they are not claims and never reach the
    # .tex as digits.
    _md_body = re.sub(r"(?m)^#{1,6}\s*[\d.]+", " ", paper)
    _md_nums = set(re.findall(r"\d+\.\d+", _md_body))
    # Numbers the converter legitimately introduces or drops: column widths and
    # lengths live only in the .tex, and a Markdown-only figure path may carry a
    # version suffix. Compare in both directions and name the direction.
    # Round 8, M29: the literal {"0.62"} exemption was dead -- _tex_data_only
    # already removes p{0.62\linewidth} -- and would have silently swallowed any
    # future real 0.62.
    _tex_only = sorted(_tex_nums - _md_nums, key=float)
    _md_only = sorted(_md_nums - _tex_nums, key=float)
    counts["cross_artifact"] += 2
    if _md_only:
        fails.append(f"{len(_md_only)} number(s) in paper.md do not appear in "
                     f"paper_lncs.tex: {_md_only[:12]} -- the authored source and the "
                     "generated artifact have diverged; re-run scripts/10_build_latex.py")
    if _tex_only:
        fails.append(f"{len(_tex_only)} number(s) in paper_lncs.tex do not appear in "
                     f"paper.md: {_tex_only[:12]} -- the artifact states something the "
                     "authored source does not")

    # Verbatim blocks do not wrap: a long line runs off the page and its tail is
    # simply absent from the PDF.
    for _vb in re.findall(r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}", _tex_raw, re.S):
        for _line in _vb.split("\n"):
            _line = _line.rstrip()
            if len(_line) < 8:
                continue
            # Normalise the needle exactly as the artifact text was normalised,
            # or a line containing "--" fails against a dash-folded haystack.
            # Round 7 switched this to the -layout extraction on the theory that
            # four failures were a false-positive class. Round 8 (N51) showed
            # they were not: the listing had repaginated and LNCS was setting a
            # running head and folio INSIDE it, which the default extraction
            # reports as a lost line tail. The check is back on the default
            # extraction, where a split block fails, and the block itself is now
            # in a minipage so it cannot split. When a check starts failing after
            # content moves, the content moved badly.
            if strip_markup(_line).strip() not in ARTIFACTS.get("paper_lncs.pdf", ""):
                fails.append(f"a verbatim line is truncated in the PDF (it does not "
                             f"wrap, so the tail is lost): {_line!r}")

    # Overfull boxes are informational: a table inside \\resizebox reports the inner
    # box's width and still renders correctly. The checks above measure truncation
    # directly, which is what matters.
    # Overfull boxes are reported for information, but only a box that is INSIDE a
    # table or verbatim environment is safely dismissed: a table in \\resizebox
    # reports its inner width and still renders, and verbatim lines are checked
    # above. A box in body prose is a real margin overrun and is named as such.
    # An earlier version dismissed all of them with one unconditional sentence,
    # which hid three genuine overruns including a 134pt URL in the bibliography.
    # The build now writes its artifacts into _build/ so they stay out of the
    # folder listing; older builds left the log at the root. Look in both, so the
    # overfull-box checks keep running either way rather than silently skipping.
    _log = next((p for p in (os.path.join(ROOT, "_build", "paper_lncs.log"),
                             os.path.join(ROOT, "paper_lncs.log"))
                 if os.path.exists(p)), os.path.join(ROOT, "_build", "paper_lncs.log"))
    if os.path.exists(_log):
        _logtxt = open(_log, errors="replace").read()
        # The log's line numbers belong to whichever file TeX had open, and TeX
        # nests those in parentheses. A bibliography box carries .bbl line numbers,
        # and mapping those onto .tex line spans can classify a 250pt bibliography
        # overrun as "inside a table" because the .tex happens to have a table at
        # that line. Walk the parenthesis nesting and record the innermost open
        # file for each box, so a .tex span map is only applied to .tex boxes.
        _boxes = []
        _stack, _i = [], 0
        _box_re = re.compile(
            r"Overfull \\hbox \(([0-9.]+)pt too wide\)[^\n]*?"
            r"(?:at lines (\d+)|in alignment at lines (\d+))")
        # Round 9, M31 added the \vbox form; round 10, N66 found it bolted on
        # outside the machinery the hbox path uses -- a bare finditer over the
        # whole log, with no source attribution, no environment map, no threshold,
        # and a message that blamed the minipage for every match. TeX emits
        # "Overfull \vbox ... while \output is active" as routine page-breaking
        # output, so as written it would fail ordinary rebuilds and name the wrong
        # construct. It is collected in the same walk below, on the same terms.
        _vboxes = []
        _vbox_re = re.compile(
            r"Overfull \\vbox \(([0-9.]+)pt too high\)([^\n]*)")
        while _i < len(_logtxt):
            _ch = _logtxt[_i]
            if _ch == "(":
                _m2 = re.match(r"\(([^()\s]+)", _logtxt[_i:])
                _stack.append(_m2.group(1) if _m2 else "?")
            elif _ch == ")" and _stack:
                _stack.pop()
            elif _ch == "O" and _logtxt.startswith("Overfull \\hbox", _i):
                _m3 = _box_re.match(_logtxt[_i:])
                if _m3:
                    _ln = int(_m3.group(2) or _m3.group(3) or 0)
                    _src = next((s for s in reversed(_stack)
                                 if s.endswith((".tex", ".bbl", ".sty", ".cls"))), "?")
                    _boxes.append((float(_m3.group(1)), _ln, _src))
            elif _ch == "O" and _logtxt.startswith("Overfull \\vbox", _i):
                _m4 = _vbox_re.match(_logtxt[_i:])
                if _m4:
                    _ln = 0
                    _m5 = re.search(r"at lines (\d+)", _m4.group(2))
                    if _m5:
                        _ln = int(_m5.group(1))
                    _src = next((s for s in reversed(_stack)
                                 if s.endswith((".tex", ".bbl", ".sty", ".cls"))), "?")
                    _vboxes.append((float(_m4.group(1)), _ln, _src,
                                    "output is active" in _m4.group(2)))
            _i += 1

        # Line spans of the environments where an overfull box is expected.
        _safe = []
        # Round 8, M26: minipage joins the list because the reproducibility
        # listing now lives in one, and figure because a float's contents are
        # measured against the float width, not the text block.
        for _env in ("table", "verbatim", "figure", "minipage"):
            for _e in re.finditer(r"\\begin\{" + _env + r"\}(.*?)\\end\{" + _env + r"\}",
                                  _tex_raw, re.S):
                _safe.append((_tex_raw[:_e.start()].count("\n") + 1,
                              _tex_raw[:_e.end()].count("\n") + 1))

        def _inside(_ln):
            return any(a <= _ln <= b for a, b in _safe)

        # Round 7, N49: 12pt is ~4.2mm past the text block, plainly visible.
        # Sized down to the smallest overrun that is still worth a human look.
        # Round 10, N66: hoisted above the vbox verdict, which uses it too --
        # it was previously defined below its first (lazily-evaluated) use.
        _BIB_PT = 5.0

        # N66: the vbox verdict, on the same terms as the hbox one. A page-breaking
        # message is routine; a small overrun is cosmetic; and a box whose line
        # falls inside a float or a table is measured against that box, not the
        # page. What is left is something unbreakable running off the page bottom.
        _v_routine = [v for v in _vboxes if v[3]]
        _v_real = [v for v in _vboxes if not v[3]]
        _v_note = [v for v in _v_real if v[0] < _BIB_PT
                   or (v[2].endswith(".tex") and _inside(v[1]))]
        _v_bad = [v for v in _v_real if v not in _v_note]
        if _v_routine or _v_note:
            print(f"note: {len(_v_routine)} routine overfull vbox(es) from page "
                  f"breaking (\\output is active) and {len(_v_note)} under "
                  f"{_BIB_PT:.0f}pt or inside a float -- neither is a defect.")
        if _v_bad:
            fails.append(
                f"{len(_v_bad)} overfull vbox(es) (max {max(_v_bad)[0]:.1f}pt too "
                f"high, in {sorted({v[2] for v in _v_bad})}) -- something that cannot "
                "break, most likely a minipage around a verbatim listing, is running "
                "off the bottom of the page. Shorten the block or let it break.")

        _prose, _bib = [], []
        for _w, _ln, _src in _boxes:
            if _src.endswith(".bbl"):
                # A bibliography box is never "inside a table"; classify it as what
                # it is. This is the exact overrun the environment map was written
                # to catch, and .bbl line numbers made it look safe.
                _bib.append((_w, _ln))
            elif _src.endswith(".tex") and _inside(_ln):
                pass
            else:
                _prose.append((_w, _ln, _src))
        # Round 6, N39: an unconditional failure on any .bbl box made every
        # rebuild of the shipped release fail on a 3.3pt overrun that loses no
        # text. A bibliography URL that runs a few points past the margin is a
        # note; one that runs far past it is the 134pt defect this rule caught.
        _n_bib_all = len(_bib)
        _bib_note = [b for b in _bib if b[0] < _BIB_PT]
        _bib = [b for b in _bib if b[0] >= _BIB_PT]
        if _bib_note:
            print(f"note: {len(_bib_note)} bibliography hbox(es) overrun by under "
                  f"{_BIB_PT:.0f}pt (max {max(_bib_note)[0]:.1f}pt). An overfull hbox "
                  "reports overhang, not truncation, so no text is lost; this is a "
                  "cosmetic overhang into the right margin")
        if _bib:
            fails.append(f"{len(_bib)} overfull hbox(es) in the bibliography "
                         f"(max {max(_bib)[0]:.0f}pt, paper_lncs.bbl line(s) "
                         f"{[l for _, l in _bib][:6]}) -- a reference is running past "
                         "the right margin")
        # Round 7, N49 (related): `if _prose:` had always been a print, never a
        # fails.append, so a body-prose overrun of ANY size passed the gate --
        # including the 83pt path overrun round 4 found by reading the PDF. Give
        # it the same threshold the bibliography rule has, so a visible overrun
        # fails and a hairline one is a note.
        _prose_note = [b for b in _prose if b[0] < _BIB_PT]
        _prose_bad = [b for b in _prose if b[0] >= _BIB_PT]
        if _prose_note:
            print(f"note: {len(_prose_note)} body-prose hbox(es) overrun by under "
                  f"{_BIB_PT:.0f}pt (max {max(_prose_note)[0]:.1f}pt) -- cosmetic "
                  "overhang into the right margin")
        if _prose_bad:
            fails.append(
                f"{len(_prose_bad)} overfull hbox(es) OUTSIDE a table, figure, minipage or "
                f"verbatim block "
                f"(max {max(_prose_bad)[0]:.0f}pt, at "
                f"{sorted({(s, l) for _, l, s in _prose_bad})[:4]}) -- body prose is "
                "running past the right margin")
        _in_env = len(_boxes) - len(_prose) - _n_bib_all
        print(f"note: {_in_env} overfull hbox(es) inside a table, figure, minipage or "
              f"verbatim block "
              f"(expected: a table in \\resizebox reports its pre-scaling width, and "
              f"verbatim lines are checked line-by-line above).")
    else:
        # Round 6, N39: paper_lncs.log is gitignored, so for anyone working from
        # the release this whole block was skipped in silence -- including the
        # row-by-row table note, which reads as a pass. Say what was not run.
        print("note: overfull-box check SKIPPED (paper_lncs.log absent -- it is "
              "gitignored; run scripts/10_build_latex.py --compile to produce it).")

    # Round 7, N48: the coverage summary belongs to the table and verbatim checks,
    # which run whether or not the log exists. It used to sit inside the
    # log-present branch, and its "could not be checked" caveat was therefore
    # missing from exactly the branch every reader of the release sees.
    print(f"note: {_n_tables} numeric table(s) checked row-by-row against the PDF"
          + (f"; {_n_vacuous} table(s) have no numeric cells and could not be checked"
             if _n_vacuous else "")
          + "; verbatim blocks checked line-by-line for truncation and for page "
            "breaks set inside them.")

# --- ranges must keep a separator in the PDF -------------------------------
# A range that loses its dash turns two numbers into one wrong number. On this
# build body-prose en-dashes extract as 0x15 rather than being dropped, so no
# range is currently merged -- but that is a property of this TeX installation,
# not a guarantee, so check it rather than assume it.
if "paper_lncs.tex" in ARTIFACTS and "paper_lncs.pdf" in ARTIFACTS:
    _pdf_raw_txt = _pdf_raw if "_pdf_raw" in dir() else ""
    # Round 8, N52: _pdf_norm was the raw, newline-bearing extraction while the
    # needle demanded the two numbers be adjacent, so a line broken after an
    # en-dash reported a MERGE that had not happened -- an assertion of data
    # corruption caused by ordinary typesetting. Collapse whitespace first.
    _pdf_norm = re.sub(r"\s+", " ", normalise_dashes(_pdf_raw_txt))
    # Round 6, N38 tightened the needle; round 7, N46 fixes the search itself.
    # Both earlier versions acquitted DOCUMENT-WIDE: a range that occurs twice --
    # 14 of the 15 in this paper do -- was acquitted at one site by its intact
    # copy at the other. That is not hypothetical, because pdftotext returns the
    # abstract's en-dash as U+2013 and a caption's as \x15, so per-site
    # divergence is exactly what this PDF does. Counting is what makes the check
    # per-occurrence without having to align two differently-normalised strings:
    # every occurrence in the source must survive as a separated form in the PDF,
    # so losing ONE of two copies is a failure even though the other is intact.
    # Counting also removes the old false-positive exposure, since an unrelated
    # "12" (a citation, a page number) is no longer evidence of anything.
    # Round 8, N53: the tex side counted only "--" while the PDF side counted
    # folded en-dashes too, so a range also written as a literal U+2013
    # somewhere in the source (the BM25 disclaimer note does this) inflated the
    # PDF count and bought slack that acquitted a real merge. Fold both sides.
    # The source of the PDF's text is the .tex AND the .bbl: the bibliography and
    # the citation notes in it are compiled from references.bib, not from the
    # .tex. Counting the .tex alone undercounted every range that occurs in a
    # reference note, and that slack is what acquitted a merged 1--2 in round 7.
    _range_src = _tex_data_only(open(TEX_PATH, encoding="utf-8").read())
    _bbl = os.path.join(ROOT, "paper_lncs.bbl")
    if os.path.exists(_bbl):
        _range_src += "\n" + _tex_data_only(open(_bbl, encoding="utf-8").read())
    else:
        print("note: paper_lncs.bbl absent; range check counts the .tex only, so a "
              "range that occurs in the bibliography is not covered")
    _tex_ranges = re.findall(
        r"(\d+(?:\.\d+)?)(?:--|\u2013|\u2014)(\d+(?:\.\d+)?)", _range_src)
    for (_lo, _hi) in sorted(set(_tex_ranges)):
        counts["cross_artifact"] += 1
        _want = _tex_ranges.count((_lo, _hi))
        # N52: allow the single space a collapsed line break leaves behind.
        _got = len(re.findall(r"(?<![0-9.])" + re.escape(_lo) + r"- ?" + re.escape(_hi)
                              + r"(?![0-9])", _pdf_norm))
        if _got < _want:
            fails.append(
                f"the range {_lo}-{_hi} occurs {_want} time(s) in the source (.tex + .bbl) but "
                f"survives as a separated range only {_got} time(s) in the PDF: at "
                f"{_want - _got} site(s) its separator was dropped, so two numbers have "
                "merged into one wrong one")

# --- claims of the form "X is worth N on top of Y" ------------------------
# N26's class: a number can be correct, appear verbatim in two places, satisfy
# every string binding, and still be measured against the wrong baseline. Both
# copies of "0.107" agreed with each other; only one agreed with results/. These
# bindings tie the figure to the CONTRAST it names, so the baseline is checked
# and not just the digits.
# Round 6, N37: this loop originally read paper.md alone, which is the file
# the claim had already been fixed in -- the same shape as round 2's B3, where
# the verifier read paper.md while the .tex was missing the disclaimer. It now
# runs over every artifact a reader can receive, so a baseline swapped in the
# LaTeX source or surviving in the compiled PDF fails the gate.
_ORACLE = prop["summary"]["qir_oracle"]["ndcg@10"]["mean"]
for _label, _base_key, _phrase in (
        ("corpus-trained fusion", "hybrid_rrf", "on top of the corpus-trained fusion"),
        ("the strongest system in the spread", "hybrid_rrf_dense",
         "more than the strongest system in that spread reaches on its own")):
    _base = base["summary"][_base_key]["ndcg@10"]["mean"]
    _gain = round(_ORACLE - _base, 3)
    _missing_from = []
    for _aname, _atext in ARTIFACTS.items():
        counts["check"] += 1
        # Round 7, N47: the round-6 version failed only when the phrase was gone
        # from ALL artifacts, so deleting it from paper.md alone (the authored
        # source) or leaving a stale PDF against a fixed source both passed. The
        # failure this gate exists for is "missing from ONE artifact".
        if _phrase not in _atext:
            _missing_from.append(_aname)
        # Every sentence using this phrase must quote the gain against THAT
        # baseline, in every artifact the phrase appears in.
        for _mm in re.finditer(re.escape(_phrase), _atext):
            _before = _atext[max(0, _mm.start() - 90):_mm.start()]
            _quoted = re.findall(r"0\.\d{3}", _before)
            if _quoted and abs(float(_quoted[-1]) - _gain) > 0.0011:
                fails.append(
                    f"in {_aname}, a sentence says {_quoted[-1]} {_phrase!r}, but the "
                    f"oracle gain over {_label} is {_gain:.3f} (qir_oracle "
                    f"{_ORACLE:.4f} minus {_base_key} {_base:.4f}). The number is "
                    "measured against the wrong baseline.")
    # A phrase missing from any artifact is either a rewrite that removed the
    # binding along with the sentence, or a surface that did not receive the fix.
    if _missing_from:
        fails.append(f"the contrast phrase {_phrase!r} is absent from "
                     f"{', '.join(_missing_from)} (present in "
                     f"{', '.join(a for a in ARTIFACTS if a not in _missing_from) or 'no artifact'}), "
                     f"so the baseline binding for the gain over {_label} is not "
                     "enforced there -- rebuild the artifact, or update the phrase in "
                     "this script to match the manuscript")

# --- claims of the form "X buys/is worth N" -------------------------------
# Round 7, N45: mutation testing showed that the two numbers round 6 forced
# corrections on -- "buys the last 0.038" and the prefilter gain -- carried no
# binding at all: editing either in paper.md alone left the run green. These tie
# each figure to the contrast its own sentence names, in every artifact.
_ENCODER_GAIN = round(base["summary"]["hybrid_rrf_dense"]["ndcg@10"]["mean"]
                      - base["summary"]["hybrid_rrf"]["ndcg@10"]["mean"], 3)
_PREFILTER_GAIN = round(prop["summary"]["prefilter_hybrid"]["ndcg@10"]["mean"]
                        - prop["summary"]["hybrid_rrf"]["ndcg@10"]["mean"], 3)
_SLOTS_GAIN = round(prop["summary"]["slots_only"]["ndcg@10"]["mean"]
                    - prop["summary"]["hybrid_rrf"]["ndcg@10"]["mean"], 3)

for _what, _pattern, _value in (
        # "the pretrained encoder buys the last 0.038"
        ("the gain from adding BGE to the corpus-trained fusion "
         "(hybrid_rrf_dense minus hybrid_rrf)",
         r"buys the last (\d\.\d{3})", _ENCODER_GAIN),
        # "a conventional filter-then-search system ... is worth +0.162 nDCG@10
        #  over the same 0.302 baseline"
        ("the gain of the hard-prefilter system over the corpus-trained fusion "
         "(prefilter_hybrid minus hybrid_rrf)",
         r"is worth \+(\d\.\d{3}) nDCG@10 over the\s+same 0\.302 baseline",
         _PREFILTER_GAIN),
        # "... more than the +0.121 the constraint channel ... is worth on its own"
        ("the gain of the soft metadata filter alone (slots_only minus hybrid_rrf)",
         r"more than the \+(\d\.\d{3}) the constraint channel", _SLOTS_GAIN),
        # Round 8, N50: the abstract's parenthetical named the wrong system --
        # 0.579 is the centroid prior on top of the SOFT filter, so stripping the
        # prior gives slots_only 0.423, not prefilter_hybrid 0.464. 318 bindings
        # did not notice, because in_all_artifacts only asks whether the string
        # "0.464" occurs somewhere in the document, and it does. Bind each of
        # these two absolute scores to the system its own clause names.
        ("the soft metadata filter's score (slots_only)",
         r"soft metadata filter alone reaches (\d\.\d{3})",
         round(prop["summary"]["slots_only"]["ndcg@10"]["mean"], 3)),
        ("the hard prefilter's score (prefilter_hybrid)",
         r"hard\s+prefilter with no defect prior reaches (\d\.\d{3})",
         round(prop["summary"]["prefilter_hybrid"]["ndcg@10"]["mean"], 3))):
    _found_in = []
    for _aname, _atext in ARTIFACTS.items():
        counts["check"] += 1
        for _mm in re.finditer(_pattern, _atext):
            _found_in.append(_aname)
            if abs(float(_mm.group(1)) - _value) > 0.0011:
                fails.append(
                    f"in {_aname}, a sentence quotes {_mm.group(1)} where {_what} is "
                    f"{_value:.3f}. The number does not match the contrast the sentence "
                    "names.")
    _absent = [a for a in ARTIFACTS if a not in _found_in]
    if _absent:
        fails.append(f"the phrase binding {_what} to its figure matches nothing in "
                     f"{', '.join(_absent)} -- the claim is unguarded there; rebuild "
                     "the artifact, or update the pattern in this script")

# --- the raw export must be the one the manifest describes ------------------
_man = os.path.join(ROOT, "data", "raw", "MANIFEST.json")
if os.path.exists(_man):
    import hashlib
    _m = json.load(open(_man, encoding="utf-8"))
    _hashed, _skipped = 0, 0
    for _entry in _m.get("files", []):
        _fp = os.path.join(ROOT, _entry["path"])
        if not os.path.exists(_fp):
            _skipped += 1                 # not mirrored, which is the documented case
            continue
        _h = hashlib.sha256()
        with open(_fp, "rb") as _fh:
            for _b in iter(lambda: _fh.read(1 << 20), b""):
                _h.update(_b)
        _hashed += 1
        if _h.hexdigest() != _entry["sha256"]:
            fails.append(f"{_entry['path']} does not match its MANIFEST.json SHA-256")
    # Say so when nothing was hashed, or a green run reads as more than it is: in
    # the release the raw export is deliberately absent, so this check verifies
    # nothing there and only bites for someone who has fetched the data.
    if _hashed == 0:
        print(f"note: MANIFEST.json lists {_skipped} raw file(s), none present "
              "locally, so no digest was verified. Fetch the export to check it.")
    else:
        print(f"note: {_hashed} raw file(s) verified against MANIFEST.json digests")
else:
    fails.append("data/raw/MANIFEST.json is missing; it records the source URL and "
                 "digest a reader needs to obtain the same export")

_covered = sorted(ARTIFACTS) + ["references.bib", "data/raw/MANIFEST.json"]
print(f"bindings: {counts['check']} check() · {counts['states']} states() · "
      f"{counts['in_text']} in_text() · {counts['cross_artifact']} cross-artifact")
print("artifacts covered: " + ", ".join(_covered))
_total = sum(counts.values())
print(f"checks run: {_total} bindings, {len(fails)} failure(s)")
for f in fails:
    print("  FAIL:", f)
sys.exit(1 if fails else 0)
