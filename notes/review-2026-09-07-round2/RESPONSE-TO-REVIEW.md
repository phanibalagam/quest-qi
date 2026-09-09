# Paper 1 — response to the round-2 pre-submission review

**Date:** 2026-09-07
**Review responded to:** `REVIEW-FINDINGS-ROUND2.md`, `REGRESSION-REPORT.md` and
`CITATIONS-UNVERIFIED.md` in this folder (verdict: NO-GO, four blocking findings, mean
rigor 7.4/10, up from 6.4).
**Round-1 review and response:** `../review-2026-09-07/`.

**State after this pass:** `scripts/08_verify_manuscript.py` reports **0 failures** and
now prints its binding count and the artifacts it covered. The full pipeline (scripts
01–05) was re-run and every number reproduces. All four blocking findings are resolved,
along with the should-fix and minor lists.

---

## The finding that mattered most was correct, and it was ours

**N1 — the macro column was missing from the typeset PDF.** Confirmed exactly as
reported. Table 1 gained a ninth column in round 1 to fix the reviewer's most serious
finding (a hidden macro-average that reversed the headline ordering). Nine columns
overflowed the `llncs` text block by 151 pt, LaTeX truncated the table, and the shipped
PDF's header read `… nDCG@10 (macro) M` with the macro and MRR columns absent. The
manuscript verifier reported a clean run because it read `paper.md` and nothing else.

So the fix for "the macro-average is hidden" produced an artifact in which the
macro-average was still hidden. That is the third round running in which a correction
landed on one surface and not the others, and it is the reason the verifier work below
was done rather than deferred.

---

## Blocking findings

| ID | Status | Action |
|---|---|---|
| N1 | Fixed at the cause | `parse_table()` in `scripts/10_build_latex.py` now wraps any table of eight or more columns in `\resizebox`, and gives a long-prose column a fixed-width `p{}` so it wraps rather than running off the page. Table 1 renders complete; verified by rendering page 10 and reading it, not only by extracting text. |
| N2 | Fixed | "negative result" removed from the abstract, Contribution 4 and both §5.3 sites, replaced with "a null we cannot resolve at this sample size" / "inconclusive null". The manuscript no longer argues it lacks the power to demonstrate absence and then asserts absence. |
| N3 | Fixed | The Reproducibility paragraph now reads "seven in script 04, eight in script 05, with the three gold controls contrasted and reported with raw p only, and two more in the Section 5.3 robustness pair", matching the Statistics paragraph and the code. |
| N4 | Fixed, both halves | §4's "no data leaving the boundary, which is the constraint a regulated organization faces" is restated as a design choice adopted because it matches on-premise deployment. The Limitations paragraph is retitled "The encoding step needs network access and a working certificate store" and now says the embeddings are regenerable in about six minutes on CPU — which is consistent with them shipping, or with them not shipping. `results/dense_manifest.json`'s host string and `scripts/09_dense_encode.py`'s docstring are rewritten to describe a TLS-trust and egress requirement rather than a property of the analysis environment. |

## Should-fix

**N5 + M2 — the release now matches the documents.** The round-2 tarball was built by
archiving the working directory, so it carried the 4 MB raw export and the 20.6 MB
embeddings while `.gitignore`, `DATA_CARD.md` and `MANIFEST.json` all said it did not.
Rather than fix the archive by hand, `scripts/12_release_package.py` now builds it from
the `.gitignore` rules and **refuses to build** if it would ship anything the data card
describes as absent. The release is 45 files, 4.5 MB packed, with no build artifacts.

**N6 — the citation dispute goes against us, and the round-1 finding was right.** The
round-1 response asserted that CrossRef and OpenAlex both give `robertson2009bm25` as
4(1–2):1–174 and kept the entry. That description of those sources is accurate and the
conclusion drawn from it was wrong. The decisive check is structural and we repeated it:
`10.1561/1500000013` — Silvestri, *Mining Query Logs* — returns **the identical volume,
issue and pages** from CrossRef. Two monographs cannot occupy 4(1–2):1–174; FnTIR 3(3)
ends at p. 331 and BM25 begins at 333. The publisher deposited Silvestri's fields against
Robertson's DOI, and adding `number = {1--2}` propagated the error rather than fixing it.
The entry is now **3(4):333–389** with a note recording why it disagrees with CrossRef,
and the References section states the general rule: where an aggregator and the printed
article disagree on volume and pages, cite the article.

**N7 — the verifier now binds numbers to all three artifacts.** This is the change that
is meant to stop a round 5, and it was tested rather than assumed:

