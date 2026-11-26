"""AGAST #4636: calls of ritzlib's exempt raw APIs from outside ritzlib, pinned down-only.

An exemption says a function is a raw boundary (the kernel ABI, the
allocator, C strings); it doesn't make the raw layer the right thing for
the rest of the tree to call.  This counts how far it escapes:
`standard_report.py --callers` finds each call of an exempt public ritzlib
fn in projects/**, outside ritzlib, in a file that imports its module.

Each project's count is a ceiling: porting callers to the idiomatic API
lowers it and passes (lower the pin when you do).  A new raw call fails.

A commit that newly exempts a ritzlib fn makes its existing callers count
for the first time: that commit raises the pins it moves, naming the API
in its message.  That is the only reason to raise one.

The second pin (#4673) is the count of `c"..."` literals per project
(`standard_report.py --c-literals`).  STANDARD.md S-TEXT-1: a NUL-terminated
literal belongs only at a C-interop boundary, so a project's count only goes
down.  Porting a call site to a StrView API lowers it (lower the pin); a new
`c""` anywhere in the project fails, tests included.  There is no reason to
raise it: a boundary that needs a new NUL-terminated string belongs in a
ritzlib wrapper that takes a StrView.

This lives in tools/, not tools/test_standard_pins/: it names every package,
and tools/ritz0_scope.py reads the pins directory as a ritz0-step source, so
there it would make every package an input of the ritz0 step (#4032).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from standard_report import (
    c_literal_breaches,
    c_literals_by_project,
    callers_by_project,
    count_callers,
)

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent
PROJECTS = RITZ_ROOT.parent

PINS = {
    "angelo": 4,
    "cryptosec": 10,
    "goliath": 0,
    "harland": 11,
    "http": 2,
    "indium": 120,
    "larb": 0,
    "lexis": 0,
    # exec (2): test_integration / test_multi_collection fork+exec the built
    # server binary; ritzlib.process.exec is that process boundary.
    "mausoleum": 2,
    "nexus": 0,
    "prism": 3,
    # ritz/examples keeps 3, typed wrappers at a syscall boundary: time.sleep
    # (nanosleep; exempt only for its free-fn name) in 10_sleep and 40_watch,
    # process.exec (execve; owns the argv block) in 35_nohup.
    "ritz": 1357,
    "ritz-lsp": 0,
    "ritzunit": 0,
    "rzrz": 3,
    # rzsh: src/rawio.ritz's sys_write x2, sys_read, sys_getpid: src/ also
    # builds the freestanding Harland bin, where ritzlib.fd / ritzlib.process
    # don't build, so stdio and the pid stay raw in that one shim (RAW_OK).
    # strview_from_cstr x1, src/os.ritz os_environ: the kernel's envp is a C
    # array of NUL-terminated strings (ritzlib.os.env's env_iter would do it,
    # but importing it pulls in ritzlib.io, whose println collides with
    # common's).
    "rzsh": 5,
    "sage": 0,
    "spire": 0,
    "squeeze": 2,
    "tempest": 0,
    "tome": 0,
    # valet: ritzlib.mapping's munmap x2, lib/valet.ritz: the request/response
    # heap buffers (BigBuf, up to 16 MB, handed to io_uring) and the TLS
    # per-task state reached through task.user_data are mmap_anon mappings;
    # munmap(span) is their release, the ritzlib.mapping pair of mmap_anon.
    "valet": 2,
    # zeus: ritzlib.mapping's mmap_shared x4 + munmap x4: the memfd rings
    # are mmap_shared mappings (lib/shm.ritz region x2, lib/zeus_client.ritz
    # attached worker, test_zeus_client's received fd) and lib/arena.ritz's
    # private test arena an mmap_anon one; munmap(span) is their release.
    # mmap_shared is exempt from #4692 on (mapping.ritz is the mmap owner, as
    # for munmap), so its calls count from that commit. ritzlib.time's sleep
    # x1, lib/worker.ritz: the 50us back-off while the response ring is full;
    # sleep(Duration) is time's API, exempt only for being a free fn.
    "zeus": 9,
}


@pytest.fixture(scope="module")
def by_project():
    return callers_by_project(
        count_callers(RITZ_ROOT / "ritzlib", [PROJECTS]), PROJECTS
    )


def test_raw_api_callers_only_go_down(by_project):
    over = {p: (n, PINS.get(p, 0)) for p, n in by_project.items() if n > PINS.get(p, 0)}
    assert over == {}, f"project: (calls, pin) over the pin: {over}"


# AGAST #4691: the syscalls ritzlib now wraps (ritzlib.process ids, SigSet,
# signalfd; ritzlib.fd poll and Fd.sendfile; ritzlib.fs unlink / rename) have
# no raw callers left in hosted code.  The compilers (ritz0, ritz1) and the
# freestanding indium / harland are out of scope, and so is rzsh's
# src/rawio.ritz: rzsh's src/ also builds a freestanding Harland bin, where
# ritzlib.fd and ritzlib.process don't build, so its pid and stdio stay raw
# in that one shim.
WRAPPED_SYSCALLS = {
    "sys_getpid", "sys_getppid", "sys_getuid", "sys_poll", "sys_rt_sigprocmask",
    "sys_signalfd4", "sys_sendfile", "sys_unlink", "sys_rename",
}
RAW_OK = ("ritz/ritz0/", "ritz/ritz1/", "indium/", "harland/", "rzsh/src/rawio.ritz")


def test_wrapped_syscalls_have_no_hosted_callers():
    sites = count_callers(RITZ_ROOT / "ritzlib", [PROJECTS])
    raw = [f"{Path(s.path).relative_to(PROJECTS)}:{s.line} {s.api}" for s in sites
           if s.api in WRAPPED_SYSCALLS
           and not str(Path(s.path).relative_to(PROJECTS)).startswith(RAW_OK)]
    assert raw == [], f"raw calls with a typed ritzlib wrapper: {raw}"


# `c"..."` literals per project, re-measured by #4686 on af511e6fba25 (rzsh by
# #4691, nexus/ritz-lsp/ritzunit/mausoleum/goliath by #4688).  Down only.
C_LITERAL_PINS = {
    "cryptosec": 295,
    "goliath": 0,
    "harland": 34,
    "http": 77,
    "indium": 157,
    "iris": 1,
    "larb": 0,
    "mausoleum": 33,
    "nexus": 0,
    "prism": 1,
    "ritz": 3876,
    "ritz-lsp": 0,
    "ritzunit": 63,
    "rzrz": 34,
    "rzsh": 0,
    "sage": 0,
    "spire": 0,
    "tome": 0,
    "valet": 0,
    "zeus": 1,
}


def test_c_literals_only_go_down():
    over = c_literal_breaches(c_literals_by_project([PROJECTS]), C_LITERAL_PINS)
    assert over == [], f"new c\"\" literals (S-TEXT-1: C interop only): {over}"
