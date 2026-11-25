# Harland ISR Stubs and CPU Support Routines
#
# Low-level interrupt service routine stubs that:
# 1. Push a dummy error code (if CPU didn't push one)
# 2. Push the interrupt vector number
# 3. Save all general-purpose registers
# 4. Call the high-level Ritz handler
# 5. Restore registers
# 6. Return from interrupt
#
# These MUST be in assembly because they need precise stack control.

.code64
.section .text

# ============================================================================
# GDT Flush (reload GDT and segment registers)
# ============================================================================

.global gdt_flush
gdt_flush:
    # RDI = pointer to GDT descriptor
    lgdt (%rdi)

    # Reload data segments with kernel data selector (0x10)
    movw $0x10, %ax
    movw %ax, %ds
    movw %ax, %es
    movw %ax, %fs
    movw %ax, %gs
    movw %ax, %ss

    # Far jump to reload CS with kernel code selector (0x08)
    pushq $0x08
    leaq .gdt_reload_cs(%rip), %rax
    pushq %rax
    lretq
.gdt_reload_cs:
    xorl %eax, %eax     # Return 0
    ret

# ============================================================================
# SWAPGS_IF_USER: enter the per-CPU GS state for a frame from ring 3
# ============================================================================
# GS_BASE is the user's when the CPU is in ring 3 (swapgs in syscall_entry
# and jump_to_userspace) and this CPU's area in the kernel (AGAST #4192).
# An interrupt or exception from user has to swapgs before any code can
# touch per-CPU state, and an exit to user has to swap it back. At stub entry
# the frame's CS is at 8(%rsp) (RIP, CS, ...) -- except that an exception
# with a CPU-pushed error code has the error at 0 and so CS at 16. Testing
# flags here is safe: the frame's RFLAGS is on the stack, untouched.
.macro SWAPGS_IF_USER_AT cs_off
    testq $3, \cs_off(%rsp)
    jz 8f
    swapgs
8:
.endm
.macro SWAPGS_IF_USER
    SWAPGS_IF_USER_AT 8
.endm

# The same for an exception with a CPU-pushed error code (CS at 16, RIP at
# 8), plus one kernel-mode case (AGAST #4610): a fault on syscall_entry.s's
# syscall_exit_iret, the IRETQ to a non-canonical user RIP. It faults with
# the kernel's CS but after the exit's swapgs, so GS is already the user's.
# exceptions.ritz treats it as the user's fault.
.macro SWAPGS_IF_USER_ERR
    testq $3, 16(%rsp)
    jnz 7f
    pushq %rax
    leaq syscall_exit_iret(%rip), %rax
    cmpq %rax, 16(%rsp)          # RIP, past the error code and saved RAX
    popq %rax                    # popq leaves the flags alone
    jne 8f
7:
    swapgs
8:
.endm

# ============================================================================
# Paranoid entry: NMI and #MC decide by GS_BASE, not CS (AGAST #4612)
# ============================================================================
# An NMI or #MC is not masked by IF, so it can land where the CPU is in ring
# 0 with the user's GS: between an exit's swapgs and its sysretq/iretq
# (syscall_entry.s, jump_to_userspace, the ISR exits below) or between
# SYSCALL and syscall_entry's first swapgs. The frame's CS is the kernel's
# there, so SWAPGS_IF_USER would not swap and the handler would run on the
# user's GS_BASE. Like Linux's paranoid_entry, these read MSR_GS_BASE: a
# value that is not one of syscall_entry.s's percpu_areas is the user's, so
# swapgs, and note it in %ebx (callee-saved: exception_handler keeps it) to
# swap back on exit. Each runs on its own IST stack (idt.ritz, AGAST #4628).
.set MSR_GS_BASE, 0xC0000101

# The paranoid body: InterruptFrame (dummy error, vector, RAX .. R15) under
# the IRET frame at %rsp, the GS_BASE check, exception_handler, the swap
# back, and the pops; it leaves %rsp at the IRET frame. Each run decides GS
# afresh, so an NMI's repeat (below) gets it right whatever GS it repeats on.
.macro PARANOID_BODY num
    pushq $0
    pushq $\num
    pushq %rax
    pushq %rbx
    pushq %rcx
    pushq %rdx
    pushq %rsi
    pushq %rdi
    pushq %rbp
    pushq %r8
    pushq %r9
    pushq %r10
    pushq %r11
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    movl $MSR_GS_BASE, %ecx
    rdmsr
    shlq $32, %rdx
    orq %rax, %rdx               # RDX = GS_BASE
    xorl %ebx, %ebx              # no swap on exit
    leaq percpu_areas(%rip), %rax
    cmpq %rax, %rdx
    jb 1f
    leaq percpu_areas_end(%rip), %rax
    cmpq %rax, %rdx
    jb 2f                        # already this CPU's area
