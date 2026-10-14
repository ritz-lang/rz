"""`clang -c -O2 <x>.ll` must be bounded, and its failure must fail the build.

AGAST #1731: build.py caught a failed per-source `clang -c -O2` and quietly
linked the .ll instead. That hid #1730 for a whole gate. Under `ulimit -v`
clang hit the cap on ritz1's tokens.ll and build.py reported success. Without
the ulimit, the same compile ran unbounded and took the host down.

These tests put a fake `clang` first on PATH. It intercepts only the `-O2`
object compile and passes every other clang call (the runtime object, the link)
through to the real clang. The fake can:

* exit 1                -> the build must fail, naming the file, status, stderr
* sleep (with a child)  -> the timeout must fire, and kill the whole group
* allocate past the cap -> RLIMIT_AS must stop it, and the build must fail
* pass through          -> the build succeeds with zero recorded failures

Nothing here runs a real -O2 compile on large IR (see the #1731 memory-safety
note): the passthrough case compiles a one-function program.
"""

import importlib.util
import os
import shutil
import signal
import stat
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
REAL_CLANG = shutil.which("clang")

pytestmark = pytest.mark.skipif(REAL_CLANG is None, reason="clang not on PATH")

FAKE_CLANG = textwrap.dedent(
    """\
    #!{python}
    import os, subprocess, sys, time
    args = sys.argv[1:]
    mode = os.environ.get("FAKE_CLANG_MODE", "pass")
    if "-O2" not in args:
        os.execv({real!r}, [{real!r}] + args)
    with open({log!r}, "a") as f:
        f.write(" ".join(args) + "\\n")
    if mode == "pass":
        os.execv({real!r}, [{real!r}] + args)
    if mode == "fail":
        sys.stderr.write("noise line\\n" * 50)
        sys.stderr.write("fake clang: LLVM ERROR: deliberate -O2 failure\\n")
        sys.exit(1)
    if mode == "sleep":
        # A grandchild too, so the test can prove the whole group is killed.
        child = subprocess.Popen(["sleep", "600"])
        with open({pids!r}, "w") as f:
            f.write(f"{{os.getpid()}} {{child.pid}}\\n")
        time.sleep(600)
        sys.exit(0)
    if mode == "hog":
        try:
            buf = bytearray(1024 * 1024 * 1024)  # 1 GiB, far over the test cap
        except MemoryError:
            sys.stderr.write("fake clang: MemoryError under the cap\\n")
            sys.exit(70)
        sys.stderr.write("fake clang: allocation was NOT capped\\n")
        sys.exit(0)
    sys.exit(99)
    """
)


@pytest.fixture
def buildpy(request):
    # build.py does `from cache import BuildCache`; load fresh per test so the
    # module-level failure counter starts at zero.
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy_1731", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeClang:
    def __init__(self, tmp_path: Path, monkeypatch):
        bindir = tmp_path / "fakebin"
        bindir.mkdir()
        self.log = tmp_path / "o2_calls.log"
        self.pids = tmp_path / "o2_pids"
        self.log.write_text("")
        path = bindir / "clang"
        path.write_text(FAKE_CLANG.format(
            python=sys.executable, real=REAL_CLANG, log=str(self.log), pids=str(self.pids)))
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
        self._mp = monkeypatch
        self.mode("pass")

    def mode(self, m: str) -> None:
        self._mp.setenv("FAKE_CLANG_MODE", m)

    def o2_calls(self):
        return self.log.read_text().splitlines()


@pytest.fixture
def fake_clang(tmp_path, monkeypatch):
    return FakeClang(tmp_path, monkeypatch)


@pytest.fixture
def pkg(tmp_path):
    p = tmp_path / "o2pkg"
    (p / "src").mkdir(parents=True)
    (p / "ritz.toml").write_text(
        '[package]\nname = "o2pkg"\nversion = "0.1.0"\nsources = ["src"]\n\n'
        '[[bin]]\nname = "o2pkg"\nentry = "main::main"\n'
    )
    (p / "src" / "main.ritz").write_text("fn main() -> i32\n    return 42\n")
    return p


def _build(buildpy, monkeypatch, pkg, *extra):
    monkeypatch.setattr(sys, "argv", ["build.py", "build", str(pkg), "--no-cache", *extra])
    return buildpy.main() or 0


def _text(capsys):
    out = capsys.readouterr()
    return out.out + out.err


def _gone(pid: int) -> bool:
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().split(") ", 1)[1].startswith("Z")  # zombie = dead
    except FileNotFoundError:
        return True


# --- the acceptance tests from the ticket ----------------------------------


