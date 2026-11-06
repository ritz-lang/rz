"""AGAST #2290: `a[i]` on an `a:& [N]T` param is an element of `[N x T]`.

    fn f(a:& [2]i32)
        a[1] = 3            # ritz0: a[1] is 3. ritz1: a[1] stays 1

The param was a reference local, and the index paths took the element type from
nowhere, so they fell back to i64: `store i64` at offset 8, past the end of the
8-byte array, with no diagnostic from ritz1 or clang. A read failed at clang.

It's now an array local whose slot is the array behind the borrow, as an integer
`:&` has been since #1644, so every element path indexes it as the caller's own
array. A bare `a` still reads as the pointer, which is what a reference slot
takes. Indexing trusts the N and T the param declares, so an argument that isn't
that array has to be refused at the call, as ritz0 does.

`[2]i32` is exactly 8 bytes, which hides a wrong-size access, so the grid covers
several sizes and element types and checks the memory around each store. ritz0
is the oracle: every program runs through both compilers.
"""

import re

import pytest

from test_borrow_param_ref_field import _compile, _run

# What each element type stores: a fill value, then two written values.  Each is
# nonzero, and a store of the wrong width changes the neighbours' bytes.
SCALARS = {
    "i8": ("-2", "-3", "-5"),
    "u8": ("200", "201", "202"),
    "i16": ("-300", "-301", "-302"),
    "u16": ("40000", "40001", "40002"),
    "i32": ("-70000", "-70001", "-70002"),
    "u32": ("3000000000", "3000000001", "3000000002"),
    "i64": ("-5000000000", "-5000000001", "-5000000002"),
    "u64": ("5000000000", "5000000001", "5000000002"),
    "f32": ("1.5", "2.5", "3.5"),
    "f64": ("1.5", "2.5", "3.5"),
    "bool": ("true", "false", "true"),
}
SIZES = (2, 3, 8, 17)


def _grid_size(ty: str, n: int, fill: str, first: str, second: str, base: int) -> tuple[str, str]:
    """The fns for `[n]ty`, and the statements in main that check them.

    `pre` and `post` are `ty`, so they touch the array with no padding between:
    a store past the end, or one too wide, lands in them.
    """
    last = n - 1
    decls = f"""
struct Box{n}
    pre: {ty}
    a: [{n}]{ty}
    post: {ty}

fn store_const{n}(a:& [{n}]{ty})
    a[{last}] = {first}

fn store_var{n}(a:& [{n}]{ty}, i: i32, v: {ty})
    a[i] = v

fn read_const{n}(a:& [{n}]{ty}) -> {ty}
    return a[{last}]

fn read_var{n}(a:& [{n}]{ty}, i: i32) -> {ty}
    return a[i]

fn intact{n}(b:& Box{n}, skip: i32, skip2: i32) -> i32
    if b.pre != {fill}
        return 1
    if b.post != {fill}
        return 2
    var i: i32 = 0
    while i < {n}
        if i != skip and i != skip2 and b.a[i] != {fill}
            return 3
        i = i + 1
    return 0
"""
    main = f"""\
    var b{n}: Box{n}
    b{n}.pre = {fill}
    b{n}.post = {fill}
    var k{n}: i32 = 0
    while k{n} < {n}
        b{n}.a[k{n}] = {fill}
        k{n} = k{n} + 1
    store_const{n}(@&b{n}.a)
    if intact{n}(@b{n}, {last}, {last}) != 0
        return {base + 1}
    if b{n}.a[{last}] != {first}
        return {base + 2}
    store_var{n}(@&b{n}.a, 0, {second})
    if intact{n}(@b{n}, 0, {last}) != 0
        return {base + 3}
    if b{n}.a[0] != {second}
        return {base + 4}
    if read_const{n}(@b{n}.a) != {first}
        return {base + 5}
    if read_var{n}(@b{n}.a, 0) != {second}
        return {base + 6}
"""
    return decls, main


def _grid(ty: str) -> str:
    fill, first, second = SCALARS[ty]
    parts = [_grid_size(ty, n, fill, first, second, 10 * (k + 1)) for k, n in enumerate(SIZES)]
    return ("".join(d for d, _ in parts) + "\npub fn main() -> i32\n"
            + "".join(m for _, m in parts) + "    return 0\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("ty", sorted(SCALARS))
def test_every_element_type_and_size(ritz1_bin, tmp_path, ty, compiler):
    assert _run(compiler, ritz1_bin, tmp_path, ty, _grid(ty)) == 0


# The ticket's store, in the IR: the array's own element, at its own width.
@pytest.mark.integration
def test_ritz1_stores_an_element_not_a_word(ritz1_bin, tmp_path):
    program = """\
fn f(a:& [2]i32)
    a[1] = 3

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    f(@&a)
    return a[1]
"""
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, "ir", program)
    assert comp.returncode == 0, comp.stdout + comp.stderr
    body = re.search(r"define [^\n]*@f\(.*?^}", ll.read_text(), re.M | re.S).group(0)
    assert "getelementptr [2 x i32]" in body
    assert "store i32" in body
    assert "store i64" not in body.replace("store i64 0", "")


TYPES = """\
struct P
    x: i32
    y: i64

struct Tiny
    b: i8

struct S
    v: [3]i32

struct Res
    n: i32

impl Drop for Res
    fn drop(self:& Res)
        return

struct Field
    a: [2]i32

struct Grid
    m: [2][3]i32

struct W
    n: i32

struct PF
    p: *[2]i32

var G: [2]i32

"""

MAIN_13 = """
pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f(@a)
"""

