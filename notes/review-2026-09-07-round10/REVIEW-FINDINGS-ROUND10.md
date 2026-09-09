# GO on the paper. The manuscript is clean for the second round running — submit it. The tooling needs one pass before paper 2 inherits it.

Round-10 re-review of `quest-qi_release.zip` (85 files, 4.95 MB), extracted to
`review/round10/r10/`. Response read at `notes/review-2026-09-07-round9/RESPONSE-TO-REVIEW.md`.

**Mean rigor: 9.5 / 10** (6.4 → 7.4 → 8.3 → 8.8 → 8.9 → 9.0 → 9.1 → 9.1 → 9.4 → 9.5).

**Nothing in the manuscript blocks submission.** Every quantitative claim was recomputed
from `results/` and the processed data for the second round running, independently and
from scratch: corpus counts, taxonomy tiers, benchmark shape, all of Tables 2–5, every
per-family figure, the §5.3 accuracies and intervals, the §5.4 ratio chain, §5.5. No
arithmetic error. The only textual change since round 9 is the corrected cross-reference,
and the decimal sets in `paper.md`, `paper_lncs.tex` and the PDF are identical in both
directions.

**N59, N61, N62, N63, M33, M35, M37 all landed and do what they claim.** I verified the
two that mattered: `Reproducibility`, its intro and the listing are now together at the top
of page 22 with no furniture between them, and Table 1's `p{0.52\linewidth}` drops page 7's
maximum extent from 496.2 to 482.3 against a 480.6 pt edge — from 5 mm into the margin to
ordinary justification.

The pattern held once more, and only in the tooling. That is where the two findings below
are, and one of them I proved by mutation.

---

# SHOULD-FIX

## N64 — M36's "all four are now bound" is false for two of the four, and I proved it
**Location** `scripts/08_verify_manuscript.py:311–316`; response line 132.

> "**M36 — FIXED.** All four are now bound and recomputed: `0.182` … `79` and `81` as the
> two anchorings of the corpus-trained share"

`check()` compares a recomputed value against a **literal typed into the script**. It never
reads `paper.md`. Only `states()` searches the manuscript, and of M36's four values only
`14.4` got one.

```
$ sed -i 's/79% rather than 81%/78% rather than 82%/' paper.md
$ python3 scripts/08_verify_manuscript.py
checks run: 347 bindings, 0 failure(s)
```

The manuscript can state two wrong percentages and the gate stays green. Round 9's finding
was "these are unbound"; they are still unbound. The arithmetic itself is right —
0.3409 − 0.1592 = 0.1817 → 0.182, 100 × 0.1433/0.1817 = 78.9 → 79,
100 × 0.1666/0.2050 = 81.3 → 81 — so the paper is correct and only the guarantee is
missing.

**Fix — EDIT + rerun.** Add `states()` calls (or an `in_text()` over the surrounding
phrase) for the span and both percentages.

## N65 — The README describes `check()` as doing something it does not do, which is what hid N64
**Location** `README.md:79–83`.

> "Bound numbers — the ones named in a `check()` or a phrase binding — are recomputed from
> `results/` **and compared to what the sentence around them claims, including the baseline
> the claim names**."

`check()` compares to a hard-coded literal; nothing connects it to any sentence. This is
the same class as the last two rounds' documentation findings, and it is precisely why N64
read as covered.
**Fix — EDIT.** "…a `states()` or phrase binding is compared against the manuscript text; a
`check()` asserts a recomputed value against a literal in the script and does not read the
manuscript."

## N66 — M31's `\vbox` rule fires unconditionally, with no environment exemption, no threshold, and no source attribution
**Location** `scripts/08_verify_manuscript.py:1205–1212`.

