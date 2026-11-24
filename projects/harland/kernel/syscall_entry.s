# Syscall Entry/Exit Assembly (x86_64)
#
# Fast system call entry point using SYSCALL instruction.
#
# On SYSCALL entry (set by CPU):
#   RCX = return RIP
#   R11 = saved RFLAGS
#   Interrupts may be disabled (depends on SFMASK)
#
# Syscall ABI:
#   RAX = syscall number
#   RDI = arg1, RSI = arg2, RDX = arg3
#   R10 = arg4 (RCX is clobbered), R8 = arg5, R9 = arg6
#
# Return value in RAX

.set SYSCALL_STACK_SIZE, 65536

# Ring-3 selectors (arch/x86_64/gdt.ritz GDT_USER_CODE/GDT_USER_DATA): user
# data at index 3, 64-bit user code at index 4, the order SYSRETQ needs
# (AGAST #4610). ritz0/test_harland_sysret.py pins them to gdt.ritz.
.set USER_SS, 0x1B
.set USER_CS, 0x23

.set KSTACK_GUARD_SIZE, 4096
.set KSTACK_STRIDE, KSTACK_GUARD_SIZE + SYSCALL_STACK_SIZE
.set KSTACK_SLOTS, 8                # proc/table.ritz MAX_PROCS

# ============================================================================
# Per-CPU area (AGAST #4192)
# ============================================================================
# Every CPU has one of these, reached through GS (arch/x86_64/percpu.ritz sets
# IA32_GS_BASE to it). syscall_entry runs in the kernel with GS on this CPU's
# area -- swapgs at entry, swapgs at exit -- so a SYSCALL on one CPU never
# touches another CPU's saved user frame or stack. The offsets are exported as
# absolute symbols so isr_stubs.s can name them too; the per-CPU module's
# layout mirrors them, and ritz0/test_harland_percpu.py pins every site to
# the same table.
.set PERCPU_SIZE, 64
.set PERCPU_SLOTS, 64               # arch/x86_64/cpu_map.ritz MAX_CPUS
.global PC_SELF
.set PC_SELF, 0                      # u64: address of this area
.global PC_CPU_INDEX
.set PC_CPU_INDEX, 8                 # u64: CPU index (cpu_map), not APIC ID
.global PC_KSTACK_TOP
.set PC_KSTACK_TOP, 16               # u64: kernel RSP syscall_entry loads
.global PC_USER_RSP
.set PC_USER_RSP, 24                 # u64: user RSP saved on entry
.global PC_USER_RIP
.set PC_USER_RIP, 32                 # u64: user RIP (RCX on entry)
.global PC_USER_RFLAGS
.set PC_USER_RFLAGS, 40              # u64: user RFLAGS (R11 on entry)
.global PC_USER_RAX
.set PC_USER_RAX, 48                 # u64: syscall number/return value

# The per-CPU areas themselves: index * PERCPU_SIZE. .bss, zeroed at boot.
.section .bss
.align 64
.global percpu_areas
.global percpu_areas_end
percpu_areas:
    .space PERCPU_SIZE * PERCPU_SLOTS
percpu_areas_end:

.section .bss
# One kernel stack per process-table slot (AGAST #3629): the running
# process's syscalls, the IRQs taken during them (IST=0), and the timer IRQ
# that preempts it in ring 3 (TSS.rsp0) all run on its own stack, and a
# process switched out in the kernel (blocked in wait/spawn/read, or
# preempted) keeps its frames there until it runs again. proc/sched.ritz
# points this CPU's PC_KSTACK_TOP and TSS.rsp0 (both per-CPU, AGAST #4192)
# at the next process's stack on every switch. Before #3629 this was a single
# syscall_stack, so a process could only stop in the kernel by never coming
# back (blocking spawn).
#
# Each slot is a guard page, then SYSCALL_STACK_SIZE of stack:
#
#   proc_kstacks + i * KSTACK_STRIDE    guard page (unmapped by
#                                       syscall_stack_init, AGAST #1877)
#   ... + KSTACK_GUARD_SIZE             the stack's lowest quadword: the
#                                       sentinel (#2761) syscall_stack_check
#                                       checks at syscall exit
#   ... + KSTACK_STRIDE                 the stack's top
#
# In .bss so an overflow can't run into .data (it once ran into g_child_pid
# and fs_current, AGAST #2761, #4064). A write into a guard page faults, and
# the #PF can't push onto the overflowed stack, so it becomes a #DF, which runs
# on its own IST stack (idt.ritz) and reports "syscall stack overflow"
# (exceptions.ritz).
.align 4096
proc_kstacks:
    .space KSTACK_STRIDE * KSTACK_SLOTS
