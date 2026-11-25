#!/usr/bin/env python3
"""ritzlib.fmt.digits stops on a span too short for its widest result (AGAST #4685).

`fmt_i64_into` and its neighbours took a bare `*u8` and trusted the caller to
size it (20 bytes for decimal, 16 for hex, 64 for any radix): a classic
overflow, exempt from the raw-ptr-param rule as a "format buffer sink".  They
now take a `[u8]` and return a StrView of the digits.  A span shorter than the
widest result ends the program through `ritz_platform_fatal(.., 101)`, for any
value, so an undersized buffer fails on its first call rather than on the first
big number, and never writes past its end.

Each case runs on ritz0, ritz1 and ritz1_selfhosted, linking the ritzlib
modules it imports (test_table_rows.ritzlib_build), as the HashMap missing-key
test in test_struct_index.py does: a trap ends the binary, so it can't be a
[[test]] in ritzlib/tests/test_fmt_digits.ritz.
"""

import subprocess

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import ritzlib_build

pytestmark = pytest.mark.integration


def _program(body: str) -> str:
    """A main that imports only the digit routines, then `body`.  A short
    case ends `return 1`: exit 1 shows the call returned, which it must not."""
    return (
        "import ritzlib.fmt.digits\n\n"
        "pub fn main() -> i32\n"
        f"{body}"
    )


def _build_and_run(ritz1_bin, compiler, tmp_path, src, row="main"):
    work = tmp_path / compiler / row
    work.mkdir(parents=True)
    (work / "main.ritz").write_text(src)
    ok, output, exe = ritzlib_build(ritz1_bin)(compiler, work / "main.ritz", work)
    assert ok, f"{compiler} failed to build:\n{output[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60, check=False)


# name -> (main's body, the message).  Each span is one byte short, and the
# value is small: the check is the span's length, not the digits'.
SHORT = {
    "i64": ("""\
    var buf: [19]u8
    let d: StrView = fmt_i64_into(@buf, 7)
    return 1
""", b"fmt_i64_into: buffer shorter than 20 bytes"),
    "u64": ("""\
    var buf: [19]u8
    let d: StrView = fmt_u64_into(@buf, 7)
    return 1
""", b"fmt_u64_into: buffer shorter than 20 bytes"),
    "hex": ("""\
    var buf: [15]u8
    let d: StrView = fmt_u64_hex_into(@buf, 7)
    return 1
""", b"fmt_u64_hex_into: buffer shorter than 16 bytes"),
    "radix": ("""\
    var buf: [63]u8
    let d: StrView = fmt_u64_radix_into(@buf, 7, 2, false)
    return 1
""", b"fmt_u64_radix_into: buffer shorter than 64 bytes"),
    # A span cut from a bigger array: the bytes past it are the caller's.
    "subspan": ("""\
    var big: [40]u8
    let part: [u8] = Span<u8> { ptr: @big[0], len: 4 }
    let d: StrView = fmt_i64_into(part, -1)
    return 1
""", b"fmt_i64_into: buffer shorter than 20 bytes"),
    "radix_out_of_range": ("""\
    var buf: [64]u8
    let d: StrView = fmt_u64_radix_into(@buf, 7, 17, false)
    return 1
""", b"fmt_u64_radix_into: radix outside 2..16"),
}


# One test per compiler iterating SHORT's rows, not a parametrised matrix (the
# ritz0 suite's case cap, tools/test_budget.toml).  A trap ends its binary, so
# every row is still its own build and run; a failure names each row it hits.
@pytest.mark.parametrize("compiler", COMPILERS)
def test_short_span_traps(ritz1_bin, tmp_path, compiler):
    wrong = []
    for case in sorted(SHORT):
        body, message = SHORT[case]
        run = _build_and_run(ritz1_bin, compiler, tmp_path, _program(body), case)
        if run.returncode != 101 or message not in run.stderr:
            wrong.append(f"{case}: exit {run.returncode}, stderr {run.stderr!r}, wanted 101 and {message!r}")
    assert not wrong, "\n".join(wrong)


# The exact sizes are enough, at each routine's widest value.
EXACT = """\
    var dec: [20]u8
    if not fmt_i64_into(@dec, 0 - 9223372036854775807 - 1).eq("-9223372036854775808")
        return 1
    if not fmt_u64_into(@dec, 0 -% (1 as u64)).eq("18446744073709551615")
        return 2
    var hex: [16]u8
    if not fmt_u64_hex_into(@hex, 0 -% (1 as u64)).eq("ffffffffffffffff")
        return 3
    var bin: [64]u8
    if fmt_u64_radix_into(@bin, 0 -% (1 as u64), 2, false).len != 64
        return 4
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_exact_sizes_hold_the_widest_value(ritz1_bin, tmp_path, compiler):
    src = "import ritzlib.strview\n" + _program(EXACT)
    run = _build_and_run(ritz1_bin, compiler, tmp_path, src)
    assert run.returncode == 0, (run.returncode, run.stderr)
