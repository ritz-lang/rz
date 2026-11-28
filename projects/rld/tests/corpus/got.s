# Every GOT load ld.lld relaxes, and the ones it keeps, in a program that
# checks what each loaded. Linked with got_norelax.s (assembled with
# -mrelax-relocations=no, so its loads are plain R_X86_64_GOTPCREL) and run:
# the exit status is 0 when every check holds, else the first failing
# check's number. stdout is the values, in hex.
    .text
    .global _start
    .type _start, @function
_start:
    xorl %r12d, %r12d

    movq value@GOTPCREL(%rip), %rax         # REX mov -> lea
    movl $1, %r12d
    cmpq $0x1234, (%rax)
    jne fail

    movl value@GOTPCREL(%rip), %ecx         # mov, no REX -> lea
    movl $2, %r12d
    cmpq $0x1234, (%rcx)
    jne fail

    leaq value(%rip), %rdx                  # test -> test $value
    movl $3, %r12d
    movq %rdx, %rsi
    testq %rsi, value@GOTPCREL(%rip)
    je fail

    movq %rdx, %r8                          # binops through REX.R -> REX.B
    movl $4, %r12d
    subq value@GOTPCREL(%rip), %r8
    jne fail
    movl $5, %r12d
    cmpq value@GOTPCREL(%rip), %rdx
    jne fail
    xorq %r11, %r11
    addq value@GOTPCREL(%rip), %r11
    movl $6, %r12d
    cmpq %rdx, %r11
    jne fail

    movl $7, %r12d                          # binop, no REX: through the GOT
    xorl %eax, %eax
    addl value@GOTPCREL(%rip), %eax
    cmpl %edx, %eax
    jne fail

    movl $8, %r12d                          # addend not -4: through the GOT
    movl value@GOTPCREL+4(%rip), %eax
    movq %rdx, %rcx
    shrq $32, %rcx
    cmpl %ecx, %eax
    jne fail

    call *add_one@GOTPCREL(%rip)            # call -> addr32 call
    movl $9, %r12d
    cmpq $0x1235, %rax
    jne fail

    call norelax_value                      # plain GOTPCREL: through the GOT
    movl $10, %r12d
    cmpq $0x1234, %rax
    jne fail

    movq value@GOTPCREL(%rip), %rdi
    movq (%rdi), %rdi
    call put_hex
    jmp *finish@GOTPCREL(%rip)              # jmp -> jmp; nop

fail:
    movl %r12d, %edi
    movl $60, %eax
    syscall

    .type add_one, @function
add_one:
    movq value(%rip), %rax
    incq %rax
    ret

    .type finish, @function
finish:
    xorl %edi, %edi
    movl $60, %eax
    syscall

# put_hex(v): v as 16 hex digits and a newline on stdout
    .type put_hex, @function
put_hex:
    subq $40, %rsp
    movb $10, 16(%rsp)
    movq $16, %rcx
1:
    movq %rdi, %rax
    andq $15, %rax
    addq $48, %rax
    cmpq $58, %rax
    jb 2f
    addq $39, %rax
2:
    decq %rcx
    movb %al, (%rsp,%rcx)
    shrq $4, %rdi
    testq %rcx, %rcx
    jnz 1b
    movq %rsp, %rsi
    movq $17, %rdx
    movq $1, %rdi
    movq $1, %rax
    syscall
    addq $40, %rsp
    ret

    .data
    .global value
    .type value, @object
    .p2align 3
value:
    .quad 0x1234
