#!/usr/bin/env python3
"""Verify a venue variant of the manuscript against the verified long version.

The long manuscript is checked number-by-number against results/ by
scripts/08_verify_manuscript.py (350 bindings). A venue cut states a *subset* of
those numbers in rewritten prose, so re-running the phrase bindings against it
would fail on wording rather than on fact. This script proves the property that
actually matters for a cut:

  every number the variant states is a number the long manuscript states,
  and the long manuscript's numbers are bound to results/.

Containment plus the parent's green run is what makes the variant's numbers
trustworthy. On top of that it re-runs the checks that are about the variant's
own artifacts rather than the parent's: markdown/tex/pdf agreement, the mandated
disclaimer, the GenAI declaration, and the venue page limit.

Usage:
  python3 scripts/13_verify_variant.py venues/ecir2027 --page-limit 12

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The long manuscript's own verifier owns these; we only fold what changes a
# number's spelling between markdown, LaTeX and extracted PDF text.
T1_LIGATURES = {"\x1b": "ff", "\x1c": "fi", "\x1d": "fl", "\x1e": "ffi",
                "\x1f": "ffl", "\x15": "-", "\x16": "-",
                "\x10": '"', "\x11": '"'}

NUM = re.compile(r"\d+\.\d+")


def fold(t):
    for k, v in T1_LIGATURES.items():
        t = t.replace(k, v)
    for a, b in (("\\%", "%"), ("\\&", "&"), ("\\#", "#"), ("\\_", "_"),
                 ("\\$", "$"), ("−", "-"), ("–", "-"), ("—", "-")):
        t = t.replace(a, b)
    return t


SEC_REF = re.compile(r"\bSections?~?\s*\d+(?:\.\d+)?(?:\s*[-\u2013]\s*\d+(?:\.\d+)?)?")
MD_HEAD = re.compile(r"(?m)^#{1,6}\s+\d+(?:\.\d+)*\s")
TEX_HEAD = re.compile(r"\\(?:sub)*section\*?\{\s*\d+(?:\.\d+)*\s")


def strip_section_numbers(t):
    """Section numbers are navigation, not data. They are the one place a
    decimal appears in the prose without a result behind it, and they differ
    between the long paper and a cut that renumbers, so they are removed
    before any number is compared."""
    t = MD_HEAD.sub("# ", t)
    t = TEX_HEAD.sub(r"\\section{", t)
    return SEC_REF.sub("Section", t)


def nums(t):
    return set(NUM.findall(strip_section_numbers(fold(t))))



# --- sentence-level bindings -------------------------------------------------
# Containment proves every number in the cut is a number the parent states and
# results/ binds. It cannot prove the number is attached to the right claim: a
# value moved onto the wrong system is still a value the parent states. That is
# the exact defect that reached an earlier draft, so the headline figures are
# bound here to the result files AND to an anchor phrase that must sit in the
# same sentence.
def _sentences(t):
    t = " ".join(fold(t).replace("**", "").split())
    return re.split(r"(?<=[.;])\s+", t)


def bind_sentences(body, value, anchors, label, fails, counter):
    counter[0] += 1
    hits = [s for s in _sentences(body) if value in s]
    if not hits:
        fails.append(f"{label}: the variant never states {value}")
        return
    for s in hits:
        if all(a.lower() in s.lower() for a in anchors):
            return
    fails.append(f"{label}: {value} appears, but not in a sentence mentioning "
                 + " / ".join(repr(a) for a in anchors)
                 + " -- check it is attached to the right system")


def pdftext(path):
    try:
        r = subprocess.run(["pdftotext", path, "-"], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else ""
    except FileNotFoundError:
        return ""


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


DISCLAIMER_PHRASES = [
    "carried out independently, on personal time and equipment",
    "not\nconnected to the author's employment",
    "No proprietary, confidential or internal data",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant", help="variant directory, e.g. venues/ecir2027")
    ap.add_argument("--page-limit", type=int, default=None,
                    help="max body pages, references excluded")
    a = ap.parse_args()

    vdir = a.variant if os.path.isabs(a.variant) else os.path.join(ROOT, a.variant)
    fails = []
    checks = 0

    parent_md = read(os.path.join(ROOT, "paper.md"))
    v_md_path = os.path.join(vdir, "paper.md")
    if not os.path.exists(v_md_path):
        print(f"FAIL: {v_md_path} is missing")
        sys.exit(1)
    v_md = read(v_md_path)

    # 1. Containment. Every decimal in the variant must be stated by the parent,
    #    whose every decimal is bound to results/ by script 08.
    parent_nums = nums(parent_md)
    v_nums = nums(v_md)
    missing = sorted(v_nums - parent_nums)
    checks += len(v_nums)
    if missing:
        fails.append("number(s) in the variant that the verified manuscript does "
                     "not state, so nothing binds them to results/: "
                     + ", ".join(missing))

    # 1b. Headline figures: bound to results/ and to the claim they belong to.
    import json
    _R = lambda n: json.load(open(os.path.join(ROOT, "results", n), encoding="utf-8"))
    try:
        prop = _R("proposed_results.json")
        base = _R("retrieval_results.json")
    except OSError as e:
        fails.append(f"cannot read results/: {e}")
        prop = base = None
    if prop is not None:
        f3 = lambda x: f"{x:.3f}"
        S = prop["summary"]
        cnt = [0]
        HEADLINE = [
            (f3(S["hybrid_rrf"]["ndcg@10"]["mean"]), ["text-only"], "hybrid RRF base"),
            (f3(S["slots_only"]["ndcg@10"]["mean"]), ["metadata channel"], "soft metadata filter"),
            (f3(S["prefilter_hybrid"]["ndcg@10"]["mean"]), ["prefilter"], "hard prefilter"),
            (f3(S["qir_centroid_slots"]["ndcg@10"]["mean"]), ["filter"], "prior + filter"),
            (f3(S["gold_additive_control"]["ndcg@10"]["mean"]), ["constant", "gold"], "additive gold control"),
            (f3(S["gold_lookup_ceiling"]["ndcg@10"]["mean"]), ["answer key"], "gold lookup ceiling"),
            (f3(base["summary"]["hybrid_rrf_dense"]["ndcg@10"]["mean"]), ["fusion"], "best text-only"),
        ]
        for value, anchors, label in HEADLINE:
            bind_sentences(v_md, value, anchors, label, fails, cnt)
        checks += cnt[0]

    # 2. The variant's own artifacts must agree with its markdown.
    tex_p = os.path.join(vdir, "paper_lncs.tex")
    pdf_p = os.path.join(vdir, "paper_lncs.pdf")
    for name, path in (("paper_lncs.tex", tex_p), ("paper_lncs.pdf", pdf_p)):
        if not os.path.exists(path):
            fails.append(f"{name} is missing from {a.variant}; build it first")
    if os.path.exists(tex_p):
        tex_n = nums(read(tex_p))
        checks += 1
        only_md = sorted(v_nums - tex_n)
        if only_md:
            fails.append("number(s) in the variant's paper.md but not its .tex: "
                         + ", ".join(only_md))
    if os.path.exists(pdf_p):
        pdf_raw = pdftext(pdf_p)
        if not pdf_raw:
            fails.append("cannot extract text from the variant PDF (install pdftotext)")
        else:
            pdf_n = nums(pdf_raw)
            checks += 1
            # Figure labels are drawn by matplotlib and live only in the PDF, so
            # compare in one direction: everything the prose claims must be set.
            unset = sorted(v_nums - pdf_n)
            if unset:
                fails.append("number(s) in the variant's paper.md that do not appear "
                             "in its compiled PDF: " + ", ".join(unset))

            # 3. Page limit, references excluded.
            if a.page_limit is not None:
                pages = pdf_raw.split("\f")
                ref_page = None
                for i, pg in enumerate(pages, 1):
                    if any(ln.strip() == "References" for ln in pg.split("\n")):
                        ref_page = i
                        break
                checks += 1
                if ref_page is None:
                    fails.append("no References heading found in the variant PDF, so "
                                 "the body page count cannot be established")
                elif ref_page > a.page_limit:
                    fails.append(f"body runs to page {ref_page}, over the "
                                 f"{a.page_limit}-page limit (references excluded)")
                else:
                    print(f"note: body ends on page {ref_page} of "
                          f"{a.page_limit} allowed; references follow")

    # 4. The mandated disclaimer and the GenAI declaration, in every artifact.
    arts = {"paper.md": v_md}
    if os.path.exists(tex_p):
        arts["paper_lncs.tex"] = read(tex_p)
    if os.path.exists(pdf_p):
        arts["paper_lncs.pdf"] = pdftext(pdf_p)
    for name, body in arts.items():
        flat = " ".join(fold(body).split())
        checks += 2
        for phrase in ("carried out independently, on personal time and equipment",
                       "No proprietary, confidential or internal data"):
            if phrase not in flat:
                fails.append(f"{name} is missing disclaimer text: {phrase!r}")
        if "Declaration of generative AI" not in flat:
            fails.append(f"{name} has no GenAI declaration")
        if "adversarial pre-submission review" not in flat:
            fails.append(f"{name}: the GenAI declaration does not disclose the "
                         "AI-assisted pre-submission review")

    print(f"variant: {a.variant}")
    print(f"numbers checked for containment: {len(v_nums)} "
          f"(parent states {len(parent_nums)})")
    print(f"checks run: {checks} bindings, {len(fails)} failure(s)")
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
