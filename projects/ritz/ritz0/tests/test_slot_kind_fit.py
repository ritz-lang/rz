"""AGAST #4653: a value whose kind doesn't fit its slot is refused at every slot.

ritz1 checked a value's KIND against its slot only for a call argument
(call_check's cc_kind: "argument 1 of `g` has the wrong type: parameter `v` is
declared `u8` but its argument is a `T`").  A `let` / `var`, an assignment, a
struct-literal field, a `return` and a fn's tail went through literal_slot,
which judged only a struct of another struct, so ritz1 emitted IR for each row
below, where ritz0 refuses it.  The rule is now one fn, call_check's
slot_kind_fit, and every slot asks it (slot_kind.ritz says it in each site's
words):

    slot            value refused
    struct          an integer, float, `bool`, `null`, `c"..."` or pointer
    int / float /   a struct
      bool
    int             a float, `null`; a pointer, unless the int is i64 / u64
    pointer         a struct (other than its own pointee: ref_check's); a
                    float; an int narrower than i64 / u64

Each row is the #4631 survey's, or a ritz0-only test's (named), on all three
compilers.  The words are ritz0's where they are already Ritz-level; where
ritz0 spells an LLVM type (`%"struct.ritz_module_1.P"`), only the Ritz-level
head is held, and ritz1 names the Ritz type.  `»` marks where ritz0 reports.

Each row is one path (docs/TESTING.md, "What a ritz0 pytest case costs").
"""

import pytest

import batching
import test_ritz1_for_header as for_header

pytestmark = pytest.mark.batched

compile_with = for_header.compile_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

HEAD = """\
struct P
    a: i64
    b: i64

struct T
    id: i32

struct S
    v: u8

struct Other
    n: i64

struct H
    f: u32
    g: bool

fn five() -> i64
    5

fn mk() -> P
    P { a: 1, b: 2 }

fn fl() -> f64
    1.5

"""

MAIN = "fn main() -> i32\n    0\n"
STRUCT_INT = "the fn returns `i32`, but this is struct `T`: a struct is not an integer (return one of its fields)"

# name -> (the program after HEAD, `»` where the error is; ritz0's words).
REFUSED = {
    # test_let_annotation_mismatch.py: both directions.
    "let_int_into_struct": ("fn main() -> i32\n    »let p: P = five()\n    p.a as i32\n",
                            "`p` is declared `P` but its initialiser has type `i64`"),
    "let_struct_into_int": ("fn main() -> i32\n    »let n: i64 = mk()\n    n as i32\n",
                            "`n` is declared `i64` but its initialiser has type `"),
    # test_struct_lit_scalar_field.py (ritz1 checked only a struct field).
    "field_struct_into_u8": ("fn main() -> i32\n    let c = S { v: »T { id: 1 } }\n    0\n",
                             "field `v` of `S` is `u8`, not `T`"),
    # test_store_mismatch_diagnostic.py
    "assign_struct_into_ptr": ('fn main() -> i32\n    var p: *u8 = c"a"\n    let v = Other { n: 1 }\n'
                               "    »p = v\n    0\n",
                               "cannot assign to `p`: cannot store "),
    "assign_int_into_struct": ("fn main() -> i32\n    var q: P = mk()\n    »q = five()\n    q.a as i32\n",
                               "cannot assign to `q`: cannot store "),
    "assign_struct_into_field": ("fn main() -> i32\n    var h = H { f: 1, g: true }\n    »h.g = mk()\n    0\n",
                                 "cannot assign to field `g`: cannot store "),
    # test_checker_corpus_gaps.py TestRoundThree::test_single_capital_struct_is_not_a_type_param
    "let_struct_into_ptr": ("fn f(s: S) -> i32\n    »let p: *u8 = s\n    0\n" + MAIN,
                            "cannot initialize *u8 with S"),
    # A struct literal's tail and return (struct_value_name had no StructLit).
    "tail_struct_lit_into_int": ("fn g() -> i32\n    »T { id: 1 }\n" + MAIN, STRUCT_INT),
    "return_struct_lit_into_int": ("fn g() -> i32\n    return »T { id: 1 }\n" + MAIN, STRUCT_INT),
    "tail_int_into_struct": ("fn g() -> P\n    »five()\n" + MAIN,
                             "block expression has type i64, expected P"),
    # test_null_fn_pointer_slot.py test_null_still_refused_by_a_non_pointer_slot
    "assign_null_into_int": ("fn main() -> i32\n    var n: i32 = 1\n    »n = null\n    n\n",
                             "cannot assign null to i32"),
    # test_int_into_float_slot_checker.py: the float into an int.
    "let_float_into_int": ("fn main() -> i32\n    let d: f64 = fl()\n    »let x: u32 = d\n    0\n",
                           "cannot initialize u32 with f64"),
    "return_float_into_int": ("fn g() -> u32\n    »return fl()\n" + MAIN,
                              "return type f64 doesn't match expected u32"),
    "field_float_into_int": ("fn main() -> i32\n    let h = H { f: »fl(), g: true }\n    0\n",
                             "field 'f': expected u32, got f64"),
    # test_deref_field_types.py: an int into a pointer, and back.
    "let_i32_into_ptr": ("fn f(t: T) -> i32\n    »let v: *u8 = t.id\n    0\n" + MAIN,
                         "cannot initialize *u8 with i32"),
    "let_ptr_into_i32": ("fn f(p: *T) -> i32\n    »let v: i32 = p\n    v\n" + MAIN,
                         "cannot initialize i32 with *T"),
    # The #4631 survey's StrView row, and test_variant_pattern_scrutinee_enum.py's.
    "let_int_into_strview": ("fn main() -> i32\n    let v: i64 = five()\n    »let s: StrView = v\n    0\n",
                             "`s` is declared `StrView` but its initialiser has type `i64`"),
    "let_payload_into_strview": ("fn f(r: Result<i64, i32>) -> i32\n    match r\n        Ok(v) =>\n"
                                 "            »let s: StrView = v\n            0\n        Err(_) => 0\n" + MAIN,
                                 "`s` is declared `StrView` but its initialiser has type `i64`"),
    # AGAST #4930, #4962: a print builtin's value is ritzlib.errno's
    # errno_check's Result<(), Errno>, whatever fn of its name is in scope.
    # This file has no ritzlib.errno, so no Errno to build: the call is a
    # procedure, and any slot is refused (test_print_result.py has the Result).
    "let_print_into_struct": ('fn main() -> i32\n    let p: P = »print("x")\n    p.a as i32\n',
                              "`print` returns nothing, so its call has no value to use here"),
    # test_strlit_span_slot_checker.py TestStillRefused::test_mixed_tails_judge_the_non_literal
    "tail_arm_strview_into_span": ('fn g(b: bool, v: StrView) -> Span<u8>\n    »if b\n        "ab"\n'
                                   "    else\n        v\n" + MAIN,
                                   "block expression has type StrView, expected Span<u8>"),
}


