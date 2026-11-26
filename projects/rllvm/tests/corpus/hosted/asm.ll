; ModuleID = 'ritz1_output'
target triple = "x86_64-unknown-linux-gnu"

%Span$u8 = type {ptr, i64}
%StrView = type {ptr, i64}



@g_slot = weak_odr global i64 0


define i64 @alu__2fb86de4(i64 %a.arg, i32 %b.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i32
  %.3 = alloca i64
  %.5 = alloca i32
  store i64 %a.arg, ptr %.1
  store i32 %b.arg, ptr %.2
  %.4 = load i64, ptr %.1
  store i64 %.4, ptr %.3
  %.6 = load i32, ptr %.2
  %.7 = zext i32 %.6 to i64
  %.8 = trunc i64 %.7 to i32
  store i32 %.8, ptr %.5
  %.9 = load i64, ptr %.3
  %.10 = load i32, ptr %.5
  %.11 = call { i64, i32 } asm sideeffect "addq $$1, $0\0Aaddl $$2, $1\0Aandq $$-16, $0\0Adecq $0\0Ashlq $$3, $0\0Axorl $1, $1\0Axorq $$5, $0", "=&r,=&r,0,1,~{memory},~{dirflag},~{fpsr},~{flags}"(i64 %.9, i32 %.10)
  %.12 = extractvalue { i64, i32 } %.11, 0
  store i64 %.12, ptr %.3
  %.13 = extractvalue { i64, i32 } %.11, 1
  store i32 %.13, ptr %.5
  %.14 = load i64, ptr %.3
  %.15 = load i32, ptr %.5
  %.16 = zext i32 %.15 to i64
  %.17 = trunc i64 %.16 to i32
  %.18 = zext i32 %.17 to i64
  %.19 = call { i64, i1 } @llvm.uadd.with.overflow.i64(i64 %.14, i64 %.18)
  %.20 = extractvalue { i64, i1 } %.19, 0
  %.21 = extractvalue { i64, i1 } %.19, 1
  br i1 %.21, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.0, i64 39)
  unreachable
L1:
  ret i64 %.20
}

define i64 @moves__2fb86de4(i64 %p.arg, i64 %v.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.3 = alloca i64
  store i64 %p.arg, ptr %.1
  store i64 %v.arg, ptr %.2
  %.4 = add i64 0, 0
  store i64 %.4, ptr %.3
  %.5 = load ptr, ptr %.1
  %.6 = load i64, ptr %.2
  %.7 = call i64 asm sideeffect "movb $$1, ($1)\0Amovw $$2, 2($1)\0Amovl $$3, 4($1)\0Amovq $2, 8($1,$2)\0Amovq 8($1,$2,8), $0\0Aleaq 16($1), $0", "=&r,r,r,~{memory},~{dirflag},~{fpsr},~{flags}"(ptr %.5, i64 %.6)
  store i64 %.7, ptr %.3
  %.8 = load i64, ptr %.3
  ret i64 %.8
}

define i64 @flags__2fb86de4() alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = add i64 0, 0
  store i64 %.2, ptr %.1
  %.3 = call i64 asm sideeffect "pushfq\0Apopq $0", "=&r,~{memory},~{dirflag},~{fpsr},~{flags}"()
  store i64 %.3, ptr %.1
  %.4 = load i64, ptr %.1
  ret i64 %.4
}

define i64 @shim_sequence__2fb86de4(i64 %argc.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %argc.arg, ptr %.1
  %.3 = load i64, ptr %.1
  store i64 %.3, ptr %.2
  %.4 = load i64, ptr %.2
  %.5 = call i64 asm sideeffect "addq $$1, %rax\0Ashlq $$3, %rax\0Aleaq g_slot(%rip), %rdx\0Amovq %rax, g_slot(%rip)\0Amovq %rax, %rdi\0Acall rt_hex", "={rax},0,~{rcx},~{rdx},~{rsi},~{rdi},~{r8},~{r9},~{r10},~{r11},~{memory},~{dirflag},~{fpsr},~{flags}"(i64 %.4)
  store i64 %.5, ptr %.2
  %.6 = load i64, ptr %.2
  ret i64 %.6
}

