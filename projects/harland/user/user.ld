/* Harland userspace linker script */
ENTRY(main)

SECTIONS {
    /* User base address at 1GB to avoid kernel's identity-mapped region.
     * The kernel identity maps 0-1GB with 2MB huge pages, so user programs
     * must be loaded above that to allow 4KB page granularity. */
    . = 0x40000000;  /* 1GB - above identity-mapped region */

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
