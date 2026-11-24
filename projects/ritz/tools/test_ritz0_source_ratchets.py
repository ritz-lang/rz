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
    # Serial: under xdist the controller builds ritz1 first (conftest item 4).
    assert "-n" not in words, words


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
