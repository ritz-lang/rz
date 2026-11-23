"""AGAST #4490: `.unwrap()` of a move-only Option consumes its carrier.

The free-count row `string_unwrap_moves_carrier` pins the owned binding
(one alloc, one free) on every compiler. These rows pin the refusal: a
borrowed receiver is "cannot move out of a reference", the same words
ritz0 uses. A copy payload, and a temporary receiver, still compile.
"""

import pytest

from test_ref_into_value import _compile

COMPILERS = ["ritz1", "ritz1_selfhosted"]

BORROWED = """\
import ritzlib.option
import ritzlib.string

fn take(o: @Option<String>) -> i32
    let s: String = o.unwrap()
    return s.len() as i32

pub fn main() -> i32
    0
"""

LENT = """\
import ritzlib.option
import ritzlib.string

fn take(o:& Option<String>) -> i32
    let s: String = o.unwrap()
    return s.len() as i32

pub fn main() -> i32
    0
"""

COPY_PAYLOAD = """\
import ritzlib.option

fn take(o: Option<i32>) -> i32
    return o.unwrap()

pub fn main() -> i32
    let o: Option<i32> = Some(3)
    return take(o)
"""

TEMPORARY = """\
import ritzlib.option
import ritzlib.string

fn pick() -> Option<String>
    return Some(string_from("hi"))

fn build() -> i32
    let s: String = pick().unwrap()
    return s.len() as i32

pub fn main() -> i32
    return build()
"""


def _need(request, compiler):
    request.getfixturevalue("ritz1_bin")
    if compiler == "ritz1_selfhosted":
        request.getfixturevalue("ritz1_selfhosted")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("src", [BORROWED, LENT], ids=["shared", "lent"])
def test_borrowed_unwrap_is_refused(request, tmp_path, compiler, src):
    _need(request, compiler)
    comp, ll, _ = _compile(compiler, tmp_path, "unwrap_borrowed", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    assert "cannot move out of a reference" in out, f"{compiler}:\n{out}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("src", [COPY_PAYLOAD, TEMPORARY], ids=["copy", "temporary"])
def test_unwrap_of_a_copy_or_a_temporary_compiles(request, tmp_path, compiler, src):
    _need(request, compiler)
    comp, ll, _ = _compile(compiler, tmp_path, "unwrap_ok", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused it:\n{out}"
