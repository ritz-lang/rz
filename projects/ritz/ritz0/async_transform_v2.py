"""
True Async Function Transformation for ritz0 (v2)

An async fn becomes three items:

    struct fetch$Future             # the header (FUTURE_HEADER: the poll fn
        __poll: fn(*u8) -> bool     # first, then the state, -1 once finished),
        __state: i32                # __result (the fn's declared type; none
        __result: i32               # for a unit fn), the params, every local,
        ...                         # and each awaited future / await result
    fn fetch(x: i32) -> fetch$Future             # the future in state 0
    fn fetch$poll(self: *fetch$Future) -> bool   # true once Ready

(`$` is not an identifier character, so no source can spell these names:
AGAST #3606.  The doc's examples write them as the compiler does.)

A poll answers `bool` (LARB R78, AGAST #3728): false while Pending, true once
the body has finished, having stored its value in `__result`.  `await` polls
until true, then reads the field, so any result type comes back whole.

The header is the same in every future (LARB R79, AGAST #4006), so a
`@&Future` reaches any of them: `future_poll(f)` calls `f.__poll(f)`.  A
finished future's `__state` is -1, and its poll answers true at once, without
running the body again: `await p` of a held future an executor already drove
only reads its result.

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

    fn sum_to$poll(self: *sum_to$Future) -> bool
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
                if !dbl$poll(@(*self).__future_0)
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
from const_eval import fold_literal_i64


# The names of the items an async fn generates.  `$` is not an identifier
# character (lexer.py: DOLLAR_OUTSIDE_ASM), so no Ritz source can spell them:
# they are the compiler's alone and can't clash with a user's `fetch_poll` or
# `fetch_Future` (AGAST #3606).  The spelling lives here and nowhere else.
FUTURE_SUFFIX = '$Future'
POLL_SUFFIX = '$poll'


def future_type_name(fn_name: str) -> str:
    """`async fn fetch`'s generated future type: `fetch$Future`."""
    return fn_name + FUTURE_SUFFIX


def poll_fn_name(fn_name: str) -> str:
    """`async fn fetch`'s generated poll fn: `fetch$poll`."""
    return fn_name + POLL_SUFFIX


def async_fn_of_future_type(name: str) -> Optional[str]:
    """The async fn whose generated future `name` is, or None.

    Only this module's own inferences produce such a name; no source can."""
    if name.endswith(FUTURE_SUFFIX):
        return name[:-len(FUTURE_SUFFIX)]
    return None


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


def _literal_operand(expr: rast.Expr) -> bool:
    """The emitter's `_literal_operand_value`: a literal, or an operator over
    literals that folds (AGAST #4082), so `(0 - 1) ^ w` is w's type."""
    return _untyped_int_literal(expr) or fold_literal_i64(expr) is not None


def poll_source_refusal(called: str, name: str) -> str:
    """The words for `await called(..)` of a sync fn or method `name` that is no
    poll source (AGAST #4558, #4604); ritz1's al_not_source says the same."""
    return (f"`await {called}(..)`: a poll source returns `Option<T>` (`None` while Pending, "
            f"`Some(v)` when Ready); `{name}` does not")


def poll_source_unknown() -> str:
    """The words for awaiting a poll source whose declared type the lowering
    can't find, a fn pointer's call say (AGAST #4604); ritz1's al_source_fn."""
    return ("`await`: the poll source's type is unknown; a poll source is a call of a fn "
            "or method declared to return `Option<T>`")


class DeclSigs(dict):
    """Declared fns by name, as a plain dict, plus what a poll source's type
    takes to read (AGAST #4604): inherent and trait methods by `(type, name)`
    and enums by name, for a monomorphised `Option$T`'s `Some` payload."""

    def __init__(self, fns=None, methods=None, enums=None):
        super().__init__(fns or {})
        self.methods: Dict[Tuple[str, str], rast.FnDef] = methods or {}
        self.enums: Dict[str, rast.EnumDef] = enums or {}

    @classmethod
    def of_module(cls, module: rast.Module) -> 'DeclSigs':
        items = module.items
        return cls({i.name: i for i in items if isinstance(i, rast.FnDef)},
                   {(i.type_name, m.name): m for i in items if isinstance(i, rast.ImplBlock)
                    for m in i.methods},
                   {i.name: i for i in items if isinstance(i, rast.EnumDef)})


def _receiver_type_name(ty: Optional[rast.Type]) -> Optional[str]:
    """The struct a method receiver of type `ty` (`S`, `*S`, `@S`) names."""
    while isinstance(ty, (rast.PtrType, rast.RefType)):
        ty = ty.inner
    if isinstance(ty, rast.NamedType) and not ty.args:
        return ty.name
    return None


def poll_source_fn(inner: rast.Expr, local_types: Dict[str, Optional[rast.Type]],
                   fn_sigs: Dict[str, rast.FnDef]) -> Optional[Tuple[rast.FnDef, str, str]]:
    """The sync fn or method a poll source `inner` calls, with the call as an
    `await` names it (`src`, `s.poll`) and the callee's own name; None when no
    declaration says (a fn pointer's call, a receiver of untold type)."""
    if isinstance(inner, rast.Call) and isinstance(inner.func, rast.Ident):
        name = inner.func.name
        fn = fn_sigs.get(name)
        if name in local_types or fn is None or fn.type_params or inner.type_args:
            return None
        return fn, name, name
    if isinstance(inner, rast.MethodCall):
        recv = _ungroup(inner.expr)
        if not isinstance(recv, rast.Ident):
            return None
        owner = _receiver_type_name(local_types.get(recv.name))
        methods = getattr(fn_sigs, 'methods', {})
        fn = methods.get((owner, inner.method)) if owner is not None else None
        if fn is None or fn.type_params:
            return None
        return fn, f"{recv.name}.{inner.method}", inner.method
    return None


def poll_source_type(inner: rast.Expr, local_types: Dict[str, Optional[rast.Type]],
                     fn_sigs: Dict[str, rast.FnDef]) -> Optional[Tuple[rast.Type, rast.Type]]:
    """A poll source's `(Option<T>, T)`, from its callee's declared return
    type (AGAST #4604); None when it has none or it is no `Option`."""
    found = poll_source_fn(inner, local_types, fn_sigs)
    if found is None:
        return None
    ret = found[0].ret_type
    value = PollAbi.source_value_type(ret, getattr(fn_sigs, 'enums', {}))
    return (ret, value) if value is not None else None


