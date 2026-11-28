# Defines `_start` strongly: linked twice, it is a duplicate.
    .text
    .global _start
_start:
    ret
