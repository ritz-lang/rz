# LARB v5 Review: harland (kernel) and goliath (filesystem)

**Reviewed:** 2026-11-16 · **Baseline:** review/4 (2026-10-25) · **Status:** CRITICAL

**Metrics:** [metrics-harland.md](metrics-harland.md). It uses the same script, paths and `--top 15` as review/4's `metrics-packages.md` §harland and §goliath. The baseline numbers below come from rerunning the script on the review/4 tree (887d91ad), and they match review/4's tables.
**Tree:** main @ 6f245b93. `git diff 6f245b93 1f18c488 -- projects/harland projects/goliath` is empty. Nothing was built or booted, and paths are relative to the repo root.

**harland-main:** still unmerged. `git log origin/main..origin/harland-main` shows the same 21 commits, the newest from 2026-02-21 (200b0f8b), with merge-base fb6846e0. main did not land #1839; it **re-ported** parts of the branch instead:
- the main.ritz split: #2750 (9f4fcf58), #2751 (edd9d057), #2752 (701bdff9);
- PMM page 0 and UEFI regions: #2749 (6bdbe17d);
- dd-free tooling: c5e31714;
- the whole-frame parent resume: #2132 (bca04433).

All findings below are against main only. See new finding F3 for what is left on the branch.

## Summary

The interface layer improved:
- The syscall dispatcher is a function-pointer table keyed on `enum Syscall: u64`. `syscall_handler` was CC 62 and is now off every top-15 list.
- There is one syscall ABI, diffed against ritzlib by a test, and one `Errno` enum.
- `main.ritz` went from 2,677 lines to 556.
- harland now uses the #1879 language features: atomics, `fence`, volatile MMIO, `extern var` and `[[callconv = "win64"]]`. The four UEFI asm shims are gone. The spec has these features, and ritz1 has code for them.

None of the kernel's correctness or architecture findings moved:
- C1: the single 4 KB syscall stack and its 21 KB `readdir` frame are unchanged. A test now pins the "compiler bug" workaround in place.
- C2: the mmap region is still inside the shared identity map.
- M2: the blocking one-child process model is unchanged.
- M3: the kernel's goliath fork is unchanged.
- Also unchanged: loop-count timing (M6), 16-entry APIC-ID arrays (M7) and the unchecked ELF loader (M9).

goliath is unchanged apart from an honest CLI stub: it still loses nested writes (M13).

Every runtime claim behind the refactors rests on hand-run QEMU scripts that CI never runs (F1). Status stays **CRITICAL** because C1 and C2 are open and unchanged.

## Against review/4

Counts: FIXED 1 · PARTLY 6 · OPEN 20 · REGRESSED 0 · OBSOLETE 0. 27 rows.

