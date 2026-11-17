"""ritz1 prints its "emitted N unlowerable expression(s)" summary only for
errors it could not locate (AGAST #3257).

Every emitter error bumps `s.error_count`, and main.ritz used to print

    error: ritz1 emitted 1 unlowerable expression(s); refusing to write output

after any of them.  For a located error, e.g. `h.0` on a named struct
(#3233: "main.ritz:5:5: `Holder` has no field `0`"), that unlocated line is
noise after the real diagnostic.

The rule: the summary is printed only when at least one error came from the
`; ERROR:` comment path (emit_ir_error and friends), which has no location,
and N counts just those.  The exit status is non-zero and no IR is written
either way.

Rows run through ritz1 and ritz1_selfhosted (ritz0 has no such summary).
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
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

# An unlocated one only: the `; ERROR: unknown identifier` site (#1369),
# which names the identifier (emit_ir_error_begin/_end) ...
_UNLOCATED = """\
fn main() -> i32
    return no_such_name
"""

# ... and a plain emit_ir_error: a BitOps method with the wrong arity.
_UNLOCATED_PLAIN = """\
fn main() -> i32
    let n: i32 = 5
    n.rotl()
"""

# Both: the unlocated one still earns the summary, counting only itself.  The
# located one is an emitter error (an unsupported `for` iterable): `h.0` is
# Sema's now (AGAST #3509), as is a `let` store (#3504), and a Sema error
# stops the compile before the emitter.
_BOTH = """\
fn f() -> i32
    var q: i32 = 3
    var t: i32 = 0
    for x in q
        t = t + 1
    t

fn main() -> i32
    return no_such_name
"""

# Said by Sema now (deref_field.ritz, AGAST #3509), in diag's form (#3445).
_HAS_NO_FIELD = "unit.ritz:6:7: error: `Holder` has no field `0`"
_FOR_ITERABLE = "unit.ritz:4:14: this `for` iterable is not supported in ritz1"
_UNKNOWN = "cannot emit: unknown identifier"

# name -> (source, messages that must appear, expected summary line or None)
CASES = {
    "located_only": (_LOCATED, [_HAS_NO_FIELD], None),
    "unlocated_only": (_UNLOCATED, [_UNKNOWN], f"error: ritz1 emitted 1 {SUMMARY}"),
    "unlocated_plain": (
        _UNLOCATED_PLAIN,
        ["cannot emit: wrong number of arguments to integer BitOps method"],
        f"error: ritz1 emitted 1 {SUMMARY}",
    ),
    "located_and_unlocated": (
        _BOTH, [_FOR_ITERABLE, _UNKNOWN], f"error: ritz1 emitted 1 {SUMMARY}"
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
