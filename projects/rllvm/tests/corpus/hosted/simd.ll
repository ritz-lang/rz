; ModuleID = 'ritz1_output'
target triple = "x86_64-unknown-linux-gnu"

%Span$u8 = type {ptr, i64}
%StrView = type {ptr, i64}





define void @sha__a1d77f5c(i64 %a.arg, i64 %b.arg, i64 %c.arg, ptr %out.arg) alignstack(16) "no-builtins" "target-cpu"="x86-64" "target-features"="+sha" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.3 = alloca i64
  %.4 = alloca ptr
  %.5 = alloca <4 x i32>
  %.16 = alloca <4 x i32>
  %.27 = alloca <4 x i32>
  %.38 = alloca <4 x i32>
  %.43 = alloca <4 x i32>
  %.47 = alloca <4 x i32>
  store i64 %a.arg, ptr %.1
  store i64 %b.arg, ptr %.2
  store i64 %c.arg, ptr %.3
  store ptr %out.arg, ptr %.4
  %.6 = load i64, ptr %.1
  %.7 = add i64 0, 0
  %.8 = mul i64 %.7, 4
  %.9 = inttoptr i64 %.6 to ptr
  %.10 = getelementptr i8, ptr %.9, i64 %.8
  %.11 = ptrtoint ptr %.10 to i64
  %.12 = inttoptr i64 %.11 to ptr
  %.13 = ptrtoint ptr %.12 to i64
  %.14 = inttoptr i64 %.13 to ptr  ; simd_load: ptr cast
  %.15 = load <4 x i32>, ptr %.14, align 1
  store <4 x i32> %.15, ptr %.5
  %.17 = load i64, ptr %.2
  %.18 = add i64 0, 0
  %.19 = mul i64 %.18, 4
  %.20 = inttoptr i64 %.17 to ptr
  %.21 = getelementptr i8, ptr %.20, i64 %.19
  %.22 = ptrtoint ptr %.21 to i64
  %.23 = inttoptr i64 %.22 to ptr
  %.24 = ptrtoint ptr %.23 to i64
  %.25 = inttoptr i64 %.24 to ptr  ; simd_load: ptr cast
  %.26 = load <4 x i32>, ptr %.25, align 1
  store <4 x i32> %.26, ptr %.16
  %.28 = load i64, ptr %.3
  %.29 = add i64 0, 0
  %.30 = mul i64 %.29, 4
  %.31 = inttoptr i64 %.28 to ptr
  %.32 = getelementptr i8, ptr %.31, i64 %.30
  %.33 = ptrtoint ptr %.32 to i64
  %.34 = inttoptr i64 %.33 to ptr
  %.35 = ptrtoint ptr %.34 to i64
  %.36 = inttoptr i64 %.35 to ptr  ; simd_load: ptr cast
  %.37 = load <4 x i32>, ptr %.36, align 1
  store <4 x i32> %.37, ptr %.27
  %.39 = load <4 x i32>, ptr %.5
  %.40 = load <4 x i32>, ptr %.16
  %.41 = load <4 x i32>, ptr %.27
  %.42 = call <4 x i32> @llvm.x86.sha256rnds2(<4 x i32> %.39, <4 x i32> %.40, <4 x i32> %.41)
  store <4 x i32> %.42, ptr %.38
  %.44 = load <4 x i32>, ptr %.38
  %.45 = load <4 x i32>, ptr %.16
  %.46 = call <4 x i32> @llvm.x86.sha256msg1(<4 x i32> %.44, <4 x i32> %.45)
  store <4 x i32> %.46, ptr %.43
  %.48 = load <4 x i32>, ptr %.43
  %.49 = load <4 x i32>, ptr %.27
  %.50 = call <4 x i32> @llvm.x86.sha256msg2(<4 x i32> %.48, <4 x i32> %.49)
  store <4 x i32> %.50, ptr %.47
  %.51 = load i64, ptr %.4
  %.52 = add i64 0, 0
  %.53 = mul i64 %.52, 4
  %.54 = inttoptr i64 %.51 to ptr
  %.55 = getelementptr i8, ptr %.54, i64 %.53
  %.56 = ptrtoint ptr %.55 to i64
  %.57 = inttoptr i64 %.56 to ptr
  %.58 = ptrtoint ptr %.57 to i64
  %.59 = load <4 x i32>, ptr %.47
  %.60 = inttoptr i64 %.58 to ptr  ; simd_store: ptr cast
  store <4 x i32> %.59, ptr %.60, align 1
  %.61 = add i64 0, 0  ; simd_store void
  ret void
}

