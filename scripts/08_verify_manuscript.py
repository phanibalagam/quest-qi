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

# Round 11, item 2: one stored value, one rendering. BGE-base on geography is
# 0.0095 in results/ -- exactly on a half, so 0.009 and 0.010 are both
# defensible -- and the manuscript printed one in Section 5.2 and the other in
# Table 6, seven pages apart, with the half-rounding convention stated only in
# Table 2's caption. Every binding passed, because each rendering was
# individually within tolerance. Tolerance is the wrong instrument here: what is
# wrong is not either digit, it is that a reader meets one number twice and sees
# two. The map from an occurrence to the value behind it is what the bindings
# already ARE, so this reads it off them rather than guessing from the text.
_RENDERINGS = {}

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

# 2026-09-18: the manuscript is built for more than one venue, so the artifact stem
# is a parameter rather than a literal. The default is unchanged, so every existing
# invocation behaves exactly as before; QUESTQI_STEM=paper_acm points the same
# bindings at the ACM build. The stem also names the artifacts in every failure
# message, so a report cannot say "paper_lncs.pdf" about a file it did not read.
# 2026-09-18: the default target is now the ACM build, because that is what is being
# submitted. It was paper_lncs, which meant a plain run checked a stale artifact and
# reported 349 bindings with 1 failure against a PDF built before the retitle, masking a
# clean 384/0 ACM build. The LNCS artifacts have been moved to _superseded_20260918/;
# QUESTQI_STEM still selects any stem, so nothing here is hard-wired to one venue.
_STEM = os.environ.get("QUESTQI_STEM", "paper_acm")

TEX_PATH = os.path.join(ROOT, f"{_STEM}.tex")
PDF_PATH = os.path.join(ROOT, f"{_STEM}.pdf")

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
    ARTIFACTS[f"{_STEM}.tex"] = strip_markup(open(TEX_PATH, encoding="utf-8").read())
else:
    fails.append(f"{_STEM}.tex is missing; run scripts/10_build_latex.py")
