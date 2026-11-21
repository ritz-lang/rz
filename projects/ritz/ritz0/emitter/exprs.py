"""Expression emission, split out of emitter_llvmlite (AGAST #1826, slice 2).

`_emit_expr` and `_emit_expr_core` were LLVMEmitter methods in the 18k-line
emitter_llvmlite.py.  The core was one 431-line if/elif chain whose cyclomatic
complexity was far over the #1826 ceiling of 60.  It is now an `ExprEmitter`
mixin:

  * `_emit_expr` is the wrapper that records operands, spans and temporaries
    (moved verbatim);
  * `_emit_expr_core` is the dispatch over expression families, with the two
    large branches delegated;
  * `_emit_expr_ident` handles `Ident` (constants, locals, params, globals,
    unit variants, function pointers, ...);
  * `_emit_expr_binop` handles `BinOp`, splitting operand unification
    (`_emit_binop_operands`) from operator selection (`_emit_binop_result`).

The moved branches are the same code in the same order, so the emitted IR is
byte-identical; the corpus replay against an origin/main worktree is the
evidence for that.
"""

from llvmlite import ir

import ritz_ast as rast
import bool_rules
import float_rules
from const_eval import fold_literal_i64
from emitter.common import (EmitError, InternalError, _is_float_lit_operand,
                            qualified_access_removed)


