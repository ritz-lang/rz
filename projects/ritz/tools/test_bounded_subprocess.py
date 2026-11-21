"""AGAST #3632: every build / rz subprocess runs under a timeout.

`bounded_run.run` is the one way build.py's modules and `rz` start a child
(compile_ll_to_obj keeps its own, older bound with a memory cap). The guard
below fails on any subprocess call in them that has neither, so a new
unbounded one cannot land; the behavioural tests check that each hung step
is killed at its bound and reported.
"""

import ast
import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
REPO = PKG_DIR.parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

bounded_run = importlib.import_module("bounded_run")

# Every file whose children must be bounded.
GUARDED = ["bounded_run.py", "build.py", "build_pipeline.py", "build_testrun.py", "build_cli.py",
           "manifest.py", "resolve.py", "cache.py", "cas.py"]
SPAWNERS = {"run", "Popen", "call", "check_call", "check_output"}


def _unbounded_calls(path: Path) -> list[str]:
    """`subprocess.<spawn>(...)` calls with no `timeout=` keyword, as
    "file:line". A function that bounds its own Popen with
    `communicate(timeout=...)` (compile_ll_to_obj, AGAST #1731; cas.py's
    clang version probe) is exempt."""
    tree = ast.parse(path.read_text())

    def bounds_itself(fn) -> bool:
        return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr == "communicate"
                   and any(k.arg == "timeout" for k in n.keywords)
                   for n in ast.walk(fn))
    exempt = [(f.lineno, f.end_lineno) for f in ast.walk(tree)
              if isinstance(f, ast.FunctionDef) and bounds_itself(f)]
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in SPAWNERS
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
                and not any(k.arg == "timeout" for k in node.keywords)
                and not any(a <= node.lineno <= b for a, b in exempt)):
            out.append(f"{path.name}:{node.lineno}")
    return sorted(out)


@pytest.mark.unit
@pytest.mark.parametrize("rel", GUARDED + ["../../rz"])
def test_no_unbounded_subprocess(rel):
    found = _unbounded_calls((PKG_DIR / rel).resolve())
    assert not found, ("subprocess call with no timeout; use bounded_run.run "
                       "(AGAST #3632):\n  " + "\n  ".join(found))


