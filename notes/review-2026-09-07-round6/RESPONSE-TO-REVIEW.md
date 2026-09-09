# Response to round-6 pre-submission review

Every blocking finding is fixed at the cause, and both leaking gates were repaired and
then tested by reproducing the reviewer's own demonstrations. `paper.md` is the authored
source; `paper_lncs.tex` and `paper_lncs.pdf` are regenerated from it, so each prose fix
below reaches all three artifacts by construction.

> **Corrected in round 7 (M20).** This paragraph originally continued "…and is checked in
> all three by `scripts/08_verify_manuscript.py`". Round 7 disproved that by mutation: of
> the three prose fixes in this pass, only the N33 baseline pair carried a binding.
> Editing "buys the last 0.038" or the +0.162 figure in `paper.md` alone left the run
> green, and there was no `paper.md` ↔ `paper_lncs.tex` numeric comparison at all. Both
> gaps are closed in round 7 (N45); the claim as written here was false when made.

Verifier after this pass: **311 bindings, 0 failures**, artifacts covered `paper.md`,
`paper_lncs.tex`, `paper_lncs.pdf`, `references.bib`, `data/raw/MANIFEST.json`.

---

## N33 — §5.2 quoted a gain against a baseline the sentence did not name — FIXED

§5.2 now reads:

> "…Giving a system the query's true defect category is worth 0.107 on top of the
> corpus-trained fusion, and 0.069 more than the strongest system in that spread reaches
> on its own, for free."

Both baselines are now named where both figures are quoted, in §2 and in §5.2, and the
binding described under N37 enforces it in every artifact.

## N34 — "it costs a 110-million-parameter encoder to cross most of it" — FIXED

The claim was false and the reviewer's arithmetic is right: MiniLM 0.1359 → Hybrid RRF
0.3025 is 0.1666 of the 0.205 spread (81.3%) with no downloaded weights; Hybrid RRF →
+ BGE is 0.0384 (18.7%). The sentence now reads:

> "…and most of it is crossed by corpus-trained channels alone; the pretrained encoder
> buys the last 0.038."

This is the reviewer's suggested wording, and it now agrees with §5.3 and with the
README's M14 text.

> **Corrected in round 7 (M20).** This sentence originally read "+0.038 is half of the
> +0.066 that fusion over BM25 alone is worth". That is wrong — 0.038 is 0.58 of 0.066.
> §5.3 says the correct thing: the interval's upper end, **+0.033**, is half of +0.066.

## N35 — the deleted superlative survived in the README — FIXED

`README.md:28` now mirrors N31's wording exactly: "…worth +0.038 (Holm p = 0.0); it is
the only pretrained dense channel added to a fusion here, so there is nothing to rank it
against." The false superlative and the missing "pretrained" qualifier are both gone.

## N36 — the shipped→promised check read only the first path segment — FIXED AND TESTED

`scripts/12_release_package.py` now enumerates **every directory prefix of every file**
plus **every top-level file**, and a directory is not documented merely because its
parent is. Re-running it immediately refused the build and named the fourteen paths the
reviewer identified — `notes/review-2026-09-07-round5/`, `data/raw/`,
`_superseded_20260907/generation_answers/`, and every top-level file including
`README.md`, `LICENSE`, `CITATION.cff`, `paper.md`, `paper_lncs.*` and `references.bib`.

`DATA_CARD.md` now documents all of them, plus `notes/review-2026-09-07-round6/`.

**Tested by reproducing the reviewer's demonstration:** adding
`notes/review-2026-09-07-round7/REVIEW.md` and a stray top-level `SCRATCH_NOTES.txt` now
refuses the build and names both. Previously it built a 75-file archive in silence.

## N37 — the "on top of X" binding read `paper.md` only — FIXED AND TESTED

The phrase loop now runs over `ARTIFACTS` — `paper.md`, `paper_lncs.tex` and the text
extracted from `paper_lncs.pdf` — and reports which artifact failed. A phrase that
appears in no artifact at all now fails too, so a rewrite cannot silently remove the
binding along with the sentence.

**Tested by reproducing the reviewer's demonstration:** swapping the two baselines inside
`paper_lncs.tex` alone, adding and removing no decimal, now produces four failures naming
`paper_lncs.tex`. Under round 5's script it produced `307 bindings, 0 failure(s)`.

---

## N38 — the range guard's acquitting pattern was too loose — FIXED AND TESTED

