"""Call and method dispatch, split out of emitter_llvmlite (AGAST #1826, slice 3).

`_emit_call_inner` (one long builtin chain), `_emit_method_call` and
`_dispatch_method_call` (the receiver-type resolution and both call paths)
were LLVMEmitter methods in emitter_llvmlite.py, the last two together over
CC 90.  They are now a `CallEmitter` mixin:

  * `_emit_call_inner` is the dispatch: indirect calls, builtins, user fns,
    externs;
  * `_emit_indirect_call`, `_emit_builtin_call` (with `_emit_print_call`),
    `_emit_user_call` (with `_emit_user_call_args`), `_emit_extern_call` are
    those arms;
  * `_dispatch_method_call` resolves the receiver type and picks the static
    or instance path; `_static_receiver_peek`, `_probe_receiver_type` and
    `_fallback_receiver_type` are the receiver-type arms, and
    `_try_emit_receiver_builtin` the built-in method families;
  * `_emit_static_method_call` and `_emit_instance_method_call` are the two
    paths, `_method_receiver_value`, `_method_explicit_args` and
    `_convert_method_args` the instance path's pieces.

The moved branches are the same code in the same order, so the emitted IR is
byte-identical; the corpus replay against an origin/main worktree is the
evidence for that.
"""

from typing import Optional

from llvmlite import ir

import ritz_ast as rast
from monomorph import resolve_alias_in
from monomorph_core import instance_display_name
from builtin_types import PRIMITIVES, target_spelling
from name_resolver import BUILTIN_GENERICS
import ref_rules
import future_rules
import main_abi
import binder_names
from emitter.common import (EmitError, InternalError, UnknownFunction,
                            MEM_BUILTINS, _llvm_callconv)


