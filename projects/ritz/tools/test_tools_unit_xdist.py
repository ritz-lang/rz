"""tools/ runs under xdist, and the state its tests share stays safe (AGAST #2792).

`make tools-unit` ran its 717 tests one at a time: 312 s of a merge gate on
omegalisk, while the ritz0 suite next to it already ran `-n $(PYTEST_J)
--dist loadgroup`.  Running tools/ the same way is only honest if the tests
do not race each other, so this file pins both halves:

* the Makefile recipe runs tools/ under xdist, with the same knob (PYTEST_J,
  where PYTEST_J=0 means serial) and the same `--dist loadgroup` as `unit`,
  so a test that truly must run alone can use xdist_group;
* `build.py`'s `ensure_runtime_object` publishes `runtime/<shim>.o`
  atomically.  Those objects live at a fixed path in the tree and are built
  on demand by every `build.py build` that links a runtime.  clang used to
  write straight onto the final path, so on a fresh tree a second worker saw
  a present, newer-than-.ll, half-written object and linked it.  clang now
  writes a private temp file that is renamed into place only on success.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
PKG_DIR = TOOLS.parent
MAKEFILE = PKG_DIR / "Makefile"


def _recipe(target: str) -> str:
    """The recipe lines of `target` in projects/ritz/Makefile, joined."""
    lines = MAKEFILE.read_text().splitlines()
    start = lines.index(f"{target}:")
    body = []
    for line in lines[start + 1:]:
        if not line.startswith("\t"):
            break
        body.append(line.strip())
    return "\n".join(body)


# --- the Makefile recipe -----------------------------------------------------

def test_tools_unit_runs_under_xdist_like_the_ritz0_suite():
    recipe = _recipe("tools-unit")
    pytest_line = next(ln for ln in recipe.splitlines() if "-m pytest" in ln)
    assert "tools/" in pytest_line
    assert "-n $(PYTEST_J)" in pytest_line, (
        "tools-unit runs serially; it must use the same -n $(PYTEST_J) as `unit`")
    assert "--dist loadgroup" in pytest_line, (
        "without --dist loadgroup an xdist_group mark would not keep a group together")


def test_unit_and_tools_unit_share_one_parallelism_knob():
    """One PYTEST_J for both suites, so `PYTEST_J=0 make test` is serial."""
    text = MAKEFILE.read_text()
    assert len(re.findall(r"^PYTEST_J\s*\?=", text, re.M)) == 1
    assert "-n $(PYTEST_J)" in _recipe("unit")


# --- runtime/<shim>.o is published atomically ---------------------------------

@pytest.fixture
def buildpy(request):
    # build.py does `from cache import BuildCache`; load a fresh copy so a
    # monkeypatch cannot leak into another test.
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location(
        "ritz_buildpy_2792", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_clang(obj_path: Path, *, rc: int, seen: list):
    """A clang that writes HALF an object to its -o and records what it saw.

    When it runs, the final path must not exist yet: a concurrent reader
    checks exactly `obj_path.exists()` and its mtime.
    """
    def run(cmd, **kw):
        out = Path(cmd[cmd.index("-o") + 1])
        seen.append({"out": out, "final_existed": obj_path.exists()})
        out.write_bytes(b"\x7fELF-half")
        err = "" if rc == 0 else "clang: boom"
        return subprocess.CompletedProcess(cmd, rc, "", err)
    return run


def test_runtime_object_is_not_written_in_place(buildpy, tmp_path, monkeypatch):
    ll = tmp_path / "ritz_start.x86_64.ll"
    ll.write_text("; shim\n")
    obj = ll.with_suffix(".o")
    seen: list = []
    monkeypatch.setattr(buildpy.subprocess, "run", _fake_clang(obj, rc=0, seen=seen))

    assert buildpy.ensure_runtime_object(obj) is True

    assert len(seen) == 1
    assert seen[0]["out"] != obj, "clang wrote straight onto the shared runtime object"
    assert seen[0]["out"].parent == obj.parent, (
        "temp must be on the same filesystem to rename")
    assert seen[0]["final_existed"] is False, "a reader could see the object mid-write"
    assert obj.read_bytes() == b"\x7fELF-half"
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([ll.name, obj.name]), (
        "temp file left behind")


def test_failed_runtime_build_publishes_nothing(buildpy, tmp_path, monkeypatch):
    ll = tmp_path / "ritz_start.x86_64.ll"
    ll.write_text("; shim\n")
    obj = ll.with_suffix(".o")
    seen: list = []
    monkeypatch.setattr(buildpy.subprocess, "run", _fake_clang(obj, rc=1, seen=seen))

    assert buildpy.ensure_runtime_object(obj) is False

    assert not obj.exists(), (
        "a failed clang left a partial object a later build would trust")
    assert [p.name for p in tmp_path.iterdir()] == [ll.name], "temp file left behind"
