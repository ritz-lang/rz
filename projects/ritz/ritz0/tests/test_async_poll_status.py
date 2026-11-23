"""AGAST #4558: a hand-written poll source returns `Option<i32>`, not a
reserved i32.

Before #4558 a poll source was any `i32` call awaited directly, and the value
-4096 (`POLL_PENDING`, AGAST #4485) meant Pending, so no source could return
-4096 as a result.  Now the status is typed: `None` is Pending and `Some(v)`
is Ready(v), so every i32 is a genuine result, -1 and -4096 among them.

  * `await src()` in an async fn evaluates `src()` again at each poll until it
    is `Some(v)`, and is `v` (LANGUAGE_SPEC §16.1);
  * an `i32` call awaited there is no poll source: refused, as the
    `Option<i32>` it is not;
  * outside an async fn nothing can suspend, so awaiting a poll source there
    is refused at the `await` (§16.2).

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


# `later` is Pending twice, then Ready(-4096): the old reserved value is a
# result now.  `eperm` is Ready(-1) at once (-EPERM).  The hand-driven poll
# counts the polls, so a Pending that was taken for Ready (or the reverse)
# changes the answer.
SOURCES = """\
var g_n: i32 = 0

fn later() -> Option<i32>
    g_n = g_n + 1
    if g_n < 3
        return None
    Some(0 - 4096)

fn eperm() -> Option<i32>
    Some(0 - 1)

"""

RUNS = {
    "genuine_sentinels": SOURCES + """\
async fn both() -> i32
    let a: i32 = await later()
    let b: i32 = await eperm()
    if a != 0 - 4096
        return 1
    if b != 0 - 1
        return 2
    let c = await eperm()
    if c != 0 - 1
        return 3
    0

pub fn main() -> i32
    var f = both()
    var polls: i32 = 1
    while !future_poll(@&f)
        polls = polls + 1
    if polls != 3
        return 10 + polls
    let r: i32 = await f
    r
""",
    # The poll source's value is the operand of an expression, and the async
    # fn is driven by `await` in a sync fn (polled to completion in place).
    "await_in_expression": SOURCES + """\
async fn sum() -> i32
    (await later()) + (await eperm())

pub fn main() -> i32
    let s: i32 = await sum()
    if s != 0 - 4097
        return 1
    if g_n != 3
        return 2
    0
""",
    # With ritzlib.io imported, ritz0 has monomorphised `Option<i32>` to
    # `Option$i32` before the await is lowered: still a poll source.
    "source_type_monomorphised": "import ritzlib.io\n\n" + SOURCES + """\
async fn go() -> i32
    let a: i32 = await later()
    if a != 0 - 4096
        return 1
    0

pub fn main() -> i32
    await go()
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_poll_source_result_is_any_i32(ritz1_bin, tmp_path, compiler, name):
    got = _run(_kind(compiler), _bin(compiler, ritz1_bin), tmp_path, name, RUNS[name])
    assert got == 0, f"{compiler} {name}: check {got} failed"


# name -> (program, message both compilers give)
REFUSALS = {
    # An i32 call is not a poll source: there is no Pending it could say.
    "i32_source_in_async_fn": ("""\
fn plain() -> i32
    5

async fn go() -> i32
    let v: i32 = await plain()
    v

pub fn main() -> i32
    await go()
""", "`await plain(..)`: a poll source returns `Option<T>`"),
    # Outside an async fn nothing can suspend: a Pending source can't wait.
    "source_in_sync_fn": (SOURCES + """\
pub fn main() -> i32
    let v: i32 = await eperm()
    v + 1
""", "a poll source can only be awaited in an async fn"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSALS))
def test_poll_source_refused(ritz1_bin, tmp_path, compiler, name):
    program, message = REFUSALS[name]
    comp, _, _ = _compile(_kind(compiler), _bin(compiler, ritz1_bin), tmp_path, name, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {name}:\n{out[-2000:]}"
    assert message in out, f"{compiler} {name}:\n{out[-2000:]}"
