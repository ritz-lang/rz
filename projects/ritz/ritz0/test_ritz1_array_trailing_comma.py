"""Regression tests for AGAST #1507 — ritz1 must accept a trailing comma in an
array literal: `[1, 2, 3,]`.

ritz0 has always accepted it. ritz1's grammar spelled the array literal as
`LBRACKET args RBRACKET`, and `args` (shared with call arguments) has no
optional trailing COMMA, so the parser failed on the `]` and ritz1 exited 1.

This is not cosmetic. cryptosec writes its AES S-boxes and the ed25519 group
order as multi-line tables with one row per line, every row ending in a comma:

    const SBOX: [256]u8 = [
        0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5,
        ...
    ]

so neither cryptosec nor valet (which links it) could be compiled by ritz1.

Every runnable program below returns 3 when the literal was parsed with the right
elements in the right order, and something else otherwise, so a fix that
parses the literal but drops or duplicates an element is caught too.
Assertions are on the runtime exit code, and ritz0 is run as the oracle.

The fix is deliberately scoped to the array-literal alternative, not to the
shared `args` rule, so call-argument parsing is unchanged; the malformed
shapes below (`[,]`, `[1,,2]`) pin that the new alternative accepts exactly
one optional trailing comma and nothing looser.
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
    """Bring RITZ1_BIN up to date; make's dependency graph decides the work.

    A stale ritz1 would assert against the old grammar (see AGAST #1322).
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
            "could not build ritz1 for the array trailing-comma tests:\n"
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


# --- forms that #1507 rejects ------------------------------------------------
#
# Module-level const tables are asserted on the emitted global initializer,
# not at runtime: indexing a module const array under ritz1 currently loads
# from address 0 and segfaults regardless of trailing commas (AGAST #1534,
# emitter-side, out of scope here). The initializer is exactly what the parser
# produced, element by element, so it is the right oracle for a parser fix.
# When #1534 lands, these can grow a runtime assertion too.

# The ticket's repro, verbatim.
CONST_ONE_LINE = """\
const T: [4]u8 = [1, 2, 3, 4,]

pub fn main() -> i32
    return 3
"""

# cryptosec's shape: one row per line, every row (including the last) ending
# in a comma, closing bracket on its own line.
CONST_MULTI_LINE = """\
const TABLE: [12]u8 = [
    0x00, 0x01, 0x02, 0x03,
    0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b,
]

pub fn main() -> i32
    return 3
"""

CONST_FORMS = {
    "const_one_line": (CONST_ONE_LINE, "T", "[4 x i8] [i8 1, i8 2, i8 3, i8 4]"),
    "const_multi_line": (
        CONST_MULTI_LINE,
        "TABLE",
        "[12 x i8] [" + ", ".join(f"i8 {i}" for i in range(12)) + "]",
    ),
}

# Already parsed before the fix; pinned so the new alternative can't shadow it.
CONST_WORKING_FORMS = {
    "const_no_trailing_comma_multi_line": (
        """\
const TABLE: [6]u8 = [
    0x00, 0x01, 0x02,
    0x03, 0x04, 0x05
]

pub fn main() -> i32
    return 3
""",
        "TABLE",
        "[6 x i8] [i8 0, i8 1, i8 2, i8 3, i8 4, i8 5]",
    ),
}

LET_ONE_LINE = """\
pub fn main() -> i32
    let a: [4]i32 = [1, 2, 3, 4,]
    return a[2]
"""

# Last element is the answer, so an element dropped at the trailing comma (or
# a phantom element appended by it) changes the result.
LET_MULTI_LINE = """\
pub fn main() -> i32
    let a: [6]i32 = [
        10, 20, 30,
        40, 50, 3,
    ]
    return a[5]
"""

# A single element with a trailing comma: the degenerate case of the new
# alternative, and the one most likely to be confused with a grouping.
SINGLE_ELEMENT = """\
pub fn main() -> i32
    let a: [1]i32 = [3,]
    return a[0]
"""

# --- runtime forms that already worked, pinned against regression ----------

ARRAY_FILL = """\
pub fn main() -> i32
    let a: [4]i32 = [3; 4]
    return a[3]
"""

CALL_ARGS = """\
fn pick(a: i32, b: i32, c: i32) -> i32
    return b

pub fn main() -> i32
    let a: [3]i32 = [pick(1, 3, 5), 2, 1]
    return a[0]
"""

LET_NO_TRAILING_COMMA = """\
pub fn main() -> i32
    let a: [4]i32 = [1, 2, 3, 4]
    return a[2]
"""

BROKEN_FORMS = {
    "let_one_line": LET_ONE_LINE,
    "let_multi_line": LET_MULTI_LINE,
    "single_element": SINGLE_ELEMENT,
}

WORKING_FORMS = {
    "array_fill": ARRAY_FILL,
    "call_args": CALL_ARGS,
    "let_no_trailing_comma": LET_NO_TRAILING_COMMA,
}

# Must still be rejected: the new alternative permits ONE trailing comma after
# at least one element, nothing else.
MALFORMED_FORMS = {
    "comma_only": """\
pub fn main() -> i32
    let a: [1]i32 = [,]
    return 3
""",
    "double_comma": """\
pub fn main() -> i32
    let a: [2]i32 = [1,,2]
    return 3
""",
    "double_trailing_comma": """\
pub fn main() -> i32
    let a: [2]i32 = [1, 2,,]
    return 3
""",
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
        f"{compiler} emitted IR that would not link for {name}:\n"
        f"{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


ALL_RUNNABLE = {**BROKEN_FORMS, **WORKING_FORMS}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ALL_RUNNABLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, ALL_RUNNABLE[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BROKEN_FORMS))
def test_ritz1_accepts_array_literal_trailing_comma(ritz1_bin, tmp_path, name):
    """AGAST #1507. Before the fix each of these was a ritz1 parse error."""
    assert _run("ritz1", tmp_path, name, BROKEN_FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING_FORMS))
