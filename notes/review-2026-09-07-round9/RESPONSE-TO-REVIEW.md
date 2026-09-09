# Response to round-9 pre-submission review

Nine rounds in, the manuscript passed clean: every quantitative claim recomputed from
`results/`, no wrong number and no wrong referent. All five should-fixes and all seven
minors are addressed below. One of them, M34, I am answering rather than implementing, and
the reason is given in full.

Verifier after this pass: **347 bindings, 0 failures**.

---

## N59 — the minipage cured the split listing by orphaning its heading — FIXED

Correct, and it is the same class as N51 by the standard round 8 set. The block was
wrapped but the heading was not, so `Reproducibility` and its one-line intro were left at
the foot of p21 under seven lines of white while the listing opened p22 under the running
head.

`scripts/10_build_latex.py` now emits `\needspace{n\baselineskip}` for the whole group.
The first attempt put it at the listing's own position and changed nothing — LaTeX honours
the reservation after the heading is already set — so the emitter **hoists it above the
nearest preceding `\section` command**. Heading, intro and listing are now together on one
page with no furniture between them.

**Tested:** removing the `\needspace` from the `.tex` and recompiling reproduces the
orphaned heading exactly as reported.

The observation that there is exactly one `\begin{verbatim}` in the manuscript is right,
and the loop is written for a block of one. It stays a loop because the converter emits it
per fenced block and a second one would otherwise be unguarded.

## N60 — the reverse-comparison note explained 16 of 28 divergences with the wrong cause — FIXED

This is the ninth instance of the pattern and the diagnosis is exact: **N53 taught the
range check about the `.bbl` at line 1240 and N56's comparison at line 1023 was not told.**

Three changes. The comparison now takes its source set from `paper_lncs.tex` **and**
`paper_lncs.bbl`. The figure labels are no longer assumed — the script reads
`figures/*.pdf` and identifies which extras actually come from there. And what remains is
attributed to the cause it has rather than to a guessed one: a value that is a prefix of a
longer source number is named as a DOI fragment left by a PDF line break.

The note now reads:

> 15 number(s) appear in the compiled PDF but not in paper_lncs.tex or paper_lncs.bbl: 13
> figure label(s) …, drawn by figures/gen_figures.py from results/ and checked there; 2 DOI
> fragment(s) left by a PDF line break (['10.186', '3190580.31']).

28 → 15, and every one of the 15 is now attributed correctly. `5.1` disappeared entirely
once the `.bbl` and the LaTeX-escape folding below were in place.

## N61 — the `.bbl` bullet asserted the opposite of `.gitignore` — FIXED

M30 documented the file and got it backwards. `DATA_CARD.md` now says `.gitignore`
excludes the other LaTeX build artifacts but deliberately keeps this one, and says why,
which is what the `.gitignore` comment itself says.

## N62 — the README stated the body-prose gate as unconditionally active — FIXED

`*.log` is excluded from the archive, so for a reader of the release the gate does not run.
The README now says the margin and page-bottom checks are hard failures **when
`paper_lncs.log` is present** — after a `--compile` build — and that the log is not in the
archive, so those three checks do not run for someone who only unpacks it, and the script
says so rather than passing in silence.

## N63 — Table 1 overhung the right margin by 14.2 pt — FIXED

An `l` plus an `r` plus `0.62\linewidth` exceeds `\linewidth`, and the tabular was not in a
`\resizebox`, so the booktabs rules and eleven cell lines ran 5 mm into the margin. The
long-prose column is now `p{0.52\linewidth}`.

**Measured after the rebuild:** p7's maximum word extent drops from 496.2 to 482.3 against
a text-block edge of 480.6 — from +15.2 pt to +1.7 pt, which is ordinary
justification. The only remaining overruns in the document are the verbatim listing
(+35.9 pt, acknowledged) and the bibliography (+3.3 pt, under the 5 pt threshold).

The review is right that the verifier was designed never to report this, and the fix for
that is M31's second half below.

---

## Minor

**M31 — the minipage created a failure mode nothing checked. FIXED AND TESTED.** A
`minipage` cannot break, so a listing taller than the text block runs off the page bottom,
which pdfTeX reports as `Overfull \vbox` — a form the log parser never looked for. N51 had
traded a visible defect for an invisible one. The parser now reads `\vbox` overruns and
fails on them. **Tested** by injecting a synthetic 23.5 pt overfull vbox into the log: one
failure, named. The two messages that still said "a table or verbatim block" now say "a
table, figure, minipage or verbatim block", which is what the safe list has contained since
M26.