if os.path.exists(PDF_PATH):
    _pdf_raw = pdf_text(PDF_PATH)
    if _pdf_raw is None:
        fails.append(f"cannot extract text from {_STEM}.pdf (install pdftotext or "
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
        ARTIFACTS[f"{_STEM}.pdf"] = strip_markup(_pdf_raw)
else:
    fails.append(f"{_STEM}.pdf is missing; build it before verifying")


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
    if isinstance(actual, float) and isinstance(expected, float):
        # Record how this occurrence renders the value it is bound to. Only a
        # call site that passes the RAW stored value is visible here: one that
        # rounds before calling has already thrown the stored value away, and
        # the coverage denominator below says how many did.
        _RENDERINGS.setdefault(round(actual, 9), {}).setdefault(
            "%.3f" % expected, claim)


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
        if _name == f"{_STEM}.pdf":
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
    # 2026-09-18: 0.010 -> 0.009. The stored value is 0.0095, exactly on a half;
    # Table 6's cell, generated from results/, prints 0.009, and this sentence
    # printed 0.010 seven pages earlier. One value, one rendering.
    "BGE, a pretrained\nretrieval encoder, reaches 0.009",
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
# selection lands on a neighboring grid point. Both round to 0.53, which is the
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

_tex_path = os.path.join(ROOT, f"{_STEM}.tex")
_pdf_path = os.path.join(ROOT, f"{_STEM}.pdf")

if not os.path.exists(_tex_path):
    fails.append(f"{_STEM}.tex is missing; run scripts/10_build_latex.py")
else:
    _tex = flat(open(_tex_path, encoding="utf-8").read())
    if "\\section*{Disclaimer}" not in _tex:
        fails.append(f"{_STEM}.tex has no Disclaimer section")
    for _m in DISCLAIMER_MARKERS:
        if flat(_m) not in _tex:
            fails.append(f"{_STEM}.tex is missing disclaimer text: {_m!r}")

if not os.path.exists(_pdf_path):
    fails.append(f"{_STEM}.pdf is missing; build it before verifying")
else:
    _txt = _pdf_text(_pdf_path)
    if _txt is None:
        fails.append(f"cannot extract text from {_STEM}.pdf (install pdftotext or "
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
            fails.append(f"{_STEM}.pdf has no Disclaimer heading")
        for _m in DISCLAIMER_MARKERS:
            if _letters(_m) not in _txt_letters:
                fails.append(f"{_STEM}.pdf is missing disclaimer text: {_m!r}")

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
    # Round 13: the five escaped specials have to be unescaped BEFORE the
    # backslash sweep below, or "95\%" becomes "95 %" and no caption containing
    # a percent sign can ever be located in the PDF. Table 9's caption is the
    # first in this paper whose leading 45 characters carry one, and it reported
    # as "that table did not typeset" when the table had typeset perfectly.
    # strip_markup has done this since round 9; this function was never told.
    for _e, _p in (("\\%", "%"), ("\\&", "&"), ("\\#", "#"),
                   ("\\_", "_"), ("\\$", "$")):
        t = t.replace(_e, _p)
    return re.sub(r"[{}$\\]", " ", t)


def _tex_data_only(t):
    """Drop comments and typesetting lengths: neither is a claim in the paper."""
    t = re.sub(r"(?<!\\)%.*", " ", t)
    # The ACM template carries a CCSXML block whose concept_id attributes are
    # dotted CCS node identifiers -- 10002951.10003317.10003338.10003340 and the
    # like. They are classification metadata, not claims: they are absent from
    # paper.md by design and acmart renders only the human-readable descriptors,
    # so they appear in neither of the artifacts this function feeds. Exempting
    # them from the number comparisons is permitted ONLY because a check
    # replaces it: _check_ccs below binds every CCSXML concept to its \ccsdesc
    # entry and fails if the two lists disagree in descriptor or in weight.
    t = re.sub(r"\\begin\{CCSXML\}.*?\\end\{CCSXML\}", " ", t, flags=re.S)
    t = re.sub(r"[pmb]\{[0-9.]+\\linewidth\}", " ", t)
    t = re.sub(r"\\(?:setlength|hspace|vspace|resizebox)\s*\{[^{}]*\}", " ", t)
    return t


# --- CCS concepts: the XML block and the \ccsdesc list must agree -----------
# Replaces the CCSXML exemption in _tex_data_only. Two lists state the same
# classification in two syntaxes -- the machine-readable block the ACM Digital
# Library ingests, and the \ccsdesc lines that are typeset for the reader -- and
# nothing else compares them. A descriptor edited in one and not the other, or a
# weight changed in one place, would publish a paper whose printed classification
# and whose indexed classification disagree.
if f"{_STEM}.tex" in ARTIFACTS:
    _ccs_src = open(TEX_PATH, encoding="utf-8").read()
    _xml = re.findall(r"<concept_desc>(.*?)</concept_desc>\s*"
                      r"<concept_significance>(\d+)</concept_significance>",
                      _ccs_src, re.S)
    _desc = re.findall(r"\\ccsdesc\[(\d+)\]\{(.*?)\}", _ccs_src)
    if _xml or _desc:
        _xml_set = {(re.sub(r"\s+", " ", d).strip().replace("&lt;", "<"), int(w))
                    for d, w in _xml}
        _desc_set = {(re.sub(r"\s+", " ", d).strip(), int(w)) for w, d in _desc}
        for _pair in sorted(_xml_set | _desc_set):
            counts["cross_artifact"] += 1
            if _pair not in _xml_set:
                fails.append(f"CCS concept {_pair[0]!r} at weight {_pair[1]} is in the "
                             f"\\ccsdesc list of {_STEM}.tex but not in its CCSXML "
                             "block, so the typeset classification and the indexed one "
                             "disagree")
            elif _pair not in _desc_set:
                fails.append(f"CCS concept {_pair[0]!r} at weight {_pair[1]} is in the "
                             f"CCSXML block of {_STEM}.tex but has no \\ccsdesc line, "
                             "so it is indexed and never printed")

if f"{_STEM}.tex" in ARTIFACTS and os.path.exists(PDF_PATH):
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
        _layout = ARTIFACTS.get(f"{_STEM}.pdf", "")
    for _c, _s in T1_LIGATURES.items():
        _layout = _layout.replace(_c, _s)
    _layout_flat = re.sub(r"\s+", " ", _layout)

    _n_tables, _n_vacuous = 0, 0
    for _m in re.finditer(r"\\begin\{table\}(.*?)\\end\{table\}", _tex_raw, re.S):
        _blk = _m.group(1)
        _cap = re.search(r"\\caption\{(.*?)\}\s*(?:\n|\\)", _blk, re.S)
        _tab = re.search(r"\\begin\{tabular\}(.*?)\\end\{tabular\}", _blk, re.S)
        if not (_cap and _tab):
            fails.append(f"a table in {_STEM}.tex has no caption, so its contents "
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
        fails.append(f"no numeric tables were found in {_STEM}.tex to check "
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
    _pdf_nums = set(re.findall(r"\d+\.\d+", ARTIFACTS.get(f"{_STEM}.pdf", "")))
    _gone = sorted(_tex_nums - _pdf_nums, key=float)
    if _gone:
        fails.append(f"{len(_gone)} number(s) present in {_STEM}.tex do not appear "
                     f"anywhere in the compiled PDF: {_gone[:12]}")
    # Round 8, N56 added this reverse direction; round 9, N60 found it explaining
    # 16 of its 28 divergences with a cause that did not apply to them. The text a
    # reader sees comes from the .tex AND the .bbl -- N53 had already taught the
    # range check that, and this comparison was not told, which is the ninth
    # instance of a fix landing on one surface and not the other. Ask both files,
    # then attribute what is left to the cause it actually has rather than to an
    # assumed one.
    _src_nums = set(_tex_nums)
    _bblp = os.path.join(ROOT, f"{_STEM}.bbl")
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
    # A line break inside a DOI leaves a PREFIX of a source number when it breaks
    # after the number starts, and a MIDDLE or SUFFIX fragment when the DOI itself is
    # split -- 10.1145/3578337.3605136 wrapped after "3578" leaves "337.3605136",
    # which prefixes nothing. Earn both the same way N67 requires: the fragment must
    # be a contiguous substring of a DOI that the source actually contains, so a
    # coincidental decimal cannot be laundered into "a DOI artifact".
    _doi_strings = set(re.findall(r"10\.\d{4,9}/[^\s,}{)\]]+", _tex_raw))
    if os.path.exists(_bblp):
        _doi_strings |= set(re.findall(r"10\.\d{4,9}/[^\s,}{)\]]+",
                                       open(_bblp, encoding="utf-8").read()))
    # The substring test needs a length floor, or it launders short numbers: "4.0"
    # is a substring of almost any DOI, and the first version of this rule stole it
    # from the license-block explanation that had actually located it in a sentence.
    # Five characters is the shortest fragment a broken DOI can leave that is not
    # also an ordinary decimal in this manuscript.
    _split = [x for x in _rest
              if any(y.startswith(x) and y != x for y in _doi_like)
              or (len(x) >= 5 and any(x in d for d in _doi_strings))]
    # acmart typesets a license line that no source file contains ("...Creative
    # Commons Attribution 4.0 International License"), so its numbers reach the
    # PDF and nothing else. Earn the explanation the way N67 requires: the number
    # must actually occur inside the class-generated sentence, not merely equal a
    # value that sentence happens to use.
    # [^.]* was wrong here: the first "." it stops at is the one inside "4.0",
    # so the matched sentence excluded the very number it exists to explain and
    # the note still read "no known cause". Bound the window by length instead.
    _lic = re.search(r"licensed under a Creative Commons Attribution.{0,60}?License",
                     ARTIFACTS.get(f"{_STEM}.pdf", ""))
    _from_class = [x for x in _rest
                   if x not in _split and _lic and x in _lic.group(0)]
    # Priority: a number located inside a real class-generated sentence keeps that
    # explanation; only what is left is offered to the DOI-fragment test.
    _split = [x for x in _split if x not in _from_class]
    # Round 11: acmart numbers the sections itself, so a typeset heading number
    # ("5.6") exists in the PDF and in no source file, and was landing in
    # "accounted for by no known cause" -- which trains a reader to skim that
    # list, which is how a real divergence gets waved through. Earn the
    # explanation the way N67 requires: recompute acmart's numbering from the
    # sectioning commands in the .tex (starred headings take no number), and
    # accept the value only where the PDF carries it immediately in front of the
    # heading that number belongs to. A heading number that is WRONG, or that
    # sits anywhere but against its own heading, stays unexplained.
    _sec_no, _sub_no, _headings = 0, 0, {}
    for _sm in re.finditer(r"\\(sub)?section(\*?)\{((?:[^{}]|\{[^{}]*\})*)\}",
                           _tex_raw):
        if _sm.group(2):
            continue                       # starred: unnumbered, so no number
        if _sm.group(1):
            _sub_no += 1
            _headings[f"{_sec_no}.{_sub_no}"] = strip_markup(_sm.group(3)).strip()
        else:
            _sec_no += 1
            _sub_no = 0
            _headings[str(_sec_no)] = strip_markup(_sm.group(3)).strip()
    _pdf_flat = ARTIFACTS.get(f"{_STEM}.pdf", "")
    _from_secnum = [x for x in _rest
                    if x not in _split and x not in _from_class
                    and x in _headings and f"{x} {_headings[x]}" in _pdf_flat]
    _unexplained = [x for x in _rest
                    if x not in _split and x not in _from_class
                    and x not in _from_secnum]
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
              f"{_STEM}.tex or {_STEM}.bbl: " + _figmsg
              + (f"; {len(_split)} DOI fragment(s) left by a PDF line break "
                 f"({_split[:4]})" if _split else "")
              + (f"; {len(_from_class)} from the acmart license block "
                 f"({_from_class[:4]})" if _from_class else "")
              + (f"; {len(_from_secnum)} heading number(s) typeset by acmart "
                 f"({_from_secnum[:4]}), each matched against the heading it "
                 "numbers" if _from_secnum else "")
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
                     f"{_STEM}.tex: {_md_only[:12]} -- the authored source and the "
                     "generated artifact have diverged; re-run scripts/10_build_latex.py")
    if _tex_only:
        fails.append(f"{len(_tex_only)} number(s) in {_STEM}.tex do not appear in "
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
            if strip_markup(_line).strip() not in ARTIFACTS.get(f"{_STEM}.pdf", ""):
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
    _log = next((p for p in (os.path.join(ROOT, "_build", f"{_STEM}.log"),
                             os.path.join(ROOT, f"{_STEM}.log"))
                 if os.path.exists(p)), os.path.join(ROOT, "_build", f"{_STEM}.log"))
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
                         f"(max {max(_bib)[0]:.0f}pt, {_STEM}.bbl line(s) "
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
        print(f"note: overfull-box check SKIPPED ({_STEM}.log absent -- it is "
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
if f"{_STEM}.tex" in ARTIFACTS and f"{_STEM}.pdf" in ARTIFACTS:
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
    _bbl = os.path.join(ROOT, f"{_STEM}.bbl")
    if os.path.exists(_bbl):
        _range_src += "\n" + _tex_data_only(open(_bbl, encoding="utf-8").read())
    else:
        print(f"note: {_STEM}.bbl absent; range check counts the .tex only, so a "
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

# --- Section 5.5: every cell of the per-family matrix, bound to results/ ------
# Tables 6, 7 and 8 publish the full system x family matrix that the aggregates
# summarise. 204 cells is 204 opportunities for a transcription error that no
# aggregate could reveal, so each cell is read back out of paper.md and compared
# to the value in results/ that it claims to be. The row label fixes the system
# and the column position fixes the family, so a value moved onto the wrong row
# or the wrong column fails even though the number itself exists in the file --
# which is the N50 defect class, applied per cell.
_FAMS_5_5 = ["A_defect_form", "B_defect_severity", "C_firm_history",
             "D_defect_period", "E_defect_geography", "F_site_country"]
_TEXT_ROWS_5_5 = [("BM25", "bm25"), ("TF-IDF", "tfidf"), ("LSA", "lsa"),
                  ("word2vec", "w2v"), ("Hybrid RRF", "hybrid_rrf"),
                  ("BGE-base", "bge_base"), ("MiniLM", "minilm"),
                  ("Hybrid RRF + dense", "hybrid_rrf_dense")]
_PROP_ROWS_5_5 = [("Hybrid RRF (text only)", "hybrid_rrf"),
                  ("Classifier prior", "qir_clf"),
                  ("Centroid prior", "qir_centroid"),
                  ("Oracle defect category", "qir_oracle"),
                  ("Soft metadata filter", "slots_only"),
                  ("Hard metadata prefilter", "prefilter_hybrid"),
                  ("Classifier prior + filter", "qir_clf_slots"),
                  ("Centroid prior + filter", "qir_centroid_slots"),
                  ("Oracle category + filter", "qir_oracle_slots"),
                  ("Control: gold, down-weight", "gold_downweight_control"),
                  ("Control: gold, additive", "gold_additive_control"),
                  ("Ceiling: gold ranked first", "gold_lookup_ceiling")]


def _matrix_rows(caption_marker):
    """Return {row label: [cell strings]} for the table just above a caption."""
    i = paper.find(caption_marker)
    if i < 0:
        fails.append(f"paper.md has no table captioned {caption_marker!r}")
        return {}
    rows = {}
    for line in paper[:i].rstrip().split("\n")[::-1]:
        line = line.strip()
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        rows[cells[0].replace("*", "").strip()] = cells[1:]
    return rows


for _cap, _rowspec, _src, _metric in (
        ("*Table 6: nDCG@10 by question family, text-only", _TEXT_ROWS_5_5,
         base["by_family"], "ndcg@10"),
        ("*Table 7: nDCG@10 by question family for the query-understanding",
         _PROP_ROWS_5_5, prop["by_family"], "ndcg@10"),
        ("*Table 8: recall@100 by question family, text-only", _TEXT_ROWS_5_5,
         base["by_family"], "recall@100")):
    _rows = _matrix_rows(_cap)
    for _label, _key in _rowspec:
        _cells = _rows.get(_label)
        if _cells is None:
            fails.append(f"{_cap[:24]}...: no row labelled {_label!r} in paper.md")
            continue
        if len(_cells) != len(_FAMS_5_5):
            fails.append(f"{_cap[:24]}...: row {_label!r} has {len(_cells)} cells, "
                         f"expected {len(_FAMS_5_5)}")
            continue
        for _fam, _cell in zip(_FAMS_5_5, _cells):
            # Pass the RAW stored value, not round(...,3). Rounding here is
            # equivalent at tol=0.0006 for the cell comparison itself, and it
            # destroyed the one thing the rendering check needs: which stored
            # value this cell is a rendering OF. 204 of the manuscript's cells
            # were invisible to it for that reason.
            check(f"{_metric} {_key} x {_fam}",
                  _src[_key][_fam][_metric], float(_cell), tol=0.0006)

# The four prose figures in 5.5 that are NOT cells of those three tables.
states("prefilter recall@100 on geography",
       round(prop["by_family"]["prefilter_hybrid"]["E_defect_geography"]["recall@100"], 3))
states("geography query count",
       base["by_family"]["bm25"]["E_defect_geography"]["n_queries"], fmt="{:d}")
states("site-country query count",
       base["by_family"]["bm25"]["F_site_country"]["n_queries"], fmt="{:d}")

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



# --- Tables 9 and 10: every interval bound to results/ ----------------------
# Round 13. results/ has carried ndcg@10_ci95_iid for every by_family cell from
# the first run and the manuscript published none of it. Adding intervals adds
# 34 numbers, and an interval is two numbers that a transcription error can swap,
# widen or narrow without any aggregate noticing -- so each bound is read back
# out of paper.md by row label and column position and compared to results/,
# exactly as the Section 5.5 cells are.
_CI_KEY = "ndcg@10_ci95_iid"


def _ci_cells(caption_marker):
    """{row label: [cell strings]} for the table above a caption. Same reader as
    _matrix_rows; kept separate because these rows carry bracketed pairs rather
    than bare decimals and a shared parser would have to branch anyway."""
    _i = paper.find(caption_marker)
    if _i < 0:
        fails.append(f"paper.md has no table captioned {caption_marker!r}")
        return {}
    _rows = {}
    for _line in paper[:_i].rstrip().split("\n")[::-1]:
        _line = _line.strip()
        if not _line.startswith("|"):
            break
        _cells = [_c.strip() for _c in _line.strip("|").split("|")]
        if set("".join(_cells)) <= set("-: "):
            continue
        _rows[_cells[0].replace("*", "").strip()] = _cells[1:]
    return _rows


def _pair(cell):
    _m = re.match(r"^\[(\d\.\d{3}),\s*(\d\.\d{3})\]$", cell.strip())
    return (float(_m.group(1)), float(_m.group(2))) if _m else None


# Table 9: the strongest text-only system across all six families.
_T9 = _ci_cells("*Table 9: nDCG@10 with 95% confidence intervals")
_t9_sys = "hybrid_rrf_dense"
for _rowname, _what in (("nDCG@10", "point"), ("95% CI", "interval")):
    _cells = _T9.get(_rowname)
    if _cells is None:
        fails.append(f"Table 9: no row labelled {_rowname!r} in paper.md")
        continue
    if len(_cells) != len(_FAMS_5_5):
        fails.append(f"Table 9: row {_rowname!r} has {len(_cells)} cells, expected "
                     f"{len(_FAMS_5_5)}")
        continue
    for _fam, _cell in zip(_FAMS_5_5, _cells):
        _src = base["by_family"][_t9_sys][_fam]
        if _what == "point":
            check(f"Table 9 point, {_fam}", _src["ndcg@10"], float(_cell), tol=0.0006)
        else:
            _p = _pair(_cell)
            if _p is None:
                fails.append(f"Table 9: {_fam} interval cell {_cell!r} is not a "
                             "[low, high] pair at three decimals")
                continue
            check(f"Table 9 CI low, {_fam}", _src[_CI_KEY][0], _p[0], tol=0.0006)
            check(f"Table 9 CI high, {_fam}", _src[_CI_KEY][1], _p[1], tol=0.0006)
            if not _src[_CI_KEY][0] <= _src["ndcg@10"] <= _src[_CI_KEY][1]:
                fails.append(f"Table 9: {_fam} point estimate {_src['ndcg@10']} lies "
                             f"outside its own interval {_src[_CI_KEY]} in results/")
            counts["check"] += 1

# Table 10: the geography column of Table 7, with intervals.
_T10_ROWS = [("Hybrid RRF (text only)", "hybrid_rrf"),
             ("Soft metadata filter", "slots_only"),
             ("Hard metadata prefilter", "prefilter_hybrid"),
             ("Centroid prior + filter", "qir_centroid_slots"),
             ("Oracle category + filter", "qir_oracle_slots")]
_T10 = _ci_cells("*Table 10: the geography column of Table 7")
for _label, _key in _T10_ROWS:
    _cells = _T10.get(_label)
    if _cells is None:
        fails.append(f"Table 10: no row labelled {_label!r} in paper.md")
        continue
    if len(_cells) != 2:
        fails.append(f"Table 10: row {_label!r} has {len(_cells)} cells, expected 2")
        continue
    _src = prop["by_family"][_key]["E_defect_geography"]
    check(f"Table 10 point, {_key}", _src["ndcg@10"], float(_cells[0]), tol=0.0006)
    _p = _pair(_cells[1])
    if _p is None:
        fails.append(f"Table 10: {_key} interval cell {_cells[1]!r} is not a "
                     "[low, high] pair at three decimals")
        continue
    check(f"Table 10 CI low, {_key}", _src[_CI_KEY][0], _p[0], tol=0.0006)
    check(f"Table 10 CI high, {_key}", _src[_CI_KEY][1], _p[1], tol=0.0006)

# Both captions name the field they were read from. If that field is ever
# renamed in results/, the caption is a false provenance statement, so check it.
for _cap_file, _blob in (("results/retrieval_results.json", base),
                         ("results/proposed_results.json", prop)):
    counts["check"] += 1
    if _CI_KEY not in _blob["by_family"]["hybrid_rrf"]["E_defect_geography"]:
        fails.append(f"the Table 9/10 captions name `{_CI_KEY}` in {_cap_file}, and "
                     "that field is not there")
in_text("`ndcg@10_ci95_iid`")

# --- claim class N70: counts and superlatives over named systems/families ----
# Round 11. Three sentences in Section 5.5 shipped false -- "five of the eight
# score exactly 0.000" (four do), "leads form, severity, period and geography"
# (it leads form, period, geography and site country, and does not lead
# severity), "1.000 for six of the eight" (four). Every NUMBER in all three was
# correct and bound; what was false was a COUNT over a column and an ORDERING
# within one, and this script had no way to express either. 558 bindings passed
# over them.
#
# The class this closes: a sentence that makes a quantified or superlative claim
# ABOUT a table column without quoting a value the column contains. No value
# binding can see it, because there is no value in the sentence to bind.
#
# The rule here is the scan-corpus rule applied to prose. Every sentence in
# paper.md that (a) contains a count of the form "<n> of the <m>" or one of the
# ranking words below and (b) names a system or a question family is a
# candidate, the count of candidates is printed, and each one must be either
# BOUND (recomputed from results/) or EXEMPT with a reason naming why no cell
# can stand behind it. A candidate matching no registry entry is UNBOUND and
# FAILS -- an unbound superlative is what went out. A registry entry matching no
# candidate also fails: a claim edited out of the paper must not leave a green
# check behind it, which is BUILD-CHECKS' "check the old path, every time".


def _claim_sentences(md):
    """Candidate claim sentences in the authored source, as a flat list."""
    _keep, _fence = [], False
    for _ln in md.split("\n"):
        _s = _ln.strip()
        if _s.startswith("```"):
            _fence = not _fence
            continue
        # Table rows are checked cell by cell above; headings, rules and image
        # includes are not prose and would merge two sentences into one.
        if _fence or _s.startswith("|") or _s.startswith("#") \
                or _s.startswith("---") or _s.startswith("!["):
            continue
        _keep.append(_ln)
    _body = " ".join(_keep)
    for _c in ("**", "*", "`", "_"):
        _body = _body.replace(_c, "")
    return [_s.strip() for _s in
            re.split(r"(?<=[.!?])\s+(?=[A-Z(])", re.sub(r"\s+", " ", _body)) if _s.strip()]


# "only" is excluded when it is the tail of a compound adjective (text-only,
# lexical-only): that is a name, not a quantifier, and treating it as one made
# every table caption in Section 5 a candidate.
_WORDNUM = r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d+)"
_PAT_COUNT = re.compile(
    r"(?<![.\d])%s\s+of\s+the\s+%s(?![.\d])" % (_WORDNUM, _WORDNUM), re.I)
_PAT_SUPER = re.compile(
    r"\b(leads?|leading|best|worst|highest|lowest|(?<!-)only|every|none|no system"
    r"|strongest|weakest|outperforms|beats|top of|bottom of)\b", re.I)
_PAT_NAMED = re.compile(
    r"\b(BM25|TF-IDF|LSA|word2vec|Hybrid RRF|BGE-base|BGE|MiniLM|dense channel"
    r"|dense fusion|classifier prior|centroid prior|oracle|prefilter"
    r"|soft metadata filter|hard metadata|gold control|firm history|site country"
    r"|geography|severity|defect form|defect period|question famil\w+"
    r"|text-only system\w*|lexical channel\w*|retrievers?)\b", re.I)

# --- recompute helpers: every claim below is answered from results/ ----------
_SYS8 = ["bm25", "tfidf", "lsa", "w2v", "hybrid_rrf", "bge_base", "minilm",
         "hybrid_rrf_dense"]
_CORPUS_TRAINED = ["bm25", "tfidf", "lsa", "w2v"]
_NO_WEIGHTS = ["bm25", "tfidf", "lsa", "w2v", "hybrid_rrf"]
_DEFECT_FAMS = ["A_defect_form", "B_defect_severity", "D_defect_period",
                "E_defect_geography"]


def _mic(k):
    return base["summary"][k]["ndcg@10"]["mean"]


def _mac(k):
    return sum(base["by_family"][k][f]["ndcg@10"] for f in _FAMS_5_5) / len(_FAMS_5_5)


def _col(fam, metric="ndcg@10", systems=None):
    return {k: base["by_family"][k][fam][metric] for k in (systems or _SYS8)}


def _amax(d):
    return max(d, key=d.get)


def _amin(d):
    return min(d, key=d.get)


def _shown(claim, stored, printed, tol=0.0006):
    """A figure the manuscript PRINTS for a stored value.

    Round 11, item 2: comparing a parsed prose number to a rounded stored value
    with _cassert checks the value and records nothing, so the occurrence is
    never tied to the value it renders and two places can print one value two
    ways -- which is exactly what Section 5.2 and Table 6 did. Routing these
    through check() ties them, because check() is what records a rendering.
    """
    check(claim, stored, printed, tol=tol)
    return True


def _cassert(name, ok, detail):
    """A structural claim -- an ordering, a count, an identity -- not a value."""
    counts["check"] += 1
    if not ok:
        fails.append(f"claim binding FAILED, {name}: {detail}")
    return ok


def _leaders(metric="ndcg@10"):
    return {f: _amax(_col(f, metric)) for f in _FAMS_5_5}


# A binding that compares results/ against a number TYPED HERE from the prose is
# the defect it exists to catch, one level up: edit the sentence and the check
# still passes. Every handler below is handed the sentence the scanner matched
# and reads the assertion OUT OF IT -- the count, the range, the families named
# -- so the comparison is sentence vs results/, never results/ vs a literal.
_WORDVAL = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
            "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
            "twelve": 12}


def _n(tok):
    return _WORDVAL.get(tok.lower(), None) if not tok.isdigit() else int(tok)


def _asserted_counts(sent):
    """Every "<n> of the <m>" the sentence asserts, as (n, m) pairs."""
    _out = []
    for _m in _PAT_COUNT.finditer(sent):
        _tok = re.findall(r"[\w.]+", _m.group(0))
        _a, _b = _n(_tok[0]), _n(_tok[-1])
        if _a is not None and _b is not None:
            _out.append((_a, _b))
    return _out


def _asserted_nums(sent):
    """The decimals the sentence states, in order, dashes folded first."""
    return [float(_x) for _x in re.findall(r"\d\.\d{3}", normalise_dashes(sent))]


# "form" also occurs in "the per-family form of the identity", which is not the
# defect-form family; requiring it not to be followed by "of" keeps the family
# word from collecting the ordinary noun, which made a true sentence read false.
_FAMWORD = [("A_defect_form", r"\bform\b(?!\s+of\b)"),
            ("B_defect_severity", r"\bseverity\b"),
            ("C_firm_history", r"\bfirm history\b"), ("D_defect_period", r"\bperiod\b"),
            ("E_defect_geography", r"\bgeography\b"),
            ("F_site_country", r"\bsite country\b")]


def _asserted_families(clause):
    """Families a clause NAMES. The relative clause that follows a list is
    commentary on the claim, not part of it, so stop at it."""
    clause = re.split(r",?\s+which\b", clause, maxsplit=1)[0]
    return [_f for _f, _p in _FAMWORD if re.search(_p, clause, re.I)]


def _one_count(name, sent, want_n, want_m, what):
    """The sentence's own "<n> of the <m>" against the recomputed pair."""
    _cs = _asserted_counts(sent)
    if len(_cs) != 1:
        return _cassert(name, False,
                        f"expected exactly one count of the form '<n> of the <m>' in "
                        f"this sentence, found {len(_cs)}: {_cs}. The binding cannot "
                        f"tell which count it is about, so it is UNBOUND.")
    _sn, _sm = _cs[0]
    return _cassert(name, (_sn, _sm) == (want_n, want_m),
                    f"the manuscript says {_sn} of the {_sm}; recomputed from "
                    f"results/, {what} gives {want_n} of {want_m}")


def _b_abstract_spread(sent):
    _m = {k: _mic(k) for k in _SYS8}
    _got = _asserted_nums(sent)
    _cassert("abstract states three figures", len(_got) >= 3,
             f"expected the span and the geography ceiling; found {_got}")
    _shown("abstract span, low end", min(_m.values()), _got[0])
    _shown("abstract span, high end", max(_m.values()), _got[1])
    _g = _col("E_defect_geography")
    _shown("abstract geography ceiling", max(_g.values()), _got[2])
    # "the micro and macro aggregates disagree on which leads" -- the pair the
    # clause before it names: the pretrained encoder and the corpus-trained
    # fusion. Recompute the winner under each and require them to differ, which
    # is the entire content of the claim.
    _pair = ["bge_base", "hybrid_rrf"]
    _wm = _amax({k: _mic(k) for k in _pair})
    _wM = _amax({k: _mac(k) for k in _pair})
    _cassert("abstract aggregate disagreement", _wm != _wM,
             f"the abstract says the aggregates disagree on which of {_pair} leads, "
             f"but both pick {_wm}")
    return (f"stated {_got[:3]}; results span {min(_m.values()):.3f}-"
            f"{max(_m.values()):.3f}, geography best {max(_g.values()):.3f}; "
            f"micro leader {_wm} vs macro leader {_wM}")


def _b_contrib_diagnosis(sent):
    _best = _amax({k: _mic(k) for k in _SYS8})
    _bf = base["by_family"][_best]
    _got = _asserted_nums(sent)
    _ds = sorted(_bf[f]["ndcg@10"] for f in
                 ("A_defect_form", "B_defect_severity", "D_defect_period"))
    _want = [_bf["C_firm_history"]["ndcg@10"], _ds[0], _ds[-1],
             _bf["E_defect_geography"]["ndcg@10"]]
    _cassert("contribution states four figures", len(_got) == 4,
             f"expected four figures for the best text-only system; found {_got}")
    for _lbl, _w, _g2 in zip(("entity", "defect-semantics low", "defect-semantics high",
                              "geography"), _want, _got + [None] * 4):
        if _g2 is not None:
            _shown(f"contribution, {_lbl}", _w, _g2)
    return f"best text-only system is {_best}; stated {_got}"


def _b_intro_spread(sent):
    _m = {k: _mic(k) for k in _SYS8}
    _sp = max(_m.values()) - min(_m.values())
    _got = _asserted_nums(sent)
    _cassert("intro spread, as stated", _got and _got[0] == round(_sp, 3),
             f"the sentence states a spread of {_got[:1]}; results give {_sp:.4f}")
    _said = re.search(r"across (\w+) systems", sent)
    _cassert("intro spread denominator, as stated",
             _said is not None and _n(_said.group(1)) == len(_SYS8),
             f"the sentence says across {_said.group(1) if _said else '?'} systems; "
             f"results/ carries {len(_SYS8)}")
    return f"stated {_got[:1]} over {_said.group(1) if _said else '?'}; results {_sp:.4f} over {len(_SYS8)}"


def _b_offline_base(sent):
    _w = _amax({k: _mic(k) for k in _NO_WEIGHTS})
    _cassert("strongest weight-free configuration", _w == "hybrid_rrf",
             f"the sentence names Hybrid RRF the strongest configuration needing no "
             f"downloaded weights; the argmax over {_NO_WEIGHTS} is {_w}")
    return f"argmax over {_NO_WEIGHTS} is {_w} ({_mic(_w):.4f})"


def _b_holm_family(sent):
    _said = re.search(r"(\w+) in script 04", sent)
    _cassert("script 04 comparison count, as stated",
             _said is not None and _n(_said.group(1)) == len(_SYS8) - 1,
             f"the sentence says {_said.group(1) if _said else '?'} comparisons, every "
             f"other system in Table 2 against Hybrid RRF; Table 2 carries "
             f"{len(_SYS8)} systems, so there are {len(_SYS8) - 1}")
    return f"stated {_said.group(1) if _said else '?'}; {len(_SYS8)} systems give {len(_SYS8) - 1} contrasts"


def _b_strongest_text_only(sent):
    _wm = _amax({k: _mic(k) for k in _SYS8})
    _wM = _amax({k: _mac(k) for k in _SYS8})
    _cassert("strongest text-only system, both aggregates",
             _wm == "hybrid_rrf_dense" and _wM == "hybrid_rrf_dense",
             f"the sentence names Hybrid RRF + BGE strongest under both aggregates; "
             f"the argmaxes are micro {_wm}, macro {_wM}")
    return f"micro argmax {_wm} ({_mic(_wm):.4f}), macro argmax {_wM} ({_mac(_wM):.4f})"


def _b_fusion_beats(sent):
    # Read the delta the sentence attaches to each NAME, not any number in the
    # sentence: the confidence intervals here carry eight more decimals of the
    # same shape, and matching against the whole set would let a CI bound stand
    # in for the point estimate.
    _said = {}
    for _who, _k in (("BM25", "bm25"), ("TF-IDF", "tfidf"), ("LSA", "lsa")):
        _d = _mic("hybrid_rrf") - _mic(_k)
        _m = re.search(r"%s alone \(([+\u2212-]?\d\.\d{3})" % _who,
                       normalise_dashes(sent))
        _said[_who] = _m.group(1) if _m else None
        _cassert(f"fusion vs {_who}, as stated",
                 _m is not None and float(_m.group(1)) == round(_d, 3),
                 f"the sentence quotes {_said[_who]} against {_who} alone; results "
                 f"give {_d:+.4f}")
        if _who != "LSA":
            _cassert(f"fusion beats {_who}, direction", _d > 0,
                     f"the sentence says fusion beats {_who}; results give {_d:+.4f}")
    return (f"stated {_said}; hybrid_rrf {_mic('hybrid_rrf'):.4f} vs bm25 "
            f"{_mic('bm25'):.4f}, tfidf {_mic('tfidf'):.4f}, lsa {_mic('lsa'):.4f}")


def _b_w2v_trails(sent):
    _rest = [k for k in _SYS8 if k not in ("w2v", "minilm")]
    _bad = [k for k in _rest if _mic(k) <= _mic("w2v")]
    _cassert("word2vec trails everything but MiniLM", not _bad,
             "the sentence says averaged word2vec trails everything, with MiniLM "
             "named next as worse still; these do not beat it: "
             + ", ".join(f"{k} {_mic(k):.3f}" for k in _bad))
    _cassert("MiniLM is worse still", _mic("minilm") < _mic("w2v"),
             f"the sentence says MiniLM is worse still; minilm {_mic('minilm'):.4f} "
             f"vs w2v {_mic('w2v'):.4f}")
    return f"w2v {_mic('w2v'):.4f}, minilm {_mic('minilm'):.4f} (floor of the eight)"


def _b_dense_ahead(sent):
    for _agg, _f in (("micro", _mic), ("macro", _mac)):
        _w = _amax({k: _f(k) for k in _SYS8})
        _cassert(f"dense fusion ahead under {_agg}", _w == "hybrid_rrf_dense",
                 f"the sentence says the dense fusion is ahead under both aggregates; "
                 f"the {_agg} argmax is {_w}")
    _said = re.search(r"\((0\.\d{3}) micro, (0\.\d{3}) macro\)", sent)
    _cassert("dense fusion aggregates are stated", _said is not None,
             "the sentence claims the lead but prints no aggregates")
    if _said:
        _shown("dense fusion, micro", _mic("hybrid_rrf_dense"), float(_said.group(1)))
        _shown("dense fusion, macro", _mac("hybrid_rrf_dense"), float(_said.group(2)))
    return (f"stated {_said.groups() if _said else None}; argmax of both is "
            f"hybrid_rrf_dense")


def _b_entity_questions(sent):
    _best = _amax({k: _mic(k) for k in _SYS8})
    _bf = base["by_family"][_best]
    _got = _asserted_nums(sent)
    _cassert("entity questions states two figures", len(_got) == 2,
             f"expected two entity figures; found {_got}")
    _shown("entity questions, firm history", _bf["C_firm_history"]["ndcg@10"], _got[0])
    _shown("entity questions, site country", _bf["F_site_country"]["ndcg@10"], _got[1])
    return f"{_best}: stated {_got}"


def _b_lexical_zero(sent):
    _g = _col("E_defect_geography")
    _lex = ["bm25", "tfidf"]
    _bad = [(k, round(_g[k], 4)) for k in _lex if round(_g[k], 3) != 0.0]
    _cassert("every lexical channel is 0.000 on geography", not _bad,
             f"the sentence says every lexical channel scores exactly 0.000 on this "
             f"family; nonzero: {_bad}")
    _got = _asserted_nums(sent)
    _cassert("5.2 geography states four figures", len(_got) == 4,
             f"expected four figures; found {_got}")
    for _lbl, _k, _i in (("lexical channels", "bm25", 0), ("LSA", "lsa", 1),
                         ("BGE", "bge_base", 2), ("dense fusion",
                                                  "hybrid_rrf_dense", 3)):
        _shown(f"5.2 geography, {_lbl}", _g[_k], _got[_i])
    return f"stated {_got}; lsa {_g['lsa']:.4f}, bge {_g['bge_base']:.4f}, dense fusion {_g['hybrid_rrf_dense']:.4f}"


def _b_weakest_corpus_trained(sent):
    _w = _amin({k: _mic(k) for k in _CORPUS_TRAINED})
    _cassert("weakest corpus-trained channel", _w == "w2v",
             f"the sentence names word2vec the weakest corpus-trained channel; the "
             f"argmin over {_CORPUS_TRAINED} is {_w}")
    _said = re.search(r"weakest corpus.trained channel \(word2vec, (\d\.\d{3})\)", sent)
    _cassert("weakest corpus-trained value is stated", _said is not None,
             "the sentence does not print the value it names")
    if _said:
        _shown("weakest corpus-trained value", _mic(_w), float(_said.group(1)))
    return f"argmin over {_CORPUS_TRAINED} is {_w} ({_mic(_w):.4f})"


def _b_oracle_headroom(sent):
    _top = max(_mic(k) for k in _SYS8)
    _orc = prop["summary"]["qir_oracle"]["ndcg@10"]["mean"]
    _said = re.search(r"and (\d\.\d{3}) more than the strongest system", sent)
    _cassert("oracle headroom over the strongest system, as stated",
             _said is not None
             and float(_said.group(1)) == round(_orc - _top, 3),
             f"the sentence states {_said.group(1) if _said else '?'} more than the "
             f"strongest system in that spread; results give {_orc:.4f} - {_top:.4f} "
             f"= {_orc - _top:+.4f}")
    return f"oracle {_orc:.4f} over strongest {_top:.4f} = {_orc - _top:+.4f}"


def _b_metadata_ladder():
    _s = round(prop["summary"]["slots_only"]["ndcg@10"]["mean"], 3)
    _h = round(prop["summary"]["prefilter_hybrid"]["ndcg@10"]["mean"], 3)
    _t = round(_mic("hybrid_rrf"), 3)
    _cassert("metadata ladder ordering", _h > _s > _t,
             f"5.4 orders hard prefilter above soft filter above the text-only "
             f"baseline; results give {_h:.3f}, {_s:.3f}, {_t:.3f}")
    return f"prefilter {_h:.3f} > soft {_s:.3f} > text-only {_t:.3f}"


def _oracle_vs_control(where, sent=None):
    _o = prop["by_family"]["qir_oracle_slots"]
    _c = prop["by_family"]["gold_additive_control"]
    _same = [f for f in _FAMS_5_5
             if abs(_o[f]["ndcg@10"] - _c[f]["ndcg@10"]) < 1e-12]
    _cassert(f"oracle-with-filter equals the additive control ({where})",
             sorted(_same) == sorted(_DEFECT_FAMS),
             f"the identity is claimed over the four defect-slot families "
             f"{sorted(_DEFECT_FAMS)}; recomputed, it holds on {sorted(_same)}")
    if sent is not None:
        # Two of the three sentences name the families one by one; the third
        # says "the four families whose predicate is defect category x
        # constraint" and names none. Read whichever form the sentence uses --
        # the list if it gives one, the cardinal if it gives that instead -- and
        # require it to agree with the recomputed set. A sentence that gives
        # neither is not tied to anything, so it fails rather than passes.
        # One of the three names the families it holds on AND the families it
        # departs on, in one sentence. Split at the contrast before reading
        # either list, or the positive set collects all six and the claim looks
        # false when it is not.
        _parts = re.split(r"\b(?:and departs from it only on|and does not hold on"
                          r"|but not on|except on)\b", sent, maxsplit=1)
        _named = _asserted_families(_parts[0])
        _excl = _asserted_families(_parts[1]) if len(_parts) == 2 else []
        if _excl:
            _cassert(f"families excluded from the identity claim ({where})",
                     all(f not in _same for f in _excl)
                     and sorted(_named + _excl) == sorted(_FAMS_5_5),
                     f"the sentence says the identity departs on {sorted(_excl)} and "
                     f"holds on {sorted(_named)}; recomputed it holds on "
                     f"{sorted(_same)}")
        _card = re.search(r"\b(\w+) families\b", sent)
        if _named:
            _cassert(f"families named in the identity claim ({where})",
                     sorted(_named) == sorted(_same),
                     f"the sentence names {sorted(_named)}; the identity holds on "
                     f"{sorted(_same)}")
        elif _card is not None and _n(_card.group(1)) is not None:
            _cassert(f"family count in the identity claim ({where})",
                     _n(_card.group(1)) == len(_same),
                     f"the sentence says {_card.group(1)} families; the identity "
                     f"holds on {len(_same)}: {sorted(_same)}")
        else:
            _cassert(f"identity claim scope ({where})",
                     bool(re.search(r"every family where a defect slot exists", sent)),
                     "the sentence names neither the families nor how many, so no "
                     "cell can be tied to it")
    return f"identity holds on {sorted(_same)}, and on no other family"


def _b_firm_history_only(sent):
    _thr = _asserted_nums(sent)
    _bar = _thr[-1] if _thr else 0.200
    _mins = {f: min(_col(f).values()) for f in _FAMS_5_5}
    _above = [f for f, v in _mins.items() if v >= _bar]
    _cassert("firm history is the only family every system answers",
             _above == ["C_firm_history"],
             f"the sentence says firm history is the only family every text-only "
             f"system answers, at the bar {_bar} it names; the families whose column "
             f"minimum clears {_bar} are {_above}")
    _c = _col("C_firm_history")
    _cassert("firm history spread is stated", len(_thr) >= 2,
             f"expected a two-ended spread; found {_thr}")
    if len(_thr) >= 2:
        _shown("firm history spread, low end", min(_c.values()), _thr[0])
        _shown("firm history spread, high end", max(_c.values()), _thr[1])
    _over = {f: (_amax(_col(f)), round(max(_col(f).values()), 3))
             for f in ("A_defect_form", "B_defect_severity", "D_defect_period")
             if max(_col(f).values()) >= _bar}
    _cassert(f"no system reaches {_bar} on form, severity or period", not _over,
             f"the sentence says no system reaches {_bar} on those three families; "
             f"column maxima that do: {_over}")
    return (f"stated spread {_thr[:2]}, bar {_bar}; column minima "
            f"{dict((f.split('_', 1)[1], round(v, 3)) for f, v in _mins.items())}")


def _b_geography_zeros(sent):
    _g = _col("E_defect_geography")
    _z = [k for k in _SYS8 if round(_g[k], 3) == 0.000]
    _one_count("geography zero count", sent, len(_z), len(_SYS8),
               "the number of systems whose geography nDCG@10 rounds to 0.000")
    _got = _asserted_nums(sent)
    _cassert("geography best is stated", bool(_got), "no figure in the sentence")
    if _got:
        _shown("geography best", max(_g.values()), _got[-1])
    return (f"stated {_asserted_counts(sent)}, best {_got[-1:]}; results give "
            f"{len(_z)} of {len(_SYS8)} at 0.000 {_z}, best {_amax(_g)} "
            f"{max(_g.values()):.4f}")


def _b_ordering_not_stable(sent):
    _lead = _leaders()
    _cassert("TF-IDF leads firm history", _lead["C_firm_history"] == "tfidf",
             f"the sentence says TF-IDF leads firm history; the column argmax is "
             f"{_lead['C_firm_history']}")
    _got = _asserted_nums(sent)
    _cassert("TF-IDF firm history value is stated", bool(_got),
             "no figure in the sentence")
    if _got:
        _shown("TF-IDF firm history value", _col("C_firm_history")["tfidf"], _got[0])
    _a = sorted(_col("A_defect_form").items(), key=lambda kv: kv[1])
    _cassert("TF-IDF sits second from last on form", _a[1][0] == "tfidf",
             f"the sentence says TF-IDF sits second from last on form; the ascending "
             f"order is {[k for k, _ in _a]}")
    _cassert("TF-IDF form value is stated", len(_got) > 1,
             "the sentence names the position but prints no value")
    if len(_got) > 1:
        _shown("TF-IDF form value", _a[1][1], _got[1])
    # The ordering claim that shipped false. Read the families the sentence
    # NAMES as led, and the families it names as not led, and compare both
    # against the per-column argmax. Nothing here is typed from the prose.
    _led = [f for f in _FAMS_5_5 if _lead[f] == "hybrid_rrf_dense"]
    _m = re.search(r"dense channel leads (.*?)(?:$|\. )", sent)
    _clause = _m.group(1) if _m else ""
    _pos, _neg = _clause, ""
    _split = re.split(r"\b(?:and leads neither|and does not lead|but not)\b",
                      _clause, maxsplit=1)
    if len(_split) == 2:
        _pos, _neg = _split
    _said_led = _asserted_families(_pos)
    _said_not = _asserted_families(_neg)
    _cassert("families the dense fusion is said to lead",
             sorted(_said_led) == sorted(_led),
             f"the sentence names {sorted(_said_led)} as led by hybrid RRF with the "
             f"dense channel; the per-column argmax gives {sorted(_led)}")
    _cassert("families the dense fusion is said not to lead",
             all(f not in _led for f in _said_not),
             f"the sentence names {sorted(_said_not)} as NOT led; the argmax puts "
             f"hybrid_rrf_dense on top of "
             f"{sorted(f for f in _said_not if f in _led)}")
    _cassert("every family is accounted for",
             sorted(_said_led + _said_not) == sorted(_FAMS_5_5)
             or not _said_not,
             f"the sentence splits the six families into led {sorted(_said_led)} and "
             f"not led {sorted(_said_not)}, which does not cover {_FAMS_5_5}")
    if _asserted_counts(_pos):
        _one_count("dense fusion lead count", _pos, len(_led), len(_FAMS_5_5),
                   "the number of families whose column argmax is hybrid_rrf_dense")
    return (f"per-column argmax "
            f"{dict((f.split('_', 1)[1], _lead[f]) for f in _FAMS_5_5)}; sentence "
            f"names led={sorted(_said_led)} not-led={sorted(_said_not)}")


def _b_geography_column(sent):
    _p = prop["by_family"]
    _reads = ["slots_only", "prefilter_hybrid", "qir_centroid_slots"]
    _flat = [k for k in _reads
             if round(_p[k]["E_defect_geography"]["ndcg@10"], 3) == 0.000]
    _cassert("every constraint-reading system moves geography", not _flat,
             f"the sentence says every system that reads a constraint off the "
             f"question moves geography; still at 0.000: {_flat}")
    _priors = ["qir_clf", "qir_centroid", "qir_oracle"]
    _moved = [(k, round(_p[k]["E_defect_geography"]["ndcg@10"], 4)) for k in _priors
              if round(_p[k]["E_defect_geography"]["ndcg@10"], 3) != 0.000]
    _cassert("every slot-free prior stays at 0.000 on geography", not _moved,
             f"the sentence says every system that infers the defect category without "
             f"reading a slot stays at exactly 0.000, the oracle included; nonzero: "
             f"{_moved}")
    _got = _asserted_nums(sent)
    _cassert("three constraint-reading figures are stated", len(_got) >= 3,
             f"expected three figures; found {_got}")
    for _i, _k in enumerate(("slots_only", "prefilter_hybrid", "qir_centroid_slots")):
        if len(_got) > _i:
            _shown(f"geography column, {_k}",
                   _p[_k]["E_defect_geography"]["ndcg@10"], _got[_i])
    return f"stated {_got[:3]}; slot-free priors all 0.000 {_priors}"


def _b_firm_recall(sent):
    _r = _col("C_firm_history", "recall@100")
    _ones = [k for k in _SYS8 if round(_r[k], 3) == 1.000]
    _one_count("firm-history recall@100 count", sent, len(_ones), len(_SYS8),
               "the number of systems whose firm-history recall@100 rounds to 1.000")
    return (f"stated {_asserted_counts(sent)}; results give {len(_ones)} of "
            f"{len(_SYS8)} at 1.000 {_ones}")


def _b_centroid_beats_classifier(sent):
    _t = prop["query_category_top1_accuracy"]
    _c, _k = _t["lsa_centroid_test"], _t["classifier_zero_shot_test"]
    _cassert("centroid beats the trained classifier", _c > _k,
             f"the sentence says the centroid prior beats a trained classifier; "
             f"results give centroid {_c}, classifier {_k}")
    _said = re.search(r"by (\d+) points of category accuracy", sent)
    _cassert("centroid margin, as stated",
             _said is not None and int(_said.group(1)) == round(100 * (_c - _k)),
             f"the sentence says {_said.group(1) if _said else '?'} points; results "
             f"give {100 * (_c - _k):.1f}")
    return f"centroid {_c:.4f} vs classifier {_k:.4f}, margin {100 * (_c - _k):.1f} points"


def _b_interval_tables(sent):
    """Tables 9 and 10 are introduced as covering "the strongest text-only
    system". Which system that is, is an argmax, not a label."""
    _w = _amax({k: _mic(k) for k in _SYS8})
    _cassert("Table 9 covers the strongest text-only system", _w == "hybrid_rrf_dense",
             f"the sentence says Tables 9 and 10 cover the strongest text-only system "
             f"and Table 9's rows are Hybrid RRF + dense; the micro argmax is {_w}")
    return f"micro argmax is {_w}; Table 9's rows are that system"


def _b_firm_interval(sent=None):
    """Firm history's interval against the rest of its row. This sentence was
    written first as "clears everything else in the row", which is false: site
    country's interval [0.579, 0.913] covers firm history's [0.688, 0.888]
    entirely. Recomputed, not read."""
    _d = base["by_family"]["hybrid_rrf_dense"]
    _lo = _d["C_firm_history"][_CI_KEY][0]
    _clears = [f for f in _FAMS_5_5
               if f != "C_firm_history" and _lo > _d[f][_CI_KEY][1]]
    _cassert("firm history clears exactly the four defect-semantics families",
             sorted(_clears) == sorted(_DEFECT_FAMS),
             f"the sentence says firm history's lower bound clears the four "
             f"defect-semantics families and not site country; recomputed, its lower "
             f"bound {_lo:.4f} clears {sorted(_clears)}")
    _cassert("site country covers firm history entirely",
             _d["F_site_country"][_CI_KEY][0] <= _d["C_firm_history"][_CI_KEY][0]
             and _d["F_site_country"][_CI_KEY][1] >= _d["C_firm_history"][_CI_KEY][1],
             f"the sentence says site country's interval covers firm history's; "
             f"{_d['F_site_country'][_CI_KEY]} vs {_d['C_firm_history'][_CI_KEY]}")
    return (f"lower bound {_lo:.4f} clears {sorted(_clears)}; site country "
            f"{_d['F_site_country'][_CI_KEY]} covers it")


def _b_site_country_overlap():
    """Unconditional: the site-country paragraph carries no ranking word, so the
    scanner does not reach it, but every figure in it is a cell."""
    _d = base["by_family"]
    _n = _d["hybrid_rrf_dense"]["F_site_country"]["n_queries"]
    _cassert("site country query count", _n == 4,
             f"the paragraph says site country rests on four queries; results/ says {_n}")
    _c = {k: _d[k]["F_site_country"] for k in
          ("hybrid_rrf_dense", "hybrid_rrf", "bge_base")}
    _width = _c["hybrid_rrf_dense"][_CI_KEY][1] - _c["hybrid_rrf_dense"][_CI_KEY][0]
    _gap = _c["hybrid_rrf_dense"]["ndcg@10"] - _c["hybrid_rrf"]["ndcg@10"]
    _cassert("site country interval is wider than the gap it is meant to resolve",
             _width > _gap,
             f"the paragraph says the interval is wider than the gap between 0.735 and "
             f"0.506; width {_width:.4f}, gap {_gap:.4f}")
    _pairs = [(a, b) for a in _c for b in _c if a < b
              and not (_c[a][_CI_KEY][1] < _c[b][_CI_KEY][0]
                       or _c[b][_CI_KEY][1] < _c[a][_CI_KEY][0])]
    _cassert("all three site-country intervals overlap", len(_pairs) == 3,
             f"the paragraph says all three overlap; overlapping pairs: {_pairs}")
    for _k in ("hybrid_rrf", "bge_base"):
        _shown(f"site country point, {_k}", _c[_k]["ndcg@10"],
               round(_c[_k]["ndcg@10"], 3))
        _shown(f"site country CI low, {_k}", _c[_k][_CI_KEY][0],
               round(_c[_k][_CI_KEY][0], 3))
        _shown(f"site country CI high, {_k}", _c[_k][_CI_KEY][1],
               round(_c[_k][_CI_KEY][1], 3))
    return (f"n={_n}; width {_width:.3f} > gap {_gap:.3f}; "
            f"{len(_pairs)} of 3 pairs overlap")


def _b_geography_precision():
    """Unconditional: the Table 10 paragraph. Width, the ratio it quotes, the
    non-separation it claims, and the floor it does claim."""
    _g = prop["by_family"]
    _c = _g["qir_centroid_slots"]["E_defect_geography"]
    _h = _g["prefilter_hybrid"]["E_defect_geography"]
    _w = _c[_CI_KEY][1] - _c[_CI_KEY][0]
    _cassert("centroid-plus-filter interval width", round(_w, 3) == 0.362,
             f"the paragraph says the interval is 0.362 wide; results give {_w:.4f}")
    _textonly = base["by_family"]["hybrid_rrf_dense"]["E_defect_geography"]["ndcg@10"]
    _cassert("width against the text-only geography reading",
             round(_w / _textonly) == 15,
             f"the paragraph says fifteen times the text-only reading of "
             f"{_textonly:.3f}; the ratio is {_w / _textonly:.1f}")
    _cassert("centroid and prefilter are not separated",
             not (_c[_CI_KEY][0] > _h[_CI_KEY][1] or _h[_CI_KEY][0] > _c[_CI_KEY][1]),
             f"the paragraph says the distance between {_c['ndcg@10']:.3f} and "
             f"{_h['ndcg@10']:.3f} is not resolved; their intervals "
             f"{_c[_CI_KEY]} and {_h[_CI_KEY]} do not overlap")
    _readers = ["slots_only", "prefilter_hybrid", "qir_centroid_slots",
                "qir_oracle_slots"]
    _atzero = [k for k in _readers if _g[k]["E_defect_geography"][_CI_KEY][0] <= 0]
    _cassert("every constraint-reading configuration has a lower bound above zero",
             not _atzero,
             f"the paragraph says every configuration that reads a constraint clears "
             f"the text-only 0.000 with a lower bound above zero; these do not: "
             f"{_atzero}")
    return (f"width {_w:.4f} = {_w / _textonly:.1f}x the text-only {_textonly:.3f}; "
            f"centroid {_c[_CI_KEY]} overlaps prefilter {_h[_CI_KEY]}; "
            f"{len(_readers)} constraint readers all have lower bounds above zero")


def _b_conclusion():
    _best = _amax({k: _mic(k) for k in _SYS8})
    _bf = base["by_family"][_best]
    _cassert("conclusion, firm questions",
             round(_bf["C_firm_history"]["ndcg@10"], 3) == 0.796,
             f"the conclusion says 0.796; results give "
             f"{_bf['C_firm_history']['ndcg@10']:.4f}")
    _cassert("conclusion, geography questions",
             round(max(_col("E_defect_geography").values()), 3) == 0.024,
             f"the conclusion says 0.024; results give "
             f"{max(_col('E_defect_geography').values()):.4f}")
    _dense = _col("E_defect_geography")["bge_base"]
    _cassert("conclusion, the encoder does not rescue geography",
             _dense < max(_col("E_defect_geography").values()),
             f"the conclusion says a pretrained encoder does not rescue geography; "
             f"BGE-base reaches {_dense:.4f} there")
    return (f"{_best} firm {_bf['C_firm_history']['ndcg@10']:.3f}, geography ceiling "
            f"{max(_col('E_defect_geography').values()):.3f}, bge {_dense:.4f}")


# Each entry: (anchor, "bound"|"exempt", recompute function | reason).
# An exemption states WHY no cell can stand behind the sentence. An exemption
# with no reason is indistinguishable from a missed hit, so there are none.
_CLAIM_REGISTRY = [
    ("Eight retrievers span", "bound", _b_abstract_spread),
    ("the best text-only system answers entity questions at", "bound",
     _b_contrib_diagnosis),
    ("the spread across document representations is", "bound", _b_intro_spread),
    ("it is the strongest configuration that needs no downloaded weights", "bound",
     _b_offline_base),
    ("every other system in Table 2 against Hybrid RRF", "bound", _b_holm_family),
    ("is the strongest text-only system we have under both aggregates", "bound",
     _b_strongest_text_only),
    ("Fusion beats BM25 alone", "bound", _b_fusion_beats),
    ("Averaged word2vec trails everything", "bound", _b_w2v_trails),
    # One sentence carries both claims -- "the only pretrained dense channel
    # added to a fusion here" (a fact about the design, which results/ cannot
    # settle) and "the dense fusion is ahead under both aggregates" (a fact
    # about two columns, which it can). One sentence gets one entry, anchored on
    # a phrase unique to it, and the entry binds the part that is measurable.
    ("adding BGE to the fusion is worth", "bound", _b_dense_ahead),
    ("the best text-only system reaches 0.796 and 0.735", "bound",
     _b_entity_questions),
    ("Every lexical channel scores exactly 0.000 on this family", "bound",
     _b_lexical_zero),
    ("measuring instead from the weakest corpus-trained channel", "bound",
     _b_weakest_corpus_trained),
    ("reaches on its own, for free", "bound", _b_oracle_headroom),
    ("it is numerically identical to the additive control, per family", "bound",
     lambda _s: _oracle_vs_control("Table 4 prose", _s)),
    ("Firm history is the only family every text-only system answers", "bound",
     _b_firm_history_only),
    ("score exactly 0.000 and the best of them reaches", "bound",
     _b_geography_zeros),
    ("TF-IDF leads firm history at", "bound", _b_ordering_not_stable),
    ("Every system that reads a constraint off the question moves it", "bound",
     _b_geography_column),
    ("reproduces the additive gold control exactly on form, severity, period and "
     "geography", "bound", lambda _s: _oracle_vs_control("Table 7 prose", _s)),
    ("On firm history recall@100", "bound", _b_firm_recall),
    ("identical to the gold-membership control on every family where a defect slot "
     "exists", "bound", lambda _s: _oracle_vs_control("Section 5.6 parenthesis", _s)),
    ("it beats a trained classifier by 27 points of category accuracy", "bound",
     _b_centroid_beats_classifier),

    ("with 95% confidence intervals for the strongest text-only system", "bound",
     _b_interval_tables),

    ("added to the RRF score of every candidate in the matching category", "exempt",
     "'every' quantifies candidate documents inside the scoring rule, not systems "
     "or families in a results table; there is no column to recompute"),
    ("it already ranks every gold document in the pool first", "exempt",
     "'every' quantifies gold documents in a 300-document pool, not table cells; "
     "the lambda values in the same sentence are bound by the dev-curve check"),
    ("lifts geography recall@100 only to", "exempt",
     "adverbial 'only' meaning 'merely'; the value is bound by "
     "states('prefilter recall@100 on geography')"),
    ("a plain absence of the phrase from every document", "exempt",
     "'every' quantifies corpus documents, not table cells; the corpus counts are "
     "bound in the corpus section"),
    ("the retriever it sits on top of was too weak", "exempt",
     "'on top of' is the preposition, not a ranking: the sentence states an "
     "objection and names no system's position in any column"),
    ("No AI system selected the corpus", "exempt",
     "the AI-disclosure statement required by AI-DISCLOSURE-STANDARD.md; 'no "
     "system' there is not a retriever in Table 2 and results/ holds nothing that "
     "could stand behind it"),
    ("both gold controls draw from a 300-document pool", "exempt",
     "describes pool construction; the pool size 300 is bound above"),
]

# Two bindings whose sentences carry no count and no ranking word, so the
# scanner does not reach them: the metadata ladder in 5.4 and the conclusion's
# two headline figures. They are recomputed the same way, unconditionally,
# rather than left in the registry where they would report as stale.
print("claim class, unconditional: metadata ladder -- " + _b_metadata_ladder())
print("claim class, unconditional: conclusion figures -- " + _b_conclusion())
print("claim class, unconditional: firm-history interval -- " + _b_firm_interval())
print("claim class, unconditional: site-country intervals -- "
      + _b_site_country_overlap())
print("claim class, unconditional: geography interval precision -- "
      + _b_geography_precision())

_CLAIM_CANDIDATES = [_s for _s in _claim_sentences(paper)
                     if (_PAT_COUNT.search(_s) or _PAT_SUPER.search(_s))
                     and _PAT_NAMED.search(_s)]
_claim_report, _claim_used = [], set()
for _sent in _CLAIM_CANDIDATES:
    _flatsent = flat(_sent)
    _hit = [_i for _i, (_a, _k, _p) in enumerate(_CLAIM_REGISTRY)
            if flat(_a) in _flatsent]
    if not _hit:
        fails.append(
            "UNBOUND claim: a sentence makes a count or ranking claim about a named "
            "system or family and no binding stands behind it -- "
            + _flatsent[:160])
        _claim_report.append(("UNBOUND", _flatsent[:110], "no registry entry"))
        continue
    if len(_hit) > 1:
        fails.append("ambiguous claim anchors "
                     + str([_CLAIM_REGISTRY[_i][0] for _i in _hit])
                     + " all match one sentence; make them distinct")
        _claim_report.append(("AMBIGUOUS", _flatsent[:110], "several anchors match"))
        continue
    _i = _hit[0]
    _claim_used.add(_i)
    _anchor, _kind, _payload = _CLAIM_REGISTRY[_i]
    if _kind == "exempt":
        _claim_report.append(("EXEMPT", _anchor, _payload))
    else:
        _claim_report.append(("BOUND", _anchor, _payload(_flatsent)))
        # A claim fixed in the Markdown and not regenerated is the N45 class, so
        # the sentence carrying it has to reach every surface a reader opens.
        in_all_artifacts(f"claim anchor {_anchor!r}", _anchor)
_stale = [_a for _i, (_a, _k, _p) in enumerate(_CLAIM_REGISTRY)
          if _i not in _claim_used]
if _stale:
    fails.append(f"{len(_stale)} claim registry entr(y/ies) match no sentence in "
                 f"paper.md, so a green check stands behind prose that is no longer "
                 f"there: {_stale}")
print(f"claim class: {len(_CLAIM_CANDIDATES)} count/superlative sentence(s) over "
      f"named systems or families in paper.md; "
      f"{sum(1 for v, _, _ in _claim_report if v == 'BOUND')} BOUND, "
      f"{sum(1 for v, _, _ in _claim_report if v == 'EXEMPT')} EXEMPT, "
      f"{sum(1 for v, _, _ in _claim_report if v not in ('BOUND', 'EXEMPT'))} UNBOUND")
for _v, _a, _d in _claim_report:
    print(f"  {_v:9s} {_a[:66]:68s} {_d}")


# --- one stored value, one rendering ----------------------------------------
# The bindings above recorded, for every float they checked, the stored value
# and the three-decimal string the manuscript uses for it. A stored value that
# two places render differently fails here. Nothing is typed from the prose:
# both sides come from the binding that already ties that occurrence to results/.
_rend_conflicts = [(_v, _r) for _v, _r in sorted(_RENDERINGS.items()) if len(_r) > 1]
counts["check"] += len(_RENDERINGS)
for _v, _r in _rend_conflicts:
    fails.append(
        f"one stored value, two renderings: {_v!r} is printed "
        + " and ".join(f"{_s} ({_c})" for _s, _c in sorted(_r.items()))
        + ". Both are within tolerance of the stored value, which is why every "
          "value binding passed; a reader meets the same number twice and sees "
          "two different digits. Pick one and use it in both places.")

# The denominator. A call site that rounded before calling check() threw away
# the stored value, so this check cannot see it -- saying how many is the
# difference between a measured coverage and an assumed one.
_stored_all = set()


def _walk_floats(o):
    if isinstance(o, dict):
        for _v in o.values():
            _walk_floats(_v)
    elif isinstance(o, list):
        for _v in o:
            _walk_floats(_v)
    elif isinstance(o, float):
        _stored_all.add(round(o, 9))


for _rf in sorted(glob.glob(os.path.join(ROOT, "results", "*.json"))):
    _walk_floats(json.load(open(_rf, encoding="utf-8")))
_tied = sum(1 for _v in _RENDERINGS if _v in _stored_all)
print(f"rendering check: {len(_RENDERINGS)} bound value(s), {_tied} of them tied to a "
      f"raw value in results/ ({len(_RENDERINGS) - _tied} came from a call site that "
      f"rounded first and are checked only against themselves); "
      f"{len(_rend_conflicts)} conflict(s).")

# The sweep the check cannot cover: every stored value that sits exactly on a
# half at three decimals has two defensible renderings. Where BOTH strings occur
# in paper.md and no binding ties them to this value, that is reported and left
# alone -- the two strings are far more often two different cells than one value
# printed twice, and saying "hit" about those would be the same false
# explanation this script keeps having to undo.
_halves, _both = [], []
for _v in sorted(_stored_all):
    if _v <= 0:
        continue
    _s = f"{_v:.10f}".rstrip("0")
    _frac = _s.split(".")[1]
    if len(_frac) != 4 or not _frac.endswith("5"):
        continue
    _halves.append(_v)
    _lo = "%.3f" % (int(round(_v * 10000)) // 10 / 1000.0)
    _hi = "%.3f" % ((int(round(_v * 10000)) // 10 + 1) / 1000.0)
    if _lo in paper_flat and _hi in paper_flat:
        _both.append((_v, _lo, _hi, _v in _RENDERINGS))
print(f"rendering sweep: {len(_halves)} stored value(s) sit exactly on a half at three "
      f"decimals; {len(_both)} have both renderings present somewhere in paper.md, of "
      f"which {sum(1 for _x in _both if _x[3])} are tied to a binding and therefore "
      f"checked above; the rest are two different cells sharing two strings and are "
      f"left alone: "
      + ", ".join(f"{_v}->{_lo}/{_hi}" for _v, _lo, _hi, _t in _both if not _t) + ".")


# --- the venue's page floor, as a binding -----------------------------------
# Round 13. Round 12 reported "905 bindings, 0 failures" against a build whose
# References heading sat on page 20, breaching TOIS's 20-page minimum excluding
# references. Nothing here knew about the floor, so a green run said nothing
# about the one constraint that blocked submission. That is the same shape as
# every other defect this script exists to catch: a true statement about what
# was checked, mistaken for a statement about what matters.
#
# It was not added in round 12 because it would have failed on arrival, and a
# check written while it fails is a note. It passes now, so it is a check.
_FLOOR_PAGE = 21          # references must begin here or later: 20 body pages
_pdf_pages = None
if os.path.exists(PDF_PATH):
    _raw = pdf_text(PDF_PATH)
    if _raw is None:
        fails.append("the page floor cannot be checked: no text could be extracted "
                     f"from {_STEM}.pdf")
    else:
        _pages = _raw.split("\f")
        _pdf_pages = sum(1 for _p in _pages if _p.strip())
        # The heading acmart typesets, not the word "references" wherever it
        # occurs: [51] cites a paper with "preferences" in its title, and the
        # bibliography itself is full of the word.
        _ref_page = None
        for _i, _p in enumerate(_pages, 1):
            if _p.lstrip().startswith("References") or "\nReferences\n" in _p:
                _ref_page = _i
                break
        counts["check"] += 1
        if _ref_page is None:
            fails.append("no References heading found in the compiled PDF, so the "
                         "page floor cannot be checked -- which is not a pass")
        elif _ref_page < _FLOOR_PAGE:
            fails.append(
                f"page floor: references begin on page {_ref_page} of {_pdf_pages}. "
                f"TOIS requires a minimum of {_FLOOR_PAGE - 1} pages excluding "
                f"references, so the heading must fall on page {_FLOOR_PAGE} or "
                f"later. The build is {_FLOOR_PAGE - _ref_page} page(s) short.")
        else:
            print(f"page floor: references begin on page {_ref_page} of "
                  f"{_pdf_pages} (minimum {_FLOOR_PAGE}).")

_covered = sorted(ARTIFACTS) + ["references.bib", "data/raw/MANIFEST.json"]
print(f"bindings: {counts['check']} check() · {counts['states']} states() · "
      f"{counts['in_text']} in_text() · {counts['cross_artifact']} cross-artifact")
print("artifacts covered: " + ", ".join(_covered))
_total = sum(counts.values())
print(f"checks run: {_total} bindings, {len(fails)} failure(s)")
for f in fails:
    print("  FAIL:", f)
sys.exit(1 if fails else 0)
