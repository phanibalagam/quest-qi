"""
12_release_package.py -- build the release archive from the tracked file set.

Why this exists. Three review rounds of this paper were each decided by a
correction that landed in one place and not another, and one of them was a
packaging failure: the release tarball was built by archiving the working
directory, so it carried `data/raw/`'s 4 MB export and the 20 MB embeddings --
two files that `.gitignore`, `DATA_CARD.md` and `data/raw/MANIFEST.json` all
state are NOT redistributed. The documents were right and the archive was wrong.

Building the archive from the same exclusion rules the documents describe is the
only way to keep them true. This script reads `.gitignore` and refuses to build
if anything it would ship contradicts the data card.

    python scripts/12_release_package.py            # -> quest-qi_release.tar.gz
    python scripts/12_release_package.py --zip      # -> quest-qi_release.zip

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tarfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_CARD = os.path.join(ROOT, "DATA_CARD.md")


def _card_section(heading_re):
    if not os.path.exists(DATA_CARD):
        return None
    text = open(DATA_CARD, encoding="utf-8").read()
    m = re.search(r"##\s*" + heading_re + r"(.*?)(?:\n##\s|\Z)", text, re.S)
    return m.group(1) if m else None


def promised_present():
    """Paths DATA_CARD.md lists under 'What is in this repository'.

    The card is a promise in both directions. An earlier version of this script
    enforced only the 'What is not' half, so a directory the card said SHIPS could
    be missing from the archive and both this script and the manuscript verifier
    stayed green -- which is exactly what happened with `_superseded_20260907/`.
    """
    sec = _card_section(r"What is in this repository")
    if sec is None:
        return None
    # EVERY backticked path in the section, not just the first per bullet. The
    # bullet-anchored pattern was copied from promised_absent(), where it is
    # correct because each exclusion bullet names the excluded path first and then
    # the mechanism that replaces it. Here it is wrong: one bullet lists three
    # sibling review directories, and only the first was ever enforced -- so the
    # folder added to fix the previous round's stale card could be deleted and the
    # build still succeeded.
    return [m for m in re.findall(r"`([A-Za-z0-9_./*-]+)`", sec)
            if "/" in m or m.endswith(".md")]


def promised_absent():
    """Read the paths DATA_CARD.md lists under 'What is not, and why'.

    The point of this script is that the archive and the documents cannot drift
    apart, so the list of things that must not ship is read from the document
    that makes the promise, not typed in here. The two fallbacks below are used
    only if the data card cannot be parsed, and the script says so when it falls
    back rather than pretending it checked.
    """
    # Widened from data/raw/openfda/ to data/raw/: the card excludes the whole
    # directory, so a raw export at any other path under it escaped the narrower one.
    fallback = ["data/processed/dense_embeddings.npz", "data/raw/"]
    sec = _card_section(r"What is not,? and why")
    if sec is None:
        return fallback, True
    m = type("M", (), {"group": staticmethod(lambda _i: sec)})()
    # Each bullet names the excluded path FIRST; later backticks in the same
    # bullet name the mechanism that replaces it (the manifest, the script that
    # regenerates it) and those do ship.
    paths = re.findall(r"^\s*[-*]\s*`([A-Za-z0-9_./-]+)`", m.group(1), re.M)
    # .gitignore's "!" lines are explicit carve-outs from those exclusions.
    _, negs = load_gitignore()
    paths = [p for p in paths if p.rstrip("/") not in [n.rstrip("/") for n in negs]]
    return (paths, False) if paths else (fallback, True)


def load_gitignore():
    path = os.path.join(ROOT, ".gitignore")
    pats, negs = [], []
    if not os.path.exists(path):
        return pats, negs
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        (negs if line.startswith("!") else pats).append(line.lstrip("!"))
    return pats, negs


def ignored(rel, pats, negs):
    def hit(p, patterns):
        for pat in patterns:
            base = pat.rstrip("/")
            if fnmatch.fnmatch(p, base) or fnmatch.fnmatch(os.path.basename(p), base):
                return True
            if pat.endswith("/") and (p + "/").startswith(base + "/"):
                return True
            if fnmatch.fnmatch(p, base.rstrip("*").rstrip("/") + "/*"):
                return True
        return False
    return hit(rel, pats) and not hit(rel, negs)


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


def walk_all():
    """Every file on disk, before any exclusion is applied."""
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in filenames:
            out.append(os.path.relpath(os.path.join(dirpath, fn), ROOT)
                       .replace(os.sep, "/"))
    return sorted(out)


def collect():
    pats, negs = load_gitignore()
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
            if not ignored(rel, pats, negs):
                out.append(rel)
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", action="store_true", help="write a .zip instead of .tar.gz")
    ap.add_argument("--name", default=None,
                    help="package stem; defaults to <repo-slug>_repo-release")
    a = ap.parse_args()
    if a.name is None:
        a.name = package_slug(ROOT) + "_repo-release"

    files = collect()
    forbidden, used_fallback = promised_absent()

    # The scan runs over the RAW walk, not the post-.gitignore set. An earlier
    # version checked the filtered list, which meant the guard could only fire if
    # .gitignore was itself broken -- so a reviewer who created the forbidden
    # files found the script building happily and reporting nothing. Reporting
    # "present on disk and correctly excluded" is the useful signal; shipping one
    # is the failure.
    on_disk = walk_all()
    _carve_early = {c.rstrip("/") for c in load_gitignore()[1]}
    present = [f for f in on_disk
               if f not in _carve_early
               and any(f == m or f.startswith(m.rstrip("/") + "/") for m in forbidden)]
    _, carve_outs = load_gitignore()
    carve = {c.rstrip("/") for c in carve_outs}
    shipping = [f for f in files
                if f not in carve
                and any(f == m or f.startswith(m.rstrip("/") + "/") for m in forbidden)]
    if shipping:
        raise SystemExit(
            "refusing to build: DATA_CARD.md states these are not in this "
            "repository, but the archive would contain them:\n  "
            + "\n  ".join(shipping))
    if used_fallback:
        # An earlier version printed a warning and built anyway -- including when
        # DATA_CARD.md was absent entirely, which produced an archive with no data
        # card in it. If the card cannot be read, the archive cannot be checked
        # against it, and an unchecked archive is the thing this script exists to
        # prevent.
        raise SystemExit(
            "refusing to build: could not read DATA_CARD.md's \"What is not, and "
            "why\" list, so the archive cannot be verified against the data card. "
            "Fix the card (or its headings) and re-run.")
    # N20: the other half of the promise.
    must_ship = promised_present()
    if must_ship is None:
        raise SystemExit("refusing to build: could not read DATA_CARD.md's \"What is "
                         "in this repository\" list.")
    missing = []
    for want in must_ship:
        if "*" in want:                       # e.g. results/*.json
            if not any(fnmatch.fnmatch(f, want) for f in files):
                missing.append(want)
            continue
        stem = want.rstrip("/")
        if not any(f == stem or f.startswith(stem + "/") for f in files):
            missing.append(want)
    if missing:
        raise SystemExit(
            "refusing to build: DATA_CARD.md says these are in this repository, but "
            "the archive would not contain them:\n  " + "\n  ".join(missing)
            + "\nEither ship them or correct the data card.")
    # The third direction: nothing checked SHIPPED -> PROMISED, so a new top-level
    # directory could ship undocumented indefinitely. That is how the round-4
    # review folder got in.
    # Round 6, N36: this read only f.split("/")[0], so "notes/" satisfied it
    # forever however many undocumented review folders appeared beneath it --
    # which is exactly the defect it was written to catch, six rounds running.
    # And `if "/" in f` excluded every top-level FILE, so a stray file at the
    # root could never be noticed. Enumerate EVERY directory prefix of every
    # file, plus every top-level file.
    _tops = set()
    for f in files:
        _parts = f.split("/")
        for _i in range(1, len(_parts)):
            _tops.add("/".join(_parts[:_i]) + "/")
        if len(_parts) == 1:
            _tops.add(f)
    _tops = sorted(_tops)
    _named = " ".join(must_ship) + " " + (_card_section(r"What is in this repository") or "")
    # A path is documented if the card names it, with or without its trailing
    # slash; a directory is NOT documented merely because its parent is.
    _undocumented = [d for d in _tops
                     if d not in _named and d.rstrip("/") not in _named]
    if _undocumented:
        raise SystemExit(
            "refusing to build: these paths are in the archive but "
            "are named nowhere in DATA_CARD.md's \"What is in this repository\":\n  "
            + "\n  ".join(_undocumented)
            + "\nDocument them in the card, or exclude them.")

    print(f"checked DATA_CARD.md in all three directions: {len(must_ship)} promised "
          f"path(s) present, {len(forbidden)} excluded path(s) absent, "
          f"{len(_tops)} shipped path(s) (every directory prefix and every "
          f"top-level file) all documented")
    print("  excluded: " + ", ".join(forbidden))
    if present:
        print(f"  {len(present)} such file(s) exist locally and were correctly "
              f"excluded: {', '.join(present[:4])}"
              + (" …" if len(present) > 4 else ""))
    else:
        print("  none present locally, so nothing to exclude")

    # The archive's internal top-level folder is what a reader sees when they
    # unpack it, and what becomes the repository root if they push it. Naming it
    # after the working folder means it inherits whatever that machine happens to
    # call it -- "paper1" here, "01_quest-qi-predicate-defined-relevance" on
    # another. Use the same derived slug the package filename uses, so the
    # unpacked tree matches the repository the manuscript points at.
    stem = package_slug(ROOT)
    dist = os.path.join(ROOT, "_dist")
    os.makedirs(dist, exist_ok=True)
    out = (a.name + (".zip" if a.zip else ".tar.gz")) if os.path.isabs(a.name) \
        else os.path.join(dist, a.name + (".zip" if a.zip else ".tar.gz"))
    if a.zip:
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                z.write(os.path.join(ROOT, f), os.path.join(stem, f))
    else:
        with tarfile.open(out, "w:gz") as t:
            for f in files:
                t.add(os.path.join(ROOT, f), os.path.join(stem, f))

    # A build record beside the packages. The point is that a FILENAME is an
    # unverified claim -- a date in it says when somebody typed the name, not what
    # is inside -- so the identity is generated here instead, by the script that
    # does the building. A hash answers "are these two the same build?", which no
    # timestamp can, and recording the verifier's outcome answers the question
    # that actually matters: was this build green when it was cut?
    import hashlib
    import datetime as _dt

    def _sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    _verifier = None
    try:
        _v = subprocess.run([sys.executable,
                             os.path.join(ROOT, "scripts", "08_verify_manuscript.py")],
                            capture_output=True, text=True, timeout=600, cwd=ROOT)
        _m = re.search(r"checks run: (\d+) bindings, (\d+) failure", _v.stdout)
        if _m:
            _verifier = {"bindings": int(_m.group(1)), "failures": int(_m.group(2))}
    except Exception:
        pass                       # a build record that cannot say is better than one that lies

    _pages = None
    _pdf = os.path.join(ROOT, "paper_lncs.pdf")
    if os.path.exists(_pdf):
        try:
            _pi = subprocess.run(["pdfinfo", _pdf], capture_output=True, text=True)
            _pm = re.search(r"Pages:\s+(\d+)", _pi.stdout)
            _pages = int(_pm.group(1)) if _pm else None
        except Exception:
            pass

    info = {
        "package": os.path.basename(out),
        "built_utc": _dt.datetime.now(_dt.timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": len(files),
        "manuscript_sha256": _sha(os.path.join(ROOT, "paper.md")),
        "pdf_sha256": _sha(_pdf) if os.path.exists(_pdf) else None,
        "pdf_pages": _pages,
        "verifier": _verifier,
        "note": ("Generated by scripts/12_release_package.py at build time. The "
                 "package filename carries no date on purpose: it is a claim "
                 "nothing checks. This file is the claim that is checked."),
    }
    with open(os.path.join(dist, "BUILD-INFO.json"), "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=2)
        fh.write("\n")

    _slug = package_slug(ROOT)
    with open(os.path.join(dist, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(f"""# Packages

