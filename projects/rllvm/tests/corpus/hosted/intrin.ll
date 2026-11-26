; ModuleID = 'ritz1_output'
target triple = "x86_64-unknown-linux-gnu"

%Span$u8 = type {ptr, i64}
%StrView = type {ptr, i64}

%Option$i64 = type { i8, [7 x i8], [8 x i8] }




define i8 @sadd8__f5e15905(i8 %a.arg, i8 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i8
  %.2 = alloca i8
  store i8 %a.arg, ptr %.1
  store i8 %b.arg, ptr %.2
  %.3 = load i8, ptr %.1
  %.4 = sext i8 %.3 to i64
  %.5 = load i8, ptr %.2
  %.6 = sext i8 %.5 to i64
  %.7 = trunc i64 %.4 to i8
  %.8 = trunc i64 %.6 to i8
  %.9 = call { i8, i1 } @llvm.sadd.with.overflow.i8(i8 %.7, i8 %.8)
  %.10 = extractvalue { i8, i1 } %.9, 0
  %.11 = extractvalue { i8, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.0, i64 41)
  unreachable
L1:
  %.12 = sext i8 %.10 to i64
  %.13 = trunc i64 %.12 to i8
  ret i8 %.13
}

define i8 @ssub8__f5e15905(i8 %a.arg, i8 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i8
  %.2 = alloca i8
  store i8 %a.arg, ptr %.1
  store i8 %b.arg, ptr %.2
  %.3 = load i8, ptr %.1
  %.4 = sext i8 %.3 to i64
  %.5 = load i8, ptr %.2
  %.6 = sext i8 %.5 to i64
  %.7 = trunc i64 %.4 to i8
  %.8 = trunc i64 %.6 to i8
  %.9 = call { i8, i1 } @llvm.ssub.with.overflow.i8(i8 %.7, i8 %.8)
  %.10 = extractvalue { i8, i1 } %.9, 0
  %.11 = extractvalue { i8, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.1, i64 41)
  unreachable
L1:
  %.12 = sext i8 %.10 to i64
  %.13 = trunc i64 %.12 to i8
  ret i8 %.13
}

define i8 @smul8__f5e15905(i8 %a.arg, i8 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i8
  %.2 = alloca i8
  store i8 %a.arg, ptr %.1
  store i8 %b.arg, ptr %.2
  %.3 = load i8, ptr %.1
  %.4 = sext i8 %.3 to i64
  %.5 = load i8, ptr %.2
  %.6 = sext i8 %.5 to i64
  %.7 = trunc i64 %.4 to i8
  %.8 = trunc i64 %.6 to i8
  %.9 = call { i8, i1 } @llvm.smul.with.overflow.i8(i8 %.7, i8 %.8)
  %.10 = extractvalue { i8, i1 } %.9, 0
  %.11 = extractvalue { i8, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.2, i64 42)
  unreachable
L1:
  %.12 = sext i8 %.10 to i64
  %.13 = trunc i64 %.12 to i8
  ret i8 %.13
}

define i8 @uadd8__f5e15905(i8 %a.arg, i8 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i8
  %.2 = alloca i8
  store i8 %a.arg, ptr %.1
  store i8 %b.arg, ptr %.2
  %.3 = load i8, ptr %.1
  %.4 = zext i8 %.3 to i64
  %.5 = load i8, ptr %.2
  %.6 = zext i8 %.5 to i64
  %.7 = trunc i64 %.4 to i8
  %.8 = trunc i64 %.6 to i8
  %.9 = call { i8, i1 } @llvm.uadd.with.overflow.i8(i8 %.7, i8 %.8)
  %.10 = extractvalue { i8, i1 } %.9, 0
  %.11 = extractvalue { i8, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.3, i64 42)
  unreachable
L1:
  %.12 = zext i8 %.10 to i64
  %.13 = trunc i64 %.12 to i8
  ret i8 %.13
}

define i8 @usub8__f5e15905(i8 %a.arg, i8 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i8
  %.2 = alloca i8
  store i8 %a.arg, ptr %.1
  store i8 %b.arg, ptr %.2
  %.3 = load i8, ptr %.1
  %.4 = zext i8 %.3 to i64
  %.5 = load i8, ptr %.2
  %.6 = zext i8 %.5 to i64
  %.7 = trunc i64 %.4 to i8
  %.8 = trunc i64 %.6 to i8
  %.9 = call { i8, i1 } @llvm.usub.with.overflow.i8(i8 %.7, i8 %.8)
  %.10 = extractvalue { i8, i1 } %.9, 0
  %.11 = extractvalue { i8, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.4, i64 42)
  unreachable
L1:
  %.12 = zext i8 %.10 to i64
  %.13 = trunc i64 %.12 to i8
  ret i8 %.13
}

define i8 @umul8__f5e15905(i8 %a.arg, i8 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i8
  %.2 = alloca i8
  store i8 %a.arg, ptr %.1
  store i8 %b.arg, ptr %.2
  %.3 = load i8, ptr %.1
  %.4 = zext i8 %.3 to i64
  %.5 = load i8, ptr %.2
  %.6 = zext i8 %.5 to i64
  %.7 = trunc i64 %.4 to i8
  %.8 = trunc i64 %.6 to i8
  %.9 = call { i8, i1 } @llvm.umul.with.overflow.i8(i8 %.7, i8 %.8)
  %.10 = extractvalue { i8, i1 } %.9, 0
  %.11 = extractvalue { i8, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.5, i64 42)
  unreachable
L1:
  %.12 = zext i8 %.10 to i64
  %.13 = trunc i64 %.12 to i8
  ret i8 %.13
}

