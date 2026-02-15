; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

define i64 @"fnv1a_init"() !dbg !17
{
entry:
  ret i64 14695981039346656037, !dbg !25
}

define i64 @"fnv1a_byte"(i64 %"h.arg", i8 %"b.arg") !dbg !18
{
entry:
  %"h" = alloca i64
  %"result.addr" = alloca i64, !dbg !29
  store i64 %"h.arg", i64* %"h"
  call void @"llvm.dbg.declare"(metadata i64* %"h", metadata !26, metadata !7), !dbg !27
  %"b" = alloca i8
  store i8 %"b.arg", i8* %"b"
  call void @"llvm.dbg.declare"(metadata i8* %"b", metadata !28, metadata !7), !dbg !27
  %".8" = load i64, i64* %"h", !dbg !29
  %".9" = load i8, i8* %"b", !dbg !29
  %".10" = zext i8 %".9" to i64 , !dbg !29
  %".11" = xor i64 %".8", %".10", !dbg !29
  store i64 %".11", i64* %"result.addr", !dbg !29
  call void @"llvm.dbg.declare"(metadata i64* %"result.addr", metadata !30, metadata !7), !dbg !31
  %".14" = load i64, i64* %"result.addr", !dbg !32
  %".15" = mul i64 %".14", 1099511628211, !dbg !32
  ret i64 %".15", !dbg !32
}

define i64 @"fnv1a_i32"(i64 %"h.arg", i32 %"val.arg") !dbg !19
{
entry:
  %"h" = alloca i64
  %"v.addr" = alloca i64, !dbg !36
  %"r.addr" = alloca i64, !dbg !39
  store i64 %"h.arg", i64* %"h"
  call void @"llvm.dbg.declare"(metadata i64* %"h", metadata !33, metadata !7), !dbg !34
  %"val" = alloca i32
  store i32 %"val.arg", i32* %"val"
  call void @"llvm.dbg.declare"(metadata i32* %"val", metadata !35, metadata !7), !dbg !34
  %".8" = load i32, i32* %"val", !dbg !36
  %".9" = zext i32 %".8" to i64 , !dbg !36
  store i64 %".9", i64* %"v.addr", !dbg !36
  call void @"llvm.dbg.declare"(metadata i64* %"v.addr", metadata !37, metadata !7), !dbg !38
  %".12" = load i64, i64* %"h", !dbg !39
  %".13" = load i64, i64* %"v.addr", !dbg !39
  %".14" = and i64 %".13", 255, !dbg !39
  %".15" = trunc i64 %".14" to i8 , !dbg !39
  %".16" = call i64 @"fnv1a_byte"(i64 %".12", i8 %".15"), !dbg !39
  store i64 %".16", i64* %"r.addr", !dbg !39
  call void @"llvm.dbg.declare"(metadata i64* %"r.addr", metadata !40, metadata !7), !dbg !41
  %".19" = load i64, i64* %"r.addr", !dbg !42
  %".20" = load i64, i64* %"v.addr", !dbg !42
  %".21" = lshr i64 %".20", 8, !dbg !42
  %".22" = and i64 %".21", 255, !dbg !42
  %".23" = trunc i64 %".22" to i8 , !dbg !42
  %".24" = call i64 @"fnv1a_byte"(i64 %".19", i8 %".23"), !dbg !42
  store i64 %".24", i64* %"r.addr", !dbg !42
  %".26" = load i64, i64* %"r.addr", !dbg !43
  %".27" = load i64, i64* %"v.addr", !dbg !43
  %".28" = lshr i64 %".27", 16, !dbg !43
  %".29" = and i64 %".28", 255, !dbg !43
  %".30" = trunc i64 %".29" to i8 , !dbg !43
  %".31" = call i64 @"fnv1a_byte"(i64 %".26", i8 %".30"), !dbg !43
  store i64 %".31", i64* %"r.addr", !dbg !43
  %".33" = load i64, i64* %"r.addr", !dbg !44
  %".34" = load i64, i64* %"v.addr", !dbg !44
  %".35" = lshr i64 %".34", 24, !dbg !44
  %".36" = and i64 %".35", 255, !dbg !44
  %".37" = trunc i64 %".36" to i8 , !dbg !44
  %".38" = call i64 @"fnv1a_byte"(i64 %".33", i8 %".37"), !dbg !44
  store i64 %".38", i64* %"r.addr", !dbg !44
  %".40" = load i64, i64* %"r.addr", !dbg !45
  ret i64 %".40", !dbg !45
}

