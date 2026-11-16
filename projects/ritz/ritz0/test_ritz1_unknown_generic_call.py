"""AGAST #3667: a call to an undefined generic fn is refused at the call.

`nope<i64>(x)` names no fn.  ritz0 says `Unknown function: nope` at the
callee.  ritz1 refused an unknown plain call there (#3255), but a call with a
type suffix skipped that check: it declared `@nope$i64`, and only the link
failed ("undefined reference", no line).

A generic that does exist, local or imported, still compiles and runs.
"""

import re

import pytest

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

S = "struct S\n    a: i32\n\n"

# name -> program.  Each calls `nope<...>` at line 6, column 5.
REFUSED = {
    "mut_ref_arg": S + "pub fn main() -> i32\n    var s: S = S { a: 40 }\n    nope<i64>(@&s) as i32\n",
    "int_arg": S + "pub fn main() -> i32\n    var x: i64 = 1\n    nope<i64>(x) as i32\n",
    "struct_type_arg": S + "pub fn main() -> i32\n    var s: S = S { a: 40 }\n    nope<S>(@s) as i32\n",
}

# name -> (program, exit code): generics that exist are not refused.
ACCEPTED = {
    "local": ("fn id<T>(x: T) -> T\n    x\n\n"
              "pub fn main() -> i32\n    id<i64>(42) as i32\n", 42),
    "imported": (for_header.GVEC + "pub fn main() -> i32\n"
                 "    var v: Vec<i64> = vec_new<i64>()\n"
                 "    v.push(40)\n    v.push(2)\n"
                 "    (v.get(0) + v.get(1)) as i32\n", 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_undefined_generic_fn_is_refused_at_the_call(compile_with, compiler, name):
    comp, ll, _ = compile_with(compiler, name, REFUSED[name])
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out[-2000:]
    sep = "" if compiler == "ritz0" else "error: "
    assert re.search(rf"main\.ritz:6:5: {sep}Unknown function: nope$", out, re.M), out[-2000:]
    assert "Traceback" not in out, out[-2000:]
    assert not ll.exists()


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_defined_generic_fn_is_called(run_with, compiler, name):
    program, expected = ACCEPTED[name]
    assert run_with(compiler, name, program) == expected
