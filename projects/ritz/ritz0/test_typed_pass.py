"""One typing pass annotates the AST; the checkers read it (LARB review/5
ritz0 N1, AGAST #3448).

ritz0 typed expressions in four places (type_checker, move_checker, monomorph,
the emitter), each re-deriving the same rules.  `typed.type_module` is now the
one walk that types a module: it leaves a `Typed` side table, keyed by node,
on `module.typed`.  It runs on every compile, as `ritz0._type`, not only under
`--check-types`; that flag now only decides whether its type errors are
reported (turning them on by default is #1823).  The move checker takes the
types of literals, casts, struct literals and calls from the table; its own
rules for those kinds are gone.  So does the emitter, for typed.EMITTER_READS
(#3555).  Monomorph still infers for itself (#3554).

Every case but one parses a few lines in-process, in milliseconds; the
win64 call case compiles once.
"""

import pytest

import ritz0
import ritz_ast as rast
import type_checker
import typed
from metadata import type_to_string
from move_checker import MoveChecker
from parser import parse
from ref_rules import VALUE_INTO_SHARED_REF

SOURCE = """
struct Point
    x: i32
    y: i32

fn make() -> Point
    Point { x: 1, y: 2 }

fn act()
    pass

fn main() -> i32
    let n = 42
    let s = "hi"
    let p = make()
    let q = n as u8
    act()
    0
"""


def _nodes(module, kind):
    """Every `kind` node in `module`, in walk order."""
    found = []

    def walk(node):
        if isinstance(node, kind):
            found.append(node)
        if isinstance(node, (list, tuple)):
            for x in node:
                walk(x)
        elif isinstance(node, rast.Node):
            for value in vars(node).values():
                if isinstance(value, (list, tuple, rast.Node)):
                    walk(value)

    walk(module.items)
    return found


def _name(ty):
    return type_to_string(ty) if ty is not None else None


# --- the table ---------------------------------------------------------------

def test_type_module_types_every_expression_kind_it_walks():
    module = parse(SOURCE)
    table = typed.type_module(module)
    assert module.typed is table
    (n_lit,) = [e for e in _nodes(module, rast.IntLit) if e.value == 42]
    assert _name(table.type_of(n_lit)) == "i64"
    (s_lit,) = _nodes(module, rast.StringLit)
    assert _name(table.type_of(s_lit)) == "StrView"
    calls = {c.func.name: c for c in _nodes(module, rast.Call)}
    assert _name(table.type_of(calls["make"])) == "Point"
    assert _name(table.type_of(calls["act"])) == "void"
    (cast,) = _nodes(module, rast.Cast)
    assert _name(table.type_of(cast)) == "u8"


def test_the_table_is_keyed_by_node_not_by_equal_nodes():
    """Two `0` literals are equal dataclasses; each is its own entry, and a
    node the pass never saw has none (not its twin's)."""
    module = parse(SOURCE)
    table = typed.type_module(module)
    stranger = rast.IntLit(None, 42)
    assert table.type_of(stranger) is None


def test_type_errors_are_kept_whether_or_not_they_are_reported():
    """The pass collects every type error; `--check-types` only decides
    whether ritz0 prints them.  The slot errors (§13.2) are their own list:
    the ownership pass prints those beside a move error."""
    module = parse("fn f(n:& i32) -> i32\n    let x: i32 = c\"no\"\n"
                   "    let p: @i32 = n\n    0\n")
    table = typed.type_module(module)
    assert [("*u8" in str(e), VALUE_INTO_SHARED_REF in str(e)) for e in table.errors] \
        == [(True, False), (False, True), (False, False)]
    assert [VALUE_INTO_SHARED_REF in str(e) for e in table.slot_errors] == [True]


# --- the pass list -----------------------------------------------------------

def test_the_typing_pass_runs_before_the_checkers_that_read_it():
    names = [p.__name__ for p in ritz0.PASSES]
    assert names.index("_type") < names.index("_check_types") \
        < names.index("_check_ownership") < names.index("_emit")
    assert names.index("_infer_struct_lit_args") < names.index("_type")


