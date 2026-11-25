"""No test .ritz file in the tree uses a fixed /tmp path (AGAST #4052, #4084).

valet's test_static_range wrote, served and unlinked
"/tmp/valet_test_static_range.txt"; two valet test runs at once (gate slots on
one box, compiler variants) truncated or unlinked each other's file between
the write and the serve, and gates flaked with "7 passed, 1 failed". A test's
scratch path takes the process id instead: ritzlib.testlib's
sandbox_path builds /tmp/ritz_<prefix>_<pid>_<suffix>, and a file whose
imports collided with testlib's old pub read_file (AGAST #4643 deleted it in
favour of ritzlib.fs's) keeps a local pid_tmp_path built from a prefix such
as "/tmp/valet_", or interpolates it: format_into(@&s, "/tmp/m7m_{pid}_db")
(AGAST #4685 moved the hand-rolled digit appenders to `{pid}`).

#4052 swept valet and http; #4084 swept the rest of projects/ and widened this
check to every .ritz file under a test/ or tests/ directory. A test that only
manipulates a path string, never the filesystem, names a directory other than
/tmp so the check stays a plain grep.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PROJECTS = REPO / "projects"

# A string literal naming a path under /tmp: "/tmp/x" or c"/tmp/x". One that
# ends in "_" or "-" is a prefix a pid is appended to, not a path, and one
# that interpolates `{pid}` carries it.
FIXED_TMP = re.compile(r'"/tmp/(?![^"]*\{pid\})[^"]*[^_\-"]"')


def ritz_test_files(root: Path) -> list[Path]:
    """Every .ritz file under a test/ or tests/ directory below root."""
    return sorted(f for f in root.rglob("*.ritz")
                  if {"test", "tests"} & set(f.relative_to(root).parts[:-1]))


def fixed_tmp_paths(root: Path, base: Path = REPO) -> list[str]:
    """`file:line: text` for every fixed /tmp literal in root's test .ritz files."""
    hits = []
    for f in ritz_test_files(root):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            code = line.split("#", 1)[0]  # a comment may name the old path
            if FIXED_TMP.search(code):
                hits.append(f"{f.relative_to(base)}:{n}: {line.strip()}")
    return hits


@pytest.mark.unit
def test_the_check_finds_a_fixed_tmp_path(tmp_path):
    t = tmp_path / "pkg" / "test"
    t.mkdir(parents=True)
    (t / "test_x.ritz").write_text(
        '# was c"/tmp/old"\nfn f() -> *u8\n    c"/tmp/valet_x.txt"\n'
        '    let head: *u8 = c"/tmp/valet_"\n'
        '    let dash: StrView = "/tmp/goliath-fs-"\n'
        '    format_into(@&s, "/tmp/m7m_{pid}_{seq}_wal")\n'
        '    format_into(@&s, "/tmp/m7m_{seq}_wal")\n')
    assert fixed_tmp_paths(tmp_path / "pkg", tmp_path) == [
        'pkg/test/test_x.ritz:3: c"/tmp/valet_x.txt"',
        'pkg/test/test_x.ritz:7: format_into(@&s, "/tmp/m7m_{seq}_wal")']


@pytest.mark.unit
def test_the_check_reads_tests_dirs_and_skips_non_test_files(tmp_path):
    nested = tmp_path / "pkg" / "lib" / "tests"
    nested.mkdir(parents=True)
    (nested / "test_y.ritz").write_text('    "/tmp/y.tmp"\n')
    (tmp_path / "pkg" / "lib" / "y.ritz").write_text('    "/tmp/lib_y"\n')
    (tmp_path / "pkg" / "test_z.ritz").write_text('    "/tmp/z"\n')
    assert fixed_tmp_paths(tmp_path, tmp_path) == [
        'pkg/lib/tests/test_y.ritz:1: "/tmp/y.tmp"']


@pytest.mark.unit
def test_the_check_sees_the_whole_tree():
    # valet and http (#4052) and the packages #4084 swept are all in scope.
    seen = {f.relative_to(PROJECTS).parts[0] for f in ritz_test_files(PROJECTS)}
    assert {"valet", "http", "ritz", "zeus", "mausoleum", "goliath"} <= seen
    assert any(f.parent.name == "tests" for f in ritz_test_files(PROJECTS))


@pytest.mark.unit
def test_no_fixed_tmp_path_in_tests():
    hits = fixed_tmp_paths(PROJECTS)
    assert not hits, ("fixed /tmp paths race concurrent test runs; put the "
                      "pid in them (ritzlib.testlib sandbox_path, or a "
                      "local pid_tmp_path):\n" + "\n".join(hits))
