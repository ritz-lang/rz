"""Regression tests for AGAST #1599: ritz1 must parse the address of a
dereference, `@*e` and `@&*e`:

    fn tab_history_go_back(history:& TabHistory) -> Option<HistoryEntry>
        if tab_history_can_go_back(@*history) == 0

ritz1's `addr_expr` was `AT AMP addr_expr | AT addr_expr | postfix_expr`. A
deref is a unary, not a postfix, so `@*history` failed to parse and the item
anchor-skip reported

    cannot parse item starting at 'fn tab_history_go_back'

which is how tempest's lib/history.ritz:72/81 died under ritz1. The fix adds
`AT STAR unary_expr` and `AT AMP STAR unary_expr` and keeps the AST as
OP_ADDR(OP_DEREF e). That way the call-argument coercions that already apply to
`@x` (by-value struct param, `@T` param) apply to `@*e` too. The emitter's
lvalue-address helper gains a deref case, and the address of `*e` is `e` itself.

Until #2045 ritz0 was not a reliable oracle for this construct: its
address-of fell through to "emit the operand", so `@*p` evaluated to the
*loaded value* `*p`, not to `p`. Writes through `@&*p` hit a copy,
`let q: *i32 = @*p` segfaulted, and on a `h:& T` borrow `*h` crashed the
emitter. The SPEC programs now pin both compilers to the right answer.

Every program returns 3 on success.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
# Build product, not a tracked file; see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


# --- programs ritz0 gets right (it is the oracle) ------------------------------

# `@*p` for `p: *H` into a `*H` param.
PTR_TO_PTR_PARAM = """\
struct H
    i: i32
fn f(h: *H) -> i32
    return h.i
pub fn main() -> i32
    var x: H = H { i: 3 }
    let p: *H = @x
    return f(@*p)
"""

# `@*h` for `h: *H` into a by-value `H` param (the tempest call shape, through
# a raw pointer, which ritz0 can compile).
PTR_TO_VALUE_PARAM = """\
struct H
    i: i32
fn f(h: H) -> i32
    return h.i
fn g(h: *H) -> i32
    return f(@*h)
pub fn main() -> i32
    var x: H = H { i: 3 }
    return g(@x)
"""

ORACLE = {
    "ptr_to_ptr_param": PTR_TO_PTR_PARAM,
    "ptr_to_value_param": PTR_TO_VALUE_PARAM,
}

# --- programs ritz0 gets wrong (#2045); the expected answer is the spec --------

# The ticket's repro, verbatim: a `:&` borrow re-borrowed as `@H`.
REPRO = """\
struct H
    i: i32
fn f(h: @H) -> i32
    return h.i
fn g(h:& H) -> i32
    return f(@*h)
pub fn main() -> i32
    var x: H = H { i: 3 }
    return g(@&x)
"""

# tempest lib/history.ritz:72 exactly: `:&` borrow, by-value param, the call
# in an `if` condition, then a write through the borrow.
TEMPEST = """\
struct TabHistory
    current_index: i32

fn tab_history_can_go_back(history: TabHistory) -> i32
    if history.current_index > 0
        return 1
    return 0

fn tab_history_go_back(history:& TabHistory) -> i32
    if tab_history_can_go_back(@*history) == 0
        return 100
    history.current_index = history.current_index - 1
    return history.current_index

pub fn main() -> i32
    var h: TabHistory = TabHistory { current_index: 4 }
    return tab_history_go_back(@&h)
"""

# `@&*h` re-borrows mutably: the write must land in the caller's struct,
# not in a copy. 2 -> 3.
REBORROW_MUT = """\
struct H
    i: i32
fn bump(h:& H)
    h.i = h.i + 1
fn g(h:& H) -> i32
    bump(@&*h)
    return h.i
pub fn main() -> i32
    var x: H = H { i: 2 }
    return g(@&x)
"""

# `@&*p` through a raw pointer; same: 2 -> 3 in x itself.
WRITE_THROUGH = """\
struct H
    i: i32
fn bump(h: *H)
    h.i = h.i + 1
pub fn main() -> i32
    var x: H = H { i: 2 }
    let p: *H = @x
    bump(@&*p)
    return x.i
"""

# `@*p` IS `p`: usable as a pointer, and equal to it.
IDENTITY = """\
pub fn main() -> i32
    var x: i32 = 3
    let p: *i32 = @x
    let q: *i32 = @*p
    if q != p
        return 100
    return *q
"""

# Nested: `@**pp` is `*pp`, i.e. p.
DOUBLE_DEREF = """\
pub fn main() -> i32
    var x: i32 = 3
    var p: *i32 = @x
    let pp: **i32 = @p
    let q: *i32 = @**pp
    return *q
"""

# A `:&` borrow of a pointer reads as that pointer: `@*p` is p's value.
BORROWED_PTR = """\
fn g(p:& *i32) -> *i32
    return @*p
