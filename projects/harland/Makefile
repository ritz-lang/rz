# Harland Microkernel Makefile
# Builds the kernel and provides minimal testing
#
# For full distribution builds (userspace, ISO, disk images),
# use the indium project instead.

# ============================================================================
# Configuration
# ============================================================================

# QEMU
QEMU = qemu-system-x86_64

# Output files
BUILD_DIR = build
KERNEL = $(BUILD_DIR)/harland.elf
BOOTLOADER = $(BUILD_DIR)/BOOTX64.EFI
ISO = $(BUILD_DIR)/harland.iso

# ============================================================================
# Phony targets
# ============================================================================

.PHONY: all build clean test test-boot test-smp test-tier1 test-uefi-boot test-uefi-gui run-gui kernel iso help inventory-img test-inventory

all: kernel

# `build` is the conventional entry point every other project exposes, and
# what CI invokes. Harland's equivalent has always been `kernel`; this alias
# means the workspace-wide build loop no longer has to special-case it.
build: kernel

# ============================================================================
# Build targets
# ============================================================================

# Build kernel using rz workspace CLI
kernel:
	@echo "=== Building Harland Kernel ==="
	../../rz build harland
	@# Copy to expected locations for test scripts
	@mkdir -p $(BUILD_DIR)
	@cp build/debug/harland.elf $(KERNEL) 2>/dev/null || true
	@cp build/debug/BOOTX64.EFI $(BOOTLOADER) 2>/dev/null || true

# Build bootable ISO with GRUB (for kernel testing)
# NOTE: For distribution ISO, use indium project
iso: kernel
	@echo "=== Creating Test ISO ==="
	@mkdir -p $(BUILD_DIR)/isodir/boot/grub
	@cp $(KERNEL) $(BUILD_DIR)/isodir/boot/harland.elf
	@echo 'set timeout=0' > $(BUILD_DIR)/isodir/boot/grub/grub.cfg
	@echo 'set default=0' >> $(BUILD_DIR)/isodir/boot/grub/grub.cfg
	@echo 'insmod all_video' >> $(BUILD_DIR)/isodir/boot/grub/grub.cfg
	@echo 'menuentry "Harland" { multiboot2 /boot/harland.elf; boot; }' >> $(BUILD_DIR)/isodir/boot/grub/grub.cfg
	grub-mkrescue -o $(ISO) $(BUILD_DIR)/isodir -- -volid "HARLAND"

# ============================================================================
# Test targets
# ============================================================================

test: test-boot

# Boot the GRUB ISO under legacy BIOS with the real initramfs. Fails on a
# KERNEL PANIC or EXCEPTION and needs init's Tier-1 suite to report ALL TESTS
# PASSED (#3437: it used to boot a blank disk and pass on the banner alone).
test-boot: iso
	@echo "=== Testing Kernel Boot (GRUB) ==="
	./tools/test_boot.sh

# AGAST #4192: two CPUs in a ring-3 SYSCALL at once, each on its own per-CPU
# stack. The acceptance boot; test-boot also checks the verdict at -smp 4.
test-smp:
	@echo "=== Testing per-CPU syscall stacks (-smp 2) ==="
	QEMU_SMP=2 ./tools/test_tier1_boot.sh native

# Boot the kernel and the indium userspace (native loader and GRUB multiboot2)
# and check init's Tier-1 suite: the spawn -> exit -> parent resume path (#2132)
test-tier1:
	./tools/test_tier1_boot.sh

# UEFI bootloader test (headless)
test-uefi-boot: kernel
	@echo "=== Testing UEFI Bootloader ==="
	cd boot && ./test.sh

# UEFI bootloader test with GUI display (shows framebuffer)
test-uefi-gui: kernel
	@echo "=== Testing UEFI Bootloader (GUI) ==="
	cd boot && ./test.sh --gui

# Interactive run with GUI (no timeout, kill QEMU manually)
run-gui: kernel
	@echo "=== Running Harland (GUI, interactive) ==="
	cd boot && ./test.sh --gui --interactive

# Hardware-inventory USB stick (AGAST #3406): HWINV.EFI on a GPT + FAT32
# image for `dd` or Etcher. See inventory/README.md.
INVENTORY_IMG ?= $(BUILD_DIR)/hwinv.img
INVENTORY_MIB ?= 64
inventory-img: kernel
	python3 inventory/esp_image.py build $(INVENTORY_IMG) --efi build/debug/HWINV.EFI --size-mib $(INVENTORY_MIB)

# Boot the stick image headless (q35 + OVMF, USB storage) and check the dump
test-inventory: kernel
	SKIP_BUILD=1 ./inventory/test.sh

# ============================================================================
# Clean
# ============================================================================

clean:
	../../rz clean harland 2>/dev/null || true
	rm -rf $(BUILD_DIR)

# ============================================================================
# Help
# ============================================================================

help:
	@echo "Harland Microkernel Build System"
	@echo ""
	@echo "This builds the kernel only. For full distribution builds,"
	@echo "including userspace and disk images, use the indium project."
	@echo ""
	@echo "Targets:"
	@echo "  kernel       - Build the kernel (default)"
	@echo "  iso          - Create test ISO with GRUB"
	@echo "  test         - Run kernel boot test (= test-boot)"
	@echo "  test-boot    - Boot the ISO (BIOS/GRUB) with the initramfs; needs ALL TESTS PASSED"
	@echo "  test-smp     - Boot with -smp 2 and check two CPUs in SYSCALL at once (#4192)"
	@echo "  test-tier1   - Boot with indium, check init Tier-1 suite (OVMF)"
	@echo "  test-uefi-boot - Test UEFI bootloader (headless)"
	@echo "  test-uefi-gui  - Test UEFI bootloader with display"
	@echo "  inventory-img  - Build the hardware-inventory USB stick image (build/hwinv.img)"
	@echo "  test-inventory - Boot the inventory stick in QEMU and check its dump"
	@echo "  run-gui        - Interactive run (no timeout, kill QEMU manually)"
	@echo "  clean        - Remove build artifacts"
	@echo "  help         - Show this help"
	@echo ""
	@echo "For full distribution builds:"
	@echo "  cd ../indium && make run"
