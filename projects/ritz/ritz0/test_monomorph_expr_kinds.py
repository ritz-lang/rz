"""
ritz0 monomorph must reach type parameters and generic calls nested inside
*every* expression / statement kind (AGAST #1937).

`_specialize_stmt` / `_specialize_expr` used to return any node kind without
its own case unchanged, so `sizeof(T)`, casts and generic calls nested in a
Match, Grouped, TupleLit, Lambda, InterpString, SliceExpr, AssignExpr,
UnsafeBlock, ... kept the template's `T` (and `sizeof(T)` then read 8, the
size of an unresolved name).  `_rewrite_stmt` / `_rewrite_expr`, the same walk
for non-generic fns, had the same hole for generic *calls*: `(g<i32>(0))` was
left pointing at the generic template, which is removed from the module.

Each case below wraps one probe in one node kind, splices it into a generic
fn (or a non-generic fn for the rewrite side), runs the pass and checks the
probe came out specialized.  The AST is built by hand so every kind is
covered, including those the surface syntax can only reach in some contexts.
"""

import dataclasses

import pytest

import ritz_ast as rast
from monomorph import monomorphize
from parser import parse


SKELETON = """
fn g<T>(x: T) -> i64
    0

fn h() -> i64
    0

fn main() -> i32
    g<i32>(0)
    0
"""

def _span():
    mod = parse(SKELETON)
    return mod.items[0].span


SP = _span()


def ident(name):
    return rast.Ident(SP, name)


def T():
    return rast.NamedType(SP, "T", [])


def sizeof_t():
    """The probe for generic fns: specialized at i32 it must read sizeof(i32)."""
    return rast.Call(SP, ident("sizeof"), [ident("T")], type_args=[])


def gcall():
    """The probe for non-generic fns: must be rewritten to the mangled g$i32."""
    return rast.Call(SP, ident("g"), [rast.IntLit(SP, 0)],
                     type_args=[rast.NamedType(SP, "i32", [])])


def walk(node):
    """Yield every AST object reachable from node (dataclass fields, lists)."""
    if isinstance(node, (list, tuple)):
        for x in node:
            yield from walk(x)
    elif dataclasses.is_dataclass(node) and not isinstance(node, type):
        yield node
        for f in dataclasses.fields(node):
            if f.name != "span":
                yield from walk(getattr(node, f.name))


def fn_named(mod, name):
    return next(i for i in mod.items if isinstance(i, rast.FnDef) and i.name == name)


# --- one wrapper per node kind ------------------------------------------------
# Each takes the probe expression and returns a Stmt containing it.

def as_stmt(e):
    return rast.ExprStmt(SP, e)


def wildcard_arm(body, guard=None):
    return rast.MatchArm(SP, rast.WildcardPattern(SP), guard, body)


EXPR_KINDS = {
    "grouped": lambda p: rast.Grouped(SP, p),
    "tuple_lit": lambda p: rast.TupleLit(SP, [p, rast.IntLit(SP, 1)]),
    "interp_string": lambda p: rast.InterpString(SP, ["a", "b"], [p]),
    "slice_start": lambda p: rast.SliceExpr(SP, ident("x"), p, None),
    "slice_end": lambda p: rast.SliceExpr(SP, ident("x"), None, p),
    "lambda_body": lambda p: rast.Lambda(SP, [], None, p),
    "closure_body": lambda p: rast.Closure(SP, [], p),
    "match_scrutinee": lambda p: rast.Match(SP, p, [wildcard_arm(rast.IntLit(SP, 0))]),
    "match_arm_body": lambda p: rast.Match(SP, ident("x"), [wildcard_arm(p)]),
    "match_arm_guard": lambda p: rast.Match(SP, ident("x"), [wildcard_arm(rast.IntLit(SP, 0), p)]),
    "await": lambda p: rast.Await(SP, p),
    "heap": lambda p: rast.HeapExpr(SP, p),
    "return_expr": lambda p: rast.ReturnExpr(SP, p),
    "assign_expr": lambda p: rast.AssignExpr(SP, ident("y"), p),
    # Nested: an unhandled kind inside an unhandled kind.
    "grouped_in_tuple": lambda p: rast.TupleLit(SP, [rast.Grouped(SP, p)]),
}

