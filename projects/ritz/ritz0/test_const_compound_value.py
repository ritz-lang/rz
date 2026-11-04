"""Compound `const` initializers fold in ritz0, and agree with ritz1 (AGAST #2150).

ritz0's emitter lowered only IntLit / FloatLit / `-literal` / array / string
const values, so even a single-module

    const X: i32 = 2 + 3

died with `ValueError: Const value must be numeric literal or array literal:
BinOp(...)`, while ritz1 has folded such initializers since #1502. The emitter
now folds a scalar integer const with `const_eval.ConstEvaluator` over every
integer const in the module, resolving consts declared later on demand, and
anything that does not fold is a located error rather than a Python traceback.

Every runnable program exits 3 when the const held the right value and
something else otherwise, and is run through all three compilers: they must
agree.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

FORMS = {
    # The ticket's four shapes.
    "binop_add": """\
const X: i32 = 2 + 3

pub fn main() -> i32
    return X - 2
""",
    "logical_not": """\
const X: i32 = !0xF0
const Y: i32 = !0

pub fn main() -> i32
    if X == 0 and Y == 1
        return 3
    return 1
""",
    "ident_times": """\
const K: i32 = 4
const X: i32 = K * 2

pub fn main() -> i32
    return X - 5
""",
    "cast_of_negative": """\
const X: i64 = -1 as i64

pub fn main() -> i32
    if X == -1
        return 3
    return 1
""",
    # Around them.
    "bit_not": """\
const X: i32 = ~0

pub fn main() -> i32
    if X == -1
        return 3
    return 1
""",
    "shift_or_i64": """\
const X: i64 = (1 << 40) | 3

pub fn main() -> i32
    if X == 1099511627779
        return 3
    return 1
""",
    "precedence": """\
const X: i32 = 10 - 4 * 2 + 7 / 7

pub fn main() -> i32
    return X
""",
    "negative_of_const": """\
const K: i32 = 3
const X: i32 = -K

pub fn main() -> i32
    return 0 - X
""",
    "parenthesised_negative": """\
const X: i32 = -(-3)

pub fn main() -> i32
    return X
""",
    "truncating_division": """\
const X: i32 = -7 / 2
const Y: i32 = -7 % 2

pub fn main() -> i32
    if X == -3 and Y == -1
        return 3
    return 1
""",
    "refers_to_later_const": """\
const B: i32 = A * 3

const A: i32 = 1

pub fn main() -> i32
    return B
""",
    # C names B, itself not yet folded: B must be resolved on demand.
    "chain_of_later_consts": """\
const C: i32 = B - 3

const B: i32 = A * 2

const A: i32 = 3

pub fn main() -> i32
    return C
""",
    "unsigned_mask": """\
const MASK: u32 = (1 << 8) - 1

pub fn main() -> i32
    if MASK == 255
        return 3
    return 1
""",
    # Not compound, but ritz0 rejected these literal kinds too (#1549); they
    # take the same folding path now.
    "bool_and_char_literals": """\
const B: bool = true
const C: u8 = 'A'

pub fn main() -> i32
    if B
        return (C as i32) - 62
    return 1
""",
    # An array type sized by a const (AGAST #2153): ritz1 parsed only a
    # NUMBER there, so `[N]i32` killed the whole item.
    "used_as_array_size": """\
const N: i32 = 2 + 1

pub fn main() -> i32
    var a: [N]i32
    a[N - 1] = 3
    return a[2]
""",
    "literal_const_array_size": """\
const N: i32 = 3

pub fn main() -> i32
    var a: [N]i32
    a[N - 1] = 3
    return a[2]
""",
    # sizeof checks the folded length, not just that the type parsed.
    "const_expr_array_size": """\
const N: i32 = 2

pub fn main() -> i32
    var a: [N * 2 - 1]i32
    a[2] = 3
    if sizeof(a) != 12
        return 1
    return a[2]
""",
    "const_sized_nd_array_and_field": """\
const R: i32 = 2
const C: i32 = R + 1

struct Grid
    cells: [C]i32

pub fn main() -> i32
    var m: [R][C]i32
    m[R - 1][C - 1] = 2
    var g: Grid
    g.cells[C - 1] = 1
    return m[1][2] + g.cells[2]
