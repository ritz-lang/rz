#!/usr/bin/env python3
"""A generic struct's literal may leave out its type arguments (§9.2).

`Box2 { v: x }` for `struct Box2<X>` names no instance.  ritz0 crashed
(`ValueError: Unknown struct: Box2`, a Python traceback), and ritz1 gave
unrelated errors or wrote `alloca %Cell`, an unsized type clang refuses.  #3311
made each compiler refuse the literal where it is written:

    file:line:col: `Box2` is generic: write its type arguments, `Box2<X> { .. }`

LARB R51 (AGAST #3314) rules that the literal infers them, and ritz0 does
(#3407):

1. The slot it fills decides: a typed `let`/`var`, a parameter, a field, the
   fn's return type (tail or `return`).  A literal field value takes the
   slot's type, and a value of another type is that field's type error.
2. With no slot (an untyped `let`/`var`), the field values bind them by
   section 4.4's call rule: `Box2 { v: 1 }` is `Box2<i64>`, as `Present(1)` is.
   An untyped `let` doesn't look at the fn's return type.
3. A param neither binds is an error at the literal:
   "can't infer `X` for `Box2`: write its type arguments, `Box2<X> { .. }`".
4. A spelled-out `Box2<u8> { .. }` is unchanged.

The inferred args are the literal's `type_args`, as if written, so the move
checker sees `Box2 { v: <a Drop T> }` move (test_ownership_drops_ritz0).
ritz1 and ritz1_selfhosted infer them the same way (#3408): generic_infer's
gi_struct_lit_args renames the literal to the instance, `Box2$u8`, before
monomorph, as if spelled out.  #3311's refused rows (an untyped let, a typed
let, a tail, an argument, two params, a generic fn, an `impl<X>` method, the
built-in Span) are each an INFERS row now.

Each row separates a path (docs/TESTING.md, "What a ritz0 pytest case costs").
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import batching
import fast_link
from ritz0_inproc import run_ritz0

pytestmark = [pytest.mark.integration, pytest.mark.batched]

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# Lines 1-7: a plain struct, a one- and a two-parameter generic struct.
HEAD = ("struct T\n    id: i32\n"
        "struct Box2<X>\n    v: X\n"
        "struct Two<A, B>\n    a: A\n    b: B\n")

# A generic struct no field binds: only a slot or written-out args can.
TAGGED = "struct Tagged<X>\n    n: i32\n"

# Each compiler infers (LARB R51).  `sizeof(b.v)` tells the instance: 1 for u8, 2 for
# u16, 8 for i64.  name -> (source after HEAD, exit code)
INFERS = {
    # Rule 1, each slot.  A literal `3` alone is an i64 (83); the slot makes it a u8.
    "slot_let": ("fn main() -> i32\n    let b: Box2<u8> = Box2 { v: 3 }\n"
                 "    sizeof(b.v) as i32 * 10 + b.v as i32\n", 13),
    "slot_var": ("fn main() -> i32\n    var b: Box2<u16> = Box2 { v: 3 }\n"
                 "    sizeof(b.v) as i32 * 10 + b.v as i32\n", 23),
    "slot_param": ("fn f(b: Box2<u16>) -> i32\n    sizeof(b.v) as i32 * 10 + b.v as i32\n"
                   "fn main() -> i32\n    f(Box2 { v: 4 })\n", 24),
    "slot_method_param": ("impl T\n    fn put(self: @T, b: Box2<u8>) -> i32\n"
                          "        sizeof(b.v) as i32 * 10 + b.v as i32 + self.id\n"
                          "fn main() -> i32\n    let t = T { id: 1 }\n"
                          "    t.put(Box2 { v: 4 })\n", 15),
    "slot_tail": ("fn mk() -> Box2<u8>\n    Box2 { v: 5 }\n"
                  "fn main() -> i32\n    let b = mk()\n"
                  "    sizeof(b.v) as i32 * 10 + b.v as i32\n", 15),
    # A `return`, and the tail through an `if`.
    "slot_return": ("fn mk(x: bool) -> Box2<u8>\n    if x\n        return Box2 { v: 6 }\n"
                    "    if x\n        Box2 { v: 1 }\n    else\n        Box2 { v: 2 }\n"
                    "fn main() -> i32\n    let b = mk(true)\n    let c = mk(false)\n"
                    "    sizeof(b.v) as i32 * 10 + b.v as i32 + c.v as i32\n", 18),
    # A field: of a plain struct, and of a spelled-out generic one.
    "slot_field": ("struct Outer\n    b: Box2<u8>\n"
                   "fn main() -> i32\n    let o = Outer { b: Box2 { v: 8 } }\n"
                   "    let w = Box2<Box2<u16>> { v: Box2 { v: 1 } }\n"
                   "    sizeof(o.b.v) as i32 * 10 + o.b.v as i32 + sizeof(w.v.v) as i32 * 100\n",
                   218),
    # ...where only the field names it: `Tagged`'s fields don't mention X, so
    # without the slot each literal is rule 3's error.  (slot_field's sizeof
    # reads the outer field's type, so it can't see an inner Box2<i64>.)
    "slot_field_only": ("struct Tagged<X>\n    n: i32\nstruct Holder\n    t: Tagged<u8>\n"
                        "fn main() -> i32\n    let h = Holder { t: Tagged { n: 1 } }\n"
                        "    let b = Box2<Tagged<u16>> { v: Tagged { n: 2 } }\n"
                        "    h.t.n + b.v.n * 10\n", 21),
    # Rule 2: an untyped let, from a typed value and a struct value.
    "untyped_from_field": ("fn main() -> i32\n    let x: u16 = 7\n    let a = Box2 { v: x }\n"
                           "    var b = Box2 { v: T { id: 1 } }\n"
                           "    sizeof(a.v) as i32 * 10 + a.v as i32 + b.v.id * 100\n", 127),
    # ...a literal is an i64, and each of two params binds on its own.
    "untyped_literal_i64": ("fn main() -> i32\n    let x: u8 = 2\n    let b = Box2 { v: 9 }\n"
                            "    let t = Two { a: 1, b: x }\n"
                            "    sizeof(b.v) as i32 * 10 + b.v as i32 + sizeof(t.b) as i32 * 100\n",
                            189),
    # An untyped let doesn't borrow the fn's return type: `b` is a Box2<i64>.
    "untyped_ignores_return": ("fn mk() -> Box2<u8>\n    let b = Box2 { v: 2 }\n"
                               "    Box2 { v: sizeof(b.v) as u8 }\nfn main() -> i32\n"
                               "    mk().v as i32\n", 8),
    # A field's value is walked: a generic call in it infers (it raised
    # "needs explicit type arguments"), as a nested literal does.
    "call_in_field": ("fn id<U>(x: U) -> U\n    x\nfn main() -> i32\n    let x: i32 = 4\n"
                      "    let t = T { id: id(x) }\n    t.id\n", 4),
    # A generic fn's template and an `impl<X>` method (#3310's args-less
    # spelling): `Box2<U>` / `Box2<X>`, substituted per instance.
    "generic_fn": ("fn g<U>(x: U) -> Box2<U>\n    let b = Box2 { v: x }\n    Box2 { v: b.v }\n"
                   "fn main() -> i32\n    let b = g<u8>(3)\n"
                   "    sizeof(b.v) as i32 * 10 + b.v as i32\n", 13),
    "impl_method": ("impl<X> Box2<X>\n    fn again(self: @Box2<X>) -> Box2<X>\n"
                    "        Box2 { v: self.v }\n"
                    "fn main() -> i32\n    let u = Box2<u8> { v: 9 }\n"
                    "    let w = u.again()\n    sizeof(w.v) as i32 * 10 + w.v as i32\n", 19),
    # The built-in Span<T> with no `import ritzlib.span` (AGAST #3357).
    "builtin_span": ("fn main() -> i32\n    var a: [3]u8 = [1, 2, 3]\n"
                     "    let s: Span<u8> = Span { ptr: @a[0], len: 3 }\n"
                     "    let t = Span { ptr: @a[1], len: 2 }\n"
                     "    (s.len + t.len) as i32 * 10 + t.ptr[1] as i32\n", 53),
}

# name -> (source after HEAD, line:col, the error)
INFER_ERRORS = {
    # Rule 1: the slot wins, so `true` in a Box2<u8> is the u8 field's error,
    # as in `S { v: true }`; alone it would make a Box2<bool>.
    "slot_vs_field": ("fn main() -> i32\n    let c: Box2<u8> = Box2 { v: true }\n"
                      "    c.v as i32\n", "9:33",
                      "cannot use bool as an integer: write `b as i32`"),
    # Rule 3: no field mentions X.
    "unbound": ("struct Tagged<X>\n    n: i32\n"
                "fn main() -> i32\n    let t = Tagged { n: 1 }\n    t.n\n", "11:13",
                "can't infer `X` for `Tagged`: write its type arguments, `Tagged<X> { .. }`"),
    # ...and the advice spells every param, the unbound one second.
    "unbound_second": ("struct Tag2<A, B>\n    a: A\n    n: i32\n"
                       "fn main() -> i32\n    let t = Tag2 { a: 1, n: 2 }\n    t.n\n", "12:13",
                       "can't infer `B` for `Tag2`: write its type arguments, `Tag2<A, B> { .. }`"),
    # ...or two fields bind it differently.
    "conflict": ("struct Pair<X>\n    a: X\n    b: X\n"
                 "fn main() -> i32\n    let x: u8 = 1\n    let y: u16 = 2\n"
                 "    let p = Pair { a: x, b: y }\n    0\n", "14:13",
                 "can't infer `X` for `Pair`: write its type arguments, `Pair<X> { .. }`"),
}

# name -> (source after HEAD, exit code): the controls.
RUNS = {
    # A plain struct's literal needs no args, beside generic ones.
    "plain_struct": ("fn main() -> i32\n    let t = T { id: 4 }\n    t.id\n", 4),
    # A program's own non-generic `struct Span` replaces the built-in one
    # (builtin_types.py), so its literal needs no args (AGAST #3357).
    "own_span": ("struct Span\n    n: i32\n"
                 "fn main() -> i32\n    let s = Span { n: 6 }\n    s.n\n", 6),
    # The spelled-out literal, in a fn and in a generic fn's template.
    "spelled_out": ("fn g<U>(x: U) -> Box2<U>\n    Box2<U> { v: x }\nfn main() -> i32\n"
                    "    let b = Box2<T> { v: T { id: 5 } }\n"
                    "    let t = Two<i32, i64> { a: 1, b: 2 }\n"
                    "    b.v.id + g<i32>(t.a).v + t.b as i32\n", 8),
    # In an `impl<X>` method (#3310): `Box2<X>` is the impl's instance, a
    # value through a tail and a typed let.  `size` is 1 only on Box2$u8.
    "impl_method_spelled_out": ("impl<X> Box2<X>\n"
                                "    fn again(self: @Box2<X>) -> Box2<X>\n"
                                "        Box2<X> { v: self.v }\n"
                                "    fn size(self: @Box2<X>) -> i32\n"
                                "        let n: Box2<X> = Box2<X> { v: self.v }\n"
                                "        sizeof(n.v) as i32\n"
                                "fn main() -> i32\n    let b = Box2<i32> { v: 3 }\n"
                                "    let u = Box2<u8> { v: 9 }\n"
                                "    b.again().v * 10 + u.size()\n", 31),
}


ALL = tuple(COMPILERS)

# LARB R51a: ritz0 (#3430), ritz1 and ritz1_selfhosted (#3431, generic_infer).
# name -> (compilers, source, exit code)
R51A_INFERS = {
    # LARB R51a (#3430): a field whose type names none of the outer's
    # params is a slot though the outer literal is args-less.  `Tagged`'s
    # X only the slot binds (it was "can't infer `X`"), and `b`'s `5` is a
    # u8, not a Box2<i64>.
    "known_field": (ALL, TAGGED + "struct W<A>\n    a: A\n    t: Tagged<u8>\n    b: Box2<u8>\n"
                    "fn main() -> i32\n    let w = W { a: 3, t: Tagged { n: 4 }, b: Box2 { v: 5 } }\n"
                    "    w.t.n + w.b.v as i32 * 10 + sizeof(w.b.v) as i32 * 100\n", 154),
    # Two deep: `t`'s slot makes the middle literal a V<u16> (its `2` a u16,
    # not an i64), and its own field the inner one a Tagged<u8>.
    "known_field_nested": (ALL, TAGGED + "struct V<B>\n    b: B\n    u: Tagged<u8>\n"
                           "struct W<A>\n    a: A\n    t: V<u16>\n"
                           "fn main() -> i32\n"
                           "    let w = W { a: 1, t: V { b: 2, u: Tagged { n: 3 } } }\n"
                           "    w.t.u.n + w.t.b as i32 * 10 + sizeof(w.t.b) as i32 * 100\n", 223),
    # A field naming a still-unbound outer param is no slot: the inner
    # literal infers from its fields (Box2<u8>), and that binds A.
    "outer_param_field": (ALL, "struct W2<A>\n    t: Box2<A>\n"
                          "fn main() -> i32\n    let x: u8 = 5\n    let w = W2 { t: Box2 { v: x } }\n"
                          "    sizeof(w.t.v) as i32 * 10 + w.t.v as i32\n", 15),
    # ...through a pointer (#3516): the inner literal is a Box2<*u8>, and A
    # binds from the `ptr_A` piece of `Box2$ptr_A`, not a whole component.
    # `f` takes only a W3<u8> (any other A is a parameter mismatch): ritz1
    # can't size `*w.t.v` through the instance yet (#3747).
    "outer_param_ptr_field": (ALL, "struct W3<A>\n    t: Box2<*A>\n"
                              "fn f(w: W3<u8>) -> i32\n    *w.t.v as i32 + 10\n"
                              "fn main() -> i32\n    var x: u8 = 7\n    let w = W3 { t: Box2 { v: @x } }\n"
                              "    f(w)\n", 17),
    # ...where the piece is a whole mangled generic: `ptr_A` against
    # `ptr_Box2$u8` binds A = Box2$u8, not `Box2`.  `w.t.v.v` auto-derefs the
    # `*Box2$u8` field of the Box2$ptr_Box2$u8 instance (#3748: it was ritz1's
    # "cannot emit: unhandled EXPR_MEMBER").
    "outer_param_ptr_generic_field": (ALL, "struct W3<A>\n    t: Box2<*A>\n"
                                      "fn f(w: W3<Box2<u8>>) -> i32\n    w.t.v.v as i32 + 10\n"
                                      "fn main() -> i32\n    let x: u8 = 7\n    var b = Box2 { v: x }\n"
                                      "    let w = W3 { t: Box2 { v: @b } }\n"
                                      "    f(w)\n", 17),
    # ...the same read with the args spelled out, so no inference is involved.
    "spelled_ptr_generic_field": (ALL, "struct W3<A>\n    t: Box2<*A>\n"
                                  "fn main() -> i32\n    var b = Box2<u8> { v: 7 }\n"
                                  "    let w = W3<Box2<u8>> { t: Box2<*Box2<u8>> { v: @b } }\n"
                                  "    w.t.v.v as i32 + 10\n", 17),
    # #3748's cause was monomorph: an instance's field type substituted whole
    # `$`-components only, so W3$Box2_u8 kept `t: Box2$ptr_A`.  A two-param
    # outer takes the other path (substitute_params_in_mangled).
    "two_param_ptr_generic_field": (ALL, "struct W9<A, B>\n    t: Box2<*A>\n    n: B\n"
                                    "fn main() -> i32\n    var b = Box2<u8> { v: 7 }\n"
                                    "    let w = W9<Box2<u8>, i32> { t: Box2<*Box2<u8>> { v: @b }, n: 10 }\n"
                                    "    w.t.v.v as i32 + w.n\n", 17),
    # A piece substitutes only after a type constructor (`ptr`, `arr2`...):
    # `My_A` is a struct's own name, not `My` over A.
    "underscored_struct_field": (ALL, "struct My_A\n    n: i32\n"
                                 "struct W10<A>\n    t: Box2<My_A>\n    a: A\n"
                                 "fn main() -> i32\n"
                                 "    let w = W10<u8> { t: Box2<My_A> { v: My_A { n: 9 } }, a: 1 }\n"
                                 "    w.t.v.n + w.a as i32 * 10\n", 19),
    # The same principle: a generic fn's concrete param is its argument's
    # slot, its `6` a u8.
    "generic_fn_known_param": (ALL, TAGGED + "fn g<U>(x: U, t: Tagged<u8>, b: Box2<u8>) -> i32\n"
                               "    t.n + b.v as i32 * 10 + sizeof(b.v) as i32 * 100\n"
                               "fn main() -> i32\n    g(1, Tagged { n: 4 }, Box2 { v: 6 })\n", 164),
}

# name -> (compilers, source after HEAD, line:col, the error)
R51A_ERRORS = {
    # LARB R51a: a partially known field type (`Tag2<u8, A>`, A bound only
    # by another field) is no slot and binds nothing, so the inner literal's
    # X is unbound, the error at the inner literal.
    "partially_known_field": (ALL, "struct Tag2<X, Y>\n    n: i32\n"
                              "struct W<A>\n    a: A\n    t: Tag2<u8, A>\n"
                              "fn main() -> i32\n    let w = W { a: 1, t: Tag2 { n: 1 } }\n"
                              "    w.t.n\n", "14:26",
                              "can't infer `X` for `Tag2`: write its type arguments, "
                              "`Tag2<X, Y> { .. }`"),
    # #3516: a `_`-piece match is exact.  `Two$ptr$u8` (a struct named `ptr`)
    # is no `Two$ptr_A$u8`: A doesn't bind the `u8` past the `$`.
    "ptr_piece_needs_its_param": (ALL, "struct ptr\n    n: i32\n"
                                  "struct W5<A>\n    t: Two<*A, u8>\n"
                                  "fn main() -> i32\n    let y: u8 = 2\n"
                                  "    let w = W5 { t: Two { a: ptr { n: 1 }, b: y } }\n    0\n",
                                  "14:13", "can't infer `A` for `W5`: write its type arguments, "
                                  "`W5<A> { .. }`"),
    # ...and a whole component: `My` is no prefix of `My_B`, so A doesn't bind
    # the `B`.  ritz0, whose mangling differs, refuses the field instead.
    "piece_is_a_whole_component": (("ritz1", "ritz1_selfhosted"),
                                   "struct My\n    n: i32\nstruct My_B\n    n: i32\n"
                                   "struct W6<A>\n    t: Two<My, A>\n"
                                   "fn main() -> i32\n    let x: u8 = 1\n"
                                   "    let w = W6 { t: Two { a: My_B { n: 1 }, b: x } }\n    0\n",
                                   "16:13", "can't infer `A` for `W6`: write its type arguments, "
                                   "`W6<A> { .. }`"),
    # ...nor `Mz`, the same length, for `My`.
    "piece_is_its_name": (("ritz1", "ritz1_selfhosted"),
                          "struct My\n    n: i32\nstruct Mz\n    n: i32\n"
                          "struct W8<A>\n    t: Two<My, A>\n"
                          "fn main() -> i32\n    let x: u8 = 1\n"
                          "    let w = W8 { t: Two { a: Mz { n: 1 }, b: x } }\n    0\n",
                          "16:13", "can't infer `A` for `W8`: write its type arguments, "
                          "`W8<A> { .. }`"),
    # ...nor of `MyX`: a piece matches the whole name.
    "piece_is_a_whole_name": (("ritz1", "ritz1_selfhosted"),
                              "struct My\n    n: i32\nstruct MyX\n    n: i32\n"
                              "struct W7<A>\n    t: Two<My, A>\n"
                              "fn main() -> i32\n    let x: u8 = 1\n"
                              "    let w = W7 { t: Two { a: MyX { n: 1 }, b: x } }\n    0\n",
                              "16:13", "can't infer `A` for `W7`: write its type arguments, "
                              "`W7<A> { .. }`"),
}


def _emit(compiler, path, ll, work):
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{work}")
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll)], cwd=work, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=work, env=env,
                          capture_output=True, text=True, timeout=300)


def _link(compiler, ll, work):
    exe = work / "main"
    cmd = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        cmd.insert(2, str(RITZ_START))
    return fast_link.clang(cmd, cwd=work, capture_output=True, text=True), exe


def _batch_compile(compiler, path, work):
    """batching's `compile`: the compile alone, into `work/main.ll` (AGAST #2867)."""
    comp = _emit(compiler, path, work / "main.ll", work)
    return comp.returncode, comp.stdout + comp.stderr