@pytest.mark.unit
def test_guard_sees_an_unbounded_call(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("import subprocess\ndef f():\n    subprocess.run(['true'])\n"
                 "    subprocess.run(['true'], timeout=5)\n"
                 "def g():\n    p = subprocess.Popen(['true'])\n    p.communicate(timeout=5)\n"
                 "def h():\n    subprocess.Popen(['true']).communicate()\n")
    assert _unbounded_calls(f) == ["x.py:3", "x.py:9"]


# --- the helper --------------------------------------------------------------

@pytest.mark.unit
def test_bounds_default_and_ignore_garbage(monkeypatch):
    monkeypatch.delenv(bounded_run.STEP_TIMEOUT_ENV, raising=False)
    assert bounded_run.step_timeout() == bounded_run.STEP_TIMEOUT_DEFAULT
    for bad in ("x", "0", "-3"):
        monkeypatch.setenv(bounded_run.STEP_TIMEOUT_ENV, bad)
        assert bounded_run.step_timeout() == bounded_run.STEP_TIMEOUT_DEFAULT
    monkeypatch.setenv(bounded_run.STEP_TIMEOUT_ENV, "9")
    assert bounded_run.step_timeout() == 9
    monkeypatch.setenv(bounded_run.CHILD_TIMEOUT_ENV, "11")
    assert bounded_run.child_timeout() == 11


def _hang_with_grandchild(tmp_path) -> list[str]:
    """A child that prints, starts a grandchild holding stdout, and hangs."""
    script = tmp_path / "hang.sh"
    script.write_text("echo started\nsleep 15 &\nsleep 15\n")
    return ["sh", str(script)]


@pytest.mark.integration
def test_a_captured_hang_returns_though_a_grandchild_holds_the_pipe(tmp_path):
    t0 = time.monotonic()
    r = bounded_run.run(_hang_with_grandchild(tmp_path), timeout=1, env_name="X_T",
                        capture_output=True, text=True)
    assert time.monotonic() - t0 < 10, "the grandchild kept the pipe open"
    assert r.returncode == bounded_run.TIMED_OUT
    assert "started" in r.stdout
    assert "timed out after 1s (X_T)" in r.stderr


@pytest.mark.integration
def test_merged_output_gets_the_timeout_line(tmp_path):
    r = bounded_run.run(_hang_with_grandchild(tmp_path), timeout=1, env_name="X_T",
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert r.returncode == bounded_run.TIMED_OUT
    assert "timed out after 1s (X_T)" in r.stdout


@pytest.mark.integration
def test_an_uncaptured_hang_is_killed_and_reported(tmp_path, capfd):
    r = bounded_run.run(["sleep", "60"], timeout=1, env_name="X_T")
    assert r.returncode == bounded_run.TIMED_OUT
    assert "timed out after 1s (X_T)" in capfd.readouterr().err


@pytest.mark.integration
def test_a_quick_run_is_unchanged():
    r = bounded_run.run(["sh", "-c", "echo out; echo err >&2; exit 3"], timeout=30,
                        env_name="X_T", capture_output=True, text=True)
    assert (r.returncode, r.stdout, r.stderr) == (3, "out\n", "err\n")


# --- the sites ---------------------------------------------------------------
#
# Each step of a package build, hung, fails the build with the bound named.

def _load_build():
    spec = importlib.util.spec_from_file_location("ritz_buildpy_3632_bounds",
                                                  PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def hung_tools(tmp_path, monkeypatch):
    """A PATH whose clang, gcc, as, ar, llvm-ar, ld, ld.lld and lld-link all
    hang; RITZ_STEP_TIMEOUT=1."""
    bindir = tmp_path / "hung-bin"
    bindir.mkdir()
    for tool in ("clang", "gcc", "as", "ar", "llvm-ar", "ld", "ld.lld", "lld-link"):
        p = bindir / tool
        p.write_text("#!/bin/sh\nsleep 15\n")
        p.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}/usr/bin{os.pathsep}/bin")
    monkeypatch.setenv(bounded_run.STEP_TIMEOUT_ENV, "1")
    return bindir


@pytest.mark.integration
def test_hung_hosted_link_fails_the_link(hung_tools, tmp_path, capsys):
    b = _load_build()
    ok = b.link_hosted(tmp_path / "bin", tmp_path / "rt.o", [tmp_path / "a.o"],
                       {"opt_level": 0})
    assert ok is False
    assert "timed out after 1s (RITZ_STEP_TIMEOUT)" in capsys.readouterr().err


@pytest.mark.integration
def test_hung_freestanding_link_fails_the_link(hung_tools, tmp_path, capsys):
    b = _load_build()
    cfg = b.BinaryConfig(name="k", src_path=tmp_path / "k.ritz", additional_sources=[],
                         freestanding=True)
    assert b.link_freestanding_elf(cfg, tmp_path / "k.elf", [tmp_path / "a.o"]) is False
    assert "timed out after 1s" in capsys.readouterr().err


@pytest.mark.integration
def test_hung_uefi_link_fails_the_link(hung_tools, tmp_path, capsys):
    b = _load_build()
    assert b.link_uefi("boot", tmp_path / "BOOT.EFI", [tmp_path / "a.o"],
                       "efi_main") is False
    assert "timed out after 1s" in capsys.readouterr().err


@pytest.mark.integration
def test_hung_assembler_fails_the_build(hung_tools, tmp_path, capsys):
    b = _load_build()
    asm = tmp_path / "boot.s"
    asm.write_text(".text\n")
    assert b.assemble_objects([asm], tmp_path, tmp_path) is None
    assert "timed out after 1s" in capsys.readouterr().err


@pytest.mark.integration
def test_hung_runtime_object_compile_fails(hung_tools, tmp_path, capsys):
    b = _load_build()
    obj = tmp_path / "rt.o"
    obj.with_suffix(".ll").write_text("; empty\n")
    assert b.ensure_runtime_object(obj) is False
    assert "timed out after 1s" in capsys.readouterr().err


@pytest.mark.integration
def test_hung_import_scan_fails(tmp_path, monkeypatch, capsys):
    b = _load_build()
    stub = tmp_path / "list_deps_dir"
    stub.mkdir()
    (stub / "list_deps.py").write_text("import time\ntime.sleep(15)\n")
    monkeypatch.setattr(b, "RITZ0_DIR", stub)
    monkeypatch.setenv(bounded_run.STEP_TIMEOUT_ENV, "1")
    assert b.discover_modules(tmp_path / "m.ritz", project_root=tmp_path) is None
    assert "timed out after 1s" in capsys.readouterr().err


@pytest.mark.integration
def test_hung_module_compile_fails_the_build(tmp_path, monkeypatch, capsys):
    b = _load_build()
    stub = tmp_path / "ritz0_stub.py"
    stub.write_text("import time\ntime.sleep(15)\n")
    monkeypatch.setattr(b, "RITZ0", stub)
    monkeypatch.setenv(bounded_run.STEP_TIMEOUT_ENV, "1")
    src = tmp_path / "m.ritz"
    src.write_text("fn main() -> i32\n    0\n")
    objs = b.compile_modules([src], tmp_path, cache=None, store=None, use_cache=False,
                             compiler="ritz0")
    assert objs is None
    assert "timed out after 1s" in capsys.readouterr().err


@pytest.mark.integration
def test_hung_test_sh_fails(tmp_path, monkeypatch, capsys):
    b = _load_build()
    (tmp_path / "test.sh").write_text("sleep 15\n")
    monkeypatch.setenv(bounded_run.CHILD_TIMEOUT_ENV, "1")
    assert b.run_test_sh(tmp_path) is False
    assert "timed out after 1s (RITZ_CHILD_TIMEOUT)" in capsys.readouterr().out


def _load_rz():
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader("rz_cli_3632_bounds", str(REPO / "rz"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.mark.integration
def test_rz_unit_hang_is_bounded(tmp_path, monkeypatch):
    rz = _load_rz()
    monkeypatch.setenv(bounded_run.CHILD_TIMEOUT_ENV, "1")
    unit = rz.Unit(project="p", order=(0,), sched=(0,), kind="build",
                   cmd=_hang_with_grandchild(tmp_path), env=dict(os.environ))
    rz.run_unit(unit)
    assert unit.rc == bounded_run.TIMED_OUT
    assert "timed out after 1s (RITZ_CHILD_TIMEOUT)" in unit.output
