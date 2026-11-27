"""`make tools-ratchets` runs ritz0's in-process tests too (AGAST #4622).

Train 2026-11-24 (train-2-9c21de9cc675-1@bangerang.log) went red on
ritz0/tests/test_ritz1_sema_walk_layout.py::test_check_calls_one_paragraph_each,
a test that reads ritz1's source and compiles nothing.  The room that broke it
had run `make tools-ratchets` (#4587), which collected tools/ only, so every
source ratchet under ritz0/tests was invisible to a room's smoke.

The fix selects by rule rather than by list, so a new ratchet cannot drift
out: ritz0/conftest.py marks `inproc` every test that is not `integration`
(spawn_guard fails such a test that starts a process or runs ritz0) and asks
for no fixture that builds ritz1; the target runs `-m inproc` over the whole
ritz0 suite.  These tests hold the target to that and check the rule picks up
the ratchets that went unseen.
"""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

RITZ = Path(__file__).resolve().parent.parent
RITZ0 = RITZ / "ritz0"

pytestmark = pytest.mark.integration  # starts make and a nested pytest


def _pytest_lines() -> list[str]:
    """The pytest command lines `make tools-ratchets` would run."""
    out = subprocess.run(
        ["make", "-n", "-s", "tools-ratchets"],
        cwd=RITZ, capture_output=True, text=True, check=True, timeout=60,
    ).stdout
    # -n prints recursive $(MAKE) lines and runs them dry, so their
    # commands appear here too.
    return [ln for ln in out.splitlines() if re.search(r"-m pytest\b", ln)]


def _ritz0_line() -> str:
    lines = [ln for ln in _pytest_lines() if re.search(r"\bcd ritz0\b", ln)]
    assert len(lines) == 1, f"want one ritz0 pytest in tools-ratchets: {_pytest_lines()}"
    return lines[0]


def test_ritz0_half_runs_every_inproc_test():
    """One pytest in ritz0/, `-m inproc`, no path: the whole suite by rule."""
    words = shlex.split(_ritz0_line().split("&&", 1)[1])
    # Everything after `-m pytest`: pytest's own arguments.
    words = words[words.index("pytest") + 1:]
    assert "-m" in words and words[words.index("-m") + 1] == "inproc", words
    # No file or directory argument narrows it: a list would drift.
    paths = [w for w in words if "/" in w or w.endswith(".py")]
    assert paths == [], f"ritz0 half names paths {paths}; select by marker only"
    # Parallel, but building nothing (AGAST #4672): without --no-ritz1-build
    # the xdist controller builds ritz1 first (conftest items 4, 14), ~15 s
    # no inproc test uses.  Serial took ~60 s.
    assert "-n" in words and "xdist" in words, words
    assert "--no-ritz1-build" in words, words


def test_incremental_deps_build_test_is_not_a_ratchet():
    """test_ritz1_incremental_deps.py builds ritz1 four times (~50 s): a build
    test, not a source ratchet (AGAST #4672).  It stays in tools-unit, which
    runs all of tools/."""
    tools = [ln for ln in _pytest_lines() if "tools/test_" in ln]
    assert tools and all("test_ritz1_incremental_deps" not in ln for ln in tools), tools
    assert any("tools/test_ritz1_ratchet.py" in ln for ln in tools), tools
    assert (RITZ / "tools" / "test_ritz1_incremental_deps.py").exists()


def test_standard_caller_pins_are_a_ratchet():
    """tools/test_standard_callers.py (#4636's down-only raw-API caller pins)
    caught two cars whose smoke ran tools-ratchets but not tools-unit
    (#4653 +29, #4654 +28 callers), so neither room saw it (AGAST #4672)."""
    tools = [ln for ln in _pytest_lines() if "tools/test_" in ln]
    assert any("tools/test_standard_callers.py" in ln for ln in tools), tools


def test_standard_pins_are_ratchets():
    """tools/test_standard_pins/ (the down-only C-shape pins over ritzlib,
    test_cshape_*.py) ran in tools-unit alone: #4820's car went 72>71 and
    83>82, precheck said EXIT=0 and train-3-3bd3947b7953-1 went red at
    [tools/ unit tests] (AGAST #4904).  The dir is in by glob, so a new pin
    file is in too."""
    tools = [ln for ln in _pytest_lines() if "tools/test_" in ln]
    assert len(tools) == 1, tools
    words = tools[0].split()
    pins = sorted((RITZ / "tools" / "test_standard_pins").glob("test_*.py"))
    assert any(p.name.startswith("test_cshape_") for p in pins), pins
    missing = [p.name for p in pins if f"tools/test_standard_pins/{p.name}" not in words]
    assert missing == [], f"tools-ratchets misses {missing}"


#   The tree guards every smoke runs (AGAST #4902, #4907): #4773's car
# tracked ritz1/src/monomorph.ritz.orig, its ritz1-only smoke planned no
# tools-unit, and the train gate went red on the leftover guard.  #4833
# (projects/buddhafinger) hit the same gap on the bin-link and fixed-/tmp
# guards.  #4907's audit then swept in the rest of the class: every other
# tools/ test that reads tracked files across projects/ (not just compiler
# sources), needs no build, and runs in low seconds alone - the repo-wide
# siblings of the leftover guard in test_project_root_hygiene.py (one shared
# `git ls-files -s` walk), the convenience-link sibling of the [[bin]] guard,
# and the manifest/syscall/stray-tests/repo-cleanup/account-name checks.
# ~3.3 s of that is the liveness walk; all 19 together are well under 5 s on
# one worker.
TREE_GUARDS = [
    "tools/test_project_root_hygiene.py::test_no_merge_or_editor_leftovers_tracked",
    "tools/test_project_root_hygiene.py::test_no_elf_tracked_in_repo",
    "tools/test_project_root_hygiene.py::test_elf_fixtures_exist",
    "tools/test_project_root_hygiene.py::test_no_compiler_output_ir_tracked",
    "tools/test_project_root_hygiene.py::test_ir_fixtures_exist",
    "tools/test_project_root_hygiene.py::test_walk_reads_tracked_files",
    "tools/test_project_root_hygiene.py::test_no_tracked_symlink_into_a_build_dir",
    "tools/test_check_liveness.py::test_real_tree_is_live",
    "tools/test_bin_links_ignored.py::test_every_bin_link_is_ignored",
    "tools/test_valet_http_tmp_paths.py::test_no_fixed_tmp_path_in_tests",
    "tools/test_convenience_links_ignored.py::test_every_convenience_link_is_ignored",
    "tools/test_legacy_printers_deleted.py::test_no_workspace_code_uses_a_legacy_printer",
    "tools/test_package_syscall_numbers.py::test_no_package_redeclares_syscall_numbers_beside_ritzlib_sys",
    "tools/test_package_syscall_numbers.py::test_no_package_passes_a_bare_syscall_number_beside_ritzlib_sys",
    "tools/test_manifest_schema.py::test_every_committed_manifest_validates",
    "tools/test_manifest_schema.py::test_every_test_sources_dir_exists",
    "tools/test_build_stray_tests_dir.py::test_no_package_in_the_repo_has_stray_tests",
    "tools/test_repo_cleanup.py::test_no_transcripts_or_generated_assets_are_tracked",
    "tools/test_room_account.py::test_repo_names_no_account_dirs",
]


def test_tree_guards_are_ratchets():
    tools = " ".join(ln for ln in _pytest_lines() if "tools/test_" in ln)
    assert [g for g in TREE_GUARDS if g not in tools.split()] == [], tools


def test_tree_guards_still_exist():
    """A renamed guard would leave tools-ratchets naming nothing: pytest
    errors on a missing node id, but say which here."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--co", "-q", *TREE_GUARDS],
        cwd=RITZ, check=False, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    # Ids print relative to tools/'s rootdir (its pytest.ini).
    got = {ln for ln in proc.stdout.splitlines() if "::" in ln}
    assert {g.removeprefix("tools/") for g in TREE_GUARDS} <= got, proc.stdout[-2000:]


def test_tools_and_ritz0_are_separate_pytests():
    """tools/ and ritz0/ in one pytest fails tools tests (read guard, #4032)."""
    for ln in _pytest_lines():
        assert not ("tools/" in ln and re.search(r"\bcd ritz0\b", ln)), ln
    assert any("tools/test_" in ln for ln in _pytest_lines()), _pytest_lines()


# The ratchets the train failed on or the ticket named, and tests in the same
# files the rule must leave out (they compile, or ask for ritz1).
IN = [
    "tests/test_ritz1_sema_walk_layout.py::test_check_calls_one_paragraph_each",
    "tests/test_ritz1_sema_walk_layout.py::test_imports_sorted_one_paragraph_each",
    "tests/test_harland_fault_hardening.py::test_pmm_reserves_the_whole_kernel_image",
    "tests/test_source_order.py::test_main_file_is_last",
    "tests/test_ritz1_type_layout_table.py::test_layout_helper_matches_known_answers",
]
OUT = [
    "tests/test_harland_fault_hardening.py::test_pmm_refuses_frames_past_the_ram_it_manages",
    "tests/test_source_order.py::test_emitted_ir_identical_across_hash_seeds",
    "tests/test_ritz1_type_layout_table.py::test_struct_with_u16_array_fits_its_sizeof",
]


def test_inproc_marker_selects_the_source_ratchets():
    files = sorted({n.split("::")[0] for n in IN + OUT})
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--disable-plugin-autoload",
         "-p", "no:cacheprovider", "--co", "-q", "-m", "inproc", *files],
        cwd=RITZ0, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    got = {ln.split("[")[0] for ln in proc.stdout.splitlines() if "::" in ln}
    assert [n for n in IN if n not in got] == [], proc.stdout[-2000:]
    assert [n for n in OUT if n in got] == []
