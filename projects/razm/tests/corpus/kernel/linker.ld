/*
 * Harland Kernel Linker Script - True Higher-Half
 * Target: x86-64 freestanding
 *
 * This creates a proper higher-half kernel where:
 * - Boot code (.multiboot, .boot*) runs at PHYSICAL addresses
 * - Kernel code (.text, .rodata, .data, .bss) runs at VIRTUAL addresses
 *
 * Memory Layout (Physical):
 *   0x100000:  Multiboot header
 *   0x100xxx:  Boot code (32-bit entry, mode switch, serial init)
 *   0x10Xxxx:  Kernel code/data (loaded here by GRUB)
 *
 * Memory Layout (Virtual):
 *   0xFFFFFFFF80100000+:  Kernel code/data (runs here after paging)
 *
 * Key points:
 * - Boot sections have VMA = LMA (run where loaded)
 * - Kernel sections have VMA at higher-half, LMA at physical
 * - The transition happens in boot code after paging is enabled
 */

OUTPUT_FORMAT(elf64-x86-64)
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start)

/* Memory base addresses */
KERNEL_PHYS_BASE = 0x100000;              /* 1MB physical */
KERNEL_VIRT_BASE = 0xFFFFFFFF80000000;    /* Higher-half base (-2GB) */

SECTIONS
{
    /* ================================================================
     * BOOT SECTIONS - Physical addresses (VMA = LMA)
     * This code runs before paging is enabled
     * ================================================================ */
    . = KERNEL_PHYS_BASE;
    __boot_start = .;

    /* Multiboot header - must be in first 32KB, 8-byte aligned */
    .multiboot ALIGN(8) :
    {
        KEEP(*(.multiboot))
    }

    /* AP trampoline - copied to low memory at runtime */
    .ap_trampoline ALIGN(16) :
    {
        __ap_trampoline_start = .;
        *(.ap_trampoline)
        __ap_trampoline_end = .;
    }

    /* Boot code - 32-bit and 64-bit pre-kernel code */
    .boot ALIGN(4K) :
    {
        *(.boot .boot.*)
    }

    /* Boot data (GDT, strings, etc.) */
    .boot.data ALIGN(16) :
    {
        *(.boot.data)
    }

    /* Boot BSS (page tables, stacks) */
    .boot.bss ALIGN(4K) (NOLOAD) :
    {
        __boot_bss_start = .;
        *(.boot.bss)
        __boot_bss_end = .;
    }

    /* End of boot sections */
    . = ALIGN(4K);
    __boot_end = .;

    /* ================================================================
     * KERNEL SECTIONS - Higher-half virtual addresses
     * VMA = KERNEL_VIRT_BASE + physical_offset
     * LMA = physical_offset (where GRUB loads it)
     * ================================================================ */

    /* Remember physical location for AT() directives */
    __kernel_phys_start = .;

    /* Switch to higher-half virtual addressing */
    . = KERNEL_VIRT_BASE + __kernel_phys_start;
    __kernel_virt_start = .;

    /* Code section */
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

    /* Global Offset Table */
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

    /* Uninitialized data (BSS) */
    .bss ALIGN(4K) : AT(ADDR(.bss) - KERNEL_VIRT_BASE)
    {
        __bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        __bss_end = .;
    }

    /* Kernel end marker */
    . = ALIGN(4K);
    __kernel_virt_end = .;

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
 * Symbol Exports
 * ================================================================ */

/* Physical addresses for boot code */
PROVIDE(__kernel_phys_base = KERNEL_PHYS_BASE);
PROVIDE(__kernel_load_addr = __kernel_phys_start);
PROVIDE(__boot_size = __boot_end - __boot_start);

/* Virtual addresses for kernel code */
PROVIDE(__kernel_virt_base = KERNEL_VIRT_BASE);
PROVIDE(__kernel_start = __kernel_virt_start);
PROVIDE(__kernel_end = __kernel_virt_end);
PROVIDE(__kernel_size = __kernel_virt_end - __kernel_virt_start);

/* BSS info */
PROVIDE(__bss_size = __bss_end - __bss_start);
