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

A type the module declares (before or after the impl) or imports is known,
and its impl is unaffected: the controls below, and
every ritzlib/corpus impl, which all target a type their own file declares
(measured 2026-11-15: 0 sites refused).

A type alias is known but can't be an impl target (LARB R35, #3368): `type
Id = Foo` then `impl Id` is "`Id` is a type alias for `Foo`: write `impl
Foo`", at `Id`.

A primitive is known but closed to an inherent impl (LARB R36, #3370):
`impl u8` is "`u8` is a built-in type; it can't have an `impl`", at the
type.  R36's revisit (#4294) admits a *trait* impl on one in the file that
declares the trait (test_impl_on_builtin_trait_file.py); anywhere else it is
"`i64` is a built-in type: a trait impl for it must be in the trait's file
(§12.2)".

An undeclared trait is "unknown trait `Nonesuch`", at the impl's trait name
(#4197 on ritz0, #4211 on ritz1).  Known: a declared or imported trait, and
a compiler trait (Drop, Deref, DerefMut, Index, IndexMut, IndexSet).
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
    # Declared after its impl: the check sees the whole module.  `Drop` is
    # a compiler trait: known with no declaration (#4211).
    "struct_after_impl": """\
impl Foo
    fn zz(self: @Foo) -> i32
        return self.x

impl Drop for Foo
    fn drop(self: @&Foo)
        return

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


# An impl on a type alias (LARB R35, #3368), inherent or trait: located at
# the alias name, both spelled "write `impl Foo`", on every compiler: ritz1
# refuses it before lowering the impl body (#3369), which failed later with
# an unlocated "cannot emit: unhandled EXPR_MEMBER".
ALIAS_ROWS = {
    "inherent": """\
struct Foo
    x: i32

type Id = Foo

impl ^Id
    fn zz(self: @Foo) -> i32
        return 7

pub fn main() -> i32
    return 0
""",
    "trait": """\
struct Foo
    x: i32

type Id = Foo

impl Speak for ^Id
    fn say(self: @Foo) -> i32
        return 7

pub fn main() -> i32
    return 0
""",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(ALIAS_ROWS))
def test_impl_on_alias_refused(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    _assert_refused(compiler, tmp_path, f"alias_{row}", PRELUDE + ALIAS_ROWS[row],
                    "`Id` is a type alias for `Foo`: write `impl Foo`")


# A target that is no plain name is spelled as written, as ritz0's
# type_to_string prints it (#3625): ritz1's alias table keeps a pointer,
# array or generic instance only in replay form (pointee kind, mangled
# `Box$u8`), and said "`Id` is a type alias: write `impl` on the type it
# names".  name -> (target, alias line).
ALIAS_SPELLED_ROWS = {
    "pointer": ("*Foo", "type Id = *Foo"),
    "array": ("[4]u8", "type Id = [4]u8"),
    "generic": ("Box<u8>", "type Id = Box<u8>"),
    # Spaced as type_to_string spaces it: after `,`, around `->`, between
    # two words, nowhere else.
    "fn_type": ("fn(*mut Foo, u8) -> i32", "type Id = fn( *mut Foo,u8 )->i32"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(ALIAS_SPELLED_ROWS))
def test_impl_on_alias_spells_target(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    target, alias = ALIAS_SPELLED_ROWS[row]
    program = f"""\
struct Foo
    x: i32

struct Box<T>
    v: T

{alias}

impl ^Id
    fn zz(self: @Id) -> i32
        return 7

pub fn main() -> i32
    return 0
"""
    _assert_refused(compiler, tmp_path, f"alias_spelled_{row}", PRELUDE + program,
                    f"`Id` is a type alias for `{target}`: write `impl {target}`")


# Known, and only compiled: a blanket impl's methods' reachability is
# R15/R17's.
COMPILES = {
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


# An inherent impl on a primitive is a built-in type, closed to `impl` (LARB
# R36, #3288), located at the type, on every compiler.  ritz1 failed with an
# unlocated "Parse error at pos 64": its grammar took only an IDENT as the
# target, and `i32` is a keyword (#3371).
#
# A *trait* impl on a primitive is R36's revisit (#4294): legal in the file
# declaring the trait, so here only one outside it is refused — `Drop` is a
# compiler trait, which no file declares (the multi-file case is
# test_impl_on_builtin_trait_file.py).
PRIMITIVE_ROWS = {
    "inherent": ("u8", """\
impl ^u8
    fn zz(self: @u8) -> i32
        return 7

pub fn main() -> i32
    return 0
""", "`u8` is a built-in type; it can't have an `impl`"),
    "trait_outside_file": ("i64", """\
impl Drop for ^i64
    fn drop(self: @&i64)
        return

pub fn main() -> i32
    return 0
""", "`i64` is a built-in type: a trait impl for it must be in the "
     "trait's file (§12.2)"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(PRIMITIVE_ROWS))
def test_impl_on_primitive_refused(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    _, program, message = PRIMITIVE_ROWS[row]
    _assert_refused(compiler, tmp_path, f"primitive_{row}", PRELUDE + program,
                    message)


# An impl of a trait nothing declares (#4211): it compiled silently on ritz1.
# `Speak` (declared) and `Drop` (a compiler trait) are known, and only the
# undeclared one is refused.  ritz0's refusal is #4197's (its row in
# test_trait_bound_check.py runs on all three compilers since #3469).
UNKNOWN_TRAIT = """\
struct Foo
    x: i32

impl Speak for Foo
    fn say(self: @Foo) -> i32
        return 1

impl Drop for Foo
    fn drop(self: @&Foo)
        return

impl ^Nonesuch for Foo
    fn g(self: @Foo) -> i32
        return 0

pub fn main() -> i32
    return 0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_impl_of_unknown_trait_refused(request, tmp_path, compiler):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    _assert_refused(compiler, tmp_path, "unknown_trait", PRELUDE + UNKNOWN_TRAIT,
                    "unknown trait `Nonesuch`")