def _batch_build(compiler, path, work):
    """batching.run's `build`: compile and link a batch the way `_run` does a row."""
    ll = work / "main.ll"
    code, output = _batch_compile(compiler, path, work)
    if code != 0 or not ll.exists():
        return False, output, None
    link, exe = _link(compiler, ll, work)
    return link.returncode == 0, link.stderr, exe


def _run(compiler, work, src):
    got = batching.run(compiler, src, _batch_build, compile=_batch_compile)  # #2806, #2867
    if got is not None:
        return got
    batching.per_row()
    path, ll = work / "main.ritz", work / "main.ll"
    path.write_text(src)
    comp = _emit(compiler, path, ll, work)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused:\n{src}\n{out[-2000:]}"
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, f"{compiler}: would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], timeout=60).returncode


@pytest.fixture
def need_ritz1(request):
    def need(compiler):
        if compiler != "ritz0":
            request.getfixturevalue("ritz1_bin")
    return need


def _refused(compiler, tmp_path, src, where, message, name):
    at = tuple(map(int, where.split(":")))
    got = batching.refused(compiler, src, _batch_compile, at=at)
    if got is not None:  # AGAST #2806: this row's diagnostics from its chunk's batch
        out, where = got
    else:
        batching.per_row()
        path, ll = tmp_path / "main.ritz", tmp_path / "main.ll"
        path.write_text(src)
        comp = _emit(compiler, path, ll, tmp_path)
        out = comp.stdout + comp.stderr
        assert comp.returncode != 0, f"{compiler} accepted {name}:\n{src}\n{out}"
    assert "Traceback" not in out, f"{compiler}: {name} crashed:\n{out[-2000:]}"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert (where, message) in found, \
        f"{compiler}: {name}, wanted {where}: {message}:\n{src}\n{out[-2000:]}"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(INFERS))
