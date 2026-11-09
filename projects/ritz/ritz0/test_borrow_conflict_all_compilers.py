"""AGAST #2438, LARB rulings R11 and R11a: §13.5's first rule, checked the same on
all three compilers, for every mutable borrow, on overlapping places.

A borrow is of a PLACE: a root binding and its field (`.f`) and index (`[i]`)
steps. Two places overlap when one's path is a prefix of the other's; field names
must match, and any two indexes count as equal. While a binding holds an `@T` of
a place, or within the arguments of one call, each of these on an overlapping
place is a located error, which names both places:

    let p = @c.x
    bump(@&c.x)         # `@&p`
    lend(c.x)           # `p` bare into a `:&` param
    c.up()              # a method taking `self: @&T` or `self:& T`
    c = d               # `p = v`, or a write inside p (`c.x = 2`)
    c.y = 2             # fine: `c.y` doesn't overlap `c.x`

- The place's root is reached by fields and indexes with no pointer or reference
  on the way, so `@vs[0]` is a loan of `vs[_]`, and a push (on `vs`) overlaps it,
  as does a write into any element (`vs[1].a[2] = 9`: R11a's heads-up, angelo).
- A loan lasts to the end of the block its holder is declared in. There's no
  liveness analysis. Only a `let` or `var` DECLARED with the reference holds
  one; `p = @x` doesn't, and an argument's lasts for its call.
- `@x` held in a `*T` isn't a borrow (Aaron, #2371), and a `self: *T` receiver or
  a `self: @T` one isn't a mutable borrow.

Until this ticket only ritz0 checked `@&x` and `:&`, and nothing saw a receiver
or a write, so `let p: @H = @vs[0]` then `vs.push(h)` read freed memory.
"""

import re

import pytest

from test_borrow_param_ref_field import _compile, _run
from test_ritz1_for_iterable import SELFHOSTED_BIN

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

C = """\
struct C
    x: i32
    y: i32

impl C
    fn up(self: @&C)
        self.x = self.x + 1

    fn lend_up(self:& C)
        self.x = self.x + 1

    fn get(self: @C) -> i32
        return self.x

    fn poke(self: *C)
        self.y = 7

fn bump(p: @&i32)
    *p = *p + 1

fn lend(p:& i32)
    p = p + 1

fn lend_c(c:& C)
    c.x = c.x + 1

struct K
    k: i32

struct R
    a: K
    b: K

fn two(a: @&K, b: @&K) -> i32
    a.k = 1
    b.k = 2
    return a.k + b.k

fn and_k(a: @&K, k: @&i32) -> i32
    *k = 4
    return a.k

fn lend_k(a:& K)
    a.k = a.k + 1

"""

MAIN = ("pub fn main() -> i32\n    var n: i32 = 1\n    var c: C = C { x: 1, y: 0 }\n"
        "    var r: R = R { a: K { k: 1 }, b: K { k: 1 } }\n")



def _msg(here, held, verb="mutable", kind="immutable"):
    """The wording: `verb` is "assign", "mutable" or "immutable"."""
    head = f"cannot assign to `{here}`" if verb == "assign" else f"cannot borrow `{here}` as {verb}"
    return f"{head} - `{held}` is already borrowed as {kind}"


def _assign(here, held, kind="immutable"):
    return _msg(here, held, "assign", kind)


