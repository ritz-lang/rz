# An absolute symbol for pie.s: defined in another object, so pie.s's
# pointer to it is a real R_X86_64_64, which a PIE must not relocate.
    .global fixed
    .set fixed, 0x1234
