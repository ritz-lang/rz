"""Tests for tools/example_tests.py, the gate over examples/**/test/*.ritz
(AGAST #3729).

Only the verdict logic is exercised here: nothing is compiled. The sweep
itself runs as its own ci-local step ("Example [[test]] suites").
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import example_tests as et

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def judge(disk, ran, known=None):
    return et.judge(set(disk), dict(ran), dict(known or {}))


class TestJudge:
    def test_all_pass_is_green(self):
        assert judge({"a/test/t.ritz"}, {"a/test/t.ritz": "pass"}) == []

    @pytest.mark.parametrize(
        "status", ["fail", "error", "empty", "timeout", "build-failed"]
    )
    def test_unlisted_failure_gates(self, status):
        problems = judge({"a/test/t.ritz"}, {"a/test/t.ritz": status})
        assert len(problems) == 1
        assert "a/test/t.ritz" in problems[0] and status in problems[0]

    def test_known_failure_is_excused(self):
        assert (
            judge(
                {"a/test/t.ritz"},
                {"a/test/t.ritz": "error"},
                {"a/test/t.ritz": "#1 broken"},
            )
            == []
        )

    def test_known_failure_that_passes_is_stale(self):
        # Strict xpass: an excuse must not outlive the failure it excuses.
        problems = judge(
            {"a/test/t.ritz"}, {"a/test/t.ritz": "pass"}, {"a/test/t.ritz": "#1 broken"}
        )
        assert len(problems) == 1 and "stale" in problems[0]

    def test_known_failure_for_a_deleted_file_is_stale(self):
        problems = judge(set(), {}, {"gone/test/t.ritz": "#1 broken"})
        assert len(problems) == 1 and "gone/test/t.ritz" in problems[0]

    def test_floor_file_on_disk_that_did_not_run_gates(self):
        # The ticket's floor: fewer files run than exist on disk is red,
        # e.g. a test/ dir with no ritz.toml, which discovery never sees.
        problems = judge(
            {"a/test/t.ritz", "orphan/test/u.ritz"}, {"a/test/t.ritz": "pass"}
        )
        assert len(problems) == 1
        assert "orphan/test/u.ritz" in problems[0]
        assert "did not run" in problems[0]

    def test_known_failing_does_not_excuse_not_running(self):
        problems = judge({"a/test/t.ritz"}, {}, {"a/test/t.ritz": "#1 broken"})
        assert any("did not run" in p for p in problems)


class TestDiskFloor:
    def test_disk_walk_is_independent_of_package_discovery(self, tmp_path):
        (tmp_path / "pkg" / "test").mkdir(parents=True)
        (tmp_path / "pkg" / "ritz.toml").write_text("[package]\nname='p'\n")
        (tmp_path / "pkg" / "test" / "t.ritz").write_text("")
        (tmp_path / "orphan" / "test").mkdir(parents=True)
        (tmp_path / "orphan" / "test" / "u.ritz").write_text("")
        (tmp_path / "pkg" / "build" / "test").mkdir(parents=True)
        (tmp_path / "pkg" / "build" / "test" / "gen.ritz").write_text("")
        assert et.test_files_on_disk(tmp_path) == {
            "pkg/test/t.ritz",
            "orphan/test/u.ritz",
        }

    def test_real_tree_has_test_files(self):
        # A walk that finds nothing would pass every floor vacuously.
        assert len(et.test_files_on_disk(EXAMPLES)) >= 72


def test_gate_runs_it():
    # A gate that is in no workflow is the bug this file exists for. The
    # bootstrap job is what ci-local (and so every room gate) runs.
    import ci_local

    steps = [s for s in ci_local.load_steps() if s.job == "bootstrap"]
    assert any("make example-tests" in s.run for s in steps)
