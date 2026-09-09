# NO-GO — do not submit. 7 blocking findings, one of which requires a rerun, not an edit.

Adversarial pre-submission review of `quest-qi_paper1_20260907.tar.gz`
(49 files, extracted to `review/extracted/quest-qi/`). Reviewed 2026-09-07.

Your notes mark this paper complete and verified. `scripts/08_verify_manuscript.py`
does pass — 143 checks, 0 failures — and I could not break the numbers: I recomputed
4,652 events, 1,655 firms, 24 countries, 4,462 documents containing "United States",
0 containing "outside the United States", and the 44.9% cross-block gold overlap
straight from the shipped JSONL, and they all reproduce. The artifact discipline here
is better than most accepted papers.

That is not the same as publishable. The verifier checks that the manuscript agrees
with `results/`. It does not check whether the right statistic was chosen from
`results/`, whether a stated limitation is true, or whether the novelty claim survives
a literature search. All seven blocking findings sit in that gap.

---

## Panel verdict

| Seat | Verdict | Rigor |
|---|---|---|
| Journal-fit / venue | Reject as submitted — 22 pages in `llncs`, no LNCS full-paper track accepts that length; no target venue is named anywhere in the package | 5.0 |
| Reviewer 1 — methodology & statistics | Major revision — underpowered null presented as a negative result; single-seed stochastic training; multiplicity family padded with certainties | 6.0 |
| Reviewer 2 — domain & regulatory | Minor revision — regulatory content is clean and correctly hedged (see "Regulatory status" below); the domain framing of an environmental constraint is not | 7.5 |
| Reviewer 3 — reproducibility & artifacts | Major revision — programme disclaimer missing from the submitted `.tex`; `MANIFEST.json` referenced but not shipped; `CITATION.cff` is invalid YAML | 7.0 |
| Devil's Advocate | Reject at a full research track; resource/short track after fixes | 6.5 |

**Mean rigor score: 6.4 / 10.**
**Panel consensus: Major revision, trending Reject at a full research track.** Two
seats independently concluded that net of the dataset there is no positive
contribution, and the dataset is not yet releasable.

---

## PRIORITY FINDING — the unreachable-endpoint disclosure

**You asked specifically whether this is still in the text, whether any methodological
choice was justified by it, and whether fixing it needs a rerun. Answers: yes, yes,
and yes — one rerun and four edits.**

The claim is still in the manuscript in three places, in the design note, and in a
results file:

1. `paper.md` L780 / `paper_lncs.tex` L389 (Limitations, "The generation study is
   small, single-model and unmatched"): *"...through a manual harness because **no
   generation endpoint was reachable from the analysis host** (the encoder step in
   Table 1 needed only a one-off weight download, which is not the same affordance)."*
2. `paper.md` L771 (Limitations, "The encoding step is not reproducible inside the
   analysis boundary"): *"...reproducing it requires reaching huggingface.co."*
3. `paper.md` L255 / `paper_lncs.tex` §4: *"All systems ... with no external API and no
   data leaving the boundary, **which is the constraint a regulated organization
   faces**."*
4. `notes/00-study-design.md` L20: *"`api.fda.gov`, `download.open.fda.gov`,
   `huggingface.co` unreachable from the analysis hosts"*, under a heading that reads
   "Environment constraints (documented, not hidden)".
5. `results/dense_manifest.json`: `"host": "windows (only host with huggingface.co
   reachable)"`.

**The package contradicts itself.** `scripts/09_dense_encode.py` L7–12 states:

> "huggingface.co is unreachable from both the cloud sandbox and the local Linux VM
> (HTTP 403 at the egress proxy). It **IS** reachable from Windows Python once the
> system certificate store is injected, which is what `truststore` below does."

That is a description of a local TLS-trust misconfiguration and its fix, sitting in the
same tarball as a Limitations section that presents the same fact as an external
boundary. You have since confirmed the encoders run fine on this machine. So a
condition that was environmental and repairable is stated in the manuscript as a
property of the deployment setting — and then used as a load-bearing justification.

**What it is holding up.** §5.6 is a hand-run study: 24 questions, one model, one pass,
no repeats, no variance, and — by the paper's own admission at L807 — *"Nothing checks
that the archived answers were produced by the model named."* The only defence offered
for that design is the sentence in (1). There is no diagnostic, no error log, no record
of an attempt against any generation endpoint anywhere in the package; the claim rests
on the same environment assumption that (5) shows was a certificate problem. Remove the
justification and a manual, single-pass, provenance-unverifiable study has no defence.

Note also the parenthetical in (1) — *"the encoder step ... needed only a one-off weight
download, which is not the same affordance"* — is a pre-emption of exactly this
objection, written after the encoder step had already been made to work by injecting a
cert store. It reads worse than the original claim, not better.

**Rerun or edit:**

- **RERUN required — §5.6, Table 4, Figure 4, Contribution 5, and the abstract's final
  sentence.** Run generation programmatically against a logged model + version, with at
  least 3 repeats per condition so the reported quantities carry variance, and with
  script 07 scoring what script 06's harness actually produced. Alternatively, delete
  §5.6 entirely and cut the abstract's last sentence — that is a legitimate option and
  costs the paper less than it looks, since two panel seats independently judged the
  generation study unable to bear the weight the abstract puts on it (see B4).
- **EDIT only — (2), (3), (4), (5).** The encoding step *is* reproducible: `truststore`
  plus `pip install sentence-transformers`, documented in your own script. Rewrite the
  "not reproducible inside the analysis boundary" limitation to say the step needs
  network access and a correctly configured certificate store, and drop "requires
  reaching huggingface.co" as a framing. Restate (3) as a design choice you adopted
  because it is realistic for on-premise deployment — not as a constraint you were
  under. Correct or date-stamp (4) and (5).

A limitation stated as external when it was environmental is a correctness problem in
the Limitations section, which is the one section a reviewer reads as a statement of
fact about the study rather than about the world. Fixing the wording without rerunning
§5.6 converts it from a misstatement into an unjustified design.

---

## Regulatory status — CLEAN, no blocking issues

You flagged draft EU GMP Annex 22, FDA PCCP scope, the January 2025 AI-for-regulatory-
decisions draft guidance, CSA finalisation, and EU AI Act high-risk deferral as blocking
if any sentence implies otherwise. I grepped both `paper.md` and `paper_lncs.tex` for
all of these.

**None of them appear in this manuscript.** There is no mention of Annex 22, PCCP,
predetermined change control, Computer Software Assurance, the EU AI Act, 21 CFR
Part 11, GAMP, ICH or EMA anywhere in the paper. The only regulatory citation is
`fda_ai_credibility`, used once, in Limitations: *"A deployed system built on these
components would require qualified human review of every output and the credibility
assessment described in [fda_ai_credibility]."* The bib entry is correctly noted as
"Draft guidance", the guidance is still draft as of today, and the sentence does not
imply adopted status. The "Human review remains mandatory" limitation and the
"Nothing here is validated for a regulatory context of use" statement are both correctly
scoped.

This check passes. Keep the "Draft guidance" note in the bib through copy-editing —
it is the one thing that could silently break here.

---

# BLOCKING

## B1 — Environmental limitation stated as an external constraint
**Location** `paper.md` L255, L771, L780; `paper_lncs.tex` §4 and Limitations;
`notes/00-study-design.md` L16–24; `results/dense_manifest.json`.
**Problem** See PRIORITY above.
**Why it matters** A false statement in Limitations is a correctness defect, and here it
is the sole justification for the design of §5.6.
**Fix** Rerun §5.6 with ≥3 logged repeats, or cut §5.6. Edit the other four locations.

## B2 — The results file contains a macro-average that reverses the headline
pretrained-vs-corpus-trained finding; the paper reports only the aggregate under which
its claim holds
**Location** `results/retrieval_results.json` → `summary[*].ndcg@10.macro_over_families`
(computed by `scripts/04_retrieval.py`); claim at Abstract, §5.1 ("A pretrained
retrieval encoder does not beat corpus-trained retrieval on this corpus"),
Contribution 3, Conclusion.
**Problem** Micro-averaged: `bge_base` 0.2877 < `hybrid_rrf` 0.3025 — the basis of the
claim. Macro-averaged over the six families: **`bge_base` 0.2963 > `hybrid_rrf`
0.2803** — the ordering flips. BGE also wins 4 of 6 families outright (B 0.160 vs
0.135; D 0.147 vs 0.121; E 0.0095 vs 0.000; F 0.657 vs 0.506). The corpus-trained
advantage is carried entirely by `C_firm_history` (0.759 vs 0.658) — 31 of 119 test
queries in which the firm name appears verbatim in the question, i.e. a database lookup.
**Why it matters** This is the most damaging finding in the review. §5.2 already tells
the reader that "the pooled aggregate is a mixture weighted by an arbitrary sampling
cap" and points them to the result file for the macro-average — and then does not report
that the macro-average contradicts the paper's own headline. Whatever the intent, an
editor shown both numbers reads this as selective reporting of the favourable statistic.
It also undercuts the abstract's inference *"the pretrained encoder alone (0.288) is
statistically indistinguishable from corpus-trained fusion (0.302), so the failure is
not a representation deficit"* — a null under one weighting that the other weighting
reverses cannot support that "so".
**Fix** Report both aggregates in Table 1. State the reversal in §5.1 in plain terms.
Downgrade the claim to what both support: neither encoder family dominates, and which
one wins depends on whether the entity families are weighted by their sampled count.
Delete "so the failure is not a representation deficit" from the abstract.

## B3 — The programme disclaimer is absent from the submitted manuscript
**Location** `paper_lncs.tex` — no Disclaimer section; confirmed absent from
`paper_lncs.pdf` (grep for "personal time" over extracted PDF text: 0 hits).
**Problem** The disclaimer exists verbatim in `paper.md` and `README.md` and is present
as a module docstring in 10 of 11 Python files. It is **not** in the LaTeX source or the
compiled PDF — which is what goes to arXiv. `scripts/08_verify_manuscript.py` L483
checks for it, but reads `paper.md` only, so the check passes while the actual
submission lacks it.
**Why it matters** This is the one artifact where the disclaimer is load-bearing. The
author's employment is in pharmaceutical manufacturing and quality analytics; the paper
is about pharmaceutical quality investigations. A preprint on that subject going up
without the independence statement is the failure mode the disclaimer exists to prevent.
**Fix** Add the disclaimer verbatim to `paper_lncs.tex` — as an unnumbered
`\section*{Disclaimer}` after the abstract or immediately before Ethics. Then extend the
verifier to check both `paper.md` and `paper_lncs.tex`.
**Related, non-blocking:** the `.py` docstring notice is present in all 11 scripts
(`scripts/01–10` and `figures/gen_figures.py`) — that check passes.

## B4 — Every number in the answer-synthesis study is a single pass, and two of them
are in the abstract
**Location** §5.6, Table 4, Figure 4, `results/generation_results.json`; abstract's
closing sentence.
**Problem** `generation_results.json` contains no confidence intervals, no standard
errors, no repeats — only means over 24 questions from one pass of one model. The
abstract states *"grounding answers in ten retrieved events yielded 14 question-relevant
firm mentions across 24 questions against 1 ... with correct abstention on 8 of the 9
questions"* with no uncertainty attached. Additional problems the table hides:
`citation_index_validity` = 1.000 is over **n = 16**, not 24; `evidence_utilisation` =
1.000 is over **n = 15**; `firms_verified` 0.964 / 0.867 are over **n = 14 and n = 10**
answers. The "14 versus 1" is a count of firm *mentions*, not of answers
(`n_firms_relevant` mean = 0.583 per question). Abstention 8/9 rests on nine items.
**Why it matters** This is exactly the check you asked for: single-run numbers presented
as findings. Every caveat is disclosed in Limitations and none of them reaches the
abstract.
**Fix** Rerun with ≥3 repeats and report variance (see B1), or move §5.6 to an appendix
and delete the abstract's final sentence. Either way, put the per-metric denominators in
Table 4 — several are not 24.

## B5 — The novelty claim is false; an entire literature is uncited
**Location** §2, "Benchmark construction and circularity": *"We are not aware of prior
work that quantifies the resulting circularity by running the gold rule itself as a
ranking signal."*
**Problem** Twenty-five years of test-collection work addresses this failure mode:
pooling and reusability bias (Zobel SIGIR 1998; Buckley & Voorhees SIGIR 2004; Buckley
et al. IRJ 2007 — which *quantify* how much a collection favours systems resembling
those that defined relevance); pseudo/automatic test collections, which are
predicate-defined relevance under another name (Asadi & Metzler SIGIR 2011; Berendsen et
al. SIGIR 2013; Dietz et al. 2020); simulated-query bias (Azzopardi & de Rijke 2006/07);
weak supervision imitating its labeller (Dehghani et al. SIGIR 2017); rule-constructed
benchmarks solvable by reconstructing the rule (Gururangan et al. NAACL 2018; Schuster
et al. EMNLP 2019); and synthetic-test-collection bias quantified recently (Rahmani et
al. SIGIR 2024). `references.bib` contains 25 entries, all RAG/dense-retrieval/LLM-era;
none of the above. Full list in `CITATIONS-UNVERIFIED.md` §6.
**Why it matters** The paper's recommendation in §6 is, in substance, the pooling-bias
lesson restated for executable-predicate gold. A reviewer who knows IR evaluation will
read the novelty sentence as evidence the author has not read the field the paper claims
to contribute a methodological warning to. That single sentence can sink the submission
on its own.
**Fix** Delete the sentence. Rewrite §2 to position the contribution at its actual size:
pooling bias is known; this measures the analogous quantity for executable-predicate
gold, and contributes a specific two-factor control recipe (scoring mechanism ×
candidate pool). That narrower claim is defensible and is genuinely the best thing in
the paper.

## B6 — "171 investigator-style questions" are 6 templates with slots filled, and no
human has validated any gold set
**Location** `scripts/03_build_benchmark.py` (6 f-string generators, 15 fixed defect
paraphrases); `data/processed/benchmark.jsonl`; claims at Abstract, Contribution 1, §3.3.
**Problem** I extracted the actual surface forms: **171 questions, 15 distinct 45-char
prefixes, 6 templates.** All 45 family-C questions differ only in a firm name; all 14
family-E questions are byte-identical apart from the trailing defect clause. The word
"templated" appears in the manuscript exactly once — in Limitations, and there it is
used to argue the templating is harmless. The abstract and Contribution 1 say
"investigator-style questions"; §3.3 says "Questions use investigator phrasing". No
human reviewed a question or a gold set: there is no adjudicated sample, no
inter-annotator agreement, no error audit of the 3.9% of events whose gold membership
comes from a classifier. The taxonomy's 0.717/0.609 macro F1 measures agreement with the
rule that generated the labels, not with ground truth.
**Why it matters** This is the artifact the paper exists to release, for a domain the
introduction frames in regulatory terms. A benchmark released with zero human validation
of relevance, whose question provenance is disclosed only in a Limitations aside, is not
releasable as a resource.
**Fix** (a) State "automatically generated from six templates" in the abstract and
Contribution 1, with the count of distinct surface forms. (b) Have ≥2 qualified
reviewers adjudicate a stratified sample of ≥150 query–document pairs; report agreement
and predicate error rate. (c) Report per-family n next to every per-family number and
mark n < 10 families as anecdotal. (d) If at all possible, collect 20–30 genuinely
investigator-written questions and report the transfer gap.

## B7 — An underpowered null is presented as a negative result
**Location** §5.3 (titled "The honest query-understanding result"), Table 2, Abstract,
§6, Conclusion; `results/proposed_results.json`.
**Problem** +0.014, CI [−0.005, 0.033]. The upper end of that interval is essentially
the +0.038 that the same paper calls "the largest single improvement in this table". The
data cannot separate "no effect" from "an effect as large as the biggest one the paper
reports". No equivalence test, no minimum detectable effect, no power analysis appears
anywhere. The dense-base robustness check makes it worse for the framing: on the
stronger base the same prior gives +0.020, raw p = 0.048. Two point estimates, both
positive, both intervals straddling or grazing zero, is *inconclusive* — not negative.
The paper's central claim ("The diagnosis survives; the fix did not") takes the stronger
reading throughout.
**Why it matters** The paper's whole identity is "an honest negative result". If the
result is an underpowered null rather than a demonstrated absence, the identity is
mis-stated — and the paper is unusually well placed to notice that, since it already
reports that the 84 defect-family test queries occupy only 15 clusters.
**Fix** Either run an equivalence test (TOST) against a pre-declared smallest effect of
interest and report the MDE at the achieved cluster count, or restate the claim
throughout as inconclusive/underpowered. Note that the equivalence test will very
likely fail at n_effective ≈ 15 — which is itself the honest headline: this benchmark,
at this size, cannot resolve query-understanding effects of the magnitude at stake.

---

# SHOULD-FIX

## S1 — Table 1 reports eight systems to three decimals with no intervals
The cluster CIs are in `retrieval_results.json` and they are wide and overlapping:
bm25 [0.169, 0.339], lsa [0.221, 0.415], bge_base [0.215, 0.393], hybrid_rrf
[0.225, 0.420], hybrid_rrf_dense [0.260, 0.463]. The abstract's "eight retrievers span
0.136–0.341" presents the spread as a finding while the table hides that almost every
pairwise ordering in it is unresolved except at the extremes. **Fix:** add the cluster
CI column to Table 1, or state under it that the ordering is not resolvable and only the
paired contrasts are.

## S2 — The manuscript misstates its own multiple-comparison family
`paper.md` L330 / `paper_lncs.tex` L148: "(**four** in Table 1, eleven in script 05…)".
`paper.md` L865 / `.tex` L418 say "**seven** in script 04". The code builds 7 contrasts,
`retrieval_results.json` has 7, and the verifier asserts 7. The reported adjusted values
are consistent with m = 7, so the numbers are right and the method description is wrong —
in the submitted LaTeX, in the section a methodological reviewer reads hardest, in a
paper whose selling point is care about how evaluations are computed. **Fix:** change
"four" to "seven"; add a verifier binding for stated family sizes.

## S3 — The Holm family is padded with quantities that are certainties
`gold_lookup_ceiling` is 1.000 by construction for every query with non-empty gold, and
is nonetheless bootstrapped, given a CI and a p-value, and counted as one of the eleven
Holm hypotheses; both gold controls are similarly not hypotheses about any system.
Inflating m inflates the adjusted p of the real test — and the paper's headline claim is
a **failure to reject**. A sceptical reviewer will read "Holm-adjusted p = 0.304" as a
number made large by padding, however unintentionally. **Fix:** remove controls and the
ceiling from the correction family and report them as descriptive rows; report raw and
adjusted p for the centroid prior.

## S4 — Single-seed stochastic training; no model-fitting variance anywhere
`TruncatedSVD(random_state=SEED)` (randomised SVD), `Word2Vec(seed=SEED)` and
`LogisticRegression(random_state=SEED)` are each fitted once, at seed 20260906. Every
bootstrap in the paper resamples *queries only*, so model-fitting variance is in no
interval. Two claims are therefore unsupported by the reported variance: **"Averaged
word2vec trails everything … and MiniLM is worse still"** (0.159 vs 0.136, with **no
contrast computed between them**, and w2v the most seed-sensitive model in the table);
and **"A general-purpose symmetric encoder is the wrong tool here"** — on
`E_defect_geography`, the family carrying the paper's flagship diagnosis, **MiniLM
scores 0.0173, above LSA (0.0133) and above BGE (0.0095)**, i.e. it is the best single
non-fused encoder on that family. That is not mentioned anywhere. At n = 10 it is noise,
which is precisely the point: these cells cannot support the adjectives attached to
them. λ is also selected on dev outside the bootstrap, so selection variance is excluded
too. **Fix:** refit under ≥5 seeds and report mean ± range per row; add the w2v-vs-MiniLM
contrast or delete the ordering claim; state plainly that all intervals are
query-resampling only.

## S5 — The cluster bootstrap is asymptotic in a quantity this design does not have
Cluster assignment gives **15 clusters holding all 84 defect queries** plus 35
singletons. The percentile cluster bootstrap undercovers below roughly 30–50 informative
clusters, and every contrast in Table 3 is driven by the 15. The paper states the
effective-n problem and then reports `p = 0.0` ("p < 0.001") for six of those contrasts
anyway. The estimator is also a ratio of means over unequal-size clusters (biased at
small cluster counts), and the p-values are CI inversions rather than null-distribution
p-values. **Fix:** wild cluster bootstrap-t or a permutation test over clusters; report
the informative-cluster count next to every p; stop reporting "p = 0.0" for
defect-driven contrasts.

## S6 — The signature statistic's interval is a plain percentile bootstrap of a ratio
`0.53, CI [0.31, 0.72]` appears in the abstract, the conclusion and the README. It is a
percentile interval on a ratio of correlated, skewed means — no BCa, no bias correction —
and it is conditioned on a single dev-selected λ per side, a single model fit, and
`POOL = 300`, none of which are resampled. (Credit where due: numerator and denominator
*are* computed on the same resample, and the denominator's CI [0.430, 0.594] is far from
zero, so the estimate is not invalid — it is just narrower than the total uncertainty.)
**Fix:** BCa or studentised interval; re-select λ inside the bootstrap; or state
explicitly that the interval is conditional on λ, seed and pool.

## S7 — `unswept_hyperparameters` does not contain what the paper says it contains
§4 lists six a-priori-fixed settings and says they "are recorded in
`results/proposed_results.json` under `unswept_hyperparameters`". The file contains five:
`slot_penalty`, `centroid_softmax_temperature`, `lsa_pool_expansion`, `rrf_k`,
`svd_dim`. **The 3–75 gold-size window is not there.** The verifier does not catch this.
**Fix:** add it to the JSON, or drop it from the sentence.

## S8 — The λ dev curve is described inaccurately
§4: the additive gold control "lands on 4; its dev curve is flat from λ = 2 upward,
because past that point it already ranks every gold document in the pool first." The
recorded dev curve is 2.0 → 0.8489, 4.0 → 0.8519, 8.0 → 0.8519, 16.0 → 0.8519. It is
flat from **4**, not 2, and the stated mechanism therefore does not hold at 2.
**Fix:** change "2" to "4".

## S9 — `data/raw/MANIFEST.json` is referenced three times and does not ship
The Reproducibility section and README both direct the reader to
`data/raw/MANIFEST.json` for the source URL and SHA-256 of the openFDA export. `data/raw/`
is in `.gitignore` and is absent from the tarball. **You asked me to check that MANIFEST
snapshot dates match the text — I cannot, because the file is not in the package.** The
export date (2026-08-27) is corroborated by `results/corpus_stats.json`
(`openfda_export_date: "2026-08-27"`) and matches the Disclaimer, §3.1 and the
Reproducibility section, so the *date* is internally consistent; the *checksum and source
URL a reader needs to obtain the same export* are not obtainable. Relatedly, `DATA_CARD.md`
gives sha256 values truncated with an ellipsis (`8b776393593c9c72…`), which cannot verify
anything. **Fix:** ship `MANIFEST.json` (it contains no raw data, only a URL and a hash),
and print full digests in the data card.

## S10 — `CITATION.cff` is invalid YAML and will not parse
Line 13 onward: the `keywords` list mixes an 8-space-indented first item with
column-0 items. `yaml.safe_load` raises `ParserError: expected '<document start>', but
found '<block sequence start>'`. GitHub's citation widget and every `cff` tool will
reject it. The whole file is also indented six spaces from column 0. **Fix:** re-emit the
file with consistent indentation and validate with `cffconvert`.

## S11 — arXiv package mechanics
Verified against arXiv's current policies:
- **Correct as-is, do not change:** `llncs.cls`, `splncs04.bst` and `orcidlink` are all
  in arXiv's TeX Live — do **not** bundle them ("do not include extraneous files").
  Letter page size is normal for a genuine `llncs` build (the class sets the text block,
  not the media box) and is not evidence of anything.
- **Add `paper_lncs.bbl`.** arXiv will run BibTeX when a `.bib` is present, so this is
  not strictly required — but shipping the `.bbl` (named to match the main `.tex`)
  removes the single most common arXiv failure mode and guarantees the rendered
  bibliography matches your local PDF.
- **Remove the four `figures/*.png` or the four `figures/*.pdf`.** The `.tex` calls
  `\includegraphics{figures/figN.png}` — so the vector PDFs you generated are unused
  files that arXiv asks you not to ship, and the paper is presenting raster figures when
  vector ones exist. Prefer switching the four `\includegraphics` calls to `.pdf` and
  deleting the PNGs.
- **AI-use disclosure.** arXiv requires significant use of generative AI to be reported
  in the paper (methods or acknowledgements), not in metadata. There is no such statement
  anywhere in the package. Given B-list findings and the AI-tell profile in M1, add one.
- **Licence** is chosen on the submission form. If LNCS is still a target, the arXiv
  perpetual non-exclusive licence is the safe default over CC BY.

## S12 — Venue fit: 22 pages in `llncs`, with no venue named
Springer's own proceedings guidance describes LNCS full papers as 12–15+ pages, and I
could find no standard LNCS track that accepts 22. The package names no target venue.
For arXiv this is a non-issue; for an LNCS submission it is a desk rejection. **Fix:**
either name the venue and cut to its limit (~35–45% reduction), or state in a footnote
that this is an extended preprint version.

## S13 — A code comment contradicts §3.3 on a design decision the paper defends at length
`scripts/03_build_benchmark.py`: *"the predicate uses the recall INITIATION year, which
is the only date the retrieval document exposes"*. §3.3 says the opposite, and §3.3 is
right — event documents contain both (`Recall initiated: 20110315. Reported: 20120620.`).
**Fix:** correct the comment to match §3.3's (correct) reasoning.

## S14 — Citation metadata
One hard error and one title error; see `CITATIONS-UNVERIFIED.md`. Summary:
`robertson2009bm25` has the wrong volume and pages (correct: Vol. 3, No. 4, pp. 333–389)
— this is the canonical BM25 reference and an IR reviewer will spot it; `fda_ai_credibility`
has the wrong title casing; `singhal2022clinicalknowledge` should cite the *Nature*
version, and `ji2022hallucination` / `rashkin2021attribution` should cite their journals.
**Zero fabricated references — all 25 resolve to primary sources.**

---

# MINOR

## M1 — AI-tell profile: word-filtered but not re-voiced
Report only, per your instruction — nothing was rewritten. The lexical layer is
implausibly clean (delve, underscore, pivotal, crucial, comprehensive, leverage, nuanced,
multifaceted, "it is worth noting", importantly, notably, furthermore, moreover: **zero
occurrences each** across 8,663 words; **zero em-dashes**). Everything a word filter
cannot see is dense: **35 paragraphs open with a bolded full thesis sentence** (14
consecutively in Limitations, 4 in a row in §5.3, 4 in a row in §6); standalone
scaffolding lines ("Two findings, both negative." / "Three consequences follow." /
"Three qualifications have to travel with that number, and all three matter."); the
canonical pivot at L72 ("That much is a clean empirical finding. The rest of this paper
is about what we could not then demonstrate."); the paired-imperative gloss ("Read
narrowly… Read sceptically… Both readings support the same conclusion:"); and
**"honest" used as a self-applied adjective six times, including in a section heading**
(§5.3 "The honest query-understanding result"). `0.53, CI [0.31, 0.72]` appears **five
times** and the phrase "and none of it is retrieval" **three times**, in near-isomorphic
sentences — the pattern a near-duplicate integrity screen surfaces. The substance reads
as human work (the admission that the first control was mis-specified, the pool sweep,
the dev/test overlap disclosure); the packaging reads as machine-generated. Highest-yield
edits if you want to reduce exposure: the 14-in-a-row bold block in Limitations, the six
"honest"s, and the five-way duplication of the 0.53 figure.

## M2 — `notes/00-study-design.md` ships stale and contradicts the final paper
It states "No pretrained transformer encoder available → dense retrieval is
corpus-trained", which the paper's central comparison now violates; and it contains the
network claim in B1. A reader working through the bundle in order meets the contradiction
before the resolution. **Fix:** date-stamp it as superseded, add one line recording what
changed, or drop it from the tarball.

## M3 — The verifier's own framing is slightly overstated
The manuscript's header says `08_verify_manuscript.py` "re-checks each one against the
result files and fails on any disagreement". 117 of its checks compare `results/` against
constants retyped in the script; the manuscript binding comes from `states()` and
`in_text()`, which cover the tabulated numbers but no prose claim about method — which is
exactly how S2, S7 and S8 survived. The script itself documents this limitation honestly
in a comment. **Fix:** soften to "every tabulated number", and add bindings for stated
family sizes and hyper-parameter lists.

## M4 — Minor code hygiene
`scripts/05` computes `hybrid_rrf_dense` twice (harmless only via short-circuit);
`_RESAMPLE_CACHE` keyed on `id(clusters)` is a latent correctness trap on reuse;
`load_dense` returns whichever of four encoder keys it finds first, so which encoder backs
the dense rows is implicit in the `.npz` rather than declared. The verifier prints
"checks run, N failure(s)" without the check count.

---

# Reproducibility — what a reader could not reproduce from this package

| Step | Reproducible? | Blocker |
|---|---|---|
| 01 build corpus | **No** | `data/raw/` is gitignored and `MANIFEST.json` — which holds the source URL and SHA-256 — does not ship (S9). A reader can download *an* openFDA export but cannot confirm it is the 2026-08-27 snapshot the paper used. `DATA_CARD.md` digests are elided with "…". |
| 02–05, 07, 08, figures | **Yes**, given `data/processed/*.jsonl`, which ship. Deterministic at seed 20260906 (but see S4 — one seed is not variance). |
| 06 + generation answers | **No.** Prompts and archived answers ship and are SHA-256 hash-linked, so script 07's scoring is auditable against the archived text — but nothing verifies that the archived answers came from the model named, the harness was manual, and there is one pass. Not reproducible in any sense a reader would accept. |
| 09 dense encode | **Yes, contrary to the manuscript.** Needs network + a working certificate store (`truststore`). `dense_embeddings.npz` is gitignored, so the reader must re-encode; the model commit hashes are pinned in `dense_manifest.json`, which is good practice. |
| Model-fitting variance | **No** — single seed, single fit for word2vec / SVD / logistic regression. |
| Table 1 ordering | **Not verifiable** as stated — no intervals in the table, and no contrast between the bottom two rows. |
| `paper_lncs.pdf` | Compiles cleanly (25 refs, no `[?]`), but `.bbl` and `llncs.cls` are absent from the package — see S11 for what actually matters. |

---

# The shortest path to a defensible submission

1. **Decide on §5.6 first**, because it sets whether you rerun or only edit. Cutting it
   removes B1's rerun, B4 entirely, and one panel objection — at the cost of
   Contribution 5 and the abstract's last sentence. Keeping it means a scripted rerun
   with ≥3 logged repeats.
2. **Fix B2 in Table 1 and §5.1.** Report both aggregates and state the reversal. This is
   the finding most likely to be read as bad faith if a reviewer finds it first.
3. **Delete the novelty sentence and rewrite §2** against the pooling-bias literature
   (B5). Claim the two-factor control recipe, which is genuinely yours.
4. **Add the disclaimer to `paper_lncs.tex`** and extend the verifier to check it there
   (B3). Ten minutes.
5. **Retitle the result** from negative to underpowered, or run the equivalence test (B7).
6. **Disclose the templates in the abstract** and adjudicate a gold sample (B6). This is
   the long pole — it is real work, and it is what turns the benchmark from a released
   file into a released resource.
7. Then the S-list: intervals in Table 1, "four"→"seven", drop the ceiling from the Holm
   family, ship `MANIFEST.json`, fix `CITATION.cff`, fix the BM25 citation, ship the
   `.bbl`, drop the duplicate figure files, add an AI-use statement.

The artifact engineering in this package is genuinely strong and worth preserving. What
the paper needs is not more verification — it needs the claims resized to what the
verified numbers support.
