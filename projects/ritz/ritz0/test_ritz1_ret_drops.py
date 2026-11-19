"""ritz1 emits a `ret`'s drops where the `ret` is emitted (AGAST #3508, #1816).

Before #3508, ownership.ritz's own_end_fn copied each finished fn body out of
the output buffer and rescanned it for `  ret ` lines, inserting a drop of
EVERY owned binding of the fn before each one (and zeroing every drop flag in
the entry block so that the bindings not yet declared there dropped nothing).
Now the drops are emitted as the `ret` is: the owned bindings live there
(Sema's FnDef.own_binds says which locals own a value) and the live
temporaries, newest first.  A binding declared after a `return` is not
dropped by it, so its drop flag needs no zeroing at entry.

The drop counts themselves are test_ownership_free_count.py's and
test_ritz1_ownership.py's.
"""

import re
import subprocess
from pathlib import Path

import pytest

import fast_link
from test_ownership_free_count import PRELUDE, RITZ_START, SLOT, _compile

RITZ1S = ("ritz1", "ritz1_selfhosted")
SRC = Path(__file__).resolve().parent.parent / "ritz1" / "src"

# An early `return` before `t` is declared, then a `return` with `t` live.
EARLY = """\
fn f(x: i32) -> i32
    if x > 0
        return 7
    let t = make(1)
    return t.id

pub fn main() -> i32
    let a = f(1)
    let b = f(0)
    return DROPS * 100 + a + b
"""


# A `return` inside a statement whose temporary (`make(1)`) is still pending,
# with the arm binding `t` declared after it: newest first, `t` then the
# temporary (ORDER 21), as own_end_fn's reverse registration order dropped
# them before #3508.  ritz0 drops the temporary first (12): AGAST #4304.
PENDING_TEMP = SLOT + """\
fn pick(id: i32) -> Slot
    Slot.Full(make(id + 1))

fn g() -> i32
    match pick(make(1).id)
        Full(t) =>
            return t.id
        _ =>
            pass
    return 0

pub fn main() -> i32
    g()
    return ORDER
"""


def _build_run(compiler, tmp_path, body):
    src = tmp_path / "main.ritz"
    src.write_text(PRELUDE + body)
    ll = tmp_path / "main.ll"
    comp = _compile(compiler, src, ll, tmp_path)
    assert comp.returncode == 0 and ll.exists(), comp.stdout[-2000:] + comp.stderr[-2000:]
    exe = tmp_path / "main"
    link = fast_link.clang(["clang", str(RITZ_START), str(ll), "-o", str(exe), "-nostdlib"],
                           cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-2000:]
    rc = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    return ll.read_text(), rc


def _fn_ir(ll: str, name: str) -> str:
    m = re.search(r"^define [^\n]*@" + re.escape(name) + r"\(.*?^}", ll, re.S | re.M)
    assert m, f"no @{name} in the IR"
    return m.group(0)


def _blocks(fn_ir: str) -> list:
    """`fn_ir` split before each block label (`entry:`, `L3:`, `own.n0:`);
    [0] is the `define` line."""
    return re.split(r"(?m)^(?=[A-Za-z_.$][\w.$]*:)", fn_ir)


@pytest.mark.unit
def test_ownership_no_longer_rewrites_the_body():
    """own_end_fn's line rescan, and the imports only it and the glue's GEP
    and a deferred statement's emission needed, are gone."""
    text = (SRC / "ownership.ritz").read_text()
    imports = re.findall(r"(?m)^import (\S+)", text)
    for mod in ("ll_copy_scan", "emitter_expr", "emitter_stmt"):
        assert mod not in imports, f"ownership.ritz still imports {mod}"
    assert "ll_starts_with" not in text and "ll_line_len" not in text
    assert "s.out.len = body_start" not in text


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_early_return_drops_only_whats_live(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    ll, rc = _build_run(compiler, tmp_path, EARLY)
    f = _fn_ir(ll, "f")
    # The early `ret` drops nothing: `t` is not declared yet.  (Before #3508
    # its block was `own.n0:`, after a load of t's flag and a drop of t.)
    rets = re.findall(r"(?m)^  ret i32 .*$", f)
    assert len(rets) == 2, f
    head = f.partition(rets[0])[0]
    early_block = _blocks(head)[-1]
    assert early_block.startswith("L"), f
    assert "load i1" not in early_block and "@Tracked_drop" not in head, f
    # No flag is zeroed in the entry block: `t`'s flag is set at its `let`.
    entry = _blocks(f)[1]
    assert entry.startswith("entry:") and "store i1 0" not in entry, f
    # The `return t.id` drops `t`, once.
    tail = f.partition(rets[0])[2]
    assert tail.count("@Tracked_drop") == 1, f
    assert rc == 100 + 7 + 1, f"{compiler}: exit {rc}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ret_drop_order_pending_temp(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    _, rc = _build_run(compiler, tmp_path, PENDING_TEMP)
    assert rc == 21, f"{compiler}: ORDER {rc}"


# An array-valued tail `if` returns through emit_array_return_from, whose
# `ret` (by value, and `ret void` after the sret copy) must start the string
# it is emitted in, or emit_str never sees it and `t` is not dropped.
ARRAY_TAIL = """\
fn small(x: i32) -> [2]i32
    let t = make(5)
    if x > 0
        [t.id, 1]
    else
        [0, 0]

fn big(x: i32) -> [64]i64
    let t = make(6)
    if x > 0
        [7; 64]
    else
        [0; 64]

pub fn main() -> i32
    let a = small(1)
    let b = big(1)
    return DROPS * 10 + a[0] - 5 + (b[63] - 7) as i32
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_array_tail_return_drops(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    ll, rc = _build_run(compiler, tmp_path, ARRAY_TAIL)
    assert "@__ritz_sret_copy" in _fn_ir(ll, "big"), "big no longer returns through sret"
    assert rc == 20, f"{compiler}: exit {rc}"
