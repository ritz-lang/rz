; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

define i64 @"strlen"(i8* %"s.arg") !dbg !17
{
entry:
  %"s" = alloca i8*
  %"len.addr" = alloca i64, !dbg !43
  store i8* %"s.arg", i8** %"s"
  call void @"llvm.dbg.declare"(metadata i8** %"s", metadata !41, metadata !7), !dbg !42
  store i64 0, i64* %"len.addr", !dbg !43
  call void @"llvm.dbg.declare"(metadata i64* %"len.addr", metadata !44, metadata !7), !dbg !45
  br label %"while.cond", !dbg !46
while.cond:
  %".8" = load i8*, i8** %"s", !dbg !46
  %".9" = load i64, i64* %"len.addr", !dbg !46
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !46
  %".11" = load i8, i8* %".10", !dbg !46
  %".12" = zext i8 %".11" to i64 , !dbg !46
  %".13" = icmp ne i64 %".12", 0 , !dbg !46
  br i1 %".13", label %"while.body", label %"while.end", !dbg !46
while.body:
  %".15" = load i64, i64* %"len.addr", !dbg !47
  %".16" = add i64 %".15", 1, !dbg !47
  store i64 %".16", i64* %"len.addr", !dbg !47
  br label %"while.cond", !dbg !47
while.end:
  %".19" = load i64, i64* %"len.addr", !dbg !48
  ret i64 %".19", !dbg !48
}

define i32 @"streq"(i8* %"a.arg", i8* %"b.arg") !dbg !18
{
entry:
  %"a" = alloca i8*
  %"i.addr" = alloca i64, !dbg !52
  store i8* %"a.arg", i8** %"a"
  call void @"llvm.dbg.declare"(metadata i8** %"a", metadata !49, metadata !7), !dbg !50
  %"b" = alloca i8*
  store i8* %"b.arg", i8** %"b"
  call void @"llvm.dbg.declare"(metadata i8** %"b", metadata !51, metadata !7), !dbg !50
  store i64 0, i64* %"i.addr", !dbg !52
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !53, metadata !7), !dbg !54
  br label %"while.cond", !dbg !55
while.cond:
  %".11" = load i8*, i8** %"a", !dbg !55
  %".12" = load i64, i64* %"i.addr", !dbg !55
  %".13" = getelementptr i8, i8* %".11", i64 %".12" , !dbg !55
  %".14" = load i8, i8* %".13", !dbg !55
  %".15" = zext i8 %".14" to i64 , !dbg !55
  %".16" = icmp ne i64 %".15", 0 , !dbg !55
  br i1 %".16", label %"and.right", label %"and.merge", !dbg !55
while.body:
  %".27" = load i8*, i8** %"a", !dbg !56
  %".28" = load i64, i64* %"i.addr", !dbg !56
  %".29" = getelementptr i8, i8* %".27", i64 %".28" , !dbg !56
  %".30" = load i8, i8* %".29", !dbg !56
  %".31" = load i8*, i8** %"b", !dbg !56
  %".32" = load i64, i64* %"i.addr", !dbg !56
  %".33" = getelementptr i8, i8* %".31", i64 %".32" , !dbg !56
  %".34" = load i8, i8* %".33", !dbg !56
  %".35" = icmp ne i8 %".30", %".34" , !dbg !56
  br i1 %".35", label %"if.then", label %"if.end", !dbg !56
while.end:
  %".43" = load i8*, i8** %"a", !dbg !59
  %".44" = load i64, i64* %"i.addr", !dbg !59
  %".45" = getelementptr i8, i8* %".43", i64 %".44" , !dbg !59
  %".46" = load i8, i8* %".45", !dbg !59
  %".47" = load i8*, i8** %"b", !dbg !59
  %".48" = load i64, i64* %"i.addr", !dbg !59
  %".49" = getelementptr i8, i8* %".47", i64 %".48" , !dbg !59
  %".50" = load i8, i8* %".49", !dbg !59
  %".51" = icmp eq i8 %".46", %".50" , !dbg !59
  %".52" = zext i1 %".51" to i32 , !dbg !59
  ret i32 %".52", !dbg !59
and.right:
  %".18" = load i8*, i8** %"b", !dbg !55
  %".19" = load i64, i64* %"i.addr", !dbg !55
  %".20" = getelementptr i8, i8* %".18", i64 %".19" , !dbg !55
  %".21" = load i8, i8* %".20", !dbg !55
  %".22" = zext i8 %".21" to i64 , !dbg !55
  %".23" = icmp ne i64 %".22", 0 , !dbg !55
  br label %"and.merge", !dbg !55
and.merge:
  %".25" = phi  i1 [0, %"while.cond"], [%".23", %"and.right"] , !dbg !55
  br i1 %".25", label %"while.body", label %"while.end", !dbg !55
if.then:
  %".37" = trunc i64 0 to i32 , !dbg !57
  ret i32 %".37", !dbg !57
if.end:
  %".39" = load i64, i64* %"i.addr", !dbg !58
  %".40" = add i64 %".39", 1, !dbg !58
  store i64 %".40", i64* %"i.addr", !dbg !58
  br label %"while.cond", !dbg !58
}

define i32 @"strneq"(i8* %"a.arg", i8* %"b.arg", i64 %"n.arg") !dbg !19
{
entry:
  %"a" = alloca i8*
  %"i.addr" = alloca i64, !dbg !64
  store i8* %"a.arg", i8** %"a"
  call void @"llvm.dbg.declare"(metadata i8** %"a", metadata !60, metadata !7), !dbg !61
  %"b" = alloca i8*
  store i8* %"b.arg", i8** %"b"
  call void @"llvm.dbg.declare"(metadata i8** %"b", metadata !62, metadata !7), !dbg !61
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !63, metadata !7), !dbg !61
  store i64 0, i64* %"i.addr", !dbg !64
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !65, metadata !7), !dbg !66
  br label %"while.cond", !dbg !67
while.cond:
  %".14" = load i64, i64* %"i.addr", !dbg !67
  %".15" = load i64, i64* %"n", !dbg !67
  %".16" = icmp slt i64 %".14", %".15" , !dbg !67
  br i1 %".16", label %"and.right", label %"and.merge", !dbg !67
while.body:
  %".36" = load i8*, i8** %"a", !dbg !68
  %".37" = load i64, i64* %"i.addr", !dbg !68
  %".38" = getelementptr i8, i8* %".36", i64 %".37" , !dbg !68
  %".39" = load i8, i8* %".38", !dbg !68
  %".40" = load i8*, i8** %"b", !dbg !68
  %".41" = load i64, i64* %"i.addr", !dbg !68
  %".42" = getelementptr i8, i8* %".40", i64 %".41" , !dbg !68
  %".43" = load i8, i8* %".42", !dbg !68
  %".44" = icmp ne i8 %".39", %".43" , !dbg !68
  br i1 %".44", label %"if.then", label %"if.end", !dbg !68
while.end:
  %".52" = load i64, i64* %"i.addr", !dbg !71
  %".53" = load i64, i64* %"n", !dbg !71
  %".54" = icmp eq i64 %".52", %".53" , !dbg !71
  br i1 %".54", label %"if.then.1", label %"if.end.1", !dbg !71
and.right:
  %".18" = load i8*, i8** %"a", !dbg !67
  %".19" = load i64, i64* %"i.addr", !dbg !67
  %".20" = getelementptr i8, i8* %".18", i64 %".19" , !dbg !67
  %".21" = load i8, i8* %".20", !dbg !67
  %".22" = zext i8 %".21" to i64 , !dbg !67
  %".23" = icmp ne i64 %".22", 0 , !dbg !67
  br label %"and.merge", !dbg !67
and.merge:
  %".25" = phi  i1 [0, %"while.cond"], [%".23", %"and.right"] , !dbg !67
  br i1 %".25", label %"and.right.1", label %"and.merge.1", !dbg !67
and.right.1:
  %".27" = load i8*, i8** %"b", !dbg !67
  %".28" = load i64, i64* %"i.addr", !dbg !67
  %".29" = getelementptr i8, i8* %".27", i64 %".28" , !dbg !67
  %".30" = load i8, i8* %".29", !dbg !67
  %".31" = zext i8 %".30" to i64 , !dbg !67
  %".32" = icmp ne i64 %".31", 0 , !dbg !67
  br label %"and.merge.1", !dbg !67
and.merge.1:
  %".34" = phi  i1 [0, %"and.merge"], [%".32", %"and.right.1"] , !dbg !67
  br i1 %".34", label %"while.body", label %"while.end", !dbg !67
if.then:
  %".46" = trunc i64 0 to i32 , !dbg !69
  ret i32 %".46", !dbg !69
if.end:
  %".48" = load i64, i64* %"i.addr", !dbg !70
  %".49" = add i64 %".48", 1, !dbg !70
  store i64 %".49", i64* %"i.addr", !dbg !70
  br label %"while.cond", !dbg !70
if.then.1:
  %".56" = trunc i64 1 to i32 , !dbg !72
  ret i32 %".56", !dbg !72
if.end.1:
  %".58" = load i8*, i8** %"a", !dbg !73
  %".59" = load i64, i64* %"i.addr", !dbg !73
  %".60" = getelementptr i8, i8* %".58", i64 %".59" , !dbg !73
  %".61" = load i8, i8* %".60", !dbg !73
  %".62" = load i8*, i8** %"b", !dbg !73
  %".63" = load i64, i64* %"i.addr", !dbg !73
  %".64" = getelementptr i8, i8* %".62", i64 %".63" , !dbg !73
  %".65" = load i8, i8* %".64", !dbg !73
  %".66" = icmp eq i8 %".61", %".65" , !dbg !73
  %".67" = zext i1 %".66" to i32 , !dbg !73
  ret i32 %".67", !dbg !73
}

define i32 @"strcmp"(i8* %"a.arg", i8* %"b.arg") !dbg !20
{
entry:
  %"a" = alloca i8*
  %"i.addr" = alloca i64, !dbg !77
  store i8* %"a.arg", i8** %"a"
  call void @"llvm.dbg.declare"(metadata i8** %"a", metadata !74, metadata !7), !dbg !75
  %"b" = alloca i8*
  store i8* %"b.arg", i8** %"b"
  call void @"llvm.dbg.declare"(metadata i8** %"b", metadata !76, metadata !7), !dbg !75
  store i64 0, i64* %"i.addr", !dbg !77
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !78, metadata !7), !dbg !79
  br label %"while.cond", !dbg !80
