"""AGAST #2955: a struct with no fields must parse in ritz1, as it does in
ritz0, and lay out as `{}`.

THE DEFECT

    pub struct E

    impl E
        pub fn k() -> i32
            7

    pub fn main() -> i32
        E.k()

    error: c2.ritz:3:1: unexpected 'impl'
    note: c2.ritz:1:1: cannot parse item starting at 'pub struct E'

ritz1's `struct_def` required `NEWLINE INDENT struct_fields DEDENT`.  A
field-less struct has no block, so there is no INDENT, and the whole item
was dropped.  Prism uses one as a namespace for static builder methods
(prism/src/protocol/command.ritz:156).

THE FIX

`struct_def` gains `[PUB] STRUCT IDENT generic_params? NEWLINE` with no
fields, after the bodied forms (it is their prefix).  The emitter already
lays out a struct with a null field list as `{}`; the run tests below check
that, with ritz0 as the oracle, in each place a struct value travels: by
value as a param and a return, a Vec element, `sizeof`, and a generic
instance.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

RITZ_ROOT = Path(__file__).resolve().parent.parent

# The ticket's program, verbatim.
TICKET = """\
pub struct E

impl E
    pub fn k() -> i32
        7

pub fn main() -> i32
    E.k()
"""

# A field-less struct in every position a struct value travels.  The bodied
# `After` follows the field-less structs, so a field-less form that ate the
# next INDENT would break it.  7 + 2 + 0 + 30 + 5 + 1 = 45, the last being
# `v.len` after one push of a zero-size element (AGAST #2965).
SHAPES = """\
import ritzlib.gvec

pub struct E

struct Unit

struct Tag<T>

struct After
    x: i32

impl E
    pub fn k() -> i32
        7

fn take(u: Unit, n: i32) -> i32
    n + 1

fn make() -> Unit
    Unit {}

fn relay(u: Unit) -> Unit
    u

fn tagged(t: Tag<i32>) -> i32
    5

pub fn main() -> i32
    var v: Vec<Unit> = vec_new<Unit>()
    vec_push<Unit>(@&v, make())
    let u: Unit = relay(vec_get<Unit>(@v, 0))
    let a: After = After { x: 30 }
    return E.k() + take(u, 1) + sizeof(Unit) as i32 + a.x + tagged(Tag<i32> {}) + v.len as i32
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_ticket_program_runs(ritz1_bin, tmp_path, compiler):
    assert _run_pkg(compiler, tmp_path, "fieldless_ticket", TICKET) == 7


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_fieldless_struct_values_run(ritz1_bin, tmp_path, compiler):
    assert _run_pkg(compiler, tmp_path, "fieldless_shapes", SHAPES) == 45


@pytest.mark.integration
def test_ritz1_lays_out_fieldless_struct_as_empty(ritz1_bin, tmp_path):
    """ritz0 emits `type {}` for a field-less struct; ritz1 must too."""
    src = tmp_path / "layout.ritz"
    src.write_text("struct Unit\n\nfn relay(u: Unit) -> Unit\n    u\n\npub fn main() -> i32\n    0\n")
    out = tmp_path / "layout.ll"
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(out)],
        cwd=tmp_path,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0 and out.exists(), proc.stderr[-2000:]
    ir = out.read_text()
    assert re.search(r"^%Unit = type \{\s*\}$", ir, re.M), ir[:2000]
