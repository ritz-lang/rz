"""A `return` operand takes its enum type from the fn it returns from.

AGAST #2207. With `Result<Page, Er>` and `Result<Vec<Page>, Er>` in one module,
`Some(p) => return Ok(p)` in a statement-position match arm built the variant
through the global variant map: whichever specialization registered last.

    cannot store %"struct...Page" to %"struct...Vec$Page"*: mismatching types

`_emit_return_expr`, the path a `return` in an arm takes, emitted its operand
with no expected enum. The `ReturnStmt` path had one only for a bare variant, so
`return match ...` and `return if ...` had the same bug, and it read
`current_fn_def`, which names the enclosing fn inside a closure body. Both paths
now go through `_emit_return_operand`.

ritz1 already took a `return` from the fn's type, except inside a `let`
initialiser, whose enum context won: `return Ok(p)` built an `Option$i64`.

When the operand needs no conversion the store succeeds and the bug surfaces
later as IR clang rejects, a `ret` of the wrong type:

    ret %"enum...Result$Vec_Page_Er" %".27"     (in a `Result$unknown_Er` fn)

which is the ticket's second symptom. The `unknown` in that name is a separate
defect in `mangle_type_name`, AGAST #2270, fixed and pinned below.

Every program declares the competing specialization AFTER the fn under test
where order matters, since the last one registered is the one that wins. Each
exit code encodes which path ran, so a value built with the wrong tag or layout
fails as well as a rejected compile.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

PRELUDE = """\
import ritzlib.gvec
import ritzlib.sys

struct Page
    id: i64

struct Er
    code: i32

fn get(n: i64) -> Option<Page>
    if n > 0
        return Some(Page { id: n })
    None

fn load(n: i64) -> Result<Page, Er>
    if n > 100
        return Err(Er { code: 9 })
    Ok(Page { id: n + 1 })
"""

# Registers the competitor. Placed after the fn under test.
COMPETITOR = """\
fn list() -> Result<Vec<Page>, Er>
    Ok(vec_new<Page>())
"""

# Reads a `Result<Page, Er>` back as an exit code: Ok gives the id, Err 50+code.
MAIN_PAGE = """\
fn code(r: Result<Page, Er>) -> i32
    match r
        Ok(p) => p.id as i32
        Err(e) => 50 + e.code

fn main() -> i32
    code(both(%s))
"""


def program(body: str, arg: int) -> str:
    return "\n".join([PRELUDE, body, COMPETITOR, MAIN_PAGE % arg])


# The ticket's repro: a variant under `return` in a statement-position arm.
REPRO = """\
fn both(n: i64) -> Result<Page, Er>
    match get(n)
        Some(p) => return Ok(p)
        None => 0
    var page: Page = load(n)?
    Ok(page)
"""

ERR_IN_ARM = """\
fn both(n: i64) -> Result<Page, Er>
    match load(n)
        Ok(p) => 0
        Err(e) => return Err(Er { code: e.code + 1 })
    Ok(Page { id: 7 })
"""

NESTED_MATCH = """\
fn both(n: i64) -> Result<Page, Er>
    match get(n)
        Some(p) =>
            match load(p.id)
                Ok(q) => return Ok(q)
                Err(e) => return Err(e)
        None => 0
    Ok(Page { id: 7 })
"""

THREE_DEEP = """\
fn both(n: i64) -> Result<Page, Er>
    match get(n)
        Some(p) =>
            match load(p.id)
                Ok(q) =>
                    match get(q.id)
                        Some(r) => return Ok(r)
                        None => 0
                Err(e) => return Err(e)
        None => 0
    Ok(Page { id: 7 })
"""

IF_IN_ARM = """\
fn both(n: i64) -> Result<Page, Er>
    match get(n)
        Some(p) =>
            if p.id > 3
                return Ok(p)
            else
                return Err(Er { code: 2 })
        None => 0
    Ok(Page { id: 7 })