proc_kstacks_end:

.section .data
# The BSP's saved kernel RSP while smp_test_enter_user runs a ring-3 test
# stub: smp_test_resume_bsp returns through it (AGAST #4192). Only the BSP
# uses this; it is not per-CPU state, because only one CPU runs the caller.
smp_test_bsp_rsp:
    .quad 0

# How many syscalls returned through the IRETQ exit (non-canonical return
# RIP) rather than SYSRETQ: the "sysret" boot self-test reads it (#4610).
.align 8
.global syscall_iret_exits
syscall_iret_exits:
    .quad 0

# ============================================================================
# Exported User Context (for spawn/exit)
# ============================================================================
# The saved user frame is per-CPU (AGAST #4192): the accessors below read and
# write this CPU's area through GS, so two CPUs in SYSCALL at once keep their
# own RIP/RSP/RFLAGS/RAX.

.section .text

# ============================================================================
# User Context Accessor Functions
# ============================================================================
# These functions allow Ritz code to read the saved user context.

# u64 syscall_iret_exit_count(void): syscall_iret_exits (AGAST #4610).
.global syscall_iret_exit_count
.type syscall_iret_exit_count, @function
syscall_iret_exit_count:
    movq syscall_iret_exits(%rip), %rax
    ret
.size syscall_iret_exit_count, . - syscall_iret_exit_count

.global get_syscall_user_rip
.type get_syscall_user_rip, @function
get_syscall_user_rip:
    movq %gs:PC_USER_RIP, %rax
    ret
.size get_syscall_user_rip, . - get_syscall_user_rip

.global get_syscall_user_rsp
.type get_syscall_user_rsp, @function
get_syscall_user_rsp:
    movq %gs:PC_USER_RSP, %rax
    ret
.size get_syscall_user_rsp, . - get_syscall_user_rsp

.global get_syscall_user_rflags
.type get_syscall_user_rflags, @function
get_syscall_user_rflags:
    movq %gs:PC_USER_RFLAGS, %rax
    ret
.size get_syscall_user_rflags, . - get_syscall_user_rflags

# ============================================================================
# Per-CPU area accessors (AGAST #4192)
# ============================================================================
# arch/x86_64/percpu.ritz binds these. The area accessors take a CPU index
# (cpu_map order); the GS ones read the area the current CPU is on.

# u64 percpu_area_for(u64 cpu_idx): the area's address (not this CPU's).
.global percpu_area_for
.type percpu_area_for, @function
percpu_area_for:
    movq %rdi, %rax
    shlq $6, %rax                    # * PERCPU_SIZE (64)
    leaq percpu_areas(%rip), %rcx
    addq %rcx, %rax
    ret
.size percpu_area_for, . - percpu_area_for

# u64 percpu_area_init(u64 cpu_idx): zero it, set self/index, return it.
.global percpu_area_init
.type percpu_area_init, @function
percpu_area_init:
    movq %rdi, %rax
    shlq $6, %rax
    leaq percpu_areas(%rip), %rcx
    addq %rcx, %rax
    movq $0, PC_SELF(%rax)
    movq $0, PC_CPU_INDEX(%rax)
    movq $0, PC_KSTACK_TOP(%rax)
    movq $0, PC_USER_RSP(%rax)
    movq $0, PC_USER_RIP(%rax)
    movq $0, PC_USER_RFLAGS(%rax)
    movq $0, PC_USER_RAX(%rax)
    movq $0, 56(%rax)
    movq %rax, PC_SELF(%rax)
    movq %rdi, PC_CPU_INDEX(%rax)
    ret