1:
    swapgs
    movl $1, %ebx
2:
    movq %rsp, %rdi
    call exception_handler
    testl %ebx, %ebx
    jz 3f
    swapgs                       # back to the GS it interrupted
3:
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
.endm

# #MC: the paranoid body and its IRET.
.macro ISR_PARANOID num
.global isr_stub_\num
isr_stub_\num:
    PARANOID_BODY \num
    iretq
.endm

# ============================================================================
# NMI entry: nested NMIs (AGAST #4650)
# ============================================================================
# The CPU blocks NMIs from an NMI's delivery to the next IRETQ, any IRETQ:
# one returning from a #GP/#PF/#DB taken inside the NMI handler unblocks
# them while the CPU is still on the NMI's stack. A second NMI then loads
# RSP from TSS.ist4 again, pushes its IRET frame over the first's and runs
# the handler over the first's frames; the first returns to garbage. As
# Linux's asm_exc_nmi does (arch/x86/entry/entry_64.S), a nested NMI runs no
# handler: it points the first NMI's IRET at .Lnmi_repeat and returns, and
# the first NMI runs the handler again once it is done. Slots are 8 bytes
# up from the first NMI's %rsp at .Lnmi_repeat; the top is TSS.ist4:
#
#   12-16  the CPU's IRET frame (RIP .. SS); a nested NMI overwrites it
#   11     saved RDX (scratch for the nested checks)
#   10     "NMI executing": 1 from .Lnmi_repeat until just before the IRETQ
#    5-9   the "iret" frame the IRETQ pops: copied from the outermost frame
#          on each run; a nested NMI rewrites it to return to .Lnmi_repeat
#    0-4   the "outermost" frame: the CPU's, copied once at the first NMI
#   below  PARANOID_BODY's InterruptFrame; its RIP .. SS is the outermost
#
# An NMI is nested if it came from ring 0 and:
#   * its RIP is in [.Lnmi_repeat, .Lnmi_end_repeat): the first NMI is
#     about to run the handler anyway, so just return; or
#   * "NMI executing" is set; or
#   * its RSP is on this stack and RFLAGS.DF is set: the first NMI's last
#     instructions, from its `std` (which no other code on this stack runs:
#     every entry here clears DF, and SYSCALL clears it through SFMASK) to its
#     IRETQ, which restores the frame's DF.
# A nested NMI looks at the first NMI's slots below its own %rsp, so it
# addresses them off %rdx: tools/check_no_red_zone.py rejects any operand
# below %rsp, and nothing else can push here while they are live (NMIs nest
# only as above; #MC and #DF have their own stacks).
.set KERNEL_CS, 0x08                  # arch/x86_64/gdt.ritz GDT_KERNEL_CODE
.set KERNEL_DS, 0x10                  # arch/x86_64/gdt.ritz GDT_KERNEL_DATA
.set NMI_STACK_SIZE, 4096             # percpu.ritz's IST4, gdt.ritz nmi_stack
.set RFLAGS_DF, 0x400

.global isr_stub_2
isr_stub_2:
    cld
    pushq %rdx                        # slot 11; the CPU's frame at 8(%rsp)
    testq $3, 16(%rsp)                # CS: an NMI from ring 3 nests nothing
    jnz .Lnmi_first
    leaq .Lnmi_repeat(%rip), %rdx
    cmpq %rdx, 8(%rsp)                # RIP
    jb 1f
    leaq .Lnmi_end_repeat(%rip), %rdx
    cmpq %rdx, 8(%rsp)
    jb .Lnmi_nested_out
1:
    movq %rsp, %rdx
    cmpq $1, -8(%rdx)                 # slot 10: NMI executing
    je .Lnmi_nested
    leaq 48(%rsp), %rdx               # the top of this stack
    cmpq %rdx, 32(%rsp)               # RSP
    ja .Lnmi_first
    subq $NMI_STACK_SIZE, %rdx
    cmpq %rdx, 32(%rsp)
    jb .Lnmi_first
    testq $RFLAGS_DF, 24(%rsp)        # RFLAGS
    jz .Lnmi_first
