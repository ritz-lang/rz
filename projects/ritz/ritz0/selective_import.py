"""LARB R54 (AGAST #3466): a name in `import m { … }` must be one `m` defines.

LANGUAGE_SPEC §15.1. Each name in the list must be declared at the top level
of `m`, or re-exported by one of `m`'s `pub import`s; otherwise it is an
error at the name:

    main.ritz:1:17: `nope` is not defined in a

What `m` reaches only through its own plain `import` doesn't count. Private
types and consts do (type privacy isn't enforced). A private fn in the list
gets §15.2's error, at the import rather than at a call:

    main.ritz:1:17: `helper` is private to a.ritz; mark it `pub` (#3413)
    /abs/a.ritz:1:1: note: `helper` is declared here

The list is checked but still doesn't filter: `import m { a }` brings in all
of `m` as `import m` does.

Only the compiled file's own imports are checked. Every file is compiled on
its own, so each import is checked once, in the file that writes it.
"""

import os
from typing import Dict, List, Optional, Tuple

import ritz_ast as rast

# A defined name: the declaring item and the file it's declared in.
Defined = Dict[str, Tuple[rast.Item, str]]

_DECLARATIONS = (rast.FnDef, rast.ExternFn, rast.StructDef, rast.EnumDef,
                 rast.ConstDef, rast.VarDef, rast.TypeAlias, rast.TraitDef)


class _Definitions:
    """Memoised `defined(path)`: the names a module declares or re-exports."""

    def __init__(self, resolver):
        self.resolver = resolver
        self.memo: Dict[str, Defined] = {}
        self.active: set = set()

    def defined(self, path: str) -> Defined:
        if path in self.memo:
            return self.memo[path]
        if path in self.active:  # a `pub import` cycle: nothing more here
            return {}
        self.active.add(path)
        try:
            names = self._collect(path)
        finally:
            self.active.discard(path)
        self.memo[path] = names
        return names

    def _collect(self, path: str) -> Defined:
        names: Defined = {}
        module = self.resolver.load_module(path)
        for item in module.items:
            if not isinstance(item, _DECLARATIONS):
                continue
            # [[target_os]] variants share a name: a `pub` one wins, so the
            # private-fn error needs every variant private.
            seen = names.get(item.name)
            if seen is None or (not _is_pub(seen[0]) and _is_pub(item)):
                names[item.name] = (item, path)
        for item in module.items:
            if not (isinstance(item, rast.Import) and item.is_pub):
                continue
            target = self.resolver._resolve_import_path(item.path, path)
            if target is None:
                continue  # `m`'s own compile reports the missing module
            reexported = self.defined(target)
            wanted = item.items if item.items else list(reexported)
            for name in wanted:
                # A name `m`'s `pub import t { x }` lists that `t` doesn't
                # define is `m`'s error, reported when `m` is compiled.
                if name in reexported and name not in names:
                    names[name] = reexported[name]
        return names


def _is_pub(item: rast.Item) -> bool:
    return bool(getattr(item, 'is_pub', False))


def _private_fn(item: rast.Item) -> bool:
    """§15.2's private fn, with `_check_private_call`'s exemptions: an
    `extern fn` (not a FnDef) and `fn .. = extern` declare a symbol defined
    elsewhere; a generated fn has no declaration of its own to mark."""
    return (isinstance(item, rast.FnDef) and not item.is_pub
            and not getattr(item, 'is_decl', False)
            and not getattr(item, 'generated', False))


def check_selective_imports(imports: List[rast.Import], resolver,
                            from_file: str) -> List[str]:
    """One error per name, in source order, for the selective imports of
    `from_file` (already resolved by `resolver`)."""
    errors: List[str] = []
    definitions = _Definitions(resolver)
    for imp in imports:
        if not imp.items:
            continue
        target = resolver._resolve_import_path(imp.path, from_file)
        if target is None:
            continue  # _process_import already refused it
        defined = definitions.defined(target)
        spans: List[Optional[rast.Span]] = list(imp.item_spans or [])
        spans += [imp.span] * (len(imp.items) - len(spans))
        for name, span in zip(imp.items, spans):
            entry = defined.get(name)
            if entry is None:
                errors.append(f"{span}: `{name}` is not defined in "
                              f"{'.'.join(imp.path)}")
                continue
            item, decl_file = entry
            if _private_fn(item):
                message = (f"{span}: `{name}` is private to "
                           f"{os.path.basename(decl_file)}; mark it `pub` "
                           f"(#3413)")
                decl = item.span
                if decl is not None and not decl.file.startswith('<'):
                    message += (f"\n{decl_file}:{decl.line}:{decl.column}: "
                                f"note: `{name}` is declared here")
                errors.append(message)
    return errors
