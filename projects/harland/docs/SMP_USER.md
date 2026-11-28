# Harland SMP: Application Processors Run User Processes

| | |
|---|---|
| Status | Decided (AGAST #4874; §2-§4 revised by #4879: no big kernel lock). Implemented by #4879, #4880 and #4881 |
| Date | 2026-11-27 |
| Audience | Harland kernel |
| Drives | M2.9b #4872: netd on a dedicated core (#4877). Real hardware: the Acer has 8 threads, the ThinkPad 28 (#1853) |

## Today

- **APs boot and idle.** `arch/x86_64/apic.ritz ap_entry` brings each AP up with `percpu.ritz cpu_bringup`: its own GS area, TSS (rsp0 and IST1-5), IDT and SYSCALL MSRs, and six guard-paged stacks. It runs the per-CPU syscall-stack self-test (`cpu_smp.ritz`, #4192), then idles in `sti;hlt` on its IST1 stack. Interrupts stay on, so #4220's AP-call IPI (vector 240, `apcall.ritz`) and CPU-local MSI-X still reach it. The AP's LAPIC timer is masked.
- **One CPU runs processes.** The BSP does. `proc/sched.ritz` says the kernel "is not preemptible, so its globals need no locks". Syscalls run with IF=1 (`syscall_entry.s` does `sti` before `syscall_handler`). IRQ handlers interleave with syscalls only on the same CPU, and the shared state they touch is guarded by `cli` (`waitset_collect`, `sched_block`).
- **Code that already assumes the BSP:**
  - `proc/waitq.ritz waitq_can_park` and `proc/waitset.ritz` (three `lapic_is_bsp` gates). "A latch on another CPU is recorded but wakes nobody."
  - `apic.ritz`'s LAPIC watchdog.
  - `mm/dma_runs.ritz` ("running on the BSP, so there is no lock").
  - `drivers/iommu/vtd.ritz` ("only the BSP calls").
  - The `mm/shm.ritz` and `cap/table.ritz` tables ("take no lock").
- **The process table has a single current slot.** `proc/table.ritz proc_cur` and `fs/syscall.ritz fs_current` are single globals. An exiting process idles on its own kernel stack in `sched_exit` until something is runnable.
- **No FPU/SSE state is saved on a switch** (no `fxsave`/`xsave` in `proc_switch.s`). This is a gap already on one CPU. Pinning neither adds to it nor fixes it.

## Decisions

### 1. First step: pinning, not per-CPU run queues

**Decision: pinning.** Every process has a home CPU (`Proc.home`, a `cpu_map` index). A CPU runs only processes whose home it is. There is no load balancing and no migration: a forwarded syscall (§2) carries the process to the BSP in kernel mode and back, but its user code runs only on its home. Processes default to the BSP, including children of a process homed on an AP. The kernel alone places a process elsewhere (§5). There is no user affinity syscall yet.

What each option needs:

| Piece | Pinning | General per-CPU run queues |
|---|---|---|
| Ownership map and mailboxes (§2) | yes | yes |
| Per-CPU current slot, idle context per CPU | yes | yes |
| Lock-free wake and kick IPI (§4) | yes | yes |
| Owner-side unmap (§3) | yes | yes |
| Pick filtered by CPU | one `on == cpu` test in `proc_pick_next` (`on` is the home except during a forwarded syscall, §2) | a queue per CPU, kept consistent with the proc table |
| Placement policy | the kernel names a CPU at spawn | a policy for every spawn and wake (least loaded, cache-warm, ...) |
| Load balancing | none | periodic or idle-time stealing, with its locking |
| Migration | none | moving a blocked or runnable process between CPUs. That means FPU state that follows it (missing today), TLB/PCID state of the old CPU, and a home, and with it the owner of the process's rows (§2), that changes under a concurrent wake |
| Tick | only on a CPU with two or more homed processes | on every CPU that has work |

Everything pinning needs, run queues need too. Run queues add three things with their own correctness problems: a placement policy, a balancer and migration. So pinning is a strict subset, and the first step. The way out is additive. `home` stays a pinned process's CPU, and a later "floating" class (`home = ANY`) is what a balancer moves. The netd use case never wants to float.

With `MAX_PROCS = 8` the table is small enough that "per-CPU queue" is a filtered scan of the one table, so pinning needs no new data structure.

### 2. Kernel concurrency: per-CPU ownership and cross-CPU messages

**Decision (Aaron, 2026-11-27): no big kernel lock.** Every piece of kernel state has one owner CPU, and only its owner writes it. Another CPU that needs a change sends the owner a message: a per-CPU mailbox plus a kick IPI, which is #4220's AP call generalised. Three things are deliberately not owned:

- **The wake path is lock-free** (§4). A process's state is one atomic word, and a wake is a CAS on it.
- **The frame allocator** keeps a cache per CPU, refilled from and returned to the global pool in batches under one leaf lock.
- **The log** (`klog` and the `serial` output ring) has one leaf lock, so lines from two CPUs never interleave mid-line.

This keeps today's invariant where it matters. Owned state is written by one CPU, which is not preemptible in the kernel, so the code that touches it keeps its current reasoning: "no lock, because one CPU". What changes is *which* CPU, and the rule that no other CPU writes it.

#### The inventory and its owners

These are the globals an AP-resident process reaches through its syscalls, IRQs and faults. They come from module-level `var`s in `kernel/src` (about 60 files have them). "Home" is the home CPU of the process the row belongs to (§1). The BSP owns every shared row: today it runs everything, so those rows keep exactly their current code.

| Subsystem | Globals | Reached by | Owner |
|---|---|---|---|
| Process table, shared part | `proc/table.ritz procs[8]` slot allocation, pids, parent links, exit codes, `proc_next_pid` | spawn, exit, wait | BSP |
| Process table, per-process part | a slot's saved context, kernel stack, `fs_procs[pid]`, its cap table, its PML4 | that process's syscalls and faults | the CPU the process is **on**: its home, or the BSP during a forwarded syscall (below) |
| Process state | the slot's state word | every wake, block and switch | none: an atomic word with fixed transitions (§4) |
| Current slot, idle context | `proc_cur`, `fs_current`, and the new idle context | every switch | each CPU its own (`percpu.ritz`) |
| Scheduler | `proc/sched.ritz` counters and `sched_running` | every switch, every tick | each CPU its own |
| Wait sets | `proc/waitset.ritz irq_objects`, `shm_latches`, `inbox`, `waitset_deadline`, `waitset_console` | DrvIrqWait, ShmWait, ShmNotify, MSI-X dispatch, COM1 IRQ, tick | an IRQ latch: the home of the IRQ's owner, where its MSI-X is aimed. A shm latch's sequence: none (atomic, §4). Its waiter registration: the waiter's home. Deadlines and the console: BSP |
| SHM | `mm/shm.ritz shm_objects`, `shm_maps`, `shm_cursors` | ShmCreate/Map/Detach, retire, detach timeout (tick) | BSP. An unmap from a space homed elsewhere is a request to that home (§3) |
| Capabilities | `cap/table.ritz cap_tables[64]` | every handle lookup, grants | a table: the CPU its process is on. A grant into a table on another CPU is a `CAP_INSERT` message to that CPU |
| | `irq_cap_owners` | DrvClaim, IRQ routing | BSP |
| Frames | `mm/pmm.ritz` bitmap, `pmm_free_pages`, `pmm_next_free` | every map, spawn, exit, DMA | the global pool: none (leaf lock `pmm_lock`). The per-CPU caches: each CPU its own (below) |
| Page tables | every user PML4 | map/unmap, spawn, exit, shm, DrvDma | the CPU its process is on |
| | the kernel half (PML4[256..511]), `mm/vmm.ritz g_mmio_next` | boot, MMIO maps | BSP; changes broadcast (§3) |
| Kernel heap | `mm/heap.ritz heap_free_list` | fs, drivers, channels | BSP. No path that runs locally on an AP allocates from it |
| DMA / IOMMU | `mm/dma.ritz`, `mm/dma_runs.ritz`, `drivers/iommu/vtd.ritz`, `amdvi.ritz` | DrvDma alloc/free, driver death | BSP |
| Driver seats | `syscall/runtime/driver.ritz drv_devices` | DrvClaim, DrvIrqWait | BSP. DrvIrqWait reads only its own cap table and IRQ latch |
| Net seat | `syscall/runtime/net.ritz`: `addr_snapshot`/`addr_generation` (NetAddr), `link_snapshot`, `exchanges[16]`, the service ids | NetPublish, NetAddr, NetInfo, the app exchange, netd restart | BSP |
| IPC | `ipc/channel.ritz channels[256]` | channel syscalls | BSP |
| fs / tty | `fs/syscall.ritz fs_procs` (shared part); `fs/kfs.ritz`, `vfs.ritz`; `tty/ldisc.ritz`; `serial.ritz` input buffers | read/write/open, console IRQ | BSP |
| Log | `klog.ritz ring_buffer`, `ring_head`, the console sink; `serial.ritz` output ring | everywhere, including IRQ, NMI and panic | none: leaf lock `klog_lock` |
| Dispatch | `syscall/dispatch.ritz g_syscall_count` | every syscall | each CPU its own count. `syscall_count()` sums them |
| In-kernel drivers | `drivers/nvme`, `virtio/blk`, `virtio/net`, `ena` queue state; `drivers/usb` (xHCI + HID keyboard, `USB.md`) controller, slot, ring and HID state | fs syscalls, the in-kernel net stack; for `drivers/usb`, its MSI-X vector (aimed at the BSP), the BSP tick's polled fallback and the console it feeds | BSP. The block and net drivers are lent to an AP for one AP call (the survey's point 2 below). `drivers/usb` is never lent |

#### Which syscalls run on the AP

The dispatch table gets a per-syscall flag, `SYS_LOCAL`. On the BSP every syscall runs locally, exactly as today. On an AP a `SYS_LOCAL` syscall runs there. Every other syscall is **forwarded** to the BSP. The list is an allowlist, so a new syscall is forwarded until someone shows it touches only its caller's rows.

| Runs locally on an AP (`SYS_LOCAL`) | Why it is safe |
|---|---|
| Getpid, Yield | its own slot and its CPU's scheduler |
| ShmWait, ShmNotify | the latch sequence and the state word are atomic (§4). The waiter registration is the waiter's own |
| DrvIrqWait | its own cap table and its IRQ latch, owned by its home (MSI-X is aimed there, §5) |
| CapInfo, CapCheck, CapDerive | its own cap table |
| Mmap, Munmap | its own PML4, and frames from its CPU's cache. Only the CPU the process is on loads that PML4 (§3) |
| DebugPrint | `klog_lock` |
| Smp (254) | the #4192 self-test barrier. Every CPU is spinning in that handler, the BSP included, so a forwarded call would never be served (the survey's point 1) |
| SmpUserLocal (252) | the smp-user boot test's local half (§6): it bumps only its CPU's own counter. Its forwarded twin, SmpUser (253), bumps a BSP-owned one |

Everything else is forwarded: Exit, the fs and tty syscalls, Spawn/SpawnArgs/SpawnBg/Wait, IPC and channels, CapGrant/CapRevoke, Input, Fb, Drv{MmioMap,DmaAlloc,DmaFree}, the Net seat (NetInfo, NetAddr, NetPublish, NetAttach), ShmMap, Sync, AcpiPoweroff. None is on netd's echo path (#4877).

**How a forwarded syscall runs: the process goes to the BSP.** A forwarded handler must be able to block (Wait, a tty read), so it cannot run in an IRQ or as a message handler. It runs in the caller itself, on the caller's own kernel stack, which moves to the BSP for the syscall:

1. On the AP, `syscall_handler` sees no `SYS_LOCAL`. It saves the caller's context and switches to the AP's idle context (or another process homed there). Because the outgoing process is leaving this CPU, the switch loads the kernel PML4 instead of keeping a lazy CR3. Only then does the AP set the slot's `on` field to the BSP and post `FORWARD{pid}`.
2. The BSP takes the message at a safe point and makes the process runnable there. Its normal pick switches to it: its CR3, its kernel stack, its TSS `rsp0`. The process continues inside `syscall_handler` and runs the handler, blocking and waking on the BSP like any BSP process.
3. When the handler returns, the process sets `on` back to its home and switches away on the BSP. That switch also loads the kernel PML4 if the BSP has nothing else to run. The BSP then posts `RETURN{pid}`. The home picks it, loads its CR3 and returns to user.

So a process's per-process rows are owned by the CPU it is **on**: its home, except during a forwarded syscall, when it is the BSP. A space is loaded only where its process is on, so the BSP's unmaps during a forwarded call are local `invlpg`s and the freed frames go straight to the BSP's cache. Only one CPU holds the process at a time: the sender is off its stack and out of its space before it publishes the move. User code runs only on the home. The kernel uses no FPU/SSE, so the user's FPU registers are not touched by the move (the missing save on a switch is the existing gap, see "Today").

The cost is two kicks, two switches and two CR3 loads per forwarded syscall, none of them on netd's echo path.

**Exit and kills** are forwarded: the process moves to the BSP and exits there exactly as today, so its address space and kernel stack are freed by the BSP, which owns the shared slot. A fault that kills an AP process forwards it in the same way. `sched_exit` ends on the BSP's idle context, so a process never idles on its own stack again.

#### The mailbox

One mailbox per CPU: a multi-producer, single-consumer ring of 16 slots of 64 bytes (one cache line each), in `kernel/src/sync/mbox.ritz`:

```
slot: seq u64 | kind u32 | from u16 | flags u16 | pid u64 | arg[5] u64
```

- **Kinds:** `CALL` and `CALL_DONE` (the AP call, #4879); `UNMAP`, `UNMAP_DONE`, `KERNEL_INVLPG` and `KERNEL_INVLPG_DONE` (#4880); `FORWARD`, `RETURN` and `CAP_INSERT` (#4881).
- **Posting** (Vyukov's bounded queue). A producer reserves ticket `t` with `lock xadd` on the ring's tail. It waits until `slot[t % 16].seq == t`, writes the body, then stores `seq = t + 1`. Under x86 TSO stores retire in program order, so the plain store of `seq` after the body is the release. The code still needs a compiler barrier between them.
- **Taking.** The owner reads `slot[head % 16].seq`. It equals `head + 1` once the slot is published. The owner copies the body out, then stores `seq = head + 16` to free the slot. Freeing before the copy would let a producer overwrite the body the owner is still reading.
- **Order:** FIFO by ticket, so FIFO per producer.
- **Never full, by construction.** Each process has at most one `FORWARD` or `RETURN` in flight, and only the BSP sends requests, one at a time, so a mailbox holds at most `MAX_PROCS + 2` messages. 16 covers that, and the producer's wait for a free slot is an assertion (`[mbox] full`), not a path.
- **The kick.** After posting, the producer runs `mfence`, then sends the owner vector 240 (today's AP-call vector, renamed `KICK_VECTOR`), unless the owner is this CPU. The fence matters in x2APIC mode: the kick is a `wrmsr` to the ICR, which is not ordered after the post's plain stores, so without it the owner can take the kick, find the slot unpublished and halt for good (`test_smp_proto.ritz` finds this; its step is `kick.fence`). The handler sends EOI and sets `pc_kick_pending`; it never drains in the IRQ. The mailbox is drained at the owner's next safe point: in #4879 that is the idle loop, whose `hlt` the kick ends. Draining at return to user (a pinned process spinning in user mode) comes with #4881. Running a `CALL` from the idle loop rather than the ISR also means no ISR is in service while the callee waits for its own device interrupt.
- **Safe points:** return to user, the idle loop, and a block. Never in the middle of kernel code, because a message mutates owner state that the interrupted code may be halfway through changing. This is what makes "only the owner writes" hold against the owner's own IRQs too. Every message handler is short and never blocks: it queues a process, inserts a capability, edits PTEs or runs one AP call.

**No deadlock.** Only the BSP ever busy-waits for another CPU: for a `CALL` result, and from #4880 for `UNMAP_DONE`. While it waits it takes only replies addressed to its own request, IF=1, and its own IRQs run. An AP never busy-waits on another CPU. A forwarded caller leaves the AP, which goes on to idle, a safe point, so the BSP's requests are always served. With no cycle of waiters there is no deadlock.

#### The AP call on the mailbox (the survey's point 2)

`apcall.ritz ap_call_one` posts `CALL{kind}` and waits for its reply. The callee (today `nvme_ap_probe`) uses BSP-owned state: the heap, the NVMe queue state and the serial log. So the BSP *lends* those rows for the call: its wait loop touches nothing but its own mailbox and `cpu_pause`, as it does today. Under a big lock the BSP would have had to release the lock for the wait, and "0 contended" in the boot log would depend on timing. Here there is no lock, so nothing can contend.

#### Non-local exits (the survey's point 3)

`syscall_entry.s smp_test_resume_bsp` returns from a syscall handler straight into boot code. `arch/x86_64/sysret_catch.ritz` does the same from a user fault. A big lock held across entry would leak from both. Under ownership nothing is held across an entry. The one rule: entry keeps no per-CPU state that the exit must unwind. Any later per-CPU depth counter is reset by `smp_test_resume_bsp`. `klog_lock` is never held at a user fault or a syscall exit, so neither path can leak it.

#### The leaf locks

- **`klog_lock`** (`klog.ritz`) covers the ring, COM1 (klog's polled output, and the output ring that `sys_write` fills and the COM1 IRQ drains, through `klog_serial_write`/`klog_serial_drain`) and the console sink (`klog_console_start`, #4868). It is a ticket spinlock taken with IF saved and cleared. One `klog` call is atomic: a line built from several calls can interleave with another CPU's at call boundaries, never inside one. A kernel panic calls `klog_emergency`, after which klog takes the lock only if it is free and writes anyway, so a CPU that died holding it cannot silence the report. The lock is written out in `klog.ritz` rather than taken from `sync/spin.ritz`, so klog stays a leaf: the host tests that log compile klog, serial and io alone.
  - **The host tests (the survey's point 4).** Every host test that logs runs klog as an ordinary user program, where `cli` faults. So the lock's IF save is a switch, `klog_irqsave`, like `drivers/display/fbcon.ritz fbcon_irqsave`, but it starts off: `kernel_main` turns it on as its first step, while IF is still clear. No host test has to remember to turn it off.
- **`pmm_lock`** (`mm/pmm.ritz`, a `sync/spin.ritz` ticket lock) covers the global bitmap and its hints. It is held only for one batch (below) or one `pmm_alloc_contig`/`pmm_alloc_page_high`, never across anything else.

Lock order, outermost first: `pmm_lock` → `klog_lock` → the console's own lock (`fbcon_write` takes it inside the console sink). Nothing else is taken while holding `klog_lock`.

#### Per-CPU frame caches

- **Size.** A stack of up to 64 frames (256 KiB) per CPU, in its per-CPU area.
- **Alloc.** `pmm_alloc_page` pops from this CPU's cache. An empty cache refills 32 frames from the global pool under `pmm_lock`, in one bitmap pass from `pmm_next_free`.
- **Free.** `pmm_free_page` pushes onto this CPU's cache. A cache past 64 returns its oldest 32 to the global pool in one locked pass.
- **Bypass.** `pmm_alloc_contig` and `pmm_alloc_page_high` (DMA, page-table placement) always go to the global pool under the lock.
- **Exit.** Exit is forwarded (§2), so the BSP frees the address space into its own cache, and overflow goes back in batches. An AP's cache changes only through its local Mmap/Munmap and page faults. netd's rings live as long as netd, so its AP's cache sits near empty and refills only at start-up.
- **Accounting.** `pmm_get_free_pages` reports the global count plus every cache's depth. That is a racy sum, fine for the log and the tests. Fault injection (`pmm_fail_allocs_after`) counts at the cache API, so it still fails the Nth allocation whatever cache it came from.

#### The cpu-index hook (the survey's point 5)

`proc_cur`, `fs_current`, the frame caches and the dispatch count are per CPU, so `proc/table.ritz`, `fs/syscall.ritz`, `mm/pmm.ritz` and `syscall/dispatch.ritz` need this CPU's index. Each declares `extern fn cpu_index() -> i32`, the way `proc/waitset.ritz` declares `lapic_is_bsp`; `proc/table.ritz` also declares `sync/idle.ritz cpu_kick_if_idle` for its wakes. The kernel supplies `percpu.ritz cpu_index`, which answers 0 until the BSP's GS base is set (only the BSP runs before that, and an AP calls none of these before its own `cpu_bringup`). Each per-CPU slot stores its value plus one, so the zeroed BSS reads as "none" before anything is set.

Every host test that compiles one of those modules supplies the stubs. The pytest harnesses (`projects/ritz/ritz0/tests/test_harland_{process_model,fd_tables,waitset,tty,syscall_dispatch}.py`, and `errno` through `syscall_dispatch`'s runner) append a `CPU_HOOKS` block to the program they build; `process_model`'s makes the CPU index and the kicks visible to its test. harland's `test/test_cap_policy.ritz`, `test_cap_device.ritz`, `test_dma.ritz`, `test_pmm_mb2.ritz` and `test_pmm_cache.ritz` define them directly. `fs/syscall.ritz`'s one `extern fn` is this arch hook: the fs layer still never asks the process layer who runs (`test_harland_fd_tables.py` pins both).

#### Alternative considered: a big kernel lock

A recursive ticket spinlock (`klock`) taken at every asm → Ritz entry and released at every `hlt`. It keeps every subsystem's reasoning unchanged with almost no audit, which is why #4874 chose it first. Rejected because:

- **It ties netd's latency to the BSP's slowest kernel path.** netd on a dedicated core (#4877) still enters the kernel to sleep and to wake. While the BSP holds `klock` through a long syscall (an fs read over NVMe), a device poll with a deadline (`nvme_q_lock`, the AP call's 10 s wait) or a burst of boot-time work, netd's AP spins. That moves the very jitter the dedicated core exists to remove.
- **The AP call (point 2) and the non-local exits (point 3)** each need a special release path. Without one, the lock leaks or the boot log's contention count depends on timing.
- **Leaving it is a long series of carve-outs** (heap, frames, the wake path, a per-syscall opt-out), each needing a measured counter to justify it. Ownership puts the hot paths (wake, frames) in their final shape now. Only the rows an AP actually touches need any thought, and the rest stay BSP-owned with today's code.

The cost of the decision: forwarded syscalls pay a round trip (two kicks, two switches, two CR3 loads), and the `SYS_LOCAL` list must be justified row by row. Both are off netd's echo path.

### 3. Address-space changes across CPUs (owner-side unmap)

With pinning and ownership, a user address space is loaded only on the CPU its process is on (§2). A CPU that a process leaves loads the kernel PML4 before it publishes the move. Without PCID a CR3 load flushes, and harland never sets `PTE_GLOBAL`. So only one CPU can hold a user space's translations, and an unmap needs no broadcast shootdown. It needs the **owner** to do it.

The cases that unmap from a space homed elsewhere:

- **`mm/shm.ritz shm_detach_expired` and retire** unmap a holder's mapping, and the holder (netd) may be live on its AP.
- **`syscall/runtime/driver.ritz`'s unmap and quarantine of DMA/MMIO leaves** (`vmm_unmap_page_in`, `vmm_quarantine_page_in`) at driver death touch the driver's PML4, and after #4875 the driver is netd.
- **The kernel half** (PML4[256..511], shared by every address space) is live on every CPU. `vmm_unmap_kernel_page` today runs only at boot (guard pages), but any later kernel-half unmap must reach all CPUs.
- **Lazy CR3.** A CPU that goes idle keeps the last process's CR3 loaded when that process stays on it, so netd waking on the same CPU costs no CR3 load. Its PML4 must not be freed while it is still loaded.

Design (#4880, in `kernel/src/mm/tlb.ritz`):

- **Owner-side unmap on request.** The BSP posts `UNMAP{pid, va, pages}` to the CPU the process is on. That CPU handles it at a safe point: it clears the PTEs, then runs `invlpg` for up to 32 pages if the space is loaded there, or reloads CR3 beyond that. Then it posts `UNMAP_DONE`. The BSP waits for it, and *only then* returns the frames to the PMM (they belong to shm and driver objects the BSP owns). If the process is on the BSP, the unmap is local, as today.
  - The entry point is `tlb_unmap_on(cpu, pid, pml4, va, pages, mode)`, `mode` `TLB_CLEAR` or `TLB_QUARANTINE`. `mm/shm.ritz shm_clear_leaves` (ShmMap's rollback, CapRevoke's `shm_unmap`, `shm_detach_expired`) and `syscall/runtime/driver.ritz unmap_run`/`quarantine_leaves` (DrvDmaFree, exit's `drv_dma_process_end`, `driver_quiesce`) call it with `proc/table.ritz proc_on_cpu(pid)`, which is the BSP for every process until #4881 adds `Proc.on`.
  - The message carries the PML4 itself (`arg[1]`), so the owner looks nothing up. Its edit uses the no-flush walkers `vmm_clear_leaf_in`/`vmm_quarantine_leaf_in`, then flushes once. `vmm_unmap_page_in` and `vmm_quarantine_page_in` now `invlpg` only when the PML4 is the one loaded on this CPU.
  - The wait has no deadline. Giving up would free a frame another CPU may still reach, so a slow owner gets one `[tlb] still waiting for ...` line and the BSP keeps waiting. This cannot deadlock (below).
- **A move during the request is harmless.** The process may forward to the BSP after `UNMAP` was posted. Its old CPU already dropped the space before it posted `FORWARD`, so it can still edit the PTEs and needs no `invlpg`. The BSP is waiting and takes only `UNMAP_DONE`, so the process cannot run anywhere until the edit is done.
- **The lazy-CR3 drop at exit.** Exit is forwarded, so the home dropped the space when the process left it (§2). The BSP frees it after its own switch away from the exiting process loads another CR3 or the kernel PML4. No cross-CPU "drop" message is needed. `PC_ACTIVE_PML4` per CPU, written on every CR3 load, lets `vmm_free_pml4` assert that no CPU still has the victim loaded.
  - `mm/vmm.ritz pc_active_pml4[cpu]` is written by `vmm_switch_pml4` (every CR3 load goes through it) before the load, by `vmm_init` on the BSP and by `vmm_cpu_init` on an AP (`ap_entry`; the trampoline loads `vmm_kernel_pml4()`). `vmm_get_current_pml4()` reads this CPU's slot, and `vmm_pml4_loaded_on(pml4, except)` scans them all.
  - The walkers' "current table" is per CPU too (`vmm_pml4_phys()`, formerly one global). A `vmm_*_in` call on an AP points only that CPU's walkers at its table, and `vmm_set_walk_pml4` points them without a CR3 load (the host tests).
  - `vmm_load_kernel_pml4()` is the drop: the CPU a process leaves calls it before it publishes the move. Exit already switches to the kernel's PML4 before it frees (`sys_exit_impl`). #4881's FORWARD and RETURN use the same call.
  - The assert does not panic. `vmm_free_pml4` of a PML4 still loaded anywhere (or of the kernel's) logs `[vmm] vmm_free_pml4: PML4 0x... is still loaded on cpu N: not freed` and leaks the tree rather than free it under a live CR3. `tools/test_tier1_boot.sh` fails a boot on that line.
- **Kernel-half unmaps** post `KERNEL_INVLPG{va, pages}` to every started CPU and wait for every acknowledgement before the frame is reused.
  - The entry point is `tlb_unmap_kernel_page(va)`: `vmm_unmap_kernel_page`, which flushes this CPU, then `tlb_kernel_shootdown`. That posts to every CPU first, so they flush in parallel, then takes the acks in any order, each one settling its CPU's request. It asks for a full flush (`pages` 0), because the unmap may have split a 2 MiB page.
  - The boot-time guard pages (`percpu.ritz cpu_stack_alloc`, `syscall/stack.ritz`) stay on plain `vmm_unmap_kernel_page`. Their frames are never reused, and the CPU a guard protects has not started yet, so it loads CR3 afresh. An AP that started earlier is still waiting in `smp_ap_run`, not at a safe point, so it could not answer a `KERNEL_INVLPG`.
- **Harland never sets `PTE_GLOBAL`.** A global entry survives the CR3 load that the lazy-CR3 drop and every flush above rely on. `test_harland_tlb.py` pins that nothing in `kernel/src` uses it.
- **No deadlock.** As in §2: only the BSP waits, and an AP serves its mailbox at every safe point. A netd spinning in user mode is reached by the kick, which drains the mailbox when it interrupts user mode.
- **Mapping needs no message.** x86 caches no not-present translations, so adding a mapping is never shot down. That is why ShmMap and DrvMmioMap can run forwarded: the process is on the BSP, and the BSP owns its space for the call. `vmm_map_page` flushes only when it replaces a present leaf or adds `PTE_USER` to a present upper entry. The boot test below depends on that: its second map must not flush on its own.

**PCID (#4878, parked).** With PCID a CR3 switch keeps the old space's tagged entries, so "dropping" a space no longer flushes it. A forwarded process would leave tagged entries on both its home and the BSP. PCID therefore needs a sticky per-space mask of the CPUs that tagged it, and a stale mark that a CPU acts on at its next load of the space (a flushing CR3 write or INVPCID). `PC_ACTIVE_PML4` stays separate from that mask for this reason.

### 4. Wake-ups across CPUs: lock-free

**The state word.** Each process slot's state is one 64-bit atomic word: `{generation: u32, state: u32}`. The generation is bumped each time the slot is reused, so a stale waker cannot wake a slot's next process. Transitions:

| Transition | Who | How |
|---|---|---|
| (new) → RUNNING | BSP at spawn | fill the slot (`on = home`), then publish the word with a locked store, then kick the home |
| RUNNING → BLOCKED | the process itself, on its home | `xchg`, then re-check its wait condition (below) |
| BLOCKED → RUNNING | any CPU (a waker) | `lock cmpxchg` on the whole word. A failed CAS means the process was already RUNNING or the slot was reused: nothing to do |
| RUNNING → ZOMBIE | the process itself, on its home | `xchg` (§2 "Exit") |

**Every wait loops on its condition.** A process that blocks re-checks what it waits for after it is woken, so a spurious wake (two wakers, or a wake meant for an earlier wait) costs one re-check, never correctness.

**Process-level sleep (eventcount).** ShmWait(handle, seen): register as the latch's waiter, `xchg` the state to BLOCKED, then re-read the latch's sequence. If it is no longer `seen`, CAS back to RUNNING and return. Otherwise switch away.

**The notifier.** ShmNotify is a locked RMW on the latch (`lock xadd` on a sequence; today's shm latches OR event bits in with `lock or`, the same kind of op), then a CAS of the registered waiter BLOCKED → RUNNING, then a kick if the waiter's CPU (its `on`) is idle (below). The IRQ latches (`irq_objects`) follow the same pattern, with MSI-X dispatch as the notifier. On TSO both sides do a locked RMW between their store and their load, so at least one side sees the other's store: the sleeper sees the new sequence, or the notifier sees BLOCKED. No wake-up is lost. With a plain store for the sleeper's announce (or the idle CPU's, below), x86's store buffer lets both miss. The notifier's bump needs no lock for this: its `notify.wake` CAS is a locked op that drains the bump before it reads the state, so the model finds no lost wake with a plain bump. It stays locked so two notifiers' bumps both count.

**CPU-level sleep.** Each CPU's idle loop does the same handshake against its own work:

1. With IF=0, `xchg pc_idle, 1`.
2. Re-check: any process on this CPU RUNNING, or the mailbox non-empty? If so, set `pc_idle = 0` and run it.
3. Otherwise `sti; hlt`. A kick sent after step 1 is held pending while IF=0. `sti`'s interrupt shadow delivers it right after `hlt` starts, so it is never lost.

A waker that made a process on another CPU RUNNING reads that CPU's `pc_idle` after its CAS, which is a locked op and therefore a full barrier. It sends the kick only if `pc_idle` is 1. Mailbox posts always kick (§2), because they are rare.

**Consequences:**

- A process that is already RUNNING gets no IPI. A wake to a busy CPU (not idle) sends none either: the process runs at that CPU's next pick. netd spinning in user mode is therefore never interrupted by notifies it does not need.
- The BSP-only gates go away. The three `lapic_is_bsp` tests in `waitset.ritz` become "CAS the owner, kick its CPU if idle", and `waitq_can_park` becomes "a current process on this CPU and not inside an IRQ handler", which keeps the AP call's in-IRQ driver wait from parking.
- **Deadlines and global timers stay on the BSP's tick.** `waitset_tick` deadlines, the LAPIC watchdog and shm detach timeouts are scanned there for every slot, and wake through the same CAS and kick.
- **An AP's own LAPIC tick** runs only while it has two or more live homed processes, to preempt between them. A lone pinned netd sees no timer interrupts at all.

The other direction (an AP-side event waking a BSP process: netd notifying an app) is the same path, mirrored.

#### The host test of the protocol

`test/test_smp_proto.ritz` (#4879 slice 2) is a small model checker on the host. It models TSO directly: each virtual CPU has a FIFO store buffer that drains at a nondeterministic step or at a locked op or `mfence`, and loads see their own buffer first. It enumerates every interleaving of short op lists that transcribe the kernel code step for step. Each kernel site cites its model step in a comment, and the model's op lists live next to the code they mirror in review.

- **Sleep/wake:** a sleeper (the eventcount ShmWait) and a notifier, then two notifiers. Every final state where the notifier finished must have the sleeper RUNNING, or sitting in `hlt` with a kick pending.
- **CPU idle:** the idle handshake against a waker and a mailbox producer.
- **Mailbox:** two producers and the consumer on a 2-slot ring, so the ring wraps. No message is lost or duplicated, each body is read whole, and order is FIFO per producer.
- **Mutation-checked.** Each break must turn its own case red: a plain store instead of `xchg` for either announce; the producer storing `seq` before the body; the consumer freeing the slot before it copies the body; the waker not reading `pc_idle` (no kick); `sti` placed before the re-check.

The model checks the protocol, not the compiled kernel. The boot tests (§6) exercise the real code.

### 5. Spawn-time placement

- **Kernel-only API.** `process_spawn_program_on(path, cpu)` sets `Proc.home` in `proc_new_child`, before `proc_start`. The spawn runs on the BSP, which owns the process table. The child first runs on its home CPU, when `proc_start`'s kick reaches it. Its first switch is the trivial move: it has never run, and its rows pass from the BSP to its home when the state word is published.
- **`place_pinned(want)`** returns `want` if it is a started AP. Otherwise it returns the *last* started AP (highest `cpu_map` index with `cpu_map_started`), so the BSP and low CPUs stay for everything else. With no started AP (-smp 1, or every AP failed to boot) it returns the BSP. netd then runs exactly as it does today, which is the fallback #4877 requires.
- **netd (#4877).** Boot option `\harland\netd-cpu=N` chooses `want`. With no option, `want` is "the last AP". A refused `N` is logged (`[net] netd-cpu N not started: using cpu K`). The netd restart path (#4745) respawns onto the same home. The NIC's MSI-X is aimed at netd's home CPU (`irq_route_dest`), so its interrupt wakes netd without a cross-CPU IPI.
- **Exclusive.** Nothing else is ever homed on netd's AP, because the kernel is the only placer and it places only netd there. A later user affinity API must refuse a CPU the kernel reserved.

### 6. Boot tests

| Test | Where | Checks |
|---|---|---|
| `test/test_smp_proto.ritz` (host) | the harland host tests (#4879) | the protocol of §4, mutation-checked |
| `[mbox] round trip OK: cpu K answered N pings` | test-tier1, test-smp (#4879) | `init_smp` sends 64 pings to every started AP (more than the 16-slot ring, so it wraps; 8 in flight) and each AP drains its mailbox from its idle loop and replies. At -smp 1 the line is `[mbox] no APs to ping`. Mutations: the AP's drain not replying, and a post without its kick, each turn the boot red. The existing AP-call NVMe line still passes, now over the mailbox |
| `[smp] syscall stacks OK` (existing) | test-smp, test-tier1 | unchanged: the Smp syscall runs locally on every CPU |
| `[tlb] owner unmap OK: cpu N saw the unmap` | test-smp, test-tier1 (#4880) | `apcall.ritz tlb_selftest_all`, on every started AP. A first AP call loads a test PML4 on the AP, maps VA → frame A and reads A's marker. The BSP checks that `PC_ACTIVE_PML4` shows the PML4 loaded there, then posts `UNMAP{va}` and waits for `UNMAP_DONE`. A second AP call maps VA → frame B, which flushes nothing, and reads B's marker. Mutation: the owner skips the `invlpg`, and the second read sees the stale A (`FAIL: cpu N read the stale frame`). At -smp 1 the line is `[tlb] no APs for the owner unmap` |
| `[tlb] kernel invlpg OK: cpu N saw the unmap` | same (#4880) | The AP reads a kernel-half VA mapped to A. The BSP runs `tlb_unmap_kernel_page` (a `KERNEL_INVLPG` to every AP) and maps the VA to B, and the AP must read B. Then an AP call loads the kernel PML4 on the AP (the lazy-CR3 drop), and the test PML4 must be loaded nowhere before `vmm_free_pml4`. Mutations: the AP skips the flush for `KERNEL_INVLPG`, and this line alone fails. Skip the drop, and `vmm_free_pml4`'s assert fires and the boot fails |
| `[smp-user] concurrent syscalls OK: cpu0 N cpuK M, forwarded F` | `\harland\smp-user`, test-smp (2 CPUs), test-tier1 (4) (#4881) | One process on the BSP and one on the last AP each make 100k calls to a forwarded test syscall that bumps a non-atomic BSP-owned counter, and 100k `SYS_LOCAL` calls that bump the CPU's own counter. Both totals are exact and the windows overlap. Mutation: mark the forwarded test syscall `SYS_LOCAL`, and counts are lost |
| `[smp-user] cross-CPU wake OK: woken on cpu K by cpu 0` | same | The AP process parks in ShmWait, the BSP process ShmNotifies, and the wakee resumes on its home CPU. Mutation: no kick, and the test times out |
| `[smp-user] single CPU: pinned spawn ran on the BSP` | an -smp 1 boot (#4881) | the placement fallback |
| netd on an AP, its CPU index in the log, an echo answered while the BSP is busy | #4877 | the goal |

"Two user processes in syscalls at once on two CPUs" now means real concurrency: the AP's `SYS_LOCAL` calls run while the BSP runs its own syscalls, and the forwarded calls prove the BSP serializes what it owns. #4192's `[smp] syscall stacks OK` line still proves raw concurrent SYSCALL entry on distinct stacks.

## Implementation order

Each step lands green at -smp 1, 2 and 4.

1. **#4879: per-CPU state, the lock-free wake, the mailbox, the leaf locks.** Processes still run only on the BSP, so behaviour does not change. The steps:
   - Slot state as the atomic word of §4, with the CAS wake and the eventcount sleep in ShmWait and the IRQ latches.
   - `proc_cur`, `fs_current`, the scheduler counters and the syscall count per CPU, through the `cpu_index` hook (§2 point 5).
   - An idle context per CPU, on its own guard-paged stack (`percpu.ritz CPU_IDLE`, the seventh per-CPU stack), with the idle handshake. `sched_block` with nothing runnable and `sched_exit` switch to it; until `sched_start` makes it, a boot self-test that blocks idles in place as before. The AP's boot-time idle loop runs the same handshake for its mailbox.
   - `sync/mbox.ritz` and `KICK_VECTOR`, with `apcall.ritz` rebuilt on them.
   - The `SYS_LOCAL` flag in the dispatch table, unused while every process is on the BSP.
   - Per-CPU frame caches and `pmm_lock`.
   - `klog_lock` with `klog_irqsave`.
   - The host protocol test.
2. **#4880: owner-side unmap and the lazy-CR3 drop.** `UNMAP`/`UNMAP_DONE`, `KERNEL_INVLPG`, `PC_ACTIVE_PML4`, a CPU loading the kernel PML4 when a process leaves it, and the `vmm_free_pml4` assert. Tested through the AP call, so it needs no AP process. Done: `mm/tlb.ritz`, the per-CPU `mm/vmm.ritz` state, and the shm and driver unmaps routed through `proc_on_cpu`. #4881 makes `proc_on_cpu` read `Proc.on`, and calls `vmm_load_kernel_pml4` in FORWARD and RETURN.
3. **#4881: APs run pinned processes on this model.** The pieces:
   - `Proc.home` and the per-CPU pick.
   - The AP idle loop on the scheduler.
   - The AP tick, only when needed.
   - `Proc.on`, syscall forwarding (`FORWARD`/`RETURN`, Exit and kills included) and `CAP_INSERT`.
   - The BSP gates dropped.
   - `process_spawn_program_on`/`place_pinned`.
   - The `\harland\smp-user` boot tests.

   Landed in slices. The first: `Proc.home` and `Proc.on` with the per-CPU pick (`proc/table.ritz`), the AP idle loop on the scheduler (`proc/sched.ritz sched_ap_enter`), the AP tick, forwarding (`sched_forward`/`sched_return_home`, finished on the idle context by `sched_finish_move`; Exit and kills forward in `sys_exit_impl`), the mailbox drain at return to user (`sched_user_safe_point`), `process_spawn_program_on`/`place_pinned`, and boot tests (a) and (c) (`syscall/runtime/smp_user.ritz`, `kernel/smp_user_stub.s`). Then the BSP gates, `CAP_INSERT` and boot test (b).

Then #4877 (netd on its own AP) depends on all three, and on #4876's batched wait.
