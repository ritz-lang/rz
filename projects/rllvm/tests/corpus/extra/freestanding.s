# The freestanding entries' one razm object: a function and data the Ritz
# sources reference from outside, and the stack protector's guard and
# failure hook for the kernel entry. Assembled with `as --64` until razm
# assembles it.
    .text

# rt_tick(n): n + 1
    .global rt_tick
    .type rt_tick, @function
rt_tick:
    movq %rdi, %rax
    addq $1, %rax
    ret

    .global __stack_chk_fail
    .type __stack_chk_fail, @function
__stack_chk_fail:
    cli
1:
    hlt
    jmp 1b

    .global ritz_platform_fatal
    .type ritz_platform_fatal, @function
ritz_platform_fatal:
    jmp __stack_chk_fail

    .data
    .align 8
    .global rt_ticks
rt_ticks:
    .quad 0
    .global __stack_chk_guard
__stack_chk_guard:
    .quad 0x2f8a9b7c6d5e4f30
