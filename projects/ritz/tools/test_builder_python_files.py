"""The builder image's Python file list is complete (AGAST #4847).

projects/builder/stage_tree.py's PYTHON_FILES is every Python file the image
ships: `rz`'s build pipeline under ritz1_selfhosted, and ritz0's front end
for the interface hashes. Nothing in the room gate builds the image, so a
ritz0 change that adds an import (#4844's ritz0/instance_site.py) left the
list short, and every package the image ran died in `import build_pipeline`
-- seen only when builder.yml next rebuilt it. This imports the pipeline
from a tree holding only those files, with the interpreter isolated from the
checkout, so the import that breaks the image breaks here first.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
STAGE_TREE = REPO_ROOT / "projects" / "builder" / "stage_tree.py"


def _python_files() -> list[str]:
    spec = importlib.util.spec_from_file_location("stage_tree_4847", STAGE_TREE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod.PYTHON_FILES)


#: What a build in the image loads (stage_tree.py's comment): the pipeline
#: in-process, and list_deps.py, which build_pipeline runs as a child.
PROBE = """
import sys
sys.path.insert(0, "projects/ritz")
sys.path.insert(1, "projects/ritz/ritz0")
import build, build_cli, build_pipeline, build_testrun, manifest
import list_deps
"""


@pytest.mark.integration
def test_the_pipeline_imports_from_the_staged_python_files_alone(tmp_path):
    for rel in _python_files():
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / rel, dest)
    # -I: no PYTHONPATH, no user site, no script dir; -B: no __pycache__.
    r = subprocess.run([sys.executable, "-I", "-B", "-c", PROBE], cwd=tmp_path,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, (
        "a module the image needs is missing from projects/builder/stage_tree.py "
        "PYTHON_FILES:\n" + r.stderr[-2000:])


def _stage_tree():
    spec = importlib.util.spec_from_file_location("stage_tree_4864", STAGE_TREE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_staged_ritzlib_keeps_its_manifest_and_drops_its_tests(tmp_path):
    """ritzlib's sources are [".", "!tests"] (AGAST #4864). An exclusion
    names no source root, so tests/ stays out of the image (test.sh's
    "no ritzlib ... test corpora" check) while ritz.toml goes in."""
    ritzlib = REPO_ROOT / "projects" / "ritz" / "ritzlib"
    _stage_tree().copy_sources(REPO_ROOT, tmp_path, ritzlib)
    staged = tmp_path / "projects" / "ritz" / "ritzlib"
    assert (staged / "ritz.toml").is_file()
    assert (staged / "strview.ritz").is_file()
    assert (staged / "fmt" / "digits.ritz").is_file()
    assert not (staged / "tests").exists()
