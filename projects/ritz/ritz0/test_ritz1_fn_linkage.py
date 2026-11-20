"""AGAST #3386 (LARB R45): ritz1's fn linkage follows visibility.

ritz1 emitted every non-generic fn `weak_odr` (#194). That tells the linker
every definition of the name is the same, so two modules' *private*
`fn helper()` with different bodies were merged into one, and one module
silently called the other's body.

The rule: a private *free* fn is an external `define` whose symbol carries its
defining file's hash (`priv_fn__1a2b3c4d`, #1858/#4356), a `pub fn` an external
`define`, `main` external, a monomorph (`$` in its name) `linkonce_odr`. An
inherent impl method stays `internal` (it can only be called through its
type's module); a trait impl's methods are external. Only the module that
declares the impl defines them.

§15.3 refuses one import closure holding two `fn helper`, so the runtime test
links two modules that never import each other: main imports `a` and reaches
`b`'s `pub fn b_val` by a declaration (`= extern`, §5.3).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

A = """\
fn helper() -> i32
    1

pub fn a_val() -> i32
    helper()
"""

B = """\
fn helper() -> i32
    2

pub fn b_val() -> i32
    helper()
"""

MAIN = """\
import a

pub fn b_val() -> i32 = extern

fn main() -> i32
    a_val() * 10 + b_val()
"""

# One module covering each linkage row: private / pub free fn, a monomorph,
# private / pub impl methods, and main.
LINKAGE = """\
struct P
    x: i32

struct D
    y: i32

impl Drop for D
    fn drop(self: @&D)
        self.y = 0

impl P
    fn priv_m(self: @P) -> i32
        self.x

    pub fn pub_m(self: @P) -> i32
        self.priv_m()

fn ident<T>(v: T) -> T
    v

fn priv_fn() -> i32
    3

pub fn pub_fn() -> i32
    priv_fn()

fn main() -> i32
    var d = D { y: 1 }
    let p = P { x: 4 }
    ident<i32>(pub_fn()) + p.pub_m()
"""


def _compile(cwd: Path, name: str, text: str) -> Path:
    src = cwd / f"{name}.ritz"
    src.write_text(text)
    ll = cwd / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(cwd)],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=300,
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz1 failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return ll


def _link_run(cwd: Path, lls: list) -> int:
    exe = cwd / "prog"
    cmd = ["clang", str(RITZ_START), *map(str, lls), "-o", str(exe), "-nostdlib"]
    link = fast_link.clang(cmd, cwd=cwd, capture_output=True, text=True)
    assert link.returncode == 0, f"IR would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _define_line(ir: str, symbol: str) -> str:
    # A private free fn's symbol carries its file's hash (#4356).
    m = re.search(rf"^define [^\n]*@{re.escape(symbol)}(?:__[0-9a-f]{{8}})?\(",
                  ir, re.M)
    assert m, f"no definition of @{symbol} in:\n{ir[:3000]}"
    return m.group(0)


@pytest.mark.integration
def test_ritz1_private_fns_of_two_modules_stay_apart(ritz1_bin, tmp_path):
    """Each module calls its own `helper`: 1*10 + 2. Under weak_odr: 11 or 22."""
    lls = [_compile(tmp_path, n, t) for n, t in (("a", A), ("b", B), ("main", MAIN))]
    assert _link_run(tmp_path, lls) == 12


# (symbol, linkage prefix of its `define` line)
ROWS = {
    "private_fn": ("priv_fn", "define i32 "),
    "pub_fn": ("pub_fn", "define i32 "),
    "main": ("main", "define i32 "),
    "monomorph": ("ident$i32", "define linkonce_odr "),
    "private_method": ("P_priv_m", "define internal "),
    "pub_method": ("P_pub_m", "define i32 "),
    # A trait impl's method is reached through the trait, wherever the
    # compiler inserts the call (a `Drop` value dropped in another module),
    # so it is external with or without `pub`.
    "trait_method": ("D_drop", "define void "),
}


@pytest.fixture(scope="module")
def linkage_ir(tmp_path_factory, ritz1_bin):
    d = tmp_path_factory.mktemp("linkage")
    ll = _compile(d, "linkage", LINKAGE)
    assert _link_run(d, [ll]) == 7, "the program itself must still run"
    return ll.read_text()


@pytest.mark.integration
@pytest.mark.parametrize("row", sorted(ROWS))
def test_ritz1_linkage_follows_visibility(linkage_ir, row):
    symbol, prefix = ROWS[row]
    line = _define_line(linkage_ir, symbol)
    assert "weak_odr" not in line, line
    assert line.startswith(prefix), f"{row}: expected {prefix!r}, got {line!r}"
