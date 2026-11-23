#!/usr/bin/env python3
"""A method call whose receiver is a module-level struct const (AGAST #4589).

    const NAME: StrView = "hello"
    NAME.as_ptr()     # ritz0: fine; ritz1: "cannot determine receiver type"

nexus's test_repos.ritz:1201 (`V1_WIKI.as_ptr()`) hit it.  emit_expr_method
(ritz1/src/emitter_expr_call.ritz) resolved an EXPR_IDENT receiver from
locals and globals (#2044) but not from consts.  A struct const is emitted as
a `%S` global (#189); its value is spilled to a slot and the method runs on
that copy, so no method can write the constant.

Each row runs on ritz0, ritz1 and ritz1_selfhosted and returns 42; any other
code names the check that failed.
"""

import pytest

from test_ref_into_value import COMPILERS, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

# StrView's own methods live in ritzlib.strview, which this harness doesn't
# link; `Name` has its shape, and nexus's `V1_WIKI.as_ptr()` is `./rz test
# nexus --compiler ritz1`'s.
NAME_DEF = """\
struct Name
    ptr: *u8
    len: i64

impl Name
    fn as_ptr(self: Name) -> *u8
        self.ptr
    fn at(self: Name, i: i64) -> u8
        self.ptr[i]

const NAME: Name = Name { ptr: c"hello", len: 5 }

"""

P_DEF = """\
struct P
    v: i64

impl P
    fn plus(self: *P, n: i64) -> i64
        self.v + n
    fn bump(self: *P) -> i64
        self.v = self.v + 1
        self.v

const P0: P = P { v: 40 }

"""

PROGRAMS = {
    # The ticket's shape: `NAME.as_ptr()` handed straight to a call.
    "as_ptr": NAME_DEF + """\
fn clen(p: *u8) -> i32
    var n: i32 = 0
    while p[n] != 0
        n = n + 1
    n

pub fn main() -> i32
    if clen(NAME.as_ptr()) != 5
        return 1
    if NAME.at(1) != 101
        return 2
    42
""",
}

# A `*self` method on a const runs on a copy of it, on every compiler (ritz0
# refused it as "Unknown variable: P0" until AGAST #4593).  The const is an
# LLVM `constant`: `bump` neither faults nor changes P0.
PTR_SELF = P_DEF + """\
pub fn main() -> i32
    if P0.bump() != 41 or P0.bump() != 41
        return 1
    if P0.v != 40
        return 2
    P0.plus(2) as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_method_on_a_struct_const(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, PROGRAMS[name]) == 42


@pytest.mark.parametrize("compiler", COMPILERS)
def test_pointer_self_runs_on_a_copy(tmp_path, compiler):
    assert _run(compiler, tmp_path, "ptr_self", PTR_SELF) == 42
