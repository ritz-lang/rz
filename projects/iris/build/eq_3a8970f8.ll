; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

define i32 @"eq_i32"(i32 %"a.arg", i32 %"b.arg") !dbg !17
{
entry:
  %"a" = alloca i32
  store i32 %"a.arg", i32* %"a"
  call void @"llvm.dbg.declare"(metadata i32* %"a", metadata !20, metadata !7), !dbg !21
  %"b" = alloca i32
  store i32 %"b.arg", i32* %"b"
  call void @"llvm.dbg.declare"(metadata i32* %"b", metadata !22, metadata !7), !dbg !21
  %".8" = load i32, i32* %"a", !dbg !23
  %".9" = load i32, i32* %"b", !dbg !23
  %".10" = icmp eq i32 %".8", %".9" , !dbg !23
  br i1 %".10", label %"if.then", label %"if.end", !dbg !23
if.then:
  %".12" = trunc i64 1 to i32 , !dbg !24
  ret i32 %".12", !dbg !24
if.end:
  %".14" = trunc i64 0 to i32 , !dbg !25
  ret i32 %".14", !dbg !25
}

define i32 @"eq_i64"(i64 %"a.arg", i64 %"b.arg") !dbg !18
{
entry:
  %"a" = alloca i64
  store i64 %"a.arg", i64* %"a"
  call void @"llvm.dbg.declare"(metadata i64* %"a", metadata !26, metadata !7), !dbg !27
  %"b" = alloca i64
  store i64 %"b.arg", i64* %"b"
  call void @"llvm.dbg.declare"(metadata i64* %"b", metadata !28, metadata !7), !dbg !27
  %".8" = load i64, i64* %"a", !dbg !29
  %".9" = load i64, i64* %"b", !dbg !29
  %".10" = icmp eq i64 %".8", %".9" , !dbg !29
  br i1 %".10", label %"if.then", label %"if.end", !dbg !29
if.then:
  %".12" = trunc i64 1 to i32 , !dbg !30
  ret i32 %".12", !dbg !30
if.end:
  %".14" = trunc i64 0 to i32 , !dbg !31
  ret i32 %".14", !dbg !31
}

define i32 @"eq_u64"(i64 %"a.arg", i64 %"b.arg") !dbg !19
{
entry:
  %"a" = alloca i64
  store i64 %"a.arg", i64* %"a"
  call void @"llvm.dbg.declare"(metadata i64* %"a", metadata !32, metadata !7), !dbg !33
  %"b" = alloca i64
  store i64 %"b.arg", i64* %"b"
  call void @"llvm.dbg.declare"(metadata i64* %"b", metadata !34, metadata !7), !dbg !33
  %".8" = load i64, i64* %"a", !dbg !35
  %".9" = load i64, i64* %"b", !dbg !35
  %".10" = icmp eq i64 %".8", %".9" , !dbg !35
  br i1 %".10", label %"if.then", label %"if.end", !dbg !35
if.then:
  %".12" = trunc i64 1 to i32 , !dbg !36
  ret i32 %".12", !dbg !36
if.end:
  %".14" = trunc i64 0 to i32 , !dbg !37
  ret i32 %".14", !dbg !37
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/ritzunit/ritz/ritzlib", filename: "eq.ritz")
!1 = distinct !DICompileUnit(emissionKind: FullDebug, file: !0, isOptimized: false, language: DW_LANG_C, producer: "ritz0 1.0", runtimeVersion: 0)
!2 = !DIBasicType()
!3 = !{  }
!4 = !DISubroutineType(types: !3)
!5 = !{ i32 2, !"Dwarf Version", i32 4 }
!6 = !{ i32 2, !"Debug Info Version", i32 3 }
!7 = !DIExpression()
!8 = !DIBasicType(encoding: DW_ATE_signed, name: "i8", size: 8)
!9 = !DIBasicType(encoding: DW_ATE_signed, name: "i16", size: 16)
!10 = !DIBasicType(encoding: DW_ATE_signed, name: "i32", size: 32)
!11 = !DIBasicType(encoding: DW_ATE_signed, name: "i64", size: 64)
!12 = !DIBasicType(encoding: DW_ATE_unsigned, name: "u8", size: 8)
!13 = !DIBasicType(encoding: DW_ATE_unsigned, name: "u16", size: 16)
!14 = !DIBasicType(encoding: DW_ATE_unsigned, name: "u32", size: 32)
!15 = !DIBasicType(encoding: DW_ATE_unsigned, name: "u64", size: 64)
!16 = !DIBasicType(encoding: DW_ATE_boolean, name: "bool", size: 8)
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 14, name: "eq_i32", scopeLine: 14, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 19, name: "eq_i64", scopeLine: 19, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 24, name: "eq_u64", scopeLine: 24, type: !4, unit: !1)
!20 = !DILocalVariable(file: !0, line: 14, name: "a", scope: !17, type: !10)
!21 = !DILocation(column: 1, line: 14, scope: !17)
!22 = !DILocalVariable(file: !0, line: 14, name: "b", scope: !17, type: !10)
!23 = !DILocation(column: 5, line: 15, scope: !17)
!24 = !DILocation(column: 9, line: 16, scope: !17)
!25 = !DILocation(column: 5, line: 17, scope: !17)
!26 = !DILocalVariable(file: !0, line: 19, name: "a", scope: !18, type: !11)
!27 = !DILocation(column: 1, line: 19, scope: !18)
!28 = !DILocalVariable(file: !0, line: 19, name: "b", scope: !18, type: !11)
!29 = !DILocation(column: 5, line: 20, scope: !18)
!30 = !DILocation(column: 9, line: 21, scope: !18)
!31 = !DILocation(column: 5, line: 22, scope: !18)
!32 = !DILocalVariable(file: !0, line: 24, name: "a", scope: !19, type: !15)
!33 = !DILocation(column: 1, line: 24, scope: !19)
!34 = !DILocalVariable(file: !0, line: 24, name: "b", scope: !19, type: !15)
!35 = !DILocation(column: 5, line: 25, scope: !19)
!36 = !DILocation(column: 9, line: 26, scope: !19)
!37 = !DILocation(column: 5, line: 27, scope: !19)