define i16 @sadd16__f5e15905(i16 %a.arg, i16 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i16
  %.2 = alloca i16
  store i16 %a.arg, ptr %.1
  store i16 %b.arg, ptr %.2
  %.3 = load i16, ptr %.1
  %.4 = sext i16 %.3 to i64
  %.5 = load i16, ptr %.2
  %.6 = sext i16 %.5 to i64
  %.7 = trunc i64 %.4 to i16
  %.8 = trunc i64 %.6 to i16
  %.9 = call { i16, i1 } @llvm.sadd.with.overflow.i16(i16 %.7, i16 %.8)
  %.10 = extractvalue { i16, i1 } %.9, 0
  %.11 = extractvalue { i16, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.6, i64 42)
  unreachable
L1:
  %.12 = sext i16 %.10 to i64
  %.13 = trunc i64 %.12 to i16
  ret i16 %.13
}

define i16 @ssub16__f5e15905(i16 %a.arg, i16 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i16
  %.2 = alloca i16
  store i16 %a.arg, ptr %.1
  store i16 %b.arg, ptr %.2
  %.3 = load i16, ptr %.1
  %.4 = sext i16 %.3 to i64
  %.5 = load i16, ptr %.2
  %.6 = sext i16 %.5 to i64
  %.7 = trunc i64 %.4 to i16
  %.8 = trunc i64 %.6 to i16
  %.9 = call { i16, i1 } @llvm.ssub.with.overflow.i16(i16 %.7, i16 %.8)
  %.10 = extractvalue { i16, i1 } %.9, 0
  %.11 = extractvalue { i16, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.7, i64 42)
  unreachable
L1:
  %.12 = sext i16 %.10 to i64
  %.13 = trunc i64 %.12 to i16
  ret i16 %.13
}

define i16 @smul16__f5e15905(i16 %a.arg, i16 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i16
  %.2 = alloca i16
  store i16 %a.arg, ptr %.1
  store i16 %b.arg, ptr %.2
  %.3 = load i16, ptr %.1
  %.4 = sext i16 %.3 to i64
  %.5 = load i16, ptr %.2
  %.6 = sext i16 %.5 to i64
  %.7 = trunc i64 %.4 to i16
  %.8 = trunc i64 %.6 to i16
  %.9 = call { i16, i1 } @llvm.smul.with.overflow.i16(i16 %.7, i16 %.8)
  %.10 = extractvalue { i16, i1 } %.9, 0
  %.11 = extractvalue { i16, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.8, i64 42)
  unreachable
L1:
  %.12 = sext i16 %.10 to i64
  %.13 = trunc i64 %.12 to i16
  ret i16 %.13
}

define i16 @uadd16__f5e15905(i16 %a.arg, i16 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i16
  %.2 = alloca i16
  store i16 %a.arg, ptr %.1
  store i16 %b.arg, ptr %.2
  %.3 = load i16, ptr %.1
  %.4 = zext i16 %.3 to i64
  %.5 = load i16, ptr %.2
  %.6 = zext i16 %.5 to i64
  %.7 = trunc i64 %.4 to i16
  %.8 = trunc i64 %.6 to i16
  %.9 = call { i16, i1 } @llvm.uadd.with.overflow.i16(i16 %.7, i16 %.8)
  %.10 = extractvalue { i16, i1 } %.9, 0
  %.11 = extractvalue { i16, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.9, i64 42)
  unreachable
L1:
  %.12 = zext i16 %.10 to i64
  %.13 = trunc i64 %.12 to i16
  ret i16 %.13
}

define i16 @usub16__f5e15905(i16 %a.arg, i16 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i16
  %.2 = alloca i16
  store i16 %a.arg, ptr %.1
  store i16 %b.arg, ptr %.2
  %.3 = load i16, ptr %.1
  %.4 = zext i16 %.3 to i64
  %.5 = load i16, ptr %.2
  %.6 = zext i16 %.5 to i64
  %.7 = trunc i64 %.4 to i16
  %.8 = trunc i64 %.6 to i16
  %.9 = call { i16, i1 } @llvm.usub.with.overflow.i16(i16 %.7, i16 %.8)
  %.10 = extractvalue { i16, i1 } %.9, 0
  %.11 = extractvalue { i16, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.10, i64 42)
  unreachable
L1:
  %.12 = zext i16 %.10 to i64
  %.13 = trunc i64 %.12 to i16
  ret i16 %.13
}

define i16 @umul16__f5e15905(i16 %a.arg, i16 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i16
  %.2 = alloca i16
  store i16 %a.arg, ptr %.1
  store i16 %b.arg, ptr %.2
  %.3 = load i16, ptr %.1
  %.4 = zext i16 %.3 to i64
  %.5 = load i16, ptr %.2
  %.6 = zext i16 %.5 to i64
  %.7 = trunc i64 %.4 to i16
  %.8 = trunc i64 %.6 to i16
  %.9 = call { i16, i1 } @llvm.umul.with.overflow.i16(i16 %.7, i16 %.8)
  %.10 = extractvalue { i16, i1 } %.9, 0
  %.11 = extractvalue { i16, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.11, i64 42)
  unreachable
L1:
  %.12 = zext i16 %.10 to i64
  %.13 = trunc i64 %.12 to i16
  ret i16 %.13
}