pub fn main() -> i32
    var x: i32 = 3
    var p: *i32 = @x
    let q: *i32 = g(@&p)
    return *q
"""

# #2075: the rest of a pointer borrow reads as the pointer too: `p` is the
# `*i32`, `*p` is the i32, and `p = q` re-points the caller's variable.
BORROWED_PTR_READS = """\
fn val(p:& *i32) -> *i32
    return p
fn get(p:& *i32) -> i32
    return *p
pub fn main() -> i32
    var x: i32 = 3
    var p: *i32 = @x
    if val(@&p) != @x
        return 100
    return get(@&p)
"""

BORROWED_PTR_WRITE = """\
fn repoint(p:& *i32, q: *i32)
    p = q
pub fn main() -> i32
    var x: i32 = 7
    var y: i32 = 3
    var p: *i32 = @x
    repoint(@&p, @y)
    return *p
"""

# A borrowed struct pointer: field access and `@*p` go through the pointer.
BORROWED_STRUCT_PTR = """\
struct H
    i: i32
fn f(h: *H) -> i32
    return h.i
fn g(p:& *H) -> i32
    if f(@*p) != p.i
        return 100
    return p.i
pub fn main() -> i32
    var x: H = H { i: 3 }
    var p: *H = @x
    return g(@&p)
"""

# `*h` on a `:&` borrow is the referent; reading it is a plain value.
BORROW_DEREF_VALUE = """\
struct H
    i: i32
fn g(h:& H) -> i32
    let v: H = *h
    return v.i
pub fn main() -> i32
    var x: H = H { i: 3 }
    return g(@&x)
"""

SPEC = {
    "borrowed_ptr": BORROWED_PTR,
    "borrowed_ptr_reads": BORROWED_PTR_READS,
    "borrowed_ptr_write": BORROWED_PTR_WRITE,
    "borrowed_struct_ptr": BORROWED_STRUCT_PTR,
    "borrow_deref_value": BORROW_DEREF_VALUE,
    "repro": REPRO,
    "tempest": TEMPEST,
    "reborrow_mut": REBORROW_MUT,
    "write_through": WRITE_THROUGH,
    "identity": IDENTITY,
    "double_deref": DOUBLE_DEREF,
}

# Malformed address-of-deref must still be rejected.
MALFORMED = {
    "addr_deref_no_operand": """\
pub fn main() -> i32
    var x: i32 = 3
    let p: *i32 = @*
    return 3
""",
    "addr_mut_deref_no_operand": """\
pub fn main() -> i32
    var x: i32 = 3
    let p: *i32 = @&*
    return 3
""",
}


def _compile(compiler: str, ritz1_bin, tmp_path: Path, name: str, program: str):
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(program)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=work, env=env, timeout=300)
    else:
        cmd = [str(ritz1_bin), str(src), "-o", str(ll)]
        comp = subprocess.run(
            cmd, cwd=work, env=env, capture_output=True, text=True, timeout=300
        )
    return comp, ll, work


def _run(compiler: str, ritz1_bin, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link, run, return the exit code."""
    comp, ll, work = _compile(compiler, ritz1_bin, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = work / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ORACLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", None, tmp_path, name, ORACLE[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ORACLE))
def test_ritz1_addr_of_deref_matches_ritz0(ritz1_bin, tmp_path, name):
    """AGAST #1599. Before the fix these died with `cannot parse item`."""
    assert _run("ritz1", ritz1_bin, tmp_path, name, ORACLE[name]) == 3


# ritz1 cases still wrong; strict so the fix has to remove them.
RITZ1_XFAIL: dict[str, str] = {}


@pytest.mark.integration
@pytest.mark.parametrize("name", [
    pytest.param(n, marks=pytest.mark.xfail(strict=True, reason=RITZ1_XFAIL[n]))
    if n in RITZ1_XFAIL else n
    for n in sorted(SPEC)
])
def test_ritz1_addr_of_deref(ritz1_bin, tmp_path, name):
    """AGAST #1599: `@*e` / `@&*e` is the pointer `e` itself."""
    assert _run("ritz1", ritz1_bin, tmp_path, name, SPEC[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(SPEC))
def test_ritz0_addr_of_deref(tmp_path, name):
    """AGAST #2045: ritz0 lowers `@*e` / `@&*e` to `e`, not to a copy of `*e`."""
    assert _run("ritz0", None, tmp_path, name, SPEC[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_ritz1_rejects_malformed_addr_of_deref(ritz1_bin, tmp_path, name):
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, name, MALFORMED[name])
    assert comp.returncode != 0, (
        f"ritz1 accepted malformed {name!r}:\n{comp.stdout[-1000:]}"
    )
    assert not ll.exists(), f"ritz1 wrote an artifact for malformed {name!r}"
