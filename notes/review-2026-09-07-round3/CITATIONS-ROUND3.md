# CITATIONS — round 3

**Clean. No action required.** 37 entries in `references.bib`, 37 `\bibitem`s in
`paper_lncs.bbl`, no `[?]` in the PDF.

## Resolved this round

| entry | round 2 | round 3 |
|---|---|---|
| `robertson2009bm25` | 4(1–2):1–174, defended in the round-1 response | **3(4):333–389**, with a note recording the bad CrossRef deposit and the structural check (Silvestri's `10.1561/1500000013` carries the identical fields; FnTIR 3(3) ends at p. 331) |
| `fuhr2018mistakes` | year 2018 | **`fuhr2017mistakes`, 2017**, SIGIR Forum 51(3):32–41, doi 10.1145/3190580.3190586, with a note on ACM's online-publication date |
| `rahmani2024synthetic` | no DOI, no pages | **pp. 2647–2651, doi 10.1145/3626772.3657942**, marked `note = {Short paper}` |

The BM25 note is the right way to handle an aggregator that disagrees with the printed
article, and the References section's general statement of that rule is worth keeping in
the other nine papers.

## Corrections to my round-2 report

Two claims in `review/round2/CITATIONS-UNVERIFIED.md` were wrong. The response disputed
both and is correct on both; I verified against the round-2 `references.bib` directly.

**§2, "stale `year` fields on the versions of record" — withdrawn.** The round-2 bib
already carried `year = {2023}` for `singhal2022clinicalknowledge`, `ji2022hallucination`
and `rashkin2021attribution`, and `year = {2024}` for `es2023ragas`, each with the correct
journal, volume, pages and DOI. Nothing needed changing.

**§3, "nine of the twelve new entries have no DOI or page range" — withdrawn.** Counted
programmatically over the round-2 bib: **one** entry, `rahmani2024synthetic`.

Cause: the subagent report I worked from listed, per entry, the full correct metadata
under a heading of "corrections needed". Those per-entry values were accurate. I turned
them into summary counts of what was *missing* without checking the shipped `.bib` — the
same not-verified-against-the-artifact error this review has been charging the manuscript
with for three rounds.

Everything else in round 2's citation report stands, including the BM25 adjudication,
which the response accepted and acted on.

## Regulatory citation — unchanged and still correct

`fda_ai_credibility` is still noted "Draft guidance", which is still accurate: the January
2025 guidance (docket FDA-2024-D-4689) remains a Level 1 draft as of today with no final
version issued. The manuscript still contains no statement about EU GMP Annex 22, FDA
PCCP, Computer Software Assurance, ICH Q9(R1), GAMP 5, 21 CFR Part 11 or the EU AI Act,
and nothing implies any of them is adopted or in force. Third round running.
