"""`+`, `-` and `*` stop the program on overflow at their type (LARB R63:
ritz0 AGAST #3488, ritz1 and ritz1_selfhosted AGAST #3489).

    fn f(a: i8, b: i8) -> i32
        let r = a + b        # a stray 127 + 1 stops here

The rule (LANGUAGE_SPEC §7.1, §7.4):

- `+`, `-`, `*` stop the program on overflow at their type, after writing
  `<file>:<line>:<col>: integer overflow in `<op>`` to stderr and exiting 1;
- `+%`, `-%` and `*%` wrap, and `op=` follows its operator;
- signed `/` and `%` of the minimum by -1, division (or remainder) by zero,
  and a shift count outside `0..width-1` stop it too;
- overflow in a constant expression is a compile error;
- `as` still truncates, and bits shifted out by `<<` don't trap;
- a freestanding target stops through `ritz_platform_fatal`, not a syscall.

Every row runs on all three compilers, except the freestanding one: ritz1
has no freestanding target (no `--target`), so its traps always stop through
the exit syscall (AGAST #4607).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

pytestmark = [pytest.mark.integration]

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
# Build product, not a tracked file: ritz1's modules take `_start` from it.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
FILE = "main.ritz"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


@pytest.fixture(params=COMPILERS)
def compiler(request):
    if request.param != "ritz0":
        request.getfixturevalue("ritz1_bin")
    return request.param


def _compile(tmp_path, name, src, compiler):
    work = tmp_path / name
    work.mkdir()
    path = work / "main.ritz"
    path.write_text(src)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(path), "-o", str(ll)], cwd=work, env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        comp = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=work,
                              env=env, capture_output=True, text=True, timeout=300)
    return comp, ll, work


def _compile_run(tmp_path, name, src, compiler):
    comp, ll, work = _compile(tmp_path, name, src, compiler)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), \
        f"{compiler} refused {name}:\n{src}\n{out[-2000:]}"
    exe = work / "main"
    cmd = ["clang", "-Wno-override-module", str(ll), "-o", str(exe),
           "-nostdlib", "-no-pie"]
    if compiler != "ritz0":
        cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, f"clang refused {name}:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)


def test_a_freestanding_trap_calls_the_platform_hook(tmp_path):
    """A kernel has no exit syscall (AGAST #4119): the stop is the
    `ritz_platform_fatal` hook a kernel already defines, so its IR must hold
    no syscall at all."""
    path = tmp_path / "kernel.ritz"
    path.write_text("fn f(a: i64) -> i64\n    a + 1\n\n"
                    "pub fn kmain() -> i32\n    return f(0) as i32\n")
    out = tmp_path / "kernel.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = run_ritz0([str(path), "-o", str(out), "--no-runtime",
                      "--target", "x86_64-none-elf"],
                     cwd=tmp_path, env=env, timeout=300)
    assert comp.returncode == 0 and out.exists(), comp.stdout + comp.stderr
    ir = out.read_text()
    assert "syscall" not in ir, "a freestanding trap issued a syscall"
    assert "ritz_platform_fatal" in ir, "the trap did not reach the platform hook"


def _located(src):
    """`src` without its `^`, and where the `^` was as `line:col`."""
    before = src[:src.index("^")]
    line = before.count("\n") + 1
    return src.replace("^", "", 1), f"{FILE}:{line}:{len(before) - before.rfind(chr(10))}"


# --- every operator, both type classes --------------------------------------------

SIGNED = {
    "i8": (-128, 127),
    "i16": (-32768, 32767),
    "i32": (-2147483648, 2147483647),
    "i64": (-9223372036854775808, 9223372036854775807),
}
UNSIGNED = {
    "u8": (0, 255),
    "u16": (0, 65535),
    "u32": (0, 4294967295),
    "u64": (0, 18446744073709551615),
}


def _operand(ty):
    """`(a, b)` from `main` that is one past the edge for `op` at `ty`."""
    signed = ty in SIGNED
    lo, hi = SIGNED[ty] if signed else UNSIGNED[ty]
    return {
        "+": (hi, 1),
        "-": (lo, 1),
        "*": (hi, 2),
    }


def _trap_source(ty, op):
    a, b = _operand(ty)[op]
    return (f"fn f(a: {ty}, b: {ty}) -> i32\n"
            f"    let r = ^a {op} b\n"
            f"    r as i32\n"
            f"\npub fn main() -> i32\n"
            f"    f({a}, {b})\n")


TRAPS = {
    f"{ty}_{op}": (ty, op)
    for table in (SIGNED, UNSIGNED)
    for ty in table
    for op in ("+", "-", "*")
}


@pytest.mark.parametrize("name", sorted(TRAPS))
def test_arithmetic_overflow_stops_the_program(tmp_path, compiler, name):
    ty, op = TRAPS[name]
    marked = _trap_source(ty, op)
    src, where = _located(marked)
    got = _compile_run(tmp_path, name, src, compiler)
    assert got.returncode == 1, f"{name}: expected exit 1, got {got.returncode}\n{got.stderr}"
    want = f"{where}: integer overflow in `{op}`"
    assert want in got.stderr, f"{name}: wanted {want!r} in {got.stderr!r}"


# `op=` follows its operator: the same trap, same message.
@pytest.mark.parametrize("ty,op", [
    ("i8", "+"), ("u32", "-"), ("i64", "*"), ("u8", "*"),
])
def test_compound_assignment_traps_like_its_operator(tmp_path, compiler, ty, op):
    a, b = _operand(ty)[op]
    marked = (f"fn f(a: {ty}, b: {ty}) -> i32\n"
              f"    var r = a\n"
              f"    ^r {op}= b\n"
              f"    r as i32\n"
              f"\npub fn main() -> i32\n"
              f"    f({a}, {b})\n")
    src, where = _located(marked)
    got = _compile_run(tmp_path, f"{ty}_{op}_eq", src, compiler)
    assert got.returncode == 1, got.stderr
    assert f"{where}: integer overflow in `{op}`" in got.stderr, got.stderr


# --- a wider slot: the operation runs, and is checked, at the slot's type ---------

# name -> (operand type, slot type, expression, a, b, value); §7.1 "Wider slots".
WIDER = {
    "u32_mul_into_i64": ("u32", "i64", "a * b", 4294967295, 1000, 4294967295000),
    "u32_add_into_i64": ("u32", "i64", "a + b", 4294967295, 1, 4294967296),
    "u8_mul_into_u16": ("u8", "u16", "a * a", 200, 0, 40000),
    "i32_sub_into_i64": ("i32", "i64", "a - b", -2147483648, 1, -2147483649),
    # The count is checked against the slot's width too: 40 < 64.
    "u8_shl_into_i64": ("u8", "i64", "a << b", 1, 40, 1099511627776),
}


@pytest.mark.parametrize("name", sorted(WIDER))
def test_a_wider_slot_is_checked_at_its_type(tmp_path, compiler, name):
    ty, slot, expr, a, b, want = WIDER[name]
    src = (f"fn f(a: {ty}, b: {ty}) -> i32\n"
           f"    let r: {slot} = {expr}\n"
           f"    if r == {want}\n"
           f"        return 3\n"
           f"    return 4\n"
           f"\npub fn main() -> i32\n"
           f"    f({a}, {b})\n")
    got = _compile_run(tmp_path, name, src, compiler)
    assert got.returncode == 3, f"{name}: got {got.returncode}\n{got.stderr}"


def test_a_wider_slot_still_stops_outside_its_type(tmp_path, compiler):
    """255 * 255 * 255 is a u16 multiply in a u16 slot, and leaves u16."""
    marked = ("fn f(a: u8) -> i32\n"
              "    let r: u16 = ^a * a * a\n"
              "    r as i32\n"
              "\npub fn main() -> i32\n"
              "    f(255)\n")
    src, where = _located(marked)
    got = _compile_run(tmp_path, "u16_slot", src, compiler)
    assert got.returncode == 1, got.stderr
    assert f"{where}: integer overflow in `*`" in got.stderr, got.stderr


# --- wrapping operators stay wrapping ----------------------------------------------

def _wrap_source(ty, op, a, b):
    return (f"fn f(a: {ty}, b: {ty}) -> i32\n"
            f"    let r = a {op}% b\n"
            f"    if r == WANT\n"
            f"        return 3\n"
            f"    return 4\n"
            f"\npub fn main() -> i32\n"
            f"    f({a}, {b})\n")


WRAPS = {
    "i8_add": ("i8", "+", 127, 1, -128),
    "i8_sub": ("i8", "-", -128, 1, 127),
    "i8_mul": ("i8", "*", 127, 2, -2),
    "u8_add": ("u8", "+", 255, 1, 0),
    "u8_sub": ("u8", "-", 0, 1, 255),
    "u8_mul": ("u8", "*", 255, 2, 254),
    "i32_add": ("i32", "+", 2147483647, 1, -2147483648),
    "u32_mul": ("u32", "*", 4294967295, 2, 4294967294),
    "i64_sub": ("i64", "-", -9223372036854775808, 1, 9223372036854775807),
    "u64_add": ("u64", "+", 18446744073709551615, 1, 0),
    "u64_mul": ("u64", "*", 18446744073709551615, 2, 18446744073709551614),
}


@pytest.mark.parametrize("name", sorted(WRAPS))
def test_wrapping_operator_does_not_trap(tmp_path, compiler, name):
    ty, op, a, b, want = WRAPS[name]
    src = _wrap_source(ty, op, a, b).replace("WANT", str(want))
    assert _compile_run(tmp_path, name, src, compiler).returncode == 3


# --- division and remainder -------------------------------------------------------

DIV_TRAPS = {
    # The signed minimum by -1 overflows the type.
    "i8_div_min": ("i8", "/", -128, -1, "integer overflow in `/`"),
    "i8_rem_min": ("i8", "%", -128, -1, "integer overflow in `%`"),
    "i32_div_min": ("i32", "/", -2147483648, -1, "integer overflow in `/`"),
    "i64_rem_min": ("i64", "%", -9223372036854775808, -1, "integer overflow in `%`"),
    # Division and remainder by zero, signed and unsigned.
    "i32_div_zero": ("i32", "/", 7, 0, "division by zero in `/`"),
    "u32_div_zero": ("u32", "/", 7, 0, "division by zero in `/`"),
    "i64_rem_zero": ("i64", "%", 7, 0, "division by zero in `%`"),
    "u8_rem_zero": ("u8", "%", 7, 0, "division by zero in `%`"),
}


@pytest.mark.parametrize("name", sorted(DIV_TRAPS))
def test_division_traps(tmp_path, compiler, name):
    ty, op, a, b, message = DIV_TRAPS[name]
    marked = (f"fn f(a: {ty}, b: {ty}) -> i32\n"
              f"    let r = ^a {op} b\n"
              f"    r as i32\n"
              f"\npub fn main() -> i32\n"
              f"    f({a}, {b})\n")
    src, where = _located(marked)
    got = _compile_run(tmp_path, name, src, compiler)
    assert got.returncode == 1, f"{name}: got {got.returncode}\n{got.stderr}"
    assert f"{where}: {message}" in got.stderr, f"{name}: {got.stderr!r}"


def test_unsigned_division_by_minus_one_is_not_a_trap(tmp_path, compiler):
    """Only the signed minimum by -1 overflows; a unsigned wraps nothing."""
    src = ("fn f(a: u32) -> i32\n"
           "    let r = a / 4294967295\n"
           "    if r == 0\n"
           "        return 3\n"
           "    return 4\n"
           "\npub fn main() -> i32\n"
           "    f(7)\n")
    assert _compile_run(tmp_path, "u32_div", src, compiler).returncode == 3


# --- shifts: the count must be in 0..width-1 --------------------------------------

SHIFT_TRAPS = {
    "u8_shl_width": ("u8", "<<", 1, 8, 8),
    "u8_shr_width": ("u8", ">>", 255, 8, 8),
    "i32_shl_width": ("i32", "<<", 1, 32, 32),
    "i64_shr_width": ("i64", ">>", 1, 64, 64),
    "i32_shl_negative": ("i32", "<<", 1, -1, 32),
    "i64_shr_negative": ("i64", ">>", 1, -1, 64),
}


@pytest.mark.parametrize("name", sorted(SHIFT_TRAPS))
def test_shift_count_out_of_range_stops_the_program(tmp_path, compiler, name):
    ty, op, a, b, width = SHIFT_TRAPS[name]
    marked = (f"fn f(a: {ty}, b: {ty}) -> i32\n"
              f"    let r = ^a {op} b\n"
              f"    r as i32\n"
              f"\npub fn main() -> i32\n"
              f"    f({a}, {b})\n")
    src, where = _located(marked)
    got = _compile_run(tmp_path, name, src, compiler)
    assert got.returncode == 1, f"{name}: got {got.returncode}\n{got.stderr}"
    want = f"{where}: shift count out of range in `{op}`"
    assert want in got.stderr, f"{name}: {got.stderr!r}"


@pytest.mark.parametrize("ty,op,a,b,want", [
    ("u8", "<<", 1, 7, 128),          # the last valid count
    ("u8", ">>", 128, 7, 1),
    ("i32", "<<", 1, 31, -2147483648),
    ("i64", ">>", -8, 1, -4),
    # Bits shifted out by `<<` don't trap: 255 << 4 is 240 in a u8.
    ("u8", "<<", 255, 4, 240),
])
def test_shift_counts_inside_the_width_do_not_trap(tmp_path, compiler, ty, op, a, b, want):
    src = (f"fn f(a: {ty}, b: {ty}) -> i32\n"
           f"    let r = a {op} b\n"
           f"    if r == {want}\n"
           f"        return 3\n"
           f"    return 4\n"
           f"\npub fn main() -> i32\n"
           f"    f({a}, {b})\n")
    assert _compile_run(tmp_path, f"{ty}_{op}_{b}", src, compiler).returncode == 3


def test_a_cast_still_truncates(tmp_path, compiler):
    src = ("fn f(x: i64) -> i32\n"
           "    let y = x as i32\n"
           "    if y == 0\n"
           "        return 3\n"
           "    return 4\n"
           "\npub fn main() -> i32\n"
           "    f(4294967296)\n")
    assert _compile_run(tmp_path, "cast_truncates", src, compiler).returncode == 3


# --- constant expressions: overflow is a compile error ---------------------------

CONST_ERRORS = {
    # A constant expression, folded by the const evaluator (array size).
    "array_size": ("fn f() -> void\n    var buf: [9223372036854775807 + 1]u8\n"),
    # An all-literal operator in value position, outside i64.
    "literal_value": ("pub fn main() -> i32\n    let z = 9223372036854775807 + 1\n    0\n"),
    # A named const folded to an overflowing i64.
    "named_const": ("const MAXV: i64 = 9223372036854775807\n"
                    "const OVER: i64 = MAXV + 1\n"
                    "pub fn main() -> i32\n    0\n"),
}


@pytest.mark.parametrize("name", sorted(CONST_ERRORS))
def test_overflow_in_a_constant_expression_is_a_compile_error(tmp_path, compiler, name):
    comp, ll, _ = _compile(tmp_path, name, CONST_ERRORS[name], compiler)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} {name}: accepted a constant overflow:\n{out}"
    assert not ll.exists()
    assert re.search(r"integer overflow in `\+`", out), out
