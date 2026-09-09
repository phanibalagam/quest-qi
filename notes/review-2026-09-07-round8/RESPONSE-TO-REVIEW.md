# Response to round-8 pre-submission review

Both blocking findings were introduced by round-7 fixes, and the second is a reading
error of mine that this response has to own before anything else.

Verifier after this pass: **341 bindings, 0 failures**.

---

## N50 — the abstract named the wrong system for 0.464 — FIXED, with a binding

The review is right about the arithmetic and right that it supplied the wrong number:
0.579 is the centroid prior on top of the **soft** filter, so stripping the prior gives
`slots_only` **0.423**, not `prefilter_hybrid` 0.464. As written, the parenthetical
implied the prior is worth 0.115 rather than the 0.156 the paper's own
`channel_ablations` records, and it presented 0.464 as a rung of a ladder that §5.4 —
rewritten last round for exactly this reason — says it is not.

Abstract and `README.md` now read: "raises nDCG@10 to 0.579 (the soft metadata filter
alone reaches 0.423; a hard prefilter with no defect prior reaches 0.464)".

**That the reviewer supplied the wrong number does not move the responsibility.** I pasted
a figure into the abstract without checking which system it belonged to, which is the
error this review has charged the manuscript with for eight rounds. The check that would
have caught it is the one the review asks for, and it is now in place: two new phrase
bindings, `soft metadata filter alone reaches (\d\.\d{3})` → `slots_only` and `hard
prefilter with no defect prior reaches (\d\.\d{3})` → `prefilter_hybrid`, each recomputed
from `results/` and enforced in all three artifacts. Mutating either figure in `paper.md`
alone now fails.

## N51 — the listing broke across pages, and my round-7 change silenced the signal — FIXED

**The review is right, and this is the more serious of the two.** Round 7 saw four
verbatim-truncation failures appear after the manuscript grew, decided they were a
false-positive class, and switched the check to the `-layout` extraction so they would
stop. They were not false. The listing had repaginated and LNCS was setting `22   P. K.
Balagam` between two of its lines. I changed a true signal into silence and then wrote
that up as a fix.

Two changes:

- `scripts/10_build_latex.py` now wraps every verbatim block in
  `\par\noindent\begin{minipage}{\linewidth}`, which cannot break, so the block moves
  whole to the next page rather than splitting. Verified in the rebuilt PDF: all eleven
  lines are on one page and no running head appears inside them.
- `scripts/08_verify_manuscript.py` is **back on the default extraction** for the
  truncation check, so a split block fails again — and a new check names the defect
  directly rather than leaving it to be inferred from a lost line tail: for each verbatim
  block, if a running head appears in the extracted text between its first and last line,
  that is a hard failure.

The reading the review draws is recorded in this folder's README and is the one that
governs from here: when a check starts failing after content moves, the first hypothesis
is that the content moved badly.

---

## N52 — the count-based range guard asserted merges that had not happened — FIXED

`_pdf_norm` was the raw, newline-bearing extraction while the needle required the two
numbers to be adjacent, so a line broken after an en-dash reported a merge. Whitespace is
now collapsed before the search and the needle allows the single space a collapsed break
leaves. **Tested:** injecting a line break at one `0.46--0.53` site now produces 0
failures; genuinely merging that site still fails.

## N53 — the guard still acquitted a real merge at three ranges — FIXED

The cause was slightly different from the diagnosis, and the diagnosis found it. The
tex-side count ran on `paper_lncs.tex` alone, but the bibliography and its citation notes
reach the PDF from `paper_lncs.bbl`. So `1--2`, `1--174` and `333--389` each counted one
fewer on the source side than the PDF side, and that slack acquitted a merge. The count
now runs over `.tex` + `.bbl`, and the pattern matches only real range separators (`--`,
en-dash, em-dash) — not a plain hyphen, which would otherwise have counted the ORCID
`0009-0007-6762-399X` as two ranges.

**Tested by mutation, all three of the review's cases:** merging `1--2-grams`, `1--174` or
`333--389` in the PDF now fails; the benign line break still passes.

## N54 — `\x10`/`\x11` are the double quotes — FIXED

