"""Diagnostics for a typed binding, shared by ritz0, ritz1 and their tests.

ritz1 spells these out in `ritz1/src/let_check.ritz`: keep them identical.
"""


def another_struct(name: str, declared: str, actual: str) -> str:
    """`let name: declared = <a struct of type actual>` (AGAST #2293).

    A struct of one type is never a struct of another: there is no conversion,
    and reading one as the other would reinterpret its bytes.
    """
    return f"`{name}` is declared `{declared}` but its initialiser is a `{actual}`"


def another_struct_return(declared: str, actual: str) -> str:
    """`return c` / a tail `c` of a struct of type actual from a `-> declared` fn (AGAST #3293).

    The same rule as another_struct, at the return slot.
    """
    return f"the fn is declared `-> {declared}` but its return value is a `{actual}`"


def another_struct_assign(name: str, declared: str, actual: str) -> str:
    """`name = <a struct of type actual>` into a `declared` local (AGAST #3294)."""
    return f"`{name}` is declared `{declared}` but the value assigned is a `{actual}`"


def another_struct_field(field: str, declared: str, actual: str) -> str:
    """`v.field = <a struct of type actual>` into a `declared` field (AGAST #3294)."""
    return f"field `{field}` is declared `{declared}` but the value assigned is a `{actual}`"


def another_struct_argument(param: str, declared: str, actual: str) -> str:
    """`g(<a struct of type actual>)` for a `param: declared` parameter (AGAST #3294)."""
    return f"parameter `{param}` is declared `{declared}` but its argument is a `{actual}`"
