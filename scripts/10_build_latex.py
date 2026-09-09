"""
10_build_latex.py -- render paper.md into Springer LNCS LaTeX.

The manuscript is authored once, in Markdown, and this script generates the
submission source from it. Nothing is hand-ported, so the .tex cannot drift from
the .md that scripts/08_verify_manuscript.py checks against results/.

    python3 scripts/10_build_latex.py [--out paper_lncs.tex] [--compile]

Handles the constructs these papers actually use: the title/author block, an
abstract, numbered sections and subsections, pipe tables, figures with italic
captions, fenced code, ordered and unordered lists, inline emphasis and code,
[@key] citations, and the Unicode this author writes (en/em dashes, U+2212 minus,
times, non-breaking artefacts, accented names in the bibliography).

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Unicode the manuscripts use, mapped to LaTeX that compiles under pdflatex.
UNI = {
    "\u2014": "---", "\u2013": "--", "\u2212": "$-$", "\u00d7": "$\\times$",
    "\u2264": "$\\leq$", "\u2265": "$\\geq$", "\u2248": "$\\approx$",
    "\u2019": "'", "\u2018": "`", "\u201c": "``", "\u201d": "''",
    "\u03bb": "$\\lambda$", "\u00b1": "$\\pm$", "\u2192": "$\\rightarrow$",
    "\u00a0": "~", "\u2026": "\\ldots{}", "\u2011": "-",
    "\u00b7": "$\\cdot$", "\u0394": "$\\Delta$", "\u03b1": "$\\alpha$",
    "\u03b2": "$\\beta$", "\u03c1": "$\\rho$", "\u00b0": "$^\\circ$",
}
ESC = {"%": "\\%", "&": "\\&", "#": "\\#", "_": "\\_", "$": "\\$"}


def esc(t, in_code=False):
    """Escape LaTeX specials, THEN map Unicode.

    Order matters: several Unicode replacements are themselves LaTeX math
    ($\\times$), so mapping first and escaping second would escape the dollars we
    just inserted and produce "3.8\\$\\times\\$".
    """
    if not in_code:
        t = "".join(ESC.get(ch, ch) for ch in t)
    for k, v in UNI.items():
        t = t.replace(k, v)
    # Anything non-ASCII left over would reach pdflatex as an unmapped Unicode
    # character and fail the build several hundred lines later. Fail here, where
    # the offending character can be named.
    stray = {c for c in t if ord(c) > 127}
    if stray:
        raise SystemExit("unmapped non-ASCII character(s) in paper.md: "
                         + " ".join(f"{c!r} (U+{ord(c):04X})" for c in sorted(stray))
                         + "\n  add them to UNI in scripts/10_build_latex.py")
    return t


def inline(t):
    """Inline markup -> LaTeX, protecting code spans from escaping."""
    spans = []

    def stash(m):
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    t = re.sub(r"`([^`]+)`", stash, t)

    # Citations are stashed BEFORE escaping: bib keys contain underscores, and
    # escaping them first yields \cite{openfda\_enforcement}, which is not a key.
    cites = []

    def stash_cite(m):
        keys = ",".join(x.strip().lstrip("@").split(",")[0].strip()
                        for x in m.group(1).split(";"))
        cites.append(keys)
        return f"\x01{len(cites) - 1}\x01"

    t = re.sub(r"\[@([^\]]+)\]", stash_cite, t)
    t = esc(t)
    t = re.sub(r"\x01(\d+)\x01", lambda m: "\\cite{" + cites[int(m.group(1))] + "}", t)
    # Straight ASCII quotes render as two right-quotes in LaTeX; pair them.
    t = re.sub(r'"([^"]*)"', r"``\1''", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", t)
    t = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\\textit{\1}", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\\href{\2}{\1}", t)
    # Markdown autolinks <https://...> were passing through with their angle
    # brackets intact and rendering literally in the PDF.
    t = re.sub(r"<(https?://[^>\s]+)>", r"\\url{\1}", t)

    def pop(m):
        raw = spans[int(m.group(1))]
        raw = raw.replace("\\", "\\textbackslash{}")
        for k, v in ESC.items():
            raw = raw.replace(k, v)
        for k, v in UNI.items():
            raw = raw.replace(k, v)
        # A long path is one unbreakable word to TeX and overhangs the margin.
        # Insert zero-width breakpoints after the separators a path already has.
        # \\allowbreak inserts NOTHING when the break is taken, so a reader can
        # never mistake a line-break artifact for part of the path -- which is what
        # went wrong with [htt]{hyphenat}, whose breaks put a real hyphen in
        # "re-sults/retrieval_results.json". (\\seqsplit was tried first and chokes
        # on the escaped underscores these paths contain.)
        # Round 6, M16: the threshold was measured on the ESCAPED string, so a
        # path's length depended on how many underscores it happened to contain
        # (`data/raw/MANIFEST.json`, 22 escaped, missed it while a shorter real
        # path with underscores cleared it). Measure the visible token.
        _visible = raw.replace("\\_", "_").replace("\\%", "%").replace("\\&", "&")
        if len(_visible) > 20:
            # Round 7, M23: a breakpoint is only useful if BOTH sides of it are
            # long enough to read as a fragment of a path rather than as a word.
            # A break after "BAAI/" or "data/" leaves a five-character line end,
            # and a break inside "unswept_hyperparameters" leaves two strings
            # that each read as an identifier of their own. Require 8 visible
            # characters on either side, measured on the unescaped token.
            # Round 8, N57: the bound was 8 and the test was >=, so the
            # underscore in "unswept_hyperparameters" sat at visible position 8
            # and passed -- keeping the exact break the comment said to
            # suppress. The fragment left is what matters, so require 9.
            _MIN = 9
            _pieces, _cut = [], 0
            _pos_v = 0                      # position in the VISIBLE string
            _i = 0
            while _i < len(raw):
                if raw[_i] == "/":
                    _sep_len, _adv = 1, 1
                elif raw.startswith("\\_", _i):
                    _sep_len, _adv = 2, 1
                else:
                    _pos_v += 1
                    _i += 1
                    continue
                _pos_v += _adv
                _i += _sep_len
                if _pos_v >= _MIN and (len(_visible) - _pos_v) >= _MIN:
                    _pieces.append(_i)
            for _p in reversed(_pieces):
                raw = raw[:_p] + "\\allowbreak{}" + raw[_p:]
            # Round 6, M18: a breakpoint after the token's final character can
            # never be taken usefully. The 8-character rule above already
            # excludes it; this is belt and braces.
            if raw.endswith("\\allowbreak{}"):
                raw = raw[:-len("\\allowbreak{}")]
        return "\\texttt{" + raw + "}"

    return re.sub(r"\x00(\d+)\x00", pop, t)


def parse_table(lines):
    """Markdown table -> LaTeX.

    Wide tables are wrapped in \\resizebox so they cannot silently overflow the
    text block. This is not cosmetic: a numeric table that overflows is TRUNCATED
    in the rendered PDF -- LaTeX reports an Overfull \\hbox and carries on -- so
    columns present in the source vanish from the artifact a reader receives.
    That happened to this paper's retrieval table (Table 1 at the time, Table 2
    after the floats were renumbered): the macro-average column, added to fix
    a reviewer finding about selective reporting, overflowed by 151pt and did not
    appear in the PDF at all, while the manuscript verifier (which read only the
    Markdown) reported a clean run.

    Any table with more than the width a text-column table comfortably holds is
    boxed. A long-text table (the example-question table in Section 3.3) instead
    gets a fixed-width p{} column so it wraps rather than running off the page.
    """
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines]
    header, body = rows[0], rows[2:]
    ncol = len(header)
    # A column whose cells are long prose must wrap, not extend.
    widest = [max((len(r[c]) for r in body if c < len(r)), default=0)
              for c in range(ncol)]
    if ncol > 1 and max(widest) > 60:
        # Give the widest column the slack and let it wrap.
        w = widest.index(max(widest))
        # Round 9, N63: an l plus an r plus 0.62\linewidth exceeds \linewidth, so
        # the tabular and its booktabs rules ran 14.2pt into the right margin.
        # The verifier is designed never to report it -- "table" is on the
        # safe-environment list -- but a Springer copy editor would.
        spec = "".join(("p{0.52\\linewidth}" if c == w else
                        ("l" if c == 0 else "r")) for c in range(ncol))
        wrap = False
    else:
        spec = "l" + "r" * (ncol - 1) if ncol > 1 else "l"
        # Seven or more columns will not fit an llncs text block at \\small.
        # Seven was measured, not guessed: the query-understanding table has seven
        # and overhung the margin by 33pt before this threshold was lowered.
        wrap = ncol >= 7
    out = []
    if wrap:
        out.append("\\resizebox{\\textwidth}{!}{%")
    out += ["\\begin{tabular}{" + spec + "}", "\\toprule",
            " & ".join(inline(c) for c in header) + " \\\\", "\\midrule"]
    for r in body:
        r = (r + [""] * ncol)[:ncol]
        out.append(" & ".join(inline(c) for c in r) + " \\\\")
    out += ["\\bottomrule", "\\end{tabular}"]
    if wrap:
        out.append("}")
    return out


def convert(md, title_override=None):
    lines = md.split("\n")
    body, i = [], 0
    title, authors, abstract, disclaimer = None, [], [], []
    pending_float = None          # ("figure", path) awaiting its caption

    # ---- front matter -----------------------------------------------------
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("# ") and title is None:
            title = ln[2:].strip()
            i += 1
            continue
        if ln.startswith("## Disclaimer"):
            # The disclaimer sits before the abstract in paper.md. It must reach
            # the .tex; an earlier version of this converter silently dropped it,
            # because the front-matter loop consumed everything up to "## Abstract".
            i += 1
            while i < len(lines) and not lines[i].startswith(("---", "## ")):
                if lines[i].strip():
                    disclaimer.append(lines[i].strip())
                i += 1
            continue
        if ln.startswith("## Abstract"):
            i += 1
            while i < len(lines) and not lines[i].startswith(("---", "## ")):
                if lines[i].strip():
                    abstract.append(lines[i].strip())
                i += 1
            break
        if title is not None and ln.strip() and not ln.startswith(("---", "*", "#")):
            authors.append(ln.strip())
        i += 1

    if not disclaimer:
        raise SystemExit("10_build_latex: no '## Disclaimer' section found in the "
                         "Markdown source; refusing to emit a .tex without it")
    body += ["", "\\section*{Disclaimer}", inline(" ".join(disclaimer)), ""]

    # ---- body -------------------------------------------------------------
    while i < len(lines):
        ln = lines[i]
        st = ln.strip()

        if st.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            # Round 8, N51: an unwrapped verbatim block breaks across pages, and
            # LNCS then sets the running head and folio INSIDE the listing --
            # "22   P. K. Balagam" between two script lines, which is a
            # copy-editing reject. A minipage cannot break, so the block moves
            # whole to the next page instead of splitting.
            # Round 9, N59: the minipage cured the split listing by orphaning the
            # heading that introduces it -- "Reproducibility" and its one-line
            # intro were left alone at the foot of p21 with seven lines of white
            # under them, and the listing opened p22 under the running head with
            # nothing above it. \needspace asks for the whole group up front, so
            # heading, intro and listing move to the next page together.
            # The reservation has to be made BEFORE the heading that introduces
            # the block, or LaTeX honours it after the heading is already set and
            # strands it at the foot of the page -- which is what N59 reported.
            #
            # Round 10, N68: the first version searched only the last 7 body
            # entries and only for "\\section", so it silently reverted to the
            # pre-N59 placement under three shapes this document can reach --
            # a heading with several intro paragraphs (outside the window), a
            # listing under a \\subsection (there is already one in this
            # manuscript), and a second listing in the same section. It worked
            # here by coincidence of layout. Search the whole body backwards for
            # any sectioning command, stop at the previous listing so two blocks
            # in one section do not both reserve from the same heading, size the
            # reservation from what actually intervenes, and say so when there is
            # no heading to hoist above.
            _at, _stop = None, 0
            for _k in range(len(body) - 1, -1, -1):
                if body[_k].startswith("\\end{minipage}"):
                    _stop = _k + 1               # a previous listing ends here
                    break
                if re.match(r"\\(?:sub)*section\*?\{", body[_k]):
                    _at = _k
                    break
            if _at is None:
                sys.stderr.write(
                    "note: a verbatim listing has no sectioning command above it "
                    "since the previous listing, so its page reservation covers the "
                    "block alone; check that nothing is left stranded above it.\n")
            # Reserve the listing plus whatever sits between the heading and it,
            # rather than a fixed allowance.
            _between = len([x for x in body[(_at if _at is not None else _stop):]
                            if x.strip()])
            _need = len(buf) + _between + 3
            _ns = f"\\needspace{{{_need}\\baselineskip}}"
            if _at is not None:
                body.insert(_at, _ns)
            else:
                body.append(_ns)
            body += ["\\par\\noindent\\begin{minipage}{\\linewidth}",
                     "\\begin{verbatim}"] + buf + ["\\end{verbatim}",
                     "\\end{minipage}", ""]
            continue

        if st == "---" or not st:
            i += 1
            continue

        m = re.match(r"^### (?:(\d+\.\d+)\s+)?(.*)$", ln)
        if m:
            body += ["", "\\subsection{" + inline(m.group(2)) + "}"]
            i += 1
            continue
        m = re.match(r"^## (?:(\d+)\s+)?(.*)$", ln)
        if m:
            name = m.group(2)
            # Endmatter carries no section number. The AI declaration joins the
            # list: it is a required statement about the work, not a numbered
            # part of the argument, and it was rendering as "9 Declaration of
            # generative AI and AI-assisted technologies" in the body sequence.
            cmd = "section*" if name in ("Abstract", "Disclaimer", "References",
                                         "On the references",
                                         "Reproducibility",
                                         "Ethics and data statement",
                                         "Declaration of generative AI and "
                                         "AI-assisted technologies") else "section"
            body += ["", "\\" + cmd + "{" + inline(name) + "}"]
            i += 1
            continue

        m = re.match(r"^!\[[^\]]*\]\(([^)]+)\)", st)
        if m:
            pending_float = m.group(1)
            i += 1
            continue

        if st.startswith("|") and i + 1 < len(lines) and re.match(
                r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            tbl = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl.append(lines[i])
                i += 1
            cap = []
            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip().startswith("*"):
                while j < len(lines) and lines[j].strip():
                    cap.append(lines[j].strip())
                    j += 1
                i = j
            capt = " ".join(cap).strip("*").strip()
            body += ["", "\\begin{table}[t]", "\\centering", "\\small"]
            if capt:
                body.append("\\caption{" + inline(capt) + "}")
            body += parse_table(tbl) + ["\\end{table}", ""]
            continue

        if pending_float and st.startswith("*"):
            cap = []
            while i < len(lines) and lines[i].strip():
                cap.append(lines[i].strip())
                i += 1
            capt = " ".join(cap).strip("*").strip()
            body += ["", "\\begin{figure}[t]", "\\centering",
                     # Prefer the vector PDF: the Markdown points at the PNG so it
                     # renders in a browser, but LaTeX should use the PDF, and
                     # arXiv asks that unused files not be shipped (S11).
                     "\\includegraphics[width=\\linewidth]{"
                     + re.sub(r"\.png$", ".pdf", pending_float) + "}",
                     "\\caption{" + inline(capt) + "}", "\\end{figure}", ""]
            pending_float = None
            continue

        if re.match(r"^\d+\.\s", st) or st.startswith("- "):
            ordered = bool(re.match(r"^\d+\.\s", st))
            env = "enumerate" if ordered else "itemize"
            items = []
            while i < len(lines):
                s2 = lines[i].strip()
                if re.match(r"^\d+\.\s", s2) or s2.startswith("- "):
                    items.append(re.sub(r"^(\d+\.|-)\s+", "", s2))
                elif s2 and lines[i].startswith(("   ", "\t")):
                    items[-1] += " " + s2
                else:
                    break
                i += 1
            body += ["\\begin{" + env + "}"] + \
                    ["\\item " + inline(x) for x in items] + \
                    ["\\end{" + env + "}", ""]
            continue

        para = []
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(
                ("|", "#", "```", "![", "- ")) and not re.match(r"^\d+\.\s", lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        if para:
            body += [inline(" ".join(para)), ""]

    return title_override or title, authors, " ".join(abstract), "\n".join(body)


TEMPLATE = r"""\documentclass[runningheads]{llncs}
%% lmodern: without it, [T1]{fontenc} falls back to Type 3 bitmap EC fonts on any
%% TeX Live lacking cm-super, and the body text ships as unsearchable bitmaps.
\usepackage{lmodern}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{graphicx}
\usepackage{array}
%% Text extracted from the PDF is what the manuscript verifier reads, so how the
%% fonts map back to Unicode matters here beyond cosmetics. Measured on this build:
%% cmap makes EN-DASHES extract correctly on this build (verified: "0.46--0.53"
%% comes back as "0.46-0.53" and the PDF carries 24 en-dash characters). That is
%% the one that could corrupt a claim: without it a stated range merges into a
%% single wrong number. LIGATURES are NOT fixed: the T1
%% encoding still emits fi/fl/ff as single glyphs that pdftotext returns as C0
%% control bytes, so "finding" extracts as "nding". The verifier compensates for
%% that with its own T1_LIGATURES table; do not read this line as a claim that
%% extraction is clean.
\usepackage{cmap}
%% The Markdown captions carry their own "Table 1:" / "Figure 2:" labels, and the
%% in-text references point at those numbers. LaTeX's float counters number in
%% placement order, which is not the same order, so letting both run produced
%% captions reading "Table 1. Table 1:" and "Fig. 3. Figure 1:". Suppress the
%% automatic label and let the manuscript's own numbering stand.
\usepackage{caption}
\captionsetup{labelformat=empty,labelsep=none}
\usepackage{booktabs}
\usepackage{needspace}
\usepackage{amsmath}
\usepackage[hidelinks,pdftitle={%(title)s},pdfauthor={Phani Kumar Balagam},pdfsubject={%(keywords)s},pdfcreator={scripts/10\string_build\string_latex.py}]{hyperref}
\usepackage{orcidlink}
\usepackage[expansion=false]{microtype}
\renewcommand{\UrlFont}{\ttfamily\small}
%% xurl lets a long URL break at any character. Without it the FDA guidance URL in
%% the bibliography ran about 4.7cm past the right margin.
\usepackage{xurl}
%% Long \texttt tokens (file paths, model ids) are single unbreakable words to TeX
%% and overhang the margin. [htt]{hyphenat} was tried and withdrawn: it breaks them
%% by inserting a REAL hyphen, so "results/retrieval_results.json" rendered as
%% "re-sults/..." across a line break and a reader cannot tell the hyphen is not
%% part of the path. \seqsplit breaks at any character without inserting one, which
%% is the same property xurl gives URLs. inline() inserts \allowbreak after each
%% "/" and "_" in a long \texttt token, which breaks without adding a character.
\emergencystretch=2em

