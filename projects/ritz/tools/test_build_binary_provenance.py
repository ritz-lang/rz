"""build.py's binary fast path must check what the binary was BUILT FROM.

AGAST #1382: `compile_binary`'s project-level fast path used to forgive any
source whose mtime was `<=` the binary's, and for newer sources asked the
source's own `.ritz.sig` whether it had changed. Neither question is "was
this binary produced from these sources?", so it served stale binaries while
printing `🔨 ... ✓`:

  REPRO A  content changed, mtime pushed OLDER than the binary  -> stale
  REPRO B  content changed, mtime EQUAL to the binary (same second) -> stale
  REPRO C  content changed, mtime newer, but a `.ritz.sig` matching the NEW
           content sits next to it -> stale

The fix is binary provenance: `build/<profile>/<name>.manifest.json` records
the hash of every source the binary was linked from, plus the compiler, its
hash, the link profile and the binary's own hash. mtime is not an input.

A and B are driven verbatim from the ticket's shell (sed + touch). Do NOT
"fix" B by changing `<=` to `<`: the verbatim B truncates to whole seconds,
so its mtime is usually strictly older than the binary and stays red under
that mutation, and so do A and C.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
BUILD_PY = PKG_DIR / "build.py"
EXAMPLE = PKG_DIR / "examples" / "tier1_basics" / "02_exitcode"


def sig_path_for(src: Path, compiler: str) -> Path:
    """ritz0's mapping of a source to its sig file (AGAST #1807), loaded by
    path: ritz0 is not an installed package."""
    spec = importlib.util.spec_from_file_location(
        "ritz0_fn_cache_1807", PKG_DIR / "ritz0" / "emitter" / "fn_cache.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.sig_path_for(src, compiler)


# ---------------------------------------------------------------------------
# End-to-end helpers: real `build.py build` over a copy of 02_exitcode.
# ---------------------------------------------------------------------------


@pytest.fixture
def pkg(tmp_path):
    dst = tmp_path / "pkg"
    shutil.copytree(EXAMPLE, dst, ignore=shutil.ignore_patterns("build", "exitcode"))
    return dst


def build(pkg: Path) -> str:
    env = dict(os.environ, RITZ_PATH=str(PKG_DIR))
    r = subprocess.run(
        [sys.executable, str(BUILD_PY), "build", str(pkg)],
        capture_output=True, text=True, cwd=PKG_DIR, env=env,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def binary(pkg: Path) -> Path:
    return pkg / "build" / "debug" / "exitcode"


def run_exit(pkg: Path) -> int:
    return subprocess.run([str(binary(pkg))]).returncode


def main_src(pkg: Path) -> Path:
    return pkg / "src" / "main.ritz"


def set_return(pkg: Path, value: int) -> None:
    src = main_src(pkg)
    text = src.read_text()
    lines = [
        f"  return {value}" if line.strip().startswith("return ") else line
        for line in text.splitlines()
    ]
    src.write_text("\n".join(lines) + "\n")


def sh(cmd: str, pkg: Path) -> None:
    subprocess.run(["bash", "-c", cmd], cwd=pkg, check=True)


def fnv1a64(data: bytes) -> str:
    h = 14695981039346656037
    for b in data:
        h = ((h ^ b) * 1099511628211) & ((1 << 64) - 1)
    return f"{h:016x}"


@pytest.fixture
def built42(pkg):
    """Package built once from `return 42`, verified."""
    build(pkg)
    assert run_exit(pkg) == 42
    return pkg


# ---------------------------------------------------------------------------
# The three repros.
# ---------------------------------------------------------------------------


def test_repro_a_content_change_with_older_mtime_rebuilds(built42):
    """REPRO A (verbatim): cp -p / tar -x / git ops leave an older mtime."""
    sh("sed -i 's/return 42/return 7/' src/main.ritz", built42)
    sh('touch -d "@$(( $(stat -c %Y build/debug/exitcode) - 10 ))" src/main.ritz', built42)
    build(built42)
    assert run_exit(built42) == 7


def test_repro_b_equal_mtime_same_second_edit_rebuilds(built42):
    """REPRO B (verbatim): a source edited in the same second as the link.

    `stat -c %Y` truncates to whole seconds, so this is also the case a
    `<=` -> `<` "fix" leaves red: the source is at-or-before the binary.
    """
    sh("sed -i 's/return 42/return 99/' src/main.ritz", built42)
    sh('touch -d "@$(stat -c %Y build/debug/exitcode)" src/main.ritz', built42)
    build(built42)
    assert run_exit(built42) == 99


def test_repro_b_exactly_equal_nanosecond_mtime_rebuilds(built42):
    """REPRO B, strict form: source mtime identical to the binary's, to the ns."""
    set_return(built42, 13)
    bin_ns = binary(built42).stat().st_mtime_ns
    os.utime(main_src(built42), ns=(bin_ns, bin_ns))
    build(built42)
    assert run_exit(built42) == 13


