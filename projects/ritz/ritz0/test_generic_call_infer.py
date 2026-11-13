"""AGAST #1982: a generic call's type args come from its arguments; when they
can't, the same located error on all three compilers.

LANGUAGE_SPEC section 4.4: `f(args)` to a generic `f<T>` binds each T by
matching each param's type against its argument's. A T that no argument binds
(one only in the return type), or that two arguments bind differently, is

    can't infer `T` for `f`: write `f<T>(...)`

at the call. This replaces ritz0's "needs explicit type arguments" (#1968)
and ritz1's fail-open: it emitted `call ... @f(...)` against an undeclared,
unspecialised `f`, and clang refused the IR. What inference accepts, and that
it runs the right instance, is pinned by test/test_diff_generic_infer.ritz.
"""

import pytest

from test_borrow_param_ref_field import _compile
from test_borrow_conflict_all_compilers import _refusal
from test_ritz1_for_iterable import SELFHOSTED_BIN

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

FNS = """\
import ritzlib.gvec

fn mk<T>() -> T
    mk<T>()

fn pick<T>(a: T, b: T) -> T
    b

fn conv<T, U>(x: T) -> U
    conv<T, U>(x)

"""
L = FNS.count("\n") + 2  # the first line of a body below


def _msg(tp, fn):
    return f"can't infer `{tp}` for `{fn}`: write `{fn}<{tp}>(...)`"


# name: (main's body, line:col of the call, message)
REFUSED = {
    # T only in the return type: nothing binds it, an annotation included.
    "return_only": ("    let x: i32 = mk()\n    return x\n", f"{L}:18", _msg("T", "mk")),
    # Two arguments bind T to i32 and to u8.
    "two_disagree": ("    let a: i32 = 1\n    let b: u8 = 2\n    return pick(a, b) as i32\n",
                     f"{L + 2}:12", _msg("T", "pick")),
    # `@&Vec<T>` binds T to u8, the item to i32.
    "vec_and_item_disagree": ("    var v = vec_new<u8>()\n    let b: i32 = 2\n"
                              "    vec_push(@&v, b)\n    return 0\n",
                              f"{L + 2}:5", _msg("T", "vec_push")),
    # T binds; U is in the return type only.
    "second_param_unbound": ("    let a: i32 = 1\n    let b: i64 = conv(a)\n    return 0\n",
                             f"{L + 1}:18", _msg("U", "conv")),
}


@pytest.fixture
def compile_with(ritz1_bin, tmp_path):
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _compile("ritz0", None, tmp_path, name, program)
        return _compile("ritz1", bins[compiler], tmp_path, name, program)
    return go


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_uninferable_generic_call_is_refused_at_the_call(compile_with, compiler, name):
    body, where, message = REFUSED[name]
    program = FNS + "pub fn main() -> i32\n" + body
    comp, ll, _ = compile_with(compiler, name, program)
    assert comp.returncode == 1, comp.stdout + comp.stderr
    assert _refusal(comp, ll, program) == (where, message)


def test_unknown_non_generic_fn_still_unknown(compile_with):
    comp, _, _ = compile_with("ritz0", "nope", "pub fn main() -> i32\n    return nope(1)\n")
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert "Unknown function: nope" in out, out
