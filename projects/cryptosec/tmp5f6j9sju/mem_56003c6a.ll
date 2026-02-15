; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Stat" = type {i64, i64, i64, i32, i32, i32, i32, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64}
%"struct.ritz_module_1.Dirent64" = type {i64, i64, i16, i8}
%"struct.ritz_module_1.Timeval" = type {i64, i64}
declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

declare i32 @"sys_stat2"(i8* %".1", %"struct.ritz_module_1.Stat"* %".2")

declare i32 @"sys_fstat2"(i32 %".1", %"struct.ritz_module_1.Stat"* %".2")

declare i32 @"sys_lstat2"(i8* %".1", %"struct.ritz_module_1.Stat"* %".2")

declare i32 @"at_fdcwd"()

declare i64 @"sys_read"(i32 %".1", i8* %".2", i64 %".3")

declare i64 @"sys_write"(i32 %".1", i8* %".2", i64 %".3")

declare i32 @"sys_open"(i8* %".1", i32 %".2")

declare i32 @"sys_open3"(i8* %".1", i32 %".2", i32 %".3")

declare i32 @"sys_close"(i32 %".1")

declare i64 @"sys_lseek"(i32 %".1", i64 %".2", i32 %".3")

declare i32 @"sys_ftruncate"(i32 %".1", i64 %".2")

declare i32 @"sys_stat"(i8* %".1", i8* %".2")

declare i32 @"sys_fstat"(i32 %".1", i8* %".2")

declare i32 @"sys_lstat"(i8* %".1", i8* %".2")

declare i32 @"sys_chmod"(i8* %".1", i32 %".2")

declare i32 @"sys_fchmod"(i32 %".1", i32 %".2")

declare i32 @"sys_chown"(i8* %".1", i32 %".2", i32 %".3")

declare i32 @"sys_fchown"(i32 %".1", i32 %".2", i32 %".3")

declare i32 @"sys_access"(i8* %".1", i32 %".2")

declare i32 @"sys_utimensat"(i32 %".1", i8* %".2", i64* %".3", i32 %".4")

declare i32 @"sys_mkdir"(i8* %".1", i32 %".2")

declare i32 @"sys_rmdir"(i8* %".1")

declare i64 @"sys_getcwd"(i8* %".1", i64 %".2")

declare i32 @"sys_chdir"(i8* %".1")

declare i64 @"sys_getdents64"(i32 %".1", i8* %".2", i64 %".3")

declare i32 @"sys_unlink"(i8* %".1")

declare i32 @"sys_rename"(i8* %".1", i8* %".2")

declare i32 @"sys_link"(i8* %".1", i8* %".2")

declare i32 @"sys_symlink"(i8* %".1", i8* %".2")

declare i64 @"sys_readlink"(i8* %".1", i8* %".2", i64 %".3")

declare i8* @"sys_mmap"(i64 %".1", i64 %".2", i32 %".3", i32 %".4", i32 %".5", i64 %".6")

declare i32 @"sys_munmap"(i8* %".1", i64 %".2")

declare i32 @"sys_mprotect"(i8* %".1", i64 %".2", i32 %".3")

declare i32 @"sys_exit"(i32 %".1")

declare i32 @"sys_getpid"()

declare i32 @"sys_getppid"()

declare i32 @"sys_getuid"()

declare i32 @"sys_getgid"()

declare i32 @"sys_geteuid"()

declare i32 @"sys_getegid"()

declare i32 @"sys_fork"()

declare i32 @"sys_execve"(i8* %".1", i8** %".2", i8** %".3")

declare i32 @"sys_wait4"(i32 %".1", i32* %".2", i32 %".3", i8* %".4")

declare i32 @"sys_kill"(i32 %".1", i32 %".2")

declare i32 @"sys_pipe"(i32* %".1")

declare i32 @"sys_dup"(i32 %".1")

declare i32 @"sys_dup2"(i32 %".1", i32 %".2")

declare i32 @"sys_rt_sigaction"(i32 %".1", i8* %".2", i8* %".3", i64 %".4")

declare i32 @"signal_ignore"(i32 %".1")

declare i32 @"sys_nanosleep"(i64* %".1", i64* %".2")

declare i32 @"sys_gettimeofday"(%"struct.ritz_module_1.Timeval"* %".1", i8* %".2")

declare i64 @"sys_sendfile"(i32 %".1", i32 %".2", i64* %".3", i64 %".4")

