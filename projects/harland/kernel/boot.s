# Harland Kernel Boot Assembly
#
# Multiboot2-compliant bootloader that:
# 1. Starts in 32-bit protected mode (from GRUB)
# 2. Sets up identity-mapped page tables
# 3. Enables long mode (64-bit)
# 4. Jumps to the 64-bit Ritz kernel
#
# Assembled with: as --32 (generates ELF32 with mixed 32/64 code)

.set KERNEL_STACK_SIZE, 16384

# Higher-half kernel virtual base address
# Kernel is loaded at 1MB physical, mapped to this virtual address
.set KERNEL_VIRT_BASE, 0xFFFFFFFF80000000

# ============================================================================
# Multiboot2 Header (must be within first 32KB)
# ============================================================================

.section .multiboot, "a"
.align 8

multiboot_header:
    .long 0xE85250D6                    # Multiboot2 magic
    .long 0                             # Architecture: 0 = i386 protected mode
    .long multiboot_header_end - multiboot_header  # Header length
    .long -(0xE85250D6 + 0 + (multiboot_header_end - multiboot_header))  # Checksum

    # Framebuffer tag (optional, request linear framebuffer)
    # .align 8
    # .word 5                           # Type: framebuffer
    # .word 0                           # Flags
    # .long 20                          # Size
    # .long 1024                        # Width
    # .long 768                         # Height
    # .long 32                          # Depth

    # End tag (required)
    .align 8
    .word 0                             # Type: end
    .word 0                             # Flags
    .long 8                             # Size
multiboot_header_end:

# ============================================================================
# 32-bit Entry Point (GRUB enters here in protected mode)
# This section runs at PHYSICAL addresses (before paging is enabled)
# ============================================================================

.section .boot, "ax"
.code32

.global _start
.type _start, @function
_start:
    # Disable interrupts
    cli

    # Save Multiboot2 info pointer (EBX from GRUB)
    movl %ebx, multiboot_info_ptr

    # Set up 32-bit stack
    movl $stack32_top, %esp

    # Verify we were loaded by Multiboot2
    cmpl $0x36D76289, %eax              # Multiboot2 bootloader magic
    jne no_long_mode                     # If not, fail

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
    je no_cpuid                         # If ID bit didn't flip, no CPUID

    # Check if extended CPUID functions are available
    movl $0x80000000, %eax
    cpuid
    cmpl $0x80000001, %eax
    jb no_long_mode                     # If max < 0x80000001, no long mode check

    # Check if long mode is supported
    movl $0x80000001, %eax
    cpuid
    testl $(1 << 29), %edx              # LM bit in EDX
    jz no_long_mode

    # Set up page tables for identity mapping (first 2GB)
    call setup_page_tables

    # Enable PAE (Physical Address Extension)
    movl %cr4, %eax
    orl $(1 << 5), %eax                 # Set PAE bit
    movl %eax, %cr4

    # Load PML4 address into CR3
    movl $pml4, %eax
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

    # Load 64-bit GDT
    lgdt gdt64_ptr

    # Far jump to 64-bit code segment - this switches to long mode!
    # We use .byte encoding because the assembler in 64-bit mode
    # doesn't emit the correct 32-bit far jump.
    # ljmp $0x08, $long_mode_start
    # Encoding: EA <offset32> <segment16> (7 bytes total)
    .byte 0xEA                          # Far jump opcode
    .long long_mode_start               # 32-bit offset
    .word 0x08                          # Code segment selector

# Error handlers (32-bit)
no_cpuid:
    movl $msg_no_cpuid, %esi
    call print32
    jmp halt32

no_long_mode:
    movl $msg_no_lm, %esi
    call print32
    jmp halt32

halt32:
    cli
    hlt
    jmp halt32

# Print null-terminated string to VGA text buffer (32-bit)
# ESI = pointer to string
print32:
    pushl %eax
    pushl %edx
    movl $0xB8000, %edi                 # VGA text buffer
.print32_loop:
    lodsb                               # Load byte from ESI
    testb %al, %al                      # Check for null
    jz .print32_done
    movb $0x4F, %ah                     # White on red (error)
    stosw                               # Store char + attribute
    jmp .print32_loop
.print32_done:
    popl %edx
    popl %eax
    ret

