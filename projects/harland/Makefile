# Harland Microkernel Makefile
# Build system for Ritz-based x86-64 kernel

# ============================================================================
# Configuration
# ============================================================================

# Ritz compiler (assumes ritzc is in PATH or set RITZC env var)
RITZC ?= ritzc
RITZC_FLAGS = --target x86_64-none-elf

# LLVM tools
LLC = llc
LLD = ld.lld
LLVM_AS = llvm-as
OBJCOPY = llvm-objcopy

# QEMU
QEMU = qemu-system-x86_64
OVMF_CODE = /usr/share/OVMF/OVMF_CODE.fd
OVMF_VARS = OVMF_VARS.fd

# Output files
KERNEL = harland.elf
BOOTLOADER = boot/BOOTX64.EFI
IMAGE = harland.qcow2

# ============================================================================
# Source files
# ============================================================================

KERNEL_SRCS = $(wildcard kernel/*.ritz) \
              $(wildcard kernel/mm/*.ritz) \
              $(wildcard kernel/sched/*.ritz) \
              $(wildcard kernel/ipc/*.ritz) \
              $(wildcard kernel/arch/x86_64/*.ritz)

BOOT_SRCS = $(wildcard boot/*.ritz)

# Derived file lists
KERNEL_LL = $(KERNEL_SRCS:.ritz=.ll)
KERNEL_O = $(KERNEL_SRCS:.ritz=.o)
BOOT_LL = $(BOOT_SRCS:.ritz=.ll)
BOOT_O = $(BOOT_SRCS:.ritz=.o)

# ============================================================================
# Phony targets
# ============================================================================

.PHONY: all clean run test test-unit test-qemu test-boot test-uefi-boot debug dirs kernel iso uefi-boot

all: kernel

# Build kernel using rz workspace CLI (recommended)
# The build order in ritz.toml ensures user program builds first, then kernel embeds it
kernel:
	@# Build all harland targets (portable_getpid, harland, bootx64)
	../../rz build harland
	@# Copy to expected locations for ISO creation and test scripts
	@cp build/debug/harland.elf build/harland.elf 2>/dev/null || true
	@cp build/debug/BOOTX64.EFI build/BOOTX64.EFI 2>/dev/null || true

# Build bootable ISO with GRUB
iso: kernel
	./tools/mkiso.sh

clean:
	../../rz clean harland
	rm -f $(KERNEL_LL) $(KERNEL_O) $(BOOT_LL) $(BOOT_O)
	rm -f $(KERNEL) $(BOOTLOADER) $(IMAGE)
	rm -f $(OVMF_VARS)
	./tools/mkiso.sh --clean 2>/dev/null || true

dirs:
	mkdir -p boot kernel/mm kernel/sched kernel/ipc kernel/arch/x86_64
	mkdir -p user/init tests/unit tests/integration tools

# ============================================================================
# Compilation rules
# ============================================================================

# Ritz -> LLVM IR
%.ll: %.ritz
	$(RITZC) $(RITZC_FLAGS) --emit-llvm $< -o $@

# LLVM IR -> Object
%.o: %.ll
	$(LLC) -filetype=obj -mtriple=x86_64-none-elf $< -o $@

# ============================================================================
# Kernel build
# ============================================================================

$(KERNEL): $(KERNEL_O) kernel/linker.ld
	$(LLD) -T kernel/linker.ld -o $@ $(KERNEL_O)

# ============================================================================
# Bootloader build (UEFI)
# ============================================================================

# UEFI apps need PE/COFF format
$(BOOTLOADER): $(BOOT_O) boot/linker.ld
	$(LLD) -T boot/linker.ld -subsystem:efi_application -entry:efi_main -o $@ $(BOOT_O)

# ============================================================================
# Image build
# ============================================================================

$(IMAGE): $(KERNEL) $(BOOTLOADER)
	python3 tools/mkimage.py --kernel $(KERNEL) --bootloader $(BOOTLOADER) --output $@

# Copy OVMF vars for writable NVRAM
$(OVMF_VARS):
	cp /usr/share/OVMF/OVMF_VARS.fd $@

# ============================================================================
# Run targets
# ============================================================================

# VirtIO block devices
INITRAMFS = $(BUILD_DIR)/initramfs.qcow2
STORAGE = $(BUILD_DIR)/storage.qcow2

$(INITRAMFS):
	qemu-img create -f qcow2 $@ 64M

$(STORAGE):
	qemu-img create -f qcow2 $@ 512M

run: $(IMAGE) $(OVMF_VARS) $(INITRAMFS) $(STORAGE)
	$(QEMU) \
		-drive if=pflash,format=raw,file=$(OVMF_CODE),readonly=on \
		-drive if=pflash,format=raw,file=$(OVMF_VARS) \
		-drive file=$(IMAGE),format=qcow2 \
		-device virtio-blk-pci,drive=initramfs \
		-drive file=$(INITRAMFS),format=qcow2,if=none,id=initramfs \
		-device virtio-blk-pci,drive=storage \
		-drive file=$(STORAGE),format=qcow2,if=none,id=storage \
		-m 4G \
		-smp 4 \
		-serial mon:stdio \
		-no-reboot

debug: $(IMAGE) $(OVMF_VARS) $(INITRAMFS) $(STORAGE)
	$(QEMU) \
		-drive if=pflash,format=raw,file=$(OVMF_CODE),readonly=on \
		-drive if=pflash,format=raw,file=$(OVMF_VARS) \
		-drive file=$(IMAGE),format=qcow2 \
		-device virtio-blk-pci,drive=initramfs \
		-drive file=$(INITRAMFS),format=qcow2,if=none,id=initramfs \
		-device virtio-blk-pci,drive=storage \
		-drive file=$(STORAGE),format=qcow2,if=none,id=storage \
		-m 4G \
		-smp 4 \
		-serial mon:stdio \
		-no-reboot \
		-d int,cpu_reset \
		-S -s

# ============================================================================
# Test targets
# ============================================================================

test: test-boot

# Milestone 1: Boot and print to serial (GRUB/Multiboot2)
test-boot: iso
	@echo "Running boot test (GRUB)..."
	./tools/test_boot.sh

# UEFI bootloader test (Ritz UEFI bootloader)
uefi-boot: kernel
	@echo "UEFI bootloader built as part of kernel target"

test-uefi-boot: kernel
	@echo "Testing UEFI bootloader..."
	cd boot && ./test.sh

test-unit:
	@echo "Running host unit tests..."
	$(RITZC) --target x86_64-linux --test tests/unit/*.ritz -o test_runner
	./test_runner

test-qemu: $(IMAGE)
	@echo "Running QEMU integration tests..."
	$(QEMU) \
		-drive if=pflash,format=raw,file=$(OVMF_CODE),readonly=on \
		-drive if=pflash,format=raw,file=$(OVMF_VARS) \
		-drive file=$(IMAGE),format=qcow2 \
		-m 4G \
		-nographic \
		-serial mon:stdio \
		-no-reboot \
		-device isa-debug-exit,iobase=0xf4,iosize=0x04 \
		| tee test_output.log
	@grep -q "ALL TESTS PASSED" test_output.log && echo "Tests passed!" || (echo "Tests failed!" && exit 1)

# ============================================================================
# Help
# ============================================================================

help:
	@echo "Harland Microkernel Build System"
	@echo ""
	@echo "Quick Start (Milestone 1):"
	@echo "  make kernel     - Build the kernel"
	@echo "  make test-boot  - Build & test in QEMU (check serial output)"
	@echo ""
	@echo "Targets:"
	@echo "  kernel         - Build kernel using build.py (recommended)"
	@echo "  iso            - Build bootable ISO with GRUB"
	@echo "  uefi-boot      - Build UEFI bootloader (Ritz)"
	@echo "  clean          - Remove build artifacts"
	@echo "  run            - Boot kernel in QEMU (requires full image)"
	@echo "  debug          - Boot kernel in QEMU with GDB server"
	@echo "  test           - Run tests (same as test-boot for now)"
	@echo "  test-boot      - Quick boot test via QEMU (GRUB)"
	@echo "  test-uefi-boot - Test UEFI bootloader via QEMU"
	@echo "  dirs           - Create directory structure"
	@echo "  help           - Show this help"