define i32 @sadd32__f5e15905(i32 %a.arg, i32 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca i32
  store i32 %a.arg, ptr %.1
  store i32 %b.arg, ptr %.2
  %.3 = load i32, ptr %.1
  %.4 = sext i32 %.3 to i64
  %.5 = load i32, ptr %.2
  %.6 = sext i32 %.5 to i64
  %.7 = trunc i64 %.4 to i32
  %.8 = trunc i64 %.6 to i32
  %.9 = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %.7, i32 %.8)
  %.10 = extractvalue { i32, i1 } %.9, 0
  %.11 = extractvalue { i32, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.12, i64 42)
  unreachable
L1:
  %.12 = sext i32 %.10 to i64
  %.13 = trunc i64 %.12 to i32
  ret i32 %.13
}

define i32 @ssub32__f5e15905(i32 %a.arg, i32 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca i32
  store i32 %a.arg, ptr %.1
  store i32 %b.arg, ptr %.2
  %.3 = load i32, ptr %.1
  %.4 = sext i32 %.3 to i64
  %.5 = load i32, ptr %.2
  %.6 = sext i32 %.5 to i64
  %.7 = trunc i64 %.4 to i32
  %.8 = trunc i64 %.6 to i32
  %.9 = call { i32, i1 } @llvm.ssub.with.overflow.i32(i32 %.7, i32 %.8)
  %.10 = extractvalue { i32, i1 } %.9, 0
  %.11 = extractvalue { i32, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.13, i64 42)
  unreachable
L1:
  %.12 = sext i32 %.10 to i64
  %.13 = trunc i64 %.12 to i32
  ret i32 %.13
}

define i32 @smul32__f5e15905(i32 %a.arg, i32 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca i32
  store i32 %a.arg, ptr %.1
  store i32 %b.arg, ptr %.2
  %.3 = load i32, ptr %.1
  %.4 = sext i32 %.3 to i64
  %.5 = load i32, ptr %.2
  %.6 = sext i32 %.5 to i64
  %.7 = trunc i64 %.4 to i32
  %.8 = trunc i64 %.6 to i32
  %.9 = call { i32, i1 } @llvm.smul.with.overflow.i32(i32 %.7, i32 %.8)
  %.10 = extractvalue { i32, i1 } %.9, 0
  %.11 = extractvalue { i32, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.14, i64 42)
  unreachable
L1:
  %.12 = sext i32 %.10 to i64
  %.13 = trunc i64 %.12 to i32
  ret i32 %.13
}

define i32 @uadd32__f5e15905(i32 %a.arg, i32 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca i32
  store i32 %a.arg, ptr %.1
  store i32 %b.arg, ptr %.2
  %.3 = load i32, ptr %.1
  %.4 = zext i32 %.3 to i64
  %.5 = load i32, ptr %.2
  %.6 = zext i32 %.5 to i64
  %.7 = trunc i64 %.4 to i32
  %.8 = trunc i64 %.6 to i32
  %.9 = call { i32, i1 } @llvm.uadd.with.overflow.i32(i32 %.7, i32 %.8)
  %.10 = extractvalue { i32, i1 } %.9, 0
  %.11 = extractvalue { i32, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.15, i64 42)
  unreachable
L1:
  %.12 = zext i32 %.10 to i64
  %.13 = trunc i64 %.12 to i32
  ret i32 %.13
}

define i32 @usub32__f5e15905(i32 %a.arg, i32 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca i32
  store i32 %a.arg, ptr %.1
  store i32 %b.arg, ptr %.2
  %.3 = load i32, ptr %.1
  %.4 = zext i32 %.3 to i64
  %.5 = load i32, ptr %.2
  %.6 = zext i32 %.5 to i64
  %.7 = trunc i64 %.4 to i32
  %.8 = trunc i64 %.6 to i32
  %.9 = call { i32, i1 } @llvm.usub.with.overflow.i32(i32 %.7, i32 %.8)
  %.10 = extractvalue { i32, i1 } %.9, 0
  %.11 = extractvalue { i32, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.16, i64 42)
  unreachable
L1:
  %.12 = zext i32 %.10 to i64
  %.13 = trunc i64 %.12 to i32
  ret i32 %.13
}

define i32 @umul32__f5e15905(i32 %a.arg, i32 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca i32
  store i32 %a.arg, ptr %.1
  store i32 %b.arg, ptr %.2
  %.3 = load i32, ptr %.1
  %.4 = zext i32 %.3 to i64
  %.5 = load i32, ptr %.2
  %.6 = zext i32 %.5 to i64
  %.7 = trunc i64 %.4 to i32
  %.8 = trunc i64 %.6 to i32
  %.9 = call { i32, i1 } @llvm.umul.with.overflow.i32(i32 %.7, i32 %.8)
  %.10 = extractvalue { i32, i1 } %.9, 0
  %.11 = extractvalue { i32, i1 } %.9, 1
  br i1 %.11, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.17, i64 42)
  unreachable
L1:
  %.12 = zext i32 %.10 to i64
  %.13 = trunc i64 %.12 to i32
  ret i32 %.13
}

