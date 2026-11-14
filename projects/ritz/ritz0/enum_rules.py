"""Enum conversion rules shared by ritz0's checker and its tests.

`n as E`, an integer to an enum, is refused for every enum (LARB R19, AGAST
#3040): an integer may name no variant, and `as` would make a value no
`match` covers.  ritz1 says the same words (emitter_expr.ritz,
int_as_enum_refused).
"""


def int_as_enum(enum_name: str) -> str:
    return (f"an integer can't be converted to enum `{enum_name}` with `as`: "
            f"it may name no variant; `match` on it")
