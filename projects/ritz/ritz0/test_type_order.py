"""AGAST #3653: type_order.order_identified_types, on llvmlite types directly.

test_fn_type_field_type_order.py runs real programs through all three
compilers.  These cover what no valid Ritz program reaches: a by-value cycle
through fn parameters (clang can't accept any order of it, but ordering must
still terminate), and a struct reached through a literal struct (tuple)
parameter.
"""

import pytest
from llvmlite import ir

from type_order import order_identified_types

pytestmark = pytest.mark.unit

I64 = ir.IntType(64)


def _names(ctx):
    return list(ctx.identified_types)


def test_by_value_cycle_terminates():
    ctx = ir.Context()
    a = ctx.get_identified_type("A")
    b = ctx.get_identified_type("B")
    a.set_body(ir.FunctionType(I64, [b]).as_pointer())
    b.set_body(ir.FunctionType(I64, [a]).as_pointer())
    order_identified_types(ctx)
    # No order is valid; it must terminate and lose neither type.
    assert sorted(_names(ctx)) == ["A", "B"]


def test_struct_inside_tuple_param_is_ordered_first():
    ctx = ir.Context()
    info = ctx.get_identified_type("Info")
    s = ctx.get_identified_type("S")
    info.set_body(ir.FunctionType(I64, [ir.LiteralStructType([s, I64])]).as_pointer())
    s.set_body(I64, I64)
    order_identified_types(ctx)
    assert _names(ctx) == ["S", "Info"]
