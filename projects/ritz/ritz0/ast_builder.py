"""
ast_builder.py - Convert parsed tokens to ritz_ast nodes

This module provides the bridge between the generated parser and ritz_ast.
The generated parser calls these builder functions to construct proper AST nodes.
"""

from typing import List, Optional, Any, Tuple
from tokens import Span, Token
import ritz_ast as ast


def make_span(token_or_result: Any) -> Span:
    """Create a Span from a token or parsed result."""
    if isinstance(token_or_result, Token):
        return token_or_result.span
    if isinstance(token_or_result, dict) and 'span' in token_or_result:
        return token_or_result['span']
    if isinstance(token_or_result, dict) and 'token' in token_or_result:
        return token_or_result['token'].span
    if hasattr(token_or_result, 'span'):
        return token_or_result.span
    # Default: create a placeholder span
    return Span(file="<unknown>", line=1, col=1)


def get_value(token_or_result: Any) -> Any:
    """Get the value from a token or result."""
    if isinstance(token_or_result, Token):
        return token_or_result.value
    if isinstance(token_or_result, dict) and 'value' in token_or_result:
        return token_or_result['value']
    return token_or_result


# ============================================================================
# Types
# ============================================================================

def build_named_type(name_token: Token, type_args: List[ast.Type] = None) -> ast.NamedType:
    """Build a NamedType from a name token and optional type args."""
    return ast.NamedType(
        span=name_token.span,
        name=name_token.value,
        args=type_args or []
    )


def build_ptr_type(inner: ast.Type, mutable: bool, span: Span) -> ast.PtrType:
    """Build a pointer type *T or *mut T."""
    return ast.PtrType(span=span, inner=inner, mutable=mutable)


def build_ref_type(inner: ast.Type, mutable: bool, span: Span) -> ast.RefType:
    """Build a reference type &T or &mut T."""
    return ast.RefType(span=span, inner=inner, mutable=mutable)


def build_array_type(size: int, inner: ast.Type, span: Span) -> ast.ArrayType:
    """Build an array type [N]T."""
    return ast.ArrayType(span=span, size=size, inner=inner)


def build_fn_type(params: List[ast.Type], ret: Optional[ast.Type], span: Span) -> ast.FnType:
    """Build a function type fn(A, B) -> C."""
    return ast.FnType(span=span, params=params, ret=ret)


# ============================================================================
# Expressions
# ============================================================================

def build_int_lit(token: Token) -> ast.IntLit:
    """Build an integer literal."""
    value = token.value
    # Handle hex, octal, binary literals
    if isinstance(value, str):
        if value.startswith('0x') or value.startswith('0X'):
            value = int(value, 16)
        elif value.startswith('0o') or value.startswith('0O'):
            value = int(value, 8)
        elif value.startswith('0b') or value.startswith('0B'):
            value = int(value, 2)
        else:
            value = int(value)
    return ast.IntLit(span=token.span, value=value)


def build_float_lit(token: Token) -> ast.FloatLit:
    """Build a float literal."""
    value = token.value
    if isinstance(value, str):
        value = float(value)
    return ast.FloatLit(span=token.span, value=value)


def build_string_lit(token: Token) -> ast.StringLit:
    """Build a string literal."""
    return ast.StringLit(span=token.span, value=token.value)


def build_cstring_lit(token: Token) -> ast.CStringLit:
    """Build a C-string literal c"..."."""
    return ast.CStringLit(span=token.span, value=token.value)


# Note: build_span_string_lit (s"...") was removed in AGAST #98 — bare
# "..." now produces StrView which is layout-compatible with Span<u8>.


def build_char_lit(token: Token) -> ast.CharLit:
    """Build a character literal."""
    value = token.value
    if isinstance(value, str) and len(value) == 1:
        value = ord(value)
    return ast.CharLit(span=token.span, value=value)


def build_bool_lit(token: Token, value: bool) -> ast.BoolLit:
    """Build a boolean literal."""
    return ast.BoolLit(span=token.span, value=value)


def build_null_lit(span: Span) -> ast.NullLit:
    """Build a null literal."""
    return ast.NullLit(span=span)


def build_ident(token: Token) -> ast.Ident:
    """Build an identifier expression."""
    return ast.Ident(span=token.span, name=token.value)


