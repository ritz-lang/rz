"""Monomorph reads the typing pass's table (AGAST #3554, after #3448).

monomorph.py typed expressions itself, in `_infer_value_type`,
`_infer_method_call_type` and `_infer_arg_type`, beside the typing pass
(typed.py) that already ran on the module it is given.  Those three are gone:
`Monomorphizer._type_of` reads `module.typed`, and in an instance's body takes
the template's type at the instance's type args.  For that the type checker
now instantiates generics: a generic call or method returns its type at the
call's type args, and a generic struct's field is its type at the receiver's.

No compiles: every case parses a few lines in-process, in milliseconds.
The cases are rows of two tests, not one test each: the ritz0 suite has a
case-count cap (test_budget.toml; docs/TESTING.md, "What a ritz0 pytest case
costs").  Each test runs every row and names every row that fails.
"""

import inspect

import pytest

import monomorph
import ritz_ast as rast
import typed
from metadata import type_to_string
from monomorph import monomorphize
from parser import parse

pytestmark = pytest.mark.unit


def _nodes(module, kind):
    """Every `kind` node in `module`, in walk order."""
    found = []

    def walk(node):
        if isinstance(node, kind):
            found.append(node)
        if isinstance(node, list):
            for x in node:
                walk(x)
        elif isinstance(node, rast.Node):
            for value in vars(node).values():
                if isinstance(value, (list, rast.Node)):
                    walk(value)

    walk(module.items)
    return found


def _name(ty):
    return type_to_string(ty) if ty is not None else None


def _let_value(module, name):
    (let,) = [s for s in _nodes(module, (rast.LetStmt, rast.VarStmt)) if s.name == name]
    return let.value


def _fn_names(module):
    return {item.name for item in module.items if isinstance(item, rast.FnDef)}


# A built-in-shaped generic `Vec<T>` with the UFCS fns its methods lower to,
# so a parse-only module exercises monomorph's `v.len()` -> vec_len<T>.
VEC = """
struct Vec<T>
    data: *T
    len: i64

fn vec_new<T>() -> Vec<T>
    Vec<T> { data: 0 as *T, len: 0 }

fn vec_len<T>(v: @Vec<T>) -> i64
    v.len

fn id<T>(x: T) -> T
    x

struct Cell<B>
    v: B

impl<B> Cell<B>
    fn get(self: @Cell<B>) -> B
        self.v
"""


# --- the type checker instantiates generics ---------------------------------

GENERIC_ROWS = [
    # written type args
    ("vec_new<u16>()", "Vec<u16>"),
    # type args the arguments bind (§4.4), an integer literal's at i64
    ("id(3)", "i64"),
    ("id(3 as u8)", "u8"),
    # a generic struct's field at the receiver's type args
    ("Cell<u32> { v: 1 }.v", "u32"),
    # a generic impl's method at the receiver's type args
    ("Cell<u32> { v: 1 }.get()", "u32"),
    # a built-in generic's UFCS method (vec_len<T>), and indexing a Vec<T>
    ("vec_new<u16>().len()", "i64"),
    ("vec_new<u16>()[0]", "u16"),
]


SLOT = "\nenum Slot<T>\n    Full(T)\n    Empty\n"

# A generic user enum's variant constructor is typed at its instance (AGAST
# #4057), by monomorph's rule for an untyped let's value (#2927): written
# args, else the fn's return type when it is an instance of the enum (#2430),
# else what the payload binds (§4.4).  Unbound, it stays bare: monomorph
# reports that, located.  (fn return type, let value, its type)
VARIANT_ROWS = [
    ("i32", "Full(5)", "Slot<i64>"),
    ("i32", "Full(5 as u16)", "Slot<u16>"),
    ("i32", "Full<u32>(5)", "Slot<u32>"),
    ("Slot<u8>", "Full(5)", "Slot<u8>"),
    ("Slot<u8>", "Empty", "Slot<u8>"),
    ("i32", "Empty", "Slot"),
    # the return-type rule is an untyped let's: a scrutinee's payload binds
    ("Slot<u8>", "match Full(7 as i32)\n        _ => 0", "Slot<i32>"),
    # as monomorph binds: `@n` as a pointer (mangled `ptr_`), and a tuple
    # literal, or a name bound to one, as nothing (#3064)
    ("i32", "Full(@n)", "Slot<*u16>"),
    ("i32", "Full(t)", "Slot"),
]


