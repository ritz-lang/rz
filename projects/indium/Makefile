# Indium Distribution Makefile
# Builds userspace, kernel, and creates bootable images

# ============================================================================
# Configuration
# ============================================================================

# Paths
HARLAND_DIR = ../harland
RZSH_DIR = ../rzsh
BUILD_DIR = build
KERNEL_ELF = $(HARLAND_DIR)/build/debug/harland.elf
BOOTLOADER = $(HARLAND_DIR)/build/debug/BOOTX64.EFI
ISO_FILE = $(BUILD_DIR)/indium.iso
UEFI_DISK = $(BUILD_DIR)/uefi-boot.img

# QEMU
QEMU = qemu-system-x86_64

# Find OVMF firmware
OVMF_CODE := $(shell for p in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd /usr/share/edk2/x64/OVMF_CODE.4m.fd; do [ -f "$$p" ] && echo "$$p" && break; done)

# VirtIO disks
INITRAMFS = $(BUILD_DIR)/initramfs.qcow2
STORAGE = $(BUILD_DIR)/storage.qcow2

# ============================================================================
# Phony targets
# ============================================================================

.PHONY: all clean kernel userspace rzsh iso run run-iso run-uefi debug test test-uefi test-uefi-gui help

all: iso

# ============================================================================
# Build targets
# ============================================================================

# Build the Harland kernel (delegates to harland project)
kernel:
	@echo "=== Building Harland Kernel ==="
	$(MAKE) -C $(HARLAND_DIR) kernel

