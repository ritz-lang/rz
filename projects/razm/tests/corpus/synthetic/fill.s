# Synthetic alignment-fill fixture: GNU as's multi-byte nop sequences in an
# executable section, per mode, after an instruction and after data; zeros
# elsewhere. Each case pads to the next 256-byte boundary.

.macro AFTER_INSN n
    .align 256
    .rept 256 - \n
    hlt
    .endr
    .align 256
.endm

.macro AFTER_DATA n
    .align 256
    .space 256 - \n, 0xcc
    .align 256
.endm

    .text
    .code64
    AFTER_INSN 1
    AFTER_INSN 2
    AFTER_INSN 3
    AFTER_INSN 4
    AFTER_INSN 5
    AFTER_INSN 6
    AFTER_INSN 7
    AFTER_INSN 8
    AFTER_INSN 9
    AFTER_INSN 10
    AFTER_INSN 11
    AFTER_INSN 12
    AFTER_INSN 13
    AFTER_INSN 14
    AFTER_INSN 15
    AFTER_INSN 16
    AFTER_INSN 22
    AFTER_INSN 23
    AFTER_INSN 33
    AFTER_INSN 77
    AFTER_INSN 87
    AFTER_INSN 88
    AFTER_INSN 89
    AFTER_INSN 129
    AFTER_INSN 130
    AFTER_INSN 255
    AFTER_DATA 1
    AFTER_DATA 3
    AFTER_DATA 12
    AFTER_DATA 88
    AFTER_DATA 89
    AFTER_DATA 131
    .code32
    AFTER_INSN 1
    AFTER_INSN 2
    AFTER_INSN 3
    AFTER_INSN 4
    AFTER_INSN 5
    AFTER_INSN 6
    AFTER_INSN 7
    AFTER_INSN 8
    AFTER_INSN 9
    AFTER_INSN 10
    AFTER_INSN 11
    AFTER_INSN 12
    AFTER_INSN 13
    AFTER_INSN 14
    AFTER_INSN 15
    AFTER_INSN 16
    AFTER_INSN 22
    AFTER_INSN 23
    AFTER_INSN 33
    AFTER_INSN 77
    AFTER_INSN 87
    AFTER_INSN 88
    AFTER_INSN 89
    AFTER_INSN 129
    AFTER_INSN 130
    AFTER_INSN 255
    AFTER_DATA 1
    AFTER_DATA 3
    AFTER_DATA 12
    AFTER_DATA 88
    AFTER_DATA 89
    AFTER_DATA 131
    .code16
    AFTER_INSN 1
    AFTER_INSN 2
    AFTER_INSN 3
    AFTER_INSN 4
    AFTER_INSN 5
    AFTER_INSN 6
    AFTER_INSN 7
    AFTER_INSN 8
    AFTER_INSN 9
    AFTER_INSN 10
    AFTER_INSN 11
    AFTER_INSN 12
    AFTER_INSN 13
    AFTER_INSN 14
    AFTER_INSN 15
    AFTER_INSN 16
    AFTER_INSN 22
    AFTER_INSN 23
    AFTER_INSN 33
    AFTER_INSN 77
    AFTER_INSN 87
    AFTER_INSN 88
    AFTER_INSN 89
    AFTER_INSN 129
    AFTER_INSN 130
    AFTER_INSN 255
    AFTER_DATA 1
    AFTER_DATA 3
    AFTER_DATA 12
    AFTER_DATA 88
    AFTER_DATA 89
    AFTER_DATA 131
    .code64
    hlt
    .align 4
    .align 16                       # an alignment counts as data
    hlt

    .section .rodata
    .byte 1
    .align 64
    .byte 2

    .section .razm_misc
    hlt
    .align 8
    .byte 3

    .bss
    .space 3
    .align 32
    .space 5
