"""The typing pass: one walk that types a module's expressions (LARB review/5
ritz0 N1, AGAST #3448).

ritz0 used to type expressions in four places: the type checker, the move
checker, monomorph and the emitter, each re-deriving the same rules.  This
pass is the one place a rule belongs.  `type_module` walks a module with the
type checker's inference and leaves a `Typed` side table, keyed by node, on
`module.typed`; the passes after it read the table instead of inferring.

It runs on every compile (ritz0._type), before the ownership pass, and again
on the monomorphised module the emitter emits (emitter_llvmlite.emit), so an
instance of a generic body is typed at its concrete `T`.  The type errors it
finds are kept on the table: `--check-types` decides whether ritz0 prints
them (on by default is #3556, #1823), and the slot errors (§13.2, §13.4) are printed
beside an ownership error, or refuse an instance, either way.

Who reads it so far: the type checker (it is the inference), and the move
checker, for MOVE_CHECKER_READS.  The move checker's own rules for the other
kinds (#3553), monomorph's inferers (#3554) and the emitter's (#3555) are
still to move here.
"""

from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

import ritz_ast as rast

# The kinds the move checker takes from the table (move_checker.EXPR_TYPES).
# Each answers as its old rule did, or `void` / a variant's enum where that
# rule said `unknown`; over the matrix corpus and ritz1 no answer changes
# whether a value is move-only.  The kinds the rules still disagree on
# (Ident, UnaryOp, BinOp, Field, Index, Match, TryOp, MethodCall, the
# aggregate literals) stay the move checker's for now (#3553).
MOVE_CHECKER_READS = (
    rast.IntLit, rast.FloatLit, rast.BoolLit, rast.CharLit,
    rast.StringLit, rast.CStringLit,
    rast.Cast, rast.StructLit, rast.Call,
)


class Typed:
    """Each expression's type, as the typing pass inferred it.

    Keyed by node identity, not equality: two `0` literals are equal
    dataclasses but two entries.  The table holds each node, so an id can't
    be reused by another node while the table lives.
    """

    def __init__(self) -> None:
        self._types: Dict[int, Tuple[rast.Expr, rast.Type]] = {}
        # Every type error the walk found, in order; `.slot` marks the slot
        # errors (TypeChecker._slot_error).
        self.errors: List = []

    def record(self, expr: rast.Expr, ty: rast.Type) -> None:
        """`expr`'s type is `ty`.  An expression typed twice (a literal's
        parts, a re-read of a place) keeps the last answer."""
        self._types[id(expr)] = (expr, ty)

    def type_of(self, expr: rast.Expr) -> Optional[rast.Type]:
        """`expr`'s type, or None if the pass never typed `expr`."""
        entry = self._types.get(id(expr))
        if entry is None or entry[0] is not expr:
            return None
        return entry[1]

    def __len__(self) -> int:
        return len(self._types)

    @property
    def slot_errors(self) -> List:
        """The errors the slot rules found (§13.2, §13.4), reported on every
        compile, unlike the rest."""
        return [e for e in self.errors if e.slot]


def type_module(module: rast.Module, module_names: Optional[Set[str]] = None,
                emits_body: Optional[Callable[[rast.FnDef], bool]] = None) -> Typed:
    """Type `module`: every body, or those `emits_body` picks.  Sets and
    returns `module.typed`."""
    from type_checker import TypeChecker
    table = Typed()
    checker = TypeChecker(module_names, typed=table)
    table.errors = checker.check(module, emits_body)
    module.typed = table
    return table


def type_bodies(module: rast.Module,
                bodies: Sequence[Tuple[rast.FnDef, Optional[rast.ImplBlock]]],
                module_names: Optional[Set[str]] = None) -> Typed:
    """Type only `bodies`, fns that are not `module`'s items (the move
    checker's copies of generic instances), against `module`'s
    declarations.  `module.typed` is left alone."""
    from type_checker import TypeChecker
    table = Typed()
    checker = TypeChecker(module_names, typed=table)
    table.errors = checker.check_bodies(module, bodies)
    return table


def typed_of(module: rast.Module) -> Typed:
    """`module.typed`, typing `module` first if no pass has."""
    table = getattr(module, 'typed', None)
    return table if table is not None else type_module(module)
