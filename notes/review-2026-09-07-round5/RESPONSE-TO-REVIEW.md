# Paper 1 — response to the round-5 pre-submission review

**Date:** 2026-09-07
**Review responded to:** `REVIEW-FINDINGS-ROUND5.md` in this folder
(NO-GO on one number; rigor 6.4 → 7.4 → 8.3 → 8.8 → **8.9**).

**State after this pass:** `checks run: 307 bindings, 0 failure(s)`. Pipeline 01–05
re-run. Archive built by `scripts/12_release_package.py --zip`.

---

## N26 — a number measured against the wrong baseline, in Related work, since round 1

Confirmed against `results/`. `qir_oracle` is 0.4097. Against corpus-trained fusion
(`hybrid_rrf`, 0.3025) the oracle gain is **+0.1072**, which is what §5.2 says. Against
"the best of them" — the eight systems in the preceding sentence, whose best is
`hybrid_rrf_dense` at 0.3409 — it is **+0.0688**. §2 overstated by 56%, in the sentence
that motivates the entire paper.

Fixed: §2 now reads "worth 0.107 on top of the corpus-trained fusion (and 0.069 on top of
the strongest system in that spread)", which states both and matches §5.2.

**Why five rounds of checking missed it.** Both copies of "0.107" agreed with each other,
so `states()` and `in_text()` were satisfied; nothing checked what the number was measured
*against*. This is exactly what the verifier's own docstring says it cannot catch —
"whether the right statistic was chosen in the first place" — and the honest reading is
that the docstring was right and the review was the mechanism that caught it.

**A binding now covers the class.** Rather than pinning the printed characters, it ties
the figure to the contrast it names: for each phrase of the form "on top of X", it
recomputes `qir_oracle − X` from `results/` and fails if the number quoted before that
phrase disagrees. Tested by reintroducing the defect:

```
FAIL: a sentence says 0.107 'on top of the strongest system in that spread', but the
      oracle gain over the strongest system in the spread is 0.069 (qir_oracle
      0.4097 minus hybrid_rrf_dense 0.3409). The number is measured against the
      wrong baseline.
```

That does not generalise to every estimand in the paper, and it should not be read as
though it does. It covers this claim and claims shaped like it.

## N27 — the data card, closed in all three directions

Both halves of the finding are right, and the second explains the first.

**(a)** The card was stale by exactly the folder the previous round added — for the
fifth consecutive round. `notes/review-2026-09-07-round4/` is now listed.

**(b)** `promised_present()` was bullet-anchored, so it captured only the first
backticked path per bullet. That reasoning was copied from `promised_absent()`, where it
is correct, and is wrong here because one bullet lists three sibling review directories.
The N20 demo in the round-4 response worked only because `_superseded_20260907/` happens
to sit alone on its bullet. Now every backtick in the section is matched.

**(c)** The third direction did not exist: nothing checked *shipped → promised*, which is
how the round-4 folder shipped undocumented. Added — every top-level directory in the
archive must be named in "What is in this repository".

That check fired immediately on `scripts/` and `figures/`, which had never been
documented either. Both are now described in the card.

Tested, with real exit codes:

```
delete notes/review-2026-09-07-round3  (shared bullet)  -> exit 1
delete notes/review-2026-09-07-round4  (shared bullet)  -> exit 1
add an undocumented top-level directory                 -> exit 1
clean                                                   -> exit 0
```

The shared-bullet case is the one that built cleanly before.

## N28 — the en-dash comment was right about the case it tested and silent about the rest

Correct. The 24 en-dash characters are in the bibliography, abstract and list bullets;
body-prose `--` extracts as the control byte `\x15`. The review's own check that no
binding is corrupted is right — `\d+\.\d+` splits `0.151\x150.193` correctly — but the
comment claimed more than it had measured.