def test_an_argless_generic_literal_infers(tmp_path, need_ritz1, compiler, name):
    need_ritz1(compiler)
    body, code = INFERS[name]
    assert _run(compiler, tmp_path, HEAD + body) == code, f"{compiler}, {name}"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(INFER_ERRORS))
def test_an_argless_literal_error_is_located(tmp_path, need_ritz1, compiler, name):
    need_ritz1(compiler)
    body, where, message = INFER_ERRORS[name]
    _refused(compiler, tmp_path, HEAD + body, where, message, name)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_a_literal_that_names_its_struct_builds(tmp_path, need_ritz1, compiler, name):
    need_ritz1(compiler)
    body, code = RUNS[name]
    assert _run(compiler, tmp_path, HEAD + body) == code, f"{compiler}, {name}"


@pytest.mark.parametrize("compiler,name", [(c, n) for n, row in sorted(R51A_INFERS.items())
                                           for c in row[0]])
def test_a_known_field_is_a_slot(tmp_path, need_ritz1, compiler, name):
    need_ritz1(compiler)
    _, body, code = R51A_INFERS[name]
    assert _run(compiler, tmp_path, HEAD + body) == code, f"{compiler}, {name}"


@pytest.mark.parametrize("compiler,name", [(c, n) for n, row in sorted(R51A_ERRORS.items())
                                           for c in row[0]])
def test_a_partly_known_field_error_is_located(tmp_path, need_ritz1, compiler, name):
    need_ritz1(compiler)
    _, body, where, message = R51A_ERRORS[name]
    _refused(compiler, tmp_path, HEAD + body, where, message, name)
