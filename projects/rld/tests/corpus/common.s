# A SHN_COMMON symbol, which no producer in the tree emits.
    .comm shared, 8, 8
    .text
    .global _start
_start:
    ret
