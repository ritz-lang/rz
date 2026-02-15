"""
parser_adapter.py - Adapter between generated parser and ritz_ast

Converts the dict-based output from parser_gen.py to proper ritz_ast nodes.
This provides the same interface as the hand-written parser.py.
"""

from typing import List, Optional, Any
from parser_gen import Lexer as GenLexer, Parser as GenParser, Token as GenToken, TokenType
import ritz_ast as ast
from tokens import Span, Token as RitzToken


def _make_span(token: GenToken) -> Span:
    """Convert a generated token to a Span."""
    return Span(file="<source>", line=token.line, column=token.col, length=len(str(token.value)))


def _get_span(node: Any) -> Span:
    """Extract span from a parse node."""
    if isinstance(node, GenToken):
        return _make_span(node)
    if isinstance(node, dict):
        # Try to find a token in the node
        for key in ['0', '1', '2', '3']:
            if key in node and isinstance(node[key], GenToken):
                return _make_span(node[key])
        # Recursively search
        for key, val in node.items():
            if isinstance(val, GenToken):
                return _make_span(val)
            if isinstance(val, dict):
                span = _get_span(val)
                if span:
                    return span
    if hasattr(node, 'span'):
        return node.span
    return Span(file="<unknown>", line=1, column=1, length=1)


