"""AGAST #2308: a `:&` param bound in its caller's slot, landing in a reference.

    fn f(n:& i32)
        let p: @&i32 = n    # the integer became the pointer: exit -11
        *p = 3

    fn g(p: @&i32)
    fn f(n:& i32)
        g(n)                # -11

`n` reads as the integer, `a:& [N]T` as the array and `h:& *U` as the pointer, but
a reference slot holds the borrow. test_borrow_param_ref_slot.py has the shapes
for a struct; this has what's different for the others:

- WIDTH. `let p: @&i8` recorded no referent, so `*p = 3` stored 8 bytes and `*p`
  loaded 8, with or without a `:&`. A lone `i32` hides that: the program still
  exits 3. So each integer here sits between two neighbours in a `[3]T`, which
  `main` checks after the call, and reads compare in place, where a truncating
  return can't tidy a wide load.
- FIT. Nothing stops an integer read into a pointer slot from being the pointer,
  so a reference to anything else is refused, with a location.

`*i32` isn't here: that's #2280's.
"""

import re

import pytest

from test_borrow_param_ref_field import _compile, _run

INTS = ["i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64"]
FLOATS = ["f32", "f64"]

TYPES = "struct C\n    x: i32\n    y: i64\n\n"
METHOD_TYPES = "struct S\n    v: i32\n\n"


def _lit(t: str, v: int) -> str:
    return f"{v}.0" if t in FLOATS else str(v)


def _neighbours(t: str, call: str, middle: int = 1) -> str:
    """`call` on the middle of three `T`s, which it should leave 3, alone."""
    one = _lit(t, 1)
    return f"""
pub fn main() -> i32
    var a: [3]{t} = [{one}, {_lit(t, middle)}, {one}]
    {call}
    if (a[0] as i32) != 1
        return 41
    if (a[2] as i32) != 1
        return 42
    return a[1] as i32
"""


