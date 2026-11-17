"""Harland's initramfs survives big archives, file-before-directory TARs and flaky reads (AGAST #2754, from #1844).

The kernel's blob store (fs/kblob.ritz) had a fixed 256-slot table and a
"TODO: Grow array if no free slot": once full, kblob_store_put returned the
zero id, knamespace_write answered NoSpc and initramfs.ritz quietly skipped the
file. Every file write puts the file plus a fresh snapshot of each directory on
its path, so ~85 files were enough to lose the rest of the archive.
initramfs.ritz also dropped a file whose directory had no TAR entry yet (NoEnt)
and failed the boot on a single transient virtio read error.

origin/harland-main fixed these in abc28b2a (read retries, parent dirs created
on demand), 8e7b4c82 (store growth) and 0eda5329 (default capacity 4096).

Both tests compile the real kernel modules into host programs (ritz0, as the
kernel build does) with stand-ins for serial, io, the kernel heap (an arena)
and, for initramfs, the virtio-blk driver: it serves a TAR this test writes and
fails every 4th read once. Exit codes name the failed claim. The boot-level
check is projects/harland/tools/test_tier1_boot.sh.
"""

import io
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
KERNEL_SRC = RITZ_ROOT.parent / "harland" / "kernel" / "src"

# --- stand-ins ----------------------------------------------------------------

SERIAL_STUB = """\
pub struct StrView
    ptr: *u8
    len: i64

pub fn prints(s: StrView) -> i32
    return 0

pub fn println(s: StrView) -> i32
    return 0

pub fn serial_print_dec(value: u64) -> i32
    return 0

pub fn serial_print_hex(value: u64) -> i32
    return 0
"""

# initramfs_load "panics" through halt_loop; here it returns so the test sees
# the error code.
IO_STUB = """\
pub fn halt_loop() -> i32
    return 0
"""

# A 32 MB bump arena: kblob never frees blob data, and every directory
# snapshot is a copy.
HEAP_STUB = """\
var g_arena: [33554432]u8
var g_top: u64 = 0

pub fn kalloc(size: u64) -> *u8
    let n: u64 = (size + 15) & 18446744073709551600
    if g_top + n > 33554432
        return 0 as *u8
    let p: *u8 = @g_arena[0] + g_top
    g_top = g_top + n
    p

pub fn kfree(ptr: *u8) -> i32
    0

pub fn heap_get_free() -> u64
    33554432 - g_top

pub fn heap_check() -> i32
    0
"""

# Serves sectors of the disk image blk_stub_set gave it; every 4th read fails
# (once: the retry is the next call).
BLK_STUB = """\
pub struct VirtioBlkDevice
    id: i32

var g_dev: VirtioBlkDevice
var g_disk: *u8
var g_disk_len: u64 = 0
var g_calls: i32 = 0
var g_injected: i32 = 0

pub fn blk_stub_set(disk: *u8, len: u64)
    g_disk = disk
    g_disk_len = len

pub fn blk_stub_injected() -> i32
    g_injected

pub fn virtio_blk_get_device() -> *VirtioBlkDevice
    @g_dev

pub fn virtio_blk_read(dev: *VirtioBlkDevice, sector: u64, count: u32, buf: *u8) -> i32
    g_calls = g_calls + 1
    if g_calls % 4 == 0
        g_injected = g_injected + 1
        return -5
    let start: u64 = sector * 512
    let n: u64 = count as u64 * 512
    var i: u64 = 0
    while i < n
        if start + i < g_disk_len
            *(buf + i) = *(g_disk + start + i)
        else
            *(buf + i) = 0
        i = i + 1
    0
"""

STUBS = {
    "serial.ritz": SERIAL_STUB,
    "io.ritz": IO_STUB,
    "mm/heap.ritz": HEAP_STUB,
    "drivers/virtio/blk.ritz": BLK_STUB,
}
REAL = ["lib/sha256.ritz", "fs/kblob.ritz", "fs/knamespace.ritz", "fs/kdir_entry.ritz",
        "fs/kpath.ritz", "fs/tar.ritz", "fs/initramfs.ritz", "syscall/errno.ritz"]


