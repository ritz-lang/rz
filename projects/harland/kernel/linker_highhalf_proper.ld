/*
 * Harland Kernel Linker Script - True Higher-Half
 * Target: x86-64 freestanding
 *
 * This linker script creates a proper higher-half kernel where:
 * - Boot code (.multiboot, .boot) has VMA = LMA at physical addresses
 * - Kernel code (.text, .rodata, .data, .bss) has VMA at higher-half
 *
 * Memory Layout (Physical):
 *   0x00100000  Multiboot header + boot code (identity-mapped)
 *   0x00102000  Kernel code (loaded here, runs from higher-half)
 *   0x001XXXXX  Kernel data, BSS, stack
 *
 * Memory Layout (Virtual):
 *   0x00000000_00100000  Boot code (identity map during boot)
 *   0xFFFFFFFF_80100000  Kernel start (higher-half)
 *   0xFFFFFFFF_80XXXXXX  Kernel heap, data, BSS
 *
 * The boot assembly (boot.s) runs at physical addresses before paging,
 * then jumps to higher-half after enabling paging.
 *
 * Key: Boot code symbols are at physical addresses.
 *      Kernel code symbols are at virtual (higher-half) addresses.
 */

OUTPUT_FORMAT(elf64-x86-64)
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start)

/* Memory base addresses */
KERNEL_PHYS_BASE = 0x100000;              /* 1MB physical */
KERNEL_VIRT_BASE = 0xFFFFFFFF80000000;    /* Higher-half base (-2GB) */

/* Boot code size (reserved for multiboot header + boot.s) */
BOOT_SIZE = 0x2000;                        /* 8KB for boot code */

SECTIONS
{
    /* ================================================================
     * BOOT SECTION - Runs at PHYSICAL addresses before paging
     * VMA = LMA (no relocation, identity-mapped during execution)
     * ================================================================ */
    . = KERNEL_PHYS_BASE;
    __boot_start = .;

    /* Multiboot2 header - must be in first 32KB, 8-byte aligned */
    .multiboot ALIGN(8) :
    {
        KEEP(*(.multiboot))
    }

    /* AP trampoline - needs to be copied to low memory at runtime */
    .ap_trampoline ALIGN(16) :
    {
        __ap_trampoline_start = .;
        *(.ap_trampoline)
        __ap_trampoline_end = .;
    }

    /* Boot code - 32-bit entry, page table setup, mode switch */
    /* This code runs before paging is enabled */
    .boot ALIGN(4K) :
    {
        *(.boot .boot.*)
    }

    /* Mark end of boot section */
    . = ALIGN(4K);
    __boot_end = .;

    /* ================================================================
     * KERNEL SECTION - Runs at VIRTUAL (higher-half) addresses
     * VMA = KERNEL_VIRT_BASE + physical_offset
     * LMA = physical_offset (where GRUB loads it)
     * ================================================================ */

    /* Calculate where kernel starts in physical memory */
    __kernel_phys_start = .;

    /* Switch to higher-half virtual addressing for kernel sections */
    /* The VMA is the virtual address, AT() specifies the LMA (load address) */
    . = KERNEL_VIRT_BASE + __kernel_phys_start;
    __kernel_start = .;

    /* Kernel code section */
    .text ALIGN(4K) : AT(__kernel_phys_start)
    {
        __text_start = .;
        *(.text .text.*)
        __text_end = .;
    }

    /* Read-only data */
    .rodata ALIGN(4K) : AT(ADDR(.rodata) - KERNEL_VIRT_BASE)
    {
        __rodata_start = .;
        *(.rodata .rodata.*)
        __rodata_end = .;
    }

    /* Global Offset Table (if PIC is used) */
    .got ALIGN(8) : AT(ADDR(.got) - KERNEL_VIRT_BASE)
    {
        *(.got .got.*)
    }

    /* Initialized data */
    .data ALIGN(4K) : AT(ADDR(.data) - KERNEL_VIRT_BASE)
    {
        __data_start = .;
        *(.data .data.*)
        __data_end = .;
    }

    /* Uninitialized data (BSS) - doesn't take space in file */
    .bss ALIGN(4K) : AT(ADDR(.bss) - KERNEL_VIRT_BASE)
    {
        __bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        __bss_end = .;
    }

    /* Kernel end marker */
    . = ALIGN(4K);
    __kernel_end = .;

    /* ================================================================
     * Discard unwanted sections
     * ================================================================ */
    /DISCARD/ :
    {
        *(.eh_frame)
        *(.comment)
        *(.note.*)
    }
}

/* ================================================================
 * Symbol Exports for Kernel Code
 * ================================================================ */

/* Physical addresses (for boot code and page table setup) */
PROVIDE(__kernel_phys_base = KERNEL_PHYS_BASE);
PROVIDE(__kernel_load_addr = __kernel_phys_start);

/* Virtual addresses (for kernel code) */
PROVIDE(__kernel_virt_base = KERNEL_VIRT_BASE);
PROVIDE(__kernel_size = __kernel_end - __kernel_start);

/* BSS info (for zeroing) */
PROVIDE(__bss_size = __bss_end - __bss_start);
