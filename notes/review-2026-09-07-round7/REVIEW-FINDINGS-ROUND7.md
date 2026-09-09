# NO-GO — the fix for a wrong-parent claim introduced an unambiguous one. One sentence.

Round-7 re-review of `quest-qi_release.zip` (75 files, 4.90 MB), extracted to
`review/round7/r7/`. Response read at `notes/review-2026-09-07-round6/RESPONSE-TO-REVIEW.md`.

**Mean rigor: 9.1 / 10** (6.4 → 7.4 → 8.3 → 8.8 → 8.9 → 9.0 → 9.1).

**N33, N34 and N35 are all fixed**, and I verified each in the artifact. §5.2 now names both
baselines; "it costs a 110-million-parameter encoder to cross most of it" is replaced with
"most of it is crossed by corpus-trained channels alone; the pretrained encoder buys the
last 0.038" — and 0.1666 + 0.0384 = 0.2050 exactly; the README mirrors N31's wording.

**Both gates are repaired and I could not defeat them.** Swapping the two baselines inside
`paper_lncs.tex` alone now produces four failures naming the `.tex`; adding an undocumented
review folder and a stray top-level file now refuses the build. The margin profile is
byte-identical to round 6 (p7 +15.2 pt, p21 +35.9 pt, p23 +3.3 pt — nothing new, nothing
worse); M16's three new breakpoints do not fire anywhere in the shipped PDF; M18 and M19
hold exactly as claimed; and the release script reproduces the shipped list, 75 for 75.

One blocking finding, and it is the same class the last six rounds have been about — this
time introduced *by* the fix.

---

# BLOCKING

## N42 — §5.4's rewrite names the wrong parent for +0.162
**Location** `paper.md:684–689`; `paper_lncs.tex:351`; PDF.

> "First, the +0.277 for the metadata configuration is not evidence about query
> understanding, and neither is the +0.121 from the constraint channel alone. A
> conventional filter-then-search system … **captures +0.162 nDCG@10 of that +0.277**."

Round 6 read "captures 0.162 of it", which was ambiguous between a fraction and an
absolute. N40 removed the ambiguity — and named the wrong parent. Recomputed from
`results/proposed_results.json`:

| system | nDCG@10 | Δ vs Hybrid RRF |
|---|---|---|
| `hybrid_rrf` | 0.3025 | — |
| `slots_only` (soft filter) | 0.4231 | **+0.1206** |
| `prefilter_hybrid` (hard prefilter, no prior) | 0.4644 | **+0.1619** |
| `qir_centroid_slots` (prior + soft filter) | 0.5793 | **+0.2768** |

The +0.277 decomposes, per the paper's own `channel_ablations`, as **0.1206 + 0.1562**:
the soft filter, then the centroid prior on top of it. The +0.162 belongs to
`prefilter_hybrid`, a **different system** — hard prefilter, no prior — which is not on
that ladder at all (0.4644 is not a rung between 0.3025 and 0.5793). And 0.162 > 0.121, so
the "conventional" system out-scores the constraint channel that actually sits inside the
reported configuration, which is a more interesting point than the sentence makes and is
lost by the wrong framing.

**Why it matters** This is a paper whose entire thesis is that gains must be measured
against the right control. A wrong-parent claim, introduced by the fix for a wrong-parent
claim, in the section that argues the point, is what a hostile reviewer leads with.

**Fix — EDIT + rebuild.** Either "captures **+0.162 nDCG@10 over the same baseline**,
against the +0.121 the constraint channel inside that configuration is worth", or use
+0.121 if the intent was "the part of the +0.277 that needs no query understanding".

---

# SHOULD-FIX

## N43 — The abstract credits 0.579 to metadata filtering alone
`paper.md:44` and `README.md:32`:

> "**Filtering candidates on the metadata the question names** raises nDCG@10 to 0.579"

Table 4 in the same manuscript: metadata filtering alone is **0.423** (soft) or **0.464**
(hard). **0.579** is the row "*Centroid prior +* metadata filter". §5.4's body is careful
about this ("the +0.277 for the metadata configuration"), which makes the abstract's
looseness harder to defend — and 0.579 is the paper's headline circularity number, quoted
in the abstract, §1, §5.4, §6 and the conclusion. It has survived all seven rounds.

(§1's "Doing so raises nDCG@10 from 0.302 to 0.579" is defensible, because "doing so"
there refers to representing the question's structure generally, which includes the prior.
The abstract and README name only the filter.)

**Fix — EDIT.** "Adding a defect-category prior to a metadata filter raises nDCG@10 to
0.579 (metadata filtering alone reaches 0.464)."