# name: (body after MAIN, the line:col it's refused at, the message). The body's
# first line is line L.
L = C.count("\n") + MAIN.count("\n") + 1
CONFLICTS = {
    # `@&x` (ritz0 has refused it since #2335).
    "addr_mut": ("    let p = @n\n    bump(@&n)\n    return *p\n",
                 f"{L + 1}:10", _msg("n", "n")),
    # `x` bare into a `:&` param.
    "bare_into_borrow": ("    let p = @n\n    lend(n)\n    return *p\n",
                         f"{L + 1}:10", _msg("n", "n")),
    "bare_struct_into_borrow": ("    let p = @c\n    lend_c(c)\n    return p.x\n",
                                f"{L + 1}:12", _msg("c", "c")),
    # A method taking `self: @&T` or `self:& T`.
    "receiver_mut_ref": ("    let p = @c\n    c.up()\n    return p.x\n",
                         f"{L + 1}:5", _msg("c", "c")),
    "receiver_lent": ("    let p = @c\n    c.lend_up()\n    return p.x\n",
                      f"{L + 1}:5", _msg("c", "c")),
    # `x = v` and writes into x's own storage.
    "assign": ("    let p = @n\n    n = 2\n    return *p\n",
               f"{L + 1}:5", _assign("n", "n")),
    "field_write": ("    let p = @c\n    c.x = 2\n    return p.x\n",
                    f"{L + 1}:5", _assign("c.x", "c")),
    "struct_assign": ("    let p = @c\n    c = C { x: 5, y: 5 }\n    return p.x\n",
                      f"{L + 1}:5", _assign("c", "c")),
    "element_write": ("    var a: [3]i32 = [1, 2, 3]\n    let p = @a\n    a[1] = 5\n    return p[1]\n",
                      f"{L + 2}:5", _assign("a[_]", "a")),
    # The holder's spellings: a typed `@T`, a `var`, a place inside the root.
    "typed_holder": ("    let p: @i32 = @n\n    n = 2\n    return *p\n",
                     f"{L + 1}:5", _assign("n", "n")),
    "var_holder": ("    var p: @C = @c\n    c.up()\n    return p.x\n",
                   f"{L + 1}:5", _msg("c", "c")),
    # R11a's refused rows: a place overlapping the loan's, either way round.
    "field_holder": ("    let p: @i32 = @c.x\n    c.up()\n    return *p\n",
                     f"{L + 1}:5", _msg("c", "c.x")),
    "field_holder_same_field": ("    let p: @i32 = @c.x\n    c.x = 2\n    return *p\n",
                                f"{L + 1}:5", _assign("c.x", "c.x")),
    "field_holder_whole": ("    let d: C = C { x: 4, y: 4 }\n    let p: @i32 = @c.x\n    c = d\n"
                           "    return *p\n",
                           f"{L + 2}:5", _assign("c", "c.x")),
    "field_holder_inside": ("    let p: @K = @r.a\n    r.a.k = 2\n    return p.k\n",
                            f"{L + 1}:5", _assign("r.a.k", "r.a")),
    "field_holder_addr_mut": ("    let p: @K = @r.a\n    let q: @&i32 = @&r.a.k\n    return p.k + *q\n",
                              f"{L + 1}:20", _msg("r.a.k", "r.a")),
    "field_holder_bare": ("    let p: @K = @r.a\n    lend_k(r.a)\n    return p.k\n",
                          f"{L + 1}:12", _msg("r.a", "r.a")),
    "element_holder": ("    var a: [3]i32 = [1, 2, 3]\n    let p: @i32 = @a[1]\n    a[1] = 5\n"
                       "    return *p\n",
                       f"{L + 2}:5", _assign("a[_]", "a[_]")),
    # Any two indexes count as equal.
    "element_holder_other_index": ("    var a: [3]i32 = [1, 2, 3]\n    let p: @i32 = @a[1]\n"
                                   "    a[2] = 5\n    return *p\n",
                                   f"{L + 2}:5", _assign("a[_]", "a[_]")),
    # Within one call's arguments.
    "args_overlap": ("    return and_k(@&r.a, @&r.a.k)\n",
                     f"{L}:25", _msg("r.a.k", "r.a", kind="mutable")),
    # An `@&T` holder: exactly one `@&`, so each of these is a second borrow.
    "mut_holder_receiver": ("    let p = @&c\n    c.up()\n    return p.x\n",
                            f"{L + 1}:5", _msg("c", "c", kind="mutable")),
    "mut_holder_assign": ("    let p = @&n\n    n = 2\n    return *p\n",
                          f"{L + 1}:5", _assign("n", "n", kind="mutable")),
    "mut_holder_shared": ("    let p = @&n\n    let q = @n\n    return *p + *q\n",
                          f"{L + 1}:13", _msg("n", "n", "immutable", "mutable")),
    "mut_holder_field_read_borrow": ("    let p = @&r.a\n    let q = @r.a.k\n    return p.k + *q\n",
                                     f"{L + 1}:13", _msg("r.a.k", "r.a", "immutable", "mutable")),
    # The loan lasts to the end of the holder's block, wherever the conflict is.
    "in_a_nested_block": ("    let p = @n\n    if n == 1\n        n = 2\n    return *p\n",
                          f"{L + 2}:9", _assign("n", "n")),
    "in_a_loop": ("    let p = @c\n    var i: i32 = 0\n    while i < 2\n        c.up()\n"
                  "        i = i + 1\n    return p.x\n",
                  f"{L + 3}:9", _msg("c", "c")),
    "both_in_a_block": ("    if n == 1\n        let p = @n\n        n = 2\n        return *p\n"
                        "    return 0\n",
                        f"{L + 2}:9", _assign("n", "n")),
    # A `:&` param is a place like any other (#2335).
    "lent_param_root": None,
}

