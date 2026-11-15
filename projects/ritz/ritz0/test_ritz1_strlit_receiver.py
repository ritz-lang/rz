"""AGAST #3156: a method call on a bare string literal receiver, `"lit".len()`.

THE DEFECT

    import ritzlib.strview
    pub fn main() -> i32
        return ("hello".len() + 37) as i32    # ritz0: 42
                                              # ritz1: "cannot determine
                                              #  receiver type for method call"

A bare `"..."` is a StrView (AGAST #98), so its methods resolve as on a
StrView local: an `impl StrView` method, or ritz1's `strview_*` UFCS
fallback.  emit_expr_method (ritz1/src/emitter_expr_call.ritz) had no arm for
an EXPR_STRING_LIT receiver, and method_recv_type_name
(ritz1/src/emitter_core.ritz) didn't name one, so the bool check couldn't type
`if "hello".starts_with("he")` either ("if condition must be bool, and ritz1
cannot tell that it is").

A `c"..."` literal is a `*u8`, not a StrView: it has no methods, and every
compiler refuses `c"hello".len()`.  That is pinned below, so a fix for the
bare literal can't start accepting the C string by accident.

Oracle: ritz0.  build.py links ritzlib.strview's impl in.
"""

import pytest

from test_borrow_param_ref_field import _compile
from test_ritz1_builtin_struct_shadow import _run_pkg
from test_ritz1_for_iterable import SELFHOSTED_BIN

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

# name: (program, exit code)
PROGRAMS = {
    # The ticket's repro: a no-argument method, its i64 result in arithmetic.
    "len": (
        "import ritzlib.strview\n\n"
        "pub fn main() -> i32\n"
        '    return ("hello".len() + 37) as i32\n',
        42,
    ),
    # Methods taking an argument (itself a literal, coerced to StrView): a
    # bool result as an `if` condition, both ways, then a u8 and an i64
    # result.  A distinct code names each failed check.
    "with_args": (
        "import ritzlib.strview\n\n"
        "pub fn main() -> i32\n"
        '    if not "hello".starts_with("he")\n'
        "        return 1\n"
        '    if "hello".starts_with("lo")\n'
        "        return 2\n"
        '    if "hello".get(1) != 101\n'
        "        return 3\n"
        '    if "hello".find("ll") != 2\n'
        "        return 4\n"
        "    return 42\n",
        42,
    ),
}

C_LIT = (
    "import ritzlib.strview\n\n"
    "pub fn main() -> i32\n"
    '    return c"hello".len() as i32\n'
)

# What each compiler says about `c"hello".len()` today (measured, not chosen).
C_LIT_REFUSAL = {
    "ritz0": "Cannot call method 'len' on unknown type",
    "ritz1": "cannot determine receiver type for method call",
    "ritz1_selfhosted": "cannot determine receiver type for method call",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_method_on_string_literal_runs(ritz1_bin, tmp_path, compiler, name):
    program, want = PROGRAMS[name]
    assert _run_pkg(compiler, tmp_path, name, program) == want


@pytest.mark.parametrize("compiler", COMPILERS)
def test_method_on_c_string_literal_is_refused(ritz1_bin, tmp_path, compiler):
    bins = {"ritz0": None, "ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}
    kind = "ritz0" if compiler == "ritz0" else "ritz1"
    comp, ll, _ = _compile(kind, bins[compiler], tmp_path, "c_lit", C_LIT)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted c\"...\".len()"
    assert not ll.exists()
    assert C_LIT_REFUSAL[compiler] in out, out[-2000:]
