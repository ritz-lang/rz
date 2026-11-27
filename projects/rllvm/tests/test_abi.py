"""rllvm's call ABI against clang's, both directions (../razm/DESIGN.md "ABI").

Two modules, `a` and `b`, are generated from one template: each defines the
same set of callees under its own prefix and a driver that calls the other's.
Every value crosses the boundary in the class the rule names: integers,
floats, 128-bit vectors, aggregates of them that straddle registers and the
stack, x87 returns, demoted returns, byval at align 8 and 32, sret, variadic
%al, and %rsp alignment probed by a naked callee. Callees print what they
received and drivers print what came back, so the clang+clang binary is the
oracle and each rllvm+clang mix must print the same bytes.

The IR uses only what the call ABI moves: integer arithmetic and loads and
stores. A float or vector is made from integer bits through memory, and
printed the same way, so these tests do not wait on float or vector
arithmetic (#4805).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import corpus as c
from conftest import run

HEAD = 'target triple = "x86_64-unknown-linux-gnu"\n'

ONE = 0x3FF0000000000000        # double 1.0; +k is k ulps above it
F_ONE = 0x3F800000              # float 1.0

TYPES = """
%Two = type { i64, i64 }
%D2 = type { double, double }
%Pair = type { i32, i32 }
%Mixed = type { i8, i64, float }
%Three = type { i64, i64, i64 }
%Four = type { i64, i64, i64, i64 }
%D4 = type { double, double, double, double }
%D5 = type { double, double, double, double, double }
%FDF = type { float, double, float }
%DDDV = type { double, double, double, <4 x i32> }
%V4 = type { <4 x i32>, <4 x i32>, <4 x i32>, <4 x i32> }
%V5 = type { <4 x i32>, <4 x i32>, <4 x i32>, <4 x i32>, <4 x i32> }
%BHL = type { i8, i16, i32 }
%Big = type { i64, i64, i64 }
%Wide = type { i64, <4 x i32>, i64 }

declare void @rt_hex(...)
"""

# Printers and makers: a float or vector to and from integer bits through
# memory. Internal, so they are rllvm-to-rllvm calls in an rllvm object.
HELPERS = r"""
define internal void @PFX_hd(double %x) {
entry:
  %s = alloca double
  store double %x, ptr %s
  %b = load i64, ptr %s
  call void (...) @rt_hex(i64 %b)
  ret void
}

define internal void @PFX_hf(float %x) {
entry:
  %s = alloca float
  store float %x, ptr %s
  %b = load i32, ptr %s
  %z = zext i32 %b to i64
  call void (...) @rt_hex(i64 %z)
  ret void
}

define internal void @PFX_hv(<4 x i32> %x) {
entry:
  %s = alloca <4 x i32>
  store <4 x i32> %x, ptr %s
  %lo = load i64, ptr %s
  %hp = getelementptr i64, ptr %s, i64 1
  %hi = load i64, ptr %hp
  call void (...) @rt_hex(i64 %lo)
  call void (...) @rt_hex(i64 %hi)
  ret void
}

; A 32-aligned alloca, past %rbp's 16: its address mod 32 prints 0.
define internal void @PFX_h8(<8 x i32> %x) {
entry:
  %s = alloca <8 x i32>
  %pad = alloca i8
  %si = ptrtoint ptr %s to i64
  %sm = and i64 %si, 31
  call void (...) @rt_hex(i64 %sm)
  store <8 x i32> %x, ptr %s
  %p1 = getelementptr i64, ptr %s, i64 1
  %p2 = getelementptr i64, ptr %s, i64 2
  %p3 = getelementptr i64, ptr %s, i64 3
  %a = load i64, ptr %s
  %b = load i64, ptr %p1
  %c = load i64, ptr %p2
  %d = load i64, ptr %p3
  call void (...) @rt_hex(i64 %a)
  call void (...) @rt_hex(i64 %b)
  call void (...) @rt_hex(i64 %c)
  call void (...) @rt_hex(i64 %d)
  ret void
}

define internal double @PFX_d(i64 %b) {
entry:
  %s = alloca i64
  store i64 %b, ptr %s
  %x = load double, ptr %s
  ret double %x
}

