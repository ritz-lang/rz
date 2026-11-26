# Synthetic .incbin fixture: no tracked .s file uses .incbin. The path is
# relative to the working directory, which is the corpus root.
    .section .rodata
    .global blob_start
blob_start:
    .incbin "synthetic/blob.bin"
blob_end:
    .align 4
    .global blob_len
blob_len:
    .long blob_end - blob_start

    .text
    .global blob_addr
    .type blob_addr, @function
blob_addr:
    leaq blob_start(%rip), %rax
    ret
    .size blob_addr, . - blob_addr
