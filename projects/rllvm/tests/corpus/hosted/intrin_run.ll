; ModuleID = 'ritz1_output'
target triple = "x86_64-unknown-linux-gnu"

%Span$u8 = type {ptr, i64}
%StrView = type {ptr, i64}




@SAT_F64 = internal constant [24 x i64] [i64 9221120237041090560, i64 9218868437227405312, i64 -4503599627370496, i64 -9223372036854775808, i64 -4584664420663164928, i64 -4584664420663164927, i64 4638637247447433216, i64 4638637247447433217, i64 -4548635623644200960, i64 -4548635623644200959, i64 4674736138332667904, i64 4674736138332667905, i64 -4476578029606273024, i64 -4476578029606273023, i64 4746794007244308480, i64 4746794007244308481, i64 -4332462841530417152, i64 -4332462841530417151, i64 4890909195324358656, i64 4890909195324358655, i64 4643176031446892544, i64 4679239875398991872, i64 4751297606873776128, i64 4895412794951729152]
@SAT_F32 = internal constant [20 x i32] [i32 2143289344, i32 2139095040, i32 4286578688, i32 2147483648, i32 3271557120, i32 3271557121, i32 1123942400, i32 1123942401, i32 3338665984, i32 3338665985, i32 1191181824, i32 1191181825, i32 3472883712, i32 3472883713, i32 1325400064, i32 1325400063, i32 1132396544, i32 1199570688, i32 1333788672, i32 1602224128]

define void @say__36f560f7(%StrView %s.arg) alignstack(16) "no-builtins" {
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

define void @put__36f560f7(i64 %v.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  store i64 %v.arg, ptr %.1
  %.2 = load i64, ptr %.1
  call void @rt_hex(i64 %.2)
  ret void
}

define i8 @sadd8__36f560f7(i8 %a.arg, i8 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.0, i64 46)
  unreachable
L1:
  %.12 = sext i8 %.10 to i64
  %.13 = trunc i64 %.12 to i8
  ret i8 %.13
}

define i8 @ssub8__36f560f7(i8 %a.arg, i8 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.1, i64 46)
  unreachable
L1:
  %.12 = sext i8 %.10 to i64
  %.13 = trunc i64 %.12 to i8
  ret i8 %.13
}

define i8 @smul8__36f560f7(i8 %a.arg, i8 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.2, i64 46)
  unreachable
L1:
  %.12 = sext i8 %.10 to i64
  %.13 = trunc i64 %.12 to i8
  ret i8 %.13
}

define i8 @uadd8__36f560f7(i8 %a.arg, i8 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.3, i64 46)
  unreachable
L1:
  %.12 = zext i8 %.10 to i64
  %.13 = trunc i64 %.12 to i8
  ret i8 %.13
}

define i8 @usub8__36f560f7(i8 %a.arg, i8 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.4, i64 46)
  unreachable
L1:
  %.12 = zext i8 %.10 to i64
  %.13 = trunc i64 %.12 to i8
  ret i8 %.13
}

define i8 @umul8__36f560f7(i8 %a.arg, i8 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.5, i64 46)
  unreachable
L1:
  %.12 = zext i8 %.10 to i64
  %.13 = trunc i64 %.12 to i8
  ret i8 %.13
}

define i16 @sadd16__36f560f7(i16 %a.arg, i16 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.6, i64 46)
  unreachable
L1:
  %.12 = sext i16 %.10 to i64
  %.13 = trunc i64 %.12 to i16
  ret i16 %.13
}

define i16 @ssub16__36f560f7(i16 %a.arg, i16 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.7, i64 46)
  unreachable
L1:
  %.12 = sext i16 %.10 to i64
  %.13 = trunc i64 %.12 to i16
  ret i16 %.13
}

define i16 @smul16__36f560f7(i16 %a.arg, i16 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.8, i64 46)
  unreachable
L1:
  %.12 = sext i16 %.10 to i64
  %.13 = trunc i64 %.12 to i16
  ret i16 %.13
}

define i16 @uadd16__36f560f7(i16 %a.arg, i16 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.9, i64 46)
  unreachable
L1:
  %.12 = zext i16 %.10 to i64
  %.13 = trunc i64 %.12 to i16
  ret i16 %.13
}

define i16 @usub16__36f560f7(i16 %a.arg, i16 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.10, i64 46)
  unreachable
L1:
  %.12 = zext i16 %.10 to i64
  %.13 = trunc i64 %.12 to i16
  ret i16 %.13
}

define i16 @umul16__36f560f7(i16 %a.arg, i16 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.11, i64 46)
  unreachable
L1:
  %.12 = zext i16 %.10 to i64
  %.13 = trunc i64 %.12 to i16
  ret i16 %.13
}

define i32 @sadd32__36f560f7(i32 %a.arg, i32 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.12, i64 46)
  unreachable
L1:
  %.12 = sext i32 %.10 to i64
  %.13 = trunc i64 %.12 to i32
  ret i32 %.13
}

define i32 @ssub32__36f560f7(i32 %a.arg, i32 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.13, i64 46)
  unreachable
L1:
  %.12 = sext i32 %.10 to i64
  %.13 = trunc i64 %.12 to i32
  ret i32 %.13
}

define i32 @smul32__36f560f7(i32 %a.arg, i32 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.14, i64 46)
  unreachable
L1:
  %.12 = sext i32 %.10 to i64
  %.13 = trunc i64 %.12 to i32
  ret i32 %.13
}

define i32 @uadd32__36f560f7(i32 %a.arg, i32 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.15, i64 46)
  unreachable
L1:
  %.12 = zext i32 %.10 to i64
  %.13 = trunc i64 %.12 to i32
  ret i32 %.13
}

define i32 @usub32__36f560f7(i32 %a.arg, i32 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.16, i64 46)
  unreachable
L1:
  %.12 = zext i32 %.10 to i64
  %.13 = trunc i64 %.12 to i32
  ret i32 %.13
}

define i32 @umul32__36f560f7(i32 %a.arg, i32 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.17, i64 46)
  unreachable
L1:
  %.12 = zext i32 %.10 to i64
  %.13 = trunc i64 %.12 to i32
  ret i32 %.13
}

define i64 @sadd64__36f560f7(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.18, i64 46)
  unreachable
L1:
  ret i64 %.6
}

define i64 @ssub64__36f560f7(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.19, i64 46)
  unreachable
L1:
  ret i64 %.6
}

define i64 @smul64__36f560f7(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.20, i64 46)
  unreachable
L1:
  ret i64 %.6
}

define i64 @uadd64__36f560f7(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.21, i64 46)
  unreachable
L1:
  ret i64 %.6
}

define i64 @usub64__36f560f7(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.22, i64 46)
  unreachable
L1:
  ret i64 %.6
}

define i64 @umul64__36f560f7(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
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
  call void @__ritz_overflow_trap(ptr @.str.23, i64 46)
  unreachable
L1:
  ret i64 %.6
}