define internal float @PFX_f(i32 %b) {
entry:
  %s = alloca i32
  store i32 %b, ptr %s
  %x = load float, ptr %s
  ret float %x
}

define internal <4 x i32> @PFX_v(i64 %lo, i64 %hi) {
entry:
  %s = alloca <4 x i32>
  store i64 %lo, ptr %s
  %hp = getelementptr i64, ptr %s, i64 1
  store i64 %hi, ptr %hp
  %x = load <4 x i32>, ptr %s
  ret <4 x i32> %x
}

define internal <8 x i32> @PFX_mk8(i64 %x) {
entry:
  %s = alloca [4 x i64]
  %p1 = getelementptr i64, ptr %s, i64 1
  %p2 = getelementptr i64, ptr %s, i64 2
  %p3 = getelementptr i64, ptr %s, i64 3
  %x1 = add i64 %x, 1
  %x2 = add i64 %x, 2
  %x3 = add i64 %x, 3
  store i64 %x, ptr %s
  store i64 %x1, ptr %p1
  store i64 %x2, ptr %p2
  store i64 %x3, ptr %p3
  %v = load <8 x i32>, ptr %s, align 8
  ret <8 x i32> %v
}

; 256-bit vectors between internal functions: ten halves, xmm0-7 then the
; stack, and a two-half return.
define internal <8 x i32> @PFX_w8(<8 x i32> %a, <8 x i32> %b, <8 x i32> %c, <8 x i32> %d, <8 x i32> %e) {
entry:
  call void @PFX_h8(<8 x i32> %a)
  call void @PFX_h8(<8 x i32> %d)
  call void @PFX_h8(<8 x i32> %e)
  ret <8 x i32> %b
}
"""

# The callees the other module's driver calls.
CALLEES = r"""
@PFX_seen_al = global i8 -1

define i64 @PFX_straddle_int(i64 %a, i64 %b, i64 %c, i64 %d, i64 %e, %Two %p) {
entry:
  call void (...) @rt_hex(i64 %e)
  %p0 = extractvalue %Two %p, 0
  %p1 = extractvalue %Two %p, 1
  call void (...) @rt_hex(i64 %p0)
  call void (...) @rt_hex(i64 %p1)
  %r = sub i64 %p1, %a
  ret i64 %r
}

define i64 @PFX_straddle_float(double %a, double %b, double %c, double %d, double %e, double %f, double %g, %D2 %p) {
entry:
  call void @PFX_hd(double %a)
  call void @PFX_hd(double %g)
  %p0 = extractvalue %D2 %p, 0
  %p1 = extractvalue %D2 %p, 1
  call void @PFX_hd(double %p0)
  call void @PFX_hd(double %p1)
  ret i64 9
}

; xmm0-7 full: a float at stack 0, a vector at 16 (not 8), a double at 32.
define i64 @PFX_vstack(double %a, double %b, double %c, double %d, double %e, double %f, double %g, double %h, float %s, <4 x i32> %v, double %t) {
entry:
  call void @PFX_hd(double %h)
  call void @PFX_hf(float %s)
  call void @PFX_hv(<4 x i32> %v)
  call void @PFX_hd(double %t)
  ret i64 10
}

define %Pair @PFX_pair(%Pair %p) {
entry:
  %x = extractvalue %Pair %p, 0
  %y = extractvalue %Pair %p, 1
  %xs = sext i32 %x to i64
  %ys = sext i32 %y to i64
  call void (...) @rt_hex(i64 %xs)
  call void (...) @rt_hex(i64 %ys)
  %q0 = insertvalue %Pair undef, i32 %y, 0
  %q1 = insertvalue %Pair %q0, i32 %x, 1
  ret %Pair %q1
}

define %Mixed @PFX_mixed(%Mixed %m) {
entry:
  %a = extractvalue %Mixed %m, 0
  %b = extractvalue %Mixed %m, 1
  %c = extractvalue %Mixed %m, 2
  %az = zext i8 %a to i64
  call void (...) @rt_hex(i64 %az)
  call void (...) @rt_hex(i64 %b)
  call void @PFX_hf(float %c)
  %a1 = add i8 %a, 1
  %b1 = add i64 %b, 1
  %r0 = insertvalue %Mixed %m, i8 %a1, 0
  %r1 = insertvalue %Mixed %r0, i64 %b1, 1
  ret %Mixed %r1
}

