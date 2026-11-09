"""AGAST #2521: only a String, Vec or Span slices, on all three compilers.

LANGUAGE_SPEC §3.4, and R9 rules 5 and 6: `a[lo..hi]` on an array, `p[lo..hi]` on
a raw `*i32`, and `pp[lo..hi]` on a `**Vec<i32>` (one level: what's behind `pp`
is a pointer, not the Vec) are no slices.

ritz1 and ritz1_selfhosted lowered each to a bare address held in an `i64`, so
`t[0]` read 20 for the first two and garbage for the third, without a word.
ritz0 refused each, but with no location: a `ValueError` for the first two and an
LLVM "Type of #1 arg mismatch" for the third, which stripped every pointer level
and handed `vec_slice` the `*Vec`.

Now each is one located refusal, at the same line:col on all three, as the
`*[4]i32` one already was on ritz1.
"""

import re

import pytest

from test_index_through_reference import HEADER
from test_slice_value_local import BOXES, compile_with  # noqa: F401  (fixture)

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
ONLY_THREE = "(only String, Vec and Span can)"

# Each: the program, and what the refusal names.  The slice is `{base}[1..3]`
# on main.ritz line SLICE_LINE, so the base's column is the same on all rows.
ARRAY_LOCAL = (f"{HEADER}pub fn main() -> i32\n    var a: [4]i32 = [10, 20, 30, 40]\n"
               "    let t = a[1..3]\n    return t[0]\n")
RAW_POINTER = (f"{HEADER}fn f(p: *i32) -> i32\n    let t = p[1..3]\n    return t[0]\n\n"
               "pub fn main() -> i32\n    var a: [4]i32 = [10, 20, 30, 40]\n    return f(@a[0])\n")
POINTER_TO_POINTER = (f"{HEADER}fn f(pp: **Vec<i32>) -> i32\n    let t = pp[1..3]\n    return t[0]\n\n"
                      f"pub fn main() -> i32\n{BOXES['Vec'][0]}    var p: *Vec<i32> = @v\n"
                      "    return f(@p)\n")
POINTER_TO_ARRAY = (f"{HEADER}fn f(p: *[4]i32) -> i32\n    let t = p[1..3]\n    return 0\n\n"
                    "pub fn main() -> i32\n    var a: [4]i32 = [10, 20, 30, 40]\n    return f(@a)\n")
INCLUSIVE = ARRAY_LOCAL.replace("a[1..3]", "a[1..=2]")
# Not a name: a field, and a call's result.  ritz1 asks the base's type.
FIELD = (f"{HEADER}struct H\n    a: [4]i32\n\npub fn main() -> i32\n"
         "    var h = H { a: [10, 20, 30, 40] }\n    let t = h.a[1..3]\n    return t[0]\n")
CALL = (f"{HEADER}fn g() -> *i32\n    return null\n\npub fn main() -> i32\n"
        "    let t = g()[1..3]\n    return t[0]\n")

CASES = {
    "array": (ARRAY_LOCAL, "an array can't be sliced"),
    "array_inclusive": (INCLUSIVE, "an array can't be sliced"),
    "field": (FIELD, "an array can't be sliced"),
    "call": (CALL, "a pointer can't be sliced"),
    "raw_pointer": (RAW_POINTER, "a pointer can't be sliced"),
    "pointer_to_pointer": (POINTER_TO_POINTER, "a pointer to a pointer can't be sliced"),
    "pointer_to_array": (POINTER_TO_ARRAY, "a pointer to an array can't be sliced"),
}


def _where(program):
    """main.ritz line:col of the slice's base, as all three locate an index."""
    for n, line in enumerate(program.splitlines(), 1):
        m = re.search(r"let t = ([\w.()]+)\[", line)
        if m:
            return n, m.start(1) + 1
    raise AssertionError("no slice in the program")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(CASES))
def test_only_string_vec_and_span_slice(compile_with, case, compiler):
    program, what = CASES[case]
    comp, _, _ = compile_with(compiler, case, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} took {case}"
    line, col = _where(program)
    assert f"main.ritz:{line}:{col}: {what} {ONLY_THREE}" in out, out[-1000:]
    # One refusal, not a cascade, and no Python traceback from ritz0.
    assert out.count(ONLY_THREE) == 1, out[-1000:]
    assert "Traceback" not in out, out[-1000:]