define i32 @"mem_zero"(i8* %"ptr.arg", i64 %"len.arg") !dbg !17
{
entry:
  %"ptr" = alloca i8*
  %"i" = alloca i64, !dbg !28
  store i8* %"ptr.arg", i8** %"ptr"
  call void @"llvm.dbg.declare"(metadata i8** %"ptr", metadata !25, metadata !7), !dbg !26
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !27, metadata !7), !dbg !26
  %".8" = load i64, i64* %"len", !dbg !28
  store i64 0, i64* %"i", !dbg !28
  br label %"for.cond", !dbg !28
for.cond:
  %".11" = load i64, i64* %"i", !dbg !28
  %".12" = icmp slt i64 %".11", %".8" , !dbg !28
  br i1 %".12", label %"for.body", label %"for.end", !dbg !28
for.body:
  %".14" = load i8*, i8** %"ptr", !dbg !29
  %".15" = load i64, i64* %"i", !dbg !29
  %".16" = getelementptr i8, i8* %".14", i64 %".15" , !dbg !29
  %".17" = trunc i64 0 to i8 , !dbg !29
  store i8 %".17", i8* %".16", !dbg !29
  br label %"for.incr", !dbg !29
for.incr:
  %".20" = load i64, i64* %"i", !dbg !29
  %".21" = add i64 %".20", 1, !dbg !29
  store i64 %".21", i64* %"i", !dbg !29
  br label %"for.cond", !dbg !29
for.end:
  ret i32 0, !dbg !29
}

define i32 @"mem_eq"(i8* %"a.arg", i8* %"b.arg", i64 %"len.arg") !dbg !18
{
entry:
  %"a" = alloca i8*
  %"diff.addr" = alloca i64, !dbg !34
  %"i" = alloca i64, !dbg !37
  store i8* %"a.arg", i8** %"a"
  call void @"llvm.dbg.declare"(metadata i8** %"a", metadata !30, metadata !7), !dbg !31
  %"b" = alloca i8*
  store i8* %"b.arg", i8** %"b"
  call void @"llvm.dbg.declare"(metadata i8** %"b", metadata !32, metadata !7), !dbg !31
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !33, metadata !7), !dbg !31
  store i64 0, i64* %"diff.addr", !dbg !34
  call void @"llvm.dbg.declare"(metadata i64* %"diff.addr", metadata !35, metadata !7), !dbg !36
  %".13" = load i64, i64* %"len", !dbg !37
  store i64 0, i64* %"i", !dbg !37
  br label %"for.cond", !dbg !37
for.cond:
  %".16" = load i64, i64* %"i", !dbg !37
  %".17" = icmp slt i64 %".16", %".13" , !dbg !37
  br i1 %".17", label %"for.body", label %"for.end", !dbg !37
for.body:
  %".19" = load i8*, i8** %"a", !dbg !38
  %".20" = load i64, i64* %"i", !dbg !38
  %".21" = getelementptr i8, i8* %".19", i64 %".20" , !dbg !38
  %".22" = load i8, i8* %".21", !dbg !38
  %".23" = zext i8 %".22" to i64 , !dbg !38
  %".24" = load i8*, i8** %"b", !dbg !39
  %".25" = load i64, i64* %"i", !dbg !39
  %".26" = getelementptr i8, i8* %".24", i64 %".25" , !dbg !39
  %".27" = load i8, i8* %".26", !dbg !39
  %".28" = zext i8 %".27" to i64 , !dbg !39
  %".29" = load i64, i64* %"diff.addr", !dbg !40
  %".30" = xor i64 %".23", %".28", !dbg !40
  %".31" = or i64 %".29", %".30", !dbg !40
  store i64 %".31", i64* %"diff.addr", !dbg !40
  br label %"for.incr", !dbg !40
for.incr:
  %".34" = load i64, i64* %"i", !dbg !40
  %".35" = add i64 %".34", 1, !dbg !40
  store i64 %".35", i64* %"i", !dbg !40
  br label %"for.cond", !dbg !40
for.end:
  %".38" = load i64, i64* %"diff.addr", !dbg !41
  %".39" = call i32 @"ct_is_zero_u64"(i64 %".38"), !dbg !41
  ret i32 %".39", !dbg !41
}

