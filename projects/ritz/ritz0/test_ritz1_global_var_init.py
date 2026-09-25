"""Regression tests for AGAST #1501 — ritz1 must honour a global `var`'s
initializer.

ritz1's `emit_global_vars` always wrote `zeroinitializer` and never read
`GlobalVarDef.init_expr`, so

    var g: i32 = 5

    pub fn main() -> i32
        return g

exited 0 under ritz1 (5 under ritz0) with no diagnostic: a silent miscompile.
zeus's `var g_running: i32 = 1` started at 0, so its daemon left its event
loop the moment it entered it.

The fix lowers a constant initializer (int / bool / char / float literal,
unary minus or `~` of one, `null`, or a cast of any of those) to the LLVM
initializer, and gives anything else a located error instead of a zero.

Every runnable program returns 3 when the global held the right value at
startup and something else otherwise; ritz0 is run as the oracle.  Storage
width is left as ritz1 already had it (narrow ints, bool and floats live in an
i64 slot), so the IR-shape tests pin the initializer in that storage type.
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
            "could not build ritz1 for the global initializer tests:\n"
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
var g: i32 = 5

pub fn main() -> i32
    return g
"""

# --- constant initializers that ritz1 zeroed before the fix -----------------
# Each returns 3 only if the global started with exactly its initializer.

BROKEN_FORMS = {
    "i32": """\
var g: i32 = 3

pub fn main() -> i32
    return g
""",
    # Needs more than 32 bits, so a truncated or i32-typed initializer fails.
    "i64_wide": """\
var g: i64 = 7777777777

pub fn main() -> i32
    if g == 7777777777
        return 3
    return 1
""",
    "u64_hex": """\
var g: u64 = 0x10000000

pub fn main() -> i32
    if g == 268435456
        return 3
    return 1
""",
    "u32_hex": """\
var g: u32 = 0x12345678

pub fn main() -> i32
    if g == 305419896
        return 3
    return 1
""",
    "i32_negative": """\
var g: i32 = -7

pub fn main() -> i32
    if g == -7
        return 3
    return 1
""",
    "i64_negative_wide": """\
var g: i64 = -5000000000

pub fn main() -> i32
    if g == -5000000000
        return 3
    return 1
""",
    "u8": """\
var g: u8 = 200

pub fn main() -> i32
    return (g as i32) - 197
""",
    "cast_of_literal": """\
var g: i64 = 3 as i64

pub fn main() -> i32
    return g as i32
""",
    # zeus's shape: a run flag the event loop polls, cleared by the body.
    "zeus_run_flag": """\
var g_running: i32 = 1
var g_ticks: i32 = 0

pub fn main() -> i32
    while g_running == 1
        g_ticks = g_ticks + 1
        if g_ticks == 3
            g_running = 0
    return g_ticks
""",
    # Initialised globals are still ordinary mutable storage.
    "mutable_after_init": """\
var g: i32 = 10

pub fn main() -> i32
    g = g - 7
    return g
""",
}

# --- forms that already worked: zero / null initializers and no initializer --

WORKING_FORMS = {
    "zero": """\
var g: i32 = 0

pub fn main() -> i32
    return g + 3
""",
    "no_initializer": """\
var g: i64

pub fn main() -> i32
    return (g as i32) + 3
""",
    "ptr_null": """\
var g: *u8 = null

pub fn main() -> i32
    if g == null
        return 3
    return 1
""",
    "ptr_zero_cast": """\
var g: *u8 = 0 as *u8

pub fn main() -> i32
    if g == null
        return 3
    return 1
""",
}

ALL_RUNNABLE = {**BROKEN_FORMS, **WORKING_FORMS}

# --- ritz1-only forms --------------------------------------------------------
# ritz0's `_emit_global_var` raises "Unsupported global var initializer" for
# bool, char and float literals (AGAST #1539), so there is no oracle here: each
# program checks its own value and returns 3 when it matches.

RITZ1_ONLY_BROKEN_FORMS = {
    "bool_true": """\
var g: bool = true

pub fn main() -> i32
    if g
        return 3
    return 1
""",
    "u8_char": """\
var g: u8 = 'A'

pub fn main() -> i32
    return (g as i32) - 62
""",
    "f64": """\
var g: f64 = 1.5

pub fn main() -> i32
    return (g * 2.0) as i32
""",
    "f64_negative": """\
var g: f64 = -0.75

pub fn main() -> i32
    # -0.75 * 4.0 + 6 == 3.  (Not `g * -4.0`: unary minus on a float
    # literal inside an expression is a separate ritz1 bug, AGAST #1541.)
    return ((g * 4.0) as i32) + 6
""",
}

# Worked before the fix only because false == 0; pinned so it keeps working.
RITZ1_ONLY_WORKING_FORMS = {
    "bool_false": """\
var g: bool = false

pub fn main() -> i32
    if g
        return 1
    return 3
""",
}

# --- emitted initializer, in ritz1's existing storage type -----------------

