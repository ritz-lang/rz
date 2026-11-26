"""AGAST #4839: a pub generic's instance calls its module's private methods
from another module's object, so ritz1 makes them external there.

A generic is instantiated in the object that uses it (`fill$Three` in the
test's), and its body calls what it names in its own module: `b.add(..)`, a
private `Box.add`.  ritz1 defined every private inherent method `internal`
(AGAST #3386), so the importer's call had nothing to bind to and linking
failed; ritz0's `--no-runtime` object defines it external.  A private *free*
fn was already external, under its file's symbol (#4356).

Now a module exporting a generic body (a `pub fn f<T>`, or a pub method of
an `impl<T>`) defines its private methods external.  One
that exports none keeps them internal: test_ritz1_fn_linkage.py's
`private_method` row, and `no_generic_keeps_internal` here.

Each library is compiled on its own and linked with main, as `rz test` links a
test file against the package's objects.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
BINS = {"ritz1": RITZ_ROOT / "ritz1" / "build" / "ritz1",
        "ritz1_selfhosted": RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"}

LIB_HEAD = """\
pub trait Src
    fn n(self: @Self) -> i64

pub struct Box
    v: i64

impl Box
    fn add(self: @&Box, x: i64)      # private: only a generic calls it
        self.v = self.v + x
"""

THREE = """\
struct Three
    pad: i64

impl Src for Three
    fn n(self: @Three) -> i64
        3
"""

# name -> (the library's generic, main's import, main's body, exit status)
ROWS = {
    # The ticket's repro: a pub generic fn calls a private method.
    "generic_fn_private_method": ("""
pub fn fill<S: Src>(b: @&Box, s: @S)
    b.add(s.n())
""", "Src, Box, fill", """\
    var b = Box { v: 1 }
    let t = Three { pad: 0 }
    fill(@&b, @t)
    b.v as i32
""", 4),
    # A private free fn: external under its file's symbol since #4356.
    "generic_fn_private_free_fn": ("""
fn twice(x: i64) -> i64
    x * 2

pub fn fill<S: Src>(b: @&Box, s: @S)
    b.v = b.v + twice(s.n())
""", "Src, Box, fill", """\
    var b = Box { v: 1 }
    let t = Three { pad: 0 }
    fill(@&b, @t)
    b.v as i32
""", 7),
    # A pub method of a generic impl.
    "generic_impl_method_private_method": ("""
pub struct Filler<S>
    s: S

impl<S: Src> Filler<S>
    pub fn fill(self: @Filler<S>, b: @&Box)
        b.add(self.s.n() * 3)
""", "Src, Box, Filler", """\
    var b = Box { v: 1 }
    let f = Filler<Three> { s: Three { pad: 0 } }
    f.fill(@&b)
    b.v as i32
""", 10),
}


def _compile(binary: Path, cwd: Path, name: str, text: str) -> Path:
    src = cwd / f"{name}.ritz"
    src.write_text(text)
    ll = cwd / f"{name}.ll"
    comp = subprocess.run(
        [str(binary), str(src), "-o", str(ll), "-I", str(cwd)],
        cwd=cwd, env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True, text=True, timeout=300,
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"{binary.name} failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
    return ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", sorted(BINS))
@pytest.mark.parametrize("row", sorted(ROWS))
def test_pub_generic_reaches_private_callee(ritz1_bin, tmp_path, row, compiler):
    generic, names, body, want = ROWS[row]
    binary = BINS[compiler]
    lib = _compile(binary, tmp_path, "a", LIB_HEAD + generic)
    main = _compile(binary, tmp_path, "main",
                    f"import a {{ {names} }}\n\n{THREE}\nfn main() -> i32\n{body}")
    exe = tmp_path / "prog"
    link = fast_link.clang(["clang", str(RITZ_START), str(lib), str(main), "-o", str(exe), "-nostdlib"],
                           cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{row}: would not link:\n{link.stderr[-2000:]}"
    assert subprocess.run([str(exe)], capture_output=True, timeout=60).returncode == want


@pytest.mark.integration
@pytest.mark.parametrize("compiler", sorted(BINS))
def test_no_generic_keeps_internal(ritz1_bin, tmp_path, compiler):
    """A module exporting no generic still defines its private methods
    internal: two modules' private `Box.add` can't meet at link."""
    ll = _compile(BINS[compiler], tmp_path, "a", LIB_HEAD + """
pub fn bump(b: @&Box)
    b.add(1)
""")
    line = re.search(r"^define [^\n]*@Box_add\(", ll.read_text(), re.M)
    assert line and line.group(0).startswith("define internal "), line
