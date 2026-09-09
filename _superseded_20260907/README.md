# WITHDRAWN — retained for audit only

Everything in this folder was removed from the manuscript on **2026-09-07**, when
Section 5.6 (the answer-synthesis study) was cut in response to a pre-submission
review. **Nothing here is cited by the paper, and none of it should be.** No number
in `paper.md`, `paper_lncs.tex` or `paper_lncs.pdf` derives from any file here.

It is kept so that the excision can be audited rather than taken on trust: a reader
who wants to know what was removed, and satisfy themselves that removing it was not
a way of hiding an inconvenient result, can read it here. The review that prompted
the cut, and the response to it, are in `../notes/review-2026-09-07/`.

| File | What it is |
|---|---|
| `06_generation_harness.py` | Wrote the answer-synthesis prompts. Its `SYSTEM_FOR_EVIDENCE` comment still refers to Sec. 5.6; that section no longer exists. |
| `07_score_generation.py` | Mechanical scoring of the archived answers. |
| `generation_results.json` | The scored results that fed the withdrawn generation table. It was Table 4 at the time; the manuscript's current Table 4 is the metadata-channel/controls table and is unrelated. |
| `generation_answers/` | Prompts and verbatim model outputs, SHA-256 hash-linked to the prompts. |
| `fig4_generation.pdf`, `.png` | The withdrawn Figure 4. The manuscript now has three figures; there is no current Figure 4. |

There was a fourth file here, `generation_runs.json` (1.9 MB), which was **not**
generation output at all: it was byte-identical (sha256 `9c28ecdc…`) to
`../results/retrieval_runs_proposed.json`. Script 05 had been silently overwriting the
generation harness's output file, so its *retrieval* rankings ended up under the
generation name. The clobbering bug is fixed and the file is removed rather than
shipped, since carrying an exact duplicate under a misleading name helps nobody; the
live copy is `results/retrieval_runs_proposed.json`. This paragraph is the record of
the bug.

## Why the study was withdrawn

The review found the generation study unreproducible — no generation endpoint was
reachable from the analysis host, so it was run by hand, single-pass, single-model —
and found the denominators in its table inconsistent (n = 16, 15 and 14 against a
stated 24). Rather than defend a study that could not be re-run, it was cut. The
paper is a retrieval paper and does not need it.