# Everything an element can do.  Each exits 3.
PROGRAMS = {
    "read": """
fn f(a:& [2]i32) -> i32
    return a[1]
""" + MAIN_13,
    "store": """
fn f(a:& [2]i32)
    a[1] = 3

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    f(@&a)
    return a[1]
""",
    # ritz0 takes `@a` where the callee writes; the store still reaches `a`.
    "store_through_shared_address": """
fn f(a:& [2]i32)
    a[1] = 3

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    f(@a)
    return a[1]
""",
    "non_constant_index": """
fn f(a:& [4]i32) -> i32
    var i: i32 = 0
    var t: i32 = 0
    while i < 4
        a[i] = a[i] + i
        t = t + a[i]
        i = i + 1
    return t - 7

pub fn main() -> i32
    var a: [4]i32 = [1, 1, 1, 1]
    return f(@&a)
""",
    "element_to_element": """
fn f(a:& [3]i32)
    a[0] = a[2]

pub fn main() -> i32
    var a: [3]i32 = [1, 2, 3]
    f(@&a)
    return a[0]
""",
    "compound": """
fn f(a:& [3]i8, i: i32)
    a[i] += 2
    a[i] *= 3
    a[i] -= 5

pub fn main() -> i32
    var a: [3]i8 = [9, 1, 9]
    f(@&a, 1)
    if a[0] != 9 or a[2] != 9
        return 0
    return (a[1] as i32) - 1
""",
    "compound_float": """
fn f(a:& [3]f64)
    a[1] += 1.5

pub fn main() -> i32
    var a: [3]f64 = [9.0, 1.5, 9.0]
    f(@&a)
    return a[1] as i32
""",
    "address_of_element": """
fn f(a:& [2]i32) -> i32
    let p: *i32 = @a[1]
    return *p
""" + MAIN_13,
    "write_through_address_of_element": """
fn f(a:& [2]i32)
    let p: *i32 = @a[1]
    *p = 3

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    f(@&a)
    return a[1]
""",
    "return_address_of_element": """
fn f(a:& [2]i32) -> *i32
    return @a[1]

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    let p: *i32 = f(@a)
    return *p
""",
    "element_as_argument": """
fn g(x: i32, y: f64) -> i32
    return x + (y as i32)

fn f(a:& [2]i32, b:& [2]f64) -> i32
    return g(a[1], b[1])

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    var b: [2]f64 = [0.0, 2.0]
    return f(@a, @b)
""",
    "borrow_of_element": """
fn g(n:& i32)
    n = 3

fn f(a:& [2]i32)
    g(@&a[1])

pub fn main() -> i32
    var a: [2]i32 = [1, 2]
    f(@&a)
    return a[1]
""",
    "borrow_of_struct_element": """
fn g(p:& P)
    p.x = 3

fn f(a:& [2]P)
    g(@&a[1])

pub fn main() -> i32
    var a: [2]P
    f(@&a)
    return a[1].x
""",
    "pointer_elements": """
fn f(a:& [2]*i32) -> i32
    return *a[1]

pub fn main() -> i32
    var x: i32 = 3
    var a: [2]*i32
    a[1] = @x
    return f(@a)
""",
    # Struct elements, strided by the struct.  Tiny is one byte.
    "field_read": """
fn f(a:& [3]P) -> i32
    return a[2].x

pub fn main() -> i32
    var a: [3]P
    a[1].x = 9
    a[2].x = 3
    return f(@a)
""",
    "field_store": """
fn f(a:& [3]P)
    a[1].x = 3

pub fn main() -> i32
    var a: [3]P
    a[0].y = 7
    a[1].y = 7
    a[2].x = 7
    f(@&a)
    if a[0].y != 7 or a[1].y != 7 or a[2].x != 7
        return 0
    return a[1].x
""",
    "field_store_tiny_stride": """
fn f(a:& [3]Tiny)
    a[1].b = 3

pub fn main() -> i32
    var a: [3]Tiny
    a[0].b = 7
    a[2].b = 7
    f(@&a)
    if a[0].b != 7 or a[2].b != 7
        return 0
    return a[1].b as i32
""",
    "compound_field": """
fn f(a:& [2]P)
    a[1].x += 2

pub fn main() -> i32
    var a: [2]P
    a[1].x = 1
    f(@&a)
    return a[1].x
""",
    "whole_element_store": """
fn f(a:& [3]P)
    a[1] = P { x: 3, y: 4 }

pub fn main() -> i32
    var a: [3]P
    a[0].y = 7
    a[2].x = 7
    f(@&a)
    if a[0].y != 7 or a[2].x != 7 or a[1].y != 4
        return 0
    return a[1].x
""",
    "array_field_of_element": """
fn f(a:& [2]S)
    a[1].v[2] = 3

pub fn main() -> i32
    var a: [2]S
    a[1].v[1] = 7
    f(@&a)
    if a[1].v[1] != 7
        return 0
    return a[1].v[2]
""",
    "method_on_element": """
impl P
    fn get(self:& P) -> i32
        return self.x

fn f(a:& [2]P) -> i32
    return a[1].get()

pub fn main() -> i32
    var a: [2]P
    a[1].x = 3
    return f(@a)
""",
    "print_element": """
import ritzlib.io

fn f(a:& [2]i32) -> i32
    print("{a[1]}\\n")
    return a[1]
""" + MAIN_13,
    "move_only_element_field": """
fn f(a:& [2]Res) -> i32
    return a[1].n

pub fn main() -> i32
    var a: [2]Res = [Res { n: 1 }, Res { n: 3 }]
    return f(@a)
""",
    "move_only_element_store": """
fn f(a:& [2]Res)
    a[1] = Res { n: 3 }

pub fn main() -> i32
    var a: [2]Res = [Res { n: 1 }, Res { n: 2 }]
    f(@&a)
    return a[1].n
""",
    # The whole array.
    "assign_whole": """
fn f(a:& [2]i32, b:& [2]i32)
    a = b

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    var b: [2]i32 = [4, 3]
    f(@&a, @b)
    return a[1]
""",
    "assign_literal": """
fn f(a:& [2]i32)
    a = [8, 3]

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    f(@&a)
    return a[1]
""",
    "sizeof": """
fn f(a:& [3]i8) -> i64
    return sizeof(a)

pub fn main() -> i32
    var a: [3]i8 = [1, 2, 3]
    return f(@a) as i32
""",
    "copy_is_a_copy": """
fn f(a:& [2]i32) -> i32
    var d = a
    d[1] = 9
    return a[1]
""" + MAIN_13,
    "deref_read": """
fn f(a:& [2]i32) -> i32
    let b: [2]i32 = *a
    return b[1]
""" + MAIN_13,
    "deref_argument": """
fn g(b: [2]i32) -> i32
    return b[1]

fn f(a:& [2]i32) -> i32
    return g(*a)
""" + MAIN_13,
    "for_bare": """
fn f(a:& [3]i32) -> i32
    var t: i32 = 0
    for x in a
        t = t + x
    return t - 3

pub fn main() -> i32
    var a: [3]i32 = [1, 2, 3]
    return f(@a)
""",
    # A bare `a` is the pointer, for every slot that takes a reference.
    "reference_let": """
fn f(a:& [2]i32) -> i32
    let p: @[2]i32 = @a
    return 3
""" + MAIN_13,
    "mut_reference_let": """
fn f(a:& [2]i32) -> i32
    let p: @&[2]i32 = @&a
    return 3
""" + MAIN_13,
    "pointer_let": """
fn f(a:& [2]i32) -> i32
    let p: *[2]i32 = @a
    return 3
""" + MAIN_13,
    "reference_return": """
fn f(a:& [2]i32) -> @[2]i32
    return @a
""" + """
pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    let p: @[2]i32 = f(@a)
    return 3
""",
    "pointer_field": """
fn f(a:& [2]i32) -> i32
    var w: PF
    w.p = @a
    return 3
""" + MAIN_13,
    "address_cast": """
fn f(a:& [2]i32) -> i32
    let p: *i32 = @a as *i32
    return p[1]
""" + MAIN_13,
    "shadowed": """
fn f(a:& [2]i32) -> i32
    var a: i32 = 3
    return a
""" + MAIN_13,
    # On to another param.  The callee writes, and the caller reads it back.
    "pass_on_store": """
fn g(a:& [2]i32)
    a[0] = 3

fn f(a:& [2]i32)
    g(a)

pub fn main() -> i32
    var a: [2]i32 = [1, 2]
    f(@&a)
    return a[0]
""",
    "pass_on_address": """
fn g(a:& [2]i32)
    a[0] = 3

fn f(a:& [2]i32)
    g(@a)

pub fn main() -> i32
    var a: [2]i32 = [1, 2]
    f(@&a)
    return a[0]
""",
    "pass_on_twice": """
fn h(a:& [3]i8)
    a[1] = 3

fn g(a:& [3]i8)
    h(a)

fn f(a:& [3]i8)
    g(a)

pub fn main() -> i32
    var a: [3]i8 = [7, 1, 7]
    f(@&a)
    if a[0] != 7 or a[2] != 7
        return 0
    return a[1] as i32
""",
    "pass_on_move_only": """
fn g(a:& [2]Res) -> i32
    return a[1].n

fn f(a:& [2]Res) -> i32
    return g(a)

pub fn main() -> i32
    var a: [2]Res = [Res { n: 1 }, Res { n: 3 }]
    return f(@a)
""",
    "pass_on_by_value": """
fn g(a: [2]i32) -> i32
    return a[1]

fn f(a:& [2]i32) -> i32
    return g(a)
""" + MAIN_13,
    "pass_on_reference": """
fn g(a: @[2]i32) -> i32
    return 3

fn f(a:& [2]i32) -> i32
    return g(@a)
""" + MAIN_13,
    # Every source of the array.
    "from_bare_local": """
fn f(a:& [2]i32)
    a[1] = 3

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    f(a)
    return a[1]
""",
    "from_global": """
fn f(a:& [2]i32) -> i32
    a[1] = 3
    return a[1]

pub fn main() -> i32
    return f(@&G)
""",
    "from_field": """
fn f(a:& [2]i32) -> i32
    return a[1]

pub fn main() -> i32
    var s: Field
    s.a[1] = 3
    return f(@s.a)
""",
    "from_row": """
fn f(a:& [3]i32) -> i32
    a[2] = 3
    return a[2]

pub fn main() -> i32
    var g: [2][3]i32
    return f(@&g[1])
""",
    "from_pointer_param": """
fn f(a:& [2]i32) -> i32
    return a[1]

fn g(p: *[2]i32) -> i32
    return f(p)
""" + """
pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return g(@a)
""",
    "from_deref_address": """
fn f(a:& [2]i32) -> i32
    return a[1]

fn g(p: *[2]i32) -> i32
    return f(@*p)

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return g(@a)
""",
    "from_call_result": """
fn h(p: *[2]i32) -> *[2]i32
    return p

fn f(a:& [2]i32) -> i32
    return a[1]

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f(h(@a))
""",
    # `[N]u32` is `[N]i32` to both compilers at an address (#2287); a by-value
    # store refuses it (#2343).  Whether this stays is #2367.
    "same_llvm_element": """
fn f(a:& [2]i32) -> i32
    a[1] = 3
    return a[1]

pub fn main() -> i32
    var a: [2]u32 = [1, 2]
    return f(@&a)
""",
    # Every way in.
    "method_param": """
impl W
    fn g(self:& W, b:& [3]i8)
        b[1] = 3

pub fn main() -> i32
    var w: W = W { n: 1 }
    var b: [3]i8 = [7, 1, 7]
    w.g(@&b)
    if b[0] != 7 or b[2] != 7
        return 0
    return b[1] as i32
""",
    "fn_value": """
fn f(a:& [2]i32) -> i32
    return a[1]

pub fn main() -> i32
    let h: fn(@[2]i32) -> i32 = f
    var b: [2]i32 = [1, 3]
    return h(@b)
""",
    "generic": """
fn f<T>(a:& [2]T) -> T
    return a[1]

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f<i32>(@a)
""",
    "generic_store_narrow": """
fn f<T>(a:& [3]T, v: T)
    a[1] = v

pub fn main() -> i32
    var a: [3]i8 = [7, 1, 7]
    f<i8>(@&a, 3)
    if a[0] != 7 or a[2] != 7
        return 0
    return a[1] as i32
""",
    "generic_struct_element": """
fn f<T>(a:& [2]T, v: T)
    a[1] = v

pub fn main() -> i32
    var a: [2]P
    var p: P
    p.x = 3
    f<P>(@&a, p)
    return a[1].x
""",
    "generic_method": """
struct Gn<T>
    n: T

impl<T> Gn<T>
    fn set(self:& Gn<T>, a:& [2]T, v: T)
        a[1] = v

pub fn main() -> i32
    var w: Gn<i32>
    var a: [2]i32 = [1, 1]
    w.set(@&a, 3)
    return a[1]
""",
    "const_length": """
const K: i32 = 3

fn f(a:& [K]i32) -> i32
    a[2] = 3
    return a[2]

pub fn main() -> i32
    var a: [K]i32 = [1, 2, 7]
    return f(@&a)
""",
    # Nested arrays.
    "nested_read": """
fn f(a:& [2][3]i32) -> i32
    return a[1][2]

pub fn main() -> i32
    var a: [2][3]i32
    a[1][2] = 3
    return f(@a)
""",
    "nested_store_neighbours": """
fn f(a:& [2][3]i8)
    a[0][2] = 3

pub fn main() -> i32
    var a: [2][3]i8
    a[0][1] = 7
    a[1][0] = 7
    f(@&a)
    if a[0][1] != 7 or a[1][0] != 7
        return 0
    return a[0][2] as i32
""",
    "nested_float": """
fn f(a:& [2][3]f64, i: i32, j: i32)
    a[i][j] = 3.0

pub fn main() -> i32
    var a: [2][3]f64
    a[1][0] = 7.0
    f(@&a, 0, 2)
    if a[1][0] != 7.0 or a[0][2] != 3.0
        return 0
    return 3
""",
    "nested_rank_3": """
fn f(a:& [2][2][2]i16)
    a[1][0][1] = 3

pub fn main() -> i32
    var a: [2][2][2]i16
    a[1][0][0] = 7
    a[1][1][0] = 7
    f(@&a)
    if a[1][0][0] != 7 or a[1][1][0] != 7
        return 0
    return a[1][0][1] as i32
""",
    "nested_struct_leaf": """
fn f(a:& [2][2]P) -> i32
    a[1][0].x = 3
    return a[1][0].x

pub fn main() -> i32
    var a: [2][2]P
    return f(@&a)
""",
    "nested_address_of_element": """
fn f(a:& [2][3]i32) -> i32
    let p: *i32 = @a[1][1]
    *p = 3
    return a[1][1]

pub fn main() -> i32
    var a: [2][3]i32
    return f(@&a)
""",
    "nested_flat_read": """
fn f(a:& [2][3]i32) -> i32
    let p: *i32 = @a as *i32
    return p[5]

pub fn main() -> i32
    var a: [2][3]i32
    a[1][2] = 3
    return f(@a)
""",
    "nested_pass_on": """
fn g(a:& [2][3]i32) -> i32
    return a[1][2]

fn f(a:& [2][3]i32) -> i32
    return g(a)

pub fn main() -> i32
    var a: [2][3]i32
    a[1][2] = 3
    return f(@a)
""",
    "nested_row_into_borrow": """
fn g(r:& [3]i32) -> i32
    return r[2]

fn f(a:& [2][3]i32) -> i32
    return g(@a[1])

pub fn main() -> i32
    var a: [2][3]i32
    a[1][2] = 3
    return f(@a)
""",
    "nested_from_field": """
fn f(a:& [2][3]i32) -> i32
    return a[1][2]

pub fn main() -> i32
    var s: Grid
    s.m[1][2] = 3
    return f(@s.m)
""",
    # Two instantiations share the parsed shape: the first can't keep it.
    "nested_generic_twice": """
fn f<T>(a:& [2][3]T, v: T)
    a[0][1] = v

pub fn main() -> i32
    var b: [2][3]i8
    var c: [2][3]i64
    b[0][2] = 7
    c[0][2] = 7
    f<i8>(@&b, 1)
    f<i64>(@&c, 2)
    if b[0][2] != 7 or c[0][2] != 7
        return 0
    return (b[0][1] as i32) + (c[0][1] as i32)
""",
    "nested_reference_let": """
fn f(a:& [2][3]i32) -> i32
    let p: @[2][3]i32 = @a
    return 3

pub fn main() -> i32
    var a: [2][3]i32
    return f(@a)
""",
    "nested_reference_param": """
fn g(a: @[2][3]i32) -> i32
    return 3

pub fn main() -> i32
    var a: [2][3]i32
    return g(@a)
""",
    "nested_generic": """
fn f<T>(a:& [2][3]T) -> T
    return a[1][2]

pub fn main() -> i32
    var a: [2][3]i32
    a[1][2] = 3
    return f<i32>(@a)
""",
    "nested_generic_store": """
fn f<T>(a:& [2][3]T, v: T)
    a[1][2] = v

pub fn main() -> i32
    var a: [2][3]i32
    f<i32>(@&a, 3)
    return a[1][2]
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_borrowed_array(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, TYPES + PROGRAMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_borrowed_array(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, TYPES + PROGRAMS[name]) == 3


# Dropping is the owner's: a borrowed array's elements aren't dropped at the end
# of the callee, and each compiler drops the same number overall.
DROPS = {
    "owner_drops_once": """
var D: i32 = 0

struct R
    n: i32

impl Drop for R
    fn drop(self:& R)
        D = D + 1

fn f(a:& [2]R)
    a[1].n = 3

pub fn main() -> i32
    if true
        var a: [2]R = [R { n: 1 }, R { n: 2 }]
        f(@&a)
    return D
""",
    "element_store": """
var D: i32 = 0

struct R
    n: i32

impl Drop for R
    fn drop(self:& R)
        D = D + 1

fn f(a:& [2]R)
    a[1] = R { n: 3 }

pub fn main() -> i32
    if true
        var a: [2]R = [R { n: 1 }, R { n: 2 }]
        f(@&a)
    return D
""",
    "pass_on": """
var D: i32 = 0

struct R
    n: i32

impl Drop for R
    fn drop(self:& R)
        D = D + 1

fn g(a:& [2]R)
    a[1].n = 3

fn f(a:& [2]R)
    g(a)

pub fn main() -> i32
    if true
        var a: [2]R = [R { n: 1 }, R { n: 2 }]
        f(@&a)
    return D
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(DROPS))
def test_drop_count_agrees(ritz1_bin, tmp_path, name):
    want = _run("ritz0", None, tmp_path / "..", f"{tmp_path.name}_r0", DROPS[name])
    assert _run("ritz1", ritz1_bin, tmp_path, name, DROPS[name]) == want