def check_poll_source(inner: rast.Expr, local_types: Dict[str, Optional[rast.Type]],
                      fn_sigs: Dict[str, rast.FnDef], span) -> Tuple[rast.Type, rast.Type]:
    """A poll source's `(Option<T>, T)`, or refused at the await `span`: its
    callee isn't declared here, or doesn't return an `Option` (#4558, #4604)."""
    found = poll_source_fn(inner, local_types, fn_sigs)
    if found is None:
        raise AsyncLoweringError(poll_source_unknown(), span)
    typed = poll_source_type(inner, local_types, fn_sigs)
    if typed is None:
        raise AsyncLoweringError(poll_source_refusal(found[1], found[2]), span)
    return typed


def poll_source_outside_async() -> str:
    """The words for awaiting a poll source outside an async fn (AGAST #4558)."""
    return ("`await` of a poll source outside an async fn: a poll source can only be awaited "
            "in an async fn, which can suspend while it is Pending")


def held_future_fn(expr: rast.Expr, local_types: Dict[str, Optional[rast.Type]],
                   fn_sigs: Dict[str, rast.FnDef]) -> Optional[rast.FnDef]:
    """The async fn whose future the local `expr` holds (`var p = f(args)`,
    LARB R79), or None."""
    if not isinstance(expr, rast.Ident):
        return None
    ty = local_types.get(expr.name)
    if not isinstance(ty, rast.NamedType) or ty.args:
        return None
    fn_name = async_fn_of_future_type(ty.name)
    if fn_name is None:
        return None
    fn = fn_sigs.get(fn_name)
    return fn if fn is not None and fn.is_async else None


