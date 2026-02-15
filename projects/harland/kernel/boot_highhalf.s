# Harland Kernel Boot Assembly - True Higher-Half
#
# Multiboot2-compliant bootloader that:
# 1. Starts in 32-bit protected mode (from GRUB)
# 2. Sets up identity-mapped page tables for boot
# 3. Enables long mode (64-bit)
# 4. Jumps to the higher-half kernel
#
# Key difference from flat boot.s:
# - Boot code (.boot section) runs at PHYSICAL addresses
# - Kernel code (.text section) runs at VIRTUAL higher-half addresses
# - The transition happens after paging is enabled

.set KERNEL_STACK_SIZE, 16384

# Higher-half kernel virtual base address
.set KERNEL_VIRT_BASE, 0xFFFFFFFF80000000

# ============================================================================
# Multiboot2 Header (must be within first 32KB)
# Section: .multiboot - physical addresses, no relocation
# ============================================================================

.section .multiboot, "a"
.align 8

multiboot_header:
    .long 0xE85250D6                    # Multiboot2 magic
    .long 0                             # Architecture: 0 = i386 protected mode
    .long multiboot_header_end - multiboot_header  # Header length
    .long -(0xE85250D6 + 0 + (multiboot_header_end - multiboot_header))  # Checksum

    # End tag (required)
    .align 8
    .word 0                             # Type: end
    .word 0                             # Flags
    .long 8                             # Size
multiboot_header_end:

# ============================================================================
# BOOT SECTION - Runs at PHYSICAL addresses before paging
# This code MUST be position-independent or use physical addresses only
# ============================================================================

.section .boot, "ax"
.code32

.global _start
.type _start, @function
_start:
    # Disable interrupts
    cli

    # Save Multiboot2 info pointer (EBX from GRUB)
    movl %ebx, (multiboot_info_ptr - KERNEL_VIRT_BASE)

    # Set up 32-bit stack (physical address)
    movl $(stack32_top - KERNEL_VIRT_BASE), %esp

    # Verify we were loaded by Multiboot2
    cmpl $0x36D76289, %eax              # Multiboot2 bootloader magic
    jne .no_long_mode

    # Check CPUID is available by trying to flip ID bit in EFLAGS
    pushfl
    popl %eax
    movl %eax, %ecx
    xorl $0x200000, %eax                # Flip ID bit (bit 21)
    pushl %eax
    popfl
    pushfl
    popl %eax
    pushl %ecx                          # Restore original EFLAGS
    popfl
    cmpl %ecx, %eax
    je .no_cpuid

    # Check if extended CPUID functions are available
    movl $0x80000000, %eax
    cpuid
    cmpl $0x80000001, %eax
    jb .no_long_mode

    # Check if long mode is supported
    movl $0x80000001, %eax
    cpuid
    testl $(1 << 29), %edx              # LM bit in EDX
    jz .no_long_mode

    # Set up page tables for:
    # - Identity mapping: 0-1GB -> 0-1GB (for boot)
    # - Higher-half mapping: 0xFFFFFFFF80000000 -> 0-1GB (for kernel)
    call .setup_page_tables

    # Enable PAE (Physical Address Extension)
    movl %cr4, %eax
    orl $(1 << 5), %eax                 # Set PAE bit
    movl %eax, %cr4

    # Load PML4 address into CR3
    movl $(pml4 - KERNEL_VIRT_BASE), %eax
    movl %eax, %cr3

    # Enable long mode in EFER MSR
    movl $0xC0000080, %ecx              # EFER MSR number
    rdmsr
    orl $(1 << 8), %eax                 # Set LME (Long Mode Enable)
    wrmsr

    # Enable paging (activates long mode)
    movl %cr0, %eax
    orl $(1 << 31), %eax                # Set PG (Paging)
    movl %eax, %cr0

    # Load 64-bit GDT (use physical address)
    lgdt (gdt64_ptr - KERNEL_VIRT_BASE)

    # Far jump to 64-bit code segment
    # We jump to physical address first, then transition to higher-half
    .byte 0xEA                          # Far jump opcode
    .long (.long_mode_start - KERNEL_VIRT_BASE)  # Physical address
    .word 0x08                          # Code segment selector