"""

BLOCK_ARM = """\
fn both(n: i64) -> Result<Page, Er>
    match get(n)
        Some(p) =>
            let q: i64 = p.id + 2
            return Ok(Page { id: q })
        None => 0
    Ok(Page { id: 7 })
"""

INTEGER_MATCH = """\
fn both(n: i64) -> Result<Page, Er>
    match n
        5 => return Ok(Page { id: 11 })
        6 => return Err(Er { code: 3 })
        _ => 0
    Ok(Page { id: 7 })
"""

LOOP_IN_ARM = """\
fn both(n: i64) -> Result<Page, Er>
    match get(n)
        Some(p) =>
            var i: i64 = 0
            while i < 10
                if i == p.id
                    return Ok(Page { id: i + 20 })
                i = i + 1
        None => 0
    Ok(Page { id: 7 })
"""

# The operand is control flow, so the expectation has to thread into its tails.
RETURN_MATCH = """\
fn both(n: i64) -> Result<Page, Er>
    return match get(n)
        Some(p) => Ok(p)
        None => Err(Er { code: 4 })
"""

RETURN_IF = """\
fn both(n: i64) -> Result<Page, Er>
    if n == 99
        return Err(Er { code: 1 })
    return if n > 3
        Ok(Page { id: n })
    else
        Err(Er { code: 5 })
"""

RETURN_MATCH_IN_ARM = """\
fn both(n: i64) -> Result<Page, Er>
    match get(n)
        Some(p) =>
            return match load(p.id)
                Ok(q) => Ok(q)
                Err(e) => Err(e)
        None => 0
    Ok(Page { id: 7 })
"""

# An arm of a `let` initialiser carries the let's expectation; a `return` there
# leaves the let, so the fn's type wins, not `Option<i64>`.
RETURN_INSIDE_LET_ARM = """\
fn both(n: i64) -> Result<Page, Er>
    let v: Option<i64> = match n
        5 => return Ok(Page { id: 12 })
        _ => Some(n)
    match v
        Some(x) => Ok(Page { id: x + 30 })
        None => Err(Er { code: 6 })
"""

RETURN_MATCH_INSIDE_LET_ARM = """\
fn both(n: i64) -> Result<Page, Er>
    let v: Option<i64> = match n
        5 =>
            return match get(n)
                Some(p) => Ok(p)
                None => Err(Er { code: 7 })
        _ => Some(n)
    match v
        Some(x) => Ok(Page { id: x + 30 })
        None => Err(Er { code: 6 })
"""

CASES = {
    "repro_taken": (REPRO, 5, 5),
    "repro_fallthrough": (REPRO, 0, 1),
    "err_in_arm": (ERR_IN_ARM, 200, 60),
    "err_in_arm_fallthrough": (ERR_IN_ARM, 5, 7),
    "nested_ok": (NESTED_MATCH, 5, 6),
    "nested_err": (NESTED_MATCH, 200, 59),
    "three_deep": (THREE_DEEP, 5, 6),
    "if_in_arm_then": (IF_IN_ARM, 5, 5),
    "if_in_arm_else": (IF_IN_ARM, 2, 52),
    "block_arm": (BLOCK_ARM, 5, 7),
    "integer_match_ok": (INTEGER_MATCH, 5, 11),
    "integer_match_err": (INTEGER_MATCH, 6, 53),
    "loop_in_arm": (LOOP_IN_ARM, 5, 25),
    "return_match_ok": (RETURN_MATCH, 5, 5),
    "return_match_err": (RETURN_MATCH, 0, 54),
    "return_if_then": (RETURN_IF, 5, 5),
    "return_if_else": (RETURN_IF, 2, 55),
    "return_match_in_arm": (RETURN_MATCH_IN_ARM, 5, 6),
    "return_inside_let_arm": (RETURN_INSIDE_LET_ARM, 5, 12),
    "return_inside_let_arm_fallthrough": (RETURN_INSIDE_LET_ARM, 6, 36),
    "return_match_inside_let_arm": (RETURN_MATCH_INSIDE_LET_ARM, 5, 5),
}

# A large payload returns through sret, a different `ret` from the cases above.
SRET_RETURN = (
    PRELUDE
    + """\
