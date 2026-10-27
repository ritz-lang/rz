"""Regression tests for AGAST #1652 / #1672 / #1754: an `@&T` value used where a `*T`
is expected.

ritz1 lowers `*T` as i64 (its value model) but `@&T` as `ptr`.  When an
`@&T` local (or an `@&v` expression) flows into a `*T` slot, the `ptr` must be
ptrtoint'd, or clang rejects the IR ("defined with type 'ptr' but expected
'i64'").  #1644 fixed the free-function call argument; these are the other
`*T` sinks:

* `let p: *S = s` (typed let) and `p = s` (assignment to a `*S` local)
* `s as *S` (the cast was a no-op that left a `ptr`), also `as i64`
* `return s` / tail `s` from a `-> *S` fn
* `h.p = s` (store into a `*S` struct field, through a pointer or a local)

Each program exits 42 only if the pointer that lands in the `*T` slot still
aliases the caller's struct (writes through it are seen by the caller).
ritz0 is the oracle.  The call-argument and by-value `*b` deref forms from the
tickets already work on main (#1644) and are pinned in WORKING.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


# Shared prelude: `S` plus a `*S` consumer that writes through its pointer.
PRELUDE = """\
struct S
    a: i32

struct H
    p: *S

struct O
    h: H

fn bump(s: *S) -> i32
    s.a = s.a + 2
    s.a

fn bump_mut(s: @&S) -> i32
    s.a = s.a + 2
    s.a
"""

# --- `let` / assignment into a `*S` local -------------------------------------

LET_ASSIGN = {
    # #1652: `let p: *S = s` stored the ptr as `store i64 <ptr>`.
    "let_typed": """\
fn f(s: @&S) -> i32
    let p: *S = s
    p.a = p.a + 2
    0

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
    s.a
""",
    # `p = s` after the declaration takes the emit_assign local path.
    "assign_local": """\
fn f(s: @&S) -> i32
    var p: *S = null
    p = s
    bump(p)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    # `@&v` straight into a `*S` let.
    "let_from_addr_mut": """\
pub fn main() -> i32
    var s: S = S { a: 40 }
    let p: *S = @&s
    bump(p)
""",
}

# --- `as *S` / `as i64` casts --------------------------------------------------

CAST = {
    # #1652: `s as *S` was a no-op, leaving a `ptr` in an i64 call arg.
    "cast_call_arg": """\
fn f(s: @&S) -> i32
    bump(s as *S)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    "cast_let": """\
fn f(s: @&S) -> i32
    let p: *S = s as *S
    bump(p)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    # The cast result is an integer address equal to the caller's `@s`.
    "cast_to_int": """\
fn addr(s: @&S) -> i64
    (s as *S) as i64

pub fn main() -> i32
    var s: S = S { a: 40 }
    let got: i64 = addr(@&s)
    let p: *S = @s
    if got != p as i64
        return 1
    42
""",
}

# --- return / field store -----------------------------------------------------

RET_FIELD = {
    "return_stmt": """\
fn as_ptr(s: @&S) -> *S
    return s

pub fn main() -> i32
    var s: S = S { a: 40 }
    bump(as_ptr(@&s))
""",
    "return_tail": """\
fn as_ptr(s: @&S) -> *S
    s

pub fn main() -> i32
    var s: S = S { a: 40 }
    bump(as_ptr(@&s))
""",
    # Tail return from an impl method (emit_impl_method's own tail path).
    "return_tail_method": """\
struct W
    k: i64

impl W
    fn pick(self: *W, s: @&S) -> *S
        s

pub fn main() -> i32
    var s: S = S { a: 40 }
    var w: W
    let wp: *W = @w
    bump(wp.pick(@&s))
""",
    # Field store through a `*H`.
    "field_store_via_ptr": """\
fn hold(h: *H, s: @&S) -> i32
    h.p = s
    0

pub fn main() -> i32
    var s: S = S { a: 40 }
    var h: H
    hold(@h, @&s)
    bump(h.p)
""",
    # The emit_assign member path: a global struct field, and nested fields
    # (through a pointer and in a local).
    "field_store_global": """\
var G: H

fn f(s: @&S) -> i32
    G.p = s
    bump(G.p)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    "field_store_nested_via_ptr": """\
fn f(o: *O, s: @&S) -> i32
    o.h.p = s
    bump(o.h.p)

pub fn main() -> i32
    var s: S = S { a: 40 }
    var o: O
    f(@o, @&s)
""",
    "field_store_nested_local": """\
fn f(s: @&S) -> i32
    var o: O
    o.h.p = s
    bump(o.h.p)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    # Field store into a local struct.
    "field_store_local": """\
fn f(s: @&S) -> i32
    var h: H
    h.p = s
    bump(h.p)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
}

# --- forms that already worked on main (#1644); pinned -------------------------

WORKING = {
    # #1652's original repro: call argument into a `*T` param.
    "call_arg": """\
fn f(s: @&S) -> i32
    bump(s)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    # #1672 repro 1.
    "call_arg_extra_args": """\
struct G
    len: i64

fn app(b: *G, len: i64) -> i32
    b.len = b.len + len
    return 0

fn via_mut(b: @&G) -> i32
    return app(b, 3)

pub fn main() -> i32
    var g: G
    g.len = 39
    via_mut(@&g)
    g.len as i32
""",
    # #1672 repro 2: by-value deref of an `@&` struct param.
    "deref_by_value": """\
struct Buffer
    pos: i64
    end: i64

fn f(b: @&Buffer) -> i64
    let start: Buffer = *b
    b.pos = 0
    return start.pos + start.end

pub fn main() -> i32
    var b: Buffer = Buffer { pos: 40, end: 2 }
    let r: i64 = f(@&b)
    if b.pos != 0
        return 1
    r as i32
""",
    # `@s` is already i64: a `*S` let must not ptrtoint it again.
    "let_from_addr": """\
pub fn main() -> i32
    var s: S = S { a: 40 }
    let p: *S = @s
    bump(p)
""",
}

