# bcmp - LLVM optimization stub
# When LLVM sees a comparison loop, it may replace it with a call to bcmp.
# Since Ritz doesn't link with libc, we provide our own implementation.
#
# Signature: bcmp(const void *s1, const void *s2, size_t n) -> int
# Returns: 0 if equal, non-zero if different
#
# Register usage (System V AMD64 ABI):
#   %rdi = s1
#   %rsi = s2
#   %rdx = n
#   %rax = return value

    .global bcmp
    .type bcmp, @function
bcmp:
    xor %eax, %eax          # result = 0 (assume equal)
    test %rdx, %rdx         # if n == 0
    jz .Ldone               #   return 0
.Lloop:
    movzbl (%rdi), %ecx     # load byte from s1
    cmpb (%rsi), %cl        # compare with byte from s2
    jne .Lneq               # if not equal, return 1
    inc %rdi                # s1++
    inc %rsi                # s2++
    dec %rdx                # n--
    jnz .Lloop              # if n > 0, continue loop
    jmp .Ldone              # return 0
.Lneq:
    mov $1, %eax            # return 1
.Ldone:
    ret
    .size bcmp, .-bcmp
