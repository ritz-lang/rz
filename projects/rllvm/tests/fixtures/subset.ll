; Every module line, type, instruction, constant and attribute in the subset
; (DESIGN.md "LLVM IR subset"), for the parser's round-trip test. Not run.
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

$once = comdat any
$gen = comdat any

%Pair = type {i32, i32}
%Mixed = type { i8, i64, float }
%Packed = type <{ i8, i32 }>
%Nest = type {%Pair, [4 x i16], <4 x i32>, ptr}
%Fwd = type {%Later}
%Later = type {i64}
%Result$i64_E = type { i8, [7 x i8], [8 x i8] }

@.str = private unnamed_addr constant [6 x i8] c"hi\0A\00\22\5C"
@.const.a = private constant [3 x i8] c"abc"
@counter = global i64 0
@weak_ptr = weak global ptr null
@odr_flag = weak_odr global i1 0
@odr_rec = weak_odr global %Pair zeroinitializer
@ext = external global i32
@table = constant [2 x ptr] [ptr @.str, ptr @counter]
@pair = internal global %Pair { i32 1, i32 -2 }
@mixed = global %Mixed { i8 7, i64 9, float 1.500000e+00 }
@packed = global %Packed <{ i8 1, i32 2 }>
@vec = global <4 x i32> <i32 1, i32 2, i32 3, i32 4>
@vec_z = global <2 x i64> zeroinitializer
@dbl = global double 0x3FF0000000000000
@flt = global float -0.000000e+00
@gep_c = global ptr getelementptr (i8, ptr @.str, i64 1)
@gep_ib = global ptr getelementptr ([6 x i8], ptr @.str, i64 0, i64 2)
@arr2 = global [2 x [2 x i8]] [[2 x i8] c"ab", [2 x i8] zeroinitializer]
@i8pp = weak global i8** null
@nl = private constant [1 x i8] c"\0A"
@aligned = global i64 5, align 8
@addr = global i64 ptrtoint (ptr @.str to i64)
@size = global i64 ptrtoint (ptr getelementptr (%Nest, ptr null, i32 1) to i64)

declare i32 @main_decl(i32, i8**, i8**)
declare i64 @var_fn(...) "no-builtins"
declare void @takes(ptr, i64, ...)
declare { i64, i1 } @llvm.sadd.with.overflow.i64(i64, i64)
declare { i8, i1 } @llvm.umul.with.overflow.i8(i8, i8)
declare i32 @llvm.fshl.i32(i32, i32, i32)
declare i16 @llvm.fshr.i16(i16, i16, i16)
declare i64 @llvm.ctlz.i64(i64, i1)
declare i8 @llvm.cttz.i8(i8, i1)
declare i32 @llvm.ctpop.i32(i32)
declare i16 @llvm.bswap.i16(i16)
declare float @llvm.fabs.f32(float)
declare double @llvm.fabs.f64(double)
declare i32 @llvm.fptosi.sat.i32.f64(double)
declare i64 @llvm.fptoui.sat.i64.f32(float)
declare void @llvm.trap() cold noreturn nounwind
declare <4 x i32> @llvm.x86.sha256rnds2(<4 x i32>, <4 x i32>, <4 x i32>)
declare <2 x i64> @llvm.x86.aesni.aesenc(<2 x i64>, <2 x i64>)
declare <2 x i64> @llvm.x86.pclmulqdq(<2 x i64>, <2 x i64>, i8)
declare <2 x i64> @llvm.x86.sse2.psad.bw(<16 x i8>, <16 x i8>)

define i32 @ints(i32 %a, i32 %b) alignstack(16) "no-builtins" {
entry:
  %add = add i32 %a, %b
  %sub = sub i32 %a, %b
  %mul = mul i32 %add, %sub
  %ud = udiv i32 %mul, 3
  %sd = sdiv i32 %mul, -3
  %ur = urem i32 %ud, 7
  %sr = srem i32 %sd, 7
  %sh = shl i32 %ur, 2
  %lr = lshr i32 %sh, 1
  %ar = ashr i32 %sr, 1
  %an = and i32 %lr, %ar
  %o = or i32 %an, 1
  %x = xor i32 %o, -1
  %c1 = icmp eq i32 %x, 0
  %c2 = icmp ne i32 %x, 0
  %c3 = icmp ult i32 %a, %b
  %c4 = icmp sge i32 %a, %b
  %t = trunc i32 %x to i8
  %z = zext i8 %t to i64
  %s = sext i8 %t to i16
  %s32 = sext i16 %s to i32
  %sel = select i1 %c1, i32 %s32, i32 %a
  %bsel = select i1 %c2, i1 %c3, i1 %c4
  br i1 %bsel, label %L1, label %L2
L1:
  br label %L2
L2:
  %p = phi i32 [ %sel, %entry ], [ 0, %L1 ]
  ret i32 %p
}

