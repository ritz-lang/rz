"""`rz test --all` warm phases (AGAST #1915).

After #1896 and #1914 the two largest costs of a warm `rz test --all` were

* the `--test-table` harness compile of every test file: never cached, so a
  warm run paid ~0.75 s x 180 files for IR it had produced before; and
* the interpreter chain of every file unit: rz -> `build.py test
  --unit-file` -> subprocess `ritz0.py --test` -> test_runner, ~0.7 s of
  start-up and imports per file before any work.

Now the harness IR is an artifact-store entry keyed like a module (compiler
fingerprint, the harness source, the interfaces of its import closure), and
build.py runs the file in-process instead of starting `ritz0.py --test`.

(build_runner_objects is not cached: its `ld -r` + `objcopy` measured ~30 ms
a file. Its cost is resolving ritzunit's imports and re-keying its modules.)
"""

import importlib
import importlib.util
import json
import os
import re
import shutil
import sys
import threading
import time
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
RITZ0_DIR = PKG_DIR / "ritz0"
for d in (str(PKG_DIR), str(RITZ0_DIR)):
    if d not in sys.path:
        sys.path.insert(0, d)

# By name, not `import cas`: test_tools_requirements reads a bare import as an
# undeclared third-party dependency.
cas = importlib.import_module("cas")

HAS_CLANG = shutil.which("clang") is not None
needs_clang = pytest.mark.skipif(not HAS_CLANG, reason="clang not on PATH")

# File and Σ lines carry these; two runs of one file differ only in the numbers.
_DURATION = re.compile(r" — (?:wall|binary|suite) \d+\.\d{3}s")


@pytest.fixture(autouse=True)
def private_store(tmp_path, monkeypatch):
    """Never touch the real ~/.cache/ritz/cas; reset per-process counters."""
    root = tmp_path / "cas"
    monkeypatch.setenv(cas.CAS_DIR_ENV, str(root))
    monkeypatch.delenv(cas.STATS_LOG_ENV, raising=False)
    monkeypatch.delenv("RITZ_NO_CAS", raising=False)
    monkeypatch.setattr(cas, "STATS", cas.Stats())
    return root


@pytest.fixture
def test_runner():
    return importlib.import_module("test_runner")


@pytest.fixture
def buildpy(tmp_path):
    """A fresh build.py, so a monkeypatch cannot leak between tests."""
    spec = importlib.util.spec_from_file_location(
        f"ritz_buildpy_1915_{tmp_path.name}", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TEST_SRC = ("import b\n\n[[test]]\nfn test_seven() -> i32\n"
            "    assert seven() == {want}\n    0\n")


def _pkg(tmp_path, want=7, b_src="pub fn seven() -> i32\n    7\n"):
    """A test-only package: src/b.ritz, and test/test_b.ritz importing it."""
    pkg = tmp_path / "pkg"
    (pkg / "src").mkdir(parents=True, exist_ok=True)
    (pkg / "test").mkdir(exist_ok=True)
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "t"\nversion = "0.1.0"\nsources = ["src"]\n\n'
        '[build]\ntest_only = true\n')
    (pkg / "src" / "b.ritz").write_text(b_src)
    t = pkg / "test" / "test_b.ritz"
    t.write_text(TEST_SRC.format(want=want))
    return pkg, t


def _spy(monkeypatch, module):
    """Record the harness compiles and `ld -r` runs made through `module.subprocess`."""
    calls = {"harness": [], "ld": [], "ritz0_test": []}
    real = module.subprocess.run

    def spy(cmd, *a, **kw):
        cmd_s = [str(c) for c in cmd]
        if "--test-table" in cmd_s:
            calls["harness"].append(cmd_s)
        if cmd_s and cmd_s[0] == "ld":
            calls["ld"].append(cmd_s)
        if any(c.endswith("ritz0.py") for c in cmd_s) and "--test" in cmd_s:
            calls["ritz0_test"].append(cmd_s)
        return real(cmd, *a, **kw)
    monkeypatch.setattr(module.subprocess, "run", spy)
    return calls


# --- harness IR from the store -----------------------------------------------


@pytest.mark.integration
@needs_clang
def test_warm_run_compiles_no_harness(tmp_path, monkeypatch, test_runner):
    _pkg_dir, t = _pkg(tmp_path)
    calls = _spy(monkeypatch, test_runner)

    assert test_runner.run_test_file(str(t))[:2] == (1, 0)
    assert len(calls["harness"]) == 1

    calls["harness"].clear()
    assert test_runner.run_test_file(str(t))[:2] == (1, 0)
    assert calls["harness"] == [], "the harness was recompiled although the store had it"


def _spy_obj_compiles(monkeypatch, test_runner):
    """Record the .ll files build.compile_ll_to_obj (clang -c -O2) is run on."""
    build = test_runner._build_module()
    real = build.compile_ll_to_obj
    seen = []

    def spy(ll_path, obj_path, src):
        seen.append(Path(ll_path).name)
        return real(ll_path, obj_path, src)
    monkeypatch.setattr(build, "compile_ll_to_obj", spy)
    return seen


@pytest.mark.integration
@needs_clang
def test_the_harness_is_linked_as_an_O2_object(tmp_path, monkeypatch, test_runner):
    """AGAST #1917: the harness went to the link as .ll, i.e. at clang's -O0,
    while every other object (and every shipped program) is -O2. Tests that
    passed only unoptimised hid real bugs."""
    _pkg_dir, t = _pkg(tmp_path)
    seen = _spy_obj_compiles(monkeypatch, test_runner)
    linked = []
    real_link = test_runner._link

    def spy_link(objects, exe_path):
        linked.extend(objects)
        return real_link(objects, exe_path)
    monkeypatch.setattr(test_runner, "_link", spy_link)

    assert test_runner.run_test_file(str(t))[:2] == (1, 0)
    assert "test_main.ll" in seen, seen
    assert linked and not [o for o in linked if not o.endswith(".o")], linked


@pytest.mark.integration
@needs_clang
def test_warm_run_compiles_no_harness_object(tmp_path, monkeypatch, test_runner):
    """The -O2 harness object is stored, so a warm run runs no clang -c on it."""
    _pkg_dir, t = _pkg(tmp_path)
    seen = _spy_obj_compiles(monkeypatch, test_runner)
    assert test_runner.run_test_file(str(t))[:2] == (1, 0)
    assert seen.count("test_main.ll") == 1, seen

    seen.clear()
    assert test_runner.run_test_file(str(t))[:2] == (1, 0)
    assert "test_main.ll" not in seen, "the harness object was rebuilt although the store had it"


@pytest.mark.integration
@needs_clang
def test_editing_the_test_file_recompiles_its_harness(tmp_path, monkeypatch, test_runner):
    _pkg_dir, t = _pkg(tmp_path)
    calls = _spy(monkeypatch, test_runner)
    assert test_runner.run_test_file(str(t))[:2] == (1, 0)

    t.write_text(TEST_SRC.format(want=8))
    calls["harness"].clear()
    assert test_runner.run_test_file(str(t))[:2] == (0, 1), "ran the stale harness"
    assert len(calls["harness"]) == 1


@pytest.mark.integration
@needs_clang
def test_harness_is_keyed_on_import_interfaces_not_bodies(tmp_path, monkeypatch, test_runner):
    """A body-only edit to an import keeps the harness (its object changes);
    an interface edit recompiles it."""
    pkg, t = _pkg(tmp_path)
    calls = _spy(monkeypatch, test_runner)
    assert test_runner.run_test_file(str(t))[:2] == (1, 0)

    (pkg / "src" / "b.ritz").write_text("pub fn seven() -> i32\n    8\n")
    calls["harness"].clear()
    assert test_runner.run_test_file(str(t))[:2] == (0, 1), "linked the stale b object"
    assert calls["harness"] == [], "a body-only edit to an import recompiled the harness"

    (pkg / "src" / "b.ritz").write_text(
        "pub fn seven() -> i32\n    7\n\npub fn eight() -> i32\n    8\n")
    assert test_runner.run_test_file(str(t))[:2] == (1, 0)
    assert len(calls["harness"]) == 1, "an interface edit to an import kept the harness"


