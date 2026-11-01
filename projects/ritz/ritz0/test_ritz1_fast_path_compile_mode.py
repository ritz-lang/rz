#!/usr/bin/env python3
"""ritz1's "Skipped (unchanged)" fast path must vouch for *this* output (AGAST #2023).

ritz0 got this fix in #2020 (``test_fast_path_compile_mode.py``); this is the
ritz1 half.  ``check_source_unchanged`` (ritz1/src/fn_cache.ritz) keys its sig
on the source, and stamps it with ``cache_fingerprint()``: the compiler, the
target OS and the import roots.  Two holes remained:

* **Path (a) never looked at the output.** Once the sig matched, any ``.ll``
  newer than the source was taken as up to date, whoever wrote it.  So the
  fast path kept:

  - a ``--test-table`` compile's output (test mode writes no sig, so the
    default-mode sig from before it still matched);
  - another target OS's IR, when that OS's compile into a *different* path
    had re-stamped the sig;
  - an output rewritten behind the sig's back.

  Fix: path (a) reuses the output only when it is byte-identical to the sig's
  ``module_ir``.  That IR is stamped with the mode's fingerprint, so a match
  means the output is what this mode would emit.  On a mismatch the sig's IR
  is spliced in (path (b)), which is correct for the same reason.

* **Import roots were fingerprinted as strings.**  A relative ``-I`` /
  ``RITZ_PATH`` entry, or the source's own directory (which imports resolve
  against first), names a different directory from a different cwd or
  through a symlink.  Fix: fingerprint them canonicalised.

Each test runs the real ritz1 binary against a private ``RITZ_CACHE_DIR``.  A
mode's expected IR is a cold compile (fresh sig cache, fresh output path).
"""

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

# Every test runs a compiler process (AGAST #1805).
pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1 = RITZ_ROOT / "ritz1" / "build" / "ritz1"


@pytest.fixture(scope="module", autouse=True)
def _ritz1_built(ritz1_bin):
    """Every test here needs an up-to-date ritz1: conftest's session build."""


# Import-free, so the compile is fast and RITZ_PATH-independent.  Each mode
# yields IR distinct from the others (test_every_mode_changes_the_ir).
MODE_SRC = """\
[[target_os = "linux"]]
const OS_TAG: i32 = 11

[[target_os = "harland"]]
const OS_TAG: i32 = 22

[[test]]
fn test_one() -> i32
    0

fn main() -> i32
    OS_TAG
"""

MODES = {
    "default": [],
    "test_mode": ["--test-table"],
    "target_os": ["--target-os", "harland"],
}

MODE_PAIRS = [(a, b) for a in MODES for b in MODES if a != b]


def _run(
    src: Path, out: Path, flags, cache: Path, cwd=None, ritz_path=None, src_arg=None
):
    env = dict(os.environ)
    env["RITZ_CACHE_DIR"] = str(cache)
    env.pop("RITZ_PATH", None)
    if ritz_path is not None:
        env["RITZ_PATH"] = ritz_path
    return subprocess.run(
        [
            str(RITZ1),
            str(src_arg if src_arg is not None else src),
            "-o",
            str(out),
            *flags,
        ],
        capture_output=True,
        text=True,
        cwd=str(cwd if cwd is not None else src.parent),
        env=env,
        timeout=120,
    )


def _compile(src, out, flags, cache, **kw) -> str:
    proc = _run(src, out, flags, cache, **kw)
    assert proc.returncode == 0, f"ritz1 {flags} failed:\n{proc.stdout}\n{proc.stderr}"
    return proc.stdout


def _cold(src, flags, tmp_path: Path, tag: str, **kw) -> str:
    """IR of a cold compile: fresh sig cache, fresh output path."""
    out = tmp_path / f"cold-{tag}.ll"
    _compile(src, out, flags, tmp_path / f"cold-cache-{tag}", **kw)
    return out.read_text()


@pytest.fixture
def mode_src(tmp_path) -> Path:
    src = tmp_path / "src" / "main.ritz"
    src.parent.mkdir()
    src.write_text(MODE_SRC)
    return src


# --- Compile mode -------------------------------------------------------------


def test_every_mode_changes_the_ir(mode_src, tmp_path):
    """Precondition: each mode's cold IR differs from every other mode's."""
    irs = {m: _cold(mode_src, f, tmp_path, m) for m, f in MODES.items()}
    assert len(set(irs.values())) == len(MODES), (
        "two modes produce identical IR; MODE_SRC no longer tells them apart"
    )