def _writes(t: str) -> dict:
    """Each stores through the reference; `T` is an integer or a float."""
    v = _lit(t, 3)
    arg = "@&a[1]"
    through = f"let p: @&{t} = f({arg})\n    *p = {v}"
    return {
        "let": f"fn f(n:& {t})\n    let p: @&{t} = n\n    *p = {v}\n" + _neighbours(t, f"f({arg})"),
        "var": f"fn f(n:& {t})\n    var p: @&{t} = n\n    *p = {v}\n" + _neighbours(t, f"f({arg})"),
        "argument": f"fn g(p: @&{t})\n    *p = {v}\n\nfn f(n:& {t})\n    g(n)\n"
                    + _neighbours(t, f"f({arg})"),
        "second_argument": f"fn g(k: i32, p: @&{t})\n    *p = {v}\n\nfn f(n:& {t})\n    g(0, n)\n"
                           + _neighbours(t, f"f({arg})"),
        "return": f"fn f(n:& {t}) -> @&{t}\n    return n\n" + _neighbours(t, through),
        "grouped_return": f"fn f(n:& {t}) -> @&{t}\n    return (n)\n" + _neighbours(t, through),
        "tail": f"fn f(n:& {t}) -> @&{t}\n    n\n" + _neighbours(t, through),
        "generic_return": "fn id<T>(c:& T) -> @&T\n    return c\n"
                          + _neighbours(t, f"let p: @&{t} = id<{t}>({arg})\n    *p = {v}"),
        "generic_let": "fn id<T>(c:& T) -> @&T\n    let p: @&T = c\n    return p\n"
                       + _neighbours(t, f"let p: @&{t} = id<{t}>({arg})\n    *p = {v}"),
        "generic_let_store": "fn id<T>(c:& T, v: T)\n    let p: @&T = c\n    *p = v\n"
                             + _neighbours(t, f"id<{t}>({arg}, {v})"),
        "generic_argument": "fn g<T>(p: @&T, v: T)\n    *p = v\n\nfn id<T>(c:& T, v: T)\n    g<T>(c, v)\n"
                            + _neighbours(t, f"id<{t}>({arg}, {v})"),
        "copied": f"fn f(n:& {t})\n    let p: @&{t} = n\n    let q: @&{t} = p\n    *q = {v}\n"
                  + _neighbours(t, f"f({arg})"),
        "untyped_from_return": f"fn f(n:& {t}) -> @&{t}\n    return n\n"
                               + _neighbours(t, f"let p = f({arg})\n    *p = {v}"),
        "untyped_from_generic": "fn id<T>(c:& T) -> @&T\n    return c\n"
                                + _neighbours(t, f"let p = id<{t}>({arg})\n    *p = {v}"),
        "deref_of_call": f"fn f(n:& {t}) -> @&{t}\n    return n\n"
                         + _neighbours(t, f"*f({arg}) = {v}"),
        "method_argument": METHOD_TYPES + f"""\
impl S
    fn put(self: @&S, p: @&{t})
        *p = {v}

fn f(n:& {t}, s: @&S)
    s.put(n)
""" + _neighbours(t, f"var s: S = S {{ v: 0 }}\n    f({arg}, @&s)"),
        "method_param": METHOD_TYPES + f"""\
impl S
    fn go(self: @&S, n:& {t})
        let p: @&{t} = n
        *p = {v}
""" + _neighbours(t, f"var s: S = S {{ v: 0 }}\n    s.go({arg})"),
        "method_return": METHOD_TYPES + f"""\
impl S
    fn go(self: @&S, n:& {t}) -> @&{t}
        return n
""" + _neighbours(t, f"var s: S = S {{ v: 0 }}\n    let p: @&{t} = s.go({arg})\n    *p = {v}"),
        "method_tail": METHOD_TYPES + f"""\
impl S
    fn go(self: @&S, n:& {t}) -> @&{t}
        n
""" + _neighbours(t, f"var s: S = S {{ v: 0 }}\n    let p: @&{t} = s.go({arg})\n    *p = {v}"),
        "method_untyped": METHOD_TYPES + f"""\
impl S
    fn go(self: @&S, n:& {t}) -> @&{t}
        return n
""" + _neighbours(t, f"var s: S = S {{ v: 0 }}\n    let p = s.go({arg})\n    *p = {v}"),
        # No `:&` in sight: this is the local that recorded no referent.
        "plain_local": _neighbours(t, f"let p: @&{t} = @&a[1]\n    *p = {v}"),
        "plain_returned": f"fn f(p: @&{t}) -> @&{t}\n    return p\n"
                          + _neighbours(t, f"*f({arg}) = {v}"),
    }


def _int_only(t: str) -> dict:
    """What leans on `n` being an integer local: #1668 hasn't bound a float so."""
    v = _lit(t, 3)
    arg = "@&a[1]"
    by_value = f"let r: {t} = f({arg})\n    a[1] = r"
    return {
        "shared_let": f"fn f(n:& {t}) -> {t}\n    let p: @{t} = n\n    n = {v}\n    return *p\n"
                      + _neighbours(t, by_value),
        "shared_var": f"fn f(n:& {t}) -> {t}\n    var p: @{t} = n\n    n = {v}\n    return *p\n"
                      + _neighbours(t, by_value),
        "shared_argument": f"fn g(p: @{t}) -> {t}\n    return *p\n\nfn f(n:& {t}) -> {t}\n    n = {v}\n    return g(n)\n"
                           + _neighbours(t, by_value),
        "shared_return": f"fn f(n:& {t}) -> @{t}\n    return n\n"
                         + _neighbours(t, f"let p: @{t} = f({arg})\n    a[1] = {v}\n    let r: {t} = *p\n    a[1] = r"),
        "pass_on": f"fn g(m:& {t})\n    m = {v}\n\nfn f(n:& {t})\n    g(n)\n" + _neighbours(t, f"f({arg})"),
        "pass_on_then_bound": f"fn g(m:& {t})\n    let p: @&{t} = m\n    *p = {v}\n\nfn f(n:& {t})\n    g(n)\n"
                              + _neighbours(t, f"f({arg})"),
    }


