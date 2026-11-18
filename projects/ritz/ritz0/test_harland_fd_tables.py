"""Harland gives each process its own fd table and releases it on exit (AGAST #2753, from #1844).

Every process used to share one kernel-wide table: vfs.ritz's kernel_fds and
fs/syscall.ritz's fs_file_state, both [64] and indexed by fd. So a child's
first open got the parent's next fd, only 61 fds (3..63) existed for
everyone, and an fd a child left open stayed taken after it exited.
origin/harland-main (3759515e, ed89529c, 7d8658ec, 242fdc09) added fd.ritz's
FdTable and per-pid contexts, but never released a context, so the next child
(children are always pid 2) inherited the last one's open fds.

Now fs/fd.ritz is the FdTable (256 fds) and fs/syscall.ritz keeps one FsProc
(FdTable + per-fd file state) per live process. syscall/runtime/process.ritz
brackets each process: fs_process_start(pid) when it starts (process_enter_init
for init, spawn)
and fs_process_end() when it exits, which closes what it left open, flushing
writes as sys_close does, and makes the parent's table current again.

The behaviour tests compile the real fs/fd.ritz, fs/syscall.ritz, fs/vfs.ritz,
fs/kpath.ritz and syscall/errno.ritz into host programs on every compiler,
with stand-ins for serial, the kernel heap (an arena that counts live
allocations) and the namespace/blob store (a few named files; writes are
recorded). Exit codes name the failed claim. Source-level tests pin where the
process layer calls into fs. The boot-level checks are indium's
fd_table_test, fd_isolation_child (driven by init) and pid_child_test, run
by projects/harland/tools/test_tier1_boot.sh.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
PROJECTS = RITZ_ROOT.parent
HARLAND = PROJECTS / "harland"
INDIUM = PROJECTS / "indium"
KERNEL_SRC = HARLAND / "kernel" / "src"

# The kernel is built by ritz0 (build.py --no-runtime): these rows pin kernel
# behaviour, so another compiler adds no rule of its own (TESTING.md, "What a
# ritz0 pytest case costs").
COMPILERS = ["ritz0"]

# --- stand-ins ----------------------------------------------------------------

# The real serial.ritz drives the UART through port I/O (and doesn't parse on
# ritz1); these have its signatures and do nothing.
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

# kalloc/kfree from an arena; heap_live() counts allocations not yet freed,
# so a test can see that a process's FsProc, path copies and write buffers
# all go back.
HEAP_STUB = """\
var g_arena: [8388608]u8
var g_top: u64 = 0
var g_live: i64 = 0

pub fn kalloc(size: u64) -> *u8
    let n: u64 = (size + 15) & 18446744073709551600
    if g_top + n > 8388608
        return 0 as *u8
    let p: *u8 = @g_arena[0] + g_top
    g_top = g_top + n
    g_live = g_live + 1
    p

pub fn kfree(ptr: *u8) -> i32
    g_live = g_live - 1
    0

pub fn heap_live() -> i64
    g_live
"""

# Blob n (1-based) is file n's bytes; its id is hash[0] = n.
KBLOB_STUB = """\
pub struct KBlobId
    hash: [32]u8

pub struct KBlobStore
    count: i32

var g_store: KBlobStore
var g_data: [8][64]u8
var g_size: [8]u64

pub fn kblob_get_store() -> *KBlobStore
    @g_store

pub fn kblob_id_is_zero(id: *KBlobId) -> bool
    var i: i32 = 0
    while i < 32
        if (*id).hash[i] != 0
            return false
        i = i + 1
    true

pub fn kblob_id_copy(src: *KBlobId) -> KBlobId
    var dst: KBlobId
    var i: i32 = 0
    while i < 32
        dst.hash[i] = (*src).hash[i]
        i = i + 1
    dst

pub fn kblob_store_get(store: *KBlobStore, id: *KBlobId) -> *u8
    let n: i32 = (*id).hash[0] as i32
    @g_data[n][0]

pub fn kblob_store_get_size(store: *KBlobStore, id: *KBlobId) -> u64
    g_size[(*id).hash[0] as i32]

