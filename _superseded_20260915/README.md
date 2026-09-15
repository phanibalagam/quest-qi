# Superseded 2026-09-15

Work kept for the record and not under submission. Nothing in this directory is being
offered to any venue.

## `ecir2027/` -- ECIR 2027 resource-paper variant

A complete 12-page cut of the QUEST-QI manuscript, reframed for the ECIR 2027 Resource
Papers track: `paper.md`, `paper_lncs.tex`, `paper_lncs.bbl`, a compiled PDF and its own
README. It passed its variant verifier at 147 bindings, 0 failures, body ending on page 12
of 12.

**Why it is retired.** It was prepared alongside an arXiv route that has since been
withdrawn, and ECIR 2027 is held in person in Southampton, United Kingdom, 21-25 March
2027, with no virtual or hybrid option offered. The author attends US-hosted meetings
only, so the venue is not reachable. The decision is about travel, not about the quality
of the work.

**The long version is the live one.** The full manuscript at the repository root is the
definitive account and is the version under preparation for journal submission. Cite that.

## Two things to know if this is ever revived

- **The symlinks no longer resolve.** `ecir2027/` referenced `figures/` and
  `references.bib` as symlinks to the repository root. Moved one level deeper, those
  paths are wrong. Repoint them before building anything here.
- **`scripts/13_verify_variant.py` still works**, and the `--disclosure-on-form` flag it
  gained on 2026-09-15 is general rather than ECIR-specific: it inverts the
  generative-AI declaration check for venues that collect the disclosure on their
  submission form instead of in the manuscript. Its `--help` text still names
  `venues/ecir2027` as the example path, which no longer exists. Any future variant is a
  new directory, not a copy of this one.

The reframing itself -- leading on the artifact rather than the study, condensing five
experiment sections to one baseline, and rewriting limitations as work a contributor
could pick up -- is reusable for any resource or artifact track that is reachable.
