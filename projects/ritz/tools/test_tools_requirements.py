#!/usr/bin/env python3
"""Every third-party import under tools/ must be a declared dependency.

Written after breaking `main` with the exact mistake it prevents.

tools/ci_local.py imports PyYAML. PyYAML was in the developer venv, so
everything passed locally — including `make ci-local` itself, run end to end.
CI installs only `projects/ritz/requirements.txt`, PyYAML was not in it, and
`make tools-unit` died at collection on the first push (AGAST #1363).

That is the same class as test_ritz1_ptr_arith_chain.py asserting a runtime .o
existed rather than building it: code that works because of state the developer
happens to have and a fresh checkout does not. Twice in one session is a
pattern, not bad luck, so this is a floor rather than a fix.

Deliberately NOT a skip-if-unavailable check. `make tools-unit` is a CI gate,
and CI greps its own pytest output for skips caused by a missing artifact and
fails the build (AGAST #1327). A test that quietly excuses itself when a
dependency is absent reports success for a check it never performed, which is
the failure grammar this repo keeps paying for.

The declared set is the union of requirements.txt (the compiler's own deps) and
requirements-dev.txt (tooling). Add an import, add it to one of those, or this
goes red.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
RITZ_ROOT = TOOLS.parent
REQUIREMENTS = [
    RITZ_ROOT / "requirements.txt",
    RITZ_ROOT / "requirements-dev.txt",
]

# Modules importable without any declaration: the standard library, plus the
# repo's own modules, which are resolved by path rather than installed.
LOCAL_MODULES = {
    "ci_local",
    "manifest",  # projects/ritz/manifest.py, the ritz.toml schema (AGAST #1837)
    "cache",  # projects/ritz/cache.py, the closure store (AGAST #4775)
    "build_pipeline",  # projects/ritz/build_pipeline.py (AGAST #4775)
    "compiler_identity",  # projects/ritz/ritz0/, the compiler hash (AGAST #3915)
    "emitter",  # projects/ritz/ritz0/emitter/, fn_cache's COMPILER_HASH (#3915)
    "apply_string_migration",
    "check_liveness",
    "audit_string_literals",
    "check_doc_examples",
    "ritz1_ir_identity",  # AGAST #4696
    "ritz1_text_ratchet",
    "check_no_s_strings",
    "check_unused_imports",  # AGAST #3458
    "check_test_tempdirs",
    "check_test_budget",
    "cpu_calibrate",
    "example_tests",
    "known_failures",  # tools/known_failures.py, the known-failures schema (AGAST #1834)
    "exec_tmpdir",
    "likely_tests",
    "python_deps",  # AGAST #2300
    "ritz0_scope",  # tools/ritz0_scope.py, the gate's diff scope (AGAST #4027)
    "ritz1_arch",
    "ritz1_ratchet",  # tools/ritz1_ratchet.py, the M1.3 thresholds (AGAST #4433)
    "ritzlib_layers",
    "ritzlib_modules",
    "run_regression_matrix",
    "ritz1_unit",
    "smoke",
    "smoke_stack",
    "shellcheck_tool",  # ritz0/harness/, the pinned shellcheck (AGAST #4360)
    "tracked",  # ritz0/harness/, tracked files for the ratchets (AGAST #4672)
    "refusal_parity",  # tools/refusal_parity.py, the refusal replay (AGAST #4669)
    "refusal_capture",  # ritz0/harness/, its capture hook (AGAST #4669)
    "ritz0_inproc",  # ritz0/harness/, the forked ritz0 the replay compiles with
    "sweep_pytest_tmp",  # ages out /tmp/pytest-of-$USER (AGAST #4274)
    "standard_report",  # docs/STANDARD.md's conformance report (AGAST #1344)
    "ritzgen_py",
    # ritz0's compiler and ritz/resolve.py, on sys.path by the test that
    # imports them (test_nexus_r59_worlds.py, AGAST #4158)
    "ritz0",
    "move_walk",
    "ritz_ast",
    "import_resolver",
    "resolve",
}

# Packages under tools/ whose modules are scanned too. smoke_stack was one
# file until AGAST #3455 split it into a package; it must not leave the check.
PACKAGES = ["smoke_stack"]

# Distribution name -> module name, where they differ.
DIST_TO_MODULE = {
    "pyyaml": "yaml",
    "pytest-xdist": "xdist",
}


def _declared_modules() -> set[str]:
    mods: set[str] = set()
    for req in REQUIREMENTS:
        if not req.is_file():
            continue
        for line in req.read_text().split("\n"):
            line = line.split("#")[0].strip()
            if not line:
                continue
            # strip version specifiers and environment markers
            dist = re.split(r"[<>=!;\[ ]", line, maxsplit=1)[0].strip().lower()
            if not dist:
                continue
            mods.add(DIST_TO_MODULE.get(dist, dist.replace("-", "_")))
    return mods


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import — local by definition
                continue
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def test_requirements_files_exist():
    assert (RITZ_ROOT / "requirements.txt").is_file()
    assert (RITZ_ROOT / "requirements-dev.txt").is_file(), (
        "requirements-dev.txt is missing; tooling deps have nowhere to be declared"
    )


def test_every_third_party_import_under_tools_is_declared():
    stdlib = set(sys.stdlib_module_names)
    declared = _declared_modules()
    undeclared: dict[str, set[str]] = {}

    for path in sorted(TOOLS.glob("*.py")) + sorted(p for pkg in PACKAGES for p in (TOOLS / pkg).glob("*.py")):
        for mod in _top_level_imports(path):
            if mod in stdlib or mod in LOCAL_MODULES or mod in declared:
                continue
            undeclared.setdefault(str(path.relative_to(TOOLS)), set()).add(mod)

    assert not undeclared, (
        "third-party imports not declared in requirements.txt or "
        f"requirements-dev.txt: {undeclared}\n"
        "A developer venv that happens to have them is not a declaration — "
        "CI installs only what these files list."
    )


def test_the_check_can_actually_fail(tmp_path, monkeypatch):
    """A floor never observed failing is indistinguishable from no floor."""
    fake_tools = tmp_path / "tools"
    fake_tools.mkdir()
    (fake_tools / "thing.py").write_text("import definitely_not_declared\n")
    reqs = tmp_path / "requirements.txt"
    reqs.write_text("pytest>=8.0\n")

    monkeypatch.setattr(sys.modules[__name__], "TOOLS", fake_tools)
    monkeypatch.setattr(sys.modules[__name__], "REQUIREMENTS", [reqs])

    stdlib = set(sys.stdlib_module_names)
    declared = _declared_modules()
    found = {
        m
        for p in fake_tools.glob("*.py")
        for m in _top_level_imports(p)
        if m not in stdlib and m not in LOCAL_MODULES and m not in declared
    }
    assert found == {"definitely_not_declared"}


def test_pyyaml_specifically_is_declared():
    """The concrete regression. ci_local.py cannot run without it."""
    assert "yaml" in _declared_modules(), (
        "PyYAML is imported by tools/ci_local.py but not declared; "
        "this is the exact break that turned main red"
    )


def test_ci_installs_the_dev_requirements():
    """Declaring it is not enough — CI has to install the file.

    Every `pip install` step in CI must pull in requirements-dev.txt, not just
    the one job that happens to run tools-unit today. Jobs move, and so do
    steps: the install lives in the composite .github/actions/setup action
    every job uses (AGAST #1838), so read the workflows and the actions.
    """
    github = RITZ_ROOT.parents[1] / ".github"
    files = sorted(github.glob("workflows/*.yml")) + sorted(github.glob("actions/*/action.yml"))
    assert files, github
    install_lines = [
        ln for f in files for ln in f.read_text().split("\n")
        if "pip install" in ln and "requirements.txt" in ln
    ]
    assert install_lines, f"no pip install step found in {[str(f) for f in files]}"
    missing = [ln.strip() for ln in install_lines
               if "requirements-dev.txt" not in ln]
    assert not missing, (
        f"install steps that do not pull in requirements-dev.txt: {missing}"
    )
