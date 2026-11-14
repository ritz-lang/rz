"""A method call evaluates its receiver exactly once (AGAST #2261).

`_emit_method_call` emitted a non-identifier receiver once to learn its type
and again to pass it, so `make(1).peek()` ran `make` twice and a chain doubled
at every link. Each program counts its side effects in `MADE`, and the exit
status is `MADE * 10 + DROPS`. Every route a receiver can take has a case:
each kind of `self`, generics, traits, `dyn`, the built-in methods that bypass
the impl table, places whose operands have side effects, and receivers inside
argument positions.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from const_eval import evaluate_array_sizes

from emitter_llvmlite import LLVMEmitter
from lexer import tokenize
from parser import Parser
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PRELUDE = """\
trait Drop
    fn drop(self: @&Self)

trait Speak
    fn say(self: @Self) -> i32

var MADE: i32 = 0
var DROPS: i32 = 0
var LAST: i32 = 0

struct T
    id: i32

impl Drop for T
    fn drop(self: @&T)
        DROPS = DROPS + 1
        LAST = self.id

impl T
    fn peek(self: @T) -> i32
        return self.id

    fn bump(self: @&T) -> i32
        self.id = self.id + 5
        return self.id

    fn burn(self: T) -> i32
        return self.id

    fn again(self: @T) -> T
        MADE = MADE + 1
        return T { id: self.id }

struct P
    x: i32

impl Speak for P
    fn say(self: @P) -> i32
        return self.x

impl P
    fn get(self: @P) -> i32
        return self.x

    fn val(self: P) -> i32
        return self.x

    fn bump(self: @&P) -> i32
        self.x = self.x + 1
        return self.x

    fn borrow_mut(self:& P) -> i32
        return self.x

    fn next(self: @P) -> P
        return P { x: self.x + 1 }

    fn other(self: @P, q: @P) -> i32
        return q.x

struct W
    p: P

struct G<X>
    v: X

impl<X> G<X>
    fn get(self: @G<X>) -> X
        return self.v

# Its own `abs`, so the float intrinsics have to let it through.
struct A
    v: i32

impl A
    fn abs(self: @A) -> i32
        return self.v

fn make(id: i32) -> T
    MADE = MADE + 1
    return T { id: id }

fn mp() -> P
    MADE = MADE + 1
    return P { x: 1 }

fn mw() -> W
    MADE = MADE + 1
    return W { p: P { x: 1 } }

fn mg() -> G<i32>
    MADE = MADE + 1
    return G<i32> { v: 1 }

fn ma() -> A
    MADE = MADE + 1
    return A { v: 1 }

fn mi() -> u32
    MADE = MADE + 1
    return 8

fn mf() -> f64
    MADE = MADE + 1
    return 1.5

fn idx() -> i64
    MADE = MADE + 1
    return 0

# Hand back what they were given, as a side effect in a place's root.
fn mq(p: *P) -> *P
    MADE = MADE + 1
    return p

fn pw(w: *W) -> *W
    MADE = MADE + 1
    return w

fn take(n: i32) -> i32
    return n

fn look(p: @P) -> i32
    return p.x

"""

# Only the span cases carry this, so a gap in it can't fail every program.
SPAN = """\
fn ms() -> Span<u8>
    MADE = MADE + 1
    return Span.empty()