# Build userspace programs
userspace:
	@echo "=== Building Indium Userspace ==="
	../../rz build indium
	@mkdir -p $(BUILD_DIR)/debug
	@cp build/debug/*.elf $(BUILD_DIR)/debug/ 2>/dev/null || true

# Build rzsh (Ritz Shell)
rzsh:
	@echo "=== Building rzsh ==="
	../../rz build rzsh
	@mkdir -p $(BUILD_DIR)/debug
	@cp $(RZSH_DIR)/build/debug/rzsh.elf $(BUILD_DIR)/debug/ 2>/dev/null || true

# Build bootable ISO with kernel and userspace
iso: kernel
	@echo "=== Creating Indium ISO ==="
	@mkdir -p $(BUILD_DIR)
	./tools/mkiso.sh

# Create UEFI boot disk (uses mtools, no root required)
$(UEFI_DISK): kernel
	@echo "=== Creating UEFI Boot Disk ==="
	@mkdir -p $(BUILD_DIR)
	@# Create 64MB FAT disk image
	dd if=/dev/zero of=$@ bs=1M count=64 2>/dev/null
	mkfs.vfat $@ >/dev/null
	@# Create EFI directory structure
	mmd -i $@ ::/EFI
	mmd -i $@ ::/EFI/BOOT
	mmd -i $@ ::/harland
	@# Copy bootloader and kernel
	mcopy -i $@ $(BOOTLOADER) ::/EFI/BOOT/BOOTX64.EFI
	mcopy -i $@ $(KERNEL_ELF) ::/harland/kernel.elf
	@# Create startup script
	@echo '@echo -off' > $(BUILD_DIR)/startup.nsh
	@echo 'FS0:\EFI\BOOT\BOOTX64.EFI' >> $(BUILD_DIR)/startup.nsh
	mcopy -i $@ $(BUILD_DIR)/startup.nsh ::/startup.nsh
	@echo "Created: $@"

# ============================================================================
# Run targets
# ============================================================================

# Create test disks
$(INITRAMFS):
	@mkdir -p $(BUILD_DIR)
	qemu-img create -f qcow2 $@ 64M

$(STORAGE):
	@mkdir -p $(BUILD_DIR)
	qemu-img create -f qcow2 $@ 512M

# Default run: BIOS/ISO (most reliable)
run: run-iso

# Run with ISO (BIOS/Multiboot2 boot) - most reliable
run-iso: iso $(INITRAMFS) $(STORAGE)
	$(QEMU) \
		-cdrom $(ISO_FILE) \
		-device virtio-blk-pci,drive=initramfs \
		-drive file=$(INITRAMFS),format=qcow2,if=none,id=initramfs \
		-device virtio-blk-pci,drive=storage \
		-drive file=$(STORAGE),format=qcow2,if=none,id=storage \
		-device virtio-net-pci,netdev=net0 \
		-netdev user,id=net0 \
		-device virtio-keyboard-pci \
		-device virtio-mouse-pci \
		-m 4G \
		-smp 4 \
		-serial mon:stdio \
		-no-reboot

# Run with UEFI (uses mtools-based disk image)
run-uefi: $(UEFI_DISK) $(INITRAMFS) $(STORAGE)
	@if [ -z "$(OVMF_CODE)" ]; then echo "ERROR: OVMF not found. Install ovmf package."; exit 1; fi
	$(QEMU) \
		-drive if=pflash,format=raw,readonly=on,file=$(OVMF_CODE) \
		-drive format=raw,file=$(UEFI_DISK) \
		-device virtio-blk-pci,drive=initramfs \
		-drive file=$(INITRAMFS),format=qcow2,if=none,id=initramfs \
		-device virtio-blk-pci,drive=storage \
		-drive file=$(STORAGE),format=qcow2,if=none,id=storage \
		-device virtio-net-pci,netdev=net0 \
		-netdev user,id=net0 \
		-device virtio-keyboard-pci \
		-device virtio-mouse-pci \
		-m 256M \
		-smp 4 \
		-serial mon:stdio \
		-no-reboot

# Run with GDB server for debugging (BIOS mode)
debug: iso $(INITRAMFS) $(STORAGE)
	$(QEMU) \
		-cdrom $(ISO_FILE) \
		-device virtio-blk-pci,drive=initramfs \
		-drive file=$(INITRAMFS),format=qcow2,if=none,id=initramfs \
		-device virtio-blk-pci,drive=storage \
		-drive file=$(STORAGE),format=qcow2,if=none,id=storage \
		-device virtio-net-pci,netdev=net0 \
		-netdev user,id=net0 \
		-m 4G \
		-smp 4 \
		-serial mon:stdio \
		-no-reboot \
		-d int,cpu_reset \
		-S -s

# Debug with UEFI
debug-uefi: $(UEFI_DISK) $(INITRAMFS) $(STORAGE)
	@if [ -z "$(OVMF_CODE)" ]; then echo "ERROR: OVMF not found. Install ovmf package."; exit 1; fi
	$(QEMU) \
		-drive if=pflash,format=raw,readonly=on,file=$(OVMF_CODE) \
		-drive format=raw,file=$(UEFI_DISK) \
		-device virtio-blk-pci,drive=initramfs \
		-drive file=$(INITRAMFS),format=qcow2,if=none,id=initramfs \
		-device virtio-blk-pci,drive=storage \
		-drive file=$(STORAGE),format=qcow2,if=none,id=storage \
		-device virtio-net-pci,netdev=net0 \
		-netdev user,id=net0 \
		-m 256M \
		-smp 4 \
		-serial mon:stdio \
		-no-reboot \
		-d int,cpu_reset \
		-S -s

# ============================================================================
# Test targets
# ============================================================================

# Test kernel boot (delegates to harland's test)
test: kernel
	$(MAKE) -C $(HARLAND_DIR) test-boot

# Test UEFI boot (delegates to harland's test)
test-uefi: kernel
	$(MAKE) -C $(HARLAND_DIR) test-uefi-boot

# Test UEFI boot with GUI display (shows framebuffer)
test-uefi-gui: kernel
	$(MAKE) -C $(HARLAND_DIR) test-uefi-gui

# ============================================================================
# Clean
# ============================================================================

clean:
	rm -rf $(BUILD_DIR)
	../../rz clean indium 2>/dev/null || true

# ============================================================================
# Help
# ============================================================================

help:
	@echo "Indium Distribution Build System"
	@echo ""
	@echo "Build Targets:"
	@echo "  all         - Build ISO (default)"
	@echo "  kernel      - Build Harland kernel"
	@echo "  userspace   - Build userspace programs"
	@echo "  iso         - Create bootable ISO with GRUB"
	@echo ""
	@echo "Run Targets:"
	@echo "  run         - Boot in QEMU (BIOS/GRUB mode, default)"
	@echo "  run-iso     - Boot in QEMU (BIOS/GRUB mode)"
	@echo "  run-uefi    - Boot in QEMU (UEFI mode)"
	@echo "  debug       - Boot with GDB server on :1234 (BIOS)"
	@echo "  debug-uefi  - Boot with GDB server on :1234 (UEFI)"
	@echo ""
	@echo "Test Targets:"
	@echo "  test        - Run kernel boot test (BIOS)"
	@echo "  test-uefi   - Run kernel boot test (UEFI, headless)"
	@echo "  test-uefi-gui - Test UEFI with display (see framebuffer)"
	@echo ""
	@echo "Other:"
	@echo "  clean       - Remove build artifacts"
	@echo "  help        - Show this help"
