# A 32-bit absolute address: no PIE can hold it, whatever its base.
    .text
    .global _start
_start:
    movq $x, %rax
    ret
    .data
    .global x
x:
    .quad 0
