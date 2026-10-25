# LARB v4 Review: harland (kernel) and goliath (filesystem)

**Reviewed:** 2026-10-25 · **Metrics:** [metrics-packages.md](metrics-packages.md) §harland, §goliath · **Status:** CRITICAL
**Scope:** `projects/harland`: 84 `.ritz` files and 25,002 lines in total. Of those, `kernel/src` is 21,357, `boot/src` 1,672, `user/` 840 and `docs/*.ritz` 1,133. `projects/goliath`: 12 files, 2,258 lines.
**Method:** `INSTRUCTIONS_v4.md`, read-only. Nothing was built or booted.

**Baseline:** findings are against `main`. `origin/harland-main` has 21 unmerged commits: the #1839 recovery work, which splits `kernel/src/main.ritz` from 2,677 lines to 481. Each finding below was re-checked on that branch with `git show origin/harland-main:<path>`. A finding is marked **(fixed on harland-main)** only where that check showed it gone.

**The three claims everything else rests on, and how each was checked:**
- **C1 (syscall stack overflow).** I read the stack definition (`syscall_entry.s:18-22`, the stack switch at `:96`) and the frames that run on it (`main.ritz:879`, `:1129-1130`, `:1204`). I worked out the `KDirEntry` size from `kdir_entry.ritz:15-27`. I confirmed the same arrays exist on harland-main (`syscall/runtime/process.ritz:113`, `:304-305`, `:361`). I read the `.data` input ordering (`kernel/linker.ld:114-118`) and the link order (Ritz objects at `ritz/build.py:1814`, assembly objects after them at `:1859`).
- **C2 (mmap region inside the shared kernel identity map).** I read both page-table builders (`kernel/boot.s:225-236`; `boot/src/main.ritz:663`, `:703-713`), the mapper (`vmm.ritz:247-248`, `:268-271`), the PML4 cloning (`vmm.ritz:586-588`, `:707`) and the mmap constants (`main.ritz:799`, `:818`). Not executed. #1878 asks for the red test.
- **The goliath fork claim (M3, M13).** I ran a `difflib` line-match over comment-stripped, name-normalised sources (numbers in M3). The nested-write data-loss bug is confirmed by reading both versions side by side: `goliath/src/namespace.ritz:258-260` and `harland/kernel/src/fs/knamespace.ritz:159-191`.

## Summary

- **Size and complexity:** `kernel_main` (388 SLOC) is the only Critical function. `syscall_handler` (CC 62) and the SHA-256 constant ladder (CC 65) are the other threshold hits. harland-main already decomposes `main.ritz`.
- **Two real correctness defects sit under "it boots":**
  - The single 4 KB syscall stack is overrun by syscall frames of 5 KB to 21 KB (C1). This is the probable cause of what `main.ritz:1789` blames on "a compiler bug that corrupts kernel globals".
  - The user mmap region lies inside page tables shared with the kernel and with every process (C2).
- **ritz1 cannot build any of this (C3):**
  - 65 inline `asm` blocks and 42 `[[packed]]` structs, neither of which is in the spec or in ritz1.
  - No volatile, atomics, linker-symbol or calling-convention constructs, so the code works around them in asm.
  - harland uses no `[[naked]]` functions, so M2.2's "`[[naked]]` works in ritz1" is not on harland's path.
- **Imports:** the kernel imports zero ritzlib modules. Instead it carries:
  - its own `StrView`;
  - nine number formatters;
  - a fork of goliath (kpath, kdir_entry, knamespace);
  - a fork of cryptosec's SHA-256.

  The goliath fork has drifted. A data-loss fix exists only in the kernel copy, and goliath upstream still loses nested writes (M13). goliath is hosted-only, so it is not fit to be harland's filesystem today (M14).
- **Dead code:** about 2,200 lines of dead kernel modules, a second 859-line build system, five unused linker/boot scripts, a diverged fork of `indium/user`, and 1,133 lines of `.ritz` under `docs/` that dominate the duplication metrics.
- **Not yet started for M2.3/M2.4:** NVMe (no code at all), MSI-X (only unused struct fields and register constants), a calibrated timer (M6), more than 16 CPUs or APIC IDs above 15 (M7), and memory above 4 GB (M7).

## Findings

### C1. One 4 KB syscall stack, overrun by syscall frames of 5 KB to 21 KB [bug] — Critical → #1877
- **The stack:** `syscall_entry.s:18-22` declares `syscall_stack: .space 4096` in `.data`, marked "TODO: per-CPU". Entry switches to it at `:96`. IRQs nest on the same stack (`:135-136`).
- **The frames that run on it:**
  - `sys_readdir_impl` declares `var entries: [64]KDirEntry` (`main.ritz:879`). `KDirEntry` is a 256-byte name, two `u8`s, a 32-byte id and a 28-byte metadata block (`kdir_entry.ritz:15-27`). That is 328 bytes by natural layout, so about **21 KB** for the array.
  - `sys_spawn_args_impl` holds `[4096]u8`, `[64]i64` and `[64]u64` (`main.ritz:1129-1130`, `:1204`): **5 KB**.
  - `knamespace_write` recurses once per path component, with a `KBlobId` and `StrView` locals in each frame (`knamespace.ritz:163-195`).
