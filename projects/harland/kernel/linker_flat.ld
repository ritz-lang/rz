/*
 * Harland Kernel Linker Script (Multiboot2)
 *
 * Produces ELF64 kernel for GRUB's multiboot2 protocol.
 * Contains 32-bit boot stub that transitions to 64-bit long mode.
 *
 * Memory layout (flat, starting at 1MB physical):
 * - 0x100000: Multiboot2 header (must be in first 32KB)
 * - 0x101000: .text (32-bit entry + 64-bit kernel)
 * - .rodata, .data, .bss follow
 *
 * Boot compatibility:
 * - GRUB with multiboot2
 * - AWS EC2 UEFI (uses separate bootloader)
 */

OUTPUT_FORMAT(elf64-x86-64)
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start)

SECTIONS
{
    /* Start at 1MB physical */
    . = 1M;

    /* Multiboot header - must be in first 8KB, 4-byte aligned */
    .multiboot ALIGN(4) :
    {
        KEEP(*(.multiboot))
    }

    /* AP trampoline code - must be relocatable to low memory */
    /* Note: This gets copied to 0x8000 at runtime by ap_setup_trampoline */
    .ap_trampoline ALIGN(16) :
    {
        *(.ap_trampoline)
    }

    /* All code (32-bit boot + 64-bit kernel) */
    .text ALIGN(4K) :
    {
        *(.text .text.*)
    }

    /* Read-only data */
    .rodata ALIGN(4K) :
    {
        *(.rodata .rodata.*)
    }

    /* Initialized data (includes GDT) */
    .data ALIGN(4K) :
    {
        *(.data .data.*)
    }

    /* Uninitialized data (page tables, stack) */
    .bss ALIGN(4K) :
    {
        __bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        __bss_end = .;
    }

    /* Kernel end marker */
    . = ALIGN(4K);
    __kernel_end = .;

    /* Discard unwanted sections */
    /DISCARD/ :
    {
        *(.eh_frame)
        *(.comment)
        *(.note.*)
    }
}
