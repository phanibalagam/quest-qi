# NO-GO — one wrong number in the paper, and the data card is stale again. Everything else is fixed.

Round-5 re-review of `…quest-qi_20260907_1.zip` (70 files, 4.87 MB), extracted to
`review/round5/r5/`. Response read at `notes/review-2026-09-07-round4/RESPONSE-TO-REVIEW.md`.

**Mean rigor: 8.9 / 10** (6.4 → 7.4 → 8.3 → 8.8 → 8.9).

**N19 is fixed, and I confirmed it the only way that counts:** I ran
`scripts/12_release_package.py` against a copy of what you sent, and it produced **70
files** — exactly the shipped list. No build artifacts. The archive was built by the
script.

Three of the four hardening items now genuinely enforce what they claim. I broke each one
deliberately:

```
corrupt Table 2's Hybrid RRF cell 0.302 → 0.288 in paper.md:
  FAIL: retrieval table in paper.md: row 'Hybrid RRF (BM25 + LSA)'
        column ndcg@10 reads 0.288 but results/ says 0.3025      (N23 ✓)
delete _superseded_20260907/:  refusing to build …               exit 1  (N20 ✓)
delete DATA_CARD.md:           refusing to build …               exit 1  (N24 ✓)
```

N23 is the one that matters — the round-4 attack that passed both checks now fails
row-anchored, by name. That closes the class that decided rounds 1 through 3.

The blocking findings below are one wrong number in the manuscript, and the data card
going stale by exactly one folder for the second round running.

---

# BLOCKING

## N26 — §2 states a number the results do not support, and §5.2 states the same number correctly
**Location** `paper.md:150` / `paper_lncs.tex:83` (Related work) against `paper.md:491` (§5.2).

Related work:
> "…the pretrained retrieval encoder among them is statistically indistinguishable from
> corpus-trained fusion here, while giving a system the query's defect category is worth
> **0.107 on top of the best of them**."

§5.2, correctly:
> "Giving a system the query's true defect category is worth **0.107 on top of the
> corpus-trained fusion**, for free."

From `results/`: `qir_oracle` = 0.4097. Against corpus-trained fusion (`hybrid_rrf`,
0.3025) that is **+0.1072** — §5.2 is right. Against "the best of them", i.e. the best of
the eight systems in the preceding sentence (`hybrid_rrf_dense`, 0.3409), it is
**+0.0688**. The Related-work sentence overstates by 56%, and it is the sentence that
motivates the whole paper: it is the asymmetry argument, stated in the section a reviewer
reads before any results.

**Why it matters** This is the first manuscript content error I have found since round 3,
and it has survived all five rounds because no binding covers it — 0.107 appears verbatim
in both places, so `states()` and `in_text()` are satisfied, and nothing checks *what the
number is measured against*. It is the same estimand problem the verifier's own docstring
warns it cannot catch: "whether the right statistic was chosen in the first place".

**Fix — EDIT + rebuild.** Change `paper.md:150` to "0.107 on top of the corpus-trained
fusion", matching §5.2. Then consider a binding that ties this figure to
`qir_oracle − hybrid_rrf` rather than to its printed characters.

## N27 — `notes/review-2026-09-07-round4/` ships and the data card does not list it, and the guard cannot see it
**Location** `DATA_CARD.md:14–15`; `scripts/12_release_package.py:54`.

Two distinct defects, and the second is why the first got through.

**(a) Stale by exactly one folder, again.** The card was updated to add
`notes/review-2026-09-07-round3/` — the folder the *previous* round added — and stops one
round short of `-round4/`, which ships. This is round 4's N20 recurring one round later,
and round 2's M5 before that.

**(b) The both-halves check enforces one of the three paths on its own bullet.**
`promised_present()` uses:

```python
re.findall(r"^\s*[-*]\s*`([A-Za-z0-9_./*-]+)`", sec, re.M)
```

anchored at the bullet marker, so it captures only the **first** backticked path per
bullet. The reasoning is copied from `promised_absent()`, where it is correct (each
bullet names the excluded path first, then the mechanism that replaces it). It is wrong
here, because `DATA_CARD.md:14–15` names three sibling directories on one bullet:

```
- `notes/review-2026-09-07/`, `notes/review-2026-09-07-round2/` and
  `notes/review-2026-09-07-round3/` — the external pre-submission reviews as received…
```

`promised_present()` returns 6 paths; rounds 2 and 3 are not among them. Demonstrated:

```
$ mv notes/review-2026-09-07-round3 /tmp/ && python3 scripts/12_release_package.py
  wrote quest-qi_release.tar.gz / 66 files …                     exit 0
```

The build succeeds after deleting the folder this round added to the card to fix the
previous round's stale card. The N20 demo in the response worked only because
`_superseded_20260907/` happens to sit alone on its bullet — I reproduced both: alone →
refuses with exit 1; on a shared bullet → builds clean.

**And there is no third direction.** Nothing checks *shipped → promised*, so a new
top-level directory ships undocumented indefinitely. That is exactly how `-round4/` got
in.

**Fix — EDIT + RERUN.** Match every backtick in the section, not just the first per
bullet; add `notes/review-2026-09-07-round4/` to the card; and add the third check —
every top-level directory in the archive must be named somewhere in "What is in this
repository". Those three changes close the card in all three directions permanently.

---

# SHOULD-FIX

## N28 — The en-dash claim is right about the case it tested and wrong about body prose
`paper_lncs.tex`'s new comment says en-dashes now extract correctly, citing
`0.46--0.53` → `0.46–0.53`. That is true — it is Table 5's caption, and it is one of the
24 en-dash characters in the PDF. But those 24 are 19 in the bibliography, 2 in the
abstract and 3 in list bullets. **Body prose is a different story:** every `--` there
extracts as the control byte `\x15`.

```python
>>> t[i-6:i+12]
'questions at 0.151\x150.193,'
```

The good news, which I checked before writing this up: the verifier's `\d+\.\d+` regex
splits `0.151\x150.193` into `0.151` and `0.193` correctly, so no binding is corrupted
and no number is silently merged. `2012–2026`, `5.3–5.5` and `12–15` are all `\x15`-joined
too, none of them numerically ambiguous.

So this is not a claim defect — it is the same class as the ligature problem the comment
*does* disclose honestly, and the comment should disclose this half too.
`T1_LIGATURES` covers `\x1b`–`\x1f` and the `strip_markup` normaliser handles
`– — − --`; neither covers `\x15`.

**Fix — EDIT.** Say in the comment that body-prose en-dashes extract as `\x15` on this
build, add `\x15` to the verifier's control-character table, and add a check that any
`\d--\d` in the `.tex` appears in the PDF text with *some* separator. A reader
copy-pasting a range out of the PDF still gets a control character.

## N29 — `hyphenat[htt]` bought the 83 pt fix by hyphenating two file paths across lines
`paper_lncs.tex:37` `\usepackage[htt]{hyphenat}` permits hyphenation inside `\texttt`, and
TeX inserts a real hyphen. New in this round:

```
p11: …exact wall-clock figures vary run to run and are recorded in re-
     sults/retrieval_results.json.
p12: …the macro-average across families are in results/retrieval_re-
     sults.json.
```

Round 4 rendered both intact. A reader cannot tell whether the path is `results/…` or
`re-sults/…`. Note `xurl` — which you used for the bibliography URL — breaks *without*
inserting a hyphen, so the right mechanism was already in the package.

**Fix — EDIT + rebuild.** Drop `[htt]`, keep `\emergencystretch`, and wrap long paths in
`\path{}` or `\seqsplit`, or `\allowbreak` at `/` and `_`.

## N30 — The new overfull-box mapper is file-blind, so a bibliography overrun can be excused as a table
`scripts/08_verify_manuscript.py:944` extracts `(width, first_line)` from the log and maps
the line number straight onto `\begin{table}`/`\begin{verbatim}` spans in **`paper_lncs.tex`**,
with no tracking of which file the log was reading. Round 4 established that bibliography
boxes carry **`.bbl`** line numbers — the 134 pt FDA-URL box was reported "at lines
189--194", and that URL is at `paper_lncs.bbl:192`. Fed a synthetic log, a 250 pt
bibliography overrun at line 200 is classified as "inside a table" because `.tex` 194–214
is Table 2. Two `.bbl` lines of margin separate the check from silently excusing the exact
overrun it was written to catch. It also captures only the paragraph's first line and
misses TeX's `in alignment at lines …` variant.

Related and minor: the mapper reads `paper_lncs.log`, which `.gitignore` correctly
excludes, so in the shipped release it reports nothing at all.

**Fix — EDIT.** Parse the log's file-nesting parentheses and apply the `.tex` span map
only to boxes emitted while `paper_lncs.tex` is the innermost open file; classify `.bbl`
boxes as bibliography overruns unconditionally.

## N31 — M10's repair makes the superlative vacuous rather than true
`paper.md:447`: "the largest gain from adding a **pretrained** dense channel anywhere in
this table". Table 2 contains exactly one row that adds a pretrained dense channel to
another system (`Hybrid RRF + BGE` over `Hybrid RRF`); `BGE-base` and `MiniLM` are
standalone rows. It is a maximum over a set of size one. Round 4 was right to kill the
unqualified version; the repair is now unfalsifiable rather than wrong.
**Fix — EDIT.** "the only pretrained dense channel added to a fusion here, and worth
+0.038".

## N32 — `_superseded_20260907/README.md` carries a stale float reference
`:17` — "| generation_results.json | The scored results that fed the withdrawn **Table 4**. |"
The live manuscript has a Table 4 (the metadata-channel/controls table). A reader auditing
the excision collides with a table that is very much present. N22 fixed exactly this class
in `README.md`; the sweep did not reach the folder added this round.
**Fix — EDIT.** "the withdrawn generation table (Table 4 at the time; the current Table 4
is unrelated)".

---

# MINOR

**M12 — N21's three named overruns are genuinely gone.** Measured off the PDF's own word
bounding boxes against a text-block right edge of 481.9 pt: the FDA URL 613.0 → inside
(breaks cleanly with no inserted hyphen), the `\texttt` path 564.8 → inside, Table 3
512.5 → inside. Table 3's new `\resizebox` costs it 16% of body type and loses no cell —
all nine values match `results/`. Two pre-existing intrusions remain (Table 1 at 14 pt,
the verbatim run-block at ~35 pt), and the newly added script-09 line adds a sixth
protruding verbatim line. Cosmetic.

**M13 — Table 2 is scaled to ~64% of body type** (2.90 pt/char against 4.54 body), below
`\tiny`. Pre-existing from round 4's nine-column fix, not a round-5 regression, but a
copy-editor will flag it. Splitting it into metrics / aggregates+CI would fix it.

**M14 — `README.md:23` still leads with 0.302** while Table 2's caption calls
`Hybrid RRF + BGE` (0.341) "the strongest text-only system we have under both aggregates".
The paper explains the 0.302 base convention in §4; the README does not, so read
standalone it conflates "BGE alone is indistinguishable" with "BGE adds nothing" — and
§5.1 reports adding BGE as +0.038, Holm p = 0.0.

**M15 — `CITATION.cff`** has `url`, `version` and `date-released` now, but no DOI and no
`preferred-citation` for the manuscript. Worth adding once a DOI is minted.

---

# Verified clean

`_superseded_20260907/` audits well: the README accurately lists all six non-README files,
the 1.9 MB duplicate is **gone** (I hashed all 13 files against `results/`,
`data/processed/` and `figures/` — no collisions), both `.py` files carry the disclaimer
notice, the verifier's loop now covers the folder because it exists, and
`06_generation_harness.py:38` correctly says "the study this fed was Sec. 5.6, now
WITHDRAWN". Nothing in it contradicts the manuscript.

**Number propagation r4 → r5 is perfect:** the decimal multiset of `paper.md` is identical
between rounds — nothing added, lost or changed. Every decimal reaches the PDF; the only
`.tex`-not-in-PDF values are `0.62` (a column width) and `4.7` (a comment). Every §5.1
statistic I recomputed from `results/` agrees, including the per-family reversals and
"difference of 0.015" = 0.0149. N22 and M10 landed on every surface, and grepping every
`Table N`/`Figure N` across `README.md`, `DATA_CARD.md`, `CITATION.cff`,
`notes/00-study-design.md` and all scripts turns up nothing stale except N32.

---

# Verdict

**Fix N26 and this is a GO.** It is one word — "the best of them" → "the corpus-trained
fusion" — and it is the only defect in this package that a reader of the paper would ever
see. Everything else on the list is repo hygiene, a build-tooling hole, or a comment that
overstates what it verified.

N27 is worth doing in the same pass, because it is the fifth consecutive round in which
the data card went stale by exactly the folder the previous round added, and the fix is
three small changes to one regex plus one new check. After that the card cannot be wrong
in any direction without the build failing, which is the outcome N20 was aiming at.

What is genuinely settled now: the archive is built by the release script and I verified
it reproduces the shipped list exactly; the row-anchored table check catches the attack
that beat round 4; the data card's forbidden half and the parse-failure path both exit 1
under test; the three margin overruns are measurably inside the text block; and not one
number moved between rounds.

N26 is a good note to end on, in the way that matters: it is not a packaging slip or a
stale sentence, it is a claim measured against the wrong baseline, sitting in Related work
since round 1 and invisible to every binding because both copies of "0.107" agree with
each other. That is the class the verifier's own docstring says needs a reader. It got
one.

Send it after N26. You do not need another round from me.