define i32 @ports__2fb86de4(i16 %port.arg, i32 %v.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i16
  %.2 = alloca i32
  %.3 = alloca i8
  %.6 = alloca i16
  %.9 = alloca i32
  store i16 %port.arg, ptr %.1
  store i32 %v.arg, ptr %.2
  %.4 = add i64 0, 0
  %.5 = trunc i64 %.4 to i8
  store i8 %.5, ptr %.3
  %.7 = add i64 0, 0
  %.8 = trunc i64 %.7 to i16
  store i16 %.8, ptr %.6
  %.10 = load i32, ptr %.2
  %.11 = zext i32 %.10 to i64
  %.12 = trunc i64 %.11 to i32
  store i32 %.12, ptr %.9
  %.13 = load i16, ptr %.1
  %.14 = call i8 asm sideeffect "inb %dx, %al", "={rax},{rdx},~{rdx},~{memory},~{dirflag},~{fpsr},~{flags}"(i16 %.13)
  store i8 %.14, ptr %.3
  %.15 = load i16, ptr %.1
  %.16 = call i16 asm sideeffect "inw %dx, %ax", "={rax},{rdx},~{rdx},~{memory},~{dirflag},~{fpsr},~{flags}"(i16 %.15)
  store i16 %.16, ptr %.6
  %.17 = load i16, ptr %.1
  %.18 = load i32, ptr %.9
  %.19 = call i32 asm sideeffect "inl %dx, %eax\0Aoutb %al, %dx\0Aoutw %ax, %dx\0Aoutl %eax, %dx", "={rax},{rdx},0,~{rdx},~{memory},~{dirflag},~{fpsr},~{flags}"(i16 %.17, i32 %.18)
  store i32 %.19, ptr %.9
  %.20 = load i8, ptr %.3
  %.21 = zext i8 %.20 to i64
  %.22 = trunc i64 %.21 to i8
  %.23 = zext i8 %.22 to i64
  %.24 = load i16, ptr %.6
  %.25 = zext i16 %.24 to i64
  %.26 = trunc i64 %.25 to i16
  %.27 = zext i16 %.26 to i64
  %.28 = trunc i64 %.23 to i32
  %.29 = trunc i64 %.27 to i32
  %.30 = call { i32, i1 } @llvm.uadd.with.overflow.i32(i32 %.28, i32 %.29)
  %.31 = extractvalue { i32, i1 } %.30, 0
  %.32 = extractvalue { i32, i1 } %.30, 1
  br i1 %.32, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.1, i64 39)
  unreachable
L1:
  %.33 = zext i32 %.31 to i64
  %.34 = load i32, ptr %.9
  %.35 = zext i32 %.34 to i64
  %.36 = trunc i64 %.33 to i32
  %.37 = trunc i64 %.35 to i32
  %.38 = call { i32, i1 } @llvm.uadd.with.overflow.i32(i32 %.36, i32 %.37)
  %.39 = extractvalue { i32, i1 } %.38, 0
  %.40 = extractvalue { i32, i1 } %.38, 1
  br i1 %.40, label %L2, label %L3
L2:
  call void @__ritz_overflow_trap(ptr @.str.2, i64 39)
  unreachable
L3:
  %.41 = zext i32 %.39 to i64
  %.42 = trunc i64 %.41 to i32
  ret i32 %.42
}

define i32 @cpuid4__2fb86de4(i32 %leaf.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca i32
  %.6 = alloca i32
  %.9 = alloca i32
  %.12 = alloca i32
  store i32 %leaf.arg, ptr %.1
  %.3 = load i32, ptr %.1
  %.4 = zext i32 %.3 to i64
  %.5 = trunc i64 %.4 to i32
  store i32 %.5, ptr %.2
  %.7 = add i64 0, 0
  %.8 = trunc i64 %.7 to i32
  store i32 %.8, ptr %.6
  %.10 = add i64 0, 0
  %.11 = trunc i64 %.10 to i32
  store i32 %.11, ptr %.9
  %.13 = add i64 0, 0
  %.14 = trunc i64 %.13 to i32
  store i32 %.14, ptr %.12
  %.15 = load i32, ptr %.2
  %.16 = load i32, ptr %.9
  %.17 = call { i32, i32, i32, i32 } asm sideeffect "cpuid", "={rax},={rbx},={rcx},={rdx},0,2,~{memory},~{dirflag},~{fpsr},~{flags}"(i32 %.15, i32 %.16)
  %.18 = extractvalue { i32, i32, i32, i32 } %.17, 0
  store i32 %.18, ptr %.2
  %.19 = extractvalue { i32, i32, i32, i32 } %.17, 1
  store i32 %.19, ptr %.6
  %.20 = extractvalue { i32, i32, i32, i32 } %.17, 2
  store i32 %.20, ptr %.9
  %.21 = extractvalue { i32, i32, i32, i32 } %.17, 3
  store i32 %.21, ptr %.12
  %.22 = load i32, ptr %.2
  %.23 = zext i32 %.22 to i64
  %.24 = load i32, ptr %.6
  %.25 = zext i32 %.24 to i64
  %.26 = xor i64 %.23, %.25
  %.27 = load i32, ptr %.9
  %.28 = zext i32 %.27 to i64
  %.29 = xor i64 %.26, %.28
  %.30 = load i32, ptr %.12
  %.31 = zext i32 %.30 to i64
  %.32 = xor i64 %.29, %.31
  %.33 = trunc i64 %.32 to i32
  ret i32 %.33
}