define %Three @PFX_three(i64 %x) {
entry:
  %x1 = add i64 %x, 1
  %x2 = add i64 %x, 2
  %r0 = insertvalue %Three undef, i64 %x, 0
  %r1 = insertvalue %Three %r0, i64 %x1, 1
  %r2 = insertvalue %Three %r1, i64 %x2, 2
  ret %Three %r2
}

define %D2 @PFX_d2(i64 %x) {
entry:
  %x1 = add i64 %x, 1
  %a = call double @PFX_d(i64 %x)
  %b = call double @PFX_d(i64 %x1)
  %r0 = insertvalue %D2 undef, double %a, 0
  %r1 = insertvalue %D2 %r0, double %b, 1
  ret %D2 %r1
}

; xmm0, xmm1, st0, st1.
define %D4 @PFX_d4(i64 %x) {
entry:
  %x1 = add i64 %x, 1
  %x2 = add i64 %x, 2
  %x3 = add i64 %x, 3
  %a = call double @PFX_d(i64 %x)
  %b = call double @PFX_d(i64 %x1)
  %c = call double @PFX_d(i64 %x2)
  %d = call double @PFX_d(i64 %x3)
  %r0 = insertvalue %D4 undef, double %a, 0
  %r1 = insertvalue %D4 %r0, double %b, 1
  %r2 = insertvalue %D4 %r1, double %c, 2
  %r3 = insertvalue %D4 %r2, double %d, 3
  ret %D4 %r3
}

; Five floats: demoted.
define %D5 @PFX_d5(i64 %x) {
entry:
  %x1 = add i64 %x, 1
  %x4 = add i64 %x, 4
  %a = call double @PFX_d(i64 %x)
  %b = call double @PFX_d(i64 %x1)
  %e = call double @PFX_d(i64 %x4)
  %r0 = insertvalue %D5 zeroinitializer, double %a, 0
  %r1 = insertvalue %D5 %r0, double %b, 1
  %r4 = insertvalue %D5 %r1, double %e, 4
  ret %D5 %r4
}

; xmm0, xmm1, then the second float to st0 (flds).
define %FDF @PFX_fdf(i32 %x, i64 %y) {
entry:
  %x1 = add i32 %x, 1
  %a = call float @PFX_f(i32 %x)
  %b = call double @PFX_d(i64 %y)
  %c = call float @PFX_f(i32 %x1)
  %r0 = insertvalue %FDF undef, float %a, 0
  %r1 = insertvalue %FDF %r0, double %b, 1
  %r2 = insertvalue %FDF %r1, float %c, 2
  ret %FDF %r2
}

; xmm0, xmm1, st0, and the vector in xmm2.
define %DDDV @PFX_dddv(i64 %x) {
entry:
  %x1 = add i64 %x, 1
  %x2 = add i64 %x, 2
  %a = call double @PFX_d(i64 %x)
  %b = call double @PFX_d(i64 %x1)
  %c = call double @PFX_d(i64 %x2)
  %v = call <4 x i32> @PFX_v(i64 7, i64 8)
  %r0 = insertvalue %DDDV undef, double %a, 0
  %r1 = insertvalue %DDDV %r0, double %b, 1
  %r2 = insertvalue %DDDV %r1, double %c, 2
  %r3 = insertvalue %DDDV %r2, <4 x i32> %v, 3
  ret %DDDV %r3
}

define %V4 @PFX_v4(i64 %x) {
entry:
  %x1 = add i64 %x, 1
  %x2 = add i64 %x, 2
  %x3 = add i64 %x, 3
  %a = call <4 x i32> @PFX_v(i64 %x, i64 %x1)
  %b = call <4 x i32> @PFX_v(i64 %x1, i64 %x2)
  %c = call <4 x i32> @PFX_v(i64 %x2, i64 %x3)
  %d = call <4 x i32> @PFX_v(i64 %x3, i64 %x)
  %r0 = insertvalue %V4 undef, <4 x i32> %a, 0
  %r1 = insertvalue %V4 %r0, <4 x i32> %b, 1
  %r2 = insertvalue %V4 %r1, <4 x i32> %c, 2
  %r3 = insertvalue %V4 %r2, <4 x i32> %d, 3
  ret %V4 %r3
}

