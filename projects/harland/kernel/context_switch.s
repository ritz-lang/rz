# Context Switch Assembly (x86_64)
#
# void context_switch(CpuContext* old, CpuContext* new)
#
# CpuContext layout (must match Ritz struct):
#   0x00: rbx
#   0x08: rbp
#   0x10: r12
#   0x18: r13
#   0x20: r14
#   0x28: r15
#   0x30: rsp
#   0x38: rip (return address)
#   0x40: rflags

.section .text
.global context_switch
.type context_switch, @function

context_switch:
    # Arguments:
    #   %rdi = old context pointer
    #   %rsi = new context pointer

    # Save callee-saved registers to old context
    movq %rbx, 0x00(%rdi)
    movq %rbp, 0x08(%rdi)
    movq %r12, 0x10(%rdi)
    movq %r13, 0x18(%rdi)
    movq %r14, 0x20(%rdi)
    movq %r15, 0x28(%rdi)

    # Save stack pointer
    movq %rsp, 0x30(%rdi)

    # Save return address (from stack - pushed by 'call' instruction)
    # The return address is at (%rsp) after the call
    # But we're called so it's at 0(%rsp) right now
    # Actually, we save the address of the instruction after context_switch returns
    leaq .Lreturn(%rip), %rax
    movq %rax, 0x38(%rdi)

    # Save flags
    pushfq
    popq %rax
    movq %rax, 0x40(%rdi)

    # Restore callee-saved registers from new context
    movq 0x00(%rsi), %rbx
    movq 0x08(%rsi), %rbp
    movq 0x10(%rsi), %r12
    movq 0x18(%rsi), %r13
    movq 0x20(%rsi), %r14
    movq 0x28(%rsi), %r15

    # Restore flags
    movq 0x40(%rsi), %rax
    pushq %rax
    popfq

    # Restore stack pointer
    movq 0x30(%rsi), %rsp

    # Jump to new task's instruction pointer
    movq 0x38(%rsi), %rax
    jmpq *%rax

.Lreturn:
    # This is where we return when switched back to
    ret

.size context_switch, . - context_switch
