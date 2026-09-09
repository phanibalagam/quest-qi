# Response to round-7 pre-submission review

Every finding is addressed. `paper.md` is the authored source and the `.tex` and PDF are
regenerated from it; where a claim is enforced across artifacts, this response says which
binding does it and how that binding was tested. Nothing here asserts coverage that was
not demonstrated by mutation.

Verifier after this pass: **318 bindings, 0 failures**, over `paper.md`, `paper_lncs.tex`,
`paper_lncs.pdf`, `references.bib`, `data/raw/MANIFEST.json`.

---

## N42 — §5.4 named the wrong parent for +0.162 — FIXED

The reviewer is right, and the arithmetic confirms it: `prefilter_hybrid` is 0.4644, a
different system with a hard prefilter and no defect prior, and its +0.162 is measured
over the 0.302 baseline, not carved out of the +0.277 ladder (which decomposes as 0.121 +
0.156). The sentence now reads:

> "A conventional filter-then-search system … is worth +0.162 nDCG@10 over the same 0.302
> baseline — more than the +0.121 the constraint channel inside the reported configuration
> is worth on its own. It is a different system rather than a rung on that ladder: it
> prefilters hard and carries no defect prior. We report the whole ladder rather than the
> top of it, because the configuration we propose has to clear a system that needs no
> query understanding at all."

This takes the reviewer's second observation as well — that 0.162 > 0.121 is the more
interesting point and was lost by the wrong framing.

## N43 — the abstract credited 0.579 to metadata filtering alone — FIXED

Abstract and `README.md` now read: "Adding a defect-category prior to a filter over the
metadata the question names raises nDCG@10 to 0.579 (the metadata filter alone reaches
0.464)". §1 and the conclusion are left as they were, for the reason the review gives:
both say "representing the question's structure", which includes the prior.

## N44 — "for free" with no oracle caveat in §2 and §5.2 — FIXED

Both sites now carry it. §2: "— an oracle over one component of the gold predicate, not an
obtainable signal (Section 5.4)." §5.2 keeps "for free" and then qualifies it: "though
'given' is the operative word: this is an oracle over one component of the gold predicate,
not an obtainable signal, and Section 5.4 is about what that distinction costs."

## N45 — two of three round-6 prose fixes carried no binding — FIXED AND TESTED

The review's mutation table was reproduced, and it was right. Three things changed.

**Two new phrase bindings**, each tying a figure to the contrast its own sentence names,
recomputed from `results/`:

- `buys the last (\d\.\d{3})` = `hybrid_rrf_dense − hybrid_rrf` = 0.038
- `is worth \+(\d\.\d{3}) nDCG@10 over the same 0\.302 baseline` = `prefilter_hybrid −
  hybrid_rrf` = 0.162
- `more than the \+(\d\.\d{3}) the constraint channel` = `slots_only − hybrid_rrf` = 0.121

**A `paper.md` ↔ `paper_lncs.tex` numeric comparison**, in both directions, which did not
exist. The review is right that there was none: coverage ran `.tex` → PDF only, so the
authored source could diverge from the artifact silently.

**Mutation results after the fix**, each editing `paper.md` alone with no rebuild:

| mutation | before | after |
|---|---|---|
| `buys the last 0.038` → `0.048` | 0 failures | **1 failure** |
| `is worth +0.162 nDCG@10` → `+0.192` | 0 failures | **2 failures** |
| `more than the +0.121` → `+0.151` | — | **1 failure** |
| `word2vec, 0.159` → `0.149` (an unbound number) | 0 failures | **1 failure** (md ↔ tex) |

The README's and DATA_CARD's claims are rewritten rather than merely corrected, because
"catches a number edited in one artifact and not another" was doing two jobs. The README
now separates the two guarantees — bound numbers are recomputed from `results/` *and*
checked against the baseline their sentence names; every other decimal gets a set
comparison in both directions between all three artifacts — and states plainly what the
script does not do: verify a decimal no binding names.

## N46 — the range guard still acquitted document-wide — FIXED AND TESTED

Round 6 tightened the needle and left the search global, which is the half that mattered.
The check is now **count-based**: every occurrence of a range in the `.tex` must survive as
a separated range in the PDF, so losing one of two copies fails even though the other is
intact. Counting also sidesteps the offset problem — the two strings are normalised
differently, so positions cannot be aligned — and removes the false-positive exposure,
since an unrelated `[12]` is no longer evidence of anything.

**Tested** on the review's own construction: merging one of the two `0.46--0.53` sites now
reports "occurs 2 time(s) in paper_lncs.tex but survives as a separated range only 1
time(s) in the PDF". All 15 ranges pass unmutated.

## N47 — the phrase gate fired only when a phrase was gone from all artifacts — FIXED AND TESTED

It now requires the phrase in **every** artifact and names which one is missing.

