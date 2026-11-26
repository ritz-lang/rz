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
%LanesA = type {i64}
%Span$u8 = type {ptr, i64}
%StrView = type {ptr, i64}
%V4 = type {<4 x i32>, <4 x i32>, <4 x i32>, <4 x i32>}
%V5 = type {<4 x i32>, <4 x i32>, <4 x i32>, <4 x i32>, <4 x i32>}
%BigWide = type {[40 x i64], <8 x i32>}





define void @say__1938ee70(%StrView %s.arg) alignstack(16) "no-builtins" {
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

define i64 @bits64__1938ee70(double %x.arg) alignstack(16) "no-builtins" {
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

define i64 @bits32__1938ee70(float %x.arg) alignstack(16) "no-builtins" {
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

define <4 x i32> @vec_of__1938ee70(i32 %base.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.0, i64 42)
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
  call void @__ritz_overflow_trap(ptr @.str.1, i64 42)
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
  call void @__ritz_overflow_trap(ptr @.str.2, i64 42)
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

define i64 @vec_sum__1938ee70(<4 x i32> %v.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.3, i64 41)
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
  call void @__ritz_overflow_trap(ptr @.str.4, i64 41)
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
  call void @__ritz_overflow_trap(ptr @.str.5, i64 41)
  unreachable
L5:
  ret i64 %.32
}

define %Pair @a_pair(%Pair %p.arg) alignstack(16) "no-builtins" {
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
  call void @say__1938ee70(%StrView %.8)
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
  %.20 = getelementptr %Pair, ptr %.1, i32 0, i32 0
  %.21 = load i32, ptr %.20
  %.22 = sext i32 %.21 to i64
  %.23 = getelementptr %Pair, ptr %.1, i32 0, i32 1
  %.24 = load i32, ptr %.23
  %.25 = sext i32 %.24 to i64
  %.26 = trunc i64 %.22 to i32
  %.27 = trunc i64 %.25 to i32
  %.28 = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %.26, i32 %.27)
  %.29 = extractvalue { i32, i1 } %.28, 0
  %.30 = extractvalue { i32, i1 } %.28, 1
  br i1 %.30, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.7, i64 42)
  unreachable
L1:
  %.31 = sext i32 %.29 to i64
  %.32 = getelementptr %Pair, ptr %.19, i32 0, i32 0
  %.33 = trunc i64 %.31 to i32
  store i32 %.33, ptr %.32
  %.34 = getelementptr %Pair, ptr %.1, i32 0, i32 0
  %.35 = load i32, ptr %.34
  %.36 = sext i32 %.35 to i64
  %.37 = getelementptr %Pair, ptr %.1, i32 0, i32 1
  %.38 = load i32, ptr %.37
  %.39 = sext i32 %.38 to i64
  %.40 = trunc i64 %.36 to i32
  %.41 = trunc i64 %.39 to i32
  %.42 = call { i32, i1 } @llvm.ssub.with.overflow.i32(i32 %.40, i32 %.41)
  %.43 = extractvalue { i32, i1 } %.42, 0
  %.44 = extractvalue { i32, i1 } %.42, 1
  br i1 %.44, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.8, i64 42)
  unreachable
L3:
  %.45 = sext i32 %.43 to i64
  %.46 = getelementptr %Pair, ptr %.19, i32 0, i32 1
  %.47 = trunc i64 %.45 to i32
  store i32 %.47, ptr %.46
  %.48 = load %Pair, ptr %.19
  ret %Pair %.48
}

define %Mixed @a_mixed(%Mixed %m.arg) alignstack(16) "no-builtins" {
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
  call void @say__1938ee70(%StrView %.8)
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
  %.18 = call i64 @bits32__1938ee70(float %.17)
  call void @rt_hex(i64 %.18)
  %.20 = getelementptr %Mixed, ptr %.1, i32 0, i32 0
  %.21 = load i8, ptr %.20
  %.22 = sext i8 %.21 to i64
  %.23 = add i64 0, 2
  %.24 = trunc i64 %.22 to i8
  %.25 = trunc i64 %.23 to i8
  %.26 = call { i8, i1 } @llvm.smul.with.overflow.i8(i8 %.24, i8 %.25)
  %.27 = extractvalue { i8, i1 } %.26, 0
  %.28 = extractvalue { i8, i1 } %.26, 1
  br i1 %.28, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.10, i64 42)
  unreachable
L1:
  %.29 = sext i8 %.27 to i64
  %.30 = getelementptr %Mixed, ptr %.19, i32 0, i32 0
  %.31 = trunc i64 %.29 to i8
  store i8 %.31, ptr %.30
  %.32 = getelementptr %Mixed, ptr %.1, i32 0, i32 1
  %.33 = load i64, ptr %.32
  %.34 = add i64 0, 2
  %.35 = call { i64, i1 } @llvm.smul.with.overflow.i64(i64 %.33, i64 %.34)
  %.36 = extractvalue { i64, i1 } %.35, 0
  %.37 = extractvalue { i64, i1 } %.35, 1
  br i1 %.37, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.11, i64 42)
  unreachable
L3:
  %.38 = getelementptr %Mixed, ptr %.19, i32 0, i32 1
  store i64 %.36, ptr %.38
  %.39 = getelementptr %Mixed, ptr %.1, i32 0, i32 2
  %.40 = load float, ptr %.39
  %.41 = fadd double 0.0, 1.0
  %.42 = fptrunc double %.41 to float
  %.43 = fadd float %.40, %.42
  %.44 = getelementptr %Mixed, ptr %.19, i32 0, i32 2
  store float %.43, ptr %.44
  %.45 = load %Mixed, ptr %.19
  ret %Mixed %.45
}

