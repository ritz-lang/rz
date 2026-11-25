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
# Report: Getpid, the CPL from CS, and arg1, packed into the exit status
#   (arg1 & 0x7FFF) << 16 | cpl << 8 | (pid & 0xFF)
# which the kernel decodes and logs as "[driver] pid N cpl C arg1 K".

.section .text

# Syscall numbers (kernel/src/syscall/numbers.ritz, enum Syscall)
.equ SYS_EXIT,   20
.equ SYS_GETPID, 23

# Modes (postinit.ritz DRIVER_STUB_*)
.equ DRIVER_STUB_FAULT, 1
.equ DRIVER_STUB_SPIN,  2

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

.size driver_stub_start, . - driver_stub_start

.global driver_stub_end
driver_stub_end:
