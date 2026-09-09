# Paper 1 — response to the round-4 pre-submission review

**Date:** 2026-09-07
**Review responded to:** `REVIEW-FINDINGS-ROUND4.md` in this folder
("NO-GO on the package, GO on the paper"; rigor 6.4 → 7.4 → 8.3 → **8.8**).

**State after this pass:** `checks run: 290 bindings, 0 failure(s)`. Pipeline 01–05
re-run. **This archive was built by `scripts/12_release_package.py`**, which is the
point of N19.

---

## N19 — the archive was hand-built, by the person who wrote the script that exists to stop that

Confirmed exactly. The shipped zip carried four LaTeX build artifacts
(`paper_lncs.aux/.log/.blg/.out`) that `12_release_package.py` excludes, because it was
assembled with a raw `zip -qr` rather than by running the script. The script's own
docstring says it exists to prevent "the release tarball was built by archiving the
working directory", and that is precisely what happened, in the round that hardened it.

There is no clever fix for this one. The archive is now built by the script and by
nothing else, and the response quotes the script's own output rather than a count taken
by hand.

## N20 — the data card promised a directory the package did not contain

Also confirmed, and the root cause is worse than the symptom: `_superseded_20260907/`
existed **only on the authoring machine**. It was created there during a sync and never
in the working tree, so the hand-built archive could not have contained it. Every one of
the five N14 sub-claims lived inside that missing folder.

Three fixes, and the third is the one that closes the class:

1. The folder is now in the working tree, so both machines carry the same thing.
2. `DATA_CARD.md` lists `notes/review-2026-09-07-round3/`, which it had omitted — stale
   by exactly the folder the previous round added, as the review notes.
3. **`12_release_package.py` now enforces both halves of the data card.** It previously
   parsed only "What is not, and why"; it now also parses "What is in this repository"
   and refuses to build if any promised path is absent from the archive. This is round
   2's N5 and round 4's N20 closed together — the card can no longer be wrong in either
   direction without the build failing.

Tested, with real exit codes:

```
$ mv _superseded_20260907 /tmp/ && python3 scripts/12_release_package.py
refusing to build: DATA_CARD.md says these are in this repository, but the
archive would not contain them:
  _superseded_20260907/                                          exit 1
```

The 1.9 MB duplicate inside that folder is **removed** rather than renamed — carrying an
exact byte-for-byte copy under a misleading name helps nobody. The folder's README now
records the clobbering bug in prose, which is what the file was being kept for.

## N24 — the parse-failure path warned and built anyway

Correct on all three modes, including the one that produced an archive with no data card
in it. `raise SystemExit` now, with exit 1 (verified: deleted card, renamed heading,
emptied list). The fallback list is widened from `data/raw/openfda/` to `data/raw/`, so a
raw export at any other path under it no longer escapes. The reporting bug is fixed too:
`data/raw/MANIFEST.json` was being named as "correctly excluded" while the archive
contained it, because the `!` carve-outs were applied to the file list but not to the
report.

## N23 — the region check was weaker than the round-3 response said

The review is right, and it demonstrated it: the window was a flat 2400 characters
forward from the caption, which runs past the table body into the following prose, so any
value recurring in that window was unprotected. Measured on the shipped PDF, Table 2's
window ended mid-§5.1.

Rewritten. The window is now bounded at the table's own last row, the body search starts
**after** the header row (the caption often repeats a row label — "Hybrid RRF + BGE is
the strongest…" — which the old code matched instead of the table row), and each value is
anchored to **its own row label**, scanning forward so an earlier row cannot satisfy a
later one. A tabular with zero numeric cells is now counted separately and reported as
not checked, rather than incrementing the coverage count: the §3.3 example table has no
decimals, so "5 tables checked" overstated coverage by one. It now reads "4 numeric
table(s) checked row-by-row … 1 table(s) have no numeric cells and could not be."

Tested against both attacks:

```
corrupt Table 2's Hybrid RRF nDCG cell 0.302 -> 0.288:
  FAIL: retrieval table in paper_lncs.tex: row 'Hybrid RRF (BM25 + LSA)'
        column ndcg@10 reads 0.288 but results/ says 0.3025

truncate Table 3 with the .tex intact:
  FAIL: in the 'Table 3: Query-underst' table, row '+ classifier defect prior'
        is missing 5 of its 9 value(s) from the PDF beside that row
```

## N21 — three real margin overruns, and a note that hid them

All three fixed at the cause: `xurl` for the 134 pt bibliography URL, `hyphenat` plus
`\emergencystretch` for the 83 pt `\texttt` path in body prose, and the table-wrap
threshold lowered from eight columns to seven for the 33 pt Table 3 overhang (seven was
measured, not guessed). Overfull boxes are down from 13 to 5, and **all five are inside a
table or verbatim block**.

The verifier's note was also wrong to dismiss all of them with one unconditional
sentence. It now maps each box's source line onto the `table` and `verbatim` line spans
in the `.tex`, reports boxes **outside** those environments as real margin overruns, and
says separately how many are inside. Fixing the three also removed the "informational"
line's only excuse for existing.

## N25 — the `cmap` claim was false as written

Measured on the round-3 build the reviewer had, and they are right: ligatures were not
fixed. Measured on this build: **en-dashes do extract correctly** (24 en-dash characters;
`0.46--0.53` comes back as `0.46–0.53`, not `0.460.53`), and **ligatures do not** — 160
raw `\x1c` bytes remain and "finding" extracts as "nding". `lmodern` was tried and is not
available in this TeX installation, so it is not used.

The comment in the template now states exactly that, including what is *not* fixed and
that the verifier compensates with its own ligature table. En-dash normalisation is added
to the verifier as well — defensively, because a range that loses its dash turns two
numbers into one wrong one, and that is the failure mode worth guarding even though this
build does not exhibit it.

## The rest

**N22** `README.md` now says Table 2, matching the renumbering; the converter's comment
is dated ("Table 1 at the time, Table 2 after the floats were renumbered"). **M10** "the
largest gain from adding a **pretrained** dense channel", since adding LSA to BM25 is
worth +0.066 and LSA is a dense representation too. **M11** noted: the round-3 response
said "§6's lead" when it changed the second paragraph's lead. Response wording; the edit
itself landed correctly in all three artifacts.

## What is still open

Unchanged and correctly identified across four rounds as not blocking arXiv: **gold-set
adjudication** by at least two qualified reviewers over at least 150 query–document
pairs, and **20–30 investigator-written questions**. Disclosed rather than fixed:
single-seed model fitting, and MiniLM's 0.0173 on the geography family.

## A note on the pattern

Four rounds, and each was decided by a correction that landed in one place and not
another: the manuscript, then the typeset artifact, then the sentence describing the fix,
then the archive itself. The verifier now covers the first three. N20's both-halves check
covers the fourth. The one thing no script can cover is the decision to run it, which is
what N19 was.
