"""Regression tests for AGAST #1367 — a bool-returning CALL used directly as a
condition must reach `br i1` as an i1.

ritz1 keeps values in a uniform i64 representation, so `emit_expr`'s EXPR_CALL
path zero-extends the callee's i1 result:

    %.1 = call i1 @yes()
    %.2 = zext i1 %.1 to i64

The condition sites (STMT_IF, STMT_WHILE, and the `and`/`or` short-circuit)
decide whether that register is *already* an i1 by asking `get_expr_type`,
which reports the function's declared return type — TYPE_BOOL. The predicate
and the actual register width disagree for exactly this one expression kind,
so the i64 is wired straight into the branch:

    br i1 %.2, label %L0, label %L2
    clang: error: '%.2' defined with type 'i64' but expected 'i1'

The same mistake is documented, for a different expression kind, one function
away: get_expr_type's OP_NOT arm returns TYPE_I64 *specifically* because `not`
lowers to `icmp + zext`, with a comment warning that returning the operand's
type "would tell STMT_IF 'already i1' and skip the i64->i1 icmp coerce, wiring
an i64 reg into `br i1 ...`". That is a verbatim description of this bug.

This is a hard compile-time failure, not a wrong answer — clang rejects the
module — so unlike #1361 there is no risk of it passing silently. It survived
because no example among the 57 that ritz1 accepts writes `if f()` with a
bool-returning f; the corpus uses `-> i32` predicates or explicit comparisons.
It became reachable only when tier5_async_52_uring came off the ritz0
known-failure list, because ritz0 had been rejecting that example first.

Both directions are pinned:

  * the broken forms must compile, link, run, and agree with ritz0, and
  * the forms that ALREADY worked must keep working. That second half is not
    padding. The obvious fix — copy `assert`'s narrower predicate, which tests
    `TYPE_BOOL and kind == EXPR_IDENT` and is why `assert f()` is the one site
    that never broke — would emit `icmp ne i64 %i1reg, 0` for a bool STRUCT
    FIELD, whose register genuinely is an i1. That trades this bug for a new
    one, so the working forms are asserted here to catch exactly that.

Assertions are on the runtime exit code, not on IR text: an IR-shape check
would be satisfied by any emitter that merely emits an `icmp` somewhere.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file — see the long note in
# test_ritz1_ptr_arith_chain.py. Asserting it exists passes on any machine
# that has ever built and fails on a fresh checkout, which is how it broke
# main CI once already (run ebb5a48). So build it and let make decide.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date; make's dependency graph decides the work.

    A stale ritz1 asserts nothing just as effectively as a missing one, and
    this file's whole purpose is to detect a change in ritz1's emitter.
    """
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", "ritz1", "ritz1"],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0 or not RITZ1_BIN.exists():
        pytest.fail(
            "could not build ritz1 for the bool-condition regression tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


def _build_runtime_start() -> None:
    proc = subprocess.run(
        ["make", "-C", "runtime", RITZ_START.name],
        cwd=RITZ_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0 or not RITZ_START.exists():
        pytest.fail(
            f"could not build the runtime start object {RITZ_START}:\n"
            f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
        )


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    _build_ritz1()
    _build_runtime_start()
    return RITZ1_BIN


# --- the forms that #1367 breaks -------------------------------------------
# Each returns 7 when the condition is evaluated correctly and 3 otherwise, so
# a branch that inverts rather than fails is caught too.

IF_CALL = """\
fn yes() -> bool
    return true

fn main() -> i32
    if yes()
        return 7
    return 3
"""

WHILE_CALL = """\
fn once() -> bool
    return g < 1

var g: i64 = 0

fn main() -> i32
    while once()
        g = g + 1
    return (6 + g) as i32
"""

IF_CALL_AND_CALL = """\
fn yes() -> bool
    return true

fn no() -> bool
    return false

fn main() -> i32
    if yes() and no()
        return 3
    if yes() and yes()
        return 7
    return 3
"""

# --- the forms that already worked, pinned against an over-narrow fix ------

IF_BOOL_IDENT = """\
fn main() -> i32
    let b: bool = true
    if b
        return 7
    return 3
"""

IF_BOOL_FIELD = """\
struct S
    flag: bool

fn main() -> i32
    var s: S
    s.flag = true
    if s.flag
        return 7
    return 3
"""

# Dereferencing a *bool. get_expr_type reports the pointee (TYPE_BOOL) while
# the load leaves an i64, so this leaks the same way a call does. Found by
# sweeping the condition forms rather than by reading the emitter — a fix
# scoped to EXPR_CALL alone would have left it broken.
IF_DEREF_BOOL = """\
fn main() -> i32
    var b: bool = true
    let p: *bool = @b
    if *p
        return 7
    return 3
"""

# `b and c` on two bool IDENTIFIERS already works, and it is here to keep the
# fix honest: get_expr_type delegates EXPR_BINARY to its left operand, so the
# temptation is to treat every logical binary as needing coercion. That would
# break this case. Predicted broken, measured working — pinned as working.
IF_BOOL_IDENT_AND = """\
fn main() -> i32
    let b: bool = true
    let c: bool = true
    if b and c
        return 7
    return 3
"""

IF_BOOL_INDEX = """\
fn main() -> i32
    var a: [2]bool
    a[0] = true
    if a[0]
        return 7
    return 3
"""

BROKEN_FORMS = {
    "if_call": IF_CALL,
    "while_call": WHILE_CALL,
    "if_call_and_call": IF_CALL_AND_CALL,
    "if_deref_bool": IF_DEREF_BOOL,
}

WORKING_FORMS = {
    "if_bool_ident": IF_BOOL_IDENT,
    "if_bool_field": IF_BOOL_FIELD,
    "if_bool_ident_and": IF_BOOL_IDENT_AND,
    "if_bool_index": IF_BOOL_INDEX,
}


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))

    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    comp = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )

    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    # This is where #1367 lands: the module is rejected as invalid IR, naming
    # the branch operand. Surface that message rather than a bare exit code.
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n"
        f"{link.stderr[-2000:]}"
    )

    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BROKEN_FORMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, BROKEN_FORMS[name]) == 7


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BROKEN_FORMS))
def test_ritz1_bool_returning_call_as_condition(ritz1_bin, tmp_path, name):
    """AGAST #1367. Before the fix each of these emitted `br i1 <i64 reg>` and
    clang rejected the module outright."""
    assert _run("ritz1", tmp_path, name, BROKEN_FORMS[name]) == 7


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING_FORMS))
def test_ritz1_already_working_condition_forms(ritz1_bin, tmp_path, name):
    """These reach `br` as a genuine i1 today.

    A fix that coerces them anyway would emit `icmp ne i64 %i1reg, 0` and fail
    to link — so this asserts the fix did not simply move the bug.
    """
    assert _run("ritz1", tmp_path, name, WORKING_FORMS[name]) == 7


@pytest.mark.integration
def test_ritz0_and_ritz1_agree_on_if_call(ritz1_bin, tmp_path):
    """Parity, stated directly, for the headline form."""
    r0 = _run("ritz0", tmp_path, "parity", IF_CALL)
    r1 = _run("ritz1", tmp_path, "parity", IF_CALL)
    assert r0 == r1, f"ritz0 returned {r0}, ritz1 returned {r1} for `if yes()`"
