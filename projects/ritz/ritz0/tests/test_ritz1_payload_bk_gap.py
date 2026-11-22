"""AGAST #4280 / #4265: Sema and the emitter agree on an Option / Result
payload binding's bool kind.

THE GAPS

RITZ1_SEMA_PROBE (test_ritz1_sema_type.py) compares Sema's sema_bool_kind with
the emitter's bool_kind on each expression; one sure and the other not is a
`bk-gap`.  Two kinds were open on a `match` arm's payload binding:

- #4280: `Some(p) => read_tag(p)` over `Option<*Inner>` (mangled
  `Option$ptr_Inner`).  #4200 taught Sema the `ptr_T` payload is a pointer;
  the emitter's payload_bool_kind (emitter_match.ritz) still read it with
  bk_tagged_payload, which leaves `ptr_T` unsure, and its bool_note_binding
  could only record a bool or an integer on the LocalVar anyway.
- #4265: `Err(e) => code(e)` over `Result<i32, E2>`, E2 a user enum (fs's
  `Errno` since #4248), and `Some(w)` over `Option<E2>`.  Sema left the binding
  untyped (sema_arm_payload_ty typed a struct payload only), while the emitter
  knew it was the enum.  A struct payload (`Err(e)` of `Result<i64, Oops>`,
  `Some(s)` of `Option<StrView>`) was typed by Sema but its bool kind stayed
  unsure: sbk_payload_struct stops at a typed binding.

THE TESTS

Each shape compiles under the probe on ritz1 and the self-hosted ritz1 with no
bk-gap and no mismatch, and runs to its expected exit code.  The dump pins
Sema's type of the user-enum bindings (the enum, as a `let x: E2` is), and
`if e` on one now gets the enum's report instead of "cannot tell".
"""

import os
import re
import subprocess

import pytest
from test_ref_into_value import RITZ1_BUILD, RITZ_ROOT, _compile, _link

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

SUMMARY = re.compile(
    r"sema-probe: (\d+) compared, (\d+) mismatched, (\d+) lenient, "
    r"(\d+) unknown, (\d+) bool-gap, (\d+) bk-gap"
)
DUMP = re.compile(r"^sema-type: (\d+):(\d+) e(\d+) (-?\d+)(?: (\S+))?$", re.MULTILINE)
STRUCT, E_IDENT = 100, 4

# One program per shape; each exits 0 when it computes the right answer.
SHAPES = {
    # #4280: a `ptr_T` Option payload, passed on.
    "option_ptr_payload": """\
struct Inner
    tag: i32

fn pick(p: *Inner) -> Option<*Inner>
    Some(p)

fn read_tag(p: *Inner) -> i64
    p.tag as i64

fn tag_of(o: Option<*Inner>) -> i64
    match o
        Some(p) => read_tag(p)
        None => -1

fn main() -> i32
    var inn: Inner = Inner { tag: 7 }
    if tag_of(pick(@inn)) != 7
        return 1
    0
""",
    # #4280: a `ptr_T` Result Ok payload.
    "result_ptr_payload": """\
struct Inner
    tag: i32

fn pick(p: *Inner, bad: i32) -> Result<*Inner, i32>
    if bad == 1
        return Err(3)
    Ok(p)

fn read_tag(p: *Inner) -> i32
    p.tag

fn main() -> i32
    var inn: Inner = Inner { tag: 7 }
    let t: i32 = match pick(@inn, 0)
        Ok(p) => read_tag(p)
        Err(c) => c
    if t != 7
        return 1
    0
""",
    # #4265: a user-enum Err payload and a user-enum Some payload.
    "user_enum_payload": """\
enum E2
    A
    B(i32)

fn code(e: E2) -> i32
    match e
        A => 1
        B(n) => n

fn mk(k: i32) -> Result<i32, E2>
    if k == 0
        return Ok(5)
    Err(B(k))

fn opt(k: i32) -> Option<E2>
    if k == 0
        return None
    Some(A)

fn main() -> i32
    var r: Result<i32, E2> = mk(3)
    let c: i32 = match r
        Ok(v) => v
        Err(e) => code(e)
    let o: Option<E2> = opt(1)
    let d: i32 = match o
        Some(w) => code(w)
        None => 0
    if c != 3 or d != 1
        return 1
    0
""",
    # #4265: ritzlib.errno's Errno through fs (the two corpus gaps of #4248).
    "errno_payload": """\
import ritzlib.fs
import ritzlib.errno

fn main() -> i32
    var r: Result<i32, Errno> = unlink("/nonexistent/ritz-4265")
    let code: i64 = match r
        Ok(v) => -1
        Err(e) => e.code() as i64
    if code != 2
        return 1
    0
""",
    # A struct Err payload and a StrView Some payload, which Sema typed but
    # whose bool kind it left unsure.
    "struct_payload": """\
import ritzlib.strview

struct Oops
    code: i64

fn mk(bad: i64) -> Result<i64, Oops>
    if bad == 1
        return Err(Oops { code: 321 })
    Ok(5)

fn fail(o: Oops) -> i64
    o.code

fn or_none(o: Option<StrView>) -> i64
    match o
        Some(s) => s.len as i64
        None => -1

fn main() -> i32
    let r: i64 = match mk(1)
        Ok(n) => n
        Err(e) => fail(e)
    if r != 321
        return 1
    if or_none(None) != -1
        return 2
    0
""",
}


