# Response to round-10 pre-submission review

GO on the paper. This response addresses the tooling pass, which is the part that matters
now, because paper 2 inherits it.

Verifier after this pass: **350 bindings, 0 failures**.

---

## N64 — "all four are now bound" was false for three of the four — FIXED AND TESTED

The reviewer is right, and the demonstration is the correct one: `check()` compares a
recomputed value against a **literal typed into the script**. It never reads `paper.md`.
Editing "79% rather than 81%" to "78% rather than 82%" left the run green.

Round 9's M36 response said "all four are now bound and recomputed", and only `14.4` had a
`states()`. The other three had arithmetic proofs and no text binding, which is not the
same thing and I described it as if it were.

Added: `states()` for the 0.182 span and `in_text()` over the exact phrase `79% rather
than 81%`, which binds both percentages to the recomputed values rather than to a literal.

**Tested with the reviewer's own mutations, `paper.md` only, no rebuild:**

| mutation | before | after |
|---|---|---|
| `79% rather than 81%` → `78% rather than 82%` | 0 failures | **1 failure** |
| `0.182 that remains above` → `0.192` | 0 failures | **3 failures** |

## N65 — the README described `check()` as doing something it does not — FIXED

This is why N64 read as covered, including to me. The README said bound numbers are
"recomputed from `results/` **and compared to what the sentence around them claims**",
which is true of a phrase binding and false of a `check()`.

Rewritten to separate the two guarantees explicitly: a `check()` proves the arithmetic and
does not read the manuscript at all; a `states()`, `in_text()` or phrase binding is matched
against the manuscript text; and a claim is covered end to end **only when both are
present**. That last sentence is the one that would have made N64 visible on a read.

## N66 — the `\vbox` rule was bolted on outside the machinery — FIXED AND TESTED

Correct on every count. M31's rule was a bare `re.finditer` over the whole log, with no
source attribution, no environment map, no threshold, and a message that blamed the
minipage for every match — including `while \output is active`, which is routine
page-breaking output. As written it would have failed ordinary rebuilds and named the wrong
construct.

Vertical overruns are now collected in the same parenthesis walk as the horizontal ones,
carrying their source file and line, and judged on the same terms: routine page-breaking
messages are excluded, the 5 pt floor applies, and a box inside a float or table is
measured against that box.

**Tested on the reviewer's synthetic log** — one 2.5 pt vbox inside `(./paper_lncs.bbl …)`
and one `while \output is active` — which now produces a note and **0 failures**, where
before it produced two hard failures with the wrong explanation. A synthetic 48 pt vbox in
the `.tex` still fails, naming the file.

## N67 — the DOI attribution was a bare string-prefix test — FIXED AND TESTED

`any(y.startswith(x))` labels any divergence that happens to prefix a source number as a
DOI artifact. The two genuine fragments were right by luck, and the comment two lines above
says exactly why that is unacceptable. The prefixed number must now be DOI-shaped.

| value | old rule | new rule |
|---|---|---|
| `0.30` (⊂ `0.302`) | DOI fragment | not claimed |
| `1.00` (⊂ `1.000`) | DOI fragment | not claimed |
| `0.14` (⊂ `0.143`) | DOI fragment | not claimed |
| `10.186` (⊂ `10.18653`) | DOI fragment | DOI fragment |
| `3190580.31` | DOI fragment | DOI fragment |

The related half is fixed too: with the figure PDFs unreadable the note now says "figure
labels could not be identified (n figure PDF(s) found, none readable), so any axis tick
below is unclassified rather than unexplained" instead of reporting "0 figure labels" and
reclassifying eleven genuine axis ticks. **Tested** by moving the figures aside.

## N68 — the `\needspace` hoist reverted silently under three reachable shapes — FIXED

It searched the last 7 body entries and only for `\section`. It worked here by coincidence
of layout. The emitter now searches the whole body backwards for **any** sectioning
command including `\subsection` (the manuscript already has a listing under one), stops at
the previous listing so two blocks in one section do not both reserve from the same
heading, sizes the reservation from what actually intervenes rather than a fixed
allowance, and prints a note when there is no heading to hoist above.

