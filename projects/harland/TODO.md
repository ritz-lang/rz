# Harland TODO

> See [MILESTONES.md](MILESTONES.md) for the full roadmap

## Current Status: Milestone 12+ Complete

All core milestones through userspace execution are complete. The kernel successfully:
- Boots via Multiboot2/GRUB
- Sets up GDT, IDT, page tables
- Manages physical/virtual memory
- Handles interrupts and preemptive multitasking
- Executes userspace PIE programs in Ring 3
- Implements syscalls (exit, read, write, spawn, wait, readdir, etc.)

## Next Steps

### High Priority

1. **Fix VirtIO TAR Loading Heap Corruption**
   - Heap corruption occurs when loading files from VirtIO disk
   - Currently using embedded initramfs as workaround
   - Need to investigate block splitting/coalescing in heap allocator
   - Files: `kernel/src/mm/heap.ritz`, `kernel/src/fs/initramfs.ritz`

2. ~~**Fix Page Fault on Process Exit**~~ ✅ FIXED
   - Fixed in PR #73 - vmm_free_user_pages was freeing shared kernel page tables
   - Child process cleanup now works correctly
   - All 5 Tier 1 tests pass reliably

3. **Add More Tier 1 Tests**
   - Port remaining ritz examples to Harland userspace
   - Add tests for syscalls: read, write, getpid
   - Consider adding: cat, echo, basic shell

### Medium Priority

4. **Implement VirtIO Network Driver**
   - Required for network stack
   - Files: `kernel/src/drivers/virtio/net.ritz` (create)

5. **Add Signal Handling**
   - Basic signals: SIGKILL, SIGTERM
   - Signal delivery to userspace

6. **File Descriptor Table**
   - Per-process file descriptors
   - stdin/stdout/stderr mapping

### Low Priority / Future

7. **Self-Hosting**
   - Run ritz0 compiler on Harland
   - Requires Python interpreter or native compiler

8. **SMP Support**
   - Multi-processor boot
   - Per-CPU data structures
   - Scheduler improvements

---

## Completed Milestones

| # | Milestone | Status |
|---|-----------|--------|
| 0 | Build Infrastructure | ✅ Complete |
| 1 | Hello World (Serial) | ✅ Complete |
| 2 | Framebuffer Console | ✅ Complete |
| 3 | CPU Setup (GDT/IDT) | ✅ Complete |
| 4 | Virtual Memory | ✅ Complete |
| 5 | APIC & Interrupts | ✅ Complete |
| 6 | Kernel Heap | ✅ Complete |
| 7 | Kernel Threads | ✅ Complete |
| 8 | User Space | ✅ Complete |
| 9 | Syscall Interface | ✅ Complete |
| 10 | VirtIO Block | ✅ Complete |
| 11 | Filesystem (Goliath) | ✅ Complete |
| 12 | Init + Userspace Apps | ✅ Complete |
| 12+ | Tier 1 Test Suite | ✅ Complete |

---

## Known Issues

1. **Import Qualified Names** (ritz-lang/rz#70)
   - `import module as X` then `X::function()` doesn't work
   - Workaround: Use `import module { function }` directly

2. **Heap Corruption with VirtIO TAR**
   - Block magic reads as 0 after splitting
   - Possibly DMA-related or alignment issue
   - Workaround: Use embedded initramfs

3. ~~**Page Fault on Process Exit Cleanup**~~ ✅ FIXED (PR #73)
   - Was freeing shared kernel page tables in vmm_free_user_pages
   - Fixed by skipping PDPT[0] and PDPT[3] which are kernel copies

---

## Architecture Notes

### Userspace Programs

Programs are PIE (Position Independent Executables) loaded at 0x400000.
They use `libharland.ritz` for syscall wrappers.

```ritz
import libharland { sys_exit, sys_write }

pub fn main() -> i32
    sys_write(1, "Hello!\n", 7)
    sys_exit(0)
```

### Init Test Registry

Init maintains a registry of expected exit codes:
```ritz
# Test registry - maps binary name to expected exit code
fn get_expected_exit_code(name: StrView) -> i32
    if strview_eq(name, "true")   -> 0
    if strview_eq(name, "false")  -> 1
    if strview_eq(name, "exitcode") -> 42
    ...
```

### Build Commands

```bash
# Build kernel and userspace
make -C projects/harland kernel

# Run in QEMU with test harness
./projects/harland/boot/test.sh

# Run interactively
./projects/harland/boot/run.sh
```

---

## Resources

- OSDev Wiki: https://wiki.osdev.org/
- Intel SDM Vol 3: System Programming Guide
- AMD64 ABI: https://refspecs.linuxbase.org/elf/x86_64-abi-0.99.pdf
