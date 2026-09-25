"""ritzlib gets a real gate (AGAST #1345).

ritzlib is the standard library every project imports, and until this change
nothing ran its own test suite. Four separate defects hid that, and each one
has its own tests below.

(a) THE SUITE WAS IN NO GATE. rz.toml declares
        members = ["projects/*", "bench/regressions/2026-05-04/*"]
    and a one-level glob cannot reach projects/ritz/ritzlib/tests. It turned
    out to be worse than that: `rz` never read `members` at all.
    discover_projects() walked projects/*/ by hand, so the declared list was
    decorative. The bench members were never built either. Now `rz` expands
    `members`, and ritzlib/tests is listed there explicitly.

(b) A GREEN TICK ON ZERO TESTS. test_async_server.ritz and test_elf.ritz
    printed "✓ ... 0 passed". Neither contains a [[test]] function; both are
    main()-style programs. That is not a discovery bug. `ritz0 --test` prints
    "0 passed, 0 failed" and exits 0 for a file with no tests, and build.py
    took that as a pass. A test file that cannot fail cannot be told apart
    from one that does not exist, so it is now a failure.

(c) THE SUMMARY SAID "0 failed" BESIDE COMPILE FAILURES.
        Σ 255 passed, 0 failed, 3 compile-failed, 0 timed-out
    reads as green to anyone scanning a log. A file that failed to compile
    has not passed. The headline now counts FILES that did not pass, and the
    word "failed" never appears next to a zero.

(d) THE MATRIX SILENTLY SKIPPED A MODULE THAT DOES NOT EXIST.
    RITZLIB_MODULES named "bytes"; there is no ritzlib/bytes.ritz and never
    has been in git history. build_ritzlib_objs() did `continue` on a missing
    file, so 15 names meant 14 links and no diagnostic. A missing named module
    is now a hard error, and "bytes" is deleted from the list because it never
    existed (nothing imports ritzlib.bytes; ritzlib/buf.ritz is the byte-buffer
    module). The runner also prints how many modules it links out of how many
    are on disk, so "matrix green" is not read as "ritzlib covered".

Nothing here excuses, skips or allowlists a failure. The ritzlib suite is
still RED after this change. That is expected: the next ticket fixes it.
"""

import importlib.machinery
import importlib.util
import re
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
RITZ_ROOT = TOOLS.parent
WORKSPACE = RITZ_ROOT.parents[1]


def _load_path(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rz():
    return _load_path("rz_cli_1345", WORKSPACE / "rz")


@pytest.fixture(scope="module")
def buildpy(request):
    # build.py does `from cache import BuildCache`.
    sys.path.insert(0, str(RITZ_ROOT))
    request.addfinalizer(lambda: sys.path.remove(str(RITZ_ROOT)))
    return _load_path("ritz_buildpy_1345", RITZ_ROOT / "build.py")


@pytest.fixture(scope="module")
def matrix():
    return _load_path("matrix_1345", TOOLS / "run_regression_matrix.py")


def _workspace(tmp_path, members, packages):
    """A throwaway workspace: rz.toml with `members`, a ritz.toml per package."""
    lines = ",\n".join(f'    "{m}"' for m in members)
    (tmp_path / "rz.toml").write_text(f"[workspace]\nmembers = [\n{lines},\n]\n")
    for rel in packages:
        d = tmp_path / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / "ritz.toml").write_text(f'[package]\nname = "{d.name}"\n')
    (tmp_path / "projects").mkdir(exist_ok=True)
    return tmp_path


@pytest.fixture
def fake_ws(rz, monkeypatch, tmp_path):
    def make(members, packages):
        root = _workspace(tmp_path, members, packages)
        monkeypatch.setattr(rz, "WORKSPACE_ROOT", root)
        monkeypatch.setattr(rz, "PROJECTS_DIR", root / "projects")
        return root
    return make


# --------------------------------------------------------------------------
# (a) the suite is in the gate
# --------------------------------------------------------------------------

