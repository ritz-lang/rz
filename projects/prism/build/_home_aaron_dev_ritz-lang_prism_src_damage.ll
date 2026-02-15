; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Rect" = type {i32, i32, i32, i32}
%"struct.ritz_module_1.DamageRegion" = type {[16 x %"struct.ritz_module_1.Rect"], i32}
declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

define i32 @"min_i32"(i32 %"a.arg", i32 %"b.arg") !dbg !17
{
entry:
  %"a" = alloca i32
  store i32 %"a.arg", i32* %"a"
  call void @"llvm.dbg.declare"(metadata i32* %"a", metadata !33, metadata !7), !dbg !34
  %"b" = alloca i32
  store i32 %"b.arg", i32* %"b"
  call void @"llvm.dbg.declare"(metadata i32* %"b", metadata !35, metadata !7), !dbg !34
  %".8" = load i32, i32* %"a", !dbg !36
  %".9" = load i32, i32* %"b", !dbg !36
  %".10" = icmp slt i32 %".8", %".9" , !dbg !36
  br i1 %".10", label %"if.then", label %"if.end", !dbg !36
if.then:
  %".12" = load i32, i32* %"a", !dbg !37
  ret i32 %".12", !dbg !37
if.end:
  %".14" = load i32, i32* %"b", !dbg !38
  ret i32 %".14", !dbg !38
}

define i32 @"max_i32"(i32 %"a.arg", i32 %"b.arg") !dbg !18
{
entry:
  %"a" = alloca i32
  store i32 %"a.arg", i32* %"a"
  call void @"llvm.dbg.declare"(metadata i32* %"a", metadata !39, metadata !7), !dbg !40
  %"b" = alloca i32
  store i32 %"b.arg", i32* %"b"
  call void @"llvm.dbg.declare"(metadata i32* %"b", metadata !41, metadata !7), !dbg !40
  %".8" = load i32, i32* %"a", !dbg !42
  %".9" = load i32, i32* %"b", !dbg !42
  %".10" = icmp sgt i32 %".8", %".9" , !dbg !42
  br i1 %".10", label %"if.then", label %"if.end", !dbg !42
if.then:
  %".12" = load i32, i32* %"a", !dbg !43
  ret i32 %".12", !dbg !43
if.end:
  %".14" = load i32, i32* %"b", !dbg !44
  ret i32 %".14", !dbg !44
}

define %"struct.ritz_module_1.DamageRegion" @"damage_region_new"() !dbg !19
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !45
  %".3" = trunc i64 0 to i32 , !dbg !45
  %".4" = trunc i64 0 to i32 , !dbg !45
  %".5" = trunc i64 0 to i32 , !dbg !45
  %".6" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".2", 0 , !dbg !45
  %".7" = insertvalue %"struct.ritz_module_1.Rect" %".6", i32 %".3", 1 , !dbg !45
  %".8" = insertvalue %"struct.ritz_module_1.Rect" %".7", i32 %".4", 2 , !dbg !45
  %".9" = insertvalue %"struct.ritz_module_1.Rect" %".8", i32 %".5", 3 , !dbg !45
  %".10" = insertvalue [16 x %"struct.ritz_module_1.Rect"] undef, %"struct.ritz_module_1.Rect" %".9", 0 , !dbg !45
  %".11" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".10", %"struct.ritz_module_1.Rect" %".9", 1 , !dbg !45
  %".12" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".11", %"struct.ritz_module_1.Rect" %".9", 2 , !dbg !45
  %".13" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".12", %"struct.ritz_module_1.Rect" %".9", 3 , !dbg !45
  %".14" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".13", %"struct.ritz_module_1.Rect" %".9", 4 , !dbg !45
  %".15" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".14", %"struct.ritz_module_1.Rect" %".9", 5 , !dbg !45
  %".16" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".15", %"struct.ritz_module_1.Rect" %".9", 6 , !dbg !45
  %".17" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".16", %"struct.ritz_module_1.Rect" %".9", 7 , !dbg !45
  %".18" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".17", %"struct.ritz_module_1.Rect" %".9", 8 , !dbg !45
  %".19" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".18", %"struct.ritz_module_1.Rect" %".9", 9 , !dbg !45
  %".20" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".19", %"struct.ritz_module_1.Rect" %".9", 10 , !dbg !45
  %".21" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".20", %"struct.ritz_module_1.Rect" %".9", 11 , !dbg !45
  %".22" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".21", %"struct.ritz_module_1.Rect" %".9", 12 , !dbg !45
  %".23" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".22", %"struct.ritz_module_1.Rect" %".9", 13 , !dbg !45
  %".24" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".23", %"struct.ritz_module_1.Rect" %".9", 14 , !dbg !45
  %".25" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".24", %"struct.ritz_module_1.Rect" %".9", 15 , !dbg !45
  %".26" = trunc i64 0 to i32 , !dbg !45
  %".27" = insertvalue %"struct.ritz_module_1.DamageRegion" undef, [16 x %"struct.ritz_module_1.Rect"] %".25", 0 , !dbg !45
  %".28" = insertvalue %"struct.ritz_module_1.DamageRegion" %".27", i32 %".26", 1 , !dbg !45
  ret %"struct.ritz_module_1.DamageRegion" %".28", !dbg !45
}

