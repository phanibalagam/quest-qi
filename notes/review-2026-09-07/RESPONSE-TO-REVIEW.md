# Paper 1 — response to the external pre-submission review

**Date:** 2026-09-07
**Review responded to:** `REVIEW-FINDINGS-PRESUBMIT.md` and `CITATIONS-UNVERIFIED.md`
in this folder (verdict: NO-GO, seven blocking findings).

**Author decisions taken before this pass:** cut §5.6 (the answer-synthesis study)
entirely, and fix everything that did not require new data collection.

**State after this pass:** `scripts/08_verify_manuscript.py` reports **0 failures**,
now checking `paper.md`, `paper_lncs.tex` **and** the text extracted from
`paper_lncs.pdf`. The full pipeline (scripts 01–04) was re-run from the raw export and
every number reproduces bit-identically.

---

## Blocking findings

| ID | Finding | Action |
|---|---|---|
| B1 | Generation study unreproducible; huggingface and generation-endpoint claims conflated | Removed with §5.6. The Limitations text on the encoder step now states the constraint precisely: certificate-trust and network policy, not weight availability. |
| B2 | Micro/macro reversal — BGE 0.296 macro vs hybrid 0.280, opposite of the micro ordering | Table 1 now carries **both** aggregates plus cluster CIs. §5.1 states the reversal, names its cause (`C_firm_history`, 0.759 vs 0.658, 31 of 119 queries), and claims only that neither family dominates. "so the failure is not a representation deficit" deleted from the abstract. |
| B3 | Disclaimer absent from `.tex` and PDF; verifier read `paper.md` only | Converter's front-matter parser fixed — it consumed everything up to `## Abstract`, silently dropping `## Disclaimer` — and now refuses to emit a `.tex` without it. Verifier checks all three artifacts, ligature-proof against T1 PDF extraction. |
| B4 | Table 4 denominators inconsistent (n = 16/15/14, not 24) | Removed with §5.6. |
| B5 | "We are not aware of prior work…" unsupportable | Sentence deleted. §2 rewritten against the pooling-bias literature (Zobel 1998; Buckley & Voorhees 2004; Buckley et al. 2007; Fuhr 2018; Azzopardi et al. 2007; Asadi et al. 2011; Berendsen et al. 2013; Dehghani et al. 2017; Dietz & Dalton 2020; Rahmani et al. 2024; Gururangan et al. 2018; Schuster et al. 2019). The claim is now the two-factor control recipe, not the observation. |
| B6 | Template generation undisclosed | Abstract, Contribution 1 and a new paragraph in §3.3 state: six templates, 15 distinct question stems, no human adjudication. A new Limitations paragraph, placed first, says what an adjudicated version would require. |
| B7 | Null presented as if it settled the question | §5.3 now states that the interval runs to +0.033 (11% relative, near the +0.038 that adding BGE buys), that no equivalence claim below that margin is available, and that roughly twice the query count would be needed. The Discussion echoes it. |

## Secondary findings

S1 cluster CIs added to Table 1 · S2 "four"→"seven" (script 04 runs seven contrasts) ·
S3 gold controls dropped from the Holm family — verified this leaves **every adjusted p
unchanged**, since all three sit below the 0.001 resolution floor · S4/S5/S6 new
paragraph stating that the bootstrap resamples queries only, and carries no uncertainty
from the corpus, taxonomy, classifier or templates · S7 gold-size window added to
`unswept_hyperparameters` · S8 "flat from 2"→"flat from 4", with the dev curve ·
S9 `data/raw/MANIFEST.json` now ships (source URL and full SHA-256), `DATA_CARD.md`
digests un-elided · S10 `CITATION.cff` re-emitted and parses · S11 `.bbl` ships,
`\includegraphics` switched to the vector PDFs, new `scripts/11_arxiv_package.py` builds
a minimal submission tarball, AI-use disclosure section added · S12 extended-preprint
status stated, no venue claimed · S13 script 03 comment corrected · S14 see below ·
M1 six self-applied "honest"s reduced to one, the 0.53 figure cut from five places to
three, the 13-bold run in Limitations merged · M2 design note date-stamped as
superseded · M3 verifier docstring now states what it cannot catch.

## Where this response disagrees with the review

**S14's first item does not hold.** The review states that `robertson2009bm25` should be
Vol. 3, No. 4, pp. 333–389. The publisher's own CrossRef deposit (`10.1561/1500000019`)
and OpenAlex both give **Vol. 4, No. 1–2, pp. 1–174**, which is what the bibliography
already had. The entry is kept, `number = {1--2}` added, with a note recording the
check. A reviewer who wants to re-check it can query CrossRef directly.

**B1 conflates two constraints.** The certificate issue that blocks huggingface.co and
the absence of a generation endpoint are different things. The conclusion still stands —
there was no logged evidence of an attempt — so §5.6 was cut regardless.

## Citation metadata

All 12 new references were verified at source (CrossRef, OpenAlex, ACL Anthology) for
title, authors, venue, year and pages. Four entries upgraded to the version of record:
`singhal2022clinicalknowledge` → Nature 620(7972):172–180; `ji2022hallucination` → ACM
Computing Surveys 55(12); `rashkin2021attribution` → Computational Linguistics
49(4):777–840; `es2023ragas` → EACL 2024 System Demonstrations, 150–158. The FDA guidance
title casing is fixed ("To Support"); the "Draft guidance" note is retained deliberately.

## Known open items, stated rather than fixed

1. **Gold-set adjudication.** At least two qualified reviewers over at least 150
   query–document pairs, to estimate agreement between the predicate and expert
   judgement. This is the single change that would move the paper from "the contrasts
   are trustworthy" to "the levels are trustworthy".
2. **20–30 investigator-written questions**, to measure how far the templates distort
   difficulty.

Neither is addressed here. Both are recorded as the benchmark's principal limitation in
§7, and a reviewer should read the absolute levels in Table 1 accordingly.

## Where things are

`arxiv_submission.tar.gz` is the submission package (tex, bbl, bib, 3 vector figures;
nothing else). Files removed by the §5.6 cut are preserved in `_superseded_20260907/`
rather than deleted, so the excision can be audited.