@pytest.mark.unit
def test_passing_o2_compile_succeeds_with_zero_failures(buildpy, fake_clang, pkg,
                                                        monkeypatch, capsys):
    rc = _build(buildpy, monkeypatch, pkg)
    assert rc == 0, _text(capsys)
    assert len(fake_clang.o2_calls()) == 1, "the -O2 object compile never ran"
    assert buildpy.CLANG_OBJ_FAILURES == 0


@pytest.mark.unit
def test_failing_o2_compile_fails_the_build_loudly(buildpy, fake_clang, pkg,
                                                   monkeypatch, capsys):
    fake_clang.mode("fail")
    rc = _build(buildpy, monkeypatch, pkg)
    text = _text(capsys)

    assert len(fake_clang.o2_calls()) == 1, "the -O2 object compile never ran"
    assert rc != 0, "a failed clang -c -O2 must not be linked around"
    assert buildpy.CLANG_OBJ_FAILURES == 1
    assert "clang -c -O2 failed" in text
    assert ".ll" in text and "main.ritz" in text, "must name the file"
    assert "exit status 1" in text
    # The stderr *tail*: the real error is the last line, after 50 lines of noise.
    assert "deliberate -O2 failure" in text
    assert text.count("noise line") < 50, "should show the tail, not all of stderr"
    assert "Linking" not in text, "a failed object compile must stop before the link"


@pytest.mark.unit
def test_o2_timeout_fires_and_kills_the_process_group(buildpy, fake_clang, pkg,
                                                      monkeypatch, capsys):
    fake_clang.mode("sleep")
    monkeypatch.setenv(buildpy.CLANG_OBJ_TIMEOUT_ENV, "2")

    # Run the build on a daemon thread so a broken timeout (or killing only
    # the driver, which leaves the grandchild holding the stderr pipe open)
    # fails this test instead of hanging the suite.
    result = {}
    worker = threading.Thread(
        target=lambda: result.setdefault("rc", _build(buildpy, monkeypatch, pkg)),
        daemon=True)
    worker.start()
    worker.join(30)
    if worker.is_alive():
        for pid in map(int, fake_clang.pids.read_text().split()):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        worker.join(10)
        pytest.fail("build hung past the 2s clang timeout (process group not killed?)")
    rc = result["rc"]
    text = _text(capsys)

    assert rc != 0
    assert buildpy.CLANG_OBJ_FAILURES == 1
    assert "timed out after 2s" in text
    driver, grandchild = map(int, fake_clang.pids.read_text().split())
    deadline = time.monotonic() + 5
    while not (_gone(driver) and _gone(grandchild)) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert _gone(driver), "timed-out clang driver still running"
    assert _gone(grandchild), "timed-out clang's child still running (group not killed)"


@pytest.mark.unit
def test_o2_compile_is_address_space_capped(buildpy, fake_clang, pkg,
                                            monkeypatch, capsys):
    fake_clang.mode("hog")
    monkeypatch.setenv(buildpy.CLANG_OBJ_MEM_ENV, "256")
    rc = _build(buildpy, monkeypatch, pkg)
    text = _text(capsys)

    assert "allocation was NOT capped" not in text, "RLIMIT_AS was not applied"
    assert "MemoryError under the cap" in text
    assert rc != 0
    assert buildpy.CLANG_OBJ_FAILURES == 1
    assert "address space 256 MiB" in text


# --- the bounds themselves ---------------------------------------------------


@pytest.mark.unit
def test_bounds_have_safe_defaults_and_ignore_garbage(buildpy, monkeypatch):
    monkeypatch.delenv(buildpy.CLANG_OBJ_TIMEOUT_ENV, raising=False)
    assert buildpy._env_int(buildpy.CLANG_OBJ_TIMEOUT_ENV, 300) == 300
    for bad in ("abc", "0", "-5"):
        monkeypatch.setenv(buildpy.CLANG_OBJ_TIMEOUT_ENV, bad)
        assert buildpy._env_int(buildpy.CLANG_OBJ_TIMEOUT_ENV, 300) == 300
    monkeypatch.setenv(buildpy.CLANG_OBJ_TIMEOUT_ENV, "7")
    assert buildpy._env_int(buildpy.CLANG_OBJ_TIMEOUT_ENV, 300) == 7


@pytest.mark.unit
def test_no_silent_fallback_remains_in_build_py():
    # Grep guard: the only -O2 object compile is the bounded helper's.
    src = (PKG_DIR / "build.py").read_text()
    assert src.count('"-O2"') == 1, "a second, unbounded clang -O2 call appeared"
