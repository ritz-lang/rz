"""AGAST #2882: ritz1 types a bool UFCS method call by its callee's `i1`.

THE DEFECT

`s.is_empty()` on a `Span<u8>` dispatches through emit_ufcs_call to
`span_is_empty$u8`, which is `define ... i1`.  emit_ufcs_call had no
TYPE_BOOL arm, so it emitted `call i64 @span_is_empty$u8(..)` and used the
whole register: the callee only sets the low bit, so whatever sat in the
upper bits of the return register read as true.  test_issue_slice_generic_
siblings.ritz's test_span_builtin_methods returned 2 on ritz1 and
ritz1_selfhosted (ritz0 passed).  Every other call path (free fn, impl
method) already called a bool fn as `call i1` and zext'd the result.

THE TESTS

  * IR: one bool method per UFCS family -- generic (`Span$T` ->
    `span_*$T`), fixed prefix (`StrView` -> `strview_*`) and the non-generic
    table (`String` -> `string_*`) -- is called as `call i1`, never `i64`,
    and the result is zext'd to the i64 value model.
  * runtime: the ticket's repro (a Span from a by-value call) runs right.
"""

import os
import re
import subprocess

import pytest
from test_ritz1_builtin_struct_shadow import RITZ1_BIN, RITZ_ROOT, _run_pkg

# The ticket's repro: `s` is a Span returned by value, so its is_empty() result
# reaches the `if` through the UFCS path.
REPRO = """\
import ritzlib.span

fn head(s: Span<u8>) -> Span<u8>
    s.slice(0, 1)

fn main() -> i32
    let buf: [3]u8 = [4, 5, 6]
    let s = head(@buf)
    if s.is_empty()
        return 2
    let e = head(@buf).slice(0, 0)
    if not e.is_empty()
        return 3
    42
"""

STRVIEW = """\
import ritzlib.strview

fn main() -> i32
    let v: StrView = "abc"
    if v.is_empty()
        return 1
    42
"""

STRING = """\
import ritzlib.string

fn main() -> i32
    var s: String = string_new()
    if s.is_empty()
        return 1
    42
"""

# family -> (program, the bool UFCS helper main calls)
IR_CASES = {
    "span": (REPRO, "span_is_empty$u8"),
    "strview": (STRVIEW, "strview_is_empty"),
    "string": (STRING, "string_is_empty"),
}


def _main_body(tmp_path, name: str, program: str) -> str:
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll)],
        check=False,
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    text = ll.read_text()
    m = re.search(r'define [^\n]*@"?main"?\(', text)
    assert m, "no main in IR"
    return text[m.end() :].split("\n}", 1)[0]


@pytest.mark.integration
@pytest.mark.parametrize("family", sorted(IR_CASES))
def test_bool_ufcs_call_is_i1(ritz1_bin, tmp_path, family):
    program, sym = IR_CASES[family]
    body = _main_body(tmp_path, family, program)
    call_re = re.compile(
        r"(%\.\d+) = call (\w+) @\"?" + re.escape(sym) + r"\"?\(", re.MULTILINE
    )
    calls = call_re.findall(body)
    assert calls, f"no call to {sym} in main:\n{body}"
    for reg, ty in calls:
        assert ty == "i1", f"{sym} is bool (i1) but called as {ty}:\n{body}"
        # The i1 is widened, not tested as a whole register.
        assert re.search(rf"= zext i1 {re.escape(reg)} to i64", body), body


@pytest.mark.integration
def test_repro_runs(ritz1_bin, tmp_path):
    assert _run_pkg("ritz1", tmp_path, "repro", REPRO) == 42
