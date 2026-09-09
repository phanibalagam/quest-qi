# NO-GO — on one sentence. Fix it and rebuild, and this is a GO.

Round-3 re-review of `quest-qi_release.tar.gz` (63 files, 5.2 MB packed), extracted to
`review/round3/rel/`. Response read at
`notes/review-2026-09-07-round2/RESPONSE-TO-REVIEW.md`.

**Mean rigor: 8.3 / 10** (6.4 → 7.4 → 8.3). All four round-2 blocking findings are
genuinely fixed, and I verified each in the artifact rather than in the response. One new
blocking finding, one sentence long. Two of the round-3 hardening changes do not enforce
what the response says they enforce — important, but neither is a claim in the paper.

**Two of my round-2 citation findings were wrong, and the response is right about both.**
Corrected below and in `CITATIONS-ROUND3.md`. That matters here more than usual, because
this round's blocking finding is about a claim that was conceded and then re-asserted —
and I am not in a position to make that point without first fixing my own.

---

## What is genuinely fixed — verified, not taken on trust

**N1 — Table 1 renders complete.** `pdftotext -layout` gives all nine columns with the
macro and MRR values present:

```
System                    R@10 R@50 R@100 P@10 nDCG@10 (micro) 95% CI (cluster) nDCG@10 (macro) MRR
BGE-base (pretrained)     0.239 0.380 0.436 0.201    0.288    [0.215, 0.393]        0.296  0.410
Hybrid RRF (BM25 + LSA)   0.260 0.396 0.457 0.211    0.302    [0.225, 0.420]        0.280  0.410
```

Independently: of 200 decimals in `paper_lncs.tex`, exactly one is absent from the PDF —
`0.62`, from `p{0.62\linewidth}`, a column width and not a claim. Fixed at the cause in
`parse_table()`, not by hand.

**N2 — "negative result" is gone** from `paper.md` and `paper_lncs.tex` (0 occurrences in
each). **N3 —** both paragraphs now say "eight in script 05", matching the 8 contrasts
carrying `p_holm` in `proposed_results.json`. **N4 —** Limitations retitled "The encoding
step needs network access and a working certificate store"; §4's "constraint a regulated
organization faces" is gone; `dense_manifest.json` and `scripts/09`'s docstring both
reframed as TLS/egress. **N9, N10, M1, M3** all done — captions are single-numbered
("Table 1:" not "Table 1. Table 1:") and the §3.3 table wraps instead of being cut.

**N7 — the verifier is now real, and I tested it by breaking things.** It prints
`bindings: 195 check() · 20 states() · 31 in_text() · 44 cross-artifact` and the artifact
list. In a scratch copy I reintroduced both failure modes:

```
FAIL: Table 1 in paper.md: row 'BGE-base (pretrained)' column macro reads 0.396
      but results/ says 0.2963
FAIL: 1 number(s) present in paper_lncs.tex do not appear in the compiled PDF …
      ['0.987']                                        (exit code 1)
```

Both caught, both clean again on restore. The exclusion for `0.62` is principled — the
check strips `[pmb]{…\linewidth}` and the first argument of
`\setlength|\hspace|\vspace|\resizebox` before extracting numbers — not a hard-coded
ignore list. This is the structural change I asked for, and it works.

**Citations are clean.** 37 entries, 37 `\bibitem`s. `robertson2009bm25` is now
3(4):333–389 with a note recording why it disagrees with CrossRef — that note is a model
of how to handle a bad publisher deposit. Fuhr is 2017, Rahmani has its DOI and pages.

---

## Where I was wrong in round 2

Both disputes in the response are **upheld**. I checked the round-2 `references.bib`
directly rather than re-reading my own report:

- **"Three versions of record kept preprint years" — false.** The round-2 bib already
  carried `year = {2023}` for `singhal2022clinicalknowledge`, `ji2022hallucination` and
  `rashkin2021attribution`, and `year = {2024}` for `es2023ragas`, each with the correct
  journal, volume, pages and DOI.
