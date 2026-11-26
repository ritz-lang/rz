; ModuleID = 'ritz1_output'
target triple = "x86_64-unknown-linux-gnu"

%Span$u8 = type {ptr, i64}
%StrView = type {ptr, i64}





define void @ritz_platform_fatal(i64 %msg.arg, i64 %len.arg, i32 %status.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.3 = alloca i32
  %.7 = alloca i64
  %.9 = alloca i64
  store i64 %msg.arg, ptr %.1
  store i64 %len.arg, ptr %.2
  store i32 %status.arg, ptr %.3
  %.4 = load i64, ptr %.1
  %.5 = load i64, ptr %.2
  %.6 = call i64 @rt_write(i64 %.4, i64 %.5)
  %.8 = add i64 0, 60
  store i64 %.8, ptr %.7
  %.10 = add i64 0, 7
  store i64 %.10, ptr %.9
  %.11 = load i64, ptr %.7
  %.12 = load i64, ptr %.9
  %.13 = call i64 asm sideeffect "syscall", "={rax},0,{rdi},~{rcx},~{r11},~{memory},~{dirflag},~{fpsr},~{flags}"(i64 %.11, i64 %.12)
  store i64 %.13, ptr %.7
  ret void
}

define i32 @main() alignstack(16) "no-builtins" {
entry:
  %.1 = alloca %StrView
  %.2 = getelementptr [28 x i8], ptr @.str.0, i64 0, i64 0
  %.3 = insertvalue %Span$u8 undef, ptr %.2, 0
  %.4 = insertvalue %Span$u8 %.3, i64 27, 1
  %.5 = extractvalue %Span$u8 %.4, 0
  %.6 = extractvalue %Span$u8 %.4, 1
  %.7 = insertvalue %StrView undef, ptr %.5, 0
  %.8 = insertvalue %StrView %.7, i64 %.6, 1
  store %StrView %.8, ptr %.1
  %.9 = getelementptr %StrView, ptr %.1, i32 0, i32 0
  %.10 = load ptr, ptr %.9
  %.11 = ptrtoint ptr %.10 to i64
  %.12 = getelementptr %StrView, ptr %.1, i32 0, i32 1
  %.13 = load i64, ptr %.12
  %.14 = add i64 0, 1
  %.15 = trunc i64 %.14 to i32
  call void @ritz_platform_fatal(i64 %.11, i64 %.13, i32 %.15)
  %.16 = add i64 0, 0
  %.17 = trunc i64 %.16 to i32
  ret i32 %.17
}


@.str.0 = private constant [28 x i8] c"strong ritz_platform_fatal\0A\00"
declare i64 @rt_write(...) "no-builtins"