define i64 @a_straddle_int(i64 %a.arg, i64 %b.arg, i64 %c.arg, i64 %d.arg, i64 %e.arg, %Two %p.arg) alignstack(16) "no-builtins" {
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
  call void @say__1938ee70(%StrView %.13)
  %.14 = load i64, ptr %.1
  %.15 = load i64, ptr %.2
  %.16 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.14, i64 %.15)
  %.17 = extractvalue { i64, i1 } %.16, 0
  %.18 = extractvalue { i64, i1 } %.16, 1
  br i1 %.18, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.13, i64 42)
  unreachable
L1:
  %.19 = load i64, ptr %.3
  %.20 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.17, i64 %.19)
  %.21 = extractvalue { i64, i1 } %.20, 0
  %.22 = extractvalue { i64, i1 } %.20, 1
  br i1 %.22, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.14, i64 42)
  unreachable
L3:
  %.23 = load i64, ptr %.4
  %.24 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.21, i64 %.23)
  %.25 = extractvalue { i64, i1 } %.24, 0
  %.26 = extractvalue { i64, i1 } %.24, 1
  br i1 %.26, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.15, i64 42)
  unreachable
L5:
  %.27 = load i64, ptr %.5
  %.28 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.25, i64 %.27)
  %.29 = extractvalue { i64, i1 } %.28, 0
  %.30 = extractvalue { i64, i1 } %.28, 1
  br i1 %.30, label %L6, label %L7
L6:
  call void @__ritz_overflow_trap(ptr @.str.16, i64 42)
  unreachable
L7:
  call void @rt_hex(i64 %.29)
  %.31 = getelementptr %Two, ptr %.6, i32 0, i32 0
  %.32 = load i64, ptr %.31
  %.33 = getelementptr %Two, ptr %.6, i32 0, i32 1
  %.34 = load i64, ptr %.33
  %.35 = call { i64, i1 } @llvm.smul.with.overflow.i64(i64 %.32, i64 %.34)
  %.36 = extractvalue { i64, i1 } %.35, 0
  %.37 = extractvalue { i64, i1 } %.35, 1
  br i1 %.37, label %L8, label %L9
L8:
  call void @__ritz_overflow_trap(ptr @.str.17, i64 41)
  unreachable
L9:
  ret i64 %.36
}

define i64 @a_straddle_float(double %a.arg, double %b.arg, double %c.arg, double %d.arg, double %e.arg, double %f.arg, double %g.arg, %D2 %p.arg) alignstack(16) "no-builtins" {
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
  call void @say__1938ee70(%StrView %.15)
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
  %.29 = call i64 @bits64__1938ee70(double %.28)
  call void @rt_hex(i64 %.29)
  %.30 = getelementptr %D2, ptr %.8, i32 0, i32 0
  %.31 = load double, ptr %.30
  %.32 = getelementptr %D2, ptr %.8, i32 0, i32 1
  %.33 = load double, ptr %.32
  %.34 = fmul double %.31, %.33
  %.35 = call i64 @bits64__1938ee70(double %.34)
  ret i64 %.35
}

define %Three @a_three(i64 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca %Three
  store i64 %x.arg, ptr %.1
  %.3 = load i64, ptr %.1
  %.4 = add i64 0, 3
  %.5 = call { i64, i1 } @llvm.smul.with.overflow.i64(i64 %.3, i64 %.4)
  %.6 = extractvalue { i64, i1 } %.5, 0
  %.7 = extractvalue { i64, i1 } %.5, 1
  br i1 %.7, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.19, i64 42)
  unreachable
L1:
  %.8 = getelementptr %Three, ptr %.2, i32 0, i32 0
  store i64 %.6, ptr %.8
  %.9 = load i64, ptr %.1
  %.10 = add i64 0, 5
  %.11 = call { i64, i1 } @llvm.smul.with.overflow.i64(i64 %.9, i64 %.10)
  %.12 = extractvalue { i64, i1 } %.11, 0
  %.13 = extractvalue { i64, i1 } %.11, 1
  br i1 %.13, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.20, i64 42)
  unreachable
L3:
  %.14 = getelementptr %Three, ptr %.2, i32 0, i32 1
  store i64 %.12, ptr %.14
  %.15 = load i64, ptr %.1
  %.16 = add i64 0, 7
  %.17 = call { i64, i1 } @llvm.smul.with.overflow.i64(i64 %.15, i64 %.16)
  %.18 = extractvalue { i64, i1 } %.17, 0
  %.19 = extractvalue { i64, i1 } %.17, 1
  br i1 %.19, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.21, i64 42)
  unreachable
L5:
  %.20 = getelementptr %Three, ptr %.2, i32 0, i32 2
  store i64 %.18, ptr %.20
  %.21 = load %Three, ptr %.2
  ret %Three %.21
}