while.cond:
  %".11" = load i8*, i8** %"a", !dbg !80
  %".12" = load i64, i64* %"i.addr", !dbg !80
  %".13" = getelementptr i8, i8* %".11", i64 %".12" , !dbg !80
  %".14" = load i8, i8* %".13", !dbg !80
  %".15" = zext i8 %".14" to i64 , !dbg !80
  %".16" = icmp ne i64 %".15", 0 , !dbg !80
  br i1 %".16", label %"and.right", label %"and.merge", !dbg !80
while.body:
  %".27" = load i8*, i8** %"a", !dbg !81
  %".28" = load i64, i64* %"i.addr", !dbg !81
  %".29" = getelementptr i8, i8* %".27", i64 %".28" , !dbg !81
  %".30" = load i8, i8* %".29", !dbg !81
  %".31" = load i8*, i8** %"b", !dbg !81
  %".32" = load i64, i64* %"i.addr", !dbg !81
  %".33" = getelementptr i8, i8* %".31", i64 %".32" , !dbg !81
  %".34" = load i8, i8* %".33", !dbg !81
  %".35" = icmp ult i8 %".30", %".34" , !dbg !81
  br i1 %".35", label %"if.then", label %"if.end", !dbg !81
while.end:
  %".56" = load i8*, i8** %"a", !dbg !86
  %".57" = load i64, i64* %"i.addr", !dbg !86
  %".58" = getelementptr i8, i8* %".56", i64 %".57" , !dbg !86
  %".59" = load i8, i8* %".58", !dbg !86
  %".60" = zext i8 %".59" to i64 , !dbg !86
  %".61" = icmp eq i64 %".60", 0 , !dbg !86
  br i1 %".61", label %"and.right.1", label %"and.merge.1", !dbg !86
and.right:
  %".18" = load i8*, i8** %"b", !dbg !80
  %".19" = load i64, i64* %"i.addr", !dbg !80
  %".20" = getelementptr i8, i8* %".18", i64 %".19" , !dbg !80
  %".21" = load i8, i8* %".20", !dbg !80
  %".22" = zext i8 %".21" to i64 , !dbg !80
  %".23" = icmp ne i64 %".22", 0 , !dbg !80
  br label %"and.merge", !dbg !80
and.merge:
  %".25" = phi  i1 [0, %"while.cond"], [%".23", %"and.right"] , !dbg !80
  br i1 %".25", label %"while.body", label %"while.end", !dbg !80
if.then:
  %".37" = sub i64 0, 1, !dbg !82
  %".38" = trunc i64 %".37" to i32 , !dbg !82
  ret i32 %".38", !dbg !82
if.end:
  %".40" = load i8*, i8** %"a", !dbg !83
  %".41" = load i64, i64* %"i.addr", !dbg !83
  %".42" = getelementptr i8, i8* %".40", i64 %".41" , !dbg !83
  %".43" = load i8, i8* %".42", !dbg !83
  %".44" = load i8*, i8** %"b", !dbg !83
  %".45" = load i64, i64* %"i.addr", !dbg !83
  %".46" = getelementptr i8, i8* %".44", i64 %".45" , !dbg !83
  %".47" = load i8, i8* %".46", !dbg !83
  %".48" = icmp ugt i8 %".43", %".47" , !dbg !83
  br i1 %".48", label %"if.then.1", label %"if.end.1", !dbg !83
if.then.1:
  %".50" = trunc i64 1 to i32 , !dbg !84
  ret i32 %".50", !dbg !84
if.end.1:
  %".52" = load i64, i64* %"i.addr", !dbg !85
  %".53" = add i64 %".52", 1, !dbg !85
  store i64 %".53", i64* %"i.addr", !dbg !85
  br label %"while.cond", !dbg !85
and.right.1:
  %".63" = load i8*, i8** %"b", !dbg !86
  %".64" = load i64, i64* %"i.addr", !dbg !86
  %".65" = getelementptr i8, i8* %".63", i64 %".64" , !dbg !86
  %".66" = load i8, i8* %".65", !dbg !86
  %".67" = zext i8 %".66" to i64 , !dbg !86
  %".68" = icmp eq i64 %".67", 0 , !dbg !86
  br label %"and.merge.1", !dbg !86
and.merge.1:
  %".70" = phi  i1 [0, %"while.end"], [%".68", %"and.right.1"] , !dbg !86
  br i1 %".70", label %"if.then.2", label %"if.end.2", !dbg !86
if.then.2:
  %".72" = trunc i64 0 to i32 , !dbg !87
  ret i32 %".72", !dbg !87
if.end.2:
  %".74" = load i8*, i8** %"a", !dbg !88
  %".75" = load i64, i64* %"i.addr", !dbg !88
  %".76" = getelementptr i8, i8* %".74", i64 %".75" , !dbg !88
  %".77" = load i8, i8* %".76", !dbg !88
  %".78" = zext i8 %".77" to i64 , !dbg !88
  %".79" = icmp eq i64 %".78", 0 , !dbg !88
  br i1 %".79", label %"if.then.3", label %"if.end.3", !dbg !88
if.then.3:
  %".81" = sub i64 0, 1, !dbg !89
  %".82" = trunc i64 %".81" to i32 , !dbg !89
  ret i32 %".82", !dbg !89
if.end.3:
  %".84" = trunc i64 1 to i32 , !dbg !90
  ret i32 %".84", !dbg !90
}

define i8* @"strchr"(i8* %"s.arg", i8 %"c.arg") !dbg !21
{
entry:
  %"s" = alloca i8*
  %"i.addr" = alloca i64, !dbg !94
  store i8* %"s.arg", i8** %"s"
  call void @"llvm.dbg.declare"(metadata i8** %"s", metadata !91, metadata !7), !dbg !92
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !93, metadata !7), !dbg !92
  store i64 0, i64* %"i.addr", !dbg !94
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !95, metadata !7), !dbg !96
  br label %"while.cond", !dbg !97
while.cond:
  %".11" = load i8*, i8** %"s", !dbg !97
  %".12" = load i64, i64* %"i.addr", !dbg !97
  %".13" = getelementptr i8, i8* %".11", i64 %".12" , !dbg !97
  %".14" = load i8, i8* %".13", !dbg !97
  %".15" = zext i8 %".14" to i64 , !dbg !97
  %".16" = icmp ne i64 %".15", 0 , !dbg !97
  br i1 %".16", label %"while.body", label %"while.end", !dbg !97
while.body:
  %".18" = load i8*, i8** %"s", !dbg !98
  %".19" = load i64, i64* %"i.addr", !dbg !98
  %".20" = getelementptr i8, i8* %".18", i64 %".19" , !dbg !98
  %".21" = load i8, i8* %".20", !dbg !98
  %".22" = load i8, i8* %"c", !dbg !98
  %".23" = icmp eq i8 %".21", %".22" , !dbg !98
  br i1 %".23", label %"if.then", label %"if.end", !dbg !98
while.end:
  %".33" = load i8, i8* %"c", !dbg !101
  %".34" = zext i8 %".33" to i64 , !dbg !101
  %".35" = icmp eq i64 %".34", 0 , !dbg !101
  br i1 %".35", label %"if.then.1", label %"if.end.1", !dbg !101
if.then:
  %".25" = load i8*, i8** %"s", !dbg !99
  %".26" = load i64, i64* %"i.addr", !dbg !99
  %".27" = getelementptr i8, i8* %".25", i64 %".26" , !dbg !99
  ret i8* %".27", !dbg !99
if.end:
  %".29" = load i64, i64* %"i.addr", !dbg !100
  %".30" = add i64 %".29", 1, !dbg !100
  store i64 %".30", i64* %"i.addr", !dbg !100
  br label %"while.cond", !dbg !100
if.then.1:
  %".37" = load i8*, i8** %"s", !dbg !102
  %".38" = load i64, i64* %"i.addr", !dbg !102
  %".39" = getelementptr i8, i8* %".37", i64 %".38" , !dbg !102
  ret i8* %".39", !dbg !102
if.end.1:
  ret i8* null, !dbg !103
}

define i8* @"strrchr"(i8* %"s.arg", i8 %"c.arg") !dbg !22
{
entry:
  %"s" = alloca i8*
  %"last.addr" = alloca i8*, !dbg !107
  %"i.addr" = alloca i64, !dbg !110
  store i8* %"s.arg", i8** %"s"
  call void @"llvm.dbg.declare"(metadata i8** %"s", metadata !104, metadata !7), !dbg !105
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !106, metadata !7), !dbg !105
  store i8* null, i8** %"last.addr", !dbg !107
  call void @"llvm.dbg.declare"(metadata i8** %"last.addr", metadata !108, metadata !7), !dbg !109
  store i64 0, i64* %"i.addr", !dbg !110
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !111, metadata !7), !dbg !112
  br label %"while.cond", !dbg !113
while.cond:
  %".13" = load i8*, i8** %"s", !dbg !113
  %".14" = load i64, i64* %"i.addr", !dbg !113
  %".15" = getelementptr i8, i8* %".13", i64 %".14" , !dbg !113
  %".16" = load i8, i8* %".15", !dbg !113
  %".17" = zext i8 %".16" to i64 , !dbg !113
  %".18" = icmp ne i64 %".17", 0 , !dbg !113
  br i1 %".18", label %"while.body", label %"while.end", !dbg !113
while.body:
  %".20" = load i8*, i8** %"s", !dbg !114
  %".21" = load i64, i64* %"i.addr", !dbg !114
  %".22" = getelementptr i8, i8* %".20", i64 %".21" , !dbg !114
  %".23" = load i8, i8* %".22", !dbg !114
  %".24" = load i8, i8* %"c", !dbg !114
  %".25" = icmp eq i8 %".23", %".24" , !dbg !114
  br i1 %".25", label %"if.then", label %"if.end", !dbg !114
while.end:
  %".36" = load i8, i8* %"c", !dbg !117
  %".37" = zext i8 %".36" to i64 , !dbg !117
  %".38" = icmp eq i64 %".37", 0 , !dbg !117
  br i1 %".38", label %"if.then.1", label %"if.end.1", !dbg !117
