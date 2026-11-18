"""Trait bounds: `<T: A + B>` on a fn, struct, enum or impl (LANGUAGE_SPEC
§11.5, LARB R55, AGAST #3468).

A bound is a check only: it doesn't change method lookup (methods on `T` are
found after substitution, §11.4).  Two rules, each located:

  * An unknown trait is an error at the bound, whether or not the generic is
    used: check_unknown_bound_traits, run with the type-name check.
  * When the generic is instantiated, each type argument needs an impl of
    each trait, exact (`impl Area for Sq`) or through a generic impl
    (`impl<T> Drop for Box<T>` covers every `Box<..>`, §12.2), else an error
    at the type argument (at the call when inferred): bound_error.  Run by
    monomorph, which is where every instance, inferred or transitive, is
    known.  ritz1's half is #3469.
"""

from typing import Dict, Iterator, List, Optional, Tuple

import ritz_ast as rast
from monomorph_core import GenericInferError, resolve_alias

# Traits the compiler knows without a `trait` declaration (§7.8, §13.6).
COMPILER_TRAITS = frozenset(("Drop", "Deref", "DerefMut", "Index", "IndexMut", "IndexSet"))


class TraitBoundError(GenericInferError):
    """A type argument without an impl its parameter's bound requires.
    The message carries `file:line:column`."""


def unsatisfied(arg_name: str, trait: str, param: str, generic: str) -> str:
    return f"`{arg_name}` doesn't implement `{trait}`, which `{param}` of `{generic}` requires"


def unknown_trait(trait: str, param: str) -> str:
    return f"unknown trait `{trait}` in the bound on `{param}`"


def _bounded(items) -> Iterator[Tuple[dict, rast.Node]]:
    """(type_param_bounds, owner) for every item that can carry bounds."""
    for item in items:
        if isinstance(item, (rast.FnDef, rast.StructDef, rast.EnumDef)):
            yield item.type_param_bounds or {}, item
        elif isinstance(item, rast.ImplBlock):
            yield item.type_param_bounds or {}, item
            for method in item.methods:
                yield method.type_param_bounds or {}, method


def check_unknown_bound_traits(module: rast.Module) -> List[str]:
    """One located error per bound naming no trait the module declares (an
    import counts) or the compiler knows."""
    known = set(COMPILER_TRAITS)
    known.update(item.name for item in module.items if isinstance(item, rast.TraitDef))
    errors = []
    for bounds, owner in _bounded(module.items):
        for param, traits in bounds.items():
            for trait in traits:
                if trait in known:
                    continue
                span = getattr(trait, "span", None) or owner.span
                errors.append(f"{span}: {unknown_trait(trait, param)}")
    return errors


class TraitImpls:
    """Which types implement which traits: exactly (`impl Area for Sq`, by
    type name) or through a generic impl (`impl<T> Drop for Box<T>`, by the
    generic type's name, with the impl's own bounds)."""

    def __init__(self, items):
        self.exact: Dict[str, set] = {}
        self.generic: Dict[Tuple[str, str], rast.ImplBlock] = {}
        for item in items:
            if isinstance(item, rast.ImplBlock) and item.trait_name:
                if item.type_params:
                    self.generic[(item.type_name, item.trait_name)] = item
                else:
                    self.exact.setdefault(item.type_name, set()).add(item.trait_name)

    def implements(self, ty: rast.Type, trait: str) -> bool:
        ty = resolve_alias(ty)
        if not isinstance(ty, rast.NamedType):
            return False  # a pointer, array or tuple has no impls (§12.2)
        if not ty.args:
            return trait in self.exact.get(ty.name, ())
        impl = self.generic.get((ty.name, trait))
        if impl is None:
            return False
        # An impl covers every instantiation (§12.2): `impl<T> G<T>`, each
        # arg one of its params, so the impl's own bounds are on ty's args.
        return self.unmet(impl.type_params, ty.args, impl.type_param_bounds or {}) is None

    def unmet(self, params: List[str], args: List[rast.Type],
              bounds: dict) -> Optional[Tuple[int, str, str]]:
        """The first (arg index, param, trait) whose bound `args` misses."""
        for i, (param, arg) in enumerate(zip(params, args)):
            for trait in bounds.get(param, ()):
                if not self.implements(arg, trait):
                    return i, param, str(trait)
        return None


def type_name(ty: rast.Type) -> str:
    """`ty` as written: `Box<i64>`, `@Sq`, `[4]u8`."""
    if isinstance(ty, rast.NamedType):
        if ty.args:
            return f"{ty.name}<{', '.join(type_name(a) for a in ty.args)}>"
        return ty.name
    if isinstance(ty, rast.RefType):
        return ("@&" if ty.mutable else "@") + type_name(ty.inner)
    if isinstance(ty, rast.PtrType):
        return "*" + type_name(ty.inner)
    if isinstance(ty, rast.ArrayType):
        return f"[{ty.size}]{type_name(ty.inner)}"
    return str(ty)


def bound_error(impls: TraitImpls, generic: str, params: List[str], args: List[rast.Type],
                bounds: dict, written: Optional[List[rast.Type]]) -> Optional[TraitBoundError]:
    """The error for the first unmet bound, at the type argument as written
    (`written`, the instance's first use; an inferred one's span is its
    call's), else None."""
    if not bounds:
        return None
    miss = impls.unmet(params, args, bounds)
    if miss is None:
        return None
    i, param, trait = miss
    where = None
    if written is not None and i < len(written):
        where = getattr(written[i], "span", None)
    if where is None:
        where = getattr(args[i], "span", None)
    return TraitBoundError(unsatisfied(type_name(args[i]), trait, param, generic), where)
