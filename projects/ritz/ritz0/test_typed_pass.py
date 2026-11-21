"""One typing pass annotates the AST; the checkers read it (LARB review/5
ritz0 N1, AGAST #3448).

ritz0 typed expressions in four places (type_checker, move_checker, monomorph,
the emitter), each re-deriving the same rules.  `typed.type_module` is now the
one walk that types a module: it leaves a `Typed` side table, keyed by node,
on `module.typed`.  It runs on every compile, as `ritz0._type`, and
`ritz0._check_types` reports its type errors on every compile too, after
emission (AGAST #3556 removed the `--check-types` flag that gated them;
#4260 kept the emitter's words where both refuse).  The move checker takes the
types of literals, casts, struct literals and calls from the table; its own
rules for those kinds are gone.  So does the emitter, for typed.EMITTER_READS
(#3555, #4066), and so does monomorph (#3554, test_monomorph_reads_typed.py).

Every case but two parses a few lines in-process, in milliseconds; the
win64 call case and the sizeof-call case compile once.
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
    """The pass collects every type error, which _check_types prints.
    The slot errors (§13.2) are their own list:
    the ownership pass prints those beside a move error."""
    module = parse("fn f(n:& i32) -> i32\n    let x: i32 = c\"no\"\n"
                   "    let p: @i32 = n\n    0\n")
    table = typed.type_module(module)
    assert [("*u8" in str(e), VALUE_INTO_SHARED_REF in str(e)) for e in table.errors] \
        == [(True, False), (False, True), (False, False)]
    assert [VALUE_INTO_SHARED_REF in str(e) for e in table.slot_errors] == [True]


# --- the pass list -----------------------------------------------------------

def test_the_typing_pass_runs_before_the_checkers_that_read_it():
    """...and its own errors are reported after emission, so the emitter's
    words win where both refuse (AGAST #4260, test_type_errors_after_emit)."""
    names = [p.__name__ for p in ritz0.PASSES]
    assert names.index("_type") < names.index("_check_ownership") \
        < names.index("_emit") < names.index("_check_types") < names.index("_write")
    assert names.index("_infer_struct_lit_args") < names.index("_type")


def test_a_compile_walks_its_module_with_the_type_checker_once(tmp_path, monkeypatch):
    """The type errors and the slot rules beside an ownership error used to
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
    ok = ritz0.compile_file(str(src), str(tmp_path / "a.ll"), check_ownership=True)
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


# --- the kinds whose rules moved to the table (#3553, #4065) -----------------

def test_the_move_checker_reads_the_table_for_every_kind_it_types():
    """Every kind the move checker types comes from the table: its own
    rules (and the `read_*` / `len` name heuristic) are gone.  Index stays
    unknown on purpose (#2268)."""
    for kind in (rast.UnaryOp, rast.BinOp, rast.TryOp, rast.ArrayLit,
                 rast.ArrayFill, rast.TupleLit, rast.NullLit,
                 rast.Ident, rast.Field, rast.Match, rast.MethodCall):
        assert kind in typed.MOVE_CHECKER_READS, kind
    assert set(MoveChecker.EXPR_TYPES) == set(typed.MOVE_CHECKER_READS)
    assert rast.Index not in MoveChecker.EXPR_TYPES
    rules = [n for n in vars(MoveChecker) if n.startswith("_type_of_")]
    assert rules == []
    assert not hasattr(MoveChecker, "PRIMITIVES")


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


OPTION = "enum Option<T>\n    Some(T)\n    None\n\nstruct Big\n    a: i64\n\n"


def test_a_payload_binding_has_its_payloads_type():
    """`Some(b) => b`: the move checker's scope gave a payload binding no
    type; the table types it at the scrutinee's `T`."""
    module = parse(OPTION + "fn f(o: Option<Big>) -> i64\n"
                   "    match o\n        Some(b) => b.a\n        None => 0\n")
    typed.type_module(module)
    b = next(e for e in _nodes(module, rast.Ident) if e.name == "b")
    assert _name(_checker_on(module)._infer_expr_type(b)) == "Big"


def test_a_match_is_typed_without_walking_its_arms():
    """A match's type is the table's, not one the walk notes on the node
    while its arms are in scope (`value_type`, AGAST #2178)."""
    module = parse(OPTION + "fn f(o: Option<Big>) -> Big\n"
                   "    match o\n        Some(b) => b\n        None => Big { a: 0 }\n")
    typed.type_module(module)
    (match,) = _nodes(module, rast.Match)
    assert _name(_checker_on(module)._infer_expr_type(match)) == "Big"


def test_a_generic_method_is_typed_at_its_receivers_arguments():
    """`o.get()` on an `Option<Big>`: the impl's `T` is the receiver's
    `Big` (#3554), with no name heuristic behind it."""
    module = parse(OPTION + "impl<T> Option<T>\n    fn get(self) -> T\n"
                   "        match self\n            Some(v) => v\n"
                   "            None => panic(c\"none\")\n\n"
                   "fn f(o: Option<Big>) -> i64\n    let b = o.get()\n    b.a\n")
    typed.type_module(module)
    (call,) = _nodes(module, rast.MethodCall)
    assert _name(_checker_on(module)._infer_expr_type(call)) == "Big"


def test_a_field_is_its_declared_type():
    module = parse("struct Pair\n    big: Big\n    n: u8\n\nstruct Big\n    a: i64\n\n"
                   "fn f(p: Pair) -> u8\n    let n = p.n\n    n\n")
    typed.type_module(module)
    field = next(e for e in _nodes(module, rast.Field) if e.field == "n")
    assert _name(_checker_on(module)._infer_expr_type(field)) == "u8"


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


U8_PTR_SLOTS = """
type CStr = *u8

fn take(p: *u8) -> i64
    0

fn view(v: StrView) -> i64
    0

fn named(c: bool) -> CStr
    if c
        "yes"
    else
        "no"

fn main() -> i32
    take("arg")
    view("not")
    let p: *u8 = "let"
    0
"""


def test_a_string_literal_in_a_u8_ptr_slot_is_a_u8_ptr():
    """LARB R3: a `"..."` takes `*u8` from a `*u8` slot (an argument, a
    `let`, an `if`'s tails, through an alias) and is a StrView anywhere
    else.  The emitter reads this instead of the `as_ptr` its slot rule
    sets as it emits (#4068)."""
    module = parse(U8_PTR_SLOTS)
    table = typed.type_module(module)
    got = {lit.value: type_to_string(table.type_of(lit))
           for lit in _nodes(module, rast.StringLit)}
    assert got == {"arg": "*u8", "not": "StrView", "let": "*u8",
                   "yes": "*u8", "no": "*u8"}


UNKNOWN_FIRST_ARM = """
fn f(x: i64) -> i32
    let r = match x
        1 => mystery()
        2 =>
            mystery()
            return 1
        _ => 5 as u8
    let s = match x
        1 =>
            return 2
        _ => 6 as u16
    let t = match x
        1 => mystery()
        _ =>
            mystery()
            return 3
    0
"""


def test_a_match_is_its_first_arm_with_a_known_type():
    """An arm the pass can't type (`unknown`), or one that leaves (a block
    ending in `return`, typed void: angelo's hello_world.ritz), doesn't decide
    the match's type; the next arm with a known type does, as the emitter's
    _note_match_result_type did: `Ok(s) => s[1..3]` before
    `Err(e) => span_empty<u8>()` is a Span<u8>, whose bytes widen unsigned
    (test_issue_slice_generic_payload.ritz, #4068)."""
    module = parse(UNKNOWN_FIRST_ARM)
    table = typed.type_module(module)
    got = [_name(table.type_of(m)) for m in _nodes(module, rast.Match)]
    # `t` is angelo's inner match: nothing known, so the emitter's own typing.
    assert got == ["u8", "u16", "unknown"]


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
    module = parse("fn f(x: u8) -> i64\n    let a = 5\n    let b = x as u16\n    let c = 'c'\n"
                   "    let s = \"s\"\n    let m = match x\n        _ => 1\n    0\n")
    table = typed.type_module(module)
    (lit,) = [e for e in _nodes(module, rast.IntLit) if e.value == 5]
    (cast,) = _nodes(module, rast.Cast)
    (char,) = _nodes(module, rast.CharLit)
    (string,) = _nodes(module, rast.StringLit)
    (match,) = _nodes(module, rast.Match)
    # A "..." the emitter had marked as_ptr, a match with no result_ritz_type:
    # their old rules would say `*u8` and nothing (#4068).
    string.as_ptr = True
    rows = ((lit, "u32"), (cast, "i8"), (char, "i16"), (string, "StrView"), (match, "u64"))
    for node, ty in rows:
        table.record(node, rast.NamedType(None, ty, []))
    em = _emitter_over(table)
    assert [_name(em._infer_ritz_type(n)) for n, _ in rows] == [ty for _, ty in rows]
    # Signedness of a cast and a char comes from the table too.
    assert [em._infer_unsigned_expr(n) for n in (cast, char)] == [False, False]


CALL_METHOD_ARRAY = """
struct S
    v: i32

impl S
    fn get(self: @&S) -> i32
        self.v

fn make() -> i32
    7

fn main() -> i32
    let s = S { v: 1 }
    let c = make()
    let m = s.get()
    let a = [1u8, 2u8]
    c + m + a[0] as i32
"""


def test_the_emitter_reads_method_calls_and_array_literals_from_the_table():
    """MethodCall and ArrayLit joined EMITTER_READS (#4066).  Their old rules
    resolved the method's declared return type and the first element's; the
    emitter answers with the table's type instead.  Call stayed: the emitter
    synthesises calls the pass never types, and reads an async fn's call as
    its post-transform future."""
    module = parse(CALL_METHOD_ARRAY)
    table = typed.type_module(module)
    (method,) = _nodes(module, rast.MethodCall)
    (array,) = _nodes(module, rast.ArrayLit)
    rows = ((method, "i8"), (array, "bool"))
    for node, ty in rows:
        table.record(node, rast.NamedType(None, ty, []))
    em = _emitter_over(table)
    assert [_name(em._infer_ritz_type(n)) for n, _ in rows] == [ty for _, ty in rows]


def test_an_untyped_let_reaches_the_array_literals_old_rule():
    """No corpus input reached `_infer_ritz_type(ArrayLit)` (#4066), so its
    agreement there meant nothing.  An untyped `let a = [..]` does reach it,
    and the table types the literal as the old rule did, so the read is safe."""
    module = parse("fn main() -> i32\n    let a = [1u8, 2u8, 3u8]\n    a[0] as i32\n")
    table = typed.type_module(module)
    (array,) = _nodes(module, rast.ArrayLit)
    assert _name(table.type_of(array)) == "[3]u8"
    assert _name(_emitter_over(table)._infer_ritz_type(array)) == "[3]u8"


SIZEOF_OPERANDS = """
struct S
    v: i32

impl S
    fn get(self: @&S) -> i32
        self.v

fn bump() -> i32
    return 1

fn main() -> i32
    let s = S { v: 1 }
    let a = sizeof(bump())
    let b = sizeof(s.get())
    (a + b) as i32
"""


def test_a_sizeof_operand_of_a_method_call_is_typed():
    """The emitter reads a MethodCall's type from the table (#4066), so the
    typing pass must type `sizeof`'s operand of that kind: `sizeof(s.get())`
    would otherwise have no type to measure.  A Call's operand stays untyped;
    its type is still the emitter's rule to find."""
    module = parse(SIZEOF_OPERANDS)
    table = typed.type_module(module)
    (bump,) = [c for c in _nodes(module, rast.Call)
               if isinstance(c.func, rast.Ident) and c.func.name == 'bump']
    (get,) = _nodes(module, rast.MethodCall)
    assert table.type_of(bump) is None
    assert _name(table.type_of(get)) == "i32"


def test_sizeof_a_method_call_operand_compiles(tmp_path):
    """The end-to-end form of the rule above: before #4066 the emitter's own
    MethodCall rule measured it; it is now the table's, so it must be recorded.
    `sizeof(bump())` alongside it is a Call's operand, still the emitter's."""
    src = tmp_path / "a.ritz"
    src.write_text(SIZEOF_OPERANDS)
    assert ritz0.compile_file(str(src), str(tmp_path / "a.ll"), check_ownership=True)


def test_the_emitter_reads_unknown_as_no_type():
    module = parse("fn f() -> i64\n    let a = 5\n    0\n")
    table = typed.type_module(module)
    (lit,) = [e for e in _nodes(module, rast.IntLit) if e.value == 5]
    table.record(lit, rast.NamedType(None, "unknown", []))
    assert _emitter_over(table)._infer_ritz_type(lit) is None


def test_the_emitter_has_no_rules_the_table_replaced():
    """`_infer_float_expr` only ever called itself (#3555); a match's type is
    the table's, not one noted on the node as its arms are emitted (#4068)."""
    from emitter_llvmlite import LLVMEmitter
    assert not hasattr(LLVMEmitter, "_infer_float_expr")
    assert not hasattr(LLVMEmitter, "_note_match_result_type")


def test_the_checker_types_an_untyped_globals_initialiser():
    """`var g = 'A'` is refused, naming the type to write (`u8`): the emitter
    reads that type off the table (test_global_init_rejected.py)."""
    module = parse("var g = 'A'\nvar h = -5\n\nfn main() -> i32\n    0\n")
    table = typed.type_module(module)
    (char,) = _nodes(module, rast.CharLit)
    (neg,) = _nodes(module, rast.UnaryOp)
    assert [_name(table.type_of(n)) for n in (char, neg)] == ["u8", "i64"]
    assert table.errors == []
