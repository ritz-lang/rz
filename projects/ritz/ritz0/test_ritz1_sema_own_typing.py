"""AGAST #4251: one typing for what the move check typed on its own (#1816).

THE CHANGE

#3507 moved ritz1's move check onto Sema (own_check.ritz).  It reads a value's
type from Sema: ref_check's image of the emitter's LocalVar (RsNote) and
sema_expr_ty.  Where neither typed a value as the emitter does, own_check
typed it itself: a user enum's unit variant `E.V` (oc_ctor_enum), a nameless
tuple literal and its fields (oc_tuple_def), `match *p` of a `p: *E` and its
payload (oc_payload_struct's enum branch), `match Some(make(1))`'s payload
(oc_tagged_ctor_payload) and `c?` of a static method call (oc_try_struct).

Sema types each of them now (sema_type.ritz): the move check reads one typing,
and those fallbacks are gone.

THE TESTS

- RITZ1_SEMA_PROBE=dump pins Sema's answer on each shape, and the probe finds
  no disagreement with the emitter there.  Red on the base: each was unknown.
- own_check.ritz defines none of the fallbacks.
- The move check says what it said: test_ritz1_sema_own.py's REACH rows (one
  more each for `E.V` and `T.f()?`), test_ownership_free_count.py and
  test_match_constructor_scrutinee.py; the corpus's IR is byte-identical.
- One verdict changes: `let x = p.0` of a nameless tuple is now a typed `let`,
  so `x.id = 4` is refused, as ritz0 refuses it.
"""

import re
from pathlib import Path

import pytest

from test_ref_into_value import _compile
from test_ritz1_sema_type import DUMP, SUMMARY, STRUCT, E_IDENT, E_MEMBER, E_UNARY

RITZ_ROOT = Path(__file__).resolve().parent.parent
OWN_CHECK = RITZ_ROOT / "ritz1" / "src" / "own_check.ritz"
COMPILERS = ["ritz1", "ritz1_selfhosted"]
E_STRUCT_LIT, E_TRY = 11, 19

SHAPES = """\
import ritzlib.gvec

struct Tracked
    id: i32

impl Drop for Tracked
    fn drop(self: @&Tracked)
        let z: i32 = self.id

impl Tracked
    fn try_new(i: i32) -> Result<Tracked, i32>
        Ok(Tracked { id: i })

struct H
    t: Tracked
    n: i32

enum Slot
    Full(Tracked)
    Empty

fn make(i: i32) -> Tracked
    Tracked { id: i }

fn eat(t: Tracked) -> i32
    t.id

fn unit_variant() -> i32
    var s = Slot.Empty
    0

fn through_pointer(p: *Slot) -> i32
    match *p
        Full(t) => return t.id
        Empty => return 0

fn static_try() -> Result<i32, i32>
    var t = Tracked.try_new(1)?
    Ok(eat(t))

fn tuple_lit() -> i32
    var p = (make(1), 2)
    var x = p.0
    eat(x)

fn tagged_ctor() -> i32
    match Some(make(1))
        Some(v) => eat(v)
        None => 0

fn vec_field(v: @Vec<H>) -> i32
    v[0].t.id

pub fn main() -> i32
    let a: i32 = unit_variant() + through_pointer(null) + tuple_lit() + tagged_ctor() + vec_field(null)
    match static_try()
        Ok(k) => k + a
        Err(e) => e
"""

# (line, col, expr kind, Sema's type kind, its name); "" for any name but none.
WANTED = [
    (29, 13, E_MEMBER, STRUCT, "Slot"),      # Slot.Empty, a unit variant
    (33, 11, E_UNARY, STRUCT, "Slot"),       # *p of p: *Slot
    (34, 27, E_IDENT, STRUCT, "Tracked"),    # t, Full's payload through *p
    (38, 13, E_TRY, STRUCT, "Tracked"),      # Tracked.try_new(1)?, a static call's Ok
    (39, 12, E_IDENT, STRUCT, "Tracked"),    # t, bound to it
    (42, 13, E_STRUCT_LIT, STRUCT, ""),      # (make(1), 2), a nameless tuple
    (43, 13, E_IDENT, STRUCT, ""),           # p, bound to it
    (43, 13, E_MEMBER, STRUCT, "Tracked"),   # p.0
    (44, 9, E_IDENT, STRUCT, "Tracked"),     # x = p.0
    (48, 24, E_IDENT, STRUCT, "Tracked"),    # v, Some's payload of Some(make(1))
    (52, 5, E_MEMBER, STRUCT, "Tracked"),    # v[0].t through a Vec (already, #3973)
]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_sema_types_what_the_move_check_typed_itself(request, tmp_path, compiler, monkeypatch):
    request.getfixturevalue("ritz1_bin")
    monkeypatch.setenv("RITZ1_SEMA_PROBE", "dump")
    comp, ll, _ = _compile(compiler, tmp_path, "own_shapes", SHAPES)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused it:\n{out}"
    seen = {}
    for line, col, kind, ty, name in DUMP.findall(out):
        seen.setdefault((int(line), int(col), int(kind)), set()).add((int(ty), name))
    bad = []
    for line, col, kind, ty, name in WANTED:
        got = seen.get((line, col, kind), set())
        if not any(t == ty and (n == name if name else n != "") for t, n in got):
            bad.append(f"{(line, col, kind)} wanted {ty} {name or '<named>'}, got {sorted(got)}")
    assert not bad, f"{compiler}:\n" + "\n".join(bad)
    summary = SUMMARY.search(out)
    assert summary and summary.group(2) == "0", f"{compiler}: the probe disagrees:\n{out}"


FALLBACKS = ["oc_struct_of", "oc_tuple_def", "oc_tuple_named", "oc_ctor_enum",
             "oc_try_struct", "oc_tagged_ctor_payload"]


@pytest.mark.unit
def test_the_move_check_types_nothing_itself():
    own = OWN_CHECK.read_text()
    left = [f for f in FALLBACKS if re.search(rf"^fn {f}\b", own, re.M)]
    assert not left, f"own_check.ritz still types values itself: {left}"


LET_TUPLE_FIELD = """\
struct Tracked
    id: i32

fn make(i: i32) -> Tracked
    Tracked { id: i }

fn lets() -> i32
    let p = (make(1), 2)
    let x = p.0
    x.id = 4
    x.id

pub fn main() -> i32
    lets()
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_let_bound_to_a_tuple_field_is_a_let(request, tmp_path, compiler):
    # Sema now types `p.0` (Tracked), so let_check sees `x` is a `let` of a
    # struct, and refuses a write through it as ritz0 does.  It went
    # unchecked while `x` was untyped.
    request.getfixturevalue("ritz1_bin")
    comp, _, _ = _compile(compiler, tmp_path, "let_tuple_field", LET_TUPLE_FIELD)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted it:\n{out}"
    assert "main.ritz:10:5: error: cannot assign through `let` binding `x`; declare it `var`" in out, out
