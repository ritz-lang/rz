"""AGAST #3935: `usize` is `u64` and `isize` is `i64` as generic arguments too.

LARB R53 (LANGUAGE_SPEC §, "a Vec<usize> is a Vec<u64>"): the word types are
other names for the 64-bit integers, not new types.  ritz0 resolves the names
where its parser reads a type (parser.TYPE_NAME_SYNONYMS), so `V<usize>`
mangles to `V$u64`.  ritz1 resolved a bare `usize` to TYPE_U64 but kept a
generic argument's source spelling, so `V<usize>` was `V$usize`, a second
instantiation, and passing `@V<usize>` where `@V<u64>` is wanted was refused:
`argument 1 of `first` has the wrong type: V$u64* != V$usize*`.

Pinned on all three compilers: the ticket's repro, `isize`/`i64`, a nested
`V<V<usize>>`, a struct literal spelled either way, and the IR, which holds
one `V$u64` (and one `V$i64`), named as ritz0 names them.
"""

import re

import pytest

from test_ref_into_value import _compile, _run

pytestmark = pytest.mark.integration

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# The ticket's repro, run: a Vec<usize> passed where a Vec<u64> is wanted.
USIZE_AS_U64 = """\
struct V<T>
    d: *T

fn first(v: @V<u64>) -> u64
    *v.d

fn g(v: @V<usize>) -> u64
    first(v)

pub fn main() -> i32
    var x: u64 = 7
    let v = V<usize> { d: @x }
    g(@v) as i32
"""

# `isize` is `i64`, both ways round, and a literal spelled `V<i64>` binds a
# `V<isize>` local.
ISIZE_AS_I64 = """\
struct V<T>
    d: *T

fn get(v: @V<isize>) -> isize
    *v.d

fn h(v: @V<i64>) -> i64
    get(v)

pub fn main() -> i32
    var y: i64 = 9
    let v: V<isize> = V<i64> { d: @y }
    h(@v) as i32
"""

# A nested argument: `V<V<usize>>` is `V<V<u64>>`.
NESTED = """\
struct V<T>
    d: *T

fn inner(v: @V<V<u64>>) -> u64
    *(*v.d).d

fn outer(v: @V<V<usize>>) -> u64
    inner(v)

pub fn main() -> i32
    var x: u64 = 5
    var i = V<usize> { d: @x }
    let o = V<V<usize>> { d: @i }
    outer(@o) as i32
"""

# Both spellings in one program, for the IR: one instantiation per width.
BOTH_SPELLINGS = """\
struct V<T>
    d: *T

fn a(v: @V<usize>) -> u64
    *v.d

fn b(v: @V<u64>) -> u64
    *v.d

fn c(v: @V<isize>) -> i64
    *v.d

fn d(v: @V<i64>) -> i64
    *v.d

fn e(v: @V<V<usize>>) -> u64
    *(*v.d).d

fn f(v: @V<V<u64>>) -> u64
    *(*v.d).d

pub fn main() -> i32
    var x: u64 = 1
    var y: i64 = 2
    var vu = V<usize> { d: @x }
    let vi = V<isize> { d: @y }
    let vv = V<V<u64>> { d: @vu }
    (a(@vu) + b(@vu) + (c(@vi) + d(@vi)) as u64 + e(@vv) + f(@vv)) as i32
"""

# A generic call's single-token argument (`f<usize>`, `f<*usize>`) is the
# same instance as the integer spelling: `mk<usize>` returns the `V$u64` a
# `V<u64>` local is.
GENERIC_CALL = """\
struct V<T>
    d: *T

fn mk<T>(p: *T) -> V<T>
    V<T> { d: p }

fn load<T>(p: *T) -> T
    *p

fn peek<T>(r: @T) -> T
    *r

fn same<T>(p: T) -> T
    p

pub fn main() -> i32
    var x: u64 = 3
    var y: i64 = 4
    let v: V<u64> = mk<usize>(@x)
    let w: V<isize> = mk<i64>(@y)
    let a: u64 = load<usize>(v.d) + load<u64>(@x)
    let b: i64 = peek<isize>(@y) + peek<i64>(@y)
    let q: *u64 = same<*usize>(@x)
    (a as i64 + b + *w.d + *q as i64) as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name,src,want", [
    pytest.param("generic_call", GENERIC_CALL, 3 + 3 + 4 + 4 + 4 + 3, id="generic_call"),
    pytest.param("usize_as_u64", USIZE_AS_U64, 7, id="usize_as_u64"),
    pytest.param("isize_as_i64", ISIZE_AS_I64, 9, id="isize_as_i64"),
    pytest.param("nested", NESTED, 5, id="nested"),
    pytest.param("both_spellings", BOTH_SPELLINGS, 1 + 1 + 2 + 2 + 1 + 1, id="both_spellings"),
])
def test_word_type_argument_is_its_integer(compiler, tmp_path, name, src, want):
    assert _run(compiler, tmp_path, name, src) == want


def _instances(compiler, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    comp, ll, _ = _compile(compiler, tmp_path, "ir", BOTH_SPELLINGS)
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr
    # ritz0 names a type `%"struct.ritz_module_1.V$u64"`, ritz1 `%V$u64`.
    return re.findall(r'^%"?(?:struct\.ritz_module_\d+\.)?(V\$[^"\s]*)"? = type',
                      ll.read_text(), re.M)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_one_instantiation_per_width(compiler, tmp_path):
    """`V<usize>` and `V<u64>` are one `V$u64`; no `usize` is left to mangle."""
    names = _instances(compiler, tmp_path)
    assert sorted(names) == ["V$V_u64", "V$i64", "V$u64"], names


@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_mangled_names_match_ritz0(compiler, tmp_path):
    want = sorted(_instances("ritz0", tmp_path / "r0"))
    assert sorted(_instances(compiler, tmp_path / compiler)) == want