WRONG_TYPE = r"main\.ritz:\d+:\d+: argument \d+ of `\w+` has the wrong type"
NOT_THAT_ARRAY = WRONG_TYPE + r": the array isn't the one the parameter points at"
NOT_AN_ARRAY = WRONG_TYPE + r": the parameter points at an array"
DEREF_STORE = r"main\.ritz:\d+:\d+: cannot store through `\*a`"
NOT_A_VALUE = r"main\.ritz:\d+:\d+: a whole array is not a value here"
NO_SLICE = r"main\.ritz:\d+:\d+: an `a:& \[N\]T` param can't be sliced"
MOVE_OUT = r"main\.ritz:\d+:\d+: error: cannot move out of a reference"

# ritz0 refuses all of these, and so does ritz1, at the line.  A wrong-sized
# argument matters most: `a[i]` in the callee trusts the N and T it declares.
REFUSED = {
    "wrong_length_address": (NOT_THAT_ARRAY, """
fn f(a:& [5]i32)
    a[4] = 3

pub fn main() -> i32
    var a: [2]i32 = [0, 0]
    f(@&a)
    return a[1]
"""),
    "wrong_length_shared_address": (NOT_THAT_ARRAY, """
fn f(a:& [5]i32) -> i32
    return a[4]

pub fn main() -> i32
    var a: [2]i32 = [0, 0]
    return f(@a)
"""),
    "wrong_length_bare": (NOT_THAT_ARRAY, """
fn f(a:& [5]i32)
    a[4] = 3

pub fn main() -> i32
    var a: [2]i32 = [0, 0]
    f(a)
    return a[1]
"""),
    "wrong_element": (NOT_THAT_ARRAY, """
fn f(a:& [2]i64)
    a[1] = 3

pub fn main() -> i32
    var a: [2]i32 = [0, 0]
    f(@&a)
    return a[1]
"""),
    "wrong_struct_element": (NOT_THAT_ARRAY, """
fn f(a:& [2]P) -> i32
    return a[1].x

pub fn main() -> i32
    var a: [2]Tiny
    return f(@a)
"""),
    "wrong_length_global": (NOT_THAT_ARRAY, """
fn f(a:& [5]i32) -> i32
    return a[4]

pub fn main() -> i32
    return f(@&G)
"""),
    "wrong_length_field": (NOT_THAT_ARRAY, """
fn f(a:& [5]i32) -> i32
    return a[4]

pub fn main() -> i32
    var s: Field
    return f(@s.a)
"""),
    "wrong_length_row": (NOT_THAT_ARRAY, """
fn f(a:& [5]i32) -> i32
    return a[4]

pub fn main() -> i32
    var g: [2][3]i32
    return f(@&g[1])
"""),
    "wrong_length_pointer_param": (NOT_THAT_ARRAY, """
fn f(a:& [5]i32) -> i32
    return a[4]

fn g(p: *[2]i32) -> i32
    return f(p)

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return g(@a)
"""),
    "wrong_length_pass_on": (NOT_THAT_ARRAY, """
fn g(a:& [5]i32)
    a[4] = 3

fn f(a:& [2]i32)
    g(a)

pub fn main() -> i32
    var a: [2]i32 = [0, 0]
    f(@&a)
    return a[1]
"""),
    "wrong_length_pass_on_address": (NOT_THAT_ARRAY, """
fn g(a:& [5]i32)
    a[4] = 3

fn f(a:& [2]i32)
    g(@a)

pub fn main() -> i32
    var a: [2]i32 = [1, 2]
    f(@&a)
    return a[0]
"""),
    "wrong_length_reference_param": (NOT_THAT_ARRAY, """
fn f(a: @[5]i32) -> i32
    return 3

pub fn main() -> i32
    var a: [2]i32 = [1, 2]
    return f(@a)
"""),
    "wrong_length_mut_reference_param": (NOT_THAT_ARRAY, """
fn f(a: @&[5]i32) -> i32
    return 3

pub fn main() -> i32
    var a: [2]i32 = [1, 2]
    return f(@&a)
"""),
    "nested_wrong_shape": (NOT_THAT_ARRAY, """
fn f(a:& [2][4]i32)
    a[1][3] = 5

pub fn main() -> i32
    var a: [2][3]i32
    f(@&a)
    return 0
"""),
    "nested_same_bytes": (NOT_THAT_ARRAY, """
fn g(a:& [6]i32) -> i32
    return a[5]

pub fn main() -> i32
    var a: [2][3]i32
    return g(@a)
"""),
    "nested_into_flat": (NOT_THAT_ARRAY, """
fn f(a:& [2]i32) -> i32
    return a[1]

pub fn main() -> i32
    var a: [2][3]i32
    return f(@a)
"""),
    "flat_into_nested": (NOT_THAT_ARRAY, """
fn f(a:& [2][3]i32) -> i32
    return a[1][2]

pub fn main() -> i32
    var a: [2]i32 = [1, 2]
    return f(@a)
"""),
    "nested_field_wrong": (NOT_THAT_ARRAY, """
fn f(a:& [2][4]i32) -> i32
    return a[1][3]

pub fn main() -> i32
    var s: Grid
    return f(@s.m)
"""),
    "nested_deref_address_wrong": (NOT_THAT_ARRAY, """
fn g(b:& [5]i32) -> i32
    return b[4]

fn f(a:& [2][3]i32) -> i32
    return g(@*a)

pub fn main() -> i32
    var a: [2][3]i32
    return f(@a)
"""),
    "nested_wrong_leaf": (NOT_THAT_ARRAY, """
fn f(a:& [2][3]i64)
    a[1][2] = 5

pub fn main() -> i32
    var a: [2][3]i32
    f(@&a)
    return 0
"""),
    "nested_pass_on_wrong": (NOT_THAT_ARRAY, """
fn g(a:& [2][4]i32) -> i32
    return a[1][3]

fn f(a:& [2][3]i32) -> i32
    return g(a)

pub fn main() -> i32
    var a: [2][3]i32
    return f(@a)
"""),
    "nested_row_wrong": (NOT_THAT_ARRAY, """
fn g(r:& [4]i32) -> i32
    return r[3]

fn f(a:& [2][3]i32) -> i32
    return g(@a[1])

pub fn main() -> i32
    var a: [2][3]i32
    return f(@a)
"""),
    "nested_reference_param_wrong": (NOT_THAT_ARRAY, """
fn g(a: @[2][4]i32) -> i32
    return 3

pub fn main() -> i32
    var a: [2][3]i32
    return g(@a)
"""),
    "address_of_scalar": (NOT_AN_ARRAY, """
fn f(a:& [2]i32) -> i32
    return a[1]

pub fn main() -> i32
    var i: i32 = 0
    return f(@&i)
"""),
    "address_of_struct": (NOT_AN_ARRAY, """
fn f(a:& [2]i32) -> i32
    return a[1]

pub fn main() -> i32
    var p: P
    return f(@&p)
"""),
    "address_of_element": (NOT_AN_ARRAY, """
fn f(a:& [2]i32) -> i32
    return a[1]

pub fn main() -> i32
    var a: [2]i32
    return f(@&a[0])
"""),
    "address_of_scalar_field": (NOT_AN_ARRAY, """
fn f(a:& [2]i32) -> i32
    return a[1]

pub fn main() -> i32
    var p: P
    return f(@&p.y)
"""),
    "address_of_nested_element": (NOT_AN_ARRAY, """
fn f(a:& [2]i32) -> i32
    return a[1]

pub fn main() -> i32
    var g: [2][3]i32
    return f(@&g[1][2])
"""),
    "bare_scalar": (NOT_AN_ARRAY, """
fn f(a:& [2]i32) -> i32
    return a[1]

pub fn main() -> i32
    var i: i32 = 0
    return f(i)
"""),
    "borrowed_scalar": (NOT_AN_ARRAY, """
fn f(a:& [2]i32) -> i32
    return a[1]

fn g(n:& i32) -> i32
    return f(n)

pub fn main() -> i32
    var i: i32 = 0
    return g(@i)
"""),
    "borrowed_struct": (NOT_AN_ARRAY, """
fn f(a:& [2]i32) -> i32
    return a[1]

fn g(c:& P) -> i32
    return f(c)

pub fn main() -> i32
    var p: P
    return g(@p)
"""),
    # `*a` reads the array, and that's all it does.
    "store_through_deref_literal": (DEREF_STORE, """
fn f(a:& [2]i32)
    *a = [1, 3]

pub fn main() -> i32
    var a: [2]i32 = [0, 0]
    f(@&a)
    return a[1]
"""),
    "store_through_deref_scalar": (DEREF_STORE, """
fn f(a:& [2]i32)
    *a = 5

pub fn main() -> i32
    var a: [2]i32 = [0, 3]
    f(@&a)
    return a[1]
"""),
    "store_through_deref_array": (DEREF_STORE, """
fn f(a:& [2]i32, b:& [2]i32)
    *a = b

pub fn main() -> i32
    var a: [2]i32 = [0, 0]
    var b: [2]i32 = [1, 3]
    f(@&a, @b)
    return a[1]
"""),
    "store_through_deref_nested": (DEREF_STORE, """
fn f(a:& [2][3]i32)
    *a = 5

pub fn main() -> i32
    var a: [2][3]i32
    f(@&a)
    return 0
"""),
    "deref_as_scalar": (NOT_A_VALUE, """
fn f(a:& [2]i32) -> i32
    let x: i32 = *a
    return x

pub fn main() -> i32
    var a: [2]i32 = [3, 1]
    return f(@a)
"""),
    "deref_then_index": (NOT_A_VALUE, """
fn f(a:& [2]i32) -> i32
    return (*a)[1]

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f(@a)
"""),
    "nested_deref_as_scalar": (NOT_A_VALUE, """
fn f(a:& [2][3]i32) -> i32
    let x: i32 = *a
    return x

pub fn main() -> i32
    var a: [2][3]i32
    return f(@a)
"""),
    "slice": (NO_SLICE, """
fn f(a:& [3]i32) -> i32
    let t: *i32 = a[1..3]
    return t[1]

pub fn main() -> i32
    var a: [3]i32 = [1, 2, 3]
    return f(@a)
"""),
    "slice_untyped": (NO_SLICE, """
fn f(a:& [3]i32) -> i32
    let t = a[1..3]
    return 3

pub fn main() -> i32
    var a: [3]i32 = [1, 2, 3]
    return f(@a)
"""),
    "move_out_whole": (MOVE_OUT, """
fn f(a:& [2]Res) -> i32
    let b: [2]Res = a
    return 0

pub fn main() -> i32
    var a: [2]Res = [Res { n: 1 }, Res { n: 3 }]
    return f(@a)
"""),
    "move_out_deref": (MOVE_OUT, """
fn f(a:& [2]Res) -> i32
    let b: [2]Res = *a
    return 0

pub fn main() -> i32
    var a: [2]Res = [Res { n: 1 }, Res { n: 3 }]
    return f(@a)
"""),
    "move_out_by_value": (MOVE_OUT, """
fn g(b: [2]Res) -> i32
    return 3

fn f(a:& [2]Res) -> i32
    return g(a)

pub fn main() -> i32
    var a: [2]Res = [Res { n: 1 }, Res { n: 3 }]
    return f(@a)
"""),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz0_refuses(tmp_path, name):
    comp, _, _ = _compile("ritz0", None, tmp_path, name, TYPES + REFUSED[name][1])
    assert comp.returncode != 0, "ritz0 now takes this: it isn't a refusal to match"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz1_refuses_at_the_line(ritz1_bin, tmp_path, name):
    pattern, program = REFUSED[name]
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, name, TYPES + program)
    assert comp.returncode != 0
    assert not ll.exists()
    assert re.search(pattern, comp.stdout + comp.stderr), comp.stdout + comp.stderr


