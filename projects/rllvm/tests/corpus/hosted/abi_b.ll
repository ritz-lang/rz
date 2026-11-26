; ModuleID = 'ritz1_output'
target triple = "x86_64-unknown-linux-gnu"

%Pair = type {i32, i32}
%Mixed = type {i8, i64, float}
%Two = type {i64, i64}
%Three = type {i64, i64, i64}
%Four = type {i64, i64, i64, i64}
%D2 = type {double, double}
%D3 = type {double, double, double}
%D4 = type {double, double, double, double}
%D5 = type {double, double, double, double, double}
%Big = type {[40 x i64]}
%Packed = type <{i8, i32, i16}>
%LanesB = type {i64}
%Span$u8 = type {ptr, i64}
%StrView = type {ptr, i64}
%V4 = type {<4 x i32>, <4 x i32>, <4 x i32>, <4 x i32>}
%V5 = type {<4 x i32>, <4 x i32>, <4 x i32>, <4 x i32>, <4 x i32>}
%BigWide = type {[40 x i64], <8 x i32>}





define void @say__08e0d8e3(%StrView %s.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca %StrView
  store %StrView %s.arg, ptr %.1
  %.2 = getelementptr %StrView, ptr %.1, i32 0, i32 0
  %.3 = load ptr, ptr %.2
  %.4 = ptrtoint ptr %.3 to i64
  %.5 = getelementptr %StrView, ptr %.1, i32 0, i32 1
  %.6 = load i64, ptr %.5
  %.7 = call i64 @rt_write(i64 %.4, i64 %.6)
  ret void
}

define i64 @bits64__08e0d8e3(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  %.2 = alloca double
  %.4 = alloca i64
  store double %x.arg, ptr %.1
  %.3 = load double, ptr %.1
  store double %.3, ptr %.2
  %.5 = ptrtoint ptr %.2 to i64
  store i64 %.5, ptr %.4
  %.6 = load i64, ptr %.4
  %.7 = inttoptr i64 %.6 to ptr
  %.8 = load i64, ptr %.7
  ret i64 %.8
}

define i64 @bits32__08e0d8e3(float %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca float
  %.2 = alloca float
  %.4 = alloca i64
  store float %x.arg, ptr %.1
  %.3 = load float, ptr %.1
  store float %.3, ptr %.2
  %.5 = ptrtoint ptr %.2 to i64
  store i64 %.5, ptr %.4
  %.6 = load i64, ptr %.4
  %.7 = inttoptr i64 %.6 to ptr
  %.8 = load i32, ptr %.7
  %.9 = zext i32 %.8 to i64
  %.10 = trunc i64 %.9 to i32
  %.11 = zext i32 %.10 to i64
  ret i64 %.11
}

define <4 x i32> @vec_of__08e0d8e3(i32 %base.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca [4 x i32]
  store i32 %base.arg, ptr %.1
  %.3 = load i32, ptr %.1
  %.4 = sext i32 %.3 to i64
  %.5 = getelementptr [4 x i32], ptr %.2, i64 0, i64 0
  %.6 = trunc i64 %.4 to i32
  store i32 %.6, ptr %.5
  %.7 = load i32, ptr %.1
  %.8 = sext i32 %.7 to i64
  %.9 = add i64 0, 1
  %.10 = trunc i64 %.8 to i32
  %.11 = trunc i64 %.9 to i32
  %.12 = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %.10, i32 %.11)
  %.13 = extractvalue { i32, i1 } %.12, 0
  %.14 = extractvalue { i32, i1 } %.12, 1
  br i1 %.14, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.0, i64 43)
  unreachable
L1:
  %.15 = sext i32 %.13 to i64
  %.16 = getelementptr [4 x i32], ptr %.2, i64 0, i64 1
  %.17 = trunc i64 %.15 to i32
  store i32 %.17, ptr %.16
  %.18 = load i32, ptr %.1
  %.19 = sext i32 %.18 to i64
  %.20 = add i64 0, 2
  %.21 = trunc i64 %.19 to i32
  %.22 = trunc i64 %.20 to i32
  %.23 = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %.21, i32 %.22)
  %.24 = extractvalue { i32, i1 } %.23, 0
  %.25 = extractvalue { i32, i1 } %.23, 1
  br i1 %.25, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.1, i64 43)
  unreachable
L3:
  %.26 = sext i32 %.24 to i64
  %.27 = getelementptr [4 x i32], ptr %.2, i64 0, i64 2
  %.28 = trunc i64 %.26 to i32
  store i32 %.28, ptr %.27
  %.29 = load i32, ptr %.1
  %.30 = sext i32 %.29 to i64
  %.31 = add i64 0, 3
  %.32 = trunc i64 %.30 to i32
  %.33 = trunc i64 %.31 to i32
  %.34 = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %.32, i32 %.33)
  %.35 = extractvalue { i32, i1 } %.34, 0
  %.36 = extractvalue { i32, i1 } %.34, 1
  br i1 %.36, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.2, i64 43)
  unreachable
L5:
  %.37 = sext i32 %.35 to i64
  %.38 = getelementptr [4 x i32], ptr %.2, i64 0, i64 3
  %.39 = trunc i64 %.37 to i32
  store i32 %.39, ptr %.38
  %.40 = add i64 0, 0
  %.41 = getelementptr [4 x i32], ptr %.2, i64 0, i64 %.40
  %.42 = ptrtoint ptr %.41 to i64
  %.43 = inttoptr i64 %.42 to ptr  ; simd_load: ptr cast
  %.44 = load <4 x i32>, ptr %.43, align 1
  ret <4 x i32> %.44
}

define i64 @vec_sum__08e0d8e3(<4 x i32> %v.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca <4 x i32>
  %.2 = alloca [4 x i32]
  store <4 x i32> %v.arg, ptr %.1
  call void @__ritz_sret_zero(ptr %.2, i64 16)
  %.3 = add i64 0, 0
  %.4 = getelementptr [4 x i32], ptr %.2, i64 0, i64 %.3
  %.5 = ptrtoint ptr %.4 to i64
  %.6 = load <4 x i32>, ptr %.1
  %.7 = inttoptr i64 %.5 to ptr  ; simd_store: ptr cast
  store <4 x i32> %.6, ptr %.7, align 1
  %.8 = add i64 0, 0  ; simd_store void
  %.9 = add i64 0, 0
  %.10 = getelementptr [4 x i32], ptr %.2, i64 0, i64 %.9
  %.11 = load i32, ptr %.10
  %.12 = sext i32 %.11 to i64
  %.13 = add i64 0, 1
  %.14 = getelementptr [4 x i32], ptr %.2, i64 0, i64 %.13
  %.15 = load i32, ptr %.14
  %.16 = sext i32 %.15 to i64
  %.17 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.12, i64 %.16)
  %.18 = extractvalue { i64, i1 } %.17, 0
  %.19 = extractvalue { i64, i1 } %.17, 1
  br i1 %.19, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.3, i64 42)
  unreachable
L1:
  %.20 = add i64 0, 2
  %.21 = getelementptr [4 x i32], ptr %.2, i64 0, i64 %.20
  %.22 = load i32, ptr %.21
  %.23 = sext i32 %.22 to i64
  %.24 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.18, i64 %.23)
  %.25 = extractvalue { i64, i1 } %.24, 0
  %.26 = extractvalue { i64, i1 } %.24, 1
  br i1 %.26, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.4, i64 42)
  unreachable
L3:
  %.27 = add i64 0, 3
  %.28 = getelementptr [4 x i32], ptr %.2, i64 0, i64 %.27
  %.29 = load i32, ptr %.28
  %.30 = sext i32 %.29 to i64
  %.31 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.25, i64 %.30)
  %.32 = extractvalue { i64, i1 } %.31, 0
  %.33 = extractvalue { i64, i1 } %.31, 1
  br i1 %.33, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.5, i64 42)
  unreachable
L5:
  ret i64 %.32
}

define i64 @entry_misalign() naked noinline {
entry:
  call void asm sideeffect "leaq 8(%rsp), %rax\0Aandq $$15, %rax\0Aretq", "~{rax},~{memory},~{dirflag},~{fpsr},~{flags}"()
  unreachable
}

