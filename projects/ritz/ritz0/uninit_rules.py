"""Definite initialisation of a binding with drop glue (LANGUAGE_SPEC §13.6,
AGAST #4033, #4096; Aaron's decision of 2026-11-19, option (a)).

`var x: S` with no initialiser owns nothing yet.  Each part of S with drop glue
starts *unwritten*: S's fields, followed down through every struct
with no `drop` of its own, to the first part that has drop glue and can't be
split (a type with its own `drop`, an enum, an array, a tuple, a `Vec`: the
parts ritz1's ownership.ritz numbers, own_build_paths).  When S itself
can't be split, the whole binding starts unwritten.

The move checker keeps an unwritten part exactly as it keeps a part moved out
(VarInfo.moved_fields, or the binding's MOVED state), with the declaration's
span as the "where", so that writing it (`x.f = v`, or `x = v`) gives it back
and the emitter's per-field drop flags skip it until then.  Two things differ
from a move, and they are what this module words:

- using `x` whole (moving, returning, lending or reading it), or a part that
  is unwritten, is an error located at the use (`unwritten_use`);
- `x` going out of scope (the end of its block, a `return`, a `break` or
  `continue` that leaves it) with a part with drop glue unwritten is an error
  (`unwritten_drop`).  A binding that starts unwritten whole owns nothing
  until it is assigned, so it has nothing to drop.

Each binding is reported once: its first unwritten use, or else its first
drop.

ritz1's ownership.ritz prints the same words.
"""

from typing import List, Optional

import ritz_ast as rast

SECTION = "§13.6"


def unwritten_use(place: str, name: str) -> str:
    """`place` (`x`, or `x.f.g`) is used before every path wrote it."""
    return f"`{place}` may be unwritten: `{name}` has no initialiser ({SECTION})"


def unwritten_drop(place: str, name: str) -> str:
    """`name` leaves scope with `place` unwritten on some path."""
    return (f"`{place}` may be unwritten when `{name}` is dropped: "
            f"`{name}` has no initialiser ({SECTION})")


def unwritten_parts(types, ty: Optional[rast.Type], prefix: str = "") -> List[str]:
    """The dotted paths below a binding of type `ty` that start unwritten:
    [""] when the binding as a whole does, [] when `ty` has no drop glue.
    `types` is the checker's MoveTypes."""
    ty = types.resolve(ty)
    if ty is None or not types.is_move_only(ty):
        return []
    if not (isinstance(ty, rast.NamedType) and ty.name in types.structs
            and not types.has_own_drop(ty)):
        return [prefix]
    out: List[str] = []
    for n, t in types.struct_fields(ty):
        out += unwritten_parts(types, t, f"{prefix}.{n}" if prefix else n)
    return out
