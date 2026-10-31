"""AGAST #1968: a generic fn called without type args is a clear error.

LANGUAGE_SPEC section 4.4: "Generic calls need their type argument spelled
out". Neither compiler infers a generic fn's type args from its arguments.
ritz0 nevertheless reported `vec_as_ptr(d)` as "Unknown function:
vec_as_ptr", which reads like a missing import. #1968 took that to be a
failure to infer T through a `@Vec<u8>` param, but it fails the same way on
a local `@v`.

ritz0 now names the generic fn and the spelled-out form. The check sits on
the path that already raised "Unknown function", so nothing that compiled
before is affected. The spelled-out calls on ref params are pinned across
all three compilers by test/test_diff_ref_vec_explicit_generic.ritz.
"""

import os
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.integration


def _compile(tmp_path, src):
    path = tmp_path / "t.ritz"
    path.write_text(src)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return run_ritz0([str(path), "-o", str(tmp_path / "t.ll")],
                     cwd=tmp_path, env=env, timeout=300)


REF_PARAM = """\
import ritzlib.gvec

fn f(d: @Vec<u8>) -> i64
    let p = vec_get_ptr(d, 0)
    return d.len() as i64

pub fn main() -> i32
    var v = vec_new<u8>()
    v.push(65 as u8)
    return f(@v) as i32
"""

LOCAL = """\
import ritzlib.gvec

pub fn main() -> i32
    var v = vec_new<u8>()
    v.push(65 as u8)
    let p = vec_as_ptr(@v)
    return 0
"""

USER_GENERIC = """\
fn ident<T>(x: T) -> T
    x

pub fn main() -> i32
    return ident(3) as i32
"""


@pytest.mark.parametrize("src,fname", [
    (REF_PARAM, "vec_get_ptr"),
    (LOCAL, "vec_as_ptr"),
    (USER_GENERIC, "ident"),
], ids=["ref_param", "local", "user_generic"])
def test_generic_call_without_type_args_names_the_fix(tmp_path, src, fname):
    proc = _compile(tmp_path, src)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out
    assert f"generic function `{fname}` needs explicit type arguments" in out, out
    assert f"`{fname}<T>(...)`" in out, out
    assert "Unknown function" not in out, out


def test_unknown_non_generic_fn_still_unknown(tmp_path):
    proc = _compile(tmp_path, "pub fn main() -> i32\n    return nope(1)\n")
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out
    assert "Unknown function: nope" in out, out
