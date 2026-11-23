#!/usr/bin/env python3
"""AGAST #4588: a copy element read through a call's `@Vec<T>` is a copy.

LANGUAGE_SPEC §13.1: a struct built only from copy types is a copy type, and
only `Drop` makes a type move-only.  So `let r = t.regions()[0]`, with
`regions` returning `@Vec<D>` and `D` plain fields, copies `D` out (§13.2:
"by value it's a copy"), as `p[0]` with `p: @Vec<D>` already did.

    let r = t.get_regions()[0]   # prism test_damage.ritz:48
        # ritz1: "cannot move out of a reference": it typed the element as
        # the Vec itself (Vec is Drop), not D.  ritz0 accepted it.

A move-only element there is still "cannot move out of a reference", on every
compiler.

The second half of the ticket: a method named like a Vec method (`get`,
`swap`) on a type from another module made ritz1 check `Vec<L>.get`'s generic
body for every move-only L it had seen, though nothing called it
(gvec.ritz:212's `*(self.data + idx)`, prism test_text_rendering.ritz).  An
uncalled generic method is not checked (ritz0 never instantiates it).
"""

import pytest

from ref_rules import MOVE_OUT_OF_REF
from test_ref_into_value import COMPILERS, _assert_refused, _compile

pytestmark = pytest.mark.integration

# `{E}` is the element's fields; `{BODY}` reads it.
HOLDER = """\
import ritzlib.gvec
import ritzlib.string

struct R
    x: i32

struct D
{E}

struct T
    v: Vec<D>

impl T
    fn regions(self: @T) -> @Vec<D>
        @self.v

fn f(t: @T) -> i32
{BODY}
"""

COPY_FIELDS = "    r: R\n    w: u64\n"
DROP_FIELDS = "    s: String\n"

MAIN = "\npub fn main() -> i32\n    0\n"


def _compiles(compiler, tmp_path, name, src):
    comp, ll, _ = _compile(compiler, tmp_path, name, src)
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused {name}:\n{(comp.stdout + comp.stderr)[-1500:]}"


def _holder(fields, body):
    return HOLDER.replace("{E}", fields.rstrip("\n")).replace("{BODY}", body.rstrip("\n"))


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_copy_element_of_a_call_result_is_copied(tmp_path, compiler):
    """`t.regions()[0]` copies a plain struct out: it compiles.

    Compiled, not run: the refusal was the compiler's, and a Vec program
    needs the allocator runtime this harness doesn't link."""
    src = _holder(COPY_FIELDS, "    let d = t.regions()[0]\n    d.r.x + d.w as i32\n") + MAIN
    _compiles(compiler, tmp_path, "copy_elem", src)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_move_only_element_of_a_call_result_does_not_move_out(tmp_path, compiler):
    """A Drop element behind the same call stays refused (R1, §13.2)."""
    marked = _holder(DROP_FIELDS, "    let d = ^t.regions()[0]\n    0\n") + MAIN
    _assert_refused(compiler, tmp_path, "drop_elem", marked, MOVE_OUT_OF_REF)


# M's own `get` beside a `Vec<L>` of a move-only L: no Vec method is called.
SAME_NAME = """\
import ritzlib.gvec
import ritzlib.string

struct L
    s: String

struct M
    v: Vec<L>

impl M
    fn new() -> M
        M { v: vec_new<L>() }

    fn get(self: @M, i: i32) -> i32
        i

    fn swap(self: @M) -> i32
        0

fn f() -> i32
{BODY}

pub fn main() -> i32
    0
"""

# How the receiver is had: what ritz1 couldn't type, and so wanted `get` and
# `swap` on every generic instance.
RECEIVERS = {
    "let": "    let m = M.new()\n    m.get(0) + m.swap()\n",
    "chained": "    M.new().get(0) + M.new().swap()\n",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("receiver", sorted(RECEIVERS))
def test_a_same_named_method_instantiates_no_vec_method(tmp_path, compiler, receiver):
    """`m.get(0)` is M's `get`: `Vec<L>.get`'s body is never checked at L."""
    _compiles(compiler, tmp_path, f"same_name_{receiver}", SAME_NAME.replace("{BODY}", RECEIVERS[receiver].rstrip("\n")))
