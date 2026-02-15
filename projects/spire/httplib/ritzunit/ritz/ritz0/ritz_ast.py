"""
Ritz Abstract Syntax Tree

AST node definitions for ritz0.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Union
from tokens import Span


# ============================================================================
# Type Parameter with optional trait bounds
# ============================================================================

@dataclass
class TypeParam:
    """A generic type parameter with optional trait bounds.

    Examples:
        T           -> TypeParam("T", [])
        T: Drop     -> TypeParam("T", ["Drop"])
        T: Drop + Clone -> TypeParam("T", ["Drop", "Clone"])
    """
    name: str
    bounds: List[str] = field(default_factory=list)

    def has_bounds(self) -> bool:
        return len(self.bounds) > 0


# Base class for all AST nodes
@dataclass
class Node:
    span: Span


# ============================================================================
# Types
# ============================================================================

@dataclass
class Type(Node):
    """Base class for type expressions."""
    pass


@dataclass
class NamedType(Type):
    """A simple named type like i32, bool, MyStruct, or generic instantiation like Vec<i32>."""
    name: str
    # Generic args like Vec<T> or Vec<i32, *u8>
    args: List['Type'] = field(default_factory=list)

    def is_generic_instantiation(self) -> bool:
        return len(self.args) > 0


@dataclass
class RefType(Type):
    """A reference type: &T or &mut T."""
    inner: Type
    mutable: bool


@dataclass
class PtrType(Type):
    """A raw pointer type: *T (immutable) or *mut T (mutable)."""
    inner: Type
    mutable: bool


@dataclass
class SliceType(Type):
    """A slice type: [T]."""
    inner: Type


@dataclass
class UnionType(Type):
    """A union type: A | B | C (tagged union)."""
    variants: List[Type]


@dataclass
class ArrayType(Type):
    """A fixed-size array type: [N]T.

    Size can be:
    - An integer literal (resolved)
    - A constant expression (to be resolved during const evaluation)

    After const evaluation, size should always be an int.
    """
    size: Union[int, 'Expr']
    inner: Type


@dataclass
class FnType(Type):
    """A function type: fn(A, B) -> C."""
    params: List[Type]
    ret: Optional[Type]


@dataclass
class VectorType(Type):
    """A SIMD vector type: vec<N, T>.

    Represents a fixed-size SIMD vector, e.g., vec<4, i32> for SSE2 __m128i.

    Common vector types:
    - vec<2, i64>  = v2i64 = __m128i (2 x 64-bit integers)
    - vec<4, i32>  = v4i32 = __m128i (4 x 32-bit integers)
    - vec<8, i16>  = v8i16 = __m128i (8 x 16-bit integers)
    - vec<16, i8>  = v16i8 = __m128i (16 x 8-bit integers)

    These map directly to LLVM IR vector types like <4 x i32>.
    """
    count: int  # Number of elements (e.g., 4 for v4i32)
    inner: Type  # Element type (e.g., i32)


# ============================================================================
# Expressions
# ============================================================================

@dataclass
class Expr(Node):
    """Base class for expressions."""
    pass


@dataclass
class IntLit(Expr):
    """Integer literal."""
    value: int


@dataclass
class FloatLit(Expr):
    """Float literal."""
    value: float


@dataclass
class StringLit(Expr):
    """String literal."""
    value: str


@dataclass
class CStringLit(Expr):
    """C-string literal: c"hello".

    Produces *u8 type (null-terminated C string).
    Does not support interpolation.
    """
    value: str


@dataclass
class SpanStringLit(Expr):
    """Span string literal: s"hello".

    Produces Span<u8> type { ptr: *u8, len: i64 } with compile-time length.
    Does not support interpolation. Zero allocation (static data).
    """
    value: str


@dataclass
class InterpString(Expr):
    """Interpolated string: "Hello, {name}!"

    Contains alternating string parts and expressions.
    parts = ["Hello, ", "!"]
    exprs = [Ident("name")]

    For "a {x} b {y} c": parts = ["a ", " b ", " c"], exprs = [x, y]
    For "{x}": parts = ["", ""], exprs = [x]
    """
    parts: List[str]   # String fragments (always len(exprs) + 1)
    exprs: List[Expr]  # Interpolated expressions


@dataclass
class CharLit(Expr):
    """Character literal (u8 value)."""
    value: int  # ASCII/byte value 0-255


@dataclass
class BoolLit(Expr):
    """Boolean literal."""
    value: bool


@dataclass
class NullLit(Expr):
    """Null pointer literal. Type must be inferred from context."""
    pass


@dataclass
class Ident(Expr):
    """Identifier."""
    name: str


@dataclass
class Grouped(Expr):
    """Parenthesized expression for preserving grouping in constant expressions."""
    expr: Expr


@dataclass
class QualifiedIdent(Expr):
    """Qualified identifier: alias::name.

    Used with import aliases to access namespaced items:
        import ritzlib.sys as sys
        sys::write(...)  # QualifiedIdent(qualifier='sys', name='write')
    """
    qualifier: str  # The namespace/alias prefix
    name: str       # The item name


@dataclass
class BinOp(Expr):
    """Binary operation: a + b, a && b, etc."""
    op: str
    left: Expr
    right: Expr


@dataclass
class UnaryOp(Expr):
    """Unary operation: -x, !x, &x, *x."""
    op: str
    operand: Expr


@dataclass
class Call(Expr):
    """Function call: foo(a, b) or foo<T>(a, b)."""
    func: Expr
    args: List[Expr]
    type_args: List[Type] = None  # Generic type arguments like <i32, *u8>

    def __post_init__(self):
        if self.type_args is None:
            self.type_args = []

    def is_generic_call(self) -> bool:
        return len(self.type_args) > 0


@dataclass
class Index(Expr):
    """Index operation: a[i]."""
    expr: Expr
    index: Expr


@dataclass
class SliceExpr(Expr):
    """Slice operation: a[start:end], a[:end], a[start:], a[:]

    Python-style slicing syntax. None for start means 0, None for end means len.
    """
    expr: Expr
    start: Optional[Expr]  # None means from beginning (0)
    end: Optional[Expr]    # None means to end (len)


@dataclass
class Field(Expr):
    """Field access: a.b."""
    expr: Expr
    field: str


@dataclass
class MethodCall(Expr):
    """Method call: a.foo(b) - sugar for Type_foo(a, b)."""
    expr: Expr
    method: str
    args: List[Expr]


@dataclass
class If(Expr):
    """If expression: if cond then_block else else_block."""
    cond: Expr
    then_block: 'Block'
    else_block: Optional['Block']


@dataclass
class Block(Expr):
    """Block expression: sequence of statements, optional final expression."""
    stmts: List['Stmt']
    expr: Optional[Expr]  # trailing expression (value of block)


@dataclass
class Lambda(Expr):
    """Lambda/closure: fn(x, y) -> T expr."""
    params: List['Param']
    ret_type: Optional[Type]
    body: Expr


@dataclass
class StructLit(Expr):
    """Struct literal: MyStruct { field: value } or MyStruct<T> { field: value }."""
    name: str
    fields: List[tuple[str, Expr]]
    type_args: List[Type] = None  # Generic type arguments like <i32>

    def __post_init__(self):
        if self.type_args is None:
            self.type_args = []

    def is_generic_instantiation(self) -> bool:
        return len(self.type_args) > 0


@dataclass
class ArrayLit(Expr):
    """Array literal: [a, b, c]."""
    elements: List[Expr]


@dataclass
class ArrayFill(Expr):
    """Array fill expression: [value; count].

    Creates an array with `count` copies of `value`.
    Example: [0; 8] creates [0, 0, 0, 0, 0, 0, 0, 0]
    """
    value: Expr
    count: int


@dataclass
class Match(Expr):
    """Match expression."""
    expr: Expr
    arms: List['MatchArm']


@dataclass
class MatchArm(Node):
    """A single arm in a match expression."""
    pattern: 'Pattern'
    guard: Optional[Expr]
    body: Expr


@dataclass
class TryOp(Expr):
    """Try operator: expr?"""
    expr: Expr


@dataclass
class Range(Expr):
    """Range expression: start..end."""
    start: Optional[Expr]
    end: Optional[Expr]
    inclusive: bool  # .. vs ..=


@dataclass
class Cast(Expr):
    """Type cast: expr as Type."""
    expr: Expr
    target: Type


@dataclass
class Await(Expr):
    """Await expression: await expr."""
    expr: Expr


@dataclass
class HeapExpr(Expr):
    """Heap allocation expression: heap expr.

    Desugars to: heap_new<T>(expr)
    where T is inferred from the expression type.
    """
    expr: Expr


@dataclass
class ClosureParam:
    """A closure parameter: name with optional type."""
    name: str
    type: Optional[Type] = None


@dataclass
class Closure(Expr):
    """Closure expression: |params| body.

    Examples:
        |x| x * 2           - single param, inferred type
        |x, y| x + y        - multiple params
        |x: i32| x * 2      - explicit param type

    A closure may capture variables from its enclosing scope.
    These are identified during closure analysis.
    """
    params: List[ClosureParam]
    body: Expr
    # Captured variables (filled in by closure analysis)
    captures: List[str] = None

    def __post_init__(self):
        if self.captures is None:
            self.captures = []


# ============================================================================
# Patterns
# ============================================================================

@dataclass
class Pattern(Node):
    """Base class for patterns."""
    pass


@dataclass
class WildcardPattern(Pattern):
    """Wildcard pattern: _."""
    pass


@dataclass
class IdentPattern(Pattern):
    """Identifier pattern: x, mut x."""
    name: str
    mutable: bool


@dataclass
class LitPattern(Pattern):
    """Literal pattern: 42, "hello", true."""
    value: Any


@dataclass
class VariantPattern(Pattern):
    """Enum variant pattern: Some(x), None."""
    name: str
    fields: List[Pattern]


@dataclass
class StructPattern(Pattern):
    """Struct pattern: Point { x, y }."""
    name: str
    fields: List[tuple[str, Pattern]]


@dataclass
class TypePattern(Pattern):
    """Type pattern for matching union variants: i32, *u8, etc."""
    type: Type


# ============================================================================
# Statements
# ============================================================================

@dataclass
class Stmt(Node):
    """Base class for statements."""
    pass


@dataclass
class LetStmt(Stmt):
    """Let binding: let x = expr, let x: T = expr."""
    name: str
    type: Optional[Type]
    value: Optional[Expr]


@dataclass
class VarStmt(Stmt):
    """Var binding (mutable): var x = expr."""
    name: str
    type: Optional[Type]
    value: Optional[Expr]


@dataclass
class ExprStmt(Stmt):
    """Expression statement."""
    expr: Expr


@dataclass
class AssignStmt(Stmt):
    """Assignment: x = expr, a[i] = expr, s.field = expr."""
    target: Expr
    value: Expr


@dataclass
class ReturnStmt(Stmt):
    """Return statement: return expr."""
    value: Optional[Expr]


@dataclass
class WhileStmt(Stmt):
    """While loop: while cond block."""
    cond: Expr
    body: Block


@dataclass
class ForStmt(Stmt):
    """For loop: for x in iter block."""
    var: str
    iter: Expr
    body: Block


@dataclass
class BreakStmt(Stmt):
    """Break statement."""
    pass


@dataclass
class ContinueStmt(Stmt):
    """Continue statement."""
    pass


@dataclass
class AssertStmt(Stmt):
    """Assert statement (only allowed in @test functions)."""
    condition: 'Expr'
    message: Optional[str] = None


# ============================================================================
# Items (top-level declarations)
# ============================================================================

class Item(Node):
    """Base class for top-level items.

    Items track their source file for separate compilation:
        item.source_file: Path to the source file where this item is defined.
                         Set by the import resolver. None for items from the
                         main compilation unit before import resolution.

    Note: source_file is not a dataclass field to avoid inheritance issues
    with required fields in subclasses. Set it as: item.source_file = path
    """
    pass


@dataclass
class Param(Node):
    """Function parameter."""
    name: str
    type: Type


@dataclass
class Attr:
    """Attribute like @test, @ignore, etc."""
    name: str
    args: List[str] = None  # For future @attr(arg1, arg2)

    def __post_init__(self):
        if self.args is None:
            self.args = []


@dataclass
class FnDef(Item):
    """Function definition."""
    name: str
    params: List[Param]
    ret_type: Optional[Type]
    body: Block
    attrs: List[Attr] = None
    is_extern: bool = False
    is_async: bool = False  # async fn
    is_pub: bool = False    # pub fn - exported from module
    type_params: List[str] = None  # Generic type parameters like <T, U>
    type_param_bounds: dict = None  # Trait bounds: {"T": ["Drop", "Clone"]}

    def __post_init__(self):
        if self.attrs is None:
            self.attrs = []
        if self.type_params is None:
            self.type_params = []
        if self.type_param_bounds is None:
            self.type_param_bounds = {}

    def has_attr(self, name: str) -> bool:
        return any(a.name == name for a in self.attrs)

    def is_generic(self) -> bool:
        return len(self.type_params) > 0

    def get_bounds(self, param: str) -> List[str]:
        """Get trait bounds for a type parameter."""
        return self.type_param_bounds.get(param, [])


@dataclass
class ExternFn(Item):
    """External function declaration."""
    name: str
    params: List[Param]
    ret_type: Optional[Type]
    varargs: bool = False
    is_pub: bool = False  # pub extern fn - exported from module


@dataclass
class StructDef(Item):
    """Struct definition."""
    name: str
    fields: List[tuple[str, Type]]
    is_pub: bool = False  # pub struct - exported from module
    type_params: List[str] = None  # Generic type parameters like <T, U>
    type_param_bounds: dict = None  # Trait bounds: {"T": ["Drop", "Clone"]}

    def __post_init__(self):
        if self.type_params is None:
            self.type_params = []
        if self.type_param_bounds is None:
            self.type_param_bounds = {}

    def is_generic(self) -> bool:
        return len(self.type_params) > 0

    def get_bounds(self, param: str) -> List[str]:
        """Get trait bounds for a type parameter."""
        return self.type_param_bounds.get(param, [])


@dataclass
class EnumDef(Item):
    """Enum definition.

    For generic enums like Option<T>, type_params contains ['T'].
    """
    name: str
    variants: List['Variant']
    is_pub: bool = False  # pub enum - exported from module
    type_params: List[str] = field(default_factory=list)
    type_param_bounds: dict = field(default_factory=dict)  # Trait bounds

    def is_generic(self) -> bool:
        return len(self.type_params) > 0

    def get_bounds(self, param: str) -> List[str]:
        """Get trait bounds for a type parameter."""
        return self.type_param_bounds.get(param, [])


@dataclass
class Variant(Node):
    """Enum variant."""
    name: str
    fields: List[Type]  # empty for unit variants


@dataclass
class ConstDef(Item):
    """Constant definition: const STDIN: i32 = 0."""
    name: str
    type: Type
    value: Expr
    is_pub: bool = False  # pub const - exported from module


@dataclass
class VarDef(Item):
    """Module-level mutable variable: var counter: i32 = 0."""
    name: str
    type: Optional[Type]
    value: Optional[Expr]
    is_pub: bool = False  # pub var - exported from module


@dataclass
class Import(Item):
    """Import statement with optional alias and selective imports.

    Variants:
        import ritzlib.sys           -> path=[ritzlib,sys], all pub items to namespace
        import ritzlib.sys as sys   -> path=[ritzlib,sys], alias='sys', qualified access
        import ritzlib.sys { a, b } -> path=[ritzlib,sys], items=['a','b'], selective
        import ritzlib.sys { a } as x -> path=[ritzlib,sys], items=['a'], alias='x'
        pub import ritzlib.sys      -> is_pub=True, re-exports imported items
    """
    path: List[str]
    alias: Optional[str] = None        # Namespace alias: import x as alias
    items: Optional[List[str]] = None  # Selective imports: { item1, item2 }
    is_pub: bool = False               # pub import re-exports items


@dataclass
class TypeAlias(Item):
    """Type alias: type IntOrStr = i32 | *u8."""
    name: str
    target: Type
    is_pub: bool = False  # pub type - exported from module


@dataclass
class StaticAssert(Item):
    """Compile-time assertion: static_assert(SIZE == 16, "wrong size")."""
    condition: 'Expr'
    message: Optional[str] = None


@dataclass
class TraitMethodSig(Node):
    """A method signature in a trait definition (no body)."""
    name: str
    params: List[Param]  # First param is self: *Self or self: Self
    ret_type: Optional[Type]


@dataclass
class TraitDef(Item):
    """Trait definition: trait Printable { fn print(self: *Self) -> i32 }."""
    name: str
    methods: List[TraitMethodSig]
    is_pub: bool = False  # pub trait - exported from module


@dataclass
class ImplBlock(Item):
    """Impl block: impl Trait for Type { fn method(...) { ... } }.

    When trait_name is None, this is an inherent impl (methods on the type itself).
    Example: impl Point { fn new(x: i32, y: i32) -> Point { ... } }

    For generic impls: impl<T> Drop for Box<T> { ... }
    - type_params contains ["T"]
    - type_name is "Box" with type_args ["T"] (stored in impl_type)

    For bounded generic impls: impl<T: Drop> Container<T> { ... }
    - type_param_bounds contains {"T": ["Drop"]}
    """
    trait_name: Optional[str]  # None for inherent impl
    type_name: str  # Base type name (e.g., "Box" for Box<T>)
    methods: List[FnDef]
    type_params: List[str] = field(default_factory=list)  # e.g., ["T"] for impl<T>
    impl_type: Optional[Type] = None  # Full type with args, e.g., Box<T>
    type_param_bounds: dict = field(default_factory=dict)  # Trait bounds

    def get_bounds(self, param: str) -> List[str]:
        """Get trait bounds for a type parameter."""
        return self.type_param_bounds.get(param, [])


@dataclass
class Module(Node):
    """A complete source file."""
    items: List[Item]
