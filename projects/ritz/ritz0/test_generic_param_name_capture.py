"""AGAST #2966: a generic fn's type parameter is not the caller's type of the
same name.

`fn take<T>(p: @T) -> T` beside a `struct T` that implements `Drop`: ritz0
read the parameter `T` as that struct. Its move checker judged the generic
body with `T` move-only, so `*p` was "cannot move out of a reference" before
inference ran; its type checker judged `peek(@n)`, `n: i32`, as an `@i32` into
an `@T`-the-struct. ritz1 and ritz1_selfhosted keep the parameter opaque, as
section 4.4 and #2263 have it (a generic body is checked with `T` a copy
type; only an instance at a move-only `T` can move out of a reference), and
all three now agree. Rename the struct and nothing here changes.

The type checker reads a generic callee's signature at the call. Its slot
rules run there before monomorphisation only after an ownership error, so the
capture showed as a bogus ref-slot error in place of the real one; under
`--check-types` the call's `T` result was the struct too.
"""

import os

import pytest

import ritz0_inproc
from test_borrow_conflict_all_compilers import _refusal
from test_borrow_param_ref_field import RITZ_ROOT, _compile
from test_ritz1_for_iterable import SELFHOSTED_BIN

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

STRUCT_T = """\
struct T
    id: i32
impl Drop for T
    fn drop(self: @&T)
        self.id = 0
"""

# A generic struct's literal without args names no instance (#3064), so
# inference has no type for `t` and the call is the can't-infer error: the
# struct `T` doesn't bind the parameter `T`.
UNINFERRED = ("fn take<T>(p: @T) -> T\n    *p\n" + STRUCT_T
              + "struct Cell<T>\n    v: T\n"
              + "pub fn main() -> i32\n    let t = Cell { v: 1 }\n"
                "    let u = take(@t)\n    0\n")

# The ticket's program in one module.  `let t = T {...}` is a `T`-the-struct,
# as `let t: T` is (#3064), so the call binds the parameter to it.
TICKET = ("fn take<T>(p: @T) -> T\n    *p\n" + STRUCT_T
          + "pub fn main() -> i32\n    let t = T { id: 1 }\n"
            "    let u: T = take(@t)\n    0\n")

# The parameter `T` is a copy type in the generic body, and `@n` fits `@T`.
# The `i32` instance is the only one, and `*p` copies there.
OPAQUE = (STRUCT_T + "fn peek<T>(p: @T) -> T\n    *p\n"
          "pub fn main() -> i32\n    let n: i32 = 3\n    peek(@n) - 3\n")

# The same for a generic impl's `T`: `self.v` copies in the generic body.
IMPL_OPAQUE = (STRUCT_T + "struct Cell<T>\n    v: T\nimpl<T> Cell<T>\n"
               "    fn get(self: @Cell<T>) -> T\n        self.v\n"
               "pub fn main() -> i32\n    let c = Cell<i32> { v: 3 }\n    c.get() - 3\n")
ACCEPTED = {"fn": OPAQUE, "impl": IMPL_OPAQUE}

# An unrelated use after move is the error, not `@n` into `@T`-the-struct.
BESIDE_A_MOVE = OPAQUE.replace("    let n: i32 = 3\n",
                               "    let a = T { id: 1 }\n    let b = a\n    let c = a\n"
                               "    let n: i32 = 3\n")

# Bound to the move-only struct, the instance moves out of a reference,
# whether `t` is annotated or typed by its literal.
INSTANCES = {"annotated": TICKET.replace("let t = T {", "let t: T = T {"),
             "literal": TICKET}


@pytest.fixture
def compile_with(ritz1_bin, tmp_path):
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _compile("ritz0", None, tmp_path, name, program)
        return _compile("ritz1", bins[compiler], tmp_path, name, program)
    return go


@pytest.mark.parametrize("compiler", COMPILERS)
def test_struct_named_like_the_param_does_not_bind_it(compile_with, compiler):
    comp, ll, _ = compile_with(compiler, "uninferred", UNINFERRED)
    assert _refusal(comp, ll, UNINFERRED) == (
        "12:13", "can't infer `T` for `take`: write `take<T>(...)`")


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_generic_body_and_call_see_the_param_not_the_struct(compile_with, compiler, name):
    comp, ll, _ = compile_with(compiler, name, ACCEPTED[name])
    assert comp.returncode == 0, comp.stdout + comp.stderr
    assert ll.exists()


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(INSTANCES))
def test_instance_at_the_move_only_struct_still_refused(compile_with, compiler, name):
    comp, ll, _ = compile_with(compiler, name, INSTANCES[name])
    assert _refusal(comp, ll, INSTANCES[name]) == ("2:5", "cannot move out of a reference")


@pytest.mark.parametrize("compiler", COMPILERS)
def test_ref_slot_check_sees_the_param_not_the_struct(compile_with, compiler):
    comp, ll, _ = compile_with(compiler, "beside", BESIDE_A_MOVE)
    where, message = _refusal(comp, ll, BESIDE_A_MOVE)
    assert (where, message.split(" (moved at ")[0]) == ("11:13", "use of moved value: `a`")
    assert message.endswith("main.ritz:10:13)"), message


def test_check_types_call_result_is_not_the_struct(tmp_path):
    """ritz0 only: `--check-types` has no ritz1 counterpart."""
    src = tmp_path / "main.ritz"
    src.write_text(OPAQUE.replace("    peek(@n) - 3\n", "    let x: i32 = peek(@n)\n    x - 3\n"))
    comp = ritz0_inproc.run_ritz0([str(src), "--check-types", "-o", str(tmp_path / "main.ll")],
                                  cwd=tmp_path, env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
                                  timeout=300)
    assert comp.returncode == 0, comp.stdout + comp.stderr