pub fn kblob_stub_set(n: i32, data: *u8, size: u64)
    var i: u64 = 0
    while i < size and i < 64
        g_data[n][i as i32] = *(data + i)
        i = i + 1
    g_size[n] = size
"""

# Files by path: /a = "alpha", /b = "bravo"; knamespace_write creates or
# replaces one and is counted, so a flush is observable.
KNAMESPACE_STUB = """\
import serial { StrView }
import fs.kblob { KBlobId, kblob_stub_set, kblob_store_get, kblob_get_store }

pub struct KNamespace
    count: i32

var g_ns: KNamespace
var g_paths: [8][16]u8
var g_lens: [8]i64
var g_files: i32 = 0
var g_writes: i32 = 0

fn find(path: StrView) -> i32
    var n: i32 = 1
    while n <= g_files
        if g_lens[n] == path.len
            var same: bool = true
            var i: i64 = 0
            while i < path.len
                if g_paths[n][i as i32] != *(path.ptr + i)
                    same = false
                i = i + 1
            if same
                return n
        n = n + 1
    0

fn add(name: *u8, len: i64, data: *u8, size: u64) -> i32
    g_files = g_files + 1
    var i: i64 = 0
    while i < len
        g_paths[g_files][i as i32] = *(name + i)
        i = i + 1
    g_lens[g_files] = len
    kblob_stub_set(g_files, data, size)
    g_files

pub fn knamespace_get() -> *KNamespace
    if g_files == 0
        add(c"/a", 2, c"alpha", 5)
        add(c"/b", 2, c"bravo", 5)
    @g_ns

pub fn knamespace_resolve(ns: *KNamespace, path: StrView) -> KBlobId
    var id: KBlobId
    var i: i32 = 0
    while i < 32
        id.hash[i] = 0
        i = i + 1
    id.hash[0] = find(path) as u8
    id

pub fn knamespace_write(ns: *KNamespace, path: StrView, data: *u8, size: u64) -> i32
    let n: i32 = find(path)
    if n == 0
        add(path.ptr, path.len, data, size)
    else
        kblob_stub_set(n, data, size)
    if size > 0
        g_writes = g_writes + 1
    0

pub fn knamespace_read(ns: *KNamespace, path: StrView, out_size: *u64) -> *u8
    0 as *u8

pub fn knamespace_exists(ns: *KNamespace, path: StrView) -> bool
    find(path) != 0

pub fn knamespace_mkdir(ns: *KNamespace, path: StrView) -> i32
    0

# Writes that carried data, and whether `path` now holds `want`.
pub fn stub_writes() -> i32
    g_writes

pub fn stub_holds(path: *u8, plen: i64, want: *u8, wlen: u64) -> bool
    let p: StrView = StrView { ptr: path, len: plen }
    var id: KBlobId = knamespace_resolve(@g_ns, p)
    if id.hash[0] == 0
        return false
    let data: *u8 = kblob_store_get(kblob_get_store(), @id)
    var i: u64 = 0
    while i < wlen
        if *(want + i) != *(data + i)
            return false
        i = i + 1
    true
