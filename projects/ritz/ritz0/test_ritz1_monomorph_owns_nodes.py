"""ritz1's monomorph pass lowers Exprs in place, and only ones it owns.

THE AUDIT (AGAST #4411, part of #1816's AST-write-back audit)

#4408 removed the emitter's writes back into an existing Expr.  Its audit
assumed monomorph.ritz "builds NEW nodes"; it does not.  Six lowering helpers
rewrite the node they are handed:

  rewrite_enum_from_call  `E.from(x)`        -> the plain call `E__from(x)`
  si_into_deref           an index call      -> `*<call>`
  rewrite_struct_index    `m[k]`             -> `Index` / `IndexMut` method call
  rewrite_value_slice     `v[lo..hi]`        -> `v.slice(lo, hi)`
  span_view_in_place      that slice         -> the `Span$T { ptr, len }` view
  slice_into_span_slot    the same, in a slot

THE DECISION: IN PLACE IS CORRECT HERE

The pass owns every node it rewrites.  A module's bodies are parsed fresh for
this compile and collect_instantiations_from_module walks each one once; a
generic body is cloned per instantiation (clone_expr) and only the clone is
touched.  Neither tree is shared with another module or another instance, and
the emitter receives the lowered tree afterwards.  So there is nothing to
write back into and no second owner to surprise.  That is different from the
emitter's write-back #4408 removed, which mutated nodes the pass did not own.

The invariant that matters is therefore narrower: a helper must never rewrite
a node that is not the construct it names.  `rewrite_enum_from_call` carries
it explicitly -- it returns when the receiver name is a local or param, since
then `E.from` is a method call on that binding, not the enum's conversion.
The tests below pin that boundary (they fail if the shadow guard goes, and
the compiler then links invalid IR: an Option value returned as i32) and pin
that the legitimate rewrites still happen, in the walked body and in each
cloned generic body.

ritz0's twin pass lacked the shadow guard until AGAST #4414 gave it lexical
scopes; every row runs on all three compilers so the boundary cannot drift
again.
"""

import pytest

from test_enum_discriminants import _run

pytestmark = pytest.mark.integration

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# A struct whose `from` method is what `E.from(...)` means once `E` is a
# local or a param.  Returns 42 when the call reaches it.
SHADOWED = """\
import ritzlib.option

enum Colour: u8
    Red = 1
    Blue = 2

struct Paint
    n: i32

impl Paint
    fn from(self: @Paint, k: i32) -> i32
        self.n + k

fn use(Colour: Paint) -> i32
    Colour.from(2)

fn main() -> i32
    let Colour = Paint { n: 40 }
    if use(Paint { n: 40 }) != 42
        return 1
    Colour.from(2)
"""

# The rewrite itself, so a "fix" that simply stops lowering `E.from` fails.
FROM = """\
import ritzlib.option

enum Colour: u8
    Red = 1
    Blue = 2

fn main() -> i32
    match Colour.from(2)
        Some(c) => match c
            Blue => 42
            _ => 1
        None => 2
"""

# The shadow guard is per fn and per scope: a same-named local elsewhere must
# not suppress a real conversion.  Both compilers walk each body with its own
# bindings, so the enum's `from` still lowers in `main`.
SHADOW_ELSEWHERE = """\
import ritzlib.option

enum Colour: u8
    Red = 1
    Blue = 2

struct Paint
    n: i32

impl Paint
    fn from(self: @Paint, k: i32) -> i32
        self.n + k

fn shadow_elsewhere() -> i32
    let Colour = Paint { n: 40 }
    Colour.from(2)

fn main() -> i32
    if shadow_elsewhere() != 42
        return 1
    match Colour.from(2)
        Some(c) => match c
            Blue => 42
            _ => 1
        None => 2
"""

# `E.from` in a generic body reaches emission only as a specialisation:
# rewrite_enum_from_call runs on each clone (clone_expr).  Two instantiations
# at different type arguments pin that each clone is lowered on its own.
FROM_TWO_INSTANCES = """\
import ritzlib.option

enum Colour: u8
    Red = 1
    Blue = 2

fn pick<T>(x: T, n: u8) -> i32
    match Colour.from(n)
        Some(c) => match c
            Blue => 2
            _ => 1
        None => 0

fn main() -> i32
    pick<i32>(1, 2) * 10 + pick<u64>(3, 1)
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_shadowed_enum_name_is_not_rewritten(compiler, tmp_path):
    assert _run(compiler, tmp_path, SHADOWED) == 42


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_shadow_elsewhere_does_not_suppress_lowering(compiler, tmp_path):
    assert _run(compiler, tmp_path, SHADOW_ELSEWHERE) == 42


@pytest.mark.parametrize("compiler", COMPILERS)
def test_enum_from_still_lowers(compiler, tmp_path):
    assert _run(compiler, tmp_path, FROM) == 42


@pytest.mark.parametrize("compiler", COMPILERS)
def test_enum_from_lowers_in_each_generic_instance(compiler, tmp_path):
    assert _run(compiler, tmp_path, FROM_TWO_INSTANCES) == 21
