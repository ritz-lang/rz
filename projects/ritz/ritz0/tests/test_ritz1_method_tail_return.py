"""AGAST #1573: ritz1 gives impl methods the same implicit-return tail as fns.

THE DEFECT

emit_impl_method (ritz1/src/emitter.ritz) emitted an implicit `ret` only when
the method's LAST statement was a bare expression (STMT_EXPR). emit_fn also
has a fallback after the body: return `last_expr_here` if it has a value in
the current block, otherwise `ret <T> 0`. The method path had neither. So a
non-void method ending in an `if`, a loop or a `let` left its final block
with no terminator:

    L2:
    }

The ritz1 compile still exited 0. clang rejects the IR.

The structural check below also asserts that every ritz1 block is terminated
and never gets a second `ret`. clang accepts a stray second `ret` as a dead unnamed block, so
the exit code alone would not catch a doubled return.

Oracle: ritz0 compiles every program in CASES, and both binaries return the
same exit code. Each program also has an identical free-fn twin that goes
through emit_fn, so the method path has to match the fn path, not just ritz0.

AGAST #1429 and #2236 made both compilers reject a non-void fn that reaches its
end without a value, so the shapes that once fell back to `ret <T> 0` are now
test_ritz1_fn_tail_requires_value.py's concern, not this file's.
"""

import re

import pytest

from test_ritz1_builtin_struct_shadow import _run

# A method ending in an if/else whose arms both yield a value. The tail
# returns that value through `last_expr_here`, the same way emit_fn does.
IF_ELSE_VALUE = """\
struct Box
    v: i64

impl Box
    fn pick(self, c: i64) -> i64
        if c > 0
            self.v
        else
            3

fn pickf(v: i64, c: i64) -> i64
    if c > 0
        v
    else
        3

pub fn main() -> i32
    let b: Box = Box { v: 7 }
    if b.pick(1) != pickf(7, 1)
        return 1
    if b.pick(0) != pickf(7, 0)
        return 2
    return (b.pick(1) * 10 + b.pick(0)) as i32
"""

# Controls: an explicit trailing `return` and a bare trailing expression must
# not gain a second `ret` (a terminator in the middle of a block is also
# invalid IR). The void method ending in an `if` must still get `ret void`, as
# must the `-> void` spelling (normalised to TYPE_VOID by the parser), and the
# one ending in a bare `return` must get only one.
CONTROLS = """\
struct Box
    v: i64

impl Box
    fn er(self, c: i64) -> i64
        if c > 0
            return 5
        return 6

    fn te(self) -> i64
        self.v + 1

    fn vd(self, c: i64)
        if c > 0
            let q: i64 = 1

    fn vr(self)
        return

    fn nv(self, c: i64) -> void
        if c > 0
            let q: i64 = 1

pub fn main() -> i32
    let b: Box = Box { v: 7 }
    b.vd(1)
    b.vr()
    b.nv(1)
    return (b.er(1) + b.er(0) + b.te()) as i32
"""

CASES = [
    ("if_else_value", IF_ELSE_VALUE),
    ("controls", CONTROLS),
]


_TERMINATORS = ("ret ", "ret\n", "br ", "unreachable", "switch ")


def _block_shape_errors(ll_text: str) -> list[str]:
    """Return one message per block in `ll_text` that is unterminated or has
    a `ret` after its terminator."""
    errors = []
    fn = None
    terminated = False
    for line in ll_text.splitlines():
        if line.startswith("define "):
            fn = re.search(r"@([\w$.]+)\(", line).group(1)
            terminated = False
            continue
        if fn is None:
            continue
        body = line.strip()
        if not body or body.startswith(";"):
            continue
        if body == "}":
            if not terminated:
                errors.append(f"{fn}: final block has no terminator")
            fn = None
        elif re.fullmatch(r"[\w.$]+:", body):
            if not terminated and body != "entry:":
                errors.append(f"{fn}: falls through into {body}")
            terminated = False
        elif terminated:
            # Only a second `ret` is the tail's doing. `if c: return x` still
            # emits a dead `br` after its `ret` (valid IR, and not #1573's
            # concern), so other trailing instructions are ignored.
            if body == "ret void" or body.startswith("ret "):
                errors.append(f"{fn}: second ret after a terminator: {body}")
        elif (body + "\n").startswith(_TERMINATORS):
            terminated = True
    return errors


@pytest.mark.integration
@pytest.mark.parametrize("name,program", CASES, ids=[c[0] for c in CASES])
def test_method_tail_matches_ritz0(ritz1_bin, tmp_path, name, program):
    expected = _run("ritz0", tmp_path, name, program)
    got = _run("ritz1", tmp_path, name, program)
    shape = _block_shape_errors((tmp_path / f"{name}_ritz1.ll").read_text())
    assert not shape, f"{name}: malformed blocks in ritz1 IR:\n" + "\n".join(shape)
    assert got == expected, f"{name}: ritz1 exit {got}, ritz0 exit {expected}"