""",
    # A folded value wraps to the const's declared width, as runtime
    # arithmetic at that width would (AGAST #2154): ritz1 used to keep the
    # unwrapped i64, so `M == 44` compared 300 with 44.
    "wraps_to_width": """\
const M: u8 = 200 + 100

pub fn main() -> i32
    if M == 44
        return 3
    return 1
""",
    # Signed sign-extends: 100 + 100 in i8 is -56.
    "signed_wraps_negative": """\
const M: i8 = 100 + 100

pub fn main() -> i32
    if M == -56 and (M as i32) == -56
        return 3
    return 1
""",
    "u16_u32_and_i32_wrap": """\
const A: u16 = 65535 + 2
const B: i32 = 2147483647 + 1
const C: u32 = 4294967295 + 4

pub fn main() -> i32
    if A == 1 and (B as i64) == -2147483648 and C == 3
        return 3
    return 1
""",
    # A const naming a wrapped one sees the wrapped value: 44 + 1, not 301.
    # (Compared, not returned: 301 - 42 exits 3 too, modulo 256.)
    "wrapped_const_as_operand": """\
const M: u8 = 200 + 100
const K: i32 = M + 1

pub fn main() -> i32
    if K == 45
        return 3
    return 1
""",
    # Resolved at emit time (names a later const), so it takes the other
    # folding path, which must wrap too.
    "wraps_when_resolved_late": """\
const M: u8 = L + 100

const L: i32 = 200

pub fn main() -> i32
    if M == 44
        return 3
    return 1
""",
    # A folded unsigned const zero-extends: 200 stays 200, not the i8
    # pattern -56 (AGAST #2154, #2170).
    "unsigned_in_range_stays_positive": """\
const M: u8 = 100 + 100

pub fn main() -> i32
    if M == 200 and (M as i32) == 200
        return 3
    return 1
""",
    # A plain literal unsigned const takes the same use-site path (#2170).
    "unsigned_literal_stays_positive": """\
const M: u8 = 200

pub fn main() -> i32
    if M == 200 and (M as i32) == 200
        return 3
    return 1
""",
    # A local inferred from an unsigned const keeps its unsignedness (#2170).
    "unsigned_const_into_inferred_local": """\
const M: u8 = 200

pub fn main() -> i32
    let x = M
    if x == 200 and (x as i32) == 200
        return 3
    return 1
""",
    # A float const with an integer initializer converts the folded integer
    # to the const's float type (AGAST #2155): ritz1 materialised it as an
    # i64 and used that as a double, which clang rejected.
    "float_from_negative_int": """\
const F: f64 = -1

pub fn main() -> i32
    if F < 0.0
        return 3
    return 1
""",
    "float_from_positive_int": """\
const F: f64 = 3

pub fn main() -> i32
    if F == 3.0
        return 3
    return 1
""",
    "float_from_folded_int": """\
const F: f64 = 2 + 5

pub fn main() -> i32
    if F == 7.0
        return 3
    return 1
""",
    # Names a later integer const, so it folds only at emit time; the
    # inferred local takes the const's float type.
    "float_from_later_int_const": """\
const F: f64 = K - 4

const K: i32 = 2

pub fn main() -> i32
    let x = F
    if x == -2.0 and (x as i32) == -2
        return 3
    return 1
""",
    "f32_from_negative_int": """\
const F: f32 = -2

pub fn main() -> i32
    if F < 0.0 and (F as i32) == -2
        return 3
    return 1
""",
}

# A const in the main file built from an imported one: resolvable only once the
# modules are merged.
IMPORT_HELPER = "pub const BASE: i32 = -10\npub const STEP: i32 = BASE + 12\n"
IMPORT_MAIN = (
    "import helper\n\nconst K: i32 = STEP + BASE + 11\n\n"
    "pub fn main() -> i32\n    return K\n"
)

# (program, 1-based line of the offending const named K)
NON_CONSTANT = {
    "call": (
        """\
fn five() -> i32
    return 5

const K: i32 = five()

pub fn main() -> i32
    return K
""",
        4,
    ),
    "unknown_ident": (
        """\
const K: i32 = NOT_DEFINED - 1

