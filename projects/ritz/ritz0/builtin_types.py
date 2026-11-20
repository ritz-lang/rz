"""The compiler's built-in types are closed to `impl` (AGAST #3162).

`Span<T>`, `StrView`, `Option<T>` and `Result<T, E>` exist with no
declaration: the emitter synthesizes them (`_ensure_strview_type`,
`_ensure_builtin_generic_struct_specialization`,
`_ensure_builtin_generic_specialization`) and lowers their methods itself
(`_try_emit_builtin_span_method`, ...).  An `impl` on one of them, inherent
or trait, at any instantiation, was lost: its methods were never called, or
were "No method found".  Aaron's decision (2026-11-15, rz-larb), the stance
R15 took on built-in indexing: it is an error, located at the `impl`.

A struct or enum of that name the program declares or imports (ritzlib's
`struct Span<T>`, `pub struct StrView`, `enum Option<T>`, `enum Result<T, E>`)
is an ordinary type, and its impls are unaffected.  ritz1 applies the same
rule (main.ritz, refuse_impls_on_builtin_types).
"""

from pathlib import Path

import ritz_ast as rast
from metadata import type_to_string
from name_resolver import NameResolver
from trait_bounds import COMPILER_TRAITS

# Built-in type -> the ritzlib module that declares it as an ordinary type.
BUILTIN_TYPES = {
    "Span": "ritzlib.span",
    "StrView": "ritzlib.strview",
    "Option": "ritzlib.option",
    "Result": "ritzlib.result",
}


# The scalars: built-in types closed to `impl`, inherent or trait (LARB R36,
# AGAST #3370; spec §12.2).  R36's revisit (Aaron, 2026-11-20, AGAST #4294)
# admits a *trait* impl on one — `impl Display for i64` — but only in the file
# that declares the trait.  SIMD vectors aren't in R36.
PRIMITIVES = frozenset({
    'i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64', 'f32', 'f64', 'bool',
})

# The built-ins R36's revisit admits as trait-impl targets, in the trait's
# file: `Span<T>` (a concrete instantiation, `impl Display for Span<u8>`) and
# `StrView`.  Option and Result are not in the ruling.  A file that imports
# ritzlib.span / ritzlib.strview declares the type outright, and its impls are
# ordinary (R65).
BUILTIN_IMPL_TARGETS = frozenset({'Span', 'StrView'})

# A pointer target: the parser spells `impl Trait for *u8` as `ptr_u8` (the
# symbol `*u8_show` isn't valid LLVM IR).  R36's revisit admits only `*u8`.
POINTER_TARGETS = frozenset({'ptr_u8'})


def target_spelling(type_name: str) -> str:
    """The source spelling of an impl target: `ptr_u8` is `*u8`."""
    return "*" + type_name[4:] if type_name.startswith("ptr_") else type_name


def is_builtin_target(type_name: str) -> bool:
    """A target no file declares (a primitive, a built-in or a pointer)."""
    return (type_name in PRIMITIVES or type_name in BUILTIN_IMPL_TARGETS
            or type_name in POINTER_TARGETS)


def in_trait_file(impl: rast.ImplBlock, traits: dict) -> bool:
    """Is `impl` a trait impl in the file that declares its trait?

    R36's revisit admits impls on primitives/built-ins only there; a trait
    the compiler knows (Drop, Index…) declares no file, so it never is."""
    if impl.trait_name is None:
        return False
    trait = traits.get(impl.trait_name)
    impl_file = getattr(impl, 'source_file', None)
    trait_file = getattr(trait, 'source_file', None) if trait is not None else None
    return (impl_file is not None and trait_file is not None
            and str(Path(impl_file).resolve()) == str(Path(trait_file).resolve()))


def refusal(type_name: str) -> str:
    return (f"`{type_name}` is a built-in type and can't be extended here: "
            f"import {BUILTIN_TYPES[type_name]} or declare your own type")


def misplaced_target(type_name: str) -> str:
    """A built-in impl target outside the trait's file (R36's revisit)."""
    return (f"`{target_spelling(type_name)}` is a built-in type: a trait impl "
            f"for it must be in the trait's file (§12.2)")