.Lnmi_nested:
    lock incl nmi_repeats_latched(%rip)
    subq $8, %rsp                     # slot 10
    movq %rsp, %rdx
    subq $80, %rdx                    # slot 0: the first NMI's %rsp at the repeat
    pushq $KERNEL_DS                  # slots 9 .. 5: the iret frame
    pushq %rdx
    pushfq                            # IF=0 and, after the cld, DF=0
    pushq $KERNEL_CS
    leaq .Lnmi_repeat(%rip), %rdx
    pushq %rdx
    addq $48, %rsp                    # slot 11
.Lnmi_nested_out:
    popq %rdx
    iretq

.Lnmi_first:
    movq (%rsp), %rdx                 # slot 11 keeps a copy; unused from here
    pushq $0                          # slot 10: NMI executing
    subq $40, %rsp                    # slots 5-9: the iret frame
    .rept 5
    pushq 88(%rsp)                    # slots 4 .. 0 from 16 .. 12
    .endr
.Lnmi_repeat:
    # The first NMI's IRETQ returns here when a nested NMI rewrote the iret
    # frame: every GPR is as the NMI interrupted it, so the copy uses no
    # register. A POP's memory operand off %rsp is taken after the pop.
    movq $1, 80(%rsp)                 # NMI executing
    .rept 5
    popq 32(%rsp)                     # outermost slot k -> iret slot k + 5
    .endr
    subq $40, %rsp                    # slot 0
.Lnmi_end_repeat:
    PARANOID_BODY 2
    addq $40, %rsp                    # slot 5: the iret frame
    std                               # see "RFLAGS.DF" above
    movq $0, 40(%rsp)                 # slot 10: no longer executing
    iretq


# ============================================================================
# Common ISR Handler
# ============================================================================

# Called after registers are saved
# RSP points to InterruptFrame
.global isr_common
isr_common:
    # Call the Ritz exception handler
    # RDI = pointer to InterruptFrame (first argument in System V ABI)
    movq %rsp, %rdi
    call exception_handler

    # Restore all general-purpose registers
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

    # Remove vector and error code from stack
    addq $16, %rsp

    # Return to user: restore the user's GS (see SWAPGS_IF_USER).
    SWAPGS_IF_USER

    # Return from interrupt
    iretq

# ============================================================================
# Common IRQ Handler
# ============================================================================

.global irq_common
irq_common:
    # Call the Ritz IRQ handler
    movq %rsp, %rdi
    call irq_handler

    # Restore all general-purpose registers
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

    # Remove vector and error code from stack
    addq $16, %rsp

    # Return to user: restore the user's GS (see SWAPGS_IF_USER).
    SWAPGS_IF_USER

    # Return from interrupt
    iretq

# ============================================================================
# Macro for ISR stub WITHOUT error code
# ============================================================================

.macro ISR_NOERR num
.global isr_stub_\num
isr_stub_\num:
    SWAPGS_IF_USER
    # Push dummy error code (0)
    pushq $0
    # Push interrupt vector number
    pushq $\num
    # Save all general-purpose registers
    pushq %rax
    pushq %rbx
    pushq %rcx
    pushq %rdx
    pushq %rsi
    pushq %rdi
    pushq %rbp
    pushq %r8
    pushq %r9
    pushq %r10
    pushq %r11
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    # Jump to common handler
    jmp isr_common
.endm

# ============================================================================
# Macro for ISR stub WITH error code (CPU pushes error code)
# ============================================================================

.macro ISR_ERR num
.global isr_stub_\num
isr_stub_\num:
    SWAPGS_IF_USER_ERR
    # Error code already pushed by CPU
    # Push interrupt vector number
    pushq $\num
    # Save all general-purpose registers
    pushq %rax
    pushq %rbx
    pushq %rcx
    pushq %rdx
    pushq %rsi
    pushq %rdi
    pushq %rbp
    pushq %r8
    pushq %r9
    pushq %r10
    pushq %r11
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    # Jump to common handler
    jmp isr_common
.endm

# ============================================================================
# Macro for IRQ stub
# ============================================================================