def test_the_typing_pass_runs_without_check_types(tmp_path, monkeypatch):
    seen = {}

    def stop(ctx):
        seen["typed"] = getattr(ctx.module, "typed", None)
        return False

    names = [p.__name__ for p in ritz0.PASSES]
    monkeypatch.setattr(ritz0, "PASSES", ritz0.PASSES[:names.index("_type") + 1] + (stop,))
    src = tmp_path / "a.ritz"
    src.write_text(SOURCE)
    ritz0.compile_file(str(src), str(tmp_path / "a.ll"), check_types=False)
    assert isinstance(seen["typed"], typed.Typed) and len(seen["typed"]) > 0


def test_a_compile_walks_its_module_with_the_type_checker_once(tmp_path, monkeypatch):
    """`--check-types` and the slot rules beside an ownership error used to
    walk the module once each; both now read the one typing pass."""
    walks = []
    real = type_checker.TypeChecker.check

    def counting(self, module, *args, **kwargs):
        walks.append(module)
        return real(self, module, *args, **kwargs)

    monkeypatch.setattr(type_checker.TypeChecker, "check", counting)
    src = tmp_path / "a.ritz"
    src.write_text("""
struct Res
    fd: i32

impl Drop for Res
    fn drop(self: @&Res)
        pass

fn take(r: Res)
    pass

fn main() -> i32
    let r = Res { fd: 1 }
    take(r)
    take(r)
    0
""")
    ok = ritz0.compile_file(str(src), str(tmp_path / "a.ll"), check_ownership=True,
                            check_types=True)
    assert ok is False
    assert len(walks) == 1


# --- the move checker reads it ----------------------------------------------

DROP_SOURCE = """
struct Res
    fd: i32

impl Drop for Res
    fn drop(self: @&Res)
        pass

fn mystery() -> i32
    7

fn main() -> i32
    mystery()
    0
"""


def test_the_move_checker_takes_a_calls_type_from_the_table():
    """Retype `mystery()` in the table as the move-only `Res`: the move
    checker now sees a move-only temporary there and marks it for a drop.
    Its own rule (the callee's declared `i32`) would not."""
    module = parse(DROP_SOURCE)
    table = typed.type_module(module)
    (call,) = [c for c in _nodes(module, rast.Call) if c.func.name == "mystery"]
    table.record(call, rast.NamedType(None, "Res", []), within=module.items[-1])
    MoveChecker().check(module)
    assert _name(getattr(call, "drop_temp", None)) == "Res"


def test_the_move_checker_takes_a_literals_type_from_the_table():
    module = parse("fn main() -> i32\n    let x = 5\n    0\n")
    table = typed.type_module(module)
    (lit,) = [e for e in _nodes(module, rast.IntLit) if e.value == 5]
    table.record(lit, rast.NamedType(None, "u16", []))
    checker = MoveChecker()
    checker.typed = table
    assert _name(checker._infer_expr_type(lit)) == "u16"


def test_the_move_checker_types_an_untyped_module_itself():
    """A caller that hands the move checker a module no pass typed (the
    emitter's own tests, a fresh monomorphised module) still gets types."""
    module = parse(DROP_SOURCE)
    assert getattr(module, "typed", None) is None
    MoveChecker().check(module)
    assert isinstance(module.typed, typed.Typed)


def test_the_move_checker_has_no_rules_of_its_own_for_the_kinds_it_reads():
    for kind in typed.MOVE_CHECKER_READS:
        assert MoveChecker.EXPR_TYPES[kind] is MoveChecker._type_from_table, kind


# --- a node shared by two bodies (AGAST #3553) --------------------------------

SHARED_SOURCE = """
fn a(v: i32) -> i32
    let w = v
    w

fn b(v: u8) -> u8
    let w = v
    w
"""


def _sharing_bodies():
    """SHARED_SOURCE with `b` given `a`'s body, as monomorph shares every
    subtree an instance leaves unchanged (monomorph.map_child_nodes)."""
    module = parse(SHARED_SOURCE)
    fn_a, fn_b = module.items
    fn_b.body = fn_a.body
    return module, fn_a, fn_b


def test_a_node_two_bodies_share_has_each_bodys_type():
    """Read `within` a body, the table answers for that body, not for
    whichever body was typed last."""
    module, fn_a, fn_b = _sharing_bodies()
    table = typed.type_module(module)
    (v,) = {id(e): e for e in _nodes(module, rast.Ident) if e.name == "v"}.values()
    assert _name(table.type_of(v, within=fn_a)) == "i32"
    assert _name(table.type_of(v, within=fn_b)) == "u8"
    assert table.type_of(v, within=rast.FnDef(None, "c", [], None, None)) is None


