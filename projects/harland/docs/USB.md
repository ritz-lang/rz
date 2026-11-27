# Harland USB: xHCI and a HID Keyboard

| | |
|---|---|
| Status | Decided (AGAST #4860, break-down). Built by the child tickets of #4860 |
| Date | 2026-11-27 |
| Audience | Harland kernel |
| Drives | M2.4 #4870: chungus (Acer A315-24PT) boots from a USB stick to rzsh, typed on a USB keyboard |

## Goal

Harland drives USB on real x86_64 UEFI machines. The first bar is a USB
keyboard that types into rzsh on the framebuffer console. Nothing else is
needed for that bar. QEMU CI (`qemu-xhci` + `usb-kbd`) proves it first, then
Aaron boots chungus (#4870).

Out of scope: mass storage, audio, video, Thunderbolt, USB4, isochronous
transfers, and EHCI (no target machine has a keyboard port that is
EHCI-only).

## Target controllers

| Machine | Controller | Interrupts | IOMMU | Notes |
|---|---|---|---|---|
| QEMU (CI) | `qemu-xhci` [1b36:000d] | MSI-X | none in CI | the first target |
| chungus (Acer A315-24PT) | AMD [1022:1503] 03:00.3, [1022:1504] 03:00.4, [1022:1505] 04:00.0 | MSI-X, 8 vectors each; 64-bit BAR | AMD-Vi: interrupt remapping, DMA **passed through untranslated** (`amdvi.ritz`) | three functions, and a keyboard can be on any of them |
| ASRock X99 | Intel [8086:8d31] 00:14.0 | **MSI only** (no MSI-X capability in `hwinv`) | VT-d: identity domain for kernel DMA | has BIOS legacy-USB SMIs to hand off |
| ThinkPad P16 (never test-boot) | Intel [8086:7a60] 00:14.0 | MSI-X | VT-d | its keyboard is i8042 (#4869), not USB |

Hubs: nothing in the hardware dumps shows whether chungus's external ports
are root-hub ports or sit behind an on-board hub, and a keyboard plugged into
an external hub needs the hub driver anyway. The hub ticket is part of the
path to #4870 for that reason.

## Decision: where the driver runs

**Decision: a kernel driver, now.** The xHCI host controller driver, USB
enumeration and the HID boot keyboard run in ring 0 and feed the console's
line discipline directly. They are written as a leaf package and a thin
kernel shell, so moving them into a CPL-3 process later moves code and does
not rewrite it.

### Why not a CPL-3 driver (D8)

D8 (`RING1_DRIVER.md`) says a ring-1-tier driver is a CPL-3 process whose
authority is its capabilities and whose DMA is fenced by a **translated** DMA
domain. The IOMMU rule has no exception: "a boot with no translated DMA
domain spawns no netd, and the kernel keeps the NIC". Apply it to USB:

- **chungus has no translated domain.** `amdvi.ritz` turns on interrupt
  remapping and passes DMA through untranslated. Under the rule, a CPL-3 USB
  driver is never spawned on the first target, so the kernel needs the driver
  anyway. Writing the CPL-3 version first would buy a second copy that the
  #4870 boot never runs.
- **The keyboard is the console.** If the driver process dies, nothing can be
  typed to restart anything. netd's restart budget makes sense for a NIC. For
  the only input device on the machine it does not.

### Why not a driver inside a service (D9)

D9 puts a driver in the process that consumes its data, because every hop
between processes costs switches (#4768's gate). The keyboard's consumer is
the kernel: `tty/ldisc.ritz` (canonical mode, echo, Ctrl-C) and
`tty/console.ritz` (the foreground kill and the BLOCK_TTY wake). By D9's own
reasoning the keyboard driver belongs where the line discipline is, in the
kernel. A CPL-3 driver would need a new syscall to push bytes into the ldisc
and would add a switch to every keystroke, for no isolation gain on chungus.

### When it moves

The xHCI driver moves to a CPL-3 process (`/bin/usbd`, or into a ring-2 input
service) when both are true:

1. AMD-Vi has translated DMA domains (as VT-d does today), so the IOMMU rule
   lets a CPL-3 driver DMA on the AMD machines; and
2. something in user space consumes USB data that is not the console (a
   desktop input service, mass storage, or a second class of device).

Until then the kernel driver is the only one. The keyboard path stays in the
kernel even after a move, as a small "console keyboard" fallback, in the way
the kernel keeps `virtio_net_init` for boots without an IOMMU.

### Code layout

| Path | Contents |
|---|---|
| `projects/harland/usb_abi/` | New leaf package on the `virtio_abi` pattern, with no kernel imports and its own host unit tests. It holds the xHCI register and TRB layouts, the TRB ring (enqueue, cycle bit, link TRB, event dequeue), the context layouts (32- and 64-byte, `HCCPARAMS1.CSZ`), the USB descriptor parser, the endpoint-interval conversion, and the HID boot report decoder (report diff, US keymap, modifiers, escape sequences). |
| `kernel/src/drivers/usb/xhci.ritz` | The controller: PCI probe, BIOS handoff, reset, DCBAA, scratchpad, command and event rings, interrupter 0, port handling. |
| `kernel/src/drivers/usb/usb.ritz` | Device enumeration: slots, Address Device, control transfers, descriptors, Set Configuration, endpoint configuration. |
| `kernel/src/drivers/usb/hid_kbd.ritz` | The HID boot keyboard: Set Protocol (boot), Set Idle, the interrupt-IN transfer, report to bytes into the console, typematic repeat. |
| `kernel/src/drivers/usb/hub.ritz` | The hub class driver (USB 2.0 hubs, and USB 3 hubs on their SuperSpeed side). |

## Concurrency under SMP_USER.md

`SMP_USER.md` §2 (#4874, #4879) is the ownership model this driver follows:
every piece of kernel state has one owner CPU, and only its owner writes it.
The driver adds no lock, no message kind and no CPU of its own.

- **All xHCI state is BSP-owned.** The controller, slot, ring and HID state
  joins the "In-kernel drivers" row of SMP_USER's inventory, next to
  `drivers/nvme`, `virtio/blk`, `virtio/net` and `ena`. It needs no lock
  because only the BSP ever touches it: its three entry points all run there.
  These are the MSI-X vector, the polled-fallback tick and the console's
  readers, each covered below. Unlike the other rows it is never lent to an
  AP, because no AP call reaches it.
- **Interrupts go to the BSP.** Each controller's interrupter 0 gets one
  MSI-X vector from `msix_vector_alloc` with the BSP as its destination
  (`irq_route_dest`, and an IRTE when remapping is on). The console's wait
  set and the `tty/ldisc.ritz` state it feeds are BSP-owned rows too, so the
  whole keystroke path stays on one CPU and needs no kick.
- **`irq_handler` calls the driver.** The MSI-X branch counts the vector as
  today (`msix_dispatch`). When the vector belongs to an xHCI controller it
  also calls `xhci_irq`, which drains the event ring, advances the per-device
  state machines and pushes keyboard bytes into the line discipline, then
  does the console's wake (`proc_wake(BLOCK_TTY)`, `waitset_console_ready`)
  and the Ctrl-C kill check that `tty_console_irq` does for COM1. It is the
  same single-CPU reasoning `tty_console_irq` relies on today.
- **A console reader homed on an AP runs no USB code there.** The tty
  syscalls are not `SYS_LOCAL`, so an AP-homed process's `read(0)` is
  forwarded (§2): the process moves to the BSP, blocks there on the console,
  and the BSP's wake makes it runnable on the BSP. The forwarded call then
  returns it to its home. The wake is a CAS on its state word (§4) on the CPU
  it is on, so it needs no kick, and the AP never touches the line discipline
  or the driver. The default under pinning is the BSP anyway, so rzsh and the
  foreground job do not pay the forward's round trip.
- **No long busy-wait after boot.** Everything the BSP owns waits behind the
  driver while it spins. That is fs syscalls, every forwarded syscall from the
  APs, the other in-kernel drivers, and the keystrokes themselves. So the
  controller reset (`CNR`, `HCHalted`, up to tens of milliseconds) and the
  BIOS handoff (up to one second of firmware SMI) run once, in `kernel_main`,
  before any AP runs a process, with TSC deadlines. Everything at run time is
  event-driven: port reset, Enable Slot, Address Device and every control
  transfer are commands or transfers whose completion arrives as an event, and
  each device is a state machine that the event moves forward. Hot-plug
  therefore never stalls the BSP's other work or keystroke latency, and never
  delays the forwarded calls of netd's core.
- **Polling fallback.** A controller with no usable vector (MSI-only before
  MSI support lands, or a vector that never fires) is polled from the BSP's
  100 Hz tick (`sched_tick`), which calls the same `xhci_irq` body. Ten
  milliseconds is well inside what typing needs. Only the BSP's tick polls, so
  the poll stays on the owner. The APs' ticks never call it.

## Data path

```
key press -> device -> interrupt-IN transfer event (event ring, MSI-X to BSP)
  -> xhci_irq -> hid_kbd: 8-byte boot report, diff against the last one
  -> usb_abi keymap: usage -> bytes (ASCII, control bytes, ESC [ A for arrows)
  -> tty console input: ldisc_input per byte, echo to COM1 and fbcon
  -> proc_wake(BLOCK_TTY) + waitset_console_ready -> rzsh's read(0) returns
```

- **One console input entry.** `tty/console.ritz` gets
  `tty_console_input(bytes: StrView, from_user: bool) -> bool`, the shared
  body of COM1's receive half. `tty_console_pull` (COM1) and `hid_kbd` both
  call it. Echo, wake and Ctrl-C semantics are unchanged and do not depend on
  where the byte came from.
- **Keymap.** US layout. Shift and Caps Lock (with the LED set by Set Report),
  Ctrl+letter gives the control byte, so Ctrl-C reaches the ldisc as 3, Ctrl-D
  as 4. Backspace sends 127, as a terminal does (`CH_DEL`). Enter sends `\r`,
  which the ldisc treats as COM1 does. Arrows, Home, End and Delete send their
  ANSI escape sequences.
- **Repeat.** A boot keyboard does not repeat in hardware (Set Idle 0). The
  BSP tick repeats the last held key: 500 ms delay, then every 3 ticks (about
  33 per second).

## xHCI bring-up, in order

1. **Find.** Every PCI function with class 0C, subclass 03, prog-if 30 (all
   three on chungus). Map BAR0 (64-bit), enable memory and bus master.
2. **BIOS handoff.** The USB Legacy Support extended capability (ID 1): set
   OS Owned, wait for BIOS Owned to clear (one-second deadline, then take it
   anyway and log it), and clear the SMI enables in USBLEGCTLSTS.
3. **Reset.** Clear Run/Stop, wait for HCHalted, set HCRST, wait for HCRST and
   CNR to clear.
4. **Memory.** DCBAA, scratchpad buffer array and pages
   (`HCSPARAMS2`), the command ring, and event ring segment 0 with its ERST.
   One zeroed page each, from `dma_alloc_zeroed`. Kernel DMA uses physical
   addresses: AMD-Vi passes it through and VT-d's identity domain maps RAM.
   `HCCPARAMS1.AC64` must be set, or every allocation must sit below 4 GiB.
5. **Interrupter 0.** IMAN.IE, IMOD (moderation off at first), the vector,
   then Run/Stop and USBCMD.INTE.
6. **Ports.** The Supported Protocol capabilities (ID 2) say which ports are
   USB 2 and which USB 3. Power the ports. A USB 3 port links up by itself. A
   USB 2 port with CCS set gets PORTSC.PR, and its Port Status Change event
   says the reset is done.
7. **Device.** Enable Slot, then Address Device with EP0's max packet size
   from the port speed (8 for low and full speed, corrected from the device
   descriptor; 64 for high speed; 512 for SuperSpeed), then GET_DESCRIPTOR
   (device, configuration), SET_CONFIGURATION, Configure Endpoint.

## Hot-plug

Port Status Change events drive attach and detach for every port, root or
hub. On detach the driver stops the device's endpoints, disables its slot and
frees its rings. If the device was the keyboard, held keys are released so a
repeat cannot outlive the device. On attach it starts at step 7. A Host System
Error or a dead controller (`USBSTS.HSE`, or registers reading all-ones)
resets that controller alone and re-enumerates its ports. The other
controllers keep running.

## Tests

| Test | Where | Checks |
|---|---|---|
| `usb_abi` unit tests | host, `usb_abi/test` | TRB encode, ring wrap and cycle toggle, event dequeue, context sizing (CSZ), descriptor parsing (good and truncated), interval conversion per speed, report diff (press, release, rollover error `0x01` ignored), keymap with modifiers |
| xHCI bring-up boot | `tools/test_usb_boot.sh` (`make test-usb`), QEMU `-device qemu-xhci` and two `usb-kbd`, one at full speed (`usb_version=1`) | the log shows the controller running on its MSI-X vector, each port connected once, slots 1 and 2 addressed (the full-speed one's EP0 size read from its first 8 bytes), each configuration read and set |
| Keyboard into rzsh | the same script, `-serial none`, `fbcon_screen.py` over QMP | `send-key` types `echo hi` and Enter, and the screen shows `hi` at rzsh's prompt. Ctrl-C kills a foreground `sleep` |
| Hot-plug | the same script | QMP `device_del` and `device_add` of `usb-kbd`, then typing works again |
| Hub | the same script, `-device usb-hub` with `usb-kbd` behind it | typing works through the hub |
| Several controllers | the same script, two `qemu-xhci` devices, the keyboard on the second | the keyboard on any controller works, as on chungus |
| MSI-only and polled | the same script, with MSI-X forced off by a boot option | typing works on the fallback path |

The script joins the `test-tier1` family in `Makefile` as `test-usb`, and the
gate runs it.

## Break-down (children of #4860)

In dependency order toward #4870. Each lands with its tests.

1. **#4887 xHCI core.** `usb_abi` (TRBs, rings, contexts), `drivers/usb/xhci.ritz`
   and the enumeration half of `usb.ritz`: probe, handoff, reset, rings,
   MSI-X to the BSP, ports, Enable Slot, Address Device, descriptors and Set
   Configuration, on one controller. Test: the bring-up boot test.
2. **#4888 HID boot keyboard into the console** (depends on #4887). `hid_kbd.ritz`,
   the keymap in `usb_abi`, `tty_console_input`, repeat. Test: typing into
   rzsh in QEMU, Ctrl-C. This meets #4860's QEMU bar.
3. **#4889 Every controller, hot-plug and recovery** (depends on #4888). All xHCI
   functions, attach and detach on every port, per-controller reset on HSE.
   chungus needs it: the keyboard can be on any of its three functions.
4. **#4890 Hubs** (depends on #4889). The hub class driver, and hub ports in hot-plug.
   Needed if chungus's ports sit behind an on-board hub, or the keyboard is on
   an external hub.
5. **#4891 MSI and the polled fallback** (depends on #4887). Plain MSI (capability 05,
   through the interrupt remapper) for the X99's Intel xHCI, and the tick-poll
   path for a controller with no usable vector. It is not on chungus's path,
   but it is the X99's, and the polled path is a safety net on chungus.

#4870 already depends on #4860, so the boot waits for all five.
