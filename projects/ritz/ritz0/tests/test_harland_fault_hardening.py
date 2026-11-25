"""Harland fault/bounds hardening (AGAST #2755, feature #1844.9).

Re-port of origin/harland-main 0eda5329, 86f03bb6 and a0e23c79 onto main.

* A CPU exception taken in ring 3 kills the running process with status
  128 + vector (a page fault exits 142) and resumes its parent; only a
  kernel-mode exception still panics.  The user path prints neither
  "!!! EXCEPTION !!!" nor "KERNEL PANIC": the boot tests treat those as a
  kernel failure.
* init (no parent) exiting powers the machine off through ACPI, so QEMU
  exits instead of hanging; only a failed poweroff halts.
* The PMM refuses to free a frame at or above the top of RAM it manages, and
  vmm never hands the PMM a frame a PTE marks PTE_DEVICE (the user
  framebuffer mapping: MMIO the PMM never owned, which may lie below the top
  of RAM).  Freeing either used to put device memory in the free pool.
* sys_fb_map maps into the calling process every time: the kernel-wide
  "already mapped" cache returned an address the next process never had.
* (The scheduler's idle-task bounds went with the unused scheduler, deleted
  in AGAST #1882; test_harland_process_model.py checks it stays gone.)

The PMM rule is checked by running the real module on the host; the rest is
structural, with the OVMF Tier-1 boot (tools/test_tier1_boot.sh: init's
fault_child test and the power-off check) as the runtime check.
"""

import re

import pytest

from test_harland_syscall_dispatch import KERNEL_SRC, _run

pytestmark = pytest.mark.unit

HARLAND = KERNEL_SRC.parents[1]
INDIUM = HARLAND.parent / "indium"
EXCEPTIONS = KERNEL_SRC / "arch" / "x86_64" / "exceptions.ritz"
PROCESS = KERNEL_SRC / "syscall" / "runtime" / "process.ritz"
FRAMEBUFFER = KERNEL_SRC / "syscall" / "runtime" / "framebuffer.ritz"
VMM = KERNEL_SRC / "mm" / "vmm.ritz"
TIER1_BOOT = HARLAND / "tools" / "test_tier1_boot.sh"


def _fn(path, name):
    """The body of fn `name` in `path`, comments stripped (they say what the
    code should do; the test checks what it does)."""
    src = path.read_text()
    m = re.search(rf"^(pub )?fn {name}\(.*?(?=^\S|\Z)", src, re.M | re.S)
    assert m, f"{name} not found in {path}"
    return "\n".join(line.split("#", 1)[0].rstrip() for line in m.group(0).splitlines())


# --- the PMM frees only frames it manages (runs pmm.ritz on the host) -------------

# mm/pmm logs through klog (#1885), which imports serial, whose `asm x86_64:`
# blocks only ritz0 parses; klog imports ritzlib.fmt.digits (#1957) and ritzlib.str.
PMM_MODULES = ["mm.pmm", "klog", "serial", "io", "boot_abi.serial", "boot_abi.portio", "ritzlib.fmt.digits", "ritzlib.str"]

# Exit code i names the i-th failing check.
PMM_OWN_FRAMES = """\
import ritzlib.option
import mm.pmm { PAGE_SIZE, pmm_init, pmm_mark_region_free, pmm_alloc_page, pmm_free_page, pmm_get_free_pages, pmm_get_total_pages }

# A 4 GiB bitmap (the boot paths size theirs from the memory map, #4183).
var bm: [131072]u8

fn main() -> i32
    pmm_init(@bm[0], 1048576)
    # RAM is pages 0..7 (page 0 stays out of the pool).
    pmm_mark_region_free(0, 8 * PAGE_SIZE)
    if pmm_get_total_pages() != 8 or pmm_get_free_pages() != 7
        return 1
    let a: u64 = pmm_alloc_page()
    if a == 0
        return 2
    # The first frame past RAM, and a framebuffer-like MMIO frame (QEMU's
    # 0x80000000, below the PMM's 4 GiB bitmap limit): never the PMM's.
    if pmm_free_page(8 * PAGE_SIZE) != -1
        return 3
    if pmm_free_page(0x80000000) != -1
        return 4
    if pmm_get_free_pages() != 6
        return 5
    # A frame the PMM handed out still goes back.
    if pmm_free_page(a) != 0 or pmm_get_free_pages() != 7
        return 6
    0
"""


@pytest.mark.integration
def test_pmm_refuses_frames_past_the_ram_it_manages(tmp_path):
    rc = _run("ritz0", tmp_path, PMM_OWN_FRAMES, PMM_MODULES)
    assert rc == 0, f"PMM ownership check {rc} failed (see PMM_OWN_FRAMES)"


def test_pmm_reserves_the_whole_kernel_image():
    """The kernel's physical extent comes from the linker, not a fixed 1 MiB.
    Once the image (.bss with the 64 KiB syscall stack) passed phys 0x200000,
    a hard-coded 1..2 MiB reservation let pmm hand out the image's last page
    as the physmap PDPT, and the syscall stack overwrote it (#2755)."""
    body = _fn(KERNEL_SRC / "mm" / "pmm.ritz", "pmm_reserve_kernel")
    assert re.search(r"^pub fn pmm_reserve_kernel\(kernel_phys_end: u64\)", body), body
    assert "pmm_mark_region_used(0x100000, 0x100000)" not in body, body
    assert re.search(r"var end: u64 = kernel_phys_end\n(.*\n)*?\s+pmm_mark_region_used\(0x100000, end - 0x100000\)", body), body
    main = (KERNEL_SRC / "main.ritz").read_text()
    assert re.search(r"^extern var __kernel_virt_end: u8$", main, re.M), "main.ritz"
    calls = re.findall(r"^\s+pmm_reserve_kernel\((.*)\)$", main, re.M)
    assert calls and all(c == "kernel_phys_end()" for c in calls), calls
    end = _fn(KERNEL_SRC / "main.ritz", "kernel_phys_end")
    assert "@__kernel_virt_end as u64 - KERNEL_VIRT_BASE" in end, end