def _reads(t: str) -> dict:
    """`*p` compared where it's read.  A wide load picks up the neighbour's
    bytes, and a narrow value in the wrong sign doesn't match."""
    v = "-3" if t.startswith("i") else "200"
    head = f"pub fn main() -> i32\n    var a: [3]{t} = [1, {v}, 1]\n"
    tail = f"    if *p == {v}\n        return 3\n    return 50\n"
    out = {}
    for form, slot, addr in (("shared", f"@{t}", "@"), ("mut", f"@&{t}", "@&")):
        out[f"read_{form}"] = f"fn f(n:& {t}) -> i32\n    let p: {slot} = n\n{tail}\n{head}    return f(@&a[1])\n"
        out[f"read_{form}_param"] = (f"fn g(p: {slot}) -> i32\n{tail}\nfn f(n:& {t}) -> i32\n    return g(n)\n\n"
                                     f"{head}    return f(@&a[1])\n")
        out[f"read_{form}_plain"] = f"{head}    let p: {slot} = {addr}a[1]\n{tail}"
    return out


# `:& f64` and `:& bool` read as the pointer until #1668, so these only lean on
# the local recording its referent.
FLOAT_READS = {}
for ft in FLOATS:
    FLOAT_READS[f"{ft}_read"] = f"""\
fn f(n:& {ft}) -> i32
    let p: @{ft} = n
    if *p == 3.0
        return 3
    return 50

pub fn main() -> i32
    var a: [3]{ft} = [1.0, 3.0, 1.0]
    return f(@&a[1])
"""
    FLOAT_READS[f"{ft}_read_param"] = f"""\
fn g(p: @{ft}) -> {ft}
    return *p

pub fn main() -> i32
    var n: {ft} = 3.0
    return g(@n) as i32
"""

BOOLS = {
    # `*p = true` stored i64 over the neighbours.
    "let": ("fn f(n:& bool)\n    let p: @&bool = n\n    *p = true\n", "f(@&a[1])"),
    "var": ("fn f(n:& bool)\n    var p: @&bool = n\n    *p = true\n", "f(@&a[1])"),
    "return": ("fn f(n:& bool) -> @&bool\n    return n\n", "let p: @&bool = f(@&a[1])\n    *p = true"),
    "tail": ("fn f(n:& bool) -> @&bool\n    n\n", "let p: @&bool = f(@&a[1])\n    *p = true"),
    "generic_return": ("fn id<T>(c:& T) -> @&T\n    return c\n",
                       "let p: @&bool = id<bool>(@&a[1])\n    *p = true"),
    "untyped_from_return": ("fn f(p: @&bool) -> @&bool\n    return p\n", "let q = f(@&a[1])\n    *q = true"),
}
BOOL_MAIN = """
pub fn main() -> i32
    var a: [3]bool = [true, false, true]
    CALL
    if a[0] and a[1] and a[2]
        return 3
    return 40
"""

ARRAY_MAIN = """
pub fn main() -> i32
    var a: [2]T = [ONE, ONE]
    CALL
    return a[1] as i32
"""