define i64 @"fnv1a_i64"(i64 %"h.arg", i64 %"val.arg") !dbg !20
{
entry:
  %"h" = alloca i64
  %"v.addr" = alloca i64, !dbg !49
  %"r.addr" = alloca i64, !dbg !52
  store i64 %"h.arg", i64* %"h"
  call void @"llvm.dbg.declare"(metadata i64* %"h", metadata !46, metadata !7), !dbg !47
  %"val" = alloca i64
  store i64 %"val.arg", i64* %"val"
  call void @"llvm.dbg.declare"(metadata i64* %"val", metadata !48, metadata !7), !dbg !47
  %".8" = load i64, i64* %"val", !dbg !49
  store i64 %".8", i64* %"v.addr", !dbg !49
  call void @"llvm.dbg.declare"(metadata i64* %"v.addr", metadata !50, metadata !7), !dbg !51
  %".11" = load i64, i64* %"h", !dbg !52
  %".12" = load i64, i64* %"v.addr", !dbg !52
  %".13" = and i64 %".12", 255, !dbg !52
  %".14" = trunc i64 %".13" to i8 , !dbg !52
  %".15" = call i64 @"fnv1a_byte"(i64 %".11", i8 %".14"), !dbg !52
  store i64 %".15", i64* %"r.addr", !dbg !52
  call void @"llvm.dbg.declare"(metadata i64* %"r.addr", metadata !53, metadata !7), !dbg !54
  %".18" = load i64, i64* %"r.addr", !dbg !55
  %".19" = load i64, i64* %"v.addr", !dbg !55
  %".20" = lshr i64 %".19", 8, !dbg !55
  %".21" = and i64 %".20", 255, !dbg !55
  %".22" = trunc i64 %".21" to i8 , !dbg !55
  %".23" = call i64 @"fnv1a_byte"(i64 %".18", i8 %".22"), !dbg !55
  store i64 %".23", i64* %"r.addr", !dbg !55
  %".25" = load i64, i64* %"r.addr", !dbg !56
  %".26" = load i64, i64* %"v.addr", !dbg !56
  %".27" = lshr i64 %".26", 16, !dbg !56
  %".28" = and i64 %".27", 255, !dbg !56
  %".29" = trunc i64 %".28" to i8 , !dbg !56
  %".30" = call i64 @"fnv1a_byte"(i64 %".25", i8 %".29"), !dbg !56
  store i64 %".30", i64* %"r.addr", !dbg !56
  %".32" = load i64, i64* %"r.addr", !dbg !57
  %".33" = load i64, i64* %"v.addr", !dbg !57
  %".34" = lshr i64 %".33", 24, !dbg !57
  %".35" = and i64 %".34", 255, !dbg !57
  %".36" = trunc i64 %".35" to i8 , !dbg !57
  %".37" = call i64 @"fnv1a_byte"(i64 %".32", i8 %".36"), !dbg !57
  store i64 %".37", i64* %"r.addr", !dbg !57
  %".39" = load i64, i64* %"r.addr", !dbg !58
  %".40" = load i64, i64* %"v.addr", !dbg !58
  %".41" = lshr i64 %".40", 32, !dbg !58
  %".42" = and i64 %".41", 255, !dbg !58
  %".43" = trunc i64 %".42" to i8 , !dbg !58
  %".44" = call i64 @"fnv1a_byte"(i64 %".39", i8 %".43"), !dbg !58
  store i64 %".44", i64* %"r.addr", !dbg !58
  %".46" = load i64, i64* %"r.addr", !dbg !59
  %".47" = load i64, i64* %"v.addr", !dbg !59
  %".48" = lshr i64 %".47", 40, !dbg !59
  %".49" = and i64 %".48", 255, !dbg !59
  %".50" = trunc i64 %".49" to i8 , !dbg !59
  %".51" = call i64 @"fnv1a_byte"(i64 %".46", i8 %".50"), !dbg !59
  store i64 %".51", i64* %"r.addr", !dbg !59
  %".53" = load i64, i64* %"r.addr", !dbg !60
  %".54" = load i64, i64* %"v.addr", !dbg !60
  %".55" = lshr i64 %".54", 48, !dbg !60
  %".56" = and i64 %".55", 255, !dbg !60
  %".57" = trunc i64 %".56" to i8 , !dbg !60
  %".58" = call i64 @"fnv1a_byte"(i64 %".53", i8 %".57"), !dbg !60
  store i64 %".58", i64* %"r.addr", !dbg !60
  %".60" = load i64, i64* %"r.addr", !dbg !61
  %".61" = load i64, i64* %"v.addr", !dbg !61
  %".62" = lshr i64 %".61", 56, !dbg !61
  %".63" = and i64 %".62", 255, !dbg !61
  %".64" = trunc i64 %".63" to i8 , !dbg !61
  %".65" = call i64 @"fnv1a_byte"(i64 %".60", i8 %".64"), !dbg !61
  store i64 %".65", i64* %"r.addr", !dbg !61
  %".67" = load i64, i64* %"r.addr", !dbg !62
  ret i64 %".67", !dbg !62
}

