# NO-GO on the package, GO on the paper. The manuscript is clean; what you handed over was not built by your release script.

Round-4 re-review of `…quest-qi_20260907.zip` (58 files, 4.67 MB), extracted to
`review/round4/r4/`. Response read at `notes/review-2026-09-07-round3/RESPONSE-TO-REVIEW.md`.

**Mean rigor: 8.8 / 10** (6.4 → 7.4 → 8.3 → 8.8).

N11 is fixed. The renumbering — by far the riskiest change in this round — did not break
anything: every float is in appearance order, all 52 cross-references point at the right
object and describe it correctly, the three renamed figure files map cleanly onto their
new names by hash, and not one decimal was lost between round 3 and round 4. That is the
first round in four where the headline change landed cleanly on every surface.

The blocking problem is one layer out, and it is the round's signature failure in its
purest form: **`scripts/12_release_package.py` — the script written specifically to stop
"archive the working directory" — was not used to build this archive.**

---

## Verified fixed

**N11.** `paper.md:541` now reads "…comparable to what adding BGE to the fusion buys
(+0.038) and half of what fusion over BM25 alone is worth (+0.066)." No substitute
superlative. §5.3's arithmetic recomputes against `results/`: 0.3409−0.3025 = 0.0384;
0.3025−0.2363 = 0.0662, half = 0.033; 0.033/0.3025 = 10.9%.

**N17 — the renumbering, audited exhaustively.** PDF float order: Figure 1 p6, Table 1 p7,
Table 2 p10, Figure 2 p11, Table 3 p12, Figure 3 p13, Table 4 p15, Table 5 p16 — exactly
as claimed, no gaps, no duplicates. Every float is now cited in body prose. The §3.3
example table has a caption and is Table 1; "Table 3b" is Table 5. Figure files verified
by sha256: `fig1_taxonomy.png` = round-3 `fig3_taxonomy.png`, `fig3_main.png` = round-3
`fig1_main.png`, `fig2_family.png` unchanged; captions describe the right figures;
`gen_figures.py` writes the new names in appearance order; no old name survives outside
the historical review notes.

