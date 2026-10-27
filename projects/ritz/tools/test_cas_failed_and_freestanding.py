"""AGAST #1896: what a warm `rz test --all` still pays for.

1. "Misses" on an unchanged tree. A warm run counted 29 store misses, and
   none carried a `missed` record to name it. They were modules that do not
   compile (lexis 19, tempest 8, spire 1, nexus 1): `get_or_build` counted the
   miss before calling `build_fn`, the build raised, nothing was stored and
   no record was written, so the same broken module was a "miss" on every
   run. A failed build is now its own counter, with a record naming the
   module, and a warm run on an unchanged tree misses 0 times.

2. Freestanding binaries (harland, indium, prism, ritzutils, rzsh) never
   used the store: `compile_freestanding_binary` ran ritz0 and clang on
   every module on every build. harland's 51 modules and indium's bins made
   their warm plan units 50 s and 44 s, the two longest in the run. Their
   objects now come from the store, keyed like compile_binary's plus the
   target, target_os and the exact clang object flags.
"""

import importlib
import importlib.util
import json
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
for d in (str(PKG_DIR), str(PKG_DIR / "tools")):
    if d not in sys.path:
        sys.path.insert(0, d)

# By name, not `import cas`: test_tools_requirements reads a bare import as
# an undeclared third-party dependency.
cas = importlib.import_module("cas")
KEY = "7c" + "b" * 62


@pytest.fixture(autouse=True)
def private_store(tmp_path, monkeypatch):
    root = tmp_path / "cas"
    monkeypatch.setenv(cas.CAS_DIR_ENV, str(root))
    monkeypatch.delenv(cas.STATS_LOG_ENV, raising=False)
    monkeypatch.delenv("RITZ_NO_CAS", raising=False)
    monkeypatch.setenv("RITZ_PATH", str(PKG_DIR))
    monkeypatch.setattr(cas, "STATS", cas.Stats())
    return root


# --- 1. a failed build is not a miss ----------------------------------------


def _fail():
    raise cas.BuildFailed("ritz0 failed for broken.ritz")


@pytest.mark.unit
def test_failed_build_is_counted_as_failed_not_as_a_miss(private_store):
    store = cas.ArtifactStore()
    with pytest.raises(cas.BuildFailed):
        store.get_or_build(KEY, "o", _fail, identity="lexis/lib/broken.ritz")
    assert cas.STATS.misses == 0, "a build that stored nothing was counted as a miss"
    assert cas.STATS.missed == []
    assert cas.STATS.failed == [[KEY, "o", "lexis/lib/broken.ritz", str(private_store)]]


@pytest.mark.unit
def test_failed_builds_reach_the_stats_log_and_the_summary(tmp_path, monkeypatch):
    log = tmp_path / "gate.jsonl"
    monkeypatch.setenv(cas.STATS_LOG_ENV, str(log))
    with pytest.raises(cas.BuildFailed):
        cas.ArtifactStore().get_or_build(KEY, "o", _fail, identity="lexis/lib/broken.ritz")
    cas._report_stats()  # what atexit does; a failure alone is activity

    rec = json.loads(log.read_text())
    assert (rec["misses"], rec["failed"]) == (0, [[KEY, "o", "lexis/lib/broken.ritz",
                                                    str(tmp_path / "cas")]])
    s = cas.summarise(log)
    assert (s["misses"], s["compiled"]) == (0, 0)
    assert s["failed_builds"] == {f"{KEY[:12]}.o": "lexis/lib/broken.ritz"}


@pytest.mark.unit
def test_summary_reads_logs_written_before_failed_was_recorded(tmp_path):
    log = tmp_path / "gate.jsonl"
    log.write_text(json.dumps({"hits": 1, "misses": 1, "bytes_written": 0}) + "\n")
    assert cas.summarise(log)["failed_builds"] == {}


@pytest.mark.unit
def test_summary_cli_and_gate_name_the_failed_modules(tmp_path, capsys):
    log = tmp_path / "gate.jsonl"
    log.write_text(json.dumps({"hits": 3, "misses": 0, "bytes_written": 0, "missed": [],
                               "failed": [[KEY, "o", "lexis/lib/broken.ritz", "/s"]]}) + "\n")
    assert cas.main(["summary", str(log)]) == 0
    ci_local = importlib.import_module("ci_local")
    ci_local.print_cas_summary(log)
    out = capsys.readouterr().out
    for line in out.split("[ritz-cas] gate:")[1:]:
        assert "misses=0 compiled=0 failed=1 " in line
        assert "failed to build: lexis/lib/broken.ritz" in line


# --- 2. freestanding objects come from the store ----------------------------

# Records each call, then fails or writes trivial IR to the `-o` path.
STUB = textwrap.dedent(
    """\
    #!{python}
    import sys
    args = sys.argv[1:]
    with open({log!r}, "a") as f:
        f.write(" ".join(args) + "\\n")
    if {fail!r}:
        sys.stderr.write("stub ritz0: deliberate failure\\n")
        sys.exit(1)
    with open(args[args.index("-o") + 1], "w") as f:
        f.write("define void @_start() {{\\n  ret void\\n}}\\n")
    """
)

needs_clang = pytest.mark.skipif(
    subprocess.run(["sh", "-c", "command -v clang"], capture_output=True).returncode != 0,
    reason="clang not on PATH")