# Set up page tables for:
# 1. Identity mapping: First 1GB at 0x00000000
# 2. Higher-half mapping: First 1GB at 0xFFFFFFFF80000000
#
# Uses 2MB huge pages for simplicity.
#
# Memory layout:
#   PML4[0]   -> pdpt_low   -> pd    (identity map 0-1GB)
#   PML4[511] -> pdpt_high  -> pd    (higher-half 0xFFFFFFFF80000000)
#
# Note: Both mappings point to the same PD, so physical 0-1GB is accessible
# via both identity addresses and higher-half addresses.
#
setup_page_tables:
    # Zero out page table memory (4 pages: PML4, pdpt_low, pdpt_high, PD)
    movl $pml4, %edi
    xorl %eax, %eax
    movl $(4096 * 4 / 4), %ecx
    rep stosl

    # ============================================
    # Identity mapping: PML4[0] -> pdpt_low -> PD
    # ============================================
    # PML4[0] -> pdpt_low
    movl $pml4, %edi
    movl $pdpt_low, %eax
    orl $0x03, %eax                     # Present + Writable
    movl %eax, (%edi)

    # pdpt_low[0] -> PD
    movl $pdpt_low, %edi
    movl $pd, %eax
    orl $0x03, %eax                     # Present + Writable
    movl %eax, (%edi)

    # ============================================
    # Higher-half mapping: PML4[511] -> pdpt_high
    # ============================================
    # Virtual address 0xFFFFFFFF80000000 breakdown:
    #   PML4 index:  511 (0x1FF) - top entry
    #   PDPT index:  510 (0x1FE) - second-to-last entry (for -2GB offset)
    #   PD index:    varies
    #
    # PML4[511] -> pdpt_high
    movl $pml4, %edi
    addl $(511 * 8), %edi               # Entry 511
    movl $pdpt_high, %eax
    orl $0x03, %eax                     # Present + Writable
    movl %eax, (%edi)
    movl $0, 4(%edi)                    # High 32 bits = 0

    # pdpt_high[510] -> PD (for 0xFFFFFFFF80000000, PDPT index is 510)
    movl $pdpt_high, %edi
    addl $(510 * 8), %edi               # Entry 510
    movl $pd, %eax
    orl $0x03, %eax                     # Present + Writable
    movl %eax, (%edi)
    movl $0, 4(%edi)                    # High 32 bits = 0

    # ============================================
    # PD: Map first 1GB using 2MB pages (512 entries)
    # ============================================
    # This PD is shared by both identity and higher-half mappings.
    movl $pd, %edi
    movl $0x83, %eax                    # Present + Writable + Huge (2MB)
    movl $512, %ecx                     # 512 * 2MB = 1GB
.setup_pd_loop:
    movl %eax, (%edi)
    movl $0, 4(%edi)                    # High 32 bits = 0
    addl $0x200000, %eax                # Next 2MB page
    addl $8, %edi                       # Next PD entry (8 bytes)
    loop .setup_pd_loop

    ret

# ============================================================================
# 64-bit Entry Point (after long mode is active)
# ============================================================================

.code64

long_mode_start:
    # Reload all data segment registers with 64-bit data segment
    movw $0x10, %ax                     # Data segment selector
    movw %ax, %ds
    movw %ax, %es
    movw %ax, %fs
    movw %ax, %gs
    movw %ax, %ss

    # Set up 64-bit stack (use identity-mapped address for now)
    movl $stack_top, %esp
    movq %rsp, %rsp                     # Zero-extend to 64-bit

    # Initialize serial port (COM1) - using identity-mapped addresses
    call serial_init64

    # Print boot message to serial
    lea msg_boot(%rip), %rdi
    call serial_print64

    # Print debug - about to call kernel
    lea msg_calling_kernel(%rip), %rdi
    call serial_print64

    # Now jump to higher-half address space
    # We have both identity and higher-half mappings active, so we can
    # use an absolute jump to transition.
    movabsq $higher_half_entry, %rax
    jmp *%rax

