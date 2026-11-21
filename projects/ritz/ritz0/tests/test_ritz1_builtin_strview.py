"""Regression tests for AGAST #2043: StrView is a builtin struct in ritz1.

    struct Box
        value: StrView
    ...
    return (b.value.len + 37) as i32     # ritz0: 42
                                         # ritz1: "unhandled EXPR_MEMBER"

A bare `"..."` literal is a StrView (AGAST #98), so a program can name the
type without importing anything.  ritz0 materialises the `{ *u8, i64 }`
struct on demand (`_builtin_strview` in emitter_llvmlite.py), but ritz1's
find_struct only knew StrView's layout once `ritzlib.strview`'s struct def
was loaded, so a field read through a StrView-typed field failed closed.

Only `with_import` imports anything.  Each returns 42 when correct and a
distinct small code naming the failed check otherwise.  ritz0 is the oracle.
"""

import subprocess

import pytest

from test_ritz1_call_result_member import EXPECTED, RITZ1_BIN, RITZ_ROOT, _run

BOX = """\
struct Box
    value: StrView

fn mk() -> Box
    Box { value: "hello" }
"""

PROGRAMS = {
    # The ticket's repro: a field of a StrView field of a local.
    "local_field_len": BOX
    + """\
pub fn main() -> i32
    let b = mk()
    return (b.value.len + 37) as i32
""",
    # `.ptr` resolves too, and points at the literal's bytes.
    "local_field_ptr": BOX
    + """\
pub fn main() -> i32
    let b = mk()
    let p: *u8 = b.value.ptr
    if *p != 104
        return 1
    if *(p + 4) != 111
        return 2
    return 42
""",
    # Two levels of nesting, then the StrView's field.
    "nested_field_len": BOX
    + """\
struct Outer
    tag: i32
    box: Box

pub fn main() -> i32
    let o = Outer { tag: 7, box: mk() }
    if o.box.value.len != 5
        return 1
    return (o.box.value.len + o.tag as i64 + 30) as i32
""",
    # Through a pointer to the enclosing struct.
    "ptr_field_len": BOX
    + """\
fn len_of(b: *Box) -> i64
    b.value.len

pub fn main() -> i32
    var b = mk()
    return (len_of(@b) + 37) as i32
""",
    # Writing a StrView field's field, then reading it back.
    "assign_field_len": BOX
    + """\
pub fn main() -> i32
    var b = mk()
    b.value.len = 2
    if b.value.len != 2
        return 1
    return (b.value.len + 40) as i32
""",
    # A StrView parameter and a StrView local, read directly.
    "param_and_local": """\
fn n(s: StrView) -> i64
    s.len

pub fn main() -> i32
    let v: StrView = "abcd"
    if v.len != 4
        return 1
    return (n(v) + n("hello world") + 27) as i32
""",
    # With the import, its StrView is the one used (no duplicate `%StrView`).
    # Field reads only: the harness links no ritzlib objects.
    "with_import": "import ritzlib.strview\n\n"
    + BOX
    + """\
pub fn main() -> i32
    let b = mk()
    return (b.value.len + 37) as i32
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_builtin_strview(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
def test_ritz1_rejects_a_strview_of_another_layout(ritz1_bin, tmp_path):
    """String literals are lowered to `{ ptr, i64 }`, so a source StrView of
    any other shape is a clean error, not a silent shadow.  (ritz0 has no
    oracle here: it crashes in llvmlite's insertvalue.)"""
    src = tmp_path / "bad.ritz"
    src.write_text(
        "struct StrView\n    a: i32\n\n"
        "pub fn main() -> i32\n"
        '    let v: StrView = "abc"\n'
        "    return v.a\n"
    )
    comp = subprocess.run(
        [
            str(RITZ1_BIN),
            str(src),
            "-o",
            str(tmp_path / "bad.ll"),
            "-I",
            str(RITZ_ROOT),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert comp.returncode != 0
    assert "struct StrView must be { ptr: *u8, len: i64 }" in comp.stderr
