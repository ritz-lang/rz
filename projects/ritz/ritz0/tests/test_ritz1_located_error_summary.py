"""ritz1 prints its "emitted N unlowerable expression(s)" summary only for
errors it could not locate (AGAST #3257).

Every emitter error bumps `s.error_count`, and main.ritz used to print

    error: ritz1 emitted 1 unlowerable expression(s); refusing to write output

after any of them.  For a located error, e.g. `h.0` on a named struct
(#3233: "main.ritz:5:5: `Holder` has no field `0`"), that unlocated line is
noise after the real diagnostic.

The rule: the summary is printed only when at least one error was printed
with no file:line:col, and N counts just those.  The exit status is non-zero
and no IR is written either way.

Since AGAST #3621 the emit_ir_error family (the `; ERROR:` comment path,
#1369) is located too, at the construct it could not lower, so it earns no
summary.  What is left unlocated is what has no position to report: a source
`struct StrView` of the wrong layout (a StructDef records none) and the
multi-dimensional leak tally.

Rows run through ritz1 and ritz1_selfhosted (ritz0 has no such summary).
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

COMPILERS = ["ritz1", "ritz1_selfhosted"]

SUMMARY = "unlowerable expression(s); refusing to write output"

# A located emitter error only: `.0` on a named struct (#3233).
_LOCATED = """\
struct Holder
    n: i32

fn main() -> i32
    var h = Holder { n: 2 }
    h.0
"""

# The emit_ir_error_begin/_end site (#1369): `unknown identifier`, naming it.
# A name nothing declares is Sema's since AGAST #4595; a payload variant used
# bare is declared, so it still reaches the emitter.
_UNKNOWN_IDENT = """\
enum E
    Empty
    Holds(i32)

fn main() -> i32
    let e: E = Holds
    return 0
"""

# ... and a plain emit_ir_error: a BitOps method with the wrong arity.
_BITOPS_ARITY = """\
fn main() -> i32
    let n: i32 = 5
    n.rotl()
"""

# An unlocated one: a StructDef records no position (ensure_view_struct).
_BAD_STRVIEW = """\
struct StrView
    a: i32

fn main() -> i32
    0
"""

# Both: the unlocated one still earns the summary, counting only itself.
_BOTH = """\
struct StrView
    a: i32

enum E
    Empty
    Holds(i32)

fn main() -> i32
    let e: E = Holds
    return 0
"""

# Said by Sema now (deref_field.ritz, AGAST #3509), in diag's form (#3445).
_HAS_NO_FIELD = "unit.ritz:6:7: error: `Holder` has no field `0`"
_STRVIEW = "error: ritz1 cannot emit: struct StrView must be { ptr: *u8, len: i64 }"

# name -> (source, messages that must appear, expected summary line or None)
CASES = {
    "located_only": (_LOCATED, [_HAS_NO_FIELD], None),
    # AGAST #3621: located, so no summary.
    "emit_ir_error_begin": (
        _UNKNOWN_IDENT,
        ["unit.ritz:6:16: error: ritz1 cannot emit: unknown identifier 'Holds'"],
        None,
    ),
    "emit_ir_error": (
        _BITOPS_ARITY,
        ["unit.ritz:3:5: error: ritz1 cannot emit: wrong number of arguments to integer BitOps method"],
        None,
    ),
    "unlocated_only": (_BAD_STRVIEW, [_STRVIEW], f"error: ritz1 emitted 1 {SUMMARY}"),
    "located_and_unlocated": (
        _BOTH,
        [_STRVIEW, "unit.ritz:9:16: error: ritz1 cannot emit: unknown identifier 'Holds'"],
        f"error: ritz1 emitted 1 {SUMMARY}",
    ),
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
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CASES))
def test_summary_follows_only_unlocated_errors(request, tmp_path, compiler, name):
    source, messages, summary = CASES[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"
    for msg in messages:
        assert msg in out, f"{compiler}, {name}: want {msg!r}:\n{out[-1500:]}"
    if summary is None:
        assert SUMMARY not in out, f"{compiler}, {name}: unlocated summary after a located error:\n{out[-1500:]}"
    else:
        lines = [ln for ln in out.splitlines() if SUMMARY in ln]
        assert lines == [summary], f"{compiler}, {name}: want {summary!r}:\n{out[-1500:]}"
