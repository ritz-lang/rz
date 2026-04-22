"""
Symbol Table for Ritz Modules

Replaces AST merging for import resolution. A SymbolTable records the public
interface of a module — exported functions, structs, enums, traits, constants,
type aliases — without needing the full AST body.

This enables:
- Separate compilation (import only needs declarations, not full source)
- Incremental compilation (unchanged modules don't need re-parsing)
- Correct cross-module type checking

TDD: Tests in test_symbol_table.py
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import ritz_ast as rast


# ============================================================================
# Symbol Representations — lightweight records of exported items
# ============================================================================

@dataclass
class ParamInfo:
    """Lightweight record of a function parameter."""
    name: str
    type_str: str = ""  # String representation of the type
    borrow: str = "CONST"  # "CONST", "MUTABLE", or "MOVE"


@dataclass
class FieldInfo:
    """Lightweight record of a struct field."""
    name: str
    type_str: str = ""


@dataclass
class MethodInfo:
    """Lightweight record of a method from an impl block."""
    name: str
    is_pub: bool = True
    params: List[ParamInfo] = field(default_factory=list)
    return_type_str: str = ""
    type_params: List[str] = field(default_factory=list)


@dataclass
class Symbol:
    """A single exported symbol from a module.

    This is the core unit of the symbol table — it records everything the
    compiler needs to know about an imported symbol WITHOUT the full AST body.
    """
    name: str
    kind: str  # "fn", "struct", "enum", "const", "extern_fn", "trait",
               # "type_alias", "var", "impl"
    is_pub: bool = True
    module_path: str = ""

    # Function-specific
    params: List[ParamInfo] = field(default_factory=list)
    return_type_str: str = ""
    type_params: List[str] = field(default_factory=list)
    is_test: bool = False  # Has [[test]] attribute
    is_variadic: bool = False  # For extern fn

    # Struct-specific
    fields: List[FieldInfo] = field(default_factory=list)

    # Enum-specific (variant names)
    variants: List[str] = field(default_factory=list)

    # Trait-specific (method signatures)
    trait_methods: List[MethodInfo] = field(default_factory=list)

    # Const-specific
    const_value: Optional[str] = None

    # Type alias-specific
    alias_target: str = ""

    # The original AST node (kept for now for generic body access)
    # Will be removed once .ritz.sig files handle generic bodies
    ast_node: Optional[object] = None


# ============================================================================
# Symbol Table — the public interface of a module
# ============================================================================

class SymbolTable:
    """Tracks all exported symbols from a single Ritz module.

    Constructed from a parsed AST via SymbolTable.from_module().
    """

    def __init__(self, module_path: str = ""):
        self.module_path = module_path
        self.symbols: Dict[str, Symbol] = {}
        # Methods grouped by type name
        self._methods: Dict[str, List[MethodInfo]] = {}
        # Test functions (may not be pub but have [[test]])
        self._test_functions: List[Symbol] = []

    def has_symbol(self, name: str) -> bool:
        return name in self.symbols

    def get_symbol(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)

    def add_symbol(self, sym: Symbol):
        self.symbols[sym.name] = sym

    def get_methods(self, type_name: str) -> List[MethodInfo]:
        """Get all methods defined for a type via impl blocks."""
        return self._methods.get(type_name, [])

    def get_test_functions(self) -> List[Symbol]:
        """Get all functions with [[test]] attribute."""
        return self._test_functions

    # ========================================================================
    # Construction from AST
    # ========================================================================

    @classmethod
    def from_module(cls, module: rast.Module, module_path: str = "") -> 'SymbolTable':
        """Build a symbol table from a parsed module AST.

        Extracts all pub items and records their signatures.
        """
        st = cls(module_path)

        for item in module.items:
            if isinstance(item, rast.FnDef):
                st._add_fn(item)
            elif isinstance(item, rast.StructDef):
                st._add_struct(item)
            elif isinstance(item, rast.EnumDef):
                st._add_enum(item)
            elif isinstance(item, rast.ExternFn):
                st._add_extern_fn(item)
            elif isinstance(item, rast.ConstDef):
                st._add_const(item)
            elif isinstance(item, rast.TraitDef):
                st._add_trait(item)
            elif isinstance(item, rast.TypeAlias):
                st._add_type_alias(item)
            elif isinstance(item, rast.ImplBlock):
                st._add_impl(item)

        return st

    def _has_test_attr(self, item) -> bool:
        """Check if an item has [[test]] attribute."""
        attrs = getattr(item, 'attributes', [])
        if not attrs:
            attrs = getattr(item, 'attrs', [])
        for attr in attrs:
            if hasattr(attr, 'name') and attr.name == 'test':
                return True
            # Some attrs are stored as strings
            if isinstance(attr, str) and attr == 'test':
                return True
        return False

    def _type_to_str(self, type_node) -> str:
        """Convert a type AST node to a string representation."""
        if type_node is None:
            return ""
        if isinstance(type_node, rast.NamedType):
            return type_node.name
        if isinstance(type_node, rast.PtrType):
            return f"*{self._type_to_str(type_node.inner)}"
        if isinstance(type_node, rast.RefType):
            if getattr(type_node, 'is_mut', False):
                return f"@&{self._type_to_str(type_node.inner)}"
            return f"@{self._type_to_str(type_node.inner)}"
        if isinstance(type_node, rast.ArrayType):
            return f"[{type_node.size}]{self._type_to_str(type_node.element_type)}"
        # Fallback
        return str(type(type_node).__name__)

    def _extract_params(self, params) -> List[ParamInfo]:
        """Extract parameter info from AST param list."""
        result = []
        for p in params:
            borrow = "CONST"
            if hasattr(p, 'borrow'):
                if p.borrow == rast.Borrow.MUTABLE:
                    borrow = "MUTABLE"
                elif p.borrow == rast.Borrow.MOVE:
                    borrow = "MOVE"
            type_str = self._type_to_str(getattr(p, 'type', None) or getattr(p, 'param_type', None))
            result.append(ParamInfo(
                name=p.name,
                type_str=type_str,
                borrow=borrow
            ))
        return result

    def _extract_type_params(self, item) -> List[str]:
        """Extract type parameter names from a generic item."""
        params = getattr(item, 'type_params', []) or []
        result = []
        for p in params:
            if isinstance(p, rast.TypeParam):
                result.append(p.name)
            elif isinstance(p, str):
                result.append(p)
        return result

    def _add_fn(self, fn: rast.FnDef):
        """Add a function definition to the symbol table."""
        is_test = self._has_test_attr(fn)
        is_pub = getattr(fn, 'is_pub', False)

        sym = Symbol(
            name=fn.name,
            kind="fn",
            is_pub=is_pub,
            module_path=self.module_path,
            params=self._extract_params(fn.params),
            return_type_str=self._type_to_str(fn.ret_type),
            type_params=self._extract_type_params(fn),
            is_test=is_test,
            ast_node=fn,
        )

        if is_test:
            self._test_functions.append(sym)

        if is_pub:
            self.symbols[fn.name] = sym

    def _add_struct(self, struct: rast.StructDef):
        """Add a struct definition."""
        if not getattr(struct, 'is_pub', False):
            return

        fields = []
        for f in getattr(struct, 'fields', []):
            # Fields are stored as (name, type) tuples in the AST
            if isinstance(f, tuple) and len(f) == 2:
                fields.append(FieldInfo(
                    name=f[0],
                    type_str=self._type_to_str(f[1])
                ))
            elif hasattr(f, 'name'):
                fields.append(FieldInfo(
                    name=f.name,
                    type_str=self._type_to_str(getattr(f, 'type', None))
                ))

        self.symbols[struct.name] = Symbol(
            name=struct.name,
            kind="struct",
            is_pub=True,
            module_path=self.module_path,
            fields=fields,
            type_params=self._extract_type_params(struct),
            ast_node=struct,
        )

    def _add_enum(self, enum: rast.EnumDef):
        """Add an enum definition."""
        if not getattr(enum, 'is_pub', False):
            return

        variants = []
        for v in getattr(enum, 'variants', []):
            variants.append(getattr(v, 'name', str(v)))

        self.symbols[enum.name] = Symbol(
            name=enum.name,
            kind="enum",
            is_pub=True,
            module_path=self.module_path,
            variants=variants,
            type_params=self._extract_type_params(enum),
            ast_node=enum,
        )

    def _add_extern_fn(self, fn: rast.ExternFn):
        """Add an extern function (always considered public)."""
        self.symbols[fn.name] = Symbol(
            name=fn.name,
            kind="extern_fn",
            is_pub=True,
            module_path=self.module_path,
            params=self._extract_params(fn.params),
            return_type_str=self._type_to_str(fn.ret_type),
            is_variadic=getattr(fn, 'is_variadic', False),
            ast_node=fn,
        )

    def _add_const(self, const: rast.ConstDef):
        """Add a constant definition."""
        if not getattr(const, 'is_pub', False):
            return

        self.symbols[const.name] = Symbol(
            name=const.name,
            kind="const",
            is_pub=True,
            module_path=self.module_path,
            ast_node=const,
        )

    def _add_trait(self, trait: rast.TraitDef):
        """Add a trait definition."""
        if not getattr(trait, 'is_pub', False):
            return

        methods = []
        for m in getattr(trait, 'methods', []):
            methods.append(MethodInfo(
                name=m.name,
                is_pub=True,
                params=self._extract_params(getattr(m, 'params', [])),
                return_type_str=self._type_to_str(getattr(m, 'return_type', None)),
            ))

        self.symbols[trait.name] = Symbol(
            name=trait.name,
            kind="trait",
            is_pub=True,
            module_path=self.module_path,
            trait_methods=methods,
            type_params=self._extract_type_params(trait),
            ast_node=trait,
        )

    def _add_type_alias(self, alias: rast.TypeAlias):
        """Add a type alias."""
        if not getattr(alias, 'is_pub', False):
            return

        self.symbols[alias.name] = Symbol(
            name=alias.name,
            kind="type_alias",
            is_pub=True,
            module_path=self.module_path,
            alias_target=self._type_to_str(getattr(alias, 'target', None) or getattr(alias, 'aliased_type', None)),
            ast_node=alias,
        )

    # ========================================================================
    # Declaration Stub Generation
    # ========================================================================

    def to_declarations(self) -> list:
        """Generate AST declaration stubs from the symbol table.

        Returns a list of AST items suitable for the emitter — functions
        have empty bodies (declare only), structs/enums/consts/etc preserve
        their full definitions since the emitter needs them for type layout.

        Items are ordered: structs, enums, type_aliases, traits, consts,
        extern_fns, functions — matching the emitter's pass order.

        Each item is tagged with source_file = self.module_path so the
        emitter knows it's an imported declaration (not a local definition).
        """
        decls = []

        # Collect by kind in emitter pass order
        structs = []
        enums = []
        type_aliases = []
        traits = []
        consts = []
        extern_fns = []
        functions = []

        for sym in self.symbols.values():
            if sym.kind == "struct":
                structs.append(self._stub_struct(sym))
            elif sym.kind == "enum":
                enums.append(self._stub_enum(sym))
            elif sym.kind == "type_alias":
                type_aliases.append(self._stub_type_alias(sym))
            elif sym.kind == "trait":
                traits.append(self._stub_trait(sym))
            elif sym.kind == "const":
                consts.append(self._stub_const(sym))
            elif sym.kind == "extern_fn":
                extern_fns.append(self._stub_extern_fn(sym))
            elif sym.kind == "fn":
                functions.append(self._stub_fn(sym))

        decls.extend(structs)
        decls.extend(enums)
        decls.extend(type_aliases)
        decls.extend(traits)
        decls.extend(consts)
        decls.extend(extern_fns)
        decls.extend(functions)

        return decls

    def _tag(self, item):
        """Tag an AST item with source_file for import tracking."""
        item.source_file = self.module_path
        return item

    def _empty_block(self):
        """Create an empty Block (no statements, no trailing expr)."""
        return rast.Block(rast.Span("<stub>", 0, 0, 0), stmts=[], expr=None)

    def _stub_fn(self, sym: Symbol):
        """Generate a FnDef stub with no body (declaration only).

        Uses the original AST node's params/ret_type for type accuracy,
        but strips the body. This is the transitional approach — eventually
        we'll generate from type info alone (for .ritz.sig files).
        """
        if sym.ast_node is not None:
            # Clone from original AST but strip body
            orig = sym.ast_node
            stub = rast.FnDef(
                span=orig.span,
                name=orig.name,
                params=orig.params,
                ret_type=orig.ret_type,
                body=self._empty_block(),  # Empty Block = declaration only
                attrs=getattr(orig, 'attrs', None),
                is_pub=orig.is_pub,
                type_params=getattr(orig, 'type_params', None),
            )
            return self._tag(stub)
        # Fallback: shouldn't normally happen, but handle gracefully
        stub = rast.FnDef(
            span=rast.Span("<stub>", 0, 0, 0),
            name=sym.name,
            params=[],
            ret_type=None,
            body=self._empty_block(),
            is_pub=sym.is_pub,
        )
        return self._tag(stub)

    def _stub_struct(self, sym: Symbol):
        """Generate a StructDef stub — preserves full field info."""
        if sym.ast_node is not None:
            node = sym.ast_node
            return self._tag(node)
        stub = rast.StructDef(
            span=rast.Span("<stub>", 0, 0, 0),
            name=sym.name,
            fields=[],
            is_pub=sym.is_pub,
        )
        return self._tag(stub)

    def _stub_enum(self, sym: Symbol):
        """Generate an EnumDef stub — preserves variants."""
        if sym.ast_node is not None:
            return self._tag(sym.ast_node)
        stub = rast.EnumDef(
            span=rast.Span("<stub>", 0, 0, 0),
            name=sym.name,
            variants=[],
            is_pub=sym.is_pub,
        )
        return self._tag(stub)

    def _stub_const(self, sym: Symbol):
        """Generate a ConstDef stub — preserves value for const folding."""
        if sym.ast_node is not None:
            return self._tag(sym.ast_node)
        stub = rast.ConstDef(
            span=rast.Span("<stub>", 0, 0, 0),
            name=sym.name,
            type=rast.NamedType(rast.Span("<stub>", 0, 0, 0), "i32"),
            value=rast.IntLit(rast.Span("<stub>", 0, 0, 0), 0),
            is_pub=sym.is_pub,
        )
        return self._tag(stub)

    def _stub_extern_fn(self, sym: Symbol):
        """Generate an ExternFn stub."""
        if sym.ast_node is not None:
            return self._tag(sym.ast_node)
        stub = rast.ExternFn(
            span=rast.Span("<stub>", 0, 0, 0),
            name=sym.name,
            params=[],
            ret_type=None,
            is_pub=sym.is_pub,
        )
        return self._tag(stub)

    def _stub_type_alias(self, sym: Symbol):
        """Generate a TypeAlias stub."""
        if sym.ast_node is not None:
            return self._tag(sym.ast_node)
        stub = rast.TypeAlias(
            span=rast.Span("<stub>", 0, 0, 0),
            name=sym.name,
            target=rast.NamedType(rast.Span("<stub>", 0, 0, 0), "i32"),
            is_pub=sym.is_pub,
        )
        return self._tag(stub)

    def _stub_trait(self, sym: Symbol):
        """Generate a TraitDef stub — preserves method signatures."""
        if sym.ast_node is not None:
            return self._tag(sym.ast_node)
        stub = rast.TraitDef(
            span=rast.Span("<stub>", 0, 0, 0),
            name=sym.name,
            methods=[],
            is_pub=sym.is_pub,
        )
        return self._tag(stub)

    def _add_impl(self, impl: rast.ImplBlock):
        """Extract methods from an impl block and record them."""
        type_name = getattr(impl, 'type_name', None) or getattr(impl, 'target_type', "")
        if isinstance(type_name, rast.Node):
            type_name = getattr(type_name, 'name', str(type_name))

        if type_name not in self._methods:
            self._methods[type_name] = []

        for m in getattr(impl, 'methods', []):
            is_pub = getattr(m, 'is_pub', False)
            method = MethodInfo(
                name=m.name,
                is_pub=is_pub,
                params=self._extract_params(getattr(m, 'params', [])),
                return_type_str=self._type_to_str(getattr(m, 'return_type', None)),
                type_params=self._extract_type_params(m),
            )
            self._methods[type_name].append(method)
