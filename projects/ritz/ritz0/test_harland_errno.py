"""Harland has one kernel errno enum; ELF loader errors are not errnos (AGAST #2123).

Before: errno values were loose constants in four modules (fs/vfs E_*,
fs/knamespace KNS_*, fs/namespace NS_*, mm/uptr UPTR_ERR_*/EFAULT, plus
syscall/dispatch ENOSYS), and many syscall paths returned bare -1 (EPERM to
any caller that reads it as -errno) or a mislabelled number (ipc/channel
answered "EAGAIN" with -4, which is EINTR). The ELF loader's ELF_ERR_* were
-1..-8: the same i32s as EPERM..ENOEXEC.

After: `pub enum Errno: i64` (syscall/errno.ritz) is the only source of
errno values, returned as `Errno.X as i64` at the ABI boundary; the loader
returns `enum ElfStatus`, a different type, which the kernel maps to an errno
when a spawn fails.

The behavioural tests compile the real kernel modules into host programs on
every compiler (helpers shared with test_harland_syscall_dispatch.py); the
source tests pin the acceptance criteria ("no loose errno consts", "no bare
-1 where an errno is meant").
"""

import re

import pytest

from test_harland_syscall_dispatch import COMPILERS, KERNEL_SRC, RITZ_ROOT, _compile, _run

pytestmark = pytest.mark.integration

ERRNO_SRC = KERNEL_SRC / "syscall" / "errno.ritz"
RITZLIB_SYS = RITZ_ROOT / "ritzlib" / "sys.ritz"

# Variant -> Linux errno number. A syscall returns -errno, so the variant's
# discriminant is the negation. Renumbering one is an ABI break.
LINUX = {
    "Perm": 1, "NoEnt": 2, "Srch": 3, "Io": 5, "TooBig": 7, "NoExec": 8,
    "BadF": 9, "Child": 10, "Again": 11, "NoMem": 12, "Acces": 13, "Fault": 14,
    "Exist": 17, "NoDev": 19, "NotDir": 20, "IsDir": 21, "Inval": 22,
    "NFile": 23, "NoSpc": 28, "Pipe": 32, "Range": 34, "NameTooLong": 36,
    "NoSys": 38, "NotEmpty": 39,
}

# Variant -> ritzlib/sys.ritz constant name, for the ones ritzlib declares.
RITZLIB_NAME = {
    "Perm": "EPERM", "NoEnt": "ENOENT", "Srch": "ESRCH", "Io": "EIO",
    "NoExec": "ENOEXEC", "BadF": "EBADF", "Child": "ECHILD", "Again": "EAGAIN",
    "NoMem": "ENOMEM", "Acces": "EACCES", "Fault": "EFAULT", "Exist": "EEXIST", "NoDev": "ENODEV",
    "NotDir": "ENOTDIR", "IsDir": "EISDIR", "Inval": "EINVAL", "NFile": "ENFILE",
    "NoSpc": "ENOSPC", "Pipe": "EPIPE", "NotEmpty": "ENOTEMPTY",
}

# The modules a host program needs to link the kernel's serial output path.
SERIAL = ["serial", "io"]

# serial.ritz and mm/vmm.ritz hold `asm x86_64:` blocks, which ritz1 can't
# parse yet (AGAST #1455/#1825; harland under ritz1 is #1848), so a test that
# links a module importing them runs on ritz0, the compiler `rz build harland`
# uses. syscall/errno, numbers and dispatch import neither: those tests run on
# every compiler.
ASM_DEPS = ["ritz0"]


def _declared_errno():
    src = ERRNO_SRC.read_text()
    m = re.search(r"^pub enum Errno: i64\n((?:[ \t]+.*\n|[ \t]*\n|#.*\n)+)", src, re.M)
    assert m, "syscall/errno.ritz has no `pub enum Errno: i64`"
    return {k: int(v) for k, v in re.findall(r"^\s+(\w+)\s*=\s*(-?\d+)", m.group(1), re.M)}


def _expect(cases):
    """`if <expr> != <want>\\n return i` for each case: exit i names the failing one."""
    return "\n".join(f"    if {expr} != {want}\n        return {i + 1}"
                     for i, (expr, want) in enumerate(cases))


def _check(compiler, tmp_path, header, cases, modules, prelude=""):
    src = f"{header}\nfn main() -> i32\n{prelude}{_expect(cases)}\n    0\n"
    rc = _run(compiler, tmp_path, src, modules)
    assert rc == 0, (f"{compiler}: {cases[rc - 1][0]} != {cases[rc - 1][1]}"
                     if 0 < rc <= len(cases) else f"{compiler}: exit {rc}")


# --- the enum ---------------------------------------------------------------------