class ASTConverter:
    """Convert parsed dict trees to ritz_ast nodes."""

    def __init__(self, source_file: str = "<source>"):
        self.source_file = source_file

    def convert_module(self, parsed: List[dict]) -> ast.Module:
        """Convert a parsed module to ast.Module."""
        items = []
        for item_dict in parsed:
            item = self.convert_item(item_dict)
            if item:
                items.append(item)
        span = items[0].span if items else Span(file=self.source_file, line=1, column=1, length=1)
        return ast.Module(span=span, items=items)

    def convert_item(self, node: dict) -> Optional[ast.Item]:
        """Convert an item dict to an Item node."""
        if not node:
            return None

        rule = node.get('_rule')
        if rule == 'item':
            # item has attrs in '0' and actual item in '1'
            attrs = self.convert_attrs(node.get('0'))
            inner = node.get('1')
            if inner:
                item = self.convert_item(inner)
                if item and isinstance(item, ast.FnDef):
                    item.attrs = attrs
                return item
            return None

        if rule == 'fn_def':
            return self.convert_fn_def(node)
        if rule == 'struct_def':
            return self.convert_struct_def(node)
        if rule == 'enum_def':
            return self.convert_enum_def(node)
        if rule == 'const_def':
            return self.convert_const_def(node)
        if rule == 'type_alias':
            return self.convert_type_alias(node)
        if rule == 'trait_def':
            return self.convert_trait_def(node)
        if rule == 'impl_block':
            return self.convert_impl_block(node)
        if rule == 'import_stmt':
            return self.convert_import(node)
        if rule == 'global_var':
            return self.convert_global_var(node)

        return None

    def convert_attrs(self, node: Any) -> List[ast.Attr]:
        """Convert attrs dict to list of Attr."""
        if not node:
            return []

        if isinstance(node, dict):
            rule = node.get('_rule')
            if rule == 'attrs':
                # attrs: attr+ - node['0'] is first attr or list
                result = []
                attr_node = node.get('0')
                while attr_node:
                    if isinstance(attr_node, dict) and attr_node.get('_rule') == 'attr':
                        attr = self.convert_attr(attr_node)
                        if attr:
                            result.append(attr)
                        attr_node = attr_node.get('1')
                    elif isinstance(attr_node, list):
                        for a in attr_node:
                            attr = self.convert_attr(a)
                            if attr:
                                result.append(attr)
                        break
                    else:
                        break
                return result
            elif rule == 'attr':
                attr = self.convert_attr(node)
                return [attr] if attr else []

        if isinstance(node, list):
            result = []
            for n in node:
                result.extend(self.convert_attrs(n))
            return result

        return []

    def convert_attr(self, node: dict) -> Optional[ast.Attr]:
        """Convert single attr dict."""
        if not node or not isinstance(node, dict):
            return None
        if node.get('_rule') != 'attr':
            return None

        # attr: AT IDENT NEWLINE?
        name_token = node.get('1')  # IDENT is at position 1
        if isinstance(name_token, GenToken):
            return ast.Attr(name=name_token.value)
        return None

    def convert_fn_def(self, node: dict) -> ast.FnDef:
        """Convert fn_def dict to FnDef."""
        # Check if it's pub fn or extern fn
        token0 = node.get('0')
        is_pub = False
        is_extern = False
        name_idx = 1
        params_idx = 4
        ret_idx = 6
        body_idx = 7

        if isinstance(token0, GenToken):
            if token0.kind == TokenType.PUB:
                is_pub = True
                name_idx = 2  # pub fn IDENT
                params_idx = 5
                ret_idx = 7
                body_idx = 8
            elif token0.kind == TokenType.EXTERN:
                is_extern = True
                name_idx = 2  # extern fn IDENT
                params_idx = 4
                ret_idx = 6

        name_token = node.get(str(name_idx))
        params = self.convert_params(node.get(str(params_idx)))
        ret_type = self.convert_type(node.get(str(ret_idx)))

        # Extract type params if present
        generic_params = node.get('2') if not is_pub else node.get('3')
        type_params = self.convert_type_params(generic_params)

        if is_extern:
            # Extern function - no body
            return ast.ExternFn(
                span=_make_span(name_token),
                name=name_token.value,
                params=params,
                ret_type=ret_type,
                is_pub=is_pub
            )

        body = self.convert_block(node.get(str(body_idx)))

        return ast.FnDef(
            span=_make_span(name_token),
            name=name_token.value,
            params=params,
            ret_type=ret_type,
            body=body,
            is_pub=is_pub,
            is_extern=is_extern,
            type_params=type_params
        )

    def convert_type_params(self, node: Any) -> List[str]:
        """Extract type parameter names from generic_params."""
        if not node:
            return []
        if isinstance(node, dict):
            rule = node.get('_rule')
            if rule == 'generic_params':
                return self.convert_type_params(node.get('1'))  # LT param_list GT
            if rule == 'generic_param_list':
                # IDENT COMMA list | IDENT
                result = []
                ident = node.get('0')
                if isinstance(ident, GenToken):
                    result.append(ident.value)
                rest = node.get('2')
                if rest:
                    result.extend(self.convert_type_params(rest))
                return result
        return []

    def convert_params(self, node: Any) -> List[ast.Param]:
        """Convert params dict to list of Param."""
        if not node:
            return []

        if isinstance(node, dict):
            rule = node.get('_rule')
            if rule == 'params':
                # params: param COMMA params | param
                result = []
                left = node.get('left')
                right = node.get('right')
                if left:
                    param = self.convert_param(left)
                    if param:
                        result.append(param)
                    result.extend(self.convert_params(right))
                else:
                    # Single param
                    param = self.convert_param(node.get('0') or node)
                    if param:
                        result.append(param)
                return result
            elif rule == 'param':
                param = self.convert_param(node)
                return [param] if param else []

        return []

    def convert_param(self, node: Any) -> Optional[ast.Param]:
        """Convert single param dict."""
        if not node or not isinstance(node, dict):
            return None

        rule = node.get('_rule')
        if rule != 'param':
            return None

        # param: IDENT COLON type
        name_token = node.get('0')
        type_node = node.get('2')

        if isinstance(name_token, GenToken):
            return ast.Param(
                span=_make_span(name_token),
                name=name_token.value,
                type=self.convert_type(type_node)
            )
        return None

    def convert_type(self, node: Any) -> Optional[ast.Type]:
        """Convert type dict to Type node."""
        if not node:
            return None

        if isinstance(node, GenToken):
            # Built-in type token like I32
            type_map = {
                TokenType.I8: 'i8',
                TokenType.I16: 'i16',
                TokenType.I32: 'i32',
                TokenType.I64: 'i64',
                TokenType.U8: 'u8',
                TokenType.U16: 'u16',
                TokenType.U32: 'u32',
                TokenType.U64: 'u64',
                TokenType.F32: 'f32',
                TokenType.F64: 'f64',
                TokenType.BOOL: 'bool',
            }
            if node.kind in type_map:
                return ast.NamedType(
                    span=_make_span(node),
                    name=type_map[node.kind]
                )
            if node.kind == TokenType.IDENT:
                return ast.NamedType(
                    span=_make_span(node),
                    name=node.value
                )

        if isinstance(node, dict):
            rule = node.get('_rule')

            if rule == 'type':
                # type can be: primitive | name | STAR type | STAR MUT type | AMP type | etc.
                token0 = node.get('0')

                # Check for pointer type: STAR type or STAR MUT type
                if isinstance(token0, GenToken) and token0.kind == TokenType.STAR:
                    inner = node.get('1')
                    mutable = False
                    if isinstance(inner, GenToken) and inner.kind == TokenType.MUT:
                        mutable = True
                        inner = node.get('2')
                    return ast.PtrType(
                        span=_make_span(token0),
                        inner=self.convert_type(inner),
                        mutable=mutable
                    )

                # Check for reference type: AMP type or AMP_MUT type
                if isinstance(token0, GenToken) and token0.kind == TokenType.AMP:
                    inner = node.get('1')
                    return ast.RefType(
                        span=_make_span(token0),
                        inner=self.convert_type(inner),
                        mutable=False
                    )
                if isinstance(token0, GenToken) and token0.kind == TokenType.AMP_MUT:
                    inner = node.get('1')
                    return ast.RefType(
                        span=_make_span(token0),
                        inner=self.convert_type(inner),
                        mutable=True
                    )

                # Check for array type: LBRACKET NUMBER RBRACKET type
                if isinstance(token0, GenToken) and token0.kind == TokenType.LBRACKET:
                    size_token = node.get('1')
                    inner = node.get('3')
                    if isinstance(size_token, GenToken) and size_token.kind == TokenType.NUMBER:
                        return ast.ArrayType(
                            span=_make_span(token0),
                            size=int(size_token.value),
                            inner=self.convert_type(inner)
                        )
                    # Slice type: LBRACKET RBRACKET type
                    inner = node.get('2')
                    return ast.SliceType(
                        span=_make_span(token0),
                        inner=self.convert_type(inner)
                    )

                # Check for parenthesized type
                if isinstance(token0, GenToken) and token0.kind == TokenType.LPAREN:
                    return self.convert_type(node.get('1'))

                # Otherwise it's a single type (primitive or name)
                return self.convert_type(token0)

            if rule == 'return_type':
                # return_type: ARROW type
                return self.convert_type(node.get('1'))

            if rule == 'ptr_type':
                # ptr_type: STAR type | STAR MUT type
                inner = node.get('1')
                mutable = False
                if isinstance(inner, GenToken) and inner.kind == TokenType.MUT:
                    mutable = True
                    inner = node.get('2')
                return ast.PtrType(
                    span=_get_span(node),
                    inner=self.convert_type(inner),
                    mutable=mutable
                )

            if rule == 'ref_type':
                # ref_type: AMP type | AMP_MUT type
                token0 = node.get('0')
                mutable = isinstance(token0, GenToken) and token0.kind == TokenType.AMP_MUT
                inner = node.get('1')
                return ast.RefType(
                    span=_get_span(node),
                    inner=self.convert_type(inner),
                    mutable=mutable
                )

            if rule == 'array_type':
                # array_type: LBRACKET NUMBER RBRACKET type
                size_token = node.get('1')
                size = int(size_token.value) if isinstance(size_token, GenToken) else 0
                inner = node.get('3')
                return ast.ArrayType(
                    span=_get_span(node),
                    size=size,
                    inner=self.convert_type(inner)
                )

            if rule == 'fn_type':
                # fn_type: FN LPAREN type_list? RPAREN (ARROW type)?
                params = self.convert_type_list(node.get('2'))
                ret = self.convert_type(node.get('4'))
                return ast.FnType(
                    span=_get_span(node),
                    params=params,
                    ret=ret
                )

            if rule == 'named_type' or rule == 'type_name':
                # named_type: IDENT generic_args?
                # generic_args: LT type_list GT
                # The type_list is at node['1'] (inlined from generic_args)
                name_token = node.get('0')
                type_args = self.convert_type_list(node.get('1'))
                if isinstance(name_token, GenToken):
                    return ast.NamedType(
                        span=_make_span(name_token),
                        name=name_token.value,
                        args=type_args
                    )

        return None

    def convert_type_list(self, node: Any) -> List[ast.Type]:
        """Convert type_list to list of Type.

        type_list structure: {'_rule': 'type_list', 'left': type, 'op': COMMA, 'right': type_or_list}
        Or just a single type token/dict.
        """
        if not node:
            return []

        result = []

        if isinstance(node, GenToken):
            # Single type token
            t = self.convert_type(node)
            if t:
                result.append(t)
            return result

        if isinstance(node, dict):
            rule = node.get('_rule')
            if rule == 'type_list':
                # type_list: type COMMA type_list | type
                left = node.get('left') or node.get('0')
                right = node.get('right') or node.get('2')

                if left:
                    t = self.convert_type(left)
                    if t:
                        result.append(t)

                if right:
                    result.extend(self.convert_type_list(right))
            elif rule == 'generic_args':
                # generic_args: LT type_list GT
                return self.convert_type_list(node.get('1'))
            else:
                # It's a type node
                t = self.convert_type(node)
                if t:
                    result.append(t)

        return result

    def convert_type_args(self, node: Any) -> List[ast.Type]:
        """Convert type_args/generic_args to list of Type."""
        if not node:
            return []
        # Delegate to convert_type_list since generic_args contains type_list
        return self.convert_type_list(node)

    def convert_block(self, node: Any) -> ast.Block:
        """Convert block dict to Block."""
        if not node:
            return ast.Block(
                span=Span(file=self.source_file, line=1, column=1, length=1),
                stmts=[],
                expr=None
            )

        if isinstance(node, dict):
            rule = node.get('_rule')
            if rule == 'block':
                # block: NEWLINE INDENT stmts DEDENT
                stmts_node = node.get('2')
                stmts, trailing_expr = self.convert_stmts(stmts_node)
                span = _get_span(node)
                return ast.Block(span=span, stmts=stmts, expr=trailing_expr)

        return ast.Block(
            span=Span(file=self.source_file, line=1, column=1, length=1),
            stmts=[],
            expr=None
        )

    def convert_stmts(self, node: Any) -> tuple[List[ast.Stmt], Optional[ast.Expr]]:
        """Convert stmts dict to list of Stmt and optional trailing expr."""
        stmts = []
        trailing_expr = None

        if not node:
            return stmts, trailing_expr

        if isinstance(node, dict):
            rule = node.get('_rule')
            if rule == 'stmts':
                # stmts: stmt stmts | { null }
                stmt_node = node.get('0')
                rest = node.get('1')

                if stmt_node:
                    stmt = self.convert_stmt(stmt_node)
                    if stmt:
                        stmts.append(stmt)

                if rest:
                    more_stmts, trailing = self.convert_stmts(rest)
                    stmts.extend(more_stmts)
                    trailing_expr = trailing
            else:
                # Direct statement
                stmt = self.convert_stmt(node)
                if stmt:
                    stmts.append(stmt)

        # Check if last statement is an expr_stmt without newline (trailing expr)
        if stmts and isinstance(stmts[-1], ast.ExprStmt):
            trailing_expr = stmts[-1].expr
            stmts = stmts[:-1]

        return stmts, trailing_expr

    def convert_stmt(self, node: Any) -> Optional[ast.Stmt]:
        """Convert stmt dict to Stmt."""
        if not node or not isinstance(node, dict):
            return None

        rule = node.get('_rule')

        if rule == 'let_stmt':
            return self.convert_let_stmt(node)
        if rule == 'var_stmt':
            return self.convert_var_stmt(node)
        if rule == 'return_stmt':
            return self.convert_return_stmt(node)
        if rule == 'if_stmt':
            return self.convert_if_stmt(node)
        if rule == 'while_stmt':
            return self.convert_while_stmt(node)
        if rule == 'for_stmt':
            return self.convert_for_stmt(node)
        if rule == 'match_stmt':
            return self.convert_match_stmt(node)
        if rule == 'break_stmt':
            return ast.BreakStmt(span=_get_span(node))
        if rule == 'continue_stmt':
            return ast.ContinueStmt(span=_get_span(node))
        if rule == 'assert_stmt':
            return self.convert_assert_stmt(node)
        if rule == 'assign_stmt':
            return self.convert_assign_stmt(node)
        if rule == 'expr_stmt':
            return self.convert_expr_stmt(node)

        return None

    def convert_let_stmt(self, node: dict) -> ast.LetStmt:
        """Convert let_stmt dict."""
        # let_stmt: LET IDENT (COLON type)? ASSIGN expr NEWLINE
        name_token = node.get('1')
        type_node = None
        value_node = None

        # Check if there's a type annotation
        idx = 2
        if isinstance(node.get('2'), GenToken) and node['2'].kind == TokenType.COLON:
            type_node = node.get('3')
            idx = 4

        # Only look for ASSIGN at the expected position
        if isinstance(node.get(str(idx)), GenToken) and node[str(idx)].kind == TokenType.ASSIGN:
            value_node = node.get(str(idx + 1))

        return ast.LetStmt(
            span=_get_span(node),
            name=name_token.value if isinstance(name_token, GenToken) else '',
            type=self.convert_type(type_node),
            value=self.convert_expr(value_node)
        )

    def convert_var_stmt(self, node: dict) -> ast.VarStmt:
        """Convert var_stmt dict."""
        # var_stmt: VAR IDENT (COLON type)? (ASSIGN expr)? NEWLINE
        name_token = node.get('1')
        type_node = None
        value_node = None

        idx = 2
        if isinstance(node.get('2'), GenToken) and node['2'].kind == TokenType.COLON:
            type_node = node.get('3')
            idx = 4

        # Only look for ASSIGN at the expected position
        if isinstance(node.get(str(idx)), GenToken) and node[str(idx)].kind == TokenType.ASSIGN:
            value_node = node.get(str(idx + 1))

        return ast.VarStmt(
            span=_get_span(node),
            name=name_token.value if isinstance(name_token, GenToken) else '',
            type=self.convert_type(type_node),
            value=self.convert_expr(value_node)
        )

    def convert_return_stmt(self, node: dict) -> ast.ReturnStmt:
        """Convert return_stmt dict."""
        # return_stmt: RETURN expr? NEWLINE
        expr_node = node.get('1')
        return ast.ReturnStmt(
            span=_get_span(node),
            value=self.convert_expr(expr_node) if expr_node and not isinstance(expr_node, GenToken) else None
        )

    def convert_if_stmt(self, node: dict) -> ast.ExprStmt:
        """Convert if_stmt to ExprStmt wrapping If expression."""
        # This matches the hand-written parser behavior
        if_expr = self.convert_if_expr_from_stmt(node)
        return ast.ExprStmt(span=if_expr.span, expr=if_expr)

    def convert_if_expr_from_stmt(self, node: dict) -> ast.If:
        """Convert if_stmt dict to If expression."""
        # if_stmt: IF expr block else_clause? NEWLINE
        cond = self.convert_expr(node.get('1'))
        then_block = self.convert_block(node.get('2'))
        else_block = None
        else_clause = node.get('3')
        if else_clause and isinstance(else_clause, dict):
            else_block = self.convert_else_clause(else_clause)

        return ast.If(
            span=_get_span(node),
            cond=cond,
            then_block=then_block,
            else_block=else_block
        )

    def convert_else_clause(self, node: dict) -> Optional[ast.Block]:
        """Convert else_clause dict."""
        if not node:
            return None
        rule = node.get('_rule')
        if rule == 'else_clause':
            # else_clause: ELSE block | ELSE if_expr
            block_or_if = node.get('1')
            if isinstance(block_or_if, dict):
                if block_or_if.get('_rule') == 'block':
                    return self.convert_block(block_or_if)
                # else if - wrap in a block with single if statement
                if_expr = self.convert_if_expr_from_stmt(block_or_if)
                return ast.Block(
                    span=if_expr.span,
                    stmts=[],
                    expr=if_expr
                )
        return None

    def convert_while_stmt(self, node: dict) -> ast.WhileStmt:
        """Convert while_stmt dict."""
        # while_stmt: WHILE expr block NEWLINE
        cond = self.convert_expr(node.get('1'))
        body = self.convert_block(node.get('2'))
        return ast.WhileStmt(
            span=_get_span(node),
            cond=cond,
            body=body
        )

    def convert_for_stmt(self, node: dict) -> ast.ForStmt:
        """Convert for_stmt dict."""
        # for_stmt: FOR IDENT IN expr block NEWLINE
        var_token = node.get('1')
        iter_expr = self.convert_expr(node.get('3'))
        body = self.convert_block(node.get('4'))
        return ast.ForStmt(
            span=_get_span(node),
            var=var_token.value if isinstance(var_token, GenToken) else '',
            iter=iter_expr,
            body=body
        )

    def convert_match_stmt(self, node: dict) -> ast.ExprStmt:
        """Convert match_stmt to ExprStmt wrapping Match expression."""
        match_expr = self.convert_match_expr_from_stmt(node)
        return ast.ExprStmt(span=match_expr.span, expr=match_expr)

    def convert_match_expr_from_stmt(self, node: dict) -> ast.Match:
        """Convert match_stmt dict to Match expression."""
        # match_stmt: MATCH expr NEWLINE INDENT match_arms DEDENT
        expr = self.convert_expr(node.get('1'))
        arms = self.convert_match_arms(node.get('4'))
        return ast.Match(
            span=_get_span(node),
            expr=expr,
            arms=arms
        )

    def convert_match_arms(self, node: Any) -> List[ast.MatchArm]:
        """Convert match_arms dict to list of MatchArm."""
        if not node:
            return []
        # TODO: implement
        return []

    def convert_assert_stmt(self, node: dict) -> ast.AssertStmt:
        """Convert assert_stmt dict."""
        # assert_stmt: ASSERT expr NEWLINE | ASSERT expr COMMA STRING NEWLINE
        condition = self.convert_expr(node.get('1'))
        message = None
        msg_token = node.get('3')
        if isinstance(msg_token, GenToken) and msg_token.kind == TokenType.STRING:
            message = msg_token.value
        return ast.AssertStmt(
            span=_get_span(node),
            condition=condition,
            message=message
        )

    def convert_assign_stmt(self, node: dict) -> ast.AssignStmt:
        """Convert assign_stmt dict."""
        # assign_stmt: lvalue ASSIGN expr NEWLINE | lvalue op_assign expr NEWLINE
        target = self.convert_lvalue(node.get('0'))
        value = self.convert_expr(node.get('2'))
        return ast.AssignStmt(
            span=_get_span(node),
            target=target,
            value=value
        )

    def convert_lvalue(self, node: Any) -> ast.Expr:
        """Convert lvalue dict to an expression (used as assignment target)."""
        if not node:
            return None

        if isinstance(node, GenToken):
            if node.kind == TokenType.IDENT:
                return ast.Ident(span=_make_span(node), name=node.value)
            return None

        if isinstance(node, dict):
            rule = node.get('_rule')
            if rule == 'lvalue':
                first = node.get('0')
                second = node.get('1')

                # Check for STAR expr (dereference)
                if isinstance(first, GenToken) and first.kind == TokenType.STAR:
                    inner = self.convert_expr(node.get('1'))
                    return ast.UnaryOp(span=_get_span(node), op='*', operand=inner)

                # Check for IDENT followed by DOT or LBRACKET
                if isinstance(first, GenToken) and first.kind == TokenType.IDENT:
                    base = ast.Ident(span=_make_span(first), name=first.value)

                    # Check for IDENT DOT IDENT (field access: dst.start)
                    if isinstance(second, GenToken) and second.kind == TokenType.DOT:
                        field_token = node.get('2')
                        if isinstance(field_token, GenToken) and field_token.kind == TokenType.IDENT:
                            return ast.Field(span=_get_span(node), expr=base, field=field_token.value)

                    # Check for IDENT LBRACKET expr RBRACKET (index: arr[0])
                    if isinstance(second, GenToken) and second.kind == TokenType.LBRACKET:
                        index = self.convert_expr(node.get('2'))
                        return ast.Index(span=_get_span(node), expr=base, index=index)

                    # Just IDENT (no field or index access)
                    return base

                # Check for lvalue LBRACKET expr RBRACKET (index)
                if isinstance(first, dict) and first.get('_rule') == 'lvalue':
                    base = self.convert_lvalue(first)
                    if isinstance(second, GenToken) and second.kind == TokenType.LBRACKET:
                        index = self.convert_expr(node.get('2'))
                        return ast.Index(span=_get_span(node), expr=base, index=index)
                    # Check for lvalue DOT IDENT (nested field)
                    if isinstance(second, GenToken) and second.kind == TokenType.DOT:
                        field_token = node.get('2')
                        if isinstance(field_token, GenToken):
                            return ast.Field(span=_get_span(node), expr=base, field=field_token.value)

        # Fall back to converting as expression
        return self.convert_expr(node)

    def convert_expr_stmt(self, node: dict) -> ast.ExprStmt:
        """Convert expr_stmt dict."""
        # expr_stmt: expr NEWLINE
        expr = self.convert_expr(node.get('0'))
        return ast.ExprStmt(span=_get_span(node), expr=expr)

    def convert_expr(self, node: Any) -> Optional[ast.Expr]:
        """Convert expression dict to Expr."""
        if not node:
            return None

        if isinstance(node, GenToken):
            return self.convert_token_to_expr(node)

        if not isinstance(node, dict):
            return None

        rule = node.get('_rule')

        # Range expression (special handling for 0..5 syntax)
        if rule == 'range_expr':
            return self.convert_range_expr(node)

        # Binary expressions
        if rule in ('or_expr', 'and_expr', 'bit_or_expr', 'bit_xor_expr', 'bit_and_expr',
                    'cmp_expr', 'shift_expr', 'add_expr', 'mul_expr'):
            return self.convert_binary_expr(node)

        # Unary expressions
        if rule == 'unary_expr':
            return self.convert_unary_expr(node)

        # Try expression (postfix ?)
        if rule == 'try_expr':
            inner = self.convert_expr(node.get('0'))
            if inner and node.get('1'):  # has QUESTION
                return ast.TryOp(span=inner.span, expr=inner)
            return inner

        # Cast expression
        if rule == 'cast_expr':
            inner = self.convert_expr(node.get('0'))
            if inner and node.get('1'):  # has AS
                target_type = self.convert_type(node.get('2'))
                return ast.Cast(span=inner.span, expr=inner, target=target_type)
            return inner

        # Postfix expressions (call, index, field)
        if rule == 'postfix_expr':
            return self.convert_postfix_expr(node)

        # Primary expressions
        if rule == 'primary_expr':
            return self.convert_primary_expr(node)

        # If expression
        if rule == 'if_expr':
            return self.convert_if_expr(node)

        # Match expression
        if rule == 'match_expr':
            return self.convert_match_expr(node)

        # Block expression
        if rule == 'block_expr':
            return self.convert_block_expr(node)

        # Lambda/closure
        if rule == 'lambda_expr' or rule == 'closure_expr':
            return self.convert_closure_expr(node)

        # Struct literal
        if rule == 'struct_lit':
            return self.convert_struct_lit(node)

        # Array literal
        if rule == 'array_lit':
            return self.convert_array_lit(node)

        # Recursively try to extract expression
        for key in ['0', '1', 'left', 'right']:
            if key in node:
                result = self.convert_expr(node[key])
                if result:
                    return result

        return None

    def convert_token_to_expr(self, token: GenToken) -> Optional[ast.Expr]:
        """Convert a token directly to an expression."""
        span = _make_span(token)

        if token.kind == TokenType.NUMBER:
            value = token.value
            if '.' in str(value):
                return ast.FloatLit(span=span, value=float(value))
            else:
                return ast.IntLit(span=span, value=int(value))

        if token.kind == TokenType.STRING:
            return ast.StringLit(span=span, value=token.value)

        if token.kind == TokenType.CSTRING:
            # C-string literal: c"hello" -> *u8 (null-terminated)
            return ast.CStringLit(span=span, value=token.value)

        if token.kind == TokenType.SPAN_STRING:
            # Span string literal: s"hello" -> Span<u8> { ptr, len }
            return ast.SpanStringLit(span=span, value=token.value)

        if token.kind == TokenType.CHAR:
            value = token.value
            # Token value includes quotes, e.g., "'x'" or "'\n'"
            if isinstance(value, str) and len(value) >= 2:
                # Strip quotes
                inner = value[1:-1]  # Remove outer quotes
                # Handle escape sequences
                if len(inner) == 2 and inner[0] == '\\':
                    escape_char = inner[1]
                    escape_map = {
                        'n': ord('\n'), 't': ord('\t'), 'r': ord('\r'),
                        '0': 0, '\\': ord('\\'), "'": ord("'"), '"': ord('"')
                    }
                    value = escape_map.get(escape_char, ord(escape_char))
                elif len(inner) == 1:
                    value = ord(inner)
                else:
                    # Fallback for unexpected format
                    value = ord(inner[0]) if inner else 0
            return ast.CharLit(span=span, value=value)

        if token.kind == TokenType.TRUE:
            return ast.BoolLit(span=span, value=True)

        if token.kind == TokenType.FALSE:
            return ast.BoolLit(span=span, value=False)

        if token.kind == TokenType.NULL:
            return ast.NullLit(span=span)

        if token.kind == TokenType.IDENT:
            return ast.Ident(span=span, name=token.value)

        return None

    def convert_range_expr(self, node: dict) -> ast.Expr:
        """Convert range expression dict (0..5 or 0..=5)."""
        left = self.convert_expr(node.get('0'))
        op_token = node.get('1')
        right = self.convert_expr(node.get('2'))

        if isinstance(op_token, GenToken):
            inclusive = op_token.kind == TokenType.DOT_DOT_EQ if hasattr(TokenType, 'DOT_DOT_EQ') else op_token.value == '..='
            span = left.span if left else _get_span(node)
            return ast.Range(span=span, start=left, end=right, inclusive=inclusive)

        # Fallback to just returning the left side
        return left or right

    def convert_binary_expr(self, node: dict) -> ast.Expr:
        """Convert binary expression dict."""
        left = self.convert_expr(node.get('left') or node.get('0'))
        right = self.convert_expr(node.get('right') or node.get('2'))
        op_token = node.get('op') or node.get('1')

        if left and right and isinstance(op_token, GenToken):
            op_map = {
                TokenType.OR: '||',
                TokenType.AND: '&&',
                TokenType.PIPE: '|',
                TokenType.CARET: '^',
                TokenType.AMP: '&',
                TokenType.EQ: '==',
                TokenType.NE: '!=',
                TokenType.LT: '<',
                TokenType.GT: '>',
                TokenType.LE: '<=',
                TokenType.GE: '>=',
                TokenType.SHL: '<<',
                TokenType.SHR: '>>',
                TokenType.PLUS: '+',
                TokenType.MINUS: '-',
                TokenType.STAR: '*',
                TokenType.SLASH: '/',
                TokenType.PERCENT: '%',
                TokenType.DOT_DOT: '..',
            }
            op = op_map.get(op_token.kind, op_token.value)
            return ast.BinOp(span=left.span, op=op, left=left, right=right)

        return left or right

    def convert_unary_expr(self, node: dict) -> ast.Expr:
        """Convert unary expression dict."""
        # unary_expr: MINUS unary_expr | BANG unary_expr | ...
        token0 = node.get('0')

        if isinstance(token0, GenToken):
            op_map = {
                TokenType.MINUS: '-',
                TokenType.BANG: '!',
                TokenType.STAR: '*',
                TokenType.AMP: '&',
                TokenType.AMP_MUT: '&mut',
                TokenType.TILDE: '~',
            }
            if token0.kind in op_map:
                operand = self.convert_expr(node.get('1'))
                return ast.UnaryOp(
                    span=_make_span(token0),
                    op=op_map[token0.kind],
                    operand=operand
                )

        # Fall through to inner expr
        return self.convert_expr(node.get('1') or node.get('0'))

    def convert_postfix_expr(self, node: dict) -> ast.Expr:
        """Convert postfix expression dict."""
        # postfix_expr: primary_expr postfix_op*
        base = self.convert_expr(node.get('0'))
        ops = node.get('1') or []

        if not isinstance(ops, list):
            ops = [ops] if ops else []

        for op in ops:
            if isinstance(op, dict):
                op_rule = op.get('_rule')
                if op_rule == 'postfix_op':
                    token0 = op.get('0')
                    if isinstance(token0, GenToken):
                        if token0.kind == TokenType.LPAREN:
                            # Function call
                            args = self.convert_args(op.get('1'))
                            base = ast.Call(span=base.span, func=base, args=args)
                        elif token0.kind == TokenType.LBRACKET:
                            # Index
                            index = self.convert_expr(op.get('1'))
                            base = ast.Index(span=base.span, expr=base, index=index)
                        elif token0.kind == TokenType.DOT:
                            # Field or method call
                            field_token = op.get('1')
                            if isinstance(field_token, GenToken):
                                # Check if it's a method call
                                if op.get('2'):  # has LPAREN
                                    args = self.convert_args(op.get('3'))
                                    base = ast.MethodCall(
                                        span=base.span,
                                        expr=base,
                                        method=field_token.value,
                                        args=args
                                    )
                                else:
                                    base = ast.Field(
                                        span=base.span,
                                        expr=base,
                                        field=field_token.value
                                    )

        return base

    def convert_args(self, node: Any) -> List[ast.Expr]:
        """Convert args dict to list of Expr."""
        if not node:
            return []

        if isinstance(node, dict):
            rule = node.get('_rule')
            if rule == 'args':
                # args: expr COMMA args | expr
                result = []
                left = node.get('left')
                right = node.get('right')
                if left:
                    expr = self.convert_expr(left)
                    if expr:
                        result.append(expr)
                    result.extend(self.convert_args(right))
                else:
                    expr = self.convert_expr(node.get('0'))
                    if expr:
                        result.append(expr)
                return result
            else:
                # Single expression
                expr = self.convert_expr(node)
                return [expr] if expr else []

        return []

    def convert_primary_expr(self, node: dict) -> Optional[ast.Expr]:
        """Convert primary expression dict."""
        # primary_expr: NUMBER | STRING | TRUE | FALSE | IDENT struct_lit? | LPAREN expr RPAREN | ...
        token0 = node.get('0')

        if isinstance(token0, GenToken):
            # Check for IDENT struct_lit? (struct literal like Counter { value: 42 })
            if token0.kind == TokenType.IDENT:
                struct_lit = node.get('1')
                if struct_lit and isinstance(struct_lit, dict):
                    # This is a struct literal: Name { field: value, ... }
                    fields = self.convert_field_inits(struct_lit)
                    return ast.StructLit(
                        span=_make_span(token0),
                        name=token0.value,
                        fields=fields
                    )
            return self.convert_token_to_expr(token0)

        if isinstance(token0, dict):
            return self.convert_expr(token0)

        return None

    def convert_field_inits(self, node: Any) -> List[tuple]:
        """Convert field_inits to list of (name, expr) tuples."""
        fields = []
        if not node:
            return fields

        if isinstance(node, dict):
            rule = node.get('_rule')
            if rule == 'struct_lit':
                # struct_lit: LBRACE field_inits RBRACE
                return self.convert_field_inits(node.get('1'))
            if rule == 'field_inits':
                # field_inits: field_init COMMA field_inits | field_init
                init = node.get('0')
                if init:
                    field = self.convert_field_init(init)
                    if field:
                        fields.append(field)
                rest = node.get('2')
                if rest:
                    fields.extend(self.convert_field_inits(rest))
            if rule == 'field_init':
                field = self.convert_field_init(node)
                if field:
                    fields.append(field)

        return fields

    def convert_field_init(self, node: dict) -> Optional[tuple]:
        """Convert field_init to (name, expr) tuple."""
        if not isinstance(node, dict):
            return None

        # field_init: IDENT COLON expr
        name_token = node.get('0')
        value = self.convert_expr(node.get('2'))

        if isinstance(name_token, GenToken) and name_token.kind == TokenType.IDENT:
            return (name_token.value, value)
        return None

    def convert_if_expr(self, node: dict) -> ast.If:
        """Convert if_expr dict to If expression."""
        # if_expr: IF expr block else_clause
        cond = self.convert_expr(node.get('1'))
        then_block = self.convert_block(node.get('2'))
        else_block = self.convert_else_clause(node.get('3'))

        return ast.If(
            span=_get_span(node),
            cond=cond,
            then_block=then_block,
            else_block=else_block
        )

    def convert_match_expr(self, node: dict) -> ast.Match:
        """Convert match_expr dict."""
        # match_expr: MATCH expr NEWLINE INDENT match_arms DEDENT
        expr = self.convert_expr(node.get('1'))
        arms = self.convert_match_arms(node.get('4'))
        return ast.Match(
            span=_get_span(node),
            expr=expr,
            arms=arms
        )

    def convert_block_expr(self, node: dict) -> ast.Block:
        """Convert block_expr dict."""
        # block_expr: LBRACE stmts expr? RBRACE
        stmts_node = node.get('1')
        stmts, trailing = self.convert_stmts(stmts_node)
        if not trailing:
            trailing = self.convert_expr(node.get('2'))
        return ast.Block(
            span=_get_span(node),
            stmts=stmts,
            expr=trailing
        )

    def convert_closure_expr(self, node: dict) -> ast.Closure:
        """Convert closure expression dict."""
        # closure_expr: PIPE closure_params PIPE expr
        # TODO: implement properly
        return ast.Closure(
            span=_get_span(node),
            params=[],
            body=self.convert_expr(node.get('3'))
        )

    def convert_struct_lit(self, node: dict) -> ast.StructLit:
        """Convert struct literal dict."""
        # struct_lit: IDENT LBRACE struct_fields RBRACE
        name_token = node.get('0')
        # TODO: convert fields properly
        return ast.StructLit(
            span=_get_span(node),
            name=name_token.value if isinstance(name_token, GenToken) else '',
            fields=[]
        )

    def convert_array_lit(self, node: dict) -> ast.ArrayLit:
        """Convert array literal dict."""
        # array_lit: LBRACKET args? RBRACKET
        elements = self.convert_args(node.get('1'))
        return ast.ArrayLit(
            span=_get_span(node),
            elements=elements
        )

    # Stub implementations for other item types
    def convert_struct_def(self, node: dict) -> ast.StructDef:
        """Convert struct_def dict to StructDef."""
        # struct_def: STRUCT IDENT type_params? NEWLINE INDENT struct_fields DEDENT
        name_token = node.get('1')
        name = name_token.value if isinstance(name_token, GenToken) else ''

        # Parse type params (generic parameters like <T>)
        type_params = []
        type_params_node = node.get('2')
        if type_params_node:
            type_params = self.convert_type_params(type_params_node)

        # Parse fields
        fields = []
        fields_node = node.get('5')
        if fields_node:
            fields = self.convert_struct_fields(fields_node)

        return ast.StructDef(span=_get_span(node), name=name, type_params=type_params, fields=fields)

    def convert_struct_fields(self, node: Any) -> List[tuple]:
        """Convert struct_fields dict to list of (name, type) tuples."""
        fields = []
        if not node:
            return fields

        if isinstance(node, dict):
            rule = node.get('_rule')
            if rule == 'struct_fields':
                # struct_fields: struct_field struct_fields | struct_field
                field_node = node.get('0')
                rest = node.get('1')

                if field_node:
                    field = self.convert_struct_field(field_node)
                    if field:
                        fields.append(field)

                if rest:
                    fields.extend(self.convert_struct_fields(rest))
            elif rule == 'struct_field':
                field = self.convert_struct_field(node)
                if field:
                    fields.append(field)

        return fields

    def convert_struct_field(self, node: dict) -> Optional[tuple]:
        """Convert struct_field dict to (name, type) tuple."""
        if not isinstance(node, dict):
            return None

        # struct_field: IDENT COLON type NEWLINE
        name_token = node.get('0')
        type_node = node.get('2')

        name = name_token.value if isinstance(name_token, GenToken) else ''
        field_type = self.convert_type(type_node)

        return (name, field_type)

    def convert_type_params(self, node: Any) -> List[str]:
        """Convert type_params to list of type parameter names."""
        params = []
        if not node:
            return params

        if isinstance(node, dict):
            rule = node.get('_rule')
            if rule == 'type_params':
                # type_params: LT type_param_list GT
                param_list = node.get('1')
                if param_list:
                    params = self.convert_type_param_list(param_list)

        return params

    def convert_type_param_list(self, node: Any) -> List[str]:
        """Convert type_param_list to list of names."""
        params = []
        if not node:
            return params

        if isinstance(node, dict):
            rule = node.get('_rule')
            if rule == 'type_param_list':
                # type_param_list: IDENT COMMA type_param_list | IDENT
                ident = node.get('0')
                if isinstance(ident, GenToken) and ident.kind == TokenType.IDENT:
                    params.append(ident.value)
                rest = node.get('2')
                if rest:
                    params.extend(self.convert_type_param_list(rest))
        elif isinstance(node, GenToken) and node.kind == TokenType.IDENT:
            params.append(node.value)

        return params

    def convert_enum_def(self, node: dict) -> ast.EnumDef:
        return ast.EnumDef(span=_get_span(node), name='', variants=[])

    def convert_const_def(self, node: dict) -> ast.ConstDef:
        """Convert const_def dict to ConstDef."""
        # const_def: CONST IDENT COLON type ASSIGN expr NEWLINE
        name_token = node.get('1')
        type_node = node.get('3')
        value_node = node.get('5')
        return ast.ConstDef(
            span=_get_span(node),
            name=name_token.value if isinstance(name_token, GenToken) else '',
            type=self.convert_type(type_node),
            value=self.convert_expr(value_node)
        )

    def convert_type_alias(self, node: dict) -> ast.TypeAlias:
        return ast.TypeAlias(
            span=_get_span(node),
            name='',
            target=ast.NamedType(span=_get_span(node), name='i32')
        )

    def convert_trait_def(self, node: dict) -> ast.TraitDef:
        return ast.TraitDef(span=_get_span(node), name='', methods=[])

    def convert_impl_block(self, node: dict) -> ast.ImplBlock:
        return ast.ImplBlock(span=_get_span(node), trait_name=None, type_name='', methods=[])

    def convert_import(self, node: dict) -> ast.Import:
        """Convert import_stmt dict to Import."""
        # import_stmt: IMPORT module_path NEWLINE
        module_path_node = node.get('1')
        path = self.convert_module_path(module_path_node)
        return ast.Import(span=_get_span(node), path=path)

    def convert_module_path(self, node: Any) -> List[str]:
        """Convert module_path dict to list of path components."""
        if not node:
            return []
        if isinstance(node, dict):
            rule = node.get('_rule')
            if rule == 'module_path':
                # module_path: IDENT DOT module_path | IDENT
                ident_token = node.get('0')
                result = []
                if isinstance(ident_token, GenToken):
                    result.append(ident_token.value)
                # Check if there's a continued path
                rest = node.get('2')
                if rest:
                    if isinstance(rest, dict):
                        result.extend(self.convert_module_path(rest))
                    elif isinstance(rest, GenToken) and rest.kind == TokenType.IDENT:
                        result.append(rest.value)
                return result
        return []

    def convert_global_var(self, node: dict) -> ast.VarDef:
        """Convert global_var dict to VarDef AST node.

        Grammar:
            global_var: VAR IDENT COLON type ASSIGN expr NEWLINE  -> indices 0,1,2,3,4,5,6
                      | VAR IDENT COLON type NEWLINE              -> indices 0,1,2,3,4
        """
        name_token = node.get('1')
        type_node = node.get('3')  # After VAR, IDENT, COLON
        value_node = None

        # Check if there's an assignment (6 items vs 5 items)
        if isinstance(node.get('4'), GenToken) and node['4'].kind == TokenType.ASSIGN:
            value_node = node.get('5')

        return ast.VarDef(
            span=_get_span(node),
            name=name_token.value if isinstance(name_token, GenToken) else '',
            type=self.convert_type(type_node),
            value=self.convert_expr(value_node) if value_node else None
        )


