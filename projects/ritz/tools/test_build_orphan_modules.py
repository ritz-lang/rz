"""`build.py build` reports src/ modules that no target compiles (AGAST #2210).

`rz build <pkg>` hands the compiler only what each target's entry point
imports, transitively. A `.ritz` under the package's src/ that nothing
imports was never compiled, and the build stayed green: nexus's repos/,
presenters/ and wiki_service could not even parse, unnoticed.

The rule: after its targets, build_package lists every src/**/*.ritz that
no target reached (binary import closures, [[lib]] modules) as uncompiled.
It is a report, not a failure: the exit code is unchanged, so the gate's
`rz build --all` stays a verdict on what IS built. Not orphans:
  * a module holding a [[test]] fn (`rz test` compiles it, AGAST #3279);
  * a module a test file imports, transitively (`rz test` compiles it);
  * files of a nested package (a dir under src/ with its own ritz.toml);
  * anything, when a target's import resolution failed: the reached set
    is then incomplete, and the build already failed with the reason.

Same area: a test file that does not build names the compiler's reason
(`did not build: <diagnostic>` from the harness), not the harness's
"0 passed, 0 failed, 1 errored" summary line.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
BUILD_PY = PKG_DIR / "build.py"


@pytest.fixture
def buildpy(request):
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy_2210", BUILD_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def make_pkg(root: Path, main: str) -> Path:
    """A one-binary package: src/main.ritz, src/util/helper.ritz (imported
    by a good main), src/dead.ritz and src/deep/gone.ritz (imported by
    nothing; gone.ritz does not even parse), src/with_tests.ritz (a [[test]]
    module), src/tested.ritz (imported only by test/test_uses.ritz: `rz
    test` compiles it), and src/sub/ as a nested package."""
    pkg = root / "orph"
    write(pkg / "ritz.toml", '[package]\nname = "orph"\nversion = "0.1.0"\n')
    write(pkg / "src" / "main.ritz", main)
    write(pkg / "src" / "util" / "helper.ritz", "pub fn helper() -> i32\n    0\n")
    write(pkg / "src" / "dead.ritz", "fn dead() -> i32\n    0\n")
    write(pkg / "src" / "deep" / "gone.ritz", "fn gone(\n    x x x\n")
    write(pkg / "src" / "with_tests.ritz",
          "[[test]]\nfn test_t() -> i32\n    0\n")
    write(pkg / "src" / "sub" / "ritz.toml",
          '[package]\nname = "sub"\nversion = "0.1.0"\n')
    write(pkg / "src" / "sub" / "src" / "main.ritz", "fn main() -> i32\n    0\n")
    write(pkg / "src" / "tested.ritz", "pub fn tested() -> i32\n    0\n")
    write(pkg / "test" / "test_uses.ritz",
          "import src.tested\n\n[[test]]\nfn test_u() -> i32\n    tested()\n")
    return pkg


GOOD_MAIN = "import util.helper\n\nfn main() -> i32\n    helper()\n"


# ---------------------------------------------------------------------------
# Unit: the orphan rule, no compiler.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unit_orphans_are_unreached_src_modules(buildpy, tmp_path):
    pkg = make_pkg(tmp_path, GOOD_MAIN)
    reached = {pkg / "src" / "main.ritz", pkg / "src" / "util" / "helper.ritz"}
    got = buildpy.orphaned_modules(pkg, reached)
    assert [p.relative_to(pkg).as_posix() for p in got] == [
        "src/dead.ritz", "src/deep/gone.ritz", "src/tested.ritz"]


@pytest.mark.unit
def test_unit_no_src_dir_has_no_orphans(buildpy, tmp_path):
    write(tmp_path / "ritz.toml", '[package]\nname = "x"\n')
    assert buildpy.orphaned_modules(tmp_path, set()) == []


@pytest.mark.unit
def test_unit_reached_paths_compare_resolved(buildpy, tmp_path):
    """list_deps may hand back a path through a symlink or with `..`."""
    pkg = make_pkg(tmp_path, GOOD_MAIN)
    reached = {pkg / "src" / "util" / ".." / "main.ritz",
               pkg / "src" / "util" / "helper.ritz",
               pkg / "src" / "dead.ritz", pkg / "src" / "deep" / "gone.ritz",
               pkg / "src" / "tested.ritz"}
    assert buildpy.orphaned_modules(pkg, reached) == []


@pytest.mark.unit
def test_unit_compile_failure_reason_prefers_harness_reason(buildpy):
    """The diagnostic is not always on captured stderr (a ritz1 child writes
    to fd 2 directly): then the harness's own `did not build:` line has it."""
    stdout = ("\n0 passed, 0 failed, 1 errored\n\nFailures:\n"
              "  - test/test_x.ritz: did not build: Import resolution failed: "
              "repo.ritz:256:1: Expected expression, got INDENT\n")
    reason = buildpy.compile_failure_reason(stdout, "")
    assert reason == ("Import resolution failed: repo.ritz:256:1: "
                      "Expected expression, got INDENT")