| id | title | v4 sev | now | evidence | ticket |
|---|---|---|---|---|---|
| C1 | One 4 KB syscall stack overrun by 5–21 KB frames | Critical | OPEN | **Stack:** `harland/kernel/syscall_entry.s:18-21` is still `.space 4096` with "TODO: per-CPU".<br>**Frames:** `var entries: [64]KDirEntry` (328 B each, about 21 KB) at `kernel/src/syscall/runtime/file.ritz:29`; `[4096]u8`+`[64]i64` and `[64]u64` at `syscall/runtime/process.ritz:252-253` and `:327`.<br>**Workaround kept:** the "compiler bug" save/restore is still in place (`process.ritz:441-455`). `ritz0/test_harland_syscall_runtime.py:218` now *asserts* it is present.<br>**Acknowledged in code:** #2132 copies the parent frame off the stack because "that stack is one global and the child's own syscalls overwrite it" (`process.ritz:50-54`). | #1877 |
| C2 | User mmap region inside the shared kernel identity map | Critical | OPEN | **Constants:** `USER_MMAP_START = 0x10000000` (`syscall/runtime/memory.ritz:35`). One global bump pointer `g_next_mmap_addr` (`:54`, `:165-166`). Unmap-on-failure TODOs at `:190` and `:200`.<br>**Page tables:** PDPT[0] is still shared into every process (`mm/vmm.ritz:587-588`), the PTE_USER table is still allocated in the shared PD (`:268`), huge-page PD entries still return −1 (`:270-271`), and the free path still skips PDPT[0] (`:707`).<br>**Correction:** see "Not findings". | #1878 |
| C3 | ritz1 can't build the kernel; features not in spec | Critical | PARTLY | **Spec now covers:** `[[packed]]` §17.4, `[[callconv]]` §17.7, volatile §18.4, atomics and fences §18.5, asm §18.6, `extern var` (`LANGUAGE_SPEC.md:1334`).<br>**ritz1 has code for them:** `emitter_core.ritz:5650-5680` (volatile, atomics), `emitter.ritz:539` (packed), `lexer_nfa.ritz:109` (asm), `parser_gen.ritz:2309` (extern var).<br>**Harland migrated** in 624a7895, and the `uefi_call*` shims are gone.<br>**Not done:** no gate shows ritz1 building `harland` or `bootx64`. #1840: grep of `.github`, `ritz1/` and `test/` finds none.<br>**asm blocks:** 65 → 45 (kernel 40, boot 5). #1879's acceptance ("asm only in io.ritz and arch/*") **fails**: `serial.ritz` ×3, `sched/mod.ritz` ×3, `drivers/ena/device.ritz` ×2, `mm/vmm.ritz` ×4. `[[packed]]` is still 42. | #1879 |
| M1 | main.ritz god module; 29-arm dispatcher | Major | PARTLY | **Dispatcher (FIXED):** `syscall/dispatch.ritz:22-51` is a table on `Syscall.from` (b4677289).<br>**Split (done on main):** `main.ritz` is 556 lines / 6 fns.<br>**Still open:** `kernel_main` is 212 SLOC / CC 29 / depth 6 (`main.ritz:247`). That is still above the 150-SLOC Major threshold and #1887's ≤ 80 target. | #1880, #1887 |
| M2 | Two process models, neither complete | Major | OPEN | **Blocking model:** `g_child_pid = 2` (`process.ritz:130`, `:230`); `sys_wait` knows only PID 2 (`:422`).<br>**Still no nesting:** there is one `g_parent_frame` (`:54`).<br>**Globals:** `g_cwd: [256]u8` (`syscall/runtime/cwd.ritz:23`), and one fd table, `kernel_fds: [64]FileDesc`, shared by all processes (`fs/vfs.ritz:233`).<br>**Scheduler:** `SYS_YIELD` returns 0 (`process.ritz:499-502`). `main.ritz:66-73` still imports `tasks`, `cpu_sched`, `scheduler_lock` and `timer_handler`, all unused (F4). `scheduler_initialized = 0` at `main.ritz:258`.<br>**Not ported:** harland-main's per-pid fd context (ed89529c). | #1882 |
| M3 | Kernel FS is a fork of goliath; three formats | Major | OPEN | `fs/kpath`, `kdir_entry`, `knamespace`, `kblob` and `lib/sha256.ritz` are all present, and `main.ritz:28-30` imports them. goliath still has no importer.<br>The dead `fs/namespace.ritz` (613 lines) is still there. Its duplicate-window lines went from 72 to 102 (metrics). | #1881 |
| M4 | Duplicated drivers and paths | Major | OPEN | **virtio-net** still has its own `VirtqDesc`/`VirtqAvail`/`VirtqUsed` (`drivers/virtio/net.ritz:74-92`).<br>**blk:** `virtio_blk_read`/`write` (`blk.ritz:213`, `:326`) carry 132 duplicate-window lines.<br>**ENA** submit is still copied 3× (`ena/device.ritz:594`, `:816`, `:914`).<br>**Two APIC inits:** `apic_init_with_mb`/`apic_init_from_bootinfo` (`arch/x86_64/apic.ritz:420`, `:464`).<br>**Two spawn paths:** `process.ritz:107`, `:194`.<br>**Loader vs kernel:** `BootInfo` vs `HarlandBootInfo` (`boot/src/main.ritz:374`, `mm/pmm.ritz:112`), and a second serial driver plus `StrView` in the loader (`boot/src/main.ritz:445-502`). | #1884 |
| M5 | No memory-ordering discipline | Major | PARTLY | **Fixed:**<br>- `fence()` before the idx publish (`virtio/common.ritz:474`);<br>- `atomic_fetch_add(@ap_count)` (`apic.ritz:301`);<br>- `atomic_xchg`/`atomic_store` lock (`sched/mod.ritz:109-119`);<br>- ENA has no asm fences (grep `mfence\|lfence` hits only `io.ritz`).<br>**Open:**<br>- the cross-CPU flags `ap_started[]` are written by the AP (`apic.ritz:300`) and polled by the BSP with plain loads (`:376`);<br>- the serial "IRQ drains" ring uses plain `i32` head, tail and count (`serial.ritz:61-64`). | #1879, #1884 |
| M6 | Time measured in loop iterations | Major | OPEN | `delay_us` "assumes ~1GHz CPU" (`apic.ritz:276-277`).<br>`while delay <` / `while timeout <` at `postinit.ritz:278`, `drivers/acpi/tables.ritz:500` and `ena/device.ritz:234`, `:300`, `:513`.<br>No TSC, HPET or calibration (grep). | #1883 |
| M7 | Hardware ceilings as array sizes | Major | OPEN | `ap_started: [16]u8` is indexed by APIC ID (`apic.ritz:232`, `:300`, `:376`). `ap_stacks: [16][4096]u8` (`:233`).<br>`MAX_CPUS = 16` (`sched/mod.ritz:44`); `cpu_apic_ids: [16]u8` (`acpi/tables.ritz:195`).<br>`MAX_MEMORY` is 4 GB (`mm/pmm.ritz:20`). `pmm_alloc_page` is a linear scan (`:249-252`). No physmap (grep).<br>Not ported: harland-main a0e23c79 ("harden scheduler CPU/task bounds"). | #1883 |
| M8 | Syscall ABI drifted three ways; no error type | Major | **FIXED** | **One ABI:** `enum Syscall: u64` (`syscall/numbers.ritz:23`). ritzlib is diffed against it by `ritz0/test_harland_syscall_dispatch.py`. The never-dispatched numbers are freed (`numbers.ritz:14-15`). The dead `arch/x86_64/syscall.ritz` is deleted (c532e019).<br>**One error type:** `pub enum Errno: i64` plus `enum ElfStatus` (cefb327c). Bare `return -1` is left only at `ipc/syscall.ritz:49`, `:60`.<br>**Residue:** stale comments (F6). | #1880 |
| M9 | Syscall boundary gaps | Major | OPEN | **ELF loader:** `elf_load` still never reads `elf_size` (`loader/elf.ritz:204`). `e_phoff` and `p_offset` are used unchecked (`:228`, `:253`). `p_vaddr` is not range-checked (`:237`). Every page is mapped `PTE_USER` (`:184`).<br>**argv is fetched three times:** `*(argv + i)` is read to validate (`process.ritz:484`), to size the copy (`:246`) and to copy it (`:274`).<br>**No caps:** `sys_acpi_poweroff_handler` takes no capability (`process.ritz:505`). | #1888 |
| M10 | Strings, formatting, logging: C idioms | Major | OPEN | **StrView:** the kernel's own `struct StrView` is still in `serial.ritz:74`, and another is in `boot/src/main.ritz:472`.<br>**Formatters:** still per file. `serial.ritz:121-209` has 12 print_hex* and print_dec variants, plus `klog.ritz:48`, `boot/src/main.ritz:487`, `:502` and `drivers/netdev.ritz:238`.<br>**Signedness bug:** `serial_print_dec(map_result as u64)` (`postinit.ritz:47`, `:197`, `:210`).<br>**i32 where unit belongs:** 125 of 292 `-> i32` fns only ever return 0 (130 of 297 at baseline, same script).<br>**ritzlib:** the kernel now imports ritzlib, but only `ritzlib.option` (×3). | #1885 |
| M11 | Dead code, second build system, forks | Major | PARTLY | **Deleted:** `arch/x86_64/syscall.ritz` (495 lines).<br>**Still present:**<br>- dead `interrupts.ritz`, `process.ritz`, `fs/namespace.ritz`, `fs/backend.ritz`, `fs/mod.ritz`, `mm/shm.ritz` and `mm/dma.ritz`, 1,719 lines with no production importer (grep);<br>- `build.py` (858 lines) and `ritz/ritz`;<br>- 4 dead linker scripts, `boot_highhalf.s` and `user/linker_spawned.ld`;<br>- `user/` (21 files);<br>- `docs/**/*.ritz` (1,132 lines, still the top 6× duplicate cluster);<br>- `ritz.toml:66` `sources = ["tests"]` (no such dir) and `[test.qemu]`.<br>**Dead code is still being edited:** 6 sweeps since review/4 edited uncompiled files (5597ffa3, ff364011, 0edfa98b, cefb327c, c532e019, cb35e7c4), and those edits cannot fail. | #1886 |
| M12 | Self-tests in boot path; faults skipped | Major | OPEN | **Moved, not fixed:** `postinit.ritz:245`, `:315-325` still runs the ELF, blk and DHCP self-tests on every boot.<br>**Faults still skipped:** `channel_close` "skip for now due to page fault" (`postinit.ritz:234-237`); `channel_debug_print` (`:241-242`).<br>**Heap checks:** 5 `heap_check()` calls remain in `main.ritz`. | #1887 |
| m1 | Stream-of-consciousness GDT comment; no sysretq | Minor | OPEN | The comment moved to `syscall/runtime/entry.ritz:51` ("Wait, this is wrong. Let me reconsider."). Every exit is still `iretq` (`syscall_entry.s:220`, `:270`, `:362`, `:420`). | #1887 |
| m2 | Magic numbers | Minor | OPEN | **Load base:** `0x100000000` ×3 (`main.ritz:209`, `process.ritz:156`, `:287`).<br>**Heap size:** `heap_init(16384)` is commented "64MB" (`main.ritz:367`).<br>**Trampoline:** `0x8FF0` (`apic.ritz:330`); ICR `0x8500` (`:362`).<br>**Struct sizes:** `uptr_check_*(…, 24/4096/16/8)` with no `sizeof` (`framebuffer.ritz:129`, `ipc.ritz:22`, `:29`, `:54`, `input.ritz:65`). | #1887 |
| m3 | Contradictory BSS handling | Minor | OPEN | `clear_bss()` at `main.ritz:249`, then "BSS might not be zeroed" at `:257-258`. | #1887 |
| m4 | Selective import doesn't filter | Minor | OPEN | `main.ritz:358` uses `vmm_pml4_phys`, which is absent from its `mm.vmm` import list (`:19`). | #1858 |
| m5 | SHA-256 constants as CC-65 if-ladder | Minor | OPEN | `get_k` is still 130 SLOC / CC 65 (`lib/sha256.ritz:88`), the only CC > 50 function left. | #1534 |
| m6 | UEFI glue in loader | Minor | PARTLY | **Fixed:** the `uefi_call*` shims are gone (05b9834a, 624a7895), and the `subq $40` cluster is gone from metrics.<br>**Open:** `setup_page_tables` still has the four PD-fill loops (`boot/src/main.ritz:605`, 99 SLOC; loops at `+58`, `+77`, `+95`, …). | #1884 |
| m7 | Makefile hides missing kernel | Minor | OPEN | `cp … 2>/dev/null \|\| true` at `harland/Makefile:43-44`. | #1886 |
| M13 | goliath loses nested writes | Major | OPEN | `update_dir_entry` repoints only the root (`goliath/src/namespace.ritz:258-260`), unchanged. Its tests still write root-level paths only. | #1881 |
| M14 | goliath hosted-only | Major | OPEN | `ritzlib.sys` is imported at `namespace.ritz:6`, `virtio_store.ritz:28`, `error.ritz:5` and `blob_id.ritz:6`. cryptosec is imported at `blob_id.ritz:7`. | #1881 |
| M15 | virtio_store a stub; store saturates | Major | OPEN | **virtio_store:** the TODOs are unchanged (`virtio_store.ritz:162`, `:179`, `:294`, `:346`, `:366`), and the magic is still "adjust as needed" (`:38`).<br>**Capacity:** `blob_store.ritz:190` "TODO: Grow array"; `namespace.ritz:272` "TODO: Implement deletion".<br>**Kernel copy:** the same "TODO: Grow" sits at `fs/kblob.ritz:168`. harland-main's growth fix (8e7b4c82) was not ported. | #1881 |
| m8 | goliath hand-typed sizes | Minor | PARTLY | **Obsolete part:** the `main.ritz:31` stray-byte write went when `main.ritz` was rewritten (d5b1deb9).<br>**Open part:** `320` is still used at `namespace.ritz:238` and `:249`. | #1881 |
| m9 | Hand-rolled vtables; i32 error codes | Minor | OPEN | `blob_store.ritz` `BlobStoreOps` and `error.ritz` constants are unchanged (metrics: no change outside `main.ritz`). | #1881 |

