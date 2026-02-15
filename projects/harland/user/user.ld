/* Harland userspace linker script */
ENTRY(main)

SECTIONS {
    . = 0x400000;  /* Standard userspace base address */

    .text : {
        *(.text*)
    }

    .rodata : {
        *(.rodata*)
    }

    .data : {
        *(.data*)
    }

    .bss : {
        *(.bss*)
        *(COMMON)
    }

    /DISCARD/ : {
        *(.comment)
        *(.note*)
    }
}