def build_qualified_ident(qualifier_token: Token, name_token: Token) -> ast.QualifiedIdent:
    """Build a qualified identifier alias::name."""
    return ast.QualifiedIdent(
        span=qualifier_token.span,
        qualifier=qualifier_token.value,
        name=name_token.value
    )


def build_binary_op(op: str, left: ast.Expr, right: ast.Expr) -> ast.BinOp:
    """Build a binary operation."""
    return ast.BinOp(span=left.span, op=op, left=left, right=right)


def build_unary_op(op: str, operand: ast.Expr, span: Span) -> ast.UnaryOp:
    """Build a unary operation."""
    return ast.UnaryOp(span=span, op=op, operand=operand)


def build_call(func: ast.Expr, args: List[ast.Expr], type_args: List[ast.Type] = None) -> ast.Call:
    """Build a function call."""
    return ast.Call(span=func.span, func=func, args=args, type_args=type_args or [])


def build_index(expr: ast.Expr, index: ast.Expr) -> ast.Index:
    """Build an index expression a[i]."""
    return ast.Index(span=expr.span, expr=expr, index=index)


def build_field(expr: ast.Expr, field_token: Token) -> ast.Field:
    """Build a field access a.b."""
    return ast.Field(span=expr.span, expr=expr, field=field_token.value)


def build_method_call(expr: ast.Expr, method_token: Token, args: List[ast.Expr]) -> ast.MethodCall:
    """Build a method call a.foo(b)."""
    return ast.MethodCall(
        span=expr.span,
        expr=expr,
        method=method_token.value,
        args=args
    )


def build_if(cond: ast.Expr, then_block: ast.Block, else_block: Optional[ast.Block], span: Span) -> ast.If:
    """Build an if expression."""
    return ast.If(span=span, cond=cond, then_block=then_block, else_block=else_block)


def build_block(stmts: List[ast.Stmt], expr: Optional[ast.Expr], span: Span) -> ast.Block:
    """Build a block expression."""
    return ast.Block(span=span, stmts=stmts, expr=expr)


def build_struct_lit(name_token: Token, fields: List[Tuple[str, ast.Expr]], type_args: List[ast.Type] = None) -> ast.StructLit:
    """Build a struct literal MyStruct { field: value }."""
    return ast.StructLit(
        span=name_token.span,
        name=name_token.value,
        fields=fields,
        type_args=type_args or []
    )


def build_array_lit(elements: List[ast.Expr], span: Span) -> ast.ArrayLit:
    """Build an array literal [a, b, c]."""
    return ast.ArrayLit(span=span, elements=elements)


def build_array_fill(value: ast.Expr, count: int, span: Span) -> ast.ArrayFill:
    """Build an array fill [value; count]."""
    return ast.ArrayFill(span=span, value=value, count=count)


def build_match(expr: ast.Expr, arms: List[ast.MatchArm], span: Span) -> ast.Match:
    """Build a match expression."""
    return ast.Match(span=span, expr=expr, arms=arms)


def build_match_arm(pattern: ast.Pattern, guard: Optional[ast.Expr], body: ast.Expr, span: Span) -> ast.MatchArm:
    """Build a match arm."""
    return ast.MatchArm(span=span, pattern=pattern, guard=guard, body=body)


def build_try_op(expr: ast.Expr) -> ast.TryOp:
    """Build a try operator expr?"""
    return ast.TryOp(span=expr.span, expr=expr)


def build_range(start: Optional[ast.Expr], end: Optional[ast.Expr], inclusive: bool, span: Span) -> ast.Range:
    """Build a range expression start..end."""
    return ast.Range(span=span, start=start, end=end, inclusive=inclusive)


def build_cast(expr: ast.Expr, target: ast.Type, span: Span) -> ast.Cast:
    """Build a cast expression expr as Type."""
    return ast.Cast(span=span, expr=expr, target=target)


def build_await(expr: ast.Expr, span: Span) -> ast.Await:
    """Build an await expression."""
    return ast.Await(span=span, expr=expr)


def build_closure(params: List[ast.ClosureParam], body: ast.Expr, span: Span) -> ast.Closure:
    """Build a closure |x, y| body."""
    return ast.Closure(span=span, params=params, body=body)


