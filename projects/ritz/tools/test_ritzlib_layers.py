"""Tests for tools/ritzlib_layers.py (AGAST #4119).

ritzlib is two layers.  The core (CORE: strings, views, spans, Option,
Result, Vec, String, the hash maps and the allocator) builds freestanding:
none of it reaches ritzlib.sys, so a target with no syscalls (the Harland
kernel) can import it.  Everything else is hosted.  `check` names every core
module that imports a hosted one; `test_core_imports_only_core` runs it on
the real tree in `make tools-unit`.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import ritzlib_layers
from ritzlib_layers import CORE, check, imports

RITZLIB = Path(__file__).resolve().parent.parent / "ritzlib"

pytestmark = pytest.mark.unit


def lib(tmp_path, sources):
    for rel, text in sources.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


def core_tree(tmp_path, **overrides):
    """A ritzlib holding every CORE module (empty) plus `overrides`."""
    sources = {f"{m.replace('.', '/')}.ritz": "" for m in CORE}
    sources.update({f"{k}.ritz": v for k, v in overrides.items()})
    return lib(tmp_path, sources)


def test_core_imports_only_core():
    assert check(RITZLIB) == []


def test_ticket_core_modules_are_core():
    # The ticket's list; fmt.digits, drop and hash are in CORE because these use them.
    assert {"str", "strview", "span", "option", "result", "gvec", "string",
            "hashmap", "memory"} <= CORE


@pytest.mark.parametrize("hosted", ["sys", "fs", "net"])
def test_core_importing_hosted_is_reported(tmp_path, hosted):
    root = core_tree(tmp_path, memory=f"# m\nimport ritzlib.str\nimport ritzlib.{hosted}\n")
    assert check(root) == [
        f"ritzlib/memory.ritz:3: core module ritzlib.memory imports "
        f"hosted ritzlib.{hosted}"]


def test_hosted_importing_core_is_fine(tmp_path):
    root = core_tree(tmp_path, io="import ritzlib.sys\nimport ritzlib.gvec\n")
    assert check(root) == []


def test_import_forms(tmp_path):
    path = lib(tmp_path, {"m.ritz": (
        "# import ritzlib.sys   (a comment is not an import)\n"
        "import ritzlib.str\n"
        "pub import ritzlib.fmt\n"
        "import ritzlib.os.env as env\n"
        "import ritzlib.gvec { vec_new }\n"
        "import other.pkg\n"
        "    import ritzlib.fs\n"
    )}) / "m.ritz"
    assert imports(path) == [(2, "str"), (3, "fmt"), (4, "os.env"),
                             (5, "gvec"), (7, "fs")]


def test_missing_core_module_is_reported(tmp_path):
    root = core_tree(tmp_path)
    (root / "hash.ritz").unlink()
    assert check(root) == ["ritzlib/hash.ritz: core module ritzlib.hash does not exist"]


def test_main_exit_status(tmp_path, capsys):
    assert ritzlib_layers.main([str(core_tree(tmp_path / "a"))]) == 0
    assert ritzlib_layers.main([str(core_tree(tmp_path / "b", gvec="import ritzlib.sys\n"))]) == 1
    assert "core module ritzlib.gvec imports hosted ritzlib.sys" in capsys.readouterr().out
