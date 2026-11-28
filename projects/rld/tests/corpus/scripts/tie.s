# .ldata is an orphan whose rank shares as many leading bits with .bss's as
# with .data's: ld.lld takes the later anchor whose rank is no greater
# than its own (.data), not the first (.bss); .rodata between them is
# farther from both.
    .globl _start
    .text
_start:
    ret
    .section .rodata,"a"
    .byte 3
    .data
    .quad 1
    .bss
    .zero 8
    .section .ldata,"awl",@progbits
    .quad 2
