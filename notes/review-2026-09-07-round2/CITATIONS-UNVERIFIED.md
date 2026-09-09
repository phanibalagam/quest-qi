# CITATIONS-UNVERIFIED — round 2

`references.bib`, 37 entries (25 in round 1, +12 in the rewritten §2). Verified against
CrossRef, OpenAlex, ACL Anthology, ACM DL, Springer, dblp, publisher pages and — where
metadata conflicted — **the published article's own printed citation line**.

**Structural health: excellent.** 37 entries, 37 `\bibitem`s in `paper_lncs.bbl`, 37
distinct keys cited in `paper_lncs.tex`, identical sets, zero uncited, zero missing, zero
`[?]` in the PDF. No fabricated references. All 12 new entries exist and are correctly
attributed.

**Field-level health: not yet.** One entry the author affirmatively defended is wrong,
three "versions of record" carry stale `year` fields, and nine of the twelve new entries
have no DOI or page range.

---

## 1. THE DISPUTED ENTRY — the author's rebuttal does not hold

### `robertson2009bm25` — **the round-1 finding was correct**

Round 1 said: Vol. 3, No. 4 (2009), pp. 333–389.
The response said: *"The publisher's own CrossRef deposit and OpenAlex both give Vol. 4,
No. 1–2, pp. 1–174, matching what the bib already had. Entry kept, `number = {1--2}`
added."*

**The rebuttal accurately describes what those two sources return, and both are wrong.**
now Publishers deposited corrupted metadata against this DOI. Evidence, source by source:

| source | what it says |
|---|---|
| CrossRef `api.crossref.org/works/10.1561/1500000019` | `"volume": "4", "issue": "1-2", "page": "1-174"` — **supports the author** |
| OpenAlex `api.openalex.org/works/doi:10.1561/1500000019` | volume 4, issue "1-2", pp. 1–174 — **but OpenAlex ingests CrossRef, so this is the same deposit, not a second witness** |
| Publisher redirect from `doi.org/10.1561/1500000019` | lands on `emerald.com/ftinr/article/4/1-2/1/…` — the landing URL is built from the same bad record |
| **ACM Digital Library**, `dl.acm.org/doi/abs/10.1561/1500000019` | page title, verbatim: *"…: Foundations and Trends in Information Retrieval: **Vol 3, No 4**"* |
| **The published article itself** — Robertson's own copy at City, University of London (`staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf`) | first-page citation line: *"Foundations and Trends® in Information Retrieval **Vol. 3, No. 4 (2009) 333–389**"*, DOI 10.1561/1500000019 |

And the decisive structural check — **4(1–2):1–174 is already occupied**:

- `api.crossref.org/works/10.1561/1500000013` returns Silvestri, *Mining Query Logs:
  Turning Search Usage Data into Knowledge*, `"volume": "4", "issue": "1-2", "page": "1-174"`.
  ACM DL independently confirms Silvestri as FnTIR Vol 4, No 1–2. Two DOIs cannot both be
  4(1–2):1–174, and 174 pages fits a query-log survey, not a 57-page BM25 monograph.
- FnTIR 3(3) is Liu, *Learning to Rank for IR*, pp. 225–331. The next monograph in
  volume 3 begins at **333** — exactly where BM25 starts.

**Verdict: reviewer correct, author incorrect.** Neither party confused the monograph with
another; the *publisher's deposit* did, by copying Silvestri's volume/issue/pages onto
Robertson & Zaragoza's DOI. Adding `number = {1--2}` propagated the error rather than
fixing it. CrossRef is not primary for volume and pages when the article's own printed
citation line disagrees.

```bibtex
@article{robertson2009bm25,
  title   = {The Probabilistic Relevance Framework: {BM25} and Beyond},
  author  = {Robertson, Stephen and Zaragoza, Hugo},
  journal = {Foundations and Trends in Information Retrieval},
  volume  = {3},
  number  = {4},
  pages   = {333--389},
  year    = {2009},
  doi     = {10.1561/1500000019},
  note    = {Volume/issue/pages per the published article; the publisher's CrossRef
             deposit erroneously lists 4(1--2):1--174, which belongs to Silvestri,
             \emph{Mining Query Logs} (10.1561/1500000013).}
}
```

Worth reporting the bad deposit to now Publishers / Emerald.

---

## 2. NEW ERRORS INTRODUCED IN ROUND 2 — stale `year` fields on the "versions of record"

The upgrade to versions of record was the right move and the venues are correct. But
three entries kept the preprint year against a version-of-record citation, which is
internally inconsistent and will render wrongly in the bibliography:

| key | venue (correct) | `year` must change |
|---|---|---|
| `singhal2022clinicalknowledge` | *Nature* **620**(7972):172–180, doi 10.1038/s41586-023-06291-2 | 2022 → **2023** |
| `ji2022hallucination` | *ACM Computing Surveys* **55**(12), Article **248**, 38 pp., doi 10.1145/3571730 | 2022 → **2023**. Also use `articleno = {248}, numpages = {38}` — CrossRef's `page: "1-38"` is not the ACM citation form |
| `rashkin2021attribution` | *Computational Linguistics* **49**(4):777–840, doi 10.1162/coli_a_00486 | 2021 → **2023** |
| `es2023ragas` | EACL 2024 System Demonstrations, pp. 150–158, doi 10.18653/v1/2024.eacl-demo.16 | 2023 → **2024**. Exact title is "**RAGAs**" — lowercase *s*, no hyphen in "Retrieval Augmented Generation"; brace-protect as `{RAGA}s` |