.macro IRQ_STUB num irq
.global irq_stub_\num
irq_stub_\num:
    SWAPGS_IF_USER
    # Push dummy error code
    pushq $0
    # Push vector number (32 + IRQ number)
    pushq $\irq
    # Save all general-purpose registers
    pushq %rax
    pushq %rbx
    pushq %rcx
    pushq %rdx
    pushq %rsi
    pushq %rdi
    pushq %rbp
    pushq %r8
    pushq %r9
    pushq %r10
    pushq %r11
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    # Jump to common IRQ handler
    jmp irq_common
.endm

# ============================================================================
# Exception ISR Stubs (0-31)
# ============================================================================

# Exceptions WITHOUT error code
ISR_NOERR 0     # Divide Error
ISR_NOERR 1     # Debug
# Vector 2, NMI: isr_stub_2 above (paranoid, nested NMIs, AGAST #4612/#4650)
ISR_NOERR 3     # Breakpoint
ISR_NOERR 4     # Overflow
ISR_NOERR 5     # Bound Range Exceeded
ISR_NOERR 6     # Invalid Opcode
ISR_NOERR 7     # Device Not Available
ISR_ERR   8     # Double Fault (has error code)
ISR_NOERR 9     # Coprocessor Segment Overrun (reserved)
ISR_ERR   10    # Invalid TSS (has error code)
ISR_ERR   11    # Segment Not Present (has error code)
ISR_ERR   12    # Stack-Segment Fault (has error code)
ISR_ERR   13    # General Protection Fault (has error code)
ISR_ERR   14    # Page Fault (has error code)
ISR_NOERR 15    # Reserved
ISR_NOERR 16    # x87 Floating-Point Exception
ISR_ERR   17    # Alignment Check (has error code)
ISR_PARANOID 18 # Machine Check (paranoid)
ISR_NOERR 19    # SIMD Floating-Point Exception
ISR_NOERR 20    # Virtualization Exception
ISR_ERR   21    # Control Protection Exception (has error code)
ISR_NOERR 22    # Reserved
ISR_NOERR 23    # Reserved
ISR_NOERR 24    # Reserved
ISR_NOERR 25    # Reserved
ISR_NOERR 26    # Reserved
ISR_NOERR 27    # Reserved
ISR_NOERR 28    # Hypervisor Injection Exception
ISR_ERR   29    # VMM Communication Exception (has error code)
ISR_ERR   30    # Security Exception (has error code)
ISR_NOERR 31    # Reserved

# ============================================================================
# IRQ Stubs (mapped to vectors 32-47)
# ============================================================================

# Vector 32, the scheduler's LAPIC tick: irq_stub_timer below.
IRQ_STUB 1,  33     # IRQ1 - Keyboard
IRQ_STUB 2,  34     # IRQ2 - Cascade
IRQ_STUB 3,  35     # IRQ3 - COM2
IRQ_STUB 4,  36     # IRQ4 - COM1
IRQ_STUB 5,  37     # IRQ5 - LPT2
IRQ_STUB 6,  38     # IRQ6 - Floppy
IRQ_STUB 7,  39     # IRQ7 - LPT1 / Spurious
IRQ_STUB 8,  40     # IRQ8 - RTC
IRQ_STUB 9,  41     # IRQ9 - Free
IRQ_STUB 10, 42     # IRQ10 - Free
IRQ_STUB 11, 43     # IRQ11 - Free
IRQ_STUB 12, 44     # IRQ12 - PS/2 Mouse
IRQ_STUB 13, 45     # IRQ13 - FPU
IRQ_STUB 14, 46     # IRQ14 - Primary ATA
IRQ_STUB 15, 47     # IRQ15 - Secondary ATA

# MSI-X vectors 64-79 (drivers/msix.ritz, AGAST #1852). Same path as the
# I/O APIC IRQs: irq_handler counts them through msix_dispatch and sends EOI.
IRQ_STUB 32, 64
IRQ_STUB 33, 65
IRQ_STUB 34, 66
IRQ_STUB 35, 67
IRQ_STUB 36, 68
IRQ_STUB 37, 69
IRQ_STUB 38, 70
IRQ_STUB 39, 71
IRQ_STUB 40, 72
IRQ_STUB 41, 73
IRQ_STUB 42, 74
IRQ_STUB 43, 75
IRQ_STUB 44, 76
IRQ_STUB 45, 77
IRQ_STUB 46, 78
IRQ_STUB 47, 79

