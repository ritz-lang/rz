"""AGAST #3891: a plain `import` is private (LANGUAGE_SPEC §15.1, §15.4).

`import m` brings in what `m` defines: the items `m` declares, and those of
the modules `m` re-exports with `pub import`. What `m` reaches only through
its own plain `import` is not brought in (the rule LARB R54 set for a
selective import's list; §15.4's `pub import` is the re-export). ritz0
merges every transitive import into one module, which codegen needs, so the
rule is a check at the use: a name the compiled file writes that reaches it
only through some module's plain import is an error there, with a hint:

    main.ritz:4:5: `c_val` is undefined (#3891): it comes from `c`; import it, or have `b` `pub import` it
    /abs/c.ritz:1:1: note: `c_val` is declared here

Only the compiled file's own uses are checked: every file is compiled on its
own, so each use is checked once, in the file that writes it. Method calls
on a value are not uses of a name: `x.len()` needs `x`'s type, not its name.
The scope walk is name_resolver's, so a local that shadows a hidden name is
the local.
"""

import os
from collections import deque
from typing import Dict, List, Optional, Tuple

import ritz_ast as rast
from name_resolver import BUILTIN_VARIANTS, NameResolver, Scope
from selective_import import _DECLARATIONS, _Definitions

_BUILTINS = (NameResolver.BUILTIN_TYPES | NameResolver.BUILTINS
             | BUILTIN_VARIANTS)

# A hidden name: (the module it comes from, as its importer wrote it, the
# module whose plain import brings it in, as written, the declaration and
# its file).
Hint = Tuple[str, str, rast.Item, str]


def _dotted(imp: rast.Import) -> str:
    return '.'.join(imp.path)


def hidden_names(own_items: List[rast.Item], resolver, from_file: str,
                 merged: rast.Module) -> Dict[str, Hint]:
    """Each top-level name the merged module has that `from_file` neither
    declares nor imports (directly, or through a `pub import`), with where it
    comes from. `resolver` has resolved `from_file` already."""
    definitions = _Definitions(resolver)
    visible = {item.name for item in own_items
               if isinstance(item, _DECLARATIONS)}
    direct = []
    for imp in own_items:
        if not isinstance(imp, rast.Import):
            continue
        target = resolver._resolve_import_path(imp.path, from_file)
        if target is None:
            continue
        visible.update(definitions.defined(target))
        direct.append((target, _dotted(imp)))

    # A built-in (`StrView`, `Option`, `Some`, `print`) is everywhere, even
    # where ritzlib declares it, so it is never hidden.
    candidates = ({item.name for item in merged.items
                   if isinstance(item, _DECLARATIONS)}
                  - visible - _BUILTINS)
    hints: Dict[str, Hint] = {}
    if not candidates:
        return hints
    # Breadth first from the direct imports, so a hint names the nearest
    # plain import that brings the name in.
    queue = deque(direct)
    seen = {target for target, _ in direct}
    while queue and len(hints) < len(candidates):
        module_path, written = queue.popleft()
        module = resolver.load_module(module_path)
        for imp in module.items:
            if not isinstance(imp, rast.Import):
                continue
            target = resolver._resolve_import_path(imp.path, module_path)
            if target is None:
                continue
            for name, (item, decl_file) in definitions.defined(target).items():
                if name in candidates and name not in hints:
                    hints[name] = (_dotted(imp), written, item, decl_file)
            if target not in seen:
                seen.add(target)
                queue.append((target, _dotted(imp)))
    return hints


class _HiddenUses(NameResolver):
    """name_resolver's walk, reporting only uses of hidden names, in one
    file. Its own unknown-name errors are --check-names', and dropped."""

    def __init__(self, hidden: Dict[str, Hint], from_file: str):
        super().__init__()
        self.hidden = hidden
        self.from_file = os.path.realpath(from_file)
        self.found: List[str] = []

    def _use(self, name: str, span: Optional[rast.Span]) -> None:
        hint = self.hidden.get(name)
        if hint is None or span is None or not span.file:
            return
        if os.path.realpath(span.file) != self.from_file:
            return
        origin, via, item, decl_file = hint
        message = (f"{span}: `{name}` is undefined (#3891): it comes from "
                   f"`{origin}`; import it, or have `{via}` `pub import` it")
        decl = item.span
        if decl is not None and decl.file and not decl.file.startswith('<'):
            message += (f"\n{decl_file}:{decl.line}:{decl.column}: note: "
                        f"`{name}` is declared here")
        self.found.append(message)

    def _check_expr(self, expr: rast.Expr, scope: Scope):
        if isinstance(expr, rast.Ident) and not scope.contains(expr.name):
            self._use(expr.name, expr.span)
        elif (isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident)
              and expr.func.name != 'sizeof'
              and not scope.contains(expr.func.name)):
            self._use(expr.func.name, expr.func.span)
        elif isinstance(expr, rast.TypeExpr):
            self._check_type(expr.ty)
        elif (isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident)
              and expr.func.name == 'sizeof'):
            # #3981: sizeof's operand is a type that reads as an expression
            # (`sizeof(K)`), or one parsed as a type (`sizeof([2]K)`), and
            # name_resolver skips it: check it as an annotation's type is.
            for arg in expr.args:
                self._check_expr(arg, scope)
        elif isinstance(expr, rast.InterpString):
            for part in expr.exprs:
                self._check_expr(part, scope)
        super()._check_expr(expr, scope)

    def _check_pattern(self, pattern: rast.Pattern, scope: Scope):
        if isinstance(pattern, rast.VariantPattern) and pattern.qualifier:
            self._use(pattern.qualifier, pattern.span)
        super()._check_pattern(pattern, scope)

    def _check_type_name(self, name: str, span: Optional[rast.Span]):
        if name not in self.type_params:
            self._use(name, span)

    def _check_impl(self, impl: rast.ImplBlock):
        if impl.trait_name:
            self._use(impl.trait_name, impl.span)
        super()._check_impl(impl)


def check_import_visibility(own_items: List[rast.Item], resolver,
                            from_file: str,
                            merged: rast.Module) -> List[str]:
    """One error per use of a hidden name in `from_file`, in source order."""
    hidden = hidden_names(own_items, resolver, from_file, merged)
    if not hidden:
        return []
    walker = _HiddenUses(hidden, from_file)
    walker._collect_definitions(merged)
    for item in own_items:
        if not isinstance(item, rast.Import):
            walker._check_item(item)
    return walker.found
