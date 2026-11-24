"""pytest plugin: a test that starts a process must be `integration` (AGAST #1805).

The suite selects tiers by marker: `make smoke` runs `-m smoke`, and smoke
excludes `integration`.  That only works if every test that compiles, links
or runs something carries the mark — and 36 subprocess-spawning files did
not.  This plugin makes the rule self-enforcing: while a test without
`integration` is in setup, call or teardown, any process it starts —
`subprocess.Popen` (and so run/check_output), `os.system`, or an
in-process ritz0 run via `ritz0_inproc` — fails that test, naming the
command.

It observes behaviour rather than grepping source, so a spawn hidden in a
helper imported from another module is caught, and a pure test in a module
that merely imports `subprocess` is not flagged.

Watching has one blind spot: a test that skips when an optional tool is
missing (`shutil.which("shellcheck")` → `pytest.skip`, or a `skipif`) never
reaches its spawn on a host without the tool, so it passes there unmarked
and fails on CI, which has the tool (AGAST #4264).  So before setup, a
non-integration test whose own source calls a spawn API (`subprocess.run`,
`os.system`, ... — see _SPAWN_CALLS) fails too, whether or not it would
skip.  This static check reads only the test function itself; helpers are
left to the runtime watch.

The converse (AGAST #4627), for a conftest that opts in (`require_spawns`;
ritz0's does, tools/ selects its ratchets by file, not by mark): a passing
`integration` test that started nothing fails.  The mark is what keeps a test
out of ritz0's `-m inproc`, so a source-only ratchet marked by habit never ran
in `make tools-ratchets`.  130 such tests were found; the source-only ones
lost the mark, and harness/integration_without_spawn.txt lists the rest.

Loaded by ritz0/conftest.py and tools/conftest.py (`pytest_plugins`; tools/
since AGAST #4092); test_spawn_guard.py loads it with `-p spawn_guard`.
"""

import ast
import contextlib
import functools
import inspect
import os
import subprocess
import textwrap

import pytest

# Spawns seen while a test runs; None when not watching.
_seen = None
# Fixtures (FixtureDef objects, by id) whose setup started a process in this
# process.  A test that uses one counts as spawning even when the fixture's
# cached value is all it touches (a module fixture compiles once).
_spawning_fixtures: set = set()

_orig_popen_init = subprocess.Popen.__init__
_orig_system = os.system


def note_spawn(what: str) -> None:
    """Record a spawn that does not go through Popen (e.g. a forked ritz0)."""
    if _seen is not None:
        _seen.append(what)


@contextlib.contextmanager
def unwatched():
    """Spawns a plugin makes for its own bookkeeping (read_guard measuring
    its scope with git, AGAST #4032) are not the test's."""
    global _seen
    saved, _seen = _seen, None
    try:
        yield
    finally:
        _seen = saved


def _describe(args) -> str:
    if isinstance(args, (str, bytes, os.PathLike)):
        return os.fsdecode(args)
    try:
        return " ".join(os.fsdecode(a) for a in args)
    except TypeError:
        return repr(args)


def _popen_init(self, args, *a, **kw):
    note_spawn(_describe(args))
    return _orig_popen_init(self, args, *a, **kw)


def _system(cmd):
    note_spawn(_describe(cmd))
    return _orig_system(cmd)


def pytest_configure(config):
    subprocess.Popen.__init__ = _popen_init
    os.system = _system


def pytest_unconfigure(config):
    subprocess.Popen.__init__ = _orig_popen_init
    os.system = _orig_system


# Calls that start a process, written as they appear in a test's source.
_SPAWN_CALLS = frozenset(
    {f"subprocess.{f}" for f in ("run", "Popen", "call", "check_call",
                                 "check_output", "getoutput", "getstatusoutput")}
    | {f"os.{f}" for f in ("system", "popen", "posix_spawn", "posix_spawnp",
                           "execv", "execve", "execvp", "execvpe",
                           "spawnv", "spawnve", "spawnvp", "spawnvpe")}
)


@functools.cache
def _static_spawns(code) -> tuple:
    """Spawn calls written in the body of the function owning `code`."""
    try:
        source = textwrap.dedent(inspect.getsource(code))
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError):
        return ()
    return tuple(sorted({
        ast.unparse(node.func) for node in ast.walk(tree)
        if isinstance(node, ast.Call) and ast.unparse(node.func) in _SPAWN_CALLS
    }))


def _check_static(item):
    """Fail an unmarked test whose own source spawns (AGAST #4264).

    Runs before setup, so neither a `skipif` mark nor a `pytest.skip` in the
    body (taken on a host missing the tool) can hide the spawn.
    """
    fn = getattr(item, "function", None)  # None for doctest and other items
    code = getattr(inspect.unwrap(fn), "__code__", None) if fn else None
    calls = _static_spawns(code) if code is not None else ()
    if calls:
        pytest.fail(
            f"{item.nodeid} calls {', '.join(calls)} but is not marked "
            f"`integration` (AGAST #1805, #4264; ritz0/harness/spawn_guard.py): a skip "
            f"when its tool is missing would hide the spawn on hosts without it.\n"
            f"Mark the test (or the module: `pytestmark = pytest.mark.integration`).",
            pytrace=False,
        )