.size percpu_area_init, . - percpu_area_init

.global percpu_self
.type percpu_self, @function
percpu_self:
    movq %gs:PC_SELF, %rax
    ret
.size percpu_self, . - percpu_self

.global percpu_cpu_index
.type percpu_cpu_index, @function
percpu_cpu_index:
    movq %gs:PC_CPU_INDEX, %rax
    ret
.size percpu_cpu_index, . - percpu_cpu_index

.section .text

# ============================================================================
# Syscall Entry Point
# ============================================================================
.global syscall_entry
.type syscall_entry, @function
syscall_entry:
    # At this point:
    #   - We're in Ring 0
    #   - RCX = user RIP (return address)
    #   - R11 = user RFLAGS
    #   - RSP = user stack (NOT safe to use yet!)
    #   - RAX = syscall number
    #   - Interrupts are disabled (SFMASK clears IF)

    # CRITICAL: switch to this CPU's kernel stack immediately (AGAST #4192).
    # GS_BASE was the user's (0) in ring 3; swapgs puts this CPU's area there
    # so the saves and the stack load touch nothing another CPU owns.
    swapgs

    # Save the user's RSP and frame in this CPU's area before using RAX.
    movq %rsp, %gs:PC_USER_RSP
    movq %rax, %gs:PC_USER_RAX      # Save syscall number
    movq %rcx, %gs:PC_USER_RIP      # User return RIP
    movq %r11, %gs:PC_USER_RFLAGS   # User RFLAGS

    # Load the running process's kernel stack (per process, selected by this
    # CPU: proc/sched.ritz sets it on every switch).
    movq %gs:PC_KSTACK_TOP, %rsp

    # Now we have a safe kernel stack. Restore RAX from the saved value.
    movq %gs:PC_USER_RAX, %rax

    # Save all registers that the syscall handler might need
    # Build a SyscallFrame on the stack
    pushq %gs:PC_USER_RSP        # user_rsp
    pushq %r11                   # saved RFLAGS
    pushq %rcx                   # return RIP
    pushq %r9                    # arg6
    pushq %r8                    # arg5
    pushq %r10                   # arg4
    pushq %rdx                   # arg3
    pushq %rsi                   # arg2
    pushq %rdi                   # arg1
    pushq %rax                   # syscall number

    # Also save callee-saved registers (in case handler uses them)
    pushq %rbx
    pushq %rbp
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15

    # Enable interrupts during syscall handling. The timer IRQ (IST=0)
    # pushes onto this process's kernel stack and only counts the tick: the
    # kernel is never preempted, a syscall leaves the CPU only by blocking
    # in the scheduler (proc/sched.ritz). Other IRQs run on IST2.
    sti

    # Call the Ritz syscall handler
    # syscall_handler(rax, rdi, rsi, rdx, r10) -> i64
    #
    # Our saved frame on the stack (after callee-saved):
    #   +0:  r15 (callee-saved)
    #   +8:  r14
    #   +16: r13
    #   +24: r12
    #   +32: rbp
    #   +40: rbx
    #   +48: RAX (syscall number)
    #   +56: RDI (arg1)
    #   +64: RSI (arg2)
    #   +72: RDX (arg3)
    #   +80: R10 (arg4)
    #   ... etc
    #
    # Load arguments from saved frame
    movq 48(%rsp), %rdi          # rdi = saved RAX (syscall number)
    movq 56(%rsp), %rsi          # rsi = saved RDI (arg1)
    movq 64(%rsp), %rdx          # rdx = saved RSI (arg2)
    movq 72(%rsp), %rcx          # rcx = saved RDX (arg3)
    movq 80(%rsp), %r8           # r8 = saved R10 (arg4)
    call syscall_handler

    # Return value is in RAX - save it to a temporary location
    # We'll store it where the syscall number was saved (we don't need it anymore)
    # Stack layout at this point (offset from RSP):
    #   +0:  r15 (callee-saved)
    #   +8:  r14
    #   +16: r13
    #   +24: r12
    #   +32: rbp
    #   +40: rbx
    #   +48: RAX (syscall number) <- we'll overwrite this with return value
    #   +56: RDI (arg1)
    #   ...
    movq %rax, 48(%rsp)          # Save return value over saved syscall number

    # Disable interrupts for exit sequence
    cli

    # Restore callee-saved registers (CRITICAL: must restore user's RBX!)
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %rbp
    popq %rbx                    # Restore user's RBX

    # Pop syscall frame
    popq %rax                    # This is now the return value (we saved it here)
    popq %rdi                    # Restore arg1
    popq %rsi                    # arg2
    popq %rdx                    # arg3
    popq %r10                    # arg4
    popq %r8                     # arg5
    popq %r9                     # arg6

    # Left on the stack: return RIP, RFLAGS, user RSP. RCX and R11 are free:
    # SYSCALL clobbers them, and they get the return RIP and RFLAGS below.
    #
    # Return to ring 3 with SYSRETQ (AGAST #4610): RCX -> RIP, R11 -> RFLAGS,
    # SS = STAR[63:48] + 8, CS = STAR[63:48] + 16 (gdt.ritz GDT_SYSRET_BASE).
    # Except for a non-canonical return RIP: SYSRETQ to one #GPs in ring 0
    # on Intel CPUs with the user's RSP already loaded (the SYSRET erratum).
    # That RIP takes the IRETQ exit instead. Canonical (4-level paging) means
    # bits 63:47 all equal bit 47: shifting it to bit 63 and back is a no-op.
    movq 0(%rsp), %rcx
    movq %rcx, %r11
    shlq $16, %r11
    sarq $16, %r11
    cmpq %rcx, %r11
    jne .Lsyscall_exit_iret

    popq %rcx                    # return RIP
    popq %r11                    # saved RFLAGS
    popq %rsp                    # user stack (user_rsp)
    # Back to the user's GS before ring 3 (AGAST #4192): the next SYSCALL's
    # swapgs then puts this CPU's area back.
    swapgs
    sysretq

