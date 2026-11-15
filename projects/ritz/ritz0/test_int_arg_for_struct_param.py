"""AGAST #3389 (LARB R47, LANGUAGE_SPEC §9.2): an integer argument for a by-value
struct parameter is refused, at the argument.

    struct S { x: i32 }    fn f(s: S) -> i32    f(1) / f(n), n: i64

A literal is the only way to make a struct value: nothing converts to one, even
a single-field struct.  ritz0 used to wrap the int (`insertvalue %S undef,
(trunc n), 0`); ritz1 passed the i64 where `%S` goes and clang refused the IR
(#3336).  Now it's "argument N of `f` has the wrong type", and you write
`f(S { x: n })`.

ritz1 and ritz1_selfhosted refuse them too (#3390, call_check.ritz rule A), in
ritz0's words followed by ritz1's own ("parameter `s` is declared `S` but its
argument is an integer").  On a method or UFCS call ritz1 used to box the
integer as the struct (`; newtype arg box`).
"""

import pytest

import batching
import test_ritz1_for_header as for_header

pytestmark = pytest.mark.batched

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

HEADER = """\
import ritzlib.gvec

struct S
    x: i32

impl S
    fn add(self: *S, t: S) -> i32
        self.x + t.x

fn f(s: S) -> i32
    s.x

pub fn main() -> i32
    var s: S = S { x: 3 }
    let n: i64 = 4
"""

WRONG = "argument {n} of `{f}` has the wrong type"

# name -> (main's next lines, `$` at the column the error names; message).
# `$`, not `@`: `@` is Ritz's address-of.
REFUSED = {
    "literal": ("    return f($1)", WRONG.format(n=1, f="f")),
    "i64": ("    return f($n)", WRONG.format(n=1, f="f")),
    # A method's receiver is argument 1 (#3319).
    "method_literal": ("    return s.add($7)", WRONG.format(n=2, f="add")),
    # The forms the old wrap's controls boxed (test_ritz1_deref_struct_arg,
    # test_ritz1_struct_result_arg): a scalar deref and a scalar method result.
    "deref_i64": ("    let p: @i64 = @n\n    return f($*p)", WRONG.format(n=1, f="f")),
    "method_result": ("    return f($s.add(s))", WRONG.format(n=1, f="f")),
    # A UFCS call: ritz1 boxed the literal as an `S`.
    "ufcs_literal": ("    var v: Vec<S> = vec_new<S>()\n    v.push($5)\n    return 0", WRONG.format(n=2, f="push")),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_an_int_for_a_struct_param_is_refused(compile_with, name, compiler):
    marked, message = REFUSED[name]
    lines = marked.splitlines()
    at = next(k for k, text in enumerate(lines) if "$" in text)
    column = 1 + lines[at].index("$")
    program = HEADER + marked.replace("$", "", 1) + "\n"
    line = 1 + HEADER.count("\n") + at
    batch = getattr(compile_with, "batch_compile", None)
    got = batching.refused(compiler, program, batch) if batch else None  # AGAST #2806
    if got is not None:
        out = got[0]
    else:
        comp, _, _ = compile_with(compiler, name, program)
        assert comp.returncode != 0, f"{compiler} took {name}"
        out = comp.stdout + comp.stderr
    assert message in out, out[-1000:]
    assert f"main.ritz:{line}:{column}:" in out, out[-1000:]


# The migration the error asks for, `f(S { x: n })`: returns 7.
LEGAL = {
    "literal_struct": "    return f(S { x: 7 })",
    "converted_i64": "    return f(S { x: n as i32 }) + 3",
    "method_struct": "    return s.add(S { x: 4 })",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(LEGAL))
def test_a_struct_literal_argument_still_runs(run_with, name, compiler):
    assert run_with(compiler, name, HEADER + LEGAL[name] + "\n") == 7
