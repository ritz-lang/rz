"""AGAST #109: `let (a, b, c, ...) = e` destructures any number of names.

THE DEFECT

ritz1's grammar took only the two-name form, `let (a, b) = g()`:

    let (a, b, c) = g3()        # ritz1: unexpected ','; cannot parse item

ritz0 takes any number of names, and `_` among them (`let (_, y) = g()`
already worked on ritz1: `_` lexes as an IDENT and binds nothing).

THE FIX

The grammar's tuple-destructure rule takes an optional tail of names after
the second (`tuple_bind_more`), carried on the statement as `tuple_more`.
Every pass that binds the two names binds the tail too: the parse-time split
of a tuple literal / if / match of literals (ast_helpers.ritz,
tuple_split_decl), sema_walk, binder_check (a name repeated within the
destructure is a reuse, as ritz0 says) and the emitter, which extracts field
i into name i (emit_tuple_decl).

THE ROWS

One per path that reads the names, each able to fail on its own:

  * a call's tuple, by the emitter, with a u8 element (widened unsigned) and
    four names (a tail of two);
  * `_` among them, in the tail and before it;
  * a tuple local, a literal, and if / match arms of literals:
    tuple_split_decl;
  * an if arm with a statement before its tuple: the emitter's if path;
  * a generic fn's `(T, T, T)`;
  * refusals: a name repeated in the tail (binder_check), and a tuple with
    fewer elements than names (the emitter; ritz0's emitter raises, unlocated).
"""

import pytest

import batching
import test_ritz1_for_header as for_header

pytestmark = pytest.mark.batched

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
RITZ1S = ["ritz1", "ritz1_selfhosted"]

FNS = """\
fn g3(a: i32) -> (i32, i64, u8)
    (a, 20, 200)

fn g4(a: i32) -> (i32, i32, i32, i32)
    (a, a + 1, a + 2, a + 3)

fn g() -> (i32, i32)
    (3, 4)

"""

# name -> (main's body, exit code)
RUNS = {
    # 1 + 20 + 200 = 221: the u8 is widened unsigned (sext would give -56).
    "call_three": ("let (x, y, z) = g3(1)\nreturn x + y as i32 + z as i32", 221),
    # 1, 2, 3, 4 -> 1234: the tail's order.
    "call_four": ("let (a, b, c, d) = g4(1)\nreturn a * 1000 + b * 100 + c * 10 + d", 1234 % 256),
    # 4 + 200 + 3: `_` first, last and in the tail.
    "placeholders": ("let (_, w) = g()\nlet (_, _, q) = g3(5)\nlet (v, _, _) = g3(3)\n"
                     "return w + q as i32 + v", 207),
    "tuple_local": ("let t: (i32, i32, i32) = (4, 5, 6)\nlet (a, b, c) = t\nreturn a * 100 + b * 10 + c", 456 % 256),
    "literal": ("let (m0, m1, m2) = (1, 2, 3)\nreturn (m0 * 100 + m1 * 10 + m2) as i32", 123),
    "if_literals": ("let k: i32 = 1\nlet (a, _, c) = if k == 1\n    (10, 20, 30)\nelse\n    (40, 50, 60)\n"
                    "return (a + c) as i32", 40),
    "match_literals": ("let k: i32 = 2\nlet (a, b, c) = match k\n    1 => (1, 2, 3)\n    _ => (4, 5, 6)\n"
                       "return (a * 100 + b * 10 + c) as i32", 456 % 256),
    "if_arm_stmts": ("let k: i32 = 0\nlet (a, b, c) = if k == 1\n    (1, 2, 3)\nelse\n    let q: i32 = 7\n"
                     "    (q, 8, 9)\nreturn (a * 100 + b * 10 + c) as i32", 789 % 256),
    "generic": ("let (a, b, c) = trip<i32>(5)\nreturn a + b + c", 15),
}

EXTRA = """\
struct P
    a: i32
    b: i32
    c: i32

fn trip<T>(x: T) -> (T, T, T)
    (x, x, x)

"""


def _program(body: str) -> str:
    return FNS + EXTRA + "pub fn main() -> i32\n" + "".join(f"    {ln}\n" for ln in body.splitlines())


# LARB R67: every compiler refuses a `(…)` pattern on a named struct
# (test_tuple_pattern_tuples_only.py for ritz0, test_ritz1_struct_destructure.py
# for ritz1 and ritz1_selfhosted since #3500).  This file's rows are tuples.
RUN_ROWS = [(compiler, name) for compiler in COMPILERS for name in sorted(RUNS)]


@pytest.mark.integration
@pytest.mark.parametrize("compiler,name", RUN_ROWS)
def test_destructure_of_n_names_runs(run_with, compiler, name):
    body, want = RUNS[name]
    assert run_with(compiler, name, _program(body)) == want


def _refused(compile_with, compiler, name, body, message, at):
    """`at` is (line within main's body, 1-based col) the error points at."""
    program = _program(body)
    line = 1 + (FNS + EXTRA).count("\n") + at[0]
    column = 4 + at[1]
    got = batching.refused(compiler, program, compile_with.batch_compile)
    if got is not None:
        out = got[0]
    else:
        comp, _, _ = compile_with(compiler, name, program)
        assert comp.returncode != 0, f"{compiler} took {name}"
        out = comp.stdout + comp.stderr
    assert message in out, out[-1000:]
    assert f"main.ritz:{line}:{column}:" in out, out[-1000:]
    return out


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_name_repeated_in_the_tail_is_refused(compile_with, compiler):
    # The third `a` reuses the first, located at the third.
    _refused(compile_with, compiler, "repeat", "let (a, b, a) = g3(1)\nreturn b as i32",
             "a local can't reuse a name bound earlier in its fn: 'a'", (1, 12))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_more_names_than_elements_is_refused(compile_with, compiler):
    out = _refused(compile_with, compiler, "arity", "let (a, b, c) = g()\nreturn a + b + c",
                   # ritz0's words, from Sema (AGAST #4665); the emitter's
                   # "a field for each name" is now only its fallback.
                   "Tuple destructuring mismatch: expected 2 elements, got 3 names", (1, 1))
    # Every name is still bound (a placeholder), so `c` is no second error.
    assert out.count("error") == 1, out[-1000:]


# LARB R67 (AGAST #3500): a named struct is read by its fields, not by
# position; the refusal is at the pattern's `(`.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_a_named_struct_is_refused(compile_with, compiler):
    _refused(compile_with, compiler, "named_struct",
             "let p: P = P { a: 1, b: 2, c: 3 }\nlet (pa, pb, pc) = p\n"
             "return pa * 100 + pb * 10 + pc",
             "`P` is a struct, not a tuple: read its fields", (2, 5))