.Lsyscall_exit_iret:
    # The return RIP is non-canonical. Build an IRETQ frame at the top of
    # this kernel stack (the three slots above are popped into this CPU's
    # area first, the only free scratch). The IRETQ still #GPs, in ring 0 but
    # on the kernel stack: isr_stubs.s's #GP stub sees the fault is at
    # syscall_exit_iret and swaps GS back, and exceptions.ritz takes it as
    # the user's fault. syscall_iret_exits counts these exits for the
    # "sysret" boot self-test (arch/x86_64/cpu_smp.ritz).
    popq %gs:PC_USER_RIP
    popq %gs:PC_USER_RFLAGS
    popq %gs:PC_USER_RSP
    pushq $USER_SS
    pushq %gs:PC_USER_RSP
    pushq %gs:PC_USER_RFLAGS
    pushq $USER_CS
    pushq %gs:PC_USER_RIP
    # RCX/R11 as SYSRETQ would leave them, not kernel values.
    movq %gs:PC_USER_RIP, %rcx
    movq %gs:PC_USER_RFLAGS, %r11
    lock incq syscall_iret_exits(%rip)
    swapgs
.global syscall_exit_iret
syscall_exit_iret:
    iretq

.size syscall_entry, . - syscall_entry

# ============================================================================
# Jump to Userspace (Initial Entry)
# ============================================================================
# void jump_to_userspace(u64 entry_point, u64 user_stack)
#
# Used to start a new user process. Sets up IRET frame and jumps.
#
.global jump_to_userspace
.type jump_to_userspace, @function
jump_to_userspace:
    # Arguments:
    #   RDI = entry point (user RIP)
    #   RSI = user stack pointer

    # Disable interrupts during transition
    cli

    # Build IRET frame for Ring 3
    # Stack layout for IRETQ: RIP, CS, RFLAGS, RSP, SS

    pushq $USER_SS               # SS (user data, ring 3)
    pushq %rsi                   # RSP (user stack)
    # Enable interrupts in userspace for true preemption
    # IF (bit 9) = 0x200, reserved bit 1 = 0x002
    pushq $0x202                 # RFLAGS (IF=1, reserved bit 1 = 1)
    pushq $USER_CS               # CS (64-bit user code, ring 3)
    pushq %rdi                   # RIP (entry point)

    # Clear all general purpose registers (security)
    xorq %rax, %rax
    xorq %rbx, %rbx
    xorq %rcx, %rcx
    xorq %rdx, %rdx
    xorq %rdi, %rdi
    xorq %rsi, %rsi
    xorq %rbp, %rbp
    xorq %r8, %r8
    xorq %r9, %r9
    xorq %r10, %r10
    xorq %r11, %r11
    xorq %r12, %r12
    xorq %r13, %r13
    xorq %r14, %r14
    xorq %r15, %r15

    # Jump to userspace! swapgs first: in ring 3 GS is the user's (0), and
    # KERNEL_GS_BASE holds this CPU's area for the next SYSCALL (AGAST #4192).
    swapgs
    iretq

