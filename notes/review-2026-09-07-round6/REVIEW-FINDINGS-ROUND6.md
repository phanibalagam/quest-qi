# NO-GO — one sentence in §5.2 carries two false claims, and both new gates leak in the direction that matters.

Round-6 re-review of `…quest-qi_20260907.zip` (73 files, 4.89 MB), extracted to
`review/round6/r6/`. Response read at `notes/review-2026-09-07-round5/RESPONSE-TO-REVIEW.md`.

**Mean rigor: 9.0 / 10** (6.4 → 7.4 → 8.3 → 8.8 → 8.9 → 9.0).

**N26 is fixed where it was reported.** §2 now reads "0.107 on top of the corpus-trained
fusion (and 0.069 on top of the strongest system in that spread)". I recomputed both:
0.4097 − 0.3025 = 0.1072, 0.4097 − 0.3409 = 0.0688. Correct. The archive still reproduces
exactly — script 12 built 73 files against 73 shipped.

**But N26 landed in §2 and not in §5.2**, where the same asymmetry is argued — and that
sentence turns out to carry a second, independent error that no previous round caught.
Both new gates also leak: I swapped the two baselines in the LaTeX source and the verifier
still reported 307 bindings, 0 failures; and I added an undocumented review folder plus a
stray top-level file and the release script built a 75-file archive without a murmur.

---

# BLOCKING

## N33 — §5.2's asymmetry sentence quotes a gain against a baseline the sentence itself does not name
**Location** `paper.md:490–493`; `paper_lncs.tex:244`; PDF p12.

> "The spread across document representations here is 0.205 nDCG@10 **(MiniLM to Hybrid
> RRF + BGE)**, and it costs a 110-million-parameter encoder to cross most of it. Giving a
> system the query's true defect category is worth **0.107 on top of the corpus-trained
> fusion**, for free."

This is the same contrast N26 was raised about, and here it is sharper: the sentence
explicitly names the top of the spread as Hybrid RRF + BGE (0.3409), then quotes a gain
measured against `hybrid_rrf` (0.3025). Against the endpoint it just named, the figure is
**0.069**. §2 got the parenthetical this round; §5.2 did not.

**Fix — EDIT + rebuild.** Add the same parenthetical, or re-anchor the sentence.

## N34 — "it costs a 110-million-parameter encoder to cross most of it" is false, and the paper says so twice elsewhere
**Location** same sentence, `paper.md:490–491`.

Recomputed from `results/`:

| step | Δ nDCG@10 | share of the 0.205 spread |
|---|---|---|
| MiniLM 0.1359 → Hybrid RRF 0.3025 — **no downloaded weights** | 0.1666 | **81.3%** |
| Hybrid RRF 0.3025 → + BGE 0.3409 — the 110M encoder | 0.0384 | **18.7%** |