define %D3 @a_d3(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  %.2 = alloca %D3
  store double %x.arg, ptr %.1
  %.3 = load double, ptr %.1
  %.4 = getelementptr %D3, ptr %.2, i32 0, i32 0
  store double %.3, ptr %.4
  %.5 = load double, ptr %.1
  %.6 = fadd double 0.0, 2.0
  %.7 = fmul double %.5, %.6
  %.8 = getelementptr %D3, ptr %.2, i32 0, i32 1
  store double %.7, ptr %.8
  %.9 = load double, ptr %.1
  %.10 = fadd double 0.0, 4.0
  %.11 = fmul double %.9, %.10
  %.12 = getelementptr %D3, ptr %.2, i32 0, i32 2
  store double %.11, ptr %.12
  %.13 = load %D3, ptr %.2
  ret %D3 %.13
}

define %V4 @a_v4(i32 %base.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca %V4
  store i32 %base.arg, ptr %.1
  %.3 = load i32, ptr %.1
  %.4 = sext i32 %.3 to i64
  %.5 = trunc i64 %.4 to i32
  %.6 = call <4 x i32> @vec_of__1938ee70(i32 %.5)
  %.7 = getelementptr %V4, ptr %.2, i32 0, i32 0
  store <4 x i32> %.6, ptr %.7
  %.8 = load i32, ptr %.1
  %.9 = sext i32 %.8 to i64
  %.10 = add i64 0, 2
  %.11 = trunc i64 %.9 to i32
  %.12 = trunc i64 %.10 to i32
  %.13 = call { i32, i1 } @llvm.smul.with.overflow.i32(i32 %.11, i32 %.12)
  %.14 = extractvalue { i32, i1 } %.13, 0
  %.15 = extractvalue { i32, i1 } %.13, 1
  br i1 %.15, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.22, i64 42)
  unreachable
L1:
  %.16 = sext i32 %.14 to i64
  %.17 = trunc i64 %.16 to i32
  %.18 = call <4 x i32> @vec_of__1938ee70(i32 %.17)
  %.19 = getelementptr %V4, ptr %.2, i32 0, i32 1
  store <4 x i32> %.18, ptr %.19
  %.20 = load i32, ptr %.1
  %.21 = sext i32 %.20 to i64
  %.22 = add i64 0, 3
  %.23 = trunc i64 %.21 to i32
  %.24 = trunc i64 %.22 to i32
  %.25 = call { i32, i1 } @llvm.smul.with.overflow.i32(i32 %.23, i32 %.24)
  %.26 = extractvalue { i32, i1 } %.25, 0
  %.27 = extractvalue { i32, i1 } %.25, 1
  br i1 %.27, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.23, i64 42)
  unreachable
L3:
  %.28 = sext i32 %.26 to i64
  %.29 = trunc i64 %.28 to i32
  %.30 = call <4 x i32> @vec_of__1938ee70(i32 %.29)
  %.31 = getelementptr %V4, ptr %.2, i32 0, i32 2
  store <4 x i32> %.30, ptr %.31
  %.32 = load i32, ptr %.1
  %.33 = sext i32 %.32 to i64
  %.34 = add i64 0, 4
  %.35 = trunc i64 %.33 to i32
  %.36 = trunc i64 %.34 to i32
  %.37 = call { i32, i1 } @llvm.smul.with.overflow.i32(i32 %.35, i32 %.36)
  %.38 = extractvalue { i32, i1 } %.37, 0
  %.39 = extractvalue { i32, i1 } %.37, 1
  br i1 %.39, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.24, i64 42)
  unreachable
L5:
  %.40 = sext i32 %.38 to i64
  %.41 = trunc i64 %.40 to i32
  %.42 = call <4 x i32> @vec_of__1938ee70(i32 %.41)
  %.43 = getelementptr %V4, ptr %.2, i32 0, i32 3
  store <4 x i32> %.42, ptr %.43
  %.44 = load %V4, ptr %.2
  ret %V4 %.44
}

define void @a_sret(ptr sret(%Big) %ret.sret, i64 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca %Big
  store i64 %x.arg, ptr %.1
  %.3 = getelementptr %Big, ptr %.2, i32 0, i32 0
  call void @__ritz_sret_zero(ptr %.3, i64 320)
  %.4 = getelementptr %Big, ptr %.2, i32 0, i32 0
  %.5 = add i64 0, 0
  %.6 = load i64, ptr %.1
  %.7 = add i64 0, 1
  %.8 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.6, i64 %.7)
  %.9 = extractvalue { i64, i1 } %.8, 0
  %.10 = extractvalue { i64, i1 } %.8, 1
  br i1 %.10, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.25, i64 42)
  unreachable
L1:
  %.11 = getelementptr [40 x i64], ptr %.4, i64 0, i64 %.5
  store i64 %.9, ptr %.11
  %.12 = getelementptr %Big, ptr %.2, i32 0, i32 0
  %.13 = add i64 0, 39
  %.14 = load i64, ptr %.1
  %.15 = add i64 0, 2
  %.16 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.14, i64 %.15)
  %.17 = extractvalue { i64, i1 } %.16, 0
  %.18 = extractvalue { i64, i1 } %.16, 1
  br i1 %.18, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.26, i64 42)
  unreachable
L3:
  %.19 = getelementptr [40 x i64], ptr %.12, i64 0, i64 %.13
  store i64 %.17, ptr %.19
  call void @__ritz_sret_copy(ptr %ret.sret, ptr %.2, i64 ptrtoint (ptr getelementptr (%Big, ptr null, i32 1) to i64))
  ret void
}

