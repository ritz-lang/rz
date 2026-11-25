"""An array length naming an imported or later-declared const (AGAST #2167).

ritz1 folds `[N]T`'s length at parse time against the consts parsed so far
(#2153).  Imports are merged into the module only after parsing, so a length
naming an imported const (`[BUF_SIZE]u8`) or one declared later in the same
file was a located error in ritz1 while ritz0 accepted it.  ritz1 now keeps
such a length pending and resolves it once the modules are merged, before
anything reads it: every row below would fail if any one site kept the
placeholder.

`sizeof([N]T)` (grammar AGAST #2124) took only a NUMBER; it takes the same
constant expression now.

Each program exits 3 when every length came out right, and a distinct code
naming the site otherwise.  All three compilers must agree.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# Imported by the "imported_*" rows.
HELPER = "pub const BUF_SIZE: i32 = 6\npub const ROWS: i32 = BUF_SIZE - 4\n"

PROGRAMS = {
    # A local: its alloca, indexing and sizeof.
    "later_local": """\
pub fn main() -> i32
    var a: [N]i32
    a[N - 1] = 3
    if sizeof(a) != 20
        return 10
    return a[4]

const N: i32 = 2 + 3
""",
    # A struct field: the layout of the field and of everything after it.
    "later_struct_field": """\
struct S
    cells: [N]u8
    tail: i64

pub fn main() -> i32
    var s: S
    s.cells[N - 1] = 1
    s.tail = 2
    if sizeof(S) != 16
        return 10
    return (s.cells[4] as i32) + (s.tail as i32)

const N: i32 = 5
""",
    "later_global": """\
var g_buf: [N * 2]i64

pub fn main() -> i32
    g_buf[N * 2 - 1] = 3
    if sizeof(g_buf) != 48
        return 10
    return g_buf[5] as i32

const N: i32 = 3
""",
    # N-D shapes: a local, a struct field, and a global.
    "later_nd": """\
struct Grid
    m: [R][C]i32

var g_m: [R][C]u8

pub fn main() -> i32
    var m: [R][C]i32
    m[R - 1][C - 1] = 1
    if sizeof(m) != 24
        return 10
    var g: Grid
    g.m[1][2] = 1
    if sizeof(Grid) != 24
        return 11
    g_m[1][2] = 1
    if sizeof(g_m) != 6
        return 12
    return m[1][2] + g.m[1][2] + (g_m[1][2] as i32)

const R: i32 = 2
const C: i32 = R + 1
""",
    # A pointer-to-array param and a type alias carry the length too.
    "later_ptr_param_and_alias": """\
type Row = [N]i32

fn last(p: *[N]i32) -> i32
    return (*p)[N - 1]

pub fn main() -> i32
    var r: Row
    r[N - 1] = 3
    if sizeof(Row) != 16
        return 10
    return last(@r)

const N: i32 = 4
""",
    "imported_sites": """\
import helper

struct Buf
    data: [BUF_SIZE]u8
    len: i32

var g_line: [BUF_SIZE * 2]u8

pub fn main() -> i32
    var b: Buf
    b.data[BUF_SIZE - 1] = 1
    if sizeof(Buf) != 12
        return 10
    var m: [ROWS][BUF_SIZE]i32
    m[ROWS - 1][BUF_SIZE - 1] = 1
    if sizeof(m) != 48
        return 11
    g_line[11] = 1
    if sizeof(g_line) != 12
        return 12
    return (b.data[5] as i32) + m[1][5] + (g_line[11] as i32)
""",
    # `sizeof([N]T)`: a later const, an imported one, an expression, N-D.
    "sizeof_array_type": """\
import helper

pub fn main() -> i32
    if sizeof([N]u8) != 7
        return 10
    if sizeof([BUF_SIZE]i32) != 24
        return 11
    if sizeof([N * 2]u16) != 28
        return 12
    if sizeof([ROWS][N]i64) != 112
        return 13
    if sizeof([2]i32) != 8
        return 14
    return 3

const N: i32 = 7
""",
}

# Still not constant once everything is merged: the located error #2153 gave,
# once, at the `[`, and no IR.  (program, line, col)
STILL_UNFOLDABLE = {
    "later_non_const": (
        """\
pub fn main() -> i32
    var a: [M]i32
    return 0

fn five() -> i32
    return 5

const M: i32 = five()
""",
        2, 12,
    ),
    "unknown_in_sizeof": (
        """\
pub fn main() -> i32
    return sizeof([NOPE]u8) as i32