IR_FORMS = {
    "i32": ("var g: i32 = 5\n", "i32 5"),
    "i64_wide": ("var g: i64 = 7777777777\n", "i64 7777777777"),
    "i32_negative": ("var g: i32 = -1\n", "i32 -1"),
    "bool_true": ("var g: bool = true\n", "i64 1"),
    "bool_false": ("var g: bool = false\n", "i64 0"),
    "u8": ("var g: u8 = 200\n", "i64 200"),
    "bit_not": ("var g: i32 = ~0\n", "i32 -1"),
    "f64": ("var g: f64 = 1.5\n", "i64 bitcast (double 1.5 to i64)"),
    "f64_negative": ("var g: f64 = -0.75\n", "i64 bitcast (double -0.75 to i64)"),
    "f64_from_int": ("var g: f64 = 2\n", "i64 bitcast (double 2.0 to i64)"),
    "f32_zero": ("var g: f32 = 0.0\n", "i64 zeroinitializer"),
    "ptr_null": ("var g: *u8 = null\n", "ptr null"),
    "ptr_int_cast": ("var g: *u8 = 4096 as *u8\n", "ptr inttoptr (i64 4096 to ptr)"),
    "no_initializer": ("var g: i32\n", "i32 zeroinitializer"),
    # Indexing a global array is AGAST #1504; only the declaration is pinned.
    "array_no_initializer": ("var g: [4]i32\n", "[4 x i32] zeroinitializer"),
}

# --- initializers ritz1 cannot fold: a located error, never a silent zero ---
# (name, program, 1-based line of the offending global)

NON_CONSTANT_FORMS = {
    "call": (
        """\
fn five() -> i32
    return 5

var g: i32 = five()

pub fn main() -> i32
    return g
""",
        4,
    ),
    "other_global": (
        """\
var a: i32 = 5
var g: i32 = a

pub fn main() -> i32
    return g
""",
        2,
    ),
    "binary": (
        """\
var g: i32 = 2 + 3

pub fn main() -> i32
    return g
""",
        1,
    ),
    # Aggregate initializers are not lowered yet; refuse rather than zero.
    "array_literal": (
        """\
var g: [2]i32 = [1, 2]

pub fn main() -> i32
    return 3
""",
        1,
    ),
    # A non-zero f32 needs its float bit pattern computed by ritz1, and LLVM
    # rejects `float 1.1` and fptrunc constexprs; refuse rather than guess.
    "f32_nonzero": (
        """\
var g: f32 = 1.1

pub fn main() -> i32
    return 3
""",
        1,
    ),
}

PROGRAM_TAIL = "\npub fn main() -> i32\n    return 0\n"


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


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    comp, ll, _ = _compile(compiler, tmp_path, name, program)
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


def _global_initializer(ll: Path, name: str) -> str:
    prefix = f"@{name} = weak_odr global "
    for line in ll.read_text().splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    raise AssertionError(f"no @{name} global in emitted IR:\n{ll.read_text()[:2000]}")


@pytest.mark.integration
def test_ritz0_repro_oracle(tmp_path):
    assert _run("ritz0", tmp_path, "repro", REPRO) == 5


@pytest.mark.integration
def test_ritz1_repro_exits_with_initializer(ritz1_bin, tmp_path):
    """AGAST #1501, verbatim. Before the fix: exit 0."""
    assert _run("ritz1", tmp_path, "repro", REPRO) == 5


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ALL_RUNNABLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, ALL_RUNNABLE[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BROKEN_FORMS))
def test_ritz1_global_starts_at_initializer(ritz1_bin, tmp_path, name):
    """Before the fix every one of these read 0 at startup."""
    assert _run("ritz1", tmp_path, name, BROKEN_FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING_FORMS))
def test_ritz1_zero_and_absent_initializers(ritz1_bin, tmp_path, name):
    """Zero/null/absent initializers worked by accident before; pin them."""
    assert _run("ritz1", tmp_path, name, WORKING_FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_ONLY_BROKEN_FORMS))
def test_ritz1_only_global_starts_at_initializer(ritz1_bin, tmp_path, name):
    """bool / char / float initializers; before the fix each read 0."""
    assert _run("ritz1", tmp_path, name, RITZ1_ONLY_BROKEN_FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_ONLY_WORKING_FORMS))
def test_ritz1_only_zero_initializers(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, RITZ1_ONLY_WORKING_FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(IR_FORMS))
def test_ritz1_emits_initializer(ritz1_bin, tmp_path, name):
    decl, expected = IR_FORMS[name]
    comp, ll, _ = _compile("ritz1", tmp_path, name, decl + PROGRAM_TAIL)
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz1 failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    assert _global_initializer(ll, "g") == expected


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(NON_CONSTANT_FORMS))
def test_ritz1_rejects_non_constant_initializer(ritz1_bin, tmp_path, name):
    """A non-constant initializer is a located error, not a silent zero."""
    program, line = NON_CONSTANT_FORMS[name]
    comp, ll, src = _compile("ritz1", tmp_path, name, program)
    assert comp.returncode != 0, (
        f"ritz1 accepted non-constant initializer {name!r}:\n{comp.stderr[-1000:]}"
    )
    assert not ll.exists(), f"ritz1 wrote an artifact for {name!r}"
    # "<file>:<line>:<col>: ..." naming the global.
    located = re.search(rf"{re.escape(str(src))}:{line}:\d+: .*'g'", comp.stderr)
    assert located, f"no located diagnostic for {name!r}:\n{comp.stderr[-2000:]}"


@pytest.mark.integration
def test_ritz1_located_error_names_imported_file(ritz1_bin, tmp_path):
    """The location must name the file that declares the global.

    An import's path String is dropped by the driver once the import is
    parsed, so the global keeps its own copy; the error must still name
    helper.ritz, not the main file or freed memory.
    """
    helper = tmp_path / "helper.ritz"
    helper.write_text("fn five() -> i32\n    return 5\n\n\nvar h: i32 = five()\n")
    src = tmp_path / "main.ritz"
    src.write_text("import helper\n\npub fn main() -> i32\n    return h\n")
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
    assert re.search(r"helper\.ritz:5:\d+: .*'h'", comp.stderr), comp.stderr[-2000:]