def test_errno_enum_is_linux_numbering():
    assert _declared_errno() == {k: -v for k, v in LINUX.items()}


def test_errno_matches_ritzlib_constants():
    """User programs compare -result against ritzlib's E* constants: the same
    numbers, so a harland errno means what a Linux one does."""
    src = RITZLIB_SYS.read_text()
    lib = {n: int(v) for n, v in re.findall(r"^(?:pub\s+)?const\s+(E[A-Z0-9]+)\s*:\s*\w+\s*=\s*(\d+)", src, re.M)}
    declared = _declared_errno()
    for variant, name in RITZLIB_NAME.items():
        assert name in lib, f"ritzlib/sys.ritz has no {name}"
        assert -declared[variant] == lib[name], f"Errno.{variant} = {declared[variant]}, ritzlib {name} = {lib[name]}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_errno_discriminants(compiler, tmp_path):
    cases = [(f"Errno.{k} as i64", -v) for k, v in LINUX.items()]
    # The i32 view (vfs, knamespace and uptr return i32) is the same number.
    cases += [("Errno.Fault as i32", -14), ("Errno.NoSys as i32", -38)]
    _check(compiler, tmp_path, "import ritzlib.option\nimport syscall.errno\n", cases, ["syscall.errno"])


def test_kernel_contract_lists_the_enum():
    """docs/KERNEL_CONTRACT.md's error table is the enum, row for row."""
    doc = (KERNEL_SRC.parents[1] / "docs" / "KERNEL_CONTRACT.md").read_text()
    section = doc[doc.index("## Error Codes"):]
    section = section[:section.index("\n---\n")]
    rows = re.findall(r"^\| (-\d+) \| E\w+ \| (\w+) \|", section, re.M)
    assert {v: int(c) for c, v in rows} == _declared_errno()


# --- uptr, vfs, knamespace, ipc, dispatch return Errno values -----------------------

@pytest.mark.parametrize("compiler", ASM_DEPS)
def test_uptr_faults_are_errno_fault(compiler, tmp_path):
    kernel = "0xFFFF800000001000 as *u8"
    cases = [
        ("uptr_validate_read(0 as *u8, 8)", "Errno.Fault as i32"),
        (f"uptr_validate_read({kernel}, 8)", "Errno.Fault as i32"),
        (f"uptr_validate_write({kernel}, 8)", "Errno.Fault as i32"),
        ("uptr_validate_string(0 as *u8, 16)", "Errno.Fault as i64"),
        (f"uptr_validate_string({kernel}, 16)", "Errno.Fault as i64"),
        ("uptr_check_read(0 as *u8, 8)", "Errno.Fault as i64"),
        (f"uptr_check_write({kernel}, 8)", "Errno.Fault as i64"),
        ("uptr_validate_read(0 as *u8, 0)", "0"),
    ]
    _check(compiler, tmp_path, "import ritzlib.option\nimport syscall.errno\nimport mm.uptr\n", cases,
           ["syscall.errno", "mm.uptr", "mm.vmm", "mm.pmm", *SERIAL])


@pytest.mark.parametrize("compiler", ASM_DEPS)
def test_vfs_errors_are_errno(compiler, tmp_path):
    cases = [
        ("fd_free(-1)", "Errno.BadF as i32"),
        ("fd_free(64)", "Errno.BadF as i32"),
        ("fd_free(5)", "Errno.BadF as i32"),          # never allocated
        ("vfs_mount(c\"/\", 1, 0)", "Errno.Inval as i32"),  # before vfs_init
        ("vfs_stat(c\"/x\", 2, 0 as *Stat)", "Errno.NoEnt as i32"),
        ("vfs_mkdir(c\"/x\", 2)", "Errno.NoEnt as i32"),
    ]
    _check(compiler, tmp_path, "import ritzlib.option\nimport syscall.errno\nimport fs.vfs\n", cases,
           ["syscall.errno", "fs.vfs", *SERIAL])


CHANNEL_PRELUDE = """\
    var closed: ChannelEndpoint
    closed.state = CHAN_STATE_CLOSED
    closed.queue_count = 0
    var lonely: ChannelEndpoint
    lonely.state = CHAN_STATE_OPEN
    lonely.peer = 0 as *ChannelEndpoint
    lonely.queue_count = 0
    var full: ChannelEndpoint
    full.state = CHAN_STATE_OPEN
    full.queue_count = CHANNEL_QUEUE_MAX
    var sender: ChannelEndpoint
    sender.state = CHAN_STATE_OPEN
    sender.peer = @full
    var msg: Message
    ipc_syscall_init()
"""


