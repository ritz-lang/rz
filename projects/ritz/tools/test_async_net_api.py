"""async_net rides on net.Socket; it keeps no i32-fd socket API (AGAST #4645).

net.ritz already had the idiomatic surface (#1483, #3835, #3880, #4298):
`socket_tcp() -> Result<Socket, Errno>`, `Socket.bind/listen/connect/
set_reuseaddr/... -> Result<(), Errno>`, `Socket.accept -> Result<Socket,
Errno>`.  async_net duplicated it on bare i32 fds with 0-or-negative-errno
returns (tcp_socket, tcp_bind, tcp_listen, ...).  #4645 ports every caller
onto Socket and deletes the i32 forms, with no wrappers:

1. async_net exports no `pub fn` returning a bare i32 (or i64) status or
   fd, and none of the deleted names is defined or called anywhere live.
2. runtime_accept hands back a Socket, not an i32 fd.
3. net.Socket gains what the callers needed: shutdown (Result), raw (the
   descriptor, for the io_uring runtime), local_port (was
   tcp_getsockname), and socket_from_raw (adopts a descriptor the io_uring
   runtime accepted).
4. net's raw syscall shims that only net uses are module-private.
5. async/blocking_fs's path calls take a StrView and return Result.

Text checks on the source, so they cost no compile.  Behaviour is covered by
ritzlib/tests/test_net_api.ritz and examples 54/59/60.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = RITZ_ROOT.parent.parent
ASYNC_NET = RITZ_ROOT / "ritzlib" / "async_net.ritz"
NET = RITZ_ROOT / "ritzlib" / "net.ritz"
BLOCKING_FS = RITZ_ROOT / "ritzlib" / "async" / "blocking_fs.ritz"

DELETED = [
    "tcp_socket",
    "tcp_socket_nonblock",
    "tcp_bind",
    "tcp_listen",
    "tcp_accept",
    "tcp_connect",
    "tcp_shutdown",
    "tcp_getsockname",
    "sys_send",
    "sys_recv",
]

# Free fns that shadowed Socket's methods; the methods stay.
DELETED_FREE = ["set_reuseaddr", "set_reuseport", "set_nodelay"]

# Only net.ritz itself calls these, so they are not API.
NET_PRIVATE = ["sys_socket", "sys_listen", "sys_shutdown", "sys_epoll_create1"]

SKIP_PARTS = {"build", ".git", "node_modules", "__pycache__", "out"}

TOP_FN = re.compile(r"^(pub\s+)?(?:async\s+)?fn (\w+)\((.*)\)\s*(?:->\s*(.*))?$", re.MULTILINE)


def _top_fns(path):
    """(is_pub, name, params, return type) for each module-level fn."""
    return [(bool(m.group(1)), m.group(2), m.group(3), (m.group(4) or "").strip())
            for m in TOP_FN.finditer(path.read_text())]


def test_scan_sees_async_net_fns():
    """The guards below are only as good as this scan."""
    names = {name for _, name, _, _ in _top_fns(ASYNC_NET)}
    assert {"runtime_accept", "runtime_send", "runtime_recv"} <= names


def test_async_net_exports_no_integer_status_or_fd():
    offenders = [f"{name} -> {ret}" for is_pub, name, _, ret in _top_fns(ASYNC_NET)
                 if is_pub and ret in ("i32", "i64")]
    assert offenders == []


@pytest.mark.parametrize("name", DELETED + DELETED_FREE)
def test_i32_form_is_deleted(name):
    assert not re.search(rf"^\s*(pub\s+)?fn {name}\(", ASYNC_NET.read_text(), re.MULTILINE)


def test_runtime_accept_returns_a_socket():
    sig = [f"{name}({params}) -> {ret}" for _, name, params, ret in _top_fns(ASYNC_NET)
           if name == "runtime_accept"]
    assert sig == ["runtime_accept(rt: @&Runtime, server: @Socket) -> Result<Socket, Errno>"]


NET_SIGNATURES = [
    "pub fn shutdown(self: @&Socket, how: i32) -> Result<(), Errno>",
    "pub fn raw(self: @Socket) -> i32",
    "pub fn local_port(self: @Socket) -> Result<i32, Errno>",
    "pub fn socket_from_raw(fd: i32) -> Socket",
]


@pytest.mark.parametrize("sig", NET_SIGNATURES, ids=lambda s: s.split("(")[0][7:])
def test_net_signature(sig):
    head = sig.split("(")[0]
    m = re.search(rf"^\s*{re.escape(head)}\(.*$", NET.read_text(), re.MULTILINE)
    assert m, f"net.ritz has no `{head}(`"
    assert m.group(0).strip() == sig


@pytest.mark.parametrize("name", NET_PRIVATE)
def test_net_only_shim_is_private(name):
    fns = {n: is_pub for is_pub, n, _, _ in _top_fns(NET)}
    assert name in fns, f"net.ritz has no fn {name}"
    assert not fns[name], f"{name} is only used by net.ritz; it should not be pub"


BLOCKING_FS_SIGNATURES = [
    "pub async fn async_open(path: StrView, flags: i32) -> Result<i32, Errno>",
    "pub async fn async_open3(path: StrView, flags: i32, mode: i32) -> Result<i32, Errno>",
    "pub async fn async_read_file(path: StrView, buf: Span<u8>) -> Result<i64, Errno>",
    "pub async fn async_write_file(path: StrView, buf: Span<u8>) -> Result<i64, Errno>",
]


@pytest.mark.parametrize("sig", BLOCKING_FS_SIGNATURES, ids=lambda s: s.split("(")[0][13:])
def test_blocking_fs_signature(sig):
    head = sig.split("(")[0]
    m = re.search(rf"^\s*{re.escape(head)}\(.*$", BLOCKING_FS.read_text(), re.MULTILINE)
    assert m, f"blocking_fs.ritz has no `{head}(`"
    assert m.group(0).strip() == sig


def _live_ritz():
    for path in WORKSPACE.joinpath("projects").rglob("*.ritz"):
        rel = path.relative_to(WORKSPACE)
        if SKIP_PARTS.intersection(rel.parts) or path.is_symlink() or not path.is_file():
            continue
        yield path


def test_nothing_calls_a_deleted_form():
    """No live source calls a deleted i32 fn (Socket's methods are `.name(`)."""
    names = "|".join(DELETED + DELETED_FREE)
    call = re.compile(rf"(?<![\w.])({names})\s*\(")
    offenders = []
    for path in _live_ritz():
        for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            code = line.split("#", 1)[0]
            if call.search(code) and not re.match(r"\s*(pub\s+)?fn ", code):
                offenders.append(f"{path.relative_to(WORKSPACE)}:{i}: {line.strip()}")
    assert offenders == []


def test_nothing_outside_net_calls_a_private_shim():
    pat = re.compile(rf"(?<![\w.])({'|'.join(NET_PRIVATE)})\s*\(")
    offenders = []
    for path in _live_ritz():
        if path == NET:
            continue
        for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if pat.search(line.split("#", 1)[0]):
                offenders.append(f"{path.relative_to(WORKSPACE)}:{i}: {line.strip()}")
    assert offenders == []
