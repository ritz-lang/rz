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
   * any real `build.py build|run` WITHOUT `--no-cache`: build.py's
     BuildCache is rooted at projects/ritz (`.ritz-cache{,-ritz1}`) whatever
     the package path.  #1806 made its writes atomic and its state merges
     locked, but a compiler-hash change still wipes `objects/` under a lock
     that readers of cached objects do not take (`--no-cache` bypasses the
     cache — prefer that);
   * `build.py run`, which writes projects/ritz/build/<name>;
   * running a nested session's make in the real tree
     (test_ritz1_session_build.py).
   Reading in-tree sources is fine; compiling into tmp_path is fine; sig
   files are per-session (item 3).  A test that copies the tree must skip
   the paths above instead (test_ritz1_bin_staleness.py does).

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
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

import ritz0_inproc

pytest_plugins = ["spawn_guard"]

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
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
    "test_parser.py",
    "test_lexer.py",
    "test_const_eval.py",
    "test_symbol_table.py",
    "test_type_checker.py",
    "test_move_checker.py",
    "test_monomorph.py",
    "test_metadata.py",
    "test_export_map.py",
    "test_attrs.py",
    "test_packaging.py",
    "test_reritz_integration.py",
    "emitter/test_struct_layout.py",
    "emitter/test_fn_cache.py",
    "test_runner_source_roots.py",
    "test_scratch_dir_location.py",
    "test_no_artifact_skips.py",
    "test_build.py",
)
_SMOKE_PATHS = frozenset((Path(__file__).resolve().parent / f) for f in SMOKE_FILES)
# Fixtures that build ritz1; a test that asks for one is not smoke.
_BUILD_FIXTURES = ("ritz1_bin", "ritz_start")


def is_smoke_item(item) -> bool:
    """Whether a collected test belongs to the smoke tier (item 7)."""
    if Path(item.path).resolve() not in _SMOKE_PATHS:
        return False
    if item.get_closest_marker("integration") is not None:
        return False
    return not any(f in item.fixturenames for f in _BUILD_FIXTURES)


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


def _session_verdict(config) -> str:
    """The build verdict for this session, building now if nobody has yet."""
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


def pytest_configure(config):
    global _SESSION_CACHE
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

    def rank(item):
        if item.get_closest_marker("slow") is not None:
            return 0
        if item.get_closest_marker("xdist_group") is not None:
            return 1
        return 2
    items.sort(key=rank)


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
def ritz0_oracle():
    """`ritz0_oracle(src) -> Oracle(ir_ok, stdout, rc, diagnostics)` (item 8)."""
    return ritz0_inproc.ritz0_oracle


@pytest.fixture(scope="session")
def run_ritz0():
    """`run_ritz0(args, cwd=, env=, timeout=)`: in-process `ritz0.py` (item 8)."""
    return ritz0_inproc.run_ritz0