define i32 @"mem_copy"(i8* %"dst.arg", i8* %"src.arg", i64 %"len.arg") !dbg !19
{
entry:
  %"dst" = alloca i8*
  %"i" = alloca i64, !dbg !46
  store i8* %"dst.arg", i8** %"dst"
  call void @"llvm.dbg.declare"(metadata i8** %"dst", metadata !42, metadata !7), !dbg !43
  %"src" = alloca i8*
  store i8* %"src.arg", i8** %"src"
  call void @"llvm.dbg.declare"(metadata i8** %"src", metadata !44, metadata !7), !dbg !43
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !45, metadata !7), !dbg !43
  %".11" = load i64, i64* %"len", !dbg !46
  store i64 0, i64* %"i", !dbg !46
  br label %"for.cond", !dbg !46
for.cond:
  %".14" = load i64, i64* %"i", !dbg !46
  %".15" = icmp slt i64 %".14", %".11" , !dbg !46
  br i1 %".15", label %"for.body", label %"for.end", !dbg !46
for.body:
  %".17" = load i8*, i8** %"src", !dbg !47
  %".18" = load i64, i64* %"i", !dbg !47
  %".19" = getelementptr i8, i8* %".17", i64 %".18" , !dbg !47
  %".20" = load i8, i8* %".19", !dbg !47
  %".21" = load i8*, i8** %"dst", !dbg !47
  %".22" = load i64, i64* %"i", !dbg !47
  %".23" = getelementptr i8, i8* %".21", i64 %".22" , !dbg !47
  store i8 %".20", i8* %".23", !dbg !47
  br label %"for.incr", !dbg !47
for.incr:
  %".26" = load i64, i64* %"i", !dbg !47
  %".27" = add i64 %".26", 1, !dbg !47
  store i64 %".27", i64* %"i", !dbg !47
  br label %"for.cond", !dbg !47
for.end:
  ret i32 0, !dbg !47
}

define i8 @"ct_select_u8"(i8 %"a.arg", i8 %"b.arg", i32 %"condition.arg") !dbg !20
{
entry:
  %"a" = alloca i8
  store i8 %"a.arg", i8* %"a"
  call void @"llvm.dbg.declare"(metadata i8* %"a", metadata !48, metadata !7), !dbg !49
  %"b" = alloca i8
  store i8 %"b.arg", i8* %"b"
  call void @"llvm.dbg.declare"(metadata i8* %"b", metadata !50, metadata !7), !dbg !49
  %"condition" = alloca i32
  store i32 %"condition.arg", i32* %"condition"
  call void @"llvm.dbg.declare"(metadata i32* %"condition", metadata !51, metadata !7), !dbg !49
  %".11" = load i32, i32* %"condition", !dbg !52
  %".12" = zext i32 %".11" to i64 , !dbg !53
  %".13" = sub i64 0, %".12", !dbg !54
  %".14" = or i64 %".12", %".13", !dbg !54
  %".15" = lshr i64 %".14", 63, !dbg !55
  %".16" = sub i64 0, %".15", !dbg !56
  %".17" = load i8, i8* %"a", !dbg !57
  %".18" = zext i8 %".17" to i64 , !dbg !57
  %".19" = load i8, i8* %"b", !dbg !58
  %".20" = zext i8 %".19" to i64 , !dbg !58
  %".21" = and i64 %".18", %".16", !dbg !59
  %".22" = xor i64 %".16", -1, !dbg !59
  %".23" = and i64 %".20", %".22", !dbg !59
  %".24" = or i64 %".21", %".23", !dbg !59
  %".25" = trunc i64 %".24" to i8 , !dbg !60
  ret i8 %".25", !dbg !60
}

define i64 @"ct_select_u64"(i64 %"a.arg", i64 %"b.arg", i32 %"condition.arg") !dbg !21
{
entry:
  %"a" = alloca i64
  store i64 %"a.arg", i64* %"a"
  call void @"llvm.dbg.declare"(metadata i64* %"a", metadata !61, metadata !7), !dbg !62
  %"b" = alloca i64
  store i64 %"b.arg", i64* %"b"
  call void @"llvm.dbg.declare"(metadata i64* %"b", metadata !63, metadata !7), !dbg !62
  %"condition" = alloca i32
  store i32 %"condition.arg", i32* %"condition"
  call void @"llvm.dbg.declare"(metadata i32* %"condition", metadata !64, metadata !7), !dbg !62
  %".11" = load i32, i32* %"condition", !dbg !65
  %".12" = zext i32 %".11" to i64 , !dbg !66
  %".13" = sub i64 0, %".12", !dbg !67
  %".14" = or i64 %".12", %".13", !dbg !67
  %".15" = lshr i64 %".14", 63, !dbg !68
  %".16" = sub i64 0, %".15", !dbg !69
  %".17" = load i64, i64* %"a", !dbg !70
  %".18" = and i64 %".17", %".16", !dbg !70
  %".19" = load i64, i64* %"b", !dbg !70
  %".20" = xor i64 %".16", -1, !dbg !70
  %".21" = and i64 %".19", %".20", !dbg !70
  %".22" = or i64 %".18", %".21", !dbg !70
  ret i64 %".22", !dbg !70
}

