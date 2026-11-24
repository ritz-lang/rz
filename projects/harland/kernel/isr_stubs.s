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
ISR_NOERR 2     # NMI
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
ISR_NOERR 18    # Machine Check
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
# gate), and nothing else runs on IST3 (NMI and #DF are IST1).
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