define i32 @"damage_region_add"(%"struct.ritz_module_1.DamageRegion"* %"region.arg", %"struct.ritz_module_1.Rect" %"r.arg") !dbg !20
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.DamageRegion"* %"region.arg", metadata !47, metadata !7), !dbg !48
  %"r" = alloca %"struct.ritz_module_1.Rect"
  store %"struct.ritz_module_1.Rect" %"r.arg", %"struct.ritz_module_1.Rect"* %"r"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"r", metadata !50, metadata !7), !dbg !48
  %".7" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !51
  %".8" = load i32, i32* %".7", !dbg !51
  %".9" = zext i32 %".8" to i64 , !dbg !51
  %".10" = icmp ult i64 %".9", 16 , !dbg !51
  br i1 %".10", label %"if.then", label %"if.end", !dbg !51
if.then:
  %".12" = load %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"r", !dbg !52
  %".13" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !52
  %".14" = load i32, i32* %".13", !dbg !52
  %".15" = zext i32 %".14" to i64 , !dbg !52
  %".16" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 0 , !dbg !52
  %".17" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".16", i32 0, i64 %".15" , !dbg !52
  store %"struct.ritz_module_1.Rect" %".12", %"struct.ritz_module_1.Rect"* %".17", !dbg !52
  %".19" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !53
  %".20" = load i32, i32* %".19", !dbg !53
  %".21" = zext i32 %".20" to i64 , !dbg !53
  %".22" = add i64 %".21", 1, !dbg !53
  %".23" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", !dbg !53
  %".24" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !53
  %".25" = trunc i64 %".22" to i32 , !dbg !53
  store i32 %".25", i32* %".24", !dbg !53
  br label %"if.end", !dbg !53
if.end:
  ret i32 0, !dbg !53
}

define i32 @"damage_region_clear"(%"struct.ritz_module_1.DamageRegion"* %"region.arg") !dbg !21
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.DamageRegion"* %"region.arg", metadata !54, metadata !7), !dbg !55
  %".4" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", !dbg !56
  %".5" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !56
  %".6" = trunc i64 0 to i32 , !dbg !56
  store i32 %".6", i32* %".5", !dbg !56
  ret i32 0, !dbg !56
}

define i1 @"damage_region_is_empty"(%"struct.ritz_module_1.DamageRegion"* %"region.arg") !dbg !22
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.DamageRegion"* %"region.arg", metadata !58, metadata !7), !dbg !59
  %".4" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !60
  %".5" = load i32, i32* %".4", !dbg !60
  %".6" = sext i32 %".5" to i64 , !dbg !60
  %".7" = icmp eq i64 %".6", 0 , !dbg !60
  ret i1 %".7", !dbg !60
}

define i32 @"damage_region_count"(%"struct.ritz_module_1.DamageRegion"* %"region.arg") !dbg !23
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.DamageRegion"* %"region.arg", metadata !61, metadata !7), !dbg !62
  %".4" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !63
  %".5" = load i32, i32* %".4", !dbg !63
  ret i32 %".5", !dbg !63
}

