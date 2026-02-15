"""
Async Function Transformation for ritz0

Transforms async functions into state machines that implement the Future trait.

Example transformation:

    # Source
    async fn fetch(x: i32) -> i32
        let a = await get_value(x)
        let b = await get_other(a)
        a + b

    # Transformed to:
    struct FetchFuture
        state: i32
        # Parameters (captured)
        x: i32
        # Locals that live across await points
        a: i32
        b: i32

    fn fetch(x: i32) -> FetchFuture
        FetchFuture { state: 0, x: x, a: 0, b: 0 }

    fn fetch_poll(self: *FetchFuture, cx: *Context) -> Poll$i32
        match self.state
            0 =>
                # Start get_value, advance state
                ... poll inner future ...
            1 =>
                # Resume after first await
                ...
            2 =>
                # Return final result
                return Poll$i32::Ready(self.a + self.b)

This module provides:
1. AwaitPointAnalysis - identifies await points in async functions
2. AsyncTransform - transforms async fn to state machine
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
import ritz_ast as rast


@dataclass
class AwaitPoint:
    """Represents a single await expression in an async function."""
    index: int                    # 0-based index of this await
    expr: rast.Await             # The await expression
    live_vars: Set[str]          # Variables live across this await
    span: Optional[rast.Span] = None


@dataclass
class AsyncFnAnalysis:
    """Analysis results for an async function."""
    fn_def: rast.FnDef
    await_points: List[AwaitPoint]
    all_locals: Dict[str, rast.Type]  # name -> type for all locals
    cross_await_locals: Set[str]      # locals that live across await points


class AsyncAnalyzer:
    """Analyzes an async function to find await points and live variables."""

    def __init__(self):
        self.await_points: List[AwaitPoint] = []
        self.current_locals: Dict[str, rast.Type] = {}
        self.await_index = 0

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
        for ap in self.await_points:
            cross_await.update(ap.live_vars)

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
            if stmt.value:
                self._analyze_expr(stmt.value)
            self.current_locals[stmt.name] = stmt.type
        elif isinstance(stmt, rast.VarStmt):
            if stmt.value:
                self._analyze_expr(stmt.value)
            self.current_locals[stmt.name] = stmt.type
        elif isinstance(stmt, rast.ExprStmt):
            self._analyze_expr(stmt.expr)
        elif isinstance(stmt, rast.AssignStmt):
            self._analyze_expr(stmt.value)
        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value:
                self._analyze_expr(stmt.value)
        elif isinstance(stmt, rast.IfStmt):
            self._analyze_expr(stmt.cond)
            self._analyze_block(stmt.then_block)
            if stmt.else_block:
                self._analyze_block(stmt.else_block)
        elif isinstance(stmt, rast.WhileStmt):
            self._analyze_expr(stmt.cond)
            self._analyze_block(stmt.body)
        elif isinstance(stmt, rast.ForStmt):
            self._analyze_expr(stmt.iter)
            self.current_locals[stmt.var] = None  # Type inferred
            self._analyze_block(stmt.body)

    def _analyze_expr(self, expr: rast.Expr):
        """Analyze an expression, recording await points."""
        if isinstance(expr, rast.Await):
            # Found an await point!
            # All currently defined locals are live across this await
            live_vars = set(self.current_locals.keys())
            ap = AwaitPoint(
                index=self.await_index,
                expr=expr,
                live_vars=live_vars,
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
                self._analyze_expr(f.value)
        elif isinstance(expr, rast.ArrayLit):
            for elem in expr.elements:
                self._analyze_expr(elem)
        # Literals and identifiers don't need analysis


def analyze_async_function(fn_def: rast.FnDef) -> AsyncFnAnalysis:
    """Convenience function to analyze an async function."""
    analyzer = AsyncAnalyzer()
    return analyzer.analyze(fn_def)


# ============================================================================
# State Machine Generator
# ============================================================================

@dataclass
class AsyncStateMachine:
    """Generated state machine for an async function."""
    # Original function definition
    original_fn: rast.FnDef
    # Generated Future struct definition
    future_struct: rast.StructDef
    # Constructor function (returns Future struct)
    constructor_fn: rast.FnDef
    # Poll function (advances state machine)
    poll_fn: rast.FnDef
    # Number of states (await points + 1 for initial + 1 for completed)
    num_states: int


class AsyncStateMachineGenerator:
    """
    Generates state machine code for an async function.

    Transformation:
        async fn foo(x: i32) -> i32
            let a = await bar(x)
            a + 1

    Becomes:
        struct FooFuture { state: i32, x: i32, a: i32 }

        fn foo(x: i32) -> FooFuture
            FooFuture { state: 0, x: x, a: 0 }

        fn foo_poll(self: *FooFuture) -> i32
            # State 0: Initial state, call bar(x)
            # State 1: After await, compute a + 1
            # State 2: Completed
            ...
    """

    def __init__(self, analysis: AsyncFnAnalysis):
        self.analysis = analysis
        self.fn_def = analysis.fn_def
        self.dummy_span = rast.Span(0, 0, 0, 0)

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
            num_states=len(self.analysis.await_points) + 2  # initial + N awaits + completed
        )

    def _make_named_type(self, name: str) -> rast.NamedType:
        """Create a NamedType AST node."""
        return rast.NamedType(span=self.dummy_span, name=name)

    def _make_ptr_type(self, inner: rast.Type) -> rast.PtrType:
        """Create a PtrType AST node."""
        return rast.PtrType(span=self.dummy_span, inner=inner, mutable=True)

    def _generate_future_struct(self) -> rast.StructDef:
        """Generate the Future struct definition.

        Fields:
        - state: i32 (current state index)
        - <params>: original function parameters
        - <cross_await_locals>: locals that live across await points
        """
        fields = []

        # State field
        fields.append(('state', self._make_named_type('i32')))

        # Parameter fields
        for param in self.fn_def.params:
            fields.append((param.name, param.type))

        # Cross-await locals
        for var_name in sorted(self.analysis.cross_await_locals):
            # Skip if it's a parameter (already added)
            param_names = {p.name for p in self.fn_def.params}
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
        """Generate constructor function that returns the Future struct.

        fn foo(x: i32) -> FooFuture
            FooFuture { state: 0, x: x, ... }
        """
        future_name = f"{self.fn_def.name}_Future"

        # Build struct literal fields as (name, value) tuples
        struct_fields = []

        # state = 0
        struct_fields.append(('state', rast.IntLit(span=self.dummy_span, value=0)))

        # Copy parameters
        for param in self.fn_def.params:
            struct_fields.append((param.name, rast.Ident(span=self.dummy_span, name=param.name)))

        # Initialize cross-await locals with default values
        param_names = {p.name for p in self.fn_def.params}
        for var_name in sorted(self.analysis.cross_await_locals):
            if var_name not in param_names:
                var_type = self.analysis.all_locals.get(var_name)
                if var_type:
                    # Default initialize based on type
                    default_val = self._default_value_for_type(var_type)
                    struct_fields.append((var_name, default_val))

        struct_lit = rast.StructLit(
            span=self.dummy_span,
            name=future_name,
            fields=struct_fields
        )

        # Function body returns the struct literal
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
            is_async=False  # Constructor is not async
        )

    def _default_value_for_type(self, ty: rast.Type) -> rast.Expr:
        """Generate a default value for a type."""
        if isinstance(ty, rast.NamedType):
            if ty.name in ('i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64'):
                return rast.IntLit(span=self.dummy_span, value=0)
            elif ty.name == 'bool':
                return rast.BoolLit(span=self.dummy_span, value=False)
            elif ty.name in ('f32', 'f64'):
                return rast.FloatLit(span=self.dummy_span, value=0.0)
        elif isinstance(ty, rast.PtrType):
            # Null pointer: 0 as *T
            return rast.Cast(
                span=self.dummy_span,
                expr=rast.IntLit(span=self.dummy_span, value=0),
                target=ty
            )
        # Fallback: 0
        return rast.IntLit(span=self.dummy_span, value=0)

    def _generate_poll_fn(self) -> rast.FnDef:
        """Generate poll function that advances the state machine.

        fn foo_poll(self: *FooFuture) -> i32
            match self.state
                0 => ...
                1 => ...
                _ => unreachable

        Note: For MVP, we generate synchronous execution.
        Full state machine would poll inner futures and return Pending.
        """
        future_name = f"{self.fn_def.name}_Future"
        poll_fn_name = f"{self.fn_def.name}_poll"

        # self parameter
        self_param = rast.Param(
            span=self.dummy_span,
            name='self',
            type=self._make_ptr_type(self._make_named_type(future_name))
        )

        # Return type is the original async function's return type
        ret_type = self.fn_def.ret_type or self._make_named_type('i32')

        # For MVP: Just execute the body synchronously
        # Transform the body to access locals through self.field
        transformed_body = self._transform_body_for_poll()

        return rast.FnDef(
            span=self.dummy_span,
            name=poll_fn_name,
            params=[self_param],
            ret_type=ret_type,
            body=transformed_body,
            is_async=False
        )

    def _transform_body_for_poll(self) -> rast.Block:
        """Transform the async function body for the poll function.

        For MVP: Execute synchronously, replacing:
        - local variable access with self.field
        - await expr with the inner expression

        Full implementation would generate state machine with switch.
        """
        # For MVP, we just return the transformed body that runs synchronously
        # Variables that cross await points are stored in self
        transformer = BodyTransformer(self.analysis, self.fn_def)
        return transformer.transform(self.fn_def.body)


class BodyTransformer:
    """Transforms async function body for poll execution."""

    def __init__(self, analysis: AsyncFnAnalysis, fn_def: rast.FnDef):
        self.analysis = analysis
        self.fn_def = fn_def
        self.dummy_span = rast.Span(0, 0, 0, 0)
        self.cross_await_vars = analysis.cross_await_locals
        self.param_names = {p.name for p in fn_def.params}

    def transform(self, block: rast.Block) -> rast.Block:
        """Transform a block."""
        new_stmts = [self._transform_stmt(s) for s in block.stmts]
        new_expr = self._transform_expr(block.expr) if block.expr else None
        return rast.Block(span=block.span, stmts=new_stmts, expr=new_expr)

    def _transform_stmt(self, stmt: rast.Stmt) -> rast.Stmt:
        """Transform a statement."""
        if isinstance(stmt, rast.LetStmt):
            new_value = self._transform_expr(stmt.value) if stmt.value else None
            # If this variable crosses await points, it becomes self.field
            if stmt.name in self.cross_await_vars:
                # Convert to assignment: self.name = value
                if new_value:
                    return rast.AssignStmt(
                        span=stmt.span,
                        target=rast.Field(
                            span=stmt.span,
                            expr=rast.UnaryOp(
                                span=stmt.span,
                                op='*',
                                operand=rast.Ident(span=stmt.span, name='self')
                            ),
                            field=stmt.name
                        ),
                        value=new_value
                    )
            return rast.LetStmt(
                span=stmt.span,
                name=stmt.name,
                type=stmt.type,
                value=new_value
            )
        elif isinstance(stmt, rast.VarStmt):
            new_value = self._transform_expr(stmt.value) if stmt.value else None
            if stmt.name in self.cross_await_vars:
                if new_value:
                    return rast.AssignStmt(
                        span=stmt.span,
                        target=rast.Field(
                            span=stmt.span,
                            expr=rast.UnaryOp(
                                span=stmt.span,
                                op='*',
                                operand=rast.Ident(span=stmt.span, name='self')
                            ),
                            field=stmt.name
                        ),
                        value=new_value
                    )
            return rast.VarStmt(
                span=stmt.span,
                name=stmt.name,
                type=stmt.type,
                value=new_value
            )
        elif isinstance(stmt, rast.ExprStmt):
            return rast.ExprStmt(
                span=stmt.span,
                expr=self._transform_expr(stmt.expr)
            )
        elif isinstance(stmt, rast.AssignStmt):
            new_target = self._transform_expr(stmt.target)
            new_value = self._transform_expr(stmt.value)
            return rast.AssignStmt(span=stmt.span, target=new_target, value=new_value)
        elif isinstance(stmt, rast.ReturnStmt):
            new_value = self._transform_expr(stmt.value) if stmt.value else None
            return rast.ReturnStmt(span=stmt.span, value=new_value)
        elif isinstance(stmt, rast.IfStmt):
            return rast.IfStmt(
                span=stmt.span,
                cond=self._transform_expr(stmt.cond),
                then_block=self.transform(stmt.then_block),
                else_block=self.transform(stmt.else_block) if stmt.else_block else None
            )
        elif isinstance(stmt, rast.WhileStmt):
            return rast.WhileStmt(
                span=stmt.span,
                cond=self._transform_expr(stmt.cond),
                body=self.transform(stmt.body)
            )
        elif isinstance(stmt, rast.BreakStmt):
            return stmt
        elif isinstance(stmt, rast.ContinueStmt):
            return stmt
        else:
            return stmt

    def _transform_expr(self, expr: rast.Expr) -> rast.Expr:
        """Transform an expression."""
        if expr is None:
            return None

        if isinstance(expr, rast.Await):
            # MVP: await just evaluates the inner expression
            return self._transform_expr(expr.expr)

        elif isinstance(expr, rast.Ident):
            # If this is a cross-await variable, access through self
            if expr.name in self.cross_await_vars:
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
            new_func = self._transform_expr(expr.func) if not isinstance(expr.func, rast.Ident) else expr.func
            return rast.Call(span=expr.span, func=new_func, args=new_args)

        elif isinstance(expr, rast.If):
            return rast.If(
                span=expr.span,
                cond=self._transform_expr(expr.cond),
                then_block=self.transform(expr.then_block),
                else_block=self.transform(expr.else_block) if expr.else_block else None
            )

        elif isinstance(expr, rast.Block):
            return self.transform(expr)

        elif isinstance(expr, rast.Cast):
            return rast.Cast(
                span=expr.span,
                expr=self._transform_expr(expr.expr),
                target=expr.target
            )

        elif isinstance(expr, rast.Field):
            return rast.Field(
                span=expr.span,
                expr=self._transform_expr(expr.expr),
                field=expr.field
            )

        elif isinstance(expr, rast.Index):
            return rast.Index(
                span=expr.span,
                expr=self._transform_expr(expr.expr),
                index=self._transform_expr(expr.index)
            )

        # Literals don't need transformation
        return expr


def generate_state_machine(fn_def: rast.FnDef) -> AsyncStateMachine:
    """Generate a state machine for an async function."""
    analysis = analyze_async_function(fn_def)
    generator = AsyncStateMachineGenerator(analysis)
    return generator.generate()


# ============================================================================
# Tests
# ============================================================================

def _test_basic_analysis():
    """Test basic async function analysis."""
    from parser import parse

    code = """
