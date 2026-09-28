"""Regression tests for AGAST #1300 — ritz1 parity with #1299: nested generic
type-argument lists must be able to close with `>>`.

The lexer emits `>>` as a single SHR token, so `Vec<Vec<i64>>` ends in SHR,
never GT GT. ritz0 (#1299) splits the token in the parser. ritz1's parser is
generated from grammars/ritz1.grammar, which now lets one SHR close two
type-argument lists (`type_spec_shr` / `generic_args`). Before that, any item
mentioning a `>>`-closed generic failed with `cannot parse item`.

Covered here, because the regression matrix (which compiles
ritz0/test/test_issue_nested_generic_close.ritz under all three compilers)
cannot reach every shape:

* runnable programs, ritz0 as the oracle: 2-, 3- and 4-deep nests, a
  `>>`-closed generic call type argument, and the right-shift / comparison
  expressions that must NOT become generics.
* multi-parameter generic structs (AGAST #1574): `HashMap<Key,
  Vec<Connection>>` fields, `Pair<i64, Vec<i64>> { ... }` literals, `>>` in
  impl headers, and plain `Pair<i64, i32>`. ritz1 used to mangle and
  substitute on the FIRST type argument only (`%Pair$i64 = type {i64,
  %B$i64}`); it now mangles on every argument (`Pair$i64$i32`) and
  substitutes every parameter.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date; make's dependency graph decides the work.

    A stale ritz1 would assert against the old parser (see AGAST #1322).
    """
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", "ritz1", "ritz1"],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0 or not RITZ1_BIN.exists():
        pytest.fail(
            "could not build ritz1 for the nested-generic tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


def _build_runtime_start() -> None:
    proc = subprocess.run(
        ["make", "-C", "runtime", RITZ_START.name],
        cwd=RITZ_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0 or not RITZ_START.exists():
        pytest.fail(
            f"could not build the runtime start object {RITZ_START}:\n"
            f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
        )


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    _build_ritz1()
    _build_runtime_start()
    return RITZ1_BIN


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    proc = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    return proc, ll


def _compiled_ir(compiler: str, tmp_path: Path, name: str, program: str) -> str:
    """Compile and return the IR text; fail loudly on any compile error."""
    comp, ll = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    assert "cannot parse" not in comp.stderr, comp.stderr[-2000:]
    return ll.read_text()


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    _compiled_ir(compiler, tmp_path, name, program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(1, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link ({name}):\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


EXPECTED = 7

BOX = """\
struct Box<T>
    v: T

"""

OTHER = (
    BOX
    + """\
struct Other
    x: i64

"""
)

MAKE = """\
fn make<T>(x: T, o: *Other) -> Box<T>
    var b: Box<T>
    b.v = x
    return b

"""

# --- runnable: every program returns 7 only when it parsed and ran right ----
#
# Programs instantiate each nesting level explicitly and read one member at a
# time: ritz1's monomorphiser does not instantiate an inner generic the
# program never names, and has no member chains through a nested generic
# field (`b.v.v`). Neither is a parse problem; these tests are about `>>`.

RUNNABLE = {
    # The ticket's shape: two lists closed by one `>>`.
    "depth2": BOX
    + """\
pub fn main() -> i32
    var b1: Box<i64>
    b1.v = 7
    var b2: Box<Box<i64>>
    b2.v = b1
    let o1: Box<i64> = b2.v
    return o1.v as i32
""",
    # `>>` then `>`: the inner SHR closes two lists, a GT the third.
    "depth3": BOX
    + """\
pub fn main() -> i32
    var b1: Box<i64>
    b1.v = 7
    var b2: Box<Box<i64>>
    b2.v = b1
    var b3: Box<Box<Box<i64>>>
    b3.v = b2
    let o2: Box<Box<i64>> = b3.v
    let o1: Box<i64> = o2.v
    return o1.v as i32
""",
    # The ticket's 4-deep `A<B<C<D<i64>>>>`: SHR SHR, each closing two.
    "depth4": BOX
    + """\
pub fn main() -> i32
    var b1: Box<i64>
    b1.v = 7
    var b2: Box<Box<i64>>
    b2.v = b1
    var b3: Box<Box<Box<i64>>>
    b3.v = b2
    var b4: Box<Box<Box<Box<i64>>>>
    b4.v = b3
    let o3: Box<Box<Box<i64>>> = b4.v
    let o2: Box<Box<i64>> = o3.v
    let o1: Box<i64> = o2.v
    return o1.v as i32
""",
    # Same type spelled with a space and closed with `>>`, in one program:
    # both must name the same instantiation.
    "spaced_and_closed": BOX
    + """\
fn unwrap(b: *Box<Box<i64>>) -> i64
    let o1: Box<i64> = b.v
    return o1.v

pub fn main() -> i32
    var b1: Box<i64>
    b1.v = 7
    var b2: Box<Box<i64> >
    b2.v = b1
    return unwrap(@b2) as i32
""",
    # A generic call whose type argument is itself generic, closed by the
    # call's `>` sharing an SHR: `make<Box<i64>>(...)`. The `as *Other` cast
    # in the arguments parses a DIFFERENT type after the type argument, so a
    # mangler reading the parser's last-type-name state instead of the
    # captured argument would instantiate make$Other.
    "generic_call_type_arg": OTHER
    + MAKE
    + """\
pub fn main() -> i32
    var o: Other
    var b1: Box<i64>
    b1.v = 7
    let b2: Box<Box<i64>> = make<Box<i64>>(b1, @o as *Other)
    let o1: Box<i64> = b2.v
    return o1.v as i32
""",
    # The same call with the closers spelled apart: `make<Box<i64> >(...)`.
    "generic_call_type_arg_spaced": OTHER
    + MAKE
    + """\
pub fn main() -> i32
    var o: Other
    var b1: Box<i64>
    b1.v = 7
    let b2: Box<Box<i64> > = make<Box<i64> >(b1, @o as *Other)
    let o1: Box<i64> = b2.v
    return o1.v as i32
""",
    # A generic struct literal whose type argument closes with `>>`. The
    # field initialiser's cast parses another type before the literal is
    # built; it must still name Box$Box$i64.
    "generic_struct_lit": OTHER
    + """\
fn keep(b: Box<i64>, o: *Other) -> Box<i64>
    return b

pub fn main() -> i32
    var o: Other
    var b1: Box<i64>
    b1.v = 7
    let b2: Box<Box<i64>> = Box<Box<i64>> { v: keep(b1, @o as *Other) }
    let o1: Box<i64> = b2.v
    return o1.v as i32
""",
    # Right shift and comparison-with-shift must stay expressions.
    "rshift_expressions": """\
pub fn main() -> i32
    let x: i64 = 256
    let a: i64 = 1
    let b: i64 = 64
    let c: i64 = 4
    var r: i64 = 0
    if x >> 4 == 16
        r = r + 1
    if a < b >> c
        r = r + 2
    if (a << 3) >> 1 == 4
        r = r + 4
    return r as i32
""",
    # Generics and shifts in one function: `>>` means both, by position.
    "rshift_beside_generics": BOX
    + """\
pub fn main() -> i32
    var b1: Box<i64>
    b1.v = 28
    var b2: Box<Box<i64>>
    b2.v = b1
    let o1: Box<i64> = b2.v
    let s: i64 = o1.v >> 2
    return s as i32
""",
}

# ritz0 cannot store into a 3+-deep nested generic field (AGAST #1575).
# strict: the day ritz0 is fixed these XPASS and fail, so the mark gets removed.
RITZ0_BROKEN = {"depth3", "depth4"}


def _oracle_params():
    for name in sorted(RUNNABLE):
        marks = []
        if name in RITZ0_BROKEN:
            marks.append(pytest.mark.xfail(strict=True, reason="AGAST #1575"))
        yield pytest.param(name, marks=marks)


@pytest.mark.integration
@pytest.mark.parametrize("name", list(_oracle_params()))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, RUNNABLE[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RUNNABLE))
def test_ritz1_runs_nested_generic_close(ritz1_bin, tmp_path, name):
    """AGAST #1300. Before the fix: `cannot parse item` for every `>>` close."""
    assert _run("ritz1", tmp_path, name, RUNNABLE[name]) == EXPECTED


@pytest.mark.integration
def test_ritz1_depth4_mangles_every_level(ritz1_bin, tmp_path):
    """Each `>>` closes the RIGHT two lists: the type is Box$Box$Box$Box$i64."""
    ir = _compiled_ir("ritz1", tmp_path, "depth4_ir", RUNNABLE["depth4"])
    assert "%Box$Box$Box$Box$i64 = type" in ir, ir[:3000]


@pytest.mark.integration
def test_ritz1_generic_call_suffix_is_nested_type(ritz1_bin, tmp_path):
    """`make<Box<i64>>` instantiates `make$Box$i64`, not `make$Box`."""
    ir = _compiled_ir(
        "ritz1", tmp_path, "gencall_ir", RUNNABLE["generic_call_type_arg"]
    )
    assert "@make$Box$i64(" in ir, ir[:3000]


# --- multi-parameter generic structs (AGAST #1574) -------------------------

PAIR = """\
struct Pair<A, B>
    first: A
    second: B

"""

MULTI_ARG = {
    # The ticket's shape: the second parameter used to stay `%B$i64`.
    "pair_prims": PAIR
    + """\
pub fn main() -> i32
    var p: Pair<i64, i32>
    p.first = 3
    p.second = 4
    return (p.first + p.second as i64) as i32
""",
    # Two instantiations sharing the FIRST argument must stay two types:
    # mangling on the first argument alone collapsed both into Pair$i64.
    "pair_same_first_arg": PAIR
    + """\
pub fn main() -> i32
    var a: Pair<i64, i8>
    a.first = 1
    a.second = 2
    var b: Pair<i64, i64>
    b.first = 0
    b.second = 4294967300
    return (a.first + a.second as i64 + b.second - 4294967296) as i32
""",
    # Parameters in the other order, and three of them.
    "triple_reordered": """\
struct Triple<A, B, C>
    c: C
    a: A
    b: B

pub fn main() -> i32
    var t: Triple<i8, i32, i64>
    t.a = 1
    t.b = 2
    t.c = 4
    return (t.a as i64 + t.b as i64 + t.c) as i32
""",
    # A field typed by a generic OVER a parameter: `b: Box<B>` is `Box$B` in
    # the template and must become `Box$i32`, not `Box$B$i64$i32`.
    "field_generic_over_param": BOX
    + """\
struct Wrap<A, B>
    a: A
    b: Box<B>

pub fn main() -> i32
    var inner: Box<i32>
    inner.v = 4
    var w: Wrap<i64, i32>
    w.a = 3
    w.b = inner
    let o: Box<i32> = w.b
    return (w.a + o.v as i64) as i32
""",
    # A generic ENUM argument: `Option$i64` owns the `$i64` after it, so the
    # suffix `$Option$i64$i32` splits into two arguments, not three.  (Only
    # `second` is touched: storing `Some(..)` into a struct field is a
    # separate ritz1 gap, as is defining `%Option$i64` when only a struct
    # field names it — hence the `none` local.)
    "option_arg": PAIR
    + """\
pub fn main() -> i32
    let none: Option<i64> = None
    var p: Pair<Option<i64>, i32>
    p.second = 7
    return p.second
""",
    # The tempest shape (#1299): a nested generic LAST in a multi-arg list,
    # as a struct field and as a local.
    "multi_arg_field": """\
struct Connection
    id: i64

struct Key
    k: i64

struct HashMap<K, V>
    key: K
    value: V

struct Vec<T>
    item: T

struct Network
    connections: HashMap<Key, Vec<Connection>>

pub fn main() -> i32
    var c: Connection
    c.id = 7
    var v: Vec<Connection>
    v.item = c
    var n: Network
    n.connections.value = v
    let hm: HashMap<Key, Vec<Connection>> = n.connections
    let v2: Vec<Connection> = hm.value
    let c2: Connection = v2.item
    return c2.id as i32
""",
    "multi_arg_struct_lit": PAIR
    + BOX
    + """\
pub fn main() -> i32
    var inner: Box<i64>
    inner.v = 4
    let p: Pair<i64, Box<i64>> = Pair<i64, Box<i64>> { first: 3, second: inner }
    let b: Box<i64> = p.second
    return (p.first + b.v) as i32
""",
    # `>>` in an impl header. The method is compiled but not called: neither
    # compiler dispatches `b2.seven()` to an impl on a concrete instantiation
    # (ritz0: "No method 'seven' found for type 'Box$Box_i64'").
    "impl_header": BOX
    + """\
impl Box<Box<i64>>
    fn seven(self: *Box<Box<i64>>) -> i32
        return 7

pub fn main() -> i32
    var b1: Box<i64>
    b1.v = 7
    var b2: Box<Box<i64>>
    b2.v = b1
    let o1: Box<i64> = b2.v
    return o1.v as i32
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MULTI_ARG))
def test_ritz0_is_the_oracle_multi_arg(tmp_path, name):
    """The reference answer for the multi-parameter shapes."""
    assert _run("ritz0", tmp_path, name, MULTI_ARG[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MULTI_ARG))
def test_ritz1_runs_multi_arg_generic_struct(ritz1_bin, tmp_path, name):
    """AGAST #1574. Before the fix: `use of undefined type named 'B$i64'`."""
    assert _run("ritz1", tmp_path, name, MULTI_ARG[name]) == EXPECTED


@pytest.mark.integration
def test_ritz1_pair_substitutes_every_param(ritz1_bin, tmp_path):
    """`Pair<i64, i32>` is `%Pair$i64$i32 = type {i64, i32}`: no `$B`."""
    ir = _compiled_ir("ritz1", tmp_path, "pair_ir", MULTI_ARG["pair_prims"])
    assert re.search(r"%Pair\$i64\$i32 = type \{\s*i64,\s*i32\s*\}", ir), ir[:3000]
    assert "$B" not in ir, ir[:3000]


@pytest.mark.integration
def test_ritz1_multi_arg_mangles_on_every_arg(ritz1_bin, tmp_path):
    """`HashMap<Key, Vec<Connection>>` mangles as HashMap$Key$Vec$Connection.

    Not HashMap$Key (first argument only, #1574), and not HashMap$Connection
    (the tail's own generic clobbering a single global save slot, #1300).
    """
    ir = _compiled_ir("ritz1", tmp_path, "mangle", MULTI_ARG["multi_arg_field"])
    assert "%HashMap$Key$Vec$Connection = type" in ir, ir[:3000]
    assert "HashMap$Connection" not in ir, ir[:3000]
    assert not re.search(r"HashMap\$Key\b(?!\$)", ir), ir[:3000]
