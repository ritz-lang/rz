"""Regression tests for AGAST #1557: ritz1 must fold each element of a module
const array. `const T: [3]i32 = [-5, 3, -7]` has to become
`[i32 -5, i32 3, i32 -7]`.

emit_const_array_entry (primitive-element branch) emitted each element's raw
`int_val`. A `-5` element is an EXPR_UNARY(NEG) node whose own int_val is 0, so
the table became `[i32 0, i32 3, i32 0]`. The same happened to const names and
expressions (`A + 1`). This is the same class of bug as #1502 (scalar consts).
Each element now goes through const_fold_int. An element that doesn't fold is a
located error instead of a silent 0.

Every runtime program exits 3 when the elements hold the right values and
exits with something else otherwise. ritz0 is the oracle.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date; a stale binary would test the old emitter."""
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
            "could not build ritz1 for the const-array fold tests:\n"
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


# --- runtime round-trips (ritz0 is the oracle) --------------------------------

# The ticket's repro: -5 + 8 == 3. With the bug T[0] is 0 and the program exits 8.
I32_NEG_REPRO = """\
const T: [3]i32 = [-5, 3, -7]

pub fn main() -> i32
    return T[0] + 8
"""

# Every element is checked, so dropping any one of them to 0 fails the test.
I32_NEG_ALL = """\
const T: [3]i32 = [-5, 3, -7]

pub fn main() -> i32
    if T[0] != -5
        return 10
    if T[1] != 3
        return 11
    if T[2] != -7
        return 12
    return 3
"""

# A negative that needs the high word: an i32 truncation or a 0 both fail.
I64_NEG = """\
const T: [3]i64 = [-8589934595, 1, -1]

pub fn main() -> i32
    if T[0] != -8589934595
        return 10
    if T[2] != -1
        return 11
    return 3
"""

# Element expressions over another integer const, declared before the array.
CONST_EXPR = """\
const A: i32 = 2

const T: [3]i32 = [A + 1, A * 5, -A]

pub fn main() -> i32
    if T[1] != 10
        return 10
    if T[2] != -2
        return 11
    return T[0]
"""

# The const is declared after the array, so it's still PENDING at parse
# time. Emit-time folding resolves it against the merged const list.
CONST_EXPR_LATER = """\
const T: [2]i32 = [B + 1, 0]

const B: i32 = 2

pub fn main() -> i32
    return T[0]
"""

# Hex elements, including a hex literal under unary minus.
HEX = """\
const T: [3]i32 = [0x03, -0x10, 0x7fffffff]

pub fn main() -> i32
    if T[1] != -16
        return 10
    if T[2] != 2147483647
        return 11
    return T[0]
"""

# ~ and ! on a hex literal fold too.
BIT_NOT = """\
const T: [3]i32 = [~0x0, !0, 3]

pub fn main() -> i32
    if T[0] != -1
        return 10
    if T[1] != 1
        return 11
    return T[2]
"""

# The iterable form (`for v in T`) reads the same global.
FOR_IN_SUM = """\
const T: [4]i32 = [-5, 10, -4, 2]

pub fn main() -> i32
    var sum: i32 = 0
    for v in T
        sum = sum + v
    return sum
"""

FORMS = {
    "i32_neg_repro": I32_NEG_REPRO,
    "i32_neg_all": I32_NEG_ALL,
    "i64_neg": I64_NEG,
    "const_expr": CONST_EXPR,
    "const_expr_later": CONST_EXPR_LATER,
    "hex": HEX,
    "bit_not": BIT_NOT,
    "for_in_sum": FOR_IN_SUM,
}

# Forms ritz0 folds that exercise the rest of its const evaluator (AGAST
# #1568): `as` casts, char literals, `!` on a named const, C-style truncating
# `/` and `%` on negative operands, and an expression in the fill form. They
# are checked against ritz0 only; ritz1 parity for them is not this ticket.
CAST_CHAR = """\
const A: i32 = 2

const T: [3]i32 = [(A + 1) as i32, 'a' as i32, !A]

pub fn main() -> i32
    if T[1] != 97
        return 10
    if T[2] != 0
        return 11
    return T[0]
"""

