"""ritzlib.net takes views, spans and references, not raw pointers (AGAST #3835).

#1483 gave ritzlib.net a StrView / Span / Result API (socket_bind,
socket_connect, socket_send_all, socket_send_str, socket_recv_into) and
kept the older raw forms for their callers. #3835 ports those callers and,
per Aaron's ruling that raw `*u8` entry points are not kept as wrappers,
deletes the raw forms:

1. socket_send / socket_recv (a `*u8` buffer and a length), socket_bind_any,
   and socket_send_string (a `*String` and a bare i64) are gone.
2. socket_connect_timeout takes `@&Socket` and a StrView address, and
   returns Result<(), i32> with the errno, not -1/-2/-3 categories.
3. No `pub fn` in net.ritz takes a `*u8` parameter, except the sys_*
   syscall shims, whose pointer arguments are the kernel ABI.

#3880 finishes the job for the Socket handle itself:

4. No fn in net.ritz takes a raw `*Socket`.  close, listen, accept,
   accept_nonblock, set_opt_int, set_reuseaddr/reuseport/nodelay and
   set_io_timeout take `@&Socket` and return Result<(), i32> or
   Result<Socket, i32> (SIGNATURES), not 0-or-negative-errno or a Socket
   whose fd < 0 means "failed".

These are text checks on the source, so they cost no compile. What the fns
do is covered by ritzlib/tests/test_net_api.ritz.
"""

import re
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = RITZ_ROOT.parent.parent
NET = RITZ_ROOT / "ritzlib" / "net.ritz"

DELETED = [
    "socket_send",
    "socket_recv",
    "socket_bind_any",
    "socket_send_string",
]

# Build output, not source.
SKIP_PARTS = {"build", ".git", "node_modules", "__pycache__", "out"}

PUB_FN = re.compile(r"^\s*pub fn (\w+)\((.*)\)\s*(?:->.*)?$", re.MULTILINE)


def _pub_fns():
    """(name, params) for every `pub fn` in net.ritz, impl methods included."""
    return [(m.group(1), m.group(2)) for m in PUB_FN.finditer(NET.read_text())]


def test_pub_fn_scan_sees_the_api():
    """The guard below is only as good as its scan: it must see real fns."""
    names = {name for name, _ in _pub_fns()}
    assert {"socket_bind", "socket_connect_timeout", "sys_bind", "send"} <= names


def test_no_raw_u8_parameter_outside_syscall_shims():
    offenders = [
        f"{name}({params})"
        for name, params in _pub_fns()
        if not name.startswith("sys_") and re.search(r":\s*\*u8\b", params)
    ]
    assert offenders == []


ANY_FN = re.compile(r"^\s*(?:pub\s+)?fn (\w+)\((.*)\)\s*(?:->.*)?$", re.MULTILINE)


def test_no_raw_socket_pointer_parameter_outside_syscall_shims():
    """#3880: no fn in net.ritz, impl methods and private fns included, takes
    a raw `*Socket`; a Socket is borrowed as `@Socket` or `@&Socket`."""
    fns = [(m.group(1), m.group(2)) for m in ANY_FN.finditer(NET.read_text())]
    assert {"socket_close", "close", "accept"} <= {name for name, _ in fns}
    offenders = [
        f"{name}({params})"
        for name, params in fns
        if not name.startswith("sys_") and re.search(r":\s*\*Socket\b", params)
    ]
    assert offenders == []


# Every Socket entry point that can fail: a borrowed Socket in, a Result out
# (#3835 connect_timeout, #3880 the rest).  No 0-or-negative-errno i32 and no
# Socket with fd < 0 standing for an error.
SIGNATURES = [
    "pub fn socket_connect_timeout(sock: @&Socket, addr: StrView, port: i32, "
    "timeout_ms: i32) -> Result<(), i32>",
    "pub fn socket_close(sock: @&Socket) -> Result<(), i32>",
    "pub fn socket_set_opt_int(sock: @&Socket, level: i32, optname: i32, "
    "value: i32) -> Result<(), i32>",
    "pub fn socket_set_reuseaddr(sock: @&Socket) -> Result<(), i32>",
    "pub fn socket_set_reuseport(sock: @&Socket) -> Result<(), i32>",
    "pub fn socket_set_nodelay(sock: @&Socket) -> Result<(), i32>",
    "pub fn socket_set_io_timeout(sock: @&Socket, timeout_ms: i32) -> Result<(), i32>",
    "pub fn socket_listen(sock: @&Socket, backlog: i32) -> Result<(), i32>",
    "pub fn socket_accept(sock: @&Socket) -> Result<Socket, i32>",
    "pub fn socket_accept_nonblock(sock: @&Socket) -> Result<Socket, i32>",
]


@pytest.mark.parametrize("sig", SIGNATURES, ids=lambda s: s.split("(")[0][7:])
def test_signature(sig):
    head = sig.split("(")[0]
    m = re.search(rf"^{re.escape(head)}\(.*$", NET.read_text(), re.MULTILINE)
    assert m, f"net.ritz has no `{head}(`"
    assert m.group(0).rstrip() == sig


@pytest.mark.parametrize("name", DELETED)
def test_raw_form_is_deleted(name):
    assert not re.search(rf"^\s*(pub\s+)?fn {name}\(", NET.read_text(), re.MULTILINE)


IMPORTS_NET = re.compile(r"^\s*import\s+ritzlib\.net\b", re.MULTILINE)


def _live_files():
    """net.ritz, the ritzlib reference, and every .ritz that imports ritzlib.net.

    Symlinks are skipped (a link would repeat its target).
    """
    yield NET
    yield RITZ_ROOT / "docs" / "STDLIB_REFERENCE.md"
    for path in WORKSPACE.joinpath("projects").rglob("*.ritz"):
        rel = path.relative_to(WORKSPACE)
        if SKIP_PARTS.intersection(rel.parts) or path.is_symlink():
            continue
        if path == NET or not path.is_file():
            continue
        if IMPORTS_NET.search(path.read_text(errors="replace")):
            yield path


def test_nothing_uses_a_deleted_raw_form():
    """No live source calls or imports, and the reference lists, a deleted fn."""
    alts = "|".join(DELETED)
    pat = re.compile(rf"(?<![\w.])({alts})\s*[(,}}]|`({alts})`")
    offenders = []
    for path in _live_files():
        for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if pat.search(line):
                offenders.append(f"{path.relative_to(WORKSPACE)}:{i}: {line.strip()}")
    assert offenders == []