## N44 — The oracle is sold "for free" in §2 and §5.2 with no caveat
`paper.md:151` and `:492–494`: "…is worth 0.107 on top of the corpus-trained fusion, and
0.069 more than the strongest system in that spread reaches on its own, **for free**."

Both figures are arithmetically right. But `qir_oracle` is an oracle over one component of
the gold predicate. §5.5 says exactly that ("an oracle over one component of the gold
predicate and so subject to the caveat above"), and §5.4 is a whole section arguing such
numbers are not research results. §2 and §5.2 carry neither the word "oracle" nor the
caveat, and add "for free" — so the paper's most-quoted asymmetry reads, in the two places
a reviewer meets it first, as an obtainable gain.

**Fix — EDIT.** Add "(an oracle over one predicate component, not an obtainable signal —
see §5.4)" at both sites.

## N45 — Two of the three round-7 prose fixes carry no binding, contrary to the response
The response opens: "each prose fix below reaches all three artifacts by construction and
is checked in all three by `scripts/08_verify_manuscript.py`". Tested by mutation:

| edit in `paper.md` only | result |
|---|---|
| `buys the last 0.038` → `0.048` (**N34**) | **311 bindings, 0 failures** |
| `captures +0.162 nDCG@10 of that +0.277` → `+0.192` (**N40**) | **311 bindings, 0 failures** |
| `about 0.11 nDCG@10` (§5.5) → `0.19` | **311 bindings, 0 failures** |
| `0.107 on top of the corpus-trained fusion` → `0.117` | 1 failure ✓ |
| `0.069 more than the strongest system…` → `0.079` | 2 failures ✓ |
| Table 2 MiniLM `0.136` → `0.146` | 1 failure ✓ |

N34's number — the one round 6 forced a correction on — is unguarded, as is N42's.

Related: `README.md:73` and `DATA_CARD.md:16` claim the verifier catches "a number edited
in one artifact and not another" and "re-checks every number … across all three
artifacts". In the N34 test `paper.md` said 0.048 while `paper_lncs.tex` said 0.038 and the
run was green — there is **no `paper.md` ↔ `paper_lncs.tex` numeric comparison at all**,
only tex→PDF.

**Fix — EDIT script + docs.** Add phrase bindings for "buys the last" (= `hybrid_rrf_dense
− hybrid_rrf`) and "captures +" (= the prefilter gain), and correct the two claims.

## N46 — N38's range guard is tighter but still acquits document-wide
The response says the old pattern "searched the whole document, so any unrelated sentence
… acquitted a genuinely merged range". The new code still searches the whole document — it
only demands a tighter needle. Demonstrated: merging **only** the Table 5 caption's
`0.46–0.53` yields **0 failures**, acquitted by the abstract's intact copy; merging both
yields 2 failures. This is not hypothetical — `pdftotext` returns the abstract's en-dash as
U+2013 and the caption's as `\x15`, so per-site divergence is exactly what this PDF does.
14 of the 15 `\d--\d` ranges occur twice, so 14 of 15 are single-site-blind.

The false-positive half is clean: all 15 ranges pass, `1--2-grams` folds correctly, and
both bibliography page ranges render with a visible dash. Nothing regressed.

**Fix — EDIT.** Check per occurrence, anchoring each range near a neighbouring word,
rather than searching globally.

## N47 — N37 fails only when a phrase is gone from *all* artifacts
Verified as claimed: removing "on top of the corpus-trained fusion" from all three does
fail. But removing it from **`paper.md` only** → 0 failures, and from the **PDF only** (a
stale PDF against a fixed source) → 0 failures. Since `paper.md` is the authored source and
the PDF is what a reader receives, "missing from one artifact" is the failure this gate
exists for.

Related extraction risk: `T1_LIGATURES` maps `\x1b`–`\x1f` and `\x15`, but this build also
emits **`\x16` for the em-dash** and **`\x10`/`\x11` for curly quotes**, unnormalised — so
any future binding phrase spanning an em-dash or a quoted string can never match in the PDF
artifact, and per the above, non-matching in one artifact is not a failure. Both current
phrases are plain ASCII and match 2/2/2, so nothing is broken today.

**Fix — EDIT.** Require the phrase in *every* artifact; add `\x16`, `\x10`, `\x11` to the
table.

## N48 — The SKIPPED branch drops the coverage caveat the log-present branch prints
The `else` says "…4 numeric table(s) were still checked row-by-row against the PDF". The
log-present branch adds "; 1 table(s) have no numeric cells and could not be". The caveat
is missing from exactly the branch every reader of the release sees, since `*.log` is
gitignored. It also does not mention that the verbatim-truncation check ran, which is what
protects the p21 block. **Fix:** hoist both out of the `if` so the branches agree.

