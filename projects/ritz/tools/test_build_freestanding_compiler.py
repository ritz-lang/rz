"""`build.py build --compiler X` must compile freestanding [[bin]]s with X.

AGAST #1473: `compile_freestanding_binary` took no compiler and hard-coded
`RITZ0 ... --no-runtime`, so every freestanding binary (harland, indium,
prism, ritzutils, rzsh) reported a ritz1 pass that ritz0 produced.

These tests replace ritz0 and ritz1 with call-recording stubs:

* a ritz1 stub that exits 1 must make a freestanding build FAIL. Before the
  fix it passed, because ritz1 was never run.
* ritz1 has no `--target-os`, so a bin that needs one must fail with a named
  reason, running neither compiler, instead of falling back to ritz0.
* ritz0 builds are unchanged.

Source discovery still goes through ritz0/list_deps.py (a resolver, not a
compiler); only RITZ0 itself, the compiler, is stubbed.
"""

import importlib.util
import os
import stat
import sys
import textwrap
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]

# Records argv plus RITZ_PATH, then either fails or writes a trivial IR module
# to the `-o` path so the rest of the pipeline has something to chew on.
STUB = textwrap.dedent(
    """\
    #!{python}
    import os, sys
    args = sys.argv[1:]
    with open({log!r}, "a") as f:
        f.write(" ".join(args) + " || RITZ_PATH=" + os.environ.get("RITZ_PATH", "") + "\\n")
    if {fail!r}:
        sys.stderr.write("stub compiler: deliberate failure\\n")
        sys.exit(1)
    out = args[args.index("-o") + 1]
    with open(out, "w") as f:
        f.write("define void @_start() {{\\n  ret void\\n}}\\n")
    """
)


def _write_stub(path: Path, log: Path, fail: bool) -> Path:
    path.write_text(STUB.format(python=sys.executable, log=str(log), fail=fail))
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.fixture
def buildpy(request):
    # build.py does `from cache import BuildCache`; load fresh per test so a
    # monkeypatched RITZ0 / RITZ1_FAMILY_BINS cannot leak between tests.
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy_1473", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Stubs:
    def __init__(self, tmp_path, monkeypatch, buildpy):
        self.ritz0_log = tmp_path / "ritz0_calls.log"
        self.ritz1_log = tmp_path / "ritz1_calls.log"
        self.ritz0_log.write_text("")
        self.ritz1_log.write_text("")
        self._tmp = tmp_path
        self._mp = monkeypatch
        self._mod = buildpy
        self.set_ritz0(fail=False)
        self.set_ritz1(fail=True)

    def set_ritz0(self, fail):
        stub = _write_stub(self._tmp / "ritz0_stub.py", self.ritz0_log, fail)
        self._mp.setattr(self._mod, "RITZ0", stub)

    def set_ritz1(self, fail, exists=True):
        stub = self._tmp / "ritz1_stub"
        if exists:
            _write_stub(stub, self.ritz1_log, fail)
        else:
            stub.unlink(missing_ok=True)
        bins = {k: (stub, hint) for k, (_, hint) in self._mod.RITZ1_FAMILY_BINS.items()}
        self._mp.setattr(self._mod, "RITZ1_FAMILY_BINS", bins)

    def ritz0_calls(self):
        return self.ritz0_log.read_text().splitlines()

    def ritz1_calls(self):
        return self.ritz1_log.read_text().splitlines()


@pytest.fixture
def stubs(tmp_path, monkeypatch, buildpy):
    return Stubs(tmp_path, monkeypatch, buildpy)


def _make_pkg(tmp_path, target_os=""):
    """A one-file freestanding package; no asm, no linker script."""
    pkg = tmp_path / "fs_pkg"
    (pkg / "src").mkdir(parents=True)
    tos = f'target_os = "{target_os}"\n' if target_os else ""
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "fs_pkg"\nversion = "0.1.0"\n\n'
        '[[bin]]\nname = "kern"\ntarget = "x86_64-unknown-none"\n'
        f"{tos}freestanding = true\n"
    )
    (pkg / "src" / "kern.ritz").write_text("fn _start()\n    return\n")
    return pkg


@pytest.fixture
def fs_pkg(tmp_path):
    return _make_pkg(tmp_path)


@pytest.fixture
def fs_pkg_target_os(tmp_path):
    return _make_pkg(tmp_path, target_os="harland")


