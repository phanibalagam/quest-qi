> **Status: superseded working note, written 2026-09-05 before the study was run.**
> It records the original framing, including a working title and a scope that included
> an answer-synthesis study. Both changed. The manuscript (`paper.md`) is the only
> current statement of what this work claims; where this note and the manuscript
> disagree, the manuscript is right. Kept for provenance, not as documentation.

# Study design — Paper 1

Working title: **Evidence-Grounded Retrieval-Augmented Generation for Pharmaceutical
Quality Investigations: A Public Benchmark and Fully-Local Baseline**

Workbook idea #1. Slug: `regulatory-grade-genai-quality-investigations`.

## One-sentence contribution
We release the first public benchmark for evidence retrieval and citation-constrained
answer synthesis over FDA drug enforcement records, and show that a fully-local
retrieval stack — no external model API, no model download — recovers the evidence a
quality investigator needs with measurable groundedness and citation precision.

## Why this framing
A regulated quality organization cannot send investigation text to an external model
endpoint without a validated context of use. Every component here runs inside the
network boundary and every answer sentence carries a record-level citation.

## Environment constraints (documented, not hidden)
- `api.fda.gov`, `download.open.fda.gov`, `huggingface.co` unreachable from the
  analysis hosts. Corpus obtained as the official openFDA bulk export.
- No pretrained transformer encoder available -> dense retrieval is corpus-trained
  (LSA / word2vec), which is also the on-premise-realistic setting.
- No LLM API available to scripts -> generation is run through a documented manual
  harness over a fixed question set, with all prompts and outputs archived.

## Data
openFDA drug enforcement reports (public domain), full export.
Each record: firm, address, product description, reason for recall, classification,
recall number, dates, distribution pattern, status.

## Defect taxonomy (proposed contribution)
`reason_for_recall` frequently opens with a defect phrase terminated by a colon
("Lack of Assurance of Sterility:", "CGMP Deviations:", "Failed Content Uniformity
Specifications:"). Normalising these yields an automatically-labelled defect
taxonomy — verify coverage empirically before relying on it.

## Benchmark construction
Queries are natural-language investigation questions parameterised over structured
predicates (defect category x product/dosage form x classification x firm x period).
Gold evidence = the record set satisfying the predicate. Objective, reproducible,
no human labelling required for the retrieval half.

## Systems compared
1. BM25 (lexical)
2. TF-IDF cosine
3. LSA / truncated SVD (corpus-trained dense)
4. word2vec-averaged embeddings (corpus-trained dense)
5. Hybrid reciprocal-rank fusion of BM25 + best dense

## Metrics
Retrieval: Recall@{10,50,100}, nDCG@10, MRR, Precision@10, with bootstrap CIs.
Generation: groundedness, citation precision, citation recall, completeness,
against gold evidence sets.

## Integrity
Public-domain data only. No employer names, internal taxonomies, or proprietary
records. All limitations, leakage controls and human-review requirements reported.
