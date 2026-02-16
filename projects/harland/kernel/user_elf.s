# Embedded user program ELF binaries
#
# This file embeds userspace ELF binaries:
#   - init.elf: First userspace process (runs tests, iterates /bin)
#   - hello.elf: Simple hello world program
#
# The kernel can access the binaries via extern declarations.

.section .rodata

# ============================================================================
# init.elf - First userspace process
# ============================================================================
.global user_elf_start
.global user_elf_end
.global user_elf_size

.align 16
user_elf_start:
    .incbin "build/debug/init.elf"
user_elf_end:

user_elf_size:
    .quad user_elf_end - user_elf_start

# ============================================================================
# hello.elf - Simple hello world program
# ============================================================================
.global hello_elf_start
.global hello_elf_end
.global hello_elf_size

.align 16
hello_elf_start:
    .incbin "build/debug/hello.elf"
hello_elf_end:

hello_elf_size:
    .quad hello_elf_end - hello_elf_start
