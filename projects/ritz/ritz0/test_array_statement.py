"""A whole array used alone as a statement is refused, located, on all three
compilers (AGAST #3189).

`b` alone, with `b` a `[N]T` local, an `a:& [N]T` param, an array field or `*p`
of a `*[N]T`, mid-block or as the tail of a void fn or method, does nothing.
ritz0 compiled it; ritz1 refused it with #2287's "a whole array is not a value
here" (emit_expr_ident and the void-tail arms of emit_fn / emit_impl_method).
Aaron's ruling: refuse it on all three, in #2287's words, at the expression.
Index it, copy it into an array of the same type, or take its address.

The wording lost its "in ritz1" (#3054's first point): ritz0 prints it too.

#2949's move-only check still fires first for an `a:& [2]Res` param
(stmt_array in test_borrow_param_ref_field.py).
"""

import pytest

from array_rules import WHOLE_ARRAY_NOT_A_VALUE
from test_ref_into_value import COMPILERS, _assert_refused, _main, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

HEAD = "struct W\n    a: [2]i32\n\n"

# `^` marks where the error lands: on the array.
REFUSED = {
    # The ticket's two programs.
    "lent_void_tail": "fn f(a:& [2]i32)\n    ^a\n",
    "local_mid_block": "fn f() -> i32\n    var b: [2]i32 = [1, 3]\n    ^b\n    return 3\n",
    # The other whole arrays. ritz1 refused a field nowhere (#3189): each of
    # its three discard sites, a statement and a fn's and a method's tail.
    "field_mid_block": "fn f(w: W) -> i32\n    ^w.a\n    return 3\n",
    "field_void_tail": "fn f(w: *W)\n    ^w.a\n",
    "method_void_tail": "impl W\n    fn g(self: *W)\n        ^self.a\n",
    "deref_void_tail": "fn f(p: *[2]i32)\n    ^*p\n",
    # An arm's last statement before its value is not the arm's value
    # (AGAST #3920: ritz1 judged only a statement with a next one, and the
    # arm's value lives apart from its statements).  As ritz0, the trailing
    # value of an else-less `if` body is not judged.
    "field_before_match_arm_value": ("fn f(w: W, c: i32) -> i32\n    match c\n        3 =>\n"
                                     "            ^w.a\n            1\n        _ => 0\n"),
    "field_before_if_expr_arm_value": ("fn f(w: W, c: i32) -> i32\n    let v: i32 = if c == 2\n"
                                       "        ^w.a\n        1\n    else\n        0\n    v\n"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", sorted(REFUSED))
def test_a_whole_array_alone_is_refused(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, _main(HEAD + REFUSED[site], "    0\n"),
                    WHOLE_ARRAY_NOT_A_VALUE)


# What the error's alternatives say: they compile and run.  Each is used, as a
# bare `a[0]` or `@&a` alone has no effect (LARB R64, AGAST #3491).
def test_the_written_forms_still_compile(tmp_path):
    body = ("fn f(a:& [2]i32) -> i32\n    let e: i32 = a[0]\n    var c: [2]i32 = a\n"
            "    let r = @&a\n    c[1] + e - r[0]\n")
    assert _run("ritz0", tmp_path, "written", _main(body, "    var b: [2]i32 = [1, 3]\n"
                                                         "    f(@&b)\n")) == 3