define i64 @sadd64__f5e15905(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %a.arg, ptr %.1
  store i64 %b.arg, ptr %.2
  %.3 = load i64, ptr %.1
  %.4 = load i64, ptr %.2
  %.5 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.3, i64 %.4)
  %.6 = extractvalue { i64, i1 } %.5, 0
  %.7 = extractvalue { i64, i1 } %.5, 1
  br i1 %.7, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.18, i64 42)
  unreachable
L1:
  ret i64 %.6
}

define i64 @ssub64__f5e15905(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %a.arg, ptr %.1
  store i64 %b.arg, ptr %.2
  %.3 = load i64, ptr %.1
  %.4 = load i64, ptr %.2
  %.5 = call { i64, i1 } @llvm.ssub.with.overflow.i64(i64 %.3, i64 %.4)
  %.6 = extractvalue { i64, i1 } %.5, 0
  %.7 = extractvalue { i64, i1 } %.5, 1
  br i1 %.7, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.19, i64 42)
  unreachable
L1:
  ret i64 %.6
}

define i64 @smul64__f5e15905(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %a.arg, ptr %.1
  store i64 %b.arg, ptr %.2
  %.3 = load i64, ptr %.1
  %.4 = load i64, ptr %.2
  %.5 = call { i64, i1 } @llvm.smul.with.overflow.i64(i64 %.3, i64 %.4)
  %.6 = extractvalue { i64, i1 } %.5, 0
  %.7 = extractvalue { i64, i1 } %.5, 1
  br i1 %.7, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.20, i64 42)
  unreachable
L1:
  ret i64 %.6
}

define i64 @uadd64__f5e15905(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %a.arg, ptr %.1
  store i64 %b.arg, ptr %.2
  %.3 = load i64, ptr %.1
  %.4 = load i64, ptr %.2
  %.5 = call { i64, i1 } @llvm.uadd.with.overflow.i64(i64 %.3, i64 %.4)
  %.6 = extractvalue { i64, i1 } %.5, 0
  %.7 = extractvalue { i64, i1 } %.5, 1
  br i1 %.7, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.21, i64 42)
  unreachable
L1:
  ret i64 %.6
}

define i64 @usub64__f5e15905(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %a.arg, ptr %.1
  store i64 %b.arg, ptr %.2
  %.3 = load i64, ptr %.1
  %.4 = load i64, ptr %.2
  %.5 = call { i64, i1 } @llvm.usub.with.overflow.i64(i64 %.3, i64 %.4)
  %.6 = extractvalue { i64, i1 } %.5, 0
  %.7 = extractvalue { i64, i1 } %.5, 1
  br i1 %.7, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.22, i64 42)
  unreachable
L1:
  ret i64 %.6
}

define i64 @umul64__f5e15905(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %a.arg, ptr %.1
  store i64 %b.arg, ptr %.2
  %.3 = load i64, ptr %.1
  %.4 = load i64, ptr %.2
  %.5 = call { i64, i1 } @llvm.umul.with.overflow.i64(i64 %.3, i64 %.4)
  %.6 = extractvalue { i64, i1 } %.5, 0
  %.7 = extractvalue { i64, i1 } %.5, 1
  br i1 %.7, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.23, i64 42)
  unreachable
L1:
  ret i64 %.6
}

define i8 @rot8__f5e15905(i8 %x.arg, i8 %n.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i8
  %.2 = alloca i8
  store i8 %x.arg, ptr %.1
  store i8 %n.arg, ptr %.2
  %.3 = load i8, ptr %.1
  %.4 = zext i8 %.3 to i64
  %.5 = trunc i64 %.4 to i8
  %.6 = load i8, ptr %.2
  %.7 = zext i8 %.6 to i64
  %.8 = trunc i64 %.7 to i8
  %.9 = call i8 @llvm.fshl.i8(i8 %.5, i8 %.5, i8 %.8)
  %.10 = zext i8 %.9 to i64
  %.11 = load i8, ptr %.1
  %.12 = zext i8 %.11 to i64
  %.13 = trunc i64 %.12 to i8
  %.14 = load i8, ptr %.2
  %.15 = zext i8 %.14 to i64
  %.16 = trunc i64 %.15 to i8
  %.17 = call i8 @llvm.fshr.i8(i8 %.13, i8 %.13, i8 %.16)
  %.18 = zext i8 %.17 to i64
  %.19 = xor i64 %.10, %.18
  %.20 = trunc i64 %.19 to i8
  ret i8 %.20
}

define i8 @counts8__f5e15905(i8 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i8
  store i8 %x.arg, ptr %.1
  %.2 = load i8, ptr %.1
  %.3 = zext i8 %.2 to i64
  %.4 = trunc i64 %.3 to i8
  %.5 = call i8 @llvm.ctlz.i8(i8 %.4, i1 false)
  %.6 = zext i8 %.5 to i64
  %.7 = load i8, ptr %.1
  %.8 = zext i8 %.7 to i64
  %.9 = trunc i64 %.8 to i8
  %.10 = call i8 @llvm.cttz.i8(i8 %.9, i1 false)
  %.11 = zext i8 %.10 to i64
  %.12 = add i64 %.6, %.11
  %.13 = load i8, ptr %.1
  %.14 = zext i8 %.13 to i64
  %.15 = trunc i64 %.14 to i8
  %.16 = call i8 @llvm.ctpop.i8(i8 %.15)
  %.17 = zext i8 %.16 to i64
  %.18 = add i64 %.12, %.17
  %.19 = trunc i64 %.18 to i8
  ret i8 %.19
}