- **"Nine of the twelve new entries have no DOI or page range" — false.** I counted the
  round-2 bib programmatically: **one**, `rahmani2024synthetic`.

What happened is worth naming, because it is the same failure I have been charging the
manuscript with. My citation subagent returned a correct per-entry table listing the
right values for each reference; I aggregated those into summary claims about what was
*missing* without checking them against the shipped `.bib`. The per-entry table was
accurate; the summary I built on top of it was not. Deduct accordingly from round 2's
`CITATIONS-UNVERIFIED.md` §2 and §3 — the rest of that file, including the BM25
adjudication, stands.

---

# BLOCKING

## N11 — The false superlative was moved, not removed, and its new home is the paper's central power argument

**Location** `paper.md:531–533`; `paper_lncs.tex:256`; PDF p. 13, §5.3.

**Problem** The response says, at line 88:

> "**N8 — the superlative was false and is removed.** '+0.038 … the largest single
> improvement in this table' was wrong: fusion over BM25 alone is +0.066."

The edit landed in §5.1, which now correctly reads "the largest gain from adding a dense
channel". In §5.3 the same superlative is re-asserted, attached to the other number:

> "The interval runs to +0.033 nDCG@10 at its upper end, an 11% relative gain over the
> 0.302 base, comparable to what adding BGE to the fusion buys (+0.038) and half of what
> fusion buys over BM25 alone (+0.066), **the largest single improvement in Table 1**."

It is still false. From `results/retrieval_results.json`, contrasts against Hybrid RRF:

| contrast | Δ nDCG@10 |
|---|---|
| hybrid_rrf − minilm | **+0.1666** |
| hybrid_rrf − w2v | **+0.1433** |
| hybrid_rrf_dense − bm25 | **+0.1046** |
| hybrid_rrf − bm25 | +0.0662 ← claimed largest |

And the manuscript refutes itself two pages earlier, at `paper.md:483`: "The spread across
document representations here is **0.205** nDCG@10 (MiniLM to Hybrid RRF + BGE)."

**Why it matters** Round 2 flagged this claim; the response conceded it in writing; the
correction reached one of the two sites. It now sits inside the sentence that calibrates
the paper's central inconclusive-null argument — the reader is asked to judge +0.033
against a benchmark that is mis-stated by a factor of 2.5. A reviewer who checks Table 1
finds the paper contradicting itself, in the paragraph the paper most needs to be trusted
in, on a point the author has already been told about once.

**Fix — EDIT + rebuild.** Delete the appositive: "…and half of what fusion over BM25 alone
is worth (+0.066)." Do not substitute another superlative. Rebuild `.tex` and PDF via
`10_build_latex.py --compile`, re-run the verifier.

---

# SHOULD-FIX

## N12 — The tex-vs-PDF check is a global set difference, so it does not catch N1's class in general
`scripts/08_verify_manuscript.py:771–774`:

```python
_tex_nums = set(re.findall(r"\d+\.\d+", _tex_data))
_pdf_nums = set(re.findall(r"\d+\.\d+", ARTIFACTS["paper_lncs.pdf"]))
_lost = sorted(_tex_nums - _pdf_nums, key=float)
```

The response calls this "the check that catches N1's whole class, whatever the cause". It
catches N1 specifically because those six MRR values appear nowhere else in the document.
It is set membership, not position: a value truncated out of a table passes as long as the
same string occurs anywhere else. Simulating Table 2 losing its entire **nDCG@10** column
— the paper's headline metric, N1's exact failure mode one table over — reports **zero
failures**, because 0.302 and 0.317 also appear in §5.3 and §5.4 prose. Across the four
tables, 55 of 142 numeric cells are shadowed this way (Table 2: 17 of 23). Table 1's own
binding does not close the gap: for the PDF it checks row-label presence only
(`:416–421`).

**Fix — EDIT (script only).** Parse Tables 2, 3 and 3b out of the PDF row-wise the way
Table 1 is parsed out of `paper.md`/`.tex`, or require each table body's numbers to appear
*within that table's block* in the PDF rather than anywhere in it.