@pytest.mark.integration
@needs_clang
def test_no_cas_compiles_the_harness_every_time(tmp_path, monkeypatch, test_runner):
    _pkg_dir, t = _pkg(tmp_path)
    monkeypatch.setenv("RITZ_NO_CAS", "1")
    calls = _spy(monkeypatch, test_runner)
    for _ in range(2):
        assert test_runner.run_test_file(str(t))[:2] == (1, 0)
    assert len(calls["harness"]) == 2


@pytest.mark.integration
@needs_clang
def test_a_harness_that_does_not_compile_is_not_stored(tmp_path, monkeypatch, test_runner,
                                                       private_store):
    _pkg_dir, t = _pkg(tmp_path)
    t.write_text("import b\n\n[[test]]\nfn test_seven() -> i32\n"
                 "    assert no_such_fn() == 7\n    0\n")
    calls = _spy(monkeypatch, test_runner)
    for _ in range(2):
        with pytest.raises(test_runner.TestBuildError, match="no_such_fn"):
            test_runner.run_test_file(str(t))
    assert len(calls["harness"]) == 2, "a failed harness compile was served from the store"
    metas = [json.loads(m.read_text()) for m in private_store.rglob("meta/*/*.json")]
    assert metas and not [m for m in metas if m["module"].endswith("#test-table")]


@pytest.mark.unit
def test_harness_key_names_the_compiler_and_differs_from_the_module_key(tmp_path, monkeypatch,
                                                                         buildpy):
    # A key folds in cas.target_id(), whose first call runs `clang --version`;
    # pin it so this pure test starts no process (AGAST #3807, spawn_guard).
    monkeypatch.setattr(cas, "_TARGET", "test-os/test-machine/test-clang")
    src = tmp_path / "test_x.ritz"
    src.write_text("[[test]]\nfn test_x() -> i32\n    0\n")
    k0 = buildpy.cas_harness_key(src, [], "ritz0")
    assert k0 and k0 == buildpy.cas_harness_key(src, [], "ritz0")
    assert k0 != buildpy.cas_harness_key(src, [], "ritz1")
    cache = buildpy.get_build_cache("ritz0")
    cache.set_import_context(project_root=tmp_path)
    assert k0 != buildpy.cas_module_key(src, cache, "ritz0")


@pytest.mark.unit
def test_harness_key_is_none_for_an_unparseable_import(tmp_path, buildpy):
    src = tmp_path / "test_x.ritz"
    src.write_text("import bad\n[[test]]\nfn test_x() -> i32\n    0\n")
    bad = tmp_path / "bad.ritz"
    bad.write_text("fn (((\n")
    assert buildpy.cas_harness_key(src, [bad], "ritz0") is None


# --- build.py runs the unit in-process ---------------------------------------


@pytest.mark.integration
@needs_clang
def test_unit_file_runs_no_ritz0_test_subprocess(tmp_path, monkeypatch, buildpy, capsys):
    pkg, t = _pkg(tmp_path)
    calls = _spy(monkeypatch, buildpy)
    result = tmp_path / "result.json"
    monkeypatch.setattr(sys, "argv", [
        "build.py", "test", str(pkg), "--unit-file", str(t), "--unit-result", str(result)])
    assert (buildpy.main() or 0) == 0
    assert calls["ritz0_test"] == [], "build.py still starts `ritz0.py --test`"
    got = json.loads(result.read_text())
    out = capsys.readouterr().out
    assert (got["status"], got["passed"], got["failed"]) == ("pass", 1, 0)
    assert isinstance(got["wall_ms"], int) and got["wall_ms"] >= 0
    assert isinstance(got["binary_ms"], int) and got["binary_ms"] >= 0
    assert "✓ test_b.ritz — 1 passed" in out
    assert re.search(r"wall \d+\.\d{3}s — binary \d+\.\d{3}s", out)