The encoder crosses under a fifth of the spread; corpus-trained channels cross four
fifths. The paper contradicts this at `paper.md:544` ("+0.038 … half of what fusion over
BM25 alone is worth (+0.066)") and again in the README's new M14 text ("the strongest
configuration that needs no downloaded weights").

**Why it matters** This is a new finding, not a residue of an old one, and it is the most
consequential wrong claim left in the manuscript: a reviewer reading only §5.2 takes away
the opposite of the paper's actual result about pretrained encoders — which is the result
§5.1 spends a page establishing.

**Fix — EDIT + rebuild.** "…and most of it is crossed by corpus-trained channels alone;
the pretrained encoder buys the last 0.038."

## N35 — N31's deleted superlative survives in the README, in a stronger and now false form
**Location** `README.md:28`.

> "*adding* it to the fusion is worth +0.038 (Holm p = 0.0), **the largest single gain in
> the table**."

N31 replaced this in `paper.md:447` and `paper_lncs.tex:223` with "it is the only
pretrained dense channel added to a fusion here, so there is nothing to rank it against" —
which is accurate. The README kept the superlative *and* dropped the "pretrained" qualifier
that made the paper's version merely unrankable, which makes the README's version simply
wrong: `hybrid_rrf − bm25` = +0.0662 and `hybrid_rrf − w2v` = +0.1433. §5.3 of the same
release says +0.038 is *half* of +0.066.

**Fix — EDIT.** Mirror the N31 wording.

## N36 — `DATA_CARD.md` is stale again, and N27's third check cannot see it
**Location** `DATA_CARD.md`; `scripts/12_release_package.py:204`.

`notes/review-2026-09-07-round5/` ships — three files, including the round-6 response
itself — and is named nowhere in the card, which stops at `-round4/`. Sixth consecutive
round in which the card is stale by exactly the folder the previous round added.

The new shipped→promised check cannot catch it:

```python
_tops = sorted({f.split("/")[0] for f in files if "/" in f})
```

`f.split("/")[0]` takes only the **first path segment**, so `notes/` satisfies it forever
however many review folders appear beneath it. And `if "/" in f` excludes every top-level
*file*, so `README.md`, `LICENSE`, `CITATION.cff`, `paper.md`, `paper_lncs.*` and
`references.bib` are all shipped and undocumented today, and a stray file would never be
noticed.

**Tested:** I added `notes/review-2026-09-07-round6/REVIEW.md` and `SCRATCH_NOTES.txt`,
re-ran script 12 → *"6 shipped director(y/ies) all documented"*, exit 0, archive grew to
**75 files**. Both of the refusals the response describes as now impossible.

To be fair to what did land: the shared-bullet hole is genuinely fixed (deleting
`-round3/` or `-round4/` now exits 1), and the check firing on `scripts/` and `figures/`
was real — both are now in the card, and all 14 promised paths exist.

**Fix — EDIT + RERUN.** Enumerate every directory prefix of every file, plus every
top-level file; add `-round5/` to the card.

## N37 — The new "on top of X" binding reads `paper.md` only
**Location** `scripts/08_verify_manuscript.py:1040–1055`.

The phrase loop iterates `paper_flat`, which is built from `paper.md` at line 46. The
`.tex` and the PDF are unguarded.

**Tested:** I swapped the two baselines inside `paper_lncs.tex` — "0.069 on top of the
corpus-trained fusion (and 0.107 on top of the strongest system in that spread)" — adding
and removing no decimal, so the cross-artifact set comparison stayed silent too. Result:
`307 bindings, 0 failure(s)`.

The exact defect class N26 names can now live in the LaTeX source and in the compiled PDF
a reader receives, behind a green gate. This is the same shape as round 2's B3 (the
verifier read `paper.md` while the disclaimer was missing from the `.tex`), and the fix is
the same one that worked then.

**Fix — EDIT.** Run the phrase loop over `ARTIFACTS["paper_lncs.tex"]` and
`ARTIFACTS["paper_lncs.pdf"]` as well.

---

# SHOULD-FIX

## N38 — N28's "appears nowhere separated" qualifier is a real hole
`08_verify_manuscript.py:1032` searches the **whole 25-page document** for a separated
form and does not require it to be the same occurrence. Demonstrated end-to-end on a
patched copy that mutates only the extracted PDF text: simulating `12--15` losing its
separator fails correctly on its own, but appending one unrelated sentence — "families 12,
15 and 18 were pooled." — produces **0 failures**. Today only `1--2` is masked by
accident, so nothing is hidden; the guard is one sentence away from silencing `12--15`
(the LNCS page limit) or `3--75` (the gold-size window).
**Fix:** require the separated match at a different offset, or restrict the search to a
±80-character window.

## N39 — The `.bbl` gate can never fire for a reader of the release, and would fail your own build
`:945` is `if os.path.exists(_log):` with no `else`. `paper_lncs.log` is correctly
gitignored, so the whole block — the unconditional `.bbl` failure, the prose-overrun note,
*and* the "N numeric tables checked row-by-row" note — is silently skipped, with no
warning. Meanwhile the bibliography does still overrun: PDF p23, `https://doi.` at
xMax 483.89 against a text-block edge of 480.6, i.e. **3.3 pt** over. So anyone who
recompiles gets an unconditional hard failure from a 3 pt overrun that has shipped in
every round.
**Fix:** print "overfull-box check SKIPPED (paper_lncs.log absent)" in the `else`, and
either fix the `.bbl` overrun or give that rule a threshold.

## N40 — Three more baseline/reference phrasings worth tightening
The wrong-baseline class survived five rounds; these are the remaining instances:

