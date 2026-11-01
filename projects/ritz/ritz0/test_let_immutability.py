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
