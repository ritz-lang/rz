"""Regression tests for AGAST #1466: ritz1 qualified enum variant constructors.

`Opt.Holds(x)` parses as a method call (EXPR_METHOD: receiver `Opt`, method
`Holds`).  ritz1's emit_expr_method only looked the receiver up as a local,
a global or an impl type, never as an enum, so every qualified payload
constructor failed "cannot determine receiver type for method call".  The
payload-less form `Opt.Vacant` (EXPR_MEMBER) already worked.

The fix lowers `E.V(x)` to the same constructor as unqualified `V(x)`
(#1797), and gives it the enum type wherever ritz1 infers an expression's
type: an untyped `let`, a `match` scrutinee, and the payload of an
enclosing `Err(...)` / `Some(...)` (that last one was broken for the
unqualified form too: the user-enum aggregate was stored as an i64).

Name resolution follows ritz0, the oracle:
  * a local (or global) named like the enum shadows it: `Opt.Holds(2)` is a
    method call on the local;
  * a variant wins over an impl method of the same name on the enum.

ritz0 rejects `Option.Some(x)` / `Result.Ok(x)` / `Option.None` ("Unknown
identifier"), and ritz1 has no generic-enum specialisation (#1295).  ritz1
must stop on those, and on a qualified ctor with the wrong arity, with an
error that names the source line.  It must never write IR that clang
rejects (`alloca %Option`).

Every RUNNABLE program exits 42 under ritz0 and must under ritz1.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0
from test_ritz1_builtin_struct_shadow import _run_pkg

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

EXPECTED = 42

OPT = """\
enum Opt
    Vacant
    Holds(i32)

fn val(o: Opt) -> i32
    match o
        Holds(v) => v
        Vacant => 100
"""

# `Result<i64, ArgError>`, read back through raw bytes: binding a user-enum
# payload out of `Err(e)` / `Some(x)` is a separate ritz1 bug
# (#2100), so the Err payload is checked in memory.  ritz0 and
# ritz1 share the layout: Result tag @0, ArgError @8 (tag @8, i64 @16).
RESULT_ARGERROR = """\
import ritzlib.result

enum ArgError
    Missing(i64)
    Bad

fn err_tag(r: *Result<i64, ArgError>) -> i32
    let base: *u8 = r as *u8
    if *base != 1
        return 0 - 1
    return *(base + 8) as i32

fn err_payload(r: *Result<i64, ArgError>) -> i64
    let p: *i64 = ((r as *u8) + 16) as *i64
    return *p
"""

RUNNABLE = {
    # The briefing's repro: an untyped let.
    "let_untyped_i32": OPT
    + """
pub fn main() -> i32
    let a = Opt.Holds(41)
    return val(a) + 1
""",
    "let_typed_i32": OPT
    + """
pub fn main() -> i32
    let a: Opt = Opt.Holds(40)
    var b: Opt = Opt.Vacant
    b = Opt.Holds(2)
    return val(a) + val(b)
""",
    # Passed straight to a call: the param's type is the context.
    # Qualified ctors as `match` arm values: the arms fix the phi's type.
    "match_arm_values": OPT
    + """
fn pick(k: i32) -> Opt
    let o = match k
        0 => Opt.Vacant
        1 => Opt.Holds(40)
        _ => Opt.Holds(k)
    o

pub fn main() -> i32
    return val(pick(1)) + val(pick(2)) + (val(pick(0)) - 100)
""",
    "call_arg": OPT
    + """
pub fn main() -> i32
    return val(Opt.Holds(30)) + val(Opt.Holds(12))
""",
    # Tail expression and `return` of a fn returning the enum.
    "return_value": OPT
    + """
fn mk(x: i32) -> Opt
    if x < 0
        return Opt.Vacant
    if x == 0
        return Opt.Holds(1)
    Opt.Holds(x + 1)

pub fn main() -> i32
    return val(mk(40)) + val(mk(0)) + (val(mk(0 - 1)) - 100)
""",
    # The ticket's shape with an i64 payload: `return Err(E.V(x))`.
    "return_err_i64": RESULT_ARGERROR
    + """
fn f(x: i64) -> Result<i64, ArgError>
    if x == 0
        return Err(ArgError.Missing(40))
    if x < 0
        return Err(ArgError.Bad)
    return Ok(x)

