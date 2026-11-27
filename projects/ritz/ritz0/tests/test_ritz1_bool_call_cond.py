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
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file — see the long note in
# test_ritz1_ptr_arith_chain.py. Asserting it exists passes on any machine
# that has ever built and fails on a fresh checkout, which is how it broke
# main CI once already (run ebb5a48). So build it and let make decide.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


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
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
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
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
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


# --- AGAST #4854: a condition is lowered as i1, never widened ---------------
#
# THE DEFECT
#
#     pub fn isspace(c: u8) -> bool
#         return c == ' ' or c == '\t' or c == '\n' or c == '\r'
#
# ritz1 zero-extended every compare to i64, joined each `or` with a
# `phi i64 [ 1, ... ], [ %zext, ... ]`, retested it with `icmp ne i64 %phi, 0`
# and `trunc`'d the last phi for `ret i1`.  Early SimplifyCFG folds a chain of
# compares into a switch only when each `br` and `phi` takes them directly, so
# clang -O2 gave ritz1's isspace 3 setcc + `or` where ritz0's became one bit
# test (`lshr i33 <mask>, %c`): +25% Ir in isspace, all of wc's 12% gap to
# ritz0 (#4850).
#
# THE FIX
#
# emit_cond (emitter_seam) is a condition's i1: a compare's icmp, `and` / `or`
# as a short-circuit with an i1 phi, `not` as `xor i1`, anything else
# `icmp ne i64 v, 0`.  if / while / if-expression / assert conditions and a
# `-> bool` return use it.  A bool VALUE is still the one i64 model (#1646):
# emit_expr zero-extends emit_cond's i1, once.
#
# Each row is a fn of one program, compiled once per ritz1 binary; the -O2 row
# is the measured win itself.

I1_PROGRAM = """\
pub fn is_space(c: u8) -> bool
    return c == ' ' or c == '\\t' or c == '\\n' or c == '\\r'

pub fn in_range(c: u8) -> bool
    c >= 'a' and c <= 'z'

pub fn neither(a: bool, b: bool) -> bool
    not (a or b)

pub fn cond_if(x: i32) -> i32
    if x > 3 and x < 9
        return 1
    0

pub fn cond_while(n: i32) -> i32
    var i: i32 = 0
    while i < n or i == 0
        i = i + 1
    i

pub fn as_value(x: i32) -> i32
    let a: bool = x > 1 and x < 5
    if a
        return 1
    0

pub fn main() -> i32
    if is_space(32) and in_range(98) and not neither(true, false)
        return cond_if(4) + cond_while(2) + as_value(3)
    0
"""

I1_COMPILERS = ["ritz1", "ritz1_selfhosted"]


def _fn_body(ll_text: str, name: str) -> str:
    m = re.search(r"^define [^\n]*@\"?" + name + r"\"?\(.*?^}", ll_text, re.S | re.M)
    assert m, f"no define for {name}"
    return m.group(0)


def _strict_i1(body: str) -> list[str]:
    """A condition merged in an i1 phi and never widened: no i64 phi, no zext
    of an i1, no `icmp ne i64 %v, 0` retest, no trunc back to i1."""
    bad = []
    if "phi i1" not in body:
        bad.append("no `phi i1`")
    for pat in (r"phi i64", r"zext i1", r"trunc i64 \S+ to i1", r"icmp ne i64 \S+, 0"):
        if re.search(pat, body):
            bad.append(f"has `{pat}`")
    return bad


def _neither_i1(body: str) -> list[str]:
    # `not (a or b)`: the xor of the i1 phi is what `ret i1` returns.  The bool
    # params are i64 values (spilled with a zext, read with `icmp ne i64`):
    # that is their storage, not a round trip.
    bad = []
    if not re.search(r"(%\.\d+) = xor i1 (%\.\d+), true\n  ret i1 \1\n", body):
        bad.append("ret i1 is not `xor i1 <phi>, true`")
    if "phi i64" in body or "phi i1" not in body:
        bad.append("the `or` did not merge in an i1 phi")
    return bad


def _as_value_i1(body: str) -> list[str]:
    # `let a: bool = x > 1 and x < 5`: an i1 phi, widened once for the slot.
    bad = []
    if "phi i1" not in body or "phi i64" in body:
        bad.append("the `and` did not merge in an i1 phi")
    if body.count("zext i1") != 1:
        bad.append(f"{body.count('zext i1')} `zext i1`, want 1 (the slot's)")
    return bad


I1_ROWS = {
    "is_space": _strict_i1,     # `return` of an `or` chain
    "in_range": _strict_i1,     # an `and` tail
    "cond_if": _strict_i1,      # an `if` condition
    "cond_while": _strict_i1,   # a `while` condition
    "neither": _neither_i1,     # `not` of an `or`
    "as_value": _as_value_i1,   # a bool value
}


def _i1_failures(tmp_path: Path, compiler: str) -> dict[str, list[str]]:
    """Every #4854 row that `compiler` gets wrong, keyed `compiler:fn`."""
    binary = RITZ1_BIN.parent / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    src = tmp_path / f"i1_{compiler}.ritz"
    src.write_text(I1_PROGRAM)
    ll = tmp_path / f"i1_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, f"{compiler}: {proc.stderr}"
    text = ll.read_text()
    failed = {f"{compiler}:{fn}": bad for fn, check in I1_ROWS.items()
              if (bad := check(_fn_body(text, fn)))}
    # The measured win: clang -O2 folds is_space's compares into one shifted
    # mask, as it does ritz0's.  It was 3 setcc + `or`.
    opt = tmp_path / f"i1_{compiler}.opt.ll"
    proc = subprocess.run(["clang", "-O2", "-S", "-emit-llvm", "-Wno-override-module",
                           str(ll), "-o", str(opt)], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    o2 = _fn_body(opt.read_text(), "is_space")
    if not re.search(r"lshr i\d+ -?\d+, ", o2) or "or i1" in o2:
        failed[f"{compiler}:is_space@O2"] = ["not a single bit test:\n" + o2]
    if failed:
        failed[f"{compiler}:ir"] = ["\n" + text]
    return failed


@pytest.mark.integration
def test_ritz1_bool_condition_rows(ritz1_bin, tmp_path):
    """One table: the headline form's parity with ritz0 (#1367), then the
    #4854 i1-lowering rows under ritz1 and ritz1_selfhosted.  Every failing
    row is named, not just the first."""
    failed: dict[str, list[str]] = {}
    r0 = _run("ritz0", tmp_path, "parity", IF_CALL)
    r1 = _run("ritz1", tmp_path, "parity", IF_CALL)
    if r0 != r1:
        failed["parity:if_call"] = [f"ritz0 returned {r0}, ritz1 returned {r1} for `if yes()`"]
    for compiler in I1_COMPILERS:
        failed.update(_i1_failures(tmp_path, compiler))
    assert not failed, "\n".join(f"{row}: {'; '.join(b)}" for row, b in failed.items())
