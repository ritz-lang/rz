"""Free counts for the ownership model in LANGUAGE_SPEC §13 (AGAST #2156, #1854).

#1854 decided the model (option (a)): a type is move-only iff it implements
`Drop` or contains a move-only field; every other type copies. The compiler
drops an owned binding at the end of its block, before `return`, on
`break`/`continue` and before reassigning it, in reverse declaration order,
and never drops a moved-from binding.

Every program below uses one instrumented `Drop` type, `Tracked`, whose
`drop` bumps a global counter (`DROPS`) and appends its id to a second one
(`ORDER`). The program's exit status encodes the counts it observed. The
expected statuses come from the spec, not from what a compiler does today.

Today's gaps are strict xfails, so the room that closes one has to flip it:
  * ritz0: AGAST #2157 (block-scope drops, `let` drops, reassignment, the
    double drop of an argument moved into a callee, field drop glue, and
    "plain structs copy");
  * ritz1 / ritz1_selfhosted: none since AGAST #2158 (ritz1/src/ownership.ritz).
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
RITZ1S = ("ritz1", "ritz1_selfhosted")

PRELUDE = """\
trait Drop
    fn drop(self: @&Self)

var DROPS: i32 = 0
var ORDER: i32 = 0

struct Tracked
    id: i32

impl Drop for Tracked
    fn drop(self: @&Tracked)
        DROPS = DROPS + 1
        ORDER = ORDER * 10 + self.id

# Move-only without a Drop impl of its own: it has a Tracked field.
struct Holder
    t: Tracked
    n: i32

# No Drop anywhere inside: copies.
struct Plain
    x: i32
    y: i32

fn make(id: i32) -> Tracked
    return Tracked { id: id }

# A by-value parameter of a move-only type takes ownership.
fn consume(t: Tracked) -> i32
    return t.id

"""

# name -> (program body, expected exit status, {compiler: gap ticket}).
# Where a helper returns `DROPS * 10`, the tens digit is the count at that
# point inside the helper and the units digit the count once it has returned.
CASES = {
    "scope_end_let": ("""\
fn f()
    let t = make(1)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {"ritz0": 2157}),

    "scope_end_var": ("""\
fn f()
    var t = make(1)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # Dropped when the `if` body ends, not when f does.
    "nested_block_end": ("""\
fn f() -> i32
    if DROPS == 0
        var t = make(1)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {"ritz0": 2157}),

    # Once per call, on either path.
    "early_return": ("""\
fn f(x: i32) -> i32
    var t = make(1)
    if x > 0
        return 7
    return 9

pub fn main() -> i32
    f(1)
    f(0)
    return DROPS
""", 2, {}),

    # Iterations 0 and 1 drop at the end of the body; iteration 2 on `break`.
    "break": ("""\
fn f()
    var i = 0
    while i < 5
        var t = make(i)
        if i == 2
            break
        i = i + 1

pub fn main() -> i32
    f()
    return DROPS
""", 3, {"ritz0": 2157}),

    # Four iterations, two of which leave by `continue`.
    "continue": ("""\
fn f()
    var i = 0
    while i < 4
        i = i + 1
        var t = make(i)
        if i % 2 == 0
            continue

pub fn main() -> i32
    f()
    return DROPS
""", 4, {"ritz0": 2157}),

    # The old value is dropped by the assignment, the new one at scope end.
    "reassignment": ("""\
fn f() -> i32
    var t = make(1)
    t = make(2)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 12, {"ritz0": 2157}),

    # consume() owns and drops it; f must not drop it again (ritz0: 12).
    "move_into_callee": ("""\
fn f() -> i32
    var t = make(1)
    consume(t)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {"ritz0": 2157}),

    # build() moves t out: not dropped there, dropped once by f's scope.
    "move_out_by_return": ("""\
fn build() -> Tracked
    var t = make(1)
    return t

fn f() -> i32
    var u = build()
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 1, {}),

    # Plain copies: `a` stays usable after every copy, and nothing drops.
    "plain_struct_copy": ("""\
fn take(p: Plain) -> i32
    return p.x

fn f() -> i32
    let a = Plain { x: 3, y: 4 }
    let b = a
    let c = a
    return take(a) + take(a) + a.x + b.x + c.y

pub fn main() -> i32
    let n = f()
    return n + DROPS
""", 16, {"ritz0": 2157}),

    # Reverse declaration order: 3, 2, 1.
    "drop_order": ("""\
fn f()
    var a = make(1)
    var b = make(2)
    var c = make(3)

pub fn main() -> i32
    f()
    return ORDER - 300
""", 21, {}),

    # Holder has no Drop impl; dropping it drops its Tracked field.
    "field_drop_glue": ("""\
fn f()
    var h = Holder { t: make(4), n: 1 }

pub fn main() -> i32
    f()
    return ORDER
""", 4, {"ritz0": 2157}),
}

# name -> (program body, binding named in the diagnostic, {compiler: gap}).
USE_AFTER_MOVE = {
    "after_move_into_callee": ("""\
pub fn main() -> i32
    var t = make(1)
    consume(t)
    return t.id
""", "t", {}),

    "after_move_by_binding": ("""\
pub fn main() -> i32
    var t = make(1)
    var u = t
    return t.id
""", "t", {}),

    # Move-only through its field.
    "holder_after_move": ("""\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 2 }
    var g = h
    return h.n
""", "h", {}),
}


def _params(table):
    out = []
    for name in sorted(table):
        gaps = table[name][-1]
        for compiler in COMPILERS:
            marks = []
            if compiler in gaps:
                marks.append(pytest.mark.xfail(
                    strict=True,
                    reason=f"AGAST #{gaps[compiler]}: {compiler} does not "
                           f"implement this part of LANGUAGE_SPEC §13 yet"))
            out.append(pytest.param(compiler, name, marks=marks,
                                    id=f"{compiler}-{name}"))
    return out


def _compile(compiler, src, ll, cwd):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=cwd, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=300)


def _write(tmp_path, body):
    src = tmp_path / "main.ritz"
    src.write_text(PRELUDE + body)
    return src


@pytest.mark.integration
@pytest.mark.parametrize("compiler,name", _params(CASES))
def test_free_count(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    body, expected, _ = CASES[name]
    src = _write(tmp_path, body)
    ll = tmp_path / "main.ll"
    comp = _compile(compiler, src, ll, tmp_path)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-2000:]}"
    rc = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    assert rc == expected, f"{compiler} {name}: exit {rc}, spec says {expected}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler,name", _params(USE_AFTER_MOVE))
def test_use_after_move_rejected(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    body, var, _ = USE_AFTER_MOVE[name]
    src = _write(tmp_path, body)
    ll = tmp_path / "main.ll"
    comp = _compile(compiler, src, ll, tmp_path)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted a use after move:\n{out[-1000:]}"
    assert "Traceback" not in out, out[-2000:]
    assert f"use of moved value: `{var}`" in out, out[-2000:]
