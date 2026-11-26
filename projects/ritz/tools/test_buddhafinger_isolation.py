"""Buddhafinger builds and tests with ritz1_selfhosted only (AGAST #4813, epic #4782).

docs/BUDDHAFINGER_PROPOSAL.md, "Tests and build isolation": the editor is
kept out of the compiler regression suites and the generic multi-compiler
sweeps (`rz build --all` / `rz test --all` under ritz0, ritz1 and
ritz1_selfhosted) by a reasoned rz.toml [workspace.exclude] entry, and is
covered instead by one dedicated entry point, `make -C projects/buddhafinger
test`, which passes ritz1_selfhosted explicitly to every build and test.

These pin both halves: the sweep skips the package, and the dedicated entry
really builds and runs its ritzunit suite with that compiler. An exclusion
whose stated gate ran nothing would hide the package from every gate.
"""

import importlib.machinery
import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[3]
RZ_PATH = WORKSPACE / "rz"
PKG_REL = "projects/buddhafinger"
PKG = WORKSPACE / PKG_REL
ENTRY = f"make -C {PKG_REL} test"
WORKFLOW = WORKSPACE / ".github" / "workflows" / "main.yml"


@pytest.fixture(scope="module")
def rz():
    spec = importlib.util.spec_from_loader(
        "rz_4813", importlib.machinery.SourceFileLoader("rz_4813", str(RZ_PATH)))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _recipe_commands():
    """The Makefile's recipe lines with its `VAR := value` / `VAR ?= value`
    variables expanded: what `make test` runs, without spawning make (a
    unit test may not start processes, AGAST #1805)."""
    text = (PKG / "Makefile").read_text()
    var = dict(re.findall(r"^([A-Z0-9_]+)\s*[:?]?=\s*(.*?)\s*$", text, re.MULTILINE))
    def expand(line):
        for _ in range(5):
            line = re.sub(r"\$\(([A-Z0-9_]+)\)", lambda m: var.get(m[1], m[0]), line)
        return line
    return [expand(ln.strip()) for ln in text.splitlines() if ln.startswith("\t")]


@pytest.mark.unit
class TestSweepExcludesBuddhafinger:
    def test_package_exists(self):
        assert (PKG / "ritz.toml").is_file()

    def test_not_swept_by_all(self, rz):
        # Neither by its id nor under it (a nested package would be swept too).
        assert not [p for p in rz.discover_projects()
                    if p == "buddhafinger" or p.startswith("buddhafinger/")]

    def test_exclusion_names_the_entry_and_the_epic(self, rz):
        reason = rz.workspace_exclusions().get(PKG_REL)
        assert reason, f"rz.toml [workspace.exclude] has no {PKG_REL!r} entry"
        assert ENTRY in reason
        assert "#4782" in reason

    def test_still_reachable_by_name(self, rz):
        # Excluded from the sweep, not from rz: the entry addresses it by name.
        assert rz.resolve_project("buddhafinger") == "buddhafinger"

    def test_ci_runs_the_dedicated_entry(self):
        # The exclusion's reason must name a gate that runs: main.yml does.
        assert re.search(rf"^\s*run:\s*{re.escape(ENTRY)}\s*$",
                         WORKFLOW.read_text(), re.MULTILINE)


@pytest.mark.unit
class TestEntryPassesTheCompilerExplicitly:
    def test_every_build_and_test_names_ritz1_selfhosted(self):
        cmds = [c for c in _recipe_commands()
                if re.search(r"(^|[\s/])(rz|build\.py)\s+(build|test)\b", c)]
        assert any(re.search(r"\brz\s+test\b", c) for c in cmds), cmds
        assert any(re.search(r"\brz\s+build\b", c) for c in cmds), cmds
        # Never the default (ritz0): every invocation passes the compiler.
        bad = [c for c in cmds if "--compiler ritz1_selfhosted" not in c]
        assert bad == []

    def test_entry_builds_the_compiler_first(self):
        assert any("ritz1-bootstrap" in c for c in _recipe_commands())


@pytest.mark.unit
def test_core_does_not_import_platform_adapters():
    # Proposal, "Ritz and platform boundaries": buffer, modes, commands and
    # screen layout stay independent of terminal and OS I/O.
    core = sorted((PKG / "src" / "core").glob("*.ritz"))
    assert {p.stem for p in core} >= {"buffer", "screen", "modes", "commands"}
    leaks = [(p.name, ln) for p in core for ln in p.read_text().splitlines()
             if re.match(r"\s*import\s+(platform\b|ritzlib\.(fd|sys|term|process|fs)\b)", ln)]
    assert leaks == []


@pytest.mark.integration
def test_dedicated_entry_runs_the_suite_under_ritz1_selfhosted():
    r = subprocess.run(["make", "-C", str(PKG), "test"], cwd=WORKSPACE,
                       capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "compiler=ritz1_selfhosted" in out or "ritz1_selfhosted" in out, out
    passed = [int(n) for n in re.findall(r"(\d+) passed", out)]
    assert passed and max(passed) >= 1, out
    assert not re.search(r"[1-9]\d* failed", out), out
