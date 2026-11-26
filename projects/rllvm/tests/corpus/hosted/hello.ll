; ModuleID = 'ritz1_output'
target triple = "x86_64-unknown-linux-gnu"

%Span$u8 = type {ptr, i64}
%StrView = type {ptr, i64}





define void @say__ff9282ec(%StrView %s.arg) alignstack(16) "no-builtins" {
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

define i64 @fib__ff9282ec(i64 %n.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.4 = alloca i64
  %.6 = alloca i64
  %.11 = alloca i64
  store i64 %n.arg, ptr %.1
  %.3 = add i64 0, 0
  store i64 %.3, ptr %.2
  %.5 = add i64 0, 1
  store i64 %.5, ptr %.4
  %.7 = add i64 0, 0
  store i64 %.7, ptr %.6
  br label %L0
L0:
  %.8 = load i64, ptr %.6
  %.9 = load i64, ptr %.1
  %.10 = icmp slt i64 %.8, %.9
  br i1 %.10, label %L1, label %L3
L1:
  %.12 = load i64, ptr %.2
  %.13 = load i64, ptr %.4
  %.14 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.12, i64 %.13)
  %.15 = extractvalue { i64, i1 } %.14, 0
  %.16 = extractvalue { i64, i1 } %.14, 1
  br i1 %.16, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.0, i64 42)
  unreachable
L5:
  store i64 %.15, ptr %.11
  %.17 = load i64, ptr %.4
  store i64 %.17, ptr %.2
  %.18 = load i64, ptr %.11
  store i64 %.18, ptr %.4
  br label %L2
L2:
  %.19 = load i64, ptr %.6
  %.20 = add i64 %.19, 1
  store i64 %.20, ptr %.6
  br label %L0
L3:
  %.21 = load i64, ptr %.2
  ret i64 %.21
}

define i64 @mix__ff9282ec(i64 %x.arg, i64 %y.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %x.arg, ptr %.1
  store i64 %y.arg, ptr %.2
  %.3 = load i64, ptr %.1
  %.4 = load i64, ptr %.2
  %.5 = add i64 0, 7
  %.6 = icmp uge i64 %.5, 64
  br i1 %.6, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.1, i64 51)
  unreachable
L1:
  %.7 = shl i64 %.4, %.5
  %.8 = xor i64 %.3, %.7
  %.9 = load i64, ptr %.2
  %.10 = add i64 0, 3
  %.11 = icmp uge i64 %.10, 64
  br i1 %.11, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.2, i64 51)
  unreachable
L3:
  %.12 = lshr i64 %.9, %.10
  %.13 = add i64 %.8, %.12
  %.14 = add i64 0, -7046029254386353131
  %.15 = mul i64 %.13, %.14
  ret i64 %.15
}

define i32 @main() alignstack(16) "no-builtins" {
entry:
  %.10 = alloca i64
  %.12 = alloca i64
  %.49 = alloca i64
  %.51 = alloca i64
  %.1 = getelementptr [29 x i8], ptr @.str.3, i64 0, i64 0
  %.2 = insertvalue %Span$u8 undef, ptr %.1, 0
  %.3 = insertvalue %Span$u8 %.2, i64 28, 1
  %.4 = extractvalue %Span$u8 %.3, 0
  %.5 = extractvalue %Span$u8 %.3, 1
  %.6 = insertvalue %StrView undef, ptr %.4, 0
  %.7 = insertvalue %StrView %.6, i64 %.5, 1
  call void @say__ff9282ec(%StrView %.7)
  %.8 = add i64 0, 50
  %.9 = call i64 @fib__ff9282ec(i64 %.8)
  call void @rt_hex(i64 %.9)
  %.11 = add i64 0, 0
  store i64 %.11, ptr %.10
  %.13 = add i64 0, 0
  store i64 %.13, ptr %.12
  br label %L0
L0:
  %.14 = load i64, ptr %.12
  %.15 = add i64 0, 1000
  %.16 = icmp slt i64 %.14, %.15
  br i1 %.16, label %L1, label %L3
L1:
  %.17 = load i64, ptr %.10
  %.18 = load i64, ptr %.12
  %.19 = load i64, ptr %.12
  %.20 = call { i64, i1 } @llvm.smul.with.overflow.i64(i64 %.18, i64 %.19)
  %.21 = extractvalue { i64, i1 } %.20, 0
  %.22 = extractvalue { i64, i1 } %.20, 1
  br i1 %.22, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.4, i64 42)
  unreachable
L5:
  %.23 = load i64, ptr %.12
  %.24 = add i64 0, 3
  %.25 = icmp eq i64 %.24, 0
  br i1 %.25, label %L6, label %L7
L6:
  call void @__ritz_overflow_trap(ptr @.str.5, i64 42)
  unreachable
L7:
  %.26 = icmp eq i64 %.23, -9223372036854775808
  %.27 = icmp eq i64 %.24, -1
  %.28 = and i1 %.26, %.27
  br i1 %.28, label %L8, label %L9
L8:
  call void @__ritz_overflow_trap(ptr @.str.6, i64 42)
  unreachable
L9:
  %.29 = sdiv i64 %.23, %.24
  %.30 = call { i64, i1 } @llvm.ssub.with.overflow.i64(i64 %.21, i64 %.29)
  %.31 = extractvalue { i64, i1 } %.30, 0
  %.32 = extractvalue { i64, i1 } %.30, 1
  br i1 %.32, label %L10, label %L11
L10:
  call void @__ritz_overflow_trap(ptr @.str.7, i64 42)
  unreachable
