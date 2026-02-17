/* PIE User program linker script for Harland */
/* Position-Independent Executable - can be loaded at any address */

OUTPUT_FORMAT("elf64-x86-64")
OUTPUT_ARCH(i386:x86-64)
ENTRY(main)

SECTIONS
{
    /* PIE: Base address will be determined at load time by the kernel */
    /* We use 0 here as a placeholder - the kernel will relocate to actual address */
    . = 0;

    /* ELF header and program headers */
    .text : {
        *(.text .text.*)
    }

    .rodata : {
        *(.rodata .rodata.*)
    }

    /* GOT and PLT for PIC code */
    .got : {
        *(.got)
    }

    .got.plt : {
        *(.got.plt)
    }

    /* Dynamic relocations (needed for PIE) */
    .rela.dyn : {
        *(.rela.dyn)
    }

    .rela.plt : {
        *(.rela.plt)
    }

    .data : {
        *(.data .data.*)
    }

    .bss : {
        *(.bss .bss.*)
        *(COMMON)
    }

    /* Discard unneeded sections */
    /DISCARD/ : {
        *(.comment)
        *(.note*)
        *(.eh_frame*)
    }
}
