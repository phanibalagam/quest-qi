# QUEST-QI — a benchmark for evidence retrieval over pharmaceutical quality events

Code and data for *When the Benchmark Answers Itself: Predicate-Defined Relevance
and the Limits of Query Understanding in Pharmaceutical Quality-Event Retrieval*.

**Paper**: `paper.md` (source), `paper_lncs.pdf` (typeset).
Every number in the manuscript is produced by the scripts here and re-checked
against `results/` by `scripts/08_verify_manuscript.py`, which exits non-zero on
any disagreement.

## What this releases

- **QUEST-QI**: 4,652 recall events aggregated from the openFDA drug enforcement
  bulk export, a 15-class defect taxonomy, and 171 investigator-style questions
  generated from six templates, with gold evidence sets defined by executable
  predicates over structured fields (52 dev / 119 test). The questions are not
  human-written and no human adjudicated any relevance judgement; the paper's
  Limitations section states what that costs.
- The full pipeline, from raw export to every figure in the paper.

## The finding, in one paragraph

Text-only retrieval reaches 0.341 nDCG@10 at best (BM25 + LSA + BGE fusion) and
collapses on questions that constrain manufacturing geography, which a pretrained
BGE encoder does not rescue. BGE *alone* is statistically indistinguishable from
corpus-trained fusion — 0.288 against 0.302, and the two aggregates disagree on
which leads — but *adding* it to the fusion is worth +0.038 (Holm p = 0.0); it is
the only pretrained dense channel added to a fusion here, so there is nothing to
rank it against. The 0.302 corpus-trained fusion is the base
every later section is measured against, for the reason given in §4: it is the
strongest configuration that needs no downloaded weights.
Adding a defect-category prior to a filter over the metadata a question names
raises this to 0.579 (the soft metadata filter alone reaches 0.423; a hard
prefilter with no defect prior reaches 0.464), but that filter
re-executes the benchmark's own relevance rule: a control that does no query
understanding and scores documents purely by gold membership reaches 0.823 over
the same candidate pool, and the literal answer key reaches 1.000. Any benchmark
whose relevance is defined by an executable predicate will reward systems for
reconstructing that predicate. We recommend publishing a mechanism-matched
gold-membership control alongside any such leaderboard.

## Reproducing

```
pip install numpy scipy scikit-learn gensim rank_bm25 matplotlib
pip install truststore sentence-transformers      # for script 09 only
# place the openFDA drug enforcement export at the path in data/raw/MANIFEST.json
python scripts/01_build_corpus.py
python scripts/02_taxonomy.py
python scripts/03_build_benchmark.py
python scripts/09_dense_encode.py   # NEEDS NETWORK. Downloads two encoders once
                                    # and writes data/processed/dense_embeddings.npz
python scripts/04_retrieval.py
python scripts/05_taxonomy_aware_retrieval.py
python figures/gen_figures.py
python scripts/10_build_latex.py --compile  # paper_lncs.tex + paper_lncs.pdf
python scripts/08_verify_manuscript.py      # must print 0 failures
python scripts/11_arxiv_package.py          # arxiv_submission.tar.gz
python scripts/12_release_package.py        # quest-qi_release.tar.gz
```

Two ordering points. Build the PDF *before* running the verifier: it checks the
compiled artifact, not just the Markdown. And run script 09 *before* scripts 04 and
05: without `dense_embeddings.npz` they skip every dense channel, Table 2 loses its
two pretrained-encoder rows, and the verifier fails on the rows it parses out of
that table. Script 09 is the one step needing network access; if you cannot run it,
scripts 04 and 05 still complete and the rest of the paper reproduces, but Table 2
will be short two rows.

`scripts/08_verify_manuscript.py` reads every number back out of `results/` and
checks it against `paper.md`, `paper_lncs.tex` and the text extracted from
`paper_lncs.pdf`, and prints its binding count and the artifacts it covered. Table 2,
the text-only retrieval table, is parsed out of each surface and compared to
`results/` numerically, and every numeric table is checked **row by row** against its
own region of the compiled PDF — a table that overflows the text block is silently
truncated by LaTeX, which is how a column added to the Markdown once failed to reach
the paper a reader receives.

