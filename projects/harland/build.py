#!/usr/bin/env python3
"""
Harland Build System

Builds the Harland microkernel components:
  - kernel: Freestanding x86-64 ELF
  - boot: UEFI bootloader (PE/COFF)
  - image: Bootable qcow2 disk image

Usage:
    python3 build.py build [kernel|boot|image|all]
    python3 build.py run
    python3 build.py test
    python3 build.py clean

This wraps the ritz compiler with the appropriate flags for freestanding builds.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Project paths
PROJECT_ROOT = Path(__file__).parent.resolve()
RITZ_DIR = PROJECT_ROOT / "ritz"
BUILD_DIR = PROJECT_ROOT / "build"
KERNEL_DIR = PROJECT_ROOT / "kernel"
BOOT_DIR = PROJECT_ROOT / "boot"
USER_DIR = PROJECT_ROOT / "user"
TOOLS_DIR = PROJECT_ROOT / "tools"

# Output files
KERNEL_ELF = BUILD_DIR / "harland.elf"
BOOTLOADER_EFI = BUILD_DIR / "BOOTX64.EFI"
IMAGE_QCOW2 = BUILD_DIR / "harland.qcow2"
INITRAMFS_QCOW2 = BUILD_DIR / "initramfs.qcow2"  # Kernel modules, drivers
STORAGE_QCOW2 = BUILD_DIR / "storage.qcow2"      # General storage

# QEMU/OVMF paths
OVMF_CODE = Path("/usr/share/OVMF/OVMF_CODE.fd")
OVMF_VARS_TEMPLATE = Path("/usr/share/OVMF/OVMF_VARS.fd")
OVMF_VARS = BUILD_DIR / "OVMF_VARS.fd"


def run(cmd: list[str], check: bool = True, cwd: Optional[Path] = None, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    # Merge with current environment if env is provided
    run_env = None
    if env:
        run_env = os.environ.copy()
        run_env.update(env)
    result = subprocess.run(cmd, cwd=cwd, capture_output=False, env=run_env)
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result


def find_llvm_tool(name: str) -> str:
    """Find LLVM tool, trying versioned names."""
    import shutil
    # For lld, prefer ld.lld over the generic wrapper
    if name == "lld":
        if shutil.which("ld.lld"):
            return "ld.lld"
        for ver in ["20", "19", "18", "17", "16", "15"]:
            if shutil.which(f"ld.lld-{ver}"):
                return f"ld.lld-{ver}"
    # Try unversioned first
    if shutil.which(name):
        return name
    # Try common version suffixes
    for ver in ["20", "19", "18", "17", "16", "15", "14"]:
        versioned = f"{name}-{ver}"
        if shutil.which(versioned):
            return versioned
    # Not found
    return name  # Will fail later with helpful error


LLC = find_llvm_tool("llc")
LLD = find_llvm_tool("lld")


def ensure_dirs():
    """Create build directories."""
    BUILD_DIR.mkdir(exist_ok=True)
    (BUILD_DIR / "kernel").mkdir(exist_ok=True)
    (BUILD_DIR / "boot").mkdir(exist_ok=True)


def find_ritz_compiler() -> Path:
    """Find the ritz compiler."""
    # First check if we have a local ritz submodule
    local_ritz = RITZ_DIR / "ritz"
    if local_ritz.exists():
        return local_ritz

    # Check if ritz is in PATH
    import shutil
    ritz_path = shutil.which("ritz")
    if ritz_path:
        return Path(ritz_path)

    print("Error: ritz compiler not found")
    print("  - Check that ./ritz submodule is initialized")
    print("  - Or install ritz globally")
    sys.exit(1)


def find_ritz_sources(src_dir: Path) -> list[Path]:
    """Find all .ritz source files in a directory tree.

    Returns sources in dependency order: base modules first, then main.
    Excludes broken/WIP modules.
    """
    # Modules to exclude (old/broken/WIP)
    exclude = {
        "arch/x86_64/syscall.ritz",   # WIP - needs syntax updates
        "arch/x86_64/interrupts.ritz", # WIP - needs syntax updates
        "arch/x86_64/idt.ritz",       # WIP - needs syntax updates
        "arch/x86_64/apic.ritz",      # WIP - needs syntax updates
        "arch/x86_64/gdt.ritz",       # WIP - needs syntax updates
        "process.ritz",               # WIP
    }

    # Explicit module order (dependencies first)
    # This ensures io.ritz compiles before serial.ritz which imports it
    ordered_modules = [
        "io.ritz",                     # Base: port I/O, CPU control (no deps)
        "serial.ritz",                 # Depends on: io
        "drivers/pci.ritz",            # Depends on: io, serial
        "mm/pmm.ritz",                 # Depends on: serial (Physical Memory Manager)
        "mm/vmm.ritz",                 # Depends on: serial, mm/pmm (Virtual Memory Manager)
        "mm/heap.ritz",                # Depends on: serial, mm/pmm, mm/vmm (Kernel Heap)
        "mm/shm.ritz",                 # Depends on: mm/pmm, mm/heap (Shared Memory)
        "mm/dma.ritz",                 # Depends on: mm/pmm, mm/heap (DMA Allocation)
        "ipc/message.ritz",            # IPC message structures (no deps)
        "ipc/channel.ritz",            # Depends on: serial, mm/heap, ipc/message
        "ipc/syscall.ritz",            # Depends on: serial, ipc/message, ipc/channel
        "cap/types.ritz",              # Capability type definitions (no deps)
        "cap/table.ritz",              # Depends on: serial, mm/heap, cap/types
        "cap/syscall.ritz",            # Depends on: serial, cap/types, cap/table
        "drivers/virtio/common.ritz",  # VirtIO common layer
        "drivers/virtio/blk.ritz",     # VirtIO block device driver
        # Filesystem modules (Goliath + VFS)
        "fs/kpath.ritz",               # Path handling (no deps)
        "fs/kdir_entry.ritz",          # Directory entry structure (no deps)
        "fs/backend.ritz",             # Backend types (no deps)
        "fs/kblob.ritz",               # Blob storage layer
        "fs/knamespace.ritz",          # Namespace layer (legacy, blob-backed)
        "fs/namespace.ritz",           # In-memory namespace tree (new!)
        "fs/vfs.ritz",                 # VFS layer
        "fs/syscall.ritz",             # Filesystem syscalls
        "fs/initramfs.ritz",           # Initramfs loader
        # arch/x86_64 modules need syntax updates before enabling
        "main.ritz",                   # Depends on: all of the above
    ]

    sources = []
    for mod in ordered_modules:
        path = src_dir / mod
        if path.exists():
            sources.append(path)

    return sources


def build_kernel_native(flat: bool = False):  # True higher-half by default
    """Build the kernel using native Ritz with inline assembly.

    Args:
        flat: If True, build flat kernel at 1MB (legacy, symbols at physical addresses)
              If False (default), build true higher-half kernel (symbols at virtual addresses)
    """
    print("\n=== Building Kernel (Native Inline ASM) ===")
    ensure_dirs()

    ritz = find_ritz_compiler()
    kernel_src = KERNEL_DIR / "src"
    main_src = kernel_src / "main.ritz"
    boot_asm = KERNEL_DIR / "boot.s"

    if not main_src.exists():
        print(f"Error: Kernel main not found at {main_src}")
        return False

    # Find all .ritz source files
    ritz_sources = find_ritz_sources(kernel_src)
    ritz_objects = []

    # Compile each .ritz file to .ll then .o
    for src_file in ritz_sources:
        # Compute relative path for output naming
        rel_path = src_file.relative_to(kernel_src)
        ll_path = BUILD_DIR / "kernel" / rel_path.with_suffix(".ll")
        obj_path = BUILD_DIR / "kernel" / rel_path.with_suffix(".o")

        # Ensure output directory exists
        ll_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  Compiling {rel_path}")
        result = run([
            str(ritz), "compile", str(src_file),
            "--no-runtime",  # Don't emit _start, we have our own entry
            "-o", str(ll_path)
        ], check=False, env={"RITZ_PATH": str(kernel_src)})

        if result.returncode != 0:
            print(f"  Ritz compilation failed for {rel_path}")
            return False

        # Compile LLVM IR to object file (64-bit)
        print(f"  Compiling {rel_path.with_suffix('.ll')} to object")
        run([LLC, "-filetype=obj", "-mtriple=x86_64-none-elf",
             "-relocation-model=static", "-code-model=kernel",
             str(ll_path), "-o", str(obj_path)])

        ritz_objects.append(obj_path)

    # Step 3: Assemble boot.s
    # The boot.s contains both 32-bit entry (from GRUB) and 64-bit code
    # We assemble as ELF64 since that's what the linker expects for x86-64
    boot_obj = BUILD_DIR / "kernel" / "boot.o"
    if boot_asm.exists():
        print("  Assembling boot.s (Multiboot2 + long mode trampoline)")
        # Use --64 for ELF64 format. The .code32/.code64 directives handle instruction encoding.
        run(["as", "--64", "-o", str(boot_obj), str(boot_asm)])
    else:
        boot_obj = None
        print("  Warning: boot.s not found, no Multiboot2 header")

    # Step 3b: Assemble isr_stubs.s (ISR/IRQ handlers)
    isr_asm = KERNEL_DIR / "isr_stubs.s"
    isr_obj = BUILD_DIR / "kernel" / "isr_stubs.o"
    if isr_asm.exists():
        print("  Assembling isr_stubs.s (exception/IRQ handlers)")
        run(["as", "--64", "-o", str(isr_obj), str(isr_asm)])
    else:
        isr_obj = None
        print("  Warning: isr_stubs.s not found, no exception handling")

    # Step 3c: Assemble ap_trampoline.s (AP bootstrap code)
    ap_asm = KERNEL_DIR / "ap_trampoline.s"
    ap_obj = BUILD_DIR / "kernel" / "ap_trampoline.o"
    if ap_asm.exists():
        print("  Assembling ap_trampoline.s (AP bootstrap trampoline)")
        run(["as", "--64", "-o", str(ap_obj), str(ap_asm)])
    else:
        ap_obj = None
        print("  Warning: ap_trampoline.s not found, no SMP support")

    # Step 3d: Assemble context_switch.s (scheduler context switch)
    ctx_asm = KERNEL_DIR / "context_switch.s"
    ctx_obj = BUILD_DIR / "kernel" / "context_switch.o"
    if ctx_asm.exists():
        print("  Assembling context_switch.s (scheduler context switch)")
        run(["as", "--64", "-o", str(ctx_obj), str(ctx_asm)])
    else:
        ctx_obj = None
        print("  Warning: context_switch.s not found, no scheduler support")

    # Step 3e: Assemble syscall_entry.s (syscall entry/exit)
    syscall_asm = KERNEL_DIR / "syscall_entry.s"
    syscall_obj = BUILD_DIR / "kernel" / "syscall_entry.o"
    if syscall_asm.exists():
        print("  Assembling syscall_entry.s (syscall entry/exit)")
        run(["as", "--64", "-o", str(syscall_obj), str(syscall_asm)])
    else:
        syscall_obj = None
        print("  Warning: syscall_entry.s not found, no syscall support")

    # Step 3f: Assemble user_program.s (first userspace program)
    user_asm = KERNEL_DIR / "user_program.s"
    user_obj = BUILD_DIR / "kernel" / "user_program.o"
    if user_asm.exists():
        print("  Assembling user_program.s (userspace test program)")
        run(["as", "--64", "-o", str(user_obj), str(user_asm)])
    else:
        user_obj = None
        print("  Warning: user_program.s not found")

    # Step 3g: Assemble user_elf.s (embedded ELF binary for ELF loader test)
    user_elf_asm = KERNEL_DIR / "user_elf.s"
    user_elf_stub_asm = KERNEL_DIR / "user_elf_stub.s"
    user_elf_obj = BUILD_DIR / "kernel" / "user_elf.o"
    if user_elf_asm.exists():
        # Check if the ELF binary exists first
        user_elf_bin = BUILD_DIR / "user" / "portable_getpid.elf"
        if user_elf_bin.exists():
            print("  Assembling user_elf.s (embedded Ritz ELF binary)")
            run(["as", "--64", "-o", str(user_elf_obj), str(user_elf_asm)])
        elif user_elf_stub_asm.exists():
            # Use stub to provide symbols for linking
            print("  Assembling user_elf_stub.s (stub for linking)")
            run(["as", "--64", "-o", str(user_elf_obj), str(user_elf_stub_asm)])
        else:
            user_elf_obj = None
            print("  Skipping user_elf.s (no build/user/portable_getpid.elf)")
    else:
        user_elf_obj = None

    # Step 4: Link
    print("  Linking kernel...")
    import shutil
    if shutil.which(LLD) or shutil.which("ld.lld"):
        linker = LLD if shutil.which(LLD) else "ld.lld"
    else:
        linker = "ld"
        print("  Warning: lld not found, using ld")

    # Choose linker script
    boot32_asm = KERNEL_DIR / "boot32.s"
    if boot32_asm.exists() and flat:
        linker_script = KERNEL_DIR / "linker32.ld"
        print("  Using 32-bit multiboot linker (QEMU compatible)")
    elif flat:
        linker_script = KERNEL_DIR / "linker_flat.ld"
        print("  Using flat memory model (symbols at physical addresses)")
    else:
        linker_script = KERNEL_DIR / "linker.ld"
        print("  Using TRUE higher-half memory model (symbols at virtual addresses)")

    link_objs = []
    if boot_obj and boot_obj.exists():
        link_objs.append(str(boot_obj))
    if isr_obj and isr_obj.exists():
        link_objs.append(str(isr_obj))
    if ap_obj and ap_obj.exists():
        link_objs.append(str(ap_obj))
    if ctx_obj and ctx_obj.exists():
        link_objs.append(str(ctx_obj))
    if syscall_obj and syscall_obj.exists():
        link_objs.append(str(syscall_obj))
    if user_obj and user_obj.exists():
        link_objs.append(str(user_obj))
    if user_elf_obj and user_elf_obj.exists():
        link_objs.append(str(user_elf_obj))
    # Add all compiled Ritz objects
    for obj in ritz_objects:
        link_objs.append(str(obj))

    run([
        linker,
        "-T", str(linker_script),
        "-o", str(KERNEL_ELF),
        *link_objs,
    ], check=False)

    if KERNEL_ELF.exists():
        print(f"  Kernel built: {KERNEL_ELF}")
        run(["file", str(KERNEL_ELF)], check=False)
        return True
    else:
        print("  Linking failed")
        return False


def build_kernel_stub():
    """Build the stub kernel (fallback using external assembly stubs)."""
    print("\n=== Building Stub Kernel (Fallback) ===")
    ensure_dirs()

    stub_dir = KERNEL_DIR / "stub"
    ritz_src = stub_dir / "main.ritz"
    asm_src = stub_dir / "asm_stubs.s"

    if not ritz_src.exists():
        print(f"Error: Stub kernel not found at {ritz_src}")
        return False

    ritz = find_ritz_compiler()

    # Step 1: Compile Ritz source to LLVM IR
    ll_path = BUILD_DIR / "kernel" / "stub_main.ll"
    ll_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"  Compiling stub/main.ritz")
    result = run([
        str(ritz), "compile", str(ritz_src),
        "--no-runtime",
        "-o", str(ll_path)
    ], check=False)

    if result.returncode != 0:
        print("  Ritz compilation failed")
        return False

    # Step 2: Compile LLVM IR to object file
    ritz_obj = BUILD_DIR / "kernel" / "stub_main.o"
    print("  Compiling LLVM IR to object")
    run([LLC, "-filetype=obj", "-mtriple=x86_64-none-elf",
         "-relocation-model=pic",
         str(ll_path), "-o", str(ritz_obj)])

    # Step 3: Assemble the ASM stubs
    asm_obj = BUILD_DIR / "kernel" / "asm_stubs.o"
    if asm_src.exists():
        print("  Assembling asm_stubs.s")
        run(["as", "-o", str(asm_obj), str(asm_src)])
    else:
        print("  Warning: asm_stubs.s not found")
        asm_obj = None

    # Step 4: Link everything
    print("  Linking kernel...")
    import shutil
    linker = LLD if shutil.which(LLD) else "ld"

    link_cmd = [linker, "-T", str(KERNEL_DIR / "linker.ld"),
                "-o", str(KERNEL_ELF), str(ritz_obj)]
    if asm_obj and asm_obj.exists():
        link_cmd.append(str(asm_obj))

    run(link_cmd, check=False)

    if KERNEL_ELF.exists():
        print(f"  Kernel built: {KERNEL_ELF}")
        run(["file", str(KERNEL_ELF)], check=False)
        return True
    return False


def build_kernel():
    """Build the kernel ELF."""
    print("\n=== Building Kernel ===")
    ensure_dirs()

    # Try native kernel first (with inline asm)
    native_main = KERNEL_DIR / "src" / "main.ritz"
    if native_main.exists():
        if build_kernel_native():
            return
        print("  Native build failed, trying stub fallback...")

    # Fallback to stub kernel (external assembly stubs)
    stub_dir = KERNEL_DIR / "stub"
    if stub_dir.exists():
        if build_kernel_stub():
            return
        print("  Stub build also failed, creating placeholder...")

    # Last resort: placeholder ELF
    create_placeholder_elf(KERNEL_ELF)


def build_bootloader():
    """Build the UEFI bootloader."""
    print("\n=== Building Bootloader ===")
    ensure_dirs()

    ritz = find_ritz_compiler()

    boot_sources = list(BOOT_DIR.glob("**/*.ritz"))
    if not boot_sources:
        print("Error: No bootloader sources found")
        sys.exit(1)

    print(f"Found {len(boot_sources)} bootloader source files")

    # Similar process to kernel but with UEFI target
    ll_files = []
    for src in boot_sources:
        rel_path = src.relative_to(BOOT_DIR)
        ll_path = BUILD_DIR / "boot" / rel_path.with_suffix(".ll")
        ll_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  Compiling {rel_path}")
        result = run([
            str(ritz), "build", str(src),
            "--emit-llvm",
            "-o", str(ll_path)
        ], check=False)

        if result.returncode != 0:
            print(f"  Warning: Failed to compile {src}")
            continue

        ll_files.append(ll_path)

    if not ll_files:
        print("Error: No files compiled successfully")
        print("Note: The bootloader uses features not yet in ritz")
        print("      Creating placeholder EFI for testing build pipeline...")
        create_placeholder_efi(BOOTLOADER_EFI)
        return

    # Link for UEFI
    print("  Linking bootloader...")
    obj_files = []
    for ll in ll_files:
        obj = ll.with_suffix(".o")
        run(["llc", "-filetype=obj", "-mtriple=x86_64-unknown-windows", str(ll), "-o", str(obj)])
        obj_files.append(obj)

    run([
        "lld-link",
        "/subsystem:efi_application",
        "/entry:efi_main",
        f"/out:{BOOTLOADER_EFI}",
        *[str(o) for o in obj_files]
    ])

    print(f"  Bootloader built: {BOOTLOADER_EFI}")


def create_placeholder_elf(path: Path):
    """Create a minimal placeholder ELF for testing the build pipeline."""
    # Minimal x86-64 ELF that just halts
    # This lets us test the image creation and QEMU boot
    asm_code = """
    .section .text
    .global kernel_main
    kernel_main:
        cli
    .loop:
        hlt
        jmp .loop
    """

    asm_path = BUILD_DIR / "placeholder.s"
    obj_path = BUILD_DIR / "placeholder.o"

    asm_path.write_text(asm_code)
    run(["as", "-o", str(obj_path), str(asm_path)])

    # Try lld first, then fall back to ld
    import shutil
    linked = False
    if shutil.which(LLD):
        result = run([LLD, "-T", str(KERNEL_DIR / "linker.ld"), "-o", str(path), str(obj_path)], check=False)
        linked = result.returncode == 0

    # If linker fails or lld not found, create with just ld
    if not linked and not path.exists():
        run(["ld", "-o", str(path), "-e", "kernel_main", str(obj_path)])


def create_placeholder_efi(path: Path):
    """Create a minimal placeholder UEFI application."""
    # For now, just touch the file - proper UEFI stub needs more work
    # TODO: Create minimal UEFI stub that prints and halts
    print(f"  Creating placeholder: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create minimal PE file header (not functional, just for testing)
    # A real UEFI app needs proper PE/COFF structure
    path.write_bytes(b"MZ" + b"\x00" * 510)  # Minimal DOS stub
    print(f"  Warning: Placeholder EFI is not functional")


def build_userspace():
    """Build userspace programs."""
    print("\n=== Building Userspace Programs ===")
    ensure_dirs()
    (BUILD_DIR / "user").mkdir(exist_ok=True)

    ritz = find_ritz_compiler()

    # Find all userspace programs (directories under user/)
    if not USER_DIR.exists():
        print("  No user/ directory found")
        return True

    programs = [d for d in USER_DIR.iterdir() if d.is_dir() and (d / "src" / "main.ritz").exists()]

    if not programs:
        print("  No userspace programs found")
        return True

    success = True
    for prog_dir in programs:
        prog_name = prog_dir.name
        src_file = prog_dir / "src" / "main.ritz"
        out_dir = BUILD_DIR / "user" / prog_name
        out_dir.mkdir(parents=True, exist_ok=True)

        ll_path = out_dir / "main.ll"
        obj_path = out_dir / "main.o"
        elf_path = BUILD_DIR / "user" / f"{prog_name}.elf"

        print(f"  Building {prog_name}...")

        # Step 1: Compile Ritz to LLVM IR
        # Userspace programs need --no-runtime (we provide our own syscall wrappers)
        result = run([
            str(ritz), "compile", str(src_file),
            "--no-runtime",
            "-o", str(ll_path)
        ], check=False, env={"RITZ_PATH": str(prog_dir / "src")})

        if result.returncode != 0:
            print(f"    Ritz compilation failed for {prog_name}")
            success = False
            continue

        # Step 2: Compile LLVM IR to object file
        # Use static relocation model for simple userspace programs
        run([LLC, "-filetype=obj", "-mtriple=x86_64-none-elf",
             "-relocation-model=static",
             str(ll_path), "-o", str(obj_path)])

        # Step 3: Link into a position-independent ELF
        # We use a simple linker script for userspace
        user_linker_script = USER_DIR / "user.ld"
        if not user_linker_script.exists():
            # Create a simple userspace linker script
            user_linker_script.write_text("""/* Harland userspace linker script */