def build_closure_param(name_token: Token, type_: Optional[ast.Type] = None) -> ast.ClosureParam:
    """Build a closure parameter."""
    return ast.ClosureParam(name=name_token.value, type=type_)


# ============================================================================
# Patterns
# ============================================================================

def build_wildcard_pattern(span: Span) -> ast.WildcardPattern:
    """Build a wildcard pattern _."""
    return ast.WildcardPattern(span=span)


def build_ident_pattern(name_token: Token, mutable: bool) -> ast.IdentPattern:
    """Build an identifier pattern."""
    return ast.IdentPattern(span=name_token.span, name=name_token.value, mutable=mutable)


def build_lit_pattern(value: Any, span: Span) -> ast.LitPattern:
    """Build a literal pattern."""
    return ast.LitPattern(span=span, value=value)


def build_variant_pattern(name_token: Token, fields: List[ast.Pattern]) -> ast.VariantPattern:
    """Build a variant pattern Some(x)."""
    return ast.VariantPattern(span=name_token.span, name=name_token.value, fields=fields)


def build_struct_pattern(name_token: Token, fields: List[Tuple[str, ast.Pattern]]) -> ast.StructPattern:
    """Build a struct pattern Point { x, y }."""
    return ast.StructPattern(span=name_token.span, name=name_token.value, fields=fields)


# ============================================================================
# Statements
# ============================================================================

def build_let_stmt(name_token: Token, type_: Optional[ast.Type], value: Optional[ast.Expr], span: Span) -> ast.LetStmt:
    """Build a let statement."""
    return ast.LetStmt(span=span, name=name_token.value, type=type_, value=value)


def build_var_stmt(name_token: Token, type_: Optional[ast.Type], value: Optional[ast.Expr], span: Span) -> ast.VarStmt:
    """Build a var statement."""
    return ast.VarStmt(span=span, name=name_token.value, type=type_, value=value)


def build_expr_stmt(expr: ast.Expr) -> ast.ExprStmt:
    """Build an expression statement."""
    return ast.ExprStmt(span=expr.span, expr=expr)


def build_assign_stmt(target: ast.Expr, value: ast.Expr) -> ast.AssignStmt:
    """Build an assignment statement."""
    return ast.AssignStmt(span=target.span, target=target, value=value)


def build_return_stmt(value: Optional[ast.Expr], span: Span) -> ast.ReturnStmt:
    """Build a return statement."""
    return ast.ReturnStmt(span=span, value=value)


def build_while_stmt(cond: ast.Expr, body: ast.Block, span: Span) -> ast.WhileStmt:
    """Build a while statement."""
    return ast.WhileStmt(span=span, cond=cond, body=body)


def build_for_stmt(var_token: Token, iter_: ast.Expr, body: ast.Block, span: Span) -> ast.ForStmt:
    """Build a for statement."""
    return ast.ForStmt(span=span, var=var_token.value, iter=iter_, body=body)


def build_break_stmt(span: Span) -> ast.BreakStmt:
    """Build a break statement."""
    return ast.BreakStmt(span=span)


def build_continue_stmt(span: Span) -> ast.ContinueStmt:
    """Build a continue statement."""
    return ast.ContinueStmt(span=span)


def build_assert_stmt(condition: ast.Expr, message: Optional[str], span: Span) -> ast.AssertStmt:
    """Build an assert statement."""
    return ast.AssertStmt(span=span, condition=condition, message=message)


# ============================================================================
# Items (top-level declarations)
# ============================================================================

def build_param(name_token: Token, type_: ast.Type) -> ast.Param:
    """Build a function parameter."""
    return ast.Param(span=name_token.span, name=name_token.value, type=type_)


def build_attr(name_token: Token) -> ast.Attr:
    """Build an attribute @name."""
    return ast.Attr(name=name_token.value)


def build_fn_def(
    name_token: Token,
    params: List[ast.Param],
    ret_type: Optional[ast.Type],
    body: ast.Block,
    attrs: List[ast.Attr] = None,
    type_params: List[str] = None,
    is_pub: bool = False,
    is_extern: bool = False,
    is_async: bool = False
) -> ast.FnDef:
    """Build a function definition."""
    return ast.FnDef(
        span=name_token.span,
        name=name_token.value,
        params=params or [],
        ret_type=ret_type,
        body=body,
        attrs=attrs or [],
        is_extern=is_extern,
        is_async=is_async,
        is_pub=is_pub,
        type_params=type_params or []
    )


