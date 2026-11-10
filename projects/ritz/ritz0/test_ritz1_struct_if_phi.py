"""AGAST #2559: ritz1 joins an `if / else if / else` whose arms are struct
values with a phi of the struct type, not `phi i64`.

THE DEFECT

    pub fn pick(self, o: B) -> B
        if self.w == 0.0
            o
        else if o.w == 0.0
            self
        else
            B.new(self.w + o.w, 1.0)

ritz1 exited 0 and emitted `%.N = phi i64 [...], [ %struct_call, ... ]`,
which clang rejects (`'%.18' defined with type '%B' but expected 'i64'`).
Found in angelo/src/shaper/types.ritz BoundsRect.union.

WHICH FORMS WERE BROKEN (measured on 5fb6e9bd)

Size (8 / 24 bytes / sret) x arm kind (param, `self`, struct literal,
static call `B.new(..)`, free-fn call `mk(..)`) x 2-arm / 3-arm chain x
position (tail, `let r = if ..`, `return if ..`): 90 programs, ritz0 runs
every one.

  * broken: every TAIL chain, any arm kind and size. A tail `if` is a
    statement (STMT_IF), whose phi was i64 unless the fn returned a tagged
    enum (ritz-task-133).
  * broken: a static-call arm in `let r = if` / `return if`. Those are
    if-EXPRESSIONS (emit_if_expr), whose phi is typed from the first struct
    arm (#1645), but resolve_expr_struct_name types a method call only
    through a local receiver, so `B.new(..)` came back untyped.
  * already fine: param, `self`, literal and free-fn-call arms in `let` /
    `return` position.

THE FIX

  * STMT_IF types its phi from the arms' values (if_stmt_arm_agg): a
    trailing expression's struct, a trailing `match`'s published phi type,
    or for an `else if` the nested if's phi type, which each statement `if`
    publishes in last_if_stmt_agg_name.
  * emit_match_arm_body falls back to call_result_struct_name (#1647) for
    an arm still untyped, so a static call types the if/match phi.

Not covered: string-literal arms (`"a"` / `"b"`) in a tail `if` of a
`-> StrView` fn give a `%Span$u8` phi, which `ret %StrView` rejects. It was
broken on 5fb6e9bd too (`phi i64`): #2563.

Oracle: ritz0 builds and runs every program with the same exit code.
"""

import itertools

import pytest

from test_ritz1_builtin_struct_shadow import _run

# 8 bytes: fits an i64.
SMALL = """\
struct B
    w: f32
    h: f32
"""
# 24 bytes: too big for an i64, below the sret threshold.
BIG = """\
struct B
    w: f32
    h: f32
    x: i64
    y: i64
"""
# >= SRET_MIN_BYTES: returned through sret.
HUGE = "struct B\n    w: f32\n    h: f32\n" + "".join(
    f"    p{i}: i64\n" for i in range(34)
)

SIZES = {"small": SMALL, "big": BIG, "huge": HUGE}


def _lit(size: str, w: str) -> str:
    """A `B { ... }` literal with field w = `w` and every other field fixed."""
    if size == "small":
        return f"B {{ w: {w}, h: 1.0 }}"
    if size == "big":
        return f"B {{ w: {w}, h: 1.0, x: 2, y: 3 }}"
    rest = ", ".join(f"p{i}: {i}" for i in range(34))
    return f"B {{ w: {w}, h: 1.0, {rest} }}"


# Arm kind -> the expression of arm i (0, 1, 2). Arm i yields w = i + 1,
# except `self`, which yields self.w = 4 in every arm.
ARMS = {
    "param": lambda size, i: "abc"[i],
    "self": lambda size, i: "self",
    "literal": lambda size, i: _lit(size, f"{i + 1}.0"),
    "static_call": lambda size, i: f"B.new({i + 1}.0)",
    "fn_call": lambda size, i: f"mk({i + 1}.0)",
}

CHAINS = {"two_arm": 2, "three_arm": 3}

POSITIONS = ("tail", "let", "return")


def _chain(n: int, arms: list, pad: str, head: str) -> str:
    """`head if k == 0 / [else if k == 1] / else` at indent `pad`."""
    out = f"{pad}{head}if k == 0\n{pad}    {arms[0]}\n"
    if n == 3:
        out += f"{pad}else if k == 1\n{pad}    {arms[1]}\n"
    out += f"{pad}else\n{pad}    {arms[n - 1]}\n"
    return out


def _body(position: str, n: int, arms: list) -> str:
    pad = "        "
    if position == "tail":
        return _chain(n, arms, pad, "")
    if position == "let":
        return _chain(n, arms, pad, "let r = ") + f"{pad}r\n"
    return _chain(n, arms, pad, "return ")


