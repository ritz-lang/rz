# The smp-user boot test's CPL-3 stub (AGAST #4881, kernel/src/syscall/runtime/smp_user.ritz)
#
# Position-independent: process_spawn_image_on copies it to USER_IMAGE_BASE
# of its own page table. RDI is the mode, RSI the bump count (MODE_COUNT).
# It asks where its local call and its forwarded call ran (OP_WHERE on
# SmpUserLocal and SmpUser), and in MODE_COUNT checks in (OP_ARRIVE), waits
# for the other process (OP_GO), then makes RSI forwarded and RSI local
# bumps, alternating. It exits with local_cpu | forwarded_cpu << 8.
#
# MODE_WAKE (test (b)): RSI is the role, WAITS_FIRST or NOTIFIES_FIRST. It
# polls OP_HANDLE until the kernel has granted its shm handle, then, in its
# role's order, ShmWaits once for DATA on it and, once OP_PEER_PARKED says
# the other process is parked on an idle CPU, ShmNotifies DATA. Its wait
# done, it says so (OP_DONE), and it exits only once the other's wait is
# done too (OP_PEER_DONE): an exit retires its handle, which posts
# PEER_CLOSE to the other from the BSP and would wake it there. It exits
# with the wait's return | the CPU it resumed on << 8 | the CPU it notified
# from << 16 | the records << 24 | the DATA bit << 28.
#
# syscall_entry.s restores the callee-saved registers, so rbx, rbp and
# r12-r15 survive every syscall.

.equ SYS_EXIT,            20
.equ SYS_SHM_WAIT,        229
.equ SYS_SHM_NOTIFY,      230
.equ SYS_SMP_USER,        253
.equ SYS_SMP_USER_LOCAL,  252
.equ OP_ARRIVE,           1
.equ OP_GO,               2
.equ OP_BUMP,             3
.equ OP_WHERE,            4
.equ OP_HANDLE,           5
.equ OP_PEER_PARKED,      6
.equ OP_DONE,             7
.equ OP_PEER_DONE,        8
.equ MODE_COUNT,          1
.equ MODE_WAKE,           3
.equ WAITS_FIRST,         0
.equ EVENT_DATA,          1
.equ WAKE_DEADLINE_MS,    5000

.section .text
.global smp_user_stub_start
.type smp_user_stub_start, @function
smp_user_stub_start:
    movq %rdi, %r12              # mode
    movq %rsi, %r13              # bumps of each kind, or the role
    cmpq $MODE_WAKE, %r12
    je .Lsmp_wake
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

.Lsmp_wake:
    movl $SYS_SMP_USER_LOCAL, %eax
    movl $OP_HANDLE, %edi
    movq %r13, %rsi
    syscall
    testq %rax, %rax
    jz .Lsmp_wake                # not granted yet
    movq %rax, %r15              # the shm handle
    xorl %r14d, %r14d            # the exit status
    cmpq $WAITS_FIRST, %r13
    jne .Lsmp_wake_notify_first
    call .Lsmp_wait_once
    call .Lsmp_notify_parked_peer
    jmp .Lsmp_wake_exit
.Lsmp_wake_notify_first:
    call .Lsmp_notify_parked_peer
    call .Lsmp_wait_once
.Lsmp_wake_exit:
    movl $SYS_SMP_USER_LOCAL, %eax
    movl $OP_PEER_DONE, %edi
    movq %r13, %rsi
    syscall
    testq %rax, %rax
    jz .Lsmp_wake_exit
    jmp .Lsmp_user_exit

# One ShmWait for DATA on r15, its request on the stack: the source at 0,
# the record at 16, the WaitRequest at 32 (sources, source_count, out_cap,
# out, deadline, out_count, _pad). ORs its fields into r14.
.Lsmp_wait_once:
    subq $80, %rsp
    movq %r15, 0(%rsp)
    movl $EVENT_DATA, 8(%rsp)
    movl $0, 12(%rsp)
    movq $0, 16(%rsp)
    movq $0, 24(%rsp)
    leaq 0(%rsp), %rax
    movq %rax, 32(%rsp)
    movl $1, 40(%rsp)
    movl $1, 44(%rsp)
    leaq 16(%rsp), %rax
    movq %rax, 48(%rsp)
    movq $WAKE_DEADLINE_MS, 56(%rsp)
    movq $0, 64(%rsp)
    leaq 32(%rsp), %rdi
    movl $SYS_SHM_WAIT, %eax
    syscall
    movzbl %al, %eax
    orq %rax, %r14               # the wait's return
    movl 64(%rsp), %eax
    andl $15, %eax
    shlq $24, %rax
    orq %rax, %r14               # the records
    movl 24(%rsp), %eax
    andl $EVENT_DATA, %eax
    shlq $28, %rax
    orq %rax, %r14               # the DATA bit
    movl $SYS_SMP_USER_LOCAL, %eax
    movl $OP_WHERE, %edi
    syscall
    movzbl %al, %eax
    shlq $8, %rax
    orq %rax, %r14               # the CPU it resumed on
    movl $SYS_SMP_USER_LOCAL, %eax
    movl $OP_DONE, %edi
    movq %r13, %rsi
    syscall
    addq $80, %rsp
    ret

# Wait until the other process is parked on an idle CPU, then ShmNotify DATA
# on r15. ORs the CPU it notified from into r14.
.Lsmp_notify_parked_peer:
    movl $SYS_SMP_USER_LOCAL, %eax
    movl $OP_PEER_PARKED, %edi
    movq %r13, %rsi
    syscall
    testq %rax, %rax
    jz .Lsmp_notify_parked_peer
    movl $SYS_SHM_NOTIFY, %eax
    movq %r15, %rdi
    movl $EVENT_DATA, %esi
    syscall
    movl $SYS_SMP_USER_LOCAL, %eax
    movl $OP_WHERE, %edi
    syscall
    movzbl %al, %eax
    shlq $16, %rax
    orq %rax, %r14
    ret

.global smp_user_stub_end
smp_user_stub_end:
