# NO-GO — and the blocking finding is my error, transcribed into your abstract.

Round-8 re-review of `quest-qi_release.zip` (79 files, 4.92 MB), extracted to
`review/round8/r8/`. Response read at `notes/review-2026-09-07-round7/RESPONSE-TO-REVIEW.md`.

**Mean rigor: 9.1 / 10** (unchanged from round 7). The machinery is better again; two new
defects, both introduced by round-8 fixes, cancel the gain.

**N42 is fixed and correct** — §5.4 now says +0.162 is "over the same 0.302 baseline —
more than the +0.121 the constraint channel inside the reported configuration is worth on
its own. It is a different system rather than a rung on that ladder." That is exactly
right, and it takes the second observation too.

N44, N45, N46, N47, N48, N49 and M21–M25 all landed and I could not break most of them.
Number propagation is perfect: zero decimals added, zero lost, and md−tex, tex−md, tex−PDF
and md−PDF are all empty.

Two blocking findings. The first is mine.

---

# BLOCKING

## N50 — The abstract now credits 0.579 to a filter it is not built on. My round-7 wording was wrong and you transcribed it.
**Location** `paper.md:44–45`; `paper_lncs.tex:55`; `README.md:32–33`; PDF page 1.

> "Adding a defect-category prior to a filter over the metadata the question names raises
> nDCG@10 to 0.579 **(the metadata filter alone reaches 0.464)**"

**This is my mistake.** Round 7's N43 told you to write "metadata filtering alone reaches
0.464", picking the wrong one of the two numbers I had listed in the same finding. You
transcribed it faithfully. It is still wrong, and it is now on page 1.

From `scripts/05_taxonomy_aware_retrieval.py`:

| line | system | nDCG@10 |
|---|---|---|
| `:390` | `slots_only = rank_with_prior(None, use_slots=True)` — the **soft** filter | **0.4231** |
| `:391` | `prefilter_hybrid = rank_prefilter()` — **hard** prefilter, no prior | 0.4644 |
| `:379` | `qir_centroid_slots = rank_with_prior(centroid_prior, use_slots=True)` | **0.5793** |

0.579 is the centroid prior added to the **soft** filter. Strip the prior and you get
**0.423**, not 0.464 — and the paper's own `channel_ablations` names that contrast
explicitly: *"defect prior on top of constraints (qir_centroid_slots − slots_only)"* =
**0.1562**. The abstract's parenthetical implies the prior is worth 0.579 − 0.464 =
**0.115**.

Worse, it contradicts the sentence N42 was rewritten to produce, four sections later
(`paper.md:696`): *"It is a **different system rather than a rung on that ladder**: it
prefilters hard and carries no defect prior."* The abstract presents 0.464 as precisely
the rung §5.4 says it is not.

**Fix — EDIT + rebuild.** "…raises nDCG@10 to 0.579 (the soft metadata filter alone
reaches 0.423; a hard prefilter with no defect prior reaches 0.464)". Same in
`README.md`. And add a fourth N45-style binding — `metadata filter alone reaches
(\d\.\d{3})` → `slots_only` — because `in_all_artifacts` only checks that the string
"0.464" appears somewhere, which is why 318 bindings did not notice.

## N51 — The code listing now breaks across pages 21/22 with the running head set inside it, and the round-8 fix silenced the signal
**Location** PDF p21/p22; source `paper_lncs.tex:413–425`.

`pdftotext -layout` of the shipped PDF, mid-listing:

```
scripts/05_taxonomy_aware_retrieval.py    # query understanding + controls
scripts/08_verify_manuscript.py           # re-checks every number here
22        P. K. Balagam

scripts/10_build_latex.py              # .md -> .tex; --compile builds the PDF
```

Round 7 has all eleven lines on one page. The lines added in §5.2 and §5.4 this round
repaginated the block.

The response records this event and reads it the other way (`RESPONSE-TO-REVIEW.md:108`):
*"four false failures when the manuscript grew by eight lines and the block repaginated"*
— and switches the truncation check to `-layout` extraction so the failures stop. **They
were not false.** The check was reporting a real repagination defect in a form that looked
like a false positive. The change converted a true signal into silence rather than fixing
the page. A camera-ready code listing broken by a page header and a folio is a
copy-editing reject at LNCS.

**Fix — EDIT + rebuild.** Wrap the listing so it cannot break — `\begin{figure}[!ht]`
around the `verbatim`, or a `minipage` — or shorten it by two lines. Then re-check the
p21/p22 boundary.

---

# SHOULD-FIX

## N52 — N46's count-based range guard introduced a false-positive class round 7 did not have
`scripts/08_verify_manuscript.py:1136–1161`. `_pdf_norm` is the **raw, newline-bearing**
extraction and the needle demands the two numbers be adjacent, but TeX may break a line
after an en-dash. Injecting `0.46\x15\n0.53` at one of the two sites produces:

