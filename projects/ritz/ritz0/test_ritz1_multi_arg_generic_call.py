"""Regression tests for AGAST #1612: ritz1 must parse a generic CALL with more
than one explicit type argument — `second<i64, i32>(a, b)` — without turning
the comparison pair `f(a < b, c > (d))` into one.

Both readings are well-formed token streams.  ritz0 resolves the ambiguity
like C#: a `<...>` list followed by `(` is ALWAYS type arguments, so ritz0
rejects `f(a < b, c > (d))` ("`f` called with 1 argument(s)").  #1300 kept
ritz1's generic calls single-argument precisely to keep that comparison
working, and this ticket must not regress it.  ritz1's rule (see
`postfix_generic_call_list` in ritz1/src/ast_helpers.ritz):

  a type-argument list of TWO OR MORE arguments in call position is a generic
  call unless one of its arguments is a bare lowercase identifier — a value
  name by Ritz style (types are PascalCase or primitive keywords) — in which
  case the parser backtracks and reads `<` and `>` as comparisons.

So ritz0 is the oracle for the runnable generic-call programs, but NOT for the
comparison programs: those assert ritz1's documented answer directly.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
LEVEL35 = RITZ_ROOT / "ritz0" / "test" / "test_level35.ritz"


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date; make's dependency graph decides the work.

    A stale ritz1 would assert against the old parser (see AGAST #1322).
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
            "could not build ritz1 for the multi-arg generic call tests:\n"
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


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    proc = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    return proc, ll


def _compiled_ir(compiler: str, tmp_path: Path, name: str, program: str) -> str:
    """Compile and return the IR text; fail loudly on any compile error."""
    comp, ll = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    assert "cannot parse" not in comp.stderr, comp.stderr[-2000:]
    return ll.read_text()


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    _compiled_ir(compiler, tmp_path, name, program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(1, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link ({name}):\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


EXPECTED = 7

SECOND = """\
fn second<T, U>(a: T, b: U) -> U
    b

"""

FIRST = """\
fn first<T, U>(a: T, b: U) -> T
    a

"""

BOX = """\
struct Box<T>
    v: T

"""

# --- generic calls: every program returns 7 only when it parsed and ran right

GENERIC_CALLS = {
    # The ticket's repro: two primitive type arguments, second param returned.
    # Before the fix: `cannot parse item starting at 'fn main'`.
    "ticket_second": SECOND
    + """\
pub fn main() -> i32
    let r: i32 = second<i64, i32>(100, 7)
    r
""",
    # The FIRST parameter substituted from the first type argument, with the
    # second argument a different width — catches a mangler or substituter
    # that reads only one of the two.
    "first_of_two": FIRST
    + """\
pub fn main() -> i32
    let r: i64 = first<i64, i32>(7, 100)
    r as i32
""",
    # Three type arguments.
    "three_args": """\
fn third<A, B, C>(a: A, b: B, c: C) -> C
    c

pub fn main() -> i32
    let r: i32 = third<i64, i64, i32>(1, 2, 7)
    r
""",
    # A PascalCase struct argument beside a primitive (test_trait_bounds'
    # `mixed_params<i32, Counter>` shape).
    "struct_type_arg": """\
struct Counter
    n: i64

fn pick<T, U>(a: T, c: *U) -> T
    a

pub fn main() -> i32
    var c: Counter
    c.n = 1
    let r: i32 = pick<i32, Counter>(7, @c)
    r
""",
    # The last argument is itself generic and its `>>` closes the call's list.
    "shr_closed": BOX
    + """\
fn unbox_second<T, U>(a: T, b: U) -> U
    b

pub fn main() -> i32
    var b: Box<i64>
    b.v = 7
    let o: Box<i64> = unbox_second<i32, Box<i64>>(0, b)
    o.v as i32
""",
    # `usize` lexes as a lowercase IDENT, like a value name; it must still
    # read as a type argument, not a comparison.
    "usize_arg": SECOND
    + """\
pub fn main() -> i32
    let r: i32 = second<usize, i32>(100, 7)
    r
""",
    # A generic body forwarding BOTH of its parameters to another
    # two-parameter generic: `second<A, B>` must instantiate second$i64$i32
    # only once A and B are both bound — never a half-substituted
    # second$i64$B.
    "forwarded_params": SECOND
    + """\
fn fwd<A, B>(a: A, b: B) -> B
    second<A, B>(a, b)

pub fn main() -> i32
    let r: i32 = fwd<i64, i32>(100, 7)
    r
""",
    # Both parameters inside one mangled struct name, in the return type, a
    # local's type and a struct literal: `Pair$A$B` must become `Pair$i64$i32`
    # component by component, not have a suffix appended per pass.
    "pair_built_in_body": """\
struct Pair<A, B>
    a: A
    b: B

fn mk<A, B>(x: A, y: B) -> Pair<A, B>
    var p: Pair<A, B> = Pair<A, B> { a: x, b: y }
    p

pub fn main() -> i32
    let p: Pair<i64, i32> = mk<i64, i32>(100, 7)
    p.b
""",
    # The ticket's full test_level35 shape: ritzlib.result's two-parameter
    # helpers, called with explicit `<i32, i32>`.
    "result_helpers": """\