## N13 — `12_release_package.py`'s "refuses to build" guarantee is unreachable
Tested in a scratch copy: I created `data/processed/dense_embeddings.npz` and
`data/raw/openfda/x.zip`, ran the script, and it built successfully and silently —
`wrote quest-qi_release.tar.gz / 63 files … 5.2 MB packed`, exit 0. `MUST_NOT_SHIP` is
checked against `files`, which is already the post-`.gitignore` set (`:83–85`), so it can
only fire if `.gitignore` is itself broken. The script also never reads `DATA_CARD.md`,
so "anything the data card describes as absent" is not what is enforced — it is a
two-item hard-coded list. The *behaviour* is right (neither file shipped); the *guarantee*
is not tested by anything.

**Fix — EDIT.** Run the `MUST_NOT_SHIP` scan over the raw `os.walk` result before
`.gitignore` filtering, so it reports when a forbidden file is present-but-excluded; and
either parse the data card's "What is not, and why" list or reword the docstring.

## N14 — `_superseded_20260907/` ships unannounced, and one file in it is misleading
The folder is in no manifest: `grep -n "_superseded" README.md DATA_CARD.md paper.md
paper_lncs.tex scripts/*.py .gitignore` returns nothing, so `DATA_CARD.md`'s "What is in
this repository" omits 13 files and 2.4 MB of the release. There is no README in the
folder saying it is withdrawn and must not be cited. Three specifics:

- `_superseded_20260907/generation_runs.json` (1.9 MB) is **byte-identical** to
  `results/retrieval_runs_proposed.json` (both sha256 `9c28ecdc…b9c0`). It is not
  generation output at all — it is script 05's retrieval rankings, preserved under the
  name the round-1 clobbering bug gave them. A reviewer opening it to audit the withdrawn
  study finds retrieval data.
- `_superseded_20260907/06_generation_harness.py:38` still reads `# the honest text-only
  pipeline; see paper Sec. 5.6`. There is no §5.6 — which also means the response's N10
  claim that script 04 held "the last surviving generation reference in the package" is
  not quite right.
- The verifier's `.py` disclaimer loop is `for _d in ("scripts", "figures")` (`:747`), so
  the folder is outside it. Both scripts do carry the notice — I checked — but nothing
  enforces it.

