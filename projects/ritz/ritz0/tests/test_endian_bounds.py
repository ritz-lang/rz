"""ritzlib.endian refuses an offset whose bytes do not fit the span (AGAST #4644).

endian's reads and writes took a raw `*u8` with no length, so a 2/4/8-byte
access past the end of a buffer was a silent overread or overwrite -- in
cryptosec's and valet's parsers of untrusted input, among others.  They now
take a `Span<u8>` and an offset, and an access that does not fit the span ends
the program with status 101 and a message naming the offset, width and length,
as hashmap's missing key does (through the `ritz_platform_fatal` hook, so a
freestanding harland build stops through its own).

The in-range behaviour is ritzlib/tests/test_endian.ritz; an exit cannot be a
[[test]] result, so the refusal is pinned here, per compiler.  One row reads
one byte past the end and one writes at a negative offset: the check is
`0 <= off` and `off + n <= len`, and each half has a row.
"""

import subprocess

import pytest

import fast_link
from test_ritz1_for_header import RITZ_START, _emit, library_objects
from test_table_rows import _closure

pytestmark = pytest.mark.integration

PROGRAM = """\
import ritzlib.span
import ritzlib.endian

fn main() -> i32
    var b: [8]u8 = [1, 2, 3, 4, 5, 6, 7, 8]
    {body}
    0
"""

CASES = {
    # A u32 at offset 5 of 8 bytes needs bytes 5..9: one past the end.
    "read_past_end": ("let v: u32 = endian_read_u32_le(@b, 5)",
                      b"endian: 4 bytes at offset 5 overrun a span of 8\n"),
    "write_negative": ("endian_write_u16_be(@b, -1, 0x1234)",
                       b"endian: 2 bytes at offset -1 overrun a span of 8\n"),
}


@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("case", sorted(CASES))
def test_out_of_range_offset_exits_101(ritz1_bin, ritz_start, tmp_path, compiler, case):
    body, message = CASES[case]
    units = _closure(("span", "endian"))
    src, ll, exe = tmp_path / "main.ritz", tmp_path / "main.ll", tmp_path / "main"
    src.write_text(PROGRAM.format(body=body))
    comp = _emit(compiler, ritz1_bin, src, ll)
    assert comp.returncode == 0, comp.stdout[-2000:] + comp.stderr[-2000:]
    # ritz0 embeds its own `_start`; ritz1 links the runtime's.
    start = [] if compiler == "ritz0" else [str(RITZ_START)]
    link = fast_link.clang(["clang", "-w", str(ll), *start,
                            *library_objects(compiler, ritz1_bin, units),
                            "-o", str(exe), "-nostdlib"],
                           cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-2000:]
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    assert (run.returncode, run.stderr) == (101, message)
