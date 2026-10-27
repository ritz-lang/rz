"""AGAST #1902: a method with its own type parameters is a located error.

`impl Box` / `fn conv<T>(self: *Box, x: T) -> T` was accepted by every
compiler and compiled wrong by all of them:

* ritz1 emitted `call %T @Box_conv(...)` and `declare %T @Box_conv(...)`,
  with `T` unsubstituted and no `Box_conv$i32` instance (fail-open, #1369
  class): monomorph only specialises free generic fns and the methods of
  generic impls, never a method's own type params;
* ritz0, the oracle, crashed on `b.conv<i32>(3)` ("Unknown field 'conv'")
  and, for `b.conv(300)`, erased `T` to `i8` and returned 300 mod 256 = 44.

Nothing in the tree declares such a method and LANGUAGE_SPEC does not
specify them, so both compilers reject the declaration, at the method, and
ask for a free generic fn instead. A generic impl's methods may still use the
impl's own parameters (`impl<T> W<T>` / `fn get(self: *W<T>) -> T`); only a
`<...>` on the method itself is refused.

The rejection is a parse-time check on the declaration (ritz0 parser.py
parse_impl, ritz1 ast_helpers impl_block_new), so an unused generic method
and one in an imported module are refused too: an import's interface would
otherwise carry a method no importer can instantiate.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
NEEDLE = "generic methods are not supported"

pytestmark = pytest.mark.integration


def _compile(compiler, tmp_path, files, main="t"):
    for name, src in files.items():
        (tmp_path / f"{name}.ritz").write_text(src)
    path = tmp_path / f"{main}.ritz"
    ll = tmp_path / f"{main}.ll"
    if ll.exists():
        ll.unlink()
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300), ll
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    proc = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc, ll


def _assert_rejected_at(compiler, tmp_path, files, where, method, main="t"):
    proc, ll = _compile(compiler, tmp_path, files, main)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted a generic method:\n{out}"
    assert NEEDLE in out, f"{compiler}: rejected, but not for the generic method:\n{out}"
    assert re.search(rf"{re.escape(where)}\b", out), (
        f"{compiler}: error not located at {where}:\n{out}")
    assert f"'{method}'" in out, f"{compiler}: error does not name '{method}':\n{out}"


def _run(compiler, tmp_path, src):
    proc, ll = _compile(compiler, tmp_path, {"t": src})
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"{compiler} rejected a control:\n{out}"
    assert NEEDLE not in out
    exe = tmp_path / f"t_{compiler}"
    link_cmd = ["clang", "-Wno-override-module", str(ll), "-o", str(exe), "-nostdlib", "-no-pie"]
    if compiler != "ritz0":
        link_cmd.insert(1, str(RITZ_START))
    link = subprocess.run(link_cmd, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler} IR did not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


BOX = """\
struct Box
    v: i64

impl Box
    fn conv<T>(self: *Box, x: T) -> T
        x
"""

# The #1902 repro: an explicit type argument at the call.
EXPLICIT_CALL = BOX + """
fn main() -> i32
    let b: Box = Box { v: 1 }
    let r: i32 = b.conv<i32>(3)
    r - 3
"""

# ritz0's silent truncation: T inferred from the argument.
INFERRED_CALL = BOX + """
fn main() -> i32
    let b: Box = Box { v: 1 }
    let r: i32 = b.conv(300)
    r - 300
"""

# The declaration is the error, used or not.
UNUSED = BOX + """
fn main() -> i32
    0
"""

# A method's own parameter on a generic impl is refused too.
GENERIC_IMPL = """\
struct W<T>
    v: T

impl<T> W<T>
    fn get(self: *W<T>) -> T
        self.v

    fn map<U>(self: *W<T>, u: U) -> U
        u

fn main() -> i32
    let w: W<i32> = W<i32> { v: 0 }
    w.get()
"""

# A `pub fn` method, the shape #1899's strip_to_interface had to special-case.
PUB_METHOD = BOX.replace("    fn conv<T>", "    pub fn conv<T>") + """
fn main() -> i32
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("src", [EXPLICIT_CALL, INFERRED_CALL, UNUSED, PUB_METHOD],
                         ids=["explicit_call", "inferred_call", "unused", "pub_method"])
def test_generic_method_in_plain_impl_is_located_error(compiler, tmp_path, src):
    _assert_rejected_at(compiler, tmp_path, {"t": src}, "t.ritz:5", "conv")


@pytest.mark.parametrize("compiler", COMPILERS)
def test_method_type_params_on_generic_impl_rejected(compiler, tmp_path):
    _assert_rejected_at(compiler, tmp_path, {"t": GENERIC_IMPL}, "t.ritz:8", "map")


LIB = """\
pub struct Box
    v: i64

impl Box
    pub fn get(self: *Box) -> i64
        self.v

    pub fn conv<T>(self: *Box, x: T) -> T
        x
"""

MAIN = """\
import lib1902

fn main() -> i32
    let b: Box = Box { v: 1 }
    let r: i32 = b.conv<i32>(3)
    r - 3
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_generic_method_in_imported_module_located_in_that_module(compiler, tmp_path):
    """The ticket's cross-module repro; the error points into the import."""
    _assert_rejected_at(compiler, tmp_path, {"lib1902": LIB, "t": MAIN},
                        "lib1902.ritz:8", "conv")


# Controls: without them, rejecting every impl, or every generic, passes.
CONTROL = """\
struct Box
    v: i64

impl Box
    fn get(self: *Box) -> i64
        self.v

struct W<T>
    v: T

impl<T> W<T>
    fn get(self: *W<T>) -> T
        self.v

fn conv<T>(b: *Box, x: T) -> T
    x

fn main() -> i32
    let b: Box = Box { v: 7 }
    let w: W<i64> = W<i64> { v: 30 }
    let r: i64 = conv<i64>(@b, 300)
    (b.get() + w.get() + r - 337) as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_impl_methods_and_free_generic_fn_still_compile_and_run(compiler, tmp_path):
    assert _run(compiler, tmp_path, CONTROL) == 0