struct Big
    a: i64
    b: i64
    c: i64
    d: i64
    e: i64

fn big(n: i64) -> Result<Big, Er>
    match get(n)
        Some(p) => return Ok(Big { a: p.id, b: 2, c: 3, d: 4, e: 5 })
        None => 0
    Err(Er { code: 8 })

"""
    + COMPETITOR
    + """
fn main() -> i32
    match big(6)
        Ok(b) => (b.a + b.e) as i32
        Err(e) => 50 + e.code
"""
)

# `Some`/`None` have the same problem as `Ok`/`Err`, without a payload on None.
OPTION_RETURN = """\
import ritzlib.option

struct Small
    x: i32

struct Wide
    y: i64
    z: i64

fn pick(n: i32) -> Option<Small>
    match n
        1 => return Some(Small { x: 21 })
        2 => return None
        _ => 0
    Some(Small { x: 3 })

fn other() -> Option<Wide>
    Some(Wide { y: 1, z: 2 })

fn main() -> i32
    var total: i32 = 0
    match pick(1)
        Some(a) => total = total + a.x
        None => total = total + 100
    match pick(2)
        Some(a) => total = total + 50
        None => total = total + 1
    match pick(3)
        Some(a) => total = total + a.x
        None => total = total + 100
    total
"""

# The generic fn's return type comes from the monomorphizer, not the source.
GENERIC_FN = (
    PRELUDE
    + """\
fn first<T>(o: Option<T>) -> Result<T, Er>
    match o
        Some(v) => return Ok(v)
        None => 0
    Err(Er { code: 4 })

"""
    + COMPETITOR
    + """
fn main() -> i32
    let r: Result<Page, Er> = first<Page>(get(8))
    match r
        Ok(p) => p.id as i32
        Err(e) => 50 + e.code
"""
)

METHOD = (
    PRELUDE
    + """\
struct Store
    base: i64

impl Store
    fn fetch(self: @Store, n: i64) -> Result<Page, Er>
        match get(n)
            Some(p) => return Ok(Page { id: p.id + self.base })
            None => 0
        Err(Er { code: 2 })

"""
    + COMPETITOR
    + """
fn main() -> i32
    let s = Store { base: 4 }
    let r: Result<Page, Er> = s.fetch(5)
    match r
        Ok(p) => p.id as i32
        Err(e) => 50 + e.code
"""
)

# ritz1 parses neither form: no closures here, no match as a call argument.
#
# A closure body changes the fn being emitted but not `current_fn_def`, so the
# `return` must take the closure's type, not the enclosing `Result`.
CLOSURE_RETURN = (
    PRELUDE
    + """\
fn both(n: i64) -> Result<Page, Er>
    let f: fn(i32) -> Option<i32> = |x| match x
        4 => return Some(x)
        _ => None
    match f(4)
        Some(v) => Ok(Page { id: v as i64 })
        None => Err(Er { code: 1 })

"""
    + COMPETITOR
    + "\n"
    + MAIN_PAGE % 5
)

# The same in a block arm, which is a `ReturnStmt` rather than a `ReturnExpr`.
CLOSURE_BLOCK_ARM_RETURN = CLOSURE_RETURN.replace(
    "        4 => return Some(x)\n", "        4 =>\n            return Some(x)\n"
)

CALL_ARG_ARM = (
    PRELUDE
    + """\
fn take(o: Option<i64>) -> i64
    7

fn both(n: i64) -> Result<Page, Er>
    let t: i64 = take(match n
        5 => return Ok(Page { id: 12 })
        _ => Some(n)
    )
    Ok(Page { id: t })

