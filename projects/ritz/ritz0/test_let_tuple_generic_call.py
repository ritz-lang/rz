"""AGAST #2593: `let (a, b) = mk<i16>(...)` destructures a generic call.

    struct Pair<T>
        x: T
        y: T
    fn mk<T>(a: T, b: T) -> Pair<T>
        Pair<T> { x: a, y: b }
    let (a, b) = mk<i16>(-300, 2)     # ritz0: ValueError "generic function
                                      # `mk` needs explicit type arguments"

ritz0's monomorph collects instantiations in _visit_stmt, which had no case
for a LetTupleStmt: the initialiser was never walked, so `mk<i16>` was never
registered or specialised, and the emitter found no `mk$i16`. `let p = ...`
worked because LetStmt was walked. ritz1 ran the tuple form.

Each program checks a generic free fn and a generic impl's method with i16,
i64 and f32, on all three compilers, and returns 0 or the failing check.
"""

from pathlib import Path

import pytest

from test_borrow_param_ref_field import _run

RITZ_ROOT = Path(__file__).resolve().parent.parent
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _run("ritz0", None, tmp_path, name, program)
        return _run("ritz1", bins[compiler], tmp_path, name, program)
    return go


PRELUDE = """struct Pair<T>
    x: T
    y: T

fn mk<T>(a: T, b: T) -> Pair<T>
    Pair<T> { x: a, y: b }

impl<T> Pair<T>
    fn flip(self: *Pair<T>) -> Pair<T>
        Pair<T> { x: self.y, y: self.x }

"""

# (type, a, b, check on a and b). Values are chosen so that a value read at
# the wrong width, or the fields swapped, fails the check.
CASES = {
    "i16": ("i16", "-300", "2", "a == -300 and b == 2"),
    "i64": ("i64", "-5000000000", "7", "a == -5000000000 and b == 7"),
    "f32": ("f32", "1.5", "-2.25", "a == 1.5 and b == -2.25"),
}


def _free(ty, a, b, check):
    return (PRELUDE + "pub fn main() -> i32\n"
            f"    let (a, b) = mk<{ty}>({a}, {b})\n"
            f"    if {check}\n        return 0\n    return 1\n")


def _method(ty, a, b, check):
    # flip() swaps, so build it the other way round.
    return (PRELUDE + "pub fn main() -> i32\n"
            f"    var p: Pair<{ty}> = Pair<{ty}> {{ x: {b}, y: {a} }}\n"
            "    let (a, b) = p.flip()\n"
            f"    if {check}\n        return 0\n    return 1\n")


def _in_generic(ty, a, b, check):
    # The tuple-decl inside a generic body: specialised, then visited again.
    return (PRELUDE + "fn sum<T>(a: T, b: T) -> T\n"
            "    let (u, v) = mk<T>(a, b)\n"
            # Through a local: ritz1 refuses `mk<T>(u, v).flip()` here, fail
            # closed ("can't tell which struct this destructures").
            "    var p: Pair<T> = mk<T>(u, v)\n"
            "    let (s, t) = p.flip()\n"
            "    return s + t + u + v\n\n"
            "pub fn main() -> i32\n"
            f"    let r: {ty} = sum<{ty}>({a}, {b})\n"
            f"    let w: {ty} = {a} + {b}\n"
            "    if r == w + w\n        return 0\n    return 1\n")


PROGRAMS = {}
for _ty, _case in CASES.items():
    PROGRAMS[f"free_{_ty}"] = _free(*_case)
    PROGRAMS[f"method_{_ty}"] = _method(*_case)
    PROGRAMS[f"in_generic_{_ty}"] = _in_generic(*_case)
# The briefing's program, verbatim: (-300 + 2 + 400) = 102.
PROGRAMS["briefing"] = PRELUDE + (
    "pub fn main() -> i32\n"
    "    let (a, b) = mk<i16>(-300, 2)\n"
    "    if (a + b + 400) as i32 != 102\n        return 1\n    return 0\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_let_tuple_of_generic_call(run_with, compiler, name):
    assert run_with(compiler, name, PROGRAMS[name]) == 0
