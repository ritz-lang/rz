#!/usr/bin/env python3
"""Self-tests for tools/smoke.py — the `make smoke` tier (AGAST #1803).

The smoke tier exists to say "fully broken" in under two minutes, so the
properties worth holding it to are the ones that would make it say "fine"
instead:

  * the canary list cannot rot silently: a canary renamed or deleted on disk
    fails the self-check, and so does a list shrunk below the floor (the
    "discovered, not listed, with a floor" rule from #1371, applied to a
    deliberately short list);
  * a failing step stops the run, and later steps do not run;
  * every step reports its wall time, and the summary names the failure;
  * the pytest subset is real: it collects hundreds of in-process tests,
    none of which needs a compiler build;
  * it is wired in where the ticket says: first in main.yml's bootstrap job,
    first in run-gate.sh's default command, and in the rz-iterate briefing.

Run with:
    python3 -m pytest projects/ritz/tools/test_smoke.py -q
"""

from __future__ import annotations

import importlib.util
import io
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
RITZ_ROOT = HERE.parent
REPO_ROOT = RITZ_ROOT.parent.parent
sys.path.insert(0, str(HERE))

import ci_local  # noqa: E402
import run_regression_matrix as matrix  # noqa: E402
import smoke  # noqa: E402


def _load_ritz0_conftest():
    spec = importlib.util.spec_from_file_location(
        "ritz0_conftest_for_smoke", RITZ_ROOT / "ritz0" / "conftest.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# Canary list
# --------------------------------------------------------------------------

@pytest.mark.unit
def test_load_canaries_ignores_comments_and_blanks(tmp_path):
    f = tmp_path / "c.txt"
    f.write_text("# header\n\ntest_a\n  test_b   # why b\n#test_c\n")
    assert smoke.load_canaries(f) == ["test_a", "test_b"]


@pytest.mark.unit
def test_canary_problems_clean_list_is_ok():
    assert smoke.canary_problems(["a", "b"], ["a", "b", "c"], floor=2) == []


@pytest.mark.unit
def test_canary_renamed_away_is_reported_by_name():
    # Negative control (d): a canary that is no longer discovered on disk.
    probs = smoke.canary_problems(["a", "gone"], ["a", "b"], floor=1)
    assert len(probs) == 1
    assert "gone" in probs[0]


@pytest.mark.unit
def test_canary_list_below_floor_fails():
    probs = smoke.canary_problems(["a"], ["a", "b"], floor=2)
    assert any("floor" in p for p in probs)


@pytest.mark.unit
def test_canary_duplicate_fails():
    probs = smoke.canary_problems(["a", "a"], ["a"], floor=1)
    assert any("twice" in p for p in probs)


@pytest.mark.unit
def test_canary_not_a_test_file_fails():
    # NOT_TESTS entries are discovered as *.ritz but never run by the matrix.
    probs = smoke.canary_problems(["test_import_lib"], ["a"], floor=1)
    assert any("test_import_lib" in p for p in probs)


@pytest.mark.unit
def test_canary_regex_selects_exactly_the_list():
    rx = re.compile(smoke.canary_regex(["test_level1", "test_a.b"]))
    names = ["test_level1", "test_level10", "test_a.b", "test_aXb", "xtest_level1"]
    assert [n for n in names if rx.search(n)] == ["test_level1", "test_a.b"]


@pytest.mark.unit
def test_checked_in_canary_list_passes_against_disk():
    canaries = smoke.load_canaries(smoke.CANARY_FILE)
    assert smoke.canary_problems(canaries, matrix.discover_test_files()) == []
    assert len(canaries) >= smoke.CANARY_FLOOR >= 8


@pytest.mark.unit
def test_canaries_are_not_expected_failures():
    # A canary that is allowed to fail cannot report "broken".
    canaries = set(smoke.load_canaries(smoke.CANARY_FILE))
    for _compiler, key in matrix.EXPECTED_FAILURES:
        assert key.partition("::")[0] not in canaries, key


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

@pytest.mark.unit
def test_run_steps_stops_at_first_failure_and_reports_times():
    ran = []

    def ok(name):
        return lambda: ran.append(name) or 0

    steps = [
        smoke.Step("first", 5, ok("first")),
        smoke.Step("second", 5, lambda: ran.append("second") or 3),
        smoke.Step("third", 5, ok("third")),
    ]
    out = io.StringIO()
    rc = smoke.run_steps(steps, out=out)
    text = out.getvalue()
    assert rc != 0
    assert ran == ["first", "second"]
    assert re.search(r"first\s.*\d+\.\d s", text)
    assert re.search(r"second\s.*FAIL", text)
    assert "third" in text and "not run" in text


@pytest.mark.unit
def test_run_steps_all_green_returns_zero():
    out = io.StringIO()
    rc = smoke.run_steps([smoke.Step("only", 1, lambda: 0)], out=out)
    assert rc == 0
    assert "smoke passed" in out.getvalue()


@pytest.mark.unit
def test_run_steps_counts_an_exception_as_failure():
    def boom():
        raise RuntimeError("kaput")
    out = io.StringIO()
    assert smoke.run_steps([smoke.Step("x", 1, boom)], out=out) != 0
    assert "kaput" in out.getvalue()


@pytest.mark.unit
def test_step_order_is_the_design():
    # fast-iteration.md §4: cheapest, most-likely-broken first.
    assert [s.name for s in smoke.build_steps()] == [
        "check-no-s-strings", "regen-check", "pytest -m smoke",
        "build ritz1", "canary matrix", "ritz1 self-compile",
    ]


@pytest.mark.unit
def test_budgets_sum_within_two_minutes():
    assert sum(s.budget for s in smoke.build_steps()) <= 120


@pytest.mark.integration
def test_self_compile_rejects_a_compiler_that_emits_garbage(tmp_path):
    fake = tmp_path / "fake_ritz1"
    fake.write_text('#!/bin/sh\n# args: <src> -o <out>\necho "not llvm" > "$3"\n')
    fake.chmod(0o755)
    rc = smoke.self_compile(fake, RITZ_ROOT / "ritz1" / "src" / "tokens_gen.ritz",
                            out=io.StringIO())
    assert rc != 0


@pytest.mark.integration
def test_self_compile_rejects_an_empty_module(tmp_path):
    # Valid IR with no function bodies is a compiler that dropped everything.
    fake = tmp_path / "fake_ritz1"
    fake.write_text('#!/bin/sh\nprintf "; empty\\n" > "$3"\n')
    fake.chmod(0o755)
    rc = smoke.self_compile(fake, RITZ_ROOT / "ritz1" / "src" / "tokens_gen.ritz",
                            out=io.StringIO())
    assert rc != 0


# --------------------------------------------------------------------------
# The ritz0 `smoke` marker
# --------------------------------------------------------------------------

@pytest.mark.unit
def test_smoke_files_all_exist():
    conftest = _load_ritz0_conftest()
    assert conftest.SMOKE_FILES, "SMOKE_FILES is empty"
    for rel in conftest.SMOKE_FILES:
        assert (RITZ_ROOT / "ritz0" / rel).is_file(), rel


@pytest.mark.integration
def test_smoke_marker_selects_in_process_tests_only():
    conftest = _load_ritz0_conftest()
    files = sorted(conftest.SMOKE_FILES)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-m", "smoke",
         "-p", "no:cacheprovider", *files],
        cwd=RITZ_ROOT / "ritz0", capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    ids = [ln for ln in proc.stdout.splitlines() if "::" in ln]
    assert len(ids) >= 600, f"only {len(ids)} smoke tests collected"
    # Every listed file contributes: a file whose tests all fell out of the
    # marker is a rotted entry.
    for rel in files:
        assert any(i.startswith(rel + "::") for i in ids), f"{rel}: no smoke tests"
    # Nothing selected by -m smoke needs ritz1 built or is an integration test.
    proc2 = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-m", "smoke and integration", "-p", "no:cacheprovider", *files],
        cwd=RITZ_ROOT / "ritz0", capture_output=True, text=True, timeout=300)
    assert not [ln for ln in proc2.stdout.splitlines() if "::" in ln]


