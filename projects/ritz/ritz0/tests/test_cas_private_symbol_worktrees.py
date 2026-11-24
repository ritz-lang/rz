"""AGAST #4626: the artifact store must not serve one worktree's object to
another when the object's symbols name its worktree.

A private free fn's symbol is `name__<sha256(absolute path)[:8]>` (AGAST
#1858, ritz0 LLVMEmitter._symbol_name / ritz1 fn_symbol), so the object of
`lib/a.ritz` defines `helper__<hash of its path>`. Since #4608 a test
harness that emits `wrap<T>`'s instance declares that same symbol. The
store (~/.cache/ritz/cas, shared by every worktree on a host) keyed modules
by their repo-relative identity and content only, so two worktrees at
different paths shared one key while their objects named different symbols.

When the harness missed the store (its file changed) but `lib/a.ritz`'s
object hit, the harness declared `helper__<this worktree>` and linked
against an object defining `helper__<other worktree>`: lexis's
test_tree_builder_start_tag failed with "undefined reference to
tag_is_p__72f14a7b" in one room's worktree and passed in fresh ones.

    wt1/lib/a.ritz, wt1/t.ritz    built first: fills the shared store
    wt2/lib/a.ritz (same bytes),  wt2/t.ritz (one comment more: the
    harness misses, lib/a.ritz's object would hit)

The fix has two halves, one test each:
* the symbol hashes the path relative to the file's checkout (the nearest
  directory holding `.git`), so worktrees of one repository agree and keep
  sharing the store (test_private_symbol_is_relative_to_its_checkout);
* a file outside any checkout (its store identity is `ext/<name>`) keeps
  its absolute path in the symbol, so that path joins the store key
  (test_second_worktree_links_against_its_own_private_symbols: tmp dirs).
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

LIB_A = """\
fn helper(x: i32) -> i32
    x + 1

pub fn wrap<T>(v: T, x: i32) -> i32
    helper(x)
"""

TEST_FILE = """\
import lib.a { wrap }

[[test]]
fn test_wrap() -> i32
    assert wrap<i64>(5, 41) == 42
    0
"""


def _worktree(root: Path, test_src: str) -> Path:
    (root / "lib").mkdir(parents=True)
    (root / "lib" / "a.ritz").write_text(LIB_A)
    src = root / "t.ritz"
    src.write_text(test_src)
    return src


def _build_and_run(test_runner, src: Path, compiler: str, monkeypatch) -> None:
    wt = src.parent
    monkeypatch.setenv("RITZ_PATH", f"{wt}:{RITZ_ROOT}")
    scratch = wt / "scratch"
    scratch.mkdir()
    exe, error = test_runner.build_test_binary(str(src), str(scratch), compiler)
    assert error is None, f"{compiler} in {wt.name}: {error}"
    run = subprocess.run([exe, *test_runner.runner_args()],
                         capture_output=True, timeout=60)
    status = {t["name"]: t["status"] for t in json.loads(run.stdout)["tests"]}
    assert run.returncode == 0 and status == {"test_wrap": "pass"}, run


@pytest.mark.parametrize("compiler", COMPILERS)
def test_second_worktree_links_against_its_own_private_symbols(
        compiler, tmp_path, monkeypatch):
    if compiler != "ritz0":
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert (RITZ1_BUILD / compiler).exists(), \
            f"{compiler} missing; run `make -C ritz1 bootstrap`"
    sys.path.insert(0, str(RITZ_ROOT / "ritz0"))
    import test_runner

    # One store for both worktrees, as on a host; empty at the start.
    monkeypatch.setenv("RITZ_CACHE_DIR", str(tmp_path / "cas"))
    monkeypatch.delenv("RITZ_NO_CAS", raising=False)
    wt1 = _worktree(tmp_path / "wt1", TEST_FILE)
    wt2 = _worktree(tmp_path / "wt2", "# a second worktree\n" + TEST_FILE)
    _build_and_run(test_runner, wt1, compiler, monkeypatch)
    _build_and_run(test_runner, wt2, compiler, monkeypatch)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_two_checkouts_share_the_store_and_link(compiler, tmp_path, monkeypatch):
    """One package built from two checkout paths over one store, as two gate
    trees (`.trees/ritz-gate-train-N`) on one host do: the second checkout's
    harness misses, `lib/a.ritz`'s object hits, and the binary links.

    Each `wtN` stands for the repository (cas.REPO_ROOT points at it while
    it builds), so `lib/a.ritz` has the same repository-relative identity,
    and therefore the same store key, in both. Train 1 failed this way:
    tempest-tab's harness declared `tag_is_p__7628e583` against a lexis
    object cached from another gate tree.
    """
    if compiler != "ritz0":
        assert (RITZ1_BUILD / compiler).exists(), \
            f"{compiler} missing; run `make -C ritz1 bootstrap`"
    sys.path.insert(0, str(RITZ_ROOT / "ritz0"))
    import test_runner
    cas = test_runner._build_module().cas

    store = tmp_path / "cas"
    monkeypatch.setenv("RITZ_CACHE_DIR", str(store))
    monkeypatch.delenv("RITZ_NO_CAS", raising=False)
    srcs = [_worktree(tmp_path / "wt1", TEST_FILE),
            _worktree(tmp_path / "wt2", "# a second checkout\n" + TEST_FILE)]
    objects = []
    for src in srcs:
        (src.parent / ".git").write_text("gitdir: /nowhere\n")
        monkeypatch.setattr(cas, "REPO_ROOT", src.parent)
        _build_and_run(test_runner, src, compiler, monkeypatch)
        objects.append(set(store.rglob("*.o")))
    # Only the second harness is new: lib/a.ritz's object was served.
    assert len(objects[1] - objects[0]) == 1, sorted(objects[1] - objects[0])


def _helper_symbol(compiler: str, wt: Path) -> str:
    """The symbol `wt/lib/a.ritz`'s `--no-runtime` object defines for `helper`."""
    src, out = wt / "lib" / "a.ritz", wt / "a.ll"
    env = dict(os.environ, RITZ_PATH=f"{wt}:{RITZ_ROOT}")
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(out), "--no-runtime"],
                         cwd=wt, env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(out)], cwd=wt, env=env,
                              capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    names = re.findall(r"^define [^@]*@\"?(helper__[0-9a-f]{8})", out.read_text(), re.M)
    assert len(names) == 1, out.read_text()
    return names[0]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_private_symbol_is_relative_to_its_checkout(compiler, tmp_path):
    """Two checkouts (a `.git`, as a worktree has) name a file's private fn
    alike, so the store's repository-relative key is enough for them; two
    plain directories still do not, which is why their path joins the key."""
    for name in ("wt1", "wt2", "plain1", "plain2"):
        _worktree(tmp_path / name, TEST_FILE)
    for name in ("wt1", "wt2"):
        (tmp_path / name / ".git").write_text("gitdir: /nowhere\n")
    assert _helper_symbol(compiler, tmp_path / "wt1") == _helper_symbol(compiler, tmp_path / "wt2")
    assert (_helper_symbol(compiler, tmp_path / "plain1")
            != _helper_symbol(compiler, tmp_path / "plain2"))
