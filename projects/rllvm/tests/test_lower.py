"""rllvm's -O0 lowering core against the rules in ../razm/DESIGN.md.

"Object contract": sections, symbols and COMDAT groups per linkage, and the
relocation set each profile writes. "ABI" (the parts this slice owns):
noredzone, naked, sspstrong. "LLVM IR subset", Instructions: one runnable
module exercises every core instruction on edge values, and its output and
status must match clang -O2's object for the same IR.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import corpus as c
from conftest import run

HEAD = 'target triple = "x86_64-unknown-linux-gnu"\n'


def compile_ll(rllvm_bin: str, tmp_path: Path, text: str, *flags: str,
               name: str = "m") -> Path:
    src = tmp_path / f"{name}.ll"
    src.write_text(HEAD + text)
    out = tmp_path / f"{name}.o"
    p = run([rllvm_bin, "-c", *flags, str(src), "-o", str(out)])
    assert p.returncode == 0, p.stderr
    return out


def readelf(*args) -> str:
    return subprocess.run(["readelf", "-W", *map(str, args)], capture_output=True,
                          text=True, check=True).stdout


def text_relocs(obj: Path) -> dict[str, set[int]]:
    """Relocation types in executable sections, by target symbol name."""
    out: dict[str, set[int]] = {}
    for r in c.read_elf(obj).relocs:
        if r.exec:
            out.setdefault(r.symbol.name, set()).add(r.type)
    return out


# --- relocation profiles (DESIGN "Relocations") ---------------------------

# External and internal data, an external and an internal call, and a pointer
# in a data initializer.
PROFILE_IR = """
@ext = external global i64
@mine = internal global i64 5
@ptrs = global [2 x ptr] [ptr @mine, ptr @ext]
declare i64 @far(i64)
define internal i64 @near(i64 %x) {
entry:
  ret i64 %x
}
define i64 @f() {
entry:
  %a = load i64, ptr @ext
  %b = load i64, ptr @mine
  %c = call i64 @far(i64 %a)
  %d = call i64 @near(i64 %b)
  %e = add i64 %c, %d
  ret i64 %e
}
"""

GOTX, PC32, PLT32, ABS64, S32 = (c.R_X86_64_REX_GOTPCRELX, c.R_X86_64_PC32,
                                 c.R_X86_64_PLT32, c.R_X86_64_64,
                                 c.R_X86_64_32S)


@pytest.mark.parametrize("flags, ext, internal, call", [
    (["-fPIC"], GOTX, PC32, PLT32),                     # small PIC
    ([], GOTX, PC32, PLT32),                            # small PIE
    (["-mcmodel=kernel"], GOTX, S32, PLT32),            # kernel
    (["-mcmodel=large"], ABS64, ABS64, ABS64),          # large
], ids=["small-pic", "small-pie", "kernel", "large"])
def test_profile_relocations(rllvm_bin, tmp_path, flags, ext, internal, call):
    obj = compile_ll(rllvm_bin, tmp_path, PROFILE_IR, *flags)
    relocs = text_relocs(obj)
    assert relocs["ext"] == {ext}
    assert relocs["far"] == {call}
    # @mine is local: its relocation goes through its section's symbol.
    assert relocs[".data"] == {internal}
    # A call into the same section needs none, except as the large model's
    # movabs of the address.
    assert ("near" in relocs or ".text" in relocs) == (call == ABS64)
    data = [r for r in c.read_elf(obj).relocs if not r.exec]
    assert {r.type for r in data} == {ABS64}, "pointers in data are R_X86_64_64"
    assert all(r.type != c.R_X86_64_32 for r in c.read_elf(obj).relocs)


# --- sections, symbols and COMDAT (DESIGN "Sections", "Symbols") ----------

LINKAGE_IR = """
$odr = comdat any
$wodr = comdat any
declare void @ext_fn()
define linkonce_odr i64 @odr(i64 %x) comdat {
entry:
  call void @ext_fn()
  ret i64 %x
}
define weak_odr i64 @wodr(i64 %x) comdat {
entry:
  call void @ext_fn()
  ret i64 %x
}
define weak void @soft() {
entry:
  ret void
}
define available_externally i64 @elsewhere() {
entry:
  ret i64 1
}
define internal i64 @hidden() {
entry:
  ret i64 2
}
@wg = weak_odr global i64 3
@cst = private constant [3 x i8] c"ab\\00"
@zero = global i64 0
define i64 @user() {
entry:
  %a = call i64 @odr(i64 1)
  %b = call i64 @wodr(i64 %a)
  call void @soft()
  %c = call i64 @elsewhere()
  %d = call i64 @hidden()
  %e = load i64, ptr @wg
  %f = load i8, ptr @cst
  %g = load i64, ptr @zero
  ret i64 %b
}
"""


@pytest.fixture
def linkage_obj(rllvm_bin, tmp_path) -> Path:
    return compile_ll(rllvm_bin, tmp_path, LINKAGE_IR, "-fPIC")


def symbol_line(syms: str, name: str) -> str:
    lines = [ln for ln in syms.splitlines() if ln.split()[-1:] == [name]]
    assert len(lines) == 1, f"{name}: {lines}"
    return lines[0]


def test_comdat_function_has_its_own_section_and_group(linkage_obj):
    groups = readelf("-g", linkage_obj)
    for name in ("odr", "wodr"):
        assert f"COMDAT group section [" in groups
        assert f"[{name}] contains" in groups, groups
        block = groups.split(f"[{name}] contains")[1].split("COMDAT")[0]
        assert f".text.{name}" in block and f".rela.text.{name}" in block
    sections = readelf("-S", linkage_obj)
    assert " .text.odr " in sections and " AXG " in sections


def test_symbols_follow_the_linkage_table(linkage_obj):
    syms = readelf("-s", linkage_obj)
    assert " WEAK " in symbol_line(syms, "odr")
    assert " WEAK " in symbol_line(syms, "wodr")
    assert " WEAK " in symbol_line(syms, "wg")
    soft = symbol_line(syms, "soft")
    assert " WEAK " in soft and " FUNC " in soft
    assert " LOCAL " in symbol_line(syms, "hidden")
    assert " GLOBAL " in symbol_line(syms, "user")
    # available_externally: no body, and the reference is undefined.
    assert " UND " in symbol_line(syms, "elsewhere")


def test_weak_without_comdat_stays_out_of_any_group(linkage_obj):
    groups = readelf("-g", linkage_obj)
    assert "[soft]" not in groups
    assert groups.count("COMDAT group section") == 2


def test_globals_go_to_data_rodata_and_bss(linkage_obj):
    syms = readelf("-s", linkage_obj)
    sections = readelf("-S", linkage_obj)

    def section_of(name: str) -> str:
        ndx = symbol_line(syms, name).split()[6]
        for ln in sections.splitlines():
            if ln.strip().startswith(f"[{ndx:>2}]") or ln.strip().startswith(f"[ {ndx}]"):
                return ln.split("]")[1].split()[0]
        raise AssertionError(f"no section {ndx}")

    assert section_of("wg") == ".data"
    assert section_of("cst") == ".rodata"
    assert section_of("zero") == ".bss"


# --- frames (DESIGN "ABI") ------------------------------------------------

def disassembly(obj: Path) -> str:
    return subprocess.run(["objdump", "-d", "--no-show-raw-insn", str(obj)],
                          capture_output=True, text=True, check=True).stdout


def function_body(dis: str, name: str) -> list[str]:
    body = dis.split(f"<{name}>:\n")[1].split("\n\n")[0]
    return [ln.split("\t", 1)[1].strip() for ln in body.splitlines() if "\t" in ln]


def test_sspstrong_checks_the_guard(rllvm_bin, tmp_path):
    obj = compile_ll(rllvm_bin, tmp_path, """