define %"struct.ritz_module_1.Rect" @"rect_new"(i32 %"x.arg", i32 %"y.arg", i32 %"width.arg", i32 %"height.arg") !dbg !24
{
entry:
  %"x" = alloca i32
  store i32 %"x.arg", i32* %"x"
  call void @"llvm.dbg.declare"(metadata i32* %"x", metadata !64, metadata !7), !dbg !65
  %"y" = alloca i32
  store i32 %"y.arg", i32* %"y"
  call void @"llvm.dbg.declare"(metadata i32* %"y", metadata !66, metadata !7), !dbg !65
  %"width" = alloca i32
  store i32 %"width.arg", i32* %"width"
  call void @"llvm.dbg.declare"(metadata i32* %"width", metadata !67, metadata !7), !dbg !65
  %"height" = alloca i32
  store i32 %"height.arg", i32* %"height"
  call void @"llvm.dbg.declare"(metadata i32* %"height", metadata !68, metadata !7), !dbg !65
  %".14" = load i32, i32* %"x", !dbg !69
  %".15" = load i32, i32* %"y", !dbg !69
  %".16" = load i32, i32* %"width", !dbg !69
  %".17" = load i32, i32* %"height", !dbg !69
  %".18" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".14", 0 , !dbg !69
  %".19" = insertvalue %"struct.ritz_module_1.Rect" %".18", i32 %".15", 1 , !dbg !69
  %".20" = insertvalue %"struct.ritz_module_1.Rect" %".19", i32 %".16", 2 , !dbg !69
  %".21" = insertvalue %"struct.ritz_module_1.Rect" %".20", i32 %".17", 3 , !dbg !69
  ret %"struct.ritz_module_1.Rect" %".21", !dbg !69
}

define %"struct.ritz_module_1.Rect" @"rect_zero"() !dbg !25
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !70
  %".3" = trunc i64 0 to i32 , !dbg !70
  %".4" = trunc i64 0 to i32 , !dbg !70
  %".5" = trunc i64 0 to i32 , !dbg !70
  %".6" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".2", 0 , !dbg !70
  %".7" = insertvalue %"struct.ritz_module_1.Rect" %".6", i32 %".3", 1 , !dbg !70
  %".8" = insertvalue %"struct.ritz_module_1.Rect" %".7", i32 %".4", 2 , !dbg !70
  %".9" = insertvalue %"struct.ritz_module_1.Rect" %".8", i32 %".5", 3 , !dbg !70
  ret %"struct.ritz_module_1.Rect" %".9", !dbg !70
}

define i1 @"rects_intersect"(%"struct.ritz_module_1.Rect"* %"a.arg", %"struct.ritz_module_1.Rect"* %"b.arg") !dbg !26
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"a.arg", metadata !72, metadata !7), !dbg !73
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"b.arg", metadata !74, metadata !7), !dbg !73
  %".6" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 0 , !dbg !75
  %".7" = load i32, i32* %".6", !dbg !75
  %".8" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 2 , !dbg !75
  %".9" = load i32, i32* %".8", !dbg !75
  %".10" = add i32 %".7", %".9", !dbg !75
  %".11" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 1 , !dbg !76
  %".12" = load i32, i32* %".11", !dbg !76
  %".13" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 3 , !dbg !76
  %".14" = load i32, i32* %".13", !dbg !76
  %".15" = add i32 %".12", %".14", !dbg !76
  %".16" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 0 , !dbg !77
  %".17" = load i32, i32* %".16", !dbg !77
  %".18" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 2 , !dbg !77
  %".19" = load i32, i32* %".18", !dbg !77
  %".20" = add i32 %".17", %".19", !dbg !77
  %".21" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 1 , !dbg !78
  %".22" = load i32, i32* %".21", !dbg !78
  %".23" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 3 , !dbg !78
  %".24" = load i32, i32* %".23", !dbg !78
  %".25" = add i32 %".22", %".24", !dbg !78
  %".26" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 0 , !dbg !79
  %".27" = load i32, i32* %".26", !dbg !79
  %".28" = icmp slt i32 %".27", %".20" , !dbg !79
  br i1 %".28", label %"and.right", label %"and.merge", !dbg !79
and.right:
  %".30" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 0 , !dbg !79
  %".31" = load i32, i32* %".30", !dbg !79
  %".32" = icmp sgt i32 %".10", %".31" , !dbg !79
  br label %"and.merge", !dbg !79
and.merge:
  %".34" = phi  i1 [0, %"entry"], [%".32", %"and.right"] , !dbg !79
  br i1 %".34", label %"and.right.1", label %"and.merge.1", !dbg !79
and.right.1:
  %".36" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 1 , !dbg !79
  %".37" = load i32, i32* %".36", !dbg !79
  %".38" = icmp slt i32 %".37", %".25" , !dbg !79
  br label %"and.merge.1", !dbg !79
and.merge.1:
  %".40" = phi  i1 [0, %"and.merge"], [%".38", %"and.right.1"] , !dbg !79
  br i1 %".40", label %"and.right.2", label %"and.merge.2", !dbg !79
and.right.2:
  %".42" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 1 , !dbg !79
  %".43" = load i32, i32* %".42", !dbg !79
  %".44" = icmp sgt i32 %".15", %".43" , !dbg !79
  br label %"and.merge.2", !dbg !79
