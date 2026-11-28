/* .dynsym and .dynamic among sections of other types: ld.lld refuses
   both, "section type mismatch" (test_rld.py). */
ENTRY(_start)
SECTIONS
{
    .text : { *(.text .text.*) }
    .rodata : { *(.rodata .rodata.*) *(.dynsym) }
    .data : { *(.data .data.*) *(.dynamic) }
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