# ritz0 takes these and ritz1 refuses, because the alternative is a wrong-sized
# access in the callee.  AGAST #2324: ritz0 doesn't check these arguments.
RITZ1_STRICTER = {
    "method_argument": """
impl W
    fn g(self:& W, b:& [5]i32) -> i32
        return 3

pub fn main() -> i32
    var w: W = W { n: 1 }
    var b: [2]i32 = [1, 1]
    return w.g(@&b)
""",
    "fn_value_argument": """
fn f(a:& [5]i32) -> i32
    return 3

pub fn main() -> i32
    let h: fn(@[5]i32) -> i32 = f
    var b: [2]i32 = [1, 1]
    return h(@b)
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_STRICTER))
def test_ritz1_is_stricter_than_ritz0_here(ritz1_bin, tmp_path, name):
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, name, TYPES + RITZ1_STRICTER[name])
    assert comp.returncode != 0 and not ll.exists()
    assert re.search(NOT_THAT_ARRAY, comp.stdout + comp.stderr), comp.stdout + comp.stderr


# ritz0 gives 3 for these; ritz1 refuses them, located.  A nested array has no
# whole value in ritz1: that's #2098 and #2099, and these are what's left of it.
NESTED_LOCATED = {
    "nested_untyped_copy": ("an initializer on a multi-dimensional array", """
fn f(a:& [2][3]i32) -> i32
    var b = a
    return b[1][2] - 2

pub fn main() -> i32
    var a: [2][3]i32
    a[1][2] = 5
    return f(@a)
"""),
    "nested_whole_assign": ("assigning a whole multi-dimensional array", """
fn f(a:& [2][3]i32, b:& [2][3]i32)
    a = b

pub fn main() -> i32
    var a: [2][3]i32
    var b: [2][3]i32
    b[1][2] = 3
    f(@&a, @b)
    return a[1][2]
"""),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(NESTED_LOCATED))
def test_ritz0_takes_what_ritz1_refuses(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, TYPES + NESTED_LOCATED[name][1]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(NESTED_LOCATED))
def test_ritz1_nested_gap_is_located(ritz1_bin, tmp_path, name):
    message, program = NESTED_LOCATED[name]
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, name, TYPES + program)
    assert comp.returncode != 0 and not ll.exists()
    assert message in comp.stdout + comp.stderr, comp.stdout + comp.stderr


# ritz0 gives 3; ritz1 emits IR clang refuses.  A whole struct element has no
# by-value read on a plain array either, so the borrow inherits AGAST #1562, and
# no binary comes out of it.
STRUCT_ELEMENT_BY_VALUE = {
    "element_to_element": """
fn f(a:& [4]P)
    a[1] = a[3]

pub fn main() -> i32
    var a: [4]P
    a[3].x = 3
    f(@&a)
    return a[1].x
""",
    "as_argument": """
fn g(p: P) -> i32
    return p.x

fn f(a:& [2]P) -> i32
    return g(a[1])

pub fn main() -> i32
    var a: [2]P
    a[1].x = 3
    return f(@a)
""",
    "let": """
fn f(a:& [2]P) -> i32
    let p: P = a[1]
    return p.x

pub fn main() -> i32
    var a: [2]P
    a[1].x = 3
    return f(@a)
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(STRUCT_ELEMENT_BY_VALUE))
def test_ritz0_reads_a_struct_element_by_value(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, TYPES + STRUCT_ELEMENT_BY_VALUE[name]) == 3


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #1562: a whole struct element has no by-value read")
@pytest.mark.parametrize("name", sorted(STRUCT_ELEMENT_BY_VALUE))
def test_ritz1_reads_a_struct_element_by_value(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, TYPES + STRUCT_ELEMENT_BY_VALUE[name]) == 3