L11:
  %.33 = load i64, ptr %.12
  %.34 = add i64 0, 7
  %.35 = icmp eq i64 %.34, 0
  br i1 %.35, label %L12, label %L13
L12:
  call void @__ritz_overflow_trap(ptr @.str.8, i64 42)
  unreachable
L13:
  %.36 = icmp eq i64 %.33, -9223372036854775808
  %.37 = icmp eq i64 %.34, -1
  %.38 = and i1 %.36, %.37
  br i1 %.38, label %L14, label %L15
L14:
  call void @__ritz_overflow_trap(ptr @.str.9, i64 42)
  unreachable
L15:
  %.39 = srem i64 %.33, %.34
  %.40 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.31, i64 %.39)
  %.41 = extractvalue { i64, i1 } %.40, 0
  %.42 = extractvalue { i64, i1 } %.40, 1
  br i1 %.42, label %L16, label %L17
L16:
  call void @__ritz_overflow_trap(ptr @.str.10, i64 42)
  unreachable
L17:
  %.43 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.17, i64 %.41)
  %.44 = extractvalue { i64, i1 } %.43, 0
  %.45 = extractvalue { i64, i1 } %.43, 1
  br i1 %.45, label %L18, label %L19
L18:
  call void @__ritz_overflow_trap(ptr @.str.11, i64 41)
  unreachable
L19:
  store i64 %.44, ptr %.10
  br label %L2
L2:
  %.46 = load i64, ptr %.12
  %.47 = add i64 %.46, 1
  store i64 %.47, ptr %.12
  br label %L0
L3:
  %.48 = load i64, ptr %.10
  call void @rt_hex(i64 %.48)
  %.50 = add i64 0, 1
  store i64 %.50, ptr %.49
  %.52 = add i64 0, 0
  store i64 %.52, ptr %.51
  br label %L20
L20:
  %.53 = load i64, ptr %.51
  %.54 = add i64 0, 64
  %.55 = icmp slt i64 %.53, %.54
  br i1 %.55, label %L21, label %L23
L21:
  %.56 = load i64, ptr %.49
  %.57 = load i64, ptr %.51
  %.58 = call i64 @mix__ff9282ec(i64 %.56, i64 %.57)
  store i64 %.58, ptr %.49
  br label %L22
L22:
  %.59 = load i64, ptr %.51
  %.60 = add i64 %.59, 1
  store i64 %.60, ptr %.51
  br label %L20
L23:
  %.61 = load i64, ptr %.49
  call void @rt_hex(i64 %.61)
  %.62 = load i64, ptr %.10
  %.63 = add i64 0, 100
  %.64 = icmp eq i64 %.63, 0
  br i1 %.64, label %L24, label %L25
L24:
  call void @__ritz_overflow_trap(ptr @.str.12, i64 41)
  unreachable
L25:
  %.65 = icmp eq i64 %.62, -9223372036854775808
  %.66 = icmp eq i64 %.63, -1
  %.67 = and i1 %.65, %.66
  br i1 %.67, label %L26, label %L27
L26:
  call void @__ritz_overflow_trap(ptr @.str.13, i64 41)
  unreachable
L27:
  %.68 = srem i64 %.62, %.63
  %.69 = trunc i64 %.68 to i32
  %.70 = sext i32 %.69 to i64
  %.71 = trunc i64 %.70 to i32
  ret i32 %.71
}


@.str.0 = private constant [43 x i8] c"hello.ritz:12:22: integer overflow in `+`\0A\00"
@.str.1 = private constant [52 x i8] c"hello.ritz:18:12: shift count out of range in `<<`\0A\00"
@.str.2 = private constant [52 x i8] c"hello.ritz:18:25: shift count out of range in `>>`\0A\00"
@.str.3 = private constant [29 x i8] c"hello from the rllvm corpus\0A\00"
@.str.4 = private constant [43 x i8] c"hello.ritz:25:16: integer overflow in `*`\0A\00"
@.str.5 = private constant [43 x i8] c"hello.ritz:25:25: division by zero in `/`\0A\00"
@.str.6 = private constant [43 x i8] c"hello.ritz:25:25: integer overflow in `/`\0A\00"
@.str.7 = private constant [43 x i8] c"hello.ritz:25:16: integer overflow in `-`\0A\00"
@.str.8 = private constant [43 x i8] c"hello.ritz:25:35: division by zero in `%`\0A\00"
@.str.9 = private constant [43 x i8] c"hello.ritz:25:35: integer overflow in `%`\0A\00"
@.str.10 = private constant [43 x i8] c"hello.ritz:25:16: integer overflow in `+`\0A\00"
@.str.11 = private constant [42 x i8] c"hello.ritz:25:9: integer overflow in `+`\0A\00"
@.str.12 = private constant [42 x i8] c"hello.ritz:31:6: division by zero in `%`\0A\00"
@.str.13 = private constant [42 x i8] c"hello.ritz:31:6: integer overflow in `%`\0A\00"
declare i64 @rt_write(...) "no-builtins"
declare void @rt_hex(...) "no-builtins"

declare { i64, i1 } @llvm.sadd.with.overflow.i64(i64, i64)
declare { i64, i1 } @llvm.ssub.with.overflow.i64(i64, i64)
declare { i64, i1 } @llvm.smul.with.overflow.i64(i64, i64)
define internal void @__ritz_overflow_trap(ptr %msg, i64 %len) cold noinline noreturn nounwind {
entry:
  %w = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 1, i64 2, ptr %msg, i64 %len)
  %x = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1)
  unreachable
}