define i16 @rot16__f5e15905(i16 %x.arg, i16 %n.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i16
  %.2 = alloca i16
  store i16 %x.arg, ptr %.1
  store i16 %n.arg, ptr %.2
  %.3 = load i16, ptr %.1
  %.4 = zext i16 %.3 to i64
  %.5 = trunc i64 %.4 to i16
  %.6 = load i16, ptr %.2
  %.7 = zext i16 %.6 to i64
  %.8 = trunc i64 %.7 to i16
  %.9 = call i16 @llvm.fshl.i16(i16 %.5, i16 %.5, i16 %.8)
  %.10 = zext i16 %.9 to i64
  %.11 = load i16, ptr %.1
  %.12 = zext i16 %.11 to i64
  %.13 = trunc i64 %.12 to i16
  %.14 = load i16, ptr %.2
  %.15 = zext i16 %.14 to i64
  %.16 = trunc i64 %.15 to i16
  %.17 = call i16 @llvm.fshr.i16(i16 %.13, i16 %.13, i16 %.16)
  %.18 = zext i16 %.17 to i64
  %.19 = xor i64 %.10, %.18
  %.20 = trunc i64 %.19 to i16
  ret i16 %.20
}

define i16 @counts16__f5e15905(i16 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i16
  store i16 %x.arg, ptr %.1
  %.2 = load i16, ptr %.1
  %.3 = zext i16 %.2 to i64
  %.4 = trunc i64 %.3 to i16
  %.5 = call i16 @llvm.ctlz.i16(i16 %.4, i1 false)
  %.6 = zext i16 %.5 to i64
  %.7 = load i16, ptr %.1
  %.8 = zext i16 %.7 to i64
  %.9 = trunc i64 %.8 to i16
  %.10 = call i16 @llvm.cttz.i16(i16 %.9, i1 false)
  %.11 = zext i16 %.10 to i64
  %.12 = add i64 %.6, %.11
  %.13 = load i16, ptr %.1
  %.14 = zext i16 %.13 to i64
  %.15 = trunc i64 %.14 to i16
  %.16 = call i16 @llvm.ctpop.i16(i16 %.15)
  %.17 = zext i16 %.16 to i64
  %.18 = add i64 %.12, %.17
  %.19 = trunc i64 %.18 to i16
  ret i16 %.19
}

define i32 @rot32__f5e15905(i32 %x.arg, i32 %n.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca i32
  store i32 %x.arg, ptr %.1
  store i32 %n.arg, ptr %.2
  %.3 = load i32, ptr %.1
  %.4 = zext i32 %.3 to i64
  %.5 = trunc i64 %.4 to i32
  %.6 = load i32, ptr %.2
  %.7 = zext i32 %.6 to i64
  %.8 = trunc i64 %.7 to i32
  %.9 = call i32 @llvm.fshl.i32(i32 %.5, i32 %.5, i32 %.8)
  %.10 = zext i32 %.9 to i64
  %.11 = load i32, ptr %.1
  %.12 = zext i32 %.11 to i64
  %.13 = trunc i64 %.12 to i32
  %.14 = load i32, ptr %.2
  %.15 = zext i32 %.14 to i64
  %.16 = trunc i64 %.15 to i32
  %.17 = call i32 @llvm.fshr.i32(i32 %.13, i32 %.13, i32 %.16)
  %.18 = zext i32 %.17 to i64
  %.19 = xor i64 %.10, %.18
  %.20 = trunc i64 %.19 to i32
  ret i32 %.20
}

define i32 @counts32__f5e15905(i32 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  store i32 %x.arg, ptr %.1
  %.2 = load i32, ptr %.1
  %.3 = zext i32 %.2 to i64
  %.4 = trunc i64 %.3 to i32
  %.5 = call i32 @llvm.ctlz.i32(i32 %.4, i1 false)
  %.6 = zext i32 %.5 to i64
  %.7 = load i32, ptr %.1
  %.8 = zext i32 %.7 to i64
  %.9 = trunc i64 %.8 to i32
  %.10 = call i32 @llvm.cttz.i32(i32 %.9, i1 false)
  %.11 = zext i32 %.10 to i64
  %.12 = add i64 %.6, %.11
  %.13 = load i32, ptr %.1
  %.14 = zext i32 %.13 to i64
  %.15 = trunc i64 %.14 to i32
  %.16 = call i32 @llvm.ctpop.i32(i32 %.15)
  %.17 = zext i32 %.16 to i64
  %.18 = add i64 %.12, %.17
  %.19 = trunc i64 %.18 to i32
  ret i32 %.19
}

define i64 @rot64__f5e15905(i64 %x.arg, i64 %n.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %x.arg, ptr %.1
  store i64 %n.arg, ptr %.2
  %.3 = load i64, ptr %.1
  %.4 = load i64, ptr %.2
  %.5 = call i64 @llvm.fshl.i64(i64 %.3, i64 %.3, i64 %.4)
  %.6 = load i64, ptr %.1
  %.7 = load i64, ptr %.2
  %.8 = call i64 @llvm.fshr.i64(i64 %.6, i64 %.6, i64 %.7)
  %.9 = xor i64 %.5, %.8
  ret i64 %.9
}