if.then:
  %".27" = load i8*, i8** %"s", !dbg !115
  %".28" = load i64, i64* %"i.addr", !dbg !115
  %".29" = getelementptr i8, i8* %".27", i64 %".28" , !dbg !115
  store i8* %".29", i8** %"last.addr", !dbg !115
  br label %"if.end", !dbg !115
if.end:
  %".32" = load i64, i64* %"i.addr", !dbg !116
  %".33" = add i64 %".32", 1, !dbg !116
  store i64 %".33", i64* %"i.addr", !dbg !116
  br label %"while.cond", !dbg !116
if.then.1:
  %".40" = load i8*, i8** %"s", !dbg !118
  %".41" = load i64, i64* %"i.addr", !dbg !118
  %".42" = getelementptr i8, i8* %".40", i64 %".41" , !dbg !118
  ret i8* %".42", !dbg !118
if.end.1:
  %".44" = load i8*, i8** %"last.addr", !dbg !119
  ret i8* %".44", !dbg !119
}

define i8* @"strstr"(i8* %"haystack.arg", i8* %"needle.arg") !dbg !23
{
entry:
  %"haystack" = alloca i8*
  %"i.addr" = alloca i64, !dbg !125
  %"j.addr" = alloca i64, !dbg !129
  store i8* %"haystack.arg", i8** %"haystack"
  call void @"llvm.dbg.declare"(metadata i8** %"haystack", metadata !120, metadata !7), !dbg !121
  %"needle" = alloca i8*
  store i8* %"needle.arg", i8** %"needle"
  call void @"llvm.dbg.declare"(metadata i8** %"needle", metadata !122, metadata !7), !dbg !121
  %".8" = load i8*, i8** %"needle", !dbg !123
  %".9" = load i8, i8* %".8", !dbg !123
  %".10" = zext i8 %".9" to i64 , !dbg !123
  %".11" = icmp eq i64 %".10", 0 , !dbg !123
  br i1 %".11", label %"if.then", label %"if.end", !dbg !123
if.then:
  %".13" = load i8*, i8** %"haystack", !dbg !124
  ret i8* %".13", !dbg !124
if.end:
  store i64 0, i64* %"i.addr", !dbg !125
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !126, metadata !7), !dbg !127
  br label %"while.cond", !dbg !128
while.cond:
  %".18" = load i8*, i8** %"haystack", !dbg !128
  %".19" = load i64, i64* %"i.addr", !dbg !128
  %".20" = getelementptr i8, i8* %".18", i64 %".19" , !dbg !128
  %".21" = load i8, i8* %".20", !dbg !128
  %".22" = zext i8 %".21" to i64 , !dbg !128
  %".23" = icmp ne i64 %".22", 0 , !dbg !128
  br i1 %".23", label %"while.body", label %"while.end", !dbg !128
while.body:
  store i64 0, i64* %"j.addr", !dbg !129
  call void @"llvm.dbg.declare"(metadata i64* %"j.addr", metadata !130, metadata !7), !dbg !131
  br label %"while.cond.1", !dbg !132
while.end:
  ret i8* null, !dbg !137
while.cond.1:
  %".28" = load i8*, i8** %"needle", !dbg !132
  %".29" = load i64, i64* %"j.addr", !dbg !132
  %".30" = getelementptr i8, i8* %".28", i64 %".29" , !dbg !132
  %".31" = load i8, i8* %".30", !dbg !132
  %".32" = zext i8 %".31" to i64 , !dbg !132
  %".33" = icmp ne i64 %".32", 0 , !dbg !132
  br i1 %".33", label %"and.right", label %"and.merge", !dbg !132
while.body.1:
  %".49" = load i64, i64* %"j.addr", !dbg !133
  %".50" = add i64 %".49", 1, !dbg !133
  store i64 %".50", i64* %"j.addr", !dbg !133
  br label %"while.cond.1", !dbg !133
while.end.1:
  %".53" = load i8*, i8** %"needle", !dbg !134
  %".54" = load i64, i64* %"j.addr", !dbg !134
  %".55" = getelementptr i8, i8* %".53", i64 %".54" , !dbg !134
  %".56" = load i8, i8* %".55", !dbg !134
  %".57" = zext i8 %".56" to i64 , !dbg !134
  %".58" = icmp eq i64 %".57", 0 , !dbg !134
  br i1 %".58", label %"if.then.1", label %"if.end.1", !dbg !134
and.right:
  %".35" = load i8*, i8** %"haystack", !dbg !132
  %".36" = load i64, i64* %"i.addr", !dbg !132
  %".37" = getelementptr i8, i8* %".35", i64 %".36" , !dbg !132
  %".38" = load i64, i64* %"j.addr", !dbg !132
  %".39" = getelementptr i8, i8* %".37", i64 %".38" , !dbg !132
  %".40" = load i8, i8* %".39", !dbg !132
  %".41" = load i8*, i8** %"needle", !dbg !132
  %".42" = load i64, i64* %"j.addr", !dbg !132
  %".43" = getelementptr i8, i8* %".41", i64 %".42" , !dbg !132
  %".44" = load i8, i8* %".43", !dbg !132
  %".45" = icmp eq i8 %".40", %".44" , !dbg !132
  br label %"and.merge", !dbg !132
and.merge:
  %".47" = phi  i1 [0, %"while.cond.1"], [%".45", %"and.right"] , !dbg !132
  br i1 %".47", label %"while.body.1", label %"while.end.1", !dbg !132
if.then.1:
  %".60" = load i8*, i8** %"haystack", !dbg !135
  %".61" = load i64, i64* %"i.addr", !dbg !135
  %".62" = getelementptr i8, i8* %".60", i64 %".61" , !dbg !135
  ret i8* %".62", !dbg !135
if.end.1:
  %".64" = load i64, i64* %"i.addr", !dbg !136
  %".65" = add i64 %".64", 1, !dbg !136
  store i64 %".65", i64* %"i.addr", !dbg !136
  br label %"while.cond", !dbg !136
}

define i8* @"strcpy"(i8* %"dest.arg", i8* %"src.arg") !dbg !24
{
entry:
  %"dest" = alloca i8*
  %"i.addr" = alloca i64, !dbg !141
  store i8* %"dest.arg", i8** %"dest"
  call void @"llvm.dbg.declare"(metadata i8** %"dest", metadata !138, metadata !7), !dbg !139
  %"src" = alloca i8*
  store i8* %"src.arg", i8** %"src"
  call void @"llvm.dbg.declare"(metadata i8** %"src", metadata !140, metadata !7), !dbg !139
  store i64 0, i64* %"i.addr", !dbg !141
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !142, metadata !7), !dbg !143
  br label %"while.cond", !dbg !144
while.cond:
  %".11" = load i8*, i8** %"src", !dbg !144
  %".12" = load i64, i64* %"i.addr", !dbg !144
  %".13" = getelementptr i8, i8* %".11", i64 %".12" , !dbg !144
  %".14" = load i8, i8* %".13", !dbg !144
  %".15" = zext i8 %".14" to i64 , !dbg !144
  %".16" = icmp ne i64 %".15", 0 , !dbg !144
  br i1 %".16", label %"while.body", label %"while.end", !dbg !144
while.body:
  %".18" = load i8*, i8** %"src", !dbg !145
  %".19" = load i64, i64* %"i.addr", !dbg !145
  %".20" = getelementptr i8, i8* %".18", i64 %".19" , !dbg !145
  %".21" = load i8, i8* %".20", !dbg !145
  %".22" = load i8*, i8** %"dest", !dbg !145
  %".23" = load i64, i64* %"i.addr", !dbg !145
  %".24" = getelementptr i8, i8* %".22", i64 %".23" , !dbg !145
  store i8 %".21", i8* %".24", !dbg !145
  %".26" = load i64, i64* %"i.addr", !dbg !146
  %".27" = add i64 %".26", 1, !dbg !146
  store i64 %".27", i64* %"i.addr", !dbg !146
  br label %"while.cond", !dbg !146
while.end:
  %".30" = load i8*, i8** %"dest", !dbg !147
  %".31" = load i64, i64* %"i.addr", !dbg !147
  %".32" = getelementptr i8, i8* %".30", i64 %".31" , !dbg !147
  %".33" = trunc i64 0 to i8 , !dbg !147
  store i8 %".33", i8* %".32", !dbg !147
  %".35" = load i8*, i8** %"dest", !dbg !148
  ret i8* %".35", !dbg !148
}

define i8* @"strncpy"(i8* %"dest.arg", i8* %"src.arg", i64 %"n.arg") !dbg !25
{
entry:
  %"dest" = alloca i8*
  %"i.addr" = alloca i64, !dbg !153
  store i8* %"dest.arg", i8** %"dest"
  call void @"llvm.dbg.declare"(metadata i8** %"dest", metadata !149, metadata !7), !dbg !150
  %"src" = alloca i8*
  store i8* %"src.arg", i8** %"src"
  call void @"llvm.dbg.declare"(metadata i8** %"src", metadata !151, metadata !7), !dbg !150
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !152, metadata !7), !dbg !150
  store i64 0, i64* %"i.addr", !dbg !153
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !154, metadata !7), !dbg !155
  br label %"while.cond", !dbg !156
while.cond:
  %".14" = load i64, i64* %"i.addr", !dbg !156
  %".15" = load i64, i64* %"n", !dbg !156
  %".16" = icmp slt i64 %".14", %".15" , !dbg !156
  br i1 %".16", label %"and.right", label %"and.merge", !dbg !156
while.body:
  %".27" = load i8*, i8** %"src", !dbg !157
  %".28" = load i64, i64* %"i.addr", !dbg !157
  %".29" = getelementptr i8, i8* %".27", i64 %".28" , !dbg !157
  %".30" = load i8, i8* %".29", !dbg !157
  %".31" = load i8*, i8** %"dest", !dbg !157
  %".32" = load i64, i64* %"i.addr", !dbg !157
  %".33" = getelementptr i8, i8* %".31", i64 %".32" , !dbg !157
  store i8 %".30", i8* %".33", !dbg !157
  %".35" = load i64, i64* %"i.addr", !dbg !158
  %".36" = add i64 %".35", 1, !dbg !158
  store i64 %".36", i64* %"i.addr", !dbg !158
  br label %"while.cond", !dbg !158
