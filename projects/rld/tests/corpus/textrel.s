# A pointer in read-only data: a PIE would need a text relocation, which
# ld.lld refuses and rld refuses too.
    .text
    .global _start
_start:
    ret
    .section .rodata
    .p2align 3
ptr:
    .quad x
    .data
    .global x
x:
    .quad 0