**Tested:** removing "on top of the corpus-trained fusion" from `paper.md` alone fails and
names `paper.md`; removing it from `paper_lncs.tex` alone (a stale artifact against a fixed
source) fails and names the `.tex`.

`T1_LIGATURES` gains `\x16` (em-dash) and `\x10`/`\x11` (curly quotes). The review is right
that this mattered more once N47 landed: an unmatchable phrase is now a failure rather than
a silent pass.

Two related extraction problems surfaced while testing this, both fixed:

- LNCS injects a running head and page number between pages, so a sentence spanning a page
  break extracted as "…over the same 0.302 baseline **When the Benchmark Answers Itself
  17** more than the +0.121…". The §5.4 sentence does exactly this. Page furniture is now
  stripped before the PDF becomes an artifact.
- The verbatim-truncation check ran against the default `pdftotext` extraction, which
  reflows a block that overhangs the text block into separate runs — indistinguishable from
  truncation. It now runs against the `-layout` extraction, which preserves the block. This
  surfaced as four false failures when the manuscript grew by eight lines and the block
  repaginated; the lines are present and whole in the PDF.

## N48 — the SKIPPED branch dropped the coverage caveat — FIXED

The table and verbatim coverage summary belonged to checks that run whether or not the log
exists, and is now printed outside the branch, with both the "no numeric cells" caveat and
the verbatim check named. Each branch now says only what it actually determined.

## N49 — the `.bbl` threshold was 3.6× the defect it was sized for — FIXED

Lowered to **5 pt**, and the note no longer asserts "no text is lost" as a measurement: an
overfull hbox reports overhang, not truncation, and the note now says that instead.

**The related observation is the more important one and is also fixed.** `if _prose:` had
always been a `print`, never a `fails.append`, so a body-prose overrun of any size passed —
including the 83 pt path overrun round 4 found by reading the PDF rather than the gate.
Body prose now fails at the same 5 pt threshold, with a note below it. The current build
has no prose overruns, so this changes no verdict today; it removes a rule that could
never have fired.

---

## Minor

- **M20** — all three inaccuracies corrected in place in
  `notes/review-2026-09-07-round6/RESPONSE-TO-REVIEW.md`, each marked as a round-7
  correction rather than silently edited: "+0.038 is half of +0.066" (it is 0.58; §5.3
  correctly says **0.033** is half of 0.066), the §5.5/§5.4 mislabel, and the opening
  "checked in all three" claim, which N45 disproved.
- **M21** — §6 now says "the ratio is of gains over the 0.302 baseline, not of the scores
  themselves", so 0.579/0.823 = 0.70 cannot be mistaken for the 0.53.
- **M22** — §5.2 now says which framing: "The foot of that spread is itself a pretrained
  encoder; measuring instead from the weakest corpus-trained channel (word2vec, 0.159),
  corpus-trained channels still cross 0.143 of the same 0.205 span, 70% rather than 81%, so
  the claim holds under either framing."
- **M23** — breakpoints are now placed only where **both** sides have at least 8 visible
  characters, measured on the unescaped token. `BAAI/bge-base-en-v1.5` and the first
  separator of `data/raw/MANIFEST.json` no longer get one; `unswept_hyperparameters` keeps
  its single breakpoint at exactly the 8-character bound, which is the review's own number.
  The blanket `.replace()` is gone, so M18's trailing-breakpoint class cannot recur by
  construction rather than by a special case.
- **M24** — `notes/review-2026-09-07-round6/` now has a README, and its findings file is
  renamed `REVIEW-FINDINGS-ROUND6.md`. Round 5's README no longer calls itself the final
  round.
- **M25** — not reconciled, because they are not the same computation: the pool sweep
  re-selects lambda on dev at every pool size and at pool = 300 lands on a neighbouring grid
  point. Both round to 0.53, the only form either takes in the paper. Documented in
  `DATA_CARD.md`, and the verifier now bounds the gap at 0.0005 so it cannot widen into the
  second decimal unnoticed.

---

## On the pattern

The review's refinement is right and it is the one this round demonstrates against itself:
round 6's fix removed an ambiguity and introduced a wrong referent, because the check
applied was "is this sentence clearer than the one it replaced" rather than "does this
number belong to the computation it names".

The verifier now enforces that distinction for four claims — the two oracle gains, the
encoder gain and the prefilter gain — by binding each figure to the contrast its own
sentence names, in every artifact. That is a small number, and the honest statement is that
it covers the four wrong-referent claims found so far, not the class. The README now says
so. What is genuinely general is the set comparison in both directions across all three
artifacts, which is new this round and which no longer lets the authored source and the
shipped artifact disagree about any decimal at all.

## Still open, and requiring the author

Unchanged: gold-set adjudication by at least two qualified reviewers over at least 150
query–document pairs, and 20–30 investigator-written questions alongside the templated
ones. Acknowledged and not fixed: M13 (Table 2 at roughly 64% of body type) and M15 (no DOI
in `CITATION.cff`, pending deposit).
