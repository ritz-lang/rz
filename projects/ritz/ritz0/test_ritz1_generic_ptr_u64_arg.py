"""Regression tests for AGAST #1519: ritz1 generic TYPE ANNOTATIONS whose
argument is a pointer or u64 (`Vec<*u8>`, `Vec<u64>`).

ritz1 spelled a generic type argument only for u8/i8/i32/i64 or a struct
name; anything else spelled as "", so `var v: Vec<*u8>` declared `%Vec$`
while the call sites instantiated `Vec$ptr_u8` / `Vec$u64`, and clang
rejected the IR (examples/tier5_async/44_csv, ritz0/test/test_level22.ritz).

The fix spells pointer arguments as ritz0 does (`ptr_` + pointee) and adds
u64.  Other widths, bool and floats are AGAST #1639.

ritz0 is the oracle for every runnable program.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import RITZ1_BIN, RITZ_ROOT, _run_pkg


def _compile_ritz1(tmp_path: Path, program: str) -> str:
    """Compile `program` with ritz1 (no link); fail on any error; return IR."""
    src = tmp_path / "spell.ritz"
    src.write_text(program)
    ll = tmp_path / "spell.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    proc = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"ritz1 failed:\n{out[-2000:]}"
    assert "unhandled EXPR_MEMBER" not in out, out[-2000:]
    return ll.read_text()


HEADER = """\
import ritzlib.memory
import ritzlib.gvec

"""

PROGRAMS = {
    # The ticket's repro.
    "vec_ptr_u8": HEADER
    + """\
pub fn main() -> i32
    var v: Vec<*u8> = vec_new<*u8>()
    vec_push<*u8>(@v, c"x")
    return v.len as i32
""",
    # Vec<u64> push / get / len round-trip.
    "vec_u64": HEADER
    + """\
pub fn main() -> i32
    var v: Vec<u64> = vec_new<u64>()
    vec_push<u64>(@v, 40)
    vec_push<u64>(@v, 2)
    let s: u64 = vec_get<u64>(@v, 0) + vec_get<u64>(@v, 1)
    return (s + v.len as u64) as i32
""",
    # Pointer to a user struct: `ptr_` + the struct name.
    "vec_ptr_struct": HEADER
    + """\
struct Cell
    x: i64

pub fn main() -> i32
    var a: Cell
    a.x = 9
    var b: Cell
    b.x = 33
    var v: Vec<*Cell> = vec_new<*Cell>()
    vec_push<*Cell>(@v, @a)
    vec_push<*Cell>(@v, @b)
    let p: *Cell = vec_get<*Cell>(@v, 1)
    return (p.x + v.len) as i32
""",
    # A generic annotation inside a struct field (44_csv's shape).
    "field_vec_ptr_u8": HEADER
    + """\
struct Row
    cells: Vec<*u8>
    n: i64

pub fn main() -> i32
    var r: Row
    r.cells = vec_new<*u8>()
    r.n = 5
    vec_push<*u8>(@r.cells, c"ab")
    vec_push<*u8>(@r.cells, c"cd")
    let s: *u8 = vec_get<*u8>(@r.cells, 1)
    return (*s as i64 + r.cells.len + r.n) as i32
""",
    # AGAST #1796: `Vec<T>.data` at T = *u8 is `**u8`.  It was cloned as
    # `*u8` (1-byte stride, `load i8`), so get/pop returned garbage pointers.
    "vec_ptr_get_pop_deref": HEADER
    + """\
pub fn main() -> i32
    var v = vec_new<*u8>()
    let a: *u8 = c"a"
    let b: *u8 = c"bc"
    vec_push<*u8>(@v, a)
    vec_push<*u8>(@v, b)
    vec_push<*u8>(@v, c"d")
    if vec_get<*u8>(@v, 1) != b
        return 1
    let top: *u8 = vec_pop<*u8>(@v)
    if vec_get<*u8>(@v, 0) != a
        return 2
    return (*top as i64 - 100 + *(vec_get<*u8>(@v, 1) + 1) as i64 - 99 + v.len * 10) as i32
""",
    # Same, for a pointer to a struct (`**Cell` element).
    "vec_ptr_struct_get_set": HEADER
    + """\
struct Cell
    x: i64

pub fn main() -> i32
    var a: Cell
    a.x = 4
    var b: Cell
    b.x = 30
    var v: Vec<*Cell> = vec_new<*Cell>()
    vec_push<*Cell>(@v, @a)
    vec_push<*Cell>(@v, @a)
    vec_set<*Cell>(@v, 1, @b)
    let p: *Cell = vec_get<*Cell>(@v, 0)
    let q: *Cell = vec_get<*Cell>(@v, 1)
    return (p.x + q.x + v.len * 100) as i32
""",
    # A pointer argument to a generic fn parameter / return type.
    "fn_param_vec_u64": HEADER
    + """\
fn total(v: *Vec<u64>) -> u64
    var s: u64 = 0
    for i in 0..v.len
        s = s + vec_get<u64>(v, i)
    return s

fn make() -> Vec<*u8>
    var v: Vec<*u8> = vec_new<*u8>()
    vec_push<*u8>(@v, c"z")
    return v

pub fn main() -> i32
    var v: Vec<u64> = vec_new<u64>()
    vec_push<u64>(@v, 30)
    vec_push<u64>(@v, 12)
    let w: Vec<*u8> = make()
    return (total(@v) + w.len as u64) as i32
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_matches_ritz0(ritz1_bin, tmp_path, name):
    program = PROGRAMS[name]
    expected = _run_pkg("ritz0", tmp_path, name, program)
    assert _run_pkg("ritz1", tmp_path, name, program) == expected


# Spellings of the annotation's type, read straight from ritz1's IR.  These
# pin the mangled names (ritz0's: `ptr_` + pointee) independent of whether
# the program happens to link.
SPELLINGS = {
    "Vec<*u8>": "Vec$ptr_u8",
    "Vec<u64>": "Vec$u64",
    "Vec<*Cell>": "Vec$ptr_Cell",
    "Vec<**u8>": "Vec$ptr_ptr_u8",
    "Vec<*i32>": "Vec$ptr_i32",
}


@pytest.mark.integration
@pytest.mark.parametrize("annot", sorted(SPELLINGS))
def test_annotation_mangles_like_call_site(ritz1_bin, tmp_path, annot):
    arg = annot[len("Vec<") : -1]
    program = (
        HEADER
        + "struct Cell\n    x: i64\n\n"
        + f"fn keep(v: *{annot}) -> i64\n    return v.len\n\n"
        + "pub fn main() -> i32\n"
        + f"    var v: {annot} = vec_new<{arg}>()\n"
        + "    return keep(@v) as i32\n"
    )
    ir = _compile_ritz1(tmp_path, program)
    want = SPELLINGS[annot]
    assert f"%Vec${want[4:]}" in ir or f'%"{want}"' in ir, ir[-3000:]
    # No empty-suffix `%Vec$` type anywhere (the bug's signature).
    assert not re.search(r'%"?Vec\$"?[\s,)*]', ir), "empty generic suffix in IR"