def _compile(tmp_path, path, name, extra=()):
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    proc = run_ritz0([str(path), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
    return ll


def _run(tmp_path, src, modules, libs=()):
    """Compile `src`, each module of the stub tree and each ritzlib `libs` file (own object each), link, run in tmp_path."""
    tree = tmp_path / "tree"
    sources = dict(STUBS)
    for rel in REAL:
        sources[rel] = (KERNEL_SRC / rel).read_text()
    for rel, text in sources.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(text)
    objs = [str(_compile(tmp_path, tree / rel, rel[:-5].replace("/", "_"), ("--no-runtime",)))
            for rel in modules]
    objs += [str(_compile(tmp_path, RITZ_ROOT / rel, rel[:-5].replace("/", "_"), ("--no-runtime",)))
             for rel in libs]
    (tmp_path / "t.ritz").write_text(src)
    objs.insert(0, str(_compile(tmp_path, tmp_path / "t.ritz", "t")))
    exe = tmp_path / "t"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], cwd=tmp_path, capture_output=True, timeout=120).returncode


# --- kblob growth ------------------------------------------------------------------

# 4200 distinct 8-byte blobs: past the default 4096 slots. Every id still
# resolves to its own bytes, and dedup still holds after the store grew.
KBLOB_GROW = """\
import fs.kblob { KBlobStore, KBlobId, kblob_store_new, kblob_store_put, kblob_store_get, kblob_store_get_size, kblob_id_is_zero }

const N: i32 = 4200
var g_ids: [4200]KBlobId

fn main() -> i32
    var store: KBlobStore = kblob_store_new()
    if store.capacity != 4096
        return 1
    var v: u64 = 0
    var i: i32 = 0
    while i < N
        v = i as u64 + 1000
        g_ids[i] = kblob_store_put(@store, @v as *u8, 8)
        if kblob_id_is_zero(@g_ids[i])
            return 2
        i = i + 1
    if store.count != N
        return 3
    if store.capacity < N
        return 4
    i = 0
    while i < N
        let p: *u64 = kblob_store_get(@store, @g_ids[i]) as *u64
        if p == 0 as *u64 or kblob_store_get_size(@store, @g_ids[i]) != 8 or *p != i as u64 + 1000
            return 5
        i = i + 1
    v = 1007
    kblob_store_put(@store, @v as *u8, 8)
    if store.count != N
        return 6
    0
"""

KBLOB_CLAIMS = {1: "default capacity is 4096", 2: "put past capacity grows instead of failing",
                3: "count", 4: "capacity grew", 5: "every id still resolves to its bytes",
                6: "dedup after growth"}


@pytest.mark.integration
def test_kblob_store_grows_past_default_capacity(tmp_path):
    rc = _run(tmp_path, KBLOB_GROW, ["serial.ritz", "mm/heap.ritz", "lib/sha256.ritz", "fs/kblob.ritz"])
    assert rc == 0, f"kblob claim failed: {KBLOB_CLAIMS.get(rc, f'exit {rc}')}"


# --- initramfs load ------------------------------------------------------------

DIRS = 20
FILES = 15


def _letter(n):
    return chr(ord("a") + n)


