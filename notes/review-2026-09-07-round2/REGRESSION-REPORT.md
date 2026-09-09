# REGRESSION REPORT — what round 2's fixes broke

Phase 2 output, kept separate from the verification table. Every item below is a defect
that **did not exist in round 1** and exists now because of a round-1 remedy, or a
round-1 defect **reintroduced by the fix for a different finding**.

Five regressions. Three are blocking. Two of the three are the same failure mode round 1
already named: a change made in one place and not propagated to the other places that
state the same fact.

---

## R1 — BLOCKING. The Holm fix landed in one paragraph and not the other. The manuscript now states two different correction-family sizes.

**Introduced by:** the fix for round-1 S3 (drop the gold controls from the Holm family).

`paper.md:369` / `paper_lncs.tex:157` — **Statistics** paragraph, rewritten:

> "Holm-corrected within each script's family of comparisons: seven in script 04 … and
> **eight in script 05** (the eight systems under test…)"

`paper.md:905` / `paper_lncs.tex:387` — **Reproducibility** paragraph, untouched:

> "Holm correction within each script's family of contrasts against the text-only
> baseline (seven in script 04, **eleven in script 05**, and two more in the Section 5.3
> robustness pair)."

The code family is eight: `scripts/05_taxonomy_aware_retrieval.py` builds `contrast_systems`
with 8 entries and slices `raw_p[:len(contrast_systems)]` before `holm()`. Eleven is the
round-1 number.

This is round-1 finding S2 — "the manuscript misstates its own multiple-comparison
family" — recreated one paragraph further down, in a paper whose selling point is care
about how evaluations are computed, and it is in the shipped PDF. A methodological
reviewer reading both paragraphs sees a manuscript that cannot state its own correction
family consistently.

**Fix (edit):** `paper.md:905` and `paper_lncs.tex:387` → "seven in script 04, eight in
script 05, three gold controls reported with raw p only, and two more in the Section 5.3
robustness pair." Rebuild the PDF.

---

## R2 — BLOCKING. Table 1's two new columns overflow the LNCS text block. The macro column and the entire MRR column are missing from the typeset paper.

**Introduced by:** the fix for round-1 B2 and S1 (add a macro-average column and a
cluster-CI column to Table 1).

`paper_lncs.tex:170` — `\begin{tabular}{lrrrrrrrr}`, nine columns, `\small`, at LNCS
textwidth (12.2 cm).

`paper_lncs.log:875` — `Overfull \hbox (151.54454pt too wide) in paragraph at lines 170--184`.

The PDF header is truncated mid-word. From `pdftotext paper_lncs.pdf -`:

> `R@10 R@50 R@100 P@10 nDCG@10 (micro) 95% CI (cluster) nDCG@10 (macro) M`

and the body rows stop after the second numeric column:

> `MiniLM (pretrained)` / `0.105 0.213`
> `word2vec (corpus-trained)` / `0.147 0.244`

Diffing every decimal in `paper_lncs.tex` against the extracted PDF text: six numbers are
in the source and absent from the PDF — `0.245, 0.256, 0.333, 0.364, 0.412, 0.500`, the
whole MRR column — plus the eight macro values. The same diff run against the **round-1**
package returns an empty set: round 1's seven-column Table 1 typeset completely.

So the fix for the single most serious round-1 finding — that the macro-average reversal
was hidden in a JSON file — has resulted in the macro-average being **absent from the
typeset paper**. It is in `paper.md`, and a reader of the PDF cannot see it. The finding
is, from the reader's point of view, not fixed.

**Fix (edit + rebuild):** `\resizebox{\textwidth}{!}{…}`, or `\footnotesize` with
`\setlength{\tabcolsep}{3pt}`, or split into two tables (metrics; aggregates + CI).
Then re-diff the .tex decimals against the rebuilt PDF's text before shipping.

---

## R3 — BLOCKING. Section 5.3 was rewritten to call the null inconclusive; the abstract, the contribution list and 5.3's own closing sentence still call it a negative result.

**Introduced by:** the fix for round-1 B7 (stop presenting an underpowered null as a
demonstrated absence).

The rewrite, `paper.md:524`:

> "**This null is inconclusive, not a demonstration of no effect, and we do not have the
> sample size to make it one.**"

Four surviving contradictions, all mirrored in `paper_lncs.tex` and the PDF:

| line | text |
|---|---|
| `paper.md:39` (Abstract) | "Second, a **negative result**: the only query-understanding component we could build…" |
| `paper.md:115` (Contribution 4) | "**A negative result and its measurement**:" |
| `paper.md:509` (§5.3 body) | "Two findings, both **negative**." |
| `paper.md:566` (§5.3, 42 lines *after* the rewrite) | "This is the paper's central **negative result**." |