ENTRY(main)

SECTIONS {
    . = 0x400000;  /* Standard userspace base address */

    .text : {
        *(.text*)
    }

    .rodata : {
        *(.rodata*)
    }

    .data : {
        *(.data*)
    }

    .bss : {
        *(.bss*)
        *(COMMON)
    }

    /DISCARD/ : {
        *(.comment)
        *(.note*)
    }
}
""")

        import shutil
        linker = LLD if shutil.which(LLD) else "ld"
        run([
            linker,
            "-T", str(user_linker_script),
            "-o", str(elf_path),
            str(obj_path),
        ], check=False)

        if elf_path.exists():
            print(f"    Built: {elf_path}")
            run(["file", str(elf_path)], check=False)
        else:
            print(f"    Linking failed for {prog_name}")
            success = False

    return success


def build_image():
    """Build the qcow2 disk image."""
    print("\n=== Building Disk Image ===")
    ensure_dirs()

    # Ensure kernel and bootloader exist
    if not KERNEL_ELF.exists():
        print("Building kernel first...")
        build_kernel()

    if not BOOTLOADER_EFI.exists():
        print("Building bootloader first...")
        build_bootloader()

    # Run mkimage.py
    run([
        "python3", str(TOOLS_DIR / "mkimage.py"),
        "--kernel", str(KERNEL_ELF),
        "--bootloader", str(BOOTLOADER_EFI),
        "--output", str(IMAGE_QCOW2)
    ])


def cmd_build(args):
    """Handle build command."""
    target = args.target if hasattr(args, 'target') else 'all'

    if target == 'kernel' or target == 'all':
        build_kernel()

    if target == 'user' or target == 'all':
        build_userspace()

    if target == 'boot' or target == 'all':
        build_bootloader()

    if target == 'image' or target == 'all':
        build_image()


def cmd_run(args):
    """Run kernel in QEMU."""
    ensure_dirs()

    if not IMAGE_QCOW2.exists():
        print("Image not found, building...")
        build_image()

    # Create initramfs disk if it doesn't exist (for drivers, modules)
    if not INITRAMFS_QCOW2.exists():
        print("Creating initramfs disk (64MB)...")
        subprocess.run([
            "qemu-img", "create", "-f", "qcow2",
            str(INITRAMFS_QCOW2), "64M"
        ], check=True)

    # Create storage disk if it doesn't exist (general purpose)
    if not STORAGE_QCOW2.exists():
        print("Creating storage disk (512MB)...")
        subprocess.run([
            "qemu-img", "create", "-f", "qcow2",
            str(STORAGE_QCOW2), "512M"
        ], check=True)

    # Copy OVMF vars if needed
    if not OVMF_VARS.exists() and OVMF_VARS_TEMPLATE.exists():
        import shutil
        shutil.copy(OVMF_VARS_TEMPLATE, OVMF_VARS)

    if not OVMF_CODE.exists():
        print(f"Error: OVMF not found at {OVMF_CODE}")
        print("Install with: sudo apt install ovmf")
        sys.exit(1)

    qemu_args = [
        "qemu-system-x86_64",
        "-drive", f"if=pflash,format=raw,file={OVMF_CODE},readonly=on",
        "-drive", f"if=pflash,format=raw,file={OVMF_VARS}",
        "-drive", f"file={IMAGE_QCOW2},format=qcow2",
        # VirtIO block devices for initramfs and storage
        "-device", "virtio-blk-pci,drive=initramfs",
        "-drive", f"file={INITRAMFS_QCOW2},format=qcow2,if=none,id=initramfs",
        "-device", "virtio-blk-pci,drive=storage",
        "-drive", f"file={STORAGE_QCOW2},format=qcow2,if=none,id=storage",
        "-m", "4G",
        "-smp", "4",
        "-serial", "mon:stdio",
        "-no-reboot",
    ]

    if args.debug:
        qemu_args.extend(["-d", "int,cpu_reset", "-S", "-s"])
        print("GDB server listening on :1234")

    run(qemu_args, check=False)


def cmd_test(args):
    """Run tests."""
    print("\n=== Running Tests ===")

    # TODO: Run unit tests
    print("Unit tests: TODO")

    # TODO: Run QEMU integration tests
    print("Integration tests: TODO")


def cmd_clean(args):
    """Clean build artifacts."""
    import shutil

    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print(f"Removed {BUILD_DIR}")

    # Clean generated files in source dirs
    for pattern in ["**/*.ll", "**/*.o"]:
        for f in PROJECT_ROOT.glob(pattern):
            if "ritz" not in str(f):  # Don't touch submodule
                f.unlink()
                print(f"Removed {f}")


def main():
    parser = argparse.ArgumentParser(description="Harland Build System")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build components")
    build_parser.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=["kernel", "user", "boot", "image", "all"],
        help="What to build"
    )
    build_parser.set_defaults(func=cmd_build)

    # Run command
    run_parser = subparsers.add_parser("run", help="Run in QEMU")
    run_parser.add_argument("--debug", "-d", action="store_true", help="Enable GDB server")
    run_parser.set_defaults(func=cmd_run)

    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.set_defaults(func=cmd_test)

    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean build artifacts")
    clean_parser.set_defaults(func=cmd_clean)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
