"""AGAST #201: an ODR definition (`linkonce_odr` / `weak_odr`) is in a comdat.

A monomorph was defined `linkonce_odr` in every object that instantiates it
(ritz0 is_monomorphized, ritz1 fn_linkage), and the linker was meant to keep
one copy.  Since AGAST #4609 each object's copy is `internal`: two types of
one name in one program (LANGUAGE_SPEC §15.3) each have a `pick$Box`, and one
kept copy served both.  The UEFI link below still holds both objects' copies.  On ELF it does: a linkonce definition is a weak symbol.  On COFF
(a `*-uefi` [[bin]] compiles for x86_64-windows-gnu) a definition without a
comdat lowers to a plain weak external, and lld-link refuses two of them:

    lld-link: error: duplicate symbol: vec_push$u8

harland's hwinv hit this when ritzlib.io and ritzlib.string both came to
instantiate `Vec<u8>`.  Clang puts every C++ inline/template definition in a
same-named `comdat any` for this reason, on every target; both compilers now
do the same for every ODR function.  Globals do not get one: their comdat
groups would match by name across unrelated modules (see the last test).

    # g.ritz                 # a.ritz               # b.ritz
    pub fn ident<T>(v: T)    pub fn a_val() -> i64  pub fn b_val() -> i64
        -> T                     ident<i64>(20)         ident<i64>(22)
        v

Each of a.o and b.o defines `ident$i64`; the UEFI link must accept both.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from test_ref_into_value import COMPILERS

pytestmark = [pytest.mark.xdist_group("tree"), pytest.mark.integration]

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BINS = {
    "ritz1": RITZ_ROOT / "ritz1" / "build" / "ritz1",
    "ritz1_selfhosted": RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted",
}

sys.path.insert(0, str(RITZ_ROOT))
from build_pipeline import find_llvm_tool

G = """\
pub fn ident<T>(v: T) -> T
    v
"""

A = """\
import g

pub fn a_val() -> i64
    ident<i64>(20)
"""

B = """\
import g

pub fn b_val() -> i64
    ident<i64>(22)
"""

MAIN = """\
import a
import b

pub fn efi_main(image: u64, table: *u8) -> u64
    (a_val() + b_val()) as u64
"""


def _build_uefi(pkg: Path, compiler: str) -> subprocess.CompletedProcess:
    src = pkg / "src"
    src.mkdir(parents=True)
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "odr"\nversion = "0.1.0"\n\n'
        '[[bin]]\nname = "odr"\nentry = "main::efi_main"\n'
        'target = "x86_64-unknown-uefi"\nfreestanding = true\n'
        'sources = ["src"]\n')
    for name, text in (("g", G), ("a", A), ("b", B), ("main", MAIN)):
        (src / f"{name}.ritz").write_text(text)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        ["python3", str(RITZ_ROOT / "build.py"), "build", str(pkg), "--no-cache",
         "--compiler", compiler],
        cwd=pkg, env=env, capture_output=True, text=True, timeout=600, check=False)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_monomorph_in_two_objects_links_for_uefi(tmp_path, compiler):
    if find_llvm_tool("lld-link") is None:
        pytest.skip("lld-link not installed (the build reports it as a setup miss)")
    proc = _build_uefi(tmp_path / "pkg", compiler)
    out = proc.stdout + proc.stderr
    assert "duplicate symbol" not in out, out[-3000:]
    assert proc.returncode == 0, out[-3000:]


def _emit_ir(compiler: str, src: Path, out: Path) -> str:
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ_ROOT / "ritz0" / "ritz0.py"), "--no-runtime",
               str(src), "-o", str(out)]
    else:
        cmd = [str(RITZ1_BINS[compiler]), str(src), "-o", str(out)]
    proc = subprocess.run(cmd, cwd=out.parent, env=env, capture_output=True,
                          text=True, timeout=600, check=False)
    assert proc.returncode == 0 and out.exists(), proc.stdout[-2000:] + proc.stderr[-2000:]
    return out.read_text()


_ODR_DEFINE = re.compile(
    r'^define (?:linkonce_odr|weak_odr) [^\n]*?@("[^"]+"|[-\w.$]+)\(([^\n]*)$', re.MULTILINE)
_ODR_GLOBAL = re.compile(r'^@("[^"]+"|[-\w.$]+) = (?:linkonce_odr|weak_odr) ([^\n]*)$', re.MULTILINE)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_odr_definition_has_its_comdat(tmp_path, compiler):
    """ritzlib.string instantiates Vec<u8>: its object carries its own,
    internal copies (AGAST #4609); any ODR function left (a generated
    `E.from`) is in its comdat.

    Functions only.  A comdat group is matched by name across objects, and
    globals of unrelated modules share names (`g_out`, every test file's
    capture buffer); the ritzunit runner localizes its own copy, so a test's
    group was discarded and its references bound to nothing (`@g_out[0]`
    became 0 -- every capture test SIGSEGVd).  Globals stay `weak_odr`.
    """
    ir = _emit_ir(compiler, RITZ_ROOT / "ritzlib" / "string.ritz", tmp_path / "string.ll")
    comdats = set(re.findall(r'^\$("[^"]+"|[-\w.$]+) = comdat any$', ir, re.MULTILINE))
    defines = _ODR_DEFINE.findall(ir)
    assert re.search(r'^define internal [^\n]*@"?Vec\$u8_push"?\(', ir, re.MULTILINE), \
        "expected ritzlib.string's own internal Vec$u8_push"
    for name, rest in defines:
        assert re.search(r'\bcomdat\b', rest), f"@{name} has no comdat: {rest[:200]}"
        assert name in comdats, f"no `${name} = comdat any` for @{name}"
    globals_ = _ODR_GLOBAL.findall(ir)
    if compiler != "ritz0":
        # ritz0 declares module globals `external` here; ritz1 defines them
        # `weak_odr` in every module, which is what made the group collision.
        assert globals_, "expected weak_odr globals in ritzlib.string"
    for name, rest in globals_:
        assert not rest.endswith(", comdat"), f"global @{name} is in a comdat: {rest[-200:]}"