@pytest.mark.parametrize(
    "first,second", MODE_PAIRS, ids=[f"{a}-then-{b}" for a, b in MODE_PAIRS]
)
def test_mode_switch_into_same_output_matches_cold(mode_src, tmp_path, first, second):
    """Mode A, then B, then A into one path: each result is that mode's cold IR."""
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    # Warm the sig in the default mode first, so a sig always exists that a
    # later compile could (wrongly) take as vouching for `out`.
    _compile(mode_src, tmp_path / "warm.ll", [], cache)
    for mode in (first, second, first):
        _compile(mode_src, out, MODES[mode], cache)
        assert out.read_text() == _cold(mode_src, MODES[mode], tmp_path, mode), (
            f"compiling {first} -> {second} -> {first}: {mode} kept another mode's output"
        )


def test_same_mode_same_output_still_skips(mode_src, tmp_path):
    """The fast path itself survives: an unchanged recompile skips and leaves
    the output alone (same bytes and mtime, so make sees no change)."""
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    for mode in ("default", "target_os"):
        _compile(mode_src, out, MODES[mode], cache)
        before = out.read_text()
        mtime = out.stat().st_mtime_ns
        stdout = _compile(mode_src, out, MODES[mode], cache)
        assert "Skipped" in stdout, f"{mode}: unchanged recompile did not skip"
        assert out.read_text() == before
        assert out.stat().st_mtime_ns == mtime, f"{mode}: skip rewrote the output"


def test_other_mode_into_other_output_does_not_vouch_for_this_one(mode_src, tmp_path):
    """The sig is per source: harland into b.ll re-stamps it, and must not then
    vouch for a.ll, which still holds linux IR."""
    a, b = tmp_path / "a.ll", tmp_path / "b.ll"
    cache = tmp_path / "cache"
    _compile(mode_src, a, MODES["default"], cache)
    _compile(mode_src, b, MODES["target_os"], cache)
    _compile(mode_src, a, MODES["target_os"], cache)
    assert a.read_text() == _cold(mode_src, MODES["target_os"], tmp_path, "harland")


def test_test_mode_output_is_not_vouched_for_by_default_sig(mode_src, tmp_path):
    """Test mode writes no sig, so the default-mode sig still matches after it;
    that must not make test mode's output pass for the default mode's."""
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    _compile(mode_src, out, [], cache)
    _compile(mode_src, out, ["--test-table"], cache)
    _compile(mode_src, out, [], cache)
    assert out.read_text() == _cold(mode_src, [], tmp_path, "default")


def test_output_rewritten_behind_the_sig_is_not_trusted(mode_src, tmp_path):
    """An output the sig did not write (here: clobbered, so newer than the
    source) is replaced with the IR this mode emits."""
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    _compile(mode_src, out, [], cache)
    good = out.read_text()
    time.sleep(0.01)
    out.write_text("; not ritz1's output\n")
    _compile(mode_src, out, [], cache)
    assert out.read_text() == good


def test_output_older_than_source_is_refreshed(mode_src, tmp_path):
    """A source touched without changing (content hash matches) leaves an
    output older than it; the fast path rewrites it so make stops re-running."""
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    _compile(mode_src, out, [], cache)
    good = out.read_text()
    os.utime(out, ns=(1_000_000_000, 1_000_000_000))
    stdout = _compile(mode_src, out, [], cache)
    assert "Skipped" in stdout
    assert out.read_text() == good
    assert out.stat().st_mtime_ns >= mode_src.stat().st_mtime_ns


# --- Import roots: a different root resolves a different module ---------------

LIB_SRC = "pub const LIB_TAG: i32 = {tag}\n"

USE_LIB_SRC = """\
import shared.tag

fn main() -> i32
    LIB_TAG
"""


@pytest.fixture
def two_roots(tmp_path):
    """Two roots, each with a `shared/tag.ritz` whose LIB_TAG differs."""
    roots = {}
    for name, tag in (("rootA", 101), ("rootB", 202)):
        root = tmp_path / name
        (root / "shared").mkdir(parents=True)
        (root / "shared" / "tag.ritz").write_text(LIB_SRC.format(tag=tag))
        roots[name] = root
    src = tmp_path / "app" / "main.ritz"
    src.parent.mkdir()
    src.write_text(USE_LIB_SRC)
    return src, roots


def _assert_tag(ir: str, tag: int):
    assert str(tag) in ir, f"expected LIB_TAG {tag} in IR:\n{ir}"