define void @overflow_rows__36f560f7() alignstack(16) "no-builtins" {
entry:
  %.1 = getelementptr [15 x i8], ptr @.str.24, i64 0, i64 0
  %.2 = insertvalue %Span$u8 undef, ptr %.1, 0
  %.3 = insertvalue %Span$u8 %.2, i64 14, 1
  %.4 = extractvalue %Span$u8 %.3, 0
  %.5 = extractvalue %Span$u8 %.3, 1
  %.6 = insertvalue %StrView undef, ptr %.4, 0
  %.7 = insertvalue %StrView %.6, i64 %.5, 1
  call void @say__36f560f7(%StrView %.7)
  %.8 = add i64 0, 0
  %.9 = add i64 0, 0
  %.10 = trunc i64 %.8 to i8
  %.11 = trunc i64 %.9 to i8
  %.12 = call i8 @sadd8__36f560f7(i8 %.10, i8 %.11)
  %.13 = sext i8 %.12 to i64
  %.14 = trunc i64 %.13 to i8
  %.15 = sext i8 %.14 to i64
  call void @put__36f560f7(i64 %.15)
  %.16 = add i64 0, 126
  %.17 = add i64 0, 1
  %.18 = trunc i64 %.16 to i8
  %.19 = trunc i64 %.17 to i8
  %.20 = call i8 @sadd8__36f560f7(i8 %.18, i8 %.19)
  %.21 = sext i8 %.20 to i64
  %.22 = trunc i64 %.21 to i8
  %.23 = sext i8 %.22 to i64
  call void @put__36f560f7(i64 %.23)
  %.24 = add i64 0, 127
  %.25 = sub i64 0, %.24
  %.26 = add i64 0, 1
  %.27 = sub i64 0, %.26
  %.28 = trunc i64 %.25 to i8
  %.29 = trunc i64 %.27 to i8
  %.30 = call i8 @sadd8__36f560f7(i8 %.28, i8 %.29)
  %.31 = sext i8 %.30 to i64
  %.32 = trunc i64 %.31 to i8
  %.33 = sext i8 %.32 to i64
  call void @put__36f560f7(i64 %.33)
  %.34 = add i64 0, 127
  %.35 = add i64 0, 128
  %.36 = sub i64 0, %.35
  %.37 = trunc i64 %.34 to i8
  %.38 = trunc i64 %.36 to i8
  %.39 = call i8 @sadd8__36f560f7(i8 %.37, i8 %.38)
  %.40 = sext i8 %.39 to i64
  %.41 = trunc i64 %.40 to i8
  %.42 = sext i8 %.41 to i64
  call void @put__36f560f7(i64 %.42)
  %.43 = add i64 0, 1
  %.44 = sub i64 0, %.43
  %.45 = add i64 0, 127
  %.46 = trunc i64 %.44 to i8
  %.47 = trunc i64 %.45 to i8
  %.48 = call i8 @ssub8__36f560f7(i8 %.46, i8 %.47)
  %.49 = sext i8 %.48 to i64
  %.50 = trunc i64 %.49 to i8
  %.51 = sext i8 %.50 to i64
  call void @put__36f560f7(i64 %.51)
  %.52 = add i64 0, 126
  %.53 = add i64 0, 1
  %.54 = sub i64 0, %.53
  %.55 = trunc i64 %.52 to i8
  %.56 = trunc i64 %.54 to i8
  %.57 = call i8 @ssub8__36f560f7(i8 %.55, i8 %.56)
  %.58 = sext i8 %.57 to i64
  %.59 = trunc i64 %.58 to i8
  %.60 = sext i8 %.59 to i64
  call void @put__36f560f7(i64 %.60)
  %.61 = add i64 0, 1
  %.62 = sub i64 0, %.61
  %.63 = add i64 0, 127
  %.64 = trunc i64 %.62 to i8
  %.65 = trunc i64 %.63 to i8
  %.66 = call i8 @smul8__36f560f7(i8 %.64, i8 %.65)
  %.67 = sext i8 %.66 to i64
  %.68 = trunc i64 %.67 to i8
  %.69 = sext i8 %.68 to i64
  call void @put__36f560f7(i64 %.69)
  %.70 = add i64 0, 128
  %.71 = sub i64 0, %.70
  %.72 = add i64 0, 1
  %.73 = trunc i64 %.71 to i8
  %.74 = trunc i64 %.72 to i8
  %.75 = call i8 @smul8__36f560f7(i8 %.73, i8 %.74)
  %.76 = sext i8 %.75 to i64
  %.77 = trunc i64 %.76 to i8
  %.78 = sext i8 %.77 to i64
  call void @put__36f560f7(i64 %.78)
  %.79 = add i64 0, 254
  %.80 = add i64 0, 1
  %.81 = trunc i64 %.79 to i8
  %.82 = trunc i64 %.80 to i8
  %.83 = call i8 @uadd8__36f560f7(i8 %.81, i8 %.82)
  %.84 = zext i8 %.83 to i64
  %.85 = trunc i64 %.84 to i8
  %.86 = zext i8 %.85 to i64
  call void @put__36f560f7(i64 %.86)
  %.87 = add i64 0, 1
  %.88 = add i64 0, 1
  %.89 = trunc i64 %.87 to i8
  %.90 = trunc i64 %.88 to i8
  %.91 = call i8 @usub8__36f560f7(i8 %.89, i8 %.90)
  %.92 = zext i8 %.91 to i64
  %.93 = trunc i64 %.92 to i8
  %.94 = zext i8 %.93 to i64
  call void @put__36f560f7(i64 %.94)
  %.95 = add i64 0, 15
  %.96 = add i64 0, 17
  %.97 = trunc i64 %.95 to i8
  %.98 = trunc i64 %.96 to i8
  %.99 = call i8 @umul8__36f560f7(i8 %.97, i8 %.98)
  %.100 = zext i8 %.99 to i64
  %.101 = trunc i64 %.100 to i8
  %.102 = zext i8 %.101 to i64
  call void @put__36f560f7(i64 %.102)
  %.103 = add i64 0, 32766
  %.104 = add i64 0, 1
  %.105 = trunc i64 %.103 to i16
  %.106 = trunc i64 %.104 to i16
  %.107 = call i16 @sadd16__36f560f7(i16 %.105, i16 %.106)
  %.108 = sext i16 %.107 to i64
  %.109 = trunc i64 %.108 to i16
  %.110 = sext i16 %.109 to i64
  call void @put__36f560f7(i64 %.110)
  %.111 = add i64 0, 32767
  %.112 = sub i64 0, %.111
  %.113 = add i64 0, 1
  %.114 = sub i64 0, %.113
  %.115 = trunc i64 %.112 to i16
  %.116 = trunc i64 %.114 to i16
  %.117 = call i16 @sadd16__36f560f7(i16 %.115, i16 %.116)
  %.118 = sext i16 %.117 to i64
  %.119 = trunc i64 %.118 to i16
  %.120 = sext i16 %.119 to i64
  call void @put__36f560f7(i64 %.120)
  %.121 = add i64 0, 1
  %.122 = sub i64 0, %.121
  %.123 = add i64 0, 32767
  %.124 = trunc i64 %.122 to i16
  %.125 = trunc i64 %.123 to i16
  %.126 = call i16 @ssub16__36f560f7(i16 %.124, i16 %.125)
  %.127 = sext i16 %.126 to i64
  %.128 = trunc i64 %.127 to i16
  %.129 = sext i16 %.128 to i64
  call void @put__36f560f7(i64 %.129)
  %.130 = add i64 0, 1
  %.131 = sub i64 0, %.130
  %.132 = add i64 0, 32767
  %.133 = trunc i64 %.131 to i16
  %.134 = trunc i64 %.132 to i16
  %.135 = call i16 @smul16__36f560f7(i16 %.133, i16 %.134)
  %.136 = sext i16 %.135 to i64
  %.137 = trunc i64 %.136 to i16
  %.138 = sext i16 %.137 to i64
  call void @put__36f560f7(i64 %.138)
  %.139 = add i64 0, 65534
  %.140 = add i64 0, 1
  %.141 = trunc i64 %.139 to i16
  %.142 = trunc i64 %.140 to i16
  %.143 = call i16 @uadd16__36f560f7(i16 %.141, i16 %.142)
  %.144 = zext i16 %.143 to i64
  %.145 = trunc i64 %.144 to i16
  %.146 = zext i16 %.145 to i64
  call void @put__36f560f7(i64 %.146)
  %.147 = add i64 0, 65535
  %.148 = add i64 0, 65535
  %.149 = trunc i64 %.147 to i16
  %.150 = trunc i64 %.148 to i16
  %.151 = call i16 @usub16__36f560f7(i16 %.149, i16 %.150)
  %.152 = zext i16 %.151 to i64
  %.153 = trunc i64 %.152 to i16
  %.154 = zext i16 %.153 to i64
  call void @put__36f560f7(i64 %.154)
  %.155 = add i64 0, 255
  %.156 = add i64 0, 257
  %.157 = trunc i64 %.155 to i16
  %.158 = trunc i64 %.156 to i16
  %.159 = call i16 @umul16__36f560f7(i16 %.157, i16 %.158)
  %.160 = zext i16 %.159 to i64
  %.161 = trunc i64 %.160 to i16
  %.162 = zext i16 %.161 to i64
  call void @put__36f560f7(i64 %.162)
  %.163 = add i64 0, 2147483646
  %.164 = add i64 0, 1
  %.165 = trunc i64 %.163 to i32
  %.166 = trunc i64 %.164 to i32
  %.167 = call i32 @sadd32__36f560f7(i32 %.165, i32 %.166)
  %.168 = sext i32 %.167 to i64
  %.169 = trunc i64 %.168 to i32
  %.170 = sext i32 %.169 to i64
  call void @put__36f560f7(i64 %.170)
  %.171 = add i64 0, 2147483647
  %.172 = sub i64 0, %.171
  %.173 = add i64 0, 1
  %.174 = sub i64 0, %.173
  %.175 = trunc i64 %.172 to i32
  %.176 = trunc i64 %.174 to i32
  %.177 = call i32 @sadd32__36f560f7(i32 %.175, i32 %.176)
  %.178 = sext i32 %.177 to i64
  %.179 = trunc i64 %.178 to i32
  %.180 = sext i32 %.179 to i64
  call void @put__36f560f7(i64 %.180)
  %.181 = add i64 0, 1
  %.182 = sub i64 0, %.181
  %.183 = add i64 0, 2147483647
  %.184 = trunc i64 %.182 to i32
  %.185 = trunc i64 %.183 to i32
  %.186 = call i32 @ssub32__36f560f7(i32 %.184, i32 %.185)
  %.187 = sext i32 %.186 to i64
  %.188 = trunc i64 %.187 to i32
  %.189 = sext i32 %.188 to i64
  call void @put__36f560f7(i64 %.189)
  %.190 = add i64 0, 1
  %.191 = sub i64 0, %.190
  %.192 = add i64 0, 2147483647
  %.193 = trunc i64 %.191 to i32
  %.194 = trunc i64 %.192 to i32
  %.195 = call i32 @smul32__36f560f7(i32 %.193, i32 %.194)
  %.196 = sext i32 %.195 to i64
  %.197 = trunc i64 %.196 to i32
  %.198 = sext i32 %.197 to i64
  call void @put__36f560f7(i64 %.198)
  %.199 = add i64 0, 46340
  %.200 = add i64 0, 46340
  %.201 = trunc i64 %.199 to i32
  %.202 = trunc i64 %.200 to i32
  %.203 = call i32 @smul32__36f560f7(i32 %.201, i32 %.202)
  %.204 = sext i32 %.203 to i64
  %.205 = trunc i64 %.204 to i32
  %.206 = sext i32 %.205 to i64
  call void @put__36f560f7(i64 %.206)
  %.207 = add i64 0, 4294967294
  %.208 = add i64 0, 1
  %.209 = trunc i64 %.207 to i32
  %.210 = trunc i64 %.208 to i32
  %.211 = call i32 @uadd32__36f560f7(i32 %.209, i32 %.210)
  %.212 = zext i32 %.211 to i64
  %.213 = trunc i64 %.212 to i32
  %.214 = zext i32 %.213 to i64
  call void @put__36f560f7(i64 %.214)
  %.215 = add i64 0, 1
  %.216 = add i64 0, 0
  %.217 = trunc i64 %.215 to i32
  %.218 = trunc i64 %.216 to i32
  %.219 = call i32 @usub32__36f560f7(i32 %.217, i32 %.218)
  %.220 = zext i32 %.219 to i64
  %.221 = trunc i64 %.220 to i32
  %.222 = zext i32 %.221 to i64
  call void @put__36f560f7(i64 %.222)
  %.223 = add i64 0, 65535
  %.224 = add i64 0, 65537
  %.225 = trunc i64 %.223 to i32
  %.226 = trunc i64 %.224 to i32
  %.227 = call i32 @umul32__36f560f7(i32 %.225, i32 %.226)
  %.228 = zext i32 %.227 to i64
  %.229 = trunc i64 %.228 to i32
  %.230 = zext i32 %.229 to i64
  call void @put__36f560f7(i64 %.230)
  %.231 = add i64 0, 9223372036854775806
  %.232 = add i64 0, 1
  %.233 = call i64 @sadd64__36f560f7(i64 %.231, i64 %.232)
  call void @put__36f560f7(i64 %.233)
  %.234 = add i64 0, 9223372036854775807
  %.235 = sub i64 0, %.234
  %.236 = add i64 0, 1
  %.237 = sub i64 0, %.236
  %.238 = call i64 @sadd64__36f560f7(i64 %.235, i64 %.237)
  call void @put__36f560f7(i64 %.238)
  %.239 = add i64 0, 1
  %.240 = sub i64 0, %.239
  %.241 = add i64 0, 9223372036854775807
  %.242 = call i64 @ssub64__36f560f7(i64 %.240, i64 %.241)
  call void @put__36f560f7(i64 %.242)
  %.243 = add i64 0, 1
  %.244 = sub i64 0, %.243
  %.245 = add i64 0, 9223372036854775807
  %.246 = call i64 @smul64__36f560f7(i64 %.244, i64 %.245)
  call void @put__36f560f7(i64 %.246)
  %.247 = add i64 0, 3037000499
  %.248 = add i64 0, 3037000499
  %.249 = call i64 @smul64__36f560f7(i64 %.247, i64 %.248)
  call void @put__36f560f7(i64 %.249)
  %.250 = add i64 0, -2
  %.251 = add i64 0, 1
  %.252 = call i64 @uadd64__36f560f7(i64 %.250, i64 %.251)
  call void @rt_hex(i64 %.252)
  %.253 = add i64 0, 1
  %.254 = add i64 0, 1
  %.255 = call i64 @usub64__36f560f7(i64 %.253, i64 %.254)
  call void @rt_hex(i64 %.255)
  %.256 = add i64 0, 4294967295
  %.257 = add i64 0, 4294967297
  %.258 = call i64 @umul64__36f560f7(i64 %.256, i64 %.257)
  call void @rt_hex(i64 %.258)
  ret void
}