Citation keys can keep their old years; the `year` fields cannot.

---

## 3. THE TWELVE NEW REFERENCES — all verified, nine incomplete

Every one exists, with the title, first author and venue as cited. Corrections needed:

| # | key/ref | status | correction |
|---|---|---|---|
| 1 | Zobel, SIGIR 1998 | VERIFIED | add `pages = {307--314}`, `doi = {10.1145/290941.291014}` |
| 2 | Buckley & Voorhees, SIGIR 2004 | VERIFIED | add `pages = {25--32}`, `doi = {10.1145/1008992.1009000}` |
| 3 | Buckley, Dimmick, Soboroff & Voorhees, 2007 | VERIFIED | *Information Retrieval* **10**(6):**491–508**, `doi = {10.1007/s10791-007-9032-x}` |
| 4 | Fuhr, "Some Common Mistakes In IR Evaluation…" | **MISMATCH (year)** | *SIGIR Forum* **51**(3):**32–41**. The issue is dated **December 2017** and dblp indexes it as 2017; ACM's online-publication date of 22 Feb 2018 is where the author's "2018" comes from. **Change 2018 → 2017**; `doi = {10.1145/3190580.3190586}` |
| 5 | Azzopardi et al., simulated known-item queries, 2007 | VERIFIED (identified) | the intended paper is **"Building simulated queries for known-item topics: an analysis using six European languages"**, SIGIR 2007, pp. 455–462, `doi = {10.1145/1277741.1277820}` — three authors (Azzopardi, de Rijke, Balog). Do **not** confuse with the 2006 two-author "Automatic construction of known-item finding test beds" |
| 6 | Asadi, Metzler, Elsayed & Lin, SIGIR 2011 | VERIFIED | add `pages = {1073--1082}`, `doi = {10.1145/2009916.2010058}` |
| 7 | Berendsen et al., SIGIR 2013 | VERIFIED | add `pages = {53--62}`, `doi = {10.1145/2484028.2484063}` |
| 8 | Dehghani et al., SIGIR 2017 | VERIFIED | add `pages = {65--74}`, `doi = {10.1145/3077136.3080832}` |
| 9 | Dietz & Dalton, 2020 | VERIFIED (title) | exact title **"Humans Optional? Automatic Large-Scale Test Collections for Entity, Passage, and Entity-Passage Retrieval"**, *Datenbank-Spektrum* **20**(1):17–28, `doi = {10.1007/s13222-020-00334-y}`. Two authors, as cited |
| 10 | Rahmani et al., SIGIR 2024 | VERIFIED | pp. **2647–2651**, `doi = {10.1145/3626772.3657942}`. It is a short/resource paper — worth knowing if the text leans on it |
| 11 | Gururangan et al., NAACL 2018 | VERIFIED | specify **Volume 2 (Short Papers)**, pp. **107–112**, `doi = {10.18653/v1/N18-2017}` |
| 12 | Schuster et al., "Towards Debiasing Fact Verification Models" | VERIFIED | title exact. Venue is **EMNLP-IJCNLP 2019**, pp. **3419–3425**, `doi = {10.18653/v1/D19-1341}` |

`paper_lncs.blg` reports `Warning--empty journal` for `asai2023selfrag`, `bohnet2022aqa`,
`chen2023benchmarkingrag` and others — the arXiv-only `@article` entries. Cosmetic under
`splncs04`, but `@misc` with `howpublished` is the cleaner form and silences the warnings.

---

## 4. REGULATORY CITATION — still correct, keep it as it is

`fda_ai_credibility` — **still a draft as of September 2026. No final version has issued.**

- FDA guidance page: "**Draft Level 1 Guidance — Not for implementation. Contains
  non-binding recommendations**", issued 7 January 2025, docket FDA-2024-D-4689.
- CDER's *Artificial Intelligence for Drug Development* page still describes it as a 2025
  draft.
- Federal Register, 90 FR, 7 Jan 2025: "Draft Guidance for Industry".

The title casing fix ("**To** Support") is correct and matches FDA's exact title. The
"Draft guidance" note is retained and must stay through copy-editing — it is the one
thing in this bibliography that could silently become false.

The manuscript contains **no** statement about EU GMP Annex 22, FDA PCCP, Computer
Software Assurance, ICH Q9(R1), GAMP 5, 21 CFR Part 11 or the EU AI Act. Nothing in the
paper implies any of them is adopted, final, or in force. This check passes for the second
round running.

---

## 5. Summary

| | round 1 | round 2 |
|---|---|---|
| entries | 25 | 37 |
| fabricated | 0 | 0 |
| existence-verified | 25/25 | 37/37 |
| hard field errors | 1 (`robertson2009bm25`) | **1, unchanged and now affirmatively defended** |
| wrong `year` | 0 | **4** (3 introduced by the version-of-record upgrade, 1 in `Fuhr`) |
| missing DOI/pages | 17 | 9 (all new entries) |
| bbl/bib/cite consistency | n/a (no bbl) | clean, 37/37/37 |
