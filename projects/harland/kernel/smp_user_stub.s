# The smp-user boot test's CPL-3 stub (AGAST #4881, kernel/src/syscall/runtime/smp_user.ritz)
#
# Position-independent: process_spawn_image_on copies it to USER_IMAGE_BASE
# of its own page table. RDI is the mode, RSI the bump count (MODE_COUNT).
# It asks where its local call and its forwarded call ran (OP_WHERE on
# SmpUserLocal and SmpUser), and in MODE_COUNT checks in (OP_ARRIVE), waits
# for the other process (OP_GO), then makes RSI forwarded and RSI local
# bumps, alternating. It exits with local_cpu | forwarded_cpu << 8.
# syscall_entry.s restores the callee-saved registers, so r12-r14 survive
# every syscall.

.equ SYS_EXIT,            20
.equ SYS_SMP_USER,        253
.equ SYS_SMP_USER_LOCAL,  252
.equ OP_ARRIVE,           1
.equ OP_GO,               2
.equ OP_BUMP,             3
.equ OP_WHERE,            4
.equ MODE_COUNT,          1

.section .text
.global smp_user_stub_start
.type smp_user_stub_start, @function
smp_user_stub_start:
    movq %rdi, %r12              # mode
    movq %rsi, %r13              # bumps of each kind
    movl $SYS_SMP_USER_LOCAL, %eax
    movl $OP_WHERE, %edi
    syscall
    movq %rax, %r14              # the CPU the local call ran on
    movl $SYS_SMP_USER, %eax
    movl $OP_WHERE, %edi
    syscall
    shlq $8, %rax
    orq %rax, %r14               # | the forwarded call's CPU << 8
    cmpq $MODE_COUNT, %r12
    jne .Lsmp_user_exit
    testq %r13, %r13
    jz .Lsmp_user_exit
    movl $SYS_SMP_USER_LOCAL, %eax
    movl $OP_ARRIVE, %edi
    syscall
.Lsmp_user_wait:
    movl $SYS_SMP_USER_LOCAL, %eax
    movl $OP_GO, %edi
    syscall
    testq %rax, %rax
    jz .Lsmp_user_wait
.Lsmp_user_bump:
    movl $SYS_SMP_USER, %eax
    movl $OP_BUMP, %edi
    syscall
    movl $SYS_SMP_USER_LOCAL, %eax
    movl $OP_BUMP, %edi
    syscall
    decq %r13
    jnz .Lsmp_user_bump
.Lsmp_user_exit:
    movq %r14, %rdi
    movl $SYS_EXIT, %eax
    syscall
    ud2                          # exit does not return

.global smp_user_stub_end
smp_user_stub_end:
