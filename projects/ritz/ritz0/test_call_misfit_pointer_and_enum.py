"""AGAST #3340: a struct value into another struct's `*Q` param, and a bare enum
variant into an integer param, are refused on ritz1 as on ritz0.

    fn take(self: *P, q: *Q) -> i64      p.take(p)    # a `P` where a `*Q` goes
    fn sz(self: *P, k: u64) -> i64       p.sz(Lo)     # an enum where a u64 goes

#1629 ran #3319's ritz0 method table (test_method_call_args.py) through
ritz1: 11 of 13 rows agreed.  These two compiled on ritz1 (exit 0) where
ritz0 refuses them.  The same two holes were in free calls, which share the
checks:

    value for pointer   call_check_kind left every pointer param to
                        auto-borrow.  A known struct value of ANOTHER type
                        than a `*Q` param's Q is now "argument N of `f` has
                        the wrong type: ", at the argument.  A value of the
                        param's own struct is ref_check's ("a value doesn't
                        fit a reference slot") and an `@Q` param is
                        ref_check's whatever the struct: both are said once,
                        in its words.
    enum for int        enum_as_int resolved `Lv.Lo` but not a bare `Lo`, so
                        `p.sz(Lo)`, `fsz(Lo)` and `let n: u64 = Lo` passed.  A
                        call argument now says ritz0's "argument N of `f`: "
                        before #2136's words.

A method call is numbered as its desugaring `m(r, ..)`: the receiver is
argument 1 (#3319); a static call has none.
"""

import pytest

import batching
import test_ritz1_for_header as for_header

pytestmark = pytest.mark.batched

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

HEADER = """\
struct P
    n: i64

struct Q
    m: i64

enum Lv
    Lo
    Hi

impl P
    fn take(self: *P, q: *Q) -> i64
        self.n + q.m
    fn ref(self: *P, q: @Q) -> i64
        self.n + q.m
    fn sz(self: *P, k: u64) -> i64
        self.n + k as i64
    fn mk(k: u64) -> P
        P { n: k as i64 }

fn ftake(q: *Q) -> i64
    q.m

fn fsz(k: u64) -> i64
    k as i64

pub fn main() -> i32
    var p: P = P { n: 1 }
    var q: Q = Q { m: 2 }
"""

WRONG = "argument {n} of `{f}` has the wrong type: "
ENUM = "argument {n} of `{f}`: expected u64, found enum 'Lv'; convert with `as`"

# name -> (main's next lines, `@` at the column the error names; message).
REFUSED = {
    # #3319's value_for_pointer row, and its free-call twin.
    "method_value_for_pointer": ("    return p.take(@p) as i32", WRONG.format(n=2, f="take")),
    "free_value_for_pointer": ("    return ftake(@p) as i32", WRONG.format(n=1, f="ftake")),
    "free_rvalue_for_pointer": ("    return ftake(@P { n: 1 }) as i32", WRONG.format(n=1, f="ftake")),
    # #3319's enum_for_int row; a static call has no receiver.
    "method_enum_for_int": ("    return p.sz(@Lo) as i32", ENUM.format(n=2, f="sz")),
    "static_enum_for_int": ("    let m = P.mk(@Lo)\n    return m.n as i32", ENUM.format(n=1, f="mk")),
    "free_enum_for_int": ("    return fsz(@Lo) as i32", ENUM.format(n=1, f="fsz")),
    "qualified_enum_for_int": ("    return fsz(@Lv.Hi) as i32", ENUM.format(n=1, f="fsz")),
    "let_enum_for_int": ("    @let n: u64 = Lo\n    return n as i32",
                         "expected u64, found enum 'Lv'; convert with `as`"),
}


def _refused(compile_with, compiler, name, marked, message):
    """`marked` is main's next lines; its first `@` is where the error is."""
    lines = marked.splitlines()
    at = next(k for k, text in enumerate(lines) if "@" in text)
    column = 1 + lines[at].index("@")
    program = HEADER + marked.replace("@", "", 1) + "\n"
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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_misfit_pointer_or_enum_argument_is_refused(compile_with, name, compiler):
    _refused(compile_with, compiler, name, *REFUSED[name])


# A value of the param's own struct, or anything into an `@Q`, is ref_check's:
# said once, in its words, not as a wrong type too.
REF_CHECK = {
    "same_struct_for_pointer": "    return p.take(q) as i32",
    "other_struct_for_reference": "    return p.ref(p) as i32",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REF_CHECK))
def test_a_value_into_a_reference_slot_is_ref_checks(compile_with, name, compiler):
    comp, _, _ = compile_with(compiler, name, HEADER + REF_CHECK[name] + "\n")
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and "a value doesn't fit a reference slot" in out, out[-1000:]
    assert "has the wrong type" not in out, out[-1000:]


# The legal neighbours: each returns 7.
LEGAL = {
    "pointer_arg": "    q.m = 6\n    return p.take(@q) as i32",
    "receiver_borrowed": "    p.n = 6\n    return p.sz(1) as i32",
    "free_pointer_arg": "    q.m = 7\n    return ftake(@q) as i32",
    "enum_as_converted": "    return (p.sz(Lv.Hi as u64) + fsz(Lv.Lo as u64) + 5) as i32",
    # AGAST #3351: a bare unit variant cast, the form the refusal above
    # tells the user to write.  ritz1 passed the `%Lv` aggregate as the int.
    "bare_enum_as_call_arg": "    return (p.sz(Hi as u64) + fsz(Lo as u64) + 5) as i32",
    "bare_enum_as_let": "    let n: u64 = Hi as u64\n    let z = Lo as u64\n    return (n + z + 6) as i32",
    "bare_enum_as_compare": "    if Hi as u64 > Lo as u64\n        return 7\n    return 0",
    "static": "    let m = P.mk(7)\n    return m.n as i32",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(LEGAL))
def test_a_fitting_pointer_or_converted_enum_still_runs(run_with, name, compiler):
    assert run_with(compiler, name, HEADER + LEGAL[name] + "\n") == 7