# AP call (vector 240, AGAST #4220): an IPI that makes one AP run a kernel
# function. It uses the interrupted stack (no IST), so it works on an AP that
# has no TSS.
IRQ_STUB 48, 240

# CPU-local MSI-X vectors 80-95 (drivers/msix.ritz, AGAST #4220): device
# interrupts aimed at the CPU that submitted the command, so an AP can take
# its own completion without the BSP's IST2 stack. No IST: an AP has no TSS.
IRQ_STUB 49, 80
IRQ_STUB 50, 81
IRQ_STUB 51, 82
IRQ_STUB 52, 83
IRQ_STUB 53, 84
IRQ_STUB 54, 85
IRQ_STUB 55, 86
IRQ_STUB 56, 87
IRQ_STUB 57, 88
IRQ_STUB 58, 89
IRQ_STUB 59, 90
IRQ_STUB 60, 91
IRQ_STUB 61, 92
IRQ_STUB 62, 93
IRQ_STUB 63, 94
IRQ_STUB 64, 95

# LAPIC watchdog (vector 96, AGAST #4220): the one-shot timer used by a wait
# that must wake even if its device interrupt never comes. It no longer uses
# vector 32, which belongs to the scheduler tick; once the tick runs, the
# watchdog rides the tick instead of reprogramming the timer. Its own vector
# is IST-free, so an AP without a TSS can use it.
IRQ_STUB 65, 96

# ============================================================================
# Timer IRQ stub (vector 32, AGAST #3629)
# ============================================================================
# The tick runs on IST3 (its own 4 KiB stack, gdt.ritz), never on the stack
# it interrupted. Since #4308 the compiled kernel is noredzone (and
# tools/check_no_red_zone.py enforces it), but IST3 also keeps the tick
# off hand-written asm stacks and off a syscall stack near its guard page.
# This stub itself must never touch memory below %rsp either: the checker
# scans it too.
#
# A tick from ring 3 may preempt the process (sched_tick switches kernel
# stacks), so its frames must live on the process's own kernel stack, where
# they stay while it is switched out: the stub saves %rax/%rbx on IST3
# (push, so nothing is below %rsp), copies the CPU's 5-word IRET frame from
# IST3 to the top of this CPU's kernel stack (PC_KSTACK_TOP via GS, which is
# TSS.rsp0; per-CPU, AGAST #4192) and continues there. A tick from
# ring 0 never switches, so it stays on IST3. IF=0 throughout (interrupt
# gate), and nothing else runs on IST3 (NMI, #MC and #DF have their own).
.global irq_stub_timer
irq_stub_timer:
    SWAPGS_IF_USER              # before any per-CPU access (AGAST #4192)
    testq $3, 8(%rsp)            # CS of the interrupted code
    jz 1f
    pushq %rax                   # IRET frame now starts at 16(%rsp)
    pushq %rbx
    movq %gs:PC_KSTACK_TOP, %rax
    subq $40, %rax
    movq 16(%rsp), %rbx          # RIP
    movq %rbx, 0(%rax)
    movq 24(%rsp), %rbx          # CS
    movq %rbx, 8(%rax)
    movq 32(%rsp), %rbx          # RFLAGS
    movq %rbx, 16(%rax)
    movq 40(%rsp), %rbx          # RSP
    movq %rbx, 24(%rax)
    movq 48(%rsp), %rbx          # SS
    movq %rbx, 32(%rax)
    movq %rsp, %rbx              # IST3: [0]=saved rbx, [8]=saved rax
    movq %rax, %rsp              # on the process's kernel stack now
    movq 8(%rbx), %rax
    movq 0(%rbx), %rbx
1:
    pushq $0                     # dummy error code
    pushq $32                    # vector
    pushq %rax
    pushq %rbx
    pushq %rcx
    pushq %rdx
    pushq %rsi
    pushq %rdi
    pushq %rbp
    pushq %r8
    pushq %r9
    pushq %r10
    pushq %r11
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    jmp irq_common