def build_extern_fn(
    name_token: Token,
    params: List[ast.Param],
    ret_type: Optional[ast.Type],
    varargs: bool = False,
    is_pub: bool = False
) -> ast.ExternFn:
    """Build an external function declaration."""
    return ast.ExternFn(
        span=name_token.span,
        name=name_token.value,
        params=params or [],
        ret_type=ret_type,
        varargs=varargs,
        is_pub=is_pub
    )


def build_struct_def(
    name_token: Token,
    fields: List[Tuple[str, ast.Type]],
    type_params: List[str] = None,
    is_pub: bool = False
) -> ast.StructDef:
    """Build a struct definition."""
    return ast.StructDef(
        span=name_token.span,
        name=name_token.value,
        fields=fields or [],
        is_pub=is_pub,
        type_params=type_params or []
    )


def build_enum_def(
    name_token: Token,
    variants: List[ast.Variant],
    type_params: List[str] = None,
    is_pub: bool = False
) -> ast.EnumDef:
    """Build an enum definition."""
    return ast.EnumDef(
        span=name_token.span,
        name=name_token.value,
        variants=variants or [],
        is_pub=is_pub,
        type_params=type_params or []
    )


def build_variant(name_token: Token, fields: List[ast.Type] = None) -> ast.Variant:
    """Build an enum variant."""
    return ast.Variant(span=name_token.span, name=name_token.value, fields=fields or [])


def build_const_def(
    name_token: Token,
    type_: ast.Type,
    value: ast.Expr,
    is_pub: bool = False
) -> ast.ConstDef:
    """Build a constant definition."""
    return ast.ConstDef(
        span=name_token.span,
        name=name_token.value,
        type=type_,
        value=value,
        is_pub=is_pub
    )


def build_var_def(
    name_token: Token,
    type_: Optional[ast.Type],
    value: Optional[ast.Expr],
    is_pub: bool = False
) -> ast.VarDef:
    """Build a module-level var definition."""
    return ast.VarDef(
        span=name_token.span,
        name=name_token.value,
        type=type_,
        value=value,
        is_pub=is_pub
    )


def build_import(
    path: List[str],
    alias: Optional[str] = None,
    items: Optional[List[str]] = None,
    is_pub: bool = False,
    span: Span = None
) -> ast.Import:
    """Build an import statement."""
    return ast.Import(
        span=span or Span(file="<unknown>", line=1, col=1),
        path=path,
        alias=alias,
        items=items,
        is_pub=is_pub
    )


def build_type_alias(
    name_token: Token,
    target: ast.Type,
    is_pub: bool = False
) -> ast.TypeAlias:
    """Build a type alias."""
    return ast.TypeAlias(
        span=name_token.span,
        name=name_token.value,
        target=target,
        is_pub=is_pub
    )


def build_trait_def(
    name_token: Token,
    methods: List[ast.TraitMethodSig],
    is_pub: bool = False
) -> ast.TraitDef:
    """Build a trait definition."""
    return ast.TraitDef(
        span=name_token.span,
        name=name_token.value,
        methods=methods or [],
        is_pub=is_pub
    )


def build_trait_method_sig(
    name_token: Token,
    params: List[ast.Param],
    ret_type: Optional[ast.Type]
) -> ast.TraitMethodSig:
    """Build a trait method signature."""
    return ast.TraitMethodSig(
        span=name_token.span,
        name=name_token.value,
        params=params or [],
        ret_type=ret_type
    )


def build_impl_block(
    trait_name: Optional[str],
    type_name: str,
    methods: List[ast.FnDef],
    type_params: List[str] = None,
    impl_type: Optional[ast.Type] = None,
    span: Span = None
) -> ast.ImplBlock:
    """Build an impl block."""
    return ast.ImplBlock(
        span=span or Span(file="<unknown>", line=1, col=1),
        trait_name=trait_name,
        type_name=type_name,
        methods=methods or [],
        type_params=type_params or [],
        impl_type=impl_type
    )


def build_module(items: List[ast.Item], span: Span) -> ast.Module:
    """Build a module."""
    return ast.Module(span=span, items=items or [])
