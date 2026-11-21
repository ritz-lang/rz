"""AGAST #4448: an `Option<*T>` / `Result<*T, E>` arm's payload is a pointer.

THE DEFECT

    fn nm(i: i64) -> Option<*u8>
        if i == 1
            return Some(c"alpha")
        return None

    match nm(i)
        Some(n) => print("  {n}\\n")
        None => pass

ritz0 prints `  alpha`; ritz1 and ritz1_selfhosted print `  4202496`, the
address, because `n` was bound as an i64 local instead of a `*u8`.  `{n}`
then took the integer path in print's Display dispatch.  Binding the payload
through an explicitly typed local (`let n: *u8 = p`) was the workaround;
every `Option<*T>` arm that binds and passes the payload on was affected.

THE FIX

emitter_match's payload bind (`emit_arm_payload_bind`) only knew a pointer to
a struct (carrier_payload_ptr_struct): a pointer to a primitive fell through
to the scalar i64 binding.  It now binds a one-level `*T` as the pointer
local a `let n: *T` makes, and Sema's `sema_arm_payload_ty` types the same
binding as TYPE_PTR so the checks agree with the emitter (#4280's rule).

ORACLE

ritz0's stdout; ritz1 and ritz1_selfhosted must match it byte for byte, and
the expected bytes are pinned too, so a bug all three share cannot pass.  Each
arm binds the payload without an outer annotation, which is the rule under
test.
"""

import os
import re
import subprocess

import pytest

from test_ref_into_value import COMPILERS, RITZ1_BUILD, RITZ_ROOT, _compile, _link

pytestmark = pytest.mark.integration

# (program, expected stdout).  One row per payload path: Option's Some,
# Result's Ok, Result's Err, and a user enum's tuple variant.  A row that
# only repeated another's was left out (docs/TESTING.md, "What a ritz0 pytest
# case costs").
RUNS = {
    # The ticket's repro, verbatim.
    "option_some_u8": (
        """\
import ritzlib.io
import ritzlib.option

fn nm(i: i64) -> Option<*u8>
    if i == 1
        return Some(c"alpha")
    return None

fn main() -> i32
    var i: i64 = 0
    while i < 3
        match nm(i)
            Some(n) =>
                print("  {n}\\n")
            None => pass
        i += 1
    0
""",
        b"  alpha\n",
    ),
    "result_ok_u8": (
        """\
import ritzlib.io
import ritzlib.result

fn pick(i: i64) -> Result<*u8, i64>
    if i == 0
        return Err(7)
    return Ok(c"beta")

fn main() -> i32
    match pick(0)
        Ok(n) => print("ok {n}\\n")
        Err(e) => print("err {e}\\n")
    match pick(1)
        Ok(n) => print("ok {n}\\n")
        Err(e) => print("err {e}\\n")
    0
""",
        b"err 7\nok beta\n",
    ),
    "result_err_u8": (
        """\
import ritzlib.io
import ritzlib.result

fn pick(i: i64) -> Result<i64, *u8>
    if i == 0
        return Err(c"gamma")
    return Ok(9)

fn main() -> i32
    match pick(0)
        Ok(n) => print("ok {n}\\n")
        Err(e) => print("err {e}\\n")
    match pick(1)
        Ok(n) => print("ok {n}\\n")
        Err(e) => print("err {e}\\n")
    0
""",
        b"err gamma\nok 9\n",
    ),
    "user_enum_ptr_u8": (
        """\
import ritzlib.io

enum Slot
    P(*u8)
    N

fn pick(i: i64) -> Slot
    if i == 1
        return P(c"delta")
    return N

fn main() -> i32
    var i: i64 = 0
    while i < 2
        match pick(i)
            P(p) => print(" {p}\\n")
            N => pass
        i += 1
    0
""",
        b" delta\n",
    ),
}

# The binding is a pointer, not just printed as one: `*n` reads a byte and
# `n + 1` steps by one.  Exits 0 when both reads are right.
DEREF = """\
import ritzlib.io
import ritzlib.option

fn mk() -> Option<*u8>
    Some(c"hello")

fn main() -> i32
    match mk()
        Some(n) =>
            let a: i32 = (*n) as i32
            let b: i32 = (*(n + 1)) as i32
            if a != 104 or b != 101
                return 1
        None => return 2
    0
"""


def _stdout(compiler, tmp_path, name, src):
    comp, ll, work = _compile(compiler, tmp_path, name, src)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} refused {name}:\n{(comp.stdout + comp.stderr)[-2000:]}"
    )
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, (
        f"{compiler}: {name} would not link:\n{link.stderr[-2000:]}"
    )
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    return run.returncode, run.stdout


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_payload_prints_as_the_pointer(tmp_path, compiler, name):
    if compiler != "ritz0":
        assert (RITZ1_BUILD / compiler).exists()
    src, expected = RUNS[name]
    code, out = _stdout(compiler, tmp_path, name, src)
    assert code == 0, f"{compiler}, {name}: exited {code}"
    assert out == expected, f"{compiler}, {name}: printed {out!r}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_payload_binds_as_a_usable_pointer(tmp_path, compiler):
    code, _ = _stdout(compiler, tmp_path, "deref", DEREF)
    assert code == 0, f"{compiler}: a *u8 payload did not deref / step as one"


DUMP = re.compile(r"^sema-type: (\d+):(\d+) e(\d+) (-?\d+)(?: (\S+))?$", re.MULTILINE)
E_IDENT, PTR = 4, 5

# (line, col) of `n` in each `Some(n) => (*n)` of `SEMA_SHAPE`.
SEMA_BINDINGS = [(5, 22), (15, 22)]

SEMA_SHAPE = """\
import ritzlib.option

fn u8_of(o: Option<*u8>) -> i32
    match o
        Some(n) => (*n) as i32
        None => 0

fn back(p: *u8) -> Option<*u8>
    Some(p)

fn main() -> i32
    var b: u8 = 5
    let o: Option<*u8> = back(@b)
    match o
        Some(n) => (*n) as i32
        None => 0
"""


@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_sema_types_the_payload_as_a_pointer(tmp_path, compiler):
    work = tmp_path / f"sema_{compiler}"
    work.mkdir()
    path = work / "main.ritz"
    path.write_text(SEMA_SHAPE)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT), RITZ1_SEMA_PROBE="dump")
    comp = subprocess.run(
        [str(RITZ1_BUILD / compiler), str(path), "-o", str(work / "main.ll")],
        cwd=work, env=env, capture_output=True, text=True, timeout=300,
    )
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0, f"{compiler} refused the probe shape:\n{out[-2000:]}"
    seen = {
        (int(ln), int(col)): (int(ty), nm)
        for ln, col, k, ty, nm in DUMP.findall(out)
        if int(k) == E_IDENT
    }
    for at in SEMA_BINDINGS:
        assert seen.get(at, (None, None))[0] == PTR, (
            f"{compiler}: `n` at {at} should be a pointer, got {seen.get(at)}"
        )