define i64 @guarded(i64 %x) sspstrong noredzone {
entry:
  %a = alloca [16 x i8]
  ret i64 %x
}
define i64 @plain(i64 %x) {
entry:
  ret i64 %x
}
""", "-mcmodel=kernel")
    assert {"__stack_chk_guard", "__stack_chk_fail"} <= c.read_elf(obj).undefined()
    dis = disassembly(obj)
    assert any("__stack_chk_fail" in ln or "call" in ln
               for ln in function_body(dis, "guarded"))
    assert not any("call" in ln for ln in function_body(dis, "plain"))


def test_noredzone_never_addresses_below_rsp(rllvm_bin, tmp_path):
    obj = compile_ll(rllvm_bin, tmp_path, """
declare i64 @g(i64, i64, i64, i64, i64, i64, i64, i64)
define i64 @f(i64 %x) noredzone {
entry:
  %a = alloca [64 x i8]
  %r = call i64 @g(i64 %x, i64 1, i64 2, i64 3, i64 4, i64 5, i64 6, i64 7)
  ret i64 %r
}
""")
    for ln in function_body(disassembly(obj), "f"):
        assert "-0x" not in ln or "(%rsp)" not in ln, ln


def test_naked_function_has_no_prologue(rllvm_bin, tmp_path):
    obj = compile_ll(rllvm_bin, tmp_path, """
define void @entry() naked {
entry:
  call void asm sideeffect "movq $$60, %rax\\0Asyscall", "~{rax}"()
  unreachable
}
""")
    body = function_body(disassembly(obj), "entry")
    assert body[0].startswith("mov") and "$0x3c" in body[0], body
    assert body[1] == "syscall"


# --- core instructions, run against clang ---------------------------------

# Every core instruction, on edge values where the width matters. main
# prints each result with rt_hex and returns a status computed from them.
CORE_IR = r"""
%Pair = type { i32, i64 }
%Quad = type { i64, i64, i64, i64 }
%Nest = type { i8, %Pair, [3 x i16] }

declare void @rt_hex(...)

@table = internal global [4 x i32] [i32 10, i32 -20, i32 30, i32 -40]
@pair_ptr = internal global ptr getelementptr (%Nest, ptr @nest, i64 0, i32 1)
@nest = internal global %Nest { i8 -1, %Pair { i32 7, i64 -9 }, [3 x i16] [i16 1, i16 -2, i16 3] }
@bytes = internal constant [4 x i8] c"\01\80\FF\7F"

define internal i64 @narrow(i8 %a, i8 %b, i16 %c, i32 %d) {
entry:
  %q = sdiv i8 %a, %b
  %r = srem i8 %a, %b
  %u = udiv i8 %a, %b
  %v = urem i8 %a, %b
  %s = ashr i16 %c, 3
  %l = lshr i16 %c, 3
  %m = mul i32 %d, %d
  %q64 = sext i8 %q to i64
  %r64 = sext i8 %r to i64
  %u64 = zext i8 %u to i64
  %v64 = zext i8 %v to i64
  %s64 = sext i16 %s to i64
  %l64 = zext i16 %l to i64
  %m64 = sext i32 %m to i64
  %x1 = shl i64 %q64, 56
  %x2 = shl i64 %r64, 48
  %x3 = shl i64 %u64, 40
  %x4 = shl i64 %v64, 32
  %x5 = shl i64 %s64, 16
  %y1 = xor i64 %x1, %x2
  %y2 = xor i64 %y1, %x3
  %y3 = xor i64 %y2, %x4
  %y4 = xor i64 %y3, %x5
  %y5 = xor i64 %y4, %l64
  %y6 = add i64 %y5, %m64
  ret i64 %y6
}

