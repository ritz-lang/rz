; ModuleID = 'ritz1_output'
target triple = "x86_64-unknown-linux-gnu"

%Span$u8 = type {ptr, i64}
%StrView = type {ptr, i64}





define void @say__6ec1d7d4(%StrView %s.arg) alignstack(16) "no-builtins" {
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

define i64 @add_tied__6ec1d7d4(i64 %x.arg, i64 %y.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.3 = alloca i64
  store i64 %x.arg, ptr %.1
  store i64 %y.arg, ptr %.2
  %.4 = load i64, ptr %.1
  store i64 %.4, ptr %.3
  %.5 = load i64, ptr %.3
  %.6 = load i64, ptr %.2
  %.7 = call i64 asm sideeffect "addq $2, $0", "=&r,0,r,~{memory},~{dirflag},~{fpsr},~{flags}"(i64 %.5, i64 %.6)
  store i64 %.7, ptr %.3
  %.8 = load i64, ptr %.3
  ret i64 %.8
}

define i64 @early__6ec1d7d4(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.3 = alloca i64
  store i64 %a.arg, ptr %.1
  store i64 %b.arg, ptr %.2
  %.4 = add i64 0, 0
  store i64 %.4, ptr %.3
  %.5 = load i64, ptr %.1
  %.6 = load i64, ptr %.2
  %.7 = call i64 asm sideeffect "movq $1, $0\0Ashlq $$3, $0\0Aaddq $2, $0\0Axorq $1, $0", "=&r,r,r,~{memory},~{dirflag},~{fpsr},~{flags}"(i64 %.5, i64 %.6)
  store i64 %.7, ptr %.3
  %.8 = load i64, ptr %.3
  ret i64 %.8
}

define i64 @pinned__6ec1d7d4(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.3 = alloca i64
  store i64 %a.arg, ptr %.1
  store i64 %b.arg, ptr %.2
  %.4 = add i64 0, 0
  store i64 %.4, ptr %.3
  %.5 = load i64, ptr %.1
  %.6 = load i64, ptr %.2
  %.7 = call i64 asm sideeffect "leaq (%rdi,%rsi,4), %rax", "={rax},{rdi},{rsi},~{rsi},~{rdi},~{memory},~{dirflag},~{fpsr},~{flags}"(i64 %.5, i64 %.6)
  store i64 %.7, ptr %.3
  %.8 = load i64, ptr %.3
  ret i64 %.8
}

define i64 @swap_pair__6ec1d7d4(i64 %a.arg, i64 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.3 = alloca i64
  %.5 = alloca i64
  store i64 %a.arg, ptr %.1
  store i64 %b.arg, ptr %.2
  %.4 = load i64, ptr %.1
  store i64 %.4, ptr %.3
  %.6 = load i64, ptr %.2
  store i64 %.6, ptr %.5
  %.7 = load i64, ptr %.3
  %.8 = load i64, ptr %.5
  %.9 = call { i64, i64 } asm sideeffect "xchgq $0, $1", "=&r,=&r,0,1,~{memory},~{dirflag},~{fpsr},~{flags}"(i64 %.7, i64 %.8)
  %.10 = extractvalue { i64, i64 } %.9, 0
  store i64 %.10, ptr %.3
  %.11 = extractvalue { i64, i64 } %.9, 1
  store i64 %.11, ptr %.5
  %.12 = load i64, ptr %.3
  %.13 = add i64 0, 8
  %.14 = icmp uge i64 %.13, 64
  br i1 %.14, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.0, i64 52)
  unreachable
L1:
  %.15 = shl i64 %.12, %.13
  %.16 = load i64, ptr %.5
  %.17 = or i64 %.15, %.16
  ret i64 %.17
}

define i64 @swapped__6ec1d7d4(i64 %v.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %v.arg, ptr %.1
  %.3 = load i64, ptr %.1
  store i64 %.3, ptr %.2
  %.4 = load i64, ptr %.2
  %.5 = call i64 asm sideeffect "bswap $0", "=&r,0,~{memory},~{dirflag},~{fpsr},~{flags}"(i64 %.4)
  store i64 %.5, ptr %.2
  %.6 = load i64, ptr %.2
  ret i64 %.6
}

define i64 @plus_forty_two__6ec1d7d4(i64 %v.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %v.arg, ptr %.1
  %.3 = load i64, ptr %.1
  store i64 %.3, ptr %.2
  %.4 = load i64, ptr %.2
  %.5 = call i64 asm sideeffect "addq $$42, %rcx", "={rcx},0,~{memory},~{dirflag},~{fpsr},~{flags}"(i64 %.4)
  store i64 %.5, ptr %.2
  %.6 = load i64, ptr %.2
  ret i64 %.6
}

