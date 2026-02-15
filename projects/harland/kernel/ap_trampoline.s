# AP (Application Processor) Trampoline Code
#
# This code is copied to low memory (0x8000) and executed by each AP
# when it receives the SIPI (Startup IPI) from the BSP.
#
# Memory layout at 0x8000:
#   0x8000 - 0x8FFF: Trampoline code
#   0x8FF0: PML4 address (u32)
#   0x8FF8: Stack pointer (u64)
#   0x9000: Entry point (u64)
#
# The BSP writes these values before sending SIPI.

.set AP_TRAMPOLINE_BASE, 0x8000
.set AP_PML4_OFFSET, 0xFF0          # 0x8FF0
.set AP_STACK_OFFSET, 0xFF8         # 0x8FF8
.set AP_ENTRY_OFFSET, 0x1000        # 0x9000

# ============================================================================
# 16-bit Real Mode Entry (this is where SIPI jumps to)
# ============================================================================

.section .ap_trampoline, "ax"
.code16
.global ap_trampoline_start
.global ap_trampoline_end

ap_trampoline_start:
    cli
    cld

    # Set up segments
    xorw %ax, %ax
    movw %ax, %ds
    movw %ax, %es
    movw %ax, %ss
    movw $0x7C00, %sp       # Temporary stack

    # Enable A20 line (fast method)
    inb $0x92, %al
    orb $0x02, %al
    andb $0xFE, %al
    outb %al, $0x92

    # Load 32-bit GDT
    lgdt (ap_gdt32_ptr - ap_trampoline_start + AP_TRAMPOLINE_BASE)

    # Enable protected mode
    movl %cr0, %eax
    orl $0x01, %eax
    movl %eax, %cr0

    # Far jump to protected mode
    .byte 0x66, 0xEA                                    # ljmpl opcode
    .long ap_pm32 - ap_trampoline_start + AP_TRAMPOLINE_BASE
    .word 0x08                                          # Code segment

# ============================================================================
# 32-bit Protected Mode
# ============================================================================

.code32
ap_pm32:
    # Set up 32-bit segments
    movw $0x10, %ax
    movw %ax, %ds
    movw %ax, %es
    movw %ax, %fs
    movw %ax, %gs
    movw %ax, %ss

    # Enable PAE
    movl %cr4, %eax
    orl $(1 << 5), %eax
    movl %eax, %cr4

    # Load PML4 from fixed location
    movl (AP_TRAMPOLINE_BASE + AP_PML4_OFFSET), %eax
    movl %eax, %cr3

    # Enable long mode in EFER
    movl $0xC0000080, %ecx
    rdmsr
    orl $(1 << 8), %eax
    wrmsr

    # Enable paging
    movl %cr0, %eax
    orl $(1 << 31), %eax
    movl %eax, %cr0

    # Load 64-bit GDT
    lgdt (ap_gdt64_ptr - ap_trampoline_start + AP_TRAMPOLINE_BASE)

    # Far jump to long mode
    .byte 0xEA                                          # ljmpl opcode
    .long ap_lm64 - ap_trampoline_start + AP_TRAMPOLINE_BASE
    .word 0x08                                          # Code segment

# ============================================================================
# 64-bit Long Mode
# ============================================================================

.code64
ap_lm64:
    # Set up 64-bit segments
    movw $0x10, %ax
    movw %ax, %ds
    movw %ax, %es
    movw %ax, %fs
    movw %ax, %gs
    movw %ax, %ss

    # Load stack from fixed location
    movq (AP_TRAMPOLINE_BASE + AP_STACK_OFFSET), %rsp

    # Load entry point and call it
    movq (AP_TRAMPOLINE_BASE + AP_ENTRY_OFFSET), %rax
    call *%rax

    # Should never return, but halt if it does
ap_halt:
    cli
    hlt
    jmp ap_halt

# ============================================================================
# GDT Data (32-bit for protected mode transition)
# ============================================================================

.align 16
ap_gdt32:
    .quad 0                         # Null
    .quad 0x00CF9A000000FFFF        # 32-bit code
    .quad 0x00CF92000000FFFF        # 32-bit data
ap_gdt32_end:

ap_gdt32_ptr:
    .word ap_gdt32_end - ap_gdt32 - 1
    .long ap_gdt32 - ap_trampoline_start + AP_TRAMPOLINE_BASE

# ============================================================================
# GDT Data (64-bit)
# ============================================================================

.align 16
ap_gdt64:
    .quad 0                         # Null
    .quad 0x00AF9A000000FFFF        # 64-bit code (L=1, D=0)
    .quad 0x00CF92000000FFFF        # 64-bit data
ap_gdt64_end:

ap_gdt64_ptr:
    .word ap_gdt64_end - ap_gdt64 - 1
    .quad ap_gdt64 - ap_trampoline_start + AP_TRAMPOLINE_BASE

ap_trampoline_end:
    nop
