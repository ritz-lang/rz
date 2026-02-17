# Embedded user program ELF binaries
#
# This file embeds userspace ELF binaries for the initramfs:
#   - init.elf:       First userspace process (runs tests, iterates /bin)
#   - hello.elf:      Simple hello world program
#   - true.elf:       Tier 1 - always exits with 0
#   - false.elf:      Tier 1 - always exits with 1
#   - exitcode.elf:   Tier 1 - exits with code 42
#   - hello_tier1.elf: Tier 1 - prints "Hello, Ritz!"
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

# ============================================================================
# true.elf - Tier 1: always exits with 0
# ============================================================================
.global true_elf_start
.global true_elf_end
.global true_elf_size

.align 16
true_elf_start:
    .incbin "build/debug/true.elf"
true_elf_end:

true_elf_size:
    .quad true_elf_end - true_elf_start

# ============================================================================
# false.elf - Tier 1: always exits with 1
# ============================================================================
.global false_elf_start
.global false_elf_end
.global false_elf_size

.align 16
false_elf_start:
    .incbin "build/debug/false.elf"
false_elf_end:

false_elf_size:
    .quad false_elf_end - false_elf_start

# ============================================================================
# exitcode.elf - Tier 1: exits with code 42
# ============================================================================
.global exitcode_elf_start
.global exitcode_elf_end
.global exitcode_elf_size

.align 16
exitcode_elf_start:
    .incbin "build/debug/exitcode.elf"
exitcode_elf_end:

exitcode_elf_size:
    .quad exitcode_elf_end - exitcode_elf_start

# ============================================================================
# hello_tier1.elf - Tier 1: prints "Hello, Ritz!"
# ============================================================================
.global hello_tier1_elf_start
.global hello_tier1_elf_end
.global hello_tier1_elf_size

.align 16
hello_tier1_elf_start:
    .incbin "build/debug/hello_tier1.elf"
hello_tier1_elf_end:

hello_tier1_elf_size:
    .quad hello_tier1_elf_end - hello_tier1_elf_start

# ============================================================================
# seq10.elf - Tier 1: prints numbers 1-10
# ============================================================================
.global seq10_elf_start
.global seq10_elf_end
.global seq10_elf_size

.align 16
seq10_elf_start:
    .incbin "build/debug/seq10.elf"
seq10_elf_end:

seq10_elf_size:
    .quad seq10_elf_end - seq10_elf_start

# ============================================================================
# cat_motd.elf - Tier 1: reads and prints /etc/motd
# ============================================================================
.global cat_motd_elf_start
.global cat_motd_elf_end
.global cat_motd_elf_size

.align 16
cat_motd_elf_start:
    .incbin "build/debug/cat_motd.elf"
cat_motd_elf_end:

cat_motd_elf_size:
    .quad cat_motd_elf_end - cat_motd_elf_start