# Error handlers (32-bit, in boot section)
.no_cpuid:
    movl $(.msg_no_cpuid - KERNEL_VIRT_BASE), %esi
    call .print32
    jmp .halt32

.no_long_mode:
    movl $(.msg_no_lm - KERNEL_VIRT_BASE), %esi
    call .print32
    jmp .halt32

.halt32:
    cli
    hlt
    jmp .halt32

# Print null-terminated string to VGA text buffer (32-bit)
.print32:
    pushl %eax
    pushl %edx
    movl $0xB8000, %edi
.print32_loop:
    lodsb
    testb %al, %al
    jz .print32_done
    movb $0x4F, %ah                     # White on red (error)
    stosw
    jmp .print32_loop
.print32_done:
    popl %edx
    popl %eax
    ret

# Set up page tables (32-bit, boot section)
# Uses physical addresses for everything
.setup_page_tables:
    # Zero out page table memory
    movl $(pml4 - KERNEL_VIRT_BASE), %edi
    xorl %eax, %eax
    movl $(4096 * 4 / 4), %ecx
    rep stosl

    # PML4[0] -> pdpt_low (identity mapping)
    movl $(pml4 - KERNEL_VIRT_BASE), %edi
    movl $(pdpt_low - KERNEL_VIRT_BASE), %eax
    orl $0x03, %eax                     # Present + Writable
    movl %eax, (%edi)

    # pdpt_low[0] -> PD
    movl $(pdpt_low - KERNEL_VIRT_BASE), %edi
    movl $(pd - KERNEL_VIRT_BASE), %eax
    orl $0x03, %eax
    movl %eax, (%edi)

    # PML4[511] -> pdpt_high (higher-half mapping)
    movl $(pml4 - KERNEL_VIRT_BASE), %edi
    addl $(511 * 8), %edi
    movl $(pdpt_high - KERNEL_VIRT_BASE), %eax
    orl $0x03, %eax
    movl %eax, (%edi)
    movl $0, 4(%edi)

    # pdpt_high[510] -> PD (for 0xFFFFFFFF80000000)
    movl $(pdpt_high - KERNEL_VIRT_BASE), %edi
    addl $(510 * 8), %edi
    movl $(pd - KERNEL_VIRT_BASE), %eax
    orl $0x03, %eax
    movl %eax, (%edi)
    movl $0, 4(%edi)

    # PD: Map first 1GB using 2MB huge pages (shared by both mappings)
    movl $(pd - KERNEL_VIRT_BASE), %edi
    movl $0x83, %eax                    # Present + Writable + Huge
    movl $512, %ecx
.setup_pd_loop:
    movl %eax, (%edi)
    movl $0, 4(%edi)
    addl $0x200000, %eax                # Next 2MB
    addl $8, %edi
    loop .setup_pd_loop
    ret

# ============================================================================
# 64-bit Long Mode Entry (still in boot section, physical addresses)
# ============================================================================

.code64

.long_mode_start:
    # Reload segment registers
    movw $0x10, %ax
    movw %ax, %ds
    movw %ax, %es
    movw %ax, %fs
    movw %ax, %gs
    movw %ax, %ss

    # Set up 64-bit stack (still physical address)
    movl $(stack_top - KERNEL_VIRT_BASE), %esp
    movq %rsp, %rsp

    # Initialize serial port (COM1)
    call .serial_init64

    # Print boot message
    lea (.msg_boot - KERNEL_VIRT_BASE)(%rip), %rdi
    call .serial_print64

    # Now jump to higher-half!
    # We use an absolute jump with the virtual address
    movabsq $higher_half_entry, %rax
    jmp *%rax

# Serial init (boot section, uses I/O ports directly)
.serial_init64:
    movw $0x3F9, %dx
    xorb %al, %al
    outb %al, %dx
    movw $0x3FB, %dx
    movb $0x80, %al
    outb %al, %dx
    movw $0x3F8, %dx
    movb $0x01, %al
    outb %al, %dx
    movw $0x3F9, %dx
    xorb %al, %al
    outb %al, %dx
    movw $0x3FB, %dx
    movb $0x03, %al
    outb %al, %dx
    movw $0x3FA, %dx
    movb $0xC7, %al
    outb %al, %dx
    movw $0x3FC, %dx
    movb $0x0B, %al
    outb %al, %dx
    ret

