"""AGAST #3585: an imported `[[inline]]` / `[[always_inline]]` fn inlines
across modules without LTO, on every compiler.

build.py compiles each module on its own, so an importer used to see only a
`declare` of an imported fn and -O2 had no body to inline: ritzlib/net.ritz
called `syscall3` (ritzlib.sys, AGAST #3397) 40-odd times instead of holding
the bare `syscall`.  Now an imported inline fn is *defined* in the importer
as `available_externally`: -O2 may inline it, and the importer never emits
a symbol for it (the defining module still does).

Only a self-contained fn qualifies (module_interface.inline_import_eligible,
ritz1's fn_inline_import): `pub`, not generic, not async, and a body naming
nothing but its params and its own locals -- no call, no module var, no
const.  Inlined, any other name could be one private to the defining module,
which the importer cannot link to.  The rest stay a `declare`.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

needs_clang = pytest.mark.skipif(shutil.which("clang") is None, reason="clang not on PATH")

# `leaf` qualifies; each of the others is refused for its own reason.
A_SRC = """\
[[inline]]
pub fn leaf(x: i64) -> i64
    var r: i64 = x
    if r > 100
        return 0
    r = r * 3 + 1
    return r

[[always_inline]]
pub fn leaf_always(x: i64) -> i64
    x - 1

[[inline]]
pub fn calls(x: i64) -> i64
    return helper(x)

fn helper(x: i64) -> i64
    x + 1

var g: i64 = 5

[[inline]]
pub fn uses_global(x: i64) -> i64
    return x + g

const K: i64 = 7

[[inline]]
pub fn uses_const(x: i64) -> i64
    return x + K

pub fn plain(x: i64) -> i64
    x * 2
"""

# leaf(4) 13 + leaf_always(3) 2 + calls(1) 2 + uses_global(1) 6
# + uses_const(1) 8 + plain(1) 2 = 33
MAIN_SRC = """\
import a

pub fn main() -> i32
    let n: i64 = leaf(4) + leaf_always(3) + calls(1) + uses_global(1) + uses_const(1) + plain(1)
    n as i32
"""

EXIT = 33


def _env(tmp_path: Path) -> dict:
    # A store of its own: no interface text stored by another run is read.
    return dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}",
                RITZ_CACHE_DIR=str(tmp_path / "cas"))


def _compile(request, compiler: str, src: Path, tmp_path: Path) -> Path:
    """`src` compiled by `compiler` (no runtime) to `<stem>.<compiler>.ll`."""
    ll = tmp_path / f"{src.stem}.{compiler}.ll"
    env = _env(tmp_path)
    if compiler == "ritz0":
        proc = run_ritz0(["--no-runtime", str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                         timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300, check=False)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]
    return ll


def _o2(ll: Path) -> str:
    opt = ll.with_suffix(".o2.ll")
    clang = subprocess.run(["clang", "-w", "-O2", "-S", "-emit-llvm", "-x", "ir", str(ll),
                            "-o", str(opt)], capture_output=True, text=True, timeout=300, check=False)
    assert clang.returncode == 0, clang.stderr[-2000:]
    return opt.read_text()


def _linkage(ir_text: str, name: str) -> str:
    """How `ir_text` has @name: 'declare', 'define <linkage>' or 'absent'."""
    m = re.search(rf'^(declare|define)\b([^@\n]*)@"?{re.escape(name)}"?\(', ir_text, re.MULTILINE)
    if not m:
        return "absent"
    if m.group(1) == "declare":
        return "declare"
    words = [w for w in m.group(2).split()
             if w in ("available_externally", "internal", "linkonce_odr", "weak_odr")]
    return " ".join(["define"] + words)


@needs_clang
@pytest.mark.parametrize("compiler", COMPILERS)
def test_net_inlines_its_syscalls_at_o2(request, tmp_path, compiler):
    """The ticket's case: ritzlib/net.ritz calls syscallN from ritzlib.sys."""
    ir_text = _o2(_compile(request, compiler, RITZ_ROOT / "ritzlib" / "net.ritz", tmp_path))
    calls = re.findall(r'call i64 @"?syscall\d"?\(', ir_text)
    assert calls == [], f"{len(calls)} calls to syscallN left in net.ritz at -O2"
    assert 'asm sideeffect "syscall"' in ir_text
    # Inlined everywhere, so no body is left either: available_externally
    # definitions are dropped once optimised.
    assert not re.search(r'^define[^\n]*@"?syscall\d"?\(', ir_text, re.MULTILINE)


@needs_clang
@pytest.mark.parametrize("compiler", COMPILERS)
def test_only_a_self_contained_inline_fn_is_defined_in_the_importer(request, tmp_path,
                                                                    compiler):
    (tmp_path / "a.ritz").write_text(A_SRC)
    (tmp_path / "main.ritz").write_text(MAIN_SRC)
    main_ll = _compile(request, compiler, tmp_path / "main.ritz", tmp_path)
    ir_text = main_ll.read_text()
    got = {name: _linkage(ir_text, name)
           for name in ("leaf", "leaf_always", "calls", "uses_global", "uses_const",
                        "plain")}
    assert got == {
        "leaf": "define available_externally",
        "leaf_always": "define available_externally",
        "calls": "declare",
        "uses_global": "declare",
        "uses_const": "declare",
        "plain": "declare",
    }, ir_text[-4000:]

    # The program links and runs at -O0 (the bodies dropped, a.ritz's symbols
    # called) and at -O2 (leaf inlined, nothing private to a.ritz named).
    a_ll = _compile(request, compiler, tmp_path / "a.ritz", tmp_path)
    for opt in ("-O0", "-O2"):
        exe = tmp_path / f"prog{opt}"
        link = fast_link.clang(["clang", "-w", opt, str(main_ll), str(a_ll), str(RITZ_START),
                                "-o", str(exe), "-nostdlib"],
                               capture_output=True, text=True, timeout=300, check=False)
        assert link.returncode == 0, link.stderr[-2000:]
        run = subprocess.run([str(exe)], capture_output=True, timeout=60, check=False)
        assert run.returncode == EXIT, (opt, run.returncode)
