# NO-GO — do not submit. Four blocking findings, all four edit-only. A round 4 will be needed, and it will be short.

Round-2 adversarial re-review of
`01_regulatory-grade-genai-quality-investigations_quest-qi_20260907.tar` (46 files,
48.6 MB uncompressed), extracted to `review/round2/extracted/`.

**This is a large, real improvement.** Twenty of the twenty-five round-1 findings are
resolved and I verified them in the code, not in the response. §5.6 was cut cleanly, §2 was
rewritten against the literature it was missing, the disclaimer now reaches all three
artifacts and the converter hard-fails without it, the Holm exclusion is a genuine code
change, the MANIFEST's SHA-256 verifies against the shipped export, and
`scripts/11_arxiv_package.py` produces a correct 59 KB submission tarball. The rigor score
moves from 6.4 to **7.4**.

It still cannot go out. Every blocking finding below is a propagation failure, not an
analysis failure — a correction applied where the reviewer pointed and not where the same
fact is stated elsewhere. Three of the four are round-2 regressions, documented separately
in `REGRESSION-REPORT.md`. All four are edits plus a PDF rebuild; none needs a rerun.

**On your prediction that round 1's fix becomes round 2's blocker: it happened again, in
four places.** The response document is largely accurate about what was changed, but it is
accurate about the *edit*, not about the *artifact*. The clearest case: the fix for the
most serious round-1 finding — the hidden macro-average — put a macro column into
`paper.md` and overflowed Table 1 by 151 pt in LaTeX, so the macro-average is **absent from
the typeset PDF**. Verifier: clean run.

---

## Panel verdict

| Seat | Round 1 | Round 2 | Note |
|---|---|---|---|
| Journal-fit / venue | 5.0 | **7.5** | Extended-preprint status now stated, no venue claimed, AI-use disclosure added. 24 pages is fine for arXiv. |
| R1 — methodology & statistics | 6.0 | **7.0** | Null correctly reframed *in §5.3*; Holm family correctly narrowed. Uncertainty from model fitting is now disclosed but still not measured. |
| R2 — domain & regulatory | 7.5 | **7.5** | Regulatory content clean for a second round. The environment-vs-constraint framing is still wrong, and now contradicted by the package itself. |
| R3 — reproducibility & artifacts | 7.0 | **7.5** | MANIFEST + digests verify; arXiv packager is good. Release built from the working dir, not the repo. |
| Devil's Advocate | 6.5 | **7.0** | Contribution honestly resized. The paper is now a defensible resource/short-track submission; still not a full-track research result. |

**Mean rigor: 7.4 / 10** (was 6.4). **Consensus: Major revision — but a short one.**

---

# PHASE 1 — Every round-1 finding, verified against the package

Legend: **R** resolved · **P** partially resolved · **N** not resolved · **D** disputed

