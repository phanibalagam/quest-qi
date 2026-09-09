# Pre-submission review, round 10, 2026-09-07 — GO

Rounds 1–9 are in `../review-2026-09-07{,-round2,…,-round9}/`.

| File | What it is |
|---|---|
| `REVIEW-FINDINGS-ROUND10.md` | The external review as received, unedited. |
| `RESPONSE-TO-REVIEW.md` | What was changed and what was tested. |

Round 10 is the first GO. The manuscript came through a full independent recomputation
clean for the second round running and nothing in it was held for submission. Every
finding was in the tooling, and the two that mattered were a guarantee asserted in prose,
absent in code, and invisible because the prose described the code inaccurately — the
reviewer changed two percentages in Section 5.2 and 347 bindings did not notice.

The habit this series ends on, from the round-9 response: a sentence describing what the
tooling does is a claim, and gets checked like one.