@pytest.mark.unit
def test_smoke_marker_excludes_ritz1_fixture_users():
    conftest = _load_ritz0_conftest()

    class Item:
        def __init__(self, path, fixtures, markers=()):
            self.path = Path(path)
            self.fixturenames = list(fixtures)
            self._markers = set(markers)

        def get_closest_marker(self, name):
            return name if name in self._markers else None

    root = RITZ_ROOT / "ritz0"
    listed = root / conftest.SMOKE_FILES[0]
    assert conftest.is_smoke_item(Item(listed, ["tmp_path"]))
    assert not conftest.is_smoke_item(Item(listed, ["ritz1_bin"]))
    assert not conftest.is_smoke_item(Item(listed, ["ritz_start"]))
    assert not conftest.is_smoke_item(Item(listed, [], ["integration"]))
    assert not conftest.is_smoke_item(Item(root / "test_nonexistent_x.py", []))


# --------------------------------------------------------------------------
# run_regression_matrix: one run, two compilers
# --------------------------------------------------------------------------

@pytest.mark.unit
def test_matrix_accepts_a_compiler_list():
    assert matrix.parse_compilers("ritz0,ritz1") == ["ritz0", "ritz1"]
    assert matrix.parse_compilers("ritz1,ritz0") == ["ritz0", "ritz1"]
    assert matrix.parse_compilers("ritz0, ritz1_selfhosted") == ["ritz0", "ritz1_selfhosted"]
    assert matrix.parse_compilers("ritz1") == ["ritz1"]
    assert matrix.parse_compilers("all") == ["ritz0", "ritz1", "ritz1_selfhosted"]
    for bad in ("ritz0,ritz9", "", ","):
        with pytest.raises(ValueError):
            matrix.parse_compilers(bad)