define internal i1 @less(i32 %a, i32 %b, i1 %signed) {
entry:
  %s = icmp slt i32 %a, %b
  %u = icmp ult i32 %a, %b
  %r = select i1 %signed, i1 %s, i1 %u
  ret i1 %r
}

define internal %Quad @quad(i64 %a) {
entry:
  %q0 = insertvalue %Quad undef, i64 %a, 0
  %b = add i64 %a, 1
  %q1 = insertvalue %Quad %q0, i64 %b, 1
  %c = sub i64 0, %a
  %q2 = insertvalue %Quad %q1, i64 %c, 2
  %q3 = insertvalue %Quad %q2, i64 -1, 3
  ret %Quad %q3
}

define internal { i64, i8, ptr } @triple(i64 %a) {
entry:
  %t0 = insertvalue { i64, i8, ptr } zeroinitializer, i64 %a, 0
  %t1 = insertvalue { i64, i8, ptr } %t0, i8 -3, 1
  %t2 = insertvalue { i64, i8, ptr } %t1, ptr @table, 2
  ret { i64, i8, ptr } %t2
}

define internal i64 @many(i64 %a, i64 %b, i64 %c, i64 %d, i64 %e, i64 %f, i64 %g, i32 %h, i8 %i) {
entry:
  %1 = mul i64 %a, 3
  %2 = add i64 %1, %b
  %3 = mul i64 %2, 3
  %4 = add i64 %3, %c
  %5 = mul i64 %4, 3
  %6 = add i64 %5, %d
  %7 = mul i64 %6, 3
  %8 = add i64 %7, %e
  %9 = mul i64 %8, 3
  %10 = add i64 %9, %f
  %11 = mul i64 %10, 3
  %12 = add i64 %11, %g
  %13 = sext i32 %h to i64
  %14 = mul i64 %12, 3
  %15 = add i64 %14, %13
  %16 = zext i8 %i to i64
  %17 = mul i64 %15, 3
  %18 = add i64 %17, %16
  ret i64 %18
}

define internal i64 @pick(%Pair %p, i1 %first) {
entry:
  %other = insertvalue %Pair %p, i32 99, 0
  %s = select i1 %first, %Pair %p, %Pair %other
  %a = extractvalue %Pair %s, 0
  %b = extractvalue %Pair %s, 1
  %a64 = sext i32 %a to i64
  %r = add i64 %a64, %b
  ret i64 %r
}

; Fibonacci, and a pair of phis that swap: each round reads the old values.
define internal i64 @fib(i64 %n) {
entry:
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %i1, %loop ]
  %a = phi i64 [ 0, %entry ], [ %b, %loop ]
  %b = phi i64 [ 1, %entry ], [ %sum, %loop ]
  %x = phi i64 [ 1, %entry ], [ %y, %loop ]
  %y = phi i64 [ 2, %entry ], [ %x, %loop ]
  %sum = add i64 %a, %b
  %i1 = add i64 %i, 1
  %done = icmp eq i64 %i1, %n
  br i1 %done, label %exit, label %loop
exit:
  %r = phi i64 [ %a, %loop ]
  %xs = shl i64 %x, 40
  %ys = shl i64 %y, 36
  %r1 = add i64 %r, %xs
  %r2 = add i64 %r1, %ys
  ret i64 %r2
}

; Placeholders at each width, $$, and %rbx (callee-saved) as an output.
define internal i64 @asm_ops(i64 %x, i32 %y) {
entry:
  %a = call i64 asm sideeffect "movq ${1}, $0\0Aaddq $$1, $0", "={rax},{rcx}"(i64 %x)
  %b = call i32 asm sideeffect "movl $1, $0\0Ashll $$4, $0", "={ebx},{edx},~{memory}"(i32 %y)
  %bx = zext i32 %b to i64
  %r = add i64 %a, %bx
  ret i64 %r
}

define internal i64 @fold(ptr %fn, i64 %x) {
entry:
  %r = call i64 %fn(i64 %x)
  ret i64 %r
}

define internal i64 @twice(i64 %x) {
entry:
  %r = shl i64 %x, 1
  ret i64 %r
}

