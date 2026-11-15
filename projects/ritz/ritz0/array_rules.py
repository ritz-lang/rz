"""What an array store may not do (LANGUAGE_SPEC §3.3, LARB ruling R5, AGAST #2343).

The wording is shared: ritz1 prints the same string (ref_check.ritz), and
ritz0/test_array_store_rule.py holds all three compilers to it.
"""

# A non-literal `[N]T1` where a `[N]T2` goes. A literal takes the slot's element
# type; anything else has one already, and converting it is a loop you write.
ELEMENT_MISMATCH = "an array only fits a slot of the same element type: write a loop to convert it"

# A non-literal `[M]T` let, var or assigned into a local `[N]T`, M not N (AGAST
# #2090). ritz1's own words, from emitter_stmt.ritz. ritz0 accepted the `let`
# form and bound the `[M x T]` value under the `[N]T` name; the `var` and assign
# forms it refused only in llvmlite's words.
LENGTH_MISMATCH = "array length does not match the local array's length"

# A whole `[N]T` where a `*U` goes, `U` not `[N]T` (AGAST #2392), or alone as a
# statement (#3189). ritz1's own words, from emitter_expr_access.ritz, which
# refuses it at every slot: ritz0 says the same at the same place rather than a
# second wording for it. No "in ritz1" (#3054): all three print it.
WHOLE_ARRAY_NOT_A_VALUE = ('a whole array is not a value here (index it, copy it '
                           'into an array of the same type, or take its address with @)')

# `[]` through a reference to anything else (AGAST #2440, LARB R9).  ritz1 prints
# the same words, from index_through.ritz.
NOT_A_BUFFER = ('a reference is one value, not a buffer: '
                '`[]` needs an array, Vec, Span or String behind it')


def ref_arith(op: str, pointee: str) -> str:
    """`p + i`, `p - i`, `p += i`, `p -= i` or `p - q` with `p` an `@T` / `@&T`
    and T not an array (AGAST #3037, LARB R16).  `op` is `+` or `-`, `pointee`
    is T as Ritz spells it.  ritz1 prints the same words, from
    emitter_expr_arith.ritz."""
    return ('a reference is one value, not a buffer: '
            f'`{op}` needs a `*T`; write `(p as *{pointee}) {op} 1`')

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

# A by-value read of a move-only `a[i]`, or of a move-only field of one, with
# `a` an array held by value (AGAST #2268, Rust's E0508): the array still drops
# every element, so the value would have two owners. ritz1 prints the same
# words, from ownership.ritz.
MOVE_OUT_OF_ELEMENT = ('cannot move out of an array element: '
                       'the array still drops it; borrow it with `@a[i]`')


def uninitialised_drop_array(name: str) -> str:
    """`var a: [2]S` with no `=`, S with drop glue (LARB R39, AGAST #3376):
    an element store drops the old element, so every one must hold a value.
    ritz1 prints the same words (#3377)."""
    return f"`{name}` must be initialised: its elements have `drop`"