def _build(buildpy, monkeypatch, pkg, compiler):
    monkeypatch.setattr(
        sys, "argv", ["build.py", "build", str(pkg), "--compiler", compiler, "--no-cache"]
    )
    return buildpy.main() or 0


def _text(capsys):
    out = capsys.readouterr()
    return out.out + out.err


# --- the acceptance test from the ticket -----------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_failing_ritz1_fails_the_freestanding_build(
    buildpy, stubs, fs_pkg, monkeypatch, capsys, compiler
):
    rc = _build(buildpy, monkeypatch, fs_pkg, compiler)
    text = _text(capsys)

    assert stubs.ritz0_calls() == [], f"ritz0 compiled a --compiler {compiler} build"
    assert len(stubs.ritz1_calls()) == 1, "the requested compiler was never run"
    assert rc != 0, "a build whose compiler exited 1 must not exit 0"
    assert "deliberate failure" in text
    # The failure is attributed to the compiler that actually failed.
    assert f"✗ {compiler} failed for 1 source file" in text
    assert "ritz0 failed" not in text


@pytest.mark.unit
def test_ritz1_command_matches_hosted_path(buildpy, stubs, fs_pkg, monkeypatch):
    # Same CLI shape as compile_binary: `<bin> <src> -o <ll> -I <ROOT>`, with
    # RITZ_PATH carrying ROOT and ROOT.parent. No ritz0-only flags.
    stubs.set_ritz1(fail=False)
    monkeypatch.setenv("RITZ_PATH", "/caller/extra")
    _build(buildpy, monkeypatch, fs_pkg, "ritz1")  # link outcome irrelevant here

    calls = stubs.ritz1_calls()
    assert stubs.ritz0_calls() == []
    assert len(calls) == 1
    argv, ritz_path = calls[0].split(" || RITZ_PATH=")
    parts = argv.split(" ")
    assert parts[0] == str(fs_pkg / "src" / "kern.ritz")
    assert parts[1] == "-o" and parts[2].endswith(".ll")
    assert parts[3:] == ["-I", str(buildpy.ROOT)]
    assert ritz_path.split(os.pathsep) == [
        str(buildpy.ROOT), str(buildpy.ROOT.parent), "/caller/extra"
    ]


@pytest.mark.unit
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_ritz1_cannot_honour_target_os_fails_loudly(
    buildpy, stubs, fs_pkg_target_os, monkeypatch, capsys, compiler
):
    stubs.set_ritz1(fail=False)  # even a "working" ritz1 must not be used
    rc = _build(buildpy, monkeypatch, fs_pkg_target_os, compiler)
    text = _text(capsys)

    assert rc != 0
    assert stubs.ritz0_calls() == [], "fell back to ritz0"
    assert stubs.ritz1_calls() == [], "ran ritz1 without the target_os it needs"
    assert f"{compiler} does not support freestanding target_os 'harland'" in text


@pytest.mark.unit
def test_missing_ritz1_binary_fails(buildpy, stubs, fs_pkg, monkeypatch, capsys):
    stubs.set_ritz1(fail=False, exists=False)
    rc = _build(buildpy, monkeypatch, fs_pkg, "ritz1")
    text = _text(capsys)

    assert rc != 0
    assert stubs.ritz0_calls() == []
    assert "ritz1 binary not found" in text


# --- ritz0 unchanged --------------------------------------------------------


@pytest.mark.unit
def test_ritz0_freestanding_command_unchanged(
    buildpy, stubs, fs_pkg_target_os, monkeypatch
):
    _build(buildpy, monkeypatch, fs_pkg_target_os, "ritz0")

    calls = stubs.ritz0_calls()
    assert stubs.ritz1_calls() == []
    assert len(calls) == 1
    argv = calls[0].split(" || ")[0].split(" ")
    assert argv[0] == str(fs_pkg_target_os / "src" / "kern.ritz")
    assert "--no-runtime" in argv
    assert argv[argv.index("--target-os") + 1] == "harland"


@pytest.mark.unit
def test_ritz0_failure_still_fails(buildpy, stubs, fs_pkg, monkeypatch, capsys):
    stubs.set_ritz0(fail=True)
    rc = _build(buildpy, monkeypatch, fs_pkg, "ritz0")
    assert rc != 0
    assert "deliberate failure" in _text(capsys)