"""

# ritz1 evaluates these receivers once too, where it can compile them. What's
# missing is something else, so each row cites its own ticket.
BOTH_RITZ1 = ("ritz1", "ritz1_selfhosted")
NO_SPAN_INTRINSIC = {c: 3125 for c in BOTH_RITZ1}
NO_CALL_RANGE_START = {c: 3126 for c in BOTH_RITZ1}
NO_RVALUE_ARGS = {c: 2297 for c in BOTH_RITZ1}
NO_DYN_RETURN = {c: 2298 for c in BOTH_RITZ1}
NO_CALL_ROOTED_PLACE = {c: 2299 for c in BOTH_RITZ1}

ARRAY = "var arr: [2]P = [P { x: 1 }, P { x: 2 }]\n    "
NESTED = "var arr: [2]W = [W { p: P { x: 1 } }, W { p: P { x: 2 } }]\n    "

# name -> (body of `g`, expected MADE, expected DROPS, {compiler: gap ticket})
CASES = {
    # The ticket's program, and each kind of `self` on a Drop type.
    "lent_self": ("make(1).peek()", 1, 1, {}),
    "mut_self": ("make(1).bump()", 1, 1, {}),
    "value_self": ("make(1).burn()", 1, 1, {}),
    # The same on a type that copies.
    "copy_lent_self": ("mp().get()", 1, 0, {}),
    "copy_value_self": ("mp().val()", 1, 0, {}),
    "copy_mut_self": ("mp().bump()", 1, 0, {}),
    "copy_borrow_param_self": ("mp().borrow_mut()", 1, 0, {}),
    "generic": ("mg().get()", 1, 0, {}),
    "trait_impl": ("mp().say()", 1, 0, {}),
    "grouped": ("(mp()).get()", 1, 0, {}),
    # A chain doubled at every link: 2, then 6 calls for two links.
    "chain": ("make(1).again().peek()", 2, 2, {}),
    "chain_long": ("make(1).again().again().again().peek()", 4, 4, {}),
    # A by-value struct a call returns names the next link's impl (#2295),
    # and the field read off the chain's end.
    "chain_copy": ("mp().next().next().next().get()", 1, 0, {}),
    "chain_copy_field": ("take(mp().next().next().x)", 1, 0, {}),
    # Built-ins that never reach the impl table.
    "bitops": ("mi().clz()", 1, 0, {}),
    "float": ("mf().abs()", 1, 0, {}),
    "user_abs_past_float": ("ma().abs()", 1, 0, {}),
    "span_len": ("ms().len()", 1, 0, {}),
    "span_ptr": ("ms().ptr()", 1, 0, NO_SPAN_INTRINSIC),
    "span_is_empty": ("ms().is_empty()", 1, 0, NO_SPAN_INTRINSIC),
    "span_slice": ("ms().slice(0, 0)", 1, 0, NO_SPAN_INTRINSIC),
    # A place is emitted for its type and again for its address.
    "index_lent": (ARRAY + "arr[idx()].get()", 1, 0, {}),
    "index_mut": (ARRAY + "arr[idx()].bump()", 1, 0, {}),
    "index_value": (ARRAY + "arr[idx()].val()", 1, 0, {}),
    "index_then_field_lent": (NESTED + "arr[idx()].p.get()", 1, 0, {}),
    "index_then_field_value": (NESTED + "arr[idx()].p.val()", 1, 0, {}),
    # The same with the side effect at the root of the place.
    "index_of_call": ("var p = P { x: 1 }\n    mq(@p)[0].get()", 1, 0,
                      NO_CALL_ROOTED_PLACE),
    # AGAST #2526: `(*f()).p` names the struct `*f()` loads.
    "field_through_deref": ("var w = W { p: P { x: 1 } }\n    (*pw(@w)).p.get()", 1, 0, {}),
    # `a[lo..hi]` is a slice, not a place, and its range is not a value.
    "span_range_index": ("var s = ms()\n    s[idx()..0].len()", 2, 0, NO_CALL_RANGE_START),
    "span_range_end": ("var s = ms()\n    s[0..idx()].len()", 2, 0, {}),
    # A field of an rvalue isn't a place, but dispatch treats it as one.
    "field_of_rvalue": ("mw().p.get()", 1, 0, {"ritz0": 2294}),
    # Inside an argument.
    "in_argument": ("take(mp().get())", 1, 0, {}),
    "in_a_borrowed_local": ("let t = mp().next()\n    look(@t)", 1, 0, {}),
    "in_a_method_argument_local": ("var s = P { x: 1 }\n    let t = mp().next()\n    s.other(@t)", 1, 0, {}),
    "in_condition": ("if mp().get() == 1\n        return 0", 1, 0, {}),
}

TEMPLATE = """\
fn g() -> i32
    {body}
    return 0

pub fn main() -> i32
    g()
    return MADE * 10 + DROPS
"""

# name -> (whole program after the prelude, expected exit status, gaps)
PROGRAMS = {
    # A trait object goes through the vtable, not the impl table.
    "dyn_receiver": ("""\
