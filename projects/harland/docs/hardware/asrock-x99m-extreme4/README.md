# ASRock X99M Extreme4 desktop: hardware inventory

A Haswell-E desktop on an ASRock X99M Extreme4 board, inventoried with the
stick (#3406, #4300). The board's SMBIOS system fields are all "To Be Filled
By O.E.M.".

| | |
|---|---|
| Board | ASRock X99M Extreme4 |
| Firmware | AMI P1.50 (2014-09-04), UEFI 2.31. Secure Boot off, in setup mode |
| CPU | Intel Core i7-5930K (Haswell-E) @ 3.50 GHz: 6 cores, 12 threads |
| Memory | 32 GiB, 4 x 8 GiB DDR4 at 2133 MT/s (SMBIOS reports the type as "Other") |
| GPU | NVIDIA GeForce GTX 1070 (GP104) [10de:1b81] at 02:00.0 |
| Display | Samsung U28E510 monitor, 3840x2160 |
| Captured | 2026-11-26, by booting the inventory stick |

## Files

| File | Contents |
|---|---|
| `hwinv/` | The stick's dump, scrubbed: raw ACPI, raw SMBIOS, the UEFI memory map, PCI config space, GOP modes, EDID. Layout: `projects/harland/inventory/README.md` |
| `hwinv-summary.txt` | CPU, RAM, PCI names and display, generated from `hwinv/` by `inventory/dump_summary.py` |

## What matters for harland's first boot

- **Framebuffer: UEFI GOP**, on the GTX 1070: firmware boots in mode 0,
  3840x2160, and the framebuffer at 0xe0000000 (size 0x21c0000,
  `hwinv/gop.txt`) is the card's BAR1.
- **Storage:** the X99 SATA controller is in RAID mode [8086:2822] at
  00:1f.2, not AHCI. A driver for it has to match this ID or the board has to
  be switched to AHCI.
- **USB:** X99 xHCI [8086:8d31] at 00:14.0, plus two EHCI controllers.
- **Ethernet:** Intel I218-V [8086:15a1] at 00:19.0 and Qualcomm Atheros
  QCA8171 [1969:10a1] at 04:00.0.
- **MCFG (PCIe ECAM):** base 0x80000000, segment 0, buses 0-255.
- **MADT:** 12 Local APIC entries, all enabled, and 2 IOAPICs: id 8 at
  0xfec00000 (GSI 0) and id 9 at 0xfec01000 (GSI 24).
- **FADT:** revision 5, not hardware-reduced, no S0 idle.
  `IAPC_BOOT_ARCH` = 0x11 (legacy devices, PCIe ASPM controls); the 8042
  flag is clear.
- **NUMA tables:** `SRAT`, `SLIT` and `MSCT` are present on this
  single-socket board. `DMAR` (VT-d) is present.

## Harland driver map

The X99 is the second real-hardware boot, after chungus (the Acer). It
boots the same way: from the USB stick, initramfs from the ESP, rzsh on the
GOP framebuffer typed on a USB keyboard. Storage and Ethernet come after
that. Each device class maps to a harland driver (path under `kernel/src/`)
or to the AGAST ticket that fills the gap. Mapped on main as of 2026-11-27.

| Class | Device | Harland | First boot |
|---|---|---|---|
| Boot, initramfs | UEFI loader on the stick | `boot/` | needed: have |
| Display | GOP framebuffer on the GTX 1070 BAR1, 3840x2160 at 0xe0000000 | `drivers/display` maps it write-combining; `fbcon.ritz` draws text on it, glyphs x2 at 4K (#4868) | needed: have |
| Kernel log, panic screen, tty output | framebuffer | `drivers/display/fbcon.ritz`: klog's and the tty's sink, and the panic screen (#4868) | needed: have |
| Keyboard (USB) | Intel xHCI [8086:8d31] 00:14.0 | gap: USB epic #4860 | **needed** |
| USB 2.0 | EHCI [8086:8d26] 00:1d.0, [8086:8d2d] 00:1a.0 | none; out of scope unless a port is EHCI-only | no |
| SATA | Intel [8086:2822] 00:1f.2, **RAID mode** | gap: SATA/AHCI epic #4861. Switch the firmware to AHCI first (the AHCI-mode ID is a different device ID) | no |
| Ethernet | Intel I218-V [8086:15a1] 00:19.0 | gap: Intel Ethernet epic #4862 | no |
| Ethernet | Qualcomm Atheros QCA8171 [1969:10a1] 04:00.0 | none, not planned | no |
| ACPI | XSDT, MADT, MCFG, FADT, `\_S5` | `drivers/acpi/tables.ritz` | needed: have |
| PCIe config | ECAM 0x80000000, buses 0-255 | `drivers/pci.ritz`, `drivers/pci_ecam.ritz` | needed: have |
| Interrupts | x2APIC, 2 IOAPICs (8, 9), MSI-X | `arch/x86_64/apic.ritz`, `drivers/msix.ritz` | needed: have |
| IOMMU | VT-d, `DMAR` | `drivers/iommu/vtd.ritz`, `dmar.ritz` (interrupt remapping) | on by default |
| GPU | NVIDIA GP104 [10de:1b81] 02:00.0 | none: GOP only | no |
| Audio | HDA [8086:8d20], [10de:10f0] | none | no |
| MEI, KT, IDE-r, SMBus, LPC | [8086:8d3a/8d3b/8d3d/8d3c/8d22/8d47] | none, not needed | no |
| PS/2 | none: the FADT 8042 flag is clear | n/a | no |

### Real-hardware risks

- **No UART** is not confirmed here (the board may have a COM1 header), but
  the console must not depend on one; see the Acer README.
- **Timer calibration.** Haswell-E reports no crystal frequency in CPUID
  0x15 and no 0x16 leaf, so `tsc_calibrate` uses the PIT. The X99 PCH has
  one; `HPET` is present as the fallback.
- **SMP bring-up:** 12 threads, APIC IDs 0-11 (listed even IDs first), all
  enabled.
- **Framebuffer size.** 3840x2160x4 is 33 MiB of uncached device memory
  (`vmm_map_mmio` maps UC): a console scrolling by reading it back is very
  slow. It needs write-combining and a shadow buffer, and an 8x16 font is
  small at this resolution.
- **SATA in RAID mode.** In RAID mode the function's class is 01:04 (RAID),
  not 01:06:01 (AHCI), so an AHCI driver that matches the class code skips
  it. Linux's `ahci` binds [8086:2822] by ID, since the register interface
  is still AHCI. The plan (#4861) is to switch the firmware to AHCI.

## Scrubbing

`hwinv/` was scrubbed by `projects/harland/inventory/scrub_dump.py`. Its
report:

- SMBIOS: the system UUID is zeroed. Every serial number and asset tag is a
  vendor placeholder ("To Be Filled By O.E.M.", blanks, `00000000`,
  `DIMM_A1_AssetTag`), so they were kept.
- `pci.bin`: the Device Serial Number of the Atheros NIC (04:00.0) is zeroed.
- `edid-0.bin`: the monitor's serial number and its serial-number string
  descriptor are zeroed, and the block's checksum is fixed.

After the scrub, the script searched every file for each removed value, as
text, as UTF-16 and as bytes in both byte orders, and for the machine's
hostname and the owner's username. Nothing matched, and `check_dump.py`
passes on the result.
