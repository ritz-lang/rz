"""ritz0's sig cache must be keyed by the ritz0 that wrote it (AGAST #3086).

Background
----------
ritz0 keeps a per-source sig file (``emitter.fn_cache.sig_path_for``). Its
"Skipped X (unchanged)" fast path in ``ritz0.compile_file`` reuses the
existing ``.ll`` when the sig's source hash, import hashes, import misses and
output entry (#1674, #2030, #2020) all still match. None of those say which
ritz0 wrote the sig. So after editing ritz0, recompiling an unchanged
``.ritz`` kept the old compiler's IR: #1891's mutation check of the emitter
passed 16/16 against a mutant that a fresh ``RITZ_CACHE_DIR`` failed 3/16.

The fix records ``compiler_hash`` (a hash of ritz0's own ``.py`` sources,
computed once per process like ``cache.compute_compiler_hash`` for build.py,
#1382) in every sig, and ``read_current_sig`` treats a sig from any other
ritz0 as absent. ritz1 has the same rule for its binary (#1279,
``test_fn_cache_compiler_identity.py``).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RITZ0_DIR))

from emitter import fn_cache
from emitter.fn_cache import (
    build_sig_data,
    hash_ritz0_sources,
    read_current_sig,
    write_sig_file,
)

# ---------------------------------------------------------------------------
# The fingerprint itself
# ---------------------------------------------------------------------------

def _stub_tree(root: Path) -> Path:
    (root / "emitter").mkdir(parents=True)
    (root / "ritz0.py").write_text("print('main')\n")
    (root / "emitter" / "fn_cache.py").write_text("X = 1\n")
    return root


@pytest.mark.unit
class TestFingerprint:
    def test_stable_for_an_unchanged_tree(self, tmp_path):
        root = _stub_tree(tmp_path / "r")
        assert hash_ritz0_sources(root) == hash_ritz0_sources(root)

    def test_changes_when_a_nested_source_changes(self, tmp_path):
        """An edit to any codegen file, in any subdirectory, is a new ritz0."""
        root = _stub_tree(tmp_path / "r")
        before = hash_ritz0_sources(root)
        (root / "emitter" / "fn_cache.py").write_text("X = 2\n")
        assert hash_ritz0_sources(root) != before

    def test_changes_when_a_source_is_added(self, tmp_path):
        root = _stub_tree(tmp_path / "r")
        before = hash_ritz0_sources(root)
        (root / "new_rules.py").write_text("")
        assert hash_ritz0_sources(root) != before

    def test_ignores_tests_and_bytecode(self, tmp_path):
        """Editing a test must not invalidate every sig (same rule as cache.py)."""
        root = _stub_tree(tmp_path / "r")
        before = hash_ritz0_sources(root)
        (root / "test_something.py").write_text("assert True\n")
        (root / "__pycache__").mkdir()
        (root / "__pycache__" / "ritz0.cpython-312.pyc").write_bytes(b"\0")
        (root / "test").mkdir()
        (root / "test" / "helper.py").write_text("")
        assert hash_ritz0_sources(root) == before

    def test_process_fingerprint_is_this_tree(self):
        """COMPILER_HASH is ritz0's own tree, computed once at import."""
        assert fn_cache.COMPILER_HASH == hash_ritz0_sources(RITZ0_DIR)


# ---------------------------------------------------------------------------
# The sig records it; a mismatch is a miss
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSigIdentity:
    @pytest.fixture
    def src(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RITZ_CACHE_DIR", str(tmp_path / "cache"))
        s = tmp_path / "a.ritz"
        s.write_text("fn main() -> i32\n    0\n")
        return str(s)

    def test_sig_records_compiler_hash(self):
        assert build_sig_data("x", {})["compiler_hash"] == fn_cache.COMPILER_HASH

    def test_matching_compiler_reads_the_sig(self, src):
        """Control: a sig this ritz0 wrote is used."""
        write_sig_file(src, build_sig_data("x", {}))
        assert read_current_sig(src) is not None

    def test_other_compiler_is_a_miss(self, src):
        data = build_sig_data("x", {})
        data["compiler_hash"] = "0" * 64
        write_sig_file(src, data)
        assert read_current_sig(src) is None

    def test_sig_without_compiler_hash_is_a_miss(self, src):
        """Sigs written before #3086 vouch for an unknown ritz0."""
        data = build_sig_data("x", {})
        del data["compiler_hash"]
        write_sig_file(src, data)
        assert read_current_sig(src) is None


# ---------------------------------------------------------------------------
# End to end: edit a copy of ritz0, recompile an unchanged source
# ---------------------------------------------------------------------------

def _run(ritz0_py: Path, src: Path, out: Path, env) -> str:
    # A real interpreter per compile: the copy of ritz0 is the compiler under
    # test, so it can't come from ritz0_inproc's preloaded forkserver.
    r = subprocess.run([sys.executable, str(ritz0_py), str(src), "-o", str(out)],
                       cwd=str(src.parent), env=env, capture_output=True, check=False,
                       text=True, timeout=120)
    assert r.returncode == 0, f"compile failed:\n{r.stdout}\n{r.stderr}"
    return r.stdout


@pytest.mark.integration
def test_edited_ritz0_recompiles_an_unchanged_source(tmp_path):
    """#1891's repro: a warm compile after editing ritz0 must not say Skipped.

    Also the controls either side of it: warm with the same ritz0 skips, and
    the edited ritz0's own warm rebuild skips again. And a second output the
    old ritz0 wrote (`b.ll`) must not ride along into the new ritz0's sig when
    `a.ll` is rebuilt first (the sig's `outputs` carry-over, #2020).
    """
    copy = tmp_path / "ritz" / "ritz0"
    shutil.copytree(RITZ0_DIR, copy, ignore=shutil.ignore_patterns(
        "test_*", "test", "__pycache__", ".pytest_cache"))
    # ritz0 imports the artifact store from beside its own tree.
    (copy.parent / "cas.py").symlink_to(RITZ0_DIR.parent / "cas.py")
    src = tmp_path / "a.ritz"
    src.write_text("fn main() -> i32\n    0\n")
    out = tmp_path / "a.ll"
    env = dict(os.environ, RITZ_CACHE_DIR=str(tmp_path / "cache"))
    ritz0_py = copy / "ritz0.py"

    out_b = tmp_path / "b.ll"

    assert "Compiled" in _run(ritz0_py, src, out, env)
    assert "Compiled" in _run(ritz0_py, src, out_b, env)
    assert "Skipped" in _run(ritz0_py, src, out, env)  # warm hit control

    with open(copy / "emitter_llvmlite.py", "a") as f:
        f.write("\n# a different ritz0\n")
    stdout = _run(ritz0_py, src, out, env)
    assert "Skipped" not in stdout and "Compiled" in stdout
    stdout = _run(ritz0_py, src, out_b, env)
    assert "Skipped" not in stdout and "Compiled" in stdout

    assert "Skipped" in _run(ritz0_py, src, out, env)  # the new ritz0's own sig