@pytest.mark.unit
class TestWorkspaceMembers:
    def test_ritzlib_tests_is_a_workspace_project(self, rz):
        # The acceptance fact: `rz test --all` sweeps ritzlib's own suite.
        assert "ritz/ritzlib/tests" in rz.discover_projects()

    def test_ritzlib_tests_resolves_to_the_real_package(self, rz):
        cfg = rz.get_project_config("ritz/ritzlib/tests")
        assert cfg["package"]["name"] == "ritzlib-tests"
        assert cfg["build"]["test_only"] is True

    def test_declared_bench_members_are_discovered(self, rz):
        # They were in `members` all along and nothing ever built them.
        found = rz.discover_projects()
        for name in ("s2_module_init", "s3_param_shadow"):
            assert f"../bench/regressions/2026-05-04/{name}" in found

    def test_top_level_projects_keep_their_bare_names(self, rz):
        # [ci.known_failing.build] and every `rz build <name>` invocation key
        # on the bare directory name; that must not change.
        found = rz.discover_projects()
        assert "ritz" in found and "lexis" in found

    def test_members_is_honoured_not_decorative(self, rz, fake_ws):
        fake_ws(["projects/*", "projects/a/nested"],
                ["projects/a", "projects/b", "projects/a/nested"])
        assert rz.discover_projects() == ["a", "a/nested", "b"]

    def test_a_package_outside_members_is_not_discovered(self, rz, fake_ws):
        # The flip side: `members` is the source of truth, so dropping a line
        # from it really does remove the package.
        fake_ws(["projects/a"], ["projects/a", "projects/b"])
        assert rz.discover_projects() == ["a"]

    def test_member_matching_no_package_is_an_error(self, rz, fake_ws):
        # Same rule as RITZLIB_MODULES below: a named thing that is not on
        # disk must not quietly disable its own coverage.
        fake_ws(["projects/*", "projects/gone"], ["projects/a"])
        with pytest.raises(SystemExit) as exc:
            rz.discover_projects()
        assert "projects/gone" in str(exc.value)

    def test_missing_members_list_is_an_error(self, rz, fake_ws):
        root = fake_ws(["projects/*"], ["projects/a"])
        (root / "rz.toml").write_text("[workspace]\nname = 'x'\n")
        with pytest.raises(SystemExit):
            rz.discover_projects()


# --------------------------------------------------------------------------
# (b) a file with zero tests fails
# --------------------------------------------------------------------------

@pytest.mark.unit
class TestClassifyTestFile:
    def test_passing_file(self, buildpy):
        assert buildpy.classify_test_file(0, "ok\n3 passed, 0 failed\n") == ("pass", 3, 0)

    def test_zero_tests_is_not_a_pass(self, buildpy):
        # Exactly what `ritz0 --test` prints for a file with no [[test]].
        status, passed, failed = buildpy.classify_test_file(0, "0 passed, 0 failed\n")
        assert status == "empty"
        assert (passed, failed) == (0, 0)

    def test_assertion_failure(self, buildpy):
        assert buildpy.classify_test_file(1, "2 passed, 1 failed\n") == ("fail", 2, 1)

    def test_no_summary_is_an_error(self, buildpy):
        assert buildpy.classify_test_file(1, "Error in x.ritz: boom\n")[0] == "error"

    def test_nonzero_exit_with_clean_summary_is_an_error(self, buildpy):
        assert buildpy.classify_test_file(139, "3 passed, 0 failed\n")[0] == "error"

    def test_last_summary_line_wins(self, buildpy):
        out = "1 passed, 0 failed\n4 passed, 0 failed\n"
        assert buildpy.classify_test_file(0, out) == ("pass", 4, 0)


@pytest.mark.integration
def test_constructed_empty_test_file_fails_the_package(buildpy, tmp_path, capsys):
    # The acceptance demonstration: a real ritz0 --test run over a file with
    # no [[test]] function makes run_tests() return False.
    (tmp_path / "test_empty.ritz").write_text("fn helper() -> i32\n    0\n")
    cfg = {"package": {"name": "empty-probe"}, "build": {"test_only": True}}
    assert buildpy.run_tests(tmp_path, cfg) is False
    out = capsys.readouterr().out
    assert "✗ test_empty.ritz" in out
    assert "✓ test_empty.ritz" not in out
    assert "no [[test]]" in out


