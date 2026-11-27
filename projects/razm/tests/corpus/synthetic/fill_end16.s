# Synthetic fill fixture for a file that ends in .code16: `as` writes every
# alignment fill at the end, so a long fill's rel32 jump takes a 0x66 prefix
# in every section, whatever the mode at its `.align`.
    .text
    .code64
    .rept 56
    hlt
    .endr
    .align 256                      # 200 bytes: 66 e9 rel32, then nops
    .code16
    .rept 56
    hlt
    .endr
    .align 256
    hlt
