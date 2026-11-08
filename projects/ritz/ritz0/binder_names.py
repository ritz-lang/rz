"""A local can't take the name of a module value (AGAST #2407, LARB R12; LANGUAGE_SPEC §4.3).

A local binding (`let`, `var`, a param, a `for` variable, a variant payload's
name) that takes the name of a `const`, a global `var` or an enum variant is a
located error at the name. With no local ever named like one, a bare read of the
name has one meaning, and no compiler has a lookup order to get wrong.

A top-level match arm's name is a binding only where it isn't a test: against
an enum a name is that enum's variant, and against an integer a `const` compares
(§8.2). Only the emitter knows the scrutinee's type, so it judges those arms with
`refusal` below (`_refuse_arm_names`). Every other binder is judged here, before
anything is emitted, so a generic fn is judged though nothing instantiates it.

Fn names are free: a call says it wants a fn. ritz1's twin is binder_check.ritz;
test_local_takes_module_name.py holds the three compilers to one table.
"""

from dataclasses import fields, is_dataclass
from typing import Dict, Iterator, List, Optional, Tuple

import ritz_ast as rast
from name_resolver import BUILTIN_VARIANTS


def module_values(module: rast.Module) -> Dict[str, str]:
    """Every name a bare read reaches as a module value, to what it is.

    A const outranks a global, and both a variant, when one name is several.
    """
    found: Dict[str, str] = {name: "variant" for name in BUILTIN_VARIANTS}
    for item in module.items:
        if isinstance(item, rast.EnumDef):
            for variant in item.variants:
                found[variant.name] = "variant"
    for item in module.items:
        if isinstance(item, rast.VarDef):
            found[item.name] = "global"
    for item in module.items:
        if isinstance(item, rast.ConstDef):
            found[item.name] = "const"
    return found


def refusal(kind: str, name: str) -> str:
    return f"a local can't take the name of a {kind}: '{name}' — rename the local"


def call_refusal(name: str) -> str:
    return f"'{name}' is a local, not a fn: it can't be called"


def _binders(node) -> Iterator[Tuple[str, Optional[rast.Span]]]:
    """Each local `node` binds, below it, but no top-level arm's name."""
    if isinstance(node, (rast.FnDef, rast.Lambda)):
        for param in node.params:
            yield param.name, param.span
    elif isinstance(node, rast.Closure):
        for param in node.params:
            yield param.name, param.span or node.span
    elif isinstance(node, (rast.LetStmt, rast.VarStmt)):
        yield node.name, node.name_span or node.span
    elif isinstance(node, rast.LetTupleStmt):
        for i, name in enumerate(node.names):
            spans = node.name_spans
            yield name, spans[i] if i < len(spans) else node.span
    elif isinstance(node, rast.ForStmt):
        yield node.var, node.var_span or node.span
    elif isinstance(node, rast.MatchArm):
        # The arm's own name is the emitter's (see the module docstring).
        if not isinstance(node.pattern, rast.IdentPattern):
            yield from _pattern_binders(node.pattern)
    for child in _children(node):
        yield from _binders(child)


def _pattern_binders(pattern) -> Iterator[Tuple[str, Optional[rast.Span]]]:
    if isinstance(pattern, rast.IdentPattern):
        yield pattern.name, pattern.span
    elif isinstance(pattern, rast.VariantPattern):
        for field_pattern in pattern.fields:
            yield from _pattern_binders(field_pattern)
    elif isinstance(pattern, rast.StructPattern):
        for _, field_pattern in pattern.fields:
            yield from _pattern_binders(field_pattern)


def _children(node) -> Iterator:
    """The AST nodes directly below `node`, in source order. Types hold none."""
    if not is_dataclass(node) or isinstance(node, (rast.Type, rast.Pattern)):
        return
    for f in fields(node):
        if f.name == 'span':
            continue
        value = getattr(node, f.name, None)
        items = value if isinstance(value, (list, tuple)) else (value,)
        for item in items:
            if isinstance(item, tuple):
                yield from (part for part in item if is_dataclass(part))
            elif is_dataclass(item) and not isinstance(item, type):
                yield item


def _judged_fns(module: rast.Module, source_path: Optional[str]) -> Iterator[rast.FnDef]:
    """The fns this compile emits a body for: its own, and an imported generic
    one it may instantiate. An imported fn's other bodies are its own file's."""
    def own(item) -> bool:
        where = getattr(item, 'source_file', None)
        return where is None or source_path is None or where == source_path

    def judged(fn, generic) -> bool:
        return not fn.is_decl and (own(fn) or (generic and bool(fn.body.stmts or fn.body.expr)))

    for item in module.items:
        if isinstance(item, rast.FnDef) and judged(item, bool(item.type_params)):
            yield item
        elif isinstance(item, rast.ImplBlock):
            for method in item.methods:
                generic = bool(item.type_params or method.type_params)
                if judged(method, generic) or (own(item) and not method.is_decl):
                    yield method


def check_binders(module: rast.Module, source_path: Optional[str] = None) -> List[str]:
    """`file:line:col: message` for each local named like a module value."""
    values = module_values(module)
    errors = []
    for fn in _judged_fns(module, source_path):
        for name, span in _binders(fn):
            kind = values.get(name)
            if kind is None:
                continue
            where = f"{span.file}:{span.line}:{span.column}: " if span else ""
            errors.append(where + refusal(kind, name))
    return errors
