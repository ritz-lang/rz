"""`module.item` access was removed in RERITZ (LANGUAGE_SPEC §15.3, AGAST #2215).

Imported names land in one flat namespace, so `m.S`, `m.K`, `m.f()` and a
`m.K =>` arm are refused, located: a type at the type (parser.py), an
expression or pattern at the use (emitter_llvmlite.py).  `Enum.Variant` and a
value's `.field` are not module access and are unaffected.  ritz1 prints the
same text (ritz1/src/qualified_access.ritz).
"""


def module_item_access_removed(qualifier: str, name: str) -> str:
    return (f"`{qualifier}.{name}`: there is no `module.item` access (LANGUAGE_SPEC §15.3). "
            f"Imported names share one namespace, so write `{name}`")
