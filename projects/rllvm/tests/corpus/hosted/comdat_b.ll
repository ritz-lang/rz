; ModuleID = 'ritz1_output'
target triple = "x86_64-unknown-linux-gnu"

%Future = type {ptr}
%shared_a$Future = type {ptr, i32, i32, i32}
%shared_b$Future = type {ptr, i32, i32, i32}
%Span$u8 = type {ptr, i64}
%StrView = type {ptr, i64}





define %shared_b$Future @shared_b(i32 %n.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca %shared_b$Future
  store i32 %n.arg, ptr %.1
  %.3 = ptrtoint ptr @shared_b$poll to i64
  %.4 = getelementptr %shared_b$Future, ptr %.2, i32 0, i32 0
  %.5 = inttoptr i64 %.3 to ptr  ; #1754 *T->@&T
  store ptr %.5, ptr %.4
  %.6 = add i64 0, 0
  %.7 = getelementptr %shared_b$Future, ptr %.2, i32 0, i32 1
  %.8 = trunc i64 %.6 to i32
  store i32 %.8, ptr %.7
  %.9 = load i32, ptr %.1
  %.10 = sext i32 %.9 to i64
  %.11 = getelementptr %shared_b$Future, ptr %.2, i32 0, i32 3
  %.12 = trunc i64 %.10 to i32
  store i32 %.12, ptr %.11
  %.13 = getelementptr %shared_b$Future, ptr %.2, i32 0, i32 2  ; omitted field: zero
  store i32 zeroinitializer, ptr %.13
  %.14 = load %shared_b$Future, ptr %.2
  ret %shared_b$Future %.14
}

$shared_b$poll = comdat any
define linkonce_odr i1 @shared_b$poll(i64 %self.arg) alignstack(16) "no-builtins" comdat {
entry:
  %.1 = alloca i64
  store i64 %self.arg, ptr %.1
  %.2 = load ptr, ptr %.1
  %.3 = getelementptr %shared_b$Future, ptr %.2, i32 0, i32 1
  %.4 = load i32, ptr %.3
  %.5 = sext i32 %.4 to i64
  %.6 = add i64 0, 0
  %.7 = add i64 0, 1
  %.8 = call { i64, i1 } @llvm.ssub.with.overflow.i64(i64 %.6, i64 %.7)
  %.9 = extractvalue { i64, i1 } %.8, 0
  %.10 = extractvalue { i64, i1 } %.8, 1
  br i1 %.10, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.0, i64 43)
  unreachable
L1:
  %.11 = icmp eq i64 %.5, %.9
  %.12 = zext i1 %.11 to i64
  %.13 = icmp ne i64 %.12, 0
  br i1 %.13, label %L2, label %L4
L2:
  %.14 = add i64 0, 1
  %.15 = trunc i64 %.14 to i1
  ret i1 %.15
L5:
  br label %L4
L4:
  %.16 = load ptr, ptr %.1
  %.17 = getelementptr %shared_b$Future, ptr %.16, i32 0, i32 1
  %.18 = add i64 0, 0
  %.19 = add i64 0, 1
  %.20 = call { i64, i1 } @llvm.ssub.with.overflow.i64(i64 %.18, i64 %.19)
  %.21 = extractvalue { i64, i1 } %.20, 0
  %.22 = extractvalue { i64, i1 } %.20, 1
  br i1 %.22, label %L6, label %L7
L6:
  call void @__ritz_overflow_trap(ptr @.str.1, i64 43)
  unreachable
L7:
  %.23 = trunc i64 %.21 to i32
  store i32 %.23, ptr %.17
  %.24 = load ptr, ptr %.1
  %.25 = getelementptr %shared_b$Future, ptr %.24, i32 0, i32 2
  %.26 = load ptr, ptr %.1
  %.27 = getelementptr %shared_b$Future, ptr %.26, i32 0, i32 3
  %.28 = load i32, ptr %.27
  %.29 = sext i32 %.28 to i64
  %.30 = add i64 0, 3
  %.31 = trunc i64 %.29 to i32
  %.32 = trunc i64 %.30 to i32
  %.33 = call { i32, i1 } @llvm.smul.with.overflow.i32(i32 %.31, i32 %.32)
  %.34 = extractvalue { i32, i1 } %.33, 0
  %.35 = extractvalue { i32, i1 } %.33, 1
  br i1 %.35, label %L8, label %L9
L8:
  call void @__ritz_overflow_trap(ptr @.str.2, i64 44)
  unreachable
L9:
  %.36 = sext i32 %.34 to i64
  %.37 = trunc i64 %.36 to i32
  store i32 %.37, ptr %.25
  %.38 = load ptr, ptr %.1
  %.39 = getelementptr %shared_b$Future, ptr %.38, i32 0, i32 1
  %.40 = add i64 0, 0
  %.41 = add i64 0, 1
  %.42 = call { i64, i1 } @llvm.ssub.with.overflow.i64(i64 %.40, i64 %.41)
  %.43 = extractvalue { i64, i1 } %.42, 0
  %.44 = extractvalue { i64, i1 } %.42, 1
  br i1 %.44, label %L10, label %L11