define i64 @b_internal_wide() alignstack(16) "no-builtins" {
entry:
  %.1 = alloca %LanesB
  %.4 = alloca [8 x i32]
  %.29 = alloca <8 x i32>
  %.2 = add i64 0, 5
  %.3 = getelementptr %LanesB, ptr %.1, i32 0, i32 0
  store i64 %.2, ptr %.3
  %.5 = add i64 0, 3
  %.6 = getelementptr [8 x i32], ptr %.4, i64 0, i64 0
  %.7 = trunc i64 %.5 to i32
  store i32 %.7, ptr %.6
  %.8 = add i64 0, 3
  %.9 = getelementptr [8 x i32], ptr %.4, i64 0, i64 1
  %.10 = trunc i64 %.8 to i32
  store i32 %.10, ptr %.9
  %.11 = add i64 0, 3
  %.12 = getelementptr [8 x i32], ptr %.4, i64 0, i64 2
  %.13 = trunc i64 %.11 to i32
  store i32 %.13, ptr %.12
  %.14 = add i64 0, 3
  %.15 = getelementptr [8 x i32], ptr %.4, i64 0, i64 3
  %.16 = trunc i64 %.14 to i32
  store i32 %.16, ptr %.15
  %.17 = add i64 0, 3
  %.18 = getelementptr [8 x i32], ptr %.4, i64 0, i64 4
  %.19 = trunc i64 %.17 to i32
  store i32 %.19, ptr %.18
  %.20 = add i64 0, 3
  %.21 = getelementptr [8 x i32], ptr %.4, i64 0, i64 5
  %.22 = trunc i64 %.20 to i32
  store i32 %.22, ptr %.21
  %.23 = add i64 0, 3
  %.24 = getelementptr [8 x i32], ptr %.4, i64 0, i64 6
  %.25 = trunc i64 %.23 to i32
  store i32 %.25, ptr %.24
  %.26 = add i64 0, 4
  %.27 = getelementptr [8 x i32], ptr %.4, i64 0, i64 7
  %.28 = trunc i64 %.26 to i32
  store i32 %.28, ptr %.27
  %.30 = add i64 0, 0
  %.31 = getelementptr [8 x i32], ptr %.4, i64 0, i64 %.30
  %.32 = ptrtoint ptr %.31 to i64
  %.33 = inttoptr i64 %.32 to ptr  ; simd_load: ptr cast
  %.34 = load <8 x i32>, ptr %.33, align 1
  store <8 x i32> %.34, ptr %.29
  %.35 = load <8 x i32>, ptr %.29
  %.36 = call i64 @LanesB_bump(ptr %.1, <8 x i32> %.35)
  ret i64 %.36
}

define %Pair @b_pair(%Pair %p.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca %Pair
  %.19 = alloca %Pair
  store %Pair %p.arg, ptr %.1
  %.2 = getelementptr [8 x i8], ptr @.str.6, i64 0, i64 0
  %.3 = insertvalue %Span$u8 undef, ptr %.2, 0
  %.4 = insertvalue %Span$u8 %.3, i64 7, 1
  %.5 = extractvalue %Span$u8 %.4, 0
  %.6 = extractvalue %Span$u8 %.4, 1
  %.7 = insertvalue %StrView undef, ptr %.5, 0
  %.8 = insertvalue %StrView %.7, i64 %.6, 1
  call void @say__08e0d8e3(%StrView %.8)
  %.9 = getelementptr %Pair, ptr %.1, i32 0, i32 0
  %.10 = load i32, ptr %.9
  %.11 = sext i32 %.10 to i64
  %.12 = trunc i64 %.11 to i32
  %.13 = zext i32 %.12 to i64
  call void @rt_hex(i64 %.13)
  %.14 = getelementptr %Pair, ptr %.1, i32 0, i32 1
  %.15 = load i32, ptr %.14
  %.16 = sext i32 %.15 to i64
  %.17 = trunc i64 %.16 to i32
  %.18 = zext i32 %.17 to i64
  call void @rt_hex(i64 %.18)
  %.20 = getelementptr %Pair, ptr %.1, i32 0, i32 1
  %.21 = load i32, ptr %.20
  %.22 = sext i32 %.21 to i64
  %.23 = add i64 0, 10
  %.24 = trunc i64 %.22 to i32
  %.25 = trunc i64 %.23 to i32
  %.26 = call { i32, i1 } @llvm.smul.with.overflow.i32(i32 %.24, i32 %.25)
  %.27 = extractvalue { i32, i1 } %.26, 0
  %.28 = extractvalue { i32, i1 } %.26, 1
  br i1 %.28, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.7, i64 43)
  unreachable
L1:
  %.29 = sext i32 %.27 to i64
  %.30 = getelementptr %Pair, ptr %.19, i32 0, i32 0
  %.31 = trunc i64 %.29 to i32
  store i32 %.31, ptr %.30
  %.32 = getelementptr %Pair, ptr %.1, i32 0, i32 0
  %.33 = load i32, ptr %.32
  %.34 = sext i32 %.33 to i64
  %.35 = add i64 0, 10
  %.36 = trunc i64 %.34 to i32
  %.37 = trunc i64 %.35 to i32
  %.38 = call { i32, i1 } @llvm.smul.with.overflow.i32(i32 %.36, i32 %.37)
  %.39 = extractvalue { i32, i1 } %.38, 0
  %.40 = extractvalue { i32, i1 } %.38, 1
  br i1 %.40, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.8, i64 43)
  unreachable
L3:
  %.41 = sext i32 %.39 to i64
  %.42 = getelementptr %Pair, ptr %.19, i32 0, i32 1
  %.43 = trunc i64 %.41 to i32
  store i32 %.43, ptr %.42
  %.44 = load %Pair, ptr %.19
  ret %Pair %.44
}

define %Mixed @b_mixed(%Mixed %m.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca %Mixed
  %.19 = alloca %Mixed
  store %Mixed %m.arg, ptr %.1
  %.2 = getelementptr [9 x i8], ptr @.str.9, i64 0, i64 0
  %.3 = insertvalue %Span$u8 undef, ptr %.2, 0
  %.4 = insertvalue %Span$u8 %.3, i64 8, 1
  %.5 = extractvalue %Span$u8 %.4, 0
  %.6 = extractvalue %Span$u8 %.4, 1
  %.7 = insertvalue %StrView undef, ptr %.5, 0
  %.8 = insertvalue %StrView %.7, i64 %.6, 1
  call void @say__08e0d8e3(%StrView %.8)
  %.9 = getelementptr %Mixed, ptr %.1, i32 0, i32 0
  %.10 = load i8, ptr %.9
  %.11 = sext i8 %.10 to i64
  %.12 = trunc i64 %.11 to i8
  %.13 = zext i8 %.12 to i64
  call void @rt_hex(i64 %.13)
  %.14 = getelementptr %Mixed, ptr %.1, i32 0, i32 1
  %.15 = load i64, ptr %.14
  call void @rt_hex(i64 %.15)
  %.16 = getelementptr %Mixed, ptr %.1, i32 0, i32 2
  %.17 = load float, ptr %.16
  %.18 = call i64 @bits32__08e0d8e3(float %.17)
  call void @rt_hex(i64 %.18)
  %.20 = getelementptr %Mixed, ptr %.1, i32 0, i32 0
  %.21 = load i8, ptr %.20
  %.22 = sext i8 %.21 to i64
  %.23 = add i64 0, 1
  %.24 = trunc i64 %.22 to i8
  %.25 = trunc i64 %.23 to i8
  %.26 = call { i8, i1 } @llvm.sadd.with.overflow.i8(i8 %.24, i8 %.25)
  %.27 = extractvalue { i8, i1 } %.26, 0
  %.28 = extractvalue { i8, i1 } %.26, 1
  br i1 %.28, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.10, i64 43)
  unreachable
