"""AGAST #3762: an untyped local in an `async fn` that awaits takes its value's type.

In an `async fn` with an `await`, every local lives in the fn's future struct
(async_transform_v2).  An untyped local's type was None, so the struct got no
field for it while the constructor still set one, and ritz0 died with a Python
traceback, `ValueError: Unknown field y in struct go_Future`.  #1318 typed only
`let v = await f(x)`, as the poll's i32.

The transform runs before emission, so it infers the local's type from what it
can see: literals, params and earlier locals, operators, casts, awaits and
calls to declared fns.  Anything else is refused at the `let`, asking for a
type, rather than guessed at.

What the local then HOLDS at run time is #3727's: with an await, the state
machine runs only the awaits and the tail, so a `let y = x + 1` is skipped,
typed or not.  The run row below is a strict xfail on it.

ritz0 only: ritz1 has no async fns (ritz1/src/main.ritz).
"""

import re

import batching
import pytest
import ritz_ast as rast
from async_transform_v2 import generate_state_machine
from parser import parse
from test_borrow_param_ref_field import _batch_compile, _compile, _run

_FETCH = "async fn fetch(x: i32) -> i32\n    x\n\n"
_TWICE = "fn twice(n: i32) -> i32\n    n * 2\n\n"
_PAIR = "struct Pair\n    a: i32\n    b: i32\n\n"
_MAIN = "pub fn main() -> i32\n    var f: go_Future = go(7)\n    return go_poll(@f)\n"


def _go(body: str, params: str = "x: i32") -> str:
    return _FETCH + _TWICE + _PAIR + f"async fn go({params}) -> i32\n" + body + "\n"


def _type_name(ty) -> str:
    if isinstance(ty, rast.PtrType):
        return "*" + _type_name(ty.inner)
    return ty.name


def _future_fields(body: str, params: str = "x: i32") -> dict:
    """go_Future's fields, name -> type, as the emitter's transform builds it."""
    module = parse(_go(body, params), "main.ritz")
    fns = {item.name: item for item in module.items if isinstance(item, rast.FnDef)}
    sm = generate_state_machine(fns["go"], {"fetch", "go"}, fns)
    return {name: _type_name(ty) for name, ty in sm.future_struct.fields}


_AWAIT = "    let v: i32 = await fetch(x)\n    v\n"

# One row per inference rule: name -> (go's body, the local, its field's type[, go's params]).
TYPES = {
    "binop_of_param": ("    let y = x + 1\n" + _AWAIT, "y", "i32"),
    # The ticket's other row: the await's i32, through the `+`.
    "await_in_binop": ("    let w = (await fetch(x)) + 1\n    w\n", "w", "i32"),
    "await_alone": ("    let w = await fetch(x)\n    w\n", "w", "i32"),
    # A literal is i64, as an untyped `let` of one is outside an async fn.
    "int_literal": ("    let y = 5\n" + _AWAIT, "y", "i64"),
    "bool_literal": ("    let y = true\n" + _AWAIT, "y", "bool"),
    # A literal operand takes the other operand's type (LARB R21).
    "literal_left_operand": ("    let y = 2 * (x as u8)\n" + _AWAIT, "y", "u8"),
    "shift_keeps_left": ("    let y = 1 << (x as u8)\n" + _AWAIT, "y", "i64"),
    "comparison_is_bool": ("    let y = x > 3\n" + _AWAIT, "y", "bool"),
    "not_is_bool": ("    let y = !(x > 3)\n" + _AWAIT, "y", "bool"),
    "negation": ("    let y = -(x as i16)\n" + _AWAIT, "y", "i16"),
    "cast": ("    let y = x as u8\n" + _AWAIT, "y", "u8"),
    "call_return_type": ("    let y = twice(x)\n" + _AWAIT, "y", "i32"),
    # A bare async call is the callee's future (AGAST #1395).
    "async_call_is_future": ("    var y = fetch(x)\n" + _AWAIT, "y", "fetch_Future"),
    # An earlier untyped local's inferred type flows on.
    "local_of_local": ("    let y = x as u16\n    let z = y\n" + _AWAIT, "z", "u16"),
    "param_pointer": ("    let y = p\n    let v: i32 = await fetch(0)\n    v\n", "y", "*i32", "p: *i32"),
    "var_after_await": ("    let v: i32 = await fetch(x)\n    var w = v\n    w\n", "w", "i32"),
    "in_if_arm": ("    if x > 0\n        let y = x + 1\n        let v: i32 = await fetch(y)\n        v\n"
                  "    else\n        0\n", "y", "i32"),
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(TYPES))
def test_untyped_async_local_takes_its_values_type(name):
    body, local, want, *params = TYPES[name]
    fields = _future_fields(body, *params)
    assert fields.get(local) == want, f"{name}: go_Future fields {fields}"


