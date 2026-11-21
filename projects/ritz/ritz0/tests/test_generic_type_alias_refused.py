"""AGAST #3813: a generic `type` alias is refused by name, at the `<`.

`type Ptr<T> = *T` used to fail with `Expected EQ, got LT`: located, but
it didn't say what was wrong. ritz0 has no generic aliases, so
parse_type_alias now names the construct at the `<`:

    generic type aliases are not supported: `type Ptr<T>`

A non-generic alias (`type IntPtr = *i32`) still parses (the control).
"""

import pytest

from parser import ParseError, parse


@pytest.mark.unit
@pytest.mark.parametrize("source, shown, column", [
    ("type Ptr<T> = *T\n", "type Ptr<T>", 9),
    ("type Pair<A, B> = *A\n", "type Pair<A, B>", 10),
])
def test_generic_type_alias_names_the_construct_at_the_lt(source, shown, column):
    with pytest.raises(ParseError) as info:
        parse(source, "c.ritz")
    err = info.value
    assert err.message == f"generic type aliases are not supported: `{shown}`"
    # Located at the `<`.
    assert (err.span.line, err.span.column) == (1, column)


@pytest.mark.unit
def test_non_generic_type_alias_still_parses():
    module = parse("type IntPtr = *i32\n", "c.ritz")
    assert module.items[0].name == "IntPtr"
