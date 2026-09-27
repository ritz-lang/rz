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
    sig = src.with_suffix(".ritz.sig")
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
