# Review notes — what these files are, and who wrote them

This folder holds the pre-submission review history of the QUEST-QI manuscript: ten rounds
of findings and the point-by-point responses to them. It ships with the release so that a
reader can check the responses against the reviews rather than taking them on trust, which
is what `DATA_CARD.md` promises.

Read this page before the rest, because the documents are written in the first person and
the "I" in them is not the author.

## Provenance

| Document | Produced by |
|---|---|
| `REVIEW-FINDINGS-*.md`, `CITATIONS-*.md`, `REGRESSION-REPORT.md` | An **external AI reviewer** — a separate model session given the release archive and asked to audit it adversarially. Not human peer review, and not a referee report from any venue. |
| `RESPONSE-TO-REVIEW.md` in each round | Drafted by the **AI assistant** (Claude, Anthropic) that also assisted with the analysis code and the manuscript text, working under the author's direction. Reviewed by the author, who decided what was changed. |
| Per-round `README.md` | Same as the responses. |
| `00-study-design.md` | A superseded working note from the start of the study, kept for provenance. |

So where a response says "I was wrong about this" or "I am not making this change, and here
is why", the first person is the assistant reporting on its own work, not the author
speaking. The author read these exchanges, decided each outcome, and is responsible for
what the manuscript says. That responsibility is stated formally in the manuscript's
*Declaration of generative AI and AI-assisted technologies*.

Two consequences worth stating plainly, because the documents do not say them themselves:

- **The reviews are machine-generated.** They are detailed and several of their findings
  were substantive, but they carry none of the authority of human peer review, and no
  reviewer named in them is a person.
- **Some responses record editorial judgement, not just edits.** Round 9's M34, for
  instance, declines a reviewer's request about rounding conventions and argues the point.
  The reasoning in these files was drafted by the assistant; the decision to keep or
  overturn it was the author's.

## What the rounds contain

Rounds 1–3 found errors that would have embarrassed the paper: a hidden macro-average that
reversed a headline result, a missing disclaimer in the typeset artifact, and a control
that could not bound the systems it was meant to bound. Rounds 4–6 found corrections that
had landed in one file and not another. Rounds 7–10 found almost nothing wrong in the paper
itself and instead found claims *about* the paper that were untrue — in the responses, in
the README, and in the verification script.

The last of those is the honest summary of what this history is worth: by the end, the
manuscript was the most reliable artifact in the repository and the documents describing it
were the least. `scripts/08_verify_manuscript.py` exists because of that, and the rule it
enforces is that a sentence describing what the tooling does is a claim, and gets checked
like one.

## Reading them

Each round's folder holds the review as received, unedited, and the response to it. They
are in chronological order; `review-2026-09-07/` is round 1. Nothing has been removed from
a review after the fact. Where a later round corrected an earlier response, the correction
is marked inline in the earlier file rather than the file being quietly rewritten.