def test_the_move_checker_reads_each_body_at_its_own_types():
    module, fn_a, fn_b = _sharing_bodies()
    table = typed.type_module(module)
    (v,) = {id(e): e for e in _nodes(module, rast.Ident) if e.name == "v"}.values()
    table.record(v, rast.NamedType(None, "u16", []), within=fn_a)
    checker = MoveChecker()
    checker.typed = table
    seen = []
    for fn in (fn_a, fn_b):
        checker._body = fn
        seen.append(_name(checker._type_from_table(v)))
    assert seen == ["u16", "u8"]


# --- the kinds whose rules moved to the table (#3553) -------------------------

def test_the_move_checker_reads_the_table_for_the_non_generic_kinds():
    """UnaryOp, BinOp, TryOp, the aggregate and null literals: their own
    rules are gone.  Ident, Field, Match and MethodCall wait for the pass to
    type a generic's members at its instance (#3554); Index stays unknown on
    purpose (#2268)."""
    for kind in (rast.UnaryOp, rast.BinOp, rast.TryOp, rast.ArrayLit,
                 rast.ArrayFill, rast.TupleLit, rast.NullLit):
        assert kind in typed.MOVE_CHECKER_READS, kind
        assert MoveChecker.EXPR_TYPES[kind] is MoveChecker._type_from_table, kind
    assert rast.Index not in MoveChecker.EXPR_TYPES
    gone = ("_type_of_unary", "_type_of_binop", "_type_of_try",
            "_type_of_array_lit", "_type_of_tuple_lit")
    assert not [n for n in gone if hasattr(MoveChecker, n)]


def _checker_on(module):
    """A MoveChecker reading `module`'s table in its last fn."""
    checker = MoveChecker()
    checker.typed = module.typed
    checker._body = module.items[-1]
    return checker


def test_an_address_of_is_a_reference():
    """`@x` makes a reference (LANGUAGE_SPEC §13.2): `&Big`, as the typing
    pass says, where the move checker's own rule said `*Big`.  Only a
    declared `*T` slot reads it as a pointer (_hold_loans)."""
    module = parse("struct Big\n    a: i64\n\nfn main() -> i32\n"
                   "    let b = Big { a: 1 }\n    let p = @b\n    0\n")
    typed.type_module(module)
    (addr,) = _nodes(module, rast.UnaryOp)
    ty = _checker_on(module)._infer_expr_type(addr)
    assert isinstance(ty, rast.RefType) and not ty.mutable and _name(ty.inner) == "Big"


def test_a_comparison_is_a_bool():
    """`a < b` is a bool, not its left operand's type."""
    module = parse("fn main() -> i32\n    let a: u16 = 1\n    let c = a < 2\n    0\n")
    typed.type_module(module)
    (cmp,) = _nodes(module, rast.BinOp)
    assert _name(_checker_on(module)._infer_expr_type(cmp)) == "bool"


def test_try_on_an_option_gives_its_payload():
    module = parse("enum Option<T>\n    Some(T)\n    None\n\n"
                   "fn f(o: Option<u32>) -> Option<u32>\n    let x = o?\n    Some(x)\n")
    typed.type_module(module)
    (try_op,) = _nodes(module, rast.TryOp)
    assert _name(_checker_on(module)._infer_expr_type(try_op)) == "u32"


def test_an_undeclared_struct_literals_fields_are_still_typed():
    """`Nope { ptr: @a }` with no `Nope` declared: the type error is the
    literal's; its field values are typed all the same, so the move checker
    still finds `@a` in the table."""
    module = parse("fn f() -> i32\n    var a: u16 = 1\n"
                   "    let s = Nope { ptr: @a, len: 3 }\n    0\n")
    typed.type_module(module)
    (addr,) = _nodes(module, rast.UnaryOp)
    ty = _checker_on(module)._infer_expr_type(addr)
    assert isinstance(ty, rast.RefType) and _name(ty.inner) == "u16"


# --- the emitter (#3555) -----------------------------------------------------

WIN64_CALL = """
[[callconv = "win64"]]
type Svc2 = fn(u64, u64) -> u64

fn call_it(p: u64) -> u64
    (p as Svc2)(1, 2)
"""


def test_the_checker_types_an_indirect_calls_callee():
    """`(p as Svc2)(...)`: the emitter reads the callee cast's type for the
    call's callconv, so the pass has to have typed it."""
    module = parse(WIN64_CALL)
    table = typed.type_module(module)
    (cast,) = _nodes(module, rast.Cast)
    assert _name(table.type_of(cast)) == "Svc2"
    assert table.errors == []


