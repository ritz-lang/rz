"""AGAST #1302: a `name:& T` parameter stored in a reference field.

    fn mk(c:& C) -> R
        var r: R
        r.ch = c

A `:&` parameter reads as its referent, so this emitted a load of the whole `C`
and then tried to store it into the field's `C*` slot:

    cannot assign to field `ch`: cannot store %C to %C**: mismatching types

which is how tempest's lib/tab_renderer.ritz:48 died. The struct literal
`R { ch: c }` failed the same way through insert_value, and a `p: *i32` field
fed from `n:& i32` compiled, turning the integer into a pointer.

A reference field now takes the borrow's own pointer. The move checker agrees:
that is a reborrow, not a move out of the parameter, so a Drop type can be
stored this way. Storing into a by-value field is still a read of the referent.

The ticket's other error was a tempest source bug: lib/document.ritz dereferenced
`vec_get`'s result, which is a `T` now. `./rz build tempest` still fails on other
tickets (#2221, #1858, #2222), so that file is compiled on its own here.

Every program returns 3 on success, and writes through the stored reference
after it was stored, so a pointer to a temporary copy can't pass.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

TYPES = """\
struct C
    x: i32
    y: i64

struct R
    n: i32
    ch:& C

struct P
    ch: *C

struct A
    ch: @&C
"""

MAIN_R = """\
pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var r: R = mk(@c)
    r.ch.x = r.ch.x + 2
    return c.x
"""

STORES = {
    "assign": TYPES + """
fn mk(c:& C) -> R
    var r: R
    r.ch = c
    return r
""" + MAIN_R,
    "assign_ptr_field": TYPES + """
fn mk(c:& C) -> P
    var p: P
    p.ch = c
    return p

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var p: P = mk(@c)
    p.ch.x = p.ch.x + 2
    return c.x
""",
    "assign_at_amp_field": TYPES + """
fn mk(c:& C) -> A
    var a: A
    a.ch = c
    return a

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var a: A = mk(@c)
    a.ch.x = a.ch.x + 2
    return c.x
""",
    "assign_through_pointer": TYPES + """
fn fill(r: *R, c:& C)
    r.ch = c

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var r: R
    fill(@r, @c)
    r.ch.x = r.ch.x + 2
    return c.x
""",
    "literal": TYPES + """
fn mk(c:& C) -> R
    return R { n: 1, ch: c }
""" + MAIN_R,
    "literal_ptr_field": TYPES + """
fn mk(c:& C) -> P
    return P { ch: c }

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var p: P = mk(@c)
    p.ch.x = p.ch.x + 2
    return c.x
""",
    # A generic struct's field type comes from its arguments.
    "literal_generic_struct": """\
struct C
    x: i32

struct G<T>
    p: *T

fn mk(c:& C) -> G<C>
    return G<C> { p: c }

pub fn main() -> i32
    var c: C = C { x: 1 }
    var g: G<C> = mk(@c)
    g.p.x = g.p.x + 2
    return c.x
""",
    # The referent is an integer: without the borrow's pointer, its value
    # converts to a pointer and the write below faults.
    "assign_primitive": """\
struct Q
    p: *i32

fn mk(n:& i32) -> Q
    var q: Q
    q.p = n
    return q

pub fn main() -> i32
    var n: i32 = 1
    var q: Q = mk(@n)
    *q.p = 3
    return n
""",
    "literal_primitive": """\
struct Q
    p: *i32

fn mk(n:& i32) -> Q
    return Q { p: n }

pub fn main() -> i32
    var n: i32 = 1
    var q: Q = mk(@n)
    *q.p = 3
    return n
""",
}

# A large literal is built in place, on a path of its own (#1741). ritz0 only:
# clang lowers ritz1's copy of it to a `memset` call, and -nostdlib has none.
LARGE_LITERAL = """\
struct C
    x: i32

struct L
    ch:& C
    pad: [8192]u8

fn fill(l: *L, c:& C)
    *l = L { ch: c, pad: [0; 8192] }

pub fn main() -> i32
    var c: C = C { x: 1 }
    var l: L
    fill(@l, @c)
    l.ch.x = l.ch.x + 2
    return c.x
"""

# The destination decides, so these must not take the borrow's pointer.
CONTROLS = {
    # `c` reads as a `*C`: that pointer is what the field holds, not the
    # address of the caller's pointer variable.
    "referent_is_a_pointer": TYPES + """
fn mk(c:& *C) -> P
    var p: P
    p.ch = c
    return p

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var q: *C = @c
    var p: P = mk(@q)
    p.ch.x = p.ch.x + 2
    return c.x
""",
    # A by-value field copies: the write lands in the copy.
    "by_value_field_copies": TYPES + """
struct V
    c: C

fn mk(c:& C) -> V
    var v: V
    v.c = c
    return v

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var v: V = mk(@c)
    v.c.x = 9
    return c.x
