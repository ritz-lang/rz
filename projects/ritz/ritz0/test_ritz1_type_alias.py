"""Regression tests for AGAST #1475 — ritz1 must accept `type Name = T` items.

ritz0 has always parsed type aliases (`TypeAlias`, transparent: the alias IS
the target type). ritz1's grammar had no alternative for them in `item`, so
any module declaring one died with

    alias.ritz:1:1: cannot parse item starting at 'type Code'

That was every ritz1 failure in goliath (`pub type ErrorCode = i32`,
`pub type EntryKind = u8`), plus spire, tempest and iris, and every package
importing those modules.

The fix resolves aliases in the parser: `type_named` substitutes the target
type's parse state, so nothing downstream (emitter, monomorph) ever sees an
alias name. Aliases are recorded in a process-wide table; when the first
parse of a compile sees any, the driver re-parses with the table populated so
use-before-declaration and aliases declared in an imported module (which is
parsed AFTER its importer) resolve too.

Every runnable program returns 3 when the alias resolved to the right type and
something else (or a compile error) otherwise. ritz0 is run as the oracle.
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
            "could not build ritz1 for the type alias tests:\n"
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
#
# Each entry: name -> (main program, {sibling module file: source}).

# The ticket's repro, verbatim.
REPRO = """\
type Code = i32

pub fn main() -> i32
    let c: Code = 3
    return c
"""

# goliath's spelling, and the alias as a param/return type.
PUB_ALIAS = """\
pub type ErrorCode = i32

fn code_of(x: ErrorCode) -> ErrorCode
    return x + 1

pub fn main() -> i32
    let c: ErrorCode = code_of(2)
    return c
"""

# Alias of a struct: variable, field access, param by pointer. `Decoy`
# (no x/y fields; its `*Decoy` field leaves `Decoy` as the parser's last
# struct name) is parsed between the alias and its uses, so resolving `P`
# must replay the alias's own struct name rather than inherit the stale one.
STRUCT_ALIAS = """\
struct Point
    x: i32
    y: i32

type P = Point

struct Decoy
    a: i64
    next: *Decoy

fn sum(p: *P) -> i32
    return p.x + p.y

pub fn main() -> i32
    var p: P = Point { x: 1, y: 2 }
    return sum(@p)
"""

# Alias of a pointer type: member access through the alias must still GEP
# into the pointee struct.
POINTER_ALIAS = """\
struct Point
    x: i32
    y: i32

type PointRef = *Point

struct Decoy
    a: i64
    next: *Decoy

fn first(p: PointRef) -> i32
    return p.x

pub fn main() -> i32
    var pt: Point = Point { x: 3, y: 9 }
    let r: PointRef = @pt
    return first(r)
"""

# A narrow alias (goliath's EntryKind) as a struct field and a cast target:
# 259 as Kind truncates to 3 only if Kind really is u8.
NARROW_FIELD_ALIAS = """\
pub type Kind = u8

struct Entry
    kind: Kind
    size: i64

pub fn main() -> i32
    let wide: i32 = 259
    let e: Entry = Entry { kind: wide as Kind, size: 0 }
    return e.kind as i32
"""

# Used before it is declared (ritz0 allows item order to be free).
FORWARD_USE = """\
fn half(x: Code) -> Code
    return x / 2

type Code = i64

pub fn main() -> i32
    return half(6) as i32
"""

# Alias of an alias.
ALIAS_CHAIN = """\
type Inner = i32
type Outer = Inner

pub fn main() -> i32
    let o: Outer = 3
    return o
"""

# Alias declared in an imported module, both whole-module and selective
# imports (goliath: `import goliath.error { ErrorCode, ... }`). The importer is
# parsed before the import, so this needs the re-parse.
CODES_MODULE = """\
pub type Code = i32

pub struct Pair
    a: i32
    b: i32

pub type PairAlias = Pair

pub fn make_code(x: i32) -> Code
    return x
"""

IMPORTED_ALIAS = """\
import codes

pub fn main() -> i32
    let c: Code = make_code(2)
    return c + 1
"""

IMPORTED_STRUCT_ALIAS = """\
import codes

pub fn main() -> i32
    let c: Code = make_code(2)
    var p: PairAlias = Pair { a: 1, b: c }
    return p.a + p.b
"""

IMPORTED_ALIAS_SELECTIVE = """\
import codes { Code, make_code }

fn twice(x: Code) -> Code
    return x * 2

pub fn main() -> i32
    return twice(make_code(1)) + 1
"""

PROGRAMS = {
    "repro": (REPRO, {}),
    "pub_alias": (PUB_ALIAS, {}),
    "struct_alias": (STRUCT_ALIAS, {}),
    "pointer_alias": (POINTER_ALIAS, {}),
    "narrow_field_alias": (NARROW_FIELD_ALIAS, {}),
    "forward_use": (FORWARD_USE, {}),
    "alias_chain": (ALIAS_CHAIN, {}),
    "imported_alias": (IMPORTED_ALIAS, {"codes.ritz": CODES_MODULE}),
    "imported_struct_alias": (IMPORTED_STRUCT_ALIAS, {"codes.ritz": CODES_MODULE}),
    "imported_alias_selective": (
        IMPORTED_ALIAS_SELECTIVE,
        {"codes.ritz": CODES_MODULE},
    ),
}

# ritz0 lowers an alias of a struct (or of a pointer to one) to i8* and fails
# to compile these (AGAST #1537), so it is no oracle for them yet. Strict
# xfail: when #1537 lands they XPASS and must be deleted from this set.
RITZ0_STRUCT_ALIAS_BROKEN = {"struct_alias", "pointer_alias", "imported_struct_alias"}

# Must still be rejected, and must not leave an artifact behind.
MALFORMED = {
    "missing_name": "type = i32\n\npub fn main() -> i32\n    return 3\n",
    "missing_target": "type Code =\n\npub fn main() -> i32\n    return 3\n",
    "missing_assign": "type Code i32\n\npub fn main() -> i32\n    return 3\n",
}


def _compile_one(compiler: str, work: Path, src: Path, ll: Path):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    return subprocess.run(
        cmd, cwd=work, env=env, capture_output=True, text=True, timeout=300
    )


def _compile(compiler: str, tmp_path: Path, name: str, program: str, siblings: dict):
    """Compile main.ritz (and each sibling module, which both compilers emit as
    its own object: imported fns are only declared in the importer's IR).

    Returns (main's CompletedProcess, main.ll, work dir, sibling .ll paths).
    """
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    for fname, text in siblings.items():
        (work / fname).write_text(text)
    src = work / "main.ritz"
    src.write_text(program)
    ll = work / "main.ll"
    comp = _compile_one(compiler, work, src, ll)
    sibling_lls = []
    for fname in siblings:
        s_ll = work / (Path(fname).stem + ".ll")
        s_comp = _compile_one(compiler, work, work / fname, s_ll)
        assert s_comp.returncode == 0 and s_ll.exists(), (
            f"{compiler} failed to compile sibling {fname} for {name}:\n"
            f"{s_comp.stdout[-2000:]}\n{s_comp.stderr[-2000:]}"
        )
        sibling_lls.append(str(s_ll))
    return comp, ll, work, sibling_lls


def _run(compiler: str, tmp_path: Path, name: str) -> int:
    """Compile PROGRAMS[name] with `compiler`, link, run, return the exit code."""
    program, siblings = PROGRAMS[name]
    comp, ll, work, sibling_lls = _compile(compiler, tmp_path, name, program, siblings)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = work / "main"
    link_cmd = ["clang", str(ll), *sibling_lls, "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(request, tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    if name in RITZ0_STRUCT_ALIAS_BROKEN:
        request.applymarker(
            pytest.mark.xfail(
                strict=True, reason="AGAST #1537: ritz0 struct alias -> i8*"
            )
        )
    assert _run("ritz0", tmp_path, name) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_type_alias(ritz1_bin, tmp_path, name):
    """AGAST #1475. Before the fix each was `cannot parse item starting at 'type ...'`."""
    assert _run("ritz1", tmp_path, name) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_ritz1_rejects_malformed_alias(ritz1_bin, tmp_path, name):
    comp, ll, _, _ = _compile("ritz1", tmp_path, name, MALFORMED[name], {})
    assert comp.returncode != 0, (
        f"ritz1 accepted malformed alias {name!r}:\n{comp.stdout[-1000:]}"
    )
    assert not ll.exists(), f"ritz1 wrote an artifact for malformed {name!r}"