def _a_generic_variant_is_typed_at_its_instance(ret, value, expected):
    module = parse(SLOT + f"\nfn f() -> {ret}\n    let n = 1 as u16\n    let t = (1, 2)\n"
                   f"    let x = {value}\n    f()\n"
                   "\nfn main() -> i32\n    0\n")
    table = typed.type_module(module)
    x = _let_value(module, "x")
    assert _name(table.type_of(x.expr if isinstance(x, rast.Match) else x)) == expected


def _monomorph_takes_a_variants_instance_from_the_table():
    """Retype `Full(5)` as a Slot<u32> in the table: the let is then a
    Slot<u32>.  Monomorph's own rule (the payload's i64) would make it a
    Slot<i64>; it keeps only the located error for an unbound T."""
    module = parse(SLOT + "\nfn main() -> i32\n    let s = Full(5)\n    0\n")
    table = typed.type_module(module)
    table.record(_let_value(module, "s"), rast.NamedType(None, "Slot", [rast.NamedType(None, "u32", [])]))
    out = monomorphize(module)
    assert "Slot$u32" in {item.name for item in out.items}
    assert "bind_type_params" not in inspect.getsource(monomorph.Monomorphizer._infer_variant_let)


def _an_unbound_variant_is_still_monomorphs_located_error():
    module = parse(SLOT + "\nfn main() -> i32\n    let s = Empty\n    0\n")
    with pytest.raises(monomorph.GenericInferError, match="can't infer `T` for `Empty`"):
        monomorphize(module)


def _a_generic_is_typed_at_its_type_args(value, expected):
    module = parse(VEC + f"\nfn main() -> i32\n    let x = {value}\n    0\n")
    table = typed.type_module(module)
    assert _name(table.type_of(_let_value(module, "x"))) == expected


# --- monomorph reads the table ----------------------------------------------

LET_SOURCE = VEC + """
fn mystery() -> i32
    7

fn main() -> i32
    let v = mystery()
    v.len()
    0
"""


def _monomorph_takes_a_receivers_type_from_the_table():
    """Retype `v` as a Vec<u16> in the table: `v.len()` is then a
    vec_len<u16>, which monomorph instantiates.  Its own rule (the callee's
    declared i32) would instantiate nothing."""
    module = parse(LET_SOURCE)
    table = typed.type_module(module)
    (recv,) = [m.expr for m in _nodes(module, rast.MethodCall) if m.method == "len"]
    table.record(recv, rast.NamedType(None, "Vec", [rast.NamedType(None, "u16", [])]))
    assert "vec_len$u16" in _fn_names(monomorphize(module))


def _monomorph_types_an_untyped_module_itself():
    """A caller that hands monomorphize() a module no pass typed (the
    emitter's own tests) still gets types."""
    module = parse(VEC + "\nfn main() -> i32\n    let v = vec_new<u8>()\n    v.len()\n    0\n")
    assert getattr(module, "typed", None) is None
    assert "vec_len$u8" in _fn_names(monomorphize(module))


INSTANCE_SOURCE = VEC + """
fn count<T>(x: T) -> i64
    let v = vec_new<T>()
    v.len()

fn main() -> i32
    count<u8>(1 as u8)
    0
"""


COPY_SOURCE = VEC + """
fn count<T>(x: T) -> i64
    vec_new<T>().len()

fn main() -> i32
    count<u16>(1 as u16)
    0
"""


def _a_copied_node_is_typed_as_the_template_node_it_copies():
    """count<u16>'s `vec_new$u16()` is a copy the table never typed: its
    type is its template's `vec_new<T>()` at T = u16, so `.len()` on it
    instantiates vec_len<u16>."""
    assert "vec_len$u16" in _fn_names(monomorphize(parse(COPY_SOURCE)))


def _an_instance_body_is_typed_at_its_type_args():
    """count<u8>'s `v` is the template's `Vec<T>` at T = u8, so its `v.len()`
    instantiates vec_len<u8>; the old inferrers saw only the instance's
    mangled call `vec_new$u8()` there, and typed nothing."""
    out = monomorphize(parse(INSTANCE_SOURCE))
    assert {"count$u8", "vec_new$u8", "vec_len$u8"} <= _fn_names(out)


