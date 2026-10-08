"""AGAST #1641: the `eprint` builtin, and StrView values in print/eprint placeholders.

THE GAP

    eprint("option '{name}' needs a value\\n")    # name: StrView

had two problems. There was no stderr counterpart to `print`, so error paths
were hand-rolled chains of eprints/eprint_int calls. And `{name}` was a
compile error in both compilers when `name` was a StrView
(`Cannot print value of type {i8*, i64}`), which is the most common thing a
message wants to print.

THE FIX

* `eprint(<literal>)` lowers exactly as `print(<literal>)` does, but writes to
  fd 2. That covers the placeholder rules, the `{{` escape, and the c-string
  rejection from #1394. ritz0 threads the fd through `_emit_interp_string_print`
  and `_emit_print_value`, and ritz1 passes 2 to `emit_print_literal`, which
  #1521 already parameterised by fd.
* A StrView placeholder (including the `%Span$u8` a bare `"..."` produces, and
  an `@StrView` / `*StrView`) writes its `len` bytes from `ptr`. It does not
  stop at a NUL, and it does not run past `len`.
* A String prints through its view, `string_as_view(@s)` (ritzlib.string);
  that case lives in the matrix file test/test_eprint_interpolation.ritz.

ORACLE

Each program is compiled by ritz0 and by ritz1 and run. Both binaries must
exit 0 and produce byte-identical stdout AND stderr, and each stream is also
pinned to a literal, so a bug both compilers share cannot pass.
"""

import os
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import RITZ0, RITZ1_BIN, RITZ_ROOT, RITZ_START
from test_ritz1_builtin_struct_shadow import ritz1_bin  # noqa: F401

# Build ritz1 (and the runtime start object) once for the module.
pytestmark = pytest.mark.usefixtures("ritz1_bin")

COMPILERS = ("ritz0", "ritz1")


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    """Compile `program`; return (CompletedProcess, path to .ll)."""
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    proc = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    return proc, ll


def _run(compiler: str, tmp_path: Path, name: str, program: str):
    """Compile, link, run; return (stdout, stderr) bytes. Asserts each step."""
    comp, ll = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    assert run.returncode == 0, (
        f"{compiler} binary for {name} exited {run.returncode}; "
        f"stderr={run.stderr[-500:]!r}"
    )
    return run.stdout, run.stderr


def _assert_parity(
    tmp_path: Path, name: str, program: str, out: bytes, err: bytes
) -> None:
    got = {c: _run(c, tmp_path, name, program) for c in COMPILERS}
    for c in COMPILERS:
        # Literal pins first: they name the right answer, not just agreement.
        assert got[c][0] == out, f"{c} stdout for {name}: {got[c][0]!r}"
        assert got[c][1] == err, f"{c} stderr for {name}: {got[c][1]!r}"


# ---------------------------------------------------------------------------
# eprint: same lowering as print, fd 2.
# ---------------------------------------------------------------------------

EPRINT_SCALARS = """\
fn twice(n: i64) -> i64
    return n * 2

pub fn main() -> i32
    let x: i64 = -21
    let b: i32 = 7
    let t: bool = true
    let s: *u8 = c"cs"
    eprint("x={x} b={b} t={t} cmp={x > 0} call={twice(x)} s={s}\\n")
    eprint("plain\\n")
    return 0
"""


def test_eprint_scalars_go_to_stderr_only(tmp_path):
    _assert_parity(
        tmp_path,
        "eprint_scalars",
        EPRINT_SCALARS,
        b"",
        b"x=-21 b=7 t=true cmp=false call=-42 s=cs\nplain\n",
    )


INTERLEAVED = """\
pub fn main() -> i32
    let n: i64 = 3
    print("out {n}\\n")
    eprint("err {n}\\n")
    print("out2\\n")
    eprint("err2 {{n}}\\n")
    return 0
"""


