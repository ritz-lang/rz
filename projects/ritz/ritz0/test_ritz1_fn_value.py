"""Regression tests for AGAST #1503 — ritz1 must accept a function name used as
a value (taking a function's address), e.g. `apply(double, 5)` or
`let f: fn(i32) -> i32 = double`.

ritz0 has always accepted it. ritz1's `emit_expr_ident` resolved an identifier
against constants, locals and globals only, never against functions, so every
such site was `error: ritz1 cannot emit: unknown identifier 'double'` and ritz1
exited 1. Indirect calls through a fn-typed local/parameter already lowered;
only producing the function's address was missing.

That blocked mausoleum (`task_server_run(srv, handle_task_event)`), nexus
(`scan_rebuild_callback as *u8`), tome (`task_server_run_multishot(...,
handle_connection)`, its only ritz1 blocker), valet, and example 57_fn_ptr.

Every runnable program returns 10 when the right function was called through
the pointer, and something else otherwise (`triple` would give 15, a null or
wrong pointer crashes), so a fix that takes *an* address but the wrong one is
caught too. ritz0 is run as the oracle.
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

EXPECTED = 10


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date; make's dependency graph decides the work.

    A stale ritz1 would assert against the old emitter (see AGAST #1322).
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
            "could not build ritz1 for the fn-value tests:\n"
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


# --- single-module forms that #1503 rejects ---------------------------------

# The ticket's repro, verbatim.
FN_ARG = """\
fn double(x: i32) -> i32
    return x * 2

fn apply(f: fn(i32) -> i32, x: i32) -> i32
    return f(x)

pub fn main() -> i32
    return apply(double, 5)
"""

# `triple` is defined and would be called by a fix that resolved the wrong
# name; it answers 15, not 10.
FN_ARG_CHOOSES_RIGHT_FN = """\
fn triple(x: i32) -> i32
    return x * 3

fn double(x: i32) -> i32
    return x * 2

fn apply(f: fn(i32) -> i32, x: i32) -> i32
    return f(x)

pub fn main() -> i32
    return apply(double, 5)
"""

LET_BOUND = """\
fn double(x: i32) -> i32
    return x * 2

pub fn main() -> i32
    let f: fn(i32) -> i32 = double
    return f(5)
"""

VAR_REASSIGNED = """\
fn triple(x: i32) -> i32
    return x * 3

fn double(x: i32) -> i32
    return x * 2

pub fn main() -> i32
    var f: fn(i32) -> i32 = triple
    f = double
    return f(5)
"""

# nexus's shape: the address cast to an opaque pointer.
CAST_TO_PTR = """\
fn double(x: i32) -> i32
    return x * 2

pub fn main() -> i32
    let p: *u8 = double as *u8
    if p == null
        return 1
    return 10
"""

# A fn declared *after* its use as a value: resolution must not depend on
# source order.
FORWARD_REFERENCE = """\
fn apply(f: fn(i32) -> i32, x: i32) -> i32
    return f(x)

pub fn main() -> i32
    return apply(double, 5)

fn double(x: i32) -> i32
    return x * 2
"""

BROKEN_FORMS = {
    "fn_arg": FN_ARG,
    "fn_arg_chooses_right_fn": FN_ARG_CHOOSES_RIGHT_FN,
    "let_bound": LET_BOUND,
    "var_reassigned": VAR_REASSIGNED,
    "cast_to_ptr": CAST_TO_PTR,
    "forward_reference": FORWARD_REFERENCE,
}

# --- forms that already worked, pinned against regression -------------------

# A local that shadows a function name must still read the local, not the fn.
LOCAL_SHADOWS_FN = """\
fn double(x: i32) -> i32
    return x * 2

pub fn main() -> i32
    let double: i32 = 10
    return double
"""

DIRECT_CALL = """\
fn double(x: i32) -> i32
    return x * 2

pub fn main() -> i32
    return double(5)
"""

WORKING_FORMS = {
    "local_shadows_fn": LOCAL_SHADOWS_FN,
    "direct_call": DIRECT_CALL,
}

# Still an error: a name that is neither a local, global, const nor function.
UNKNOWN_NAME = """\
pub fn main() -> i32
    let f: fn(i32) -> i32 = no_such_fn
    return f(5)
"""

# --- imported function used as a value --------------------------------------
#
# ritz1 compiles one module per .ll; an imported fn is merged into the module
# for type info but is defined in the other .ll, so its address needs an
# extern `declare` here. Both modules are compiled separately and linked.

IMPORT_HELPER = """\
pub fn double(x: i32) -> i32
    return x * 2
"""

IMPORT_MAIN = """\
import fnv_helper

fn apply(f: fn(i32) -> i32, x: i32) -> i32
    return f(x)

pub fn main() -> i32
    return apply(double, 5)
"""

# The imported fn used ONLY as a value, never called directly — so nothing but
# the value path can have registered its extern declaration.
IMPORT_MAIN_LET = """\
import fnv_helper

pub fn main() -> i32
    let f: fn(i32) -> i32 = double
    return f(5)
"""

IMPORT_FORMS = {
    "import_fn_arg": IMPORT_MAIN,
    "import_let_bound": IMPORT_MAIN_LET,
}


def _compile_file(compiler: str, cwd: Path, src: Path, ll: Path):
    env = dict(os.environ, RITZ_PATH=f"{cwd}:{RITZ_ROOT}")
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    return subprocess.run(
        cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=300
    )


def _link_and_run(compiler: str, cwd: Path, lls: list, exe: Path) -> int:
    link_cmd = ["clang", *map(str, lls), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(1, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=cwd, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link ({exe.name}):\n"
        f"{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    return _compile_file(compiler, tmp_path, src, ll), ll


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    comp, ll = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return _link_and_run(compiler, tmp_path, [ll], tmp_path / f"{name}_{compiler}")


def _run_imported(compiler: str, tmp_path: Path, name: str) -> int:
    """Compile helper and main as separate modules, link, run."""
    (tmp_path / "fnv_helper.ritz").write_text(IMPORT_HELPER)
    main_src = tmp_path / f"{name}.ritz"
    main_src.write_text(IMPORT_FORMS[name])
    lls = []
    if compiler == "ritz0":
        # ritz0 inlines imported modules into one .ll; compile main only.
        sources = [main_src]
    else:
        sources = [tmp_path / "fnv_helper.ritz", main_src]
    for src in sources:
        ll = tmp_path / f"{src.stem}_{compiler}.ll"
        comp = _compile_file(compiler, tmp_path, src, ll)
        assert comp.returncode == 0 and ll.exists(), (
            f"{compiler} failed to compile {src.name}:\n"
            f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
        )
        lls.append(ll)
    return _link_and_run(compiler, tmp_path, lls, tmp_path / f"{name}_{compiler}")


ALL_RUNNABLE = {**BROKEN_FORMS, **WORKING_FORMS}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ALL_RUNNABLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, ALL_RUNNABLE[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BROKEN_FORMS))
def test_ritz1_fn_name_as_value(ritz1_bin, tmp_path, name):
    """AGAST #1503. Before the fix: `unknown identifier 'double'`, exit 1."""
    assert _run("ritz1", tmp_path, name, BROKEN_FORMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING_FORMS))
def test_ritz1_already_working_forms(ritz1_bin, tmp_path, name):
    """Locals still shadow fns; direct calls are unchanged."""
    assert _run("ritz1", tmp_path, name, WORKING_FORMS[name]) == EXPECTED


@pytest.mark.integration
def test_ritz1_unknown_name_still_rejected(ritz1_bin, tmp_path):
    """The fn fallback must not swallow genuinely unknown identifiers."""
    comp, ll = _compile("ritz1", tmp_path, "unknown_name", UNKNOWN_NAME)
    assert comp.returncode != 0
    assert "unknown identifier 'no_such_fn'" in comp.stderr + comp.stdout
    assert not ll.exists()


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(IMPORT_FORMS))
def test_ritz1_imported_fn_as_value(ritz1_bin, tmp_path, name):
    """AGAST #1503 — imported fn used as a value needs an extern declaration."""
    assert _run_imported("ritz1", tmp_path, name) == EXPECTED
