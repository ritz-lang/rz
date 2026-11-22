"""ritzlib.process takes references, not raw pointers (AGAST #3750).

#1481 gave ritzlib.process a StrView / Span API (spawn, find_command,
process_write_all) and kept the older *u8 forms as wrappers. #3750 finishes
the job:

1. The fns that act on a live Process take `p: @&Process` (they close fds,
   set `waited`), and the read-only process_valid takes `p: @Process`. With a
   raw `*Process` any `@p` fit, and nothing said which calls mutate.
2. result_success returns bool, not a 1/0 i32, and result_code is gone:
   it only returned `r.exit_code`.
3. The raw wrappers are deleted: spawn_cstr, spawn_args, spawn_full,
   find_command_in_path, process_write, process_write_str. spawn_env
   (cmd, args, env: Span<StrView>) replaces spawn_full's explicit envp.

#4298 moves every Err to ritzlib.errno's `Errno` (as #4248 did for fs):

4. spawn / spawn_env return Result<Process, Errno>; process_write_all,
   process_read_stdout and process_read_stderr return Result<i64, Errno>
   (Err(BadF) once the pipe is closed) instead of -1 / a negative errno;
   process_wait returns Result<ProcessResult, Errno> (Err(Child) when there
   is nothing left to wait for) instead of an exit_code of -1.  No pub fn
   body has a `return -1` / `return null` sentinel.

These are text checks on the source, so they cost no compile. What the fns
do is covered by ritzlib/tests/test_process_api.ritz and
test_process_env.ritz, and examples/tier5_async/80_process.
"""

import re
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = RITZ_ROOT.parent.parent
PROCESS = RITZ_ROOT / "ritzlib" / "process.ritz"

MUTATING = [
    "close_stdin",
    "read_stdout",
    "read_stdout_all",
    "read_line",
    "read_stderr",
    "read_stderr_all",
    "wait",
    "kill",
    "close_pipes",
    "cleanup",
]

DELETED = [
    "spawn_cstr",
    "spawn_args",
    "spawn_full",
    "find_command_in_path",
    "process_write",
    "process_write_str",
    "result_code",
]

# Build output, not source.
SKIP_PARTS = {"build", ".git", "node_modules", "__pycache__", "out"}


def _signature(name: str) -> str:
    """The `pub fn name(...)` line of method `name` in process.ritz."""
    text = PROCESS.read_text()
    m = re.search(rf"^\s*pub fn {name}\((.*)$", text, re.MULTILINE)
    assert m, f"process.ritz has no `pub fn {name}(`"
    return m.group(0).lstrip()


def _first_param_type(name: str) -> str:
    sig = _signature(name)
    m = re.match(rf"\s*pub fn {name}\(\s*\w+\s*:\s*([^,)]+)", sig)
    assert m, f"cannot read the first parameter of: {sig}"
    return m.group(1).strip()


@pytest.mark.parametrize("name", MUTATING)
def test_mutating_fn_takes_mut_ref(name):
    assert _first_param_type(name) == "@&Process"


def test_process_valid_takes_shared_ref():
    assert _first_param_type("valid") == "@Process"


def test_result_success_returns_bool():
    sig = _signature("success")
    assert _first_param_type("success") == "@ProcessResult"
    assert sig.rstrip().endswith("-> bool"), sig


def test_spawn_env_takes_views():
    sig = _signature("spawn_env")
    assert re.fullmatch(
        r"pub fn spawn_env\(cmd: StrView, args: Span<StrView>, env: Span<StrView>\)"
        r" -> Result<Process, Errno>",
        sig.rstrip(),
    ), sig


RESULT_SIGNATURES = [
    "pub fn spawn(cmd: StrView, args: Span<StrView>) -> Result<Process, Errno>",
    "pub fn write_all(self: @&Process, data: StrView) -> Result<i64, Errno>",
    "pub fn read_stdout(self: @&Process, buf: Span<u8>) -> Result<i64, Errno>",
    "pub fn read_stderr(self: @&Process, buf: Span<u8>) -> Result<i64, Errno>",
    "pub fn wait(self: @&Process) -> Result<ProcessResult, Errno>",
]


@pytest.mark.parametrize("sig", RESULT_SIGNATURES, ids=lambda s: s.split("(")[0][7:])
def test_errno_result_signature(sig):
    name = sig.split("(")[0][len("pub fn "):]
    assert _signature(name).rstrip() == sig


def _pub_fn_bodies():
    lines = PROCESS.read_text().splitlines()
    out = []
    for i, line in enumerate(lines):
        m = re.match(r"^\s*pub fn (\w+)\(", line)
        if not m:
            continue
        body = []
        for nxt in lines[i + 1:]:
            if nxt.strip() and not nxt[0].isspace():
                break
            body.append(nxt)
        out.append((m.group(1), line, "\n".join(body)))
    return out


def test_no_i32_errno_result():
    offenders = [sig for _, sig, _ in _pub_fn_bodies() if re.search(r"Result<.*,\s*i32>", sig)]
    assert offenders == []


def test_no_sentinel_return():
    offenders = [
        name for name, _, body in _pub_fn_bodies()
        if re.search(r"\breturn\s+(-1\b|null\b|-\()", body)
    ]
    assert offenders == []


@pytest.mark.parametrize("name", DELETED)
def test_wrapper_is_deleted(name):
    text = PROCESS.read_text()
    assert not re.search(rf"^\s*(pub\s+)?fn {name}\(", text, re.MULTILINE)


IMPORTS_PROCESS = re.compile(r"^\s*import\s+ritzlib\.process\b", re.MULTILINE)


def _live_files():
    """process.ritz, the ritzlib reference, and every .ritz that imports it.

    Only importers: harland's kernel has a `spawn_args` syscall of its own.
    Symlinks are skipped (a link would repeat its target).
    """
    yield PROCESS
    yield RITZ_ROOT / "docs" / "STDLIB_REFERENCE.md"
    for path in WORKSPACE.joinpath("projects").rglob("*.ritz"):
        rel = path.relative_to(WORKSPACE)
        if SKIP_PARTS.intersection(rel.parts) or path.is_symlink():
            continue
        if path == PROCESS or not path.is_file():
            continue
        if IMPORTS_PROCESS.search(path.read_text(errors="replace")):
            yield path


def test_nothing_calls_a_deleted_wrapper():
    """No live source calls, or the reference lists, a deleted fn."""
    pat = re.compile(r"(?<![\w.])(" + "|".join(DELETED) + r")\s*\(|`(" + "|".join(DELETED) + r")`")
    offenders = []
    for path in _live_files():
        for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if pat.search(line):
                offenders.append(f"{path.relative_to(WORKSPACE)}:{i}: {line.strip()}")
    assert offenders == []
