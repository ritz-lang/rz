"""No workspace code calls ritzlib.io's deleted legacy printers (AGAST #4565).

#203 / #4565 moved every caller onto interpolated `print("..{x}..")` and
then deleted prints_cstr, println_cstr, print_int, print_hex and
print_string from ritzlib/io.ritz, with no wrappers.  A comment may still
name them (history); code may not, and neither may a new definition of the
same name.  harland and indium have their own, wider ban list
(test_harland_indium_print.py).  Runs in `make tools-unit`.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

WORKSPACE = Path(__file__).resolve().parents[3]
LEGACY = ("prints_cstr", "println_cstr", "print_int", "print_hex", "print_string")
LEGACY_CALL = re.compile(r"\b(" + "|".join(LEGACY) + r")\s*\(")


def code(line):
    """line without its comment or string literals."""
    line = re.sub(r'c?"(?:[^"\\]|\\.)*"', '""', line)
    return line.split("#", 1)[0]


def legacy_hits(root):
    """'file:line: text' for each legacy printer call or definition under root."""
    hits = []
    for path in sorted(root.rglob("*.ritz")):
        rel = path.relative_to(root).as_posix()
        if "/build/" in f"/{rel}" or "/archive/" in f"/{rel}":
            continue
        for n, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            if LEGACY_CALL.search(code(line)):
                hits.append(f"{rel}:{n}: {line.strip()}")
    return hits


def test_scanner_sees_each_form(tmp_path):
    (tmp_path / "a.ritz").write_text(
        "    print_int(n)\n"
        '    prints_cstr(c"y")\n'
        "pub fn print_hex(n: i64)\n"
        "    print_string (@s)\n"
        "    println_cstr(p)\n"
        "    print_hex64(n)\n"
        "    eprint_int(n)\n"
        '    print("print_int(")  # print_int(n)\n'
    )
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "b.ritz").write_text("    print_int(n)\n")
    assert [h.split(": ", 1)[0] for h in legacy_hits(tmp_path)] == [
        f"a.ritz:{n}" for n in (1, 2, 3, 4, 5)
    ]


def test_no_workspace_code_uses_a_legacy_printer():
    hits = legacy_hits(WORKSPACE / "projects") + legacy_hits(WORKSPACE / "bench")
    assert hits == [], "legacy printer calls:\n" + "\n".join(hits)