- **Abstract, `paper.md:30`** — "the best of them scores 0.193, 0.151, 0.161 and 0.024 on
  the four question families". Per family the best is not always `hybrid_rrf_dense`: on
  family B, LSA reaches **0.1830** against the quoted 0.1510. The intended reading ("best
  overall") is defensible; say "the best overall of them".
- **`paper.md:151`** — "0.069 **on top of** the strongest system in that spread". `qir_oracle`
  is built on the `hybrid_rrf` backbone (`05_taxonomy_aware_retrieval.py:377`); the
  dense-base rerun covers only the two priors. So 0.069 is a difference between systems on
  *different* backbones, not an increment added on top of `hybrid_rrf_dense`. Say "0.069
  more than the strongest system in that spread reaches on its own".
- **`paper.md:~596`** — "captures 0.162 of it" reads as a fraction and is an absolute
  (0.4644 − 0.3025); as a share it would be 0.58. Say "captures +0.162 nDCG@10 of that
  +0.277".

## N41 — The response overstates N29 by one clause
*"…no path is hyphen-broken in the rebuilt PDF; the only hyphenated break left is ordinary
word hyphenation of 'stability'."* The first clause is **true** and I verified it: all 17
long `\texttt` tokens either render whole or break at an inserted `\allowbreak` with no
character added, no fragment under 8 characters, and no break that reads as two words. The
83 pt round-4 overrun did not return — that path now sits 192 pt inside the margin. But the
PDF contains dozens of ordinary hyphenated breaks (`prod-`, `conse-`, `ques-`,
`bibliogra-`…), not one. Harmless to the paper; the kind of claim a reviewer spot-checks.

---

# MINOR

**M16** — `10_build_latex.py:106` gates breakpoints on `len(raw) > 24` measured on the
*escaped* string, so `results/corpus_stats.json` (25) gets them while
`data/raw/MANIFEST.json` (22) and `BAAI/bge-base-en-v1.5` (21) do not. All fit today;
the threshold will bite on the next path added.

**M17** — N31's replacement leaves an unclosed em-dash at `paper_lncs.tex:223` /
`paper.md:447`: the dash opens a parenthetical that closes with a comma.

**M18** — `paper_lncs.tex:429` ends a token with `enforcement/\allowbreak{}` — a
breakpoint after the final character, an artifact of the blanket `.replace("/", …)`.

**M19** — PDF p16 ends a body line on a bare `/` (the ratio `(0.423 − 0.302) /`).
Pre-existing.

---

# Verified clean

**Margin profile is identical to round 5 to the point** — I measured every word on all 25
pages against a text-block edge of 480.6 pt in both builds: p7 Table 1 max +15.2 pt, p21
verbatim +35.9 pt, p23 bibliography +3.3 pt. Nothing new, nothing worse.

**Number propagation r5 → r6:** nothing lost, exactly one decimal added — `0.069` — which
reaches the `.tex` and the PDF and recomputes correctly. `md − pdf` is empty; the only
`.tex`-not-in-`md` values are `0.62` (a column width) and `4.7` (a comment).

**Every ratio, difference and percentage in the paper recomputed from `results/`**: the
0.205 spread, +0.014 CI [−0.005, 0.033] Holm 0.304, +0.020 CI [0.0002, 0.041] p 0.048/0.096,
the 11% relative figure, SE ≈ 0.010, +0.066, +0.121/+0.162/+0.277/+0.454/+0.520, 0.434 CI
[0.29, 0.55], 0.53 and all six pool-sensitivity rows, "pessimistic by 0.24", 27 points of
category accuracy, recall@50 +0.05, and the macro values 0.296/0.280/0.343. All correct.
The only wrong-baseline instances are N33, N34 and N40.

**N29, N31, N32, M14 all landed and are true**, except that N31 did not reach the README
(N35). N31's claim is accurate against Table 2: `04_retrieval.py:279` builds
`hybrid_rrf_dense` as BM25+LSA+BGE only, and MiniLM is never fused.

---

# Verdict

**Fix N33, N34 and N35 and the paper is done.** Three prose edits and a rebuild. N34 is
the one to look at first — it is a new finding, not a residue, and it is the only
remaining sentence in the manuscript that would give a reviewer the opposite of your
actual result.

N36 and N37 are the gates, and both leak in the direction that matters: the binding
written to catch wrong-baseline claims reads only the file where the claim was already
fixed, and the check written to stop undocumented directories reads only the first path
segment. Both are small edits, and both are worth doing before paper 2 inherits the
tooling — the second especially, because it has now failed to catch the same thing six
rounds running.

What is settled: the archive is built by the release script and reproduces exactly; the
row-anchored table check holds; the shared-bullet hole is closed; `hyphenat` is gone and
the paths render correctly without reintroducing the margin overrun; every number in the
paper except the three named above recomputes from `results/`; and not one decimal moved
between rounds.

The pattern held again, and it is worth naming precisely because it is now the only thing
between this paper and submission: for six rounds the error has been a correction landing
in one place and not the others, and each round the "others" has been somewhere further
in — the archive, the artifact, the sentence describing the fix, the second file stating
the same claim. This round it was §5.2, one section away from the §2 sentence that was
fixed. Sweep for the claim, not for the location.