def _arrays(t: str) -> dict:
    one, three = _lit(t, 1), _lit(t, 3)
    store = f"*p = [{one}, {three}]"
    through = f"let p: @&[2]{t} = f(@&a)\n    {store}"
    shared = f"let p: @[2]{t} = f(@&a)\n    a[1] = {three}\n    let v: [2]{t} = *p\n    a[1] = v[1]"

    def main(call: str) -> str:
        return ARRAY_MAIN.replace("T", t).replace("ONE", one).replace("CALL", call)

    return {
        "let": f"fn f(a:& [2]{t})\n    let p: @&[2]{t} = a\n    {store}\n" + main("f(@&a)"),
        "var": f"fn f(a:& [2]{t})\n    var p: @&[2]{t} = a\n    {store}\n" + main("f(@&a)"),
        "return": f"fn f(a:& [2]{t}) -> @&[2]{t}\n    return a\n" + main(through),
        "tail": f"fn f(a:& [2]{t}) -> @&[2]{t}\n    a\n" + main(through),
        "argument": f"fn g(p: @&[2]{t})\n    {store}\n\nfn f(a:& [2]{t})\n    g(a)\n" + main("f(@&a)"),
        "pass_on": f"fn g(b:& [2]{t})\n    b[1] = {three}\n\nfn f(a:& [2]{t})\n    g(a)\n" + main("f(@&a)"),
        "shared_let": f"fn f(a:& [2]{t}) -> {t}\n    let p: @[2]{t} = a\n    a[1] = {three}\n"
                      f"    let v: [2]{t} = *p\n    return v[1]\n"
                      + main(f"let r: {t} = f(@&a)\n    a[1] = r"),
        "shared_return": f"fn f(a:& [2]{t}) -> @[2]{t}\n    return a\n" + main(shared),
        "generic_return": "fn id<T>(c:& T) -> @&T\n    return c\n"
                          + main(f"let p: @&[2]{t} = id<[2]{t}>(@&a)\n    {store}"),
    }


POINTER_MAIN = """
pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var d: C = C { x: 3, y: 0 }
    var q: *C = @&c
    CALL
    return q.x
"""
POINTER_INT_MAIN = """
pub fn main() -> i32
    var a: i32 = 1
    var b: i32 = 3
    var q: *i32 = @&a
    CALL
    return *q
"""

POINTERS = {
    "let": TYPES + "fn go(h:& *C, d: *C)\n    let p: @&*C = h\n    *p = d\n"
           + POINTER_MAIN.replace("CALL", "go(@&q, @&d)"),
    "var": TYPES + "fn go(h:& *C, d: *C)\n    var p: @&*C = h\n    *p = d\n"
           + POINTER_MAIN.replace("CALL", "go(@&q, @&d)"),
    "return": TYPES + "fn go(h:& *C) -> @&*C\n    return h\n"
              + POINTER_MAIN.replace("CALL", "let p: @&*C = go(@&q)\n    *p = @&d"),
    "tail": TYPES + "fn go(h:& *C) -> @&*C\n    h\n"
            + POINTER_MAIN.replace("CALL", "let p: @&*C = go(@&q)\n    *p = @&d"),
    "shared_let": TYPES + "fn go(h:& *C, d: *C) -> i32\n    let p: @*C = h\n    h = d\n"
                  "    let r: *C = *p\n    return r.x\n"
                  + POINTER_MAIN.replace("CALL", "let r: i32 = go(@&q, @&d)\n    q.x = r"),
    "integer_let": "fn go(h:& *i32, d: *i32)\n    let p: @&*i32 = h\n    *p = d\n"
                   + POINTER_INT_MAIN.replace("CALL", "go(@&q, @&b)"),
    "integer_return": "fn go(h:& *i32) -> @&*i32\n    return h\n"
                      + POINTER_INT_MAIN.replace("CALL", "let p: @&*i32 = go(@&q)\n    *p = @&b"),
    "sign_blind": "fn go(h:& *u32) -> @&*i32\n    return h\n\npub fn main() -> i32\n    var n: u32 = 3\n"
                  "    var q: *u32 = @&n\n    go(@&q)\n    return *q as i32\n",
    # `@&*T` is a reference to a pointer, whatever T turns out to be.
    "generic_let": TYPES + "fn go<T>(h:& *T, d: *T)\n    let p: @&*T = h\n    *p = d\n"
                   + POINTER_MAIN.replace("CALL", "go<C>(@&q, @&d)"),
    "generic_return": TYPES + "fn go<T>(h:& *T) -> @&*T\n    return h\n"
                      + POINTER_MAIN.replace("CALL", "let p: @&*C = go<C>(@&q)\n    *p = @&d"),
    # A generic fn clones what it doesn't substitute, too.
    "in_a_generic": "fn go<T>(h:& *i32, d: *i32, t: T)\n    let p: @&*i32 = h\n    *p = d\n"
                    + POINTER_INT_MAIN.replace("CALL", "go<i64>(@&q, @&b, 0)"),
    "generic_integer_let": "fn go<T>(h:& *T, d: *T)\n    let p: @&*T = h\n    *p = d\n"
                           + POINTER_INT_MAIN.replace("CALL", "go<i32>(@&q, @&b)"),
    "two_levels_let": TYPES + """\
fn go(h:& **C, d: **C)
    let p: @&**C = h
    *p = d

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var d: C = C { x: 3, y: 0 }
    var q: *C = @&c
    var r: *C = @&d
    var qq: **C = @&q
    go(@&qq, @&r)
    let z: *C = *qq
    return z.x
""",
    "two_levels_return": TYPES + """\
fn go(h:& **C) -> @&**C
    return h

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var d: C = C { x: 3, y: 0 }
    var q: *C = @&c
    var r: *C = @&d
    var qq: **C = @&q
    let p: @&**C = go(@&qq)
    *p = @&r
    let z: *C = *qq
    return z.x
""",
}

