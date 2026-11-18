"""smoke_stack -- start every server and CLI, talk to it for real (AGAST #2456).

Every package's [[test]] suite passed on 2026-11-08 while tome's default
io_uring server never replied, mausoleum lost its documents on restart,
nexus served a page on only every other request and several CLIs exited 0
having done nothing. No gate started a server and made a request. This one
does, after `./rz build --all`, using the debug binaries that step built:

  help      every [[bin]] that targets Linux runs `--help`: exit 0, usage
            on stdout, nothing written into its cwd
  valet     GET /, a static file, a directory index, traversal -> 403, HTTPS
  tome      PING, SET/GET, INCR, a pipelined SET+GET and tome-cli, in the
            default io_uring mode AND in blocking mode (-b)
  mausoleum wiki-seed writes, restart on the same --data-dir, read back;
            wiki-seed exit codes; the encrypted protocol; the shell
  stack     valet -> zeus (2 workers) -> nexus + mausoleum: create a page,
            GET it 4 times, edit it, restart the whole stack, GET it again;
            100 keep-alive requests (the last says Connection: close);
            whole log lines; no mausoleum with 2 workers -> 503, not 404;
            MAUSOLEUM_PLAINTEXT=1 against a --no-encryption mausoleum, the
            handshake hint without it, a bad value -> refuse;
            SIGTERM/SIGINT/SIGKILL to zeus alone stops its workers in 2 s;
            kill -9 of one worker: zeus respawns it in 2 s, and a SIGHUP
            hot reload reaps it; zeus logs each line in one write(2)
  hollow    sage, goliath, rzrz and ritz-lsp must not report success for
            work they did not do
  rzsh      the Linux shell: echo, cd, $X, $?, >, |, external commands, EOF

What fails today is a STRICT xfail citing the child ticket that owns the
bug (XFAILS below). A check that starts passing fails the run (XPASS) until
its entry is deleted, so fixing a bug forces its xfail out, the same
strict-xpass rule as the known-failures/ list. A broken
precondition (a missing binary, a server that never listens) is a plain
FAIL even under an xfail: the xfail excuses the named bug, not a different
breakage that happens to make the same check red.

Every process is started in its own session and killed by process group
(zeus's nexus workers included) on exit, on failure and on SIGTERM/SIGINT.
The run checks afterwards that nothing it started survived. Ports come from
the kernel (bind to 0), mausoleum's too: nexus dials the port zeus passes
on as MAUSOLEUM_PORT (#3065), so a stack never shares mausoleum's default.

Run from anywhere, after `./rz build --all`:
    python3 projects/ritz/tools/smoke_stack            # everything
    python3 projects/ritz/tools/smoke_stack tome valet # some suites
    python3 projects/ritz/tools/smoke_stack --list     # check ids

CI runs it in main.yml's build-all job (so `make ci-local` and the room gate
run it too; ci_local parses the workflow). Exits 0 or 1 only: ci_local reads
3 as a SETUP ERROR, and a red run here is a regression.

Layout (AGAST #3455): one module per suite (help, valet, tome, mausoleum,
stack + stack_zeus, hollow, rzsh), the shared harness in harness, main() in
cli. A suite's shared state (processes, ports, paths) is a ctx dataclass and
every check a module-level function taking it: no closures over captured
locals. test_smoke_stack_shape.py holds the package to that.
"""

from __future__ import annotations

from .cli import RUNNERS, SUITES, XFAILS, main
from .harness import (
    FAIL,
    IO_TIMEOUT,
    PASS,
    SKIP,
    XFAIL,
    XPASS,
    Broken,
    CheckFailed,
    Procs,
    Reporter,
    Result,
    _suite_of,
    free_port,
    http_req,
    run_cmd,
    short,
    unix_socket_path,
    wait_listening,
    wait_path,
)
from .help import Bin, linux_bins, targets_linux
from .tome import resp_cmd, resp_exchange

__all__ = [
    "FAIL",
    "IO_TIMEOUT",
    "PASS",
    "RUNNERS",
    "SKIP",
    "SUITES",
    "XFAIL",
    "XFAILS",
    "XPASS",
    "Bin",
    "Broken",
    "CheckFailed",
    "Procs",
    "Reporter",
    "Result",
    "_suite_of",
    "free_port",
    "http_req",
    "linux_bins",
    "main",
    "resp_cmd",
    "resp_exchange",
    "run_cmd",
    "short",
    "targets_linux",
    "unix_socket_path",
    "wait_listening",
    "wait_path",
]
