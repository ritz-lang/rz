"""A statement with no effect is a located error (LARB R64, R69; AGAST #3491).

LARB R64 (LANGUAGE_SPEC §6.6, which ritz1's #3492 writes): an expression
statement that isn't its block's value is an error when its outermost node is
a literal, name, field, index, borrow, `*p`, cast, aggregate literal or
operator:

    main.ritz:<line>:<col>: statement has no effect: the value of `<expr>` is discarded

A string adds "a string on its own line prints nothing: call print": the 259
lost zeus `"FAIL: …"` lines (#3490) were that slip.  Calls, assignments and
`if`/`match`/blocks are allowed (a `[[must_use]]` call is §17.8's,
test_must_use.py).  It is an error, not a warning: Ritz has none.

R69 says when a block is a value: only when it is used as one.  The last line
of a void fn, a loop body, a statement `if` branch or a statement `match` arm
is discarded like any other statement, so `_ => 0` in a statement match is
refused; a do-nothing arm is `_ => pass`.

ritz0 only: ritz1's twin is #3492.  One refusal row per node kind and per
R69 position; the legal rows each pin one thing the rule must not refuse.
"""

import pytest

from no_effect import STRING_HINT, no_effect_message
from test_ref_into_value import _assert_refused, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

COMPILER = "ritz0"

PRELUDE = """\
struct P
    x: i32

fn touch(x: i32) -> i32
    x + 1

"""

# `^` marks where the error lands; the text after it on that line is `<expr>`.
REFUSED = {
    # One row per node kind (R64).
    "int_literal": "fn main() -> i32\n    ^555\n    0\n",
    "name": "fn main() -> i32\n    let x: i32 = 1\n    ^x\n    x\n",
    "field": "fn main() -> i32\n    let p = P { x: 1 }\n    ^p.x\n    0\n",
    "index": "fn main() -> i32\n    let a: [2]i32 = [1, 2]\n    ^a[0]\n    0\n",
    "borrow": "fn main() -> i32\n    let x: i32 = 1\n    ^@x\n    x\n",
    "deref": "fn peek(p: *i32) -> i32\n    ^*p\n    0\n\nfn main() -> i32\n    0\n",
    "cast": "fn main() -> i32\n    let x: i32 = 1\n    ^x as i64\n    x\n",
    "struct_literal": "fn main() -> i32\n    ^P { x: 1 }\n    0\n",
    "array_literal": "fn main() -> i32\n    ^[1, 2]\n    0\n",
    "binop": "fn main() -> i32\n    let x: i32 = 1\n    ^x == 1\n    x\n",
    "unary": "fn main() -> i32\n    let x: i32 = 1\n    ^-x\n    x\n",
    # R69: the last line of a body that is never a value.
    "void_fn_tail": "fn run(x: i32)\n    ^x\n\nfn main() -> i32\n    run(1)\n    0\n",
    "loop_tail": ("fn main() -> i32\n    var i: i32 = 0\n    while i < 3\n"
                  "        i = i + 1\n        ^i\n    0\n"),
    "stmt_if_tail": ("fn main() -> i32\n    let x: i32 = 1\n    if x == 1\n"
                     "        touch(x)\n        ^x + 1\n    0\n"),
    "stmt_match_arm": ("fn main() -> i32\n    let x: i32 = 1\n    match x\n"
                       "        1 => touch(x)\n        _ => ^0\n    0\n"),
}

STRING = 'fn main() -> i32\n    ^"FAIL: x\\n"\n    0\n'

# The quoted `<expr>` ends where the expression does, not at the line's end:
# an inline `if` arm stops at its `else` or the group's `)`; an operator whose
# operand is an inline `if` keeps the whole `if … else …`.
INLINE = {
    "inline_if_then_arm": ("fn main() -> i32\n    let x: i32 = 1\n"
                           "    (if x == 1 then ^x else touch(x))\n    0\n", "x"),
    "inline_if_else_arm": ("fn main() -> i32\n    let x: i32 = 1\n"
                           "    (if x == 1 then touch(x) else ^x + 2)\n    0\n", "x + 2"),
    "operand_inline_if": ("fn main() -> i32\n    let x: i32 = 1\n"
                          "    ^x + if x == 1 then 1 else 2\n    0\n",
                          "x + if x == 1 then 1 else 2"),
}

