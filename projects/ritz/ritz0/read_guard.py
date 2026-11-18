"""pytest plugin: a ritz0 test may not read what a gate may skip it for (AGAST #4032).

tools/ritz0_scope.py lets a gate skip the "ritz0 unit tests" step when every
change is outside the step's inputs, and it finds those inputs by scanning
the step's sources for paths.  A scan can miss a read: a walk of projects/,
a path built from a variable, a helper elsewhere.  Measured 2026-11-18, one
lint here read every package's *.ritz while the scan's docstring said none
did.  This plugin checks the scan on every run instead of trusting it.

While a test is in setup, call or teardown, or a module is being collected,
an audit hook (sys.addaudithook) watches what the process opens, lists and
hands to a child: `open` for reading, `os.listdir`/`os.scandir`,
`subprocess.Popen` arguments, cwd and RITZ_PATH, `os.posix_spawn`/`os.exec`,
and ritz0_inproc's forked compiles (note_exec).  Each path in this repo but
outside projects/ritz is judged by the scope's own rule, ritz0_scope.why_safe:

  * a file read, or a path handed to a child: as if MODIFIED;
  * a directory listed: as if a file were ADDED to it (a package's A/D always
    runs; a listing of .claude/ would see a skippable add).

Markdown is judged by basename wherever it is, as the scope does: a read of
an unnamed .md, even under projects/ritz, is a hit.  A directory listed or
handed to a child is not judged for the .md files it may hold; the scope
treats every .md as an input once a source reads *.md by pattern.

If the scope would let a gate skip that change, the test fails, naming the
path: a gate could skip this test for a change that breaks it.  The fix is to
make the scan see the read (name the package by path in the test), never to
widen the allowlist.  CI on main runs the whole step, so a test that starts
reading an unnamed package fails on its first push, before any gate trusts
the scope for it.

What it cannot see: a child process (ritz1, clang, build.py) reading a path
it was not handed, e.g. a package found through RITZ_PATH=projects/.  The
scan's `import pkg` rule covers programs in the step's own sources.

The scope is measured once per session: by the xdist controller, passed to
each worker (so no worker pays ~1 s for it); or, without xdist, the first
time a test touches a path outside projects/ritz.  RITZ_READ_GUARD=0 turns
the guard off.

Loaded by ritz0/conftest.py (`pytest_plugins`); test_read_guard.py tests it.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

_TOOLS = str(Path(__file__).resolve().parent.parent / "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import ritz0_scope  # noqa: E402

_WORKER_KEY = "ritz0_read_scope"
_nothing = contextlib.nullcontext
# A name no real file has: what a change "in this directory" looks like.
_PROBE = "read_guard_probe"


def _scope_to_json(sc: ritz0_scope.Scope) -> dict:
    return {"named": sorted(sc.named), "md_wild": sc.md_wild,
            "md_names": sorted(sc.md_names), "named_tops": sorted(sc.named_tops)}


def _scope_from_json(d: dict) -> ritz0_scope.Scope:
    return ritz0_scope.Scope(named=frozenset(d["named"]), md_wild=bool(d["md_wild"]),
                             md_names=frozenset(d["md_names"]),
                             named_tops=frozenset(d["named_tops"]))


class Guard:
    """Judges paths against a scope.  `scope` is None until measured."""

    def __init__(self, repo: Path, scope: ritz0_scope.Scope | None = None):
        self.repo = os.path.realpath(repo)
        self._prefix = self.repo + os.sep
        self._ritz = os.path.join(self.repo, "projects", "ritz") + os.sep
        self.scope = scope
        self.broken: str | None = None  # why the scope could not be measured

    # -- what is in play -----------------------------------------------------

    def _rel(self, path, cwd: str | None = None) -> str | None:
        """`path` relative to the repo, if the scope could let a gate skip a
        change to it: in the repo, and outside projects/ritz (always an
        input) unless it is Markdown (judged by basename wherever it is)."""
        try:
            p = os.fsdecode(path)
        except TypeError:
            return None
        if not p:
            return None
        if not os.path.isabs(p):
            p = os.path.join(cwd or os.getcwd(), p)
        p = os.path.normpath(p)
        if not p.startswith(self._prefix):
            return None
        if (p + os.sep).startswith(self._ritz) and not p.endswith(".md"):
            return None
        p = os.path.realpath(p)  # projects/ritzlib -> projects/ritz/ritzlib
        if not p.startswith(self._prefix):
            return None
        if (p + os.sep).startswith(self._ritz) and not p.endswith(".md"):
            return None
        return p[len(self._prefix):]

    def _sc(self) -> ritz0_scope.Scope | None:
        """The scope, measured on first use.  None if it can't be (a copy of
        ritz0/ outside a git checkout, as test_stale_ritz1_binary's nested
        session is): there is no gate scope to check there, so no check."""
        if self.scope is None and self.broken is None:
            sg = sys.modules.get("spawn_guard")
            try:
                with sg.unwatched() if sg is not None else _nothing():
                    self.scope = ritz0_scope.scope(Path(self.repo))
            except (subprocess.CalledProcessError, OSError) as e:
                self.broken = f"{e}"
                print(f"read_guard: no scope to check in {self.repo} ({e}); "
                      f"guard off", file=sys.stderr)
        return self.scope

    def _judge(self, rel: str, *probes: tuple[str, str]) -> str | None:
        sc = self._sc()
        if sc is None:
            return None
        for status, path in probes:
            why = ritz0_scope.why_safe(status, path, sc)
            if why is not None:
                return why
        return None

    # -- the three kinds of access -------------------------------------------

    def read(self, path, cwd: str | None = None) -> tuple[str, str] | None:
        """(rel, why) if reading `path` is something a gate may skip."""
        rel = self._rel(path, cwd)
        if rel is None:
            return None
        if os.path.isdir(os.path.join(self.repo, rel)):
            return self.under(rel)
        why = self._judge(rel, ("M", rel))
        return (rel, why) if why else None

    def under(self, rel: str) -> tuple[str, str] | None:
        """(rel, why) if a child handed directory `rel` may read a file in
        it that a gate may skip."""
        why = self._judge(rel, ("M", f"{rel}/{_PROBE}"))
        return (rel + "/", why) if why else None

    def listing(self, path) -> tuple[str, str] | None:
        """(rel, why) if a listing of `path` would see a skippable add."""
        rel = self._rel(path)
        if rel is None:
            return None
        why = self._judge(rel, ("A", f"{rel}/{_PROBE}"))
        return (rel + "/", why) if why else None

    def exec(self, argv, cwd=None, env=None) -> list[tuple[str, str]]:
        """Every path handed to a child (argument, cwd, RITZ_PATH entry) that a
        gate may skip.  Arguments are split on whitespace, `=` and `:`, so
        `--x=path`, `-Ipath` and search paths count too."""
        cwd = os.fsdecode(cwd) if cwd is not None else None
        hits = []
        if isinstance(argv, (str, bytes, os.PathLike)):
            argv = [argv]
        for a in argv or ():
            try:
                a = os.fsdecode(a)
            except TypeError:
                continue
            for tok in a.replace("=", " ").replace(":", " ").split():
                if tok.startswith("-") and "/" in tok:
                    tok = tok[tok.index("/"):]
                if "/" in tok or tok.endswith(".ritz"):
                    hits.append(self.read(tok, cwd))
        if cwd is not None:
            rel = self._rel(cwd)
            if rel is not None:
                hits.append(self.under(rel))
        ritz_path = None
        if env is not None:
            try:
                ritz_path = env.get("RITZ_PATH") or env.get(b"RITZ_PATH")
            except (AttributeError, TypeError):
                ritz_path = None
        for entry in os.fsdecode(ritz_path).split(":") if ritz_path else ():
            rel = self._rel(entry, cwd)
            if rel is not None:
                hits.append(self.under(rel))
        return [h for h in hits if h]


# -- the session's guard and the audit hook ----------------------------------

_guard: Guard | None = None
# (rel, how, why) seen while a test or collector runs; None when not watching.
_window: list | None = None
_busy = False  # the guard's own measuring (git, file reads) is not the test's


def _note(hit, how: str) -> None:
    if hit and _window is not None:
        _window.append((hit[0], how, hit[1]))


def _audit(event: str, args) -> None:
    global _busy
    if _window is None or _busy or _guard is None:
        return
    if event not in _EVENTS:
        return
    _busy = True
    try:
        _EVENTS[event](args)
    except Exception as e:  # a guard bug must not look like a test's
        _window.append(("<read_guard>", event, f"guard error: {e!r}"))
    finally:
        _busy = False


def _on_open(args) -> None:
    path, mode, flags = args
    if not isinstance(path, (str, bytes, os.PathLike)):
        return  # an fd
    if isinstance(mode, str):
        if "r" not in mode and "+" not in mode:
            return
    elif flags is not None and flags & os.O_ACCMODE == os.O_WRONLY:
        return
    _note(_guard.read(path), "open")


def _on_list(args) -> None:
    path = args[0] if args else None
    if path is None or not isinstance(path, (str, bytes, os.PathLike)):
        return
    _note(_guard.listing(path), "list")


def _on_popen(args) -> None:
    exe, argv, cwd, env = args
    for hit in _guard.exec(([exe] if exe else []) + list(_as_list(argv)), cwd, env):
        _note(hit, "subprocess")


def _on_spawn(args) -> None:
    path, argv, env = args[0], args[1], args[2] if len(args) > 2 else None
    for hit in _guard.exec([path, *_as_list(argv)], None, env):
        _note(hit, "exec")


def _as_list(argv):
    if argv is None:
        return []
    if isinstance(argv, (str, bytes, os.PathLike)):
        return [argv]
    return list(argv)


_EVENTS = {
    "open": _on_open,
    "os.listdir": _on_list,
    "os.scandir": _on_list,
    "subprocess.Popen": _on_popen,
    "os.posix_spawn": _on_spawn,
    "os.exec": _on_spawn,
}


_hooked = False


def _hook() -> None:
    global _hooked
    if not _hooked:
        sys.addaudithook(_audit)  # cannot be removed; idle while _window is None
        _hooked = True


def note_exec(argv, cwd=None, env=None) -> None:
    """A compile that runs in a forked child (ritz0_inproc), which the audit
    hook in this process cannot see."""
    global _busy
    if _window is None or _busy or _guard is None:
        return
    _busy = True
    try:
        for hit in _guard.exec(list(argv), cwd, env):
            _note(hit, "ritz0 (in-process)")
    finally:
        _busy = False


def install(guard: Guard | None) -> None:
    """Use `guard` for the session (None turns the guard off)."""
    global _guard
    _guard = guard
    if guard is not None:
        _hook()


# -- pytest wiring -----------------------------------------------------------

def _enabled() -> bool:
    return os.environ.get("RITZ_READ_GUARD", "1") != "0"


def pytest_configure(config):
    if not _enabled():
        return
    repo = Path(__file__).resolve().parents[3]
    workerinput = getattr(config, "workerinput", None)
    if workerinput is not None:
        d = workerinput.get(_WORKER_KEY)
        install(Guard(repo, _scope_from_json(d) if d else None))
    elif config.getoption("dist", "no") != "no":
        # The xdist controller runs no tests: measure once, for every worker.
        try:
            config._ritz0_read_scope = _scope_to_json(ritz0_scope.scope(repo))
        except Exception as e:  # noqa: BLE001 -- workers measure for themselves
            print(f"read_guard: could not measure the scope here ({e}); "
                  f"each worker will", file=sys.stderr)
        return
    else:
        install(Guard(repo))


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node):
    d = getattr(node.config, "_ritz0_read_scope", None)
    if d is not None:
        node.workerinput[_WORKER_KEY] = d


def _report(seen) -> str:
    shown = "\n  ".join(f"{rel} ({how}): {why}" for rel, how, why in seen[:5])
    more = f"\n  ... and {len(seen) - 5} more" if len(seen) > 5 else ""
    return (f"read {len(seen)} path(s) tools/ritz0_scope.py lets a gate skip this "
            f"step for (AGAST #4032; ritz0/read_guard.py):\n  {shown}{more}\n"
            f"A change there could break this test while the gate skips it.  Name "
            f"the package (or file) by path in the test so the scope counts it.")


def _dedup(seen):
    out, keys = [], set()
    for s in seen:
        if s[0] not in keys:
            keys.add(s[0])
            out.append(s)
    return out


def _watch(item):
    global _window
    if _guard is None:
        return (yield)
    _window = []
    try:
        result = yield
    finally:
        seen, _window = _window, None
    if seen:
        pytest.fail(f"{item.nodeid} {_report(_dedup(seen))}", pytrace=False)
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


@pytest.hookimpl(wrapper=True)
def pytest_make_collect_report(collector):
    global _window
    if _guard is None or _window is not None:
        return (yield)
    _window = []
    try:
        rep = yield
    finally:
        seen, _window = _window, None
    if seen and rep.outcome != "failed":
        rep.outcome = "failed"
        rep.longrepr = f"collecting {collector.nodeid} {_report(_dedup(seen))}"
    return rep
