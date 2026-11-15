"""`module.item` is refused, located, on every compiler (AGAST #2215).

LANGUAGE_SPEC §15.3: "There is no `module::item` or `module.item` access
form. Imported names land in a single flat namespace."  `::` was refused by
#2591; the `.` form was still half-accepted, and which half depended on the
item kind:

    import m
    struct P
        c: m.S          # ritz0: an i8 field, then "Cannot access field on
                        #   non-struct type: i8" at the use, unlocated
    m.K                 # compiled (a flat lookup of K), on ritz0 and ritz1
    m.mk()              # "Unknown identifier: m", unlocated
    match x
        m.K => ...      # compared against K (#2409's rewrite)

Each is now a located error: a type at the type (the declaration), an
expression at the use.  The message names the bare spelling to write.

Controls: the bare names compile; a bare imported const in a match arm
compares rather than binding (the second arm stays reachable: angelo's
interpreter relies on it); `Enum.Variant` and a local's `.field` are
unaffected.
"""

import os
import re
import subprocess

import pytest

from test_ref_into_value import COMPILERS, RITZ1_BUILD, RITZ_ROOT, _link, _located
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

MODULE = """\
pub struct S
    x: i32

pub const K: u8 = 7
pub const J: u8 = 8

pub fn mk() -> i32
    3
"""


def message(q, name):
    return (f"`{q}.{name}`: there is no `module.item` access (LANGUAGE_SPEC §15.3). "
            f"Imported names share one namespace, so write `{name}`")


# name -> (qualified spelling, program).  `^` marks where the error belongs.
REFUSED = {
    # The ticket's program: the field's type, at the declaration.
    "field_type": ("m.S", """\
import m

struct P
    c: ^m.S

pub fn main() -> i32
    var p: P
    p.c.x
"""),
    "param_type": ("m.S", """\
import m

fn f(s: @^m.S) -> i32
    s.x

pub fn main() -> i32
    0
"""),
    # harland's `"..." as serial.StrView`: a cast's target.
    "cast_type": ("m.S", """\
import m

pub fn main() -> i32
    let p: *u8 = null
    let q = p as *^m.S
    0
"""),
    "const_expr": ("m.K", """\
import m

pub fn main() -> i32
    ^m.K as i32
"""),
    "fn_call": ("m.mk", """\
import m

pub fn main() -> i32
    ^m.mk()
"""),
    # angelo's `instructions.NPUSHB =>`.
    "match_arm": ("m.K", """\
import m

fn f(x: u8) -> i32
    match x
        ^m.K => 1
        _ => 2

pub fn main() -> i32
    f(7)
"""),
}

ACCEPTED = {
    # (No imported fn is called: a single-file compile doesn't link m's bodies.)
    "bare_names": (7, """\
import m

struct P
    c: S

pub fn main() -> i32
    var p = P { c: S { x: K as i32 } }
    p.c.x
"""),
    # A bare const arm compares: were `K` a fresh binding it would catch 8
    # too, and f(8) would be 1, not 2.
    "bare_const_arm_compares": (213, """\
import m

fn f(x: u8) -> i32
    match x
        K => 1
        J => 2
        _ => 3

pub fn main() -> i32
    f(8) * 100 + f(7) * 10 + f(0)
"""),
    "enum_variant_and_local_field": (12, """\
import m

enum E
    A
    B

struct Q
    K: i32

fn g(e: E) -> i32
    match e
        E.A => 1
        E.B => 2

pub fn main() -> i32
    var m = Q { K: 10 }
    m.K + g(E.B)
"""),
}


def _compile(compiler, tmp_path, name, src):
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    (work / "m.ritz").write_text(MODULE)
    path = work / "main.ritz"
    path.write_text(src)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(path), "-o", str(ll)], cwd=work, env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        comp = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=work, env=env,
                              capture_output=True, text=True, timeout=300)
    return comp, ll, work


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(REFUSED))
def test_qualified_access_refused(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    spelled, marked = REFUSED[row]
    src, where = _located(marked)
    comp, ll, _ = _compile(compiler, tmp_path, row, src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {row}:\n{src}"
    assert not ll.exists()
    q, name = spelled.split(".")
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert (where, message(q, name)) in found, f"{compiler}: {row}, wanted {where}:\n{src}\n{out[-2000:]}"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(ACCEPTED))
def test_bare_names_accepted(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    want, src = ACCEPTED[row]
    comp, ll, work = _compile(compiler, tmp_path, row, src)
    assert comp.returncode == 0 and ll.exists(), \
        f"{compiler} refused {row}:\n{src}\n{(comp.stdout + comp.stderr)[-2000:]}"
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, f"{compiler}: {row} would not link:\n{link.stderr[-2000:]}"
    assert subprocess.run([str(exe)], capture_output=True, timeout=60).returncode == want