The old pattern `lo[^0-9]{1,3}hi` searched the whole document, so any unrelated sentence
containing both numbers a few characters apart acquitted a genuinely merged range. The
guard now folds the dash forms first and demands the exact separated range `lo-hi`; a
comma, a word or a bracket between the two numbers no longer counts.

Tested on the reviewer's own construction: "the 1215 page limit … families 12, 15 and 18
were pooled" is now flagged, while an intact `12–15` is not.

## N39 — the overfull-box block was silently skipped, and the `.bbl` rule was absolute — FIXED

Two changes. An `else` branch now prints "overfull-box check SKIPPED (paper_lncs.log
absent …)" and says which checks did still run, so the block's silence can no longer read
as a pass for anyone working from the release. And the `.bbl` rule now has a 12 pt
threshold: a bibliography URL a few points past the margin prints as a note, while the
134 pt class of defect the rule was written for still fails hard. The 3.3 pt overrun on
p23 loses no text and no longer fails a rebuild of the shipped release.

## N40 — three remaining baseline/reference phrasings — ALL THREE FIXED

- Abstract: "the best **overall** of them scores 0.193, 0.151, 0.161 and 0.024…". LSA
  reaching 0.1830 on family B is why.
- §2: "0.069 **more than the strongest system in that spread reaches on its own**", the
  reviewer's wording. `qir_oracle` is built on the `hybrid_rrf` backbone, so 0.069 is a
  difference between systems, not an increment on `hybrid_rrf_dense`. The same wording is
  now used in §5.2.
- §5.4 (mislabelled §5.5 here when written — corrected in round 7, M20): "captures
  **+0.162 nDCG@10 of that +0.277**", so the figure cannot be read as a fraction.
  **Round 7 (N42) found this fix names the wrong parent:** +0.162 belongs to
  `prefilter_hybrid`, a different system, not to a rung of the +0.277 ladder. Rewritten
  in round 7.

## N41 — the round-5 response overstated N29 by one clause — CORRECTED IN PLACE

`notes/review-2026-09-07-round5/RESPONSE-TO-REVIEW.md` carried the claim that the only
hyphenated break left in the PDF was ordinary word hyphenation of "stability". The PDF
contains dozens of ordinary hyphenated word breaks. The clause has been withdrawn in that
file, with a note saying so; the claim that matters — that no `\texttt` path is
hyphen-broken — is true and the reviewer independently verified it.

---

## Minor

- **M16** — the breakpoint threshold in `10_build_latex.py` was measured on the *escaped*
  string, so a path's length depended on how many underscores it contained. It now
  measures the visible token, at > 20 characters.
- **M17** — the em-dash opened at `paper.md:447` now closes with a dash, not a comma.
- **M18** — a trailing `\allowbreak{}` after a token's final character is now dropped, so
  `enforcement/\allowbreak{}` no longer occurs; zero such tokens remain in the `.tex`.
- **M19** — the ratio in §5.4 is now set as `(0.423 − 0.302)/(0.581 − 0.302)`, so the line
  cannot end on a bare `/`. The remaining line-final slashes in the PDF are the deliberate
  `\allowbreak` points inside long paths and one URL.

---

## On the pattern the review names

The closing instruction was "sweep for the claim, not for the location." Before rebuilding,
every corrected claim was grepped across all surfaces — `paper.md`, `paper_lncs.tex`,
`README.md`, `DATA_CARD.md`, `notes/`, `scripts/` — rather than only the file the finding
cited. That sweep is what found N35's residue in the README under a different sentence and
N40's third instance, and it is why the `.tex` occurrences of "110-million-parameter" and
"largest single gain" were confirmed gone rather than assumed gone after the rebuild.

Structurally, the two gate fixes move the guarantee from "the file the reviewer quoted" to
"every artifact a reader receives" (N37) and from "the first path segment" to "every path"
(N36). Both were verified by reintroducing the exact defect, which is the only evidence
that a gate works.

## Still open, and requiring the author rather than a rebuild

Unchanged from round 5, and not blocking arXiv: gold-set adjudication by at least two
qualified reviewers over at least 150 query–document pairs, and 20–30
investigator-written questions to sit alongside the templated ones. Acknowledged and not
fixed: M13 (Table 2 is set at roughly 64% of body type) and M15 (no DOI in
`CITATION.cff`, pending deposit).