define i32 @main() {
entry:
  %n1 = call i64 @narrow(i8 -128, i8 3, i16 -32768, i32 65537)
  call void (...) @rt_hex(i64 %n1)
  %n2 = call i64 @narrow(i8 127, i8 -7, i16 32767, i32 -1)
  call void (...) @rt_hex(i64 %n2)

  %l1 = call i1 @less(i32 -1, i32 1, i1 true)
  %l2 = call i1 @less(i32 -1, i32 1, i1 false)
  %l1x = zext i1 %l1 to i64
  %l2x = zext i1 %l2 to i64
  %l2s = shl i64 %l2x, 4
  %ls = or i64 %l1x, %l2s
  call void (...) @rt_hex(i64 %ls)

  %q = call %Quad @quad(i64 41)
  %q0 = extractvalue %Quad %q, 0
  %q1 = extractvalue %Quad %q, 1
  %q2 = extractvalue %Quad %q, 2
  %q3 = extractvalue %Quad %q, 3
  call void (...) @rt_hex(i64 %q0)
  call void (...) @rt_hex(i64 %q1)
  call void (...) @rt_hex(i64 %q2)
  call void (...) @rt_hex(i64 %q3)

  %t = call { i64, i8, ptr } @triple(i64 5)
  %t0 = extractvalue { i64, i8, ptr } %t, 0
  %t1 = extractvalue { i64, i8, ptr } %t, 1
  %t2 = extractvalue { i64, i8, ptr } %t, 2
  %t1x = sext i8 %t1 to i64
  %t2p = getelementptr [4 x i32], ptr %t2, i64 0, i64 3
  %t2v = load i32, ptr %t2p
  %t2x = sext i32 %t2v to i64
  call void (...) @rt_hex(i64 %t0)
  call void (...) @rt_hex(i64 %t1x)
  call void (...) @rt_hex(i64 %t2x)

  %m = call i64 @many(i64 1, i64 2, i64 3, i64 4, i64 5, i64 6, i64 7, i32 -8, i8 255)
  call void (...) @rt_hex(i64 %m)

  %p0 = insertvalue %Pair undef, i32 -5, 0
  %p1 = insertvalue %Pair %p0, i64 100, 1
  %k1 = call i64 @pick(%Pair %p1, i1 true)
  %k2 = call i64 @pick(%Pair %p1, i1 false)
  call void (...) @rt_hex(i64 %k1)
  call void (...) @rt_hex(i64 %k2)

  %f = call i64 @fib(i64 50)
  call void (...) @rt_hex(i64 %f)

  ; memory: GEP through a nested struct, a negative index, volatile access
  %pp = load ptr, ptr @pair_ptr
  %pf = getelementptr %Pair, ptr %pp, i32 0, i32 1
  %pv = load i64, ptr %pf
  call void (...) @rt_hex(i64 %pv)
  %arr = getelementptr %Nest, ptr @nest, i64 0, i32 2, i64 2
  %back = getelementptr i16, ptr %arr, i64 -1
  %bv = load volatile i16, ptr %back
  %bvx = sext i16 %bv to i64
  call void (...) @rt_hex(i64 %bvx)
  %slot = alloca %Nest
  %whole = load %Nest, ptr @nest
  store volatile %Nest %whole, ptr %slot
  %sb = getelementptr %Nest, ptr %slot, i64 0, i32 0
  %sbv = load i8, ptr %sb
  %sbx = zext i8 %sbv to i64
  call void (...) @rt_hex(i64 %sbx)
  %te = getelementptr [4 x i32], ptr @table, i64 0, i64 1
  store i32 12345, ptr %te
  %tv = load i32, ptr %te
  %tvx = zext i32 %tv to i64
  call void (...) @rt_hex(i64 %tvx)
  %by = getelementptr [4 x i8], ptr @bytes, i64 0, i64 1
  %byv = load i8, ptr %by
  %byx = sext i8 %byv to i64
  call void (...) @rt_hex(i64 %byx)

  ; casts
  %ip = ptrtoint ptr @table to i64
  %pi = inttoptr i64 %ip to ptr
  %same = icmp eq ptr %pi, @table
  %samex = zext i1 %same to i64
  call void (...) @rt_hex(i64 %samex)
  %tr = trunc i64 -2 to i1
  %trx = sext i1 %tr to i64
  call void (...) @rt_hex(i64 %trx)
  %bc = bitcast i64 81985529216486895 to i64
  %bct = trunc i64 %bc to i16
  %bcx = zext i16 %bct to i64
  call void (...) @rt_hex(i64 %bcx)

  %ao = call i64 @asm_ops(i64 41, i32 3)
  call void (...) @rt_hex(i64 %ao)

  %ind = call i64 @fold(ptr @twice, i64 21)
  call void (...) @rt_hex(i64 %ind)

  %st = trunc i64 %ind to i32
  ret i32 %st
}
"""


# Float, SSE2 vector and atomic lowering (DESIGN "LLVM IR subset",
# Instructions: Float, the vector types, atomics; AGAST #4805). Defined
# values only, no poison: every operand is picked so the result does not
# depend on anything DESIGN leaves unspecified (an undef byte, a division
# whose divisor could be zero).
FLOAT_VECTOR_ATOMIC_IR = r"""
declare void @rt_hex(...)

