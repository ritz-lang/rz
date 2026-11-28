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
| `projects/harland/usb_abi/` | New leaf package on the `virtio_abi` pattern, with no kernel imports and its own host unit tests. It holds the xHCI register and TRB layouts, the TRB ring (enqueue, cycle bit, link TRB, event dequeue), the context layouts (32- and 64-byte, `HCCPARAMS1.CSZ`) and where a device is (`SlotPlace`: root port, route string, TT hub slot and port), the USB descriptor parser, the hub class protocol (`hub.ritz`: requests, hub descriptor, port status and changes, the status change bitmap), the endpoint-interval conversion, and the HID boot report decoder (report diff, US keymap, modifiers, escape sequences). |
| `kernel/src/drivers/usb/xhci.ritz` | The controllers, each with its own state: PCI probe, BIOS handoff, reset, DCBAA, scratchpad, command and event rings, interrupter 0 (`setup_vector`, the one place a controller's interrupt source is chosen), port handling, and the tick-driven recovery reset (`xhci_tick`). |
| `kernel/src/drivers/usb/usb.ritz` | Device enumeration per controller and root port: slots, Address Device, control transfers, descriptors, Set Configuration; a configured device a class driver takes is `Bound` and its events go there. Detach and re-attach, a failed controller's devices, and the entry points `usb_irq` (a vector) and `usb_tick` (the BSP tick). |
| `kernel/src/drivers/usb/hid_kbd.ritz` | The HID boot keyboard: Set Protocol (boot), Set Idle, Configure Endpoint for the interrupt-IN endpoint, a Normal TRB always queued, report to bytes into the console, the Caps Lock LED, typematic repeat on the BSP tick. |
| `kernel/src/drivers/usb/hub.ritz` | The hub class driver (USB 2.0 hubs, and USB 3 hubs on their SuperSpeed side): bring-up, port power, debounce, reset and status changes on the hub's interrupt endpoint, and the controller's one default address (see "Hubs"). |

## Concurrency under SMP_USER.md

`SMP_USER.md` §2 (#4874, #4879) is the ownership model this driver follows:
every piece of kernel state has one owner CPU, and only its owner writes it.
The driver adds no lock, no message kind and no CPU of its own.

- **All xHCI state is BSP-owned.** The controller, slot, ring and HID state
  joins the "In-kernel drivers" row of SMP_USER's inventory, next to
  `drivers/nvme`, `virtio/blk`, `virtio/net` and `ena`. It needs no lock
  because only the BSP ever touches it: its three entry points all run there.
  These are the controller's vector (MSI-X, or plain MSI), the
  polled-fallback tick and the console's readers, each covered below. Unlike the other rows it is never lent to an
  AP, because no AP call reaches it.
- **Interrupts go to the BSP.** Each controller's interrupter 0 gets one
  vector from `msix_vector_alloc` with the BSP as its destination
  (`irq_route_dest`, and an IRTE when remapping is on): MSI-X entry 0, or,
  on a function with no MSI-X (the X99's Intel 8086:8d31), plain MSI with
  one message (`msi_enable`, #4885). `setup_vector` in
  `drivers/usb/xhci.ritz` is the one place the source is chosen. The console's wait
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
  before any AP runs a process, with TSC deadlines. A recovery reset after
  boot (see "Hot-plug") does not spin: the BSP tick checks each of its steps
  once per tick. Everything else at run time is event-driven: port reset, Enable Slot, Address Device and every control
  transfer are commands or transfers whose completion arrives as an event, and
  each device is a state machine that the event moves forward. Hot-plug
  therefore never stalls the BSP's other work or keystroke latency, and never
  delays the forwarded calls of netd's core.
- **Polling fallback.** A controller with no usable vector (neither MSI-X
  nor MSI, or neither could be aimed at a CPU) has its INTx masked and is
  polled from the BSP's 100 Hz tick (`usb_tick`, which already runs each
  controller's health check and recovery), calling the same `xhci_irq` body.
  So is one whose vector never fires: at each 100 ms health check
  (`VectorWatch`, `drivers/usb/irq_mode.ritz`), an event waiting on
  interrupter 0's event ring at two checks in a row with no interrupt
  counted on its vector between them moves the controller to the poll for
  good, and the log says so. The ring is asked rather than `IMAN.IP`, which
  can stay set over a drained ring. Ten milliseconds is well inside what typing needs. Only the BSP's tick
  polls, so the poll stays on the owner. The APs' ticks never call it.
- **Test hooks.** The boot options `\harland\usb-no-msix` (GRUB:
  `usb-no-msix`) leave MSI-X off, so each controller uses plain MSI, and
  `\harland\usb-poll` (`usb-poll`) gives no controller a vector, so the
  tick polls each one (#4891). Only the fallback boots set them.

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

## Hubs

How it is built (#4890). `usb.ritz` keeps one device entry per root port and
as many again for devices behind hubs; an entry's number owns its commands
(`xhci_command`), so a detach waits for exactly its own. A configured
device whose configuration has a hub interface (class 9) is handed to
`hub.ritz`, after the keyboard driver declines it.

- **Bring-up.** GET_DESCRIPTOR of the hub descriptor (type 29h; a
  SuperSpeed hub's is 2Ah, and it then gets SET_HUB_DEPTH), then Configure
  Endpoint: the slot context gets Hub, Number of Ports and TT Think Time
  (single TT: MTT is never selected), and the status change endpoint is
  added. Each port gets SET_FEATURE(PORT_POWER), and after bPwrOn2PwrGood
  (on the BSP tick, no spin) every port is looked at once and a Normal TRB
  waits on the status change endpoint, requeued as each bitmap arrives.
  Ports past 15 have no route string field and are not driven.
- **Ports.** The hub's EP0 runs one request at a time. A port the bitmap
  (or the tick) names gets GET_STATUS; each change bit is cleared
  (CLEAR_FEATURE, lowest first) and the status read again until none is
  left; then the port's stage moves on. A new connection is debounced for
  100 ms, reset (SET_FEATURE(PORT_RESET), whose end is a C_PORT_RESET
  change), given 10 ms of reset recovery, and handed to `usb.ritz` as
  attached at the speed its status gives. A SuperSpeed port that is
  enabled already needs no reset.
- **The device below.** It enumerates as a root port's device does, from
  Enable Slot, with its slot context's Route String (tier 1, the hub on the
  root port, in bits 3:0), the root port, and for a low- or full-speed
  device behind a high-speed hub that hub's slot and port as its TT (behind
  a full-speed hub, the nearest high-speed hub's). Its log names it by root
  port and hub ports, as QEMU does: `hc1 port 5.1`.
- **One default address.** A device just reset answers at address 0 until
  Address Device gives it one, so each controller has at most one hub port
  between its reset and its Address Device. The next waiting port is reset
  when that device is addressed, fails, or goes.
- **Detach.** A disconnect, a connect change or a disabled port is the
  device gone, and it detaches as in "Hot-plug". A hub that goes takes
  everything below it with it: its devices detach first (their commands
  queue before its own), then the hub's endpoint is stopped and its slot
  disabled. When a device below a hub is freed, the hub looks at that port
  again.

## Hot-plug

Port Status Change events drive attach and detach for every port, root or
hub. On detach the driver stops the device's endpoints, disables its slot and
frees its rings. If the device was the keyboard, held keys are released so a
repeat cannot outlive the device. On attach it starts at step 7. A Host System
Error or a dead controller (`USBSTS.HSE`, or registers reading all-ones)
resets that controller alone and re-enumerates its ports. The other
controllers keep running.

How it is built (#4889):

- **Detach.** The keyboard's held keys are released at once
  (`HidKbd.release_all`). Then Stop Endpoint for its interrupt-IN endpoint
  and EP0, and Disable Slot, are queued together; the command ring runs them
  in order. The controller counts each root port's outstanding commands, and
  when the port's last one completes, the slot's DCBAA entry is cleared and
  the device's and keyboard's pages go back to the DMA allocator. An Enable
  Slot that was in flight at the disconnect has its slot disabled too. If a
  device is connected again by then, it enumerates from step 7.
- **Recovery.** A Host Controller Error and a vanished controller raise no
  interrupt, so the BSP tick reads each running controller's `USBSTS` every
  100 ms (`HSE`, `HCE` or all-ones). A failed controller's keyboards release
  their keys at once, and the reset then steps once per tick, each step under
  its deadline: clear Run/Stop and wait for `HCHalted`, set `HCRST` and wait
  for it and `CNR` to clear, reprogram the DCBAA and the rings (the pages are
  kept), start, and wait for `HCHalted` to clear. Only then are its devices'
  pages freed and its ports scanned as at boot. No step spins, so the BSP's
  other work and the other controllers' keystrokes are not delayed. A reset
  that times out (a controller that is gone) leaves that controller off and
  its pages leaked, since a half-reset controller may still write them.
- **Test hook.** The boot option `\harland\fault-usb` (GRUB: `fault-usb`)
  fails the last controller once a keyboard on it is ready, by giving
  interrupter 0 a segment table QEMU's controller refuses (it asserts
  `HCE`). Only the enumerate boot sets it.

## Tests

| Test | Where | Checks |
|---|---|---|
| `usb_abi` unit tests | host, `usb_abi/test` | TRB encode, ring wrap and cycle toggle, event dequeue, context sizing (CSZ), descriptor parsing (good and truncated), interval conversion per speed, report diff (press, release, rollover error `0x01` ignored), keymap with modifiers |
| xHCI bring-up boot | `tools/test_usb_boot.sh` (`make test-usb`), two QEMU `qemu-xhci`: two `usb-kbd` on the first, one at full speed (`usb_version=1`), and one on the second, with `\harland\fault-usb` | the log shows each controller running on its own MSI-X vector, each port of the first connected once, its slots 1 and 2 addressed (the full-speed one's EP0 size read from its first 8 bytes), each configuration read and set. The second controller's forced error resets it alone and its keyboard is ready again; the first is never reset |
| Keyboard into rzsh | `tools/test_usb_boot.sh keyboard` (`make test-usb-kbd`): q35 with `i8042=off`, `-serial none`, one `usb-kbd`; `fbcon_screen.py --send` types over QMP | `send-key` types `echo hi` and Enter, and the screen shows `hi` at rzsh's prompt. Ctrl-C kills a foreground `spin` (ring 3, no syscalls, so the kill is the xHCI interrupt's) and `echo $?` shows 130. Caps Lock types `echo ABc` as typed; a key held 1.2 s repeats |
| Hot-plug | the keyboard boot (`fbcon_screen.py --qmp-do`) | QMP `device_del` of `usb-kbd`: its port is detached and its slot disabled. `device_add`: it is ready again and `echo back` types |
| `usb_abi` hub tests | host, `usb_abi/test/test_hub.ritz`, and `test_context.ritz` | hub class requests, the hub descriptor (USB 2 and SuperSpeed, malformed), port status and the change cleared next, the status change bitmap, the hub interface; route string per tier, TT hub slot and port, the hub's slot context fields |
| Hub | `tools/test_usb_boot.sh keyboard-hub` (`make test-usb-hub`): the keyboard boot with QEMU's `usb-hub` on hc1 and `usb-kbd` on its port 1 | the hub is ready and the keyboard behind it addressed by route (`port 5.1`) and ready; `echo hi` types and Ctrl-C kills `spin`. QMP `device_del` of the hub detaches both (each slot disabled, keys released); `device_add` of both and `echo back` types |
| Several controllers | the keyboard boot: two `qemu-xhci` devices, the keyboard on the second | the keyboard on any controller works, as on chungus |
| MSI-only and polled | `tools/test_usb_boot.sh keyboard-msi` (`make test-usb-msi`) and `keyboard-poll` (`make test-usb-poll`): the keyboard boot with `\harland\usb-no-msix` (and `qemu-xhci,msi=on`: QEMU offers MSI only when asked) or `\harland\usb-poll` | hc1's keyboard-ready line on screen names its source (`MSI`, or `polled`; MSI-X boots say `MSI-X`) and no controller runs any other way; `echo hi` types and Ctrl-C kills `spin` (`$?` = 130) |
| Dead-vector watch | host, `test/test_usb_irq_mode.ritz` | which sources each boot option allows; a pending interrupt across two health checks with none delivered is a stall, one look or a delivered interrupt is not |

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