# The strict xfail can't tell a clang refusal from a wrong answer, and a wrong
# answer is what this ticket was.  So: no binary.
@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(STRUCT_ELEMENT_BY_VALUE))
def test_ritz1_struct_element_by_value_fails_closed(ritz1_bin, tmp_path, name):
    with pytest.raises(AssertionError, match="would not link"):
        _run("ritz1", ritz1_bin, tmp_path, name, TYPES + STRUCT_ELEMENT_BY_VALUE[name])


# AGAST #2321: not `:&`: the same index on a pointer param.  Every other form of
# it is in test_ritz1_array_pointer_index.py.
POINTER_INDEX = {
    "reference_param": """
fn f(a: @[2]i32) -> i32
    return a[1]
""" + MAIN_13,
    "pointer_param": """
fn f(p: *[2]i32) -> i32
    return p[1]
""" + MAIN_13,
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(POINTER_INDEX))
def test_indexes_through_a_pointer_param(ritz1_bin, tmp_path, name, compiler):
    assert _run(compiler, ritz1_bin, tmp_path, name, TYPES + POINTER_INDEX[name]) == 3


# AGAST #2322: ritz0 refuses these; the bare array reads as its address.
LAX = {
    "integer_slot": """
fn f(a:& [2]i32) -> i32
    var x: i64 = a
    return 3
""" + MAIN_13,
    "cast_to_pointer": """
fn f(a:& [2]i32) -> i32
    let p: *i32 = a as *i32
    return p[1]
""" + MAIN_13,
    "cast_to_integer": """
fn f(a:& [2]i32) -> i32
    let x: i64 = a as i64
    return 3
""" + MAIN_13,
    "compare_with_null": """
fn f(a:& [2]i32) -> i32
    if a == null
        return 0
    return 3
""" + MAIN_13,
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(LAX))
def test_ritz0_refuses_a_bare_array_as_an_address(tmp_path, name):
    comp, _, _ = _compile("ritz0", None, tmp_path, name, TYPES + LAX[name])
    assert comp.returncode != 0


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2322: a bare `:&` array reads as its pointer")
@pytest.mark.parametrize("name", sorted(LAX))
def test_ritz1_refuses_a_bare_array_as_an_address(ritz1_bin, tmp_path, name):
    comp, _, _ = _compile("ritz1", ritz1_bin, tmp_path, name, TYPES + LAX[name])
    assert comp.returncode != 0


