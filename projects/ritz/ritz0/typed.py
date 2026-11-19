"""The typing pass: one walk that types a module's expressions (LARB review/5
ritz0 N1, AGAST #3448).

ritz0 used to type expressions in four places: the type checker, the move
checker, monomorph and the emitter, each re-deriving the same rules.  This
pass is the one place a rule belongs.  `type_module` walks a module with the
type checker's inference and leaves a `Typed` side table, keyed by node, on
`module.typed`; the passes after it read the table instead of inferring.

It runs on every compile (ritz0._type), before the ownership pass, and again
on the monomorphised module the emitter emits (ritz0._check_instances), so an
instance of a generic body is typed at its concrete `T`.  The type errors it
finds are kept on the table, and ritz0._check_types prints them on every
compile (AGAST #3556), and the slot errors (§13.2, §13.4) are printed
beside an ownership error, or refuse an instance, either way.

Who reads it so far: the type checker (it is the inference), the move
checker, for every kind it types (MOVE_CHECKER_READS, #3553, #4065),
monomorph (#3554), and the emitter, for EMITTER_READS (#3555).  The
emitter's rules for the other kinds (#4066, #4067) are still to move here.
"""

from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

import ritz_ast as rast

# The kinds the move checker takes from the table (move_checker.EXPR_TYPES).
# Each answers as its old rule did, or better (`@x` is a reference, `&T`, not
# `*T`; `a < b` is a bool); over the matrix corpus, ritz1 and examples no IR
# changes.  Ident, Field, Match and MethodCall followed once the pass typed
# a generic's members at its instance (#3554, #4065): a payload binding, a
# match and a generic method are typed where the old rules said `unknown`, and
# the method-name heuristic (`len` is i64) is gone.  Index is deliberately not
# read (#2268).  ArrayFill `[v; n]` is `[n]V`, so a fill
# of a fill of a move-only value is move-only too: `[ [r; 1]; 2]` copies `r`
# (#3433).
MOVE_CHECKER_READS = (
    rast.IntLit, rast.FloatLit, rast.BoolLit, rast.CharLit,
    rast.StringLit, rast.CStringLit, rast.NullLit,
    rast.Cast, rast.StructLit, rast.Call,
    rast.UnaryOp, rast.BinOp, rast.TryOp, rast.ArrayLit, rast.ArrayFill,
    rast.TupleLit,
    rast.Ident, rast.Field, rast.Match, rast.MethodCall,
)

# The kinds the emitter takes from the table (LLVMEmitter._typed_type, #3555).
# Where its old rule said nothing (an `if` with no tail, a tuple with an
# untyped element) the table may say more; over the matrix corpus, ritz1, the
# examples and the .ritz tests the emitted IR is byte-identical.  A "..." in a
# `*u8` slot is a `*u8` here (LARB R3), and a match is its first arm with a
# known type, as the emitter's rules said when they were set as it emitted
# (as_ptr, result_ritz_type; #4068).  The
# kinds left (Ident, UnaryOp, BinOp, Call, Field, Index, MethodCall, ArrayLit)
# disagree, mostly in generic instances (#3554); they stay the emitter's
# (#4066, #4067).
EMITTER_READS = (
    rast.IntLit, rast.FloatLit, rast.BoolLit, rast.CharLit,
    rast.StringLit, rast.CStringLit, rast.NullLit,
    rast.Cast, rast.StructLit, rast.TupleLit,
    rast.If, rast.Block, rast.Match, rast.TryOp,
)


class Typed:
    """Each expression's type, as the typing pass inferred it.

    Keyed by node identity, not equality: two `0` literals are equal
    dataclasses but two entries.  The table holds each node, so an id can't
    be reused by another node while the table lives.

    And keyed by body: monomorph shares each subtree an instance leaves
    unchanged (monomorph.map_child_nodes), so `v` in a generic body is one
    node in every instance, typed once per instance.  `type_of(e, within=fn)`
    is `e`'s type in `fn`; without `within`, the last body's (#3553).
    """

    def __init__(self) -> None:
        self._types: Dict[int, Tuple[rast.Expr, rast.Type]] = {}
        # (id(body), id(expr)) -> (body, expr, type); body None outside one.
        self._in_body: Dict[Tuple[int, int], Tuple[object, rast.Expr, rast.Type]] = {}
        # The body `record` files under (`enter`).
        self._body: Optional[rast.FnDef] = None
        # Every type error the walk found, in order; `.slot` marks the slot
        # errors (TypeChecker._slot_error).
        self.errors: List = []

    def enter(self, body: Optional[rast.FnDef]) -> None:
        """Record what follows as `body`'s types (None: outside any body)."""
        self._body = body

    def record(self, expr: rast.Expr, ty: rast.Type,
               within: Optional[rast.FnDef] = None) -> None:
        """`expr`'s type is `ty`, in `within` (default: the body entered).
        An expression typed twice (a literal's parts, a re-read of a place)
        keeps the last answer."""
        body = within if within is not None else self._body
        self._types[id(expr)] = (expr, ty)
        self._in_body[(id(body), id(expr))] = (body, expr, ty)

    def type_of(self, expr: rast.Expr,
                within: Optional[rast.FnDef] = None) -> Optional[rast.Type]:
        """`expr`'s type (in body `within`, if given), or None if the pass
        never typed `expr` there."""
        if within is not None:
            entry = self._in_body.get((id(within), id(expr)))
            if entry is None or entry[0] is not within or entry[1] is not expr:
                return None
            return entry[2]
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