A paper cannot argue in one paragraph that it lacks the power to demonstrate absence and
assert in the next that absence is its central result. The abstract is the version most
readers take away, and it is the un-rewritten one.

**Fix (edit):** replace at all four sites in both files with "inconclusive null" /
"a null we cannot resolve at this sample size". Rebuild.

---

## R4 — BLOCKING. The package now ships two files that the DATA_CARD says it does not ship, that `.gitignore` excludes, and that the Limitations section says cannot be reproduced.

**Introduced by:** the fix for round-1 S9 (ship `data/raw/MANIFEST.json`) — the release
was built by archiving the working directory rather than the tracked repository.

Shipped in the tarball:
- `data/raw/openfda/drug_enforcement/drug-enforcement-0001-of-0001.json.zip` (3,974,979 bytes)
- `data/processed/dense_embeddings.npz` (20,619,570 bytes)

`.gitignore` excludes both (`data/raw/*` with a single `!MANIFEST.json` exception, and
`data/processed/dense_embeddings.npz`).

`DATA_CARD.md`, under the heading **"What is not, and why"**:

> "`data/raw/` — … **Not mirrored here**: it is freely downloadable…"
> "`data/processed/dense_embeddings.npz` (20 MB) — **regenerate** with `scripts/09_dense_encode.py`"

`data/raw/MANIFEST.json` says the same:

> "**Raw export is not mirrored in this repository.** Download the file at source_url and
> check its SHA-256…"

And `paper.md:789`, Limitations:

> "**The encoding step is not reproducible inside the analysis boundary.** … reproducing
> it requires reaching huggingface.co, which the analysis host cannot do."

The embeddings that limitation says a reader cannot regenerate are in the box. This is
the round-1 priority finding in a new form: a limitation stated as external, now
contradicted not by a script docstring but by the package's own contents.

Two of these three artifacts are internally consistent and the third is the release, so
the fix is a choice, not a wording pass — see N4 in the findings report.

**Fix (edit + repackage):** decide whether the data ships. If it does, rewrite
`DATA_CARD.md`, `MANIFEST.json`'s note and the Limitations paragraph and adjust
`.gitignore`. If it does not, build the release from `git archive` and the 48.6 MB drops
to about 8 MB. Either way the three statements must agree.

---

## R5 — SHOULD-FIX. LaTeX build artifacts now ship.

**Introduced by:** the fix for round-1 S11 (ship `paper_lncs.bbl`) — the `.bbl` was added
by including the build directory rather than the one file.

`paper_lncs.aux`, `paper_lncs.log`, `paper_lncs.blg`, `paper_lncs.out` are all in the
tarball; `.gitignore` excludes all four. arXiv's own guidance is not to include leftover
build files.

This one is double-edged: the shipped `paper_lncs.log` is what let me confirm R2 (the
151 pt overfull box), so it has audit value in a *review* archive. It has no place in a
release or a submission. Note that `scripts/11_arxiv_package.py` correctly excludes them
from the actual arXiv tarball — the problem is only in the repo archive you circulated.

**Fix (repackage):** build the release with `git archive`, or add the four to the release
script's exclusion list.

---

## R6 — SHOULD-FIX. Script 05's per-query rankings no longer ship.

**Introduced by:** an unannounced (and correct) bug fix during the round-2 re-run.