def test_ritz1_already_working_array_forms(ritz1_bin, tmp_path, name):
    """Adjacent array/call forms that parsed before the fix must still parse."""
    assert _run("ritz1", tmp_path, name, WORKING_FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED_FORMS))
def test_ritz1_rejects_malformed_array_commas(ritz1_bin, tmp_path, name):
    """Only one trailing comma after at least one element is legal."""
    comp, ll = _compile("ritz1", tmp_path, name, MALFORMED_FORMS[name])
    assert comp.returncode != 0, (
        f"ritz1 accepted malformed array literal {name!r}:\n{comp.stdout[-1000:]}"
    )
    assert not ll.exists(), f"ritz1 wrote an artifact for malformed {name!r}"


def _const_initializer(ll: Path, name: str) -> str:
    for line in ll.read_text().splitlines():
        if line.startswith(f"@{name} = "):
            return line.split(" constant ", 1)[1].strip()
    raise AssertionError(f"no @{name} global in emitted IR:\n{ll.read_text()[:2000]}")


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CONST_FORMS))
def test_ritz1_const_table_trailing_comma(ritz1_bin, tmp_path, name):
    """AGAST #1507 — the cryptosec shape. Before the fix: parse error, exit 1."""
    program, glob, expected = CONST_FORMS[name]
    comp, ll = _compile("ritz1", tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz1 failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    assert _const_initializer(ll, glob) == expected


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CONST_WORKING_FORMS))
def test_ritz1_const_table_without_trailing_comma(ritz1_bin, tmp_path, name):
    program, glob, expected = CONST_WORKING_FORMS[name]
    comp, ll = _compile("ritz1", tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), comp.stderr[-2000:]
    assert _const_initializer(ll, glob) == expected


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted({**CONST_FORMS, **CONST_WORKING_FORMS}))
def test_ritz0_accepts_const_tables(tmp_path, name):
    """Oracle: ritz0 accepts every const shape asserted above and runs it."""
    program = {**CONST_FORMS, **CONST_WORKING_FORMS}[name][0]
    assert _run("ritz0", tmp_path, name, program) == 3
