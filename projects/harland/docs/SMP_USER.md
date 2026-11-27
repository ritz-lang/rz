# Harland SMP: Application Processors Run User Processes

| | |
|---|---|
| Status | Decided (AGAST #4874). Implemented by #4879, #4880 and #4881 |
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

**Decision: pinning.** Every process has a home CPU (`Proc.home`, a `cpu_map` index). A CPU runs only processes whose home it is. There is no load balancing and no migration. Processes default to the BSP, including children of a process homed on an AP. The kernel alone places a process elsewhere (§5). There is no user affinity syscall yet.

What each option needs:

| Piece | Pinning | General per-CPU run queues |
|---|---|---|
| Kernel lock (§2) | yes | yes |
| Per-CPU current slot, idle context per CPU | yes | yes |
| Wake IPI to another CPU (§4) | yes | yes |
| TLB shootdown (§3) | yes | yes |
| Pick filtered by CPU | one `home == cpu` test in `proc_pick_next` | a queue per CPU, kept consistent with the proc table |
| Placement policy | the kernel names a CPU at spawn | a policy for every spawn and wake (least loaded, cache-warm, ...) |
| Load balancing | none | periodic or idle-time stealing, with its locking |
| Migration | none | moving a blocked or runnable process between CPUs. That means FPU state that follows it (missing today), TLB/PCID state of the old CPU, and a home that changes under a concurrent wake |
| Tick | only on a CPU with two or more homed processes | on every CPU that has work |

Everything pinning needs, run queues need too. Run queues add three things with their own correctness problems: a placement policy, a balancer and migration. So pinning is a strict subset, and the first step. The way out is additive. `home` stays a pinned process's CPU, and a later "floating" class (`home = ANY`) is what a balancer moves. The netd use case never wants to float.

With `MAX_PROCS = 8` the table is small enough that "per-CPU queue" is a filtered scan of the one table, so pinning needs no new data structure.

### 2. Kernel concurrency: a big kernel lock first, then leaf and hot-path locks

**Decision: one big kernel lock (`klock`).** It is taken at every entry from asm into Ritz kernel code and released at the matching exit. Fine-grained locks are carved out of it in a fixed order (below), each one driven by a measured counter.

#### The inventory

These are the globals an AP-resident process reaches through its syscalls, IRQs and faults. They come from module-level `var`s in `kernel/src` (about 60 files have them).

| Subsystem | Globals | Reached by |
|---|---|---|
| Process table | `proc/table.ritz procs[8]`, `proc_cur`, `proc_next_pid` | spawn, exit, wait, every wake, every switch |
| Scheduler | `proc/sched.ritz` counters and `sched_running` | every switch, every tick |
| Wait sets | `proc/waitset.ritz irq_objects`, `shm_latches`, `inbox`, `waitset_deadline`, `waitset_console` | DrvIrqWait, ShmWait, ShmNotify, MSI-X dispatch, COM1 IRQ, tick |
| SHM | `mm/shm.ritz shm_objects`, `shm_maps`, `shm_cursors` | ShmCreate/Map/Notify/Detach, retire, detach timeout (tick) |
| Capabilities | `cap/table.ritz cap_tables[64]`, `irq_cap_owners` | every handle lookup, grants |
| Frames | `mm/pmm.ritz` bitmap, `pmm_free_pages`, `pmm_next_free` | every map, spawn, exit, DMA |
| Page tables | `mm/vmm.ritz` (`g_mmio_next`), and every PML4 itself | map/unmap, spawn, exit, shm, DrvDma |
| Kernel heap | `mm/heap.ritz heap_free_list` | fs, drivers, channels |
| DMA / IOMMU | `mm/dma.ritz`, `mm/dma_runs.ritz`, `drivers/iommu/vtd.ritz`, `amdvi.ritz` | DrvDma alloc/free, driver death |
| Driver seats | `syscall/runtime/driver.ritz drv_devices` | DrvClaim, DrvIrqWait |
| Net seat | `syscall/runtime/net.ritz`: `addr_snapshot`/`addr_generation` (NetAddr), `link_snapshot`, `exchanges[16]`, the service ids | NetPublish, NetAddr, NetInfo, the app exchange, netd restart |
| IPC | `ipc/channel.ritz channels[256]` | channel syscalls |
| fs / tty | `fs/syscall.ritz fs_procs`, `fs_current`; `fs/kfs.ritz`, `vfs.ritz`; `tty/ldisc.ritz`; `serial.ritz` buffers | read/write/open, console IRQ |
| Log | `klog.ritz ring_buffer`, `ring_head`; `serial.ritz` output ring | everywhere, including IRQ, NMI and panic |
| Dispatch | `syscall/dispatch.ritz g_syscall_count` | every syscall |
| In-kernel drivers | `drivers/nvme`, `virtio/blk`, `virtio/net`, `ena` queue state | fs syscalls, the in-kernel net stack |

#### Why a big lock

- **It keeps today's invariant exactly.** "Kernel code runs exclusively between blocking points" holds now because one CPU runs it and it is not preemptible. With a big lock that is held from entry to exit and released at every blocking point, it still holds on N CPUs. Every subsystem above keeps its current reasoning and no code in it changes. The other option would audit and lock about 60 modules before an AP could make its first syscall.
- **The workload it serves barely contends.** netd on a dedicated core is meant to poll its rings in user mode with no syscalls on the echo path (#4877). It enters the kernel only to sleep in the batched wait and to wake. Per-subsystem locks would buy nothing there until something else contends.
- **It is cheap to measure.** Contention is a counter, so we leave the big lock when a number says so, not on a guess.

#### The lock

- `kernel/src/sync/klock.ritz` (#4879): a ticket spinlock, recursive per CPU (owner CPU index plus depth). Ticket order gives FIFO fairness between CPUs.
- **Spin with IF=0** (save IF, `cli`, spin, restore IF). A nested IRQ on a CPU that is waiting would take a second ticket behind its own first ticket and deadlock. An IRQ on the *holder* only recurses (depth + 1).
- **While spinning, poll this CPU's shootdown mailbox** (§3). This is what makes a synchronous shootdown by the holder safe.
- **Taken:** in `syscall_handler` before `syscall_entry.s`'s `sti`, in `irq_handler`, in the fault handlers, and in `reap_if_marked`'s `sys_exit_impl`, which are all the Ritz entries from asm.
- **Released:** at each matching exit, and in `proc_first_entry` before a new process's first `iretq` (it was switched to under the lock).
- **Never taken:** the NMI handler, the wake IPI (§4) and the shootdown IPI (§3).
- **Blocking points release it fully.** The rule is that *every `hlt` in the kernel* releases the lock. `kernel_idle_wait()` does release-all (saving the depth), then `sti;hlt`, `cli`, and reacquires to the saved depth. `sched_block`, `sched_exit`, the scheduler's idle loop, `waitq`'s non-parking fallback and `nvme_q_lock` all go through it. The release happens with IF=0 *before* `sti;hlt`: a wake IPI sent in between is held pending, and `sti`'s interrupt shadow delivers it right after `hlt` starts, so no wake-up is lost.
- **Switching:** a switch happens only at depth 1 (a syscall that blocks or yields, or a tick from user). The lock belongs to the CPU, not the process, so the process switched to resumes holding it at the same depth. `sched_switch_to` asserts depth 1. A driver wait inside an IRQ handler (the boot-time AP call) is at depth 2 and must not park: `waitq_can_park` becomes "depth 1 and a current process", replacing "is the BSP".
- **Counters per CPU:** acquisitions, contended acquisitions, spin TSC cycles, and the longest hold. `sched_report` prints them, and the net latency entries quote them.

Busy-waits that hold the lock without `hlt` (a device-register poll with a deadline, like `apcall`'s) stay legal but stall the other CPUs for their length. A new one needs a comment saying why it cannot park.

#### Leaving the big lock

The order of carve-outs. Each is its own ticket when a counter shows the need, except the first.

1. **Leaf locks, now (#4879).** `klog` and `serial` get their own IRQ-safe spinlock, so two CPUs' lines never interleave mid-line. NMI and panic use trylock and write anyway. These never call up into anything that takes `klock`.
2. **The frame allocator and heap**, when spawn and DMA on two CPUs contend: `pmm_lock`, `heap_lock`, both leaves.
3. **The wake path**, when netd's wait/notify syscalls show `klock` contention: a `sched_lock` over process state transitions, the per-CPU current slots and the wait sets (`waitset.ritz`, the shm latches). ShmNotify, ShmWait and DrvIrqWait then run without `klock`.
4. **Per-syscall opt-out.** The dispatch table gets a `KLOCK_FREE` flag. A syscall whose subsystems all have their own locks is marked and dispatch skips `klock` for it. Unmarked syscalls keep the big lock, so the carve-out is incremental and every step lands green.

Lock order, outermost first: `klock` → `sched_lock` → `vmm`/shootdown → `pmm_lock` → `heap_lock` → `klog_lock`. A lock never takes one to its left. From step 2 on, *every* spinlock's spin loop polls the shootdown mailbox, not only `klock`'s.

### 3. TLB shootdown

**It is needed for both halves, even without threads.** One address space is never *running* on two CPUs until threads exist. But the kernel edits page tables of processes that are not running on the editing CPU:

- **`mm/shm.ritz shm_detach_expired` and retire** unmap a holder's mapping, and the holder (netd) may be live on its AP.
- **`syscall/runtime/driver.ritz`'s unmap and quarantine of DMA/MMIO leaves** (`vmm_unmap_page_in`, `vmm_quarantine_page_in`) touch the driver's PML4, and after #4875 the driver is netd.
- **The kernel half** (PML4[256..511], shared by every address space) is live on every CPU. `vmm_unmap_kernel_page` today runs only at boot (guard pages), but any later kernel-half unmap must reach all CPUs.
- **Lazy CR3.** A CPU that goes idle keeps the last process's CR3 loaded, so that netd waking on the same CPU costs no CR3 load. If that process exits and its PML4 is freed by its reaper on another CPU, the idle CPU still points at freed page tables, and speculative walks read reused frames.

Design (#4880):

- **Tracking.** `PC_ACTIVE_PML4` per CPU, written on every CR3 load. Each address space has a `cpus` bitmask of the CPUs that may hold its translations. Without PCID the mask is exactly "the CPUs whose CR3 is this PML4" (a CR3 load flushes, and harland never sets `PTE_GLOBAL`, so no global entries exist whatever CR4.PGE the firmware left).
- **Mailbox and IPI.** Per CPU: `{pml4, va, pages, generation, ack}`, and vector 242. The handler takes no lock. It does invlpg for up to 32 pages, or a CR3 reload beyond that, or a "drop" request (load the kernel PML4), then acks.
- **Unmap protocol.** Clear the PTEs, invalidate locally if this CPU's CR3 is that PML4, post to every other CPU in the mask, send 242, and wait for each ack. *Only then* return the frames to the PMM. Kernel-half unmaps go to every started CPU. `vmm_free_pml4` first sends "drop" to any CPU whose `PC_ACTIVE_PML4` is the victim.
- **No deadlock.** Only the `klock` holder edits page tables, so there is one initiator at a time. A target is in one of three states:
  - in user mode or in the kernel with IF=1: it takes the IPI;
  - spinning on `klock` with IF=0: the spin loop polls the mailbox;
  - in a short `cli` section: it reaches IF=1 soon.
- **Mapping needs no shootdown.** x86 caches no not-present translations, so adding a mapping is never shot down.

**PCID (#4878, parked).** With PCID a CR3 switch keeps the old space's tagged entries, so a CPU that *ran* a space and moved on still holds them. The mask becomes sticky: a bit is set on load and cleared only by a flush of that PCID. A shootdown to a CPU that is not currently running the space need not interrupt it. Instead it marks that CPU's PCID for the space stale, and its next load of the space uses a flushing CR3 write (bit 63 clear) or INVPCID. Only CPUs currently running the space get the IPI. This is why the mask and the "active" word are separate from day one.

### 4. Wake-ups across CPUs

**The rule.** Whenever kernel code makes a process RUNNING whose home is another CPU, it sends that CPU a wake IPI. That covers `proc_wake`, `proc_wake_pid`, `proc_start`, `proc_mark_exit` and the parent wake in `proc_exit_current`. The wake IPI is vector 241, and its handler does EOI only and takes no lock. The `hlt` in the target's idle loop returns, and the loop re-checks under `klock`. The state change itself is under `klock`, like everything else.

- A process that is already RUNNING gets no IPI (its state did not change). netd spinning in user mode is therefore never interrupted by notifies it does not need.
- The release-before-`sti;hlt` ordering (§2) makes the check-then-sleep race-free.
- The BSP-only gates go away. The three `lapic_is_bsp` tests in `waitset.ritz` become "wake the owner wherever its home is", and `waitq_can_park` stops testing for the BSP (§2).
- **Deadlines and global timers stay on the BSP's tick.** `waitset_tick` deadlines, the LAPIC watchdog and shm detach timeouts are scanned there for every slot, and wake through the same IPI.
- **An AP's own LAPIC tick** runs only while it has two or more live homed processes, to preempt between them. A lone pinned netd sees no timer interrupts at all.

The other direction (an AP-side event waking a BSP process: netd notifying an app) is the same path, mirrored.

### 5. Spawn-time placement

- **Kernel-only API.** `process_spawn_program_on(path, cpu)` sets `Proc.home` in `proc_new_child`, before `proc_start`. The spawn runs on the parent's CPU (the BSP, under `klock`). The child first runs on its home CPU, when `proc_start`'s wake IPI reaches it. Its first switch is the only "migration" that ever happens, and it is the trivial one: it has never run.
- **`place_pinned(want)`** returns `want` if it is a started AP. Otherwise it returns the *last* started AP (highest `cpu_map` index with `cpu_map_started`), so the BSP and low CPUs stay for everything else. With no started AP (-smp 1, or every AP failed to boot) it returns the BSP. netd then runs exactly as it does today, which is the fallback #4877 requires.
- **netd (#4877).** Boot option `\harland\netd-cpu=N` chooses `want`. With no option, `want` is "the last AP". A refused `N` is logged (`[net] netd-cpu N not started: using cpu K`). The netd restart path (#4745) respawns onto the same home. The NIC's MSI-X is aimed at netd's home CPU (`irq_route_dest`), so its interrupt wakes netd without a cross-CPU IPI.
- **Exclusive.** Nothing else is ever homed on netd's AP, because the kernel is the only placer and it places only netd there. A later user affinity API must refuse a CPU the kernel reserved.

### 6. Boot tests

| Test | Where | Checks |
|---|---|---|
| `[klock]` counters, 0 contended | test-tier1, test-smp (#4879) | the lock is on every entry and nothing regressed with processes on the BSP only |
| `[tlb] shootdown OK: cpu N saw the remap` | test-smp, test-tier1 (#4880) | The AP (through the AP call) loads a test PML4 and reads VA → frame A's marker. The BSP remaps VA to B and shoots down. The AP reads B. Mutation: skip the IPI, and the AP reads the stale A |
| `[smp-user] concurrent syscalls OK: ...` | `\harland\smp-user`, test-smp (2 CPUs), test-tier1 (4) (#4881) | One process homed on the BSP and one on the last AP each make 100k test syscalls that bump a non-atomic kernel counter. The total is exact, both CPUs' syscall counts advanced in overlapping windows, and `klock` contended > 0 |
| `[smp-user] cross-CPU wake OK: woken on cpu K by cpu 0` | same | The AP process parks in ShmWait, the BSP process ShmNotifies, and the wakee resumes on its home CPU. Mutation: no wake IPI, and the test times out |
| `[smp-user] single CPU: pinned spawn ran on the BSP` | an -smp 1 boot (#4881) | the placement fallback |
| netd on an AP, its CPU index in the log, an echo answered while the BSP is busy | #4877 | the goal |

"Two user processes in syscalls at once on two CPUs" means, under a big lock, two CPUs *inside* the kernel at once: one holding `klock` and the other spinning on it or parked having released it. The concurrent-syscalls test proves the serialization is correct. The lock's contended counter proves the overlap really happened. #4192's existing `[smp] syscall stacks OK` line still proves raw concurrent SYSCALL entry on distinct stacks, before any lock.

## Implementation order

Each step lands green on its own.

1. **#4879: the kernel lock and per-CPU scheduler state.** Processes still run only on the BSP, so behaviour does not change. It adds `klock` at every entry and exit, release at every `hlt`, and the klog/serial leaf lock. `proc_cur` and `fs_current` become per CPU, and each CPU gets an idle context, so `sched_exit` no longer idles on a stack whose slot another CPU may reuse.
2. **#4880: TLB shootdown and address-space tracking.** Tested through the AP call, so it needs no AP process.
3. **#4881: APs run pinned processes.** `Proc.home`, the per-CPU pick, the AP idle loop, the AP tick only when needed, the wake IPI, the BSP gates dropped, `process_spawn_program_on`/`place_pinned`, and the `\harland\smp-user` boot tests.

Then #4877 (netd on its own AP) depends on all three, and on #4876's batched wait.
