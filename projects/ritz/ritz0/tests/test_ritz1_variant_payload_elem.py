"""A struct array element as a variant payload (AGAST #4678), and a
`StrView` payload's `unwrap_or("lit")` (AGAST #4679).

#4678: `Some(m.params[idx])` was refused by ritz1 with "a whole struct is not
a value here" (valet).  emit_payload_into_slot emitted the payload with a bare
emit_expr, and a whole struct element is a value only when it's marked as the
copy into a struct slot (emit_struct_copy).  One row per way the element is
reached (an array field through a pointer, a local array, `p[i]` on a `*S`),
per variant builder (`Some`, `Ok`, `Err`, a user enum's tuple variant), and a
user struct beside `StrView`.

#4679: `opt.unwrap_or("/")` on `Option<StrView>` emitted the literal default
untyped, a `%Span$u8`, into a `select` of `%StrView`s, and clang refused it
(rzsh).  One row per place the result lands (a let, an assignment, a return,
a call argument), and `Result<StrView, E>`.  The scalar arm's default is
emitted at the payload's type too: `Option<*u8>.unwrap_or("lit")`.
"""

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import assert_runs

pytestmark = pytest.mark.integration

HEAD = "import ritzlib.strview\nimport ritzlib.option\nimport ritzlib.result\n\n"


def _prog(defs, body):
    return f"{HEAD}{defs}\npub fn main() -> i32\n{body}"


# The ticket's repro: an array field read through `*M`.
FIELD = """\
struct M
    params: [4]StrView
    count: i32

fn param(m: *M, idx: i32) -> Option<StrView>
    if idx < 0 || idx >= m.count
        return None
    return Some(m.params[idx])
"""

LOCAL = """\
fn pick(i: i32) -> Option<StrView>
    var a: [2]StrView
    a[0] = "ab"
    a[1] = "xyz"
    return Some(a[i])
"""

POINTER = """\
fn at(p: *StrView, i: i32) -> Option<StrView>
    Some(p[i])
"""

POINT = """\
struct P
    x: i32
    y: i32

fn first(ps: *P, i: i32) -> Option<P>
    Some(ps[i])
"""

RESULTS = """\
fn ok_at(a: *StrView, i: i32) -> Result<StrView, i32>
    Ok(a[i])

fn err_at(a: *StrView, i: i32) -> Result<i32, StrView>
    Err(a[i])
"""

USER_ENUM = """\
enum Tok
    Word(StrView)
    End

fn word(a: *StrView, i: i32) -> Tok
    Tok.Word(a[i])

fn tok_len(t: Tok) -> i32
    match t
        Tok.Word(w) => w.len as i32
        _ => 0
"""

ARR3 = '    var a: [3]StrView\n    a[0] = "a"\n    a[1] = "bcd"\n    a[2] = "ef"\n'

# name: (program, exit code).
PAYLOAD_ROWS = {
    "some_field_through_pointer": (_prog(FIELD,
        '    var m: M\n    m.params[0] = "ab"\n    m.count = 1\n    let e: StrView = ""\n'
        "    let v: StrView = param(@m, 0).unwrap_or(e)\n    return v.len as i32 + 1\n"), 3),
    "some_local_array": (_prog(LOCAL,
        '    let e: StrView = ""\n    let v: StrView = pick(1).unwrap_or(e)\n    v.len as i32\n'), 3),
    "some_pointer_index": (_prog(POINTER, ARR3 +
        '    let e: StrView = ""\n    let v: StrView = at(@a[0], 1).unwrap_or(e)\n    v.len as i32\n'), 3),
    "some_user_struct": (_prog(POINT,
        "    var ps: [2]P\n    ps[1].x = 4\n    ps[1].y = 5\n"
        "    let q: P = first(@ps[0], 1).unwrap()\n    q.x + q.y\n"), 9),
    "ok_and_err": (_prog(RESULTS, ARR3 +
        "    var n: i32 = 0\n"
        "    match ok_at(@a[0], 1)\n        Ok(v) => n = n + v.len as i32\n        Err(_) => n = 100\n"
        "    match err_at(@a[0], 2)\n        Ok(_) => n = 100\n        Err(v) => n = n + v.len as i32\n"
        "    n\n"), 5),
    "user_enum_tuple_variant": (_prog(USER_ENUM, ARR3 + "    tok_len(word(@a[0], 1))\n"), 3),
}

LOOKUP = """\
fn lookup(hit: bool) -> Option<StrView>
    if hit
        return Some("home")
    return None

fn len_of(v: StrView) -> i32
    v.len as i32

fn res(hit: bool) -> Result<StrView, i32>
    if hit
        return Ok("home")
    Err(1)

fn cstr(hit: bool) -> Option<*u8>
    if hit
        return Some(c"home")
    None
"""

DIR_OR_ROOT = """\
fn dir_or_root(hit: bool) -> StrView
    return lookup(hit).unwrap_or("/")
"""

UNWRAP_OR_ROWS = {
    "let": (_prog(LOOKUP,
        '    let d: StrView = lookup(false).unwrap_or("/x")\n    d.len as i32\n'), 2),
    # The ticket's repro: an assignment.
    "assignment": (_prog(LOOKUP,
        '    var dir: StrView = "/"\n    dir = lookup(false).unwrap_or("/ab")\n'
        "    dir.len as i32\n"), 3),
    "return": (_prog(LOOKUP + "\n" + DIR_OR_ROOT,
        "    dir_or_root(false).len as i32 + dir_or_root(true).len as i32\n"), 5),
    "argument": (_prog(LOOKUP,
        '    len_of(lookup(false).unwrap_or("abcd")) + len_of(lookup(true).unwrap_or(""))\n'), 8),
    "result": (_prog(LOOKUP,
        '    let a: StrView = res(false).unwrap_or("xy")\n'
        '    let b: StrView = res(true).unwrap_or("xy")\n    a.len as i32 + b.len as i32\n'), 6),
    "scalar_pointer_payload": (_prog(LOOKUP,
        '    let p: *u8 = cstr(false).unwrap_or("q")\n    let h: *u8 = cstr(true).unwrap_or("q")\n'
        "    (*p - 'q') as i32 + (*h - 'h') as i32 + 1\n"), 1),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_struct_element_payload(tmp_path, compiler):
    assert_runs(compiler, tmp_path, PAYLOAD_ROWS)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_strview_unwrap_or_literal(tmp_path, compiler):
    assert_runs(compiler, tmp_path, UNWRAP_OR_ROWS)
