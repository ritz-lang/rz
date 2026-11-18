#!/usr/bin/env python3
"""A struct value in a scalar field of a struct literal is a located error (AGAST #3424).

`struct S { v: u8 }`, `struct T { id: i32 }`: `S { v: T { id: 1 } }` and the
spelled-out generic `Box2<u8> { v: T { id: 1 } }` made ritz0 die in
`_emit_struct_lit` with a Python TypeError from llvmlite's insertvalue ("Can
only insert i8 at [0] in %S: got %T").  `S { v: true }` was already refused
where it is written.  Now:

- the emitter refuses any initialiser `_convert_type` leaves at another type
  than its field's, located (it refused only an aggregate field's before);
- `--check-types` substitutes a spelled-out literal's type arguments into its
  field types, so `Box2<u8> { v: T { .. } }` is the u8 field's type error, as
  `S { v: T { .. } }` already was.

A spelled-out instance is named mangled (`Box2$u8`), as #3428 names it.

Each row is one path (docs/TESTING.md, "What a ritz0 pytest case costs").
"""

import os
import re
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

pytestmark = [pytest.mark.integration]

RITZ_ROOT = Path(__file__).resolve().parent.parent

# Lines 1-6.
HEAD = "struct T\n    id: i32\nstruct S\n    v: u8\nstruct Box2<X>\n    v: X\n"

# name -> (source after HEAD; the initialiser is on line 8).
SOURCES = {
    "plain": "fn main() -> i32\n    let c = S { v: T { id: 1 } }\n    0\n",
    "spelled_out_generic": "fn main() -> i32\n    let c = Box2<u8> { v: T { id: 1 } }\n    0\n",
}

# (name, --check-types?) -> (line:col, the error)
EXPECTED = {
    ("plain", False): ("8:20", "field `v` of `S` is `u8`, not `T`"),
    ("spelled_out_generic", False): ("8:27", "field `v` of `Box2$u8` is `u8`, not `T`"),
    ("plain", True): ("8:20", "field 'v': expected u8, got T"),
    ("spelled_out_generic", True): ("8:27", "field 'v': expected u8, got T"),
}


def _compile(tmp_path, src, check_types):
    path, ll = tmp_path / "main.ritz", tmp_path / "main.ll"
    path.write_text(src)
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    args = (["--check-types"] if check_types else []) + [str(path), "-o", str(ll)]
    comp = run_ritz0(args, cwd=tmp_path, env=env, timeout=300)
    return comp.returncode, comp.stdout + comp.stderr


@pytest.mark.parametrize("name, check_types", sorted(EXPECTED))
def test_a_struct_in_a_scalar_field_is_located(tmp_path, name, check_types):
    where, message = EXPECTED[(name, check_types)]
    src = HEAD + SOURCES[name]
    code, out = _compile(tmp_path, src, check_types)
    assert code != 0, f"accepted {name}:\n{out}"
    assert "Traceback" not in out, f"{name} crashed:\n{out[-2000:]}"
    found = re.findall(r"main\.ritz:(\d+:\d+): (.*)", out)
    assert (where, message) in found, f"{name}: wanted {where}: {message}:\n{out[-2000:]}"


def test_the_spelled_out_field_still_takes_its_type(tmp_path):
    """Control: substituting the args doesn't refuse a value that fits them."""
    src = HEAD + ("fn main() -> i32\n    let b = Box2<T> { v: T { id: 5 } }\n"
                  "    let u = Box2<u8> { v: 7 }\n    b.v.id + u.v as i32\n")
    code, out = _compile(tmp_path, src, True)
    assert code == 0, out