define void @rot8__36f560f7(i8 %x.arg, i8 %n.arg) alignstack(16) "no-builtins" {
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
  call void @rt_hex(i64 %.10)
  %.11 = load i8, ptr %.1
  %.12 = zext i8 %.11 to i64
  %.13 = trunc i64 %.12 to i8
  %.14 = load i8, ptr %.2
  %.15 = zext i8 %.14 to i64
  %.16 = trunc i64 %.15 to i8
  %.17 = call i8 @llvm.fshr.i8(i8 %.13, i8 %.13, i8 %.16)
  %.18 = zext i8 %.17 to i64
  call void @rt_hex(i64 %.18)
  ret void
}

define void @rot16__36f560f7(i16 %x.arg, i16 %n.arg) alignstack(16) "no-builtins" {
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
  call void @rt_hex(i64 %.10)
  %.11 = load i16, ptr %.1
  %.12 = zext i16 %.11 to i64
  %.13 = trunc i64 %.12 to i16
  %.14 = load i16, ptr %.2
  %.15 = zext i16 %.14 to i64
  %.16 = trunc i64 %.15 to i16
  %.17 = call i16 @llvm.fshr.i16(i16 %.13, i16 %.13, i16 %.16)
  %.18 = zext i16 %.17 to i64
  call void @rt_hex(i64 %.18)
  ret void
}

define void @rot32__36f560f7(i32 %x.arg, i32 %n.arg) alignstack(16) "no-builtins" {
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
  call void @rt_hex(i64 %.10)
  %.11 = load i32, ptr %.1
  %.12 = zext i32 %.11 to i64
  %.13 = trunc i64 %.12 to i32
  %.14 = load i32, ptr %.2
  %.15 = zext i32 %.14 to i64
  %.16 = trunc i64 %.15 to i32
  %.17 = call i32 @llvm.fshr.i32(i32 %.13, i32 %.13, i32 %.16)
  %.18 = zext i32 %.17 to i64
  call void @rt_hex(i64 %.18)
  ret void
}

define void @rot64__36f560f7(i64 %x.arg, i64 %n.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %x.arg, ptr %.1
  store i64 %n.arg, ptr %.2
  %.3 = load i64, ptr %.1
  %.4 = load i64, ptr %.2
  %.5 = call i64 @llvm.fshl.i64(i64 %.3, i64 %.3, i64 %.4)
  call void @rt_hex(i64 %.5)
  %.6 = load i64, ptr %.1
  %.7 = load i64, ptr %.2
  %.8 = call i64 @llvm.fshr.i64(i64 %.6, i64 %.6, i64 %.7)
  call void @rt_hex(i64 %.8)
  ret void
}

