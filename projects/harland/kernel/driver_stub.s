# Boot-test stub for a kernel-spawned CPL-3 process (AGAST #4713,
# RING1_DRIVER.md section 2, Tests 1-3).
#
# postinit.ritz's driver-* boot tests copy the bytes between
# driver_stub_start and driver_stub_end into one user page of a child of
# pid 1 (syscall/runtime/process.ritz process_spawn_image) and enter it at
# CPL 3 through sched_prepare_user's ordinary frame (CS 0x23, SS 0x1B). The
# code is position-independent and uses no data outside the copied range.
# Only the boot-test mode spawns it.
#
# Entry: RDI = mode, RSI = arg1, both chosen by the kernel.
#   mode 0 (ENTER): report and exit.
#   mode 1 (FAULT): read address 0; the #PF kills the process (status 142).
#   mode 2 (SPIN):  busy-wait RSI TSC cycles at CPL 3 (the timer preempts
#                   it), then report and exit.
#   mode 3 (IRQ_WAIT, #4719): RSI is a CAP_TYPE_IRQ handle the kernel
#                   granted. Five DrvIrqWait calls, each checked; the exit
#                   status is the number of the first that failed, else 0:
#                   1  out_cap 0             -> Errno.Inval, out_count kept
#                   2  out_cap 9             -> Errno.Inval, out_count kept
#                   3  handle 0 (not held)   -> Errno.Perm, out_count kept
#                   4  out_cap 2, parks      -> 0: out_count 1, out[0] =
#                      { handle, EVENT_DATA }, out[1] kept
#                   5  the same again        -> 1 at the deadline:
#                      out_count 0, out[0] kept
# Report: Getpid, the CPL from CS, and arg1, packed into the exit status
#   (arg1 & 0x7FFF) << 16 | cpl << 8 | (pid & 0xFF)
# which the kernel decodes and logs as "[driver] pid N cpl C arg1 K".

.section .text

# Syscall numbers (kernel/src/syscall/numbers.ritz, enum Syscall)
.equ SYS_EXIT,   20
.equ SYS_GETPID, 23
.equ SYS_DRV_IRQ_WAIT, 220

# Modes (postinit.ritz DRIVER_STUB_*)
.equ DRIVER_STUB_FAULT, 1
.equ DRIVER_STUB_SPIN,  2
.equ DRIVER_STUB_IRQ_WAIT, 3

# driver_abi/src/wait.ritz: WaitRequest (40 bytes) and WaitEvent (16)
.equ WR_SOURCES,      0
.equ WR_SOURCE_COUNT, 8
.equ WR_OUT_CAP,      12
.equ WR_OUT,          16
.equ WR_DEADLINE,     24
.equ WR_OUT_COUNT,    32
.equ WR_PAD,          36
.equ WR_EVENTS,       48          # two WaitEvents after the request
.equ WE_HANDLE,       0
.equ WE_BITS,         8
.equ WE_SIZE,         16
.equ EVENT_DATA,      1
.equ ERRNO_PERM,      -1
.equ ERRNO_INVAL,     -22
.equ KEPT_COUNT,      0x5A        # out_count before a call that must not write it

.global driver_stub_start
.type driver_stub_start, @function
driver_stub_start:
    # syscall_entry.s restores the callee-saved registers, so r12-r14 hold
    # the entry arguments across Getpid.
    movq %rdi, %r12
    movq %rsi, %r13
    cmpq $DRIVER_STUB_FAULT, %r12
    jne .Ldriver_stub_not_fault
    xorl %eax, %eax
    movq (%rax), %rax            # #PF at CPL 3: never returns
    ud2
.Ldriver_stub_not_fault:
    cmpq $DRIVER_STUB_IRQ_WAIT, %r12
    je .Ldriver_stub_irq_wait
    cmpq $DRIVER_STUB_SPIN, %r12
    jne .Ldriver_stub_report
    rdtsc
    shlq $32, %rdx
    orq %rdx, %rax
    leaq (%rax,%r13), %r14       # the deadline: now + arg1 cycles
.Ldriver_stub_spin:
    pause
    rdtsc
    shlq $32, %rdx
    orq %rdx, %rax
    cmpq %r14, %rax
    jb .Ldriver_stub_spin
