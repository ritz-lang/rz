"""TypeChecker's questions about types: predicates (`_is_*`), array-length
and literal fit checks, compatibility and promotion, and type spelling.
Split out of type_checker.py to keep it under LARB's file-size limit
(AGAST #3522)."""

import re
from typing import Optional, Tuple

import array_rules
import float_rules
import ritz_ast as rast
from monomorph import mangle_generic_name
from tail_value import slot_tails

_UNSIGNED_INT = re.compile(r"(?<![\w$])u(8|16|32|64|size)(?![\w$])")


def _unsigned_as_signed(key: str) -> str:
    """A _referent_key spelled as LLVM sees it: `u32` and `i32` are one `i32`."""
    return _UNSIGNED_INT.sub(r"i\1", key)


class FloatLitType(rast.NamedType):
    """A float literal's type: f64, unless its context makes it an f32."""

class TypeQueriesMixin:
    """TypeChecker methods that answer questions about types.  Mixed into
    type_checker.TypeChecker; reads its tables (structs, enums, aliases)."""

    @staticmethod
    def _is_null(ty: rast.Type) -> bool:
        return isinstance(ty, rast.NamedType) and ty.name == 'null'

    @staticmethod
    def _is_span(ty: rast.Type) -> bool:
        return isinstance(ty, rast.NamedType) and (
            ty.name == 'Span' or ty.name.startswith('Span$'))

    def _check_array_slot(self, expr: rast.Expr, actual: Optional[rast.Type],
                          slot: Optional[rast.Type]) -> None:
        """A non-literal `[N]T1` fits `[N]T2` only if T1 is T2 (LARB R5). A
        literal takes the slot's element type, and its parts land one by one; its
        length is `_check_literal_length`'s."""
        if (slot is None or actual is None or id(expr) in self._slot_reported
                or isinstance(expr, (rast.ArrayLit, rast.ArrayFill, rast.TupleLit))
                or self._arrays_fit(actual, slot)):
            return
        self._slot_reported.add(id(expr))
        self._slot_error(array_rules.ELEMENT_MISMATCH, expr.span)

    def _check_literal_length(self, expr: rast.Expr, slot: Optional[rast.Type]) -> bool:
        """An array literal or fill must be its `[N]T` slot's N long (LARB R42,
        AGAST #3315): nothing is zero-filled, and a longer one is refused the
        same. Refused at the literal. True if it was. `slot` is resolved."""
        if not (isinstance(expr, (rast.ArrayLit, rast.ArrayFill))
                and isinstance(slot, rast.ArrayType)) or id(expr) in self._slot_reported:
            return False
        have = len(expr.elements) if isinstance(expr, rast.ArrayLit) else expr.count
        have = getattr(have, 'value', have)
        want = getattr(slot.size, 'value', slot.size)
        if not (isinstance(have, int) and isinstance(want, int)) or have == want:
            return False
        self._slot_reported.add(id(expr))
        self._slot_error(array_rules.literal_length(have, self._type_str(slot)), expr.span)
        return True

    def _check_global_literal(self, expr: rast.Expr, slot: Optional[rast.Type]) -> None:
        """A global's initialiser and the literals inside it, against its type:
        the only check a global's value gets here."""
        slot = self._resolve_alias(slot) if slot is not None else None
        while isinstance(expr, rast.Grouped):
            expr = expr.expr
        if self._check_literal_length(expr, slot) or not isinstance(slot, rast.ArrayType):
            return
        parts = (expr.elements if isinstance(expr, rast.ArrayLit)
                 else [expr.value] if isinstance(expr, rast.ArrayFill) else [])
        for part in parts:
            self._check_global_literal(part, slot.inner)

    def _check_local_array_length(self, stmt: rast.Stmt, value: rast.Expr,
                                  actual: Optional[rast.Type],
                                  slot: Optional[rast.Type]) -> None:
        """A non-literal `[M]T` into a local `[N]T`, M not N (AGAST #2090): a
        `let` bound the `[M x T]` value under the `[N]T` name. Refused at the
        statement, in ritz1's words. A literal's length is `_check_literal_length`'s,
        at the literal (LARB R42)."""
        if (slot is None or actual is None or id(value) in self._slot_reported
                or isinstance(value, (rast.ArrayLit, rast.ArrayFill))):
            return
        actual = self._resolve_alias(actual)
        slot = self._resolve_alias(slot)
        if not (isinstance(actual, rast.ArrayType) and isinstance(slot, rast.ArrayType)):
            return
        have = getattr(actual.size, 'value', actual.size)
        want = getattr(slot.size, 'value', slot.size)
        if isinstance(have, int) and isinstance(want, int) and have != want:
            self._slot_reported.add(id(value))
            self._slot_error(array_rules.LENGTH_MISMATCH, stmt.span)

    def _emitter_dispatched(self, receiver: rast.Type,
                            expr: rast.MethodCall) -> Optional[rast.Type]:
        """The type of a method call no declared fn answers but the emitter
        dispatches, which the refusal predicates below leave alone (AGAST
        #4260): `v.len()` on a Vec (_try_emit_len_builtin) is an i64, and a
        `Deref` type's call reaches its target's methods through `Foo_deref`
        (§7.7), typed by the target's own method.  None for anything else."""
        if not isinstance(receiver, rast.NamedType):
            return None
        name = receiver.name.split('$')[0]
        if name == 'Vec' and expr.method == 'len' and not expr.args:
            return rast.NamedType(expr.span, 'i64', [])
        for key in (receiver.name, name):
            if key in self.deref_targets:
                target = self._strip_indirection(self.deref_targets[key][1])
                if not isinstance(target, rast.NamedType):
                    return rast.NamedType(expr.span, 'unknown', [])
                sig = self.functions.get(f"{target.name}_{expr.method}")
                if sig is not None and sig.ret_type is not None:
                    return sig.ret_type
                return rast.NamedType(expr.span, 'unknown', [])
        return None

    def _is_u8(self, ty: rast.Type) -> bool:
        ty = self._resolve_alias(ty)
        return isinstance(ty, rast.NamedType) and ty.name == 'u8' and not ty.args

    def _is_strview(self, ty: rast.Type) -> bool:
        ty = self._resolve_alias(ty)
        return isinstance(ty, rast.NamedType) and ty.name == 'StrView' and not ty.args

    def _is_byte_array(self, ty: rast.Type) -> bool:
        """`[N]u8` / `[N]i8`, or an `@` / `*` of one."""
        ty = self._resolve_alias(ty)
        if isinstance(ty, (rast.PtrType, rast.RefType)):
            ty = self._resolve_alias(ty.inner)
        if not isinstance(ty, rast.ArrayType):
            return False
        elem = self._resolve_alias(ty.inner)
        return isinstance(elem, rast.NamedType) and elem.name in ('u8', 'i8')

    def _arrays_fit(self, actual: rast.Type, slot: rast.Type) -> bool:
        """False if an array in `actual` lands on another element type in `slot`.
        The length is judged elsewhere."""
        actual = self._resolve_alias(actual)
        slot = self._resolve_alias(slot)
        if isinstance(actual, rast.ArrayType) and isinstance(slot, rast.ArrayType):
            return self._same_type(actual.inner, slot.inner)
        if (isinstance(actual, rast.TupleType) and isinstance(slot, rast.TupleType)
                and len(actual.elements) == len(slot.elements)):
            return all(self._arrays_fit(a, s) for a, s in zip(actual.elements, slot.elements))
        return True

    def _same_type(self, a: rast.Type, b: rast.Type) -> bool:
        """`a` and `b` are one type, through aliases and module qualifiers. An
        opaque type can't be judged, so it isn't refused."""
        a = self._resolve_alias(a)
        b = self._resolve_alias(b)
        if self._is_opaque(a) or self._is_opaque(b):
            return True
        if isinstance(a, rast.ArrayType) and isinstance(b, rast.ArrayType):
            return (getattr(a.size, 'value', a.size) == getattr(b.size, 'value', b.size)
                    and self._same_type(a.inner, b.inner))
        if isinstance(a, (rast.PtrType, rast.RefType)) and type(a) is type(b):
            return a.mutable == b.mutable and self._same_type(a.inner, b.inner)
        # `Box<T>` against `Box<i32>`: T is a callee's type parameter, which
        # can't be judged here either (AGAST #4260)
        if (isinstance(a, rast.NamedType) and isinstance(b, rast.NamedType)
                and a.name == b.name and a.args and len(a.args) == len(b.args)):
            return all(self._same_type(x, y) for x, y in zip(a.args, b.args))
        return self._type_str(a) == self._type_str(b)

    # Helper methods

    def _resolve_alias(self, ty: rast.Type) -> rast.Type:
        """Follow `type X = Y`, and drop a module qualifier (`token.Kind`)."""
        seen = set()
        while isinstance(ty, rast.NamedType) and ty.name not in seen:
            seen.add(ty.name)
            qualifier, dot, name = ty.name.rpartition('.')
            if dot and qualifier.rpartition('.')[2] in self.module_names:
                ty = rast.NamedType(ty.span, name, ty.args)
            elif ty.name in self.type_aliases:
                ty = self.type_aliases[ty.name]
            else:
                break
        return ty

    def _is_module_ref(self, expr: rast.Expr) -> bool:
        """An identifier naming an imported module, not a shadowing value."""
        return (isinstance(expr, rast.Ident) and expr.name in self.module_names
                and self._lookup_var(expr.name) is None)

    def _type_receiver_name(self, expr: rast.Expr) -> Optional[str]:
        """The struct or enum a bare receiver identifier names, if any.

        A local shadows the type, a global doesn't (`var String: i32` beside
        `String.from(..)`, as the emitter has it); a type shadows another
        enum's same-named variant (AGAST #3618), which a receiver reaches as
        `Mode.Color`.
        """
        if not isinstance(expr, rast.Ident) or expr.name in self.locals:
            return None
        if expr.name in self.structs or expr.name in self.enums:
            return expr.name
        # `Span.empty()`: the built-in Span, typed by the emitter from its
        # slot (AGAST #3597); its methods are the emitter's.  (A local
        # `Span` returned None above, as in _builtin_type_receiver.)
        if expr.name == 'Span':
            return expr.name
        return None

    def _declares_variant(self, ty: rast.Type, name: str) -> bool:
        """Does the enum under `ty`'s indirection declare a variant `name`?"""
        base = self._strip_indirection(ty)
        if not isinstance(base, rast.NamedType):
            return False
        info = self.enums.get(base.name)
        return info is not None and any(v.name == name for v in info.variants)

    def _strip_indirection(self, ty: rast.Type) -> rast.Type:
        """The type under any pointers, references and aliases."""
        ty = self._resolve_alias(ty)
        while isinstance(ty, (rast.PtrType, rast.RefType)):
            ty = self._resolve_alias(ty.inner)
        return ty

    def _is_type_param(self, ty: rast.Type) -> bool:
        """A generic parameter: declared in scope, or by the single-capital
        convention (a generic struct's field type reaches here unsubstituted)."""
        if not isinstance(ty, rast.NamedType):
            return False
        if ty.name in self.current_type_params:
            return True
        return (len(ty.name) == 1 and ty.name.isupper()
                and ty.name not in self.structs and ty.name not in self.enums
                and ty.name not in self.type_aliases)

    @staticmethod
    def _plain(ty: rast.Type) -> rast.Type:
        """`ty` as a type an instance is made at: a float literal's f64 is
        just f64 there."""
        if isinstance(ty, FloatLitType):
            return rast.NamedType(ty.span, ty.name, list(ty.args))
        return ty

    @staticmethod
    def _is_unknown(ty: Optional[rast.Type]) -> bool:
        return ty is None or (isinstance(ty, rast.NamedType) and ty.name == 'unknown')

    def _is_opaque(self, ty: rast.Type) -> bool:
        """A type that can't be judged: `unknown` was either reported where it
        arose or is outside what this checker infers, and a type parameter
        stands for whatever it is instantiated with."""
        return (isinstance(ty, rast.NamedType) and ty.name in ('unknown', 'Self')) \
            or self._is_type_param(ty)

    def _is_bool_type(self, ty: rast.Type) -> bool:
        """Check if type is bool."""
        ty = self._resolve_alias(ty)
        return isinstance(ty, rast.NamedType) and ty.name == 'bool'

    def _is_integer_type(self, ty: rast.Type) -> bool:
        """Check if type is an integer type."""
        ty = self._resolve_alias(ty)
        if isinstance(ty, rast.NamedType):
            return ty.name in self.INT_TYPES
        return False

    def _is_numeric_type(self, ty: rast.Type) -> bool:
        """Check if type is numeric (integer or float)."""
        ty = self._resolve_alias(ty)
        if isinstance(ty, rast.NamedType):
            return ty.name in self.NUMERIC_TYPES
        return False

    def _is_bool_or_opaque(self, ty: rast.Type) -> bool:
        return self._is_bool_type(ty) or self._is_opaque(self._resolve_alias(ty))

    def _is_raw_ptr(self, ty: rast.Type) -> bool:
        """A `*T`.  This pass types `@x` / `@&x` as a RefType; PtrType's
        `shared` / `mut_ref` marks are monomorph's and the emitter's."""
        return isinstance(self._resolve_alias(ty), rast.PtrType)

    def _is_int_or_opaque(self, ty: rast.Type) -> bool:
        return self._is_integer_type(ty) or self._is_opaque(self._resolve_alias(ty))

    def _is_numeric_or_opaque(self, ty: rast.Type) -> bool:
        return self._is_numeric_type(ty) or self._is_opaque(self._resolve_alias(ty))

    def _check_integer_type(self, ty: rast.Type, span: Optional[rast.Span]):
        """Check that type is an integer, error if not."""
        if not self._is_int_or_opaque(ty):
            self._error(f"expected integer type, got {self._type_str(ty)}", span)

    def _value_fits(self, value: Optional[rast.Expr], actual: rast.Type,
                    expected: rast.Type) -> bool:
        """`value`, of type `actual`, in an `expected` slot. A string literal has
        no fixed type: it is `*u8` in a `*u8` slot (LARB R3) and a `Span<u8>` of
        its bytes in a `Span<u8>` slot (LARB R62, AGAST #3596), and nothing else
        is, so a StrView, a `c"…"` or a String stays a mismatch. An integer
        literal is whichever float its f32 / f64 slot is (§7.5, AGAST #3604), and
        any other integer fits one when exact there (§7.5, AGAST #4113)."""
        if self._type_fits(actual, expected):
            return True
        if value is None:
            return False
        if self._is_vec_range_view(value, actual, expected):
            return True
        tails = list(slot_tails(expected, value))
        if not any(self._is_slot_typed_literal(tail) for tail, _ in tails):
            return False
        return all(self._is_u8_ptr(slot) or self._is_u8_span(slot)
                   if isinstance(tail, rast.StringLit)
                   else (float_rules.int_literal_only(tail) and self._is_float(slot))
                   or self._type_fits(self._tail_type(tail), slot)
                   for tail, slot in tails)

    def _tail_type(self, tail: rast.Expr) -> rast.Type:
        """A tail's type as typed in its own scope: a match arm's binding
        (`n => n`) is out of scope here, so re-inferring it called `n`
        undefined (AGAST #4260).  Inferred afresh only if never typed."""
        ty = self.typed.type_of(tail)
        return ty if ty is not None else self._infer_type(tail)

    def _type_fits(self, actual: rast.Type, expected: rast.Type) -> bool:
        """A value of type `actual` in an `expected` slot: compatible, or an
        integer exact in its float slot (the emitter's _int_into_float_slot)."""
        if self._types_compatible(actual, expected):
            return True
        pair = self._int_into_float(actual, expected)
        return pair is not None and float_rules.is_exact(int(pair[0][1:]), pair[1])

    def _int_into_float(self, actual: rast.Type,
                        expected: rast.Type) -> Optional[Tuple[str, str]]:
        """(integer, float) type names when an integer meets an f32 / f64 slot."""
        actual = self._resolve_alias(actual)
        expected = self._resolve_alias(expected)
        if (isinstance(actual, rast.NamedType) and actual.name in self.INT_TYPES
                and self._is_float(expected)):
            return actual.name, expected.name
        return None

    def _misfit(self, value: Optional[rast.Expr], actual: rast.Type,
                expected: rast.Type, message: str, span: Optional[rast.Span]):
        """Report `value` refused by its slot: an inexact integer into a float
        in the emitter's words, at the value; anything else as `message`."""
        pair = self._int_into_float(actual, expected)
        if pair is not None and value is not None:
            self._error(float_rules.int_into_float_inexact(*pair), value.span)
        else:
            self._error(message, span)

    def _is_u8_span(self, ty: rast.Type) -> bool:
        """`Span<u8>`, or monomorphisation's `Span$u8` spelling of it."""
        ty = self._resolve_alias(ty)
        if not self._is_span(ty):
            return False
        if ty.args:
            return (len(ty.args) == 1 and
                    mangle_generic_name('Span', [self._resolve_alias(ty.args[0])])
                    == 'Span$u8')
        return ty.name == 'Span$u8'

    def _is_vec_range_view(self, value: rast.Expr, actual: rast.Type,
                           expected: rast.Type) -> bool:
        """`v[lo..hi]` of a Vec<T> is a Vec<T> (vec_slice<T>), except in a
        Span<T> slot, where it is a view of v (AGAST #2451)."""
        while isinstance(value, rast.Grouped):
            value = value.expr
        if not (isinstance(value, rast.Index) and isinstance(value.index, rast.Range)):
            return False
        actual = self._resolve_alias(actual)
        expected = self._resolve_alias(expected)
        return (isinstance(actual, rast.NamedType) and actual.name == 'Vec'
                and isinstance(expected, rast.NamedType) and expected.name == 'Span'
                and len(actual.args) == 1 and len(expected.args) == 1
                and self._types_compatible(actual.args[0], expected.args[0]))

    @staticmethod
    def _is_slot_typed_literal(tail: rast.Expr) -> bool:
        """A literal whose type `_value_fits` reads from its slot."""
        return isinstance(tail, rast.StringLit) or float_rules.int_literal_only(tail)

    def _is_float(self, ty: rast.Type) -> bool:
        ty = self._resolve_alias(ty)
        return isinstance(ty, rast.NamedType) and ty.name in ('f32', 'f64')

    @staticmethod
    def _is_u8_ptr(ty: rast.Type) -> bool:
        return (isinstance(ty, rast.PtrType) and isinstance(ty.inner, rast.NamedType)
                and ty.inner.name == 'u8')

    def _types_compatible(self, actual: rast.Type, expected: rast.Type) -> bool:
        """Check if actual type is compatible with expected type."""
        # Handle None/unknown
        if actual is None or expected is None:
            return True

        actual = self._resolve_alias(actual)
        expected = self._resolve_alias(expected)

        # Nothing to judge against, and `null` may instantiate a type parameter
        if self._is_opaque(actual) or self._is_opaque(expected):
            return True

        # `void` (a fn with no return type) and `()` are one unit type (#3594)
        if self._is_unit(actual) and self._is_unit(expected):
            return True

        # A float literal is whichever float its context wants
        for lit, other in ((actual, expected), (expected, actual)):
            if isinstance(lit, FloatLitType) and isinstance(other, rast.NamedType) \
                    and other.name in ('f32', 'f64'):
                return True

        # Null is compatible with any pointer type, a fn pointer included
        # (§5.5: a fn type lowers to an opaque `ptr`; AGAST #3601)
        if isinstance(actual, rast.NamedType) and actual.name == 'null':
            return isinstance(expected, (rast.PtrType, rast.RefType, rast.FnType)) or \
                   (isinstance(expected, rast.NamedType) and expected.name == 'null')

        if isinstance(expected, rast.NamedType) and expected.name == 'null':
            return isinstance(actual, (rast.PtrType, rast.RefType, rast.FnType)) or \
                   (isinstance(actual, rast.NamedType) and actual.name == 'null')

        # Same named type
        if isinstance(actual, rast.NamedType) and isinstance(expected, rast.NamedType):
            if actual.name == expected.name:
                return True
            # Integer literal coercion: i64 literal can be used where smaller int expected
            if actual.name == 'i64' and expected.name in self.INT_TYPES:
                return True
            if actual.name in self.INT_TYPES and expected.name in self.INT_TYPES:
                return True  # Allow integer type coercion for now
            # An f32 widens into an f64 slot implicitly; only the other way
            # needs `as` (LANGUAGE_SPEC §7.5, AGAST #4260)
            if actual.name == 'f32' and expected.name == 'f64':
                return True
            # void compatible with no return
            if actual.name == 'void' or expected.name == 'void':
                return True

        # Pointer-to-integer and integer-to-pointer coercion (common for low-level code)
        if isinstance(actual, (rast.PtrType, rast.RefType)) and isinstance(expected, rast.NamedType):
            if expected.name in {'i64', 'u64'}:
                return True
        if isinstance(actual, rast.NamedType) and isinstance(expected, (rast.PtrType, rast.RefType)):
            if actual.name in {'i64', 'u64'}:
                return True

        # The byte pointer is the way between (LANGUAGE_SPEC, LARB R71): any
        # `*T` or `@T` fits a `*u8`, and a `*u8` fits any `*T` (AGAST #4260)
        if isinstance(expected, rast.PtrType) and (
                (isinstance(actual, (rast.PtrType, rast.RefType)) and self._is_u8(expected.inner))
                or (isinstance(actual, rast.PtrType) and self._is_u8(actual.inner))):
            return True
        # ...and a fn type, which lowers to an opaque `ptr` (§5.5): `*u8` from
        # an `extern fn addr(..) -> *u8` is the way into one
        if isinstance(expected, rast.FnType) and isinstance(actual, rast.PtrType) \
                and self._is_u8(actual.inner):
            return True

        # Pointer types
        if isinstance(actual, rast.PtrType) and isinstance(expected, rast.PtrType):
            return self._types_compatible(actual.inner, expected.inner)

        # Reference types
        if isinstance(actual, rast.RefType) and isinstance(expected, rast.RefType):
            return self._types_compatible(actual.inner, expected.inner)

        # Pointer and reference are compatible for now
        if isinstance(actual, rast.PtrType) and isinstance(expected, rast.RefType):
            return self._types_compatible(actual.inner, expected.inner)
        if isinstance(actual, rast.RefType) and isinstance(expected, rast.PtrType):
            return self._types_compatible(actual.inner, expected.inner)

        # Array types
        if isinstance(actual, rast.ArrayType) and isinstance(expected, rast.ArrayType):
            return self._types_compatible(actual.inner, expected.inner)

        # Tuple types
        if isinstance(actual, rast.TupleType) and isinstance(expected, rast.TupleType):
            if len(actual.elements) != len(expected.elements):
                return False
            return all(self._types_compatible(a, e)
                       for a, e in zip(actual.elements, expected.elements))

        # `[N]u8` / `[N]i8`, bare or `@`, is `StrView { &a[0], N }`, as the
        # emitter lowers it (AGAST #4260, test_ritz1_whole_array's strview_*)
        if self._is_strview(expected) and self._is_byte_array(actual):
            return True

        # `@a` of an array or a Vec views its elements: it fits their Span
        if self._is_span(expected) and self._span_view_fits(actual, expected):
            return True

        # Function pointer types
        if isinstance(actual, rast.FnType) and isinstance(expected, rast.FnType):
            if len(actual.params) != len(expected.params):
                return False
            for i, (a, e) in enumerate(zip(actual.params, expected.params)):
                if self._types_compatible(a, e) and self._arrays_agree(a, e):
                    continue
                # A `name:& T` slot is physically a `*T` (AGAST #3034): it
                # fits a `@T` / `@&T` / `*T` param, as the emitter lowers it
                # (AGAST #4260, test_ritz1_borrow_array's fn_value).
                if i in actual.lent and isinstance(e, (rast.RefType, rast.PtrType)) \
                        and self._types_compatible(a, e.inner) \
                        and self._arrays_agree(a, e.inner):
                    continue
                return False
            return self._types_compatible(actual.ret, expected.ret)

        return False

    def _arrays_agree(self, actual: rast.Type, expected: rast.Type) -> bool:
        """An array a fn's param reads is the array its slot's type passes.

        `_types_compatible`'s array rule takes any length and, through the
        integer coercion, any element width: right for a literal, which is
        whatever array its slot is, but a fn reading a `[2]i32` called through
        a `fn(@[3]i32)` or `fn(@[2]i64)` reads another array as one (AGAST
        #4278). Arrays reached through matching `*` / `@` layers need the same
        length and the same element type; a size still an expression is
        judged elsewhere.
        """
        actual, expected = self._resolve_alias(actual), self._resolve_alias(expected)
        refs = (rast.PtrType, rast.RefType)
        while isinstance(actual, refs) and isinstance(expected, refs):
            actual = self._resolve_alias(actual.inner)
            expected = self._resolve_alias(expected.inner)
        if not (isinstance(actual, rast.ArrayType) and isinstance(expected, rast.ArrayType)):
            return True
        if isinstance(actual.size, int) and isinstance(expected.size, int) \
                and actual.size != expected.size:
            return False
        a, e = self._resolve_alias(actual.inner), self._resolve_alias(expected.inner)
        # `_types_compatible` has checked any type args; the widening rules
        # (i32 into i64, f32 into f64) are for a value, not an element read
        if isinstance(a, rast.NamedType) and isinstance(e, rast.NamedType):
            return a.name == e.name
        return self._arrays_agree(a, e)

    def _promote_numeric_types(self, t1: rast.Type, t2: rast.Type) -> rast.Type:
        """Get the common type for two numeric types."""
        # Simplified: the first type, unless it's a literal the other one fixes,
        # or an f32 meets an f64, which widens it (§7.1, AGAST #3607).
        # Full implementation would return the "wider" type
        if self._mixed_float_widths(t1, t2):
            return rast.NamedType(t1.span, 'f64', [])
        return t2 if isinstance(t1, FloatLitType) else t1

    def _mixed_float_widths(self, t1: rast.Type, t2: rast.Type):
        """(`t1`'s name, `t2`'s) when one is f32 and the other f64, neither a
        literal (a literal takes the other side's type), else None."""
        if isinstance(t1, FloatLitType) or isinstance(t2, FloatLitType):
            return None
        t1, t2 = self._resolve_alias(t1), self._resolve_alias(t2)
        if not (isinstance(t1, rast.NamedType) and isinstance(t2, rast.NamedType)):
            return None
        if {t1.name, t2.name} == {'f32', 'f64'}:
            return t1.name, t2.name
        return None

    def _get_iterator_element_type(self, iter_type: rast.Type) -> rast.Type:
        """Get element type from an iterator type."""
        if isinstance(iter_type, rast.NamedType):
            if iter_type.name == 'Range':
                return rast.NamedType(iter_type.span, 'i64', [])
        resolved = self._resolve_alias(iter_type)
        if isinstance(resolved, rast.ArrayType):
            return resolved.inner
        return rast.NamedType(None, 'unknown', [])

    def _get_type_name(self, ty: rast.Type) -> str:
        """Get the base type name for method lookup."""
        if isinstance(ty, rast.NamedType):
            return ty.name
        elif isinstance(ty, rast.PtrType):
            return self._get_type_name(ty.inner)
        elif isinstance(ty, rast.RefType):
            return self._get_type_name(ty.inner)
        return 'unknown'

    def _type_str(self, ty: Optional[rast.Type]) -> str:
        """Convert type to string for error messages."""
        if ty is None:
            return 'void'
        if isinstance(ty, rast.NamedType):
            if ty.args:
                args = ', '.join(self._type_str(a) for a in ty.args)
                return f"{ty.name}<{args}>"
            return ty.name
        elif isinstance(ty, rast.PtrType):
            return f"*{self._type_str(ty.inner)}"
        elif isinstance(ty, rast.RefType):
            if ty.mutable:
                return f"@&{self._type_str(ty.inner)}"
            return f"@{self._type_str(ty.inner)}"
        elif isinstance(ty, rast.ArrayType):
            return f"[{ty.size}]{self._type_str(ty.inner)}"
        elif isinstance(ty, rast.FnType):
            params = ', '.join(self._type_str(p) for p in ty.params)
            return f"fn({params}) -> {self._type_str(ty.ret)}"
        elif isinstance(ty, rast.TupleType):
            elem_strs = ', '.join(self._type_str(e) for e in ty.elements)
            return f"({elem_strs})"
        return str(ty)