def test_repro_c_matching_sig_does_not_forgive_binary_built_from_other_content(pkg):
    """REPRO C: the .ritz.sig describes the SOURCE, not the BINARY.

    Newer mtime, so mtime cannot be the cause. A sig whose source_hash
    matches the NEW content is exactly what a prior compile of that content
    leaves behind (e.g. a compile whose link failed).
    """
    set_return(pkg, 5)
    build(pkg)
    assert run_exit(pkg) == 5

    set_return(pkg, 8)
    src = main_src(pkg)
    t = binary(pkg).stat().st_mtime + 60
    os.utime(src, (t, t))
    # Plant it wherever either compiler would look (AGAST #1807 namespaces).
    for compiler in ("ritz0", "ritz1"):
        sig = sig_path_for(src, compiler)
        sig.parent.mkdir(parents=True, exist_ok=True)
        sig.write_text(json.dumps({"source_hash": fnv1a64(src.read_bytes())}))

    build(pkg)
    assert run_exit(pkg) == 8


def test_control_edit_with_newer_mtime_rebuilds(built42):
    """CONTROL: plain edit (mtime strictly newer) was always caught."""
    set_return(built42, 7)
    t = binary(built42).stat().st_mtime + 5
    os.utime(main_src(built42), (t, t))
    build(built42)
    assert run_exit(built42) == 7


# ---------------------------------------------------------------------------
# The fast path must still exist, and must say what it did (#1360 rule).
# ---------------------------------------------------------------------------


def test_noop_rebuild_is_up_to_date_and_says_so(built42):
    before = binary(built42).stat().st_mtime_ns
    out = build(built42)
    assert binary(built42).stat().st_mtime_ns == before, "no-op build relinked"
    assert "up to date" in out
    assert "🔨" not in out and "✓" not in out, out
    assert "Linking" not in out


def test_touch_without_content_change_stays_up_to_date(built42):
    """mtime is only ever a reason to look, never a verdict: a bare touch
    (content identical) must not force a relink."""
    before = binary(built42).stat().st_mtime_ns
    t = binary(built42).stat().st_mtime + 30
    os.utime(main_src(built42), (t, t))
    out = build(built42)
    assert binary(built42).stat().st_mtime_ns == before
    assert "up to date" in out


def test_real_rebuild_prints_hammer_and_check(built42):
    set_return(built42, 3)
    out = build(built42)
    assert "🔨" in out and "✓" in out and "up to date" not in out
    assert run_exit(built42) == 3


def test_binary_from_other_compiler_is_rebuilt(built42):
    """#1360 grammar: a binary some OTHER compiler produced must not satisfy
    this compiler's build. Simulated by rewriting the manifest's compiler, as
    `build.py build --compiler ritz1` would have left it."""
    manifest = binary(built42).with_name("exitcode.manifest.json")
    data = json.loads(manifest.read_text())
    data["compiler"] = "ritz1"
    manifest.write_text(json.dumps(data))
    before = binary(built42).stat().st_mtime_ns
    out = build(built42)
    assert "🔨" in out and "up to date" not in out
    assert binary(built42).stat().st_mtime_ns != before