L1:
  %.29 = sext i8 %.27 to i64
  %.30 = getelementptr %Mixed, ptr %.19, i32 0, i32 0
  %.31 = trunc i64 %.29 to i8
  store i8 %.31, ptr %.30
  %.32 = getelementptr %Mixed, ptr %.1, i32 0, i32 1
  %.33 = load i64, ptr %.32
  %.34 = add i64 0, 1
  %.35 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.33, i64 %.34)
  %.36 = extractvalue { i64, i1 } %.35, 0
  %.37 = extractvalue { i64, i1 } %.35, 1
  br i1 %.37, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.11, i64 43)
  unreachable
L3:
  %.38 = getelementptr %Mixed, ptr %.19, i32 0, i32 1
  store i64 %.36, ptr %.38
  %.39 = getelementptr %Mixed, ptr %.1, i32 0, i32 2
  %.40 = load float, ptr %.39
  %.41 = fadd double 0.0, 2.0
  %.42 = fptrunc double %.41 to float
  %.43 = fmul float %.40, %.42
  %.44 = getelementptr %Mixed, ptr %.19, i32 0, i32 2
  store float %.43, ptr %.44
  %.45 = load %Mixed, ptr %.19
  ret %Mixed %.45
}

define i64 @b_straddle_int(i64 %a.arg, i64 %b.arg, i64 %c.arg, i64 %d.arg, i64 %e.arg, %Two %p.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.3 = alloca i64
  %.4 = alloca i64
  %.5 = alloca i64
  %.6 = alloca %Two
  store i64 %a.arg, ptr %.1
  store i64 %b.arg, ptr %.2
  store i64 %c.arg, ptr %.3
  store i64 %d.arg, ptr %.4
  store i64 %e.arg, ptr %.5
  store %Two %p.arg, ptr %.6
  %.7 = getelementptr [16 x i8], ptr @.str.12, i64 0, i64 0
  %.8 = insertvalue %Span$u8 undef, ptr %.7, 0
  %.9 = insertvalue %Span$u8 %.8, i64 15, 1
  %.10 = extractvalue %Span$u8 %.9, 0
  %.11 = extractvalue %Span$u8 %.9, 1
  %.12 = insertvalue %StrView undef, ptr %.10, 0
  %.13 = insertvalue %StrView %.12, i64 %.11, 1
  call void @say__08e0d8e3(%StrView %.13)
  %.14 = load i64, ptr %.1
  %.15 = load i64, ptr %.2
  %.16 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.14, i64 %.15)
  %.17 = extractvalue { i64, i1 } %.16, 0
  %.18 = extractvalue { i64, i1 } %.16, 1
  br i1 %.18, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.13, i64 43)
  unreachable
L1:
  %.19 = load i64, ptr %.3
  %.20 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.17, i64 %.19)
  %.21 = extractvalue { i64, i1 } %.20, 0
  %.22 = extractvalue { i64, i1 } %.20, 1
  br i1 %.22, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.14, i64 43)
  unreachable
L3:
  %.23 = load i64, ptr %.4
  %.24 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.21, i64 %.23)
  %.25 = extractvalue { i64, i1 } %.24, 0
  %.26 = extractvalue { i64, i1 } %.24, 1
  br i1 %.26, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.15, i64 43)
  unreachable
L5:
  %.27 = load i64, ptr %.5
  %.28 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.25, i64 %.27)
  %.29 = extractvalue { i64, i1 } %.28, 0
  %.30 = extractvalue { i64, i1 } %.28, 1
  br i1 %.30, label %L6, label %L7
L6:
  call void @__ritz_overflow_trap(ptr @.str.16, i64 43)
  unreachable
L7:
  call void @rt_hex(i64 %.29)
  %.31 = getelementptr %Two, ptr %.6, i32 0, i32 0
  %.32 = load i64, ptr %.31
  call void @rt_hex(i64 %.32)
  %.33 = getelementptr %Two, ptr %.6, i32 0, i32 1
  %.34 = load i64, ptr %.33
  call void @rt_hex(i64 %.34)
  %.35 = getelementptr %Two, ptr %.6, i32 0, i32 0
  %.36 = load i64, ptr %.35
  %.37 = getelementptr %Two, ptr %.6, i32 0, i32 1
  %.38 = load i64, ptr %.37
  %.39 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.36, i64 %.38)
  %.40 = extractvalue { i64, i1 } %.39, 0
  %.41 = extractvalue { i64, i1 } %.39, 1
  br i1 %.41, label %L8, label %L9
L8:
  call void @__ritz_overflow_trap(ptr @.str.17, i64 42)
  unreachable
L9:
  ret i64 %.40
}

define i64 @b_straddle_float(double %a.arg, double %b.arg, double %c.arg, double %d.arg, double %e.arg, double %f.arg, double %g.arg, %D2 %p.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  %.2 = alloca double
  %.3 = alloca double
  %.4 = alloca double
  %.5 = alloca double
  %.6 = alloca double
  %.7 = alloca double
  %.8 = alloca %D2
  store double %a.arg, ptr %.1
  store double %b.arg, ptr %.2
  store double %c.arg, ptr %.3
  store double %d.arg, ptr %.4
  store double %e.arg, ptr %.5
  store double %f.arg, ptr %.6
  store double %g.arg, ptr %.7
  store %D2 %p.arg, ptr %.8
  %.9 = getelementptr [18 x i8], ptr @.str.18, i64 0, i64 0
  %.10 = insertvalue %Span$u8 undef, ptr %.9, 0
  %.11 = insertvalue %Span$u8 %.10, i64 17, 1
  %.12 = extractvalue %Span$u8 %.11, 0
  %.13 = extractvalue %Span$u8 %.11, 1
  %.14 = insertvalue %StrView undef, ptr %.12, 0
  %.15 = insertvalue %StrView %.14, i64 %.13, 1
  call void @say__08e0d8e3(%StrView %.15)
  %.16 = load double, ptr %.1
  %.17 = load double, ptr %.2
  %.18 = fadd double %.16, %.17
  %.19 = load double, ptr %.3
  %.20 = fadd double %.18, %.19
  %.21 = load double, ptr %.4
  %.22 = fadd double %.20, %.21
  %.23 = load double, ptr %.5
  %.24 = fadd double %.22, %.23
  %.25 = load double, ptr %.6
  %.26 = fadd double %.24, %.25
  %.27 = load double, ptr %.7
  %.28 = fadd double %.26, %.27
  %.29 = call i64 @bits64__08e0d8e3(double %.28)
  call void @rt_hex(i64 %.29)
  %.30 = getelementptr %D2, ptr %.8, i32 0, i32 0
  %.31 = load double, ptr %.30
  %.32 = call i64 @bits64__08e0d8e3(double %.31)
  call void @rt_hex(i64 %.32)
  %.33 = getelementptr %D2, ptr %.8, i32 0, i32 1
  %.34 = load double, ptr %.33
  %.35 = call i64 @bits64__08e0d8e3(double %.34)
  call void @rt_hex(i64 %.35)
  %.36 = getelementptr %D2, ptr %.8, i32 0, i32 0
  %.37 = load double, ptr %.36
  %.38 = getelementptr %D2, ptr %.8, i32 0, i32 1
  %.39 = load double, ptr %.38
  %.40 = fadd double %.37, %.39
  %.41 = call i64 @bits64__08e0d8e3(double %.40)
  ret i64 %.41
}

