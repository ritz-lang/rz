"""
True Async Function Transformation for ritz0 (v2)

An async fn becomes three items:

    struct fetch_Future             # __state, __result (the fn's declared
        __state: i32                # type; none for a unit fn), the params,
        __result: i32               # every local, and each awaited future /
        ...                         # await result
    fn fetch(x: i32) -> fetch_Future             # the future in state 0
    fn fetch_poll(self: *fetch_Future) -> bool   # true once Ready

A poll answers `bool` (LARB R78, AGAST #3728): false while Pending, true once
the body has finished, having stored its value in `__result`.  `await` polls
until true, then reads the field, so any result type comes back whole.

With no await the poll runs the body once: Ready at once.  With one, the body
is lowered to a control-flow graph of states (AGAST #3727), and the poll is a
dispatch loop over them:

    async fn sum_to(n: i32) -> i32
        var s: i32 = 0
        var i: i32 = 0
        while i < n
            s += await dbl(i)
            i += 1
        s

    fn sum_to_poll(self: *sum_to_Future) -> bool
        while true
            if (*self).__state == 0           # entry
                (*self).s = 0
                (*self).i = 0
                (*self).__state = 1
                continue
            if (*self).__state == 1           # loop head
                if (*self).i < (*self).n  { state = 2 } else { state = 4 }
                continue
            if (*self).__state == 2           # build the awaited future
                (*self).__future_0 = dbl((*self).i)
                (*self).__state = 3
                continue
            if (*self).__state == 3           # resume point: poll it
                if !dbl_poll(@(*self).__future_0)
                    return false              # Pending: resume here next poll
                (*self).s = (*self).s + (*self).__future_0.__result
                (*self).i = (*self).i + 1
                (*self).__state = 1
                continue
            if (*self).__state == 4
                (*self).__result = (*self).s  # Ready
                return true
        false

How a poll answers (Pending / Ready) is PollAbi's alone.
"""

import copy
from dataclasses import dataclass, field, fields
from typing import List, Dict, Set, Optional, Tuple
import ritz_ast as rast


@dataclass
class AwaitPoint:
    """Represents a single await expression in an async function."""
    index: int                    # 0-based index of this await
    expr: rast.Await             # The await expression
    span: Optional[rast.Span] = None


@dataclass
class AsyncFnAnalysis:
    """Analysis results for an async function."""
    fn_def: rast.FnDef
    await_points: List[AwaitPoint]
    all_locals: Dict[str, rast.Type]  # name -> type for all locals
    cross_await_locals: Set[str]      # locals that live across await points


class UntypedAsyncLocal(Exception):
    """An untyped local in an async fn whose type the transform cannot infer
    (AGAST #3762).  Every local of an async fn that awaits lives in its future
    struct, which needs the local's type before emission works it out; the
    emitter reports this located, as an EmitError."""

    def __init__(self, fn_name: str, local: str, span: Optional[rast.Span]):
        self.span = span
        super().__init__(
            f"cannot infer the type of `{local}`, which `{fn_name}`'s future holds "
            f"across an `await`: give `{local}` a type (`let {local}: T = ...`)")


# Operators whose value is a bool, whatever their operands.
_BOOL_BINOPS = frozenset(('==', '!=', '<', '<=', '>', '>=', '&&', '||', 'and', 'or'))
_BOOL_UNOPS = frozenset(('!', 'not'))
_INT_ARITH_OPS = frozenset(('+', '-', '*', '/', '%', '&', '|', '^', '<<', '>>'))


def _untyped_int_literal(expr: rast.Expr) -> bool:
    """`5` or `-5`: a literal that takes the other operand's type (LARB R21)."""
    if isinstance(expr, rast.UnaryOp) and expr.op == '-':
        expr = expr.operand
    return isinstance(expr, rast.IntLit)


