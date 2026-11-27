"""AGAST #4625: a procedure has one lowering, `extern fn f()` or `fn f()`.

ritz0 lowered a procedure definition `fn f()` to `i32` with a dummy return
but `extern fn f()` to `void`. A module whose closure holds both (harland's
cycle-breaking externs: nvme.ritz's `extern fn waitq_wake_irq()` beside
proc/waitq.ritz's definition) took the extern's `void` type, and the body's
`ret i32 0` was invalid IR that clang refused ("value doesn't match function
result type 'void'"). #4600 worked around it by giving six harland fns a
dummy `-> i32`.

ritz1 already lowered both to `void`; its test keeps the two agreeing.

AGAST #4652: a procedure spelled `-> void` lowered to `i8` (void's
`_ritz_type_to_llvm`) on both paths, so `extern fn wake() -> void` beside
`fn wake()` (or the reverse) still mismatched. Each test runs over the
spellings: unspelled on both sides, and `-> void` on either one.
"""

import os
import re
import subprocess
from pathlib import Path

import llvmlite.binding as llvm
import pytest
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

pytestmark = pytest.mark.integration

# The defining module imports the one holding the extern, so the extern is
# declared before the definition's body is emitted (waitq.ritz's closure).
WAITQ = """\
import nvme

var g_count: i32 = 0

pub fn wake{def_ret}
    g_count = g_count + 1

pub fn poke()
    irq()
"""

NVME = """\
extern fn wake{ext_ret}

pub fn irq()
    wake()
"""


# A definition with no extern of it in the module's closure.
SOLO = """\
var g_count: i32 = 0

pub fn wake{def_ret}
    g_count = g_count + 1
"""

# (definition's spelling, extern's spelling): the #4625 case, then `-> void`
# on each side. Both spelled is covered by the two: each side lowers alone.
SPELLINGS = [("()", "()"), ("() -> void", "()"), ("()", "() -> void")]
spellings = pytest.mark.parametrize(
    "def_ret,ext_ret", SPELLINGS, ids=["unspelled", "def-void", "extern-void"]
)


def _write(tmp_path, def_ret, ext_ret):
    (tmp_path / "waitq.ritz").write_text(WAITQ.format(def_ret=def_ret))
    (tmp_path / "nvme.ritz").write_text(NVME.format(ext_ret=ext_ret))


def _emit(tmp_path, main, def_ret, ext_ret):
    _write(tmp_path, def_ret, ext_ret)
    ll = tmp_path / f"{main}.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    proc = run_ritz0(
        [str(tmp_path / f"{main}.ritz"), "--no-runtime", "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return ll.read_text()


def _verify(text):
    """Parse and verify the module as clang would: raises on invalid IR."""
    mod = llvm.parse_assembly(text)
    mod.verify()
    return mod


@spellings
def test_definition_beside_extern_is_valid_ir(tmp_path, def_ret, ext_ret):
    """The definition's body, emitted under the extern's declaration, is
    valid IR (it was `define void @wake` holding `ret i32 0`)."""
    _verify(_emit(tmp_path, "waitq", def_ret, ext_ret))


@spellings
@pytest.mark.parametrize("main", ["waitq", "nvme"])
def test_extern_procedure_lowers_as_definition(tmp_path, main, def_ret, ext_ret):
    """Both a module defining `wake` and one only declaring it through the
    extern give it the procedure's `i32 ()` type, so the objects agree."""
    text = _emit(tmp_path, main, def_ret, ext_ret)
    _verify(text)
    sigs = re.findall(r'^(?:declare|define)\b.* (\S+) @"wake"\(', text, re.MULTILINE)
    assert sigs == ["i32"], sigs


@pytest.mark.parametrize("def_ret", ["()", "() -> void"], ids=["unspelled", "void"])
def test_definition_alone_lowers_as_procedure(tmp_path, def_ret):
    """A definition with no extern in its closure is declared by its own
    signature: `fn wake() -> void` is `i32 ()` as `fn wake()` is (#4652),
    not void's `i8`."""
    (tmp_path / "solo.ritz").write_text(SOLO.format(def_ret=def_ret))
    ll = tmp_path / "solo.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    proc = run_ritz0(
        [str(tmp_path / "solo.ritz"), "--no-runtime", "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = ll.read_text()
    _verify(text)
    sigs = re.findall(r'^define\b.* (\S+) @"wake"\(', text, re.MULTILINE)
    assert sigs == ["i32"], sigs


@spellings
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_ritz1_extern_procedure_agrees_with_definition(
    tmp_path, compiler, def_ret, ext_ret
):
    """ritz1 gives `wake` one return type in both modules, and clang accepts
    the module holding both."""
    _write(tmp_path, def_ret, ext_ret)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    rets = []
    for main in ("waitq", "nvme"):
        ll = tmp_path / f"{main}.ll"
        proc = subprocess.run(
            [str(binary), f"{main}.ritz", "-o", str(ll)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        cc = subprocess.run(
            ["clang", "-c", "-x", "ir", str(ll), "-o", os.devnull],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        assert cc.returncode == 0, cc.stderr
        rets += re.findall(
            r'^(?:declare|define)\b.* (\S+) @"?wake"?\(', ll.read_text(), re.MULTILINE
        )
    assert len(rets) == 2 and len(set(rets)) == 1, rets