define i64 @b_packed(%Packed %p.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca %Packed
  store %Packed %p.arg, ptr %.1
  %.2 = getelementptr [10 x i8], ptr @.str.19, i64 0, i64 0
  %.3 = insertvalue %Span$u8 undef, ptr %.2, 0
  %.4 = insertvalue %Span$u8 %.3, i64 9, 1
  %.5 = extractvalue %Span$u8 %.4, 0
  %.6 = extractvalue %Span$u8 %.4, 1
  %.7 = insertvalue %StrView undef, ptr %.5, 0
  %.8 = insertvalue %StrView %.7, i64 %.6, 1
  call void @say__08e0d8e3(%StrView %.8)
  %.9 = getelementptr %Packed, ptr %.1, i32 0, i32 0
  %.10 = load i8, ptr %.9, align 1
  %.11 = zext i8 %.10 to i64
  %.12 = trunc i64 %.11 to i8
  %.13 = zext i8 %.12 to i64
  call void @rt_hex(i64 %.13)
  %.14 = getelementptr %Packed, ptr %.1, i32 0, i32 1
  %.15 = load i32, ptr %.14, align 1
  %.16 = zext i32 %.15 to i64
  %.17 = trunc i64 %.16 to i32
  %.18 = zext i32 %.17 to i64
  call void @rt_hex(i64 %.18)
  %.19 = getelementptr %Packed, ptr %.1, i32 0, i32 2
  %.20 = load i16, ptr %.19, align 1
  %.21 = zext i16 %.20 to i64
  %.22 = trunc i64 %.21 to i16
  %.23 = zext i16 %.22 to i64
  call void @rt_hex(i64 %.23)
  %.24 = getelementptr %Packed, ptr %.1, i32 0, i32 0
  %.25 = load i8, ptr %.24, align 1
  %.26 = zext i8 %.25 to i64
  %.27 = trunc i64 %.26 to i8
  %.28 = zext i8 %.27 to i64
  %.29 = getelementptr %Packed, ptr %.1, i32 0, i32 1
  %.30 = load i32, ptr %.29, align 1
  %.31 = zext i32 %.30 to i64
  %.32 = trunc i64 %.31 to i32
  %.33 = zext i32 %.32 to i64
  %.34 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.28, i64 %.33)
  %.35 = extractvalue { i64, i1 } %.34, 0
  %.36 = extractvalue { i64, i1 } %.34, 1
  br i1 %.36, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.20, i64 42)
  unreachable
L1:
  %.37 = getelementptr %Packed, ptr %.1, i32 0, i32 2
  %.38 = load i16, ptr %.37, align 1
  %.39 = zext i16 %.38 to i64
  %.40 = trunc i64 %.39 to i16
  %.41 = zext i16 %.40 to i64
  %.42 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.35, i64 %.41)
  %.43 = extractvalue { i64, i1 } %.42, 0
  %.44 = extractvalue { i64, i1 } %.42, 1
  br i1 %.44, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.21, i64 42)
  unreachable
L3:
  ret i64 %.43
}

define %Three @b_three(i64 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca %Three
  store i64 %x.arg, ptr %.1
  %.3 = load i64, ptr %.1
  %.4 = getelementptr %Three, ptr %.2, i32 0, i32 0
  store i64 %.3, ptr %.4
  %.5 = load i64, ptr %.1
  %.6 = add i64 0, 1
  %.7 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.5, i64 %.6)
  %.8 = extractvalue { i64, i1 } %.7, 0
  %.9 = extractvalue { i64, i1 } %.7, 1
  br i1 %.9, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.22, i64 43)
  unreachable
L1:
  %.10 = getelementptr %Three, ptr %.2, i32 0, i32 1
  store i64 %.8, ptr %.10
  %.11 = load i64, ptr %.1
  %.12 = add i64 0, 2
  %.13 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.11, i64 %.12)
  %.14 = extractvalue { i64, i1 } %.13, 0
  %.15 = extractvalue { i64, i1 } %.13, 1
  br i1 %.15, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.23, i64 43)
  unreachable
L3:
  %.16 = getelementptr %Three, ptr %.2, i32 0, i32 2
  store i64 %.14, ptr %.16
  %.17 = load %Three, ptr %.2
  ret %Three %.17
}

define %Four @b_four(i64 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca %Four
  store i64 %x.arg, ptr %.1
  %.3 = load i64, ptr %.1
  %.4 = getelementptr %Four, ptr %.2, i32 0, i32 0
  store i64 %.3, ptr %.4
  %.5 = load i64, ptr %.1
  %.6 = add i64 0, 1
  %.7 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.5, i64 %.6)
  %.8 = extractvalue { i64, i1 } %.7, 0
  %.9 = extractvalue { i64, i1 } %.7, 1
  br i1 %.9, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.24, i64 43)
  unreachable
L1:
  %.10 = getelementptr %Four, ptr %.2, i32 0, i32 1
  store i64 %.8, ptr %.10
  %.11 = load i64, ptr %.1
  %.12 = add i64 0, 2
  %.13 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.11, i64 %.12)
  %.14 = extractvalue { i64, i1 } %.13, 0
  %.15 = extractvalue { i64, i1 } %.13, 1
  br i1 %.15, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.25, i64 43)
  unreachable
L3:
  %.16 = getelementptr %Four, ptr %.2, i32 0, i32 2
  store i64 %.14, ptr %.16
  %.17 = load i64, ptr %.1
  %.18 = add i64 0, 3
  %.19 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.17, i64 %.18)
  %.20 = extractvalue { i64, i1 } %.19, 0
  %.21 = extractvalue { i64, i1 } %.19, 1
  br i1 %.21, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.26, i64 43)
  unreachable
L5:
  %.22 = getelementptr %Four, ptr %.2, i32 0, i32 3
  store i64 %.20, ptr %.22
  %.23 = load %Four, ptr %.2
  ret %Four %.23
}

define %D2 @b_d2(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  %.2 = alloca %D2
  store double %x.arg, ptr %.1
  %.3 = load double, ptr %.1
  %.4 = getelementptr %D2, ptr %.2, i32 0, i32 0
  store double %.3, ptr %.4
  %.5 = load double, ptr %.1
  %.6 = fadd double 0.0, 1.0
  %.7 = fadd double %.5, %.6
  %.8 = getelementptr %D2, ptr %.2, i32 0, i32 1
  store double %.7, ptr %.8
  %.9 = load %D2, ptr %.2
  ret %D2 %.9
}

define %D3 @b_d3(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  %.2 = alloca %D3
  store double %x.arg, ptr %.1
  %.3 = load double, ptr %.1
  %.4 = getelementptr %D3, ptr %.2, i32 0, i32 0
  store double %.3, ptr %.4
  %.5 = load double, ptr %.1
  %.6 = fadd double 0.0, 1.0
  %.7 = fadd double %.5, %.6
  %.8 = getelementptr %D3, ptr %.2, i32 0, i32 1
  store double %.7, ptr %.8
  %.9 = load double, ptr %.1
  %.10 = fadd double 0.0, 2.0
  %.11 = fadd double %.9, %.10
  %.12 = getelementptr %D3, ptr %.2, i32 0, i32 2
  store double %.11, ptr %.12
  %.13 = load %D3, ptr %.2
  ret %D3 %.13
}

define %D4 @b_d4(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  %.2 = alloca %D4
  store double %x.arg, ptr %.1
  %.3 = load double, ptr %.1
  %.4 = getelementptr %D4, ptr %.2, i32 0, i32 0
  store double %.3, ptr %.4
  %.5 = load double, ptr %.1
  %.6 = fadd double 0.0, 1.0
  %.7 = fadd double %.5, %.6
  %.8 = getelementptr %D4, ptr %.2, i32 0, i32 1
  store double %.7, ptr %.8
  %.9 = load double, ptr %.1
  %.10 = fadd double 0.0, 2.0
  %.11 = fadd double %.9, %.10
  %.12 = getelementptr %D4, ptr %.2, i32 0, i32 2
  store double %.11, ptr %.12
  %.13 = load double, ptr %.1
  %.14 = fadd double 0.0, 3.0
  %.15 = fadd double %.13, %.14
  %.16 = getelementptr %D4, ptr %.2, i32 0, i32 3
  store double %.15, ptr %.16
  %.17 = load %D4, ptr %.2
  ret %D4 %.17
}

define %D5 @b_d5(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  %.2 = alloca %D5
  store double %x.arg, ptr %.1
  %.3 = load double, ptr %.1
  %.4 = getelementptr %D5, ptr %.2, i32 0, i32 0
  store double %.3, ptr %.4
  %.5 = load double, ptr %.1
  %.6 = fadd double 0.0, 1.0
  %.7 = fadd double %.5, %.6
  %.8 = getelementptr %D5, ptr %.2, i32 0, i32 1
  store double %.7, ptr %.8
  %.9 = load double, ptr %.1
  %.10 = fadd double 0.0, 2.0
  %.11 = fadd double %.9, %.10
  %.12 = getelementptr %D5, ptr %.2, i32 0, i32 2
  store double %.11, ptr %.12
  %.13 = load double, ptr %.1
  %.14 = fadd double 0.0, 3.0
  %.15 = fadd double %.13, %.14
  %.16 = getelementptr %D5, ptr %.2, i32 0, i32 3
  store double %.15, ptr %.16
  %.17 = load double, ptr %.1
  %.18 = fadd double 0.0, 4.0
  %.19 = fadd double %.17, %.18
  %.20 = getelementptr %D5, ptr %.2, i32 0, i32 4
  store double %.19, ptr %.20
  %.21 = load %D5, ptr %.2
  ret %D5 %.21
}

