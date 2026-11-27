# Acer Aspire 3 A315-24PT: hardware inventory

An AMD laptop that runs Windows, inventoried with the stick (#3406, #4300).

| | |
|---|---|
| Model | Acer Aspire A315-24PT ("Aspire 3 15"), board MDC Herbag_MDU V1.18 |
| Firmware | Insyde V1.18 (2024-06-18), UEFI 2.80. Secure Boot was off for the capture |
| CPU | AMD Ryzen 5 7520U (Mendocino, Zen 2): 4 cores, 8 threads |
| Memory | 16 GiB LPDDR5-5500, soldered (two 8 GiB channels) |
| Display | 1920x1080 internal panel, Innolux (CMN) N156HCN-EAA |
| Captured | 2026-11-26, by booting the inventory stick |

## Files

| File | Contents |
|---|---|
| `hwinv/` | The stick's dump, scrubbed: raw ACPI, raw SMBIOS, the UEFI memory map, PCI config space, GOP modes, EDID. Layout: `projects/harland/inventory/README.md` |
| `hwinv-summary.txt` | CPU, RAM, PCI names and display, generated from `hwinv/` by `inventory/dump_summary.py` |

## What matters for harland's first boot

- **Framebuffer: UEFI GOP.** Firmware boots in mode 0, 1920x1080. The
  framebuffer is at 0x7ee0000000, size 0x7e9000 (`hwinv/gop.txt`). The GPU is
  the integrated Radeon (Mendocino) [1002:1506] at 03:00.0.
- **NVMe:** Kingston OM8PGP4 (DRAM-less) [2646:501b] at 01:00.0.
- **USB:** three AMD xHCI functions, at 03:00.3, 03:00.4 and 04:00.0.
- **WiFi:** MediaTek MT7921 [14c3:7961] at 02:00.0. There is no wired
  Ethernet controller.
- **MCFG (PCIe ECAM):** base 0xe0000000, segment 0, buses 0-255.
- **MADT:** 16 Local APIC entries (8 enabled) and 2 IOAPICs: id 33 at
  0xfec00000 (GSI 0) and id 34 at 0xfec01000 (GSI 24).
- **FADT:** revision 5, not hardware-reduced, `LOW_POWER_S0_IDLE_CAPABLE`
  set. `IAPC_BOOT_ARCH` = 0x3 (legacy devices, 8042).
- **IOMMU:** AMD-Vi, `IVRS` present. `CRAT` and `CDIT` describe the APU
  topology for HSA.

## Harland driver map

chungus is the **first real-hardware boot** (#4870). The bar: harland boots
from the USB stick to rzsh on the GOP framebuffer, typed on a USB keyboard,
with the kernel log and panic screen on screen. The initramfs comes from the
stick's ESP (the UEFI loader reads it), so no storage driver is needed.
Before a test boot, drain chungus or PAUSE its rooms: it is an rz room host
and someone's desktop.

Each device class maps to a harland driver (path under `kernel/src/`) or to
the AGAST ticket that fills the gap. Mapped on main as of 2026-11-27.

| Class | Device | Harland | First boot |
|---|---|---|---|
| Boot, initramfs | UEFI loader, `\EFI\BOOT\BOOTX64.EFI` on the stick | `boot/` | needed: have |
| Display | GOP framebuffer, 1920x1080 at 0x7ee0000000 | `drivers/display` maps and fills it; it draws **no text** | needed: have |
| Kernel log, panic screen, tty output | framebuffer (there is no serial port) | gap: `klog` and `tty/console.ritz` write COM1 only. On-screen log + panic #4868 | **needed** |
| Keyboard (USB) | AMD xHCI [1022:1503] 03:00.3, [1022:1504] 03:00.4, [1022:1505] 04:00.0 | gap: USB epic #4860 | **needed** |
| Keyboard (internal) | i8042 PS/2, ACPI `MSFT0001` (in the DSDT); FADT `IAPC_BOOT_ARCH` has the 8042 flag | gap: PS/2 #4869 | not needed |
| ACPI | XSDT, MADT, MCFG, FADT, `\_S5` | `drivers/acpi/tables.ritz` | needed: have |
| PCIe config | ECAM 0xe0000000, buses 0-255 | `drivers/pci.ritz`, `drivers/pci_ecam.ritz` | needed: have |
| Interrupts | x2APIC, 2 IOAPICs (33, 34), MSI-X | `arch/x86_64/apic.ritz`, `drivers/msix.ritz` | needed: have |
| IOMMU | AMD-Vi [1022:14b6] 00:00.2, `IVRS` | `drivers/iommu/amdvi.ritz`, `ivrs.ritz` (interrupt remapping, DMA pass-through) | on by default |
| NVMe | Kingston OM8PGP4 [2646:501b] 01:00.0 | `drivers/nvme` | not needed |
| WiFi | MediaTek MT7921 [14c3:7961] 02:00.0 | none, not planned | no |
| GPU | Radeon Mendocino [1002:1506] 03:00.0 | none: GOP only | no |
| Audio | HDA [1002:1640], [1022:15e3]; ACP [1022:15e2] | none | no |
| PSP/CCP, SMBus, LPC | [1022:1649], [1022:790b], [1022:790e] | none, not needed | no |

### Real-hardware risks

- **No UART.** With nothing at COM1, port reads return 0xFF, so
  `serial_data_available()` (LSR bit 0) is always true and
  `tty_console_pull`'s `while serial_data_available()` loop never ends: the
  first console read hangs, feeding 0xFF bytes into the line discipline.
  Output does not hang (THRE also reads set). The on-screen log ticket #4868
  probes COM1 (scratch register / LSR 0xFF) and drops it when absent.
- **Timer calibration.** `tsc_calibrate` tries CPUID 0x15, then the PIT,
  then CPUID 0x16. Zen 2 has neither leaf, so the PIT is the only real
  source. If the FCH's 8254 doesn't tick, the TSC and LAPIC timer run on an
  "uncalibrated guess". The `HPET` table is present: HPET is the fallback to
  add if the boot log shows `(uncalibrated guess)`.
- **SMP bring-up:** 8 threads. The MADT lists 16 Local APICs, IDs 0-7
  enabled and 8 more with flags 0; `cpu_map` skips those (it needs Enabled
  or Online Capable). First boot on real INIT-SIPI-SIPI timing.
- **AMD-Vi.** Interrupt remapping turns on whenever `IVRS` exists, so every
  IOAPIC and MSI interrupt goes through it. The IVRS special entries look
  standard: IOAPIC 33 at 00:14.0, IOAPIC 34 at 00:00.1, HPET 0 at 00:14.0.
  A wrong special entry is a known firmware bug that silences legacy IRQs;
  suspect it first if the keyboard or timer IRQ never arrives.
- **Framebuffer speed.** The framebuffer is device memory. A text console
  that scrolls by reading it back is slow unless it is mapped
  write-combining and drawn from a shadow buffer.

## Scrubbing

`hwinv/` was scrubbed by `projects/harland/inventory/scrub_dump.py`. Its
report:

- SMBIOS: the system and baseboard serial numbers (overwritten with `X`s)
  and the system UUID (zeroed). The chassis serial and asset tags are vendor
  placeholders ("Chassis Serial Number", "Type2 - Board Asset Tag"), and the
  DIMM serials are `00000000`, so they were kept.
- `acpi/MSDM`: the embedded Windows product key is overwritten with `X`s and
  the table's checksum is fixed.
- No PCI function has a Device Serial Number, and the EDID has no serial
  number.

After the scrub, the script searched every file for each removed value, as
text, as UTF-16 and as bytes in both byte orders, and for the machine's
hostname and the owner's username. Nothing matched, and `check_dump.py`
passes on the result.
