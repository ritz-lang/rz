"""Type-argument inference for generic calls, struct literals and variant
constructors (AGAST #1982, #3407): the Monomorphizer's inference half, split
out of monomorph.py to keep it under LARB's file-size limit (AGAST #3522)."""

import copy
import dataclasses
from typing import Dict, List, Optional

import ritz_ast as rast
from monomorph_core import (GenericInferError, TypeSubstitution, _names_type_param,
                            bind_type_params, resolve_alias)


def _at(ty: rast.Type, span) -> rast.Type:
    """A copy of inferred type arg `ty`, located at the call or literal it
    was inferred for: nothing wrote it, so an error about it (a failed trait
    bound, §11.5) is reported there."""
    ty = copy.deepcopy(ty)
    ty.span = span
    return ty

class MonoInferMixin:
    """Monomorphizer methods that fill in omitted type args before instances are
    collected.  Mixed into monomorph.Monomorphizer; reads its state."""

    # ------------------------------------------------------------------
    # Type-argument inference for generic calls (AGAST #1982)
    # ------------------------------------------------------------------

    def _infer_call_type_args(self, module: rast.Module) -> None:
        """Fill in the type args of every `f(args)` call to a generic `f`.

        Every fn body is walked, generic ones too: in `fn g<T>(x: T)` a call
        `f(x)` becomes `f<T>(x)`, and specialising g substitutes T as it does
        for a spelled-out call.  Calls are inferred inside-out, so `f(g(x))`
        knows g's instance before it types f's argument.
        """
        for item in module.items:
            if isinstance(item, rast.FnDef):
                self._infer_in_fn(item, None)
            elif isinstance(item, rast.ImplBlock):
                for method in item.methods:
                    self._infer_in_fn(method, item.type_name, item.type_params)

    def _infer_in_fn(self, fn: rast.FnDef, impl_type_name: Optional[str],
                     impl_type_params: Optional[List[str]] = None) -> None:
        if fn.body is None:
            return
        self.var_types = {}
        self._tuple_lit_names = set()
        self._infer_ret_type = fn.ret_type
        # The slot each args-less generic struct literal fills, by id (§9.2):
        # filled top-down here and by _mark_lit_slots, read by
        # _infer_struct_lit_args.  The fn's tail is the return type's slot.
        self._lit_slots: Dict[int, rast.Type] = {}
        self._mark_lit_slot(fn.body, fn.ret_type)
        for param in fn.params:
            param_type = param.type
            if param_type is None and param.name == 'self' and impl_type_name:
                args = [rast.NamedType(fn.span, tp, []) for tp in (impl_type_params or [])]
                param_type = rast.NamedType(fn.span, impl_type_name, args)
            if param_type is not None:
                self.var_types[param.name] = param_type
        self._infer_walk(fn.body)
        self.var_types = {}
        self._tuple_lit_names = set()

    def _infer_walk(self, node) -> None:
        """Visit `node` in source order: a let's value before its name is
        typed, a call's arguments before the call.  A struct literal's
        fields are `(name, value)` tuples: walked too, so `S { v: id(3) }`
        infers id<i64> and a nested literal its args (§9.2, #3407)."""
        if isinstance(node, (list, tuple)):
            for child in node:
                self._infer_walk(child)
            return
        if not dataclasses.is_dataclass(node) or isinstance(node, type):
            return
        if isinstance(node, rast.Type):
            return
        # Slots before the values that fill them (§9.2): a literal's slot
        # decides its args before its fields are walked, so a nested literal
        # in one of its fields has a slot too.
        self._mark_lit_slots(node)
        if isinstance(node, rast.StructLit):
            self._struct_lit_from_slot(node)
            self._mark_field_slots(node)
        for f in dataclasses.fields(node):
            if f.name == 'span':
                continue
            self._infer_walk(getattr(node, f.name))
        if isinstance(node, (rast.LetStmt, rast.VarStmt)):
            self._note_tuple_lit_let(node)
            if node.type is None and node.value is not None:
                node.type = self._infer_variant_let(node.value)
            if node.type is not None:
                self.var_types[node.name] = node.type
            elif node.value is not None:
                inferred = self._type_of(node.value)
                if inferred is not None:
                    self.var_types[node.name] = inferred
        elif isinstance(node, rast.Call):
            self._infer_one_call(node)
        elif isinstance(node, rast.StructLit):
            self._infer_struct_lit_args(node)
        elif isinstance(node, rast.Match) and node.ctor_type is None:
            node.ctor_type = self._infer_variant_scrutinee(node.expr)

    def _argless_struct(self, lit: rast.StructLit):
        """(type params, [(field, type)]) of the generic struct an args-less
        literal names, or None when it names a plain struct or has its args.

        The built-in `Span<T>` counts when nothing declares or imports a
        `Span` (AGAST #3357): with no `import ritzlib.span` it isn't in
        generic_structs, and the emitter raised a ValueError."""
        if lit.type_args:
            return None
        struct_def = self.generic_structs.get(lit.name)
        if struct_def is not None:
            return struct_def.type_params, struct_def.fields
        if lit.name == 'Span' and 'Span' not in self.struct_defs:
            # ritzlib/span.ritz's fields.
            t = rast.NamedType(lit.span, 'T', [])
            return ['T'], [('ptr', rast.PtrType(lit.span, t, False)),
                           ('len', rast.NamedType(lit.span, 'i64', []))]
        return None

    def _mark_lit_slot(self, expr, ty: Optional[rast.Type]) -> None:
        """Record `ty` as the slot of the literal `expr` is, or ends in: a
        block's tail, each branch of an `if` / `match` (§9.2)."""
        if expr is None or ty is None:
            return
        if isinstance(expr, (rast.Grouped, rast.Block)):
            self._mark_lit_slot(expr.expr, ty)
        elif isinstance(expr, rast.If):
            self._mark_lit_slot(expr.then_block, ty)
            self._mark_lit_slot(expr.else_block, ty)
        elif isinstance(expr, rast.Match):
            for arm in expr.arms:
                self._mark_lit_slot(arm.body, ty)
        elif isinstance(expr, rast.StructLit):
            self._lit_slots[id(expr)] = ty

    def _mark_lit_slots(self, node) -> None:
        """The slots `node` gives its values (§9.2): a typed let / var's, a
        `return`'s (the fn's return type), a call's parameters."""
        if isinstance(node, (rast.LetStmt, rast.VarStmt)) and node.type is not None:
            self._mark_lit_slot(node.value, node.type)
        elif isinstance(node, rast.ReturnStmt):
            self._mark_lit_slot(node.value, self._infer_ret_type)
        elif isinstance(node, rast.Call) and isinstance(node.func, rast.Ident) \
                and node.func.name not in self.var_types:
            fn_def = self.fn_signatures.get(node.func.name)
            params = list(fn_def.params) if fn_def is not None else []
            subst = None
            generic = self.generic_functions.get(node.func.name)
            if generic is not None and node.type_args \
                    and len(node.type_args) == len(generic.type_params):
                params = list(generic.params)
                subst = TypeSubstitution(dict(zip(generic.type_params, node.type_args)))
            elif generic is not None and not node.type_args:
                # Args still being inferred: only a param whose type names
                # none of the fn's type params is a slot (LARB R51a).
                params = [None if _names_type_param(p.type, generic.type_params) else p
                          for p in generic.params]
            for param, arg in zip(params, node.args):
                if param is not None and param.type is not None:
                    self._mark_lit_slot(arg, subst.apply(param.type) if subst else param.type)
        elif isinstance(node, rast.MethodCall):
            # A plain impl's method: its params after `self`.
            recv = self._type_of(node.expr)
            while isinstance(recv, (rast.PtrType, rast.RefType)):
                recv = recv.inner
            if isinstance(recv, rast.NamedType):
                method = self.impl_methods.get(recv.name, {}).get(node.method)
                if method is not None and method.params \
                        and method.params[0].name == 'self':
                    for param, arg in zip(method.params[1:], node.args):
                        self._mark_lit_slot(arg, param.type)

    def _mark_field_slots(self, lit: rast.StructLit) -> None:
        """A literal whose struct is known gives each field value that
        field's type as its slot: `Outer { b: Box2 { v: 8 } }` (§9.2)."""
        struct_def = self.struct_defs.get(lit.name)
        if struct_def is None:
            return
        fields = dict(struct_def.fields)
        subst = None
        params = struct_def.type_params or []
        if params and len(lit.type_args) == len(params):
            subst = TypeSubstitution(dict(zip(params, lit.type_args)))
        elif params and lit.type_args:
            return
        for name, value in lit.fields:
            field_type = fields.get(name)
            if field_type is None:
                continue
            if subst is not None:
                self._mark_lit_slot(value, subst.apply(field_type))
            elif not _names_type_param(field_type, params):
                # Args-less with no slot: a field whose type is fully known
                # is still a slot (LARB R51a); one naming a param is not, and
                # its value binds that param after it infers (§4.4).
                self._mark_lit_slot(value, field_type)

    def _struct_lit_from_slot(self, lit: rast.StructLit) -> None:
        """An args-less generic literal in a slot of its struct's instance
        takes that instance's args (§9.2 rule 1, LARB R51): `Box2 { v: 1 }` in
        a `Box2<u8>` slot is `Box2<u8> { v: 1 }`, as if written.  A slot of
        any other type leaves the args to the fields."""
        found = self._argless_struct(lit)
        slot = self._lit_slots.get(id(lit))
        if found is None or slot is None:
            return
        slot = resolve_alias(slot)
        if isinstance(slot, rast.NamedType) and slot.name == lit.name \
                and len(slot.args) == len(found[0]):
            lit.type_args = [copy.deepcopy(a) for a in slot.args]

    def _infer_struct_lit_args(self, lit: rast.StructLit) -> None:
        """An args-less generic literal with no slot binds its args from
        its field values, by section 4.4's rule for a generic call (§9.2
        rule 2, LARB R51): `Box2 { v: 1 }` is `Box2<i64>`, as `Present(1)` is,
        and an integer literal binds a bare `X` only when no other field does.
        A param no field binds, or two bind differently, is a located error
        (rule 3).  The args are written into `lit.type_args`, as if spelled
        out, so every later pass sees `Box2<i64> { .. }`.

        #3311 refused the literal; ritz1's generic_infer infers it too (#3408)."""
        found = self._argless_struct(lit)
        if found is None:
            return
        params, fields = found
        field_types = dict(fields)
        bound, conflict = bind_type_params(
            params, [(field_types.get(name), value, self._type_of(value))
                     for name, value in lit.fields])
        for tp in params:
            if tp not in bound or tp in conflict:
                raise GenericInferError(
                    f"can't infer `{tp}` for `{lit.name}`: write its type arguments, "
                    f"`{lit.name}<{', '.join(params)}> {{ .. }}`", lit.span)
        lit.type_args = [_at(bound[tp], lit.span) for tp in params]

    def _generic_variant(self, name: str):
        """(enum, variant) when `name` is a variant of a generic user enum and
        of no other enum, else None.  Option / Result are the builtin
        constructors' (#2430); two enums declaring it is #2039's error."""
        if name in self.var_types or name in self.fn_signatures \
                or name in self.generic_functions:
            return None
        found = [(e, v) for e in self.enum_defs.values() for v in e.variants
                 if v.name == name]
        if len(found) != 1:
            return None
        enum_def, variant = found[0]
        if not enum_def.type_params or enum_def.name in ('Option', 'Result'):
            return None
        return enum_def, variant

    def _infer_variant_scrutinee(self, value: rast.Expr) -> Optional[rast.Type]:
        """The instance `match Hold(5)` / `match Gone` builds, `Hold` a
        variant of a generic `enum W<T>` (AGAST #2437), or None for any other
        scrutinee.  A scrutinee has no slot and isn't the fn's value (#2419),
        so only the payload binds T, as for an untyped let in a fn that
        returns something else; an unbound T is the same located error.
        ritz0 crashed (`Unknown function: Hold`), ritz1 called `@Hold`."""
        while isinstance(value, rast.Grouped):
            value = value.expr
        if isinstance(value, rast.UnaryOp) and value.op in ('@', '&', '@&', '&mut'):
            value = value.operand
        return self._infer_variant_let(value, use_ret=False)

    def _infer_variant_let(self, value: rast.Expr,
                           use_ret: bool = True) -> Optional[rast.Type]:
        """The type of an untyped `let s = Full(5)` / `var s = Empty`, `Full`
        a variant of a generic `enum Slot<T>` (AGAST #2927), or None for any
        other initialiser.

        The fn's return type when it is an instance of that enum, as #2430
        has it for `let o = Some(5)` (unless `use_ret` is False); else the
        instance the payload binds, by
        section 4.4's rule for a generic call: `Full(5)` is a `Slot<i64>`.  A
        type param the payload leaves unbound (any of a unit variant's) is a
        located error: ritz0 crashed unlocated and ritz1 called `@Full`.
        """
        if isinstance(value, rast.Call) and isinstance(value.func, rast.Ident) \
                and not value.type_args:
            name, args = value.func.name, value.args
        elif isinstance(value, rast.Ident):
            name, args = value.name, []
        else:
            return None
        found = self._generic_variant(name)
        if found is None:
            return None
        enum_def, variant = found
        ret = self._infer_ret_type if use_ret else None
        if isinstance(ret, rast.NamedType) and ret.name == enum_def.name \
                and len(ret.args) == len(enum_def.type_params):
            return copy.deepcopy(ret)
        params = enum_def.type_params
        bound, conflict = bind_type_params(
            params, [(field_type, arg, self._type_of(arg))
                     for field_type, arg in zip(variant.fields, args)])
        for tp in params:
            if tp not in bound or tp in conflict:
                raise GenericInferError(
                    f"can't infer `{tp}` for `{name}`: give the binding a type", value.span)
        return rast.NamedType(value.span, enum_def.name,
                              [copy.deepcopy(bound[tp]) for tp in params])

    def _infer_one_call(self, call: rast.Call) -> None:
        """Bind the type params of a generic `f(args)` from its arguments.

        An argument binds each T its parameter's type mentions, matched
        structurally (`T`, `@T`, `*T`, `Vec<T>`, `@Vec<T>`...).  An integer
        literal binds a bare `T` param only when no other argument binds T,
        so `vec_push(@&v, 3)` on a Vec<i32> is vec_push<i32>.  A T no
        argument binds, or two bind differently, is a located error.
        """
        if call.type_args or not isinstance(call.func, rast.Ident):
            return
        fn_name = call.func.name
        fn_def = self.generic_functions.get(fn_name)
        if fn_def is None or fn_name in self.var_types:
            return
        params = fn_def.type_params
        bound, conflict = bind_type_params(
            params, [(param.type, arg, self._type_of(arg))
                     for param, arg in zip(fn_def.params, call.args)])
        for tp in params:
            if tp not in bound or tp in conflict:
                raise GenericInferError(
                    f"can't infer `{tp}` for `{fn_name}`: write `{fn_name}<{tp}>(...)`",
                    call.span)
        call.type_args = [_at(bound[tp], call.span) for tp in params]
