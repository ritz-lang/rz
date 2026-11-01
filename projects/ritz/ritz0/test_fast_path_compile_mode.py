#!/usr/bin/env python3
"""ritz0's "Skipped … (unchanged)" fast path must respect the compile mode (AGAST #2020).

`compile_file` skips a compile, and keeps the existing output, when the output
is newer than the source and the sig's source and import hashes still match.
Nothing in those checks says the output was built in *this* mode, so a
recompile into the same path with a different flag kept the other mode's IR:
`--no-runtime` kept `_start`, test mode kept no test table, `--target` kept the
old triple, `--target-os` kept the other OS's items, and a different import root
(RITZ_PATH / --sources / --project-root / --deps) kept the module the *old*
root resolved.  Skipping also skipped the checks: a compile with ownership
checks on reported success for a file whose last compile had them off.

Each test runs ritz0's real CLI (`ritz0_inproc.run_ritz0`, a fork per compile,
no result cache) against a private ``RITZ_CACHE_DIR``.  A mode's expected IR is
a cold compile of that mode (a fresh sig cache) into its own path.
"""

import json
import os
import time
from pathlib import Path

import pytest

from emitter.fn_cache import (
    build_outputs, check_output_entry, compile_mode_key, source_file_hash,
)
from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent

# Every mode flag compile_file reads that changes the IR it writes.  Each one
# yields IR distinct from the default for MODE_SRC (checked by
# test_every_mode_changes_the_ir, so a flag that stops mattering is noticed).
MODE_SRC = """\
import ritzlib.sys

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
    "no_runtime": ["--no-runtime"],
    "test_mode": ["--test-table"],
    "target": ["--target", "x86_64-none-elf"],
    "target_os": ["--target-os", "harland"],
}

# Ordered pairs (a, b), a != b: compile a, then b into the same output path.
# Covers both orders of every pair.
MODE_PAIRS = [(a, b) for a in MODES for b in MODES if a != b]


def _env(cache_dir: Path, ritz_path) -> dict:
    env = dict(os.environ)
    env["RITZ_PATH"] = os.pathsep.join(str(p) for p in ritz_path)
    env["RITZ_CACHE_DIR"] = str(cache_dir)
    return env


def _ritz0(src: Path, out: Path, flags, cache_dir: Path, ritz_path=(RITZ_ROOT,)):
    return run_ritz0(
        [str(src), "-o", str(out), *flags],
        cwd=str(src.parent),
        env=_env(cache_dir, ritz_path),
        timeout=300,
    )


def _compile(src: Path, out: Path, flags, cache_dir: Path, **kw) -> str:
    proc = _ritz0(src, out, flags, cache_dir, **kw)
    assert proc.returncode == 0, f"ritz0 {flags} failed:\n{proc.stdout}\n{proc.stderr}"
    return proc.stdout


def _cold(src: Path, flags, tmp_path: Path, tag: str, **kw) -> str:
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


@pytest.mark.integration
def test_every_mode_changes_the_ir(mode_src, tmp_path):
    """Precondition: each mode's cold IR differs from every other mode's."""
    irs = {m: _cold(mode_src, f, tmp_path, m) for m, f in MODES.items()}
    assert len(set(irs.values())) == len(MODES), (
        "two modes produce identical IR; MODE_SRC no longer tells them apart"
    )


@pytest.mark.integration
@pytest.mark.parametrize("first,second", MODE_PAIRS, ids=[f"{a}-then-{b}" for a, b in MODE_PAIRS])
def test_mode_switch_into_same_output_matches_cold(mode_src, tmp_path, first, second):
    """Compile mode A then mode B into one path: the result is B's cold IR."""
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    _compile(mode_src, out, MODES[first], cache)
    assert out.read_text() == _cold(mode_src, MODES[first], tmp_path, first)

    _compile(mode_src, out, MODES[second], cache)
    assert out.read_text() == _cold(mode_src, MODES[second], tmp_path, second), (
        f"recompiling with {MODES[second]} kept the {first} output"
    )

    # And back again: the sig must not now be stuck on `second`'s mode.
    _compile(mode_src, out, MODES[first], cache)
    assert out.read_text() == _cold(mode_src, MODES[first], tmp_path, first)


