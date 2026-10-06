"""AGAST #1521: ritz1 lowers `print("x={x}\\n")` interpolation exactly as ritz0 does.

THE DEFECT

    pub fn main() -> i32
        let x: i64 = 5
        print("x={x}\\n")
        return 0

ritz0 prints `x=5`. ritz1 printed `x={x}` and exited 0: its print builtin wrote
the literal's bytes verbatim. It also printed `{{` as two braces where ritz0
prints one, and printed `print(c"c={x}")` verbatim where ritz0 rejects it
with a located diagnostic (#1394).

THE FIX (ritz1/src/interp.ritz + the print builtin in emitter_expr_call.ritz)

The print builtin re-reads the literal's RAW source text (the cooked text
cannot tell `\\{x}` from `{x}`) and splits it with ritz0's lexer rule
(lexer.py `_lex_string`): `{` opens a placeholder only when a matching `}`
follows before the closing quote; `{{` / `}}` print one brace; `\\{` / `\\}`
are literal braces. Each placeholder is lexed and parsed with ritz1's own
lexer and `parse_expr`, then printed by type, as ritz0's
`_emit_print_value` does: integers in decimal, bool as true/false, and
pointers as NUL-terminated strings. Anything else is a compile error, as it
is in ritz0. The lowering takes the output fd as a parameter (1 for print),
so #1641's `eprint` only adds a name.

ORACLE

Every program is compiled by ritz0 and by ritz1. Both binaries must exit 0
and print byte-identical stdout, and that stdout is also pinned to a literal
expected string, so a bug both compilers share cannot pass either.
"""

import os
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import RITZ0, RITZ1_BIN, RITZ_ROOT, RITZ_START
from test_ritz1_builtin_struct_shadow import ritz1_bin  # noqa: F401

# Build ritz1 (and the runtime start object) once for the module.
pytestmark = pytest.mark.usefixtures("ritz1_bin")


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


def _stdout(compiler: str, tmp_path: Path, name: str, program: str) -> bytes:
    """Compile, link, run; return stdout bytes. Asserts every step succeeds."""
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
    assert run.returncode == 0, f"{compiler} binary for {name} exited {run.returncode}"
    return run.stdout


def _assert_parity(tmp_path: Path, name: str, program: str, expected: bytes) -> None:
    out0 = _stdout("ritz0", tmp_path, name, program)
    out1 = _stdout("ritz1", tmp_path, name, program)
    # The literal pin first: it names the right answer, not just agreement.
    assert out0 == expected, f"ritz0 oracle drifted for {name}: {out0!r}"
    assert out1 == expected, f"ritz1 printed {out1!r}, ritz0 printed {out0!r}"


# The ticket's repro.
REPRO = """\
pub fn main() -> i32
    let x: i64 = 5
    print("x={x}\\n")
    return 0
"""

# One value of each printable type, via locals.
TYPES = """\
pub fn main() -> i32
    let a: i64 = -1234567
    let z: i64 = 0
    let b: i32 = -42
    let c: i8 = -7
    let d: u8 = 65
    let e: i16 = 300
    let f: u32 = 7
    let t: bool = true
    let g: bool = false
    let s: *u8 = c"cstr"
    print("a={a} z={z} b={b} c={c} d={d} e={e} f={f}\\n")
    print("t={t} g={g} s={s}\\n")
    return 0
"""

# Placeholders hold expressions, not just names (LANGUAGE_SPEC, #1374).
EXPRS = """\
struct P
    x: i64
    y: i32

fn twice(n: i64) -> i64
    return n * 2

fn is_big(n: i64) -> bool
    return n > 10

fn name() -> *u8
    return c"ritz"

fn show(flag: bool, n: i64) -> i64
    # Bool locals live in i64 slots; parameters and fields load an i1.
    let big: bool = n > 1
    print("param={flag} not={not (n > 5)} and={big and n > 1}\\n")
    return n

pub fn main() -> i32
    let x: i64 = 21
    var p: P = P { x: 3, y: -4 }
    print("call={twice(x)} sum={x + 1} cmp={x > 3} bool_fn={is_big(x)}\\n")
    print("member={p.x},{p.y} ptr_fn={name()} spaced={ x }\\n")
    show(true, 2)
    return 0
"""

# The splitting rules, each from ritz0's lexer.
SPLIT = """\
pub fn main() -> i32
    let x: i64 = 9
    let y: i64 = 8
    print("{x}\\n")
    print("{x}{y}\\n")
    print("pre {x} mid {y} post\\n")
    print("dbl {{x}} close }} open {{\\n")
    print("esc \\{x\\}\\n")
    print("lone { brace\\n")
    print("lone } brace\\n")
    print("json {\\"k\\": {x}}\\n")
    print("tab\\there\\n")
    return 0
"""

# print with no placeholder keeps working, and its return value is still the
# write(2) byte count.
PLAIN = """\
pub fn main() -> i32
    let n: i64 = print("hello\\n")
    if n != 6
        return 1
    print(c"cstr plain\\n")
    return 0
"""


def test_repro_interpolates(tmp_path):
    _assert_parity(tmp_path, "repro", REPRO, b"x=5\n")