.size jump_to_userspace, . - jump_to_userspace

# ============================================================================
# Set Syscall Return Context
# ============================================================================
# void syscall_set_return_context(u64 rip, u64 rsp, u64 rflags)
#
# Used by sys_exit to restore parent context when a child process exits.
# Modifies the saved values on the syscall stack so that when syscall_entry
# returns, it goes to the specified context instead of the original caller.
#
.global syscall_set_return_context
.type syscall_set_return_context, @function
syscall_set_return_context:
    # Arguments:
    #   RDI = new user RIP
    #   RSI = new user RSP
    #   RDX = new user RFLAGS
    #
    # Update this CPU's saved context variables - these will be used
    # by the next syscall return
    movq %rdi, %gs:PC_USER_RIP
    movq %rsi, %gs:PC_USER_RSP
    movq %rdx, %gs:PC_USER_RFLAGS
    ret

.size syscall_set_return_context, . - syscall_set_return_context

# ============================================================================
# Jump to Userspace with Arguments (argc/argv)
# ============================================================================
# void jump_to_userspace_with_args(u64 entry_point, u64 user_stack, i64 argc, u64 argv)
#
# Jumps to userspace with argc in RDI and argv in RSI.
# This follows the SysV AMD64 ABI for passing arguments to main().
#
.global jump_to_userspace_with_args
.type jump_to_userspace_with_args, @function
jump_to_userspace_with_args:
    # Arguments:
    #   RDI = entry point (user RIP)
    #   RSI = user stack pointer
    #   RDX = argc
    #   RCX = argv pointer

    # Disable interrupts during transition
    cli

    # Save argc and argv before we clobber RDX/RCX
    movq %rdx, %r8              # Save argc in R8
    movq %rcx, %r9              # Save argv in R9

    # Build IRET frame for Ring 3
    # Stack layout for IRETQ: RIP, CS, RFLAGS, RSP, SS

    pushq $USER_SS               # SS (user data, ring 3)
    pushq %rsi                   # RSP (user stack)
    pushq $0x202                 # RFLAGS (IF=1, reserved bit 1 = 1)
    pushq $USER_CS               # CS (64-bit user code, ring 3)
    pushq %rdi                   # RIP (entry point)

    # Set up main() arguments per SysV AMD64 ABI:
    #   RDI = argc (first argument)
    #   RSI = argv (second argument)
    movq %r8, %rdi              # argc
    movq %r9, %rsi              # argv

    # Clear other registers (security)
    xorq %rax, %rax
    xorq %rbx, %rbx
    xorq %rcx, %rcx
    xorq %rdx, %rdx
    xorq %rbp, %rbp
    xorq %r8, %r8
    xorq %r9, %r9
    xorq %r10, %r10
    xorq %r11, %r11
    xorq %r12, %r12
    xorq %r13, %r13
    xorq %r14, %r14
    xorq %r15, %r15

    # Jump to userspace! swapgs first (see jump_to_userspace).
    swapgs
    iretq