@pytest.mark.parametrize("how", ["dash_i", "env"])
def test_absolute_root_switch_recompiles(two_roots, tmp_path, how):
    """`-I` and RITZ_PATH reach the fingerprint (#1807): switching an absolute
    root into the same output gives the new root's module."""
    src, roots = two_roots
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    for name, tag in (("rootA", 101), ("rootB", 202), ("rootA", 101)):
        if how == "dash_i":
            _compile(src, out, ["-I", str(roots[name])], cache)
        else:
            _compile(src, out, [], cache, ritz_path=str(roots[name]))
        _assert_tag(out.read_text(), tag)


@pytest.mark.parametrize("how", ["dash_i", "env"])
def test_relative_root_from_another_cwd_recompiles(two_roots, tmp_path, how):
    """The same relative root string from two cwds names two directories."""
    src, roots = two_roots
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    # rootA/../rootA is just "rootA" from tmp_path; make cwd-specific dirs
    # whose `lib` points at a different root each.
    cwd_a, cwd_b = tmp_path / "cwdA", tmp_path / "cwdB"
    for cwd, name in ((cwd_a, "rootA"), (cwd_b, "rootB")):
        cwd.mkdir()
        (cwd / "lib").symlink_to(roots[name])
    for cwd, tag in ((cwd_a, 101), (cwd_b, 202), (cwd_a, 101)):
        if how == "dash_i":
            _compile(src, out, ["-I", "lib"], cache, cwd=cwd)
        else:
            _compile(src, out, [], cache, cwd=cwd, ritz_path="lib")
        _assert_tag(out.read_text(), tag)


def test_source_through_symlink_resolves_relative_imports_there(tmp_path):
    """Imports resolve against the source's directory *as named*.  A symlink
    to the source from another directory shares its sig (the sig key is the
    canonical source) but resolves `shared.tag` somewhere else."""
    real = tmp_path / "real" / "main.ritz"
    real.parent.mkdir()
    real.write_text(USE_LIB_SRC)
    (real.parent / "shared").mkdir()
    (real.parent / "shared" / "tag.ritz").write_text(LIB_SRC.format(tag=101))

    other = tmp_path / "other"
    (other / "shared").mkdir(parents=True)
    (other / "shared" / "tag.ritz").write_text(LIB_SRC.format(tag=202))
    (other / "main.ritz").symlink_to(real)

    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    _compile(real, out, [], cache)
    _assert_tag(out.read_text(), 101)
    _compile(real, out, [], cache, src_arg=other / "main.ritz", cwd=other)
    _assert_tag(out.read_text(), 202)
    _compile(real, out, [], cache)
    _assert_tag(out.read_text(), 101)


def test_relative_source_climbs_from_cwd(tmp_path):
    """The resolver climbs a relative source dir textually: `x/y/` then `x/`.
    From two cwds `x/y` can be the same directory while `x/` is not."""
    real = tmp_path / "real" / "main.ritz"
    real.parent.mkdir()
    real.write_text(USE_LIB_SRC)
    cwds = {}
    for name, tag in (("cwdA", 101), ("cwdB", 202)):
        x = tmp_path / name / "x"
        (x / "shared").mkdir(parents=True)
        (x / "shared" / "tag.ritz").write_text(LIB_SRC.format(tag=tag))
        (x / "y").symlink_to(real.parent)
        cwds[name] = x.parent

    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    for name, tag in (("cwdA", 101), ("cwdB", 202), ("cwdA", 101)):
        _compile(real, out, [], cache, src_arg="x/y/main.ritz", cwd=cwds[name])
        _assert_tag(out.read_text(), tag)


def test_root_switch_still_skips_when_unchanged(two_roots, tmp_path):
    """Canonicalising the roots must not cost the warm case its skip, and
    spelling the same root differently (relative vs absolute) still skips."""
    src, roots = two_roots
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    _compile(src, out, ["-I", str(roots["rootA"])], cache)
    assert "Skipped" in _compile(src, out, ["-I", str(roots["rootA"])], cache)
    assert "Skipped" in _compile(src, out, ["-I", "rootA"], cache, cwd=tmp_path)
    assert "Skipped" in _compile(src, out, ["-I", "rootA/"], cache, cwd=tmp_path)


def test_missing_root_that_appears_later_recompiles(two_roots, tmp_path):
    """A root that does not exist yet cannot be canonicalised; when it is
    created later it must not fingerprint the same as before."""
    src, roots = two_roots
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    late = tmp_path / "late"
    rp = f"{late}:{roots['rootB']}"
    _compile(src, out, [], cache, ritz_path=rp)
    _assert_tag(out.read_text(), 202)
    shutil.copytree(roots["rootA"], late)
    _compile(src, out, [], cache, ritz_path=rp)
    _assert_tag(out.read_text(), 101)