define i32 @"ct_is_zero_u64"(i64 %"x.arg") !dbg !22
{
entry:
  %"x" = alloca i64
  store i64 %"x.arg", i64* %"x"
  call void @"llvm.dbg.declare"(metadata i64* %"x", metadata !71, metadata !7), !dbg !72
  %".5" = load i64, i64* %"x", !dbg !73
  %".6" = load i64, i64* %"x", !dbg !73
  %".7" = sub i64 0, %".6", !dbg !73
  %".8" = or i64 %".5", %".7", !dbg !73
  %".9" = lshr i64 %".8", 63, !dbg !74
  %".10" = sub i64 1, %".9", !dbg !75
  %".11" = trunc i64 %".10" to i32 , !dbg !75
  ret i32 %".11", !dbg !75
}

define i32 @"mem_is_zero"(i8* %"ptr.arg", i64 %"len.arg") !dbg !23
{
entry:
  %"ptr" = alloca i8*
  %"acc.addr" = alloca i64, !dbg !81
  %"i" = alloca i64, !dbg !84
  store i8* %"ptr.arg", i8** %"ptr"
  call void @"llvm.dbg.declare"(metadata i8** %"ptr", metadata !76, metadata !7), !dbg !77
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !78, metadata !7), !dbg !77
  %".8" = load i64, i64* %"len", !dbg !79
  %".9" = icmp eq i64 %".8", 0 , !dbg !79
  br i1 %".9", label %"if.then", label %"if.end", !dbg !79
if.then:
  %".11" = trunc i64 1 to i32 , !dbg !80
  ret i32 %".11", !dbg !80
if.end:
  store i64 0, i64* %"acc.addr", !dbg !81
  call void @"llvm.dbg.declare"(metadata i64* %"acc.addr", metadata !82, metadata !7), !dbg !83
  %".15" = load i64, i64* %"len", !dbg !84
  store i64 0, i64* %"i", !dbg !84
  br label %"for.cond", !dbg !84
for.cond:
  %".18" = load i64, i64* %"i", !dbg !84
  %".19" = icmp slt i64 %".18", %".15" , !dbg !84
  br i1 %".19", label %"for.body", label %"for.end", !dbg !84
for.body:
  %".21" = load i64, i64* %"acc.addr", !dbg !85
  %".22" = load i8*, i8** %"ptr", !dbg !85
  %".23" = load i64, i64* %"i", !dbg !85
  %".24" = getelementptr i8, i8* %".22", i64 %".23" , !dbg !85
  %".25" = load i8, i8* %".24", !dbg !85
  %".26" = zext i8 %".25" to i64 , !dbg !85
  %".27" = or i64 %".21", %".26", !dbg !85
  store i64 %".27", i64* %"acc.addr", !dbg !85
  br label %"for.incr", !dbg !85
for.incr:
  %".30" = load i64, i64* %"i", !dbg !85
  %".31" = add i64 %".30", 1, !dbg !85
  store i64 %".31", i64* %"i", !dbg !85
  br label %"for.cond", !dbg !85
