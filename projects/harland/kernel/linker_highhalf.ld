/*
 * Harland Kernel Linker Script (Higher-Half)
 *
 * Produces ELF64 kernel for GRUB's multiboot2 protocol.
 *
 * Memory layout:
 *   Physical 0x100000:           Multiboot header, boot code
 *   Physical 0x102000+:          Kernel code/data (loaded here)
 *   Virtual 0xFFFFFFFF80102000+: Kernel code/data (runs here)
 *
 * GRUB loads the entire kernel at 1MB physical.
 * Boot code sets up page tables that map:
 *   - Identity: 0x0 - 0x40000000 -> 0x0 - 0x40000000 (first 1GB)
 *   - Higher-half: 0xFFFFFFFF80000000 -> 0x0 (first 1GB at high addresses)
 *
 * After paging is enabled, boot code jumps to kernel_main using
 * the higher-half virtual address.
 */

OUTPUT_FORMAT(elf64-x86-64)
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start)

/* Memory base addresses */
KERNEL_PHYS_BASE = 0x100000;              /* 1MB physical */
KERNEL_VIRT_BASE = 0xFFFFFFFF80000000;    /* Higher-half base */

SECTIONS
{
    /* ================================================================
     * BOOT SECTION - Physical/identity-mapped addresses
     * This code runs before paging is fully configured
     * VMA = LMA for boot code (identity mapped)
     * ================================================================ */
    . = KERNEL_PHYS_BASE;

    /* Multiboot header - must be in first 32KB of file, 4-byte aligned */
    .multiboot ALIGN(4) :
    {
        KEEP(*(.multiboot))
    }

    /* AP trampoline - copied to low memory at runtime */
    .ap_trampoline ALIGN(16) :
    {
        *(.ap_trampoline)
    }

    /* Boot code - identity mapped, runs at physical addresses */
    /* Placed in .text but will be early in file */
    /* Note: boot.s code is intermixed with kernel code in .text */

    /* All code - both boot and kernel */
    /* VMA is still physical here since boot code needs to run first */
    .text ALIGN(4K) :
    {
        *(.text .text.*)
    }

    /* Read-only data */
    .rodata ALIGN(4K) :
    {
        *(.rodata .rodata.*)
    }

    /* Initialized data (includes GDT, strings) */
    .data ALIGN(4K) :
    {
        *(.data .data.*)
    }

    /* Uninitialized data (page tables, stack, BSS) */
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

/* Provide symbols for kernel code */
PROVIDE(__kernel_phys_base = KERNEL_PHYS_BASE);
PROVIDE(__kernel_virt_base = KERNEL_VIRT_BASE);

/*
 * Note: This linker script keeps everything at physical addresses.
 * The boot code adds KERNEL_VIRT_BASE to addresses when jumping to
 * higher-half. The kernel code can use __kernel_virt_base to calculate
 * virtual addresses from physical addresses.
 *
 * For a true higher-half kernel where symbols are at virtual addresses,
 * we'd need to split boot code into a separate section with different VMA.
 * That's a more complex setup - this is a simpler incremental step.
 */