# --- AGAST #1754: the leftovers ----------------------------------------------

# A local initialised from an `@&S` ident must stay a struct pointer, so
# `q.a` resolves (was "unhandled EXPR_MEMBER").
LOCAL_FROM_MUT_REF = {
    "let_untyped": """\
fn f(s: @&S) -> i32
    let q = s
    q.a = q.a + 2
    0

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
    s.a
""",
    "let_untyped_read": """\
fn f(s: @&S) -> i32
    let q = s
    q.a + 2

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    "let_mut_ref_typed": """\
fn f(s: @&S) -> i32
    let q: @&S = s
    q.a = q.a + 2
    0

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
    s.a
""",
    # A `@&S` slot fed an i64 `*S` cast: inttoptr, then `q.a` writes through.
    "let_mut_ref_from_cast": """\
pub fn main() -> i32
    var s: S = S { a: 40 }
    let p: *S = @s
    let q: @&S = p as @&S
    q.a = q.a + 2
    s.a
""",
    # `@S` (TYPE_REF) slot from an `@&S` value.
    "let_ref_typed": """\
fn f(s: @&S) -> i32
    let r: @S = s
    r.a + 2

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    # The untyped local is still usable as a `*S` / `@&S` argument.
    "let_untyped_as_args": """\
fn f(s: @&S) -> i32
    let q = s
    bump(q)
    bump_mut(q)
    q.a

pub fn main() -> i32
    var s: S = S { a: 38 }
    f(@&s)
""",
}

# `*S -> @&S`: the i64 address must be inttoptr'd into the `ptr` model.
CAST_TO_MUT_REF = {
    "return_cast": """\
fn g(s: *S) -> @&S
    return s as @&S

pub fn main() -> i32
    var s: S = S { a: 40 }
    let r = g(@s)
    bump_mut(r)
""",
    "tail_cast": """\
fn g(s: *S) -> @&S
    s as @&S

pub fn main() -> i32
    var s: S = S { a: 40 }
    let r: @&S = g(@s)
    r.a = r.a + 2
    s.a
""",
    "call_arg_cast": """\
pub fn main() -> i32
    var s: S = S { a: 40 }
    let p: *S = @s
    bump_mut(p as @&S)
""",
    # `@&S` -> `@&S` cast stays a ptr (no bogus inttoptr of a ptr).
    "mut_ref_to_mut_ref_cast": """\
fn f(s: @&S) -> i32
    bump_mut(s as @&S)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
}

# `-> @S` is i64 like `*S`: an `@&S` value returned there needs the ptrtoint.
REF_RETURN = {
    "ref_return_stmt": """\
fn view(s: @&S) -> @S
    return s

pub fn main() -> i32
    var s: S = S { a: 40 }
    let r = view(@&s)
    r.a + 2
""",
    "ref_return_tail": """\
fn view(s: @&S) -> @S
    s

pub fn main() -> i32
    var s: S = S { a: 40 }
    let r = view(@&s)
    r.a + 2
""",
}

# `*S == @&S`: both operands must be compared as i64.
COMPARE = {
    "cmp_mixed": """\
fn f(s: @&S) -> i32
    let p: *S = s
    let n: *S = null
    if n == s
        return 1
    if p != s
        return 2
    if s == p
        return 42
    3

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
}

