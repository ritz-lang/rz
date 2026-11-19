"""Named struct-variant patterns and construction (docs/ENUM_VARIANTS.md
§4–5, AGAST #4187).

A struct-declared variant

    enum Msg
        SetViewport
            width: i32
            height: i32

may be matched as `SetViewport { height, width } =>` (or qualified,
`Msg.SetViewport { .. }`) and built as `SetViewport { width: 1, height: 2 }`.
Field names are sugar over the positional forms, so this pass, run on the
merged module after import resolution, rewrites each into its positional
equivalent: the pattern's bindings are reordered into declaration order, and
the literal becomes the call `SetViewport(1, 2)`.  Every later pass sees only
positional forms.  ritz1 does the same mapping in its emitter
(ritz1/src/struct_variants.ritz).

Each field must be named exactly once.  A literal's values are evaluated in
the variant's field order, as the positional call evaluates them.

Errors, located at the variant's name and worded the same in every compiler:
a named form on a variant declared without field names, a field the variant
does not declare, one named twice, and one left out.
"""

from typing import Dict, List, Optional

import ritz_ast as rast


def no_named_fields(v: str) -> str:
    return f"variant `{v}` has no named fields"


def no_such_field(v: str, f: str) -> str:
    return f"variant `{v}` has no field `{f}`"


def named_twice(v: str, f: str) -> str:
    return f"field `{f}` of variant `{v}` named twice"


def missing_field(v: str, f: str) -> str:
    return f"missing field `{f}` of variant `{v}`"


def _order(variant: rast.Variant, written: List[str]) -> tuple:
    """(index of each declared field in `written`, error or None)."""
    v = variant.name
    if not variant.is_struct_variant():
        return None, no_named_fields(v)
    seen: Dict[str, int] = {}
    for i, name in enumerate(written):
        if name not in variant.field_names:
            return None, no_such_field(v, name)
        if name in seen:
            return None, named_twice(v, name)
        seen[name] = i
    for name in variant.field_names:
        if name not in seen:
            return None, missing_field(v, name)
    return [seen[name] for name in variant.field_names], None


def rewrite_named_variants(module: rast.Module) -> List[str]:
    """Rewrite named variant patterns and literals in place; return located
    errors."""
    enums = [it for it in module.items if isinstance(it, rast.EnumDef)]
    if not enums:
        return []
    structs = {it.name for it in module.items if isinstance(it, rast.StructDef)}
    by_name: Dict[str, List[tuple]] = {}
    for e in enums:
        for v in e.variants:
            by_name.setdefault(v.name, []).append((e.name, v))
    errors: List[str] = []

    def variant_for(name: str, qualifier: Optional[str]) -> Optional[rast.Variant]:
        """The variant a named form names.  Several enums may declare the
        same name: a struct-declared one wins; the rest are left to the
        passes that resolve positional forms by the scrutinee's type, which
        only works here if they agree on the field order."""
        found = [v for (e, v) in by_name.get(name, ())
                 if qualifier is None or e == qualifier]
        if not found:
            return None
        named = [v for v in found if v.is_struct_variant()]
        if not named:
            return found[0]
        return named[0]

    def pattern(node: rast.VariantPattern) -> None:
        variant = variant_for(node.name, node.qualifier)
        if variant is None:
            return  # no such variant: the usual unknown-variant error
        order, err = _order(variant, node.field_names)
        if err:
            errors.append(f"{node.span}: {err}")
            return
        node.fields = [node.fields[i] for i in order]
        node.field_names = None

    def literal(node: rast.StructLit):
        if node.name in structs or node.type_args:
            return node
        variant = variant_for(node.name, None)
        if variant is None:
            return node  # unknown type: type_names.py says so
        order, err = _order(variant, [n for (n, _) in node.fields])
        if err:
            errors.append(f"{node.span}: {err}")
            return node
        return rast.Call(node.span, rast.Ident(node.span, node.name),
                         [node.fields[i][1] for i in order])

    skip = rast.Type

    def visit(x):
        if isinstance(x, rast.Node) and not isinstance(x, skip):
            walk(x)
            if isinstance(x, rast.VariantPattern) and x.field_names is not None:
                pattern(x)
            elif isinstance(x, rast.StructLit):
                return literal(x)
            return x
        if isinstance(x, list):
            for i, y in enumerate(x):
                x[i] = visit(y)
        elif isinstance(x, tuple):
            return tuple(visit(y) for y in x)
        return x

    def walk(node):
        d = node.__dict__
        for k, v in d.items():
            if isinstance(v, (rast.Node, list, tuple)):
                d[k] = visit(v)

    for item in module.items:
        walk(item)
    return errors