"""
    + COMPETITOR
    + "\n"
    + MAIN_PAGE % 5
)

RITZ0_ONLY = {
    "closure_return": (CLOSURE_RETURN, 4),
    "closure_block_arm_return": (CLOSURE_BLOCK_ARM_RETURN, 4),
    "call_arg_arm": (CALL_ARG_ARM, 12),
}

WHOLE_PROGRAMS = {
    "sret_return": (SRET_RETURN, 11),
    "option_return": (OPTION_RETURN, 25),
    "method": (METHOD, 9),
    "generic_fn": (GENERIC_FN, 8),  # ritz1 since AGAST #2418 (was #2275)
}

# The second symptom's shape, in both orders. `ritzlib.result` is what routes
# `Result<(), E>` through `mangle_type_name`. ritz1 cannot parse `()` as a type
# argument at all (AGAST #2272), so this one is ritz0 only.
UNIT_RESULT_CHECK = """\
fn check(n: i64) -> Result<(), Er>
    match load(n)
        Ok(p) => 0
        Err(e) => return Err(e)
    Ok(())
"""

UNIT_RESULT_MAIN = """\
fn main() -> i32
    match check(%s)
        Ok(_) => 40
        Err(e) => 50 + e.code
"""

UNIT_RESULT_PRELUDE = PRELUDE.replace(
    "import ritzlib.sys\n", "import ritzlib.sys\nimport ritzlib.result\n"
)


def unit_program(competitor_first: bool, arg: int) -> str:
    parts = [UNIT_RESULT_CHECK, COMPETITOR]
    if competitor_first:
        parts.reverse()
    return "\n".join([UNIT_RESULT_PRELUDE, *parts, UNIT_RESULT_MAIN % arg])


def _run(compiler: str, tmp_path: Path, name: str, source: str) -> int:
    """Compile `source` with `compiler`, link it, run it, return the exit code."""
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(source)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        comp = subprocess.run(
            [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(1, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link ({name}):\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_return_uses_fn_type(tmp_path, name):
    body, arg, want = CASES[name]
    assert _run("ritz0", tmp_path, name, program(body, arg)) == want


@pytest.mark.parametrize("name", sorted(WHOLE_PROGRAMS))
def test_ritz0_return_whole_program(tmp_path, name):
    source, want = WHOLE_PROGRAMS[name]
    assert _run("ritz0", tmp_path, name, source) == want


@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_return_uses_fn_type(tmp_path, ritz1_bin, ritz_start, name):
    body, arg, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program(body, arg)) == want


@pytest.mark.parametrize("name", sorted(WHOLE_PROGRAMS))
def test_ritz1_return_whole_program(tmp_path, ritz1_bin, ritz_start, name):
    source, want = WHOLE_PROGRAMS[name]
    assert _run("ritz1", tmp_path, name, source) == want


@pytest.mark.parametrize("competitor_first", [False, True])
@pytest.mark.parametrize("arg,want", [(5, 40), (200, 59)])
def test_ritz0_unit_result_return_in_arm(tmp_path, competitor_first, arg, want):
    source = unit_program(competitor_first, arg)
    assert _run("ritz0", tmp_path, "unit", source) == want


@pytest.mark.parametrize("name", sorted(RITZ0_ONLY))
def test_ritz0_only_forms(tmp_path, name):
    source, want = RITZ0_ONLY[name]
    assert _run("ritz0", tmp_path, name, source) == want


# --- neighbouring defects found here, each with its own ticket ----------------

TUPLE_ARGS = """\
struct Er
    code: i32

struct Box2<T>
    v: T

fn wrap<T>(x: T) -> Box2<T>
    Box2<T> { v: x }

fn a() -> Box2<Result<(), Er>>
    let r: Result<(), Er> = Ok(())
    wrap<Result<(), Er>>(r)