and.merge.2:
  %".46" = phi  i1 [0, %"and.merge.1"], [%".44", %"and.right.2"] , !dbg !79
  ret i1 %".46", !dbg !79
}

define %"struct.ritz_module_1.Rect" @"rect_union"(%"struct.ritz_module_1.Rect"* %"a.arg", %"struct.ritz_module_1.Rect"* %"b.arg") !dbg !27
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"a.arg", metadata !80, metadata !7), !dbg !81
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"b.arg", metadata !82, metadata !7), !dbg !81
  %".6" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 0 , !dbg !83
  %".7" = load i32, i32* %".6", !dbg !83
  %".8" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 0 , !dbg !83
  %".9" = load i32, i32* %".8", !dbg !83
  %".10" = call i32 @"min_i32"(i32 %".7", i32 %".9"), !dbg !83
  %".11" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 1 , !dbg !84
  %".12" = load i32, i32* %".11", !dbg !84
  %".13" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 1 , !dbg !84
  %".14" = load i32, i32* %".13", !dbg !84
  %".15" = call i32 @"min_i32"(i32 %".12", i32 %".14"), !dbg !84
  %".16" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 0 , !dbg !85
  %".17" = load i32, i32* %".16", !dbg !85
  %".18" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 2 , !dbg !85
  %".19" = load i32, i32* %".18", !dbg !85
  %".20" = add i32 %".17", %".19", !dbg !85
  %".21" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 0 , !dbg !86
  %".22" = load i32, i32* %".21", !dbg !86
  %".23" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 2 , !dbg !86
  %".24" = load i32, i32* %".23", !dbg !86
  %".25" = add i32 %".22", %".24", !dbg !86
  %".26" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 1 , !dbg !87
  %".27" = load i32, i32* %".26", !dbg !87
  %".28" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 3 , !dbg !87
  %".29" = load i32, i32* %".28", !dbg !87
  %".30" = add i32 %".27", %".29", !dbg !87
  %".31" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 1 , !dbg !88
  %".32" = load i32, i32* %".31", !dbg !88
  %".33" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 3 , !dbg !88
  %".34" = load i32, i32* %".33", !dbg !88
  %".35" = add i32 %".32", %".34", !dbg !88
  %".36" = call i32 @"max_i32"(i32 %".20", i32 %".25"), !dbg !89
  %".37" = call i32 @"max_i32"(i32 %".30", i32 %".35"), !dbg !90
  %".38" = sub i32 %".36", %".10", !dbg !91
  %".39" = sub i32 %".37", %".15", !dbg !91
  %".40" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".10", 0 , !dbg !91
  %".41" = insertvalue %"struct.ritz_module_1.Rect" %".40", i32 %".15", 1 , !dbg !91
  %".42" = insertvalue %"struct.ritz_module_1.Rect" %".41", i32 %".38", 2 , !dbg !91
  %".43" = insertvalue %"struct.ritz_module_1.Rect" %".42", i32 %".39", 3 , !dbg !91
  ret %"struct.ritz_module_1.Rect" %".43", !dbg !91
}

define %"struct.ritz_module_1.Rect" @"rect_intersection"(%"struct.ritz_module_1.Rect"* %"a.arg", %"struct.ritz_module_1.Rect"* %"b.arg") !dbg !28
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"a.arg", metadata !92, metadata !7), !dbg !93
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"b.arg", metadata !94, metadata !7), !dbg !93
  %".6" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 0 , !dbg !95
  %".7" = load i32, i32* %".6", !dbg !95
  %".8" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 2 , !dbg !95
  %".9" = load i32, i32* %".8", !dbg !95
  %".10" = add i32 %".7", %".9", !dbg !95
  %".11" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 1 , !dbg !96
  %".12" = load i32, i32* %".11", !dbg !96
  %".13" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 3 , !dbg !96
  %".14" = load i32, i32* %".13", !dbg !96
  %".15" = add i32 %".12", %".14", !dbg !96
  %".16" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 0 , !dbg !97
  %".17" = load i32, i32* %".16", !dbg !97
  %".18" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 2 , !dbg !97
  %".19" = load i32, i32* %".18", !dbg !97
  %".20" = add i32 %".17", %".19", !dbg !97
  %".21" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 1 , !dbg !98
  %".22" = load i32, i32* %".21", !dbg !98
  %".23" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 3 , !dbg !98
  %".24" = load i32, i32* %".23", !dbg !98
  %".25" = add i32 %".22", %".24", !dbg !98
  %".26" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 0 , !dbg !99
  %".27" = load i32, i32* %".26", !dbg !99
  %".28" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 0 , !dbg !99
  %".29" = load i32, i32* %".28", !dbg !99
  %".30" = call i32 @"max_i32"(i32 %".27", i32 %".29"), !dbg !99
  %".31" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 1 , !dbg !100
  %".32" = load i32, i32* %".31", !dbg !100
  %".33" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 1 , !dbg !100
  %".34" = load i32, i32* %".33", !dbg !100
  %".35" = call i32 @"max_i32"(i32 %".32", i32 %".34"), !dbg !100
  %".36" = call i32 @"min_i32"(i32 %".10", i32 %".20"), !dbg !101
  %".37" = call i32 @"min_i32"(i32 %".15", i32 %".25"), !dbg !102
  %".38" = icmp sgt i32 %".36", %".30" , !dbg !103
  br i1 %".38", label %"and.right", label %"and.merge", !dbg !103
