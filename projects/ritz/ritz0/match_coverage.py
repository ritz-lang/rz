"""Does a `match` cover its scrutinee, and can every arm be reached? (LARB R6,
AGAST #2344; LARB R13, AGAST #2349; LANGUAGE_SPEC §8.1)

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

from typing import (Any, Callable, Collection, Hashable, List, Mapping, Optional,
                    Sequence, Tuple)

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


# --- Reachability (LARB R13, AGAST #2349) -----------------------------------
#
# Arms are tried top to bottom and the first that matches wins, so an arm no
# value can reach is an error at that arm, naming the arm that covers it. That
# is an unguarded arm earlier testing the same thing (literal, const value,
# variant, union member), or, once the arms so far leave no gap under R6, the
# arm that closed it: a catch-all, or the last new variant. A guarded arm
# covers nothing, but can itself be unreachable. ritz1's twin is
# match_check_reachable in ritz1/src/emitter_match.ritz.

# What a pattern tests, and whether it takes every value of that: `Some(v)` takes
# every `Some`, `Some(0)` only one. None for a catch-all, which `gap` judges.
Test = Optional[Tuple[Hashable, bool]]


def scalar_test(constants: Mapping[str, Any]) -> Callable[[rast.Pattern], Test]:
    """A literal, or a const by its value (§8.2), so `K` and `5` are one test
    when K is 5. `constants` maps a const's name to its value."""
    def test(pattern: rast.Pattern) -> Test:
        if isinstance(pattern, rast.IdentPattern) and pattern.name in constants:
            value = constants[pattern.name]
        elif isinstance(pattern, rast.LitPattern):
            value = pattern.value
        else:
            return None
        # `True == 1`, so a bool keeps its own kind.
        return (type(value) is bool, value), True
    return test


def enum_test(variants: Collection[str]) -> Callable[[rast.Pattern], Test]:
    """A variant by name, whatever its payload binds."""
    def test(pattern: rast.Pattern) -> Test:
        if isinstance(pattern, rast.IdentPattern) and pattern.name in variants:
            return pattern.name, True
        if isinstance(pattern, rast.VariantPattern):
            return pattern.name, all(_takes_any_value(field) for field in pattern.fields)
        return None
    return test


def union_test(show: Callable[[rast.Type], str]) -> Callable[[rast.Pattern], Test]:
    """A member by its spelling."""
    def test(pattern: rast.Pattern) -> Test:
        if isinstance(pattern, rast.TypePattern):
            return show(pattern.type), True
        return None
    return test


def unreachable_arm(
    arms: Sequence[rast.MatchArm],
    gap: Callable[[Sequence[rast.MatchArm]], List[str]],
    test: Callable[[rast.Pattern], Test],
) -> Optional[Tuple[rast.MatchArm, rast.MatchArm]]:
    """The first arm no value can reach, with the arm that covers it, or None.
    `gap` is the scrutinee's R6 check, asked of the arms so far."""
    covered = {}
    closer = None
    for index, arm in enumerate(arms):
        # An arm that repeats a test names the arm it repeats, even once all is
        # covered: `Some(v) / None / Some(_)` is a second `Some`, said at `Some(v)`.
        tested = test(arm.pattern)
        if tested is not None and tested[0] in covered:
            return arm, covered[tested[0]]
        if closer is not None:
            return arm, closer
        if arm.guard is None:
            if tested is not None and tested[1]:
                covered[tested[0]] = arm
            if not gap(arms[:index + 1]):
                closer = arm
    return None


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