class AsyncAnalyzer:
    """Analyzes an async function to find await points."""

    def __init__(self, fn_sigs: Optional[Dict[str, rast.FnDef]] = None):
        self.await_points: List[AwaitPoint] = []
        self.current_locals: Dict[str, rast.Type] = {}
        self.await_index = 0
        # Declared fns by name, for an untyped `let y = f(x)` (AGAST #3762).
        self.fn_sigs: Dict[str, rast.FnDef] = fn_sigs or {}

    def _infer_type(self, expr: rast.Expr) -> Optional[rast.Type]:
        """The type of an untyped local's value, or None when it takes more
        than the async fn's own signature, its locals and declared fns' return
        types to tell (AGAST #3762).  Mirrors the emitter's inference for an
        untyped `let` (`_infer_ritz_type`) on the forms it covers."""
        span = getattr(expr, 'span', None)
        if isinstance(expr, rast.IntLit):
            return rast.NamedType(span, 'i64')
        if isinstance(expr, rast.BoolLit):
            return rast.NamedType(span, 'bool')
        if isinstance(expr, rast.FloatLit):
            return rast.NamedType(span, 'f64')
        if isinstance(expr, rast.CharLit):
            return rast.NamedType(span, 'u8')
        if isinstance(expr, rast.Ident):
            return self.current_locals.get(expr.name)
        if isinstance(expr, rast.Await):
            # An async fn's declared result (AGAST #1318, LARB R78); a
            # hand-written poll source's i32.
            inner = expr.expr
            while isinstance(inner, rast.Grouped):
                inner = inner.expr
            if isinstance(inner, rast.Call) and isinstance(inner.func, rast.Ident):
                fn = self.fn_sigs.get(inner.func.name)
                if fn is not None and fn.is_async:
                    return fn.ret_type
            return rast.NamedType(span, 'i32')
        if isinstance(expr, rast.Cast):
            return expr.target
        if isinstance(expr, rast.BinOp):
            if expr.op in _BOOL_BINOPS:
                return rast.NamedType(span, 'bool')
            if expr.op not in _INT_ARITH_OPS:
                return None
            if (expr.op not in ('<<', '>>') and _untyped_int_literal(expr.left)
                    and not _untyped_int_literal(expr.right)):
                return self._infer_type(expr.right)
            return self._infer_type(expr.left)
        if isinstance(expr, rast.UnaryOp):
            if expr.op in _BOOL_UNOPS:
                return rast.NamedType(span, 'bool')
            if expr.op in ('-', '~'):
                return self._infer_type(expr.operand)
            return None
        if isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident) and not expr.type_args:
            fn = self.fn_sigs.get(expr.func.name)
            if fn is None or fn.type_params or expr.func.name in self.current_locals:
                return None
            if fn.is_async:
                # A bare call is the fn's future (AGAST #1395).
                return rast.NamedType(span, f"{fn.name}_Future")
            return fn.ret_type
        return None

    def analyze(self, fn_def: rast.FnDef) -> AsyncFnAnalysis:
        """Analyze an async function."""
        if not fn_def.is_async:
            raise ValueError(f"Function {fn_def.name} is not async")

        self.await_points = []
        self.current_locals = {}
        self.await_index = 0
        self.untyped: List[Tuple[str, Optional[rast.Span]]] = []

        # Add parameters as locals
        for param in fn_def.params:
            self.current_locals[param.name] = param.type

        # Walk the function body
        if fn_def.body:
            self._analyze_block(fn_def.body)

        # With an await, every local is a field of the future, which needs its
        # type (AGAST #3762).  Without one there is no future state to hold.
        if self.await_points and self.untyped:
            name, span = self.untyped[0]
            raise UntypedAsyncLocal(fn_def.name, name, span)

        # With an await, every local lives in the future: a state ends at
        # each await, and a loop or branch may reach any local from another.
        cross_await = set(self.current_locals) if self.await_points else set()

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
        if isinstance(stmt, (rast.LetStmt, rast.VarStmt)):
            # An untyped binding takes its value's type: an await's is the
            # awaited fn's result (AGAST #1318, R78), anything else's is
            # inferred (#3762).
            # Left as None, the local got no field in the future struct while
            # the constructor still set it.  Inferred before the value is
            # walked, so an await in it is not yet a local.
            local_type = stmt.type
            if local_type is None and stmt.value is not None:
                local_type = self._infer_type(stmt.value)
            if local_type is None:
                self.untyped.append((stmt.name, stmt.span))
            if stmt.value:
                self._analyze_expr(stmt.value)
            self.current_locals[stmt.name] = local_type
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
        elif isinstance(stmt, rast.DeferStmt):
            self._analyze_block(stmt.body)
        elif isinstance(stmt, rast.ForStmt):
            self._analyze_expr(stmt.iter)
            self._analyze_block(stmt.body)
        elif isinstance(stmt, rast.UnsafeBlock):
            self._analyze_block(stmt.body)
        elif isinstance(stmt, rast.AssertStmt):
            self._analyze_expr(stmt.condition)

    def _analyze_expr(self, expr: rast.Expr):
        """Analyze an expression, recording await points."""
        if isinstance(expr, rast.Await):
            # An await nested in the awaited expression runs first.
            self._analyze_expr(expr.expr)
            self.await_points.append(AwaitPoint(index=self.await_index, expr=expr,
                                                span=getattr(expr, 'span', None)))
            self.await_index += 1

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
            self._analyze_expr(expr.expr)
            for arm in expr.arms:
                if arm.guard:
                    self._analyze_expr(arm.guard)
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


class AsyncLoweringError(Exception):
    """An async fn body the state machine can't lower (AGAST #3727): an await
    in a place it has no resume point for yet (#4013).  Located; the emitter
    reports it as an EmitError."""

    def __init__(self, message: str, span: Optional[rast.Span]):
        self.span = span
        super().__init__(message)


def _unplaced(what: str, span: Optional[rast.Span]) -> AsyncLoweringError:
    return AsyncLoweringError(
        f"`await` inside {what} in an async fn is not supported yet (AGAST #4013)", span)