# --- vmm skips device frames; fb_map marks them -----------------------------------

def test_vmm_frees_no_device_frame():
    src = VMM.read_text()
    m = re.search(r"^pub const PTE_DEVICE: u64 = (\d+)$", src, re.M)
    assert m, "vmm.ritz defines no PTE_DEVICE"
    # One of the three bits x86-64 leaves to the OS (9..11) in a 4 KiB PTE.
    assert int(m.group(1)) in (1 << 9, 1 << 10, 1 << 11), m.group(1)
    body = _fn(VMM, "vmm_free_user_pt")
    frees = re.findall(r"^(\s+)(?:if .*\n\s+)?pmm_free_page\(", body, re.M)
    assert len(frees) == 1, body
    # A PTE_SHM leaf is a shared object's frame, not the process's (#4717):
    # skipped too, and on its own bit.
    m_shm = re.search(r"^pub const PTE_SHM: u64 = (\d+)$", src, re.M)
    assert m_shm and int(m_shm.group(1)) in (1 << 10, 1 << 11), "vmm.ritz defines no PTE_SHM on a free OS bit"
    assert re.search(r"if \(pt_entry & PTE_PRESENT\) != 0 and \(pt_entry & \(PTE_DEVICE \| PTE_SHM\)\) == 0\n"
                     r"\s+pmm_free_page\(pt_entry & PTE_ADDR_MASK\)", body), body


def test_fb_map_marks_device_frames_and_maps_every_time():
    body = _fn(FRAMEBUFFER, "sys_fb_map_impl")
    m = re.search(r"vmm_map_page\(virt_addr, phys_addr, ([^)]*)\)", body)
    assert m and "PTE_DEVICE" in m.group(1) and "PTE_USER" in m.group(1), body
    # No kernel-wide cache: each process gets its own mapping.
    src = FRAMEBUFFER.read_text()
    assert "g_user_fb_mapped" not in src and "g_user_fb_addr" not in src


# --- a user-mode exception kills the process ----------------------------------------

def test_user_mode_exception_kills_only_the_process():
    body = _fn(EXCEPTIONS, "exception_handler")
    # Any non-zero CPL is a process (RING1_DRIVER.md section 3, AGAST #4711):
    # a ring-1 driver's fault kills it like a ring-3 program's.
    m = re.search(r"if \(\(\*frame\)\.cs & 3\) != 0\n((?:\s{8}.*\n)+)", body)
    assert m, "exception_handler does not test for a non-zero-CPL fault"
    user = m.group(1)
    # Before any panic output, and it exits with 128 + vector.
    assert body.index(m.group(0)) < body.index("!!! EXCEPTION !!!")
    assert re.search(r"process_kill_current\(128 \+ \(\(\*frame\)\.vector as i32\)\)", user), user
    assert "EXCEPTION" not in user and "PANIC" not in user and "halt_loop" not in user, user
    src = EXCEPTIONS.read_text()
    assert re.search(r"^import syscall\.runtime\.process \{ [^}]*process_kill_current", src, re.M)


def test_every_process_predicate_is_any_nonzero_cpl():
    """exception_handler, the tick's sched_tick argument and the console
    IRQ's tty_console_irq argument treat CPL 1 as a process, like CPL 3
    (RING1_DRIVER.md section 3, AGAST #4711): none tests for ring 3 alone."""
    code = "\n".join(line.split("#", 1)[0].rstrip() for line in EXCEPTIONS.read_text().splitlines())
    assert not re.search(r"cs & 3\) == 3", code), "a CPL test still means ring 3 only"
    irq = _fn(EXCEPTIONS, "irq_handler")
    assert "sched_tick(((*frame).cs & 3) != 0)" in irq, irq
    assert "tty_console_irq(((*frame).cs & 3) != 0)" in irq, irq


def test_process_kill_current_is_exit():
    body = _fn(PROCESS, "process_kill_current")
    assert "sys_exit_impl(status)" in body, body


# --- init exiting powers off --------------------------------------------------------

def test_init_exit_powers_off():
    body = _fn(PROCESS, "sys_exit_impl")
    init = body.split("sched_exit()", 1)[1]
    # fds flushed, then ACPI poweroff; only a failed poweroff halts.
    assert init.index("fs_process_end()") < init.index("acpi_poweroff()") < init.index("halt_loop()")


# --- indium: the fault test and init's own exit -------------------------------------

def test_init_runs_the_fault_test_and_exits_to_poweroff():
    init = INDIUM / "user" / "init.ritz"
    suite = _fn(init, "run_tier1_tests")
    assert 'run_test(c"/bin/fault_child",  c"fault_child",  142)' in suite, suite
    # A later test still runs: init survived the child's fault.
    assert suite.index("fault_child") < suite.index("rzsh --help")
    # init leaves the poweroff to the kernel's exit path
    assert "sys_acpi_poweroff" not in _fn(init, "main")
    toml = (INDIUM / "ritz.toml").read_text()
    assert 'name = "fault_child"\nentry = "fault_child::main"' in toml
    assert (INDIUM / "user" / "fault_child.ritz").exists()


def test_tier1_boot_requires_qemu_to_power_off():
    script = TIER1_BOOT.read_text()
    assert "init exited with code" in script
    assert re.search(r'^powered_off\(\) \{', script, re.M), "no power-off check"
    assert script.count("powered_off native") == 1 and script.count("powered_off grub") == 1
