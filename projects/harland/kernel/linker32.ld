/*
 * Harland Kernel Linker Script (32-bit Multiboot)
 *
 * Produces a 32-bit ELF that QEMU can load directly with -kernel.
 * Contains both 32-bit boot stub and 64-bit kernel code.
 *
 * The boot stub runs in 32-bit mode, sets up paging and long mode,
 * then jumps to the 64-bit kernel.
 */

OUTPUT_FORMAT(elf32-i386)
OUTPUT_ARCH(i386)
ENTRY(_start)

SECTIONS
{
    /* Start at 1MB physical */
    . = 1M;

    /* Multiboot header - must be in first 8KB */
    .multiboot ALIGN(4) :
    {
        KEEP(*(.multiboot))
    }

    /* All code */
    .text ALIGN(4K) :
    {
        *(.text .text.*)
    }

    /* Read-only data */
    .rodata ALIGN(4K) :
    {
        *(.rodata .rodata.*)
    }

    /* Initialized data */
    .data ALIGN(4K) :
    {
        *(.data .data.*)
    }

    /* Uninitialized data */
    .bss ALIGN(4K) :
    {
        __bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        __bss_end = .;
    }

    . = ALIGN(4K);
    __kernel_end = .;

    /DISCARD/ :
    {
        *(.eh_frame)
        *(.comment)
        *(.note.*)
    }
}