"""

STUBS = {
    "serial.ritz": SERIAL_STUB,
    "mm/heap.ritz": HEAP_STUB,
    "fs/kblob.ritz": KBLOB_STUB,
    "fs/knamespace.ritz": KNAMESPACE_STUB,
}
REAL = ["fs/fd.ritz", "fs/syscall.ritz", "fs/vfs.ritz", "fs/kpath.ritz", "syscall/errno.ritz"]


def _compile(compiler, tmp_path, path, name, extra=()):
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        proc = run_ritz0([str(path), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0 and ll.exists(), \
        f"{compiler} rejected {name}:\n{proc.stdout}{proc.stderr}"
    return ll


def _run(compiler, tmp_path, src, modules):
    """Compile `src` and each module of the stub tree (own object each), link, run."""
    tree = tmp_path / "tree"
    sources = dict(STUBS)
    for rel in REAL:
        sources[rel] = (KERNEL_SRC / rel).read_text()
    for rel, text in sources.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(text)
    extra = ("--no-runtime",) if compiler == "ritz0" else ()
    # Each module compiles from its place in the tree, so its imports resolve
    # to the tree's siblings (ritz1 looks next to the importing file first).
    objs = [str(_compile(compiler, tmp_path, tree / rel, rel[:-5].replace("/", "_"), extra))
            for rel in modules]
    (tmp_path / "t.ritz").write_text(src)
    objs.insert(0, str(_compile(compiler, tmp_path, tmp_path / "t.ritz", "t")))
    if compiler != "ritz0":
        objs.insert(0, str(RITZ_START))
    exe = tmp_path / f"t_{compiler}"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


FD_MODULES = ["fs/fd.ritz", "syscall/errno.ritz"]
FS_MODULES = ["serial.ritz", "mm/heap.ritz", "fs/kblob.ritz", "fs/knamespace.ritz",
              "fs/fd.ritz", "fs/syscall.ritz", "fs/vfs.ritz", "fs/kpath.ritz",
              "syscall/errno.ritz"]

# --- FdTable (fs/fd.ritz) ---------------------------------------------------------

FDTABLE = """\
import ritzlib.option
import syscall.errno { Errno }
import fs.fd

var g_t: FdTable

fn main() -> i32
    let t: *FdTable = @g_t
    if fd_table_init(t) != 0 or fd_count_open(t) != 0
        return 1
    # stdin/stdout/stderr are in use and can't be freed
    if fd_get(t, 0) == 0 as *FileDescriptor or fd_get(t, 2) == 0 as *FileDescriptor
        return 2
    if fd_free(t, 1) != Errno.BadF as i32
        return 3
    # 3..255: MAX_FDS per table, then Errno.NFile
    if MAX_FDS != 256
        return 4
    var want: i32 = 3
    while want < 256
        if fd_alloc(t) != want
            return 5
        want = want + 1
    if fd_alloc(t) != Errno.NFile as i32
        return 6
    # the lowest freed fd comes back
    if fd_free(t, 10) != 0 or fd_free(t, 7) != 0
        return 7
    if fd_free(t, 7) != Errno.BadF as i32 or fd_get(t, 7) != 0 as *FileDescriptor
        return 8
    if fd_alloc(t) != 7 or fd_alloc(t) != 10
        return 9
    # a dup shares the open file and keeps it alive after the original closes
    if fd_free(t, 3) != 0
        return 10
    let d: i32 = fd_dup(t, 4)
    if d != 3 or fd_get(t, d) != fd_get(t, 4)
        return 11
    if fd_free(t, 4) != 0 or fd_get(t, d) == 0 as *FileDescriptor or fd_get(t, 4) != 0 as *FileDescriptor
        return 12
    if fd_free(t, d) != 0 or fd_get(t, d) != 0 as *FileDescriptor
        return 13
    if fd_count_open(t) != 251
        return 14
    0
"""

FDTABLE_CLAIMS = {1: "init", 2: "stdio reserved", 3: "stdio unfreeable", 4: "MAX_FDS is 256",
                  5: "alloc order 3..255", 6: "full table -> NFile", 7: "free", 8: "double free -> BadF",
                  9: "lowest freed fd reused", 10: "free 3", 11: "dup shares the file",
                  12: "dup outlives the original", 13: "last ref frees", 14: "open count"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_fd_table_alloc_free_reuse_dup(compiler, tmp_path):
    rc = _run(compiler, tmp_path, FDTABLE, FD_MODULES)
    assert rc == 0, f"{compiler}: FdTable claim failed: {FDTABLE_CLAIMS.get(rc, f'exit {rc}')}"


# --- per-process tables (fs/syscall.ritz) -----------------------------------------

FS_PRELUDE = """\
import ritzlib.option
import syscall.errno { Errno }
import fs.syscall
import fs.vfs { O_RDONLY, O_WRONLY, O_CREAT }
import mm.heap { heap_live }
import fs.knamespace { stub_writes, stub_holds }