- **Why this is probably the "compiler bug":**
  - The stack grows down out of `syscall_stack` into whatever `.data` precedes it.
  - `.data` is laid out in input order (`linker.ld:114-118`), and Ritz objects are linked before the assembly files (`ritz/build.py:1814` vs `:1859`). So `main.ritz`'s initialised globals sit below the stack.
  - Those are exactly the globals the `SYS_OPEN` workaround saves and restores (`main.ritz:1789-1806`): `g_child_pid = 1` and `g_has_parent`.
  - The workaround blames 32-byte struct returns, but large struct returns moved to sret in #1730/#1736 (`ritz0/test_large_struct_copy.py:5`).
- **On harland-main:** the same arrays persist (`syscall/runtime/process.ritz:113`, `:304-305`, `:361`), the stack is still `.space 4096`, and the workaround is deleted without a test.
- **Fix direction:** per-CPU kernel stacks of at least 16 KB with an unmapped guard page and a TSS IST entry for faults. Keep large buffers off the stack (`kalloc`, or copy out to user memory in chunks). Restore or delete the `SYS_OPEN` workaround only after a red test.

### C2. The user mmap region is inside the kernel's shared identity map [bug][architecture] — Critical → #1878
- **The layout:**
  - Both boot paths identity-map low memory with 2 MB pages in a page directory that is also the higher-half kernel's: `boot.s:225-236` maps 0–1 GB, and `boot/src/main.ritz:703-713` maps at least 256 MB (`:663`).
  - `USER_MMAP_START = 0x10000000` (`main.ritz:799`) is 256 MB, which is PDPT[0] → PD[128].
  - `vmm_create_user_pml4` copies the kernel's PDPT[0] entry into every process (`vmm.ritz:586-588`). So every process's mmap region resolves through the kernel's own page directory.
- **What happens, depending on RAM:**
  - **1 GB or more** (indium runs with `-m 4G`, `indium/Makefile:169`): PD[128] is a huge page, so `vmm_map_page` returns −1 (`vmm.ritz:270-271`). Every kernel-chosen `sys_mmap` therefore fails.
  - **256 MB** (`boot/test.sh:286`): PD[128] is empty. A page table is allocated *inside the shared PD* with `PTE_USER` set (`vmm.ritz:268`). The page then also appears at `0xFFFFFFFF90000000` in kernel space and is reachable from every process. `vmm_free_user_pages` skips PDPT[0] (`:707`), so the table leaks.
- **Also:**
  - `g_next_mmap_addr` is one global bump pointer for all processes, never reset (`main.ritz:818`, `:1347-1348`).
  - Partial failures leak pages (`:1372`, `:1382` TODOs).
  - `indium/user/mmap_test.ritz:14-17` tests for failure with `== 0`, but the kernel returns −1, so the test cannot see the failure.
- **On harland-main:** persists (`syscall/runtime/memory.ritz:18`, `:27`, `:86-87`).
- **Fix direction:** put user mappings only in private page tables (for example PML4[1..255]; never under a shared kernel PDPT). Keep a per-process mmap cursor in a process struct. Run the kernel through a separate physmap rather than the low identity map.

### C3. ritz1 cannot build the kernel; the needed features are not in the spec [language-gap] — Critical → #1879 (#1825, #1840)
- **Inline asm:** 55 `asm x86_64:` blocks in `kernel/src` (17 in `io.ritz`, 9 in `drivers/ena/device.ritz`) and 10 in `boot/src/main.ritz`. Spec §2 says `asm` "is reserved but has no syntax behind it yet" (`LANGUAGE_SPEC.md:150`). ritz1 has no asm support (no match in `ritz1/src`).
- **`[[packed]]`:** 42 uses (21 in `boot/src/main.ritz`, 16 in `drivers/ena/admin.ritz`, plus gdt, idt and pmm). It is not in spec §17, and ritz0 alone implements it (`ritz0/test_attrs.py`).
- **No volatile load/store:** all MMIO is plain dereference (`drivers/virtio/common.ritz:231-253`). It is correct today only because ritz0 builds at `-O0`.
- **No atomics:** the spinlock is an asm `xchg` against a hard-coded symbol name, `lea scheduler_lock(%rip)` (`sched/mod.ritz:111-118`). That relies on globals never being mangled.
- **No extern data symbols:** linker symbols are declared as functions and cast, e.g. `extern fn __bss_start()` (`main.ritz:92-99`) and `ap_trampoline_start` (`:474`).
- **No foreign calling convention:** UEFI is called through four hand-written MS-x64 asm shims, `uefi_call2..5` (`boot/src/main.ritz:534-594`). These are the source of the duplicate `subq $40, %rsp` cluster.
- **Correction for M2.2:** zero `[[naked]]` uses in harland (verified with grep). The entry stubs are `.s` files. M2.2's "`[[naked]]` works in ritz1" is not on harland's path.

