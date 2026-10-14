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
floor.  parser_alloc now fails loudly, with a nonzero exit, if an allocation
ever passes the arena's capacity, instead of corrupting the heap.
"""

import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import (  # noqa: F401
    RITZ_ROOT,
    _run,
    ritz1_bin,
)

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
def test_ritz1_long_program_fits_parser_arena(ritz1_bin, tmp_path):  # noqa: F811
    """A source whose AST is bigger than 4 MB parses intact (no overflow)."""
    assert _run("ritz1", tmp_path, "long", LONG_PROGRAM) == 42


@pytest.mark.integration
def test_ritz1_self_compiles_emitter_stmt(ritz1_bin, tmp_path):  # noqa: F811
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
