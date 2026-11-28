# Assembled with -mrelax-relocations=no: a plain R_X86_64_GOTPCREL, which
# ld.lld never relaxes, so `value` gets a GOT entry.
    .text
    .global norelax_value
    .type norelax_value, @function
norelax_value:
    movq value@GOTPCREL(%rip), %rax
    movq (%rax), %rax
    ret