define void @aes__a1d77f5c(i64 %state.arg, i64 %key.arg, ptr %out.arg) alignstack(16) "no-builtins" "target-cpu"="x86-64" "target-features"="+aes" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.3 = alloca ptr
  %.4 = alloca <2 x i64>
  %.15 = alloca <2 x i64>
  %.26 = alloca <2 x i64>
  %.30 = alloca <2 x i64>
  %.34 = alloca <2 x i64>
  %.38 = alloca <2 x i64>
  %.42 = alloca <2 x i64>
  %.45 = alloca <2 x i64>
  store i64 %state.arg, ptr %.1
  store i64 %key.arg, ptr %.2
  store ptr %out.arg, ptr %.3
  %.5 = load i64, ptr %.1
  %.6 = add i64 0, 0
  %.7 = mul i64 %.6, 8
  %.8 = inttoptr i64 %.5 to ptr
  %.9 = getelementptr i8, ptr %.8, i64 %.7
  %.10 = ptrtoint ptr %.9 to i64
  %.11 = inttoptr i64 %.10 to ptr
  %.12 = ptrtoint ptr %.11 to i64
  %.13 = inttoptr i64 %.12 to ptr  ; simd_load: ptr cast
  %.14 = load <2 x i64>, ptr %.13, align 1
  store <2 x i64> %.14, ptr %.4
  %.16 = load i64, ptr %.2
  %.17 = add i64 0, 0
  %.18 = mul i64 %.17, 8
  %.19 = inttoptr i64 %.16 to ptr
  %.20 = getelementptr i8, ptr %.19, i64 %.18
  %.21 = ptrtoint ptr %.20 to i64
  %.22 = inttoptr i64 %.21 to ptr
  %.23 = ptrtoint ptr %.22 to i64
  %.24 = inttoptr i64 %.23 to ptr  ; simd_load: ptr cast
  %.25 = load <2 x i64>, ptr %.24, align 1
  store <2 x i64> %.25, ptr %.15
  %.27 = load <2 x i64>, ptr %.4
  %.28 = load <2 x i64>, ptr %.15
  %.29 = call <2 x i64> @llvm.x86.aesni.aesenc(<2 x i64> %.27, <2 x i64> %.28)
  store <2 x i64> %.29, ptr %.26
  %.31 = load <2 x i64>, ptr %.26
  %.32 = load <2 x i64>, ptr %.15
  %.33 = call <2 x i64> @llvm.x86.aesni.aesenclast(<2 x i64> %.31, <2 x i64> %.32)
  store <2 x i64> %.33, ptr %.30
  %.35 = load <2 x i64>, ptr %.30
  %.36 = load <2 x i64>, ptr %.15
  %.37 = call <2 x i64> @llvm.x86.aesni.aesdec(<2 x i64> %.35, <2 x i64> %.36)
  store <2 x i64> %.37, ptr %.34
  %.39 = load <2 x i64>, ptr %.34
  %.40 = load <2 x i64>, ptr %.15
  %.41 = call <2 x i64> @llvm.x86.aesni.aesdeclast(<2 x i64> %.39, <2 x i64> %.40)
  store <2 x i64> %.41, ptr %.38
  %.43 = load <2 x i64>, ptr %.38
  %.44 = call <2 x i64> @llvm.x86.aesni.aesimc(<2 x i64> %.43)
  store <2 x i64> %.44, ptr %.42
  %.46 = load <2 x i64>, ptr %.42
  %.47 = call <2 x i64> @llvm.x86.aesni.aeskeygenassist(<2 x i64> %.46, i8 1)
  store <2 x i64> %.47, ptr %.45
  %.48 = load i64, ptr %.3
  %.49 = add i64 0, 0
  %.50 = mul i64 %.49, 8
  %.51 = inttoptr i64 %.48 to ptr
  %.52 = getelementptr i8, ptr %.51, i64 %.50
  %.53 = ptrtoint ptr %.52 to i64
  %.54 = inttoptr i64 %.53 to ptr
  %.55 = ptrtoint ptr %.54 to i64
  %.56 = load <2 x i64>, ptr %.45
  %.57 = inttoptr i64 %.55 to ptr  ; simd_store: ptr cast
  store <2 x i64> %.56, ptr %.57, align 1
  %.58 = add i64 0, 0  ; simd_store void
  ret void
}

