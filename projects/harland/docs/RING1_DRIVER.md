# Harland Ring-1 Driver Substrate

| | |
|---|---|
| Author | placeholder |
| Date | 2026-11-23 |
| Status | Draft |
| Audience | Harland kernel |

## Overview

Harland's NIC still runs in ring 0. `netdev_init` probes virtio-net and then ENA, the IPv4 stack in `net/stack.ritz` polls that device, and syscall 60 does not exist. The next slice gives drivers one privilege level, ring 1, and moves virtio-net's queues into a process at that level. Ring 0 keeps the IDT, the LAPIC EOI, and MSI-X table programming. The IPv4 stack has its home in ring 2: ARP, DHCP, ICMP, UDP, and later TCP, which is `ARCHITECTURE.md` phase 5. This slice leaves that code in ring 0 so the existing self-test can be the first consumer of the frame rings. Moving it is a change of who maps the consumer side. The process publishes Ethernet frames on a portable single-producer single-consumer (SPSC) descriptor ring. `NetInfo` (syscall 224) copies the link record that process publishes: MAC, link, MTU, and device type. Addresses stay with the stack. Numbers 60 and 61 stay free for their Linux meanings.

Ring 1 does not widen page permissions. On x86-64 the user/supervisor bit treats CPL 1 the same as CPL 3. The ring is still the right boundary: the iret frame's RPL is unforgeable, `projects/harland/docs/ARCHITECTURE.md` already assigns drivers to ring 1, and a later call gate can use `TSS.rsp1`. This design does not add that gate, a socket API, or TCP.

## Background and motivation

### What runs today

The boot self-test is opt-in. `projects/harland/boot/src/main.ritz` sets `HARLAND_BOOT_FLAG_NET_SELFTEST` (value 1 in `boot_abi/src/handoff.ritz`) when the ESP contains `\harland\net-selftest`. `kernel_main` calls `postinit_diagnostics` before `run_init`. Only then does `network_dhcp_ping` call `net_stack_init`. There is no process yet: `process_enter_init` runs later, from `run_init`. `waitq_can_park` is false because `proc_current()` is null, so the NIC wait is `sti;hlt`, not a parked Proc.

`net/stack.ritz` `handle_ipv4_packet` dispatches ICMP and UDP. The TCP arm is a comment and `return 0`. `handle_udp_packet` accepts only DHCP (server port to client port). `icmp_ping` returns -1 when the next hop is not in the ARP cache. `net/ip.ritz` holds `ip_our_addr`, `ip_gateway`, `ip_netmask`, `ip_dns`, and `ip_configured`, written by `dhcp_on_ack`.

virtio-net (`drivers/virtio/net.ritz`) drives either transport in `drivers/virtio/common.ritz`: legacy BAR0 port I/O (`VIO_TRANSPORT_LEGACY`) or modern MMIO (`VIO_TRANSPORT_MMIO`). The MSI-X boot (`tools/test_msix_boot.sh`) passes `disable-legacy=on` and `rx_queue_size=1024`. The driver caps the queue at `VIRTQ_MAX_SIZE` (256) and posts 32 RX and 32 TX buffers of 2048 bytes. `NetDevice.mtu` is 1500. Link state is bit 0 of the virtio-net status field at config offset 6 (`VIRTIO_NET_CFG_STATUS`). `virtio_net_wait_rx` calls `irq_wait_vector(..., may_park=false)`, so the boot log's `halted` count is the `sti;hlt` path.

ENA stays behind the same `netdev` vtable (`NETDEV_TYPE_ENA` = 2). `netdev_wait_rx` returns false for ENA. Peer ping (`\harland\net-responder`, flag value 2) runs only when `net_device_type() == NETDEV_TYPE_ENA`.

### Why a ring-1 process cannot be entered

`sched_tick` and `exception_handler` treat a process as `cs & 3 == 3`. A CPL-1 frame would take the kernel path: no preemption, and a fault prints `KERNEL PANIC` and halts. The GDT has ring 0 and ring 3 only. `syscall_entry.s` returns with `iretq` and immediate selectors `0x1B` / `0x23`.

The assembly stubs are already wider than those Ritz tests. `SWAPGS_IF_USER` and `irq_stub_timer` use `testq $3` / `jz`, which is any non-zero RPL. A ring-1 interrupt swaps GS and the timer copies the iret frame onto `PC_KSTACK_TOP`. The comments say "ring 3". The predicate does not. This design changes the Ritz tests to match the stubs. It does not narrow the stubs to `== 3`.

### Documents that contradict the tree