@pytest.fixture
def buildpy(tmp_path):
    spec = importlib.util.spec_from_file_location(f"ritz_buildpy_1896_{tmp_path.name}",
                                                  PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.get_build_cache("ritz0")._cache_dir = tmp_path / ".ritz-cache"
    return mod


class Ritz0:
    def __init__(self, tmp_path, monkeypatch, buildpy):
        self.log = tmp_path / "ritz0_calls.log"
        self.log.write_text("")
        self._stub = tmp_path / "ritz0_stub.py"
        self.fail(False)
        monkeypatch.setattr(buildpy, "RITZ0", self._stub)

    def fail(self, fail):
        self._stub.write_text(STUB.format(python=sys.executable, log=str(self.log), fail=fail))
        self._stub.chmod(self._stub.stat().st_mode | stat.S_IXUSR)

    @property
    def calls(self):
        return len(self.log.read_text().splitlines())


@pytest.fixture
def ritz0(tmp_path, monkeypatch, buildpy):
    return Ritz0(tmp_path, monkeypatch, buildpy)


def _pkg(tmp_path, *, target_os="", flags=""):
    pkg = tmp_path / "fs_pkg"
    (pkg / "src").mkdir(parents=True, exist_ok=True)
    tos = f'target_os = "{target_os}"\n' if target_os else ""
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "fs_pkg"\nversion = "0.1.0"\n\n'
        '[[bin]]\nname = "kern"\ntarget = "x86_64-unknown-none"\n'
        f"{tos}freestanding = true\n"
        + (f"\n[bin.kern.flags]\n{flags}\n" if flags else ""))
    src = pkg / "src" / "kern.ritz"
    if not src.exists():
        src.write_text("fn _start()\n    return\n")
    return pkg


def _build(buildpy, monkeypatch, pkg, *extra):
    monkeypatch.setattr(sys, "argv", ["build.py", "build", str(pkg), "--compiler", "ritz0",
                                      *extra])
    return buildpy.main() or 0  # the link outcome (no ld.lld here?) is irrelevant


@pytest.mark.unit
@needs_clang
def test_second_freestanding_build_compiles_nothing(buildpy, ritz0, tmp_path, monkeypatch):
    pkg = _pkg(tmp_path)
    _build(buildpy, monkeypatch, pkg)
    assert ritz0.calls == 1
    _build(buildpy, monkeypatch, pkg)
    assert ritz0.calls == 1, "an unchanged freestanding module was compiled again"
    assert buildpy.cas.STATS.hits >= 1


@pytest.mark.unit
@needs_clang
def test_a_hit_puts_the_stored_object_where_the_link_reads_it(
        buildpy, ritz0, tmp_path, monkeypatch, private_store):
    pkg = _pkg(tmp_path)
    _build(buildpy, monkeypatch, pkg)
    _build(buildpy, monkeypatch, pkg, "--debug")  # --debug keeps build/debug/obj
    assert ritz0.calls == 1
    kept = list((pkg / "build" / "debug" / "obj").glob("kern_*.o"))
    stored = list(private_store.rglob("*.o"))
    assert len(kept) == 1 and len(stored) == 1
    assert kept[0].read_bytes() == stored[0].read_bytes()


@pytest.mark.unit
@needs_clang
def test_editing_the_source_recompiles(buildpy, ritz0, tmp_path, monkeypatch):
    pkg = _pkg(tmp_path)
    _build(buildpy, monkeypatch, pkg)
    (pkg / "src" / "kern.ritz").write_text("fn _start()\n    return\n\nfn f() -> i32\n    1\n")
    _build(buildpy, monkeypatch, pkg)
    assert ritz0.calls == 2


@pytest.mark.unit
@needs_clang
def test_target_os_is_part_of_the_key(buildpy, ritz0, tmp_path, monkeypatch):
    # [[target_os]] conditional compilation: the same source is a different
    # module for harland.
    _build(buildpy, monkeypatch, _pkg(tmp_path))
    _build(buildpy, monkeypatch, _pkg(tmp_path, target_os="harland"))
    assert ritz0.calls == 2


@pytest.mark.unit
@needs_clang
def test_clang_object_flags_are_part_of_the_key(buildpy, ritz0, tmp_path, monkeypatch):
    _build(buildpy, monkeypatch, _pkg(tmp_path))
    _build(buildpy, monkeypatch, _pkg(tmp_path, flags="no-red-zone = true"))
    assert ritz0.calls == 2


@pytest.mark.unit
@needs_clang
def test_a_hosted_object_of_the_same_source_is_not_reused(
        buildpy, ritz0, tmp_path, monkeypatch):
    pkg = _pkg(tmp_path)
    assert buildpy.cas_object(pkg / "src" / "kern.ritz", tmp_path / "hosted.o",
                              project_root=pkg) is None
    assert ritz0.calls == 1
    _build(buildpy, monkeypatch, pkg)
    assert ritz0.calls == 2, "a hosted (-O2, no --target) object was linked into a kernel"


@pytest.mark.unit
@needs_clang
def test_a_failed_compile_fails_the_build_and_is_not_stored(
        buildpy, ritz0, tmp_path, monkeypatch, capsys):
    pkg = _pkg(tmp_path)
    ritz0.fail(True)
    assert _build(buildpy, monkeypatch, pkg) != 0
    assert _build(buildpy, monkeypatch, pkg) != 0
    assert ritz0.calls == 2
    assert "deliberate failure" in capsys.readouterr().err
    assert buildpy.cas.STATS.misses == 0
    assert [f[2] for f in buildpy.cas.STATS.failed] == ["ext/kern.ritz"] * 2


@pytest.mark.unit
@needs_clang
def test_no_cache_always_compiles(buildpy, ritz0, tmp_path, monkeypatch):
    pkg = _pkg(tmp_path)
    _build(buildpy, monkeypatch, pkg, "--no-cache")
    _build(buildpy, monkeypatch, pkg, "--no-cache")
    assert ritz0.calls == 2
