"""ritz0: an element store drops the old element; arrays of any rank drop;
a Drop array must be initialised (LARB R39, AGAST #3305, #3376).

LANGUAGE_SPEC §13.6: `a[i] = v`, `g[i][j] = v` and `h.a[i] = v` drop the
element's old value after `v` and the index are evaluated, before `v` is
stored, as a field store does. An array of any rank drops element by element
in index order. §3.3: so every element always holds a value, a local array
whose element type has drop glue must have an initialiser.

`S`'s drop appends its `x` to `D` as a decimal digit string (`D * 10 + x`),
so `D` spells out both which elements dropped and in what order. Each program
exits 42 when `D` is what the spec says, otherwise `D % 200` (never 42).

ritz1 does the same in #3377; until then these run on ritz0 only.
"""

import os
import subprocess
from pathlib import Path

import fast_link
import pytest
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent

PRELUDE = """\
var D: i64 = 0

struct S
    x: i64

impl Drop for S
    fn drop(self:& S)
        D = D * 10 + self.x

struct H
    a: [2]S
    n: i32

fn mk(x: i64) -> S
    D = D * 10 + 8
    return S { x: x }

fn idx(i: i64) -> i64
    D = D * 10 + 7
    return i

fn verdict(want: i64) -> i32
    if D == want
        return 42
    let r = (D % 200) as i32
    if r == 42
        return 43
    return r

"""

RUNS = {
    # #3305's repro: the old x=2 drops at the store, then 1 and 30 at the
    # end: digits 2, 1, then 30 added on (D * 10 + 30).
    "one_rank1_store": ("""\
fn one()
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    a[1] = S { x: 30 }
""", "one()", (2 * 10 + 1) * 10 + 30),
    # v (8), then the index (7), then the old element (2); 1 and 3 at the end.
    "store_order": ("""\
fn f()
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    a[idx(1)] = mk(3)
""", "f()", 87213),
    # Rank 2 at scope end: index order, g[0][0] .. g[1][1].
    "rank2_scope_end": ("""\
fn f()
    var g: [2][2]S = [ [S { x: 1 }, S { x: 2 }], [S { x: 3 }, S { x: 4 }] ]
""", "f()", 1234),
    # Rank 3 too.
    "rank3_scope_end": ("""\
fn f()
    var g: [2][1][2]S = [ [ [S { x: 1 }, S { x: 2 }] ], [ [S { x: 3 }, S { x: 4 }] ] ]
""", "f()", 1234),
    # g[1][0] = v drops the old g[1][0] (3) at the store.
    "rank2_store": ("""\
fn f()
    var g: [2][2]S = [ [S { x: 1 }, S { x: 2 }], [S { x: 3 }, S { x: 4 }] ]
    g[1][0] = S { x: 5 }
""", "f()", 31254),
    # A field's array: h.a[0] = v drops the old h.a[0] (1).
    "field_array_store": ("""\
fn f()
    var h: H = H { a: [S { x: 1 }, S { x: 2 }], n: 0 }
    h.a[0] = S { x: 5 }
""", "f()", 152),
    # A moved-out array owns nothing: storing into it drops nothing, and it
    # owns its elements again. The callee drops the moved one (1, 2).
    "store_into_moved_array_drops_nothing": ("""\
fn eat(a: [2]S)
    D = D * 10 + 9

fn f()
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    eat(a)
    a = [S { x: 3 }, S { x: 4 }]
    a[0] = S { x: 5 }
""", "f()", 9123 * 100 + 54),
    # Through a raw pointer, nothing owns the old element (as `p.f = v`,
    # AGAST #2179): only the local's own drops run.
    "store_through_pointer_drops_nothing": ("""\
fn put(p: *S)
    p[0] = S { x: 5 }

fn f()
    var a: [1]S = [S { x: 1 }]
    put(@a[0])
""", "f()", 5),
}


def _source(body, call, want):
    return (PRELUDE + body + "\npub fn main() -> i32\n    " + call
            + f"\n    return verdict({want})\n")


def _compile(tmp_path, src_text):
    src = tmp_path / "main.ritz"
    src.write_text(src_text)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    return comp, ll


@pytest.mark.parametrize("name", sorted(RUNS))
def test_ritz0_element_store_and_nd_drops(tmp_path, name):
    body, call, want = RUNS[name]
    comp, ll = _compile(tmp_path, _source(body, call, want))
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz0 failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
    exe = tmp_path / "main"
    link = fast_link.clang(["clang", str(ll), "-o", str(exe), "-nostdlib"],
                           cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-2000:]
    rc = subprocess.run([str(exe)], check=False, capture_output=True, timeout=60).returncode
    assert rc == 42, f"{name}: D % 200 == {rc}, spec says D == {want}"


# §3.3: a Drop array local needs an initialiser; the error is at the name.
UNINIT = {
    "rank1": "    var a: [2]S\n",
    "rank2": "    var a: [2][2]S\n",
    "field_holder": "    var a: [2]H\n",
}


@pytest.mark.parametrize("name", sorted(UNINIT))
def test_ritz0_uninitialised_drop_array_refused(tmp_path, name):
    body = "fn f()\n    let k = 1\n" + UNINIT[name]
    comp, _ = _compile(tmp_path, _source(body, "f()", 0))
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"accepted an uninitialised Drop array:\n{out[-1000:]}"
    assert "Traceback" not in out, out[-2000:]
    assert "main.ritz:" + str(PRELUDE.count("\n") + 3) + ":9: " in out, out[-2000:]
    assert "`a` must be initialised: its elements have `drop`" in out, out[-2000:]


def test_ritz0_uninitialised_copy_array_and_drop_struct_accepted(tmp_path):
    """Only an array of a drop-glue type needs one: a `[2]i32`, and a plain
    `var b: S` (the constructor idiom, 13 in the corpus), stay as they were."""
    body = "fn f()\n    var a: [2]i32\n    a[0] = 1\n    var b: S\n    b.x = 4\n"
    comp, ll = _compile(tmp_path, _source(body, "f()", 4))
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), out[-2000:]