| Document | Claim | Tree |
|---|---|---|
| `ARCHITECTURE.md` ring model | Already assigns drivers to ring 1 and the stack to ring 2 | Kept. The tree still runs both in ring 0. PR 1 does not rewrite that diagram. |
| `ARCHITECTURE.md` phases 1–4 | Multi-core, scheduler, IPC, virtio-net are future | LAPIC, APs, preemption (`AGAST #3629`), ring-3 syscalls, and virtio-net are in the kernel. PR 1 marks this list historical. |
| `ARCHITECTURE.md` size | Ring 0 under 10KB, about 5KB | Historical target. This workspace has no `harland.elf` to measure. This design does not claim 10KB. |
| `ARCHITECTURE.md` drivers | "Direct hardware access (MMIO, port I/O)" at the ring-1 row | The ring-1 assignment stays. This substrate does not grant port I/O. PR 1 marks that phrase as not granted. |
| `NETWORK_DESIGN.md` | `SYS_NET_INFO = 40`, `SYS_NET_PING = 41` | 40 is `CapGrant`, 41 is `CapRevoke` (`syscall/numbers.ritz`). |
| `NETWORK_DESIGN.md` steps 9–11 | `net/syscall.ritz`, `/bin/ping`, shell ifconfig | Not present. UDP is DHCP-only. TCP drops. |
| `NETWORK_DESIGN.md` ring section | Ring 1/2 is future work, drivers get `IOPORT` | The ring level is this design. `IOPORT` is rejected. |
| `KERNEL_CONTRACT.md` | "Goliath runs as a Ring 2 service", "Block drivers (Ring 2)", "Device Syscalls (Ring 2 Drivers Only)". `SYS_SHM_*` = 50–52, `SYS_IRQ_WAIT` = 60, `SYS_DMA_ALLOC` = 61, `SYS_DMA_FREE` = 62, `SYS_MMIO_MAP` = 63, `SYS_IRQ_ACK` = 64 | 50 and 51 are `InputPoll` and `InputRead`. 60 and 61 stay free for their Linux meanings and are not `net_info` or `net_ping`. 64 is not a live syscall and is not this design's IRQ path: the kernel EOIs. None of 50–64 are allocated for a driver ABI. Shared memory is `CAP_TYPE_SHM` with `ShmMap` (227), not `SYS_SHM_*`. |
| `SYSCALL_ABSTRACTION.md` | Harland backend is "via IPC/ring buf" | Entry is `syscall` / `iretq` in `syscall_entry.s`. The SPSC ring is the frame dataplane beside that ABI, not a replacement for it. |
| `numbers.ritz` header, `test_harland_syscall_dispatch.py` | 60 and 61 are free (removed by AGAST #2122, declared but never dispatched) | They stay free. This design does not declare them. `NetInfo` is 224. `NetAddr` is 225. |

`ipc/channel.ritz` is not the documented Zeus ring. It is a copied linked-list queue, `CHANNEL_QUEUE_MAX` 16, `MAX_CHANNELS` 256.

## Goals and non-goals

### Goals

1. One driver privilege level: CPL 1, DPL-1 non-conforming code and a DPL-1 data segment, a ring-1 stack in the iret frame, and an iret return to that RPL.
2. Any non-zero CPL is a process for the timer, for faults, and for console Ctrl-C. CPL 0 stays non-preemptible and a kernel fault still panics.
3. One waitable device interrupt: the existing `BLOCK_IRQ` park. The kernel owns the IDT and the LAPIC EOI.
4. MMIO and DMA mappings into that process only, under new syscall numbers past the live ABI. A private translated DMA domain is installed before the driver may program queue addresses or bus-master the NIC.
5. A portable SPSC frame ring. Harland maps it and wakes with the scheduler. The publication rule is `seq_cst` atomics, which Linux and Win64-on-ARM can honor.
6. virtio-net queues, BAR access, RX/TX, and the MAC/link record move into the ring-1 process. `NetInfo` (224) copies that record. The device process is authorized with capabilities, the same table `FbMap` already checks.
7. The `\harland\net-selftest` assertions still hold after a single cutover. In-kernel virtio and the ring-1 driver never both own the queues. The receive wait has a deadline, and the 300-send burst schedules the driver while it waits for replies.

### Non-goals

- `net_ping`. It is not numbered. 61 stays free for its Linux meaning. No arguments, no ICMP wrapper, no ARP retry loop.
- Building the ring-2 network service in this slice. That service is the stack's home: ARP, IPv4, DHCP, ICMP, UDP, and TCP. While the kernel is still the consumer, non-DHCP UDP and TCP keep today's drop. There is no socket API here.
- Moving ENA. Peer ping keeps the in-kernel ENA owner.
- User-mode interrupt delivery, IOPL, or an I/O permission bitmap.
- A second shared-memory family at numbers 50–52. Those contract numbers stay struck. `CAP_TYPE_SHM`, the existing `CapGrant` / `CapRevoke`, and `ShmMap` (227) are the one grant path. Spawn uses that path. A later attach uses it again.
- Linux and Win64 implementations. The protocol and the mapping table are in scope. The code is not.
- A new Ritz memory-order intrinsic. `seq_cst` atomics already exist.
- Replacing `syscall_entry.s` with SYSRET.

## Corrections to the brief

The brief matches the tree except where this section says otherwise.

- The syscall return is already `iretq`, not SYSRET. `syscall/runtime/entry.ritz` leaves `STAR[63:48]` at 0 because SYSRET wants user data at `base+8` and user code at `base+16`, and the GDT has user code at index 3 (`0x18`) then user data at index 4 (`0x20`). Intel SYSRET also forces the new CS RPL to 3 (`CS = (STAR[63:48] + 16) | 3`). A ring-1 return cannot be SYSRET on Intel. The change is the `syscall_entry` iret tail, which today pushes the immediates `0x23` and `0x1B`. Those become per-CPU slots. `jump_to_userspace` keeps the immediates. The slots do not fit in the current 64-byte area; section 2 sizes the replacement.
- `TSS.rsp0` is what a CPL-0 handler with IST 0 loads on a privilege change from CPL 1 or CPL 3. `TSS.rsp1` is what the CPU loads when the *target* CPL is 1 (a call gate or a handler whose CS has DPL 1). Kernel entry from ring 1 does not read `rsp1`. The timer gate is IST 3 and MSI-X gates 64–79 are IST 2 (`idt.ritz`), so those entries do not load `rsp0` either. `irq_stub_timer` then copies the five-word iret frame to `PC_KSTACK_TOP` when `cs & 3 != 0`. `rsp1` stays 0.
- virtio-net is not MMIO-only. Legacy is port I/O. ENA is MMIO. Ring 1 gets no port I/O, so the moved driver is the modern transport only.
- The virtqueue cap is 256. The boot device offers 1024 and is capped. The live buffer pool is 32 × 2048, not 256 × 2048.
- Ritz can express a release publication. `LANGUAGE_SPEC.md` §18.5 defines `atomic_store`, `atomic_load`, and `fence()` as LLVM `seq_cst`. §18.4 says volatile orders nothing across CPUs. The spec's `fence(); volatile_store(index)` example is not the cross-CPU rule this protocol uses.
- `dma.ritz` says DMA memory is non-cacheable. `dma_alloc` returns a physmap pointer, and the physmap leaves are write-back 2 MiB pages (`vmm_physmap_fill`). The working virtio path programs those write-back pages. Driver DMA follows that path, not the comment.
- `test_harland_percpu.py` asserts `GDT_ENTRIES == GDT_TSS_FIRST + 2 * MAX_CPUS`. Appending descriptors updates that assertion in the same change. It is not a silent GDT growth.
- The self-test runs with no Proc. Cutover has to create the driver process before the DHCP window. `virtio_net_wait_rx` does not park, and `test_msix_boot.sh` requires `halted > 0`. A parked driver fails that assertion until the script changes.
- The handler `syscall_handler(rax, rdi, rsi, rdx, r10)` receives four user arguments. `syscall_entry.s` does not pass the saved r8/r9. New syscalls stay inside those four registers.
- The permission error already used for a missing capability (`sys_fb_map_handler`, `sys_open_handler`, the cap syscalls) is `Errno.Perm` (-1), not `Errno.Acces`.

## Proposed design

### Privilege transitions

```mermaid
flowchart LR
  subgraph r3 [CPL 3]
    app["App CS 0x1B SS 0x23"]
  end
  subgraph r0 [CPL 0]
    kern["Kernel CS 0x08"]
    idt["IDT and LAPIC EOI"]
    stack["IPv4 DHCP ICMP"]
  end
  subgraph r1 [CPL 1]
    drv["virtio-net CS 0x429 SS 0x431"]
  end
  dev["Device MMIO and DMA"]

  app -->|"syscall, iret 0x1B"| kern
  drv -->|"syscall, iret 0x429"| kern
  dev -->|"MSI-X to the BSP"| idt
  idt -->|"proc_wake BLOCK_IRQ"| drv
  drv -->|"UC BAR, WB DMA"| dev
  drv -->|"SPSC RX, DrvRingKick"| stack
  stack -->|"SPSC TX"| drv
```

The diagram is this slice. The IPv4 box moves to CPL 2 with the network service. The rings between that service and the driver stay as drawn.

CPL 0 is the only mode that walks kernel-half page tables (`U/S = 0`). CPL 1 and CPL 3 both fault on those pages. `vmm_create_user_pml4` copies PML4 entries 256–511 with `PTE_USER` cleared. User image, mmap, stack, framebuffer, and the new driver windows sit below PML4[256] with `PTE_USER` set. `boot.s` and `ap_trampoline.s` set CR4.PAE only (bit 5). Nothing in the kernel sets CR4.SMEP (bit 20) or CR4.SMAP (bit 21). There is no second page-privilege lever hiding behind ring 1.

### 1. GDT

Fixed descriptors stay where they are (`gdt.ritz`):

| Index | Selector constant | What |
|---|---|---|
| 0 | `GDT_NULL` 0x00 | Null |
| 1 | `GDT_KERNEL_CODE` 0x08 | Ring 0 code, long mode |
| 2 | `GDT_KERNEL_DATA` 0x10 | Ring 0 data |
| 3 | `GDT_USER_CODE` 0x1B | Ring 3 code, RPL 3 (`0x18 \| 3`) |
| 4 | `GDT_USER_DATA` 0x23 | Ring 3 data, RPL 3 (`0x20 \| 3`) |
| 5 .. 132 | CPU 0 selector `GDT_TSS` 0x28 | 64 TSS pairs. `GDT_TSS_FIRST = 5`. `tss_selector(cpu) = (5 + cpu * 2) * 8`. `MAX_CPUS` is 64. |

`ltr` uses `tss_selector`, not a hardcoded `0x28`, but the constant `GDT_TSS = 0x28` is the CPU 0 selector and `test_harland_percpu.py` locks the formula. Descriptors are appended so index 5 does not move.

| Index | Selector with RPL 1 | Access | Flags |
|---|---|---|---|
| 133 | `GDT_DRIVER_CODE` = 0x429 | `0xBA` = present `0x80`, DPL 1 `0x20`, code `0x1A` | `0xA0` = L and G, same as user code |
| 134 | `GDT_DRIVER_DATA` = 0x431 | `0xB2` = present, DPL 1, data `0x12` | `0x80` = G, same as user data |

`0x1A` is readable, non-conforming, executable. A conforming segment would keep the caller's CPL; this one does not. `GDT_ENTRIES` becomes 135. `var gdt` grows to `[135]GdtEntry`. `GDT_TSS_FIRST` stays 5. `tss_fill` still sets `iopb_offset = 104` (no I/O bitmap) and does not write `rsp1`.

`gdt_init` fills indexes 133 and 134 with `make_gdt_entry`, base 0, limit `0xFFFFF`, the same helper the user segments use. `gdt_get_driver_code_selector` and `gdt_get_driver_data_selector` return `0x429` and `0x431`.

`STAR` stays `KERNEL_CS << 32` with the high half 0, in both `syscall_init` and per-CPU `syscall_msr_init`. Reordering the GDT so SYSRET could find user data then user code would move the TSS or change `0x1B` / `0x23`. Neither happens.

Who loads `rsp0`: `sched_use_kstack` calls `gdt_set_kernel_stack_cpu(cpu_index(), kstack_top(slot))` on `sched_start` and on every switch. That is the CPL-0 stack for an IST-0 privilege change, and it is `PC_KSTACK_TOP`, which `irq_stub_timer` copies a non-zero-RPL tick onto. `rsp1` is not part of that path and is left zero. A future call gate whose target DPL is 1 would be the first writer of `rsp1`. This design has no such gate.

The ring-1 stack in the iret frame is the ordinary user stack from `alloc_user_stack` (`USER_STACK_TOP` = `0x7FFFFFFFE000`, 16 pages, `PTE_USER | PTE_WRITABLE`). SS in that frame is `0x431`. It is not `TSS.rsp1`.

### 2. Process entry

`Proc` stores the return CS/SS the kernel chose for that slot. `proc_free` and `proc_new_child` clear them back to `0x1B` / `0x23`. There is no `driver` bit. A boolean cannot name a third CPL, and it cannot name a window, an IRQ, or a shared region. CPL 1 and CPL 2 are selector pairs. Authorization is a capability, checked the way `FbMap` checks `CAP_TYPE_DISPLAY`.

The kernel grants those capabilities to the process it spawns for the device. The self-test's binary is `projects/indium/user/virtio_net.ritz`, installed as `/bin/virtio-net`. The spawn path is an argument of that boot, not a string the syscall table treats as the only legal driver. An ENA driver or an NVMe driver later receives the same kind of grant for its own device. The ring-2 service receives `CAP_TYPE_SHM` for the frame rings and its address page, and not `CAP_TYPE_MMIO` or `CAP_TYPE_IRQ`. A ring-3 `sys_spawn` gets neither the device capabilities nor a DPL-1 selector.

`sched_prepare_driver(slot, entry, user_rsp, arg0, arg1)` is `sched_prepare_user` with `FRAME_CS = 0x429`, `FRAME_SS = 0x431`, and the same `USER_RFLAGS` (`0x202`: bit 1 reserved, IF set, IOPL bits 12–13 clear). `KERNEL_RFLAGS` on the `sched_switch` frame stays `0x2`. `proc_first_entry` already `swapgs` then `iretq`s whatever CS/SS that frame holds. The first entry does not go through `jump_to_userspace`, which hardcodes `0x1B` / `0x23` for the SMP self-test and stays ring-3-only.

The iret tail of `syscall_entry` pushes two new per-CPU qwords, `PC_USER_CS` and `PC_USER_SS`, instead of `pushq $0x23` and `pushq $0x1B`. RPL 1 never takes SYSRET. The existing comment that hopes to switch the ring-3 return to SYSRET stays a ring-3-only future; the RPL test is `PC_USER_CS & 3 == 3`. This design does not implement that SYSRET.

The whole iret frame is built on the kernel stack. The current tail does `popq %rsp` and then pushes SS, RSP, RFLAGS, CS, and RIP through that pointer, so an invalid saved user stack faults in CPL 0. That sequence is replaced. The pushes use `PC_USER_SS`, the saved user RSP, RFLAGS, `PC_USER_CS`, and the saved user RIP, while the kernel stack is still current. `iretq` is what loads the user RSP. A non-canonical saved RSP, or one in the kernel half, is rejected before `iretq` and the process is killed. An unmapped but canonical user stack is not touched until after `iretq`, so that fault belongs to the process. The same tail returns to CPL 3 and to CPL 1. The test covers both, including a saved RSP that is non-canonical and one that is canonical and unmapped.

The area those slots have to live in is 64 bytes today (`PERCPU_SIZE` in `syscall_entry.s`). Named slots occupy 0 through 48 (`PC_SELF`, `PC_CPU_INDEX`, `PC_KSTACK_TOP`, `PC_USER_RSP`, `PC_USER_RIP`, `PC_USER_RFLAGS`, `PC_USER_RAX`). `percpu_area_init` zeros an anonymous qword at offset 56. `percpu_area_for` and `percpu_area_init` both scale the CPU index with `shlq $6`. Two selector qwords need 16 bytes. Offset 56 has 8. `pushq %gs:PC_USER_CS` is an 8-byte memory operand, so the selectors stay qwords. Offset 56 stays the anonymous padding qword `percpu_area_init` already zeros.

The area grows to 128 bytes. `PERCPU_SIZE` becomes 128. Both `shlq $6` sites become `shlq $7`. `.align 64` stays, and 128 keeps each CPU on its own pair of lines. A stride of 80 would share a line between CPU 0's tail and CPU 1's head. `PERCPU_SLOTS` stays 64, so the `.bss` object grows from 4096 bytes to 8192. The new slots:

| Offset | Symbol | Contents |
|---|---|---|
| 64 | `PC_USER_CS` | `u64`. The selector is the low 16 bits. The upper bits stay 0 so `pushq %gs:PC_USER_CS` pushes a clean selector. |
| 72 | `PC_USER_SS` | `u64`, same rule. |
| 80 .. 127 | none | Zero. Not a third named slot. |

`percpu_area_init` writes `0x1B` to `PC_USER_CS` and `0x23` to `PC_USER_SS` after the existing zeros. `cpu_bringup` calls it on the BSP and on every AP before any Proc exists. That is the value the SMP phase-1 return uses. `sys_smp_test_handler` returns 0 on `SMP_PHASE_PING` and `syscall_entry` then irets, from `init_smp`, before `sched_start`. A zero CS there is a `#GP` on every CPU that took phase 1. The initialized selectors make that iret the ring-3 return it is today.

`sched_use_kstack` overwrites both slots from the Proc it is switching to, on `sched_start` and on every `sched_switch_to`. A driver Proc stores `0x429` / `0x431`. Every other Proc stores `0x1B` / `0x23`. Writing only on the driver path would leave `0x429` installed after the switch back to a ring-3 process, and that process's next syscall would iret to CPL 1. The no-Proc path never calls `sched_use_kstack`, which is why the init values have to be right by themselves.

`jump_to_userspace` and `jump_to_userspace_with_args` keep `pushq $0x23` and `pushq $0x1B`. They are the first entry of `/bin/init` and of the SMP stub (`smp_ap_run`, `smp_test_enter_user`). They do not read the slots, and they do not have to write them. The syscall return is the path that reads them.

`syscall_entry` itself is valid from CPL 1. SYSCALL loads CS from `STAR[47:32]` (`0x08`) and SS from that value plus 8 (`0x10`), ignores the TSS, and the stub `swapgs`s. The driver runs with user GS (0) and `KERNEL_GS_BASE` holding the per-CPU area, same as ring 3, because `proc_first_entry` and the syscall exit both `swapgs`.

Inside a syscall the live CS is `0x08`. Driver syscalls authorize with a capability handle, not with a CPL read and not with a process-wide bit. A caller without the handle gets `Errno.Perm` (-1).

IOPL stays 0. There is no IOPB. `in` / `out` from the driver are `#GP`.

### 3. Scheduler and faults

Three Ritz predicates change from `cs & 3 == 3` to `cs & 3 != 0`:

- `exception_handler` in `exceptions.ritz`. A non-zero CPL kills the current process with `process_kill_current(128 + vector)` and logs `[fault] PID`, the same status ring 3 uses (`#UD` is 128+6, `#PF` is 128+14). CPL 0 still panics, including the syscall-stack guard page.
- The `sched_tick` argument from `irq_handler` vector 32. `sched_tick` preempts only when `from_user` is true and `sched_running` is set, and only when `proc_pick_next` returns a different slot. CPL 0, including a syscall and `DrvIrqWait`'s kernel half, stays non-preemptible. `sched_preemptions` counts the switch.
- The `tty_console_irq` argument. A foreground driver takes Ctrl-C with status `TTY_INTR_STATUS` (130) and then the death path below. A background driver does not, which is the rule `tty_fg_is_current` already applies.

`irq_stub_timer` already copies the iret frame for any non-zero RPL, so a ring-1 tick lands on that process's kernel stack where `sched_switch` expects it. MSI-X stays on IST 2: the handler wakes and irets; it does not preempt.

Processes run on the BSP only (`sched.ritz`: APs halt after the syscall-stack self-test). `msix_set_entry` aims at `lapic_id()` of the CPU that programs it, then `irq_route_dest`. `waitq_wake_irq` returns without waking when `lapic_is_bsp()` is false. The ring-1 virtio driver is pinned to the BSP. Kernel MSI-X setup for this device uses the BSP's APIC ID and refuses to start the driver if `irq_route_dest(bsp)` is not the BSP. An IRQ delivered elsewhere would EOI on that CPU and never wake the waiter.

### Driver death

`process_kill_current` is `sys_exit_impl`. A fault (`exception_handler`), `exit` (`sys_exit_handler`), and Ctrl-C (`tty_console_irq`) all enter that one function. For any non-init process it switches to `g_kernel_pml4`, closes fds, and then calls `vmm_free_pml4`. `vmm_free_user_pt` `pmm_free_page`s every present leaf that does not have `PTE_DEVICE`. Only after that free does it `disable_interrupts` and call `proc_exit_current`. Init's exit takes the other branch and powers off. The driver is not init.

`driver_quiesce` runs from `sys_exit_impl` when the exiting pid is the recorded owner of a device IRQ capability, after the switch to the kernel PML4 and before `vmm_free_pml4`. The kernel records that pid when it grants the capability. It does not run from `proc_exit_current`. By then the user tables are already gone and the device has been DMA-ing into freed frames.

1. Mask the device's MSI-X table entries through the kernel mapping. The process never receives that table.
2. Through the kernel's existing `vmm_map_mmio` window, write virtio status 0. That write starts the reset. The kernel then reads status until it is 0, bounded by `VIRTIO_RESET_TIMEOUT_US` (100 ms). That constant lives with the virtio code. It is not `VTD_TIMEOUT_US`, which is private to `vtd.ritz`. A 0 readback is the completion Virtio 1.2 requires before the device may be treated as idle. The kernel BAR map outlives the Proc. Queues are not left `DRIVER_OK` with no owner.
3. Invalidate every IOVA in this requester's DMA domain and wait for the IOTLB invalidation to finish. The domain is the device's access. Clearing a CPU page table does not revoke it.
4. Invalidate the kernel link snapshot (section 7). Clear `driver_registered` and the kernel's pointer at the shared region. Do not write the shared `NetInfo`. The driver was its only writer, and the pages are about to go away.
5. Wake the frame endpoint's one waiter. Do not call `proc_wake` on a shared reason. The consumer's recheck then observes "no driver" and does not sleep, and does not load a ring pointer. On this one CPU the consumer is not running during exit: CPL 0 is not preempted, so the wake only marks it runnable.

`vmm_free_pml4` then frees the shared ring and any DMA run whose reset completed and whose invalidation completed. Those leaves are not `PTE_DEVICE`. `driver_quiesce` does not call `dma_free_pages`, and `DrvDmaAlloc` does not insert the same frames into `dma_regions`. A second free would hand the PMM a page it has already taken back. `PTE_DEVICE` stays on the MMIO leaves, so `vmm_free_user_pt` does not free a device frame.

If the status readback does not return 0, or the IOTLB invalidation does not complete, those queue and packet pages are not returned to the PMM. `vmm_free_user_pt` frees every present user leaf that lacks `PTE_DEVICE`, so a list by itself does not save them. Before `vmm_free_pml4`, `driver_quiesce` records each such frame on `dma_quarantine` and sets `PTE_DEVICE` on its user leaf. The free walk then skips it. The list owns the frame until reboot. Pages whose reset and invalidation both finished keep `PTE_DEVICE` clear and are freed once. The shared frame rings are not in the device domain, so they are not marked and they are still freed once the consumer has dropped its pointer.

`NetInfo` then returns `Errno.NoDev` (-19). That is the same result as "no driver has registered". A zeroed struct with `link_up = 0` would look like a NIC. The kernel does not synthesize `link_up = 0` with a remembered MAC. Quiesce is the device side of "link down". `Errno.NoDev` is the userspace side.

### 4. One waitable interrupt

Syscall `DrvIrqWait` = 220. The argument is a `CAP_TYPE_IRQ` handle. The handler checks that the caller holds it for this device, then uses the same brackets `irq_wait_vector` uses:

```ritz
disable_interrupts()
lapic_watchdog_arm(VIRTIO_NET_RX_WAIT_TICKS)   # 0x00020000, one round
waitq_park()                                   # proc_block(BLOCK_IRQ, 0); sched_block
lapic_watchdog_stop()
enable_interrupts()
return 0
```

`waitq_park` is entered and left with interrupts off. `VIRTIO_NET_RX_WAIT_TICKS` is the bound `virtio_net_wait_rx` already passes to `irq_wait_vector` with `max_rounds` 1 (`drivers/virtio/net.ritz`). The driver re-reads the used ring and the TX ring after every return, including a watchdog wake, then parks again if both are idle.

`sched_tick` calls `proc_wake(BLOCK_IRQ)` only when `lapic_watchdog_expired()` is true, and that stays false while `lapic_watchdog_active` is 0. Arming is what connects the backstop. After `lapic_timer_start`, `lapic_watchdog_arm` sees `lapic_tick_initial != 0` and rides the periodic tick: it counts scheduler periods and does not reprogram the timer. One period at `SCHED_HZ` 100 is 10 ms. `lapic_watchdog_stop` then clears `lapic_watchdog_active`. It does not touch the periodic timer, because this arm was not a one-shot.

The first `DrvIrqWait` of the cutover runs before `sched_start`, so `lapic_tick_initial` is still 0 and `lapic_watchdog_arm` takes the one-shot path: vector 96, `lapic_watchdog_oneshot = 1`. That one-shot does not wake the parked driver. `irq_handler` calls `sched_tick` only for vector 32 (`irq_num == 0`). Vector 96 is `IRQ_STUB 65`, `irq_num` 64. `msix_dispatch` accepts 64–79 and 80–95 and returns false for 96, and the handler then EOIs. `sched_yield` returns when the driver's `sched_block` switches back to pid 1, which is before the one-shot can fire and before `lapic_watchdog_stop` inside this handler runs. Pid 1 therefore calls `lapic_watchdog_stop` itself, then `sched_start`. Stop masks the one-shot (`LAPIC_TIMER_MASKED`) and clears `lapic_watchdog_oneshot`. `lapic_timer_start` then calibrates and installs the periodic tick. Leaving `oneshot` set across that calibration would make `lapic_watchdog_expired` read `LAPIC_TIMER_CURRENT == 0` on the periodic counter. The driver's later `lapic_watchdog_stop`, after a TX kick or an MSI-X wakes this first park, is idempotent: `lapic_watchdog_active` is already 0.

Every later park is after the periodic tick exists, so the arm rides `sched_tick`. An MSI-X that lands after the driver has read the device and before `proc_block` finds no `PROC_BLOCKED` waiter. `proc_wake` does not change `PROC_RUNNING`. The tick-riding watchdog is what wakes that park when no second TX kick arrives. The frame consumer in section 6 rechecks under `cli` and also wakes when its own deadline passes. That wake names the frame endpoint. It is not this device watchdog. The device wait cannot use the same recheck, because the missed event is an IRQ that already ran.

The kernel does not inject the vector and does not load a ring-1 IDT. The process holds a `CAP_TYPE_IRQ` handle, and `DrvIrqWait` checks that handle. The handle is the right to park on the device's vector. It is not a userspace IDT entry. Gate bytes stay `IDT_GATE_INTERRUPT` (0x8E, DPL 0). Hardware delivery does not consult gate DPL. Software `int` from CPL 1 does, and fails. `IDT_GATE_USER` (0xEE) is not used.

`irq_handler` order for MSI-X stays: `msix_dispatch`, `waitq_wake_irq`, then `lapic_eoi`. The waiter cannot run until the ISR irets, so the EOI has completed before the driver executes. The driver does not EOI.

`DrvIrqWait` from ring 3 returns `Errno.Perm`. From a CPU that cannot park it returns `Errno.Again` (-11), the errno `proc_enter_init` already uses when a slot is unavailable. The boot path does not call it until the driver Proc exists.

### 5. MMIO and DMA syscalls

Numbers sit past the last userspace ABI group. Framebuffer is 210–211. Debug is 254–255. The device and snapshot group is 220–227.

| Number | Enum | Arguments (rdi, rsi, rdx) | Returns |
|---|---|---|---|
| 220 | `DrvIrqWait` | `CAP_TYPE_IRQ` handle | 0, or `Errno.Perm` / `Errno.Again` |
| 221 | `DrvMmioMap` | `CAP_TYPE_MMIO` handle | user VA, or a negative errno |
| 222 | `DrvDmaAlloc` | `CAP_TYPE_IRQ` handle, size, pointer to `DmaAlloc` | user VA, or a negative errno |
| 223 | `DrvRingKick` | `CAP_TYPE_IRQ` handle | 0, or `Errno.Perm` |
| 224 | `NetInfo` | user pointer | 0, or `Errno.NoDev` / `Errno.Fault` |
| 225 | `NetAddr` | user pointer | 0, or `Errno.NoDev` / `Errno.Fault` |
| 226 | `NetPublish` | `CAP_TYPE_SHM` handle | 0, or `Errno.Perm` / `Errno.Again` |
| 227 | `ShmMap` | `CAP_TYPE_SHM` handle | user VA, or a negative errno |

60 and 61 are not in this table. `numbers.ritz` keeps them free for their Linux meanings, which is why `Sync` is 162 (AGAST #4321). `net_ping` is not given a number.

`DmaAlloc` is 16 bytes, size taken with `sizeof`: `iova: u64`, `size: u64`. The VA is the rax return, matching the brief. `iova` and the granted size are copied out. `uptr_check_write` covers the pointer before the copy, the same check `sys_fb_info_handler` uses. A faulting pointer returns `Errno.Fault` (-14).

MMIO grants are uncached. There is no cache-type argument and no write-back MMIO.

Virtio capability ranges are byte-sized and can share a page. `vio_find_mmio_caps` already records a BAR, a byte offset, and a length. A grant is the complete pages that cover that byte range, not a page-aligned request that must sit strictly inside it. The kernel keeps one record per window in kernel memory: page base, byte offset of the capability within the first page, length, and the notify multiplier. `DrvMmioMap` resolves the handle against that record. The bytes at `0x0300` repeat the list for the driver's convenience and are not authoritative. The driver adds the offset to the mapped page. It does not pass a raw physical address.

`DrvMmioMap` takes a `CAP_TYPE_MMIO` handle. The kernel granted one such capability per recorded window when it spawned the device process. The handle's `object_id` is that window. A handle the caller does not hold is `Errno.Perm`. An object that is not one of those windows is `Errno.Inval`. The kernel maps every page of that window into this process's PML4 at `DRV_MMIO_BASE`, using the window record in kernel memory. It never reads a page base, a length, or a notify multiplier back from the shared region. The map is not installed in any other PML4. A page that also contains a protected register, the MSI-X table or the PBA, is not a grant. The call returns `Errno.Inval` and maps nothing. The kernel keeps programming those registers through its own `U/S = 0` mapping. A failure halfway through the pages unmaps the pages this call already installed.

`DrvDmaAlloc` and `DrvRingKick` take the device's `CAP_TYPE_IRQ` handle. That handle is what used to be proposed as a process-wide driver bit. The bytes at `0x0300` in the shared region are a convenience copy of the window list and the MSI-X indexes. The page is writable because it also holds the rings, so those bytes are advisory. Overwriting them does not change what `DrvMmioMap` maps.

`DrvDmaAlloc` zeroes each page before the bytes are reachable from the device or from the process. A failure halfway through unmaps and frees the pages this call already installed, and does not publish their IOVAs.

Pages are mapped at `DRV_MMIO_BASE` = `0x7E8000000000` (PML4[253]), bumping a per-process cursor inside that 512 GiB slot. PML4[254] is the framebuffer (`0x7F0000000000`). PML4[255] is the user stack. Flags passed to `vmm_map_page`, which ORs `PTE_PRESENT` itself:

`PTE_WRITABLE | PTE_USER | PTE_WRITE_THROUGH | PTE_CACHE_DISABLE | PTE_DEVICE | vmm_nx_flag()`

That is the kernel `vmm_map_mmio` cache type (PCD|PWT, PAT bit 7 clear, uncached) plus `PTE_USER` and `PTE_DEVICE`. `PTE_DEVICE` (bit 9, value 512) is the software bit `vmm_free_user_pt` already honors so a process exit does not `pmm_free_page` a device frame. `vmm_map_page` propagates `PTE_USER` up PDPT/PD/PT when the leaf asks for it. NX follows `g_pte_nx` (set when EFER.NXE is on).

`DrvDmaAlloc` checks the `CAP_TYPE_IRQ` handle, rejects 0 and any size above 4 MiB (`Errno.Inval` / `Errno.NoMem`), rounds up to pages, and allocates one contiguous run with `dma_alloc_pages` (`pmm_alloc_contig`). Non-contiguous pages are not stitched together (AGAST #4427). The copied-out address is the IOVA in this device's DMA domain, which is the address the driver programs into a queue register. On a domain that uses identity translation the IOVA equals the physical address. The field is still the IOVA. The pages are mapped for the CPU at `DRV_DMA_BASE` = `0x7E0000000000` (PML4[252]) with:

`PTE_WRITABLE | PTE_USER | vmm_nx_flag()`

No `PTE_CACHE_DISABLE`, no `PTE_WRITE_THROUGH`, no `PTE_DEVICE`. The pages are PMM RAM. `vmm_free_user_pt` frees them once on exit because `PTE_DEVICE` is clear. `driver_quiesce` does not also call `dma_free_pages`. Write-back matches the physmap the in-kernel driver already hands to the device. virtio-pci on x86 is DMA-coherent; the in-kernel driver publishes descriptors with `memory_barrier()` (`fence()`, seq_cst) before `vq_notify`. The ring-1 driver does the same before notify. Uncached DMA would be a new, untested mapping and is not required for this device.

### DMA domain

Write access to virtio queue-address registers lets the NIC DMA wherever its requester is allowed to. CPU page tables do not constrain that. `vtd.ritz` never sets TE, and `amdvi.ritz` builds device-table entries as DMA pass-through. The cutover therefore installs a private translated domain for this requester before bus mastering is enabled for the driver and before any page that contains a queue-address register is mapped into the process.

The requester is PCI segment and device identity, `segment << 16 | bus:dev.fn`, plus the DMA aliases the DMAR or IVRS table names for it. A unit that cannot translate, or a requester that cannot be named, refuses the cutover. Virtio stays in the kernel on that boot, and `virtio_net_init` stays in the tree for as long as untranslated boots are supported. Both owners are maintained. `\harland\net-selftest` without an IOMMU keeps the in-kernel path.

The translating boot is a second run of `test_msix_boot.sh`, in CI, added with the DMA domain (PR 5b) and required again at the cutover (PR 7). QEMU does not put a virtio device behind `intel-iommu` unless the device is created with `iommu_platform=on`, and `intel-iommu` on this host wants the q35 machine. `intremap=on` wants `kernel-irqchip=split`. The run is:

```text
-machine q35,kernel-irqchip=split
-device intel-iommu,intremap=on
-device virtio-net-pci,disable-legacy=on,iommu_platform=on
```

The ring-1 driver negotiates `VIRTIO_F_ACCESS_PLATFORM` (feature bit 33). Without the flag and the bit, the device DMAs to guest-physical addresses and a domain walk can pass while proving nothing. The acceptance check is a fault from the IOMMU when the device is given an IOVA outside the domain. A walk that merely shows the framebuffer unmapped is not that check.

The domain maps only the granted queue pages and the packet pages from `DrvDmaAlloc`. The frame rings, the framebuffer, kernel RAM, and every other device's buffers are absent. Device permission on those IOVAs is read-write. The mapping lives until `driver_quiesce` invalidates it. The acceptance check is that the NIC writes an allocated buffer, and a walk of the domain shows the framebuffer and a kernel page have no mapping.

The shared ring is not allocated through `DrvDmaAlloc` and is not entered in the domain. The kernel allocates it at spawn with `pmm_alloc_contig`, maps it user at `DRV_RING_BASE` = `0x7D8000000000` (PML4[251]) with the DMA leaf flags (write-back, user, NX, not `PTE_DEVICE`), and reads it through the physmap. One physical run, two CPU views. The physmap is not a second owner of the frames. `vmm_free_pml4` is the one `pmm_free_page` of those leaves, and only after `driver_quiesce` has cleared the kernel pointer and finished the domain invalidation.

`USER_MMAP_END` is `0x7FFFFFF00000`, above these windows, and `mmap_cursor_pick` will occupy a present page only by skipping it. `sys_mmap_impl` and `sys_munmap_impl` both reject any range that overlaps `[DRV_RING_BASE, USER_STACK_BASE)`, including a request that starts below the window and runs into it. A `MAP_FIXED` request there returns `Errno.Inval`. `sys_munmap_impl` today frees any page-aligned address inside `[USER_MMAP_START, USER_MMAP_END)`, and these windows sit in that span, so the overlap check is the change. The framebuffer address stays where it is.

Ring 3 cannot map a BAR. The kernel mapping of the BAR is `U/S = 0` and remains unreachable from both CPL 1 and CPL 3.

### 6. Portable SPSC ring

The protocol lives in a new leaf package `projects/harland/driver_abi/`, on the pattern of `boot_abi`: structs and constants, no kernel imports, compiled by the kernel, by the indium driver, and later by a Linux port. Slot sizes come from `sizeof`. A hardcoded byte count is how Zeus's request slot drifted (AGAST #2464: a literal 48 hid a larger struct and overlapped the arena).

`[[repr_c]]` is a compile error (LANGUAGE_SPEC §17). These structs are not `[[packed]]`: packed layout would delete the cache-line gaps, and its alignment is 1. The default layout is the one §17.4 shows for an unpacked struct, where a `u16` followed by a `u64` occupies 16 bytes because each field is naturally aligned. The explicit pad arrays are that layout written out, so a reader can see the gaps. They are the byte contract with Linux and Win64, which do not read a Ritz attribute. A host test in `driver_abi` asserts `sizeof` and every field offset against the table below.

`[[align(N)]]` does not exist. Padding a struct by hand is the wrong long-term spelling, and AGENT.md says to fix the language rather than live with that. The language change is `[[align(64)]]` on a field. It lands in ritz before PR 6, or PR 6 carries it. The pads come out when the attribute exists, and the same host test has to pass unchanged. Until that attribute is in the compiler, the pads stay, because an unpackaged comment cannot keep the offsets.

The virtqueue itself is a second leaf, `projects/harland/virtio_abi/`. `drivers/virtio/common.ritz` imports `klog`, port I/O, `pmm`, `heap`, and `vmm_map_mmio`, and it is shared with `blk.ritz` and `input.ritz`, which stay in the kernel. A CPL-1 binary cannot import any of those. `virtio_abi` holds the transport-independent virtqueue and the feature-bit negotiation, and it takes allocation and register access as parameters. It imports none of the kernel modules. The in-kernel block and input drivers, the in-kernel net driver on a boot with no IOMMU, and the indium net driver all call it. PR 7 adds the package. It does not copy `vq_*` into the driver.

Two directions, two rings, one region. Names are from the driver's point of view of the frame, and they are not symmetric in who produces:

| Ring | Producer | Consumer | Payload |
|---|---|---|---|
| RX | ring-1 driver | ring-2 network service. This slice seats the kernel stack there | One Ethernet frame, virtio-net header already stripped |
| TX | ring-2 network service. This slice seats the kernel stack there | ring-1 driver | One Ethernet frame, driver adds the virtio-net header |

Virtio `VringDesc`, avail, and used rings stay the device DMA queue inside the driver. They are not this ABI. Zeus `RequestSlot` / `ResponseSlot` (HTTP method, path, headers) are not this ABI.

```ritz
struct FrameDesc
    length: u32
    flags: u32
    arena_off: u32
    _pad: u32

struct SpscCtrl
    write_idx: u64
    _pad_w: [56]u8    # write_idx owns bytes 0..63
    read_idx: u64
    _pad_r: [56]u8    # read_idx owns the next line
    wake: u32         # Linux futex word. Not a u64.
    _pad_k: [60]u8    # the rest of that line
```

`flags` values: `FRAME_F_NONE = 0`. A lease-handoff flag is not defined. Depth `FRAME_RING_CAP = 256`, the virtqueue cap, a power of two. The mask is 255. The device offer of 1024 is not the depth; the driver already refuses a queue above 256. Depth 256 does fill. 256 completions with a consumer that has not run is a full ring. The posted virtio pool is only 32 buffers, so the SPSC fills before the device queue does whenever the consumer is behind. The 300-send burst is larger than 256 and depends on the producer waiting, below, rather than on the ring never filling.

`FRAME_MAX = 2048`, `VIRTIO_NET_RX_BUFFER_SIZE`. That covers MTU 1500, the Ethernet header, and the 10- or 12-byte virtio header the driver strips before publish. Each arena is `256 * 2048 = 524288` bytes. Both arenas are 1 MiB. Descriptors are `256 * sizeof(FrameDesc)` per ring. With the struct above, `sizeof` is 16 and each descriptor ring is one page. Indexes are monotonic `u64`. The slot is `seq & 255`.

`SpscCtrl` puts `write_idx` and `read_idx` on separate 64-byte lines. Zeus `ControlBlock` does not: `req_write_idx` is offset 0 and `req_read_idx` is offset 8, and `control_block_size` returning 128 does not split them. The wake word is on a third line so a consumer spinning on `wake` does not share a line with the index the producer stores. 64 bytes is the line Zeus documents and the line x86 and Windows-on-ARM use. Padding is not the publication rule. `wake` is a `u32` because classic Linux futex operations wait on a 32-bit word. A `u64` wake cannot be that word.

Publication, producer. Atomics take pointers (§18.5):

1. Write the frame bytes at `arena_off`, then the descriptor (`length`, `flags`, `arena_off`).
2. `atomic_store(@ctrl.write_idx, next)`. That store is `seq_cst`. The plain writes sit before it, which is the side a `seq_cst` store orders against a later `seq_cst` load. The frame ring needs no extra `fence()`. The seqlock in section 7 does, because its plain bytes sit on the wrong side of a bare atomic.
3. `atomic_fetch_add(@ctrl.wake, 1)`, then the OS wake below.

The consumer `atomic_load(@ctrl.write_idx)` runs before it reads the slot. It does not read a slot at or past the index it loaded. After it finishes the slot it `atomic_store(@ctrl.read_idx, r + 1)`. Empty is the two indexes equal. Full is a difference of 256. The producer does not publish a slot the consumer has not released, and it does not drop one.

A full ring stalls that direction's producer until `read_idx` advances. It does not drop the frame, and it does not stop the other direction.

- RX. The driver does not take the virtio used element, and does not replenish that descriptor, until the RX ring has a free slot. The frame stays on the device queue. While it waits it keeps draining TX, so a full RX ring still reclaims send buffers and still completes the device's used ring. Each time the ring is still full it calls `Yield` (syscall 24). `sched_yield` switches even when `sched_running` is 0, which is the window before `sched_start`, where the timer does not preempt. The driver does not park on the frame endpoint. A `cli` spin would deadlock: the consumer cannot run while the producer holds the CPU with interrupts off.
- TX, while the kernel holds the seat. The kernel send does not return success while the TX ring is full. With interrupts disabled it rechecks `read_idx`. While the ring is full and `driver_registered` is set, it wakes the driver pid and `sched_yield`. `proc_pick_next` returns the first runnable slot after the current one, so the wake has to happen before the yield or the yield finds only pid 1 and returns. The driver drains TX and blocks again in `DrvIrqWait`. The yield returns with interrupts still off, because `sched_yield` restores the caller's IF and the caller had cleared it. The send then rechecks. Success is the `atomic_store` of `write_idx` after a free slot was observed. If `driver_registered` is clear, the send returns `Errno.NoDev` and does not count as a transmitted packet. A CPL-0 spin on `read_idx` without yielding never runs the driver, so that is not the wait. The ring-2 service, which is both consumer and producer, does not block itself on this wait. Its pending-send cap is in `RING2_NET.md`.

The frame ring has one registered waiter, the current RX consumer. `proc_wake(reason)` in `proc/table.ritz` marks every `PROC_BLOCKED` process with that reason runnable. The frame path does not call it. A kick, a deadline, and `driver_quiesce` wake that one pid. A second waiter, including a later app attachment, is a different endpoint. `BLOCK_IRQ` stays the device park in section 4, and this cutover has one driver on it.

A kick that lands after an empty check and before `proc_block` is overwritten by the block, and `sched_block` then sleeps on a ring that already holds a frame. The RX consumer uses the same section `wait_for_child` uses, and the same one `irq_wait_vector` uses before `waitq_park`, and it also leaves when its deadline passes:

`driver_registered` is a `bool`. So is `net_via_ring`. The `u8` flags already in `Proc` predate `bool` and are not the pattern for these.

```ritz
enum RxWait
    Frame
    Timeout
    NoDriver

fn take_rx(ctrl: *SpscCtrl, deadline: u64) -> RxWait
    disable_interrupts()
    while driver_registered and not deadline_passed(deadline)
        let w = atomic_load(@ctrl.write_idx)
        let r = atomic_load(@ctrl.read_idx)
        if w - r > 256
            enable_interrupts()
            kill_device_owner()
            return NoDriver
        if w == r
            block_on_frame_endpoint(deadline)
            sched_block()
            continue
        match check_slot(ctrl, r)
            Bad =>
                atomic_store(@ctrl.read_idx, r + 1)
                continue
            Good =>
                copy_slot(ctrl, r)
                atomic_store(@ctrl.read_idx, r + 1)
                enable_interrupts()
                return Frame
    enable_interrupts()
    if not driver_registered
        # do not load the ring pointer. vmm_free_pml4 has already run:
        # on this CPU the consumer is switched to only after sched_exit.
        return NoDriver
    Timeout
```

`RxWait` is the kernel function's result. It is not a syscall return, and it is not `1`, `0`, and `-1`, which collide with an errno. `Frame` means a slot was copied for dispatch. A rejected slot stores `read_idx` past itself and continues the wait. It does not return `Frame`. `Timeout` is a quiet link: the caller rechecks its window. `NoDriver` means the owner is gone.

An occupancy above 256 is the producer writing a `write_idx` the ring cannot hold. The consumer does not walk it and does not advance `read_idx` across it, because there is no honest slot to skip to. On the RX ring that producer is the device owner, so the consumer kills that process and `driver_quiesce` runs. The ring does not stay wedged under a live driver. On the TX ring the producer is whoever holds the seat. While that is pid 1, a bad occupancy is a kernel bug and the send path stops and logs. It does not kill init. Once the service holds the seat, a bad TX occupancy kills the service and runs the frame-seat fault path in `RING2_NET.md`.

`sched_tick` wakes the frame endpoint when that deadline has passed. It still wakes `BLOCK_IRQ` only for the device watchdog. The copy finishes before the next park. The consumer does not resume a copy after a wake that sees `driver_registered` clear. `driver_quiesce` wakes the frame endpoint so a consumer blocked in the DHCP window takes the empty recheck and leaves. A quiet link, including one that goes silent after DHCP, returns `Timeout` instead of sleeping until a frame that is not coming.

Before any copy or dispatch the consumer checks the peer's words. DMA isolation does not make them trustworthy: the driver still has the shared CPU mapping.

- The slot index is `seq & 255`. The arena offset is derived from that slot, `(seq & 255) * FRAME_MAX`. The descriptor's `arena_off` must equal that value. A mismatch is `Bad`.
- `length` must be in `1..=FRAME_MAX`. Any other length is `Bad`. `flags` must be `FRAME_F_NONE`. Any other value is `Bad`.
- A `Bad` slot is not copied and not dispatched. The consumer stores `read_idx` past it so one bad descriptor cannot pin the ring, and the serial log counts the reject. The wait returns `Frame` only from the `Good` arm.

The kernel is the side that validates. The driver validates TX descriptors with the same three checks before it programs a device buffer. A bad TX slot is not given to the NIC. The driver stores its `read_idx` past it and counts the reject.

A per-slot complete flag is what `zeus_client_peek_response_slot` needs because it peeks out of FIFO order and because the worker stores `id` before the rest of the slot. The comment there states the assumption this protocol refuses: "On x86 (TSO) and ritz's plain memory writes, source-order stores are observed in order, so COMPLETE-after-id-and-fields is a safe release fence." There are no atomics on that path. FIFO plus a `seq_cst` index store does not need the flag. `fence()` followed by `volatile_store` of the index is also rejected: volatile is not an atomic, and a fence synchronizes only with other atomics.

`io.ritz` `read_barrier` / `write_barrier` are `lfence` / `sfence` in x86 assembly. They stay available for the device path inside the kernel. They are not the portable publish.

No new compiler intrinsic. §18.5 already says weaker orders can be added when a measurement asks for them. `seq_cst` is a correct implementation of release-store / acquire-load, which is the property the other ports must honor.

The region is `0x103000` bytes: 1 MiB of arenas plus three pages. Page-aligning both controls, both descriptor arrays, and the link record separately would be five pages, so both controls and the link record share page 0. The kernel zeros the region before the process starts. Both indexes start at 0. `link_seq` starts at 0, which section 7 defines as unpublished.

| Offset | Size | Contents |
|---|---|---|
| `0x0000` | `0x100` | RX `SpscCtrl`. `write_idx` at 0, `read_idx` at `0x40`, `wake` at `0x80`. Bytes `0xC0..0xFF` are unused so the next block starts on a 256-byte boundary. |
| `0x0100` | `0x100` | TX `SpscCtrl`. `write_idx` at `0x100`, `read_idx` at `0x140`, `wake` at `0x180`. |
| `0x0200` | 32 | `NetInfo`. |
| `0x0220` | 8 | `link_seq`, a `u64`. |
| `0x0300` | to `0x1000` | Advisory copy of the window list and the MSI-X indexes. The kernel's authoritative copy is in kernel memory. `DrvMmioMap` does not read this span. The page cannot be read-only, because the control blocks and `NetInfo` share it. |
| `0x1000` | 4096 | RX `FrameDesc[256]`. |
| `0x2000` | 4096 | TX `FrameDesc[256]`. |
| `0x3000` | 524288 | RX arena. |
| `0x83000` | 524288 | TX arena. The region ends at `0x103000`. |

OS mapping of that same layout:

| OS | Share | Wake |
|---|---|---|
| Harland | PMM pages. `CAP_TYPE_SHM` names the region. `ShmMap` (227) maps it. The kernel grants that capability and calls the same map path at spawn, into the driver CR3 at `DRV_RING_BASE`. A later attach, including a ring-3 app, uses `ShmMap` again. Kernel reads the physmap. `CapRevoke` (41) drops the handle and the mapping. | Device: `DrvIrqWait` parks `BLOCK_IRQ`; the ISR and a TX publish wake the driver pid. Frames: `DrvRingKick` wakes the frame endpoint's one waiter. The shared `wake` `u32` is still incremented so the bytes match the other ports. No futex, no memfd. |
| Linux | `memfd_create` + `mmap(MAP_SHARED)`. The fd crosses processes with `SCM_RIGHTS`, the mechanism `projects/zeus/src/main.ritz` already uses for a different layout. | `FUTEX_WAIT` / `FUTEX_WAKE` on the `u32` at `wake`. Not `FUTEX_PRIVATE`: the word is cross-process, which Zeus already requires. |
| Win64 | A pagefile-backed section, `MapViewOfFile`. The event handle crosses processes with `DuplicateHandle`. | A shared event, plus a recheck of the index after the wait returns. `WakeByAddressSingle` and `WaitOnAddress` are process-local and are not the wake. |

No Win64 code. The Harland wake word is still updated with `atomic_fetch_add` so a later port waits on the same bytes. The add is on the `u32`.

The kernel is the RX consumer and the TX producer until the ring-2 service takes that seat. Replacement is a change of who maps the consumer side, not a change of `FrameDesc`. The service then owns the address record. The kernel releases its own lease with DHCPRELEASE and does not copy it into that page. Frames the in-kernel consumer does not handle keep today's behavior, in `handle_ipv4_packet` and `handle_udp_packet`: TCP returns 0, UDP only DHCP. This slice does not grow that consumer.

`channel.ritz` is not used for frames, for the link record, or for the kick. A 16-deep copied queue is a different transport with a different failure mode. One dataplane.

`DrvRingKick` (223) is the producer's wake on Harland. It checks the `CAP_TYPE_IRQ` handle, wakes the frame endpoint's consumer pid, increments that ring's `wake` `u32`, and returns 0. It does not copy a frame and it does not call `proc_wake` on a shared reason. The consumer parks with the `cli` recheck above, not with a bare `proc_block`. During the self-test that consumer is pid 1, still on the boot stack at CPL 0, which is how `sched_switch` already returns to whoever called it. After the window the same wait is what a later kernel poll calls. A ring-2 process later blocks on the same endpoint, with the same recheck, once it is the registered consumer. The driver does not block on that endpoint. Its full-ring wait is the preemptible spin, which keeps draining the other direction, and its device wait is `BLOCK_IRQ`.

TX publish from the kernel is the mirror once a slot is free: fill the slot, `atomic_store` the TX `write_idx`, `atomic_fetch_add` the TX `wake`, wake the driver pid. The driver treats that as a spurious device wake and drains TX before it waits again. The full-ring yield above is what happens when that publish cannot yet store the index. A group that still fits in the ring also yields. Section 9 says when, because fitting in 256 slots is the usual case for a group of four.

### 7. Link snapshot

`Syscall.NetInfo = 224`, added to the enum in the same change as its handler. `numbers.ritz` forbids a variant without a handler, and `test_every_declared_syscall_is_dispatched` enforces it. The header comment keeps 60 and 61 free for their Linux meanings. It does not reserve them for `net_info` or `net_ping`. The ABI dict gains `"NetInfo": 224`, `"NetAddr": 225`, `"NetPublish": 226`, and `"ShmMap": 227`. `ritzlib/sys.ritz` gains the matching `[[target_os = "harland"]]` constants. Linux `SYS_EXIT` is 60 and stays a Linux number. Harland `SYS_EXIT` stays 20.

```ritz
struct NetInfo
    mac: [6]u8
    link_up: u8
    device_type: u8     # NETDEV_TYPE_VIRTIO = 1 when this driver publishes
    mtu: u32
    ipv4: [4]u8
    gateway: [4]u8
    netmask: [4]u8
    dns: [4]u8
    configured: u8      # 0 for the life of this design
    _pad: [3]u8
```

`NetInfo` takes the user pointer in rdi. `uptr_check_write(p, sizeof(NetInfo))` or `Errno.Fault`. On success it copies `sizeof(NetInfo)` from the kernel snapshot and returns 0. Any process may call it. The snapshot is not a secret.

The only writer of the shared record is the ring-1 driver. The kernel does not write those bytes. Zeroed memory starts at `link_seq == 0`, and 0 is even, so "even means stable" would publish a NIC of zeros the moment `driver_registered` is set. `link_seq` 0 is unpublished. It is not a generation.

The driver publishes with a seqlock, and the first stable generation is 2. Ritz atomics are `seq_cst` loads and stores (§18.5). They do not keep a plain store from rising above an earlier atomic, and they do not keep a plain load from sinking below a later atomic. `fence()` is the operation that orders plain accesses against the atomics around them.

1. `atomic_store(@link_seq, even + 1)`. The first store is 1. An odd value means a write is in progress.
2. `fence()`. Without it the plain writes in the next step can become visible under the previous even generation.
3. Write the `NetInfo` bytes.
4. `atomic_store(@link_seq, odd + 1)`. The first stable value is 2. Every later stable value is the next even number, and it is never 0.
5. `NetPublish` (226) with the link region's `CAP_TYPE_SHM` handle. This is the only refresh. A link that goes up or down after the self-test does not reach `NetInfo`, or the ring-2 wait, until this call runs. `DrvRingKick` stays a frame wake and does not sample the record.

The kernel's sample, inside `NetPublish`:

1. `s1 = atomic_load(@link_seq)`. An odd value, or a value below 2, leaves the previous snapshot in place and returns `Errno.Again`.
2. Copy `NetInfo`.
3. `fence()`. Without it the copy can sink below the second load and a torn copy validates.
4. `s2 = atomic_load(@link_seq)`. If `s2 != s1`, retry a bounded number of times and then leave the previous snapshot. If `s2 == s1`, commit the copy and wake the frame endpoint so the ring-2 wait observes the new generation.

`NetInfo` and `net_get_mac` read the snapshot. They do not return bytes from the shared page, and they do not sample it themselves. `driver_quiesce` invalidates the snapshot, step 4 of the death path, before the page is freed, and does not store a zero MAC into it.

`configured` stays 0 and the address fields stay zero in this record. `ip_set_config` keeps writing `net/ip.ritz` for the in-kernel stack's own transmit during this slice. It does not write `NetInfo`. The lease stays with the stack. When that stack moves to ring 2, the service publishes addresses on its own record and readers use `NetAddr` (225). The driver does not apply a lease. Userspace that calls `NetInfo` sees MAC, `link_up`, MTU, and device type from the snapshot.

`link_up` is 1 only when virtio-net status bit 0 is set, the bit `virtio_net_init` already logs as UP. `mtu` is 1500. `device_type` is `NETDEV_TYPE_VIRTIO` (1).

Until the first stable generation is in the snapshot, and again after `driver_quiesce` invalidates it, `NetInfo` returns `Errno.NoDev`. It does not return a zeroed `NetInfo`. It does not call `ip_is_configured`, `net_get_mac`, or `netdev_get_default`. Generation 0 stays unpublished for the life of the record.

A host test of the seqlock, if it can force the plain accesses onto the wrong side of the atomics, fails when the `fence()` calls are removed. The frame-ring test does not need that reorder: its plain accesses already sit on the correct side of each atomic.

### 8. virtio-net move

Stays in ring 0:

- IDT, including MSI-X vectors 64–79 on IST 2, and the LAPIC EOI.
- PCI enumeration, bus-master enable, the kernel `vmm_map_mmio` of the BARs, MSI-X capability enable, and `msix_set_entry` aimed at the BSP. The process never receives the MSI-X table, so it cannot change the APIC ID in the message address.
- The IPv4 stack, ARP, ICMP, UDP-DHCP, and the TX burst, for this slice. They consume and produce the SPSC rings. Their home is the ring-2 service, which takes this seat later without a layout change.
- ENA, unchanged, including `network_wait_for_peer_ping`.

Moves into the indium virtio-net program at CPL 1. The kernel blk and input drivers keep using `virtio_abi` from ring 0:

- Feature negotiation, queue allocation in `DrvDmaAlloc` memory, queue address registers, `DRIVER_OK`.
- RX and TX processing, descriptor reclaim (the AGAST #4073 rule: a TX buffer stays busy until the used ring returns it; the boot burst sends 300 and requires more than 256 distinct replies).
- Reads of MAC and link status from device config MMIO.
- Publishing `NetInfo` and RX frames. Consuming TX frames. `DrvIrqWait` and `DrvRingKick`.
- Writing virtio `queue_msix_vector` / config MSI-X registers in the common config after a device reset. The kernel keeps the three table indexes (config, RX, TX) in kernel memory and hands them to the process with the device capabilities. It does not re-read them from the shared page. PCI-level MSI-X enable is already done and survives a virtio status reset; the queue-select registers do not, and they are MMIO the driver is allowed to write. Feature negotiation includes bit 33, `VIRTIO_F_ACCESS_PLATFORM`, on the translating boot.

On a boot with a translated domain, `netdev_init` does not call `virtio_net_init`. `NETDEV_TYPE_VIRTIO` is not registered on that boot. The ring is not a `NetDevice`, and `netdev_get_mac` of a null device still writes six zero bytes. The stack grows a `net_via_ring` bool instead of a fake device. On every boot without translation, `virtio_net_init` still runs, and `drivers/virtio/net.ritz` stays whole. A boot has one of those owners, never both.

`net_stack_init` keeps `arp_init`, `ip_init`, and one `netdev_init` call. After the cutover that probe is ENA only, so on QEMU `dev_count` is 0 and today's function logs `[net] No network devices found!` and returns -1. `network_dhcp_ping` then logs `Network stack initialization failed` and never enters the window. The marker path changes the predicate, not the probe:

```ritz
let dev_count: i32 = netdev_init()
if dev_count > 0
    net_device = netdev_get_default()
    if net_device == null
        return -2
    net_via_ring = false
    net_initialized = 1
    return 0
if ring_driver_published()          # snapshot generation even and >= 2
    net_device = null
    net_via_ring = true
    net_initialized = 1
    return 0
klog("[net] No network devices found!\n")
return -1
```

`ena_init` success is the first branch. `net_via_ring` stays false. The stack does not also read the SPSC rings. A virtio driver that was spawned and then found no device has already exited. A machine that has both keeps ENA as the only `NetDevice`. The virtio queues, if a driver published them, are not a second stack path.

`ring_driver_published` is true only when the kernel snapshot holds a generation that is even and at least 2. The snapshot changes when `NetPublish` runs, and when `driver_quiesce` invalidates it. Nothing else reads the shared page to refresh it. The kernel does not write the shared page.

With `net_via_ring` set, the three I/O functions are the section 6 endpoints. With it clear, they stay the `netdev_*` calls they are today, including `net_send`'s `-1` when `net_device` is null.

- `net_get_mac` copies `mac[6]` from the kernel snapshot. `dhcp_discover` calls it before `net_send` (`dhcp.ritz`, the client MAC at offset 28). A zero MAC from `netdev_get_mac(null)`, or from a snapshot that was never published, is not a discover. The copy requires generation >= 2, which the first park already published.
- `net_send` is the TX producer. Success is the `atomic_store` of the TX `write_idx` from section 6. A missing driver is `Errno.NoDev`, not the `-1` from a null `NetDevice`, and not a success. After each published group the burst yields to the driver even when the ring still has room. Section 9 is that yield.
- `net_poll` pops one RX frame if `take_rx` would see one without waiting, validates it, and dispatches it through the existing Ethernet switch. It does not park. Empty returns 0. An occupancy above 256 kills the device owner. TCP still returns 0. UDP is still DHCP only.
- `net_wait_rx(deadline)` is `take_rx`. It returns `RxWait.Frame`, `RxWait.Timeout`, or `RxWait.NoDriver`. The DHCP loop passes the sooner of `window_end` and `ping_after` until the gateway ping has been sent, then `window_end`. `Timeout` does not call `delay_us(2000)`. The loop body runs, so the window deadline and the deferred ping are checked on a quiet link and on a link that goes quiet after DHCP. The ENA path has no MSI-X park and keeps today's 2 ms delay when its wait cannot block. On the ring path the wait blocks, so pid 1 at CPL 0 lets the driver run until a frame arrives or the deadline does.

`net_is_ready` has no caller outside its definition. It becomes `net_initialized == 1 and (net_via_ring or (net_device != null and netdev_is_running(net_device)))`, so a later caller does not treat a live ring as absent.

A legacy virtio-net (port I/O, no modern MMIO windows) is not claimed by the process. The process exits. A translating marker boot does not also call `virtio_net_init`. An untranslated marker boot does not spawn the process. `test_msix_boot.sh` already passes `disable-legacy=on` on today's run, and the second run adds the q35 and `iommu_platform` flags from the DMA section. `test_tier1_boot.sh` does not set the marker, and `net_stack_init` has no other caller, so that boot's transitional NIC is not probed today and is not probed after the cutover.

The kernel probe records the MMIO windows and programs MSI-X, then spawns the process. It does not set up virtqueues and does not set `DRIVER_OK`. The process does. Until the process does, the device is not armed.

### 9. Self-test cutover

Until the cutover PR, `\harland\net-selftest` keeps today's path: `network_dhcp_ping` calls `net_stack_init`, the in-kernel driver owns the queues, and the log still shows `[dhcp] Configured!`, `[net] TX burst: sent=300/300 replies=` with replies > 256, `[msix] virtio-net: MSI-X on`, interrupts > 0, and `rx waits` with `halted > 0`.

The cutover runs only on a boot that enables DMA translation. A machine with no IOMMU, including today's QEMU net-selftest, keeps `virtio_net_init` and the halt assertion. `test_msix_boot.sh` runs the park-counter assertions only when that boot enables an IOMMU (`intel-iommu`, or the AMD equivalent). The cutover PR does not run both owners. On the translating boot, `netdev_init` no longer initializes virtio. The marker path becomes:

1. `process_create_init` runs before the window. That is the part of today's `process_enter_init` (`syscall/runtime/process.ritz`) which calls `proc_table_reset`, records `g_kernel_pml4`, calls `proc_enter_init` in `proc/table.ritz`, and `fs_process_start(1)`. It does not call `sched_start`. It runs only when `proc_current()` is null. A second call does not reset the table. Pid 1 exists and stays on the boot stack at CPL 0. It is the RX consumer and the TX producer. `sched_running` is still 0.
2. The kernel records BARs, programs MSI-X at the BSP, refuses the boot window if the routed destination is not the BSP, creates the shared region as a `CAP_TYPE_SHM` object, and spawns the device program with `proc_new_child`, `sched_prepare_driver`, and `proc_start`. It grants that process the IRQ capability, one MMIO capability per window, and the shm capability, then maps the region with the same `ShmMap` path an attach uses later. Spawn needs a current process: `proc_new_child` returns `Errno.Srch` when `proc_cur < 0`, which is why pid 1 exists first. A missing ELF fails the window. This step runs only on the translating boot. An untranslated boot calls `virtio_net_init` and does not spawn the process. The driver is `PROC_RUNNING`. The periodic tick is not armed.
3. Pid 1 calls `sched_yield` while `sched_running` is still 0. `sched_tick` returns before `proc_pick_next` when that flag is 0, so a timer interrupt cannot switch the driver back to pid 1. `sched_yield` itself calls `proc_pick_next`, finds the driver, and switches. `USER_RFLAGS` is `0x202`, so the driver enters CPL 1 with IF set, and nothing preempts it. Before its first `DrvIrqWait` it resets the device, sets `DRIVER_OK`, stores `link_seq` 2, calls `NetPublish`, posts the RX buffers, and drains TX. That drain is empty. `NetPublish` copies generation 2 into the snapshot and wakes the frame endpoint. The park's `sched_block` is the only switch back to pid 1. The yield returns with the driver `PROC_BLOCKED` inside that first `DrvIrqWait`, not mid-init and not still `PROC_RUNNING`, and with generation 2 already committed.
4. Pid 1 calls `lapic_watchdog_stop`, then `sched_start` once. Stop drops the one-shot the first park armed (section 4). `sched_start` sets `sched_running` and calls `lapic_timer_start(SCHED_HZ)`. This is still before any send. `run_init` does not call `sched_start` again.
5. `network_dhcp_ping` calls `net_stack_init`. `netdev_init` returns 0. The snapshot makes `net_stack_init` return 0 with `net_via_ring` set (section 8). `dhcp_discover` then calls `net_get_mac`, which copies the snapshot MAC, and `net_send`, which is the first TX publish and the wake of the driver pid. The driver drains that TX before it parks again. `net_wait_rx` takes the window deadline, and the sooner ping deadline until that ping has been sent, so a quiet link still reaches the deferred gateway ping and still ends the window. `network_tx_burst` no longer polls replies with interrupts disabled while the driver stays in `DrvIrqWait`. A group of `NET_TX_BURST_GROUP` (4) sends fits in 256 slots, so the full-ring yield does not run. After each group is published the burst enables interrupts and `sched_yield`s, the TX kick having already made the driver runnable, then polls replies. It yields again when a poll finds the RX ring empty and replies are still short, bounded by the same per-group poll cap the function has today. `sent=300/300` and replies > 256 stay the pass conditions, produced by the same `dhcp_on_ack` and the same counters. `[dhcp] Configured!` stays.
6. `test_msix_boot.sh` stops requiring virtio-net `halted > 0`. Parking does not increment `virtio_net_rx_halts` (`irq_wait_vector` counts a halt only on the `sti;hlt` branch, and the in-kernel virtio path passes `may_park=false`). The script instead requires a driver park count > 0 and the same interrupt count > 0. The interrupt and MSI-X log lines stay, counted by the kernel MSI-X path the kernel still owns (`msix_dispatch`), not by a deleted `virtio_net_irq_count`. NVMe's halt assertions are untouched. NVMe stays in the kernel.

After the window, `run_init` in `main.ritz` loads `/bin/init`. It does not call `process_enter_init`. That function is `process_create_init` plus `sched_start`, and its first act is `proc_table_reset`, which would free the driver slot and leave the device with no owner (`netdev_init` no longer calls `virtio_net_init`, and ENA is not present on the QEMU path). `run_init` sees `proc_is_init(proc_current())`, skips both the reset and the second `sched_start`, loads the ELF into the kernel PML4 pid 1 already uses, allocates the user stack, and `jump_to_userspace` (CS `0x1B`, SS `0x23`, unchanged). The driver Proc remains. It is not killed at the end of the window.

`MAX_PROCS` stays 8. So do `FS_MAX_PROCS` and `KSTACK_SLOTS` (`syscall_entry.s` `.set KSTACK_SLOTS, 8`, locked to `MAX_PROCS` by `test_harland_syscall_stack.py`). The table is `var procs: [8]Proc`. The driver occupies one of those eight for the rest of the boot: pid 1, the driver, and at most six other live or zombie Procs. The ring-2 service later occupies one of those six, so `RING2_NET.md` caps attached apps at five. `proc_new_child` already returns `Errno.Again` (-11) when `proc_free_slot` fails. `KERNEL_CONTRACT.md` already says spawn returns EAGAIN with 8 processes live. That sentence stays true. The resident driver is one of the eight, so the seventh concurrent descendant fails where an eighth used to fit. This design does not raise the ceiling. Raising it would move the literal array, the kernel-stack `.space`, and the contract together, which is a separate change.

### RX path

```mermaid
sequenceDiagram
  participant Dev as virtio-net
  participant Isr as Ring 0 ISR
  participant Drv as Ring 1 driver
  participant Q as RX SPSC
  participant Ip as Ring 0 stack

  Dev->>Isr: MSI-X on a vector in 64..79, BSP
  Isr->>Isr: msix_dispatch, proc_wake BLOCK_IRQ, lapic_eoi
  Isr->>Drv: iret CS 0x429
  Drv->>Dev: used ring in WB DMA, notify and status in UC MMIO
  Drv->>Q: frame bytes, FrameDesc, atomic_store write_idx
  Drv->>Ip: DrvRingKick wakes the frame endpoint
  Ip->>Q: atomic_load write_idx, then the slot
  Ip->>Ip: ARP, or IPv4 to ICMP or DHCP UDP. TCP and other UDP dropped
```

## API and interface changes

Syscall convention, unchanged: number in rax, args in rdi, rsi, rdx, r10, return in rax as a negative `Errno` or a non-negative result. The assembly entry already saves this frame. Handlers stay `fn(rdi, rsi, rdx, r10) -> i64`.

New kernel functions: `sched_prepare_driver`, `process_create_init`, `gdt_get_driver_code_selector`, `gdt_get_driver_data_selector`, the handlers for 220–227, and `driver_quiesce`. `sched_prepare_user` is not generalized with a userspace CPL argument. `process_enter_init` remains the non-net boot path: `process_create_init` then `sched_start`, called once from `run_init` when pid 1 does not already exist. Granting a device uses the existing capability table. There is no `proc_mark_driver`.

`PC_USER_CS` is per-CPU offset 64 and `PC_USER_SS` is offset 72, inside a 128-byte area indexed by `shlq $7`. `percpu_area_init` stores `0x1B` and `0x23`. `sched_use_kstack` overwrites both from the incoming Proc. `syscall_entry`'s iret tail `pushq %gs:`-loads them. `jump_to_userspace` does not.

The return selectors are not a syscall. Ring 3 cannot store `0x429` into its own `Proc`. The kernel writes them at spawn.

Copy-out shapes follow `sys_fb_info_handler`: the user pointer is checked, then the kernel writes a `sizeof` struct. `NetInfo` returns 0 or an errno. `DrvDmaAlloc` returns the VA or an errno and writes `DmaAlloc` through rsi. `DrvMmioMap` returns the VA or an errno.

The frame endpoint records one waiter pid. Waking it marks that pid runnable and does not scan other blocked processes. `proc_wake(reason)` stays the broadcast it is, and the frame path does not call it. `BLOCK_IRQ` stays the device reason.

## Data model

`driver_abi` is the shared schema. No on-disk migration. The region is anonymous RAM, recreated every boot.

`GDT_ENTRIES` 133 to 135 is a boot-time table, not a migrated structure. CPU 0's TSS selector stays `0x28`.

`Proc` grows by the return selectors. `proc_free` / `proc_new_child` clear them so a slot reuse cannot inherit CPL 1. The host test `test_harland_process_model.py` compiles `proc/table.ritz` and does not construct `Proc` literals; it keeps passing if those two functions clear the new fields.

The shared `NetInfo` is not `ip_our_addr`. The kernel snapshot is a separate copy. `NetInfo` (224) reads the snapshot. The kernel does not write the shared page.

## Alternatives considered

### Ring 3 instead of CPL 1

CPL and authorization are separate. This design keeps CPL 1 for the driver and CPL 2 for the service. It authorizes with capabilities.

Page tables do not get simpler either way: `PTE_USER` is already the bit CPL 1 and CPL 3 both need, and kernel pages are already `U/S = 0`. SMEP and SMAP are off, so ring 1 gains no execution or access right that a capability-checked ring-3 process lacks. The iret frame's RPL is written by the CPU. `ARCHITECTURE.md` assigns drivers to ring 1 and the stack to ring 2, and a later call gate into the driver uses `TSS.rsp1`, which exists only for a target CPL of 1. The cost of CPL 1 is the GDT entries, the iret selectors, and the three `== 3` predicates. That cost is the whole of PRs 2 and 3.

### A process-wide driver bit

Rejected. `FbMap` already refuses a caller without `CAP_TYPE_DISPLAY`. A boolean is only as honest as every syscall that remembers to check it, which was the objection this design used to aim at capabilities, and it applies to the bit just as well. A boolean also cannot name a window, an IRQ, or a shared region, and it cannot tell a driver from a ring-2 service once a third CPL exists. `Proc` stores the return CS/SS. `DrvMmioMap` checks `CAP_TYPE_MMIO`. `DrvIrqWait` checks `CAP_TYPE_IRQ`. The frame region, the app exchange, and the address page are `CAP_TYPE_SHM`.

### `NetInfo` as a copy of the in-kernel stack

Rejected. The kernel would fill `NetInfo` from `net_get_mac`, `netdev_type`, `ip_get_our_addr`, and `ip_is_configured`. That ships a userspace link view without moving the device, and it makes the kernel the writer of the record the driver is supposed to own. The moment queues move, every caller of that copy is wrong. `NetInfo` is 224 and copies the driver's snapshot after `NetPublish`. Number 60 stays free.

### Deliver the virtio IRQ as a user-mode interrupt

Rejected for this design. The IDT and the LAPIC EOI stay in ring 0. `irq_handler` already counts the vector and wakes `BLOCK_IRQ`. There is no user-interrupt MSR programming, no ring-1 IDT, and no IST for a CPL-1 handler. Injecting the vector would also fight the timer stub, which assumes a CPL-0 handler. `DrvIrqWait` plus a spurious-wake re-read is the mechanism `irq_wait.ritz` already documents for NVMe.

### `ipc/channel.ritz` as the frame path

Rejected for the dataplane. A send copies a `Message` onto a linked list capped at 16, and the peer copies it out. A 2048-byte frame does not belong there, the cap is below the virtqueue depth, and the layout is not the protocol Linux and Win64 would share. The kick is `proc_wake`, not `ipc_send`. The channel syscalls stay as they are for the programs that use them. They are not extended with a shared-memory mode in this design.

### Append the GDT entries, rather than insert them at index 5

Inserting two descriptors before the TSS moves `GDT_TSS_FIRST` and CPU 0's selector from `0x28` to `0x38`. `tss_selector` would follow, and `ltr` would stay correct, but the constant `GDT_TSS` and the per-CPU test's mental model of "index 5" would lie. Appending leaves every existing selector alone. The per-CPU test's equality changes on purpose, in that PR.

### Uncached DMA

Rejected. The comment in `dma.ritz` is not what virtio runs on. The physmap is write-back, the device gets the physical address, and `memory_barrier` runs before notify. Driver DMA uses that mapping. MMIO stays uncached.

### Kernel-written `link_up = 0` on driver death

Rejected. Writing `link_up = 0` into the shared record would make the kernel a second writer, and returning that struct would look like a NIC that is down. Quiesce invalidates the snapshot instead. `NetInfo` then returns `Errno.NoDev`, the same result `sys_fb_info` uses when no device is registered.

## Security and privacy

Threats that matter here:

- A ring-3 process maps a BAR or a DMA window. Mitigated by `CAP_TYPE_MMIO` and `CAP_TYPE_IRQ`, granted only to the process the kernel spawned for that device. The failure is `Errno.Perm`. The spawn syscall does not grow a flag that selects the mark.
- The driver maps arbitrary physical memory. Mitigated by the probe window list. Kernel half stays `U/S = 0` in this CR3 and is never given `PTE_USER`.
- The driver steers MSI-X at another CPU. Mitigated by not mapping the MSI-X table. The process can write a virtio queue-vector index; it cannot write the APIC ID. Indexes outside the three the kernel published are a device bug in a kernel-spawned binary, not a ring-3 attack. v1 does not add a second check in the device.
- The driver executes `in` / `out` or a privileged MSR. IOPL is 0, there is no IOPB, and MSR access is CPL 0. `#GP` kills the process (vector 13, status 141) and quiesces the device.
- A fault in the driver panics the machine. Mitigated only if every non-zero-CPL test is updated. The asm paths already qualify. The Ritz paths are the ones this design changes. A missed site is the panic.
- DMA stays writable by the device after the process dies. Mitigated by the MSI-X mask, a virtio status readback of 0, and IOTLB invalidation before the pages are freed. Pages whose reset or invalidation does not finish stay on `dma_quarantine` until reboot. The kernel BAR map outlives the Proc.
- The NIC DMA-reads or DMA-writes the framebuffer or another device's buffers. Mitigated by the private domain: those pages are not mapped, and the cutover is refused when the requester cannot be isolated.
- The syscall return builds the iret frame through a user-controlled RSP and faults in CPL 0. Mitigated by building the whole frame on the kernel stack. A non-canonical or kernel-half saved RSP kills the process before `iretq`. SYSRET is not added, so a ring-1 return cannot land in ring 3 by the SYSRET RPL rule.
- A torn `NetInfo` or a frame observed before its bytes. Mitigated by `seq_cst` index and sequence stores, not by TSO.
- Cross-process futex or section wake is specified so a later port does not invent a private wake that fails across processes. Harland does not implement those ports.

The link record contains a MAC. It is not a secret. It is readable by any process that can issue `NetInfo` (224), which is every process, once a snapshot exists. The address record is `NetAddr` (225), the same shape, and it is not a field of `NetInfo`. DMA and MMIO are not readable that way.

## Observability

Existing logs that stay as pass signals: `[virtio-net] MAC`, `[virtio-net] Link status`, `[dhcp] Configured!`, `[net] TX burst: sent=S/300 replies=R`, `[msix] virtio-net: MSI-X on`, `[msix] virtio-net interrupts: N`, `[fault] PID`, `[sched] T ticks, S switches, P preemptions`.

New logs, all on the serial klog: driver pid and CPL at spawn, MSI-X destination APIC ID when it is not the BSP (and the refusal), `NetInfo` published (MAC bytes, not a second stack dump), quiesce on death (pid, vector or exit status). No per-frame log.

Counters: `sched_preemptions` for the preempt test, `msix_vector_count` for the interrupt test, a new park counter incremented in `DrvIrqWait` when `waitq_park` succeeds. The old `virtio_net_rx_halts` counter remains for the in-kernel path until the cutover deletes that path. The boot script switches to the park counter in that PR.

No new metric transport. Harland's observation channel for these tests is the serial line `test_msix_boot.sh` already greps.

## Rollout

There is no feature flag beyond `\harland\net-selftest`. PRs 2 through 6, including the DMA-domain PR, do not change the NIC owner. PR 7 is the cutover and is reverted as a unit if the DHCP or burst assertion fails. Revert restores `virtio_net_init` inside `netdev_init` and the old halt assertion. Partial revert that leaves queues in both places is not a rollback. A boot that cannot translate DMA never enters PR 7's path.

PRs 2–6 are bootable on a machine with no NIC. The ring-1 entry test and the fault test run under the existing boot-test option (`HARLAND_BOOT_FLAG_BOOT_TEST`), the gate `test_tier1_boot.sh` already exercises, and do not require the NIC marker.

`test_harland_syscall_dispatch.py` is updated in the PR that adds each enum variant, not before, so a number is never declared without a handler.

## Tests

TDD order. Each test is named as the file it extends or the boot log it adds. None of them need the full ritz0 matrix or a compiler change.

1. **GDT selectors.** Extend `projects/ritz/ritz0/test_harland_percpu.py` `test_gdt_has_one_tss_descriptor_per_cpu`. Assert `GDT_ENTRIES == GDT_TSS_FIRST + 2 * MAX_CPUS + 2`, `var gdt: [135]GdtEntry`, indexes 133 and 134 use access `0xBA` and `0xB2`, selectors `0x429` and `0x431`, `GDT_TSS_FIRST` still 5, and `tss_selector(0)` is still `0x28`. This test reads source. `gdt.ritz` contains asm and is not host-executed.
2. **Ring-1 enter, syscall, exit.** A boot-test stub mapped as user pages with `sched_prepare_driver`, issues `Getpid` (23) and `Exit` (20), and the serial log shows the pid. `proc_first_entry` and the modified iret tail are the code under test. `jump_to_userspace` is not. The same PR's source test checks that `percpu_area_init` stores `0x1B` / `0x23` and that the SMP phase-1 path still returns through `syscall_entry`. A zero `PC_USER_CS` fails that boot. The iret frame is built on the kernel stack for a CPL-1 return and a CPL-3 return. A non-canonical saved RSP, and a saved RSP in the kernel half, kill the process before `iretq` and do not fault in the return path. A canonical unmapped user stack faults after `iretq` as that process.
3. **Fault kills.** The same stub dereferences address 0. Log contains `[fault] PID` and `killing the process`, status 128+14, and does not contain `KERNEL PANIC`.
4. **Preemption.** The stub spins. A second runnable Proc exists (pid 1). After the run, `sched_preemptions` in the `[sched]` line is greater than 0. `SCHED_HZ` is 100, so a 50 ms spin is five ticks.
5. **Ring 3 MMIO refusal.** A normal ring-3 process calls `DrvMmioMap` and gets -1 (`Errno.Perm`). Host-level dispatch test once the handler is registered: the ABI dict includes 221, and a caller with no `CAP_TYPE_MMIO` returns `Errno.Perm`. The real CR3 map is a boot test.
6. **Driver map.** With a virtio device, the driver reads the status byte from the common-config window and the boot log matches the kernel's last status. With no device, the boot-test double is one write-back page the kernel filled with a known byte and passed through the MMIO syscall's range check via a test-only recorded window under `HARLAND_BOOT_FLAG_BOOT_TEST`. The double is not compiled into the marker path.
7. **`NetInfo` (224).** Before spawn, and while `link_seq` is still 0, `NetInfo` returns `Errno.NoDev` and does not write the user buffer. Publishing the bytes without `NetPublish` leaves the snapshot unpublished. After `NetPublish` of generation 2, the copied MAC equals the device MAC the driver logged, `device_type` is 1, `mtu` is 1500, `configured` is 0. A later link change reaches the snapshot only through another `NetPublish`. The ABI test locks 224 and does not lock 60. Killing the driver invalidates the snapshot and the next call is `Errno.NoDev` again, with no read of the freed page. Numbers 60 and 61 stay absent from the enum.
8. **Cutover, last, and only with an IOMMU.** `tools/test_msix_boot.sh` keeps `[dhcp] Configured!`, `sent=300/300`, replies > 256, MSI-X on, interrupts > 0, and replaces virtio-net `halted > 0` with the park counter > 0. The log must not contain both `[netdev] Registered VirtIO-net` and a ring-1 driver banner. A quiet-link run still ends the DHCP window and still reaches the deferred ping. The burst log is produced with a yield after each group of four. The acceptance check is an IOMMU fault on an IOVA outside the domain. A walk that only shows the framebuffer unmapped is not enough. Without an IOMMU the script keeps today's in-kernel path and the halt assertion.

`test_harland_process_model.py` runs once `Proc` grows, with no new case beyond `proc_free` clearing `driver`. `test_harland_errno.py` is unchanged; no new errno values.

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Iret tail left at `0x1B`/`0x23`, a zero `PC_USER_CS` on the SMP return, or a SYSRET optimization returns RPL 3 | High. The driver would run its ring-1 maps at CPL 3, the SMP phase-1 iret would `#GP` on CS 0, or a later ring-3 syscall would iret to `0x429`. | `PC_USER_CS` / `PC_USER_SS` are qwords at offsets 64 and 72. `percpu_area_init` stores `0x1B` / `0x23`. `sched_use_kstack` writes the incoming Proc's selectors on every switch, including the switch back to ring 3. SYSRET is not added. The enter/exit test runs `Getpid` from the driver frame, and the SMP phase-1 return still completes. |
| One `cs & 3 == 3` site left in place | High. A ring-1 fault panics the kernel, or the driver is never preempted. | The three sites are listed. The asm `testq $3` paths stay as they are. The fault test expects `[fault]` and forbids `KERNEL PANIC`. |
| MMIO mapped `U/S=1` into the kernel PML4 or another process | High | Map only `vmm_pml4_phys` of the driver slot, only below PML4[256], only inside recorded BARs. |
| DMA mapped uncached, or a cacheable map used on a non-coherent device later | Medium for virtio-pci, which is coherent and already uses the write-back physmap. High if a later device assumes UC. | This design states WB on purpose. A non-coherent device is a new mapping flag, not a silent change. |
| Driver death leaves `DRIVER_OK`, frees a page the device can still DMA, or `dma_free_pages` runs after `vmm_free_pml4` | High. The device DMAs into a recycled frame, or the PMM is handed the same page twice. | `driver_quiesce` runs in `sys_exit_impl` after the kernel PML4 switch and before `vmm_free_pml4`: mask MSI-X, virtio status 0 with a 0 readback, IOTLB invalidation, invalidate the link snapshot, wake the frame endpoint. Pages whose readback or invalidation does not finish go to `dma_quarantine` until reboot. `vmm_free_user_pt` frees non-`PTE_DEVICE` leaves once, and only the runs whose reset finished. No `dma_free_pages` of those leaves. Fault, `exit`, and Ctrl-C all enter `sys_exit_impl`. |
| False sharing, or the consumer observing `write_idx` before the bytes | High on a non-TSO port, medium on x86 | Separate lines are necessary but not sufficient. `atomic_store` / `atomic_load` of the index is the rule. Zeus's plain stores are not copied. |
| Syscall number collision with `KERNEL_CONTRACT.md` or the live enum | High if 50–64 or 60/61 are reused | 220–227 are checked against `numbers.ritz` and the ABI dict. 4, 29, 32, 60, and 61 stay free. PR 1 strikes contract numbers 50–64, including `SYS_IRQ_ACK` 64 and `SYS_IRQ_WAIT` 60, so the next reader does not reintroduce them. |
| Self-test goes red at cutover, or `run_init` resets the driver away | High | One PR, no dual owner, halt assertion updated in that PR. `process_create_init` runs once before the window. `run_init` does not call `proc_table_reset` when pid 1 already exists. Revert of that PR restores the in-kernel driver. |
| `sched_start` before the first park preempts the driver mid-init | High. `SCHED_HZ` is 100. Pid 1 is still runnable, so the tick switches back within 10 ms, `NetInfo` is unpublished, and `net_get_mac` zeroes the DHCP MAC. | The first switch is `sched_yield` while `sched_running` is 0. `sched_tick` returns before `proc_pick_next` in that state. Publish and the empty TX drain happen before the first `DrvIrqWait`. `sched_start` runs after that yield returns. |
| `net_stack_init` still requires `dev_count > 0` | High. QEMU has no ENA, so the function returns -1 and the window never starts. | `net_via_ring` is set when the driver has published and `netdev_init` returned 0. `ena_init` success does not set it. The ring is not a `NetDevice`. |
| One-shot watchdog left armed across `lapic_timer_start` | High. `lapic_watchdog_oneshot` stays 1, and `lapic_watchdog_expired` then reads the periodic counter. | Vector 96 does not call `sched_tick`. Pid 1 calls `lapic_watchdog_stop` before `sched_start`. Later parks ride the tick. |
| A frame kick is lost, a full ring drops a frame, or a quiet link stalls the DHCP window | High. The window sleeps with a frame queued, the deferred ping never runs, or the 300-send burst reports fewer than 300 successes. | The consumer parks only under `cli` after a reload of `write_idx`, and `sched_tick` wakes that one endpoint when its deadline passes. A full RX ring leaves the used element in place and the driver keeps draining TX. A full TX ring yields to the driver and returns success only after `read_idx` advances. The burst yields after every group of four, including a group that fits. Death wakes the frame endpoint. |
| ENA and virtio both claim `netdev` | High on a machine that has both, and on any boot that still calls `virtio_net_init` | `netdev_init` drops virtio in the cutover. ENA remains. The ring is not registered as a `NetDevice`. |
| The NIC's requester can DMA the framebuffer or kernel RAM | High. A CPU allowlist does not constrain the device. | No queue-address page is mapped, and bus mastering for the driver stays off, until a private translated domain holds only the granted queue and packet pages. A requester that cannot be named refuses the cutover. The acceptance walk shows the framebuffer and a kernel page absent from the domain. |
| `irq_route_dest` moves the MSI-X off the BSP and `waitq_wake_irq` ignores it | Medium | Refuse to start the driver unless the routed destination is the BSP. The BSP is the only CPU that runs Procs. |
| `test_harland_percpu.py` equality on `GDT_ENTRIES` | Low, caught at CI | Updated in the GDT PR, not discovered later. |
| `mmap` or `munmap` reaches PML4[251]–[253], including a range that starts below the window | High if it happens. `sys_munmap_impl` today frees any mapped phys in that span. | Both `sys_mmap_impl` and `sys_munmap_impl` reject any overlap of `[DRV_RING_BASE, USER_STACK_BASE)`. A partial `DrvMmioMap` or `DrvDmaAlloc` rolls its own pages back. |

## Key decisions

1. **CPL 1 with selectors `0x429` and `0x431` appended at GDT indexes 133 and 134.** CPU 0's TSS stays `0x28`. `GDT_ENTRIES` is 135. Ring 3 was the alternative and loses because the iret RPL, the architecture doc, and a future `rsp1` call gate are the point of the ring. Page rights do not distinguish the two. Capabilities authorize the process. They do not choose its CPL.
2. **Return stays `iretq`, and the whole iret frame is built on the kernel stack.** `iretq` loads the saved user RSP. A non-canonical or kernel-half saved RSP kills the process before `iretq`. An unmapped canonical stack faults after `iretq`, as that process. The same tail returns to CPL 3 and CPL 1. Per-process CS/SS are qwords at per-CPU offsets 64 and 72. The area is 128 bytes, indexed by `shlq $7`. `percpu_area_init` stores `0x1B` / `0x23` so the SMP phase-1 iret, which never calls `sched_use_kstack`, still returns to ring 3. `sched_use_kstack` writes the incoming Proc's selectors on every switch. Offset 56 is not reused: `pushq` of a GS slot is 8 bytes, and the iret tail has no scratch. SYSRET cannot represent CPL 1 on Intel, and the GDT is not ordered for SYSRET even for ring 3.
3. **`rsp1` stays 0.** Kernel entry uses `rsp0` or an IST. The ring-1 stack is the user stack in the iret frame.
4. **Non-zero CPL is a process** in `exception_handler`, `sched_tick`, and `tty_console_irq`. The asm stubs already use that predicate.
5. **IOPL 0, no IOPB, modern MMIO virtio only.** Legacy port I/O is not given a proxy.
6. **Device authority is a capability, not a `Proc` bit and not a hardcoded path.** `DrvIrqWait` and `DrvDmaAlloc` and `DrvRingKick` check `CAP_TYPE_IRQ`. `DrvMmioMap` checks `CAP_TYPE_MMIO` and maps from the kernel's window record. The frame rings, the app exchange, and the address page are `CAP_TYPE_SHM`, mapped by `ShmMap` (227) and revoked by `CapRevoke`. Spawn is the kernel exercising that path. `Proc` stores return CS/SS. The handler's CS is `0x08`, so it cannot authorize by CPL. Refusal is `Errno.Perm`.
7. **`DrvIrqWait` = 220 reuses `BLOCK_IRQ` and arms the LAPIC watchdog around `waitq_park`.** The bound is `VIRTIO_NET_RX_WAIT_TICKS` (`0x00020000`), one round. After `sched_start` the arm rides the periodic tick and `sched_tick` wakes `BLOCK_IRQ` when it expires. The first park is before that tick. Vector 96 does not enter `sched_tick`, so pid 1 calls `lapic_watchdog_stop` before `lapic_timer_start`. The kernel keeps the IDT and the EOI. User-mode IRQ delivery is rejected.
8. **`DrvMmioMap` = 221, `DrvDmaAlloc` = 222, `DrvRingKick` = 223, `NetInfo` = 224, `NetAddr` = 225, `NetPublish` = 226, `ShmMap` = 227.** `net_ping` is not numbered. Contract numbers 50–64 are not reused. 4, 29, 32, 60, and 61 stay free for their Linux meanings.
9. **MMIO grants are complete pages of a recorded window, uncached, in that CR3 only.** `DrvMmioMap` takes a capability whose object is that window. A page that also holds the MSI-X table or the PBA is refused. DMA pages are zeroed before they are reachable, and `DrvDmaAlloc` returns the IOVA. The shared ring is write-back, matching the physmap virtio already uses, and it is not in the device's DMA domain. The bytes at `0x0300` are advisory.
10. **Two SPSC rings, depth 256, 2048-byte frames, `sizeof` for every slot, indexes on separate cache lines, a `u32` wake, `seq_cst` index stores.** The region is `0x103000` bytes, with both controls and `NetInfo` on page 0. The consumer derives `arena_off` from the slot. A bad length or a mismatched offset is skipped. An occupancy above 256 kills the device owner. A full ring stalls that direction and keeps draining the other. The driver's full-RX wait calls `Yield` (24). The kernel seat yields when TX is full. The consumer parks under `cli` with a recheck and a deadline, and returns `RxWait`. The wake names the frame endpoint, not every waiter of a shared reason. Linux waits on the `u32` with `FUTEX_WAIT` / `FUTEX_WAKE`. Win64 uses a shared event and rechecks the index. The frame ring needs no extra `fence()`. The link seqlock does. Zeus HTTP slots and Zeus plain stores are not the protocol. `channel.ritz` is not the dataplane.
11. **The driver is the only writer of shared `NetInfo`, and the kernel snapshot is what `NetInfo` returns.** `link_seq` 0 is unpublished. The first stable generation is 2. The writer fences after the odd store. The sampler fences before the second load. `NetPublish` is the only refresh, and it wakes the frame endpoint. MAC, link, MTU, device type. Address fields stay zero. The lease stays with the stack and moves to ring 2 with it. Readers use `NetAddr`. No snapshot, or a snapshot `driver_quiesce` has invalidated, is `Errno.NoDev`. The kernel does not write the shared record. Quarantined DMA pages get `PTE_DEVICE` before `vmm_free_pml4`. Virtio reset waits on `VIRTIO_RESET_TIMEOUT_US`.
12. **ENA stays in-kernel. virtio leaves `netdev_init` only on a boot with a translated DMA domain.** The first switch is `sched_yield` while `sched_running` is 0, after `proc_start` and before `sched_start`. The driver publishes generation 2 and drains TX before that first `DrvIrqWait`. `sched_start` runs once after the yield returns and after `lapic_watchdog_stop`, still before any send. `net_stack_init` returns 0 when the snapshot is published and `netdev_init` returns 0, and does not register a `NetDevice`. `net_get_mac`, `net_send`, `net_poll`, and `net_wait_rx` are the ring endpoints only while `net_via_ring` is set. `net_wait_rx` returns at its deadline on a quiet link. The 300-send burst yields to the driver after every group. An `ena_init` success keeps the `NetDevice` path and does not set that flag. A boot with no IOMMU keeps `virtio_net_init`. `run_init` does not reset the table. `MAX_PROCS`, `FS_MAX_PROCS`, and `KSTACK_SLOTS` stay 8. The halt assertion moves to a park counter on the translating boot. Death is `driver_quiesce` before `vmm_free_pml4`, with status readback, IOTLB invalidation, and `dma_quarantine` for pages that cannot be proven idle.

## Open questions

None. The trade-offs above are decided. A weaker-than-`seq_cst` order is a later measurement, not a blocker: the language has one order, and it is correct for the ports.

## PR plan

### PR 1. Docs only

**Title:** harland: Correct the stale driver-ABI numbers and the phase list

**Files:** `projects/harland/docs/RING1_DRIVER.md` (this document), `ARCHITECTURE.md`, `NETWORK_DESIGN.md`, `KERNEL_CONTRACT.md`.

**Depends on:** nothing.

**Description:** Land the design. Do not change `ARCHITECTURE.md`'s ring-1 driver assignment or its ring-2 stack assignment. Mark phases 1–4 historical where that work already exists in ring 0, and mark the ring-1 row's "port I/O" phrase as not granted by this substrate. Record the IPC departure: `ARCHITECTURE.md` describes a per-call page-table flip with no data copy, and these drafts use persistent SPSC rings instead, so a message does not edit page tables or shoot down the TLB. In `NETWORK_DESIGN.md`, replace `SYS_NET_INFO = 40` / `SYS_NET_PING = 41` with `NetInfo` 224 and `NetAddr` 225, and say 60 and 61 stay free. Leave that doc's ring-1 driver / ring-2 netd diagram alone. In `KERNEL_CONTRACT.md`, replace the ring-2 driver wording ("Goliath runs as a Ring 2 service", "Block drivers (Ring 2)", "Device Syscalls (Ring 2 Drivers Only)") with ring 1 for drivers, and strike `SYS_SHM_CREATE` 50, `SYS_SHM_MAP` 51, `SYS_SHM_UNMAP` 52, `SYS_IRQ_WAIT` 60, `SYS_DMA_ALLOC` 61, `SYS_DMA_FREE` 62, `SYS_MMIO_MAP` 63, and `SYS_IRQ_ACK` 64. Point shared memory at `CAP_TYPE_SHM` and `ShmMap` 227, MMIO at 221, DMA at 222, and IRQ wait at 220. IRQ acknowledgement stays a kernel EOI, not a syscall. No code, no behavior.

### PR 2. GDT DPL-1 descriptors

**Title:** harland: Add unused DPL-1 code and data descriptors

**Files:** `kernel/src/arch/x86_64/gdt.ritz`, `projects/ritz/ritz0/test_harland_percpu.py`.

**Depends on:** PR 1 for the numbers in comments only. The code does not depend on the doc landing first, but the selector values should match it.

**Description:** Append indexes 133 and 134. Tests for the selectors, access bytes, and the unchanged TSS formula. No process loads the selectors.

### PR 3. Ring-1 entry, preempt, fault

**Title:** harland: Enter a driver-class process at CPL 1

**Files:** `gdt.ritz` (selectors already present), `proc/table.ritz`, `proc/sched.ritz`, `syscall_entry.s`, `exceptions.ritz`, `proc_switch.s` comments if they still say the frame is ring 3 only, a boot-test stub, `projects/ritz/ritz0/test_harland_percpu.py`, `projects/ritz/ritz0/tests/test_harland_syscall_stack.py`, `test_harland_process_model.py` if a field initializer needs a touch.

**Depends on:** PR 2.

**Description:** `PERCPU_SIZE` 128, `shlq $7` in `percpu_area_for` and `percpu_area_init`, `PC_USER_CS` at 64, `PC_USER_SS` at 72. `percpu_area_init` stores `0x1B` / `0x23`. `sched_use_kstack` writes the incoming Proc's selectors. The `syscall_entry` iret tail builds SS, the saved user RSP, RFLAGS, CS, and RIP on the kernel stack, then `iretq` loads the user RSP. It does not `popq %rsp` and push through that pointer. A non-canonical or kernel-half saved RSP kills the process before `iretq`. `jump_to_userspace` keeps its immediates. `sched_prepare_driver`. `cs & 3 != 0` at the three Ritz sites. Tests: the percpu source test stops requiring `pushq $0x1B` inside `syscall_entry` and requires `pushq %gs:PC_USER_CS` (the syscall-stack test has the same assertion and changes with it); enter and `Getpid` from CPL 1 and from CPL 3; the invalid-RSP cases; the SMP phase-1 return still irets; fault does not panic; spin is preempted. No MMIO and no NIC.

### PR 3b. Capabilities for device authority

**Title:** harland: Authorize a device process with capabilities

**Files:** `kernel/src/cap/types.ritz` only if a right bit is missing, `cap/table.ritz`, `cap/syscall.ritz`, `syscall/numbers.ritz` (`ShmMap` = 227), `syscall/runtime/entry.ritz`, `ritzlib/sys.ritz`, `test_harland_syscall_dispatch.py`.

**Depends on:** PR 3. PR 4 does not add a handler until this lands, so the numbers are not frozen against a driver bit.

**Description:** Grant `CAP_TYPE_IRQ`, `CAP_TYPE_MMIO`, and `CAP_TYPE_SHM` through the existing cap table. `CapGrant` (40) and `CapRevoke` (41) are the grant and revoke. `ShmMap` (227) maps a shm capability into the caller. No `Proc.driver`. No hardcoded `/bin/virtio-net` check. A caller without the handle gets `Errno.Perm`. This PR does not move the NIC. It is the path PR 6 and the ring-2 attach both call.

### PR 4. IRQ wait

**Title:** harland: Park a driver process on BLOCK_IRQ

**Files:** `syscall/numbers.ritz`, `syscall/runtime/entry.ritz`, a new handler module under `syscall/runtime/`, `ritzlib/sys.ritz`, `test_harland_syscall_dispatch.py`, the boot-test stub.

**Depends on:** PR 3b.

**Description:** `DrvIrqWait` = 220 checks the caller's `CAP_TYPE_IRQ` handle. A caller without that handle, including every ring-3 process, gets `Errno.Perm`. The handler arms `lapic_watchdog_arm(VIRTIO_NET_RX_WAIT_TICKS)` before `waitq_park` and calls `lapic_watchdog_stop` after it. The driver stub waits, a kernel MSI-X or the tick-riding watchdog wakes it, the stub exits. The vector is not injected. Virtio is still in the kernel, so this test uses the watchdog wake or a test IPI, not the NIC. The test that runs before `sched_start` checks that pid 1's `lapic_watchdog_stop` clears `lapic_watchdog_oneshot` and that `lapic_timer_start` still installs vector 32.

### PR 5. MMIO map and DMA alloc

**Title:** harland: Map MMIO and DMA into a driver process

**Files:** the handler module, `mm/vmm.ritz` only if a small "map into this range" helper is required, `syscall/runtime/memory.ritz` for the mmap exclusion, `numbers.ritz`, `ritzlib/sys.ritz`, the ABI test, the boot-test stub.

**Depends on:** PR 3b. PR 4 is not a functional dependency. Sequence it after PR 4 so the syscall numbers land in order.

**Description:** `DrvMmioMap` = 221 takes a `CAP_TYPE_MMIO` handle and maps every page of the window that handle names in kernel memory. It does not take a window index and it does not read `0x0300`. A caller without the handle gets `Errno.Perm`. A page that also contains the MSI-X table or the PBA returns `Errno.Inval` and maps nothing. The kernel keeps the window's byte offset, length, and notify multiplier in kernel memory. The shared-page copy is advisory. A partial map unmaps the pages that call installed. `DrvDmaAlloc` = 222 checks the `CAP_TYPE_IRQ` handle, zeroes pages before they are reachable, and rolls a partial failure back. The copied-out address is an IOVA only once PR 5b's domain exists; until then the syscall allocates and maps for the CPU and does not publish an address the device can use. A caller without the matching capability is refused. UC MMIO and WB DMA PTEs as specified. Boot-test double when no BAR exists. `sys_mmap_impl` and `sys_munmap_impl` both reject any overlap of `[DRV_RING_BASE, USER_STACK_BASE)`, including a request that starts below the window. Queue-address pages stay unmapped in this PR. Bus mastering for the driver stays off.

### PR 5b. Per-device DMA domain

**Title:** harland: Give the NIC a private translated DMA domain

**Files:** `kernel/src/drivers/iommu/vtd.ritz`, `kernel/src/drivers/iommu/amdvi.ritz`, `drivers/virtio/net.ritz` (feature bit 33 on this boot only), the driver-syscall module that publishes IOVAs, `tools/test_msix_boot.sh`, a boot test that faults an IOVA outside the domain.

**Depends on:** PR 5. PR 6 can proceed on CPU mappings without this. PR 7 cannot.

**Description:** Before any page that contains a queue-address register is mapped into the driver, and before bus mastering is enabled for it, install one translated domain for this requester. The requester is PCI segment and device identity plus the DMA aliases the firmware table names. A unit that cannot translate, or a requester that cannot be named, refuses the later cutover. The domain maps only granted queue pages and `DrvDmaAlloc` packet pages, read-write for the device. `DrvDmaAlloc`'s copied-out address is the IOVA. Frame rings, the framebuffer, and other RAM are absent. Teardown invalidates every IOVA and waits for the IOTLB before those pages return to the PMM. The second `test_msix_boot.sh` run uses q35, `kernel-irqchip=split`, `intel-iommu,intremap=on`, and `virtio-net-pci` with `disable-legacy=on,iommu_platform=on`. The in-kernel virtio path on that run negotiates feature bit 33, so the device uses the domain. The acceptance check is an IOMMU fault when the device is given an IOVA outside the domain, and a NIC write into an allocated buffer. A domain walk that only shows the framebuffer unmapped is not enough. `vtd.ritz` gains a path that sets translation. `amdvi.ritz` stops using DMA pass-through for this requester. This PR does not move virtio out of the kernel. PR 7 runs the same boot again with the ring-1 driver negotiating bit 33.

### PR 6. SPSC frame ring

**Title:** harland: Add the portable SPSC frame ring and its Harland mapping

**Files:** `projects/harland/driver_abi/` (new), kernel mapping and `DrvRingKick` = 223, `proc/table.ritz` (one frame-endpoint waiter), `numbers.ritz`, `ritzlib/sys.ritz`, the ABI test, a host test of the abi package that publishes and consumes one frame with `atomic_store` / `atomic_load`.

**Depends on:** PR 5 for the user mapping helper. The abi package itself has no kernel dependency and can be reviewed first.

**Description:** Layout at the offsets in section 6, region size `0x103000`, `sizeof`, separate index lines, `wake` as `u32`, seq_cst publication. `[[align(64)]]` is added in ritz in this PR if it is not already in, and `SpscCtrl` uses it. A host test asserts `sizeof` and every field offset against the table. The grant is `CAP_TYPE_SHM` plus `ShmMap`, including when the kernel does it at spawn. The consumer parks with interrupts off, a reload of `@ctrl.write_idx`, and a deadline, and returns `RxWait`. A rejected slot continues the wait. An occupancy above 256 kills the producer instead of wedging the ring. A full ring does not drop: the stand-in producer waits until `read_idx` advances, and a full RX side keeps draining TX and calls `Yield`. Kick wakes the one frame-endpoint waiter. The bytes at `0x0300` are not an authority. No virtio yet. No new memory-order intrinsic. A host test fails if the consumer reads the slot before the index store by single-stepping the two operations in order; it does not claim to be a non-TSO litmus test. A second host test fills 256 slots and checks that publish does not advance `write_idx` until the consumer stores `read_idx`. A third rejects the bad length and the mismatched offset, and kills the producer on occupancy above 256. A fourth returns `Timeout` at the deadline with the ring still empty.

### PR 7. virtio-net cutover

**Title:** harland: Move virtio-net queues into the ring-1 driver

**Files:** `projects/indium/user/virtio_net.ritz`, `projects/harland/virtio_abi/` (new leaf: virtqueue and feature negotiation, no kernel imports), `drivers/virtio/common.ritz` and `drivers/virtio/net.ritz` (call the leaf; `net.ritz` stays whole for untranslated boots), `drivers/virtio/blk.ritz` and `drivers/virtio/input.ritz` only where they share the leaf, `drivers/netdev.ritz`, `net/stack.ritz`, `postinit.ritz`, `main.ritz` (`run_init`), `syscall/runtime/process.ritz` (`process_create_init`, `driver_quiesce` inside `sys_exit_impl`), `NetInfo` / `NetPublish` handlers, `numbers.ritz`, `ritzlib/sys.ritz`, `test_harland_syscall_dispatch.py`, `tools/test_msix_boot.sh`.

**Depends on:** PRs 3b, 4, 5, 5b, and 6. Queue-address pages are not granted before PR 5b.

**Description:** One owner per boot. A translating boot spawns the indium driver and does not call `virtio_net_init`. Every other boot keeps `virtio_net_init`, and `net.ritz` is not deleted. Both stay for as long as untranslated boots are supported. The second `test_msix_boot.sh` run uses q35, `kernel-irqchip=split`, `intel-iommu,intremap=on`, and `iommu_platform=on`, and the driver negotiates feature bit 33. An IOMMU fault on an unmapped IOVA is an acceptance check. ENA stays. `process_create_init`, then `sched_yield` while `sched_running` is 0, then `lapic_watchdog_stop` and one `sched_start`, all before `net_stack_init`. The driver publishes generation 2, calls `NetPublish`, and drains TX before its first park. `net_stack_init` returns 0 when the snapshot holds that generation even though `netdev_init` returned 0, and does not register a `NetDevice`. `net_get_mac` copies the snapshot. `net_send`, `net_poll`, and `net_wait_rx` are the SPSC endpoints. `net_wait_rx` returns `RxWait` and takes the DHCP deadline. `network_tx_burst` yields to the driver after every group of four and keeps `sent=300/300` and replies > 256. `ena_init` success leaves `net_via_ring` false. `run_init` does not reset the table. The driver is one of `MAX_PROCS` (8). `NetInfo` (224) reads the snapshot and returns `Errno.NoDev` while the generation is 0 and after the snapshot is invalidated. Death masks MSI-X, writes virtio status 0, and waits `VIRTIO_RESET_TIMEOUT_US` for a 0 readback, then invalidates the DMA domain and the snapshot, before `vmm_free_pml4`. Pages that fail that confirmation are marked `PTE_DEVICE` and recorded on `dma_quarantine`. The wake names the frame endpoint. Death does not `dma_free_pages` the user-mapped frames and does not write shared `NetInfo`. The translating boot requires the park counter instead of virtio-net `halted > 0`. Address fields in the record stay zero. The ring-2 service publishes them later, and apps read them with `NetAddr`. 60 and 61 stay free.

## References

- `projects/harland/kernel/src/arch/x86_64/gdt.ritz`, `idt.ritz`, `exceptions.ritz`
- `projects/harland/kernel/syscall_entry.s`, `isr_stubs.s` (`SWAPGS_IF_USER`, `irq_stub_timer`), `proc_switch.s` (`proc_first_entry`)
- `projects/harland/kernel/src/proc/sched.ritz`, `proc/table.ritz`, `proc/waitq.ritz`
- `projects/harland/kernel/src/syscall/numbers.ritz`, `syscall/errno.ritz`, `syscall/runtime/entry.ritz`, `syscall/runtime/framebuffer.ritz`, `syscall/runtime/process.ritz`
- `projects/harland/kernel/src/mm/vmm.ritz` (`PTE_*`, `vmm_map_mmio`, `vmm_create_user_pml4`, physmap), `mm/dma.ritz`, `mm/pmm.ritz`
- `projects/harland/kernel/src/drivers/virtio/common.ritz`, `drivers/virtio/net.ritz`, `drivers/netdev.ritz`, `drivers/msix.ritz`, `drivers/irq_wait.ritz`
- `projects/harland/kernel/src/net/stack.ritz`, `net/ip.ritz`, `net/icmp.ritz`, `net/dhcp.ritz`
- `projects/harland/kernel/src/postinit.ritz`, `projects/harland/tools/test_msix_boot.sh`
- `projects/harland/docs/ARCHITECTURE.md`, `NETWORK_DESIGN.md`, `KERNEL_CONTRACT.md`, `SYSCALL_ABSTRACTION.md`
- `projects/ritz/docs/LANGUAGE_SPEC.md` §18.4 and §18.5
- `projects/ritz/ritz0/tests/test_harland_syscall_dispatch.py`, `test_harland_percpu.py`
- `projects/zeus/lib/control.ritz`, `ring.ritz`, `shm.ritz`, `zeus_client.ritz` (`zeus_client_peek_response_slot`)
- `projects/harland/kernel/src/ipc/channel.ritz`
- `projects/harland/docs/RING1_DRIVER_FEEDBACK.md` — the review this text absorbs. The feedback file stays the review record.
- `projects/harland/docs/RING1_RING2_REVIEW.md` — the review of both drafts against the tree. The feedback file stays the review record.
- `projects/harland/kernel/src/cap/types.ritz` — `CAP_TYPE_MMIO`, `CAP_TYPE_IRQ`, `CAP_TYPE_SHM`
- `projects/indium/` — userspace programs, including the virtio-net driver
- `projects/harland/kernel/src/drivers/iommu/vtd.ritz`, `drivers/iommu/amdvi.ritz` — translation is off, and AMD-Vi is pass-through, until PR 5b
- Intel 64 and IA-32 Architectures SDM, Volume 3, §6.14.5: on an interrupt that changes privilege in IA-32e mode, IST non-zero selects `TSS.IST`, otherwise the new RSP is `TSS.RSP` indexed by the new CPL. Volume 2, SYSCALL and SYSRET: SYSCALL does not read the TSS; Intel SYSRET forces the destination RPL to 3.
- Virtio 1.2 device reset: a status write of 0 starts the reset; a status read of 0 is the completion
- Linux futex: classic `FUTEX_WAIT` / `FUTEX_WAKE` operate on a 32-bit word
- Win32 `WakeByAddressSingle`: process-local. The cross-process wake is a shared event plus a recheck