and.right:
  %".40" = icmp sgt i32 %".37", %".35" , !dbg !103
  br label %"and.merge", !dbg !103
and.merge:
  %".42" = phi  i1 [0, %"entry"], [%".40", %"and.right"] , !dbg !103
  br i1 %".42", label %"if.then", label %"if.else", !dbg !103
if.then:
  %".44" = sub i32 %".36", %".30", !dbg !103
  %".45" = sub i32 %".37", %".35", !dbg !103
  %".46" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".30", 0 , !dbg !103
  %".47" = insertvalue %"struct.ritz_module_1.Rect" %".46", i32 %".35", 1 , !dbg !103
  %".48" = insertvalue %"struct.ritz_module_1.Rect" %".47", i32 %".44", 2 , !dbg !103
  %".49" = insertvalue %"struct.ritz_module_1.Rect" %".48", i32 %".45", 3 , !dbg !103
  br label %"if.end", !dbg !103
if.else:
  %".50" = call %"struct.ritz_module_1.Rect" @"rect_zero"(), !dbg !103
  br label %"if.end", !dbg !103
if.end:
  %".53" = phi  %"struct.ritz_module_1.Rect" [%".49", %"if.then"], [%".50", %"if.else"] , !dbg !103
  ret %"struct.ritz_module_1.Rect" %".53", !dbg !103
}

define i1 @"rect_contains_point"(%"struct.ritz_module_1.Rect"* %"r.arg", i32 %"x.arg", i32 %"y.arg") !dbg !29
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"r.arg", metadata !104, metadata !7), !dbg !105
  %"x" = alloca i32
  store i32 %"x.arg", i32* %"x"
  call void @"llvm.dbg.declare"(metadata i32* %"x", metadata !106, metadata !7), !dbg !105
  %"y" = alloca i32
  store i32 %"y.arg", i32* %"y"
  call void @"llvm.dbg.declare"(metadata i32* %"y", metadata !107, metadata !7), !dbg !105
  %".10" = load i32, i32* %"x", !dbg !108
  %".11" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"r.arg", i32 0, i32 0 , !dbg !108
  %".12" = load i32, i32* %".11", !dbg !108
  %".13" = icmp sge i32 %".10", %".12" , !dbg !108
  br i1 %".13", label %"and.right", label %"and.merge", !dbg !108
and.right:
  %".15" = load i32, i32* %"x", !dbg !108
  %".16" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"r.arg", i32 0, i32 0 , !dbg !108
  %".17" = load i32, i32* %".16", !dbg !108
  %".18" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"r.arg", i32 0, i32 2 , !dbg !108
  %".19" = load i32, i32* %".18", !dbg !108
  %".20" = add i32 %".17", %".19", !dbg !108
  %".21" = icmp slt i32 %".15", %".20" , !dbg !108
  br label %"and.merge", !dbg !108
and.merge:
  %".23" = phi  i1 [0, %"entry"], [%".21", %"and.right"] , !dbg !108
  br i1 %".23", label %"and.right.1", label %"and.merge.1", !dbg !108
and.right.1:
  %".25" = load i32, i32* %"y", !dbg !108
  %".26" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"r.arg", i32 0, i32 1 , !dbg !108
  %".27" = load i32, i32* %".26", !dbg !108
  %".28" = icmp sge i32 %".25", %".27" , !dbg !108
  br label %"and.merge.1", !dbg !108
and.merge.1:
  %".30" = phi  i1 [0, %"and.merge"], [%".28", %"and.right.1"] , !dbg !108
  br i1 %".30", label %"and.right.2", label %"and.merge.2", !dbg !108