The script has two kinds of binding and they guarantee different things. A `check()`
recomputes a value from `results/` and asserts it against a literal in the script: it
proves the arithmetic and does not read the manuscript at all, so on its own it cannot
tell you that the paper states the number. A `states()`, an `in_text()` or a phrase
binding is matched against the manuscript text, and a phrase binding additionally ties
the figure to the contrast its own sentence names, so a number measured against the
wrong control fails even when the digits agree with themselves. A claim is covered end
to end only when both kinds are present, which is why the arithmetic checks are paired
with text bindings rather than trusted alone.

Every other decimal is covered by a weaker guarantee: a set comparison in both
directions between `paper.md` and `paper_lncs.tex`, and from the source into the PDF, so
a number that exists in one surface and not another is caught even though its value is
not independently checked. The source side for the PDF comparison is `paper_lncs.tex`
and `paper_lncs.bbl` together, since the bibliography's text reaches the PDF from the
`.bbl`. The reverse direction — decimals the PDF carries and the source does not — is
reported rather than enforced, because what is left after both source files is the three
embedded figures, whose axis ticks and bar labels are checked against `results/` in
`figures/gen_figures.py`, plus the occasional DOI split across a line by the PDF
renderer. The script identifies which extras came from where rather than assuming a
single cause, and says so when it cannot.

The PDF artifact also has LNCS running heads stripped before comparison, along with each
page's own folio — a bare integer is removed only when it equals the number of the page
it sits on and sits at a page boundary, which is what makes it a folio rather than a
table cell or a section number that happens to match. Both are stripped so that a
sentence spanning a page break is not broken by the page furniture set between its
halves.

When `paper_lncs.log` is present — that is, after a build with
`scripts/10_build_latex.py --compile` — a body-prose or bibliography line running past
the right margin by 5 pt or more is a hard failure, as is a vertical overrun of 5 pt or
more that is neither routine page-breaking output nor inside a float, which is the case
where something unbreakable is running off the bottom of the page. `.gitignore` excludes
`*.log`, so that log is not in the release archive and those checks do not run for a
reader who only unpacks it; the script says so rather than passing in silence.

What it catches: a number edited in one artifact and not another, a claim measured
against the wrong baseline, a stale PDF, a truncated table, a range whose separator
was dropped, a missing disclaimer, a manuscript reference to a file that no longer
exists, a local raw export that does not match its manifest digest.

What it does not: verify a decimal that no binding names. A number can be internally
consistent across all three artifacts and still be wrong about the world; that is what
the external review rounds in `notes/` are for.

What it does not catch, and no amount of extending it would: whether the right
statistic was chosen in the first place, whether a sentence describing the method
is true, or whether a novelty claim survives a literature search. Those need a
reader. A green run means the manuscript is internally consistent with `results/`
across all three artifacts, and nothing stronger.

`scripts/09_dense_encode.py` is the one step needing network access: it downloads
the pretrained encoders once and writes `data/processed/dense_embeddings.npz`.
Scripts 04 and 05 skip their dense channels if that file is absent, so the
pipeline runs end to end offline.

Single seed 20260906 throughout. Runtime a few minutes on one CPU core.

## Licence

Code MIT (`LICENSE`); derived data and results CC BY 4.0 (`LICENSE-DATA`).
Upstream FDA records are US federal public-domain works.

## Disclaimer

This work was carried out independently, on personal time and equipment, and is
not connected to the author's employment. The views expressed are the author's own
and do not represent the views, positions or policies of any current, former or
future employer or client. No proprietary, confidential or internal data of any
organization was used. All data is public: the openFDA drug enforcement bulk
export (US federal public domain, export date 2026-08-27), and two pretrained
sentence encoders downloaded from their public repositories with their commit
hashes recorded.
