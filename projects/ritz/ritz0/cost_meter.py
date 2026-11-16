"""pytest plugin: what each test file costs, in CPU-seconds (AGAST #3453).

LARB review/5 tooling F1: the suite grew from 2,898 to 39,054 tests in three
weeks, and with it the gate.  This plugin measures every test, and
`tools/check_test_budget.py` holds the result to `tools/test_budget.toml`.

What is measured is CPU time, not wall time: the test process's user+system
time plus that of every child it waited for (`os.times()`'s children_* --
where a compile, a link or a forked ritz0 spends it), over the test's setup,
call and teardown.  On a loaded gate host the same tree's pytest step ran
anywhere from 223 to 752 s; CPU-seconds barely move with load, so a budget on
them goes red on a slower test, not on a busier host.  Wall time is recorded
alongside, for the log.

    --cost-report=PATH   write {"wall_s", "cpu_s", "files": {file: {"tests",
                         "cpu_s", "wall_s"}}} to PATH at the end of the run,
                         and print the costliest files in the terminal summary

Each test's CPU is measured where it runs (an xdist worker) and travels to the
controller as a `user_properties` entry, which xdist already serialises.

Loaded by ritz0/conftest.py (`pytest_plugins`); tools/test_check_test_budget.py
loads it with `-p cost_meter`.
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path

import pytest

_PROP = "cost_cpu_s"
_cpu_key = pytest.StashKey[float]()
# Files listed in the terminal summary, costliest first.
SUMMARY_FILES = 25


def _cpu() -> float:
    t = os.times()
    return t.user + t.system + t.children_user + t.children_system


def pytest_addoption(parser):
    parser.addoption(
        "--cost-report", metavar="PATH", default=None,
        help="write per-file CPU/wall test-seconds as JSON (AGAST #3453)")


def _measure(item):
    start = _cpu()
    try:
        return (yield)
    finally:
        item.stash[_cpu_key] = item.stash.get(_cpu_key, 0.0) + (_cpu() - start)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item):
    return (yield from _measure(item))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    return (yield from _measure(item))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    try:
        return (yield from _measure(item))
    finally:
        # The teardown report is made after this hook, from item.user_properties.
        item.user_properties.append((_PROP, round(item.stash.get(_cpu_key, 0.0), 4)))


class _Collector:
    """Sums the reports on the process that sees all of them (xdist's controller)."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.files = defaultdict(lambda: {"tests": 0, "cpu_s": 0.0, "wall_s": 0.0})
        self.start = time.monotonic()
        self.wall = 0.0

    def pytest_runtest_logreport(self, report):
        f = self.files[report.nodeid.split("::", 1)[0]]
        f["wall_s"] += report.duration
        if report.when == "teardown":
            f["tests"] += 1
            f["cpu_s"] += sum(v for k, v in report.user_properties if k == _PROP)

    def data(self) -> dict:
        files = {
            name: {**v, "cpu_s": round(v["cpu_s"], 3), "wall_s": round(v["wall_s"], 3)}
            for name, v in sorted(self.files.items())
        }
        return {
            "wall_s": round(self.wall, 3),
            "cpu_s": round(sum(v["cpu_s"] for v in files.values()), 3),
            "files": files,
        }

    def pytest_sessionfinish(self, session):
        self.wall = time.monotonic() - self.start
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.data(), indent=1) + "\n")
        os.replace(tmp, self.path)

    def pytest_terminal_summary(self, terminalreporter):
        d = self.data()
        tr = terminalreporter
        tr.write_sep("=", f"{SUMMARY_FILES} costliest test files by CPU (cost_meter, AGAST #3453)")
        ranked = sorted(d["files"].items(), key=lambda kv: -kv[1]["cpu_s"])
        tr.write_line(f"{'cpu_s':>9} {'wall_s':>9} {'tests':>6}  file")
        for name, v in ranked[:SUMMARY_FILES]:
            tr.write_line(f"{v['cpu_s']:9.1f} {v['wall_s']:9.1f} {v['tests']:6d}  {name}")
        tr.write_line(
            f"suite: {d['cpu_s']:.1f} CPU-s in {d['wall_s']:.1f} s wall, "
            f"{sum(v['tests'] for v in d['files'].values())} tests, "
            f"{len(d['files'])} files -> {self.path}")


def pytest_configure(config):
    path = config.getoption("--cost-report")
    if path and not hasattr(config, "workerinput"):
        config.pluginmanager.register(_Collector(path), "cost_meter_collector")
