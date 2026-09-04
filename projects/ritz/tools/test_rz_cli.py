"""Tests for the workspace-level `rz` CLI (AGAST #1324).

Why these tests live here: `rz` sits at the workspace root with no test
suite of its own, while CI's bootstrap job already runs `make tools-unit`
(pytest over projects/ritz/tools/). Importing the script by path from here
puts the gate logic under the only pytest umbrella that actually runs in CI.

What broke and what these tests pin down:

1. `rz test --all` in CI printed every "Testing: <project>" banner
   back-to-back with no diagnostics between them. The diagnostics existed —
   they were emitted by the build.py children — but the parent's banners
   were block-buffered (stdout was a pipe) while each child flushed at
   exit, so the log showed orphaned diagnostics followed by a wall of
   banners. The fix is (a) flush banners before spawning the child and
   (b) run children with PYTHONUNBUFFERED so grandchild output interleaves
   correctly too. `_child_env` is the tested seam for (b).

2. The gate itself: build-all/test-all had been red for 12+ runs, which is
   a disabled gate. The replacement is an explicit, named, per-project
   known-failing list in rz.toml ([ci.known_failing.build] ONLY — there is
   deliberately no .test list; see TestKnownFailingConfig), each entry
   mapping project -> justification citing an AGAST task, validated by rz
   at load time. `gate_outcome` is the pure classification: hard failures
   gate, known failures are advisory-but-visible, and a known-failing
   project that PASSES also gates (strict xpass — stale entries are forced
   out; new entries are a review-time concern).
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

# rz is an extensionless executable script three levels up from tools/.
RZ_PATH = Path(__file__).resolve().parents[3] / "rz"

# A justification must cite a task NUMBER. A bare "#" is not a reference.
AGAST_REF = re.compile(r"#\d+")


@pytest.fixture(scope="module")
def rz():
    spec = importlib.util.spec_from_loader(
        "rz_cli", importlib.machinery.SourceFileLoader("rz_cli", str(RZ_PATH))
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def buildpy(request):
    # build.py does `from cache import BuildCache`, so its own directory
    # must be importable while we exec it by path.
    pkg_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(pkg_dir))
    request.addfinalizer(lambda: sys.path.remove(str(pkg_dir)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy", pkg_dir / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
class TestChildEnv:
    def test_child_env_is_unbuffered(self, rz, monkeypatch):
        # The CI-illegibility bug: buffered children detach diagnostics
        # from their banners. Every child must run unbuffered.
        # delenv first: many dev shells and agent harnesses export
        # PYTHONUNBUFFERED=1 themselves, and child_env copies os.environ —
        # without this the test passes even if the feature is deleted.
        monkeypatch.delenv("PYTHONUNBUFFERED", raising=False)
        env = rz.child_env("ritz")
        assert env.get("PYTHONUNBUFFERED") == "1"

    def test_child_env_has_ritz_path_with_ritz(self, rz):
        env = rz.child_env("ritz")
        assert "RITZ_PATH" in env
        assert any(Path(p).name == "ritz" for p in env["RITZ_PATH"].split(":")), (
            "RITZ_PATH must include projects/ritz for ritzlib resolution"
        )


@pytest.mark.unit
class TestGateOutcome:
    def test_all_green(self, rz):
        hard, known, xpass = rz.gate_outcome(
            failed=[], known_failing={}, ran=["a", "b"]
        )
        assert (hard, known, xpass) == ([], [], [])

    def test_unlisted_failure_gates(self, rz):
        hard, known, xpass = rz.gate_outcome(
            failed=["b"], known_failing={}, ran=["a", "b"]
        )
        assert hard == ["b"]
        assert known == []
        assert xpass == []

    def test_known_failure_is_advisory(self, rz):
        hard, known, xpass = rz.gate_outcome(
            failed=["b"], known_failing={"b": "AGAST #0 why"}, ran=["a", "b"]
        )
        assert hard == []
        assert known == ["b"]
        assert xpass == []

    def test_known_failing_that_passes_is_flagged(self, rz):
        # Strict xpass: a stale exclusion must be removed, not accumulate.
        hard, known, xpass = rz.gate_outcome(
            failed=[], known_failing={"b": "AGAST #0 why"}, ran=["a", "b"]
        )
        assert hard == []
        assert known == []
        assert xpass == ["b"]

    def test_known_failing_not_run_is_ignored(self, rz):
        # Listing a project that wasn't in this sweep (e.g. filtered out)
        # must not produce a phantom xpass.
        hard, known, xpass = rz.gate_outcome(
            failed=[], known_failing={"zzz": "AGAST #0 why"}, ran=["a"]
        )
        assert xpass == []

    def test_mixed(self, rz):
        hard, known, xpass = rz.gate_outcome(
            failed=["a", "b"],
            known_failing={"b": "AGAST #1 x", "c": "AGAST #2 y"},
            ran=["a", "b", "c", "d"],
        )
        assert hard == ["a"]
        assert known == ["b"]
        assert xpass == ["c"]


@pytest.mark.unit
class TestKnownFailingValidation:
    """Validation lives in rz itself (validate_known_failing) — rz refuses
    a malformed excuse at runtime rather than honouring it. These tests
    exercise that seam with FIXED inputs, so they are non-vacuous even
    when the workspace list is empty (a previous revision iterated over
    the real rz.toml, which had no [ci] section — the loop ran zero times
    and the 'enforcement' could never fail)."""

    @pytest.mark.parametrize(
        "bad_reason",
        [
            "no ticket reference at all",
            "#",  # a bare hash is not a task number
            "see the tracker",
            "",
        ],
    )
    def test_excuse_without_agast_number_is_rejected(self, rz, bad_reason):
        with pytest.raises(SystemExit):
            rz.validate_known_failing("build", {"proj": bad_reason})

    def test_non_string_reason_is_rejected(self, rz):
        with pytest.raises(SystemExit):
            rz.validate_known_failing("build", {"proj": 1321})

    def test_non_dict_table_is_rejected(self, rz):
        with pytest.raises(SystemExit):
            rz.validate_known_failing("build", ["proj"])

    def test_valid_excuse_is_accepted(self, rz):
        good = {"proj": "AGAST #1321 — compile failures, tracked"}
        assert rz.validate_known_failing("build", good) == good


@pytest.mark.unit
class TestKnownFailingConfig:
    def test_workspace_build_list_validates(self, rz):
        # The real rz.toml must load through the same runtime validation:
        # every entry is project -> reason citing an AGAST task number.
        entries = rz.known_failing_from_config("build")
        assert isinstance(entries, dict)
        for project, reason in entries.items():
            assert AGAST_REF.search(reason), (
                f"[ci.known_failing.build] {project}: justification must "
                f"cite an AGAST task number, got: {reason!r}"
            )

    def test_no_test_side_excuse_list_exists(self, rz):
        # Deliberate design decision (house rule, scripts/regression.sh):
        # an allowlist may say "known not to compile"; it must never
        # excuse behavioural failure. The test sweep therefore consults
        # the BUILD list only (see cmd_test). If someone adds
        # [ci.known_failing.test], this fails and points them at the rule.
        config = rz.load_workspace_config()
        kf = config.get("ci", {}).get("known_failing", {})
        assert "test" not in kf, (
            "[ci.known_failing.test] must not exist: excusing a test "
            "result excuses behavioural failure, which the house rule in "
            "scripts/regression.sh forbids. Compile-broken projects are "
            "already excused via [ci.known_failing.build]."
        )

    def test_gate_summary_exit_codes(self, rz):
        # summarize_gate returns the job exit code: hard failures and
        # stale exclusions gate; known failures alone do not.
        assert rz.summarize_gate("test", [], {}, ["a"]) == 0
        assert rz.summarize_gate("test", ["a"], {}, ["a"]) == 1
        assert rz.summarize_gate("test", ["a"], {"a": "AGAST #0"}, ["a"]) == 0
        assert rz.summarize_gate("test", [], {"a": "AGAST #0"}, ["a"]) == 1

    def test_gate_summary_names_the_source_list(self, rz, capsys):
        # The test sweep borrows the BUILD list; the summary must point
        # readers at the table the excuse actually lives in.
        rz.summarize_gate("test", ["a"], {"a": "AGAST #0 x"}, ["a"], list_kind="build")
        out = capsys.readouterr().out
        assert "[ci.known_failing.build]" in out
        assert "[ci.known_failing.test]" not in out


@pytest.mark.unit
class TestBuildPyRitzPathForTests:
    """build.py's run_tests RITZ_PATH seam (AGAST #1324 review fix).

    Resolution is first-match-wins, so ROOT must come FIRST: a leaked
    RITZ_PATH from a parent shell may point at a different worktree, and
    under direct invocation (`python3 build.py test ...`, `make test`)
    its ritzlib must not shadow this tree's. This matches the ritz1
    compile-step ordering in the same file.
    """

    def test_root_comes_first(self, buildpy):
        root = str(buildpy.ROOT.resolve())
        result = buildpy.ritz_path_for_tests("/some/other/worktree/ritz")
        assert result.split(":")[0] == root
        assert result.split(":")[1] == "/some/other/worktree/ritz"

    def test_empty_caller_path_yields_just_root(self, buildpy):
        assert buildpy.ritz_path_for_tests("") == str(buildpy.ROOT.resolve())

    def test_duplicate_root_is_deduplicated_even_unresolved(self, buildpy):
        # An unresolved/relative spelling of ROOT must not survive as a
        # second entry (the old `not in _parts` check compared strings).
        unresolved = str(buildpy.ROOT) + "/."
        result = buildpy.ritz_path_for_tests(unresolved)
        assert result == str(buildpy.ROOT.resolve())

    def test_caller_order_is_preserved_after_root(self, buildpy):
        result = buildpy.ritz_path_for_tests("/a:/b")
        assert result.split(":")[1:] == ["/a", "/b"]