define i64 @"fnv1a_u64"(i64 %"h.arg", i64 %"val.arg") !dbg !21
{
entry:
  %"h" = alloca i64
  %"r.addr" = alloca i64, !dbg !66
  store i64 %"h.arg", i64* %"h"
  call void @"llvm.dbg.declare"(metadata i64* %"h", metadata !63, metadata !7), !dbg !64
  %"val" = alloca i64
  store i64 %"val.arg", i64* %"val"
  call void @"llvm.dbg.declare"(metadata i64* %"val", metadata !65, metadata !7), !dbg !64
  %".8" = load i64, i64* %"h", !dbg !66
  %".9" = load i64, i64* %"val", !dbg !66
  %".10" = and i64 %".9", 255, !dbg !66
  %".11" = trunc i64 %".10" to i8 , !dbg !66
  %".12" = call i64 @"fnv1a_byte"(i64 %".8", i8 %".11"), !dbg !66
  store i64 %".12", i64* %"r.addr", !dbg !66
  call void @"llvm.dbg.declare"(metadata i64* %"r.addr", metadata !67, metadata !7), !dbg !68
  %".15" = load i64, i64* %"r.addr", !dbg !69
  %".16" = load i64, i64* %"val", !dbg !69
  %".17" = lshr i64 %".16", 8, !dbg !69
  %".18" = and i64 %".17", 255, !dbg !69
  %".19" = trunc i64 %".18" to i8 , !dbg !69
  %".20" = call i64 @"fnv1a_byte"(i64 %".15", i8 %".19"), !dbg !69
  store i64 %".20", i64* %"r.addr", !dbg !69
  %".22" = load i64, i64* %"r.addr", !dbg !70
  %".23" = load i64, i64* %"val", !dbg !70
  %".24" = lshr i64 %".23", 16, !dbg !70
  %".25" = and i64 %".24", 255, !dbg !70
  %".26" = trunc i64 %".25" to i8 , !dbg !70
  %".27" = call i64 @"fnv1a_byte"(i64 %".22", i8 %".26"), !dbg !70
  store i64 %".27", i64* %"r.addr", !dbg !70
  %".29" = load i64, i64* %"r.addr", !dbg !71
  %".30" = load i64, i64* %"val", !dbg !71
  %".31" = lshr i64 %".30", 24, !dbg !71
  %".32" = and i64 %".31", 255, !dbg !71
  %".33" = trunc i64 %".32" to i8 , !dbg !71
  %".34" = call i64 @"fnv1a_byte"(i64 %".29", i8 %".33"), !dbg !71
  store i64 %".34", i64* %"r.addr", !dbg !71
  %".36" = load i64, i64* %"r.addr", !dbg !72
  %".37" = load i64, i64* %"val", !dbg !72
  %".38" = lshr i64 %".37", 32, !dbg !72
  %".39" = and i64 %".38", 255, !dbg !72
  %".40" = trunc i64 %".39" to i8 , !dbg !72
  %".41" = call i64 @"fnv1a_byte"(i64 %".36", i8 %".40"), !dbg !72
  store i64 %".41", i64* %"r.addr", !dbg !72
  %".43" = load i64, i64* %"r.addr", !dbg !73
  %".44" = load i64, i64* %"val", !dbg !73
  %".45" = lshr i64 %".44", 40, !dbg !73
  %".46" = and i64 %".45", 255, !dbg !73
  %".47" = trunc i64 %".46" to i8 , !dbg !73
  %".48" = call i64 @"fnv1a_byte"(i64 %".43", i8 %".47"), !dbg !73
  store i64 %".48", i64* %"r.addr", !dbg !73
  %".50" = load i64, i64* %"r.addr", !dbg !74
  %".51" = load i64, i64* %"val", !dbg !74
  %".52" = lshr i64 %".51", 48, !dbg !74
  %".53" = and i64 %".52", 255, !dbg !74
  %".54" = trunc i64 %".53" to i8 , !dbg !74
  %".55" = call i64 @"fnv1a_byte"(i64 %".50", i8 %".54"), !dbg !74
  store i64 %".55", i64* %"r.addr", !dbg !74
  %".57" = load i64, i64* %"r.addr", !dbg !75
  %".58" = load i64, i64* %"val", !dbg !75
  %".59" = lshr i64 %".58", 56, !dbg !75
  %".60" = and i64 %".59", 255, !dbg !75
  %".61" = trunc i64 %".60" to i8 , !dbg !75
  %".62" = call i64 @"fnv1a_byte"(i64 %".57", i8 %".61"), !dbg !75
  store i64 %".62", i64* %"r.addr", !dbg !75
  %".64" = load i64, i64* %"r.addr", !dbg !76
  ret i64 %".64", !dbg !76
}