def test_binary_without_manifest_is_rebuilt(built42):
    """A binary left by an older build.py (or an aborted run) has no
    provenance and must not be trusted, however new its mtime (#1401)."""
    binary(built42).with_name("exitcode.manifest.json").unlink()
    set_return(built42, 21)
    os.utime(main_src(built42), (1, 1))  # far older than the binary
    out = build(built42)
    assert "🔨" in out
    assert run_exit(built42) == 21


def test_failed_build_still_names_its_target(built42):
    """Deferring the 🔨 line must not orphan an error: a build that fails
    before committing to a rebuild (here, import resolution on a parse
    error) still prints which target failed."""
    good = main_src(built42).read_text()
    main_src(built42).write_text(good + "\nfn broken( -> \n")
    env = dict(os.environ, RITZ_PATH=str(PKG_DIR))
    r = subprocess.run([sys.executable, str(BUILD_PY), "build", str(built42)],
                       capture_output=True, text=True, cwd=PKG_DIR, env=env)
    assert r.returncode != 0
    assert "🔨 exitcode" in r.stdout and "Failed to build exitcode" in r.stdout
    assert "up to date" not in r.stdout


def test_manifest_written_next_to_binary(built42):
    manifest = binary(built42).with_name("exitcode.manifest.json")
    data = json.loads(manifest.read_text())
    srcs = dict(data["sources"])
    assert str(main_src(built42).resolve()) in srcs
    assert data["compiler"] == "ritz0"
    assert data["compiler_hash"]


# ---------------------------------------------------------------------------
# Unit tests on the provenance predicate.
# ---------------------------------------------------------------------------


@pytest.fixture
def buildpy(request):
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy_1382", BUILD_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PROFILE = {"name": "debug", "opt_level": 0, "debug": True, "lto": False}


@pytest.fixture
def linked(tmp_path, buildpy):
    """A fake binary + two sources with a manifest recorded for them."""
    a = tmp_path / "a.ritz"
    b = tmp_path / "b.ritz"
    a.write_text("fn a() -> i32\n  1\n")
    b.write_text("fn main() -> i32\n  0\n")
    bin_path = tmp_path / "out" / "prog"
    bin_path.parent.mkdir()
    bin_path.write_bytes(b"\x7fELF fake")
    prov = buildpy.binary_provenance([a, b], "ritz0", "H1", PROFILE)
    buildpy.write_binary_manifest(bin_path, prov)
    return buildpy, bin_path, [a, b], prov


def fresh(mod, bin_path, sources, compiler="ritz0", chash="H1", profile=PROFILE):
    prov = mod.binary_provenance(sources, compiler, chash, profile)
    return mod.binary_is_up_to_date(bin_path, prov)


def test_unit_matching_manifest_is_fresh(linked):
    mod, bin_path, srcs, _ = linked
    assert fresh(mod, bin_path, srcs)
    assert mod.binary_manifest_path(bin_path).name == "prog.manifest.json"


def test_unit_source_content_change_is_stale_regardless_of_mtime(linked):
    mod, bin_path, srcs, _ = linked
    st = srcs[0].stat()
    srcs[0].write_text("fn a() -> i32\n  2\n")
    os.utime(srcs[0], ns=(st.st_atime_ns, st.st_mtime_ns))  # mtime restored
    assert not fresh(mod, bin_path, srcs)


def test_unit_missing_manifest_is_stale(linked):
    mod, bin_path, srcs, _ = linked
    mod.binary_manifest_path(bin_path).unlink()
    assert not fresh(mod, bin_path, srcs)


def test_unit_corrupt_manifest_is_stale(linked):
    mod, bin_path, srcs, _ = linked
    mod.binary_manifest_path(bin_path).write_text("{not json")
    assert not fresh(mod, bin_path, srcs)


def test_unit_compiler_hash_change_is_stale(linked):
    mod, bin_path, srcs, _ = linked
    assert not fresh(mod, bin_path, srcs, chash="H2")


def test_unit_compiler_change_is_stale(linked):
    """#1360 grammar: ritz0's binary must not satisfy a ritz1 build."""
    mod, bin_path, srcs, _ = linked
    assert not fresh(mod, bin_path, srcs, compiler="ritz1")