fn reads(fd: i32, want: *u8, n: u64) -> bool
    var buf: [16]u8
    if sys_fs_read(fd, @buf[0], n) != n as i64
        return false
    var i: u64 = 0
    while i < n
        if buf[i as i32] != *(want + i)
            return false
        i = i + 1
    true

"""

# init opens /a (fd 3) and spawns a child; the child's first open is also
# fd 3 and reads its own file. It leaves /b and a written /w open and exits:
# both are closed, /w's write is flushed, and init is current again with its
# fd 3 intact and fd 4 free. Nothing stays allocated once init exits.
ISOLATION = FS_PRELUDE + """\
fn main() -> i32
    let base: i64 = heap_live()
    if fs_process_start(1) != 0
        return 1
    if sys_open(c"/a", 2, O_RDONLY) != 3
        return 2
    if fs_process_start(2) != 0 or fs_process_pid() != 2
        return 3
    if sys_open(c"/b", 2, O_RDONLY) != 3
        return 4
    if not reads(3, c"bravo", 5)
        return 5
    if sys_open(c"/w", 2, O_WRONLY | O_CREAT) != 4 or sys_fs_write(4, c"hello", 5) != 5
        return 6
    let writes: i32 = stub_writes()
    if fs_process_end() != 2
        return 7
    if fs_process_pid() != 1
        return 8
    if stub_writes() != writes + 1 or not stub_holds(c"/w", 2, c"hello", 5)
        return 9
    if not reads(3, c"alpha", 5)
        return 10
    if is_fs_fd(4) or sys_close(4) != Errno.BadF as i64
        return 11
    if sys_open(c"/b", 2, O_RDONLY) != 4
        return 12
    if fs_process_end() != 2 or fs_process_pid() != 0 or fs_process_count() != 0
        return 13
    if heap_live() != base
        return 14
    0
"""

ISOLATION_CLAIMS = {1: "init gets a table", 2: "init's first fd is 3", 3: "child gets a table",
                    4: "child's first fd is 3 (own table)", 5: "child's fd 3 is its own file",
                    6: "child opens and writes /w", 7: "exit closes the child's 2 fds",
                    8: "exit makes the parent current", 9: "exit flushes the child's write",
                    10: "parent's fd 3 still reads its own file",
                    11: "child's fd 4 did not survive in the parent",
                    12: "parent's next fd is 4", 13: "init exit releases its table",
                    14: "FsProcs/paths/write buffers freed"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_child_has_own_fd_table_released_on_exit(compiler, tmp_path):
    rc = _run(compiler, tmp_path, ISOLATION, FS_MODULES)
    assert rc == 0, f"{compiler}: {ISOLATION_CLAIMS.get(rc, f'exit {rc}')}"


# More children than FS_MAX_PROCS, one after another, each leaving an fd open:
# every one starts with fd 3 free, because exit gave the last one's table back.
SEQUENTIAL = FS_PRELUDE + """\
fn main() -> i32
    if fs_process_start(1) != 0
        return 1
    let base: i64 = heap_live()
    var i: i32 = 0
    while i < 3 * FS_MAX_PROCS
        if fs_process_start(2) != 0
            return 2
        if sys_open(c"/a", 2, O_RDONLY) != 3
            return 3
        if fs_process_end() != 1
            return 4
        i = i + 1
    if fs_process_count() != 1 or fs_process_pid() != 1
        return 5
    if heap_live() != base
        return 6
    0
