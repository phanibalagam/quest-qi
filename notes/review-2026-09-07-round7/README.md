# Pre-submission review, round 7, 2026-09-07

Rounds 1–6 are in `../review-2026-09-07{,-round2,-round3,-round4,-round5,-round6}/`.

| File | What it is |
|---|---|
| `REVIEW-FINDINGS-ROUND7.md` | The external review as received, unedited. |
| `RESPONSE-TO-REVIEW.md` | What was changed and what was tested. |

Round 7 found that the round-6 fix for an *ambiguous* wrong-parent phrase had produced an
*unambiguous* wrong-parent claim, and — by mutation-testing the verifier — that two of the
three numbers round 6 corrected carried no binding at all. Its refinement of round 6's
instruction is the procedure this repository now follows: check what a number is
**attached to** — every "of that X", "on top of Y", "captures", "raises to" — against the
computation that produced it, not against the sentence it replaced.