def test_unit_unknown_compiler_hash_never_fresh(tmp_path, buildpy):
    a = tmp_path / "a.ritz"
    a.write_text("x")
    bin_path = tmp_path / "prog"
    bin_path.write_bytes(b"bin")
    prov = buildpy.binary_provenance([a], "ritz0", "unknown", PROFILE)
    buildpy.write_binary_manifest(bin_path, prov)
    assert not buildpy.binary_is_up_to_date(bin_path, prov)


def test_unit_source_set_change_is_stale(linked, tmp_path):
    mod, bin_path, srcs, _ = linked
    c = tmp_path / "c.ritz"
    c.write_text("fn c() -> i32\n  3\n")
    assert not fresh(mod, bin_path, [srcs[0], c, srcs[1]])
    assert not fresh(mod, bin_path, srcs[1:])


def test_unit_profile_change_is_stale(linked):
    mod, bin_path, srcs, _ = linked
    assert not fresh(mod, bin_path, srcs, profile=dict(PROFILE, opt_level=2))


def test_unit_runtime_shim_change_is_stale(linked, tmp_path):
    mod, bin_path, srcs, prov = linked
    shim = tmp_path / "ritz_start.ll"
    shim.write_text("; v1\n")
    p1 = mod.binary_provenance(srcs, "ritz0", "H1", PROFILE, runtime=[shim])
    mod.write_binary_manifest(bin_path, p1)
    assert mod.binary_is_up_to_date(bin_path, p1)
    shim.write_text("; v2\n")
    p2 = mod.binary_provenance(srcs, "ritz0", "H1", PROFILE, runtime=[shim])
    assert not mod.binary_is_up_to_date(bin_path, p2)


def test_unit_binary_replaced_is_stale(linked):
    """Something else wrote the binary (another build path, a cp): the
    manifest no longer describes it."""
    mod, bin_path, srcs, _ = linked
    bin_path.write_bytes(b"\x7fELF other")
    assert not fresh(mod, bin_path, srcs)


def test_unit_missing_binary_is_stale(linked):
    mod, bin_path, srcs, _ = linked
    bin_path.unlink()
    assert not fresh(mod, bin_path, srcs)


# ---------------------------------------------------------------------------
# AGAST #1499: concurrent builds into one output path (two worktrees or
# overlay roots that reach the same package through a symlink).
#
# The manifest used to hash `bin_path` as it was on disk when the manifest
# was written. If another build's link landed between this build's link and
# its manifest, the manifest certified the OTHER build's binary as built
# from THIS build's sources, and every later cached build of this tree
# served it as "up to date" (`--no-cache` skips the fast path, which is why
# it looked like a cache bug). The manifest must record the binary this
# build linked, so a foreign binary on disk never matches it.
# ---------------------------------------------------------------------------

FOREIGN = b"\x7fELF built by the other tree"


