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