@pytest.mark.parametrize("compiler", ASM_DEPS)
def test_ipc_errors_are_errno(compiler, tmp_path):
    """channel.ritz returned -1..-5 labelled EINVAL/EBADF/EPIPE/EAGAIN/ENOMEM,
    which are really EPERM/ENOENT/ESRCH/EINTR/EIO."""
    none = "0 as *ChannelEndpoint"
    cases = [
        (f"channel_send({none}, @msg, 1)", "Errno.Inval as i32"),
        ("channel_send(@closed, @msg, 1)", "Errno.BadF as i32"),
        ("channel_send(@lonely, @msg, 1)", "Errno.Pipe as i32"),
        ("channel_send(@sender, @msg, 1)", "Errno.Again as i32"),
        (f"channel_recv({none}, @msg, 0 as *u32)", "Errno.Inval as i32"),
        ("channel_recv(@closed, @msg, 0 as *u32)", "Errno.BadF as i32"),
        ("channel_recv(@lonely, @msg, 0 as *u32)", "Errno.Again as i32"),
        ("sys_ipc_send(1, 7, @msg)", "Errno.BadF as i64"),
        ("sys_ipc_recv(1, 7, @msg, 0 as *u32)", "Errno.BadF as i64"),
        ("sys_ipc_close(1, -1)", "Errno.BadF as i64"),
        (f"channel_close({none})", "Errno.Inval as i32"),
    ]
    header = ("import ritzlib.option\nimport syscall.errno\nimport ipc.message\n"
              "import ipc.channel\nimport ipc.syscall\n")
    _check(compiler, tmp_path, header, cases,
           ["syscall.errno", "ipc.syscall", "ipc.channel", "ipc.message", "mm.heap", "mm.pmm", "mm.vmm", *SERIAL],
           prelude=CHANNEL_PRELUDE)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_unknown_syscall_is_errno_nosys(compiler, tmp_path):
    cases = [("syscall_dispatch(5, 0, 0, 0, 0)", "Errno.NoSys as i64"),
             ("syscall_dispatch(0xFFFFFFFFFFFFFFFF, 0, 0, 0, 0)", "-38")]
    header = "import ritzlib.option\nimport syscall.errno\nimport syscall.numbers\nimport syscall.dispatch\n"
    _check(compiler, tmp_path, header, cases, ["syscall.errno", "syscall.numbers", "syscall.dispatch"])


# --- the ELF loader has its own error type ------------------------------------------

ELF_PRELUDE = """\
    var h: Elf64Ehdr
    h.e_ident[0] = 0x7F
    h.e_ident[1] = 0x45
    h.e_ident[2] = 0x4C
    h.e_ident[3] = 0x46
    h.e_ident[4] = 2
    h.e_ident[5] = 1
    h.e_type = ET_EXEC
    h.e_machine = 62
    h.e_phnum = 1
    if elf_validate_header(@h) != ElfStatus.Ok
        return 100
    h.e_phnum = 0
    if elf_validate_header(@h) != ElfStatus.NoSegments
        return 101
    h.e_phnum = 1
    h.e_machine = 3
    if elf_validate_header(@h) != ElfStatus.WrongMachine
        return 102
    h.e_machine = 62
    h.e_type = 1
    if elf_validate_header(@h) != ElfStatus.NotExecutable
        return 103
    h.e_type = ET_EXEC
    h.e_ident[5] = 2
    if elf_validate_header(@h) != ElfStatus.NotLittleEndian
        return 104
    h.e_ident[5] = 1
    h.e_ident[4] = 1
    if elf_validate_header(@h) != ElfStatus.NotElf64
        return 105
    h.e_ident[4] = 2
    h.e_ident[0] = 0
    if elf_validate_header(@h) != ElfStatus.InvalidMagic
        return 106
"""

ELF_MODULES = ["loader.elf", "mm.vmm", "mm.pmm", *SERIAL]


# elf_exec calls into main.ritz (extern fns); the host program supplies them.
ELF_STUBS = """\
pub fn alloc_user_stack() -> u64
    0

pub fn jump_to_userspace(entry: u64, stack: u64)
    return

"""


@pytest.mark.parametrize("compiler", ASM_DEPS)
def test_elf_validate_header_returns_elf_status(compiler, tmp_path):
    src = ("import ritzlib.option\nimport loader.elf\n\n" + ELF_STUBS + "fn main() -> i32\n"
           + ELF_PRELUDE + "    0\n")
    rc = _run(compiler, tmp_path, src, ELF_MODULES)
    assert rc == 0, f"{compiler}: elf check {rc - 100} failed (exit {rc})"