fn b() -> Box2<Result<(i64, i64), Er>>
    let r: Result<(i64, i64), Er> = Ok((1, 2))
    wrap<Result<(i64, i64), Er>>(r)

fn main() -> i32
    let x = a()
    let y = b()
    match y.v
        Ok(t) => (t.0 + t.1) as i32
        Err(e) => 50
"""

DEAD_TAIL = """\
enum E
    A
    B

fn f(e: E) -> i32
    match e
        A => return 1
        B => return 2
    3

fn main() -> i32
    f(A)
"""

UNIT_TYPE_ARG = """\
fn f(n: i32) -> Result<(), i32>
    if n < 0
        return Err(n)
    Ok(())

fn main() -> i32
    0
"""

PAYLOAD_MEMBER = """\
import ritzlib.result

struct Er
    code: i32

struct Store
    base: i64

impl Store
    fn fetch(self: @Store, n: i64) -> Result<i64, Er>
        Err(Er { code: 2 })

fn main() -> i32
    let s = Store { base: 4 }
    match s.fetch(5)
        Ok(p) => p as i32
        Err(e) => 50 + e.code
"""

GENERIC_ENUM_SIGNATURE = """\
import ritzlib.option

fn unwrap_or<T>(o: Option<T>, d: T) -> T
    match o
        Some(v) => v
        None => d

fn main() -> i32
    let o: Option<i32> = Some(7)
    unwrap_or<i32>(o, 3)
"""

ONE_LETTER_STRUCT = """\
import ritzlib.option

struct A
    x: i32

fn pick(n: i32) -> Option<A>
    Some(A { x: 21 })

fn main() -> i32
    match pick(1)
        Some(a) => a.x
        None => 100
"""


# AGAST #2270: every tuple mangled as `unknown`, so both `wrap`s collided.
def test_ritz0_tuple_args_do_not_collide(tmp_path):
    assert _run("ritz0", tmp_path, "tuple_args", TUPLE_ARGS) == 3


def test_ritz0_dead_code_after_all_arms_return(tmp_path):
    assert _run("ritz0", tmp_path, "dead_tail", DEAD_TAIL) == 1


@pytest.mark.xfail(strict=True, reason="AGAST #2272: `()` type argument")
def test_ritz1_unit_type_argument(tmp_path, ritz1_bin, ritz_start):
    assert _run("ritz1", tmp_path, "unit_arg", UNIT_TYPE_ARG) == 0


def test_ritz1_payload_member_from_call_scrutinee(tmp_path, ritz1_bin, ritz_start):
    assert _run("ritz1", tmp_path, "payload_member", PAYLOAD_MEMBER) == 52


# AGAST #2274, fixed by #2432: `Option$A` is no template when `struct A` exists.
def test_ritz1_one_letter_struct_payload(tmp_path, ritz1_bin, ritz_start):
    assert _run("ritz1", tmp_path, "one_letter", ONE_LETTER_STRUCT) == 21


# AGAST #2275, fixed by #2418: `o: Option<T>` was defined as `%Option$T`.
def test_ritz1_generic_enum_signature(tmp_path, ritz1_bin, ritz_start):
    assert _run("ritz1", tmp_path, "generic_sig", GENERIC_ENUM_SIGNATURE) == 7


@pytest.mark.xfail(strict=True, reason="AGAST #2276: IndexError hides the error")
def test_ritz0_closure_error_keeps_its_diagnostic(tmp_path):
    src = tmp_path / "closure_error.ritz"
    src.write_text(
        "fn main() -> i32\n    let f: fn(i32) -> i32 = |x| nosuchname + x\n    f(4)\n"
    )
    comp = run_ritz0([str(src), "-o", str(tmp_path / "closure_error.ll")], cwd=tmp_path)
    assert comp.returncode != 0
    # The chained traceback names `nosuchname` too, so ask for the absence of
    # the IndexError that replaced it.
    assert "pop from empty list" not in comp.stdout + comp.stderr