define i32 @main() {
entry:
  %a = fadd double 0.0, 3.5
  %b = fadd double 0.0, -3.5
  %nan = fdiv double 0.0, 0.0

  %p1 = fcmp oeq double %a, %a
  %p2 = fcmp one double %a, %b
  %p3 = fcmp olt double %b, %a
  %p4 = fcmp ogt double %a, %b
  %p5 = fcmp ole double %a, %a
  %p6 = fcmp oge double %a, %a
  %p7 = fcmp ueq double %a, %nan
  %p8 = fcmp une double %a, %nan
  %p9 = fcmp uno double %a, %nan
  %p10 = fcmp ord double %a, %a
  %p11 = fcmp ult double %nan, %a
  %p12 = fcmp ule double %nan, %a
  %p13 = fcmp ugt double %nan, %a
  %p14 = fcmp uge double %nan, %a
  %p15 = fcmp false double %a, %a
  %p16 = fcmp true double %a, %a

  %z1 = zext i1 %p1 to i64
  %z2 = zext i1 %p2 to i64
  %z3 = zext i1 %p3 to i64
  %z4 = zext i1 %p4 to i64
  %z5 = zext i1 %p5 to i64
  %z6 = zext i1 %p6 to i64
  %z7 = zext i1 %p7 to i64
  %z8 = zext i1 %p8 to i64
  %z9 = zext i1 %p9 to i64
  %z10 = zext i1 %p10 to i64
  %z11 = zext i1 %p11 to i64
  %z12 = zext i1 %p12 to i64
  %z13 = zext i1 %p13 to i64
  %z14 = zext i1 %p14 to i64
  %z15 = zext i1 %p15 to i64
  %z16 = zext i1 %p16 to i64

  %s1 = shl i64 %z1, 15
  %s2 = shl i64 %z2, 14
  %s3 = shl i64 %z3, 13
  %s4 = shl i64 %z4, 12
  %s5 = shl i64 %z5, 11
  %s6 = shl i64 %z6, 10
  %s7 = shl i64 %z7, 9
  %s8 = shl i64 %z8, 8
  %s9 = shl i64 %z9, 7
  %s10 = shl i64 %z10, 6
  %s11 = shl i64 %z11, 5
  %s12 = shl i64 %z12, 4
  %s13 = shl i64 %z13, 3
  %s14 = shl i64 %z14, 2
  %s15 = shl i64 %z15, 1
  %o1 = or i64 %s1, %s2
  %o2 = or i64 %o1, %s3
  %o3 = or i64 %o2, %s4
  %o4 = or i64 %o3, %s5
  %o5 = or i64 %o4, %s6
  %o6 = or i64 %o5, %s7
  %o7 = or i64 %o6, %s8
  %o8 = or i64 %o7, %s9
  %o9 = or i64 %o8, %s10
  %o10 = or i64 %o9, %s11
  %o11 = or i64 %o10, %s12
  %o12 = or i64 %o11, %s13
  %o13 = or i64 %o12, %s14
  %o14 = or i64 %o13, %s15
  %o15 = or i64 %o14, %z16
  call void (...) @rt_hex(i64 %o15)

  %f32 = fptrunc double %a to float
  %back = fpext float %f32 to double
  %bits32 = bitcast float %f32 to i32
  %bits32x = zext i32 %bits32 to i64
  call void (...) @rt_hex(i64 %bits32x)

  %i = sitofp i32 -7 to double
  %ibits = bitcast double %i to i64
  call void (...) @rt_hex(i64 %ibits)
  %u = uitofp i32 300 to double
  %ubits = bitcast double %u to i64
  call void (...) @rt_hex(i64 %ubits)
  %t = fptosi double %back to i64
  call void (...) @rt_hex(i64 %t)

  %pa = alloca <4 x i32>
  %pb = alloca <4 x i32>
  store <4 x i32> <i32 10, i32 -20, i32 30, i32 -40>, ptr %pa
  store <4 x i32> <i32 1, i32 2, i32 3, i32 4>, ptr %pb
  %va = load <4 x i32>, ptr %pa
  %vb = load <4 x i32>, ptr %pb

  %add = add <4 x i32> %va, %vb
  %sub = sub <4 x i32> %va, %vb
  %mul = mul <4 x i32> %va, %vb
  %and = and <4 x i32> %va, %vb
  %or = or <4 x i32> %va, %vb
  %xor = xor <4 x i32> %va, %vb
  %shl = shl <4 x i32> %va, <i32 1, i32 2, i32 3, i32 4>
  %lshr = lshr <4 x i32> %va, <i32 1, i32 1, i32 1, i32 1>
  %ashr = ashr <4 x i32> %va, <i32 1, i32 1, i32 1, i32 1>
  %sdiv = sdiv <4 x i32> %va, <i32 3, i32 3, i32 3, i32 3>
  %udiv = udiv <4 x i32> %va, <i32 3, i32 3, i32 3, i32 3>
  %srem = srem <4 x i32> %va, <i32 3, i32 3, i32 3, i32 3>

  %e0 = extractelement <4 x i32> %add, i32 0
  %e1 = extractelement <4 x i32> %sub, i32 1
  %e2 = extractelement <4 x i32> %mul, i32 2
  %e3 = extractelement <4 x i32> %and, i32 3
  %e4 = extractelement <4 x i32> %or, i32 0
  %e5 = extractelement <4 x i32> %xor, i32 1
  %e6 = extractelement <4 x i32> %shl, i32 0
  %e7 = extractelement <4 x i32> %shl, i32 3
  %e8 = extractelement <4 x i32> %lshr, i32 1
  %e9 = extractelement <4 x i32> %ashr, i32 1
  %e10 = extractelement <4 x i32> %sdiv, i32 1
  %e11 = extractelement <4 x i32> %udiv, i32 1
  %e12 = extractelement <4 x i32> %srem, i32 1

  %x0 = sext i32 %e0 to i64
  %x1 = sext i32 %e1 to i64
  %x2 = sext i32 %e2 to i64
  %x3 = sext i32 %e3 to i64
  %x4 = sext i32 %e4 to i64
  %x5 = sext i32 %e5 to i64
  %x6 = sext i32 %e6 to i64
  %x7 = sext i32 %e7 to i64
  %x8 = sext i32 %e8 to i64
  %x9 = sext i32 %e9 to i64
  %x10 = sext i32 %e10 to i64
  %x11 = sext i32 %e11 to i64
  %x12 = sext i32 %e12 to i64

  call void (...) @rt_hex(i64 %x0)
  call void (...) @rt_hex(i64 %x1)
  call void (...) @rt_hex(i64 %x2)
  call void (...) @rt_hex(i64 %x3)
  call void (...) @rt_hex(i64 %x4)
  call void (...) @rt_hex(i64 %x5)
  call void (...) @rt_hex(i64 %x6)
  call void (...) @rt_hex(i64 %x7)
  call void (...) @rt_hex(i64 %x8)
  call void (...) @rt_hex(i64 %x9)
  call void (...) @rt_hex(i64 %x10)
  call void (...) @rt_hex(i64 %x11)
  call void (...) @rt_hex(i64 %x12)

  ; icmp on vectors, insertelement, shufflevector.
  %eq = icmp eq <4 x i32> %va, <i32 10, i32 0, i32 30, i32 0>
  %gt = icmp sgt <4 x i32> %va, %vb
  %eq0 = extractelement <4 x i1> %eq, i32 0
  %eq1 = extractelement <4 x i1> %eq, i32 1
  %gt0 = extractelement <4 x i1> %gt, i32 0
  %eq0x = zext i1 %eq0 to i64
  %eq1x = zext i1 %eq1 to i64
  %gt0x = zext i1 %gt0 to i64
  call void (...) @rt_hex(i64 %eq0x)
  call void (...) @rt_hex(i64 %eq1x)
  call void (...) @rt_hex(i64 %gt0x)

  %ins = insertelement <4 x i32> %va, i32 999, i32 2
  %insx = extractelement <4 x i32> %ins, i32 2
  %insxx = sext i32 %insx to i64
  call void (...) @rt_hex(i64 %insxx)

  %shuf = shufflevector <4 x i32> %va, <4 x i32> %vb, <4 x i32> <i32 0, i32 4, i32 1, i32 5>
  %sh0 = extractelement <4 x i32> %shuf, i32 1
  %sh0x = sext i32 %sh0 to i64
  call void (...) @rt_hex(i64 %sh0x)

  ; <2 x i64>, including the compare SSE2 lacks.
  %pc = alloca <2 x i64>
  %pd = alloca <2 x i64>
  store <2 x i64> <i64 100, i64 -200>, ptr %pc
  store <2 x i64> <i64 100, i64 300>, ptr %pd
  %vc = load <2 x i64>, ptr %pc
  %vd = load <2 x i64>, ptr %pd
  %cadd = add <2 x i64> %vc, %vd
  %ceq = icmp eq <2 x i64> %vc, %vd
  %ceq0 = extractelement <2 x i1> %ceq, i32 0
  %ceq1 = extractelement <2 x i1> %ceq, i32 1
  %ceq0x = zext i1 %ceq0 to i64
  %ceq1x = zext i1 %ceq1 to i64
  %ca0 = extractelement <2 x i64> %cadd, i32 0
  call void (...) @rt_hex(i64 %ceq0x)
  call void (...) @rt_hex(i64 %ceq1x)
  call void (...) @rt_hex(i64 %ca0)

  ; seq_cst load/store, cmpxchg (success and failure), the six atomicrmw
  ; ops, and fence.
  %p = alloca i64
  store i64 42, ptr %p

  %ld = load atomic i64, ptr %p seq_cst, align 8
  call void (...) @rt_hex(i64 %ld)

  store atomic i64 100, ptr %p seq_cst, align 8
  %ld2 = load i64, ptr %p
  call void (...) @rt_hex(i64 %ld2)

  %cx1 = cmpxchg ptr %p, i64 100, i64 200 seq_cst seq_cst, align 8
  %cx1v = extractvalue { i64, i1 } %cx1, 0
  %cx1b = extractvalue { i64, i1 } %cx1, 1
  %cx1bx = zext i1 %cx1b to i64
  call void (...) @rt_hex(i64 %cx1v)
  call void (...) @rt_hex(i64 %cx1bx)

  %cx2 = cmpxchg ptr %p, i64 999, i64 300 seq_cst seq_cst, align 8
  %cx2v = extractvalue { i64, i1 } %cx2, 0
  %cx2b = extractvalue { i64, i1 } %cx2, 1
  %cx2bx = zext i1 %cx2b to i64
  call void (...) @rt_hex(i64 %cx2v)
  call void (...) @rt_hex(i64 %cx2bx)
  %ld3 = load i64, ptr %p
  call void (...) @rt_hex(i64 %ld3)

  %old_xchg = atomicrmw xchg ptr %p, i64 55 seq_cst
  call void (...) @rt_hex(i64 %old_xchg)
  %old_add = atomicrmw add ptr %p, i64 10 seq_cst
  call void (...) @rt_hex(i64 %old_add)
  %old_sub = atomicrmw sub ptr %p, i64 5 seq_cst
  call void (...) @rt_hex(i64 %old_sub)
  %old_and = atomicrmw and ptr %p, i64 15 seq_cst
  call void (...) @rt_hex(i64 %old_and)
  %old_or = atomicrmw or ptr %p, i64 128 seq_cst
  call void (...) @rt_hex(i64 %old_or)
  %old_xor = atomicrmw xor ptr %p, i64 255 seq_cst
  call void (...) @rt_hex(i64 %old_xor)
  %final = load i64, ptr %p
  call void (...) @rt_hex(i64 %final)

  fence seq_cst
  ret i32 0
}
"""


def test_float_vector_atomic_match_clang(rllvm_bin, tmp_path):
    src = tmp_path / "fva.ll"
    src.write_text(HEAD + FLOAT_VECTOR_ATOMIC_IR)
    shim = c.clang_compile(c.entry("hosted/shim.ll"), tmp_path / "shim.o")
    extra = c.assemble("hosted", tmp_path / "extra.o")
    results = []
    for tool in (["clang"], [rllvm_bin]):
        obj = tmp_path / f"fva.{Path(tool[0]).name}.o"
        p = run([*tool, *c.PROFILE_FLAGS["hosted"], str(src), "-o", str(obj)])
        assert p.returncode == 0, p.stderr
        assert c.check_relocations(obj, "hosted") == []
        exe = tmp_path / f"fva.{Path(tool[0]).name}"
        link = c.link_hosted([shim, obj, extra], exe)
        assert link.returncode == 0, link.stderr
        results.append(c.run(exe))
    oracle, ours = results
    assert oracle.status == 0 and oracle.stdout.count(b"\n") == 40
    assert ours == oracle


def test_core_instructions_match_clang(rllvm_bin, tmp_path):
    src = tmp_path / "core.ll"
    src.write_text(HEAD + CORE_IR)
    shim = c.clang_compile(c.entry("hosted/shim.ll"), tmp_path / "shim.o")
    extra = c.assemble("hosted", tmp_path / "extra.o")
    results = []
    for tool in (["clang"], [rllvm_bin]):
        obj = tmp_path / f"core.{Path(tool[0]).name}.o"
        p = run([*tool, *c.PROFILE_FLAGS["hosted"], str(src), "-o", str(obj)])
        assert p.returncode == 0, p.stderr
        assert c.check_relocations(obj, "hosted") == []
        exe = tmp_path / f"core.{Path(tool[0]).name}"
        link = c.link_hosted([shim, obj, extra], exe)
        assert link.returncode == 0, link.stderr
        results.append(c.run(exe))
    oracle, ours = results
    assert oracle.status == 42 and oracle.stdout.count(b"\n") == 24
    assert ours == oracle


# --- constant getelementptr off null and off another GEP -----------------

# ritz1's sizeof/offsetof idiom, `ptrtoint (getelementptr (T, ptr null,
# ...))`, folds to an absolute integer: in an instruction operand, as a call
# argument, in data. A GEP whose base is itself a GEP off a global keeps the
# global's symbol with the summed addend. A ptrtoint to i32 truncates.
CONST_GEP_IR = r"""
%Pair = type { i32, i64 }
%Nest = type { i8, %Pair, [3 x i16] }

