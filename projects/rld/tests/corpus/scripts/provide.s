# References `__provided_used`, so carry.ld's PROVIDE defines it; nothing
# references `__provided_unused`.
    .text
    .globl use_provided
use_provided:
    movq $__provided_used, %rax
    ret
