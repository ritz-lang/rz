"""pytest configuration for the ritz0 suite.

AGAST #1392. Two things live here, and they are independent.

1. `collect_ignore_glob` — a backstop, not the fix.

   Leaked test scratch directories used to be created inside the tree under
   test and contained a `ritzlib` symlink. When the package under test was
   ritzlib itself, the symlink pointed at its own ancestor and pytest's
   collector — which follows directory symlinks — walked a cycle. The suite
   burned 739 s and collected zero tests, against a 73 s baseline. Two such
   directories existed simultaneously, so the walk branched: the cost was
   exponential in depth, which is why it presented as "the suite got slow"
   rather than as an obvious hang.

   The actual fix is `test_runner.make_scratch_dir()`, which puts scratch under
   the system temp directory so the cycle is unconstructible. This glob exists
   so that a *future* leak — from an older checkout, a task-room worktree, or a
   third-party tool — degrades collection instead of wedging it. It is
   deliberately not the primary defence: an ignore rule that silently hides
   debris is how the original `.gitignore` entries came to paper over the same
   bug twice, once for the repo root and once for cryptosec.

2. `markers` — the suite decorates tests with `@pytest.mark.unit` and
   `@pytest.mark.integration`, which were unregistered. That emitted 99
   PytestUnknownMarkWarnings per run and, more importantly, meant `-m unit`
   silently selected on a typo'd name rather than erroring.

3. `RITZ_CACHE_DIR` (AGAST #1807) — compilers keep their sig files in a cache
   directory that mirrors each source's absolute path.  Tests compile sources
   under the temp directory, so without this every run would leave a mirror
   of its tmp_path trees in ~/.cache/ritz.  The session gets a private cache,
   removed at exit; an explicit RITZ_CACHE_DIR wins.  Under xdist the
   controller sets it before the workers start, so they inherit and share it
   (fn_cache writes are atomic for exactly that reason).

4. `ritz1_bin` (AGAST #1804) — ONE build of ritz1 and the runtime start object
   per session, shared by every test that needs them.

   43 modules used to carry their own copy of `_build_ritz1()` and a module
   fixture around it, so a serial run invoked `make -C ritz1 ritz1` ~80 times,
   and an xdist run would have had several workers running make on the same
   `ritz1/build/` at once (racing on .d.tmp/.ll/.o).  Now:

   * serial run: the session fixture builds on first use;
   * xdist run: the controller builds while setting up the first worker
     (`pytest_configure_node`), before any worker runs a test, and hands each
     worker the verdict through `workerinput`.  Workers
     never run make.  The verdict travels in workerinput rather than an
     environment variable on purpose: a test that runs a nested pytest (see
     test_ritz1_bin_staleness.py) would inherit an env var and skip its own
     build, grading a stale binary.

   The rules of #1322 and #1327 carry over unchanged: always run make (it
   decides freshness from mtimes; a binary that merely exists may be stale),
   and a failed build FAILS every test that asked for ritz1, never skips it.

   `RITZ_TEST_MAKE_LOG`, if set, receives one line per make this conftest runs.
   test_ritz1_session_build.py uses it to prove an xdist session builds once.

5. `xdist_group("tree")` (AGAST #1804) — the suite runs with
   `-n <N> --dist loadgroup`.  A test that WRITES state at a fixed path in
   projects/ritz which another test also uses goes in the "tree" group, so
   the group runs on one worker, one test at a time.  Today that means:
   * any real `build.py build|run` that uses the in-tree build cache:
     build.py's BuildCache is rooted at projects/ritz (`.ritz-cache{,-ritz1}`)
     whatever the package path.  #1806 made its writes atomic and its state
     merges locked, but a compiler-hash change still wipes `objects/` under a
     lock that readers of cached objects do not take (`build --no-cache`
     bypasses the cache, RITZ_BUILD_CACHE_DIR=<tmp_path> moves it — prefer
     those);
   * running a nested session's make in the real tree
     (test_ritz1_session_build.py).
   `build.py run`'s binary is not on the list: since AGAST #2252 it links
   each source to its own projects/ritz/build/run/<digest>/, so a run of a
   tmp_path source with RITZ_BUILD_CACHE_DIR set needs no group
   (test_build_run_output_path.py, test_import_alias_match_arm.py).
   Reading in-tree sources is fine; compiling into tmp_path is fine; sig
   files are per-session (item 3).  A test that copies the tree must skip
   the paths above instead (test_ritz1_bin_staleness.py does).
   A split group still passes unless two tests collide, so
   test_xdist_group_holds.py proves it holds (AGAST #2251: it silently didn't
   on pytest 9.2.0, hence the cap in requirements.txt).

6. Scheduling (AGAST #1804) — xdist hands out work in collection order.
   `@pytest.mark.slow` tests (minutes on their own) and xdist_group members
   (which run one after another on a single worker) are moved to the front,
   stably, so neither becomes the tail of a parallel run.

7. `smoke` (AGAST #1803) — the in-process subset `make smoke` runs with
   `pytest -m smoke`.  The marker is applied here from SMOKE_FILES, the ONE
   list of files in the tier, rather than by decorating tests, so the tier is
   readable and editable in one place.  Within a listed file a test is smoke
   unless it is `integration`-marked or asks for `ritz1_bin`/`ritz_start`:
   smoke runs before ritz1 is built and must not build it.  Run it serially
   (no `-n`): under xdist the controller builds ritz1 before any worker starts
   (item 4), which is exactly the cost the smoke tier avoids.

8. `ritz0_oracle` / `run_ritz0` (AGAST #1805) — ritz0 without launching
   ritz0.  ~600 `python3 ritz0.py` processes per session each spent ~0.8 s
   importing the emitter and llvmlite to compile a program in milliseconds.
   ritz0_inproc.py forks each compile from a forkserver that has ritz0
   imported (a fresh process per compile, so emitter state cannot leak) and
   caches by sha256 of the inputs.  Use `run_ritz0(args, cwd=, env=)` where a
   test would `subprocess.run(["python3", RITZ0, *args])`, and
   `ritz0_oracle(src) -> Oracle(ir_ok, stdout, rc, diagnostics)` for "what
   does ritz0 make of this single-module program".  Both are importable
   (`from ritz0_inproc import ...`) and offered as fixtures.  Set
   RITZ_TEST_RITZ0_LOG to count launches (`inproc `-tagged lines are forks).

9. `spawn_guard` (AGAST #1805) — a test that starts any process (or runs
   ritz0 in-process) without `@pytest.mark.integration` fails, naming the
   command.  So `-m "not integration"` really is the no-subprocess tier.
   The converse (AGAST #4627): a passing `integration` test that started
   nothing, itself or through a fixture, fails too, since the mark is what
   keeps a source-only ratchet out of `-m inproc` (item 13).  A test asking
   for a ritz1-building fixture is exempt (it is not inproc anyway), and
   harness/integration_without_spawn.txt lists the known offenders.

10. `fast_link` (AGAST #2793) — `fast_link.clang(cmd, **kw)` stands in for
   `subprocess.run(clang_cmd, **kw)` on a link expected to succeed: llvmlite
   codegen in a helper process plus clang's own `ld` line, ~6 ms instead of
   clang's ~50 ms startup.  Anything it does not model, and every failure,
   runs real clang, so a refusal's message is clang's.  Importable and offered
   as the `clang_link` fixture; RITZ_TEST_LINK=clang turns it off.

11. `batched` (AGAST #2806) — a matrix file marked `pytest.mark.batched`
   compiles CHUNK of a test function's rows as one program per compiler
   (ritz0/harness/batching.py).  `pytest_pyfunc_call` below runs such a test with
   batching on and, if it fails on a batched answer, again with it off, so
   every failure is the row's own per-row compile.  A row that could lean on
   another row's import or generic instance is compiled alone too, and gets
   no batched answer if it does (AGAST #2867).  RITZ_TEST_BATCH=0 turns it
   off.

12. `--only-file=PATH` (AGAST #3623, ritz0/only_files.py) — collect only the
   listed files, in the listed order.  The gate's likely-first pre-pass uses
   it: as 60 file arguments the same files cost every xdist worker ~8 s of
   collection, since pytest re-walks this directory once per file argument.

13. `inproc` (AGAST #4622) — every test that is not `integration`-marked and
   asks for no ritz1-building fixture (`is_inproc_item`, the rule smoke uses
   within its files).  It compiles nothing (item 9), so it runs before ritz1
   is built.  `make tools-ratchets` runs `-m inproc`, which is how a
   room's smoke reaches the ritz1 source-layout ratchets kept here
   (test_ritz1_sema_walk_layout.py and the like).  A test that only reads
   source needs no marker: leave off `integration` and it is in.

14. `--no-ritz1-build` (AGAST #4672) — the session builds nothing: the
   verdict (item 4) is a refusal naming the option, so a test that asks for
   ritz1 fails, never skips.  `make tools-ratchets` passes it to run
   `-m inproc` under xdist, whose controller would otherwise build ritz1
   before any worker starts, though no inproc test uses it.  An option, not
   an environment variable, for item 4's reason: a nested pytest must not
   inherit it.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# The test harness lives in ritz0/harness/ (AGAST #3915): outside the files
# ritz0 imports, so editing it, or this file, leaves the compiler hash (and
# every sig and cached artifact) alone.  Tests still `import fast_link` etc.
# by bare name.
#
# The tests themselves live in ritz0/tests/ (AGAST #4373).  pytest inserts a
# test file's own directory (tests/) on sys.path, not ritz0/, so put ritz0 on
# it explicitly: the tests import the compiler modules (`import lexer`, ...)
# by bare name.  Without this, `pytest ritz0/tests/test_lexer.py` from
# projects/ritz fails, though `cd ritz0 && python -m pytest` would not (the
# interpreter puts the cwd on sys.path).
RITZ0_DIR = str(Path(__file__).resolve().parent)
if RITZ0_DIR not in sys.path:
    sys.path.append(RITZ0_DIR)
HARNESS_DIR = str(Path(RITZ0_DIR) / "harness")
if HARNESS_DIR not in sys.path:
    sys.path.append(HARNESS_DIR)
# Tests also import sibling *test* modules by bare name (from test_ref_into_value
# import COMPILERS).  pytest's prepend import mode puts a test file's own
# directory on sys.path, but that is an implementation detail of one import
# mode: name tests/ here so the imports hold even under an explicit
# --import-mode=importlib, a nested pytest, or a direct `pytest <file>` run.
TESTS_DIR = str(Path(RITZ0_DIR) / "tests")
if TESTS_DIR not in sys.path:
    sys.path.append(TESTS_DIR)

import batching  # noqa: E402
import fast_link  # noqa: E402
import ritz0_inproc  # noqa: E402
import refusal_capture  # noqa: E402

pytest_plugins = ["spawn_guard", "cost_meter", "only_files", "read_guard"]

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ1_SELFHOSTED = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

# Key for the build verdict, both in config.stash (controller / serial run) and
# in xdist's `workerinput` (workers).  The verdict is an error string, or "" for
# a successful build.
_BUILD_KEY = "ritz1_session_build"
_build_verdict = pytest.StashKey[str]()

_SESSION_CACHE = None

# The smoke tier's files (item 7), relative to ritz0/.  In-process tests of the
# front end and of the build/test tooling: no compiler subprocess, no ritz1.
# tools/test_smoke.py fails if an entry no longer exists or contributes no test.
SMOKE_FILES = (
    "tests/test_parser.py",
    "tests/test_lexer.py",
    "tests/test_const_eval.py",
    "tests/test_type_checker.py",
    "tests/test_move_checker.py",
    "tests/test_monomorph.py",
    "tests/test_metadata.py",
    "tests/test_export_map.py",
    "tests/test_attrs.py",
    "tests/test_reritz_integration.py",
    "emitter/test_struct_layout.py",
    "emitter/test_fn_cache.py",
    "tests/test_runner_source_roots.py",
    "tests/test_scratch_dir_location.py",
    "tests/test_no_artifact_skips.py",
    "tests/test_build.py",
)
_SMOKE_PATHS = frozenset((Path(__file__).resolve().parent / f) for f in SMOKE_FILES)
# Fixtures that build ritz1; a test that asks for one is not smoke.
_BUILD_FIXTURES = ("ritz1_bin", "ritz_start", "ritz1_selfhosted")
# Item 9's `integration` tests let off starting nothing; only remove entries.
NOSPAWN_ALLOWLIST = Path(HARNESS_DIR) / "integration_without_spawn.txt"


def is_inproc_item(item) -> bool:
    """Whether a collected test compiles nothing and builds nothing (item 13).

    Not `integration`-marked (spawn_guard, item 9, fails such a test that
    starts a process) and asks for no fixture that builds ritz1.
    """
    if item.get_closest_marker("integration") is not None:
        return False
    return not any(f in item.fixturenames for f in _BUILD_FIXTURES)


def is_smoke_item(item) -> bool:
    """Whether a collected test belongs to the smoke tier (item 7)."""
    if Path(item.path).resolve() not in _SMOKE_PATHS:
        return False
    return is_inproc_item(item)


collect_ignore_glob = [
    "tmp*",
    "ritz_test_*",
    "ritz_batch_test_*",
]


def _ritz1_stale() -> bool:
    """Whether to hand ritz1 to make.  Always: existence is not freshness.

    test_ritz1_bin_staleness.py swaps the return line below for the old
    build-if-missing rule and asserts the two disagree on a broken tree, so
    keep it a single literal line.
    """
    return True  # make decides freshness from mtimes (#1322)


def _ritz1_jobs() -> str:
    """The repo's -j rule for ritz1 builds (AGAST #1802): min(nproc, 8)."""
    proc = subprocess.run(
        ["sh", str(RITZ_ROOT / "scripts" / "ritz1-jobs.sh")],
        capture_output=True, text=True, check=True,
    )
    return proc.stdout.strip()


