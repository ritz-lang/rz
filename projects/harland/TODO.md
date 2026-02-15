# Harland TODO

> See [MILESTONES.md](MILESTONES.md) for the full roadmap

## Current Focus: Milestone 0 → 1 (Hello World)

### Milestone 0: Build Infrastructure ✅ COMPLETE

**Goal**: Ritz compiles to x86-64 freestanding binary

- [x] Ritz compiler supports `--no-runtime` flag for freestanding code
- [x] `asm x86_64:` block syntax with `{varname}` interpolation
- [x] Integer types: `u8-u64`, `i8-i64`
- [x] build.py compiles kernel/src/main.ritz to ELF64
- [x] Inline assembly works for port I/O (`outb`, `inb`)
- [x] Serial driver works with inline assembly
- [x] Kernel entry point exports properly (`pub fn kernel_main`)

### Milestone 1: Hello World 🔄 IN PROGRESS

**Goal**: Boot in QEMU, print to serial

- [x] Kernel serial output (kernel/src/main.ritz)
  - [x] `outb` / `inb` port I/O via inline assembly
  - [x] Serial port init (COM1 at 115200 baud)
  - [x] `serial_print`, `serial_print_hex`, `serial_print_dec`
- [x] Build infrastructure
  - [x] Multiboot2 header in boot.s
  - [x] Flat linker script (kernel at 1MB physical)
  - [x] tools/qemu-test.sh for automated testing
  - [x] tools/mkiso.sh for GRUB ISO creation
- [ ] QEMU boot testing
  - [ ] Install QEMU: `sudo apt install qemu-system-x86`
  - [ ] Run: `make test-boot`
  - [ ] Verify: "Hello from Harland!" appears in serial output
- [ ] UEFI bootloader (deferred - using Multiboot2/GRUB for now)
  - [ ] Rewrite boot/stage1.ritz in current Ritz syntax
  - [ ] qcow2 image creation

---

## Upcoming Milestones

| # | Milestone | Status |
|---|-----------|--------|
| 0 | Build Infrastructure | ✅ Complete |
| 1 | Hello World (Serial) | 🔄 In Progress |
| 2 | Framebuffer Console | ⏳ Planned |
| 3 | CPU Setup (GDT/IDT) | ⏳ Planned |
| 4 | Virtual Memory | ⏳ Planned |
| 5 | APIC & Interrupts | ⏳ Planned |
| 6 | Kernel Heap | ⏳ Planned |
| 7 | Kernel Threads | ⏳ Planned |
| 8 | User Space | ⏳ Planned |
| **9** | **Syscall Abstraction** | ⏳ **Critical Path** |
| 10 | VirtIO Network | ⏳ Planned |
| 11 | Filesystem | ⏳ Planned |
| 12 | Self-Hosting | ⏳ Planned |

---

## Critical Architecture Decision: Syscall Abstraction Layer

**Goal**: Ritz programs run on Linux, Windows, macOS, ARM, AND Harland

```
Ritz App → ritz::sys (abstract) → Backend (harland/linux/windows/etc)
```

This needs to be designed NOW, even if Harland-specific syscalls come later.

### ritz::sys API (Draft)

```ritz
# Platform-agnostic syscall interface
sys_read(fd: i32, buf: ptr[u8], count: usize) -> isize
sys_write(fd: i32, buf: ptr[u8], count: usize) -> isize
sys_open(path: ptr[u8], flags: i32, mode: u32) -> i32
sys_close(fd: i32) -> i32
sys_mmap(...) -> ptr[void]
sys_exit(code: i32) -> !
# ... etc
```

### Backend Selection

```ritz
@cfg(target_os = "harland")
import ritz.sys.harland as backend

@cfg(target_os = "linux")
import ritz.sys.linux as backend

# All backends implement same interface
```

See MILESTONES.md § Milestone 9 for full design.

---

## Questions / Decisions Needed

1. **Ritz compiler changes**: Fork ritz repo, or add kernel target to existing?
   - Leaning: In-place extension, keep one codebase

2. **UEFI bootloader linking**: PE/COFF vs ELF conversion?
   - Option A: LLVM target `x86_64-unknown-windows` for PE
   - Option B: Build ELF, `objcopy` to PE
   - Leaning: Option A (cleaner)

3. **Test framework**: How to run integration tests in QEMU?
   - Use `isa-debug-exit` device for exit codes
   - Serial output captured and grep'd for results
   - Timeout handling for hangs

---

## Notes

### QEMU Command Reference
```bash
qemu-system-x86_64 \
    -drive if=pflash,format=raw,file=/usr/share/OVMF/OVMF_CODE.fd,readonly=on \
    -drive if=pflash,format=raw,file=OVMF_VARS.fd \
    -drive file=harland.qcow2,format=qcow2 \
    -m 4G \
    -smp 4 \
    -serial mon:stdio \
    -no-reboot \
    -d int,cpu_reset  # Debug: show interrupts and resets
```

### Key Resources
- OSDev Wiki: https://wiki.osdev.org/
- BOOTBOOT: https://gitlab.com/bztsrc/bootboot
- OVMF: https://github.com/tianocore/tianocore.github.io/wiki/OVMF
- Intel SDM Vol 3: System Programming Guide
- AMD64 ABI: https://refspecs.linuxbase.org/elf/x86_64-abi-0.99.pdf