### M1. `main.ritz` is a god module; the dispatcher is a 29-arm `if` ladder [architecture][language-gap] — Major → #1880
- **One file holds everything:** the ring-buffer logger, PIC, LAPIC, IOAPIC, SMP bring-up, every syscall implementation, the dispatcher and boot orchestration (2,677 lines).
- **Size and complexity:** `kernel_main` is 388 SLOC / CC 51 / depth 6 (`:2115`). `syscall_handler` is CC 62 (`:1781`).
- **(fixed on harland-main):** the split into `syscall/dispatch.ritz`, `syscall/runtime/*`, `postinit.ritz`, `klog.ritz` and `arch/x86_64/apic.ritz`.
- **What remains:** `dispatch.ritz` is still 29 `if rax ==` arms.
- **Language gap:**
  - `match` supports literal, enum and wildcard patterns only (spec §8.2). A bare `SYS_READ =>` would be a binding, not a comparison.
  - Enums have no explicit discriminants (spec §10.1).
  - So the ABI cannot be an enum. That also keeps `MB2_TAG_*` (25 constants imported at `main.ritz:18`), the errno values and the ELF error codes as loose constants.
- **Cleanup available today:** a handler table of function pointers. Function-pointer fields already compile, e.g. `goliath/src/virtio_store.ritz:93`.

### M2. Two process models, neither complete [architecture] — Major → #1882
- **Spawn is "blocking":** one global `g_parent_ctx`, `g_has_parent`, `g_child_pid = 2` and `g_child_pml4` (`main.ritz:829-842`, `:1003-1008`, `:1259-1283`).
- **Consequences:**
  - A child that spawns overwrites its parent's saved context, so nesting is impossible (init → rzsh → script → command).
  - `sys_wait` only knows PID 2 (`:1297`).
  - cwd is one global (`:1466-1467`).
- **The scheduler is unused:** `sched/mod.ritz` has tasks, a ready queue and per-CPU state. But preemption is disabled (`:404`), `timer_handler` is never called (`arch/x86_64/exceptions.ritz:296-300` just sends EOI), nothing calls `task_create`, and `SYS_YIELD` is a no-op (`main.ritz:1880-1883`). APs halt forever (`:533-535`).
- **Layering:** `main` imports scheduler internals (`tasks`, `cpu_sched`, `scheduler_lock`; `main.ritz:73-79`) and writes `scheduler_initialized = 0` directly (`:2126`).
- **On harland-main:** persists (`syscall/runtime/process.ritz:40`, `:155-166`).

### M3. The kernel filesystem is a fork of goliath; three storage formats [architecture] — Major → #1881 (needs #1857)
- **Fork evidence** (difflib, comment-stripped, `k`-prefixes normalised):
  - `fs/kdir_entry.ritz` matches 101 of 113 lines of `goliath/src/dir_entry.ritz` (ratio 0.90).
  - `fs/kpath.ritz` matches 75 of 94 lines of `goliath/src/path.ritz` (0.74).
  - `fs/knamespace.ritz` matches 126 of 200 lines of `goliath/src/namespace.ritz` (0.61).
  - `lib/sha256.ritz` matches 210 lines of `cryptosec/lib/sha256.ritz` (0.52).
- **Why the fork exists:** `docs/GOLIATH_INTEGRATION.md:24-40` planned it. goliath uses `ritzlib.sys` `sys_mmap`, and cryptosec imports `ritzlib.sys` (`cryptosec/lib/sha256.ritz:15`). Neither builds freestanding, which is ritzlib's M3.
- **The fork has drifted:** nested-path propagation exists only in the kernel copy (M13).
- **Three on-disk/in-memory formats:**
  - goliath `virtio_store.ritz`: "GOLIATH" magic, 2,048 blobs, bitmap;
  - harland `fs/persist.ritz`: "HARBLOB" magic, 640 blobs (`:40-44`), no free map;
  - the initramfs TAR.
- **A second namespace inside the kernel:** dead `fs/namespace.ritz` (619 lines; matches only 27 lines with knamespace) is the only code that checks caps.
- **No garbage collection:** with content addressing and no GC, every write is permanent. The 64 MB heap comment reads "content-addressed FS needs space for version history" (`main.ritz:2215`).

### M4. Duplicated drivers and paths [cleanup] — Major → #1884
- **Two virtio transports:**
  - `drivers/virtio/net.ritz:21-147` has a private legacy I/O-port virtqueue (`VirtqDesc`, `VirtQueue`) and does not import `drivers.virtio.common`.
  - blk and input use `common.ritz` (`VringDesc`, `Virtqueue`, modern MMIO).