# AGAST #1757: a `-> @&S` call result is i64 (ptrtoint'd into the value
# model), so passing it straight into an `@&S` param needs the inttoptr even
# though get_expr_type says TYPE_MUT_REF.
CALL_RESULT_TO_MUT_REF = {
    "call_result_arg": """\
fn g(s: @&S) -> @&S
    s

pub fn main() -> i32
    var s: S = S { a: 40 }
    bump_mut(g(@&s))
""",
    # Nested: the inner call's `@&S` result feeds the outer `@&S` param.
    "call_result_nested": """\
fn g(s: @&S) -> @&S
    s

pub fn main() -> i32
    var s: S = S { a: 38 }
    bump_mut(g(g(@&s)))
    s.a + 2
""",
    # Second argument position, after a plain i64.
    "call_result_second_arg": """\
fn g(s: @&S) -> @&S
    s

fn add_to(n: i32, s: @&S) -> i32
    s.a = s.a + n
    s.a

pub fn main() -> i32
    var s: S = S { a: 40 }
    add_to(2, g(@&s))
""",
}

LEFTOVERS = {
    **LOCAL_FROM_MUT_REF,
    **CAST_TO_MUT_REF,
    **REF_RETURN,
    **COMPARE,
    **CALL_RESULT_TO_MUT_REF,
}

BROKEN = {**LET_ASSIGN, **CAST, **RET_FIELD}
ALL = {**BROKEN, **WORKING, **LEFTOVERS}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(PRELUDE + "\n" + program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
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
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ALL))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, ALL[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(LET_ASSIGN))
def test_ritz1_mut_ref_into_ptr_local(ritz1_bin, tmp_path, name):
    """`let p: *S = s` / `p = s` with `s: @&S` ptrtoints into the i64 slot."""
    assert _run("ritz1", tmp_path, name, LET_ASSIGN[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CAST))
def test_ritz1_mut_ref_cast_to_ptr(ritz1_bin, tmp_path, name):
    """`s as *S` yields the i64 address, not the raw `ptr`."""
    assert _run("ritz1", tmp_path, name, CAST[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RET_FIELD))
def test_ritz1_mut_ref_into_ptr_return_and_field(ritz1_bin, tmp_path, name):
    """`return s` from `-> *S` and `h.p = s` into a `*S` field."""
    assert _run("ritz1", tmp_path, name, RET_FIELD[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING))
def test_ritz1_already_working_forms(ritz1_bin, tmp_path, name):
    """Forms that worked before #1652 (call arg, by-value deref, `@s`)."""
    assert _run("ritz1", tmp_path, name, WORKING[name]) == 42


@pytest.mark.integration
def test_ritz1_ptr_let_from_addr_is_not_cast_again(ritz1_bin, tmp_path):
    """`@s` is already i64: the `*S` let must not add a second ptrtoint."""
    comp, ll = _compile("ritz1", tmp_path, "addr_ir", WORKING["let_from_addr"])
    assert comp.returncode == 0, comp.stdout[-2000:]
    main_ir = ll.read_text().split("define i32 @main", 1)[1]
    assert main_ir.count("ptrtoint ptr") == 1, main_ir  # the `@s` itself
    assert "#1652" not in main_ir, main_ir


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(LOCAL_FROM_MUT_REF))
def test_ritz1_local_from_mut_ref_is_struct_ptr(ritz1_bin, tmp_path, name):
    """#1754: `let q = s` / `let q: @&S = s` / `let r: @S = s` keep `q.a` working."""
    assert _run("ritz1", tmp_path, name, LOCAL_FROM_MUT_REF[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CAST_TO_MUT_REF))
def test_ritz1_cast_ptr_to_mut_ref(ritz1_bin, tmp_path, name):
    """#1754: `p as @&S` (p: *S) inttoptrs the i64 address."""
    assert _run("ritz1", tmp_path, name, CAST_TO_MUT_REF[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REF_RETURN))
def test_ritz1_mut_ref_into_ref_return(ritz1_bin, tmp_path, name):
    """#1754: `return s` / tail `s` from `-> @S` ptrtoints into its i64."""
    assert _run("ritz1", tmp_path, name, REF_RETURN[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(COMPARE))
def test_ritz1_compare_ptr_with_mut_ref(ritz1_bin, tmp_path, name):
    """#1754: `p == s` with `p: *S`, `s: @&S` compares two i64s."""
    assert _run("ritz1", tmp_path, name, COMPARE[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CALL_RESULT_TO_MUT_REF))
def test_ritz1_call_result_into_mut_ref_param(ritz1_bin, tmp_path, name):
    """#1757: a `-> @&S` call result (i64) passed to an `@&S` param is inttoptr'd."""
    assert _run("ritz1", tmp_path, name, CALL_RESULT_TO_MUT_REF[name]) == 42