async fn fetch(x: i32) -> i32
    let a: i32 = await get_value(x)
    let b: i32 = await get_other(a)
    a + b
"""
    module = parse(code)
    fn = module.items[0]

    analysis = analyze_async_function(fn)

    assert len(analysis.await_points) == 2
    assert 'x' in analysis.await_points[0].live_vars
    assert 'x' in analysis.await_points[1].live_vars
    assert 'a' in analysis.await_points[1].live_vars
    print("✓ Basic analysis test passed")


def _test_no_await():
    """Test async function with no await points."""
    from parser import parse

    code = """
async fn simple() -> i32
    42
"""
    module = parse(code)
    fn = module.items[0]

    analysis = analyze_async_function(fn)

    assert len(analysis.await_points) == 0
    print("✓ No await test passed")


def _test_state_machine_generation():
    """Test state machine generation."""
    from parser import parse

    code = """
async fn fetch(x: i32) -> i32
    let a: i32 = await get_value(x)
    a + 1
"""
    module = parse(code)
    fn = module.items[0]

    sm = generate_state_machine(fn)

    assert sm.future_struct.name == "fetch_Future"
    assert len(sm.future_struct.fields) >= 2  # state + x + a
    assert sm.constructor_fn.name == "fetch"
    assert sm.poll_fn.name == "fetch_poll"
    print("✓ State machine generation test passed")


if __name__ == '__main__':
    _test_basic_analysis()
    _test_no_await()
    _test_state_machine_generation()
    print("All tests passed!")