define i64 @"hash_i32"(i32 %"val.arg") !dbg !22
{
entry:
  %"val" = alloca i32
  store i32 %"val.arg", i32* %"val"
  call void @"llvm.dbg.declare"(metadata i32* %"val", metadata !77, metadata !7), !dbg !78
  %".5" = call i64 @"fnv1a_init"(), !dbg !79
  %".6" = load i32, i32* %"val", !dbg !79
  %".7" = call i64 @"fnv1a_i32"(i64 %".5", i32 %".6"), !dbg !79
  ret i64 %".7", !dbg !79
}

define i64 @"hash_i64"(i64 %"val.arg") !dbg !23
{
entry:
  %"val" = alloca i64
  store i64 %"val.arg", i64* %"val"
  call void @"llvm.dbg.declare"(metadata i64* %"val", metadata !80, metadata !7), !dbg !81
  %".5" = call i64 @"fnv1a_init"(), !dbg !82
  %".6" = load i64, i64* %"val", !dbg !82
  %".7" = call i64 @"fnv1a_i64"(i64 %".5", i64 %".6"), !dbg !82
  ret i64 %".7", !dbg !82
}

define i64 @"hash_u64"(i64 %"val.arg") !dbg !24
{
entry:
  %"val" = alloca i64
  store i64 %"val.arg", i64* %"val"
  call void @"llvm.dbg.declare"(metadata i64* %"val", metadata !83, metadata !7), !dbg !84
  %".5" = call i64 @"fnv1a_init"(), !dbg !85
  %".6" = load i64, i64* %"val", !dbg !85
  %".7" = call i64 @"fnv1a_u64"(i64 %".5", i64 %".6"), !dbg !85
  ret i64 %".7", !dbg !85
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/cryptosec/ritz/ritzlib", filename: "hash.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 19, name: "fnv1a_init", scopeLine: 19, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 22, name: "fnv1a_byte", scopeLine: 22, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 31, name: "fnv1a_i32", scopeLine: 31, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 40, name: "fnv1a_i64", scopeLine: 40, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 53, name: "fnv1a_u64", scopeLine: 53, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 69, name: "hash_i32", scopeLine: 69, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 72, name: "hash_i64", scopeLine: 72, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 75, name: "hash_u64", scopeLine: 75, type: !4, unit: !1)
!25 = !DILocation(column: 5, line: 20, scope: !17)
!26 = !DILocalVariable(file: !0, line: 22, name: "h", scope: !18, type: !15)
!27 = !DILocation(column: 1, line: 22, scope: !18)
!28 = !DILocalVariable(file: !0, line: 22, name: "b", scope: !18, type: !12)
!29 = !DILocation(column: 5, line: 24, scope: !18)
!30 = !DILocalVariable(file: !0, line: 24, name: "result", scope: !18, type: !15)
!31 = !DILocation(column: 1, line: 24, scope: !18)
!32 = !DILocation(column: 5, line: 25, scope: !18)
!33 = !DILocalVariable(file: !0, line: 31, name: "h", scope: !19, type: !15)
!34 = !DILocation(column: 1, line: 31, scope: !19)
!35 = !DILocalVariable(file: !0, line: 31, name: "val", scope: !19, type: !10)
!36 = !DILocation(column: 5, line: 33, scope: !19)
!37 = !DILocalVariable(file: !0, line: 33, name: "v", scope: !19, type: !15)
!38 = !DILocation(column: 1, line: 33, scope: !19)
!39 = !DILocation(column: 5, line: 34, scope: !19)
!40 = !DILocalVariable(file: !0, line: 34, name: "r", scope: !19, type: !15)
!41 = !DILocation(column: 1, line: 34, scope: !19)
!42 = !DILocation(column: 5, line: 35, scope: !19)
!43 = !DILocation(column: 5, line: 36, scope: !19)
!44 = !DILocation(column: 5, line: 37, scope: !19)
!45 = !DILocation(column: 5, line: 38, scope: !19)
!46 = !DILocalVariable(file: !0, line: 40, name: "h", scope: !20, type: !15)
!47 = !DILocation(column: 1, line: 40, scope: !20)
!48 = !DILocalVariable(file: !0, line: 40, name: "val", scope: !20, type: !11)
!49 = !DILocation(column: 5, line: 42, scope: !20)
!50 = !DILocalVariable(file: !0, line: 42, name: "v", scope: !20, type: !15)
!51 = !DILocation(column: 1, line: 42, scope: !20)
!52 = !DILocation(column: 5, line: 43, scope: !20)
!53 = !DILocalVariable(file: !0, line: 43, name: "r", scope: !20, type: !15)
!54 = !DILocation(column: 1, line: 43, scope: !20)
!55 = !DILocation(column: 5, line: 44, scope: !20)
!56 = !DILocation(column: 5, line: 45, scope: !20)
!57 = !DILocation(column: 5, line: 46, scope: !20)
!58 = !DILocation(column: 5, line: 47, scope: !20)
!59 = !DILocation(column: 5, line: 48, scope: !20)
!60 = !DILocation(column: 5, line: 49, scope: !20)
!61 = !DILocation(column: 5, line: 50, scope: !20)
!62 = !DILocation(column: 5, line: 51, scope: !20)
!63 = !DILocalVariable(file: !0, line: 53, name: "h", scope: !21, type: !15)
!64 = !DILocation(column: 1, line: 53, scope: !21)
!65 = !DILocalVariable(file: !0, line: 53, name: "val", scope: !21, type: !15)
!66 = !DILocation(column: 5, line: 55, scope: !21)
!67 = !DILocalVariable(file: !0, line: 55, name: "r", scope: !21, type: !15)
!68 = !DILocation(column: 1, line: 55, scope: !21)
!69 = !DILocation(column: 5, line: 56, scope: !21)
!70 = !DILocation(column: 5, line: 57, scope: !21)
!71 = !DILocation(column: 5, line: 58, scope: !21)
!72 = !DILocation(column: 5, line: 59, scope: !21)
!73 = !DILocation(column: 5, line: 60, scope: !21)
!74 = !DILocation(column: 5, line: 61, scope: !21)
!75 = !DILocation(column: 5, line: 62, scope: !21)
!76 = !DILocation(column: 5, line: 63, scope: !21)
!77 = !DILocalVariable(file: !0, line: 69, name: "val", scope: !22, type: !10)
!78 = !DILocation(column: 1, line: 69, scope: !22)
!79 = !DILocation(column: 5, line: 70, scope: !22)
!80 = !DILocalVariable(file: !0, line: 72, name: "val", scope: !23, type: !11)
!81 = !DILocation(column: 1, line: 72, scope: !23)
!82 = !DILocation(column: 5, line: 73, scope: !23)
!83 = !DILocalVariable(file: !0, line: 75, name: "val", scope: !24, type: !15)
!84 = !DILocation(column: 1, line: 75, scope: !24)
!85 = !DILocation(column: 5, line: 76, scope: !24)