# None of these lands in a reference to what's lent, so each still reads it.
BY_VALUE = {
    # `h` reads as the `*C` a `*C` or `@C` holds.
    "pointer_let": TYPES + "fn go(h:& *C) -> *C\n    let p: *C = h\n    return p\n"
                   + POINTER_MAIN.replace("CALL", "let r: *C = go(@&q)\n    r.x = 3"),
    "pointer_return": TYPES + "fn go(h:& *C) -> *C\n    return h\n"
                      + POINTER_MAIN.replace("CALL", "let r: *C = go(@&q)\n    r.x = 3"),
    "pointer_argument": TYPES + "fn g(p: *C)\n    p.x = 3\n\nfn go(h:& *C)\n    g(h)\n"
                        + POINTER_MAIN.replace("CALL", "go(@&q)"),
    "pointer_into_reference_of_the_pointee": TYPES + "fn go(h:& *C)\n    let p: @&C = h\n    p.x = 3\n"
                                             + POINTER_MAIN.replace("CALL", "go(@&q)"),
    # A shadowing binding is the slot's own value, not the param.
    "shadowed_by_let": "var G: i32 = 3\n\nfn f(n:& i32) -> @&i32\n    let n: @&i32 = @&G\n    return n\n\n"
                       "pub fn main() -> i32\n    var k: i32 = 9\n    let p: @&i32 = f(@&k)\n    return *p\n",
    "shadowed_by_var": "var G: i32 = 3\n\nfn f(n:& i32) -> @&i32\n    var n: @&i32 = @&G\n    return n\n\n"
                       "pub fn main() -> i32\n    var k: i32 = 9\n    let p: @&i32 = f(@&k)\n    return *p\n",
    "shadowed_by_integer": "fn g(n: i32) -> i32\n    return n\n\nfn f(n:& i32) -> i32\n    let n: i32 = 3\n"
                           "    return g(n)\n\npub fn main() -> i32\n    var k: i32 = 9\n    return f(@&k)\n",
}
for it in INTS:
    three = _lit(it, 3)
    keep = _neighbours(it, f"a[1] = {three}\n    let r: {it} = f(@&a[1])\n    a[1] = r")
    BY_VALUE[f"{it}_let"] = f"fn f(n:& {it}) -> {it}\n    let d: {it} = n\n    n = 1\n    return d\n" + keep
    BY_VALUE[f"{it}_untyped_let"] = f"fn f(n:& {it}) -> {it}\n    let d = n\n    n = 1\n    return d\n" + keep
    BY_VALUE[f"{it}_return"] = f"fn f(n:& {it}) -> {it}\n    return n\n" + keep
    BY_VALUE[f"{it}_argument"] = f"fn g(m: {it}) -> {it}\n    return m\n\nfn f(n:& {it}) -> {it}\n    return g(n)\n" + keep