class PollAbi:
    """How a poll fn answers: Pending, or Ready with its result stored.

    LARB R78 (AGAST #3728): every poll returns `bool`, true once the body has
    finished, having written the result into the future's `__result` field,
    of the fn's declared type (a unit fn's future has none).  `await` polls
    until true, then reads the field.  The old i32 answer, -1 for Pending,
    narrowed an i64 / pointer / struct result and could not tell a genuine -1
    from Pending.  The state machine asks only this class."""

    RET_TYPE = 'bool'
    RESULT = '__result'

    # An awaited expression that is not an async fn's call is a hand-written
    # poll source, evaluated again at each poll: an i32, -1 while Pending.
    EXPR_TYPE = 'i32'

    def __init__(self, span: rast.Span):
        self.span = span

    def _bool(self, value: bool) -> rast.Expr:
        return rast.BoolLit(span=self.span, value=value)

    def not_ready(self, polled: rast.Expr) -> rast.Expr:
        """Whether an inner generated poll's answer, `polled`, is Pending."""
        return rast.UnaryOp(span=self.span, op='!', operand=polled)

    def expr_is_pending(self, answer: rast.Expr) -> rast.Expr:
        """Whether an awaited poll source's i32 `answer` is Pending (-1)."""
        minus_one = rast.BinOp(span=self.span, op='-', left=rast.IntLit(span=self.span, value=0),
                               right=rast.IntLit(span=self.span, value=1))
        return rast.BinOp(span=self.span, op='==', left=answer, right=minus_one)

    def pending(self) -> rast.Stmt:
        """Return Pending from this poll."""
        return rast.ReturnStmt(span=self.span, value=self._bool(False))

    def unreachable(self) -> rast.Expr:
        """The poll's value after its dispatch loop, which never ends."""
        return self._bool(False)

    def result_field(self, future: rast.Expr, span) -> rast.Field:
        """`future.__result`."""
        return rast.Field(span=span, expr=future, field=self.RESULT)

    def _store_then_true(self, result: Optional[rast.Field], value: Optional[rast.Expr],
                         span) -> rast.Block:
        """`{ result = value; return true }`; a unit fn's value only runs."""
        stmts: List[rast.Stmt] = []
        if value is not None:
            if result is not None:
                stmts.append(rast.AssignStmt(span=span, target=result, value=value))
            elif not isinstance(value, (rast.IntLit, rast.BoolLit, rast.Ident, rast.Field)):
                stmts.append(rast.ExprStmt(span=span, expr=value))
        stmts.append(rast.ReturnStmt(span=span, value=rast.BoolLit(span=span, value=True)))
        return rast.Block(span=span, stmts=stmts, expr=None)

    def ready(self, result: Optional[rast.Field], value: Optional[rast.Expr], span) -> rast.Stmt:
        """Return Ready from this poll, `value` stored in `result` (None for a
        unit fn)."""
        block = self._store_then_true(result, value, span)
        if len(block.stmts) == 1:
            return block.stmts[0]
        return rast.ExprStmt(span=span, expr=block)

    def ready_expr(self, result: Optional[rast.Field], value: Optional[rast.Expr], span) -> rast.Expr:
        """`return` as an expression (a match arm's): Ready, as `ready`."""
        return self._store_then_true(result, value, span)


def _child_nodes(node):
    """`node`'s direct children, in field (evaluation) order: expressions,
    statements and blocks, not types or patterns."""
    for f in fields(node):
        val = getattr(node, f.name)
        items = val if isinstance(val, (list, tuple)) else (val,)
        for item in items:
            # A struct literal's field is a (name, value) pair.
            if isinstance(item, tuple):
                item = item[-1]
            if isinstance(item, rast.Node) and not isinstance(item, (rast.Type, rast.Pattern)):
                yield item


def _first_await(node) -> Optional[rast.Await]:
    if isinstance(node, rast.Await):
        return node
    for child in _child_nodes(node):
        found = _first_await(child)
        if found is not None:
            return found
    return None


def _has_await(node) -> bool:
    return _first_await(node) is not None


def _escaping_jump(node) -> Optional[rast.Node]:
    """A `break` / `continue` in `node` that leaves it for an enclosing loop."""
    if isinstance(node, (rast.BreakStmt, rast.ContinueStmt, rast.BreakExpr, rast.ContinueExpr)):
        return node
    if isinstance(node, (rast.WhileStmt, rast.ForStmt)):
        return None  # its own jumps are its own
    for child in _child_nodes(node):
        found = _escaping_jump(child)
        if found is not None:
            return found
    return None


_INT_NAMES = frozenset(('i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64', 'isize', 'usize'))


def _zero_of(ty: Optional[rast.Type], span) -> Optional[rast.Expr]:
    """A scalar type's zero: 0, false or a null pointer; None for any other."""
    if isinstance(ty, rast.PtrType):
        return rast.NullLit(span=span)
    if isinstance(ty, rast.NamedType) and ty.name in _INT_NAMES:
        return rast.IntLit(span=span, value=0)
    if isinstance(ty, rast.NamedType) and ty.name == 'bool':
        return rast.BoolLit(span=span, value=False)
    return None


def _pattern_names(pat) -> Set[str]:
    """The names a match pattern binds."""
    if isinstance(pat, rast.IdentPattern):
        return {pat.name}
    names: Set[str] = set()
    if isinstance(pat, rast.VariantPattern):
        for sub in pat.fields:
            names |= _pattern_names(sub)
    elif isinstance(pat, rast.StructPattern):
        for _, sub in pat.fields:
            names |= _pattern_names(sub)
    return names