| # | Round-1 finding | Status | Verified how / what remains |
|---|---|---|---|
| B1 | Environmental limitation stated as external constraint | **P** | §5.6 cut, which removes the rerun. But `paper.md:294` still reads "no external API and no data leaving the boundary, **which is the constraint a regulated organization faces**" — unchanged. The Limitations heading is still "The encoding step is **not reproducible** inside the analysis boundary" while `dense_embeddings.npz` now **ships in the tarball**. `results/dense_manifest.json` still records `"host": "windows (only host with huggingface.co reachable)"`. `scripts/09_dense_encode.py`'s docstring is byte-identical to round 1. See **N4**. |
| — | *(author's dispute: "B1 conflates two constraints")* | **D — partly upheld** | The distinction is real: a TLS-trust failure to huggingface.co and the absence of a generation endpoint are logically independent, and the review should have separated them. But the author concedes the operative point ("there was no logged evidence of an attempt") and cut §5.6 anyway, so the dispute changes the reasoning and not the outcome. Upheld as a correction to the review's wording; the finding stands. |
| B2 | Macro-average reversal unreported | **P** | Table 1 in `paper.md` now carries micro, cluster CI **and** macro for all 8 systems; every cell reconciles to `results/retrieval_results.json` to printed precision, and the macro values recompute exactly as the unweighted mean of the six `by_family` entries. §5.1 states the reversal and names `C_firm_history` (0.759 vs 0.658, 31 of 119) — verified against `by_family`. "so the failure is not a representation deficit" is gone from the abstract. **But the macro column does not render in the PDF — see N1.** |
| B3 | Disclaimer absent from `.tex` and PDF | **R** | `\section*{Disclaimer}` at `paper_lncs.tex:30`; present in the extracted PDF text; `scripts/10_build_latex.py` hard-fails without it; `08_verify_manuscript.py:513–556` checks `.md`, `.tex` and pdftotext output, ligature-proofed against T1 encoding. Genuinely fixed, and fixed at the cause (the front-matter parser was consuming everything up to `## Abstract`). |
| B4 | Table 4 denominators | **R** | Removed with §5.6. |
| B5 | False novelty claim | **R** | Sentence gone. §2 rewritten; 12 new references, all verified to exist with correct title/first author/venue (see `CITATIONS-UNVERIFIED.md`). The claim is now the two-factor control recipe. |
| B6 | Template generation undisclosed | **R** | Abstract, Contribution 1, §3.3 and a new first Limitations paragraph all state six templates / 15 distinct stems / no human adjudication. Verified independently against `data/processed/benchmark.jsonl`: 171 questions, 171 distinct strings, exactly **15** distinct 45-char stems. |
| B7 | Null presented as a demonstrated absence | **P** | §5.3 rewritten well — interval to +0.033, no equivalence claim available, ~2× query count needed. **But "negative result" survives in the abstract, Contribution 4, and twice inside §5.3 itself — see N2.** |
| S1 | Table 1 without intervals | **P** | Cluster CIs added and correct in source; invisible in the PDF (**N1**). |
| S2 | "four in Table 1" vs seven | **P** | Fixed in the Statistics paragraph. The Reproducibility paragraph now says "**eleven** in script 05" against Statistics' "**eight**" — the same defect one paragraph later (**N3**). |
| S3 | Holm family padded with certainties | **R** | Real code change: `scripts/05` slices `raw_p[:len(contrast_systems)]`, family = 8, the three controls get `p_holm: None` plus a note. The author's claim that every adjusted p is unchanged is **true** — verified by diffing OLD↔NEW `proposed_results.json` (only the three controls moved, `0.0 → None`), and true by construction since the removed p were the smallest in the family. |
| S4/S5/S6 | Single-seed training; 15-cluster bootstrap; percentile ratio CI | **P — disclosure only** | A new paragraph states the bootstrap resamples queries only and carries no uncertainty from the corpus, taxonomy, classifier or templates. That is the honest disclosure and it is worth having. None of the three underlying issues is *fixed*: still one seed for word2vec/SVD/logistic regression, still a percentile cluster bootstrap on 15 informative clusters, still a plain percentile interval on a ratio, still no w2v-vs-MiniLM contrast, and MiniLM's 0.0173 on family E — above LSA and BGE, on the family carrying the flagship diagnosis — is still unmentioned. Acceptable for a preprint if the disclosure is explicit; a conference reviewer will ask. |
| S7 | `unswept_hyperparameters` incomplete | **R** | `gold_set_size_window: [3, 75]` present, matches `scripts/03` `MIN_GOLD, MAX_GOLD = 3, 75` and the paper's "3–75". |
| S8 | "flat from λ = 2" | **R** | Now "flat from 4"; `lambda_selection` dev curve is `{2.0: 0.8489, 4.0: 0.8519, 8.0: 0.8519, 16.0: 0.8519}`. Correct. |
| S9 | `MANIFEST.json` missing; digests elided | **R, with a new problem** | MANIFEST ships; its SHA-256 `7f63ce0a…ec4f` **verifies** against the shipped zip. All three `DATA_CARD.md` digests un-elided and **verified**. But the raw export and the embeddings now ship while three documents say they don't (**N5**). |
| S10 | `CITATION.cff` invalid YAML | **R** | `yaml.safe_load` parses. |
| S11 | arXiv mechanics | **R** | `.bbl` ships (37 `\bibitem`s, matching 37 bib entries and 37 cited keys); `\includegraphics` switched to the three vector PDFs; `scripts/11_arxiv_package.py` builds a clean 59 KB tarball and refuses raster figures; AI-use disclosure section present in `.md`, `.tex` and PDF. Build artifacts now ship in the repo archive (**minor, see M2**). |
| S12 | 22 pages, no venue | **R** | `paper.md:875`: "This version is an extended preprint… the LNCS class is used here for typesetting only and no venue is claimed." Now 24 pages. |
| S13 | Script 03 comment contradicts §3.3 | **R** | Corrected. |
| S14 | Citation metadata | **D — dispute NOT upheld; plus new errors** | The BM25 rebuttal is wrong; see **N6** and `CITATIONS-UNVERIFIED.md` §1. The version-of-record upgrades are correct in venue but introduced four wrong `year` fields. |
| M1 | AI-tells | **P** | "honest" as a self-applied adjective reduced to one; the 0.53 figure from five sites to three; the long bolded run in Limitations merged. Not re-audited in full. |
| M2 | Stale design note | **R** | `notes/00-study-design.md` carries a "superseded working note… where this note and the manuscript disagree, the manuscript is right" banner. |
| M3 | Verifier framing overstated | **P** | The docstring is now exemplary about what it cannot catch. The structural gaps remain, and the README now overstates in the docstring's place (**N7**, Phase 3). |
| M4 | Code hygiene | **P** | Script 05's run-file collision was silently fixed (it was overwriting `generation_runs.json`); the renamed output does not ship (`REGRESSION-REPORT.md` R6). |

**Score: 20 resolved, 8 partial, 0 not-resolved-outright, 2 disputes adjudicated (1 upheld
in reasoning only, 1 rejected).**

---

# BLOCKING (round 2)

## N1 — Table 1's macro column and MRR column are missing from the typeset PDF
**Location** `paper_lncs.tex:170` (`\begin{tabular}{lrrrrrrrr}`); `paper_lncs.log:875`.
**Problem** `Overfull \hbox (151.54454pt too wide)`. The PDF header truncates mid-word —
`… nDCG@10 (macro) M` — and rows stop after two numeric columns. Diffing decimals in the
`.tex` against `pdftotext` output: `0.245, 0.256, 0.333, 0.364, 0.412, 0.500` (the whole
MRR column) and all eight macro values are in the source and **not in the PDF**. The same
diff on the round-1 package returns empty — round 1's seven-column table typeset fine.
**Why it matters** This is the fix for round-1 B2, the finding an editor would read as
selective reporting. In the artifact a reviewer receives, the macro-average is still not
there. The finding is, from the reader's side, not fixed.
**Fix — EDIT + rebuild.** `\resizebox{\textwidth}{!}{…}`, or `\footnotesize` with
`\setlength{\tabcolsep}{3pt}`, or split into two tables. Then diff the `.tex` decimals
against the rebuilt PDF's text before shipping.

## N2 — The abstract and contribution list still call the null a "negative result"
**Location** `paper.md:39` (Abstract), `:115` (Contribution 4), `:509`, `:566`; mirrored in
`paper_lncs.tex` and the PDF.
**Problem** §5.3 now says, at `:524`, "This null is inconclusive, not a demonstration of no
effect, and we do not have the sample size to make it one." Forty-two lines later, `:566`
says "This is the paper's central **negative result**." The abstract and Contribution 4
say the same.
**Why it matters** The paper's identity is at stake in exactly this word. A manuscript
that argues it lacks the power to demonstrate absence and then asserts absence as its
central result invites the reviewer to conclude the rewrite was cosmetic. The abstract is
the version most readers keep.
**Fix — EDIT.** Replace at all four sites in both files with "inconclusive null" / "a null
we cannot resolve at this sample size". Rebuild.

## N3 — The manuscript states two different Holm family sizes for script 05
**Location** `paper.md:369` ("**eight** in script 05") vs `paper.md:905` ("**eleven** in
script 05"); identically in `paper_lncs.tex:157` vs `:387`; both in the PDF.
**Problem** The code family is eight. "Eleven" is the round-1 number, left in the
Reproducibility paragraph when the Statistics paragraph was rewritten.
**Why it matters** This is round-1 finding S2 recreated one paragraph away, in the two
places a methodological reviewer checks against each other, in a paper about evaluation
rigour. Twice in two rounds is a process signal, not a typo.
**Fix — EDIT.** `paper.md:905` / `paper_lncs.tex:387` → "seven in script 04, eight in
script 05, three gold controls reported with raw p only, and two more in the Section 5.3
robustness pair." Rebuild.

## N4 — The encoding limitation is still stated as external, and the package now contradicts it
**Location** `paper.md:294` (§4) and `paper.md:789` (Limitations);
`results/dense_manifest.json`; `scripts/09_dense_encode.py:7–10`.
**Problem** Two things, one unfixed and one newly broken.

*(a) Unfixed.* §4 still reads: "with no external API and **no data leaving the boundary,
which is the constraint a regulated organization faces**." Round 1 asked for this to be
restated as a design choice the author adopted because it is realistic for on-premise
deployment, not as a constraint the author was under. It is byte-identical to round 1.
`dense_manifest.json` still records `"host": "windows (only host with huggingface.co
reachable)"`, and `scripts/09`'s docstring is unchanged.

*(b) Newly broken.* The Limitations paragraph is now self-contradictory. Its heading and
first sentence still assert "**The encoding step is not reproducible inside the analysis
boundary** … reproducing it requires reaching huggingface.co, which the analysis host
cannot do", and the added sentence correctly names the cause as "a certificate-trust and
network-policy one". But `data/processed/dense_embeddings.npz` — the artifact that
paragraph says a reader cannot regenerate — **is in the tarball**, 20.6 MB of it.

**Why it matters** This is the round-1 priority finding in a new form. A limitation stated
as external, contradicted this time not by a script docstring but by the package's own
contents. It is the one class of defect that reads as a correctness problem rather than a
wording problem, and it has now survived a round that explicitly addressed it.
**Fix — EDIT.** Retitle to "The encoding step needs network access and a working
certificate store". Say plainly: the encoders run locally once `truststore` injects the
system certificate store; the embeddings ship (or are regenerable in about six minutes on
CPU); nothing about this is a property of a regulated deployment. Restate §4's sentence as
a design choice. Correct `dense_manifest.json`'s host string and `scripts/09`'s docstring.
No rerun — the encoders already ran, and their output is in the box.

---

# SHOULD-FIX

## N5 — The release ships two files that three documents say it does not ship
`data/raw/…json.zip` (4.0 MB) and `data/processed/dense_embeddings.npz` (20.6 MB) are in
the tarball. `.gitignore` excludes both. `DATA_CARD.md` lists both under "**What is not,
and why**". `data/raw/MANIFEST.json` says "Raw export is **not mirrored** in this
repository." The release was built by archiving the working directory rather than the
tracked repo. **Fix — EDIT + repackage:** decide whether the data ships and make the three
documents agree; `git archive` drops the tarball from 48.6 MB to about 8 MB. Full detail
in `REGRESSION-REPORT.md` R4.

## N6 — The BM25 citation dispute goes against the response, and four `year` fields are now wrong
`robertson2009bm25` is **Vol. 3, No. 4 (2009), pp. 333–389**. CrossRef and OpenAlex do
return 4(1–2):1–174 — the response describes them accurately — but that is a corrupted
publisher deposit: those exact fields belong to Silvestri's *Mining Query Logs*
(10.1561/1500000013), ACM DL lists BM25 as "Vol 3, No 4", Robertson's own copy of the
published PDF carries "Vol. 3, No. 4 (2009) 333–389" on its first page, and FnTIR 3(3)
ends at p. 331. Adding `number = {1--2}` propagated the error. Separately, the
version-of-record upgrades kept preprint years: Singhal 2022→**2023**, Ji 2022→**2023**,
Rashkin 2021→**2023**, Es 2023→**2024**; and Fuhr should be **2017**, not 2018. Nine of
the twelve new references have no DOI or pages. **Fix — EDIT.** Full evidence and a
corrected BibTeX entry in `CITATIONS-UNVERIFIED.md`.

## N7 — The verifier: no binding count, `paper.md` only, and forty hard-coded strings
Phase 3 in full.

- **Binding count is not emitted.** `scripts/08_verify_manuscript.py:572` is
  `print(f"checks run, {len(fails)} failure(s)")` — literally "checks run, 0 failure(s)",
  with no count. You asked for both numbers; the script cannot supply one. By hand: **88
  `check()`, 3 `in_text()` sites covering 40 fragments, ~30 `states()` bindings.**
- **Every numeric binding targets `paper.md`.** `paper` is opened once at `:38`;
  `states()`'s own docstring says "Assert **paper.md** contains…". The `.tex` and the PDF
  are checked for the **disclaimer only**. `README.md:50` claims the verifier "checks it
  against `paper.md`, `paper_lncs.tex` and the text extracted from `paper_lncs.pdf`" —
  that is not true of any number, and N1 is the direct consequence.
- **The forty `in_text()` fragments are hard-coded literals.** Every Table 1 row —
  including the new macro and CI cells — and the macro-reversal sentence are checked as
  strings typed into the verifier, e.g. `"Under the macro-average\nover families the
  ordering reverses: BGE 0.296 against 0.280"`. Nothing formats those out of `results/`.
  This is precisely the estimand problem: if `macro_over_families` were computed
  differently, the paper and the verifier would carry the same stale constant and the run
  would stay green. The fix for B2 expanded the verifier's apparent coverage while adding
  **zero** results-derived binding.
- **`states()` is still markdown-shaped in one place:** `"**{:.3f}**"` at `:387` can only
  ever match `paper.md`.
- **Corpus shape is still sourced from `results/`.** `n_events`, `n_firms`, `n_countries`,
  the classification counts and the document-length statistics are all
  `corpus_stats.json` compared against constants typed into the verifier — if script 01
  has a bug, both agree. Round 2 did add five checks that read `data/processed/events.jsonl`
  directly (initiation year, report-year range, empty-country count, and the two
  "United States" string counts), which is real progress. Nothing checks the raw export
  against `MANIFEST.json`'s SHA-256, though the manifest now makes that a two-line check
  (I ran it by hand: it passes).
- **Disclaimer assertion: good, but silent.** It checks `paper.md`, `\section*{Disclaimer}`
  in the `.tex`, three ligature-proof markers in the PDF, and loops over every `.py` in
  `scripts/` and `figures/`. It does **not** emit the file list you asked for — it appends
  only on failure, so a passing run does not tell you which files were covered.

**Fix — EDIT.** Print the binding count. Run the numeric bindings against `paper_lncs.tex`
and the pdftotext output as well as `paper.md` (this alone catches N1). Replace the
hard-coded `in_text()` table rows with `states()` calls formatted from `results/`. Verify
the raw zip against `MANIFEST.json`. Emit the covered-file list on success.

## N8 — "The largest single improvement in this table" is false, and §5.3 now leans on it
`paper.md:435`: "adding BGE to the fusion is worth +0.038 … the largest single improvement
in this table." Eleven lines earlier, `:414`: "Fusion beats BM25 alone (**+0.066**…)".
Table 1's own rows give BM25 0.236 → Hybrid RRF 0.302. The claim existed in round 1; round
2 promoted it into evidence at `:526`: "nearly the size of the largest single improvement
anywhere in Table 1 (+0.038 for adding BGE)". The underpowering argument's calibration
anchor is mis-stated by a factor of ~1.7. (The rest of that paragraph's arithmetic is
right: 0.033/0.302 = 10.9%; 0.038/3.92 = 0.0097; the "roughly twice the query count" step
checks out.) **Fix — EDIT:** "the largest single improvement from adding a dense channel",
or drop the superlative, in both files and in the §5.3 sentence.

## N9 — Script 05's per-query rankings no longer ship
`scripts/05:752` now writes `results/retrieval_runs_proposed.json` (a correct fix — in
round 1 script 05 was silently overwriting the generation harness's `generation_runs.json`).
The renamed file is neither in the release nor in `.gitignore`. A reader can no longer
check any §5.3–5.5 claim at the query level, while script 04's `retrieval_runs.json`
(1.3 MB) ships. **Fix — RERUN + repackage** (or gitignore it and say so in `DATA_CARD.md`).

## N10 — `scripts/04_retrieval.py` still justifies its baseline by the deleted study
`:19–24`, byte-identical to round 1: "hybrid_rrf … stays the baseline that **scripts 05-07**
build on: the **answer-synthesis study in 06/07** was run by hand … its **prompts are
hash-linked to that run**, so silently changing the baseline would invalidate archived
outputs that cannot be regenerated." Scripts 06 and 07 do not exist. The author corrected
this exact sentence in `paper.md:47` and twice in `scripts/05`; script 04 was missed. It is
the **only** surviving generation reference in the whole package. **Fix — EDIT:** copy the
replacement wording already used in script 05.

---

# MINOR

**M1 — "All of them small" overstates the macro explanation.** `paper.md:429`: BGE leads on
B, D, E, F, "all of them small". D has n = 25, third-largest of six (A=31, C=31, D=25,
B=18, E=10, F=4). And `:427` says corpus-trained fusion's "**entire** advantage" is
`C_firm_history`; Hybrid RRF also leads on A (0.1616 vs 0.1476). Fix: "B, E and F are
small; D is mid-sized", and "almost all of its advantage".

**M2 — Build artifacts ship.** `paper_lncs.aux/.log/.blg/.out` are in the tarball despite
`.gitignore` excluding them. Useful in a review archive — the `.log` is how N1 was
confirmed — but they belong in neither a release nor a submission.
`scripts/11_arxiv_package.py` correctly excludes them from the actual arXiv tarball.

**M3 — Pre-existing typesetting defects, still in the PDF.** Double-numbered captions
throughout ("**Table 1. Table 1:**", "**Fig. 3. Figure 1:**" — and the auto-numbers
disagree with the in-text references). The §3.3 example-question table overflows by
465 pt (`paper_lncs.log:852`) and every example question is cut mid-sentence in the PDF
("Find previous recall events for ste"). Both present in round 1, but §3.3 is now
load-bearing for the template disclosure, so its table being unreadable matters more.

**M4 — Run orders disagree.** `paper.md:886` lists 01–05, 08, 09 and `gen_figures.py`
(correctly purged of 06/07); `README.md:46` adds `scripts/10_build_latex.py --compile` and
`scripts/11_arxiv_package.py`. No stated script count anywhere, so nothing is numerically
wrong — the two lists just differ.

**M5 — `paper_lncs.blg` warnings.** `Warning--empty journal` for the arXiv-only `@article`
entries (`asai2023selfrag`, `bohnet2022aqa`, `chen2023benchmarkingrag`, …). Cosmetic under
`splncs04`; `@misc` with `howpublished` silences them.

---

# PHASE 4 — Fresh eyes, on ground round 1 did not cover

**Endpoint-availability disclosure — re-checked against the current environment.** Covered
in N4. The one thing round 1 got wrong and this round corrects: the review conflated the
huggingface certificate failure with generation-endpoint availability. Those are separate
claims and the author is right to say so. The finding survives anyway, because the
encoders demonstrably run on this machine and their output now ships, so "not reproducible
inside the analysis boundary" is false on its own terms.

**Circularity — no new instances.** I looked for any system whose relevance is defined by
a predicate the system also consumes, beyond the ones the paper already dissects. There
are none new. The metadata channel and both priors are correctly labelled; §5.4's control
ladder and Table 3's caption still carry the oracle/additive-control per-family identity;
the Limitations paragraph on the priors matching the stored `defect_category` field
survives the rewrite intact. Nothing introduced in round 2 adds a circular path.

**Regulatory statements — clean, second round running.** `paper.md` and `paper_lncs.tex`
contain no mention of EU GMP Annex 22, FDA PCCP or predetermined change control, Computer
Software Assurance, ICH Q9(R1), GAMP 5, 21 CFR Part 11, or the EU AI Act. No sentence
implies any of them is adopted, final, or in force. The single regulatory citation is the
January 2025 FDA AI guidance, used once in Limitations, correctly noted as **draft** — and
still draft as of today, with no final version issued. Keep that note through
copy-editing.

**One thing round 1 and round 2 have both left alone.** §5.3's power argument is now
correct in structure but rests on the mis-stated anchor in N8, and §5.5's "reaches 0.410
nDCG@10" oracle ceiling is still presented without an interval anywhere in the text. A
reviewer who accepts the underpowering argument in §5.3 will ask why §5.5's headroom
estimate is quoted bare.

---

# PHASE 5 — Submission mechanics

**The 47.5 MB tarball is not the submission, and it is not compressed.** The file is
`…20260907.tar` — an **uncompressed** POSIX tar of the whole repository, 48,640,000 bytes.
arXiv's 50 MB source limit is not the relevant number, because this is not what would be
uploaded.

What grew, and where it belongs:

| item | size | belongs in the arXiv source? | belongs in the repo release? |
|---|---|---|---|
| `data/processed/dense_embeddings.npz` | 20.6 MB | no | **no** — `.gitignore` excludes it; regenerable in ~6 min on CPU |
| `data/processed/events_labeled.jsonl` | 11.1 MB | no | yes — it is the released benchmark |
| `data/processed/events.jsonl` | 10.1 MB | no | yes |
| `data/raw/…json.zip` | 4.0 MB | no | **no** — `.gitignore` excludes it; MANIFEST + verified SHA is the correct mechanism |
| `results/retrieval_runs.json` | 1.3 MB | no | yes |
| everything else | ~1.5 MB | tex/bbl/bib/figures only | yes |

**Recommendation.** Build the release with `git archive` — it drops to roughly 8 MB and
the `.gitignore`/`DATA_CARD`/`MANIFEST` statements become true again. Then deposit
`data/processed/*.jsonl` (21 MB, already CC BY 4.0 under `LICENSE-DATA`) in **Zenodo or
Figshare with a DOI**, and cite that DOI from `DATA_CARD.md`, `CITATION.cff` and the
paper's Reproducibility section. A benchmark release with a DOI is citable, versioned and
permanent; a 21 MB blob inside a preprint tarball is none of those. The embeddings and the
raw export should not be redistributed at all — the manifest's verified digest already
does that job better.

**The actual arXiv package is in good shape.** I ran `scripts/11_arxiv_package.py`: it
produces `arxiv_submission.tar.gz` at **59,483 bytes** containing `paper_lncs.tex`,
`paper_lncs.bbl`, `references.bib` and the three vector figure PDFs, and it refuses to
build if the `.tex` includes a raster. That is exactly right. (Note: running it wrote
`arxiv_submission.tar.gz` into my extraction directory at
`review/round2/extracted/01_regulatory-grade-genai-quality-investigations/`; delete it if
you re-tar from there.)

| check | result |
|---|---|
| `.bbl` ships | **yes** — 37 `\bibitem`s, matching 37 bib entries and 37 cited keys |
| figures vector | **yes** — all three `\includegraphics` calls take `.pdf`; the PNGs are excluded from the submission tarball |
| no absolute paths or credentials | **yes** — scanned `.py`, `.tex`, `.json`, `.md`, `.bib` for Windows/Unix home paths, API keys, tokens, passwords and the user's name: clean |
| disclaimer in all three artifacts | **yes** — `paper.md`, `paper_lncs.tex:30`, PDF; enforced by both the converter and the verifier |
| AI-use disclosure | **yes** — "Statement on the use of generative AI" in all three artifacts |
| compiles clean from the package alone | **NO, twice over.** Not verifiable here (this machine's TeX Live lacks `texlive-publishers`, so `llncs.cls` and `splncs04.bst` are absent — on arXiv's TeX Live both are present, so the submission should build). More important: the author's own `paper_lncs.log` shows 0 errors but **19 overfull hboxes**, including the 151 pt Table 1 overflow (N1) and the 465 pt §3.3 table overflow (M3). It builds; it does not build clean. |
| PDF | 24 pages, pdfTeX 1.40.25, 25 → 37 references, no `[?]` |

---

# Does this need a round 4?

**Yes — and it should be the last one.** Everything blocking is an edit plus a rebuild;
there is no analysis left to redo. Realistically two hours:

1. N2, N3, N8 — five string replacements across `paper.md` and `paper_lncs.tex`.
2. N1 — resize Table 1, rebuild, then **diff the `.tex` decimals against the rebuilt PDF's
   extracted text**. That diff is the check that would have caught it.
3. N4 — rewrite one Limitations heading and paragraph, one §4 sentence, one JSON field, one
   docstring.
4. N5 + M2 — rebuild the release with `git archive`.
5. N6 — five BibTeX fields.
6. N10 — one docstring.
7. N7 — the verifier changes, which are what stop round 5 from existing.

**What breaks the cycle.** Three rounds have now each been decided by the same failure:
a correction that landed in one place and not the others. That is not carelessness — it is
a package with four surfaces (`paper.md`, `paper_lncs.tex`, the built PDF, and `results/`)
and a verifier that binds only the first. Round 2 added a disclaimer check across all
three manuscript artifacts and it worked perfectly: B3 is fixed, at the cause, and stayed
fixed. Do the same thing for numbers — run `states()` against the `.tex` and the pdftotext
output, replace the forty hard-coded `in_text()` fragments with values formatted out of
`results/`, and print the binding count — and round 4's fixes will not become round 5's
blockers. Without it, they will.

The paper itself is now roughly where it should be: an honestly-scoped resource-and-warning
contribution with a well-characterised benchmark, a correctly-labelled inconclusive null,
and unusually good artifact discipline. The two open items from round 1 that still need
you rather than an editor — gold-set adjudication and investigator-written questions — are
correctly identified in your response as not blocking arXiv and as the first thing a
conference reviewer will ask for. That judgement is right.
