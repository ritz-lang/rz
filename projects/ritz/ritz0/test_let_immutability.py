"""AGAST #2026: a `let` binding is immutable through its fields, its
elements and `@&`, not just as a whole.

THE DEFECT

ritz0 rejected only `b = v` on a `let`. It accepted `b.f = v`, `b[i] = v`
and `@&b`. A small `let` is an SSA value, so those wrote a throwaway temp
copy and the write vanished. Since #2025 a large-struct `let` lives in one
slot, so the same writes stuck and mutated an immutable binding.

THE RULE

A write (`=`, `+=`, ...) or a mutable borrow (`@&`) whose place is the
`let`'s own storage is a compile error: the binding itself, a by-value
field of it, or an element of a by-value array in it, to any depth. A path
that goes through a pointer (`let p: *T`, a `*T` field, a slice) writes
the pointee, not the binding, and stays legal. So do `var`s, a `var` that
shadows a `let`, and shared borrows `@b`.
"""

import os
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent

PRELUDE = """\
struct Pt
    x: i64
    y: i64

struct Big
    data: [1000]u8
    n: i64
    pt: Pt

struct Holder
    p: *Pt
    buf: *u8

fn big_new() -> Big
    var b: Big
    b.n = 1
    return b

fn pt_x(p: *Pt) -> i64
    return p.x

fn big_n(b: *Big) -> i64
    return b.n

"""


def _compile(tmp_path: Path, body: str):
    src = tmp_path / "prog.ritz"
    src.write_text(PRELUDE + "fn main() -> i32\n" + body + "    0\n")
    ll = tmp_path / "prog.ll"
    r = run_ritz0([str(src), "-o", str(ll), "--no-runtime"], cwd=tmp_path,
                  env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)), timeout=300)
    return r, r.stdout + r.stderr


def _indent(lines: str) -> str:
    return "".join(f"    {ln}\n" for ln in lines.strip("\n").splitlines())


# (id, body, binding name, kind) -- each must be rejected.
REJECTED = [
    # Small `let` (an SSA value): the write used to vanish into a temp.
    ("small-field", "let p = Pt { x: 1, y: 2 }\np.x = 3", "p", "assign"),
    ("small-field-compound", "let p = Pt { x: 1, y: 2 }\np.x += 3", "p", "assign"),
    ("small-array-elem", "let a: [4]i64 = [1, 2, 3, 4]\na[0] = 9", "a", "assign"),
    # A match-arm assignment is an AssignExpr, not an AssignStmt.
    ("small-field-match-arm",
     "let p = Pt { x: 1, y: 2 }\nlet o: Option<i64> = Some(3)\n"
     "match o\n    Some(v) => p.x = v\n    None => p.y = 0", "p", "assign"),
    ("small-mut-borrow", "let p = Pt { x: 1, y: 2 }\nlet q: *Pt = @&p", "p", "borrow"),
    ("small-mut-borrow-field", "let p = Pt { x: 1, y: 2 }\nlet q: *i64 = @&p.x", "p", "borrow"),
    ("scalar-mut-borrow", "let k: i64 = 4\nlet q: *i64 = @&k", "k", "borrow"),
    # Large `let` (a #2025 slot): the write used to stick.
    ("large-field", "let b: Big = big_new()\nb.n = 3", "b", "assign"),
    ("large-nested-field", "let b: Big = big_new()\nb.pt.x = 3", "b", "assign"),
    ("large-array-field-elem", "let b: Big = big_new()\nb.data[7] = 3", "b", "assign"),
    ("large-mut-borrow", "let b: Big = big_new()\nlet q: *Big = @&b", "b", "borrow"),
    ("large-mut-borrow-elem", "let b: Big = big_new()\nlet q: *u8 = @&b.data[3]", "b", "borrow"),
]


@pytest.mark.integration
@pytest.mark.parametrize("body,name,kind",
                         [r[1:] for r in REJECTED], ids=[r[0] for r in REJECTED])
def test_mutating_a_let_is_rejected(tmp_path, body, name, kind):
    r, out = _compile(tmp_path, _indent(body))
    assert r.returncode != 0, f"mutating `let {name}` compiled:\n{body}"
    if kind == "assign":
        want = f"cannot assign through `let` binding `{name}`; declare it `var`"
    else:
        want = f"cannot borrow `let` binding `{name}` as mutable; declare it `var`"
    assert want in out, out[-2000:]
    assert "Traceback" not in out, out[-3000:]