; Five vectors: demoted.
define %V5 @PFX_v5(i64 %x) {
entry:
  %x1 = add i64 %x, 1
  %a = call <4 x i32> @PFX_v(i64 %x, i64 %x1)
  %e = call <4 x i32> @PFX_v(i64 %x1, i64 %x)
  %r0 = insertvalue %V5 zeroinitializer, <4 x i32> %a, 0
  %r4 = insertvalue %V5 %r0, <4 x i32> %e, 4
  ret %V5 %r4
}

; al, dx, ecx.
define %BHL @PFX_bhl(i64 %x) {
entry:
  %a = trunc i64 %x to i8
  %s = lshr i64 %x, 8
  %b = trunc i64 %s to i16
  %t = lshr i64 %x, 24
  %c = trunc i64 %t to i32
  %r0 = insertvalue %BHL undef, i8 %a, 0
  %r1 = insertvalue %BHL %r0, i16 %b, 1
  %r2 = insertvalue %BHL %r1, i32 %c, 2
  ret %BHL %r2
}

; Four integers: demoted, so the six arguments shift by one and %f is on
; the stack.
define %Four @PFX_four(i64 %a, i64 %b, i64 %c, i64 %d, i64 %e, i64 %f) {
entry:
  call void (...) @rt_hex(i64 %e)
  call void (...) @rt_hex(i64 %f)
  %ab = add i64 %a, %b
  %r0 = insertvalue %Four undef, i64 %ab, 0
  %r1 = insertvalue %Four %r0, i64 %c, 1
  %r2 = insertvalue %Four %r1, i64 %d, 2
  %r3 = insertvalue %Four %r2, i64 %f, 3
  ret %Four %r3
}

define i64 @PFX_small(i1 %a, i8 %b, i16 %c) {
entry:
  %a64 = zext i1 %a to i64
  %b64 = zext i8 %b to i64
  %c64 = zext i16 %c to i64
  %c1 = shl i64 %c64, 16
  %b1 = shl i64 %b64, 4
  %r0 = add i64 %a64, %b1
  %r1 = add i64 %r0, %c1
  ret i64 %r1
}

define i64 @PFX_big(ptr byval(%Big) align 8 %b, i64 %k) {
entry:
  %p1 = getelementptr %Big, ptr %b, i64 0, i32 1
  %p2 = getelementptr %Big, ptr %b, i64 0, i32 2
  %x0 = load i64, ptr %b
  %x1 = load i64, ptr %p1
  %x2 = load i64, ptr %p2
  call void (...) @rt_hex(i64 %x0)
  call void (...) @rt_hex(i64 %x1)
  call void (...) @rt_hex(i64 %x2)
  call void (...) @rt_hex(i64 %k)
  store i64 -1, ptr %b
  %s = add i64 %x0, %x2
  ret i64 %s
}

define i64 @PFX_wide(i64 %k, ptr byval(%Wide) align 32 %w) {
entry:
  %p1 = getelementptr %Wide, ptr %w, i64 0, i32 1
  %p2 = getelementptr %Wide, ptr %w, i64 0, i32 2
  %x0 = load i64, ptr %w
  %v = load <4 x i32>, ptr %p1
  %x2 = load i64, ptr %p2
  call void (...) @rt_hex(i64 %k)
  call void (...) @rt_hex(i64 %x0)
  call void @PFX_hv(<4 x i32> %v)
  ret i64 %x2
}

define void @PFX_sret(ptr sret(%Four) %r, i64 %x) {
entry:
  %p1 = getelementptr %Four, ptr %r, i64 0, i32 1
  %p2 = getelementptr %Four, ptr %r, i64 0, i32 2
  %p3 = getelementptr %Four, ptr %r, i64 0, i32 3
  %x1 = add i64 %x, 1
  %x2 = add i64 %x, 2
  %x3 = add i64 %x, 3
  store i64 %x, ptr %r
  store i64 %x1, ptr %p1
  store i64 %x2, ptr %p2
  store i64 %x3, ptr %p3
  ret void
}

; A variadic callee's view of %al.
define void @PFX_al_probe() naked noinline {
entry:
  call void asm sideeffect "movb %al, PFX_seen_al(%rip)\0Aretq", "~{memory}"()
  unreachable
}

; (%rsp + 8) mod 16 and mod 32 at entry: 0 when the caller aligned it.
define i64 @PFX_rsp16() naked noinline {
entry:
  call void asm sideeffect "leaq 8(%rsp), %rax\0Aandq $$15, %rax\0Aretq", "~{rax},~{memory}"()
  unreachable
}

define i64 @PFX_rsp32(ptr byval(%Wide) align 32 %w) naked noinline {
entry:
  call void asm sideeffect "leaq 8(%rsp), %rax\0Aandq $$31, %rax\0Aretq", "~{rax},~{memory}"()
  unreachable
}
"""

DECLARES = """
@OTH_seen_al = external global i8
declare i64 @OTH_straddle_int(i64, i64, i64, i64, i64, %Two)
declare i64 @OTH_straddle_float(double, double, double, double, double, double, double, %D2)
declare i64 @OTH_vstack(double, double, double, double, double, double, double, double, float, <4 x i32>, double)
declare %Pair @OTH_pair(%Pair)
declare %Mixed @OTH_mixed(%Mixed)
declare %Three @OTH_three(i64)
declare %D2 @OTH_d2(i64)
declare %D4 @OTH_d4(i64)
declare %D5 @OTH_d5(i64)
declare %FDF @OTH_fdf(i32, i64)
declare %DDDV @OTH_dddv(i64)
declare %V4 @OTH_v4(i64)
declare %V5 @OTH_v5(i64)
declare %BHL @OTH_bhl(i64)
declare %Four @OTH_four(i64, i64, i64, i64, i64, i64)
declare i64 @OTH_small(i1, i8, i16)
declare i64 @OTH_big(ptr byval(%Big) align 8, i64)
declare i64 @OTH_wide(i64, ptr byval(%Wide) align 32)
declare void @OTH_sret(ptr sret(%Four), i64)
declare void @OTH_al_probe(...)
declare i64 @OTH_rsp16(...)
declare i64 @OTH_rsp32(ptr byval(%Wide) align 32)
"""


def _driver() -> str:
    d = [ONE + k for k in range(10)]
    lines = ["define void @PFX_drive() {", "entry:"]
    add = lines.append

    def hex_(v):
        add(f"  call void (...) @rt_hex(i64 {v})")

    def fields(name, ty, n, printer):
        for i in range(n):
            add(f"  %{name}.{i} = extractvalue {ty} %{name}, {i}")
            printer(f"%{name}.{i}")

    def hd(v):
        add(f"  call void @PFX_hd(double {v})")

    def hf(v):
        add(f"  call void @PFX_hf(float {v})")

    def hv(v):
        add(f"  call void @PFX_hv(<4 x i32> {v})")

    # A constant aggregate straddling r9 and the stack.
    add("  %si = call i64 @OTH_straddle_int(i64 1, i64 2, i64 3, i64 4, i64 5, %Two { i64 6, i64 7 })")
    hex_("%si")
    for k in range(9):
        add(f"  %d{k} = call double @PFX_d(i64 {d[k]})")
    add("  %dp0 = insertvalue %D2 undef, double %d7, 0")
    add("  %dp1 = insertvalue %D2 %dp0, double %d8, 1")
    args = ", ".join(f"double %d{k}" for k in range(7))
    add(f"  %sf = call i64 @OTH_straddle_float({args}, %D2 %dp1)")
    hex_("%sf")
    add(f"  %vsf = call float @PFX_f(i32 {F_ONE + 3})")
    add("  %vsv = call <4 x i32> @PFX_v(i64 -2, i64 -3)")
    eight = ", ".join(f"double %d{k}" for k in range(8))
    add(f"  %vs = call i64 @OTH_vstack({eight}, float %vsf, <4 x i32> %vsv, double %d8)")
    hex_("%vs")
    add("  %pr = call %Pair @OTH_pair(%Pair { i32 -3, i32 4 })")
    for i in range(2):
        add(f"  %pr.{i} = extractvalue %Pair %pr, {i}")
        add(f"  %pr.{i}x = sext i32 %pr.{i} to i64")
        hex_(f"%pr.{i}x")
    add(f"  %fl = call float @PFX_f(i32 {F_ONE + 5})")
    add("  %m0 = insertvalue %Mixed undef, i8 -2, 0")
    add("  %m1 = insertvalue %Mixed %m0, i64 1311768467463790320, 1")
    add("  %m2 = insertvalue %Mixed %m1, float %fl, 2")
    add("  %mr = call %Mixed @OTH_mixed(%Mixed %m2)")
    add("  %mr.0 = extractvalue %Mixed %mr, 0")
    add("  %mr.0x = zext i8 %mr.0 to i64")
    hex_("%mr.0x")
    add("  %mr.1 = extractvalue %Mixed %mr, 1")
    hex_("%mr.1")
    add("  %mr.2 = extractvalue %Mixed %mr, 2")
    hf("%mr.2")
    add("  %t = call %Three @OTH_three(i64 100)")
    fields("t", "%Three", 3, hex_)
    add(f"  %dd = call %D2 @OTH_d2(i64 {ONE + 20})")
    fields("dd", "%D2", 2, hd)
    # Unused x87 returns: each call must pop both, or the ninth push faults
    # the x87 stack and the named call below reads garbage.
    for _ in range(5):
        add(f"  call %D4 @OTH_d4(i64 {ONE + 30})")
    add(f"  %q4 = call %D4 @OTH_d4(i64 {ONE + 40})")
    fields("q4", "%D4", 4, hd)
    add(f"  %fdf = call %FDF @OTH_fdf(i32 {F_ONE + 9}, i64 {ONE + 50})")
    add("  %fdf.0 = extractvalue %FDF %fdf, 0")
    hf("%fdf.0")
    add("  %fdf.1 = extractvalue %FDF %fdf, 1")
    hd("%fdf.1")
    add("  %fdf.2 = extractvalue %FDF %fdf, 2")
    hf("%fdf.2")
    add(f"  %dv = call %DDDV @OTH_dddv(i64 {ONE + 60})")
    for i in range(3):
        add(f"  %dv.{i} = extractvalue %DDDV %dv, {i}")
        hd(f"%dv.{i}")
    add("  %dv.3 = extractvalue %DDDV %dv, 3")
    hv("%dv.3")
    add("  %v4 = call %V4 @OTH_v4(i64 70)")
    fields("v4", "%V4", 4, hv)
    add("  %v5 = call %V5 @OTH_v5(i64 80)")
    fields("v5", "%V5", 5, hv)
    add("  call %V5 @OTH_v5(i64 90)")
    add(f"  %q5 = call %D5 @OTH_d5(i64 {ONE + 100})")
    fields("q5", "%D5", 5, hd)
    add("  %bhl = call %BHL @OTH_bhl(i64 1234605616436508552)")
    for i, w in enumerate(("i8", "i16", "i32")):
        add(f"  %bhl.{i} = extractvalue %BHL %bhl, {i}")
        add(f"  %bhl.{i}x = zext {w} %bhl.{i} to i64")
        hex_(f"%bhl.{i}x")
    add("  %fo = call %Four @OTH_four(i64 1, i64 2, i64 3, i64 4, i64 5, i64 6)")
    fields("fo", "%Four", 4, hex_)
    add("  call %Four @OTH_four(i64 11, i64 12, i64 13, i64 14, i64 15, i64 16)")
    add("  %sm = call i64 @OTH_small(i1 true, i8 -1, i16 -1)")
    hex_("%sm")
    # byval: the callee gets a copy, so its store does not reach ours.
    add("  %bg = alloca %Big")
    add("  %bg1 = getelementptr %Big, ptr %bg, i64 0, i32 1")
    add("  %bg2 = getelementptr %Big, ptr %bg, i64 0, i32 2")
    add("  store i64 21, ptr %bg")
    add("  store i64 22, ptr %bg1")
    add("  store i64 23, ptr %bg2")
    add("  %bgr = call i64 @OTH_big(ptr byval(%Big) align 8 %bg, i64 24)")
    hex_("%bgr")
    add("  %bg0 = load i64, ptr %bg")
    hex_("%bg0")
    add("  %wd = alloca %Wide")
    add("  %wd1 = getelementptr %Wide, ptr %wd, i64 0, i32 1")
    add("  %wd2 = getelementptr %Wide, ptr %wd, i64 0, i32 2")
    add("  %wv = call <4 x i32> @PFX_v(i64 31, i64 32)")
    add("  store i64 30, ptr %wd")
    add("  store <4 x i32> %wv, ptr %wd1")
    add("  store i64 33, ptr %wd2")
    add("  %wdr = call i64 @OTH_wide(i64 29, ptr byval(%Wide) align 32 %wd)")
    hex_("%wdr")
    add("  %sr = alloca %Four")
    add("  call void @OTH_sret(ptr sret(%Four) %sr, i64 50)")
    for i in range(4):
        add(f"  %sr{i} = getelementptr %Four, ptr %sr, i64 0, i32 {i}")
        add(f"  %sr{i}v = load i64, ptr %sr{i}")
        hex_(f"%sr{i}v")
    # %al: vector registers used by a variadic call.
    add("  %vv = call <4 x i32> @PFX_v(i64 1, i64 2)")
    calls = [
        "double %d0, <4 x i32> %vv, i64 3",
        "i64 1, i64 2",
        ", ".join(f"double %d{k}" for k in range(9)),
    ]
    for n, a in enumerate(calls):
        add(f"  call void (...) @OTH_al_probe({a})")
        add(f"  %al{n} = load i8, ptr @OTH_seen_al")
        add(f"  %al{n}x = zext i8 %al{n} to i64")
        hex_(f"%al{n}x")
    # %rsp at entry: no stack arguments, an odd count of them, a byval at 32.
    add("  %rs0 = call i64 (...) @OTH_rsp16()")
    hex_("%rs0")
    seven = ", ".join(f"i64 {k}" for k in range(7))
    add(f"  %rs1 = call i64 (...) @OTH_rsp16({seven})")
    hex_("%rs1")
    add("  %rs2 = call i64 @OTH_rsp32(ptr byval(%Wide) align 32 %wd)")
    hex_("%rs2")
    for k in range(5):
        add(f"  %w{k} = call <8 x i32> @PFX_mk8(i64 {k * 4 + 1})")
    wargs = ", ".join(f"<8 x i32> %w{k}" for k in range(5))
    add(f"  %wr = call <8 x i32> @PFX_w8({wargs})")
    add("  call void @PFX_h8(<8 x i32> %wr)")
    add("  ret void")
    add("}")
    return "\n".join(lines) + "\n"


MAIN = """
declare void @b_drive()
define i32 @main() {
entry:
  call void @a_drive()
  call void @b_drive()
  ret i32 0
}
"""


def module(side: str) -> str:
    other = "b" if side == "a" else "a"
    text = TYPES + HELPERS + CALLEES + DECLARES + _driver()
    if side == "a":
        text += MAIN
    return HEAD + text.replace("PFX_", f"{side}_").replace("OTH_", f"{other}_")


@pytest.fixture(scope="module")
def abi_pair(tmp_path_factory):
    root = tmp_path_factory.mktemp("abi")
    srcs = {}
    for side in "ab":
        srcs[side] = root / f"{side}.ll"
        srcs[side].write_text(module(side))
    shim = c.clang_compile(c.entry("hosted/shim.ll"), root / "shim.o")
    extra = c.assemble("hosted", root / "extra.o")
    return root, srcs, shim, extra


def _compile(tool: list[str], src: Path, out: Path) -> Path:
    p = run([*tool, *c.PROFILE_FLAGS["hosted"], str(src), "-o", str(out)])
    assert p.returncode == 0, f"{tool[0]} {src.name}: {p.stderr}"
    assert c.check_relocations(out, "hosted", c.asm_symbols(src)) == []
    return out


def _binary(abi_pair, rllvm_bin, rllvm_sides: str) -> c.RunResult:
    root, srcs, shim, extra = abi_pair
    objs = []
    for side in "ab":
        tool = [rllvm_bin] if side in rllvm_sides else ["clang"]
        tag = "rllvm" if side in rllvm_sides else "clang"
        objs.append(_compile(tool, srcs[side], root / f"{side}.{tag}.o"))
    exe = root / f"abi.{rllvm_sides or 'clang'}"
    link = c.link_hosted([shim, *objs, extra], exe)
    assert link.returncode == 0, link.stderr
    return c.run(exe)


@pytest.fixture(scope="module")
def oracle(abi_pair):
    return _binary(abi_pair, "", "")


def test_oracle_prints_every_case(oracle):
    assert oracle.status == 0
    lines = oracle.stdout.decode().split()
    half = len(lines) // 2
    assert len(lines) == 2 * half and half > 100
    # Each driver's sret fields, then %al for 2, 0 and 9 vector arguments
    # (capped at 8), then (%rsp + 8) mod 16, mod 16 and mod 32 at entry.
    probes = [f"{v:016x}" for v in (50, 51, 52, 53, 2, 0, 8, 0, 0, 0)]
    for side in (lines[:half], lines[half:]):
        text = " ".join(side)
        assert " ".join(probes) in text


@pytest.mark.parametrize("rllvm_sides", ["a", "b", "ab"])
def test_abi_matches_clang(abi_pair, oracle, rllvm_bin, rllvm_sides):
    assert _binary(abi_pair, rllvm_bin, rllvm_sides) == oracle


# --- what rllvm refuses (DESIGN "ABI", 256-bit vectors at a boundary) ------

REJECT = {
    "external definition": """