define i64 @internal_wide__1938ee70() alignstack(16) "no-builtins" {
entry:
  %.1 = alloca %LanesA
  %.4 = alloca [8 x i32]
  %.29 = alloca <8 x i32>
  %.2 = add i64 0, 3
  %.3 = getelementptr %LanesA, ptr %.1, i32 0, i32 0
  store i64 %.2, ptr %.3
  %.5 = add i64 0, 7
  %.6 = getelementptr [8 x i32], ptr %.4, i64 0, i64 0
  %.7 = trunc i64 %.5 to i32
  store i32 %.7, ptr %.6
  %.8 = add i64 0, 7
  %.9 = getelementptr [8 x i32], ptr %.4, i64 0, i64 1
  %.10 = trunc i64 %.8 to i32
  store i32 %.10, ptr %.9
  %.11 = add i64 0, 7
  %.12 = getelementptr [8 x i32], ptr %.4, i64 0, i64 2
  %.13 = trunc i64 %.11 to i32
  store i32 %.13, ptr %.12
  %.14 = add i64 0, 7
  %.15 = getelementptr [8 x i32], ptr %.4, i64 0, i64 3
  %.16 = trunc i64 %.14 to i32
  store i32 %.16, ptr %.15
  %.17 = add i64 0, 7
  %.18 = getelementptr [8 x i32], ptr %.4, i64 0, i64 4
  %.19 = trunc i64 %.17 to i32
  store i32 %.19, ptr %.18
  %.20 = add i64 0, 7
  %.21 = getelementptr [8 x i32], ptr %.4, i64 0, i64 5
  %.22 = trunc i64 %.20 to i32
  store i32 %.22, ptr %.21
  %.23 = add i64 0, 7
  %.24 = getelementptr [8 x i32], ptr %.4, i64 0, i64 6
  %.25 = trunc i64 %.23 to i32
  store i32 %.25, ptr %.24
  %.26 = add i64 0, 8
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
  %.36 = call i64 @LanesA_twice(ptr %.1, <8 x i32> %.35)
  ret i64 %.36
}

define i32 @main() alignstack(16) "no-builtins" {
entry:
  %.8 = alloca %Pair
  %.9 = alloca %Pair  ; rvalue struct literal
  %.28 = alloca %Mixed
  %.29 = alloca %Mixed  ; rvalue struct literal
  %.56 = alloca %Two  ; rvalue struct literal
  %.70 = alloca %D2  ; rvalue struct literal
  %.77 = alloca %Three
  %.86 = alloca %Four
  %.106 = alloca %D2
  %.115 = alloca %D3
  %.121 = alloca %D4
  %.130 = alloca %D5
  %.136 = alloca %V4
  %.149 = alloca %V5
  %.162 = alloca %Big
  %.173 = alloca %Big  ; #1739 byval arg
  %.175 = alloca %Packed  ; rvalue struct literal
  %.187 = alloca [8 x i32]
  %.212 = alloca <8 x i32>
  %.218 = alloca %BigWide
  %.227 = alloca %BigWide  ; #1739 byval arg
  %.229 = alloca %Big
  %.231 = alloca %Big
  %.1 = getelementptr [11 x i8], ptr @.str.27, i64 0, i64 0
  %.2 = insertvalue %Span$u8 undef, ptr %.1, 0
  %.3 = insertvalue %Span$u8 %.2, i64 10, 1
  %.4 = extractvalue %Span$u8 %.3, 0
  %.5 = extractvalue %Span$u8 %.3, 1
  %.6 = insertvalue %StrView undef, ptr %.4, 0
  %.7 = insertvalue %StrView %.6, i64 %.5, 1
  call void @say__1938ee70(%StrView %.7)
  %.10 = add i64 0, 1
  %.11 = getelementptr %Pair, ptr %.9, i32 0, i32 0
  %.12 = trunc i64 %.10 to i32
  store i32 %.12, ptr %.11
  %.13 = add i64 0, 2
  %.14 = getelementptr %Pair, ptr %.9, i32 0, i32 1
  %.15 = trunc i64 %.13 to i32
  store i32 %.15, ptr %.14
  %.16 = load %Pair, ptr %.9
  %.17 = call %Pair @b_pair(%Pair %.16)
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
  %.30 = add i64 0, 3
  %.31 = sub i64 0, %.30
  %.32 = getelementptr %Mixed, ptr %.29, i32 0, i32 0
  %.33 = trunc i64 %.31 to i8
  store i8 %.33, ptr %.32
  %.34 = add i64 0, 1234567890123
  %.35 = getelementptr %Mixed, ptr %.29, i32 0, i32 1
  store i64 %.34, ptr %.35
  %.36 = fadd double 0.0, 1.25
  %.37 = getelementptr %Mixed, ptr %.29, i32 0, i32 2
  %.38 = fptrunc double %.36 to float
  store float %.38, ptr %.37
  %.39 = load %Mixed, ptr %.29
  %.40 = call %Mixed @b_mixed(%Mixed %.39)
  store %Mixed %.40, ptr %.28
  %.41 = getelementptr %Mixed, ptr %.28, i32 0, i32 0
  %.42 = load i8, ptr %.41
  %.43 = sext i8 %.42 to i64
  %.44 = trunc i64 %.43 to i8
  %.45 = zext i8 %.44 to i64
  call void @rt_hex(i64 %.45)
  %.46 = getelementptr %Mixed, ptr %.28, i32 0, i32 1
  %.47 = load i64, ptr %.46
  call void @rt_hex(i64 %.47)
  %.48 = getelementptr %Mixed, ptr %.28, i32 0, i32 2
  %.49 = load float, ptr %.48
  %.50 = call i64 @bits32__1938ee70(float %.49)
  call void @rt_hex(i64 %.50)
  %.51 = add i64 0, 1
  %.52 = add i64 0, 2
  %.53 = add i64 0, 3
  %.54 = add i64 0, 4
  %.55 = add i64 0, 5
  %.57 = add i64 0, 6
  %.58 = getelementptr %Two, ptr %.56, i32 0, i32 0
  store i64 %.57, ptr %.58
  %.59 = add i64 0, 7
  %.60 = getelementptr %Two, ptr %.56, i32 0, i32 1
  store i64 %.59, ptr %.60
  %.61 = load %Two, ptr %.56
  %.62 = call i64 @b_straddle_int(i64 %.51, i64 %.52, i64 %.53, i64 %.54, i64 %.55, %Two %.61)
  call void @rt_hex(i64 %.62)
  %.63 = fadd double 0.0, 0.5
  %.64 = fadd double 0.0, 1.5
  %.65 = fadd double 0.0, 2.5
  %.66 = fadd double 0.0, 3.5
  %.67 = fadd double 0.0, 4.5
  %.68 = fadd double 0.0, 5.5
  %.69 = fadd double 0.0, 6.5
  %.71 = fadd double 0.0, 7.25
  %.72 = getelementptr %D2, ptr %.70, i32 0, i32 0
  store double %.71, ptr %.72
  %.73 = fadd double 0.0, 8.75
  %.74 = getelementptr %D2, ptr %.70, i32 0, i32 1
  store double %.73, ptr %.74
  %.75 = load %D2, ptr %.70
  %.76 = call i64 @b_straddle_float(double %.63, double %.64, double %.65, double %.66, double %.67, double %.68, double %.69, %D2 %.75)
  call void @rt_hex(i64 %.76)
  %.78 = add i64 0, 10
  %.79 = call %Three @b_three(i64 %.78)
  store %Three %.79, ptr %.77
  %.80 = getelementptr %Three, ptr %.77, i32 0, i32 0
  %.81 = load i64, ptr %.80
  call void @rt_hex(i64 %.81)
  %.82 = getelementptr %Three, ptr %.77, i32 0, i32 1
  %.83 = load i64, ptr %.82
  call void @rt_hex(i64 %.83)
  %.84 = getelementptr %Three, ptr %.77, i32 0, i32 2
  %.85 = load i64, ptr %.84
  call void @rt_hex(i64 %.85)
  %.87 = add i64 0, 20
  %.88 = call %Four @b_four(i64 %.87)
  store %Four %.88, ptr %.86
  %.89 = getelementptr %Four, ptr %.86, i32 0, i32 0
  %.90 = load i64, ptr %.89
  %.91 = getelementptr %Four, ptr %.86, i32 0, i32 1
  %.92 = load i64, ptr %.91
  %.93 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.90, i64 %.92)
  %.94 = extractvalue { i64, i1 } %.93, 0
  %.95 = extractvalue { i64, i1 } %.93, 1
  br i1 %.95, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.28, i64 43)
  unreachable
