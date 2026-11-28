/* The GOT and .got.plt inside .data, after its object sections, so each
   sits at an offset in its output section; the dynamic-linking sections
   are orphans (test_rld.py's scripted PIE tests). */
ENTRY(_start)
SECTIONS
{
    . = 0x10000;
    .text : { *(.text .text.*) }
    .rodata : { *(.rodata .rodata.*) }
    .data : { *(.data .data.*) *(.got) *(.got.plt) }
    .bss : { *(.bss .bss.*) }
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