define i64 @counts64__f5e15905(i64 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  store i64 %x.arg, ptr %.1
  %.2 = load i64, ptr %.1
  %.3 = call i64 @llvm.ctlz.i64(i64 %.2, i1 false)
  %.4 = load i64, ptr %.1
  %.5 = call i64 @llvm.cttz.i64(i64 %.4, i1 false)
  %.6 = add i64 %.3, %.5
  %.7 = load i64, ptr %.1
  %.8 = call i64 @llvm.ctpop.i64(i64 %.7)
  %.9 = add i64 %.6, %.8
  ret i64 %.9
}

define i16 @swap16__f5e15905(i16 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i16
  store i16 %x.arg, ptr %.1
  %.2 = load i16, ptr %.1
  %.3 = zext i16 %.2 to i64
  %.4 = trunc i64 %.3 to i16
  %.5 = call i16 @llvm.bswap.i16(i16 %.4)
  %.6 = zext i16 %.5 to i64
  %.7 = trunc i64 %.6 to i16
  ret i16 %.7
}

define i32 @swap32__f5e15905(i32 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  store i32 %x.arg, ptr %.1
  %.2 = load i32, ptr %.1
  %.3 = zext i32 %.2 to i64
  %.4 = trunc i64 %.3 to i32
  %.5 = call i32 @llvm.bswap.i32(i32 %.4)
  %.6 = zext i32 %.5 to i64
  %.7 = trunc i64 %.6 to i32
  ret i32 %.7
}

define i64 @swap64__f5e15905(i64 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  store i64 %x.arg, ptr %.1
  %.2 = load i64, ptr %.1
  %.3 = call i64 @llvm.bswap.i64(i64 %.2)
  ret i64 %.3
}

define double @abs64__f5e15905(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  store double %x.arg, ptr %.1
  %.2 = load double, ptr %.1
  %.3 = call double @llvm.fabs.f64(double %.2)
  ret double %.3
}

define float @abs32__f5e15905(float %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca float
  store float %x.arg, ptr %.1
  %.2 = load float, ptr %.1
  %.3 = call float @llvm.fabs.f32(float %.2)
  ret float %.3
}

define i8 @i8_of_f32__f5e15905(float %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca float
  store float %x.arg, ptr %.1
  %.2 = load float, ptr %.1
  %.3 = call i8 @llvm.fptosi.sat.i8.f32(float %.2)
  %.4 = sext i8 %.3 to i64
  %.5 = trunc i64 %.4 to i8
  ret i8 %.5
}

define i16 @i16_of_f32__f5e15905(float %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca float
  store float %x.arg, ptr %.1
  %.2 = load float, ptr %.1
  %.3 = call i16 @llvm.fptosi.sat.i16.f32(float %.2)
  %.4 = sext i16 %.3 to i64
  %.5 = trunc i64 %.4 to i16
  ret i16 %.5
}

define i32 @i32_of_f32__f5e15905(float %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca float
  store float %x.arg, ptr %.1
  %.2 = load float, ptr %.1
  %.3 = call i32 @llvm.fptosi.sat.i32.f32(float %.2)
  %.4 = sext i32 %.3 to i64
  %.5 = trunc i64 %.4 to i32
  ret i32 %.5
}

define i64 @i64_of_f32__f5e15905(float %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca float
  store float %x.arg, ptr %.1
  %.2 = load float, ptr %.1
  %.3 = call i64 @llvm.fptosi.sat.i64.f32(float %.2)
  ret i64 %.3
}

define i8 @u8_of_f32__f5e15905(float %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca float
  store float %x.arg, ptr %.1
  %.2 = load float, ptr %.1
  %.3 = call i8 @llvm.fptoui.sat.i8.f32(float %.2)
  %.4 = zext i8 %.3 to i64
  %.5 = trunc i64 %.4 to i8
  ret i8 %.5
}

define i16 @u16_of_f32__f5e15905(float %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca float
  store float %x.arg, ptr %.1
  %.2 = load float, ptr %.1
  %.3 = call i16 @llvm.fptoui.sat.i16.f32(float %.2)
  %.4 = zext i16 %.3 to i64
  %.5 = trunc i64 %.4 to i16
  ret i16 %.5
}

define i32 @u32_of_f32__f5e15905(float %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca float
  store float %x.arg, ptr %.1
  %.2 = load float, ptr %.1
  %.3 = call i32 @llvm.fptoui.sat.i32.f32(float %.2)
  %.4 = zext i32 %.3 to i64
  %.5 = trunc i64 %.4 to i32
  ret i32 %.5
}

define i64 @u64_of_f32__f5e15905(float %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca float
  store float %x.arg, ptr %.1
  %.2 = load float, ptr %.1
  %.3 = call i64 @llvm.fptoui.sat.i64.f32(float %.2)
  ret i64 %.3
}

define i8 @i8_of_f64__f5e15905(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  store double %x.arg, ptr %.1
  %.2 = load double, ptr %.1
  %.3 = call i8 @llvm.fptosi.sat.i8.f64(double %.2)
  %.4 = sext i8 %.3 to i64
  %.5 = trunc i64 %.4 to i8
  ret i8 %.5
}