\begin{document}

\title{%(title)s}
\titlerunning{%(shorttitle)s}
\author{Phani Kumar Balagam\orcidlink{0009-0007-6762-399X}}
\authorrunning{P. K. Balagam}
\institute{Independent Researcher, United States\\
\email{balagam.phani@gmail.com}\\
\url{https://github.com/phanibalagam}}

\maketitle

\begin{abstract}
%(abstract)s
\keywords{%(keywords)s}
\end{abstract}

%(body)s

\bibliographystyle{splncs04}
\bibliography{references}

\end{document}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default=os.path.join(ROOT, "paper.md"))
    ap.add_argument("--out", default=os.path.join(ROOT, "paper_lncs.tex"))
    ap.add_argument("--keywords", default="")
    ap.add_argument("--shorttitle", default="")
    ap.add_argument("--compile", action="store_true")
    a = ap.parse_args()

    md = open(a.md, encoding="utf-8").read()
    title, authors, abstract, body = convert(md)
    short = a.shorttitle or (title.split(":")[0] if ":" in title else title[:60])
    tex = TEMPLATE % {"title": esc(title), "shorttitle": esc(short),
                      "abstract": inline(abstract),
                      "keywords": esc(a.keywords or "predicate-defined relevance, "
                                          "retrieval benchmark, pharmaceutical "
                                          "quality, evaluation circularity"),
                      "body": body}
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(tex)
    print(f"wrote {a.out} ({len(tex.splitlines())} lines)")

    if a.compile:
        d = os.path.dirname(a.out) or "."
        stem = os.path.splitext(os.path.basename(a.out))[0]
        # LaTeX drops .aux/.log/.out/.blg beside the source, where they sit in the
        # middle of the folder listing between the files a reader is looking for.
        # They are gitignored and excluded from the release already; -output-directory
        # keeps them out of sight as well. The two outputs that are NOT litter --
        # the PDF and the .bbl, which arXiv needs shipped -- are copied back to the
        # folder root below.
        bdir = os.path.join(d, "_build")
        os.makedirs(bdir, exist_ok=True)
        for cmd in (["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                     "-output-directory=_build", stem],
                    ["bibtex", os.path.join("_build", stem)],
                    ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                     "-output-directory=_build", stem],
                    ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                     "-output-directory=_build", stem]):
            r = subprocess.run(cmd, cwd=d, capture_output=True, text=True)
            if r.returncode != 0 and cmd[0] == "pdflatex":
                tail = [l for l in r.stdout.splitlines() if l.startswith("!")][:6]
                print("LaTeX errors:", *tail, sep="\n  ")
                sys.exit(1)
        # The PDF and the .bbl are outputs, not litter: the PDF is the artifact a
        # reader receives and the .bbl has to ship with the arXiv source, because
        # arXiv does not run BibTeX. Bring both back to the folder root; everything
        # else stays in _build/.
        import shutil
        pdf = os.path.join(d, stem + ".pdf")
        for ext in (".pdf", ".bbl"):
            src = os.path.join(bdir, stem + ext)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(d, stem + ext))
        if not os.path.exists(pdf):
            print("compile produced no PDF; see", os.path.join(bdir, stem + ".log"))
            sys.exit(1)
        print("compiled:", pdf, os.path.getsize(pdf), "bytes")
        print("  build artifacts in", bdir)


if __name__ == "__main__":
    main()
