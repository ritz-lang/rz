"""ritz1's call and statement errors print through `diag` (AGAST #3445, #3621).

Every ritz1 error is one line, `<file>:<line>:<col>: error: <message>`
(ritz1/src/diag.ritz).  Before #3445 the printers in emitter_expr_call.ritz
wrote the other order,

    error: unit.ritz:7:7: no method `cmp` on `Foo`: ...

and the emit_ir_error family in emitter_expr_call.ritz / emitter_stmt.ritz
had no location at all:

    error: ritz1 cannot emit: wrong number of arguments to integer BitOps method

Now both are `unit.ritz:L:C: error: ...`, at the construct the message is
about.  Only the prefix moved: the message text is ritz0's (*_rules.py) and
stays byte for byte.

One row per printer, each able to fail on its own: an emit_ir_error call in
emitter_expr_call (the method call), the two in emitter_stmt that have a
statement-side span (the assignment's, and the assigned value's), and each
`error: ` printer of emitter_expr_call reachable from source.  The
let/ownership/ref_check printers already printed this form and print it
through diag since AGAST #3621; their own tests (test_ritz1_instance_move_*,
test_borrow_param_ref_slot, ...) hold them to it, and the row below holds
let_check's emitter-side one, which nothing else located.

Rows run through ritz1 and ritz1_selfhosted (ritz0 words these its own way).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

COMPILERS = ["ritz1", "ritz1_selfhosted"]

# name -> (source, line, col, message after `error: `)
CASES = {
    # emitter_expr_call: emit_ir_error, at the method call.
    "call_emit_ir_error": ("""\
fn main() -> i32
    let n: i32 = 5
    n.rotl()
""", 3, 5, "ritz1 cannot emit: wrong number of arguments to integer BitOps method"),
    # emitter_stmt: emit_ir_error_begin/_end, at the assignment.
    "stmt_unknown_variable": ("""\
fn main() -> i32
    no_such = 5
    0
""", 2, 5, "ritz1 cannot emit: unknown variable 'no_such'"),
    # emitter_stmt: emit_ir_error, at the value assigned.
    "stmt_array_length": ("""\
fn main() -> i32
    var a: [4]i32 = [1, 2, 3, 4]
    var b: [3]i32 = [0, 0, 0]
    b = a
    b[0]
""", 4, 9, "ritz1 cannot emit: array length does not match the local array's length"),
    # refuse_no_method, at the method name.
    "no_method": ("""\
struct Foo
    n: i32

fn main() -> i32
    let a = Foo { n: 1 }
    let b = Foo { n: 2 }
    a.cmp(b)
    0
""", 7, 7, "no method `cmp` on `Foo`: declare it in `impl Foo`"),
    # call_check.ritz's ca_array (AGAST #4173), at the call.
    "arg_type": ("""\
fn f(a: [3]i32) -> i32
    a[0]

fn main() -> i32
    let b: [4]i32 = [1, 2, 3, 4]
    f(b)
""", 6, 5, "argument 1 of `f` has the wrong type: the array's length isn't the parameter's"),
    # sizeof_error, at the operand.
    "sizeof": ("""\
fn main() -> i32
    sizeof(nosuch) as i32
""", 2, 12, "sizeof: unknown type or value `nosuch`"),
    # try_emit_enum_from, at the call.
    "enum_from": ("""\
enum E
    A
    B

fn main() -> i32
    let e = E.from(1)
    0
""", 6, 13, "enum 'E' has no 'from': that needs a representation type "
            "('enum E: <integer type>') and its module must import ritzlib.option"),
    # static_call_of_self_error, at the call.
    "static_call_of_self": ("""\
struct C
    n: i32

impl C
    fn get(self) -> i32
        self.n

fn main() -> i32
    C.get()
""", 9, 5, "Static method call Type.method() but method 'get' expects 'self' "
           "parameter: write `c.get()` or `C_get(c)`"),
    # refuse_receiver_short_of_self, at the receiver.
    "receiver_short_of_self": ("""\
struct C
    x: i32

impl C
    fn rd(self: **C) -> i32
        self.x

fn mk(c: *C) -> *C
    c

fn main() -> i32
    var c = C { x: 3 }
    mk(@&c).rd()
""", 13, 5, "a receiver of a pointer `self` must be a place one level short of it, "
            "or have its levels"),
    # let_check's let_error on the emitter's side (env.s set): ref_check
    # refuses `@x` of a `let` in an `@&` slot (AGAST #3621).
    "let_borrow_emitter": ("""\
fn f(p: @&i32) -> i32
    0

fn main() -> i32
    let x: i32 = 1
    f(@x)
""", 6, 7, "cannot borrow `let` binding `x` as mutable; declare it `var`"),
}


def _compile(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    proc = subprocess.run([str(binary), str(src.name), "-o", str(ll)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CASES))
def test_error_is_located_through_diag(request, tmp_path, compiler, name):
    source, line, col, message = CASES[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"
    want = rf"^unit\.ritz:{line}:{col}: error: {re.escape(message)}$"
    assert re.search(want, out, re.M), f"{compiler}, {name}: want {want!r}:\n{out[-1500:]}"