LENT_PARAM_ROOT = C + """\
fn go(d:& C) -> i32
    let p = @d
    d.x = 3
    return p.x

""" + MAIN + "    return go(c)\n"

VEC = """\
import ritzlib.gvec

struct H
    a: [3]i32

pub fn main() -> i32
    var vs: Vec<H> = vec_new<H>()
    var h: H
    h.a[2] = 4
    vs.push(h)
"""

# `@vs[0]` is a loan of `vs[_]`, and a push, on `vs`, overlaps it: the push may
# move the buffer (#2425: ritz0 read the freed buffer).
VEC_CONFLICTS = {
    "element_then_push": (VEC + "    let p: @H = @vs[0]\n    vs.push(h)\n    return p.a[2]\n",
                          "12:5", _msg("vs", "vs[_]")),
    "whole_then_push": (VEC + "    let p: @Vec<H> = @vs\n    vs.push(h)\n    return p.len() as i32\n",
                        "12:5", _msg("vs", "vs")),
    "element_then_assign": (VEC + "    let p: @H = @vs[0]\n    vs = vec_new<H>()\n    return p.a[2]\n",
                            "12:5", _assign("vs", "vs[_]")),
    # A write inside the element, or any other: two indexes are equal.
    "element_then_element_write": (VEC + "    let p: @H = @vs[0]\n    vs[1].a[2] = 9\n    return p.a[2]\n",
                                   "12:5", _assign("vs[_].a[_]", "vs[_]")),
}


def _program(name):
    if name == "lent_param_root":
        return LENT_PARAM_ROOT
    return C + MAIN + CONFLICTS[name][0]


def _where(name):
    if name == "lent_param_root":
        return f"{LENT_PARAM_ROOT.count(chr(10), 0, LENT_PARAM_ROOT.index('    d.x = 3')) + 1}:5", _assign("d.x", "d")
    return CONFLICTS[name][1], CONFLICTS[name][2]


