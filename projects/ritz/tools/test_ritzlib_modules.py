"""Tests for tools/ritzlib_modules.py (AGAST #3913).

ritzlib/README.md's module table listed 31 of 45 modules, two of them
(crt0.ritz, testing.ritz) not in the tree (#1859).  It is now generated from
the module headers, and `test_readme_table_is_current` fails when it drifts.
"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import ritzlib_modules
from ritzlib_modules import BEGIN, END, module_table, modules, render_readme

RITZLIB = Path(__file__).resolve().parent.parent / "ritzlib"

pytestmark = pytest.mark.unit


def lib(tmp_path, sources):
    for rel, text in sources.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


def test_modules_reads_each_header(tmp_path):
    root = lib(tmp_path, {
        "sys.ritz": "# ritzlib/sys.ritz - System call wrappers\n\nfn f()\n",
        "async/tasks.ritz": "# ritzlib/async/tasks.ritz - Task executor\n",
    })
    assert modules(root) == [
        ("async/tasks.ritz", "Task executor"),
        ("sys.ritz", "System call wrappers"),
    ]


def test_tests_package_is_not_a_module(tmp_path):
    root = lib(tmp_path, {
        "sys.ritz": "# ritzlib/sys.ritz - Syscalls\n",
        "tests/test_sys.ritz": "# not a module\n",
    })
    assert modules(root) == [("sys.ritz", "Syscalls")]


@pytest.mark.parametrize("first", [
    "import ritzlib.option\n",                 # result.ritz had no header
    "# Option<T> - Optional value type\n",     # header without the path
    "# ritzlib/other.ritz - wrong file\n",     # header naming another file
])
def test_module_without_its_header_is_an_error(tmp_path, first):
    root = lib(tmp_path, {"x.ritz": first})
    with pytest.raises(ValueError, match="x.ritz"):
        modules(root)


def test_table_lists_every_module_with_its_import_path(tmp_path):
    root = lib(tmp_path, {
        "sys.ritz": "# ritzlib/sys.ritz - Syscalls\n",
        "os/env.ritz": "# ritzlib/os/env.ritz - Environment\n",
    })
    assert module_table(root) == (
        "| Module | Import | Description |\n"
        "|--------|--------|-------------|\n"
        "| `os/env.ritz` | `ritzlib.os.env` | Environment |\n"
        "| `sys.ritz` | `ritzlib.sys` | Syscalls |\n"
    )


def test_render_replaces_only_the_marked_block(tmp_path):
    root = lib(tmp_path, {"sys.ritz": "# ritzlib/sys.ritz - Syscalls\n"})
    readme = f"# Title\n\n{BEGIN}\nstale | rows\n{END}\n\nTail\n"
    assert render_readme(readme, root) == (
        f"# Title\n\n{BEGIN}\n{module_table(root)}{END}\n\nTail\n")


def test_render_without_markers_is_an_error(tmp_path):
    root = lib(tmp_path, {"sys.ritz": "# ritzlib/sys.ritz - Syscalls\n"})
    with pytest.raises(ValueError, match="marker"):
        render_readme("# no table here\n", root)


def test_readme_table_is_current():
    """The guard: fails tools-unit when a module is added, removed or renamed
    without `python3 tools/ritzlib_modules.py --write`."""
    readme = (RITZLIB / "README.md").read_text()
    assert render_readme(readme, RITZLIB) == readme, (
        "ritzlib/README.md module table is stale: run "
        "`python3 tools/ritzlib_modules.py --write`")


@pytest.mark.integration
def test_cli_check_and_write(tmp_path):
    root = lib(tmp_path, {
        "sys.ritz": "# ritzlib/sys.ritz - Syscalls\n",
        "README.md": f"{BEGIN}\nstale\n{END}\n",
    })
    tool = [sys.executable, ritzlib_modules.__file__, "--ritzlib", str(root)]

    stale = subprocess.run(tool, capture_output=True, text=True, check=False)
    assert stale.returncode == 1
    assert "--write" in stale.stdout

    wrote = subprocess.run([*tool, "--write"], capture_output=True, text=True, check=False)
    assert wrote.returncode == 0, wrote.stdout + wrote.stderr
    assert "`ritzlib.sys`" in (root / "README.md").read_text()

    clean = subprocess.run(tool, capture_output=True, text=True, check=False)
    assert clean.returncode == 0, clean.stdout + clean.stderr
