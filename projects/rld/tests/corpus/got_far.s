# A GOT load of a symbol more than 2 GiB from it, past a large .bss: the
# relaxed lea would not reach, so the load keeps its GOT entry, as ld.lld
# keeps it. Exits 0 when the loaded address is `far`'s.
    .text
    .global _start
    .type _start, @function
_start:
    movq far@GOTPCREL(%rip), %rax
    leaq near(%rip), %rcx
    movabsq $0x90000000, %rdx
    addq %rdx, %rcx
    xorl %edi, %edi
    cmpq %rcx, %rax
    setne %dil
    movl $60, %eax
    syscall

    .bss
    .p2align 3
near:
    .zero 0x90000000
far:
    .quad 0