Mapped to `"`, and `strip_markup` now folds `` `` ``, `''`, and the curly quotes to the
same form, so the three surfaces spell a quotation identically. The review is right that
this mattered more once N47 made a missing phrase a hard failure: the trap was live.

## N55 — the page-furniture strip deleted real content — FIXED

`re.fullmatch(r"\d{1,3}")` was unanchored and removed 57 lines where only 25 were folios,
taking every section number, both figures' bar labels and axis ticks, and a Table 5 pool
cell with it. A bare integer is now stripped only when its nearest non-blank neighbour on
either side is a form feed or a running head — adjacency has to skip blanks, because
`pdftotext` puts one between the head and the folio.

**Tested:** all sixteen integers the review named (`308 263 202 146 143 129 111 97`, `554
514 496 474 453`, `733`, `800`, and Table 5's `100`) survive in the artifact; 46 lines are
removed, all of them running heads and folios. The §5.4 page-break case the strip was
written for still passes.

## N56 — README and DATA_CARD overstated the comparison — FIXED

The tex→PDF comparison is one direction, and the reverse is not a defect signal: the three
embedded figures carry their own axis ticks and bar labels, drawn by
`figures/gen_figures.py` from `results/`, which the `.tex` has no reason to contain. The
reverse direction is now computed and **printed as a note**, and both documents say "in
both directions between `paper.md` and the `.tex`, and from the `.tex` into the PDF". The
README also now mentions the page-furniture stripping and the hard body-prose gate, which
it did not.

## N57 — M23's rule kept the break its own comment said to suppress — FIXED

`unswept` is 7 characters, so the separator sat at visible position 8 and `8 >= 8` passed.
The bound is 9. `unswept_hyperparameters` no longer takes a breakpoint; the margin profile
is unchanged (identical overfull widths to round 7: 15.62, 20.29, 36.03, 4.54 pt), no path
is hyphen-broken, and no line ends on a bare separator except the two deliberate ones
inside long paths.

## N58 — §5.2 mixed anchors — FIXED

The review's wording, and its arithmetic: 0.1433/0.1817 = 78.9%. §5.2 now reads "still
cross 0.143 of the 0.182 that remains above word2vec, 79% rather than 81%".

---

## Minor

- **M26** — `figure` and `minipage` added to the safe-environment list; the listing now
  lives in a minipage, and a float's contents are measured against the float width.
- **M28** — "and could not be checked", and the note now also says the verbatim blocks
  were checked for page breaks set inside them.
- **M29** — the `{"0.62"}` exemption is gone. It was dead (`_tex_data_only` already
  removes `p{0.62\linewidth}`) and would have swallowed a future real 0.62.
- **M30** — `paper_lncs.bbl` now has its own line in `DATA_CARD.md`, saying why a file
  `.gitignore` excludes nevertheless ships: arXiv wants the `.bbl` rather than running
  BibTeX, and the verifier reads it, because the bibliography's text reaches the PDF from
  there and not from the `.tex` — which is what N53 turned out to be about.

---

## On the boundary the review names

The closing paragraph is right and worth restating rather than agreeing with in the
abstract: 318 bindings did not notice a wrong referent on page 1, because a binding checks
what a number **is** and the six phrase bindings that check what it is **attached to**
cover the six claims already found. That is not a general guarantee and this response does
not claim one.

What did change this round is that the failure mode moved: for eight rounds the error was
a correction landing in one surface and not the others. Round 8's two blocking findings
were both introduced *by* fixes, one by transcribing a supplied number without checking
its provenance and one by explaining away a true failure. Neither is caught by comparing
surfaces to each other. The procedure both point at is the same: a number is not adopted
until it has been traced to the computation that produced it, and a failure is not
explained until the explanation has been tested against the artifact.

## Still open, and requiring the author

Unchanged: gold-set adjudication by at least two qualified reviewers over at least 150
query–document pairs, and 20–30 investigator-written questions. Acknowledged and not
fixed: M13 (Table 2 at roughly 64% of body type) and M15 (no DOI in `CITATION.cff`,
pending deposit).