- **Inside blk:** `virtio_blk_read`/`virtio_blk_write` (`blk.ritz:213-325` vs `:326-437`) share 93 of 113 lines. This is the 132-line duplicate window.
- **Other copies:**
  - The ENA admin submit/wait/check sequence appears 3 times (`ena/device.ritz:597`, `:819`, `:917`).
  - `apic_init_with_mb` and `apic_init_from_bootinfo` are the same 40 lines apart from the ACPI call (`main.ritz:651-692` vs `:695-735`).
  - `sys_spawn_impl` and `sys_spawn_args_impl` duplicate the namespace read, context save, PML4 setup and three error-unwind blocks (`main.ritz:986-1061` vs `:1072-1183`).
  - `alloc_user_stack` has two copies of its unwind loop (`:933-942`, `:949-958`).
- **Loader vs kernel ABI:**
  - The boot ABI is declared twice: `[[packed]] BootInfo` (`boot/src/main.ritz:373-391`) and an unpacked `HarlandBootInfo` (`mm/pmm.ritz:112-128`). The layouts agree only because the padding is explicit.
  - The ELF structs are declared twice (`boot/src/main.ritz:309-353` vs `loader/elf.ritz`).
  - The serial driver is written twice (`boot/src/main.ritz:429-520` vs `serial.ritz`).

### M5. No memory-ordering discipline for devices and SMP [language-gap][bug] — Major → #1879, #1884
- **Missing barrier:** `vq_submit` has no barrier between the ring write and the `idx` publish. The comment says so: "In a real implementation, we'd use a proper memory barrier" (`virtio/common.ritz:478-479`).
- **Barriers not shared:** ENA open-codes `mfence`/`lfence` in asm (`ena/device.ritz:201`, `:490`, `:516`, `:526`, `:1019`, `:1202`), while `io.ritz:93-106` already exports `memory_barrier`, `read_barrier` and `write_barrier`.
- **Races:** `ap_count = ap_count + 1` runs on every AP with no atomic (`main.ritz:530`). `sched_unlock` is a plain store (`sched/mod.ritz:124-126`).
- **The serial "lock-free" claim:** `serial.ritz:58` says COM1's THRE interrupt drains the output buffer while syscalls fill it. The producer/consumer indices are plain `i32` globals (`:62-65`).

### M6. Time is measured in loop iterations [architecture] — Major → #1883 (M2.3 #1841: "timer on")
- **Delays:**
  - `delay_us` "assumes ~1GHz CPU" (`main.ritz:505-512`). It counts `pause` instructions, whose latency varies more than tenfold across microarchitectures.
  - AP start-up timeouts are built on it (`:588-609`).
- **Polling loops:**
  - DHCP polls 1,000 times with `while delay < 100000` between polls (`:2625-2632`).
  - ENA admin waits for 100,000 iterations (`ena/device.ritz:513-558`).
  - The reset wait is `delay < 100` (`:232-237`).
- **No time source:** there is no TSC, HPET or LAPIC-timer calibration anywhere. `apic_timer_init` was removed (`sched/mod.ritz:404`).

### M7. Hardware ceilings baked in as array sizes [bug][architecture] — Major → #1883 (#1841, #1842)
- **APIC IDs index 16-entry arrays:** `ap_started[16]` is indexed by **APIC ID**, not CPU index (`main.ritz:461`, `:529`, `:607`, `:611`). An APIC ID of 16 or more writes out of bounds. Sparse or high APIC IDs are normal on larger EC2 instances and on AMD. Persists on harland-main (`apic.ritz:209`, `:261`, `:265`).
- **The 16-CPU limit is spelled three ways:** `MAX_CPUS = 16` (`sched/mod.ritz:44`), `cpu_apic_ids: [16]u8` (`acpi/tables.ritz:195`, `:439`) and the literals at `main.ritz:461-462`. There is no x2APIC.
- **Memory:**
  - The PMM caps at 4 GB (`mm/pmm.ritz:20-21`, `:146`).
  - The ELF loader writes physical pages through the identity map (`loader/elf.ritz:286`, `:293`). That map covers 1 GB on the Multiboot path (`boot.s:225-230`) and 4 GB at most on UEFI (`boot/src/main.ritz:661`), while the PMM can hand out any page below 4 GB.
  - There is no `phys_to_virt` and no physmap.
- **Allocation:** `pmm_alloc_page` is a linear scan from page 0 (`pmm.ritz:244-253`).