@pytest.mark.integration
def test_a_call_through_a_cast_to_a_win64_alias_stays_win64cc(tmp_path):
    """The harland UEFI loader's shape: the emitter takes the callee's
    callconv from the table, and a callee the pass never typed lost
    `win64cc`, so the call used the SysV registers."""
    from ritz0_inproc import run_ritz0
    src = tmp_path / "main.ritz"
    src.write_text(WIN64_CALL + "\npub fn main() -> i32\n    0\n")
    ll = tmp_path / "main.ll"
    result = run_ritz0([str(src), "-o", str(ll)], cwd=str(tmp_path))
    assert result.returncode == 0, result.stderr
    calls = [l for l in ll.read_text().splitlines() if " = call " in l and "(i64 1, i64 2)" in l]
    assert len(calls) == 1 and "call win64cc i64" in calls[0], calls


def test_the_checker_types_an_option_try_as_its_payload():
    """`o?` on an `Option<T>` is a `T`, as on a `Result<T, E>`: the emitter
    registers `let v = o?` for its scope-end drop by that type (#2264)."""
    module = parse("fn f(o: Option<u16>) -> Option<u16>\n    let v = o?\n    Some(v)\n")
    table = typed.type_module(module)
    (try_op,) = _nodes(module, rast.TryOp)
    assert _name(table.type_of(try_op)) == "u16"


def test_the_checker_types_a_sizeof_value_operand():
    module = parse("fn f(x: u8) -> i64\n    sizeof(x as u16)\n")
    table = typed.type_module(module)
    (cast,) = _nodes(module, rast.Cast)
    assert _name(table.type_of(cast)) == "u16"


def _emitter_over(table):
    """An emitter with the table and no aliases: the kinds it reads need no
    other state."""
    from emitter_llvmlite import LLVMEmitter
    em = LLVMEmitter.__new__(LLVMEmitter)
    em.typed = table
    em.type_aliases = {}
    return em


def test_the_emitter_takes_the_types_of_the_kinds_it_reads_from_the_table():
    """Retype each node in the table: the emitter answers with the table's
    type, not a rule of its own (an int literal would be its own `i64`, a
    cast its target, a char a `u8`)."""
    module = parse("fn f(x: u8) -> i64\n    let a = 5\n    let b = x as u16\n    let c = 'c'\n    0\n")
    table = typed.type_module(module)
    (lit,) = [e for e in _nodes(module, rast.IntLit) if e.value == 5]
    (cast,) = _nodes(module, rast.Cast)
    (char,) = _nodes(module, rast.CharLit)
    for node, ty in ((lit, "u32"), (cast, "i8"), (char, "i16")):
        table.record(node, rast.NamedType(None, ty, []))
    em = _emitter_over(table)
    assert [_name(em._infer_ritz_type(n)) for n in (lit, cast, char)] == ["u32", "i8", "i16"]
    # Signedness of a cast and a char comes from the table too.
    assert [em._infer_unsigned_expr(n) for n in (cast, char)] == [False, False]


def test_the_emitter_reads_unknown_as_no_type():
    module = parse("fn f() -> i64\n    let a = 5\n    0\n")
    table = typed.type_module(module)
    (lit,) = [e for e in _nodes(module, rast.IntLit) if e.value == 5]
    table.record(lit, rast.NamedType(None, "unknown", []))
    assert _emitter_over(table)._infer_ritz_type(lit) is None


def test_the_emitter_has_no_float_inferer():
    """`_infer_float_expr` only ever called itself; it is gone (#3555)."""
    from emitter_llvmlite import LLVMEmitter
    assert not hasattr(LLVMEmitter, "_infer_float_expr")


def test_the_checker_types_an_untyped_globals_initialiser():
    """`var g = 'A'` is refused, naming the type to write (`u8`): the emitter
    reads that type off the table (test_global_init_rejected.py)."""
    module = parse("var g = 'A'\nvar h = -5\n\nfn main() -> i32\n    0\n")
    table = typed.type_module(module)
    (char,) = _nodes(module, rast.CharLit)
    (neg,) = _nodes(module, rast.UnaryOp)
    assert [_name(table.type_of(n)) for n in (char, neg)] == ["u8", "i64"]
    assert table.errors == []
