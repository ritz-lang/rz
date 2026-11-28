# The load-time relocations a PIE needs (../../../razm/DESIGN.md "Outputs"):
# initialized pointers in writable data, and a GOT entry that survives
# relaxation. Linked as a PIE and run at whatever base the loader picks:
# the exit status is 0 when every pointer holds its loaded address, else
# the first failing check's number.
    .text
    .global _start
    .type _start, @function
_start:
    leaq x(%rip), %rcx

    movl $1, %edi                       # tab: R_X86_64_64 against x
    cmpq %rcx, tab(%rip)
    jne 1f

    movl $2, %edi                       # tab + 8: against x + 8
    leaq 8(%rcx), %rdx
    cmpq %rdx, tab+8(%rip)
    jne 1f

    movl $3, %edi                       # a binop's GOT load stays in a PIE
    cmpq x@GOTPCREL(%rip), %rcx
    jne 1f

    movl $4, %edi                       # an addend not -4 stays too
    movl x@GOTPCREL+4(%rip), %eax
    movq %rcx, %rdx
    shrq $32, %rdx
    cmpl %edx, %eax
    jne 1f

    movl $5, %edi                       # a mov relaxes to lea
    movq x@GOTPCREL(%rip), %rax
    cmpq %rcx, %rax
    jne 1f

    movl $6, %edi                       # pie_abs.s's absolute symbol is not relocated
    cmpq $0x1234, abs_ptr(%rip)
    jne 1f

    xorl %edi, %edi
1:
    movl $60, %eax
    syscall

    .data
    .p2align 3
x:
    .quad 7
    .quad 8
tab:
    .quad x
    .quad x + 8
abs_ptr:
    .quad fixed
