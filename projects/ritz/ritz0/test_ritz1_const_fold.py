"""Regression tests for AGAST #1502 — ritz1 must fold an integer `const`'s
initializer instead of reading `int_val` off whatever node it is.

`const_new` stored `val.int_val`, which is only meaningful on an int literal.
For `-7` the node is a unary minus whose int_val is 0, so

    const K: i32 = -7

    pub fn main() -> i32
        return 0 - K

exited 0 under ritz1 (7 under ritz0) with no diagnostic: every negative const
in the corpus (error codes, `-1` sentinels) was silently 0, and ritz-lsp
answered an unknown method with `"code":0` instead of -32601.

The fix folds any constant integer expression (literals, unary - ~ !, casts,
binary arithmetic / bitwise / comparison, and references to other integer
consts, including imported ones) and gives anything else a located error
instead of a zero.

Every runnable program returns 3 when the const held the right value and
something else otherwise; ritz0 is the oracle where it supports the form.
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


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date; a stale binary would test the old parser."""
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
            "could not build ritz1 for the const folding tests:\n"
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


# --- the ticket's repro, verbatim: exit code IS the value -------------------

REPRO = """\
const K: i32 = -7

pub fn main() -> i32
    return 0 - K
"""

# --- negative literals: the ticket's reported shape --------------------------
# Each returns 3 only if the const has exactly the declared value.

NEGATIVE_FORMS = {
    # The ticket's second case: an i64 sentinel compared against -1.
    "i64_minus_one": """\
const M: i64 = -1

pub fn main() -> i32
    if M == -1
        return 3
    return 1
""",
    # ritz-lsp's shape: a JSON-RPC error code.
    "lsp_error_code": """\
const LSP_ERR_METHOD_NOT_FOUND: i32 = -32601

pub fn main() -> i32
    if LSP_ERR_METHOD_NOT_FOUND == -32601
        return 3
    return 1
""",
    # Needs more than 32 bits.
    "i64_negative_wide": """\
const M: i64 = -5000000000

pub fn main() -> i32
    if M == -5000000000
        return 3
    return 1
""",
    "negative_in_arithmetic": """\
const K: i32 = -4

pub fn main() -> i32
    return K + 7
""",
    "negative_passed_to_fn": """\
const K: i32 = -2

fn neg(x: i32) -> i32
    return 0 - x

pub fn main() -> i32
    return neg(K) + 1
""",
    "negative_stored_in_local": """\
const K: i64 = -10

pub fn main() -> i32
    let x: i64 = K
    return (x + 13) as i32
""",
}

# --- other constant expressions ritz1 zeroed before the fix -----------------
# ritz0 accepts only a (possibly negative) numeric literal as a const
# initializer (AGAST #1549), so there is no oracle here: each program checks
# its own value and returns 3 when it matches.

FOLDED_FORMS = {
    "bit_not": """\
const K: i32 = ~0

pub fn main() -> i32
    if K == -1
        return 3
    return 1
""",
    "binary_add": """\
const K: i32 = 1 + 2

pub fn main() -> i32
    return K
""",
    "binary_shift_or": """\
const K: i64 = (1 << 4) | 3

pub fn main() -> i32
    if K == 19
        return 3
    return 1
""",
    "binary_mixed": """\
const K: i32 = 10 - 4 * 2 + 7 / 7

pub fn main() -> i32
    return K
""",
    "refers_to_const": """\
const A: i32 = -4
const B: i32 = A + 7

pub fn main() -> i32
    return B
""",
    "refers_to_later_const": """\
const B: i32 = A * 3

const A: i32 = 1

pub fn main() -> i32
    return B
""",
    # C is resolved first and names B, itself still unresolved: B must be
    # resolved on demand, not in list order.
    "chain_of_later_consts": """\
const C: i32 = B - 3

const B: i32 = A * 2

const A: i32 = 3

pub fn main() -> i32
    return C
""",
    "cast_of_negative": """\
const K: i64 = -3 as i64

pub fn main() -> i32
    return (0 - K) as i32
""",
    "parenthesised_negative": """\
const K: i32 = -(-3)

pub fn main() -> i32
    return K
""",
}

# --- forms that already worked: pin them -----------------------------------

WORKING_FORMS = {
    "positive": """\
const K: i32 = 3

pub fn main() -> i32
    return K
""",
    "hex": """\
const K: u32 = 0x10

pub fn main() -> i32
    return (K as i32) - 13
""",
    "zero": """\
const K: i32 = 0

pub fn main() -> i32
    return K + 3
""",
}

ALL_RUNNABLE = {**NEGATIVE_FORMS, **WORKING_FORMS}

# ritz1 already accepted these literals; ritz0 rejects them (AGAST #1549).
RITZ1_ONLY_WORKING_FORMS = {
    "bool_true": """\
const B: bool = true

pub fn main() -> i32
    if B
        return 3
    return 1
""",
    "char": """\
const C: u8 = 'A'

pub fn main() -> i32
    return (C as i32) - 62
""",
}

