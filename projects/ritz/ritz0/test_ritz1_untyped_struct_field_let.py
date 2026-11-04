"""AGAST #2172: an untyped `var` / `let` whose initialiser reads a
struct-typed field gets a struct slot in ritz1.

THE DEFECT

emit_var_decl's untyped-init inference (ritz1/src/emitter_stmt.ritz) typed
an EXPR_MEMBER initialiser only when the field was an enum (#1660).  For a
struct-typed field (`var u = o.i`, `var w = mk().i`) the slot kept the
parser default i64: with `o` untyped, `u.x` then failed "unhandled
EXPR_MEMBER", and with `o: Out` annotated, the init emitted
`store i64 %<%In>`, which clang rejects.

THE FIX

When the member chain resolves (resolve_member_chain_field) to a field of
struct type, the slot takes that struct type.  That covers a local root, a
call or method root, a pointer root and a nested chain.

One program per root shape, so a regression names the shape that broke.
ritz0 is the oracle.
"""

import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import _run

TYPES = """\
struct In
    x: i32

struct Out
    i: In
    n: i32

struct Deep
    o: Out
    k: i32

fn mk() -> Out
    return Out { i: In { x: 7 }, n: 1 }

impl Out
    fn twin(self: *Out) -> Out
        return Out { i: In { x: self.i.x + 1 }, n: 0 }

"""

CASES = {
    # The ticket's repro: exit 12 under ritz0.
    "ticket_repro": (
        TYPES
        + """\
pub fn main() -> i32
    var o = Out { i: In { x: 5 }, n: 1 }
    var u = o.i
    var w = mk().i
    return u.x + w.x
""",
        12,
    ),
    # Untyped root (`var o = Out {...}`).
    "local_root_untyped": (
        TYPES
        + """\
pub fn main() -> i32
    var o = Out { i: In { x: 5 }, n: 1 }
    var u = o.i
    return u.x
""",
        5,
    ),
    # Annotated root: this was the `store i64 %<%In>` form.
    "local_root_annotated": (
        TYPES
        + """\
pub fn main() -> i32
    var o: Out = Out { i: In { x: 6 }, n: 1 }
    let u = o.i
    return u.x
""",
        6,
    ),
    "call_root": (
        TYPES
        + """\
pub fn main() -> i32
    let w = mk().i
    return w.x
""",
        7,
    ),
    "method_root": (
        TYPES
        + """\
pub fn main() -> i32
    var o = Out { i: In { x: 8 }, n: 1 }
    let w = o.twin().i
    return w.x
""",
        9,
    ),
    "ptr_param_root": (
        TYPES
        + """\
fn get(p: *Out) -> i32
    let u = p.i
    return u.x

pub fn main() -> i32
    var o = Out { i: In { x: 10 }, n: 1 }
    return get(@o)
""",
        10,
    ),
    "nested_chain": (
        TYPES
        + """\
pub fn main() -> i32
    var d = Deep { o: Out { i: In { x: 3 }, n: 1 }, k: 2 }
    let a = d.o
    let b = d.o.i
    return a.i.x * 10 + b.x + a.n
""",
        34,
    ),
    # The binding is a copy: writing it leaves the source field alone.
    "copy_not_alias": (
        TYPES
        + """\
pub fn main() -> i32
    var o = Out { i: In { x: 5 }, n: 1 }
    var u = o.i
    u.x = 40
    return u.x + o.i.x - 3
""",
        42,
    ),
    # A scalar field next to it still binds an integer.
    "scalar_field_unchanged": (
        TYPES
        + """\
pub fn main() -> i32
    var o = Out { i: In { x: 5 }, n: 37 }
    let n = o.n
    let u = o.i
    return (n as i32) + u.x
""",
        42,
    ),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_untyped_struct_field_let(ritz1_bin, tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", ["local_root_annotated", "call_root"])
def test_ritz1_untyped_struct_field_slot_type(ritz1_bin, tmp_path, name):
    """The binding's slot is `alloca %In`, never the i64 default."""
    src = tmp_path / f"{name}.ritz"
    src.write_text(CASES[name][0])
    ll = tmp_path / f"{name}.ll"
    proc = subprocess.run([str(ritz1_bin), str(src), "-o", str(ll)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-2000:]
    body = ll.read_text().split("@main(", 1)[1].split("\n}", 1)[0]
    allocas = [ln.split("= alloca ", 1)[1].strip() for ln in body.splitlines() if "= alloca " in ln]
    assert "%In" in allocas, body
    assert "store i64" not in "\n".join(ln for ln in body.splitlines() if "%In" in ln), body
