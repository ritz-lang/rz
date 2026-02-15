# Stub user ELF for when portable_getpid.elf isn't built
# Provides empty symbols to satisfy linker

.section .rodata
.global user_elf_start
.global user_elf_end
.global user_elf_size

.align 16
user_elf_start:
    .byte 0x7f, 'E', 'L', 'F'  # Minimal ELF magic
user_elf_end:

user_elf_size:
    .quad user_elf_end - user_elf_start
