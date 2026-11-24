"""Struct layout and Ritz-to-LLVM type lowering (AGAST #1826, slice 4).

How a Ritz type is laid out in LLVM — the struct layout registry, the enum
payload/field layout, the Ritz-to-LLVM type lowering and the size/align
helpers behind `sizeof` — was spread through emitter_llvmlite.py.  It is now
this module: the layout records at module level and a `LayoutEmitter` mixin
for the methods, moved verbatim in the same order, so the emitted IR is
byte-identical; the corpus replay against the train-tail worktree is the
evidence for that.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from llvmlite import ir

import deref_rules
import ritz_ast as rast
from monomorph import resolve_alias_in
from monomorph_core import note_instance_display
from emitter.common import EmitError, InternalError, SourceError


def _abi_size_align(ty: ir.Type) -> tuple:
    """(alloc size, ABI alignment) of `ty` as LLVM lays it out on x86-64.

    Unlike _type_size_bytes this pads struct fields, so an array of structs
    is measured as ritz1's elem_size_align measures it: both compilers must
    agree which arrays cross SRET_MIN_BYTES (AGAST #2306).
    """
    if isinstance(ty, ir.IntType):
        size = max(1, (ty.width + 7) // 8)
        align = 1
        while align < size and align < 16:
            align *= 2
        return size, align
    if isinstance(ty, ir.FloatType):
        return 4, 4
    if isinstance(ty, ir.DoubleType):
        return 8, 8
    if isinstance(ty, ir.PointerType):
        return 8, 8
    if isinstance(ty, ir.ArrayType):
        size, align = _abi_size_align(ty.element)
        return ty.count * size, align
    if isinstance(ty, ir.VectorType):
        # x86-64: a vector is aligned to its size rounded up to a power of
        # two, and its alloc size is that rounded size (<4 x i64>: 32, 32).
        size = ty.count * _abi_size_align(ty.element)[0]
        align = 1
        while align < size:
            align *= 2
        return align, align
    if isinstance(ty, ir.BaseStructType) and ty.elements is not None:
        packed = getattr(ty, 'packed', False)
        off, max_align = 0, 1
        for el in ty.elements:
            size, align = _abi_size_align(el)
            if packed:
                align = 1
            off = (off + align - 1) // align * align + size
            max_align = max(max_align, align)
        return (off + max_align - 1) // max_align * max_align, max_align
    return 8, 8


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
        raise InternalError(f"Unknown field '{name}' in struct '{self.name}'")


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
            raise InternalError(f"Unknown struct: {name}")

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

    def is_pending(self, name: str) -> bool:
        """True if `name` is declared (laid out yet or not)."""
        return name in self._pending

    def get_layout(self, name: str) -> Optional[StructLayout]:
        """Get computed layout for a struct, or None if not computed yet."""
        return self._layouts.get(name)

    def get_field_index(self, struct_name: str, field_name: str) -> int:
        """Get field index by name. Raises if struct/field not found."""
        layout = self._layouts.get(struct_name)
        if layout is None:
            raise InternalError(f"Struct '{struct_name}' layout not computed")
        return layout.get_field_index(field_name)

    def get_size(self, struct_name: str) -> int:
        """Get total size of a struct in bytes."""
        layout = self._layouts.get(struct_name)
        if layout is None:
            raise InternalError(f"Struct '{struct_name}' layout not computed")
        return layout.size

    def get_alignment(self, struct_name: str) -> int:
        """Get alignment of a struct."""
        layout = self._layouts.get(struct_name)
        if layout is None:
            raise InternalError(f"Struct '{struct_name}' layout not computed")
        return layout.alignment


class LayoutEmitter:
    """Struct layout and type lowering for `LLVMEmitter`; mixed in with its bases."""

    def _struct_layout_on_demand(self, name: str) -> Optional[StructLayout]:
        """Layout of struct `name`, computing it now if it is only declared."""
        layout = self.struct_registry.get_layout(name)
        if layout is None and self.struct_registry.is_pending(name):
            layout = self.struct_registry.compute_layout(
                name, self._ritz_type_size_and_align
            )
        return layout

    def _ritz_type_size_and_align(self, ty: rast.Type) -> Tuple[int, int]:
        """Get size and alignment of a Ritz type in bytes.

        Used by StructRegistry to compute field layouts.

        Returns:
            (size_bytes, alignment_bytes)
        """
        # AGAST #2151: a field spelled through an alias (`g: Grid`,
        # `type Grid = [4][4]u8`) hit the unknown-type fallback of (8, 8)
        # below, so sizeof disagreed with the alias-resolved LLVM layout.
        ty = resolve_alias_in(ty, self.type_aliases)
        if isinstance(ty, rast.NamedType):
            # Primitive types
            primitives = {
                'i8': (1, 1), 'u8': (1, 1),
                'i16': (2, 2), 'u16': (2, 2),
                'i32': (4, 4), 'u32': (4, 4),
                'i64': (8, 8), 'u64': (8, 8),
                # AGAST #1814: f32 had no entry and fell back to (8, 8), so
                # sizeof of a struct with an f32 field disagreed with the
                # `{float, ...}` layout LLVM gives it.
                'f32': (4, 4), 'f64': (8, 8),
                'bool': (1, 1),
                # SIMD vector types (SSE2 128-bit, 16-byte aligned)
                'v2i64': (16, 16),  # 2 x 8 = 16 bytes
                'v4i32': (16, 16),  # 4 x 4 = 16 bytes
                'v8i16': (16, 16),  # 8 x 2 = 16 bytes
                'v16i8': (16, 16),  # 16 x 1 = 16 bytes
                # SIMD vector types (AVX2 256-bit, 32-byte aligned)
                'v4i64': (32, 32),  # 4 x 8 = 32 bytes
                'v8i32': (32, 32),  # 8 x 4 = 32 bytes
                'v16i16': (32, 32), # 16 x 2 = 32 bytes
                'v32i8': (32, 32),  # 32 x 1 = 32 bytes
            }
            if ty.name in primitives:
                return primitives[ty.name]

            # Struct types - get from registry, laying out on demand.
            # AGAST #1936: structs are laid out in source order, so a struct
            # declared later (or an enum payload naming one) used to miss here
            # and fall back to 8/8. Lazy layout can't recurse without bound: a
            # by-value struct cycle has infinite size and can't exist.
            layout = self._struct_layout_on_demand(ty.name)
            if layout:
                return (layout.size, layout.alignment)
            # The built-in `{ *u8, i64 }` view, before anything registered
            # it: `Option<StrView>` was sized with an 8-byte payload (#2433).
            if ty.name == 'StrView':
                return (16, 8)

            # Enum types (AGAST #1923): their real all-i8 layout, not 8/8.
            enum_sa = self._enum_size_and_align(ty.name)
            if enum_sa:
                return enum_sa

            # Unmangled generic instantiation (e.g. `Span<u8>`): the registry
            # is keyed by the specialized name, and built-in generics may not
            # be materialized yet. Resolve it rather than guessing 8 bytes.
            if ty.args:
                specialized = self._get_specialized_type_name(ty)
                # On demand: `Box$Box_i32` is defined before `Box$i32`, so its
                # field `Box<i32>` sized as 8 by the fallback below (#3268).
                layout = self._struct_layout_on_demand(specialized)
                if layout:
                    return (layout.size, layout.alignment)
                # Option<T> / Result<T, E> / generic user enums (#1923).
                if specialized not in self.enum_types:
                    self._ensure_builtin_generic_specialization(ty)
                enum_sa = self._enum_size_and_align(specialized)
                if enum_sa:
                    return enum_sa
                synthesized = self._ensure_builtin_generic_struct_specialization(ty)
                if synthesized and synthesized in self.struct_types:
                    llvm_ty = self.struct_types[synthesized]
                    # Padded, at its own alignment (AGAST #3655).
                    return _abi_size_align(llvm_ty)

            # Fallback for unknown types (treat as 8-byte pointer-sized)
            return (8, 8)

        elif isinstance(ty, rast.PtrType) or isinstance(ty, rast.RefType):
            # Pointers and references are 8 bytes on x86_64
            return (8, 8)

        elif isinstance(ty, rast.ArrayType):
            # Array: element_size * count, alignment = element alignment
            elem_size, elem_align = self._ritz_type_size_and_align(ty.inner)
            return (elem_size * ty.size, elem_align)

        elif isinstance(ty, rast.VectorType):
            # SIMD vector: size = count * element_size, alignment = total size
            # SSE2 vectors (128-bit) should be 16-byte aligned
            # AVX vectors (256-bit) should be 32-byte aligned
            elem_size, _ = self._ritz_type_size_and_align(ty.inner)
            total_size = elem_size * ty.count
            return (total_size, total_size)

        elif isinstance(ty, rast.TupleType):
            # Tuple: calculate size with proper alignment padding
            if not ty.elements:
                # Empty tuple: 0 bytes, 1-byte alignment (unit type)
                return (0, 1)
            total_size = 0
            max_align = 1
            for elem_ty in ty.elements:
                elem_size, elem_align = self._ritz_type_size_and_align(elem_ty)
                # Align element within the tuple
                if total_size % elem_align != 0:
                    total_size += elem_align - (total_size % elem_align)
                total_size += elem_size
                max_align = max(max_align, elem_align)
            # Align total size to max alignment (struct padding)
            if total_size % max_align != 0:
                total_size += max_align - (total_size % max_align)
            return (total_size, max_align)

        else:
            # Default fallback
            return (8, 8)

    # Primitive names `sizeof` accepts; their sizes come from
    # _ritz_type_size_and_align.
    _SIZEOF_PRIMITIVES = frozenset((
        'i8', 'u8', 'i16', 'u16', 'i32', 'u32', 'i64', 'u64',
        'f32', 'f64', 'bool',
        'v2i64', 'v4i32', 'v8i16', 'v16i8', 'v4i64', 'v8i32', 'v16i16', 'v32i8',
    ))

    def _sizeof_operand_size(self, call: rast.Call) -> int:
        """Size in bytes of `sizeof`'s operand (LANGUAGE_SPEC §7.9).

        The operand is a type (`sizeof(i32)`, `sizeof([8]u8)`) or an
        expression, whose *type* is measured: it is never evaluated, so no
        code is emitted for it. AGAST #2124: every non-type operand used to
        come out as 8, and so did an unknown type name, so
        `mem_zero(@key[0], sizeof(key))` wiped 8 bytes of a 64-byte key.
        Anything we can't size is now a compile error.
        """
        if len(call.args) != 1:
            raise EmitError("sizeof takes exactly one argument (a type or an expression)", call.span)
        arg = call.args[0]
        ty = self._sizeof_operand_type(arg)
        if ty is not None:
            size = self._sizeof_ritz_type(ty)
            if size is not None:
                return size
        if isinstance(arg, rast.Ident) and not self._sizeof_is_value(arg.name):
            raise EmitError(f"sizeof: unknown type or value `{arg.name}`", arg.span)
        # A value whose Ritz type isn't tracked: its storage type is exact,
        # unless it holds a struct (_type_size_bytes ignores padding).
        if isinstance(arg, rast.Ident):
            llvm_ty = self._sizeof_value_llvm_type(arg.name)
            elem = llvm_ty
            while isinstance(elem, ir.ArrayType):
                elem = elem.element
            if llvm_ty is not None and not isinstance(elem, ir.BaseStructType):
                return self._type_size_bytes(llvm_ty)
        raise EmitError("sizeof: cannot determine the type of this expression", arg.span)

    def _sizeof_is_value(self, name: str) -> bool:
        return (name in self.locals or name in self.params or name in self.globals
                or name in self.const_arrays or name in self.constants)

    def _sizeof_value_llvm_type(self, name: str) -> Optional[ir.Type]:
        for table in (self.locals, self.params, self.globals, self.const_arrays):
            if name in table:
                return table[name][1]
        if name in self.constants:
            return self.constants[name][1]
        return None

    def _sizeof_operand_type(self, arg: rast.Expr) -> Optional[rast.Type]:
        """The Ritz type `sizeof` measures, or None if it can't be found."""
        if isinstance(arg, rast.TypeExpr):
            return arg.ty
        if isinstance(arg, rast.Grouped):
            return self._sizeof_operand_type(arg.expr)
        if isinstance(arg, rast.Ident):
            # A value in scope wins over a type of the same name.
            if self._sizeof_is_value(arg.name):
                return self.ritz_types.get(arg.name)
            return rast.NamedType(arg.span, arg.name, [])
        # `sizeof(*u8)` / `sizeof(@Pair)` parse as a deref / borrow of a
        # type name: when the operand is not a value, it's a pointer type.
        if (isinstance(arg, rast.UnaryOp) and arg.op in ('*', '&', '@', '&mut', '@&')
                and self._sizeof_names_type(arg.operand)):
            return rast.PtrType(arg.span, rast.NamedType(arg.span, 'u8', []), mutable=False)
        # A comparison or `and`/`or` is a bool; _infer_ritz_type gives every
        # BinOp its left operand's type (ritz1's sizeof agrees).
        if isinstance(arg, rast.BinOp) and arg.op in (
                '==', '!=', '<', '<=', '>', '>=', 'and', 'or', '&&', '||'):
            return rast.NamedType(arg.span, 'bool', [])
        return self._infer_ritz_type(arg)

    def _sizeof_names_type(self, expr: rast.Expr) -> bool:
        """True if `expr` spells a type rather than a value (`u8`, `*Pair`)."""
        if isinstance(expr, rast.TypeExpr):
            return True
        if isinstance(expr, rast.Ident):
            return (not self._sizeof_is_value(expr.name)
                    and self._sizeof_ritz_type(rast.NamedType(expr.span, expr.name, [])) is not None)
        if isinstance(expr, rast.UnaryOp) and expr.op in ('*', '&', '@', '&mut', '@&'):
            return self._sizeof_names_type(expr.operand)
        return False

    def _sizeof_ritz_type(self, ty: rast.Type) -> Optional[int]:
        """Size of `ty`, or None if it names a type that doesn't exist."""
        ty = resolve_alias_in(ty, self.type_aliases)
        if isinstance(ty, rast.NamedType):
            known = (ty.name in self._SIZEOF_PRIMITIVES
                     or ty.args
                     or self._struct_layout_on_demand(ty.name) is not None
                     or self._enum_size_and_align(ty.name) is not None)
            if not known:
                return None
        elif isinstance(ty, rast.ArrayType):
            if self._sizeof_ritz_type(ty.inner) is None:
                return None
        elif isinstance(ty, rast.TupleType):
            if any(self._sizeof_ritz_type(e) is None for e in ty.elements):
                return None
        return self._ritz_type_size_and_align(ty)[0]

    def _ritz_type_to_llvm(self, ty: rast.Type) -> ir.Type:
        """Convert a Ritz type to an LLVM type."""
        if isinstance(ty, rast.NamedType):
            # If this is a generic instantiation (e.g., Span<u8>, Vec<u8>,
            # Option<i32>, Result<Vec<u8>, StrView>), resolve to the already
            # registered specialization rather than falling through to the
            # opaque `i8` placeholder, which would break downstream field
            # access.
            if ty.args:
                specialized_name = self._get_specialized_type_name(ty)
                if specialized_name in self.enum_types:
                    return self.enum_types[specialized_name][0]
                if specialized_name in self.struct_types:
                    return self.struct_types[specialized_name]
                # Synthesize built-in generic structs (Span<T>) on demand so
                # that parameters typed `Span<u8>` resolve to a real struct
                # even when monomorphization hasn't materialized them.
                synthesized_struct = self._ensure_builtin_generic_struct_specialization(ty)
                if synthesized_struct and synthesized_struct in self.struct_types:
                    return self.struct_types[synthesized_struct]
                # Synthesize built-in generic enums (Result<T,E>, Option<T>)
                # on demand when monomorphization missed them.
                synthesized = self._ensure_builtin_generic_specialization(ty)
                if synthesized and synthesized in self.enum_types:
                    return self.enum_types[synthesized][0]
            mapping = {
                'i8': self.i8,
                'i16': self.i16,
                'i32': self.i32,
                'i64': self.i64,
                'u8': self.i8,
                'u16': self.i16,
                'u32': self.i32,
                'u64': self.i64,
                'bool': self.i1,
                'f32': self.f32,
                'f64': self.f64,
            }
            if ty.name in mapping:
                return mapping[ty.name]
            # SIMD vector type aliases (SSE2 128-bit vectors)
            simd_types = {
                'v2i64': ir.VectorType(self.i64, 2),  # <2 x i64>
                'v4i32': ir.VectorType(self.i32, 4),  # <4 x i32>
                'v8i16': ir.VectorType(self.i16, 8),  # <8 x i16>
                'v16i8': ir.VectorType(self.i8, 16),  # <16 x i8>
                # AVX2 256-bit vectors
                'v4i64': ir.VectorType(self.i64, 4),  # <4 x i64>
                'v8i32': ir.VectorType(self.i32, 8),  # <8 x i32>
                'v16i16': ir.VectorType(self.i16, 16), # <16 x i16>
                'v32i8': ir.VectorType(self.i8, 32),  # <32 x i8>
            }
            if ty.name in simd_types:
                # Mark current function as using SIMD types
                # Functions using SIMD need alignstack(16) for proper stack alignment
                if self.current_fn_def:
                    self.simd_functions.add(self.current_fn_def.name)
                return simd_types[ty.name]
            # Check for enum types
            if ty.name in self.enum_types:
                return self.enum_types[ty.name][0]
            # Check for struct types
            if ty.name in self.struct_types:
                return self.struct_types[ty.name]
            # Legacy mangling fallback: monomorphizer sometimes uses '_' as a
            # separator for the first generic arg (e.g. Vec_u8) while the
            # struct registry uses '$' (Vec$u8). Try the dollar-form variant.
            if '_' in ty.name and '$' not in ty.name:
                legacy_name = ty.name.replace('_', '$', 1)
                if legacy_name in self.enum_types:
                    return self.enum_types[legacy_name][0]
                if legacy_name in self.struct_types:
                    return self.struct_types[legacy_name]
            # StrView is a built-in `{ ptr, len }` view. A module that only
            # meets it through an imported signature (e.g. `Result<u8,
            # StrView>` from a selective import) has no struct registered for
            # it; falling through to the i8 placeholder would silently size an
            # enum payload at 1 byte instead of 16 and corrupt the ABI.
            if ty.name == 'StrView':
                return self._ensure_strview_type()
            # An alias is its target: `type Handler = fn(..)` lowers
            # to the fn pointer, not to the i8 placeholder (AGAST #1879 -- a
            # `let f: Handler` slot was one byte wide).
            if ty.name in self.type_aliases and not ty.args:
                target = resolve_alias_in(ty, self.type_aliases)
                if target is not ty:
                    return self._ritz_type_to_llvm(target)
            # Treat unknown types as opaque struct types (i8 placeholder)
            # This allows forward references and unknown struct types
            return self.i8
        elif isinstance(ty, rast.PtrType):
            inner = self._ritz_type_to_llvm(ty.inner)
            return ir.PointerType(inner)
        elif isinstance(ty, rast.RefType):
            inner = self._ritz_type_to_llvm(ty.inner)
            return ir.PointerType(inner)
        elif isinstance(ty, rast.ArrayType):
            inner = self._ritz_type_to_llvm(ty.inner)
            return ir.ArrayType(inner, ty.size)
        elif isinstance(ty, rast.FnType):
            # Function pointer type: fn(T1, T2, ...) -> R
            # Compiles to LLVM function pointer
            param_types = [self._ritz_type_to_llvm(p) for p in ty.params]
            # AGAST #1739: a large by-value struct param is physically a
            # `%T*` (byval), exactly as in _new_function, so that a named fn
            # converts to this type without a by-value bitcast.  The byval
            # attribute itself goes on each indirect call (_fn_type_byval).
            param_types = [ir.PointerType(t) if self._sret_struct_type(t) is not None else t
                           for t in param_types]
            # AGAST #3286: `-> void` is no return, not the `i8` a bare
            # `void` names elsewhere, so `fn(T) -> void` is `fn(T)`.
            ret_type = (self._ritz_type_to_llvm(ty.ret) if self._ret_is_a_value(ty.ret)
                        else self.void)
            # AGAST #1745: a large struct return is an sret pointer, again as
            # in _new_function: `fn(i32) -> Big` is `void (%Big*, i32)*`.
            # The sret attribute and result slot come from each indirect call
            # (_fn_type_sret).
            sret_ty = self._sret_struct_type(ret_type)
            if sret_ty is not None:
                param_types = [ir.PointerType(sret_ty), *param_types]
                ret_type = self.void
            fn_type = ir.FunctionType(ret_type, param_types)
            return ir.PointerType(fn_type)
        elif isinstance(ty, rast.VectorType):
            # SIMD vector type: vec<N, T> -> <N x T>
            # Maps to LLVM vector types for SSE2/AVX operations
            inner = self._ritz_type_to_llvm(ty.inner)
            return ir.VectorType(inner, ty.count)
        elif isinstance(ty, rast.TupleType):
            # Tuple type: (T1, T2, ...) -> { T1, T2, ... }
            # Maps to LLVM literal struct type
            if not ty.elements:
                # Empty tuple (unit type): empty struct
                return ir.LiteralStructType([])
            element_types = [self._ritz_type_to_llvm(elem) for elem in ty.elements]
            return ir.LiteralStructType(element_types)
        else:
            raise InternalError(f"Unknown type: {ty}")

    def _ensure_strview_type(self) -> ir.Type:
        """Materialize the built-in `StrView` struct: `{ *u8, i64 }`."""
        if 'StrView' in self.struct_types:
            return self.struct_types['StrView']
        strview_ty = self.module.context.get_identified_type('StrView')
        strview_ty.set_body(self.i8_ptr, self.i64)
        self.struct_types['StrView'] = strview_ty
        self.struct_fields['StrView'] = [
            ('ptr', rast.PtrType(None, rast.NamedType(None, 'u8', []), mutable=False)),
            ('len', rast.NamedType(None, 'i64', [])),
        ]
        return strview_ty

    def _is_builtin_strview(self, expr: rast.Expr) -> bool:
        """Whether `expr` is a StrView by its Ritz type (AGAST #3326)."""
        ty = self._infer_ritz_type(expr)
        return isinstance(ty, rast.NamedType) and ty.name == 'StrView' and not ty.args

    def _ensure_builtin_generic_struct_specialization(self, ty: rast.NamedType) -> Optional[str]:
        """Synthesize lightweight generic structs used by built-ins (Span<T>).

        When a function parameter is typed `Span<T>` and no explicit
        monomorphization produced the struct, we materialize it here so that
        field access and indexing have a concrete LLVM struct to work with.
        """
        if not ty.args:
            return None
        specialized_name = self._get_specialized_type_name(ty)
        if specialized_name in self.struct_types:
            return specialized_name
        if ty.name != 'Span' or len(ty.args) != 1:
            return None
        note_instance_display(specialized_name, ty.name, ty.args)  # AGAST #4266

        elem_ty = self._ritz_type_to_llvm(ty.args[0])
        span_ty = self.module.context.get_identified_type(specialized_name)
        span_ty.set_body(ir.PointerType(elem_ty), self.i64)
        self.struct_types[specialized_name] = span_ty
        self.struct_fields[specialized_name] = [
            ('ptr', rast.PtrType(ty.span, ty.args[0], mutable=False)),
            ('len', rast.NamedType(ty.span, 'i64', [])),
        ]
        return specialized_name

    def _ensure_builtin_generic_specialization(self, ty: rast.NamedType) -> Optional[str]:
        """Synthesize Result/Option specializations on demand when monomorphization missed them."""
        if not ty.args:
            return None

        specialized_name = self._get_specialized_type_name(ty)
        if specialized_name in self.enum_types:
            return specialized_name
        if ty.name == 'Result' and len(ty.args) == 2:
            variants = [
                rast.Variant(ty.span, 'Ok', [ty.args[0]]),
                rast.Variant(ty.span, 'Err', [ty.args[1]]),
            ]
        elif ty.name == 'Option' and len(ty.args) == 1:
            variants = [
                rast.Variant(ty.span, 'Some', [ty.args[0]]),
                rast.Variant(ty.span, 'None', []),
            ]
        else:
            return None
        note_instance_display(specialized_name, ty.name, ty.args)  # AGAST #4266

        enum_type = self.module.context.get_identified_type(specialized_name)
        self.enum_types[specialized_name] = (enum_type, variants)
        for variant in variants:
            self.variant_to_enum[variant.name] = specialized_name

        # Layout MUST come from the shared helper (the documented single
        # source of truth) so synthesis agrees with every consumer:
        # `_get_enum_data_index`, variant construction and match binding all
        # recompute the layout at use time via `_enum_variant_field_layout` /
        # `_ritz_type_size_and_align`. The previous ad-hoc sizing here used
        # `_type_size_bytes(_ritz_type_to_llvm(field))`, which (a) conflated
        # alignment with size and (b) lowered a not-yet-registered payload
        # struct (e.g. String) to the 1-byte generic placeholder — producing
        # a `{i8, [1 x i8]}` body that use-time layout (align 8, data at
        # index 2) then GEPed past the end of. AGAST #1321.
        self._set_enum_body(enum_type, variants)

        return specialized_name

    def _type_size_bytes(self, ty: ir.Type) -> int:
        """Get the size of an LLVM type in bytes."""
        if ty == self.i1:
            return 1
        elif ty == self.i8:
            return 1
        elif ty == self.i16:
            return 2
        elif ty == self.i32:
            return 4
        elif ty == self.i64:
            return 8
        elif ty == self.f32:
            return 4
        elif ty == self.f64:
            return 8
        elif isinstance(ty, ir.PointerType):
            return 8  # 64-bit pointers
        elif isinstance(ty, ir.ArrayType):
            return ty.count * self._type_size_bytes(ty.element)
        elif isinstance(ty, ir.BaseStructType):
            # Sum of field sizes (simplified - doesn't account for padding)
            # Handle opaque structs (not yet defined) - use pointer size as fallback
            if ty.elements is None:
                return 8  # Default to pointer size for opaque structs
            total = 0
            for field_ty in ty.elements:
                total += self._type_size_bytes(field_ty)
            return total
        elif isinstance(ty, ir.LiteralStructType):
            total = 0
            for field_ty in ty.elements:
                total += self._type_size_bytes(field_ty)
            return total
        elif isinstance(ty, ir.VectorType):
            # SIMD vector: count * element_size
            return ty.count * self._type_size_bytes(ty.element)
        else:
            return 8  # Default to 8 for unknown types

    def _type_size(self, ty: ir.Type) -> int:
        """Get the size of a type in bits for comparison."""
        if ty == self.i1:
            return 1
        elif ty == self.i8:
            return 8
        elif ty == self.i16:
            return 16
        elif ty == self.i32:
            return 32
        elif ty == self.i64:
            return 64
        elif ty == self.f32:
            return 32
        elif ty == self.f64:
            return 64
        elif isinstance(ty, ir.PointerType):
            return 64  # Pointers are 64 bits
        else:
            return 64  # Default to 64 for unknown types


    def _enum_payload_shape(self, variants) -> Tuple[int, int]:
        """(padding, data_size) of an enum's `{ i8, [P x i8], [N x i8] }` body.

        N is the largest variant payload; P pads the tag so the payload sits
        at the strictest alignment any variant requires. N == 0 means a
        tag-only enum, `{ i8 }`. The single source of the enum body: the
        LLVM type (_set_enum_body) and its size (_enum_size_and_align) both
        come from here, so sizeof cannot drift from the emitted type.
        """
        max_size = 0
        max_align = 1
        for variant in variants:
            _, variant_size, variant_align = \
                self._enum_variant_field_layout(variant)
            max_align = max(max_align, variant_align)
            max_size = max(max_size, variant_size)
        if max_size == 0:
            return 0, 0
        return (max_align - (1 % max_align)) % max_align, max_size

    def _set_enum_body(self, enum_type, variants, tag_type=None) -> None:
        """Give an enum its `{ i8 tag, [P x i8] pad, [N x i8] data }` body.

        `tag_type` is an `enum E: <int>`'s repr type (AGAST #4574): such an
        enum is fieldless and its body is `{ iN }`, holding the discriminant.
        """
        padding, data_size = self._enum_payload_shape(variants)
        if not any(variant.fields for variant in variants):
            # all unit variants: just a tag
            enum_type.set_body(tag_type if tag_type is not None else self.i8)
        elif data_size == 0:
            # AGAST #2941: a payload of zero bytes (`Option<()>`) still has a
            # field, and `_get_enum_data_index` / construction / match binding
            # all GEP field 1 for it, so keep a zero-length data buffer there.
            # Layout-equal to ritz1's `{ i8, [0 x i8], [0 x i8] }`.
            enum_type.set_body(self.i8, ir.ArrayType(self.i8, 0))
        elif padding > 0:
            enum_type.set_body(self.i8, ir.ArrayType(self.i8, padding),
                               ir.ArrayType(self.i8, data_size))
        else:
            enum_type.set_body(self.i8, ir.ArrayType(self.i8, data_size))

    def _enum_size_and_align(self, name: str) -> Optional[Tuple[int, int]]:
        """ABI (size, alignment) of enum `name`, or None if it is not one.

        AGAST #1923: the body is all i8, so LLVM 1-aligns it and its size is
        exactly 1 + P + N. This used to fall through to the unknown-type
        (8, 8) guess, so `sizeof` of a struct with an enum field disagreed
        with the `{ %Enum, ... }` type it emits (16 vs 40 for a 32-byte
        enum), and an enum nested in another's payload got an 8-byte slot.
        Computed from the variants rather than the LLVM body because struct
        layouts are computed before enum bodies are set.
        """
        entry = self.enum_types.get(name)
        if entry is None:
            return None
        repr_name = self.enum_reprs.get(name)
        if repr_name is not None:
            # AGAST #4574: `enum E: iN` is laid out as its repr type.
            width = int(repr_name[1:]) // 8
            return (width, width)
        padding, data_size = self._enum_payload_shape(entry[1])
        return (1 + padding + data_size, 1)

    def _enum_variant_field_layout(self, variant):
        """Compute payload field offsets for one enum variant.

        Returns (offsets, size, align):
          offsets -- byte offset of each field within the payload buffer,
                     in declaration order
          size    -- total payload size for this variant, rounded up to its
                     own alignment
          align   -- the strictest alignment any of its fields requires

        Fields are placed in declaration order, each rounded up to its own
        alignment. The interior padding is not optional: the emitter bitcasts
        the payload buffer to a typed pointer and loads through it, so LLVM
        assumes natural alignment. Laying `message: String` (align 8) directly
        after `level: i32` at offset 4 produces a misaligned load, which is
        undefined behaviour rather than merely slow.

        This is the single source of truth for payload offsets. Enum layout,
        variant construction and match binding all call it, so they cannot
        drift apart -- a divergence there reads fields from the wrong address
        without any diagnostic.
        """
        offsets = []
        offset = 0
        max_align = 1
        for field_type in variant.fields:
            size, align = self._ritz_type_size_and_align(field_type)
            align = max(align, 1)
            if offset % align != 0:
                offset += align - (offset % align)
            offsets.append(offset)
            offset += size
            max_align = max(max_align, align)

        # Round the variant's total size up to its own alignment so that the
        # enum's data buffer is large enough for a correctly padded payload.
        if offset % max_align != 0:
            offset += max_align - (offset % max_align)

        return offsets, offset, max_align


    def _param_to_llvm_type(self, param: rast.Param) -> 'ir.Type':
        """Convert a Ritz parameter to LLVM type, considering Borrow semantics.

        In RERITZ mode with explicit :& modifier:
            :& T  (MUTABLE) -> *T (mutable borrow, passed by reference)

        In all other cases (legacy, CONST, MOVE):
            Falls back to direct type conversion (pass by value).

        Note: CONST borrow (: T in RERITZ) semantically means read-only access,
        but we don't yet distinguish it from legacy pass-by-value. Full RERITZ
        const borrow semantics will be implemented in a future phase.
        """
        base_type = self._ritz_type_to_llvm(param.type)

        # Only MUTABLE borrow (:&) passes by reference for now
        # This is the explicit RERITZ syntax that requires pass-by-reference
        if hasattr(param, 'borrow') and param.borrow == rast.Borrow.MUTABLE:
            return ir.PointerType(base_type)
        else:
            # CONST, MOVE, or legacy - pass by value
            return base_type


    def _sizeof_type(self, ty: ir.Type) -> int:
        """The alloc size in bytes of an LLVM type, padding included.

        AGAST #3654: this measured an i1 as `1 // 8 == 0` bytes, so a large
        `[false; N]` memset nothing and left the bools uninitialised.
        """
        return _abi_size_align(ty)[0]


    def _struct_lit_layout(self, expr: rast.StructLit):
        """(%T, [(field name, Ritz type)]) for a struct literal's struct."""
        if expr.name == 'StrView':
            # Built-in, so `StrView { ptr, len }` needs no import (AGAST
            # #3326); a declared or imported `struct StrView` is kept.
            self._ensure_strview_type()
        if expr.name == 'Span' and expr.type_args:
            # Built-in, so `Span<u8> { ptr, len }` needs no import (AGAST
            # #3346): with `ritzlib.span` the monomorphizer has already
            # renamed the literal to `Span$u8`; without it, build that struct
            # as a `Span<u8>` parameter would.
            ty = rast.NamedType(expr.span, 'Span', list(expr.type_args))
            name = self._ensure_builtin_generic_struct_specialization(ty)
            return self.struct_types[name], self.struct_fields[name]
        if expr.name not in self.struct_types:
            raise self._err(f"Unknown struct: {expr.name}")
        return self.struct_types[expr.name], self.struct_fields[expr.name]

    def _struct_lit_field_indices(self, expr: rast.StructLit, field_defs):
        """[(field index, initialiser)] in source (= evaluation) order.  A
        field the struct lacks is R17 rule 5(a)'s "`S` has no field `f`", as
        ritz1 says it, at the field's value (AGAST #4655)."""
        field_indices = {name: i for i, (name, _) in enumerate(field_defs)}
        out = []
        for field_name, field_expr in expr.fields:
            if field_name not in field_indices:
                shown = (rast.NamedType(expr.span, expr.name, list(expr.type_args))
                         if expr.type_args else expr.name)
                raise SourceError(deref_rules.no_field(self._show_type(shown), field_name),
                                  getattr(field_expr, 'span', None) or expr.span)
            out.append((field_indices[field_name], field_expr))
        return out
