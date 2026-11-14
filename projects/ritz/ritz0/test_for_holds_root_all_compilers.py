"""AGAST #2439, LARB ruling R11 (second batch): a `for` over a place whose path
crosses an index into anything but an array holds an `@` for its whole body.

A `for` walks its iterable in place (#2387, §6.3): `for v in vs[0].a` reads
`vs[0].a` where it lives, in `vs`'s buffer. A push may move that buffer, so the
loop holds a shared loan, and §13.5's check (#2438) refuses a mutable borrow of
the place the index is into (`vs`), or of a place holding it, in the body:

    for v in vs[0].a
        vs.push(h)          # refused: `vs` is already borrowed as immutable
        vs[0].a[2] = 50     # fine: a write that can't move the buffer, and seen

The loan is on the base of the last such index: `s.vs[0].a` holds `s.vs`, and a
`*H` indexed (`p[0].a`) holds `p`. A use INSIDE that place (`vs[0]...`, `@&vs[1]`)
can't move the buffer and stays legal; `for v in vs` (the Vec itself, #2388) and
every array-rooted path (`h.a`, `hs[0].a`) hold nothing.

It's a definite-case check: a push through another path (a pointer to `vs`, a
callee reaching it) isn't seen. §6.3 keeps that limit.
"""

import re

import pytest

from test_borrow_param_ref_field import _compile
from test_ritz1_builtin_struct_shadow import _run_pkg
from test_ritz1_for_iterable import SELFHOSTED_BIN

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

PRELUDE = """\
import ritzlib.gvec

struct H
    a: [3]i32

struct S
    vs: Vec<H>

fn grow(v: @&Vec<H>)
    v.len = v.len

fn lend_vs(v:& Vec<H>)
    v.len = v.len

pub fn main() -> i32
    var vs: Vec<H> = vec_new<H>()
    var h: H
    h.a[0] = 1
    h.a[1] = 2
    h.a[2] = 3
    vs.push(h)
    var n: i32 = 0
"""

# The body's first line.
L = PRELUDE.count("\n") + 2


def _loop(head, body, tail="    return n\n"):
    """`for v in <head>` with `body` (each line already indented 8)."""
    return PRELUDE + f"    for v in {head}\n" + body + tail


def _msg(here, held, verb="mutable"):
    head = f"cannot assign to `{here}`" if verb == "assign" else f"cannot borrow `{here}` as {verb}"
    return f"{head} - `{held}` is already borrowed as immutable"


# name: (program, line:col, message)
CONFLICTS = {
    # A method taking `self: @&T`: the push the rule is for.
    "push": (_loop("vs[0].a", "        vs.push(h)\n"), f"{L}:9", _msg("vs", "vs")),
    "addr_mut": (_loop("vs[0].a", "        grow(@&vs)\n"), f"{L}:14", _msg("vs", "vs")),
    "bare_into_borrow": (_loop("vs[0].a", "        lend_vs(vs)\n"), f"{L}:17", _msg("vs", "vs")),
    "assign": (_loop("vs[0].a", "        vs = vec_new<H>()\n"), f"{L}:9", _msg("vs", "vs", "assign")),
    # Anywhere in the body, not only its first statement.
    "nested_in_body": (_loop("vs[0].a", "        n = n + v\n        if n > 1\n            vs.push(h)\n"),
                       f"{L + 2}:13", _msg("vs", "vs")),
    # The Vec is a field: the loan is on `s.vs`, and `s` holds it.
    "field_vec": (PRELUDE + "    var s: S = S { vs: vec_new<H>() }\n    s.vs.push(h)\n"
                  "    for v in s.vs[0].a\n        s.vs.push(h)\n    return n\n",
                  f"{L + 2}:9", _msg("s.vs", "s.vs")),
    # An index into a pointer holds the pointer.
    "pointer": (PRELUDE + "    var hs: [2]H\n    var p: *H = @hs[0]\n"
                "    for v in p[0].a\n        p = @hs[1]\n    return n\n",
                f"{L + 2}:9", _msg("p", "p", "assign")),
}


# name: (program, what it returns)
LEGAL = {
    # A write into the element can't move the buffer, and the loop sees it.
    "element_write_seen": (_loop("vs[0].a", "        vs[0].a[2] = 50\n        n = n + v\n"), 53),
    # A read of the Vec, and a mutable borrow inside it.
    "read_and_inner_borrow": (_loop("vs[0].a", "        n = n + v + vs.len() as i32\n"
                                    "        let q: @&H = @&vs[0]\n        q.a[1] = 2\n"), 9),
    # `for v in vs` reads `len` and `data` each pass: a push is safe (#2388).
    "walk_the_vec": (_loop("vs", "        if n == 0\n            vs.push(h)\n        n = n + 1\n"), 2),
    # Array-rooted paths hold nothing.
    "array_field": (_loop("h.a", "        h.a[2] = 50\n        n = n + v\n"), 53),
    # An index into an array: the storage can't move, so even the root is free.
    "array_index": (PRELUDE + "    var hs: [2]H\n    hs[0] = h\n    var gs: [2]H\n    gs[0] = h\n"
                    "    gs[0].a[1] = 9\n    for v in hs[0].a\n        hs = gs\n        n = n + v\n"
                    "    return n\n", 13),
    # The loan ends with the loop.
    "push_after": (_loop("vs[0].a", "        n = n + v\n",
                         "    vs.push(h)\n    return n + vs.len() as i32\n"), 8),
}


@pytest.fixture
def compile_with(ritz1_bin, tmp_path):
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _compile("ritz0", None, tmp_path, name, program)
        return _compile("ritz1", bins[compiler], tmp_path, name, program)
    return go


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    """build.py links gvec's allocator (ritzlib.memory) in."""
    def go(compiler, name, program):
        return _run_pkg(compiler, tmp_path, name, program)
    return go


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CONFLICTS))
def test_a_mutable_borrow_of_the_vec_in_the_body_is_refused(compile_with, compiler, name):
    program, where, message = CONFLICTS[name]
    comp, ll, _ = compile_with(compiler, name, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"accepted:\n{program}"
    assert not ll.exists()
    found = re.search(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert found, f"no location:\n{out[-2000:]}"
    assert (found.group(1), found.group(2).strip()) == (where, message)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(LEGAL))
def test_what_cant_move_the_buffer_runs(run_with, compiler, name):
    program, expected = LEGAL[name]
    assert run_with(compiler, name, program) == expected
