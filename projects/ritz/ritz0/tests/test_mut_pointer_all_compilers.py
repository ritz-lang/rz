"""AGAST #3930: `*mut T` (LANGUAGE_SPEC §5), the same on all three compilers.

ritz1 and ritz1_selfhosted refused `fn raw(p: *mut i32)` with
`unexpected 'mut'`; ritz0 compiled it.  ritz0 parses `*mut T` as a PtrType with
`mutable=True`, and nothing but generic type-argument identity reads that flag:
a `*mut T` and a `*T` pass for each other in a `let`, an argument, a return
and a field, and `**mut T` / `*mut *mut T` nest like `**T`.  ritz1 now accepts
`*mut T` wherever it accepts `*T` and lowers it the same.

AGAST #3959, LARB R74: `*mut T` is another spelling of `*T`, so a generic
over one IS the generic over the other: `Vec<*mut i32>` is `Vec<*i32>`, one
instance under one mangled name.  ritz0 kept `mutable` in type identity and
mangling (`Vec$ptrmut_i32` / `Vec$ptr_i32`) and refused one for the other;
ritz1 has a single pointer type code, so it never did.  The `generic_same_*`
cases pin that, and the ritz0-only check that no `ptrmut` name is emitted.
"""

import pytest

from test_borrow_param_ref_field import _compile
from test_defer_all_compilers import COMPILERS, run_with  # noqa: F401  (fixture)

pytestmark = pytest.mark.integration

MAIN = "pub fn main() -> i32\n"
# A generic of our own, so no case needs an allocator linked.
BOX = "struct Box<T>\n    v: T\n\n"
# AGAST #3959: a fn over the `*T` spelling, and a generic fn instantiated
# from both spellings.
BOX_SAME = (BOX + "fn n(b: @Box<*i32>) -> i32\n    return *b.v\n\n"
            "fn get<T>(b: @Box<T>) -> T\n    return b.v\n\n")