while.end:
  br label %"while.cond.1", !dbg !159
and.right:
  %".18" = load i8*, i8** %"src", !dbg !156
  %".19" = load i64, i64* %"i.addr", !dbg !156
  %".20" = getelementptr i8, i8* %".18", i64 %".19" , !dbg !156
  %".21" = load i8, i8* %".20", !dbg !156
  %".22" = zext i8 %".21" to i64 , !dbg !156
  %".23" = icmp ne i64 %".22", 0 , !dbg !156
  br label %"and.merge", !dbg !156
and.merge:
  %".25" = phi  i1 [0, %"while.cond"], [%".23", %"and.right"] , !dbg !156
  br i1 %".25", label %"while.body", label %"while.end", !dbg !156
while.cond.1:
  %".40" = load i64, i64* %"i.addr", !dbg !159
  %".41" = load i64, i64* %"n", !dbg !159
  %".42" = icmp slt i64 %".40", %".41" , !dbg !159
  br i1 %".42", label %"while.body.1", label %"while.end.1", !dbg !159
while.body.1:
  %".44" = load i8*, i8** %"dest", !dbg !160
  %".45" = load i64, i64* %"i.addr", !dbg !160
  %".46" = getelementptr i8, i8* %".44", i64 %".45" , !dbg !160
  %".47" = trunc i64 0 to i8 , !dbg !160
  store i8 %".47", i8* %".46", !dbg !160
  %".49" = load i64, i64* %"i.addr", !dbg !161
  %".50" = add i64 %".49", 1, !dbg !161
  store i64 %".50", i64* %"i.addr", !dbg !161
  br label %"while.cond.1", !dbg !161
while.end.1:
  %".53" = load i8*, i8** %"dest", !dbg !162
  ret i8* %".53", !dbg !162
}

define i8* @"strcat"(i8* %"dest.arg", i8* %"src.arg") !dbg !26
{
entry:
  %"dest" = alloca i8*
  %"len.addr" = alloca i64, !dbg !166
  store i8* %"dest.arg", i8** %"dest"
  call void @"llvm.dbg.declare"(metadata i8** %"dest", metadata !163, metadata !7), !dbg !164
  %"src" = alloca i8*
  store i8* %"src.arg", i8** %"src"
  call void @"llvm.dbg.declare"(metadata i8** %"src", metadata !165, metadata !7), !dbg !164
  %".8" = load i8*, i8** %"dest", !dbg !166
  %".9" = call i64 @"strlen"(i8* %".8"), !dbg !166
  store i64 %".9", i64* %"len.addr", !dbg !166
  call void @"llvm.dbg.declare"(metadata i64* %"len.addr", metadata !167, metadata !7), !dbg !168
  %".12" = load i8*, i8** %"dest", !dbg !169
  %".13" = load i64, i64* %"len.addr", !dbg !169
  %".14" = getelementptr i8, i8* %".12", i64 %".13" , !dbg !169
  %".15" = load i8*, i8** %"src", !dbg !169
  %".16" = call i8* @"strcpy"(i8* %".14", i8* %".15"), !dbg !169
  %".17" = load i8*, i8** %"dest", !dbg !170
  ret i8* %".17", !dbg !170
}

define i64 @"atoi"(i8* %"s.arg") !dbg !27
{
entry:
  %"s" = alloca i8*
  %"result.addr" = alloca i64, !dbg !173
  %"neg.addr" = alloca i32, !dbg !176
  %"i.addr" = alloca i64, !dbg !179
  store i8* %"s.arg", i8** %"s"
  call void @"llvm.dbg.declare"(metadata i8** %"s", metadata !171, metadata !7), !dbg !172
  store i64 0, i64* %"result.addr", !dbg !173
  call void @"llvm.dbg.declare"(metadata i64* %"result.addr", metadata !174, metadata !7), !dbg !175
  %".7" = trunc i64 0 to i32 , !dbg !176
  store i32 %".7", i32* %"neg.addr", !dbg !176
  call void @"llvm.dbg.declare"(metadata i32* %"neg.addr", metadata !177, metadata !7), !dbg !178
  store i64 0, i64* %"i.addr", !dbg !179
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !180, metadata !7), !dbg !181
  br label %"while.cond", !dbg !182
while.cond:
  %".13" = load i8*, i8** %"s", !dbg !182
  %".14" = load i64, i64* %"i.addr", !dbg !182
  %".15" = getelementptr i8, i8* %".13", i64 %".14" , !dbg !182
  %".16" = load i8, i8* %".15", !dbg !182
  %".17" = icmp eq i8 %".16", 32 , !dbg !182
  br i1 %".17", label %"or.merge", label %"or.right", !dbg !182
while.body:
  %".27" = load i64, i64* %"i.addr", !dbg !183
  %".28" = add i64 %".27", 1, !dbg !183
  store i64 %".28", i64* %"i.addr", !dbg !183
  br label %"while.cond", !dbg !183
while.end:
  %".31" = load i8*, i8** %"s", !dbg !184
  %".32" = load i64, i64* %"i.addr", !dbg !184
  %".33" = getelementptr i8, i8* %".31", i64 %".32" , !dbg !184
  %".34" = load i8, i8* %".33", !dbg !184
  %".35" = icmp eq i8 %".34", 45 , !dbg !184
  br i1 %".35", label %"if.then", label %"if.else", !dbg !184
or.right:
  %".19" = load i8*, i8** %"s", !dbg !182
  %".20" = load i64, i64* %"i.addr", !dbg !182
  %".21" = getelementptr i8, i8* %".19", i64 %".20" , !dbg !182
  %".22" = load i8, i8* %".21", !dbg !182
  %".23" = icmp eq i8 %".22", 9 , !dbg !182
  br label %"or.merge", !dbg !182
or.merge:
  %".25" = phi  i1 [1, %"while.cond"], [%".23", %"or.right"] , !dbg !182
  br i1 %".25", label %"while.body", label %"while.end", !dbg !182
if.then:
  %".37" = trunc i64 1 to i32 , !dbg !185
  store i32 %".37", i32* %"neg.addr", !dbg !185
  %".39" = load i64, i64* %"i.addr", !dbg !186
  %".40" = add i64 %".39", 1, !dbg !186
  store i64 %".40", i64* %"i.addr", !dbg !186
  br label %"if.end", !dbg !187
if.else:
  %".42" = load i8*, i8** %"s", !dbg !186
  %".43" = load i64, i64* %"i.addr", !dbg !186
  %".44" = getelementptr i8, i8* %".42", i64 %".43" , !dbg !186
  %".45" = load i8, i8* %".44", !dbg !186
  %".46" = icmp eq i8 %".45", 43 , !dbg !186
  br i1 %".46", label %"if.then.1", label %"if.end.1", !dbg !186
if.end:
  br label %"while.cond.1", !dbg !188
if.then.1:
  %".48" = load i64, i64* %"i.addr", !dbg !187
  %".49" = add i64 %".48", 1, !dbg !187
  store i64 %".49", i64* %"i.addr", !dbg !187
  br label %"if.end.1", !dbg !187
if.end.1:
  br label %"if.end", !dbg !187
while.cond.1:
  %".55" = load i8*, i8** %"s", !dbg !188
  %".56" = load i64, i64* %"i.addr", !dbg !188
  %".57" = getelementptr i8, i8* %".55", i64 %".56" , !dbg !188
  %".58" = load i8, i8* %".57", !dbg !188
  %".59" = icmp uge i8 %".58", 48 , !dbg !188
  br i1 %".59", label %"and.right", label %"and.merge", !dbg !188
while.body.1:
  %".69" = load i64, i64* %"result.addr", !dbg !189
  %".70" = mul i64 %".69", 10, !dbg !189
  %".71" = load i8*, i8** %"s", !dbg !189
  %".72" = load i64, i64* %"i.addr", !dbg !189
  %".73" = getelementptr i8, i8* %".71", i64 %".72" , !dbg !189
  %".74" = load i8, i8* %".73", !dbg !189
  %".75" = sub i8 %".74", 48, !dbg !189
  %".76" = sext i8 %".75" to i64 , !dbg !189
  %".77" = add i64 %".70", %".76", !dbg !189
  store i64 %".77", i64* %"result.addr", !dbg !189
  %".79" = load i64, i64* %"i.addr", !dbg !190
  %".80" = add i64 %".79", 1, !dbg !190
  store i64 %".80", i64* %"i.addr", !dbg !190
  br label %"while.cond.1", !dbg !190
while.end.1:
  %".83" = load i32, i32* %"neg.addr", !dbg !191
  %".84" = sext i32 %".83" to i64 , !dbg !191
  %".85" = icmp ne i64 %".84", 0 , !dbg !191
  br i1 %".85", label %"if.then.2", label %"if.end.2", !dbg !191
and.right:
  %".61" = load i8*, i8** %"s", !dbg !188
  %".62" = load i64, i64* %"i.addr", !dbg !188
  %".63" = getelementptr i8, i8* %".61", i64 %".62" , !dbg !188
  %".64" = load i8, i8* %".63", !dbg !188
  %".65" = icmp ule i8 %".64", 57 , !dbg !188
  br label %"and.merge", !dbg !188
and.merge:
  %".67" = phi  i1 [0, %"while.cond.1"], [%".65", %"and.right"] , !dbg !188
  br i1 %".67", label %"while.body.1", label %"while.end.1", !dbg !188
if.then.2:
  %".87" = load i64, i64* %"result.addr", !dbg !192
  %".88" = sub i64 0, %".87", !dbg !192
  ret i64 %".88", !dbg !192
if.end.2:
  %".90" = load i64, i64* %"result.addr", !dbg !193
  ret i64 %".90", !dbg !193
}