define i16 @i16_of_f64__f5e15905(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  store double %x.arg, ptr %.1
  %.2 = load double, ptr %.1
  %.3 = call i16 @llvm.fptosi.sat.i16.f64(double %.2)
  %.4 = sext i16 %.3 to i64
  %.5 = trunc i64 %.4 to i16
  ret i16 %.5
}

define i32 @i32_of_f64__f5e15905(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  store double %x.arg, ptr %.1
  %.2 = load double, ptr %.1
  %.3 = call i32 @llvm.fptosi.sat.i32.f64(double %.2)
  %.4 = sext i32 %.3 to i64
  %.5 = trunc i64 %.4 to i32
  ret i32 %.5
}

define i64 @i64_of_f64__f5e15905(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  store double %x.arg, ptr %.1
  %.2 = load double, ptr %.1
  %.3 = call i64 @llvm.fptosi.sat.i64.f64(double %.2)
  ret i64 %.3
}

define i8 @u8_of_f64__f5e15905(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  store double %x.arg, ptr %.1
  %.2 = load double, ptr %.1
  %.3 = call i8 @llvm.fptoui.sat.i8.f64(double %.2)
  %.4 = zext i8 %.3 to i64
  %.5 = trunc i64 %.4 to i8
  ret i8 %.5
}

define i16 @u16_of_f64__f5e15905(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  store double %x.arg, ptr %.1
  %.2 = load double, ptr %.1
  %.3 = call i16 @llvm.fptoui.sat.i16.f64(double %.2)
  %.4 = zext i16 %.3 to i64
  %.5 = trunc i64 %.4 to i16
  ret i16 %.5
}

define i32 @u32_of_f64__f5e15905(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  store double %x.arg, ptr %.1
  %.2 = load double, ptr %.1
  %.3 = call i32 @llvm.fptoui.sat.i32.f64(double %.2)
  %.4 = zext i32 %.3 to i64
  %.5 = trunc i64 %.4 to i32
  ret i32 %.5
}

define i64 @u64_of_f64__f5e15905(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  store double %x.arg, ptr %.1
  %.2 = load double, ptr %.1
  %.3 = call i64 @llvm.fptoui.sat.i64.f64(double %.2)
  ret i64 %.3
}

define i64 @first__f5e15905(%Option$i64 %o.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca %Option$i64
  store %Option$i64 %o.arg, ptr %.1
  %.2 = getelementptr %Option$i64, ptr %.1, i32 0, i32 0
  %.3 = load i8, ptr %.2
  %.4 = icmp eq i8 %.3, 0  ; unwrap tag check (Ok/Some == 0)
  br i1 %.4, label %L0, label %L1
L1:
  call void @llvm.trap()  ; unwrap of None / Err
  unreachable
L0:
  %.5 = getelementptr %Option$i64, ptr %.1, i32 0, i32 2
  %.6 = load i64, ptr %.5
  ret i64 %.6
}

define i32 @main() alignstack(16) "no-builtins" {
entry:
  %.1 = add i64 0, 0
  %.2 = trunc i64 %.1 to i32
  ret i32 %.2
}