L1:
  %.96 = getelementptr %Four, ptr %.86, i32 0, i32 2
  %.97 = load i64, ptr %.96
  %.98 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.94, i64 %.97)
  %.99 = extractvalue { i64, i1 } %.98, 0
  %.100 = extractvalue { i64, i1 } %.98, 1
  br i1 %.100, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.29, i64 43)
  unreachable
L3:
  %.101 = getelementptr %Four, ptr %.86, i32 0, i32 3
  %.102 = load i64, ptr %.101
  %.103 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.99, i64 %.102)
  %.104 = extractvalue { i64, i1 } %.103, 0
  %.105 = extractvalue { i64, i1 } %.103, 1
  br i1 %.105, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.30, i64 43)
  unreachable
L5:
  call void @rt_hex(i64 %.104)
  %.107 = fadd double 0.0, 1.0
  %.108 = call %D2 @b_d2(double %.107)
  store %D2 %.108, ptr %.106
  %.109 = getelementptr %D2, ptr %.106, i32 0, i32 0
  %.110 = load double, ptr %.109
  %.111 = call i64 @bits64__1938ee70(double %.110)
  call void @rt_hex(i64 %.111)
  %.112 = getelementptr %D2, ptr %.106, i32 0, i32 1
  %.113 = load double, ptr %.112
  %.114 = call i64 @bits64__1938ee70(double %.113)
  call void @rt_hex(i64 %.114)
  %.116 = fadd double 0.0, 2.0
  %.117 = call %D3 @b_d3(double %.116)
  store %D3 %.117, ptr %.115
  %.118 = getelementptr %D3, ptr %.115, i32 0, i32 2
  %.119 = load double, ptr %.118
  %.120 = call i64 @bits64__1938ee70(double %.119)
  call void @rt_hex(i64 %.120)
  %.122 = fadd double 0.0, 3.0
  %.123 = call %D4 @b_d4(double %.122)
  store %D4 %.123, ptr %.121
  %.124 = getelementptr %D4, ptr %.121, i32 0, i32 2
  %.125 = load double, ptr %.124
  %.126 = call i64 @bits64__1938ee70(double %.125)
  call void @rt_hex(i64 %.126)
  %.127 = getelementptr %D4, ptr %.121, i32 0, i32 3
  %.128 = load double, ptr %.127
  %.129 = call i64 @bits64__1938ee70(double %.128)
  call void @rt_hex(i64 %.129)
  %.131 = fadd double 0.0, 4.0
  %.132 = call %D5 @b_d5(double %.131)
  store %D5 %.132, ptr %.130
  %.133 = getelementptr %D5, ptr %.130, i32 0, i32 4
  %.134 = load double, ptr %.133
  %.135 = call i64 @bits64__1938ee70(double %.134)
  call void @rt_hex(i64 %.135)
  %.137 = add i64 0, 1
  %.138 = trunc i64 %.137 to i32
  %.139 = call %V4 @b_v4(i32 %.138)
  store %V4 %.139, ptr %.136
  %.140 = getelementptr %V4, ptr %.136, i32 0, i32 0
  %.141 = load <4 x i32>, ptr %.140
  %.142 = call i64 @vec_sum__1938ee70(<4 x i32> %.141)
  %.143 = getelementptr %V4, ptr %.136, i32 0, i32 3
  %.144 = load <4 x i32>, ptr %.143
  %.145 = call i64 @vec_sum__1938ee70(<4 x i32> %.144)
  %.146 = call { i64, i1 } @llvm.uadd.with.overflow.i64(i64 %.142, i64 %.145)
  %.147 = extractvalue { i64, i1 } %.146, 0
  %.148 = extractvalue { i64, i1 } %.146, 1
  br i1 %.148, label %L6, label %L7