### M8. The syscall ABI has drifted three ways; there is no error type [cleanup][language-gap] — Major → #1880
- **ritzlib redeclares the numbers:** `ritzlib/sys.ritz:47-94` duplicates harland's numbers under the comment "MUST match the harland kernel (kernel/src/main.ritz)" (`:45`). The numbers moved to `syscall/numbers.ritz` (commit 9ed1d7e, "single source of truth"), so the comment is stale.
- **Declared but never dispatched:** ritzlib exports `spawn_ex` and `pipe` (`sys.ritz:169`, `:176`), which the kernel never dispatches, so they always return −1 through "unknown syscall" (`main.ritz:2046-2049`). Also declared and never dispatched: `SYS_STAT`, `SYS_LSEEK` (although `sys_lseek` is imported at `:37`), `SYS_MKDIR`, `SYS_IPC_CALL` and `SYS_NET_*` (`syscall/numbers.ritz` vs `main.ritz:1783-2043`).
- **A dead file with conflicting numbers:** `arch/x86_64/syscall.ritz:60` says `SYS_MMAP = 10`, where `numbers.ritz:20` says 9. `kernel/user_program.s:11` tells readers to match that dead file.
- **Errors:**
  - Syscalls return a mix of bare −1, `EFAULT = -14` (`mm/uptr.ritz:39`) and `E_*` errnos (`fs/vfs.ritz:41-50`).
  - ELF errors −1 to −5 collide with errno values (`loader/elf.ritz:124-129`).
  - Error-code enums need explicit discriminants (M1). `Result` is in a hosted ritzlib (#1857).

### M9. Syscall boundary gaps [bug] — Major → #1888 (#1843)
- **The ELF loader trusts its input:** `elf_load` never reads `elf_size` (`loader/elf.ritz:194`; the parameter is only referenced at `:359`). It does not check `e_phoff` or `p_offset + p_filesz`, and it does not check that `p_vaddr` is a user address (`:227-235`). Every page is mapped `PTE_USER` (`:174`).
- **That makes it reachable from userspace:** files are user-writable (`sys_fs_write` → `knamespace_write`) and spawnable (`sys_spawn` → `knamespace_read`, `main.ritz:996`). A crafted ELF can make the loader read past its buffer, and can map user pages into the 4 KB-paged kernel heap range (`mm/heap.ritz:21-27`).
- **Double fetch:** the handler validates each `argv[i]` (`main.ritz:1925-1932`), then the implementation re-reads the user array (`:1123`, `:1151`).
- **No capability checks:** caps are checked only inside the cap syscalls (`cap/syscall.ritz:152`). `SYS_ACPI_POWEROFF`, `SYS_FB_MAP`, IPC and FS are open to every process (`main.ritz:2026-2043`). The only cap-gated namespace is the dead `fs/namespace.ritz:232`.

### M10. Strings, formatting and logging: C idioms, reimplemented [cleanup] — Major → #1885 (needs #1857, #1824)
- **The kernel declares its own `StrView`** (`serial.ritz:74`). The loader declares another (`boot/src/main.ritz:472`).
- **Nine number formatters:**
  - `serial.ritz:121`, `:142`, `:170`
  - `main.ritz:146`
  - `drivers/netdev.ritz:238`
  - `drivers/virtio/net.ritz:474`
  - `drivers/ena/device.ritz:1294`, `:1308`
  - `boot/src/main.ritz:487`, `:502`

  `arch/x86_64/interrupts.ritz:296` is dead.
- **Signedness bug:** `serial_print_dec` takes `u64`, but callers pass signed values, e.g. `map_result as u64` for −1 (`main.ritz:2405`) prints `18446744073709551615`.
- **Four logging entry points with different sinks:** `klog(*u8)` writes serial and the ring buffer; `prints(StrView)`, `serial_print(*u8)` and `prints_str(*u8)` write serial only, and `prints_str` (`main.ritz:1688`) duplicates `serial_print`. Most of `kernel_main` uses `prints`, so its messages never reach the crash ring buffer.
- **Hand-rolled strlen:** `syscall_strlen` and 7 other open-coded strlen loops (grep `while *p != 0`).
- **i32 used where unit or bool belongs:** 129 of the 297 `-> i32` functions in kernel and boot have `return 0` as their only return (checked with a script). There are 23 `u8` globals used as booleans.
- **Fixed buffers:** `g_cwd: [256]u8` + `g_cwd_len` (`main.ritz:1466-1467`).

### M11. Dead code, a second build system, forks [cleanup] — Major → #1886
- **Modules with no production importer.** `rz build` compiles only the import closure of `main` (`ritz/build.py:1686-1709`, `list_deps.py`), so these are never compiled and rot silently:
  - `arch/x86_64/interrupts.ritz` (423), a second `exception_handler`/`irq_handler`
  - `arch/x86_64/syscall.ritz` (495)
  - `process.ritz` (173), imported only by the dead syscall.ritz
  - `fs/namespace.ritz` (619)
  - `fs/backend.ritz` (122), imported only by the dead namespace
  - `fs/mod.ritz` (13)
  - `mm/shm.ritz` (204) and `mm/dma.ritz` (171), "WIP - commented out until imports are fixed" (`main.ritz:22-24`)

  That is about 2,220 lines.
- **A second build system:** `harland/build.py` (859 lines) plus the checked-in `harland/ritz/ritz`, a wrapper that hard-wires ritz0. The Makefile uses `rz build` (`Makefile:42`). Only stale echo lines in `tools/mkiso.sh:31` and `tools/qemu-test.sh:44` mention `build.py`.
- **Unused linker and boot scripts:** `kernel/linker32.ld`, `linker_flat.ld`, `linker_highhalf.ld`, `linker_highhalf_proper.ld`, `boot_highhalf.s` and `user/linker_spawned.ld`; 836 lines.
- **`harland/user/`** (21 files, 840 lines) is a diverged fork of `indium/user`: 13 files differ and 3 are missing. Nothing builds it, and `ritz.toml:3-4` says userspace lives in indium.
- **Design files written as code:** `docs/*.ritz` and `docs/old_designs/**` (1,133 lines) produce the top duplicate clusters in the metrics.
- **Tools copied into indium:** `tools/mkimage.py`, `mkboot.sh` and `mkiso.sh` (29, 20 and 87 differing lines).
- **Boot tests:** three QEMU boot scripts (`tools/qemu-test.sh`, `tools/test_boot.sh`, `boot/test.sh`), none run by CI. `ritz.toml`'s `[test] sources = ["tests"]` names a directory that doesn't exist, and nothing reads `[test.qemu]` (cf. tooling F8, #1837).

### M12. Self-tests in the boot path, and known faults skipped instead of fixed [architecture] — Major → #1887
- **Boot runs tests nobody asserts:** `kernel_main` runs VMM, higher-half, heap and IPC tests that print PASS/FAILED (`main.ritz:2383-2597`). It also runs `test_elf_loader()` (`:2667`), `virtio_blk_test` (`:2662`) and a DHCP-then-ping loop (`:2610-2653`). This is test policy inside boot mechanism.
- **Two page faults are hidden:**
  - `channel_close` is skipped "due to page fault" (`:2589-2592`).
  - `channel_debug_print` "causes page fault - skipped" (`:2596-2597`).
  - Both are still on harland-main (`postinit.ritz:226`).
- **The heap is checked by hand:** six `heap_check()` calls in `kernel_main` print `HEAP CORRUPT` and carry on (`:2260-2302`).

### Minor → #1887 unless noted
- **m1. A stream-of-consciousness comment:** "Wait, this is wrong. Let me reconsider." (`main.ritz:1701-1741`). Its conclusion is correct: the GDT order (`gdt.ritz:22-25`) prevents `sysretq`, so every exit is `iretq` (`syscall_entry.s:220`, `:270`, `:348`, `:407`). Reorder the GDT to user-data then user-code and use `sysretq`.
- **m2. Magic numbers:**
  - trampoline parameters `0x8FF0`/`0x8FF8`/`0x9000` duplicate `ap_trampoline.s` (`main.ritz:561-572`)
  - ICR `0x8500` (`:593`) and SFMASK `0x200` (`:1750`)
  - the load base `0x100000000` three times (`:1034`, `:1164`, `:2076`)
  - the framebuffer address `0x7F0000000000` (`:1658`)
  - `heap_init(16384)` commented as "64MB" (`:2215`)
  - a test rectangle at 540,350, which assumes the screen resolution (`:2252`)
  - user-struct sizes `4096`/`16`/`8`/`24` in the dispatcher (`:1945`, `:1977`, `:2020`, `:2036`), where `sizeof` exists (spec §7.9)
- **m3. Contradictory BSS handling:** `clear_bss()` runs, then `scheduler_initialized = 0` is set because "BSS might not be zeroed" (`main.ritz:2117`, `:2125-2126`).
- **m4. A selective import that doesn't filter:** `main.ritz` uses `vmm_pml4_phys` (`:562`, `:2210`), which is not in its `mm.vmm` import list (`:19`). → #1858
- **m5. SHA-256 round constants are a 130-line `if` ladder** with CC 65 (`lib/sha256.ritz:88`); cryptosec has the same ladder. A `const K: [64]u32` table works under ritz0, but under ritz1 indexing a module const array segfaults (#1534). Fix #1534, then use the table.
- **m6. Bare-metal UEFI glue in the loader:** the `uefi_call*` shims (C3) and `setup_page_tables`' four copies of the PD-fill loop (`boot/src/main.ritz:703-780`) collapse to one loop over GB index. → #1884
- **m7. Silent failure in the Makefile:** `cp ... 2>/dev/null || true` (`Makefile:43-44`) hides a missing kernel image from the test targets. → #1886

## goliath (content-addressed filesystem)

**Liveness:** nothing outside goliath imports it (grep `import goliath` finds only `ritz/ritz1/src/ast_helpers.ritz`). The kernel uses its fork (M3).
**Fitness verdict:** not fit to be harland's filesystem as it stands:
- it is hosted-only;
- its persistent store is a stub;
- it loses nested writes;
- it fills after about 30 writes.

The kernel fork is the de-facto filesystem.

### M13. Nested writes are silently lost [bug] — Major → #1881
- `update_dir_entry` writes a new parent-directory blob but repoints only the root, and only when the parent *is* root (`namespace.ritz:258-260`).
- So `namespace_write("/a/b")` creates a new `/a` blob that nothing references. It still returns `ERR_OK`.
- The kernel fork fixed this with recursive propagation (`knamespace.ritz:159-195`).
- goliath's tests write only root-level paths (`test/test_namespace.ritz`; there is no `"/x/y"` literal).

### M14. Hosted-only, so the kernel cannot link it [architecture] — Major → #1881 (needs #1857)
- `ritzlib.sys` `sys_mmap`/`sys_munmap` is used in `blob_store.ritz:8`, `namespace.ritz:6` and `virtio_store.ritz:28`; `write` in `error.ritz:5` and `blob_id.ritz:6`.
- SHA-256 comes via cryptosec, which imports `ritzlib.sys`.
- **Fix direction:** pass in an allocator interface and a block-device interface. `virtio_store` already takes `read_fn`/`write_fn` (`:93-94`), so the pattern exists. That lets one goliath build for Linux tests and for the kernel.

### M15. `virtio_store` is a non-persistent stub, and the store saturates [bug] — Major → #1881
- **Persistence:**
  - The index is never loaded ("TODO: Load index from disk", `virtio_store.ritz:162`) and never written back (`:346`).
  - There is no free-space management (`:294`), and nothing tests or imports it.
  - The magic `0x0048544149494C4F` decodes to `"OLIIATH\0"`, with the comment "adjust as needed" (`:38`). The header comment promises `"GOLIATH"` (`:9`).
- **Capacity:**
  - `MemoryBlobStore` has a fixed 64 slots with "TODO: Grow array" (`blob_store.ritz:17`, `:190`).
  - Every write adds a file blob and a directory blob, and nothing is ever freed: no GC or refcount, and `namespace_delete` is a TODO (`namespace.ritz:272`). The store is full after about 30 root-level writes.
  - `sys_mmap` results are never checked (`blob_store.ritz:116`, `:198`; `namespace.ritz:227`).
  - Every lookup scans the full capacity (`blob_store.ritz:140-147`).

### Minor (goliath) → #1881
- **m8. Sizes typed in by hand:**
  - `320` for the serialized entry size (`namespace.ritz:53`, `:238`, `:249`; `dir_entry.ritz:121`, commented "~320")
  - `56  # sizeof(BlobEntry) - approximate` (`blob_store.ritz:110`, `:253`), where `sizeof` exists
  - `main.ritz:31` writes 50 bytes of a 49-byte string literal, one stray byte, with lengths counted by hand although the StrView literal carries its length
- **m9. Hand-rolled vtables with `self: *u8`** (`blob_store.ritz:27-38`, `:151-260`). `dyn` and traits are ritz0-only (M1.2 #1829). The error codes are `i32` constants (`error.ritz:8-20`) rather than an enum or `Result`.

## Not findings
- **`.s` files for ISR stubs, syscall entry, context switch and the AP trampoline.** Right while Ritz has no naked functions. They are better than inline asm for code that owns the stack.
- **`[[packed]]` on UEFI, ACPI, ENA and Multiboot wire structs.** Correct use. The finding is that ritz1 and the spec lack it (C3).
- **Hardware register names.** `serial.ritz:11-35`, `LAPIC_*` (`main.ritz:281-303`), `MSR_*` and `drivers/ena/regs.ritz` are well named. The magic numbers in m2 are the exceptions.
- **The kernel not using ritzlib's allocator.** Justified until #1857: `memory.ritz` calls the 6-argument Linux `sys_mmap`.
- **Stale "ritz1 can't..." comments.** None found in harland or goliath (grep for `ritz1|ritz0|not supported|limitation`).
- **`kernel/linker.ld`.** Required and used by `ritz.toml:28`. Only the other four kernel linker scripts are dead (M11).

## Tickets filed

Priorities are as filed in AGAST (rescaled against the other v4 tickets); every ticket depends on #1844 except #1879 and #1880.

Epic **#48** (Kernel: harland boots). Land **#1839** (harland-main) first, then re-check each ticket's evidence on the merged tree.

| Ticket | Pri | Findings | Acceptance criteria (each can fail) |
|---|---|---|---|
| #1877 (new) Per-CPU kernel stacks with guard pages; no large syscall frames | 80 | C1 | **Red first:** a canary word below `syscall_stack` plus a `readdir` of a 64-entry directory in the boot gate trips today. **Green:** per-CPU stacks of at least 16 KB with an unmapped guard page and a double-fault IST. `grep -nE 'var \w+: \[(64\]KDirEntry\|[0-9]{4,}\]u8)'` over syscall paths returns nothing. The `SYS_OPEN` save/restore is gone and a test that opens 100 files leaves `g_child_pid` intact. |
| #1878 (new) User address-space layout | 78 | C2, M7 (physmap part) | `indium/user/mmap_test` passes under `-m 256M` and `-m 4G` in the boot gate (it fails on 4G today). Two processes mapping `MAP_FIXED` at the same address don't alias (a write test). `vmm_create_user_pml4` shares no table below PML4[256]. The test's `== 0` failure check is fixed to match the −1 return. |
| #1879 (new; companion of #1825, under #1840) Kernel language features: specify and port to ritz1 | 70 | C3, M5 | Compile-gated spec sections for: `asm` with operands, `[[packed]]`, volatile load/store, atomic `xchg`/`cmpxchg`/fence, extern data symbols, and a calling-convention attribute for UEFI. ritz1 builds `harland` and `bootx64` (#1840). `grep -n 'asm x86_64' kernel/src` lists only `io.ritz` and `arch/*`. No `extern fn __bss_start`. |
| #1880 (new, language) Enums with explicit discriminants and constant patterns; table-driven dispatch | 60 | M1, M8 | Spec plus ritz0 plus ritz1 support `enum Syscall: u64` with `= N` and conversion from an integer. `syscall_handler` CC ≤ 15 in ritz-metrics. One syscall-number source that ritzlib's harland block is generated from or imports (a test diffs them). Every declared syscall is either dispatched or deleted. One kernel errno enum. |
| #1881 (new; depends on #1857; un-parks goliath from #49) One filesystem implementation | 60 | M3, M13, M14, M15, m8, m9 | **Red first:** goliath test `write("/a/b")` then `read("/a/b")`, which fails today. goliath builds freestanding behind allocator and block-device interfaces. `kernel/src/fs/{kpath,kdir_entry,knamespace,kblob}.ritz` and `lib/sha256.ritz` are deleted and the kernel imports goliath and cryptosec. One on-disk format, with a test that survives a reboot in the boot gate. The store grows, and deleting a file frees its blobs. |
| #1882 (new) A process model for user processes | 60 | M2 | A per-process struct (pid, pml4, cwd, fds, mmap cursor, saved context) replaces the `g_*` globals. A boot-gate test of init → rzsh → script → command, three levels deep, with exit codes checked. `main` no longer imports `tasks`, `cpu_sched` or `scheduler_lock`. A timer IRQ calls the scheduler, or the scheduler is deleted. |
| #1883 (feeds #1841, #1842) Time source and hardware ceilings | 55 | M6, M7 | A calibrated time source (TSC against PIT/HPET, or the LAPIC timer). Grep finds no `while delay <` or `us * 100` loops. Per-CPU arrays are indexed by CPU index and the boot gate passes with `-smp 4` and sparse APIC IDs. Memory above 4 GB is usable through a physmap, tested with `-m 6G`. |
| #1888 (new, child of #1843) Syscall boundary hardening | 50 | M9 | A fuzz or table test feeds `elf_load` truncated and kernel-address ELFs, and each is rejected. argv is copied in exactly once. `SYS_ACPI_POWEROFF` and `SYS_FB_MAP` require a capability, and a process without it gets an error in the boot gate. |
| #1884 (new) Driver and loader deduplication | 40 | M4, M5 (cleanup part), m6 | virtio-net uses `drivers/virtio/common.ritz`. `virtio_blk_rw` replaces read/write. `vq_submit` has a write barrier. ENA uses `io.ritz` barriers. One `apic_init`. One spawn path. One boot-ABI module shared by the loader and the kernel. Every duplicate cluster in `drivers/` has fewer than 3 copies in ritz-metrics. |
| #1885 (new; depends on #1857, #1824) One kernel string, format and log API | 35 | M10 | One `klog(StrView)` and one formatter that prints `i64::MIN` and negative numbers correctly (red test first). `grep -n 'struct StrView' kernel boot` returns nothing once the freestanding core exists. Fewer than 20 always-0 `-> i32` functions (script). |
| #1886 (new) Dead code, the second build system and the forks | 40 | M11, m7 | Delete: the 8 dead modules, `harland/build.py`, `harland/ritz/`, the 4 dead kernel linker scripts, `boot_highhalf.s`, `user/linker_spawned.ld`, `harland/user/` and `docs/**/*.ritz`. Merge the boot-test scripts into the one #1839 gate uses. Add a liveness check: every `kernel/src` module is reachable from `main::kernel_main` or the check fails. `ritz.toml` has no `[test]`/`[test.qemu]` keys that nothing reads. |
| #1887 (new) Boot path vs self-tests; known faults | 35 | M12, m1–m5 | The self-tests move to a boot-test mode whose PASS/FAIL lines the QEMU gate asserts. `channel_close` and `channel_debug_print` run without faulting (unskipped, red first). `kernel_main` ≤ 80 SLOC. The m2 literals become named constants or `sizeof`. |

## Existing tickets referenced in code and docs
- **#1839–#1843:** milestones M2.1–M2.5.
- **#48:** epic.
- **#49:** PHASE 7, where goliath is parked.
- **#1825:** asm.
- **#1814:** type table, which M2.2 needs.
- **#1857:** ritzlib freestanding core and allocator.
- **#1858:** selective import must filter.
- **#1824:** format into a buffer.
- **#1534:** ritz1 const-array indexing.
- **#1829:** M1.2, for `dyn`/traits.
- **#1837 / #1835:** tooling config keys; freestanding build copy.
- **#1730 / #1736:** sret for large struct returns, cited against the `SYS_OPEN` workaround.
- **#1443:** cited at `main.ritz:1437` for the `munmap` fix.
- **#1484:** cited in `goliath/README.md:83`.