# ============================================================================
# The "nmi-gs" boot self-test's probe (AGAST #4612)
# ============================================================================
# u64 nmi_gs_probe(u64 icr_lo, u64 apic_id): sit in ring 0 on the user's GS
# (swapgs, as every exit does just before its sysretq/iretq), send this CPU
# an NMI and wait for its handler (arch/x86_64/nmi_probe.ritz, through the
# paranoid entry above) to call nmi_probe_mark. Returns GS_BASE as the NMI's
# exit left it (the user's, if the paranoid exit swapped back), then swaps
# back to this CPU's area. icr_lo is the xAPIC ICR's mapped low word, or 0
# in x2APIC mode (the ICR is then MSR 0x830). Interrupts stay off; an NMI
# ignores IF.
.set X2APIC_ICR_MSR, 0x830
.set ICR_NMI_ASSERT, 0x4400           # delivery mode NMI, level assert
.set NMI_PROBE_SPIN, 50000000

.section .bss
.align 4
nmi_repeats_latched:
    .long 0
nmi_probe_hit:
    .long 0
.section .text

.global nmi_probe_mark
.type nmi_probe_mark, @function
nmi_probe_mark:
    movl $1, nmi_probe_hit(%rip)
    ret
.size nmi_probe_mark, . - nmi_probe_mark

# void nmi_self_send(u64 icr_lo, u64 apic_id): send CPU `apic_id` (this one)
# an NMI through the xAPIC ICR at `icr_lo`, or the x2APIC ICR MSR when it is
# 0. Touches no per-CPU state, so it runs on any GS, and in an NMI handler
# ("nmi-nest", arch/x86_64/nmi_probe.ritz).
.global nmi_self_send
.type nmi_self_send, @function
nmi_self_send:
    movq %rsi, %r8                    # destination: this CPU's APIC ID
    movl $ICR_NMI_ASSERT, %eax
    testq %rdi, %rdi
    jnz 1f
    movl %r8d, %edx                   # x2APIC: destination in ICR[63:32]
    movl $X2APIC_ICR_MSR, %ecx
    wrmsr
    ret
1:
    shll $24, %r8d                    # xAPIC: destination in ICR_HI[31:24]
    movl %r8d, 0x10(%rdi)
    movl %eax, (%rdi)                 # writing ICR_LO sends it
    ret
.size nmi_self_send, . - nmi_self_send

.global nmi_gs_probe
.type nmi_gs_probe, @function
nmi_gs_probe:
    pushfq
    cli
    movl $0, nmi_probe_hit(%rip)
    swapgs                            # GS = the user's, in ring 0
    call nmi_self_send                # same arguments
    movl $NMI_PROBE_SPIN, %ecx
3:
    cmpl $0, nmi_probe_hit(%rip)
    jne 4f
    pause
    decl %ecx
    jnz 3b
4:
    movl $MSR_GS_BASE, %ecx
    rdmsr
    shlq $32, %rdx
    orq %rdx, %rax                    # GS_BASE after the NMI
    swapgs                            # back to this CPU's area
    popfq
    ret
.size nmi_gs_probe, . - nmi_gs_probe

# ============================================================================
# The "ist-nest" boot self-test's faults (AGAST #4628)
# ============================================================================
# void ist_nest_faults(u64 unmapped): called from the NMI handler while the
# test is armed (arch/x86_64/nmi_probe.ritz). A #GP (a load from a
# non-canonical address) and then a #PF (a load from `unmapped`, a kernel
# address with no page); exceptions.ritz resumes each at its _resume label.
# Both run on the stack they interrupt, here the NMI's IST stack below its
# frame; on a shared IST stack the fault would restart at its top, over the
# NMI's frame, and this `ret` would go to garbage.
.global ist_nest_faults
.global ist_nest_gp_at
.global ist_nest_gp_resume
.global ist_nest_pf_at
.global ist_nest_pf_resume
.type ist_nest_faults, @function
ist_nest_faults:
    movabsq $0x8000000000000000, %rax
ist_nest_gp_at:
    movq (%rax), %rax                 # non-canonical: #GP(0)
ist_nest_gp_resume:
ist_nest_pf_at:
    movq (%rdi), %rax                 # not present: #PF
ist_nest_pf_resume:
    ret
.size ist_nest_faults, . - ist_nest_faults

# u64 nmi_repeats(): how many NMIs isr_stub_2 has latched as nested, each
# turned into a repeat of the NMI it interrupted ("nmi-nest", AGAST #4650).
.global nmi_repeats
.type nmi_repeats, @function
nmi_repeats:
    movl nmi_repeats_latched(%rip), %eax
    ret
.size nmi_repeats, . - nmi_repeats
