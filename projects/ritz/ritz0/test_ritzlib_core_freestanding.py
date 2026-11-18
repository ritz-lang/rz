"""ritzlib's core compiles for a freestanding target (AGAST #4119).

ritzlib.memory took its default pages from ritzlib.sys (sys_mmap_anon), and
gvec and hashmap imported sys too, so the whole core dragged the syscall layer
in and a target with no syscalls (the Harland kernel) could not use it.  The
core (tools/ritzlib_layers.py CORE) now reaches the platform only through
three `extern fn` hooks, which ritzlib.sys defines for a hosted program.

One program, compiled as harland's kernel is (`--target x86_64-none-elf
--no-runtime`), imports every core module, uses the allocator, Vec, String
and HashMapI64's missing-key path, and defines the hooks itself, as a kernel
does.  It must compile, its import closure must be core only, and its IR must
hold no `syscall`.
"""

import os
import sys
from pathlib import Path

import pytest

from import_resolver import collect_all_source_files

pytestmark = pytest.mark.integration   # runs ritz0 once

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
RITZLIB = RITZ_ROOT / "ritzlib"

sys.path.insert(0, str(RITZ_ROOT / "tools"))
from ritzlib_layers import CORE  # noqa: E402

KERNEL = "\n".join(f"import ritzlib.{m}" for m in sorted(CORE)) + """

var g_pool: [65536]u8
var g_next: i64 = 0

# The hooks a hosted program gets from ritzlib.sys: here a bump allocator over
# a static pool, as a kernel's frame allocator would be.
pub fn ritz_platform_page_map(len: i64) -> *u8
    if g_next + len > 65536
        return null
    let p: *u8 = @g_pool[g_next]
    g_next += len
    return p

pub fn ritz_platform_page_unmap(p: *u8, len: i64) -> i32
    return 0

pub fn ritz_platform_fatal(msg: *u8, len: i64, status: i32)
    loop
        g_next = g_next

pub fn kmain() -> i32
    let p: *u8 = malloc(64)
    var v: Vec<i64> = vec_new<i64>()
    vec_push(@&v, 7)
    var m: HashMapI64 = hashmap_i64_new()
    hashmap_i64_insert(@&m, 1, 2)
    let s: String = string_from("core")
    free(p)
    return (m[1] + vec_get(@v, 0) + string_len(@s)) as i32
"""


def test_core_compiles_freestanding_without_sys(tmp_path, run_ritz0, monkeypatch):
    monkeypatch.setenv("RITZ_PATH", str(RITZ_ROOT))
    src = tmp_path / "kernel.ritz"
    src.write_text(KERNEL)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))

    closure = {Path(f).resolve() for f in collect_all_source_files(str(src))}
    hosted = sorted(str(f.relative_to(RITZLIB)) for f in closure
                    if f.is_relative_to(RITZLIB)
                    and f.relative_to(RITZLIB).with_suffix("").as_posix().replace("/", ".")
                    not in CORE)
    assert hosted == [], f"core reaches hosted ritzlib modules: {hosted}"

    out = tmp_path / "kernel.ll"
    proc = run_ritz0([src, "-o", out, "--no-runtime", "--target", "x86_64-none-elf"],
                     cwd=RITZ0_DIR, env=env, timeout=300)
    assert proc.returncode == 0 and out.exists(), proc.stdout + proc.stderr
    ir = out.read_text()
    assert "syscall" not in ir, "freestanding core IR issues a syscall"
    assert "define" in ir and "ritz_platform_page_map" in ir