PROGRAMS = {}
for it in INTS:
    PROGRAMS.update({f"{it}_{k}": v for k, v in {**_writes(it), **_int_only(it), **_reads(it)}.items()})
for ft in FLOATS:
    PROGRAMS.update({f"{ft}_{k}": v for k, v in _writes(ft).items()})
PROGRAMS.update(FLOAT_READS)
PROGRAMS.update({f"bool_{k}": body + BOOL_MAIN.replace("CALL", call) for k, (body, call) in BOOLS.items()})
for at in ["i8", "i16", "i32", "i64", "f64"]:
    PROGRAMS.update({f"array_{at}_{k}": v for k, v in _arrays(at).items()})
PROGRAMS.update({f"pointer_{k}": v for k, v in POINTERS.items()})
PROGRAMS.update({
    "array_of_structs_let": TYPES + """\
fn f(a:& [2]C) -> i32
    let p: @&[2]C = a
    let v: [2]C = *p
    return v[1].x

pub fn main() -> i32
    var a: [2]C = [C { x: 1, y: 0 }, C { x: 3, y: 0 }]
    return f(@&a)
""",
    "array_of_structs_return": TYPES + """\
fn f(a:& [2]C) -> @&[2]C
    return a

pub fn main() -> i32
    var a: [2]C = [C { x: 1, y: 0 }, C { x: 3, y: 0 }]
    let p: @&[2]C = f(@&a)
    let v: [2]C = *p
    return v[1].x
""",
    "array_rows_let": """\
fn f(a:& [2][2]i32) -> i32
    let p: @&[2][2]i32 = a
    return a[1][1]

pub fn main() -> i32
    var a: [2][2]i32
    a[1][1] = 3
    return f(@&a)
""",
    "array_rows_return": """\
fn f(a:& [2][2]i32) -> @&[2][2]i32
    return a

pub fn main() -> i32
    var a: [2][2]i32
    a[1][1] = 3
    f(@&a)
    return a[1][1]
""",
    # The next function reuses a param's LocalVar.
    "flag_does_not_leak": """\
fn a(n:& i32) -> i32
    return n

fn g(p: @&i32)
    *p = 3

fn b(q: @&i32)
    g(q)

pub fn main() -> i32
    var n: i32 = 1
    a(@&n)
    b(@&n)
    return n
""",
    "alias_slot": """\
type R = @&i32

fn f(n:& i32) -> R
    return n

pub fn main() -> i32
    var n: i32 = 1
    let p: R = f(@&n)
    *p = 3
    return n
""",
    "alias_referent": """\
type W = i32

fn f(n:& W) -> @&W
    return n

pub fn main() -> i32
    var n: W = 1
    let p: @&W = f(@&n)
    *p = 3
    return n
""",
    # As in ritz0's _borrow_for_ref_slot it's the LLVM type that has to match.
    "sign_blind": """\
fn f(n:& u32)
    let p: @&i32 = n
    *p = 3

pub fn main() -> i32
    var n: u32 = 1
    f(@&n)
    return n as i32
""",
    "static_method_argument": METHOD_TYPES + """\
impl S
    fn put(p: @&i32)
        *p = 3

fn f(n:& i32)
    S.put(n)

pub fn main() -> i32
    var n: i32 = 1
    f(@&n)
    return n
""",
    "method_shared_argument": METHOD_TYPES + """\
impl S
    fn get(self: @&S, p: @i32) -> i32
        return *p

fn f(n:& i32, s: @&S) -> i32
    return s.get(n)

pub fn main() -> i32
    var s: S = S { v: 0 }
    var n: i32 = 3
    return f(@&n, @&s)
""",
    "deref_of_call_read": """\
fn f(n:& i8) -> @i8
    return n

pub fn main() -> i32
    var a: [3]i8 = [1, 3, 1]
    if *f(@&a[1]) == 3
        return 3
    return 50
""",
    "float_deref_of_call": """\
fn f(p: @&f64) -> @&f64
    return p

pub fn main() -> i32
    var n: f64 = 1.0
    *f(@&n) = 3.0
    return n as i32
""",
    "through_pointer_to_pointer": TYPES + """\
pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var d: C = C { x: 3, y: 0 }
    var p: *C = @&c
    var pp: **C = @&p
    *pp = @&d
    return p.x
""",
})