class SimpleBodyTransformer:
    """Rewrites async fn code to run inside its poll fn.

    A name that lives in the future struct (a param; with an await, every
    local) reads and writes `(*self).name`, wherever it appears: a `while`
    condition, an assignment's target, a match arm (AGAST #3727: only
    let/var/return/expression statements were rewritten, so `while i < n` with
    a param `n` was "Unknown identifier: n").  A let of such a local is an
    assignment to its field.  An await already driven by a state reads its
    stored result, and a `return` is the poll's Ready.
    """

    def __init__(self, fields: Set[str], local_fields: Set[str], abi: PollAbi, unit: bool,
                 await_results: Optional[Dict[int, str]] = None):
        self.fields = set(fields)
        self.local_fields = local_fields
        self.abi = abi
        self.unit = unit
        self.await_results = await_results if await_results is not None else {}

    def self_field(self, name: str, span) -> rast.Field:
        """(*self).name"""
        return rast.Field(
            span=span,
            expr=rast.UnaryOp(span=span, op='*', operand=rast.Ident(span=span, name='self')),
            field=name
        )

    def _shadowed(self, names: Set[str], node):
        """`node` rewritten with `names` (a pattern's or a `for`'s own) left alone."""
        hidden = names & self.fields
        self.fields -= hidden
        try:
            return self._rewrite_fields(node)
        finally:
            self.fields |= hidden

    def rewrite(self, node):
        if isinstance(node, list):
            out = [self.rewrite(n) for n in node]
            return [n for n in out if n is not None]
        if isinstance(node, tuple):
            return tuple(self.rewrite(n) for n in node)
        if not isinstance(node, rast.Node) or isinstance(node, (rast.Type, rast.Pattern)):
            return node

        if isinstance(node, rast.Ident):
            if node.name in self.fields:
                return self.self_field(node.name, node.span)
            return node
        if isinstance(node, rast.Await):
            # A state drove it: its result is stored.
            if id(node) in self.await_results:
                return self.self_field(self.await_results[id(node)], node.span)
            return self.rewrite(node.expr)
        if isinstance(node, (rast.LetStmt, rast.VarStmt)) and node.name in self.local_fields:
            # The local lives in the future struct.  One with no value is
            # zeroed if a scalar, as it always was (ritz1 alike); an array or
            # struct (`var buf: [32]u8`) is only its field.
            if node.value is None:
                value = _zero_of(node.type, node.span)
                if value is None:
                    return None
            else:
                value = self.rewrite(node.value)
            return rast.AssignStmt(span=node.span, target=self.self_field(node.name, node.span), value=value)
        if isinstance(node, rast.ReturnStmt):
            return self.ready(self.rewrite(node.value) if node.value else None, node.span)
        if isinstance(node, rast.ReturnExpr):
            value = self.rewrite(node.value) if node.value else None
            return self.abi.ready_expr(self.result(node.span), value, node.span)
        if isinstance(node, rast.MatchArm):
            return self._shadowed(_pattern_names(node.pattern), node)
        if isinstance(node, rast.ForStmt):
            new = copy.copy(node)
            new.iter = self.rewrite(node.iter)
            new.body = self._shadowed({node.var}, node.body)
            return new
        return self._rewrite_fields(node)

    def _rewrite_fields(self, node):
        new = copy.copy(node)
        for f in fields(node):
            val = getattr(node, f.name)
            if isinstance(val, list) and val and isinstance(val[0], tuple):
                # A struct literal's (name, value) pairs.
                setattr(new, f.name, [(k, self.rewrite(v)) for k, v in val])
            else:
                setattr(new, f.name, self.rewrite(val))
        return new

    def result(self, span) -> Optional[rast.Field]:
        """`(*self).__result`, where the poll stores its value; None for a unit fn."""
        if self.unit:
            return None
        return self.abi.result_field(rast.UnaryOp(span=span, op='*', operand=rast.Ident(span=span, name='self')),
                                     span)

    def ready(self, value: Optional[rast.Expr], span) -> rast.Stmt:
        """`return value` from the async fn: Ready, `value` in its result field
        (a unit fn's only runs)."""
        return self.abi.ready(self.result(span), value, span)

    # The names earlier callers used.
    def transform(self, block: rast.Block) -> rast.Block:
        return self.rewrite(block)

    def _transform_expr(self, expr: rast.Expr) -> rast.Expr:
        return self.rewrite(expr)

    def _transform_stmt(self, stmt: rast.Stmt) -> Optional[rast.Stmt]:
        return self.rewrite(stmt)


@dataclass
class _Loop:
    head: int   # the state that tests the condition: `continue` goes here
    exit: int   # the state after the loop: `break` goes here