`scripts/05_taxonomy_aware_retrieval.py:752` now writes
`results/retrieval_runs_proposed.json`. In round 1 it wrote `results/generation_runs.json`
— and round 1's `generation_runs.json` has top-level keys `hybrid_rrf, slots_only,
prefilter_hybrid, gold_downweight_control, …`, i.e. script 05 was silently overwriting the
generation harness's own run file. The rename is right.

But the renamed file is not in the release, and it is not in `.gitignore` either. The
per-query rankings for every system in §§5.3–5.5 — the proposed retriever, both priors,
the metadata channel, all three gold controls — are now unavailable to a reader, while
script 04's `retrieval_runs.json` (1.3 MB) ships. A reader can no longer check any
Section 5.4 claim at the query level.

**Fix (rerun + repackage, or edit):** re-run script 05 and ship
`results/retrieval_runs_proposed.json`, or gitignore it and say so in `DATA_CARD.md`.

---

## R7 — SHOULD-FIX. `README.md` now advertises a verification that does not happen.

**Introduced by:** the fix for round-1 B3 (make the verifier check the .tex and the PDF).

`README.md:50`:

> "`scripts/08_verify_manuscript.py` reads every number back out of `results/` and checks
> it against **`paper.md`, `paper_lncs.tex` and the text extracted from
> `paper_lncs.pdf`**."

The script opens `paper.md` only (`:38`). Every `check()`, `states()` and `in_text()`
binding targets `paper_flat`, which is derived from `paper.md`. What it reads out of the
`.tex` and the PDF is the **disclaimer, and nothing else** (`:513–556`). The script's own
docstring is honest about this; the README is not.

R2 is the direct consequence. Nothing compares the `.tex` to the built PDF, so a table
that lost two columns in typesetting shipped with a clean verifier run.

**Fix:** either correct the README sentence, or — the real fix — run the numeric bindings
against `paper_lncs.tex` and the `pdftotext` output as well. The second would have caught
R2 automatically.

---

## What the fixes did NOT break — verified, not assumed

These were the obvious regression candidates. I checked each and they are clean:

- **§5.6 is purged from every artifact but one.** `paper.md`, `paper_lncs.tex`, the PDF,
  `README.md`, `DATA_CARD.md`, `CITATION.cff`, `.gitignore`, `figures/gen_figures.py`,
  `scripts/08`, `scripts/10`, `scripts/11` contain no reference to the generation study,
  Table 4, Figure 4, or scripts 06/07. All seven of its decimals (`0.272, 0.867, 0.964,
  1.17, 1.33, 6.42, 9.6`) are gone. The single leftover is `scripts/04_retrieval.py:19–24`
  — see N7.
- **Section, table, figure and contribution numbering survived the deletion.** §§5.1–5.5,
  Tables 1/2/3/3b, Figures 1–3, four contributions, no gaps, no dangling "5", and no
  stated count anywhere that could go stale.
- **Figures are not stale.** `gen_figures.py` was re-run (figure PDFs differ only in
  `/CreationDate`) and produced byte-identical PNGs, because nothing it plots changed —
  the macro and cluster-CI values already existed in round-1
  `results/retrieval_results.json`. `gen_figures.py` no longer defines `fig4` and no
  longer loads `generation_results.json`; its output list matches what ships.
- **The Holm change is a real code change, not a display filter,** and the author's claim
  that "every adjusted p is unchanged" is true — empirically (the only OLD↔NEW deltas in
  `proposed_results.json` are the three controls' `p_holm: 0.0 → None`) and by Holm's
  construction, since the three removed p-values were the smallest in the family.
- **Every new Table 1 cell reconciles to `results/`.** All eight macro values and all
  eight cluster CIs match `summary[system].ndcg@10.macro_over_families` and `.ci95_cluster`
  to printed precision, and the macro values recompute exactly as the unweighted mean of
  the six `by_family` entries.
- **`paper.md` and `paper_lncs.tex` are numerically identical.** Extracting every decimal
  from each, the only asymmetries are section numbers LaTeX renders itself.
- **The bibliography survived +12 entries cleanly:** 37 in `references.bib`, 37
  `\bibitem`s in `paper_lncs.bbl`, 37 distinct keys cited in the `.tex`, identical sets,
  zero uncited, zero missing, zero `[?]` in the PDF.
- **The disclaimer converter fix works and is enforced.** `\section*{Disclaimer}` is at
  `paper_lncs.tex:30` and in the PDF; `10_build_latex.py` hard-fails without it; the
  verifier checks all three artifacts and is ligature-proof against T1 PDF extraction.
- **`data/raw/MANIFEST.json`'s SHA-256 verifies** against the shipped zip
  (`7f63ce0a…ec4f`), and all three un-elided `DATA_CARD.md` digests verify against the
  shipped JSONL files.
- **`CITATION.cff` parses.**
- **`scripts/11_arxiv_package.py` works** and produces a correct 59 KB submission tarball
  (tex, bbl, bib, three vector PDFs) with no extraneous files.

---

## Verdict

**Yes, the fixes introduced new defects, and the pattern is the one you predicted.**

Four of the seven regressions are propagation failures: a correction applied where the
reviewer pointed and not where the same fact is stated elsewhere. R1 is round-1's S2
recreated one paragraph away. R3 is a rewrite that stopped at the section boundary and
left the abstract contradicting it. R2 is a fix that is correct in the source and
invisible in the artifact readers receive. R4 is a fix that made three other documents
false.

The underlying substance is sound — the analysis changes are real, verified, and
correctly computed. What keeps failing is the last mile, and it fails for a structural
reason: the verifier binds `paper.md` only, its manuscript bindings are largely hard-coded
strings rather than values formatted out of `results/`, and nothing at all compares the
`.tex` to the built PDF. Until the verifier is the gate rather than a report, round 4 will
produce round 5.
