# The paper is clean. For the first time in nine rounds I recomputed every number and found nothing wrong.

Round-9 re-review of `quest-qi_release.zip` (82 files, 4.93 MB), extracted to
`review/round9/r9/`. Response read at `notes/review-2026-09-07-round8/RESPONSE-TO-REVIEW.md`.

**Mean rigor: 9.4 / 10** (6.4 → 7.4 → 8.3 → 8.8 → 8.9 → 9.0 → 9.1 → 9.1 → 9.4).

**No blocking finding in the manuscript.** Every quantitative claim was recomputed from
`results/`: the new abstract parenthetical (`slots_only` 0.4231 → 0.423, `prefilter_hybrid`
0.4644 → 0.464, `qir_centroid_slots` 0.5793 → 0.579), N58's 0.143 / 0.182 / 79%, all eight
Table 4 deltas, all six Table 5 rows, the 0.532 ratio, the 0.434 mechanism-exact pair, the
0.24 pessimism gap, 14.4% recomputed from `events.jsonl` at 14.38%, and the family-E
figures. No wrong number and no wrong referent. That is the first time.

**N50 and N51 are both fixed**, and I verified N51 the way it should be verified — the
listing is contiguous at lines 1093–1103 of the extracted text with no running head inside
it, and running the round-9 verifier against the round-8 PDF produces the intended hard
failure.

What remains is one typesetting defect and three documentation statements that are false.
All edits, no rerun.

---

# SHOULD-FIX

## N59 — The minipage cured the split listing by orphaning its heading
**Location** `scripts/10_build_latex.py:256`; `paper_lncs.tex:413`; PDF p21/p22.

Page 21 now ends:

```
Reproducibility
Run in order; each script writes JSON into results/.
```

…and page 22 opens with eleven lines of code directly under the running head, with no
heading and no introduction above them. Page 21 dropped from 41 non-blank lines in round 8
to **34** — roughly seven lines of added white — because the minipage cannot break and
pushed the whole block over.