TRUNC_DIV = """\
const T: [3]i32 = [-7 / 2, -7 % 2, 7 / -2]

pub fn main() -> i32
    if T[1] != -1
        return 10
    if T[2] != -3
        return 11
    return T[0] + 6
"""

FILL_EXPR = """\
const A: i32 = 1

const T: [4]i32 = [A + 2; 4]

pub fn main() -> i32
    return T[3]
"""

RITZ0_ONLY_FORMS = {
    "cast_char": CAST_CHAR,
    "trunc_div": TRUNC_DIV,
    "fill_expr": FILL_EXPR,
}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
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
    return comp, ll


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    comp, ll = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FORMS))
def test_ritz0_oracle(name: str, tmp_path: Path) -> None:
    """ritz0 is the reference: every program is written to exit 3."""
    assert _run("ritz0", tmp_path, name, FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ0_ONLY_FORMS))
def test_ritz0_folds_const_expr_elements(name: str, tmp_path: Path) -> None:
    assert _run("ritz0", tmp_path, name, RITZ0_ONLY_FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FORMS))
def test_ritz1_const_array_fold(name: str, ritz1_bin: Path, tmp_path: Path) -> None:
    rc = _run("ritz1", tmp_path, name, FORMS[name])
    assert rc == 3, f"ritz1 build of {name} exited {rc}, expected 3"


# --- emitted IR ----------------------------------------------------------------


@pytest.mark.integration
def test_ritz1_emits_folded_global(ritz1_bin: Path, tmp_path: Path) -> None:
    """The ticket's exact symptom: the global itself holds the folded values."""
    comp, ll = _compile("ritz1", tmp_path, "ir", I32_NEG_REPRO)
    assert comp.returncode == 0, comp.stderr
    ir = ll.read_text()
    assert "@T = internal constant [3 x i32] [i32 -5, i32 3, i32 -7]" in ir, ir


# --- unfoldable elements are errors, not a silent 0 ---------------------------

UNFOLDABLE_CALL = """\
fn f() -> i32
    return 1

const T: [2]i32 = [f(), 2]

pub fn main() -> i32
    return T[1]
"""

UNFOLDABLE_UNKNOWN = """\
const T: [2]i32 = [1, NOPE]

pub fn main() -> i32
    return T[0]
"""


@pytest.mark.integration
@pytest.mark.parametrize(
    "name,program,elem",
    [("call", UNFOLDABLE_CALL, 0), ("unknown_name", UNFOLDABLE_UNKNOWN, 1)],
)
def test_ritz1_rejects_unfoldable_element(
    name: str, program: str, elem: int, ritz1_bin: Path, tmp_path: Path
) -> None:
    comp, _ = _compile("ritz1", tmp_path, name, program)
    assert comp.returncode != 0, (
        f"ritz1 accepted a non-constant array element for {name}:\n{comp.stderr}"
    )
    assert "error: const 'T'" in comp.stderr, comp.stderr
    assert f"element {elem}" in comp.stderr, comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize(
    "name,program,elem,line",
    [("call", UNFOLDABLE_CALL, 0, 4), ("unknown_name", UNFOLDABLE_UNKNOWN, 1, 1)],
)
def test_ritz0_rejects_unfoldable_element(
    name: str, program: str, elem: int, line: int, tmp_path: Path
) -> None:
    """AGAST #1568: a located error naming the const and element, no traceback."""
    comp, _ = _compile("ritz0", tmp_path, name, program)
    assert comp.returncode != 0, (
        f"ritz0 accepted a non-constant array element for {name}:\n{comp.stderr}"
    )
    out = comp.stdout + comp.stderr
    assert "Traceback" not in out, out
    assert f"{name}_ritz0.ritz:{line}:" in out, out
    assert "const 'T'" in out and f"element {elem}" in out, out