L6:
  call void @__ritz_overflow_trap(ptr @.str.31, i64 43)
  unreachable
L7:
  call void @rt_hex(i64 %.147)
  %.150 = add i64 0, 2
  %.151 = trunc i64 %.150 to i32
  %.152 = call %V5 @b_v5(i32 %.151)
  store %V5 %.152, ptr %.149
  %.153 = getelementptr %V5, ptr %.149, i32 0, i32 0
  %.154 = load <4 x i32>, ptr %.153
  %.155 = call i64 @vec_sum__1938ee70(<4 x i32> %.154)
  %.156 = getelementptr %V5, ptr %.149, i32 0, i32 4
  %.157 = load <4 x i32>, ptr %.156
  %.158 = call i64 @vec_sum__1938ee70(<4 x i32> %.157)
  %.159 = call { i64, i1 } @llvm.uadd.with.overflow.i64(i64 %.155, i64 %.158)
  %.160 = extractvalue { i64, i1 } %.159, 0
  %.161 = extractvalue { i64, i1 } %.159, 1
  br i1 %.161, label %L8, label %L9
L8:
  call void @__ritz_overflow_trap(ptr @.str.32, i64 43)
  unreachable
L9:
  call void @rt_hex(i64 %.160)
  %.163 = getelementptr %Big, ptr %.162, i32 0, i32 0
  call void @__ritz_sret_zero(ptr %.163, i64 320)
  %.164 = getelementptr %Big, ptr %.162, i32 0, i32 0
  %.165 = add i64 0, 0
  %.166 = add i64 0, 11
  %.167 = getelementptr [40 x i64], ptr %.164, i64 0, i64 %.165
  store i64 %.166, ptr %.167
  %.168 = getelementptr %Big, ptr %.162, i32 0, i32 0
  %.169 = add i64 0, 39
  %.170 = add i64 0, 22
  %.171 = getelementptr [40 x i64], ptr %.168, i64 0, i64 %.169
  store i64 %.170, ptr %.171
  call void @__ritz_sret_copy(ptr %.173, ptr %.162, i64 ptrtoint (ptr getelementptr (%Big, ptr null, i32 1) to i64))
  %.174 = call i64 @b_big(ptr byval(%Big) align 8 %.173)
  call void @rt_hex(i64 %.174)
  %.176 = add i64 0, 1
  %.177 = getelementptr %Packed, ptr %.175, i32 0, i32 0
  %.178 = trunc i64 %.176 to i8
  store i8 %.178, ptr %.177, align 1
  %.179 = add i64 0, 16909060
  %.180 = getelementptr %Packed, ptr %.175, i32 0, i32 1
  %.181 = trunc i64 %.179 to i32
  store i32 %.181, ptr %.180, align 1
  %.182 = add i64 0, 1286
  %.183 = getelementptr %Packed, ptr %.175, i32 0, i32 2
  %.184 = trunc i64 %.182 to i16
  store i16 %.184, ptr %.183, align 1
  %.185 = load %Packed, ptr %.175
  %.186 = call i64 @b_packed(%Packed %.185)
  call void @rt_hex(i64 %.186)
  %.188 = add i64 0, 41
  %.189 = getelementptr [8 x i32], ptr %.187, i64 0, i64 0
  %.190 = trunc i64 %.188 to i32
  store i32 %.190, ptr %.189
  %.191 = add i64 0, 41
  %.192 = getelementptr [8 x i32], ptr %.187, i64 0, i64 1
  %.193 = trunc i64 %.191 to i32
  store i32 %.193, ptr %.192
  %.194 = add i64 0, 41
  %.195 = getelementptr [8 x i32], ptr %.187, i64 0, i64 2
  %.196 = trunc i64 %.194 to i32
  store i32 %.196, ptr %.195
  %.197 = add i64 0, 41
  %.198 = getelementptr [8 x i32], ptr %.187, i64 0, i64 3
  %.199 = trunc i64 %.197 to i32
  store i32 %.199, ptr %.198
  %.200 = add i64 0, 41
  %.201 = getelementptr [8 x i32], ptr %.187, i64 0, i64 4
  %.202 = trunc i64 %.200 to i32
  store i32 %.202, ptr %.201
  %.203 = add i64 0, 41
  %.204 = getelementptr [8 x i32], ptr %.187, i64 0, i64 5
  %.205 = trunc i64 %.203 to i32
  store i32 %.205, ptr %.204
  %.206 = add i64 0, 41
  %.207 = getelementptr [8 x i32], ptr %.187, i64 0, i64 6
  %.208 = trunc i64 %.206 to i32
  store i32 %.208, ptr %.207
  %.209 = add i64 0, 42
  %.210 = getelementptr [8 x i32], ptr %.187, i64 0, i64 7
  %.211 = trunc i64 %.209 to i32
  store i32 %.211, ptr %.210
  %.213 = add i64 0, 0
  %.214 = getelementptr [8 x i32], ptr %.187, i64 0, i64 %.213
  %.215 = ptrtoint ptr %.214 to i64
  %.216 = inttoptr i64 %.215 to ptr  ; simd_load: ptr cast
  %.217 = load <8 x i32>, ptr %.216, align 1
  store <8 x i32> %.217, ptr %.212
  %.219 = getelementptr %BigWide, ptr %.218, i32 0, i32 0
  call void @__ritz_sret_zero(ptr %.219, i64 320)
  %.220 = load <8 x i32>, ptr %.212
  %.221 = getelementptr %BigWide, ptr %.218, i32 0, i32 1
  store <8 x i32> %.220, ptr %.221
  %.222 = getelementptr %BigWide, ptr %.218, i32 0, i32 0
  %.223 = add i64 0, 1
  %.224 = add i64 0, 33
  %.225 = getelementptr [40 x i64], ptr %.222, i64 0, i64 %.223
  store i64 %.224, ptr %.225
  call void @__ritz_sret_copy(ptr %.227, ptr %.218, i64 ptrtoint (ptr getelementptr (%BigWide, ptr null, i32 1) to i64))
  %.228 = call i64 @b_big_wide(ptr byval(%BigWide) align 32 %.227)
  call void @rt_hex(i64 %.228)
  %.230 = add i64 0, 5
  call void @b_sret(ptr sret(%Big) %.231, i64 %.230)
  call void @__ritz_sret_copy(ptr %.229, ptr %.231, i64 ptrtoint (ptr getelementptr (%Big, ptr null, i32 1) to i64))
  %.233 = getelementptr %Big, ptr %.229, i32 0, i32 0
  %.234 = add i64 0, 0
  %.235 = getelementptr [40 x i64], ptr %.233, i64 0, i64 %.234
  %.236 = load i64, ptr %.235
  %.237 = getelementptr %Big, ptr %.229, i32 0, i32 0
  %.238 = add i64 0, 39
  %.239 = getelementptr [40 x i64], ptr %.237, i64 0, i64 %.238
  %.240 = load i64, ptr %.239
  %.241 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.236, i64 %.240)
  %.242 = extractvalue { i64, i1 } %.241, 0
  %.243 = extractvalue { i64, i1 } %.241, 1
  br i1 %.243, label %L10, label %L11
