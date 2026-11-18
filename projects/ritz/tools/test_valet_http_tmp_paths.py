"""valet's and http's .ritz tests use no fixed /tmp path (AGAST #4052).

test_static_range wrote, served and unlinked "/tmp/valet_test_static_range.txt";
two valet test runs at once (gate slots on one box, compiler variants)
truncated or unlinked each other's file between the write and the serve, and
gates flaked with "7 passed, 1 failed". A test's scratch file takes the
process id: each file's pid_tmp_path builds /tmp/valet_<pid>_<name> from the
prefix "/tmp/valet_". (ritzlib.testlib's make_sandbox_path does the same, but
its pub read_file collides with ritzlib.fs's, which valet's lib.static imports.)

Scoped to valet and http, the packages #4052 swept; the rest of the tree is
a separate ticket.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PACKAGES = ("valet", "http")

# A string literal naming a path under /tmp: "/tmp/x" or c"/tmp/x". One that
# ends in "_" is a prefix a pid is appended to, not a path.
FIXED_TMP = re.compile(r'"/tmp/[^"]*[^_"]"')


def fixed_tmp_paths(root: Path, base: Path = REPO) -> list[str]:
    """`file:line: text` for every fixed /tmp literal in root's test .ritz files."""
    hits = []
    for f in sorted(root.rglob("test/**/*.ritz")):
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
        '    let head: *u8 = c"/tmp/valet_"\n')
    assert fixed_tmp_paths(tmp_path / "pkg", tmp_path) == [
        'pkg/test/test_x.ritz:3: c"/tmp/valet_x.txt"']


@pytest.mark.unit
@pytest.mark.parametrize("pkg", PACKAGES)
def test_no_fixed_tmp_path_in_tests(pkg):
    root = REPO / "projects" / pkg
    assert (root / "test").is_dir(), f"{pkg} has no test/ directory"
    hits = fixed_tmp_paths(root)
    assert not hits, ("fixed /tmp paths race concurrent test runs; put the "
                      "pid in them, as pid_tmp_path does:\n" + "\n".join(hits))
