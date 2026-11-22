"""Pattern and match emission, split out of emitter_llvmlite (AGAST #1826, slice 4).

The match family — `_emit_match`'s dispatch, the bare-constructor scrutinee
resolution, the float/tuple arm merge, `_emit_enum_match`, the integer and
StrView matches and every refusal helper they call — were LLVMEmitter methods
in emitter_llvmlite.py.  They are now a `PatternEmitter` mixin, moved verbatim
in the same order, so the emitted IR is byte-identical; the corpus replay
against the train-tail worktree is the evidence for that.
"""

from typing import ClassVar, List, Optional

from llvmlite import ir

import ritz_ast as rast
from monomorph import resolve_alias_in
from tail_value import arm_diverges, value_tails
import bool_rules
import match_coverage
import binder_names
from emitter.common import (EmitError, NoValue, _PASS_ARM, has_no_value)


class PatternEmitter:
    """Pattern and match emission for `LLVMEmitter`; mixed in with its bases."""

    def _emit_match(self, expr: rast.Match) -> ir.Value:
        """Emit a match expression.

        For enum types with VariantPattern arms, generates a switch on the tag.
        Each arm extracts the appropriate type from the enum data.
        """
        # A bare constructor names its enum by its payload alone (#2433).
        built = self._emit_bare_ctor_scrutinee(expr)
        if built is not None:
            return self._emit_enum_match(expr, *built)

        # Emit the match expression
        match_val = self._emit_expr(expr.expr)

        # A StrView compares with string literal arms (§8.2, AGAST #1876);
        # nothing else takes one.
        strview_ty = self.struct_types.get('StrView')
        if strview_ty is not None and match_val.type == strview_ty:
            return self._emit_strview_match(expr, match_val)
        self._refuse_string_arms(expr)

        # Check if matching on an enum type. `match @place` (angelo's
        # `match @self.cmap`) matches the enum the borrow addresses:
        # _emit_enum_match loads through a pointer-to-enum. Since #2124 `@x`
        # infers as a pointer, so the enum is named by the operand (AGAST
        # #2140). Kept here, not in _get_enum_name_from_expr: `(@e)?` and
        # `(@e) as T` are pointer operations, not enum ones.
        enum_src = expr.expr
        if (isinstance(enum_src, rast.UnaryOp)
                and enum_src.op in ('@', '&', '@&', '&mut')):
            enum_src = enum_src.operand
        enum_name = self._get_enum_name_from_expr(enum_src)
        if enum_name and enum_name in self.enum_types:
            return self._emit_enum_match(expr, match_val, enum_name)

        # Source-level classification can fail — a UFCS method-call scrutinee
        # (`match v.pop()`) or an unqualified constructor (`match Holds(1)`,
        # `match Vacant`) has no inferable declared type. But the emitted
        # value already knows: its LLVM type is the enum's identified struct.
        # Falling through instead sent Option matches to _emit_integer_match,
        # where `Some(x)` binds nothing and the arm dies with `Unknown
        # identifier: x` (AGAST #1321). Compare the type itself: a user enum's
        # struct is named `enum.<module>.Opt`, not its enum_types key (#2101).
        for enum_name, (enum_ty, _) in self.enum_types.items():
            if match_val.type == enum_ty:
                return self._emit_enum_match(expr, match_val, enum_name)

        # Check if matching on an integer type
        if isinstance(match_val.type, ir.IntType):
            return self._emit_integer_match(expr, match_val)

        # A char pattern is refused on every scrutinee but a u8 (LARB R72,
        # #4196); a type none of the above took (a pointer, say) says so at
        # the pattern rather than with the generic "not supported" below.
        self._refuse_char_arms(expr, False)
        raise NotImplementedError(f"Match on type {match_val.type} not yet supported")

    # The builtin constructors: (generic enum, which type argument the payload
    # gives, or None for a unit variant).
    _BUILTIN_CTORS = {'Some': ('Option', 0), 'None': ('Option', None),
                      'Ok': ('Result', 0), 'Err': ('Result', 1)}

    def _bare_ctor_type(self, expr: rast.Expr) -> Optional[rast.NamedType]:
        """The enum the bare constructor `expr` builds, from it alone, or None.

        `Some(5)` is `Option<i64>` and `Err("x")` is `Result<i64, StrView>`: the
        payload gives its type argument, and one nothing gives is i64 (ritz1's
        rule, #2419). An unqualified variant of a user's enum is that enum. What
        the module has registered has no say (#2433): ritz0 reused the last
        `Option<...>` it had, so with `Option<u8>` registered `Some(300)` didn't fit,
        and without any `Some` was an unknown function. None for anything else,
        a name a value shadows, or a payload whose type isn't inferable.
        """
        while isinstance(expr, rast.Grouped):
            expr = expr.expr
        if isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident):
            name, args, span = expr.func.name, expr.args, expr.func.span
        elif isinstance(expr, rast.Ident):
            name, args, span = expr.name, None, expr.span
        else:
            return None
        if self._sizeof_is_value(name):
            return None
        declarers = self.variant_declarers.get(name, ())
        if declarers:
            self._check_variant_unambiguous(name, span)
            return rast.NamedType(span, declarers[0], [])
        if name not in self._BUILTIN_CTORS:
            return None
        base, slot = self._BUILTIN_CTORS[name]
        if (slot is None) != (args is None) or (args is not None and len(args) != 1):
            return None
        type_args = [rast.NamedType(span, 'i64', []) for _ in range(2 if base == 'Result' else 1)]
        if slot is not None:
            arg = args[0]
            if (isinstance(arg, rast.BinOp)
                    and arg.op in bool_rules.COMPARISONS + bool_rules.LOGICAL):
                # _infer_ritz_type gives a BinOp its left operand's type.
                payload = rast.NamedType(arg.span, 'bool', [])
            else:
                payload = self._bare_ctor_type(arg) or self._infer_ritz_type(arg)
            if payload is None or (isinstance(payload, rast.NamedType)
                                   and payload.name in ('null', 'unknown')):
                return None
            type_args[slot] = payload
        return rast.NamedType(span, base, type_args)

    def _builtin_ctor_parts(self, expr: rast.Expr) -> Optional[tuple]:
        """(name, payload or None) of a bare builtin constructor, else None.

        `Some(x)` -> ('Some', x), `None` -> ('None', None). A name a user enum
        declares is that enum's (_bare_variant_enum), so it is no builtin here.
        """
        while isinstance(expr, rast.Grouped):
            expr = expr.expr
        if isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident):
            name, payload = expr.func.name, (expr.args[0] if len(expr.args) == 1 else None)
        elif isinstance(expr, rast.Ident):
            name, payload = expr.name, None
        else:
            return None
        if name not in self._BUILTIN_CTORS or self.variant_declarers.get(name):
            return None
        return name, payload

    def _untyped_nested_ctor_type(self, value: rast.Expr) -> Optional[rast.NamedType]:
        """The enum an untyped `let` / `var` binds when a constructor nests one.

        `let o = Some(Some(5))` is `Option<Option<i64>>`, and the arms of
        `if c then Ok(1) else Err(Ok(5))` build `Result<i64, Result<i64, i64>>`:
        each type argument from the first constructor whose payload gives it
        (_bare_ctor_type, ritz1's #2419 / #2435 rule), i64 where none does.
        With no enum the outer constructor took whichever Option the module
        registered last, and its `Option$i64` payload met that enum's i64 slot
        (AGAST #3045). None, leaving the initialiser as it was, unless some
        tail is a builtin constructor wrapping another, every tail is a
        builtin constructor of one family, and each payload is inferable.
        """
        tails = list(value_tails(value))
        parts = [self._builtin_ctor_parts(tail) for tail in tails]
        if not any(p is not None and p[1] is not None
                   and self._builtin_ctor_parts(p[1]) is not None for p in parts):
            return None
        if any(p is None for p in parts):
            return None
        base = self._BUILTIN_CTORS[parts[0][0]][0]
        type_args: List[Optional[rast.Type]] = [None] * (2 if base == 'Result' else 1)
        for tail, (name, _) in zip(tails, parts):
            family, slot = self._BUILTIN_CTORS[name]
            if family != base:
                return None
            ty = self._bare_ctor_type(tail)
            if ty is None:
                return None
            if slot is not None and type_args[slot] is None:
                type_args[slot] = ty.args[slot]
        span = getattr(value, 'span', None)
        return rast.NamedType(span, base, [
            arg if arg is not None else rast.NamedType(span, 'i64', []) for arg in type_args])

    def _emit_bare_ctor_scrutinee(self, expr: rast.Match) -> Optional[tuple]:
        """Build `match Some(5)`'s scrutinee as the enum _bare_ctor_type names.

        Returns (value, enum name) for _emit_enum_match, or None when the
        scrutinee is no bare constructor. `@Some(5)` borrows a value only the
        match holds, so it is matched as that value. The match owns what it
        built (#2174) by the move checker's `owns_scrutinee`.
        """
        scrut = expr.expr
        while isinstance(scrut, rast.Grouped):
            scrut = scrut.expr
        if isinstance(scrut, rast.UnaryOp) and scrut.op in ('@', '&', '@&', '&mut'):
            scrut = scrut.operand
        if expr.ctor_type is not None:
            # A generic user enum's instance, as monomorph inferred it from
            # the payload (`match Hold(5)` is a `W$i64`, AGAST #2437).
            enum_name = self._resolve_enum_type_name(expr.ctor_type)
            if enum_name is not None:
                return self._emit_enum_variant_with_type(scrut, enum_name), enum_name
        ty = self._bare_ctor_type(scrut)
        if ty is None:
            return None
        if ty.args:
            enum_name = self._ensure_builtin_generic_specialization(ty)
        else:
            enum_name = ty.name
        if enum_name not in self.enum_types:
            return None
        return self._emit_enum_variant_with_type(scrut, enum_name), enum_name

    @staticmethod
    def _require_covered(expr: rast.Match, gap: List[str]) -> None:
        """Refuse a match that misses something (LARB R6, AGAST #2344).

        Every switch below then has an `unreachable` default that really is
        unreachable. Before this a miss ran the last arm: LLVM folds such a
        default into a case, so `f(5)` silently took `1 => 2`.
        """
        if gap:
            raise EmitError(f"non-exhaustive match: missing {', '.join(gap)}", expr.span)

    @staticmethod
    def _require_reachable(expr: rast.Match, gap, test) -> None:
        """Refuse an arm no value can reach (LARB R13, AGAST #2349).

        Arms are tried in order, so before this `_ => 1 / 5 => 2` gave 2 here
        (the catch-all became the switch default and `5` still a case) and 1
        on ritz1, silently, and a repeated value failed at clang, unlocated.
        `gap` is the R6 check for this scrutinee, asked of the arms so far.
        """
        found = match_coverage.unreachable_arm(expr.arms, gap, test)
        if found:
            arm, cover = found
            raise EmitError(f"unreachable match arm: the arm at line "
                            f"{cover.pattern.span.line} covers it", arm.pattern.span)

    @staticmethod
    def _int_const_fits(const: ir.Constant, width: int) -> bool:
        """True if integer constant `const` is representable in `width` bits.

        Accepts the signed range and the unsigned range, so `0xFFFFFFFF` fits a
        u32-typed (i32) arm just as `-1` does.
        """
        value = const.constant
        return -(1 << (width - 1)) <= value < (1 << width)

    # --- AGAST #2027: arms of a float-annotated initialiser ------------------
    #
    # `let a: f64 = 0` and `let a: f64 = <int expr>` convert the initialiser
    # to the annotation (sitofp, via _convert_type); so does `let a: f32 =
    # <f64>` (fptrunc). A match or if that IS the initialiser gets the same
    # conversion per arm, so its arms merge at the annotation's float type
    # instead of being called irreconcilable (match: no value, once a raw
    # AttributeError in LetStmt) or merged at the "larger" int type (if:
    # `if c then 0 else 1.5` truncated 1.5 to 1). Same rule as ritz1 #1946.

    def _float_tail_ids(self, root: Optional[rast.Expr]) -> set:
        """Ids of the Match / If nodes that are value tails of `root`.

        A tail is the initialiser itself, or (recursively) a match arm body,
        an if branch's trailing expression, or a block's trailing expression.
        Anything else (a call argument, an operand, a cast) consumes the
        value at a type we have not established, so the descent stops there.
        """
        ids = set()
        stack = [root]
        while stack:
            node = stack.pop()
            if isinstance(node, rast.Match):
                ids.add(id(node))
                stack.extend(arm.body for arm in node.arms)
            elif isinstance(node, rast.If):
                ids.add(id(node))
                stack.append(node.then_block)
                stack.append(node.else_block)
            elif isinstance(node, rast.Block):
                stack.append(node.expr)
        return ids

    def _float_annotation_llvm(self, ty: Optional[rast.Type]) -> Optional[ir.Type]:
        """The LLVM float type for an `f32` / `f64` annotation, else None."""
        if isinstance(ty, rast.NamedType) and not ty.args:
            if ty.name == 'f32':
                return self.f32
            if ty.name == 'f64':
                return self.f64
        return None

    def _enter_float_tails(self, ty: Optional[rast.Type], value) -> tuple:
        """Install the float-merge context for a typed initialiser.

        Returns the previous context for _leave_float_tails: a typed `let`
        nested in an arm block must not leave its own context behind.
        """
        saved = (getattr(self, '_float_tail_set', frozenset()),
                 getattr(self, '_float_tail_ty', None))
        float_ty = self._float_annotation_llvm(ty)
        if float_ty is None:
            self._float_tail_set, self._float_tail_ty = frozenset(), None
        else:
            self._float_tail_set = self._float_tail_ids(value)
            self._float_tail_ty = float_ty
        return saved

    def _leave_float_tails(self, saved: tuple) -> None:
        self._float_tail_set, self._float_tail_ty = saved

    def _float_merge_type(self, node) -> Optional[ir.Type]:
        """The float type `node`'s arms must merge at, or None."""
        if id(node) in getattr(self, '_float_tail_set', frozenset()):
            return self._float_tail_ty
        return self._float_slot_ids.get(id(node))

    def _float_slot(self, ty: Optional[rast.Type], value) -> None:
        """LARB R43 (#3384): `value` lands in a slot of Ritz type `ty`.

        A `-> f64` return or tail, or an `f64` parameter, is a float slot as
        an annotated let is: the match / if tails of `value` merge at it, so
        an integer literal arm converts, and a non-literal integer arm meets
        §7.5's exactness rule (_int_into_float_slot) instead of #2094's
        refusal.
        """
        float_ty = self._float_annotation_llvm(
            resolve_alias_in(ty, self.type_aliases) if ty is not None else None)
        if float_ty is not None:
            self._mark_float_tails(float_ty, value)

    def _mark_float_tails(self, float_ty: ir.Type, value) -> None:
        """Merge `value`'s match / if tails at `float_ty` (see _float_slot)."""
        if value is not None:
            for node_id in self._float_tail_ids(value):
                self._float_slot_ids[node_id] = float_ty

    @staticmethod
    def _is_float_arm_convertible(ty: ir.Type) -> bool:
        """Arm types _convert_type turns into a float the way a plain let does.

        bool (i1) is excluded: the plain form `let a: f64 = <bool>` gives
        -1.0 in ritz0 and 1.0 in ritz1 (#2093), so it is not copied here.
        """
        if isinstance(ty, (ir.FloatType, ir.DoubleType)):
            return True
        return isinstance(ty, ir.IntType) and ty.width > 1

    def _merge_arms_at_float(self, incoming: list, float_ty: ir.Type) -> Optional[ir.Value]:
        """Merge (value, exit_block) arms at `float_ty`, or None.

        Applies when every arm converts the way the plain-form let does
        (_is_float_arm_convertible), all-int arms included (#3313): each
        converts as its own type, so an i32 arm next to an i64 literal is
        not first widened to an i64 the annotation refuses as lossy. A
        non-numeric arm returns None so the caller's irreconcilable path
        runs. Each conversion goes in the arm's own exit block, before its
        branch, so it dominates the phi.
        """
        types = [v.type for v, _ in incoming]
        if not all(self._is_float_arm_convertible(t) for t in types):
            return None
        merge_block = self.builder.block
        converted = []
        for val, block in incoming:
            if val.type != float_ty:
                self.builder.position_before(block.terminator)
                val = self._convert_type(val, float_ty)
            converted.append((val, block))
        self.builder.position_at_end(merge_block)
        phi = self.builder.phi(float_ty)
        for val, block in converted:
            phi.add_incoming(val, block)
        return phi

    # --- AGAST #2094: the same arms with no float annotation -----------------
    #
    # With nothing to fix the merge type, an integer arm next to a float arm
    # is a located error, worded as ritz1's (#1946). It applies only when the
    # merge's value is used: a statement-position if / match whose arm tails
    # are an int call and a float call has no merge to type.

    MIXED_INT_FLOAT_ARMS = (
        "match arms yield both an integer and a float value; write the "
        "integer arm as a float (`0.0`) or annotate the binding")

    # --- AGAST #2093: a pointer into a float slot -----------------------------
    #
    # LARB R1 / R4: nothing converts implicitly into a float but a number.
    # `let a: f64 = p` bound the pointer as an f64, and an if arm `p` next to
    # `1.5` built `phi i8*` over a double constant. One message for the plain
    # let / var and for an if or match arm, located at the pointer value.

    POINTER_AS_FLOAT = "cannot use a pointer as a float"

    # AGAST #3759: `pass` where a value is wanted, worded as ritz1's
    # (ritz1/src/pass_value.ritz). Located at the `pass`.
    PASS_HAS_NO_VALUE = (
        "`pass` has no value, so it can't be used where a value is wanted; "
        "write the value (`0` if you mean 0)")

    def _reject_pointer_into_float(self, val: ir.Value, float_ty: ir.Type,
                                   at: Optional[rast.Expr] = None) -> None:
        """Refuse `val` landing in `float_ty` when it is a pointer."""
        if not (isinstance(val.type, ir.PointerType)
                and isinstance(float_ty, (ir.FloatType, ir.DoubleType))):
            return
        if at is None:
            origin = self._value_origin.get(id(val))
            at = origin[1] if origin is not None and origin[0] is val else None
        # #4199: an arm block's value is its tail (`let q: *u8 ...` then
        # `q`), reported there rather than at the block's first line.
        while isinstance(at, rast.Block) and at.expr is not None:
            at = at.expr
        raise EmitError(self.POINTER_AS_FLOAT,
                        self._value_span(at) if at is not None else None)

    def _reject_pointer_beside_float(self, arms: list) -> None:
        """Refuse a pointer arm of an unannotated merge with a float arm.

        `arms` is (value, located expr or None). With no float slot ritz0
        merged by size, so `if c then 1.5 else p` built `phi i8*` over a
        double (#4199); a float arm fixes the merge as a float, as ritz1's
        Sema does, and the pointer is #2093's error at the pointer. Used or
        not: ritz1 refuses a statement-position merge too.
        """
        float_tys = [v.type for v, _ in arms
                     if isinstance(v.type, (ir.FloatType, ir.DoubleType))]
        if not float_tys:
            return
        for val, at in arms:
            self._reject_pointer_into_float(val, float_tys[0], at)

    def _merge_value_used(self, node) -> bool:
        """Whether the value of match / if `node` is used (#2046, #2094)."""
        if id(node) in self._tail_merge_ids:
            return True
        if isinstance(node, rast.If):
            bodies = [node.then_block, node.else_block]
        else:
            bodies = [arm.body for arm in node.arms]
        return any(id(b) in self._used_arms for b in bodies if b is not None)

    def _reject_mixed_int_float_arms(self, node, types) -> None:
        """Refuse a used, unannotated merge of integer and float arms.

        bool (i1) is not an integer here: next to a float it is #2093's.
        """
        has_float = any(isinstance(t, (ir.FloatType, ir.DoubleType))
                        for t in types)
        has_int = any(isinstance(t, ir.IntType) and t.width > 1
                      for t in types)
        if has_float and has_int and self._merge_value_used(node):
            raise EmitError(self.MIXED_INT_FLOAT_ARMS,
                            getattr(node, 'span', None))

    def _merge_float_arms(self, expr: rast.Match,
                          incoming: list) -> Optional[ir.Value]:
        """A match's float merge (#2027), or None; refuses #2094's arms."""
        float_ty = self._float_merge_type(expr)
        if float_ty is None:
            self._reject_mixed_int_float_arms(expr, [v.type for v, _ in incoming])
            self._reject_pointer_beside_float([(v, None) for v, _ in incoming])
            return None
        for val, _ in incoming:
            self._reject_pointer_into_float(val, float_ty)
        return self._merge_arms_at_float(incoming, float_ty)

    def _unify_tuple_arms(self, incoming: list) -> list:
        """Tuple arms of a match retyped to the first live arm's tuple type.

        AGAST #3022: an untyped integer literal is an i64, so `Some(v) =>
        (v, 1)` (v: i32) and `None => (5, 6)` yield `{i32, i64}` and
        `{i64, i64}`: no single phi type, and the match read as having no
        value. As in ritz1 (#3005), the first arm fixes the tuple type and
        a later arm of the same arity converts to it, element by element,
        in its own exit block before that block's branch to the merge.
        Anything else (not all tuples, arities differ) is left as it was.
        """
        if not incoming:
            return incoming
        first = incoming[0][0].type
        if not isinstance(first, ir.LiteralStructType) or not all(
                isinstance(v.type, ir.LiteralStructType)
                and len(v.type.elements) == len(first.elements)
                for v, _ in incoming):
            return incoming
        if all(v.type == first for v, _ in incoming):
            return incoming
        merge_block = self.builder.block
        unified = []
        for val, block in incoming:
            if val.type != first:
                self.builder.position_before(block.terminator)
                val = self._convert_type(val, first)
            unified.append((val, block))
        self.builder.position_at_end(merge_block)
        return unified

    def _merge_match_arms(self, incoming: list) -> ir.Value:
        """Build the merge phi for a value-producing match.

        `incoming` is a non-empty list of (value, exit_block) pairs whose types
        are all equal or all integers (callers reject anything else). The builder
        must be positioned at the (empty) start of the merge block.

        The phi type is NOT the first arm's type (AGAST #1653): an untyped
        integer literal is an i64 constant, so `Ok(_) => 0` followed by
        `Err(e) => e` (i32) produced `phi i64 [0, ..], [%i32val, ..]` — invalid
        IR. Instead:

        * Integer-literal arms (int constants) adopt the widest *non-constant*
          arm type, provided their value fits it.
        * Otherwise (a literal that does not fit, or differing non-constant
          widths) everything widens to the widest arm type.
        * A non-constant arm that must widen is converted in its OWN exit
          block, just before that block's branch to the merge block. Converting
          in the merge block would put the instruction after/among the phis
          and fail to dominate its phi use.
        """
        first_type = incoming[0][0].type
        for val, _ in incoming[1:]:
            self._check_bool_slot(val, first_type, None)
        merged = self._merge_large_struct_arms(incoming)
        if merged is not None:
            return merged
        if all(v.type == first_type for v, _ in incoming):
            phi = self.builder.phi(first_type)
            for val, block in incoming:
                phi.add_incoming(val, block)
            return phi

        def is_int_literal(v):
            return isinstance(v, ir.Constant) and isinstance(v.constant, int)

        typed = [v for v, _ in incoming if not is_int_literal(v)]
        if typed:
            common_type = max((v.type for v in typed), key=lambda t: t.width)
            if not all(self._int_const_fits(v, common_type.width)
                       for v, _ in incoming if is_int_literal(v)):
                common_type = max((v.type for v, _ in incoming),
                                  key=lambda t: t.width)
        else:
            common_type = max((v.type for v, _ in incoming),
                              key=lambda t: t.width)

        merge_block = self.builder.block
        converted = []
        for val, block in incoming:
            if val.type != common_type:
                if is_int_literal(val):
                    # Retype the literal; width only shrinks when it fits.
                    # Store it in signed form so `i32 4294967295` prints as
                    # `i32 -1`.
                    value, width = val.constant, common_type.width
                    if value >= (1 << (width - 1)):
                        value -= 1 << width
                    val = ir.Constant(common_type, value)
                else:
                    self.builder.position_before(block.terminator)
                    val = self._convert_type(val, common_type)
            converted.append((val, block))
        self.builder.position_at_end(merge_block)

        phi = self.builder.phi(common_type)
        for val, block in converted:
            phi.add_incoming(val, block)
        self._note_int_merge(phi, [v for v, _ in incoming])
        return phi

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
        variant_names = {variant.name for variant in variants}
        # A char pattern's own error, ahead of the generic literal one.
        self._refuse_char_arms(expr, False)
        self._refuse_pattern_kind(expr, rast.LitPattern)
        self._refuse_arm_names(expr, lambda name: name in variant_names)
        names = [variant.name for variant in variants]
        # Ahead of coverage, which judges the fields a pattern has: `Two(a)`
        # covered `Two(i32, i32)` (AGAST #2408).
        for arm in expr.arms:
            self._require_field_count(enum_name, arm.pattern)
        self._require_covered(expr, match_coverage.enum_gap(expr.arms, names))
        # An arm naming a variant this enum doesn't declare is that error, not
        # an unreachable arm, though it follows every variant (AGAST #2349).
        for arm in expr.arms:
            if isinstance(arm.pattern, rast.VariantPattern):
                self._require_enum_variant(enum_name, arm.pattern.name, arm.pattern.span)
        self._require_reachable(expr, lambda arms: match_coverage.enum_gap(arms, names),
                                match_coverage.enum_test(variant_names))

        # Store enum to memory so we can extract tag and data. Matching on a
        # place (`match self.cmap`) can hand us a pointer to the enum rather
        # than the value; load through it first.
        if (isinstance(enum_val.type, ir.PointerType)
                and enum_val.type.pointee == enum_type):
            enum_val = self.builder.load(enum_val)
        enum_alloca = self.builder._entry_alloca(enum_type, "match.enum")
        self.builder.store(enum_val, enum_alloca)
        # A match owns a scrutinee it moved (AGAST #2177, set by the move
        # checker): the spill is a nameless binding in a drop scope of its
        # own, dropped after the arms meet unless an arm took its payload.
        scrut_flag = self._own_match_scrutinee(expr, enum_alloca)

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
                # Find the tag for this variant. A pattern naming a variant the
                # scrutinee's enum does not declare is a source error that no
                # earlier pass rejects, so report it here against the pattern's
                # own span instead of letting a bare ValueError escape.
                self._require_enum_variant(enum_name, pattern.name, pattern.span)
                self._refuse_payload_pattern(pattern)
                tag_val = self._get_enum_variant_tag(enum_name, pattern.name)
                switch.add_case(ir.Constant(self.i8, tag_val), arm_block)
            elif isinstance(pattern, rast.IdentPattern):
                # IdentPattern with a variant name (e.g., just `None` without parens)
                # `variant_to_enum` is global across every enum in scope, so a
                # bare name belonging to a *different* enum used to pass this
                # test and then crash in the tag lookup. An unqualified name is
                # only a variant case when it belongs to *this* enum; otherwise
                # it is an ordinary catch-all binding.
                if self._has_enum_variant(enum_name, pattern.name):
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
            # The arm's payload bindings drop at its end (AGAST #2177).
            if scrut_flag is not None:
                self._push_drop_scope()
                takes = getattr(arm, 'takes_payload', False)
                if takes:
                    # This arm, not the scrutinee, owns the payload now.
                    self.builder.store(ir.Constant(self.i1, 0), scrut_flag)

            # Bind pattern variables if this is a VariantPattern with fields
            if isinstance(pattern, rast.VariantPattern) and pattern.fields:
                variant = self._get_enum_variant(enum_name, pattern.name)

                # Get pointer to data buffer (index depends on alignment padding)
                data_index = self._get_enum_data_index(enum_name)
                data_ptr = self.builder.gep(enum_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, data_index)])

                # Extract and bind each field. Offsets come from the shared
                # layout helper, the same one the constructor uses.
                field_offsets, _, _ = self._enum_variant_field_layout(variant)
                for j, (field_pattern, field_type) in enumerate(zip(pattern.fields, variant.fields)):
                    llvm_field_type = self._ritz_type_to_llvm(field_type)

                    # Cast data buffer to pointer to field type at offset.
                    # data_ptr is [N x i8]* (pointer to array), so the GEP needs
                    # two indices -- 0 to step through the pointer, then the
                    # byte offset within the array. A single index strides by
                    # whole arrays and reads past the end of the enum. Must
                    # stay in lockstep with _emit_enum_variant_constructor.
                    field_ptr = self.builder.bitcast(
                        self.builder.gep(data_ptr, [ir.Constant(self.i32, 0),
                                                    ir.Constant(self.i32, field_offsets[j])]),
                        ir.PointerType(llvm_field_type)
                    )
                    field_val = self.builder.load(field_ptr)

                    # Bind the field value to the pattern variable
                    if isinstance(field_pattern, rast.IdentPattern):
                        # Store in params so it can be used in the arm body
                        self.params[field_pattern.name] = (field_val, llvm_field_type)
                        # Also store the Ritz type for field access on reference types
                        self.ritz_types[field_pattern.name] = field_type
                        if scrut_flag is not None and takes:
                            # The binding owns a move-only payload.
                            self._register_let_drop(field_pattern.name, field_val, field_type)
                    elif scrut_flag is not None and takes:
                        # `Pair(a, _)`: a move-only payload nobody binds
                        # drops with the arm's bindings.
                        if self._register_drop_variable("match.payload", field_ptr, field_type):
                            self._mark_drop_variable_initialized(field_ptr)
                    # Wildcard patterns just discard the value

            # Emit the arm body
            # A `return` inside one arm must not leak has_returned past
            # the match — _emit_if saves/restores per branch; matches must
            # too, or the function's trailing expression is skipped and the
            # merge block is left empty and unterminated (AGAST #1321,
            # angelo loader/ttf.ritz). Reset per arm, recombined at merge.
            _saved_arm_returned = self.has_returned
            self.has_returned = False
            arm_val = self._emit_expr_with_expected_enum(
                arm.body, getattr(self, '_expected_enum_name', None))
            self.has_returned = _saved_arm_returned
            self._end_diverging_arm(arm.body)
            self._pin_arm_unsigned(arm_val)  # payload bindings still in scope
            if scrut_flag is not None:
                # Falling off the arm drops what its bindings still own.
                self._leave_drop_scope()

            # Remember which block we're in after emitting the body. One value
            # per arm, terminated or not: _enum_match_result zips the values
            # with the exit blocks, so appending a value only for live arms
            # paired a `return` arm's `None` block with the next arm's value
            # and the tail yielded a dummy 0 (AGAST #3318).
            arm_values.append(_PASS_ARM if self._ends_in_pass(arm.body) else arm_val)
            if not self.builder.block.is_terminated:
                arm_exit_blocks.append(self.builder.block)
                self.builder.branch(merge_block)
            else:
                arm_exit_blocks.append(None)

            # Clean up bound variables
            if isinstance(pattern, rast.VariantPattern) and pattern.fields:
                for field_pattern in pattern.fields:
                    if isinstance(field_pattern, rast.IdentPattern):
                        del self.params[field_pattern.name]
                        if field_pattern.name in self.ritz_types:
                            del self.ritz_types[field_pattern.name]

        # Position at merge block
        self.builder.position_at_end(merge_block)
        # The function has definitively returned only if *every* arm
        # terminated (nothing reaches the merge block). Otherwise control
        # continues here and later statements/tail must still be emitted.
        if arm_exit_blocks and all(b is None for b in arm_exit_blocks):
            self.has_returned = True
        result = self._enum_match_result(expr, arm_values, arm_exit_blocks)
        if scrut_flag is not None:
            # After the result's phi: drop the scrutinee where no arm took
            # its payload. Nothing reaches the merge when every arm left.
            scope = self._pop_drop_scope()
            if any(b is not None for b in arm_exit_blocks):
                self._emit_drop_for_scope(scope)
        return result

    def _is_integer_const(self, name: str) -> bool:
        ty = self.constants[name][1] if name in self.constants else None
        return isinstance(ty, ir.IntType) and ty.width > 1

    def _refuse_arm_names(self, expr: rast.Match, tests) -> None:
        """A top-level arm's name binds unless `tests(name)` says it's a test
        here, and a binding can't take a module value's name (AGAST #2407).
        Ahead of coverage, as binder_names judges every other binder."""
        for arm in expr.arms:
            pattern = arm.pattern
            if not isinstance(pattern, rast.IdentPattern) or tests(pattern.name):
                continue
            kind = self._module_values.get(pattern.name)
            if kind is not None:
                raise EmitError(binder_names.refusal(kind, pattern.name),
                                pattern.span or arm.span)

    # What each pattern kind tests, for the error when the scrutinee isn't one.
    _PATTERN_NEEDS: ClassVar[dict[type, str]] = {
        rast.VariantPattern: "a variant pattern needs an enum scrutinee",
        rast.LitPattern: "a literal pattern needs an integer scrutinee"}

    # A char literal is u8 (§2.6), so only a u8 scrutinee takes its pattern
    # (LARB R72, AGAST #4196). On anything else — a wider integer, bool,
    # StrView or enum — it is an error at the pattern.
    CHAR_PATTERN_NEEDS_U8 = "a character pattern needs a u8 scrutinee"

    def _refuse_char_arms(self, expr: rast.Match, allow_u8: bool) -> None:
        """Refuse a `'(' =>` pattern unless the scrutinee is a u8."""
        if allow_u8:
            return
        for arm in expr.arms:
            pattern = arm.pattern
            if isinstance(pattern, rast.LitPattern) and pattern.is_char:
                raise EmitError(self.CHAR_PATTERN_NEEDS_U8,
                                pattern.span or arm.span)

    def _refuse_pattern_kind(self, expr: rast.Match, *kinds: type) -> None:
        """Refuse an arm whose pattern can't test this scrutinee (AGAST #2409).

        The integer switch has a case only for a literal or a const, so
        `Some(v)` on an i64 was an arm no value reached and `match n` gave the
        next one, silently. Like `true` on an integer (#2344), it is the wrong
        kind of pattern, said at the pattern. A literal on an enum raised an unlocated NotImplementedError
        (#3002); a `true` there says what #2344 says, as ritz1 does.
        """
        for arm in expr.arms:
            pattern = arm.pattern
            if not isinstance(pattern, kinds):
                continue
            message = self._PATTERN_NEEDS[type(pattern)]
            if isinstance(pattern, rast.LitPattern) and isinstance(pattern.value, bool):
                message = "a `true` or `false` pattern needs a bool scrutinee"
            raise EmitError(message, pattern.span or arm.span)

    def _resolve_module_consts(self, expr: rast.Match) -> None:
        """`mod.CONST =>` is refused, at the arm (§15.3, AGAST #2215).

        It parses as the qualified variant `C.G` does.  #2409 rewrote it to
        the const's IdentPattern; module access is gone, so the arm is now
        the bare `CONST =>`, which compares against the const (it is not a
        fresh binding).  `C.G` with `C` an enum stays a variant.
        """
        for arm in expr.arms:
            pat = arm.pattern
            if isinstance(pat, rast.VariantPattern) and pat.qualifier and not pat.fields:
                self._refuse_module_item(pat.qualifier, pat.name, pat.span)

    def _require_field_count(self, enum_name: str, pattern: rast.Pattern) -> None:
        """A variant pattern lists every field of its variant (AGAST #2408).

        The arms zip the two, so a mismatch was cut to the shorter: `Two(a)`
        read one field of two, and `Z(a)` on a bare `Z` bound nothing and died
        unlocated. A bare `Two` tests the tag alone and has no list to count;
        a variant the enum doesn't declare is _require_enum_variant's error.
        """
        if (not isinstance(pattern, rast.VariantPattern) or not pattern.fields
                or not self._has_enum_variant(enum_name, pattern.name)):
            return
        has = len(self._get_enum_variant(enum_name, pattern.name).fields)
        if has != len(pattern.fields):
            noun = "field" if has == 1 else "fields"
            raise EmitError(
                f"variant '{pattern.name}' has {has} {noun}, but this pattern "
                f"lists {len(pattern.fields)}", pattern.span)

    def _require_payload_count(self, variant_name: str, variant, args: List[rast.Expr],
                               call_span=None) -> None:
        """A variant constructor takes one value per field (AGAST #3992).

        The constructors zip the two, so `Rect(1)` on `Rect(i64, i64)` left
        the second field unwritten and `Rect(1, 2, 3)` dropped the third, both
        silently. The constructor twin of _require_field_count, said at the
        first value with ritz1's message (#1295). `call_span` is the call's,
        None for a bare `Z`: a call's list is counted whatever its length, so
        `Z(1)` and `One()` are refused at the call too (#4153).
        """
        has = len(variant.fields)
        if (call_span or args) and len(args) != has:
            raise EmitError(
                f"variant `{variant_name}` takes {has} payload value(s), "
                f"got {len(args)}", args[0].span if args else call_span)

    def _refuse_payload_pattern(self, pattern: rast.VariantPattern) -> None:
        """A variant's payload pattern is a name or `_` (LARB R76; §8.2).

        The switch above reads the tag alone, so anything inside a variant
        that would test its payload was dropped: `Some(0)` took every `Some`
        (#2350), and `Ok(Simple(x))` bound nothing and failed later with the
        red herring `Unknown identifier: x` (#1321). Both are refused at the
        inner pattern, with the message ritz1's parse recovery gives too.
        A name named like a const or variant was refused already, by
        binder_names (R12, AGAST #2407).
        """
        for field_pattern in pattern.fields:
            if not isinstance(field_pattern, (rast.WildcardPattern, rast.IdentPattern)):
                raise EmitError(
                    "a variant's payload pattern is a name or `_`: match the "
                    "inner value in its own `match`",
                    field_pattern.span or pattern.span)

    def _own_match_scrutinee(self, expr: rast.Match,
                             slot: ir.AllocaInstr) -> Optional[ir.AllocaInstr]:
        """If the match owns its scrutinee (`expr.owns_scrutinee`, the move
        checker's), open the match's drop scope with `slot`, the spilled
        scrutinee, as its nameless binding. Returns that binding's drop
        flag, or None when the match owns nothing (AGAST #2177)."""
        ty = getattr(expr, 'owns_scrutinee', None)
        if ty is None or not self.drop_scope_stack:
            return None
        self._push_drop_scope()
        if not self._register_drop_variable("match.scrut", slot, ty):
            self._pop_drop_scope()
            return None
        self._mark_drop_variable_initialized(slot)
        return self.drop_flags[id(slot)]

    def _end_diverging_arm(self, body) -> None:
        """End a match arm that never yields a value but left its block open.

        AGAST #3270: an arm that is an endless `loop` (left only by `return`)
        falls into the loop's dead exit block, which is unterminated. Branching
        it to the merge made the arm a live incoming with no value, so the
        match read as a statement and a `-> T` fn ending in it was refused.
        Like a `return` arm, it contributes no type: the block is unreachable.
        """
        if not self.builder.block.is_terminated and arm_diverges(body):
            self.builder.unreachable()

    def _enum_match_result(self, expr: rast.Match, arm_values: list,
                           arm_exit_blocks: list) -> ir.Value:
        """The value of an enum match, built in its merge block."""

        # Create phi node for the result if arms have values
        arm_values = self._fill_pass_arms(arm_values)
        if arm_values and arm_exit_blocks:
            # Filter out terminated blocks (those that returned)
            incoming = [(val, block) for val, block in zip(arm_values, arm_exit_blocks) if block is not None]
            # A match used as a *statement* has arms that produce no value
            # (a block ending in a statement). Those emit ir.Undefined (or a
            # nested match's NoValue), which cannot be phi'd: the match has
            # no value. It fell through to the `i32 0` dummy below, which a
            # value consumer read as a silent 0 (#1357); a NoValue is
            # reported at this match instead, as _emit_integer_match does.
            if not all(hasattr(val, 'type') for val, _ in incoming):
                return NoValue(getattr(expr, "span", None))
            # A float-annotated initialiser fixes the merge type (#2027).
            # #2094: unannotated int + float arms are refused if used.
            merged = self._merge_float_arms(expr, incoming) if incoming else None
            if merged is not None:
                return merged
            # Irreconcilable arm types (assignment arm yielding its enum
            # value next to a `pass` arm's dummy i32 0) also make this a
            # statement match — a phi would mix an integer constant into an
            # enum-typed phi, invalid IR (AGAST #1321, font.ritz ensure_cmap).
            #
            # Return a NoValue rather than falling through to the `i32 0`
            # dummy at the end of this function, as _emit_integer_match does.
            # In STATEMENT position nobody consumes the result. In VALUE
            # position the dummy was a fail-open: an ill-typed
            # `let v: i64 = match s { A(q) => p; B(q) => 7 }` compiled clean
            # and silently evaluated to 0 (test_match_mixed_type_arms.py).
            # Reading a NoValue raises MatchHasNoValue, located at this match
            # (#1357; it was a raw `'_Undefined' ... no attribute 'type'`).
            incoming = self._unify_tuple_arms(incoming)  # AGAST #3022
            if incoming and not all(
                    v.type == incoming[0][0].type
                    or (isinstance(v.type, ir.IntType)
                        and isinstance(incoming[0][0].type, ir.IntType))
                    for v, _ in incoming):
                return NoValue(getattr(expr, "span", None))
            if incoming:
                return self._merge_match_arms(incoming)

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
        is_bool = int_type == self.i1
        self._refuse_char_arms(expr, int_type == ir.IntType(8))
        for arm in expr.arms:
            if (not is_bool and isinstance(arm.pattern, rast.LitPattern)
                    and isinstance(arm.pattern.value, bool)):
                raise EmitError("a `true` or `false` pattern needs a bool scrutinee",
                                arm.pattern.span)
        self._resolve_module_consts(expr)
        self._refuse_pattern_kind(expr, rast.VariantPattern)
        # A name that is an integer `const` compares (§8.2); a float or bool
        # one would bind, and can't (AGAST #2407).
        self._refuse_arm_names(expr, self._is_integer_const)
        gap = match_coverage.bool_gap if is_bool else match_coverage.scalar_gap
        self._require_covered(expr, gap(expr.arms, self.constants))
        values = {name: value for name, (value, _ty) in self.constants.items()}
        self._require_reachable(expr, lambda arms: gap(arms, values),
                                match_coverage.scalar_test(values))

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

        def binds(pattern):
            return (isinstance(pattern, rast.IdentPattern)
                    and pattern.name not in self.constants)

        return self._emit_scalar_arm_bodies(expr, match_val, arm_blocks, merge_block,
                                            binds, self._infer_ritz_type(expr.expr))

    STRING_PATTERN_NEEDS_STRVIEW = "a string pattern needs a StrView scrutinee"

    def _refuse_string_arms(self, expr: rast.Match) -> None:
        """A `"..."` arm compares a StrView, so on anything else it is an error
        at the arm (AGAST #1876). A `*u8` or `String` scrutinee converts first:
        `strview_from_cstr(p)`, `string_as_view(@s)`."""
        for arm in expr.arms:
            pattern = arm.pattern
            if isinstance(pattern, rast.LitPattern) and isinstance(pattern.value, str):
                raise EmitError(self.STRING_PATTERN_NEEDS_STRVIEW,
                                pattern.span or arm.span)

    def _emit_strview_match(self, expr: rast.Match, match_val: ir.Value) -> ir.Value:
        """Emit a match on a StrView with string literal arms (§8.2, AGAST #1876).

        match name
            "html" => 1
            _ => 0

        Each literal arm tests the length, then (only if that is equal, so no
        byte past the end is read) every byte; the arms are tried in order and
        the first catch-all ends the chain. Like an integer, a StrView needs a
        catch-all, and a name never compares here: an integer const tests only
        an integer, so every name binds the StrView. ritz1's twin is
        emit_str_pattern_test in emitter_match.ritz.
        """
        self._refuse_char_arms(expr, False)
        for arm in expr.arms:
            pattern = arm.pattern
            if isinstance(pattern, rast.LitPattern) and not isinstance(pattern.value, str):
                message = self._PATTERN_NEEDS[rast.LitPattern]
                if isinstance(pattern.value, bool):
                    message = "a `true` or `false` pattern needs a bool scrutinee"
                raise EmitError(message, pattern.span or arm.span)
        self._resolve_module_consts(expr)
        self._refuse_pattern_kind(expr, rast.VariantPattern)
        self._refuse_arm_names(expr, lambda name: False)
        self._require_covered(expr, match_coverage.scalar_gap(expr.arms, ()))
        self._require_reachable(expr, lambda arms: match_coverage.scalar_gap(arms, ()),
                                match_coverage.scalar_test({}))

        arm_blocks = [self.current_fn.append_basic_block(f"match.arm.{i}")
                      for i in range(len(expr.arms))]
        merge_block = self.current_fn.append_basic_block("match.merge")
        ptr = self.builder.extract_value(match_val, 0)
        length = self.builder.extract_value(match_val, 1)
        for i, arm in enumerate(expr.arms):
            pattern = arm.pattern
            if not isinstance(pattern, rast.LitPattern):
                # A catch-all; reachability refused any arm after it.
                self.builder.branch(arm_blocks[i])
                break
            data = pattern.value.encode('utf-8')
            nxt = self.current_fn.append_basic_block(f"match.next.{i}")
            same_len = self.builder.icmp_signed(
                '==', length, ir.Constant(length.type, len(data)))
            if not data:
                self.builder.cbranch(same_len, arm_blocks[i], nxt)
            else:
                cmp_block = self.current_fn.append_basic_block(f"match.bytes.{i}")
                self.builder.cbranch(same_len, cmp_block, nxt)
                self.builder.position_at_end(cmp_block)
                equal = None
                for k, byte in enumerate(data):
                    at = self.builder.gep(ptr, [ir.Constant(self.i64, k)])
                    hit = self.builder.icmp_unsigned(
                        '==', self.builder.load(at), ir.Constant(self.i8, byte))
                    equal = hit if equal is None else self.builder.and_(equal, hit)
                self.builder.cbranch(equal, arm_blocks[i], nxt)
            self.builder.position_at_end(nxt)
        else:
            # Coverage demands a catch-all, so this is never reached.
            self.builder.unreachable()

        def binds(pattern):
            return isinstance(pattern, rast.IdentPattern)

        return self._emit_scalar_arm_bodies(expr, match_val, arm_blocks, merge_block,
                                            binds, rast.NamedType(None, 'StrView', []))

    def _emit_scalar_arm_bodies(self, expr: rast.Match, match_val: ir.Value,
                                arm_blocks: list, merge_block, binds,
                                scrut_ritz) -> ir.Value:
        """Emit the arm bodies of an integer or StrView match and merge them.

        The caller has branched to `arm_blocks[i]` when arm i is taken.
        `binds(pattern)` says whether the arm binds the scrutinee to its
        name, which then has Ritz type `scrut_ritz`.
        """
        # Emit each arm body
        arm_values = []
        arm_exit_blocks = []

        for i, (arm, arm_block) in enumerate(zip(expr.arms, arm_blocks)):
            self.builder.position_at_end(arm_block)
            pattern = arm.pattern

            # Bind identifier pattern to the match value
            arm_binds = binds(pattern)
            if arm_binds:
                # Bind the match value to the pattern name for use in the arm body
                self.params[pattern.name] = (match_val, match_val.type)
                # The binding has the scrutinee's Ritz type, so a u32 `n`
                # reads unsigned in the arm (AGAST #3344). No outer name can
                # share it: a local can't rebind one, nor take a global's.
                if scrut_ritz is not None:
                    self.ritz_types[pattern.name] = scrut_ritz

            # Emit the arm body
            # A `return` inside one arm must not leak has_returned past
            # the match — _emit_if saves/restores per branch; matches must
            # too, or the function's trailing expression is skipped and the
            # merge block is left empty and unterminated (AGAST #1321,
            # angelo loader/ttf.ritz). Reset per arm, recombined at merge.
            _saved_arm_returned = self.has_returned
            self.has_returned = False
            arm_val = self._emit_expr_with_expected_enum(
                arm.body, getattr(self, '_expected_enum_name', None))
            self.has_returned = _saved_arm_returned
            self._end_diverging_arm(arm.body)
            self._pin_arm_unsigned(arm_val)  # `n` still bound (AGAST #3344)
            arm_values.append(_PASS_ARM if self._ends_in_pass(arm.body) else arm_val)

            # Check if the arm already terminated (e.g., with return)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_block)
                arm_exit_blocks.append(self.builder.block)
            else:
                arm_exit_blocks.append(None)

            # Clean up bound pattern variable
            if arm_binds:
                del self.params[pattern.name]
                self.ritz_types.pop(pattern.name, None)

        # Position at merge block
        self.builder.position_at_end(merge_block)
        # The function has definitively returned only if *every* arm
        # terminated (nothing reaches the merge block). Otherwise control
        # continues here and later statements/tail must still be emitted.
        if arm_exit_blocks and all(b is None for b in arm_exit_blocks):
            self.has_returned = True

        # Create phi node for the result if arms have values
        arm_values = self._fill_pass_arms(arm_values)
        if arm_values and arm_exit_blocks:
            # Filter out terminated blocks (those that returned)
            incoming = [(val, block) for val, block in zip(arm_values, arm_exit_blocks) if block is not None]
            # A live arm yielding no value (a block ending in a statement,
            # or a unit-typed `?`) makes the match a statement, not a value —
            # it cannot be a phi incoming. Read as one, the NoValue is
            # reported at this match (#1357).
            # AGAST #1321 (angelo hinting interpreter: opcode-dispatch match
            # mixing `self.pop()?` value arms with `self.gs.rp0 = p` tails).
            if any(has_no_value(val) for val, _ in incoming):
                return NoValue(getattr(expr, "span", None))
            # A float-annotated initialiser fixes the merge type (#2027).
            # #2094: unannotated int + float arms are refused if used.
            merged = self._merge_float_arms(expr, incoming) if incoming else None
            if merged is not None:
                return merged
            # Irreconcilable arm types (e.g. an assignment arm yielding its
            # enum value next to a `pass` arm's dummy i32 0) mean nobody can
            # consume this match as a value: it is a statement. Building a
            # phi would put an integer constant into an enum-typed phi —
            # invalid IR (AGAST #1321, angelo font.ritz ensure_cmap).
            # All-integer mixes are fine: they widen below / convert.
            incoming = self._unify_tuple_arms(incoming)  # AGAST #3022
            if incoming and not all(
                    v.type == incoming[0][0].type
                    or (isinstance(v.type, ir.IntType)
                        and isinstance(incoming[0][0].type, ir.IntType))
                    for v, _ in incoming):
                return NoValue(getattr(expr, "span", None))
            if incoming:
                return self._merge_match_arms(incoming)

        # Return a dummy value if no arms produce values
        return ir.Constant(self.i32, 0)
