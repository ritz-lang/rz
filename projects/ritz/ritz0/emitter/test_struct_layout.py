"""
Tests for the struct layout registry.

Validates field alignment, padding, and struct sizing follow
x86_64 System V ABI rules.
"""

import pytest
import sys
from pathlib import Path

# Add ritz0 to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from emitter.struct_layout import FieldLayout, StructLayout, StructRegistry
import ritz_ast as rast
from tokens import Span


def _span():
    return Span("<test>", 0, 0, 0)


def _named(name):
    return rast.NamedType(_span(), name, [])


def _ptr(inner):
    return rast.PtrType(_span(), inner, mutable=False)


def _array(size, elem):
    return rast.ArrayType(_span(), size, elem)


def simple_resolver(ty):
    """Simple type resolver for testing: returns (size, alignment)."""
    if isinstance(ty, rast.NamedType):
        sizes = {
            'i8': (1, 1), 'u8': (1, 1),
            'i16': (2, 2), 'u16': (2, 2),
            'i32': (4, 4), 'u32': (4, 4),
            'i64': (8, 8), 'u64': (8, 8),
            'f32': (4, 4), 'f64': (8, 8),
            'bool': (1, 1),
        }
        return sizes.get(ty.name, (8, 8))
    elif isinstance(ty, rast.PtrType):
        return (8, 8)  # Pointers are 8 bytes on x86_64
    elif isinstance(ty, rast.ArrayType):
        elem_size, elem_align = simple_resolver(ty.inner)
        count = ty.size if isinstance(ty.size, int) else 1
        return (elem_size * count, elem_align)
    return (8, 8)


class TestFieldLayout:
    def test_basic_field(self):
        fl = FieldLayout("x", 0, 0, 4, 4, _named("i32"))
        assert fl.name == "x"
        assert fl.size == 4


class TestStructLayout:
    def test_get_field(self):
        layout = StructLayout("Point", [
            FieldLayout("x", 0, 0, 4, 4, _named("i32")),
            FieldLayout("y", 1, 4, 4, 4, _named("i32")),
        ], size=8, alignment=4)
        assert layout.get_field("x").index == 0
        assert layout.get_field("y").index == 1
        assert layout.get_field("z") is None

    def test_get_field_index(self):
        layout = StructLayout("Point", [
            FieldLayout("x", 0, 0, 4, 4, _named("i32")),
            FieldLayout("y", 1, 4, 4, 4, _named("i32")),
        ], size=8, alignment=4)
        assert layout.get_field_index("x") == 0
        assert layout.get_field_index("y") == 1
        with pytest.raises(ValueError):
            layout.get_field_index("z")


class TestStructRegistry:
    def test_simple_struct(self):
        """Two i32 fields: no padding, size=8, align=4."""
        reg = StructRegistry()
        reg.declare("Point", [("x", _named("i32")), ("y", _named("i32"))])
        layout = reg.compute_layout("Point", simple_resolver)
        assert layout.size == 8
        assert layout.alignment == 4
        assert len(layout.fields) == 2
        assert layout.fields[0].offset == 0
        assert layout.fields[1].offset == 4

    def test_padding_between_fields(self):
        """i8 followed by i32: 3 bytes padding after i8."""
        reg = StructRegistry()
        reg.declare("Padded", [("a", _named("i8")), ("b", _named("i32"))])
        layout = reg.compute_layout("Padded", simple_resolver)
        assert layout.fields[0].offset == 0  # a at 0
        assert layout.fields[1].offset == 4  # b at 4 (3 bytes padding)
        assert layout.size == 8  # 4 + 4 = 8
        assert layout.alignment == 4

    def test_tail_padding(self):
        """Struct with i32 + i8: needs tail padding to reach alignment."""
        reg = StructRegistry()
        reg.declare("TailPad", [("a", _named("i32")), ("b", _named("i8"))])
        layout = reg.compute_layout("TailPad", simple_resolver)
        assert layout.fields[0].offset == 0
        assert layout.fields[1].offset == 4
        assert layout.size == 8  # 4 + 1 + 3 padding = 8
        assert layout.alignment == 4

    def test_pointer_alignment(self):
        """Pointer field forces 8-byte alignment."""
        reg = StructRegistry()
        reg.declare("WithPtr", [
            ("tag", _named("i8")),
            ("ptr", _ptr(_named("u8"))),
        ])
        layout = reg.compute_layout("WithPtr", simple_resolver)
        assert layout.fields[0].offset == 0
        assert layout.fields[1].offset == 8  # 7 bytes padding after i8
        assert layout.size == 16
        assert layout.alignment == 8

    def test_packed_struct(self):
        """Packed struct: no padding, alignment=1."""
        reg = StructRegistry()
        reg.declare("Packed", [
            ("a", _named("i8")),
            ("b", _named("i32")),
        ], packed=True)
        layout = reg.compute_layout("Packed", simple_resolver)
        assert layout.fields[0].offset == 0
        assert layout.fields[1].offset == 1  # No padding!
        assert layout.size == 5  # 1 + 4 = 5
        assert layout.alignment == 1  # Packed = align 1

    def test_cached_layout(self):
        """Second call returns cached layout."""
        reg = StructRegistry()
        reg.declare("Point", [("x", _named("i32")), ("y", _named("i32"))])
        layout1 = reg.compute_layout("Point", simple_resolver)
        layout2 = reg.compute_layout("Point", simple_resolver)
        assert layout1 is layout2

    def test_unknown_struct(self):
        """Requesting layout for undeclared struct raises."""
        reg = StructRegistry()
        with pytest.raises(ValueError, match="Unknown struct"):
            reg.compute_layout("Nonexistent", simple_resolver)

    def test_get_size_and_alignment(self):
        reg = StructRegistry()
        reg.declare("Point", [("x", _named("i32")), ("y", _named("i32"))])
        reg.compute_layout("Point", simple_resolver)
        assert reg.get_size("Point") == 8
        assert reg.get_alignment("Point") == 4

    def test_array_field(self):
        """Array field: [4]i32 = 16 bytes, align 4."""
        reg = StructRegistry()
        reg.declare("WithArray", [
            ("data", _array(4, _named("i32"))),
            ("len", _named("i64")),
        ])
        layout = reg.compute_layout("WithArray", simple_resolver)
        assert layout.fields[0].offset == 0
        assert layout.fields[0].size == 16  # 4 * 4 = 16
        assert layout.fields[1].offset == 16  # aligned to 8
        assert layout.size == 24  # 16 + 8 = 24

    def test_string_like_struct(self):
        """String struct: ptr + len + cap = 24 bytes."""
        reg = StructRegistry()
        reg.declare("String", [
            ("data", _ptr(_named("u8"))),
            ("len", _named("i64")),
            ("cap", _named("i64")),
        ])
        layout = reg.compute_layout("String", simple_resolver)
        assert layout.fields[0].offset == 0
        assert layout.fields[1].offset == 8
        assert layout.fields[2].offset == 16
        assert layout.size == 24
        assert layout.alignment == 8
