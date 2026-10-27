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

Loaded by ritz0/conftest.py (`pytest_plugins`); test_spawn_guard.py loads it
with `-p spawn_guard`.
"""

import os
import subprocess

import pytest

# Spawns seen while a non-integration test runs; None when not watching.
_seen = None

_orig_popen_init = subprocess.Popen.__init__
_orig_system = os.system


def note_spawn(what: str) -> None:
    """Record a spawn that does not go through Popen (e.g. a forked ritz0)."""
    if _seen is not None:
        _seen.append(what)


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


def _watch(item):
    global _seen
    if item.get_closest_marker("integration") is not None:
        return (yield)
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
            f"`integration` (AGAST #1805; ritz0/spawn_guard.py):\n  {shown}{more}\n"
            f"Mark the test (or the module: `pytestmark = pytest.mark.integration`).",
            pytrace=False,
        )
    return result


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item):
    return (yield from _watch(item))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    return (yield from _watch(item))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    return (yield from _watch(item))