L10:
  call void @__ritz_overflow_trap(ptr @.str.33, i64 43)
  unreachable
L11:
  call void @rt_hex(i64 %.242)
  %.244 = call i64 @b_aligned()
  call void @rt_hex(i64 %.244)
  %.245 = call i64 @b_internal_wide()
  call void @rt_hex(i64 %.245)
  %.246 = call i64 @internal_wide__1938ee70()
  call void @rt_hex(i64 %.246)
  call void @b_calls_a()
  %.247 = add i64 0, 0
  %.248 = trunc i64 %.247 to i32
  ret i32 %.248
}

define internal i64 @LanesA_lane7(ptr %self.arg, <8 x i32> %v.arg) alignstack(16) "no-builtins" {
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

define internal i64 @LanesA_twice(ptr %self.arg, <8 x i32> %v.arg) alignstack(16) "no-builtins" {
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
  %.11 = getelementptr %LanesA, ptr %.10, i32 0, i32 0
  %.12 = load i64, ptr %.11
  %.13 = call { i64, i1 } @llvm.uadd.with.overflow.i64(i64 %.9, i64 %.12)
  %.14 = extractvalue { i64, i1 } %.13, 0
  %.15 = extractvalue { i64, i1 } %.13, 1
  br i1 %.15, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.34, i64 42)
  unreachable
L1:
  ret i64 %.14
}


