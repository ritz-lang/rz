"""AGAST #1730: ritz1's parser arena is sized to the input and bounds-checked.

THE DEFECT

parse_tokens (ritz1/src/main.ritz) bump-allocated every AST node from a fixed
4 MB malloc, and parser_alloc (ast_helpers.ritz) never checked the bound.  A
large enough source silently overran the arena into the rest of the heap.
ritz1's own src/emitter_stmt.ritz already overran it by ~7.5k allocations on
origin/main 0f49e9a.  That was harmless only by luck: a few hundred more AST
nodes (#1730's sret change) moved the overrun onto live data, and the
self-hosting bootstrap died parsing emitter_stmt.ritz at "line 29502" of a
3k-line file.

THE FIX

parse_tokens sizes the arena from the token count (interp.ritz's existing
bound: a few 128-byte nodes per token, 1 KB per token), keeping 4 MB as a
floor.  parser_bump (behind parser_new) now fails loudly, with a nonzero exit, if an allocation
ever passes the arena's capacity, instead of corrupting the heap.
"""

import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import RITZ_ROOT, _run
from test_ritz1_for_iterable import run_with  # noqa: F401  (fixture)

# ~72k tokens: well past the old 4 MB arena (about 60 bytes of AST per token
# here), and still quick to compile.
N_STMTS = 12000
LONG_PROGRAM = (
    "pub fn main() -> i32\n"
    "    var x: i64 = 0\n"
    + "    x = x + 1\n" * N_STMTS
    + f"    return (x - {N_STMTS - 42}) as i32\n"
)


@pytest.mark.integration
def test_ritz0_oracle_long_program(tmp_path):
    assert _run("ritz0", tmp_path, "long", LONG_PROGRAM) == 42


@pytest.mark.integration
def test_ritz1_long_program_fits_parser_arena(ritz1_bin, tmp_path):
    """A source whose AST is bigger than 4 MB parses intact (no overflow)."""
    assert _run("ritz1", tmp_path, "long", LONG_PROGRAM) == 42


@pytest.mark.integration
def test_ritz1_self_compiles_emitter_stmt(ritz1_bin, tmp_path):
    """The bootstrap's real victim: ritz1 parses its own emitter_stmt.ritz."""
    src_dir = RITZ_ROOT / "ritz1" / "src"
    out = tmp_path / "emitter_stmt.ll"
    proc = subprocess.run(
        [str(ritz1_bin), str(src_dir / "emitter_stmt.ritz"), "-o", str(out)],
        cwd=src_dir.parent,
        env={"RITZ_PATH": str(RITZ_ROOT), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0 and out.exists(), proc.stderr[-2000:]
    assert "arena" not in proc.stderr, proc.stderr[-2000:]


# AGAST #4842: a failed alternative's nodes stay in the arena, so a grammar rule
# that re-parses a nested expression multiplies the arena use per nesting level.
# `call_args : args COMMA | args` parsed every argument list twice when it had
# no trailing comma, `args : expr COMMA args | expr` parsed the last argument
# twice, and postfix_op's `LBRACKET expr ...` slices parsed an index five
# times.  The ticket's file, 100 lines of `n += k("a", "b", p(p(1, 2), p(3,
# 4)))`, took ~2 KB a token and hit the 1 KB-a-token cap ("parser arena
# exhausted"); a bigger file only made the cap bigger by the same factor.
# Each program below exhausts the old arena on its own rule, and fits now
# that every argument and index is parsed once.

RITZ1S = ["ritz1", "ritz1_selfhosted"]
REPRO_HEADER = (
    "fn k(a: StrView, b: StrView, c: i32) -> i32\n    c\n\n"
    "fn p(a: i32, b: i32) -> i32\n    a + b\n\n"
)


def _repro(n_lines: int) -> str:
    """The ticket's file: each line adds p(p(1, 2), p(3, 4)) == 10."""
    return (REPRO_HEADER + "pub fn main() -> i32\n    var n: i32 = 0\n"
            + '    n += k("a", "b", p(p(1, 2), p(3, 4)))\n' * n_lines
            + f"    return n - {10 * n_lines - 42}\n")


def _nested(depth: int, wrap) -> str:
    s = "0"
    for _ in range(depth):
        s = wrap(s)
    return s


# Each `p(.., 1)` adds 1: the nesting is in a first argument, so only
# call_args's re-parse of the whole list doubles it.
FIRST_ARG = (REPRO_HEADER + "pub fn main() -> i32\n"
             f"    return {_nested(22, lambda s: f'p({s}, 1)')} + 20\n")
# The nesting is in a last argument, which args re-parsed as well (so the old
# call_args alone also overran the arena here).
LAST_ARG = (REPRO_HEADER + "pub fn main() -> i32\n"
            f"    return {_nested(22, lambda s: f'p(1, {s})')} + 20\n")
# arr maps 0->1->2->3->0, so 13 lookups from 0 end on 1; five parses per level
# overran the arena by depth 9.
DEEP_INDEX = ("pub fn main() -> i32\n    var arr: [4]i32 = [1, 2, 3, 0]\n"
              f"    return {_nested(13, lambda s: f'arr[{s}]')} + 41\n")

NESTING = {
    "repro_100": _repro(100),     # under the cap's 4 MB floor
    "repro_2000": _repro(2000),   # where the cap scales with the tokens
    "first_arg": FIRST_ARG,
    "last_arg": LAST_ARG,
    "index": DEEP_INDEX,
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", list(NESTING))
def test_ritz1_nested_expressions_fit_parser_arena(run_with, compiler, name):
    """Nested calls and indexes parse each expression once, not 2^depth times."""
    assert run_with(compiler, name, NESTING[name]) == 42
