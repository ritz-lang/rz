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

# Spawns seen while a non-integration test runs; None when not watching.
_seen = None

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


def _watch(item, static=False):
    global _seen
    if item.get_closest_marker("integration") is not None:
        return (yield)
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
    return (yield from _watch(item))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    return (yield from _watch(item))
