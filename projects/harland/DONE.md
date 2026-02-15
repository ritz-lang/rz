# Harland DONE

## 2026-02-14: Project Kickoff

### Design Session (Initial)
- [x] Reviewed Ritz language documentation from `nevelis/ritz` repo
- [x] Analyzed ownership/borrowing semantics for kernel suitability
- [x] Designed microkernel architecture (scheduler, VMM, IPC, interrupts)
- [x] Defined 4-level paging strategy (with LA57 as future enhancement)
- [x] Specified UEFI boot sequence (Stage 1 in Ritz)
- [x] Identified SIMD/AVX opportunities (page zeroing, memcpy, crypto)
- [x] Documented language extensions needed (@asm, @naked, @packed, @volatile)
- [x] Created DESIGN.md with full architecture specification
- [x] Created TODO.md with phase-based work breakdown
- [x] Established TDD strategy (unit on host, integration in QEMU)

### Design Refinement (User Feedback)
- [x] Updated target strategy: Both QEMU/KVM and real hardware equally
- [x] Refined inline assembly syntax: `asm x86_64:` block with indentation
- [x] Added variable interpolation design: `{varname}` in asm blocks
- [x] Documented automatic register allocation for asm
- [x] Added BOOTBOOT as reference for bootloader design
- [x] Expanded language extension docs with full examples
- [x] Added bitfield support design (`@bitfield` attribute)

### Key Decisions Made
- **Target**: QEMU/KVM primary iteration, EC2/bare-metal validation
- **Bootloader**: Written in Ritz, BOOTBOOT-inspired design
- **Paging**: 4-level (256TB is plenty)
- **Inline ASM**: `asm x86_64:` block syntax with `{var}` interpolation
- **Architecture**: L4-style microkernel with IPC

### Milestone Roadmap (MILESTONES.md)
- [x] Defined 12 concrete milestones from Hello World to self-hosting
- [x] Designed syscall abstraction layer (Milestone 9 - Critical)
- [x] Created `ritz::sys` API for multi-platform support
- [x] Planned backend system: Harland, Linux, Windows, macOS, ARM
- [x] Established per-milestone testing strategy

### Vision: Portable Ritz Runtime
```
Ritz App → ritz::sys (abstract) → Backend (harland/linux/windows/macos/arm)
```
- Same Ritz code runs on Harland kernel OR existing OSes
- Syscall layer abstracts platform differences
- Enables incremental adoption: test on Linux, deploy on Harland