def _sha(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _foreign_write_before_manifest(mod, monkeypatch, target_name):
    """Make another build's output land on `target_name` just before this
    build writes its manifest: the interleaving the race produces."""
    real = mod.write_binary_manifest

    def racing(path, provenance, *args, **kwargs):
        if path.name == target_name:
            path.write_bytes(FOREIGN)
        return real(path, provenance, *args, **kwargs)

    monkeypatch.setattr(mod, "write_binary_manifest", racing)


def test_race_foreign_binary_before_manifest_is_not_certified(pkg, buildpy, monkeypatch):
    """compile_binary: a binary another build wrote over ours must not be
    recorded as ours, so the next cached build relinks instead of serving it."""
    out_dir = pkg / "build" / "debug"
    out_dir.mkdir(parents=True)
    monkeypatch.setenv("RITZ_PATH", str(PKG_DIR))
    _foreign_write_before_manifest(buildpy, monkeypatch, "exitcode")
    bin_path = buildpy.compile_binary("exitcode", main_src(pkg), out_dir, pkg_dir=pkg)
    assert bin_path is not None
    assert bin_path.read_bytes() == FOREIGN  # the other build won the path
    recorded = json.loads(buildpy.binary_manifest_path(bin_path).read_text())
    assert recorded["binary_sha256"] != _sha(FOREIGN), \
        "manifest certifies the other build's binary as built from these sources"

    monkeypatch.undo()
    monkeypatch.setenv("RITZ_PATH", str(PKG_DIR))
    rebuilt = []
    buildpy.compile_binary("exitcode", main_src(pkg), out_dir, pkg_dir=pkg,
                           on_rebuild=lambda: rebuilt.append(1))
    assert rebuilt, "cached build served the other build's binary as up to date"
    assert bin_path.read_bytes() != FOREIGN


def test_race_publish_records_hash_of_linked_file(tmp_path, buildpy):
    """publish_binary hashes the file this build produced, before it is
    visible at `bin_path`, and leaves no temp file behind."""
    a = tmp_path / "a.ritz"
    a.write_text("x")
    out = tmp_path / "out"
    out.mkdir()
    bin_path = out / "prog"
    tmp = buildpy.private_output_path(bin_path)
    assert tmp.parent == bin_path.parent and tmp != bin_path
    assert buildpy.private_output_path(bin_path) != tmp, "temp names must not collide"
    tmp.write_bytes(b"ours")
    prov = buildpy.binary_provenance([a], "ritz0", "H1", PROFILE)
    buildpy.publish_binary(tmp, bin_path, prov)
    assert bin_path.read_bytes() == b"ours"
    assert buildpy.binary_is_up_to_date(bin_path, prov)
    assert sorted(p.name for p in out.iterdir()) == ["prog", "prog.manifest.json"]
    # The manifest names our bytes: a later foreign write is never fresh.
    bin_path.write_bytes(FOREIGN)
    assert not buildpy.binary_is_up_to_date(bin_path, prov)


def test_race_publish_with_foreign_write_before_manifest(tmp_path, buildpy, monkeypatch):
    """The unit form of the race: a foreign write between publishing the
    binary and writing its manifest is never certified."""
    a = tmp_path / "a.ritz"
    a.write_text("x")
    bin_path = tmp_path / "prog"
    tmp = buildpy.private_output_path(bin_path)
    tmp.write_bytes(b"ours")
    prov = buildpy.binary_provenance([a], "ritz0", "H1", PROFILE)
    _foreign_write_before_manifest(buildpy, monkeypatch, "prog")
    buildpy.publish_binary(tmp, bin_path, prov)
    assert not buildpy.binary_is_up_to_date(bin_path, prov)


def test_race_manifest_temp_names_are_private(tmp_path, buildpy, monkeypatch):
    """Two builds writing one manifest must not share its temp file: one's
    os.replace would move the other's half-written file, or fail on a temp
    that the other already renamed."""
    a = tmp_path / "a.ritz"
    a.write_text("x")
    bin_path = tmp_path / "prog"
    bin_path.write_bytes(b"ours")
    prov = buildpy.binary_provenance([a], "ritz0", "H1", PROFILE)
    seen = []
    real_replace = os.replace

    def spy(src, dst):
        seen.append(Path(src).name)
        return real_replace(src, dst)

    monkeypatch.setattr(buildpy.os, "replace", spy)
    buildpy.write_binary_manifest(bin_path, prov)
    buildpy.write_binary_manifest(bin_path, prov)
    assert len(seen) == 2 and seen[0] != seen[1], seen


def test_race_foreign_archive_before_manifest_is_not_certified(tmp_path, buildpy, monkeypatch):
    """compile_library has the same publish step as compile_binary."""
    src = tmp_path / "lib" / "util.ritz"
    src.parent.mkdir()
    src.write_text("pub fn util_one() -> i32\n    1\n")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    lib = buildpy.LibraryConfig(name="util", modules=[src])
    monkeypatch.setenv("RITZ_PATH", str(PKG_DIR))
    _foreign_write_before_manifest(buildpy, monkeypatch, "libutil.a")
    archive = buildpy.compile_library(lib, out_dir, pkg_dir=tmp_path)
    assert archive is not None and archive.read_bytes() == FOREIGN
    recorded = json.loads(buildpy.binary_manifest_path(archive).read_text())
    assert recorded["binary_sha256"] != _sha(FOREIGN)
    assert sorted(p.name for p in out_dir.iterdir()) == ["libutil.a", "libutil.a.manifest.json"]