**M32 — the folio rule both under- and over-stripped. FIXED AND TESTED.** Adjacency was
the wrong test, and the review's suggestion is the right one: a folio is not a number near
a page break, it is **the number of the page it sits on**. The strip now counts pages by
form feed and removes a bare integer only when it equals the current page number. That
makes both errors impossible rather than unlikely. **Measured:** 48 lines removed — 24
running heads and all 24 folios, up from 22 — every one of the sixteen named integers
survives, and the bare integers still standing are section numbers and figure labels, which
is correct. The README no longer says "folios stripped" without qualification.

**M33 — the running-head check had four latent holes. FIXED.** `find()` took the first
occurrence document-wide; the search is now over whole lines, the last line is located
**forward from** the first, and the two paths that used to `continue` in silence now print
a note saying the check was skipped and which block it was skipped for.

**M34 — I am not making this change, and here is why.** The observation is right: the paper
writes 0.284, 0.494, 0.010 and 0.783 (half-up) but 0.299 for LSA. What the finding misses
is that `hybrid_rrf`'s 0.3025 is the same kind of tie and also rounds the other way — so
routing `states()` through `f3` does not change one cell, it changes **two**, and the second
is `0.302`, which appears sixteen times in the manuscript and inside a phrase binding.

More to the point, the position the review is asking me to overturn is already stated, at
`08_verify_manuscript.py:447`: *"Several stored values are exact ties at the third decimal
… At a tie both 0.302 and 0.303 are correct, so a string binding would enforce a rounding
house style instead of catching a changed number."* The stored value is itself a rounding
to four decimals, so the third decimal of a tie is genuinely ambiguous and neither form is
wrong.

What **was** a real defect is the one the finding uncovered on the way: `f3()` had zero call
sites, so its docstring asserted a convention the script did not apply — documentation
describing behaviour that does not exist, which is precisely this round's theme. It now has
one call site, and it is used to **accept** rather than to impose: `states()` passes if the
paper writes either correct rounding of a tie, and says so in the failure message when it
writes neither.

**M35 — FIXED.** `paper.md:186` said "our Table 2 (Section 5.4)"; Table 2 is in Section 5.1.
Corrected there and, by regeneration, in the `.tex` and the PDF. The second site the finding
cites (`:740`) carries no cross-reference — it says "any system in Table 2", which is
correct — so there was one instance, not two.

**M36 — FIXED.** All four are now bound and recomputed: `0.182` as
`hybrid_rrf_dense − w2v`; `79` and `81` as the two anchorings of the corpus-trained share;
and `14.4%` from `events.jsonl` as the share of events whose initiation year differs from
the report year — 14.38%, which is what the review computed independently.

Adding the last of those exposed a further extraction gap worth recording: LaTeX escapes the
five specials, so the `.tex` carries `14.4\%` where `paper.md` and the PDF carry `14.4%`,
and `strip_markup`'s control-sequence rule could not remove it — none of `% & # _ $` is
alphabetic. Any binding phrase or value containing one could never match the `.tex`
artifact, which is the same trap N54 found with quotes and now has the same fix.

**M37 — FIXED.** The extra "and" is gone and the list carries rounds 1–9.

---

## On what the review says about where the errors now live

The closing observation is the useful one and it is worth stating as a conclusion rather
than a compliment: the manuscript stopped being the weak point, and **four of this round's
five should-fixes are documentation asserting something the package does not do** — the
`.bbl` bullet, the margin gate, the reverse-comparison note, and `f3()`'s docstring. That
is the same class as every earlier round, applied to a different surface.

The concrete consequence for how this repository is maintained: **a sentence describing what
the tooling does is a claim, and gets checked like one.** The note that explains the reverse
comparison now derives its explanation from the files rather than asserting it, which is why
it could be corrected from 28-with-a-wrong-cause to 15-each-attributed without anyone
noticing the difference by reading.

## Still open, and requiring the author

Unchanged: gold-set adjudication by at least two qualified reviewers over at least 150
query–document pairs, and 20–30 investigator-written questions. Acknowledged and not fixed:
M13 (Table 2 at roughly 64% of body type) and M15 (no DOI in `CITATION.cff`, pending
deposit).