# Each is a located error on both compilers: the slot refers to something else.
D = "struct D\n    a: i32\n\n"
ENTRY = "\npub fn main() -> i32\n    return 0\n"
MISFITS = {
    "wider": "fn f(n:& i32)\n    let p: @&i64 = n\n    *p = 3\n",
    "narrower": "fn f(n:& i64) -> @i32\n    return n\n",
    "wider_tail": "fn f(n:& i32) -> @i64\n    n\n",
    "float_of_the_same_size": "fn f(n:& i64)\n    let p: @&f64 = n\n",
    "bool_of_the_same_size": "fn f(n:& i8)\n    let p: @&bool = n\n",
    "pointer_of_the_same_size": "fn f(n:& i64)\n    let p: @&*i64 = n\n",
    "struct": TYPES + "fn f(n:& i32)\n    let p: @&C = n\n",
    "array": "fn f(n:& i32)\n    let p: @&[1]i32 = n\n",
    "array_length": "fn f(a:& [2]i32)\n    let p: @&[3]i32 = a\n",
    "array_length_returned": "fn f(a:& [2]i32) -> @&[3]i32\n    return a\n",
    "array_element": "fn f(a:& [2]i32)\n    let p: @&[2]i64 = a\n",
    "array_element_struct": TYPES + D + "fn f(a:& [2]C)\n    let p: @&[2]D = a\n",
    "array_to_its_element": "fn f(a:& [2]i32)\n    let p: @&i32 = a\n",
}
MISFIT_ARGUMENTS = {
    "wider": "fn g(p: @&i64)\n    *p = 3\n\nfn f(n:& i32)\n    g(n)\n",
    "array_to_its_element": "fn g(p: @&i32)\n    *p = 3\n\nfn f(a:& [2]i32)\n    g(a)\n",
}
METHOD_MISFIT = METHOD_TYPES + """\
impl S
    fn put(self: @&S, p: @&i64)
        *p = 3

fn f(n:& i32, s: @&S)
    s.put(n)
"""

# #2325: ritz0 refuses these, so a `:& *U` isn't lent to an argument on either.
POINTER_ARG_REFUSED = {
    "argument": TYPES + "fn g(p: @&*C, d: *C)\n    *p = d\n\nfn go(h:& *C, d: *C)\n    g(h, d)\n",
    "pass_on": TYPES + "fn g(m:& *C, d: *C)\n    m = d\n\nfn go(h:& *C, d: *C)\n    g(h, d)\n",
}
# #2325: ritz0 accepts these, and shouldn't.
ANOTHER_POINTER = {
    "struct": TYPES + D + "fn f(h:& *C)\n    let p: @&*D = h\n",
    "integer": "fn f(h:& *i32)\n    let p: @&*i64 = h\n",
}

RITZ0_GAPS = {
    **{f"u8_read_{form}": "AGAST #2326: `*p == 200` through `@u8` is false on ritz0"
       for form in ("shared", "shared_param", "shared_plain", "mut", "mut_param", "mut_plain")},
    "static_method_argument": "AGAST #2326: ritz0 reads the referent into a static method's `@&T`",
}


def _params(programs, gaps):
    return [pytest.param(name, marks=[pytest.mark.xfail(strict=True, reason=gaps[name])]
                         if name in gaps else [])
            for name in sorted(programs)]


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_takes_the_borrow_at_its_width(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, PROGRAMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", _params(PROGRAMS, RITZ0_GAPS))
def test_ritz0_is_the_oracle(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, PROGRAMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(BY_VALUE))
def test_a_slot_of_the_value_still_reads_it(ritz1_bin, tmp_path, compiler, name):
    assert _run(compiler, ritz1_bin, tmp_path, name, BY_VALUE[name]) == 3


def _refused(comp, ll, out_re):
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out[-2000:]
    assert not ll.exists()
    assert re.search(out_re, out), out[-2000:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(MISFITS))
def test_a_reference_to_something_else_is_located_and_refused(ritz1_bin, tmp_path, compiler, name):
    comp, ll, _ = _compile(compiler, ritz1_bin, tmp_path, name, MISFITS[name] + ENTRY)
    _refused(comp, ll, r"main\.ritz:\d+:\d+.*parameter can't be held in a reference to another type")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(MISFIT_ARGUMENTS))