define void @rotate_rows__36f560f7() alignstack(16) "no-builtins" {
entry:
  %.8 = alloca [6 x i8]
  %.27 = alloca i64
  %.41 = alloca [6 x i16]
  %.60 = alloca i64
  %.74 = alloca [6 x i32]
  %.93 = alloca i64
  %.107 = alloca [6 x i64]
  %.120 = alloca i64
  %.1 = getelementptr [11 x i8], ptr @.str.25, i64 0, i64 0
  %.2 = insertvalue %Span$u8 undef, ptr %.1, 0
  %.3 = insertvalue %Span$u8 %.2, i64 10, 1
  %.4 = extractvalue %Span$u8 %.3, 0
  %.5 = extractvalue %Span$u8 %.3, 1
  %.6 = insertvalue %StrView undef, ptr %.4, 0
  %.7 = insertvalue %StrView %.6, i64 %.5, 1
  call void @say__36f560f7(%StrView %.7)
  %.9 = add i64 0, 0
  %.10 = getelementptr [6 x i8], ptr %.8, i64 0, i64 0
  %.11 = trunc i64 %.9 to i8
  store i8 %.11, ptr %.10
  %.12 = add i64 0, 1
  %.13 = getelementptr [6 x i8], ptr %.8, i64 0, i64 1
  %.14 = trunc i64 %.12 to i8
  store i8 %.14, ptr %.13
  %.15 = add i64 0, 7
  %.16 = getelementptr [6 x i8], ptr %.8, i64 0, i64 2
  %.17 = trunc i64 %.15 to i8
  store i8 %.17, ptr %.16
  %.18 = add i64 0, 8
  %.19 = getelementptr [6 x i8], ptr %.8, i64 0, i64 3
  %.20 = trunc i64 %.18 to i8
  store i8 %.20, ptr %.19
  %.21 = add i64 0, 9
  %.22 = getelementptr [6 x i8], ptr %.8, i64 0, i64 4
  %.23 = trunc i64 %.21 to i8
  store i8 %.23, ptr %.22
  %.24 = add i64 0, 15
  %.25 = getelementptr [6 x i8], ptr %.8, i64 0, i64 5
  %.26 = trunc i64 %.24 to i8
  store i8 %.26, ptr %.25
  %.28 = add i64 0, 0
  store i64 %.28, ptr %.27
  br label %L0
L0:
  %.29 = load i64, ptr %.27
  %.30 = add i64 0, 6
  %.31 = icmp slt i64 %.29, %.30
  br i1 %.31, label %L1, label %L3
L1:
  %.32 = add i64 0, 129
  %.33 = load i64, ptr %.27
  %.34 = getelementptr [6 x i8], ptr %.8, i64 0, i64 %.33
  %.35 = load i8, ptr %.34
  %.36 = zext i8 %.35 to i64
  %.37 = trunc i64 %.32 to i8
  %.38 = trunc i64 %.36 to i8
  call void @rot8__36f560f7(i8 %.37, i8 %.38)
  br label %L2
L2:
  %.39 = load i64, ptr %.27
  %.40 = add i64 %.39, 1
  store i64 %.40, ptr %.27
  br label %L0
L3:
  %.42 = add i64 0, 0
  %.43 = getelementptr [6 x i16], ptr %.41, i64 0, i64 0
  %.44 = trunc i64 %.42 to i16
  store i16 %.44, ptr %.43
  %.45 = add i64 0, 1
  %.46 = getelementptr [6 x i16], ptr %.41, i64 0, i64 1
  %.47 = trunc i64 %.45 to i16
  store i16 %.47, ptr %.46
  %.48 = add i64 0, 15
  %.49 = getelementptr [6 x i16], ptr %.41, i64 0, i64 2
  %.50 = trunc i64 %.48 to i16
  store i16 %.50, ptr %.49
  %.51 = add i64 0, 16
  %.52 = getelementptr [6 x i16], ptr %.41, i64 0, i64 3
  %.53 = trunc i64 %.51 to i16
  store i16 %.53, ptr %.52
  %.54 = add i64 0, 17
  %.55 = getelementptr [6 x i16], ptr %.41, i64 0, i64 4
  %.56 = trunc i64 %.54 to i16
  store i16 %.56, ptr %.55
  %.57 = add i64 0, 31
  %.58 = getelementptr [6 x i16], ptr %.41, i64 0, i64 5
  %.59 = trunc i64 %.57 to i16
  store i16 %.59, ptr %.58
  %.61 = add i64 0, 0
  store i64 %.61, ptr %.60
  br label %L4
L4:
  %.62 = load i64, ptr %.60
  %.63 = add i64 0, 6
  %.64 = icmp slt i64 %.62, %.63
  br i1 %.64, label %L5, label %L7
L5:
  %.65 = add i64 0, 32769
  %.66 = load i64, ptr %.60
  %.67 = getelementptr [6 x i16], ptr %.41, i64 0, i64 %.66
  %.68 = load i16, ptr %.67
  %.69 = zext i16 %.68 to i64
  %.70 = trunc i64 %.65 to i16
  %.71 = trunc i64 %.69 to i16
  call void @rot16__36f560f7(i16 %.70, i16 %.71)
  br label %L6
L6:
  %.72 = load i64, ptr %.60
  %.73 = add i64 %.72, 1
  store i64 %.73, ptr %.60
  br label %L4
L7:
  %.75 = add i64 0, 0
  %.76 = getelementptr [6 x i32], ptr %.74, i64 0, i64 0
  %.77 = trunc i64 %.75 to i32
  store i32 %.77, ptr %.76
  %.78 = add i64 0, 1
  %.79 = getelementptr [6 x i32], ptr %.74, i64 0, i64 1
  %.80 = trunc i64 %.78 to i32
  store i32 %.80, ptr %.79
  %.81 = add i64 0, 31
  %.82 = getelementptr [6 x i32], ptr %.74, i64 0, i64 2
  %.83 = trunc i64 %.81 to i32
  store i32 %.83, ptr %.82
  %.84 = add i64 0, 32
  %.85 = getelementptr [6 x i32], ptr %.74, i64 0, i64 3
  %.86 = trunc i64 %.84 to i32
  store i32 %.86, ptr %.85
  %.87 = add i64 0, 33
  %.88 = getelementptr [6 x i32], ptr %.74, i64 0, i64 4
  %.89 = trunc i64 %.87 to i32
  store i32 %.89, ptr %.88
  %.90 = add i64 0, 63
  %.91 = getelementptr [6 x i32], ptr %.74, i64 0, i64 5
  %.92 = trunc i64 %.90 to i32
  store i32 %.92, ptr %.91
  %.94 = add i64 0, 0
  store i64 %.94, ptr %.93
  br label %L8
L8:
  %.95 = load i64, ptr %.93
  %.96 = add i64 0, 6
  %.97 = icmp slt i64 %.95, %.96
  br i1 %.97, label %L9, label %L11
L9:
  %.98 = add i64 0, 2147483649
  %.99 = load i64, ptr %.93
  %.100 = getelementptr [6 x i32], ptr %.74, i64 0, i64 %.99
  %.101 = load i32, ptr %.100
  %.102 = zext i32 %.101 to i64
  %.103 = trunc i64 %.98 to i32
  %.104 = trunc i64 %.102 to i32
  call void @rot32__36f560f7(i32 %.103, i32 %.104)
  br label %L10
L10:
  %.105 = load i64, ptr %.93
  %.106 = add i64 %.105, 1
  store i64 %.106, ptr %.93
  br label %L8
L11:
  %.108 = add i64 0, 0
  %.109 = getelementptr [6 x i64], ptr %.107, i64 0, i64 0
  store i64 %.108, ptr %.109
  %.110 = add i64 0, 1
  %.111 = getelementptr [6 x i64], ptr %.107, i64 0, i64 1
  store i64 %.110, ptr %.111
  %.112 = add i64 0, 63
  %.113 = getelementptr [6 x i64], ptr %.107, i64 0, i64 2
  store i64 %.112, ptr %.113
  %.114 = add i64 0, 64
  %.115 = getelementptr [6 x i64], ptr %.107, i64 0, i64 3
  store i64 %.114, ptr %.115
  %.116 = add i64 0, 65
  %.117 = getelementptr [6 x i64], ptr %.107, i64 0, i64 4
  store i64 %.116, ptr %.117
  %.118 = add i64 0, 127
  %.119 = getelementptr [6 x i64], ptr %.107, i64 0, i64 5
  store i64 %.118, ptr %.119
  %.121 = add i64 0, 0
  store i64 %.121, ptr %.120
  br label %L12
L12:
  %.122 = load i64, ptr %.120
  %.123 = add i64 0, 6
  %.124 = icmp slt i64 %.122, %.123
  br i1 %.124, label %L13, label %L15
L13:
  %.125 = add i64 0, -9223372036854775807
  %.126 = load i64, ptr %.120
  %.127 = getelementptr [6 x i64], ptr %.107, i64 0, i64 %.126
  %.128 = load i64, ptr %.127
  call void @rot64__36f560f7(i64 %.125, i64 %.128)
  br label %L14
L14:
  %.129 = load i64, ptr %.120
  %.130 = add i64 %.129, 1
  store i64 %.130, ptr %.120
  br label %L12
L15:
  ret void
}

