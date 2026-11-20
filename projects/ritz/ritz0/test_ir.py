"""Reading ritz0's LLVM IR from tests.

Separate compilation (`--no-runtime`) keeps a private fn's external linkage but
gives its symbol its defining file's hash, `helper__1a2b3c4d` (AGAST #1858):
two files' private `be16`s are two symbols, not one defined twice.  A
`pub` fn's symbol is its name, as before.

Tests name a fn by its Ritz name.  These helpers match either form, so a test
does not depend on a private fn's symbol.  `__[0-9a-f]{8}` is the suffix; a
private fn in a single-file compile keeps its plain name on ritz0, while
ritz1 mangles every private free fn (AGAST #4356).
"""

import re

SUFFIX = r'(?:__[0-9a-f]{8})?'


def symbol(name: str) -> str:
    """Regex source for the IR symbol of `name`: quoted or bare, with or
    without the `__<8 hex>` file hash."""
    return r'@"?' + re.escape(name) + SUFFIX + r'"?'


def define(name: str) -> str:
    """Regex source for the `define ... @"name"(...)` line.  Not anchored, so
    it works with `re.search` and with `re.match`."""
    return r'define\b[^\n]*' + symbol(name) + r'\('


def strip(name: str) -> str:
    """The Ritz name of a captured IR symbol: the `__<8 hex>` suffix off."""
    return re.sub(r'__[0-9a-f]{8}$', '', name)


def define_text(ir: str, name: str) -> str:
    """`name`'s whole `define ... { ... }` in `ir`, closing `}` included."""
    m = re.search(r'^define\b[^\n]*' + symbol(name) + r'\(.*?^\}',
                  ir, re.M | re.S)
    assert m, f"no definition of {name} in IR:\n{ir[:3000]}"
    return m.group(0)


def define_rest(ir: str, name: str) -> str:
    """What the old `ir.split(f" @{name}(")[1].split("\\n}")[0]` gave: the
    rest of `name`'s `define` header, then its body, ending before the
    closing `}` line."""
    m = re.search(r'^define\b[^\n]*?' + symbol(name) + r'\(', ir, re.M)
    assert m, f"no definition of {name} in IR:\n{ir[:3000]}"
    return ir[m.end():].split("\n}", 1)[0]
