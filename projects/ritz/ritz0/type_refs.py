"""TypeChecker's reference rules: what a `@T`, `@&T` or `*T` may be given
and returned, borrows behind shared references, and references to locals
that outlive them (ref_rules).  Split out of type_checker.py to keep it
under LARB's file-size limit (AGAST #3522)."""

import copy
from typing import Optional

import array_rules
import enum_rules
import ref_rules
import ritz_ast as rast
from monomorph import mangle_generic_name
from type_queries import _unsigned_as_signed

class RefChecksMixin:
    """TypeChecker methods that check references.  Mixed into
    type_checker.TypeChecker; reads its scopes and signatures."""

    def _check_ref_slot(self, expr: rast.Expr, actual: rast.Type,
                        slot: Optional[rast.Type]) -> None:
        """An `@T`, `@&T` or `*T` doesn't fit a by-value `T` slot, and a `T`
        doesn't fit a reference to one. `@a` of an array fits a Span; `a` doesn't."""
        if slot is None or actual is None or id(expr) in self._slot_reported:
            return
        actual = self._resolve_alias(actual)
        slot = self._resolve_alias(slot)
        if isinstance(slot, rast.RefType) and slot.mutable:
            self._check_addr_into_mut(expr)
            self._check_shared_into_mut(expr, actual)
        if isinstance(slot, (rast.PtrType, rast.RefType)):
            self._check_value_into_ref(expr, actual, slot)
            return
        if self._is_span(slot) and isinstance(actual, rast.ArrayType):
            self._report_value_into_ref(expr, slot)
            return
        if self._span_of_other_element(actual, slot):
            self._slot_reported.add(id(expr))
            self._slot_error(array_rules.ELEMENT_MISMATCH, expr.span)
            return
        if not isinstance(actual, (rast.PtrType, rast.RefType)) or self._is_opaque(slot):
            return
        if self._type_str(self._resolve_alias(actual.inner)) != self._type_str(slot):
            return
        self._slot_reported.add(id(expr))
        addr = isinstance(expr, rast.UnaryOp) and expr.op in ('&', '@', '&mut', '@&')
        self._slot_error(ref_rules.ADDR_INTO_VALUE if addr else ref_rules.REF_INTO_VALUE,
                         expr.span)

    def _span_of_other_element(self, actual: rast.Type, slot: rast.Type) -> bool:
        """`@a` with `a: [N]T1` into a `Span<T2>` / `[T2]` slot, T1 not T2
        (AGAST #2781, #2366). The emitter builds `Span { &a[0], N }` from it,
        which views the array at T2's stride: LARB R5's rule for an array
        store holds here too, and converting is a loop you write."""
        if not self._is_span(slot) or not isinstance(actual, (rast.PtrType, rast.RefType)):
            return False
        array = self._resolve_alias(actual.inner)
        if not isinstance(array, rast.ArrayType):
            return False
        held = self._resolve_alias(array.inner)
        return self._span_element_fits(mangle_generic_name('Span', [held]),
                                       held, slot) is False

    def _span_view_fits(self, actual: rast.Type, slot: rast.Type) -> bool:
        """`@a` / `@&a` of an array or a Vec into a `Span<T>` slot: a view of
        its elements, which the emitter builds as `Span { ptr, len }` (§13,
        AGAST #3595). Its element must be T; `a` itself is a value and
        doesn't fit, nor does another generic struct."""
        if not isinstance(actual, rast.RefType):
            return False
        held = self._resolve_alias(actual.inner)
        if isinstance(held, rast.ArrayType):
            elem = self._resolve_alias(held.inner)
            view = mangle_generic_name('Span', [elem])
        elif isinstance(held, rast.NamedType) and held.name == 'Vec' and len(held.args) == 1:
            elem = self._resolve_alias(held.args[0])
            view = mangle_generic_name('Span', [elem])
        elif isinstance(held, rast.NamedType) and held.name.startswith('Vec$'):
            elem = None                 # monomorphised: `Vec$T` names its element
            view = 'Span$' + held.name.split('$', 1)[1]
        else:
            return False
        return self._span_element_fits(view, elem, slot) is not False

    def _span_element_fits(self, view: str, elem: Optional[rast.Type],
                           slot: rast.Type) -> Optional[bool]:
        """Is `view` (the Span a reference's elements make, spelled `Span$T1`)
        the `slot`'s Span? None when either element is opaque (a type
        parameter, `unknown`): nothing to judge."""
        if elem is not None and self._is_opaque(self._resolve_alias(elem)):
            return None
        # Monomorphisation has spelled the slot `Span$T`: spell T1 the same way.
        if slot.args:
            if len(slot.args) != 1 or self._is_opaque(self._resolve_alias(slot.args[0])):
                return None
            slot_name = mangle_generic_name('Span', slot.args)
        else:
            slot_name = slot.name
        return slot_name == view

    def _check_value_into_ref(self, expr: rast.Expr, actual: rast.Type,
                              slot: rast.Type) -> None:
        """A `T` doesn't fit an `@T`, `@&T` or `*T`: a reference is written.

        Nothing but a reference fits an `@T` or `@&T`, and nothing but a pointer
        a `*T` for a `:&` param, which is a `T` too. A plain integer into `*U`
        of another `U` is a pointer as an integer, a different question.
        """
        inner = self._resolve_alias(slot.inner)
        if self._is_opaque(inner) or self._is_opaque(actual):
            return
        same = self._type_str(inner) == self._type_str(actual)
        pointer = isinstance(actual, (rast.PtrType, rast.RefType))
        if pointer and isinstance(slot, rast.RefType) and isinstance(inner, rast.PtrType):
            held = self._resolve_alias(actual.inner)
            if isinstance(held, rast.PtrType) and self._type_str(held) != self._type_str(inner):
                self._slot_reported.add(id(expr))
                self._slot_error(ref_rules.REF_TO_OTHER_POINTER, expr.span)
                return
        if not same and (pointer or self._is_null(actual)):
            return
        lent = (isinstance(expr, rast.Ident) and expr.name in self.lent_locals
                and self._lookup_var(expr.name) is self.lent_locals[expr.name])
        if same or lent or isinstance(slot, rast.RefType):
            self._report_value_into_ref(expr, slot)
        elif isinstance(actual, rast.ArrayType):
            # A whole array into a `*U` of anything but itself (#2392): ritz1's
            # emitter refuses it at the array, in its words. Into an `@U`, or
            # from a `:&` param, it's the value-into-reference error above, as
            # it is in ritz1. Into a `*U` of a non-array U, `@a` is refused
            # too, so the words name `@a[0]` (#3054), as ritz1's ref_check.
            self._slot_reported.add(id(expr))
            message = (array_rules.WHOLE_ARRAY_NOT_A_VALUE if isinstance(inner, rast.ArrayType)
                       else array_rules.WHOLE_ARRAY_INTO_POINTER)
            self._slot_error(message, expr.span)

    @staticmethod
    def _is_void(ty: rast.Type) -> bool:
        return isinstance(ty, rast.NamedType) and ty.name == 'void' and not ty.args

    @classmethod
    def _is_unit(cls, ty: rast.Type) -> bool:
        """`void` or `()`: the one unit type, spelled two ways."""
        return cls._is_void(ty) or (isinstance(ty, rast.TupleType) and not ty.elements)

    def _check_discarded(self, expr: rast.Expr, actual: Optional[rast.Type]) -> None:
        """A whole array alone as a statement, or a void fn's tail: a `[N]T`
        local, an `a:& [N]T` param, an array field or `*p` of a `*[N]T`
        (AGAST #3189). It does nothing; ritz1 refuses it at the array in
        #2287's words, and so does ritz0. A call returning an array is a
        call, and its value may be dropped."""
        place = expr
        while isinstance(place, rast.Grouped):
            place = place.expr
        if not (isinstance(place, (rast.Ident, rast.Field))
                or (isinstance(place, rast.UnaryOp) and place.op == '*')):
            return
        if actual is not None and isinstance(self._resolve_alias(actual), rast.ArrayType):
            self._slot_error(array_rules.WHOLE_ARRAY_NOT_A_VALUE, place.span, after_moves=True)

    def _check_array_into_scalar(self, expr: rast.Expr, actual: Optional[rast.Type],
                                 slot: Optional[rast.Type]) -> None:
        """A whole array, literal or named, returned from a number or bool fn
        or cast to one (AGAST #3187, #3190). The emitter wrote a `ret [N x T]`
        in a scalar fn, which clang rejects; ritz1 refuses it at the array.
        Only these two sites: a `let`/`var`/assign/argument already refuses it
        as a store mismatch, and a pointer, reference or Span slot has its own
        rule (_check_value_into_ref)."""
        if slot is None or actual is None or id(expr) in self._slot_reported:
            return
        if isinstance(self._resolve_alias(actual), rast.ArrayType) and (
                self._is_numeric_type(slot) or self._is_bool_type(slot)):
            self._slot_reported.add(id(expr))
            self._slot_error(array_rules.WHOLE_ARRAY_NOT_A_VALUE, expr.span)

    def _check_cast_to_ref(self, cast: rast.Cast, source: Optional[rast.Type]) -> None:
        """`c as @&C`, `c as @C` or `c as *C` with `c` a struct or array value,
        a `:&` param's included (AGAST #2370): a cast isn't a borrow, so it's
        the bare form's error, as ritz1's ref_cast_value_to_ref. An integer
        source is the integer-to-pointer cast and stays; a string literal is a
        `*u8` already, and a StrView or String into a `*T` has LARB R3's own
        words (the emitter's _STR_AS_PTR, AGAST #2341)."""
        target = self._resolve_alias(cast.target)
        if source is None or not isinstance(target, (rast.PtrType, rast.RefType)):
            return
        operand = cast.expr
        while isinstance(operand, rast.Grouped):
            operand = operand.expr
        if isinstance(operand, rast.StringLit) or id(operand) in self._slot_reported:
            return
        source = self._resolve_alias(source)
        if isinstance(target, rast.PtrType) and isinstance(source, rast.NamedType) \
                and source.name in ('StrView', 'String'):
            return
        if isinstance(source, rast.ArrayType) or self._is_struct(source):
            self._report_value_into_ref(operand, target)

    def _check_int_as_enum(self, cast: rast.Cast, source: Optional[rast.Type]) -> None:
        """`n as E` with `n` an integer, for any enum `E`: fieldless, with a
        representation type, or carrying data (LARB R19, AGAST #3040). An
        integer may name no variant, so it's refused at the `as`; the way in
        is a `match`. A slot error, so it's reported on every compile and
        stops emission, which crashed on a data enum. `e as U` is §10.4's
        enum-to-integer and isn't judged here."""
        if source is None or not self._is_integer_type(source):
            return
        target = self._resolve_alias(cast.target)
        if not isinstance(target, rast.NamedType) or target.name not in self.enums:
            return
        self._slot_error(enum_rules.int_as_enum(target.name), cast.as_span or cast.span)

    def _check_other_referent(self, expr: rast.Expr, actual: Optional[rast.Type],
                              slot: Optional[rast.Type]) -> None:
        """`@x` or `@&x` lands in an `@U`, `@&U` or `*U` of another `U`: the
        reference would be reinterpreted. Exactly the same type, not the same
        width (Aaron's ruling on AGAST #2368). After the return check, as
        ritz1's ref_into does, so a reference to a local says that first.
        A `*T` value into a `*U` is _check_other_pointee's (LARB R71)."""
        if slot is None or actual is None:
            return
        if not self._is_written_ref(expr):
            self._check_other_pointee(expr, actual, slot)
            return
        actual = self._resolve_alias(actual)
        slot = self._resolve_alias(slot)
        if not isinstance(slot, (rast.PtrType, rast.RefType)) \
                or not isinstance(actual, (rast.PtrType, rast.RefType)):
            return
        # A struct for another struct at a call is #1948's "argument N of `f`
        # has the wrong type", which ritz1 says too; this doesn't pre-empt it.
        if self._arg_depth and self._is_struct(actual.inner) and self._is_struct(slot.inner):
            return
        # `@&h` of a `*C` into `@&*D` was REF_TO_OTHER_POINTER, said first.
        if self._other_referent(actual.inner, slot.inner):
            self._report_once(expr, ref_rules.REF_TO_OTHER_TYPE)

    def _check_other_pointee(self, expr: rast.Expr, actual: rast.Type,
                             slot: rast.Type) -> None:
        """A pointer or reference value, not a written `@x`, lands in a
        pointer or reference slot of another pointee (LARB R71): `*[4]i32`
        into `*[3]i32`, `*C` into `*D`, `@T` into `@U`. The byte pointer is
        the way between: a `*T` or `@T` fits a `*u8`, and a `*u8` fits any
        `*T`. `null` is no pointer type here, so it fits. What the checker
        can't name (opaque, generic) stays unjudged."""
        actual = self._resolve_alias(actual)
        slot = self._resolve_alias(slot)
        if not isinstance(slot, (rast.PtrType, rast.RefType)) \
                or not isinstance(actual, (rast.PtrType, rast.RefType)):
            return
        if isinstance(slot, rast.PtrType) and (
                self._is_byte(slot.inner)
                or (isinstance(actual, rast.PtrType) and self._is_byte(actual.inner))):
            return
        # A struct for another struct at a call is #1948's "argument N of `f`
        # has the wrong type", as for `@x` (_check_other_referent).
        if self._arg_depth and self._is_struct(actual.inner) and self._is_struct(slot.inner):
            return
        if not self._other_referent(actual.inner, slot.inner):
            return
        # Into an `@U` or `@&U` param, a pointee of another LLVM type (`@i32`
        # into `@[2]i32`) is #1948's words too: the emitter compares the
        # pointer types, and ritz1 refuses it the same way. Left to R71 is
        # what passes that: a pointee differing only in an integer's sign.
        if self._arg_depth and isinstance(slot, rast.RefType) and _unsigned_as_signed(
                self._referent_key(actual.inner)) != _unsigned_as_signed(
                self._referent_key(slot.inner)):
            return
        self._report_once(expr, ref_rules.REF_TO_OTHER_TYPE)

    def _is_byte(self, ty: rast.Type) -> bool:
        ty = self._resolve_alias(ty)
        return isinstance(ty, rast.NamedType) and ty.name == 'u8' and not ty.args

    def _check_lent_referent(self, arg: rast.Expr, actual: Optional[rast.Type],
                             referent: rast.Type) -> None:
        """`@x` or `@&x` goes to a `name:& T` param, whose referent is `referent`:
        of another type, it would be reinterpreted (#2367, #2368). A bare place
        is the emitter's "argument N has the wrong type"."""
        if actual is None or not self._is_written_ref(arg):
            return
        actual = self._resolve_alias(actual)
        if isinstance(actual, (rast.PtrType, rast.RefType)) \
                and self._other_referent(actual.inner, referent):
            self._report_once(arg, ref_rules.REF_TO_OTHER_TYPE)

    def _is_struct(self, ty: rast.Type) -> bool:
        ty = self._resolve_alias(ty)
        return isinstance(ty, rast.NamedType) and self._referent_key(ty) is not None \
            and (ty.args != [] or ty.name in self.structs or '$' in ty.name)

    def _other_referent(self, held: rast.Type, inner: rast.Type) -> bool:
        """`held` is known not to be `inner`: exactly, not by width. What the
        checker can't name stays unjudged."""
        a, b = self._referent_key(held), self._referent_key(inner)
        return a is not None and b is not None and a != b

    def _referent_key(self, ty: rast.Type) -> Optional[str]:
        """`ty` spelled one way, whatever its aliases, with a generic struct as
        monomorphisation names it (`Box<i32>` is `Box$i32`). A pointer inside is
        `*` whatever its kind: `@T` fits `*T`, so `@@C` fits `**C`. None if any
        part of it is opaque or a type this doesn't spell."""
        ty = self._resolve_alias(ty)
        if ty is None or self._is_opaque(ty):
            return None
        if isinstance(ty, (rast.PtrType, rast.RefType)):
            inner = self._referent_key(ty.inner)
            return None if inner is None else f"*{inner}"
        if isinstance(ty, rast.ArrayType):
            inner = self._referent_key(ty.inner)
            size = ty.size.value if isinstance(ty.size, rast.IntLit) else ty.size
            if inner is None or not isinstance(size, int):
                return None
            return f"[{size}]{inner}"
        if isinstance(ty, rast.TupleType):
            parts = [self._referent_key(part) for part in ty.elements]
            return None if None in parts else f"({', '.join(parts)})"
        if not isinstance(ty, rast.NamedType):
            return None
        if ty.args:
            if any(self._referent_key(arg) is None for arg in ty.args):
                return None
            return mangle_generic_name(ty.name, ty.args)
        return ty.name

    @staticmethod
    def _is_written_ref(expr: rast.Expr) -> bool:
        """`@x` or `@&x`, written where the slot is."""
        while isinstance(expr, rast.Grouped):
            expr = expr.expr
        return isinstance(expr, rast.UnaryOp) and expr.op in ('&', '@', '&mut', '@&')

    def _report_value_into_ref(self, expr: rast.Expr, slot: rast.Type) -> None:
        self._slot_reported.add(id(expr))
        mutable = isinstance(slot, rast.RefType) and slot.mutable
        self._slot_error(ref_rules.VALUE_INTO_MUT_REF if mutable
                         else ref_rules.VALUE_INTO_SHARED_REF, expr.span)

    # `@T` is read-only (LANGUAGE_SPEC §3.2, §13.3, AGAST #2338)

    def _quiet_type(self, expr: rast.Expr) -> rast.Type:
        """The type of `expr`, which has already had its say."""
        mark = len(self.errors)
        ty = self._infer_type(expr)
        del self.errors[mark:]
        return self._resolve_alias(ty)

    def _check_write(self, target: rast.Expr) -> None:
        """`target` is written."""
        self._forget_local_ref(target)
        if self._behind_shared(target):
            self._report_once(target, ref_rules.WRITE_THROUGH_SHARED)

    def _report_once(self, expr: rast.Expr, message: str) -> None:
        if id(expr) not in self._slot_reported:
            self._slot_reported.add(id(expr))
            self._slot_error(message, expr.span)

    def _behind_shared(self, target: rast.Expr) -> bool:
        """Walk the place `target` from itself to its root: an `@T` on the way
        means it's read-only, whatever is behind it, and a `*T` ends the walk,
        since what it points at is the pointer's business. So is anything the
        checker can't type, which stays unjudged."""
        place = target
        while True:
            if isinstance(place, rast.Grouped):
                place = place.expr
                continue
            if isinstance(place, (rast.Field, rast.Index)):
                base = place.expr
            elif isinstance(place, rast.UnaryOp) and place.op == '*':
                base = place.operand
            else:
                return False
            ty = self._quiet_type(base)
            # `.` reads through every level, so the one nearest the place counts.
            while isinstance(place, rast.Field) and isinstance(ty, (rast.PtrType, rast.RefType)) \
                    and isinstance(self._resolve_alias(ty.inner), (rast.PtrType, rast.RefType)):
                ty = self._resolve_alias(ty.inner)
            if isinstance(ty, rast.RefType) and not ty.mutable:
                return True
            if isinstance(ty, rast.PtrType) or self._is_opaque(ty):
                return False
            place = base

    def _as_let(self, ty: rast.Type) -> rast.Type:
        """`ty`, for a `let` to hold."""
        held = copy.copy(ty)
        self._let_types.append(held)
        return held

    def _own_storage(self, place: rast.Expr) -> Optional[str]:
        """The local whose own storage `place` is, reached with no pointer or
        reference on the path."""
        if isinstance(place, rast.Grouped):
            return self._own_storage(place.expr)
        if isinstance(place, rast.Ident):
            return place.name if place.name in self.locals else None
        if isinstance(place, (rast.Field, rast.Index)):
            if isinstance(place, rast.Index) and isinstance(place.index, rast.Range):
                return None
            base = self._quiet_type(place.expr)
            if isinstance(base, rast.ArrayType if isinstance(place, rast.Index)
                          else (rast.NamedType, rast.TupleType)) and not self._is_opaque(base):
                return self._own_storage(place.expr)
        return None

    def _is_let(self, name: str) -> bool:
        held = self.locals.get(name)
        return any(held is ty for ty in self._let_types)

    def _let_root(self, place: rast.Expr) -> Optional[str]:
        """The `let` whose own storage `place` is. The emitter's _let_place, ahead
        of LLVM types."""
        name = self._own_storage(place)
        return name if name is not None and self._is_let(name) else None

    def _check_addr_into_mut(self, expr: rast.Expr) -> None:
        """`expr` lands in an `@&T` or a `:&` param, which `@x` never does. Of a
        `let`, or of a place behind an `@T`, `@&x` wouldn't do either, so those
        say what would."""
        if isinstance(expr, rast.UnaryOp) and expr.op in ('&', '@'):
            name = self._let_root(expr.operand)
            if name is not None:
                self._report_once(expr, ref_rules.let_into_mut(name))
            elif self._behind_shared(expr.operand):
                self._report_once(expr, ref_rules.BORROW_THROUGH_SHARED)
            else:
                self._report_once(expr, ref_rules.ADDR_INTO_MUT)

    # An `@T` doesn't become an `@&T` (LANGUAGE_SPEC §3.2, §13.3, AGAST #2374)

    def _check_borrow(self, expr: rast.UnaryOp) -> None:
        """`expr` is a mutable borrow of its operand."""
        if self._behind_shared(expr.operand):
            self._report_once(expr, ref_rules.BORROW_THROUGH_SHARED)

    def _check_shared_into_mut(self, expr: rast.Expr, actual: rast.Type) -> None:
        """`expr`, of type `actual`, lands in an `@&T`. `@x` is
        _check_addr_into_mut's. An `@&T` reached through an `@T`, as `h.m` of
        `h: @H` is, is read-only too (#2381): what `expr` points at is walked."""
        written = isinstance(expr, rast.UnaryOp) and expr.op in ('&', '@')
        if not isinstance(actual, rast.RefType) or written:
            return
        if not actual.mutable or self._behind_shared(rast.UnaryOp(expr.span, '*', expr)):
            self._report_once(expr, ref_rules.SHARED_INTO_MUT)

    def _check_receiver(self, expr: rast.MethodCall, sig) -> None:
        """A method taking `self: @&T` writes what its receiver reaches, as
        `recv.f = v` would: `.` finds the receiver the same way. A standalone
        function takes it as its first param, whatever that's called."""
        if not sig.params:
            return
        slot = self._resolve_alias(sig.params[0][1])
        mutable = 0 in sig.lent or (isinstance(slot, rast.RefType) and slot.mutable)
        if mutable and self._behind_shared(rast.Field(expr.span, expr.expr, expr.method)):
            self._report_once(expr.expr, ref_rules.SHARED_INTO_MUT)

    # A reference to a local doesn't leave its fn (LANGUAGE_SPEC §13.5, LARB ruling
    # R2, AGAST #2340). A check for the definite case: what can't be told stays
    # unjudged. ritz1's twins are in ref_check.ritz, and
    # ritz0/test_return_local_ref.py holds all three compilers to them.

    def _local_root(self, place: rast.Expr) -> Optional[str]:
        """The local root `place` is in: its own storage, and not the caller's,
        which a `:&` param is. A by-value `self` is a local root (#2393)."""
        name = self._own_storage(place)
        if name is None:
            return None
        held = self.locals[name]
        if held is self.lent_locals.get(name):
            return None
        return name

    def _referent(self, expr: rast.Expr) -> Optional[str]:
        """The local root `expr` definitely refers to: `@x` of one, or a binding
        that holds such a reference."""
        if isinstance(expr, rast.Grouped):
            return self._referent(expr.expr)
        if isinstance(expr, rast.UnaryOp) and expr.op in ('&', '@', '&mut', '@&'):
            return self._local_root(expr.operand)
        if isinstance(expr, rast.Index) and isinstance(expr.index, rast.Range):
            # `v[a..b]` of a Vec or String: in a Span slot, a view of v (LARB
            # R57); elsewhere a copy, which no reference slot takes. A Span's
            # slice views what the Span does: a param's is the caller's.
            base = self._quiet_type(expr.expr)
            if isinstance(base, rast.NamedType) and (
                    base.name in ('Vec', 'String') or base.name.startswith('Vec$')):
                return self._local_root(expr.expr)
            return None
        if not isinstance(expr, rast.Ident):
            return None
        held = self._local_refs.get(id(self.locals.get(expr.name)))
        if held is None:
            return None
        _, root, depth = held
        # A loop can reach a `var`'s later write before this read.
        return root if self._is_let(expr.name) or self._loop_depth <= depth else None

    def _note_local_ref(self, name: str, root: Optional[str]) -> None:
        """`name` was just bound to a reference to `root`, if there's a root."""
        held = self.locals[name]
        if root is not None and self._is_ref_slot(held):
            self._local_refs[id(held)] = (held, root, self._loop_depth)

    def _is_ref_slot(self, slot: Optional[rast.Type]) -> bool:
        """Does `slot` hold a reference for R2: a pointer, a reference, or a
        Span, a view (LARB R57)?"""
        held = self._resolve_alias(slot) if slot is not None else None
        return isinstance(held, (rast.PtrType, rast.RefType)) or (
            held is not None and self._is_span(held))

    def _forget_local_ref(self, place: rast.Expr) -> None:
        """`place` is written, or its address may let it be: if it's a `var`, what
        it holds is no longer definite."""
        if isinstance(place, rast.Grouped):
            self._forget_local_ref(place.expr)
        elif isinstance(place, rast.Ident) and not self._is_let(place.name):
            self._local_refs.pop(id(self.locals.get(place.name)), None)

    def _gives_referent(self, arg: rast.Expr, lent: bool, pointee: rast.Type) -> Optional[str]:
        """The local root `arg` refers to, if it has pointee `pointee`. A `:&`
        param or a receiver borrows `arg` itself when it's that `T`."""
        ty = self._quiet_type(arg)
        root = self._referent(arg)
        if root is not None and isinstance(ty, (rast.PtrType, rast.RefType)):
            ty = self._resolve_alias(ty.inner)
        elif lent:
            root = self._local_root(arg)
        wanted = self._resolve_alias(pointee)
        if root is None or self._is_opaque(ty) or self._is_opaque(wanted) \
                or self._type_str(ty) != self._type_str(wanted):
            return None
        return root

    def _call_referent(self, call: rast.Expr) -> Optional[str]:
        """The local root a call returning `@U` or `@&U` was given a reference to,
        with pointee `U`: the result may be that reference, so a raw `*U` return,
        which no reference has to live through, isn't asked."""
        callee = self._callees.get(id(call))
        ret = self._resolve_alias(callee[0].ret_type) if callee and callee[0].ret_type else None
        if not isinstance(ret, rast.RefType):
            return None
        sig, skip = callee
        given = [(arg, i + skip in sig.lent) for i, arg in enumerate(call.args)]
        if isinstance(call, rast.MethodCall):
            given.insert(0, (call.expr, True))
        roots = (self._gives_referent(arg, lent, ret.inner) for arg, lent in given)
        return next((root for root in roots if root is not None), None)

    def _check_return(self, expr: rast.Expr) -> None:
        """`expr` is a return value or a tail of one."""
        root = self._referent(expr)
        if root is None and isinstance(expr, (rast.Call, rast.MethodCall)):
            root = self._call_referent(expr)
        if root is not None and self._is_ref_slot(self._ret_slot()):
            self._report_once(expr, ref_rules.returns_local(root))