L10:
  call void @__ritz_overflow_trap(ptr @.str.3, i64 43)
  unreachable
L11:
  %.45 = trunc i64 %.43 to i32
  store i32 %.45, ptr %.39
  %.46 = add i64 0, 1
  %.47 = trunc i64 %.46 to i1
  ret i1 %.47
}

define i1 @poll_it__d1674f73(ptr %f.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca ptr
  store ptr %f.arg, ptr %.1
  %.2 = load ptr, ptr %.1
  %.3 = ptrtoint ptr %.2 to i64  ; #1644 @&T->*T
  %.4 = call i1 @future_poll(i64 %.3)
  %.5 = zext i1 %.4 to i64
  %.6 = trunc i64 %.5 to i1
  ret i1 %.6
}

define i64 @drive_b(i32 %n.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca %shared_b$Future
  %.7 = alloca i64
  store i32 %n.arg, ptr %.1
  %.3 = load i32, ptr %.1
  %.4 = sext i32 %.3 to i64
  %.5 = trunc i64 %.4 to i32
  %.6 = call %shared_b$Future @shared_b(i32 %.5)
  store %shared_b$Future %.6, ptr %.2
  %.8 = add i64 0, 0
  store i64 %.8, ptr %.7
  br label %L0
L0:
  %.9 = call i1 @poll_it__d1674f73(ptr %.2)
  %.10 = zext i1 %.9 to i64
  %.11 = icmp eq i64 %.10, 0
  %.12 = zext i1 %.11 to i64
  %.13 = icmp ne i64 %.12, 0
  br i1 %.13, label %L1, label %L2
L1:
  %.14 = load i64, ptr %.7
  %.15 = add i64 0, 1
  %.16 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.14, i64 %.15)
  %.17 = extractvalue { i64, i1 } %.16, 0
  %.18 = extractvalue { i64, i1 } %.16, 1
  br i1 %.18, label %L3, label %L4
L3:
  call void @__ritz_overflow_trap(ptr @.str.4, i64 44)
  unreachable
L4:
  store i64 %.17, ptr %.7
  br label %L0
L2:
  %.19 = load i64, ptr %.7
  call void @rt_hex(i64 %.19)
  %.20 = load i64, ptr %.7
  %.21 = load i32, ptr %.1
  %.22 = sext i32 %.21 to i64
  %.23 = trunc i64 %.22 to i32
  %.24 = sext i32 %.23 to i64
  %.25 = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %.20, i64 %.24)
  %.26 = extractvalue { i64, i1 } %.25, 0
  %.27 = extractvalue { i64, i1 } %.25, 1
  br i1 %.27, label %L5, label %L6
L5:
  call void @__ritz_overflow_trap(ptr @.str.5, i64 44)
  unreachable
L6:
  ret i64 %.26
}

$future_poll = comdat any
define weak_odr i1 @future_poll(i64 %f.arg) alignstack(16) "no-builtins" comdat {
entry:
  %.1 = alloca i64
  store i64 %f.arg, ptr %.1
  %.2 = load ptr, ptr %.1
  %.3 = getelementptr %Future, ptr %.2, i32 0, i32 0
  %.4 = load ptr, ptr %.3
  %.5 = ptrtoint ptr %.4 to i64
  %.6 = load i64, ptr %.1
  %.7 = inttoptr i64 %.5 to ptr
  %.8 = call i1 %.7(i64 %.6)
  %.9 = zext i1 %.8 to i64
  %.10 = trunc i64 %.9 to i1
  ret i1 %.10
}


@.str.0 = private constant [44 x i8] c"comdat_b.ritz:8:1: integer overflow in `-`\0A\00"
@.str.1 = private constant [44 x i8] c"comdat_b.ritz:8:1: integer overflow in `-`\0A\00"
@.str.2 = private constant [45 x i8] c"comdat_b.ritz:9:12: integer overflow in `*`\0A\00"
@.str.3 = private constant [44 x i8] c"comdat_b.ritz:9:5: integer overflow in `-`\0A\00"
@.str.4 = private constant [45 x i8] c"comdat_b.ritz:19:9: integer overflow in `+`\0A\00"
@.str.5 = private constant [45 x i8] c"comdat_b.ritz:21:5: integer overflow in `+`\0A\00"
declare void @rt_hex(...) "no-builtins"

declare { i64, i1 } @llvm.sadd.with.overflow.i64(i64, i64)
declare { i64, i1 } @llvm.ssub.with.overflow.i64(i64, i64)
declare { i32, i1 } @llvm.smul.with.overflow.i32(i32, i32)
define internal void @__ritz_overflow_trap(ptr %msg, i64 %len) cold noinline noreturn nounwind {
entry:
  %w = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 1, i64 2, ptr %msg, i64 %len)
  %x = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1)
  unreachable
}
