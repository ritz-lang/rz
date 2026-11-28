/* AT carries its VMA-to-LMA offset forward to the sections after it,
 * patterns claim in statement order, NOLOAD makes NOBITS (of PROGBITS
 * input too), and a PROVIDE
 * defines only what an input references. */
ENTRY(_start)
SECTIONS
{
    . = 0x400000;
    .text : { *(.text.entry) *(.text .text.*) }
    .rodata ALIGN(4K) : AT(0x9000) { *(.rodata*) }
    .data : { *(.data) }
    .noload (NOLOAD) : { *(.mydata) }
    .bss (NOLOAD) : { *(.bss) }
    /DISCARD/ : { *(.eh_frame) }
}
PROVIDE(__provided_used = 0x1234);
PROVIDE(__provided_unused = 0x5678);
