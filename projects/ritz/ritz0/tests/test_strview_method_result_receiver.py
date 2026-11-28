#!/usr/bin/env python3
"""A method call on a StrView's method result names its instance (AGAST #4928).

`("42").parse_i64().unwrap_or(-1)` calls Option<i64>.unwrap_or. Neither
compiler typed the receiver, `StrView.parse_i64`'s result, so both wanted
`unwrap_or` on every instance with one: with a `Result<String, i32>` in the
program, `Result<String, i32>.unwrap_or` was instantiated too and refused
("cannot move out of a reference", a String out of `@Result`), though nothing
calls it. ritz0's type checker gave a built-in receiver's source method
(ritzlib's `impl StrView`) no type; ritz1's monomorph didn't type a string
literal receiver (a StrView local it did), nor a match's payload bound from
a method call's result.

A const receiver too (AGAST #4957): `const HEX: StrView = ".."` then
`HEX.get(1)` wanted `get` on every instance, and with a `Vec<String>` in
the program (ritzlib.fs list_dir's) ritz1 instantiated `Vec<String>.get`,
which moves a String out of `@Vec`. ritz1's monomorph typed a struct global
receiver (#4774) but not a const. Nor did its bool check: `if
HEX.eq("..")` took `HEX`, neither local nor global, for a static call's
type name, so `eq`'s bool was unknown and an `if` or `assert` on it refused.

Every row runs on ritz0, ritz1 and ritz1_selfhosted.
"""

import pytest

from test_ref_into_value import _compile

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


PRELUDE = (
    "import ritzlib.string\nimport ritzlib.strview\nimport ritzlib.option\nimport ritzlib.result\n"
    "fn get() -> Result<String, i32>\n    Ok(string_from(\"42\"))\n"
)

# name -> source; each compiles (the refusal was at compile time).
ROWS = {
    "literal_receiver": (
        PRELUDE + "pub fn main() -> i32\n    let n: i64 = (\"42\").parse_i64().unwrap_or(-1)\n"
        "    (n - 40) as i32\n"),
    "local_receiver": (
        PRELUDE + "pub fn main() -> i32\n    let s: StrView = \"x\"\n"
        "    let n: i64 = s.parse_i64().unwrap_or(-1)\n    (n + 4) as i32\n"),
    # A payload bound from a method call's result: `f` is a Split, and
    # `f.before` a StrView (ritz1 didn't type the scrutinee).
    "payload_of_a_method_result": (
        PRELUDE + "pub fn main() -> i32\n    let s: StrView = \"4\\t2\"\n"
        "    match s.split_once('\\t')\n"
        "        Some(f) => f.before.parse_i64().unwrap_or(-1) as i32\n"
        "        None => 9\n"),
    "const_receiver": (
        "import ritzlib.gvec\nimport ritzlib.string\nimport ritzlib.strview\n"
        "const HEX: StrView = \"0123\"\n"
        "fn names() -> Vec<String>\n    var v: Vec<String> = vec_new<String>()\n"
        "    v.push(string_from(\"a\"))\n    v\n"
        "pub fn main() -> i32\n    let v: Vec<String> = names()\n"
        "    (HEX.get(1) as i32) + (v.len() as i32)\n"),
    "const_receiver_bool": (
        "import ritzlib.strview\nconst HEX: StrView = \"0123\"\n"
        "pub fn main() -> i32\n    if HEX.eq(\"0123\") and not HEX.eq(\"x\")\n"
        "        return 0\n    1\n"),
}


def _need(request, compiler):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")


# ROWS are table rows of one test per compiler (the suite's case cap,
# docs/TESTING.md): every row runs, and each failing row is named.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_unwrap_or_on_a_strview_methods_result_compiles(request, tmp_path, compiler):
    _need(request, compiler)
    failed = []
    for name in sorted(ROWS):
        comp, ll, _ = _compile(compiler, tmp_path, name, ROWS[name])
        if comp.returncode != 0 or not ll.exists():
            failed.append(f"{name}:\n{(comp.stdout + comp.stderr)[-800:]}")
    assert failed == [], f"{compiler}:\n" + "\n".join(failed)