define %V4 @b_v4(i32 %base.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca %V4
  store i32 %base.arg, ptr %.1
  %.3 = load i32, ptr %.1
  %.4 = sext i32 %.3 to i64
  %.5 = trunc i64 %.4 to i32
  %.6 = call <4 x i32> @vec_of__08e0d8e3(i32 %.5)
  %.7 = getelementptr %V4, ptr %.2, i32 0, i32 0
  store <4 x i32> %.6, ptr %.7
  %.8 = load i32, ptr %.1
  %.9 = sext i32 %.8 to i64
  %.10 = add i64 0, 10
  %.11 = trunc i64 %.9 to i32
  %.12 = trunc i64 %.10 to i32
  %.13 = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %.11, i32 %.12)
  %.14 = extractvalue { i32, i1 } %.13, 0
  %.15 = extractvalue { i32, i1 } %.13, 1
  br i1 %.15, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.27, i64 43)
  unreachable
L1:
  %.16 = sext i32 %.14 to i64
  %.17 = trunc i64 %.16 to i32
  %.18 = call <4 x i32> @vec_of__08e0d8e3(i32 %.17)
  %.19 = getelementptr %V4, ptr %.2, i32 0, i32 1
  store <4 x i32> %.18, ptr %.19
  %.20 = load i32, ptr %.1
  %.21 = sext i32 %.20 to i64
  %.22 = add i64 0, 20
  %.23 = trunc i64 %.21 to i32
  %.24 = trunc i64 %.22 to i32
  %.25 = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %.23, i32 %.24)
  %.26 = extractvalue { i32, i1 } %.25, 0
  %.27 = extractvalue { i32, i1 } %.25, 1
  br i1 %.27, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.28, i64 43)
  unreachable
L3:
  %.28 = sext i32 %.26 to i64
  %.29 = trunc i64 %.28 to i32
  %.30 = call <4 x i32> @vec_of__08e0d8e3(i32 %.29)
  %.31 = getelementptr %V4, ptr %.2, i32 0, i32 2
  store <4 x i32> %.30, ptr %.31
  %.32 = load i32, ptr %.1
  %.33 = sext i32 %.32 to i64
  %.34 = add i64 0, 30
  %.35 = trunc i64 %.33 to i32
  %.36 = trunc i64 %.34 to i32
  %.37 = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %.35, i32 %.36)
  %.38 = extractvalue { i32, i1 } %.37, 0
  %.39 = extractvalue { i32, i1 } %.37, 1
  br i1 %.39, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.29, i64 43)
  unreachable
L5:
  %.40 = sext i32 %.38 to i64
  %.41 = trunc i64 %.40 to i32
  %.42 = call <4 x i32> @vec_of__08e0d8e3(i32 %.41)
  %.43 = getelementptr %V4, ptr %.2, i32 0, i32 3
  store <4 x i32> %.42, ptr %.43
  %.44 = load %V4, ptr %.2
  ret %V4 %.44
}

define %V5 @b_v5(i32 %base.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca %V5
  store i32 %base.arg, ptr %.1
  %.3 = load i32, ptr %.1
  %.4 = sext i32 %.3 to i64
  %.5 = trunc i64 %.4 to i32
  %.6 = call <4 x i32> @vec_of__08e0d8e3(i32 %.5)
  %.7 = getelementptr %V5, ptr %.2, i32 0, i32 0
  store <4 x i32> %.6, ptr %.7
  %.8 = load i32, ptr %.1
  %.9 = sext i32 %.8 to i64
  %.10 = add i64 0, 10
  %.11 = trunc i64 %.9 to i32
  %.12 = trunc i64 %.10 to i32
  %.13 = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %.11, i32 %.12)
  %.14 = extractvalue { i32, i1 } %.13, 0
  %.15 = extractvalue { i32, i1 } %.13, 1
  br i1 %.15, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.30, i64 43)
  unreachable
L1:
  %.16 = sext i32 %.14 to i64
  %.17 = trunc i64 %.16 to i32
  %.18 = call <4 x i32> @vec_of__08e0d8e3(i32 %.17)
  %.19 = getelementptr %V5, ptr %.2, i32 0, i32 1
  store <4 x i32> %.18, ptr %.19
  %.20 = load i32, ptr %.1
  %.21 = sext i32 %.20 to i64
  %.22 = add i64 0, 20
  %.23 = trunc i64 %.21 to i32
  %.24 = trunc i64 %.22 to i32
  %.25 = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %.23, i32 %.24)
  %.26 = extractvalue { i32, i1 } %.25, 0
  %.27 = extractvalue { i32, i1 } %.25, 1
  br i1 %.27, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.31, i64 43)
  unreachable
L3:
  %.28 = sext i32 %.26 to i64
  %.29 = trunc i64 %.28 to i32
  %.30 = call <4 x i32> @vec_of__08e0d8e3(i32 %.29)
  %.31 = getelementptr %V5, ptr %.2, i32 0, i32 2
  store <4 x i32> %.30, ptr %.31
  %.32 = load i32, ptr %.1
  %.33 = sext i32 %.32 to i64
  %.34 = add i64 0, 30
  %.35 = trunc i64 %.33 to i32
  %.36 = trunc i64 %.34 to i32
  %.37 = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %.35, i32 %.36)
  %.38 = extractvalue { i32, i1 } %.37, 0
  %.39 = extractvalue { i32, i1 } %.37, 1
  br i1 %.39, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.32, i64 43)
  unreachable
L5:
  %.40 = sext i32 %.38 to i64
  %.41 = trunc i64 %.40 to i32
  %.42 = call <4 x i32> @vec_of__08e0d8e3(i32 %.41)
  %.43 = getelementptr %V5, ptr %.2, i32 0, i32 3
  store <4 x i32> %.42, ptr %.43
  %.44 = load i32, ptr %.1
  %.45 = sext i32 %.44 to i64
  %.46 = add i64 0, 40
  %.47 = trunc i64 %.45 to i32
  %.48 = trunc i64 %.46 to i32
  %.49 = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %.47, i32 %.48)
  %.50 = extractvalue { i32, i1 } %.49, 0
  %.51 = extractvalue { i32, i1 } %.49, 1
  br i1 %.51, label %L6, label %L7
L6:
  call void @__ritz_overflow_trap(ptr @.str.33, i64 44)
  unreachable
L7:
  %.52 = sext i32 %.50 to i64
  %.53 = trunc i64 %.52 to i32
  %.54 = call <4 x i32> @vec_of__08e0d8e3(i32 %.53)
  %.55 = getelementptr %V5, ptr %.2, i32 0, i32 4
  store <4 x i32> %.54, ptr %.55
  %.56 = load %V5, ptr %.2
  ret %V5 %.56
}

