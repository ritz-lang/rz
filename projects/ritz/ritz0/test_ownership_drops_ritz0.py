"""ritz0 ownership details beyond test_ownership_free_count.py (AGAST #2157).

test_ownership_free_count.py pins one rule per case on all three compilers.
These pin the ritz0-specific edges #2157 had to get right on the way:

  * move-vs-copy comes from Drop (LANGUAGE_SPEC §13.1), not a hard-coded
    list: generic copy types such as `Span<u8>` (#1489) and `Option<i64>`
    (#1548) copy, while `Option<Tracked>` and a struct holding a `Tracked`
    move;
  * a moved-from binding is never dropped, whichever kind of binding it is
    (`let`, `var`, parameter) and on whichever path it moved (drop flags);
  * `break` leaves only the scopes inside the innermost loop;
  * a value lent to an `@T` or `name:& T` parameter (auto-borrow) is not
    moved, and a write through `:&` reaches the caller (AGAST #1315);
  * a type with its own `drop` runs it before its fields' drops;
  * a match arm binding one payload of several owns them all (AGAST #2177);
  * a `name:& T` parameter can't be moved out of, and what reads it instead
    leaves the caller the only owner (AGAST #2231);
  * a move out of a nested field `a.b.c` is tracked per path, so its parents
    are partly moved and their other fields still drop (AGAST #2232).

Exit statuses encode what the program observed, as in the free-count test.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent

PRELUDE = """\
trait Drop
    fn drop(self: @&Self)

var DROPS: i32 = 0
var ORDER: i32 = 0

struct Tracked
    id: i32

impl Drop for Tracked
    fn drop(self: @&Tracked)
        DROPS = DROPS + 1
        ORDER = ORDER * 10 + self.id

struct Holder
    t: Tracked
    n: i32

# Its own drop (id 9) runs before its field's (the Tracked's id).
struct Owner
    t: Tracked

impl Drop for Owner
    fn drop(self: @&Owner)
        DROPS = DROPS + 1
        ORDER = ORDER * 10 + 9

fn make(id: i32) -> Tracked
    return Tracked { id: id }

fn consume(t: Tracked) -> i32
    return t.id

fn peek(t: @Tracked) -> i32
    return t.id

"""


def _compile(tmp_path, body):
    src = tmp_path / "main.ritz"
    src.write_text(PRELUDE + body)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    return comp, ll


def _run(tmp_path, body):
    comp, ll = _compile(tmp_path, body)
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz0 failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
    exe = tmp_path / "main"
    link = subprocess.run(["clang", str(ll), "-o", str(exe), "-nostdlib"],
                          cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-2000:]
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


# A move-only enum with a two-field variant (AGAST #2177).
PAIR = """\
enum P
    Two(Tracked, Tracked)
    No

"""

RUNS = {
    # #1489: a generic struct of copy fields copies.
    "span_copies": ("""\
import ritzlib.span

fn total(s: Span<u8>) -> i64
    return s.len

pub fn main() -> i32
    var buf: [4]u8
    let s = Span<u8> { ptr: @buf[0], len: 4 }
    let t = s
    return (total(s) + total(s) + t.len) as i32
""", 12),

    # #1548: Option of a copy type copies; matching it twice is fine.
    "option_copy_copies": ("""\
import ritzlib.option

fn get(o: Option<i64>) -> i64
    match o
        Some(v) => v
        None => 0

pub fn main() -> i32
    let o: Option<i64> = Some(5)
    let p = o
    return (get(o) + get(o) + get(p)) as i32
""", 15),

    # AGAST #1315: `:&` lends. Both writes reach the caller's value, nothing
    # drops during the calls (exit 30 + 0), and the owner drops it once.
    "mut_borrow_param_lends": ("""\
fn bump(t:& Tracked)
    t.id = t.id + 1

fn f() -> i32
    var t = make(1)
    bump(t)
    bump(t)
    return t.id * 10 + DROPS

pub fn main() -> i32
    let r = f()
    return r + DROPS
""", 31),

    # The same through a field: the holder still owns and drops it, once.
    "mut_borrow_of_field_lends": ("""\
fn bump(t:& Tracked)
    t.id = t.id + 1

fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    bump(h.t)
    bump(h.t)
    return h.t.id * 10 + DROPS

pub fn main() -> i32
    let r = f()
    return r + DROPS
""", 31),

    # The same through a method receiver.
    "mut_borrow_receiver_lends": ("""\
impl Tracked
    fn bump(self:& Tracked)
        self.id = self.id + 1

fn f() -> i32
    var t = make(1)
    t.bump()
    t.bump()
    return t.id * 10 + DROPS