The `hbox` path walks the log's parenthesis nesting, maps `.tex` line spans onto
`table`/`verbatim`/`figure`/`minipage`, splits `.bbl` out and applies a 5 pt floor. The
`vbox` path is a bare `re.finditer` over the whole log with none of that. A synthetic log
containing one `Overfull \vbox (2.5pt too high)` inside `(./paper_lncs.bbl …)` and one
routine `Overfull \vbox … while \output is active` produces two hard failures, both
reported as *"most likely the minipage around a verbatim listing, is running off the bottom
of the page"*. `while \output is active` is a normal page-breaking message; as written the
gate will fail rebuilds on cosmetically irrelevant output and blame the wrong construct.
**Fix — EDIT.** Run vbox matches through the same `_stack`/`_inside` machinery, exempt
`\output is active`, apply a pt floor.

## N67 — N60's DOI attribution is a bare string-prefix test
**Location** `scripts/08_verify_manuscript.py:1115`.

```python
_split = [x for x in _rest if any(y.startswith(x) and y != x for y in _src_nums)]
```
…printed as *"DOI fragment(s) left by a PDF line break"*. Any real source/PDF divergence
whose value happens to be a string prefix of some source number is labelled a DOI artifact:
`0.30` ⊂ `0.302`, `0.79` ⊂ `0.796`, `1.00` ⊂ `1.000`, `0.14` ⊂ `0.143`. The two genuine
fragments here (`10.186` ⊂ `10.18653`, `3190580.31` ⊂ `3190580.3190586`) are correct by
luck rather than by test.

The comment two lines above reads: *"an explanation that does not apply to what it explains
is the failure mode this whole file exists to prevent"* — which is what the rule does. To
be precise about my evidence: I read the rule and confirmed the mechanism; a quick
injection of my own did not reproduce it because the value I chose still occurs elsewhere
in the `.tex`. The over-breadth is visible in the expression itself.

Related, same function: with the three figure PDFs moved aside the note becomes *"0 figure
label(s); **11 DOI fragment(s)**"* — eleven genuine axis ticks reclassified. Say "figure
labels could not be identified" instead.
**Fix — EDIT.** Require the prefixed source number to be DOI-shaped (a leading `10.`, or
found inside a `\doi{}`/`url`).

## N68 — The `\needspace` hoist reverts to the pre-N59 placement under three reachable document shapes, silently
**Location** `scripts/10_build_latex.py:273–280`.

The emitter searches only the **last 7 body entries** and only for `\section`. Today it
works — `\needspace{17\baselineskip}` sits above `\section*{Reproducibility}` and the fix
holds. But: a section with four intro paragraphs falls outside the window and the directive
lands *after* the heading, which the code's own comment says "strands it at the foot of the
page"; a listing under a `\subsection` gets no hoist at all, because `\subsection` does not
`startswith("\section")` — and there is already such a case at `paper_lncs.tex:361`; and two
listings in one section leave the second unreserved. No warning is printed in any of the
three.

(`needspace` itself is fine — `\usepackage{needspace}` is at `paper_lncs.tex:25` and the
package is in TeX Live, so arXiv has it.)
**Fix — EDIT.** Search the whole body backwards for any sectioning command, stop at the
previous verbatim block, size the reservation from the actual intervening lines, and warn
when no heading is found.

## N69 — M32's folio rule is right; the README's consequence clause is not
`README.md:93` — "a bare integer is removed only when it equals the number of the page it
sits on, **so a figure label or a table cell that happens to be an integer survives**." The
premise holds and the measurement checks out (48 lines removed = 24 running heads + all 24
folios, up from 22; every named integer survives; no off-by-one — folios 2–25 all match
their counted page). But the conclusion does not follow: a table cell `17` on page 17 is
removed, and section numbers 1–9 currently sit on pages 2–21, so one page of reflow puts §8
on page 8 and it disappears.
**Fix — EDIT.** Drop the "so …" clause, or require an adjacent form feed **and** a value
match.

---

# MINOR