def _where(program):
    """(line, col) of the `»` in HEAD + `program`, and the program without it."""
    text = HEAD + program
    before = text[:text.index("»")]
    return (before.count("\n") + 1, len(before) - before.rfind("\n")), text.replace("»", "", 1)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_value_of_the_wrong_kind_is_refused(compile_with, name, compiler):
    marked, message = REFUSED[name]
    (line, col), program = _where(marked)
    where = f"{line}:{col}"
    batch = getattr(compile_with, "batch_compile", None)
    got = batching.refused(compiler, program, batch, at=(line, col)) if batch else None  # AGAST #2806
    if got is not None:
        out, where = got
    else:
        comp, ll, _ = compile_with(compiler, name, program)
        out = comp.stdout + comp.stderr
        assert comp.returncode != 0, f"{compiler} took {name}:\n{out[-1000:]}"
        assert not ll.exists(), f"{compiler} wrote {ll.name} for {name}"
    assert f"main.ritz:{where}: " in out and message in out, f"{name}: wanted {where}: {message}\n{out[-1500:]}"


# Controls: each is a slot the rule must leave alone.
ACCEPTED = {
    "int_literal_into_float": "fn main() -> i32\n    let x: f64 = 1\n    x as i32\n",
    "i64_into_ptr": "fn main() -> i32\n    let p: *u8 = five()\n    0\n",
    "ptr_into_u64": "fn f(p: *T) -> u64\n    let n: u64 = p\n    n\n" + MAIN,
    "null_into_ptr": "fn main() -> i32\n    var p: *u8 = null\n    p = null\n    0\n",
    "string_lit_into_span": 'fn g() -> Span<u8>\n    "ab"\n' + MAIN,
    "struct_field_of_its_own": "fn main() -> i32\n    let h = H { f: 7, g: true }\n    h.f as i32\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_values_that_fit_their_slots_still_compile(compile_with, compiler):
    """One program holding every control, so a compiler pays one compile."""
    bodies = []
    for i, (name, prog) in enumerate(sorted(ACCEPTED.items())):
        bodies.append(prog.replace(MAIN, "").replace("fn main()", f"fn m{i}()"))
    program = HEAD + "".join(bodies) + MAIN
    comp, _, _ = compile_with(compiler, "accepted", program)
    assert comp.returncode == 0, comp.stdout + comp.stderr