# Each must compile: the write or `@&` is not to a `let`'s own storage.
ACCEPTED = [
    ("var-field", "var p = Pt { x: 1, y: 2 }\np.x = 3\np.x += 1"),
    ("var-field-match-arm",
     "var p = Pt { x: 1, y: 2 }\nlet o: Option<i64> = Some(3)\n"
     "match o\n    Some(v) => p.x = v\n    None => p.y = 0"),
    ("var-array-elem", "var a: [4]i64 = [1, 2, 3, 4]\na[0] = 9"),
    ("var-mut-borrow", "var p = Pt { x: 1, y: 2 }\nlet q: *Pt = @&p\nq.x = 5"),
    ("var-large", "var b: Big = big_new()\nb.n = 3\nb.data[1] = 2\nlet q: *Big = @&b"),
    # Through a pointer held in a `let`: the pointee is written.
    ("let-ptr-field", "var v = Pt { x: 1, y: 2 }\nlet p: *Pt = @&v\np.x = 3"),
    ("let-ptr-index", "var a: [4]i64 = [1, 2, 3, 4]\nlet p: *i64 = @&a[0]\np[1] = 7"),
    ("let-ptr-field-borrow", "var v = Pt { x: 1, y: 2 }\nlet p: *Pt = @&v\nlet q: *i64 = @&p.x"),
    ("let-struct-ptr-field",
     "var v = Pt { x: 1, y: 2 }\nvar c: u8 = 0\n"
     "let h = Holder { p: @&v, buf: @&c }\nh.p.x = 3\nh.buf[0] = 4"),
    # Shared borrows of a `let` are fine.
    ("let-shared-borrow", "let p = Pt { x: 1, y: 2 }\nlet n = pt_x(@p)"),
    ("large-let-shared-borrow", "let b: Big = big_new()\nlet n = big_n(@b)"),
    # A `var` that shadows a `let` is mutable.
    ("var-shadows-let", "let p = Pt { x: 1, y: 2 }\nvar p = Pt { x: 3, y: 4 }\np.x = 5\nlet q: *Pt = @&p"),
    ("var-shadows-large-let", "let b: Big = big_new()\nvar b: Big = big_new()\nb.n = 5\nlet q: *Big = @&b"),
]


@pytest.mark.integration
@pytest.mark.parametrize("body", [a[1] for a in ACCEPTED], ids=[a[0] for a in ACCEPTED])
def test_non_let_mutation_is_accepted(tmp_path, body):
    r, out = _compile(tmp_path, _indent(body))
    assert r.returncode == 0, f"rejected:\n{body}\n{out[-2000:]}"


# AGAST #2031: whole-binding `x = v` / `x op= v` on any `let`. A small `let`
# is an SSA value in self.params, so before #2031 it fell through to an
# uncaught `ValueError: Unknown variable: x` traceback; only a #2025
# large-struct slot got the `let` diagnostic, and that one had no span.
WHOLE_REJECTED = [
    ("whole-scalar", "let k: i64 = 4\nk = 5", "k"),
    ("whole-scalar-inferred", "let k = 4\nk = 5", "k"),
    ("whole-scalar-compound", "let k: i64 = 4\nk += 1", "k"),
    ("whole-scalar-in-loop", "let k: i64 = 4\nvar i = 0\nwhile i < 3\n    k = i\n    i += 1", "k"),
    ("whole-small-struct", "let p = Pt { x: 1, y: 2 }\np = Pt { x: 3, y: 4 }", "p"),
    ("whole-large-struct", "let b: Big = big_new()\nb = big_new()", "b"),
    # A `let` that shadows a `var` is immutable from there on.
    ("whole-let-shadows-var", "var k: i64 = 1\nlet k: i64 = 2\nk = 3", "k"),
    # A match-arm assignment is an AssignExpr, not an AssignStmt.
    ("whole-scalar-match-arm",
     "let k: i64 = 4\nlet o: Option<i64> = Some(3)\n"
     "match o\n    Some(v) => k = v\n    None => k = 0", "k"),
    ("whole-large-match-arm",
     "let b: Big = big_new()\nlet o: Option<i64> = Some(3)\n"
     "match o\n    Some(v) => b = big_new()\n    None => b = big_new()", "b"),
]


@pytest.mark.integration
@pytest.mark.parametrize("body,name", [r[1:] for r in WHOLE_REJECTED],
                         ids=[r[0] for r in WHOLE_REJECTED])
def test_assigning_a_let_is_rejected(tmp_path, body, name):
    r, out = _compile(tmp_path, _indent(body))
    assert r.returncode != 0, f"assigning `let {name}` compiled:\n{body}"
    assert f"cannot assign to `let` binding `{name}`; declare it `var`" in out, out[-2000:]
    assert "Traceback" not in out, out[-3000:]
    assert "Unknown variable" not in out, out[-2000:]
    # Located at the assignment, not just named (prelude + `fn main` line).
    assert "prog.ritz:" in out, out[-2000:]


WHOLE_ACCEPTED = [
    ("whole-var-scalar", "var k: i64 = 4\nk = 5\nk += 1"),
    ("whole-var-shadows-let", "let k: i64 = 4\nvar k: i64 = 5\nk = 6\nk += 1"),
    ("whole-var-shadows-large-let", "let b: Big = big_new()\nvar b: Big = big_new()\nb = big_new()"),
    ("whole-var-match-arm",
     "var k: i64 = 4\nlet o: Option<i64> = Some(3)\n"
     "match o\n    Some(v) => k = v\n    None => k = 0"),
]


@pytest.mark.integration
@pytest.mark.parametrize("body", [a[1] for a in WHOLE_ACCEPTED],
                         ids=[a[0] for a in WHOLE_ACCEPTED])
def test_assigning_a_var_is_accepted(tmp_path, body):
    r, out = _compile(tmp_path, _indent(body))
    assert r.returncode == 0, f"rejected:\n{body}\n{out[-2000:]}"


# AGAST #2029: an *implicit* mutable borrow -- a `self:&` / `self: @&T`
# method receiver, or call-site autoborrow into a `name:& T` / `name: @&T`
# parameter -- is the same `@&` as #2026's explicit one, and was accepted.
# A small `let` was spilled to a temp so the mutation vanished; a #2025
# large `let` slot was passed in place, so it stuck.
IMPLICIT_PRELUDE = """\
impl Pt
    fn bump(self:& Pt)
        self.x = self.x + 1
    fn bump_ref(self: @&Pt)
        self.x = self.x + 1
    fn peek(self: @Pt) -> i64
        return self.x
    fn get(self: Pt) -> i64
        return self.x
    fn absorb(self:& Pt, other:& Pt)
        self.x = self.x + other.x

impl Big
    fn bump(self:& Big)
        self.n = self.n + 1

fn set(p:& Pt)
    p.x = 9

fn set_ref(p: @&Pt)
    p.x = 9

fn pt_read(p: @Pt) -> i64
    return p.x

fn set_big(b:& Big)
    b.n = 9

fn set_i64(k:& i64)
    k = 9

struct Wrap
    pt: Pt
    pp: *Pt

"""


def _compile_implicit(tmp_path: Path, body: str):
    src = tmp_path / "prog.ritz"
    src.write_text(PRELUDE + IMPLICIT_PRELUDE + "fn main() -> i32\n" + body + "    0\n")
    ll = tmp_path / "prog.ll"
    r = run_ritz0([str(src), "-o", str(ll), "--no-runtime"], cwd=tmp_path,
                  env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)), timeout=300)
    return r, r.stdout + r.stderr


IMPLICIT_REJECTED = [
    # Method receivers.
    ("recv-small", "let p = Pt { x: 1, y: 2 }\np.bump()", "p"),
    ("recv-small-ref", "let p = Pt { x: 1, y: 2 }\np.bump_ref()", "p"),
    ("recv-large", "let b: Big = big_new()\nb.bump()", "b"),
    ("recv-large-nested-field", "let b: Big = big_new()\nb.pt.bump()", "b"),
    ("recv-small-field", "let w = Wrap { pt: Pt { x: 1, y: 2 }, pp: null }\nw.pt.bump()", "w"),
    # A method's explicit `:&` argument.
    ("method-arg", "var p = Pt { x: 1, y: 2 }\nlet q = Pt { x: 3, y: 4 }\np.absorb(q)", "q"),
    # Free-function autoborrow.
    ("arg-small", "let q = Pt { x: 1, y: 2 }\nset(q)", "q"),
    ("arg-small-ref", "let q = Pt { x: 1, y: 2 }\nset_ref(q)", "q"),
    ("arg-large", "let b: Big = big_new()\nset_big(b)", "b"),
    ("arg-large-field", "let b: Big = big_new()\nset(b.pt)", "b"),
    ("arg-scalar", "let k: i64 = 4\nset_i64(k)", "k"),
]


@pytest.mark.integration
@pytest.mark.parametrize("body,name", [r[1:] for r in IMPLICIT_REJECTED],
                         ids=[r[0] for r in IMPLICIT_REJECTED])
def test_implicit_mut_borrow_of_let_is_rejected(tmp_path, body, name):
    r, out = _compile_implicit(tmp_path, _indent(body))
    assert r.returncode != 0, f"implicit mutable borrow of `let {name}` compiled:\n{body}"
    assert f"cannot borrow `let` binding `{name}` as mutable; declare it `var`" in out, out[-2000:]
    assert "Traceback" not in out, out[-3000:]
    assert "prog.ritz:" in out, out[-2000:]


# Each autoborrow call is the body's last use of its argument: the move
# checker still counts a `name:&` autoborrow as a move (separate defect).
IMPLICIT_ACCEPTED = [
    # Shared and by-value receivers/params of a `let`.
    ("recv-shared", "let p = Pt { x: 1, y: 2 }\nlet n = p.peek()"),
    ("recv-by-value", "let p = Pt { x: 1, y: 2 }\nlet n = p.get()"),
    ("arg-shared", "let p = Pt { x: 1, y: 2 }\nlet n = pt_read(p)"),
    # `var` receivers and arguments.
    ("recv-var", "var p = Pt { x: 1, y: 2 }\np.bump()\np.bump_ref()"),
    ("recv-var-large", "var b: Big = big_new()\nb.bump()\nb.pt.bump()"),
    ("arg-var", "var p = Pt { x: 1, y: 2 }\nset(p)"),
    ("arg-var-ref", "var p = Pt { x: 1, y: 2 }\nset_ref(p)"),
    ("arg-var-large", "var b: Big = big_new()\nset_big(b)"),
    ("arg-var-large-field", "var b: Big = big_new()\nset(b.pt)"),
    ("var-shadows-let", "let p = Pt { x: 1, y: 2 }\nvar p = Pt { x: 3, y: 4 }\np.bump()\nset(p)"),
    # A `let` holding a pointer: the pointee is borrowed, not the binding.
    ("let-ptr-recv", "var v = Pt { x: 1, y: 2 }\nlet p: *Pt = @&v\np.bump()\np.bump_ref()"),
    ("let-ptr-arg", "var v = Pt { x: 1, y: 2 }\nlet p: *Pt = @&v\nset(p)"),
    ("let-ptr-arg-ref", "var v = Pt { x: 1, y: 2 }\nlet p: *Pt = @&v\nset_ref(p)"),
    ("let-ref-arg", "var v = Pt { x: 1, y: 2 }\nlet p: @&Pt = @&v\np.bump()\nset(p)"),
    ("let-ptr-field-recv",
     "var v = Pt { x: 1, y: 2 }\nlet w = Wrap { pt: Pt { x: 0, y: 0 }, pp: @&v }\nw.pp.bump()\nset(w.pp)"),
    # Rvalues are spilled to a fresh temp.
    ("rvalue-recv", "Pt { x: 1, y: 2 }.bump()"),
]


@pytest.mark.integration
@pytest.mark.parametrize("body", [a[1] for a in IMPLICIT_ACCEPTED],
                         ids=[a[0] for a in IMPLICIT_ACCEPTED])
def test_implicit_non_let_mut_borrow_is_accepted(tmp_path, body):
    r, out = _compile_implicit(tmp_path, _indent(body))
    assert r.returncode == 0, f"rejected:\n{body}\n{out[-2000:]}"