pub fn main() -> i32
    let m: Result<i64, ArgError> = f(0)
    let b: Result<i64, ArgError> = f(0 - 1)
    if err_tag(@m) != 0 or err_tag(@b) != 1
        return 1
    var r: i64 = 3
    match f(2)
        Ok(n) => r = err_payload(@m) + n
        Err(e) => r = 3
    return r as i32
""",
    # The unqualified form had the same Err-payload bug.
    "return_err_unqualified": RESULT_ARGERROR
    + """
fn f(x: i64) -> Result<i64, ArgError>
    if x == 0
        return Err(Missing(42))
    return Ok(x)

pub fn main() -> i32
    let m: Result<i64, ArgError> = f(0)
    if err_tag(@m) != 0
        return 1
    return err_payload(@m) as i32
""",
    # A payload wider than i32, with its high bits significant.
    "i64_payload": """\
enum Big
    Nothing
    Num(i64)

fn get(b: Big) -> i64
    match b
        Num(n) => n
        Nothing => 0

pub fn main() -> i32
    let big: i64 = 1 << 40
    let a = Big.Num(big + 42)
    let b: Big = Big.Num(big)
    return (get(a) - get(b)) as i32
""",
    # A struct payload: built from a literal, from a local and from a call.
    "struct_payload": """\
struct Pt
    x: i32
    y: i32

enum Shape
    Empty
    Dot(Pt)

fn mkpt(x: i32, y: i32) -> Pt
    Pt { x: x, y: y }

fn sum(s: Shape) -> i32
    match s
        Dot(p) => p.x + p.y
        Empty => 1000

pub fn main() -> i32
    let p: Pt = Pt { x: 15, y: 7 }
    let a = Shape.Dot(Pt { x: 10, y: 11 })
    let b: Shape = Shape.Dot(p)
    return sum(a) + sum(b) + sum(Shape.Dot(mkpt(0, 0))) - 1 + (sum(Shape.Empty) - 1000)
""",
    # A Some(...) / Ok(...) wrapping a qualified ctor (the aggregate payload).
    "inside_some": OPT
    + """
import ritzlib.option

pub fn main() -> i32
    let o: Option<Opt> = Some(Opt.Holds(40))
    # Option<Opt> is { i8, [8 x i8] } in both: Opt's tag @1, its i32 @5.
    let base: *u8 = @o as *u8
    if *base != 0 or *(base + 1) != 1
        return 1
    return (*(base + 5) as i32) + 2
""",
    # ritz0: a variant wins over an impl method of the same name.
    "variant_beats_impl_method": OPT
    + """
impl Opt
    fn Holds(x: i32) -> Opt
        return Opt.Vacant

pub fn main() -> i32
    let a: Opt = Opt.Holds(42)
    return val(a)
""",
    # ritz0: a local named like the enum shadows it.
    "local_shadows_enum": """\
enum Opt
    Vacant
    Holds(i32)

struct S
    v: i32

impl S
    fn Holds(self: *S, x: i32) -> i32
        return self.v + x

pub fn main() -> i32
    var Opt: S = S { v: 40 }
    return Opt.Holds(2)
""",
}

# ritz0 rejects these, so ritz1's result is checked against the value the
# program computes by hand (42).  ritz0: `match <rvalue enum>` is "Match on
# type %enum.Opt not yet supported" and a static method on an enum impl is
# "Unknown identifier: Opt" (#2101).
RITZ1_ONLY = {
    # As a match scrutinee, including the qualified pattern form.
    "match_scrutinee": OPT
    + """
pub fn main() -> i32
    var r: i32 = 0
    match Opt.Holds(40)
        Opt.Holds(v) => r = v
        Opt.Vacant => r = 1
    match Opt.Vacant
        Holds(v) => r = 0
        Vacant => r = r + 2
    return r
""",
    # The unqualified ctor as a scrutinee had the same gap.
    "match_scrutinee_unqualified": OPT
    + """
pub fn main() -> i32
    var r: i32 = 0
    match Holds(41)
        Holds(v) => r = v + 1
        Vacant => r = 1
    return r
""",
    # ...but other impl methods on the enum still dispatch statically.
    "impl_static_method_on_enum": OPT
    + """
