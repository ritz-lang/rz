"""AGAST #4421: `rz cache gc` must free space the CAS never held.

`rz cache gc` used to manage only `~/.cache/ritz/cas`. On chungus the hog was
7.5 G of stale *sandbox repo copies* under
`~/.cache/ritz/<compiler>/home/<user>/dev/ritz-lang/*` (and, on the descr in
the ticket, `~/.cache/ritz/home/...`), plus ~75 M of `<compiler>/tmp`. This
file pins the age-based pass that evicts both:

* a sandbox repo copy older than a day goes; one with a recent mtime is a
  live gate's working set and must survive, and the skip is logged;
* `<compiler>/tmp` entries follow the same rule;
* biggest win first, and every skip/eviction is logged;
* `--max-bytes` accepts human suffixes (`3GiB`) as well as raw bytes.

The ≥5 GB acceptance uses a throwaway cache tree of *sparse* files, never the
host's real cache.
"""

import importlib
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
REPO = PKG_DIR.parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

cas = importlib.import_module("cas")

DAY = 24 * 60 * 60
GIB = 1024 ** 3


@pytest.fixture(autouse=True)
def cache(tmp_path, monkeypatch):
    """A throwaway cache root; the real ~/.cache/ritz is never touched."""
    root = tmp_path / "cache"
    (root / "cas").mkdir(parents=True)
    monkeypatch.setenv(cas.CAS_DIR_ENV, str(root / "cas"))
    monkeypatch.delenv(cas.STATS_LOG_ENV, raising=False)
    monkeypatch.setattr(cas, "STATS", cas.Stats())
    return root


def _age(path: Path, days: float) -> Path:
    stamp = time.time() - days * DAY
    os.utime(path, (stamp, stamp))
    return path


def _sandbox(cache_root: Path, compiler: str, name: str, *, age_days,
             size: int = 100) -> Path:
    """A sandbox repo copy: <cache>/<compiler>/home/<user>/dev/ritz-lang/<name>.

    `compiler` may be "" for the `~/.cache/ritz/home/...` layout the ticket
    describes. Files are written first, then the copy's own mtime is set."""
    base = cache_root / compiler / "home" / "u" / "dev" / "ritz-lang"
    p = base / name
    p.mkdir(parents=True)
    (p / "f.ritz").write_bytes(b"x" * size)
    return _age(p, age_days)


def _tmp_entry(cache_root: Path, compiler: str, name: str, *, age_days,
               size: int = 100) -> Path:
    comp = cache_root / compiler
    (comp / "home").mkdir(parents=True, exist_ok=True)
    p = comp / "tmp" / name
    p.mkdir(parents=True)
    (p / "f").write_bytes(b"y" * size)
    return _age(p, age_days)


@pytest.mark.unit
def test_age_pass_evicts_stale_sandbox_repo_copies_and_keeps_live_ones(cache):
    old = _sandbox(cache, "ritz0", "rz-task-1", age_days=3, size=500)
    live = _sandbox(cache, "ritz1", "rz-task-2", age_days=0, size=500)
    # The chungus description's layout: home directly under the cache root.
    old_direct = _sandbox(cache, "", "rz-task-3", age_days=3, size=40)

    removed, freed = cas.ArtifactStore().gc(max_bytes=10 ** 15)

    assert not old.exists(), "a stale sandbox repo copy survived"
    assert not old_direct.exists(), "a stale home/**/ritz-lang copy survived"
    assert live.exists(), "gc touched a live gate's working set"
    assert (removed, freed) == (2, 540)


@pytest.mark.unit
def test_age_pass_evicts_stale_compiler_tmp_entries(cache):
    old_dir = _tmp_entry(cache, "ritz0", "scratch-old", age_days=2, size=300)
    live_dir = _tmp_entry(cache, "ritz0", "scratch-live", age_days=0, size=300)
    old_file = cache / "ritz0" / "tmp" / "old.o"
    old_file.write_bytes(b"z" * 7)
    _age(old_file, 2)

    removed, freed = cas.ArtifactStore().gc(max_bytes=10 ** 15)

    assert not old_dir.exists()
    assert not old_file.exists()
    assert live_dir.exists()
    assert (removed, freed) == (2, 307)


