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
    "apply_string_migration",
    "audit_string_literals",
    "check_doc_examples",
    "check_no_s_strings",
    "run_regression_matrix",
    "ab_test",
}

# Distribution name -> module name, where they differ.
DIST_TO_MODULE = {
    "pyyaml": "yaml",
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

    for path in sorted(TOOLS.glob("*.py")):
        for mod in _top_level_imports(path):
            if mod in stdlib or mod in LOCAL_MODULES or mod in declared:
                continue
            undeclared.setdefault(path.name, set()).add(mod)

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

    Every `pip install` step in the workflow must pull in requirements-dev.txt,
    not just the one job that happens to run tools-unit today. Jobs move.
    """
    workflow = RITZ_ROOT.parents[1] / ".github" / "workflows" / "main.yml"
    assert workflow.is_file(), workflow
    text = workflow.read_text()
    install_lines = [
        ln for ln in text.split("\n")
        if "pip install" in ln and "requirements.txt" in ln
    ]
    assert install_lines, "no pip install step found in main.yml"
    missing = [ln.strip() for ln in install_lines
               if "requirements-dev.txt" not in ln]
    assert not missing, (
        f"install steps that do not pull in requirements-dev.txt: {missing}"
    )
