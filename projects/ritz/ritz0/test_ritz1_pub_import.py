"""Regression tests for AGAST #1523 — ritz1 must parse `pub import` (re-export).

ritz1's `import_stmt` rule had no `PUB` alternative, so

    pub import ritzlib.sys

    pub fn main() -> i32
        return 0

failed with "cannot parse item starting at 'pub'" (ritz0: exit 0).  That kept
25 angelo modules, and every module importing them, off ritz1.

Re-export semantics (LANGUAGE_SPEC §15.4): the importer of a module also sees
the pub items of the modules it `pub import`s.  Both compilers already make
an import's names visible transitively, so the chain tests pin the visible
behaviour: a fn declared in `a`, re-exported by `b`, is called from `main`,
which imports only `b`.  The modules are compiled separately and linked, as
build.py does, so the exit code is the value the re-exported fn returned.
"""

import os
import subprocess
from pathlib import Path

import fast_link
import pytest
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


# --- the ticket's repro, verbatim ------------------------------------------

REPRO = """\
pub import ritzlib.sys

pub fn main() -> i32
    return 0
"""

# --- 3-module chain: a declares, b re-exports, main imports only b ---------

MOD_A = "pub fn base_val() -> i32\n    return 7\n"

MAIN = "import b\n\npub fn main() -> i32\n    return base_val() + mid()\n"

# Each shape of the import statement, with `pub` in front (b's source).
# Selective and aliased imports bring in the whole module, as a plain import
# does in both compilers (see the note on `import_stmt` in the grammar).
B_FORMS = {
    "plain": "pub import a\n",
    "alias": "pub import a as aa\n",
    "selective": "pub import a { base_val }\n",
    # After another item: a `pub import` must not end `item*` early.
    "after_item": "const K: i32 = 1\n\npub import a\n",
}

B_TAIL = "\npub fn mid() -> i32\n    return 1\n"


def _compile(compiler: str, cwd: Path, src: Path, ll: Path):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=cwd, env=env, timeout=300)
    cmd = [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(cwd)]
    return subprocess.run(
        cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=300, check=False
    )


def _build_run(compiler: str, tmp_path: Path, modules: dict) -> int:
    """Compile each module separately, link them all, run; return exit code."""
    lls = []
    for name, text in modules.items():
        (tmp_path / f"{name}.ritz").write_text(text)
    for name in modules:
        src = tmp_path / f"{name}.ritz"
        ll = tmp_path / f"{name}.ll"
        comp = _compile(compiler, tmp_path, src, ll)
        assert comp.returncode == 0 and ll.exists(), (
            f"{compiler} failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
        )
        lls.append(ll)
    exe = tmp_path / "prog"
    link_cmd = ["clang", *map(str, lls), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler} IR would not link:\n{link.stderr[-2000:]}"
    return subprocess.run(
        [str(exe)], capture_output=True, timeout=60, check=False
    ).returncode


@pytest.mark.integration
def test_ritz0_repro_oracle(tmp_path):
    assert _build_run("ritz0", tmp_path, {"repro": REPRO}) == 0


@pytest.mark.integration
def test_ritz1_parses_repro(ritz1_bin, tmp_path):
    """AGAST #1523, verbatim. Before the fix: 'cannot parse item starting at pub'."""
    assert _build_run("ritz1", tmp_path, {"repro": REPRO}) == 0


@pytest.mark.integration
def test_ritz0_chain_oracle(tmp_path):
    mods = {"a": MOD_A, "b": B_FORMS["plain"] + B_TAIL, "main": MAIN}
    assert _build_run("ritz0", tmp_path, mods) == 8


@pytest.mark.integration
@pytest.mark.parametrize("form", sorted(B_FORMS))
def test_ritz1_chain_resolves_reexported_fn(ritz1_bin, tmp_path, form):
    """main imports only b; base_val comes from a through b's `pub import`."""
    mods = {"a": MOD_A, "b": B_FORMS[form] + B_TAIL, "main": MAIN}
    assert _build_run("ritz1", tmp_path, mods) == 8