def test_an_argument_to_something_else_is_located_and_refused(ritz1_bin, tmp_path, compiler, name):
    comp, ll, _ = _compile(compiler, ritz1_bin, tmp_path, name, MISFIT_ARGUMENTS[name] + ENTRY)
    _refused(comp, ll, r"main\.ritz:\d+:\d+.*argument \d of `\w+` has the wrong type")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", [
    pytest.param("ritz0", marks=pytest.mark.xfail(
        strict=True, reason="AGAST #2326: ritz0 doesn't check a `:&` going to a method's `@&T`")),
    "ritz1"])
def test_a_method_argument_to_something_else_is_located_and_refused(ritz1_bin, tmp_path, compiler):
    comp, ll, _ = _compile(compiler, ritz1_bin, tmp_path, "method", METHOD_MISFIT + ENTRY)
    _refused(comp, ll, r"main\.ritz:\d+:\d+.*argument \d of `\w+` has the wrong type")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(POINTER_ARG_REFUSED))
def test_a_pointer_param_is_not_lent_to_an_argument(ritz1_bin, tmp_path, compiler, name):
    comp, ll, _ = _compile(compiler, ritz1_bin, tmp_path, name, POINTER_ARG_REFUSED[name] + ENTRY)
    _refused(comp, ll, r"main\.ritz:\d+:\d+.*argument 1 of `g` has the wrong type")


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ANOTHER_POINTER))
def test_ritz1_refuses_a_reference_to_another_pointer(ritz1_bin, tmp_path, name):
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, name, ANOTHER_POINTER[name] + ENTRY)
    _refused(comp, ll, r"main\.ritz:\d+:\d+.*parameter can't be held in a reference to another type")


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2325: ritz0 keeps the `*C` in a `@&*D`")
@pytest.mark.parametrize("name", sorted(ANOTHER_POINTER))
def test_ritz0_refuses_a_reference_to_another_pointer(tmp_path, name):
    comp, ll, _ = _compile("ritz0", None, tmp_path, name, ANOTHER_POINTER[name] + ENTRY)
    _refused(comp, ll, r"main\.ritz:\d+:\d+.*can't be held in a reference to another type")


METHOD_DEREF = METHOD_TYPES + """\
impl S
    fn go(self: @&S, n:& i8) -> @&i8
        return n

pub fn main() -> i32
    var s: S = S { v: 0 }
    var a: [3]i8 = [1, 1, 1]
    *s.go(@&a[1]) = 3
    if a[2] != 1
        return 42
    return a[1] as i32
"""


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2327: `*x.m()` has no pointee width")
def test_ritz1_deref_of_a_method_call_stores_its_width(ritz1_bin, tmp_path):
    assert _run("ritz1", ritz1_bin, tmp_path, "method_deref", METHOD_DEREF) == 3


POINTER_VALUE_RETURN = {
    "plain": TYPES + """\
fn f(p: *C) -> @&C
    return p

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    let r: @&C = f(@c)
    return r.x
""",
    "lent": TYPES + "fn go(h:& *C) -> @&C\n    return h\n"
            + POINTER_MAIN.replace("CALL", "let r: @&C = go(@&q)\n    r.x = 3"),
}


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2327: a `*C` value into `-> @&C` fails at clang")
@pytest.mark.parametrize("name", sorted(POINTER_VALUE_RETURN))
def test_ritz1_pointer_value_returned_as_a_reference(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, POINTER_VALUE_RETURN[name]) == 3
