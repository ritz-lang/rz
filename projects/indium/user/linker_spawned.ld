/* Linker script for spawned user programs in Harland */
/* Links at 8GB virtual address to avoid conflicts with init at 4GB */

OUTPUT_FORMAT("elf64-x86-64")
OUTPUT_ARCH(i386:x86-64)
ENTRY(main)

SECTIONS
{
    /* Start at 8GB - separate from init's address space at 4GB */
    . = 0x200000000;

    .text : {
        *(.text .text.*)
    }

    .rodata : {
        *(.rodata .rodata.*)
    }

    .data : {
        *(.data .data.*)
    }

    .bss : {
        *(.bss .bss.*)
    }
}
