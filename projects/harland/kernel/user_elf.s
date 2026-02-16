# Embedded user program ELF binary
#
# This file embeds the init.elf binary - the first userspace process.
# init.ritz:
# - Runs system tests (sys_write, sys_getpid, sys_yield)
# - Reports test results
# - Triggers ACPI poweroff on success
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
    .incbin "build/debug/init.elf"
user_elf_end:

# Store the size for convenience
user_elf_size:
    .quad user_elf_end - user_elf_start