class ExprEmitter:
    """Expression emission for `LLVMEmitter`; mixed in ahead of its own base."""

    def _emit_expr(self, expr: rast.Expr) -> ir.Value:
        """Emit an expression."""
        # AGAST #1869: an operand _emit_assert already evaluated, so the
        # comparison and the failure report share one evaluation.
        if self._emitted_operands:
            pre = self._emitted_operands.get(id(expr))
            if pre is not None:
                return pre
        # AGAST #2261: part of a method call's receiver, already evaluated.
        if self._evaluated_once:
            pre = self._evaluated_once.get(id(expr))
            if pre is not None:
                return pre
        saved_span = self._emit_span
        span = getattr(expr, 'span', None)
        if span is not None:
            self._emit_span = span   # AGAST #3738: where its temporaries are
        try:
            val = self._emit_expr_core(expr)
        finally:
            self._emit_span = saved_span
        if getattr(expr, 'drop_temp', None) is not None:
            self._own_temporary(expr, val)
        self._value_origin[id(val)] = (val, expr)
        if id(expr) in self._ptr_tails:
            self._ptr_tails.discard(id(expr))
            self._check_str_tail(val, expr)
        return val

    def _emit_expr_core(self, expr: rast.Expr) -> ir.Value:
        """Emit an expression (_emit_expr, before temporaries)."""
        if id(expr) in self._slot_ctx_widths or id(expr) in getattr(self, '_literal_ctx_nodes', ()):
            # AGAST #1445 / #4164: a literal arm of an if / match in a typed slot.
            arm = self._literal_at_slot_width(expr)
            if arm is not None:
                return arm
        if isinstance(expr, rast.IntLit):
            return ir.Constant(self.i64, expr.value)

        elif isinstance(expr, rast.FloatLit):
            return ir.Constant(self.f64, expr.value)

        elif isinstance(expr, rast.BoolLit):
            return ir.Constant(self.i1, 1 if expr.value else 0)

        elif isinstance(expr, rast.StringLit) and not expr.as_ptr:
            # "hello" -> StrView (zero-copy view)
            return self._emit_strview_string_literal(expr)

        elif isinstance(expr, (rast.StringLit, rast.CStringLit)):
            # c"hello", or "hello" in a `*u8` slot -> *u8 (null-terminated)
            gvar = self._get_string_constant(expr.value)
            # Get pointer to first element
            zero = ir.Constant(self.i64, 0)
            return self.builder.gep(gvar, [zero, zero])

        # Note: SpanStringLit (s"...") was removed in AGAST #98 — bare
        # StringLit (above) emits a StrView of the same shape.

        elif isinstance(expr, rast.InterpString):
            # The parser builds an InterpString only as print / eprint's
            # argument, which _emit_call lowers itself (AGAST #2102). Reaching
            # here means some pass moved one out of that position.
            raise InternalError(f"internal: InterpString outside print/eprint (line {expr.span.line})")

        elif isinstance(expr, rast.CharLit):
            # Character literal is a u8 constant
            return ir.Constant(self.i8, expr.value)

        elif isinstance(expr, rast.NullLit):
            # Null pointer literal - type must be inferred from context
            # Default to *u8 (i8*) which is compatible with most pointer casts
            return ir.Constant(self.i8.as_pointer(), None)

        elif isinstance(expr, rast.Ident):
            return self._emit_expr_ident(expr)

        elif isinstance(expr, rast.BinOp):
            return self._emit_expr_binop(expr)

        elif isinstance(expr, rast.Call):
            return self._emit_lending_call(expr, self._emit_call)

        elif isinstance(expr, rast.Index):
            return self._emit_index(expr)

        elif isinstance(expr, rast.If):
            # If used as expression - returns phi value from branches
            result = self._emit_if(expr)
            if result is not None:
                return result
            # No value. This DOES happen: an else-less `if` in a
            # let/var/assign/return is rejected earlier (AGAST #1406,
            # `_reject_valueless_if`), but one used as an operand or call
            # argument still arrives here and still becomes this zero — a
            # silent wrong answer tracked as AGAST #1435. Statement-position
            # `if`s never reach this branch; they go straight to `_emit_if`.
            return ir.Constant(self.i32, 0)

        elif isinstance(expr, rast.UnaryOp):
            folded = fold_literal_i64(expr)          # `~63` (AGAST #4082)
            if folded is not None:
                return ir.Constant(self.i64, folded)
            return self._emit_unary(expr)

        elif isinstance(expr, rast.StructLit):
            return self._emit_struct_lit(expr)

        elif isinstance(expr, rast.ArrayLit):
            return self._emit_array_lit(expr)

        elif isinstance(expr, rast.ArrayFill):
            return self._emit_array_fill(expr)

        elif isinstance(expr, rast.TupleLit):
            return self._emit_tuple_lit(expr)

        elif isinstance(expr, rast.Field):
            # AGAST #2451: `t.len` on a String names no field. The lookup
            # locates it itself now (#1390), at this expression.
            return self._emit_field_access(expr)

        elif isinstance(expr, rast.Cast):
            self._raw_written(expr)
            return self._emit_cast(expr)

        elif isinstance(expr, rast.Match):
            return self._emit_match(expr)

        elif isinstance(expr, rast.MethodCall):
            return self._emit_lending_call(expr, self._emit_method_call)

        elif isinstance(expr, rast.TryOp):
            return self._emit_try_op(expr)

        elif isinstance(expr, rast.SliceExpr):
            return self._emit_slice(expr)

        elif isinstance(expr, rast.Await):
            return self._emit_await(expr)

        elif isinstance(expr, rast.HeapExpr):
            return self._emit_heap_expr(expr)

        elif isinstance(expr, rast.ContinueExpr):
            return self._emit_continue_expr(expr)

        elif isinstance(expr, rast.BreakExpr):
            return self._emit_break_expr(expr)

        elif isinstance(expr, rast.ReturnExpr):
            return self._emit_return_expr(expr)

        elif isinstance(expr, rast.Block):
            return self._emit_block_expr(expr)

        elif isinstance(expr, rast.AssignExpr):
            return self._emit_assign_expr(expr)

        elif isinstance(expr, rast.QualifiedIdent):
            # AGAST #2591: `::` is not Ritz syntax (LANGUAGE_SPEC §10.2, §15.3).
            # The parser still builds a QualifiedIdent so this can say so.
            # Nothing lowers one, not even `alias::item` under `import ... as
            # alias` (AGAST #1624), so every one reaching here is a source
            # error, not a missing emitter case.
            raise EmitError(qualified_access_removed(expr), expr.span)

        else:
            raise NotImplementedError(f"Expression: {type(expr)}")

    def _emit_expr_ident(self, expr: rast.Ident) -> ir.Value:
        """Emit an identifier: a constant, local, param, global, unit variant
        or function pointer."""
        name = expr.name

        # Check constants
        if name in self.constants:
            val, ty = self.constants[name]
            return ir.Constant(ty, val)

        # Check string constants (StrView)
        if hasattr(self, 'const_strviews') and name in self.const_strviews:
            gvar = self.const_strviews[name]
            # Load the StrView struct from the global
            return self.builder.load(gvar)

        # Check locals (var bindings) FIRST - mutable vars shadow let bindings
        # This is critical because the same name may appear as both 'var' and 'let'
        # in different branches of if-else, and we need to use the correct one.
        if name in self.locals:
            alloca, ty = self.locals[name]
            loaded = self.builder.load(alloca)
            self._note_move(expr)
            return loaded

        # Check params (let bindings and function params)
        if name in self.params:
            val, _ = self.params[name]
            self._note_move(expr)
            return val

        # Check module-level globals (var at top level)
        if name in self.globals:
            gvar, ty = self.globals[name]
            return self.builder.load(gvar)

        # A struct or enum const (LARB R60): a copy of its read-only data.
        if self._is_const_array_name(name) and not isinstance(
                self.const_arrays[name][1], ir.ArrayType):
            return self.builder.load(self.const_arrays[name][0])

        # Handle nil keyword (null pointer literal)
        if name == "nil":
            # Return a null pointer of i8* type
            return ir.Constant(ir.IntType(8).as_pointer(), None)

        # `pass` is a no-op with no value (LANGUAGE_SPEC §2.4, AGAST #3759).
        # As an arm of an if / match used as a statement it yields a
        # dummy that nothing reads. Where a value is wanted (a used arm,
        # an initialiser, operand, argument, ...) it is an error here, at
        # the `pass`: it was a silent 0, and invalid IR in a struct phi.
        if name == "pass":
            if id(expr) in self._used_arms or id(expr) in self._wanted_values:
                raise EmitError(self.PASS_HAS_NO_VALUE, getattr(expr, 'span', None))
            return ir.Constant(self.i32, 0)

        # Check if this is a unit variant (enum variant without parentheses)
        self._refuse_no_instance(expr)
        if name in self.variant_to_enum:
            self._check_variant_unambiguous(name, expr.span)
            # Get the variant and check if it's a unit variant (no fields)
            enum_name = self._bare_variant_enum(name)
            variant = self._get_enum_variant(enum_name, name)
            if not variant.fields:
                # Unit variant - construct it with no args
                return self._emit_enum_variant_constructor(name, [])

        # Check if this is a function name - return function pointer
        if name in self.functions:
            fn, fn_def = self.functions[name]
            # Return the function as a pointer value
            return fn

        raise self._err(f"Unknown identifier: {name}")

    def _emit_expr_binop(self, expr: rast.BinOp) -> ir.Value:
        """Emit a binary operator: short-circuits, literal folds, then the
        operands and the operator."""
        op = expr.op

        # bool only, so always short-circuit (LARB R4, AGAST #2342).
        if op in ('&&', 'and'):
            return self._emit_short_circuit_and(expr)
        elif op in ('||', 'or'):
            return self._emit_short_circuit_or(expr)

        # AGAST #4082: an all-literal operator is one constant, the i64
        # it computed, so R21 can give it its sibling's width.
        folded = fold_literal_i64(expr)
        if folded is not None:
            return ir.Constant(self.i64, folded)

        left, right, wider_slot = self._emit_binop_operands(expr)
        return self._emit_binop_result(expr, left, right, wider_slot)

    def _emit_binop_operands(self, expr: rast.BinOp):
        """Emit and unify a binop's operands: same integer width, one float
        width, integer literals in the neighbour's type.  Returns
        `(left, right, wider_slot)`."""
        op = expr.op
        left = self._emit_expr(expr.left)
        right = self._emit_expr(expr.right)
        self._check_bool_operands(expr, left, right)
        self._reject_struct_operand(expr, left, right)
        self._reject_pointer_strlit_compare(expr, left, right)

        # LARB R21 (#3112): a literal operand is the other operand's type.
        if op in self._INT_ARITH_OPS:
            left, right = self._literal_takes_operand_type(expr, left, right)

        # AGAST #3225: directly in a wider integer slot, the operation runs
        # in the slot's type, each operand widened by its own signedness.
        # `/` and `%` take the slot's signedness: `(a - b) / 2` into an i64
        # is a signed divide of a possibly negative difference.
        wider_slot = self._wider_slot(expr) if op in self._SLOT_ARITH_OPS else None
        if (wider_slot is not None and isinstance(left.type, ir.IntType)
                and isinstance(right.type, ir.IntType)):
            left = self._widen_to(expr.left, left, wider_slot[0])
            right = self._widen_to(expr.right, right, wider_slot[0])
        else:
            wider_slot = None

        # Ensure same type
        if left.type != right.type:
            if isinstance(left.type, ir.IntType) and isinstance(right.type, ir.IntType):
                # AGAST #1396: what R21 leaves alone, a shift's left literal
                # under a declared type (`let r: u32 = 1 << n`), takes the
                # declared width rather than widening its neighbour to 64
                # bits. Returns None whenever the declaration is absent or
                # asks for something wider, in which case the original
                # widening below runs unchanged.
                retyped = self._retype_literal_operand(expr, left, right)
                if retyped is not None:
                    left, right = retyped

            # Determine signedness for proper extension
            if (left.type != right.type
                    and isinstance(left.type, ir.IntType)
                    and isinstance(right.type, ir.IntType)):
                # An operator expression has its operands' type, so a u8
                # `a ^ z` widens with zext (#2361).
                left_unsigned = self._int_shape(expr.left, left.type.width < 64)[1]
                right_unsigned = self._int_shape(expr.right, right.type.width < 64)[1]

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

        # Unify float widths: `f32_value + 1.0` has an f32 operand and a
        # double literal. Narrow the literal side (its value is exact in
        # the source; `-lit` counts too, #1969), otherwise widen so both
        # sides agree.
        if (self._is_float_type(left.type) and self._is_float_type(right.type)
                and left.type != right.type):
            if _is_float_lit_operand(expr.right):
                right = self._convert_type(right, left.type)
            elif _is_float_lit_operand(expr.left):
                left = self._convert_type(left, right.type)
            elif expr.op in bool_rules.COMPARISONS:
                # §7.2, AGAST #3607: the writer picks the precision.  The
                # typing pass refuses it first; this holds without it.
                names = ('f32', 'f64') if left.type == self.f32 else ('f64', 'f32')
                raise EmitError(float_rules.mixed_float_compare(*names), expr.span)
            elif left.type == self.f32:
                left = self.builder.fpext(left, right.type)
            else:
                right = self.builder.fpext(right, left.type)

        # AGAST #4285: an integer literal operand (`x != 2`, `1 + x`) is
        # in a float slot (§7.5), so it is a constant of the other side's
        # float type, never the i64 it folded to.
        left, right = self._int_literal_takes_float_type(expr, left, right)

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

        return left, right, wider_slot

    def _emit_binop_result(self, expr: rast.BinOp, left, right, wider_slot) -> ir.Value:
        """Emit the operation of an already-unified binop."""
        op = expr.op

        # Check if this is a floating-point operation
        is_float = self._is_float_type(left.type) or self._is_float_type(right.type)

        if op in ('+', '-'):
            self._refuse_reference_arithmetic(expr, left, right)

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
            # AGAST #2928 / #2597: ptr - ptr is the distance in elements
            # (LANGUAGE_SPEC §7.1 "Pointer difference"), the inverse of
            # `p + n`.  `sub` on pointers is invalid IR.
            if isinstance(left.type, ir.PointerType) and isinstance(right.type, ir.PointerType):
                return self._pointer_difference(left, right, expr)
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
            if (wider_slot[1] if wider_slot is not None
                    else self._operands_unsigned(expr, left)):
                return self.builder.udiv(left, right)
            return self.builder.sdiv(left, right)
        elif op == '%':
            if is_float:
                # Not `frem`: it lowers to a libm fmod call (AGAST #3817).
                return self.builder.call(self._fmod_helper(left.type), [left, right])
            # Use unsigned remainder for unsigned types
            if (wider_slot[1] if wider_slot is not None
                    else self._operands_unsigned(expr, left)):
                return self.builder.urem(left, right)
            return self.builder.srem(left, right)
        elif op == '==':
            if is_float:
                return self.builder.fcmp_ordered('==', left, right)
            enum_cmp = self._try_enum_tag_compare(op, left, right)
            if enum_cmp is not None:
                return enum_cmp
            self._reject_aggregate_compare(op, left, expr)
            # Equality is sign-agnostic
            return self.builder.icmp_signed('==', left, right)
        elif op == '!=':
            if is_float:
                return self.builder.fcmp_unordered('!=', left, right)
            enum_cmp = self._try_enum_tag_compare(op, left, right)
            if enum_cmp is not None:
                return enum_cmp
            self._reject_aggregate_compare(op, left, expr)
            # Inequality is sign-agnostic
            return self.builder.icmp_signed('!=', left, right)
        elif op == '<':
            if is_float:
                return self.builder.fcmp_ordered('<', left, right)
            # Use unsigned comparison for unsigned types
            if self._operands_unsigned(expr, left):
                return self.builder.icmp_unsigned('<', left, right)
            return self.builder.icmp_signed('<', left, right)
        elif op == '<=':
            if is_float:
                return self.builder.fcmp_ordered('<=', left, right)
            if self._operands_unsigned(expr, left):
                return self.builder.icmp_unsigned('<=', left, right)
            return self.builder.icmp_signed('<=', left, right)
        elif op == '>':
            if is_float:
                return self.builder.fcmp_ordered('>', left, right)
            if self._operands_unsigned(expr, left):
                return self.builder.icmp_unsigned('>', left, right)
            return self.builder.icmp_signed('>', left, right)
        elif op == '>=':
            if is_float:
                return self.builder.fcmp_ordered('>=', left, right)
            if self._operands_unsigned(expr, left):
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
            # Logical on an unsigned left operand, arithmetic on a signed
            # one; the count has no say (#2356).
            if self._int_shape(expr.left, left.type.width < 64)[1]:
                return self.builder.lshr(left, right)
            return self.builder.ashr(left, right)
        else:
            raise InternalError(f"Unknown operator: {op}")
