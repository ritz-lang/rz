"""AGAST #2142: an enum ctor stored into a NON-enum slot is a ritz1 error.

ritz1 now gives a variant constructor its enum from the slot it is stored
into: an assignment target (`x = ..`, `s.f = ..`, `*p = ..`) or a
struct-literal field (`S { f: .. }`). The positive cases are the matrix test
ritz0/test/test_issue_enum_ctor_assign.ritz, run on all three compilers.

This file pins the other half, mirroring #1498's call-argument rule: when the
slot is not an enum, the ctor must NOT borrow the enclosing fn's Option
return type (that silently built an %Option$i64 and failed only at clang, or
not at all). It must be a located ritz1 error.
"""

import os
import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import RITZ1_BIN, RITZ_ROOT

# Each program sits in a fn returning Option<i64>, so the old return-type
# fallback had an enum to (wrongly) borrow.
ASSIGN_LOCAL = """\
fn h() -> Option<i64>
    var n: i64 = 0
    n = Some(1)
    Some(n)

pub fn main() -> i32
    0
"""

FIELD = """\
struct W
    n: i64

fn h() -> Option<i64>
    var w: W = W { n: 0 }
    w.n = None
    Some(w.n)

pub fn main() -> i32
    0
"""

STRUCT_LIT = """\
struct W
    n: i64

fn h() -> Option<i64>
    let w: W = W { n: Some(1) }
    Some(w.n)

pub fn main() -> i32
    0
"""

# The let's Option<W> context must not leak into W's i64 field.
STRUCT_LIT_LET_LEAK = """\
struct W
    n: i64

pub fn main() -> i32
    let o: Option<W> = Some(W { n: None })
    0
"""

# AGAST #2926: a variant's payload is a slot too.  `Has(W)` gives the inner
# ctor no enum, so it must not borrow the fn's Option<i64> return type.
VARIANT_PAYLOAD = """\
struct W
    n: i64

enum H
    Has(W)
    Lacks

fn h() -> Option<i64>
    let a: H = Has(Some(1))
    None

pub fn main() -> i32
    0
"""


@pytest.mark.integration
@pytest.mark.parametrize(
    "program",
    [ASSIGN_LOCAL, FIELD, STRUCT_LIT, STRUCT_LIT_LET_LEAK, VARIANT_PAYLOAD],
    ids=["assign_local", "field", "struct_lit", "struct_lit_let_leak", "variant_payload"],
)
def test_ritz1_ctor_into_non_enum_slot_is_an_error(ritz1_bin, tmp_path, program):
    src = tmp_path / "slot.ritz"
    src.write_text(program)
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(tmp_path / "slot.ll")],
        cwd=tmp_path,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode != 0, "ritz1 accepted a ctor stored into a non-enum slot"
    assert "enum context" in comp.stderr, comp.stderr[-2000:]