.Ldriver_stub_report:
    movq $SYS_GETPID, %rax
    syscall
    movzbl %al, %edi             # pid & 0xFF
    movl %cs, %eax
    andl $3, %eax                # the CPL this code runs at
    shll $8, %eax
    orl %eax, %edi
    movl %r13d, %eax
    andl $0x7FFF, %eax
    shll $16, %eax
    orl %eax, %edi
    movq $SYS_EXIT, %rax
    syscall
    ud2                          # exit does not return

# Mode 3. r14 = the request and its two out slots, on the user stack; r15 =
# the step number reported if a check fails.
.Ldriver_stub_irq_wait:
    subq $80, %rsp
    movq %rsp, %r14
    movabsq $0xEEEEEEEEEEEEEEEE, %rbx   # the untouched out-slot pattern

    movl $1, %r15d                       # 1: out_cap 0
    xorl %esi, %esi
    call .Lirq_wait_call_cap
    cmpq $ERRNO_INVAL, %rax
    jne .Lirq_wait_fail
    cmpl $KEPT_COUNT, WR_OUT_COUNT(%r14)
    jne .Lirq_wait_fail

    movl $2, %r15d                       # 2: out_cap 9
    movl $9, %esi
    call .Lirq_wait_call_cap
    cmpq $ERRNO_INVAL, %rax
    jne .Lirq_wait_fail
    cmpl $KEPT_COUNT, WR_OUT_COUNT(%r14)
    jne .Lirq_wait_fail

    movl $3, %r15d                       # 3: a handle it does not hold
    movl $2, %esi
    call .Lirq_wait_fill
    movq $SYS_DRV_IRQ_WAIT, %rax
    xorl %edi, %edi
    movq %r14, %rsi
    syscall
    cmpq $ERRNO_PERM, %rax
    jne .Lirq_wait_fail
    cmpl $KEPT_COUNT, WR_OUT_COUNT(%r14)
    jne .Lirq_wait_fail

    movl $4, %r15d                       # 4: parks until its IRQ is latched
    movl $2, %esi
    call .Lirq_wait_call_cap
    cmpq $0, %rax
    jne .Lirq_wait_fail
    cmpl $1, WR_OUT_COUNT(%r14)
    jne .Lirq_wait_fail
    cmpq %r13, WR_EVENTS+WE_HANDLE(%r14)
    jne .Lirq_wait_fail
    cmpl $EVENT_DATA, WR_EVENTS+WE_BITS(%r14)
    jne .Lirq_wait_fail
    cmpq %rbx, WR_EVENTS+WE_SIZE+WE_HANDLE(%r14)
    jne .Lirq_wait_fail

    movl $5, %r15d                       # 5: seen = latched: the deadline
    movl $2, %esi
    call .Lirq_wait_call_cap
    cmpq $1, %rax
    jne .Lirq_wait_fail
    cmpl $0, WR_OUT_COUNT(%r14)
    jne .Lirq_wait_fail
    cmpq %rbx, WR_EVENTS+WE_HANDLE(%r14)
    jne .Lirq_wait_fail

    xorl %r15d, %r15d                    # every check held
.Lirq_wait_fail:
    movl %r15d, %edi
    movq $SYS_EXIT, %rax
    syscall
    ud2

# Fill the request for out_cap ESI (no sources, out = the two slots,
# out_count KEPT_COUNT, both slots the untouched pattern) and call
# DrvIrqWait with the granted handle (r13). RAX = the result.
.Lirq_wait_call_cap:
    call .Lirq_wait_fill
    movq $SYS_DRV_IRQ_WAIT, %rax
    movq %r13, %rdi
    movq %r14, %rsi
    syscall
    ret

.Lirq_wait_fill:
    movq $0, WR_SOURCES(%r14)
    movl $0, WR_SOURCE_COUNT(%r14)
    movl %esi, WR_OUT_CAP(%r14)
    leaq WR_EVENTS(%r14), %rax
    movq %rax, WR_OUT(%r14)
    movq $0, WR_DEADLINE(%r14)
    movl $KEPT_COUNT, WR_OUT_COUNT(%r14)
    movl $0, WR_PAD(%r14)
    movq %rbx, WR_EVENTS+WE_HANDLE(%r14)
    movq %rbx, WR_EVENTS+WE_BITS(%r14)
    movq %rbx, WR_EVENTS+WE_SIZE+WE_HANDLE(%r14)
    movq %rbx, WR_EVENTS+WE_SIZE+WE_BITS(%r14)
    ret

.size driver_stub_start, . - driver_stub_start

.global driver_stub_end
driver_stub_end:
