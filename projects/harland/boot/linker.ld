/*
 * Harland UEFI Bootloader Linker Script
 *
 * Creates an ELF file that objcopy converts to PE/COFF for UEFI.
 */

OUTPUT_FORMAT(elf64-x86-64)
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start)

SECTIONS
{
    /* Start at 4KB to ensure entry point is non-zero */
    . = 0x1000;

    /* Code section */
    .text ALIGN(4K) : {
        *(.text .text.*)
    }

    /* Read-only data */
    .rodata ALIGN(4K) : {
        *(.rodata .rodata.*)
    }

    /* Initialized data */
    .data ALIGN(4K) : {
        *(.data .data.*)
    }

    /* BSS */
    .bss ALIGN(4K) : {
        __bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        __bss_end = .;
    }

    /DISCARD/ : {
        *(.eh_frame)
        *(.comment)
        *(.note.*)
    }
}