# Serial print (boot section)
.serial_print64:
    pushq %rax
    pushq %rdx
.serial_print64_loop:
    movb (%rdi), %al
    testb %al, %al
    jz .serial_print64_done
.serial_wait64:
    movw $0x3FD, %dx
    inb %dx, %al
    testb $0x20, %al
    jz .serial_wait64
    movb (%rdi), %al
    movw $0x3F8, %dx
    outb %al, %dx
    incq %rdi
    jmp .serial_print64_loop
.serial_print64_done:
    popq %rdx
    popq %rax
    ret

# Boot section strings (physical addresses)
.msg_no_cpuid:
    .asciz "ERROR: CPUID not supported\n"
.msg_no_lm:
    .asciz "ERROR: Long mode not supported\n"
.msg_boot:
    .asciz "Harland bootloader: Long mode active\n"

# ============================================================================
# KERNEL TEXT SECTION - Runs at VIRTUAL higher-half addresses
# This code runs AFTER paging is enabled with higher-half mapping
# ============================================================================

.section .text
.code64

.global higher_half_entry
higher_half_entry:
    # Now running from higher-half addresses!
    # Update stack to higher-half virtual address
    movabsq $stack_top, %rsp

    # Print message that we're in higher-half
    lea msg_higher_half(%rip), %rdi
    call serial_print64_hh

    # Call the Ritz kernel main
    # RDI = Multiboot2 info pointer (physical address)
    movl multiboot_info_ptr(%rip), %edi
    call kernel_main

    # If kernel returns, print error and halt
    lea msg_kernel_returned(%rip), %rdi
    call serial_print64_hh
    lea msg_returned(%rip), %rdi
    call serial_print64_hh

halt64:
    cli
    hlt
    jmp halt64

# Serial print for higher-half code
serial_print64_hh:
    pushq %rax
    pushq %rdx
.serial_print64_hh_loop:
    movb (%rdi), %al
    testb %al, %al
    jz .serial_print64_hh_done
.serial_wait64_hh:
    movw $0x3FD, %dx
    inb %dx, %al
    testb $0x20, %al
    jz .serial_wait64_hh
    movb (%rdi), %al
    movw $0x3F8, %dx
    outb %al, %dx
    incq %rdi
    jmp .serial_print64_hh_loop
.serial_print64_hh_done:
    popq %rdx
    popq %rax
    ret

# ============================================================================
# Data Section (virtual addresses, but loaded at physical)
# ============================================================================

.section .data

.align 4
multiboot_info_ptr:
    .long 0

msg_higher_half:
    .asciz "Bootloader: Running in higher-half address space\n"

msg_kernel_returned:
    .asciz "Bootloader: kernel_main returned.\n"

msg_returned:
    .asciz "ERROR: Kernel returned!\n"

# 64-bit GDT
.align 16
gdt64:
    .quad 0                             # Null descriptor
    .quad 0x00AF9A000000FFFF            # Code segment (64-bit)
    .quad 0x00CF92000000FFFF            # Data segment
gdt64_end:

gdt64_ptr:
    .word gdt64_end - gdt64 - 1         # Limit
    .quad gdt64                         # Base (will be virtual address)

# Also provide physical address version for boot code
.section .boot
gdt64_ptr_phys:
    .word gdt64_end - gdt64 - 1
    .quad (gdt64 - KERNEL_VIRT_BASE)

# ============================================================================
# BSS Section (virtual addresses)
# ============================================================================

.section .bss
.align 4096

# Page tables
pml4:       .space 4096
pdpt_low:   .space 4096
pdpt_high:  .space 4096
pd:         .space 4096

# 32-bit bootstrap stack
.align 16
stack32_bottom:
    .space 4096
stack32_top:

# Main 64-bit kernel stack
.align 16
stack_bottom:
    .space KERNEL_STACK_SIZE
stack_top:
