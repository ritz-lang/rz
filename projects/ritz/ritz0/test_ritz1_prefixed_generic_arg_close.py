"""AGAST #2943: a prefixed type argument (`*T`, `@T`, `@&T`, `[N]T`) whose
inner generic closes with `>>` must parse in ritz1, and a parse failure inside
an item must be reported where it happened, not at the item.

THE DEFECT

    import ritzlib.gvec
    pub fn main() -> i32
        var v: Vec<*Vec<i32>> = vec_new<*Vec<i32>>()
        return 0

    error: e2.ritz:3:1: cannot parse item starting at 'pub'
    error: e2.ritz:3:5: cannot parse item starting at 'fn main'

The lexer emits `>>` as one SHR token.  ritz1's grammar lets an SHR close two
type-argument lists through `type_spec_shr` (AGAST #1300), but that rule only
matched a bare `IDENT < ... >>`.  `*Vec<i32>>` is a STAR in front of one, so
no rule closed the outer list, `generic_args` failed, and the whole fn was
dropped.  `Vec<Vec<i32>>` and `Vec<*Vec<i32> >` always parsed.

Both errors pointed at the fn: recovery reported the item at `pub`, skipped
one token to the next anchor (`fn`), failed the same item again and reported
it a second time.

THE FIX

* grammar: `type_spec_shr` gains the prefixed forms `type_spec` has, each
  wrapping a `type_spec_shr`, so `*Vec<i32>>` closes the enclosing list.
* location: the generated `p_advance` keeps a high-water mark (`max_pos`) of
  the furthest token the parser reached, reset at each item.  A dropped item
  is reported at that token (the type's `>>` here), with a note naming the
  item, once: recovery's re-try from a later anchor in the same item reaches
  the same token and is not reported again.

THE MATRIX

One shape per `type_spec_shr` alternative added (the rule, not the cross
product), in both a type annotation and a generic call where the shape
allows.  Parsing is the defect, so these are compile-only; the ticket's
program also runs, with ritz0 as the oracle.
"""

import os
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

RITZ_ROOT = Path(__file__).resolve().parent.parent

BOX = "struct Box<T>\n    v: T\n\n"


def _compile_ritz1(ritz1: Path, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    out = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [str(ritz1), str(src), "-o", str(out)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc, src, out


def _body(*lines: str) -> str:
    return BOX + "pub fn main() -> i32\n" + "".join(f"    {ln}\n" for ln in lines) + "    return 0\n"


# One case per prefixed `type_spec_shr` alternative, plus the places a
# `type_spec_shr` is reached from: a later argument (type_arg_tail_shr), a
# nest of two prefixed closers, and a generic call's type arguments.
PARSES = {
    "ptr": _body("var p: Box<*Box<i64>>"),
    "ref": _body("var b: Box<i64>", "b.v = 1", "var p: Box<@Box<i64>>", "p.v = @b"),
    "mut_ref": _body("var b: Box<i64>", "b.v = 1", "var p: Box<@&Box<i64>>", "p.v = @&b"),
    # `[4]` reaches the `[expr]` alternative: a literal folds like any const.
    "array_number": _body("var p: Box<[4]Box<i64>>"),
    "array_expr": _body("var p: Box<[2 * 2]Box<i64>>"),
    "ptr_ptr": _body("var p: Box<**Box<i64>>"),
    "nested_ptr": _body("var p: Box<*Box<*Box<i64>>>"),
    "second_arg": "struct Pair<A, B>\n    a: A\n    b: B\n\n"
    + _body("var p: Pair<i64, *Box<i64>>"),
    "call_ptr": "import ritzlib.gvec\n\n"
    + _body("var v: Vec<*Vec<i32>> = vec_new<*Vec<i32>>()"),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PARSES))
def test_ritz1_parses_prefixed_arg_closed_by_shr(ritz1_bin, tmp_path, name):
    proc, _src, out = _compile_ritz1(ritz1_bin, tmp_path, name, PARSES[name])
    assert "cannot parse" not in proc.stderr, proc.stderr[-2000:]
    assert proc.returncode == 0 and out.exists(), (
        f"ritz1 rejected {name}:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    )


# The ticket's program, made to observe the pointer it stores: 3 + 4.
TICKET = """\
import ritzlib.gvec

pub fn main() -> i32
    var inner: Vec<i32> = vec_new<i32>()
    vec_push<i32>(@&inner, 3)
    vec_push<i32>(@&inner, 4)
    var v: Vec<*Vec<i32>> = vec_new<*Vec<i32>>()
    vec_push<*Vec<i32>>(@&v, @&inner)
    let back: *Vec<i32> = vec_get<*Vec<i32>>(@v, 0)
    return vec_get<i32>(back, 0) + vec_get<i32>(back, 1)
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_ticket_program_runs(ritz1_bin, tmp_path, compiler):
    assert _run_pkg(compiler, tmp_path, "vec_of_vec_ptr", TICKET) == 7


# --- error location ---------------------------------------------------------
#
# `***` can never follow a complete type argument, so this stays a parse
# error whatever the grammar learns.  Line 8 is `    var p: Box<i64 ***>`;
# the parser gets as far as the first `*`, at column 20.
BAD_TYPE = BOX + "fn ok() -> i32\n    0\n\npub fn main() -> i32\n    var p: Box<i64 ***>\n    return 0\n"


@pytest.mark.integration
def test_parse_error_points_at_the_type(ritz1_bin, tmp_path):
    proc, src, out = _compile_ritz1(ritz1_bin, tmp_path, "bad_type", BAD_TYPE)
    err = proc.stderr
    assert proc.returncode != 0 and not out.exists(), err
    assert f"error: {src}:8:20: unexpected '*'" in err, err
    # The item is still named, at its own line.
    assert f"{src}:7:1: cannot parse item starting at 'pub fn main'" in err, err


@pytest.mark.integration
def test_parse_error_names_a_layout_token(ritz1_bin, tmp_path):
    """An unclosed `Box<i64` stops at the NEWLINE token, whose lexeme is a
    line break: it is named, not quoted."""
    program = BOX + "pub fn main() -> i32\n    var p: Box<i64\n    return 0\n"
    proc, src, _out = _compile_ritz1(ritz1_bin, tmp_path, "bad_eol", program)
    err = proc.stderr
    assert proc.returncode != 0, err
    assert f"error: {src}:5:" in err and ": unexpected end of line\n" in err, err


@pytest.mark.integration
def test_parse_error_reports_the_item_once(ritz1_bin, tmp_path):
    """Recovery re-tries the item from `fn` after skipping `pub`; that is the
    same failure and must not produce a second error."""
    proc, _src, _out = _compile_ritz1(ritz1_bin, tmp_path, "bad_once", BAD_TYPE)
    err = proc.stderr
    assert err.count("error:") == 2, err  # the item, and the module summary
    assert "1 top-level item(s) failed to parse" in err, err


@pytest.mark.integration
def test_parse_error_with_nothing_consumed_keeps_the_item_location(ritz1_bin, tmp_path):
    """A failure at the item's first token has no deeper position to report:
    the item location stays the error line (AGAST #1301's contract)."""
    proc, src, _out = _compile_ritz1(ritz1_bin, tmp_path, "bad_start", "fn ok() -> i32\n    0\n\n@@@\n")
    err = proc.stderr
    assert proc.returncode != 0, err
    assert f"error: {src}:4:1:" in err, err