def _program(size: str, kind: str, chain: str, position: str) -> str:
    n = CHAINS[chain]
    arms = [ARMS[kind](size, i) for i in range(n)]
    # pick(k) for k = 0, 1, 2 gives arms 0, n-2 (or 1), n-1; weight them so
    # the exit code records which arm each call took.
    return (
        SIZES[size]
        + f"""
fn mk(w: f32) -> B
    {_lit(size, "w")}

impl B
    pub fn new(w: f32) -> B
        {_lit(size, "w")}
    pub fn pick(self, a: B, b: B, c: B, k: i32) -> B
"""
        + _body(position, n, arms)
        + """
pub fn main() -> i32
    let s = B.new(4.0)
    let a = B.new(1.0)
    let b = B.new(2.0)
    let c = B.new(3.0)
    let r0 = s.pick(a, b, c, 0)
    let r1 = s.pick(a, b, c, 1)
    let r2 = s.pick(a, b, c, 2)
    return (r0.w as i32) + (r1.w as i32) * 5 + (r2.w as i32) * 25
"""
    )


def _expected(kind: str, chain: str) -> int:
    n = CHAINS[chain]
    if kind == "self":
        return 4 + 4 * 5 + 4 * 25
    picks = [1, 2, 3] if n == 3 else [1, 2, 2]
    return picks[0] + picks[1] * 5 + picks[2] * 25


WAS_BROKEN = {
    (size, kind, chain, pos)
    for size, kind, chain, pos in itertools.product(SIZES, ARMS, CHAINS, POSITIONS)
    if pos == "tail" or kind == "static_call"
}

MATRIX = [
    pytest.param(
        size,
        kind,
        chain,
        pos,
        id=f"{size}-{kind}-{chain}-{pos}"
        + ("-was_broken" if (size, kind, chain, pos) in WAS_BROKEN else ""),
    )
    for size, kind, chain, pos in itertools.product(SIZES, ARMS, CHAINS, POSITIONS)
]


@pytest.mark.integration
@pytest.mark.parametrize("size,kind,chain,position", MATRIX)
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_struct_if_chain(tmp_path, compiler, size, kind, chain, position):
    name = f"sip_{size}_{kind}_{chain}_{position}"
    program = _program(size, kind, chain, position)
    assert _run(compiler, tmp_path, name, program) == _expected(kind, chain)


# The ticket's program: mixed arms (param, self, static call) in a 3-arm
# tail chain, the shape of angelo's BoundsRect.union.
TICKET = """\
struct B
    w: f32
    h: f32
impl B
    pub fn new(w: f32, h: f32) -> B
        B { w: w, h: h }
    pub fn pick(self, o: B) -> B
        if self.w == 0.0
            o
        else if o.w == 0.0
            self
        else
            B.new(self.w + o.w, 1.0)
pub fn main() -> i32
    let a = B.new(2.0, 1.0)
    let b = B.new(3.0, 1.0)
    let c = a.pick(b)
    return c.w as i32
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_ticket_mixed_arms(tmp_path, compiler):
    assert _run(compiler, tmp_path, "sip_ticket", TICKET) == 5


# A tail `if` whose arms are both matches over struct arms: only the
# matches' published type can type the outer phi. Before it, a scalar statement `if` in the same
# struct-returning fn must keep its i64 phi; and a tagged-enum fn's tail `if`
# (ritz-task-133) is still typed by the fn's return.
MATCH_ARM = """\
struct B
    w: i32
    h: i32
fn pick(k: i32, o: Option<i32>) -> B
    var t: i32 = 0
    if k == 9
        t + 1
    else
        t + 2
    if k == 0
        match o
            Some(v) => B { w: v + 1, h: 0 }
            None => B { w: 1, h: 0 }
    else
        match o
            Some(v) => B { w: v, h: 0 }
            None => B { w: 7, h: 0 }
fn res(k: i32) -> Result<i32, i32>
    if k == 0
        Ok(3)
    else
        Err(4)
pub fn main() -> i32
    let b = pick(1, Some(5))
    var r: i32 = 0
    match res(0)
        Ok(v) => r = v
        Err(e) => r = e
    return b.w * 10 + r
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_tail_if_with_match_arm(tmp_path, compiler):
    assert _run(compiler, tmp_path, "sip_match_arm", MATCH_ARM) == 53


# A tail `if` whose arms are both nested `if`s: only the nested statement
# ifs' published phi type (last_if_stmt_agg_name) can type the outer phi.
NESTED = """\
struct B
    w: f32
    h: f32
fn pick(a: B, b: B, k: i32) -> B
    if k < 2
        if k == 0
            a
        else
            b
    else
        if k == 2
            b
        else
            a
pub fn main() -> i32
    let a = B { w: 1.0, h: 0.0 }
    let b = B { w: 2.0, h: 0.0 }
    let r0 = pick(a, b, 0)
    let r1 = pick(a, b, 1)
    let r2 = pick(a, b, 2)
    let r3 = pick(a, b, 3)
    return (r0.w as i32) + (r1.w as i32) * 3 + (r2.w as i32) * 9 + (r3.w as i32) * 27
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_tail_if_with_nested_if_arms(tmp_path, compiler):
    assert _run(compiler, tmp_path, "sip_nested", NESTED) == 1 + 6 + 18 + 27