## N49 — The 12 pt `.bbl` threshold works but is 3.6× the defect it was sized for
Tested with synthetic logs: 11 pt → note, 13 pt → FAIL, 3.3 pt (the shipped case) → note.
Exactly as claimed. But 12 pt is ~4.2 mm past the text block, plainly visible, and the note
asserts "no text is lost" without measuring it. Suggest 5 pt.

Worth knowing, and not a round-7 regression: the `.tex` **prose** overrun rule was never a
hard failure — `if _prose:` has always been a `print`, never `fails.append`. So no
body-prose overrun of any size fails the gate.

---

# MINOR

**M20** — Three inaccuracies in the response file itself: "+0.038 is half of the +0.066"
(it is 0.58; §5.3 correctly says **0.033** is half of 0.066); N40's third bullet is
labelled §5.5 but the sentence is in §5.4; and the opening "checked in all three" claim is
false for two of three fixes (N45).

**M21** — §6 juxtaposes raw scores with a ratio of differences: "the corrected control
scores 0.823 against 0.579 … so roughly half the available gain is captured (0.53)". A
reader computing 0.579/0.823 gets 0.70. §5.4 shows the arithmetic; §6 does not. One
parenthetical fixes it.

**M22** — §5.2's spread is anchored at MiniLM, itself a pretrained encoder, so "most of it
is crossed by corpus-trained channels alone" measures from a pretrained model's score. The
arithmetic is exact and the claim replaces a false one; bounding from the weakest
*corpus-trained* channel (w2v 0.1592) still gives 70%, so it survives either framing — say
which.

**M23** — M16's three new breakpoints (`BAAI/bge-base-en-v1.5`, `unswept_hyperparameters`,
`data/raw/MANIFEST.json`) do not fire in this build, but on any reflow `BAAI/` and `data/`
would leave 5-character line ends and `unswept_` / `hyperparameters` reads as two
identifiers. Suppress breakpoints that would leave under 8 characters.

**M24** — `notes/review-2026-09-07-round6/` has no README, unlike rounds 1–5, and its
findings file is named `REVIEWFINDINGSROUND6.md`, breaking the `REVIEW-FINDINGS-ROUNDn.md`
convention. DATA_CARD's review-folder bullet describes contents that folder does not have.

**M25** — `results/proposed_results.json` disagrees with itself by 1e-4:
`fraction_of_matched_control_recovered` = 0.5318 against `pool_sensitivity` row 300 =
0.5317. Both round to 0.53.

---

# Verified clean

**Margin profile byte-identical to round 6** — I re-derived the text-block edge
independently (480.6 pt, modal x1 over 413 justified lines) and measured every word on all
25 pages: p7 +15.2, p21 +35.9, p23 +3.3, nothing else above +2.3 pt. M16's extra
breakpoints and M19's ratio change introduced zero new overruns. **M18 holds** (zero
trailing `\allowbreak{}`); **M19 holds** (round 6's bare-`/` line end on p16 is gone); **no
path is hyphen-broken**.

**N39 behaves exactly as specified** under synthetic logs and did not weaken the prose
rule. **N38 produces no false positives.** **N36 is complete in both directions** — 26
shipped paths all documented, 22 promised paths all present, 2 excluded paths absent, and
the 14 additions are real.

**Number propagation r6 → r7:** exactly three decimals added (`0.038`, `0.069`, `0.277`),
nothing lost, all reaching the `.tex` and the PDF and agreeing with `results/`. The
abstract's "best **overall** of them" is now correct — LSA's 0.1830 on family B is exactly
why "overall" is needed.

---

# Verdict

**One edit.** N42 is a single sentence, and the fix is a phrase.

I would do N43 and N44 in the same pass: they are the same class, they sit in the abstract
and in §2 — the two places a reviewer meets the paper — and they have survived all seven
rounds because no binding covers a claim's *referent*, only its digits. N45 is the reason
why, and adding those two phrase bindings is what stops the next round from silently
regressing what this one fixed.

The mechanical work this round is the best of the seven and I could not break any of it.
Both gates now do what they say; the archive reproduces; the margin profile is unchanged to
the point; every number that moved propagates correctly and recomputes from `results/`.

The pattern held once more, and in its purest form yet: the fix for an ambiguous
wrong-parent phrase produced an unambiguous wrong-parent claim. Round 6's advice was to
sweep for the claim rather than the location. The refinement after seven rounds is to check
what the number is *attached to* — every "of that X", "on top of Y", "captures", "raises
to" — against the file that produced it, not against the sentence it replaced.