# --------------------------------------------------------------------------
# (c) the summary grammar
# --------------------------------------------------------------------------

@pytest.mark.unit
class TestSummaryGrammar:
    def _s(self, buildpy, **kw):
        base = dict(n_files=17, tests_passed=255, tests_failed=0,
                    n_fail=0, n_error=0, n_empty=0, n_timeout=0)
        base.update(kw)
        return buildpy.format_test_summary(**base)

    def test_the_line_from_the_ticket_no_longer_reads_green(self, buildpy):
        line = self._s(buildpy, n_error=3)
        assert not re.search(r"\b0 failed\b", line), line
        assert "✗" in line and "✓" not in line
        assert "3 of 17 files FAILED" in line
        assert "3 compile-failed" in line

    @pytest.mark.parametrize("only", [
        {"n_fail": 1, "tests_failed": 1}, {"n_error": 1}, {"n_empty": 1},
        {"n_timeout": 1},
    ])
    def test_zero_counts_are_not_printed(self, buildpy, only):
        # Printing "0 timed-out" beside real failures is the same noise that
        # hid "3 compile-failed" behind "0 failed". Each kind is the sole
        # non-zero in turn, so every branch has to leave its zero out.
        line = self._s(buildpy, **only)
        assert not re.search(r"\b0 ", line), line

    def test_every_kind_of_non_pass_is_counted(self, buildpy):
        line = self._s(buildpy, n_fail=1, tests_failed=2, n_error=3,
                       n_empty=2, n_timeout=2)
        assert "8 of 17 files FAILED" in line
        assert "1 with failing tests (2 failed)" in line
        assert "3 compile-failed" in line
        assert "2 with no [[test]] functions" in line
        assert "2 timed-out" in line

    def test_all_green(self, buildpy):
        line = self._s(buildpy)
        assert "✓" in line and "✗" not in line
        assert "17 of 17 files passed" in line
        assert "FAILED" not in line and "failed" not in line


# --------------------------------------------------------------------------
# (d) the matrix's module list
# --------------------------------------------------------------------------

@pytest.mark.unit
class TestRitzlibModuleList:
    def test_every_named_module_exists(self, matrix):
        _srcs, missing = matrix.resolve_ritzlib_modules()
        assert missing == [], f"RITZLIB_MODULES names missing modules: {missing}"

    def test_bytes_was_deleted_not_silenced(self, matrix):
        # There has never been a ritzlib/bytes.ritz. The decision recorded
        # here is: delete the name. If someone writes the module later, they
        # add it back and this test is deleted with a note.
        assert "bytes" not in matrix.RITZLIB_MODULES
        assert not (RITZ_ROOT / "ritzlib" / "bytes.ritz").exists()

    def test_missing_module_is_reported(self, matrix, tmp_path):
        (tmp_path / "sys.ritz").write_text("")
        srcs, missing = matrix.resolve_ritzlib_modules(["sys", "nope"], tmp_path)
        assert srcs == [tmp_path / "sys.ritz"]
        assert missing == ["nope"]

    def test_missing_module_fails_the_build_step(self, matrix, monkeypatch, tmp_path):
        # The silent `continue` is the bug. build_ritzlib_objs must return an
        # error naming the module BEFORE it compiles anything.
        monkeypatch.setattr(matrix, "RITZLIB_MODULES", ["definitely_not_a_module"])
        objs, err = matrix.build_ritzlib_objs(str(tmp_path), {})
        assert objs is None
        assert "definitely_not_a_module" in err

    def test_coverage_line_states_the_real_denominator(self, matrix, tmp_path):
        for m in ("a", "b", "c", "d"):
            (tmp_path / f"{m}.ritz").write_text("")
        line = matrix.ritzlib_coverage_line(["a", "b"], tmp_path)
        assert "2 of 4" in line
        assert "not" in line.lower()  # says what green does NOT mean

    def test_coverage_line_uses_the_real_ritzlib(self, matrix):
        on_disk = len(list((RITZ_ROOT / "ritzlib").glob("*.ritz")))
        line = matrix.ritzlib_coverage_line()
        assert f"{len(matrix.RITZLIB_MODULES)} of {on_disk}" in line
