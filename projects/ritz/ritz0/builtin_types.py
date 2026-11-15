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