@pytest.mark.unit
def test_gc_logs_every_eviction_and_every_skip(cache):
    old = _sandbox(cache, "ritz0", "gone", age_days=2, size=10)
    live = _sandbox(cache, "ritz0", "live", age_days=0.01, size=10)
    messages = []

    cas.ArtifactStore().gc(max_bytes=10 ** 15, log=messages.append)

    evictions = [m for m in messages if "evict" in m]
    skips = [m for m in messages if "skip" in m]
    assert any(str(old) in m for m in evictions), messages
    assert any(str(live) in m for m in skips), messages


@pytest.mark.unit
def test_gc_evicts_the_biggest_stale_copy_first(cache):
    _sandbox(cache, "ritz0", "small", age_days=2, size=10)
    big = _sandbox(cache, "ritz0", "big", age_days=2, size=10_000)
    messages = []

    cas.ArtifactStore().gc(max_bytes=10 ** 15, log=messages.append)

    evictions = [m for m in messages if "evict" in m]
    assert str(big) in evictions[0], evictions


@pytest.mark.unit
@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("3221225472", 3221225472),
        ("3GiB", 3 * GIB),
        ("3gib", 3 * GIB),
        ("4G", 4 * GIB),
        ("1.5MiB", 1024 * 1024 + 512 * 1024),
        ("0", 0),
    ],
)
def test_parse_size_accepts_raw_bytes_and_binary_suffixes(text, want):
    assert cas.parse_size(text) == want


@pytest.mark.unit
@pytest.mark.parametrize("text", ["", "3GBB", "lots", "-1", "1.2.3G"])
def test_parse_size_rejects_junk(text):
    with pytest.raises(ValueError):
        cas.parse_size(text)


@pytest.mark.unit
def test_cli_gc_accepts_a_suffix(cache, capsys):
    assert cas.main(["gc", "--max-bytes", "3GiB"]) == 0
    assert "freed 0 bytes" in capsys.readouterr().out


@pytest.mark.unit
def test_cli_help_documents_bytes_and_suffixes(capsys):
    with pytest.raises(SystemExit):
        cas.main(["gc", "--help"])
    # argparse wraps help; compare words, not line breaks.
    out = " ".join(capsys.readouterr().out.split())
    assert "--max-bytes" in out and "bytes" in out
    assert "suffixes are accepted" in out, out
    assert "3GiB" in out, out


@pytest.mark.unit
def test_acceptance_gc_reclaims_5gb_of_stale_sandbox_copies(cache):
    """Acceptance: one documented command frees ≥5 GB, live working set intact.

    Sparse files: apparent size is counted, disk use is ~0."""
    per = 100 * 1024 * 1024
    stale = [_sandbox(cache, "ritz0", f"rz-task-{1000 + i}", age_days=2)
             for i in range(60)]
    for p in stale:
        with open(p / "big.bin", "wb") as f:
            f.truncate(per)
        _age(p, 2)
    live = _sandbox(cache, "ritz0", "rz-task-live", age_days=0)
    with open(live / "big.bin", "wb") as f:
        f.truncate(per)

    _removed, freed = cas.ArtifactStore().gc(max_bytes=10 ** 15)

    assert freed >= 5 * GIB, f"only {freed} bytes freed"
    assert live.exists(), "gc removed a live gate's working set"
    assert not any(p.exists() for p in stale)


@pytest.mark.integration
def test_provision_refusal_prints_the_reclaim_recipe(tmp_path):
    """The 20 GB refusal names the command that actually works."""
    exec_dir = tmp_path / "exec"
    exec_dir.mkdir()
    env = {**os.environ, "RZ_MIN_DISK_GB": "999999999",
           "RZ_EXEC_DIRS": str(exec_dir)}
    r = subprocess.run(
        ["bash", str(REPO / ".claude" / "provision-room.sh"),
         "--check-host", str(REPO)],
        env=env, capture_output=True, text=True, timeout=120, check=False)
    assert r.returncode == 1, r.stdout + r.stderr
    out = r.stdout
    assert "rz cache gc" in out, out
    assert "ritz-lang" in out, out
    assert "~/tmp" in out, out
    assert "live gate" in out, out
    assert "20 GB" in out, out