class _CfgBuilder:
    """Lowers an async fn body that awaits to a control-flow graph of states.

    Each state is a straight run of statements that ends by jumping to
    another state (`(*self).__state = N; continue` in the poll's dispatch
    loop), returning Ready, or returning Pending at a resume point.  An await
    is its own state: it polls the awaited future, kept in the future struct,
    and returns Pending until it is Ready, so the next poll resumes there.
    Everything between awaits runs in the states that reach it, once (AGAST
    #3727: the old lowering ran each await once, in order, and then only the
    body's tail).  Loops and branches are ordinary edges between states, so
    an await in a `while` runs on every pass and only the taken arm's do.

    A statement with no await (and no `break`/`continue` out of a loop that
    has one) is kept whole, rewritten in place: no state is spent on it.
    """

    def __init__(self, gen: 'TrueAsyncGenerator', rewriter: SimpleBodyTransformer):
        self.gen = gen
        self.rw = rewriter
        self.abi = rewriter.abi
        self.span = gen.dummy_span
        self.blocks: List[List[rast.Stmt]] = []
        self.closed: Set[int] = set()
        self.cur: Optional[int] = None
        self.n_awaits = 0
        # Fields the lowering adds: awaited futures and await results.
        self.extra_fields: List[Tuple[str, rast.Type]] = []

    # -- states ------------------------------------------------------------

    def new_block(self) -> int:
        self.blocks.append([])
        return len(self.blocks) - 1

    def _at(self) -> int:
        """The open state, or a fresh (unreachable) one after a jump."""
        if self.cur is None:
            self.cur = self.new_block()
        return self.cur

    def emit(self, stmt: Optional[rast.Stmt]):
        if stmt is not None:
            self.blocks[self._at()].append(stmt)

    def _close(self, *stmts: rast.Stmt):
        b = self._at()
        self.blocks[b].extend(stmts)
        self.closed.add(b)
        self.cur = None

    def _set_state(self, target: int) -> rast.Stmt:
        return rast.AssignStmt(span=self.span, target=self.rw.self_field('__state', self.span),
                               value=rast.IntLit(span=self.span, value=target))

    def goto(self, target: int):
        self._close(self._set_state(target), rast.ContinueStmt(span=self.span))

    def branch(self, cond: rast.Expr, then_b: int, else_b: int):
        jump = rast.If(span=self.span, cond=cond,
                       then_block=rast.Block(span=self.span, stmts=[self._set_state(then_b)], expr=None),
                       else_block=rast.Block(span=self.span, stmts=[self._set_state(else_b)], expr=None))
        self._close(rast.ExprStmt(span=self.span, expr=jump), rast.ContinueStmt(span=self.span))

    def ret(self, value: Optional[rast.Expr], span):
        self._close(self.rw.ready(value, span))

    def _add_field(self, name: str, ty: rast.Type) -> str:
        self.extra_fields.append((name, ty))
        self.rw.fields.add(name)
        return name

    # -- statements --------------------------------------------------------

    def lower_body(self, body: rast.Block):
        self.cur = self.new_block()  # state 0
        self.lower_stmts(body.stmts, None)
        if body.expr is not None:
            self.lower_value(body.expr, ('return',), None)
        if self.cur is not None:
            # Off the end: a unit fn's Ready.
            self.ret(None, self.span)

    def lower_stmts(self, stmts: List[rast.Stmt], loop: Optional[_Loop]):
        for stmt in stmts:
            self.lower_stmt(stmt, loop)

    def _needs_lowering(self, node, loop: Optional[_Loop]) -> bool:
        return _has_await(node) or (loop is not None and _escaping_jump(node) is not None)

    def lower_stmt(self, stmt: rast.Stmt, loop: Optional[_Loop]):
        if isinstance(stmt, rast.DeferStmt):
            # Its block's exit is spread over states: it would run as its
            # state ends, not as the block does.
            raise AsyncLoweringError(
                "`defer` in an async fn that awaits is not supported yet (AGAST #4013)", stmt.span)
        if not self._needs_lowering(stmt, loop):
            self.emit(self.rw.rewrite(stmt))
            if isinstance(stmt, rast.ReturnStmt):
                self.closed.add(self._at())
                self.cur = None
            return

        if isinstance(stmt, (rast.LetStmt, rast.VarStmt)):
            self.lower_value(stmt.value, ('field', stmt.name, stmt.span), loop)
        elif isinstance(stmt, rast.AssignStmt):
            target = self.hoist(stmt.target)
            self.lower_value(stmt.value, ('assign', stmt, target), loop)
        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value is None:
                self.ret(None, stmt.span)
            else:
                self.lower_value(stmt.value, ('return',), loop)
        elif isinstance(stmt, rast.ExprStmt):
            self.lower_value(stmt.expr, None, loop)
        elif isinstance(stmt, rast.WhileStmt):
            self._lower_while(stmt)
        elif isinstance(stmt, rast.BreakStmt):
            self.goto(loop.exit)
        elif isinstance(stmt, rast.ContinueStmt):
            self.goto(loop.head)
        elif isinstance(stmt, rast.UnsafeBlock):
            self.lower_value(stmt.body, None, loop)
        elif isinstance(stmt, rast.ForStmt):
            raise _unplaced("a `for` loop", self._culprit(stmt))
        else:
            raise _unplaced("this statement", self._culprit(stmt))

    def _culprit(self, node) -> Optional[rast.Span]:
        found = _first_await(node) or _escaping_jump(node) or node
        return found.span

    def _lower_while(self, stmt: rast.WhileStmt):
        head = self.new_block()
        self.goto(head)
        self.cur = head
        cond = self.hoist(stmt.cond)  # its awaits re-run on every pass
        body, exit_b = self.new_block(), self.new_block()
        self.branch(cond, body, exit_b)
        self.cur = body
        self.lower_stmts(stmt.body.stmts, _Loop(head, exit_b))
        if stmt.body.expr is not None:
            self.lower_value(stmt.body.expr, None, _Loop(head, exit_b))
        if self.cur is not None:
            self.goto(head)
        self.cur = exit_b

    # -- values ------------------------------------------------------------

    def lower_value(self, expr: rast.Expr, dest, loop: Optional[_Loop]):
        """Evaluate `expr` into `dest`: None (discarded), ('return',),
        ('field', local, span) or ('assign', stmt, target)."""
        while isinstance(expr, rast.Grouped):
            expr = expr.expr
        if not self._needs_lowering(expr, loop):
            self.deliver(self.rw.rewrite(expr), dest)
        elif isinstance(expr, rast.If):
            cond = self.hoist(expr.cond)
            then_b, else_b, join = self.new_block(), self.new_block(), self.new_block()
            self.branch(cond, then_b, else_b)
            self.cur = then_b
            self.lower_value(expr.then_block, dest, loop)
            if self.cur is not None:
                self.goto(join)
            self.cur = else_b
            if expr.else_block is not None:
                self.lower_value(expr.else_block, dest, loop)
            if self.cur is not None:
                self.goto(join)
            self.cur = join
        elif isinstance(expr, rast.Block):
            self.lower_stmts(expr.stmts, loop)
            if expr.expr is not None:
                self.lower_value(expr.expr, dest, loop)
            elif dest == ('return',) and self.cur is not None:
                self.ret(None, expr.span)
        elif isinstance(expr, rast.Await):
            self.lower_await(expr, dest)
        elif not _has_await(expr):
            # Only a jump out of the loop, from somewhere it can't be a state edge.
            raise AsyncLoweringError(
                "`break` / `continue` inside a `match` of an async fn's loop that awaits "
                "is not supported yet (AGAST #4013)", _escaping_jump(expr).span)
        else:
            self.deliver(self.hoist(expr), dest)

    def deliver(self, value: rast.Expr, dest):
        if dest is None:
            # A value nobody reads: keep it only for its effects.
            if not isinstance(value, (rast.IntLit, rast.Field, rast.Ident)):
                self.emit(rast.ExprStmt(span=value.span, expr=value))
        elif dest[0] == 'return':
            self.ret(value, value.span)
        elif dest[0] == 'field':
            _, name, span = dest
            self.emit(rast.AssignStmt(span=span, target=self.rw.self_field(name, span), value=value))
        else:
            _, stmt, target = dest
            new = copy.copy(stmt)
            new.target, new.value = target, value
            self.emit(new)

    def hoist(self, expr: rast.Expr) -> rast.Expr:
        """Drive each await in `expr` in its own state, in evaluation order,
        storing its result; then `expr` rewritten to read the results."""
        self._hoist(expr, None)
        return self.rw.rewrite(expr)

    def _hoist(self, node, under: Optional[str]):
        if isinstance(node, rast.Await):
            if under is not None:
                raise _unplaced(under, node.span)
            # An await in the awaited expression runs first.
            tmp = self._add_field(f"__await_result_{self.n_awaits}", self.gen._await_type(node))
            self.lower_await(node, ('field', tmp, node.span))
            self.rw.await_results[id(node)] = tmp
            return
        if isinstance(node, rast.If):
            self._hoist(node.cond, under)
            for arm in (node.then_block, node.else_block):
                if arm is not None:
                    self._hoist(arm, under or "an `if` inside an expression")
            return
        if isinstance(node, rast.Match):
            self._hoist(node.expr, under)
            for arm in node.arms:
                self._hoist(arm, under or "a `match`")
            return
        if isinstance(node, rast.BinOp) and node.op in ('&&', '||', 'and', 'or'):
            self._hoist(node.left, under)
            op = {'and': '&&', 'or': '||'}.get(node.op, node.op)
            self._hoist(node.right, under or f"the right of `{op}`")
            return
        if isinstance(node, rast.Block):
            under = under or "a block inside an expression"
        for child in _child_nodes(node):
            self._hoist(child, under)

    def lower_await(self, aw: rast.Await, dest):
        """`await inner` into `dest`: a resume point.

        An async fn's call builds its future into a field once; the resume
        state polls it until it answers true (LARB R78), so a Pending one is
        polled again on the next poll, not rebuilt, and then reads its
        `__result`.  Any other awaited expression is a hand-written poll
        source, evaluated again at each poll until it is not -1."""
        k = self.n_awaits
        self.n_awaits += 1
        inner = aw.expr
        while isinstance(inner, rast.Grouped):
            inner = inner.expr
        if self.gen._is_async_call(inner):
            fn_name = inner.func.name
            fut = self._add_field(f"__future_{k}", self.gen._make_named_type(f"{fn_name}_Future"))
            args = [self.hoist(a) for a in inner.args]
            # The call keeps its source spans: it is the user's call of `foo`,
            # so a private `foo` of another file is refused here, at `foo`
            # (#3925, LARB R45a).  `foo_poll` is the compiler's own call.
            self.emit(rast.AssignStmt(
                span=self.span, target=self.rw.self_field(fut, self.span),
                value=rast.Call(span=inner.span, func=rast.Ident(span=inner.func.span, name=fn_name), args=args)))
            polled = rast.Call(span=self.span, func=rast.Ident(span=self.span, name=f"{fn_name}_poll"),
                               args=[rast.UnaryOp(span=self.span, op='@',
                                                  operand=self.rw.self_field(fut, self.span))])
            resume = self.new_block()
            self.goto(resume)
            self.cur = resume
            self.emit(rast.ExprStmt(span=self.span, expr=rast.If(
                span=self.span, cond=self.abi.not_ready(polled),
                then_block=rast.Block(span=self.span, stmts=[self.abi.pending()], expr=None), else_block=None)))
            if self.gen._async_ret_type(fn_name) is None:
                # A unit fn's future has no result to deliver.
                if dest is None:
                    return
                if dest == ('return',) and self.rw.unit:
                    self.ret(None, aw.span)
                    return
                raise AsyncLoweringError(f"`await {fn_name}(..)` has no value: `{fn_name}` is a unit async fn",
                                         aw.span)
            self.deliver(self.abi.result_field(self.rw.self_field(fut, self.span), self.span), dest)
            return
        answer = f"__poll_{k}"
        polled = self.hoist(inner)
        resume = self.new_block()
        self.goto(resume)
        self.cur = resume
        self.emit(rast.LetStmt(span=self.span, name=answer,
                               type=self.gen._make_named_type(PollAbi.EXPR_TYPE), value=polled))
        self.emit(rast.ExprStmt(span=self.span, expr=rast.If(
            span=self.span, cond=self.abi.expr_is_pending(rast.Ident(span=self.span, name=answer)),
            then_block=rast.Block(span=self.span, stmts=[self.abi.pending()], expr=None), else_block=None)))
        self.deliver(rast.Ident(span=self.span, name=answer), dest)

    # -- the poll body -----------------------------------------------------

    def dispatch(self) -> rast.Block:
        """`while true` over `if (*self).__state == N` for each state."""
        arms = []
        for i, stmts in enumerate(self.blocks):
            if i not in self.closed:
                stmts = stmts + [self.abi.pending()]  # unreachable: nothing jumps here
            arms.append(rast.ExprStmt(span=self.span, expr=rast.If(
                span=self.span,
                cond=rast.BinOp(span=self.span, op='==', left=self.rw.self_field('__state', self.span),
                                right=rast.IntLit(span=self.span, value=i)),
                then_block=rast.Block(span=self.span, stmts=stmts, expr=None), else_block=None)))
        loop = rast.WhileStmt(span=self.span, cond=rast.BoolLit(span=self.span, value=True),
                              body=rast.Block(span=self.span, stmts=arms, expr=None))
        return rast.Block(span=self.span, stmts=[loop], expr=self.abi.unreachable())