define <8 x i32> @f(<8 x i32> %x) {
entry:
  ret <8 x i32> %x
}
""",
    "aggregate in a declare": """
declare void @g({ i64, <4 x i64> })
""",
    "indirect call": """
define internal void @f(ptr %fp, ptr %p) {
entry:
  %v = load <8 x i32>, ptr %p, align 8
  call void %fp(<8 x i32> %v)
  ret void
}
""",
    "call to a declare": """
declare void @g(...)
define internal void @f(ptr %p) {
entry:
  %v = load <4 x i64>, ptr %p, align 8
  call void (...) @g(<4 x i64> %v)
  ret void
}
""",
    "win64cc definition": """
define win64cc void @f() {
entry:
  ret void
}
""",
    "win64cc call": """
declare void @g()
define void @f() {
entry:
  call win64cc void @g()
  ret void
}
""",
}


@pytest.mark.parametrize("case", REJECT)
def test_boundary_signatures_exit_2(rllvm_bin, tmp_path, case):
    src = tmp_path / "m.ll"
    src.write_text(HEAD + REJECT[case])
    p = run([rllvm_bin, "-c", str(src), "-o", str(tmp_path / "m.o")])
    assert p.returncode == 2, p.stderr
    assert ("256-bit" in p.stderr) != ("win64cc" in case), p.stderr


def test_internal_256_bit_signature_compiles(rllvm_bin, tmp_path):
    src = tmp_path / "m.ll"
    src.write_text(HEAD + """