@pytest.mark.integration
@needs_clang
@pytest.mark.parametrize("src, status, line", [
    (TEST_SRC.format(want=8), "fail", "✗ test_b.ritz — 0 passed, 1 failed"),
    # A harness that does not compile is compile-failed (AGAST #3795): no
    # test ran, and the line shown is the compiler's diagnostic.
    ("import b\n\n[[test]]\nfn test_seven() -> i32\n    assert nope() == 7\n    0\n",
     "error", "Unknown function: nope"),
    ("fn helper() -> i32\n    0\n", "empty", "ran 0 tests"),
])
def test_in_process_verdicts_match_the_subprocess_ones(tmp_path, monkeypatch, buildpy,
                                                       capsys, src, status, line):
    """The same file, run in-process and through `ritz0.py --test`: one verdict."""
    pkg, t = _pkg(tmp_path)
    t.write_text(src)
    env, timeout = buildpy.test_env_for_files(), buildpy.per_file_timeout()

    got = buildpy.run_test_file(t, pkg, env, timeout)
    out = capsys.readouterr().out
    assert got["status"] == status
    assert line in out
    assert re.search(r"wall \d+\.\d{3}s — binary \d+\.\d{3}s", out)

    monkeypatch.setattr(buildpy, "_can_run_in_process", lambda: False)
    calls = _spy(monkeypatch, buildpy)
    second = buildpy.run_test_file(t, pkg, env, timeout)
    # Durations move between runs; the verdict text around them does not.
    assert (second["status"], second["passed"], second["failed"]) == (
        got["status"], got["passed"], got["failed"])
    assert len(calls["ritz0_test"]) == 1
    second_out = capsys.readouterr().out
    assert _DURATION.sub("", second_out) == _DURATION.sub("", out)
    assert re.search(r"wall \d+\.\d{3}s — binary \d+\.\d{3}s", second_out)


@pytest.mark.unit
def test_in_process_unit_runs_in_the_package_with_the_test_env(tmp_path, monkeypatch,
                                                                buildpy, test_runner):
    """`ritz0 --test` ran with cwd=pkg_dir and env=test_env (integration tests
    `fork/exec ./binary`); in-process must do the same, and put both back."""
    pkg, t = _pkg(tmp_path)
    seen = {}

    def fake(path, verbose=False, compiler="ritz0"):
        seen.update(cwd=os.getcwd(), ritz_path=os.environ.get("RITZ_PATH"),
                    marker=os.environ.get("RITZ_1915_MARKER"), path=path, compiler=compiler)
        return 1, 0, []
    monkeypatch.setattr(test_runner, "run_test_file", fake)
    cwd, env_before = os.getcwd(), dict(os.environ)
    env = {**buildpy.test_env_for_files(), "RITZ_1915_MARKER": "yes"}

    got = buildpy.run_test_file(t, pkg, env, 60, "ritz1")
    assert (got["status"], got["passed"], got["failed"]) == ("pass", 1, 0)
    assert "wall_ms" in got and "binary_ms" in got
    assert seen == {"cwd": str(pkg), "ritz_path": env["RITZ_PATH"], "marker": "yes",
                    "path": str(t), "compiler": "ritz1"}
    assert os.getcwd() == cwd
    assert dict(os.environ) == env_before


@pytest.mark.unit
def test_in_process_unit_times_out(tmp_path, monkeypatch, buildpy, test_runner, capsys):
    pkg, t = _pkg(tmp_path)
    monkeypatch.setattr(test_runner, "run_test_file",
                        lambda *a, **k: (time.sleep(30), (1, 0, []))[1])
    t0 = time.monotonic()
    got = buildpy.run_test_file(t, pkg, buildpy.test_env_for_files(), 1)
    assert time.monotonic() - t0 < 10
    assert (got["status"], got["passed"], got["failed"]) == ("timeout", 0, 0)
    out = capsys.readouterr().out
    assert "TIMEOUT after 1s" in out
    assert re.search(r"wall \d+\.\d{3}s — binary \d+\.\d{3}s", out)


