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
AGAST #1540 adds a reference to a module integer (or bool) const, folded to
the const's value.

Every runnable program returns 3 when the global held the right value at
startup and something else otherwise; ritz0 is run as the oracle (it lowers
bool, char and float initializers, and `N as *T`, since AGAST #1539).  Storage
width is left as ritz1 already had it (narrow ints and floats live in an i64
slot; a bool is an i1 since AGAST #3001), so the IR-shape tests pin the
initializer in that storage type.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


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
    # --- AGAST #1539: ritz0 refused these, so they were ritz1-only ---
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
    "i64_char_cast": """\
var g: i64 = 'A' as i64

pub fn main() -> i32
    return (g as i32) - 62
""",
    "f64_cast": """\
var g: f64 = 1.5 as f64

pub fn main() -> i32
    return (g * 2.0) as i32
""",
    # ritz0 dropped the integer and wrote `null` for any pointer target.
    "ptr_int_cast": """\
var g: *u8 = 4096 as *u8

pub fn main() -> i32
    if (g as u64) == 4096
        return 3
    return 1
""",
    "ptr_int_bare": """\
var g: *u8 = 4096

pub fn main() -> i32
    if (g as u64) == 4096
        return 3
    return 1
""",
    # --- AGAST #1540: a module integer const folds to its value ---
    # ritz0 folds them too since AGAST #3702, so it is their oracle.
    "const_ident": """\
const K: i32 = 3
var g: i32 = K

pub fn main() -> i32
    return g
""",
    # Needs #1502's folded value: the const's raw int_val would be 0.
    "const_negative": """\
const NEG: i64 = -7
var g: i64 = NEG

pub fn main() -> i32
    if g == -7
        return 3
    return 1
""",
    # A const declared after the global and derived from another: resolved
    # at emit time (PENDING at parse time), and unary minus composes over it.
    "const_later_derived": """\
var g: i32 = -NEG3

const NEG3: i32 = BASE - 4
const BASE: i32 = 1

pub fn main() -> i32
    return g
""",
    "const_bool": """\
const ON: bool = true
var g: bool = ON

pub fn main() -> i32
    if g
        return 3
    return 1
""",
}

# The forms #1539 made oracle-checked, also run on ritz1_selfhosted.
FORMS_1539 = (
    "bool_true",
    "u8_char",
    "f64",
    "f64_negative",
    "i64_char_cast",
    "f64_cast",
    "ptr_int_cast",
    "ptr_int_bare",
    "bool_false",
)

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
    # `~` of an int literal, and unary operators nested over one, fold as
    # ritz1's global_init_fold folds them; ritz0 raised a bare ValueError
    # (AGAST #3027).
    "bit_not": """\
var g: i32 = ~0

pub fn main() -> i32
    if g == -1
        return 3
    return 1
""",
    "neg_of_bit_not": """\
var g: i32 = -~2

pub fn main() -> i32
    return g
""",
    # Worked before #1501 only because false == 0; pinned so it keeps working.
    "bool_false": """\
var g: bool = false

pub fn main() -> i32
    if g
        return 1
    return 3
""",
}

ALL_RUNNABLE = {**BROKEN_FORMS, **WORKING_FORMS}

# --- ritz1-only forms --------------------------------------------------------
# ritz0 lowers only a `"..."` here, not `c"..."` (#2357; ritz1 points both at
# the literal's `@.str`), so there is no oracle: the program checks its own
# value and returns 3 when it matches.

RITZ1_ONLY_BROKEN_FORMS = {
    "cstring": """\
var g: *u8 = c"A"

pub fn main() -> i32
    return (*g as i32) - 62
""",
}

# The #1540 forms, also run on ritz1_selfhosted.
FORMS_1540 = ("const_ident", "const_negative", "const_later_derived", "const_bool")

# --- ritz0-only forms --------------------------------------------------------
# ritz1 refuses a non-zero f32 (see NON_CONSTANT_FORMS); ritz0 lowers it.

RITZ0_ONLY_FORMS = {
    "f32_nonzero": """\
var g: f32 = 1.5

pub fn main() -> i32
    return (g * 2.0) as i32
""",
}

# --- emitted initializer, in ritz1's existing storage type -----------------

IR_FORMS = {
    "i32": ("var g: i32 = 5\n", "i32 5"),
    "i64_wide": ("var g: i64 = 7777777777\n", "i64 7777777777"),
    "i32_negative": ("var g: i32 = -1\n", "i32 -1"),
    # A bool is the one i1 byte every access is (AGAST #3001).
    "bool_true": ("var g: bool = true\n", "i1 1"),
    "bool_false": ("var g: bool = false\n", "i1 0"),
    "u8": ("var g: u8 = 200\n", "i64 200"),
    "bit_not": ("var g: i32 = ~0\n", "i32 -1"),
    "f64": ("var g: f64 = 1.5\n", "i64 bitcast (double 1.5 to i64)"),
    "f64_negative": ("var g: f64 = -0.75\n", "i64 bitcast (double -0.75 to i64)"),
    "f64_from_int": ("var g: f64 = 2\n", "i64 bitcast (double 2.0 to i64)"),
    "f32_zero": ("var g: f32 = 0.0\n", "i64 zeroinitializer"),
    "ptr_null": ("var g: *u8 = null\n", "ptr null"),
    "ptr_int_cast": ("var g: *u8 = 4096 as *u8\n", "ptr inttoptr (i64 4096 to ptr)"),
    "no_initializer": ("var g: i32\n", "i32 zeroinitializer"),
    # AGAST #1540: an integer const is written as its value, in g's storage.
    "const_ident": ("const K: i32 = 5\nvar g: i32 = K\n", "i32 5"),
    "const_negative": ("const K: i32 = -7\nvar g: i32 = K\n", "i32 -7"),
    "f64_from_int_const": ("const K: i32 = 2\nvar g: f64 = K\n", "i64 bitcast (double 2.0 to i64)"),
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
    # AGAST #1540 folds only integer consts: a float const's `value` is not
    # its value (it would read as 0).
    "float_const": (
        """\
const F: f64 = 1.5
var g: f64 = F

pub fn main() -> i32
    return 3
""",
        2,
    ),
    # A const that does not fold has its own error; the global naming it
    # must be refused too, not written as the const's placeholder 0.
    "bad_const": (
        """\
fn five() -> i32
    return 5

const B: i32 = five()
var g: i32 = B

pub fn main() -> i32
    return g
""",
        5,
    ),
    # A string fits only a pointer global (#2357).
    "string_not_pointer": (
        """\
var g: i64 = c"A"

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
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        cmd = [str(RITZ1_BIN.parent / compiler), str(src), "-o", str(ll)]
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
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
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
    """A c-string initializer; before the fix it read 0."""
    assert _run("ritz1", tmp_path, name, RITZ1_ONLY_BROKEN_FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", FORMS_1539)
def test_ritz1_selfhosted_global_starts_at_initializer(ritz1_bin, tmp_path, name):
    """AGAST #1539's forms on the third compiler, against the same oracle."""
    assert _run("ritz1_selfhosted", tmp_path, name, ALL_RUNNABLE[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", FORMS_1540)
def test_ritz1_selfhosted_global_from_const(ritz1_bin, tmp_path, name):
    """AGAST #1540's const-identifier forms on the third compiler."""
    assert _run("ritz1_selfhosted", tmp_path, name, ALL_RUNNABLE[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ0_ONLY_FORMS))
def test_ritz0_only_global_starts_at_initializer(tmp_path, name):
    assert _run("ritz0", tmp_path, name, RITZ0_ONLY_FORMS[name]) == 3


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
