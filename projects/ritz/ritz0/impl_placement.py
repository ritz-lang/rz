"""Where an `impl` may live, and what it covers (LARB R65, AGAST #3493; §12.2).

An inherent `impl T` is in the file that declares `T`. A trait impl is in the
type's file or the trait's file; a trait no module declares (Drop, Index…,
the compiler's own) counts as the type's file. One flat namespace (§15.3)
gives no way to say which file's method a call means: two files adding
`Foo.tag` failed at link with no location, and a method added in one file
reached every file that imported it.

An impl covers every instantiation: `impl<T> G<T>`, never `impl G<u8>`.
`impl G<u8>` alone was an unlocated ValueError, and next to `impl<T> G<T>`
ritz0 silently ran the generic body.

A generic impl declares its parameters (LARB R81, #1390): in `impl Box<T>`
without `<T>`, `T` names nothing, which is "unknown type `T`" at the `T`
rather than R65's message, and was a ValueError traceback before R65.

The other two errors are located at the impl's type name. Only parsed impls carry
`type_span`; one loaded from a module interface was checked when its own
module compiled. Impls on types nothing declares (primitives, built-ins,
unknown names) are builtin_types.py's errors. ritz1's half is #3494.
"""

from pathlib import Path

import ritz_ast as rast
from builtin_types import BUILTIN_IMPL_TARGETS
from name_resolver import NameResolver
from type_names import unknown_type


def _file(item) -> str | None:
    path = getattr(item, 'source_file', None)
    return str(Path(path).resolve()) if path else None


def _misplaced(impl: rast.ImplBlock, decl, traits: dict) -> str | None:
    """The placement error for `impl`, or None if its file may hold it."""
    type_file, impl_file = _file(decl), _file(impl)
    if type_file is None or impl_file is None or impl_file == type_file:
        return None
    trait = traits.get(impl.trait_name) if impl.trait_name else None
    if trait is not None and _file(trait) == impl_file:
        return None
    return (f"`{impl.type_name}` is declared in {Path(type_file).name}: "
            f"its `impl` must be there (§12.2)")


def _covers_every_instantiation(impl: rast.ImplBlock, decl) -> bool:
    """Every argument of the impl's type is one of its own parameters, each once."""
    args = impl.impl_type.args if isinstance(impl.impl_type, rast.NamedType) else []
    if not (decl.type_params or args):
        return True
    names = [a.name for a in args
             if isinstance(a, rast.NamedType) and not a.args and a.name in impl.type_params]
    return len(names) == len(args) == len(set(names))


def _free_param(impl: rast.ImplBlock, decl, known) -> str | None:
    """LARB R81 (#1390): `impl Box<T>` without `<T>`. A generic impl declares
    its parameters; here `T` is an ordinary type name, and it names nothing.
    Located at the `T`."""
    args = impl.impl_type.args if isinstance(impl.impl_type, rast.NamedType) else []
    for arg in args:
        if (isinstance(arg, rast.NamedType) and not arg.args
                and arg.name not in impl.type_params and not known(arg.name)):
            params = ", ".join(decl.type_params)
            return (f"{arg.span}: {unknown_type(arg.name)}: a generic impl "
                    f"declares it, `impl<{params}> {impl.type_name}<{params}>`")
    return None


def _partial(impl: rast.ImplBlock, decl) -> str | None:
    if _covers_every_instantiation(impl, decl):
        return None
    params = ", ".join(decl.type_params)
    return (f"an impl covers every instantiation of `{impl.type_name}`: "
            f"write `impl<{params}> {impl.type_name}<{params}>`")


def check_impl_placement(module: rast.Module) -> list[str]:
    """One located error per parsed `impl` in the wrong file or on one
    instantiation. Runs on the merged module, after import resolution, when
    every declaration carries its `source_file`."""
    decls = {item.name: item for item in module.items
             if isinstance(item, (rast.StructDef, rast.EnumDef))}
    traits = {item.name: item for item in module.items
              if isinstance(item, rast.TraitDef)}
    declared = {item.name for item in module.items
                if isinstance(item, (rast.StructDef, rast.EnumDef,
                                     rast.TraitDef, rast.TypeAlias))}

    def known(name: str) -> bool:
        return name in declared or name in NameResolver.BUILTIN_TYPES

    errors = []
    for impl in module.items:
        if not isinstance(impl, rast.ImplBlock) or not hasattr(impl, 'type_span'):
            continue
        decl = decls.get(impl.type_name)
        if decl is None:
            continue
        free = _free_param(impl, decl, known)
        if free is not None:
            errors.append(free)
            continue
        trait = traits.get(impl.trait_name) if impl.trait_name else None
        # R36's revisit (#4294): `impl Display for Span<u8>` is a concrete
        # instantiation, which R65 otherwise refuses, and is legal in the
        # trait's file.  StrView has no instantiation; the same file rule
        # already reaches it through `_misplaced`.
        builtin_concrete = (impl.type_name in BUILTIN_IMPL_TARGETS
                            and trait is not None
                            and _file(trait) == _file(impl))
        errors_for = [_misplaced(impl, decl, traits)]
        if not builtin_concrete:
            errors_for.append(_partial(impl, decl))
        for error in errors_for:
            if error is not None:
                errors.append(f"{impl.type_span}: {error}")
                break
    return errors