def _make(args: list[str], timeout: int) -> subprocess.CompletedProcess:
    log = os.environ.get("RITZ_TEST_MAKE_LOG")
    if log:
        with open(log, "a") as f:
            f.write(f"{os.getpid()} make {' '.join(args)}\n")
    return subprocess.run(
        ["make", *args],
        cwd=RITZ_ROOT,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def build_ritz1_artifacts() -> str:
    """Bring ritz1 and the runtime start object up to date.

    Returns "" on success, otherwise the reason (with make's output tail).
    """
    if _ritz1_stale():
        proc = _make(["-j", _ritz1_jobs(), "-C", "ritz1", "ritz1"], timeout=1800)
        if proc.returncode != 0 or not RITZ1_BIN.exists():
            return (
                f"could not build ritz1 (make exit {proc.returncode}):\n"
                f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
            )
    # RITZ_START is gitignored; build it rather than assume it exists (#1327).
    proc = _make(["-C", "runtime", RITZ_START.name], timeout=300)
    if proc.returncode != 0 or not RITZ_START.exists():
        return (
            f"could not build the runtime start object {RITZ_START}:\n"
            f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
        )
    return ""


_NO_BUILD = (
    "ritz1 was not built: this session ran with --no-ritz1-build (conftest "
    "item 14), so a test that needs ritz1 cannot run in it"
)


def pytest_addoption(parser):
    parser.addoption(
        "--no-ritz1-build", action="store_true", default=False,
        help="build neither ritz1 nor the runtime start object; tests that "
             "ask for them fail (conftest item 14)",
    )


def _session_verdict(config) -> str:
    """The build verdict for this session, building now if nobody has yet."""
    if config.getoption("--no-ritz1-build"):
        return _NO_BUILD
    workerinput = getattr(config, "workerinput", None)
    if workerinput is not None:
        if _BUILD_KEY not in workerinput:
            return (
                "xdist worker started without the controller's ritz1 build "
                "verdict; conftest.pytest_configure_node did not run"
            )
        return workerinput[_BUILD_KEY]
    if _build_verdict not in config.stash:
        config.stash[_build_verdict] = build_ritz1_artifacts()
    return config.stash[_build_verdict]


def _warm_process_memos() -> None:
    """Item 9: fill the per-process memos that spawn, before any test runs.

    cas.target_id() runs `clang --version` once per process.  Left to the
    tests, whichever test reached it first on an xdist worker spawned and the
    rest did not, so spawn_guard's "an `integration` test must start
    something" passed or failed a test by scheduling (AGAST #4627).  Filled
    here, no test spawns through it, on every run.
    """
    import importlib.util
    cas = sys.modules.get("cas")
    if cas is None:
        spec = importlib.util.spec_from_file_location("cas", RITZ_ROOT / "cas.py")
        cas = importlib.util.module_from_spec(spec)
        sys.modules["cas"] = cas
        spec.loader.exec_module(cas)
    cas.target_id()


def pytest_configure(config):
    global _SESSION_CACHE
    # AGAST #4669: with RITZ_REFUSAL_CAPTURE set, record the in-process
    # sources the ritz0-only test files lex (ritz0/harness/refusal_capture.py).
    refusal_capture.install_lexer_hook()
    if not os.environ.get("RITZ_CACHE_DIR"):
        _SESSION_CACHE = tempfile.mkdtemp(prefix="ritz-test-cache-")
        os.environ["RITZ_CACHE_DIR"] = _SESSION_CACHE
    config.addinivalue_line(
        "markers", "unit: fast, in-process test with no compiler subprocess"
    )
    config.addinivalue_line(
        "markers", "integration: drives a real compile/link/run subprocess"
    )
    config.addinivalue_line(
        "markers", "slow: minutes on its own; scheduled first under xdist"
    )
    config.addinivalue_line(
        "markers", "smoke: in the `make smoke` tier; applied from SMOKE_FILES"
    )
    config.addinivalue_line(
        "markers", "batched: matrix rows share one compile per compiler (item 11)"
    )
    config.addinivalue_line(
        "markers", "inproc: no integration mark, no ritz1 build fixture (item 13)"
    )
    # Item 9: an `integration` test must start something (AGAST #4627).
    config.pluginmanager.get_plugin("spawn_guard").require_spawns(
        config, allowlist=NOSPAWN_ALLOWLIST, exempt_fixtures=_BUILD_FIXTURES)
    _warm_process_memos()


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    """Item 11: a `batched` test runs batched, then per-row if that fails."""
    return batching.pyfunc_call(pyfuncitem)


# tryfirst: the marker must be on the items before pytest's own `-m`
# deselection, which also runs in this hook.
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    """Mark the smoke tier; then slow tests first, xdist_group members, the rest.

    The order is deterministic (a stable sort), so every xdist worker collects
    the same order.
    """
    for item in items:
        if is_smoke_item(item):
            item.add_marker(pytest.mark.smoke)
        if is_inproc_item(item):
            item.add_marker(pytest.mark.inproc)

    def rank(item):
        if item.get_closest_marker("slow") is not None:
            return 0
        if item.get_closest_marker("xdist_group") is not None:
            return 1
        return 2
    items.sort(key=rank)
    # Item 11, after the sort: a batch's xdist_group is not the "tree" kind.
    batching.assign_groups(items)


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node):
    """xdist controller hook: hand each worker the session's build verdict.

    Runs on the controller while it sets up each worker, before any worker
    executes a test; the first call builds, later ones reuse the verdict.
    """
    node.workerinput[_BUILD_KEY] = _session_verdict(node.config)


def pytest_unconfigure(config):
    if _SESSION_CACHE is not None:
        shutil.rmtree(_SESSION_CACHE, ignore_errors=True)


@pytest.fixture(scope="session")
def ritz1_bin(request) -> Path:
    """Path to an up-to-date ritz1; the runtime start object is built too.

    Fails — never skips — when the build fails: a skipped test is
    indistinguishable from a passing one in aggregate output (#1327).
    """
    verdict = _session_verdict(request.config)
    if verdict:
        pytest.fail(verdict)
    return RITZ1_BIN


@pytest.fixture(scope="session")
def ritz_start(ritz1_bin) -> Path:
    """Path to the runtime start object; built alongside ritz1 by `ritz1_bin`."""
    return RITZ_START


@pytest.fixture(scope="session")
def ritz1_selfhosted() -> Path:
    """The compiler ritz1 built from its own source (AGAST #4541).

    `make -C ritz1 bootstrap` builds it; the gate's "Build ritz1 +
    ritz1_selfhosted" step runs that before the ritz0 unit tests.  Fails,
    never skips, when it is absent: a skipped parity test is
    indistinguishable from a passing one in aggregate output (#1327).
    """
    if not RITZ1_SELFHOSTED.exists():
        pytest.fail(
            f"{RITZ1_SELFHOSTED} is missing; run `make -C ritz1 bootstrap` "
            f"(the gate's bootstrap step does)")
    return RITZ1_SELFHOSTED


@pytest.fixture(scope="session")
def ritz0_oracle():
    """`ritz0_oracle(src) -> Oracle(ir_ok, stdout, rc, diagnostics)` (item 8)."""
    return ritz0_inproc.ritz0_oracle


@pytest.fixture(scope="session")
def run_ritz0():
    """`run_ritz0(args, cwd=, env=, timeout=)`: in-process `ritz0.py` (item 8)."""
    return ritz0_inproc.run_ritz0


@pytest.fixture(scope="session")
def clang_link():
    """`clang_link(cmd, **kw)`: `subprocess.run` for a clang link (item 10)."""
    return fast_link.clang


def pytest_runtest_logreport(report):
    # AGAST #4669: the ritz0-only tests that ran, for tools/refusal_parity.py's
    # strict-xpass rule.  Off (one environ lookup) unless capturing.
    if report.when == "call" and os.environ.get(refusal_capture.ENV):
        refusal_capture.on_test_ran(report.nodeid)
