"""
Pattern matching and cast emission mixin for the LLVM emitter.

Contains: _emit_match, _emit_union_match, _emit_enum_match, _emit_integer_match,
          _emit_try_op, _emit_cast, _emit_cast_to_union, _emit_cast_from_union,
          _emit_cast_to_dyn, _emit_cast_to_dyn_ref
"""

from typing import Optional, List, Tuple
from llvmlite import ir
import ritz_ast as rast


class PatternEmitterMixin:
    """Mixin providing pattern matching and cast emission methods for LLVMEmitter."""

    def _emit_match(self, expr: rast.Match) -> ir.Value:
        """Emit a match expression.

        For union types with TypePattern arms, generates a switch on the tag.
        For enum types with VariantPattern arms, generates a switch on the tag.
        Each arm extracts the appropriate type from the union/enum data.
        """
        # Emit the match expression
        match_val = self._emit_expr(expr.expr)

        # Check if matching on a union type
        union_name = self._get_union_name_from_expr(expr.expr)
        if union_name and union_name in self.union_types:
            return self._emit_union_match(expr, match_val, union_name)

        # Check if matching on an enum type
        enum_name = self._get_enum_name_from_expr(expr.expr)
        if enum_name and enum_name in self.enum_types:
            return self._emit_enum_match(expr, match_val, enum_name)

        # Check if matching on an integer type
        if isinstance(match_val.type, ir.IntType):
            return self._emit_integer_match(expr, match_val)

        raise NotImplementedError(f"Match on type {match_val.type} not yet supported")


    def _emit_union_match(self, expr: rast.Match, union_val: ir.Value, union_name: str) -> ir.Value:
        """Emit a match on a union type with TypePattern arms."""
        union_type, variants = self.union_types[union_name]

        # Store union to memory so we can extract tag and data
        union_alloca = self.builder.alloca(union_type, name="match.union")
        self.builder.store(union_val, union_alloca)

        # Load the tag
        tag_ptr = self.builder.gep(union_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        tag = self.builder.load(tag_ptr)

        # Create blocks for each arm and the merge block
        arm_blocks = []
        for i, arm in enumerate(expr.arms):
            block = self.current_fn.append_basic_block(f"match.arm.{i}")
            arm_blocks.append(block)

        merge_block = self.current_fn.append_basic_block("match.merge")

        # Create an unreachable default block (should never be reached in well-typed code)
        unreachable_block = self.current_fn.append_basic_block("match.unreachable")
        default_block = unreachable_block

        # Build switch instruction
        switch = self.builder.switch(tag, default_block)

        # Add cases for each TypePattern arm
        arm_values = []
        arm_exit_blocks = []

        for i, (arm, arm_block) in enumerate(zip(expr.arms, arm_blocks)):
            pattern = arm.pattern

            if isinstance(pattern, rast.TypePattern):
                # Find the tag for this type
                tag_val = self._get_union_tag_for_type(union_name, pattern.type)
                switch.add_case(ir.Constant(self.i8, tag_val), arm_block)
            elif isinstance(pattern, rast.WildcardPattern):
                # Wildcard matches any remaining - becomes default
                switch.default = arm_block
            else:
                raise NotImplementedError(f"Pattern type {type(pattern)} not supported in union match")

        # Emit the unreachable block
        self.builder.position_at_end(unreachable_block)
        self.builder.unreachable()

        # Emit each arm body
        for i, (arm, arm_block) in enumerate(zip(expr.arms, arm_blocks)):
            self.builder.position_at_end(arm_block)

            # Emit the arm body (which may include casts like `x as i32`)
            arm_val = self._emit_expr(arm.body)
            arm_values.append(arm_val)

            # Remember which block we're in after emitting the body
            if not self.builder.block.is_terminated:
                arm_exit_blocks.append(self.builder.block)
                self.builder.branch(merge_block)
            else:
                arm_exit_blocks.append(None)

        # Position at merge block
        self.builder.position_at_end(merge_block)

        # Create phi node for the result if arms have values
        if arm_values and arm_exit_blocks:
            # Filter out terminated blocks (those that returned)
            incoming = [(val, block) for val, block in zip(arm_values, arm_exit_blocks) if block is not None]
            if incoming:
                # Find the common type for all arms
                # For integer types, use the widest type
                common_type = incoming[0][0].type
                for val, _ in incoming[1:]:
                    if isinstance(val.type, ir.IntType) and isinstance(common_type, ir.IntType):
                        if val.type.width > common_type.width:
                            common_type = val.type

                # Create phi node with the common type
                phi = self.builder.phi(common_type)
                for val, block in incoming:
                    # Convert value to common type if needed
                    if val.type != common_type:
                        val = self._convert_type(val, common_type)
                    phi.add_incoming(val, block)
                return phi

        # Return a dummy value if no arms produce values
        return ir.Constant(self.i32, 0)


    def _emit_enum_match(self, expr: rast.Match, enum_val: ir.Value, enum_name: str) -> ir.Value:
        """Emit a match on an enum type with VariantPattern arms.

        For Option<i32> match:
            match opt
                Some(x) -> x + 1
                None -> 0

        Generates:
            1. Store enum value to memory
            2. Load tag byte
            3. Switch on tag to arm blocks
            4. In each arm, extract payload if needed and bind to pattern variables
            5. Evaluate arm body
            6. Jump to merge block
            7. Phi node for result
        """
        enum_type, variants = self.enum_types[enum_name]

        # Store enum to memory so we can extract tag and data
        enum_alloca = self.builder.alloca(enum_type, name="match.enum")
        self.builder.store(enum_val, enum_alloca)

        # Load the tag
        tag_ptr = self.builder.gep(enum_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        tag = self.builder.load(tag_ptr)

        # Create blocks for each arm and the merge block
        arm_blocks = []
        for i, arm in enumerate(expr.arms):
            block = self.current_fn.append_basic_block(f"match.arm.{i}")
            arm_blocks.append(block)

        merge_block = self.current_fn.append_basic_block("match.merge")

        # Create an unreachable default block (should never be reached in well-typed code)
        unreachable_block = self.current_fn.append_basic_block("match.unreachable")
        default_block = unreachable_block

        # Build switch instruction
        switch = self.builder.switch(tag, default_block)

        # Add cases for each VariantPattern arm
        for i, (arm, arm_block) in enumerate(zip(expr.arms, arm_blocks)):
            pattern = arm.pattern

            if isinstance(pattern, rast.VariantPattern):
                # Find the tag for this variant
                tag_val = self._get_enum_variant_tag(enum_name, pattern.name)
                switch.add_case(ir.Constant(self.i8, tag_val), arm_block)
            elif isinstance(pattern, rast.IdentPattern):
                # IdentPattern with a variant name (e.g., just `None` without parens)
                if pattern.name in self.variant_to_enum:
                    tag_val = self._get_enum_variant_tag(enum_name, pattern.name)
                    switch.add_case(ir.Constant(self.i8, tag_val), arm_block)
                else:
                    # This is a catch-all binding - becomes default
                    switch.default = arm_block
            elif isinstance(pattern, rast.WildcardPattern):
                # Wildcard matches any remaining - becomes default
                switch.default = arm_block
            else:
                raise NotImplementedError(f"Pattern type {type(pattern)} not supported in enum match")

        # Emit the unreachable block
        self.builder.position_at_end(unreachable_block)
        self.builder.unreachable()

        # Emit each arm body
        arm_values = []
        arm_exit_blocks = []

        for i, (arm, arm_block) in enumerate(zip(expr.arms, arm_blocks)):
            self.builder.position_at_end(arm_block)
            pattern = arm.pattern

            # Bind pattern variables if this is a VariantPattern with fields
            if isinstance(pattern, rast.VariantPattern) and pattern.fields:
                variant = self._get_enum_variant(enum_name, pattern.name)

                # Get pointer to data buffer (index depends on alignment padding)
                data_index = self._get_enum_data_index(enum_name)
                data_ptr = self.builder.gep(enum_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, data_index)])

                # Extract and bind each field
                offset = 0
                for j, (field_pattern, field_type) in enumerate(zip(pattern.fields, variant.fields)):
                    llvm_field_type = self._ritz_type_to_llvm(field_type)

                    # Cast data buffer to pointer to field type at offset
                    field_ptr = self.builder.bitcast(
                        self.builder.gep(data_ptr, [ir.Constant(self.i32, offset)]),
                        ir.PointerType(llvm_field_type)
                    )
                    field_val = self.builder.load(field_ptr)

                    # Bind the field value to the pattern variable
                    if isinstance(field_pattern, rast.IdentPattern):
                        # Store in params so it can be used in the arm body
                        self.params[field_pattern.name] = (field_val, llvm_field_type)
                    # Wildcard patterns just discard the value

                    offset += self._type_size_bytes(llvm_field_type)

            # Emit the arm body
            arm_val = self._emit_expr(arm.body)

            # Remember which block we're in after emitting the body
            if not self.builder.block.is_terminated:
                arm_exit_blocks.append(self.builder.block)
                arm_values.append(arm_val)
                self.builder.branch(merge_block)
            else:
                arm_exit_blocks.append(None)

            # Clean up bound variables
            if isinstance(pattern, rast.VariantPattern) and pattern.fields:
                for field_pattern in pattern.fields:
                    if isinstance(field_pattern, rast.IdentPattern):
                        del self.params[field_pattern.name]

        # Position at merge block
        self.builder.position_at_end(merge_block)

        # Create phi node for the result if arms have values
        if arm_values and arm_exit_blocks:
            # Filter out terminated blocks (those that returned)
            incoming = [(val, block) for val, block in zip(arm_values, arm_exit_blocks) if block is not None]
            if incoming:
                # All values should have the same type (or be convertible)
                # For now assume they're all the same type
                phi = self.builder.phi(incoming[0][0].type)
                for val, block in incoming:
                    phi.add_incoming(val, block)
                return phi

        # Return a dummy value if no arms produce values
        return ir.Constant(self.i32, 0)


    def _emit_integer_match(self, expr: rast.Match, match_val: ir.Value) -> ir.Value:
        """Emit a match on an integer type with literal or wildcard patterns.

        match x
            0 => "zero"
            1 => "one"
            _ => "other"

        Generates a switch instruction with cases for each literal pattern
        and a default case for wildcard/identifier patterns.
        """
        int_type = match_val.type

        # Create blocks for each arm and the merge block
        arm_blocks = []
        for i, arm in enumerate(expr.arms):
            block = self.current_fn.append_basic_block(f"match.arm.{i}")
            arm_blocks.append(block)

        merge_block = self.current_fn.append_basic_block("match.merge")

        # Find the default arm (wildcard or catch-all identifier that's not a constant)
        default_block = None
        default_arm_idx = None
        for i, arm in enumerate(expr.arms):
            if isinstance(arm.pattern, rast.WildcardPattern):
                default_block = arm_blocks[i]
                default_arm_idx = i
                break
            elif isinstance(arm.pattern, rast.IdentPattern):
                # IdentPattern is a catch-all ONLY if it's not a constant reference
                if arm.pattern.name not in self.constants:
                    default_block = arm_blocks[i]
                    default_arm_idx = i
                    break

        # If no default, create an unreachable block
        if default_block is None:
            unreachable_block = self.current_fn.append_basic_block("match.unreachable")
            default_block = unreachable_block

        # Build switch instruction
        switch = self.builder.switch(match_val, default_block)

        # Add cases for each literal pattern
        for i, (arm, arm_block) in enumerate(zip(expr.arms, arm_blocks)):
            pattern = arm.pattern

            if isinstance(pattern, rast.LitPattern):
                # Get the literal value
                lit_val = pattern.value
                if isinstance(lit_val, int):
                    case_val = ir.Constant(int_type, lit_val)
                    switch.add_case(case_val, arm_block)
                elif isinstance(lit_val, str) and len(lit_val) == 1:
                    # Character literal
                    case_val = ir.Constant(int_type, ord(lit_val))
                    switch.add_case(case_val, arm_block)
                else:
                    raise NotImplementedError(f"Literal pattern type not supported: {type(lit_val)}")
            elif isinstance(pattern, rast.IdentPattern):
                # Check if this is a constant reference
                if pattern.name in self.constants:
                    # Constants are stored as (value, type) tuples
                    val, ty = self.constants[pattern.name]
                    if isinstance(ty, ir.IntType):
                        # Create LLVM constant with the match value's type
                        case_val = ir.Constant(int_type, val)
                        switch.add_case(case_val, arm_block)
                # Otherwise it's a catch-all (handled as default above)
            # WildcardPattern is handled as default above

        # Emit the unreachable block if we created one
        if default_arm_idx is None:
            self.builder.position_at_end(default_block)
            self.builder.unreachable()

        # Emit each arm body
        arm_values = []
        arm_exit_blocks = []

        for i, (arm, arm_block) in enumerate(zip(expr.arms, arm_blocks)):
            self.builder.position_at_end(arm_block)
            pattern = arm.pattern

            # Bind identifier pattern to the match value
            if isinstance(pattern, rast.IdentPattern) and pattern.name not in self.constants:
                # Bind the match value to the pattern name for use in the arm body
                self.params[pattern.name] = (match_val, int_type)

            # Emit the arm body
            arm_val = self._emit_expr(arm.body)
            arm_values.append(arm_val)

            # Check if the arm already terminated (e.g., with return)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_block)
                arm_exit_blocks.append(self.builder.block)
            else:
                arm_exit_blocks.append(None)

            # Clean up bound pattern variable
            if isinstance(pattern, rast.IdentPattern) and pattern.name not in self.constants:
                del self.params[pattern.name]

        # Position at merge block
        self.builder.position_at_end(merge_block)

        # Create phi node for the result if arms have values
        if arm_values and arm_exit_blocks:
            # Filter out terminated blocks (those that returned)
            incoming = [(val, block) for val, block in zip(arm_values, arm_exit_blocks) if block is not None]
            if incoming:
                phi = self.builder.phi(incoming[0][0].type)
                for val, block in incoming:
                    phi.add_incoming(val, block)
                return phi

        # Return a dummy value if no arms produce values
        return ir.Constant(self.i32, 0)


    def _emit_try_op(self, expr: rast.TryOp) -> ir.Value:
        """Emit the try operator: expr?

        For Result<T, E>:
        - If expr is Ok(v), return v
        - If expr is Err(e), return early from the function with Err(e)

        The enclosing function must return Result<_, E> with the same error type.
        """
        # Emit the inner expression
        result_val = self._emit_expr(expr.expr)

        # Get the enum name from the expression type
        enum_name = self._get_enum_name_from_expr(expr.expr)
        if not enum_name:
            raise ValueError(f"Try operator requires a Result type, got expression: {type(expr.expr)}")

        if not enum_name.startswith("Result$"):
            raise ValueError(f"Try operator requires a Result type, got: {enum_name}")

        # Get the Result type info
        enum_type, variants = self.enum_types[enum_name]

        # Store result to memory so we can extract tag and data
        result_alloca = self.builder.alloca(enum_type, name="try.result")
        self.builder.store(result_val, result_alloca)

        # Load the tag
        tag_ptr = self.builder.gep(result_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        tag = self.builder.load(tag_ptr)

        # Create blocks for Ok and Err cases
        ok_block = self.current_fn.append_basic_block("try.ok")
        err_block = self.current_fn.append_basic_block("try.err")
        merge_block = self.current_fn.append_basic_block("try.merge")

        # Result<T, E> has tag 0 = Ok, tag 1 = Err
        is_ok = self.builder.icmp_unsigned('==', tag, ir.Constant(self.i8, 0))
        self.builder.cbranch(is_ok, ok_block, err_block)

        # Err block: return early with Err(e)
        self.builder.position_at_end(err_block)

        # Get the function's return type - must also be a Result
        ret_type = self.current_fn.function_type.return_type
        ret_ritz_type = self.current_fn_def.ret_type if self.current_fn_def else None

        # Extract the Err payload from the result
        # Get the Err variant's field type
        err_variant = next((v for v in variants if v.name == "Err"), None)
        if not err_variant or not err_variant.fields:
            raise ValueError(f"Result type {enum_name} has no Err variant with payload")

        err_field_type = err_variant.fields[0]
        llvm_err_type = self._ritz_type_to_llvm(err_field_type)

        # Get pointer to data buffer (index depends on alignment padding)
        data_index = self._get_enum_data_index(enum_name)
        data_ptr = self.builder.gep(result_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, data_index)])
        err_ptr = self.builder.bitcast(data_ptr, ir.PointerType(llvm_err_type))
        err_val = self.builder.load(err_ptr)

        # Create the Err result to return
        # We need to construct a Result<T', E> where T' is the function's return type's Ok payload
        # The function return type should be Result_X_Y where Y matches our E
        fn_ret_type_name = None
        if isinstance(ret_ritz_type, rast.NamedType):
            if ret_ritz_type.args:
                # Generic instantiation like Result<i32, i32>
                fn_ret_type_name = self._get_specialized_type_name(ret_ritz_type)
            else:
                # Simple named type (already monomorphized)
                fn_ret_type_name = ret_ritz_type.name

        if not fn_ret_type_name or fn_ret_type_name not in self.enum_types:
            raise ValueError(f"Try operator used in function not returning Result type (got {fn_ret_type_name})")

        fn_ret_enum_type, _ = self.enum_types[fn_ret_type_name]

        # Create a new Result with Err variant
        ret_alloca = self.builder.alloca(fn_ret_enum_type, name="try.ret")

        # Set tag to 1 (Err)
        ret_tag_ptr = self.builder.gep(ret_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        self.builder.store(ir.Constant(self.i8, 1), ret_tag_ptr)

        # Store the error value (use data index for the return type enum)
        ret_data_index = self._get_enum_data_index(fn_ret_type_name)
        ret_data_ptr = self.builder.gep(ret_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, ret_data_index)])
        ret_err_ptr = self.builder.bitcast(ret_data_ptr, ir.PointerType(llvm_err_type))
        self.builder.store(err_val, ret_err_ptr)

        # Load the result and return
        ret_val = self.builder.load(ret_alloca)

        # Emit drops before early return (no variable to exclude)
        self._emit_drop_for_all_scopes(None)
        self.builder.ret(ret_val)

        # Ok block: extract the Ok payload and continue
        self.builder.position_at_end(ok_block)

        # Get the Ok variant's field type
        ok_variant = next((v for v in variants if v.name == "Ok"), None)
        if not ok_variant or not ok_variant.fields:
            raise ValueError(f"Result type {enum_name} has no Ok variant with payload")

        ok_field_type = ok_variant.fields[0]
        llvm_ok_type = self._ritz_type_to_llvm(ok_field_type)

        # Extract the Ok payload (reuse data_index from earlier)
        ok_data_ptr = self.builder.gep(result_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, data_index)])
        ok_ptr = self.builder.bitcast(ok_data_ptr, ir.PointerType(llvm_ok_type))
        ok_val = self.builder.load(ok_ptr)

        # Branch to merge with the Ok value
        self.builder.branch(merge_block)
        ok_exit = self.builder.block

        # Merge block: phi node for the Ok value
        self.builder.position_at_end(merge_block)
        phi = self.builder.phi(llvm_ok_type, name="try.val")
        phi.add_incoming(ok_val, ok_exit)

        return phi


    def _get_specialized_type_name(self, ty: rast.NamedType) -> str:
        """Get the specialized name for a generic type (e.g., Result<i32, i32> -> Result$i32_i32)."""
        base = ty.name
        arg_parts = []
        for arg in ty.args:
            arg_parts.append(self._type_to_name_suffix(arg))
        # Use $ separator between base name and type args (matches monomorphizer)
        return f"{base}${'_'.join(arg_parts)}"


    def _type_to_name_suffix(self, ty: rast.Type) -> str:
        """Convert a type to a name suffix for monomorphization."""
        if isinstance(ty, rast.NamedType):
            if ty.args:
                return self._get_specialized_type_name(ty)
            return ty.name
        elif isinstance(ty, rast.PtrType):
            return "ptr_" + self._type_to_name_suffix(ty.inner)
        else:
            return str(ty)


    def _emit_cast(self, expr: rast.Cast) -> ir.Value:
        """Emit a type cast: expr as Type.

        This is an explicit cast operation that allows conversions that
        the implicit _convert_type might not allow. It also provides
        type information for subsequent operations (e.g., field access
        on cast pointers).
        """
        # Check if casting TO a union type
        if isinstance(expr.target, rast.NamedType) and expr.target.name in self.union_types:
            return self._emit_cast_to_union(expr)

        # Check if casting TO a dyn Trait type
        if isinstance(expr.target, rast.DynType):
            return self._emit_cast_to_dyn(expr)

        # Check if casting TO a reference/pointer to dyn Trait (e.g., &dyn Animal)
        if isinstance(expr.target, (rast.RefType, rast.PtrType)):
            if isinstance(expr.target.inner, rast.DynType):
                return self._emit_cast_to_dyn_ref(expr)

        # Check if casting FROM a union type to a variant type
        # This happens in match arms: x as i32, x as *u8, etc.
        val = self._emit_expr(expr.expr)

        # Check if the source expression's type is a union
        src_union_name = self._get_union_name_from_expr(expr.expr)
        if src_union_name and src_union_name in self.union_types:
            return self._emit_cast_from_union(val, src_union_name, expr.target)

        target_type = self._ritz_type_to_llvm(expr.target)

        # Check if source OR target is unsigned for proper extension
        # When casting to unsigned (e.g., i32 as u64), use zext to avoid sign pollution
        # When casting from unsigned (e.g., u8 as u64), also use zext
        use_zext = self._infer_unsigned_expr(expr.expr) or self._is_unsigned_type(expr.target)

        # Handle integer widening with proper sign extension
        if isinstance(val.type, ir.IntType) and isinstance(target_type, ir.IntType):
            if val.type.width < target_type.width:
                # Boolean always uses zext
                if val.type.width == 1:
                    return self.builder.zext(val, target_type)
                # Unsigned types use zext
                if use_zext:
                    return self.builder.zext(val, target_type)
                return self.builder.sext(val, target_type)
            elif val.type.width > target_type.width:
                return self.builder.trunc(val, target_type)
            else:
                return val  # Same width

        # Use _convert_type for other conversions
        return self._convert_type(val, target_type)


    def _get_union_name_from_expr(self, expr: rast.Expr) -> Optional[str]:
        """Get the union type name if the expression has a union type."""
        if isinstance(expr, rast.Ident):
            name = expr.name
            # Check locals (var bindings)
            if name in self.locals:
                alloca, ty = self.locals[name]
                # Check if ty is a union type
                for union_name, (union_ty, _) in self.union_types.items():
                    if ty == union_ty:
                        return union_name
            # Check params (let bindings and function parameters)
            if name in self.params:
                val, ty = self.params[name]
                # Check if ty is a union type
                for union_name, (union_ty, _) in self.union_types.items():
                    if ty == union_ty:
                        return union_name
            # Check ritz_types for declared type
            if name in self.ritz_types:
                ritz_ty = self.ritz_types[name]
                if isinstance(ritz_ty, rast.NamedType) and ritz_ty.name in self.union_types:
                    return ritz_ty.name
        return None


    def _get_enum_name_from_expr(self, expr: rast.Expr) -> Optional[str]:
        """Get the enum type name if the expression has an enum type."""
        if isinstance(expr, rast.Ident):
            name = expr.name
            # Check locals (var bindings)
            if name in self.locals:
                alloca, ty = self.locals[name]
                # Check if ty is an enum type
                for enum_name, (enum_ty, _) in self.enum_types.items():
                    if ty == enum_ty:
                        return enum_name
            # Check params (let bindings and function parameters)
            if name in self.params:
                val, ty = self.params[name]
                # Check if ty is an enum type
                for enum_name, (enum_ty, _) in self.enum_types.items():
                    if ty == enum_ty:
                        return enum_name
            # Check ritz_types for declared type
            if name in self.ritz_types:
                ritz_ty = self.ritz_types[name]
                if isinstance(ritz_ty, rast.NamedType) and ritz_ty.name in self.enum_types:
                    return ritz_ty.name
        elif isinstance(expr, rast.UnaryOp) and expr.op == '*':
            # Dereference: *opt where opt is a pointer to an enum
            inner_expr = expr.operand
            if isinstance(inner_expr, rast.Ident):
                name = inner_expr.name
                # Check params for pointer-to-enum type
                if name in self.params:
                    val, ty = self.params[name]
                    if isinstance(ty, ir.PointerType):
                        pointee = ty.pointee
                        for enum_name, (enum_ty, _) in self.enum_types.items():
                            if pointee == enum_ty:
                                return enum_name
                # Check ritz_types for pointer-to-enum
                if name in self.ritz_types:
                    ritz_ty = self.ritz_types[name]
                    if isinstance(ritz_ty, rast.PtrType) and isinstance(ritz_ty.inner, rast.NamedType):
                        inner_name = ritz_ty.inner.name
                        if inner_name in self.enum_types:
                            return inner_name
        elif isinstance(expr, rast.Call):
            # Function call: look up the function's return type
            fn_name = None
            if isinstance(expr.func, rast.Ident):
                fn_name = expr.func.name
            elif isinstance(expr.func, str):
                fn_name = expr.func
            if fn_name and fn_name in self.functions:
                _, fn_def = self.functions[fn_name]
                if fn_def and fn_def.ret_type:
                    ret_type = fn_def.ret_type
                    if isinstance(ret_type, rast.NamedType):
                        if ret_type.args:
                            # Generic instantiation like Result<i32, i32>
                            specialized_name = self._get_specialized_type_name(ret_type)
                            if specialized_name in self.enum_types:
                                return specialized_name
                        else:
                            # Simple named type (possibly already monomorphized)
                            if ret_type.name in self.enum_types:
                                return ret_type.name
        return None


    def _emit_cast_to_union(self, expr: rast.Cast) -> ir.Value:
        """Emit a cast from a value to a union type: 42 as IntOrStr."""
        union_name = expr.target.name
        union_type, variants = self.union_types[union_name]

        # Emit the source value
        val = self._emit_expr(expr.expr)
        val_type = val.type

        # Find which variant this value matches (by looking at the LLVM type)
        tag = -1
        matched_variant = None
        for i, variant in enumerate(variants):
            llvm_variant_ty = self._ritz_type_to_llvm(variant)
            if val_type == llvm_variant_ty:
                tag = i
                matched_variant = variant
                break

        if tag == -1:
            raise ValueError(f"Cannot cast value of type {val_type} to union {union_name}")

        # Create the union value on stack
        # Allocate space for the union
        union_alloca = self.builder.alloca(union_type, name="union.tmp")

        # Store the tag
        tag_ptr = self.builder.gep(union_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        self.builder.store(ir.Constant(self.i8, tag), tag_ptr)

        # Store the data - bitcast the data pointer to the variant type
        data_ptr = self.builder.gep(union_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 1)])
        # Cast data buffer to pointer to variant type
        variant_ptr = self.builder.bitcast(data_ptr, ir.PointerType(val_type))
        self.builder.store(val, variant_ptr)

        # Load and return the union value
        return self.builder.load(union_alloca)


    def _emit_cast_from_union(self, union_val: ir.Value, union_name: str, target_type: rast.Type) -> ir.Value:
        """Emit a cast from a union value to a variant type: x as i32."""
        union_type, variants = self.union_types[union_name]
        target_llvm_type = self._ritz_type_to_llvm(target_type)

        # Store union to memory so we can extract from it
        union_alloca = self.builder.alloca(union_type, name="union.extract")
        self.builder.store(union_val, union_alloca)

        # Get pointer to data buffer and bitcast to target type
        data_ptr = self.builder.gep(union_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 1)])
        variant_ptr = self.builder.bitcast(data_ptr, ir.PointerType(target_llvm_type))

        # Load and return the value
        return self.builder.load(variant_ptr)


    def _emit_cast_to_dyn(self, expr: rast.Cast) -> ir.Value:
        """Emit a cast to dyn Trait: expr as dyn Trait.

        This creates a fat pointer { data_ptr, vtable_ptr }.
        """
        dyn_type = expr.target  # rast.DynType
        trait_name = dyn_type.trait_name

        # Get the concrete type being cast
        concrete_type_name = self._get_type_name_from_expr(expr.expr)
        if not concrete_type_name:
            raise ValueError(f"Cannot determine concrete type for dyn cast at {expr.span}")

        # Get the vtable for this (trait, type) pair
        vtable = self._get_vtable_for_type(trait_name, concrete_type_name)
        if vtable is None:
            raise ValueError(f"No vtable found for {concrete_type_name} implementing {trait_name} at {expr.span}")

        # Emit the expression value
        val = self._emit_expr(expr.expr)

        # Get a pointer to the data
        # If val is already a pointer, use it directly; otherwise allocate
        if isinstance(val.type, ir.PointerType):
            data_ptr = val
        else:
            # Allocate storage for the value
            data_alloca = self.builder.alloca(val.type, name='dyn.storage')
            self.builder.store(val, data_alloca)
            data_ptr = data_alloca

        # Create fat pointer
        return self._pack_fat_pointer(trait_name, data_ptr, vtable)


    def _emit_cast_to_dyn_ref(self, expr: rast.Cast) -> ir.Value:
        """Emit a cast to &dyn Trait or *dyn Trait.

        This is the most common case: &concrete_val as &dyn Trait.
        """
        dyn_type = expr.target.inner  # rast.DynType (inside the RefType/PtrType)
        trait_name = dyn_type.trait_name

        # Get the concrete type being cast
        # For &T -> &dyn Trait, we need the T
        concrete_type_name = self._get_type_name_from_expr(expr.expr)
        if not concrete_type_name:
            # Try to infer from the inner type if expr is a reference
            inner_type = self._infer_ritz_type(expr.expr)
            if isinstance(inner_type, (rast.RefType, rast.PtrType)):
                if isinstance(inner_type.inner, rast.NamedType):
                    concrete_type_name = inner_type.inner.name

        if not concrete_type_name:
            raise ValueError(f"Cannot determine concrete type for dyn cast at {expr.span}")

        # Get the vtable for this (trait, type) pair
        vtable = self._get_vtable_for_type(trait_name, concrete_type_name)
        if vtable is None:
            raise ValueError(f"No vtable found for {concrete_type_name} implementing {trait_name} at {expr.span}")

        # Emit the expression (should be a reference/pointer)
        data_ptr = self._emit_expr(expr.expr)

        # Create fat pointer
        return self._pack_fat_pointer(trait_name, data_ptr, vtable)


