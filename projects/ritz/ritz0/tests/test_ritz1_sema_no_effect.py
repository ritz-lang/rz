"""A statement with no effect is a located error on ritz1 (LARB R64, R69;
AGAST #3492).

LARB R64 (LANGUAGE_SPEC §6.6, written with this check): an expression
statement that isn't its block's value is an error when its outermost node is
a literal, name, field, index, borrow, `*p`, cast, aggregate literal or
operator:

    main.ritz:<line>:<col>: error: statement has no effect: the value of `<expr>` is discarded

A string adds "a string on its own line prints nothing: call print".  Calls,
assignments and `if`/`match`/blocks are allowed; a `[[must_use]]` call is
§17.8's (test_ritz1_sema_must_use.py).

R69 says when a block is a value: only when it is used as one.  The last line
of a void fn, a loop body, a statement `if` branch or a statement `match` arm
is discarded like any other statement, so `_ => 0` in a statement match is
refused; a do-nothing arm is `_ => pass`.  A whole array alone keeps
discarded_array.ritz's more specific message.

The rows are ritz0's (test_no_effect_statement.py) verbatim in intent, plus one
refusal row per node kind and the two traps: `pass` is the no-op, and a whole
array is not this rule's.  Both compilers must match ritz0's words, at the
same line and column.
"""

import re

import pytest

from no_effect import STRING_HINT, no_effect_message
from test_ref_into_value import _assert_refused, _compile, _run

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

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
    "float_literal": "fn main() -> i32\n    ^1.5\n    0\n",
    "char_literal": "fn main() -> i32\n    ^'a'\n    0\n",
    "nil_literal": "fn main() -> i32\n    ^null\n    0\n",
    "name": "fn main() -> i32\n    let x: i32 = 1\n    ^x\n    x\n",
    "field": "fn main() -> i32\n    let p = P { x: 1 }\n    ^p.x\n    0\n",
    "index": "fn main() -> i32\n    let a: [2]i32 = [1, 2]\n    ^a[0]\n    0\n",
    "borrow": "fn main() -> i32\n    let x: i32 = 1\n    ^@x\n    x\n",
    "deref": "fn peek(p: *i32) -> i32\n    ^*p\n    0\n\nfn main() -> i32\n    0\n",
    "cast": "fn main() -> i32\n    let x: i32 = 1\n    ^x as i64\n    x\n",
    "struct_literal": "fn main() -> i32\n    ^P { x: 1 }\n    0\n",
    "array_literal": "fn main() -> i32\n    ^[1, 2]\n    0\n",
    "array_fill": "fn main() -> i32\n    ^[0; 2]\n    0\n",
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

# Strings get the hint: a print that was never written.  Both literal shapes.
STRINGS = {
    "string": 'fn main() -> i32\n    ^"FAIL: x\\n"\n    0\n',
    "cstring": 'fn main() -> i32\n    ^c"FAIL: x\\n"\n    0\n',
}

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
    # `pass` is the no-op: an arm, and the tail of a void fn.
    "pass_is_the_no_op": """\
fn bump(k: i32)
    match k
        0 => pass
        _ => touch(k)
    pass

fn main() -> i32
    bump(0)
    bump(1)
    0
""",
    # R64's fix, `_ => pass`, beside arms storing a bool.
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
    # A procedure's tail is discarded (§5.1, R69), a bool call's too.
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
    # an i32 (examples/tier5_async/79_ritzlib_json).
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

# A whole array place alone is discarded_array.ritz's (field) or the
# emitter's (local, `:& [N]T` param, `*p`), in its more specific words.  This
# rule must stay quiet, or the diagnostic the shared tables expect disappears
# when Sema stops the compile before emission (AGAST #3189, #3054).
WHOLE_ARRAYS = {
    "local": "fn f() -> i32\n    var b: [2]i32 = [1, 3]\n    b\n    return 3\n",
    "lent_param": "fn f(a:& [2]i32)\n    a\n",
    "field": "fn f(w: W) -> i32\n    w.a\n    return 3\n",
    "deref": "fn f(p: *[2]i32)\n    *p\n",
}

WHOLE_ARRAY_HEAD = """\
struct W
    a: [2]i32

"""

WHOLE_ARRAY_MAIN = "\npub fn main() -> i32\n    0\n"


def _expr_text(marked: str) -> str:
    """The text after `^` on its line: the row's `<expr>`."""
    return marked[marked.index("^") + 1:].split("\n", 1)[0]


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_no_effect_statement_is_refused(request, tmp_path, compiler, name):
    request.getfixturevalue("ritz1_bin")
    marked = PRELUDE + REFUSED[name]
    _assert_refused(compiler, tmp_path, name, marked,
                    no_effect_message(_expr_text(marked), is_string=False))


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(STRINGS))
def test_a_string_statement_names_print(request, tmp_path, compiler, name):
    request.getfixturevalue("ritz1_bin")
    marked = PRELUDE + STRINGS[name]
    message = no_effect_message(_expr_text(marked), is_string=True)
    assert message.endswith(STRING_HINT)
    _assert_refused(compiler, tmp_path, name, marked, message)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(INLINE))
def test_quoted_expression_ends_with_it(request, tmp_path, compiler, name):
    request.getfixturevalue("ritz1_bin")
    marked, text = INLINE[name]
    _assert_refused(compiler, tmp_path, name, PRELUDE + marked,
                    no_effect_message(text, is_string=False))


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(LEGAL))
def test_effectful_statement_is_legal(request, tmp_path, compiler, name):
    request.getfixturevalue("ritz1_bin")
    assert _run(compiler, tmp_path, name, PRELUDE + LEGAL[name]) == 0


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("shape", sorted(WHOLE_ARRAYS))
def test_a_whole_array_keeps_its_own_message(request, tmp_path, compiler, shape):
    """The more specific refusal stands; this rule stays quiet."""
    request.getfixturevalue("ritz1_bin")
    src = WHOLE_ARRAY_HEAD + WHOLE_ARRAYS[shape] + WHOLE_ARRAY_MAIN
    comp, ll, _ = _compile(compiler, tmp_path, f"whole_array_{shape}", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    assert "statement has no effect" not in out, f"{compiler} doubled the report:\n{out}"
    assert re.search(r"main\.ritz:\d+:\d+: error: a whole array is not a value here", out), out