@pytest.mark.integration
def test_same_mode_same_output_still_skips(mode_src, tmp_path):
    """The fast path itself survives: an unchanged recompile is a skip."""
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    for flags in MODES.values():
        _compile(mode_src, out, flags, cache)
        before = out.read_text()
        stdout = _compile(mode_src, out, flags, cache)
        assert "Skipped" in stdout, f"{flags}: unchanged recompile did not skip"
        assert out.read_text() == before


@pytest.mark.integration
def test_other_mode_into_other_output_does_not_vouch_for_this_one(mode_src, tmp_path):
    """The sig is per source, not per output: mode B into b.ll, then mode B
    into a.ll (which holds mode A's IR) must not skip."""
    a, b = tmp_path / "a.ll", tmp_path / "b.ll"
    cache = tmp_path / "cache"
    _compile(mode_src, a, MODES["default"], cache)
    _compile(mode_src, b, MODES["no_runtime"], cache)
    _compile(mode_src, a, MODES["no_runtime"], cache)
    assert a.read_text() == _cold(mode_src, MODES["no_runtime"], tmp_path, "nr")


@pytest.mark.integration
def test_output_rewritten_behind_the_sig_is_recompiled(mode_src, tmp_path):
    """An output the sig did not write (here: clobbered) is not vouched for."""
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    _compile(mode_src, out, [], cache)
    good = out.read_text()
    out.write_text("; not ritz0's output\n")
    stdout = _compile(mode_src, out, [], cache)
    assert "Skipped" not in stdout
    assert out.read_text() == good


# --- Import resolution: a different root resolves a different module ---------

LIB_SRC = """\
pub const LIB_TAG: i32 = {tag}
"""

USE_LIB_SRC = """\
import ritzlib.sys
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


def _switch_roots(src, tmp_path, kw_a, kw_b):
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    flags_a, ritz_a = kw_a
    flags_b, ritz_b = kw_b
    _compile(src, out, flags_a, cache, ritz_path=ritz_a)
    assert "ret i32 101" in out.read_text()
    _compile(src, out, flags_b, cache, ritz_path=ritz_b)
    ir = out.read_text()
    assert "ret i32 202" in ir, "recompiling against rootB kept rootA's import"
    assert ir == _cold(src, flags_b, tmp_path, "b", ritz_path=ritz_b)


@pytest.mark.integration
def test_ritz_path_switch_recompiles(two_roots, tmp_path):
    src, roots = two_roots
    _switch_roots(
        src, tmp_path,
        ([], (roots["rootA"], RITZ_ROOT)),
        ([], (roots["rootB"], RITZ_ROOT)),
    )


@pytest.mark.integration
def test_sources_switch_recompiles(two_roots, tmp_path):
    src, roots = two_roots
    _switch_roots(
        src, tmp_path,
        (["--sources", json.dumps([str(roots["rootA"])])], (RITZ_ROOT,)),
        (["--sources", json.dumps([str(roots["rootB"])])], (RITZ_ROOT,)),
    )


@pytest.mark.integration
def test_project_root_switch_recompiles(two_roots, tmp_path):
    src, roots = two_roots
    _switch_roots(
        src, tmp_path,
        (["--project-root", str(roots["rootA"])], (RITZ_ROOT,)),
        (["--project-root", str(roots["rootB"])], (RITZ_ROOT,)),
    )


@pytest.mark.integration
def test_deps_switch_recompiles(two_roots, tmp_path):
    src, roots = two_roots

    def deps(root):
        return ["--deps", json.dumps({"shared": {"path": str(root), "sources": ["shared"]}})]

    _switch_roots(
        src, tmp_path,
        (deps(roots["rootA"]), (RITZ_ROOT,)),
        (deps(roots["rootB"]), (RITZ_ROOT,)),
    )


# --- Checks: a skip must not stand in for a check the last compile skipped ---

MOVE_ERROR_SRC = """\
import ritzlib.sys

struct Point
    x: i32
    y: i32

fn takes_point(p: Point) -> i32
    return p.x

fn main() -> i32
    var p: Point = Point { x: 1, y: 2 }
    takes_point(p)
    return p.x