# integration: it runs the ritz0 stub as a real subprocess (AGAST #3807).
@pytest.mark.integration
def test_off_the_main_thread_the_unit_runs_as_a_subprocess(tmp_path, monkeypatch, buildpy):
    """SIGALRM (the in-process timeout) only works on the main thread."""
    pkg, t = _pkg(tmp_path)
    stub = tmp_path / "ritz0_stub.py"
    stub.write_text("print('1 passed, 0 failed')\n")
    monkeypatch.setattr(buildpy, "RITZ0", stub)
    out = {}
    th = threading.Thread(target=lambda: out.update(
        r=buildpy.run_test_file(t, pkg, buildpy.test_env_for_files(), 60)))
    th.start()
    th.join()
    assert (out["r"]["status"], out["r"]["passed"], out["r"]["failed"]) == ("pass", 1, 0)
    assert "wall_ms" in out["r"] and "binary_ms" in out["r"]


_SLOW_SRC = """\
import ritzlib.sys

fn sleep_ms(ms: i64)
    var ts: [2]i64
    ts[0] = ms / 1000
    ts[1] = (ms % 1000) * 1000000
    sys_nanosleep(@ts[0], null)

[[test]]
fn test_instant() -> i32
    0

[[test]]
fn test_over_one_second() -> i32
    sleep_ms(1200)
    0
"""


@pytest.mark.integration
@needs_clang
def test_file_line_names_wall_binary_suite_and_a_slow_test(tmp_path, buildpy, capsys):
    """The real verdict printer, fed by a real ritzunit JSON report.

    `test_over_one_second` sleeps 1.2s, so its `duration_ms` is at least
    1000 and the file line must name it. The instant test must not be named.
    """
    pkg = tmp_path / "pkg"
    (pkg / "test").mkdir(parents=True)
    (pkg / "test" / "test_slow.ritz").write_text(_SLOW_SRC)
    cfg = {"package": {"name": "t"}, "build": {"test_only": True}}

    assert buildpy.run_tests(pkg, cfg) is True
    out = capsys.readouterr().out
    assert re.search(
        r"✓ test_slow\.ritz — 2 passed — wall \d+\.\d{3}s — binary \d+\.\d{3}s",
        out), out
    binary = re.search(r"✓ test_slow\.ritz — 2 passed — wall \d+\.\d{3}s — binary (\d+\.\d{3})s", out)
    assert float(binary.group(1)) >= 1.0, out
    named = re.findall(r"^        (\S+) (\d+\.\d{3})s$", out, re.M)
    assert [name for name, _ in named] == ["test_over_one_second"], out
    assert float(named[0][1]) >= 1.0
    assert re.search(
        r"Σ ✓ 1 of 1 files passed \(2 tests\) — suite \d+\.\d{3}s", out), out
    suite = re.search(r"suite (\d+\.\d{3})s", out)
    assert float(suite.group(1)) >= 1.0


# --- the tiers hold under spawn_guard ----------------------------------------


@pytest.mark.integration
def test_unit_tier_starts_no_process_under_spawn_guard(tmp_path):
    """This file's non-integration tests pass with ritz0's spawn guard loaded.

    `make tools-unit` runs tools/ in its own session, without ritz0/conftest.py,
    so nothing there enforces AGAST #1805's rule. A mixed local run such as
    `pytest ritz0/test_x.py tools/<this file>` loads the guard, and two `unit`
    tests here failed it (AGAST #3807): one ran a ritz0 stub as a subprocess,
    the other paid cas.target_id()'s `clang --version`. One nested session,
    the guard loaded by name as ritz0/test_spawn_guard.py does.
    """
    import subprocess
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")}
    env["PYTHONPATH"] = os.pathsep.join([str(RITZ0_DIR), str(RITZ0_DIR / "harness")])
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "spawn_guard", "-p", "no:cacheprovider",
         "-m", "not integration", str(Path(__file__).resolve())],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
    assert " passed" in r.stdout and "deselected" in r.stdout, r.stdout