define i64 @b_big(ptr byval(%Big) align 8 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = getelementptr i8, ptr %b.arg, i64 0  ; #1739 byval param
  %.2 = getelementptr [7 x i8], ptr @.str.34, i64 0, i64 0
  %.3 = insertvalue %Span$u8 undef, ptr %.2, 0
  %.4 = insertvalue %Span$u8 %.3, i64 6, 1
  %.5 = extractvalue %Span$u8 %.4, 0
  %.6 = extractvalue %Span$u8 %.4, 1
  %.7 = insertvalue %StrView undef, ptr %.5, 0
  %.8 = insertvalue %StrView %.7, i64 %.6, 1
  call void @say__08e0d8e3(%StrView %.8)
  %.9 = getelementptr %Big, ptr %.1, i32 0, i32 0
  %.10 = add i64 0, 0
  %.11 = getelementptr [40 x i64], ptr %.9, i64 0, i64 %.10
  %.12 = load i64, ptr %.11
  call void @rt_hex(i64 %.12)
  %.13 = getelementptr %Big, ptr %.1, i32 0, i32 0
  %.14 = add i64 0, 39
  %.15 = getelementptr [40 x i64], ptr %.13, i64 0, i64 %.14
  %.16 = load i64, ptr %.15
  call void @rt_hex(i64 %.16)
  %.17 = getelementptr %Big, ptr %.1, i32 0, i32 0
  %.18 = add i64 0, 0
  %.19 = getelementptr [40 x i64], ptr %.17, i64 0, i64 %.18
  %.20 = load i64, ptr %.19
  %.21 = getelementptr %Big, ptr %.1, i32 0, i32 0
  %.22 = add i64 0, 39
  %.23 = getelementptr [40 x i64], ptr %.21, i64 0, i64 %.22
  %.24 = load i64, ptr %.23
  %.25 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.20, i64 %.24)
  %.26 = extractvalue { i64, i1 } %.25, 0
  %.27 = extractvalue { i64, i1 } %.25, 1
  br i1 %.27, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.35, i64 42)
  unreachable
L1:
  ret i64 %.26
}

define i64 @b_big_wide(ptr byval(%BigWide) align 32 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.13 = alloca %LanesB
  %.1 = getelementptr i8, ptr %b.arg, i64 0  ; #1739 byval param
  %.2 = getelementptr [12 x i8], ptr @.str.36, i64 0, i64 0
  %.3 = insertvalue %Span$u8 undef, ptr %.2, 0
  %.4 = insertvalue %Span$u8 %.3, i64 11, 1
  %.5 = extractvalue %Span$u8 %.4, 0
  %.6 = extractvalue %Span$u8 %.4, 1
  %.7 = insertvalue %StrView undef, ptr %.5, 0
  %.8 = insertvalue %StrView %.7, i64 %.6, 1
  call void @say__08e0d8e3(%StrView %.8)
  %.9 = getelementptr %BigWide, ptr %.1, i32 0, i32 0
  %.10 = add i64 0, 1
  %.11 = getelementptr [40 x i64], ptr %.9, i64 0, i64 %.10
  %.12 = load i64, ptr %.11
  call void @rt_hex(i64 %.12)
  %.14 = add i64 0, 0
  %.15 = getelementptr %LanesB, ptr %.13, i32 0, i32 0
  store i64 %.14, ptr %.15
  %.16 = getelementptr %BigWide, ptr %.1, i32 0, i32 1
  %.17 = load <8 x i32>, ptr %.16
  %.18 = call i64 @LanesB_lane7(ptr %.13, <8 x i32> %.17)
  call void @rt_hex(i64 %.18)
  %.19 = getelementptr %BigWide, ptr %.1, i32 0, i32 0
  %.20 = add i64 0, 1
  %.21 = getelementptr [40 x i64], ptr %.19, i64 0, i64 %.20
  %.22 = load i64, ptr %.21
  ret i64 %.22
}

define void @b_sret(ptr sret(%Big) %ret.sret, i64 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca %Big
  store i64 %x.arg, ptr %.1
  %.3 = getelementptr %Big, ptr %.2, i32 0, i32 0
  call void @__ritz_sret_zero(ptr %.3, i64 320)
  %.4 = getelementptr %Big, ptr %.2, i32 0, i32 0
  %.5 = add i64 0, 0
  %.6 = load i64, ptr %.1
  %.7 = getelementptr [40 x i64], ptr %.4, i64 0, i64 %.5
  store i64 %.6, ptr %.7
  %.8 = getelementptr %Big, ptr %.2, i32 0, i32 0
  %.9 = add i64 0, 39
  %.10 = load i64, ptr %.1
  %.11 = add i64 0, 2
  %.12 = call { i64, i1 } @llvm.smul.with.overflow.i64(i64 %.10, i64 %.11)
  %.13 = extractvalue { i64, i1 } %.12, 0
  %.14 = extractvalue { i64, i1 } %.12, 1
  br i1 %.14, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.37, i64 43)
  unreachable
L1:
  %.15 = getelementptr [40 x i64], ptr %.8, i64 0, i64 %.9
  store i64 %.13, ptr %.15
  call void @__ritz_sret_copy(ptr %ret.sret, ptr %.2, i64 ptrtoint (ptr getelementptr (%Big, ptr null, i32 1) to i64))
  ret void
}

define i64 @b_aligned() alignstack(16) "no-builtins" {
entry:
  %.1 = call i64 @entry_misalign()
  ret i64 %.1
}

define void @b_calls_a() alignstack(16) "no-builtins" {
entry:
  %.8 = alloca %Pair
  %.9 = alloca %Pair  ; rvalue struct literal
  %.28 = alloca %Mixed
  %.29 = alloca %Mixed  ; rvalue struct literal
  %.55 = alloca %Two  ; rvalue struct literal
  %.69 = alloca %D2  ; rvalue struct literal
  %.76 = alloca %Three
  %.91 = alloca %D3
  %.103 = alloca %V4
  %.128 = alloca %Big
  %.130 = alloca %Big
  %.1 = getelementptr [11 x i8], ptr @.str.38, i64 0, i64 0
  %.2 = insertvalue %Span$u8 undef, ptr %.1, 0
  %.3 = insertvalue %Span$u8 %.2, i64 10, 1
  %.4 = extractvalue %Span$u8 %.3, 0
  %.5 = extractvalue %Span$u8 %.3, 1
  %.6 = insertvalue %StrView undef, ptr %.4, 0
  %.7 = insertvalue %StrView %.6, i64 %.5, 1
  call void @say__08e0d8e3(%StrView %.7)
  %.10 = add i64 0, 3
  %.11 = getelementptr %Pair, ptr %.9, i32 0, i32 0
  %.12 = trunc i64 %.10 to i32
  store i32 %.12, ptr %.11
  %.13 = add i64 0, 4
  %.14 = getelementptr %Pair, ptr %.9, i32 0, i32 1
  %.15 = trunc i64 %.13 to i32
  store i32 %.15, ptr %.14
  %.16 = load %Pair, ptr %.9
  %.17 = call %Pair @a_pair(%Pair %.16)
  store %Pair %.17, ptr %.8
  %.18 = getelementptr %Pair, ptr %.8, i32 0, i32 0
  %.19 = load i32, ptr %.18
  %.20 = sext i32 %.19 to i64
  %.21 = trunc i64 %.20 to i32
  %.22 = zext i32 %.21 to i64
  call void @rt_hex(i64 %.22)
  %.23 = getelementptr %Pair, ptr %.8, i32 0, i32 1
  %.24 = load i32, ptr %.23
  %.25 = sext i32 %.24 to i64
  %.26 = trunc i64 %.25 to i32
  %.27 = zext i32 %.26 to i64
  call void @rt_hex(i64 %.27)
  %.30 = add i64 0, 7
  %.31 = getelementptr %Mixed, ptr %.29, i32 0, i32 0
  %.32 = trunc i64 %.30 to i8
  store i8 %.32, ptr %.31
  %.33 = add i64 0, 70
  %.34 = getelementptr %Mixed, ptr %.29, i32 0, i32 1
  store i64 %.33, ptr %.34
  %.35 = fadd double 0.0, 0.5
  %.36 = getelementptr %Mixed, ptr %.29, i32 0, i32 2
  %.37 = fptrunc double %.35 to float
  store float %.37, ptr %.36
  %.38 = load %Mixed, ptr %.29
  %.39 = call %Mixed @a_mixed(%Mixed %.38)
  store %Mixed %.39, ptr %.28
  %.40 = getelementptr %Mixed, ptr %.28, i32 0, i32 0
  %.41 = load i8, ptr %.40
  %.42 = sext i8 %.41 to i64
  %.43 = trunc i64 %.42 to i8
  %.44 = zext i8 %.43 to i64
  call void @rt_hex(i64 %.44)
  %.45 = getelementptr %Mixed, ptr %.28, i32 0, i32 1
  %.46 = load i64, ptr %.45
  call void @rt_hex(i64 %.46)
  %.47 = getelementptr %Mixed, ptr %.28, i32 0, i32 2
  %.48 = load float, ptr %.47
  %.49 = call i64 @bits32__08e0d8e3(float %.48)
  call void @rt_hex(i64 %.49)
  %.50 = add i64 0, 1
  %.51 = add i64 0, 2
  %.52 = add i64 0, 3
  %.53 = add i64 0, 4
  %.54 = add i64 0, 5
  %.56 = add i64 0, 60
  %.57 = getelementptr %Two, ptr %.55, i32 0, i32 0
  store i64 %.56, ptr %.57
  %.58 = add i64 0, 70
  %.59 = getelementptr %Two, ptr %.55, i32 0, i32 1
  store i64 %.58, ptr %.59
  %.60 = load %Two, ptr %.55
  %.61 = call i64 @a_straddle_int(i64 %.50, i64 %.51, i64 %.52, i64 %.53, i64 %.54, %Two %.60)
  call void @rt_hex(i64 %.61)
  %.62 = fadd double 0.0, 1.0
  %.63 = fadd double 0.0, 2.0
  %.64 = fadd double 0.0, 3.0
  %.65 = fadd double 0.0, 4.0
  %.66 = fadd double 0.0, 5.0
  %.67 = fadd double 0.0, 6.0
  %.68 = fadd double 0.0, 7.0
  %.70 = fadd double 0.0, 8.5
  %.71 = getelementptr %D2, ptr %.69, i32 0, i32 0
  store double %.70, ptr %.71
  %.72 = fadd double 0.0, 9.5
  %.73 = getelementptr %D2, ptr %.69, i32 0, i32 1
  store double %.72, ptr %.73
  %.74 = load %D2, ptr %.69
  %.75 = call i64 @a_straddle_float(double %.62, double %.63, double %.64, double %.65, double %.66, double %.67, double %.68, %D2 %.74)
  call void @rt_hex(i64 %.75)
  %.77 = add i64 0, 100
  %.78 = call %Three @a_three(i64 %.77)
  store %Three %.78, ptr %.76
  %.79 = getelementptr %Three, ptr %.76, i32 0, i32 0
  %.80 = load i64, ptr %.79
  %.81 = getelementptr %Three, ptr %.76, i32 0, i32 1
  %.82 = load i64, ptr %.81
  %.83 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.80, i64 %.82)
  %.84 = extractvalue { i64, i1 } %.83, 0
  %.85 = extractvalue { i64, i1 } %.83, 1
  br i1 %.85, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.39, i64 43)
  unreachable