.size jump_to_userspace_with_args, . - jump_to_userspace_with_args

# ============================================================================
# Userspace Syscall Stub (for testing - would be in user program)
# ============================================================================
# This is what userspace programs call to make syscalls.
# In a real system, this would be in a user library (libc equivalent).
#
# i64 harland_syscall(u64 num, u64 a1, u64 a2, u64 a3, u64 a4, u64 a5, u64 a6)
#
.global harland_syscall
.type harland_syscall, @function
harland_syscall:
    # Arguments already in the right registers:
    #   RDI = syscall number → move to RAX
    #   RSI = arg1 → move to RDI
    #   RDX = arg2 → move to RSI
    #   RCX = arg3 → move to RDX
    #   R8  = arg4 → move to R10
    #   R9  = arg5 → move to R8
    #   [stack] = arg6 → move to R9

    movq %rdi, %rax              # Syscall number
    movq %rsi, %rdi              # Arg 1
    movq %rdx, %rsi              # Arg 2
    movq %rcx, %rdx              # Arg 3
    movq %r8, %r10               # Arg 4 (R10, not RCX - SYSCALL clobbers RCX)
    movq %r9, %r8                # Arg 5
    movq 8(%rsp), %r9            # Arg 6 from stack

    syscall

    # Return value is in RAX
    ret

.size harland_syscall, . - harland_syscall

# ============================================================================
# Kernel Stacks (AGAST #2761, #1877, #3629)
# ============================================================================
# The sentinel, guard-page and high-water logic is syscall/stack.ritz's; it
# finds each slot from these.

# u64 proc_kstacks_base(void): address of slot 0's guard page (page-aligned).
.global proc_kstacks_base
.type proc_kstacks_base, @function
proc_kstacks_base:
    leaq proc_kstacks(%rip), %rax
    ret
.size proc_kstacks_base, . - proc_kstacks_base

# u64 kstack_stride(void): bytes per slot, guard page included.
.global kstack_stride
.type kstack_stride, @function
kstack_stride:
    movq $KSTACK_STRIDE, %rax
    ret
.size kstack_stride, . - kstack_stride

# u64 kstack_slots(void): how many slots (proc/table.ritz MAX_PROCS).
.global kstack_slots
.type kstack_slots, @function
kstack_slots:
    movq $KSTACK_SLOTS, %rax
    ret
.size kstack_slots, . - kstack_slots

# u64 syscall_stack_size(void): one slot's stack, in bytes.
.global syscall_stack_size
.type syscall_stack_size, @function
syscall_stack_size:
    movq $SYSCALL_STACK_SIZE, %rax
    ret
.size syscall_stack_size, . - syscall_stack_size

# void kstack_set_current(u64 top): the stack syscall_entry loads, per CPU.
# Called with GS on this CPU's area (arch/x86_64/percpu.ritz cpu_bringup).
.global kstack_set_current
.type kstack_set_current, @function
kstack_set_current:
    movq %rdi, %gs:PC_KSTACK_TOP
    ret
.size kstack_set_current, . - kstack_set_current

# u64 kstack_get_current(void)
.global kstack_get_current
.type kstack_get_current, @function
kstack_get_current:
    movq %gs:PC_KSTACK_TOP, %rax
    ret
.size kstack_get_current, . - kstack_get_current