@pytest.mark.unit
def test_unit_compile_failure_reason_prefers_the_compilers_stderr(buildpy):
    """When the compiler's own diagnostic is on stderr (AGAST #3795), it is
    shown: it names the file relatively; the harness's reason, absolutely."""
    stdout = ("0 passed, 0 failed, 1 errored\n"
              "  - test/test_b.ritz: did not build: ritz0 failed for harness: "
              "Compiler error: /tmp/x/test/test_b.ritz:3:12: Unknown function: nope\n")
    stderr = "Error in test_b.ritz: test_b.ritz:3:12: Unknown function: nope\n"
    assert buildpy.compile_failure_reason(stdout, stderr) == stderr.strip()


@pytest.mark.unit
def test_unit_compile_failure_reason_survives_a_long_path(buildpy):
    """The reason names the file by absolute path; under a gate tree's
    pytest tmpdir that alone passed the old 200-char cut, and the message
    itself ("Unknown function: nope") was dropped."""
    path = "/tmp/" + "d" * 300 + "/test_b.ritz"
    stdout = (f"  - test/test_b.ritz: did not build: ritz0 failed for harness: "
              f"Compiler error: {path}:5:12: Unknown function: nope\n")
    assert buildpy.compile_failure_reason(stdout, "").endswith(
        f"{path}:5:12: Unknown function: nope")


@pytest.mark.unit
def test_unit_compile_failure_reason_falls_back_to_error_line(buildpy):
    """No `did not build:` line: the first error line, never the harness's
    "1 errored" summary, which names no reason."""
    stdout = "0 passed, 0 failed, 1 errored\nfatal error: Cannot select: 0x1234\n"
    assert buildpy.compile_failure_reason(stdout, "") == "fatal error: Cannot select: 0x1234"


# ---------------------------------------------------------------------------
# End to end: real `build.py build`.
# ---------------------------------------------------------------------------


def build(pkg: Path):
    env = dict(os.environ, RITZ_PATH=str(PKG_DIR))
    return subprocess.run([sys.executable, str(BUILD_PY), "build", str(pkg)],
                          capture_output=True, text=True, cwd=pkg, env=env,
                          check=False)


@pytest.mark.integration
def test_e2e_build_reports_orphans_and_stays_green(tmp_path):
    pkg = make_pkg(tmp_path, GOOD_MAIN)
    r = build(pkg)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "2 modules under src/ are not compiled" in out, out
    assert "src/dead.ritz" in out and "src/deep/gone.ritz" in out, out
    for reached_or_excused in ("helper.ritz", "with_tests.ritz", "tested.ritz", "sub/"):
        assert reached_or_excused not in out, out


@pytest.mark.integration
def test_e2e_failed_import_resolution_lists_no_orphans(tmp_path):
    """main imports a module that does not exist: the build fails with that
    reason, and every other module is not called an orphan."""
    pkg = make_pkg(tmp_path, "import nowhere\n\nfn main() -> i32\n    0\n")
    r = build(pkg)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out
    assert "src/dead.ritz" not in out, out
    assert "orphan check skipped" in out, out
