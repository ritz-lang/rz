"""An `impl` on a type nothing declares is "unknown type", at its name (#3264).

With no `struct Foo` / `enum Foo` declared or imported, this compiled with
rc 0 on ritz0 and ritz1, and `zz` could never be called:

    impl Foo
        fn zz(self: @Foo) -> i32
            return 7

`Vec<u8>` and `String` without `import ritzlib.vec` / `ritzlib.string` are
the same case: unlike #3162's four built-ins (test_impl_builtin_refused.py),
those types don't exist without a declaration.  The impl is now a located
"unknown type `Foo`" at the impl's type name (after `for` in a trait impl)
on ritz0, ritz1 and ritz1_selfhosted.

A type the module declares (before or after the impl) or imports, a
primitive, or a type alias is known, and its impl is unaffected: the
controls below, and every ritzlib/corpus impl, which all target a type their
own file declares (measured 2026-11-15: 0 sites refused).
"""

import pytest

from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = pytest.mark.integration


def message(type_name):
    return f"unknown type `{type_name}`"


PRELUDE = """\
trait Speak
    fn say(self: @Self) -> i32

"""

# name -> (target, program after PRELUDE).  `^` marks the impl's type name.
ROWS = {
    # The ticket's program.
    "inherent": ("Foo", """\
impl ^Foo
    fn zz(self: @Foo) -> i32
        return 7

pub fn main() -> i32
    return 0
"""),
    # Not built-ins: they exist only once ritzlib declares them.
    "vec_unimported": ("Vec", """\
impl ^Vec<u8>
    fn zz(self: @Vec<u8>) -> i32
        return 7

pub fn main() -> i32
    return 0
"""),
    "string_unimported": ("String", """\
impl ^String
    fn zz(self: @String) -> i32
        return 7

pub fn main() -> i32
    return 0
"""),
    "trait": ("Foo", """\
impl Speak for ^Foo
    fn say(self: @Foo) -> i32
        return 1

pub fn main() -> i32
    return 0
"""),    # `Self` names no type outside an impl.
    "self": ("Self", """\
impl ^Self
    fn zz(self: @Self) -> i32
        return 7

pub fn main() -> i32
    return 0
"""),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(ROWS))
def test_impl_on_unknown_type_refused(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    type_name, program = ROWS[row]
    _assert_refused(compiler, tmp_path, row, PRELUDE + program, message(type_name))


# Known targets: the impl compiles and its method runs.
KNOWN = {
    # Declared after its impl: the check sees the whole module.
    "struct_after_impl": """\
impl Foo
    fn zz(self: @Foo) -> i32
        return self.x

struct Foo
    x: i32

pub fn main() -> i32
    let f = Foo { x: 7 }
    return f.zz()
""",
    "enum": """\
enum E
    A
    B

impl Speak for E
    fn say(self: @E) -> i32
        return 7

pub fn main() -> i32
    let e = E.A
    return e.say()
""",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(KNOWN))
def test_impl_on_known_type_accepted(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    assert _run(compiler, tmp_path, row, PRELUDE + KNOWN[row]) == 7


# Known, and only compiled: whether an alias's impl methods are reachable is
# #3287 (unreachable on all three today; ritz1 can't lower `self.x` in its
# body), and a blanket impl's is R15/R17's.
COMPILES = {
    "alias": """\
struct Foo
    x: i32

type Id = Foo

impl Id
    fn zz(self: @Foo) -> i32
        return 7

pub fn main() -> i32
    return 7
""",
    "simd": """\
impl Speak for v4i32
    fn say(self: @v4i32) -> i32
        return 7

pub fn main() -> i32
    return 7
""",
    # The impl's own type parameter.
    "type_param": """\
impl<T> Speak for T
    fn say(self: @T) -> i32
        return 7

pub fn main() -> i32
    return 7
""",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(COMPILES))
def test_impl_on_known_type_compiles(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    assert _run(compiler, tmp_path, row, PRELUDE + COMPILES[row]) == 7


# A primitive.  ritz0 only: ritz1 can't parse `impl Speak for i32` (#3288).
def test_impl_on_primitive_accepted(tmp_path):
    assert _run("ritz0", tmp_path, "primitive", PRELUDE + """\
impl Speak for i32
    fn say(self: @i32) -> i32
        return *self

pub fn main() -> i32
    let x: i32 = 7
    return x.say()
""") == 7