pub fn main() -> i32
    let r = f()
    return r + DROPS
""", 31),

    # A moved `let` is not dropped again by its scope.
    "let_moved_not_dropped": ("""\
fn f() -> i32
    let t = make(1)
    consume(t)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11),

    # A by-value param passed on is moved: fwd must not drop it as well.
    "param_forwarded": ("""\
fn fwd(t: Tracked) -> i32
    return consume(t)

pub fn main() -> i32
    fwd(make(1))
    return DROPS
""", 1),

    # Moved on one path only: dropped by f's scope on the other.
    "conditional_move": ("""\
fn f(c: i32)
    var t = make(1)
    if c > 0
        consume(t)

pub fn main() -> i32
    f(1)
    f(0)
    return DROPS
""", 2),

    # Assigning to a moved-from binding drops nothing; it owns again.
    "assign_after_move": ("""\
fn f() -> i32
    var t = make(1)
    consume(t)
    t = make(2)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 12),

    # `break` in the inner loop drops the inner body's binding only; the
    # outer body's binding is dropped once per outer iteration.
    "nested_loop_break": ("""\
fn f() -> i32
    var i = 0
    while i < 2
        var o = make(1)
        var j = 0
        while j < 5
            var t = make(2)
            if j == 1
                break
            j = j + 1
        i = i + 1
    return DROPS

pub fn main() -> i32
    return f()
""", 6),

    # Auto-borrow into an `@Tracked` param is a loan, not a move.
    "autoborrow_is_not_a_move": ("""\
fn f() -> i32
    var t = make(3)
    let a = peek(t)
    let b = peek(t)
    return a + b + DROPS

pub fn main() -> i32
    let inner = f()
    return inner * 10 + DROPS
""", 61),

    # Its own drop first (9), then its Tracked field (5).
    "own_drop_then_fields": ("""\
fn f()
    var o = Owner { t: make(5) }

pub fn main() -> i32
    f()
    return ORDER
""", 95),

    # A struct literal field moves the binding into the struct.
    "move_into_struct_field": ("""\
fn f()
    var t = make(4)
    var h = Holder { t: t, n: 1 }

pub fn main() -> i32
    f()
    return DROPS
""", 1),

    # Returning a binding from a nested block moves it out; the others drop.
    "return_from_nested_block": ("""\
fn build(c: i32) -> Tracked
    var a = make(1)
    if c > 0
        var b = make(2)
        return b
    return make(3)

pub fn main() -> i32
    var t = build(1)
    let before = ORDER
    return before
""", 1),

    # AGAST #2177: an arm binding one move-only payload of several owns the
    # whole payload; the unbound `_` one drops with its bindings, at the
    # arm's end (ritz1 binds a single payload only, so these are ritz0's).
    "match_pair_payload_wildcard": (PAIR + """\
fn f() -> i32
    var s = P.Two(make(1), make(2))
    match s
        Two(a, _) => a.id
        _ => 0
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 22),

    # One payload moved on, the other dropped at the arm's end: once each.
    "match_pair_payload_one_moved": (PAIR + """\
fn f() -> i32
    var s = P.Two(make(1), make(2))
    match s
        Two(a, b) => consume(b)
        _ => 0
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 22),
}

REJECTS = {
    "option_tracked_after_move": ("""\
fn take(o: Option<Tracked>) -> i32
    return 0

pub fn main() -> i32
    var o: Option<Tracked> = Some(make(1))
    take(o)
    take(o)
    return 0
""", "o"),

    "let_after_move": ("""\
pub fn main() -> i32
    let t = make(1)
    consume(t)
    return t.id
""", "t"),
}


# Reads of a `name:& T` parameter (AGAST #2231): the caller stays the only
# owner, so one value drops once.
LENT_READS = {
    "let_as_reference": """\
fn g(t:& Tracked) -> i32
    let p: @Tracked = t
    return p.id
""",
    "let_as_pointer": """\
fn g(t:& Tracked) -> i32
    let p: *Tracked = t
    return p.id
""",
    "relend": """\
fn h(t:& Tracked) -> i32
    return t.id

fn g(t:& Tracked) -> i32
    return h(t) + peek(t)
""",
}

# Moves out of a `name:& T` parameter (AGAST #2231): each of these used to
# compile and drop one value twice.
LENT_MOVES = {
    "call": ("fn g(t:& Tracked) -> i32\n    return consume(t)\n", "t"),
    "let": ("fn g(t:& Tracked) -> i32\n    let u = t\n    return u.id\n", "t"),
    "deref": ("fn g(t:& Tracked) -> i32\n    return consume(*t)\n", "t"),
    "field": ("fn g(h:& Holder) -> i32\n    return consume(h.t)\n", "h"),
}


@pytest.mark.parametrize("name", sorted(LENT_READS))
def test_ritz0_lent_read_drops_once(tmp_path, name):
    rc = _run(tmp_path, LENT_READS[name] + """
fn f()
    var t = make(1)
    g(t)

pub fn main() -> i32
    f()
    return DROPS
""")
    assert rc == 1, f"{name}: one value dropped {rc} times"


def test_ritz0_lent_match_drops_once(tmp_path):
    rc = _run(tmp_path, """
enum Slot
    Full(Tracked)
    Empty

fn g(s:& Slot) -> i32
    match s
        Full(t) => return t.id
        Empty => return 0

fn f()
    var s = Slot.Full(make(1))
    g(s)

pub fn main() -> i32
    f()
    return DROPS
""")
    assert rc == 1, f"one value dropped {rc} times"


@pytest.mark.parametrize("name", sorted(LENT_MOVES))
def test_ritz0_move_out_of_lent_param_rejected(tmp_path, name):
    body, param = LENT_MOVES[name]
    comp, _ = _compile(tmp_path, body + "\npub fn main() -> i32\n    return 0\n")
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"accepted a move out of a borrow:\n{out[-1000:]}"
    assert "Traceback" not in out, out[-2000:]
    assert f"cannot move out of borrowed parameter `{param}`" in out, out[-2000:]


# Moves out of a nested field (AGAST #2232). `m.d.t` is 1, `m.d.u` 2, `m.x` 3.
NESTED = """\
struct Deep
    t: Tracked
    u: Tracked
    n: i32

struct Mid
    d: Deep
    x: Tracked

struct Top
    m: Mid

type DeepAlias = Deep

struct Aliased
    d: DeepAlias

struct Gen<T>
    v: T

fn deep(a: i32, b: i32) -> Deep
    return Deep { t: make(a), u: make(b), n: 7 }

fn mid() -> Mid
    return Mid { d: deep(1, 2), x: make(3) }

fn eat(d: Deep) -> i32
    return d.n

fn look(d: @Deep) -> i32
    return d.n

"""

# name -> (body defining `fn f(c: bool)`, argument, drop order).
NESTED_RUNS = {
    "single_move": ("""\
fn f(c: bool)
    var m = mid()
    consume(m.d.t)
""", "true", 123),
    "three_levels": ("""\
fn f(c: bool)
    var o = Top { m: mid() }
    consume(o.m.d.t)
""", "true", 123),
    "let_binding": ("""\
fn f(c: bool)
    let m = mid()
    consume(m.d.t)
""", "true", 123),
    "by_value_param": ("""\
fn g(m: Mid)
    consume(m.d.t)

fn f(c: bool)
    g(mid())
""", "true", 123),
    "grouped": ("""\
fn f(c: bool)
    var m = mid()
    consume((m.d).t)
""", "true", 123),
    "through_alias": ("""\
fn f(c: bool)
    var a = Aliased { d: deep(1, 2) }
    consume(a.d.t)
""", "true", 12),
    "through_generic": ("""\
fn f(c: bool)
    var g = Gen<Deep> { v: deep(1, 2) }
    consume(g.v.t)
""", "true", 12),
    "every_leaf_moved": ("""\
fn f(c: bool)
    var m = mid()
    consume(m.d.u)
    consume(m.x)
    consume(m.d.t)
""", "true", 231),
    "copy_sibling_still_readable": ("""\
fn f(c: bool)
    var m = mid()
    consume(m.d.t)
    ORDER = ORDER * 10 + m.d.n
""", "true", 1723),
    "into_binding": ("""\
fn f(c: bool)
    var m = mid()
    var u = m.d.t
""", "true", 123),
    "into_struct_literal": ("""\
fn f(c: bool)
    var m = mid()
    var h = Holder { t: m.d.t, n: 0 }
""", "true", 123),
    "returned": ("""\
fn g() -> Tracked
    var m = mid()
    return m.d.t

fn f(c: bool)
    consume(g())
""", "true", 231),
    "moved_on_taken_path": ("""\
fn f(c: bool)
    var m = mid()
    if c
        consume(m.d.t)
    ORDER = ORDER * 10 + 9
""", "true", 1923),
    "not_moved_on_untaken_path": ("""\
fn f(c: bool)
    var m = mid()
    if c
        consume(m.d.t)
    ORDER = ORDER * 10 + 9
""", "false", 9123),
    # Parent or child, depending on the path: both flags are in play.
    "parent_or_child_parent": ("""\
fn f(c: bool)
    var m = mid()
    if c
        eat(m.d)
    else
        consume(m.d.t)
    ORDER = ORDER * 10 + 9
""", "true", 1293),
    "parent_or_child_child": ("""\
fn f(c: bool)
    var m = mid()
    if c
        eat(m.d)
    else
        consume(m.d.t)
    ORDER = ORDER * 10 + 9
""", "false", 1923),
    # Assigning what was moved out re-owns it and drops nothing.
    "leaf_assigned_back": ("""\
fn f(c: bool)
    var m = mid()
    consume(m.d.t)
    m.d.t = make(4)
""", "true", 1423),
    "live_leaf_assigned": ("""\
fn f(c: bool)
    var m = mid()
    m.d.t = make(4)
""", "true", 1423),
    # The parent's assignment drops what's left of the old value.
    "parent_assigned_after_child": ("""\
fn f(c: bool)
    var m = mid()
    consume(m.d.t)
    m.d = deep(4, 5)
""", "true", 12453),
    "parent_assigned_child_maybe_moved": ("""\
fn f(c: bool)
    var m = mid()
    if c
        consume(m.d.t)
    m.d = deep(4, 5)
""", "false", 12453),
    # The new value's fields are live again: the second move is valid.
    "moved_again_after_parent_assigned": ("""\
fn f(c: bool)
    var m = mid()
    consume(m.d.t)
    m.d = deep(4, 5)
    consume(m.d.t)
""", "true", 12453),
    "binding_assigned_after_child": ("""\
fn f(c: bool)
    var m = mid()
    consume(m.d.t)
    m = Mid { d: deep(4, 5), x: make(6) }
""", "true", 123456),
    "moved_each_iteration": ("""\
fn f(c: bool)
    var m = mid()
    var i = 0
    while i < 2
        consume(m.d.t)
        m.d.t = make(4)
        i = i + 1
""", "true", 14423),
    # A lent nested field stays where it is.
    "lent_not_moved": ("""\
fn f(c: bool)
    var m = mid()
    peek(m.d.t)
    peek(m.d.t)
    look(m.d)
""", "true", 123),
    # As for `make().t`: no partial drops of a temporary.
    "temporary_nested_field": ("""\
fn f(c: bool)
    var u = mid().d.t
""", "true", 1),
}

# name -> (body defining `fn f()`, the moved path the error names).
NESTED_REJECTED = {
    "moved_twice": ("""\
fn f()
    var m = mid()
    consume(m.d.t)
    consume(m.d.t)
""", "m.d.t"),
    "three_levels_twice": ("""\
fn f()
    var o = Top { m: mid() }
    consume(o.m.d.t)
    consume(o.m.d.t)
""", "o.m.d.t"),
    "grouped_twice": ("""\
fn f()
    var m = mid()
    consume((m.d).t)
    consume(m.d.t)
""", "m.d.t"),
    "alias_twice": ("""\
fn f()
    var a = Aliased { d: deep(1, 2) }
    consume(a.d.t)
    consume(a.d.t)
""", "a.d.t"),
    "read_after_move": ("""\
fn f()
    var m = mid()
    consume(m.d.t)
    ORDER = m.d.t.id
""", "m.d.t"),
    "lent_after_move": ("""\
fn f()
    var m = mid()
    consume(m.d.t)
    peek(m.d.t)
""", "m.d.t"),
    "parent_moved_after_child": ("""\
fn f()
    var m = mid()
    consume(m.d.t)
    eat(m.d)
""", "m.d.t"),
    "parent_lent_after_child": ("""\
fn f()
    var m = mid()
    consume(m.d.t)
    look(m.d)
""", "m.d.t"),
    "binding_moved_after_child": ("""\
fn g(m: Mid)
    consume(m.x)

fn f()
    var m = mid()
    consume(m.d.t)
    g(m)
""", "m.d.t"),
    "child_after_parent": ("""\
fn f()
    var m = mid()
    eat(m.d)
    consume(m.d.t)
""", "m.d"),
    "maybe_moved": ("""\
fn f(c: bool)
    var m = mid()
    if c
        consume(m.d.t)
    consume(m.d.t)
""", "m.d.t"),
    "moved_in_loop": ("""\
fn f()
    var m = mid()
    var i = 0
    while i < 2
        consume(m.d.t)
        i = i + 1
""", "m.d.t"),
    # Both moved, on different paths: the leaf can't come back without m.d.
    "assign_leaf_of_maybe_moved_parent": ("""\
fn f(c: bool)
    var m = mid()
    if c
        eat(m.d)
    else
        consume(m.d.t)
    m.d.t = make(4)
""", "m.d"),
    "assign_leaf_of_moved_parent": ("""\
fn f()
    var m = mid()
    eat(m.d)
    m.d.t = make(4)
""", "m.d"),
}

# Moving out of a type with its own `drop`, at any level of the path.
NESTED_DROP_PARENT = {
    "middle": ("""\
struct Shell
    o: Owner

fn f(s: Shell)
    consume(s.o.t)
""", "s.o.t", "Owner"),
    "root": ("""\
struct Sealed
    h: Holder

impl Drop for Sealed
    fn drop(self: @&Sealed)
        DROPS = DROPS + 1

fn f(s: Sealed)
    consume(s.h.t)
""", "s.h.t", "Sealed"),
}


@pytest.mark.parametrize("name", sorted(NESTED_RUNS))
def test_ritz0_nested_field_drops(tmp_path, name):
    body, arg, order = NESTED_RUNS[name]
    rc = _run(tmp_path, NESTED + body + f"""
pub fn main() -> i32
    f({arg})
    return ORDER
""")
    # An exit status keeps the low byte, which is enough to tell orders apart.
    assert rc == order % 256, f"{name}: exit {rc}, drop order {order} is {order % 256}"


@pytest.mark.parametrize("name", sorted(NESTED_REJECTED))
def test_ritz0_nested_field_use_after_move_rejected(tmp_path, name):
    body, path = NESTED_REJECTED[name]
    comp, _ = _compile(tmp_path, NESTED + body + "\npub fn main() -> i32\n    return 0\n")
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"accepted a use after move:\n{out[-1000:]}"
    assert "Traceback" not in out, out[-2000:]
    assert f"use of moved value: `{path}`" in out, out[-2000:]


@pytest.mark.parametrize("name", sorted(NESTED_DROP_PARENT))
def test_ritz0_nested_move_out_of_drop_type_rejected(tmp_path, name):
    body, path, owner = NESTED_DROP_PARENT[name]
    comp, _ = _compile(tmp_path, NESTED + body + "\npub fn main() -> i32\n    return 0\n")
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"accepted a move out of a Drop type:\n{out[-1000:]}"
    assert "Traceback" not in out, out[-2000:]
    assert f"cannot move out of `{path}`: `{owner}` implements Drop" in out, out[-2000:]


# A match on a nested field owns what it moved, as on a direct one (AGAST #2177).
NESTED_MATCH = """\
enum Slot
    Full(Tracked)
    Empty

struct Bag
    s: Slot
    k: Tracked

struct Sack
    b: Bag

"""


def test_ritz0_nested_match_payload_binding_owns_it(tmp_path):
    rc = _run(tmp_path, NESTED_MATCH + """
fn f()
    var o = Sack { b: Bag { s: Slot.Full(make(1)), k: make(2) } }
    match o.b.s
        Full(t) => consume(t)
        Empty => 0

pub fn main() -> i32
    f()
    return ORDER
""")
    assert rc == 12


def test_ritz0_nested_match_unbound_payload_drops_with_scrutinee(tmp_path):
    rc = _run(tmp_path, NESTED_MATCH + """
fn f()
    var o = Sack { b: Bag { s: Slot.Full(make(1)), k: make(2) } }
    match o.b.s
        Full(_) => ORDER = 5
        Empty => ORDER = 6

pub fn main() -> i32
    f()
    return ORDER
""")
    assert rc == 512 % 256


def test_ritz0_nested_match_moves_the_scrutinee(tmp_path):
    comp, _ = _compile(tmp_path, NESTED_MATCH + """
fn f()
    var o = Sack { b: Bag { s: Slot.Full(make(1)), k: make(2) } }
    match o.b.s
        Full(_) => ORDER = 5
        Empty => ORDER = 6
    match o.b.s
        Full(_) => ORDER = 5
        Empty => ORDER = 6

pub fn main() -> i32
    return 0
""")
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"matched a moved field:\n{out[-1000:]}"
    assert "use of moved value: `o.b.s`" in out, out[-2000:]


@pytest.mark.parametrize("name", sorted(RUNS))
def test_ritz0_drops(tmp_path, name):
    body, expected = RUNS[name]
    rc = _run(tmp_path, body)
    assert rc == expected, f"{name}: exit {rc}, spec says {expected}"


@pytest.mark.parametrize("name", sorted(REJECTS))
def test_ritz0_use_after_move_rejected(tmp_path, name):
    body, var = REJECTS[name]
    comp, _ = _compile(tmp_path, body)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"accepted a use after move:\n{out[-1000:]}"
    assert "Traceback" not in out, out[-2000:]
    assert f"use of moved value: `{var}`" in out, out[-2000:]
