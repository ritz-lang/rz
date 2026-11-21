"""AGAST #2518 / #3050: a call's by-value result is a temporary, not a place.

    fn mk() -> R
    mk().n[1] = 3               ritz0: ValueError traceback; ritz1: compiled, write lost
    let p: *i32 = @mk().n[1]    ritz0: the same; ritz1: compiled, a dangling pointer
    look(@mk())                 ritz0: "arg mismatch %R* != %R"; ritz1: "cannot take address"
    suma(@mka())                ritz0: 6; ritz1: "1 unlowerable expression(s)" (#3214)

Aaron's ruling (#2518, LARB review 4 "The three settled answers"):

- A store into a call's temporary is a located error on all three compilers:
  `=`, `+=`, into a field or an element, and a method whose `self` is
  `@&T` / `:& T` (R1 exception 4's auto-ref makes it the same store).
  A read, and a read-only method (`mk().get()`), stay.
- `@` / `@&` of a call's temporary, or of a field or element in it, is a
  located error, EXCEPT passed directly as a call's argument, `f(@mk())`:
  the temporary lives until that call returns and drops then (#3050). The
  drop counts are in test_ownership_free_count.py (`lent_temp_*`).
- A call returning `*R` yields a real place: `mkp().x = 1` and `@mkp().x`
  store and point into the struct it points at (test_store_through_call_pointer.py).

Each run program returns 0, or the number of the first check that failed.
"""

import pytest

import ref_rules
from test_ritz1_array_pointer_index import COMPILERS, compile_with, run_with  # noqa: F401 (fixtures)

pytestmark = pytest.mark.batched

PRELUDE = """\
struct R
    x: i32
    n: [3]i32
    q: *i32
    rp: *R

var gr: R
var calls: i32 = 0

fn mk() -> R
    calls = calls + 1
    var r: R
    r.x = 1
    r.n[0] = 10
    r.n[1] = 20
    r.n[2] = 30
    r.q = @gr.n[0]
    r.rp = @gr
    return r

fn mkp() -> *R
    calls = calls + 1
    return @gr

impl R
    fn get(self: @R) -> i32
        return self.x
    fn bump(self: @&R)
        self.x = self.x + 1
    fn tick(self:& R)
        self.x = self.x + 1
    fn me(self: @R) -> R
        calls = calls + 1
        var r: R
        r.x = self.x + 1
        return r

struct Box
    p: *i32

fn look(r: @R) -> i32
    return r.x

fn poke(r: @&R) -> i32
    r.x = r.x + 5
    return r.x

fn at(p: @i32) -> i32
    return *p

fn raw(p: *i32) -> i32
    return *p

fn two(a: @R, b: i32) -> i32
    return a.n[2] + b

fn mka() -> [3]i32
    calls = calls + 1
    var a: [3]i32 = [1, 2, 3]
    return a

fn suma(a: @[3]i32) -> i32
    return a[0] + a[1] + a[2]

# 320 bytes: returned through sret (SRET_MIN_BYTES, #3181).
fn mkbig() -> [40]i64
    calls = calls + 1
    var a: [40]i64
    a[0] = 5
    a[39] = 7
    return a

fn ends(a: @[40]i64) -> i64
    return a[0] + a[39]

struct Sink
    k: i32

impl Sink
    fn see(self: @Sink, r: @R) -> i32
        return r.x + self.k
    fn seea(self: @Sink, a: @[3]i32) -> i32
        return a[2] + self.k

struct O
    r: R

fn mo() -> O
    calls = calls + 1
    var o: O
    o.r.x = 1
    return o

fn mra() -> [2]R
    calls = calls + 1
    var a: [2]R
    a[1].x = 1
    a[1].n[2] = 30
    return a

"""

# Line 1 of the body is this line of the program.
_FIRST = PRELUDE.count("\n") + 2


def _prog(body: str, calls: int = 1) -> str:
    lines = "".join("    " + line + "\n" for line in body.splitlines())
    return (PRELUDE + "pub fn main() -> i32\n" + lines
            + f"    if calls != {calls}\n        return 9\n    return 0\n")


# Each refusal: (body with `^` where the error is, the message). Every row is
# a different place the refusal must be made: a field, an element, a
# compound store, each kind of mutating receiver, each `@`, and each place
# an `@` can go that outlives its statement.
REFUSED = {
    # Stores (#2518).
    "store_field": ("^mk().x = 1", ref_rules.STORE_INTO_TEMP),
    "store_elem": ("^mk().n[1] = 3", ref_rules.STORE_INTO_TEMP),
    "store_compound": ("^mk().x += 1", ref_rules.STORE_INTO_TEMP),
    "store_method_temp": ("var k: R\n^k.me().x = 4", ref_rules.STORE_INTO_TEMP),
    "mut_self_ref": ("^mk().bump()", ref_rules.MUT_SELF_ON_TEMP),
    "mut_self_borrow": ("^mk().tick()", ref_rules.MUT_SELF_ON_TEMP),
    # A field of the temporary is in it: the store is as lost (#2294).
    "mut_self_field_ref": ("^mo().r.bump()", ref_rules.MUT_SELF_ON_TEMP),
    "mut_self_field_borrow": ("^mo().r.tick()", ref_rules.MUT_SELF_ON_TEMP),
    # So is an element of an array temporary (#3234): it reads as a field
    # does, and a store into it is as lost.
    "store_array_elem_field": ("^mra()[1].x = 3", ref_rules.STORE_INTO_TEMP),
    "store_array_elem": ("var k: R\n^mra()[1] = k", ref_rules.STORE_INTO_TEMP),
    "mut_self_array_elem": ("^mra()[1].bump()", ref_rules.MUT_SELF_ON_TEMP),
    # `@` that outlives the statement (#2518).
    "addr_let": ("let p: @R = ^@mk()\nif p.x != 1\n    return 1", ref_rules.ADDR_OF_TEMP),
    "addr_mut_let": ("let p: @&R = ^@&mk()\np.x = 2", ref_rules.ADDR_OF_TEMP),
    "addr_elem_let": ("let p: *i32 = ^@mk().n[1]\nif *p != 20\n    return 1", ref_rules.ADDR_OF_TEMP),
    "addr_field_store": ("var b: Box\nb.p = ^@mk().x", ref_rules.ADDR_OF_TEMP),
    # A struct literal's field is no call's argument: the Box outlives it.
    "addr_struct_lit": ("let b = Box { p: ^@mk().n[2] }", ref_rules.ADDR_OF_TEMP),
}