define void @sad__a1d77f5c(i64 %a.arg, i64 %b.arg, ptr %out.arg) alignstack(16) "no-builtins" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.3 = alloca ptr
  %.4 = alloca <16 x i8>
  %.14 = alloca <16 x i8>
  %.24 = alloca <2 x i64>
  store i64 %a.arg, ptr %.1
  store i64 %b.arg, ptr %.2
  store ptr %out.arg, ptr %.3
  %.5 = load i64, ptr %.1
  %.6 = add i64 0, 0
  %.7 = inttoptr i64 %.5 to ptr
  %.8 = getelementptr i8, ptr %.7, i64 %.6
  %.9 = ptrtoint ptr %.8 to i64
  %.10 = inttoptr i64 %.9 to ptr
  %.11 = ptrtoint ptr %.10 to i64
  %.12 = inttoptr i64 %.11 to ptr  ; simd_load: ptr cast
  %.13 = load <16 x i8>, ptr %.12, align 1
  store <16 x i8> %.13, ptr %.4
  %.15 = load i64, ptr %.2
  %.16 = add i64 0, 0
  %.17 = inttoptr i64 %.15 to ptr
  %.18 = getelementptr i8, ptr %.17, i64 %.16
  %.19 = ptrtoint ptr %.18 to i64
  %.20 = inttoptr i64 %.19 to ptr
  %.21 = ptrtoint ptr %.20 to i64
  %.22 = inttoptr i64 %.21 to ptr  ; simd_load: ptr cast
  %.23 = load <16 x i8>, ptr %.22, align 1
  store <16 x i8> %.23, ptr %.14
  %.25 = load <16 x i8>, ptr %.4
  %.26 = load <16 x i8>, ptr %.14
  %.27 = call <2 x i64> @llvm.x86.sse2.psad.bw(<16 x i8> %.25, <16 x i8> %.26)
  store <2 x i64> %.27, ptr %.24
  %.28 = load i64, ptr %.3
  %.29 = add i64 0, 0
  %.30 = mul i64 %.29, 8
  %.31 = inttoptr i64 %.28 to ptr
  %.32 = getelementptr i8, ptr %.31, i64 %.30
  %.33 = ptrtoint ptr %.32 to i64
  %.34 = inttoptr i64 %.33 to ptr
  %.35 = ptrtoint ptr %.34 to i64
  %.36 = load <2 x i64>, ptr %.24
  %.37 = inttoptr i64 %.35 to ptr  ; simd_store: ptr cast
  store <2 x i64> %.36, ptr %.37, align 1
  %.38 = add i64 0, 0  ; simd_store void
  ret void
}