import ritzlib.result

fn divide(a: i32, b: i32) -> Result<i32, i32>
    if b == 0
        return Err(1)
    return Ok(a / b)

pub fn main() -> i32
    var ok: Result<i32, i32> = divide(14, 2)
    var bad: Result<i32, i32> = divide(1, 0)
    if result_is_err<i32, i32>(@bad) != 1
        return 1
    result_unwrap_or<i32, i32>(@ok, -1)
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(GENERIC_CALLS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, GENERIC_CALLS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(GENERIC_CALLS))
def test_ritz1_runs_multi_arg_generic_call(ritz1_bin, tmp_path, name):
    """AGAST #1612. Before the fix: `cannot parse item` for any 2+-arg call."""
    assert _run("ritz1", tmp_path, name, GENERIC_CALLS[name]) == EXPECTED


@pytest.mark.integration
def test_ritz1_mangles_on_every_type_arg(ritz1_bin, tmp_path):
    """`second<i64, i32>` instantiates `second$i64$i32` — ritz0's spelling."""
    ir = _compiled_ir("ritz1", tmp_path, "second_ir", GENERIC_CALLS["ticket_second"])
    assert re.search(r"define[^\n]*@second\$i64\$i32\(", ir), ir[:3000]
    assert re.search(r"call[^\n]*@second\$i64\$i32\(", ir), ir[:3000]


@pytest.mark.integration
def test_ritz1_forwarding_instantiates_only_concrete(ritz1_bin, tmp_path):
    """`fwd<i64, i32>` calling `second<A, B>` yields second$i64$i32 and no
    half-bound `second$i64$B` (registered between the A and B passes)."""
    ir = _compiled_ir(
        "ritz1", tmp_path, "fwd_ir", GENERIC_CALLS["forwarded_params"]
    )
    assert re.search(r"define[^\n]*@second\$i64\$i32\(", ir), ir[:3000]
    assert "second$i64$B" not in ir, ir[:3000]


# --- comparisons that must NOT become generic calls --------------------------
#
# f(x, y) adds 1 when x is true and 2 when y is true; main adds 4.  7 means
# BOTH comparison arguments arrived and both were true.

CMP_F = """\
fn f(x: bool, y: bool) -> i32
    var r: i32 = 0
    if x
        r = r + 1
    if y
        r = r + 2
    r

"""

COMPARISONS = {
    # The #1300 case named in the ticket, verbatim.
    "ticket_comparison_pair": CMP_F
    + """\
pub fn main() -> i32
    let a: i64 = 1
    let b: i64 = 2
    let c: i64 = 9
    let d: i64 = 3
    f(a < b, c > (d)) + 4
""",
    # One side a SCREAMING_CASE constant: the other, lowercase, still marks
    # the list as values.
    "constant_beside_value": CMP_F
    + """\
const LIMIT: i64 = 5

pub fn main() -> i32
    let x: i64 = 1
    let y: i64 = 9
    let z: i64 = 3
    f(x < LIMIT, y > (z)) + 4
""",
    # The lowercase name is the FIRST argument of the would-be list.
    "value_then_constant": CMP_F
    + """\
const LIMIT: i64 = 5

pub fn main() -> i32
    let x: i64 = 1
    let y: i64 = 2
    f(x < y, LIMIT > (3)) + 4
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(COMPARISONS))
def test_ritz1_keeps_comparison_pairs(ritz1_bin, tmp_path, name):
    """`f(a < b, c > (d))` stays two comparison arguments (AGAST #1300)."""
    assert _run("ritz1", tmp_path, name, COMPARISONS[name]) == EXPECTED


@pytest.mark.integration
def test_ritz0_reads_the_comparison_pair_as_a_call(tmp_path):
    """Pins the documented divergence: ritz0 takes `<b, c>(d)` as type args.

    If ritz0 ever adopts ritz1's rule this fails, and the module docstring's
    claim that ritz0 is not the oracle for COMPARISONS should be revisited.
    """
    comp, _ll = _compile(
        "ritz0", tmp_path, "cmp_ritz0", COMPARISONS["ticket_comparison_pair"]
    )
    assert comp.returncode != 0
    assert "called with 1 argument" in comp.stdout + comp.stderr


# --- test_level35, every [[test]] fn ----------------------------------------


def _level35_harness() -> str:
    """test_level35 with a main that runs EVERY [[test]] fn, not just the first.

    Returns 100 + the index of the first failing test, or 0.
    """
    src = LEVEL35.read_text()
    names = re.findall(r"\[\[test\]\]\s*\n\s*fn\s+([A-Za-z_]\w*)\s*\(", src)
    assert len(names) >= 5, names
    lines = ["", "pub fn main() -> i32"]
    for i, n in enumerate(names):
        lines += [f"    if {n}() != 0", f"        return {100 + i}"]
    lines.append("    0")
    return src + "\n".join(lines) + "\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_level35_every_test_passes(ritz1_bin, tmp_path, compiler):
    """The ticket's acceptance file: `result_is_err<i32, i32>(@res)` etc."""
    assert _run(compiler, tmp_path, "level35", _level35_harness()) == 0