def _tar(path):
    """Orphans first (no dir entry, or file before its dir), then DIRS x FILES ordered files.

    Each file's content is its own absolute path.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        def add_file(name):
            data = name[1:].encode()  # "./x/y" -> "/x/y"
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))

        def add_dir(name):
            info = tarfile.TarInfo(name=name)
            info.type = tarfile.DIRTYPE
            tar.addfile(info)

        for f in range(5):
            add_file(f"./late/x/f{_letter(f)}")   # no entry for ./late or ./late/x
        add_file("./post/fa")                    # its dir entry comes after it
        add_dir("./post")
        for d in range(DIRS):
            add_dir(f"./d{_letter(d)}")
            for f in range(FILES):
                add_file(f"./d{_letter(d)}/f{_letter(f)}")
    path.write_bytes(buf.getvalue())


INITRAMFS = f"""\
import ritzlib.sys
import serial {{ StrView }}
import drivers.virtio.blk {{ blk_stub_set, blk_stub_injected }}
import fs.kblob {{ KBlobStore, kblob_init, kblob_get_store }}
import fs.knamespace {{ knamespace_init, knamespace_get, knamespace_read }}
import fs.initramfs {{ initramfs_load }}

var g_image: [4194304]u8

# Does `path` hold its own bytes?
fn holds(path: *u8, len: i64) -> bool
    var size: u64 = 0
    let data: *u8 = knamespace_read(knamespace_get(), StrView {{ ptr: path, len: len }}, @size)
    if data == 0 as *u8 or size != len as u64
        return false
    var i: i64 = 0
    while i < len
        if *(data + i) != *(path + i)
            return false
        i = i + 1
    true

fn main() -> i32
    let fd: i32 = sys_open(c"initramfs.tar", 0)
    if fd < 0
        return 90
    var len: i64 = 0
    while true
        let n: i64 = sys_read(fd, @g_image[0] + len, 4194304 - len)
        if n <= 0
            break
        len = len + n
    sys_close(fd)
    blk_stub_set(@g_image[0], len as u64)

    if kblob_init() != 0
        return 91
    knamespace_init(kblob_get_store())
    if initramfs_load() != 0
        return 1
    if blk_stub_injected() == 0
        return 93

    # files whose directories had no entry (or a later one)
    var late: [16]u8
    var p: *u8 = c"/late/x/fa"
    var i: i64 = 0
    while i < 10
        late[i] = *(p + i)
        i = i + 1
    var f: i32 = 0
    while f < 5
        late[9] = 97 + f as u8
        if not holds(@late[0], 10)
            return 2
        f = f + 1
    if not holds(c"/post/fa", 8)
        return 2

    # every ordered file, well past the old 256-blob store
    var path: [8]u8
    path[0] = 47
    path[1] = 100
    path[3] = 47
    path[4] = 102
    var d: i32 = 0
    while d < {DIRS}
        path[2] = 97 + d as u8
        f = 0
        while f < {FILES}
            path[5] = 97 + f as u8
            if not holds(@path[0], 6)
                return 3
            f = f + 1
        d = d + 1
    if (*kblob_get_store()).count <= 256
        return 92
    0
"""

INITRAMFS_CLAIMS = {1: "load succeeds through transient read errors",
                    2: "a file whose directory has no (or a later) TAR entry is loaded",
                    3: "every file loads once the archive needs more than 256 blobs",
                    90: "test setup: open initramfs.tar", 91: "test setup: kblob_init",
                    93: "test setup: no read error was injected",
                    92: "test setup: archive stayed under 256 blobs"}


@pytest.mark.integration
def test_initramfs_loads_large_unordered_archive_through_read_errors(tmp_path):
    _tar(tmp_path / "initramfs.tar")
    rc = _run(tmp_path, INITRAMFS, ["serial.ritz", "io.ritz", "mm/heap.ritz", "drivers/virtio/blk.ritz",
                                    "lib/sha256.ritz", "fs/kblob.ritz", "fs/knamespace.ritz",
                                    "fs/kdir_entry.ritz", "fs/kpath.ritz", "fs/tar.ritz",
                                    "fs/initramfs.ritz", "syscall/errno.ritz"],
              libs=["ritzlib/sys.ritz"])
    assert rc == 0, f"initramfs claim failed: {INITRAMFS_CLAIMS.get(rc, f'exit {rc}')}"
