#!/usr/bin/env python3
"""ritz1's module-IR fast path must honour imports; sigs live per compiler (AGAST #1807).

Two defects, one cache.

1. Stale IR (correctness).  ``check_source_unchanged`` in
   ``ritz1/src/fn_cache.ritz`` reused a module's IR when its OWN source hash
   and the compiler matched — and never looked at its imports.  A module's
   ``.ll`` bakes in every imported struct layout (field offsets, GEP indices),
   constant and signature, so changing a struct in ``b.ritz`` left ``a.ll``
   reading fields at their old offsets.  ritz0 fixed the same hole in #1674
   (``import_hashes``); ritz1 never caught up.

2. Shared sig path (performance/design, #1280).  ritz0, ritz1 and
   ritz1_selfhosted all wrote ``<src>.ritz.sig`` beside the source, with
   different schemas, so every compiler boundary in a gate evicted the
   others' entries.  Sigs now live in ``<cache root>/<compiler>/<realpath>.sig``
   (see ``emitter.fn_cache.sig_path_for``).

Each test sets ``RITZ_CACHE_DIR`` to its own directory, so the cache is
isolated per test and the expected sig location is computable.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
RITZ1 = RITZ_ROOT / "ritz1" / "build" / "ritz1"
sys.path.insert(0, str(RITZ0_DIR))

from emitter.fn_cache import sig_path_for  # noqa: E402

SKIPPED = "Skipped (unchanged)"


@pytest.fixture(scope="module", autouse=True)
def _ritz1_built(ritz1_bin):
    """Every test here needs an up-to-date ritz1: conftest's session build (#1804)."""


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """A private sig cache for this test; returned so tests can inspect it."""
    d = tmp_path / "sigcache"
    monkeypatch.setenv("RITZ_CACHE_DIR", str(d))
    return d


def _env(**extra) -> dict:
    env = dict(os.environ)
    env.pop("RITZ_PATH", None)
    env.update(extra)
    return env


def _ritz1(src: Path, out: Path, *extra, env=None) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [str(RITZ1), str(src), "-o", str(out), *extra],
        capture_output=True, text=True, cwd=str(src.parent), env=env or _env(),
        timeout=300,
    )
    assert proc.returncode == 0, f"ritz1 failed:\n{proc.stdout}\n{proc.stderr}"
    return proc


def _ritz0(src: Path, out: Path) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [sys.executable, str(RITZ0_DIR / "ritz0.py"), str(src), "-o", str(out)],
        capture_output=True, text=True, cwd=str(src.parent), env=_env(), timeout=300,
    )
    assert proc.returncode == 0, f"ritz0 failed:\n{proc.stdout}\n{proc.stderr}"
    return proc


def _cold_ir(src: Path, tmp: Path) -> str:
    """What ritz1 emits for `src` with no cache at all — the ground truth."""
    out = tmp / "cold.ll"
    _ritz1(src, out, env=_env(RITZ_CACHE_DIR=str(tmp / "cold-cache")))
    return out.read_text()


# `a` reads Rec.b, whose offset depends on the type of Rec.a — declared in b.
REC_I32 = "pub struct Rec\n    a: i32\n    b: i32\n"
REC_I64 = "pub struct Rec\n    a: i64\n    b: i32\n"
A_SRC = (
    "import b\n\n"
    "fn get_b(r: *Rec) -> i32\n"
    "    r.b\n\n"
    "fn main() -> i32\n"
    "    0\n"
)


@pytest.fixture
def two_modules(tmp_path, cache_dir):
    """a imports b; a is compiled once with ritz1 so the cache is warm."""
    proj = tmp_path / "proj"
    proj.mkdir()
    b = proj / "b.ritz"
    b.write_text(REC_I32)
    a = proj / "a.ritz"
    a.write_text(A_SRC)
    out = proj / "a.ll"
    _ritz1(a, out)
    return a, b, out