""",
    "by_value_literal_copies": TYPES + """
struct V
    c: C

fn mk(c:& C) -> V
    return V { c: c }

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var v: V = mk(@c)
    v.c.x = 9
    return c.x
""",
    # A later `let` of the same name is what the field gets.
    "shadowed_param": TYPES + """
fn mk(c:& C, other: *C) -> P
    let c: *C = other
    var p: P
    p.ch = c
    return p

pub fn main() -> i32
    var a: C = C { x: 9, y: 0 }
    var b: C = C { x: 1, y: 0 }
    var p: P = mk(@a, @b)
    p.ch.x = p.ch.x + 2
    return b.x
""",
}

RES = """\
struct Res
    h: i32

impl Drop for Res
    fn drop(self: @&Res)
        self.h = 0

struct H
    r:& Res

struct V
    r: Res
"""

# Storing a reference to a Drop type lends it on: nothing moves or drops.
DROP_STORES = {
    "assign": RES + """
fn mk(t:& Res) -> H
    var h: H
    h.r = t
    return h

pub fn main() -> i32
    var r: Res = Res { h: 1 }
    var h: H = mk(@r)
    h.r.h = 3
    return r.h
""",
    "literal": RES + """
fn mk(t:& Res) -> H
    return H { r: t }

pub fn main() -> i32
    var r: Res = Res { h: 1 }
    var h: H = mk(@r)
    h.r.h = 3
    return r.h
""",
}

# A by-value field of the same type really would take it from the caller.
MOVE_OUT = {
    "assign": RES + """
fn mk(t:& Res) -> V
    var v: V
    v.r = t
    return v

pub fn main() -> i32
    return 0
""",
    "literal": RES + """
fn mk(t:& Res) -> V
    return V { r: t }

pub fn main() -> i32
    return 0
""",
}


# ritz1 gets the ticket's case right; these are its own, separate defects.
RITZ1_GAPS = {
    "assign_primitive": "AGAST #2250: ritz1 stores the referent in a `*T` field",
    "literal_primitive": "AGAST #2250: ritz1 stores the referent in a `*T` field",
    "by_value_field_copies": "AGAST #2250: ritz1 stores the borrow in a `T` field",
    "by_value_literal_copies": "AGAST #2250: ritz1 stores the borrow in a `T` field",
}


def _compile(compiler, ritz1_bin, tmp_path: Path, name: str, program: str):
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(program)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=work, env=env, timeout=300)
    else:
        comp = subprocess.run([str(ritz1_bin), str(src), "-o", str(ll)], cwd=work,
                              env=env, capture_output=True, text=True, timeout=300)
    return comp, ll, work


def _run(compiler, ritz1_bin, tmp_path: Path, name: str, program: str) -> int:
    comp, ll, work = _compile(compiler, ritz1_bin, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed on {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
    exe = work / "main"
    cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        cmd.insert(2, str(RITZ_START))
    link = subprocess.run(cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, f"{name} would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(STORES))
def test_ritz0_ref_field_takes_the_borrow(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, STORES[name]) == 3


@pytest.mark.integration
def test_ritz0_large_literal_takes_the_borrow(tmp_path):
    assert _run("ritz0", None, tmp_path, "large", LARGE_LITERAL) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CONTROLS))
def test_ritz0_destination_decides(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, CONTROLS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(DROP_STORES))
def test_ritz0_drop_type_reborrow_is_not_a_move(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, DROP_STORES[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MOVE_OUT))
def test_ritz0_by_value_field_is_still_a_move_out(tmp_path, name):
    comp, _, _ = _compile("ritz0", None, tmp_path, name, MOVE_OUT[name])
    assert comp.returncode != 0
    assert "cannot move out of borrowed parameter `t`" in comp.stdout + comp.stderr


@pytest.mark.integration
def test_tempest_document_compiles(tmp_path):
    tempest = RITZ_ROOT.parent / "tempest"
    ll = tmp_path / "document.ll"
    env = dict(os.environ, RITZ_PATH=f"{tempest.parent}:{tempest}")
    comp = run_ritz0(["lib/document.ritz", "--no-runtime", "--project-root", ".",
                      "-o", str(ll)], cwd=tempest, env=env, timeout=300)
    assert comp.returncode == 0 and ll.exists(), comp.stdout[-2000:] + comp.stderr[-2000:]


def _ritz1_params(programs: dict) -> list:
    """Every program, with ritz1's known gaps as strict xfails."""
    return [pytest.param(name, marks=[pytest.mark.xfail(strict=True, reason=RITZ1_GAPS[name])]
                         if name in RITZ1_GAPS else [])
            for name in sorted(programs)]


@pytest.mark.integration
@pytest.mark.parametrize("name", _ritz1_params(STORES))
def test_ritz1_ref_field_takes_the_borrow(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, STORES[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", _ritz1_params(CONTROLS))
def test_ritz1_destination_decides(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, CONTROLS[name]) == 3
