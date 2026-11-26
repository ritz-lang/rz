"""Buddhafinger builds and tests with ritz1_selfhosted only (AGAST #4813,
epic #4782; the CI side is #4826, folded into #4825's builder-matrix job).

docs/BUDDHAFINGER_PROPOSAL.md, "Tests and build isolation": the editor is
kept out of the compiler regression suites and the generic multi-compiler
sweeps (`rz build --all` / `rz test --all` under ritz0, ritz1 and
ritz1_selfhosted) by a reasoned rz.toml [workspace.exclude] entry. Locally,
`make -C projects/buddhafinger test` passes ritz1_selfhosted explicitly to
every build and test. In CI (AGAST #4826), rz.toml's exclusion reason opts
the package into main.yml's builder-matrix job (AGAST #4825): one container
run of the published builder image's ritz1_selfhosted, isolated from the
host toolchain, instead of a step running the Makefile target on the
runner. test_builder_matrix.py pins that opt-in and the matrix job itself;
this file pins the sweep exclusion and the local Makefile entry point.

These pin both halves: the sweep skips the package, and a dedicated entry
really builds and runs its ritzunit suite with that compiler. An exclusion
whose stated gate ran nothing would hide the package from every gate.
"""

import importlib.machinery
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[3]
RZ_PATH = WORKSPACE / "rz"
PKG_REL = "projects/buddhafinger"
PKG = WORKSPACE / PKG_REL
ENTRY = f"make -C {PKG_REL} test"
WORKFLOW = WORKSPACE / ".github" / "workflows" / "main.yml"

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
import builder_matrix  # noqa: E402


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

    def test_ci_opts_into_the_builder_matrix_not_a_host_step(self, rz):
        # AGAST #4826: no step in main.yml runs the Makefile target on the
        # runner's own toolchain any more -- that was the isolation gap.
        assert not re.search(rf"^\s*run:\s*{re.escape(ENTRY)}\s*$",
                             WORKFLOW.read_text(), re.MULTILINE)
        # Instead it is in the builder-matrix job's package list (AGAST
        # #4825), which runs it inside the published builder image.
        assert "buddhafinger" in builder_matrix.list_packages(rz=rz)


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
