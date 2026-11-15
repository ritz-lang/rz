"""An `impl` on a compiler built-in type is refused, at the `impl` (#3162).

Four types exist with no declaration at all: `Span<T>` (#3127), `StrView`
(a string literal's type), `Option<T>` and `Result<T, E>`.  An impl on one of
them, inherent or trait, at any instantiation, used to be quietly lost:

    impl Span<u8>                     # no `struct Span` in scope
        fn is_empty(self: @Span<u8>) -> bool
            ...                       # never called: the built-in runs

ritz0 ran the built-in method, ritz1 emitted `Span_is_empty` and called
`Span$u8_is_empty` (a link failure before #3125's intrinsic), and on
`Option` a method of the impl was "No method found" (ritz0) or undefined
at link (ritz1).  Aaron decided (2026-11-15, rz-larb) that built-ins are
closed, as R15 made built-in indexing: such an impl is a located error at
the `impl`, on ritz0, ritz1 and ritz1_selfhosted.

A type the program declares or imports under that name is an ordinary type
and unaffected.  The control rows live where they already ran:
test_method_receiver_once.py's span_own_methods (a module's own
`struct Span<T>` + `impl<T> Span<T>`) and span_param_ritzlib (ritzlib.span's),
and test_strview_ufcs_by_value.py (a module's own `struct StrView` + impl).
"""

import pytest

from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = pytest.mark.integration

MODULE = {"Span": "span", "StrView": "strview", "Option": "option", "Result": "result"}


def message(type_name):
    return (f"`{type_name}` is a built-in type and can't be extended here: "
            f"import ritzlib.{MODULE[type_name]} or declare your own type")


PRELUDE = """\
var MADE: i32 = 0

trait Speak
    fn say(self: @Self) -> i32

"""

# name -> (built-in type, program after PRELUDE).  `^` marks the `impl`.
ROWS = {
    # The ticket's program (#3125): a counting `is_empty` the call never reached.
    "span_inherent_u8": ("Span", """\
^impl Span<u8>
    fn is_empty(self: @Span<u8>) -> bool
        MADE = MADE + 1
        return false

fn c(s: Span<u8>) -> i32
    return s.is_empty() as i32

pub fn main() -> i32
    var a: [2]u8 = [1, 2]
    return c(@a) * 10 + MADE
"""),
    # Every instantiation, generic included.
    "span_inherent_generic": ("Span", """\
^impl<T> Span<T>
    fn first(self: @Span<T>) -> *T
        return self.ptr

pub fn main() -> i32
    return 0
"""),
    "span_trait": ("Span", """\
^impl Speak for Span<u8>
    fn say(self: @Span<u8>) -> i32
        return 1

pub fn main() -> i32
    return 0
"""),
    # A module's `len` on a string literal's type lost to the built-in.
    "strview_inherent": ("StrView", """\
^impl StrView
    fn len(self: @StrView) -> i64
        MADE = MADE + 1
        return 100

fn c(s: StrView) -> i64
    return s.len()

pub fn main() -> i32
    return c("abc") as i32 + MADE
"""),
    "option_inherent": ("Option", """\
^impl Option<i32>
    fn zz(self: @Option<i32>) -> i32
        return 7

pub fn main() -> i32
    let o: Option<i32> = Some(3)
    return o.zz()
"""),
    "result_trait": ("Result", """\
^impl Speak for Result<i32, i32>
    fn say(self: @Result<i32, i32>) -> i32
        return 1

pub fn main() -> i32
    return 0
"""),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(ROWS))
def test_impl_on_builtin_type_refused(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    type_name, program = ROWS[row]
    _assert_refused(compiler, tmp_path, row, PRELUDE + program, message(type_name))


# A module's own enum of a built-in's name is ordinary: its impl compiles.
# (Only compiles: whether a method of an impl on one instantiation is
# reachable is #3256's question, and is "No method found" today.)
DECLARED = {
    "own_option": """\
enum Option<T>
    Some(T)
    None

impl Option<i32>
    fn zz(self: @Option<i32>) -> i32
        return 7

pub fn main() -> i32
    let o: Option<i32> = Some(3)
    return 0
""",
    "own_result": """\
enum Result<T, E>
    Ok(T)
    Err(E)

impl Speak for Result<i32, i32>
    fn say(self: @Result<i32, i32>) -> i32
        return 7

pub fn main() -> i32
    let r: Result<i32, i32> = Ok(1)
    return 0
""",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(DECLARED))
def test_impl_on_declared_type_of_builtin_name_accepted(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    assert _run(compiler, tmp_path, row, PRELUDE + DECLARED[row]) == 0