# AGAST #2323: a pointer local records nothing the check can use.
UNCHECKED_POINTER = {
    "pointer_to_scalar": """
fn f(a:& [2]i32) -> i32
    return a[1]

fn g(p: *i32) -> i32
    return f(p)

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return g(@a[0])
""",
    "pointer_to_bytes": """
fn f(a:& [2]i32) -> i32
    return 3

fn g(p: *u8) -> i32
    return f(p)

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return g(@a as *u8)
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(UNCHECKED_POINTER))
def test_ritz0_refuses_a_pointer_that_is_no_array(tmp_path, name):
    comp, _, _ = _compile("ritz0", None, tmp_path, name, TYPES + UNCHECKED_POINTER[name])
    assert comp.returncode != 0


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2323: a pointer local doesn't record its array")
@pytest.mark.parametrize("name", sorted(UNCHECKED_POINTER))
def test_ritz1_refuses_a_pointer_that_is_no_array(ritz1_bin, tmp_path, name):
    comp, _, _ = _compile("ritz1", ritz1_bin, tmp_path, name, TYPES + UNCHECKED_POINTER[name])
    assert comp.returncode != 0


REFERENCE_FIELD = """
struct H
    r: @[2]i32

fn f(a:& [2]i32) -> i32
    var h: H
    h.r = @a
    return 3
""" + MAIN_13


@pytest.mark.integration
def test_ritz0_stores_a_borrowed_array_in_a_reference_field(tmp_path):
    assert _run("ritz0", None, tmp_path, "field", TYPES + REFERENCE_FIELD) == 3


@pytest.mark.integration
def test_ritz1_stores_a_borrowed_array_in_a_reference_field(ritz1_bin, tmp_path):
    assert _run("ritz1", ritz1_bin, tmp_path, "field", TYPES + REFERENCE_FIELD) == 3


# A by-value `[N]T` param owns its array, and stays a plain local: only `:&` is
# bound over the caller's memory.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_by_value_param_is_still_the_callee_s_copy(ritz1_bin, tmp_path, compiler):
    program = """\
fn f(a: [2]i32)
    var b: [2]i32 = a
    b[1] = 9

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    f(a)
    return a[1]
"""
    assert _run(compiler, ritz1_bin, tmp_path, "by_value", program) == 3
