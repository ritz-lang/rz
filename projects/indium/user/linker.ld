/* User program linker script for Harland */
/* Links at 4GB virtual address, above kernel's identity-mapped region */
/* Entry point is _start (provided by runtime) which calls main() and sys_exit() */

OUTPUT_FORMAT("elf64-x86-64")
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start)

SECTIONS
{
    /* Start at 4GB - well above the 1GB identity-mapped region */
    . = 0x100000000;

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