define <4 x i32> @vecs(<4 x i32> %a, <4 x i32> %b, <2 x i64> %q, <16 x i8> %w, <8 x i16> %h) alignstack(16) "no-builtins" {
entry:
  %add = add <4 x i32> %a, %b
  %mul = mul <4 x i32> %add, %b
  %sh = shl <4 x i32> %mul, <i32 1, i32 1, i32 1, i32 1>
  %cmp = icmp sgt <4 x i32> %sh, zeroinitializer
  %e = extractelement <4 x i32> %sh, i32 2
  %i = insertelement <4 x i32> %sh, i32 %e, i64 0
  %sv = shufflevector <4 x i32> %i, <4 x i32> %a, <4 x i32> <i32 0, i32 5, i32 2, i32 7>
  %sv2 = shufflevector <4 x i32> %sv, <4 x i32> undef, <4 x i32> zeroinitializer
  %bc = bitcast <4 x i32> %sv2 to <2 x i64>
  %qx = xor <2 x i64> %bc, %q
  %back = bitcast <2 x i64> %qx to <4 x i32>
  %sel = select <4 x i1> %cmp, <4 x i32> %back, <4 x i32> %a
  %hh = sub <8 x i16> %h, %h
  %ww = and <16 x i8> %w, %w
  ret <4 x i32> %sel
}

define internal <8 x i32> @wide(<8 x i32> %a, <4 x i64> %b) {
entry:
  %r = add <8 x i32> %a, %a
  ret <8 x i32> %r
}

define double @floats(float %f, double %d) alignstack(16) "no-builtins" {
entry:
  %n = fneg float %f
  %a = fadd float %n, 1.000000e+00
  %s = fsub float %a, %f
  %m = fmul double %d, 2.500000e-01
  %q = fdiv double %m, 0x7FF0000000000000
  %c1 = fcmp olt double %q, %d
  %c2 = fcmp uno double %q, %q
  %c3 = fcmp une float %s, 0.000000e+00
  %c4 = fcmp true float %s, %s
  %c5 = and i1 %c1, %c2
  %c6 = or i1 %c3, %c4
  %ext = fpext float %s to double
  %tr = fptrunc double %ext to float
  %si = sitofp i64 -5 to double
  %ui = uitofp i32 5 to float
  %fi = fptosi double %si to i32
  %fs = call i32 @llvm.fptosi.sat.i32.f64(double %q)
  %fu = call i64 @llvm.fptoui.sat.i64.f32(float %ui)
  %ab = call float @llvm.fabs.f32(float %tr)
  %ad = call double @llvm.fabs.f64(double %m)
  %r = select i1 %c6, double %ad, double %ext
  ret double %r
}

define void @memory(ptr %p, ptr sret({ i64, i64, i64 }) %out, ptr byval({ i64, i64, i64 }) align 8 %in) alignstack(16) "no-builtins" {
entry:
  %slot = alloca i64
  %arr = alloca [4 x i32], align 16
  %rec = alloca %Nest, align 16
  %dyn = alloca i32, i64 4
  %dyn16 = alloca i8, i32 3, align 16
  store i64 1, ptr %slot
  store i64 2, ptr %slot, align 8
  %v = load i64, ptr %slot
  %v8 = load i64, ptr %slot, align 1
  store volatile i64 %v, ptr %p
  %vv = load volatile i64, ptr %p
  %a = load atomic i64, ptr %p seq_cst, align 8
  store atomic i64 %a, ptr %p seq_cst, align 8
  %cx = cmpxchg ptr %p, i64 %a, i64 %vv seq_cst seq_cst
  %cv = extractvalue { i64, i1 } %cx, 0
  %ok = extractvalue { i64, i1 } %cx, 1
  %r1 = atomicrmw xchg ptr %p, i64 1 seq_cst
  %r2 = atomicrmw add ptr %p, i64 1 seq_cst
  %r3 = atomicrmw sub ptr %p, i64 1 seq_cst
  %r4 = atomicrmw and ptr %p, i64 1 seq_cst
  %r5 = atomicrmw or ptr %p, i64 1 seq_cst
  %r6 = atomicrmw xor ptr %p, i64 1 seq_cst
  fence seq_cst
  %g1 = getelementptr i8, ptr %p, i64 8
  %g2 = getelementptr [4 x i32], ptr %arr, i64 0, i64 3
  %g3 = getelementptr %Nest, ptr %rec, i32 0, i32 1, i64 2
  %g4 = getelementptr %Pair, ptr %p, i64 1, i32 1
  %pi = ptrtoint ptr %g1 to i64
  %ip = inttoptr i64 %pi to ptr
  %tp = inttoptr i64 %pi to i8*
  %pt = ptrtoint [1 x i8]* @nl to i64
  %ld = load i8*, i8** @i8pp
  %u = insertvalue { i64, i64, i64 } undef, i64 %cv, 0
  %u2 = insertvalue { i64, i64, i64 } %u, i64 %pt, 2
  store { i64, i64, i64 } %u2, ptr %out
  %ex = extractvalue %Nest zeroinitializer, 1, 2
  %ag = insertvalue [2 x %Pair] zeroinitializer, %Pair { i32 3, i32 4 }, 1
  ret void
}