class ParseError(Exception):
    """Parser error with source location."""
    def __init__(self, message: str, span: Span):
        self.message = message
        self.span = span
        super().__init__(f"{span}: {message}")


class Parser:
    """
    Parser for Ritz source code.

    This adapter provides the same interface as the hand-written parser.py
    but uses the generated parser internally.

    Note: Unlike the hand-written parser, this requires the source string
    to be preserved and passed separately, OR the tokens must include
    a reference to the source. For compatibility, we accept tokens but
    require the source to be set via set_source().
    """

    # Class variable to hold source during parsing
    _sources: dict = {}

    def __init__(self, tokens: List[RitzToken], source: str = None):
        self._ritz_tokens = tokens
        self._source_file = tokens[0].span.file if tokens else "<source>"
        self._source = source
        # Also check class-level source cache
        if source is None and self._source_file in Parser._sources:
            self._source = Parser._sources[self._source_file]

    @classmethod
    def set_source(cls, source_file: str, source: str):
        """Cache source string for later use by Parser instances."""
        cls._sources[source_file] = source

    def parse_module(self) -> ast.Module:
        """Parse the token stream into a Module AST."""
        if self._source is None:
            raise ParseError(
                "Parser adapter needs source string. "
                "Call Parser.set_source(file, source) before creating Parser, "
                "or pass source= to Parser constructor.",
                Span(file=self._source_file, line=1, column=1, length=1)
            )

        return parse_source(self._source, self._source_file)


def parse_source(source: str, source_file: str = "<source>") -> ast.Module:
    """
    Parse Ritz source code into a Module AST.

    This is the main entry point for the generated parser.
    """
    lexer = GenLexer(source)
    tokens = lexer.tokenize()
    parser = GenParser(tokens)
    parsed = parser.parse_module()

    converter = ASTConverter(source_file)
    return converter.convert_module(parsed)