# Shapes whose program needs ritzlib's objects to link (this harness links the
# module alone): probed, not run.  The corpus runs fs's Errno payload.
PROBE_ONLY = {"errno_payload"}


def _probe(compiler, tmp_path, name, src, mode="1"):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT), RITZ1_SEMA_PROBE=mode)
    work = tmp_path / f"{name}_{compiler}_{mode}"
    work.mkdir()
    path = work / "main.ritz"
    path.write_text(src)
    ll = work / "main.ll"
    comp = subprocess.run(
        [str(RITZ1_BUILD / compiler), str(path), "-o", str(ll)],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return comp, ll, work


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(SHAPES))
def test_payload_binding_has_no_bk_gap(request, tmp_path, compiler, name):
    request.getfixturevalue("ritz1_bin")
    comp, ll, work = _probe(compiler, tmp_path, name, SHAPES[name])
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} refused {name}:\n{out[-2000:]}"
    )
    summary = SUMMARY.search(out)
    assert summary, f"{compiler}: no probe summary for {name}:\n{out[-2000:]}"
    gaps = [ln for ln in out.splitlines() if "bk-gap at" in ln or "mismatch" in ln]
    assert summary.group(2) == "0" and summary.group(6) == "0", (
        f"{compiler}: {name}:\n" + "\n".join(gaps)
    )
    if name in PROBE_ONLY:
        return
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, (
        f"{compiler}: {name} would not link:\n{link.stderr[-2000:]}"
    )
    assert (
        subprocess.run(
            [str(exe)], capture_output=True, timeout=60, check=False
        ).returncode
        == 0
    )


# (line, col) of `e` in `code(e)` and `w` in `code(w)` in user_enum_payload.
ENUM_BINDINGS = [(24, 24), (27, 25)]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_user_enum_payload_is_typed_as_the_enum(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, _, _ = _probe(
        compiler, tmp_path, "user_enum_payload", SHAPES["user_enum_payload"], "dump"
    )
    out = comp.stdout + comp.stderr
    seen = {
        (int(ln), int(col)): (int(ty), nm)
        for ln, col, k, ty, nm in DUMP.findall(out)
        if int(k) == E_IDENT
    }
    for at in ENUM_BINDINGS:
        assert seen.get(at) == (STRUCT, "E2"), (
            f"{compiler}: {at} wanted E2, got {seen.get(at)}"
        )


COND = """\
enum E2
    A
    B(i32)

fn mk(k: i32) -> Result<i32, E2>
    if k == 0
        return Ok(5)
    Err(B(k))

fn main() -> i32
    var r: Result<i32, E2> = mk(3)
    let c: i32 = match r
        Ok(v) => v
        Err(e) =>
            if e
                return 1
            2
    c
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_user_enum_payload_condition_names_the_enum(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, _, _ = _compile(compiler, tmp_path, "cond", COND)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted `if e` on an enum payload"
    assert (
        "main.ritz:15:16: error: if condition must be bool, got a struct or enum" in out
    ), out