By the standard round 8 applied ("a running head set inside a listing is a copy-editing
reject"), a visibly stretched page with a section heading stranded from the listing it
introduces is the same class of defect. The block itself is fine — 11 lines against a
572 pt text block, so no overflow risk today.

Also worth noting: there is exactly **one** `\begin{verbatim}` in the manuscript, so
"every verbatim block" is a block of one.

**Fix — EDIT + rebuild.** Put the heading and its intro sentence inside the same
non-breaking group as the listing, or emit `\needspace{14\baselineskip}` before the
section, so `Reproducibility` starts on page 22 with its listing.

## N60 — N56's new note explains 16 of its 28 divergences with the wrong cause
**Location** `scripts/08_verify_manuscript.py:1038`; `README.md:86–90`.

> "note: 28 number(s) appear in the compiled PDF but not in paper_lncs.tex … **Expected:
> these come from the embedded figures**"

I enumerated all 28 and checked each against the `.bbl`:

- **12 are genuine figure labels** — `0.2 0.4 0.57 0.59 0.6 0.60 0.67 0.71 0.76 0.78 0.8
  0.81`, all present in `pdftotext figures/fig*.pdf`.
- **15 are in `paper_lncs.bbl`** — `10.1007 10.1038 10.1145 10.1162 10.186 10.18653
  290941.291014 1008992.1009000 1277741.1277820 2009916.2010058 2484028.2484063
  3077136.3080832 3190580.31 3626772.3657942 1.2` — DOI fragments, two of them split by a
  PDF line break.
- **1 is a LaTeX section number** — `5.1`, page 10.

The root cause is the pattern this review has named for nine rounds: **N53 added the
`.bbl` to the range source at line 1240; N56 did not add it to `_tex_nums` at line 1023.**
The fix landed in one place and not the other. With the `.bbl` included the extras drop
from 28 to 16.

It is benign in substance — none of it is a real source/PDF divergence — but the note and
the README sentence are both false as written, and explaining away a divergence with a
cause that does not apply to it is exactly the round-8 N51 failure mode.

**Fix — EDIT.** Include the `.bbl` in `_tex_nums` for this comparison, then reword the
note and README to name the three real causes.

## N61 — `DATA_CARD.md`'s new `.bbl` bullet asserts the opposite of `.gitignore`
`DATA_CARD.md:48`:

> "`paper_lncs.bbl` — the compiled bibliography. It is a build artifact and **`.gitignore`
> says so**, but it ships deliberately…"

`.gitignore:5–6` says the reverse, explicitly:

> "# LaTeX build artifacts. The .bbl is deliberately **NOT** here: arXiv does not run
> # BibTeX, so the compiled bibliography has to ship with the source."

M30 documented the `.bbl` and got the documentation backwards.
**Fix — EDIT.** "`.gitignore` excludes the other LaTeX build artifacts but deliberately
keeps the `.bbl`…"

## N62 — README states the body-prose margin gate as active; it never runs on the release
`README.md:92`: "…a body-prose line running past the right margin by 5 pt or more is now a
hard failure rather than a note." `.gitignore` excludes `*.log`, the log is not in the
archive, and the verifier prints `note: overfull-box check SKIPPED`. For every reader of
the release this gate is dead. Same overstatement class N56 was meant to remove.
**Fix — EDIT.** Qualify with "when `paper_lncs.log` is present (build with `--compile`)".

## N63 — Table 1 overhangs the right margin by 14.2 pt, and the verifier cannot see it
`paper_lncs.tex:136` — `\begin{tabular}{lrp{0.62\linewidth}}`. An `l` plus an `r` plus
0.62\linewidth exceeds `\linewidth`, and the tabular is not in a `\resizebox`. On page 7
the three booktabs rules run to x = 496.2 against a text-block edge of 482.0, so the rules
and eleven cell lines stick 5 mm into the margin. Identical in round 8 —
**pre-existing, not a round-9 regression** — but `table` is on the safe-environment list,
so the verifier is designed never to report it, and a Springer copy editor will.
**Fix — EDIT.** `p{0.52\linewidth}`, or wrap in `\resizebox`.

---

# MINOR

**M31 — the minipage created a failure mode nothing checks.** A `minipage` cannot break, so
a listing taller than the text block would run off the page bottom, and pdfTeX reports that
as `Overfull \vbox`, which the log parser never looks for (`:1115` matches `\hbox` only).
There is ~47 lines of headroom today, but N51 replaced a visible defect with an invisible
one. Add a `\vbox` branch. In the same edit: M26 added `figure` and `minipage` to the safe
list at `:1139` but the two messages at `:1192` and `:1197` still say "a table or verbatim
block".

**M32 — N55 no longer over-strips, but it under-strips, and over-strip is still
constructible.** 46 lines removed, all furniture, and all sixteen named integers survive —
that part is right. But only 22 of 24 folios go: pages 11 and 13 keep theirs, because
pdftotext interleaves figure text and the nearest non-blank neighbour is a bar label. No
live consequence (no `in_all_artifacts` needle is a bare integer — all 20 are decimals),
but `README.md:90` says "running heads and folios stripped" without qualification. And
adjacency is one hop, so a legitimate bare integer landing next to a page boundary still
dies — demonstrable with Table 5's `100` or fig1's `733`. Require the value to equal the
page's own number.

**M33 — N51's running-head check is correct on the real case, with four latent holes.**
`_lay.find(_first)` takes the first occurrence document-wide, so a first line that also
appears in prose widens the window across an unrelated page break; a block legitimately
containing "P. K. Balagam" or the title would fail; and both `_b < _a` and `_a < 0` fall
through to `continue`, silently skipping a real split. Anchor to whole lines, search
forward from `_a`, and make the two `continue` paths print a note.

**M34 — Table 2's LSA cell rounds against the paper's own convention.** `results/` stores
`0.2995`; the paper writes `0.299`. `f3()` at `:416` was written to fix exactly this
("0.2835 formats as 0.283 while the manuscript writes 0.284") and has **zero call sites** —
`states()` uses `"{:.3f}"`. The rest of the paper rounds half-up (0.2835 → 0.284, 0.4935 →
0.494, 0.0095 → 0.010, 0.7825 → 0.783); only LSA goes the other way. Route `states()`
through `f3` and write 0.300, or state the convention as `{:.3f}` and fix the other four.

**M35 — "Table 2 (Section 5.4)" is a wrong cross-reference, twice.** `paper.md:186` and
`:740`. Table 2 is in §5.1; §5.4's table is Table 4. The arithmetic behind the claim is
fine.

**M36 — three new §5.2 quantities are unbound.** `0.143` is bound at `:295`; `0.182`, `79`
and `81` are not, nor is `14.4%` (which I recomputed independently at 14.38%).

**M37 —** `DATA_CARD.md:24` reads "…round6/` and `…round7/` and `…round8/`" — one "and"
too many.

---

# Verified clean

**N52, N53, N54, N55, N57, N58 and M26–M30 all landed.** N53's cross-file range counting is
genuinely free of false positives — I enumerated all 26 distinct ranges across `.tex` +
`.bbl` against the normalised PDF and every one matches or exceeds its source count, the
three previously-slack cases (`1--2`, `1--174`, `333--389`) are now correctly counted, and
the ORCID contributes zero ranges since the pattern requires a real separator. N51's
truncation check is back on the default extraction and does **not** false-positive on the
overhanging block — `strip_markup`'s whitespace collapse rejoins the split runs.

**Margin profile is byte-identical between rounds 8 and 9** (16 overrunning lines each:
+33.99, +18.30 ×2, thirteen p7 table cells, +2.62, +1.39). No path is hyphen-broken;
`unswept_hyperparameters` is intact after N57.

**Number propagation r8 → r9:** two hunks, `0.423` gains an occurrence, `0.182` added,
nothing lost. md↔tex sets differ only by a markdown heading number, `p{0.62\linewidth}` and
a comment. Repagination beyond the listing is clean — no stranded heading elsewhere, no
table split, no figure separated from its caption, references numbering intact.

**Archive is complete in all three directions**, 82 files, and script 12 passes its own
checks.

---

# Verdict

**Submit after an afternoon of edits.** N59 is a `\needspace` and a rebuild; N60 is a
one-line change plus a reworded note; N61 and N62 are two sentences. N63 I would do at the
same time since a copy editor will raise it.

The thing worth marking is that the manuscript itself is now clean. I recomputed every
quantitative claim in the paper against `results/` — every ratio, difference, percentage,
"alone reaches", "on top of", "more than" — and for the first time in nine rounds there is
nothing to report. The wrong-referent class that decided rounds 6, 7 and 8 is gone, and
your own response identified the procedure that closed it: a number is not adopted until it
has been traced to the computation that produced it.

The pattern held once more, but only in the tooling: N53 taught the range check about the
`.bbl` and N56's reverse comparison was not told, so the verifier now prints a false
explanation for 16 of 28 divergences. That is the ninth instance of a fix landing on one
surface, and it is instructive that it survived into a round where the paper had none — the
manuscript is done being the weak point; the documentation about the manuscript is now
where the errors live. Three of this round's four documentation edits assert something the
package does not do.

None of that touches a result. Fix the five, rebuild, and send it.