**Tickets whose acceptance the code fails** (checked against the code; AGAST was not queried):
- **#1879:** its asm grep fails (C3).
- **#1877:** its own red-first canary was never added, yet a new test asserts the workaround the ticket says to remove.
- **#1886:** the dead-module set shrank by one file.
- **#1887:** `kernel_main` is 212 SLOC, against a target of ≤ 80.

## Metrics delta

| metric | review/4 | now |
|---|---|---|
| harland files / SLOC / fns (ritz-metrics) | 84 / 15,181 / 974 | 98 / 15,216 / 1,009 |
| harland `.ritz` lines (all / `kernel/src`) | 25,002 / 21,357 | 25,031 / 21,349 |
| largest file | `kernel/src/main.ritz` 2,677 lines / 1,522 SLOC (> 1,500 Major) | `boot/src/main.ritz` 1,600 / 1,138; `kernel/src/main.ritz` 556 / 334 |
| fns > 300 SLOC (Critical) | 1 (`kernel_main` 388) | 0 |
| fns > 150 SLOC (Major) | 2 (`kernel_main`, `syscall_handler` 158) | 1 (`kernel_main` 212) |
| CC > 50 | 3 (`get_k` 65, `syscall_handler` 62, `kernel_main` 51) | 1 (`get_k` 65) |
| CC > 30 | 5 | 3 (`get_k`, `keycode_to_ascii` 36, `dhcp_handle_packet` 33) |
| depth ≥ 6 | 6 | 6 (same functions) |
| duplicate clusters | 118 | 108 (top cluster is still `docs/*.ritz`, 6×) |
| C-idiom smells (total / cstr / i32-as-bool) | 686 / 320 / 194 | 678 / 320 / 190 |
| inline `asm` blocks / `[[packed]]` | 65 / 42 | 45 / 42 |
| ritzlib imports in the kernel | 0 | 3 (`ritzlib.option` only) |
| dead kernel modules (lines) | ≈ 2,220 | 1,719 |
| always-0 `-> i32` fns (kernel + boot) | 130 / 297 | 125 / 292 |
| goliath files / SLOC / fns | 12 / 1,428 / 119 | 12 / 1,450 / 120 (only `src/main.ritz` changed) |
| goliath dup clusters / smells | 10 / 46 | 10 / 62 (+16 from the CLI stub's `c"..."`) |

## New findings

### F1. The kernel's runtime is not gated; the refactors are verified by source greps [architecture] — Major
- **Evidence:**
  - CI builds harland (`main.yml:74` `rz build --all`) but never boots it. `.github/workflows/*.yml` has no `qemu`, `OVMF` or boot-script step (grep).
  - `rz test harland` runs only `test/test_boot_fb.ritz`.
  - The seven `ritz/ritz0/test_harland_*.py` are source-text or IR scans. Each names a hand-run script as "the runtime check": `test_harland_syscall_runtime.py:26`, `test_harland_apic_module.py:20`, `test_harland_postinit_klog.py:22` (all → `tools/test_tier1_boot.sh`).
  - Boot scripts went from 3 to 4 plus a verdict helper: `tools/qemu-test.sh`, `tools/test_boot.sh`, `tools/test_tier1_boot.sh` (new), `boot/test.sh` and `boot/uefi_verdict.sh`.
  - `test_harland_syscall_runtime.py:218` asserts that the C1 workaround *exists*.
- **Impact:** about 12 harland commits since review/4 (2118–2752) shipped on structural checks alone. Nothing in CI would catch C1-class corruption or a boot regression.
- **Fix direction:** one boot gate (`test_tier1_boot.sh`, which takes `SKIP_BUILD`/`BOOT_TIMEOUT`) as a CI job. Delete the other three scripts. Turn the source-scan tests that pin workarounds into red tests for #1877. Extends #1886's "merge boot-test scripts" criterion.
- **Ticket:** #1845 (existing).

### F2. Threshold hits review/4 left unclassified [cleanup] — Major
- **Evidence:** these are over the v4 defaults with no finding or justification in either review:
  - `keycode_to_ascii` CC 36 (`drivers/virtio/input.ritz:408`);
  - `dhcp_handle_packet` CC 33 (`net/dhcp.ritz:233`);
  - depth 7: `elf_load` (`loader/elf.ritz:204`) and `vmm_reserve_page_tables` (`mm/vmm.ritz:633`);
  - depth 6: `kalloc` (`mm/heap.ritz:116`), `vmm_free_user_pages` (`mm/vmm.ritz:689`) and `vfs_find_fs` (`fs/vfs.ritz:183`).
- **Fix direction:**
  - `keycode_to_ascii`: a `[N]u8` scancode table.
  - `dhcp_handle_packet`: split it into an option parser and a per-message-type handler.
  - `elf_load`: split out per-segment mapping (this pairs with the #1888 bounds checks).
  - The vmm/heap loops: early `continue`, or one helper per table level.
- **Ticket:** #3457.

### F3. harland-main is a stale fork that still holds unported fixes [architecture] — Minor
- **Evidence:** there are 21 unmerged commits from 2026-02-20 to 21, and review/4 said to land #1839 first. main re-ported only the split and the PMM, dd and resume fixes. Not on main:
  - per-pid fd context (ed89529c, 169+/70−);
  - kblob growth (8e7b4c82; main still has "TODO: Grow", `fs/kblob.ritz:168`);
  - scheduler CPU/task bounds (a0e23c79);
  - fault/initramfs hardening (0eda5329);
  - fd capacity (7d8658ec);
  - getpid path (242fdc09);
  - init exit via ACPI (86f03bb6).
- **Fix direction:** triage each commit into a ticket or reject it, then delete the branch so there is one kernel line.
- **Ticket:** #3458.

### F4. `main.ritz` imports 300 names, 210 of them unused [cleanup] — Minor
- **Evidence:** this was checked by script: every brace-import name in `main.ritz` was matched against the file body. 210 never appear, including `tasks`, `cpu_sched`, `scheduler_lock` and `timer_handler` (`main.ritz:66-73`) and most of `io`, `serial` and `pci` (`:15-17`). The modules split out of main import none they don't use: `postinit.ritz` 0 of 32, `process.ritz` 0 of 26, `apic.ritz` 0 of 17.
- **Impact:** the import list overstates main's coupling to the scheduler (M2's layering evidence) and hides what main really depends on.
- **Fix direction:** trim the list. Add an unused-import diagnostic or lint so splits can't leave this behind.
- **Ticket:** #3458.

### F5. Eight open-coded `asm pause` blocks; `io.ritz` has no `cpu_pause()` [cleanup] — Minor
- **Evidence:**
  - `serial.ritz:94`, `:229`, `:411`
  - `sched/mod.ritz:111`
  - `drivers/ena/device.ritz:235`, `:553`
  - two more in `arch/x86_64/apic.ritz` (`:258`, `:281`)

  `io.ritz` exports `halt` and the barriers but no pause (`io.ritz:65-146`).
- **Fix direction:** add `io.cpu_pause()` and replace the eight blocks. That also clears most of #1879's non-arch asm-grep failures (C3).
- **Ticket:** #3458.

### F6. Stale comments left by the split and the ABI work [cleanup] — Minor
- **Evidence:**
  - `syscall/numbers.ritz:10` says handlers are "registered in main.ritz (syscall_table_init)". It is at `syscall/runtime/entry.ritz:128`.
  - `main.ritz:6` says "All hardware interaction uses native Ritz inline assembly". `main.ritz` has 0 asm blocks.
  - `process.ritz:441-443` still blames a struct-return "compiler bug", which C1 explains otherwise.
  - The `entry.ritz:51` monologue (m1).
- **Ticket:** #1887 (existing).

### F7. `projects/goliath/goliath` is a tracked symlink into `build/` [cleanup] — Minor
- **Evidence:** `git ls-files -s projects/goliath/goliath` gives mode `120000` → `build/debug/goliath`, added by 0879eb0a ("prism tests green"). It dangles in a clean checkout.
- **Fix direction:** delete it and ignore `projects/*/<name>` build links.
- **Ticket:** #2199 (existing).

## Not findings

- **review/4 C2 correction.** `indium/user/mmap_test.ritz` does catch the −1 return. The `== 0` check misses it, but the range check `(ptr as i64) < 0x10000000` (`:22`) fails on −1 with exit 2. The −1/null mismatch is still untidy; it is not a blind test.
- **`docs/hardware/thinkpad-p16-gen2/`** (1.2 MB of ACPI tables and lspci dumps, dd76c65d). These are binaries in git, but they are reference input for M2.4 NVMe/MSI-X bring-up, not build artifacts.
- **`syscall/dispatch.ritz`'s 256-entry handler table.** This is a fixed-capacity global, but it is sized by the ABI's number space (`numbers.ritz` 0..255) and not by a guessed `MAX_*`.
- **NVMe and MSI-X are still absent** (grep finds only ENA/virtio constants). This is milestone scope (M2.3/M2.4), not a design finding, as in review/4.