and.right.2:
  %".32" = load i32, i32* %"y", !dbg !108
  %".33" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"r.arg", i32 0, i32 1 , !dbg !108
  %".34" = load i32, i32* %".33", !dbg !108
  %".35" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"r.arg", i32 0, i32 3 , !dbg !108
  %".36" = load i32, i32* %".35", !dbg !108
  %".37" = add i32 %".34", %".36", !dbg !108
  %".38" = icmp slt i32 %".32", %".37" , !dbg !108
  br label %"and.merge.2", !dbg !108
and.merge.2:
  %".40" = phi  i1 [0, %"and.merge.1"], [%".38", %"and.right.2"] , !dbg !108
  ret i1 %".40", !dbg !108
}

define i32 @"rect_area"(%"struct.ritz_module_1.Rect"* %"r.arg") !dbg !30
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"r.arg", metadata !109, metadata !7), !dbg !110
  %".4" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"r.arg", i32 0, i32 2 , !dbg !111
  %".5" = load i32, i32* %".4", !dbg !111
  %".6" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"r.arg", i32 0, i32 3 , !dbg !111
  %".7" = load i32, i32* %".6", !dbg !111
  %".8" = mul i32 %".5", %".7", !dbg !111
  ret i32 %".8", !dbg !111
}

define i1 @"rect_is_empty"(%"struct.ritz_module_1.Rect"* %"r.arg") !dbg !31
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"r.arg", metadata !112, metadata !7), !dbg !113
  %".4" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"r.arg", i32 0, i32 2 , !dbg !114
  %".5" = load i32, i32* %".4", !dbg !114
  %".6" = sext i32 %".5" to i64 , !dbg !114
  %".7" = icmp eq i64 %".6", 0 , !dbg !114
  br i1 %".7", label %"or.merge", label %"or.right", !dbg !114
or.right:
  %".9" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"r.arg", i32 0, i32 3 , !dbg !114
  %".10" = load i32, i32* %".9", !dbg !114
  %".11" = sext i32 %".10" to i64 , !dbg !114
  %".12" = icmp eq i64 %".11", 0 , !dbg !114
  br label %"or.merge", !dbg !114
or.merge:
  %".14" = phi  i1 [1, %"entry"], [%".12", %"or.right"] , !dbg !114
  ret i1 %".14", !dbg !114
}

