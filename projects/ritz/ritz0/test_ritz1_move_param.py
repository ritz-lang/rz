"""Regression tests for AGAST #1527: ritz1 must accept the move parameter
`name:= T`.

ritz0 lexes `:=` as one COLON_EQ token and parses `name:= T` as a parameter
with `Borrow.MOVE`. Nothing past the symbol table reads that flag: the
emitter, type checker and move checker treat it exactly like a by-value
`name: T`. That matches LANGUAGE_SPEC §13.2: a by-value parameter of a
move-only type already takes ownership, so `:=` is an ownership marker only.

ritz1's grammar had no `:=` parameter alternative. `fn take(r:= R)` matched
no `param`, so the whole item failed with `cannot parse item starting at
'fn take'`. That is the first stop for angelo's types, cache, discovery, font
and loader/ttf modules under `--compiler ritz1`.

ritz1 lexes `:=` as COLON ASSIGN (as it lexes `:&` as COLON AMP), and the new
alternative builds the same Param as `name: T`. So everything §13 does for a
by-value parameter (a Copy type copies, a Drop type moves and is dropped once,
by the callee) must hold for `:=` too. The Drop cases check that with the
free-count style of test_ownership_free_count.py: a run that drops twice, or
never, exits with the wrong status.

ritz0 is the oracle. Each program's expected exit status is checked against
it, so an oracle change shows up as its own failure.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0
from test_ritz1_builtin_struct_shadow import _run_pkg

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

POINT = """\
struct Point
    x: i32
    y: i32

struct Bag
    total: i32

"""

# The instrumented Drop type from test_ownership_free_count.py.
TRACKED = """\
trait Drop
    fn drop(self: @&Self)

var DROPS: i32 = 0

struct Tracked
    id: i32

impl Drop for Tracked
    fn drop(self: @&Tracked)
        DROPS = DROPS + 1

fn make(id: i32) -> Tracked
    return Tracked { id: id }

"""

# --- `:=` forms that #1527 rejects -------------------------------------------

# name -> (program, expected exit status)
MOVE_FORMS = {
    # The ticket's repro.
    "repro": ("""\
struct R
    pos: i64

fn take(r:= R) -> i64
    return r.pos

pub fn main() -> i32
    let r = R { pos: 4 }
    return take(r) as i32
""", 4),
    # A Copy struct: `:=` copies it, so the caller's `a` stays usable.
    "free_fn_copy_struct": (POINT + """\
fn sum(p:= Point) -> i32
    return p.x + p.y

pub fn main() -> i32
    let a = Point { x: 1, y: 2 }
    let s = sum(a)
    return s + a.x
""", 4),
    # angelo's shape: `fn add_contour(self:& GlyphOutline, contour:= Contour)`.
    "method_after_self_borrow": (POINT + """\
impl Bag
    fn add(self:& Bag, p:= Point)
        self.total = self.total + p.x + p.y

pub fn main() -> i32
    var b = Bag { total: 0 }
    b.add(Point { x: 1, y: 2 })
    b.add(Point { x: 3, y: 4 })
    return b.total
""", 10),
    # A static method (no receiver) whose first parameter is `:=`.
    "static_method": (POINT + """\
impl Bag
    fn build(p:= Point) -> Bag
        return Bag { total: p.x * p.y }

pub fn main() -> i32
    let b = Bag.build(Point { x: 2, y: 3 })
    return b.total
""", 6),
    # angelo's `fn load_font_data(data:= Vec<u8>)`: a generic type argument.
    "vec_u8": ("""\
import ritzlib.memory
import ritzlib.gvec

fn total(data:= Vec<u8>) -> i32
    var s: i32 = 0
    var i: i64 = 0
    while i < vec_len<u8>(@data)
        s = s + vec_get<u8>(@data, i) as i32
        i = i + 1
    return s

pub fn main() -> i32
    var v: Vec<u8> = vec_new<u8>()
    vec_push<u8>(@&v, 2 as u8)
    vec_push<u8>(@&v, 5 as u8)
    let s = total(v)
    vec_drop<u8>(@&v)
    return s
""", 7),
    # A Drop type moves into the callee, which drops it once: DROPS == 1
    # after the call, and main does not drop the moved-from `t` again.
    # Exit = DROPS * 10 + id.
    "drop_free_fn": (TRACKED + """\
fn consume(t:= Tracked) -> i32
    return t.id

pub fn main() -> i32
    var t = make(3)
    let r = consume(t)
    return DROPS * 10 + r
""", 13),
    "drop_method_after_self_borrow": (TRACKED + """\
struct Sink
    n: i32

