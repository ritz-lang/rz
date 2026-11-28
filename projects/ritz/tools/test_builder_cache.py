"""The builder's persistent CAS (AGAST #4857).

projects/builder/entrypoint.sh compiled a package's whole import closure
(its own sources, ritzlib, ritzunit) in every container, into a CAS under
its private temp workspace. With RZ_BUILDER_CACHE naming a mounted
directory, the CAS lives there instead, under a subdirectory named by
`rz-builder --cache-key` (ritz1_selfhosted's sha256 and clang's version), so
a run on an unchanged compiler reuses the objects of the last and a new
compiler starts empty. main.yml's hosted builder-matrix keeps that directory
in actions/cache under the same key.

What the image does end to end (a second run compiles nothing, a changed
compiler misses) is projects/builder/test.sh's, which builds and runs the
image. These check the parts a host can run: the key, summary.py's view of
a shared store, run_builder_package.sh's mount and the workflow's cache.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
ENTRYPOINT = REPO_ROOT / "projects" / "builder" / "entrypoint.sh"
SUMMARY = REPO_ROOT / "projects" / "builder" / "summary.py"
RUN_PACKAGE = REPO_ROOT / ".github" / "scripts" / "run_builder_package.sh"
MAIN_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "main.yml"

CLANG_STUB = """#!/bin/sh
echo "Debian clang version 21.1.8 (++20251221032922+2078da43e25a-1~exp1~20251221153059.70)"
echo "Target: x86_64-pc-linux-gnu"
"""


# --- rz-builder --cache-key --------------------------------------------------

def _cache_key(tmp_path: Path, ritz1_bytes: bytes) -> subprocess.CompletedProcess:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    (bin_dir / "clang").write_text(CLANG_STUB)
    (bin_dir / "clang").chmod(0o755)
    ritz1 = tmp_path / "ritz1_selfhosted"
    ritz1.write_bytes(ritz1_bytes)
    ritz1.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}", RITZ1=str(ritz1),
               RZ_ROOT=str(tmp_path / "no-workspace"))
    return subprocess.run(["bash", str(ENTRYPOINT), "--cache-key"], env=env,
                          capture_output=True, text=True, timeout=30)


@pytest.mark.integration
def test_cache_key_names_the_compiler_sha256_and_clang_version(tmp_path):
    """The key is the builder image's dev.ritz.ritz1-selfhosted.sha256 label
    (the binary's sha256, which the Dockerfile checks) plus clang's version:
    an object is only as good as both."""
    r = _cache_key(tmp_path, b"compiler one")
    assert r.returncode == 0, r.stderr
    sha = hashlib.sha256(b"compiler one").hexdigest()
    assert r.stdout == f"ritz1-{sha[:16]}-clang-21.1.8\n", r.stdout
    other = _cache_key(tmp_path, b"compiler two").stdout
    assert other and other != r.stdout


# --- concurrent runs on one cache (AGAST #4927) --------------------------------

# The workspace's `./rz`. `build` puts an object in this run's store; with
# $HOLD set it then waits for $HOLD/go (a neighbour's whole run happens
# meanwhile) and fails if the object is gone.
FAKE_RZ = """#!/usr/bin/env bash
[[ $1 == build ]] || exit 0
mkdir -p "$RITZ_CACHE_DIR/objects/ab"
echo obj > "$RITZ_CACHE_DIR/objects/ab/ab.o"
if [[ -n ${HOLD:-} ]]; then
    touch "$HOLD/building"
    for _ in $(seq 300); do [[ -e $HOLD/go ]] && break; sleep 0.1; done
    [[ -f $RITZ_CACHE_DIR/objects/ab/ab.o ]] || { echo "fake rz: store deleted under me"; exit 1; }
fi
"""


def _builder_workspace(tmp_path: Path) -> tuple[Path, Path]:
    """A stand-in for the image's /rz: just enough for the entrypoint to
    stage a package, find its compiler and run `./rz build`."""
    root = tmp_path / "rz"
    ritz = root / "projects" / "ritz"
    ritz.mkdir(parents=True)
    (ritz / "build_pipeline.py").write_text(
        'RITZ1_SELFHOSTED_BIN = "projects/ritz/ritz1/build/ritz1_selfhosted"\n')
    (ritz / "cas.py").write_text('print("gc: trimmed nothing")\n')
    (root / "rz").write_text(FAKE_RZ)
    (root / "rz").chmod(0o755)
    (root / "rz.toml").write_text("")
    (root / "projects" / "pkg").mkdir()
    (root / "projects" / "pkg" / "ritz.toml").write_text('[package]\nname = "pkg"\n')
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "clang").write_text(CLANG_STUB)
    (bin_dir / "clang").chmod(0o755)
    return root, bin_dir


def _entrypoint(tmp_path: Path, root: Path, bin_dir: Path, cache: Path, name: str,
                ritz1_bytes: bytes, **env: str) -> subprocess.Popen:
    run = tmp_path / name
    (run / "tmp").mkdir(parents=True)
    ritz1 = run / "ritz1_selfhosted"
    ritz1.write_bytes(ritz1_bytes)
    ritz1.chmod(0o755)
    full_env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}", RITZ1=str(ritz1),
                    RZ_ROOT=str(root), RZ_OUT=str(run / "out"), TMPDIR=str(run / "tmp"),
                    RZ_BUILDER_CACHE=str(cache), **env)
    return subprocess.Popen(["bash", str(ENTRYPOINT), "--build-only", "projects/pkg"],
                            env=full_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True)


@pytest.mark.integration
def test_a_run_never_deletes_the_store_a_concurrent_run_is_using(tmp_path):
    """Gates on one host share RZ_BUILDER_CACHE. A run on another compiler
    prunes old stores, but not one a neighbour is building in: #4808's and
    #4809's gates failed when it did. An idle store of another compiler is
    still pruned, so the cache keeps one store per compiler in use."""
    root, bin_dir = _builder_workspace(tmp_path)
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "ritz1-0000000000000000-clang-21.1.8" / "objects").mkdir(parents=True)
    hold = tmp_path / "hold"
    hold.mkdir()
    a = _entrypoint(tmp_path, root, bin_dir, cache, "a", b"compiler one", HOLD=str(hold))
    try:
        deadline = time.monotonic() + 60
        while not (hold / "building").exists():
            assert a.poll() is None, a.communicate()[0]
            assert time.monotonic() < deadline, "run A never started building"
            time.sleep(0.05)
        b = _entrypoint(tmp_path, root, bin_dir, cache, "b", b"compiler two")
        b_out = b.communicate(timeout=60)[0]
    finally:
        (hold / "go").touch()
        a_out = a.communicate(timeout=60)[0]
    assert b.returncode == 0, b_out
    assert a.returncode == 0, a_out
    stores = sorted(p.name for p in cache.iterdir() if p.is_dir())
    assert len(stores) == 2 and "ritz1-0000000000000000-clang-21.1.8" not in stores, stores
    assert sorted(p.name for p in cache.glob("*.lock")) == [f"{s}.lock" for s in stores]


# --- summary.py over a shared store -------------------------------------------

def _store_object(cas: Path, key: str, module: str, mtime: float) -> None:
    obj = cas / "objects" / key[:2] / f"{key}.o"
    obj.parent.mkdir(parents=True, exist_ok=True)
    obj.write_bytes(b"\x7fELF" + key.encode())
    meta = cas / "meta" / key[:2] / f"{key}.json"
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(json.dumps({"module": module}))
    os.utime(obj, (mtime, mtime))


def _summary_module():
    spec = importlib.util.spec_from_file_location("builder_summary_4857", SUMMARY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _finish(tmp_path: Path, cas: Path, *extra: str) -> dict:
    """summary.py's `finish`, in process, for a build-only run."""
    out = tmp_path / "out"
    (tmp_path / "build.log").write_text("")
    (tmp_path / "test.log").write_text("")
    rc = _summary_module().main(
        ["finish", "--out", str(out),
         "--build-log", str(tmp_path / "build.log"), "--build-rc", "0",
         "--test-log", str(tmp_path / "test.log"), "--test-rc", "0",
         "--build-only", "1", "--package-build", str(tmp_path / "none"),
         "--cas", str(cas), "--source", "projects/x",
         "--manifest", str(tmp_path / "none.toml"), "--ritz1", str(tmp_path / "none"),
         *extra])
    assert rc == 0
    return json.loads((out / "summary.json").read_text())


@pytest.mark.unit
def test_objects_are_the_ones_this_run_used_not_the_whole_store(tmp_path):
    """A persistent store holds every package's and every earlier run's
    objects. /out/obj gets the ones this run compiled or hit: ArtifactStore
    touches an object on a hit, so its mtime is at or after the run's start."""
    cas = tmp_path / "cas"
    now = time.time()
    _store_object(cas, "aa" + "0" * 62, "projects/old/stale.ritz", now - 3600)
    _store_object(cas, "bb" + "0" * 62, "projects/ritz/ritzlib/io.ritz", now)
    marker = tmp_path / "run-start"
    marker.touch()
    os.utime(marker, (now - 60, now - 60))
    summary = _finish(tmp_path, cas, "--since", str(marker))
    assert summary["objects"] == 1
    assert sorted(p.name for p in (tmp_path / "out" / "obj").iterdir()) == \
        ["projects_ritz_ritzlib_io.o"]


@pytest.mark.unit
def test_without_since_every_object_in_the_store_is_this_runs(tmp_path):
    """A private, per-run store (no RZ_BUILDER_CACHE) holds only this run's."""
    cas = tmp_path / "cas"
    _store_object(cas, "aa" + "0" * 62, "projects/a/a.ritz", time.time() - 3600)
    _store_object(cas, "bb" + "0" * 62, "projects/b/b.ritz", time.time())
    assert _finish(tmp_path, cas)["objects"] == 2


@pytest.mark.unit
def test_cas_stats_count_hits_and_what_this_run_compiled(tmp_path):
    """summary.json's `cas` says what the store saved: a warm run of an
    unchanged compiler and sources compiles nothing (`compiled` 0)."""
    log = tmp_path / "cas-stats.jsonl"
    k1, k2, k3 = ("1" * 64, "2" * 64, "3" * 64)
    log.write_text("\n".join(json.dumps(r) for r in [
        {"hits": 3, "misses": 2, "missed": [[k1, "o", "projects/ritz/ritzlib/io.ritz", "/c"],
                                            [k2, "o", "pkg/x/src/main.ritz", "/c"]]},
        {"hits": 4, "misses": 1, "missed": [[k3, "o", "projects/ritz/ritzlib/sys.ritz", "/c"]]},
        {"hits": 1, "misses": 0, "missed": []},
    ]) + "\nnot json\n")
    summary = _finish(tmp_path, tmp_path / "cas", "--cas-stats", str(log))
    assert summary["cas"] == {"hits": 8, "misses": 3, "compiled": 3}


@pytest.mark.unit
def test_no_cas_stats_log_means_no_cas_entry(tmp_path):
    assert "cas" not in _finish(tmp_path, tmp_path / "cas")


# --- run_builder_package.sh --cache --------------------------------------------

DOCKER_STUB = """#!/usr/bin/env bash
echo "$*" >> "$STUB_DIR/calls"
for a in "$@"; do
    case $a in *:/out) out=${a%%:/out} ;; esac
done
printf '{"ok": true, "test": {"passed": 1, "failed": 0}}' > "$out/summary.json"
"""


def _run_package(tmp_path: Path, *flags: str) -> list[str]:
    stub = tmp_path / "bin"
    stub.mkdir()
    (stub / "docker").write_text(DOCKER_STUB)
    (stub / "docker").chmod(0o755)
    cwd = tmp_path / "cwd"
    (cwd / "projects" / "x").mkdir(parents=True)
    (cwd / "projects" / "x" / "ritz.toml").write_text('[package]\nname = "x"\n')
    env = dict(os.environ, PATH=f"{stub}:{os.environ['PATH']}", STUB_DIR=str(tmp_path))
    r = subprocess.run(["bash", str(RUN_PACKAGE), *flags, "rz-builder:ci", "projects/x",
                        str(tmp_path / "out")],
                       cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stdout + r.stderr
    return (tmp_path / "calls").read_text().splitlines()


@pytest.mark.integration
def test_cache_mounts_the_directory_writable_and_names_it(tmp_path):
    cache = tmp_path / "cas"
    [call] = _run_package(tmp_path, "--cache", str(cache))
    assert cache.is_dir()
    assert f"-v {cache}:/cache " in call, call
    assert "-e RZ_BUILDER_CACHE=/cache" in call, call
    assert call.endswith("rz-builder:ci projects/x"), call


@pytest.mark.integration
def test_no_cache_flag_mounts_no_cache(tmp_path):
    [call] = _run_package(tmp_path)
    assert "/cache" not in call and "RZ_BUILDER_CACHE" not in call, call


# --- main.yml: the hosted fallback keeps the store in actions/cache ------------

@pytest.mark.unit
def test_hosted_builder_matrix_restores_and_saves_the_store_by_compiler_key():
    """Keyed by `rz-builder --cache-key`, so a compiler change restores
    nothing; the run id makes every run save its (trimmed) store, so the
    objects of ritzlib changes since the first save are kept too."""
    steps = yaml.safe_load(MAIN_WORKFLOW.read_text())["jobs"]["builder-matrix"]["steps"]
    by_id = {s.get("id"): s for s in steps if s.get("id")}
    assert "--cache-key" in by_id["cas"]["run"]
    [cache] = [s for s in steps if str(s.get("uses", "")).startswith("actions/cache@")]
    w = cache["with"]
    assert w["path"] == "${{ runner.temp }}/builder-cas"
    prefix = "builder-cas-${{ steps.cas.outputs.key }}-"
    assert w["key"].startswith(prefix) and "${{ github.run_id }}" in w["key"]
    assert [k.strip() for k in w["restore-keys"].strip().splitlines()][-1] == prefix
    [run] = [s for s in steps if "run_builder_package.sh" in str(s.get("run", ""))]
    assert '--cache "$RUNNER_TEMP/builder-cas"' in run["run"]
    assert steps.index(cache) < steps.index(run)