pub fn main() -> i32
    return K
""",
        1,
    ),
    "self_reference": (
        """\
const K: i32 = K + 1

pub fn main() -> i32
    return K
""",
        1,
    ),
    # Reported on the first const of the cycle, J, which names K.
    "mutual_reference": (
        """\
const J: i32 = K + 1
const K: i32 = J + 1

pub fn main() -> i32
    return K
""",
        1,
    ),
    "divide_by_zero": (
        """\
const K: i32 = 1 / 0

pub fn main() -> i32
    return K
""",
        1,
    ),
}


def _compile(compiler, src, ll, cwd):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=cwd, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=300)


def _build_and_run(compiler, d, main_src):
    ll = d / "main.ll"
    comp = _compile(compiler, main_src, ll, d)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = d / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=d, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(FORMS))
def test_compound_const_value(request, tmp_path, compiler, name):
    """Before #2150, ritz0 raised ValueError on every one of these."""
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    src = tmp_path / "main.ritz"
    src.write_text(FORMS[name])
    assert _build_and_run(compiler, tmp_path, src) == 3


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_compound_const_from_imported_consts(request, tmp_path, compiler):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    (tmp_path / "helper.ritz").write_text(IMPORT_HELPER)
    src = tmp_path / "main.ritz"
    src.write_text(IMPORT_MAIN)
    assert _build_and_run(compiler, tmp_path, src) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(NON_CONSTANT))
def test_ritz0_rejects_non_constant_initializer(tmp_path, name):
    """Not foldable: a located diagnostic naming the const, no traceback, no IR."""
    program, line = NON_CONSTANT[name]
    src = tmp_path / "main.ritz"
    src.write_text(program)
    ll = tmp_path / "main.ll"
    comp = _compile("ritz0", src, ll, tmp_path)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"ritz0 accepted {name!r}:\n{out[-1000:]}"
    assert not ll.exists(), f"ritz0 wrote IR for {name!r}"
    assert "Traceback" not in out, out[-2000:]
    assert re.search(rf"main\.ritz:{line}:\d+.*'K'", out), out[-2000:]


@pytest.mark.integration
def test_ritz0_folded_const_is_wrapped_in_ir(tmp_path):
    """The folded value is stored at the declared width, not as `i8 300`.

    LLVM truncates an out-of-range literal silently, so the run above passes
    either way; the IR is where an unwrapped value shows.
    """
    src = tmp_path / "main.ritz"
    src.write_text(FORMS["wraps_to_width"])
    ll = tmp_path / "main.ll"
    comp = _compile("ritz0", src, ll, tmp_path)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir_text = ll.read_text()
    assert "i8 300" not in ir_text
    assert "i8 44" in ir_text


# Array lengths ritz1 cannot fold at parse time (AGAST #2153): a located error
# at the `[`, never a silently zero-length array.  (line, col) of the `[`.
RITZ1_UNFOLDABLE_ARRAY_SIZE = {
    "unknown_ident": (
        """\
pub fn main() -> i32
    var a: [NOPE]i32
    return 0
""",
        2, 12,
    ),
    "call": (
        """\
fn five() -> i32
    return 5

pub fn main() -> i32
    var a: [five()]i32
    return 0
""",
        5, 12,
    ),
    "negative": (
        """\
const N: i32 = 0 - 2

pub fn main() -> i32
    var a: [N]i32
    return 0
""",
        4, 12,
    ),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
@pytest.mark.parametrize("name", sorted(RITZ1_UNFOLDABLE_ARRAY_SIZE))
def test_ritz1_rejects_unfoldable_array_size(request, tmp_path, compiler, name):
    request.getfixturevalue("ritz1_bin")
    program, line, col = RITZ1_UNFOLDABLE_ARRAY_SIZE[name]
    src = tmp_path / "main.ritz"
    src.write_text(program)
    ll = tmp_path / "main.ll"
    comp = _compile(compiler, src, ll, tmp_path)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {name!r}:\n{out[-1000:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name!r}"
    hits = re.findall(rf"main\.ritz:{line}:{col}: array length ", out)
    # Once, though the backtracking parser runs the action on every retry.
    assert len(hits) == 1, out[-2000:]