# ---------------------------------------------------------------------------
# 1. Stale import → stale IR
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRitz1FastPathChecksImports:

    def test_unchanged_imports_still_hit_the_fast_path(self, two_modules):
        """Guard: the import check must not turn the cache off."""
        a, _b, out = two_modules
        assert SKIPPED in _ritz1(a, out).stdout

    def test_path_a_recompiles_when_imported_struct_changes(self, two_modules, tmp_path):
        """Path (a): a.ll stays newer than a.ritz; only b.ritz changed."""
        a, b, out = two_modules
        stale = out.read_text()
        b.write_text(REC_I64)
        t = a.stat().st_mtime + 10
        os.utime(out, (t, t))

        second = _ritz1(a, out)
        assert SKIPPED not in second.stdout, "served a.ll built against b's old layout"
        fresh = _cold_ir(a, tmp_path)
        assert fresh != stale, "test is vacuous: b's change does not affect a's IR"
        assert out.read_text() == fresh

    def test_path_b_recompiles_when_imported_struct_changes(self, two_modules, tmp_path):
        """Path (b): make deleted a.ll; the splice must not resurrect stale IR."""
        a, b, out = two_modules
        b.write_text(REC_I64)
        out.unlink()

        second = _ritz1(a, out)
        assert SKIPPED not in second.stdout, "spliced module_ir built against b's old layout"
        assert out.read_text() == _cold_ir(a, tmp_path)

    def test_transitive_import_change_recompiles(self, tmp_path, cache_dir):
        """a → m → b: a change two hops away still invalidates a."""
        proj = tmp_path / "proj"
        proj.mkdir()
        b = proj / "b.ritz"
        b.write_text(REC_I32)
        (proj / "m.ritz").write_text("import b\n\npub fn m_id(x: i32) -> i32\n    x\n")
        a = proj / "a.ritz"
        a.write_text(A_SRC.replace("import b\n", "import m\n"))
        out = proj / "a.ll"
        _ritz1(a, out)
        b.write_text(REC_I64)
        out.unlink()
        assert SKIPPED not in _ritz1(a, out).stdout

    def test_sig_records_import_hashes(self, two_modules):
        a, b, _out = two_modules
        data = json.loads(sig_path_for(a, "ritz1").read_text())
        hashes = data.get("import_hashes")
        assert isinstance(hashes, dict), data.keys()
        assert os.path.realpath(b) in hashes, hashes

    def test_sig_without_import_hashes_is_not_trusted(self, two_modules):
        """A sig that cannot vouch for its imports must fail closed."""
        a, _b, out = two_modules
        sig = sig_path_for(a, "ritz1")
        data = json.loads(sig.read_text())
        data.pop("import_hashes", None)
        sig.write_text(json.dumps(data))
        assert SKIPPED not in _ritz1(a, out).stdout

    def test_import_resolving_elsewhere_recompiles(self, tmp_path, cache_dir):
        """Same a.ritz, same b.ritz bytes on disk — but RITZ_PATH now finds another b."""
        v1 = tmp_path / "v1"
        v2 = tmp_path / "v2"
        proj = tmp_path / "proj"
        for d in (v1, v2, proj):
            d.mkdir()
        (v1 / "b.ritz").write_text(REC_I32)
        (v2 / "b.ritz").write_text(REC_I64)
        a = proj / "a.ritz"
        a.write_text(A_SRC)
        out = proj / "a.ll"
        _ritz1(a, out, env=_env(RITZ_PATH=str(v1)))
        out.unlink()
        second = _ritz1(a, out, env=_env(RITZ_PATH=str(v2)))
        assert SKIPPED not in second.stdout, "reused IR built against a different b.ritz"


# ---------------------------------------------------------------------------
# 2. Sig location: out of the source tree, one namespace per compiler
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSigLocation:

    def test_ritz1_writes_no_sig_beside_the_source(self, two_modules):
        a, b, _out = two_modules
        assert not list(a.parent.glob("*.sig")), list(a.parent.iterdir())

    def test_ritz1_sig_lives_in_its_namespace(self, two_modules, cache_dir):
        a, _b, _out = two_modules
        expected = cache_dir / "ritz1" / (os.path.realpath(a).lstrip("/") + ".sig")
        assert sig_path_for(a, "ritz1") == expected
        assert expected.exists(), sorted(str(p) for p in cache_dir.rglob("*"))

    def test_ritz0_writes_no_sig_beside_the_source(self, tmp_path, cache_dir):
        src = tmp_path / "solo.ritz"
        src.write_text("fn main() -> i32\n    0\n")
        _ritz0(src, tmp_path / "solo.ll")
        assert not list(tmp_path.glob("*.sig"))
        assert sig_path_for(src, "ritz0").exists()

    def test_default_root_is_xdg_cache(self, tmp_path, monkeypatch):
        """No RITZ_CACHE_DIR: $XDG_CACHE_HOME/ritz/<compiler>/..."""
        monkeypatch.delenv("RITZ_CACHE_DIR", raising=False)
        xdg = tmp_path / "xdg"
        monkeypatch.setenv("XDG_CACHE_HOME", str(xdg))
        src = tmp_path / "solo.ritz"
        src.write_text("fn main() -> i32\n    0\n")
        _ritz1(src, tmp_path / "solo.ll")
        assert (xdg / "ritz" / "ritz1" / (os.path.realpath(src).lstrip("/") + ".sig")).exists()

    def test_ritz1_binaries_are_namespaced_by_name(self, tmp_path, cache_dir):
        """ritz1 and ritz1_selfhosted must not evict each other either."""
        # The namespace is the basename /proc/self/exe resolves to, so a
        # differently named copy stands in for ritz1_selfhosted.
        copy = tmp_path / "bin" / "ritz1_other"
        copy.parent.mkdir()
        copy.write_bytes(RITZ1.read_bytes())
        copy.chmod(0o755)
        src = tmp_path / "solo.ritz"
        src.write_text("fn main() -> i32\n    0\n")
        subprocess.run([str(copy), str(src), "-o", str(tmp_path / "solo.ll")],
                       check=True, capture_output=True, env=_env())
        assert sig_path_for(src, "ritz1_other").exists()
        assert not sig_path_for(src, "ritz1").exists()


@pytest.mark.integration
def test_ritz0_compile_between_ritz1_compiles_keeps_ritz1_warm(two_modules):
    """#1280: a ritz0 compile of the same file used to wipe ritz1's entry."""
    a, _b, out = two_modules
    _ritz0(a, out.with_name("a.ritz0.ll"))
    assert SKIPPED in _ritz1(a, out).stdout