declare void @rt_hex(...)

@nest = internal global %Nest { i8 -1, %Pair { i32 7, i64 -9 }, [3 x i16] [i16 1, i16 -2, i16 3] }
@sizes = internal constant [3 x i64] [i64 ptrtoint (ptr getelementptr (%Nest, ptr null, i32 1) to i64), i64 ptrtoint (ptr getelementptr (%Nest, ptr null, i64 0, i32 2, i64 1) to i64), i64 ptrtoint (ptr getelementptr (i8, ptr null, i64 -3) to i64)]
@deep = internal global ptr getelementptr (i8, ptr getelementptr (%Nest, ptr @nest, i64 0, i32 1), i64 8)
@from_null = internal global ptr getelementptr (%Pair, ptr null, i64 3)
@abs_only = constant i64 ptrtoint (ptr getelementptr (%Nest, ptr null, i32 2) to i64)

define internal i64 @take(i64 %a, i32 %b) {
entry:
  %w = zext i32 %b to i64
  %s = shl i64 %w, 8
  %r = add i64 %a, %s
  ret i64 %r
}

define i32 @main() {
entry:
  %size = add i64 ptrtoint (ptr getelementptr (%Nest, ptr null, i32 1) to i64), 0
  call void (...) @rt_hex(i64 %size)
  %off = add i64 ptrtoint (ptr getelementptr (%Nest, ptr null, i64 0, i32 2, i64 1) to i64), 0
  call void (...) @rt_hex(i64 %off)
  %t = add i32 ptrtoint (ptr getelementptr (i8, ptr null, i64 -1) to i32), 0
  %t64 = zext i32 %t to i64
  call void (...) @rt_hex(i64 %t64)
  %arg = call i64 @take(i64 ptrtoint (ptr getelementptr (%Pair, ptr null, i32 1) to i64), i32 ptrtoint (ptr getelementptr (i8, ptr null, i64 5) to i32))
  call void (...) @rt_hex(i64 %arg)
  %p = getelementptr i8, ptr getelementptr (%Nest, ptr @nest, i64 0, i32 1), i64 8
  %deep_v = load i64, ptr getelementptr (i8, ptr getelementptr (%Nest, ptr @nest, i64 0, i32 1), i64 8)
  call void (...) @rt_hex(i64 %deep_v)
  %dp = load ptr, ptr @deep
  %same = icmp eq ptr %dp, getelementptr (%Nest, ptr @nest, i64 0, i32 1, i32 1)
  %same64 = zext i1 %same to i64
  call void (...) @rt_hex(i64 %same64)
  %np = load ptr, ptr @from_null
  %npi = ptrtoint ptr %np to i64
  call void (...) @rt_hex(i64 %npi)
  %nullp = icmp eq ptr getelementptr (i8, ptr null, i64 0), null
  %nullp64 = zext i1 %nullp to i64
  call void (...) @rt_hex(i64 %nullp64)
  %sum = alloca i64
  store i64 0, ptr %sum
  br label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %i1, %loop ]
  %ep = getelementptr [3 x i64], ptr @sizes, i64 0, i64 %i
  %e = load i64, ptr %ep
  call void (...) @rt_hex(i64 %e)
  %i1 = add i64 %i, 1
  %more = icmp ult i64 %i1, 3
  br i1 %more, label %loop, label %done