@.str.0 = private constant [42 x i8] c"intrin.ritz:7:5: integer overflow in `+`\0A\00"
@.str.1 = private constant [42 x i8] c"intrin.ritz:9:5: integer overflow in `-`\0A\00"
@.str.2 = private constant [43 x i8] c"intrin.ritz:11:5: integer overflow in `*`\0A\00"
@.str.3 = private constant [43 x i8] c"intrin.ritz:13:5: integer overflow in `+`\0A\00"
@.str.4 = private constant [43 x i8] c"intrin.ritz:15:5: integer overflow in `-`\0A\00"
@.str.5 = private constant [43 x i8] c"intrin.ritz:17:5: integer overflow in `*`\0A\00"
@.str.6 = private constant [43 x i8] c"intrin.ritz:19:5: integer overflow in `+`\0A\00"
@.str.7 = private constant [43 x i8] c"intrin.ritz:21:5: integer overflow in `-`\0A\00"
@.str.8 = private constant [43 x i8] c"intrin.ritz:23:5: integer overflow in `*`\0A\00"
@.str.9 = private constant [43 x i8] c"intrin.ritz:25:5: integer overflow in `+`\0A\00"
@.str.10 = private constant [43 x i8] c"intrin.ritz:27:5: integer overflow in `-`\0A\00"
@.str.11 = private constant [43 x i8] c"intrin.ritz:29:5: integer overflow in `*`\0A\00"
@.str.12 = private constant [43 x i8] c"intrin.ritz:31:5: integer overflow in `+`\0A\00"
@.str.13 = private constant [43 x i8] c"intrin.ritz:33:5: integer overflow in `-`\0A\00"
@.str.14 = private constant [43 x i8] c"intrin.ritz:35:5: integer overflow in `*`\0A\00"
@.str.15 = private constant [43 x i8] c"intrin.ritz:37:5: integer overflow in `+`\0A\00"
@.str.16 = private constant [43 x i8] c"intrin.ritz:39:5: integer overflow in `-`\0A\00"
@.str.17 = private constant [43 x i8] c"intrin.ritz:41:5: integer overflow in `*`\0A\00"
@.str.18 = private constant [43 x i8] c"intrin.ritz:43:5: integer overflow in `+`\0A\00"
@.str.19 = private constant [43 x i8] c"intrin.ritz:45:5: integer overflow in `-`\0A\00"
@.str.20 = private constant [43 x i8] c"intrin.ritz:47:5: integer overflow in `*`\0A\00"
@.str.21 = private constant [43 x i8] c"intrin.ritz:49:5: integer overflow in `+`\0A\00"
@.str.22 = private constant [43 x i8] c"intrin.ritz:51:5: integer overflow in `-`\0A\00"
@.str.23 = private constant [43 x i8] c"intrin.ritz:53:5: integer overflow in `*`\0A\00"
declare i8 @llvm.fshl.i8(i8, i8, i8)
declare i16 @llvm.fshl.i16(i16, i16, i16)
declare i32 @llvm.fshl.i32(i32, i32, i32)
declare i64 @llvm.fshl.i64(i64, i64, i64)
declare i8 @llvm.fshr.i8(i8, i8, i8)
declare i16 @llvm.fshr.i16(i16, i16, i16)
declare i32 @llvm.fshr.i32(i32, i32, i32)
declare i64 @llvm.fshr.i64(i64, i64, i64)
declare i8 @llvm.ctlz.i8(i8, i1)
declare i16 @llvm.ctlz.i16(i16, i1)
declare i32 @llvm.ctlz.i32(i32, i1)
declare i64 @llvm.ctlz.i64(i64, i1)
declare i8 @llvm.cttz.i8(i8, i1)
declare i16 @llvm.cttz.i16(i16, i1)
declare i32 @llvm.cttz.i32(i32, i1)
declare i64 @llvm.cttz.i64(i64, i1)
declare i8 @llvm.ctpop.i8(i8)
declare i16 @llvm.ctpop.i16(i16)
declare i32 @llvm.ctpop.i32(i32)
declare i64 @llvm.ctpop.i64(i64)
declare i16 @llvm.bswap.i16(i16)
declare i32 @llvm.bswap.i32(i32)
declare i64 @llvm.bswap.i64(i64)
declare float @llvm.fabs.f32(float)
declare double @llvm.fabs.f64(double)
declare i8 @llvm.fptosi.sat.i8.f32(float)
declare i16 @llvm.fptosi.sat.i16.f32(float)
declare i32 @llvm.fptosi.sat.i32.f32(float)
declare i64 @llvm.fptosi.sat.i64.f32(float)
declare i8 @llvm.fptoui.sat.i8.f32(float)
declare i16 @llvm.fptoui.sat.i16.f32(float)
declare i32 @llvm.fptoui.sat.i32.f32(float)
declare i64 @llvm.fptoui.sat.i64.f32(float)
declare i8 @llvm.fptosi.sat.i8.f64(double)
declare i16 @llvm.fptosi.sat.i16.f64(double)
declare i32 @llvm.fptosi.sat.i32.f64(double)
declare i64 @llvm.fptosi.sat.i64.f64(double)
declare i8 @llvm.fptoui.sat.i8.f64(double)
declare i16 @llvm.fptoui.sat.i16.f64(double)
declare i32 @llvm.fptoui.sat.i32.f64(double)
declare i64 @llvm.fptoui.sat.i64.f64(double)
declare { i8, i1 } @llvm.sadd.with.overflow.i8(i8, i8)
declare { i16, i1 } @llvm.sadd.with.overflow.i16(i16, i16)
declare { i32, i1 } @llvm.sadd.with.overflow.i32(i32, i32)
declare { i64, i1 } @llvm.sadd.with.overflow.i64(i64, i64)
declare { i8, i1 } @llvm.uadd.with.overflow.i8(i8, i8)
declare { i16, i1 } @llvm.uadd.with.overflow.i16(i16, i16)
declare { i32, i1 } @llvm.uadd.with.overflow.i32(i32, i32)
declare { i64, i1 } @llvm.uadd.with.overflow.i64(i64, i64)
declare { i8, i1 } @llvm.ssub.with.overflow.i8(i8, i8)
declare { i16, i1 } @llvm.ssub.with.overflow.i16(i16, i16)
declare { i32, i1 } @llvm.ssub.with.overflow.i32(i32, i32)
declare { i64, i1 } @llvm.ssub.with.overflow.i64(i64, i64)
declare { i8, i1 } @llvm.usub.with.overflow.i8(i8, i8)
declare { i16, i1 } @llvm.usub.with.overflow.i16(i16, i16)
declare { i32, i1 } @llvm.usub.with.overflow.i32(i32, i32)
declare { i64, i1 } @llvm.usub.with.overflow.i64(i64, i64)
declare { i8, i1 } @llvm.smul.with.overflow.i8(i8, i8)
declare { i16, i1 } @llvm.smul.with.overflow.i16(i16, i16)
declare { i32, i1 } @llvm.smul.with.overflow.i32(i32, i32)
declare { i64, i1 } @llvm.smul.with.overflow.i64(i64, i64)
declare { i8, i1 } @llvm.umul.with.overflow.i8(i8, i8)
declare { i16, i1 } @llvm.umul.with.overflow.i16(i16, i16)
declare { i32, i1 } @llvm.umul.with.overflow.i32(i32, i32)
declare { i64, i1 } @llvm.umul.with.overflow.i64(i64, i64)
define internal void @__ritz_overflow_trap(ptr %msg, i64 %len) cold noinline noreturn nounwind {
entry:
  %w = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 1, i64 2, ptr %msg, i64 %len)
  %x = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1)
  unreachable
}