define i64 @xcr0__2fb86de4() alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.4 = alloca i32
  %.7 = alloca i32
  %.2 = add i64 0, 0
  %.3 = trunc i64 %.2 to i32
  store i32 %.3, ptr %.1
  %.5 = add i64 0, 0
  %.6 = trunc i64 %.5 to i32
  store i32 %.6, ptr %.4
  %.8 = add i64 0, 0
  %.9 = trunc i64 %.8 to i32
  store i32 %.9, ptr %.7
  %.10 = load i32, ptr %.7
  %.11 = call { i32, i32 } asm sideeffect "xgetbv", "={rax},={rdx},{rcx},~{memory},~{dirflag},~{fpsr},~{flags}"(i32 %.10)
  %.12 = extractvalue { i32, i32 } %.11, 0
  store i32 %.12, ptr %.1
  %.13 = extractvalue { i32, i32 } %.11, 1
  store i32 %.13, ptr %.4
  %.14 = load i32, ptr %.4
  %.15 = zext i32 %.14 to i64
  %.16 = trunc i64 %.15 to i32
  %.17 = zext i32 %.16 to i64
  %.18 = add i64 0, 32
  %.19 = icmp uge i64 %.18, 64
  br i1 %.19, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.3, i64 48)
  unreachable
L1:
  %.20 = shl i64 %.17, %.18
  %.21 = load i32, ptr %.1
  %.22 = zext i32 %.21 to i64
  %.23 = trunc i64 %.22 to i32
  %.24 = zext i32 %.23 to i64
  %.25 = or i64 %.20, %.24
  ret i64 %.25
}

define i64 @control__2fb86de4(i64 %v.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %v.arg, ptr %.1
  %.3 = add i64 0, 0
  store i64 %.3, ptr %.2
  %.4 = load i64, ptr %.1
  %.5 = call i64 asm sideeffect "movq %cr2, $0\0Amovq %cr3, $0\0Amovq $1, %cr3", "=&r,r,~{memory},~{dirflag},~{fpsr},~{flags}"(i64 %.4)
  store i64 %.5, ptr %.2
  %.6 = load i64, ptr %.2
  ret i64 %.6
}

define i64 @msr__2fb86de4(i32 %idx.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i32
  %.2 = alloca i32
  %.5 = alloca i32
  store i32 %idx.arg, ptr %.1
  %.3 = add i64 0, 0
  %.4 = trunc i64 %.3 to i32
  store i32 %.4, ptr %.2
  %.6 = add i64 0, 0
  %.7 = trunc i64 %.6 to i32
  store i32 %.7, ptr %.5
  %.8 = load i32, ptr %.1
  %.9 = call { i32, i32 } asm sideeffect "rdmsr\0Awrmsr", "={rax},={rdx},{rcx},~{memory},~{dirflag},~{fpsr},~{flags}"(i32 %.8)
  %.10 = extractvalue { i32, i32 } %.9, 0
  store i32 %.10, ptr %.2
  %.11 = extractvalue { i32, i32 } %.9, 1
  store i32 %.11, ptr %.5
  %.12 = call { i32, i32 } asm sideeffect "rdtsc", "={rax},={rdx},~{memory},~{dirflag},~{fpsr},~{flags}"()
  %.13 = extractvalue { i32, i32 } %.12, 0
  store i32 %.13, ptr %.2
  %.14 = extractvalue { i32, i32 } %.12, 1
  store i32 %.14, ptr %.5
  %.15 = load i32, ptr %.5
  %.16 = zext i32 %.15 to i64
  %.17 = trunc i64 %.16 to i32
  %.18 = zext i32 %.17 to i64
  %.19 = add i64 0, 32
  %.20 = icmp uge i64 %.19, 64
  br i1 %.20, label %L0, label %L1
L0:
  call void @__ritz_overflow_trap(ptr @.str.4, i64 48)
  unreachable
L1:
  %.21 = shl i64 %.18, %.19
  %.22 = load i32, ptr %.2
  %.23 = zext i32 %.22 to i64
  %.24 = trunc i64 %.23 to i32
  %.25 = zext i32 %.24 to i64
  %.26 = or i64 %.21, %.25
  ret i64 %.26
}