def _monomorph_has_no_inferrers_of_its_own():
    """No `_infer*` that types an expression is left (the remaining ones
    infer type args); every caller reads `_type_of`, which reads the table."""
    for gone in ("_infer_value_type", "_infer_method_call_type", "_infer_arg_type",
                 "_element_type", "_unify"):
        assert not hasattr(monomorph.Monomorphizer, gone), gone
    assert "self._typed.type_of(" in inspect.getsource(monomorph.Monomorphizer._type_of)


# --- what the instantiated types must not break (--check-types) -------------

def _an_option_or_result_predicate_is_a_bool():
    """The emitter lowers `is_some` and kin itself, as a bool; ritzlib's
    `option_is_some<T>` (an i32) is not what the method calls."""
    module = parse(VEC + """
fn option_is_some<T>(o: *Option<T>) -> i32
    1

fn main() -> i32
    let o: Option<u8> = Some(1 as u8)
    let x = o.is_some()
    assert o.is_some()
    0
""")
    table = typed.type_module(module)
    assert _name(table.type_of(_let_value(module, "x"))) == "bool"
    assert table.errors == []


def _a_vec_range_is_a_span_view_in_a_span_slot():
    """`v[1..3]` of a Vec<u8> is a Vec<u8>, and a Span<u8> where one is wanted."""
    module = parse(VEC + """
struct Span<T>
    ptr: *T
    len: i64

fn main() -> i32
    let v = vec_new<u8>()
    let w = v[1..3]
    let view: Span<u8> = v[1..3]
    0
""")
    table = typed.type_module(module)
    assert _name(table.type_of(_let_value(module, "w"))) == "Vec<u8>"
    assert [str(e) for e in table.errors] == []


def _an_address_of_binds_t_as_a_pointer():
    """`id(@x)` binds T as `*u8`, the instance the emitter calls (`id$ptr_u8`),
    not the `@u8` the table types `@x` as."""
    module = parse(VEC + "\nfn main() -> i32\n    let x = 1 as u8\n    id(@x)\n    0\n")
    assert "id$ptr_u8" in _fn_names(monomorphize(module))


def _an_argless_literal_binds_from_a_literal_bound_before_it():
    """Before the typing pass, an args-less literal's args come from its
    fields' types (§9.2): `b`'s field is `a`, a Cell<i64> by then."""
    module = parse(VEC + """
fn main() -> i32
    let a = Cell { v: 1 }
    let b = Cell { v: a }
    0
""")
    monomorph.infer_struct_lit_args(module)
    b = _let_value(module, "b")
    assert [_name(t) for t in b.type_args] == ["Cell<i64>"]


def _a_generic_variant_pattern_binds_its_payload_at_the_scrutinees_args():
    """`Has(x)` of an `Opt<u16>` binds a u16, not the enum's raw `T`, so
    monomorph sees `x` at its instance (`Some(v) => v[1..3]` needs
    vec_slice<i32>)."""
    module = parse("""
enum Opt<T>
    Has(T)
    No

fn f(o: Opt<u16>) -> i32
    match o
        Has(x) =>
            let y = x
            0
        No => 1

fn main() -> i32
    0
""")
    table = typed.type_module(module)
    assert _name(table.type_of(_let_value(module, "y"))) == "u16"


# A built-in Option / Result the checker doesn't declare (the emitter
# instantiates it): its variant's payload is the scrutinee's type arg all the
# same -- Some and Ok take T, Err takes E (AGAST #4099).
BUILTIN_VARIANT_ROWS = [
    ("Result<i32, Vec<u16>>", "Ok(x)", "i32"),
    ("Result<i32, Vec<u16>>", "Err(x)", "Vec<u16>"),
    ("@Result<i32, Vec<u16>>", "Result.Err(x)", "Vec<u16>"),
    ("Option<Vec<u16>>", "Some(x)", "Vec<u16>"),
]


def _a_builtin_variant_pattern_binds_its_payload_at_the_scrutinees_args(
        scrut, pattern, expected):
    module = parse(VEC + f"""
fn f(o: {scrut}) -> i32
    match o
        {pattern} =>
            let y = x
            0
        _ => 1

fn main() -> i32
    0
""")
    table = typed.type_module(module)
    assert _name(table.type_of(_let_value(module, "y"))) == expected


