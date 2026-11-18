"""Every tracked projects/ritz/grammars/*.grammar has a consumer (AGAST #2265).

grammars/ritz.grammar outlived the Python parser generator that read it for
months: the only text still naming `grammars/ritz.grammar` was
examples/tier5_async/49_ritzgen, which bundles (and means) its own copy.

A consumer is a tracked, non-markdown file outside the archives that names
`grammars/<file>`, where no directory between it and projects/ritz bundles its
own `grammars/<file>` (that reference resolves to the bundled copy instead).
Runs in `make tools-unit` (`pytest tools/`).
"""

import re
import subprocess
from pathlib import Path, PurePosixPath

import pytest

pytestmark = pytest.mark.unit

RITZ = Path(__file__).resolve().parent.parent
IGNORED_PREFIXES = ("docs/archive/",)


def tracked_files(root):
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
    ).stdout.decode()
    return [f for f in out.split("\0") if f]


def bundles_own_copy(rel, name, tracked):
    """True if a directory above `rel` (below the project root) has grammars/<name>."""
    for parent in PurePosixPath(rel).parents:
        if str(parent) == ".":
            return False
        if f"{parent}/grammars/{name}" in tracked:
            return True
    return False


def unconsumed_grammars(root, files):
    tracked = set(files)
    grammars = sorted(
        f for f in files if f.startswith("grammars/") and f.endswith(".grammar")
    )
    readers = [
        f
        for f in files
        if not f.endswith(".md")
        and not f.startswith(IGNORED_PREFIXES)
        and not f.startswith("grammars/")
    ]
    texts = {}
    for f in readers:
        try:
            texts[f] = (root / f).read_text(errors="ignore")
        except (OSError, IsADirectoryError):
            continue
    orphans = []
    for g in grammars:
        name = PurePosixPath(g).name
        # Trailing boundary: `grammars/ritz.grammar.old` does not name ritz.grammar.
        ref = re.compile(re.escape(g) + r"(?![\w.])")
        if not any(
            ref.search(text) and not bundles_own_copy(f, name, tracked)
            for f, text in texts.items()
        ):
            orphans.append(g)
    return orphans


def test_every_grammar_has_a_consumer():
    assert unconsumed_grammars(RITZ, tracked_files(RITZ)) == []


def write(root, files):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return list(files)


def test_grammar_named_by_makefile_is_consumed(tmp_path):
    files = write(
        tmp_path, {"grammars/a.grammar": "", "Makefile": "gen grammars/a.grammar"}
    )
    assert unconsumed_grammars(tmp_path, files) == []


def test_reference_to_bundled_copy_does_not_count(tmp_path):
    files = write(
        tmp_path,
        {
            "grammars/a.grammar": "",
            "examples/x/grammars/a.grammar": "",
            "examples/x/test.sh": "./gen grammars/a.grammar",
        },
    )
    assert unconsumed_grammars(tmp_path, files) == ["grammars/a.grammar"]


def test_longer_name_is_not_a_reference(tmp_path):
    files = write(
        tmp_path, {"grammars/a.grammar": "", "t.py": '"grammars/a.grammar.old"'}
    )
    assert unconsumed_grammars(tmp_path, files) == ["grammars/a.grammar"]


def test_docs_and_archives_do_not_count(tmp_path):
    files = write(
        tmp_path,
        {
            "grammars/a.grammar": "",
            "README.md": "see grammars/a.grammar",
            "docs/archive/old.txt": "grammars/a.grammar",
        },
    )
    assert unconsumed_grammars(tmp_path, files) == ["grammars/a.grammar"]
