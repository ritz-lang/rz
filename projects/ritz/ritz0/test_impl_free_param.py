"""A free parameter in `impl Box<T>` without `<T>` is "unknown type" (LARB R81).

A generic impl declares its parameters: `impl<T> Box<T>`.  In `impl Box<T>`
with no `<T>`, `T` is an ordinary type name; when no type `T` exists it names
nothing, located at the `T`:

    main.ritz:4:10: unknown type `T`: a generic impl declares it, `impl<T> Box<T>`

ritz0's half is #1390.  ritz1 and ritz1_selfhosted reported the same words
with no hint, at each method's `T` instead of the impl's, and compiled the
program cleanly when no method spelled `T` (AGAST #4002).

The parameter lists and the `impl<...> T<...>` hint come from the target's
declaration, so a non-generic `Foo` suggests `impl<> Foo<>` and
`Map<K, V>` suggests `impl<K, V> Map<K, V>`.  The control declares the
parameter and runs.
"""

import pytest

from test_ref_into_value import COMPILERS, _assert_refused, _compile, _run

pytestmark = pytest.mark.integration

MAIN = "\npub fn main() -> i32\n    3\n"


def free(name, write):
    return f"unknown type `{name}`: a generic impl declares it, `{write}`"


# name -> (program with `^` at the free argument, message).  A bare argument
# that names nothing is ordinary: `T` here is not the impl's parameter.
REFUSED = {
    # The ticket's impl: `b.get()` on a `Box<u32>` compiled and ran.
    "ticket": ("""\
struct Box<T>
    v: T

impl Box<^T>
    fn get(self: @Box<T>) -> T
        self.v
""", free("T", "impl<T> Box<T>")),
    # No method spells `T`: the impl's own argument is enough.
    "unused_by_methods": ("""\
struct Box<T>
    v: T

impl Box<^T>
    fn nope(x: i32) -> i32
        x
""", free("T", "impl<T> Box<T>")),
    # The impl declares one parameter; a second is still free.
    "second_param": ("""\
struct Box<T>
    v: T

impl<T> Box<^U>
    fn nope(x: i32) -> i32
        x
""", free("U", "impl<T> Box<T>")),
    # A target with no parameters: the declared list is empty.
    "nongeneric_target": ("""\
struct Foo
    a: i32

impl Foo<^T>
    fn nope(x: i32) -> i32
        x
""", free("T", "impl<> Foo<>")),
    # A misspelt concrete argument is the same free name.
    "unknown_concrete": ("""\
struct Box<T>
    v: T

impl Box<^Nope>
    fn nope(x: i32) -> i32
        x
""", free("Nope", "impl<T> Box<T>")),
    # Every declared parameter is named in the hint, not only the free one.
    "multiparam_target": ("""\
struct Map<K, V>
    k: K
    v: V

impl Map<^T>
    fn nope(x: i32) -> i32
        x
""", free("T", "impl<K, V> Map<K, V>")),
    # A trait impl's target arguments are the same rule.
    "trait_target": ("""\
trait Speak
    fn say(self: @Self) -> i32

struct P<K, V>
    k: K
    v: V

impl Speak for P<^T, i32>
    fn say(self: @P<T, i32>) -> i32
        self.v
""", free("T", "impl<K, V> P<K, V>")),
}

ROWS = [(c, row) for c in COMPILERS for row in sorted(REFUSED)]


@pytest.mark.parametrize("compiler,row", ROWS)
def test_a_free_impl_argument_is_refused(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    marked, message = REFUSED[row]
    _assert_refused(compiler, tmp_path, row, marked + MAIN, message)


# The one error lands at the impl's `T`, not at every method that spells it.
@pytest.mark.parametrize("compiler", COMPILERS)
def test_one_located_message(request, tmp_path, compiler):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    src = REFUSED["ticket"][0].replace("^", "") + MAIN
    comp, ll, _ = _compile(compiler, tmp_path, "one", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert not ll.exists()
    assert out.count("unknown type `T`") == 1, out
    assert "main.ritz:4:10: " in out, out


# R81's control: the same program, the impl declaring `T`, compiles and runs.
CONTROL = (REFUSED["ticket"][0].replace("^", "").replace(
    "impl Box<T>", "impl<T> Box<T>") + """
pub fn main() -> i32
    let b = Box<u32> { v: 3 }
    b.get() as i32
""")


@pytest.mark.parametrize("compiler", COMPILERS)
def test_declaring_the_parameter_compiles_and_runs(request, tmp_path, compiler):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    assert _run(compiler, tmp_path, "control", CONTROL) == 3