# What stays legal, and what each returns.
LEGAL = {
    # A read of the root, and a `self: @T` or `self: *T` receiver.
    "read": ("    let p = @n\n    let m: i32 = n + *p\n    return m\n", 2),
    "shared_receiver": ("    let p = @c\n    return c.get() + p.x\n", 2),
    "pointer_receiver": ("    let p = @c\n    c.poke()\n    return p.x + c.y\n", 8),
    "two_shared": ("    let p = @n\n    let q = @n\n    return *p + *q\n", 2),
    # `@x` held in a `*T` isn't a borrow (#2371).
    "raw_pointer_holder": ("    let p: *i32 = @n\n    let q: @&i32 = @&n\n    *q = 2\n    return *p\n", 2),
    "raw_pointer_holder_write": ("    let p: *C = @c\n    c.up()\n    c.x = c.x + 1\n    return p.x\n", 3),
    "raw_pointer_holder_lend": ("    let p: *i32 = @n\n    lend(n)\n    n = n + 1\n    return *p\n", 3),
    # A borrow in a block that has ended.
    "ended_block": ("    var k: i32 = 0\n    if n == 1\n        let p = @n\n        k = *p\n"
                    "    bump(@&n)\n    n = n + 1\n    return n + k\n", 4),
    "ended_loop_body": ("    var i: i32 = 0\n    while i < 2\n        let p = @c\n        i = i + p.x\n"
                        "    c.up()\n    return c.x + i\n", 4),
    # A borrow made for a call, or not held by a binding, ends with its statement.
    # An `@` no binding holds borrows nothing past its call: an `if` condition's
    # doesn't reach its body (angelo's `match @self.loca`).
    "unheld_condition": ("    if *(@n) == 1\n        n = 2\n        bump(@&n)\n    return n\n", 3),
    "call_argument": ("    let m: i32 = c.get()\n    bump(@&n)\n    n = n + m\n    return n\n", 3),
    # Writing through the holder is what it's for.
    "write_through_holder": ("    let p = @&c\n    p.x = 2\n    return c.x\n", 2),
    # R11a: disjoint places of one root don't conflict.
    "field_holder_other_field": ("    let p: @i32 = @c.x\n    c.y = 2\n    return *p + c.y\n", 3),
    "args_disjoint": ("    return two(@&r.a, @&r.b) + r.a.k + r.b.k\n", 6),
    "field_holder_other_bare": ("    let p: @K = @r.a\n    lend_k(r.b)\n    return p.k + r.b.k\n", 3),
    "mut_holder_other_field": ("    let p = @&r.a\n    r.b.k = 5\n    p.k = 2\n    return r.a.k + r.b.k\n", 7),
    # Another root is untouched.
    "other_root": ("    var m: i32 = 1\n    let p = @n\n    m = 2\n    bump(@&m)\n    return m + *p\n", 4),
    # A pointer's pointee isn't the pointer's.
    "through_a_pointer": ("    var q: *C = @c\n    let p = @q.x\n    q.x = 2\n    return *p\n", 2),
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
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _run("ritz0", None, tmp_path, name, program)
        return _run("ritz1", bins[compiler], tmp_path, name, program)
    return go


def _refusal(comp, ll, program):
    """`line:col: message` of the first located error."""
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"accepted:\n{program}"
    assert not ll.exists()
    found = re.search(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert found, f"no location:\n{out[-2000:]}"
    return found.group(1), found.group(2).strip()


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CONFLICTS))
def test_a_mutable_borrow_beside_a_loan_is_refused(compile_with, compiler, name):
    program = _program(name)
    comp, ll, _ = compile_with(compiler, name, program)
    assert _refusal(comp, ll, program) == _where(name)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(VEC_CONFLICTS))
def test_a_push_beside_a_loan_of_the_vec_is_refused(compile_with, compiler, name):
    program, where, message = VEC_CONFLICTS[name]
    comp, ll, _ = compile_with(compiler, name, program)
    assert _refusal(comp, ll, program) == (where, message)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_vec_element_loan_compiles_without_a_push(compile_with, compiler):
    """`@vs[0]` itself is fine, beside a read of the Vec and a write into
    another root."""
    program = (VEC + "    let p: @H = @vs[0]\n    h.a[1] = vs.len() as i32\n"
               "    return p.a[2] + h.a[1]\n")
    comp, ll, _ = compile_with(compiler, "vec_element", program)
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(LEGAL))
def test_what_isnt_a_conflict_runs(run_with, compiler, name):
    body, expected = LEGAL[name]
    assert run_with(compiler, name, C + MAIN + body) == expected


# An `assert`'s condition is checked like any expression: ritz0 skipped it, so
# `string_push_string(@&s, @s)` passed there and was refused on ritz1.
ASSERT_ARGS = """\
fn put(n: @&i32, v: @i32) -> i32
    *n = *v
    return 0

[[test]]
fn t() -> i32
    var x: i32 = 1
    assert put(@&x, @x) == 0
    return 0

pub fn main() -> i32
    return 0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_assert_condition_is_checked(compile_with, compiler):
    comp, ll, _ = compile_with(compiler, "assert_args", ASSERT_ARGS)
    assert _refusal(comp, ll, ASSERT_ARGS) == ("8:21", _msg("x", "x", "immutable", "mutable"))
