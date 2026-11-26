"""TypeChecker's slot typing: the return / tail slot an expression fills, and
typing a literal, arm or variant constructor into it (`_infer_into`).  Split
out of type_checker.py to keep it under LARB's file-size limit (AGAST #3522)."""

import copy
from typing import List, Optional

import ritz_ast as rast
from monomorph_core import bind_type_params


class SlotInferMixin:
    """TypeChecker methods that type an expression against the slot it fills.
    Mixed into type_checker.TypeChecker; reads its current fn and tail state."""

    # By-value slots (LANGUAGE_SPEC §13.2, AGAST #2336)

    def _ret_slot(self) -> Optional[rast.Type]:
        return self.current_fn.ret_type if self.current_fn else None

    def _take_tail_slot(self) -> Optional[rast.Type]:
        slot, self._tail_slot = self._tail_slot, None
        return slot

    def _take_discarding(self) -> bool:
        discarding, self._discarding = self._discarding, False
        return discarding

    def _infer_discarded(self, expr: rast.Expr) -> rast.Type:
        """The type of `expr`, whose value is dropped: an expression
        statement, the tail of a unit fn or a loop body, an arm of a dropped
        `if`/`match`.  A dropped `if` or `match` is a statement, and its arms
        needn't agree (AGAST #3593); the emitter never joins them."""
        inner = expr
        while isinstance(inner, rast.Grouped):
            inner = inner.expr
        if isinstance(inner, (rast.If, rast.Match, rast.Block)):
            self._discarding = True
            ty = self._infer_type(inner)
            self._discarding = False
            return ty
        return self._infer_type(expr)

    def _infer_arm(self, body: rast.Expr, slot: Optional[rast.Type],
                   discarded: bool) -> rast.Type:
        """An arm's or branch's value: dropped with its `if`/`match`, or
        landing in the slot that one lands in.  A dropped one is judged as
        any discarded statement (LARB R69, AGAST #3968): a branch of an `if`
        used as a statement, else-less always, or an arm of a `match` used
        as one, is never a value, so a whole array there is refused."""
        if not discarded:
            return self._infer_into(body, slot)
        ty = self._infer_discarded(body)
        self._check_discarded(body, ty)
        return ty

    def _infer_into(self, expr: rast.Expr, slot: Optional[rast.Type]) -> rast.Type:
        """The type of `expr`, whose value lands in a `slot`-typed place.
        `if`, `match` and block tails land there too, each in its own scope,
        as do the parts of a literal the slot types."""
        if isinstance(expr, rast.Grouped):
            return self._infer_into(expr.expr, slot)
        if isinstance(expr, (rast.If, rast.Match, rast.Block)):
            self._tail_slot = slot
            ty = self._infer_type(expr)
            self._tail_slot = None
            return ty
        ty = self._infer_type(expr)
        ty = self._slot_variant_type(expr, ty, slot)
        ty = self._slot_string_type(expr, ty, slot)
        self._check_ref_slot(expr, ty, slot)
        self._check_array_slot(expr, ty, slot)
        self._check_parts(expr, slot)
        if slot is not None and slot is self._ret_slot():
            self._check_array_into_scalar(expr, ty, slot)
            self._check_return(expr)
        self._check_other_referent(expr, ty, slot)
        return ty

    def _slot_variant_type(self, expr: rast.Expr, ty: rast.Type,
                           slot: Optional[rast.Type]) -> rast.Type:
        """A bare variant `V` or `V(..)` in a slot whose enum declares `V` is
        the slot's variant, as the emitter builds it (AGAST #3602):
        variant_to_enum holds the last enum to declare the name, so an
        `enum Display` with a `None` made every `None` Display's.  Option and
        Result are the emitter's own, so their slots declare their variants
        with or without ritzlib's enum in scope.  Anything else keeps `ty`."""
        if isinstance(expr, rast.Ident):
            name = expr.name
        elif isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident):
            name = expr.func.name
        else:
            return ty
        # No local can be named like a variant (AGAST #2407), so the name is
        # the variant.
        if slot is None or name not in self.variant_to_enum:
            return ty
        base = self._resolve_alias(slot)
        if not isinstance(base, rast.NamedType):
            return ty
        builtin = {'Option': ('Some', 'None'), 'Result': ('Ok', 'Err')}
        if name in builtin.get(base.name, ()) or self._declares_variant(base, name):
            return copy.copy(base)
        return ty

    def _slot_string_type(self, expr: rast.Expr, ty: rast.Type,
                          slot: Optional[rast.Type]) -> rast.Type:
        """A `"..."` in a `*u8` slot is still typed `*u8` here (LARB R3), so
        this pass's own slot checks (_check_ref_slot et al.) treat it as
        compatible rather than raising their own, differently-worded
        mismatch: the literal's actual fate is the emitter's
        `_literal_into_slot`, which refuses it outright (AGAST #4694) rather
        than emitting it as one. Anything else keeps `ty`."""
        if not isinstance(expr, rast.StringLit) or slot is None:
            return ty
        base = self._resolve_alias(slot)
        if not (isinstance(base, rast.PtrType) and isinstance(base.inner, rast.NamedType)
                and base.inner.name == 'u8' and not base.inner.args):
            return ty
        ty = rast.PtrType(expr.span, rast.NamedType(expr.span, 'u8', []), mutable=False)
        self.typed.record(expr, ty)
        return ty

    def _check_variant_unambiguous(self, name: str, span: Optional[rast.Span]) -> None:
        """A bare variant two or more concrete user enums declare is an error
        wherever it appears (AGAST #2039), with the emitter's text: the two
        alphabetically-first declarers.  Match arms resolve against the
        scrutinee and don't come here."""
        declarers = self.variant_declarers.get(name, ())
        if len(declarers) >= 2:
            a, b = sorted(declarers)[:2]
            self._error(f"ambiguous enum variant '{name}': declared by enum '{a}' and "
                        f"enum '{b}'; qualify it, e.g. '{a}.{name}'", span)

    def _check_parts(self, expr: rast.Expr, slot: Optional[rast.Type]) -> None:
        """The elements of a literal or the payload of a variant landing in
        `slot`, which says what each part is."""
        slot = self._resolve_alias(slot) if slot is not None else None
        self._check_literal_length(expr, slot)
        if isinstance(expr, rast.ArrayLit) and isinstance(slot, rast.ArrayType):
            for element in expr.elements:
                self._infer_into(element, slot.inner)
        elif isinstance(expr, rast.ArrayFill) and isinstance(slot, rast.ArrayType):
            self._infer_into(expr.value, slot.inner)
        elif isinstance(expr, rast.TupleLit) and isinstance(slot, rast.TupleType):
            for element, part in zip(expr.elements, slot.elements):
                self._infer_into(element, part)
        elif isinstance(slot, rast.NamedType) and slot.name in self.enums:
            if isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident):
                self._check_payload(expr.args, slot.name, expr.func.name)
            elif isinstance(expr, rast.MethodCall):
                self._check_payload(expr.args, slot.name, expr.method)
        elif isinstance(slot, rast.NamedType) and isinstance(expr, rast.Call) \
                and isinstance(expr.func, rast.Ident) and len(expr.args) == 1:
            # The emitter's own Option and Result: the slot names the payload.
            part = {'Some': 0, 'Ok': 0, 'Err': 1}.get(expr.func.name)
            if slot.name in ('Option', 'Result') and part is not None and part < len(slot.args):
                self._infer_into(expr.args[0], slot.args[part])

    def _check_payload(self, args: List[rast.Expr], enum_name: Optional[str],
                       variant: str) -> List[rast.Type]:
        """The arguments of `enum_name`'s `variant`, or of an unknown enum's;
        returns their types."""
        enum = self.enums.get(enum_name) if enum_name else None
        found = next((v for v in enum.variants if v.name == variant), None) if enum else None
        fields = found.fields if found is not None else []
        return [self._infer_into(arg, fields[i] if i < len(fields) else None)
                for i, arg in enumerate(args)]

    def _variant_type(self, expr: rast.Expr, name: str, args: List[rast.Expr],
                      arg_types: List[rast.Type]) -> rast.Type:
        """The type of variant constructor `expr` (`V(args)` or a unit `V`):
        its enum, and for a generic user enum's (AGAST #4057) the instance it
        builds, which monomorph reads (`_infer_variant_let`): the written
        args (`Full<u8>(5)`), else the fn's return type for an untyped let's
        value when that's an instance of the enum (#2430, #2927), else what
        the payload binds (§4.4): `Full(5)` is a `Slot<i64>`.  Unbound, it is
        the bare enum, for monomorph to report located.  A slot whose enum
        declares the variant overrides this (_slot_variant_type)."""
        enum_name = self.variant_to_enum[name]
        bare = rast.NamedType(expr.span, enum_name, [])
        enum = self.enums.get(enum_name)
        # Option / Result are the builtin constructors' (#2430); a variant
        # several enums declare, or named like a fn, is monomorph's to skip.
        if enum is None or not enum.type_params or enum_name in ('Option', 'Result') \
                or self.variant_owners.get(name) != 1 or name in self.functions:
            return bare
        params = enum.type_params
        written = getattr(expr, 'type_args', None)
        if written:
            if len(written) != len(params):
                return bare
            return rast.NamedType(expr.span, enum_name, list(written))
        ret = self._ret_slot()
        if id(expr) in self._untyped_let_values and isinstance(ret, rast.NamedType) \
                and ret.name == enum_name and len(ret.args) == len(params):
            return ret
        variant = next(v for v in enum.variants if v.name == name)
        pairs = [(field, arg, self._binding_type(arg, ty))
                 for field, arg, ty in zip(variant.fields, args, arg_types)]
        bound, conflict = bind_type_params(params, pairs, self._resolve_alias)
        if all(tp in bound and tp not in conflict for tp in params):
            return rast.NamedType(expr.span, enum_name, [bound[tp] for tp in params])
        return bare

    def _binding_type(self, arg: rast.Expr, ty: Optional[rast.Type]) -> Optional[rast.Type]:
        """The type `arg` (typed `ty`) binds a type param as, as monomorph's
        `_type_of` has it: `@x` / `@&x` a pointer, which mangles `ptr_` (the
        emitter's spelling, #2335); a tuple literal, or a name an untyped let
        bound one to, nothing (#3064); None where unknown."""
        while isinstance(arg, rast.Grouped):
            arg = arg.expr
        if isinstance(arg, rast.TupleLit) or (
                isinstance(arg, rast.Ident) and arg.name in self._tuple_lit_names):
            return None
        if isinstance(arg, rast.UnaryOp) and arg.op in ('@', '&', '@&', '&mut'):
            inner = self._binding_type(arg.operand, self.typed.type_of(arg.operand))
            if inner is None:
                return None
            return rast.PtrType(arg.span, inner, mutable=arg.op in ('@&', '&mut'),
                                shared=arg.op == '@')
        return None if self._is_unknown(ty) else self._plain(ty)

    def _note_tuple_lit_let(self, stmt) -> None:
        """Track whether `stmt` binds its name to an untyped tuple literal."""
        value = stmt.value
        while isinstance(value, rast.Grouped):
            value = value.expr
        if stmt.type is None and isinstance(value, rast.TupleLit):
            self._tuple_lit_names.add(stmt.name)
        else:
            self._tuple_lit_names.discard(stmt.name)