# Entry point after jumping to higher-half address space
higher_half_entry:
    # Now we're running from higher-half addresses!
    # Update stack to higher-half address
    # stack_top is at physical ~0x110000, which maps to virtual 0xFFFFFFFF80110000
    movabsq $KERNEL_VIRT_BASE, %rax
    movl $stack_top, %ecx               # Physical address of stack
    addq %rcx, %rax                     # Higher-half stack address
    movq %rax, %rsp

    # Print message that we're in higher-half
    lea msg_higher_half(%rip), %rdi
    call serial_print64

    # Call the Ritz kernel main
    # RDI = Multiboot2 info pointer (still 32-bit physical address)
    movl multiboot_info_ptr(%rip), %edi
    call kernel_main

    # If we get here, kernel returned - manually output 'K' to serial
    movw $0x3FD, %dx
1:  inb %dx, %al
    testb $0x20, %al
    jz 1b
    movb $'K', %al
    movw $0x3F8, %dx
    outb %al, %dx

    # Print debug - kernel returned
    lea msg_kernel_returned(%rip), %rdi
    call serial_print64

    # If kernel returns, print error and halt
    lea msg_returned(%rip), %rdi
    call serial_print64

halt64:
    cli
    hlt
    jmp halt64

# Initialize COM1 serial port at 115200 baud, 8N1
serial_init64:
    # Disable all interrupts
    movw $0x3F9, %dx
    xorb %al, %al
    outb %al, %dx

    # Enable DLAB (set baud rate divisor)
    movw $0x3FB, %dx
    movb $0x80, %al
    outb %al, %dx

    # Set divisor to 1 (115200 baud)
    movw $0x3F8, %dx
    movb $0x01, %al
    outb %al, %dx
    movw $0x3F9, %dx
    xorb %al, %al
    outb %al, %dx

    # 8 bits, no parity, one stop bit (8N1)
    movw $0x3FB, %dx
    movb $0x03, %al
    outb %al, %dx

    # Enable FIFO, clear them, with 14-byte threshold
    movw $0x3FA, %dx
    movb $0xC7, %al
    outb %al, %dx

    # Enable IRQs, RTS/DSR set
    movw $0x3FC, %dx
    movb $0x0B, %al
    outb %al, %dx

    ret

# Print null-terminated string to serial port (64-bit)
# RDI = pointer to string
serial_print64:
    pushq %rax
    pushq %rdx
.serial_print64_loop:
    movb (%rdi), %al
    testb %al, %al
    jz .serial_print64_done

    # Wait for transmitter to be ready
.serial_wait64:
    movw $0x3FD, %dx
    inb %dx, %al
    testb $0x20, %al                    # Transmitter empty?
    jz .serial_wait64

    # Send character
    movb (%rdi), %al
    movw $0x3F8, %dx
    outb %al, %dx

    incq %rdi
    jmp .serial_print64_loop

.serial_print64_done:
    popq %rdx
    popq %rax
    ret

# ============================================================================
# Boot Data Section (physical addresses, used by boot code)
# ============================================================================

.section .boot.data, "aw"

.align 4
multiboot_info_ptr:
    .long 0

msg_no_cpuid:
    .asciz "ERROR: CPUID not supported\n"

msg_no_lm:
    .asciz "ERROR: Long mode not supported\n"

msg_boot:
    .asciz "Harland bootloader: Long mode active\n"

msg_returned:
    .asciz "ERROR: Kernel returned!\n"

msg_calling_kernel:
    .asciz "Bootloader: Calling kernel_main...\n"

msg_kernel_returned:
    .asciz "Bootloader: kernel_main returned.\n"

msg_higher_half:
    .asciz "Bootloader: Running in higher-half address space\n"

# 64-bit GDT
.align 16
gdt64:
    .quad 0                             # Null descriptor
    # Code segment: base=0, limit=max, type=code execute/read, DPL=0, P=1, L=1
    .quad 0x00AF9A000000FFFF
    # Data segment: base=0, limit=max, type=data read/write, DPL=0, P=1
    .quad 0x00CF92000000FFFF
gdt64_end:

gdt64_ptr:
    .word gdt64_end - gdt64 - 1         # Limit
    .quad gdt64                         # Base (64-bit)

# ============================================================================
# Boot BSS Section (physical addresses, page tables and stacks)
# ============================================================================

.section .boot.bss, "aw", @nobits
.align 4096

# Page tables (must be page-aligned)
pml4:       .space 4096
pdpt_low:   .space 4096     # For identity mapping (PML4[0])
pdpt_high:  .space 4096     # For higher-half mapping (PML4[511])
pd:         .space 4096     # Shared by both mappings

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