_spawned = pytest.StashKey[bool]()
_call_passed = pytest.StashKey[bool]()
_used_fixtures = pytest.StashKey[frozenset]()


def _watch(item, static=False):
    global _seen
    if item.get_closest_marker("integration") is not None:
        return (yield from _watch_integration(item))
    if static:
        _check_static(item)
    _seen = []
    try:
        result = yield
    finally:
        seen, _seen = _seen, None
    if seen:
        shown = "\n  ".join(s[:200] for s in seen[:5])
        more = f"\n  … and {len(seen) - 5} more" if len(seen) > 5 else ""
        pytest.fail(
            f"{item.nodeid} started {len(seen)} process(es) but is not marked "
            f"`integration` (AGAST #1805; ritz0/harness/spawn_guard.py):\n  {shown}{more}\n"
            f"Mark the test (or the module: `pytestmark = pytest.mark.integration`).",
            pytrace=False,
        )
    return result


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item):
    return (yield from _watch(item, static=True))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    result = yield from _watch(item)
    item.stash[_call_passed] = True  # not reached on a failure, skip or xfail
    item.stash[_used_fixtures] = _resolved_fixtures(item)
    return result


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    result = yield from _watch(item)
    _check_spawned(item)
    return result


def _watch_integration(item):
    """Record whether a marked test spawned; it may (the mark allows it)."""
    global _seen
    saved, _seen = _seen, []
    try:
        result = yield
    finally:
        seen, _seen = _seen, saved
        if seen:
            item.stash[_spawned] = True
    return result


@pytest.hookimpl(wrapper=True)
def pytest_fixture_setup(fixturedef, request):
    if _seen is None:
        return (yield)
    before = len(_seen)
    try:
        return (yield)
    finally:
        if _seen is not None and len(_seen) > before:
            _spawning_fixtures.add(id(fixturedef))


def _resolved_fixtures(item) -> frozenset:
    """ids of the FixtureDefs the item used, by argument or by
    `request.getfixturevalue` (which its static closure does not list)."""
    ids = set()
    info = getattr(item, "_fixtureinfo", None)
    if info is not None:
        ids.update(id(d) for defs in info.name2fixturedefs.values() for d in defs)
    request = getattr(item, "_request", None)
    resolved = getattr(request, "_fixture_defs", None) or {}
    ids.update(id(d) for d in resolved.values())
    return frozenset(ids)


def _used_spawning_fixture(item) -> bool:
    return not _spawning_fixtures.isdisjoint(item.stash.get(_used_fixtures, frozenset()))


# ---- AGAST #4627: an `integration` test must start something --------------
#
# The mark keeps a test out of ritz0's `-m inproc` (conftest item 13), the set
# `make tools-ratchets` runs.  So a source-only ratchet marked by habit (often
# by a module-level `pytestmark`) never ran in a room's smoke.  A conftest
# that opts in (`require_spawns`) gets every passing `integration` test that
# started no process, ran no in-process ritz0, took no batched answer and used
# no fixture that did, failed in teardown.  Exempt: a test that asks for a
# fixture in `exempt_fixtures` (it is out of `-m inproc` anyway: under xdist
# ritz1 is built by the controller, so the worker sees no spawn), and the
# functions listed in the allowlist, the known offenders to drain.

_policy = pytest.StashKey[tuple]()


def require_spawns(config, allowlist=None, exempt_fixtures=()) -> None:
    """Opt in.  `allowlist`: a file of test functions, one per line
    (`path::[Class::]name`, no parameters; `#` comments) let off."""
    allowed = frozenset(read_allowlist(allowlist)) if allowlist else frozenset()
    config.stash[_policy] = (allowed, tuple(exempt_fixtures))


def read_allowlist(path) -> list:
    entries = []
    with open(path) as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if line:
                entries.append(line)
    return entries


def function_id(nodeid: str) -> str:
    """`nodeid` without parameters or xdist's `@group` suffix."""
    return nodeid.split("[", 1)[0].split("@", 1)[0]


def _check_spawned(item):
    """An `integration` test that passed without starting anything (AGAST #4627)."""
    policy = item.config.stash.get(_policy, None)
    if policy is None or item.get_closest_marker("integration") is None:
        return
    if not item.stash.get(_call_passed, False):
        return  # failed, skipped or xfailed: it says nothing about spawning
    if item.stash.get(_spawned, False) or _used_spawning_fixture(item):
        return
    allowed, exempt = policy
    if any(f in item.fixturenames for f in exempt):
        return
    if function_id(item.nodeid) in allowed:
        return
    log = os.environ.get("RITZ_TEST_NOSPAWN_LOG")
    if log:  # report, don't fail: how the allowlist was measured
        with open(log, "a") as fh:
            fh.write(f"{item.nodeid}\n")
        return
    pytest.fail(
        f"{item.nodeid} is marked `integration` but started no process and ran "
        f"no ritz0 (AGAST #4627; ritz0/harness/spawn_guard.py).  The mark keeps it "
        f"out of `-m inproc`, so `make tools-ratchets` never runs it.\n"
        f"If it only reads source or runs Python, drop the mark (for a module-level "
        f"`pytestmark`, mark the tests that spawn instead).  If it spawns only "
        f"through a per-process memo (cas.target_id's `clang --version`), list "
        f"the function in ritz0/harness/integration_without_spawn.txt.",
        pytrace=False,
    )
