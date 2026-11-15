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