define void @bits8__36f560f7(i8 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i8
  store i8 %x.arg, ptr %.1
  %.2 = load i8, ptr %.1
  %.3 = zext i8 %.2 to i64
  %.4 = trunc i64 %.3 to i8
  %.5 = call i8 @llvm.ctlz.i8(i8 %.4, i1 false)
  %.6 = zext i8 %.5 to i64
  call void @rt_hex(i64 %.6)
  %.7 = load i8, ptr %.1
  %.8 = zext i8 %.7 to i64
  %.9 = trunc i64 %.8 to i8
  %.10 = call i8 @llvm.cttz.i8(i8 %.9, i1 false)
  %.11 = zext i8 %.10 to i64
  call void @rt_hex(i64 %.11)
  %.12 = load i8, ptr %.1
  %.13 = zext i8 %.12 to i64
  %.14 = trunc i64 %.13 to i8
  %.15 = call i8 @llvm.ctpop.i8(i8 %.14)
  %.16 = zext i8 %.15 to i64
  call void @rt_hex(i64 %.16)
  ret void
}

define void @bits16__36f560f7(i16 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i16
  store i16 %x.arg, ptr %.1
  %.2 = load i16, ptr %.1
  %.3 = zext i16 %.2 to i64
  %.4 = trunc i64 %.3 to i16
  %.5 = call i16 @llvm.ctlz.i16(i16 %.4, i1 false)
  %.6 = zext i16 %.5 to i64
  call void @rt_hex(i64 %.6)
  %.7 = load i16, ptr %.1
  %.8 = zext i16 %.7 to i64
  %.9 = trunc i64 %.8 to i16
  %.10 = call i16 @llvm.cttz.i16(i16 %.9, i1 false)
  %.11 = zext i16 %.10 to i64
  call void @rt_hex(i64 %.11)
  %.12 = load i16, ptr %.1
  %.13 = zext i16 %.12 to i64
  %.14 = trunc i64 %.13 to i16
  %.15 = call i16 @llvm.ctpop.i16(i16 %.14)
  %.16 = zext i16 %.15 to i64
  call void @rt_hex(i64 %.16)
  ret void
}

define void @bits32__36f560f7(i32 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  store i32 %x.arg, ptr %.1
  %.2 = load i32, ptr %.1
  %.3 = zext i32 %.2 to i64
  %.4 = trunc i64 %.3 to i32
  %.5 = call i32 @llvm.ctlz.i32(i32 %.4, i1 false)
  %.6 = zext i32 %.5 to i64
  call void @rt_hex(i64 %.6)
  %.7 = load i32, ptr %.1
  %.8 = zext i32 %.7 to i64
  %.9 = trunc i64 %.8 to i32
  %.10 = call i32 @llvm.cttz.i32(i32 %.9, i1 false)
  %.11 = zext i32 %.10 to i64
  call void @rt_hex(i64 %.11)
  %.12 = load i32, ptr %.1
  %.13 = zext i32 %.12 to i64
  %.14 = trunc i64 %.13 to i32
  %.15 = call i32 @llvm.ctpop.i32(i32 %.14)
  %.16 = zext i32 %.15 to i64
  call void @rt_hex(i64 %.16)
  ret void
}

define void @bits64__36f560f7(i64 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  store i64 %x.arg, ptr %.1
  %.2 = load i64, ptr %.1
  %.3 = call i64 @llvm.ctlz.i64(i64 %.2, i1 false)
  call void @rt_hex(i64 %.3)
  %.4 = load i64, ptr %.1
  %.5 = call i64 @llvm.cttz.i64(i64 %.4, i1 false)
  call void @rt_hex(i64 %.5)
  %.6 = load i64, ptr %.1
  %.7 = call i64 @llvm.ctpop.i64(i64 %.6)
  call void @rt_hex(i64 %.7)
  ret void
}

