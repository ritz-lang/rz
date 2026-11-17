"""Regression tests for AGAST #1456 — ritz1 parses `async fn` and `await`.

ritz1 had no `async` / `await` tokens, so every async item stopped the parse:

    error: ritzlib/async/blocking_fs.ritz:25:1: cannot parse item starting at 'async'

and the compile dropped every item after the first one.

What this ticket does is parse only.  ritz0 never lowers an `async fn` as a
plain fn: it always builds a state machine (a `<f>_Future` struct, a `<f>_poll`
fn, a sync wrapper for `async fn main`; ritz0/async_transform_v2.py).  As
#1456 required, that lowering is split out to AGAST #3814.  Until #3814 lands,
ritz1 parses each form into the AST (FnDef.is_async, an EXPR_AWAIT node) and
then refuses it at its own location, once, naming #3814.  It never emits it
as a plain fn, which would let a caller drop the `await` that #1395
(LANGUAGE_SPEC §16.2) requires.

The tests pin:
  * each `async fn` form (`async fn`, `pub async fn`, an impl method) and
    each `await` (in an async fn, and in a sync fn) is reported at its own
    line:col, once, with no "cannot parse" error;
  * ritzlib/async/blocking_fs.ritz (the ticket's module) has no parse errors;
  * `async` stays usable as an import path segment
    (`import ritzlib.async.tasks`), which making it a keyword could break.

When #3814 lands, the refusal cases become run-and-compare-with-ritz0 cases.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"

REFUSAL = "AGAST #3814"

# The minimal repro from #1456's #1789 survey (65_async_main), verbatim.
REPRO_65 = """\
async fn compute_result(x: i32) -> i32
    x * 7 + 3

async fn main() -> i32
    let result: i32 = await compute_result(5)
    result - 38
"""


def _ritz1(tmp_path: Path, src: Path):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(tmp_path / "out.ll"), "-I", str(RITZ_ROOT)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300, check=False,
    )


def _compile_text(tmp_path: Path, text: str):
    src = tmp_path / "m.ritz"
    src.write_text(text)
    return _ritz1(tmp_path, src)


def _refusals(stderr: str):
    """(line, col, text) of each error line naming the lowering ticket."""
    out = []
    for ln in stderr.splitlines():
        m = re.search(r":(\d+):(\d+): error: (.*)", ln)
        if m and REFUSAL in ln:
            out.append((int(m.group(1)), int(m.group(2)), m.group(3)))
    return out


def _assert_parsed(res):
    assert "cannot parse" not in res.stderr, res.stderr
    assert res.returncode != 0, "refused forms must fail the compile until #3814"


@pytest.mark.integration
def test_repro_65_refused_where_written(ritz1_bin, tmp_path):
    """Both async fns at their `async`, the await at its `await`, once each."""
    res = _compile_text(tmp_path, REPRO_65)
    _assert_parsed(res)
    # Sorted: an async fn is refused once its body has parsed, after its awaits.
    got = sorted(_refusals(res.stderr))
    assert [(l, c) for l, c, _ in got] == [(1, 1), (4, 1), (5, 23)], res.stderr
    assert "async fn 'compute_result'" in got[0][2]
    assert "async fn 'main'" in got[1][2]
    assert "await" in got[2][2]


# Each item form, alone, with the line:col its refusal must carry.
FORMS = {
    "pub_async_fn": ("pub async fn f() -> i32\n    1\n", (1, 1), "async fn 'f'"),
    "after_other_item": (
        "const K: i32 = 1\n\nasync fn g() -> i32\n    K\n", (3, 1), "async fn 'g'"),
    "impl_method": (
        "struct S\n    v: i32\n\nimpl S\n    async fn get(self: *S) -> i32\n        1\n",
        (5, 5), "async fn 'get'"),
    "pub_impl_method": (
        "struct S\n    v: i32\n\nimpl S\n    pub async fn get(self: *S) -> i32\n        1\n",
        (5, 5), "async fn 'get'"),
    # ritz0 lowers this to a poll loop (62_async_compiler's test_await_in_sync_fn).
    "await_in_sync_fn": (
        "fn h() -> i32\n    1\n\nfn k() -> i32\n    let v: i32 = await h()\n    v\n",
        (5, 18), "await"),
    # A match arm's body is parsed twice (backtracking): still one refusal.
    "await_in_match_arm": (
        "fn h() -> i32\n    1\n\nfn k() -> i32\n    match h()\n"
        "        1 => 3\n        _ => await h()\n",
        (7, 14), "await"),
    # An attribute's item-kind lookahead must see `async fn` as a fn.
    "attributed": ("[[inline]]\nasync fn a() -> i32\n    1\n", (2, 1), "async fn 'a'"),
}


@pytest.mark.integration
@pytest.mark.parametrize("form", sorted(FORMS))
def test_form_refused_where_written(ritz1_bin, tmp_path, form):
    text, loc, what = FORMS[form]
    res = _compile_text(tmp_path, text)
    _assert_parsed(res)
    errors = [ln for ln in res.stderr.splitlines() if ": error: " in ln]
    assert all(REFUSAL in ln for ln in errors), res.stderr
    got = _refusals(res.stderr)
    assert [(l, c) for l, c, _ in got] == [loc], res.stderr
    assert what in got[0][2], res.stderr


@pytest.mark.integration
def test_blocking_fs_parses(ritz1_bin, tmp_path):
    """The ticket's module: every error is a #3814 refusal, none a parse stop."""
    res = _ritz1(tmp_path, RITZ_ROOT / "ritzlib" / "async" / "blocking_fs.ritz")
    _assert_parsed(res)
    errors = [ln for ln in res.stderr.splitlines() if ": error: " in ln]
    assert errors and all(REFUSAL in ln for ln in errors), res.stderr


@pytest.mark.integration
def test_async_import_path_segment(ritz1_bin, tmp_path):
    """`async` is a keyword now, and still a module path segment."""
    res = _compile_text(
        tmp_path, "import ritzlib.async.tasks\n\nfn main() -> i32\n    0\n")
    assert res.returncode == 0, res.stderr
