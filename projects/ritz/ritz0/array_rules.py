"""What an array store may not do (LANGUAGE_SPEC §3.3, LARB ruling R5, AGAST #2343).

The wording is shared: ritz1 prints the same string (ref_check.ritz), and
ritz0/test_array_store_rule.py holds all three compilers to it.
"""

# A non-literal `[N]T1` where a `[N]T2` goes. A literal takes the slot's element
# type; anything else has one already, and converting it is a loop you write.
ELEMENT_MISMATCH = "an array only fits a slot of the same element type: write a loop to convert it"

# `[]` through a reference to anything else (AGAST #2440, LARB R9).  ritz1 prints
# the same words, from index_through.ritz.
NOT_A_BUFFER = ('a reference is one value, not a buffer: '
                '`[]` needs an array, Vec, Span or String behind it')

# `(*v)[i]` with `v` a Vec, Span, String or struct value, not a pointer to one
# (AGAST #2452).  ritz0 raised a Python AttributeError, ritz1 failed at clang.
# ritz1 prints the same words, from index_through.ritz.
NOT_A_POINTER = '`*x` needs `x` to be a pointer or a reference: this one is a value'

# `p[i] = b` with `p` a `*[N]T`, `@[N]T` or `@&[N]T` and `b` a whole `[N]T` (AGAST #2330,
# LARB R9).  `p[i]` is element i, a T; ritz0 stored `b` at stride `[N]T`, a row
# on.  ritz1 prints the same words, from index_through.ritz.
ELEMENT_NOT_ARRAY = ('`p[i]` is one element of the array behind `p`, '
                     'not the whole array: `*p = a` stores the array')

# `*a = v` on an `a:& [N]T` param (AGAST #2290, #2972): `*a` reads the array,
# and `a = v` is how to store it.  ritz1 prints the same words, from
# emitter_stmt.ritz.  ritz0 refused it only by raising a Python ValueError.
BORROW_DEREF_STORE = ('cannot store through `*a` of an `a:& [N]T` param '
                      '(assign to `a`, it is the array)')

# `[v; n]` with n > 1 of a move-only `v` (AGAST #2963): one value copied into n
# elements, each of which would drop it. ritz1 prints the same words, from
# ref_check.ritz.
FILL_MOVE_ONLY = ('`[v; n]` copies `v` into every element: '
                  'a move-only value fills one, `[v; 1]`')
