/* .rela.dyn among .data's PROGBITS: ld.lld makes .rela.dyn for every
   link, an executable's too, and refuses it there (test_rld.py). */
ENTRY(_start)
SECTIONS
{
    .text : { *(.text .text.*) }
    .data : { *(.data .data.*) *(.rela.dyn) }
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