define i8* @"itoa"(i64 %"n.arg", i8* %"buf.arg") !dbg !28
{
entry:
  %"n" = alloca i64
  %"neg.addr" = alloca i32, !dbg !197
  %"tmp.addr" = alloca [20 x i8], !dbg !203
  %"len.addr" = alloca i64, !dbg !209
  %"pos.addr" = alloca i64, !dbg !219
  %"i.addr" = alloca i64, !dbg !225
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !194, metadata !7), !dbg !195
  %"buf" = alloca i8*
  store i8* %"buf.arg", i8** %"buf"
  call void @"llvm.dbg.declare"(metadata i8** %"buf", metadata !196, metadata !7), !dbg !195
  %".8" = trunc i64 0 to i32 , !dbg !197
  store i32 %".8", i32* %"neg.addr", !dbg !197
  call void @"llvm.dbg.declare"(metadata i32* %"neg.addr", metadata !198, metadata !7), !dbg !199
  %".11" = load i64, i64* %"n", !dbg !200
  %".12" = icmp slt i64 %".11", 0 , !dbg !200
  br i1 %".12", label %"if.then", label %"if.end", !dbg !200
if.then:
  %".14" = trunc i64 1 to i32 , !dbg !201
  store i32 %".14", i32* %"neg.addr", !dbg !201
  %".16" = load i64, i64* %"n", !dbg !202
  %".17" = sub i64 0, %".16", !dbg !202
  store i64 %".17", i64* %"n", !dbg !202
  br label %"if.end", !dbg !202
if.end:
  call void @"llvm.dbg.declare"(metadata [20 x i8]* %"tmp.addr", metadata !207, metadata !7), !dbg !208
  store i64 0, i64* %"len.addr", !dbg !209
  call void @"llvm.dbg.declare"(metadata i64* %"len.addr", metadata !210, metadata !7), !dbg !211
  %".23" = load i64, i64* %"n", !dbg !212
  %".24" = icmp eq i64 %".23", 0 , !dbg !212
  br i1 %".24", label %"if.then.1", label %"if.else", !dbg !212
if.then.1:
  %".26" = getelementptr [20 x i8], [20 x i8]* %"tmp.addr", i32 0, i64 0 , !dbg !213
  %".27" = trunc i64 48 to i8 , !dbg !213
  store i8 %".27", i8* %".26", !dbg !213
  store i64 1, i64* %"len.addr", !dbg !214
  br label %"if.end.1", !dbg !218
if.else:
  br label %"while.cond", !dbg !215
if.end.1:
  store i64 0, i64* %"pos.addr", !dbg !219
  call void @"llvm.dbg.declare"(metadata i64* %"pos.addr", metadata !220, metadata !7), !dbg !221
  %".52" = load i32, i32* %"neg.addr", !dbg !222
  %".53" = sext i32 %".52" to i64 , !dbg !222
  %".54" = icmp ne i64 %".53", 0 , !dbg !222
  br i1 %".54", label %"if.then.2", label %"if.end.2", !dbg !222
while.cond:
  %".31" = load i64, i64* %"n", !dbg !215
  %".32" = icmp sgt i64 %".31", 0 , !dbg !215
  br i1 %".32", label %"while.body", label %"while.end", !dbg !215
while.body:
  %".34" = load i64, i64* %"n", !dbg !216
  %".35" = srem i64 %".34", 10, !dbg !216
  %".36" = add i64 %".35", 48, !dbg !216
  %".37" = trunc i64 %".36" to i8 , !dbg !216
  %".38" = load i64, i64* %"len.addr", !dbg !216
  %".39" = getelementptr [20 x i8], [20 x i8]* %"tmp.addr", i32 0, i64 %".38" , !dbg !216
  store i8 %".37", i8* %".39", !dbg !216
  %".41" = load i64, i64* %"n", !dbg !217
  %".42" = sdiv i64 %".41", 10, !dbg !217
  store i64 %".42", i64* %"n", !dbg !217
  %".44" = load i64, i64* %"len.addr", !dbg !218
  %".45" = add i64 %".44", 1, !dbg !218
  store i64 %".45", i64* %"len.addr", !dbg !218
  br label %"while.cond", !dbg !218
while.end:
  br label %"if.end.1", !dbg !218
if.then.2:
  %".56" = load i8*, i8** %"buf", !dbg !223
  %".57" = trunc i64 45 to i8 , !dbg !223
  store i8 %".57", i8* %".56", !dbg !223
  store i64 1, i64* %"pos.addr", !dbg !224
  br label %"if.end.2", !dbg !224
if.end.2:
  %".61" = load i64, i64* %"len.addr", !dbg !225
  %".62" = sub i64 %".61", 1, !dbg !225
  store i64 %".62", i64* %"i.addr", !dbg !225
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !226, metadata !7), !dbg !227
  br label %"while.cond.1", !dbg !228
while.cond.1:
  %".66" = load i64, i64* %"i.addr", !dbg !228
  %".67" = icmp sge i64 %".66", 0 , !dbg !228
  br i1 %".67", label %"while.body.1", label %"while.end.1", !dbg !228
while.body.1:
  %".69" = load i64, i64* %"i.addr", !dbg !229
  %".70" = getelementptr [20 x i8], [20 x i8]* %"tmp.addr", i32 0, i64 %".69" , !dbg !229
  %".71" = load i8, i8* %".70", !dbg !229
  %".72" = load i8*, i8** %"buf", !dbg !229
  %".73" = load i64, i64* %"pos.addr", !dbg !229
  %".74" = getelementptr i8, i8* %".72", i64 %".73" , !dbg !229
  store i8 %".71", i8* %".74", !dbg !229
  %".76" = load i64, i64* %"pos.addr", !dbg !230
  %".77" = add i64 %".76", 1, !dbg !230
  store i64 %".77", i64* %"pos.addr", !dbg !230
  %".79" = load i64, i64* %"i.addr", !dbg !231
  %".80" = sub i64 %".79", 1, !dbg !231
  store i64 %".80", i64* %"i.addr", !dbg !231
  br label %"while.cond.1", !dbg !231
while.end.1:
  %".83" = load i8*, i8** %"buf", !dbg !232
  %".84" = load i64, i64* %"pos.addr", !dbg !232
  %".85" = getelementptr i8, i8* %".83", i64 %".84" , !dbg !232
  %".86" = trunc i64 0 to i8 , !dbg !232
  store i8 %".86", i8* %".85", !dbg !232
  %".88" = load i8*, i8** %"buf", !dbg !233
  ret i8* %".88", !dbg !233
}

define i32 @"isdigit"(i8 %"c.arg") !dbg !29
{
entry:
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !234, metadata !7), !dbg !235
  %".5" = load i8, i8* %"c", !dbg !236
  %".6" = icmp uge i8 %".5", 48 , !dbg !236
  br i1 %".6", label %"and.right", label %"and.merge", !dbg !236
and.right:
  %".8" = load i8, i8* %"c", !dbg !236
  %".9" = icmp ule i8 %".8", 57 , !dbg !236
  br label %"and.merge", !dbg !236
and.merge:
  %".11" = phi  i1 [0, %"entry"], [%".9", %"and.right"] , !dbg !236
  %".12" = zext i1 %".11" to i32 , !dbg !236
  ret i32 %".12", !dbg !236
}

define i32 @"isalpha"(i8 %"c.arg") !dbg !30
{
entry:
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !237, metadata !7), !dbg !238
  %".5" = load i8, i8* %"c", !dbg !239
  %".6" = icmp uge i8 %".5", 65 , !dbg !239
  br i1 %".6", label %"and.right", label %"and.merge", !dbg !239
and.right:
  %".8" = load i8, i8* %"c", !dbg !239
  %".9" = icmp ule i8 %".8", 90 , !dbg !239
  br label %"and.merge", !dbg !239
and.merge:
  %".11" = phi  i1 [0, %"entry"], [%".9", %"and.right"] , !dbg !239
  br i1 %".11", label %"or.merge", label %"or.right", !dbg !239
or.right:
  %".13" = load i8, i8* %"c", !dbg !239
  %".14" = icmp uge i8 %".13", 97 , !dbg !239
  br i1 %".14", label %"and.right.1", label %"and.merge.1", !dbg !239
or.merge:
  %".21" = phi  i1 [1, %"and.merge"], [%".19", %"and.merge.1"] , !dbg !239
  %".22" = zext i1 %".21" to i32 , !dbg !239
  ret i32 %".22", !dbg !239
and.right.1:
  %".16" = load i8, i8* %"c", !dbg !239
  %".17" = icmp ule i8 %".16", 122 , !dbg !239
  br label %"and.merge.1", !dbg !239
and.merge.1:
  %".19" = phi  i1 [0, %"or.right"], [%".17", %"and.right.1"] , !dbg !239
  br label %"or.merge", !dbg !239
}

define i32 @"isalnum"(i8 %"c.arg") !dbg !31
{
entry:
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !240, metadata !7), !dbg !241
  %".5" = load i8, i8* %"c", !dbg !242
  %".6" = call i32 @"isdigit"(i8 %".5"), !dbg !242
  %".7" = sext i32 %".6" to i64 , !dbg !242
  %".8" = icmp ne i64 %".7", 0 , !dbg !242
  br i1 %".8", label %"or.merge", label %"or.right", !dbg !242
or.right:
  %".10" = load i8, i8* %"c", !dbg !242
  %".11" = call i32 @"isalpha"(i8 %".10"), !dbg !242
  %".12" = sext i32 %".11" to i64 , !dbg !242
  %".13" = icmp ne i64 %".12", 0 , !dbg !242
  br label %"or.merge", !dbg !242
or.merge:
  %".15" = phi  i1 [1, %"entry"], [%".13", %"or.right"] , !dbg !242
  %".16" = zext i1 %".15" to i32 , !dbg !242
  ret i32 %".16", !dbg !242
}

define i32 @"isspace"(i8 %"c.arg") !dbg !32
{
entry:
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !243, metadata !7), !dbg !244
  %".5" = load i8, i8* %"c", !dbg !245
  %".6" = icmp eq i8 %".5", 32 , !dbg !245
  br i1 %".6", label %"or.merge", label %"or.right", !dbg !245
or.right:
  %".8" = load i8, i8* %"c", !dbg !245
  %".9" = icmp eq i8 %".8", 9 , !dbg !245
  br label %"or.merge", !dbg !245
or.merge:
  %".11" = phi  i1 [1, %"entry"], [%".9", %"or.right"] , !dbg !245
  br i1 %".11", label %"or.merge.1", label %"or.right.1", !dbg !245
or.right.1:
  %".13" = load i8, i8* %"c", !dbg !245
  %".14" = icmp eq i8 %".13", 10 , !dbg !245
  br label %"or.merge.1", !dbg !245
or.merge.1:
  %".16" = phi  i1 [1, %"or.merge"], [%".14", %"or.right.1"] , !dbg !245
  br i1 %".16", label %"or.merge.2", label %"or.right.2", !dbg !245
or.right.2:
  %".18" = load i8, i8* %"c", !dbg !245
  %".19" = icmp eq i8 %".18", 13 , !dbg !245
  br label %"or.merge.2", !dbg !245
or.merge.2:
  %".21" = phi  i1 [1, %"or.merge.1"], [%".19", %"or.right.2"] , !dbg !245
  %".22" = zext i1 %".21" to i32 , !dbg !245
  ret i32 %".22", !dbg !245
}

define i32 @"isupper"(i8 %"c.arg") !dbg !33
{
entry:
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !246, metadata !7), !dbg !247
  %".5" = load i8, i8* %"c", !dbg !248
  %".6" = icmp uge i8 %".5", 65 , !dbg !248
  br i1 %".6", label %"and.right", label %"and.merge", !dbg !248
and.right:
  %".8" = load i8, i8* %"c", !dbg !248
  %".9" = icmp ule i8 %".8", 90 , !dbg !248
  br label %"and.merge", !dbg !248
and.merge:
  %".11" = phi  i1 [0, %"entry"], [%".9", %"and.right"] , !dbg !248
  %".12" = zext i1 %".11" to i32 , !dbg !248
  ret i32 %".12", !dbg !248
}

define i32 @"islower"(i8 %"c.arg") !dbg !34
{
entry:
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !249, metadata !7), !dbg !250
  %".5" = load i8, i8* %"c", !dbg !251
  %".6" = icmp uge i8 %".5", 97 , !dbg !251
  br i1 %".6", label %"and.right", label %"and.merge", !dbg !251
and.right:
  %".8" = load i8, i8* %"c", !dbg !251
  %".9" = icmp ule i8 %".8", 122 , !dbg !251
  br label %"and.merge", !dbg !251
and.merge:
  %".11" = phi  i1 [0, %"entry"], [%".9", %"and.right"] , !dbg !251
  %".12" = zext i1 %".11" to i32 , !dbg !251
  ret i32 %".12", !dbg !251
}

define i8 @"toupper"(i8 %"c.arg") !dbg !35
{
entry:
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !252, metadata !7), !dbg !253
  %".5" = load i8, i8* %"c", !dbg !254
  %".6" = icmp uge i8 %".5", 97 , !dbg !254
  br i1 %".6", label %"and.right", label %"and.merge", !dbg !254
and.right:
  %".8" = load i8, i8* %"c", !dbg !254
  %".9" = icmp ule i8 %".8", 122 , !dbg !254
  br label %"and.merge", !dbg !254
and.merge:
  %".11" = phi  i1 [0, %"entry"], [%".9", %"and.right"] , !dbg !254
  br i1 %".11", label %"if.then", label %"if.end", !dbg !254
if.then:
  %".13" = load i8, i8* %"c", !dbg !255
  %".14" = zext i8 %".13" to i64 , !dbg !255
  %".15" = sub i64 %".14", 32, !dbg !255
  %".16" = trunc i64 %".15" to i8 , !dbg !255
  ret i8 %".16", !dbg !255
if.end:
  %".18" = load i8, i8* %"c", !dbg !256
  ret i8 %".18", !dbg !256
}

define i8 @"tolower"(i8 %"c.arg") !dbg !36
{
entry:
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !257, metadata !7), !dbg !258
  %".5" = load i8, i8* %"c", !dbg !259
  %".6" = icmp uge i8 %".5", 65 , !dbg !259
  br i1 %".6", label %"and.right", label %"and.merge", !dbg !259
and.right:
  %".8" = load i8, i8* %"c", !dbg !259
  %".9" = icmp ule i8 %".8", 90 , !dbg !259
  br label %"and.merge", !dbg !259
and.merge:
  %".11" = phi  i1 [0, %"entry"], [%".9", %"and.right"] , !dbg !259
  br i1 %".11", label %"if.then", label %"if.end", !dbg !259
if.then:
  %".13" = load i8, i8* %"c", !dbg !260
  %".14" = zext i8 %".13" to i64 , !dbg !260
  %".15" = add i64 %".14", 32, !dbg !260
  %".16" = trunc i64 %".15" to i8 , !dbg !260
  ret i8 %".16", !dbg !260
if.end:
  %".18" = load i8, i8* %"c", !dbg !261
  ret i8 %".18", !dbg !261
}

define i8* @"memset"(i8* %"dest.arg", i8 %"c.arg", i64 %"n.arg") !dbg !37
{
entry:
  %"dest" = alloca i8*
  %"i" = alloca i64, !dbg !266
  store i8* %"dest.arg", i8** %"dest"
  call void @"llvm.dbg.declare"(metadata i8** %"dest", metadata !262, metadata !7), !dbg !263
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !264, metadata !7), !dbg !263
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !265, metadata !7), !dbg !263
  %".11" = load i64, i64* %"n", !dbg !266
  store i64 0, i64* %"i", !dbg !266
  br label %"for.cond", !dbg !266
for.cond:
  %".14" = load i64, i64* %"i", !dbg !266
  %".15" = icmp slt i64 %".14", %".11" , !dbg !266
  br i1 %".15", label %"for.body", label %"for.end", !dbg !266
for.body:
  %".17" = load i8, i8* %"c", !dbg !267
  %".18" = load i8*, i8** %"dest", !dbg !267
  %".19" = load i64, i64* %"i", !dbg !267
  %".20" = getelementptr i8, i8* %".18", i64 %".19" , !dbg !267
  store i8 %".17", i8* %".20", !dbg !267
  br label %"for.incr", !dbg !267
for.incr:
  %".23" = load i64, i64* %"i", !dbg !267
  %".24" = add i64 %".23", 1, !dbg !267
  store i64 %".24", i64* %"i", !dbg !267
  br label %"for.cond", !dbg !267
for.end:
  %".27" = load i8*, i8** %"dest", !dbg !268
  ret i8* %".27", !dbg !268
}

define i8* @"memcpy"(i8* %"dest.arg", i8* %"src.arg", i64 %"n.arg") !dbg !38
{
entry:
  %"dest" = alloca i8*
  %"i" = alloca i64, !dbg !273
  store i8* %"dest.arg", i8** %"dest"
  call void @"llvm.dbg.declare"(metadata i8** %"dest", metadata !269, metadata !7), !dbg !270
  %"src" = alloca i8*
  store i8* %"src.arg", i8** %"src"
  call void @"llvm.dbg.declare"(metadata i8** %"src", metadata !271, metadata !7), !dbg !270
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !272, metadata !7), !dbg !270
  %".11" = load i64, i64* %"n", !dbg !273
  store i64 0, i64* %"i", !dbg !273
  br label %"for.cond", !dbg !273
for.cond:
  %".14" = load i64, i64* %"i", !dbg !273
  %".15" = icmp slt i64 %".14", %".11" , !dbg !273
  br i1 %".15", label %"for.body", label %"for.end", !dbg !273
for.body:
  %".17" = load i8*, i8** %"src", !dbg !274
  %".18" = load i64, i64* %"i", !dbg !274
  %".19" = getelementptr i8, i8* %".17", i64 %".18" , !dbg !274
  %".20" = load i8, i8* %".19", !dbg !274
  %".21" = load i8*, i8** %"dest", !dbg !274
  %".22" = load i64, i64* %"i", !dbg !274
  %".23" = getelementptr i8, i8* %".21", i64 %".22" , !dbg !274
  store i8 %".20", i8* %".23", !dbg !274
  br label %"for.incr", !dbg !274
for.incr:
  %".26" = load i64, i64* %"i", !dbg !274
  %".27" = add i64 %".26", 1, !dbg !274
  store i64 %".27", i64* %"i", !dbg !274
  br label %"for.cond", !dbg !274
for.end:
  %".30" = load i8*, i8** %"dest", !dbg !275
  ret i8* %".30", !dbg !275
}

define i32 @"memcmp"(i8* %"a.arg", i8* %"b.arg", i64 %"n.arg") !dbg !39
{
entry:
  %"a" = alloca i8*
  %"i" = alloca i64, !dbg !280
  store i8* %"a.arg", i8** %"a"
  call void @"llvm.dbg.declare"(metadata i8** %"a", metadata !276, metadata !7), !dbg !277
  %"b" = alloca i8*
  store i8* %"b.arg", i8** %"b"
  call void @"llvm.dbg.declare"(metadata i8** %"b", metadata !278, metadata !7), !dbg !277
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !279, metadata !7), !dbg !277
  %".11" = load i64, i64* %"n", !dbg !280
  store i64 0, i64* %"i", !dbg !280
  br label %"for.cond", !dbg !280
for.cond:
  %".14" = load i64, i64* %"i", !dbg !280
  %".15" = icmp slt i64 %".14", %".11" , !dbg !280
  br i1 %".15", label %"for.body", label %"for.end", !dbg !280
for.body:
  %".17" = load i8*, i8** %"a", !dbg !281
  %".18" = load i64, i64* %"i", !dbg !281
  %".19" = getelementptr i8, i8* %".17", i64 %".18" , !dbg !281
  %".20" = load i8, i8* %".19", !dbg !281
  %".21" = load i8*, i8** %"b", !dbg !281
  %".22" = load i64, i64* %"i", !dbg !281
  %".23" = getelementptr i8, i8* %".21", i64 %".22" , !dbg !281
  %".24" = load i8, i8* %".23", !dbg !281
  %".25" = icmp ult i8 %".20", %".24" , !dbg !281
  br i1 %".25", label %"if.then", label %"if.end", !dbg !281
for.incr:
  %".43" = load i64, i64* %"i", !dbg !283
  %".44" = add i64 %".43", 1, !dbg !283
  store i64 %".44", i64* %"i", !dbg !283
  br label %"for.cond", !dbg !283
for.end:
  %".47" = trunc i64 0 to i32 , !dbg !284
  ret i32 %".47", !dbg !284
if.then:
  %".27" = sub i64 0, 1, !dbg !282
  %".28" = trunc i64 %".27" to i32 , !dbg !282
  ret i32 %".28", !dbg !282
if.end:
  %".30" = load i8*, i8** %"a", !dbg !282
  %".31" = load i64, i64* %"i", !dbg !282
  %".32" = getelementptr i8, i8* %".30", i64 %".31" , !dbg !282
  %".33" = load i8, i8* %".32", !dbg !282
  %".34" = load i8*, i8** %"b", !dbg !282
  %".35" = load i64, i64* %"i", !dbg !282
  %".36" = getelementptr i8, i8* %".34", i64 %".35" , !dbg !282
  %".37" = load i8, i8* %".36", !dbg !282
  %".38" = icmp ugt i8 %".33", %".37" , !dbg !282
  br i1 %".38", label %"if.then.1", label %"if.end.1", !dbg !282
if.then.1:
  %".40" = trunc i64 1 to i32 , !dbg !283
  ret i32 %".40", !dbg !283
if.end.1:
  br label %"for.incr", !dbg !283
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/cryptosec/ritz/ritzlib", filename: "str.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 9, name: "strlen", scopeLine: 9, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 15, name: "streq", scopeLine: 15, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 23, name: "strneq", scopeLine: 23, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 33, name: "strcmp", scopeLine: 33, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 51, name: "strchr", scopeLine: 51, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 61, name: "strrchr", scopeLine: 61, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 72, name: "strstr", scopeLine: 72, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 89, name: "strcpy", scopeLine: 89, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 97, name: "strncpy", scopeLine: 97, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 107, name: "strcat", scopeLine: 107, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "atoi", scopeLine: 116, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 141, name: "itoa", scopeLine: 141, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "isdigit", scopeLine: 179, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 182, name: "isalpha", scopeLine: 182, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 185, name: "isalnum", scopeLine: 185, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 188, name: "isspace", scopeLine: 188, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 191, name: "isupper", scopeLine: 191, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 194, name: "islower", scopeLine: 194, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 197, name: "toupper", scopeLine: 197, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 202, name: "tolower", scopeLine: 202, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 211, name: "memset", scopeLine: 211, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 216, name: "memcpy", scopeLine: 216, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 221, name: "memcmp", scopeLine: 221, type: !4, unit: !1)
!40 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!41 = !DILocalVariable(file: !0, line: 9, name: "s", scope: !17, type: !40)
!42 = !DILocation(column: 1, line: 9, scope: !17)
!43 = !DILocation(column: 5, line: 10, scope: !17)
!44 = !DILocalVariable(file: !0, line: 10, name: "len", scope: !17, type: !11)
!45 = !DILocation(column: 1, line: 10, scope: !17)
!46 = !DILocation(column: 5, line: 11, scope: !17)
!47 = !DILocation(column: 9, line: 12, scope: !17)
!48 = !DILocation(column: 5, line: 13, scope: !17)
!49 = !DILocalVariable(file: !0, line: 15, name: "a", scope: !18, type: !40)
!50 = !DILocation(column: 1, line: 15, scope: !18)
!51 = !DILocalVariable(file: !0, line: 15, name: "b", scope: !18, type: !40)
!52 = !DILocation(column: 5, line: 16, scope: !18)
!53 = !DILocalVariable(file: !0, line: 16, name: "i", scope: !18, type: !11)
!54 = !DILocation(column: 1, line: 16, scope: !18)
!55 = !DILocation(column: 5, line: 17, scope: !18)
!56 = !DILocation(column: 9, line: 18, scope: !18)
!57 = !DILocation(column: 13, line: 19, scope: !18)
!58 = !DILocation(column: 9, line: 20, scope: !18)
!59 = !DILocation(column: 5, line: 21, scope: !18)
!60 = !DILocalVariable(file: !0, line: 23, name: "a", scope: !19, type: !40)
!61 = !DILocation(column: 1, line: 23, scope: !19)
!62 = !DILocalVariable(file: !0, line: 23, name: "b", scope: !19, type: !40)
!63 = !DILocalVariable(file: !0, line: 23, name: "n", scope: !19, type: !11)
!64 = !DILocation(column: 5, line: 24, scope: !19)
!65 = !DILocalVariable(file: !0, line: 24, name: "i", scope: !19, type: !11)
!66 = !DILocation(column: 1, line: 24, scope: !19)
!67 = !DILocation(column: 5, line: 25, scope: !19)
!68 = !DILocation(column: 9, line: 26, scope: !19)
!69 = !DILocation(column: 13, line: 27, scope: !19)
!70 = !DILocation(column: 9, line: 28, scope: !19)
!71 = !DILocation(column: 5, line: 29, scope: !19)
!72 = !DILocation(column: 9, line: 30, scope: !19)
!73 = !DILocation(column: 5, line: 31, scope: !19)
!74 = !DILocalVariable(file: !0, line: 33, name: "a", scope: !20, type: !40)
!75 = !DILocation(column: 1, line: 33, scope: !20)
!76 = !DILocalVariable(file: !0, line: 33, name: "b", scope: !20, type: !40)
!77 = !DILocation(column: 5, line: 34, scope: !20)
!78 = !DILocalVariable(file: !0, line: 34, name: "i", scope: !20, type: !11)
!79 = !DILocation(column: 1, line: 34, scope: !20)
!80 = !DILocation(column: 5, line: 35, scope: !20)
!81 = !DILocation(column: 9, line: 36, scope: !20)
!82 = !DILocation(column: 13, line: 37, scope: !20)
!83 = !DILocation(column: 9, line: 38, scope: !20)
!84 = !DILocation(column: 13, line: 39, scope: !20)
!85 = !DILocation(column: 9, line: 40, scope: !20)
!86 = !DILocation(column: 5, line: 41, scope: !20)
!87 = !DILocation(column: 9, line: 42, scope: !20)
!88 = !DILocation(column: 5, line: 43, scope: !20)
!89 = !DILocation(column: 9, line: 44, scope: !20)
!90 = !DILocation(column: 5, line: 45, scope: !20)
!91 = !DILocalVariable(file: !0, line: 51, name: "s", scope: !21, type: !40)
!92 = !DILocation(column: 1, line: 51, scope: !21)
!93 = !DILocalVariable(file: !0, line: 51, name: "c", scope: !21, type: !12)
!94 = !DILocation(column: 5, line: 52, scope: !21)
!95 = !DILocalVariable(file: !0, line: 52, name: "i", scope: !21, type: !11)
!96 = !DILocation(column: 1, line: 52, scope: !21)
!97 = !DILocation(column: 5, line: 53, scope: !21)
!98 = !DILocation(column: 9, line: 54, scope: !21)
!99 = !DILocation(column: 13, line: 55, scope: !21)
!100 = !DILocation(column: 9, line: 56, scope: !21)
!101 = !DILocation(column: 5, line: 57, scope: !21)
!102 = !DILocation(column: 9, line: 58, scope: !21)
!103 = !DILocation(column: 5, line: 59, scope: !21)
!104 = !DILocalVariable(file: !0, line: 61, name: "s", scope: !22, type: !40)
!105 = !DILocation(column: 1, line: 61, scope: !22)
!106 = !DILocalVariable(file: !0, line: 61, name: "c", scope: !22, type: !12)
!107 = !DILocation(column: 5, line: 62, scope: !22)
!108 = !DILocalVariable(file: !0, line: 62, name: "last", scope: !22, type: !40)
!109 = !DILocation(column: 1, line: 62, scope: !22)
!110 = !DILocation(column: 5, line: 63, scope: !22)
!111 = !DILocalVariable(file: !0, line: 63, name: "i", scope: !22, type: !11)
!112 = !DILocation(column: 1, line: 63, scope: !22)
!113 = !DILocation(column: 5, line: 64, scope: !22)
!114 = !DILocation(column: 9, line: 65, scope: !22)
!115 = !DILocation(column: 13, line: 66, scope: !22)
!116 = !DILocation(column: 9, line: 67, scope: !22)
!117 = !DILocation(column: 5, line: 68, scope: !22)
!118 = !DILocation(column: 9, line: 69, scope: !22)
!119 = !DILocation(column: 5, line: 70, scope: !22)
!120 = !DILocalVariable(file: !0, line: 72, name: "haystack", scope: !23, type: !40)
!121 = !DILocation(column: 1, line: 72, scope: !23)
!122 = !DILocalVariable(file: !0, line: 72, name: "needle", scope: !23, type: !40)
!123 = !DILocation(column: 5, line: 73, scope: !23)
!124 = !DILocation(column: 9, line: 74, scope: !23)
!125 = !DILocation(column: 5, line: 75, scope: !23)
!126 = !DILocalVariable(file: !0, line: 75, name: "i", scope: !23, type: !11)
!127 = !DILocation(column: 1, line: 75, scope: !23)
!128 = !DILocation(column: 5, line: 76, scope: !23)
!129 = !DILocation(column: 9, line: 77, scope: !23)
!130 = !DILocalVariable(file: !0, line: 77, name: "j", scope: !23, type: !11)
!131 = !DILocation(column: 1, line: 77, scope: !23)
!132 = !DILocation(column: 9, line: 78, scope: !23)
!133 = !DILocation(column: 13, line: 79, scope: !23)
!134 = !DILocation(column: 9, line: 80, scope: !23)
!135 = !DILocation(column: 13, line: 81, scope: !23)
!136 = !DILocation(column: 9, line: 82, scope: !23)
!137 = !DILocation(column: 5, line: 83, scope: !23)
!138 = !DILocalVariable(file: !0, line: 89, name: "dest", scope: !24, type: !40)
!139 = !DILocation(column: 1, line: 89, scope: !24)
!140 = !DILocalVariable(file: !0, line: 89, name: "src", scope: !24, type: !40)
!141 = !DILocation(column: 5, line: 90, scope: !24)
!142 = !DILocalVariable(file: !0, line: 90, name: "i", scope: !24, type: !11)
!143 = !DILocation(column: 1, line: 90, scope: !24)
!144 = !DILocation(column: 5, line: 91, scope: !24)
!145 = !DILocation(column: 9, line: 92, scope: !24)
!146 = !DILocation(column: 9, line: 93, scope: !24)
!147 = !DILocation(column: 5, line: 94, scope: !24)
!148 = !DILocation(column: 5, line: 95, scope: !24)
!149 = !DILocalVariable(file: !0, line: 97, name: "dest", scope: !25, type: !40)
!150 = !DILocation(column: 1, line: 97, scope: !25)
!151 = !DILocalVariable(file: !0, line: 97, name: "src", scope: !25, type: !40)
!152 = !DILocalVariable(file: !0, line: 97, name: "n", scope: !25, type: !11)
!153 = !DILocation(column: 5, line: 98, scope: !25)
!154 = !DILocalVariable(file: !0, line: 98, name: "i", scope: !25, type: !11)
!155 = !DILocation(column: 1, line: 98, scope: !25)
!156 = !DILocation(column: 5, line: 99, scope: !25)
!157 = !DILocation(column: 9, line: 100, scope: !25)
!158 = !DILocation(column: 9, line: 101, scope: !25)
!159 = !DILocation(column: 5, line: 102, scope: !25)
!160 = !DILocation(column: 9, line: 103, scope: !25)
!161 = !DILocation(column: 9, line: 104, scope: !25)
!162 = !DILocation(column: 5, line: 105, scope: !25)
!163 = !DILocalVariable(file: !0, line: 107, name: "dest", scope: !26, type: !40)
!164 = !DILocation(column: 1, line: 107, scope: !26)
!165 = !DILocalVariable(file: !0, line: 107, name: "src", scope: !26, type: !40)
!166 = !DILocation(column: 5, line: 108, scope: !26)
!167 = !DILocalVariable(file: !0, line: 108, name: "len", scope: !26, type: !11)
!168 = !DILocation(column: 1, line: 108, scope: !26)
!169 = !DILocation(column: 5, line: 109, scope: !26)
!170 = !DILocation(column: 5, line: 110, scope: !26)
!171 = !DILocalVariable(file: !0, line: 116, name: "s", scope: !27, type: !40)
!172 = !DILocation(column: 1, line: 116, scope: !27)
!173 = !DILocation(column: 5, line: 117, scope: !27)
!174 = !DILocalVariable(file: !0, line: 117, name: "result", scope: !27, type: !11)
!175 = !DILocation(column: 1, line: 117, scope: !27)
!176 = !DILocation(column: 5, line: 118, scope: !27)
!177 = !DILocalVariable(file: !0, line: 118, name: "neg", scope: !27, type: !10)
!178 = !DILocation(column: 1, line: 118, scope: !27)
!179 = !DILocation(column: 5, line: 119, scope: !27)
!180 = !DILocalVariable(file: !0, line: 119, name: "i", scope: !27, type: !11)
!181 = !DILocation(column: 1, line: 119, scope: !27)
!182 = !DILocation(column: 5, line: 122, scope: !27)
!183 = !DILocation(column: 9, line: 123, scope: !27)
!184 = !DILocation(column: 5, line: 126, scope: !27)
!185 = !DILocation(column: 9, line: 127, scope: !27)
!186 = !DILocation(column: 9, line: 128, scope: !27)
!187 = !DILocation(column: 9, line: 130, scope: !27)
!188 = !DILocation(column: 5, line: 133, scope: !27)
!189 = !DILocation(column: 9, line: 134, scope: !27)
!190 = !DILocation(column: 9, line: 135, scope: !27)
!191 = !DILocation(column: 5, line: 137, scope: !27)
!192 = !DILocation(column: 9, line: 138, scope: !27)
!193 = !DILocation(column: 5, line: 139, scope: !27)
!194 = !DILocalVariable(file: !0, line: 141, name: "n", scope: !28, type: !11)
!195 = !DILocation(column: 1, line: 141, scope: !28)
!196 = !DILocalVariable(file: !0, line: 141, name: "buf", scope: !28, type: !40)
!197 = !DILocation(column: 5, line: 142, scope: !28)
!198 = !DILocalVariable(file: !0, line: 142, name: "neg", scope: !28, type: !10)
!199 = !DILocation(column: 1, line: 142, scope: !28)
!200 = !DILocation(column: 5, line: 143, scope: !28)
!201 = !DILocation(column: 9, line: 144, scope: !28)
!202 = !DILocation(column: 9, line: 145, scope: !28)
!203 = !DILocation(column: 5, line: 148, scope: !28)
!204 = !DISubrange(count: 20)
!205 = !{ !204 }
!206 = !DICompositeType(baseType: !12, elements: !205, size: 160, tag: DW_TAG_array_type)
!207 = !DILocalVariable(file: !0, line: 148, name: "tmp", scope: !28, type: !206)
!208 = !DILocation(column: 1, line: 148, scope: !28)
!209 = !DILocation(column: 5, line: 149, scope: !28)
!210 = !DILocalVariable(file: !0, line: 149, name: "len", scope: !28, type: !11)
!211 = !DILocation(column: 1, line: 149, scope: !28)
!212 = !DILocation(column: 5, line: 151, scope: !28)
!213 = !DILocation(column: 9, line: 152, scope: !28)
!214 = !DILocation(column: 9, line: 153, scope: !28)
!215 = !DILocation(column: 9, line: 155, scope: !28)
!216 = !DILocation(column: 13, line: 156, scope: !28)
!217 = !DILocation(column: 13, line: 157, scope: !28)
!218 = !DILocation(column: 13, line: 158, scope: !28)
!219 = !DILocation(column: 5, line: 161, scope: !28)
!220 = !DILocalVariable(file: !0, line: 161, name: "pos", scope: !28, type: !11)
!221 = !DILocation(column: 1, line: 161, scope: !28)
!222 = !DILocation(column: 5, line: 162, scope: !28)
!223 = !DILocation(column: 9, line: 163, scope: !28)
!224 = !DILocation(column: 9, line: 164, scope: !28)
!225 = !DILocation(column: 5, line: 166, scope: !28)
!226 = !DILocalVariable(file: !0, line: 166, name: "i", scope: !28, type: !11)
!227 = !DILocation(column: 1, line: 166, scope: !28)
!228 = !DILocation(column: 5, line: 167, scope: !28)
!229 = !DILocation(column: 9, line: 168, scope: !28)
!230 = !DILocation(column: 9, line: 169, scope: !28)
!231 = !DILocation(column: 9, line: 170, scope: !28)
!232 = !DILocation(column: 5, line: 172, scope: !28)
!233 = !DILocation(column: 5, line: 173, scope: !28)
!234 = !DILocalVariable(file: !0, line: 179, name: "c", scope: !29, type: !12)
!235 = !DILocation(column: 1, line: 179, scope: !29)
!236 = !DILocation(column: 5, line: 180, scope: !29)
!237 = !DILocalVariable(file: !0, line: 182, name: "c", scope: !30, type: !12)
!238 = !DILocation(column: 1, line: 182, scope: !30)
!239 = !DILocation(column: 5, line: 183, scope: !30)
!240 = !DILocalVariable(file: !0, line: 185, name: "c", scope: !31, type: !12)
!241 = !DILocation(column: 1, line: 185, scope: !31)
!242 = !DILocation(column: 5, line: 186, scope: !31)
!243 = !DILocalVariable(file: !0, line: 188, name: "c", scope: !32, type: !12)
!244 = !DILocation(column: 1, line: 188, scope: !32)
!245 = !DILocation(column: 5, line: 189, scope: !32)
!246 = !DILocalVariable(file: !0, line: 191, name: "c", scope: !33, type: !12)
!247 = !DILocation(column: 1, line: 191, scope: !33)
!248 = !DILocation(column: 5, line: 192, scope: !33)
!249 = !DILocalVariable(file: !0, line: 194, name: "c", scope: !34, type: !12)
!250 = !DILocation(column: 1, line: 194, scope: !34)
!251 = !DILocation(column: 5, line: 195, scope: !34)
!252 = !DILocalVariable(file: !0, line: 197, name: "c", scope: !35, type: !12)
!253 = !DILocation(column: 1, line: 197, scope: !35)
!254 = !DILocation(column: 5, line: 198, scope: !35)
!255 = !DILocation(column: 9, line: 199, scope: !35)
!256 = !DILocation(column: 5, line: 200, scope: !35)
!257 = !DILocalVariable(file: !0, line: 202, name: "c", scope: !36, type: !12)
!258 = !DILocation(column: 1, line: 202, scope: !36)
!259 = !DILocation(column: 5, line: 203, scope: !36)
!260 = !DILocation(column: 9, line: 204, scope: !36)
!261 = !DILocation(column: 5, line: 205, scope: !36)
!262 = !DILocalVariable(file: !0, line: 211, name: "dest", scope: !37, type: !40)
!263 = !DILocation(column: 1, line: 211, scope: !37)
!264 = !DILocalVariable(file: !0, line: 211, name: "c", scope: !37, type: !12)
!265 = !DILocalVariable(file: !0, line: 211, name: "n", scope: !37, type: !11)
!266 = !DILocation(column: 5, line: 212, scope: !37)
!267 = !DILocation(column: 9, line: 213, scope: !37)
!268 = !DILocation(column: 5, line: 214, scope: !37)
!269 = !DILocalVariable(file: !0, line: 216, name: "dest", scope: !38, type: !40)
!270 = !DILocation(column: 1, line: 216, scope: !38)
!271 = !DILocalVariable(file: !0, line: 216, name: "src", scope: !38, type: !40)
!272 = !DILocalVariable(file: !0, line: 216, name: "n", scope: !38, type: !11)
!273 = !DILocation(column: 5, line: 217, scope: !38)
!274 = !DILocation(column: 9, line: 218, scope: !38)
!275 = !DILocation(column: 5, line: 219, scope: !38)
!276 = !DILocalVariable(file: !0, line: 221, name: "a", scope: !39, type: !40)
!277 = !DILocation(column: 1, line: 221, scope: !39)
!278 = !DILocalVariable(file: !0, line: 221, name: "b", scope: !39, type: !40)
!279 = !DILocalVariable(file: !0, line: 221, name: "n", scope: !39, type: !11)
!280 = !DILocation(column: 5, line: 222, scope: !39)
!281 = !DILocation(column: 9, line: 223, scope: !39)
!282 = !DILocation(column: 13, line: 224, scope: !39)
!283 = !DILocation(column: 13, line: 226, scope: !39)
!284 = !DILocation(column: 5, line: 227, scope: !39)