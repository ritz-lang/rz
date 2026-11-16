"""Method syntax reaches only impl methods (AGAST #3244, LANGUAGE_SPEC §9).

THE DEFECT

`a.cmp(b)` on a user `struct Foo` with only a free `fn foo_cmp(a: Foo, b: Foo)`
passed ritz0's type checker, which also tried `<lowercased type>_<method>`, and
then died in the emitter, which doesn't: `ValueError: No method 'cmp' found for
type 'Foo'`, a Python traceback with no location. ritz1 and ritz1_selfhosted
called an undeclared `@Foo_cmp(...)` and failed at link time.

THE RULE (Aaron, 2026-11-15)

`x.m(...)` on a user type resolves only to a method declared in an `impl` for
that type, or a trait impl. A free fn that happens to be called `foo_cmp` is not
a method. Otherwise all three compilers refuse it at the method name. The
ritzlib types in the UFCS table (ritz0/ufcs.py, ritz1's
ufcs_non_generic_prefix) still dispatch to their free fns, until #3252.
"""

import pytest

from ref_rules import no_method
from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = pytest.mark.integration

FOO = """\
struct Foo
    x: i32
"""

ENUM = """\
enum Color
    Red
    Blue
"""

MAIN = """
pub fn main() -> i32
    let a = Foo { x: 1 }
    let b = Foo { x: 2 }
    a.^cmp(b)
"""

# name -> (program with `^` at the method name, message)
REFUSED = {
    # The ticket's program: a free `foo_cmp` is named in the hint.
    "free_foo_cmp": (
        FOO
        + """
fn foo_cmp(a: Foo, b: Foo) -> i32
    a.x - b.x
"""
        + MAIN,
        no_method("cmp", "Foo", "foo_cmp(a, b)"),
    ),
    # Nor is a free fn of the method's own name a method (ritz0's checker
    # tried that too).
    "free_cmp": (
        FOO
        + """
fn cmp(a: Foo, b: Foo) -> i32
    a.x - b.x
"""
        + MAIN,
        no_method("cmp", "Foo"),
    ),
    # An enum is a user type too: ritz1 called an undeclared `@Color_nope`
    # and failed at link time with no location (AGAST #1572).
    "enum_no_impl": (
        ENUM
        + """
pub fn main() -> i32
    let c = Color.Red
    c.^nope()
""",
        no_method("nope", "Color"),
    ),
}

# AGAST #1572: refused by ritz1 and ritz1_selfhosted, which called an
# undeclared `@<Type>_nope` and failed at link time. A generic instance's
# methods are monomorphized in each module that calls them (`linkonce_odr`),
# so one find_spec_impl_method misses is defined nowhere. ritz0 refuses these
# with an unlocated ValueError: AGAST #3649.
RITZ1_COMPILERS = ["ritz1", "ritz1_selfhosted"]
RITZ1_REFUSED = {
    "generic_instance": (
        """\
struct W<T>
    x: T

impl<T> W<T>
    fn get(self: @W<T>) -> T
        self.x

pub fn main() -> i32
    let w = W<i32> { x: 1 }
    w.^nope()
""",
        no_method("nope", "W$i32"),
    ),
    # A UFCS-table generic (`vec_<m>$T`) with no `vec_nope`.
    "ufcs_table_generic": (
        """\
import ritzlib.gvec

pub fn main() -> i32
    var v: Vec<i32> = vec_new<i32>()
    v.^nope()
""",
        no_method("nope", "Vec$i32"),
    ),
}

# name -> (program, exit status): what still dispatches.
DISPATCHED = {
    "impl_method": (
        FOO
        + """
impl Foo
    fn cmp(self: @Foo, b: Foo) -> i32
        self.x - b.x
"""
        + MAIN.replace("^", "").replace("a.cmp(b)", "a.cmp(b) + 10"),
        9,
    ),
    "trait_impl_method": (
        """\
trait Cmp
    fn cmp(self: @Self, b: Foo) -> i32

"""
        + FOO
        + """
impl Cmp for Foo
    fn cmp(self: @Foo, b: Foo) -> i32
        self.x - b.x
"""
        + MAIN.replace("^", "").replace("a.cmp(b)", "a.cmp(b) + 10"),
        9,
    ),
    # AGAST #1572: an enum's impl method, and a generic impl's at an instance.
    "enum_impl_method": (
        ENUM
        + """
impl Color
    fn code(self: @Color) -> i32
        match *self
            Red => 3
            Blue => 4

pub fn main() -> i32
    let c = Color.Blue
    c.code()
""",
        4,
    ),
    "generic_impl_method": (
        """\
struct W<T>
    x: T

impl<T> W<T>
    fn get(self: @W<T>) -> T
        self.x

pub fn main() -> i32
    let w = W<i32> { x: 6 }
    w.get()
""",
        6,
    ),
    # §7.7 rule 2: `w.get()` is the `Deref` target's method, not a missing one.
    "deref_target_method": (
        """\
struct Inner
    x: i32

impl Inner
    fn get(self: @Inner) -> i32
        self.x

struct Wrap
    inner: Inner

impl Deref for Wrap
    fn deref(self: @Wrap) -> @Inner
        @self.inner

pub fn main() -> i32
    let w = Wrap { inner: Inner { x: 7 } }
    w.get()
""",
        7,
    ),
    # A type in the UFCS table: `s.len()` on a `String` is `string_len(@s)`.
    # The table goes by the type's name, so ritzlib's String is declared here
    # in its shape, and the program links without ritzlib's objects.
    "table_string_len": (
        """\
struct String
    data: *u8
    len: i64
    cap: i64

fn string_len(s: @String) -> i64
    s.len

pub fn main() -> i32
    let s = String { data: null, len: 5, cap: 0 }
    s.len() as i32
""",
        5,
    ),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_method_syntax_needs_an_impl_method(tmp_path, compiler, name):
    program, message = REFUSED[name]
    _assert_refused(compiler, tmp_path, name, program, message)


@pytest.mark.parametrize("compiler", RITZ1_COMPILERS)
@pytest.mark.parametrize("name", sorted(RITZ1_REFUSED))
def test_ritz1_refuses_a_method_no_module_defines(tmp_path, compiler, name):
    program, message = RITZ1_REFUSED[name]
    _assert_refused(compiler, tmp_path, name, program, message)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(DISPATCHED))
def test_impl_and_table_methods_still_dispatch(tmp_path, compiler, name):
    program, want = DISPATCHED[name]
    assert _run(compiler, tmp_path, name, program) == want