define void @clmul__a1d77f5c(i64 %a.arg, i64 %b.arg, ptr %out.arg) alignstack(16) "no-builtins" "target-cpu"="x86-64" "target-features"="+pclmul" {
entry:
  %.1 = alloca i64
  %.2 = alloca i64
  %.3 = alloca ptr
  %.4 = alloca <2 x i64>
  %.15 = alloca <2 x i64>
  %.26 = alloca <2 x i64>
  store i64 %a.arg, ptr %.1
  store i64 %b.arg, ptr %.2
  store ptr %out.arg, ptr %.3
  %.5 = load i64, ptr %.1
  %.6 = add i64 0, 0
  %.7 = mul i64 %.6, 8
  %.8 = inttoptr i64 %.5 to ptr
  %.9 = getelementptr i8, ptr %.8, i64 %.7
  %.10 = ptrtoint ptr %.9 to i64
  %.11 = inttoptr i64 %.10 to ptr
  %.12 = ptrtoint ptr %.11 to i64
  %.13 = inttoptr i64 %.12 to ptr  ; simd_load: ptr cast
  %.14 = load <2 x i64>, ptr %.13, align 1
  store <2 x i64> %.14, ptr %.4
  %.16 = load i64, ptr %.2
  %.17 = add i64 0, 0
  %.18 = mul i64 %.17, 8
  %.19 = inttoptr i64 %.16 to ptr
  %.20 = getelementptr i8, ptr %.19, i64 %.18
  %.21 = ptrtoint ptr %.20 to i64
  %.22 = inttoptr i64 %.21 to ptr
  %.23 = ptrtoint ptr %.22 to i64
  %.24 = inttoptr i64 %.23 to ptr  ; simd_load: ptr cast
  %.25 = load <2 x i64>, ptr %.24, align 1
  store <2 x i64> %.25, ptr %.15
  %.27 = load <2 x i64>, ptr %.4
  %.28 = load <2 x i64>, ptr %.15
  %.29 = call <2 x i64> @llvm.x86.pclmulqdq(<2 x i64> %.27, <2 x i64> %.28, i8 17)
  store <2 x i64> %.29, ptr %.26
  %.30 = load i64, ptr %.3
  %.31 = add i64 0, 0
  %.32 = mul i64 %.31, 8
  %.33 = inttoptr i64 %.30 to ptr
  %.34 = getelementptr i8, ptr %.33, i64 %.32
  %.35 = ptrtoint ptr %.34 to i64
  %.36 = inttoptr i64 %.35 to ptr
  %.37 = ptrtoint ptr %.36 to i64
  %.38 = load <2 x i64>, ptr %.26
  %.39 = inttoptr i64 %.37 to ptr  ; simd_store: ptr cast
  store <2 x i64> %.38, ptr %.39, align 1
  %.40 = add i64 0, 0  ; simd_store void
  ret void
}

define i32 @main() alignstack(16) "no-builtins" {
entry:
  %.1 = add i64 0, 0
  %.2 = trunc i64 %.1 to i32
  ret i32 %.2
}


declare <4 x i32> @llvm.x86.sha256rnds2(<4 x i32>, <4 x i32>, <4 x i32>)
declare <4 x i32> @llvm.x86.sha256msg1(<4 x i32>, <4 x i32>)
declare <4 x i32> @llvm.x86.sha256msg2(<4 x i32>, <4 x i32>)
declare <2 x i64> @llvm.x86.aesni.aesenc(<2 x i64>, <2 x i64>)
declare <2 x i64> @llvm.x86.aesni.aesenclast(<2 x i64>, <2 x i64>)
declare <2 x i64> @llvm.x86.aesni.aesdec(<2 x i64>, <2 x i64>)
declare <2 x i64> @llvm.x86.aesni.aesdeclast(<2 x i64>, <2 x i64>)
declare <2 x i64> @llvm.x86.aesni.aesimc(<2 x i64>)
declare <2 x i64> @llvm.x86.aesni.aeskeygenassist(<2 x i64>, i8)
declare <2 x i64> @llvm.x86.sse2.psad.bw(<16 x i8>, <16 x i8>)
declare <2 x i64> @llvm.x86.pclmulqdq(<2 x i64>, <2 x i64>, i8)

