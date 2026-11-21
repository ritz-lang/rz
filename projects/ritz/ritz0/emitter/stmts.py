"""Statement emission, split out of emitter_llvmlite (AGAST #1826, slice 3).

`_emit_stmt_inner` was a 631-line LLVMEmitter method in emitter_llvmlite.py
whose cyclomatic complexity was ~119, over the #1826 ceiling of 60.  It is now
a `StmtEmitter` mixin:

  * `_emit_stmt_inner` is the dispatch over statement families;
  * `_emit_return_stmt`, `_emit_var_stmt`, `_emit_let_stmt`,
    `_emit_let_tuple_stmt` and `_emit_expr_stmt` are those families, moved
    verbatim;
  * `_emit_assign_stmt` is the assignment dispatch, with one method per target
    shape (ident, index, deref, field) and the shared value/index helpers it
    used to close over (`_emit_assign_value`, `_emit_assign_index_value`).

The moved branches are the same code in the same order, so the emitted IR is
byte-identical; the corpus replay against an origin/main worktree is the
evidence for that.
"""

from typing import Union

from llvmlite import ir

import ritz_ast as rast
from monomorph import resolve_alias_in
import array_rules
import index_rules
import let_rules
import ref_rules
from emitter.common import EmitError


class StmtEmitter:
    """Statement emission for `LLVMEmitter`; mixed in ahead of its other bases."""

    def _emit_stmt_inner(self, stmt: rast.Stmt) -> Union[bool, ir.Value, None]:
        """Emit a statement. Returns True if block terminated."""
        # Set debug location for source-level debugging
        self._set_debug_loc(stmt)
        self._reject_valueless_if(stmt)
        self._want_stmt_values(stmt)
        if isinstance(stmt, (rast.LetStmt, rast.VarStmt)):
            self._literal_into_slot(stmt.type, stmt.value)

        if isinstance(stmt, rast.ReturnStmt):
            return self._emit_return_stmt(stmt)

        elif isinstance(stmt, rast.VarStmt):
            return self._emit_var_stmt(stmt)

        elif isinstance(stmt, rast.LetStmt):
            return self._emit_let_stmt(stmt)

        elif isinstance(stmt, rast.LetTupleStmt):
            return self._emit_let_tuple_stmt(stmt)

        elif isinstance(stmt, rast.AssignStmt):
            return self._emit_assign_stmt(stmt)

        elif isinstance(stmt, rast.ExprStmt):
            return self._emit_expr_stmt(stmt)

        elif isinstance(stmt, rast.WhileStmt):
            # A loop body is never a value (LARB R69, AGAST #3796).
            self._reject_discarded_tail(stmt.body)
            return self._emit_while(stmt)

        elif isinstance(stmt, rast.ForStmt):
            self._reject_discarded_tail(stmt.body)
            return self._emit_for(stmt)

        elif isinstance(stmt, rast.AssertStmt):
            return self._emit_assert(stmt)

        elif isinstance(stmt, rast.BreakStmt):
            if not self.loop_stack:
                raise RuntimeError("break statement outside of loop")
            _, break_block = self.loop_stack[-1]
            self._drop_loop_scopes()
            self.builder.branch(break_block)
            return True  # Terminates this block

        elif isinstance(stmt, rast.ContinueStmt):
            if not self.loop_stack:
                raise RuntimeError("continue statement outside of loop")
            continue_block, _ = self.loop_stack[-1]
            self._drop_loop_scopes()
            self.builder.branch(continue_block)
            return True  # Terminates this block

        elif isinstance(stmt, rast.DeferStmt):
            self._register_defer(stmt)
            return False

        elif isinstance(stmt, rast.AsmStmt):
            return self._emit_asm(stmt)

        elif isinstance(stmt, rast.UnsafeBlock):
            return self._emit_unsafe_block(stmt)

        else:
            raise NotImplementedError(f"Statement: {type(stmt)}")

    def _emit_return_stmt(self, stmt: rast.ReturnStmt) -> bool:
        """Emit `return v`, or a bare `return` with drops (AGAST #1826)."""
        ret_type = self._fn_ret_type(self.current_fn)
        if stmt.value:
            # Check if we're returning a local variable - it should be moved, not dropped
            exclude_var = None
            if isinstance(stmt.value, rast.Ident):
                var_name = stmt.value.name
                if var_name in self.locals:
                    # This is a local variable being returned - treat as move
                    exclude_var = var_name

            # Expected Ritz type, used to resolve associated calls whose
            # type argument is only implied (`return Span.empty()`).
            if self.current_fn_def:
                self.expected_ritz_type = self.current_fn_def.ret_type
                self._literal_ctx_nodes = self._arith_context_nodes(stmt.value)

            if self._emit_large_lit_into(
                    stmt.value, self._sret_dest(self.current_fn, ret_type)):
                # AGAST #1741: the literal was built in the sret slot.
                self.expected_ritz_type = None
                self._emit_drop_for_all_scopes(exclude_var)
                self.builder.ret_void()
                self.has_returned = True
                return True
            else:
                val = self._emit_return_operand(stmt.value)
            self.expected_ritz_type = None
            ret_ritz = self.current_fn_def.ret_type if self.current_fn_def else None
            ret_span = getattr(stmt.value, 'span', None) or getattr(stmt, 'span', None)
            self._reject_enum_as_int(val, ret_type, ret_ritz, ret_span)
            self._reject_struct_as_int(val, ret_type, ret_ritz, stmt.value, ret_span)
            self._reject_another_struct_return(val, ret_type, getattr(stmt, 'span', None) or ret_span)
            self._check_return_narrowing(stmt.value, val, ret_type, ret_ritz)
            self._reject_pointer_into_float(val, ret_type, stmt.value)  # #4199
            val = self._convert_type(val, ret_type, stmt.value)
            # Emit drops for all scopes before return (excluding moved variable)
            self._emit_drop_for_all_scopes(exclude_var)
            self.builder.ret(val)
        else:
            # Emit drops for all scopes before return
            self._emit_drop_for_all_scopes()
            if ret_type == self.void:
                self.builder.ret_void()
            else:
                self.builder.ret(self._zero_constant(ret_type))
        self.has_returned = True
        return True

    def _emit_var_stmt(self, stmt: rast.VarStmt) -> None:
        """Emit `var` binding, declared or inferred type (AGAST #1826)."""
        ritz_type = stmt.type  # May be None if type is inferred
        # Get line number for debug info
        stmt_span = getattr(stmt, 'span', None)
        stmt_line = stmt_span.line if stmt_span else 1

        if stmt.type:
            ty = self._ritz_type_to_llvm(stmt.type)
            self.ritz_types[stmt.name] = stmt.type  # Store Ritz type for signedness
        elif stmt.value:
            # Infer from value - emit first to get LLVM type. A nested
            # constructor names its enum, as the untyped let's (#3045).
            nested_type = self._untyped_nested_ctor_type(stmt.value)
            val = self._emit_expr_with_expected_enum(
                stmt.value, self._let_annotation_enum(nested_type))
            ty = val.type
            # Also infer Ritz type for Drop tracking
            inferred_ritz_type = nested_type or self._infer_ritz_type(stmt.value, val)
            if inferred_ritz_type:
                ritz_type = inferred_ritz_type
                self.ritz_types[stmt.name] = ritz_type
            # Always allocate in entry block to prevent stack leaks in loops
            alloca = self._alloca_in_entry_block(ty, f"{stmt.name}.addr")
            # AGAST #1736: an sret call writes the new var in place.
            if not self._retarget_sret_result(val, alloca):
                self.builder.store(val, alloca)
            self._bind_var(stmt.name, alloca, ty)
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
            # LARB R49: a literal is not a `String`.
            if (stmt.type and isinstance(stmt.type, rast.NamedType)
                and stmt.type.name == 'String'
                and isinstance(stmt.value, rast.StringLit)):
                self._refuse_string_literal(stmt.value)
            # Special case: large array fill - initialize alloca directly with memset
            # This avoids loading/storing huge arrays which crashes LLVM SelectionDAG
            elif isinstance(stmt.value, rast.ArrayFill) and stmt.value.count > 64:
                self._emit_array_fill_to_alloca(stmt.value, alloca, ty, stmt.type)
            # AGAST #1741: a large struct literal is built in the new var.
            elif self._emit_large_lit_into(stmt.value, alloca):
                pass
            # Check if this is an enum variant constructor that needs type context
            elif self._is_enum_variant_call(stmt.value) and stmt.type and isinstance(stmt.type, rast.NamedType):
                # Use declared enum type to construct the correct variant.
                # A generic annotation (`Option<Foo>`) must resolve to its
                # specialization (`Option$Foo`) — the raw name is not a
                # registered enum and raised "Unknown enum type: Option"
                # (AGAST #1321, tests.ritz). Mirrors the AssignStmt path.
                target_enum = self._resolve_enum_type_name(stmt.type)
                if target_enum is None and stmt.type.args:
                    target_enum = self._ensure_builtin_generic_specialization(
                        stmt.type)
                if target_enum is None:
                    target_enum = stmt.type.name
                val = self._emit_enum_variant_with_type(stmt.value, target_enum)
                val = self._convert_type(val, ty)
                self.builder.store(val, alloca)
            else:
                # Set SIMD expected type context for var statements too
                if stmt.type and isinstance(stmt.type, rast.NamedType):
                    if stmt.type.name in ('v8i32', 'v4i64', 'v16i16', 'v32i8',
                                          'v4i32', 'v2i64', 'v8i16', 'v16i8'):
                        self.simd_expected_type = stmt.type
                # AGAST #1396: `var` carried no declared-type context, so
                # `var q: u32 = x + 1` kept the i64 round-trip that `let`
                # no longer has. Saved and restored rather than cleared,
                # so a `var` nested inside a typed initialiser does not
                # destroy the enclosing context.
                saved_expected = getattr(self, 'expected_ritz_type', None)
                saved_ctx = getattr(self, '_literal_ctx_nodes', set())
                if stmt.type:
                    self.expected_ritz_type = stmt.type
                    self._literal_ctx_nodes = self._arith_context_nodes(stmt.value)
                saved_float = self._enter_float_tails(stmt.type, stmt.value)
                try:
                    val = self._emit_expr(stmt.value)
                finally:
                    self.expected_ritz_type = saved_expected
                    self._literal_ctx_nodes = saved_ctx
                    self._leave_float_tails(saved_float)
                self.simd_expected_type = None  # Clear SIMD context
                if stmt.type:
                    self._check_initialiser_has_value(stmt, val)
                    self._reject_enum_as_int(val, ty, stmt.type,
                                             getattr(stmt, 'span', None))
                    self._reject_another_struct(stmt, val, ty)
                    self._reject_pointer_into_float(val, ty, stmt.value)
                if stmt.type:
                    self._check_implicit_narrowing(stmt, val.type, ty, val)
                # AGAST #1736: an sret call writes the new var in place
                # (no first-class %T, which clang -O2 lowers per byte).
                if not self._retarget_sret_result(val, alloca):
                    val = self._convert_type(val, ty, stmt.value)
                    self.builder.store(val, alloca)
        self._bind_var(stmt.name, alloca, ty)
        # Register for Drop if type is known and implements Drop
        if ritz_type:
            self._register_drop_variable(stmt.name, alloca, ritz_type)
            # Mark as initialized if we just assigned a value
            if stmt.value:
                self._mark_drop_variable_initialized(alloca)
            else:
                self._start_unwritten(stmt, alloca)
        # Emit debug info for variable (requires ritz_type for proper type info)
        if ritz_type:
            self._emit_dbg_declare(alloca, stmt.name, ritz_type, stmt_line)
        return None

    def _emit_let_stmt(self, stmt: rast.LetStmt) -> None:
        """Emit `let` binding, declared or inferred type (AGAST #1826)."""
        if self._emit_large_let_lit(stmt):
            return None
        nested_type = None
        # LARB R49: a literal is not a `String`.
        if (stmt.type and isinstance(stmt.type, rast.NamedType)
            and stmt.type.name == 'String'
            and isinstance(stmt.value, rast.StringLit)):
            self._refuse_string_literal(stmt.value)
        else:
            # Set expected type context for SIMD type inference (e.g., v8i32 vs v4i32)
            if stmt.type and isinstance(stmt.type, rast.NamedType):
                if stmt.type.name in ('v8i32', 'v4i64', 'v16i16', 'v32i8',
                                      'v4i32', 'v2i64', 'v8i16', 'v16i8'):
                    self.simd_expected_type = stmt.type
            # Restored, not cleared: this `let` may sit in an arm whose
            # tail is still to land in the enclosing slot.
            saved_let_expected = self.expected_ritz_type
            # And so is the context set: the arm's literal tail still needs
            # its mark after this `let` (AGAST #1445).
            saved_let_ctx = getattr(self, '_literal_ctx_nodes', set())
            self.expected_ritz_type = stmt.type
            self._literal_ctx_nodes = self._arith_context_nodes(stmt.value)
            # AGAST #1964: variant names are global (`Some` -> whichever
            # Option specialization registered last), so with Option<f32>
            # and Option<f64> both in the module `let o: Option<f64> =
            # Some(2.5)` was built as Option$f32. Resolve the annotation
            # to its specialization and emit through the expected-enum
            # path, which also threads it into if / match / block tails.
            let_enum = self._let_annotation_enum(stmt.type)
            # AGAST #3045: an untyped `let o = Some(Some(5))` has no
            # annotation, so the nesting names the enum.
            nested_type = (self._untyped_nested_ctor_type(stmt.value)
                           if stmt.type is None else None)
            if nested_type is not None:
                let_enum = self._let_annotation_enum(nested_type)
            saved_float = self._enter_float_tails(stmt.type, stmt.value)
            try:
                val = self._emit_expr_with_expected_enum(stmt.value, let_enum)
            finally:
                self._leave_float_tails(saved_float)
            self.simd_expected_type = None  # Clear SIMD context
            self.expected_ritz_type = saved_let_expected
            self._literal_ctx_nodes = saved_let_ctx
        if stmt.type:
            self._check_initialiser_has_value(stmt, val)
            # Use declared type and convert value if needed
            declared_ty = self._ritz_type_to_llvm(stmt.type)
            src_ty = val.type  # before _convert_type hides any narrowing
            src_val = val
            self._reject_enum_as_int(val, declared_ty, stmt.type,
                                     getattr(stmt, 'span', None))
            self._reject_another_struct(stmt, val, declared_ty)
            self._reject_pointer_into_float(val, declared_ty, stmt.value)
            val = self._convert_type(val, declared_ty, stmt.value)
            self._check_implicit_narrowing(stmt, src_ty, declared_ty, src_val)
            self._check_let_annotation(stmt, val, declared_ty)
            self._forget_int_merge(src_val)
            self._bind_let(stmt.name, val, declared_ty)
            self.ritz_types[stmt.name] = stmt.type  # Store Ritz type for signedness
            self._register_let_drop(stmt.name, val, stmt.type)
        else:
            # Infer Ritz type from expression for signedness tracking
            inferred_ritz_type = nested_type or self._infer_ritz_type(stmt.value, val)
            self._forget_int_merge(val)
            self._bind_let(stmt.name, val, val.type)
            if inferred_ritz_type:
                self.ritz_types[stmt.name] = inferred_ritz_type
            self._register_let_drop(stmt.name, val, inferred_ritz_type)
        return None

    def _emit_let_tuple_stmt(self, stmt: rast.LetTupleStmt) -> None:
        """Emit `let (a, b, ...) = expr` destructuring (AGAST #1826)."""
        # Tuple destructuring: let (a, b, c) = expr
        # Emit the tuple expression
        tuple_val = self._emit_expr(stmt.value)

        # LARB R67 (AGAST #3499): a `(…)` pattern destructures tuples
        # only.  A tuple is a literal struct; a named struct is identified,
        # and binding its fields by position would rebind them silently
        # when one is added.  Refused at the `(`, before the arity check
        # (3 fields, 2 names was an unlocated ValueError).
        struct = (self._get_struct_name_from_type(tuple_val.type)
                  if isinstance(tuple_val.type, ir.IdentifiedStructType) else None)
        if struct is not None:
            raise EmitError(let_rules.tuple_pattern_on_struct(struct.split('$', 1)[0]),
                            stmt.paren_span or getattr(stmt, 'span', None))
        if not isinstance(tuple_val.type, ir.BaseStructType):
            raise self._err(f"Cannot destructure non-tuple type: {tuple_val.type}")

        elements = tuple_val.type.elements
        if len(stmt.names) != len(elements):
            raise self._err(f"Tuple destructuring mismatch: expected {len(elements)} "
                           f"elements, got {len(stmt.names)} names")

        # AGAST #3192: each name takes its element's Ritz type, as a
        # `let` takes its value's.  Without it a `u8` element (or the
        # `**u8` of `(*T, i32)` at T = *u8) was a bare LLVM `i8`, which
        # widens signed: 200 read as -56.
        tuple_ritz = self._infer_ritz_type(stmt.value, tuple_val)
        elem_ritz = (tuple_ritz.elements if isinstance(tuple_ritz, rast.TupleType)
                     and len(tuple_ritz.elements) == len(elements) else None)
        for i, name in enumerate(stmt.names):
            elem_val = self.builder.extract_value(tuple_val, i)
            self._bind_let(name, elem_val, elem_val.type)
            # Popped when unknown: a stale type from an earlier binding
            # of the name must not survive the rebind.
            if elem_ritz is not None:
                self.ritz_types[name] = elem_ritz[i]
            else:
                self.ritz_types.pop(name, None)
            # AGAST #2282: each name owns its element and drops it at
            # scope end, as a `let` does (§13.6); the source moved into
            # the names (the move checker marked it, _note_move above).
            self._register_let_drop(name, elem_val,
                                    elem_ritz[i] if elem_ritz is not None else None)
        return None

    def _emit_assign_stmt(self, stmt: rast.AssignStmt) -> None:
        """Emit assignment, dispatching on target shape (AGAST #1826)."""
        self._check_let_write(stmt.target)
        # `m[k] = v` / `m[k] op= x` on a struct (§7.8, AGAST #1635).
        if isinstance(stmt.target, rast.Index) and self._emit_struct_index_assign(stmt):
            return None
        # A store at or inside a field reached through `DerefMut` (§7.7).
        if self._emit_deref_assign(stmt):
            return None
        # `m[k].f = x` needs `IndexMut`: refuse it with the use spelled out.
        root = stmt.target
        while isinstance(root, rast.Field):
            root = root.expr
        if root is not stmt.target and isinstance(root, rast.Index):
            self._struct_index(root, "m[k].f = x")
        # `x = Some(v)` must build the variant for the *target's* enum.
        # Variant names are global (`Some` -> whichever Option was
        # specialized last), so without the target type an assignment to
        # `Option<CmapTable>` could be handed an `Option<Glyph>`.
        target_ritz_type = None
        if self._is_enum_variant_call(stmt.value):
            target_ritz_type = self._infer_ritz_type(stmt.target)
            while isinstance(target_ritz_type, (rast.PtrType, rast.RefType)):
                target_ritz_type = target_ritz_type.inner
        target_enum = None
        if isinstance(target_ritz_type, rast.NamedType):
            target_enum = self._resolve_enum_type_name(target_ritz_type)
            if target_enum is None and target_ritz_type.args:
                target_enum = self._ensure_builtin_generic_specialization(
                    target_ritz_type)
        target_slot = self._infer_ritz_type(stmt.target)
        self._literal_into_slot(target_slot, stmt.value)
        if isinstance(stmt.target, rast.Ident):
            self._emit_assign_to_ident(stmt, target_enum, target_slot)
        elif isinstance(stmt.target, rast.Index):
            self._emit_assign_to_index(stmt, target_enum, target_slot)
        elif isinstance(stmt.target, rast.UnaryOp) and stmt.target.op == '*':
            self._emit_assign_to_deref(stmt, target_enum, target_slot)
        elif isinstance(stmt.target, rast.Field):
            self._emit_assign_to_field(stmt, target_enum, target_slot)
        else:
            raise NotImplementedError(f"Assignment to: {type(stmt.target)}")
        return None

    def _emit_assign_value(self, stmt: rast.AssignStmt, target_enum,
                           target_slot) -> ir.Value:
        """Emit the assignment's value, in the target's enum/slot context."""
        if target_enum is not None:
            v = self._emit_enum_variant_with_type(stmt.value, target_enum)
        else:
            with self._int_slot_context(target_slot, stmt.value):
                v = self._emit_into_array_slot(stmt.value, self._assign_slot(stmt))
        self._reject_enum_assign(stmt.target, v, getattr(stmt, 'span', None))
        self._expect_assign_narrowing(stmt.target, stmt.value, v,
                                      getattr(stmt, 'lowered_let', None),
                                      getattr(stmt, 'span', None),
                                      getattr(stmt, 'lowered_return', None))
        return v

    def _emit_assign_index_value(self, stmt: rast.AssignStmt) -> ir.Value:
        """The index of an assignment's `a[i]` target (LARB R61 order)."""
        return self._emit_index_value(stmt.target.index)

    def _emit_assign_to_ident(self, stmt: rast.AssignStmt, target_enum,
                              target_slot) -> None:
        """Emit `x = v` for a name target (AGAST #1826)."""
        # LARB R61 (§13.6): the place, then `v`.  A name has nothing to
        # evaluate, so `v` is emitted first.
        val = self._emit_assign_value(stmt, target_enum, target_slot)
        name = stmt.target.name
        # A `let` (#2025 slot or SSA value) was rejected by
        # _check_let_write above (AGAST #2031).
        if name in self.locals:
            alloca, ty = self.locals[name]
            val = self._convert_type(val, ty, stmt.value)
            slot_type = (self.typed.type_of(stmt.target)
                         if self.typed is not None else None)
            if self._lent_arg(stmt.target) is not None and slot_type is not None:
                # `h = v` on a `h:& T` stores to the caller's T (R58).
                self._drop_old_through_ref(alloca, slot_type)
            self._store_binding(name, alloca, val)
        elif name in self.globals:
            gvar, ty = self.globals[name]
            val = self._convert_type(val, ty, stmt.value)
            self.builder.store(val, gvar)
        else:
            raise self._err(f"Unknown variable: {name}")

    def _emit_assign_to_index(self, stmt: rast.AssignStmt, target_enum,
                              target_slot) -> None:
        """Emit `a[i] = v`, each base shape addressed first (AGAST #1826)."""
        # Assignment to indexed location: arr[i] = val
        through = self._index_through(stmt.target)
        if through is not None:
            ptr = self._emit_expr(through.operand)
            val = self._emit_assign_value(stmt, target_enum, target_slot)
            # `(*p)[i] = b` over an array is `p[i] = b`: element i, not the
            # whole array, as the general case below says (#2331).  Located
            # at the `*`, as `(*p).f = v` is.
            if (isinstance(val.type, ir.ArrayType)
                    and not isinstance(ptr.type.pointee, ir.ArrayType)
                    and isinstance(self._infer_ritz_type(stmt.target.expr), rast.ArrayType)):
                base = stmt.target.expr
                while isinstance(base, rast.Grouped):
                    base = base.expr
                raise EmitError(array_rules.ELEMENT_NOT_ARRAY, base.span)
            self.builder.store(self._convert_type(val, ptr.type.pointee, stmt.value), ptr)
            return None
        # Each route addresses the base first, then emits the index
        # (index_of), then v (emit_val): LARB R61.
        # Special handling for identifiers that are arrays
        if isinstance(stmt.target.expr, rast.Ident):
            name = stmt.target.expr.name
            if name in self.locals:
                alloca, ty = self.locals[name]
                if isinstance(ty, ir.ArrayType):
                    # Array type - use two-level GEP [0, index] on the alloca
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(alloca, [zero, self._emit_assign_index_value(stmt)])
                    val = self._convert_type(
                        self._emit_assign_value(stmt, target_enum, target_slot), ty.element)
                    self._drop_old_element(stmt.target, ptr)
                    self.builder.store(val, ptr)
                    return None
            elif name in self.globals:
                gvar, ty = self.globals[name]
                if isinstance(ty, ir.ArrayType):
                    # Global array - use two-level GEP [0, index] on the global
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(gvar, [zero, self._emit_assign_index_value(stmt)])
                    val = self._convert_type(
                        self._emit_assign_value(stmt, target_enum, target_slot), ty.element)
                    self.builder.store(val, ptr)
                    return None

        # Special handling for struct field that is an array (e.g., buf.data[0] = val)
        # `mk().q[i] = v`, `q` a pointer: stored through, below (#2518).
        if (isinstance(stmt.target.expr, rast.Field)
                and not self._through_temp_pointer(stmt.target.expr)):
            field_addr = self._emit_lvalue_addr(stmt.target.expr)
            if isinstance(field_addr.type, ir.PointerType):
                pointee = field_addr.type.pointee
                if isinstance(pointee, ir.ArrayType):
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(field_addr, [zero, self._emit_assign_index_value(stmt)])
                    val = self._convert_type(
                        self._emit_assign_value(stmt, target_enum, target_slot), pointee.element)
                    self._drop_old_element(stmt.target, ptr)
                    self.builder.store(val, ptr)
                    return None

        # Special handling for nested array indexing (e.g., arr[i][j] = val)
        if isinstance(stmt.target.expr, rast.Index):
            inner_addr = self._emit_lvalue_addr(stmt.target.expr)
            if isinstance(inner_addr.type, ir.PointerType):
                pointee = inner_addr.type.pointee
                if isinstance(pointee, ir.ArrayType):
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(inner_addr, [zero, self._emit_assign_index_value(stmt)])
                    val = self._convert_type(
                        self._emit_assign_value(stmt, target_enum, target_slot), pointee.element)
                    self._drop_old_element(stmt.target, ptr)
                    self.builder.store(val, ptr)
                    return None

        # Vec<T> element assignment: `v[i] = x` writes into the Vec's
        # heap buffer.
        vec_addr = self._try_vec_lvalue_base(stmt.target.expr)
        if vec_addr is not None:
            zero = ir.Constant(self.i32, 0)
            data_ptr = self.builder.load(
                self.builder.gep(vec_addr, [zero, ir.Constant(self.i32, 0)]))
            idx = self._emit_assign_index_value(stmt)
            if idx.type != self.i64:
                idx = self._convert_type(idx, self.i64)
            ptr = self.builder.gep(data_ptr, [idx])
            val = self._convert_type(
                self._emit_assign_value(stmt, target_enum, target_slot),
                data_ptr.type.pointee)
            self.builder.store(val, ptr)
            return None

        # General case - pointer indexing
        base = self._emit_expr(stmt.target.expr)
        index = self._emit_assign_index_value(stmt)
        if (isinstance(base.type, ir.ArrayType)
                and isinstance(stmt.target.expr, (rast.Call, rast.MethodCall))):
            # `mka()[1] = v`: an element of a call's array (AGAST #3234).
            raise EmitError(ref_rules.STORE_INTO_TEMP, stmt.target.span)
        val = self._emit_assign_value(stmt, target_enum, target_slot)
        if isinstance(base.type, ir.PointerType) and isinstance(base.type.pointee, ir.ArrayType):
            # AGAST #2330, LARB R9: element i at stride T, as the read.  This
            # took GEP [i], at stride `[N]T`, so a scalar didn't fit and a
            # whole `[N]T` was stored over the next row.
            elem = base.type.pointee.element
            if isinstance(val.type, ir.ArrayType) and not isinstance(elem, ir.ArrayType):
                raise EmitError(array_rules.ELEMENT_NOT_ARRAY, stmt.span)
            ptr = self.builder.gep(base, [ir.Constant(self.i32, 0), index])
            self.builder.store(self._convert_type(val, elem, stmt.value), ptr)
        elif isinstance(base.type, ir.PointerType):
            ptr = self.builder.gep(base, [index])
            val = self._convert_type(val, base.type.pointee)
            self.builder.store(val, ptr)
        else:
            # AGAST #3754: `(n + 1)[0] = v`, `(n as i64)[0] = v`: an
            # integer base has nothing to index, as `n[0] = v` (#2886),
            # in the same words and at the `[`.  This raised a bare
            # ValueError ("Cannot index type: i64") with a traceback.
            ty = self._infer_ritz_type(stmt.target.expr)
            if ty is not None:
                ty = resolve_alias_in(ty, self.type_aliases)
            if isinstance(ty, rast.NamedType) and ty.name in index_rules.SCALARS:
                raise EmitError(index_rules.needs_index(ty.name),
                                stmt.target.bracket or stmt.target.span)
            raise self._err(f"Cannot index type: {base.type}")
        return None

    def _emit_assign_to_deref(self, stmt: rast.AssignStmt, target_enum,
                              target_slot) -> None:
        """Emit `*p = v` (AGAST #1826)."""
        # Assignment to dereferenced pointer: *ptr = val
        # AGAST #2972: on a `h:& T` borrow of a non-pointer T, `h`
        # reads as the referent, so `*h` is `h` (the read arm, #2045)
        # and `*h = v` stores to the caller's T, as `h = v` does.
        # An `a:& [N]T` is the exception, as on ritz1 (#2290).
        slot = self._borrow_referent_slot(stmt.target.operand)
        if slot is not None and isinstance(slot.type.pointee, ir.ArrayType):
            raise EmitError(array_rules.BORROW_DEREF_STORE, stmt.target.span)
        ptr = slot if slot is not None else self._emit_expr(stmt.target.operand)
        if not isinstance(ptr.type, ir.PointerType):
            raise EmitError(array_rules.NOT_A_POINTER, stmt.target.span)  # AGAST #2885
        val = self._convert_type(
            self._emit_assign_value(stmt, target_enum, target_slot),
            ptr.type.pointee, stmt.value)
        if self._store_reach(stmt.target) == 'ref':
            slot_type = self.typed.type_of(stmt.target)
            if slot_type is not None:
                self._drop_old_through_ref(ptr, slot_type)
        self.builder.store(val, ptr)
        return None

    def _emit_assign_to_field(self, stmt: rast.AssignStmt, target_enum,
                              target_slot) -> None:
        """Emit `obj.field = v` (AGAST #1826)."""
        # Assignment to struct field: obj.field = val
        # First, try to get the value of the expression
        # If it's already a pointer to a struct, use it directly
        # Otherwise, try to get its address. Struct storage (a local,
        # global or field chain) is addressed directly: evaluating it
        # as a value loads the whole struct (AGAST #1914).
        # `mk().p.f = v`, `p` a pointer: stored through it (#2518).
        # Read `p` once, before any route tries for an address.
        struct_val = (self._emit_expr(stmt.target.expr)
                      if self._through_temp_pointer(stmt.target.expr)
                      else self._struct_place_addr(stmt.target.expr))
        # `m[k].f = x` on a struct's `[]`: the element `index_mut` gives
        # (§7.8), never a read of it first.
        place = (self._struct_index(stmt.target.expr, "m[k].f = x")
                 if isinstance(stmt.target.expr, rast.Index) else None)
        if place is not None:
            struct_val = self._emit_expr(place.operand)
        if struct_val is None and self._call_rooted_field(stmt.target.expr):
            # AGAST #2879: `sp(@s).inner.y = v`: address the field
            # through the call's pointer.  Reading `sp(@s).inner` as a
            # value, then addressing it, ran the call twice.
            struct_val = self._emit_lvalue_addr(stmt.target.expr)
        if struct_val is None and self._names_struct_value(stmt.target.expr):
            # `ps[idx(0)].inn.v = v`: address the struct.  Reading it
            # as a value, then addressing it, ran idx() twice.
            struct_val = self._emit_lvalue_addr(stmt.target.expr)
        if struct_val is None:
            struct_val = self._emit_expr(stmt.target.expr)

        if isinstance(struct_val.type, ir.PointerType):
            # Expression evaluates to a pointer: through every level
            # of it to the struct (§5.4, #2398).
            struct_ptr = self._through_pointers(struct_val)
        elif isinstance(struct_val.type, ir.BaseStructType):
            # Value-type struct - need to get address from lvalue
            struct_ptr = self._emit_lvalue_addr(stmt.target.expr)
        else:
            raise self._err(f"Invalid type for field assignment: {struct_val.type}")
        # The place is addressed: now `v` (LARB R61, AGAST #1740).
        val = self._emit_assign_value(stmt, target_enum, target_slot)
        pointee_type = struct_ptr.type.pointee
        if self._assign_tuple_element(stmt, struct_ptr, val):
            pass
        elif isinstance(pointee_type, ir.BaseStructType):
            struct_name = self._get_struct_name_from_type(pointee_type)
            if not struct_name:
                raise self._err("Cannot determine struct type for field assignment")
            idx = self._get_struct_field_index(struct_name, stmt.target.field)
            _, field_type = self.struct_fields[struct_name][idx]
            field_llvm_type = self._ritz_type_to_llvm(field_type)
            field_ptr = self.builder.gep(struct_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
            val = self._convert_type(val, field_llvm_type, stmt.value)
            self._drop_old_field(stmt.target, field_ptr, field_type)
            self.builder.store(val, field_ptr)
        else:
            raise self._err(f"Cannot assign field on non-struct pointer: {pointee_type}")
        return None

    def _emit_expr_stmt(self, stmt: rast.ExprStmt) -> Union[bool, ir.Value, None]:
        """Emit an expression statement whose value is discarded (#2137)."""
        # A statement's value is discarded (AGAST #2137), and so are a
        # statement match/if's arm values (LARB R69, AGAST #3796).
        self._reject_discarded_tail(stmt.expr)
        # Check if this is an If expression used as statement
        if isinstance(stmt.expr, rast.If):
            return self._emit_if(stmt.expr, discard=True)
        # A bare "{x}" statement is a plain StringLit, not a print
        # (AGAST #2102): only print / eprint interpolate.
        return self._emit_expr(stmt.expr)
