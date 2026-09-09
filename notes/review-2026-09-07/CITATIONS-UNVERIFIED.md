# CITATIONS-UNVERIFIED — quest-qi_paper1_20260907

Scope: all 25 entries in `references.bib`, checked against arXiv, ACL Anthology,
CrossRef/DOI, publisher pages and fda.gov. Method: resolve the identifier, confirm
exact title + first author + year at the source. "Plausible" was not accepted as
verified.

**Headline: 0 fabricated references. 1 hard metadata error. 1 title error.
17 entries with incomplete venue metadata. The bib's own header claim — "retrieved
programmatically from the arXiv API or CrossRef (2026-09-06) and verified to exist" —
holds for existence but not for field correctness.**

---

## 1. Verified wrong — must fix before submission

### robertson2009bm25 — WRONG VOLUME AND PAGES
- Manuscript: `volume = {4}, pages = {1--174}`
- Correct: *Foundations and Trends in Information Retrieval* **Vol. 3, No. 4 (2009),
  pp. 333–389**
- Title, authors, year and DOI (`10.1561/1500000019`) are correct.
- Evidence: https://dl.acm.org/doi/10.1561/1500000019
- This is the only citation in the paper whose bibliographic fields are factually
  wrong. It is the canonical BM25 reference and an IR reviewer will know the page
  range on sight.

### fda_ai_credibility — TITLE CASING DOES NOT MATCH FDA'S TITLE
- Manuscript: "Considerations for the Use of Artificial Intelligence **to** Support
  Regulatory Decision-Making for Drug and Biological Products"
- FDA's exact title capitalises the infinitive: "... Artificial Intelligence **To**
  Support ..."
- Evidence: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/considerations-use-artificial-intelligence-support-regulatory-decision-making-drug-and-biological

**Regulatory-status check (this was a blocking item): PASSES.** The entry's note reads
"Draft guidance; accessed 2026-09-06". That is correct as of today. The guidance was
issued as a draft in January 2025 (docket FDA-2024-D-4689, comments closed 7 Apr 2025);
no final version has been issued, and CDER's AI-in-drug-development page (last updated
1 May 2026) still lists it as a 2025 draft. The one sentence in the manuscript that
cites it (Limitations, "Human review remains mandatory") does not imply adopted status.
Keep the "Draft guidance" note — do not drop it in copy-editing.

---

## 2. Verified but incomplete — cite the published version

These resolve correctly on arXiv, but the work has since been formally published and a
reviewer will expect the version of record. The first two matter most.

| key | published as | why it matters |
|---|---|---|
| singhal2022clinicalknowledge | *Nature* **620**(7972):172–180 (2023), doi:10.1038/s41586-023-06291-2 | Cited to motivate the closed-book baseline in a manuscript that invokes regulatory credibility. Citing a preprint of a Nature paper here is the kind of thing a domain reviewer flags. |
| ji2022hallucination | *ACM Computing Surveys* **55**(12), doi:10.1145/3571730 | Survey used as a motivating citation; journal + DOI missing entirely. |
| rashkin2021attribution | *Computational Linguistics* **49**(4):777–840 (2023) | |
| es2023ragas | EACL 2024 System Demonstrations; published title is "**RAGAs**" (capitalisation differs) | |

## 3. Verified, venue metadata absent (lower priority, but a reviewer will notice)

All confirmed to exist with correct title/first author/year on arXiv. Each is an
`@article` with only an eprint, for work published at a named venue:

lewis2020rag (NeurIPS 2020) · karpukhin2020dpr (EMNLP 2020) ·
izacard2021contriever (TMLR 2022) · gao2023alce (EMNLP 2023) ·
saadfalcon2023ares (NAACL 2024) · min2023factscore (EMNLP 2023) ·
liu2023lostinmiddle (TACL 2024) · gao2022hyde (ACL 2023) ·
chen2023benchmarkingrag (AAAI 2024) · asai2023selfrag (ICLR 2024) ·
reimers2019sbert (EMNLP-IJCNLP 2019) · thakur2021beir (NeurIPS 2021 D&B) ·
muennighoff2022mteb (EACL 2023) · zheng2023llmjudge (NeurIPS 2023 D&B)

Note on `izacard2021contriever`: arXiv v1 (Dec 2021) was titled "**Towards**
Unsupervised Dense Information Retrieval with Contrastive Learning". The bib uses the
current/TMLR title, which is the right choice — flagged only so it is not "corrected"
back.

## 4. Verified, no action

gao2023ragsurvey · ni2025trustworthyrag · wang2022e5 · bohnet2022aqa — arXiv-only, no
formal venue found; entries are correct as they stand.

`openfda_enforcement` — URL resolves (openFDA Drug Enforcement Reports API). Minor: the
note carries an access date; keep it.

## 5. Citation keys vs. usage

`scripts/08_verify_manuscript.py` checks that every `[@key]` in `paper.md` exists in
`references.bib` and reports no orphans. All 25 entries appear in the compiled
bibliography of `paper_lncs.pdf` (25 numbered items, no `[?]` markers). No placeholder
citations, no "et al. (forthcoming)", no self-citations.

## 6. Citations that are MISSING rather than wrong

Not a bib-verification finding, but it belongs here because it is the largest
citation-side problem in the submission. §2 states: *"We are not aware of prior work
that quantifies the resulting circularity."* This claim is not supportable — see
Blocking B5 in `REVIEW-FINDINGS-PRESUBMIT.md`. The following are uncited and directly
on point:

- Zobel, *How reliable are the results of large-scale IR experiments?* SIGIR 1998
- Buckley & Voorhees, *Retrieval evaluation with incomplete information*, SIGIR 2004
- Buckley, Dimmick, Soboroff & Voorhees, *Bias and the limits of pooling for large
  collections*, Information Retrieval Journal 2007
- Azzopardi & de Rijke, on simulated known-item query bias, 2006/2007
- Asadi, Metzler et al., *Pseudo test collections for learning web search ranking
  functions*, SIGIR 2011
- Berendsen et al., *Pseudo test collections for training and tuning microblog
  rankers*, SIGIR 2013
- Dehghani et al., *Neural Ranking Models with Weak Supervision*, SIGIR 2017
- Fuhr, *Some Common Mistakes in IR Evaluation*, SIGIR Forum 2017
- Gururangan et al., *Annotation Artifacts in Natural Language Inference Data*,
  NAACL 2018; Schuster et al. on FEVER claim-only bias, EMNLP 2019
- Dietz et al., *Humans Optional? Automatic Large-Scale Test Collections*,
  Datenbank-Spektrum 2020
- Rahmani et al., *Synthetic Test Collections for Retrieval Evaluation*, SIGIR 2024

## 7. Nothing unverifiable

Every entry resolved to a primary source. There is no entry in this bibliography that
could not be checked, and none that failed an existence check.
