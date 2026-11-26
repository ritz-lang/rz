# Harland process switch (AGAST #3629)
#
# Every process has its own kernel stack (syscall_entry.s proc_kstacks). A
# process leaves the CPU only from inside the kernel, on that stack: a timer
# IRQ that interrupted it in ring 3 (its IRET frame and GPRs sit at the top),
# or a syscall that blocks or yields. proc/sched.ritz switches page table,
# TSS.rsp0, the syscall stack and the fs table, then calls sched_switch to
# swap kernel stacks. The switched-to process returns from its own
# sched_switch call and unwinds to its own iretq.
#
# Not named context_switch.s: that was the deleted kernel-thread scheduler's
# (#1882), which test_harland_process_model.py keeps out.

.code64
.section .text

# void sched_switch(u64* save_ksp, u64 new_ksp)
# Push the callee-saved registers and RFLAGS (so IF comes back as each side
# left it), save RSP to *save_ksp, load new_ksp, pop the same, return into
# the other process. Called with IF=0.
#
# The frame at a saved ksp, low to high:
#   rflags, r15, r14, r13, r12, rbx, rbp, return address
# sched_prepare_user (proc/sched.ritz) builds one by hand for a new process.
.global sched_switch
.type sched_switch, @function
sched_switch:
    pushq %rbp
    pushq %rbx
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    pushfq
    movq %rsp, (%rdi)
    movq %rsi, %rsp
    popfq
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %rbx
    popq %rbp
    ret
.size sched_switch, . - sched_switch

# A new process's first sched_switch returns here, with RSP at the user
# frame sched_prepare_user put at the top of its kernel stack: isr_stubs.s's
# InterruptFrame layout (15 GPRs from r15 up, vector, error code, then the
# IRET frame RIP, CS, RFLAGS, RSP, SS). The same exit as irq_common's.
.global proc_first_entry
.type proc_first_entry, @function
proc_first_entry:
    # A process marked PROC_REAP before it ever ran does not enter user mode
    # either (#4714, syscall_entry.s reap_if_marked).
    call reap_if_marked
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %r11
    popq %r10
    popq %r9
    popq %r8
    popq %rbp
    popq %rdi
    popq %rsi
    popq %rdx
    popq %rcx
    popq %rbx
    popq %rax
    addq $16, %rsp
    # A new process is first switched to from kernel mode (a spawn's
    # sched_switch), where GS is this CPU's area; ring 3 needs the user's GS
    # and KERNEL_GS_BASE to hold the area for its next SYSCALL (AGAST #4192).
    swapgs
    iretq
.size proc_first_entry, . - proc_first_entry

# void kstack_call(void (*body)(void), u64 top): run body() on the stack
# whose top is `top`, then return on the caller's stack. Pid 1 before
# run_init runs on the boot stack, which is identity-mapped and absent from
# every user PML4 (vmm_create_user_pml4 copies only the kernel half), so
# code that switches pid 1 to a child must first move onto pid 1's own
# kernel stack (AGAST #4713, RING1_DRIVER.md section 9 step 1). `top` is
# 16-byte aligned (kstack_top); RBP keeps the caller's RSP across the call.
.global kstack_call
.type kstack_call, @function
kstack_call:
    pushq %rbp
    movq %rsp, %rbp
    movq %rsi, %rsp
    callq *%rdi
    movq %rbp, %rsp
    popq %rbp
    ret
.size kstack_call, . - kstack_call
