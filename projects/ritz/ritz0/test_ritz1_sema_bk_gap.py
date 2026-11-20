"""AGAST #3768: sema_bool_kind types the shapes it left unsure (#3502 follow-up).

THE GAP

bool_check judges on Sema with sema_bool_kind (#3502).  Where it couldn't type
an expression it said BK_UNSURE, while the emitter's bool_kind, read off
get_expr_type, was sure: RITZ1_SEMA_PROBE counted 154 such `bk-gap`s over
ritz0/test.  At a gap a condition reads "ritz1 cannot tell that it is" bool:
an integer gets a vaguer report, and a real `bool` of that shape is refused.

THE CHANGE

sema_bool_kind (ritz1/src/bool_check.ritz) now types, from Sema's scope:

- `K[i]` of a `const K: [N]T` (a scalar T);
- `p[i]` / `*p` of `let p = f()` with `f() -> *T`, whose pointee the return
  names ("i32", #1984), and `*f()` / `*x.m()` of a `-> *T` / `-> @T` (so
  `m[k]`, which is `*m.index(k)` through `impl Index`);
- `(*p).arr[i]`, an array field through what sbk_receiver names;
- `*(*pp + k)` of a `**T`: its T;
- `*@a[i]`: what `a[i]` is;
- nameless tuples: `let t = (a, b)`, `t.1`, `let (x, y) = t`, nested ones,
  a struct element's fields, `let (g, h) = n.0`, and an `if` / `match` whose arms are tuples (its
  first arm's, each tuple literal judged in its own scope: an arm's own `let w`
  is out of scope at the `let (c, d)`).

The probe's ceiling (BK_GAP_CEILING, test_ritz1_sema_type.py) drops to what's
left: a field through a generic Deref (#3810's receiver typing), an index
through a Vec / Span / StrView field or payload (#3510's), and places the
emitter is the unsure side.  The IR is unchanged: bool_check only reports.

THE TESTS

One program of integer conditions, one per shape, each wanting "must be bool,
got an integer", not "cannot tell"; and one of `bool`s in the same shapes
(`KS[i]` too since #3949, when ritz1's emitter learnt to index a
`const [N]bool`), which must compile.  Both failed before the change, row by row.
"""

import os
import re
import subprocess

import pytest

from test_ref_into_value import RITZ1_BUILD, RITZ_ROOT, _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

# The shapes over `T`; the integer program sets T = i32 and V = 7, the bool
# one bool and false.
DECLS = """\
const KS: [2]T = [V, V]
var g_t: [3]T

struct Q
    arr: [2]T

struct P
    x: T

struct M
    v: T

impl Index for M
    pub fn index(self: @M, key: i64) -> @T
        @self.v

fn pt() -> *T
    return @g_t[0]

fn main() -> i32
    var pp: **T = null
    var q: Q = Q { arr: [V, V] }
    let pq: *Q = @q
    let p = pt()
    let m: M = M { v: V }
    let t = (V, 1)
    let (x, y) = t
    let n = ((V, 2), P { x: V })
    let (inner, s) = n
    let (a, b) = inner
    let (g, h) = n.0
    let (c, d) = if a == a
        let w: T = V
        (w, 1)
    else
        (V, 2)
"""

# One `if` per shape.  Both programs have every one: `KS[1]` of a `const [N]bool`
# was the integer program's only until #3949.
CONDITIONS = [
    "KS[1]",            # a const array's element
    "p[1]",             # `let p = pt()`, pt() -> *T
    "*p",
    "*pt()",            # a `-> *T` call
    "m[0]",             # `*m.index(0)`, a `-> @T` method
    "(*pq).arr[1]",     # an array field through `*pq`
    "*(*pp + 1)",       # a `**T`'s T
    "*@g_t[1]",         # what `g_t[1]` is
    "t.0",              # `let t = (V, 1)`
    "x",                # `let (x, y) = t`
    "a",                # nested: `let (a, b) = inner`, inner of `let (inner, s) = n`
    "s.x",              # a struct element's field
    "g",                # `let (g, h) = n.0`, an element that is a tuple
    "c",                # an `if` of tuples: its first arm's, whose `w` is its own
]


def _program(ty, value, conds):
    """The program and the line of each condition in it."""
    lines = DECLS.splitlines()
    at = {}
    for i, cond in enumerate(conds, 1):
        lines.append(f"    if {cond}")
        at[cond] = len(lines)
        lines.append(f"        return {i}")
    lines.append("    0")
    src = "\n".join(lines) + "\n"
    return src.replace("T", ty).replace("V", value), at


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_integer_of_each_shape_is_reported_as_one(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    src, at = _program("i32", "7", CONDITIONS)
    comp, ll, _ = _compile(compiler, tmp_path, "bk_gap_int", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = {int(line): msg for line, msg in re.findall(r"main\.ritz:(\d+):\d+: error: (.*)", out)}
    for cond, line in at.items():
        # Not "ritz1 cannot tell that it is": Sema knows it is an integer.
        assert found.get(line, "").startswith("if condition must be bool, got an integer"), \
            f"{compiler}: `if {cond}` (line {line}): {found.get(line)!r}\n{out}"
    assert set(found) == set(at.values()), f"{compiler}:\n{out}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_bool_of_each_shape_is_a_condition(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    src, _ = _program("bool", "false", CONDITIONS)
    comp, ll, _ = _compile(compiler, tmp_path, "bk_gap_bool", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused it:\n{out}"


# AGAST #3948: the emitter's bk_receiver read the struct through `*p`, `a[i]`
# and a field, but not through the `@` / `@&` it derefs: `(*(@o.s)).x` and
# `(*(@v[0])).x` were BK_UNSURE while Sema typed them, so a bool field of that
# shape was refused.  The probe pins the two sides together; zero bk-gaps here
# means the emitter now sees through the address too.
ADDR_FIELD = """\
import ritzlib.gvec

struct S
    a: i32
    x: bool

struct Outer
    pad: i64
    s: S

fn main() -> i32
    var o: Outer = Outer { pad: 0, s: S { a: 1, x: true } }
    var arr: [2]S = [S { a: 0, x: true }, S { a: 0, x: false }]
    var v = vec_new<S>()
    v.push(S { a: 0, x: true })
    v.push(S { a: 0, x: false })
    if (*(@o.s)).x
        if (*(@&o.s)).x
            if (*(@arr[0])).x
                if (*(@&arr[1])).x
                    if (*(@v[0])).x
                        return 0
    1
"""

BKGAP = re.compile(r"sema-probe: \d+ compared, \d+ mismatched, \d+ lenient, "
                   r"\d+ unknown, \d+ bool-gap, (\d+) bk-gap")


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_field_through_an_address_has_no_bool_kind_gap(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    work = tmp_path / f"bk_gap_addr_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(ADDR_FIELD)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT), RITZ1_SEMA_PROBE="1",
               RITZ_CACHE_DIR=str(work / "cache"))
    comp = subprocess.run([str(binary), str(src), "-o", str(work / "main.ll")],
                          cwd=work, env=env, capture_output=True, text=True, timeout=120)
    out = comp.stdout + comp.stderr
    assert "sema-probe: mismatch" not in out, f"{compiler} disagrees:\n{out}"
    gap = BKGAP.search(out)
    assert gap, f"{compiler} printed no probe summary:\n{out}"
    assert int(gap.group(1)) == 0, f"{compiler}: {gap.group(1)} bool-kind gaps\n{out}"
    assert comp.returncode == 0 and (work / "main.ll").exists(), \
        f"{compiler} refused a bool field through an address:\n{out}"