@pytest.mark.unit
def test_untyped_local_without_an_await_needs_no_type():
    """With no await there is no future state, so nothing is refused: a field
    access stays an ordinary local, emitted as any other fn's."""
    assert "y" not in _future_fields("    let y = p.a\n    y\n", "p: Pair")


# The ticket's program now compiles: go_Future has its `y`.
@pytest.mark.integration
@pytest.mark.batched
def test_ticket_program_compiles(tmp_path):
    src = _go("    let y = x + 1\n    let v: i32 = await fetch(y)\n    v + 1\n") + _MAIN
    comp, ll, _ = _compile("ritz0", None, tmp_path, "ticket", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists() and "Traceback" not in out, out[-2000:]


@pytest.mark.integration
@pytest.mark.batched
def test_ticket_program_runs(tmp_path):
    src = _go("    let y = x + 1\n    let v: i32 = await fetch(y)\n    v + 1\n") + _MAIN
    assert _run("ritz0", None, tmp_path, "ticket_run", src) == 9


def _located(text):
    """`text` without its `^`, and where the `^` was as `line:col`."""
    before = text[:text.index("^")]
    line = before.count("\n") + 1
    return text.replace("^", "", 1), f"{line}:{len(before) - before.rfind(chr(10))}"


# name -> (program with `^` at the diagnostic, the local's name)
REFUSALS = {
    # A field's type needs the struct's definition, which the transform does
    # not consult: refused at the `let`, not a traceback.
    "field_access": (_go("    ^let y = p.a\n    let v: i32 = await fetch(y)\n    v\n", "p: Pair") + _MAIN, "y"),
    # An untyped local after the await is a field too.
    "after_await": (_go("    let v: i32 = await fetch(x)\n    ^var w = p.b\n    v\n", "x: i32, p: Pair")
                    + _MAIN.replace("go(7)", "go(7, Pair { a: 1, b: 2 })"), "w"),
}


@pytest.mark.integration
@pytest.mark.batched
@pytest.mark.parametrize("name", sorted(REFUSALS))
def test_untyped_async_local_of_unknown_type_is_refused(tmp_path, name):
    marked, local = REFUSALS[name]
    message = (f"cannot infer the type of `{local}`, which `go`'s future holds across an `await`: "
               f"give `{local}` a type (`let {local}: T = ...`)")
    src, where = _located(marked)
    got = batching.refused("ritz0", src, _batch_compile(None), at=tuple(map(int, where.split(":"))))
    if got is not None:  # AGAST #2806: this row's diagnostics from its chunk's batch
        out, where = got
    else:
        comp, _ll, _ = _compile("ritz0", None, tmp_path, name, src)
        out = comp.stdout + comp.stderr
        assert comp.returncode != 0, f"ritz0 accepted {name}:\n{src}"
    assert "Traceback" not in out, f"{name}: a traceback, not a diagnostic\n{out[-2000:]}"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert (where, message) in found, f"{name}, wanted {where}: {message}\n{src}\n{out[-2000:]}"