def test_elf_status_owns_its_codes():
    """ELF_ERR_* were the i32s -1..-8, i.e. -EPERM..-ENOEXEC: returned from a
    syscall, a loader code read as an errno. ElfStatus is its own enum with no
    integer representation (so no negative discriminant), and the kernel turns
    one into a number only through elf_status_errno (spawn's errno) or
    elf_status_code (serial logs)."""
    src = (KERNEL_SRC / "loader" / "elf.ritz").read_text()
    assert re.search(r"^pub enum ElfStatus\n", src, re.M), \
        "loader/elf.ritz has no `pub enum ElfStatus` (without an integer representation)"
    assert re.search(r"^\s+error: ElfStatus\b", src, re.M), "ElfLoadResult.error is not an ElfStatus"
    assert re.search(r"^pub fn elf_validate_header\(.*\) -> ElfStatus$", src, re.M)
    assert not re.search(r"\bELF_(OK|ERR_\w+)\b", src), "ELF_OK/ELF_ERR_* constants remain"
    assert "syscall.errno" not in src, "the loader should not speak errno"
    main = (KERNEL_SRC / "main.ritz").read_text()
    uses = re.findall(r"load_result\.error[^\n]*", main)
    assert uses, "main.ritz no longer checks load_result.error"
    for use in uses:
        assert re.match(r"load_result\.error( != ElfStatus\.Ok$|\))", use), \
            f"an ElfStatus used other than compared or passed to elf_status_errno/elf_status_code: {use}"


def test_spawn_maps_elf_status_to_errno():
    """A failed load answers ENOMEM (out of pages) or ENOEXEC (not a loadable
    x86-64 executable): both spawn paths go through elf_status_errno."""
    main = (KERNEL_SRC / "main.ritz").read_text()
    m = re.search(r"^fn elf_status_errno\(s: ElfStatus\) -> i64\n((?:[ \t]+.*\n)+)", main, re.M)
    assert m, "main.ritz has no elf_status_errno"
    body = m.group(1)
    assert re.search(r"AllocFailed => Errno\.NoMem as i64", body)
    assert re.search(r"MapFailed => Errno\.NoMem as i64", body)
    assert re.search(r"_ => Errno\.NoExec as i64", body)
    assert main.count("return elf_status_errno(load_result.error)") == 2


# --- acceptance: no loose errno values left in the kernel ---------------------------

def _kernel_files():
    return sorted(p for p in KERNEL_SRC.rglob("*.ritz") if p != ERRNO_SRC)


# Private status codes of modules no syscall reaches (mm/shm, mm/dma are not
# imported by the kernel); they are not errnos and never reach user space.
NOT_ERRNO = {"SHM_", "DMA_"}


def test_no_loose_errno_constants():
    loose = []
    for p in _kernel_files():
        for m in re.finditer(r"^(?:pub\s+)?const\s+(\w+)\s*:\s*i\d+\s*=\s*-\d+", p.read_text(), re.M):
            if not any(m.group(1).startswith(pfx) for pfx in NOT_ERRNO):
                loose.append(f"{p.relative_to(KERNEL_SRC)}: {m.group(0)}")
    assert not loose, "negative constants beside enum Errno:\n" + "\n".join(loose)


def _fn_bodies(src):
    """{name: body} for each top-level fn in a Ritz source file."""
    out = {}
    for m in re.finditer(r"^(?:pub\s+)?fn\s+(\w+)\(.*?\n((?:[ \t]+.*\n|[ \t]*\n)*)", src, re.M):
        out[m.group(1)] = m.group(2)
    return out


# The functions whose results reach rax: every sys_* fn, and the module
# functions they pass through unchanged.
PASSTHROUGH = {
    "fs/vfs.ritz": None,             # every fn
    "fs/knamespace.ritz": {"knamespace_write", "knamespace_mkdir", "knamespace_list"},
    "mm/uptr.ritz": None,
    "ipc/channel.ritz": {"channel_send", "channel_recv", "channel_close"},
    "fs/syscall.ritz": {"fs_flush_write_buffer"},   # sys_close returns it
}


def test_no_bare_negative_returns_on_syscall_paths():
    bad = []
    for p in _kernel_files():
        rel = str(p.relative_to(KERNEL_SRC))
        for name, body in _fn_bodies(p.read_text()).items():
            watched = name.startswith("sys_") or (
                rel in PASSTHROUGH and (PASSTHROUGH[rel] is None or name in PASSTHROUGH[rel]))
            if not watched:
                continue
            for line in body.splitlines():
                code = line.split("#")[0]
                if re.search(r"\breturn\s+\(?-\d+", code):
                    bad.append(f"{rel}: {name}: {line.strip()}")
    assert not bad, "bare negative returns where an errno is meant:\n" + "\n".join(bad)