define void @count_rows__36f560f7() alignstack(16) "no-builtins" {
entry:
  %.8 = alloca [5 x i8]
  %.24 = alloca i64
  %.36 = alloca [5 x i16]
  %.52 = alloca i64
  %.64 = alloca [5 x i32]
  %.80 = alloca i64
  %.92 = alloca [5 x i64]
  %.103 = alloca i64
  %.1 = getelementptr [17 x i8], ptr @.str.26, i64 0, i64 0
  %.2 = insertvalue %Span$u8 undef, ptr %.1, 0
  %.3 = insertvalue %Span$u8 %.2, i64 16, 1
  %.4 = extractvalue %Span$u8 %.3, 0
  %.5 = extractvalue %Span$u8 %.3, 1
  %.6 = insertvalue %StrView undef, ptr %.4, 0
  %.7 = insertvalue %StrView %.6, i64 %.5, 1
  call void @say__36f560f7(%StrView %.7)
  %.9 = add i64 0, 0
  %.10 = getelementptr [5 x i8], ptr %.8, i64 0, i64 0
  %.11 = trunc i64 %.9 to i8
  store i8 %.11, ptr %.10
  %.12 = add i64 0, 1
  %.13 = getelementptr [5 x i8], ptr %.8, i64 0, i64 1
  %.14 = trunc i64 %.12 to i8
  store i8 %.14, ptr %.13
  %.15 = add i64 0, 128
  %.16 = getelementptr [5 x i8], ptr %.8, i64 0, i64 2
  %.17 = trunc i64 %.15 to i8
  store i8 %.17, ptr %.16
  %.18 = add i64 0, 255
  %.19 = getelementptr [5 x i8], ptr %.8, i64 0, i64 3
  %.20 = trunc i64 %.18 to i8
  store i8 %.20, ptr %.19
  %.21 = add i64 0, 85
  %.22 = getelementptr [5 x i8], ptr %.8, i64 0, i64 4
  %.23 = trunc i64 %.21 to i8
  store i8 %.23, ptr %.22
  %.25 = add i64 0, 0
  store i64 %.25, ptr %.24
  br label %L0
L0:
  %.26 = load i64, ptr %.24
  %.27 = add i64 0, 5
  %.28 = icmp slt i64 %.26, %.27
  br i1 %.28, label %L1, label %L3
L1:
  %.29 = load i64, ptr %.24
  %.30 = getelementptr [5 x i8], ptr %.8, i64 0, i64 %.29
  %.31 = load i8, ptr %.30
  %.32 = zext i8 %.31 to i64
  %.33 = trunc i64 %.32 to i8
  call void @bits8__36f560f7(i8 %.33)
  br label %L2
L2:
  %.34 = load i64, ptr %.24
  %.35 = add i64 %.34, 1
  store i64 %.35, ptr %.24
  br label %L0
L3:
  %.37 = add i64 0, 0
  %.38 = getelementptr [5 x i16], ptr %.36, i64 0, i64 0
  %.39 = trunc i64 %.37 to i16
  store i16 %.39, ptr %.38
  %.40 = add i64 0, 1
  %.41 = getelementptr [5 x i16], ptr %.36, i64 0, i64 1
  %.42 = trunc i64 %.40 to i16
  store i16 %.42, ptr %.41
  %.43 = add i64 0, 32768
  %.44 = getelementptr [5 x i16], ptr %.36, i64 0, i64 2
  %.45 = trunc i64 %.43 to i16
  store i16 %.45, ptr %.44
  %.46 = add i64 0, 65535
  %.47 = getelementptr [5 x i16], ptr %.36, i64 0, i64 3
  %.48 = trunc i64 %.46 to i16
  store i16 %.48, ptr %.47
  %.49 = add i64 0, 21845
  %.50 = getelementptr [5 x i16], ptr %.36, i64 0, i64 4
  %.51 = trunc i64 %.49 to i16
  store i16 %.51, ptr %.50
  %.53 = add i64 0, 0
  store i64 %.53, ptr %.52
  br label %L4
L4:
  %.54 = load i64, ptr %.52
  %.55 = add i64 0, 5
  %.56 = icmp slt i64 %.54, %.55
  br i1 %.56, label %L5, label %L7
L5:
  %.57 = load i64, ptr %.52
  %.58 = getelementptr [5 x i16], ptr %.36, i64 0, i64 %.57
  %.59 = load i16, ptr %.58
  %.60 = zext i16 %.59 to i64
  %.61 = trunc i64 %.60 to i16
  call void @bits16__36f560f7(i16 %.61)
  br label %L6
L6:
  %.62 = load i64, ptr %.52
  %.63 = add i64 %.62, 1
  store i64 %.63, ptr %.52
  br label %L4
L7:
  %.65 = add i64 0, 0
  %.66 = getelementptr [5 x i32], ptr %.64, i64 0, i64 0
  %.67 = trunc i64 %.65 to i32
  store i32 %.67, ptr %.66
  %.68 = add i64 0, 1
  %.69 = getelementptr [5 x i32], ptr %.64, i64 0, i64 1
  %.70 = trunc i64 %.68 to i32
  store i32 %.70, ptr %.69
  %.71 = add i64 0, 2147483648
  %.72 = getelementptr [5 x i32], ptr %.64, i64 0, i64 2
  %.73 = trunc i64 %.71 to i32
  store i32 %.73, ptr %.72
  %.74 = add i64 0, 4294967295
  %.75 = getelementptr [5 x i32], ptr %.64, i64 0, i64 3
  %.76 = trunc i64 %.74 to i32
  store i32 %.76, ptr %.75
  %.77 = add i64 0, 1431655765
  %.78 = getelementptr [5 x i32], ptr %.64, i64 0, i64 4
  %.79 = trunc i64 %.77 to i32
  store i32 %.79, ptr %.78
  %.81 = add i64 0, 0
  store i64 %.81, ptr %.80
  br label %L8
L8:
  %.82 = load i64, ptr %.80
  %.83 = add i64 0, 5
  %.84 = icmp slt i64 %.82, %.83
  br i1 %.84, label %L9, label %L11
L9:
  %.85 = load i64, ptr %.80
  %.86 = getelementptr [5 x i32], ptr %.64, i64 0, i64 %.85
  %.87 = load i32, ptr %.86
  %.88 = zext i32 %.87 to i64
  %.89 = trunc i64 %.88 to i32
  call void @bits32__36f560f7(i32 %.89)
  br label %L10
L10:
  %.90 = load i64, ptr %.80
  %.91 = add i64 %.90, 1
  store i64 %.91, ptr %.80
  br label %L8
L11:
  %.93 = add i64 0, 0
  %.94 = getelementptr [5 x i64], ptr %.92, i64 0, i64 0
  store i64 %.93, ptr %.94
  %.95 = add i64 0, 1
  %.96 = getelementptr [5 x i64], ptr %.92, i64 0, i64 1
  store i64 %.95, ptr %.96
  %.97 = add i64 0, -9223372036854775808
  %.98 = getelementptr [5 x i64], ptr %.92, i64 0, i64 2
  store i64 %.97, ptr %.98
  %.99 = add i64 0, -1
  %.100 = getelementptr [5 x i64], ptr %.92, i64 0, i64 3
  store i64 %.99, ptr %.100
  %.101 = add i64 0, 6148914691236517205
  %.102 = getelementptr [5 x i64], ptr %.92, i64 0, i64 4
  store i64 %.101, ptr %.102
  %.104 = add i64 0, 0
  store i64 %.104, ptr %.103
  br label %L12
L12:
  %.105 = load i64, ptr %.103
  %.106 = add i64 0, 5
  %.107 = icmp slt i64 %.105, %.106
  br i1 %.107, label %L13, label %L15
L13:
  %.108 = load i64, ptr %.103
  %.109 = getelementptr [5 x i64], ptr %.92, i64 0, i64 %.108
  %.110 = load i64, ptr %.109
  call void @bits64__36f560f7(i64 %.110)
  br label %L14
L14:
  %.111 = load i64, ptr %.103
  %.112 = add i64 %.111, 1
  store i64 %.112, ptr %.103
  br label %L12
L15:
  ret void
}

