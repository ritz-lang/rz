; ModuleID = 'ritz1_output'
target triple = "x86_64-unknown-linux-gnu"

%Span$u8 = type {ptr, i64}
%StrView = type {ptr, i64}



@rt_ticks = external global i64
@g_value = weak_odr global i64 41
@g_table = weak_odr global [4 x i64] [i64 10, i64 20, i64 30, i64 40]
@g_names = weak_odr global [2 x %StrView] [%StrView { ptr @.str.0, i64 5 }, %StrView { ptr @.str.1, i64 4 }]


define i64 @sum_table__d8cb3b5b() alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.3 = alloca i64
  %.2 = add i64 0, 0
  store i64 %.2, ptr %.1
  %.4 = add i64 0, 0
  store i64 %.4, ptr %.3
  br label %L0
L0:
  %.5 = load i64, ptr %.3
  %.6 = add i64 0, 4
  %.7 = icmp slt i64 %.5, %.6
  br i1 %.7, label %L1, label %L3
L1:
  %.8 = load i64, ptr %.1
  %.9 = load i64, ptr %.3
  %.10 = getelementptr [4 x i64], ptr @g_table, i64 0, i64 %.9
  %.11 = load i64, ptr %.10
  %.12 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.8, i64 %.11)
  %.13 = extractvalue { i64, i1 } %.12, 0
  %.14 = extractvalue { i64, i1 } %.12, 1
  br i1 %.14, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.2, i64 39)
  unreachable
L5:
  store i64 %.13, ptr %.1
  br label %L2
L2:
  %.15 = load i64, ptr %.3
  %.16 = add i64 %.15, 1
  store i64 %.16, ptr %.3
  br label %L0
L3:
  %.17 = load i64, ptr %.1
  ret i64 %.17
}

define i32 @main() alignstack(16) "no-builtins" {
entry:
  %.1 = load i64, ptr @g_value
  %.2 = add i64 0, 1
  %.3 = getelementptr [2 x %StrView], ptr @g_names, i64 0, i64 %.2
  %.4 = getelementptr %StrView, ptr %.3, i32 0, i32 1
  %.5 = load i64, ptr %.4
  %.6 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.1, i64 %.5)
  %.7 = extractvalue { i64, i1 } %.6, 0
  %.8 = extractvalue { i64, i1 } %.6, 1
  br i1 %.8, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.3, i64 40)
  unreachable
L1:
  store i64 %.7, ptr @g_value
  %.9 = load i64, ptr @rt_ticks
  %.10 = call i64 @sum_table__d8cb3b5b()
  %.11 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.9, i64 %.10)
  %.12 = extractvalue { i64, i1 } %.11, 0
  %.13 = extractvalue { i64, i1 } %.11, 1
  br i1 %.13, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.4, i64 40)
  unreachable
L3:
  store i64 %.12, ptr @rt_ticks
  %.14 = load i64, ptr @g_value
  %.15 = call i64 @rt_tick(i64 %.14)
  %.16 = trunc i64 %.15 to i32
  %.17 = sext i32 %.16 to i64
  %.18 = trunc i64 %.17 to i32
  ret i32 %.18
}


@.str.0 = private constant [6 x i8] c"alpha\00"
@.str.1 = private constant [5 x i8] c"beta\00"
@.str.2 = private constant [40 x i8] c"pic.ritz:14:9: integer overflow in `+`\0A\00"
@.str.3 = private constant [41 x i8] c"pic.ritz:18:15: integer overflow in `+`\0A\00"
@.str.4 = private constant [41 x i8] c"pic.ritz:19:16: integer overflow in `+`\0A\00"
declare i64 @rt_tick(...) "no-builtins"

declare { i64, i1 } @llvm.sadd.with.overflow.i64(i64, i64)
define internal void @__ritz_overflow_trap(ptr %msg, i64 %len) cold noinline noreturn nounwind {
entry:
  %w = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 1, i64 2, ptr %msg, i64 %len)
  %x = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1)
  unreachable
}
