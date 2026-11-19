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
    iretq
.size proc_first_entry, . - proc_first_entry
