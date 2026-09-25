"""AGAST #1440: a struct's layout comes from its source definition.

THE DEFECT

ritz1's emitter carried hard-coded copies of ~20 struct layouts (NFA,
Transition, ArgParser, LineBounds, String, the Vec$/Span$ monomorphs, ...)
in two places: `emit_builtin_struct_types` (the `%Name = type {...}` strings)
and `register_builtin_structs` (the field table used for member lookup). Both
were installed before the module's own structs and both won:

  * `register_builtin_structs` prepended its StructDefs to `m.structs`, so
    `find_struct("Transition")` returned the copy, not the program's struct;
  * `emit_builtin_struct_types` marked each name emitted, so the program's
    `%Transition = type {...}` was never written.

So any program naming a struct `Transition`, `NFA`, `ArgParser`, `String`,
`LineBounds`, ... got ritz1's layout instead of its own. Fields the copy did
not have were unreadable ("unhandled EXPR_MEMBER"), and fields it had in a
different position were silently read and written at the wrong offset.

It also meant every edit to one of those structs (`struct NFA` in
ritz1/src/nfa.ritz, `struct ArgParser` in ritzlib/args.ritz, ...) needed a
matching hand-edit in two places in emitter.ritz, or ritz1 would silently
drop stores to the new field (#1436 hit exactly this).

The fix deletes the copies: ritz1 already resolves imports and monomorphises
generic structs, so every layout is available from source. Removing them
exposed two monomorph gaps the Vec$ copies had been hiding (instantiations
named only through `@&Vec<T>` params / specialised fns were never created,
and a cloned `data: *T` lost its pointee, breaking `v.data + i` stride).

One type stays compiler-supplied: `Span$u8`, which bare string literals
lower to. It is added only when the source lacks it; a source `Span$u8`
wins, and one whose layout is not `{ ptr, i64 }` is an error.

THE TESTS

  * user-struct: a program defines a struct with a formerly-built-in name and
    its OWN fields; it must compile and compute the right answer.
  * layout: a program defines `struct Transition` with the built-in's field
    NAMES in a different ORDER; the first declared field must sit at offset 0.
    Name-lookup alone cannot pass this — only the source layout can.
  * import: programs that take these structs from ritzlib (ArgParser, String,
    Vec<LineBounds>) must still compile and run — the copies are not needed.
  * static: emitter*.ritz contains no hard-coded `%Name = type` layout for a
    struct that has a source definition.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ1_SRC = RITZ_ROOT / "ritz1" / "src"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _build_ritz1() -> None:
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
            "could not build ritz1 for the built-in struct shadow tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


def _build_runtime_start() -> None:
    """RITZ_START is gitignored; build it rather than assume it exists."""
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


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
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


def _run_pkg(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Build `program` as a package via build.py (which compiles and links
    every transitively imported module), run it, return the exit code."""
    pkg = tmp_path / f"{name}_{compiler}"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "main.ritz").write_text(program)
    (pkg / "ritz.toml").write_text(
        f'[package]\nname = "{name}"\nversion = "0.1.0"\n\n'
        '[build]\ntarget = "x86_64-linux"\n'
    )
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [
            "python3",
            str(RITZ_ROOT / "build.py"),
            "build",
            str(pkg),
            "--no-cache",
            "--compiler",
            compiler,
        ],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    exe = pkg / "build" / "debug" / name
    assert proc.returncode == 0 and exe.exists(), (
        f"{compiler} failed to build {name}:\n"
        f"{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


# Every non-generic name ritz1 used to hard-code. A user program may name a
# struct any of these; none is reserved by the language.
FORMER_BUILTINS = [
    "Transition",
    "NFA",
    "NFAState",
    "NFAFragment",
    "TokenPattern",
    "LineBounds",
    "ArgParser",
    "OptDef",
    "PosDef",
    "String",
]


def _user_struct_program(name: str) -> str:
    # Field names none of the old copies had, so lookup must use this struct.
    # `gamma` is then read back RAW from offset 8, where this layout puts it.
    # Every old copy had its third member at offset 16 (or no third member),
    # so a stale `%{name} = type` string fails here even when the field table
    # is right — OptDef/PosDef/String had exactly that split: no registered
    # fields, but a hard-coded LLVM type.
    return f"""\
struct {name}
    alpha: i32
    beta: u8
    gamma: i64

fn main() -> i32
    var t: {name}
    t.alpha = 30
    t.beta = 5
    t.gamma = 7
    let base: *u8 = @t as *u8
    let gp: *i64 = (base + 8) as *i64
    return t.alpha + t.beta as i32 + *gp as i32
"""


# The old %Transition was { kind, char_lo, char_hi, from_state, to_state }, all
# i64. Declaring to_state FIRST means a correct compiler stores it at offset 0.
# With the copy shadowing the source, `t.to_state` resolved to member 4
# (offset 32) and the raw read at offset 0 saw `kind` (= 1) instead.
TRANSITION_REORDERED = """\
struct Transition
    to_state: i64
    kind: i64

fn main() -> i32
    var t: Transition
    t.to_state = 42
    t.kind = 1
    let p: *i64 = @t as *i64
    return *p as i32
"""


@pytest.mark.integration
@pytest.mark.parametrize("name", FORMER_BUILTINS)
def test_ritz0_oracle_user_struct(tmp_path, name):
    assert _run("ritz0", tmp_path, name, _user_struct_program(name)) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", FORMER_BUILTINS)
def test_ritz1_user_struct_uses_its_own_fields(ritz1_bin, tmp_path, name):
    """A program's own `struct <name>` wins; no field of it is unknown."""
    assert _run("ritz1", tmp_path, name, _user_struct_program(name)) == 42


@pytest.mark.integration
def test_ritz0_oracle_transition_layout(tmp_path):
    assert _run("ritz0", tmp_path, "trans_layout", TRANSITION_REORDERED) == 42


@pytest.mark.integration
def test_ritz1_transition_uses_source_layout(ritz1_bin, tmp_path):
    """The ticket's acceptance case: same field names, different layout."""
    assert _run("ritz1", tmp_path, "trans_layout", TRANSITION_REORDERED) == 42


# --- the copies are not needed: imported layouts still work ---------------

ARGPARSER_IMPORTED = """\
import ritzlib.memory
import ritzlib.args

fn main() -> i32
    var p: ArgParser
    p.option_count = 3
    p.pos_def_count = 4
    p.positional_count = 35
    return p.option_count + p.pos_def_count + p.positional_count
"""

STRING_IMPORTED = """\
import ritzlib.memory
import ritzlib.string

fn main() -> i32
    var s: String = string_new()
    string_push(@s, 65)
    string_push(@s, 66)
    let n: i64 = string_len(@s)
    let b: u8 = string_get(@s, 1)
    return n as i32 + b as i32 - 26
"""

VEC_LINEBOUNDS_IMPORTED = """\
import ritzlib.memory
import ritzlib.gvec

fn main() -> i32
    var v: Vec<LineBounds> = vec_new<LineBounds>()
    var a: LineBounds
    a.start = 10
    a.length = 2
    var b: LineBounds
    b.start = 30
    b.length = 12
    vec_push<LineBounds>(@v, a)
    vec_push<LineBounds>(@v, b)
    let second: *LineBounds = v.data + 1
    return second.length as i32 + v.len as i32 * 15 - 0
"""

# No annotation anywhere names `Vec$i16`: the only place it appears is the
# return type of the specialised `vec_new$i16`. So the struct instantiation
# has to be collected from specialised fns, and `v.data + 1` must stride by
# sizeof(i16), which needs the cloned `data: *T` to keep its pointee.
VEC_I16_INFERRED = """\
import ritzlib.memory
import ritzlib.gvec

fn main() -> i32
    var v = vec_new<i16>()
    vec_push<i16>(@v, 5)
    vec_push<i16>(@v, 40)
    # vec_push$i16 stores at `v.data + len`, striding by the FIELD's pointee.
    # Reading through a local `*i16` strides by 2 regardless, so a lost
    # pointee (stride 8) is caught instead of cancelling itself out.
    let base: *i16 = v.data
    let p: *i16 = base + 1
    return *p as i32 + v.len as i32
"""


def _vec_user_struct_program(name: str, annotated: bool) -> str:
    """Vec<T> for a user struct T, read back through a `@&Vec<T>` param.

    A one-letter struct name (`P`) mangles to `Vec$P`, which has exactly the
    shape of the unsubstituted placeholder `Vec$T`. Monomorph must not
    mistake it for one (#1487 found 988bd60 doing exactly that). `second.b`
    at `data + 1` also checks the stride is sizeof(T) = 16.
    """
    decl = f"var w: Vec<{name}> = " if annotated else "var w = "
    return f"""\
import ritzlib.memory
import ritzlib.gvec

struct {name}
    a: i64
    b: i64

fn second_b(w: @&Vec<{name}>) -> i64
    let second: *{name} = w.data + 1
    second.b

fn main() -> i32
    {decl}vec_new<{name}>()
    var x: {name}
    x.a = 1
    x.b = 2
    var y: {name}
    y.a = 3
    y.b = 40
    vec_push<{name}>(@w, x)
    vec_push<{name}>(@w, y)
    return second_b(@&w) as i32 + w.len as i32
"""


IMPORTED = {
    "argparser": (ARGPARSER_IMPORTED, 42),
    "string": (STRING_IMPORTED, 42),
    "vec_linebounds": (VEC_LINEBOUNDS_IMPORTED, 42),
    "vec_i16_inferred": (VEC_I16_INFERRED, 42),
    # One-letter names collide with the `Vec$T` placeholder shape; `Pt` is
    # the control.
    "vec_user_p_annotated": (_vec_user_struct_program("P", True), 42),
    "vec_user_p_inferred": (_vec_user_struct_program("P", False), 42),
    "vec_user_pt_annotated": (_vec_user_struct_program("Pt", True), 42),
    "vec_user_pt_inferred": (_vec_user_struct_program("Pt", False), 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(IMPORTED))
def test_ritz0_oracle_imported(tmp_path, name):
    program, want = IMPORTED[name]
    assert _run_pkg("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(IMPORTED))
def test_ritz1_imported_layout(ritz1_bin, tmp_path, name):
    program, want = IMPORTED[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == want


# --- Span$u8: the one type ritz1 supplies itself ---------------------------
# A bare "..." literal lowers to a %Span$u8 aggregate, so ritz1 must provide
# the type when the source does not. When the source does (ritzlib's
# `struct Span<T>` at u8), the source wins; a layout the literal lowering
# cannot honour is an error, never a silent shadow.

STRING_LITERAL_NO_IMPORTS = """\
fn main() -> i32
    let s = "hello, world"
    return s.len as i32 + 30
"""

SPAN_FROM_SOURCE = """\
import ritzlib.memory
import ritzlib.span

fn main() -> i32
    var sp: Span<u8>
    sp.len = 30
    let s: StrView = "hello, world"
    return sp.len as i32 + s.len as i32
"""

SPAN_MISMATCHED = """\
struct Span<T>
    len: i64
    ptr: *T

fn main() -> i32
    var s: Span<u8>
    s.len = 3
    let lit: StrView = "hi"
    return s.len as i32
"""


@pytest.mark.integration
def test_ritz1_supplies_string_literal_type(ritz1_bin, tmp_path):
    assert _run("ritz1", tmp_path, "lit", STRING_LITERAL_NO_IMPORTS) == 42


@pytest.mark.integration
def test_ritz1_source_span_u8_wins(ritz1_bin, tmp_path):
    assert _run_pkg("ritz1", tmp_path, "span_src", SPAN_FROM_SOURCE) == 42


@pytest.mark.integration
def test_ritz1_rejects_span_u8_it_cannot_honour(ritz1_bin, tmp_path):
    src = tmp_path / "span_bad.ritz"
    src.write_text(SPAN_MISMATCHED)
    ll = tmp_path / "span_bad.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode != 0, (
        "ritz1 accepted a Span$u8 that string literals cannot use"
    )
    assert "Span$u8" in proc.stderr, proc.stderr[-2000:]


# --- static: no second copy of a source layout ----------------------------


def _source_struct_names() -> set[str]:
    names = set()
    for root in (RITZ1_SRC, RITZ_ROOT / "ritzlib"):
        for path in root.rglob("*.ritz"):
            names.update(re.findall(r"^struct (\w+)", path.read_text(), re.M))
    return names


@pytest.mark.unit
def test_emitter_has_no_hardcoded_source_layouts():
    """A `%Name = type {...}` string for a struct that has a source definition
    is a second copy of that layout, and the two drift (#1436, #1440)."""
    defined = _source_struct_names()
    # Generic templates count too: `Vec$u8` is a copy of `struct Vec<T>`.
    offenders = []
    for path in sorted(RITZ1_SRC.glob("emitter*.ritz")):
        for m in re.finditer(r'c"%(\w+)(?:\$\w+)? = type \{', path.read_text()):
            if m.group(1) in defined:
                offenders.append(f"{path.name}: {m.group(0)}")
    assert not offenders, "hard-coded struct layouts in ritz1:\n" + "\n".join(offenders)