Two files, and what each one is for.

| File | Where it goes |
|---|---|
| `{_slug}_arxiv-source.tar.gz` | Upload to arXiv. LaTeX source, the compiled `.bbl` and the figures \u2014 arXiv builds the PDF from it. |
| `{_slug}_repo-release.zip` | Push to the public repository. The whole tracked tree: manuscript, scripts, results, data card, licences, review notes. |

`BUILD-INFO.json` records when these were built, how many files, the SHA-256 of the
manuscript and the PDF, and the verifier's result at build time.

Both are rebuilt in place by `scripts/11_arxiv_package.py` and
`scripts/12_release_package.py --zip`, so these names always point at the current
build. They carry no date on purpose \u2014 a date in a filename says when somebody
typed the name, not what is inside, and two copies of the same name can disagree.
Use the hashes in `BUILD-INFO.json` to tell two builds apart.

To keep a version you sent somewhere, copy it into `_archive/` with an ISO-8601
UTC stamp: `_archive/{_slug}_repo-release_20260908T2235Z.zip`. Dates belong on
frozen snapshots, not on the working copy.
""")

    total = sum(os.path.getsize(os.path.join(ROOT, f)) for f in files)
    print(f"wrote {out}")
    print(f"  {len(files)} files, {total / 1e6:.1f} MB uncompressed, "
          f"{os.path.getsize(out) / 1e6:.1f} MB packed")
    print("  excluded per .gitignore and DATA_CARD.md: the raw openFDA export, the "
          "encoder embeddings, LaTeX build artifacts, and any archive in this folder")


if __name__ == "__main__":
    main()
