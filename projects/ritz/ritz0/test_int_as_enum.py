#!/usr/bin/env python3
"""`n as E`, an integer to an enum, is an error (LARB R19, AGAST #3040).

An integer may name no variant, so `as` can't make an enum of it: `7 as A`
ran the last arm on ritz0, `60 as Sc` gave a bad tag (ritz0 converted the
declaration index, not §10.4's discriminant), `n as B` of an enum with data
crashed ritz0's emitter, and ritz1 lowered every one of them to IR that only
llc refused.  The way in is a `match` on the integer.

Each refusal row must give exactly one error, located at the `as` (`^`),
in the same words on ritz0, ritz1 and ritz1_selfhosted.  `e as U` (enum to
integer, LANGUAGE_SPEC §10.4) is unchanged: the controls still run.
"""

import re

import pytest

from enum_rules import int_as_enum
from test_ref_into_value import COMPILERS, _compile, _ids, _located, _run

pytestmark = pytest.mark.integration

ENUMS = """\
enum A
    V
    P

enum B
    V
    Q(i32)

enum Sc: u64
    Rd = 0
    Ex = 60

"""

# The program after ENUMS, `^` where the error lands, and the enum it names.
REFUSED = {
    # The ticket's repro: a data enum as a match scrutinee.
    "repro_match_data": ("fn main() -> i32\n    let n: i32 = 1\n    match n ^as B\n"
                         "        V => 1\n        Q(x) => 5\n", "B"),
    "fieldless_in_range": ("fn main() -> i32\n    let a: A = 1 ^as A\n"
                           "    match a\n        V => 1\n        P => 2\n", "A"),
    "fieldless_out_of_range": ("fn main() -> i32\n    let n: i64 = 7\n    let a: A = n ^as A\n"
                               "    match a\n        V => 1\n        P => 2\n", "A"),
    "repr": ("fn main() -> i32\n    let n: u64 = 60\n    let s: Sc = n ^as Sc\n"
             "    match s\n        Rd => 1\n        Ex => 2\n", "Sc"),
    "data_let": ("fn main() -> i32\n    let n: i32 = 1\n    let b: B = n ^as B\n"
                 "    match b\n        V => 1\n        Q(x) => x\n", "B"),
}

# `e as U` still converts: the program after ENUMS and its exit code.
CONTROLS = {
    "fieldless_to_int": ("fn main() -> i32\n    let a = A.P\n    a as i32\n", 1),
    "repr_to_int": ("fn main() -> i32\n    let n: u64 = Sc.Ex as u64\n    n as i32\n", 60),
    # Arms that store, not yield: ritz1 lowers enum-valued match arms (as a
    # value, or `=> return A.V`) to a `phi i64`, which is AGAST #3205.
    "match_is_the_way_in": ("fn to_a(n: i32) -> A\n    var a = A.V\n    match n\n"
                            "        0 => a = A.V\n        _ => a = A.P\n    a\n\n"
                            "fn main() -> i32\n    let a = to_a(1)\n    a as i32 + 40\n", 41),
}

_DIAG = re.compile(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)")


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", _ids(REFUSED))
def test_int_as_enum_is_one_located_error(tmp_path, compiler, case):
    body, enum = REFUSED[case]
    src, where = _located(ENUMS + body)
    comp, ll, _ = _compile(compiler, tmp_path, case, src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {case}:\n{src}"
    assert not ll.exists()
    assert "Traceback" not in out, f"{compiler} crashed on {case}:\n{out[-2000:]}"
    assert _DIAG.findall(out) == [(where, int_as_enum(enum))], \
        f"{compiler}: {case}, wanted one error at {where}:\n{src}\n{out[-2000:]}"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", _ids(CONTROLS))
def test_enum_as_int_still_runs(tmp_path, compiler, case):
    body, code = CONTROLS[case]
    assert _run(compiler, tmp_path, case, ENUMS + body) == code