- Table 1 is **parsed out of** `paper.md` and `paper_lncs.tex` and every cell compared to
  `results/retrieval_results.json` numerically. The forty hard-coded `in_text()` literals
  for the table are gone. The macro column is recomputed from `by_family` rather than
  read from the summary field, so a disagreement between those two surfaces fails.
- Comparison is numeric, not string-based, deliberately: five stored values are exact
  ties at the third decimal (0.2995, 0.3025, 0.2835, 0.4165, 0.4935), where both roundings
  are correct. A string binding would have enforced a rounding house style instead of
  catching a changed number.
- Every decimal in the `.tex` must appear in the compiled PDF. This is the check that
  catches N1's whole class, whatever the cause.
- Every line of every `verbatim` block must appear in the PDF, since verbatim does not
  wrap and a long line loses its tail.
- The local raw export, if present, is checked against `MANIFEST.json`'s SHA-256.
- The script prints `bindings: 195 check() · 20 states() · 31 in_text() · 44
  cross-artifact` and the list of artifacts covered, on success as well as failure.

**Both failure modes were tested by reintroducing them.** Disabling the table resize
makes the verifier report *"6 number(s) present in paper_lncs.tex do not appear in the
compiled PDF … ['0.245', '0.256', '0.333', '0.364', '0.412', '0.500']"* — the same six
MRR values the reviewer found by hand. Editing one macro value in `paper.md` alone
reports *"row 'BGE-base (pretrained)' column macro reads 0.396 but results/ says
0.2963"*. Both pass again once reverted.

**N8 — the superlative was false and is removed.** "+0.038 … the largest single
improvement in this table" was wrong: fusion over BM25 alone is +0.066. §5.1 now says
"the largest gain from adding a dense channel anywhere in this table", and §5.3's power
argument is recalibrated against both figures rather than the wrong one.

**N9** script 05 was re-run so `results/retrieval_runs_proposed.json` exists and ships;
`DATA_CARD.md` now names both run files and says what they are for. **N10** the stale
reference to deleted scripts 06/07 in `scripts/04_retrieval.py` is replaced with the same
wording already used in script 05 — it was the last surviving generation reference in the
package.

## Minor

**M1** "all of them small" corrected: B (n = 18), E (n = 10) and F (n = 4) are small, D
is mid-sized at n = 25; and "entire advantage" softened to "almost all", since Hybrid RRF
also leads on `A_defect_form`. **M3** both pre-existing typesetting defects fixed — the
double-numbered captions ("Table 1. Table 1:") are gone, because the auto-label is now
suppressed and the manuscript's own numbering stands, which also keeps the in-text
references correct; and the §3.3 example-question table wraps instead of being cut
mid-sentence. **M4** run orders reconciled, with the PDF built before the verifier runs,
since the verifier now checks the compiled artifact. PDF metadata (`/Title`, `/Author`)
is now set through hyperref.

## Where this response disagrees with the review

Both points are in the citation audit, and neither affects a blocking finding.

**§2, "stale `year` fields", does not hold.** The review states that
`singhal2022clinicalknowledge`, `ji2022hallucination`, `rashkin2021attribution` and
`es2023ragas` kept preprint years. They did not: `references.bib` and `paper_lncs.bbl`
both carried 2023, 2023, 2023 and 2024 in the reviewed package. The keys retain their
old years, which the review itself says is acceptable.

**§3, "nine of the twelve new entries have no DOI or page range", does not hold.** The
actual count in the reviewed package was **one** — `rahmani2024synthetic`. The review's
own per-entry table is accurate; it lists corrections that were already applied. That one
genuine gap is now filled (pp. 2647–2651, doi 10.1145/3626772.3657942).

The review's **Fuhr 2017 vs 2018** point is upheld: dblp and SIGIR's own index both date
SIGIR Forum 51(3) to December 2017, and ACM's 2018 is the online-publication date. Key
and year both changed to 2017.

## Still open, and stated rather than fixed

Unchanged from round 1, and correctly identified by the review as not blocking arXiv:

1. **Gold-set adjudication** by at least two qualified reviewers over at least 150
   query–document pairs.
2. **20–30 investigator-written questions**, to measure how far the templates distort
   difficulty.

Round 2 adds two more that are disclosed rather than resolved, in the same spirit:
model-fitting variance is still single-seed for word2vec, SVD and the classifier; and
MiniLM's 0.0173 on the geography family — above both LSA and BGE, on the family carrying
the flagship diagnosis — is a small-sample artifact we have not investigated. The
Statistics paragraph states that the bootstrap carries none of this uncertainty.

## Where things are

`arxiv_submission.tar.gz` — the submission package (tex, bbl, bib, 3 vector figures).
`quest-qi_release.tar.gz` — the repository release, built by
`scripts/12_release_package.py` from the `.gitignore` rules.