define internal <8 x i32> @f(<8 x i32> %x) {
entry:
  ret <8 x i32> %x
}
define private void @g(ptr %p) {
entry:
  %v = load <8 x i32>, ptr %p, align 8
  %r = call <8 x i32> @f(<8 x i32> %v)
  store <8 x i32> %r, ptr %p, align 8
  ret void
}
""")
    p = run([rllvm_bin, "-c", str(src), "-o", str(tmp_path / "m.o")])
    assert p.returncode == 0, p.stderr


def test_sret_callee_returns_its_pointer_in_rax(rllvm_bin, tmp_path):
    # No caller in the run test reads %rax after an sret call, so the
    # disassembly is the check: the pointer is reloaded into %rax before ret.
    src = tmp_path / "m.ll"
    src.write_text(HEAD + """
define void @f(ptr sret({ i64, i64, i64, i64 }) %r, i64 %x) {
entry:
  store i64 %x, ptr %r
  ret void
}
""")
    obj = tmp_path / "m.o"
    p = run([rllvm_bin, "-c", str(src), "-o", str(obj)])
    assert p.returncode == 0, p.stderr
    dis = run(["objdump", "-d", "--no-show-raw-insn", str(obj)]).stdout
    body = [ln.split("\t", 1)[1].strip() for ln in dis.splitlines()
            if "\t" in ln and ":" in ln.split("\t", 1)[0]]
    ret = max(i for i, ins in enumerate(body) if ins.startswith("ret"))
    assert any(ins.startswith("mov") and ins.endswith(",%rax")
               for ins in body[ret - 4:ret]), body
