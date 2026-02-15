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
# Common ISR Handler
# ============================================================================

# Called after registers are saved
# RSP points to InterruptFrame
.global isr_common
isr_common:
    # Save segment registers (just in case)
    # Not strictly necessary in 64-bit mode with flat segments

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

    # Return from interrupt
    iretq

# ============================================================================
# Macro for ISR stub WITHOUT error code
# ============================================================================

.macro ISR_NOERR num
.global isr_stub_\num
isr_stub_\num:
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

IRQ_STUB 0,  32     # IRQ0 - Timer
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