fn md(p: @P) -> dyn Speak
    MADE = MADE + 1
    return p as dyn Speak

pub fn main() -> i32
    var held = P { x: 7 }
    let r = md(@held).say()
    return MADE * 10 + r
""", 17, NO_DYN_RETURN),

    # One value: what `bump` wrote is what `drop` sees.
    "drop_sees_the_mutation": ("""\
fn g() -> i32
    make(1).bump()
    return 0

pub fn main() -> i32
    g()
    return LAST * 10 + DROPS
""", 61, {}),

    # So on a method's result: `again`'s temporary is the one `bump` writes
    # and the one dropped first (AGAST #2262).
    "drop_sees_the_mutation_chain": ("""\
fn g() -> i32
    var t = make(2)
    t.again().bump()
    return LAST

pub fn main() -> i32
    let last = g()
    return last * 10 + DROPS
""", 72, {}),

    # The receiver is evaluated before the arguments, and each once.
    # A loop body is emitted once: each pass evaluates the receiver once.
    "in_a_loop": ("""\
fn g() -> i32
    var i = 0
    while i < 3
        make(1).peek()
        i = i + 1
    return 0

pub fn main() -> i32
    g()
    return MADE * 10 + DROPS
""", 33, {}),

    # One body, emitted per instantiation: what the first emission evaluated
    # doesn't carry over to the second.
    "generic_body_twice": ("""\
fn both<X>(x: X) -> i32
    return mp().get()

pub fn main() -> i32
    both<i32>(1)
    both<i64>(2)
    return MADE
""", 2, {}),

    # The value the method returns is the receiver's, not another evaluation's.
    "reads_the_value_it_evaluated": ("""\
fn counted() -> P
    MADE = MADE + 1
    return P { x: MADE }

pub fn main() -> i32
    return counted().get() * 10 + MADE
""", 11, {}),
}


def _params(table):
    out = []
    for name in sorted(table):
        gaps = table[name][-1]
        for compiler in COMPILERS:
            marks = []
            if compiler in gaps:
                marks.append(pytest.mark.xfail(
                    strict=True,
                    reason=f"AGAST #{gaps[compiler]}: {compiler} can't run this "
                           f"program correctly yet"))
            out.append(pytest.param(compiler, name, marks=marks,
                                    id=f"{compiler}-{name}"))
    return out


def _run(request, tmp_path, compiler, program):
    src = tmp_path / "main.ritz"
    src.write_text(PRELUDE + program)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        comp = subprocess.run([str(RITZ1_BUILD / compiler), str(src), "-o", str(ll)],
                              cwd=tmp_path, env=env, capture_output=True, text=True,
                              timeout=300)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
    exe = tmp_path / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.parametrize("compiler,name", _params(CASES))
def test_receiver_evaluated_once(request, tmp_path, compiler, name):
    body, made, drops, _ = CASES[name]
    prefix = SPAN if name.startswith("span_") else ""
    rc = _run(request, tmp_path, compiler, prefix + TEMPLATE.format(body=body))
    assert rc == made * 10 + drops, (
        f"{compiler} {name}: exit {rc}, expected MADE={made} DROPS={drops}")


@pytest.mark.parametrize("compiler,name", _params(PROGRAMS))
def test_receiver_program(request, tmp_path, compiler, name):
    program, expected, _ = PROGRAMS[name]
    rc = _run(request, tmp_path, compiler, program)
    assert rc == expected, f"{compiler} {name}: exit {rc}, expected {expected}"


def test_nothing_outlives_the_call():
    """What a call evaluated is keyed by id(expr), and a node built during
    desugaring can be freed and its id reused: a stale entry would hand a later
    expression another's value, in a block that may not even dominate it."""
    source = """\
struct P
    x: i32

impl P
    fn get(self: @P) -> i32
        return self.x

fn mp() -> P
    return P { x: 1 }

pub fn main() -> i32
    var arr: [1]P = [P { x: 1 }]
    return mp().get() + arr[0].get()
"""
    module = Parser(tokenize(source)).parse_module()
    assert evaluate_array_sizes(module) == []  # as ritz0.py does before emitting
    emitter = LLVMEmitter()
    emitter.emit_module(module)
    assert emitter._evaluated_once == {}
