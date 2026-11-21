"""AGAST #3975: a bare `self:&` is its impl's struct, in Sema too.

THE GAP

The parser names a bare `self` (`self: T`, impl_name_bare_self) but leaves a
bare `self:&` nameless: the emitter takes its type from the ImplBlock.  So
Sema's sema_bind_param bound it as a struct with no name, sema_bool_kind
answered BK_UNSURE for `self.b` and `self.t.ok()`, and bool_check refused
`if self.t.ok()` with "ritz1 cannot tell that it is" (prism's
compositor/mod.ritz:298 `if not self.damage.has_damage()` in
`render_frame(self:&)`).  ritz0 compiles it.

THE CHANGE

sema_check_module records the impl whose method it walks (Sema.cur_impl), and
sema_bind_param names a nameless `self:&` from it.

THE TESTS

`if <r>.b` and `if <r>.t.ok()` compile on all three compilers under each
receiver form; the `self:&` rows failed before the change.  An integer field
`if self.t.v` under `self:&` is "got an integer", not "cannot tell": Sema
knows the type, it does not merely give up quietly.
"""

import re

import pytest

from test_ref_into_value import _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PRELUDE = """\
struct T
    v: i32

impl T
    pub fn ok(self) -> bool
        self.v == 1

struct D
    t: T
    b: bool

"""

MAIN = """
fn main() -> i32
    var d = D {{ t: T {{ v: 1 }}, b: true }}
    {call}
"""

# How the method or fn names its D, and how main calls it.
RECEIVERS = {
    "self": ("impl D\n    pub fn run(self) -> i32", "self", "d.run()"),
    "self_lent": ("impl D\n    pub fn run(self:&) -> i32", "self", "d.run()"),
    "self_at_mut": ("impl D\n    pub fn run(self: @&D) -> i32", "self", "d.run()"),
    "param_lent": ("fn run(x:& D) -> i32", "x", "run(@&d)"),
    "param_at": ("fn run(x: @D) -> i32", "x", "run(@d)"),
}

CONDITIONS = {"field": "{r}.b", "method_on_field": "{r}.t.ok()"}


def _program(form, cond):
    head, r, call = RECEIVERS[form]
    ind = "        " if head.startswith("impl") else "    "
    body = f"{ind}if {cond.format(r=r)}\n{ind}    return 1\n{ind}0\n"
    return PRELUDE + head + "\n" + body + MAIN.format(call=call)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("cond", CONDITIONS)
@pytest.mark.parametrize("form", RECEIVERS)
def test_a_field_or_method_of_a_receivers_field_is_a_condition(request, tmp_path, compiler, form, cond):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    src = _program(form, CONDITIONS[cond])
    comp, ll, _ = _compile(compiler, tmp_path, f"recv_{form}_{cond}", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused {form} {cond}:\n{src}\n{out}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_integer_field_of_self_lent_is_an_integer(request, tmp_path, compiler):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    src = _program("self_lent", "{r}.t.v")
    comp, ll, _ = _compile(compiler, tmp_path, "recv_int", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted `if self.t.v`:\n{out}"
    assert re.search(r":14:12: .*if condition must be bool, got an integer", out), f"{compiler}:\n{out}"
