#!/bin/bash
# Build the Harland UEFI bootloader
#
# Produces: boot/build/harland_boot.efi
#
# Uses clang + lld-link for proper PE/COFF creation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create build directory
mkdir -p build

echo "=== Building Harland UEFI Bootloader ==="

# Step 1: Compile Ritz code to LLVM IR
echo "  [1/5] Compiling Ritz code..."
python3 ../ritz/ritz0/ritz0.py \
    --no-runtime \
    --target x86_64-none-elf \
    -o build/main.ll \
    src/main.ritz

# Step 2: Compile LLVM IR to Windows/UEFI COFF object
echo "  [2/5] Compiling to COFF object..."
clang-20 --target=x86_64-unknown-windows \
    -c -o build/main.o \
    -x ir build/main.ll

# Step 3: Assemble the UEFI entry point as COFF
echo "  [3/5] Assembling UEFI entry (COFF)..."
clang-20 --target=x86_64-unknown-windows \
    -c -o build/uefi_entry.o \
    uefi_entry.s

# Step 4: Link into PE using lld-link
echo "  [4/5] Linking PE/COFF with lld-link..."
lld-link \
    /entry:_start \
    /subsystem:efi_application \
    /out:build/harland_boot.efi \
    build/uefi_entry.o \
    build/main.o

echo ""
echo "=== Build Complete ==="
ls -la build/harland_boot.efi
file build/harland_boot.efi
echo ""