class CallEmitter:
    """Call emission for `LLVMEmitter`; mixed in ahead of its other bases."""

    def _emit_call_inner(self, call: rast.Call) -> ir.Value:
        """Emit a function call.

        Supports:
        - Direct calls: foo(x, y)
        - Indirect calls through function pointer: fn_ptr(x, y)
        """
        # Handle indirect calls through function pointer variable or parameter
        indirect = self._emit_indirect_call(call)
        if indirect is not None:
            return indirect

        fname = call.func.name

        builtin = self._emit_builtin_call(call, fname)
        if builtin is not None:
            return builtin

        # Look up user-defined function
        if fname in self.functions:
            return self._emit_user_call(call, fname)

        # Look up extern function
        if fname in self.extern_fns:
            return self._emit_extern_call(call, fname)

        # A generic fn called without type args.  Monomorph infers them from
        # the arguments or refuses the call (AGAST #1982), so this is only
        # reached by a call it skips, e.g. through a local that shadows the
        # fn's name; name the fix rather than "Unknown function" (#1968).
        if fname in getattr(self, 'generic_fn_names', ()):
            raise self._err(
                f"generic function `{fname}` needs explicit type arguments here: "
                f"write `{fname}<T>(...)`")
        # `W_bump(w)` of a method of `impl<T> W<T>`: only a non-generic
        # impl's methods have R10's free name (§5.4, LARB R37, #3372).
        generic_method = getattr(self, 'generic_method_names', {}).get(fname)
        if generic_method is not None:
            raise UnknownFunction(ref_rules.generic_method_free_call(*generic_method), self._call_span(call))
        raise UnknownFunction(f"Unknown function: {fname}", self._call_span(call))

    def _emit_indirect_call(self, call: rast.Call) -> Optional[ir.Value]:
        """Emit a call whose callee is not a known fn, or None to fall through."""
        if isinstance(call.func, rast.Ident):
            fname = call.func.name

            # Check if this is a function pointer (local, parameter, or let binding)
            # The Ritz type is stored in ritz_types, which tells us if it's a FnType
            if fname in self.ritz_types:
                # A local typed with a fn-type alias (`let f: Handler`) is a
                # fn pointer too; the alias may carry a [[callconv]] (#1879).
                ritz_type = resolve_alias_in(self.ritz_types[fname], self.type_aliases)
                if isinstance(ritz_type, rast.FnType):
                    if not self._ret_is_a_value(ritz_type.ret):   # AGAST #2260, #3286
                        self._reject_procedure_value(call, fname)
                    self._check_fn_type_arity(call, fname, ritz_type)
                    # This is a function pointer - indirect call
                    # Get the function pointer value
                    if fname in self.locals:
                        var_ptr, _ = self.locals[fname]
                        fn_ptr = self.builder.load(var_ptr)
                    elif fname in self.params:
                        fn_ptr, _ = self.params[fname]
                    else:
                        raise InternalError(f"Function pointer '{fname}' not found in locals or params")

                    # Emit and convert arguments
                    for i, (arg, param_type) in enumerate(zip(call.args, ritz_type.params)):
                        if i not in ritz_type.lent:
                            self._literal_into_slot(param_type, arg)
                            self._float_slot(param_type, arg)
                    converted_args = []
                    for i, (arg, param_type) in enumerate(zip(call.args, ritz_type.params)):
                        expected_llvm = self._ritz_type_to_llvm(param_type)
                        if i in ritz_type.lent:
                            # AGAST #3034: a `:& T` slot borrows a bare
                            # place, as a direct call to the fn does.
                            lent = rast.Param(arg.span, f"#{i + 1}", param_type,
                                              borrow=rast.Borrow.MUTABLE)
                            converted_args.append(self._emit_place_borrow(
                                arg, ir.PointerType(expected_llvm), fname, i + 1, lent))
                            continue
                        with self._int_slot_context(param_type, arg):
                            arg_val = self._emit_expr(arg)
                        self._check_arg_narrowing(arg, arg_val, expected_llvm,
                                                  param_type, fname, i)
                        converted_args.append(self._convert_type(arg_val, expected_llvm, arg, arg=True))
                    # AGAST #1739 / #1745: large struct args go byval and a
                    # large struct result via sret, as for a direct call.
                    # AGAST #1879: a `[[callconv]]` fn-type alias's convention.
                    return self.builder.call(fn_ptr, converted_args,
                                             cconv=_llvm_callconv(ritz_type.callconv),
                                             byval=self._fn_type_byval(ritz_type),
                                             sret=self._fn_type_sret(ritz_type))
            # A local named like a fn is the local (AGAST #2407): a call of
            # one that holds no fn value isn't the fn's.
            if self._local_holds_no_fn(fname):
                raise EmitError(binder_names.call_refusal(fname),
                                call.func.span or call.span)
            return None
        # Non-identifier function expression (e.g., field access returning fn ptr)
        fn_ptr = self._emit_expr(call.func)
        # AGAST #2120: the callee's type is often the alias itself
        # (`(p as EfiFn)(..)`, a field, an element, a returned fn), and
        # the alias is what carries the [[callconv]]: resolve it.
        ritz_type = self._infer_ritz_type(call.func, fn_ptr)
        if ritz_type is not None:
            ritz_type = resolve_alias_in(ritz_type, self.type_aliases)
        if isinstance(ritz_type, rast.FnType):
            if not self._ret_is_a_value(ritz_type.ret):   # AGAST #2260, #3286
                self._reject_procedure_value(call, None)
            self._check_fn_type_arity(call, "<expression>", ritz_type)
            for arg, param_type in zip(call.args, ritz_type.params):
                self._literal_into_slot(param_type, arg)
                self._float_slot(param_type, arg)
        args = [self._emit_expr(arg) for arg in call.args]
        if isinstance(ritz_type, rast.FnType):
            args = [self._convert_type(a, self._ritz_type_to_llvm(p), arg, arg=True)
                    for arg, a, p in zip(call.args, args, ritz_type.params)]
            return self.builder.call(fn_ptr, args,
                                     cconv=_llvm_callconv(ritz_type.callconv),
                                     byval=self._fn_type_byval(ritz_type),
                                     sret=self._fn_type_sret(ritz_type))
        return self.builder.call(fn_ptr, args)

    def _emit_builtin_call(self, call: rast.Call, fname: str) -> Optional[ir.Value]:
        """Emit a reserved builtin call, or None if `fname` is not one.

        Reserved names are checked before user functions, as ritz1 orders them.
        """
        # Handle enum variant constructors: Some(x), None, Ok(v), Err(e)
        self._refuse_no_instance(call)
        if fname in self.variant_to_enum:
            self._check_variant_unambiguous(fname, call.func.span)
            return self._emit_enum_variant_constructor(fname, call.args, call.span)

        # Handle __builtin_alloca
        if fname == '__builtin_alloca':
            size = self._emit_expr(call.args[0])
            if isinstance(size, ir.Constant):
                return self.builder.alloca(self.i8, size.constant)
            else:
                return self.builder.alloca(self.i8, size)

        # Handle SIMD builtin functions
        simd_result = self._try_emit_simd_builtin(fname, call.args)
        if simd_result is not None:
            return simd_result

        # sizeof(T) / sizeof(expr) -> compile-time size in bytes (spec §7.9).
        if fname == 'sizeof':
            return ir.Constant(self.i64, self._sizeof_operand_size(call))

        # Volatile / atomic memory builtins (AGAST #1879). Reserved names, like
        # sizeof: checked before user functions.
        if fname in MEM_BUILTINS:
            return self._emit_mem_builtin(fname, call)

        # future_poll(f: @&Future) -> bool: the header's poll fn, on f (LARB R79).
        if fname == future_rules.POLL and fname not in self.functions:
            return self._emit_future_poll(call)

        # Handle print / eprint builtins - print(string_literal) -> write(1, ptr, len).
        # eprint is the same lowering to fd 2 (AGAST #1641). println and
        # eprintln take the same lowering plus a newline (AGAST #202), but
        # only for an interpolated literal: a plain one still resolves to
        # whatever `println` names in this file (ritzlib.io's, or a test's).
        printed = self._emit_print_call(call, fname)
        if printed is not None:
            self._print_is_procedure(call, fname)
            return printed

        # write(w, "...{x}...") / writeln: Display through the Writer the
        # program named, not an implicit one (AGAST #202). Only an
        # interpolated literal is lowered here; a plain one is the ordinary
        # StrView call. Checked before user fns, like print.
        if (fname in ('write', 'writeln') and len(call.args) == 2
                and isinstance(call.args[1], rast.InterpString)):
            written = self._emit_interp_string_print(
                call.args[1], newline=(fname == 'writeln'), writer=call.args[0])
            self._print_is_procedure(call, fname)
            return written

        # format_into(sink, "...") -- print's literal, appended to a buffer
        # (AGAST #1824). Reserved like print: checked before user functions.
        if fname == 'format_into':
            return self._emit_format_into(call)

        # AGAST #4198: once main took the entry adapter, `main` is the
        # adapter's (argc, argv, envp); the user's fn is __ritz_main and the
        # adapter is its only caller. A call to `main` is refused here, in
        # main_abi's words, not as an arity error against the adapter.
        if fname == "main" and main_abi.ADAPTED_NAME in self.functions:
            raise EmitError(main_abi.MSG_CALL, self._call_span(call))
        return None

    def _emit_print_call(self, call: rast.Call, fname: str) -> Optional[ir.Value]:
        """`print` / `eprint` / interpolated `println` / `eprintln`, or None."""
        line_print = fname in ('println', 'eprintln')
        interp_line = (line_print and len(call.args) == 1
                       and isinstance(call.args[0], rast.InterpString))
        if fname in ('print', 'eprint') or interp_line:
            out_fd = 1 if fname in ('print', 'println') else 2
            if len(call.args) == 1:
                arg = call.args[0]
                if isinstance(arg, rast.CStringLit) and self._has_interp_placeholder(arg.value):
                    # AGAST #1374. `print(c"...{x}...")` used to compile clean,
                    # exit 0, and print the placeholder verbatim. 72_raii
                    # shipped exactly that: it built, linked and ran green while
                    # emitting `id={id}` against an expected `id=1`.
                    #
                    # We reject rather than interpolate. Interpolating c-strings
                    # was measured and rejected: 48 corpus sites rely on `{...}`
                    # staying opaque, 14 of them ritz1's own LLVM inline-asm
                    # constraints (`"={rax},{rax},{rdi}"`). Interpolating those
                    # corrupts every syscall the self-hosted compiler emits.
                    #
                    # The check lives HERE, in the print builtin's lowering, and
                    # not in the lexer or parser, for exactly that reason: those
                    # would hit all 48 sites.
                    raise EmitError(
                        "`c\"...\"` literals do not interpolate: the placeholder "
                        "would be printed verbatim. Use a plain string literal "
                        "`\"...\"` here, or `{{` to print a literal brace",
                        getattr(arg, "span", None) or getattr(call, "span", None),
                    )
                if isinstance(arg, (rast.StringLit, rast.CStringLit)):
                    s = arg.value
                    # AGAST #1913: `{{` / `}}` print as one brace, but only
                    # here -- the literal itself keeps both. c"..." never
                    # collapses them.
                    if isinstance(arg, rast.StringLit) and arg.print_value is not None:
                        s = arg.print_value
                    # Get or create the string constant
                    str_const = self._get_string_constant(s)
                    # GEP to get i8* pointer to string data
                    ptr = self.builder.gep(str_const, [ir.Constant(self.i64, 0), ir.Constant(self.i64, 0)])
                    length = len(s)
                    # write(out_fd, ptr, length) via syscall; its value is
                    # the Result of that one write (AGAST #4962).
                    got = self._emit_write_syscall(ir.Constant(self.i64, out_fd), ptr, ir.Constant(self.i64, length))
                    zero = ir.Constant(self.i64, 0)
                    status = self.builder.select(
                        self.builder.icmp_signed('<', got, zero), got, zero)
                    return self._print_result(status, getattr(call, "span", None))
                elif isinstance(arg, rast.InterpString):
                    # Handle interpolated string - desugar to Display calls
                    return self._emit_interp_string_print(arg, out_fd,
                                                          newline=line_print)
            # AGAST #3933: located, at the argument (at the call when there
            # isn't exactly one), as ritz1's call_check says it.
            at = call.args[0] if len(call.args) == 1 else call
            raise EmitError(f"{fname}() requires a single string literal argument",
                            getattr(at, "span", None) or getattr(call, "span", None))
        return None

    def _emit_user_call(self, call: rast.Call, fname: str) -> ir.Value:
        """Emit a call to a user-defined fn."""
        fn, fn_def = self.functions[fname]
        self._check_private_call(fn_def, fname, call.func.span)
        if self._is_procedure(fn_def):
            self._resolved_to_procedure(call, fname.partition('$')[0])

        # Check argument count BEFORE processing
        if len(call.args) != len(self._fn_param_types(fn)):
            # AGAST #1366. This one already named the function — that is
            # why 52_uring's identical-class failure was fixed in one step
            # while 47_lisp's anonymous one sat on the allowlist. It still
            # arrived as a bare ValueError with a traceback and no
            # location, so give it the same treatment.
            raise EmitError(
                f"`{fname}` called with {len(call.args)} argument(s) but "
                f"defined with {len(self._fn_param_types(fn))}",
                self._call_span(call))

        args = self._emit_user_call_args(call, fname, fn, fn_def)
        return self.builder.call(fn, args)

    def _emit_user_call_args(self, call: rast.Call, fname: str, fn,
                             fn_def) -> list:
        """Emit a direct call's arguments with type conversion and borrowing."""
        # Emit arguments with type conversion
        # Also handle RERITZ Borrow semantics - borrowed params need addresses
        args = []
        for i, arg in enumerate(call.args):
            param_def = fn_def.params[i]
            expected_type = self._fn_param_types(fn)[i]
            self._check_struct_ptr_arg(arg, param_def, fname, i + 1)
            self._literal_into_slot(param_def.type, arg)
            self._float_slot(param_def.type, arg)

            # Check if this parameter is a reference type (@T or @&T in RERITZ, or :& borrow)
            # References pass by pointer - we need to pass the address of the argument
            is_mutable_borrow = hasattr(param_def, 'borrow') and param_def.borrow == rast.Borrow.MUTABLE
            is_ref_type = isinstance(param_def.type, rast.RefType)

            # Check if the argument is already a RefType, PtrType, or explicit address-of
            arg_ritz_type = self._infer_ritz_type(arg)
            arg_is_ref = isinstance(arg_ritz_type, rast.RefType) if arg_ritz_type else False
            # PtrType is compatible with RefType at LLVM level (both are pointers)
            arg_is_ptr = isinstance(arg_ritz_type, rast.PtrType) if arg_ritz_type else False
            # Also check if argument is explicit &x or @x (address-of expression)
            arg_is_addr_of = isinstance(arg, rast.UnaryOp) and arg.op in ('&', '@', '@&', '&mut')

            # AGAST #1290: a `*T` PtrType param whose pointee is the
            # argument's own named type is a borrow site too — an rvalue
            # argument (e.g. a call result) must be spilled so its address
            # can be taken. Requiring the pointee to *match* the argument's
            # named type keeps `*u8` params off this path, and pointer-typed arguments (arg_is_ptr) never
            # match because their inferred type is a PtrType, not a
            # NamedType. This is the `_emit_call` arm of the two-sited
            # auto-borrow defect; the `_emit_method_call` arm is #1321.
            # Restricted to *struct* pointees: primitive pointees like
            # `*u8` are byte-buffer/cstr params whose arguments are often
            # pointer arithmetic (`@buf[0] + n`) that _infer_ritz_type
            # reports as the element type `u8` — spilling those passes
            # `i8**` where `i8*` is expected (broke ritzlib/fs.ritz).
            is_matching_ptr_param = (
                isinstance(param_def.type, rast.PtrType)
                and isinstance(param_def.type.inner, rast.NamedType)
                and isinstance(arg_ritz_type, rast.NamedType)
                and arg_ritz_type.name == param_def.type.inner.name
                and arg_ritz_type.name in self.struct_types
            )

            if is_matching_ptr_param and not (is_mutable_borrow or is_ref_type):
                # `*T` param whose pointee matches the arg's inferred named
                # type. Inference is not authoritative here: an Ident
                # *holding* a `*Task` can infer as `Task` (ritzlib
                # async/tasks.ritz), and taking its lvalue address would
                # pass `Task**`. Decide from the actual emitted types:
                #   - lvalue address matches the param -> borrow in place
                #   - emitted value matches the param  -> already a pointer
                #   - emitted value matches the pointee -> rvalue, spill
                val = None
                try:
                    addr = self._emit_lvalue_addr(arg)
                    if addr.type == expected_type:
                        val = addr
                except ValueError:
                    pass
                if val is None:
                    tmp_val = self._emit_expr(arg)
                    if tmp_val.type == expected_type:
                        val = tmp_val
                    elif (isinstance(expected_type, ir.PointerType)
                            and tmp_val.type == expected_type.pointee):
                        tmp = self._alloca_in_entry_block(
                            tmp_val.type, "arg.tmp")
                        self.builder.store(tmp_val, tmp)
                        val = tmp
                    else:
                        val = self._convert_type(tmp_val, expected_type)
            elif is_mutable_borrow:
                val = self._emit_place_borrow(arg, expected_type, fname, i + 1, param_def)
            elif is_ref_type:
                if arg_is_ref or arg_is_ptr or arg_is_addr_of:
                    # Argument is already a pointer type - just emit it
                    val = self._emit_expr(arg)
                    # Any async fn's future is a `Future` (LARB R79): the
                    # generated `NAME$Future` is unspellable (AGAST #3606),
                    # so a pointer argument is cast to the slot's type.
                    if (future_rules.is_future(resolve_alias_in(param_def.type.inner, self.type_aliases))
                            and isinstance(val.type, ir.PointerType)):
                        val = self.builder.bitcast(val, expected_type)
                else:
                    self._check_let_implicit_mut_borrow(arg, param_def)
                    # Reference parameter: emit address of the argument.
                    # If the argument is an rvalue (e.g. a method call result),
                    # spill it to a stack slot so we can take its address.
                    try:
                        val = self._emit_lvalue_addr(arg)
                    except ValueError:
                        tmp_val = self._emit_expr(arg)
                        tmp = self._alloca_in_entry_block(tmp_val.type, "arg.tmp")
                        self.builder.store(tmp_val, tmp)
                        val = tmp
            else:
                # Moved/value parameter: emit value normally.
                # `f(Some(x))` must build the variant for the *parameter's*
                # enum - variant names are global, so otherwise `Some`
                # resolves to whichever Option was specialized last, or
                # to an enclosing let's enum (AGAST #1577).
                with self._int_slot_context(param_def.type, arg):
                    val = self._emit_value_arg(
                        arg, param_def.type, lambda a, s=param_def.type: self._emit_param_value(a, s))
                self._check_arg_narrowing(arg, val, expected_type,
                                          param_def.type, fname, i)
                val = self._convert_type(val, expected_type, arg, arg=True)
            args.append(val)
        return args

    def _emit_param_value(self, a: rast.Expr, slot: Optional[rast.Type]) -> ir.Value:
        """Emit the argument `a` into a by-value param of type `slot`, a fn's
        or a method's alike (AGAST #4837: a method's took the copy)."""
        if (self._is_range_index(a)
                or self._builtin_type_receiver(a) is not None
                or self._is_generic_static_call(a)):
            # AGAST #2877: a Vec slice into a `Span<T>` param is a view
            # (_emit_vec_span_slice), as into a Span let.  AGAST #2296:
            # `Span.empty()` takes its T from the param, not from whatever
            # slot encloses the call; so does `Slot.mk(5)` (AGAST #2185).
            return self._emit_slice_into(a, slot)
        return self._emit_into_array_slot(a, slot)

    def _emit_extern_call(self, call: rast.Call, fname: str) -> ir.Value:
        """Emit a call to a declared extern fn."""
        fn_type, extern_def = self.extern_fns[fname]

        # Check argument count
        expected_arg_count = len(fn_type.args)
        if extern_def.varargs:
            # For varargs, at least the fixed params must be provided
            if len(call.args) < expected_arg_count:
                raise self._err(f"Extern function '{fname}' requires at least {expected_arg_count} args, got {len(call.args)}")
        else:
            if len(call.args) != expected_arg_count:
                raise self._err(f"Extern function '{fname}' called with {len(call.args)} args but declared with {expected_arg_count} params")

        # Declare the extern function in LLVM if not already done
        if fname not in self.module.globals:
            fn = self._new_function(fname, fn_type.return_type, list(fn_type.args),
                                    extern_def.callconv)
        else:
            fn = self.module.globals[fname]

        # Emit arguments with type conversion
        args = []
        for i, arg in enumerate(call.args):
            with self._int_slot_context(
                    extern_def.params[i].type if i < len(extern_def.params) else None,
                    arg):
                val = self._emit_expr(arg)
            if i < len(fn_type.args):
                expected_type = fn_type.args[i]
                self._check_arg_narrowing(
                    arg, val, expected_type,
                    extern_def.params[i].type if i < len(extern_def.params) else None,
                    fname, i)
                val = self._convert_type(val, expected_type, arg, arg=True)
            args.append(val)

        return self.builder.call(fn, args)

    def _emit_method_call(self, expr: rast.MethodCall) -> ir.Value:
        """Emit a method call, evaluating its receiver once (AGAST #2261).

        Dispatch needs the receiver's type before it knows how the method
        takes `self`, and several routes then re-emit the receiver: the
        by-value path, the place path, and built-ins that never see the
        probe. What this call evaluated stays recorded until it has been
        emitted, so `_emit_expr` hands all of them the same value.
        """
        # `m.f()`: no `module.item` access (§15.3, AGAST #2215); was
        # "Unknown identifier: m", unlocated.
        if isinstance(expr.expr, rast.Ident):
            self._refuse_module_item(expr.expr.name, expr.method, expr.span)
        field_call = self._fn_field_call(expr)
        if field_call is not None:
            return self._emit_call(field_call)
        expr = self._deref_method_call(expr)
        outer = self._evaluated_once
        outer_use = self._deref_use_now
        self._evaluated_once = dict(outer)
        # A receiver reached through `Deref` (`b.q.m()`): a `self: @&T` method
        # needs `deref_mut`, any other `deref` (§7.7).
        if isinstance(expr.expr, (rast.Field, rast.Index)) and self._has_deref_step(expr.expr):
            fn = self._receiver_method_def(expr)
            self._deref_use_now = (f"method:{expr.method}" if fn is not None
                                   and self._mutates_self(fn) else "read")
        try:
            return self._dispatch_method_call(expr)
        finally:
            self._evaluated_once = outer
            self._deref_use_now = outer_use

    def _dispatch_method_call(self, expr: rast.MethodCall) -> ir.Value:
        """Emit a method call: receiver.method(args...).

        Method calls are desugared to static function calls using name mangling:
        - Type_method(receiver, args...) for inherent methods
        - Trait method calls look up the impl and use Type_method

        With monomorphization, we determine the receiver type at compile time
        and call the appropriate mangled function.

        If the method expects *Self and receiver is a value, we auto-borrow.
        """
        # Associated function on a built-in generic type: `Span.empty()`,
        # `Vec.new()`, ... The receiver is a *type*, not a value, so there is
        # no receiver argument and the type parameter comes from the context
        # the call sits in (return type, let annotation).
        self._record_assert_site(expr)
        assoc = self._try_emit_associated_builtin_call(expr)
        if assoc is not None:
            return assoc

        enum_ctor = self._try_emit_enum_ctor_on_type(expr)
        if enum_ctor is not None:
            return enum_ctor

        # First, check if the receiver is an lvalue (identifier, field, index)
        # If so, get its address for auto-borrowing when method expects *Self
        receiver_is_lvalue = isinstance(expr.expr, (rast.Ident, rast.Field, rast.Index))
        # A slice `x[lo..hi]` is a new value with no place (AGAST #3088): an
        # `@self` method on it is lent a spill, as on any rvalue.  It was
        # "can't take the address of a slice", where ritz1 accepts
        # `all[a..b].copy_from(src)` (AGAST #4843, buddhafinger's buffer.ritz).
        if isinstance(expr.expr, rast.Index) and isinstance(expr.expr.index, rast.Range):
            receiver_is_lvalue = False

        (type_name, is_static_call, receiver_is_lvalue,
         receiver_probe, receiver_slot, rvalue_field, early) = \
            self._resolve_receiver_type(expr, receiver_is_lvalue)
        if early is not None:
            return early

        if type_name is None:
            raise self._err(f"Cannot call method '{expr.method}' on unknown type")

        builtin = self._try_emit_receiver_builtin(expr, type_name, receiver_probe)
        if builtin is not None:
            return builtin

        # Method syntax reaches only impl methods: the UFCS name table that
        # sent `v.m()` to a free `vec_m$T` / `string_m` went with LARB R66
        # (AGAST #3496).
        method_key = (type_name, expr.method)
        if method_key in self.method_lookup:
            mangled_name = self.method_lookup[method_key]
        else:
            # Core Span<T> operations are built-in shapes ({ ptr, len }),
            # so they must work without importing ritzlib.span.
            builtin_span = self._try_emit_builtin_span_method(expr, type_name)
            if builtin_span is not None:
                return builtin_span
            if type_name.split('$')[0] in BUILTIN_GENERICS:
                # ritz1's words, at the method name (AGAST #3764): the
                # checker leaves a built-in generic's methods to us.
                # Option/Result too, imported from ritzlib or not
                # (AGAST #4262).  Named as ritz1 names it, not by
                # type_name, its linked name (AGAST #4266).
                raise EmitError(ref_rules.no_method(
                                    expr.method, instance_display_name(type_name)),
                                expr.name_span or expr.span)
            # `ptr_u8` is the linked spelling; name the pointer the way the
            # source does, `*u8` (R36's revisit, #4294, names primitives and
            # pointers instead of leaving them "unknown type").
            raise self._err(f"No method '{expr.method}' found for type "
                            f"'{target_spelling(type_name)}'",
                            expr.name_span or expr.span)

        if mangled_name not in self.functions:
            raise InternalError(f"Method function '{mangled_name}' not found")

        fn, fn_def = self.functions[mangled_name]
        self._check_private_call(fn_def, f"{type_name}.{expr.method}",
                                 expr.name_span or expr.span)
        if self._is_procedure(fn_def):
            self._resolved_to_procedure(expr, expr.method)

        # Check if this is a static method (no self parameter)
        # Static methods are called as Type.method() with no receiver instance
        has_self_param = len(fn_def.params) > 0 and fn_def.params[0].name == 'self'

        # For static calls (Type.method()), verify there's no self parameter
        # A lent `self` too, `@T`, `@&T`, `*T` or `:&` (AGAST #2292, #3236).
        if is_static_call and has_self_param:
            p0 = fn_def.params[0]
            by_value = not (p0.borrow == rast.Borrow.MUTABLE or isinstance(p0.type, (rast.RefType, rast.PtrType)))
            raise EmitError(ref_rules.static_call_of_self(expr.method, expr.expr.name, by_value), expr.span)

        # Handle static method call - no receiver needed
        if is_static_call or not has_self_param:
            return self._emit_static_method_call(expr, fn, fn_def, mangled_name)

        return self._emit_instance_method_call(
            expr, fn, fn_def, mangled_name, receiver_probe, receiver_slot,
            receiver_is_lvalue, rvalue_field)

    def _try_emit_enum_ctor_on_type(self, expr: rast.MethodCall) -> Optional[ir.Value]:
        """`Enum.Variant(args)`, which parses as a method call, or None.

        The receiver is a *type name*, so the fallback (emit the receiver,
        inspect its LLVM type) would try to evaluate the bare identifier as a
        value and fail with "Unknown identifier". The variant-list probe keeps
        genuine inherent methods on an enum — `Color.parse(s)` — on the normal
        dispatch path.
        """
        if isinstance(expr.expr, rast.Ident):
            enum_name = expr.expr.name
            if (enum_name in self.enum_types
                    and enum_name not in self.locals
                    and enum_name not in self.params
                    and self._has_enum_variant(enum_name, expr.method)):
                return self._emit_enum_variant_constructor_for_type(
                    expr.method, expr.args, enum_name, expr.span)
        return None

    def _resolve_receiver_type(self, expr: rast.MethodCall, receiver_is_lvalue):
        """Resolve the method receiver's type and probe.

        Returns (type_name, is_static_call, receiver_is_lvalue, receiver_probe,
        receiver_slot, rvalue_field, early) where `early` is a value some
        receiver route already emitted (a float intrinsic on a probed receiver).
        """
        type_name, is_static_call = self._static_receiver_peek(expr)
        receiver_probe = None
        receiver_slot = None  # The temporary holding the receiver, if any
        rvalue_field = False  # `mw().p`: a field of a value, not a place
        early = None
        if type_name is None:
            (receiver_probe, receiver_slot, rvalue_field, receiver_is_lvalue,
             type_name, early) = self._probe_receiver_type(expr, receiver_is_lvalue)
        if early is None and type_name is None:
            type_name = self._fallback_receiver_type(expr)
        return (type_name, is_static_call, receiver_is_lvalue, receiver_probe,
                receiver_slot, rvalue_field, early)

    def _static_receiver_peek(self, expr: rast.MethodCall):
        """The receiver type a type-name or binding names, and static-ness."""
        type_name = None
        is_static_call = False  # True if Type.method() with no receiver instance
        if isinstance(expr.expr, rast.Ident):
            name = expr.expr.name
            # Check if this is a static method call (receiver is a type name, not a variable)
            # e.g., ShapedGlyph.simple(...) where ShapedGlyph is a type, not a variable
            if name in self.struct_types and name not in self.locals and name not in self.params:
                type_name = name
                is_static_call = True
            # The same for an enum's impl: `Opt.make(40)`. A variant of that
            # name was already built above. A global named like the enum
            # shadows it, as a local does (AGAST #2101).
            elif (name in self.enum_types and name not in self.locals
                    and name not in self.params and name not in self.globals):
                type_name = name
                is_static_call = True
            # `Slot.mk(5)` on `impl<T> Slot<T>`: the instance is the slot's
            # (AGAST #2185); the bare template was emitted as a value.
            elif self._generic_type_receiver(name, expr.method):
                type_name = self._generic_static_instance(expr)
                is_static_call = True
            # First check ritz_types for the original Ritz type (preserves signedness)
            elif name in self.ritz_types:
                ritz_type = self.ritz_types[name]
                if isinstance(ritz_type, rast.NamedType):
                    if ritz_type.args:
                        type_name = self._get_specialized_type_name(ritz_type)
                    else:
                        type_name = ritz_type.name
            # Fall back to LLVM type inspection for struct types
            if type_name is None:
                if name in self.locals:
                    alloca, ty = self.locals[name]
                    type_name = self._get_struct_name_from_type(ty)
                elif name in self.params:
                    val, ty = self.params[name]
                    type_name = self._get_struct_name_from_type(ty)
        return type_name, is_static_call

    def _probe_receiver_type(self, expr: rast.MethodCall, receiver_is_lvalue):
        """Emit the receiver once and read its LLVM type.

        Returns (receiver_probe, receiver_slot, rvalue_field,
        receiver_is_lvalue, type_name, early).
        """
        receiver_probe = None
        receiver_slot = None  # The temporary holding the receiver, if any
        rvalue_field = False  # `mw().p`: a field of a value, not a place
        early = None
        type_name = None
        # Fall back to emitting the expression and checking its type.
        # This is the receiver's one evaluation (AGAST #2261).
        if receiver_is_lvalue:
            self._evaluate_place_operands(expr.expr)
        receiver_probe = self._emit_expr_core(expr.expr)
        receiver_slot = self._own_temporary(expr.expr, receiver_probe)
        self._evaluated_once[id(expr.expr)] = receiver_probe
        # `mw().p.get()`: a field of an rvalue is a value, not a place,
        # so it's lent as any rvalue is, from a spill (AGAST #2294).
        rvalue_field = receiver_is_lvalue and self._field_of_rvalue(expr.expr)
        if rvalue_field:
            receiver_is_lvalue = False
        receiver_type = receiver_probe.type
        if isinstance(receiver_type, ir.PointerType):
            # The type at the end of every pointer level (§5.4, #2398);
            # _load_to_self takes the levels off.
            _, pointee = self._pointer_levels(receiver_type)
            type_name = self._get_struct_name_from_type(pointee)
            if type_name is None:
                # Pointer-to-enum receiver (e.g. *Result<T,E>)
                for enum_name, (enum_ty, _) in self.enum_types.items():
                    if pointee == enum_ty:
                        type_name = enum_name
                        break
        else:
            type_name = self._get_struct_name_from_type(receiver_type)
            # Also check for primitive integer types (for BitOps support)
            if type_name is None and isinstance(receiver_type, ir.IntType):
                # An integer's LLVM type has no sign.  Prefer the source
                # type when inference names it — `e.key` on a specialised
                # HashMapEntry<K, V> is i64 only through its fields — or
                # `e.key.equals(key)` saw u64 and missed `impl Eq for i64`
                # (AGAST #1858).  Unsigned is the BitOps default: both
                # signednesses work the same there.
                inferred = self._infer_ritz_type(expr.expr)
                if (isinstance(inferred, rast.NamedType) and not inferred.args
                        and inferred.name in PRIMITIVES):
                    type_name = inferred.name
                else:
                    type_name = f'u{receiver_type.width}'
            # Float primitive methods on expression receivers (ceil/floor/round/abs)
            if type_name is None and self._is_float_type(receiver_type):
                early = self._try_emit_float_intrinsic(expr, receiver_probe)
            if type_name is None:
                # Value-of-enum receiver (e.g. result of fn returning Result/Option)
                for enum_name, (enum_ty, _) in self.enum_types.items():
                    if receiver_type == enum_ty:
                        type_name = enum_name
                        break
        return (receiver_probe, receiver_slot, rvalue_field,
                receiver_is_lvalue, type_name, early)

    def _fallback_receiver_type(self, expr: rast.MethodCall) -> Optional[str]:
        """The receiver type from inference, then built-in receiver names."""
        type_name = None
        # Final fallback: resolve the receiver's Ritz type via inference
        # (handles call/field receivers whose return-type carries generic args)
        enum_name = self._get_enum_name_from_expr(expr.expr)
        if enum_name:
            type_name = enum_name

        if type_name is None:
            inferred = self._infer_ritz_type(expr.expr)
            if isinstance(inferred, rast.NamedType):
                if inferred.args:
                    type_name = self._get_specialized_type_name(inferred)
                else:
                    type_name = inferred.name

        # R36's revisit (#4294): a receiver inferred as a primitive, a `*u8`,
        # or a reference to one dispatches to the trait impl on that built-in
        # type.  `fmt_show<T>`'s `v.show(w)` at T = i64 is a `@i64`.
        if type_name is None:
            type_name = self._builtin_receiver_name(expr.expr)
        return type_name

    def _try_emit_receiver_builtin(self, expr: rast.MethodCall, type_name: str,
                                   receiver_probe) -> Optional[ir.Value]:
        """The built-in method families that pre-empt impl lookup, or None."""
        # Check for BitOps intrinsics on primitive integer types
        bitops_result = self._try_emit_bitops_intrinsic(expr, type_name)
        if bitops_result is not None:
            return bitops_result

        # Float intrinsic methods when receiver type was inferred from symbols.
        float_result = self._try_emit_float_intrinsic(expr, receiver_probe)
        if float_result is not None:
            return float_result

        # Built-in enum predicate methods (is_some/is_none/is_ok/is_err) for
        # Option/Result. Emit a direct tag comparison rather than relying on
        # ritzlib helper specializations, which the monomorphizer can't always
        # see (e.g. when the receiver's type is inferred from a function call
        # without an explicit annotation).
        enum_predicate = self._try_emit_enum_predicate_method(expr, type_name, receiver_probe)
        if enum_predicate is not None:
            return enum_predicate

        # Built-in StrView helpers (.as_bytes)
        strview_builtin = self._try_emit_strview_builtin(expr, type_name, receiver_probe)
        if strview_builtin is not None:
            return strview_builtin

        # Built-in .len() for Vec/Span/StrView when no impl is in scope
        len_builtin = self._try_emit_len_builtin(expr, type_name, receiver_probe)
        if len_builtin is not None:
            return len_builtin

        # Built-in unwrap for Option/Result (.unwrap/.unwrap_or)
        unwrap_builtin = self._try_emit_enum_unwrap_method(expr, type_name, receiver_probe)
        if unwrap_builtin is not None:
            return unwrap_builtin
        return None

    def _emit_static_method_call(self, expr: rast.MethodCall, fn: ir.Function,
                                 fn_def, mangled_name: str) -> ir.Value:
        """Emit `Type.method(args)`: no receiver argument."""
        self._check_method_arity(expr, fn, len(expr.args))
        # Static method - just emit the arguments, no receiver
        all_args = []
        for i, arg in enumerate(expr.args):
            if i < len(fn_def.params):
                self._check_struct_ptr_arg(arg, fn_def.params[i], expr.method, i + 1)
                self._literal_into_slot(fn_def.params[i].type, arg)
                self._float_slot(fn_def.params[i].type, arg)
            if i < len(fn_def.params) and self._takes_place(fn_def.params[i]):
                all_args.append(self._emit_place_borrow(
                    arg, self._fn_param_types(fn)[i], expr.method, i + 1,
                    fn_def.params[i]))
            else:
                slot = fn_def.params[i].type if i < len(fn_def.params) else None
                # AGAST #1577: at the param's enum, not an outer let's.
                with self._int_slot_context(slot, arg):
                    all_args.append(self._emit_value_arg(
                        arg, slot, lambda a, s=slot: self._emit_param_value(a, s)))

        # Convert argument types as needed
        converted_args = []
        for i, arg in enumerate(all_args):
            expected_type = self._fn_param_types(fn)[i]
            self._check_arg_narrowing(
                expr.args[i], arg, expected_type,
                fn_def.params[i].type if i < len(fn_def.params) else None,
                expr.method, i)
            converted = self._convert_type(arg, expected_type, expr.args[i], arg=True)
            converted_args.append(converted)

        return self._emit_method_call_insn(expr, fn, mangled_name, converted_args, 0)

    def _emit_instance_method_call(self, expr: rast.MethodCall, fn: ir.Function,
                                   fn_def, mangled_name: str, receiver_probe,
                                   receiver_slot, receiver_is_lvalue,
                                   rvalue_field) -> ir.Value:
        """Emit `receiver.method(args)`: the receiver is argument 1."""
        # The receiver is argument 1, as `get(p, 1, 2)` would have it.
        self._check_method_arity(expr, fn, len(expr.args) + 1)
        first_param_type = self._fn_param_types(fn)[0]

        # `mk().bump()` with `self: @&T` / `self:& T` is a store into the
        # call's temporary, lost with it (AGAST #2518, R1 exception 4).
        self_param = fn_def.params[0]
        # A field of one is in it: `mw().p.bump()` loses the store as well.
        if (rvalue_field and self._mutates_self(fn_def)
                and not isinstance(receiver_probe.type, ir.PointerType)):
            raise EmitError(ref_rules.MUT_SELF_ON_TEMP, expr.expr.span)
        if (isinstance(expr.expr, (rast.Call, rast.MethodCall))
                and (getattr(self_param, 'borrow', None) == rast.Borrow.MUTABLE
                     or (isinstance(self_param.type, rast.RefType) and self_param.type.mutable))):
            probe = receiver_probe if receiver_probe is not None else self._emit_expr(expr.expr)
            if not isinstance(probe.type, ir.PointerType):
                raise EmitError(ref_rules.MUT_SELF_ON_TEMP, expr.expr.span)
            if receiver_probe is None:
                self._evaluated_once[id(expr.expr)] = probe

        receiver_val = self._method_receiver_value(
            expr, fn_def, first_param_type, receiver_probe, receiver_slot,
            receiver_is_lvalue)
        receiver_val = self._load_to_self(receiver_val, first_param_type)

        # Build arguments: receiver first, then explicit args
        all_args = [receiver_val]
        self._method_explicit_args(expr, fn, fn_def, all_args)
        converted_args = self._convert_method_args(expr, fn, fn_def, all_args)
        return self._emit_method_call_insn(expr, fn, mangled_name, converted_args, 1)

    def _method_receiver_value(self, expr: rast.MethodCall, fn_def,
                               first_param_type, receiver_probe, receiver_slot,
                               receiver_is_lvalue) -> ir.Value:
        """The receiver's value: by value, borrowed in place, or spilled."""
        # Determine whether to pass by value or by pointer (auto-borrow)
        # If method expects pointer and receiver is lvalue, get address
        receiver_val = None
        if self._receiver_short_of_self(expr.expr, first_param_type, receiver_probe):
            receiver_val = self._borrow_receiver(expr.expr, fn_def.params[0], receiver_probe)
        elif self._deref_place_receiver(expr.expr, first_param_type, receiver_probe):
            # LARB R9: `*p` is a place, so `(*p).m()` is `p.m()`. The probe
            # loaded the struct from the pointee; lend that address, not a
            # copy of what it loaded (AGAST #2175).
            receiver_val = receiver_probe.operands[0]
        elif receiver_is_lvalue and isinstance(first_param_type, ir.PointerType):
            self._check_let_implicit_mut_borrow(expr.expr, fn_def.params[0])
            # Try to get address of the receiver
            # For `var` bindings, this is the alloca
            # For `let` bindings with struct values, we need special handling
            if isinstance(expr.expr, rast.Ident):
                name = expr.expr.name
                if name in self.locals:
                    # var binding - get the alloca
                    alloca, ty = self.locals[name]
                    # If the local is already a pointer, use it directly
                    if isinstance(ty, ir.PointerType):
                        receiver_val = self.builder.load(alloca)
                    else:
                        receiver_val = alloca
                elif name in self.globals:
                    # global var - get the global variable pointer
                    gvar, ty = self.globals[name]
                    if isinstance(ty, ir.PointerType):
                        receiver_val = self.builder.load(gvar)
                    else:
                        receiver_val = gvar
                elif name in self.params:
                    val, ty = self.params[name]
                    # If param is already a pointer, use it directly
                    if isinstance(ty, ir.PointerType):
                        receiver_val = val
                    else:
                        # let binding with struct value - create temporary storage
                        tmp = self.builder._entry_alloca(ty, f"{name}.tmp")  # AGAST #3661
                        self.builder.store(val, tmp)
                        receiver_val = tmp
                elif self._is_const_data(name):
                    # A struct or enum const is read-only data (LARB R60):
                    # a pointer `self` runs on a copy of it, as ritz1's
                    # emit_expr_method does (AGAST #4589, #4593), so no
                    # method can write the constant.
                    gvar = self._const_data_global(name)
                    tmp = self.builder._entry_alloca(gvar.type.pointee, f"{name}.copy")
                    self.builder.store(self.builder.load(gvar), tmp)
                    receiver_val = tmp
                else:
                    raise self._err(f"Unknown variable: {name}")
            else:
                # For other lvalues (field, index), use normal lvalue_addr
                receiver_val = self._emit_lvalue_addr(expr.expr)
        else:
            # Emit as normal expression
            receiver_val = self._emit_expr(expr.expr)
            # If the method expects a pointer receiver but we just computed
            # an rvalue (e.g. `Point { x: 2.0 }.scale(3.0)`), spill to a stack
            # slot so we can pass its address (auto-borrow rvalue).
            if (
                isinstance(first_param_type, ir.PointerType)
                and not isinstance(receiver_val.type, ir.PointerType)
                and receiver_val.type == first_param_type.pointee
            ):
                # A temporary is lent from its own slot, so what `@&self`
                # writes is what its drop sees.
                if receiver_slot is not None:
                    receiver_val = receiver_slot
                else:
                    tmp = self._alloca_in_entry_block(receiver_val.type, "recv.tmp")
                    self.builder.store(receiver_val, tmp)
                    receiver_val = tmp
        return receiver_val

    def _method_explicit_args(self, expr: rast.MethodCall, fn: ir.Function,
                              fn_def, all_args: list) -> None:
        """Append a method call's explicit arguments, auto-borrowing places."""
        # Auto-borrow addressable args when the method expects a pointer param.
        for j, arg in enumerate(expr.args, start=1):
            expected_type = self._fn_param_types(fn)[j] if j < len(self._fn_param_types(fn)) else None
            if j < len(fn_def.params):
                self._check_struct_ptr_arg(arg, fn_def.params[j], expr.method, j + 1)
                self._literal_into_slot(fn_def.params[j].type, arg)
                self._float_slot(fn_def.params[j].type, arg)
            if j < len(fn_def.params) and self._takes_place(fn_def.params[j]):
                all_args.append(self._emit_place_borrow(arg, expected_type, expr.method, j + 1,
                                                         fn_def.params[j]))
                continue
            arg_ritz_type = self._infer_ritz_type(arg)
            arg_is_ref = isinstance(arg_ritz_type, rast.RefType) if arg_ritz_type else False
            arg_is_ptr = isinstance(arg_ritz_type, rast.PtrType) if arg_ritz_type else False
            arg_is_addr_of = isinstance(arg, rast.UnaryOp) and arg.op in ('&', '@', '@&', '&mut')
            if (expected_type is not None and isinstance(expected_type, ir.PointerType)
                    and not (arg_is_ref or arg_is_ptr or arg_is_addr_of)):
                if j < len(fn_def.params):
                    self._check_let_implicit_mut_borrow(arg, fn_def.params[j])
                # Decide from actual emitted types, not inference: an Ident
                # holding a `*T` infers as `T`, and its lvalue address is
                # `T**` — passing that where `T*` is expected broke
                # mausoleum/tome/valet (same hazard as _emit_call's arm).
                val = None
                try:
                    addr = self._emit_lvalue_addr(arg)
                    if addr.type == expected_type:
                        val = addr
                except ValueError:
                    pass
                if val is None:
                    # Already-pointer value, or an rvalue (literal, call
                    # result, ...) that must be spilled to a stack slot so we
                    # can pass its address (auto-borrow rvalue).
                    tmp_val = self._emit_expr(arg)
                    if tmp_val.type == expected_type:
                        val = tmp_val
                    elif (not isinstance(tmp_val.type, ir.PointerType)
                            and tmp_val.type == expected_type.pointee):
                        tmp = self._alloca_in_entry_block(tmp_val.type, "arg.tmp")
                        self.builder.store(tmp_val, tmp)
                        val = tmp
                    else:
                        val = tmp_val
                all_args.append(val)
            else:
                slot = fn_def.params[j].type if j < len(fn_def.params) else None
                # AGAST #1577: at the param's enum, not an outer let's.
                with self._int_slot_context(slot, arg):
                    all_args.append(self._emit_value_arg(
                        arg, slot, lambda a, s=slot: self._emit_param_value(a, s)))

    def _convert_method_args(self, expr: rast.MethodCall, fn: ir.Function,
                             fn_def, all_args: list) -> list:
        """Convert a method call's arguments (receiver led) to their params."""
        # Convert argument types as needed
        converted_args = []
        for i, arg in enumerate(all_args):
            expected_type = self._fn_param_types(fn)[i]
            # all_args[0] is the receiver.
            if i:
                self._check_arg_narrowing(
                    expr.args[i - 1], arg, expected_type,
                    fn_def.params[i].type if i < len(fn_def.params) else None,
                    expr.method, i - 1)
            converted = self._convert_type(arg, expected_type, expr.args[i - 1] if i else None,
                                           arg=i > 0)
            converted_args.append(converted)
        return converted_args
