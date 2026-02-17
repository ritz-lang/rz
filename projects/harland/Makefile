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

.PHONY: all clean test test-boot test-uefi-boot test-uefi-gui kernel iso help

all: kernel

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
	@echo 'menuentry "Harland" { multiboot2 /boot/harland.elf; boot; }' >> $(BUILD_DIR)/isodir/boot/grub/grub.cfg
	grub-mkrescue -o $(ISO) $(BUILD_DIR)/isodir -- -volid "HARLAND"

# ============================================================================
# Test targets
# ============================================================================

test: test-boot

# Boot test via GRUB (BIOS mode)
test-boot: iso
	@echo "=== Testing Kernel Boot (GRUB) ==="
	./tools/test_boot.sh

# UEFI bootloader test (headless)
test-uefi-boot: kernel
	@echo "=== Testing UEFI Bootloader ==="
	cd boot && ./test.sh

# UEFI bootloader test with GUI display (shows framebuffer)
test-uefi-gui: kernel
	@echo "=== Testing UEFI Bootloader (GUI) ==="
	cd boot && ./test.sh --gui

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
	@echo "  test         - Run kernel boot test"
	@echo "  test-boot    - Run kernel boot test (GRUB/BIOS)"
	@echo "  test-uefi-boot - Test UEFI bootloader (headless)"
	@echo "  test-uefi-gui  - Test UEFI bootloader with display"
	@echo "  clean        - Remove build artifacts"
	@echo "  help         - Show this help"
	@echo ""
	@echo "For full distribution builds:"
	@echo "  cd ../indium && make run"