define i16 @swap16__36f560f7(i16 %x.arg) alignstack(16) "no-builtins" {
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

define i32 @swap32__36f560f7(i32 %x.arg) alignstack(16) "no-builtins" {
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

define i64 @swap64__36f560f7(i64 %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  store i64 %x.arg, ptr %.1
  %.2 = load i64, ptr %.1
  %.3 = call i64 @llvm.bswap.i64(i64 %.2)
  ret i64 %.3
}

define void @bswap_rows__36f560f7() alignstack(16) "no-builtins" {
entry:
  %.1 = getelementptr [7 x i8], ptr @.str.27, i64 0, i64 0
  %.2 = insertvalue %Span$u8 undef, ptr %.1, 0
  %.3 = insertvalue %Span$u8 %.2, i64 6, 1
  %.4 = extractvalue %Span$u8 %.3, 0
  %.5 = extractvalue %Span$u8 %.3, 1
  %.6 = insertvalue %StrView undef, ptr %.4, 0
  %.7 = insertvalue %StrView %.6, i64 %.5, 1
  call void @say__36f560f7(%StrView %.7)
  %.8 = add i64 0, 4660
  %.9 = trunc i64 %.8 to i16
  %.10 = call i16 @swap16__36f560f7(i16 %.9)
  %.11 = zext i16 %.10 to i64
  %.12 = trunc i64 %.11 to i16
  %.13 = zext i16 %.12 to i64
  call void @rt_hex(i64 %.13)
  %.14 = add i64 0, 305419896
  %.15 = trunc i64 %.14 to i32
  %.16 = call i32 @swap32__36f560f7(i32 %.15)
  %.17 = zext i32 %.16 to i64
  %.18 = trunc i64 %.17 to i32
  %.19 = zext i32 %.18 to i64
  call void @rt_hex(i64 %.19)
  %.20 = add i64 0, 81985529216486895
  %.21 = call i64 @swap64__36f560f7(i64 %.20)
  call void @rt_hex(i64 %.21)
  ret void
}

define double @f64_of__36f560f7(i64 %bits.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.4 = alloca i64
  store i64 %bits.arg, ptr %.1
  %.3 = load i64, ptr %.1
  store i64 %.3, ptr %.2
  %.5 = ptrtoint ptr %.2 to i64
  store i64 %.5, ptr %.4
  %.6 = load i64, ptr %.4
  %.7 = inttoptr i64 %.6 to ptr
  %.8 = load double, ptr %.7
  ret double %.8
}

define i64 @f64_bits__36f560f7(double %x.arg) alignstack(16) "no-builtins" {
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

define float @f32_of__36f560f7(i32 %bits.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca i32
  %.6 = alloca i64
  store i32 %bits.arg, ptr %.1
  %.3 = load i32, ptr %.1
  %.4 = zext i32 %.3 to i64
  %.5 = trunc i64 %.4 to i32
  store i32 %.5, ptr %.2
  %.7 = ptrtoint ptr %.2 to i64
  store i64 %.7, ptr %.6
  %.8 = load i64, ptr %.6
  %.9 = inttoptr i64 %.8 to ptr
  %.10 = load float, ptr %.9
  ret float %.10
}

define i64 @f32_bits__36f560f7(float %x.arg) alignstack(16) "no-builtins" {
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

define double @abs64__36f560f7(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  store double %x.arg, ptr %.1
  %.2 = load double, ptr %.1
  %.3 = call double @llvm.fabs.f64(double %.2)
  ret double %.3
}

define float @abs32__36f560f7(float %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca float
  store float %x.arg, ptr %.1
  %.2 = load float, ptr %.1
  %.3 = call float @llvm.fabs.f32(float %.2)
  ret float %.3
}

define void @fabs_rows__36f560f7() alignstack(16) "no-builtins" {
entry:
  %.8 = alloca [4 x i64]
  %.17 = alloca i64
  %.22 = alloca double
  %.32 = alloca [4 x i32]
  %.45 = alloca i64
  %.50 = alloca float
  %.1 = getelementptr [6 x i8], ptr @.str.28, i64 0, i64 0
  %.2 = insertvalue %Span$u8 undef, ptr %.1, 0
  %.3 = insertvalue %Span$u8 %.2, i64 5, 1
  %.4 = extractvalue %Span$u8 %.3, 0
  %.5 = extractvalue %Span$u8 %.3, 1
  %.6 = insertvalue %StrView undef, ptr %.4, 0
  %.7 = insertvalue %StrView %.6, i64 %.5, 1
  call void @say__36f560f7(%StrView %.7)
  %.9 = add i64 0, -9223372036854775808
  %.10 = getelementptr [4 x i64], ptr %.8, i64 0, i64 0
  store i64 %.9, ptr %.10
  %.11 = add i64 0, 9221120237041090560
  %.12 = getelementptr [4 x i64], ptr %.8, i64 0, i64 1
  store i64 %.11, ptr %.12
  %.13 = add i64 0, 9218868437227405312
  %.14 = getelementptr [4 x i64], ptr %.8, i64 0, i64 2
  store i64 %.13, ptr %.14
  %.15 = add i64 0, -4503599627370496
  %.16 = getelementptr [4 x i64], ptr %.8, i64 0, i64 3
  store i64 %.15, ptr %.16
  %.18 = add i64 0, 0
  store i64 %.18, ptr %.17
  br label %L0
L0:
  %.19 = load i64, ptr %.17
  %.20 = add i64 0, 4
  %.21 = icmp slt i64 %.19, %.20
  br i1 %.21, label %L1, label %L3
L1:
  %.23 = load i64, ptr %.17
  %.24 = getelementptr [4 x i64], ptr %.8, i64 0, i64 %.23
  %.25 = load i64, ptr %.24
  %.26 = call double @f64_of__36f560f7(i64 %.25)
  store double %.26, ptr %.22
  %.27 = load double, ptr %.22
  %.28 = call double @abs64__36f560f7(double %.27)
  %.29 = call i64 @f64_bits__36f560f7(double %.28)
  call void @rt_hex(i64 %.29)
  br label %L2
L2:
  %.30 = load i64, ptr %.17
  %.31 = add i64 %.30, 1
  store i64 %.31, ptr %.17
  br label %L0
L3:
  %.33 = add i64 0, 2147483648
  %.34 = getelementptr [4 x i32], ptr %.32, i64 0, i64 0
  %.35 = trunc i64 %.33 to i32
  store i32 %.35, ptr %.34
  %.36 = add i64 0, 2143289344
  %.37 = getelementptr [4 x i32], ptr %.32, i64 0, i64 1
  %.38 = trunc i64 %.36 to i32
  store i32 %.38, ptr %.37
  %.39 = add i64 0, 2139095040
  %.40 = getelementptr [4 x i32], ptr %.32, i64 0, i64 2
  %.41 = trunc i64 %.39 to i32
  store i32 %.41, ptr %.40
  %.42 = add i64 0, 4286578688
  %.43 = getelementptr [4 x i32], ptr %.32, i64 0, i64 3
  %.44 = trunc i64 %.42 to i32
  store i32 %.44, ptr %.43
  %.46 = add i64 0, 0
  store i64 %.46, ptr %.45
  br label %L4
L4:
  %.47 = load i64, ptr %.45
  %.48 = add i64 0, 4
  %.49 = icmp slt i64 %.47, %.48
  br i1 %.49, label %L5, label %L7
L5:
  %.51 = load i64, ptr %.45
  %.52 = getelementptr [4 x i32], ptr %.32, i64 0, i64 %.51
  %.53 = load i32, ptr %.52
  %.54 = zext i32 %.53 to i64
  %.55 = trunc i64 %.54 to i32
  %.56 = call float @f32_of__36f560f7(i32 %.55)
  store float %.56, ptr %.50
  %.57 = load float, ptr %.50
  %.58 = call float @abs32__36f560f7(float %.57)
  %.59 = call i64 @f32_bits__36f560f7(float %.58)
  call void @rt_hex(i64 %.59)
  br label %L6
L6:
  %.60 = load i64, ptr %.45
  %.61 = add i64 %.60, 1
  store i64 %.61, ptr %.45
  br label %L4
L7:
  ret void
}

define void @sat64__36f560f7(double %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca double
  store double %x.arg, ptr %.1
  %.2 = load double, ptr %.1
  %.3 = call i8 @llvm.fptosi.sat.i8.f64(double %.2)
  %.4 = sext i8 %.3 to i64
  %.5 = trunc i64 %.4 to i8
  %.6 = sext i8 %.5 to i64
  call void @put__36f560f7(i64 %.6)
  %.7 = load double, ptr %.1
  %.8 = call i16 @llvm.fptosi.sat.i16.f64(double %.7)
  %.9 = sext i16 %.8 to i64
  %.10 = trunc i64 %.9 to i16
  %.11 = sext i16 %.10 to i64
  call void @put__36f560f7(i64 %.11)
  %.12 = load double, ptr %.1
  %.13 = call i32 @llvm.fptosi.sat.i32.f64(double %.12)
  %.14 = sext i32 %.13 to i64
  %.15 = trunc i64 %.14 to i32
  %.16 = sext i32 %.15 to i64
  call void @put__36f560f7(i64 %.16)
  %.17 = load double, ptr %.1
  %.18 = call i64 @llvm.fptosi.sat.i64.f64(double %.17)
  call void @put__36f560f7(i64 %.18)
  %.19 = load double, ptr %.1
  %.20 = call i8 @llvm.fptoui.sat.i8.f64(double %.19)
  %.21 = zext i8 %.20 to i64
  %.22 = trunc i64 %.21 to i8
  %.23 = zext i8 %.22 to i64
  call void @rt_hex(i64 %.23)
  %.24 = load double, ptr %.1
  %.25 = call i16 @llvm.fptoui.sat.i16.f64(double %.24)
  %.26 = zext i16 %.25 to i64
  %.27 = trunc i64 %.26 to i16
  %.28 = zext i16 %.27 to i64
  call void @rt_hex(i64 %.28)
  %.29 = load double, ptr %.1
  %.30 = call i32 @llvm.fptoui.sat.i32.f64(double %.29)
  %.31 = zext i32 %.30 to i64
  %.32 = trunc i64 %.31 to i32
  %.33 = zext i32 %.32 to i64
  call void @rt_hex(i64 %.33)
  %.34 = load double, ptr %.1
  %.35 = call i64 @llvm.fptoui.sat.i64.f64(double %.34)
  call void @rt_hex(i64 %.35)
  ret void
}

define void @sat32__36f560f7(float %x.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca float
  store float %x.arg, ptr %.1
  %.2 = load float, ptr %.1
  %.3 = call i8 @llvm.fptosi.sat.i8.f32(float %.2)
  %.4 = sext i8 %.3 to i64
  %.5 = trunc i64 %.4 to i8
  %.6 = sext i8 %.5 to i64
  call void @put__36f560f7(i64 %.6)
  %.7 = load float, ptr %.1
  %.8 = call i16 @llvm.fptosi.sat.i16.f32(float %.7)
  %.9 = sext i16 %.8 to i64
  %.10 = trunc i64 %.9 to i16
  %.11 = sext i16 %.10 to i64
  call void @put__36f560f7(i64 %.11)
  %.12 = load float, ptr %.1
  %.13 = call i32 @llvm.fptosi.sat.i32.f32(float %.12)
  %.14 = sext i32 %.13 to i64
  %.15 = trunc i64 %.14 to i32
  %.16 = sext i32 %.15 to i64
  call void @put__36f560f7(i64 %.16)
  %.17 = load float, ptr %.1
  %.18 = call i64 @llvm.fptosi.sat.i64.f32(float %.17)
  call void @put__36f560f7(i64 %.18)
  %.19 = load float, ptr %.1
  %.20 = call i8 @llvm.fptoui.sat.i8.f32(float %.19)
  %.21 = zext i8 %.20 to i64
  %.22 = trunc i64 %.21 to i8
  %.23 = zext i8 %.22 to i64
  call void @rt_hex(i64 %.23)
  %.24 = load float, ptr %.1
  %.25 = call i16 @llvm.fptoui.sat.i16.f32(float %.24)
  %.26 = zext i16 %.25 to i64
  %.27 = trunc i64 %.26 to i16
  %.28 = zext i16 %.27 to i64
  call void @rt_hex(i64 %.28)
  %.29 = load float, ptr %.1
  %.30 = call i32 @llvm.fptoui.sat.i32.f32(float %.29)
  %.31 = zext i32 %.30 to i64
  %.32 = trunc i64 %.31 to i32
  %.33 = zext i32 %.32 to i64
  call void @rt_hex(i64 %.33)
  %.34 = load float, ptr %.1
  %.35 = call i64 @llvm.fptoui.sat.i64.f32(float %.34)
  call void @rt_hex(i64 %.35)
  ret void
}

define void @sat_rows__36f560f7() alignstack(16) "no-builtins" {
entry:
  %.8 = alloca i64
  %.26 = alloca i64
  %.1 = getelementptr [27 x i8], ptr @.str.29, i64 0, i64 0
  %.2 = insertvalue %Span$u8 undef, ptr %.1, 0
  %.3 = insertvalue %Span$u8 %.2, i64 26, 1
  %.4 = extractvalue %Span$u8 %.3, 0
  %.5 = extractvalue %Span$u8 %.3, 1
  %.6 = insertvalue %StrView undef, ptr %.4, 0
  %.7 = insertvalue %StrView %.6, i64 %.5, 1
  call void @say__36f560f7(%StrView %.7)
  %.9 = add i64 0, 0
  store i64 %.9, ptr %.8
  br label %L0
L0:
  %.10 = load i64, ptr %.8
  %.11 = add i64 0, 24
  %.12 = icmp slt i64 %.10, %.11
  br i1 %.12, label %L1, label %L3
L1:
  %.13 = load i64, ptr %.8
  %.14 = getelementptr [24 x i64], ptr @SAT_F64, i64 0, i64 %.13
  %.15 = load i64, ptr %.14
  %.16 = call double @f64_of__36f560f7(i64 %.15)
  call void @sat64__36f560f7(double %.16)
  br label %L2
L2:
  %.17 = load i64, ptr %.8
  %.18 = add i64 %.17, 1
  store i64 %.18, ptr %.8
  br label %L0
L3:
  %.19 = getelementptr [27 x i8], ptr @.str.30, i64 0, i64 0
  %.20 = insertvalue %Span$u8 undef, ptr %.19, 0
  %.21 = insertvalue %Span$u8 %.20, i64 26, 1
  %.22 = extractvalue %Span$u8 %.21, 0
  %.23 = extractvalue %Span$u8 %.21, 1
  %.24 = insertvalue %StrView undef, ptr %.22, 0
  %.25 = insertvalue %StrView %.24, i64 %.23, 1
  call void @say__36f560f7(%StrView %.25)
  %.27 = add i64 0, 0
  store i64 %.27, ptr %.26
  br label %L4
L4:
  %.28 = load i64, ptr %.26
  %.29 = add i64 0, 20
  %.30 = icmp slt i64 %.28, %.29
  br i1 %.30, label %L5, label %L7
L5:
  %.31 = load i64, ptr %.26
  %.32 = getelementptr [20 x i32], ptr @SAT_F32, i64 0, i64 %.31
  %.33 = load i32, ptr %.32
  %.34 = zext i32 %.33 to i64
  %.35 = trunc i64 %.34 to i32
  %.36 = call float @f32_of__36f560f7(i32 %.35)
  call void @sat32__36f560f7(float %.36)
  br label %L6
L6:
  %.37 = load i64, ptr %.26
  %.38 = add i64 %.37, 1
  store i64 %.38, ptr %.26
  br label %L4
L7:
  ret void
}

define i32 @main() alignstack(16) "no-builtins" {
entry:
  call void @overflow_rows__36f560f7()
  call void @rotate_rows__36f560f7()
  call void @count_rows__36f560f7()
  call void @bswap_rows__36f560f7()
  call void @fabs_rows__36f560f7()
  call void @sat_rows__36f560f7()
  %.1 = getelementptr [10 x i8], ptr @.str.31, i64 0, i64 0
  %.2 = insertvalue %Span$u8 undef, ptr %.1, 0
  %.3 = insertvalue %Span$u8 %.2, i64 9, 1
  %.4 = extractvalue %Span$u8 %.3, 0
  %.5 = extractvalue %Span$u8 %.3, 1
  %.6 = insertvalue %StrView undef, ptr %.4, 0
  %.7 = insertvalue %StrView %.6, i64 %.5, 1
  call void @say__36f560f7(%StrView %.7)
  %.8 = add i64 0, 2147483647
  %.9 = add i64 0, 1
  %.10 = trunc i64 %.8 to i32
  %.11 = trunc i64 %.9 to i32
  %.12 = call i32 @sadd32__36f560f7(i32 %.10, i32 %.11)
  %.13 = sext i32 %.12 to i64
  %.14 = trunc i64 %.13 to i32
  %.15 = sext i32 %.14 to i64
  call void @put__36f560f7(i64 %.15)
  %.16 = add i64 0, 0
  %.17 = trunc i64 %.16 to i32
  ret i32 %.17
}


@.str.0 = private constant [47 x i8] c"intrin_run.ritz:16:5: integer overflow in `+`\0A\00"
@.str.1 = private constant [47 x i8] c"intrin_run.ritz:18:5: integer overflow in `-`\0A\00"
@.str.2 = private constant [47 x i8] c"intrin_run.ritz:20:5: integer overflow in `*`\0A\00"
@.str.3 = private constant [47 x i8] c"intrin_run.ritz:22:5: integer overflow in `+`\0A\00"
@.str.4 = private constant [47 x i8] c"intrin_run.ritz:24:5: integer overflow in `-`\0A\00"
@.str.5 = private constant [47 x i8] c"intrin_run.ritz:26:5: integer overflow in `*`\0A\00"
@.str.6 = private constant [47 x i8] c"intrin_run.ritz:28:5: integer overflow in `+`\0A\00"
@.str.7 = private constant [47 x i8] c"intrin_run.ritz:30:5: integer overflow in `-`\0A\00"
@.str.8 = private constant [47 x i8] c"intrin_run.ritz:32:5: integer overflow in `*`\0A\00"
@.str.9 = private constant [47 x i8] c"intrin_run.ritz:34:5: integer overflow in `+`\0A\00"
@.str.10 = private constant [47 x i8] c"intrin_run.ritz:36:5: integer overflow in `-`\0A\00"
@.str.11 = private constant [47 x i8] c"intrin_run.ritz:38:5: integer overflow in `*`\0A\00"
@.str.12 = private constant [47 x i8] c"intrin_run.ritz:40:5: integer overflow in `+`\0A\00"
@.str.13 = private constant [47 x i8] c"intrin_run.ritz:42:5: integer overflow in `-`\0A\00"
@.str.14 = private constant [47 x i8] c"intrin_run.ritz:44:5: integer overflow in `*`\0A\00"
@.str.15 = private constant [47 x i8] c"intrin_run.ritz:46:5: integer overflow in `+`\0A\00"
@.str.16 = private constant [47 x i8] c"intrin_run.ritz:48:5: integer overflow in `-`\0A\00"
@.str.17 = private constant [47 x i8] c"intrin_run.ritz:50:5: integer overflow in `*`\0A\00"
@.str.18 = private constant [47 x i8] c"intrin_run.ritz:52:5: integer overflow in `+`\0A\00"
@.str.19 = private constant [47 x i8] c"intrin_run.ritz:54:5: integer overflow in `-`\0A\00"
@.str.20 = private constant [47 x i8] c"intrin_run.ritz:56:5: integer overflow in `*`\0A\00"
@.str.21 = private constant [47 x i8] c"intrin_run.ritz:58:5: integer overflow in `+`\0A\00"
@.str.22 = private constant [47 x i8] c"intrin_run.ritz:60:5: integer overflow in `-`\0A\00"
@.str.23 = private constant [47 x i8] c"intrin_run.ritz:62:5: integer overflow in `*`\0A\00"
@.str.24 = private constant [15 x i8] c"with.overflow\0A\00"
@.str.25 = private constant [11 x i8] c"fshl/fshr\0A\00"
@.str.26 = private constant [17 x i8] c"ctlz/cttz/ctpop\0A\00"
@.str.27 = private constant [7 x i8] c"bswap\0A\00"
@.str.28 = private constant [6 x i8] c"fabs\0A\00"
@.str.29 = private constant [27 x i8] c"fptosi.sat/fptoui.sat f64\0A\00"
@.str.30 = private constant [27 x i8] c"fptosi.sat/fptoui.sat f32\0A\00"
@.str.31 = private constant [10 x i8] c"overflow\0A\00"
declare i64 @rt_write(...) "no-builtins"
declare void @rt_hex(...) "no-builtins"

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
