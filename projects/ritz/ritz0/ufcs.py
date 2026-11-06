"""Which standalone function a method call means on a type with no impl block.

The emitter dispatches on this, and the type checker needs the same answer: a
`self`-less `vec_push` takes its receiver as an `@&T` too (AGAST #2374).
"""

from typing import Optional

# UFCS prefixes for non-generic ritzlib types: `b.len()` on a Buffer calls
# `buf_len(@b)`. NOT the lowercased type name (Buffer -> buf_, ArgParser ->
# args_). ritz1 carries a copy of this table in
# ritz1/src/emitter_expr_call.ritz (ufcs_non_generic_prefix);
# test_ritz1_ufcs_prefix.py asserts the two agree (AGAST #1368).
UFCS_NON_GENERIC_PREFIXES = {
    'String': 'string_',
    'GrowBuf': 'growbuf_',
    'Buffer': 'buf_',
    'ArgParser': 'args_',
}


def find_ufcs_function(functions, type_name: str, method_name: str) -> Optional[str]:
    """Find a standalone function that acts as a method for the given type.

    This provides UFCS (Uniform Function Call Syntax) for types without impl blocks.
    Enables method syntax v.len() to desugar to vec_len$u8(&v) for Vec$u8.

    Mapping rules:
    - Vec$T.method()   -> vec_method$T
    - Span$T.method()  -> span_method$T
    - String.method()  -> string_method
    - GrowBuf.method() -> growbuf_method (or buf_method)

    `functions` is keyed by name. Returns the mangled name, or None.
    """
    # Known type prefixes and their function name mappings
    type_mappings = [
        ('Vec$', 'vec_'),      # Vec$u8 -> vec_
        ('Span$', 'span_'),    # Span$u8 -> span_
        ('Option$', 'option_'), # Option$i32 -> option_
        ('Result$', 'result_'), # Result$i32_Error -> result_
        ('Box$', 'box_'),      # Box$Point -> box_
    ]

    for prefix, fn_prefix in type_mappings:
        if type_name.startswith(prefix):
            # Extract type parameter suffix (e.g., "u8" from "Vec$u8")
            type_param = type_name[len(prefix):]
            base = f"{fn_prefix}{method_name}"

            # Preferred exact forms.
            exact_candidates = [
                f"{base}${type_param}",
                base,
            ]
            for candidate in exact_candidates:
                if candidate in functions:
                    return candidate

            # Namespaced/mangled fallback forms (strict suffix match only).
            for name in functions:
                if name.endswith(f"{base}${type_param}"):
                    return name
            # Generic template fallback (e.g., vec_push$T) if specialization missing.
            for generic_param in ("T", "U", "V", "K", "E"):
                generic_candidate = f"{base}${generic_param}"
                if generic_candidate in functions:
                    return generic_candidate
            for name in functions:
                if any(name.endswith(f"{base}${gp}") for gp in ("T", "U", "V", "K", "E")):
                    return name

    # Non-generic types: String, GrowBuf, Buffer, etc.
    if type_name in UFCS_NON_GENERIC_PREFIXES:
        fn_prefix = UFCS_NON_GENERIC_PREFIXES[type_name]
        candidate = f"{fn_prefix}{method_name}"
        if candidate in functions:
            return candidate
        for name in functions:
            if name.endswith(candidate):
                return name
        for name in functions:
            if candidate in name:
                return name

    return None