# --- initializers that are not integer constants: a located error -----------
# (name, program, 1-based line of the offending const)

NON_CONSTANT_FORMS = {
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
    "divide_by_zero": (
        """\
const K: i32 = 1 / 0

pub fn main() -> i32
    return K
""",
        1,
    ),
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
    return comp, ll, src


def _link_and_run(compiler: str, tmp_path: Path, name: str, ll: Path) -> int:
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    comp, ll, _ = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return _link_and_run(compiler, tmp_path, name, ll)


def _run_with_import(compiler: str, tmp_path: Path, helper: str, main: str) -> int:
    """Build main.ritz importing helper.ritz, in a directory of its own."""
    d = tmp_path / compiler
    d.mkdir()
    (d / "helper.ritz").write_text(helper)
    src = d / "main.ritz"
    src.write_text(main)
    ll = d / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    comp = subprocess.run(
        cmd, cwd=d, env=env, capture_output=True, text=True, timeout=300
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile the import program:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return _link_and_run(compiler, d, "main", ll)


@pytest.mark.integration
def test_ritz0_repro_oracle(tmp_path):
    assert _run("ritz0", tmp_path, "repro", REPRO) == 7


@pytest.mark.integration
def test_ritz1_repro_negative_const(ritz1_bin, tmp_path):
    """AGAST #1502, verbatim. Before the fix: exit 0."""
    assert _run("ritz1", tmp_path, "repro", REPRO) == 7


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ALL_RUNNABLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, ALL_RUNNABLE[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(NEGATIVE_FORMS))
def test_ritz1_negative_const(ritz1_bin, tmp_path, name):
    """Before the fix every one of these read the const as 0."""
    assert _run("ritz1", tmp_path, name, NEGATIVE_FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FOLDED_FORMS))
def test_ritz1_folds_constant_expression(ritz1_bin, tmp_path, name):
    """Before the fix every one of these read the const as 0."""
    assert _run("ritz1", tmp_path, name, FOLDED_FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING_FORMS))
def test_ritz1_literal_consts_still_work(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, WORKING_FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_ONLY_WORKING_FORMS))
def test_ritz1_only_literal_consts_still_work(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, RITZ1_ONLY_WORKING_FORMS[name]) == 3


IMPORT_HELPER = "pub const K: i32 = -7\n"
IMPORT_MAIN = "import helper\n\npub fn main() -> i32\n    return 0 - K\n"

# A const in the main file built from an imported one: only resolvable once
# the modules are merged, so it cannot be folded while parsing main.ritz.
IMPORT_CHAIN_HELPER = "pub const BASE: i32 = -10\n"
IMPORT_CHAIN_MAIN = (
    "import helper\n\nconst K: i32 = BASE + 13\n\npub fn main() -> i32\n    return K\n"
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_imported_negative_const(request, tmp_path, compiler):
    """The ticket: 'Same result when K is imported from another module.'"""
    if compiler == "ritz1":
        request.getfixturevalue("ritz1_bin")
    assert _run_with_import(compiler, tmp_path, IMPORT_HELPER, IMPORT_MAIN) == 7


@pytest.mark.integration
def test_ritz1_const_built_from_imported_const(ritz1_bin, tmp_path):
    """ritz1-only: ritz0 rejects a non-literal initializer (AGAST #1549)."""
    got = _run_with_import("ritz1", tmp_path, IMPORT_CHAIN_HELPER, IMPORT_CHAIN_MAIN)
    assert got == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(NON_CONSTANT_FORMS))
def test_ritz1_rejects_non_constant_initializer(ritz1_bin, tmp_path, name):
    """A non-foldable initializer is a located error, not a silent zero."""
    program, line = NON_CONSTANT_FORMS[name]
    comp, ll, src = _compile("ritz1", tmp_path, name, program)
    assert comp.returncode != 0, (
        f"ritz1 accepted non-constant initializer {name!r}:\n{comp.stderr[-1000:]}"
    )
    assert not ll.exists(), f"ritz1 wrote an artifact for {name!r}"
    # "<file>:<line>:<col>: ..." naming the const.
    located = re.search(rf"{re.escape(str(src))}:{line}:\d+: .*'K'", comp.stderr)
    assert located, f"no located diagnostic for {name!r}:\n{comp.stderr[-2000:]}"


@pytest.mark.integration
def test_ritz1_located_error_names_imported_file(ritz1_bin, tmp_path):
    """The location must name the file that declares the const."""
    helper = tmp_path / "helper.ritz"
    helper.write_text("fn five() -> i32\n    return 5\n\n\npub const H: i32 = five()\n")
    src = tmp_path / "main.ritz"
    src.write_text("import helper\n\npub fn main() -> i32\n    return H\n")
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode != 0 and not ll.exists(), comp.stderr[-2000:]
    assert re.search(r"helper\.ritz:5:\d+: .*'H'", comp.stderr), comp.stderr[-2000:]