impl Sink
    fn eat(self:& Sink, t:= Tracked) -> i32
        self.n = self.n + 1
        return t.id

pub fn main() -> i32
    var s = Sink { n: 0 }
    var t = make(3)
    let r = s.eat(t)
    return DROPS * 10 + r + s.n
""", 14),
    "drop_static_method": (TRACKED + """\
impl Tracked
    fn take(t:= Tracked) -> i32
        return t.id

pub fn main() -> i32
    var t = make(3)
    let r = Tracked.take(t)
    return DROPS * 10 + r
""", 13),
    # Two `:=` params of a Drop type in one signature: both owned, both
    # dropped by the callee.
    "drop_two_move_params": (TRACKED + """\
fn both(a:= Tracked, b:= Tracked) -> i32
    return a.id + b.id

pub fn main() -> i32
    var a = make(1)
    var b = make(2)
    let r = both(a, b)
    return DROPS * 10 + r
""", 23),
}

# --- borrow forms that already worked, pinned against regression ------------

CONTROL_FORMS = {
    # `name:& T` (#1301): the alternative `:=` mirrors.
    "free_fn_colon_amp": ("""\
struct R
    pos: i64

fn seek(r:& R, p: i64)
    r.pos = p

pub fn main() -> i32
    var r: R = R { pos: 0 }
    seek(@&r, 3)
    return r.pos as i32
""", 3),
    # `self:&` receivers (#1522), typed and bare.
    "self_colon_amp": ("""\
struct R
    pos: i64

impl R
    fn seek(self:& R, p: i64)
        self.pos = p

    fn bump(self:&)
        self.pos = self.pos + 1

pub fn main() -> i32
    var r: R = R { pos: 0 }
    r.seek(2)
    r.bump()
    return r.pos as i32
""", 3),
    # A plain by-value Drop parameter: the `:=` Drop cases must match it.
    "drop_plain_by_value": (TRACKED + """\
fn consume(t: Tracked) -> i32
    return t.id

pub fn main() -> i32
    var t = make(3)
    let r = consume(t)
    return DROPS * 10 + r
""", 13),
}

ALL_FORMS = {**MOVE_FORMS, **CONTROL_FORMS}


def _compile(compiler: str, tmp_path: Path, program: str):
    src = tmp_path / "main.ritz"
    src.write_text(program)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        comp = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
    return comp, ll


def _run(compiler: str, tmp_path: Path, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code.

    A program that imports ritzlib goes through build.py, which also compiles
    and links the imported modules (gvec needs ritzlib.memory's allocator).
    """
    if "import " in program:
        return _run_pkg(compiler, tmp_path, "main", program)
    comp, ll = _compile(compiler, tmp_path, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(MOVE_FORMS))
def test_move_param(request, tmp_path, compiler, name):
    """AGAST #1527. Before the fix each was a ritz1 parse error (exit 1)."""
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    program, expected = MOVE_FORMS[name]
    rc = _run(compiler, tmp_path, program)
    assert rc == expected, f"{compiler} {name}: exit {rc}, expected {expected}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CONTROL_FORMS))
def test_borrow_param_controls(request, tmp_path, compiler, name):
    """Parameter forms that parsed before the fix must still work."""
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    program, expected = CONTROL_FORMS[name]
    rc = _run(compiler, tmp_path, program)
    assert rc == expected, f"{compiler} {name}: exit {rc}, expected {expected}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_move_param_use_after_move_rejected(request, tmp_path, compiler):
    """`:=` takes ownership of a Drop type: using the source afterwards is an error.

    This is what pins `:=` to the move checker. A fix that lowered `:=` to a
    borrow would accept this program.
    """
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    comp, ll = _compile(compiler, tmp_path, TRACKED + """\
fn consume(t:= Tracked) -> i32
    return t.id

pub fn main() -> i32
    var t = make(3)
    consume(t)
    return t.id
""")
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted a use after move:\n{out[-1000:]}"
    assert "Traceback" not in out, out[-2000:]
    assert "use of moved value: `t`" in out, out[-2000:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("spelling", ["r:== R", "r:=& R"])
def test_malformed_move_param_rejected(request, tmp_path, compiler, spelling):
    """The new alternative accepts `:=` followed by a type, nothing looser."""
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    comp, ll = _compile(compiler, tmp_path, f"""\
struct R
    pos: i64

fn take({spelling}) -> i64
    return 4

pub fn main() -> i32
    let r = R {{ pos: 4 }}
    return take(r) as i32
""")
    assert comp.returncode != 0, f"{compiler} accepted `{spelling}`:\n{comp.stdout[-1000:]}"
    assert not ll.exists(), f"{compiler} wrote an artifact for `{spelling}`"