> "FAIL: the range 0.46--0.53 occurs 2 time(s) in paper_lncs.tex but survives as a
> separated range only 1 time(s) in the PDF … **so two numbers have merged into one wrong
> one**"

Nothing merged. Round 7's version could not produce this, because it also required the
merged token to be present. Given N51 shows this manuscript does repaginate, this will fire
spuriously — and its message asserts a data corruption that did not happen.
**Fix:** collapse whitespace in `_pdf_norm` and search `lo-\s?hi`.

## N53 — N46 still acquits a real merge at three of the ten distinct ranges
Enumerated all 15 `\d--\d` occurrences against the PDF: `1--2` counts 2 in the tex and 3 in
the PDF, `1--174` 1 against 2, `333--389` 1 against 2. The slack comes from the BM25
disclaimer note, which writes those ranges with a literal U+2013 that the `--` regex on the
tex side never counts but the PDF side does. Confirmed by mutation: merging `1--2-grams` in
the PDF → **0 failures**; merging one `0.46--0.53` → correctly fails.
**Fix:** count the tex side on `normalise_dashes(...)` so en-dash and `--` sources count
alike.

## N54 — N47's `\x10`/`\x11` mapping is wrong, and N47's every-artifact rule turns that into a trap
`:79–80` maps both to a single apostrophe. They are the **double** quotes (17 occurrences
each): the PDF carries `\x10outside the United States\x11` where `paper.md:684` has
`"outside the United States"`. That leaves three incompatible forms — md `"…"`, tex
` ``…'' `, PDF `'…'`:

```
'no record says "outside the United States"'   md=True  tex=False pdf=False
"says 'outside the United States'"             md=False tex=False pdf=True
```

Since N47 now fails when a phrase is missing from **any** artifact, the first phrase
binding anyone writes over a quoted sentence will hard-fail on two of three surfaces for a
reason that is purely an extraction bug. The comment above the table says these "have to
be right"; they are not.
**Fix:** map `\x10`/`\x11` to `"`, and fold ` `` `, `''`, `"` and curly quotes to one form
in `strip_markup`.

## N55 — N47's page-furniture strip deletes real content
`:151–166` — `if re.fullmatch(r"\d{1,3}", _st): continue` is unanchored to page context. It
removes **57 lines**, of which only 25 are folios. Also removed: every top-level section
number, Figure 1/2 bar labels and axis ticks (`308 263 202 146 143 129 111 97`, `554 514
496 474 453`, `733`, `800`), and Table 5's `100` pool cell. Fourteen integers present in
the round-7 artifact are absent from the round-8 one.

The direction is fortunate — every consumer of the PDF artifact is a needle-in-haystack or
count test, so shrinking the haystack yields false positives, never misses, and the
row-by-row table check reads the unstripped `-layout` text. But the figure data labels are
now unverifiable from the PDF at all, and any future integer claim will fail for a reason
that is not a defect.

To be clear about what *did* work: the §5.4 page-break case it was written for **is**
handled — the p16/p17 break falls between "the +0.121 the constraint" and "channel inside
the reported configuration", and the N45 pattern matches after stripping. And the running
heads strip exactly 12 verso + 12 recto lines, so there is no over-strip there.
**Fix:** only strip a bare number adjacent to a form feed or to a running-head line.

## N56 — README and DATA_CARD overstate the verifier in the paragraph rewritten to stop overstating it
`README.md:82–85` says "a set comparison **in both directions** between `paper.md` and
`paper_lncs.tex`, **and between the `.tex` and the PDF**". The tex→PDF comparison is one
direction only: `_gone = sorted(_tex_nums - _pdf_nums)` at `:963`, with no reverse.
`DATA_CARD.md:15–18` repeats it. Neither mentions that the PDF artifact now has page
furniture stripped, nor the new hard body-prose gate.
**Fix:** add the reverse comparison, or say "in both directions between `paper.md` and the
`.tex`, and from the `.tex` into the PDF."

## N57 — M23's rule does not do what its own comment says
`scripts/10_build_latex.py:112–133`. The comment says a break inside
`unswept_hyperparameters` "leaves two strings that each read as an identifier of their
own. Require 8 visible characters on either side." The rule keeps that exact break —
`unswept` is 7 characters, so the underscore sits at visible position 8 and `8 >= 8`
passes. `BAAI/` and `data/` are suppressed as intended; this one is not.

The rest of M23 is clean, and I verified it properly: regenerating the `.tex` with
`scripts/10_build_latex.py` produces a file **byte-identical to the shipped one**, every
long `\texttt` token renders whole in the PDF with no hyphen-broken path and no new margin
overrun, and removing the blanket `.replace()` dropped no needed breakpoint.
**Fix:** use `> 8` on the left, or set the bound to 9.

