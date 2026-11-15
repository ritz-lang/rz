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

import ritz_ast as rast
from name_resolver import NameResolver

# Built-in type -> the ritzlib module that declares it as an ordinary type.
BUILTIN_TYPES = {
    "Span": "ritzlib.span",
    "StrView": "ritzlib.strview",
    "Option": "ritzlib.option",
    "Result": "ritzlib.result",
}


def refusal(type_name: str) -> str:
    return (f"`{type_name}` is a built-in type and can't be extended here: "
            f"import {BUILTIN_TYPES[type_name]} or declare your own type")


def check_builtin_impls(module: rast.Module) -> list[str]:
    """One located error per `impl` whose target is a built-in type.

    Runs on the merged module, after import resolution, so an imported
    declaration counts as the program's own."""
    declared = {item.name for item in module.items
                if isinstance(item, (rast.StructDef, rast.EnumDef))}
    return [f"{item.span}: {refusal(item.type_name)}"
            for item in module.items
            if isinstance(item, rast.ImplBlock)
            and item.type_name in BUILTIN_TYPES
            and item.type_name not in declared]


def check_unknown_impl_targets(module: rast.Module) -> list[str]:
    """One located error per `impl` on a type nothing declares (AGAST #3264).

    `impl Foo` with no `struct Foo` / `enum Foo` in scope compiled, and its
    methods were unreachable; so did `impl Vec<u8>` without ritzlib.vec.
    Located at the impl's type name.  Known: a struct, enum or type alias of
    the merged module (an import counts), a name the resolver has built in
    (a primitive, a SIMD vector, a built-in type: an impl on one of the last
    is check_builtin_impls's error), or one of the impl's own type
    parameters.  Only parsed impls carry `type_span`; one loaded from a module
    interface was checked when its own module compiled.  ritz1 says the same
    (monomorph.ritz, refuse_impls_on_unknown_types)."""
    known = {item.name for item in module.items
             if isinstance(item, (rast.StructDef, rast.EnumDef, rast.TypeAlias))}
    # Scalars, SIMD vectors and the built-ins.  Not `Self` (it names no type
    # outside an impl) or `void`: ritz1 knows neither as an impl target.
    known |= NameResolver.BUILTIN_TYPES - {'Self', 'void'}
    return [f"{item.type_span}: unknown type `{item.type_name}`"
            for item in module.items
            if isinstance(item, rast.ImplBlock)
            and hasattr(item, 'type_span')
            and item.type_name not in known
            and item.type_name not in item.type_params]