done:
  %a = load i64, ptr @abs_only
  call void (...) @rt_hex(i64 %a)
  %st = trunc i64 %a to i32
  ret i32 %st
}
"""


def test_constant_gep_off_null_and_nested_match_clang(rllvm_bin, tmp_path):
    src = tmp_path / "cgep.ll"
    src.write_text(HEAD + CONST_GEP_IR)
    shim = c.clang_compile(c.entry("hosted/shim.ll"), tmp_path / "shim.o")
    extra = c.assemble("hosted", tmp_path / "extra.o")
    results = []
    for tool in (["clang"], [rllvm_bin]):
        obj = tmp_path / f"cgep.{Path(tool[0]).name}.o"
        p = run([*tool, *c.PROFILE_FLAGS["hosted"], str(src), "-o", str(obj)])
        assert p.returncode == 0, p.stderr
        assert c.check_relocations(obj, "hosted") == []
        exe = tmp_path / f"cgep.{Path(tool[0]).name}"
        link = c.link_hosted([shim, obj, extra], exe)
        assert link.returncode == 0, link.stderr
        results.append(c.run(exe))
    oracle, ours = results
    assert oracle.status == 64 and oracle.stdout.count(b"\n") == 12
    assert ours == oracle


def test_constant_gep_off_null_carries_no_relocation(rllvm_bin, tmp_path):
    obj = compile_ll(rllvm_bin, tmp_path, CONST_GEP_IR)
    syms = readelf("-s", obj)
    sections = readelf("-S", obj)
    # A constant with no symbol in it is read-only data, as clang places it.
    ndx = symbol_line(syms, "abs_only").split()[6]
    assert f"[{int(ndx):2}] .rodata" in sections
    relocs = {r.symbol.name for r in c.read_elf(obj).relocs}
    assert "" not in relocs and None not in relocs


# --- extractelement / insertelement at a runtime index --------------------

# The index comes from a call, so it is never a constant. Every lane of an
# <8 x i32>, a <2 x i64> and a <16 x i8> is read back after an insert at a
# runtime lane; the index is in range (out of range is poison).
VAR_LANE_IR = r"""
declare void @rt_hex(...)