"""

SEQUENTIAL_CLAIMS = {1: "init gets a table", 2: "a table slot is free for the next child",
                     3: "the next child's first fd is 3", 4: "exit closes the leaked fd",
                     5: "only init's table is left", 6: "each child's table is freed"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_exited_childrens_tables_are_reused(compiler, tmp_path):
    rc = _run(compiler, tmp_path, SEQUENTIAL, FS_MODULES)
    assert rc == 0, f"{compiler}: {SEQUENTIAL_CLAIMS.get(rc, f'exit {rc}')}"


# 253 fds open at once in one process (the old shared table had 61), then
# Errno.NFile; closing them all frees fd 3 again.
CAPACITY = FS_PRELUDE + """\
fn main() -> i32
    if fs_process_start(1) != 0
        return 1
    var want: i64 = 3
    while want < 256
        if sys_open(c"/a", 2, O_RDONLY) != want
            return 2
        want = want + 1
    if sys_open(c"/a", 2, O_RDONLY) != Errno.NFile as i64
        return 3
    var fd: i32 = 3
    while fd < 256
        if sys_close(fd) != 0
            return 4
        fd = fd + 1
    if sys_open(c"/a", 2, O_RDONLY) != 3
        return 5
    # stdio is not a filesystem fd
    if is_fs_fd(0) or is_fs_fd(2) or sys_close(1) != Errno.BadF as i64
        return 6
    0
"""

CAPACITY_CLAIMS = {1: "init gets a table", 2: "253 fds (3..255) open at once",
                   3: "the 254th is Errno.NFile", 4: "all close", 5: "fd 3 free again",
                   6: "stdio is not an fs fd"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_process_holds_253_fds(compiler, tmp_path):
    rc = _run(compiler, tmp_path, CAPACITY, FS_MODULES)
    assert rc == 0, f"{compiler}: {CAPACITY_CLAIMS.get(rc, f'exit {rc}')}"


# A dup'd fd shares its original's open file (AGAST #2786): the same blob and
# one position (POSIX dup), whichever fd closes first; pending writes flush
# once, when the last fd closes; a dup left open at exit is closed too; and
# nothing is freed twice. stdio and unopened fds don't dup. sys_dup is not
# in the syscall table yet; this pins what wiring it will expose.
DUP = FS_PRELUDE + """\
fn main() -> i32
    let base: i64 = heap_live()
    if fs_process_start(1) != 0
        return 1
    if sys_open(c"/a", 2, O_RDONLY) != 3 or sys_dup(3) != 4
        return 2
    if not reads(4, c"al", 2) or not reads(3, c"pha", 3)
        return 3
    if sys_close(3) != 0 or is_fs_fd(3)
        return 4
    if sys_lseek(4, 0, SEEK_SET) != 0 or not reads(4, c"alpha", 5)
        return 5
    if sys_close(4) != 0 or is_fs_fd(4) or sys_close(4) != Errno.BadF as i64
        return 6
    if sys_open(c"/w", 2, O_WRONLY | O_CREAT) != 3 or sys_dup(3) != 4
        return 7
    if sys_fs_write(3, c"he", 2) != 2 or sys_fs_write(4, c"llo", 3) != 3
        return 8
    let writes: i32 = stub_writes()
    if sys_close(4) != 0 or stub_writes() != writes
        return 9
    if sys_close(3) != 0 or stub_writes() != writes + 1 or not stub_holds(c"/w", 2, c"hello", 5)
        return 10
    if sys_dup(1) != Errno.BadF as i64 or sys_dup(9) != Errno.BadF as i64
        return 11
    if sys_open(c"/a", 2, O_RDONLY) != 3 or sys_dup(3) != 4
        return 12
    if fs_process_end() != 2 or heap_live() != base
        return 13
    0