STMT_KINDS = {
    "unsafe_block": lambda p: rast.UnsafeBlock(SP, rast.Block(SP, [as_stmt(p)], None)),
    "asm_operand": lambda p: rast.AsmStmt(
        SP, "x86_64", "nop", [rast.AsmOperand("a", "r", p)]),
}


def all_wrappers():
    for name, wrap in EXPR_KINDS.items():
        yield name, (lambda w: lambda p: as_stmt(w(p)))(wrap)
    yield from STMT_KINDS.items()


WRAPPERS = dict(all_wrappers())


def specialize_with(stmt):
    """Splice stmt into g<T>'s body, monomorphize, return g$i32."""
    mod = parse(SKELETON)
    g = fn_named(mod, "g")
    g.body = rast.Block(SP, [stmt], rast.IntLit(SP, 0))
    return fn_named(monomorphize(mod), "g$i32")


def rewrite_with(stmt):
    """Splice stmt into non-generic h's body, monomorphize, return h."""
    mod = parse(SKELETON)
    h = fn_named(mod, "h")
    h.body = rast.Block(SP, [stmt], rast.IntLit(SP, 0))
    return fn_named(monomorphize(mod), "h")


def sizeof_args(fn):
    return [n.args[0].name for n in walk(fn.body)
            if isinstance(n, rast.Call) and isinstance(n.func, rast.Ident)
            and n.func.name == "sizeof"]


@pytest.mark.unit
@pytest.mark.parametrize("kind", sorted(WRAPPERS))
def test_sizeof_t_specialized_inside(kind):
    fn = specialize_with(WRAPPERS[kind](sizeof_t()))
    assert sizeof_args(fn) == ["i32"], kind


@pytest.mark.unit
@pytest.mark.parametrize("kind", sorted(WRAPPERS))
def test_generic_call_rewritten_inside(kind):
    fn = rewrite_with(WRAPPERS[kind](gcall()))
    callees = [n.func.name for n in walk(fn.body)
               if isinstance(n, rast.Call) and isinstance(n.func, rast.Ident)]
    assert callees == ["g$i32"], kind
    assert not [n for n in walk(fn.body)
                if isinstance(n, rast.Call) and n.type_args], kind


@pytest.mark.unit
def test_cast_target_specialized_inside_grouped():
    cast = rast.Cast(SP, ident("x"), T())
    fn = specialize_with(as_stmt(rast.Grouped(SP, cast)))
    targets = [n.target.name for n in walk(fn.body) if isinstance(n, rast.Cast)]
    assert targets == ["i32"]


@pytest.mark.unit
def test_lambda_and_closure_types_specialized():
    lam = rast.Lambda(SP, [rast.Param(SP, "p", T())], T(), ident("p"))
    clo = rast.Closure(SP, [rast.ClosureParam("q", T())], ident("q"))
    mod = parse(SKELETON)
    g = fn_named(mod, "g")
    g.body = rast.Block(SP, [as_stmt(lam), as_stmt(clo)], rast.IntLit(SP, 0))
    fn = fn_named(monomorphize(mod), "g$i32")
    names = [n.name for n in walk(fn.body) if isinstance(n, rast.NamedType)]
    assert names == ["i32", "i32", "i32"]


@pytest.mark.unit
def test_template_is_not_mutated():
    """Specializing must copy: the template's own probe still names T."""
    mod = parse(SKELETON)
    g = fn_named(mod, "g")
    probe = sizeof_t()
    grouped = rast.Grouped(SP, probe)
    g.body = rast.Block(SP, [as_stmt(grouped)], rast.IntLit(SP, 0))
    monomorphize(mod)
    assert grouped.expr is probe
    assert probe.args[0].name == "T"


@pytest.mark.unit
def test_ticket_repro_parsed():
    """The source from AGAST #1937: Grouped and Match arms around sizeof(T)."""
    src = """
fn g<T>(x: T, k: i64) -> i64
    let a = (sizeof(T))
    let b = match k
        0 => sizeof(T)
        _ => 0
    return a * 10 + b

fn main() -> i32
    g<i32>(0, 0)
    0
"""
    fn = fn_named(monomorphize(parse(src)), "g$i32")
    assert sizeof_args(fn) == ["i32", "i32"]
