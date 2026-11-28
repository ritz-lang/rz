# The kernel's C-side symbols the seven .s objects and kernel.ll reference.
    .text
    .globl syscall_handler, exception_handler, irq_handler, proc_reap_current
    .globl process_reap_exit, kernel_main, __stack_chk_fail, rt_tick
    .globl ritz_platform_fatal
syscall_handler:
exception_handler:
irq_handler:
proc_reap_current:
process_reap_exit:
kernel_main:
__stack_chk_fail:
rt_tick:
ritz_platform_fatal:
    ret

    .data
    .globl __stack_chk_guard, rt_ticks
    .p2align 3
__stack_chk_guard:
    .quad 0
rt_ticks:
    .quad 0