`\x15` is added to the verifier's control-character table and to the dash normaliser, and
a new check requires every `\d--\d` range in the `.tex` to appear in the PDF with *some*
separator, failing only when the range appears nowhere separated. That last qualifier
matters: `1--2-grams` and a bibliography page range both produce a "12" elsewhere in the
document, and flagging those would be noise.

## N29 — `hyphenat[htt]` bought the margin fix by putting a hyphen inside file paths

Confirmed: round 4 rendered `results/retrieval_results.json` intact; the `[htt]` build
broke it as `re-sults/…`, and a reader cannot tell the hyphen is not part of the path.
Removed. `inline()` now inserts `\allowbreak` after each `/` and `_` in a long `\texttt`
token, which breaks without adding a character — the same property `xurl` gives URLs, as
the review points out. (`\seqsplit` was tried first and chokes on the escaped
underscores these paths contain.) Verified: no path is hyphen-broken in the rebuilt PDF.

*Corrected in round 6 (N41):* the sentence that followed here claimed the only hyphenated
break left in the PDF was ordinary word hyphenation of "stability". That was wrong — the
PDF contains dozens of ordinary hyphenated word breaks (`prod-`, `conse-`, `ques-`,
`bibliogra-`, and others). The claim that matters, that no `\texttt` path is hyphen-broken,
is true and was independently verified in round 6; the "only ... one" clause was an
overstatement about ordinary prose hyphenation and has been withdrawn.

## N30 — the overfull-box mapper was file-blind

Right, and it is the sharpest of the hardening findings: the mapper read line numbers
from the log and applied a `.tex` span map without tracking which file TeX had open, so a
`.bbl` overrun at line 200 would be excused as "inside a table" because the `.tex` has a
table there. Two `.bbl` lines of margin separated the check from silently excusing the
exact 134 pt bibliography overrun it was written to catch.

The mapper now walks the log's parenthesis nesting and records the innermost open file for
each box. `.bbl` boxes are classified as bibliography overruns unconditionally and **fail**
rather than being noted; `.tex` boxes are matched against the environment spans; the
`in alignment at lines` variant is now matched too. Tested by injecting a synthetic 250 pt
`.bbl` box inside the `.bbl` scope:

```
FAIL: 1 overfull hbox(es) in the bibliography (max 250pt, paper_lncs.bbl line(s)
      [200]) -- a reference is running past the right margin
```

All five real boxes in this build attribute correctly to `paper_lncs.tex`.

## N31, N32, M14

**N31** the qualified superlative was a maximum over a set of size one. Replaced with
what is actually true: "it is the only pretrained dense channel added to a fusion here, so
there is nothing to rank it against". **N32** `_superseded_20260907/README.md` referred to
"the withdrawn Table 4" when the live manuscript has a Table 4; both that and the Figure 4
row now say so explicitly. **M14** the README led with 0.302 and read, standalone, as
though BGE adds nothing; it now gives 0.341 as the best system, states the +0.038 gain,
and explains why 0.302 is the base later sections are measured against.

**M13** (Table 2 scaled to ~64% of body type) and **M15** (no DOI in `CITATION.cff`) are
acknowledged and not fixed: the first needs a table split that would change the paper's
presentation for a copy-editing reason, and the second needs a DOI that does not exist
yet.

## What is still open

Unchanged across five rounds and correctly identified as not blocking arXiv: **gold-set
adjudication** by at least two qualified reviewers over at least 150 query–document
pairs, and **20–30 investigator-written questions**. Disclosed rather than fixed:
single-seed model fitting, and MiniLM's 0.0173 on the geography family.

## On N26 as the last finding

Five rounds, and the errors moved steadily inward: the archive, then the typeset artifact,
then the sentences describing the fixes, and finally a claim measured against the wrong
baseline. Each earlier class now has a gate. This one did not, and could not have been
caught by any binding that compares a manuscript to itself — both copies of the number
agreed. It took someone who asked what the number was measured against.