def _located(text: str) -> tuple[str, str]:
    """`text` without its `^`, and where the `^` was in the program, `line:col`."""
    before = text[:text.index("^")]
    line = _FIRST + before.count("\n")
    col = len(before) - (before.rfind("\n") + 1) + 5   # the body's 4-space indent
    return text.replace("^", "", 1), f"{line}:{col}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_store_or_lasting_at_into_a_calls_temporary_is_refused(compile_with, name, compiler):
    marked, message = REFUSED[name]
    body, where = _located(marked)
    comp, ll, _ = compile_with(compiler, name, _prog(body))
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} took {name}:\n{out[-1500:]}"
    assert "Traceback" not in out, out[-2000:]
    assert message in out, out[-1500:]
    assert f"main.ritz:{where}:" in out, f"wanted {where}:\n{out[-1500:]}"


# What still compiles and runs: reads, a read-only method, and `@` of a
# temporary passed straight to a call (#3050), by each route a call takes
# its arguments.
RUNS = {
    # Reads stay (#2428).
    "read_field": "if mk().x != 1\n    return 1",
    "read_elem": "if mk().n[1] != 20\n    return 1",
    "read_method": "if mk().get() != 1\n    return 1",
    # A read-only method on a field of one lends it from a spill (#2294).
    "read_method_field": "if mo().r.get() != 1\n    return 1",
    # ...and so does one on an element of an array one (#3234).
    "read_method_array_elem": "if mra()[1].get() != 1\n    return 1",
    "read_array_elem_array": "if mra()[1].n[2] != 30\n    return 1",
    "read_array_elem_copy": "let q = mra()[1]\nif q.x != 1\n    return 1",
    "arg_array_elem": "if look(@mra()[1]) != 1\n    return 1",
    # `@` straight into a call's argument (#3050).
    "arg_whole": "if look(@mk()) != 1\n    return 1",
    "arg_mut": "if poke(@&mk()) != 6\n    return 1",
    "arg_field": "if at(@mk().x) != 1\n    return 1",
    "arg_elem": "if at(@mk().n[1]) != 20\n    return 1",
    "arg_raw_ptr": "if raw(@mk().n[2]) != 30\n    return 1",
    "arg_method_temp": "var k: R\nk.x = 4\nif look(@k.me()) != 5\n    return 1",
    "arg_of_method": "var s = Sink { k: 100 }\nif s.see(@mk()) != 101\n    return 1",
    "arg_with_others": "if two(@mk(), 3) != 33\n    return 1",
    "arg_nested": "if two(@mk(), look(@mk())) != 31\n    return 1",
    "arg_in_let": "let v = look(@mk()) + at(@mk().n[0])\nif v != 11\n    return 1",
    # An array result is lent the same way (#3214).
    "arg_array": "if suma(@mka()) != 6\n    return 1",
    "arg_array_sret": "if ends(@mkbig()) != 12\n    return 1",
    "arg_array_of_method": "var s = Sink { k: 100 }\nif s.seea(@mka()) != 103\n    return 1",
    # A `*R` result is a place: stores and `@` land in `gr` (#2879).
    "pointer_store": "mkp().x = 7\nif gr.x != 7\n    return 1",
    "pointer_addr": "let p: *i32 = @mkp().n[1]\n*p = 8\nif gr.n[1] != 8\n    return 1",
    "pointer_mut_method": "mkp().bump()\nif gr.x != 1\n    return 1",
    # So is what a pointer field of a by-value result points at: a store or
    # `@` there lands in `gr`, not in the temporary.
    "pointer_field_store": "mk().rp.x = 7\nif gr.x != 7\n    return 1",
    "pointer_field_elem": "mk().q[1] = 9\nif gr.n[1] != 9\n    return 1",
    "pointer_field_addr": "let p: *i32 = @mk().rp.n[2]\n*p = 6\nif gr.n[2] != 6\n    return 1",
}
_CALLS = {"arg_method_temp": 1, "arg_nested": 2, "arg_in_let": 2}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_a_read_or_an_argument_of_a_calls_temporary_runs(run_with, name, compiler):
    assert run_with(compiler, name, _prog(RUNS[name], _CALLS.get(name, 1))) == 0