for.end:
  %".34" = load i64, i64* %"acc.addr", !dbg !86
  %".35" = call i32 @"ct_is_zero_u64"(i64 %".34"), !dbg !86
  ret i32 %".35", !dbg !86
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/cryptosec/lib", filename: "mem.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 21, name: "mem_zero", scopeLine: 21, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 38, name: "mem_eq", scopeLine: 38, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 56, name: "mem_copy", scopeLine: 56, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 70, name: "ct_select_u8", scopeLine: 70, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 89, name: "ct_select_u64", scopeLine: 89, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 109, name: "ct_is_zero_u64", scopeLine: 109, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 125, name: "mem_is_zero", scopeLine: 125, type: !4, unit: !1)
!24 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!25 = !DILocalVariable(file: !0, line: 21, name: "ptr", scope: !17, type: !24)
!26 = !DILocation(column: 1, line: 21, scope: !17)
!27 = !DILocalVariable(file: !0, line: 21, name: "len", scope: !17, type: !11)
!28 = !DILocation(column: 5, line: 26, scope: !17)
!29 = !DILocation(column: 9, line: 27, scope: !17)
!30 = !DILocalVariable(file: !0, line: 38, name: "a", scope: !18, type: !24)
!31 = !DILocation(column: 1, line: 38, scope: !18)
!32 = !DILocalVariable(file: !0, line: 38, name: "b", scope: !18, type: !24)
!33 = !DILocalVariable(file: !0, line: 38, name: "len", scope: !18, type: !11)
!34 = !DILocation(column: 5, line: 39, scope: !18)
!35 = !DILocalVariable(file: !0, line: 39, name: "diff", scope: !18, type: !15)
!36 = !DILocation(column: 1, line: 39, scope: !18)
!37 = !DILocation(column: 5, line: 43, scope: !18)
!38 = !DILocation(column: 9, line: 44, scope: !18)
!39 = !DILocation(column: 9, line: 45, scope: !18)
!40 = !DILocation(column: 9, line: 46, scope: !18)
!41 = !DILocation(column: 5, line: 50, scope: !18)
!42 = !DILocalVariable(file: !0, line: 56, name: "dst", scope: !19, type: !24)
!43 = !DILocation(column: 1, line: 56, scope: !19)
!44 = !DILocalVariable(file: !0, line: 56, name: "src", scope: !19, type: !24)
!45 = !DILocalVariable(file: !0, line: 56, name: "len", scope: !19, type: !11)
!46 = !DILocation(column: 5, line: 57, scope: !19)
!47 = !DILocation(column: 9, line: 58, scope: !19)
!48 = !DILocalVariable(file: !0, line: 70, name: "a", scope: !20, type: !12)
!49 = !DILocation(column: 1, line: 70, scope: !20)
!50 = !DILocalVariable(file: !0, line: 70, name: "b", scope: !20, type: !12)
!51 = !DILocalVariable(file: !0, line: 70, name: "condition", scope: !20, type: !10)
!52 = !DILocation(column: 5, line: 74, scope: !20)
!53 = !DILocation(column: 5, line: 75, scope: !20)
!54 = !DILocation(column: 5, line: 79, scope: !20)
!55 = !DILocation(column: 5, line: 80, scope: !20)
!56 = !DILocation(column: 5, line: 81, scope: !20)
!57 = !DILocation(column: 5, line: 83, scope: !20)
!58 = !DILocation(column: 5, line: 84, scope: !20)
!59 = !DILocation(column: 5, line: 86, scope: !20)
!60 = !DILocation(column: 5, line: 87, scope: !20)
!61 = !DILocalVariable(file: !0, line: 89, name: "a", scope: !21, type: !15)
!62 = !DILocation(column: 1, line: 89, scope: !21)
!63 = !DILocalVariable(file: !0, line: 89, name: "b", scope: !21, type: !15)
!64 = !DILocalVariable(file: !0, line: 89, name: "condition", scope: !21, type: !10)
!65 = !DILocation(column: 5, line: 91, scope: !21)
!66 = !DILocation(column: 5, line: 92, scope: !21)
!67 = !DILocation(column: 5, line: 94, scope: !21)
!68 = !DILocation(column: 5, line: 95, scope: !21)
!69 = !DILocation(column: 5, line: 96, scope: !21)
!70 = !DILocation(column: 5, line: 98, scope: !21)
!71 = !DILocalVariable(file: !0, line: 109, name: "x", scope: !22, type: !15)
!72 = !DILocation(column: 1, line: 109, scope: !22)
!73 = !DILocation(column: 5, line: 112, scope: !22)
!74 = !DILocation(column: 5, line: 115, scope: !22)
!75 = !DILocation(column: 5, line: 117, scope: !22)
!76 = !DILocalVariable(file: !0, line: 125, name: "ptr", scope: !23, type: !24)
!77 = !DILocation(column: 1, line: 125, scope: !23)
!78 = !DILocalVariable(file: !0, line: 125, name: "len", scope: !23, type: !11)
!79 = !DILocation(column: 5, line: 126, scope: !23)
!80 = !DILocation(column: 9, line: 127, scope: !23)
!81 = !DILocation(column: 5, line: 129, scope: !23)
!82 = !DILocalVariable(file: !0, line: 129, name: "acc", scope: !23, type: !15)
!83 = !DILocation(column: 1, line: 129, scope: !23)
!84 = !DILocation(column: 5, line: 130, scope: !23)
!85 = !DILocation(column: 9, line: 131, scope: !23)
!86 = !DILocation(column: 5, line: 133, scope: !23)