# name: (program, main's exit code).
CASES = {
    # The ticket's repro: the LANGUAGE_SPEC §5 example's signature.
    "param": ("fn raw(p: *mut i32)\n    pass\n\n" + MAIN + "    var x: i32 = 0\n"
              "    raw(@x)\n    0\n", 0),
    "write_through_param": ("fn put(p: *mut i32)\n    *p = 9\n\n" + MAIN +
                            "    var x: i32 = 1\n    put(@x)\n    return x\n", 9),
    # Interchangeable with `*T`, both ways, in a `let` and in a call.
    "let_mut_into_plain": (MAIN + "    var x: i32 = 5\n    let m: *mut i32 = @x\n"
                           "    let q: *i32 = m\n    return *q\n", 5),
    "let_plain_into_mut": (MAIN + "    var x: i32 = 5\n    let q: *i32 = @x\n"
                           "    let m: *mut i32 = q\n    *m = 7\n    return x\n", 7),
    "call_plain_into_mut": ("fn put(p: *mut i32)\n    *p = 9\n\n" + MAIN +
                            "    var x: i32 = 1\n    let q: *i32 = @x\n    put(q)\n"
                            "    return x\n", 9),
    "call_mut_into_plain": ("fn get(p: *i32) -> i32\n    return *p\n\n" + MAIN +
                            "    var x: i32 = 4\n    let m: *mut i32 = @x\n"
                            "    return get(m)\n", 4),
    # Nesting: `**mut T` (a pointer to a `*mut T`) and `*mut *mut T`.
    "ptr_to_mut_ptr": ("fn f(pp: **mut i32) -> i32\n    return **pp\n\n" + MAIN +
                       "    var x: i32 = 6\n    var p: *mut i32 = @x\n    return f(@p)\n", 6),
    "mut_ptr_to_mut_ptr": ("fn f(pp: *mut *mut i32) -> i32\n    return **pp\n\n" + MAIN +
                           "    var x: i32 = 8\n    var p: *mut i32 = @x\n"
                           "    return f(@p)\n", 8),
    # Every other slot a type goes in.
    "return_type": ("fn id(p: *mut i32) -> *mut i32\n    return p\n\n" + MAIN +
                    "    var x: i32 = 3\n    return *id(@x)\n", 3),
    "field": ("struct S\n    p: *mut i32\n\n" + MAIN + "    var x: i32 = 2\n"
              "    let s = S { p: @x }\n    return *s.p\n", 2),
    "var_no_init": (MAIN + "    var x: i32 = 12\n    var p: *mut i32\n    p = @x\n"
                    "    return *p\n", 12),
    "cast": (MAIN + "    var x: i32 = 13\n    let a = @x as *mut i32\n    return *a\n", 13),
    "array_pointee": ("fn f(p: *mut [2]i32) -> i32\n    return p[1]\n\n" + MAIN +
                      "    var a: [2]i32 = [1, 14]\n    return f(@a)\n", 14),
    # The N-D pointee forms (#2098): a param, a var with and without a value.
    "nd_var": (MAIN + "    var a: [2][3]i32\n    a[1][2] = 18\n"
               "    var p: *mut [2][3]i32 = @a\n    return p[1][2]\n", 18),
    "nd_param": ("fn f(p: *mut [2][3]i32) -> i32\n    return p[1][2]\n\n" + MAIN +
                 "    var a: [2][3]i32\n    a[1][2] = 15\n    return f(@a)\n", 15),
    "nd_var_no_init": (MAIN + "    var a: [2][3]i32\n    a[1][2] = 16\n"
                       "    var p: *mut [2][3]i32\n    p = @a\n    return p[1][2]\n", 16),
    # A generic argument, and one closed by `>>` (type_spec_shr).
    "generic_arg": (BOX + MAIN + "    var x: i32 = 11\n"
                    "    let b: Box<*mut i32> = Box { v: @x }\n    return *b.v\n", 11),
    "generic_arg_shr": (BOX + MAIN + "    var w: Box<i32> = Box { v: 17 }\n"
                        "    let b: Box<*mut Box<i32>> = Box { v: @w }\n"
                        "    return b.v.v\n", 17),
    # AGAST #3959: `Box<*mut i32>` and `Box<*i32>` are one type, as an
    # argument behind `@`, by value both ways, and as one generic instance.
    "generic_same_ref_arg": (BOX_SAME + MAIN + "    var x: i32 = 19\n"
                             "    let b: Box<*mut i32> = Box { v: @x }\n"
                             "    return n(@b)\n", 19),
    "generic_same_by_value": (BOX_SAME + MAIN + "    var x: i32 = 20\n"
                              "    let m: Box<*mut i32> = Box { v: @x }\n"
                              "    let q: Box<*i32> = m\n    let r: Box<*mut i32> = q\n"
                              "    *r.v = 21\n    return x\n", 21),
    "generic_same_instance": (BOX_SAME + MAIN + "    var x: i32 = 10\n    var y: i32 = 12\n"
                              "    let m: Box<*mut i32> = Box { v: @x }\n"
                              "    let q: Box<*i32> = Box { v: @y }\n"
                              "    return *get(@m) + *get(@q)\n", 22),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CASES))
def test_mut_pointer_is_a_pointer(run_with, compiler, name):
    program, code = CASES[name]
    assert run_with(compiler, name, program) == code


def test_ritz0_mangles_one_instance(tmp_path):
    """AGAST #3959: both spellings name one struct and one `get` instance."""
    program, _ = CASES["generic_same_instance"]
    comp, ll, _ = _compile("ritz0", None, tmp_path, "mangle", program)
    assert comp.returncode == 0, comp.stdout[-2000:] + comp.stderr[-2000:]
    text = ll.read_text()
    assert "ptrmut" not in text
    assert text.count("define") and '@"get$ptr_i32"' in text
