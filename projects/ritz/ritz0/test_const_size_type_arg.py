"""AGAST #2857: a const-named array size inside an expression is folded.

const_eval walked a Call's args but not its type_args, and skipped whole
expression kinds (struct literals, method calls, grouping, `?`, lambdas,
`sizeof`, assignments...).  So with `const N: i64 = 2`, the `[N]i8` in
`first<*[N]i8>(@x)` kept `size = Ident('N')` and ritz0 died with an internal
TypeError in llvmlite (since #2843, in mangle_type_name) instead of compiling.

The rule: after const eval, every array size reachable anywhere in a
function body is an int.  ritz1 already folded these; it is the oracle.
"""

import dataclasses
import subprocess

import pytest

from const_eval import ConstEvalError, evaluate_array_sizes
from lexer import Lexer
from parser import Parser
import ritz_ast as rast

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with

PRELUDE = (
    "const N: i64 = 2\n"
    "struct Box<T>\n    v: T\n    tag: i64\n\n"
    "struct S\n    a: i64\n\n"
    "impl S\n    fn take(self: *S, p: *[2]i8) -> i64\n        0\n\n"
    "fn first<T>(a: T) -> T\n    a\n\n"
)

# Where a `[N]i8` can sit inside a function body, one row per expression
# kind const_eval used to skip.  Each body declares `x: [2]i8`.
FORMS = {
    "call_type_arg": "let p: *[2]i8 = first<*[N]i8>(@x)",
    "struct_lit_type_arg": "let b: Box<[2]i8> = Box<[N]i8> { v: x, tag: 0 }",
    "method_call_arg": "var s: S = S { a: 0 }\n    s.take(first<*[N]i8>(@x))",
    "grouped": "let p: *[2]i8 = (first<*[N]i8>(@x))",
    "sizeof": "let n: i64 = sizeof([N]i8)",
    "assign_value": "var p: *[2]i8 = @x\n    p = first<*[N]i8>(@x)",
    "lambda_param": "let f: fn(*[2]i8) -> i64 = fn(p: *[N]i8) -> i64 0",
    "tuple_type": "let t: (i64, [N]i8) = (1, x)",
    "nested_type_arg": "let b: Box<Box<[N]i8>> = Box<Box<[N]i8>> { v: Box<[N]i8> { v: x, tag: 0 }, tag: 0 }",
}


def _parse(source: str) -> rast.Module:
    return Parser(list(Lexer(source, "test").tokenize())).parse_module()


def _array_sizes(node, seen=None):
    """Every ArrayType size reachable from `node`, by walking all AST fields."""
    seen = set() if seen is None else seen
    if id(node) in seen:
        return
    seen.add(id(node))
    if isinstance(node, (list, tuple)):
        for item in node:
            yield from _array_sizes(item, seen)
    elif isinstance(node, rast.Node):
        if isinstance(node, rast.ArrayType):
            yield node.size
        for f in dataclasses.fields(node):
            if f.name != "span":
                yield from _array_sizes(getattr(node, f.name), seen)


@pytest.mark.parametrize("form", FORMS)
def test_size_in_expression_is_folded(form):
    module = _parse(
        PRELUDE + "pub fn main() -> i32\n    var x: [2]i8 = [1, 2]\n"
        f"    {FORMS[form]}\n    0\n")
    # The parser must have produced an unfolded size for the row to mean anything.
    assert any(isinstance(s, rast.Ident) for s in _array_sizes(module)), form
    assert evaluate_array_sizes(module) == []
    sizes = list(_array_sizes(module))
    assert all(type(s) is int for s in sizes), sizes


@pytest.mark.parametrize("item", [
    "enum E\n    A([N]i8)\n    B\n",
    "trait T\n    fn f(self: *Self, p: *[N]i8) -> i64\n",
])
def test_size_in_item_is_folded(item):
    """Not only fns, structs, globals and aliases: an enum payload's array was
    left an IntLit that the emitter unwrapped by hand."""
    module = _parse("const N: i64 = 2\n" + item)
    assert any(isinstance(s, rast.Ident) for s in _array_sizes(module)), item
    assert evaluate_array_sizes(module) == []
    sizes = list(_array_sizes(module))
    assert all(type(s) is int for s in sizes), sizes


def test_unknown_const_in_type_arg_is_a_diagnostic():
    module = _parse(
        PRELUDE + "pub fn main() -> i32\n    var x: [2]i8 = [1, 2]\n"
        "    let p: *[2]i8 = first<*[M]i8>(@x)\n    0\n")
    errors = evaluate_array_sizes(module)
    assert len(errors) == 1 and isinstance(errors[0], ConstEvalError)
    assert "M" in str(errors[0])


COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# The ticket's repro, plus a struct literal and a folded expression.  Each
# returns 0, or the number of the check that failed.
PROGRAMS = {
    "call": (
        "const N: i64 = 2\n"
        "fn first<T>(a: T) -> T\n    a\n\n"
        "pub fn main() -> i32\n"
        "    var x: [2]i8 = [1, 2]\n"
        "    let px: *[N]i8 = first<*[N]i8>(@x)\n"
        "    if px[1] != 2\n        return 1\n"
        "    0\n",
        "first$ptr_arr2_i8"),
    "struct_lit": (
        "const N: i64 = 2\n"
        "struct Box<T>\n    v: T\n    tag: i64\n\n"
        "pub fn main() -> i32\n"
        "    let b: Box<[N]i8> = Box<[N]i8> { v: [1, 2], tag: 7 }\n"
        "    if b.tag != 7\n        return 1\n"
        "    if b.v[1] != 2\n        return 2\n"
        "    0\n",
        "Box$arr2_i8"),
    "expr_size": (
        "const N: i64 = 2\n"
        "fn first<T>(a: T) -> T\n    a\n\n"
        "pub fn main() -> i32\n"
        "    var x: [4]i8 = [1, 2, 3, 4]\n"
        "    let px: *[4]i8 = first<*[N * 2]i8>(@x)\n"
        "    if px[3] != 4\n        return 1\n"
        "    0\n",
        "first$ptr_arr4_i8"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", PROGRAMS)
def test_program_compiles_and_runs(ritz1_bin, compile_with, compiler, name):
    program, symbol = PROGRAMS[name]
    comp, ll, work = compile_with(compiler, name, program)
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr
    assert symbol in ll.read_text(), f"{compiler} did not name {symbol}"
    link, exe = for_header._link(compiler, ritz1_bin, ll, work)
    assert link.returncode == 0, link.stderr
    assert subprocess.run([str(exe)], timeout=60).returncode == 0