"""


@pytest.mark.integration
def test_ownership_check_runs_after_unchecked_compile(tmp_path):
    src = tmp_path / "src" / "main.ritz"
    src.parent.mkdir()
    src.write_text(MOVE_ERROR_SRC)
    out = tmp_path / "a.ll"
    cache = tmp_path / "cache"
    _compile(src, out, ["--no-check-ownership"], cache)
    proc = _ritz0(src, out, [], cache)
    assert proc.returncode != 0, (
        f"ownership-checked compile skipped the check:\n{proc.stdout}"
    )
    assert "use of moved value" in proc.stderr


# --- Entries written under other sources must not survive ---------------------


@pytest.mark.integration
def test_entry_from_older_source_does_not_vouch_after_revert(mode_src, tmp_path):
    """v1 -> a.ll, v2 -> b.ll, v1 -> c.ll, then v1 -> b.ll (b.ll holds v2's IR,
    newer than the source): b's entry was written for v2 and must be gone."""
    cache = tmp_path / "cache"
    a, b, c = (tmp_path / f"{n}.ll" for n in "abc")
    v1 = MODE_SRC
    v2 = MODE_SRC.replace("const OS_TAG: i32 = 11", "const OS_TAG: i32 = 33")
    _compile(mode_src, a, [], cache)
    mode_src.write_text(v2)
    _compile(mode_src, b, [], cache)
    mode_src.write_text(v1)
    _compile(mode_src, c, [], cache)
    future = time.time() + 3600
    os.utime(b, (future, future))
    stdout = _compile(mode_src, b, [], cache)
    assert "Skipped" not in stdout, "b.ll (v2's IR) was vouched for under v1"
    assert "ret i32 11" in b.read_text()


# --- Unit: the sig helpers ---------------------------------------------------


@pytest.mark.unit
def test_compile_mode_key_is_canonical():
    assert compile_mode_key({"a": 1, "b": [2]}) == compile_mode_key({"b": [2], "a": 1})
    assert compile_mode_key({"a": 1}) != compile_mode_key({"a": 2})


def _sig(src, imports, outputs):
    return {"source_hash": source_file_hash(src), "import_hashes": imports,
            "outputs": outputs, "functions": {}}


@pytest.mark.unit
def test_build_outputs_keeps_entries_for_same_inputs(tmp_path):
    a, b = tmp_path / "a.ll", tmp_path / "b.ll"
    a.write_text("A")
    old = _sig("src", {"i": "h"}, {str(a): {"mode": "m1", "ir_hash": "x"}})
    out = build_outputs(old, "src", {"i": "h"}, b, "m2", "B")
    assert set(out) == {str(a), os.path.realpath(b)}
    assert out[os.path.realpath(b)] == {"mode": "m2", "ir_hash": source_file_hash("B")}


@pytest.mark.unit
@pytest.mark.parametrize("src,imports", [("changed", {"i": "h"}), ("src", {"i": "h2"})],
                         ids=["source-changed", "imports-changed"])
def test_build_outputs_drops_entries_for_other_inputs(tmp_path, src, imports):
    a, b = tmp_path / "a.ll", tmp_path / "b.ll"
    a.write_text("A")
    old = _sig("src", {"i": "h"}, {str(a): {"mode": "m1", "ir_hash": "x"}})
    assert set(build_outputs(old, src, imports, b, "m2", "B")) == {os.path.realpath(b)}


@pytest.mark.unit
def test_build_outputs_drops_missing_files(tmp_path):
    gone, b = tmp_path / "gone.ll", tmp_path / "b.ll"
    old = _sig("src", {}, {str(gone): {"mode": "m", "ir_hash": "x"}})
    assert set(build_outputs(old, "src", {}, b, "m", "B")) == {os.path.realpath(b)}


@pytest.mark.unit
def test_check_output_entry(tmp_path):
    out = tmp_path / "a.ll"
    out.write_text("IR")
    sig = {"outputs": {os.path.realpath(out): {"mode": "m", "ir_hash": source_file_hash("IR")}}}
    assert check_output_entry(sig, out, "m")
    assert not check_output_entry(sig, out, "other-mode")
    assert not check_output_entry(sig, tmp_path / "b.ll", "m")
    assert not check_output_entry({"functions": {}}, out, "m"), "pre-#2020 sig vouches for nothing"
    assert not check_output_entry(None, out, "m")
    out.write_text("IR, rewritten")
    assert not check_output_entry(sig, out, "m")