def test_each_type_prints_like_ritz0(tmp_path):
    _assert_parity(
        tmp_path,
        "types",
        TYPES,
        b"a=-1234567 z=0 b=-42 c=-7 d=65 e=300 f=7\nt=true g=false s=cstr\n",
    )


def test_placeholder_expressions(tmp_path):
    _assert_parity(
        tmp_path,
        "exprs",
        EXPRS,
        b"call=42 sum=22 cmp=true bool_fn=true\nmember=3,-4 ptr_fn=ritz spaced=21\n"
        b"param=true not=true and=true\n",
    )


def test_splitting_rules_match_ritz0_lexer(tmp_path):
    _assert_parity(
        tmp_path,
        "split",
        SPLIT,
        b"9\n98\npre 9 mid 8 post\ndbl {x} close } open {\nesc {x}\n"
        b'lone { brace\nlone } brace\njson {"k": 9}\ntab\there\n',
    )


def test_plain_print_unchanged(tmp_path):
    _assert_parity(tmp_path, "plain", PLAIN, b"hello\ncstr plain\n")


# ---------------------------------------------------------------------------
# Fail closed: never print a placeholder verbatim.
# ---------------------------------------------------------------------------

REJECT = {
    # Same rule as ritz0 (#1394): c"..." does not interpolate, so passing one
    # with a placeholder to print is an error rather than verbatim output.
    "cstring": 'let x: i64 = 1\n    print(c"c={x}\\n")',
    # No printable form in ritz0's _emit_print_value. #1641 adds StrView.
    "float": 'let f: f64 = 1.5\n    print("f={f}\\n")',
    "strview": 'let v: StrView = "sv"\n    print("v={v}\\n")',
    "empty": 'print("e={}\\n")',
    "bad_expr": 'print("b={1 +}\\n")',
}


@pytest.mark.parametrize("case", sorted(REJECT))
def test_unprintable_is_a_compile_error_in_both(tmp_path, case):
    program = (
        "import ritzlib.strview\n\npub fn main() -> i32\n    "
        + REJECT[case]
        + "\n    return 0\n"
    )
    for compiler in ("ritz0", "ritz1"):
        comp, _ = _compile(compiler, tmp_path, f"reject_{case}", program)
        assert comp.returncode != 0, (
            f"{compiler} accepted unprintable interpolation ({case}):\n"
            f"{comp.stdout[-1000:]}\n{comp.stderr[-1000:]}"
        )
        if compiler == "ritz1":
            # Located: the diagnostic names the print literal's line.
            line = next(
                i for i, text in enumerate(program.splitlines(), 1) if "print(" in text
            )
            assert f"line {line}" in comp.stderr, comp.stderr


def test_cstring_braces_outside_print_stay_opaque(tmp_path):
    """The self-hosting guard from #1394: ritz1 emits inline-asm constraint
    strings like this one. Only print's lowering may look at braces."""
    program = """\
fn strlen(s: *u8) -> i64
    var i: i64 = 0
    while *(s + i) != 0
        i = i + 1
    i

pub fn main() -> i32
    let c: *u8 = c"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"
    if strlen(c) != 42
        return 1
    print("ok\\n")
    return 0
"""
    _assert_parity(tmp_path, "opaque", program, b"ok\n")


def test_bool_struct_field_and_array_element(tmp_path):
    """Bool fields (an i1 in memory, zext'd at the load since #1646) and
    `[N]bool` elements print as true/false, like `: bool` locals."""
    program = """\
struct F
    ok: bool
    n: i64

pub fn main() -> i32
    var f: F = F { ok: true, n: 1 }
    var arr: [2]bool
    arr[0] = false
    arr[1] = true
    print("field={f.ok} elem={arr[0]},{arr[1]}\\n")
    return 0
"""
    _assert_parity(tmp_path, "boolslots", program, b"field=true elem=false,true\n")


def test_unsigned_narrow_ints_print_as_ritz0_does(tmp_path):
    """ritz0 sign-extends every integer it prints, so a u8 holding 200 prints
    -56. That is ritz0's behaviour today, and ritz1 must print the same bytes.
    If unsigned printing is fixed, fix both compilers and this test together."""
    program = """\
pub fn main() -> i32
    let a: u8 = 200
    let b: u16 = 65535
    let c: u32 = 4294967295
    print("{a} {b} {c}\\n")
    return 0
"""
    _assert_parity(tmp_path, "unsigned", program, b"-56 -1 -1\n")


def test_interpolation_inside_a_generic_function(tmp_path):
    """Monomorphization clones the literal; the clone must keep the raw text."""
    program = """\
fn show<T>(v: T) -> T
    print("v={v}\\n")
    return v

pub fn main() -> i32
    let x: i64 = 7
    show<i64>(x)
    return 0
"""
    _assert_parity(tmp_path, "generic", program, b"v=7\n")


def test_inferred_bool_locals(tmp_path):
    """`let b = x > 1` has no annotation; ritz0 still types it bool."""
    program = """\
fn is_big(n: i64) -> bool
    return n > 10

pub fn main() -> i32
    let x: i64 = 5
    let b = x > 1
    let nb = not (x > 1)
    let both = x > 1 and x < 3
    let ok = is_big(x)
    print("b={b} nb={nb} both={both} ok={ok}\\n")
    return 0
"""
    _assert_parity(
        tmp_path, "inferred", program, b"b=true nb=false both=false ok=false\n"
    )