define internal i32 @id(i32 %x) noinline {
entry:
  ret i32 %x
}

define i32 @main() {
entry:
  %v8 = insertelement <8 x i32> <i32 10, i32 11, i32 12, i32 13, i32 14, i32 15, i32 16, i32 17>, i32 -1, i32 0
  %vq = insertelement <2 x i64> <i64 1, i64 2>, i64 3, i32 1
  %vb = insertelement <16 x i8> zeroinitializer, i8 7, i32 15
  br label %loop
loop:
  %i = phi i32 [ 0, %entry ], [ %i1, %loop ]
  %acc = phi i64 [ 0, %entry ], [ %acc1, %loop ]
  %k = call i32 @id(i32 %i)
  %k8 = and i32 %k, 7
  %e = extractelement <8 x i32> %v8, i32 %k8
  %e64 = sext i32 %e to i64
  call void (...) @rt_hex(i64 %e64)
  %k2 = and i32 %k, 1
  %ins = insertelement <2 x i64> %vq, i64 -9, i32 %k2
  %f = extractelement <2 x i64> %ins, i32 %k2
  %g = extractelement <2 x i64> %ins, i64 1
  %fs = xor i64 %f, %g
  call void (...) @rt_hex(i64 %fs)
  %kb = mul i32 %k, 2
  %bi = insertelement <16 x i8> %vb, i8 -3, i32 %kb
  %b = extractelement <16 x i8> %bi, i32 %kb
  %b15 = extractelement <16 x i8> %bi, i32 15
  %b64 = zext i8 %b to i64
  %b1564 = zext i8 %b15 to i64
  %bs = shl i64 %b1564, 8
  %bo = or i64 %b64, %bs
  call void (...) @rt_hex(i64 %bo)
  %acc1 = add i64 %acc, %e64
  %i1 = add i32 %i, 1
  %more = icmp ult i32 %i1, 8
  br i1 %more, label %loop, label %done
done:
  %r = trunc i64 %acc1 to i32
  ret i32 %r
}
"""


def test_variable_lane_index_matches_clang(rllvm_bin, tmp_path):
    src = tmp_path / "lane.ll"
    src.write_text(HEAD + VAR_LANE_IR)
    shim = c.clang_compile(c.entry("hosted/shim.ll"), tmp_path / "shim.o")
    extra = c.assemble("hosted", tmp_path / "extra.o")
    results = []
    for tool in (["clang"], [rllvm_bin]):
        obj = tmp_path / f"lane.{Path(tool[0]).name}.o"
        p = run([*tool, *c.PROFILE_FLAGS["hosted"], str(src), "-o", str(obj)])
        assert p.returncode == 0, p.stderr
        exe = tmp_path / f"lane.{Path(tool[0]).name}"
        link = c.link_hosted([shim, obj, extra], exe)
        assert link.returncode == 0, link.stderr
        results.append(c.run(exe))
    oracle, ours = results
    assert oracle.status == (-1 + 11 + 12 + 13 + 14 + 15 + 16 + 17) & 0xFF
    assert oracle.stdout.count(b"\n") == 24
    assert ours == oracle