class TrueAsyncGenerator:
    """
    Generates the state machine for an async function: its future struct
    (state, params, locals, inner futures), a constructor that stands for the
    fn, and `NAME_poll`, which runs the body from its current state to the
    next Pending await or to its end (Ready).

    When async_functions is provided, recognizes calls to async functions
    and generates proper foo() + foo_poll() sequences.
    """

    def __init__(self, analysis: AsyncFnAnalysis, async_functions: Optional[Set[str]] = None,
                 fn_sigs: Optional[Dict[str, rast.FnDef]] = None):
        self.analysis = analysis
        # Declared fns by name: an awaited async fn's result type (R78).
        self.fn_sigs: Dict[str, rast.FnDef] = fn_sigs or {}
        self.fn_def = analysis.fn_def
        self.dummy_span = rast.Span(0, 0, 0, 0)
        # Set of known async function names (for await transformation)
        self.async_functions = async_functions or set()
        self.abi = PollAbi(self.dummy_span)

    def generate(self) -> AsyncStateMachine:
        """Generate the complete state machine."""
        param_names = [p.name for p in self.fn_def.params]
        # Locals live in the future only when there is an await to live across.
        local_fields = ({n for n in self.analysis.cross_await_locals if n not in param_names}
                        if self.analysis.await_points else set())
        rewriter = SimpleBodyTransformer(set(param_names) | local_fields, local_fields, self.abi,
                                         unit=self.fn_def.ret_type is None)

        extra: List[Tuple[str, rast.Type]] = []
        if not self.analysis.await_points:
            body = self._straight_body(rewriter)
            num_states = 1
        else:
            cfg = _CfgBuilder(self, rewriter)
            cfg.lower_body(self.fn_def.body)
            body = cfg.dispatch()
            extra = cfg.extra_fields
            num_states = len(cfg.blocks)

        fields_ = [('__state', self._make_named_type('i32'))]
        if self.fn_def.ret_type is not None:
            # Where the poll leaves its value (LARB R78).
            fields_.append((PollAbi.RESULT, self.fn_def.ret_type))
        fields_ += [(p.name, p.type) for p in self.fn_def.params]
        for name in sorted(local_fields):
            ty = self.analysis.all_locals.get(name)
            if ty is not None:
                fields_.append((name, ty))
        fields_ += extra
        future_name = f"{self.fn_def.name}_Future"
        future_struct = rast.StructDef(span=self.dummy_span, name=future_name, fields=fields_)

        return AsyncStateMachine(
            original_fn=self.fn_def,
            future_struct=future_struct,
            constructor_fn=self._generate_constructor(future_name),
            poll_fn=self._generate_poll_fn(future_name, body),
            num_states=num_states
        )

    def _make_named_type(self, name: str) -> rast.NamedType:
        return rast.NamedType(span=self.dummy_span, name=name)

    def _make_ident(self, name: str) -> rast.Ident:
        return rast.Ident(span=self.dummy_span, name=name)

    def _async_ret_type(self, fn_name: str) -> Optional[rast.Type]:
        """An awaited async fn's declared result type; None for a unit fn."""
        fn = self.fn_sigs.get(fn_name)
        if fn is None and fn_name == self.fn_def.name:
            fn = self.fn_def
        return fn.ret_type if fn is not None else None

    def _await_type(self, aw: rast.Await) -> rast.Type:
        """The type of `aw`'s value: an async fn's declared result type (R78);
        a hand-written poll source's i32."""
        inner = aw.expr
        while isinstance(inner, rast.Grouped):
            inner = inner.expr
        if self._is_async_call(inner):
            ty = self._async_ret_type(inner.func.name)
            if ty is None:
                raise AsyncLoweringError(
                    f"`await {inner.func.name}(..)` has no value: `{inner.func.name}` is a unit async fn", aw.span)
            return ty
        return self._make_named_type(PollAbi.EXPR_TYPE)

    def _is_async_call(self, expr: rast.Expr) -> bool:
        """Check if expr is a call to a known async function."""
        if isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident):
            return expr.func.name in self.async_functions
        return False

    def _generate_constructor(self, future_name: str) -> rast.FnDef:
        """The fn itself: its future, in state 0 with its params.  The other
        fields (locals, inner futures) are written before they are read."""
        span = self.dummy_span
        fut = '__fut'

        def fut_field(name):
            return rast.Field(span=span, expr=self._make_ident(fut), field=name)

        stmts: List[rast.Stmt] = [rast.VarStmt(span=span, name=fut, type=self._make_named_type(future_name), value=None)]
        stmts.append(rast.AssignStmt(span=span, target=fut_field('__state'), value=rast.IntLit(span=span, value=0)))
        for param in self.fn_def.params:
            stmts.append(rast.AssignStmt(span=span, target=fut_field(param.name), value=self._make_ident(param.name)))

        # The constructor stands for the async fn itself, so it carries its
        # declaration span: a privacy refusal's note points there (#3925).
        return rast.FnDef(
            span=self.fn_def.span,
            name=self.fn_def.name,
            params=self.fn_def.params,
            ret_type=self._make_named_type(future_name),
            body=rast.Block(span=span, stmts=stmts, expr=self._make_ident(fut)),
            is_async=False
        )

    def _generate_poll_fn(self, future_name: str, body: rast.Block) -> rast.FnDef:
        """`NAME_poll(self: *NAME_Future)`, answering as PollAbi says."""
        self_param = rast.Param(
            span=self.dummy_span,
            name='self',
            type=rast.PtrType(span=self.dummy_span, inner=self._make_named_type(future_name), mutable=True)
        )
        return rast.FnDef(
            span=self.dummy_span,
            name=f"{self.fn_def.name}_poll",
            params=[self_param],
            ret_type=self._make_named_type(PollAbi.RET_TYPE),
            body=body,
            is_async=False
        )

    def _straight_body(self, rewriter: SimpleBodyTransformer) -> rast.Block:
        """A body with no await runs whole on the first poll: Ready at once,
        its tail value stored in `__result` (LARB R78).  A unit fn's tail
        (`pass` parses as one) is a statement, and its poll is true too
        (AGAST #1395: even an empty body)."""
        transformed = rewriter.rewrite(self.fn_def.body)
        tail = transformed.expr
        if tail is not None and not (isinstance(tail, rast.Ident) and tail.name == 'pass'):
            if self.fn_def.ret_type is not None:
                transformed.stmts.append(rast.AssignStmt(span=tail.span, target=rewriter.result(tail.span),
                                                         value=tail))
            else:
                transformed.stmts.append(rast.ExprStmt(span=tail.span, expr=tail))
        transformed.expr = rast.BoolLit(span=self.dummy_span, value=True)
        return transformed


def analyze_async_function(fn_def: rast.FnDef,
                           fn_sigs: Optional[Dict[str, rast.FnDef]] = None) -> AsyncFnAnalysis:
    """Convenience function to analyze an async function."""
    analyzer = AsyncAnalyzer(fn_sigs)
    return analyzer.analyze(fn_def)


def generate_state_machine(fn_def: rast.FnDef, async_functions: Optional[Set[str]] = None,
                           fn_sigs: Optional[Dict[str, rast.FnDef]] = None) -> AsyncStateMachine:
    """Generate a TRUE state machine for an async function.

    Args:
        fn_def: The async function definition to transform
        async_functions: Set of known async function names (for await transformation)
        fn_sigs: Declared fns by name, to type an untyped `let y = f(x)` (AGAST #3762)

    Raises UntypedAsyncLocal for an untyped local it cannot type.
    """
    analysis = analyze_async_function(fn_def, fn_sigs)
    generator = TrueAsyncGenerator(analysis, async_functions, fn_sigs)
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

    sm = generate_state_machine(fn)
    assert sm.num_states == 2  # entry, and the await's resume point
    print("✓ Await test passed")


if __name__ == '__main__':
    _test_basic()
    _test_with_await()
    print("All tests passed!")