**N15, N16, N18, M6, M7, M9** all landed. **Number propagation r3→r4 is lossless** — zero
decimals lost, exactly one added (a seventh `0.033`, N15's §8 sentence), and it reached
the `.tex` and the PDF. Verifier: `checks run: 290 bindings, 0 failure(s)`.

---

# BLOCKING

## N19 — The shipped tree was not produced by the release script
**Location** package root; `scripts/12_release_package.py`.
**Problem** I ran the script against a copy of the shipped tree:

```
$ python3 scripts/12_release_package.py
  54 files, 26.0 MB uncompressed, 4.6 MB packed
  excluded per .gitignore and DATA_CARD.md: … LaTeX build artifacts …
```

Its output contains **zero** `.aux`/`.log`/`.blg`/`.out` files. The shipped zip contains
**four**. `ignored()` matches bare `*.ext` patterns correctly, so gitignore matching is not
broken — the archive you sent was assembled some other way. Round 3's release did not
carry them; round 4's does.

**Why it matters** This is the exact failure the script's own docstring says it exists to
prevent ("the release tarball was built by archiving the working directory"), recurring in
the round that hardened it. And it is not cosmetic, because it is also what let N20
through.

**Fix — RERUN.** `python3 scripts/12_release_package.py --zip` and hand over its output.

## N20 — `DATA_CARD.md` promises a directory the package does not contain, and nothing can detect it
**Location** `DATA_CARD.md:17–20`.
**Problem**

> "`_superseded_20260907/` — material withdrawn from the manuscript on 2026-09-07 when
> Section 5.6 was cut. **Nothing in it is cited by the paper.** It ships so the excision
> can be audited; see the README in that folder…"

The folder is absent. Three consequences: all five N14 sub-claims — the added README, the
renamed duplicate, the corrected `Sec. 5.6` comment — are *inside* the missing folder and
cannot be verified as shipped. The verifier's extended disclaimer loop
(`08_verify_manuscript.py:750–753`) iterates `("scripts","figures","_superseded_20260907")`
and `continue`s silently when the directory is absent, so N14's "the verifier's disclaimer
loop now covers the folder" is true only when the folder exists — in the shipped tree it
covers nothing and reports nothing. And script 12 parses only the data card's *"What is
not, and why"* section; nothing checks the *"What is in this repository"* list against the
archive, which is precisely why a promised-and-missing directory passes both gates green.

This is round 2's N5 inverted: then the card said "absent" and the files shipped; now the
card says "ships" and they do not.

**Also stale in the same file:** `DATA_CARD.md:14` lists `notes/review-2026-09-07/` and
`-round2/` but omits `notes/review-2026-09-07-round3/`, which does ship — stale by exactly
the folder this round added, the same class of error as M5 last round.

**Fix — EDIT + RERUN.** Decide whether `_superseded_20260907/` ships; make the card match.
Add `notes/review-2026-09-07-round3/`. Then extend script 12 to assert that every path in
"What is in this repository" actually exists in the archive — that check is four lines and
closes this class permanently.

---

# SHOULD-FIX

## N21 — Three real margin overruns in the PDF, and the verifier's "informational" note is too broad
`paper_lncs.log` reports 13 overfull hboxes. The verifier dismisses all of them with one
unconditional line (`:861–863`): *"5 table(s) checked cell-by-cell against their own
region of the PDF, so these are informational."* That reasoning only licenses dismissing
boxes **inside tables**. Three are not:

| box | actually at | verdict |
|---|---|---|
| **134.19 pt** | `paper_lncs.bbl:192` — the FDA guidance `\url{}` in `\bibitem{fda_ai_credibility}`. The log's line numbers are *`.bbl`* lines; `paper_lncs.tex:189–194` is Table 2, which is inside `\resizebox` and reports no box at all. | **Real.** ~4.7 cm past the right margin on p25. Fix: `\usepackage{xurl}`. |
| **83.13 pt** | `paper_lncs.tex:144–145`, body prose — `\texttt{results/dense_manifest.json,}` | **Real**, p8. Fix: `\allowbreak` or reflow. |
| **33.41 pt** | `paper_lncs.tex:246–255`, Table 3's tabular — which has `\small` but, unlike Table 2, **no `\resizebox`** | Overhangs the margin; nothing is cut (all 21 values present). Fix: wrap Table 3 like Table 2. |

The two ~20–36 pt boxes in the verbatim run-block are genuinely harmless — I confirmed
every line extracts in full.

**Fix — EDIT + rebuild.** Fix the three, and make the verifier's note conditional on the
box's source line falling inside a `table` environment.

## N22 — The renumbering reached `README.md:56` and `:59` and stopped at `:64`
`README.md:64`: *"…**Table 1** is parsed out of each surface and compared to `results/`
numerically…"* The table the verifier parses is the text-only retrieval table, which is
now **Table 2** — and the verifier's own comments were updated (`:201`, `:357`, `:537` all
say Table 2), as were README:56 and :59 in the same pass. One paragraph short. This is the
round-4 instance of the pattern, and it is a one-word edit.
(`scripts/10_build_latex.py:111` also says "this paper's Table 1", but that sentence is
recounting what happened in round 2, when it *was* Table 1. Defensible as history — I
would still add "(now Table 2)".)

## N23 — N12 is a real improvement, but "must appear in that table's region" is overstated
The per-table region check genuinely catches full-column truncation — I confirmed it fires
on a truncated Table 2 macro+MRR column and on Table 3's Δ column. But it is a `set`
difference over a **fixed 2400-character forward window** from the caption
(`08_verify_manuscript.py:806`), and that window runs well past the table body into the
following prose. Measured on the shipped PDF: Table 2's window ends mid-§5.1 at
*"…where it reaches 0.759 against BGE's 0.658…"*.

So there is no row or column awareness, and any value that recurs inside its own window is
unprotected. `0.302` occurs **16 times** in this PDF. I rewrote Table 2's Hybrid RRF
headline cell from `0.302` to `0.288` in the extracted text — a wrong number a reader would
act on — and **both the region check and the global backstop passed**. Per table, the
number of cells that can be corrupted undetectably: Table 2 **12 of 65**, Table 3 5/21,
Table 4 5/29, Table 5 4/17 — which includes essentially every headline number.

