"""Does a `match` cover its scrutinee? (LARB R6, AGAST #2344; LANGUAGE_SPEC §8.1)

Covered means an unguarded `_` or binding; every variant of an enum; `true` and
`false`; or every member of a union. An integer needs a catch-all. A guarded arm
never counts. Both parsers refuse guards today (#1939), but the rule must not
start counting them the day they parse.

Each function answers with what is missing, in declaration order, and an empty
list means covered. The caller knows the scrutinee's type: the emitter asks only
once it has the value, because a bare `Red` is a variant or a binding depending
on that type, and no reading of the arms alone can tell which. ritz1's twin is
match_gap in ritz1/src/emitter_match.ritz; test_match_exhaustive.py holds both to
one table.
"""

from typing import Callable, Collection, List, Sequence

import ritz_ast as rast

CATCH_ALL = "a catch-all"


def _counted(arms: Sequence[rast.MatchArm]) -> List[rast.Pattern]:
    return [arm.pattern for arm in arms if arm.guard is None]


def _takes_any_value(pattern: rast.Pattern) -> bool:
    return isinstance(pattern, (rast.WildcardPattern, rast.IdentPattern))


def _is_catch_all(pattern: rast.Pattern, constants: Collection[str]) -> bool:
    """A name that is a `const` compares (§8.2), so it takes only that value."""
    if isinstance(pattern, rast.IdentPattern):
        return pattern.name not in constants
    return isinstance(pattern, rast.WildcardPattern)


def enum_gap(arms: Sequence[rast.MatchArm], variants: Sequence[str]) -> List[str]:
    """The variants no arm covers. A name that is no variant here is a binding."""
    covered = set()
    for pattern in _counted(arms):
        if isinstance(pattern, rast.WildcardPattern):
            return []
        if isinstance(pattern, rast.IdentPattern):
            if pattern.name not in variants:
                return []
            covered.add(pattern.name)
        # `Some(0)` covers one value of `Some`, so it does not cover `Some`.
        elif isinstance(pattern, rast.VariantPattern) and all(
            _takes_any_value(field) for field in pattern.fields
        ):
            covered.add(pattern.name)
    return [name for name in variants if name not in covered]


def bool_gap(arms: Sequence[rast.MatchArm], constants: Collection[str]) -> List[str]:
    """`true` and `false`, unless an arm has them. `1` and `0` are not them."""
    covered = set()
    for pattern in _counted(arms):
        if _is_catch_all(pattern, constants):
            return []
        if isinstance(pattern, rast.LitPattern) and isinstance(pattern.value, bool):
            covered.add(pattern.value)
    return [
        name
        for name, value in (("true", True), ("false", False))
        if value not in covered
    ]


def scalar_gap(arms: Sequence[rast.MatchArm], constants: Collection[str]) -> List[str]:
    """An integer needs a catch-all."""
    if any(_is_catch_all(pattern, constants) for pattern in _counted(arms)):
        return []
    return [CATCH_ALL]


def union_gap(
    arms: Sequence[rast.MatchArm],
    members: Sequence[rast.Type],
    same_type: Callable[[rast.Type, rast.Type], bool],
    show: Callable[[rast.Type], str],
) -> List[str]:
    """The union members no arm names."""
    patterns = _counted(arms)
    if any(_takes_any_value(pattern) for pattern in patterns):
        return []
    named = [
        pattern.type for pattern in patterns if isinstance(pattern, rast.TypePattern)
    ]
    return [
        show(member)
        for member in members
        if not any(same_type(member, ty) for ty in named)
    ]