define %Pair @calls(i64 %n) alignstack(16) "no-builtins" {
entry:
  %r = call i64 (...) @var_fn(i64 %n, i32 2)
  call void (ptr, i64, ...) @takes(ptr @.str, i64 1, double 1.0)
  %o = call { i64, i1 } @llvm.sadd.with.overflow.i64(i64 %n, i64 1)
  %m = call { i8, i1 } @llvm.umul.with.overflow.i8(i8 3, i8 100)
  %rot = call i32 @llvm.fshl.i32(i32 1, i32 1, i32 3)
  %fsh = call i16 @llvm.fshr.i16(i16 1, i16 2, i16 17)
  %lz = call i64 @llvm.ctlz.i64(i64 %n, i1 false)
  %tz = call i8 @llvm.cttz.i8(i8 0, i1 false)
  %pc = call i32 @llvm.ctpop.i32(i32 255)
  %bs = call i16 @llvm.bswap.i16(i16 258)
  %fp = load ptr, ptr @weak_ptr
  %ind = call i64 %fp(i64 %n)
  %sr = alloca { i64, i64, i64 }
  call void @memory(ptr %fp, ptr sret({ i64, i64, i64 }) %sr, ptr byval({ i64, i64, i64 }) align 8 %sr)
  %w = call <8 x i32> @wide(<8 x i32> zeroinitializer, <4 x i64> zeroinitializer)
  %aes = call <2 x i64> @llvm.x86.aesni.aesenc(<2 x i64> zeroinitializer, <2 x i64> zeroinitializer)
  %cl = call <2 x i64> @llvm.x86.pclmulqdq(<2 x i64> %aes, <2 x i64> %aes, i8 17)
  %sad = call <2 x i64> @llvm.x86.sse2.psad.bw(<16 x i8> zeroinitializer, <16 x i8> zeroinitializer)
  %sha = call <4 x i32> @llvm.x86.sha256rnds2(<4 x i32> zeroinitializer, <4 x i32> zeroinitializer, <4 x i32> zeroinitializer)
  %t = trunc i64 %r to i32
  %p0 = insertvalue %Pair undef, i32 %t, 0
  %p1 = insertvalue %Pair %p0, i32 %rot, 1
  ret %Pair %p1
}

define i64 @asm_blocks(i64 %x) alignstack(16) "no-builtins" {
entry:
  %a = call i64 asm sideeffect "addq $$1, $0", "=r,0,~{dirflag},~{fpsr},~{flags}"(i64 %x)
  %b = call i64 asm sideeffect "movq ${1}, $0\0Ashlq $$3, $0", "=&r,r,~{memory}"(i64 %a)
  %xg = call { i32, i32 } asm sideeffect "xgetbv", "={ax},={dx},{cx}"(i32 0)
  %lo = extractvalue { i32, i32 } %xg, 0
  %s = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 39, i64 0)
  call void asm sideeffect "
    # a comment line
    pause
  ", "~{memory}"()
  ret i64 %b
}

define void @naked_entry() naked {
entry:
  call void asm sideeffect "andq $$-16, %rsp\0Acall main", "~{rsp},~{memory}"()
  unreachable
}

define internal void @cold_trap() cold noinline noreturn nounwind {
entry:
  call void @llvm.trap()
  unreachable
}

define void @kernel_fn() noredzone sspstrong alignstack(16) "no-builtins" {
entry:
  ret void
}

define void @attr_fn() alwaysinline inlinehint {
entry:
  ret void
}

define void @crypto(<4 x i32> %a) alignstack(16) "no-builtins" "target-cpu"="x86-64" "target-features"="+sha,+aes,+pclmul" {
entry:
  ret void
}

define linkonce_odr i64 @once(i64 %x) comdat {
entry:
  ret i64 %x
}

define weak_odr i32 @gen(i32 %x) comdat {
entry:
  ret i32 %x
}

define weak void @weak_fn() {
entry:
  ret void
}

define available_externally i64 @inl(i64 %x) alignstack(16) "no-builtins" inlinehint {
entry:
  ret i64 %x
}

define private void @priv() {
entry:
  ret void
}