## N58 — §5.2's new "70% rather than 81%" mixes anchors
`paper.md:494–497`: "measuring instead from the weakest corpus-trained channel (word2vec,
0.159), corpus-trained channels still cross 0.143 of the same 0.205 span, 70% rather than
81%." The arithmetic is exact (0.1433/0.205 = 69.9%), but 81% is
(hybrid_rrf − minilm)/span while the new figure re-anchors the numerator to word2vec and
keeps the MiniLM-anchored denominator. Like for like, the word2vec-anchored share is
0.1433/(0.3409 − 0.1592) = **79%**. The sentence understates its own case and invites the
question of where 0.062 of the span went.
**Fix:** "…still cross 0.143 of the 0.182 that remains above word2vec, 79% rather than
81%."

---

# MINOR

**M26** — N49's four outcomes confirmed under synthetic logs (prose 4/6 pt × bbl 4/6 pt,
all correct), and **the paper can still build green**: p7's +15.2 pt box falls inside
`\begin{table}` and p21/p22's +35.9 pt inside `\begin{verbatim}`, both excused by `_safe`,
and p23's bibliography box is 3.3 pt < 5.0. Residual risk: a box whose innermost open file
is `llncs.cls` or a `.sty` is classified as prose and now hard-fails, and `\begin{figure}`
is not in `_safe`.

**M27** — Margin profile otherwise unchanged from round 7 (body right edge re-derived at
480.6 pt): p7 +15.2, p21 +35.9, p23 +3.3, p25 +2.3, everything else ≤ +1.9. The only
change is p22 gaining +20.2, which is the N51 split.

**M28** — N48's hoisted summary prints an ungrammatical fragment: "…1 table(s) have no
numeric cells **and could not be**; verbatim blocks checked…". Append "checked".

**M29** — `_tex_only = sorted(_tex_nums - _md_nums - {"0.62"})` at `:982` — `p{0.62\linewidth}`
is already removed by `_tex_data_only`, so the literal exemption is now an unguarded hole
for any future real 0.62. Drop it.

**M30** — M24 verified clean: the round-6 notes folder has a README matching the rounds 5/7
template, the findings file is renamed, and no stale reference survives. M25's guard bounds
the 0.5318/0.5317 gap at 0.0005 and the actual gap is 0.0001. Path documentation is
complete except `LICENSE`, `LICENSE-DATA`, `.gitignore` and `paper_lncs.bbl`, which ship
without a line in either doc — the `.bbl` is worth one, since `.gitignore` explains why it
ships.

---

# Verified clean

**N42 is right**, and its arithmetic checks: `prefilter_hybrid` 0.4644 − 0.3025 = 0.162,
`slots_only` 0.4231 − 0.3025 = 0.121, and the +0.277 ladder is 0.121 + 0.156.

**Number propagation r7 → r8:** zero decimals added, zero lost. md−tex, tex−md, tex−PDF and
md−PDF are all empty. Every quantitative claim recomputed from `results/`: 0.038, 0.069,
0.107, 0.121, 0.143, 0.162, 0.277, 0.5318, 0.434, all six Table 5 rows, 0.717, 0.783, 96.1,
64.4, and 0.717 − 0.609 ≈ 0.11. M21's §6 parenthetical is sound.

**N46 does now catch a per-site merge** that round 7 acquitted — confirmed by mutation on
`0.46--0.53` and `5.3--5.5`. **N47's every-artifact rule works** in both directions I
tested. **N45's three new phrase bindings and the new md↔tex comparison all fire** under
mutation. **Script 12 reproduces the shipped list**, 79 for 79.

---

# Verdict

**Fix N50 and N51 and this goes.** N50 is a parenthetical, and I owe you the correction:
round 7's suggested wording named the wrong number and I should have checked which system
0.579 is built on before handing you a phrase to paste. That is the same
not-verified-against-the-artifact error this review has charged the manuscript with for
eight rounds, and it is worth saying plainly that the review is not exempt from it. Do add
the binding — a claim that survived my own review needs a gate more than one that did not.

N51 is a `\begin{figure}` wrapper and a rebuild. The thing to take from it is not the page
break but the reading: when a check fails after content moves, the first hypothesis should
be that the content moved badly, not that the check is wrong. Four failures, all real, all
silenced.

Everything else is hardening. N52 and N54 are worth doing before anyone writes another
phrase binding, since both will produce failures that look like data corruption and are
not.

The machinery this round is genuinely strong — the range guard, the every-artifact phrase
gate, the md↔tex comparison and the prose-overrun gate are all real improvements that I
tested by breaking them. What the round shows is the limit of that approach: 318 bindings
did not notice a wrong referent in the abstract, because bindings check what a number *is*
and not what it is *attached to*, and the four phrase bindings that do check attachment
cover the four claims already found. That is the honest boundary, and your response says so
itself.
