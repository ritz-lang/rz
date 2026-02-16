"""
Ritz LLVM IR Emitter using llvmlite

Generates LLVM IR from the AST using llvmlite's IR builder.
This is more robust than hand-writing IR strings.

Note: We generate IR text that uses inline asm for syscalls (no libc).
This requires external `llc` to compile since llvmlite's bundled LLVM
doesn't include the x86 asm parser.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List, Union, Set
from llvmlite import ir
import ritz_ast as rast
from async_transform_v2 import generate_state_machine, AsyncStateMachine


# ============================================================================
# Struct Layout Registry
# ============================================================================

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


# Linux x86_64 syscall numbers
SYSCALL_READ = 0
SYSCALL_WRITE = 1
SYSCALL_OPEN = 2
SYSCALL_CLOSE = 3
SYSCALL_NANOSLEEP = 35
SYSCALL_EXIT = 60


class LLVMEmitter:
    """
    Emits LLVM IR from a Ritz AST using llvmlite.

    Uses inline asm for syscalls (no libc dependency).
    Output is IR text that must be compiled with external llc.
    """

    def __init__(self, source_file: str = "unknown.ritz", source_dir: str = ".",
                 target: str = 'x86_64-unknown-linux-gnu'):
        # Target triple configuration
        self.target = target
        self.is_freestanding = target.endswith('-none-elf') or '-none-' in target

        # LLVM types - integers
        self.i8 = ir.IntType(8)
        self.i16 = ir.IntType(16)
        self.i32 = ir.IntType(32)
        self.i64 = ir.IntType(64)
        self.void = ir.VoidType()
        self.i1 = ir.IntType(1)
        self.i8_ptr = ir.PointerType(self.i8)
        # LLVM types - floats
        self.f32 = ir.FloatType()
        self.f64 = ir.DoubleType()

        self.module: Optional[ir.Module] = None
        self.builder: Optional[ir.IRBuilder] = None
        self.current_fn: Optional[ir.Function] = None

        # Symbol tables
        self.locals: Dict[str, Tuple[ir.AllocaInstr, ir.Type]] = {}  # name -> (alloca, type)
        self.params: Dict[str, Tuple[ir.Value, ir.Type]] = {}  # name -> (value, type)
        self.functions: Dict[str, Tuple[ir.Function, rast.FnDef]] = {}
        self.constants: Dict[str, Tuple[int, ir.Type]] = {}  # name -> (value, type)
        self.const_arrays: Dict[str, Tuple[ir.GlobalVariable, ir.Type]] = {}  # name -> (gvar, type)
        self.globals: Dict[str, Tuple[ir.GlobalVariable, ir.Type]] = {}  # name -> (gvar, type)
        self.extern_fns: Dict[str, ir.Function] = {}
        self.struct_types: Dict[str, ir.BaseStructType] = {}  # name -> LLVM struct type
        self.struct_fields: Dict[str, List[Tuple[str, rast.Type]]] = {}  # name -> [(field_name, type)]
        self.ritz_types: Dict[str, rast.Type] = {}  # name -> Ritz AST type (for signedness)

        self.string_counter = 0
        self.closure_counter = 0  # Counter for anonymous closure names
        self.closure_expected_type: Optional[rast.FnType] = None  # Expected type for closure inference
        self.simd_expected_type: Optional[rast.Type] = None  # Expected SIMD type for loadu inference
        # Closure environment tracking for captures
        self._closure_env_types: Dict[str, ir.Type] = {}  # env struct types
        self._closure_env_arrays: Dict[str, ir.GlobalVariable] = {}  # env slot arrays
        self._closure_env_counters: Dict[str, ir.GlobalVariable] = {}  # slot counters
        self._closure_thunk_arrays: Dict[str, ir.GlobalVariable] = {}  # thunk fn ptr arrays
        self.has_returned = False
        self.main_fn_def: Optional[rast.FnDef] = None
        self.in_test_fn = False  # True when emitting a @test function
        self.current_fn_def: Optional[rast.FnDef] = None  # Current function being emitted
        self.in_unsafe = False  # True when inside an unsafe block

        # Loop context for break/continue (stack of (continue_block, break_block))
        self.loop_stack: List[Tuple[ir.Block, ir.Block]] = []

        # Scope tracking for automatic Drop (RAII)
        # Each scope is a list of (var_name, alloca, ritz_type) for variables that need Drop
        self.drop_scope_stack: List[List[Tuple[str, ir.AllocaInstr, rast.Type]]] = []

        # Drop flags for conditional scopes
        # Maps alloca -> flag_alloca (using id() since AllocaInstr is not hashable)
        # The flag is set to 1 when variable is initialized, checked before dropping
        self.drop_flags: Dict[int, ir.AllocaInstr] = {}

        # Type aliases: name -> Ritz type (for resolving union types)
        self.type_aliases: Dict[str, rast.Type] = {}
        # Union types: name -> (LLVM struct type, list of variant types)
        # Union layout: { i8 tag, [max_size x i8] data }
        self.union_types: Dict[str, Tuple[ir.BaseStructType, List[rast.Type]]] = {}

        # Enum types: name -> (LLVM struct type, list of Variant objects)
        # Enum layout: { i8 tag, [max_size x i8] data }
        # Unlike union_types, enums have named variants with optional payloads
        self.enum_types: Dict[str, Tuple[ir.BaseStructType, List[rast.Variant]]] = {}
        # Variant to enum mapping: variant_name -> enum_name
        # Used to resolve variant constructors like Some(x) -> Option_i32
        self.variant_to_enum: Dict[str, str] = {}

        # Traits: name -> list of method signatures (TraitMethodSig)
        self.traits: Dict[str, List[rast.TraitMethodSig]] = {}
        # Impl blocks: (trait_name, type_name) -> list of method FnDefs
        # trait_name is None for inherent impls
        self.impls: Dict[Tuple[Optional[str], str], List[rast.FnDef]] = {}
        # Method lookup: (type_name, method_name) -> mangled_fn_name
        self.method_lookup: Dict[Tuple[str, str], str] = {}

        # Trait objects (dyn Trait) support
        # vtable_types: trait_name -> LLVM struct type for vtable
        # Each vtable is a struct of function pointers for trait methods
        self.vtable_types: Dict[str, ir.BaseStructType] = {}
        # vtable_instances: (trait_name, impl_type) -> global vtable instance
        self.vtable_instances: Dict[Tuple[str, str], ir.GlobalVariable] = {}
        # dyn_types: trait_name -> LLVM struct type for fat pointer {*data, *vtable}
        self.dyn_types: Dict[str, ir.BaseStructType] = {}

        # Debug info state
        self.source_file = source_file
        self.source_dir = source_dir
        self.emit_debug = True  # Emit DWARF debug info (clang handles DWARF5 properly)
        self.di_file = None
        self.di_compile_unit = None
        self.di_subprograms: Dict[str, ir.DIValue] = {}  # fn name -> DISubprogram
        self.current_di_scope = None  # Current DISubprogram for locations
        self.di_types: Dict[str, ir.DIValue] = {}  # type name -> DIBasicType/DICompositeType
        self.di_expression = None  # Empty DIExpression (cached)
        self.dbg_declare_fn = None  # llvm.dbg.declare intrinsic

        # Separate compilation support
        self._current_source_file: Optional[str] = None  # Set in emit_module

        # Struct layout registry (computed field offsets with proper alignment)
        self.struct_registry = StructRegistry()

        # Async function registry: tracks which functions are async
        # Used during await transformation to know when to call foo_poll vs foo
        self.async_functions: Set[str] = set()

        # Context for current async function being emitted (if any)
        self.in_async_fn: bool = False

        # SIMD function registry: tracks functions that use SIMD types/intrinsics
        # These functions need alignstack(16) attribute to ensure proper stack alignment
        # for SIMD load/store operations (movaps requires 16-byte aligned addresses)
        self.simd_functions: Set[str] = set()

    def _ritz_type_size_and_align(self, ty: rast.Type) -> Tuple[int, int]:
        """Get size and alignment of a Ritz type in bytes.

        Used by StructRegistry to compute field layouts.

        Returns:
            (size_bytes, alignment_bytes)
        """
        if isinstance(ty, rast.NamedType):
            # Primitive types
            primitives = {
                'i8': (1, 1), 'u8': (1, 1),
                'i16': (2, 2), 'u16': (2, 2),
                'i32': (4, 4), 'u32': (4, 4),
                'i64': (8, 8), 'u64': (8, 8),
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

            # Struct types - get from registry if computed
            layout = self.struct_registry.get_layout(ty.name)
            if layout:
                return (layout.size, layout.alignment)

            # Fallback for unknown types (treat as 8-byte pointer-sized)
            return (8, 8)

        elif isinstance(ty, rast.PtrType) or isinstance(ty, rast.RefType):
            # Pointers and references are 8 bytes on x86_64
            return (8, 8)

        elif isinstance(ty, rast.ArrayType):
            # Array: element_size * count, alignment = element alignment
            elem_size, elem_align = self._ritz_type_size_and_align(ty.inner)
            # Extract integer size (may be int or IntLit)
            array_size = ty.size.value if isinstance(ty.size, rast.IntLit) else ty.size
            return (elem_size * array_size, elem_align)

        elif isinstance(ty, rast.VectorType):
            # SIMD vector: size = count * element_size, alignment = total size
            # SSE2 vectors (128-bit) should be 16-byte aligned
            # AVX vectors (256-bit) should be 32-byte aligned
            elem_size, _ = self._ritz_type_size_and_align(ty.inner)
            total_size = elem_size * ty.count
            return (total_size, total_size)

        else:
            # Default fallback
            return (8, 8)

    def _ritz_type_to_llvm(self, ty: rast.Type) -> ir.Type:
        """Convert a Ritz type to an LLVM type."""
        if isinstance(ty, rast.NamedType):
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
            # Check for union types (type aliases to UnionType)
            if ty.name in self.union_types:
                return self.union_types[ty.name][0]
            # Check for enum types
            if ty.name in self.enum_types:
                return self.enum_types[ty.name][0]
            # Check for struct types
            if ty.name in self.struct_types:
                return self.struct_types[ty.name]
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
            # Extract integer size (may be int or IntLit)
            array_size = ty.size.value if isinstance(ty.size, rast.IntLit) else ty.size
            return ir.ArrayType(inner, array_size)
        elif isinstance(ty, rast.UnionType):
            # Anonymous union type - compute layout
            # Union layout: { i8 tag, [max_size x i8] data }
            max_size = 0
            for variant in ty.variants:
                llvm_ty = self._ritz_type_to_llvm(variant)
                size = self._type_size_bytes(llvm_ty)
                if size > max_size:
                    max_size = size
            # Create struct with tag (i8) and data buffer
            data_array = ir.ArrayType(self.i8, max_size)
            return ir.LiteralStructType([self.i8, data_array])
        elif isinstance(ty, rast.FnType):
            # Function pointer type: fn(T1, T2, ...) -> R
            # Compiles to LLVM function pointer
            param_types = [self._ritz_type_to_llvm(p) for p in ty.params]
            ret_type = self._ritz_type_to_llvm(ty.ret) if ty.ret else self.void
            fn_type = ir.FunctionType(ret_type, param_types)
            return ir.PointerType(fn_type)
        elif isinstance(ty, rast.VectorType):
            # SIMD vector type: vec<N, T> -> <N x T>
            # Maps to LLVM vector types for SSE2/AVX operations
            inner = self._ritz_type_to_llvm(ty.inner)
            return ir.VectorType(inner, ty.count)
        elif isinstance(ty, rast.DynType):
            # Trait object: dyn Trait -> { *void data, *vtable }
            # Fat pointer for runtime polymorphism
            if ty.trait_name in self.dyn_types:
                return self.dyn_types[ty.trait_name]
            # If vtable not yet created, create a placeholder fat pointer
            return ir.LiteralStructType([self.i8_ptr, self.i8_ptr])
        else:
            raise ValueError(f"Unknown type: {ty}")

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

    def _infer_ritz_type(self, expr: rast.Expr, llvm_val: ir.Value = None) -> Optional[rast.Type]:
        """Infer a Ritz type from an expression, for signedness tracking.

        This mirrors the type checker's inference but is used during emission
        when no explicit type annotation is provided.
        """
        if isinstance(expr, rast.IntLit):
            # Integer literals default to i64 (signed)
            return rast.NamedType(expr.span, 'i64', [])
        elif isinstance(expr, rast.FloatLit):
            return rast.NamedType(expr.span, 'f64', [])
        elif isinstance(expr, rast.BoolLit):
            return rast.NamedType(expr.span, 'bool', [])
        elif isinstance(expr, rast.CharLit):
            return rast.NamedType(expr.span, 'u8', [])
        elif isinstance(expr, rast.StringLit):
            # "hello" -> StrView (zero-copy view)
            return rast.NamedType(expr.span, 'StrView', [])
        elif isinstance(expr, rast.CStringLit):
            return rast.PtrType(expr.span, rast.NamedType(expr.span, 'u8', []), mutable=False)
        elif isinstance(expr, rast.SpanStringLit):
            # s"hello" -> Span<u8>
            return rast.NamedType(expr.span, 'Span', [rast.NamedType(expr.span, 'u8', [])])
        elif isinstance(expr, rast.NullLit):
            return rast.NamedType(expr.span, 'null', [])
        elif isinstance(expr, rast.Ident):
            # Look up existing type
            if expr.name in self.ritz_types:
                return self.ritz_types[expr.name]
            return None
        elif isinstance(expr, rast.BinOp):
            # Binary ops inherit type from left operand
            return self._infer_ritz_type(expr.left)
        elif isinstance(expr, rast.UnaryOp):
            inner_type = self._infer_ritz_type(expr.operand)
            if expr.op == '&' and inner_type:
                return rast.PtrType(expr.span, inner_type, mutable=False)
            elif expr.op == '*' and inner_type:
                if isinstance(inner_type, rast.PtrType):
                    return inner_type.inner
            return inner_type
        elif isinstance(expr, rast.Call):
            # Look up function return type from self.functions
            if isinstance(expr.func, rast.Ident):
                fn_name = expr.func.name
                if fn_name in self.functions:
                    _, fn_def = self.functions[fn_name]
                    return fn_def.ret_type
                # Check for generic instantiation
                for name, (_, fn_def) in self.functions.items():
                    if name.startswith(fn_name + '$'):
                        return fn_def.ret_type
            return None
        elif isinstance(expr, rast.MethodCall):
            # Method call return type - look up in method signatures
            return None  # Complex - would need full type resolution
        elif isinstance(expr, rast.Field):
            # Field access - resolve struct type and return field type
            base_type = self._infer_ritz_type(expr.expr)
            if base_type:
                # Handle pointer to struct: *S.field -> type of S.field
                if isinstance(base_type, rast.PtrType):
                    base_type = base_type.inner
                elif isinstance(base_type, rast.RefType):
                    base_type = base_type.inner
                # Look up field type in struct definition
                if isinstance(base_type, rast.NamedType):
                    struct_name = base_type.name
                    if struct_name in self.struct_fields:
                        for fname, ftype in self.struct_fields[struct_name]:
                            if fname == expr.field:
                                return ftype
            return None
        elif isinstance(expr, rast.Index):
            base_type = self._infer_ritz_type(expr.expr)
            if base_type:
                if isinstance(base_type, rast.ArrayType):
                    return base_type.inner
                elif isinstance(base_type, rast.PtrType):
                    return base_type.inner
            return None
        elif isinstance(expr, rast.Cast):
            return expr.target
        elif isinstance(expr, rast.StructLit):
            return rast.NamedType(expr.span, expr.name, [])
        elif isinstance(expr, rast.ArrayLit):
            if expr.elements:
                elem_type = self._infer_ritz_type(expr.elements[0])
                if elem_type:
                    return rast.ArrayType(expr.span, len(expr.elements), elem_type)
            return None
        elif isinstance(expr, rast.If):
            if expr.then_block and expr.then_block.expr:
                return self._infer_ritz_type(expr.then_block.expr)
            return None
        elif isinstance(expr, rast.Block):
            if expr.expr:
                return self._infer_ritz_type(expr.expr)
            return rast.NamedType(expr.span, 'void', [])
        return None

    def _get_string_constant(self, value: str) -> ir.GlobalVariable:
        """Create a global string constant."""
        name = f".str.{self.string_counter}"
        self.string_counter += 1

        # Create null-terminated byte array
        byte_data = bytearray(value.encode('utf-8')) + bytearray([0])
        arr_type = ir.ArrayType(self.i8, len(byte_data))
        const = ir.Constant(arr_type, byte_data)

        gvar = ir.GlobalVariable(self.module, arr_type, name=name)
        gvar.global_constant = True
        gvar.linkage = "private"
        gvar.initializer = const

        return gvar

    def _emit_string_from_literal(self, expr: rast.StringLit) -> ir.Value:
        """Emit a String from a string literal via string_from_bytes().

        Converts "hello" -> string_from_bytes(ptr, 5), using compile-time known length.
        This avoids the runtime strlen() that string_from() would do.
        """
        if "string_from_bytes" not in self.functions:
            raise ValueError("String literal to String conversion requires string_from_bytes() to be defined. "
                             "Import ritzlib.string to use String type.")

        fn, _ = self.functions["string_from_bytes"]

        # Get the C string pointer
        gvar = self._get_string_constant(expr.value)
        zero = ir.Constant(self.i64, 0)
        cstr_ptr = self.builder.gep(gvar, [zero, zero])

        # Use compile-time known length instead of runtime strlen
        length = ir.Constant(self.i64, len(expr.value))

        # Call string_from_bytes(cstr_ptr, length)
        return self.builder.call(fn, [cstr_ptr, length])

    def _emit_span_string_literal(self, expr: rast.SpanStringLit) -> ir.Value:
        """Emit a Span<u8> from a span string literal.

        Converts s"hello" -> Span<u8> { ptr: @.str.0, len: 5 }
        Zero allocation - static data with compile-time known length.
        """
        # Get the string constant pointer
        gvar = self._get_string_constant(expr.value)
        zero = ir.Constant(self.i64, 0)
        ptr = self.builder.gep(gvar, [zero, zero])

        # Compile-time length
        length = ir.Constant(self.i64, len(expr.value))

        # Get the Span<u8> struct type (monomorphized as Span$u8)
        # Span<u8> is: { ptr: *u8, len: i64 }
        span_type_name = "Span$u8"
        if span_type_name in self.struct_types:
            span_type = self.struct_types[span_type_name]
        else:
            # Create inline literal struct type if Span$u8 not defined
            # This allows span strings to work without importing ritzlib.span
            span_type = ir.LiteralStructType([self.i8.as_pointer(), self.i64])

        # Build the Span struct value
        span = self.builder.insert_value(ir.Constant(span_type, ir.Undefined), ptr, 0)
        span = self.builder.insert_value(span, length, 1)

        return span

    def _emit_strview_string_literal(self, expr: rast.StringLit) -> ir.Value:
        """Emit a StrView from a string literal (RERITZ mode).

        Converts "hello" -> StrView { ptr: @.str.0, len: 5 }
        Zero allocation - static data with compile-time known length.

        In RERITZ mode, "hello" returns a StrView (ptr + len) instead of *u8.
        This provides zero-copy string handling by default.
        """
        # Get the string constant pointer
        gvar = self._get_string_constant(expr.value)
        zero = ir.Constant(self.i64, 0)
        ptr = self.builder.gep(gvar, [zero, zero])

        # Compile-time length
        length = ir.Constant(self.i64, len(expr.value))

        # Get the StrView struct type
        # StrView is: { ptr: *u8, len: i64 }
        if "StrView" in self.struct_types:
            strview_type = self.struct_types["StrView"]
        else:
            # Create inline literal struct type if StrView not defined
            # This allows string literals to work without importing ritzlib.strview
            strview_type = ir.LiteralStructType([self.i8.as_pointer(), self.i64])

        # Build the StrView struct value
        sv = self.builder.insert_value(ir.Constant(strview_type, ir.Undefined), ptr, 0)
        sv = self.builder.insert_value(sv, length, 1)

        return sv

    def _coerce_string_to_u8_ptr(self, string_val: ir.Value, arg_expr: rast.Expr) -> ir.Value:
        """Coerce a String value to *u8 by calling string_as_ptr().

        Issue #89 Phase 2: Implicit String -> *u8 coercion in function calls.

        Args:
            string_val: The LLVM value of the String (struct type)
            arg_expr: The original AST expression (used to find lvalue address)

        Returns:
            The *u8 pointer from string_as_ptr()
        """
        if "string_as_ptr" not in self.functions:
            raise ValueError("String to *u8 coercion requires string_as_ptr() to be defined. "
                             "Import ritzlib.string to use String type.")

        fn, _ = self.functions["string_as_ptr"]

        # string_as_ptr expects &mut String (pointer to String)
        # If arg_expr is an lvalue (variable), we can get its address
        # Otherwise, we need to store the temporary String on the stack

        string_ptr = None

        if isinstance(arg_expr, rast.Ident):
            name = arg_expr.name
            if name in self.locals:
                # var binding - the alloca IS the pointer
                string_ptr, _ = self.locals[name]
            elif name in self.globals:
                # global var - the global IS the pointer
                string_ptr, _ = self.globals[name]

        if string_ptr is None:
            # Temporary - allocate stack space and store the String there
            # Get String type from struct registry
            if "String" not in self.struct_types:
                raise ValueError("String struct not defined. Import ritzlib.string.")
            string_type = self.struct_types["String"]
            string_ptr = self.builder.alloca(string_type, name="string_temp")
            self.builder.store(string_val, string_ptr)

        # Call string_as_ptr(&mut string)
        return self.builder.call(fn, [string_ptr])

    def _emit_global_var(self, var_def: rast.VarDef) -> None:
        """Emit a module-level mutable variable.

        With separate compilation:
        - Variables from the current source file get definitions (with initializers)
        - Variables from other files get external declarations only (no initializer)

        Linkage rules:
        - pub var: external linkage (visible to linker, can be shared across modules)
        - var (private): internal linkage (hidden from linker, module-local)
        - imported var: external linkage (declaration only, defined elsewhere)
        """
        # Determine the type
        if var_def.type is not None:
            ty = self._ritz_type_to_llvm(var_def.type)
            ritz_ty = var_def.type
        elif var_def.value is not None:
            # Infer type from initializer
            ritz_ty = self._infer_ritz_type(var_def.value)
            if ritz_ty is None:
                raise ValueError(f"Cannot infer type for module-level var '{var_def.name}'")
            ty = self._ritz_type_to_llvm(ritz_ty)
        else:
            raise ValueError(f"Module-level var '{var_def.name}' needs type or initializer")

        # Create the global variable
        gvar = ir.GlobalVariable(self.module, ty, name=var_def.name)

        # Check if this variable is from the current source file or imported
        is_from_current_file = self._should_emit_body(var_def)

        if is_from_current_file:
            # This is a definition - set linkage based on visibility
            if var_def.is_pub:
                # pub var: default (external) linkage so other modules can access it
                # Note: Don't explicitly set "external" because LLVM treats that
                # as a declaration without initializer. Just leave linkage unset
                # for a global definition with external visibility.
                pass  # Default linkage is external for global definitions
            else:
                # private var: internal linkage, hidden from linker
                gvar.linkage = "internal"

            # Set initializer for definitions
            if var_def.value is not None:
                if isinstance(var_def.value, rast.IntLit):
                    if isinstance(ty, ir.PointerType):
                        # Pointer initialized with integer literal (e.g., 0) -> null pointer
                        gvar.initializer = ir.Constant(ty, None)
                    else:
                        gvar.initializer = ir.Constant(ty, var_def.value.value)
                elif isinstance(var_def.value, rast.UnaryOp) and var_def.value.op == '-':
                    # Handle negative integer literals like -1
                    if isinstance(var_def.value.operand, rast.IntLit):
                        gvar.initializer = ir.Constant(ty, -var_def.value.operand.value)
                    else:
                        raise ValueError(f"Complex unary op initializer not supported: {var_def.value}")
                elif isinstance(var_def.value, rast.Cast):
                    # Handle `0 as *i8` style initialization
                    if isinstance(var_def.value.expr, rast.IntLit):
                        if isinstance(ty, ir.PointerType):
                            # Cast to pointer type with zero -> null pointer
                            gvar.initializer = ir.Constant(ty, None)
                        else:
                            gvar.initializer = ir.Constant(ty, var_def.value.expr.value)
                    else:
                        raise ValueError(f"Complex cast initializer not supported: {var_def.value}")
                elif isinstance(var_def.value, rast.NullLit):
                    # Handle `null` initialization for pointer types
                    if isinstance(ty, ir.PointerType):
                        gvar.initializer = ir.Constant(ty, None)
                    else:
                        raise ValueError(f"null can only initialize pointer types, not {ty}")
                else:
                    raise ValueError(f"Unsupported global var initializer: {var_def.value}")
            else:
                # Zero initialize
                gvar.initializer = ir.Constant(ty, None)  # zeroinitializer
        else:
            # This is an imported variable - external declaration only
            # No initializer, just a reference to a symbol defined elsewhere
            gvar.linkage = "external"
            # No initializer for external declarations

        # Store in lookup table
        self.globals[var_def.name] = (gvar, ty)
        self.ritz_types[var_def.name] = ritz_ty

    def _emit_const_array(self, name: str, ritz_type: rast.Type, value: rast.Expr) -> None:
        """Emit a module-level constant array as a global.

        const SBOX: [256]u8 = [0x63, 0x7c, ...]

        Creates an immutable global array that can be indexed.
        """
        # Get the LLVM array type
        llvm_type = self._ritz_type_to_llvm(ritz_type)
        if not isinstance(llvm_type, ir.ArrayType):
            raise ValueError(f"Const array '{name}' must have array type, got {llvm_type}")

        elem_type = llvm_type.element

        # Extract element values
        if isinstance(value, rast.ArrayLit):
            elements = []
            for elem in value.elements:
                elem_val = self._extract_int_from_expr(elem)
                elements.append(ir.Constant(elem_type, elem_val))
        elif isinstance(value, rast.ArrayFill):
            fill_val = self._extract_int_from_expr(value.value)
            elements = [ir.Constant(elem_type, fill_val)] * value.count
        else:
            raise ValueError(f"Const array '{name}' must be array literal or fill")

        # Create the constant array value
        const_array = ir.Constant(llvm_type, elements)

        # Create global variable
        gvar = ir.GlobalVariable(self.module, llvm_type, name=name)
        gvar.global_constant = True
        gvar.initializer = const_array
        gvar.linkage = "internal"

        # Store in lookup - array constants are stored in globals, not constants
        # because they need to be addressed for indexing
        self.const_arrays[name] = (gvar, llvm_type)
        self.ritz_types[name] = ritz_type

    def _extract_int_from_expr(self, expr: rast.Expr) -> int:
        """Extract an integer value from a constant expression."""
        if isinstance(expr, rast.IntLit):
            return expr.value
        elif isinstance(expr, rast.UnaryOp) and expr.op == '-':
            if isinstance(expr.operand, rast.IntLit):
                return -expr.operand.value
        raise ValueError(f"Expected integer literal, got {expr}")

    # Module counter for unique naming
    _module_counter = 0

    def _setup_debug_info(self) -> None:
        """Set up DWARF debug info metadata for the module."""
        if not self.emit_debug:
            return

        # Create DIFile - the source file reference
        self.di_file = self.module.add_debug_info('DIFile', {
            'filename': self.source_file,
            'directory': self.source_dir,
        })

        # Create DICompileUnit - describes the compilation
        self.di_compile_unit = self.module.add_debug_info('DICompileUnit', {
            'language': ir.DIToken('DW_LANG_C'),  # No Ritz language ID, use C
            'file': self.di_file,
            'producer': 'ritz0 1.0',
            'runtimeVersion': 0,
            'isOptimized': False,
            'emissionKind': ir.DIToken('FullDebug'),
        }, is_distinct=True)

        # Create the empty types array for subroutine type
        self.di_types_empty = self.module.add_debug_info('DIBasicType', {})

        # Create subroutine type (function signature)
        self.di_subroutine_type = self.module.add_debug_info('DISubroutineType', {
            'types': self.module.add_metadata([]),  # Empty for now
        })

        # Add to llvm.dbg.cu named metadata
        self.module.add_named_metadata('llvm.dbg.cu')
        self.module.get_named_metadata('llvm.dbg.cu').add(self.di_compile_unit)

        # Add module flags for DWARF version
        self.module.add_named_metadata('llvm.module.flags')
        # DWARF version 4
        dwarf_version = self.module.add_metadata([
            ir.Constant(self.i32, 2),  # Behavior: Warning
            ir.MetaDataString(self.module, 'Dwarf Version'),
            ir.Constant(self.i32, 4),
        ])
        self.module.get_named_metadata('llvm.module.flags').add(dwarf_version)

        # Debug Info Version 3
        debug_info_version = self.module.add_metadata([
            ir.Constant(self.i32, 2),  # Behavior: Warning
            ir.MetaDataString(self.module, 'Debug Info Version'),
            ir.Constant(self.i32, 3),
        ])
        self.module.get_named_metadata('llvm.module.flags').add(debug_info_version)

        # Create DIExpression (empty - most common case)
        self.di_expression = self.module.add_debug_info('DIExpression', {})

        # Declare llvm.dbg.declare intrinsic for variable debug info
        metadata_type = ir.MetaDataType()
        dbg_declare_type = ir.FunctionType(ir.VoidType(), [metadata_type, metadata_type, metadata_type])
        self.dbg_declare_fn = ir.Function(self.module, dbg_declare_type, name='llvm.dbg.declare')

        # Pre-create DIBasicType for common primitive types
        self._setup_di_basic_types()

    def _setup_di_basic_types(self) -> None:
        """Create DIBasicType entries for common Ritz types."""
        if not self.emit_debug:
            return

        # Integer types - signed
        for name, size in [('i8', 8), ('i16', 16), ('i32', 32), ('i64', 64)]:
            self.di_types[name] = self.module.add_debug_info('DIBasicType', {
                'name': name,
                'size': size,
                'encoding': ir.DIToken('DW_ATE_signed'),
            })

        # Integer types - unsigned
        for name, size in [('u8', 8), ('u16', 16), ('u32', 32), ('u64', 64)]:
            self.di_types[name] = self.module.add_debug_info('DIBasicType', {
                'name': name,
                'size': size,
                'encoding': ir.DIToken('DW_ATE_unsigned'),
            })

        # Boolean
        self.di_types['bool'] = self.module.add_debug_info('DIBasicType', {
            'name': 'bool',
            'size': 8,  # Ritz bools are 1 byte
            'encoding': ir.DIToken('DW_ATE_boolean'),
        })

    def _get_di_type(self, ritz_type: rast.Type) -> Optional[ir.DIValue]:
        """Get or create DIType for a Ritz type.

        Returns None if debug info is disabled or type cannot be represented.
        """
        if not self.emit_debug or not self.di_file:
            return None

        if isinstance(ritz_type, rast.NamedType):
            type_name = ritz_type.name
            if type_name in self.di_types:
                return self.di_types[type_name]

            # Check if it's a struct type
            layout = self.struct_registry.get_layout(type_name)
            if layout:
                # Create DICompositeType for struct
                # For now, use a simple placeholder - full struct debug info is more complex
                di_type = self.module.add_debug_info('DICompositeType', {
                    'tag': ir.DIToken('DW_TAG_structure_type'),
                    'name': type_name,
                    'file': self.di_file,
                    'size': layout.size * 8,  # Size in bits
                    'align': layout.alignment * 8,  # Align in bits
                })
                self.di_types[type_name] = di_type
                return di_type

            # Unknown named type - return None
            return None

        elif isinstance(ritz_type, rast.PtrType):
            # Pointer type - create DIDerivedType
            inner_di = self._get_di_type(ritz_type.inner)
            ptr_key = f'*{self._type_to_str(ritz_type.inner)}'
            if ptr_key in self.di_types:
                return self.di_types[ptr_key]

            di_type = self.module.add_debug_info('DIDerivedType', {
                'tag': ir.DIToken('DW_TAG_pointer_type'),
                'size': 64,  # 8 bytes on x86_64
                'baseType': inner_di if inner_di else self.di_types.get('u8'),
            })
            self.di_types[ptr_key] = di_type
            return di_type

        elif isinstance(ritz_type, rast.RefType):
            # Reference type - similar to pointer for debug info
            inner_di = self._get_di_type(ritz_type.inner)
            ref_key = f'&{self._type_to_str(ritz_type.inner)}'
            if ref_key in self.di_types:
                return self.di_types[ref_key]

            di_type = self.module.add_debug_info('DIDerivedType', {
                'tag': ir.DIToken('DW_TAG_reference_type'),
                'size': 64,  # 8 bytes on x86_64
                'baseType': inner_di if inner_di else self.di_types.get('u8'),
            })
            self.di_types[ref_key] = di_type
            return di_type

        elif isinstance(ritz_type, rast.ArrayType):
            # Array type
            inner_di = self._get_di_type(ritz_type.inner)
            if not inner_di:
                return None

            # Extract integer size (may be int or IntLit AST node after const eval)
            array_size = ritz_type.size
            if isinstance(array_size, rast.IntLit):
                array_size = array_size.value
            elif not isinstance(array_size, int):
                # If size is still an unevaluated expression, skip debug info
                return None

            arr_key = f'[{array_size}]{self._type_to_str(ritz_type.inner)}'
            if arr_key in self.di_types:
                return self.di_types[arr_key]

            elem_size, _ = self._ritz_type_size_and_align(ritz_type.inner)
            total_size = elem_size * array_size

            # Create subrange for array dimension
            subrange = self.module.add_debug_info('DISubrange', {
                'count': array_size,
            })

            di_type = self.module.add_debug_info('DICompositeType', {
                'tag': ir.DIToken('DW_TAG_array_type'),
                'size': total_size * 8,  # Size in bits
                'baseType': inner_di,
                'elements': self.module.add_metadata([subrange]),
            })
            self.di_types[arr_key] = di_type
            return di_type

        return None

    def _type_to_str(self, ritz_type: rast.Type) -> str:
        """Get string representation of a Ritz type for debug info keys."""
        if isinstance(ritz_type, rast.NamedType):
            return ritz_type.name
        elif isinstance(ritz_type, rast.PtrType):
            return f'*{self._type_to_str(ritz_type.inner)}'
        elif isinstance(ritz_type, rast.RefType):
            return f'&{self._type_to_str(ritz_type.inner)}'
        elif isinstance(ritz_type, rast.ArrayType):
            # Extract integer size (may be int or IntLit)
            size = ritz_type.size
            if isinstance(size, rast.IntLit):
                size = size.value
            return f'[{size}]{self._type_to_str(ritz_type.inner)}'
        return 'unknown'

    def _emit_dbg_declare(self, alloca: ir.AllocaInstr, name: str, ritz_type: rast.Type, line: int) -> None:
        """Emit llvm.dbg.declare for a local variable.

        This associates the alloca with debug info so GDB can display variable values.
        """
        if not self.emit_debug or not self.current_di_scope or not self.dbg_declare_fn:
            return

        di_type = self._get_di_type(ritz_type)
        if not di_type:
            return

        # Create DILocalVariable for this variable
        di_var = self.module.add_debug_info('DILocalVariable', {
            'name': name,
            'scope': self.current_di_scope,
            'file': self.di_file,
            'line': line,
            'type': di_type,
        })

        # Create location for the declare call
        di_loc = self.module.add_debug_info('DILocation', {
            'line': line,
            'column': 1,
            'scope': self.current_di_scope,
        })

        # Save current debug metadata
        old_metadata = self.builder.debug_metadata

        # Set location for the declare call
        self.builder.debug_metadata = di_loc

        # Call llvm.dbg.declare(metadata ptr %alloca, metadata !DILocalVariable, metadata !DIExpression)
        self.builder.call(self.dbg_declare_fn, [alloca, di_var, self.di_expression])

        # Restore previous debug metadata
        self.builder.debug_metadata = old_metadata

    def emit_module(self, module: rast.Module, source_file: Optional[str] = None) -> str:
        """Emit a complete module.

        Args:
            module: The AST module to emit
            source_file: If provided, only emit function bodies for items where
                        item.source_file == source_file. Other functions are
                        declared but not defined, enabling separate compilation.
                        If None, emit all function bodies (legacy behavior).
        """
        self._current_source_file = source_file
        LLVMEmitter._module_counter += 1

        # Transform async functions into state machines (before any emission)
        module = self._transform_async_functions(module)

        # Create a fresh context for each module to avoid struct type conflicts
        ctx = ir.Context()
        self.module = ir.Module(name=f"ritz_module_{LLVMEmitter._module_counter}", context=ctx)
        self.module.triple = self.target

        # For freestanding targets (kernel mode), set module flags:
        # - No stack protector (no __stack_chk_guard available)
        # - No red zone (interrupt handlers need predictable stack)
        if self.is_freestanding:
            # Add module-level metadata for freestanding flags
            # These affect code generation when compiled with llc
            # Note: Function-level attributes are more reliable for these
            pass  # Module flags handled via function attributes below

        # Set up debug info
        self._setup_debug_info()

        # First pass: declare all struct and enum types (opaque - names only)
        # This enables forward references and self-references in struct fields
        for item in module.items:
            if isinstance(item, rast.StructDef):
                self._declare_struct(item)
            elif isinstance(item, rast.EnumDef):
                self._declare_enum(item)

        # Second pass: define struct and enum bodies (now all type names are known)
        for item in module.items:
            if isinstance(item, rast.StructDef):
                self._define_struct(item)
            elif isinstance(item, rast.EnumDef):
                self._define_enum(item)

        # Process type aliases (must come after struct types)
        for item in module.items:
            if isinstance(item, rast.TypeAlias):
                self._process_type_alias(item)

        # Third pass: collect constants, module-level vars, and extern declarations
        for item in module.items:
            if isinstance(item, rast.ConstDef):
                ty = self._ritz_type_to_llvm(item.type)
                if isinstance(item.value, rast.IntLit):
                    self.constants[item.name] = (item.value.value, ty)
                elif isinstance(item.value, rast.FloatLit):
                    self.constants[item.name] = (item.value.value, ty)
                elif isinstance(item.value, rast.UnaryOp) and item.value.op == '-':
                    # Handle negative literals like -1 or -3.14
                    if isinstance(item.value.operand, rast.IntLit):
                        self.constants[item.name] = (-item.value.operand.value, ty)
                    elif isinstance(item.value.operand, rast.FloatLit):
                        self.constants[item.name] = (-item.value.operand.value, ty)
                    else:
                        raise ValueError(f"Const value must be numeric literal: {item.value}")
                elif isinstance(item.value, (rast.ArrayLit, rast.ArrayFill)):
                    # Array constants - emit as global constant
                    self._emit_const_array(item.name, item.type, item.value)
                else:
                    raise ValueError(f"Const value must be numeric literal or array literal: {item.value}")
            elif isinstance(item, rast.VarDef):
                self._emit_global_var(item)
            elif isinstance(item, rast.ExternFn):
                self._declare_extern(item)

        # Fourth pass: process traits and impl blocks
        # Traits just store method signatures for validation
        # Impl blocks create mangled function names for method dispatch
        for item in module.items:
            if isinstance(item, rast.TraitDef):
                self._process_trait(item)
            elif isinstance(item, rast.ImplBlock):
                self._process_impl(item)

        # Fourth-and-a-half pass: create vtable instances for trait impls
        # This must happen after all functions are declared but we create stubs first
        self._create_vtable_instances()

        # Fifth pass: declare all functions (signatures only)
        # This enables forward references - functions can call each other
        # regardless of source order
        for item in module.items:
            if isinstance(item, rast.FnDef):
                self._declare_function(item)
                if item.name == 'main':
                    self.main_fn_def = item

        # Sixth pass: emit all function bodies
        # If source_file is specified, only emit bodies for functions from that file
        for item in module.items:
            if isinstance(item, rast.FnDef):
                if self._should_emit_body(item):
                    self._emit_function_body(item)

        # Seventh pass: emit all impl block method bodies
        self._emit_impl_methods()

        # Emit _start entry point if we have main and runtime is enabled
        if self.main_fn_def and not getattr(self, 'no_runtime', False):
            self._emit_start_function()

        # Emit memset if we used the llvm.memset intrinsic (needed for -nostdlib linking)
        if hasattr(self, '_memset_fn') and not getattr(self, 'no_runtime', False):
            self._emit_memset_function()

        # Generate IR string
        ir_str = str(self.module)

        # Post-process IR to add alignstack(16) attribute to SIMD functions
        # This ensures proper 16-byte stack alignment for SIMD operations
        # (e.g., movaps instruction requires 16-byte aligned memory addresses)
        if self.simd_functions:
            ir_str = self._add_simd_alignstack(ir_str)

        # Add header comment
        lines = ir_str.split('\n')
        lines.insert(0, '; Ritz compiled module')
        return '\n'.join(lines)

    def _add_simd_alignstack(self, ir_str: str) -> str:
        """Add alignstack(16) attribute to functions that use SIMD.

        SIMD operations (SSE2/AVX) often require 16-byte aligned memory.
        When LLVM's register allocator spills SIMD registers to the stack,
        it uses aligned store instructions (movaps) that require the stack
        to be 16-byte aligned.

        The x86-64 ABI guarantees 16-byte stack alignment at function entry,
        but the red zone (below RSP) may not maintain this alignment.
        Adding alignstack(16) forces the function to realign the stack.

        This fixes SIGSEGV crashes when SIMD values are spilled to stack.
        """
        import re

        for fn_name in self.simd_functions:
            # Match 'define <rettype> @"<fn_name>"(<params>) <attrs> !dbg'
            # We need to insert alignstack(16) before !dbg
            # Pattern: define ... @"fn_name"(...) !dbg
            # Note: fn_name might contain special chars, so we escape it
            escaped_name = re.escape(fn_name)
            pattern = rf'(define [^@]+@"{escaped_name}"\([^)]*\))(\s*)(!dbg)'
            replacement = rf'\1 alignstack(16)\2\3'
            ir_str = re.sub(pattern, replacement, ir_str)

        return ir_str

    def _transform_async_functions(self, module: rast.Module) -> rast.Module:
        """Transform async functions into state machine equivalents.

        For each async fn, generates:
        - A Future struct to hold state and locals
        - A constructor function (replaces the original fn)
        - A poll function to advance the state machine

        Also populates self.async_functions registry for await transformation.

        Currently (MVP): The poll function runs synchronously.
        Future: True state machine with suspend/resume.
        """
        new_items = []
        has_async_main = False

        # First pass: collect all async function names
        for item in module.items:
            if isinstance(item, rast.FnDef) and getattr(item, 'is_async', False):
                self.async_functions.add(item.name)
                if item.name == 'main':
                    has_async_main = True

        # Second pass: transform async functions
        for item in module.items:
            if isinstance(item, rast.FnDef) and getattr(item, 'is_async', False):
                # Transform this async function
                try:
                    # Pass async_functions so await can recognize calls to async fns
                    sm = generate_state_machine(item, self.async_functions)

                    # Add the generated items
                    new_items.append(sm.future_struct)     # The Future struct

                    # Special handling for async main: rename constructor, add wrapper
                    if item.name == 'main':
                        # Rename constructor: main -> __main_future
                        sm.constructor_fn.name = '__main_future'
                        new_items.append(sm.constructor_fn)
                        new_items.append(sm.poll_fn)

                        # Generate sync main wrapper
                        main_wrapper = self._generate_async_main_wrapper()
                        new_items.append(main_wrapper)
                    else:
                        new_items.append(sm.constructor_fn)
                        new_items.append(sm.poll_fn)

                except Exception as e:
                    # Fall back to keeping original function if transformation fails
                    # This allows MVP to work while we develop the full transformation
                    import sys
                    print(f"WARNING: Async transform failed for {item.name}: {e}", file=sys.stderr)
                    new_items.append(item)
            else:
                new_items.append(item)

        # Return modified module
        return rast.Module(items=new_items, span=module.span)

    def _generate_async_main_wrapper(self) -> rast.FnDef:
        """Generate a synchronous main wrapper for async main.

        Generates:
            fn main() -> i32
                var future: main_Future = __main_future()
                while true
                    let result: i32 = main_poll(&future)
                    if result >= 0
                        return result
        """
        dummy_span = rast.Span(0, 0, 0, 0)

        # var future: main_Future = __main_future()
        future_init = rast.VarStmt(
            span=dummy_span,
            name='future',
            type=rast.NamedType(span=dummy_span, name='main_Future'),
            value=rast.Call(
                span=dummy_span,
                func=rast.Ident(span=dummy_span, name='__main_future'),
                args=[]
            )
        )

        # let result: i32 = main_poll(&future)
        poll_call = rast.LetStmt(
            span=dummy_span,
            name='result',
            type=rast.NamedType(span=dummy_span, name='i32'),
            value=rast.Call(
                span=dummy_span,
                func=rast.Ident(span=dummy_span, name='main_poll'),
                args=[rast.UnaryOp(
                    span=dummy_span,
                    op='&',
                    operand=rast.Ident(span=dummy_span, name='future')
                )]
            )
        )

        # if result >= 0: return result
        check_ready = rast.If(
            span=dummy_span,
            cond=rast.BinOp(
                span=dummy_span,
                op='>=',
                left=rast.Ident(span=dummy_span, name='result'),
                right=rast.IntLit(span=dummy_span, value=0)
            ),
            then_block=rast.Block(
                span=dummy_span,
                stmts=[rast.ReturnStmt(
                    span=dummy_span,
                    value=rast.Ident(span=dummy_span, name='result')
                )],
                expr=None
            ),
            else_block=None
        )

        # while true { poll; check }
        poll_loop = rast.WhileStmt(
            span=dummy_span,
            cond=rast.BoolLit(span=dummy_span, value=True),
            body=rast.Block(
                span=dummy_span,
                stmts=[poll_call, rast.ExprStmt(span=dummy_span, expr=check_ready)],
                expr=None
            )
        )

        # Function body
        body = rast.Block(
            span=dummy_span,
            stmts=[future_init, poll_loop],
            expr=None
        )

        return rast.FnDef(
            span=dummy_span,
            name='main',
            params=[],
            ret_type=rast.NamedType(span=dummy_span, name='i32'),
            body=body,
            is_async=False
        )

    def _declare_struct(self, struct_def: rast.StructDef):
        """Declare a struct type (opaque, no body yet).

        This enables forward references - structs can reference each other
        regardless of source order.
        """
        # Store field info for later lookup (legacy - kept for compatibility)
        self.struct_fields[struct_def.name] = struct_def.fields

        # [[packed]] attribute removes alignment padding between fields
        is_packed = struct_def.has_attr('packed')

        # Register in struct registry for layout computation
        self.struct_registry.declare(struct_def.name, struct_def.fields, packed=is_packed)

        # Create LLVM identified struct type (opaque - no body yet)
        # This ensures structs with the same field layout are distinguishable
        unique_name = f"struct.{self.module.name}.{struct_def.name}"
        struct_type = self.module.context.get_identified_type(unique_name, packed=is_packed)
        self.struct_types[struct_def.name] = struct_type

    def _define_struct(self, struct_def: rast.StructDef):
        """Define a struct type body (after all structs are declared).

        Now that all struct names are registered, we can resolve field types
        including forward references and self-references.

        Also computes and caches the struct layout with proper field offsets
        and alignment in the struct registry.
        """
        struct_type = self.struct_types[struct_def.name]
        field_types = [self._ritz_type_to_llvm(ty) for _, ty in struct_def.fields]
        struct_type.set_body(*field_types)

        # Compute layout with proper alignment
        self.struct_registry.compute_layout(
            struct_def.name,
            self._ritz_type_size_and_align
        )

    def _declare_enum(self, enum_def: rast.EnumDef):
        """Declare an enum type (opaque, no body yet).

        Enums are similar to unions but with named variants.
        Layout: { i8 tag, [max_size x i8] data }
        """
        # Create LLVM identified struct type (opaque - no body yet)
        unique_name = f"enum.{self.module.name}.{enum_def.name}"
        enum_type = self.module.context.get_identified_type(unique_name)
        # Store placeholder - will be defined in _define_enum
        self.enum_types[enum_def.name] = (enum_type, enum_def.variants)

        # Register variant names for constructor resolution
        for variant in enum_def.variants:
            self.variant_to_enum[variant.name] = enum_def.name

    def _define_enum(self, enum_def: rast.EnumDef):
        """Define an enum type body (after all types are declared).

        Calculates the max size and alignment needed for variant payloads and creates
        a struct layout with proper alignment for the data field.

        Layout: { i8 tag, [padding x i8], [max_size x i8] data }

        The data field is aligned to the maximum alignment requirement of any variant
        payload. For example, if a variant contains a String (8-byte alignment),
        the data field will be at offset 8, not offset 1.

        For Option<i32>:
            Some(i32) -> needs 4 bytes, 4-byte alignment
            None -> needs 0 bytes
            Result: { i8, [3 x i8] padding, [4 x i8] data } = 8 bytes total

        For Result<String, i32>:
            Ok(String) -> needs 24 bytes, 8-byte alignment
            Err(i32) -> needs 4 bytes, 4-byte alignment
            Result: { i8, [7 x i8] padding, [24 x i8] data } = 32 bytes total
        """
        enum_type, variants = self.enum_types[enum_def.name]

        # Calculate max size and alignment of all variant payloads
        max_size = 0
        max_align = 1
        for variant in variants:
            variant_size = 0
            for field_type in variant.fields:
                size, align = self._ritz_type_size_and_align(field_type)
                variant_size += size
                max_align = max(max_align, align)
            if variant_size > max_size:
                max_size = variant_size

        # Layout with proper alignment for data buffer
        # If max_size is 0 (all unit variants), we still need the tag
        if max_size > 0:
            # Compute padding needed after tag (1 byte) to align data to max_align
            tag_size = 1
            padding_needed = (max_align - (tag_size % max_align)) % max_align

            if padding_needed > 0:
                # Layout: { i8 tag, [padding x i8], [max_size x i8] data }
                padding_array = ir.ArrayType(self.i8, padding_needed)
                data_array = ir.ArrayType(self.i8, max_size)
                enum_type.set_body(self.i8, padding_array, data_array)
            else:
                # No padding needed (data is 1-byte aligned)
                # Layout: { i8 tag, [max_size x i8] data }
                data_array = ir.ArrayType(self.i8, max_size)
                enum_type.set_body(self.i8, data_array)
        else:
            # All unit variants - just a tag
            enum_type.set_body(self.i8)

    def _get_enum_data_index(self, enum_name: str) -> int:
        """Get the struct index of the data buffer in an enum.

        Returns 1 if no padding is needed (data follows tag at index 1),
        or 2 if padding is present (tag at 0, padding at 1, data at 2).
        """
        if enum_name not in self.enum_types:
            raise ValueError(f"Unknown enum type: {enum_name}")

        enum_type, variants = self.enum_types[enum_name]

        # Calculate max alignment of all variant payloads
        max_align = 1
        has_data = False
        for variant in variants:
            for field_type in variant.fields:
                has_data = True
                _, align = self._ritz_type_size_and_align(field_type)
                max_align = max(max_align, align)

        if not has_data:
            # No data buffer (all unit variants)
            raise ValueError(f"Enum {enum_name} has no data buffer")

        # If max_align > 1, we need padding after the 1-byte tag
        tag_size = 1
        padding_needed = (max_align - (tag_size % max_align)) % max_align

        # Index 0 is tag, index 1 is padding (if present), index 2 (or 1) is data
        return 2 if padding_needed > 0 else 1

    def _get_enum_variant_tag(self, enum_name: str, variant_name: str) -> int:
        """Get the tag value for an enum variant."""
        if enum_name not in self.enum_types:
            raise ValueError(f"Unknown enum type: {enum_name}")
        _, variants = self.enum_types[enum_name]
        for i, variant in enumerate(variants):
            if variant.name == variant_name:
                return i
        raise ValueError(f"Unknown variant {variant_name} in enum {enum_name}")

    def _get_enum_variant(self, enum_name: str, variant_name: str) -> rast.Variant:
        """Get the Variant object for an enum variant."""
        if enum_name not in self.enum_types:
            raise ValueError(f"Unknown enum type: {enum_name}")
        _, variants = self.enum_types[enum_name]
        for variant in variants:
            if variant.name == variant_name:
                return variant
        raise ValueError(f"Unknown variant {variant_name} in enum {enum_name}")

    def _emit_enum_variant_constructor(self, variant_name: str, args: List[rast.Expr]) -> ir.Value:
        """Emit code to construct an enum variant value.

        For Some(42):
            1. Get the enum type (Option_i32)
            2. Get the tag for Some (0)
            3. Allocate stack space for the enum
            4. Store the tag
            5. Store the payload data
            6. Return the enum value

        For None:
            1. Get the enum type
            2. Get the tag for None (1)
            3. Create enum value with just the tag
        """
        enum_name = self.variant_to_enum[variant_name]
        enum_type, variants = self.enum_types[enum_name]
        tag = self._get_enum_variant_tag(enum_name, variant_name)
        variant = self._get_enum_variant(enum_name, variant_name)

        # Allocate stack space for the enum
        enum_alloca = self.builder.alloca(enum_type, name=f"{variant_name}.alloca")

        # Store the tag (index 0)
        tag_ptr = self.builder.gep(enum_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        self.builder.store(ir.Constant(self.i8, tag), tag_ptr)

        # Store payload data if any
        if variant.fields and args:
            # Get pointer to data buffer (index depends on alignment padding)
            data_index = self._get_enum_data_index(enum_name)
            data_ptr = self.builder.gep(enum_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, data_index)])

            # For each field in the variant, store the corresponding arg
            offset = 0
            for i, (field_type, arg) in enumerate(zip(variant.fields, args)):
                arg_val = self._emit_expr(arg)
                llvm_field_type = self._ritz_type_to_llvm(field_type)

                # Convert arg to field type (e.g., i64 literal -> i32)
                arg_val = self._convert_type(arg_val, llvm_field_type)

                # Cast data buffer to pointer to field type
                field_ptr = self.builder.bitcast(
                    self.builder.gep(data_ptr, [ir.Constant(self.i32, offset)]),
                    ir.PointerType(llvm_field_type)
                )
                self.builder.store(arg_val, field_ptr)
                offset += self._type_size_bytes(llvm_field_type)

        # Load and return the enum value
        return self.builder.load(enum_alloca)

    def _is_enum_variant_call(self, expr: rast.Expr) -> bool:
        """Check if expression is an enum variant constructor call."""
        if isinstance(expr, rast.Call):
            if isinstance(expr.func, rast.Ident):
                return expr.func.name in self.variant_to_enum
        elif isinstance(expr, rast.Ident):
            # Unit variant without parens
            return expr.name in self.variant_to_enum
        return False

    def _emit_enum_variant_with_type(self, expr: rast.Expr, enum_type_name: str) -> ir.Value:
        """Emit an enum variant constructor with explicit type context.

        This handles cases like `var opt: Option<i64> = Some(42)` where
        we need to construct the variant using the declared type, not
        the first registered enum with that variant name.
        """
        if isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident):
            variant_name = expr.func.name
            return self._emit_enum_variant_constructor_for_type(variant_name, expr.args, enum_type_name)
        elif isinstance(expr, rast.Ident):
            # Unit variant without parens
            return self._emit_enum_variant_constructor_for_type(expr.name, [], enum_type_name)
        else:
            # Fallback to regular expression emission
            return self._emit_expr(expr)

    def _emit_enum_variant_constructor_for_type(self, variant_name: str, args: List[rast.Expr], enum_name: str) -> ir.Value:
        """Emit code to construct an enum variant for a specific enum type.

        This is like _emit_enum_variant_constructor but uses the specified
        enum type rather than looking up variant_to_enum.
        """
        if enum_name not in self.enum_types:
            raise ValueError(f"Unknown enum type: {enum_name}")

        enum_type, variants = self.enum_types[enum_name]
        tag = self._get_enum_variant_tag(enum_name, variant_name)
        variant = self._get_enum_variant(enum_name, variant_name)

        # Allocate stack space for the enum
        enum_alloca = self.builder.alloca(enum_type, name=f"{variant_name}.alloca")

        # Store the tag (index 0)
        tag_ptr = self.builder.gep(enum_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        self.builder.store(ir.Constant(self.i8, tag), tag_ptr)

        # Store payload data if any
        if variant.fields and args:
            # Get pointer to data buffer (index depends on alignment padding)
            data_index = self._get_enum_data_index(enum_name)
            data_ptr = self.builder.gep(enum_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, data_index)])

            # For each field in the variant, store the corresponding arg
            offset = 0
            for i, (field_type, arg) in enumerate(zip(variant.fields, args)):
                arg_val = self._emit_expr(arg)
                llvm_field_type = self._ritz_type_to_llvm(field_type)

                # Convert arg to field type (e.g., i64 literal -> i32)
                arg_val = self._convert_type(arg_val, llvm_field_type)

                # Cast data buffer to pointer to field type
                field_ptr = self.builder.bitcast(
                    self.builder.gep(data_ptr, [ir.Constant(self.i32, offset)]),
                    ir.PointerType(llvm_field_type)
                )
                self.builder.store(arg_val, field_ptr)
                offset += self._type_size_bytes(llvm_field_type)

        # Load and return the enum value
        return self.builder.load(enum_alloca)

    def _process_type_alias(self, type_alias: rast.TypeAlias):
        """Process a type alias, creating union types as needed.

        For union types (A | B | C), creates:
        - Named LLVM struct type with layout: { i8 tag, [max_size x i8] data }
        - Stores variant information for later cast/match operations
        """
        self.type_aliases[type_alias.name] = type_alias.target

        if isinstance(type_alias.target, rast.UnionType):
            # Calculate max size of all variants
            max_size = 0
            variants = type_alias.target.variants
            for variant in variants:
                llvm_ty = self._ritz_type_to_llvm(variant)
                size = self._type_size_bytes(llvm_ty)
                if size > max_size:
                    max_size = size

            # Create named struct type for this union
            unique_name = f"union.{self.module.name}.{type_alias.name}"
            union_type = self.module.context.get_identified_type(unique_name)
            # Layout: { i8 tag, [max_size x i8] data }
            data_array = ir.ArrayType(self.i8, max_size)
            union_type.set_body(self.i8, data_array)

            # Store union info
            self.union_types[type_alias.name] = (union_type, variants)

    def _get_union_tag_for_type(self, union_name: str, variant_type: rast.Type) -> int:
        """Get the tag index for a variant type in a union."""
        if union_name not in self.union_types:
            raise ValueError(f"Unknown union type: {union_name}")
        _, variants = self.union_types[union_name]
        for i, variant in enumerate(variants):
            if self._types_equal(variant, variant_type):
                return i
        raise ValueError(f"Type {variant_type} is not a variant of union {union_name}")

    def _types_equal(self, a: rast.Type, b: rast.Type) -> bool:
        """Check if two Ritz types are equal."""
        if type(a) != type(b):
            return False
        if isinstance(a, rast.NamedType):
            return a.name == b.name
        if isinstance(a, rast.PtrType):
            return a.mutable == b.mutable and self._types_equal(a.inner, b.inner)
        if isinstance(a, rast.RefType):
            return a.mutable == b.mutable and self._types_equal(a.inner, b.inner)
        if isinstance(a, rast.ArrayType):
            # Extract integer sizes (may be int or IntLit)
            size_a = a.size.value if isinstance(a.size, rast.IntLit) else a.size
            size_b = b.size.value if isinstance(b.size, rast.IntLit) else b.size
            return size_a == size_b and self._types_equal(a.inner, b.inner)
        return False

    def _process_trait(self, trait_def: rast.TraitDef):
        """Process a trait definition.

        Stores method signatures for validation when checking impl blocks.
        Also creates vtable type for dyn Trait support.
        """
        self.traits[trait_def.name] = trait_def.methods

        # Create vtable type for dyn Trait
        # Vtable layout: { fn_ptr_drop, fn_ptr_method1, fn_ptr_method2, ... }
        vtable_fields = []

        # First slot: drop function (for destructor)
        # void (*drop)(void* self)
        drop_fn_type = ir.FunctionType(self.void, [self.i8_ptr])
        vtable_fields.append(ir.PointerType(drop_fn_type))

        # Add slots for each trait method
        for method in trait_def.methods:
            # Method signature: ret_type (*method)(void* self, args...)
            # First param is self as opaque pointer
            param_types = [self.i8_ptr]  # self as opaque ptr
            # Add other parameters (skip self param from method signature)
            for param in method.params[1:]:  # Skip self
                param_types.append(self._ritz_type_to_llvm(param.param_type))
            ret_type = self._ritz_type_to_llvm(method.ret_type) if method.ret_type else self.void
            fn_type = ir.FunctionType(ret_type, param_types)
            vtable_fields.append(ir.PointerType(fn_type))

        # Create vtable struct type
        vtable_type = self.module.context.get_identified_type(f"vtable.{trait_def.name}")
        vtable_type.set_body(*vtable_fields)
        self.vtable_types[trait_def.name] = vtable_type

        # Create dyn type: { *void data, *vtable }
        dyn_type = self.module.context.get_identified_type(f"dyn.{trait_def.name}")
        dyn_type.set_body(self.i8_ptr, ir.PointerType(vtable_type))
        self.dyn_types[trait_def.name] = dyn_type

    def _process_impl(self, impl_block: rast.ImplBlock):
        """Process an impl block.

        For each method in the impl:
        1. Create a mangled function name: Type_method (e.g., Point_print)
        2. Register in method_lookup for dispatch
        3. Declare the function (will be emitted later)
        4. Register the method body for emission

        With monomorphization, method calls are resolved at compile time to direct calls.
        Multiple impl blocks for the same type are merged.
        """
        key = (impl_block.trait_name, impl_block.type_name)
        if key not in self.impls:
            self.impls[key] = []
        self.impls[key].extend(impl_block.methods)

        for method in impl_block.methods:
            # Mangle name: Type_method
            mangled_name = f"{impl_block.type_name}_{method.name}"
            self.method_lookup[(impl_block.type_name, method.name)] = mangled_name

            # Create a copy of the method with the mangled name
            # We need to declare and emit it like a regular function
            mangled_method = rast.FnDef(
                span=method.span,
                name=mangled_name,
                params=method.params,
                ret_type=method.ret_type,
                body=method.body,
                attrs=method.attrs,
                type_params=method.type_params
            )
            # Preserve source_file for separate compilation
            if hasattr(method, 'source_file'):
                mangled_method.source_file = method.source_file
            # Declare the mangled function
            self._declare_function(mangled_method)

    def _emit_impl_methods(self):
        """Emit all method bodies from impl blocks.

        Called after all function signatures are declared.
        For separate compilation, only emit methods from the current source file.
        """
        for (trait_name, type_name), methods in self.impls.items():
            for method in methods:
                # Check if this method should be emitted in this compilation unit
                if not self._should_emit_body(method):
                    continue

                mangled_name = f"{type_name}_{method.name}"
                # Create mangled method def for emission
                mangled_method = rast.FnDef(
                    span=method.span,
                    name=mangled_name,
                    params=method.params,
                    ret_type=method.ret_type,
                    body=method.body,
                    attrs=method.attrs,
                    type_params=method.type_params
                )
                # Preserve is_monomorphized for weak linkage
                if getattr(method, 'is_monomorphized', False):
                    mangled_method.is_monomorphized = True
                self._emit_function_body(mangled_method)

    def _create_vtable_instances(self):
        """Create vtable instances for all trait implementations.

        For each (trait_name, impl_type) pair, creates a global constant
        vtable struct containing function pointers to the impl methods.
        """
        for (trait_name, type_name), methods in self.impls.items():
            # Skip inherent impls (no trait)
            if trait_name is None:
                continue

            # Skip if trait doesn't have a vtable type (shouldn't happen)
            if trait_name not in self.vtable_types:
                continue

            vtable_type = self.vtable_types[trait_name]
            trait_methods = self.traits.get(trait_name, [])

            # Build vtable values
            vtable_values = []

            # First slot: drop function
            # Look for a drop method, or use a no-op
            drop_mangled = f"{type_name}_drop"
            if drop_mangled in self.functions:
                fn, _ = self.functions[drop_mangled]
                # Cast to void(*)(void*) signature
                drop_fn_type = ir.FunctionType(self.void, [self.i8_ptr])
                vtable_values.append(fn.bitcast(ir.PointerType(drop_fn_type)))
            else:
                # No drop method - use null pointer
                drop_fn_type = ir.FunctionType(self.void, [self.i8_ptr])
                vtable_values.append(ir.Constant(ir.PointerType(drop_fn_type), None))

            # Add slots for each trait method
            for trait_method in trait_methods:
                mangled_name = f"{type_name}_{trait_method.name}"
                if mangled_name in self.functions:
                    fn, _ = self.functions[mangled_name]
                    # Get expected type from vtable
                    slot_index = len(vtable_values)
                    expected_fn_type = vtable_type.elements[slot_index].pointee
                    # Cast function pointer to opaque self version
                    vtable_values.append(fn.bitcast(ir.PointerType(expected_fn_type)))
                else:
                    # Method not found - this is an error but we'll use null for now
                    slot_index = len(vtable_values)
                    expected_fn_type = vtable_type.elements[slot_index].pointee
                    vtable_values.append(ir.Constant(ir.PointerType(expected_fn_type), None))

            # Create global vtable constant
            vtable_name = f"vtable.{trait_name}.{type_name}"
            vtable_const = ir.Constant(vtable_type, vtable_values)
            vtable_global = ir.GlobalVariable(self.module, vtable_type, name=vtable_name)
            vtable_global.global_constant = True
            vtable_global.initializer = vtable_const
            vtable_global.linkage = 'private'

            self.vtable_instances[(trait_name, type_name)] = vtable_global

    # ================================================================
    # Fat Pointer Operations (dyn Trait support)
    # ================================================================

    def _pack_fat_pointer(self, trait_name: str, data_ptr: ir.Value, vtable_ptr: ir.Value) -> ir.Value:
        """Create a fat pointer { data_ptr, vtable_ptr } for dyn Trait.

        Args:
            trait_name: Name of the trait
            data_ptr: Pointer to concrete type data (will be cast to i8*)
            vtable_ptr: Pointer to vtable global

        Returns:
            Fat pointer struct value
        """
        dyn_type = self.dyn_types[trait_name]

        # Cast data pointer to i8* if needed
        if data_ptr.type != self.i8_ptr:
            data_ptr = self.builder.bitcast(data_ptr, self.i8_ptr, name='dyn.data')

        # Build fat pointer struct
        fat_ptr = ir.Constant(dyn_type, ir.Undefined)
        fat_ptr = self.builder.insert_value(fat_ptr, data_ptr, 0, name='dyn.with_data')
        fat_ptr = self.builder.insert_value(fat_ptr, vtable_ptr, 1, name='dyn.fat_ptr')
        return fat_ptr

    def _extract_data_ptr(self, fat_pointer: ir.Value) -> ir.Value:
        """Extract data pointer from fat pointer (index 0)."""
        return self.builder.extract_value(fat_pointer, 0, name='dyn.data_ptr')

    def _extract_vtable_ptr(self, fat_pointer: ir.Value) -> ir.Value:
        """Extract vtable pointer from fat pointer (index 1)."""
        return self.builder.extract_value(fat_pointer, 1, name='dyn.vtable_ptr')

    def _get_vtable_for_type(self, trait_name: str, impl_type: str) -> Optional[ir.GlobalVariable]:
        """Look up vtable instance for (trait, type) pair."""
        return self.vtable_instances.get((trait_name, impl_type))

    def _get_trait_method_index(self, trait_name: str, method_name: str) -> int:
        """Get the index of a method in a trait's vtable.

        Index 0 is always the drop function, so methods start at index 1.
        """
        trait_methods = self.traits.get(trait_name, [])
        for i, method in enumerate(trait_methods):
            if method.name == method_name:
                return i + 1  # +1 because drop is at index 0
        raise ValueError(f"Method {method_name} not found in trait {trait_name}")

    def _get_struct_field_index(self, struct_name: str, field_name: str) -> int:
        """Get the index of a field in a struct.

        Uses the struct registry if layout is computed, otherwise falls back
        to the legacy struct_fields dict.
        """
        # Try struct registry first (preferred - has computed layout)
        layout = self.struct_registry.get_layout(struct_name)
        if layout:
            return layout.get_field_index(field_name)

        # Fallback to legacy struct_fields dict
        if struct_name not in self.struct_fields:
            raise ValueError(f"Unknown struct: {struct_name}")
        for i, (name, _) in enumerate(self.struct_fields[struct_name]):
            if name == field_name:
                return i
        raise ValueError(f"Unknown field {field_name} in struct {struct_name}")

    def _get_struct_name_from_type(self, ty: ir.Type) -> Optional[str]:
        """Get the struct name from an LLVM type."""
        for name, struct_ty in self.struct_types.items():
            if ty == struct_ty:
                return name
            # Also check pointer to struct
            if isinstance(ty, ir.PointerType) and ty.pointee == struct_ty:
                return name
        return None

    def _get_field_type(self, field_expr: rast.Field) -> Optional[rast.Type]:
        """Get the Ritz type of a struct field expression.

        Given a field access expression like `s.data`, returns the Ritz type
        of the `data` field in struct `s`. Used by _infer_unsigned_expr to
        determine signedness for struct field array indexing (Issue #98).
        """
        if not isinstance(field_expr.expr, rast.Ident):
            return None

        base_name = field_expr.expr.name
        if base_name not in self.ritz_types:
            return None

        struct_type = self.ritz_types[base_name]
        struct_name = None

        if isinstance(struct_type, rast.NamedType):
            struct_name = struct_type.name
        elif isinstance(struct_type, rast.PtrType) and isinstance(struct_type.inner, rast.NamedType):
            struct_name = struct_type.inner.name

        if struct_name and struct_name in self.struct_fields:
            for field_name, field_type in self.struct_fields[struct_name]:
                if field_name == field_expr.field:
                    return field_type

        return None

    def _is_box_type(self, struct_name: str) -> bool:
        """Check if a struct is a monomorphized Box<T> type (e.g., Box$Point)."""
        return struct_name.startswith('Box$')

    def _get_box_inner_type_name(self, box_struct_name: str) -> Optional[str]:
        """Get the inner type name from a Box struct (e.g., Box$Point -> Point)."""
        if not self._is_box_type(box_struct_name):
            return None
        return box_struct_name[4:]  # Strip 'Box$' prefix

    def _find_method_fallback(self, type_name: str, method_name: str) -> Optional[str]:
        """Find a standalone function that acts as a method for the given type.

        This provides UFCS (Uniform Function Call Syntax) for types without impl blocks.
        Enables method syntax v.len() to desugar to vec_len$u8(&v) for Vec$u8.

        Mapping rules:
        - Vec$T.method()   -> vec_method$T
        - Span$T.method()  -> span_method$T
        - String.method()  -> string_method
        - GrowBuf.method() -> growbuf_method (or buf_method)

        Returns the mangled function name if found, None otherwise.
        """
        # Known type prefixes and their function name mappings
        type_mappings = [
            ('Vec$', 'vec_'),      # Vec$u8 -> vec_
            ('Span$', 'span_'),    # Span$u8 -> span_
            ('Option$', 'option_'), # Option$i32 -> option_
            ('Result$', 'result_'), # Result$i32_Error -> result_
            ('Box$', 'box_'),      # Box$Point -> box_
        ]

        for prefix, fn_prefix in type_mappings:
            if type_name.startswith(prefix):
                # Extract type parameter suffix (e.g., "u8" from "Vec$u8")
                type_param = type_name[len(prefix):]
                # Try: vec_len$u8, vec_swap$u8, etc.
                candidate = f"{fn_prefix}{method_name}${type_param}"
                if candidate in self.functions:
                    return candidate

        # Non-generic types: String, GrowBuf, Buffer, etc.
        non_generic_mappings = {
            'String': 'string_',
            'GrowBuf': 'growbuf_',
            'Buffer': 'buf_',
            'ArgParser': 'args_',
        }

        if type_name in non_generic_mappings:
            fn_prefix = non_generic_mappings[type_name]
            candidate = f"{fn_prefix}{method_name}"
            if candidate in self.functions:
                return candidate

        return None

    def _struct_has_field(self, struct_name: str, field_name: str) -> bool:
        """Check if a struct has a given field without raising an exception."""
        layout = self.struct_registry.get_layout(struct_name)
        if layout:
            return any(f.name == field_name for f in layout.fields)
        if struct_name in self.struct_fields:
            return any(name == field_name for name, _ in self.struct_fields[struct_name])
        return False

    # =========================================================================
    # Drop trait / RAII support
    # =========================================================================

    def _type_implements_drop(self, ty: rast.Type) -> bool:
        """Check if a type implements the Drop trait."""
        if not isinstance(ty, rast.NamedType):
            return False
        # Look for impl Drop for TypeName
        type_name = ty.name
        return ('Drop', type_name) in self.impls

    def _get_drop_fn_name(self, ty: rast.Type) -> Optional[str]:
        """Get the mangled drop function name for a type, if it implements Drop."""
        if not isinstance(ty, rast.NamedType):
            return None
        type_name = ty.name
        # The method lookup stores (type_name, method_name) -> mangled_fn_name
        return self.method_lookup.get((type_name, 'drop'))

    def _push_drop_scope(self):
        """Enter a new scope for Drop tracking."""
        self.drop_scope_stack.append([])

    def _pop_drop_scope(self):
        """Exit the current scope, returning variables that need Drop."""
        if self.drop_scope_stack:
            return self.drop_scope_stack.pop()
        return []

    def _register_drop_variable(self, name: str, alloca: ir.AllocaInstr, ritz_type: rast.Type):
        """Register a variable that may need Drop when its scope ends.

        Creates a drop flag (i1 alloca initialized to 0) that gets set to 1
        when the variable is actually initialized. This handles conditional
        initialization correctly - we only drop variables that were actually
        created in this execution path.

        Returns the alloca for use with _mark_drop_variable_initialized.
        """
        if self.drop_scope_stack and self._type_implements_drop(ritz_type):
            # Create a drop flag alloca at the entry block (like all allocas)
            # Initialize to 0 (not yet initialized)
            entry_block = self.current_fn.entry_basic_block

            # Save current position
            current_block = self.builder.block

            # Insert flag alloca at start of entry block (after other allocas)
            # Find position after existing allocas
            first_non_alloca = None
            for instr in entry_block.instructions:
                if not isinstance(instr, ir.AllocaInstr):
                    first_non_alloca = instr
                    break

            if first_non_alloca:
                self.builder.position_before(first_non_alloca)
            else:
                self.builder.position_at_end(entry_block)

            flag_alloca = self.builder.alloca(self.i1, name=f"{name}.drop_flag")
            self.builder.store(ir.Constant(self.i1, 0), flag_alloca)

            # Restore position
            self.builder.position_at_end(current_block)

            # Register both the variable and its flag (key by alloca id, not name)
            self.drop_scope_stack[-1].append((name, alloca, ritz_type))
            self.drop_flags[id(alloca)] = flag_alloca

    def _mark_drop_variable_initialized(self, alloca: ir.AllocaInstr):
        """Set the drop flag to 1, indicating the variable is now initialized.

        This must be called after the variable is assigned a value.
        """
        alloca_id = id(alloca)
        if alloca_id in self.drop_flags:
            flag_alloca = self.drop_flags[alloca_id]
            self.builder.store(ir.Constant(self.i1, 1), flag_alloca)

    def _alloca_in_entry_block(self, ty: ir.Type, name: str) -> ir.AllocaInstr:
        """Allocate space in the entry block.

        All allocas should be in the entry block so they dominate all uses.
        This is required for mem2reg optimization and for correct drop handling.
        """
        entry_block = self.current_fn.entry_basic_block
        current_block = self.builder.block

        # Find position after existing allocas in entry block
        first_non_alloca = None
        for instr in entry_block.instructions:
            if not isinstance(instr, ir.AllocaInstr):
                first_non_alloca = instr
                break

        if first_non_alloca:
            self.builder.position_before(first_non_alloca)
        else:
            self.builder.position_at_end(entry_block)

        alloca = self.builder.alloca(ty, name=name)

        # Restore position
        self.builder.position_at_end(current_block)
        return alloca

    def _emit_drop_for_scope(self, drop_vars: List[Tuple[str, ir.AllocaInstr, rast.Type]],
                              exclude_var: Optional[str] = None):
        """Emit drop calls for variables in reverse declaration order.

        Uses drop flags to conditionally drop only variables that were actually
        initialized in this execution path.

        Args:
            drop_vars: List of (name, alloca, ritz_type) tuples
            exclude_var: Variable name to skip (for return moves)
        """
        # Drop in reverse order (LIFO - last declared, first dropped)
        for name, alloca, ritz_type in reversed(drop_vars):
            if exclude_var and name == exclude_var:
                # Skip - this variable is being moved out (returned)
                continue
            drop_fn_name = self._get_drop_fn_name(ritz_type)
            if drop_fn_name and drop_fn_name in self.functions:
                fn, _ = self.functions[drop_fn_name]

                # Check drop flag - only drop if variable was initialized
                alloca_id = id(alloca)
                if alloca_id in self.drop_flags:
                    flag_alloca = self.drop_flags[alloca_id]
                    flag_val = self.builder.load(flag_alloca, name=f"{name}.flag_check")

                    # Create conditional drop: if (flag) { drop(&var) }
                    drop_block = self.current_fn.append_basic_block(f"drop.{name}")
                    cont_block = self.current_fn.append_basic_block(f"drop.{name}.cont")

                    self.builder.cbranch(flag_val, drop_block, cont_block)

                    # Drop block
                    self.builder.position_at_end(drop_block)
                    self.builder.call(fn, [alloca])
                    self.builder.branch(cont_block)

                    # Continue after drop
                    self.builder.position_at_end(cont_block)
                else:
                    # No flag (shouldn't happen, but fall back to unconditional)
                    self.builder.call(fn, [alloca])

    def _emit_drop_for_all_scopes(self, exclude_var: Optional[str] = None):
        """Emit drop calls for all scopes (used before return).

        Args:
            exclude_var: Variable name to exclude from dropping (for return moves)
        """
        # Drop all scopes from innermost to outermost
        for scope in reversed(self.drop_scope_stack):
            self._emit_drop_for_scope(scope, exclude_var)

    def _declare_extern(self, extern: rast.ExternFn) -> ir.Function:
        """Declare an external function.

        For syscall-like functions (e.g., syscall1-6), these are handled
        specially and inlined. For other extern functions, we declare them
        in the LLVM module so they can be linked with external object files.
        """
        param_types = [self._ritz_type_to_llvm(p.type) for p in extern.params]
        ret_type = self._ritz_type_to_llvm(extern.ret_type) if extern.ret_type else self.void

        fn_type = ir.FunctionType(ret_type, param_types)

        # Check if this is a syscall function (handled specially)
        syscall_names = {'syscall0', 'syscall1', 'syscall2', 'syscall3',
                        'syscall4', 'syscall5', 'syscall6'}

        if extern.name in syscall_names:
            # Syscalls are inlined, don't declare in module
            self.extern_fns[extern.name] = (fn_type, extern)
            return None

        # Actually declare the extern function in the LLVM module
        # This allows linking with external assembly/object files
        fn = ir.Function(self.module, fn_type, name=extern.name)
        fn.linkage = 'external'

        # Store for later reference - use tuple format (fn, fn_def) like regular functions
        # For extern fns, we use the ExternFn object as the "definition"
        self.extern_fns[extern.name] = (fn_type, extern)
        self.functions[extern.name] = (fn, extern)

        return fn

    def _should_emit_body(self, item: rast.Item) -> bool:
        """Check if we should emit a function body for this item.

        With separate compilation enabled (source_file set), we only emit
        bodies for items from the current source file. Items from other
        files are declared but not defined (external linkage).

        Args:
            item: The AST item to check

        Returns:
            True if the function body should be emitted
        """
        # If no source file tracking, emit all bodies (legacy behavior)
        if self._current_source_file is None:
            return True

        # If item has no source_file set, it's from the main file
        item_source = getattr(item, 'source_file', None)
        if item_source is None:
            return True

        # Emit body only if item is from the current source file
        return item_source == self._current_source_file

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

    def _declare_function(self, fn_def: rast.FnDef) -> ir.Function:
        """Declare a function (create signature, register in functions dict).

        This is the first pass - declares all functions so they can be called
        from any other function regardless of source order.
        """
        # Skip if already declared (can happen with consolidated modules)
        if fn_def.name in self.functions:
            return self.functions[fn_def.name][0]

        # Build function type - use _param_to_llvm_type for RERITZ Borrow support
        param_types = [self._param_to_llvm_type(p) for p in fn_def.params]
        ret_type = self._ritz_type_to_llvm(fn_def.ret_type) if fn_def.ret_type else self.i32

        fn_type = ir.FunctionType(ret_type, param_types)
        fn = ir.Function(self.module, fn_type, name=fn_def.name)

        # Set linkage: non-pub functions get internal linkage (not visible to linker)
        # This prevents symbol collisions when linking multiple modules
        # Exception: 'main' always needs external linkage so runtime _start can call it
        # Exception: When no_runtime is set (separate compilation), all functions are external
        #            since other modules may need to call them
        if not getattr(self, 'no_runtime', False):
            if not fn_def.is_pub and fn_def.name != 'main' and self._should_emit_body(fn_def):
                fn.linkage = 'internal'

        # Create DISubprogram for debug info (only for functions we'll define, not declarations)
        if self.emit_debug and self.di_file and self._should_emit_body(fn_def):
            # Get line from span if available
            span = getattr(fn_def, 'span', None)
            line = span.line if span else 1
            di_sp = self.module.add_debug_info('DISubprogram', {
                'name': fn_def.name,
                'file': self.di_file,
                'line': line,
                'scopeLine': line,
                'type': self.di_subroutine_type,
                'isLocal': False,
                'isDefinition': True,
                'unit': self.di_compile_unit,
            }, is_distinct=True)
            self.di_subprograms[fn_def.name] = di_sp
            fn.set_metadata('dbg', di_sp)

        # Add inline attributes if specified
        if fn_def.has_attr('inline'):
            fn.attributes.add('inlinehint')
        elif fn_def.has_attr('always_inline'):
            fn.attributes.add('alwaysinline')
        elif fn_def.has_attr('noinline'):
            fn.attributes.add('noinline')

        # [[naked]] functions have no prologue/epilogue - useful for interrupt handlers
        # and low-level kernel code that manages its own stack frame
        if fn_def.has_attr('naked'):
            fn.attributes.add('naked')

        # For freestanding targets (kernel mode), add attributes to disable
        # stack protector and red zone - these require runtime support not
        # available in kernel/freestanding environments
        if self.is_freestanding:
            fn.attributes.add('noredzone')
            # Note: "ssp" attributes would enable stack protector; not adding them
            # means stack protector is disabled by default

        # Register function so it can be called from any function body
        self.functions[fn_def.name] = (fn, fn_def)
        return fn

    def _set_debug_loc(self, node) -> None:
        """Set debug location on current builder position from AST node.

        If the node has a span with line/column info, creates a DILocation
        and attaches it to subsequent instructions.
        """
        if not self.emit_debug or not self.current_di_scope:
            return

        # Get line/column from span (preferred) or direct attributes (fallback)
        span = getattr(node, 'span', None)
        if span:
            line = span.line
            col = span.column
        else:
            line = getattr(node, 'line', 0)
            col = getattr(node, 'column', 0) or getattr(node, 'col', 0)

        if line > 0:
            di_loc = self.module.add_debug_info('DILocation', {
                'line': line,
                'column': col if col > 0 else 1,
                'scope': self.current_di_scope,
            })
            self.builder.debug_metadata = di_loc

    def _emit_function_body(self, fn_def: rast.FnDef) -> ir.Function:
        """Emit a function body (second pass, after all functions declared)."""
        fn, _ = self.functions[fn_def.name]
        ret_type = self._ritz_type_to_llvm(fn_def.ret_type) if fn_def.ret_type else self.i32

        # Set linkage for monomorphized functions to avoid duplicate symbol errors
        # linkonce_odr means: keep one copy, merge duplicates (One Definition Rule)
        if getattr(fn_def, 'is_monomorphized', False):
            fn.linkage = 'linkonce_odr'

        self.current_fn = fn

        # Set current debug scope
        if self.emit_debug and fn_def.name in self.di_subprograms:
            self.current_di_scope = self.di_subprograms[fn_def.name]

        # Create entry block
        block = fn.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)

        # Reset state
        self.locals.clear()
        self.params.clear()
        self.has_returned = False
        self.current_fn_def = fn_def
        self.in_test_fn = fn_def.has_attr('test')
        self.drop_scope_stack.clear()  # Clear drop scopes from previous function
        self.drop_flags.clear()  # Clear drop flags from previous function
        self.simd_expected_type = None  # Clear SIMD type context from previous function
        self.closure_expected_type = None  # Clear closure type context from previous function

        # [[naked]] functions have special semantics:
        # - No prologue/epilogue generated by LLVM
        # - Cannot access parameters through LLVM IR (must use asm directly)
        # - Body must be inline asm followed by unreachable
        if fn_def.has_attr('naked'):
            # For naked functions, emit ONLY the inline asm statements
            # Parameters exist for type-checking but are not usable as LLVM values
            for stmt in fn_def.body.stmts:
                if isinstance(stmt, rast.AsmStmt):
                    self._emit_asm(stmt)
                # Skip other statements - naked functions can only contain asm

            # Naked functions must end with unreachable (the asm must handle return)
            if not self.builder.block.is_terminated:
                self.builder.unreachable()
            return fn

        # Push function-level drop scope
        self._push_drop_scope()

        # Set up parameters - allocate them like locals so they can be mutated
        # Get function line number for parameter debug info
        fn_span = getattr(fn_def, 'span', None)
        fn_line = fn_span.line if fn_span else 1

        for arg, param in zip(fn.args, fn_def.params):
            arg.name = f"{param.name}.arg"

            # Check if parameter is a reference type or mutable borrow
            is_mutable_borrow = hasattr(param, 'borrow') and param.borrow == rast.Borrow.MUTABLE
            is_ref_type = isinstance(param.type, rast.RefType)

            if is_mutable_borrow:
                # :& borrow: arg is *T where T is param.type
                # Store in locals so `x = val` assignments work (load/store through pointer)
                # The arg IS the alloca-like storage (a pointer passed from caller)
                self.locals[param.name] = (arg, arg.type.pointee)
                self.ritz_types[param.name] = param.type
                # Don't register for Drop - borrowed values are not owned
                self._emit_dbg_declare(arg, param.name, param.type, fn_line)
            elif is_ref_type:
                # @T or @&T: arg is already *T (pointer), and the TYPE is RefType
                # Store in params so `x` expression returns the pointer value
                self.params[param.name] = (arg, arg.type)
                self.ritz_types[param.name] = param.type
                # Don't register for Drop - borrowed values are not owned
                self._emit_dbg_declare(arg, param.name, param.type, fn_line)
            else:
                # Moved/value parameter: allocate storage like before
                alloca = self.builder.alloca(arg.type, name=param.name)
                self.builder.store(arg, alloca)
                self.locals[param.name] = (alloca, arg.type)
                # Store Ritz type for enum/union detection in match expressions
                self.ritz_types[param.name] = param.type
                # Register parameter for Drop if it has a Drop impl
                self._register_drop_variable(param.name, alloca, param.type)
                # Parameters are always initialized on entry
                self._mark_drop_variable_initialized(alloca)
                # Emit debug info for parameter
                self._emit_dbg_declare(alloca, param.name, param.type, fn_line)

        # Emit body (Block contains stmts and optional trailing expr)
        last_val = None
        for stmt in fn_def.body.stmts:
            result = self._emit_stmt(stmt)
            if result is True:  # Block terminated
                break

        # Handle trailing expression and implicit return
        if not self.has_returned and not self.builder.block.is_terminated:
            if fn_def.body.expr:
                # Check if we're returning a local variable - it should be moved, not dropped
                exclude_var = None
                if isinstance(fn_def.body.expr, rast.Ident):
                    var_name = fn_def.body.expr.name
                    if var_name in self.locals:
                        # This is a local variable being returned - treat as move
                        exclude_var = var_name

                # Set debug location for trailing expression
                self._set_debug_loc(fn_def.body.expr)
                # Set expected type for closure inference if return type is a function type
                if isinstance(fn_def.ret_type, rast.FnType):
                    self.closure_expected_type = fn_def.ret_type
                last_val = self._emit_expr(fn_def.body.expr)
                self.closure_expected_type = None  # Clear context
                last_val = self._convert_type(last_val, ret_type)
                # Emit drops before returning (excluding moved variable)
                self._emit_drop_for_all_scopes(exclude_var)
                self.builder.ret(last_val)
            else:
                # Emit drops before implicit return
                self._emit_drop_for_all_scopes()
                self.builder.ret(ir.Constant(ret_type, 0))

        return fn

    def _emit_start_function(self) -> None:
        """Emit the _start entry point for Linux x86_64."""
        # We need to emit this as raw IR text since llvmlite doesn't support naked functions
        # This will be appended after the module is stringified
        num_params = len(self.main_fn_def.params)
        main_takes_args = num_params >= 2
        main_takes_envp = num_params >= 3

        # Create a void function
        start_type = ir.FunctionType(self.void, [])
        start_fn = ir.Function(self.module, start_type, name="_start")

        # Mark as naked - llvmlite doesn't support this directly
        # We'll need to fix up the IR string later

        block = start_fn.append_basic_block(name="entry")
        builder = ir.IRBuilder(block)

        # Emit inline asm - llvmlite's inline asm support is limited
        # We'll use the call asm sideeffect approach
        #
        # Stack layout at _start:
        #   (%rsp)     = argc
        #   8(%rsp)    = argv[0]
        #   ...          argv[argc] = NULL
        #   ...          envp[0], envp[1], ..., NULL
        #
        # For 3-arg main: envp = &argv[argc+1] = argv + (argc+1)*8
        if main_takes_envp:
            # 3-argument main(argc, argv, envp)
            asm_str = """
    movq (%rsp), %rdi
    leaq 8(%rsp), %rsi
    leaq 8(%rsi,%rdi,8), %rdx
    andq $$-16, %rsp
    call main
    movq %rax, %rdi
    movq $$60, %rax
    syscall
  """
        elif main_takes_args:
            # 2-argument main(argc, argv)
            asm_str = """
    movq (%rsp), %rdi
    leaq 8(%rsp), %rsi
    andq $$-16, %rsp
    call main
    movq %rax, %rdi
    movq $$60, %rax
    syscall
  """
        else:
            # 0-argument main()
            asm_str = """
    andq $$-16, %rsp
    call main
    movq %rax, %rdi
    movq $$60, %rax
    syscall
  """

        # Create inline asm type
        asm_func_ty = ir.FunctionType(self.void, [])
        asm_ir = ir.InlineAsm(asm_func_ty, asm_str,
                              "~{rax},~{rdi},~{rsi},~{rdx},~{rsp},~{rcx},~{r11},~{memory}",
                              side_effect=True)
        builder.call(asm_ir, [])
        builder.unreachable()

    def _emit_memset_function(self) -> None:
        """Emit a memset implementation for -nostdlib linking.

        When LLVM lowers the llvm.memset intrinsic, it may emit a call to
        the libc memset function. When linking with -nostdlib, we need to
        provide this symbol ourselves.

        Signature: void *memset(void *dest, int c, size_t n)
        """
        # void* memset(void* dest, int c, size_t n)
        memset_ty = ir.FunctionType(
            self.i8.as_pointer(),
            [self.i8.as_pointer(), self.i32, self.i64]
        )
        memset_fn = ir.Function(self.module, memset_ty, name="memset")

        entry = memset_fn.append_basic_block("entry")
        loop = memset_fn.append_basic_block("loop")
        done = memset_fn.append_basic_block("done")

        builder = ir.IRBuilder(entry)
        dest, c, n = memset_fn.args

        # Truncate c (i32) to i8 for byte storage
        c_byte = builder.trunc(c, self.i8)

        # Check if n == 0, skip loop
        is_zero = builder.icmp_unsigned("==", n, ir.Constant(self.i64, 0))
        builder.cbranch(is_zero, done, loop)

        # Loop: for i in 0..n: dest[i] = c
        builder = ir.IRBuilder(loop)
        i_phi = builder.phi(self.i64, "i")
        i_phi.add_incoming(ir.Constant(self.i64, 0), entry)

        ptr = builder.gep(dest, [i_phi], inbounds=True)
        builder.store(c_byte, ptr)

        i_next = builder.add(i_phi, ir.Constant(self.i64, 1))
        i_phi.add_incoming(i_next, loop)

        cond = builder.icmp_unsigned("<", i_next, n)
        builder.cbranch(cond, loop, done)

        # Return dest
        builder = ir.IRBuilder(done)
        builder.ret(dest)

    def _emit_stmt(self, stmt: rast.Stmt) -> Union[bool, ir.Value, None]:
        """Emit a statement. Returns True if block terminated."""
        # Set debug location for source-level debugging
        self._set_debug_loc(stmt)

        if isinstance(stmt, rast.ReturnStmt):
            ret_type = self.current_fn.function_type.return_type
            if stmt.value:
                # Check if we're returning a local variable - it should be moved, not dropped
                exclude_var = None
                if isinstance(stmt.value, rast.Ident):
                    var_name = stmt.value.name
                    if var_name in self.locals:
                        # This is a local variable being returned - treat as move
                        exclude_var = var_name

                # Set expected type for closure inference if return type is a function type
                if self.current_fn_def and isinstance(self.current_fn_def.ret_type, rast.FnType):
                    self.closure_expected_type = self.current_fn_def.ret_type
                val = self._emit_expr(stmt.value)
                self.closure_expected_type = None  # Clear context
                val = self._convert_type(val, ret_type)
                # Emit drops for all scopes before return (excluding moved variable)
                self._emit_drop_for_all_scopes(exclude_var)
                self.builder.ret(val)
            else:
                # Emit drops for all scopes before return
                self._emit_drop_for_all_scopes()
                if ret_type == self.void:
                    self.builder.ret_void()
                else:
                    self.builder.ret(ir.Constant(ret_type, 0))
            self.has_returned = True
            return True

        elif isinstance(stmt, rast.VarStmt):
            ritz_type = stmt.type  # May be None if type is inferred
            # Get line number for debug info
            stmt_span = getattr(stmt, 'span', None)
            stmt_line = stmt_span.line if stmt_span else 1

            if stmt.type:
                ty = self._ritz_type_to_llvm(stmt.type)
                self.ritz_types[stmt.name] = stmt.type  # Store Ritz type for signedness
            elif stmt.value:
                # Infer from value - emit first to get LLVM type
                val = self._emit_expr(stmt.value)
                ty = val.type
                # Also infer Ritz type for Drop tracking
                inferred_ritz_type = self._infer_ritz_type(stmt.value, val)
                if inferred_ritz_type:
                    ritz_type = inferred_ritz_type
                    self.ritz_types[stmt.name] = ritz_type
                # Always allocate in entry block to prevent stack leaks in loops
                alloca = self._alloca_in_entry_block(ty, f"{stmt.name}.addr")
                self.builder.store(val, alloca)
                self.locals[stmt.name] = (alloca, ty)
                # Register for Drop if type was inferred and implements Drop
                if ritz_type:
                    self._register_drop_variable(stmt.name, alloca, ritz_type)
                    self._mark_drop_variable_initialized(alloca)
                return None
            else:
                ty = self.i64  # Default

            # Always allocate in entry block to prevent stack leaks in loops
            # and to ensure allocas dominate all uses (required for mem2reg).
            alloca = self._alloca_in_entry_block(ty, f"{stmt.name}.addr")

            if stmt.value:
                # Handle String literal inference: "hello" -> string_from("hello")
                if (stmt.type and isinstance(stmt.type, rast.NamedType)
                    and stmt.type.name == 'String'
                    and isinstance(stmt.value, rast.StringLit)):
                    val = self._emit_string_from_literal(stmt.value)
                    val = self._convert_type(val, ty)
                    self.builder.store(val, alloca)
                # Special case: large array fill - initialize alloca directly with memset
                # This avoids loading/storing huge arrays which crashes LLVM SelectionDAG
                elif isinstance(stmt.value, rast.ArrayFill) and stmt.value.count > 64:
                    self._emit_array_fill_to_alloca(stmt.value, alloca, ty)
                # Check if this is an enum variant constructor that needs type context
                elif self._is_enum_variant_call(stmt.value) and stmt.type and isinstance(stmt.type, rast.NamedType):
                    # Use declared enum type to construct the correct variant
                    val = self._emit_enum_variant_with_type(stmt.value, stmt.type.name)
                    val = self._convert_type(val, ty)
                    self.builder.store(val, alloca)
                else:
                    # Set SIMD expected type context for var statements too
                    if stmt.type and isinstance(stmt.type, rast.NamedType):
                        if stmt.type.name in ('v8i32', 'v4i64', 'v16i16', 'v32i8',
                                              'v4i32', 'v2i64', 'v8i16', 'v16i8'):
                            self.simd_expected_type = stmt.type
                    val = self._emit_expr(stmt.value)
                    self.simd_expected_type = None  # Clear SIMD context
                    val = self._convert_type(val, ty)
                    self.builder.store(val, alloca)
            self.locals[stmt.name] = (alloca, ty)
            # Register for Drop if type is known and implements Drop
            if ritz_type:
                self._register_drop_variable(stmt.name, alloca, ritz_type)
                # Mark as initialized if we just assigned a value
                if stmt.value:
                    self._mark_drop_variable_initialized(alloca)
            # Emit debug info for variable (requires ritz_type for proper type info)
            if ritz_type:
                self._emit_dbg_declare(alloca, stmt.name, ritz_type, stmt_line)
            return None

        elif isinstance(stmt, rast.LetStmt):
            # Handle String literal inference: "hello" -> string_from("hello")
            if (stmt.type and isinstance(stmt.type, rast.NamedType)
                and stmt.type.name == 'String'
                and isinstance(stmt.value, rast.StringLit)):
                # Convert string literal to String via string_from
                val = self._emit_string_from_literal(stmt.value)
            else:
                # Set expected type context for closure type inference
                if stmt.type and isinstance(stmt.type, rast.FnType):
                    self.closure_expected_type = stmt.type
                # Set expected type context for SIMD type inference (e.g., v8i32 vs v4i32)
                if stmt.type and isinstance(stmt.type, rast.NamedType):
                    if stmt.type.name in ('v8i32', 'v4i64', 'v16i16', 'v32i8',
                                          'v4i32', 'v2i64', 'v8i16', 'v16i8'):
                        self.simd_expected_type = stmt.type
                val = self._emit_expr(stmt.value)
                self.closure_expected_type = None  # Clear context
                self.simd_expected_type = None  # Clear SIMD context
            if stmt.type:
                # Use declared type and convert value if needed
                declared_ty = self._ritz_type_to_llvm(stmt.type)
                val = self._convert_type(val, declared_ty)
                self.params[stmt.name] = (val, declared_ty)
                self.ritz_types[stmt.name] = stmt.type  # Store Ritz type for signedness
                # Note: let bindings don't get allocas, they're just SSA values
                # For Drop to work, the variable needs to be addressable (use var instead of let)
            else:
                # Infer Ritz type from expression for signedness tracking
                inferred_ritz_type = self._infer_ritz_type(stmt.value, val)
                self.params[stmt.name] = (val, val.type)
                if inferred_ritz_type:
                    self.ritz_types[stmt.name] = inferred_ritz_type
            return None

        elif isinstance(stmt, rast.AssignStmt):
            val = self._emit_expr(stmt.value)
            if isinstance(stmt.target, rast.Ident):
                name = stmt.target.name
                if name in self.locals:
                    alloca, ty = self.locals[name]
                    val = self._convert_type(val, ty)
                    self.builder.store(val, alloca)
                elif name in self.globals:
                    gvar, ty = self.globals[name]
                    val = self._convert_type(val, ty)
                    self.builder.store(val, gvar)
                else:
                    raise ValueError(f"Unknown variable: {name}")
            elif isinstance(stmt.target, rast.Index):
                # Assignment to indexed location: arr[i] = val
                index = self._emit_expr(stmt.target.index)

                # Special handling for identifiers that are arrays
                if isinstance(stmt.target.expr, rast.Ident):
                    name = stmt.target.expr.name
                    if name in self.locals:
                        alloca, ty = self.locals[name]
                        if isinstance(ty, ir.ArrayType):
                            # Array type - use two-level GEP [0, index] on the alloca
                            zero = ir.Constant(self.i32, 0)
                            ptr = self.builder.gep(alloca, [zero, index])
                            val = self._convert_type(val, ty.element)
                            self.builder.store(val, ptr)
                            return None
                    elif name in self.globals:
                        gvar, ty = self.globals[name]
                        if isinstance(ty, ir.ArrayType):
                            # Global array - use two-level GEP [0, index] on the global
                            zero = ir.Constant(self.i32, 0)
                            ptr = self.builder.gep(gvar, [zero, index])
                            val = self._convert_type(val, ty.element)
                            self.builder.store(val, ptr)
                            return None

                # Special handling for struct field that is an array (e.g., buf.data[0] = val)
                if isinstance(stmt.target.expr, rast.Field):
                    field_addr = self._emit_lvalue_addr(stmt.target.expr)
                    if isinstance(field_addr.type, ir.PointerType):
                        pointee = field_addr.type.pointee
                        if isinstance(pointee, ir.ArrayType):
                            zero = ir.Constant(self.i32, 0)
                            ptr = self.builder.gep(field_addr, [zero, index])
                            val = self._convert_type(val, pointee.element)
                            self.builder.store(val, ptr)
                            return None

                # Special handling for nested array indexing (e.g., arr[i][j] = val)
                if isinstance(stmt.target.expr, rast.Index):
                    inner_addr = self._emit_lvalue_addr(stmt.target.expr)
                    if isinstance(inner_addr.type, ir.PointerType):
                        pointee = inner_addr.type.pointee
                        if isinstance(pointee, ir.ArrayType):
                            zero = ir.Constant(self.i32, 0)
                            ptr = self.builder.gep(inner_addr, [zero, index])
                            val = self._convert_type(val, pointee.element)
                            self.builder.store(val, ptr)
                            return None

                # Special handling for HashMapI64 indexed assignment: m[k] = v -> hashmap_i64_insert(&m, k, v)
                if isinstance(stmt.target.expr, rast.Ident):
                    name = stmt.target.expr.name
                    if name in self.ritz_types:
                        base_ritz_type = self.ritz_types[name]
                        if isinstance(base_ritz_type, rast.NamedType):
                            if base_ritz_type.name == 'HashMapI64':
                                fn_name = "hashmap_i64_insert"
                                if fn_name not in self.functions:
                                    raise ValueError(f"HashMapI64 indexed assignment requires {fn_name} to be defined")
                                fn, _ = self.functions[fn_name]
                                # Get pointer to hashmap
                                map_ptr = self._emit_lvalue_addr(stmt.target.expr)
                                # Ensure key is i64
                                if index.type != self.i64:
                                    index = self.builder.sext(index, self.i64)
                                # Ensure value is i64
                                if val.type != self.i64:
                                    val = self.builder.sext(val, self.i64)
                                self.builder.call(fn, [map_ptr, index, val])
                                return None

                # General case - pointer indexing
                base = self._emit_expr(stmt.target.expr)
                if isinstance(base.type, ir.PointerType):
                    ptr = self.builder.gep(base, [index])
                    val = self._convert_type(val, base.type.pointee)
                    self.builder.store(val, ptr)
                else:
                    raise ValueError(f"Cannot index type: {base.type}")
            elif isinstance(stmt.target, rast.UnaryOp) and stmt.target.op == '*':
                # Assignment to dereferenced pointer: *ptr = val
                ptr = self._emit_expr(stmt.target.operand)
                if isinstance(ptr.type, ir.PointerType):
                    val = self._convert_type(val, ptr.type.pointee)
                    self.builder.store(val, ptr)
                else:
                    raise ValueError(f"Cannot dereference non-pointer: {ptr.type}")
            elif isinstance(stmt.target, rast.Field):
                # Assignment to struct field: obj.field = val
                # First, try to get the value of the expression
                # If it's already a pointer to a struct, use it directly
                # Otherwise, try to get its address
                struct_val = self._emit_expr(stmt.target.expr)

                if isinstance(struct_val.type, ir.PointerType):
                    # Expression evaluates to a pointer - use it directly
                    pointee_type = struct_val.type.pointee
                    if isinstance(pointee_type, ir.BaseStructType):
                        struct_name = self._get_struct_name_from_type(pointee_type)
                        if struct_name:
                            idx = self._get_struct_field_index(struct_name, stmt.target.field)
                            _, field_type = self.struct_fields[struct_name][idx]
                            field_llvm_type = self._ritz_type_to_llvm(field_type)
                            field_ptr = self.builder.gep(struct_val, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                            val = self._convert_type(val, field_llvm_type)
                            self.builder.store(val, field_ptr)
                        else:
                            raise ValueError(f"Cannot determine struct type for field assignment")
                    elif isinstance(pointee_type, ir.PointerType) and isinstance(pointee_type.pointee, ir.BaseStructType):
                        # Double pointer (**Struct) - load once to get *Struct, then GEP
                        inner_ptr = self.builder.load(struct_val)
                        inner_pointee = pointee_type.pointee
                        struct_name = self._get_struct_name_from_type(inner_pointee)
                        if struct_name:
                            idx = self._get_struct_field_index(struct_name, stmt.target.field)
                            _, field_type = self.struct_fields[struct_name][idx]
                            field_llvm_type = self._ritz_type_to_llvm(field_type)
                            field_ptr = self.builder.gep(inner_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                            val = self._convert_type(val, field_llvm_type)
                            self.builder.store(val, field_ptr)
                        else:
                            raise ValueError(f"Cannot determine struct type for field assignment")
                    else:
                        raise ValueError(f"Cannot assign field on non-struct pointer: {pointee_type}")
                elif isinstance(struct_val.type, ir.BaseStructType):
                    # Value-type struct - need to get address from lvalue
                    struct_ptr = self._emit_lvalue_addr(stmt.target.expr)
                    struct_name = self._get_struct_name_from_type(struct_val.type)
                    if struct_name:
                        idx = self._get_struct_field_index(struct_name, stmt.target.field)
                        _, field_type = self.struct_fields[struct_name][idx]
                        field_llvm_type = self._ritz_type_to_llvm(field_type)
                        field_ptr = self.builder.gep(struct_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                        val = self._convert_type(val, field_llvm_type)
                        self.builder.store(val, field_ptr)
                    else:
                        raise ValueError(f"Cannot determine struct type for field assignment")
                else:
                    raise ValueError(f"Invalid type for field assignment: {struct_val.type}")
            else:
                raise NotImplementedError(f"Assignment to: {type(stmt.target)}")
            return None

        elif isinstance(stmt, rast.ExprStmt):
            # Check if this is an If expression used as statement
            if isinstance(stmt.expr, rast.If):
                return self._emit_if(stmt.expr)
            # Interpolated strings get desugared to print calls
            if isinstance(stmt.expr, rast.InterpString):
                return self._emit_interp_string_print(stmt.expr)
            return self._emit_expr(stmt.expr)

        elif isinstance(stmt, rast.WhileStmt):
            return self._emit_while(stmt)

        elif isinstance(stmt, rast.ForStmt):
            return self._emit_for(stmt)

        elif isinstance(stmt, rast.AssertStmt):
            return self._emit_assert(stmt)

        elif isinstance(stmt, rast.BreakStmt):
            if not self.loop_stack:
                raise RuntimeError("break statement outside of loop")
            _, break_block = self.loop_stack[-1]
            self.builder.branch(break_block)
            return True  # Terminates this block

        elif isinstance(stmt, rast.ContinueStmt):
            if not self.loop_stack:
                raise RuntimeError("continue statement outside of loop")
            continue_block, _ = self.loop_stack[-1]
            self.builder.branch(continue_block)
            return True  # Terminates this block

        elif isinstance(stmt, rast.AsmStmt):
            return self._emit_asm(stmt)

        elif isinstance(stmt, rast.UnsafeBlock):
            return self._emit_unsafe_block(stmt)

        else:
            raise NotImplementedError(f"Statement: {type(stmt)}")

    def _emit_interp_string_print(self, expr: rast.InterpString):
        """Emit print calls for an interpolated string.

        Desugars "x = {x}, y = {y}" to:
            prints("x = ")
            print_int(x)  # or appropriate print function based on type
            prints(", y = ")
            print_int(y)
        """
        for i, part in enumerate(expr.parts):
            # Print string literal part (if non-empty)
            if part:
                str_const = self._get_string_constant(part)
                ptr = self.builder.gep(str_const, [ir.Constant(self.i64, 0), ir.Constant(self.i64, 0)])
                self._emit_write_syscall(ir.Constant(self.i64, 1), ptr, ir.Constant(self.i64, len(part)))

            # Print expression (if not past the last part)
            if i < len(expr.exprs):
                value = self._emit_expr(expr.exprs[i])
                self._emit_print_value(value, expr.exprs[i])

        # Return the byte count of the last write (or 0 if no parts)
        return ir.Constant(self.i64, 0)

    def _emit_print_value(self, value: ir.Value, expr: rast.Expr):
        """Emit code to print a value based on its type.

        Handles: integers, pointers (as strings), booleans.
        Always uses inline printing (syscalls) for self-contained output.
        """
        ty = value.type

        # Integer types - print using inline itoa + write
        if ty in (self.i8, self.i16, self.i32, self.i64):
            # Extend to i64 if needed
            if ty != self.i64:
                value = self.builder.sext(value, self.i64)
            self._emit_print_int_inline(value)

        # Pointer types (assume *u8 = string) - use strlen + write
        elif isinstance(ty, ir.PointerType):
            self._emit_write_str(value)

        # Boolean - print "true" or "false"
        elif ty == self.i1:
            true_str = self._get_string_constant("true")
            false_str = self._get_string_constant("false")
            true_ptr = self.builder.gep(true_str, [ir.Constant(self.i64, 0), ir.Constant(self.i64, 0)])
            false_ptr = self.builder.gep(false_str, [ir.Constant(self.i64, 0), ir.Constant(self.i64, 0)])
            ptr = self.builder.select(value, true_ptr, false_ptr)
            length = self.builder.select(value, ir.Constant(self.i64, 4), ir.Constant(self.i64, 5))
            self._emit_write_syscall(ir.Constant(self.i64, 1), ptr, length)

        else:
            # For other types, try to print as integer
            if hasattr(ty, 'width'):
                value = self.builder.zext(value, self.i64) if ty.width < 64 else value
                self._emit_print_int_inline(value)
            else:
                raise ValueError(f"Cannot print value of type {ty}")

    def _emit_print_int_inline(self, value: ir.Value):
        """Inline integer printing using itoa and write syscall.

        Algorithm: Extract digits in reverse order, store in buffer from end,
        then write the filled portion of the buffer.
        """
        # Allocate buffer at end of 21-byte array and work backwards
        buf = self.builder.alloca(ir.ArrayType(self.i8, 21))
        buf_start = self.builder.gep(buf, [ir.Constant(self.i64, 0), ir.Constant(self.i64, 0)])
        buf_end = self.builder.gep(buf, [ir.Constant(self.i64, 0), ir.Constant(self.i64, 20)])

        # Working pointer (starts at end, moves backwards)
        ptr_ptr = self.builder.alloca(self.i8.as_pointer())
        self.builder.store(buf_end, ptr_ptr)

        val_ptr = self.builder.alloca(self.i64)
        self.builder.store(value, val_ptr)

        # Check if negative
        is_neg = self.builder.icmp_signed('<', value, ir.Constant(self.i64, 0))
        neg_block = self.current_fn.append_basic_block("print_int.neg")
        check_zero = self.current_fn.append_basic_block("print_int.check_zero")
        self.builder.cbranch(is_neg, neg_block, check_zero)

        # Negative: negate value (we'll add '-' at the end)
        self.builder.position_at_end(neg_block)
        neg_val = self.builder.sub(ir.Constant(self.i64, 0), self.builder.load(val_ptr))
        self.builder.store(neg_val, val_ptr)
        self.builder.branch(check_zero)

        # Check for zero special case
        self.builder.position_at_end(check_zero)
        curr_val = self.builder.load(val_ptr)
        is_zero_val = self.builder.icmp_signed('==', curr_val, ir.Constant(self.i64, 0))
        zero_block = self.current_fn.append_basic_block("print_int.zero")
        digit_loop = self.current_fn.append_basic_block("print_int.digits")
        self.builder.cbranch(is_zero_val, zero_block, digit_loop)

        # Zero: just store '0'
        self.builder.position_at_end(zero_block)
        curr_ptr = self.builder.load(ptr_ptr)
        new_ptr = self.builder.gep(curr_ptr, [ir.Constant(self.i64, -1)])
        self.builder.store(ir.Constant(self.i8, ord('0')), new_ptr)
        self.builder.store(new_ptr, ptr_ptr)
        write_block = self.current_fn.append_basic_block("print_int.write")
        self.builder.branch(write_block)

        # Extract digits in reverse
        self.builder.position_at_end(digit_loop)
        val = self.builder.load(val_ptr)
        val_done = self.builder.icmp_signed('==', val, ir.Constant(self.i64, 0))
        digit_done = self.current_fn.append_basic_block("print_int.digit_done")
        digit_body = self.current_fn.append_basic_block("print_int.digit_body")
        self.builder.cbranch(val_done, digit_done, digit_body)

        # Store one digit
        self.builder.position_at_end(digit_body)
        digit = self.builder.srem(self.builder.load(val_ptr), ir.Constant(self.i64, 10))
        char_val = self.builder.add(digit, ir.Constant(self.i64, ord('0')))
        char_byte = self.builder.trunc(char_val, self.i8)

        curr_ptr2 = self.builder.load(ptr_ptr)
        new_ptr2 = self.builder.gep(curr_ptr2, [ir.Constant(self.i64, -1)])
        self.builder.store(char_byte, new_ptr2)
        self.builder.store(new_ptr2, ptr_ptr)

        new_val = self.builder.sdiv(self.builder.load(val_ptr), ir.Constant(self.i64, 10))
        self.builder.store(new_val, val_ptr)
        self.builder.branch(digit_loop)

        # Add minus sign if negative
        self.builder.position_at_end(digit_done)
        add_minus = self.current_fn.append_basic_block("print_int.minus")
        skip_minus = self.current_fn.append_basic_block("print_int.skip_minus")
        self.builder.cbranch(is_neg, add_minus, skip_minus)

        self.builder.position_at_end(add_minus)
        curr_ptr3 = self.builder.load(ptr_ptr)
        new_ptr3 = self.builder.gep(curr_ptr3, [ir.Constant(self.i64, -1)])
        self.builder.store(ir.Constant(self.i8, ord('-')), new_ptr3)
        self.builder.store(new_ptr3, ptr_ptr)
        self.builder.branch(skip_minus)

        self.builder.position_at_end(skip_minus)
        self.builder.branch(write_block)

        # Write the result
        self.builder.position_at_end(write_block)
        final_ptr = self.builder.load(ptr_ptr)
        # Length = buf_end - final_ptr
        ptr_int = self.builder.ptrtoint(final_ptr, self.i64)
        end_int = self.builder.ptrtoint(buf_end, self.i64)
        length = self.builder.sub(end_int, ptr_int)
        self._emit_write_syscall(ir.Constant(self.i64, 1), final_ptr, length)

        done_block = self.current_fn.append_basic_block("print_int.done")
        self.builder.branch(done_block)
        self.builder.position_at_end(done_block)

    def _emit_write_str(self, ptr: ir.Value):
        """Write a null-terminated string using strlen + write."""
        # Calculate length with loop
        len_loop = self.current_fn.append_basic_block("strlen.loop")
        len_body = self.current_fn.append_basic_block("strlen.body")
        len_done = self.current_fn.append_basic_block("strlen.done")

        # Initialize length counter
        len_ptr = self.builder.alloca(self.i64)
        self.builder.store(ir.Constant(self.i64, 0), len_ptr)
        self.builder.branch(len_loop)

        # Loop check: while *(ptr + len) != 0
        self.builder.position_at_end(len_loop)
        curr_len = self.builder.load(len_ptr)
        char_ptr = self.builder.gep(ptr, [curr_len])
        char_val = self.builder.load(char_ptr)
        is_zero = self.builder.icmp_unsigned('==', char_val, ir.Constant(self.i8, 0))
        self.builder.cbranch(is_zero, len_done, len_body)

        # Loop body: increment and continue
        self.builder.position_at_end(len_body)
        curr_len2 = self.builder.load(len_ptr)
        new_len = self.builder.add(curr_len2, ir.Constant(self.i64, 1))
        self.builder.store(new_len, len_ptr)
        self.builder.branch(len_loop)

        # Done: call write
        self.builder.position_at_end(len_done)
        final_len = self.builder.load(len_ptr)
        self._emit_write_syscall(ir.Constant(self.i64, 1), ptr, final_len)

    def _emit_unsafe_block(self, stmt: rast.UnsafeBlock):
        """Emit an unsafe block.

        Unsafe blocks allow raw pointer operations that would otherwise be
        forbidden. The in_unsafe flag tracks whether we're in such a block.

        Syntax:
            unsafe
                *ptr = value    # Raw pointer deref (write)
                let x = *ptr    # Raw pointer deref (read)
                ptr.cast::<T>() # Raw pointer cast
        """
        # Save previous unsafe state (for nested unsafe blocks)
        prev_unsafe = self.in_unsafe
        self.in_unsafe = True

        try:
            # Emit body statements
            for body_stmt in stmt.body.stmts:
                if self._emit_stmt(body_stmt):
                    break  # Block terminated (return/break/continue)
        finally:
            # Restore previous state
            self.in_unsafe = prev_unsafe

        return False  # Unsafe block doesn't terminate control flow

    def _emit_asm(self, stmt: rast.AsmStmt):
        """Emit inline assembly using LLVM inline asm.

        Converts Ritz inline assembly syntax to LLVM IR inline asm.

        Supports both input and output operands. Output operands are detected
        by analyzing the assembly template for write patterns (e.g., mov to operand).

        Example Ritz (input only):
            asm x86_64:
                movw {port}, %dx
                outb %al, %dx

        Example Ritz (with output):
            asm x86_64:
                movw {port}, %dx
                inb %dx, %al
                movb %al, {result}

        For outputs, the value is returned from the asm and stored back.
        """
        import re

        template = stmt.template

        # Detect which operands are outputs by analyzing the template.
        # In AT&T syntax, the destination is the LAST operand of mov/store instructions.
        # Pattern: movX <src>, {operand} means {operand} is an output
        output_operands = set()
        for operand in stmt.operands:
            # Check for patterns where this operand is a destination
            # AT&T syntax: instruction source, destination
            patterns = [
                rf'mov[bwlq]?\s+[^,]+,\s*\{{{operand.name}\}}',  # movb %al, {result}
                rf'xchg[bwlq]?\s+[^,]+,\s*\{{{operand.name}\}}',  # xchg
                rf'lea[bwlq]?\s+[^,]+,\s*\{{{operand.name}\}}',  # lea
                rf'pop[bwlq]?\s+\{{{operand.name}\}}',  # pop {result}
                rf'in[bwl]?\s+[^,]*,?\s*\{{{operand.name}\}}',  # in %dx, {result}
            ]
            for pattern in patterns:
                if re.search(pattern, template, re.IGNORECASE):
                    output_operands.add(operand.name)
                    break

        # Separate outputs and inputs for LLVM constraint ordering
        # LLVM requires outputs first, then inputs, in the constraint string
        outputs = []
        inputs = []
        output_addrs = {}  # Map operand name -> LLVM address to store result

        for operand in stmt.operands:
            if operand.name in output_operands:
                outputs.append(operand)
                # For outputs, we need the address to store to, not the value
                # The operand.expr should be an Ident referencing a variable
                if isinstance(operand.expr, rast.Ident):
                    var_name = operand.expr.name
                    if var_name in self.locals:
                        output_addrs[operand.name], _ = self.locals[var_name]
                    elif var_name in self.globals:
                        output_addrs[operand.name], _ = self.globals[var_name]
                    else:
                        raise ValueError(f"Unknown variable for asm output: {var_name}")
                else:
                    raise ValueError(f"Asm output operand must be a variable, got: {type(operand.expr)}")
            else:
                inputs.append(operand)

        # Build constraint string and operand lists
        # Outputs come first in both the constraint string and operand lists
        constraints = []
        input_values = []
        output_types = []
        operand_map = {}  # Maps {name} -> $N

        # Add output constraints first (=r for each output)
        for i, operand in enumerate(outputs):
            operand_map[operand.name] = f"${i}"
            constraints.append("=r")
            # Get the type for the output
            addr = output_addrs[operand.name]
            if isinstance(addr.type, ir.PointerType):
                output_types.append(addr.type.pointee)
            else:
                output_types.append(addr.type)

        # Then add input constraints
        for i, operand in enumerate(inputs):
            operand_map[operand.name] = f"${len(outputs) + i}"
            # Emit the operand expression to get its value
            val = self._emit_expr(operand.expr)
            input_values.append(val)
            # Input constraint based on type
            ty = val.type
            if ty in (self.i8, self.i16, self.i32, self.i64):
                constraints.append("r")
            elif isinstance(ty, ir.PointerType):
                constraints.append("r")
            else:
                constraints.append("r")

        # Replace {name} with $N in template
        # First, escape literal $ for LLVM
        template_escaped = template.replace('$', '$$')

        # Now replace {name} with temporary markers
        operand_markers = {}
        def replace_with_marker(match):
            name = match.group(1)
            if name in operand_map:
                idx = operand_map[name]
                marker = f'\x00{idx[1:]}\x00'
                operand_markers[marker] = idx
                return marker
            else:
                raise ValueError(f"Unknown asm operand: {{{name}}}")

        llvm_template = re.sub(r'\{(\w+)\}', replace_with_marker, template_escaped)

        # Replace markers back to $N
        for marker, idx in operand_markers.items():
            llvm_template = llvm_template.replace(marker, idx)

        llvm_template = llvm_template.replace('\n', '\\0A')

        # Auto-detect register clobbers from the template
        x86_64_regs = {
            'rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp', 'rsp',
            'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15',
            'eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'esp',
            'ax', 'bx', 'cx', 'dx', 'si', 'di', 'bp', 'sp',
            'al', 'ah', 'bl', 'bh', 'cl', 'ch', 'dl', 'dh',
            'sil', 'dil', 'bpl', 'spl',
        }

        detected_clobbers = set()
        template_lower = template.lower()
        for reg in x86_64_regs:
            if re.search(rf'\b{reg}\b', template_lower):
                reg_map = {
                    'eax': 'rax', 'ax': 'rax', 'al': 'rax', 'ah': 'rax',
                    'ebx': 'rbx', 'bx': 'rbx', 'bl': 'rbx', 'bh': 'rbx',
                    'ecx': 'rcx', 'cx': 'rcx', 'cl': 'rcx', 'ch': 'rcx',
                    'edx': 'rdx', 'dx': 'rdx', 'dl': 'rdx', 'dh': 'rdx',
                    'esi': 'rsi', 'si': 'rsi', 'sil': 'rsi',
                    'edi': 'rdi', 'di': 'rdi', 'dil': 'rdi',
                    'ebp': 'rbp', 'bp': 'rbp', 'bpl': 'rbp',
                    'esp': 'rsp', 'sp': 'rsp', 'spl': 'rsp',
                }
                canonical = reg_map.get(reg, reg)
                detected_clobbers.add(canonical)

        if stmt.clobbers:
            for clobber in stmt.clobbers:
                detected_clobbers.add(clobber)

        for clobber in sorted(detected_clobbers):
            constraints.append(f"~{{{clobber}}}")

        if stmt.volatile:
            constraints.append("~{memory}")

        constraint_str = ','.join(constraints) if constraints else ""

        # Determine return type based on outputs
        if len(outputs) == 0:
            ret_type = self.void
        elif len(outputs) == 1:
            ret_type = output_types[0]
        else:
            # Multiple outputs -> return a struct
            ret_type = ir.LiteralStructType(output_types)

        # Build function type
        if input_values:
            param_types = [v.type for v in input_values]
            asm_fn_type = ir.FunctionType(ret_type, param_types)
        else:
            asm_fn_type = ir.FunctionType(ret_type, [])

        # Create inline asm value
        asm_val = ir.InlineAsm(
            asm_fn_type,
            llvm_template,
            constraint_str,
            side_effect=stmt.volatile
        )

        # Call the inline asm
        if input_values:
            result = self.builder.call(asm_val, input_values)
        else:
            result = self.builder.call(asm_val, [])

        # Store output values back to variables
        if len(outputs) == 1:
            addr = output_addrs[outputs[0].name]
            self.builder.store(result, addr)
        elif len(outputs) > 1:
            for i, operand in enumerate(outputs):
                val = self.builder.extract_value(result, i)
                addr = output_addrs[operand.name]
                self.builder.store(val, addr)

        return None

    def _emit_short_circuit_and(self, expr: rast.BinOp):
        """Emit short-circuit AND: left && right.

        Evaluates left first. If left is false, returns false without
        evaluating right. Only evaluates right if left is true.
        """
        # Evaluate left operand
        left = self._emit_expr(expr.left)

        # Convert to i1 if needed
        if left.type != self.i1:
            left_bool = self.builder.icmp_signed('!=', left, ir.Constant(left.type, 0))
        else:
            left_bool = left

        # Create blocks
        eval_right_block = self.current_fn.append_basic_block("and.right")
        merge_block = self.current_fn.append_basic_block("and.merge")

        # Remember entry block for phi
        entry_block = self.builder.block

        # If left is false, short-circuit to merge (result is false)
        # If left is true, evaluate right
        self.builder.cbranch(left_bool, eval_right_block, merge_block)

        # Evaluate right operand
        self.builder.position_at_end(eval_right_block)
        right = self._emit_expr(expr.right)

        # Convert to i1 if needed
        if right.type != self.i1:
            right_bool = self.builder.icmp_signed('!=', right, ir.Constant(right.type, 0))
        else:
            right_bool = right

        right_exit_block = self.builder.block
        self.builder.branch(merge_block)

        # Merge block with phi node
        self.builder.position_at_end(merge_block)
        result = self.builder.phi(self.i1)
        result.add_incoming(ir.Constant(self.i1, 0), entry_block)  # false from short-circuit
        result.add_incoming(right_bool, right_exit_block)          # right result if evaluated

        return result

    def _emit_short_circuit_or(self, expr: rast.BinOp):
        """Emit short-circuit OR: left || right.

        Evaluates left first. If left is true, returns true without
        evaluating right. Only evaluates right if left is false.
        """
        # Evaluate left operand
        left = self._emit_expr(expr.left)

        # Convert to i1 if needed
        if left.type != self.i1:
            left_bool = self.builder.icmp_signed('!=', left, ir.Constant(left.type, 0))
        else:
            left_bool = left

        # Create blocks
        eval_right_block = self.current_fn.append_basic_block("or.right")
        merge_block = self.current_fn.append_basic_block("or.merge")

        # Remember entry block for phi
        entry_block = self.builder.block

        # If left is true, short-circuit to merge (result is true)
        # If left is false, evaluate right
        self.builder.cbranch(left_bool, merge_block, eval_right_block)

        # Evaluate right operand
        self.builder.position_at_end(eval_right_block)
        right = self._emit_expr(expr.right)

        # Convert to i1 if needed
        if right.type != self.i1:
            right_bool = self.builder.icmp_signed('!=', right, ir.Constant(right.type, 0))
        else:
            right_bool = right

        right_exit_block = self.builder.block
        self.builder.branch(merge_block)

        # Merge block with phi node
        self.builder.position_at_end(merge_block)
        result = self.builder.phi(self.i1)
        result.add_incoming(ir.Constant(self.i1, 1), entry_block)  # true from short-circuit
        result.add_incoming(right_bool, right_exit_block)          # right result if evaluated

        return result

    def _emit_if(self, if_expr: rast.If):
        """Emit an if expression/statement. Returns phi value if if-expr has value, else None."""
        cond = self._emit_expr(if_expr.cond)

        # Ensure condition is i1
        if cond.type != self.i1:
            cond = self.builder.icmp_signed('!=', cond, ir.Constant(cond.type, 0))

        # Create blocks
        then_block = self.current_fn.append_basic_block("if.then")
        else_block = self.current_fn.append_basic_block("if.else") if if_expr.else_block else None
        end_block = self.current_fn.append_basic_block("if.end")

        # Branch
        if else_block:
            self.builder.cbranch(cond, then_block, else_block)
        else:
            self.builder.cbranch(cond, then_block, end_block)

        # Then block
        self.builder.position_at_end(then_block)
        saved_returned = self.has_returned
        self.has_returned = False

        for s in if_expr.then_block.stmts:
            result = self._emit_stmt(s)
            if result is True:
                break

        # Handle trailing expression in then block - capture value for phi
        then_value = None
        if not self.builder.block.is_terminated and if_expr.then_block.expr:
            if isinstance(if_expr.then_block.expr, rast.If):
                then_value = self._emit_if(if_expr.then_block.expr)
            else:
                then_value = self._emit_expr(if_expr.then_block.expr)

        # DON'T branch yet - we may need to add type conversion first
        then_exit_block = self.builder.block  # Remember where we are after then block
        then_terminated = self.builder.block.is_terminated
        then_returned = self.has_returned

        # Else block
        else_value = None
        else_exit_block = None
        else_returned = False
        if if_expr.else_block:
            self.builder.position_at_end(else_block)
            self.has_returned = False

            for s in if_expr.else_block.stmts:
                result = self._emit_stmt(s)
                if result is True:
                    break

            # Handle trailing expression in else block - capture value for phi
            if not self.builder.block.is_terminated and if_expr.else_block.expr:
                if isinstance(if_expr.else_block.expr, rast.If):
                    else_value = self._emit_if(if_expr.else_block.expr)
                else:
                    else_value = self._emit_expr(if_expr.else_block.expr)

            # DON'T branch yet
            else_exit_block = self.builder.block  # Remember where we are after else block
            else_terminated = self.builder.block.is_terminated
            else_returned = self.has_returned

        # If both branches have values with different types, convert BEFORE branching
        target_type = None
        if then_value is not None and else_value is not None:
            if then_value.type != else_value.type:
                # Pick the larger type
                if self._type_size(else_value.type) > self._type_size(then_value.type):
                    target_type = else_value.type
                else:
                    target_type = then_value.type

                # Convert then value if needed (while still in else block, go back to then)
                if then_value.type != target_type and not then_terminated:
                    self.builder.position_at_end(then_exit_block)
                    then_value = self._convert_type(then_value, target_type)
                    then_exit_block = self.builder.block

                # Convert else value if needed
                if else_value.type != target_type and not else_terminated:
                    self.builder.position_at_end(else_exit_block)
                    else_value = self._convert_type(else_value, target_type)
                    else_exit_block = self.builder.block
            else:
                # Types are already the same
                target_type = then_value.type

        # NOW add the branches
        if not then_terminated:
            self.builder.position_at_end(then_exit_block)
            self.builder.branch(end_block)

        if else_exit_block and not else_terminated:
            self.builder.position_at_end(else_exit_block)
            self.builder.branch(end_block)

        # Position at end block
        self.builder.position_at_end(end_block)

        # Restore has_returned
        self.has_returned = saved_returned or (then_returned and else_returned)

        # Create phi node if both branches have values
        if then_value is not None and else_value is not None:
            phi = self.builder.phi(then_value.type)  # Types should match now after conversion
            phi.add_incoming(then_value, then_exit_block)
            phi.add_incoming(else_value, else_exit_block)
            return phi

        return None

    def _emit_while(self, stmt: rast.WhileStmt) -> None:
        """Emit a while loop."""
        cond_block = self.current_fn.append_basic_block("while.cond")
        body_block = self.current_fn.append_basic_block("while.body")
        end_block = self.current_fn.append_basic_block("while.end")

        # Push loop context for break/continue
        self.loop_stack.append((cond_block, end_block))

        # Jump to condition
        self.builder.branch(cond_block)

        # Condition
        self.builder.position_at_end(cond_block)
        cond = self._emit_expr(stmt.cond)
        if cond.type != self.i1:
            cond = self.builder.icmp_signed('!=', cond, ir.Constant(cond.type, 0))
        self.builder.cbranch(cond, body_block, end_block)

        # Body
        self.builder.position_at_end(body_block)
        saved_returned = self.has_returned
        self.has_returned = False

        for s in stmt.body.stmts:
            result = self._emit_stmt(s)
            if result is True:
                break

        # Handle trailing expression in while body (if any)
        if not self.builder.block.is_terminated and stmt.body.expr:
            if isinstance(stmt.body.expr, rast.If):
                self._emit_if(stmt.body.expr)
            else:
                self._emit_expr(stmt.body.expr)

        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)

        self.has_returned = saved_returned

        # Pop loop context
        self.loop_stack.pop()

        # End
        self.builder.position_at_end(end_block)
        return None

    def _emit_for(self, stmt: rast.ForStmt) -> None:
        """Emit a for loop.

        Desugars `for x in start..end` to:
            var x = start
            while x < end:   # (or <= for inclusive)
                body
                x = x + 1
        """
        # For now, only support Range expressions
        if not isinstance(stmt.iter, rast.Range):
            raise NotImplementedError(f"for loop only supports range expressions, got {type(stmt.iter)}")

        range_expr = stmt.iter
        if range_expr.start is None or range_expr.end is None:
            raise NotImplementedError("for loop requires both start and end in range")

        # Emit start and end values
        start_val = self._emit_expr(range_expr.start)
        end_val = self._emit_expr(range_expr.end)

        # Determine the type of the loop variable
        # If start is 0 (default i64) but end is a different int type, use end's type
        # This handles common case: for i in 0..count where count is i32
        loop_ty = start_val.type
        if start_val.type != end_val.type:
            # Prefer the end type if start is just a constant 0
            if isinstance(range_expr.start, rast.IntLit) and range_expr.start.value == 0:
                loop_ty = end_val.type
                start_val = ir.Constant(loop_ty, 0)
            else:
                # Otherwise, widen to the larger type
                if self._type_size(start_val.type) > self._type_size(end_val.type):
                    loop_ty = start_val.type
                    if self._is_signed_type(end_val.type):
                        end_val = self.builder.sext(end_val, loop_ty)
                    else:
                        end_val = self.builder.zext(end_val, loop_ty)
                else:
                    loop_ty = end_val.type
                    if self._is_signed_type(start_val.type):
                        start_val = self.builder.sext(start_val, loop_ty)
                    else:
                        start_val = self.builder.zext(start_val, loop_ty)

        # Create the loop variable (allocate in entry block to prevent stack leaks in nested loops)
        loop_var = self._alloca_in_entry_block(loop_ty, stmt.var)
        self.builder.store(start_val, loop_var)

        # Add to local vars scope
        self.locals[stmt.var] = (loop_var, loop_ty)

        # Create basic blocks
        cond_block = self.current_fn.append_basic_block("for.cond")
        body_block = self.current_fn.append_basic_block("for.body")
        incr_block = self.current_fn.append_basic_block("for.incr")
        end_block = self.current_fn.append_basic_block("for.end")

        # Push loop context for break/continue
        # continue goes to increment block, break goes to end block
        self.loop_stack.append((incr_block, end_block))

        # Jump to condition
        self.builder.branch(cond_block)

        # Condition block
        self.builder.position_at_end(cond_block)
        current_val = self.builder.load(loop_var)

        # Compare: x < end (or x <= end for inclusive)
        if range_expr.inclusive:
            cmp_op = '<=' if self._is_signed_type(loop_ty) else '<='
            if self._is_signed_type(loop_ty):
                cond = self.builder.icmp_signed('<=', current_val, end_val)
            else:
                cond = self.builder.icmp_unsigned('<=', current_val, end_val)
        else:
            if self._is_signed_type(loop_ty):
                cond = self.builder.icmp_signed('<', current_val, end_val)
            else:
                cond = self.builder.icmp_unsigned('<', current_val, end_val)

        self.builder.cbranch(cond, body_block, end_block)

        # Body block
        self.builder.position_at_end(body_block)
        saved_returned = self.has_returned
        self.has_returned = False

        for s in stmt.body.stmts:
            result = self._emit_stmt(s)
            if result is True:
                break

        # Handle trailing expression in for body (if any)
        if not self.builder.block.is_terminated and stmt.body.expr:
            if isinstance(stmt.body.expr, rast.If):
                self._emit_if(stmt.body.expr)
            else:
                self._emit_expr(stmt.body.expr)

        # Jump to increment if not terminated
        if not self.builder.block.is_terminated:
            self.builder.branch(incr_block)

        self.has_returned = saved_returned

        # Increment block
        self.builder.position_at_end(incr_block)
        current_val = self.builder.load(loop_var)
        incremented = self.builder.add(current_val, ir.Constant(loop_ty, 1))
        self.builder.store(incremented, loop_var)
        self.builder.branch(cond_block)

        # Pop loop context
        self.loop_stack.pop()

        # End block
        self.builder.position_at_end(end_block)
        return None

    def _is_signed_type(self, ty) -> bool:
        """Check if an LLVM integer type should be treated as signed."""
        # i8, i16, i32, i64 are signed by convention in Ritz
        # u8, u16, u32, u64 would be unsigned, but in LLVM they're all just IntType
        # We need to track this from the source type, but for now assume i* types are signed
        # This is a simplification - proper tracking would require carrying type info
        return True  # Default to signed comparisons for now

    def _emit_assert(self, stmt: rast.AssertStmt) -> None:
        """Emit an assert statement (only valid in test functions)."""
        # Enforce assert only in @test functions
        if not self.in_test_fn:
            fn_name = self.current_fn_def.name if self.current_fn_def else "unknown"
            raise ValueError(f"assert is only allowed in @test functions, not in '{fn_name}'")

        # Emit the condition
        cond = self._emit_expr(stmt.condition)

        # Ensure condition is i1
        if cond.type != self.i1:
            cond = self.builder.icmp_signed('!=', cond, ir.Constant(cond.type, 0))

        # Create blocks
        pass_block = self.current_fn.append_basic_block("assert.pass")
        fail_block = self.current_fn.append_basic_block("assert.fail")

        # Branch based on condition
        self.builder.cbranch(cond, pass_block, fail_block)

        # Fail block: exit(1) via syscall
        self.builder.position_at_end(fail_block)
        # syscall 60 = exit on x86_64
        exit_code = ir.Constant(self.i64, 1)
        asm_str = "syscall"
        constraints = "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"
        asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64])
        asm_ir = ir.InlineAsm(asm_func_ty, asm_str, constraints, side_effect=True)
        self.builder.call(asm_ir, [ir.Constant(self.i64, 60), exit_code])
        self.builder.unreachable()

        # Pass block: continue
        self.builder.position_at_end(pass_block)
        return None

    def _emit_expr(self, expr: rast.Expr) -> ir.Value:
        """Emit an expression."""
        if isinstance(expr, rast.IntLit):
            return ir.Constant(self.i64, expr.value)

        elif isinstance(expr, rast.FloatLit):
            return ir.Constant(self.f64, expr.value)

        elif isinstance(expr, rast.BoolLit):
            return ir.Constant(self.i1, 1 if expr.value else 0)

        elif isinstance(expr, rast.StringLit):
            # "hello" -> StrView (zero-copy view)
            return self._emit_strview_string_literal(expr)

        elif isinstance(expr, rast.CStringLit):
            # C-string literal: c"hello" -> *u8 (null-terminated)
            gvar = self._get_string_constant(expr.value)
            # Get pointer to first element
            zero = ir.Constant(self.i64, 0)
            return self.builder.gep(gvar, [zero, zero])

        elif isinstance(expr, rast.SpanStringLit):
            # Span string literal: s"hello" -> Span<u8> { ptr, len }
            return self._emit_span_string_literal(expr)

        elif isinstance(expr, rast.InterpString):
            # Interpolated strings are currently only supported as expression statements
            # where they get desugared to print calls. When used as a value, error.
            raise ValueError(f"Interpolated strings cannot be used as values (line {expr.span.line}). "
                           "Use them as expression statements for printing, or build a String manually.")

        elif isinstance(expr, rast.CharLit):
            # Character literal is a u8 constant
            return ir.Constant(self.i8, expr.value)

        elif isinstance(expr, rast.NullLit):
            # Null pointer literal - type must be inferred from context
            # Default to *u8 (i8*) which is compatible with most pointer casts
            return ir.Constant(self.i8.as_pointer(), None)

        elif isinstance(expr, rast.Ident):
            name = expr.name

            # Check constants
            if name in self.constants:
                val, ty = self.constants[name]
                return ir.Constant(ty, val)

            # Check locals (var bindings) FIRST - mutable vars shadow let bindings
            # This is critical because the same name may appear as both 'var' and 'let'
            # in different branches of if-else, and we need to use the correct one.
            if name in self.locals:
                alloca, ty = self.locals[name]
                return self.builder.load(alloca)

            # Check params (let bindings and function params)
            if name in self.params:
                val, _ = self.params[name]
                return val

            # Check module-level globals (var at top level)
            if name in self.globals:
                gvar, ty = self.globals[name]
                return self.builder.load(gvar)

            # Handle nil keyword (null pointer literal)
            if name == "nil":
                # Return a null pointer of i8* type
                return ir.Constant(ir.IntType(8).as_pointer(), None)

            # Check if this is a unit variant (enum variant without parentheses)
            if name in self.variant_to_enum:
                # Get the variant and check if it's a unit variant (no fields)
                enum_name = self.variant_to_enum[name]
                variant = self._get_enum_variant(enum_name, name)
                if not variant.fields:
                    # Unit variant - construct it with no args
                    return self._emit_enum_variant_constructor(name, [])

            # Check if this is a function name - return function pointer
            if name in self.functions:
                fn, fn_def = self.functions[name]
                # Return the function as a pointer value
                return fn

            raise ValueError(f"Unknown identifier: {name}")

        elif isinstance(expr, rast.BinOp):
            op = expr.op

            # Handle short-circuit operators BEFORE evaluating right operand
            if op in ('&&', 'and'):
                return self._emit_short_circuit_and(expr)
            elif op in ('||', 'or'):
                return self._emit_short_circuit_or(expr)

            left = self._emit_expr(expr.left)
            right = self._emit_expr(expr.right)

            # Ensure same type
            if left.type != right.type:
                if isinstance(left.type, ir.IntType) and isinstance(right.type, ir.IntType):
                    # Determine signedness for proper extension
                    left_unsigned = self._infer_unsigned_expr(expr.left)
                    right_unsigned = self._infer_unsigned_expr(expr.right)

                    if left.type.width < right.type.width:
                        # Use zext for i1 (boolean) or unsigned types
                        if left.type.width == 1 or left_unsigned:
                            left = self.builder.zext(left, right.type)
                        else:
                            left = self.builder.sext(left, right.type)
                    else:
                        if right.type.width == 1 or right_unsigned:
                            right = self.builder.zext(right, left.type)
                        else:
                            right = self.builder.sext(right, left.type)

            op = expr.op

            # Handle pointer comparison with integer 0 (null pointer check)
            # Only for comparison operators, not arithmetic
            if op in ('==', '!=', '<', '<=', '>', '>='):
                if isinstance(left.type, ir.PointerType) and isinstance(right.type, ir.IntType):
                    # Convert integer 0 to null pointer for comparison
                    if isinstance(expr.right, rast.IntLit) and expr.right.value == 0:
                        right = ir.Constant(left.type, None)  # null pointer
                elif isinstance(right.type, ir.PointerType) and isinstance(left.type, ir.IntType):
                    # Convert integer 0 to null pointer for comparison
                    if isinstance(expr.left, rast.IntLit) and expr.left.value == 0:
                        left = ir.Constant(right.type, None)  # null pointer

            # Check if this is a floating-point operation
            is_float = self._is_float_type(left.type) or self._is_float_type(right.type)

            if op == '+':
                # Handle pointer arithmetic: ptr + int -> GEP
                if isinstance(left.type, ir.PointerType) and isinstance(right.type, ir.IntType):
                    return self.builder.gep(left, [right])
                elif isinstance(right.type, ir.PointerType) and isinstance(left.type, ir.IntType):
                    return self.builder.gep(right, [left])
                if is_float:
                    return self.builder.fadd(left, right)
                return self.builder.add(left, right)
            elif op == '-':
                # Handle pointer arithmetic: ptr - int -> GEP with negated offset
                if isinstance(left.type, ir.PointerType) and isinstance(right.type, ir.IntType):
                    neg_right = self.builder.neg(right)
                    return self.builder.gep(left, [neg_right])
                if is_float:
                    return self.builder.fsub(left, right)
                return self.builder.sub(left, right)
            elif op == '*':
                if is_float:
                    return self.builder.fmul(left, right)
                return self.builder.mul(left, right)
            elif op == '/':
                if is_float:
                    return self.builder.fdiv(left, right)
                # Use unsigned division for unsigned types
                if self._infer_unsigned_expr(expr.left) or self._infer_unsigned_expr(expr.right):
                    return self.builder.udiv(left, right)
                return self.builder.sdiv(left, right)
            elif op == '%':
                if is_float:
                    return self.builder.frem(left, right)
                # Use unsigned remainder for unsigned types
                if self._infer_unsigned_expr(expr.left) or self._infer_unsigned_expr(expr.right):
                    return self.builder.urem(left, right)
                return self.builder.srem(left, right)
            elif op == '==':
                if is_float:
                    return self.builder.fcmp_ordered('==', left, right)
                # Equality is sign-agnostic
                return self.builder.icmp_signed('==', left, right)
            elif op == '!=':
                if is_float:
                    return self.builder.fcmp_ordered('!=', left, right)
                # Inequality is sign-agnostic
                return self.builder.icmp_signed('!=', left, right)
            elif op == '<':
                if is_float:
                    return self.builder.fcmp_ordered('<', left, right)
                # Use unsigned comparison for unsigned types
                if self._infer_unsigned_expr(expr.left) or self._infer_unsigned_expr(expr.right):
                    return self.builder.icmp_unsigned('<', left, right)
                return self.builder.icmp_signed('<', left, right)
            elif op == '<=':
                if is_float:
                    return self.builder.fcmp_ordered('<=', left, right)
                if self._infer_unsigned_expr(expr.left) or self._infer_unsigned_expr(expr.right):
                    return self.builder.icmp_unsigned('<=', left, right)
                return self.builder.icmp_signed('<=', left, right)
            elif op == '>':
                if is_float:
                    return self.builder.fcmp_ordered('>', left, right)
                if self._infer_unsigned_expr(expr.left) or self._infer_unsigned_expr(expr.right):
                    return self.builder.icmp_unsigned('>', left, right)
                return self.builder.icmp_signed('>', left, right)
            elif op == '>=':
                if is_float:
                    return self.builder.fcmp_ordered('>=', left, right)
                if self._infer_unsigned_expr(expr.left) or self._infer_unsigned_expr(expr.right):
                    return self.builder.icmp_unsigned('>=', left, right)
                return self.builder.icmp_signed('>=', left, right)
            elif op == '&':
                # Bitwise AND: left & right
                return self.builder.and_(left, right)
            elif op == '|':
                # Bitwise OR: left | right
                return self.builder.or_(left, right)
            elif op == '^':
                # Bitwise XOR: left ^ right
                return self.builder.xor(left, right)
            elif op == '<<':
                # Left shift: left << right
                return self.builder.shl(left, right)
            elif op == '>>':
                # Right shift: use logical shift (lshr) for unsigned, arithmetic (ashr) for signed
                if self._infer_unsigned_expr(expr.left):
                    return self.builder.lshr(left, right)
                return self.builder.ashr(left, right)
            else:
                raise ValueError(f"Unknown operator: {op}")

        elif isinstance(expr, rast.Call):
            return self._emit_call(expr)

        elif isinstance(expr, rast.Index):
            return self._emit_index(expr)

        elif isinstance(expr, rast.If):
            # If used as expression - returns phi value from branches
            result = self._emit_if(expr)
            if result is not None:
                return result
            # If no value (shouldn't happen for well-formed if expressions), return 0
            return ir.Constant(self.i32, 0)

        elif isinstance(expr, rast.UnaryOp):
            return self._emit_unary(expr)

        elif isinstance(expr, rast.StructLit):
            return self._emit_struct_lit(expr)

        elif isinstance(expr, rast.ArrayLit):
            return self._emit_array_lit(expr)

        elif isinstance(expr, rast.ArrayFill):
            return self._emit_array_fill(expr)

        elif isinstance(expr, rast.Field):
            return self._emit_field_access(expr)

        elif isinstance(expr, rast.Cast):
            return self._emit_cast(expr)

        elif isinstance(expr, rast.Match):
            return self._emit_match(expr)

        elif isinstance(expr, rast.MethodCall):
            return self._emit_method_call(expr)

        elif isinstance(expr, rast.TryOp):
            return self._emit_try_op(expr)

        elif isinstance(expr, rast.SliceExpr):
            return self._emit_slice(expr)

        elif isinstance(expr, rast.Await):
            return self._emit_await(expr)

        elif isinstance(expr, rast.Closure):
            return self._emit_closure(expr)

        elif isinstance(expr, rast.Lambda):
            return self._emit_lambda(expr)

        elif isinstance(expr, rast.HeapExpr):
            return self._emit_heap_expr(expr)

        else:
            raise NotImplementedError(f"Expression: {type(expr)}")

    def _emit_index(self, expr: rast.Index) -> ir.Value:
        """Emit an indexing operation: base[index]."""
        index = self._emit_expr(expr.index)

        # Special handling for identifiers that are arrays
        if isinstance(expr.expr, rast.Ident):
            name = expr.expr.name
            if name in self.locals:
                alloca, ty = self.locals[name]
                if isinstance(ty, ir.ArrayType):
                    # Array type - use two-level GEP [0, index] on the alloca
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(alloca, [zero, index])
                    return self.builder.load(ptr)
            elif name in self.const_arrays:
                # Const array - use two-level GEP [0, index] on the global
                gvar, ty = self.const_arrays[name]
                if isinstance(ty, ir.ArrayType):
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(gvar, [zero, index])
                    return self.builder.load(ptr)
            elif name in self.globals:
                gvar, ty = self.globals[name]
                if isinstance(ty, ir.ArrayType):
                    # Global array - use two-level GEP [0, index] on the global
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(gvar, [zero, index])
                    return self.builder.load(ptr)

        # Special handling for struct field that is an array (e.g., buf.data[0])
        if isinstance(expr.expr, rast.Field):
            # Get the address of the array field, then index into it
            field_addr = self._emit_lvalue_addr(expr.expr)
            if isinstance(field_addr.type, ir.PointerType):
                pointee = field_addr.type.pointee
                if isinstance(pointee, ir.ArrayType):
                    # GEP with [0, index] to get element address
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(field_addr, [zero, index])
                    return self.builder.load(ptr)

        # Special handling for nested array indexing (e.g., arr[i][j] where arr is [N][M]T)
        if isinstance(expr.expr, rast.Index):
            # Get pointer to inner array element using lvalue_addr
            inner_addr = self._emit_lvalue_addr(expr.expr)
            if isinstance(inner_addr.type, ir.PointerType):
                pointee = inner_addr.type.pointee
                if isinstance(pointee, ir.ArrayType):
                    # Inner is array - GEP with [0, index] to get element address
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(inner_addr, [zero, index])
                    return self.builder.load(ptr)

        # Check if this is a Vec or String type - provide index sugar
        # v[i] becomes vec_get(&v, i), s[i] becomes string_get(&s, i)
        if isinstance(expr.expr, rast.Ident):
            name = expr.expr.name
            if name in self.ritz_types:
                base_ritz_type = self.ritz_types[name]
                if isinstance(base_ritz_type, rast.NamedType):
                    type_name = base_ritz_type.name

                    # Handle Vec<T> / Vec$T indexing
                    if type_name.startswith('Vec$') or type_name == 'Vec':
                        # Get element type from Vec$T name
                        if type_name.startswith('Vec$'):
                            elem_type_name = type_name[4:]  # Strip "Vec$"
                        else:
                            # Try to get from type args
                            if base_ritz_type.type_args:
                                elem_ty = base_ritz_type.type_args[0]
                                elem_type_name = self._type_to_mangled_name(elem_ty)
                            else:
                                raise ValueError("Vec type without element type")

                        # Build vec_get call: vec_get$T(&v, i)
                        fn_name = f"vec_get${elem_type_name}"
                        if fn_name not in self.functions:
                            raise ValueError(f"Vec indexing requires {fn_name} to be defined")

                        fn, _ = self.functions[fn_name]
                        # Get pointer to vec
                        vec_ptr = self._emit_lvalue_addr(expr.expr)
                        # Ensure index is i64
                        if index.type != self.i64:
                            index = self.builder.sext(index, self.i64)
                        return self.builder.call(fn, [vec_ptr, index])

                    # Handle String indexing: s[i] -> string_get(&s, i)
                    elif type_name == 'String':
                        fn_name = "string_get"
                        if fn_name not in self.functions:
                            raise ValueError(f"String indexing requires {fn_name} to be defined")

                        fn, _ = self.functions[fn_name]
                        # Get pointer to string
                        str_ptr = self._emit_lvalue_addr(expr.expr)
                        # Ensure index is i64
                        if index.type != self.i64:
                            index = self.builder.sext(index, self.i64)
                        return self.builder.call(fn, [str_ptr, index])

                    # Handle HashMapI64 indexing: m[k] -> hashmap_i64_get(&m, k)
                    elif type_name == 'HashMapI64':
                        fn_name = "hashmap_i64_get"
                        if fn_name not in self.functions:
                            raise ValueError(f"HashMapI64 indexing requires {fn_name} to be defined")

                        fn, _ = self.functions[fn_name]
                        # Get pointer to hashmap
                        map_ptr = self._emit_lvalue_addr(expr.expr)
                        # Ensure key is i64
                        if index.type != self.i64:
                            index = self.builder.sext(index, self.i64)
                        return self.builder.call(fn, [map_ptr, index])

        # General case
        base = self._emit_expr(expr.expr)

        # Get element type
        if isinstance(base.type, ir.PointerType):
            elem_type = base.type.pointee
            # GEP to get pointer to element
            ptr = self.builder.gep(base, [index])
            # Load the element
            return self.builder.load(ptr)
        else:
            raise ValueError(f"Cannot index type: {base.type}")

    def _emit_slice(self, expr: rast.SliceExpr) -> ir.Value:
        """Emit a slice operation: a[start:end].

        This is zero-cost syntax sugar that translates to method/function calls:
        - String: s[1:5] → string_slice(&s, 1, 5)
        - Vec<T>: v[1:5] → vec_slice_T(&v, 1, 5)

        For missing bounds:
        - [:end] → slice(0, end)
        - [start:] → slice(start, len)
        - [:] → clone()
        """
        # Determine the type of the base expression
        if isinstance(expr.expr, rast.Ident):
            name = expr.expr.name
            if name in self.ritz_types:
                base_ritz_type = self.ritz_types[name]
                if isinstance(base_ritz_type, rast.NamedType):
                    type_name = base_ritz_type.name

                    # Handle String slicing
                    if type_name == 'String':
                        return self._emit_string_slice(expr)

                    # Handle Vec<T> slicing
                    if type_name.startswith('Vec$') or type_name == 'Vec':
                        return self._emit_vec_slice(expr, type_name, base_ritz_type)

        raise ValueError(f"Slice operation not supported for this type. "
                         f"Only String and Vec types support slicing.")

    def _emit_string_slice(self, expr: rast.SliceExpr) -> ir.Value:
        """Emit string slice: s[1:5] → string_slice(&s, 1, 5)."""
        fn_name = "string_slice"
        if fn_name not in self.functions:
            raise ValueError(f"String slicing requires {fn_name} to be defined "
                             "(import ritzlib.string)")

        fn, _ = self.functions[fn_name]
        str_ptr = self._emit_lvalue_addr(expr.expr)

        # Emit start index (default to 0)
        if expr.start is not None:
            start = self._emit_expr(expr.start)
            if start.type != self.i64:
                start = self.builder.sext(start, self.i64)
        else:
            start = ir.Constant(self.i64, 0)

        # Emit end index (default to len)
        if expr.end is not None:
            end = self._emit_expr(expr.end)
            if end.type != self.i64:
                end = self.builder.sext(end, self.i64)
        else:
            # Get length via string_len
            len_fn_name = "string_len"
            if len_fn_name not in self.functions:
                raise ValueError(f"String slicing requires {len_fn_name} to be defined")
            len_fn, _ = self.functions[len_fn_name]
            end = self.builder.call(len_fn, [str_ptr])

        return self.builder.call(fn, [str_ptr, start, end])

    def _emit_vec_slice(self, expr: rast.SliceExpr, type_name: str,
                        base_ritz_type: rast.NamedType) -> ir.Value:
        """Emit vec slice: v[1:5] → vec_slice_T(&v, 1, 5)."""
        # Get element type from Vec$T name
        if type_name.startswith('Vec$'):
            elem_type_name = type_name[4:]  # Strip "Vec$"
        else:
            # Try to get from type args
            if base_ritz_type.args:
                elem_ty = base_ritz_type.args[0]
                elem_type_name = self._type_to_mangled_name(elem_ty)
            else:
                raise ValueError("Vec type without element type")

        fn_name = f"vec_slice${elem_type_name}"
        if fn_name not in self.functions:
            raise ValueError(f"Vec slicing requires {fn_name} to be defined")

        fn, _ = self.functions[fn_name]
        vec_ptr = self._emit_lvalue_addr(expr.expr)

        # Emit start index (default to 0)
        if expr.start is not None:
            start = self._emit_expr(expr.start)
            if start.type != self.i64:
                start = self.builder.sext(start, self.i64)
        else:
            start = ir.Constant(self.i64, 0)

        # Emit end index (default to len)
        if expr.end is not None:
            end = self._emit_expr(expr.end)
            if end.type != self.i64:
                end = self.builder.sext(end, self.i64)
        else:
            # Get length via vec_len$T
            len_fn_name = f"vec_len${elem_type_name}"
            if len_fn_name not in self.functions:
                raise ValueError(f"Vec slicing requires {len_fn_name} to be defined")
            len_fn, _ = self.functions[len_fn_name]
            end = self.builder.call(len_fn, [vec_ptr])

        return self.builder.call(fn, [vec_ptr, start, end])

    def _emit_struct_lit(self, expr: rast.StructLit) -> ir.Value:
        """Emit a struct literal: MyStruct { field: value, ... }."""
        struct_name = expr.name
        if struct_name not in self.struct_types:
            raise ValueError(f"Unknown struct: {struct_name}")

        struct_type = self.struct_types[struct_name]
        field_info = self.struct_fields[struct_name]

        # Build a list of field values in order
        field_values = {}
        for name, val_expr in expr.fields:
            field_values[name] = self._emit_expr(val_expr)

        # Create the struct value
        values = []
        for field_name, field_type in field_info:
            if field_name in field_values:
                val = field_values[field_name]
                llvm_type = self._ritz_type_to_llvm(field_type)
                val = self._convert_type(val, llvm_type)
                values.append(val)
            else:
                raise ValueError(f"Missing field {field_name} in struct literal")

        # Create struct aggregate
        result = ir.Constant(struct_type, ir.Undefined)
        for i, val in enumerate(values):
            result = self.builder.insert_value(result, val, i)

        return result

    def _emit_array_lit(self, expr: rast.ArrayLit) -> ir.Value:
        """Emit an array literal: [a, b, c]."""
        if not expr.elements:
            raise ValueError("Empty array literals not supported")

        # Emit all elements and infer type from first element
        values = [self._emit_expr(e) for e in expr.elements]
        elem_type = values[0].type

        # Convert all values to same type
        converted = []
        for val in values:
            converted.append(self._convert_type(val, elem_type))

        # Create array type
        arr_type = ir.ArrayType(elem_type, len(converted))

        # Build array aggregate
        result = ir.Constant(arr_type, ir.Undefined)
        for i, val in enumerate(converted):
            result = self.builder.insert_value(result, val, i)

        return result

    def _emit_array_fill(self, expr: rast.ArrayFill) -> ir.Value:
        """Emit an array fill expression: [value; count].

        Creates an array with `count` copies of `value`.

        Optimizations:
        - For zero fills: Use LLVM zeroinitializer (O(1) IR)
        - For small arrays (N <= 64): Use insertvalue chain
        - For large arrays: Use memset for byte fills, or store loop for others
        """
        if expr.count <= 0:
            raise ValueError("Array fill count must be positive")

        # Emit the value once
        val = self._emit_expr(expr.value)
        elem_type = val.type

        # Create array type
        arr_type = ir.ArrayType(elem_type, expr.count)

        # Optimization: Check if this is a zero fill
        is_zero_fill = self._is_zero_constant(val)

        # For small arrays, we can use zeroinitializer or insertvalue chain
        if expr.count <= 64:
            if is_zero_fill:
                # Use zeroinitializer for small zero fills
                return ir.Constant(arr_type, None)
            # Use insertvalue chain for small arrays (generates N instructions but N is small)
            result = ir.Constant(arr_type, ir.Undefined)
            for i in range(expr.count):
                result = self.builder.insert_value(result, val, i)
            return result

        # For large arrays, allocate on stack and use memset/loop.
        # We can't use zeroinitializer for large arrays because:
        # 1. `store [65536 x i32] zeroinitializer, ptr` causes LLVM SelectionDAG to crash
        # 2. Even if it didn't crash, it would generate a huge store operation
        # Instead, we allocate and use memset which generates efficient code.
        arr_alloca = self.builder.alloca(arr_type)

        if is_zero_fill:
            # Use memset to zero the array (efficient O(1) IR)
            ptr = self.builder.bitcast(arr_alloca, self.i8.as_pointer())
            elem_size = self._sizeof_type(elem_type)
            total_bytes = elem_size * expr.count
            byte_val = ir.Constant(self.i8, 0)
            count = ir.Constant(self.i64, total_bytes)
            self._emit_memset(ptr, byte_val, count)
        else:
            # Get element size
            elem_size = self._sizeof_type(elem_type)

            # For single-byte fills, use memset
            if elem_size == 1 and isinstance(val, ir.Constant):
                # memset(ptr, val, count)
                ptr = self.builder.bitcast(arr_alloca, self.i8.as_pointer())
                byte_val = val
                if byte_val.type != self.i8:
                    byte_val = self.builder.trunc(val, self.i8)
                count = ir.Constant(self.i64, expr.count)
                self._emit_memset(ptr, byte_val, count)
            else:
                # For multi-byte fills or non-constant values, use a store loop
                # Generate: for i in 0..count: arr[i] = val
                self._emit_fill_loop(arr_alloca, arr_type, val, expr.count)

        # Load and return the filled array
        return self.builder.load(arr_alloca)

    def _emit_array_fill_to_alloca(self, expr: rast.ArrayFill, alloca: ir.AllocaInstr,
                                    target_type: ir.Type) -> None:
        """Emit array fill directly to an existing alloca.

        This is an optimization for large array fills assigned to variables.
        Instead of:
            1. Create temp alloca
            2. Fill temp
            3. Load temp (huge value!)
            4. Store to target (huge value!)
        We do:
            1. Fill target alloca directly

        This avoids the massive load/store that crashes LLVM SelectionDAG.
        """
        # Emit the fill value
        val = self._emit_expr(expr.value)
        is_zero_fill = self._is_zero_constant(val)

        # Get target element type
        if isinstance(target_type, ir.ArrayType):
            target_elem_type = target_type.element
        else:
            # Should be array type, but fall back to value type if not
            target_elem_type = val.type

        # Convert value to target element type if needed
        if val.type != target_elem_type:
            val = self._convert_type(val, target_elem_type)

        if is_zero_fill:
            # Use memset for zero fills (efficient O(1) IR)
            ptr = self.builder.bitcast(alloca, self.i8.as_pointer())
            elem_size = self._sizeof_type(target_elem_type)
            total_bytes = elem_size * expr.count
            byte_val = ir.Constant(self.i8, 0)
            count = ir.Constant(self.i64, total_bytes)
            self._emit_memset(ptr, byte_val, count)
        else:
            elem_size = self._sizeof_type(target_elem_type)
            # For single-byte fills, use memset
            if elem_size == 1 and isinstance(val, ir.Constant):
                ptr = self.builder.bitcast(alloca, self.i8.as_pointer())
                byte_val = val
                if byte_val.type != self.i8:
                    byte_val = self.builder.trunc(val, self.i8)
                count = ir.Constant(self.i64, expr.count)
                self._emit_memset(ptr, byte_val, count)
            else:
                # Use fill loop for multi-byte non-zero fills
                arr_type = ir.ArrayType(target_elem_type, expr.count)
                self._emit_fill_loop(alloca, arr_type, val, expr.count)

    def _is_zero_constant(self, val: ir.Value) -> bool:
        """Check if a value is a compile-time zero constant."""
        if not isinstance(val, ir.Constant):
            return False

        # Check for integer zero
        if isinstance(val.type, ir.IntType):
            return val.constant == 0

        # Check for float zero
        if isinstance(val.type, (ir.FloatType, ir.DoubleType)):
            return val.constant == 0.0

        # Check for null pointer
        if isinstance(val.type, ir.PointerType):
            return val.constant is None

        return False

    def _sizeof_type(self, ty: ir.Type) -> int:
        """Get the size in bytes of an LLVM type."""
        if isinstance(ty, ir.IntType):
            return ty.width // 8
        elif isinstance(ty, ir.FloatType):
            return 4
        elif isinstance(ty, ir.DoubleType):
            return 8
        elif isinstance(ty, ir.PointerType):
            return 8  # 64-bit pointers
        elif isinstance(ty, ir.ArrayType):
            return self._sizeof_type(ty.element) * ty.count
        elif isinstance(ty, ir.LiteralStructType):
            return sum(self._sizeof_type(e) for e in ty.elements)
        else:
            # Default to pointer size for unknown types
            return 8

    def _emit_memset(self, ptr: ir.Value, byte_val: ir.Value, count: ir.Value) -> None:
        """Emit a call to llvm.memset intrinsic."""
        # Declare memset if not already done
        if not hasattr(self, '_memset_fn'):
            # llvm.memset.p0i8.i64(i8* dest, i8 val, i64 len, i1 isvolatile)
            memset_ty = ir.FunctionType(self.void, [
                self.i8.as_pointer(),  # dest
                self.i8,               # val
                self.i64,              # len
                self.i1                # isvolatile
            ])
            self._memset_fn = ir.Function(self.module, memset_ty, name="llvm.memset.p0i8.i64")

        is_volatile = ir.Constant(self.i1, 0)
        self.builder.call(self._memset_fn, [ptr, byte_val, count, is_volatile])

    def _emit_fill_loop(self, arr_alloca: ir.Value, arr_type: ir.ArrayType,
                        val: ir.Value, count: int) -> None:
        """Emit a loop to fill an array with a value.

        Generates:
            for (i64 i = 0; i < count; i++) {
                arr[i] = val;
            }
        """
        # Create basic blocks
        loop_header = self.builder.append_basic_block("fill_header")
        loop_body = self.builder.append_basic_block("fill_body")
        loop_end = self.builder.append_basic_block("fill_end")

        # Initialize counter
        counter_alloca = self.builder.alloca(self.i64)
        self.builder.store(ir.Constant(self.i64, 0), counter_alloca)
        self.builder.branch(loop_header)

        # Loop header: check if i < count
        self.builder.position_at_end(loop_header)
        i = self.builder.load(counter_alloca)
        cond = self.builder.icmp_signed('<', i, ir.Constant(self.i64, count))
        self.builder.cbranch(cond, loop_body, loop_end)

        # Loop body: arr[i] = val; i++
        self.builder.position_at_end(loop_body)
        i = self.builder.load(counter_alloca)
        elem_ptr = self.builder.gep(arr_alloca, [ir.Constant(self.i32, 0), i])
        self.builder.store(val, elem_ptr)
        next_i = self.builder.add(i, ir.Constant(self.i64, 1))
        self.builder.store(next_i, counter_alloca)
        self.builder.branch(loop_header)

        # Continue after loop
        self.builder.position_at_end(loop_end)

    def _emit_array_convert_loop(self, src_alloca: ir.Value, dst_alloca: ir.Value,
                                  src_type: ir.ArrayType, dst_type: ir.ArrayType) -> None:
        """Emit a loop to convert array elements from src to dst type.

        Generates:
            for (i64 i = 0; i < count; i++) {
                dst[i] = convert(src[i], target_elem_type);
            }
        """
        count = src_type.count

        # Create basic blocks
        loop_header = self.builder.append_basic_block("convert_header")
        loop_body = self.builder.append_basic_block("convert_body")
        loop_end = self.builder.append_basic_block("convert_end")

        # Initialize counter
        counter_alloca = self.builder.alloca(self.i64)
        self.builder.store(ir.Constant(self.i64, 0), counter_alloca)
        self.builder.branch(loop_header)

        # Loop header: check if i < count
        self.builder.position_at_end(loop_header)
        i = self.builder.load(counter_alloca)
        cond = self.builder.icmp_signed('<', i, ir.Constant(self.i64, count))
        self.builder.cbranch(cond, loop_body, loop_end)

        # Loop body: dst[i] = convert(src[i]); i++
        self.builder.position_at_end(loop_body)
        i = self.builder.load(counter_alloca)

        # Load source element
        src_elem_ptr = self.builder.gep(src_alloca, [ir.Constant(self.i32, 0), i])
        src_elem = self.builder.load(src_elem_ptr)

        # Convert to target type
        converted = self._convert_type(src_elem, dst_type.element)

        # Store to destination
        dst_elem_ptr = self.builder.gep(dst_alloca, [ir.Constant(self.i32, 0), i])
        self.builder.store(converted, dst_elem_ptr)

        # Increment counter
        next_i = self.builder.add(i, ir.Constant(self.i64, 1))
        self.builder.store(next_i, counter_alloca)
        self.builder.branch(loop_header)

        # Continue after loop
        self.builder.position_at_end(loop_end)

    def _emit_lvalue_addr(self, expr: rast.Expr) -> ir.Value:
        """
        Get the address of an lvalue expression (for assignment purposes).
        Returns a pointer to the storage location, not the loaded value.
        """
        if isinstance(expr, rast.Ident):
            name = expr.name
            if name in self.locals:
                alloca, _ = self.locals[name]
                return alloca
            elif name in self.globals:
                gvar, _ = self.globals[name]
                return gvar
            elif name in self.params:
                # For params/let bindings that are SSA values, create a temp alloca
                # This allows borrowing of immutable bindings (for RERITZ @ and call-site borrows)
                val, ty = self.params[name]
                temp_alloca = self.builder.alloca(ty, name=f"{name}.addr")
                self.builder.store(val, temp_alloca)
                return temp_alloca
            else:
                raise ValueError(f"Unknown variable: {name}")
        elif isinstance(expr, rast.UnaryOp) and expr.op == '*':
            # *ptr -> return ptr itself
            return self._emit_expr(expr.operand)
        elif isinstance(expr, rast.Index):
            # arr[i] -> GEP to element
            index = self._emit_expr(expr.index)
            if isinstance(expr.expr, rast.Ident):
                name = expr.expr.name
                if name in self.locals:
                    alloca, ty = self.locals[name]
                    if isinstance(ty, ir.ArrayType):
                        zero = ir.Constant(self.i32, 0)
                        return self.builder.gep(alloca, [zero, index])
                elif name in self.globals:
                    gvar, ty = self.globals[name]
                    if isinstance(ty, ir.ArrayType):
                        # Global array - use two-level GEP [0, index] on the global
                        zero = ir.Constant(self.i32, 0)
                        return self.builder.gep(gvar, [zero, index])
            # Handle struct field that is an array (e.g., buf.data[0] = x)
            if isinstance(expr.expr, rast.Field):
                field_addr = self._emit_lvalue_addr(expr.expr)
                if isinstance(field_addr.type, ir.PointerType):
                    pointee = field_addr.type.pointee
                    if isinstance(pointee, ir.ArrayType):
                        zero = ir.Constant(self.i32, 0)
                        return self.builder.gep(field_addr, [zero, index])
            # Handle nested array indexing (e.g., arr[i][j] where arr is [N][M]T)
            if isinstance(expr.expr, rast.Index):
                inner_addr = self._emit_lvalue_addr(expr.expr)
                if isinstance(inner_addr.type, ir.PointerType):
                    pointee = inner_addr.type.pointee
                    if isinstance(pointee, ir.ArrayType):
                        # Inner is array - GEP with [0, index] to get element
                        zero = ir.Constant(self.i32, 0)
                        return self.builder.gep(inner_addr, [zero, index])
                    else:
                        # Inner is pointer to element - GEP with [index]
                        return self.builder.gep(inner_addr, [index])
            base = self._emit_expr(expr.expr)
            if isinstance(base.type, ir.PointerType):
                return self.builder.gep(base, [index])
            raise ValueError(f"Cannot index type: {base.type}")
        elif isinstance(expr, rast.Field):
            # struct.field -> GEP to field
            # There are several cases:
            # 1. Base is a local struct variable: buf.data -> GEP from alloca
            # 2. Base is a pointer to struct: p.data where p: *Struct -> load p, then GEP

            if isinstance(expr.expr, rast.Ident):
                name = expr.expr.name
                if name in self.locals:
                    alloca, ty = self.locals[name]
                    # Check if this is a pointer-to-struct (e.g., b: *StackBuffer)
                    if isinstance(ty, ir.PointerType):
                        pointee = ty.pointee
                        if isinstance(pointee, ir.BaseStructType):
                            # Load the pointer first, then GEP into the struct
                            struct_ptr = self.builder.load(alloca)
                            struct_name = self._get_struct_name_from_type(pointee)
                            if struct_name:
                                idx = self._get_struct_field_index(struct_name, expr.field)
                                return self.builder.gep(struct_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                    # Regular struct local: GEP directly from alloca
                    if isinstance(ty, ir.BaseStructType):
                        struct_name = self._get_struct_name_from_type(ty)
                        if struct_name:
                            idx = self._get_struct_field_index(struct_name, expr.field)
                            return self.builder.gep(alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                elif name in self.params:
                    ptr_val, ptr_ty = self.params[name]
                    # If it's a pointer to a struct, use the pointer directly
                    if isinstance(ptr_ty, ir.PointerType):
                        pointee = ptr_ty.pointee
                        if isinstance(pointee, ir.BaseStructType):
                            struct_name = self._get_struct_name_from_type(pointee)
                            if struct_name:
                                idx = self._get_struct_field_index(struct_name, expr.field)
                                return self.builder.gep(ptr_val, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])

            # General case: get address of struct then GEP to field
            struct_addr = self._emit_lvalue_addr(expr.expr)
            if isinstance(struct_addr.type, ir.PointerType):
                pointee = struct_addr.type.pointee
                if isinstance(pointee, ir.BaseStructType):
                    struct_name = self._get_struct_name_from_type(pointee)
                    if struct_name:
                        idx = self._get_struct_field_index(struct_name, expr.field)
                        return self.builder.gep(struct_addr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                # Handle pointer-to-pointer case: if the field is a pointer type,
                # we need to load it first then GEP into the struct it points to.
                # e.g., lex.defs.defs where lex.defs is *TokenDefs
                if isinstance(pointee, ir.PointerType):
                    inner_pointee = pointee.pointee
                    if isinstance(inner_pointee, ir.BaseStructType):
                        # Load the pointer value
                        ptr_val = self.builder.load(struct_addr)
                        struct_name = self._get_struct_name_from_type(inner_pointee)
                        if struct_name:
                            idx = self._get_struct_field_index(struct_name, expr.field)
                            return self.builder.gep(ptr_val, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
            raise ValueError(f"Cannot access field on type: {struct_addr.type}")
        else:
            raise ValueError(f"Cannot get address of: {type(expr)}")

    def _find_free_variables(self, expr: rast.Expr, bound_vars: set) -> set:
        """Find free variables in an expression (referenced but not locally bound).

        Args:
            expr: Expression to analyze
            bound_vars: Set of variable names that are locally bound

        Returns:
            Set of free variable names
        """
        free_vars = set()

        if isinstance(expr, rast.Ident):
            name = expr.name
            # Only consider it free if not bound locally and not a global/function
            if name not in bound_vars:
                free_vars.add(name)

        elif isinstance(expr, rast.BinOp):
            free_vars |= self._find_free_variables(expr.left, bound_vars)
            free_vars |= self._find_free_variables(expr.right, bound_vars)

        elif isinstance(expr, rast.UnaryOp):
            free_vars |= self._find_free_variables(expr.operand, bound_vars)

        elif isinstance(expr, rast.Call):
            if isinstance(expr.func, rast.Ident):
                # Check if this is a variable (function pointer) vs a defined function
                # If it's not a known function, it might be a captured variable
                func_name = expr.func.name
                if func_name not in self.functions and func_name not in bound_vars:
                    # Could be a captured function pointer variable
                    free_vars.add(func_name)
            else:
                free_vars |= self._find_free_variables(expr.func, bound_vars)
            for arg in expr.args:
                free_vars |= self._find_free_variables(arg, bound_vars)

        elif isinstance(expr, rast.Index):
            free_vars |= self._find_free_variables(expr.expr, bound_vars)
            free_vars |= self._find_free_variables(expr.index, bound_vars)

        elif isinstance(expr, rast.Field):
            free_vars |= self._find_free_variables(expr.expr, bound_vars)

        elif isinstance(expr, rast.If):
            free_vars |= self._find_free_variables(expr.cond, bound_vars)
            for stmt in expr.then_block.stmts:
                free_vars |= self._find_free_variables_stmt(stmt, bound_vars)
            if expr.then_block.expr:
                free_vars |= self._find_free_variables(expr.then_block.expr, bound_vars)
            if expr.else_block:
                for stmt in expr.else_block.stmts:
                    free_vars |= self._find_free_variables_stmt(stmt, bound_vars)
                if expr.else_block.expr:
                    free_vars |= self._find_free_variables(expr.else_block.expr, bound_vars)

        elif isinstance(expr, rast.Cast):
            free_vars |= self._find_free_variables(expr.expr, bound_vars)

        elif isinstance(expr, rast.StructLit):
            for _, val in expr.fields:
                free_vars |= self._find_free_variables(val, bound_vars)

        elif isinstance(expr, rast.ArrayLit):
            for elem in expr.elements:
                free_vars |= self._find_free_variables(elem, bound_vars)

        elif isinstance(expr, rast.Closure):
            # Nested closure - add its params to bound vars
            inner_bound = bound_vars | {p.name for p in expr.params}
            free_vars |= self._find_free_variables(expr.body, inner_bound)

        # Literals don't have free variables
        elif isinstance(expr, (rast.IntLit, rast.FloatLit, rast.StringLit,
                               rast.CStringLit, rast.SpanStringLit, rast.CharLit,
                               rast.BoolLit, rast.NullLit)):
            pass

        return free_vars

    def _find_free_variables_stmt(self, stmt: rast.Stmt, bound_vars: set) -> set:
        """Find free variables in a statement."""
        free_vars = set()

        if isinstance(stmt, rast.ExprStmt):
            free_vars |= self._find_free_variables(stmt.expr, bound_vars)
        elif isinstance(stmt, (rast.LetStmt, rast.VarStmt)):
            free_vars |= self._find_free_variables(stmt.value, bound_vars)
        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value:
                free_vars |= self._find_free_variables(stmt.value, bound_vars)
        elif isinstance(stmt, rast.AssignStmt):
            free_vars |= self._find_free_variables(stmt.value, bound_vars)
            free_vars |= self._find_free_variables(stmt.target, bound_vars)

        return free_vars

    def _emit_await(self, await_expr: rast.Await) -> ir.Value:
        """Emit an await expression.

        Behavior depends on context:
        1. Inside async fn: Handled by async_transform, should not reach here
        2. Outside async fn: Generate poll loop for async function calls

        For non-async calls, just evaluate the inner expression (synchronous MVP).
        """
        inner_expr = await_expr.expr

        # Check if this is a call to an async function
        if isinstance(inner_expr, rast.Call) and isinstance(inner_expr.func, rast.Ident):
            fn_name = inner_expr.func.name
            if fn_name in self.async_functions:
                # Async function call outside async context - generate poll loop
                return self._emit_await_poll_loop(fn_name, inner_expr.args)

        # Non-async call: just evaluate the inner expression (MVP behavior)
        return self._emit_expr(inner_expr)

    def _emit_await_poll_loop(self, fn_name: str, args: list) -> ir.Value:
        """Generate a poll loop for awaiting an async function outside async context.

        Equivalent to:
            var future = fn_name(args)
            while true
                let result = fn_name_poll(&future)
                if result >= 0
                    return result
        """
        future_type_name = f"{fn_name}_Future"
        poll_fn_name = f"{fn_name}_poll"

        # Get LLVM types
        future_llvm_type = self.struct_types.get(future_type_name)
        if future_llvm_type is None:
            raise ValueError(f"Unknown Future type: {future_type_name}")

        # Get the poll function
        if poll_fn_name not in self.functions:
            raise ValueError(f"Unknown poll function: {poll_fn_name}")
        poll_fn, _ = self.functions[poll_fn_name]

        # Get the constructor function
        if fn_name not in self.functions:
            raise ValueError(f"Unknown async function: {fn_name}")
        constructor_fn, _ = self.functions[fn_name]

        # Emit arguments with type conversion (int literals default to i64)
        emit_args = []
        for i, arg in enumerate(args):
            val = self._emit_expr(arg)
            expected_type = constructor_fn.function_type.args[i]
            val = self._convert_type(val, expected_type)
            emit_args.append(val)

        # Create the future: var future = fn_name(args)
        future_alloca = self.builder.alloca(future_llvm_type, name="future")
        future_val = self.builder.call(constructor_fn, emit_args, name="future_init")
        self.builder.store(future_val, future_alloca)

        # Create loop blocks
        loop_block = self.current_fn.append_basic_block("poll_loop")
        done_block = self.current_fn.append_basic_block("poll_done")

        # Jump to loop
        self.builder.branch(loop_block)

        # Poll loop body
        self.builder.position_at_end(loop_block)

        # Call poll: result = fn_name_poll(&future)
        poll_result = self.builder.call(poll_fn, [future_alloca], name="poll_result")

        # Check if ready: result >= 0
        pending = ir.Constant(self.i32, -1)
        is_pending = self.builder.icmp_signed('==', poll_result, pending, name="is_pending")
        self.builder.cbranch(is_pending, loop_block, done_block)

        # Done block - return the result
        self.builder.position_at_end(done_block)

        return poll_result

    def _emit_heap_expr(self, heap_expr: rast.HeapExpr) -> ir.Value:
        """Emit a heap expression: heap expr.

        Compiles to inline heap allocation:
            1. Evaluate expression to get value
            2. malloc(sizeof(T))
            3. Store value at allocated address
            4. Return *T pointer to heap memory

        The heap keyword provides syntactic sugar for heap allocation:
            let p = heap 42
            // allocates i64 on heap, returns *i64
        """
        # Emit the inner expression
        inner_val = self._emit_expr(heap_expr.expr)
        llvm_type = inner_val.type

        # Calculate size of the value type
        size = self._type_size_bytes(llvm_type)
        size_val = ir.Constant(self.i64, size)

        # Call malloc - look in functions first, then extern_fns
        malloc_fn = None
        if "malloc" in self.functions:
            malloc_fn, _ = self.functions["malloc"]
        elif "malloc" in self.extern_fns:
            malloc_fn_type, _ = self.extern_fns["malloc"]
            # Declare the function if not already in module
            malloc_fn = self.module.globals.get("malloc")
            if malloc_fn is None:
                malloc_fn = ir.Function(self.module, ir.FunctionType(
                    ir.PointerType(ir.IntType(8)), [self.i64]), name="malloc")
        if malloc_fn is None:
            raise ValueError("heap requires ritzlib.memory (malloc not found)")
        raw_ptr = self.builder.call(malloc_fn, [size_val], name="heap_ptr")

        # Cast to *T
        ptr_type = ir.PointerType(llvm_type)
        typed_ptr = self.builder.bitcast(raw_ptr, ptr_type, name="typed_ptr")

        # Store the value
        self.builder.store(inner_val, typed_ptr)

        # Return the typed pointer directly
        # Usage: let p = heap 42  // p is *i64
        #        *p = 100        // modify value
        #        free(p as *u8)  // manual cleanup
        return typed_ptr

    def _emit_closure(self, closure: rast.Closure) -> ir.Value:
        """Emit a closure expression: |params| body.

        Closures compile to anonymous functions. If the closure captures
        variables from the enclosing scope, they are passed as additional
        parameters and the closure is wrapped in a partial application struct.

        For closures without captures, returns a direct function pointer.
        For closures with captures, returns a "fat pointer" struct containing
        the function pointer and captured values.

        The closure's types are inferred from:
        1. Explicit parameter types in the closure
        2. The expected type from context (e.g., let x: fn(i32) -> i32 = |x| ...)

        Returns a function pointer to the anonymous function.
        """
        # Get expected type for type inference
        expected_type = self.closure_expected_type

        if expected_type is None:
            raise ValueError(
                f"Cannot infer closure type - must be assigned to a typed variable. "
                f"Use: let f: fn(T) -> R = |x| ..."
            )

        # Find captured variables
        param_names = {p.name for p in closure.params}
        free_vars = self._find_free_variables(closure.body, param_names)

        # Filter to only variables that exist in the enclosing scope
        # (not globals, functions, or unknown names)
        captures = []
        capture_values = []
        capture_llvm_types = []
        capture_ritz_types = []

        for name in sorted(free_vars):  # Sort for deterministic ordering
            # Check if it's a local or parameter in the enclosing scope
            if name in self.locals:
                alloca, ty = self.locals[name]
                val = self.builder.load(alloca)
                captures.append(name)
                capture_values.append(val)
                capture_llvm_types.append(ty)
                capture_ritz_types.append(self.ritz_types.get(name))
            elif name in self.params:
                val, ty = self.params[name]
                captures.append(name)
                capture_values.append(val)
                capture_llvm_types.append(ty)
                capture_ritz_types.append(self.ritz_types.get(name))
            # Globals, functions, and constants are accessible without capture

        # Generate unique name for the anonymous function
        self.closure_counter += 1
        closure_name = f"__closure_{self.closure_counter}"

        # Build parameter types from expected type PLUS captured variables
        param_types = [self._ritz_type_to_llvm(p) for p in expected_type.params]
        # Add capture types at the end
        param_types.extend(capture_llvm_types)

        ret_type = self._ritz_type_to_llvm(expected_type.ret) if expected_type.ret else self.void

        # Create the function type and function
        fn_type = ir.FunctionType(ret_type, param_types)
        fn = ir.Function(self.module, fn_type, name=closure_name)
        fn.linkage = 'private'  # Not visible outside this module

        # Save current state
        saved_builder = self.builder
        saved_fn = self.current_fn
        saved_locals = self.locals.copy()
        saved_params = self.params.copy()
        saved_ritz_types = self.ritz_types.copy()
        saved_has_returned = self.has_returned

        # Set up new function context
        self.current_fn = fn
        self.locals = {}
        self.params = {}
        self.has_returned = False

        # Create entry block
        block = fn.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)

        # Set up regular parameters
        num_regular_params = len(closure.params)
        for i, (arg, param) in enumerate(zip(fn.args[:num_regular_params], closure.params)):
            param_name = param.name
            arg.name = f"{param_name}.arg"

            # Allocate storage for the parameter (so it can be used like a local)
            alloca = self.builder.alloca(arg.type, name=param_name)
            self.builder.store(arg, alloca)
            self.locals[param_name] = (alloca, arg.type)

            # Store Ritz type
            if i < len(expected_type.params):
                self.ritz_types[param_name] = expected_type.params[i]

        # Set up captured variables as parameters
        for i, (cap_name, cap_ritz_type) in enumerate(zip(captures, capture_ritz_types)):
            arg = fn.args[num_regular_params + i]
            arg.name = f"{cap_name}.cap"

            # Allocate storage for the captured value
            alloca = self.builder.alloca(arg.type, name=cap_name)
            self.builder.store(arg, alloca)
            self.locals[cap_name] = (alloca, arg.type)

            # Store Ritz type
            if cap_ritz_type:
                self.ritz_types[cap_name] = cap_ritz_type

        # Emit closure body expression
        result = self._emit_expr(closure.body)

        # Emit return
        if ret_type == self.void:
            self.builder.ret_void()
        else:
            # Convert result type if needed
            result = self._convert_type(result, ret_type)
            self.builder.ret(result)

        # Restore previous state
        self.builder = saved_builder
        self.current_fn = saved_fn
        self.locals = saved_locals
        self.params = saved_params
        self.ritz_types = saved_ritz_types
        self.has_returned = saved_has_returned

        # If there are no captures, return the function pointer directly
        if not captures:
            return fn

        # With captures, we use a "capture by value" approach:
        # The closure function takes extra parameters for captured values.
        # We generate a unique thunk per closure INSTANCE that passes the
        # captured values.
        #
        # To handle multiple instances of the same closure (e.g., calling
        # make_adder(5) and make_adder(10)), we use an array of environment
        # slots. Each closure instance gets its own slot.
        #
        # This is a simplified implementation for the bootstrap compiler.
        # A production implementation would use heap-allocated environments.

        # Create the environment struct type (same for all instances of this closure)
        env_struct_name = f"__closure_env_{self.closure_counter}"
        if env_struct_name not in self._closure_env_types:
            env_struct_type = self.module.context.get_identified_type(env_struct_name)
            env_struct_type.set_body(*capture_llvm_types)
            self._closure_env_types[env_struct_name] = env_struct_type
        else:
            env_struct_type = self._closure_env_types[env_struct_name]

        # Create an array of environment slots for this closure (max 16 instances)
        # This is a hack - proper impl would use heap allocation
        MAX_CLOSURE_INSTANCES = 16
        env_array_name = f"__closure_env_{self.closure_counter}_array"
        if env_array_name not in self._closure_env_arrays:
            env_array_type = ir.ArrayType(env_struct_type, MAX_CLOSURE_INSTANCES)
            env_array = ir.GlobalVariable(self.module, env_array_type, name=env_array_name)
            env_array.linkage = 'private'
            # Initialize with zeros
            zero_env = ir.Constant(env_struct_type, [ir.Constant(ty, None) for ty in capture_llvm_types])
            env_array.initializer = ir.Constant(env_array_type, [zero_env] * MAX_CLOSURE_INSTANCES)
            self._closure_env_arrays[env_array_name] = env_array

            # Create a counter for instance allocation
            counter_name = f"__closure_env_{self.closure_counter}_idx"
            counter = ir.GlobalVariable(self.module, self.i32, name=counter_name)
            counter.linkage = 'private'
            counter.initializer = ir.Constant(self.i32, 0)
            self._closure_env_counters[env_array_name] = counter

        env_array = self._closure_env_arrays[env_array_name]
        env_counter = self._closure_env_counters[env_array_name]

        # Allocate a new environment slot
        current_idx = self.builder.load(env_counter)
        # Store captured values into the allocated slot
        for i, (cap_name, cap_val, cap_ty) in enumerate(zip(captures, capture_values, capture_llvm_types)):
            ptr = self.builder.gep(env_array, [ir.Constant(self.i32, 0), current_idx, ir.Constant(self.i32, i)])
            self.builder.store(cap_val, ptr)

        # Increment the counter for next allocation (with wraparound)
        next_idx = self.builder.add(current_idx, ir.Constant(self.i32, 1))
        wrapped_idx = self.builder.urem(next_idx, ir.Constant(self.i32, MAX_CLOSURE_INSTANCES))
        self.builder.store(wrapped_idx, env_counter)

        # Generate a thunk for each environment slot (we only need one per slot actually used)
        # For simplicity, we generate MAX_CLOSURE_INSTANCES thunks statically
        thunk_array_name = f"__closure_thunks_{self.closure_counter}"
        if thunk_array_name not in self._closure_thunk_arrays:
            thunk_param_types = [self._ritz_type_to_llvm(p) for p in expected_type.params]
            thunk_fn_type = ir.FunctionType(ret_type, thunk_param_types)

            thunks = []
            for slot_idx in range(MAX_CLOSURE_INSTANCES):
                thunk_name = f"__closure_thunk_{self.closure_counter}_{slot_idx}"
                thunk_fn = ir.Function(self.module, thunk_fn_type, name=thunk_name)
                thunk_fn.linkage = 'private'

                # Build thunk body
                thunk_block = thunk_fn.append_basic_block(name="entry")
                thunk_builder = ir.IRBuilder(thunk_block)

                # Gather arguments: regular params + captured values from this slot
                call_args = list(thunk_fn.args)
                for i in range(len(captures)):
                    ptr = thunk_builder.gep(env_array, [
                        ir.Constant(self.i32, 0),
                        ir.Constant(self.i32, slot_idx),
                        ir.Constant(self.i32, i)
                    ])
                    cap_val = thunk_builder.load(ptr)
                    call_args.append(cap_val)

                # Call the real closure function
                result = thunk_builder.call(fn, call_args)

                if ret_type == self.void:
                    thunk_builder.ret_void()
                else:
                    thunk_builder.ret(result)

                thunks.append(thunk_fn)

            # Create array of thunk function pointers
            thunk_ptr_type = ir.PointerType(thunk_fn_type)
            thunk_array_type = ir.ArrayType(thunk_ptr_type, MAX_CLOSURE_INSTANCES)
            thunk_array = ir.GlobalVariable(self.module, thunk_array_type, name=thunk_array_name)
            thunk_array.linkage = 'private'
            thunk_array.initializer = ir.Constant(thunk_array_type, thunks)
            self._closure_thunk_arrays[thunk_array_name] = thunk_array

        thunk_array = self._closure_thunk_arrays[thunk_array_name]

        # Look up the thunk for this instance's slot
        thunk_ptr_ptr = self.builder.gep(thunk_array, [ir.Constant(self.i32, 0), current_idx])
        thunk_ptr = self.builder.load(thunk_ptr_ptr)

        return thunk_ptr

    def _emit_lambda(self, lambda_expr: rast.Lambda) -> ir.Value:
        """Emit a lambda expression: fn(params) -> RetType expr.

        Lambda is the older form of closure with explicit parameters.
        We convert it to a Closure and delegate to _emit_closure.
        """
        # Convert Lambda parameters to ClosureParams
        closure_params = [
            rast.ClosureParam(p.name, p.type)
            for p in lambda_expr.params
        ]

        # Create a Closure AST node and delegate
        closure = rast.Closure(
            lambda_expr.span,
            closure_params,
            lambda_expr.body,
            captures=[]
        )

        return self._emit_closure(closure)

    def _emit_unary(self, expr: rast.UnaryOp) -> ir.Value:
        """Emit a unary operation: -x, !x, *x, @x, @&x."""
        # Handle address-of operators: @, @&
        # RERITZ syntax: @ = immutable ref, @& = mutable ref
        # Legacy & and &mut are still accepted here for backward compat with existing AST
        # All map to the same LLVM IR: taking a pointer to the operand
        if expr.op in ('&', '@', '&mut', '@&'):
            if isinstance(expr.operand, rast.Ident):
                name = expr.operand.name
                if name in self.locals:
                    alloca, _ = self.locals[name]
                    return alloca  # Return the alloca pointer
                elif name in self.globals:
                    gvar, _ = self.globals[name]
                    return gvar  # Return the global variable pointer
                elif name in self.params:
                    # For params/let bindings that are SSA values, create a temp alloca
                    # This allows taking address of immutable bindings (for @ operator in RERITZ)
                    val, ty = self.params[name]
                    temp_alloca = self.builder.alloca(ty, name=f"{name}.addr")
                    self.builder.store(val, temp_alloca)
                    return temp_alloca
                else:
                    raise ValueError(f"Unknown variable: {name}")
            elif isinstance(expr.operand, rast.Index):
                # For &arr[i] or &arr[i][j], use _emit_lvalue_addr which handles all cases
                # including nested array indexing
                return self._emit_lvalue_addr(expr.operand)
            elif isinstance(expr.operand, rast.Field):
                # For &struct.field, use _emit_lvalue_addr to get the field's address
                return self._emit_lvalue_addr(expr.operand)
            else:
                # For more complex expressions, emit the value (might be a pointer already)
                operand = self._emit_expr(expr.operand)
                return operand

        operand = self._emit_expr(expr.operand)

        if expr.op == '-':
            # Negation
            if isinstance(operand.type, ir.IntType):
                return self.builder.neg(operand)
            else:
                return self.builder.fneg(operand)

        elif expr.op in ('!', 'not'):
            # Logical not - compare with zero
            zero = ir.Constant(operand.type, 0)
            return self.builder.icmp_unsigned('==', operand, zero)

        elif expr.op == '*':
            # Dereference
            if isinstance(operand.type, ir.PointerType):
                return self.builder.load(operand)
            else:
                raise ValueError(f"Cannot dereference non-pointer: {operand.type}")

        elif expr.op == '~':
            # Bitwise NOT: ~x = xor x, -1
            all_ones = ir.Constant(operand.type, -1)
            return self.builder.xor(operand, all_ones)

        else:
            raise ValueError(f"Unknown unary operator: {expr.op}")

    def _emit_struct_lit(self, expr: rast.StructLit) -> ir.Value:
        """Emit a struct literal: MyStruct { field1: value1, field2: value2 }."""
        struct_name = expr.name
        if struct_name not in self.struct_types:
            raise ValueError(f"Unknown struct: {struct_name}")

        struct_type = self.struct_types[struct_name]
        field_defs = self.struct_fields[struct_name]

        # Create a map of field name -> index
        field_indices = {name: i for i, (name, _) in enumerate(field_defs)}

        # Build an array of field values in the correct order
        field_values = [None] * len(field_defs)

        # Fill in the field values as provided in the struct literal
        for field_name, field_expr in expr.fields:
            if field_name not in field_indices:
                raise ValueError(f"Unknown field {field_name} in struct {struct_name}")

            idx = field_indices[field_name]
            field_val = self._emit_expr(field_expr)

            # Get the expected type for this field
            _, expected_type = field_defs[idx]
            expected_llvm_type = self._ritz_type_to_llvm(expected_type)

            # Convert if needed
            field_val = self._convert_type(field_val, expected_llvm_type)

            field_values[idx] = field_val

        # Check that all fields are provided
        for i, val in enumerate(field_values):
            if val is None:
                field_name, _ = field_defs[i]
                raise ValueError(f"Field {field_name} not provided in struct literal")

        # Build struct using insert_value
        # Start with undef then insert each field
        result = ir.Constant(struct_type, ir.Undefined)
        for i, val in enumerate(field_values):
            result = self.builder.insert_value(result, val, i)

        return result

    def _get_local_alloca(self, expr: rast.Expr) -> Optional[ir.AllocaInstr]:
        """Get the alloca for a local variable expression, if applicable.

        Returns the alloca pointer if expr is an identifier that's a local variable,
        otherwise returns None.
        """
        if isinstance(expr, rast.Ident):
            name = expr.name
            if name in self.locals:
                alloca, _ = self.locals[name]
                return alloca
        return None

    def _emit_field_access(self, expr: rast.Field) -> ir.Value:
        """Emit field access: struct_val.field or struct_ptr->field.

        Supports implicit deref for Box<T> types:
          If b: Box<Point>, then b.x is equivalent to (*b.ptr).x

        For local variables, uses GEP directly on the alloca to avoid loading
        the entire struct into a register (which can crash LLVM for large structs).
        """
        # Optimization: if the inner expression is a local variable, use GEP directly
        # instead of loading the entire struct then extracting a field.
        local_alloca = self._get_local_alloca(expr.expr)
        if local_alloca is not None:
            pointee_type = local_alloca.type.pointee
            if isinstance(pointee_type, ir.BaseStructType):
                struct_name = self._get_struct_name_from_type(pointee_type)
                if struct_name:
                    # Check for Box implicit deref
                    if self._is_box_type(struct_name) and not self._struct_has_field(struct_name, expr.field):
                        inner_type_name = self._get_box_inner_type_name(struct_name)
                        if inner_type_name and self._struct_has_field(inner_type_name, expr.field):
                            ptr_field_ptr = self.builder.gep(local_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
                            inner_ptr = self.builder.load(ptr_field_ptr)
                            idx = self._get_struct_field_index(inner_type_name, expr.field)
                            field_ptr = self.builder.gep(inner_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                            return self.builder.load(field_ptr)

                    idx = self._get_struct_field_index(struct_name, expr.field)
                    field_ptr = self.builder.gep(local_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                    return self.builder.load(field_ptr)

        struct_val = self._emit_expr(expr.expr)

        # Determine if we're accessing through a pointer or value
        if isinstance(struct_val.type, ir.PointerType):
            # Pointer to struct: load the struct first
            pointee_type = struct_val.type.pointee
            if isinstance(pointee_type, ir.BaseStructType):
                # This is a pointer to a struct type - we need to GEP to the field, then load
                struct_name = self._get_struct_name_from_type(pointee_type)
                if struct_name:
                    # Check for Box implicit deref: if field not on Box, deref through ptr
                    if self._is_box_type(struct_name) and not self._struct_has_field(struct_name, expr.field):
                        inner_type_name = self._get_box_inner_type_name(struct_name)
                        if inner_type_name and self._struct_has_field(inner_type_name, expr.field):
                            # Load the ptr field (index 0 in Box), then access field on pointee
                            ptr_field_ptr = self.builder.gep(struct_val, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
                            inner_ptr = self.builder.load(ptr_field_ptr)
                            # Now access the field on the inner struct
                            idx = self._get_struct_field_index(inner_type_name, expr.field)
                            field_ptr = self.builder.gep(inner_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                            return self.builder.load(field_ptr)

                    idx = self._get_struct_field_index(struct_name, expr.field)
                    # GEP to field
                    field_ptr = self.builder.gep(struct_val, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                    # Load the field value
                    return self.builder.load(field_ptr)
                else:
                    raise ValueError(f"Cannot determine struct type for pointer")
            elif isinstance(pointee_type, ir.PointerType):
                # Pointer to pointer - this means we have a RefType that needs one more deref
                # struct_val is **T, we need to load once to get *T, then GEP into the struct
                inner_pointee = pointee_type.pointee
                if isinstance(inner_pointee, ir.BaseStructType):
                    # Load to get *T from **T
                    struct_ptr = self.builder.load(struct_val)
                    struct_name = self._get_struct_name_from_type(inner_pointee)
                    if struct_name:
                        idx = self._get_struct_field_index(struct_name, expr.field)
                        field_ptr = self.builder.gep(struct_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                        return self.builder.load(field_ptr)
                raise ValueError(f"Cannot access field on double pointer: {pointee_type}")
            else:
                raise ValueError(f"Cannot access field on non-struct pointer: {pointee_type}")
        elif isinstance(struct_val.type, ir.BaseStructType):
            # Value of struct type: extract the field
            struct_name = self._get_struct_name_from_type(struct_val.type)
            if struct_name:
                # Check for Box implicit deref: if field not on Box, deref through ptr
                if self._is_box_type(struct_name) and not self._struct_has_field(struct_name, expr.field):
                    inner_type_name = self._get_box_inner_type_name(struct_name)
                    if inner_type_name and self._struct_has_field(inner_type_name, expr.field):
                        # Extract the ptr field (index 0 in Box)
                        inner_ptr = self.builder.extract_value(struct_val, 0)
                        # Now access the field on the inner struct via the pointer
                        idx = self._get_struct_field_index(inner_type_name, expr.field)
                        field_ptr = self.builder.gep(inner_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                        return self.builder.load(field_ptr)

                idx = self._get_struct_field_index(struct_name, expr.field)
                return self.builder.extract_value(struct_val, idx)
            else:
                raise ValueError(f"Cannot determine struct type for value")
        else:
            raise ValueError(f"Cannot access field on non-struct type: {struct_val.type}")

    def _emit_call(self, call: rast.Call) -> ir.Value:
        """Emit a function call.

        Supports:
        - Direct calls: foo(x, y)
        - Indirect calls through function pointer: fn_ptr(x, y)
        """
        # Handle indirect calls through function pointer variable or parameter
        if isinstance(call.func, rast.Ident):
            fname = call.func.name

            # Check if this is a function pointer (local, parameter, or let binding)
            # The Ritz type is stored in ritz_types, which tells us if it's a FnType
            if fname in self.ritz_types:
                ritz_type = self.ritz_types[fname]
                if isinstance(ritz_type, rast.FnType):
                    # This is a function pointer - indirect call
                    # Get the function pointer value
                    if fname in self.locals:
                        var_ptr, _ = self.locals[fname]
                        fn_ptr = self.builder.load(var_ptr)
                    elif fname in self.params:
                        fn_ptr, _ = self.params[fname]
                    else:
                        raise ValueError(f"Function pointer '{fname}' not found in locals or params")

                    # Emit and convert arguments
                    args = [self._emit_expr(arg) for arg in call.args]
                    converted_args = []
                    for arg_val, param_type in zip(args, ritz_type.params):
                        expected_llvm = self._ritz_type_to_llvm(param_type)
                        converted_args.append(self._convert_type(arg_val, expected_llvm))
                    return self.builder.call(fn_ptr, converted_args)
        else:
            # Non-identifier function expression (e.g., field access returning fn ptr)
            fn_ptr = self._emit_expr(call.func)
            args = [self._emit_expr(arg) for arg in call.args]
            return self.builder.call(fn_ptr, args)

        fname = call.func.name

        # Handle enum variant constructors: Some(x), None, Ok(v), Err(e)
        if fname in self.variant_to_enum:
            return self._emit_enum_variant_constructor(fname, call.args)

        # Handle __builtin_alloca
        if fname == '__builtin_alloca':
            size = self._emit_expr(call.args[0])
            if isinstance(size, ir.Constant):
                return self.builder.alloca(self.i8, size.constant)
            else:
                return self.builder.alloca(self.i8, size)

        # Handle SIMD builtin functions
        simd_result = self._try_emit_simd_builtin(fname, call.args)
        if simd_result is not None:
            return simd_result

        # Handle sizeof builtin - sizeof(Type) -> compile-time size in bytes
        # Usage: sizeof(MyStruct), sizeof(i64), sizeof(*u8)
        if fname == 'sizeof':
            if len(call.args) != 1:
                raise ValueError("sizeof() requires exactly 1 type argument")

            # The argument should be a type expression, parsed as an identifier
            # For sizeof(i32), call.args[0] is Ident("i32")
            # For sizeof(MyStruct), call.args[0] is Ident("MyStruct")
            arg = call.args[0]

            # Try to interpret the argument as a type
            if isinstance(arg, rast.Ident):
                type_name = arg.name
                # Check primitives
                primitives = {
                    'i8': 1, 'u8': 1,
                    'i16': 2, 'u16': 2,
                    'i32': 4, 'u32': 4,
                    'i64': 8, 'u64': 8,
                    'bool': 1,
                }
                if type_name in primitives:
                    return ir.Constant(self.i64, primitives[type_name])

                # Check struct types via registry
                layout = self.struct_registry.get_layout(type_name)
                if layout:
                    return ir.Constant(self.i64, layout.size)

                # Fallback: unknown type, return 8 (pointer size)
                return ir.Constant(self.i64, 8)

            # For more complex type expressions, use the type resolver
            elif hasattr(arg, 'span'):
                # Try to create a NamedType from the identifier
                ritz_ty = rast.NamedType(span=arg.span, name=str(arg))
                size, _ = self._ritz_type_size_and_align(ritz_ty)
                return ir.Constant(self.i64, size)

            raise ValueError(f"sizeof() argument must be a type name, got: {type(arg)}")

        # Handle print builtin - print(string_literal) -> write(1, ptr, len)
        if fname == 'print':
            if len(call.args) == 1:
                arg = call.args[0]
                if isinstance(arg, (rast.StringLit, rast.CStringLit)):
                    s = arg.value
                    # Get or create the string constant
                    str_const = self._get_string_constant(s)
                    # GEP to get i8* pointer to string data
                    ptr = self.builder.gep(str_const, [ir.Constant(self.i64, 0), ir.Constant(self.i64, 0)])
                    length = len(s)
                    # Call write(1, ptr, length) via syscall
                    return self._emit_write_syscall(ir.Constant(self.i64, 1), ptr, ir.Constant(self.i64, length))
                elif isinstance(arg, rast.InterpString):
                    # Handle interpolated string - desugar to print calls
                    return self._emit_interp_string_print(arg)
            raise ValueError("print() requires a single string literal argument")

        # Handle named syscalls
        if fname in ('write', 'read', 'open', 'close', 'nanosleep'):
            return self._emit_syscall(fname, call.args)

        # Handle generic syscallN(num, args...) builtins
        # ONLY match exact builtin names: syscall0-syscall6, __syscall0-__syscall6
        # Don't match other functions that happen to start with "syscall" (e.g., syscall_init)
        syscall_builtins = {'syscall0', 'syscall1', 'syscall2', 'syscall3', 'syscall4', 'syscall5', 'syscall6',
                           '__syscall0', '__syscall1', '__syscall2', '__syscall3', '__syscall4', '__syscall5', '__syscall6'}
        if fname in syscall_builtins:
            return self._emit_generic_syscall(fname, call.args)

        # Look up user-defined function
        if fname in self.functions:
            fn, fn_def = self.functions[fname]

            # Check argument count BEFORE processing
            if len(call.args) != len(fn.function_type.args):
                raise ValueError(f"Function '{fname}' called with {len(call.args)} args but defined with {len(fn.function_type.args)} params")

            # Emit arguments with type conversion and String -> *u8 coercion
            # Also handle RERITZ Borrow semantics - borrowed params need addresses
            args = []
            for i, arg in enumerate(call.args):
                param_def = fn_def.params[i]
                expected_type = fn.function_type.args[i]

                # Check if this parameter is a reference type (@T or @&T in RERITZ, or :& borrow)
                # References pass by pointer - we need to pass the address of the argument
                is_mutable_borrow = hasattr(param_def, 'borrow') and param_def.borrow == rast.Borrow.MUTABLE
                is_ref_type = isinstance(param_def.type, rast.RefType)

                # Check if the argument is already a RefType, PtrType, or explicit address-of
                arg_ritz_type = self._infer_ritz_type(arg)
                arg_is_ref = isinstance(arg_ritz_type, rast.RefType) if arg_ritz_type else False
                # PtrType is compatible with RefType at LLVM level (both are pointers)
                arg_is_ptr = isinstance(arg_ritz_type, rast.PtrType) if arg_ritz_type else False
                # Also check if argument is explicit &x or @x (address-of expression)
                arg_is_addr_of = isinstance(arg, rast.UnaryOp) and arg.op in ('&', '@', '@&', '&mut')

                if is_mutable_borrow or is_ref_type:
                    if arg_is_ref or arg_is_ptr or arg_is_addr_of:
                        # Argument is already a pointer type - just emit it
                        val = self._emit_expr(arg)
                    else:
                        # Reference parameter: emit address of the argument
                        val = self._emit_lvalue_addr(arg)
                else:
                    # Moved/value parameter: emit value normally
                    val = self._emit_expr(arg)

                    # Check for String -> *u8 implicit coercion (Issue #89)
                    arg_ritz_type = self._infer_ritz_type(arg)
                    if (arg_ritz_type and isinstance(arg_ritz_type, rast.NamedType)
                        and arg_ritz_type.name == 'String'
                        and isinstance(expected_type, ir.PointerType)
                        and expected_type.pointee == self.i8):
                        val = self._coerce_string_to_u8_ptr(val, arg)
                    # Check for StrView -> *u8 implicit coercion (RERITZ string literals)
                    elif (arg_ritz_type and isinstance(arg_ritz_type, rast.NamedType)
                          and arg_ritz_type.name == 'StrView'
                          and isinstance(expected_type, ir.PointerType)
                          and expected_type.pointee == self.i8):
                        # Extract ptr field from StrView struct
                        val = self.builder.extract_value(val, 0, name='strview.ptr')
                    else:
                        val = self._convert_type(val, expected_type)
                args.append(val)

            return self.builder.call(fn, args)

        # Look up extern function
        if fname in self.extern_fns:
            fn_type, extern_def = self.extern_fns[fname]

            # Check argument count
            expected_arg_count = len(fn_type.args)
            if extern_def.varargs:
                # For varargs, at least the fixed params must be provided
                if len(call.args) < expected_arg_count:
                    raise ValueError(f"Extern function '{fname}' requires at least {expected_arg_count} args, got {len(call.args)}")
            else:
                if len(call.args) != expected_arg_count:
                    raise ValueError(f"Extern function '{fname}' called with {len(call.args)} args but declared with {expected_arg_count} params")

            # Declare the extern function in LLVM if not already done
            if fname not in self.module.globals:
                fn = ir.Function(self.module, fn_type, name=fname)
            else:
                fn = self.module.globals[fname]

            # Emit arguments with type conversion and String -> *u8 coercion
            args = []
            for i, arg in enumerate(call.args):
                val = self._emit_expr(arg)
                if i < len(fn_type.args):
                    expected_type = fn_type.args[i]
                    # Check for String -> *u8 implicit coercion (Issue #89)
                    arg_ritz_type = self._infer_ritz_type(arg)
                    if (arg_ritz_type and isinstance(arg_ritz_type, rast.NamedType)
                        and arg_ritz_type.name == 'String'
                        and isinstance(expected_type, ir.PointerType)
                        and expected_type.pointee == self.i8):
                        val = self._coerce_string_to_u8_ptr(val, arg)
                    # Check for StrView -> *u8 implicit coercion (RERITZ string literals)
                    elif (arg_ritz_type and isinstance(arg_ritz_type, rast.NamedType)
                          and arg_ritz_type.name == 'StrView'
                          and isinstance(expected_type, ir.PointerType)
                          and expected_type.pointee == self.i8):
                        # Extract ptr field from StrView struct
                        val = self.builder.extract_value(val, 0, name='strview.ptr')
                    else:
                        val = self._convert_type(val, expected_type)
                args.append(val)

            return self.builder.call(fn, args)

        raise ValueError(f"Unknown function: {fname}")

    def _try_emit_simd_builtin(self, fname: str, args: list) -> Optional[ir.Value]:
        """Try to emit a SIMD builtin function.

        Returns the IR value if this is a SIMD builtin, or None otherwise.

        SIMD Builtins:
        - simd_load(ptr: *T) -> vec<N, T>: Aligned vector load (16/32-byte)
        - simd_loadu(ptr: *T) -> vec<N, T>: Unaligned vector load
        - simd_store(ptr: *T, val: vec<N, T>): Aligned vector store
        - simd_storeu(ptr: *T, val: vec<N, T>): Unaligned vector store
        - simd_extract(vec: vec<N, T>, idx: i32) -> T: Extract element
        - simd_insert(vec: vec<N, T>, idx: i32, val: T) -> vec<N, T>: Insert element
        - simd_shuffle(a: vec<N, T>, b: vec<N, T>, mask: ...) -> vec<N, T>: Shuffle elements
        - simd_sad(a: vec<16, i8>, b: vec<16, i8>) -> vec<2, i64>: Sum of absolute differences
        - simd_add(a: vec<N, T>, b: vec<N, T>) -> vec<N, T>: Vector integer addition
        - simd_xor(a: vec<N, T>, b: vec<N, T>) -> vec<N, T>: Vector XOR
        - simd_rotl(v: vec<N, T>, n: i32) -> vec<N, T>: Vector rotate left (constant n)
        """
        # Mark current function as using SIMD if this is a SIMD builtin
        # SIMD functions need alignstack(16) to ensure proper stack alignment
        # for SIMD operations (e.g., movaps requires 16-byte aligned memory)
        if fname.startswith('simd_') and self.current_fn_def:
            self.simd_functions.add(self.current_fn_def.name)

        # Common SIMD vector types for SSE2 (128-bit)
        v16i8 = ir.VectorType(self.i8, 16)
        v8i16 = ir.VectorType(self.i16, 8)
        v4i32 = ir.VectorType(self.i32, 4)
        v2i64 = ir.VectorType(self.i64, 2)
        # AVX2 vector types (256-bit)
        v32i8 = ir.VectorType(self.i8, 32)
        v16i16 = ir.VectorType(self.i16, 16)
        v8i32 = ir.VectorType(self.i32, 8)
        v4i64 = ir.VectorType(self.i64, 4)

        if fname == 'simd_load':
            # simd_load(ptr: *T) -> vec<N, T>
            # Aligned load (16-byte for SSE2, 32-byte for AVX2)
            if len(args) != 1:
                raise ValueError("simd_load() requires exactly 1 argument (pointer)")
            ptr = self._emit_expr(args[0])
            # Determine vector type from pointer element type
            if isinstance(ptr.type, ir.PointerType):
                elem_type = ptr.type.pointee
                # Check if we have an expected type from declaration
                expected = self.simd_expected_type
                is_avx2 = False
                if expected and isinstance(expected, rast.NamedType):
                    type_map = {
                        # SSE2 128-bit
                        'v16i8': v16i8, 'v8i16': v8i16, 'v4i32': v4i32, 'v2i64': v2i64,
                        # AVX2 256-bit
                        'v32i8': v32i8, 'v16i16': v16i16, 'v8i32': v8i32, 'v4i64': v4i64,
                    }
                    vec_type = type_map.get(expected.name)
                    if vec_type is None:
                        raise ValueError(f"simd_load: unsupported expected type {expected.name}")
                    is_avx2 = expected.name in ('v32i8', 'v16i16', 'v8i32', 'v4i64')
                else:
                    # Default to 128-bit vectors (SSE2)
                    if elem_type == self.i8:
                        vec_type = v16i8
                    elif elem_type == self.i16:
                        vec_type = v8i16
                    elif elem_type == self.i32:
                        vec_type = v4i32
                    elif elem_type == self.i64:
                        vec_type = v2i64
                    else:
                        raise ValueError(f"simd_load: unsupported element type {elem_type}")
                # Cast pointer to vector pointer type
                vec_ptr = self.builder.bitcast(ptr, ir.PointerType(vec_type))
                # Aligned load (16-byte for SSE2, 32-byte for AVX2)
                load_instr = self.builder.load(vec_ptr)
                load_instr.align = 32 if is_avx2 else 16
                return load_instr
            raise ValueError("simd_load() requires a pointer argument")

        elif fname == 'simd_loadu':
            # simd_loadu(ptr: *T) -> vec<N, T>
            # Unaligned load (align=1)
            # Determines SSE2 (128-bit) vs AVX2 (256-bit) from expected type context
            if len(args) != 1:
                raise ValueError("simd_loadu() requires exactly 1 argument (pointer)")
            ptr = self._emit_expr(args[0])
            if isinstance(ptr.type, ir.PointerType):
                elem_type = ptr.type.pointee
                # Check if we have an expected type from declaration (e.g., let v: v8i32 = ...)
                expected = self.simd_expected_type
                if expected and isinstance(expected, rast.NamedType):
                    # Use the declared type directly
                    type_map = {
                        # SSE2 128-bit
                        'v16i8': v16i8, 'v8i16': v8i16, 'v4i32': v4i32, 'v2i64': v2i64,
                        # AVX2 256-bit
                        'v32i8': v32i8, 'v16i16': v16i16, 'v8i32': v8i32, 'v4i64': v4i64,
                    }
                    vec_type = type_map.get(expected.name)
                    if vec_type is None:
                        raise ValueError(f"simd_loadu: unsupported expected type {expected.name}")
                else:
                    # Default to SSE2 128-bit vectors based on element type
                    if elem_type == self.i8:
                        vec_type = v16i8
                    elif elem_type == self.i16:
                        vec_type = v8i16
                    elif elem_type == self.i32:
                        vec_type = v4i32
                    elif elem_type == self.i64:
                        vec_type = v2i64
                    else:
                        raise ValueError(f"simd_loadu: unsupported element type {elem_type}")
                vec_ptr = self.builder.bitcast(ptr, ir.PointerType(vec_type))
                load_instr = self.builder.load(vec_ptr)
                load_instr.align = 1  # Unaligned
                return load_instr
            raise ValueError("simd_loadu() requires a pointer argument")

        elif fname == 'simd_store':
            # simd_store(ptr: *T, val: vec<N, T>)
            # Aligned 16-byte store
            if len(args) != 2:
                raise ValueError("simd_store() requires 2 arguments (pointer, value)")
            ptr = self._emit_expr(args[0])
            val = self._emit_expr(args[1])
            if isinstance(ptr.type, ir.PointerType) and isinstance(val.type, ir.VectorType):
                vec_ptr = self.builder.bitcast(ptr, ir.PointerType(val.type))
                store_instr = self.builder.store(val, vec_ptr)
                store_instr.align = 16
                return store_instr
            raise ValueError("simd_store() requires (pointer, vector) arguments")

        elif fname == 'simd_storeu':
            # simd_storeu(ptr: *T, val: vec<N, T>)
            # Unaligned store
            if len(args) != 2:
                raise ValueError("simd_storeu() requires 2 arguments (pointer, value)")
            ptr = self._emit_expr(args[0])
            val = self._emit_expr(args[1])
            if isinstance(ptr.type, ir.PointerType) and isinstance(val.type, ir.VectorType):
                vec_ptr = self.builder.bitcast(ptr, ir.PointerType(val.type))
                store_instr = self.builder.store(val, vec_ptr)
                store_instr.align = 1  # Unaligned
                return store_instr
            raise ValueError("simd_storeu() requires (pointer, vector) arguments")

        elif fname == 'simd_extract':
            # simd_extract(vec: vec<N, T>, idx: i32) -> T
            if len(args) != 2:
                raise ValueError("simd_extract() requires 2 arguments (vector, index)")
            vec = self._emit_expr(args[0])
            idx = self._emit_expr(args[1])
            if isinstance(vec.type, ir.VectorType):
                return self.builder.extract_element(vec, idx)
            raise ValueError("simd_extract() requires a vector argument")

        elif fname == 'simd_insert':
            # simd_insert(vec: vec<N, T>, idx: i32, val: T) -> vec<N, T>
            if len(args) != 3:
                raise ValueError("simd_insert() requires 3 arguments (vector, index, value)")
            vec = self._emit_expr(args[0])
            idx = self._emit_expr(args[1])
            val = self._emit_expr(args[2])
            if isinstance(vec.type, ir.VectorType):
                return self.builder.insert_element(vec, val, idx)
            raise ValueError("simd_insert() requires a vector argument")

        elif fname == 'simd_shuffle':
            # simd_shuffle(a: vec<N, T>, b: vec<N, T>, mask_vals...)
            # Variadic: mask indices follow the two vectors
            # Example: simd_shuffle(a, b, 0, 1, 2, 3) for identity shuffle
            if len(args) < 3:
                raise ValueError("simd_shuffle() requires at least 3 arguments (vec, vec, mask...)")
            vec_a = self._emit_expr(args[0])
            vec_b = self._emit_expr(args[1])
            if not isinstance(vec_a.type, ir.VectorType):
                raise ValueError("simd_shuffle() first argument must be a vector")
            # Build mask from remaining args (must be constants)
            mask_vals = []
            for i, mask_arg in enumerate(args[2:]):
                mask_val = self._emit_expr(mask_arg)
                if isinstance(mask_val, ir.Constant):
                    mask_vals.append(int(mask_val.constant))
                else:
                    raise ValueError(f"simd_shuffle() mask index {i} must be a constant")
            # Create mask as constant vector
            mask_type = ir.VectorType(self.i32, len(mask_vals))
            mask = ir.Constant(mask_type, mask_vals)
            return self.builder.shuffle_vector(vec_a, vec_b, mask)

        elif fname == 'simd_sad':
            # simd_sad(a: vec<16, i8>, b: vec<16, i8>) -> vec<2, i64>
            # Sum of absolute differences: psadbw intrinsic
            # Returns two 64-bit sums (low and high halves)
            if len(args) != 2:
                raise ValueError("simd_sad() requires 2 arguments (vec<16, i8>, vec<16, i8>)")
            vec_a = self._emit_expr(args[0])
            vec_b = self._emit_expr(args[1])
            # Ensure both are v16i8
            if vec_a.type != v16i8 or vec_b.type != v16i8:
                raise ValueError("simd_sad() requires vec<16, i8> arguments")
            # Get or declare llvm.x86.sse2.psad.bw intrinsic
            intrinsic_name = 'llvm.x86.sse2.psad.bw'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v16i8, v16i8])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            return self.builder.call(intrinsic, [vec_a, vec_b])

        elif fname == 'simd_clmul':
            # simd_clmul(a: v2i64, b: v2i64, imm: i8) -> v2i64
            # Carryless multiply: PCLMULQDQ intrinsic for CRC32 acceleration
            #
            # The imm8 selects which 64-bit halves to multiply:
            #   0x00: a[63:0]   * b[63:0]   (low * low)
            #   0x01: a[127:64] * b[63:0]   (high * low)
            #   0x10: a[63:0]   * b[127:64] (low * high)
            #   0x11: a[127:64] * b[127:64] (high * high)
            #
            # IMPORTANT: imm8 MUST be a compile-time constant (immarg constraint)
            # Result is 128-bit carryless product in v2i64.
            if len(args) != 3:
                raise ValueError("simd_clmul() requires 3 arguments (v2i64, v2i64, imm8)")
            vec_a = self._emit_expr(args[0])
            vec_b = self._emit_expr(args[1])

            # The imm8 must be a compile-time constant for PCLMULQDQ
            # Extract the constant value from the AST node directly
            imm_arg = args[2]
            imm_value = None
            if isinstance(imm_arg, rast.IntLit):
                imm_value = imm_arg.value
            elif isinstance(imm_arg, rast.Cast) and isinstance(imm_arg.expr, rast.IntLit):
                imm_value = imm_arg.expr.value
            else:
                raise ValueError("simd_clmul() imm8 must be a compile-time constant integer literal")

            # Validate range
            if imm_value < 0 or imm_value > 255:
                raise ValueError(f"simd_clmul() imm8 must be 0-255, got {imm_value}")

            imm = ir.Constant(self.i8, imm_value)

            # Ensure vectors are v2i64
            if vec_a.type != v2i64 or vec_b.type != v2i64:
                raise ValueError("simd_clmul() requires v2i64 arguments")

            # Get or declare llvm.x86.pclmulqdq intrinsic
            intrinsic_name = 'llvm.x86.pclmulqdq'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v2i64, v2i64, self.i8])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            return self.builder.call(intrinsic, [vec_a, vec_b, imm])

        elif fname == 'simd_add':
            # simd_add(a: vec<N, T>, b: vec<N, T>) -> vec<N, T>
            # Vector integer addition (works for both SSE2 and AVX2)
            if len(args) != 2:
                raise ValueError("simd_add() requires 2 arguments (vector, vector)")
            vec_a = self._emit_expr(args[0])
            vec_b = self._emit_expr(args[1])
            if not isinstance(vec_a.type, ir.VectorType) or not isinstance(vec_b.type, ir.VectorType):
                raise ValueError("simd_add() requires vector arguments")
            if vec_a.type != vec_b.type:
                raise ValueError("simd_add() requires vectors of the same type")
            # LLVM add instruction works on vectors
            return self.builder.add(vec_a, vec_b)

        elif fname == 'simd_xor':
            # simd_xor(a: vec<N, T>, b: vec<N, T>) -> vec<N, T>
            # Vector XOR (works for both SSE2 and AVX2)
            if len(args) != 2:
                raise ValueError("simd_xor() requires 2 arguments (vector, vector)")
            vec_a = self._emit_expr(args[0])
            vec_b = self._emit_expr(args[1])
            if not isinstance(vec_a.type, ir.VectorType) or not isinstance(vec_b.type, ir.VectorType):
                raise ValueError("simd_xor() requires vector arguments")
            if vec_a.type != vec_b.type:
                raise ValueError("simd_xor() requires vectors of the same type")
            # LLVM xor instruction works on vectors
            return self.builder.xor(vec_a, vec_b)

        elif fname == 'simd_rotl':
            # simd_rotl(v: vec<N, T>, n: i32) -> vec<N, T>
            # Vector rotate left by constant amount (for ChaCha20 quarter round)
            # Implemented as: (v << n) | (v >> (bits - n))
            # Note: n must be a compile-time constant for optimal codegen
            if len(args) != 2:
                raise ValueError("simd_rotl() requires 2 arguments (vector, shift)")
            vec = self._emit_expr(args[0])
            if not isinstance(vec.type, ir.VectorType):
                raise ValueError("simd_rotl() requires a vector argument")

            # Extract shift amount (must be constant for efficient codegen)
            shift_arg = args[1]
            if isinstance(shift_arg, rast.IntLit):
                shift_amount = shift_arg.value
            elif isinstance(shift_arg, rast.Cast) and isinstance(shift_arg.expr, rast.IntLit):
                shift_amount = shift_arg.expr.value
            else:
                raise ValueError("simd_rotl() shift amount must be a compile-time constant")

            # Determine element bit width
            elem_type = vec.type.element
            if elem_type == self.i32:
                bits = 32
            elif elem_type == self.i64:
                bits = 64
            elif elem_type == self.i16:
                bits = 16
            elif elem_type == self.i8:
                bits = 8
            else:
                raise ValueError(f"simd_rotl() unsupported element type {elem_type}")

            # Create broadcast vectors for shift amounts
            num_elems = vec.type.count
            left_shift_val = ir.Constant(vec.type, [shift_amount] * num_elems)
            right_shift_val = ir.Constant(vec.type, [bits - shift_amount] * num_elems)

            # rotl(v, n) = (v << n) | (v >> (bits - n))
            left = self.builder.shl(vec, left_shift_val)
            right = self.builder.lshr(vec, right_shift_val)
            return self.builder.or_(left, right)

        elif fname == 'cpuid_raw':
            # cpuid_raw(leaf: u32, subleaf: u32, out_eax: *u32, out_ebx: *u32, out_ecx: *u32, out_edx: *u32) -> void
            # Uses inline assembly to execute CPUID instruction
            # Writes results to the provided output pointers
            if len(args) != 6:
                raise ValueError("cpuid_raw() requires 6 arguments (leaf, subleaf, out_eax, out_ebx, out_ecx, out_edx)")
            leaf = self._emit_expr(args[0])
            subleaf = self._emit_expr(args[1])
            out_eax = self._emit_expr(args[2])
            out_ebx = self._emit_expr(args[3])
            out_ecx = self._emit_expr(args[4])
            out_edx = self._emit_expr(args[5])

            # Convert to i32 if needed
            if leaf.type != self.i32:
                leaf = self.builder.trunc(leaf, self.i32) if leaf.type.width > 32 else self.builder.zext(leaf, self.i32)
            if subleaf.type != self.i32:
                subleaf = self.builder.trunc(subleaf, self.i32) if subleaf.type.width > 32 else self.builder.zext(subleaf, self.i32)

            # Define the result struct type: {i32, i32, i32, i32} for eax, ebx, ecx, edx
            result_type = ir.LiteralStructType([self.i32, self.i32, self.i32, self.i32])

            # CPUID inline asm:
            # Input: eax = leaf, ecx = subleaf
            # Output: eax, ebx, ecx, edx
            # The asm string uses AT&T syntax (cpuid clobbers eax, ebx, ecx, edx)
            asm_str = "cpuid"
            # Constraints: ={eax},={ebx},={ecx},={edx},{eax},{ecx}
            # Output: eax, ebx, ecx, edx (in order)
            # Input: eax (leaf), ecx (subleaf)
            constraints = "={ax},={bx},={cx},={dx},{ax},{cx},~{dirflag},~{fpsr},~{flags}"

            asm_func_ty = ir.FunctionType(result_type, [self.i32, self.i32])
            asm_ir = ir.InlineAsm(asm_func_ty, asm_str, constraints, side_effect=True)
            result = self.builder.call(asm_ir, [leaf, subleaf])

            # Extract and store each register value
            eax = self.builder.extract_value(result, 0)
            ebx = self.builder.extract_value(result, 1)
            ecx = self.builder.extract_value(result, 2)
            edx = self.builder.extract_value(result, 3)

            self.builder.store(eax, out_eax)
            self.builder.store(ebx, out_ebx)
            self.builder.store(ecx, out_ecx)
            self.builder.store(edx, out_edx)

            # Return void (no value)
            return ir.Constant(self.i32, 0)

        elif fname == 'xgetbv':
            # xgetbv(xcr: u32) -> u64
            # Uses inline assembly to execute XGETBV instruction
            # Returns XCR register value (edx:eax combined as u64)
            if len(args) != 1:
                raise ValueError("xgetbv() requires 1 argument (xcr)")
            xcr = self._emit_expr(args[0])

            # Convert to i32 if needed
            if xcr.type != self.i32:
                xcr = self.builder.trunc(xcr, self.i32) if xcr.type.width > 32 else self.builder.zext(xcr, self.i32)

            # XGETBV returns edx:eax as a 64-bit value
            # Input: ecx = xcr number
            # Output: edx:eax (high:low 32-bit parts)
            asm_str = "xgetbv"
            # Use =A constraint to get edx:eax as a single 64-bit value
            constraints = "={ax},={dx},{cx},~{dirflag},~{fpsr},~{flags}"

            # Returns two i32 values that we combine into i64
            result_type = ir.LiteralStructType([self.i32, self.i32])
            asm_func_ty = ir.FunctionType(result_type, [self.i32])
            asm_ir = ir.InlineAsm(asm_func_ty, asm_str, constraints, side_effect=True)
            result = self.builder.call(asm_ir, [xcr])

            # Extract eax (low) and edx (high) and combine into i64
            eax = self.builder.extract_value(result, 0)
            edx = self.builder.extract_value(result, 1)
            eax_64 = self.builder.zext(eax, self.i64)
            edx_64 = self.builder.zext(edx, self.i64)
            edx_shifted = self.builder.shl(edx_64, ir.Constant(self.i64, 32))
            return self.builder.or_(eax_64, edx_shifted)

        # =====================================================================
        # AES-NI: Advanced Encryption Standard New Instructions (ritz#119)
        # =====================================================================

        elif fname == 'aesenc':
            # aesenc(state, key) -> same type as input
            # One round of AES encryption (ShiftRows, SubBytes, MixColumns, AddRoundKey)
            # Accepts v4i32 or v2i64 (both are 128-bit vectors)
            if len(args) != 2:
                raise ValueError("aesenc() requires 2 arguments (state, key)")
            state = self._emit_expr(args[0])
            key = self._emit_expr(args[1])

            # Determine input type and convert to v2i64 for LLVM intrinsic
            input_type = state.type
            if input_type == v4i32:
                state_i64 = self.builder.bitcast(state, v2i64)
                key_i64 = self.builder.bitcast(key, v2i64)
            elif input_type == v2i64:
                state_i64 = state
                key_i64 = key
            else:
                raise ValueError("aesenc() requires v4i32 or v2i64 arguments")

            intrinsic_name = 'llvm.x86.aesni.aesenc'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v2i64, v2i64])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            result = self.builder.call(intrinsic, [state_i64, key_i64])
            # Return same type as input
            if input_type == v4i32:
                return self.builder.bitcast(result, v4i32)
            return result

        elif fname == 'aesenclast':
            # aesenclast(state, key) -> same type as input
            # Final round of AES encryption (ShiftRows, SubBytes, AddRoundKey - no MixColumns)
            if len(args) != 2:
                raise ValueError("aesenclast() requires 2 arguments (state, key)")
            state = self._emit_expr(args[0])
            key = self._emit_expr(args[1])

            input_type = state.type
            if input_type == v4i32:
                state_i64 = self.builder.bitcast(state, v2i64)
                key_i64 = self.builder.bitcast(key, v2i64)
            elif input_type == v2i64:
                state_i64 = state
                key_i64 = key
            else:
                raise ValueError("aesenclast() requires v4i32 or v2i64 arguments")

            intrinsic_name = 'llvm.x86.aesni.aesenclast'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v2i64, v2i64])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            result = self.builder.call(intrinsic, [state_i64, key_i64])
            if input_type == v4i32:
                return self.builder.bitcast(result, v4i32)
            return result

        elif fname == 'aesdec':
            # aesdec(state, key) -> same type as input
            # One round of AES decryption (InvShiftRows, InvSubBytes, InvMixColumns, AddRoundKey)
            if len(args) != 2:
                raise ValueError("aesdec() requires 2 arguments (state, key)")
            state = self._emit_expr(args[0])
            key = self._emit_expr(args[1])

            input_type = state.type
            if input_type == v4i32:
                state_i64 = self.builder.bitcast(state, v2i64)
                key_i64 = self.builder.bitcast(key, v2i64)
            elif input_type == v2i64:
                state_i64 = state
                key_i64 = key
            else:
                raise ValueError("aesdec() requires v4i32 or v2i64 arguments")

            intrinsic_name = 'llvm.x86.aesni.aesdec'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v2i64, v2i64])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            result = self.builder.call(intrinsic, [state_i64, key_i64])
            if input_type == v4i32:
                return self.builder.bitcast(result, v4i32)
            return result

        elif fname == 'aesdeclast':
            # aesdeclast(state, key) -> same type as input
            # Final round of AES decryption (InvShiftRows, InvSubBytes, AddRoundKey - no InvMixColumns)
            if len(args) != 2:
                raise ValueError("aesdeclast() requires 2 arguments (state, key)")
            state = self._emit_expr(args[0])
            key = self._emit_expr(args[1])

            input_type = state.type
            if input_type == v4i32:
                state_i64 = self.builder.bitcast(state, v2i64)
                key_i64 = self.builder.bitcast(key, v2i64)
            elif input_type == v2i64:
                state_i64 = state
                key_i64 = key
            else:
                raise ValueError("aesdeclast() requires v4i32 or v2i64 arguments")

            intrinsic_name = 'llvm.x86.aesni.aesdeclast'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v2i64, v2i64])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            result = self.builder.call(intrinsic, [state_i64, key_i64])
            if input_type == v4i32:
                return self.builder.bitcast(result, v4i32)
            return result

        elif fname == 'aesimc':
            # aesimc(key) -> same type as input
            # AES Inverse MixColumns (for computing decryption round keys)
            # Accepts v4i32 or v2i64 (both are 128-bit vectors)
            if len(args) != 1:
                raise ValueError("aesimc() requires 1 argument (key)")
            key = self._emit_expr(args[0])

            input_type = key.type
            if input_type == v4i32:
                key_i64 = self.builder.bitcast(key, v2i64)
            elif input_type == v2i64:
                key_i64 = key
            else:
                raise ValueError("aesimc() requires v4i32 or v2i64 argument")

            intrinsic_name = 'llvm.x86.aesni.aesimc'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v2i64])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            result = self.builder.call(intrinsic, [key_i64])
            if input_type == v4i32:
                return self.builder.bitcast(result, v4i32)
            return result

        # =====================================================================
        # SHA-NI: SHA Extensions for hardware SHA-256 (ritz#119)
        # =====================================================================

        elif fname == 'sha256rnds2':
            # sha256rnds2(cdgh: v4i32, abef: v4i32, wk: v4i32) -> v4i32
            # Perform two SHA-256 rounds
            # cdgh = state words c,d,g,h; abef = state words a,b,e,f
            # wk = message schedule word + round constant (only low 64 bits used)
            if len(args) != 3:
                raise ValueError("sha256rnds2() requires 3 arguments (cdgh, abef, wk)")
            cdgh = self._emit_expr(args[0])
            abef = self._emit_expr(args[1])
            wk = self._emit_expr(args[2])
            if cdgh.type != v4i32 or abef.type != v4i32 or wk.type != v4i32:
                raise ValueError("sha256rnds2() requires v4i32 arguments")

            intrinsic_name = 'llvm.x86.sha256rnds2'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v4i32, [v4i32, v4i32, v4i32])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            return self.builder.call(intrinsic, [cdgh, abef, wk])

        elif fname == 'sha256msg1':
            # sha256msg1(w0: v4i32, w1: v4i32) -> v4i32
            # SHA-256 message schedule transformation (part 1)
            # Computes sigma0 and adds to message words
            if len(args) != 2:
                raise ValueError("sha256msg1() requires 2 arguments (w0, w1)")
            w0 = self._emit_expr(args[0])
            w1 = self._emit_expr(args[1])
            if w0.type != v4i32 or w1.type != v4i32:
                raise ValueError("sha256msg1() requires v4i32 arguments")

            intrinsic_name = 'llvm.x86.sha256msg1'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v4i32, [v4i32, v4i32])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            return self.builder.call(intrinsic, [w0, w1])

        elif fname == 'sha256msg2':
            # sha256msg2(w0: v4i32, w1: v4i32) -> v4i32
            # SHA-256 message schedule transformation (part 2)
            # Computes sigma1 and completes message expansion
            if len(args) != 2:
                raise ValueError("sha256msg2() requires 2 arguments (w0, w1)")
            w0 = self._emit_expr(args[0])
            w1 = self._emit_expr(args[1])
            if w0.type != v4i32 or w1.type != v4i32:
                raise ValueError("sha256msg2() requires v4i32 arguments")

            intrinsic_name = 'llvm.x86.sha256msg2'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v4i32, [v4i32, v4i32])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            return self.builder.call(intrinsic, [w0, w1])

        # Not a SIMD builtin
        return None

    def _try_emit_bitops_intrinsic(self, expr: rast.MethodCall, type_name: str) -> ir.Value:
        """Try to emit a BitOps intrinsic for primitive integer types.

        Returns the IR value if this is a BitOps method on a primitive,
        or None if it should be handled as a normal method call.

        BitOps methods:
        - rotl(n: u8) -> Self: rotate left
        - rotr(n: u8) -> Self: rotate right
        - clz() -> u8: count leading zeros
        - ctz() -> u8: count trailing zeros
        - popcnt() -> u8: population count (hamming weight)
        - swap_bytes() -> Self: byte swap (endianness conversion)
        """
        # Check if type is a primitive integer
        int_types = {'u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64'}
        if type_name not in int_types:
            return None

        method = expr.method
        bitops_methods = {'rotl', 'rotr', 'clz', 'ctz', 'popcnt', 'swap_bytes'}
        if method not in bitops_methods:
            return None

        # Emit the receiver value
        receiver = self._emit_expr(expr.expr)

        # Get the LLVM type for this integer
        type_bits = {
            'u8': 8, 'i8': 8,
            'u16': 16, 'i16': 16,
            'u32': 32, 'i32': 32,
            'u64': 64, 'i64': 64,
        }
        bits = type_bits[type_name]
        llvm_type = getattr(self, f'i{bits}')

        if method == 'rotl':
            # llvm.fshl.i32(a, a, b) = funnel shift left = rotate left when a == a
            if len(expr.args) != 1:
                raise ValueError(f"rotl() requires exactly 1 argument")
            shift_amount = self._emit_expr(expr.args[0])
            # Convert shift amount to same type as receiver
            shift_amount = self.builder.zext(shift_amount, llvm_type) if shift_amount.type.width < bits else shift_amount
            shift_amount = self.builder.trunc(shift_amount, llvm_type) if shift_amount.type.width > bits else shift_amount
            # Declare and call llvm.fshl intrinsic (need to specify fnty for correct signature)
            fn_type = ir.FunctionType(llvm_type, [llvm_type, llvm_type, llvm_type])
            intrinsic = self.module.declare_intrinsic('llvm.fshl', [llvm_type], fnty=fn_type)
            return self.builder.call(intrinsic, [receiver, receiver, shift_amount])

        elif method == 'rotr':
            # llvm.fshr.i32(a, a, b) = funnel shift right = rotate right when a == a
            if len(expr.args) != 1:
                raise ValueError(f"rotr() requires exactly 1 argument")
            shift_amount = self._emit_expr(expr.args[0])
            shift_amount = self.builder.zext(shift_amount, llvm_type) if shift_amount.type.width < bits else shift_amount
            shift_amount = self.builder.trunc(shift_amount, llvm_type) if shift_amount.type.width > bits else shift_amount
            fn_type = ir.FunctionType(llvm_type, [llvm_type, llvm_type, llvm_type])
            intrinsic = self.module.declare_intrinsic('llvm.fshr', [llvm_type], fnty=fn_type)
            return self.builder.call(intrinsic, [receiver, receiver, shift_amount])

        elif method == 'clz':
            # llvm.ctlz.i32(x, is_zero_poison) -> count leading zeros
            if len(expr.args) != 0:
                raise ValueError(f"clz() takes no arguments")
            fn_type = ir.FunctionType(llvm_type, [llvm_type, ir.IntType(1)])
            intrinsic = self.module.declare_intrinsic('llvm.ctlz', [llvm_type], fnty=fn_type)
            # is_zero_poison = false (return bit width for zero input)
            result = self.builder.call(intrinsic, [receiver, ir.Constant(ir.IntType(1), 0)])
            # Truncate to u8
            return self.builder.trunc(result, self.i8)

        elif method == 'ctz':
            # llvm.cttz.i32(x, is_zero_poison) -> count trailing zeros
            if len(expr.args) != 0:
                raise ValueError(f"ctz() takes no arguments")
            fn_type = ir.FunctionType(llvm_type, [llvm_type, ir.IntType(1)])
            intrinsic = self.module.declare_intrinsic('llvm.cttz', [llvm_type], fnty=fn_type)
            result = self.builder.call(intrinsic, [receiver, ir.Constant(ir.IntType(1), 0)])
            return self.builder.trunc(result, self.i8)

        elif method == 'popcnt':
            # llvm.ctpop.i32(x) -> population count
            if len(expr.args) != 0:
                raise ValueError(f"popcnt() takes no arguments")
            fn_type = ir.FunctionType(llvm_type, [llvm_type])
            intrinsic = self.module.declare_intrinsic('llvm.ctpop', [llvm_type], fnty=fn_type)
            result = self.builder.call(intrinsic, [receiver])
            return self.builder.trunc(result, self.i8)

        elif method == 'swap_bytes':
            # llvm.bswap.i32(x) -> byte swap
            if len(expr.args) != 0:
                raise ValueError(f"swap_bytes() takes no arguments")
            if bits < 16:
                # bswap not defined for i8, just return the value
                return receiver
            fn_type = ir.FunctionType(llvm_type, [llvm_type])
            intrinsic = self.module.declare_intrinsic('llvm.bswap', [llvm_type], fnty=fn_type)
            return self.builder.call(intrinsic, [receiver])

        return None

    def _emit_method_call(self, expr: rast.MethodCall) -> ir.Value:
        """Emit a method call: receiver.method(args...).

        Method calls are desugared to static function calls using name mangling:
        - Type_method(receiver, args...) for inherent methods
        - Trait method calls look up the impl and use Type_method

        With monomorphization, we determine the receiver type at compile time
        and call the appropriate mangled function.

        If the method expects *Self and receiver is a value, we auto-borrow.

        For dyn Trait, we use dynamic dispatch through the vtable.
        """
        # Check if this is a method call on a dyn Trait (dynamic dispatch)
        receiver_type = self._infer_ritz_type(expr.expr)
        if isinstance(receiver_type, rast.DynType):
            return self._emit_dyn_method_call(expr, receiver_type)
        # Also handle reference to dyn Trait
        if isinstance(receiver_type, (rast.RefType, rast.PtrType)):
            if isinstance(receiver_type.inner, rast.DynType):
                return self._emit_dyn_method_call(expr, receiver_type.inner)

        # First, check if the receiver is an lvalue (identifier, field, index)
        # If so, get its address for auto-borrowing when method expects *Self
        receiver_is_lvalue = isinstance(expr.expr, (rast.Ident, rast.Field, rast.Index))

        # Determine receiver type first by peeking at the expression
        # For identifiers, we can look up the type directly
        type_name = None
        if isinstance(expr.expr, rast.Ident):
            name = expr.expr.name
            # First check ritz_types for the original Ritz type (preserves signedness)
            if name in self.ritz_types:
                ritz_type = self.ritz_types[name]
                if isinstance(ritz_type, rast.NamedType):
                    type_name = ritz_type.name
            # Fall back to LLVM type inspection for struct types
            if type_name is None:
                if name in self.locals:
                    alloca, ty = self.locals[name]
                    type_name = self._get_struct_name_from_type(ty)
                elif name in self.params:
                    val, ty = self.params[name]
                    type_name = self._get_struct_name_from_type(ty)

        # Look up the mangled function name (need type_name first)
        if type_name is None:
            # Fall back to emitting the expression and checking its type
            receiver_val = self._emit_expr(expr.expr)
            receiver_type = receiver_val.type
            if isinstance(receiver_type, ir.PointerType):
                type_name = self._get_struct_name_from_type(receiver_type.pointee)
            else:
                type_name = self._get_struct_name_from_type(receiver_type)
                # Also check for primitive integer types (for BitOps support)
                if type_name is None and isinstance(receiver_type, ir.IntType):
                    bits = receiver_type.width
                    # Default to unsigned for BitOps (both signed/unsigned work the same)
                    type_name = f'u{bits}'

        if type_name is None:
            raise ValueError(f"Cannot call method '{expr.method}' on unknown type")

        # Check for BitOps intrinsics on primitive integer types
        bitops_result = self._try_emit_bitops_intrinsic(expr, type_name)
        if bitops_result is not None:
            return bitops_result

        method_key = (type_name, expr.method)
        if method_key in self.method_lookup:
            mangled_name = self.method_lookup[method_key]
        else:
            # Fallback: look for standalone functions with naming convention
            # Vec$u8.len() -> vec_len$u8(&self)
            # String.len() -> string_len(&self)
            # Span$u8.len() -> span_len$u8(&self)
            mangled_name = self._find_method_fallback(type_name, expr.method)
            if mangled_name is None:
                raise ValueError(f"No method '{expr.method}' found for type '{type_name}'")

        if mangled_name not in self.functions:
            raise ValueError(f"Method function '{mangled_name}' not found")

        fn, fn_def = self.functions[mangled_name]
        first_param_type = fn.function_type.args[0]

        # Determine whether to pass by value or by pointer (auto-borrow)
        # If method expects pointer and receiver is lvalue, get address
        receiver_val = None
        if receiver_is_lvalue and isinstance(first_param_type, ir.PointerType):
            # Try to get address of the receiver
            # For `var` bindings, this is the alloca
            # For `let` bindings with struct values, we need special handling
            if isinstance(expr.expr, rast.Ident):
                name = expr.expr.name
                if name in self.locals:
                    # var binding - get the alloca
                    alloca, ty = self.locals[name]
                    # If the local is already a pointer, use it directly
                    if isinstance(ty, ir.PointerType):
                        receiver_val = self.builder.load(alloca)
                    else:
                        receiver_val = alloca
                elif name in self.globals:
                    # global var - get the global variable pointer
                    gvar, ty = self.globals[name]
                    if isinstance(ty, ir.PointerType):
                        receiver_val = self.builder.load(gvar)
                    else:
                        receiver_val = gvar
                elif name in self.params:
                    val, ty = self.params[name]
                    # If param is already a pointer, use it directly
                    if isinstance(ty, ir.PointerType):
                        receiver_val = val
                    else:
                        # let binding with struct value - create temporary storage
                        tmp = self.builder.alloca(ty, name=f"{name}.tmp")
                        self.builder.store(val, tmp)
                        receiver_val = tmp
                else:
                    raise ValueError(f"Unknown variable: {name}")
            else:
                # For other lvalues (field, index), use normal lvalue_addr
                receiver_val = self._emit_lvalue_addr(expr.expr)
        else:
            # Emit as normal expression
            receiver_val = self._emit_expr(expr.expr)

        # Build arguments: receiver first, then explicit args
        all_args = [receiver_val]
        for arg in expr.args:
            all_args.append(self._emit_expr(arg))

        # Convert argument types as needed
        converted_args = []
        for i, arg in enumerate(all_args):
            expected_type = fn.function_type.args[i]
            converted = self._convert_type(arg, expected_type)
            converted_args.append(converted)

        return self.builder.call(fn, converted_args)

    def _emit_dyn_method_call(self, expr: rast.MethodCall, dyn_type: rast.DynType) -> ir.Value:
        """Emit a method call on a dyn Trait using dynamic dispatch.

        Dynamic dispatch works through the vtable:
        1. Extract data pointer and vtable pointer from fat pointer
        2. Look up method function pointer in vtable
        3. Call through function pointer with data as self
        """
        trait_name = dyn_type.trait_name

        # Emit receiver (the fat pointer)
        fat_ptr = self._emit_expr(expr.expr)

        # If fat_ptr is a pointer to dyn struct, load it
        dyn_struct_type = self.dyn_types.get(trait_name)
        if dyn_struct_type and isinstance(fat_ptr.type, ir.PointerType):
            if fat_ptr.type.pointee == dyn_struct_type:
                fat_ptr = self.builder.load(fat_ptr, name='dyn.loaded')

        # Extract data and vtable pointers
        data_ptr = self._extract_data_ptr(fat_ptr)
        vtable_ptr = self._extract_vtable_ptr(fat_ptr)

        # Get method index in vtable
        method_index = self._get_trait_method_index(trait_name, expr.method)

        # Get vtable type for GEP
        vtable_type = self.vtable_types[trait_name]

        # Load method function pointer from vtable
        # vtable_ptr is *vtable.Trait, we need to GEP to get the method slot
        method_ptr_ptr = self.builder.gep(
            vtable_ptr,
            [ir.Constant(self.i32, 0), ir.Constant(self.i32, method_index)],
            name=f'dyn.method.{expr.method}.ptr_ptr'
        )
        method_ptr = self.builder.load(method_ptr_ptr, name=f'dyn.method.{expr.method}.ptr')

        # Build arguments: data_ptr as opaque self, then explicit args
        all_args = [data_ptr]
        for arg in expr.args:
            all_args.append(self._emit_expr(arg))

        # Call through function pointer
        return self.builder.call(method_ptr, all_args, name=f'dyn.call.{expr.method}')

    def _emit_syscall(self, name: str, args: List[rast.Expr]) -> ir.Value:
        """Emit an inline syscall."""
        syscall_nums = {
            'read': SYSCALL_READ,
            'write': SYSCALL_WRITE,
            'open': SYSCALL_OPEN,
            'close': SYSCALL_CLOSE,
            'nanosleep': SYSCALL_NANOSLEEP,
        }
        syscall_num = syscall_nums[name]

        # Emit arguments
        arg_vals = [self._emit_expr(arg) for arg in args]

        # Convert all args to i64
        arg_vals_64 = []
        for val in arg_vals:
            arg_vals_64.append(self._to_i64(val))

        # Build inline asm based on arg count
        if len(arg_vals_64) == 1:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64])
            asm_args = [ir.Constant(self.i64, syscall_num), arg_vals_64[0]]
        elif len(arg_vals_64) == 2:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64])
            asm_args = [ir.Constant(self.i64, syscall_num), arg_vals_64[0], arg_vals_64[1]]
        elif len(arg_vals_64) == 3:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64, self.i64])
            asm_args = [ir.Constant(self.i64, syscall_num)] + arg_vals_64
        else:
            raise ValueError(f"Syscall with {len(arg_vals_64)} args not supported")

        asm_ir = ir.InlineAsm(asm_func_ty, asm_str, constraints, side_effect=True)
        result = self.builder.call(asm_ir, asm_args)

        # Truncate result if needed (e.g., open returns i32)
        if name in ('open', 'close'):
            result = self.builder.trunc(result, self.i32)

        return result

    def _emit_generic_syscall(self, fname: str, args: List[rast.Expr]) -> ir.Value:
        """Emit a generic syscallN(num, arg1, ...) call.

        syscall1(num, arg1) - 1 arg syscall
        syscall2(num, arg1, arg2) - 2 arg syscall
        syscall3(num, arg1, arg2, arg3) - 3 arg syscall
        syscall4(num, arg1, arg2, arg3, arg4) - 4 arg syscall
        """
        # Emit all arguments
        arg_vals = [self._emit_expr(arg) for arg in args]

        # First arg is the syscall number
        if not arg_vals:
            raise ValueError(f"{fname} requires at least a syscall number")

        syscall_num = self._to_i64(arg_vals[0])

        # Remaining args are the syscall arguments
        syscall_args = [self._to_i64(v) for v in arg_vals[1:]]

        if len(syscall_args) == 0:
            # syscall with no args (just the number)
            asm_str = "syscall"
            constraints = "=&{rax},{rax},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64])
            asm_args = [syscall_num]
        elif len(syscall_args) == 1:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64])
            asm_args = [syscall_num, syscall_args[0]]
        elif len(syscall_args) == 2:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64])
            asm_args = [syscall_num, syscall_args[0], syscall_args[1]]
        elif len(syscall_args) == 3:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64, self.i64])
            asm_args = [syscall_num] + syscall_args
        elif len(syscall_args) == 4:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64, self.i64, self.i64])
            asm_args = [syscall_num] + syscall_args
        elif len(syscall_args) == 5:
            # 5 args: rdi, rsi, rdx, r10, r8
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},{rdx},{r10},{r8},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64, self.i64, self.i64, self.i64])
            asm_args = [syscall_num] + syscall_args
        elif len(syscall_args) == 6:
            # 6 args: rdi, rsi, rdx, r10, r8, r9 (e.g., mmap)
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},{rdx},{r10},{r8},{r9},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64, self.i64, self.i64, self.i64, self.i64])
            asm_args = [syscall_num] + syscall_args
        else:
            raise ValueError(f"Syscall with {len(syscall_args)} args not supported (max 6)")

        asm_ir = ir.InlineAsm(asm_func_ty, asm_str, constraints, side_effect=True)
        return self.builder.call(asm_ir, asm_args)

    def _emit_write_syscall(self, fd: ir.Value, buf: ir.Value, count: ir.Value) -> ir.Value:
        """Emit a write syscall (fd, buf, count) -> bytes written."""
        # Convert args to i64
        fd_64 = self._to_i64(fd)
        buf_64 = self._to_i64(buf)
        count_64 = self._to_i64(count)

        asm_str = "syscall"
        constraints = "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"
        asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64, self.i64])
        asm_args = [ir.Constant(self.i64, SYSCALL_WRITE), fd_64, buf_64, count_64]

        asm_ir = ir.InlineAsm(asm_func_ty, asm_str, constraints, side_effect=True)
        return self.builder.call(asm_ir, asm_args)

    def _to_i64(self, val: ir.Value) -> ir.Value:
        """Convert a value to i64."""
        if val.type == self.i64:
            return val
        elif isinstance(val.type, ir.IntType):
            return self.builder.sext(val, self.i64)
        elif isinstance(val.type, ir.PointerType):
            return self.builder.ptrtoint(val, self.i64)
        else:
            raise ValueError(f"Cannot convert {val.type} to i64")

    def _convert_type(self, val: ir.Value, target_type: ir.Type) -> ir.Value:
        """Convert a value to the target type if needed."""
        if val.type == target_type:
            return val

        # Integer conversions
        if isinstance(val.type, ir.IntType) and isinstance(target_type, ir.IntType):
            if val.type.width < target_type.width:
                # Use zext for i1 (boolean) to preserve 0/1, sext for other integers
                if val.type.width == 1:
                    return self.builder.zext(val, target_type)
                return self.builder.sext(val, target_type)
            elif val.type.width > target_type.width:
                return self.builder.trunc(val, target_type)

        # Pointer to integer
        if isinstance(val.type, ir.PointerType) and isinstance(target_type, ir.IntType):
            return self.builder.ptrtoint(val, target_type)

        # Integer to pointer
        if isinstance(val.type, ir.IntType) and isinstance(target_type, ir.PointerType):
            return self.builder.inttoptr(val, target_type)

        # Pointer to pointer (bitcast)
        if isinstance(val.type, ir.PointerType) and isinstance(target_type, ir.PointerType):
            return self.builder.bitcast(val, target_type)

        # Array type conversion: [N x T1] to [N x T2]
        if isinstance(val.type, ir.ArrayType) and isinstance(target_type, ir.ArrayType):
            if val.type.count == target_type.count:
                count = val.type.count

                # For small arrays, use zeroinitializer for zero fills or element-by-element
                if count <= 64:
                    # Optimization: If source is zeroinitializer, use zeroinitializer of target type
                    if (isinstance(val, ir.Constant) and
                        val.constant is None and  # zeroinitializer
                        isinstance(target_type.element, (ir.IntType, ir.FloatType, ir.DoubleType, ir.PointerType))):
                        return ir.Constant(target_type, None)

                    # For small arrays, convert element by element (O(N) IR but N is small)
                    result = ir.Constant(target_type, ir.Undefined)
                    for i in range(count):
                        elem = self.builder.extract_value(val, i)
                        converted_elem = self._convert_type(elem, target_type.element)
                        result = self.builder.insert_value(result, converted_elem, i)
                    return result

                # For large arrays, we need to avoid generating huge IR or crashing LLVM
                arr_alloca = self.builder.alloca(target_type)

                # If source is zeroinitializer, use memset instead of storing the constant
                # (storing large zeroinitializer crashes LLVM SelectionDAG)
                if isinstance(val, ir.Constant) and val.constant is None:
                    ptr = self.builder.bitcast(arr_alloca, self.i8.as_pointer())
                    elem_size = self._sizeof_type(target_type.element)
                    total_bytes = elem_size * count
                    byte_val = ir.Constant(self.i8, 0)
                    byte_count = ir.Constant(self.i64, total_bytes)
                    self._emit_memset(ptr, byte_val, byte_count)
                else:
                    # For other values, allocate and use a conversion loop
                    src_alloca = self.builder.alloca(val.type)
                    self.builder.store(val, src_alloca)
                    self._emit_array_convert_loop(src_alloca, arr_alloca, val.type, target_type)

                return self.builder.load(arr_alloca)

        return val

    def _is_unsigned_type(self, ty: rast.Type) -> bool:
        """Check if a Ritz type is unsigned."""
        if isinstance(ty, rast.NamedType):
            return ty.name in ('u8', 'u16', 'u32', 'u64')
        return False

    def _infer_unsigned_expr(self, expr: rast.Expr) -> bool:
        """Check if an expression produces an unsigned integer type.

        This is used to determine whether to use zext (unsigned) or sext (signed)
        when widening integers, and whether to use icmp_unsigned vs icmp_signed
        for comparisons.
        """
        # Character literals are u8 (unsigned)
        if isinstance(expr, rast.CharLit):
            return True

        # Identifier - check stored type
        if isinstance(expr, rast.Ident):
            if expr.name in self.ritz_types:
                return self._is_unsigned_type(self.ritz_types[expr.name])
            return False

        # Cast expression - check the target type (what we're casting TO)
        if isinstance(expr, rast.Cast):
            return self._is_unsigned_type(expr.target)

        # Dereference of pointer to unsigned type
        if isinstance(expr, rast.UnaryOp) and expr.op == '*':
            # Check inner expression type
            inner = expr.operand
            if isinstance(inner, rast.Ident):
                if inner.name in self.ritz_types:
                    ritz_type = self.ritz_types[inner.name]
                    if isinstance(ritz_type, rast.PtrType):
                        return self._is_unsigned_type(ritz_type.inner)
            # Pointer arithmetic: (ptr + offset) where ptr is *u8
            if isinstance(inner, rast.BinOp) and inner.op == '+':
                if isinstance(inner.left, rast.Ident):
                    if inner.left.name in self.ritz_types:
                        ritz_type = self.ritz_types[inner.left.name]
                        if isinstance(ritz_type, rast.PtrType):
                            return self._is_unsigned_type(ritz_type.inner)
            return False

        # Index into unsigned array or pointer
        if isinstance(expr, rast.Index):
            if isinstance(expr.expr, rast.Ident):
                if expr.expr.name in self.ritz_types:
                    ritz_type = self.ritz_types[expr.expr.name]
                    if isinstance(ritz_type, rast.ArrayType):
                        return self._is_unsigned_type(ritz_type.inner)
                    # Also handle pointer indexing: ptr[idx] where ptr is *u8
                    if isinstance(ritz_type, rast.PtrType):
                        return self._is_unsigned_type(ritz_type.inner)
            # Handle struct field array indexing: s.data[0] where data is [N]u8
            # Issue #98: This case was missing, causing sext instead of zext
            elif isinstance(expr.expr, rast.Field):
                field_type = self._get_field_type(expr.expr)
                if field_type:
                    if isinstance(field_type, rast.ArrayType):
                        return self._is_unsigned_type(field_type.inner)
                    if isinstance(field_type, rast.PtrType):
                        return self._is_unsigned_type(field_type.inner)
            return False

        # Field access - check struct field type
        if isinstance(expr, rast.Field):
            if isinstance(expr.expr, rast.Ident):
                if expr.expr.name in self.ritz_types:
                    struct_type = self.ritz_types[expr.expr.name]
                    struct_name = None
                    if isinstance(struct_type, rast.NamedType):
                        struct_name = struct_type.name
                    elif isinstance(struct_type, rast.PtrType) and isinstance(struct_type.inner, rast.NamedType):
                        struct_name = struct_type.inner.name
                    if struct_name and struct_name in self.struct_fields:
                        for field_name, field_type in self.struct_fields[struct_name]:
                            if field_name == expr.field:
                                return self._is_unsigned_type(field_type)
            return False

        return False

    def _is_float_type(self, llvm_ty: ir.Type) -> bool:
        """Check if an LLVM type is a floating-point type."""
        return isinstance(llvm_ty, (ir.FloatType, ir.DoubleType))

    def _infer_float_expr(self, expr: rast.Expr) -> bool:
        """Check if an expression produces a floating-point type.

        This is used to determine whether to use float operations (fadd, fmul, etc.)
        vs integer operations (add, mul, etc.).
        """
        # Float literals are always f64
        if isinstance(expr, rast.FloatLit):
            return True

        # Identifier - check stored type
        if isinstance(expr, rast.Ident):
            if expr.name in self.ritz_types:
                ritz_type = self.ritz_types[expr.name]
                if isinstance(ritz_type, rast.NamedType):
                    return ritz_type.name in ('f32', 'f64')
            return False

        # Cast expression - check the target type
        if isinstance(expr, rast.Cast):
            if isinstance(expr.target, rast.NamedType):
                return expr.target.name in ('f32', 'f64')
            return False

        # Binary operation - if either operand is float, result is float
        if isinstance(expr, rast.BinOp):
            return self._infer_float_expr(expr.left) or self._infer_float_expr(expr.right)

        # Field access - check field type
        if isinstance(expr, rast.FieldAccess):
            if isinstance(expr.expr, rast.Ident):
                struct_name = expr.expr.name
                if struct_name in self.ritz_types:
                    ritz_type = self.ritz_types[struct_name]
                    if isinstance(ritz_type, rast.NamedType):
                        struct_name = ritz_type.name
                if struct_name in self.struct_fields:
                    for field_name, field_type in self.struct_fields[struct_name]:
                        if field_name == expr.field:
                            if isinstance(field_type, rast.NamedType):
                                return field_type.name in ('f32', 'f64')
            return False

        return False

    def _emit_match(self, expr: rast.Match) -> ir.Value:
        """Emit a match expression.

        For union types with TypePattern arms, generates a switch on the tag.
        For enum types with VariantPattern arms, generates a switch on the tag.
        Each arm extracts the appropriate type from the union/enum data.
        """
        # Emit the match expression
        match_val = self._emit_expr(expr.expr)

        # Check if matching on a union type
        union_name = self._get_union_name_from_expr(expr.expr)
        if union_name and union_name in self.union_types:
            return self._emit_union_match(expr, match_val, union_name)

        # Check if matching on an enum type
        enum_name = self._get_enum_name_from_expr(expr.expr)
        if enum_name and enum_name in self.enum_types:
            return self._emit_enum_match(expr, match_val, enum_name)

        # Check if matching on an integer type
        if isinstance(match_val.type, ir.IntType):
            return self._emit_integer_match(expr, match_val)

        raise NotImplementedError(f"Match on type {match_val.type} not yet supported")

    def _emit_union_match(self, expr: rast.Match, union_val: ir.Value, union_name: str) -> ir.Value:
        """Emit a match on a union type with TypePattern arms."""
        union_type, variants = self.union_types[union_name]

        # Store union to memory so we can extract tag and data
        union_alloca = self.builder.alloca(union_type, name="match.union")
        self.builder.store(union_val, union_alloca)

        # Load the tag
        tag_ptr = self.builder.gep(union_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        tag = self.builder.load(tag_ptr)

        # Create blocks for each arm and the merge block
        arm_blocks = []
        for i, arm in enumerate(expr.arms):
            block = self.current_fn.append_basic_block(f"match.arm.{i}")
            arm_blocks.append(block)

        merge_block = self.current_fn.append_basic_block("match.merge")

        # Create an unreachable default block (should never be reached in well-typed code)
        unreachable_block = self.current_fn.append_basic_block("match.unreachable")
        default_block = unreachable_block

        # Build switch instruction
        switch = self.builder.switch(tag, default_block)

        # Add cases for each TypePattern arm
        arm_values = []
        arm_exit_blocks = []

        for i, (arm, arm_block) in enumerate(zip(expr.arms, arm_blocks)):
            pattern = arm.pattern

            if isinstance(pattern, rast.TypePattern):
                # Find the tag for this type
                tag_val = self._get_union_tag_for_type(union_name, pattern.type)
                switch.add_case(ir.Constant(self.i8, tag_val), arm_block)
            elif isinstance(pattern, rast.WildcardPattern):
                # Wildcard matches any remaining - becomes default
                switch.default = arm_block
            else:
                raise NotImplementedError(f"Pattern type {type(pattern)} not supported in union match")

        # Emit the unreachable block
        self.builder.position_at_end(unreachable_block)
        self.builder.unreachable()

        # Emit each arm body
        for i, (arm, arm_block) in enumerate(zip(expr.arms, arm_blocks)):
            self.builder.position_at_end(arm_block)

            # Emit the arm body (which may include casts like `x as i32`)
            arm_val = self._emit_expr(arm.body)
            arm_values.append(arm_val)

            # Remember which block we're in after emitting the body
            if not self.builder.block.is_terminated:
                arm_exit_blocks.append(self.builder.block)
                self.builder.branch(merge_block)
            else:
                arm_exit_blocks.append(None)

        # Position at merge block
        self.builder.position_at_end(merge_block)

        # Create phi node for the result if arms have values
        if arm_values and arm_exit_blocks:
            # Filter out terminated blocks (those that returned)
            incoming = [(val, block) for val, block in zip(arm_values, arm_exit_blocks) if block is not None]
            if incoming:
                # Find the common type for all arms
                # For integer types, use the widest type
                common_type = incoming[0][0].type
                for val, _ in incoming[1:]:
                    if isinstance(val.type, ir.IntType) and isinstance(common_type, ir.IntType):
                        if val.type.width > common_type.width:
                            common_type = val.type

                # Create phi node with the common type
                phi = self.builder.phi(common_type)
                for val, block in incoming:
                    # Convert value to common type if needed
                    if val.type != common_type:
                        val = self._convert_type(val, common_type)
                    phi.add_incoming(val, block)
                return phi

        # Return a dummy value if no arms produce values
        return ir.Constant(self.i32, 0)

    def _emit_enum_match(self, expr: rast.Match, enum_val: ir.Value, enum_name: str) -> ir.Value:
        """Emit a match on an enum type with VariantPattern arms.

        For Option<i32> match:
            match opt
                Some(x) -> x + 1
                None -> 0

        Generates:
            1. Store enum value to memory
            2. Load tag byte
            3. Switch on tag to arm blocks
            4. In each arm, extract payload if needed and bind to pattern variables
            5. Evaluate arm body
            6. Jump to merge block
            7. Phi node for result
        """
        enum_type, variants = self.enum_types[enum_name]

        # Store enum to memory so we can extract tag and data
        enum_alloca = self.builder.alloca(enum_type, name="match.enum")
        self.builder.store(enum_val, enum_alloca)

        # Load the tag
        tag_ptr = self.builder.gep(enum_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        tag = self.builder.load(tag_ptr)

        # Create blocks for each arm and the merge block
        arm_blocks = []
        for i, arm in enumerate(expr.arms):
            block = self.current_fn.append_basic_block(f"match.arm.{i}")
            arm_blocks.append(block)

        merge_block = self.current_fn.append_basic_block("match.merge")

        # Create an unreachable default block (should never be reached in well-typed code)
        unreachable_block = self.current_fn.append_basic_block("match.unreachable")
        default_block = unreachable_block

        # Build switch instruction
        switch = self.builder.switch(tag, default_block)

        # Add cases for each VariantPattern arm
        for i, (arm, arm_block) in enumerate(zip(expr.arms, arm_blocks)):
            pattern = arm.pattern

            if isinstance(pattern, rast.VariantPattern):
                # Find the tag for this variant
                tag_val = self._get_enum_variant_tag(enum_name, pattern.name)
                switch.add_case(ir.Constant(self.i8, tag_val), arm_block)
            elif isinstance(pattern, rast.IdentPattern):
                # IdentPattern with a variant name (e.g., just `None` without parens)
                if pattern.name in self.variant_to_enum:
                    tag_val = self._get_enum_variant_tag(enum_name, pattern.name)
                    switch.add_case(ir.Constant(self.i8, tag_val), arm_block)
                else:
                    # This is a catch-all binding - becomes default
                    switch.default = arm_block
            elif isinstance(pattern, rast.WildcardPattern):
                # Wildcard matches any remaining - becomes default
                switch.default = arm_block
            else:
                raise NotImplementedError(f"Pattern type {type(pattern)} not supported in enum match")

        # Emit the unreachable block
        self.builder.position_at_end(unreachable_block)
        self.builder.unreachable()

        # Emit each arm body
        arm_values = []
        arm_exit_blocks = []

        for i, (arm, arm_block) in enumerate(zip(expr.arms, arm_blocks)):
            self.builder.position_at_end(arm_block)
            pattern = arm.pattern

            # Bind pattern variables if this is a VariantPattern with fields
            if isinstance(pattern, rast.VariantPattern) and pattern.fields:
                variant = self._get_enum_variant(enum_name, pattern.name)

                # Get pointer to data buffer (index depends on alignment padding)
                data_index = self._get_enum_data_index(enum_name)
                data_ptr = self.builder.gep(enum_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, data_index)])

                # Extract and bind each field
                offset = 0
                for j, (field_pattern, field_type) in enumerate(zip(pattern.fields, variant.fields)):
                    llvm_field_type = self._ritz_type_to_llvm(field_type)

                    # Cast data buffer to pointer to field type at offset
                    field_ptr = self.builder.bitcast(
                        self.builder.gep(data_ptr, [ir.Constant(self.i32, offset)]),
                        ir.PointerType(llvm_field_type)
                    )
                    field_val = self.builder.load(field_ptr)

                    # Bind the field value to the pattern variable
                    if isinstance(field_pattern, rast.IdentPattern):
                        # Store in params so it can be used in the arm body
                        self.params[field_pattern.name] = (field_val, llvm_field_type)
                    # Wildcard patterns just discard the value

                    offset += self._type_size_bytes(llvm_field_type)

            # Emit the arm body
            arm_val = self._emit_expr(arm.body)

            # Remember which block we're in after emitting the body
            if not self.builder.block.is_terminated:
                arm_exit_blocks.append(self.builder.block)
                arm_values.append(arm_val)
                self.builder.branch(merge_block)
            else:
                arm_exit_blocks.append(None)

            # Clean up bound variables
            if isinstance(pattern, rast.VariantPattern) and pattern.fields:
                for field_pattern in pattern.fields:
                    if isinstance(field_pattern, rast.IdentPattern):
                        del self.params[field_pattern.name]

        # Position at merge block
        self.builder.position_at_end(merge_block)

        # Create phi node for the result if arms have values
        if arm_values and arm_exit_blocks:
            # Filter out terminated blocks (those that returned)
            incoming = [(val, block) for val, block in zip(arm_values, arm_exit_blocks) if block is not None]
            if incoming:
                # All values should have the same type (or be convertible)
                # For now assume they're all the same type
                phi = self.builder.phi(incoming[0][0].type)
                for val, block in incoming:
                    phi.add_incoming(val, block)
                return phi

        # Return a dummy value if no arms produce values
        return ir.Constant(self.i32, 0)

    def _emit_integer_match(self, expr: rast.Match, match_val: ir.Value) -> ir.Value:
        """Emit a match on an integer type with literal or wildcard patterns.

        match x
            0 => "zero"
            1 => "one"
            _ => "other"

        Generates a switch instruction with cases for each literal pattern
        and a default case for wildcard/identifier patterns.
        """
        int_type = match_val.type

        # Create blocks for each arm and the merge block
        arm_blocks = []
        for i, arm in enumerate(expr.arms):
            block = self.current_fn.append_basic_block(f"match.arm.{i}")
            arm_blocks.append(block)

        merge_block = self.current_fn.append_basic_block("match.merge")

        # Find the default arm (wildcard or catch-all identifier that's not a constant)
        default_block = None
        default_arm_idx = None
        for i, arm in enumerate(expr.arms):
            if isinstance(arm.pattern, rast.WildcardPattern):
                default_block = arm_blocks[i]
                default_arm_idx = i
                break
            elif isinstance(arm.pattern, rast.IdentPattern):
                # IdentPattern is a catch-all ONLY if it's not a constant reference
                if arm.pattern.name not in self.constants:
                    default_block = arm_blocks[i]
                    default_arm_idx = i
                    break

        # If no default, create an unreachable block
        if default_block is None:
            unreachable_block = self.current_fn.append_basic_block("match.unreachable")
            default_block = unreachable_block

        # Build switch instruction
        switch = self.builder.switch(match_val, default_block)

        # Add cases for each literal pattern
        for i, (arm, arm_block) in enumerate(zip(expr.arms, arm_blocks)):
            pattern = arm.pattern

            if isinstance(pattern, rast.LitPattern):
                # Get the literal value
                lit_val = pattern.value
                if isinstance(lit_val, int):
                    case_val = ir.Constant(int_type, lit_val)
                    switch.add_case(case_val, arm_block)
                elif isinstance(lit_val, str) and len(lit_val) == 1:
                    # Character literal
                    case_val = ir.Constant(int_type, ord(lit_val))
                    switch.add_case(case_val, arm_block)
                else:
                    raise NotImplementedError(f"Literal pattern type not supported: {type(lit_val)}")
            elif isinstance(pattern, rast.IdentPattern):
                # Check if this is a constant reference
                if pattern.name in self.constants:
                    # Constants are stored as (value, type) tuples
                    val, ty = self.constants[pattern.name]
                    if isinstance(ty, ir.IntType):
                        # Create LLVM constant with the match value's type
                        case_val = ir.Constant(int_type, val)
                        switch.add_case(case_val, arm_block)
                # Otherwise it's a catch-all (handled as default above)
            # WildcardPattern is handled as default above

        # Emit the unreachable block if we created one
        if default_arm_idx is None:
            self.builder.position_at_end(default_block)
            self.builder.unreachable()

        # Emit each arm body
        arm_values = []
        arm_exit_blocks = []

        for i, (arm, arm_block) in enumerate(zip(expr.arms, arm_blocks)):
            self.builder.position_at_end(arm_block)
            pattern = arm.pattern

            # Bind identifier pattern to the match value
            if isinstance(pattern, rast.IdentPattern) and pattern.name not in self.constants:
                # Bind the match value to the pattern name for use in the arm body
                self.params[pattern.name] = (match_val, int_type)

            # Emit the arm body
            arm_val = self._emit_expr(arm.body)
            arm_values.append(arm_val)

            # Check if the arm already terminated (e.g., with return)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_block)
                arm_exit_blocks.append(self.builder.block)
            else:
                arm_exit_blocks.append(None)

            # Clean up bound pattern variable
            if isinstance(pattern, rast.IdentPattern) and pattern.name not in self.constants:
                del self.params[pattern.name]

        # Position at merge block
        self.builder.position_at_end(merge_block)

        # Create phi node for the result if arms have values
        if arm_values and arm_exit_blocks:
            # Filter out terminated blocks (those that returned)
            incoming = [(val, block) for val, block in zip(arm_values, arm_exit_blocks) if block is not None]
            if incoming:
                phi = self.builder.phi(incoming[0][0].type)
                for val, block in incoming:
                    phi.add_incoming(val, block)
                return phi

        # Return a dummy value if no arms produce values
        return ir.Constant(self.i32, 0)

    def _emit_try_op(self, expr: rast.TryOp) -> ir.Value:
        """Emit the try operator: expr?

        For Result<T, E>:
        - If expr is Ok(v), return v
        - If expr is Err(e), return early from the function with Err(e)

        The enclosing function must return Result<_, E> with the same error type.
        """
        # Emit the inner expression
        result_val = self._emit_expr(expr.expr)

        # Get the enum name from the expression type
        enum_name = self._get_enum_name_from_expr(expr.expr)
        if not enum_name:
            raise ValueError(f"Try operator requires a Result type, got expression: {type(expr.expr)}")

        if not enum_name.startswith("Result$"):
            raise ValueError(f"Try operator requires a Result type, got: {enum_name}")

        # Get the Result type info
        enum_type, variants = self.enum_types[enum_name]

        # Store result to memory so we can extract tag and data
        result_alloca = self.builder.alloca(enum_type, name="try.result")
        self.builder.store(result_val, result_alloca)

        # Load the tag
        tag_ptr = self.builder.gep(result_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        tag = self.builder.load(tag_ptr)

        # Create blocks for Ok and Err cases
        ok_block = self.current_fn.append_basic_block("try.ok")
        err_block = self.current_fn.append_basic_block("try.err")
        merge_block = self.current_fn.append_basic_block("try.merge")

        # Result<T, E> has tag 0 = Ok, tag 1 = Err
        is_ok = self.builder.icmp_unsigned('==', tag, ir.Constant(self.i8, 0))
        self.builder.cbranch(is_ok, ok_block, err_block)

        # Err block: return early with Err(e)
        self.builder.position_at_end(err_block)

        # Get the function's return type - must also be a Result
        ret_type = self.current_fn.function_type.return_type
        ret_ritz_type = self.current_fn_def.ret_type if self.current_fn_def else None

        # Extract the Err payload from the result
        # Get the Err variant's field type
        err_variant = next((v for v in variants if v.name == "Err"), None)
        if not err_variant or not err_variant.fields:
            raise ValueError(f"Result type {enum_name} has no Err variant with payload")

        err_field_type = err_variant.fields[0]
        llvm_err_type = self._ritz_type_to_llvm(err_field_type)

        # Get pointer to data buffer (index depends on alignment padding)
        data_index = self._get_enum_data_index(enum_name)
        data_ptr = self.builder.gep(result_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, data_index)])
        err_ptr = self.builder.bitcast(data_ptr, ir.PointerType(llvm_err_type))
        err_val = self.builder.load(err_ptr)

        # Create the Err result to return
        # We need to construct a Result<T', E> where T' is the function's return type's Ok payload
        # The function return type should be Result_X_Y where Y matches our E
        fn_ret_type_name = None
        if isinstance(ret_ritz_type, rast.NamedType):
            if ret_ritz_type.args:
                # Generic instantiation like Result<i32, i32>
                fn_ret_type_name = self._get_specialized_type_name(ret_ritz_type)
            else:
                # Simple named type (already monomorphized)
                fn_ret_type_name = ret_ritz_type.name

        if not fn_ret_type_name or fn_ret_type_name not in self.enum_types:
            raise ValueError(f"Try operator used in function not returning Result type (got {fn_ret_type_name})")

        fn_ret_enum_type, _ = self.enum_types[fn_ret_type_name]

        # Create a new Result with Err variant
        ret_alloca = self.builder.alloca(fn_ret_enum_type, name="try.ret")

        # Set tag to 1 (Err)
        ret_tag_ptr = self.builder.gep(ret_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        self.builder.store(ir.Constant(self.i8, 1), ret_tag_ptr)

        # Store the error value (use data index for the return type enum)
        ret_data_index = self._get_enum_data_index(fn_ret_type_name)
        ret_data_ptr = self.builder.gep(ret_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, ret_data_index)])
        ret_err_ptr = self.builder.bitcast(ret_data_ptr, ir.PointerType(llvm_err_type))
        self.builder.store(err_val, ret_err_ptr)

        # Load the result and return
        ret_val = self.builder.load(ret_alloca)

        # Emit drops before early return (no variable to exclude)
        self._emit_drop_for_all_scopes(None)
        self.builder.ret(ret_val)

        # Ok block: extract the Ok payload and continue
        self.builder.position_at_end(ok_block)

        # Get the Ok variant's field type
        ok_variant = next((v for v in variants if v.name == "Ok"), None)
        if not ok_variant or not ok_variant.fields:
            raise ValueError(f"Result type {enum_name} has no Ok variant with payload")

        ok_field_type = ok_variant.fields[0]
        llvm_ok_type = self._ritz_type_to_llvm(ok_field_type)

        # Extract the Ok payload (reuse data_index from earlier)
        ok_data_ptr = self.builder.gep(result_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, data_index)])
        ok_ptr = self.builder.bitcast(ok_data_ptr, ir.PointerType(llvm_ok_type))
        ok_val = self.builder.load(ok_ptr)

        # Branch to merge with the Ok value
        self.builder.branch(merge_block)
        ok_exit = self.builder.block

        # Merge block: phi node for the Ok value
        self.builder.position_at_end(merge_block)
        phi = self.builder.phi(llvm_ok_type, name="try.val")
        phi.add_incoming(ok_val, ok_exit)

        return phi

    def _get_specialized_type_name(self, ty: rast.NamedType) -> str:
        """Get the specialized name for a generic type (e.g., Result<i32, i32> -> Result$i32_i32)."""
        base = ty.name
        arg_parts = []
        for arg in ty.args:
            arg_parts.append(self._type_to_name_suffix(arg))
        # Use $ separator between base name and type args (matches monomorphizer)
        return f"{base}${'_'.join(arg_parts)}"

    def _type_to_name_suffix(self, ty: rast.Type) -> str:
        """Convert a type to a name suffix for monomorphization."""
        if isinstance(ty, rast.NamedType):
            if ty.args:
                return self._get_specialized_type_name(ty)
            return ty.name
        elif isinstance(ty, rast.PtrType):
            return "ptr_" + self._type_to_name_suffix(ty.inner)
        else:
            return str(ty)

    def _emit_cast(self, expr: rast.Cast) -> ir.Value:
        """Emit a type cast: expr as Type.

        This is an explicit cast operation that allows conversions that
        the implicit _convert_type might not allow. It also provides
        type information for subsequent operations (e.g., field access
        on cast pointers).
        """
        # Check if casting TO a union type
        if isinstance(expr.target, rast.NamedType) and expr.target.name in self.union_types:
            return self._emit_cast_to_union(expr)

        # Check if casting TO a dyn Trait type
        if isinstance(expr.target, rast.DynType):
            return self._emit_cast_to_dyn(expr)

        # Check if casting TO a reference/pointer to dyn Trait (e.g., &dyn Animal)
        if isinstance(expr.target, (rast.RefType, rast.PtrType)):
            if isinstance(expr.target.inner, rast.DynType):
                return self._emit_cast_to_dyn_ref(expr)

        # Check if casting FROM a union type to a variant type
        # This happens in match arms: x as i32, x as *u8, etc.
        val = self._emit_expr(expr.expr)

        # Check if the source expression's type is a union
        src_union_name = self._get_union_name_from_expr(expr.expr)
        if src_union_name and src_union_name in self.union_types:
            return self._emit_cast_from_union(val, src_union_name, expr.target)

        target_type = self._ritz_type_to_llvm(expr.target)

        # Check if source OR target is unsigned for proper extension
        # When casting to unsigned (e.g., i32 as u64), use zext to avoid sign pollution
        # When casting from unsigned (e.g., u8 as u64), also use zext
        use_zext = self._infer_unsigned_expr(expr.expr) or self._is_unsigned_type(expr.target)

        # Handle integer widening with proper sign extension
        if isinstance(val.type, ir.IntType) and isinstance(target_type, ir.IntType):
            if val.type.width < target_type.width:
                # Boolean always uses zext
                if val.type.width == 1:
                    return self.builder.zext(val, target_type)
                # Unsigned types use zext
                if use_zext:
                    return self.builder.zext(val, target_type)
                return self.builder.sext(val, target_type)
            elif val.type.width > target_type.width:
                return self.builder.trunc(val, target_type)
            else:
                return val  # Same width

        # Use _convert_type for other conversions
        return self._convert_type(val, target_type)

    def _get_union_name_from_expr(self, expr: rast.Expr) -> Optional[str]:
        """Get the union type name if the expression has a union type."""
        if isinstance(expr, rast.Ident):
            name = expr.name
            # Check locals (var bindings)
            if name in self.locals:
                alloca, ty = self.locals[name]
                # Check if ty is a union type
                for union_name, (union_ty, _) in self.union_types.items():
                    if ty == union_ty:
                        return union_name
            # Check params (let bindings and function parameters)
            if name in self.params:
                val, ty = self.params[name]
                # Check if ty is a union type
                for union_name, (union_ty, _) in self.union_types.items():
                    if ty == union_ty:
                        return union_name
            # Check ritz_types for declared type
            if name in self.ritz_types:
                ritz_ty = self.ritz_types[name]
                if isinstance(ritz_ty, rast.NamedType) and ritz_ty.name in self.union_types:
                    return ritz_ty.name
        return None

    def _get_enum_name_from_expr(self, expr: rast.Expr) -> Optional[str]:
        """Get the enum type name if the expression has an enum type."""
        if isinstance(expr, rast.Ident):
            name = expr.name
            # Check locals (var bindings)
            if name in self.locals:
                alloca, ty = self.locals[name]
                # Check if ty is an enum type
                for enum_name, (enum_ty, _) in self.enum_types.items():
                    if ty == enum_ty:
                        return enum_name
            # Check params (let bindings and function parameters)
            if name in self.params:
                val, ty = self.params[name]
                # Check if ty is an enum type
                for enum_name, (enum_ty, _) in self.enum_types.items():
                    if ty == enum_ty:
                        return enum_name
            # Check ritz_types for declared type
            if name in self.ritz_types:
                ritz_ty = self.ritz_types[name]
                if isinstance(ritz_ty, rast.NamedType) and ritz_ty.name in self.enum_types:
                    return ritz_ty.name
        elif isinstance(expr, rast.UnaryOp) and expr.op == '*':
            # Dereference: *opt where opt is a pointer to an enum
            inner_expr = expr.operand
            if isinstance(inner_expr, rast.Ident):
                name = inner_expr.name
                # Check params for pointer-to-enum type
                if name in self.params:
                    val, ty = self.params[name]
                    if isinstance(ty, ir.PointerType):
                        pointee = ty.pointee
                        for enum_name, (enum_ty, _) in self.enum_types.items():
                            if pointee == enum_ty:
                                return enum_name
                # Check ritz_types for pointer-to-enum
                if name in self.ritz_types:
                    ritz_ty = self.ritz_types[name]
                    if isinstance(ritz_ty, rast.PtrType) and isinstance(ritz_ty.inner, rast.NamedType):
                        inner_name = ritz_ty.inner.name
                        if inner_name in self.enum_types:
                            return inner_name
        elif isinstance(expr, rast.Call):
            # Function call: look up the function's return type
            fn_name = None
            if isinstance(expr.func, rast.Ident):
                fn_name = expr.func.name
            elif isinstance(expr.func, str):
                fn_name = expr.func
            if fn_name and fn_name in self.functions:
                _, fn_def = self.functions[fn_name]
                if fn_def and fn_def.ret_type:
                    ret_type = fn_def.ret_type
                    if isinstance(ret_type, rast.NamedType):
                        if ret_type.args:
                            # Generic instantiation like Result<i32, i32>
                            specialized_name = self._get_specialized_type_name(ret_type)
                            if specialized_name in self.enum_types:
                                return specialized_name
                        else:
                            # Simple named type (possibly already monomorphized)
                            if ret_type.name in self.enum_types:
                                return ret_type.name
        return None

    def _emit_cast_to_union(self, expr: rast.Cast) -> ir.Value:
        """Emit a cast from a value to a union type: 42 as IntOrStr."""
        union_name = expr.target.name
        union_type, variants = self.union_types[union_name]

        # Emit the source value
        val = self._emit_expr(expr.expr)
        val_type = val.type

        # Find which variant this value matches (by looking at the LLVM type)
        tag = -1
        matched_variant = None
        for i, variant in enumerate(variants):
            llvm_variant_ty = self._ritz_type_to_llvm(variant)
            if val_type == llvm_variant_ty:
                tag = i
                matched_variant = variant
                break

        if tag == -1:
            raise ValueError(f"Cannot cast value of type {val_type} to union {union_name}")

        # Create the union value on stack
        # Allocate space for the union
        union_alloca = self.builder.alloca(union_type, name="union.tmp")

        # Store the tag
        tag_ptr = self.builder.gep(union_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        self.builder.store(ir.Constant(self.i8, tag), tag_ptr)

        # Store the data - bitcast the data pointer to the variant type
        data_ptr = self.builder.gep(union_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 1)])
        # Cast data buffer to pointer to variant type
        variant_ptr = self.builder.bitcast(data_ptr, ir.PointerType(val_type))
        self.builder.store(val, variant_ptr)

        # Load and return the union value
        return self.builder.load(union_alloca)

    def _emit_cast_from_union(self, union_val: ir.Value, union_name: str, target_type: rast.Type) -> ir.Value:
        """Emit a cast from a union value to a variant type: x as i32."""
        union_type, variants = self.union_types[union_name]
        target_llvm_type = self._ritz_type_to_llvm(target_type)

        # Store union to memory so we can extract from it
        union_alloca = self.builder.alloca(union_type, name="union.extract")
        self.builder.store(union_val, union_alloca)

        # Get pointer to data buffer and bitcast to target type
        data_ptr = self.builder.gep(union_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 1)])
        variant_ptr = self.builder.bitcast(data_ptr, ir.PointerType(target_llvm_type))

        # Load and return the value
        return self.builder.load(variant_ptr)

    def _emit_cast_to_dyn(self, expr: rast.Cast) -> ir.Value:
        """Emit a cast to dyn Trait: expr as dyn Trait.

        This creates a fat pointer { data_ptr, vtable_ptr }.
        """
        dyn_type = expr.target  # rast.DynType
        trait_name = dyn_type.trait_name

        # Get the concrete type being cast
        concrete_type_name = self._get_type_name_from_expr(expr.expr)
        if not concrete_type_name:
            raise ValueError(f"Cannot determine concrete type for dyn cast at {expr.span}")

        # Get the vtable for this (trait, type) pair
        vtable = self._get_vtable_for_type(trait_name, concrete_type_name)
        if vtable is None:
            raise ValueError(f"No vtable found for {concrete_type_name} implementing {trait_name} at {expr.span}")

        # Emit the expression value
        val = self._emit_expr(expr.expr)

        # Get a pointer to the data
        # If val is already a pointer, use it directly; otherwise allocate
        if isinstance(val.type, ir.PointerType):
            data_ptr = val
        else:
            # Allocate storage for the value
            data_alloca = self.builder.alloca(val.type, name='dyn.storage')
            self.builder.store(val, data_alloca)
            data_ptr = data_alloca

        # Create fat pointer
        return self._pack_fat_pointer(trait_name, data_ptr, vtable)

    def _emit_cast_to_dyn_ref(self, expr: rast.Cast) -> ir.Value:
        """Emit a cast to &dyn Trait or *dyn Trait.

        This is the most common case: &concrete_val as &dyn Trait.
        """
        dyn_type = expr.target.inner  # rast.DynType (inside the RefType/PtrType)
        trait_name = dyn_type.trait_name

        # Get the concrete type being cast
        # For &T -> &dyn Trait, we need the T
        concrete_type_name = self._get_type_name_from_expr(expr.expr)
        if not concrete_type_name:
            # Try to infer from the inner type if expr is a reference
            inner_type = self._infer_ritz_type(expr.expr)
            if isinstance(inner_type, (rast.RefType, rast.PtrType)):
                if isinstance(inner_type.inner, rast.NamedType):
                    concrete_type_name = inner_type.inner.name

        if not concrete_type_name:
            raise ValueError(f"Cannot determine concrete type for dyn cast at {expr.span}")

        # Get the vtable for this (trait, type) pair
        vtable = self._get_vtable_for_type(trait_name, concrete_type_name)
        if vtable is None:
            raise ValueError(f"No vtable found for {concrete_type_name} implementing {trait_name} at {expr.span}")

        # Emit the expression (should be a reference/pointer)
        data_ptr = self._emit_expr(expr.expr)

        # Create fat pointer
        return self._pack_fat_pointer(trait_name, data_ptr, vtable)

    def _get_type_name_from_expr(self, expr: rast.Expr) -> Optional[str]:
        """Get the concrete type name from an expression."""
        ritz_type = self._infer_ritz_type(expr)
        if isinstance(ritz_type, rast.NamedType):
            return ritz_type.name
        elif isinstance(ritz_type, (rast.RefType, rast.PtrType)):
            if isinstance(ritz_type.inner, rast.NamedType):
                return ritz_type.inner.name
        return None


def filter_by_target_os(module: rast.Module, target_os: str) -> rast.Module:
    """Filter out items that don't match the target OS.

    Items with [[target_os = "..."]] attribute are only included if the
    attribute value matches the current target_os. Items without the
    attribute are always included.

    Args:
        module: The module to filter
        target_os: The target OS to match (e.g., "linux", "harland")

    Returns:
        A new module with only matching items
    """
    filtered_items = []
    for item in module.items:
        # Check if item has target_os attribute
        if hasattr(item, 'get_attr_value'):
            item_target_os = item.get_attr_value('target_os')
            if item_target_os is not None and item_target_os != target_os:
                # Skip items that don't match target_os
                continue
        elif hasattr(item, 'attrs'):
            # Fallback for items that have attrs but not get_attr_value
            for attr in item.attrs:
                if attr.name == 'target_os' and attr.value is not None:
                    if attr.value != target_os:
                        continue
        filtered_items.append(item)

    # Create new module with filtered items
    return rast.Module(module.span, filtered_items)


def emit(module: rast.Module, no_runtime: bool = False,
         source_file: str = "unknown.ritz", source_dir: str = ".",
         main_source_path: Optional[str] = None,
         test_mode: bool = False,
         target: str = 'x86_64-unknown-linux-gnu',
         target_os: str = 'linux') -> str:
    """Convenience function to emit a module to LLVM IR.

    Args:
        module: The Ritz AST module to emit
        no_runtime: If True, don't emit _start and runtime
        source_file: Source filename for debug info (default: unknown.ritz)
        source_dir: Source directory for debug info (default: .)
        main_source_path: Full path to main source file (for separate compilation).
                          Only functions from this file will have bodies emitted.
        test_mode: If True, generate test main instead of regular main
        target: Target triple (default: x86_64-unknown-linux-gnu)
                Use x86_64-none-elf for freestanding/kernel builds.
        target_os: Target OS for conditional compilation (default: linux)

    Returns:
        LLVM IR text
    """
    # Monomorphize generics before emission
    from monomorph import monomorphize
    module = monomorphize(module)

    # Note: target_os filtering happens earlier in compile_file() before name resolution

    emitter = LLVMEmitter(source_file=source_file, source_dir=source_dir, target=target)
    emitter.no_runtime = no_runtime
    emitter.test_mode = test_mode

    # Always use separate compilation - pass source path to control body emission
    if main_source_path:
        ir_str = emitter.emit_module(module, source_file=main_source_path)
    else:
        ir_str = emitter.emit_module(module)

    # Fix up _start to be naked (only if runtime was emitted)
    if not no_runtime:
        ir_str = ir_str.replace('define void @"_start"()', 'define void @_start() naked')
        ir_str = ir_str.replace('@"_start"', '@_start')

    return ir_str


def get_test_functions(module: rast.Module) -> List[rast.FnDef]:
    """Get all @test functions from a module."""
    tests = []
    for item in module.items:
        if isinstance(item, rast.FnDef) and item.has_attr('test'):
            tests.append(item)
    return tests


def generate_test_main_source(test_fns: List[rast.FnDef]) -> str:
    """Generate Ritz source for a test main that runs all test functions.

    This generates a main() function that uses ritzlib/testing.ritz to run
    all the discovered test functions.
    """
    if not test_fns:
        return """
import ritzlib.testing

fn main() -> i32
    prints("No tests found.\\n")
    return 0
"""

    # Build the test array and main function
    lines = [
        "import ritzlib.testing",
        "",
        "# Test entry array",
        f"var __test_entries: [{len(test_fns)}]TestEntry",
        "",
        "fn main() -> i32",
    ]

    # Initialize test entries
    for i, fn in enumerate(test_fns):
        lines.append(f'    __test_entries[{i}].name = "{fn.name}"')
        lines.append(f'    __test_entries[{i}].func = &{fn.name}')

    # Call the runner
    lines.append(f"    return run_tests_array(&__test_entries[0], {len(test_fns)})")
    lines.append("")

    return "\n".join(lines)