define void @system__2fb86de4(i64 %p.arg, i16 %sel.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i16
  store i64 %p.arg, ptr %.1
  store i16 %sel.arg, ptr %.2
  %.3 = load ptr, ptr %.1
  %.4 = load i16, ptr %.2
  call void asm sideeffect "cli\0Asti\0Ahlt\0Alidt ($0)\0Altr $1\0Ainvlpg ($0)\0Aclflush ($0)", "r,r,~{memory},~{dirflag},~{fpsr},~{flags}"(ptr %.3, i16 %.4)
  ret void
}

define void @fences__2fb86de4(i64 %p.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  store i64 %p.arg, ptr %.1
  %.2 = load ptr, ptr %.1
  call void asm sideeffect "lfence\0Amfence\0Asfence\0Apause\0Anop\0Anopl ($0)", "r,~{memory},~{dirflag},~{fpsr},~{flags}"(ptr %.2)
  ret void
}

define i64 @loop_down__2fb86de4(i64 %n.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  store i64 %n.arg, ptr %.1
  %.3 = load i64, ptr %.1
  store i64 %.3, ptr %.2
  %.4 = load i64, ptr %.2
  %.5 = call i64 asm sideeffect "1:\0Adecq $0\0Ajnz 1b", "=&r,0,~{memory},~{dirflag},~{fpsr},~{flags}"(i64 %.4)
  store i64 %.5, ptr %.2
  %.6 = load i64, ptr %.2
  ret i64 %.6
}

define void @jump__2fb86de4(i64 %target.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  store i64 %target.arg, ptr %.1
  %.2 = load i64, ptr %.1
  call void asm sideeffect "jmpq *$0", "r,~{memory},~{dirflag},~{fpsr},~{flags}"(i64 %.2)
  ret void
}

define void @leave__2fb86de4() alignstack(16) "no-builtins" {
entry:
  call void asm sideeffect "retq", "~{memory},~{dirflag},~{fpsr},~{flags}"()
  ret void
}

define i64 @raw_syscall__2fb86de4(i64 %nr.arg, i64 %a.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.3 = alloca i64
  store i64 %nr.arg, ptr %.1
  store i64 %a.arg, ptr %.2
  %.4 = load i64, ptr %.1
  store i64 %.4, ptr %.3
  %.5 = load i64, ptr %.3
  %.6 = load i64, ptr %.2
  %.7 = call i64 asm sideeffect "syscall", "={rax},0,{rdi},~{rcx},~{r11},~{memory},~{dirflag},~{fpsr},~{flags}"(i64 %.5, i64 %.6)
  store i64 %.7, ptr %.3
  %.8 = load i64, ptr %.3
  ret i64 %.8
}

define i32 @main() alignstack(16) "no-builtins" {
entry:
  %.1 = add i64 0, 0
  %.2 = trunc i64 %.1 to i32
  ret i32 %.2
}


@.str.0 = private constant [40 x i8] c"asm.ritz:20:5: integer overflow in `+`\0A\00"
@.str.1 = private constant [40 x i8] c"asm.ritz:64:6: integer overflow in `+`\0A\00"
@.str.2 = private constant [40 x i8] c"asm.ritz:64:6: integer overflow in `+`\0A\00"
@.str.3 = private constant [49 x i8] c"asm.ritz:81:7: shift count out of range in `<<`\0A\00"
@.str.4 = private constant [49 x i8] c"asm.ritz:99:7: shift count out of range in `<<`\0A\00"
declare void @rt_hex(...) "no-builtins"

declare { i32, i1 } @llvm.uadd.with.overflow.i32(i32, i32)
declare { i64, i1 } @llvm.uadd.with.overflow.i64(i64, i64)
define internal void @__ritz_overflow_trap(ptr %msg, i64 %len) cold noinline noreturn nounwind {
entry:
  %w = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 1, i64 2, ptr %msg, i64 %len)
  %x = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1)
  unreachable
}
