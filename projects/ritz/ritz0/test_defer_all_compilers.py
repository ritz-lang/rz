"""AGAST #1625, LARB R14: `defer` (LANGUAGE_SPEC §13.7), the same on all three
compilers.

The runtime rules (exits, order, evaluation at exit, Drop interleave) live in
the matrix files test/test_level41.ritz and test/test_defer_exits.ritz, which
every compiler runs. This file holds what a .ritz test can't: the refusals,
each located at the `defer`, and the move rules, which need a Drop type and a
by-value consumer.
"""

import re

import pytest

from test_borrow_param_ref_field import _compile, _run
from test_ritz1_for_iterable import SELFHOSTED_BIN

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

HEAD = """\
import ritzlib.result

var log: i64 = 0

fn note(d: i64) -> i32
    log = log * 10 + d
    0

fn fails() -> Result<i32, i32>
    Err(1)

struct Noisy
    id: i64

impl Drop for Noisy
    fn drop(self: @&Noisy)
        note(self.id)

fn consume(n: Noisy) -> i32
    note(5)
    0

"""

# The body's first line, after `pub fn main...` (or `fn go...`).
L = HEAD.count("\n") + 2

# name: (program after HEAD, "line:col" of the `defer`, the message).
REFUSED = {
    "return": ("pub fn main() -> i32\n    defer\n        return 1\n    0\n",
               f"{L}:5", "`return` can't leave a deferred statement"),
    "try": ("fn go() -> Result<i32, i32>\n    defer fails()?\n    Ok(0)\n\n"
            "pub fn main() -> i32\n    0\n",
            f"{L}:5", "`?` can't leave a deferred statement"),
    "break": ("pub fn main() -> i32\n    while true\n        defer break\n    0\n",
              f"{L + 1}:9", "`break` can't leave a deferred statement"),
    "continue": ("pub fn main() -> i32\n    for i in 0..3\n        defer\n"
                 "            if i == 1\n                continue\n    0\n",
                 f"{L + 1}:9", "`continue` can't leave a deferred statement"),
    "let": ("pub fn main() -> i32\n    defer let x = 1\n    0\n",
            f"{L}:5", "a deferred `let` or `var` would die at once"),
    "bare": ("pub fn main() -> i32\n    defer\n    0\n",
             f"{L}:5", "`defer` needs a statement"),
    # Checked as if written at the exit: `a` is gone by then.
    "moved_before": ("pub fn main() -> i32\n    let a = Noisy { id: 1 }\n"
                     "    defer note(a.id)\n    consume(a)\n    0\n",
                     f"{L + 1}:5", "`a` may be moved before the deferred statement runs"),
}

# name: (program after HEAD, main's exit code). main returns `log`'s low digits.
RUNS = {
    # A loop wholly inside a deferred block may break out of itself.
    "inner_loop_break": ("pub fn go() -> i32\n    defer\n        while true\n"
                         "            note(3)\n            break\n    note(1)\n    0\n\n"
                         "pub fn main() -> i32\n    go()\n    log as i32\n", 13),
    # A deferred move is the binding's last use: consume drops it (5 then 1),
    # and the binding isn't dropped again at the exit.
    "deferred_move": ("pub fn go() -> i32\n    let a = Noisy { id: 1 }\n"
                      "    defer consume(a)\n    note(2)\n    0\n\n"
                      "pub fn main() -> i32\n    go()\n    log as i32\n", 251),
}


@pytest.fixture
def compile_with(ritz1_bin, tmp_path):
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _compile("ritz0", None, tmp_path, name, program)
        return _compile("ritz1", bins[compiler], tmp_path, name, program)
    return go


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _run("ritz0", None, tmp_path, name, program)
        return _run("ritz1", bins[compiler], tmp_path, name, program)
    return go


def _refusal(comp, ll, program):
    """`line:col`, message of the first located error."""
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"accepted:\n{program}"
    assert not ll.exists()
    found = re.search(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert found, f"no location:\n{out[-2000:]}"
    return found.group(1), found.group(2).strip()


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_bad_defer_is_refused_at_the_defer(compile_with, compiler, name):
    body, where, message = REFUSED[name]
    program = HEAD + body
    comp, ll, _ = compile_with(compiler, name, program)
    assert _refusal(comp, ll, program) == (where, message)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_a_legal_defer_runs(run_with, compiler, name):
    body, expected = RUNS[name]
    assert run_with(compiler, name, HEAD + body) == expected
