"""AGAST #4604: a poll source returns `Option<T>` for any T, not only
`Option<i32>`.

AGAST #4558 typed a poll source's status as `Option<i32>`, but the await's
value stayed an i32 in both frontends: the async lowering runs before type
checking.  Now the await's type is the source's T, read from the callee's
declared return type:

  * a sync fn's call: the fn's `-> Option<T>`;
  * a method call `recv.m(..)`: the method's `-> Option<T>`, found through the
    receiver local's (or param's) declared type;

so `await` of an i64, pointer or struct source needs no i32 cast, and an
untyped `let v = await src()` is T in both compilers.  A source whose type the
lowering can't tell (a fn pointer's call) is refused at the await, not taken
for an i32.

Every row runs on ritz0, ritz1 and ritz1_selfhosted, and each program answers
0 or the number of the first check that failed.
"""

from pathlib import Path

import pytest

from test_borrow_param_ref_field import _compile, _run

RITZ_ROOT = Path(__file__).resolve().parents[2]
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


def _bin(compiler, ritz1_bin):
    return {"ritz0": None, "ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}[compiler]


def _kind(compiler):
    return "ritz0" if compiler == "ritz0" else "ritz1"


# Each source is Pending once, then Ready, so every await suspends and a local
# set before it lives in the future across the boundary.  `big`'s value needs
# all 64 bits: an i32 await truncates it.
SOURCES = """\
struct Pt
    x: i64
    y: i64

struct Src
    n: i32

var g_x: i32 = 7
var g_polls: i32 = 0

fn ready_now() -> bool
    g_polls = g_polls + 1
    g_polls % 2 == 0

fn big() -> Option<i64>
    if !ready_now()
        return None
    Some(5000000000)

fn ptr_src() -> Option<*i32>
    if !ready_now()
        return None
    Some(@g_x)

fn pt_src() -> Option<Pt>
    if !ready_now()
        return None
    Some(Pt { x: 3, y: 5000000000 })

impl Src
    fn poll(self: *Src) -> Option<i64>
        if !ready_now()
            return None
        Some((self.n as i64) * 1000000000)

"""

RUNS = {
    # A typed let of each T: no cast, and the value is whole.
    "typed_lets": SOURCES + """\
async fn go() -> i32
    let a: i64 = await big()
    if a != 5000000000
        return 1
    let p: *i32 = await ptr_src()
    if *p != 7
        return 2
    let q: Pt = await pt_src()
    if q.x != 3 or q.y != 5000000000
        return 3
    0

pub fn main() -> i32
    await go()
""",
    # An untyped let is T, and each lives in the future across a later await.
    "untyped_lets": SOURCES + """\
async fn go() -> i32
    let a = await big()
    let p = await ptr_src()
    let q = await pt_src()
    let z: i64 = await big()
    if a != 5000000000
        return 1
    if *p != 7
        return 2
    if q.x != 3 or q.y != 5000000000
        return 3
    if z != a
        return 4
    0

pub fn main() -> i32
    await go()
""",
    # A method source: T from the method's signature, through the receiver
    # param's type and a local's.
    "method_source": SOURCES + """\
async fn go(s: *Src) -> i32
    let a = await s.poll()
    if a != 5000000000
        return 1
    var t: Src = Src { n: 6 }
    let b: i64 = await t.poll()
    if b != 6000000000
        return 2
    0

pub fn main() -> i32
    var s: Src = Src { n: 5 }
    await go(@s)
""",
    # The await is an operand: its value, held in the future across the next
    # await, is T.
    "await_in_expression": SOURCES + """\
async fn sum() -> i64
    (await big()) + (await big())

pub fn main() -> i32
    let s: i64 = await sum()
    if s != 10000000000
        return 1
    0
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_poll_source_value_is_its_t(ritz1_bin, tmp_path, compiler, name):
    got = _run(_kind(compiler), _bin(compiler, ritz1_bin), tmp_path, name, RUNS[name])
    assert got == 0, f"{compiler} {name}: check {got} failed"


UNKNOWN = ("`await`: the poll source's type is unknown; a poll source is a call of a fn "
           "or method declared to return `Option<T>`")

# name -> (program, message both compilers give, line:col of the await)
REFUSALS = {
    # A method not returning an Option is no poll source.
    "method_not_option": (SOURCES + """\
impl Pt
    fn len(self: *Pt) -> i64
        self.x

async fn go(p: *Pt) -> i64
    let v: i64 = await p.len()
    v

pub fn main() -> i32
    var p: Pt = Pt { x: 1, y: 2 }
    (await go(@p)) as i32
""", "`await p.len(..)`: a poll source returns `Option<T>` (`None` while Pending, "
     "`Some(v)` when Ready); `len` does not", "41:18"),
    # A fn pointer's call: nothing declares what it returns here.
    "fn_pointer_source": (SOURCES + """\
async fn go() -> i64
    let f: fn() -> Option<i64> = big
    let v: i64 = await f()
    v

pub fn main() -> i32
    (await go()) as i32
""", UNKNOWN, "38:18"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSALS))
def test_poll_source_type_refused(ritz1_bin, tmp_path, compiler, name):
    program, message, where = REFUSALS[name]
    comp, _, _ = _compile(_kind(compiler), _bin(compiler, ritz1_bin), tmp_path, name, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {name}:\n{out[-2000:]}"
    assert message in out, f"{compiler} {name}:\n{out[-2000:]}"
    assert f"main.ritz:{where}" in out, f"{compiler} {name} not located at {where}:\n{out[-2000:]}"
