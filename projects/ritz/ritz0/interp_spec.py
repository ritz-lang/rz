"""`{expr:spec}` format specs in print / eprint / format_into placeholders.

AGAST #201 (#198 Phase 2). A placeholder's spec is the text after its last
top-level `:` -- not inside nested `()`, `[]`, `{}` or a string / char
literal. Ritz has no `:` operator outside a struct literal's braces, so the
split is unambiguous. The valid specs are ritzlib/fmt/spec.ritz
`fmt_spec_parse`'s grammar, the v1 set:

    ?               Debug
    <N  >N  ^N      left / right / centre in a width N
    [0][N]R         R one of x X b o; a leading 0 needs a width N

N is decimal digits, at most 4096. Nothing else is a spec (no fill, no
precision, no `#?`, and not the empty text after a colon).

ritz1 has the same rules in ritz1/src/interp.ritz (interp_spec_colon,
interp_spec_valid) and the same two messages.
"""

from typing import Optional

MAX_WIDTH = 4096


def spec_colon(text: str) -> int:
    """Index of the last top-level `:` in a placeholder's raw text, or -1."""
    depth = 0
    quote: Optional[str] = None
    found = -1
    i = 0
    while i < len(text):
        c = text[i]
        if c == '\\':
            i += 2
            continue
        if quote is not None:
            if c == quote:
                quote = None
        elif c in '"\'':
            quote = c
        elif c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif c == ':' and depth == 0:
            found = i
        i += 1
    return found


def spec_valid(spec: str) -> bool:
    """Is `spec` (the text after the colon) one of the v1 specs?"""
    if spec == '?':
        return True
    i = 0
    align = spec[:1] in ('<', '>', '^')
    zero = False
    if align:
        i = 1
    elif spec[:1] == '0' and len(spec) > 1:
        zero = True
        i = 1
    digits_at = i
    width = 0
    while i < len(spec) and '0' <= spec[i] <= '9':
        width = width * 10 + ord(spec[i]) - 48
        if width > MAX_WIDTH:
            return False
        i += 1
    has_width = i > digits_at
    if align:
        return has_width and i == len(spec)
    if zero and not has_width:
        return False
    return i == len(spec) - 1 and spec[i] in 'xXbo'


def unknown_spec_message(expr: str, spec: str) -> str:
    return (f"unknown format spec `{spec}` in `{{{expr}:{spec}}}`: the v1 specs "
            "are x X b o, a zero-padded width (08x), <N >N ^N and ?")


def not_printed_message(spec: str) -> str:
    return (f"format spec `{spec}` is parsed but not printed until AGAST #202; "
            f"drop `:{spec}` for now")