class AsyncAnalyzer:
    """Analyzes an async function to find await points."""

    def __init__(self, fn_sigs: Optional[Dict[str, rast.FnDef]] = None,
                 async_functions: Optional[Set[str]] = None):
        self.await_points: List[AwaitPoint] = []
        self.current_locals: Dict[str, rast.Type] = {}
        self.await_index = 0
        # Declared fns by name, for an untyped `let y = f(x)` (AGAST #3762).
        self.fn_sigs: Dict[str, rast.FnDef] = fn_sigs if fn_sigs is not None else {}
        # The async fns an `await f(..)` polls as futures, as the generator
        # tells them (its _is_async_call); any other call is a poll source.
        self.async_functions: Set[str] = (async_functions if async_functions is not None else
                                          {n for n, f in self.fn_sigs.items() if f.is_async})

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
            # hand-written poll source's T, from its `-> Option<T>` (#4604).
            inner = expr.expr
            while isinstance(inner, rast.Grouped):
                inner = inner.expr
            if isinstance(inner, rast.Call) and isinstance(inner.func, rast.Ident):
                fn = self.fn_sigs.get(inner.func.name)
                if fn is not None and fn.is_async:
                    return fn.ret_type
            held = held_future_fn(inner, self.current_locals, self.fn_sigs)
            if held is not None:
                return held.ret_type
            typed = poll_source_type(inner, self.current_locals, self.fn_sigs)
            return typed[1] if typed is not None else None
        if isinstance(expr, rast.Cast):
            return expr.target
        if isinstance(expr, rast.BinOp):
            if expr.op in _BOOL_BINOPS:
                return rast.NamedType(span, 'bool')
            if expr.op not in _INT_ARITH_OPS:
                return None
            # An all-literal operand (`0 - 1`) is one literal too (#4082).
            if (expr.op not in ('<<', '>>') and _literal_operand(expr.left)
                    and not _literal_operand(expr.right)):
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
                return rast.NamedType(span, future_type_name(fn.name))
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

        # A local in a re-entered block that dies before it crosses a state
        # boundary stays a poll local: the emitter's own block-end drop then
        # frees it once per run (AGAST #4527).
        poll_locals = self._poll_locals(fn_def.body) if self.await_points else set()
        if self.await_points:
            for name, span in self.untyped:
                if name not in poll_locals:
                    raise UntypedAsyncLocal(fn_def.name, name, span)

        # Otherwise a local lives in the future: a state ends at each await,
        # and a loop or branch may reach any local from another.
        cross_await = (set(self.current_locals) - poll_locals
                       if self.await_points else set())

        return AsyncFnAnalysis(
            fn_def=fn_def,
            await_points=self.await_points,
            all_locals=dict(self.current_locals),
            cross_await_locals=cross_await
        )

    def _poll_locals(self, body: rast.Block) -> Set[str]:
        """The locals that may stay locals of the poll rather than fields of
        the future (AGAST #4527).

        A local declared in a block the machine re-enters (a loop body, or a
        `defer` body, which runs at every exit edge) becomes one field, so
        each run overwrites the last value and nothing drops it.  One that
        is dead before any state boundary in the same activation crosses no
        `await` and can stay a poll local: the emitter's normal block-end
        drop then frees it once per run.  A local anywhere else, or one live
        across a boundary, stays a field as before."""
        ok: Dict[str, bool] = {}

        def record(name: str, reentered: bool, crosses: bool):
            ok[name] = ok.get(name, True) and reentered and not crosses

        def walk_block(block: rast.Block, reentered: bool):
            for i, stmt in enumerate(block.stmts):
                if isinstance(stmt, (rast.LetStmt, rast.VarStmt)):
                    crosses = stmt.value is not None and _has_await(stmt.value)
                    if not crosses:
                        crosses = _crosses_after(stmt.name, block.stmts[i + 1:], block.expr)
                    record(stmt.name, reentered, crosses)
                walk_node(stmt, reentered)

        def walk_node(node, reentered: bool):
            if isinstance(node, rast.Block):
                walk_block(node, reentered)
            elif isinstance(node, rast.WhileStmt):
                walk_node(node.cond, reentered)
                walk_block(node.body, True)
            elif isinstance(node, rast.ForStmt):
                walk_node(node.iter, reentered)
                walk_block(node.body, True)
            elif isinstance(node, rast.DeferStmt):
                # A `defer` body is one synchronous region: it runs whole at
                # each exit edge, so its own locals never cross a state.
                walk_block(node.body, True)
            else:
                for child in _child_nodes(node):
                    walk_node(child, reentered)

        if body is not None:
            walk_block(body, False)
        return {name for name, is_poll in ok.items() if is_poll}

    def _check_source(self, aw: rast.Await):
        """Refuse, at the await, a poll source with no declared `Option<T>`
        (AGAST #4558, #4604), here in source order and before an untyped
        local it would have typed is reported."""
        inner = _ungroup(aw.expr)
        if isinstance(inner, rast.Call) and isinstance(inner.func, rast.Ident):
            if inner.func.name in self.async_functions:
                return
        if held_future_fn(inner, self.current_locals, self.fn_sigs) is not None:
            return
        check_poll_source(inner, self.current_locals, self.fn_sigs, aw.span)

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
            self._check_source(expr)
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
    STATE = '__state'
    # The header's first field: the future's own poll, `fn(*u8) -> bool`.
    POLL = '__poll'
    # `__state` once the body has finished.
    DONE = -1

    # An awaited expression that is not an async fn's call is a hand-written
    # poll source, evaluated again at each poll: an `Option<i32>`, `None`
    # while Pending and `Some(v)` once Ready.  The status is the Option's, so
    # every i32 is a genuine result, -1 and -4096 among them (AGAST #4558;
    # #4485's reserved -4096 is gone).  The source may be any `Option<T>`, and
    # the await's value is its T, read from the callee's declared return type
    # (AGAST #4604).  ritz1 lowers it alike (async_lower.ritz's al_lower_await).
    SOURCE_TYPE = 'Option'

    def __init__(self, span: rast.Span, fn_name: Optional[str] = None):
        self.span = span
        # The async fn whose poll this is: a narrowing in the store of its
        # result names `fn_name`, not `*self.__result` (#4166).
        self.fn_name = fn_name

    def _bool(self, value: bool) -> rast.Expr:
        return rast.BoolLit(span=self.span, value=value)

    def _state(self, span) -> rast.Field:
        """`(*self).__state`."""
        return rast.Field(span=span, field=self.STATE,
                          expr=rast.UnaryOp(span=span, op='*', operand=rast.Ident(span=span, name='self')))

    def _done(self, span) -> rast.Expr:
        return rast.BinOp(span=span, op='-', left=rast.IntLit(span=span, value=0),
                          right=rast.IntLit(span=span, value=-self.DONE))

    def finish(self, span) -> rast.Stmt:
        """Mark this future finished: a later poll is true at once."""
        return rast.AssignStmt(span=span, target=self._state(span), value=self._done(span))

    def finished_guard(self, span) -> rast.Stmt:
        """A poll's first statement: a finished future is Ready, its body
        not run again (LARB R79)."""
        return rast.ExprStmt(span=span, expr=rast.If(
            span=span, cond=rast.BinOp(span=span, op='==', left=self._state(span), right=self._done(span)),
            then_block=rast.Block(span=span, stmts=[rast.ReturnStmt(span=span, value=self._bool(True))], expr=None),
            else_block=None))

    @classmethod
    def header(cls, span) -> List[Tuple[str, rast.Type]]:
        """FUTURE_HEADER: every future's first fields, in this order."""
        byte_ptr = rast.PtrType(span=span, inner=rast.NamedType(span=span, name='u8'), mutable=False)
        return [(cls.POLL, rast.FnType(span=span, params=[byte_ptr], ret=rast.NamedType(span=span, name=cls.RET_TYPE))),
                (cls.STATE, rast.NamedType(span=span, name='i32'))]

    def not_ready(self, polled: rast.Expr) -> rast.Expr:
        """Whether an inner generated poll's answer, `polled`, is Pending."""
        return rast.UnaryOp(span=self.span, op='!', operand=polled)

    @classmethod
    def source_value_type(cls, ty: Optional[rast.Type],
                          enums: Dict[str, rast.EnumDef]) -> Optional[rast.Type]:
        """The T of a poll source's type `ty`, `Option<T>` as written or the
        monomorphised `Option$T` an import of ritzlib.option has made it by
        now (its `Some` payload); None for any other type (AGAST #4604)."""
        if not isinstance(ty, rast.NamedType):
            return None
        if ty.name == cls.SOURCE_TYPE and len(ty.args) == 1:
            return ty.args[0]
        if ty.args or not ty.name.startswith(cls.SOURCE_TYPE + '$'):
            return None
        enum = enums.get(ty.name)
        some = [v for v in enum.variants if v.name == 'Some'] if enum is not None else []
        if len(some) != 1 or len(some[0].fields) != 1:
            return None
        return some[0].fields[0]

    def expr_is_pending(self, answer: rast.Expr) -> rast.Expr:
        """Whether an awaited poll source's `answer` is Pending: `answer.is_none()`."""
        return rast.MethodCall(span=self.span, expr=answer, method='is_none', args=[])

    def expr_value(self, answer: rast.Expr) -> rast.Expr:
        """A Ready poll source's value: `answer.unwrap()`, read once it is not None."""
        return rast.MethodCall(span=self.span, expr=answer, method='unwrap', args=[])

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
                stmts.append(rast.AssignStmt(span=span, target=result, value=value,
                                             lowered_return=self.fn_name))
            elif not isinstance(value, (rast.IntLit, rast.BoolLit, rast.Ident, rast.Field)):
                stmts.append(rast.ExprStmt(span=span, expr=value))
        stmts.append(self.finish(span))
        stmts.append(rast.ReturnStmt(span=span, value=rast.BoolLit(span=span, value=True)))
        return rast.Block(span=span, stmts=stmts, expr=None)

    def ready(self, result: Optional[rast.Field], value: Optional[rast.Expr], span) -> rast.Stmt:
        """Return Ready from this poll, `value` stored in `result` (None for a
        unit fn)."""
        return rast.ExprStmt(span=span, expr=self._store_then_true(result, value, span))

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


def _has_return(node) -> bool:
    """Whether `node` holds a `return` (which leaves the whole fn, and so
    runs every active `defer`, however deeply it sits)."""
    if isinstance(node, (rast.ReturnStmt, rast.ReturnExpr)):
        return True
    return any(_has_return(child) for child in _child_nodes(node))