def check_builtin_impls(module: rast.Module) -> list[str]:
    """One located error per `impl` whose target is a built-in type.

    Runs on the merged module, after import resolution, so an imported
    declaration counts as the program's own.  A trait impl on `Span<T>` or
    `StrView` in the trait's file is R36's revisit and stands; one outside it
    is the placement error, not the import hint."""
    declared = {item.name for item in module.items
                if isinstance(item, (rast.StructDef, rast.EnumDef))}
    traits = {item.name: item for item in module.items
              if isinstance(item, rast.TraitDef)}
    errors = []
    for item in module.items:
        if (not isinstance(item, rast.ImplBlock)
                or item.type_name not in BUILTIN_TYPES
                or item.type_name in declared):
            continue
        if item.type_name in BUILTIN_IMPL_TARGETS and item.trait_name is not None:
            if not in_trait_file(item, traits):
                errors.append(f"{item.type_span}: {misplaced_target(item.type_name)}")
            continue
        errors.append(f"{item.span}: {refusal(item.type_name)}")
    return errors


def check_unknown_impl_targets(module: rast.Module) -> list[str]:
    """One located error per `impl` on a type nothing declares (AGAST #3264).

    `impl Foo` with no `struct Foo` / `enum Foo` in scope compiled, and its
    methods were unreachable; so did `impl Vec<u8>` without ritzlib.vec.
    Located at the impl's type name.  Known: a struct or enum of the merged
    module (an import counts), a name the resolver has built in
    (a primitive, a SIMD vector, a built-in type: an impl on one of the last
    is check_builtin_impls's error), or one of the impl's own type
    parameters.  Only parsed impls carry `type_span`; one loaded from a module
    interface was checked when its own module compiled.  An impl on a type
    alias of the merged module is "`Id` is a type alias for `Foo`: write
    `impl Foo`" at the same place (LARB R35), and one on a primitive is
    "`i32` is a built-in type; it can't have an `impl`" (LARB R36; ritz1's
    half is #3371).  ritz1 says the same for an
    unknown type and an alias (monomorph.ritz, refuse_impls_on_unknown_types,
    #3369).

    The impl's trait is judged too, at its name (AGAST #4197): known if the
    merged module declares it (an import counts) or the compiler does
    (trait_bounds.COMPILER_TRAITS), the same rule as an unknown trait in a
    bound (check_unknown_bound_traits, #3468)."""
    trait_set = set(COMPILER_TRAITS)
    trait_set.update(item.name for item in module.items if isinstance(item, rast.TraitDef))
    trait_defs = {item.name: item for item in module.items
                  if isinstance(item, rast.TraitDef)}
    known = {item.name for item in module.items
             if isinstance(item, (rast.StructDef, rast.EnumDef))}
    # A type alias is known, but not an impl target (LARB R35, #3368): a
    # type's methods live under the name it was declared with, and an alias
    # of an imported type would be a way around #3256.
    aliases = {item.name: item.target for item in module.items
               if isinstance(item, rast.TypeAlias)}
    # Scalars, SIMD vectors and the built-ins.  Not `Self` (it names no type
    # outside an impl) or `void`: ritz1 knows neither as an impl target.
    known |= NameResolver.BUILTIN_TYPES - {'Self', 'void'}
    errors = []
    for item in module.items:
        if (isinstance(item, rast.ImplBlock) and hasattr(item, 'trait_span')
                and item.trait_name not in trait_set):
            errors.append(f"{item.trait_span}: unknown trait `{item.trait_name}`")
        if (not isinstance(item, rast.ImplBlock) or not hasattr(item, 'type_span')
                or item.type_name in item.type_params):
            continue
        if item.type_name in aliases:
            target = type_to_string(aliases[item.type_name])
            errors.append(f"{item.type_span}: `{item.type_name}` is a type alias "
                          f"for `{target}`: write `impl {target}`")
        elif item.type_name in PRIMITIVES or item.type_name in POINTER_TARGETS:
            # R36's revisit (#4294): a trait impl on a primitive / `*u8` is
            # legal in the trait's file, and nowhere else.  An inherent impl
            # is still the old refusal.
            if item.trait_name is None:
                errors.append(f"{item.type_span}: `{target_spelling(item.type_name)}` "
                              f"is a built-in type; it can't have an `impl`")
            elif not in_trait_file(item, trait_defs):
                errors.append(f"{item.type_span}: {misplaced_target(item.type_name)}")
        elif item.type_name not in known:
            errors.append(f"{item.type_span}: unknown type `{item.type_name}`")
    return errors
