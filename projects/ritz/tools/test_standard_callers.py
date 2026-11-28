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
    count_c_literals,
    count_callers,
)

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent
PROJECTS = RITZ_ROOT.parent

PINS = {
    "angelo": 0,
    # cryptosec: ritzlib.mapping's munmap x1, lib/ca_store.ritz
    # ca_store_destroy: the certificate arena is an mmap_anon mapping that
    # hands out *X509Certificate slots by bump allocation; munmap(span) is
    # its release, the ritzlib.mapping pair of mmap_anon.
    "cryptosec": 1,
    "goliath": 0,
    "harland": 11,
    "http": 0,
    "indium": 120,
    "larb": 0,
    "lexis": 0,
    # exec (2): test_integration / test_multi_collection fork+exec the built
    # server binary; ritzlib.process.exec is that process boundary.
    "mausoleum": 2,
    "nexus": 0,
    "prism": 0,
    # ritz/examples keeps 3, typed wrappers at a syscall boundary: time.sleep
    # (nanosleep; exempt only for its free-fn name) in 10_sleep and 40_watch,
    # process.exec (execve; owns the argv block) in 35_nohup.
    "ritz": 806,
    "ritz-lsp": 0,
    "ritzunit": 0,
    "rzrz": 0,
    # rzsh: src/rawio.ritz's sys_getpid x1: src/ also builds the
    # freestanding Harland bin, where ritzlib.process doesn't build (its
    # fork/exec/wait/signalfd syscalls are Linux-only), so the pid stays raw
    # in that one shim (RAW_OK). Its stdio is ritzlib.fd's (AGAST #4928).
    "rzsh": 1,
    "sage": 0,
    "spire": 0,
    "squeeze": 0,
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


# AGAST #4928: ritzlib's own tests count (standard_report skips the library's
# sources, not its tests/), per file. A test of a Ritz-level API reaches it
# through that API (testlib.capture for what a printer writes, sandbox_path +
# fs.* for files, "..." literals for views), so a file not named here is 0.
# The files named here test the raw boundary itself: the calls are their
# subject.
RITZLIB_TESTS = RITZ_ROOT / "ritzlib" / "tests"
RITZLIB_TEST_PINS = {
    # ritzlib.memory: malloc/free/realloc/calloc, memcpy/memmove/memset/
    # memcmp, the allocator's own API, each tested directly.
    "test_memory.ritz": 116,
    # ritzlib.allocator: allocator_of / heap_alloc / heap_free and the raw
    # blocks they hand out.
    "test_allocator.ritz": 42,
    # ritzlib.cstr: strlen, streq, strview_from_cstr, cstr_of ... on
    # NUL-terminated input, the C-string boundary.
    "test_cstr.ritz": 19,
    # strview_join2 / strview_join3 (+ the free each result needs): the
    # pointer-returning join is the subject.
    "test_strview_join.ritz": 16,
    # String.into_view hands its buffer to the caller, who frees it with
    # free(result.ptr) (the same exempt hand-off as strview_join2/3, AGAST
    # #4915): each test frees the view it took.
    "test_string_into_view.ritz": 6,
    # ritzlib.mapping's mmap_shared / munmap: the mmap owner's own API.
    "test_mapping.ritz": 7,
    # spawn_env / spawn_env_merged (exempt: they own the argv/envp blocks).
    "test_process_env.ritz": 3,
    "test_process_pipes.ritz": 1,
    # process.exec (exempt for the same reason) x2: the exec tests; and
    # process.spawn_fn x2 (exempt: its child exits with the body's value,
    # AGAST #4928): the spawn_fn tests.
    "test_process_fork.ritz": 4,
    # strview_from_cstr / strview_from_ptr, each tested once.
    "test_strview.ritz": 2,
    # time.sleep (exempt only as a free fn): its own tests.
    "test_time.ritz": 2,
    # AGAST #4929 ports these (hand-rolled fork/pipe capture around async
    # bodies) and lowers them to 0; test_async_server is at what #4929's
    # rewrite left.
    "test_async_server.ritz": 29,
    "test_async_spawn.ritz": 39,
    "test_block_on_future.ritz": 9,
}


def _is_ritzlib_test(site) -> bool:
    return Path(site.path).resolve().is_relative_to(RITZLIB_TESTS.resolve())


@pytest.fixture(scope="module")
def sites():
    return count_callers(RITZ_ROOT / "ritzlib", [PROJECTS])


@pytest.fixture(scope="module")
def by_project(sites):
    return callers_by_project([s for s in sites if not _is_ritzlib_test(s)], PROJECTS)


def test_raw_api_callers_only_go_down(by_project):
    over = {p: (n, PINS.get(p, 0)) for p, n in by_project.items() if n > PINS.get(p, 0)}
    assert over == {}, f"project: (calls, pin) over the pin: {over}"


def test_ritzlib_tests_raw_callers_only_go_down(sites):
    by_file: dict[str, list[str]] = {}
    for s in sites:
        if _is_ritzlib_test(s):
            by_file.setdefault(Path(s.path).name, []).append(f"{s.line} {s.api}")
    over = {f: (len(v), RITZLIB_TEST_PINS.get(f, 0), v[:8]) for f, v in by_file.items()
            if len(v) > RITZLIB_TEST_PINS.get(f, 0)}
    assert over == {}, f"ritzlib/tests file: (calls, pin, first sites) over the pin: {over}"


def test_ritzlib_tests_are_counted(sites):
    """The pin above sees ritzlib/tests at all: the boundary tests have calls."""
    assert any(_is_ritzlib_test(s) and Path(s.path).name == "test_memory.ritz" for s in sites)


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
    "http": 74,
    "indium": 105,
    "iris": 1,
    "larb": 0,
    "mausoleum": 33,
    "nexus": 0,
    "prism": 1,
    "ritz": 384,
    "ritz-lsp": 0,
    "ritzunit": 63,
    "rzrz": 0,
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


# AGAST #4928: ritzlib/tests' `c"..."` literals per file, down only (they are
# also in the `ritz` total above). A "..." literal is a StrView; a c"" stays
# only where NUL termination is the subject: the C-string tests, and the
# compilers' lexer tests of the c"" literal itself. Any other file is 0.
RITZLIB_TEST_C_LITERAL_PINS = {
    # ritzlib.cstr's strlen / streq / strview_from_cstr need NUL-terminated input.
    "test_cstr.ritz": 22,
    # strview_from_cstr's own test needs one NUL-terminated input.
    "test_strview.ritz": 1,
    # The `*u8` Display / Debug impls: a NUL-terminated pointer is the input.
    "test_fmt_impls.ritz": 1,
    # AGAST #4929 ports these and lowers them to 0.
    "test_async_server.ritz": 3,
    "test_async_spawn.ritz": 4,
}


def test_ritzlib_tests_c_literals_only_go_down():
    over = {}
    for f in sorted(RITZLIB_TESTS.glob("*.ritz")):
        n = sum(count_c_literals(ln) for ln in f.read_text().split("\n"))
        if n > RITZLIB_TEST_C_LITERAL_PINS.get(f.name, 0):
            over[f.name] = (n, RITZLIB_TEST_C_LITERAL_PINS.get(f.name, 0))
    assert over == {}, f'ritzlib/tests file: (c"" literals, pin) over the pin: {over}'
