"""
Struct Layout Registry

Computes and caches struct field layouts with proper alignment and padding.
Extracted from emitter_llvmlite.py for modularity.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List
import ritz_ast as rast


@dataclass
class FieldLayout:
    """Layout information for a single struct field."""
    name: str
    index: int          # Field index (0-based)
    offset: int         # Byte offset from struct start
    size: int           # Size in bytes
    alignment: int      # Alignment requirement
    ritz_type: rast.Type  # Original Ritz type


@dataclass
class StructLayout:
    """Complete layout information for a struct."""
    name: str
    fields: List[FieldLayout]
    size: int           # Total size in bytes (with padding)
    alignment: int      # Struct alignment (max of field alignments)

    def get_field(self, name: str) -> Optional[FieldLayout]:
        """Get field layout by name."""
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def get_field_index(self, name: str) -> int:
        """Get field index by name. Raises if not found."""
        for f in self.fields:
            if f.name == name:
                return f.index
        raise ValueError(f"Unknown field '{name}' in struct '{self.name}'")


class StructRegistry:
    """
    Registry for struct layouts with computed field offsets.

    Computes proper alignment and padding for structs, eliminating
    the need for hardcoded offsets like parser_alloc(p, 160).

    Alignment rules (x86_64 System V ABI):
    - i8/u8:   1 byte alignment
    - i16/u16: 2 byte alignment
    - i32/u32: 4 byte alignment
    - i64/u64: 8 byte alignment
    - pointers: 8 byte alignment
    - arrays: alignment of element type
    - structs: max alignment of fields
    """

    def __init__(self):
        # name -> StructLayout
        self._layouts: Dict[str, StructLayout] = {}
        # Pending structs (declared but not yet laid out)
        self._pending: Dict[str, List[Tuple[str, rast.Type]]] = {}
        # Track which structs are packed (no alignment padding)
        self._packed: set = set()

    def declare(self, name: str, fields: List[Tuple[str, rast.Type]], packed: bool = False) -> None:
        """Declare a struct with its fields. Layout is computed lazily."""
        self._pending[name] = fields
        if packed:
            self._packed.add(name)

    def compute_layout(self, name: str, type_resolver) -> StructLayout:
        """
        Compute and cache the layout for a struct.

        Args:
            name: Struct name
            type_resolver: Callable(rast.Type) -> (size, alignment) for resolving types
        """
        if name in self._layouts:
            return self._layouts[name]

        if name not in self._pending:
            raise ValueError(f"Unknown struct: {name}")

        fields = self._pending[name]
        field_layouts = []
        current_offset = 0
        max_alignment = 1
        is_packed = name in self._packed

        for idx, (field_name, field_type) in enumerate(fields):
            size, alignment = type_resolver(field_type)
            if not is_packed:
                max_alignment = max(max_alignment, alignment)

                # Add padding for alignment
                if current_offset % alignment != 0:
                    current_offset += alignment - (current_offset % alignment)
            # For packed structs, alignment is 1 and no padding is added

            field_layouts.append(FieldLayout(
                name=field_name,
                index=idx,
                offset=current_offset,
                size=size,
                alignment=1 if is_packed else alignment,
                ritz_type=field_type
            ))

            current_offset += size

        # Add tail padding for struct alignment (not for packed structs)
        if not is_packed and current_offset % max_alignment != 0:
            current_offset += max_alignment - (current_offset % max_alignment)

        layout = StructLayout(
            name=name,
            fields=field_layouts,
            size=current_offset,
            alignment=max_alignment
        )
        self._layouts[name] = layout
        return layout

    def get_layout(self, name: str) -> Optional[StructLayout]:
        """Get computed layout for a struct, or None if not computed yet."""
        return self._layouts.get(name)

    def get_field_index(self, struct_name: str, field_name: str) -> int:
        """Get field index by name. Raises if struct/field not found."""
        layout = self._layouts.get(struct_name)
        if layout is None:
            raise ValueError(f"Struct '{struct_name}' layout not computed")
        return layout.get_field_index(field_name)

    def get_size(self, struct_name: str) -> int:
        """Get total size of a struct in bytes."""
        layout = self._layouts.get(struct_name)
        if layout is None:
            raise ValueError(f"Struct '{struct_name}' layout not computed")
        return layout.size

    def get_alignment(self, struct_name: str) -> int:
        """Get alignment of a struct."""
        layout = self._layouts.get(struct_name)
        if layout is None:
            raise ValueError(f"Struct '{struct_name}' layout not computed")
        return layout.alignment