define i64 @tsc_ok__6ec1d7d4() alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.4 = alloca i32
  %.10 = alloca i64
  %.2 = add i64 0, 0
  %.3 = trunc i64 %.2 to i32
  store i32 %.3, ptr %.1
  %.5 = add i64 0, 0
  %.6 = trunc i64 %.5 to i32
  store i32 %.6, ptr %.4
  %.7 = call { i32, i32 } asm sideeffect "rdtsc", "={rax},={rdx},~{memory},~{dirflag},~{fpsr},~{flags}"()
  %.8 = extractvalue { i32, i32 } %.7, 0
  store i32 %.8, ptr %.1
  %.9 = extractvalue { i32, i32 } %.7, 1
  store i32 %.9, ptr %.4
  %.11 = load i32, ptr %.4
  %.12 = zext i32 %.11 to i64
  %.13 = trunc i64 %.12 to i32
  %.14 = zext i32 %.13 to i64
  %.15 = add i64 0, 32
  %.16 = icmp uge i64 %.15, 64
  br i1 %.16, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.1, i64 53)
  unreachable
L1:
  %.17 = shl i64 %.14, %.15
  %.18 = load i32, ptr %.1
  %.19 = zext i32 %.18 to i64
  %.20 = trunc i64 %.19 to i32
  %.21 = zext i32 %.20 to i64
  %.22 = or i64 %.17, %.21
  store i64 %.22, ptr %.10
  %.23 = load i64, ptr %.10
  %.24 = add i64 0, 0
  %.25 = icmp ne i64 %.23, %.24
  %.26 = zext i1 %.25 to i64
  %.27 = icmp ne i64 %.26, 0
  br i1 %.27, label %L2, label %L3
L2:
  %.28 = add i64 0, 1
  br label %L4
L3:
  %.29 = add i64 0, 0
  br label %L4
L4:
  %.30 = phi i64 [ %.28, %L2 ], [ %.29, %L3 ]
  ret i64 %.30
}

define i32 @main() alignstack(16) "no-builtins" {
entry:
  %.1 = getelementptr [5 x i8], ptr @.str.2, i64 0, i64 0
  %.2 = insertvalue %Span$u8 undef, ptr %.1, 0
  %.3 = insertvalue %Span$u8 %.2, i64 4, 1
  %.4 = extractvalue %Span$u8 %.3, 0
  %.5 = extractvalue %Span$u8 %.3, 1
  %.6 = insertvalue %StrView undef, ptr %.4, 0
  %.7 = insertvalue %StrView %.6, i64 %.5, 1
  call void @say__6ec1d7d4(%StrView %.7)
  %.8 = add i64 0, 40
  %.9 = add i64 0, 2
  %.10 = call i64 @add_tied__6ec1d7d4(i64 %.8, i64 %.9)
  call void @rt_hex(i64 %.10)
  %.11 = add i64 0, 5
  %.12 = add i64 0, 7
  %.13 = call i64 @early__6ec1d7d4(i64 %.11, i64 %.12)
  call void @rt_hex(i64 %.13)
  %.14 = add i64 0, 100
  %.15 = add i64 0, 3
  %.16 = call i64 @pinned__6ec1d7d4(i64 %.14, i64 %.15)
  call void @rt_hex(i64 %.16)
  %.17 = add i64 0, 1
  %.18 = add i64 0, 2
  %.19 = call i64 @swap_pair__6ec1d7d4(i64 %.17, i64 %.18)
  call void @rt_hex(i64 %.19)
  %.20 = add i64 0, 72623859790382856
  %.21 = call i64 @swapped__6ec1d7d4(i64 %.20)
  call void @rt_hex(i64 %.21)
  %.22 = add i64 0, 8
  %.23 = call i64 @plus_forty_two__6ec1d7d4(i64 %.22)
  call void @rt_hex(i64 %.23)
  %.24 = call i64 @tsc_ok__6ec1d7d4()
  call void @rt_hex(i64 %.24)
  %.25 = add i64 0, 0
  %.26 = trunc i64 %.25 to i32
  ret i32 %.26
}


@.str.0 = private constant [53 x i8] c"asm_run.ritz:40:6: shift count out of range in `<<`\0A\00"
@.str.1 = private constant [54 x i8] c"asm_run.ritz:62:20: shift count out of range in `<<`\0A\00"
@.str.2 = private constant [5 x i8] c"asm\0A\00"
declare i64 @rt_write(...) "no-builtins"
declare void @rt_hex(...) "no-builtins"

define internal void @__ritz_overflow_trap(ptr %msg, i64 %len) cold noinline noreturn nounwind {
entry:
  %w = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 1, i64 2, ptr %msg, i64 %len)
  %x = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1)
  unreachable
}
