# ECIR 2027 resource-paper version

A 12-page cut of the manuscript for the **ECIR 2027 Resource Papers** track
(submission 2 November 2026, notification 7 December 2026, single-blind, Springer LNCS,
12 pages plus unlimited references, EasyChair).

## What is different from the long version

This is not the long paper with sections deleted. The resource track scores the artifact,
not the study, so the paper is reframed around it:

| | long version | this version |
|---|---|---|
| Lead contribution | the diagnosis and the null | the benchmark itself |
| Corpus, taxonomy, questions | Section 3, ~1,000 words | Section 3, expanded, with a section on what predicate-defined relevance costs |
| Five experiment sections | ~3,500 words | one baseline section, ~1,400 words |
| Availability and maintenance | a Reproducibility note | Section 6, including how the collection regenerates from a newer export |
| Limitations | Section 7, ~1,100 words | Section 5, condensed to four, each stated as work a contributor could do |

The long version remains the definitive account of the argument and is the one to cite for
the analysis. This one is the one to cite for the resource.

## Building and verifying

Both versions share one toolchain and one set of result files. Nothing here is a copy of a
script.

```
python3 scripts/10_build_latex.py --md venues/ecir2027/paper.md \
        --out venues/ecir2027/paper_lncs.tex --compile
python3 scripts/13_verify_variant.py venues/ecir2027 --page-limit 12
```

`figures/` and `references.bib` are symlinks to the parent, so a figure regenerated from
`results/` appears in both PDFs and cannot drift between them.

## What the variant verifier proves, and what it does not

The long manuscript is checked number by number against `results/` by
`scripts/08_verify_manuscript.py` (350 bindings, 0 failures). Re-running those bindings
here would fail on wording rather than on fact, because the prose is rewritten. So
`scripts/13_verify_variant.py` proves a different property:

1. **Containment.** Every decimal this paper states is a decimal the long manuscript
   states, and the long manuscript's numbers are bound to `results/`. Section numbers are
   stripped first, since they are navigation rather than data.
2. **Sentence bindings for the headline figures.** Containment alone cannot catch a value
   moved onto the wrong system -- a misattributed number is still a number the parent
   states, which is exactly the defect that reached an earlier draft. Seven headline
   figures are therefore read from `results/` and required to appear in a sentence naming
   the system they belong to.
3. **Artifact agreement.** Every number in `paper.md` is set in `paper_lncs.tex` and
   appears in the compiled PDF.
4. **The mandated disclaimer and the GenAI declaration**, in all three artifacts,
   including the clause disclosing the AI-assisted pre-submission review.
5. **The venue page limit**, measured as the page the References heading falls on.

Each of these was proved by reintroducing the defect it catches: an unbound number, a
swapped pair of system results, a removed disclaimer sentence, and a body one page over
the limit. All four failed the run; the restored file passes.

What it does not prove: that the reframed prose describes the resource accurately. Nothing
mechanical can check that, and it is what a reader should check.

## Current state

146 bindings, 0 failures. Body ends on page 12 of 12 allowed; references follow.
