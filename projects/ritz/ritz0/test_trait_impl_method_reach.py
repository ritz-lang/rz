"""AGAST #201: a trait impl's methods need no `pub` (LANGUAGE_SPEC §15.2).

They are reachable wherever the trait is. ritzlib.fmt's generics are the
first real users: `fmt_show<T>` in ritzlib/fmt/display.ritz calls the
`show` of a user's `impl Display for Point`, from another file.

    # shape.ritz                     # main.ritz
    pub trait Area                   struct Sq
        fn area(self: @Self) -> i64      s: i64
                                     impl Area for Sq
    pub fn total<T>(v: @T) -> i64        fn area(self: @Sq) -> i64   # no pub
        v.area()                             ...

Before: ritz0 refused the instance's call ("`Sq.area` is private to
main.ritz; mark it `pub` (#3413)") and ritz1 the same, and a ritz1 package
build gave the method internal linkage, so the other file's object could
not link against it. Both compilers now mark a trait impl's methods `pub`
at the parse (ritz0 parser.parse_impl, ritz1 ast_helpers.impl_block_new).

A package build, so each file is its own object as in a real program.
"""

import os
import subprocess
from pathlib import Path

import pytest

from test_ref_into_value import COMPILERS

pytestmark = [pytest.mark.xdist_group("tree"), pytest.mark.integration]

RITZ_ROOT = Path(__file__).resolve().parent.parent

SHAPE = """\
pub trait Area
    fn area(self: @Self) -> i64

pub fn total<T>(a: @T, b: @T) -> i64
    a.area() + b.area()
"""

MAIN = """\
import shape

struct Sq
    s: i64

impl Area for Sq
    fn area(self: @Sq) -> i64
        self.s * self.s

pub fn main() -> i32
    let a = Sq { s: 2 }
    let b = Sq { s: 3 }
    total(@a, @b) as i32
"""

# The inherent method stays private: only a trait impl's are reachable.
MAIN_INHERENT = MAIN.replace("impl Area for Sq", "impl Sq")


def _build(pkg: Path, compiler: str, main: str):
    (pkg / "src").mkdir(parents=True)
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "reach"\nversion = "0.1.0"\n\n'
        '[[bin]]\nname = "reach"\npath = "src/main.ritz"\n')
    (pkg / "src" / "shape.ritz").write_text(SHAPE)
    (pkg / "src" / "main.ritz").write_text(main)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["python3", str(RITZ_ROOT / "build.py"), "build", str(pkg), "--no-cache",
         "--compiler", compiler],
        cwd=pkg, env=env, capture_output=True, text=True, timeout=600)
    return proc, pkg / "build" / "debug" / "reach"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_generic_in_another_file_calls_a_trait_impl_method(tmp_path, compiler):
    proc, exe = _build(tmp_path / "pkg", compiler, MAIN)
    assert proc.returncode == 0 and exe.exists(), proc.stdout[-3000:] + proc.stderr[-3000:]
    assert subprocess.run([str(exe)], timeout=60).returncode == 13


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_inherent_method_stays_private(tmp_path, compiler):
    proc, exe = _build(tmp_path / "pkg", compiler, MAIN_INHERENT)
    assert proc.returncode != 0
    assert "`Sq.area` is private to main.ritz; mark it `pub` (#3413)" in proc.stdout + proc.stderr