# --------------------------------------------------------------------------
# Wiring
# --------------------------------------------------------------------------

@pytest.mark.unit
def test_makefile_has_smoke_target():
    text = (RITZ_ROOT / "Makefile").read_text()
    assert re.search(r"^smoke:", text, re.M)
    assert re.search(r"^\t.*tools/smoke\.py", text, re.M)


@pytest.mark.unit
def test_smoke_is_first_gate_step_in_ci_bootstrap():
    gates = [s for s in ci_local.load_steps()
             if s.job == "bootstrap" and not s.is_setup]
    assert gates[0].name == "Smoke"
    assert gates[0].run.strip() == "make smoke"
    assert gates[0].workdir == "projects/ritz"


@pytest.mark.unit
def test_run_gate_runs_smoke_before_ci_local():
    text = (REPO_ROOT / ".claude" / "skills" / "rz-iterate" / "run-gate.sh").read_text()
    m = re.search(r'^CMD="\$\{RZ_GATE_CMD:-(.*)\}"$', text, re.M)
    assert m, "default RZ_GATE_CMD not found"
    cmd = m.group(1).replace('\\"', '"')  # as bash expands the default
    assert "make -C projects/ritz smoke &&" in cmd
    assert cmd.index("smoke") < cmd.index("ci-local")
    # Still a clean gate: the wipe comes before anything builds.
    assert cmd.index("rm -rf") < cmd.index("smoke")
    # AGAST #1897: ci-local must not run main.yml's Smoke step a second time.
    assert re.search(r'ci-local ARGS="[^"]*--skip Smoke\b[^"]*"', cmd), cmd
    assert "--fail-fast" in cmd[cmd.index("ci-local"):]


@pytest.mark.unit
def test_rz_iterate_briefing_asks_for_smoke_before_gate():
    text = (REPO_ROOT / ".claude" / "skills" / "rz-iterate" / "SKILL.md").read_text()
    gate_at = text.index("**Gate that commit**")
    smoke_at = text.find("make -C projects/ritz smoke")
    assert 0 <= smoke_at < gate_at