def test_print_and_eprint_keep_their_streams(tmp_path):
    _assert_parity(
        tmp_path, "interleaved", INTERLEAVED, b"out 3\nout2\n", b"err 3\nerr2 {n}\n"
    )


EPRINT_RETURN = """\
pub fn main() -> i32
    let n: i64 = eprint("abcd\\n")
    if n != 5
        return 1
    eprint(c"cstr ok\\n")
    return 0
"""


def test_eprint_plain_returns_byte_count_and_accepts_cstring(tmp_path):
    _assert_parity(tmp_path, "eprint_ret", EPRINT_RETURN, b"", b"abcd\ncstr ok\n")


# ---------------------------------------------------------------------------
# StrView placeholders, in print and eprint.
# ---------------------------------------------------------------------------

STRVIEW = """\
import ritzlib.strview

struct Opt
    name: StrView
    n: i64

fn pick(i: i64) -> StrView
    if i > 0
        return "yes"
    return "no"

fn by_param(v: StrView)
    print("param=[{v}]\\n")

fn by_ref(v: @StrView)
    print("ref=[{v}]\\n")

pub fn main() -> i32
    let v: StrView = "view"
    # A view of 2 bytes onto a longer NUL-terminated buffer: prints exactly
    # 2 bytes, so the printer uses len, not strlen.
    let part: StrView = StrView { ptr: c"hello", len: 2 }
    let empty: StrView = StrView { ptr: c"zzz", len: 0 }
    let o: Opt = Opt { name: "opt", n: 1 }
    print("local=[{v}] part=[{part}] empty=[{empty}]\\n")
    print("call=[{pick(1)}],[{pick(0)}] field=[{o.name}]\\n")
    by_param(v)
    by_ref(@v)
    eprint("option '{v}' needs a value ({part})\\n")
    return 0
"""


def test_strview_placeholders_print_len_bytes(tmp_path):
    _assert_parity(
        tmp_path,
        "strview",
        STRVIEW,
        b"local=[view] part=[he] empty=[]\ncall=[yes],[no] field=[opt]\n"
        b"param=[view]\nref=[view]\n",
        b"option 'view' needs a value (he)\n",
    )


# String (string_as_view) is covered by the matrix file
# ritz0/test/test_eprint_interpolation.ritz: it needs ritzlib.string linked,
# which this single-file harness does not do.


# ---------------------------------------------------------------------------
# Fail closed, as print does.
# ---------------------------------------------------------------------------

REJECT = {
    # #1394 mirrored: c"..." does not interpolate.
    "eprint_cstring": ('let x: i64 = 1\n    eprint(c"c={x}\\n")', "eprint("),
    "eprint_empty": ('eprint("e={}\\n")', "eprint("),
    "eprint_float": ('let f: f64 = 1.5\n    eprint("f={f}\\n")', "eprint("),
}


@pytest.mark.parametrize("case", sorted(REJECT))
def test_eprint_rejects_what_print_rejects(tmp_path, case):
    body, marker = REJECT[case]
    program = "pub fn main() -> i32\n    " + body + "\n    return 0\n"
    for compiler in COMPILERS:
        comp, _ = _compile(compiler, tmp_path, f"reject_{case}", program)
        assert comp.returncode != 0, (
            f"{compiler} accepted {case}:\n{comp.stdout[-1000:]}\n{comp.stderr[-1000:]}"
        )
        if compiler == "ritz1":
            line = next(
                i for i, text in enumerate(program.splitlines(), 1) if marker in text
            )
            assert f"line {line}" in comp.stderr, comp.stderr


def test_eprint_cstring_rejection_names_the_fix(tmp_path):
    program = 'pub fn main() -> i32\n    let x: i64 = 1\n    eprint(c"c={x}\\n")\n    return 0\n'
    for compiler in COMPILERS:
        comp, _ = _compile(compiler, tmp_path, "reject_msg", program)
        assert "do not interpolate" in comp.stdout + comp.stderr, (compiler, comp.stderr)
