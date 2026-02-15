# First Harland Userspace Program
#
# A minimal user program that:
# 1. Makes a SYS_DEBUG_PRINT syscall to print a message
# 2. Makes a SYS_EXIT syscall to terminate
#
# This program runs in Ring 3 (user mode).

.section .text

# Syscall numbers (must match kernel/src/arch/x86_64/syscall.ritz)
.equ SYS_WRITE,       1
.equ SYS_EXIT,        20
.equ SYS_DEBUG_PRINT, 255

# ============================================================================
# User Program Entry Point
# ============================================================================
.global user_program_start
.type user_program_start, @function
user_program_start:
    # Print "Hello from userspace!" using SYS_DEBUG_PRINT
    # syscall(SYS_DEBUG_PRINT, buf, len)

    movq $SYS_DEBUG_PRINT, %rax  # Syscall number
    leaq user_message(%rip), %rdi # Arg1: buffer pointer
    movq $user_message_len, %rsi  # Arg2: length
    syscall

    # Print newline
    movq $SYS_DEBUG_PRINT, %rax
    leaq user_newline(%rip), %rdi
    movq $1, %rsi
    syscall

    # Exit with code 42 (so we know it worked!)
    movq $SYS_EXIT, %rax          # Syscall number
    movq $42, %rdi                # Exit code
    syscall

    # Should never reach here
    hlt
    jmp .

.size user_program_start, . - user_program_start

# Mark the end of the user program (for size calculation)
.global user_program_end
user_program_end:

# ============================================================================
# User Program Data
# ============================================================================
.section .rodata

user_message:
    .ascii "Hello from Harland userspace!"
user_message_len = . - user_message

user_newline:
    .byte 10  # '\n'

# ============================================================================
# Alternative: Minimal Test Program
# ============================================================================
# If the above doesn't work, here's an even simpler version
# that just exits immediately:

.section .text
.global user_program_minimal
.type user_program_minimal, @function
user_program_minimal:
    # Just exit with code 0
    movq $20, %rax                # SYS_EXIT
    xorq %rdi, %rdi               # code = 0
    syscall
    hlt

.size user_program_minimal, . - user_program_minimal
