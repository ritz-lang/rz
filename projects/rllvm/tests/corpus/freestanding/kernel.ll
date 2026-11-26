; ModuleID = 'ritz1_output'
target triple = "x86_64-unknown-linux-gnu"

%Span$u8 = type {ptr, i64}
%StrView = type {ptr, i64}



@rt_ticks = external global i64
@g_value = weak_odr global i64 41
@g_table = weak_odr global [4 x i64] [i64 10, i64 20, i64 30, i64 40]
@g_names = weak_odr global [2 x %StrView] [%StrView { ptr @.str.0, i64 5 }, %StrView { ptr @.str.1, i64 4 }]


define i64 @checksum__4afb816e(i64 %n.arg) alignstack(16) "no-builtins" sspstrong noredzone {
entry:
  %.1 = alloca i64
  %.2 = alloca [32 x i8]
  %.3 = alloca i64
  %.22 = alloca i64
  %.24 = alloca i64
  store i64 %n.arg, ptr %.1
  call void @__ritz_sret_zero(ptr %.2, i64 32)
  %.4 = add i64 0, 0
  store i64 %.4, ptr %.3
  br label %L0
L0:
  %.5 = load i64, ptr %.3
  %.6 = add i64 0, 32
  %.7 = icmp slt i64 %.5, %.6
  br i1 %.7, label %L1, label %L3
L1:
  %.8 = load i64, ptr %.3
  %.9 = load i64, ptr %.1
  %.10 = load i64, ptr %.3
  %.11 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.9, i64 %.10)
  %.12 = extractvalue { i64, i1 } %.11, 0
  %.13 = extractvalue { i64, i1 } %.11, 1
  br i1 %.13, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.2, i64 42)
  unreachable
L5:
  %.14 = add i64 0, 255
  %.15 = and i64 %.12, %.14
  %.16 = trunc i64 %.15 to i8
  %.17 = zext i8 %.16 to i64
  %.18 = getelementptr [32 x i8], ptr %.2, i64 0, i64 %.8
  %.19 = trunc i64 %.17 to i8
  store i8 %.19, ptr %.18
  br label %L2
L2:
  %.20 = load i64, ptr %.3
  %.21 = add i64 %.20, 1
  store i64 %.21, ptr %.3
  br label %L0
L3:
  %.23 = add i64 0, 0
  store i64 %.23, ptr %.22
  %.25 = add i64 0, 0
  store i64 %.25, ptr %.24
  br label %L6
L6:
  %.26 = load i64, ptr %.24
  %.27 = add i64 0, 32
  %.28 = icmp slt i64 %.26, %.27
  br i1 %.28, label %L7, label %L9
L7:
  %.29 = load i64, ptr %.22
  %.30 = load i64, ptr %.24
  %.31 = getelementptr [32 x i8], ptr %.2, i64 0, i64 %.30
  %.32 = load i8, ptr %.31
  %.33 = zext i8 %.32 to i64
  %.34 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.29, i64 %.33)
  %.35 = extractvalue { i64, i1 } %.34, 0
  %.36 = extractvalue { i64, i1 } %.34, 1
  br i1 %.36, label %L10, label %L11
L10:
  call void @__ritz_overflow_trap(ptr @.str.3, i64 41)
  unreachable
L11:
  store i64 %.35, ptr %.22
  br label %L8
L8:
  %.37 = load i64, ptr %.24
  %.38 = add i64 %.37, 1
  store i64 %.38, ptr %.24
  br label %L6
L9:
  %.39 = load i64, ptr %.22
  ret i64 %.39
}

define i64 @sum_table__4afb816e() alignstack(16) "no-builtins" sspstrong noredzone {
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
  call void @__ritz_overflow_trap(ptr @.str.4, i64 41)
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

define i64 @kmain(i64 %x.arg) alignstack(16) "no-builtins" sspstrong noredzone {
entry:
  %.1 = alloca i64
  store i64 %x.arg, ptr %.1
  %.2 = load i64, ptr @g_value
  %.3 = add i64 0, 1
  %.4 = getelementptr [2 x %StrView], ptr @g_names, i64 0, i64 %.3
  %.5 = getelementptr %StrView, ptr %.4, i32 0, i32 1
  %.6 = load i64, ptr %.5
  %.7 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.2, i64 %.6)
  %.8 = extractvalue { i64, i1 } %.7, 0
  %.9 = extractvalue { i64, i1 } %.7, 1
  br i1 %.9, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.5, i64 42)
  unreachable
L1:
  store i64 %.8, ptr @g_value
  %.10 = load i64, ptr @rt_ticks
  %.11 = call i64 @sum_table__4afb816e()
  %.12 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.10, i64 %.11)
  %.13 = extractvalue { i64, i1 } %.12, 0
  %.14 = extractvalue { i64, i1 } %.12, 1
  br i1 %.14, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.6, i64 42)
  unreachable
L3:
  store i64 %.13, ptr @rt_ticks
  %.15 = load i64, ptr %.1
  %.16 = call i64 @checksum__4afb816e(i64 %.15)
  %.17 = load i64, ptr @g_value
  %.18 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.16, i64 %.17)
  %.19 = extractvalue { i64, i1 } %.18, 0
  %.20 = extractvalue { i64, i1 } %.18, 1
  br i1 %.20, label %L4, label %L5
L4:
  call void @__ritz_overflow_trap(ptr @.str.7, i64 42)
  unreachable
L5:
  %.21 = call i64 @rt_tick(i64 %.19)
  ret i64 %.21
}


@.str.0 = private constant [6 x i8] c"alpha\00"
@.str.1 = private constant [5 x i8] c"beta\00"
@.str.2 = private constant [43 x i8] c"kernel.ritz:15:20: integer overflow in `+`\00"
@.str.3 = private constant [42 x i8] c"kernel.ritz:18:9: integer overflow in `+`\00"
@.str.4 = private constant [42 x i8] c"kernel.ritz:24:9: integer overflow in `+`\00"
@.str.5 = private constant [43 x i8] c"kernel.ritz:28:15: integer overflow in `+`\00"
@.str.6 = private constant [43 x i8] c"kernel.ritz:29:16: integer overflow in `+`\00"
@.str.7 = private constant [43 x i8] c"kernel.ritz:30:13: integer overflow in `+`\00"
declare i64 @rt_tick(...) "no-builtins"

define internal void @__ritz_sret_copy(ptr %d, ptr %s, i64 %n) "no-builtins" noredzone {
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

define internal void @__ritz_sret_zero(ptr %d, i64 %n) "no-builtins" noredzone {
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

declare { i64, i1 } @llvm.sadd.with.overflow.i64(i64, i64)
define internal void @__ritz_overflow_trap(ptr %msg, i64 %len) cold noinline noreturn nounwind noredzone {
entry:
  call void @ritz_platform_fatal(ptr %msg, i64 %len, i32 1)
  unreachable
}
declare void @ritz_platform_fatal(ptr, i64, i32) "no-builtins"