# Each returns 0; each is a shape the rule must leave alone.
LEGAL = {
    # A block's value: a fn tail, a value `if`, a value `match` arm, a block.
    "block_value": """\
fn pick(x: i32) -> i32
    let v: i32 = if x == 1
        x + 1
    else
        x - 1
    let w: i32 = match x
        1 => 0
        _ => 1
    v - x - 1 + w
fn main() -> i32
    pick(1)
""",
    # A discarded call, method call included; an assignment.
    "call": """\
impl P
    fn get(self: @P) -> i32
        self.x

fn main() -> i32
    var n: i32 = 0
    touch(n)
    let p = P { x: 2 }
    p.get()
    n = touch(n) - 1
    n
""",
    # A statement `if`/`match` whose bodies run for effect, `_ => pass`.
    "statement_if_match": """\
fn main() -> i32
    var n: i32 = 0
    if n == 0
        touch(n)
    match n
        0 => n = 0
        _ => pass
    var i: i32 = 0
    while i < 2
        i = touch(i)
    n
""",
    # R64's fix, `_ => pass`, beside arms storing a bool, as the tail of a
    # procedure (prism keyboard.ritz): `pass` has no value, so there is no
    # integer to mix with them.  Its dummy i32 0 was refused as "cannot use
    # an integer as bool".
    "pass_beside_bool_stores": """\
struct M
    s: bool
    c: bool

fn up(m: *M, k: i32)
    match k
        1 => m.s = true
        2 => m.c = true
        _ => pass

fn main() -> i32
    var m = M { s: false, c: false }
    up(@m, 1)
    up(@m, 3)
    if m.s and not m.c
        return 0
    1
""",
    # A procedure's tail is discarded (§5.1, R69), a bool call's too: it was
    # converted into the dummy return and refused as a bool used as an integer.
    "procedure_bool_call_tail": """\
fn ok() -> bool
    true

fn run()
    ok()

fn main() -> i32
    run()
    0
""",
    # `_ => pass` in a match inside a statement if-chain, beside arms yielding
    # an i32 (examples/tier5_async/79_ritzlib_json): the chain reads its value.
    "pass_arm_in_if_chain": """\
fn main() -> i32
    let o: Option<i32> = Some(1)
    var n: i32 = 0
    if n == 1
        touch(n)
    else if n == 0
        match o
            Some(v) => touch(v)
            None => pass
    else
        touch(n)
    n
""",
}


def _expr_text(marked: str) -> str:
    """The text after `^` on its line: the row's `<expr>`."""
    return marked[marked.index("^") + 1:].split("\n", 1)[0]


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_no_effect_statement_is_refused(tmp_path, name):
    marked = PRELUDE + REFUSED[name]
    _assert_refused(COMPILER, tmp_path, name, marked,
                    no_effect_message(_expr_text(marked), is_string=False))


@pytest.mark.parametrize("name", sorted(INLINE))
def test_quoted_expression_ends_with_it(tmp_path, name):
    marked, text = INLINE[name]
    _assert_refused(COMPILER, tmp_path, name, PRELUDE + marked,
                    no_effect_message(text, is_string=False))


def test_string_statement_names_print(tmp_path):
    marked = PRELUDE + STRING
    message = no_effect_message(_expr_text(marked), is_string=True)
    assert message.endswith(STRING_HINT)
    _assert_refused(COMPILER, tmp_path, "string", marked, message)


def test_message_words():
    """The words are the ruling's (R64), which ritz1 (#3492) copies."""
    assert no_effect_message("x", is_string=False) == (
        "statement has no effect: the value of `x` is discarded")
    assert STRING_HINT == "a string on its own line prints nothing: call print"


@pytest.mark.parametrize("name", sorted(LEGAL))
def test_effectful_statement_is_legal(tmp_path, name):
    assert _run(COMPILER, tmp_path, name, PRELUDE + LEGAL[name]) == 0