**Fix — EDIT.** Add `_superseded_20260907/README.md` ("Withdrawn from the manuscript on
2026-09-07, retained for audit only; nothing here is cited by the paper and none of it
should be"), list the folder in `DATA_CARD.md`, delete or rename the duplicate
`generation_runs.json`, strike the Sec. 5.6 comment, extend the disclaimer loop.

## N15 — §6 was not touched by N2, and still leads with a demonstrated absence
`paper.md:726`: **"The diagnosis survives; the fix did not."** The paragraph recovers four
sentences later ("'not enough' here means the benchmark could not separate +0.014 from
zero, not that the effect is absent"), but the bolded lead is what a skimming reviewer
takes. The round2→round3 diff shows zero changes in §6. §8's only hedge is "with a
confidence interval spanning zero". **Fix — EDIT + rebuild:** "The diagnosis survives; the
fix is unresolved", plus one clause in §8.

## N16 — §6 drops a qualifier and the sentence becomes false
`paper.md:718`: "Getting either wrong moves the number by more than any system in the
table." The Introduction says the same thing correctly at `:182` — "more than any system
in our **Table 1**". §6 sits in a paragraph about Table 3, where `Centroid prior +
metadata filter` is +0.277, larger than the 0.242 mis-specification gap. **Fix — EDIT:**
restore "in Table 1".

## N17 — Float numbering is internally consistent but bibliographically wrong
Suppressing the auto-label (`\captionsetup{labelformat=empty}`) was safe — there are zero
`\ref`/`\label` in the `.tex`, so nothing broke. But nothing now enforces order or
citation either. In PDF page order the captions run **Figure 3 (p.6), Table 1 (p.10),
Figure 2 (p.11), Figure 1 (p.12)** — figures appear 3, 2, 1, against the universal rule
that figures are numbered in order of first appearance. Figure 1, Figure 3 and Table 3b
are never cited in the body. The §3.3 example-question table has no caption at all. And
"Table 3b" is not a legal LNCS number — it should be Table 4. **Fix — EDIT + rebuild:**
renumber figures to appearance order, cite every float once, caption the §3.3 table,
promote 3b to Table 4.

## N18 — The README's reproduce block omits script 09
`README.md:37–48` runs 01–05, `gen_figures.py`, 10, 08, 11, 12 — no script 09 — then says
`08_verify_manuscript.py` "must print 0 failures". Followed literally, `dense_embeddings.npz`
is absent, scripts 04/05 skip every dense channel, and Table 1 loses the two rows the
verifier parses. **Fix — EDIT:** insert script 09 before 04 with its network caveat.

---

# MINOR

**M5 — the response's release figures are stale.** "The release is 45 files, 4.5 MB
packed" (`RESPONSE-TO-REVIEW.md:48`); the shipped tarball is **63 files, 5,245,884 bytes**.
The gap is exactly 63 − 13 − 5: `_superseded_20260907/` and
`notes/review-2026-09-07-round2/` were added after the count was written. Same class as
N11, with nothing at stake.

**M6 — the MANIFEST digest check is vacuous in the release.** `:812` skips when the file
is absent, and the release ships only `MANIFEST.json`, so zero files are hashed. (The
digest itself is genuine — I verified `7f63ce0a…ec4f` against the round-2 copy of the
export.) Print a note so a green run is not over-read.

**M7 — the summary line still has no count.** `:827` prints `checks run, 0 failure(s)`.
The binding counts are on the line above now, so this is cosmetic — but finish the job.

**M8 — PDF text extraction loses ligatures and en-dashes** ("findings"→"ndings",
"0.46–0.53"→"0.460.53"), and there is no `/Outlines`. `\usepackage{cmap}` fixes the
ToUnicode maps. Pre-existing. Also `pdfinfo` shows `Creator: scripts/10buildlatex.py` —
underscores eaten from the hyperref string.

**M9 — `CITATION.cff`** names `github.com/phanibalagam/quest-qi` while the manuscript's
`\url{}` points at the bare user page; the file has no `version`, `date-released` or DOI.

---

# Verdict, and what round 4 looks like

**One sentence stands between this and a GO.** N11 is a single appositive clause in
§5.3 plus a rebuild. Everything else is hardening or hygiene, and none of it is a false
claim in the paper.

That said, the two artifacts the response nominates as "the change that is meant to stop
a round 5" — the tex-vs-PDF check and the release script's refusal — do not enforce what
they are advertised to enforce. Neither is a defect in the manuscript, and I would not
hold submission for either. But if the intent is that the next paper in the programme
inherits a gate rather than a report, N12 and N13 are the two to fix properly, and N12 is
the one that matters: parse the other three tables out of the PDF the way Table 1 is
parsed out of the source, and the class of failure that has decided three of these four
rounds stops being possible.

**Does this need a round 4?** It needs a revision pass, not a review round. Fix N11,
rebuild, re-run the verifier; do N15, N16, N17, N18 in the same pass since they are all
one-line edits in `paper.md`; add the `_superseded` notice and delete the duplicate; then
harden N12 and N13 at leisure. I do not need to see it again before you submit — send it
if you want the check, but the go/no-go is now in your hands and the verifier will tell
you more than I will.

The paper itself is in good shape: an honestly-scoped resource-and-warning contribution,
a correctly-labelled inconclusive null, a benchmark whose provenance is disclosed in the
abstract, and artifact discipline that is now genuinely better than most published work.
The two items still open — gold-set adjudication and investigator-written questions — are
correctly identified in your response as not blocking arXiv and as the first thing a
conference reviewer will ask for.
