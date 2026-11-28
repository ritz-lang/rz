# A program for the script tests: one input section for each placement rule
# the scripts exercise.
#   .text.entry   claimed before .text by carry.ld's first pattern
#   .rodata.str   matched by a trailing-`*` pattern
#   .mydata       an orphan under every script (writable, PROGBITS)
#   .bss          NOBITS, after the data
    .section .text.entry,"ax"
    .globl _start, main
_start:
main:
    movl $60, %eax
    leaq marker(%rip), %rdi
    syscall

    .text
    ret

    .section .rodata.str,"a"
msg:
    .ascii "hi"

    .data
marker:
    .quad _start

    .section .mydata,"aw"
    .quad 7

    .bss
    .zero 64
