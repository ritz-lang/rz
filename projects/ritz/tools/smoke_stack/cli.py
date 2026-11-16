"""The command line: XFAILS, the suite table and main()."""

from __future__ import annotations

import argparse
import atexit
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path

from .harness import FAIL, XPASS, Procs, Reporter
from .help import suite_help
from .hollow import suite_hollow
from .mausoleum import suite_mausoleum
from .rzsh import suite_rzsh
from .stack import suite_stack
from .tome import suite_tome
from .valet import suite_valet

# Check id -> the ticket that owns its failure. Delete an entry in the same
# change that makes its check pass; the run fails (XPASS) until you do.
XFAILS: dict[str, str] = {
    # help: exit 0 on --help, usage on stdout, nothing written into cwd
    "help:ritz-lsp/ritz-lsp": "#3159 ignores --help: starts the server, logs to stderr only, nothing on stdout",
    "help:lexis/lexis": "#3700 SIGSEGV at startup: main's stack frame is ~205 GB (by-value Stylesheet/StyleEngine locals)",
    # hollow entry points (#2460 made the rest honest; sage still runs nothing)
    "hollow.sage_runs_js": "#2787 sage has no interpreter: `sage t.js` exits 1 'not implemented'",
}

# Suite name -> fn(reporter, procs, tmp), in run order.
RUNNERS = {
    "help": lambda r, procs, tmp: suite_help(r, tmp),
    "valet": suite_valet,
    "tome": suite_tome,
    "mausoleum": suite_mausoleum,
    "stack": suite_stack,
    "hollow": lambda r, procs, tmp: suite_hollow(r, tmp),
    "rzsh": lambda r, procs, tmp: suite_rzsh(r, tmp),
}
SUITES = list(RUNNERS)


def _on_signal(signum, _frame):
    raise SystemExit(f"smoke_stack: killed by signal {signum}")


def _parse(argv: list[str] | None) -> argparse.Namespace:
    from . import __doc__ as doc  # the package docstring is the manual
    ap = argparse.ArgumentParser(description=doc.split("\n\n")[0])
    ap.add_argument("suites", nargs="*", metavar="SUITE",
                    help=f"subset of {', '.join(SUITES)} (default: all)")
    ap.add_argument("--list", action="store_true", help="print the xfail table and exit")
    ap.add_argument("--keep", action="store_true", help="keep the temp dir (logs) afterwards")
    return ap.parse_args(argv)


def _run_suites(r: Reporter, selected: list[str], keep: bool) -> tuple[list[tuple[str, float]], float]:
    """Every selected suite, with every process it started killed after it.
    Returns per-suite seconds and the start time."""
    tmp = Path(tempfile.mkdtemp(prefix="smoke_stack_"))
    procs = Procs(tmp)
    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(s, _on_signal)
    atexit.register(procs.kill_all)

    t0 = time.monotonic()
    timings = []
    try:
        for suite in selected:
            ts = time.monotonic()
            print(f"--- {suite}", flush=True)
            try:
                RUNNERS[suite](r, procs, tmp)
            except Exception as e:  # noqa: BLE001 -- one crashed suite must not hide the rest
                r.broken(f"{suite}.harness", f"suite crashed: {type(e).__name__}: {e}")
            procs.kill_all()  # a suite that bailed early leaves nothing behind
            timings.append((suite, time.monotonic() - ts))
    finally:
        procs.kill_all()
        leaked = procs.survivors()
        if leaked:
            r.broken("harness.cleanup", f"process groups still alive after SIGKILL: {leaked}")
        if keep:
            print(f"logs kept in {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    return timings, t0


def _report(r: Reporter, timings: list[tuple[str, float]], t0: float) -> int:
    print("\n=== smoke-stack: per-suite seconds ===")
    for suite, secs in timings:
        print(f"  {suite:10} {secs:6.1f}s")
    print(f"  {'total':10} {time.monotonic() - t0:6.1f}s")
    print(f"=== {r.summary()}")
    failed = [x for x in r.results if x.outcome in (FAIL, XPASS)]
    for x in failed:
        print(f"  {x.outcome}: {x.check}  {x.detail if x.outcome == FAIL else XFAILS.get(x.check, '')}")
    code = r.exit_code()
    print("✓ smoke-stack passed" if code == 0 else "💥 smoke-stack FAILED")
    return code


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    if args.list:
        for k, v in XFAILS.items():
            print(f"{k:40} {v}")
        return 0
    unknown = [s for s in args.suites if s not in SUITES]
    if unknown:  # not ap.error(): that exits 2, and this script exits 0 or 1
        print(f"smoke_stack: unknown suite(s) {unknown}; choose from {SUITES}", file=sys.stderr)
        return 1
    selected = args.suites or SUITES
    r = Reporter(XFAILS)
    timings, t0 = _run_suites(r, selected, args.keep)
    for k in r.unused_xfails(set(selected)):
        r.broken(f"harness.xfail:{k}", "XFAILS entry matches no check that ran: rename or delete it")
    return _report(r, timings, t0)
