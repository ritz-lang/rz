"""Regression tests for AGAST #1543 — ritz1 must parse enum variants that carry
a block of named fields (struct-style variants):

    pub enum Msg
        Navigate
            url: i32
        Stop

ritz0 has accepted this since #1282. ritz1's `enum_variant` rule only took
`IDENT NEWLINE` and `IDENT ( type )`, so the whole enum_def failed and the
item anchor-skip reported it as

    cannot parse item starting at 'enum Msg'

which is how tempest's lib/ipc.ritz died under ritz1. The fix adds
`IDENT NEWLINE INDENT struct_fields DEDENT`, reusing the struct field rule, and
records the variant name like the other forms so that qualified references
(`Msg.Stop`) keep their tag index.

Payload layout and construction of struct variants under ritz1 are out of
scope here (ritz1 user enums are tag-only; see #1295). These programs
therefore only declare struct variants and use the unit ones.

Every program returns 3 on success. ritz0 is the oracle.
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
    """Bring RITZ1_BIN up to date so we never assert against a stale grammar."""
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
            "could not build ritz1 for the struct-variant tests:\n"
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


# --- programs -----------------------------------------------------------------

# The ticket's repro, verbatim (tempest lib/ipc.ritz:61 shape).
REPRO = """\
pub enum Msg
    Navigate
        url: i32
    Stop

pub fn main() -> i32
    return 3
"""

# tempest's real shape: comments between variants, multi-field struct
# variants, struct variants last, and String / pointer field types.
TEMPEST_SHAPE = """\
pub enum BrowserToTabMsg
    # Navigation
    Navigate
        url: StrView
    Stop
    GoBack
    # Viewport
    SetViewport
        width: i32
        height: i32
        scale: f64
    Click
        x: i32
        y: i32
        button: u8
        target: *u8

pub fn main() -> i32
    return 3
"""

# Struct, tuple and bare variants mixed in one enum, inside a generic enum,
# and followed by more items (the enum must not swallow what comes after).
MIXED = """\
enum Shape
    Circle(i32)
    Rect
        w: i32
        h: i32
    Empty

enum Box<T>
    Full
        value: T
    Nothing

struct After
    v: i32

pub fn main() -> i32
    let a: After = After { v: 3 }
    return a.v
"""

# Variant indices must count struct variants too: `Msg.Stop` is tag 1 and
# `Msg.GoBack` tag 3, so a struct variant that failed to record would shift
# every later tag.
TAG_INDEX = """\
enum Msg
    Navigate
        url: i32
    Stop
    Resize
        w: i32
        h: i32
    GoBack

fn code(m: Msg) -> i32
    match m
        Stop => 1
        GoBack => 2
        _ => 100

pub fn main() -> i32
    return code(Msg.Stop) + code(Msg.GoBack)
"""

PROGRAMS = {
    "repro": REPRO,
    "tempest_shape": TEMPEST_SHAPE,
    "mixed": MIXED,
    "tag_index": TAG_INDEX,
}

# Malformed field blocks must still be rejected.
MALFORMED = {
    "field_missing_type": """\
enum Bad
    Navigate
        url:
    Stop

pub fn main() -> i32
    return 3
""",
    "field_missing_colon": """\
enum Bad
    Navigate
        url i32
    Stop

pub fn main() -> i32
    return 3
""",
}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(program)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    comp = subprocess.run(
        cmd, cwd=work, env=env, capture_output=True, text=True, timeout=300
    )
    return comp, ll, work


def _run(compiler: str, tmp_path: Path, name: str) -> int:
    """Compile PROGRAMS[name] with `compiler`, link, run, return the exit code."""
    comp, ll, work = _compile(compiler, tmp_path, name, PROGRAMS[name])
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = work / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_struct_enum_variants(ritz1_bin, tmp_path, name):
    """AGAST #1543. Before the fix these died with `cannot parse item`."""
    assert _run("ritz1", tmp_path, name) == 3


# TAG_INDEX alone cannot catch a struct variant that is parsed but never
# recorded: the match arms and `Msg.X` resolve through the same tracker, so
# every tag shifts consistently and the program still returns 3. The absolute
# tag is only visible in the IR (an `as i32` cast of an enum emits invalid IR
# in both compilers today, so it cannot be observed at run time). Navigate=0,
# Stop=1, Resize=2, GoBack=3: constructing GoBack must store tag 3.
TAG_VALUE = """\
enum Msg
    Navigate
        url: i32
    Stop
    Resize
        w: i32
        h: i32
    GoBack

pub fn main() -> i32
    let g: Msg = Msg.GoBack
    return 3
"""


@pytest.mark.integration
def test_ritz1_struct_variant_counts_toward_tag(ritz1_bin, tmp_path):
    comp, ll, _ = _compile("ritz1", tmp_path, "tag_value", TAG_VALUE)
    assert comp.returncode == 0 and ll.exists(), comp.stderr[-2000:]
    ir = ll.read_text()
    m = re.search(r"enum variant ctor.*?store i8 (\d+), ptr", ir, re.DOTALL)
    assert m, f"no enum variant ctor tag store in ritz1 IR:\n{ir[-2000:]}"
    assert m.group(1) == "3", f"Msg.GoBack got tag {m.group(1)}, expected 3"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_ritz1_rejects_malformed_struct_variant(ritz1_bin, tmp_path, name):
    comp, ll, _ = _compile("ritz1", tmp_path, name, MALFORMED[name])
    assert comp.returncode != 0, (
        f"ritz1 accepted malformed struct variant {name!r}:\n{comp.stdout[-1000:]}"
    )
    assert not ll.exists(), f"ritz1 wrote an artifact for malformed {name!r}"
