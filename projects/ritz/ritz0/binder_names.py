"""A local's name has one meaning (LANGUAGE_SPEC §4.3).

A local binding (`let`, `var`, a param, a `for` variable, a tuple `let`'s names,
a match arm's name, a variant payload's name) is a located error at its name
when it takes the name of:

- a `const`, a global `var` or an enum variant (AGAST #2407, LARB R12), so a bare
  read of the name has one meaning and no compiler has a lookup order to get
  wrong; or
- a local still in scope in its fn (AGAST #2395, Aaron 2026-11-06, extended
  2026-11-08 on #2455): an enclosing block's, the same block's, a param's, a
  `for` variable's or an arm's. A name whose binding has gone out of scope is
  free again. `_` binds nothing.

A top-level match arm's name is a binding only where it isn't a test: against
an enum a name is that enum's variant, and against an integer a `const` compares
(§8.2). Only the emitter knows the scrutinee's type, so it judges an arm named
like a module value with `refusal` below (`_refuse_arm_names`). Every other
binder is judged here, before anything is emitted, so a generic fn is judged
though nothing instantiates it.

Fn names are free: a call says it wants a fn. ritz1's twin is binder_check.ritz;
test_local_takes_module_name.py and test_local_reuses_a_name.py hold the three
compilers to one table.
"""

from dataclasses import fields, is_dataclass
from typing import Dict, Iterator, List, Optional

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


def reuse_refusal(name: str, earlier: Optional[rast.Span]) -> str:
    at = f" (at {earlier.line}:{earlier.column})" if earlier else ""
    return (f"a local can't reuse a name bound earlier in its fn: '{name}'{at}"
            f" — rename the local")


class _Judge:
    """One fn's walk: the names in scope at each binder, innermost frame last.

    A binder is judged when it's reached, in source order: first against the
    module's values (R12), then against the names in scope (#2395). A `let`'s
    name is judged before its initialiser and bound after it, as it reads.
    """

    def __init__(self, values: Dict[str, str]):
        self.values = values
        self.frames: List[Dict[str, Optional[rast.Span]]] = []
        self.errors: List[str] = []

    def judge(self, name: str, span: Optional[rast.Span], also=None) -> None:
        """Refuse `name` if it's a module value's or still bound; `also` is a
        frame not pushed yet (a tuple `let`'s earlier names). `_` is never
        bound, so it passes."""
        where = f"{span.file}:{span.line}:{span.column}: " if span else ""
        kind = self.values.get(name)
        if kind is not None:
            self.errors.append(where + refusal(kind, name))
            return
        for frame in reversed(([also] if also else []) + self.frames):
            if name in frame:
                self.errors.append(where + reuse_refusal(name, frame[name]))
                return

    def bind(self, name: str, span: Optional[rast.Span]) -> None:
        if name != '_' and name not in self.values:
            self.frames[-1].setdefault(name, span)

    def binder(self, name: str, span: Optional[rast.Span]) -> None:
        self.judge(name, span)
        self.bind(name, span)

    def scoped(self, *nodes) -> None:
        self.frames.append({})
        for node in nodes:
            self.walk(node)
        self.frames.pop()

    def params(self, node, params) -> None:
        self.frames.append({})
        for param in params:
            span = param.span if isinstance(node, (rast.FnDef, rast.Lambda)) else (param.span or node.span)
            self.binder(param.name, span)
        self.walk(node.body)
        self.frames.pop()

    def pattern(self, pattern) -> None:
        if isinstance(pattern, rast.IdentPattern):
            self.binder(pattern.name, pattern.span)
        elif isinstance(pattern, rast.VariantPattern):
            for field_pattern in pattern.fields:
                self.pattern(field_pattern)
        elif isinstance(pattern, rast.StructPattern):
            for _, field_pattern in pattern.fields:
                self.pattern(field_pattern)

    def walk(self, node) -> None:
        if node is None:
            return
        if isinstance(node, (rast.FnDef, rast.Lambda, rast.Closure)):
            self.params(node, node.params)
        elif isinstance(node, rast.Block):
            self.scoped(*node.stmts, node.expr)
        elif isinstance(node, (rast.LetStmt, rast.VarStmt)):
            span = node.name_span or node.span
            self.judge(node.name, span)
            self.walk(node.value)
            self.bind(node.name, span)
        elif isinstance(node, rast.LetTupleStmt):
            spans = node.name_spans
            named = [(name, spans[i] if i < len(spans) else node.span)
                     for i, name in enumerate(node.names)]
            earlier: Dict[str, Optional[rast.Span]] = {}
            for name, span in named:
                self.judge(name, span, earlier)
                if name != '_':
                    earlier.setdefault(name, span)
            self.walk(node.value)
            for name, span in named:
                self.bind(name, span)
        elif isinstance(node, rast.ForStmt):
            self.walk(node.iter)
            self.frames.append({})
            self.binder(node.var, node.var_span or node.span)
            self.walk(node.body)
            self.frames.pop()
        elif isinstance(node, rast.MatchArm):
            self.frames.append({})
            if isinstance(node.pattern, rast.IdentPattern):
                # A module value's name is the emitter's to judge
                # (_refuse_arm_names); any other is a binding.
                if node.pattern.name not in self.values:
                    self.binder(node.pattern.name, node.pattern.span)
            else:
                self.pattern(node.pattern)
            self.walk(node.guard)
            self.walk(node.body)
            self.frames.pop()
        else:
            for child in _children(node):
                self.walk(child)


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
    """`file:line:col: message` for each local named like a module value
    (#2407), or like a local still in scope in its fn (#2395)."""
    judge = _Judge(module_values(module))
    for fn in _judged_fns(module, source_path):
        judge.walk(fn)
    return judge.errors
