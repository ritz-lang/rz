"""A hosted program that imports only ritzlib's core still links (AGAST #4119).

ritzlib's core (tools/ritzlib_layers.py) no longer imports ritzlib.sys:
memory gets its default pages, and hashmap ends the program on a missing key,
through `extern fn ritz_platform_*` hooks.  ritzlib.sys defines them, but a
program that imports only core modules never links sys.  Every hosted
`_start` therefore carries weak Linux definitions of them, as it does
`__ritz_envp`: runtime/ritz_start*.ll, the `_start` ritz0 embeds, and the one
ritz1 emits for a test binary.  sys's strong definitions win when it is linked.

The program imports only ritzlib.hashmap, allocates (the page hook) and reads
a missing key (the fatal hook): it must exit 101 with hashmap's message on
stderr.  Each compiler links it with the core modules' objects and no sys: ritz0
against its embedded `_start`, ritz1 against runtime/ritz_start.x86_64.o.  ritz1's test-binary `_start` is run by
`rz test ritz/ritzlib/tests --compiler ritz1` (test_strview.ritz and others
import no hosted module).
"""

import subprocess
from pathlib import Path

import pytest

import fast_link
from test_ritz1_for_header import RITZ_START, _emit, library_objects
from test_table_rows import _closure

pytestmark = pytest.mark.integration

PROGRAM = """\
import ritzlib.hashmap

fn main() -> i32
    var m: HashMapI64 = hashmap_i64_new()
    m[1] = 10
    let v: i64 = m[-42]
    0
"""

MESSAGE = b"HashMapI64: key not found: -42\n"


@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_core_only_program_links_and_runs(ritz1_bin, ritz_start, tmp_path, compiler):
    units = _closure(("hashmap",))
    assert "sys" not in units, units
    src, ll, exe = tmp_path / "main.ritz", tmp_path / "main.ll", tmp_path / "main"
    src.write_text(PROGRAM)
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
    assert (run.returncode, run.stderr) == (101, MESSAGE)
