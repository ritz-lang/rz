"""AGAST #2276: a raise inside a closure body restores the enclosing fn's state.

`_emit_closure` swaps the enclosing function's emission state out for the
closure's own and swaps it back afterwards.  It used to swap back only on the
normal path, so an error in the body (`|x| nosuchname + x`) left the closure's
state installed: the enclosing `_emit_stmt`'s `finally` then popped the
closure's empty `_temp_frames` and its IndexError replaced the real, located
diagnostic.  The end-to-end symptom is pinned by
`test_ritz0_closure_error_keeps_its_diagnostic` (test_return_expected_enum.py);
these rows pin each piece of saved state, one row per piece, in-process.
"""

import pytest

from const_eval import evaluate_array_sizes
from emitter_llvmlite import LLVMEmitter
from lexer import tokenize
from parser import Parser

# `k` is an SSA `let`, bound in `params`, so the enclosing `params` is not
# the empty dict the closure installs.
SOURCE = """\
fn g(n: i32) -> i32
    let k = n + 1
    let f: fn(i32) -> i32 = |x| nosuchname + x
    f(n)
"""


def _state(emitter, name):
    """The comparable value of one piece of saved state."""
    value = getattr(emitter, name)
    # `locals`, `params` and `ritz_types` are saved as copies and restored
    # from them, so they come back equal, not identical.
    if name in ("locals", "params", "ritz_types"):
        return dict(value)
    return value


@pytest.mark.parametrize("name", [
    "builder", "current_fn", "locals", "params", "ritz_types",
    "has_returned", "_temp_frames",
])
def test_closure_error_restores_enclosing_state(name):
    module = Parser(tokenize(SOURCE)).parse_module()
    assert evaluate_array_sizes(module) == []  # as ritz0.py does before emitting
    emitter = LLVMEmitter()
    emit_closure = emitter._emit_closure
    seen = {}

    def spy(closure):
        # `main` has not returned yet, which is what the closure resets
        # `has_returned` to; make the enclosing value differ so a leak shows.
        emitter.has_returned = True
        before = _state(emitter, name)
        try:
            return emit_closure(closure)
        finally:
            seen["before"], seen["after"] = before, _state(emitter, name)

    emitter._emit_closure = spy
    # Any exception: which one reaches the user is the end-to-end test's
    # business, and a leaked `_temp_frames` must not redden the other rows.
    with pytest.raises(Exception):
        emitter.emit_module(module)
    if name in ("builder", "current_fn", "_temp_frames"):
        assert seen["after"] is seen["before"]
    else:
        assert seen["after"] == seen["before"]
