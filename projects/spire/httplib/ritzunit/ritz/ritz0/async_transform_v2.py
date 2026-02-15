"""
True Async Function Transformation for ritz0 (v2)

Transforms async functions into proper state machines that:
1. Return Poll<T> encoding: -1 = Pending, >=0 = Ready(value)
2. Switch on state field to resume at correct point
3. Poll inner futures and propagate Pending

Example transformation:

    # Source
    async fn fetch(x: i32) -> i32
        let a = await get_value(x)
        let b = await get_other(a)
        a + b

    # Transformed to:
    struct fetch_Future
        state: i32
        x: i32
        a: i32
        b: i32
        # Inner futures stored inline for simple cases

    fn fetch(x: i32) -> fetch_Future
        fetch_Future { state: 0, x: x, a: 0, b: 0 }

    fn fetch_poll(self: *fetch_Future) -> i32
        # State 0: Start, call first await
        if (*self).state == 0
            let inner_result = get_value_poll(...)
            if inner_result == -1  # Pending
                return -1
            (*self).a = inner_result
            (*self).state = 1

        # State 1: After first await, call second
        if (*self).state == 1
            let inner_result = get_other_poll(...)
            if inner_result == -1
                return -1
            (*self).b = inner_result
            (*self).state = 2

        # State 2: Complete
        return (*self).a + (*self).b
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
import ritz_ast as rast


# Poll encoding: -1 = Pending, value >= 0 = Ready(value)
POLL_PENDING = -1


@dataclass
class AwaitPoint:
    """Represents a single await expression in an async function."""
    index: int                    # 0-based index of this await
    expr: rast.Await             # The await expression
    result_var: str              # Variable to store result (e.g., 'a' for 'let a = await ...')
    result_type: rast.Type       # Type of the result
    span: Optional[rast.Span] = None


@dataclass
class AsyncFnAnalysis:
    """Analysis results for an async function."""
    fn_def: rast.FnDef
    await_points: List[AwaitPoint]
    all_locals: Dict[str, rast.Type]  # name -> type for all locals
    cross_await_locals: Set[str]      # locals that live across await points


class AsyncAnalyzer:
    """Analyzes an async function to find await points."""

    def __init__(self):
        self.await_points: List[AwaitPoint] = []
        self.current_locals: Dict[str, rast.Type] = {}
        self.await_index = 0
        self.current_let_target: Optional[Tuple[str, rast.Type]] = None

    def analyze(self, fn_def: rast.FnDef) -> AsyncFnAnalysis:
        """Analyze an async function."""
        if not fn_def.is_async:
            raise ValueError(f"Function {fn_def.name} is not async")

        self.await_points = []
        self.current_locals = {}
        self.await_index = 0

        # Add parameters as locals
        for param in fn_def.params:
            self.current_locals[param.name] = param.type

        # Walk the function body
        if fn_def.body:
            self._analyze_block(fn_def.body)

        # Compute which locals live across await points
        cross_await = set()
        for i, ap in enumerate(self.await_points):
            # All locals defined before this await that are used after it
            for var_name in self.current_locals.keys():
                cross_await.add(var_name)

        return AsyncFnAnalysis(
            fn_def=fn_def,
            await_points=self.await_points,
            all_locals=dict(self.current_locals),
            cross_await_locals=cross_await
        )

    def _analyze_block(self, block: rast.Block):
        """Analyze a block for await points."""
        for stmt in block.stmts:
            self._analyze_stmt(stmt)
        if block.expr:
            self._analyze_expr(block.expr)

    def _analyze_stmt(self, stmt: rast.Stmt):
        """Analyze a statement."""
        if isinstance(stmt, rast.LetStmt):
            # Track the let target for await point association
            self.current_let_target = (stmt.name, stmt.type)
            if stmt.value:
                self._analyze_expr(stmt.value)
            self.current_let_target = None
            self.current_locals[stmt.name] = stmt.type
        elif isinstance(stmt, rast.VarStmt):
            self.current_let_target = (stmt.name, stmt.type)
            if stmt.value:
                self._analyze_expr(stmt.value)
            self.current_let_target = None
            self.current_locals[stmt.name] = stmt.type
        elif isinstance(stmt, rast.ExprStmt):
            self._analyze_expr(stmt.expr)
        elif isinstance(stmt, rast.AssignStmt):
            self._analyze_expr(stmt.value)
        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value:
                self._analyze_expr(stmt.value)
        # Note: Ritz uses If as expression, not IfStmt
        # If statements come as ExprStmt containing If expression
        elif isinstance(stmt, rast.WhileStmt):
            self._analyze_expr(stmt.cond)
            self._analyze_block(stmt.body)

    def _analyze_expr(self, expr: rast.Expr):
        """Analyze an expression, recording await points."""
        if isinstance(expr, rast.Await):
            # Found an await point!
            result_var = f"__await_result_{self.await_index}"
            result_type = rast.NamedType(span=rast.Span(0,0,0,0), name='i32')

            # If we're in a let statement, use that variable name
            if self.current_let_target:
                result_var, result_type = self.current_let_target
            else:
                # Add synthetic result variable to locals so it gets a field
                self.current_locals[result_var] = result_type

            ap = AwaitPoint(
                index=self.await_index,
                expr=expr,
                result_var=result_var,
                result_type=result_type,
                span=getattr(expr, 'span', None)
            )
            self.await_points.append(ap)
            self.await_index += 1
            # Also analyze the inner expression
            self._analyze_expr(expr.expr)

        elif isinstance(expr, rast.BinOp):
            self._analyze_expr(expr.left)
            self._analyze_expr(expr.right)
        elif isinstance(expr, rast.UnaryOp):
            self._analyze_expr(expr.operand)
        elif isinstance(expr, rast.Call):
            if not isinstance(expr.func, rast.Ident):
                self._analyze_expr(expr.func)
            for arg in expr.args:
                self._analyze_expr(arg)
        elif isinstance(expr, rast.MethodCall):
            self._analyze_expr(expr.expr)
            for arg in expr.args:
                self._analyze_expr(arg)
        elif isinstance(expr, rast.Field):
            self._analyze_expr(expr.expr)
        elif isinstance(expr, rast.Index):
            self._analyze_expr(expr.expr)
            self._analyze_expr(expr.index)
        elif isinstance(expr, rast.If):
            self._analyze_expr(expr.cond)
            self._analyze_block(expr.then_block)
            if expr.else_block:
                self._analyze_block(expr.else_block)
        elif isinstance(expr, rast.Block):
            self._analyze_block(expr)
        elif isinstance(expr, rast.Cast):
            self._analyze_expr(expr.expr)
        elif isinstance(expr, rast.Match):
            self._analyze_expr(expr.value)
            for arm in expr.arms:
                if arm.body:
                    self._analyze_expr(arm.body)
        elif isinstance(expr, rast.StructLit):
            for f in expr.fields:
                if isinstance(f, tuple):
                    self._analyze_expr(f[1])
                else:
                    self._analyze_expr(f.value)
        elif isinstance(expr, rast.ArrayLit):
            for elem in expr.elements:
                self._analyze_expr(elem)


@dataclass
class AsyncStateMachine:
    """Generated state machine for an async function."""
    original_fn: rast.FnDef
    future_struct: rast.StructDef
    constructor_fn: rast.FnDef
    poll_fn: rast.FnDef
    num_states: int


class TrueAsyncGenerator:
    """
    Generates TRUE state machine code for an async function.

    Unlike the MVP, this generates:
    1. poll() returns i32 with -1 = Pending, value = Ready(value)
    2. State machine with if/else chain for each state
    3. Proper suspension on await

    When async_functions is provided, recognizes calls to async functions
    and generates proper foo() + foo_poll() sequences.
    """

    def __init__(self, analysis: AsyncFnAnalysis, async_functions: Optional[Set[str]] = None):
        self.analysis = analysis
        self.fn_def = analysis.fn_def
        self.dummy_span = rast.Span(0, 0, 0, 0)
        # Set of known async function names (for await transformation)
        self.async_functions = async_functions or set()

    def generate(self) -> AsyncStateMachine:
        """Generate the complete state machine."""
        future_struct = self._generate_future_struct()
        constructor_fn = self._generate_constructor()
        poll_fn = self._generate_poll_fn()

        return AsyncStateMachine(
            original_fn=self.fn_def,
            future_struct=future_struct,
            constructor_fn=constructor_fn,
            poll_fn=poll_fn,
            num_states=len(self.analysis.await_points) + 1
        )

    def _make_named_type(self, name: str) -> rast.NamedType:
        return rast.NamedType(span=self.dummy_span, name=name)

    def _make_ptr_type(self, inner: rast.Type) -> rast.PtrType:
        return rast.PtrType(span=self.dummy_span, inner=inner, mutable=True)

    def _make_int(self, value: int) -> rast.IntLit:
        return rast.IntLit(span=self.dummy_span, value=value)

    def _make_ident(self, name: str) -> rast.Ident:
        return rast.Ident(span=self.dummy_span, name=name)

    def _make_self_field(self, field_name: str) -> rast.Field:
        """Generate (*self).field_name"""
        return rast.Field(
            span=self.dummy_span,
            expr=rast.UnaryOp(
                span=self.dummy_span,
                op='*',
                operand=self._make_ident('self')
            ),
            field=field_name
        )

    def _make_binop(self, op: str, left: rast.Expr, right: rast.Expr) -> rast.BinOp:
        return rast.BinOp(span=self.dummy_span, op=op, left=left, right=right)

    def _is_async_call(self, expr: rast.Expr) -> bool:
        """Check if expr is a call to a known async function."""
        if isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident):
            return expr.func.name in self.async_functions
        return False

    def _generate_future_struct(self) -> rast.StructDef:
        """Generate the Future struct definition."""
        fields = []

        # State field (use __state to avoid collision with user params named 'state')
        fields.append(('__state', self._make_named_type('i32')))

        # Parameter fields
        for param in self.fn_def.params:
            fields.append((param.name, param.type))

        # Cross-await locals (results of awaits)
        param_names = {p.name for p in self.fn_def.params}
        for var_name in sorted(self.analysis.cross_await_locals):
            if var_name not in param_names:
                var_type = self.analysis.all_locals.get(var_name)
                if var_type:
                    fields.append((var_name, var_type))

        struct_name = f"{self.fn_def.name}_Future"
        return rast.StructDef(
            span=self.dummy_span,
            name=struct_name,
            fields=fields
        )

    def _generate_constructor(self) -> rast.FnDef:
        """Generate constructor function that returns the Future struct."""
        future_name = f"{self.fn_def.name}_Future"

        # Build struct literal fields
        struct_fields = []
        struct_fields.append(('__state', self._make_int(0)))

        for param in self.fn_def.params:
            struct_fields.append((param.name, self._make_ident(param.name)))

        # Initialize cross-await locals with 0
        param_names = {p.name for p in self.fn_def.params}
        for var_name in sorted(self.analysis.cross_await_locals):
            if var_name not in param_names:
                struct_fields.append((var_name, self._make_int(0)))

        struct_lit = rast.StructLit(
            span=self.dummy_span,
            name=future_name,
            fields=struct_fields
        )

        body = rast.Block(
            span=self.dummy_span,
            stmts=[],
            expr=struct_lit
        )

        return rast.FnDef(
            span=self.dummy_span,
            name=self.fn_def.name,
            params=self.fn_def.params,
            ret_type=self._make_named_type(future_name),
            body=body,
            is_async=False
        )

    def _generate_poll_fn(self) -> rast.FnDef:
        """Generate poll function with proper state machine.

        Returns i32: -1 = Pending, value >= 0 = Ready(value)

        Structure:
            if (*self).state == 0
                # Initial state - execute up to first await
                ...
            if (*self).state == 1
                # After first await - execute to second await
                ...
            # Final state - return result
            return final_value
        """
        future_name = f"{self.fn_def.name}_Future"
        poll_fn_name = f"{self.fn_def.name}_poll"

        self_param = rast.Param(
            span=self.dummy_span,
            name='self',
            type=self._make_ptr_type(self._make_named_type(future_name))
        )

        # Return type is i32 (Poll encoding)
        ret_type = self._make_named_type('i32')

        # Generate the state machine body
        body = self._generate_state_machine_body()

        return rast.FnDef(
            span=self.dummy_span,
            name=poll_fn_name,
            params=[self_param],
            ret_type=ret_type,
            body=body,
            is_async=False
        )

    def _generate_state_machine_body(self) -> rast.Block:
        """Generate the state machine body with if/else for each state."""
        stmts = []

        # If no await points, just execute and return the result
        if not self.analysis.await_points:
            # Transform body to access params through self
            transformer = SimpleBodyTransformer(self.analysis, self.fn_def)
            transformed = transformer.transform(self.fn_def.body)
            return transformed

        # Generate state checks for each await point
        for i, await_point in enumerate(self.analysis.await_points):
            state_check = self._generate_state_handler(i, await_point)
            stmts.append(state_check)

        # Final state: compute and return the result
        final_expr = self._generate_final_return()

        return rast.Block(
            span=self.dummy_span,
            stmts=stmts,
            expr=final_expr
        )

    def _generate_state_handler(self, state_index: int, await_point: AwaitPoint) -> rast.ExprStmt:
        """Generate handler for a specific state.

        if (*self).state == N
            # For async function calls: foo(x) + foo_poll(&future)
            # For other expressions: call directly

            # Check for Pending:
            # if __inner_result == -1
            #     return -1

            # Store result
            (*self).result_var = __inner_result

            # Advance state
            (*self).state = N + 1

        Note: Ritz uses `If` as expression, wrapped in `ExprStmt` for use as statement.
        """
        then_stmts = []

        # Get the inner expression (what's being awaited)
        inner_expr = await_point.expr.expr

        # Transform inner_expr to access parameters through self
        # e.g., `x` becomes `(*self).x`
        transformer = SimpleBodyTransformer(self.analysis, self.fn_def)

        inner_result_var = f"__inner_result_{state_index}"

        # Check if this is a call to an async function
        if self._is_async_call(inner_expr):
            # Async function call: need to call foo(args) then foo_poll(&future)
            fn_name = inner_expr.func.name
            future_var = f"__future_{state_index}"
            future_type_name = f"{fn_name}_Future"

            # Transform arguments to access through self
            transformed_args = [transformer._transform_expr(arg) for arg in inner_expr.args]

            # var __future_N: foo_Future = foo(args)
            create_future = rast.VarStmt(
                span=self.dummy_span,
                name=future_var,
                type=self._make_named_type(future_type_name),
                value=rast.Call(
                    span=self.dummy_span,
                    func=self._make_ident(fn_name),
                    args=transformed_args
                )
            )
            then_stmts.append(create_future)

            # let __inner_result: i32 = foo_poll(&__future_N)
            poll_call = rast.LetStmt(
                span=self.dummy_span,
                name=inner_result_var,
                type=self._make_named_type('i32'),
                value=rast.Call(
                    span=self.dummy_span,
                    func=self._make_ident(f"{fn_name}_poll"),
                    args=[rast.UnaryOp(
                        span=self.dummy_span,
                        op='&',
                        operand=self._make_ident(future_var)
                    )]
                )
            )
            then_stmts.append(poll_call)
        else:
            # Not an async function - call directly (existing behavior)
            transformed_inner_expr = transformer._transform_expr(inner_expr)

            # let __inner_result: i32 = inner_expr (transformed)
            inner_call = rast.LetStmt(
                span=self.dummy_span,
                name=inner_result_var,
                type=self._make_named_type('i32'),
                value=transformed_inner_expr
            )
            then_stmts.append(inner_call)

        # Check for Pending and propagate
        # if __inner_result == -1
        #     return -1
        # Using rast.If (expression) wrapped in ExprStmt
        pending_check_if = rast.If(
            span=self.dummy_span,
            cond=self._make_binop(
                '==',
                self._make_ident(inner_result_var),
                # -1 for Pending
                rast.BinOp(
                    span=self.dummy_span,
                    op='-',
                    left=self._make_int(0),
                    right=self._make_int(1)
                )
            ),
            then_block=rast.Block(
                span=self.dummy_span,
                stmts=[rast.ReturnStmt(
                    span=self.dummy_span,
                    value=rast.BinOp(
                        span=self.dummy_span,
                        op='-',
                        left=self._make_int(0),
                        right=self._make_int(1)
                    )
                )],
                expr=None
            ),
            else_block=None
        )
        then_stmts.append(rast.ExprStmt(span=self.dummy_span, expr=pending_check_if))

        # Store result: (*self).result_var = __inner_result
        store_result = rast.AssignStmt(
            span=self.dummy_span,
            target=self._make_self_field(await_point.result_var),
            value=self._make_ident(inner_result_var)
        )
        then_stmts.append(store_result)

        # Advance state: (*self).__state = N + 1
        advance_state = rast.AssignStmt(
            span=self.dummy_span,
            target=self._make_self_field('__state'),
            value=self._make_int(state_index + 1)
        )
        then_stmts.append(advance_state)

        # Build the if expression (not statement) and wrap in ExprStmt
        state_cond = self._make_binop(
            '==',
            self._make_self_field('__state'),
            self._make_int(state_index)
        )

        state_if = rast.If(
            span=self.dummy_span,
            cond=state_cond,
            then_block=rast.Block(
                span=self.dummy_span,
                stmts=then_stmts,
                expr=None
            ),
            else_block=None
        )

        return rast.ExprStmt(span=self.dummy_span, expr=state_if)

    def _generate_final_return(self) -> rast.Expr:
        """Generate the final return expression.

        Transform the original body's return expression to use self.field
        for any variables that were stored across awaits.
        """
        # Get the final expression from the body
        if self.fn_def.body.expr:
            transformer = SimpleBodyTransformer(self.analysis, self.fn_def)
            return transformer._transform_expr(self.fn_def.body.expr)

        # Default: return 0
        return self._make_int(0)


class SimpleBodyTransformer:
    """Simple transformer that replaces cross-await vars with self.field."""

    def __init__(self, analysis: AsyncFnAnalysis, fn_def: rast.FnDef):
        self.analysis = analysis
        self.fn_def = fn_def
        self.dummy_span = rast.Span(0, 0, 0, 0)
        self.cross_await_vars = analysis.cross_await_locals
        self.param_names = {p.name for p in fn_def.params}

    def transform(self, block: rast.Block) -> rast.Block:
        new_stmts = [self._transform_stmt(s) for s in block.stmts]
        new_expr = self._transform_expr(block.expr) if block.expr else None
        return rast.Block(span=block.span, stmts=new_stmts, expr=new_expr)

    def _transform_stmt(self, stmt: rast.Stmt) -> rast.Stmt:
        if isinstance(stmt, rast.LetStmt):
            new_value = self._transform_expr(stmt.value) if stmt.value else None
            return rast.LetStmt(
                span=stmt.span,
                name=stmt.name,
                type=stmt.type,
                value=new_value
            )
        elif isinstance(stmt, rast.ReturnStmt):
            new_value = self._transform_expr(stmt.value) if stmt.value else None
            return rast.ReturnStmt(span=stmt.span, value=new_value)
        elif isinstance(stmt, rast.ExprStmt):
            return rast.ExprStmt(span=stmt.span, expr=self._transform_expr(stmt.expr))
        return stmt

    def _transform_expr(self, expr: rast.Expr) -> rast.Expr:
        if expr is None:
            return None

        if isinstance(expr, rast.Await):
            # Should not reach here in final transform - awaits handled by state machine
            return self._transform_expr(expr.expr)

        elif isinstance(expr, rast.Ident):
            # If this is a cross-await variable or parameter, access through self
            if expr.name in self.cross_await_vars or expr.name in self.param_names:
                return rast.Field(
                    span=expr.span,
                    expr=rast.UnaryOp(
                        span=expr.span,
                        op='*',
                        operand=rast.Ident(span=expr.span, name='self')
                    ),
                    field=expr.name
                )
            return expr

        elif isinstance(expr, rast.BinOp):
            return rast.BinOp(
                span=expr.span,
                op=expr.op,
                left=self._transform_expr(expr.left),
                right=self._transform_expr(expr.right)
            )

        elif isinstance(expr, rast.UnaryOp):
            return rast.UnaryOp(
                span=expr.span,
                op=expr.op,
                operand=self._transform_expr(expr.operand)
            )

        elif isinstance(expr, rast.Call):
            new_args = [self._transform_expr(a) for a in expr.args]
            new_func = expr.func
            if not isinstance(expr.func, rast.Ident):
                new_func = self._transform_expr(expr.func)
            return rast.Call(span=expr.span, func=new_func, args=new_args)

        elif isinstance(expr, rast.Cast):
            return rast.Cast(
                span=expr.span,
                expr=self._transform_expr(expr.expr),
                target=expr.target
            )

        return expr


def analyze_async_function(fn_def: rast.FnDef) -> AsyncFnAnalysis:
    """Convenience function to analyze an async function."""
    analyzer = AsyncAnalyzer()
    return analyzer.analyze(fn_def)


def generate_state_machine(fn_def: rast.FnDef, async_functions: Optional[Set[str]] = None) -> AsyncStateMachine:
    """Generate a TRUE state machine for an async function.

    Args:
        fn_def: The async function definition to transform
        async_functions: Set of known async function names (for await transformation)
    """
    analysis = analyze_async_function(fn_def)
    generator = TrueAsyncGenerator(analysis, async_functions)
    return generator.generate()


# ============================================================================
# Tests
# ============================================================================

def _test_basic():
    """Test basic async function transformation."""
    from parser import parse

    code = """
async fn simple(x: i32) -> i32
    x + 1
"""
    module = parse(code)
    fn = module.items[0]

    sm = generate_state_machine(fn)

    assert sm.future_struct.name == "simple_Future"
    assert sm.constructor_fn.name == "simple"
    assert sm.poll_fn.name == "simple_poll"
    print("✓ Basic test passed")


def _test_with_await():
    """Test async function with await."""
    from parser import parse

    code = """
async fn fetch(x: i32) -> i32
    let a: i32 = await get_value(x)
    a + 1
"""
    module = parse(code)
    fn = module.items[0]

    analysis = analyze_async_function(fn)
    assert len(analysis.await_points) == 1
    assert analysis.await_points[0].result_var == 'a'

    sm = generate_state_machine(fn)
    assert sm.num_states == 2  # state 0 + 1 await
    print("✓ Await test passed")


if __name__ == '__main__':
    _test_basic()
    _test_with_await()
    print("All tests passed!")
