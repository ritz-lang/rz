"""`s.as_bytes()` on a StrView is a `Span<u8>` to the typing pass (AGAST #3599).

`as_bytes` is an emitter built-in: no ritzlib fn declares it, and the
emitter turns `s.as_bytes()` into a `Span<u8>` of the view's bytes. The
typing pass typed every built-in StrView method as `unknown`, so after
`let bytes = text.as_bytes()` the checker saw `bytes` as unknown and
reported `expected Span<u8>, got @unknown` at a `Span<u8>` slot (angelo's
shaper, four sites). Typed, `bytes` passes as itself, and `@bytes` is what
LARB R1 refuses: an `@Span<u8>` is not a `Span<u8>`.

The same branch must also read ritzlib's `impl StrView` methods (AGAST
#4925): it typed `s.parse_i64()` as `unknown`, and an `unknown` receiver
makes monomorph want a method on *every* instance, so `s.parse_i64().
unwrap_or(0)` instantiated `Result<String, E>.unwrap_or` too and the
compile failed in ritzlib/result.ritz at a line the program never called.

No compiles: every case parses a few lines in-process.
"""

import pytest

import ritz_ast as rast
import typed
from metadata import type_to_string
from parser import parse

pytestmark = pytest.mark.unit

# A stand-in for ritzlib's `impl StrView`: one plain return, one generic.
IMPL = """\
enum Opt<T>
    Some(T)
    None

impl StrView
    pub fn count(self: StrView) -> i64
        self.len
    pub fn number(self: StrView) -> Opt<i64>
        Opt.None

"""

FIRST = "fn first(b: Span<u8>, i: usize) -> i32\n    b[i] as i32\n\n"


def _errors(source: str) -> list:
    return [str(e) for e in typed.type_module(parse(source)).errors]


def _method_type(source: str, method: str = "as_bytes") -> str:
    """The type the pass gave the one `.method()` call in `source`."""
    module = parse(source)
    table = typed.type_module(module)
    calls = []

    def walk(node):
        if isinstance(node, rast.MethodCall) and node.method == method:
            calls.append(node)
        if isinstance(node, list):
            for x in node:
                walk(x)
        elif isinstance(node, rast.Node):
            for value in vars(node).values():
                if isinstance(value, (list, rast.Node)):
                    walk(value)

    walk(module.items)
    (call,) = calls
    ty = table.type_of(call)
    return type_to_string(ty) if ty is not None else None


@pytest.mark.parametrize("param", ["StrView", "@StrView"])
def test_strview_methods_are_typed(param):
    # A by-value receiver and one read through a borrow: the emitter loads both.
    src = f"fn f(s: {param}) -> i64\n    let b = s.as_bytes()\n    b.len\n"
    assert _method_type(src) == "Span<u8>"
    assert _errors(src) == []
    # An `impl StrView` method is its declared return type, generic or not.
    for method, want in (("count", "i64"), ("number", "Opt<i64>")):
        src = IMPL + f"fn f(s: {param}) -> i32\n    let n = s.{method}()\n    0\n"
        assert _method_type(src, method) == want, method
        assert _errors(src) == [], method


def test_bound_bytes_fill_a_span_slot():
    # The ticket's repro, written as R1 asks: `bytes`, not `@bytes`.
    src = FIRST + ("pub fn shape(text: StrView) -> i32\n"
                   "    let bytes = text.as_bytes()\n"
                   "    first(bytes, 0) - 65\n")
    assert _errors(src) == []


def test_borrowed_bytes_are_refused_at_a_by_value_span():
    # LARB R1: no auto-deref. The error names the real type, not `@unknown`.
    src = FIRST + ("pub fn shape(text: StrView) -> i32\n"
                   "    let bytes = text.as_bytes()\n"
                   "    first(@bytes, 0) - 65\n")
    errs = _errors(src)
    assert errs, "an @Span<u8> passed to a by-value Span<u8> must be refused"
    assert not any("unknown" in e for e in errs), errs
    assert any("expected Span<u8>" in e for e in errs), errs


def test_as_bytes_with_arguments_stays_untyped():
    # The emitter refuses `as_bytes(x)`; the pass doesn't claim a type for it.
    src = "fn f(s: StrView) -> i32\n    s.as_bytes(1)\n    0\n"
    assert _method_type(src) != "Span<u8>"


def test_only_a_strview_receiver_gets_the_built_in():
    # The pass's built-in receivers share one branch; `as_bytes` is StrView's.
    src = "fn f(x: Span<u8>) -> i32\n    x.as_bytes()\n    0\n"
    assert _method_type(src) != "Span<u8>"


def test_other_strview_built_ins_are_not_spans():
    # `s.len()`, StrView's other built-in, is not a `Span<u8>`.
    module = parse("fn f(s: StrView) -> i32\n    s.len()\n    0\n")
    table = typed.type_module(module)
    stmt = module.items[0].body.stmts[0]
    call = getattr(stmt, "expr", stmt)
    assert isinstance(call, rast.MethodCall) and call.method == "len"
    ty = table.type_of(call)
    assert ty is None or type_to_string(ty) != "Span<u8>"
