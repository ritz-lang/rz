"""Harland and indium print through interpolation, and mains are Ritz-native (AGAST #4564).

#203 moved the hosted binaries off ritzlib.io's legacy printers (prints,
prints_cstr, print_int, print_hex, ...) and the C-shaped
`fn main(argc: i32, argv: **u8)`. The kernel had already moved to klog
(#1885) and the UEFI loader to boot_abi's serial printer (#4601); indium's
userland still chained libharland's print_str / print_int / print_digit and
read argv as `**u8`.

On Harland, `print("... {n}\\n")` lowers to an inline formatter and a raw
write syscall (no ritzlib import), so it links in every indium binary,
freestanding or not. A main that wants its arguments takes
`args: Span<StrView>` and gets the compiler's adapter (#200, #4019).

These read the sources of projects/harland and projects/indium: no call to,
or definition of, a legacy printer, and no C-shaped main. Runs in
`make tools-unit`.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PROJECTS = Path(__file__).resolve().parents[2]
ROOTS = (PROJECTS / "harland", PROJECTS / "indium")

# ritzlib.io's printers (every pub fn but vec_read_all_fd) and libharland's.
LEGACY = (
    "prints", "eprints", "prints_cstr", "eprints_cstr", "println_cstr",
    "eprintln_cstr", "print_char", "eprint_char", "print_int", "eprint_int",
    "print_hex", "print_size_human", "println", "eprintln", "print_string",
    "eprint_string", "println_string", "eprintln_string", "print_i64",
    "println_i64", "eprint_i64", "eprintln_i64", "print_hex64",
    "println_hex64", "print_str", "print_digit",
)
LEGACY_CALL = re.compile(r"\b(" + "|".join(LEGACY) + r")\s*\(")

# `fn main(argc: i32, argv: **u8)`, whatever the parameter names.
C_MAIN = re.compile(r"\bfn\s+main\s*\(\s*\w+\s*:\s*i32\s*,\s*\w+\s*:\s*\*\*u8\b")


def code(line):
    """line without its comment or string literals."""
    line = re.sub(r'c?"(?:[^"\\]|\\.)*"', '""', line)
    return line.split("#", 1)[0]


def legacy_hits(root):
    """'file:line: text' for each legacy printer or C-shaped main under root."""
    hits = []
    for path in sorted(root.rglob("*.ritz")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            text = code(line)
            if LEGACY_CALL.search(text) or C_MAIN.search(text):
                hits.append(f"{path.relative_to(root.parent)}:{n}: {line.strip()}")
    return hits


def test_scanner_sees_each_legacy_form(tmp_path):
    (tmp_path / "a.ritz").write_text(
        "pub fn main(argc: i32, argv: **u8) -> i32\n"
        '    print_str(c"x")  # old\n'
        '    print("{n}\\n")\n'
        "    print_int(n)\n"
        '    prints_cstr(c"y")\n'
        "pub fn print_digit(n: i32)\n"
        "    print_hex_prefix(v)\n"
        '    print("print_str(")  # print_int(n)\n'
        "pub fn main(args: Span<StrView>) -> i32\n"
        "fn main(c: i32, v: **u8) -> i32\n"
    )
    assert [h.split(": ", 1)[0] for h in legacy_hits(tmp_path)] == [
        f"{tmp_path.name}/a.ritz:{n}" for n in (1, 2, 4, 5, 6, 10)
    ]


@pytest.mark.parametrize("root", ROOTS, ids=lambda p: p.name)
def test_no_legacy_print_or_c_main(root):
    hits = legacy_hits(root)
    assert not hits, (
        f"{len(hits)} legacy print call(s) or C-shaped main(s) under "
        f"projects/{root.name}: print with interpolation (`print(\"{{n}}\\n\")`; "
        "klog in the kernel) and take `args: Span<StrView>`:\n"
        + "\n".join(hits[:40])
    )