"""

DUP_CLAIMS = {1: "init gets a table", 2: "open /a as 3, dup as 4",
              3: "the dup reads the same file at one shared position",
              4: "the original closes", 5: "the dup still reads after the original closed",
              6: "the dup closes, once", 7: "open /w as 3, dup as 4",
              8: "both fds write", 9: "closing one fd does not flush",
              10: "the last close flushes both writes once",
              11: "stdio and unopened fds don't dup",
              12: "open /a and dup it again", 13: "exit closes both; nothing leaked or double-freed"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_dup_shares_the_open_file(compiler, tmp_path):
    rc = _run(compiler, tmp_path, DUP, FS_MODULES)
    assert rc == 0, f"{compiler}: {DUP_CLAIMS.get(rc, f'exit {rc}')}"


# --- where the process layer calls fs ---------------------------------------------

def _fn(path, name):
    src = path.read_text()
    m = re.search(rf"^(pub )?fn {name}\(.*?(?=^\S|\Z)", src, re.M | re.S)
    assert m, f"{name} not found in {path}"
    return m.group(0)


PROCESS = KERNEL_SRC / "syscall" / "runtime" / "process.ritz"


def test_exit_releases_the_table_before_the_parent_resumes():
    body = _fn(PROCESS, "sys_exit_impl")
    child, init = body.split("# No parent", 1)
    # child: in the parent's address space, before the parent runs again (the
    # order is #2753's; a flush growing the heap is safe under any CR3, #2761)
    assert child.index("vmm_switch_pml4(g_parent_ctx.user_pml4)") < child.index("fs_process_end()") \
        < child.index("resume_user_frame(")
    # init exiting: released before the halt
    assert init.index("fs_process_end()") < init.index("halt_loop()")


@pytest.mark.parametrize("spawn", ["sys_spawn_impl", "sys_spawn_args_impl"])
def test_spawn_gives_the_child_a_table_and_undoes_it_on_failure(spawn):
    body = _fn(PROCESS, spawn)
    # made before the switch into the child's page table (kalloc may map
    # heap pages through the identity map, which the child's lacks)
    assert body.index("fs_process_start(g_child_pid)") < body.index("vmm_switch_pml4(child_pml4)")
    # every later failure path gives it back
    fails = re.findall(r"vmm_switch_pml4\(g_parent_ctx\.user_pml4\)\n(\s+)(\S.*)\n", body)
    assert fails and all(line == "fs_process_end()" for _, line in fails), fails


def test_init_gets_a_table_before_it_runs():
    # run_init makes the running process init through process_enter_init
    # (syscall/runtime/process.ritz, #2751), before it jumps to /bin/init.
    enter = _fn(PROCESS, "process_enter_init")
    assert "fs_process_start(1)" in enter
    body = _fn(KERNEL_SRC / "main.ritz", "run_init")
    assert body.index("process_enter_init()") < body.index("jump_to_userspace(")


def test_fs_layer_does_not_import_the_process_layer():
    # No import cycle and no same-language `extern fn` (c6dc7be8): the process
    # layer tells fs who runs; fs never asks.
    for rel in ("fs/syscall.ritz", "fs/fd.ritz"):
        src = (KERNEL_SRC / rel).read_text()
        assert not re.search(r"^import syscall\.runtime", src, re.M), rel
        assert "extern fn" not in src, rel


def test_no_kernel_wide_fd_table_is_left():
    vfs = (KERNEL_SRC / "fs" / "vfs.ritz").read_text()
    assert "kernel_fds" not in vfs and "fn fd_alloc" not in vfs
    fs = (KERNEL_SRC / "fs" / "syscall.ritz").read_text()
    # one heap FsProc per live process; the BSS keeps only the pointers
    assert re.search(r"^var fs_procs: \[8\]\*FsProc$", fs, re.M)
    assert not re.search(r"^var \w+: \[\d+\]", fs.replace("var fs_procs", ""), re.M)


def test_init_runs_the_fd_table_tests():
    suite = _fn(INDIUM / "user" / "init.ritz", "run_tier1_tests")
    assert 'run_test(c"/bin/fd_table_test",  c"fd_table_test",  0)' in suite
    assert 'run_test(c"/bin/pid_child_test", c"pid_child_test", 0)' in suite
    assert "run_fd_isolation_test()" in suite
    # init is the parent and runs the child twice (a second run must get fd 3)
    steps = _fn(INDIUM / "user" / "init.ritz", "fd_isolation_steps")
    assert steps.count('spawn_and_wait(c"/bin/fd_isolation_child")') == 2
    toml = (INDIUM / "ritz.toml").read_text()
    for name in ("fd_table_test", "fd_isolation_child", "pid_child_test"):
        assert f'name = "{name}"\nentry = "{name}::main"' in toml, name
        assert (INDIUM / "user" / f"{name}.ritz").exists(), name
