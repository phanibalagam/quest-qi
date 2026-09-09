# QUEST-QI: A Benchmark for Evidence Retrieval over Pharmaceutical Quality Events

**Phani Kumar Balagam** Independent Researcher, United States ORCID
[0009-0007-6762-399X](https://orcid.org/0009-0007-6762-399X) · <balagam.phani@gmail.com>
· <https://github.com/phanibalagam>

*Resource paper.* Every number in this manuscript is produced by the scripts in
`scripts/` from the public data described in Section 3 and read from the JSON files in
`results/`; `scripts/08_verify_manuscript.py` re-checks each one against the result files
and fails on any disagreement.

## Disclaimer

This work was carried out independently, on personal time and equipment, and is not
connected to the author's employment. The views expressed are the author's own and do
not represent the views, positions or policies of any current, former or future employer
or client. No proprietary, confidential or internal data of any organization was used.
All data is public: the openFDA drug enforcement bulk export (US federal public domain,
export date 2026-08-27), and two pretrained sentence encoders downloaded from their
public repositories with their commit hashes recorded.

---

## Abstract

We release QUEST-QI, a benchmark for evidence retrieval over pharmaceutical quality
events and, to our knowledge, the first public one in this domain. It comprises 4,652
recall events aggregated from the openFDA drug enforcement export, a 15-class defect
taxonomy covering 96.1% of the corpus from canonical phrases, and 171 investigator-style
questions in six families whose gold evidence sets are defined by executable predicates
over structured fields rather than by human adjudication. Eight retrievers span
0.136-0.341 nDCG@10 on the held-out split. The benchmark is hard in a specific and
reproducible way: the best text-only system answers entity questions at 0.796 nDCG@10 and
the four defect-semantics families at 0.193, 0.151, 0.161 and 0.024, the last because no
document contains the phrase a geography-constrained question uses. A pretrained BGE
encoder does not fix this, reaching 0.010 on that family against 0.000 for every lexical
channel. We also ship the control that a predicate-defined collection needs and that such
collections rarely include. Because relevance is an executable rule, the rule can be run
as a ranking signal: a system that reads constraints off the question reaches 0.579
nDCG@10, but a control that simply adds a constant to every gold document over the same
300-document pool reaches 0.823 and the answer key 1.000, so that configuration recovers
about half of what a pure lookup is worth. The component that infers its slot instead of
reading it off recovers +0.014 nDCG@10 (95% CI [-0.005, 0.033]). We release the corpus
builder, the taxonomy, the queries, the baselines and these controls under MIT, with the
raw export identified by SHA-256, so that a system evaluated on QUEST-QI can be placed
against the lookup bound rather than against the leaderboard alone.

---

## 1 Introduction

A pharmaceutical quality investigation begins with a question about precedent. An
investigator holding a new deviation asks whether the same failure mode has been seen
before in the same dosage form, whether it has ever been classified as a serious hazard,
whether it clusters in a particular period or manufacturing geography, and what the same
firm has on record. The answers shape root-cause hypotheses, CAPA scope and
effectiveness-check design, and they must be traceable to source records because a
regulator will ask where each statement came from.

Retrieval-augmented generation [@lewis2020rag] is the obvious architecture for this, and
evaluating it needs a test collection. None exists for this domain. To our knowledge no
public benchmark covers retrieval over pharmaceutical quality and manufacturing records;
the openFDA enforcement data [@openfda_enforcement] has been used for epidemiological
description rather than as a retrieval corpus. QUEST-QI fills that gap.

Building a collection here means confronting the annotation problem directly. Relevance
judgments for questions of this kind need domain expertise that is expensive and scarce,
and the natural shortcut is to define relevance by a rule over the structured fields the
records already carry. We took that shortcut, and this paper reports both what it bought
and what it cost. It bought a collection that is reproducible from the corpus alone,
regenerable when the export is refreshed, and free of the incompleteness that pooling
introduces. It cost the property that makes retrieval evaluation meaningful: where the
relevance rule is executable, a system can be rewarded for reconstructing the rule rather
than for retrieving. We do not treat that as a caveat to be noted in a limitations
section. We treat it as something the resource has to measure, and we ship the
measurement.

**Contributions.**

1. **QUEST-QI**, a public benchmark for pharmaceutical quality-event retrieval: 4,652
   events from 1,655 firms in 24 countries, a 15-class defect taxonomy, and 171 questions
   in six families with predicate-defined gold sets, split into 52 dev and 119 test.
2. **Eight reproducible baselines** spanning lexical, corpus-trained and pretrained dense
   retrieval, with a diagnosis of where they fail that is tested rather than asserted: a
   pretrained encoder does not rescue the families that carry defect semantics.
3. **A circularity control shipped with the collection.** Because the relevance rule is
   executable, it can be run as a ranking signal, which turns an abstract worry about
   predicate-defined relevance into a number on the same scale as the leaderboard. We
   show the control needs two choices declared together -- how the gold signal enters the
   score, and what candidate set it can reach -- and that getting either wrong moves the
   number by more than any baseline in the table.

---

## 2 Related resources

**Retrieval benchmarks and their construction.** BEIR [@thakur2021beir] established
zero-shot retrieval evaluation across domains, and MTEB [@muennighoff2022mteb] ranks the
encoders that answer it; neither covers regulatory manufacturing records. That test
collections encode biases which flatter some systems over others is old and
well-established. Zobel showed that pooled collections are incomplete in ways that
systematically disadvantage systems absent from the pool [@zobel1998reliable], and Buckley
and Voorhees quantified how incompleteness changes measured ordering
[@buckley2004incomplete]; Buckley et al. named the limits of pooling directly
[@buckley2007bias], and Fuhr catalogued the evaluation errors that follow when these
properties are ignored [@fuhr2017mistakes].

**Human-optional collections.** Automatically generated collections trade annotation cost
for exactly this risk. Azzopardi and de Rijke showed that simulated known-item queries
carry a bias determined by the generation procedure [@azzopardi2007simulated]; pseudo test
collections built from anchor text or microblog structure inherit the biases of the signal
used to build them [@asadi2011pseudo; @berendsen2013pseudo], and weak supervision derived
from an existing ranker teaches a model that ranker's behavior [@dehghani2017weak]. Dietz
et al. survey the general case [@dietz2020humansoptional] and Rahmani et al. examine
collections generated by language models [@rahmani2024synthetic]. The parallel outside IR
is annotation artifacts: models reach high accuracy on NLI and fact-verification
benchmarks by exploiting regularities introduced during construction rather than by
performing the task [@gururangan2018artifacts; @schuster2019fever].

QUEST-QI sits squarely in this tradition, and what it adds is not the observation but a
measurement recipe that ships with the data. Where the relevance rule is an executable
predicate, the rule can be run as a ranking signal and reported on the leaderboard's own
scale. Section 3.4 gives the recipe and Section 4.4 the numbers.

**Downstream evaluation.** RAG evaluation has followed two lines: measuring attribution
directly [@rashkin2021attribution; @bohnet2022aqa; @gao2023alce; @min2023factscore], and
automating end-to-end judgment with a second language model [@es2023ragas;
@saadfalcon2023ares; @zheng2023llmjudge]. Both presuppose that the retrieved passages are
the right ones; surveys of hallucination [@ji2022hallucination] and trustworthy RAG
[@ni2025trustworthyrag] identify retrieval failure as an upstream cause. QUEST-QI
evaluates the retrieval stage only, and reports that in this domain it is the binding
constraint.

---

## 3 The resource

### 3.1 Corpus

We use the official openFDA drug enforcement bulk export (public domain, export date
2026-08-27), containing 17,899 records. A record is a product line; a recall *event* can
span hundreds of product lines sharing one firm, one reason for recall and one
classification. An investigator reasons about events, so we aggregate by `event_id`,
which also removes duplication that would otherwise dominate every metric, since one event
in this export spans 470 records.

The corpus holds **4,652 events** from 1,655 firms in 24 countries, spanning 2012-2026
(mean 3.85 records per event, median 1, max 470). By classification: 2,911 Class II, 1,142
Class III, 598 Class I, 1 not yet classified. Each event becomes one retrieval document
containing firm, location, classification, status, initiation and report dates, the
reason-for-recall text, up to eight distinct product presentations, distribution pattern
and notification mode; documents average 117 words (median 93, p95 263).

### 3.2 A defect taxonomy from canonical phrases

The FDA reason-for-recall field usually opens with a canonical defect phrase terminated by
a delimiter, as in "CGMP Deviations:", "Lack of Assurance of Sterility;" or "Labeling
- ...". We exploit this in three tiers. **Prefix tier**: the leading phrase is matched
against an ordered rule set of 15 categories (3,615 events). **Short tier**: the reason
has no delimiter but is short enough (<=60 characters) to be a canonical phrase itself,
and matches the same rules (855 events). **Classifier tier**: free-text narratives,
labeled by a TF-IDF logistic regression (182 events, 3.9%).

Rules cover **96.1%** of the corpus. The classifier trains *only* on prefix-tier events and
*only* on the text following the canonical phrase (3,559 examples), so the seed evidence is
never a feature. Five-fold cross-validation gives **0.717 macro F1** and 0.783 micro F1,
but that figure flatters the tail. 64.4% of those remainders still contain a phrase that
some rule matches, and 34.1% still echo the rule that produced their own label. Restricted
to the 1,266 remainders where no rule fires, which is the population the classifier
actually faces, macro F1 is **0.609** (micro 0.728). We treat the rule-free figure as the
estimate that matches deployment, and we report it here because a user of this resource
inherits the tail, not the average. Figure 1 shows the category distribution alongside the
per-category scores.

![Figure 1](figures/fig1_taxonomy.png)

*Figure 1: The 15-category defect taxonomy. Left, events per category. Right, five-fold
cross-validated F1 on the phrase-stripped task; the dashed line is overall macro F1
(0.717), which overstates performance on the free-text tail by about 0.11.*

Well-separated categories are unapproved marketing (0.93), labeling and packaging (0.92)
and impurity/degradation (0.86). Weak ones are stability/expiry (0.47) and
cross-contamination (0.56), both sharing vocabulary with neighbors.

### 3.3 Questions and predicate-defined gold sets

Each query pairs a natural-language question with a structured predicate; the gold
evidence set is every corpus event satisfying that predicate. This removes human relevance
judgment from the benchmark and makes it reproducible from the corpus alone. Table 1 gives
the six families with an example of each.

| Family | Predicate | Example question |
|---|---|---|
| A | defect × dosage form | *Find previous recall events for sterile injectable products where sterility of the finished product could not be assured.* |
| B | defect × severity class | *Which recalls with the most serious health consequences (Class I) were driven by a situation where the amount of active ingredient was outside the labeled strength?* |
| C | firm | *Summarize every recall event on record for the firm Amneal Pharmaceuticals, LLC.* |
| D | defect × period | *Between 2019 and 2021, which recalls happened because the batch did not meet its release testing profile for drug release rate?* |
| E | defect × non-US geography | *Find recalls from firms located outside the United States where a degradant or impurity exceeded its acceptance criterion.* |
| F | site country | *What recall events involve product manufactured or recalled from a site in Spain?* |

*Table 1: The six question families, their predicates and one generated example each.
Every question in the benchmark is an instantiation of one of these six templates; the 15
distinct question stems are the slot fillers applied to them.*

The questions are **generated, not written**. One template per family is instantiated with
slot fillers drawn from the taxonomy, the severity classes, the dosage-form vocabulary,
the firm list and the period grid. The 171 questions are all distinct as strings, but they
reduce to 15 distinct 45-character stems, and within a family the variation is confined to
the slots. Two consequences follow and we do not hide either. Lexical diversity is far
below what an investigator population would produce, so the absolute levels in Table 2
should not be read as an estimate of live performance. And because a template pairs one
phrasing with one predicate, a system that learned the template-to-predicate map would
score well without understanding anything. No human adjudicated any query-document pair.
Section 5 states what an adjudicated version would require.

Questions use investigator phrasing and deliberately avoid the FDA canonical phrase, so no
system can succeed by string-matching a category name: the STERILITY_ASSURANCE category is
asked as "sterility of the finished product could not be assured", never as "Lack of
Assurance of Sterility".

Family D's predicate uses the recall *initiation* year rather than the FDA report year,
which differ for 14.4% of events. The choice aligns the predicate with the field the
metadata filter reads, so that the two are not silently measuring different things. It
gives text-only systems no lexical advantage: both dates are written into the document
text, but as unsegmented eight-digit tokens (`20190315`), which the tokenizer keeps whole,
so neither date is matchable against "Between 2019 and 2021" by any lexical channel.

We keep queries whose gold set holds 3-75 events and sample up to 45 per family with a
fixed seed, giving **171 queries** (3,646 query-event gold pairs over 2,185 distinct
events; gold set size median 15, mean 21.3, max 71). A stratified 30/70 split yields **52
dev and 119 test** queries. Family sizes on the test split are uneven (A = 31, B = 18,
C = 31, D = 25, E = 10, F = 4), so per-family cells carry wide uncertainty and the pooled
aggregate is a mixture weighted by an arbitrary sampling cap.

### 3.4 What predicate-defined relevance costs, and how to measure it

A collection whose relevance is an executable rule invites a specific failure: a system
can score well by reconstructing the rule instead of retrieving. This is not hypothetical
here, and the resource is designed so that a user can size it rather than argue about it.

The recipe is to run the gold rule itself as a ranking signal and report the result on the
leaderboard's scale. It requires two choices, and our contribution is that they must be
declared together rather than one at a time:

- **How the gold signal enters the score.** Adding a constant to gold documents is a
  different bound from ranking the gold set first, and they differ by a wide margin.
- **What candidate set the signal can reach.** A control applied over a 300-document
  candidate pool bounds something different from one applied over all 4,652 events.

Getting either wrong moves the number by more than any baseline system in Table 2. We ship
three controls at the two extremes -- an additive constant over the pool, and a
gold-first answer key -- together with the pool-size and scoring-mechanism sensitivities,
so that a user reporting a QUEST-QI result can state the fraction of the lookup bound
their system recovers rather than an unanchored nDCG. Section 4.4 reports our own systems
against them.

We recommend that papers using QUEST-QI report this fraction alongside nDCG@10, and we
provide it as a one-line call in the released evaluation script.

---

## 4 Baselines

All systems index the 4,652 event documents and rank on one CPU core, with no external
API and no data leaving the boundary, which is what an on-premise deployment in a
regulated organization would look like. The pretrained encoders are the single exception:
their weights are downloaded once and then run locally.

**Text channels.** *BM25* [@robertson2009bm25]. *TF-IDF* cosine over 1-2-grams with
sublinear term frequency. *LSA*, truncated SVD to 300 dimensions over the TF-IDF matrix.
*word2vec*, skip-gram trained on the corpus (200 dimensions, window 8, 8 epochs),
documents as IDF-weighted mean token vectors.

**Pretrained encoders.** *BGE*, `BAAI/bge-base-en-v1.5` (768 dimensions, 512-token
window), encoded with the asymmetric query instruction it was trained with; *MiniLM*,
`all-MiniLM-L6-v2` (384 dimensions) [@reimers2019sbert]. Both are L2-normalized and ranked
by inner product. Model commit hashes are recorded in `results/dense_manifest.json`, so
"we used BGE" is a checkable statement rather than a model name.

**Fusion.** *Hybrid RRF*, reciprocal rank fusion (k = 60) of BM25 and LSA. *Hybrid RRF +
BGE* additionally fuses the BGE ranking. Hybrid RRF is the base the constrained
configurations are contrasted against, because it is the strongest configuration that
needs no downloaded weights and so is the one a reader can reproduce offline.

**Statistics.** Queries built from the same defect category share most of their gold
events, so an i.i.d. bootstrap over queries understates variance. Headline intervals and
contrasts use a cluster bootstrap over 50 clusters: one per defect category, plus one per
query for the entity families. Clusters are gold-disjoint within each block, but 44.9% of
the gold events in entity clusters also appear in some defect cluster, so the two blocks
are not independent and the intervals are not fully conservative. The 84 defect-family
test queries occupy only 15 clusters, so contrasts driven by those families have an
effective n nearer 15 than 119. Resamples are 2,000, drawn once and reused. Because the
two-sided p is twice the smaller tail, 2,000 resamples cannot resolve below 0.001; a
reported 0.0 means p < 0.001 and we never claim more. The clusters are over queries: the
corpus, the taxonomy, the templates and the predicates are held fixed in every resample,
so every interval here is a statement about query sampling variability alone.

### 4.1 Text-only retrieval

| System | R@10 | R@50 | R@100 | P@10 | **nDCG@10 (micro)** | 95% CI (cluster) | nDCG@10 (macro) | MRR |
|---|---|---|---|---|---|---|---|---|
| MiniLM (pretrained) | 0.105 | 0.213 | 0.259 | 0.088 | 0.136 | [0.092, 0.201] | 0.124 | 0.256 |
| word2vec (corpus-trained) | 0.147 | 0.244 | 0.286 | 0.103 | 0.159 | [0.105, 0.241] | 0.119 | 0.245 |
| BM25 | 0.221 | 0.342 | 0.389 | 0.164 | 0.236 | [0.169, 0.339] | 0.200 | 0.333 |
| TF-IDF | 0.241 | 0.362 | 0.416 | 0.166 | 0.264 | [0.186, 0.386] | 0.249 | 0.364 |
| BGE-base (pretrained) | 0.239 | 0.380 | 0.436 | 0.201 | 0.288 | [0.215, 0.393] | 0.296 | 0.410 |
| LSA (corpus-trained) | 0.257 | 0.411 | 0.484 | 0.208 | 0.299 | [0.221, 0.415] | 0.257 | 0.412 |
| Hybrid RRF (BM25 + LSA) | 0.260 | 0.396 | 0.457 | 0.211 | 0.302 | [0.225, 0.420] | 0.280 | 0.410 |
| **Hybrid RRF + BGE** | **0.284** | **0.424** | **0.494** | **0.229** | **0.341** | [0.260, 0.463] | **0.343** | **0.500** |

*Table 2: Text-only retrieval, 119 held-out test queries. Micro is the mean over queries;
macro is the unweighted mean over the six question families. Intervals are 2,000-resample
cluster bootstraps over 50 defect-category clusters, and are wide enough that only the
extremes of this table are separated. Cells are the four-decimal values in
`results/retrieval_results.json` displayed to three; several sit exactly on a half, where
either rounding is correct and this table uses both, so read a third-decimal difference of
one unit as a display artifact rather than a result.*

Fusion beats BM25 alone (+0.066, CI [0.034, 0.106], Holm p = 0.0) and TF-IDF alone
(+0.039, CI [0.004, 0.072], Holm p = 0.099) and is indistinguishable from LSA alone
(+0.003, CI [-0.024, 0.031], Holm p = 1.0). Averaged word2vec trails everything, and
MiniLM is worse still (fusion beats it by +0.167, CI [0.116, 0.244], Holm p = 0.0). A
general-purpose symmetric encoder is the wrong tool here.

**Neither encoder family dominates, and the aggregate decides which one looks better.**
Under the micro-average BGE-base reaches 0.288 against 0.302 for BM25 + LSA fusion, a
difference of 0.015 with CI [-0.047, 0.076] and Holm p = 1.0. Under the macro-average over
families the ordering reverses: BGE 0.296 against 0.280. Both differences are inside the
interval, so the defensible statement is that the two are indistinguishable on this
corpus. The reversal is a real difference in shape rather than noise: the micro-average is
dominated by the two largest families, and almost all of corpus-trained fusion's advantage
sits in `C_firm_history`, where it reaches 0.759 against BGE's 0.658 on 31 of 119 test
queries. Users of this resource should report both aggregates, as we do.

Users of this resource should report both aggregates, as we do. Adding BGE to the fusion
is worth +0.038, CI [0.023, 0.057], Holm p = 0.0 under the micro-average, and the dense
fusion leads under both (0.341 micro, 0.343 macro). Indexing is cheap: under a second for
BM25, tens of seconds for word2vec, and about five minutes to encode the corpus once with
BGE on CPU; per-query latency is in the low milliseconds on one core.

### 4.2 Where the benchmark is hard

![Figure 2](figures/fig2_family.png)

*Figure 2: nDCG@10 by question family, test split. Text-only fusion answers entity
questions and collapses on defect-semantics questions. The third bar re-executes the gold
predicate and is shown for scale, not as a system.*

Split by family, the aggregate hides two regimes. On **entity questions** (firm history
and site country) the best text-only system reaches 0.796 and 0.735 nDCG@10, because the
firm or country name is a rare string appearing verbatim in the target documents. On the
four **defect-semantics families** it reaches 0.193, 0.151, 0.161 and **0.024**.

The last is the clearest case. No document contains "outside the United States", so a
question built on that constraint retrieves almost nothing relevant. Every lexical channel
scores exactly 0.000 on this family; corpus-trained LSA reaches 0.013; **BGE, a pretrained
retrieval encoder, reaches 0.010**, and the fusion that includes it reaches 0.024. Adding a
strong pretrained encoder moves this family from nothing to nothing.

The reason is not that the country is missing from the text. It is written down in every
document: each opens `Location: <city>, <state>, <country>`, and 4,462 documents contain
the string "United States". What no similarity channel can express is the *complement* of
that set. Encoding the documents better cannot help, because the operation the question
requires is set difference and the operation a similarity score performs is not. This is
the property that makes QUEST-QI worth having as a resource: it isolates a class of
information need that better document representations do not address.

### 4.3 What query understanding is worth here

Giving a system the query's true defect category is worth 0.107 nDCG@10 on top of the
corpus-trained fusion, and 0.069 more than the strongest system in Table 2 reaches on its
own. That is an oracle over one component of the gold predicate rather than an obtainable
signal, and it sets up the measurement that follows.

The only component we could build that *infers* its slot rather than reading it off the
question is an unsupervised defect-category prior: cosine between the question's LSA
vector and each category's mean LSA vector, softmax-scaled, added to the fused score of
candidates in the matching category. It recovers **+0.014 nDCG@10** (95% CI [-0.005,
0.033], Holm p = 0.304) -- a null we cannot resolve at this sample size. Even that figure
is an upper bound rather than a clean measurement: the prior matches against the same
stored `defect_category` field the gold rule tests, so it is not fully independent of the
predicate either.

### 4.4 The circularity control

A metadata channel that reads severity class, year range, country and dosage form off the
question and down-weights violating candidates reaches **0.423** nDCG@10 on its own; a
hard prefilter with no defect prior reaches **0.464**; the prior added to that filter
reaches **0.579**, against 0.302 for the text-only base.

None of that is a retrieval result. The channel re-executes the benchmark's gold
predicate, comparing the same fields with the same regular expressions the predicate uses.
Applying the recipe of Section 3.4: a control that adds a constant to every gold document
over the same 300-document pool reaches **0.823**, and an answer key that ranks the gold
set first reaches **1.000**. The 0.579 configuration therefore recovers about half of what
the additive control is worth (**0.53**, 95% CI [0.31, 0.72]).

This is the number we think a QUEST-QI result should be reported against. A system that
posts 0.579 on this benchmark has not beaten the text-only baseline by 0.277; it has
recovered 0.53 of a lookup, and the fraction is the honest scale. Any benchmark whose
relevance is defined by an executable predicate rewards systems for reconstructing it. We
cannot remove that property from QUEST-QI without an annotation budget, so we quantify it
and ship the quantification.

---

## 5 Limitations and intended use

**The gold sets are not adjudicated.** No human judged any query-document pair. A
predicate is a definition of relevance, not a measurement of it, and where the predicate
and an expert would disagree, the benchmark follows the predicate. An adjudicated version
would need at least two qualified reviewers over at least 150 query-document pairs, with
agreement reported; we state this as the resource's principal limitation and as the first
thing a contributor could add.

**The questions are generated.** 171 strings reduce to 15 stems. Absolute levels in Table 2
are not an estimate of live performance, and a system that learns the
template-to-predicate map scores well without understanding anything. Twenty to thirty
investigator-written questions would test whether the baselines transfer off-template; the
released generator makes adding them mechanical.

**The intervals cover query sampling only.** The corpus, the taxonomy, the templates and
the predicates are fixed in every resample. A different export of the same openFDA data,
or a differently worded template set, could move these numbers by more than the intervals
suggest, and nothing here bounds by how much.

**The taxonomy's tail is weak.** Distant supervision covers 96.1%; the classifier that
handles the remainder scores 0.609 macro F1 on the rule-free population it actually faces.
Categories built on that tail are noisier than the headline figure implies.

**Intended use.** QUEST-QI is a retrieval benchmark for method development and comparison,
not an operational tool. Nothing in it should be read as an assessment of any firm's
current quality state, and no result from it should enter a regulatory decision without
human review of the underlying records.

---

## 6 Availability, licensing and maintenance

The corpus builder, the taxonomy, the queries, the baselines, the controls and every file
in `results/` are released at <https://github.com/phanibalagam/quest-qi> under the MIT
license, with a data card recording provenance and exclusions, and archived with the
concept DOI <https://doi.org/10.5281/zenodo.22668726>, which always resolves to the
latest archived version. The raw openFDA export is
US federal public domain and is identified in `data/raw/MANIFEST.json` by source URL and
SHA-256, so a user can obtain the identical export rather than a later one.

Seven numbered scripts run in order and write JSON into `results/`: corpus build,
taxonomy, benchmark construction, dense encoding, the text-only baselines, the
query-understanding systems with their controls, and a verifier that re-checks every
number in this paper against the result files and fails on any disagreement. Only the
dense-encoding step needs network access, and it need not be re-run: the systems that read
its output verify that the embedding ids match the current build, refuse to run against a
stale one, and skip their dense channels if it is absent. Single random seed 20260906
throughout; dependencies are numpy, scipy, scikit-learn, gensim, rank_bm25 and matplotlib,
plus sentence-transformers for encoding. Total runtime is a few minutes on one CPU core.

The benchmark regenerates from a newer openFDA export by re-running scripts 01-03; the
predicates are export-independent, so a refreshed corpus yields a comparable collection
rather than requiring re-annotation. That is the practical dividend of predicate-defined
relevance, and the reason we consider the trade-off worth making once its cost is
measured.

---

## Ethics and data statement

All data is public-domain US federal regulatory data about corporate entities; no personal
data is involved. No employer names, internal taxonomies, proprietary records or non-public
performance results were used at any point. Firm names appear in the corpus because they
are part of the public record; nothing here should be read as an assessment of any firm's
current quality state, and recall records reflect, among other things, differences in
reporting and inspection intensity.

## Declaration of generative AI and AI-assisted technologies

During the preparation of this manuscript, the author used Claude (Anthropic) to support the
drafting and editing of manuscript text, the development and revision of analysis code, and
the adversarial pre-submission review of the manuscript recorded in `notes/`. The author
retained sole responsibility for all final decisions concerning the research question, study
design, data selection, outcome definitions, analytical methods and experimental controls;
independently verified all sources, data and results; executed and validated the analyses;
interpreted the findings; reviewed and edited all AI-assisted content; and assumes full
responsibility for the accuracy and integrity of the manuscript.
