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
  * a value lent to an `@T` parameter (auto-borrow) is not moved;
  * a type with its own `drop` runs it before its fields' drops.

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