**M38 — the rounding question: your decline is right on the merits, and its arithmetic
under-counts.** At an exact third-decimal tie both roundings are defensible, and imposing a
house style in the verifier would enforce a convention rather than catch a changed number.
That position is sound and I withdraw the part of round 9's M34 that asked you to overturn
it. Two corrections though. My framing said "only LSA goes the other way" — wrong;
`0.3025 → 0.302` does too, exactly as you say. And your count of two is the number of
`states()` sites that hit ties, not the number of affected cells: across the manuscript the
half-up ties are 0.0095 → 0.010, 0.1235 → 0.124, 0.2835 → 0.284, 0.4935 → 0.494,
0.7825 → 0.783, and the half-down ties are 0.2995 → 0.299, 0.3025 → 0.302 (×16),
0.4165 → 0.416, 0.5205 → 0.520. **Table 2 alone rounds three ties up and three down.** A
copy editor will ask. One sentence in the Table 2 caption stating the convention settles
it; changing cells is not necessary.

**M39 — the tie-acceptance branch skips the cross-artifact check.** `:449–450` is an
`elif` chain: when the paper uses the other rounding of a tie, `txt` is reassigned and
`in_all_artifacts()` is never called, though the comment names an artifact check. The
branch never fires in this build, so `f3()`'s single call site is real but the
accept-either behaviour is untested.

**M40 — `README.md:96` overstates the vbox rule** ("any unbreakable block running off the
bottom of the page") — per N66 it fails on any overfull vbox, breakable or not, in any
file, at any size. **M41 — `README.md:86` keeps a stale rationale**: it says the reverse
direction cannot be enforced partly because the PDF carries `.bbl` text, but N60 now adds
the `.bbl` decimals to the source set.

**M42 — a note, not a defect:** page 21 now ends with a ~140 pt white gap at its foot. With
a 16-line unbreakable block and about 14 lines left on the page the break is unavoidable —
flagged only so it is not a surprise.

---

# Verified clean

**N60 works as far as its inputs go** — the reverse comparison now sources from `.tex` +
`.bbl` and the note drops from 28 to 15, with `5.1` disappearing entirely. **M32, M33,
M35, M37** all verified. **M36's escape fold is load-bearing and safe**: the `.tex` carries
28 `\%` and 35 `\_` and zero `\&`/`\#`/`\$`, no control sequence is corrupted, disabling it
produces exactly one new failure, and it does not touch the decimal comparison. Mutating
`14.4%` fails correctly.

**Page-by-page r9 → r10:** 25 pages both; pages 1–3, 5–6, 8–20, 24–25 byte-identical.
Page 4 is the cross-reference fix, page 7 the Table 1 reflow (no split, no truncation),
pages 21–23 the `\needspace` shift. No orphaned heading, no widow, no table split, no
figure separated from its caption.

**DATA_CARD** digests and sizes all verify, the notes list matches the directory exactly,
`12_release_package.py` enforces 27/27 promised paths, and the `.bbl` bullet now agrees
with `.gitignore`.

---

# Verdict

**Send the paper.** Ten rounds in, the manuscript has been clean twice running on a full
independent recomputation, the typesetting defects are gone, the archive is built by its own
release script and complete in all three directions, and the bibliography is correct. There
is nothing left in the paper that a reviewer would catch and nothing I would hold submission
for.

The tooling is a separate matter, and it is worth one pass before paper 2 inherits it —
N64 and N65 especially, because together they are the failure this whole exercise has been
about: a guarantee asserted in prose, absent in code, and invisible because the prose
described the code inaccurately. I changed two percentages in your abstract's own section
and 347 bindings did not notice.

Ten rounds is a lot, and it is worth saying what they bought. The first three found things
that would have embarrassed the paper — a hidden macro-average that reversed a headline, a
missing disclaimer, a novelty claim the literature refutes. The last four found nothing in
the paper at all; they found claims about the paper that were not true, in responses, in
READMEs, and in the checks themselves. That migration is the actual result here: the
manuscript is now the most reliable artifact in the repository, and the things describing
it are the least. If you carry one habit into papers 2 through 10, make it the one your
round-9 response wrote down — a sentence describing what the tooling does is a claim, and
gets checked like one.