The rebuilt `.tex` carries `\needspace{16\baselineskip}` immediately above
`\section*{Reproducibility}`, and heading, intro and listing remain together.

## N69 — the folio rule is right; the consequence clause was not — FIXED IN BOTH

The reviewer is right that the conclusion does not follow from the premise: a table cell
`17` on page 17 is removed, and one page of reflow would put section 8 on page 8.

Rather than only softening the sentence, the rule now requires **both** conditions — the
value equals the page number **and** the line sits at a page boundary (its own line carries
the form feed, or one is within three non-blank lines). Together, those are what a folio
is.

**Measured:** 47 lines removed — 24 running heads and 23 folios, which is all of them
(page 1 carries none). Every one of the sixteen named integers survives, and the bare
integers still standing are section numbers `1`, `2`, `3`, `29` and the figure labels —
including `2` and `3`, which match their page numbers and survive because they are not at
a boundary. That is the case the old rule got wrong. The README now states the two-part
rule instead of the false consequence.

---

## Minor

**M38 — accepted, and the arithmetic correction is taken.** My count of two was the number
of `states()` sites that hit ties, not the number of affected cells; across the manuscript
the half-up ties are 0.0095, 0.1235, 0.2835, 0.4935 and 0.7825, and the half-down ties are
0.2995, 0.3025 (×16), 0.4165 and 0.5205. Table 2 alone rounds three ties up and three
down, and a copy editor will ask. Table 2's caption now says so:

> "Cells are the four-decimal values in `results/retrieval_results.json` displayed to
> three; several sit exactly on a half, where either rounding is correct and this table
> uses both, so read a third-decimal difference of one unit as a display artifact rather
> than a result."

No cells changed, which was the reviewer's own recommendation once the position was
withdrawn.

**M39 — FIXED AND TESTED.** The `elif` chain meant the accept-either branch reassigned
`txt` and never called `in_all_artifacts()`, so the comment named an artifact check that
did not run on that path. Restructured with an early return on genuine failure. **Tested**
by adding a temporary `states()` on a tie the paper writes the other way (0.2835 → the
paper's 0.284): the cross-artifact count rises, and removing `0.284` from the `.tex`
artifact produces the expected failure. The branch is no longer untested.

**M40, M41 — FIXED.** The README's vbox sentence now matches N66's actual rule, and the
stale rationale is gone: the source side of the PDF comparison is named as `.tex` **and**
`.bbl`, with the figures and the occasional line-split DOI as what remains after both.

**M42 — noted, no action.** The ~140 pt gap at the foot of page 21 is the unavoidable
consequence of a 16-line unbreakable block with about 14 lines left on the page. Recorded
here so it is not a surprise.

---

## On what ten rounds bought

The review's closing observation is the right one to end on, and it is worth restating as a
finding rather than a compliment: the first three rounds found things that would have
embarrassed the paper, and the last four found nothing in the paper at all — they found
claims *about* the paper that were not true, in responses, in READMEs, and in the checks
themselves.

N64 and N65 are the clearest instance in the whole series, and they are mine: I wrote "all
four are now bound", the prose describing the verifier said a `check()` compares against
the manuscript, and between them the gap was invisible to a reader and to me. The fix is
not only the two bindings; it is that the README now states which kind of binding proves
which thing, so the next gap of this shape is legible from the documentation rather than
only from a mutation test.

Carried into papers 2 through 10: **a sentence describing what the tooling does is a claim,
and gets checked like one** — and a coverage claim is not established until the defect it
claims to catch has been reintroduced and caught.

## Still open, and requiring the author

Unchanged and not blocking submission: gold-set adjudication by at least two qualified
reviewers over at least 150 query–document pairs, and 20–30 investigator-written questions.
Acknowledged and not fixed: M13 (Table 2 at roughly 64% of body type) and M15 (no DOI in
`CITATION.cff`, pending deposit).
