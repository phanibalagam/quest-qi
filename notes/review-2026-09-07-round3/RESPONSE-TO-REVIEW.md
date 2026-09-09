# Paper 1 — response to the round-3 pre-submission review

**Date:** 2026-09-07
**Review responded to:** `REVIEW-FINDINGS-ROUND3.md` and `CITATIONS-ROUND3.md` in this
folder (NO-GO on one sentence; rigor 6.4 → 7.4 → **8.3**).

**State after this pass:** `scripts/08_verify_manuscript.py` reports
`checks run: 290 bindings, 0 failure(s)`. Pipeline 01–05 re-run; every number
reproduces. All eight round-3 findings addressed, including both hardening items the
reviewer said do not enforce what they claim to.

---

## N11 — the blocking finding, and it is the worst kind

The round-2 response said, in writing: *"the superlative was false and is removed."* It
was removed from §5.1 and left in §5.3 — inside the sentence that calibrates the paper's
central inconclusive-null argument, which is the paragraph the paper most needs to be
trusted in. A reader was asked to judge +0.033 against a benchmark mis-stated by a factor
of 2.5, and Table 2 two pages earlier contradicts it.

That is the same failure this review has been charging the manuscript with for three
rounds, committed in the act of claiming it had been fixed. The appositive is deleted:
the sentence now reads *"…comparable to what adding BGE to the fusion buys (+0.038) and
half of what fusion over BM25 alone is worth (+0.066)."* No substitute superlative.

## The two hardening items — both were real, and both are now tested

**N12 — the tex-vs-PDF check was position-blind.** The round-2 response called it "the
check that catches N1's whole class". It was a global set difference, so it caught N1
only because those six MRR values happen to occur nowhere else. The reviewer's point is
correct and I confirmed the mechanism: **0.302 occurs sixteen times in the PDF**, so a
table could lose the column containing it and the check would pass.

Replaced with a per-table region check: each table is located in the PDF by its own
caption (`pdftotext -layout`), and that table's numbers must appear **in that table's
region**. Tested by widening Table 3 so LaTeX truncates it while the `.tex` stays intact —
N1's exact failure mode, one table over:

```
FAIL: 6 value(s) in the 'Table 3: Query-underst' tabular do not appear in that
      table's region of the PDF -- the table is being truncated:
      ['0.014', '0.033', '0.304', '0.409', '0.410', '0.425']
```

The old check would have caught two of those six. The global set difference is retained
as a backstop for numbers outside tables, and a table without a caption is now itself a
failure, since an uncaptioned table cannot be located and therefore cannot be checked.

**N13 — the release script's refusal was unreachable.** Correct: `MUST_NOT_SHIP` was
tested against the post-`.gitignore` list, so it could only fire if `.gitignore` was
already broken, and the script never read `DATA_CARD.md` at all. Now the forbidden list
is **parsed out of `DATA_CARD.md`'s "What is not, and why" section** — the document that
makes the promise — with `.gitignore`'s `!` carve-outs subtracted, and the scan runs over
the raw `os.walk` before filtering. It reports which forbidden files exist locally and
were correctly excluded, and says so loudly if the data card cannot be parsed rather than
silently falling back. Tested by removing the embeddings line from `.gitignore`:

```
refusing to build: DATA_CARD.md states these are not in this repository, but the
archive would contain them:
  data/processed/dense_embeddings.npz                              (exit 1)
```

## The rest

**N14** `_superseded_20260907/README.md` added, stating the folder is withdrawn, that
nothing in it is cited, and why the study was cut. The folder is now listed in
`DATA_CARD.md`, as are the review folders. The misleading duplicate is renamed
`DUPLICATE-of-results_retrieval_runs_proposed.json` with its provenance recorded — it is
script 05's retrieval rankings under the filename a since-fixed clobbering bug gave them,
not generation output. The stale `Sec. 5.6` comment in `06_generation_harness.py` is
corrected, and the verifier's disclaimer loop now covers the folder. The reviewer is
right that this makes the round-2 claim about script 04 holding "the last surviving
generation reference" wrong; it was the last one in the *shipped pipeline*.

**N15** §6's lead is now "The diagnosis survives; the fix is unresolved", and §8 says
plainly that the interval also spans a +0.033 gain this benchmark is too small to rule
out. **N16** "in Table 1" restored (now Table 2 after renumbering). **N17** figures
renumbered to appearance order — in PDF page order the floats now run Figure 1, Table 1,
Table 2, Figure 2, Table 3, Figure 3, Table 4, Table 5 — every float is cited at least
once in the body, the §3.3 example-question table has a caption and is Table 1, and
"Table 3b" is now Table 5. All five tables were renumbered in appearance order rather
than leaving a "Table 1a" ahead of Table 1. **N18** script 09 is in the README's run
block with its network caveat and an explanation of what breaks without it.

**M5** the stale release figures in the round-2 response were exactly the class of error
under discussion; this response quotes counts from the run that produced the shipped
archive. **M6** the verifier now prints whether any digest was actually checked, so a
green run in the release — where the raw export is deliberately absent — is not
over-read. **M7** the summary line carries the count. **M8** `cmap` added, so extracted
text keeps its ligatures ("findings", not "ndings"), which matters because the verifier
reads that text; the `Creator` string's underscores are fixed. **M9** `CITATION.cff` has
`url`, `version` and `date-released`.

## Note on the reviewer's own corrections

The review withdraws two round-2 citation findings after checking them against the
shipped `.bib`, and names the cause as the same not-verified-against-the-artifact error
it had been charging the manuscript with. Recording that here because it is the reason
the round-2 disputes were worth writing down rather than quietly accepting: a review that
corrects itself in public is more useful than one that does not, and the discipline runs
in both directions.

## Still open

Unchanged and correctly identified as not blocking arXiv: **gold-set adjudication** by at
least two qualified reviewers over at least 150 query–document pairs, and **20–30
investigator-written questions**. Both are the first thing a conference reviewer will ask
for. Also disclosed rather than fixed: single-seed model fitting, and MiniLM's 0.0173 on
the geography family — above LSA and BGE, on the family carrying the flagship diagnosis —
which is a small-sample artifact we have not investigated.