class _IfTyper(AsyncAnalyzer):
    """_infer_type that also reads through a value `if` and a block's tail,
    for an awaiting `if` operand's `__if_K` field (AGAST #4190).  ritz1's
    al_value_type.  Only that field's type: an untyped `let`'s is unchanged."""

    def _infer_type(self, expr: rast.Expr) -> Optional[rast.Type]:
        expr = _ungroup(expr)
        if isinstance(expr, rast.Block):
            return None if expr.expr is None else self._infer_type(expr.expr)
        if isinstance(expr, rast.If):
            if expr.else_block is None:
                return None
            # The first arm whose value isn't a bare literal (`7`, which takes
            # the other arm's type); else the first arm that answers (`i64`).
            arms = (expr.then_block, expr.else_block)
            for arm in arms:
                if not _untyped_int_literal(_tail_value(arm)):
                    ty = self._infer_type(arm)
                    if ty is not None:
                        return ty
            for arm in arms:
                ty = self._infer_type(arm)
                if ty is not None:
                    return ty
            return None
        return super()._infer_type(expr)


def _tail_value(expr: rast.Expr) -> Optional[rast.Expr]:
    """A block's value, read through blocks and parentheses."""
    expr = _ungroup(expr)
    while isinstance(expr, rast.Block):
        expr = None if expr.expr is None else _ungroup(expr.expr)
    return expr


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


def _mentions(node, name: str) -> bool:
    """Whether `node` reads or writes the local `name` (AGAST #4527)."""
    if isinstance(node, rast.Ident):
        return node.name == name
    return any(_mentions(child, name) for child in _child_nodes(node))


def _splits(node) -> bool:
    """Whether lowering `node` ends the state it starts in: it holds an
    `await`, or a `break` / `continue` out of a loop that lowers it."""
    if _has_await(node):
        return True
    if isinstance(node, (rast.WhileStmt, rast.ForStmt)):
        return _escaping_jump(node.body) is not None
    return _escaping_jump(node) is not None


def _uses_across(node, name: str, split: bool) -> bool:
    """Whether `node` uses `name` in a state other than the one before it.

    A `defer` body runs at exits, after any await on the way out; a lowered
    loop runs the name from its back edge or exit; any statement holding an
    `await` may read it in a state of its own.  Otherwise only a use after an
    earlier split crosses (a conservative answer: crossing keeps a field)."""
    if isinstance(node, rast.DeferStmt):
        return _mentions(node.body, name)
    if isinstance(node, (rast.WhileStmt, rast.ForStmt)):
        return (_splits(node) or split) and _mentions(node, name)
    if _splits(node):
        return _mentions(node, name)
    return split and _mentions(node, name)


def _crosses_after(name: str, stmts: List[rast.Stmt], tail: Optional[rast.Expr]) -> bool:
    """Whether `name`, declared before `stmts`, is used after a state
    boundary in the same activation (AGAST #4527)."""
    split = False
    for stmt in stmts:
        if isinstance(stmt, (rast.LetStmt, rast.VarStmt)) and stmt.name == name:
            return False  # a redeclaration shadows it; its own decl is checked
        if _uses_across(stmt, name, split):
            return True
        if _splits(stmt):
            split = True
    return split and tail is not None and _mentions(tail, name)


def _range_of(it: rast.Expr) -> Optional[rast.Range]:
    """A `for`'s iterable as the range the emitter loops over (its
    _normalize_for_iter_expr); None for an array, Vec or other iterable."""
    if isinstance(it, rast.Range):
        return it if it.start is not None and it.end is not None else None
    if isinstance(it, rast.BinOp):
        if it.op == 'as':
            return _range_of(it.left)
        if isinstance(it.left, rast.Range):
            # `for i in 0..n - 1` parses as (0..n) - 1.
            r = it.left
            return _range_of(rast.Range(r.span, r.start, rast.BinOp(it.span, it.op, r.end, it.right), r.inclusive))
    if isinstance(it, rast.Cast):
        return _range_of(it.expr)
    return None