""",
        2, 19,
    ),
}


def _compile(compiler, src, ll, cwd):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=cwd, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=300)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_deferred_array_length(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    (tmp_path / "helper.ritz").write_text(HELPER)
    src = tmp_path / "main.ritz"
    src.write_text(PROGRAMS[name])
    ll = tmp_path / "main.ll"
    comp = _compile(compiler, src, ll, tmp_path)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-2000:]}"
    assert subprocess.run([str(exe)], capture_output=True, timeout=60).returncode == 3


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
@pytest.mark.parametrize("name", sorted(STILL_UNFOLDABLE))
def test_ritz1_rejects_length_unfoldable_after_merge(request, tmp_path, compiler, name):
    request.getfixturevalue("ritz1_bin")
    program, line, col = STILL_UNFOLDABLE[name]
    src = tmp_path / "main.ritz"
    src.write_text(program)
    ll = tmp_path / "main.ll"
    comp = _compile(compiler, src, ll, tmp_path)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {name!r}:\n{out[-1000:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name!r}"
    hits = re.findall(rf"main\.ritz:{line}:{col}: error: array length ", out)
    assert len(hits) == 1, out[-2000:]


# AGAST #4769: an alias whose length is a const from another module, used from
# a third.  The second pass parses main before a/t.ritz, so main replayed the
# first pass's alias snapshot (length still pending, 0): `@g` became
# `[0 x i8]`, `fill(@&g)` was refused, and an index ran past a 0-byte global.
# Each file of a row is (path, text); main.ritz exits 3 when every length is
# right.
THIRD_MODULE = {
    "alias_global_ref": {
        "a/c.ritz": "pub const N: u64 = 16\n",
        "a/t.ritz": """\
import a.c { N }
pub type Buf = [N]u8

pub fn fill(b:& Buf) -> u64
    b[N - 1] = 7
    sizeof(Buf)
""",
        "main.ritz": """\
import a.t { Buf, fill }

var g: Buf

struct Holder
    buf: Buf
    tail: u8

pub fn main() -> i32
    if fill(@&g) != 16
        return 10
    if g[15] != 7
        return 11
    if sizeof(g) != 16
        return 12
    var h: Holder
    h.tail = 1
    if sizeof(Holder) != 17
        return 13
    var l: Buf
    l[15] = 2
    return (g[15] as i32) - (l[15] as i32) - (h.tail as i32) - 1
""",
    },
    # Aliases of aliases, each in its own module: one link settles a pass,
    # so this takes five.
    "alias_chain": {
        "a/c.ritz": "pub const N: i32 = 5\n",
        "a/t.ritz": "import a.c { N }\npub type Row = [N]i32\n",
        "a/u.ritz": "import a.t { Row }\npub type Line = Row\n",
        "a/v.ritz": "import a.u { Line }\npub type Lane = Line\n",
        "a/w.ritz": "import a.v { Lane }\npub type Path = Lane\n",
        "main.ritz": """\
import a.w { Path }

var g: Path

pub fn main() -> i32
    g[4] = 3
    if sizeof(g) != 20
        return 10
    return g[4]
""",
    },
}


def _write_tree(root, files):
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def _compile_tree(compiler, root):
    env = dict(os.environ, RITZ_PATH=f"{root}:{RITZ_ROOT}")
    src, ll = root / "main.ritz", root / "main.ll"
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=root, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=root, env=env,
                          capture_output=True, text=True, timeout=300, check=False)


def _compile_module(compiler, root, rel):
    env = dict(os.environ, RITZ_PATH=f"{root}:{RITZ_ROOT}")
    ll = root / (rel.replace("/", "_") + ".ll")
    if compiler == "ritz0":
        comp = run_ritz0([str(root / rel), "--no-runtime", "-o", str(ll)],
                         cwd=root, env=env, timeout=300)
    else:
        comp = subprocess.run([str(RITZ1_BUILD / compiler), str(root / rel), "-o", str(ll)],
                              cwd=root, env=env, capture_output=True, text=True, timeout=300, check=False)
    assert comp.returncode == 0, f"{compiler} {rel}:\n{comp.stdout[-1000:]}\n{comp.stderr[-2000:]}"
    return ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(THIRD_MODULE))
def test_alias_length_from_third_module(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    _write_tree(tmp_path, THIRD_MODULE[name])
    comp = _compile_tree(compiler, tmp_path)
    ll = tmp_path / "main.ll"
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    assert "[0 x" not in ll.read_text(), f"{compiler} emitted a zero-length array"
    # Each module is its own object: main.ll only declares `fill`.
    objs = [str(ll)]
    for rel in sorted(THIRD_MODULE[name]):
        if rel != "main.ritz":
            objs.append(str(_compile_module(compiler, tmp_path, rel)))
    exe = tmp_path / "main"
    link_cmd = ["clang", *objs, "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(1, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-2000:]}"
    assert subprocess.run([str(exe)], capture_output=True, timeout=60, check=False).returncode == 3


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_ritz1_rejects_unfoldable_alias_length_from_third_module(request, tmp_path, compiler):
    """An imported alias whose length never folds is refused at its `[`, never
    emitted as `[0 x T]` (AGAST #4769)."""
    request.getfixturevalue("ritz1_bin")
    _write_tree(tmp_path, {
        "a/c.ritz": "pub const N: u64 = 16\n",
        "a/t.ritz": "import a.c { N }\npub type Buf = [NOPE]u8\n",
        "main.ritz": "import a.t { Buf }\n\nvar g: Buf\n\npub fn main() -> i32\n    0\n",
    })
    comp = _compile_tree(compiler, tmp_path)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted it:\n{out[-1000:]}"
    assert not (tmp_path / "main.ll").exists(), f"{compiler} wrote IR"
    assert re.search(r"t\.ritz:2:16: error: array length ", out), out[-2000:]
