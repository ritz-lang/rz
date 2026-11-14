"""AGAST #2351: a bare `None` as the tail of an impl method emits invalid IR.

    impl T
        fn o(self) -> Option<i32>
            None

emit_impl_method's struct-return tail treated every EXPR_IDENT that is not a
struct-valued local as a local holding a pointer-as-int: it `inttoptr`'d the
value and loaded the struct back through it.  `None` is an identifier but not
a local; emit_expr has already built the `%Option$i32` aggregate, so clang
rejected `inttoptr i64 %<aggregate>` with no source location.  `Some(1)` is a
call, so it never took that path; emit_fn only takes the pointer path for a
real local and was fine.

Cases: an instance method (by-value and `@` self), a static method, an
Option of a large struct (the sret return path), and `Some` and free-fn
controls.  Each program returns 3 on success.  ritz0 is the oracle.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

# `self` by value, the ticket's repro.
INSTANCE = """\
import ritzlib.option

struct T
    v: i64

impl T
    fn o(self) -> Option<i32>
        None

pub fn main() -> i32
    let t: T = T { v: 1 }
    match t.o()
        Some(x) => return 1
        None => return 3
    return 2
"""

# `self` borrowed.
BORROWED_SELF = """\
import ritzlib.option

struct T
    v: i64

impl T
    fn o(self: @T) -> Option<i64>
        None

pub fn main() -> i32
    let t: T = T { v: 1 }
    match t.o()
        Some(x) => return 1
        None => return 3
    return 2
"""

STATIC = """\
import ritzlib.option

struct T
    v: i64

impl T
    fn none() -> Option<i32>
        None

pub fn main() -> i32
    match T.none()
        Some(x) => return 1
        None => return 3
    return 2
"""

# A payload too large to return in registers: the sret path.
SRET = """\
import ritzlib.option

struct Big
    a: i64
    b: i64
    c: i64
    d: i64

struct T
    v: i64

impl T
    fn o(self) -> Option<Big>
        None

pub fn main() -> i32
    let t: T = T { v: 1 }
    match t.o()
        Some(x) => return 1
        None => return 3
    return 2
"""

# Controls: `Some` as the method tail, and a free fn's bare `None` tail.
SOME_CONTROL = """\
import ritzlib.option

struct T
    v: i64

impl T
    fn o(self) -> Option<i32>
        Some(3)

pub fn main() -> i32
    let t: T = T { v: 1 }
    match t.o()
        Some(x) => return x
        None => return 1
    return 2
"""

FREE_FN_CONTROL = """\
import ritzlib.option

fn o() -> Option<i32>
    None

pub fn main() -> i32
    match o()
        Some(x) => return 1
        None => return 3
    return 2
"""

CASES = {
    "instance": INSTANCE,
    "borrowed_self": BORROWED_SELF,
    "static": STATIC,
    "sret": SRET,
    "some_control": SOME_CONTROL,
    "free_fn_control": FREE_FN_CONTROL,
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, CASES[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_method_none_tail(ritz1_bin, tmp_path, name):
    """AGAST #2351. Before the fix: `inttoptr i64 %<Option aggregate>` -> clang error."""
    assert _run("ritz1", tmp_path, name, CASES[name]) == 3
