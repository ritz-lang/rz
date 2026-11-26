"""AGAST #4454: ritz1's driver I/O -- what a compile reads, writes and says.

Three contracts of the `ritz1 src -o out.ll` driver, on both ritz1 binaries
(ritz0 is the Python bootstrap; its I/O is Python's):

* A successful compile writes NOTHING to stderr.  The `[MONOMORPH]` debug
  prints that once went there are gone (#1820); this pins that no other
  chatter takes their place, so a clean build log stays clean.
* The output is written whole or the compile fails.  `write_output_file` used to
  issue one `sys_write` and ignore what it returned: a full disk
  (`/dev/full`, ENOSPC) or a file-size limit that cut the write short left
  a missing or truncated `.ll` behind an exit code of 0.
* A source bigger than the read chunk compiles: `read_source_file` appends whole
  chunks (`push_bytes`), not one `push` per byte.  The source check pins
  the per-byte loop gone; the large-source compile pins the chunking right.
"""

import os
import re
import resource
import signal
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parents[2]
SRC = RITZ_ROOT / "ritz1" / "src"
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
COMPILERS = ["ritz1", "ritz1_selfhosted"]

# Imports, a generic instantiation and a method call: the parse, import,
# monomorph and emit stages all run, so any of them printing would show.
PROGRAM = """\
import ritzlib.gvec

fn total(v: @Vec<i32>) -> i32
    var s: i32 = 0
    for i in 0..v.len()
        s += v.get(i)
    s

pub fn main() -> i32
    var v: Vec<i32> = vec_new<i32>()
    v.push(40)
    v.push(2)
    total(@v)
"""


@pytest.fixture
def compiler_bin(request, ritz1_bin, ritz1_selfhosted) -> Path:
    return {"ritz1": ritz1_bin, "ritz1_selfhosted": ritz1_selfhosted}[request.param]


def _compile(binary: Path, src: Path, out: str, preexec=None):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [str(binary), str(src), "-o", out, "-I", str(RITZ_ROOT)],
        cwd=RITZ_ROOT, env=env, capture_output=True, timeout=300,
        preexec_fn=preexec,
    )


@pytest.mark.integration
@pytest.mark.parametrize("compiler_bin", COMPILERS, indirect=True)
def test_successful_compile_writes_no_stderr(compiler_bin, tmp_path):
    src = tmp_path / "main.ritz"
    src.write_text(PROGRAM)
    out = tmp_path / "main.ll"
    proc = _compile(compiler_bin, src, str(out))
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    assert out.stat().st_size > 0
    assert proc.stderr == b"", proc.stderr.decode(errors="replace")


@pytest.mark.integration
@pytest.mark.parametrize("compiler_bin", COMPILERS, indirect=True)
def test_full_disk_fails_the_compile(compiler_bin, tmp_path):
    src = tmp_path / "main.ritz"
    src.write_text(PROGRAM)
    proc = _compile(compiler_bin, src, "/dev/full")
    assert proc.returncode != 0
    assert b"/dev/full" in proc.stderr, proc.stderr.decode(errors="replace")


def _cap_file_size():
    # The kernel cuts a write that crosses RLIMIT_FSIZE short at the limit
    # and fails the next one with EFBIG; SIGXFSZ is ignored so it is an
    # error return, not a kill.  The IR is far bigger than 4 KiB.
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (4096, 4096))


@pytest.mark.integration
@pytest.mark.parametrize("compiler_bin", COMPILERS, indirect=True)
def test_short_write_is_not_success(compiler_bin, tmp_path):
    src = tmp_path / "main.ritz"
    src.write_text(PROGRAM)
    out = tmp_path / "main.ll"
    proc = _compile(compiler_bin, src, str(out), preexec=_cap_file_size)
    assert proc.returncode != 0, f"truncated {out.stat().st_size}-byte .ll reported as success"
    assert str(out).encode() in proc.stderr, proc.stderr.decode(errors="replace")


@pytest.mark.integration
@pytest.mark.parametrize("compiler_bin", COMPILERS, indirect=True)
def test_source_larger_than_a_chunk_compiles(compiler_bin, tmp_path):
    # ~40 KiB of comment between main and the fn it calls: the fn's text
    # arrives in a later read chunk than main's.
    pad = "".join(f"# padding line {i:05d} .........................\n" for i in range(800))
    src = tmp_path / "main.ritz"
    src.write_text(
        "pub fn main() -> i32\n    after_the_padding()\n\n" + pad
        + "fn after_the_padding() -> i32\n    42\n")
    assert src.stat().st_size > 32768
    out = tmp_path / "main.ll"
    proc = _compile(compiler_bin, src, str(out))
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    assert "after_the_padding" in out.read_text()


def _fn_body(text: str, name: str) -> str:
    m = re.search(rf"^fn {name}\(.*?(?=^\S)", text, re.MULTILINE | re.DOTALL)
    assert m, f"fn {name} not found"
    return m.group(0)


@pytest.mark.unit
@pytest.mark.parametrize("path,fn", [
    ("main.ritz", "read_source_file"),
    ("no_effect.ritz", "ne_read_file"),
])
def test_read_helpers_append_whole_chunks(path, fn):
    """No `buf.push(chunk[i])` per byte: a read appends its chunk at once."""
    body = _fn_body((SRC / path).read_text(), fn)
    assert "push_bytes(" in body, body
    assert not re.search(r"\.push\(chunk\[", body), body


@pytest.mark.unit
def test_sig_writer_escapes_with_ritzlib_json():
    """fn_cache writes sig strings with ritzlib.json, hex hashes in one place.

    It carried its own JSON string escaper (a copy of json_emit_bytes that
    wrote \\b and \\f as \\u00XX) and the 16-digit hex push loop twice."""
    text = (SRC / "fn_cache.ritz").read_text()
    assert "fn emit_json_string_bytes" not in text
    assert "json_emit_bytes(" in text
    assert len(re.findall(r"while k < 16", text)) <= 1, "hex16 push loop copied"
