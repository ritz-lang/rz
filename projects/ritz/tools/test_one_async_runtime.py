"""ritzlib has one async runtime (AGAST #1855).

There were five: async.ritz (placeholders), executor.ritz, async_runtime.ritz,
async_tasks.ritz (the live one: tome, valet, mausoleum) and async/*, a fork of
async_tasks that had fallen behind it. Each one defined some of `Task`,
`Executor`, `run_tasks` and `task_server_run`, so a program could not link two
of them, and a fix to one never reached the others.

What is left, all under ritzlib/async/:

    tasks.ritz        Task, TaskPool, run_tasks, TaskServer: N tasks, one ring
    runtime.ritz      Runtime, block_on: one future, one ring
    blocking_fs.ritz  `async fn` file calls that block (it was async_fs.ritz,
                      a name that promised io_uring and delivered read(2))

These tests are the ticket's acceptance grep, kept running so the runtimes
cannot quietly grow back. Behaviour is tested by
ritzlib/tests/test_async_server.ritz and the tier5_async examples.
"""

import re
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZLIB = RITZ_ROOT / "ritzlib"
PROJECTS = RITZ_ROOT.parent

RETIRED_FILES = [
    "async.ritz",
    "async_fs.ritz",
    "async_runtime.ritz",
    "async_tasks.ritz",
    "executor.ritz",
    "async/executor.ritz",
    "async/io.ritz",
    "async/mod.ritz",
    "async/server.ritz",
    "async/task.ritz",
]

# Each of these was defined by at least two runtimes.
ONE_DEFINITION = [
    ("struct", "Task"),
    ("struct", "TaskPool"),
    ("struct", "TaskServer"),
    ("struct", "Runtime"),
    ("fn", "spawn_task"),
    ("fn", "run_tasks"),
    ("fn", "task_server_run"),
    ("fn", "task_server_run_multishot"),
    ("fn", "block_on"),
]

RETIRED_IMPORT = re.compile(
    r"^\s*(?:pub\s+)?import\s+ritzlib\."
    r"(?:async_tasks|async_runtime|async_fs|executor"
    r"|async(?=\s|$|\{)"
    r"|async\.(?:mod|task|io|server|executor)\b)",
    re.MULTILINE,
)


def _definitions(kind: str, name: str) -> list[str]:
    pattern = re.compile(rf"^\s*(?:pub\s+)?{kind}\s+{name}\b", re.MULTILINE)
    return [
        str(path.relative_to(RITZLIB))
        for path in sorted(RITZLIB.rglob("*.ritz"))
        if "tests" not in path.relative_to(RITZLIB).parts
        and pattern.search(path.read_text(encoding="utf-8"))
    ]


@pytest.mark.unit
@pytest.mark.parametrize("relative", RETIRED_FILES)
def test_retired_runtime_file_is_gone(relative):
    assert not (RITZLIB / relative).exists()


@pytest.mark.unit
@pytest.mark.parametrize("kind,name", ONE_DEFINITION)
def test_exactly_one_definition(kind, name):
    assert len(_definitions(kind, name)) == 1, _definitions(kind, name)


@pytest.mark.unit
def test_no_executor_struct_survives():
    """Runtime took over Executor's job, and its name would be a second one."""
    assert _definitions("struct", "Executor") == []


@pytest.mark.unit
def test_nothing_imports_a_retired_module():
    importers = [
        str(path.relative_to(PROJECTS))
        for path in sorted(PROJECTS.rglob("*.ritz"))
        if path.is_file()
        and RETIRED_IMPORT.search(path.read_text(encoding="utf-8", errors="replace"))
    ]
    assert importers == []


@pytest.mark.unit
def test_bootstrap_ritzlib_has_no_link_to_a_retired_module():
    """ritz1/bootstrap_ritzlib/ mirrors ritzlib/ in symlinks; see test_ritzlib_no_eq."""
    links = RITZ_ROOT / "ritz1" / "bootstrap_ritzlib"
    assert [path.name for path in sorted(links.iterdir()) if not path.exists()] == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "line",
    [
        "import ritzlib.async",
        "import ritzlib.async_tasks",
        "import ritzlib.async_tasks {",
        "import ritzlib.async_runtime",
        "import ritzlib.async_fs",
        "import ritzlib.executor",
        "import ritzlib.async.task",
        "import ritzlib.async.executor",
    ],
)
def test_retired_import_pattern_matches(line):
    """The guard above is only as good as this pattern."""
    assert RETIRED_IMPORT.search(line)


@pytest.mark.unit
@pytest.mark.parametrize(
    "line",
    [
        "import ritzlib.async_net",
        "import ritzlib.async.tasks",
        "import ritzlib.async.runtime",
        "import ritzlib.async.blocking_fs",
    ],
)
def test_live_imports_are_not_retired(line):
    assert not RETIRED_IMPORT.search(line)
