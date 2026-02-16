# Embedded user program ELF binary
#
# This file embeds the portable_getpid.elf binary for testing syscalls.
# portable_getpid.ritz demonstrates:
# - sys_write(), sys_exit(), sys_yield(), sys_getpid()
# - Cross-platform syscall abstraction
# - Harland-specific syscall numbers
#
# The kernel can access the binary via:
#   extern fn user_elf_start()
#   extern fn user_elf_end()
#   let size = user_elf_end - user_elf_start

.section .rodata
.global user_elf_start
.global user_elf_end
.global user_elf_size

.align 16
user_elf_start:
    .incbin "build/debug/portable_getpid.elf"
user_elf_end:

# Store the size for convenience
user_elf_size:
    .quad user_elf_end - user_elf_start
