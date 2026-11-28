/* .bss, then .rodata, then .data: the two anchors .ldata ties between
 * are apart. */
ENTRY(_start)
SECTIONS
{
    . = 0x400000;
    .text : { *(.text) }
    .bss : { *(.bss) }
    .rodata : { *(.rodata) }
    .data : { *(.data) }
}