L1:
  %.86 = getelementptr %Three, ptr %.76, i32 0, i32 2
  %.87 = load i64, ptr %.86
  %.88 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.84, i64 %.87)
  %.89 = extractvalue { i64, i1 } %.88, 0
  %.90 = extractvalue { i64, i1 } %.88, 1
  br i1 %.90, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.40, i64 43)
  unreachable
L3:
  call void @rt_hex(i64 %.89)
  %.92 = fadd double 0.0, 1.5
  %.93 = call %D3 @a_d3(double %.92)
  store %D3 %.93, ptr %.91
  %.94 = getelementptr %D3, ptr %.91, i32 0, i32 0
  %.95 = load double, ptr %.94
  %.96 = getelementptr %D3, ptr %.91, i32 0, i32 1
  %.97 = load double, ptr %.96
  %.98 = fadd double %.95, %.97
  %.99 = getelementptr %D3, ptr %.91, i32 0, i32 2
  %.100 = load double, ptr %.99
  %.101 = fadd double %.98, %.100
  %.102 = call i64 @bits64__08e0d8e3(double %.101)
  call void @rt_hex(i64 %.102)
  %.104 = add i64 0, 1
  %.105 = trunc i64 %.104 to i32
  %.106 = call %V4 @a_v4(i32 %.105)
  store %V4 %.106, ptr %.103
  %.107 = getelementptr %V4, ptr %.103, i32 0, i32 0
  %.108 = load <4 x i32>, ptr %.107
  %.109 = call i64 @vec_sum__08e0d8e3(<4 x i32> %.108)
  %.110 = getelementptr %V4, ptr %.103, i32 0, i32 1
  %.111 = load <4 x i32>, ptr %.110
  %.112 = call i64 @vec_sum__08e0d8e3(<4 x i32> %.111)
  %.113 = call { i64, i1 } @llvm.uadd.with.overflow.i64(i64 %.109, i64 %.112)
  %.114 = extractvalue { i64, i1 } %.113, 0
  %.115 = extractvalue { i64, i1 } %.113, 1
  br i1 %.115, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.41, i64 43)
  unreachable
L5:
  %.116 = getelementptr %V4, ptr %.103, i32 0, i32 2
  %.117 = load <4 x i32>, ptr %.116
  %.118 = call i64 @vec_sum__08e0d8e3(<4 x i32> %.117)
  %.119 = call { i64, i1 } @llvm.uadd.with.overflow.i64(i64 %.114, i64 %.118)
  %.120 = extractvalue { i64, i1 } %.119, 0
  %.121 = extractvalue { i64, i1 } %.119, 1
  br i1 %.121, label %L6, label %L7
L6:
  call void @__ritz_overflow_trap(ptr @.str.42, i64 43)
  unreachable
L7:
  %.122 = getelementptr %V4, ptr %.103, i32 0, i32 3
  %.123 = load <4 x i32>, ptr %.122
  %.124 = call i64 @vec_sum__08e0d8e3(<4 x i32> %.123)
  %.125 = call { i64, i1 } @llvm.uadd.with.overflow.i64(i64 %.120, i64 %.124)
  %.126 = extractvalue { i64, i1 } %.125, 0
  %.127 = extractvalue { i64, i1 } %.125, 1
  br i1 %.127, label %L8, label %L9
L8:
  call void @__ritz_overflow_trap(ptr @.str.43, i64 43)
  unreachable
L9:
  call void @rt_hex(i64 %.126)
  %.129 = add i64 0, 9
  call void @a_sret(ptr sret(%Big) %.130, i64 %.129)
  call void @__ritz_sret_copy(ptr %.128, ptr %.130, i64 ptrtoint (ptr getelementptr (%Big, ptr null, i32 1) to i64))
  %.132 = getelementptr %Big, ptr %.128, i32 0, i32 0
  %.133 = add i64 0, 0
  %.134 = getelementptr [40 x i64], ptr %.132, i64 0, i64 %.133
  %.135 = load i64, ptr %.134
  %.136 = getelementptr %Big, ptr %.128, i32 0, i32 0
  %.137 = add i64 0, 39
  %.138 = getelementptr [40 x i64], ptr %.136, i64 0, i64 %.137
  %.139 = load i64, ptr %.138
  %.140 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.135, i64 %.139)
  %.141 = extractvalue { i64, i1 } %.140, 0
  %.142 = extractvalue { i64, i1 } %.140, 1
  br i1 %.142, label %L10, label %L11
L10:
  call void @__ritz_overflow_trap(ptr @.str.44, i64 43)
  unreachable
L11:
  call void @rt_hex(i64 %.141)
  %.143 = call i64 @entry_misalign()
  call void @rt_hex(i64 %.143)
  ret void
}

define internal i64 @LanesB_lane7(ptr %self.arg, <8 x i32> %v.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca ptr
  %.2 = alloca <8 x i32>
  store ptr %self.arg, ptr %.1
  store <8 x i32> %v.arg, ptr %.2
  %.3 = load <8 x i32>, ptr %.2
  %.4 = add i64 0, 7
  %.5 = trunc i64 %.4 to i32
  %.6 = extractelement <8 x i32> %.3, i32 %.5
  %.7 = sext i32 %.6 to i64
  ret i64 %.7
}

