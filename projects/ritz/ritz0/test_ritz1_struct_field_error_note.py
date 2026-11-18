"""AGAST #3271: a struct field's parse error notes the struct, not the field.

THE DEFECT

    struct P
        c: m.S

    f.ritz:2:8: error: `m.S`: there is no `module.item` access ...
    note: f.ritz:2:5: cannot parse item starting at ' c'

The bodied `struct_def` failed at the field, and the field-less form
(AGAST #2955, `STRUCT IDENT NEWLINE`) then matched its prefix: `struct P`
parsed as an empty struct and the body's INDENT was left as the next "item".
Recovery dropped that one, so the note sat on the INDENT and printed its
lexeme (a space) and the field name.

THE FIX

The field-less form refuses when an INDENT follows its NEWLINE
(`fieldless_struct_def_new`): a struct with a body is never field-less.  The
struct item fails whole, and the note names it at its own line:col, as it
does for `fn f` and `pub fn main`.

One case per shape the note prints (`struct P`, and the `pub` prefix with
generic params), each on both ritz1 binaries.  The field-less form itself is
pinned by test_ritz1_fieldless_struct.py.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
COMPILERS = ["ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

# The ticket's program: a dotted field type (#2215).  `fn main` after it must
# still parse, so the struct is the only dropped item.
DOTTED = """\
import ritzlib.sys

struct P
    c: m.S

fn main() -> i32
    0
"""

# A plain field error in a later field of a `pub` generic struct.
PUB_GENERIC = """\
pub struct Q<T>
    a: i32
    b: i32 i32

fn main() -> i32
    0
"""


def _stderr(compiler, tmp_path, src):
    path = tmp_path / "f.ritz"
    path.write_text(src)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    proc = subprocess.run([str(binary), str(path), "-o", str(tmp_path / "f.ll")],
                          cwd=tmp_path, env=env, capture_output=True, text=True,
                          timeout=120)
    assert proc.returncode != 0, f"{compiler} accepted:\n{src}"
    return proc.stdout + proc.stderr


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("src, error, note", [
    (DOTTED, "f.ritz:4:8: error: `m.S`: there is no `module.item` access",
     "f.ritz:3:1: cannot parse item starting at 'struct P'"),
    (PUB_GENERIC, "f.ritz:3:12: error: unexpected 'i32'",
     "f.ritz:1:1: cannot parse item starting at 'pub struct Q'"),
], ids=["dotted", "pub_generic"])
def test_field_error_notes_the_struct(compiler, tmp_path, src, error, note):
    out = _stderr(compiler, tmp_path, src)
    assert error in out, out
    assert "note: " in out and note in out, out
    # Only the struct is dropped: no stray item at the body's INDENT and no
    # cascade into `fn main`.
    assert out.count("cannot parse item") == 1, out
    assert "1 top-level item(s) failed to parse" in out, out