Separately, Table 1 (the §3.3 example table) contains no decimals, so its region check is
vacuous while still incrementing the counter — "5 table(s) checked cell-by-cell" overstates
coverage by one.

**Fix — EDIT (script only).** Bound the window at the next `\bottomrule` or next caption
rather than 2400 characters; anchor each value to its row label; and either fail or
explicitly skip a tabular with zero numeric cells.

## N24 — N13's parse-failure path warns and then builds anyway
The response says script 12 "says so loudly if the data card cannot be parsed rather than
silently falling back." It prints a warning and then builds and exits 0 in all three
failure modes tested — heading renamed, bullet list emptied, and **`DATA_CARD.md` deleted
entirely**, which produced an archive with no data card in it. The fallback list
(`data/raw/openfda/`) is also narrower than the card's (`data/raw/`), so a raw export at
any other path under `data/raw/` escapes it.

The positive paths do work: adding both forbidden files produced *"3 such file(s) exist
locally and were correctly excluded"*, and removing the embeddings line from `.gitignore`
produced the documented refusal with exit 1. **One reporting bug:** that same message
names `data/raw/MANIFEST.json` as "correctly excluded" while the archive contains it — the
`!` carve-out is applied to the file list but not to the report.

**Fix — EDIT.** `raise SystemExit` on parse failure; widen the fallback to `data/raw/`;
subtract the carve-outs from the report as well as the archive.

## N25 — `cmap` did not do what the response says
`paper_lncs.tex:11–13` claims extracted text now "keeps its ligatures and en-dashes
('findings' rather than 'ndings')". Measured on the shipped PDF: `"finding"` occurs **0**
times, `"nding"` **25** times, and the raw extraction still carries 160 `\x1c` bytes (the
T1 `fi` glyph). En-dashes are dropped outright — the PDF text reads `Sections 5.35.5`,
`0.460.53`, `1215 page limit`. The verifier survives only because of its unrelated
`T1_LIGATURES` table; the **en-dash loss is uncompensated**, so any stated range could
silently merge. (The response's "so pdftotext keeps ligatures" is also off: `-cmap` is not
a pdftotext option, and the verifier calls plain `pdftotext` everywhere.)
**Fix — EDIT.** Either make the claim true (`\usepackage[T1]{fontenc}` with `lmodern`, and
re-measure) or correct the comment, and add en-dash normalisation to the verifier's text
handling.

---

# MINOR

**M10** — `paper.md:455` still carries a superlative of the N11 family: *"the largest gain
from adding a dense channel anywhere in this table"*. Adding LSA to BM25 is worth +0.066
and LSA is a 300-dimension SVD representation. Defensible only because §4 files LSA under
"Text channels"; a hostile reviewer will query it. Say "**pretrained** dense channel".

**M11** — The response says N15 changed "§6's lead". It changed the *second* paragraph's
lead (`paper.md:735`); §6 still opens with "Report a gold-membership control, and report
what defines it." The wording change itself landed correctly in all three artifacts. No
contradiction — response wording only.

---

# Verdict

**The paper is done. The package is not.**

Nothing on the blocking list is a claim in the manuscript. §5.3's arithmetic is right,
§5.4 and §5.5 recompute, the renumbering is clean across 52 cross-references, the
bibliography is correct, the regulatory content has passed four rounds running, and the
verifier now runs 290 bindings across four artifacts and catches things I could not get
past it. On content I would sign this off.

What is left is that the archive you handed over is not the one your release script
builds, and the data card describes a directory that is not in it. Both are fixed by
running `scripts/12_release_package.py --zip` and reconciling two lines of
`DATA_CARD.md`. Then the three margin overruns and the one stale "Table 1" in the README,
which are a ten-minute editing pass and a rebuild.

The two hardening claims — N12's per-table check and N13's refusal — are both real
improvements and both weaker than the response states. I would **not** hold submission for
either; I would fix the sentences describing them now and harden the code before paper 2
inherits it. N23 is the one worth doing properly: bound the window at `\bottomrule` and
anchor on row labels, and the class of failure that decided rounds 1 through 3 stops being
reachable at all.

Send it once the release script has built it. I do not need to see it again.
