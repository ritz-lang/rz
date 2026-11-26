# The hosted entries' one razm object: output helpers for the Ritz sources.
# Assembled with `as --64` until razm assembles it.
    .text

# rt_write(buf, len): write(1, buf, len)
    .global rt_write
    .type rt_write, @function
rt_write:
    movq %rsi, %rdx
    movq %rdi, %rsi
    movq $1, %rdi
    movq $1, %rax
    syscall
    ret

# rt_hex(v): v as 16 hex digits and a newline on stdout
    .global rt_hex
    .type rt_hex, @function
rt_hex:
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
