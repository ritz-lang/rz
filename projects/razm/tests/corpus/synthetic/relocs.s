# Synthetic relocation fixture: each field and mode selects its relocation
# type, as `as` does; constants and later-defined symbols size as `as` sizes
# them.
.equ SMALL, 8

    .text
    .global entry
    .type entry, @function
entry:
    movl $ext, %esi                 # R_X86_64_32
    movq $ext, %rax                 # R_X86_64_32S
    movw $ext, %ax                  # R_X86_64_16
    movabsq $ext, %rax              # R_X86_64_64
    leaq ext(%rip), %rax            # R_X86_64_PC32
    leaq table(%rip), %rax          # local in another section
    leaq here(%rip), %rax           # local in this section: resolved
    movq ext, %rax                  # absolute memory: R_X86_64_32S
    lgdt table
    addq $SMALL, %rax               # known constant: imm8
    addq $LATER, %rax               # later constant: imm32
    movq $LATER, %rdx
    movq $len, %rcx                 # later label difference
    movl $(table_end - table), %ecx
    pushq $alias
here:
    ret
    .size entry, . - entry

    .code32
    movl $ext, %esi                 # R_X86_64_32
    movl ext, %eax                  # absolute memory: R_X86_64_32
    lgdt table
    .code16
    movw $ext, %ax                  # R_X86_64_16
    .code64

    .section .rodata
table:
    .byte ext                       # R_X86_64_8
    .word ext                       # R_X86_64_16
    .long ext                       # R_X86_64_32
    .quad ext                       # R_X86_64_64
    .quad entry + 8
    .quad here                      # local: section symbol plus offset
    .long ext - .                   # R_X86_64_PC32
    .long entry - .
    .long table - .                 # same section: a constant
    .long table_end - table
table_end:
len = table_end - table
.equ LATER, 0x1000
.set alias, table + 4