define %"struct.ritz_module_1.Rect" @"damage_region_bounds"(%"struct.ritz_module_1.DamageRegion"* %"region.arg") !dbg !32
{
entry:
  %"bounds.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !119
  %"i.addr" = alloca i32, !dbg !120
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.DamageRegion"* %"region.arg", metadata !115, metadata !7), !dbg !116
  %".4" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !117
  %".5" = load i32, i32* %".4", !dbg !117
  %".6" = sext i32 %".5" to i64 , !dbg !117
  %".7" = icmp eq i64 %".6", 0 , !dbg !117
  br i1 %".7", label %"if.then", label %"if.end", !dbg !117
if.then:
  %".9" = call %"struct.ritz_module_1.Rect" @"rect_zero"(), !dbg !118
  ret %"struct.ritz_module_1.Rect" %".9", !dbg !118
if.end:
  %".11" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 0 , !dbg !119
  %".12" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".11", i32 0, i64 0 , !dbg !119
  %".13" = load %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %".12", !dbg !119
  store %"struct.ritz_module_1.Rect" %".13", %"struct.ritz_module_1.Rect"* %"bounds.addr", !dbg !119
  %".15" = trunc i64 1 to i32 , !dbg !120
  store i32 %".15", i32* %"i.addr", !dbg !120
  call void @"llvm.dbg.declare"(metadata i32* %"i.addr", metadata !121, metadata !7), !dbg !122
  br label %"while.cond", !dbg !123
while.cond:
  %".19" = load i32, i32* %"i.addr", !dbg !123
  %".20" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !123
  %".21" = load i32, i32* %".20", !dbg !123
  %".22" = icmp ult i32 %".19", %".21" , !dbg !123
  br i1 %".22", label %"while.body", label %"while.end", !dbg !123
while.body:
  %".24" = load i32, i32* %"i.addr", !dbg !124
  %".25" = zext i32 %".24" to i64 , !dbg !124
  %".26" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 0 , !dbg !124
  %".27" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".26", i32 0, i64 %".25" , !dbg !124
  %".28" = call %"struct.ritz_module_1.Rect" @"rect_union"(%"struct.ritz_module_1.Rect"* %"bounds.addr", %"struct.ritz_module_1.Rect"* %".27"), !dbg !124
  store %"struct.ritz_module_1.Rect" %".28", %"struct.ritz_module_1.Rect"* %"bounds.addr", !dbg !124
  %".30" = load i32, i32* %"i.addr", !dbg !125
  %".31" = zext i32 %".30" to i64 , !dbg !125
  %".32" = add i64 %".31", 1, !dbg !125
  %".33" = trunc i64 %".32" to i32 , !dbg !125
  store i32 %".33", i32* %"i.addr", !dbg !125
  br label %"while.cond", !dbg !125
while.end:
  %".36" = load %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"bounds.addr", !dbg !126
  ret %"struct.ritz_module_1.Rect" %".36", !dbg !126
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/prism/src", filename: "damage.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 24, name: "min_i32", scopeLine: 24, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 29, name: "max_i32", scopeLine: 29, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 38, name: "damage_region_new", scopeLine: 38, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 44, name: "damage_region_add", scopeLine: 44, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 49, name: "damage_region_clear", scopeLine: 49, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 52, name: "damage_region_is_empty", scopeLine: 52, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 55, name: "damage_region_count", scopeLine: 55, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 62, name: "rect_new", scopeLine: 62, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 65, name: "rect_zero", scopeLine: 65, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 68, name: "rects_intersect", scopeLine: 68, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 77, name: "rect_union", scopeLine: 77, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 94, name: "rect_intersection", scopeLine: 94, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 115, name: "rect_contains_point", scopeLine: 115, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 118, name: "rect_area", scopeLine: 118, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 121, name: "rect_is_empty", scopeLine: 121, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 128, name: "damage_region_bounds", scopeLine: 128, type: !4, unit: !1)
!33 = !DILocalVariable(file: !0, line: 24, name: "a", scope: !17, type: !10)
!34 = !DILocation(column: 1, line: 24, scope: !17)
!35 = !DILocalVariable(file: !0, line: 24, name: "b", scope: !17, type: !10)
!36 = !DILocation(column: 5, line: 25, scope: !17)
!37 = !DILocation(column: 9, line: 26, scope: !17)
!38 = !DILocation(column: 5, line: 27, scope: !17)
!39 = !DILocalVariable(file: !0, line: 29, name: "a", scope: !18, type: !10)
!40 = !DILocation(column: 1, line: 29, scope: !18)
!41 = !DILocalVariable(file: !0, line: 29, name: "b", scope: !18, type: !10)
!42 = !DILocation(column: 5, line: 30, scope: !18)
!43 = !DILocation(column: 9, line: 31, scope: !18)
!44 = !DILocation(column: 5, line: 32, scope: !18)
!45 = !DILocation(column: 5, line: 39, scope: !19)
!46 = !DICompositeType(align: 32, file: !0, name: "DamageRegion", size: 2080, tag: DW_TAG_structure_type)
!47 = !DILocalVariable(file: !0, line: 44, name: "region", scope: !20, type: !46)
!48 = !DILocation(column: 1, line: 44, scope: !20)
!49 = !DICompositeType(align: 32, file: !0, name: "Rect", size: 128, tag: DW_TAG_structure_type)
!50 = !DILocalVariable(file: !0, line: 44, name: "r", scope: !20, type: !49)
!51 = !DILocation(column: 5, line: 45, scope: !20)
!52 = !DILocation(column: 9, line: 46, scope: !20)
!53 = !DILocation(column: 9, line: 47, scope: !20)
!54 = !DILocalVariable(file: !0, line: 49, name: "region", scope: !21, type: !46)
!55 = !DILocation(column: 1, line: 49, scope: !21)
!56 = !DILocation(column: 5, line: 50, scope: !21)
!57 = !DIDerivedType(baseType: !46, size: 64, tag: DW_TAG_reference_type)
!58 = !DILocalVariable(file: !0, line: 52, name: "region", scope: !22, type: !57)
!59 = !DILocation(column: 1, line: 52, scope: !22)
!60 = !DILocation(column: 5, line: 53, scope: !22)
!61 = !DILocalVariable(file: !0, line: 55, name: "region", scope: !23, type: !57)
!62 = !DILocation(column: 1, line: 55, scope: !23)
!63 = !DILocation(column: 5, line: 56, scope: !23)
!64 = !DILocalVariable(file: !0, line: 62, name: "x", scope: !24, type: !10)
!65 = !DILocation(column: 1, line: 62, scope: !24)
!66 = !DILocalVariable(file: !0, line: 62, name: "y", scope: !24, type: !10)
!67 = !DILocalVariable(file: !0, line: 62, name: "width", scope: !24, type: !14)
!68 = !DILocalVariable(file: !0, line: 62, name: "height", scope: !24, type: !14)
!69 = !DILocation(column: 5, line: 63, scope: !24)
!70 = !DILocation(column: 5, line: 66, scope: !25)
!71 = !DIDerivedType(baseType: !49, size: 64, tag: DW_TAG_reference_type)
!72 = !DILocalVariable(file: !0, line: 68, name: "a", scope: !26, type: !71)
!73 = !DILocation(column: 1, line: 68, scope: !26)
!74 = !DILocalVariable(file: !0, line: 68, name: "b", scope: !26, type: !71)
!75 = !DILocation(column: 5, line: 70, scope: !26)
!76 = !DILocation(column: 5, line: 71, scope: !26)
!77 = !DILocation(column: 5, line: 72, scope: !26)
!78 = !DILocation(column: 5, line: 73, scope: !26)
!79 = !DILocation(column: 5, line: 75, scope: !26)
!80 = !DILocalVariable(file: !0, line: 77, name: "a", scope: !27, type: !71)
!81 = !DILocation(column: 1, line: 77, scope: !27)
!82 = !DILocalVariable(file: !0, line: 77, name: "b", scope: !27, type: !71)
!83 = !DILocation(column: 5, line: 78, scope: !27)
!84 = !DILocation(column: 5, line: 79, scope: !27)
!85 = !DILocation(column: 5, line: 80, scope: !27)
!86 = !DILocation(column: 5, line: 81, scope: !27)
!87 = !DILocation(column: 5, line: 82, scope: !27)
!88 = !DILocation(column: 5, line: 83, scope: !27)
!89 = !DILocation(column: 5, line: 84, scope: !27)
!90 = !DILocation(column: 5, line: 85, scope: !27)
!91 = !DILocation(column: 5, line: 87, scope: !27)
!92 = !DILocalVariable(file: !0, line: 94, name: "a", scope: !28, type: !71)
!93 = !DILocation(column: 1, line: 94, scope: !28)
!94 = !DILocalVariable(file: !0, line: 94, name: "b", scope: !28, type: !71)
!95 = !DILocation(column: 5, line: 95, scope: !28)
!96 = !DILocation(column: 5, line: 96, scope: !28)
!97 = !DILocation(column: 5, line: 97, scope: !28)
!98 = !DILocation(column: 5, line: 98, scope: !28)
!99 = !DILocation(column: 5, line: 100, scope: !28)
!100 = !DILocation(column: 5, line: 101, scope: !28)
!101 = !DILocation(column: 5, line: 102, scope: !28)
!102 = !DILocation(column: 5, line: 103, scope: !28)
!103 = !DILocation(column: 5, line: 105, scope: !28)
!104 = !DILocalVariable(file: !0, line: 115, name: "r", scope: !29, type: !71)
!105 = !DILocation(column: 1, line: 115, scope: !29)
!106 = !DILocalVariable(file: !0, line: 115, name: "x", scope: !29, type: !10)
!107 = !DILocalVariable(file: !0, line: 115, name: "y", scope: !29, type: !10)
!108 = !DILocation(column: 5, line: 116, scope: !29)
!109 = !DILocalVariable(file: !0, line: 118, name: "r", scope: !30, type: !71)
!110 = !DILocation(column: 1, line: 118, scope: !30)
!111 = !DILocation(column: 5, line: 119, scope: !30)
!112 = !DILocalVariable(file: !0, line: 121, name: "r", scope: !31, type: !71)
!113 = !DILocation(column: 1, line: 121, scope: !31)
!114 = !DILocation(column: 5, line: 122, scope: !31)
!115 = !DILocalVariable(file: !0, line: 128, name: "region", scope: !32, type: !57)
!116 = !DILocation(column: 1, line: 128, scope: !32)
!117 = !DILocation(column: 5, line: 129, scope: !32)
!118 = !DILocation(column: 9, line: 130, scope: !32)
!119 = !DILocation(column: 5, line: 132, scope: !32)
!120 = !DILocation(column: 5, line: 133, scope: !32)
!121 = !DILocalVariable(file: !0, line: 133, name: "i", scope: !32, type: !14)
!122 = !DILocation(column: 1, line: 133, scope: !32)
!123 = !DILocation(column: 5, line: 134, scope: !32)
!124 = !DILocation(column: 9, line: 135, scope: !32)
!125 = !DILocation(column: 9, line: 136, scope: !32)
!126 = !DILocation(column: 5, line: 137, scope: !32)