# ============================================================================
# SYSCALL MSRs (AGAST #4192)
# ============================================================================
# EFER.SCE, STAR (kernel CS 0x08 in 47:32, SYSRETQ's base 0x13 in 63:48),
# LSTAR (syscall_entry) and SFMASK (IF) are
# per-CPU MSRs: every CPU sets its own in cpu_bringup, before it can enter
# ring 3. Same values syscall/runtime/entry.ritz writes on the BSP.
.set MSR_EFER, 0xC0000080
.set MSR_STAR, 0xC0000081
.set MSR_LSTAR, 0xC0000082
.set MSR_SFMASK, 0xC0000084
.set EFER_SCE, 1
.set KERNEL_CS, 0x08                   # arch/x86_64/gdt.ritz GDT_KERNEL_CODE
.set SYSRET_BASE, 0x13                 # arch/x86_64/gdt.ritz GDT_SYSRET_BASE
.set RFLAGS_IF, 0x200
.global syscall_msr_init
.type syscall_msr_init, @function
syscall_msr_init:
    # EFER.SCE = 1
    movl $MSR_EFER, %ecx
    rdmsr
    orl $EFER_SCE, %eax
    wrmsr
    # STAR: bits 47:32 (EDX's low half) = kernel CS, bits 63:48 (EDX's high
    # half) = SYSRETQ's base (AGAST #4610)
    movl $MSR_STAR, %ecx
    xorl %eax, %eax
    movl $(KERNEL_CS | (SYSRET_BASE << 16)), %edx
    wrmsr
    # LSTAR = syscall_entry
    movabsq $syscall_entry, %rax
    movq %rax, %rdx
    shrq $32, %rdx
    movl $MSR_LSTAR, %ecx
    wrmsr
    # SFMASK = RFLAGS.IF: SYSCALL enters the kernel with IF=0
    movl $MSR_SFMASK, %ecx
    movl $RFLAGS_IF, %eax
    xorl %edx, %edx
    wrmsr
    ret
.size syscall_msr_init, . - syscall_msr_init

# ============================================================================
# Ring-3 self-test entry/resume (AGAST #4192)
# ============================================================================
# uint64 smp_test_enter_user(u64 entry, u64 user_stack): run a user stub
# from kernel mode and return when it SYSCALLs the "done" phase. Saves the
# caller's callee-saved registers and RSP; smp_test_resume_bsp restores them.
# Kernel GS state on return is the state syscall_entry leaves (GS = this
# CPU's area), so the caller continues in the kernel as usual.
.global smp_test_enter_user
.type smp_test_enter_user, @function
smp_test_enter_user:
    pushq %rbp
    pushq %rbx
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    movq %rsp, smp_test_bsp_rsp(%rip)
    # RDI = entry, RSI = user_stack: jump_to_userspace's arguments.
    jmp jump_to_userspace
.size smp_test_enter_user, . - smp_test_enter_user

.global smp_test_resume_bsp
.type smp_test_resume_bsp, @function
smp_test_resume_bsp:
    movq smp_test_bsp_rsp(%rip), %rsp
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %rbx
    popq %rbp
    xorl %eax, %eax
    ret
.size smp_test_resume_bsp, . - smp_test_resume_bsp

# uint64 sysret_ring0_iret_probe(u64 user_rip, u64 user_rsp): drive #4610's
# ring-0 fixup on any CPU (AGAST #4612). The non-canonical exit #GPs in ring
# 0 only where the IRETQ checks the RIP (KVM, real hardware); TCG loads it
# and faults on the fetch in ring 3. This IRETQs from syscall_exit_iret,
# with the exit's GS state (the user's), to a ring-3 frame with a null SS,
# which #GPs in ring 0 on every x86-64: the #GP stub must swap GS back for a
# fault at syscall_exit_iret and exceptions.ritz must take it as the user's
# fault. Its catcher (arch/x86_64/sysret_catch.ritz, armed by the caller)
# resumes here through smp_test_resume_bsp, like smp_test_enter_user. It
# jumps past the exit's syscall_iret_exits count.
.global sysret_ring0_iret_probe
.type sysret_ring0_iret_probe, @function
sysret_ring0_iret_probe:
    pushq %rbp
    pushq %rbx
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    movq %rsp, smp_test_bsp_rsp(%rip)
    cli
    pushq $0                     # SS: null, with a ring-3 CS: #GP(0) in ring 0
    pushq %rsi                   # RSP
    pushq $2                     # RFLAGS: IF=0
    pushq $USER_CS
    pushq %rdi                   # RIP
    swapgs                       # the exit's GS: the user's
    jmp syscall_exit_iret
.size sysret_ring0_iret_probe, . - sysret_ring0_iret_probe
