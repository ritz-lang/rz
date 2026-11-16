"""One typing pass annotates the AST; the checkers read it (LARB review/5
ritz0 N1, AGAST #3448).

ritz0 typed expressions in four places (type_checker, move_checker, monomorph,
the emitter), each re-deriving the same rules.  `typed.type_module` is now the
one walk that types a module: it leaves a `Typed` side table, keyed by node,
on `module.typed`.  It runs on every compile, as `ritz0._type`, not only under
`--check-types`; that flag now only decides whether its type errors are
reported (turning them on by default is #1823).  The move checker takes the
types of literals, casts, struct literals and calls from the table; its own
rules for those kinds are gone.  Monomorph and the emitter still infer for
themselves (follow-up tickets).

No compiles: every case parses a few lines in-process, in milliseconds.
"""

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
    table.record(call, rast.NamedType(None, "Res", []))
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