impl Opt
    fn make(x: i32) -> Opt
        return Opt.Holds(x + 2)

pub fn main() -> i32
    let a: Opt = Opt.make(40)
    return val(a)
""",
}

# The ticket's own StrView repro, built as a package (it imports ritzlib, so
# every imported module has to be compiled and linked).  #1295 (open) owns
# StrView payload MATCHING, so nothing here binds the payload; construction
# (`let` and `return Err(...)`) must compile, link and run.
STRVIEW_REPRO = """\
import ritzlib.io
import ritzlib.result
import ritzlib.strview

pub enum ArgError
    Missing(StrView)

fn f(s: StrView) -> Result<i64, ArgError>
    if s.len == 0
        return Err(ArgError.Missing(s))
    return Ok(3)

pub fn main() -> i32
    let e = ArgError.Missing(strview_from_cstr(c"x"))
    var r: i64 = 0
    match f(strview_from_cstr(c""))
        Ok(n) => r = 100
        Err(e2) => prints("err\\n")
    match f(strview_from_cstr(c"ab"))
        Ok(n) => r = r + n + 39
        Err(e2) => r = 200
    return r as i32
"""

# Forms ritz1 does not lower: each a located error, no output written.
# (name -> (program, ":line:", message fragment)).
FAIL_CLOSED = {
    "option_some": (
        """\
import ritzlib.option

pub fn main() -> i32
    let a: Option<i64> = Option.Some(42)
    return 0
""",
        ":4:",
        "generic enum",
    ),
    "result_ok": (
        """\
import ritzlib.result

fn h(x: i64) -> Result<i64, i32>
    return Result.Ok(x)

pub fn main() -> i32
    return 0
""",
        ":4:",
        "generic enum",
    ),
    "result_err": (
        """\
import ritzlib.result

fn h(x: i64) -> Result<i64, i32>
    return Result.Err(3 as i32)

pub fn main() -> i32
    return 0
""",
        ":4:",
        "generic enum",
    ),
    # The payload-less member form wrote `alloca %Option` (clang rejects).
    "option_none_member": (
        """\
import ritzlib.option

pub fn main() -> i32
    let a: Option<i64> = Option.None
    return 0
""",
        ":4:",
        "generic enum",
    ),
    "user_generic_enum": (
        """\
enum Box<T>
    Empty
    Full(T)

pub fn main() -> i32
    let b = Box.Full(3)
    return 0
""",
        ":6:",
        "generic enum",
    ),
    "too_many_args": (
        OPT
        + """
pub fn main() -> i32
    let a = Opt.Holds(1, 2)
    return 0
""",
        ":11:",
        "takes 1 payload",
    ),
    "missing_payload": (
        OPT
        + """
pub fn main() -> i32
    let a = Opt.Holds()
    return 0
""",
        ":11:",
        "takes 1 payload",
    ),
    "unit_variant_with_payload": (
        OPT
        + """
pub fn main() -> i32
    let a = Opt.Vacant(3)
    return 0
""",
        ":11:",
        "takes no payload",
    ),
}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
        proc = subprocess.run(
            cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
        )
    return proc, ll


def _link(compiler: str, tmp_path: Path, name: str, ll: Path) -> Path:
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(1, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link ({name}):\n{link.stderr[-2000:]}"
    )
    return exe


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    comp, ll = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = _link(compiler, tmp_path, name, ll)
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RUNNABLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    assert _run("ritz0", tmp_path, name, RUNNABLE[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RUNNABLE))
def test_ritz1_qualified_variant_ctor(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, RUNNABLE[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_ONLY))
def test_ritz1_only(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, RITZ1_ONLY[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_strview_repro(ritz1_bin, tmp_path, compiler):
    assert _run_pkg(compiler, tmp_path, "strview_repro", STRVIEW_REPRO) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FAIL_CLOSED))
def test_ritz1_fails_closed(ritz1_bin, tmp_path, name):
    program, needle, msg = FAIL_CLOSED[name]
    comp, ll = _compile("ritz1", tmp_path, name, program)
    assert comp.returncode != 0, f"ritz1 accepted {name}"
    assert not ll.exists(), f"ritz1 wrote output for {name}"
    err = comp.stderr
    assert needle in err and msg in err, f"unlocated or wrong error for {name}:\n{err}"