@.str.0 = private constant [43 x i8] c"abi_a.ritz:26:29: integer overflow in `+`\0A\00"
@.str.1 = private constant [43 x i8] c"abi_a.ritz:26:39: integer overflow in `+`\0A\00"
@.str.2 = private constant [43 x i8] c"abi_a.ritz:26:49: integer overflow in `+`\0A\00"
@.str.3 = private constant [42 x i8] c"abi_a.ritz:32:6: integer overflow in `+`\0A\00"
@.str.4 = private constant [42 x i8] c"abi_a.ritz:32:6: integer overflow in `+`\0A\00"
@.str.5 = private constant [42 x i8] c"abi_a.ritz:32:6: integer overflow in `+`\0A\00"
@.str.6 = private constant [8 x i8] c"a_pair\0A\00"
@.str.7 = private constant [43 x i8] c"abi_a.ritz:51:15: integer overflow in `+`\0A\00"
@.str.8 = private constant [43 x i8] c"abi_a.ritz:51:29: integer overflow in `-`\0A\00"
@.str.9 = private constant [9 x i8] c"a_mixed\0A\00"
@.str.10 = private constant [43 x i8] c"abi_a.ritz:58:16: integer overflow in `*`\0A\00"
@.str.11 = private constant [43 x i8] c"abi_a.ritz:58:28: integer overflow in `*`\0A\00"
@.str.12 = private constant [16 x i8] c"a_straddle_int\0A\00"
@.str.13 = private constant [43 x i8] c"abi_a.ritz:62:13: integer overflow in `+`\0A\00"
@.str.14 = private constant [43 x i8] c"abi_a.ritz:62:13: integer overflow in `+`\0A\00"
@.str.15 = private constant [43 x i8] c"abi_a.ritz:62:13: integer overflow in `+`\0A\00"
@.str.16 = private constant [43 x i8] c"abi_a.ritz:62:13: integer overflow in `+`\0A\00"
@.str.17 = private constant [42 x i8] c"abi_a.ritz:63:5: integer overflow in `*`\0A\00"
@.str.18 = private constant [18 x i8] c"a_straddle_float\0A\00"
@.str.19 = private constant [43 x i8] c"abi_a.ritz:71:16: integer overflow in `*`\0A\00"
@.str.20 = private constant [43 x i8] c"abi_a.ritz:71:26: integer overflow in `*`\0A\00"
@.str.21 = private constant [43 x i8] c"abi_a.ritz:71:36: integer overflow in `*`\0A\00"
@.str.22 = private constant [43 x i8] c"abi_a.ritz:77:37: integer overflow in `*`\0A\00"
@.str.23 = private constant [43 x i8] c"abi_a.ritz:77:58: integer overflow in `*`\0A\00"
@.str.24 = private constant [43 x i8] c"abi_a.ritz:77:79: integer overflow in `*`\0A\00"
@.str.25 = private constant [43 x i8] c"abi_a.ritz:81:15: integer overflow in `+`\0A\00"
@.str.26 = private constant [43 x i8] c"abi_a.ritz:82:16: integer overflow in `+`\0A\00"
@.str.27 = private constant [11 x i8] c"a_calls_b\0A\00"
@.str.28 = private constant [44 x i8] c"abi_a.ritz:107:13: integer overflow in `+`\0A\00"
@.str.29 = private constant [44 x i8] c"abi_a.ritz:107:13: integer overflow in `+`\0A\00"
@.str.30 = private constant [44 x i8] c"abi_a.ritz:107:13: integer overflow in `+`\0A\00"
@.str.31 = private constant [44 x i8] c"abi_a.ritz:119:12: integer overflow in `+`\0A\00"
@.str.32 = private constant [44 x i8] c"abi_a.ritz:121:12: integer overflow in `+`\0A\00"
@.str.33 = private constant [44 x i8] c"abi_a.ritz:133:13: integer overflow in `+`\0A\00"
@.str.34 = private constant [43 x i8] c"abi_a.ritz:45:10: integer overflow in `+`\0A\00"
declare i64 @rt_write(...) "no-builtins"
declare void @rt_hex(...) "no-builtins"
declare %Pair @b_pair(...) "no-builtins"
declare %Mixed @b_mixed(...) "no-builtins"
declare i64 @b_straddle_int(...) "no-builtins"
declare i64 @b_straddle_float(...) "no-builtins"
declare %Three @b_three(...) "no-builtins"
declare %Four @b_four(...) "no-builtins"
declare %D2 @b_d2(...) "no-builtins"
declare %D3 @b_d3(...) "no-builtins"
declare %D4 @b_d4(...) "no-builtins"
declare %D5 @b_d5(...) "no-builtins"
declare %V4 @b_v4(...) "no-builtins"
declare %V5 @b_v5(...) "no-builtins"
declare i64 @b_big(ptr byval(%Big) align 8) "no-builtins"
declare i64 @b_packed(...) "no-builtins"
declare i64 @b_big_wide(ptr byval(%BigWide) align 32) "no-builtins"
declare void @b_sret(...) "no-builtins"
declare i64 @b_aligned(...) "no-builtins"
declare i64 @b_internal_wide(...) "no-builtins"
declare void @b_calls_a(...) "no-builtins"

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

declare { i32, i1 } @llvm.sadd.with.overflow.i32(i32, i32)
declare { i64, i1 } @llvm.sadd.with.overflow.i64(i64, i64)
declare { i64, i1 } @llvm.uadd.with.overflow.i64(i64, i64)
declare { i32, i1 } @llvm.ssub.with.overflow.i32(i32, i32)
declare { i8, i1 } @llvm.smul.with.overflow.i8(i8, i8)
declare { i32, i1 } @llvm.smul.with.overflow.i32(i32, i32)
declare { i64, i1 } @llvm.smul.with.overflow.i64(i64, i64)
define internal void @__ritz_overflow_trap(ptr %msg, i64 %len) cold noinline noreturn nounwind {
entry:
  %w = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 1, i64 2, ptr %msg, i64 %len)
  %x = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1)
  unreachable
}
