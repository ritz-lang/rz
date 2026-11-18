"""A type name that names nothing is refused, at the name (AGAST #3932).

`struct P` / `name: Nope` and `let q: Nope = 0` compiled under ritz0, which
laid `Nope` out as an opaque `{ i8 }`, and ritz1 emitted `%Nope` IR clang
refused with no source location.  Every compiler now says
"unknown type `Nope`" where the name is written, the words #3264 uses for an
`impl` on one.

The walk is name_resolver's (it runs in full only under `--check-names`),
keeping only its type-name findings: known is a primitive, a SIMD vector, a
built-in type, a struct, enum, alias or trait of the merged module (an
import counts), an item's own type parameter, or a module-qualified name.
Beyond name_resolver's walk, an enum variant's payload and an alias's target
are type positions too.  An `impl`'s target is check_unknown_impl_targets's
(builtin_types.py), which runs first.  ritz1's half is sema_type.ritz.
"""

import ritz_ast as rast
from name_resolver import NameResolver


def unknown_type(name: str) -> str:
    return f"unknown type `{name}`"


class _TypeNames(NameResolver):
    """name_resolver's walk, reporting only type names that resolve to nothing."""

    def __init__(self, module_names=None):
        super().__init__(module_names)
        self.unknown: list[str] = []

    def _check_type_name(self, name, span):
        before = len(self.errors)
        super()._check_type_name(name, span)
        if len(self.errors) > before:
            self.unknown.append(
                f"{span}: {unknown_type(name)}" if span else unknown_type(name)
            )

    def _check_type(self, type_node):
        # name_resolver's walk stops at a reference and a tuple.
        if isinstance(type_node, rast.RefType):
            self._check_type(type_node.inner)
        elif isinstance(type_node, rast.TupleType):
            for elem in type_node.elements:
                self._check_type(elem)
        else:
            super()._check_type(type_node)

    def _check_impl(self, impl):
        # The target is builtin_types.check_unknown_impl_targets's to judge.
        with self._generic(impl.type_params):
            for method in impl.methods:
                self._check_function(method)

    def _check_item(self, item):
        if isinstance(item, rast.EnumDef):
            with self._generic(getattr(item, "type_params", None)):
                for variant in item.variants:
                    for ty in getattr(variant, "fields", None) or ():
                        self._check_type(ty)
        elif isinstance(item, rast.TypeAlias):
            with self._generic(getattr(item, "type_params", None)):
                self._check_type(item.target)
        else:
            super()._check_item(item)


def check_unknown_type_names(module: rast.Module, module_names=None) -> list[str]:
    """One located error per written type name nothing declares."""
    checker = _TypeNames(module_names)
    checker.resolve(module)
    return checker.unknown