def _ungroup(expr: rast.Expr) -> rast.Expr:
    while isinstance(expr, rast.Grouped):
        expr = expr.expr
    return expr


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

    A name that lives in the future struct (a param, or a local that outlives
    a state boundary) reads and writes `(*self).name`, wherever it appears: a
    `while` condition, an assignment's target, a match arm (AGAST #3727: only
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
        # A name read through another field: an awaiting `for`'s var (#4188).
        self.renames: Dict[str, str] = {}

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

        if id(node) in self.await_results:
            # A state drove it (an await, or a short-circuit `&&` / `||`
            # whose right operand awaits): its value is stored.
            return self.self_field(self.await_results[id(node)], node.span)
        if isinstance(node, rast.Ident):
            if node.name in self.renames:
                return self.self_field(self.renames[node.name], node.span)
            if node.name in self.fields:
                return self.self_field(node.name, node.span)
            return node
        if isinstance(node, rast.Await):
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
    scope: int = 0  # the loop body's defer-scope index: `break`/`continue` run from it


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
        self.n_shorts = 0
        self.n_ifs = 0
        self.n_fors = 0
        self.n_matches = 0
        # The `defer`s registered so far in each enclosing block, innermost
        # last.  A deferred body runs on every exit edge of its block: the
        # state machine can't leave that to the emitter, whose drop scopes
        # don't span the states the block's exit does (AGAST #4191).
        self.defer_scopes: List[List[rast.DeferStmt]] = []
        # Fields the lowering adds: awaited futures, await results,
        # short-circuit values, range-`for` vars and ends and binding
        # `match`es' scrutinees, in the order lowering meets them.
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
        """Return Ready from the poll.  A Ready leaves every block, so every
        active `defer` runs, innermost first, after `value` is stored."""
        if not self._has_active_defers():
            self._close(self.rw.ready(value, span))
            return
        self._emit_ready_value(value, span)
        self._run_exit_defers(0)
        self._close(self.abi.finish(span),
                    rast.ReturnStmt(span=span, value=rast.BoolLit(span=span, value=True)))

    def _emit_ready_value(self, value: Optional[rast.Expr], span):
        """Store a Ready's value in `__result`, without finishing: PollAbi's
        `_store_then_true` minus the finish, so defers can run in between."""
        if value is None:
            return
        result = self.rw.result(span)
        if result is not None:
            self.emit(rast.AssignStmt(span=span, target=result, value=value,
                                      lowered_return=self.abi.fn_name))
        elif not isinstance(value, (rast.IntLit, rast.BoolLit, rast.Ident, rast.Field)):
            self.emit(rast.ExprStmt(span=span, expr=value))

    def _has_active_defers(self) -> bool:
        return any(self.defer_scopes)

    def _run_exit_defers(self, from_index: int):
        """Run the defers of every block from `from_index` inward, innermost
        block first and, within one, in reverse order (LARB §13.7).  Each
        deferred block is rewritten afresh: the same body runs at several
        exits, and a rewrite must not be shared between them."""
        for scope in reversed(self.defer_scopes[from_index:]):
            for defer in reversed(scope):
                for stmt in self.rw.rewrite(defer.body).stmts:
                    self.emit(stmt)

    def _lower_return_tail(self, tail: rast.Expr, loop: Optional[_Loop]):
        """The body's (or a block's) tail value when a `defer` is active: the
        value is evaluated and stored, then the defers run, then Ready."""
        if self.gen.fn_def.ret_type is not None:
            self.lower_value(tail, ('result', tail.span), loop)
        else:
            self.lower_value(tail, None, loop)
        if self.cur is not None:
            self._run_exit_defers(0)
            self._close(self.abi.finish(self.span),
                        rast.ReturnStmt(span=tail.span, value=rast.BoolLit(span=tail.span, value=True)))

    def _add_field(self, name: str, ty: rast.Type) -> str:
        self.extra_fields.append((name, ty))
        self.rw.fields.add(name)
        return name

    # -- statements --------------------------------------------------------

    def lower_body(self, body: rast.Block):
        self.cur = self.new_block()  # state 0
        # The function body is a block like any other: a defer in it runs at
        # its exits, which include the tail's Ready.
        self._lower_block(body, None, ('return',))

    def _lower_block(self, block: rast.Block, loop: Optional[_Loop], dest):
        """A whole block: its statements, its tail value into `dest`, then its
        fall-through defers.  A tail going to `return` stores its value before
        the defers run, and then leaves every enclosing block's defers to run:
        the fn's Ready."""

        self.defer_scopes.append([])
        self._lower_stmts(block.stmts, loop)
        if block.expr is not None:
            if dest == ('return',) and self._has_active_defers():
                self._lower_return_tail(block.expr, loop)
            else:
                self.lower_value(block.expr, dest, loop)
        elif dest == ('return',) and self.cur is not None:
            self.ret(None, block.span)  # leaves the fn: every defer runs
        if self.cur is not None:
            self._run_exit_defers(len(self.defer_scopes) - 1)
        self.defer_scopes.pop()

    def _lower_stmts(self, stmts: List[rast.Stmt], loop: Optional[_Loop]):
        for stmt in stmts:
            self.lower_stmt(stmt, loop)

    def _needs_lowering(self, node, loop: Optional[_Loop]) -> bool:
        if _has_await(node) or (loop is not None and _escaping_jump(node) is not None):
            return True
        # A `return` runs every active defer, which the emitter can't see
        # across states: lower the statement that holds it.
        return self._has_active_defers() and _has_return(node)

    def lower_stmt(self, stmt: rast.Stmt, loop: Optional[_Loop]):
        if isinstance(stmt, rast.DeferStmt):
            # Nothing runs at the `defer`: its body runs at each exit of this
            # block, which _run_exit_defers places on every edge.
            jump = _first_await(stmt.body)
            if jump is not None:
                raise AsyncLoweringError(
                    "`await` inside a `defer` in an async fn is not supported yet (AGAST #4013)",
                    jump.span)
            self.defer_scopes[-1].append(stmt)
            return
        if not self._needs_lowering(stmt, loop):
            self.emit(self.rw.rewrite(stmt))
            if isinstance(stmt, rast.ReturnStmt):
                self.closed.add(self._at())
                self.cur = None
            return

        if isinstance(stmt, (rast.LetStmt, rast.VarStmt)):
            self.lower_value(stmt.value, ('field', stmt.name, stmt.span, stmt.name), loop)
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
            self._run_exit_defers(loop.scope)
            self.goto(loop.exit)
        elif isinstance(stmt, rast.ContinueStmt):
            self._run_exit_defers(loop.scope)
            self.goto(loop.head)
        elif isinstance(stmt, rast.UnsafeBlock):
            self.lower_value(stmt.body, None, loop)
        elif isinstance(stmt, rast.ForStmt):
            self._lower_for(stmt)
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
        # `break` / `continue` leave the body block: its defers run from there.
        self._lower_block(stmt.body, _Loop(head, exit_b, len(self.defer_scopes)), None)
        if self.cur is not None:
            self.goto(head)
        self.cur = exit_b

    def _for_type(self, rng: rast.Range) -> Optional[rast.Type]:
        """An awaiting `for`'s var's type: its start's, unless that is a bare
        literal (`0..n`) or untold; then its end's.  ritz1's al_for_type."""
        inf = AsyncAnalyzer(self.gen.fn_sigs)
        inf.current_locals = dict(self.gen.analysis.all_locals)
        start, end = _ungroup(rng.start), _ungroup(rng.end)
        ty = None if _untyped_int_literal(start) else inf._infer_type(start)
        return ty if ty is not None else inf._infer_type(end)

    def _lower_for(self, stmt: rast.ForStmt):
        """`for v in a..b` (AGAST #4188): `v` and the end are future fields,
        `__for_K` and `__for_end_K`, the end evaluated once; then a `while
        __for_K < __for_end_K` whose `continue` goes to the increment."""
        rng = _range_of(stmt.iter)
        if rng is None:
            raise _unplaced("a `for` over an iterable", self._culprit(stmt))
        ty = self._for_type(rng)
        if ty is None:
            raise AsyncLoweringError(
                f"cannot infer the type of `{stmt.var}`, which `{self.gen.fn_def.name}`'s future holds "
                f"across an `await`: cast a bound of its range (`0..(n as i64)`)", stmt.span)
        k = self.n_fors
        self.n_fors += 1
        var = self._add_field(f"__for_{k}", ty)
        end = self._add_field(f"__for_end_{k}", ty)
        self.emit(rast.AssignStmt(span=stmt.span, target=self.rw.self_field(var, stmt.span),
                                  value=self.hoist(rng.start)))
        self.emit(rast.AssignStmt(span=stmt.span, target=self.rw.self_field(end, stmt.span),
                                  value=self.hoist(rng.end)))
        head = self.new_block()
        self.goto(head)
        self.cur = head
        cond = rast.BinOp(span=stmt.span, op='<=' if rng.inclusive else '<',
                          left=self.rw.self_field(var, stmt.span), right=self.rw.self_field(end, stmt.span))
        body, incr, exit_b = self.new_block(), self.new_block(), self.new_block()
        self.branch(cond, body, exit_b)
        self.cur = body
        # A nested `for` can't reuse the name, so no outer rename is hidden.
        self.rw.renames[stmt.var] = var
        loop = _Loop(incr, exit_b, len(self.defer_scopes))
        self._lower_block(stmt.body, loop, None)
        del self.rw.renames[stmt.var]
        if self.cur is not None:
            self.goto(incr)
        self.cur = incr
        self.emit(rast.AssignStmt(span=stmt.span, target=self.rw.self_field(var, stmt.span), value=rast.BinOp(
            span=stmt.span, op='+', left=self.rw.self_field(var, stmt.span),
            right=rast.IntLit(span=stmt.span, value=1))))
        self.goto(head)
        self.cur = exit_b

    # -- values ------------------------------------------------------------

    def lower_value(self, expr: rast.Expr, dest, loop: Optional[_Loop]):
        """Evaluate `expr` into `dest`: None (discarded), ('return',),
        ('result', span) (a Ready's value, before its defers and finish),
        ('field', local, span) or ('assign', stmt, target)."""
        while isinstance(expr, rast.Grouped):
            expr = expr.expr
        if not self._needs_lowering(expr, loop):
            self.deliver(self.rw.rewrite(expr), dest)
            if (isinstance(expr, rast.Block) and expr.expr is None and expr.stmts
                    and isinstance(expr.stmts[-1], rast.ReturnStmt) and self.cur is not None):
                # An arm emitted whole that ends in `return` is Ready: no
                # jump may follow it (an `if (await f()) > 0` arm, #4013).
                self.closed.add(self.cur)
                self.cur = None
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
            self._lower_block(expr, loop, dest)
        elif isinstance(expr, rast.Match) and any(self._needs_lowering(arm.body, loop) for arm in expr.arms):
            self._lower_match(expr, dest, loop)
        elif isinstance(expr, rast.BreakExpr) and loop is not None:
            self._run_exit_defers(loop.scope)
            self.goto(loop.exit)  # an arm's `break` (#4189)
        elif isinstance(expr, rast.ContinueExpr) and loop is not None:
            self._run_exit_defers(loop.scope)
            self.goto(loop.head)
        elif isinstance(expr, rast.Await):
            self.lower_await(expr, dest)
        elif not _has_await(expr):
            # Only a jump out of the loop, from an operand (`1 + if c ...`),
            # where it can't be a state edge.
            raise AsyncLoweringError(
                "`break` / `continue` inside an expression of an async fn's loop that awaits "
                "is not supported yet (AGAST #4013)", _escaping_jump(expr).span)
        else:
            self.deliver(self.hoist(expr), dest)

    def _rematch(self, m: rast.Match, scrut: rast.Expr, bodies) -> rast.Stmt:
        """`m`'s arms over `scrut`, arm j running `bodies(j)`: the same
        patterns, so the same arm is taken and the match stays exhaustive."""
        new = copy.copy(m)
        new.expr = scrut
        new.arms = [rast.MatchArm(span=arm.span, pattern=arm.pattern, guard=None,
                                  body=rast.Block(span=arm.span, stmts=bodies(j), expr=None))
                    for j, arm in enumerate(m.arms)]
        return rast.ExprStmt(span=m.span, expr=new)

    def _lower_match(self, m: rast.Match, dest, loop: Optional[_Loop]):
        """A `match` whose arms await, or jump out of the loop (AGAST #4189):
        each arm is a state, entered by matching the scrutinee once.

        An arm's names are bound by the match, which a later state of the arm
        doesn't run.  When an arm binds one, the scrutinee is a future field,
        `__match_K`, and each of that arm's states runs inside a match of it
        over the same patterns (a pattern binds no `mut` name, and has no
        guard, so the same arm is taken with the same values):

            __match_K = scrutinee
            match __match_K { p0 => -> A0, p1 => -> A1 }
          A1: match __match_K { p0 => {}, p1 => { ...A1's statements } }"""
        names = [_pattern_names(arm.pattern) for arm in m.arms]
        scrut = self.hoist(m.expr)
        slot = None
        if any(names):
            inf = AsyncAnalyzer(self.gen.fn_sigs)
            inf.current_locals = dict(self.gen.analysis.all_locals)
            ty = inf._infer_type(_ungroup(m.expr))
            if ty is None:
                raise AsyncLoweringError(
                    f"cannot infer the type of the `match`'s scrutinee, which `{self.gen.fn_def.name}`'s future "
                    f"holds across an `await`: match a typed local (`let v: T = ...`)", m.expr.span)
            slot = self._add_field(f"__match_{self.n_matches}", ty)
            self.n_matches += 1
            self.emit(rast.AssignStmt(span=m.span, target=self.rw.self_field(slot, m.span), value=scrut))
            scrut = self.rw.self_field(slot, m.span)
        entries = [self.new_block() for _ in m.arms]
        join = self.new_block()
        self._close(self._rematch(m, scrut, lambda j: [self._set_state(entries[j])]),
                    rast.ContinueStmt(span=self.span))
        for i, arm in enumerate(m.arms):
            first = len(self.blocks)
            self.cur = entries[i]
            # The arm's names are its own, not a field or a `for` var.
            hidden = names[i] & self.rw.fields
            self.rw.fields -= hidden
            renamed = {n: self.rw.renames.pop(n) for n in names[i] if n in self.rw.renames}
            try:
                self.lower_value(arm.body, dest, loop)
            finally:
                self.rw.fields |= hidden
                self.rw.renames.update(renamed)
            if self.cur is not None:
                self.goto(join)
            if names[i]:
                # A nested match's states are wrapped already: this match
                # goes around, so its names are in scope there too.
                for b in [entries[i]] + list(range(first, len(self.blocks))):
                    body = self.blocks[b]
                    self.blocks[b] = [self._rematch(m, self.rw.self_field(slot, m.span),
                                                    lambda j: body if j == i else [])]
        self.cur = join

    def deliver(self, value: rast.Expr, dest):
        if dest is None:
            # A value nobody reads: keep it only for its effects.
            if not isinstance(value, (rast.IntLit, rast.Field, rast.Ident)):
                self.emit(rast.ExprStmt(span=value.span, expr=value))
        elif dest[0] == 'return':
            self.ret(value, value.span)
        elif dest[0] == 'result':
            # A Ready's value store on its own: the defers run after it, so
            # the finish and return true come later (AGAST #4191).
            self.emit(rast.AssignStmt(span=dest[1], target=self.rw.result(dest[1]), value=value,
                                      lowered_return=self.abi.fn_name))
        elif dest[0] == 'field':
            _, name, span, *let = dest
            self.emit(rast.AssignStmt(span=span, target=self.rw.self_field(name, span), value=value,
                                      lowered_let=let[0] if let else None))
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
            if under is None and node.else_block is not None and _has_await(node):
                self._if_value(node)
                return
            self._hoist(node.cond, under)
            for arm in (node.then_block, node.else_block):
                if arm is not None:
                    self._hoist(arm, under or "an `if` inside an expression")
            return
        if isinstance(node, rast.Match):
            self._hoist(node.expr, under)
            for arm in node.arms:
                self._hoist(arm, under or "a `match` inside an expression")
            return
        if isinstance(node, rast.BinOp) and node.op in ('&&', '||', 'and', 'or'):
            if under is None and _has_await(node.right):
                self._short_circuit(node)
                return
            self._hoist(node.left, under)
            self._hoist(node.right, under)
            return
        if isinstance(node, rast.Block):
            under = under or "a block inside an expression"
        for child in _child_nodes(node):
            self._hoist(child, under)

    def _short_circuit(self, node: rast.BinOp):
        """`l && r` / `l || r` whose `r` awaits (AGAST #4013): `r`, and its
        awaits, run only when `l` doesn't decide the value.

            __short_K = l
            if __short_K { -> R } else { -> J }    # `||`: the arms swap
          R: __short_K = r                         # r's awaits in states
          J: ... the expression reads __short_K"""
        self._hoist(node.left, None)
        tmp = self._add_field(f"__short_{self.n_shorts}", self.gen._make_named_type('bool'))
        self.n_shorts += 1
        self.emit(rast.AssignStmt(span=node.span, target=self.rw.self_field(tmp, node.span),
                                  value=self.rw.rewrite(node.left)))
        rhs, join = self.new_block(), self.new_block()
        known = self.rw.self_field(tmp, self.span)
        if node.op in ('&&', 'and'):
            self.branch(known, rhs, join)
        else:
            self.branch(known, join, rhs)
        self.cur = rhs
        self.emit(rast.AssignStmt(span=node.span, target=self.rw.self_field(tmp, node.span),
                                  value=self.hoist(node.right)))
        self.goto(join)
        self.cur = join
        self.rw.await_results[id(node)] = tmp

    def _if_type(self, node: rast.If) -> Optional[rast.Type]:
        typer = _IfTyper(self.gen.fn_sigs)
        typer.current_locals = dict(self.gen.analysis.all_locals)
        return typer._infer_type(node)

    def _if_value(self, node: rast.If):
        """A value `if` that is an operand and awaits (AGAST #4190): each arm
        runs in states of its own, its awaits only when it is taken, and
        writes the value to a field the expression reads.  #4013's
        _short_circuit, with two arms.

            if c { -> T } else { -> E }    # c's awaits first
          T: __if_K = then-value           # its awaits in states
          E: __if_K = else-value
          J: ... the expression reads __if_K"""
        jump = _escaping_jump(node)
        if jump is not None:
            # An arm's `break` would leave the dispatch loop, not the user's.
            raise AsyncLoweringError(
                "`break` / `continue` inside an expression of an async fn's loop that awaits "
                "is not supported yet (AGAST #4013)", jump.span)
        ty = self._if_type(node)
        if ty is None:
            raise AsyncLoweringError(
                f"cannot infer the type of the `if`'s value, which `{self.gen.fn_def.name}`'s future holds "
                f"across an `await`: cast an arm (`x as i32`)", node.span)
        self._hoist(node.cond, None)
        tmp = self._add_field(f"__if_{self.n_ifs}", ty)
        self.n_ifs += 1
        then_b, else_b, join = self.new_block(), self.new_block(), self.new_block()
        self.branch(self.rw.rewrite(node.cond), then_b, else_b)
        for entry, arm in ((then_b, node.then_block), (else_b, node.else_block)):
            self.cur = entry
            self.lower_value(arm, ('field', tmp, node.span), None)
            if self.cur is not None:
                self.goto(join)
        self.cur = join
        self.rw.await_results[id(node)] = tmp

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
        held = self.gen._held_future(inner)
        if held is not None:
            # A held future (LARB R79): polled where it is, not rebuilt.  A
            # finished one answers true at once, and is only read.
            self._resume_on(held.name, self.hoist(inner), aw, dest)
            return
        if self.gen._is_async_call(inner):
            fn_name = inner.func.name
            fut = self._add_field(f"__future_{k}", self.gen._make_named_type(future_type_name(fn_name)))
            args = [self.hoist(a) for a in inner.args]
            # The call keeps its source spans: it is the user's call of `foo`,
            # so a private `foo` of another file is refused here, at `foo`
            # (#3925, LARB R45a).  `foo$poll` is the compiler's own call.
            # The build takes the await's span: the emitter locates code per
            # statement, and a call with no !dbg location makes LLVM strip
            # the module's debug info (#3800).  The resume state is emitted
            # next, so `foo$poll` inherits the location.
            self.emit(rast.AssignStmt(
                span=aw.span, target=self.rw.self_field(fut, self.span),
                value=rast.Call(span=inner.span, func=rast.Ident(span=inner.func.span, name=fn_name), args=args)))
            self._resume_on(fn_name, self.rw.self_field(fut, self.span), aw, dest)
            return
        source_type, _ = self.gen._poll_source(inner, aw)
        answer = f"__poll_{k}"
        polled = self.hoist(inner)
        resume = self.new_block()
        self.goto(resume)
        self.cur = resume
        # The await's span locates the poll source's call (#3800).
        self.emit(rast.LetStmt(span=aw.span, name=answer,
                               type=copy.deepcopy(source_type), value=polled))
        self.emit(rast.ExprStmt(span=self.span, expr=rast.If(
            span=self.span, cond=self.abi.expr_is_pending(rast.Ident(span=self.span, name=answer)),
            then_block=rast.Block(span=self.span, stmts=[self.abi.pending()], expr=None), else_block=None)))
        self.deliver(self.abi.expr_value(rast.Ident(span=self.span, name=answer)), dest)

    def _resume_on(self, fn_name: str, fut: rast.Expr, aw: rast.Await, dest):
        """A resume state polling `fn_name`'s future, the place `fut`, until
        true (Pending until then), then `fut.__result` into `dest`."""
        polled = rast.Call(span=self.span, func=rast.Ident(span=self.span, name=poll_fn_name(fn_name)),
                           args=[rast.UnaryOp(span=self.span, op='@', operand=fut)])
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
        self.deliver(self.abi.result_field(fut, self.span), dest)

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
    fn, and `NAME$poll`, which runs the body from its current state to the
    next Pending await or to its end (Ready).

    When async_functions is provided, recognizes calls to async functions
    and generates proper foo() + foo$poll() sequences.
    """

    def __init__(self, analysis: AsyncFnAnalysis, async_functions: Optional[Set[str]] = None,
                 fn_sigs: Optional[Dict[str, rast.FnDef]] = None):
        self.analysis = analysis
        # Declared fns by name: an awaited async fn's result type (R78).
        self.fn_sigs: Dict[str, rast.FnDef] = fn_sigs if fn_sigs is not None else {}
        self.fn_def = analysis.fn_def
        self.dummy_span = rast.Span(0, 0, 0, 0)
        # Set of known async function names (for await transformation)
        self.async_functions = async_functions or set()
        self.abi = PollAbi(self.dummy_span, self.fn_def.name)

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

        fields_ = PollAbi.header(self.dummy_span)
        if self.fn_def.ret_type is not None:
            # Where the poll leaves its value (LARB R78).
            fields_.append((PollAbi.RESULT, self.fn_def.ret_type))
        fields_ += [(p.name, p.type) for p in self.fn_def.params]
        for name in sorted(local_fields):
            ty = self.analysis.all_locals.get(name)
            if ty is not None:
                fields_.append((name, ty))
        fields_ += extra
        future_name = future_type_name(self.fn_def.name)
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
        a hand-written poll source's T, of its `Option<T>` (AGAST #4604)."""
        inner = aw.expr
        while isinstance(inner, rast.Grouped):
            inner = inner.expr
        if self._is_async_call(inner):
            ty = self._async_ret_type(inner.func.name)
            if ty is None:
                raise AsyncLoweringError(
                    f"`await {inner.func.name}(..)` has no value: `{inner.func.name}` is a unit async fn", aw.span)
            return ty
        held = self._held_future(inner)
        if held is not None and held.ret_type is not None:
            return held.ret_type
        return self._poll_source(inner, aw)[1]

    def _poll_source(self, inner: rast.Expr, aw: rast.Await) -> Tuple[rast.Type, rast.Type]:
        """A poll source's `(Option<T>, T)`, from the declared return type of
        the fn or method it calls (AGAST #4604); refused at the await when
        there is none, or it is no `Option` (#4558).  The analyzer has
        refused these already, in source order."""
        types = {p.name: p.type for p in self.fn_def.params}
        types.update(self.analysis.all_locals)
        return check_poll_source(inner, types, self.fn_sigs, aw.span)

    def _held_future(self, expr: rast.Expr) -> Optional[rast.FnDef]:
        """The async fn whose future the local or param `expr` holds."""
        types = {p.name: p.type for p in self.fn_def.params}
        types.update(self.analysis.all_locals)
        return held_future_fn(expr, types, self.fn_sigs)

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
        stmts.append(rast.AssignStmt(span=span, target=fut_field(PollAbi.POLL),
                                     value=self._make_ident(poll_fn_name(self.fn_def.name))))
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
        """`NAME$poll(self: *NAME$Future)`, answering as PollAbi says."""
        self_param = rast.Param(
            span=self.dummy_span,
            name='self',
            type=rast.PtrType(span=self.dummy_span, inner=self._make_named_type(future_name), mutable=True)
        )
        body = rast.Block(span=body.span, stmts=[self.abi.finished_guard(self.dummy_span)] + body.stmts,
                          expr=body.expr)
        return rast.FnDef(
            span=self.dummy_span,
            name=poll_fn_name(self.fn_def.name),
            params=[self_param],
            ret_type=self._make_named_type(PollAbi.RET_TYPE),
            body=body,
            is_async=False,
            is_async_poll=True,
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
                                                         value=tail, lowered_return=self.fn_def.name))
            else:
                transformed.stmts.append(rast.ExprStmt(span=tail.span, expr=tail))
        transformed.stmts.append(self.abi.finish(self.dummy_span))
        transformed.expr = rast.BoolLit(span=self.dummy_span, value=True)
        return transformed


def analyze_async_function(fn_def: rast.FnDef,
                           fn_sigs: Optional[Dict[str, rast.FnDef]] = None,
                           async_functions: Optional[Set[str]] = None) -> AsyncFnAnalysis:
    """Convenience function to analyze an async function."""
    analyzer = AsyncAnalyzer(fn_sigs, async_functions)
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
    analysis = analyze_async_function(fn_def, fn_sigs, async_functions)
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

    assert sm.future_struct.name == "simple$Future"
    assert sm.constructor_fn.name == "simple"
    assert sm.poll_fn.name == "simple$poll"
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