define internal i64 @LanesB_bump(ptr %self.arg, <8 x i32> %v.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca ptr
  %.2 = alloca <8 x i32>
  store ptr %self.arg, ptr %.1
  store <8 x i32> %v.arg, ptr %.2
  %.3 = load <8 x i32>, ptr %.2
  %.4 = load <8 x i32>, ptr %.2
  %.5 = add <8 x i32> %.3, %.4
  %.6 = add i64 0, 7
  %.7 = trunc i64 %.6 to i32
  %.8 = extractelement <8 x i32> %.5, i32 %.7
  %.9 = sext i32 %.8 to i64
  %.10 = load ptr, ptr %.1
  %.11 = getelementptr %LanesB, ptr %.10, i32 0, i32 0
  %.12 = load i64, ptr %.11
  %.13 = call { i64, i1 } @llvm.uadd.with.overflow.i64(i64 %.9, i64 %.12)
  %.14 = extractvalue { i64, i1 } %.13, 0
  %.15 = extractvalue { i64, i1 } %.13, 1
  br i1 %.15, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.45, i64 43)
  unreachable
L1:
  ret i64 %.14
}


@.str.0 = private constant [44 x i8] c"abi_b.ritz:112:29: integer overflow in `+`\0A\00"
@.str.1 = private constant [44 x i8] c"abi_b.ritz:112:39: integer overflow in `+`\0A\00"
@.str.2 = private constant [44 x i8] c"abi_b.ritz:112:49: integer overflow in `+`\0A\00"
@.str.3 = private constant [43 x i8] c"abi_b.ritz:118:6: integer overflow in `+`\0A\00"
@.str.4 = private constant [43 x i8] c"abi_b.ritz:118:6: integer overflow in `+`\0A\00"
@.str.5 = private constant [43 x i8] c"abi_b.ritz:118:6: integer overflow in `+`\0A\00"
@.str.6 = private constant [8 x i8] c"b_pair\0A\00"
@.str.7 = private constant [44 x i8] c"abi_b.ritz:151:15: integer overflow in `*`\0A\00"
@.str.8 = private constant [44 x i8] c"abi_b.ritz:151:28: integer overflow in `*`\0A\00"
@.str.9 = private constant [9 x i8] c"b_mixed\0A\00"
@.str.10 = private constant [44 x i8] c"abi_b.ritz:158:16: integer overflow in `+`\0A\00"
@.str.11 = private constant [44 x i8] c"abi_b.ritz:158:28: integer overflow in `+`\0A\00"
@.str.12 = private constant [16 x i8] c"b_straddle_int\0A\00"
@.str.13 = private constant [44 x i8] c"abi_b.ritz:162:13: integer overflow in `+`\0A\00"
@.str.14 = private constant [44 x i8] c"abi_b.ritz:162:13: integer overflow in `+`\0A\00"
@.str.15 = private constant [44 x i8] c"abi_b.ritz:162:13: integer overflow in `+`\0A\00"
@.str.16 = private constant [44 x i8] c"abi_b.ritz:162:13: integer overflow in `+`\0A\00"
@.str.17 = private constant [43 x i8] c"abi_b.ritz:165:5: integer overflow in `+`\0A\00"
@.str.18 = private constant [18 x i8] c"b_straddle_float\0A\00"
@.str.19 = private constant [10 x i8] c"b_packed\0A\00"
@.str.20 = private constant [43 x i8] c"abi_b.ritz:179:6: integer overflow in `+`\0A\00"
@.str.21 = private constant [43 x i8] c"abi_b.ritz:179:6: integer overflow in `+`\0A\00"
@.str.22 = private constant [44 x i8] c"abi_b.ritz:182:22: integer overflow in `+`\0A\00"
@.str.23 = private constant [44 x i8] c"abi_b.ritz:182:32: integer overflow in `+`\0A\00"
@.str.24 = private constant [44 x i8] c"abi_b.ritz:185:21: integer overflow in `+`\0A\00"
@.str.25 = private constant [44 x i8] c"abi_b.ritz:185:31: integer overflow in `+`\0A\00"
@.str.26 = private constant [44 x i8] c"abi_b.ritz:185:41: integer overflow in `+`\0A\00"
@.str.27 = private constant [44 x i8] c"abi_b.ritz:200:37: integer overflow in `+`\0A\00"
@.str.28 = private constant [44 x i8] c"abi_b.ritz:200:59: integer overflow in `+`\0A\00"
@.str.29 = private constant [44 x i8] c"abi_b.ritz:200:81: integer overflow in `+`\0A\00"
@.str.30 = private constant [44 x i8] c"abi_b.ritz:203:37: integer overflow in `+`\0A\00"
@.str.31 = private constant [44 x i8] c"abi_b.ritz:203:59: integer overflow in `+`\0A\00"
@.str.32 = private constant [44 x i8] c"abi_b.ritz:203:81: integer overflow in `+`\0A\00"
@.str.33 = private constant [45 x i8] c"abi_b.ritz:203:103: integer overflow in `+`\0A\00"
@.str.34 = private constant [7 x i8] c"b_big\0A\00"
@.str.35 = private constant [43 x i8] c"abi_b.ritz:209:5: integer overflow in `+`\0A\00"
@.str.36 = private constant [12 x i8] c"b_big_wide\0A\00"
@.str.37 = private constant [44 x i8] c"abi_b.ritz:221:16: integer overflow in `*`\0A\00"
@.str.38 = private constant [11 x i8] c"b_calls_a\0A\00"
@.str.39 = private constant [44 x i8] c"abi_b.ritz:240:13: integer overflow in `+`\0A\00"
@.str.40 = private constant [44 x i8] c"abi_b.ritz:240:13: integer overflow in `+`\0A\00"
@.str.41 = private constant [44 x i8] c"abi_b.ritz:244:12: integer overflow in `+`\0A\00"
@.str.42 = private constant [44 x i8] c"abi_b.ritz:244:12: integer overflow in `+`\0A\00"
@.str.43 = private constant [44 x i8] c"abi_b.ritz:244:12: integer overflow in `+`\0A\00"
@.str.44 = private constant [44 x i8] c"abi_b.ritz:246:13: integer overflow in `+`\0A\00"
@.str.45 = private constant [44 x i8] c"abi_b.ritz:139:10: integer overflow in `+`\0A\00"
declare %Pair @a_pair(...) "no-builtins"
declare %Mixed @a_mixed(...) "no-builtins"
declare i64 @a_straddle_int(...) "no-builtins"
declare i64 @a_straddle_float(...) "no-builtins"
declare %Three @a_three(...) "no-builtins"
declare %D3 @a_d3(...) "no-builtins"
declare %V4 @a_v4(...) "no-builtins"
declare void @a_sret(...) "no-builtins"
declare i64 @rt_write(...) "no-builtins"
declare void @rt_hex(...) "no-builtins"

define internal void @__ritz_sret_copy(ptr %d, ptr %s, i64 %n) "no-builtins" {
entry:
  %z = icmp eq i64 %n, 0
  br i1 %z, label %done, label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %i1, %loop ]
  %sp = getelementptr i8, ptr %s, i64 %i
  %c = load i8, ptr %sp
  %dp = getelementptr i8, ptr %d, i64 %i
  store i8 %c, ptr %dp
  %i1 = add i64 %i, 1
  %more = icmp ult i64 %i1, %n
  br i1 %more, label %loop, label %done
done:
  ret void
}

define internal void @__ritz_sret_zero(ptr %d, i64 %n) "no-builtins" {
entry:
  %z = icmp eq i64 %n, 0
  br i1 %z, label %done, label %loop
loop:
  %i = phi i64 [ 0, %entry ], [ %i1, %loop ]
  %dp = getelementptr i8, ptr %d, i64 %i
  store i8 0, ptr %dp
  %i1 = add i64 %i, 1
  %more = icmp ult i64 %i1, %n
  br i1 %more, label %loop, label %done
done:
  ret void
}

declare { i8, i1 } @llvm.sadd.with.overflow.i8(i8, i8)
declare { i32, i1 } @llvm.sadd.with.overflow.i32(i32, i32)
declare { i64, i1 } @llvm.sadd.with.overflow.i64(i64, i64)
declare { i64, i1 } @llvm.uadd.with.overflow.i64(i64, i64)
declare { i32, i1 } @llvm.smul.with.overflow.i32(i32, i32)
declare { i64, i1 } @llvm.smul.with.overflow.i64(i64, i64)
define internal void @__ritz_overflow_trap(ptr %msg, i64 %len) cold noinline noreturn nounwind {
entry:
  %w = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 1, i64 2, ptr %msg, i64 %len)
  %x = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1)
  unreachable
}