def _monomorph_slices_an_err_payload_from_the_table_alone():
    """`Err(x) => x.len()` of a Result<i32, Vec<u16>> instantiates
    vec_len<u16> from the table's type for `x`: monomorph keeps no binding
    types of its own to fall back on (AGAST #4099)."""
    module = parse(VEC + """
fn f(o: Result<i32, Vec<u16>>) -> i64
    match o
        Err(x) => x.len()
        _ => 0

fn main() -> i32
    0
""")
    assert "vec_len$u16" in _fn_names(monomorphize(module))
    assert not hasattr(monomorph.Monomorphizer, "_pattern_bindings")
    assert "var_types" not in inspect.getsource(monomorph.Monomorphizer._type_of)


def _an_undefined_structs_literal_still_types_its_values():
    """A built-in struct the checker doesn't declare (`Span`) is one monomorph
    knows: its literal's args bind from its values, so they are typed."""
    module = parse("fn main() -> i32\n    let t = Nope { a: 3 as u8 }\n    0\n")
    table = typed.type_module(module)
    ((_, value),) = _let_value(module, "t").fields
    assert _name(table.type_of(value)) == "u8"


def _a_global_named_like_a_type_does_not_shadow_it_as_a_receiver():
    """`S.make()` beside a global `var S: i32` is the static call: only a
    local shadows the type (test_static_ufcs_inferred_ptr's batched rows)."""
    module = parse("""
struct S
    n: i32

impl S
    fn make() -> S
        S { n: 1 }

var S: i32 = 5

fn main() -> i32
    let t = S.make()
    0
""")
    table = typed.type_module(module)
    assert _name(table.type_of(_let_value(module, "t"))) == "S"


# --- the two tests: every row runs, every failing row is named ---------------

def _failures(rows):
    """Run each `(name, check)` row; the `name: error` of each that raised."""
    failed = []
    for name, check in rows:
        try:
            check()
        except Exception as e:  # an AssertionError, or a crash in a pass
            failed.append(f"{name}: {type(e).__name__}: {e}")
    return failed


def test_the_typing_pass_types_each_row():
    """The type checker instantiates generics (GENERIC_ROWS), and the types
    it now gives don't break --check-types or what monomorph binds from them."""
    rows = [(f"{value} is {expected}",
             lambda v=value, x=expected: _a_generic_is_typed_at_its_type_args(v, x))
            for value, expected in GENERIC_ROWS]
    rows += [(f"{pattern} of {scrut} binds {expected}",
              lambda s=scrut, p=pattern, x=expected:
              _a_builtin_variant_pattern_binds_its_payload_at_the_scrutinees_args(s, p, x))
             for scrut, pattern, expected in BUILTIN_VARIANT_ROWS]
    rows += [(f"{value!r} in a -> {ret} fn is {expected}",
              lambda r=ret, v=value, x=expected: _a_generic_variant_is_typed_at_its_instance(r, v, x))
             for ret, value, expected in VARIANT_ROWS]
    rows += [(check.__name__.lstrip("_"), check) for check in (
        _an_option_or_result_predicate_is_a_bool,
        _a_vec_range_is_a_span_view_in_a_span_slot,
        _an_argless_literal_binds_from_a_literal_bound_before_it,
        _a_generic_variant_pattern_binds_its_payload_at_the_scrutinees_args,
        _an_undefined_structs_literal_still_types_its_values,
        _a_global_named_like_a_type_does_not_shadow_it_as_a_receiver,
    )]
    assert _failures(rows) == []


def test_monomorph_instantiates_each_row():
    """Monomorph reads the table (and types an untyped module itself), so it
    instantiates at the table's types, in templates and their copies alike."""
    rows = [(check.__name__.lstrip("_"), check) for check in (
        _monomorph_takes_a_receivers_type_from_the_table,
        _monomorph_types_an_untyped_module_itself,
        _a_copied_node_is_typed_as_the_template_node_it_copies,
        _an_instance_body_is_typed_at_its_type_args,
        _monomorph_has_no_inferrers_of_its_own,
        _an_address_of_binds_t_as_a_pointer,
        _monomorph_slices_an_err_payload_from_the_table_alone,
        _monomorph_takes_a_variants_instance_from_the_table,
        _an_unbound_variant_is_still_monomorphs_located_error,
    )]
    assert _failures(rows) == []
