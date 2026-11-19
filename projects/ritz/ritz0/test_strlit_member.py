"""AGAST #4301: a field of a bare string literal, `"acpi".ptr` / `"acpi".len`.

THE DEFECT

    fn open_dir(fd: i32, name: *u8, len: i64) -> i32
    ...
    open_dir(top, "acpi".ptr, 4)      # ritz0: compiles
                                      # ritz1: "cannot emit: unhandled
                                      #  EXPR_MEMBER"

A bare `"..."` is a StrView, `{ ptr, len }` (LANGUAGE_SPEC, AGAST #98), so its
fields read as on a StrView local's: `.ptr` is the literal's NUL-terminated
global, `.len` its byte count.  emit_expr_member
(ritz1/src/emitter_expr_access.ritz) had no arm for an EXPR_STRING_LIT base.
#3406 worked around it in harland's inventory (open_dir_sv).

A StrView has no other field; every compiler refuses `"acpi".foo`.

Oracle: ritz0.  ritz0/test_ritz1_strlit_receiver.py pins the literal's
methods (`"lit".len()`, #3156); this pins its fields.
"""

import pytest

from test_borrow_param_ref_field import _compile
from test_ritz1_builtin_struct_shadow import _run_pkg
from test_ritz1_for_iterable import SELFHOSTED_BIN

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

# name: (program, exit code).  A distinct code names each failed check.
PROGRAMS = {
    # The ticket's shape: `.ptr` straight into a `*u8` parameter, with the
    # literal's `.len` beside it.
    "ptr_arg": (
        "fn first_last(p: *u8, n: i64) -> i32\n"
        "    return (*p as i32) + (*(p + n - 1) as i32)\n\n"
        "pub fn main() -> i32\n"
        '    if first_last("acpi".ptr, "acpi".len) != 97 + 105\n'
        "        return 1\n"
        "    return 42\n",
        42,
    ),
    # Bound to locals, annotated and not: the bytes, the NUL past the end,
    # and `.len` as an i64 in arithmetic.
    "locals": (
        "pub fn main() -> i32\n"
        '    let p: *u8 = "acpi".ptr\n'
        '    let n = "acpi".len\n'
        "    if *(p + 1) != 99\n"
        "        return 1\n"
        "    if *(p + n) != 0\n"
        "        return 2\n"
        '    let e: i64 = "".len\n'
        "    if e != 0\n"
        "        return 3\n"
        '    return (n + "hello".len + 33) as i32\n',
        42,
    ),
}

BAD_FIELD = (
    "pub fn main() -> i32\n"
    '    let n = "acpi".foo\n'
    "    return 0\n"
)

# What each compiler says about `"acpi".foo` (measured, not chosen): ritz1's
# Sema (deref_field.ritz) refuses it before the emitter's new arm is reached.
BAD_FIELD_REFUSAL = {
    "ritz0": "Unknown field 'foo' in struct 'StrView'",
    "ritz1": "`StrView` has no field `foo`",
    "ritz1_selfhosted": "`StrView` has no field `foo`",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_field_of_string_literal_runs(ritz1_bin, tmp_path, compiler, name):
    program, want = PROGRAMS[name]
    assert _run_pkg(compiler, tmp_path, name, program) == want


@pytest.mark.parametrize("compiler", COMPILERS)
def test_unknown_field_of_string_literal_is_refused(ritz1_bin, tmp_path, compiler):
    bins = {"ritz0": None, "ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}
    kind = "ritz0" if compiler == "ritz0" else "ritz1"
    comp, ll, _ = _compile(kind, bins[compiler], tmp_path, "bad_field", BAD_FIELD)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f'{compiler} accepted "acpi".foo'
    assert not ll.exists()
    assert BAD_FIELD_REFUSAL[compiler] in out, out[-2000:]
