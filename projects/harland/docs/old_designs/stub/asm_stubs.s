# Harland Kernel - Assembly Stubs
#
# These functions require inline assembly. They're implemented here
# until ritz supports `asm x86_64:` blocks.
#
# All functions follow System V AMD64 ABI:
#   Args: rdi, rsi, rdx, rcx, r8, r9
#   Return: rax
#   Caller-saved: rax, rcx, rdx, rsi, rdi, r8, r9, r10, r11
#   Callee-saved: rbx, rbp, r12, r13, r14, r15

.section .text

# ============================================================================
# Port I/O
# ============================================================================

.global outb
.type outb, @function
outb:
    # outb(port: u16 [rdi], value: u8 [rsi])
    mov %di, %dx           # port in dx
    mov %sil, %al          # value in al
    out %al, %dx
    ret

.global inb
.type inb, @function
inb:
    # inb(port: u16 [rdi]) -> u8
    mov %di, %dx           # port in dx
    xor %eax, %eax         # clear rax
    in %dx, %al            # result in al
    ret

.global outw
.type outw, @function
outw:
    # outw(port: u16 [rdi], value: u16 [rsi])
    mov %di, %dx
    mov %si, %ax
    out %ax, %dx
    ret

.global inw
.type inw, @function
inw:
    # inw(port: u16 [rdi]) -> u16
    mov %di, %dx
    xor %eax, %eax
    in %dx, %ax
    ret

.global outl
.type outl, @function
outl:
    # outl(port: u32 [rdi], value: u32 [rsi])
    mov %edi, %edx
    mov %esi, %eax
    out %eax, %dx
    ret

.global inl
.type inl, @function
inl:
    # inl(port: u32 [rdi]) -> u32
    mov %edi, %edx
    xor %eax, %eax
    in %dx, %eax
    ret

# ============================================================================
# CPU Control
# ============================================================================

.global halt
.type halt, @function
halt:
    # halt() -> !  (never returns)
    cli                    # disable interrupts
.halt_loop:
    hlt                    # halt CPU
    jmp .halt_loop         # in case of NMI

.global enable_interrupts
.type enable_interrupts, @function
enable_interrupts:
    sti
    ret

.global disable_interrupts
.type disable_interrupts, @function
disable_interrupts:
    cli
    ret

# ============================================================================
# Control Register Access
# ============================================================================

.global read_cr0
.type read_cr0, @function
read_cr0:
    mov %cr0, %rax
    ret

.global write_cr0
.type write_cr0, @function
write_cr0:
    mov %rdi, %cr0
    ret

.global read_cr3
.type read_cr3, @function
read_cr3:
    mov %cr3, %rax
    ret

.global write_cr3
.type write_cr3, @function
write_cr3:
    mov %rdi, %cr3
    ret

.global read_cr4
.type read_cr4, @function
read_cr4:
    mov %cr4, %rax
    ret

.global write_cr4
.type write_cr4, @function
write_cr4:
    mov %rdi, %cr4
    ret

# ============================================================================
# MSR Access
# ============================================================================

.global rdmsr
.type rdmsr, @function
rdmsr:
    # rdmsr(msr: u32 [rdi]) -> u64
    mov %edi, %ecx         # MSR number in ecx
    rdmsr                  # result in edx:eax
    shl $32, %rdx          # shift high 32 bits
    or %rdx, %rax          # combine into rax
    ret

.global wrmsr
.type wrmsr, @function
wrmsr:
    # wrmsr(msr: u32 [rdi], value: u64 [rsi])
    mov %edi, %ecx         # MSR number in ecx
    mov %rsi, %rax         # low 32 bits in eax
    shr $32, %rsi
    mov %esi, %edx         # high 32 bits in edx
    wrmsr
    ret

# ============================================================================
# GDT/IDT Loading
# ============================================================================

.global lgdt
.type lgdt, @function
lgdt:
    # lgdt(gdtr: *GDTR [rdi])
    lgdt (%rdi)
    ret

.global lidt
.type lidt, @function
lidt:
    # lidt(idtr: *IDTR [rdi])
    lidt (%rdi)
    ret

.global ltr
.type ltr, @function
ltr:
    # ltr(selector: u16 [rdi])
    mov %di, %ax
    ltr %ax
    ret

# ============================================================================
# QEMU Debug Exit (for testing)
# ============================================================================

.global qemu_debug_exit
.type qemu_debug_exit, @function
qemu_debug_exit:
    # qemu_debug_exit(code: u32 [rdi])
    # Writes to isa-debug-exit device
    # QEMU exits with (code << 1) | 1
    mov $0xf4, %dx         # isa-debug-exit default port
    mov %edi, %eax
    out %eax, %dx
    ret
