"""
11_arxiv_package.py -- assemble the arXiv submission tarball.

arXiv asks that a submission contain no extraneous files. Everything below is
either compiled or read at compile time:

  paper_lncs.tex      the source
  paper_lncs.bbl      the compiled bibliography; shipping it guarantees the
                      rendered reference list matches the local PDF and removes
                      the commonest arXiv build failure
  references.bib      kept alongside the .bbl for provenance
  figures/*.pdf       vector figures, the only ones the .tex includes

Deliberately NOT shipped: llncs.cls, splncs04.bst and orcidlink (all in arXiv's
TeX Live), the .png figures (unused by the .tex, and raster where vector exists),
and every result, script and data file.

    python scripts/11_arxiv_package.py

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import os
import re
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Packages go in _dist/, not the folder root: Explorer lists folders first and "_"
# sorts to the top, so the two things you actually hand to somebody are the first
# thing you see instead of being scattered through the file listing alphabetically.
# The name is DERIVED from the folder, so it cannot drift from it the way a typed
# name does, and it says what the file is FOR rather than what it is.
def package_slug(root):
    """The name every package in _dist/ is built from.

    Derived, never typed. First choice is the repository the paper itself points
    a reader at -- that URL is printed in the manuscript and checked by the arXiv
    submission audit, so the package, the folder's contents and the paper all name
    the same artifact and cannot drift apart. Falls back to the folder name minus
    its NN_ ordering prefix.
    """
    import re as _re
    for doc in ("README.md", "paper.md"):
        p = os.path.join(root, doc)
        if os.path.exists(p):
            m = _re.search(r"github\.com/[A-Za-z0-9_.-]+/([A-Za-z0-9_.-]+)",
                           open(p, encoding="utf-8").read())
            if m:
                return m.group(1)
    base = os.path.basename(root)
    return base.split("_", 1)[1] if _re.match(r"^\d+[_-]", base) else base


DIST = os.path.join(ROOT, "_dist")
SLUG = package_slug(ROOT)
OUT = os.path.join(DIST, SLUG + "_arxiv-source.tar.gz")

REQUIRED = ["paper_lncs.tex", "paper_lncs.bbl", "references.bib"]


def main():
    tex_path = os.path.join(ROOT, "paper_lncs.tex")
    missing = [f for f in REQUIRED if not os.path.exists(os.path.join(ROOT, f))]
    if missing:
        raise SystemExit("missing (run scripts/10_build_latex.py --compile first): "
                         + ", ".join(missing))

    tex = open(tex_path, encoding="utf-8").read()
    figs = sorted(set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex)))
    for f in figs:
        if not f.endswith(".pdf"):
            raise SystemExit(f"{f}: the .tex must include vector PDFs, not raster")
        if not os.path.exists(os.path.join(ROOT, f)):
            raise SystemExit(f"{f}: included by the .tex but not on disk")

    names = REQUIRED + figs
    os.makedirs(DIST, exist_ok=True)
    with tarfile.open(OUT, "w:gz") as tar:
        for n in names:
            tar.add(os.path.join(ROOT, n), arcname=n)
    print(f"wrote {OUT}")
    for n in names:
        print(f"  {n:32s} {os.path.getsize(os.path.join(ROOT, n)):>9,d} bytes")
    print("\nNot included, by design: llncs.cls, splncs04.bst, orcidlink (arXiv "
          "provides them), figures/*.png (unused by the .tex), and all scripts, "
          "results and data.")


if __name__ == "__main__":
    main()
