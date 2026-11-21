"""ritz1: a string literal into an impl method's `StrView` param (AGAST #3495).

THE DEFECT

ritz1 emits a bare `"..."` as a `%Span$u8`, and an un-annotated `let x =
"..."` local is a `Span$u8` too (#98, #2103). The free-call and UFCS arms
rebuild such an argument as the layout-equal `%StrView` when the param is a
`StrView` (emit_strview_from_lit). The impl method arms didn't: both the
static arm (`Foo.mk("abcd")`) and the instance arm (`f.add("abcd")`) passed
the `%Span$u8` register under `%StrView`, and clang refused it ("defined with
type '%"Span$u8"' but expected '%StrView'"), unlocated.

Found by LARB R66 step 1: once ritzlib's String has a real `impl String`,
ritz1 dispatches `String.from("x")` and `s.push_str("x")` through these arms
instead of the UFCS table, so every such call in the tree broke.

Covered: a literal and a literal local, into the static and the instance arm,
as the first and a later param. Each program returns 42, else a distinct
code per failed check. ritz0 is the oracle.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

PRELUDE = """\
struct Foo
    n: i64

impl Foo
    pub fn mk(sv: StrView) -> i64
        return sv.len

    pub fn mk2(k: i64, sv: StrView) -> i64
        return k * sv.len

    pub fn add(self: @&Foo, sv: StrView) -> i64
        self.n = self.n + sv.len
        return self.n

    pub fn add2(self: @Foo, k: i64, sv: StrView) -> i64
        return self.n + k * sv.len
"""

STATIC = PRELUDE + """
fn main() -> i32
    let x = "xyz"
    if Foo.mk("abcd") != 4
        return 1
    if Foo.mk(x) != 3
        return 2
    if Foo.mk2(2, "ab") != 4
        return 3
    if Foo.mk2(3, x) != 9
        return 4
    return 42
"""

INSTANCE = PRELUDE + """
fn main() -> i32
    var f: Foo = Foo { n: 1 }
    let x = "xyz"
    if f.add("abcd") != 5
        return 1
    if f.add(x) != 8
        return 2
    if f.add2(2, "ab") != 12
        return 3
    if f.add2(1, x) != 11
        return 4
    return 42
"""

CASES = {"static": STATIC, "instance": INSTANCE}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, CASES[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_impl_strview_lit_arg(ritz1_bin, tmp_path, name):
    """Before the fix: `call ... (%StrView %<Span$u8>)` -> clang error."""
    assert _run("ritz1", tmp_path, name, CASES[name]) == 42
