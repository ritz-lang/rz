# Synthetic branch-sizing fixture: jmp and jcc to same-section local labels
# take rel8 when the displacement fits and the near form otherwise, decided by
# growing branches until none grows, as `as` does. call is always rel32, loop
# is rel8, and a branch to a global, undefined or other-section symbol is near
# with a relocation.
    .text
    .global start
start:
    jmp fwd127                      # rel8 at the edge
    .rept 127
    nop
    .endr
fwd127:
    jmp fwd128                      # one past: near
    .rept 128
    nop
    .endr
fwd128:
    .rept 125
    nop
    .endr
    je start                        # backward, out of range
back:
    .rept 120
    nop
    .endr
    jne back                        # backward, in range
    loop back                       # rel8 only

# A chain: the first jz is in range only while the jmp inside it stays short,
# and the jmp grows because of the alignment after it.
chain:
    jz chain_end
    jmp chain_far
    .rept 100
    nop
    .endr
    .align 32
chain_end:
    .rept 30
    nop
    .endr
    .align 64
chain_far:
    call chain                      # always rel32, resolved here
    call extern_fn                  # PLT32
    jmp start                       # global: PLT32, never relaxed
    jmp other_label                 # another section: PLT32
    jz 1f
    nop
1:  jmp 1b

    .code32
c32:
    jmp c32_far
    .rept 130
    nop
    .endr
c32_far:
    jb c32
    ja c32_near
    nop
c32_near:
    call extern_fn                  # PC32

    .code16
c16:
    jmp c16_far
    .rept 200
    nop
    .endr
c16_far:
    jne c16
    jnc c16_near
    nop
c16_near:
    call extern_fn                  # PC16
    .code64

    .section .other, "ax"
other_label:
    ret
