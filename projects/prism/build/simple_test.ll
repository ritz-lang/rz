; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Stat" = type {i64, i64, i64, i32, i32, i32, i32, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64}
%"struct.ritz_module_1.Dirent64" = type {i64, i64, i16, i8}
%"struct.ritz_module_1.Timeval" = type {i64, i64}
%"struct.ritz_module_1.Point" = type {i32, i32}
%"struct.ritz_module_1.Size" = type {i32, i32}
%"struct.ritz_module_1.Rect" = type {i32, i32, i32, i32}
%"struct.ritz_module_1.Color" = type {i32}
%"struct.ritz_module_1.DamageRegion" = type {[16 x %"struct.ritz_module_1.Rect"], i32}
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

define i32 @"test_point_creation"() !dbg !17
{
entry:
  %".2" = trunc i64 10 to i32 , !dbg !47
  %".3" = trunc i64 20 to i32 , !dbg !47
  %".4" = insertvalue %"struct.ritz_module_1.Point" undef, i32 %".2", 0 , !dbg !47
  %".5" = insertvalue %"struct.ritz_module_1.Point" %".4", i32 %".3", 1 , !dbg !47
  %".6" = extractvalue %"struct.ritz_module_1.Point" %".5", 0 , !dbg !48
  %".7" = sext i32 %".6" to i64 , !dbg !48
  %".8" = icmp ne i64 %".7", 10 , !dbg !48
  br i1 %".8", label %"if.then", label %"if.end", !dbg !48
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !49
  ret i32 %".10", !dbg !49
if.end:
  %".12" = extractvalue %"struct.ritz_module_1.Point" %".5", 1 , !dbg !50
  %".13" = sext i32 %".12" to i64 , !dbg !50
  %".14" = icmp ne i64 %".13", 20 , !dbg !50
  br i1 %".14", label %"if.then.1", label %"if.end.1", !dbg !50
if.then.1:
  %".16" = trunc i64 2 to i32 , !dbg !51
  ret i32 %".16", !dbg !51
if.end.1:
  %".18" = trunc i64 0 to i32 , !dbg !52
  ret i32 %".18", !dbg !52
}

define i32 @"test_point_zero"() !dbg !18
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !53
  %".3" = trunc i64 0 to i32 , !dbg !53
  %".4" = insertvalue %"struct.ritz_module_1.Point" undef, i32 %".2", 0 , !dbg !53
  %".5" = insertvalue %"struct.ritz_module_1.Point" %".4", i32 %".3", 1 , !dbg !53
  %".6" = extractvalue %"struct.ritz_module_1.Point" %".5", 0 , !dbg !54
  %".7" = sext i32 %".6" to i64 , !dbg !54
  %".8" = icmp ne i64 %".7", 0 , !dbg !54
  br i1 %".8", label %"if.then", label %"if.end", !dbg !54
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !55
  ret i32 %".10", !dbg !55
if.end:
  %".12" = extractvalue %"struct.ritz_module_1.Point" %".5", 1 , !dbg !56
  %".13" = sext i32 %".12" to i64 , !dbg !56
  %".14" = icmp ne i64 %".13", 0 , !dbg !56
  br i1 %".14", label %"if.then.1", label %"if.end.1", !dbg !56
if.then.1:
  %".16" = trunc i64 2 to i32 , !dbg !57
  ret i32 %".16", !dbg !57
if.end.1:
  %".18" = trunc i64 0 to i32 , !dbg !58
  ret i32 %".18", !dbg !58
}

define i32 @"test_size_creation"() !dbg !19
{
entry:
  %".2" = trunc i64 800 to i32 , !dbg !59
  %".3" = trunc i64 600 to i32 , !dbg !59
  %".4" = insertvalue %"struct.ritz_module_1.Size" undef, i32 %".2", 0 , !dbg !59
  %".5" = insertvalue %"struct.ritz_module_1.Size" %".4", i32 %".3", 1 , !dbg !59
  %".6" = extractvalue %"struct.ritz_module_1.Size" %".5", 0 , !dbg !60
  %".7" = zext i32 %".6" to i64 , !dbg !60
  %".8" = icmp ne i64 %".7", 800 , !dbg !60
  br i1 %".8", label %"if.then", label %"if.end", !dbg !60
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !61
  ret i32 %".10", !dbg !61
if.end:
  %".12" = extractvalue %"struct.ritz_module_1.Size" %".5", 1 , !dbg !62
  %".13" = zext i32 %".12" to i64 , !dbg !62
  %".14" = icmp ne i64 %".13", 600 , !dbg !62
  br i1 %".14", label %"if.then.1", label %"if.end.1", !dbg !62
if.then.1:
  %".16" = trunc i64 2 to i32 , !dbg !63
  ret i32 %".16", !dbg !63
if.end.1:
  %".18" = trunc i64 0 to i32 , !dbg !64
  ret i32 %".18", !dbg !64
}

define i32 @"test_size_area"() !dbg !20
{
entry:
  %".2" = trunc i64 10 to i32 , !dbg !65
  %".3" = trunc i64 20 to i32 , !dbg !65
  %".4" = insertvalue %"struct.ritz_module_1.Size" undef, i32 %".2", 0 , !dbg !65
  %".5" = insertvalue %"struct.ritz_module_1.Size" %".4", i32 %".3", 1 , !dbg !65
  %".6" = extractvalue %"struct.ritz_module_1.Size" %".5", 0 , !dbg !66
  %".7" = extractvalue %"struct.ritz_module_1.Size" %".5", 1 , !dbg !66
  %".8" = mul i32 %".6", %".7", !dbg !66
  %".9" = sext i32 %".8" to i64 , !dbg !67
  %".10" = icmp ne i64 %".9", 200 , !dbg !67
  br i1 %".10", label %"if.then", label %"if.end", !dbg !67
if.then:
  %".12" = trunc i64 1 to i32 , !dbg !68
  ret i32 %".12", !dbg !68
if.end:
  %".14" = trunc i64 0 to i32 , !dbg !69
  ret i32 %".14", !dbg !69
}

define i32 @"test_rect_creation"() !dbg !21
{
entry:
  %".2" = trunc i64 10 to i32 , !dbg !70
  %".3" = trunc i64 20 to i32 , !dbg !70
  %".4" = trunc i64 100 to i32 , !dbg !70
  %".5" = trunc i64 50 to i32 , !dbg !70
  %".6" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".2", 0 , !dbg !70
  %".7" = insertvalue %"struct.ritz_module_1.Rect" %".6", i32 %".3", 1 , !dbg !70
  %".8" = insertvalue %"struct.ritz_module_1.Rect" %".7", i32 %".4", 2 , !dbg !70
  %".9" = insertvalue %"struct.ritz_module_1.Rect" %".8", i32 %".5", 3 , !dbg !70
  %".10" = extractvalue %"struct.ritz_module_1.Rect" %".9", 0 , !dbg !71
  %".11" = sext i32 %".10" to i64 , !dbg !71
  %".12" = icmp ne i64 %".11", 10 , !dbg !71
  br i1 %".12", label %"if.then", label %"if.end", !dbg !71
if.then:
  %".14" = trunc i64 1 to i32 , !dbg !72
  ret i32 %".14", !dbg !72
if.end:
  %".16" = extractvalue %"struct.ritz_module_1.Rect" %".9", 1 , !dbg !73
  %".17" = sext i32 %".16" to i64 , !dbg !73
  %".18" = icmp ne i64 %".17", 20 , !dbg !73
  br i1 %".18", label %"if.then.1", label %"if.end.1", !dbg !73
if.then.1:
  %".20" = trunc i64 2 to i32 , !dbg !74
  ret i32 %".20", !dbg !74
if.end.1:
  %".22" = extractvalue %"struct.ritz_module_1.Rect" %".9", 2 , !dbg !75
  %".23" = zext i32 %".22" to i64 , !dbg !75
  %".24" = icmp ne i64 %".23", 100 , !dbg !75
  br i1 %".24", label %"if.then.2", label %"if.end.2", !dbg !75
if.then.2:
  %".26" = trunc i64 3 to i32 , !dbg !76
  ret i32 %".26", !dbg !76
if.end.2:
  %".28" = extractvalue %"struct.ritz_module_1.Rect" %".9", 3 , !dbg !77
  %".29" = zext i32 %".28" to i64 , !dbg !77
  %".30" = icmp ne i64 %".29", 50 , !dbg !77
  br i1 %".30", label %"if.then.3", label %"if.end.3", !dbg !77
if.then.3:
  %".32" = trunc i64 4 to i32 , !dbg !78
  ret i32 %".32", !dbg !78
if.end.3:
  %".34" = trunc i64 0 to i32 , !dbg !79
  ret i32 %".34", !dbg !79
}

define i32 @"test_rect_contains_point"() !dbg !22
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !80
  %".3" = trunc i64 0 to i32 , !dbg !80
  %".4" = trunc i64 100 to i32 , !dbg !80
  %".5" = trunc i64 100 to i32 , !dbg !80
  %".6" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".2", 0 , !dbg !80
  %".7" = insertvalue %"struct.ritz_module_1.Rect" %".6", i32 %".3", 1 , !dbg !80
  %".8" = insertvalue %"struct.ritz_module_1.Rect" %".7", i32 %".4", 2 , !dbg !80
  %".9" = insertvalue %"struct.ritz_module_1.Rect" %".8", i32 %".5", 3 , !dbg !80
  %".10" = trunc i64 50 to i32 , !dbg !81
  %".11" = trunc i64 50 to i32 , !dbg !82
  %".12" = extractvalue %"struct.ritz_module_1.Rect" %".9", 0 , !dbg !83
  %".13" = icmp slt i32 %".10", %".12" , !dbg !83
  br i1 %".13", label %"or.merge", label %"or.right", !dbg !83
or.right:
  %".15" = extractvalue %"struct.ritz_module_1.Rect" %".9", 0 , !dbg !83
  %".16" = extractvalue %"struct.ritz_module_1.Rect" %".9", 2 , !dbg !83
  %".17" = add i32 %".15", %".16", !dbg !83
  %".18" = icmp sge i32 %".10", %".17" , !dbg !83
  br label %"or.merge", !dbg !83
or.merge:
  %".20" = phi  i1 [1, %"entry"], [%".18", %"or.right"] , !dbg !83
  br i1 %".20", label %"if.then", label %"if.end", !dbg !83
if.then:
  %".22" = trunc i64 1 to i32 , !dbg !84
  ret i32 %".22", !dbg !84
if.end:
  %".24" = extractvalue %"struct.ritz_module_1.Rect" %".9", 1 , !dbg !85
  %".25" = icmp slt i32 %".11", %".24" , !dbg !85
  br i1 %".25", label %"or.merge.1", label %"or.right.1", !dbg !85
or.right.1:
  %".27" = extractvalue %"struct.ritz_module_1.Rect" %".9", 1 , !dbg !85
  %".28" = extractvalue %"struct.ritz_module_1.Rect" %".9", 3 , !dbg !85
  %".29" = add i32 %".27", %".28", !dbg !85
  %".30" = icmp sge i32 %".11", %".29" , !dbg !85
  br label %"or.merge.1", !dbg !85
or.merge.1:
  %".32" = phi  i1 [1, %"if.end"], [%".30", %"or.right.1"] , !dbg !85
  br i1 %".32", label %"if.then.1", label %"if.end.1", !dbg !85
if.then.1:
  %".34" = trunc i64 2 to i32 , !dbg !86
  ret i32 %".34", !dbg !86
if.end.1:
  %".36" = trunc i64 150 to i32 , !dbg !87
  %".37" = extractvalue %"struct.ritz_module_1.Rect" %".9", 0 , !dbg !88
  %".38" = icmp sge i32 %".36", %".37" , !dbg !88
  br i1 %".38", label %"and.right", label %"and.merge", !dbg !88
and.right:
  %".40" = extractvalue %"struct.ritz_module_1.Rect" %".9", 0 , !dbg !88
  %".41" = extractvalue %"struct.ritz_module_1.Rect" %".9", 2 , !dbg !88
  %".42" = add i32 %".40", %".41", !dbg !88
  %".43" = icmp slt i32 %".36", %".42" , !dbg !88
  br label %"and.merge", !dbg !88
and.merge:
  %".45" = phi  i1 [0, %"if.end.1"], [%".43", %"and.right"] , !dbg !88
  br i1 %".45", label %"if.then.2", label %"if.end.2", !dbg !88
if.then.2:
  %".47" = trunc i64 3 to i32 , !dbg !89
  ret i32 %".47", !dbg !89
if.end.2:
  %".49" = trunc i64 0 to i32 , !dbg !90
  ret i32 %".49", !dbg !90
}

define %"struct.ritz_module_1.Color" @"color_rgb"(i8 %"r.arg", i8 %"g.arg", i8 %"b.arg") !dbg !23
{
entry:
  %"r" = alloca i8
  store i8 %"r.arg", i8* %"r"
  call void @"llvm.dbg.declare"(metadata i8* %"r", metadata !91, metadata !7), !dbg !92
  %"g" = alloca i8
  store i8 %"g.arg", i8* %"g"
  call void @"llvm.dbg.declare"(metadata i8* %"g", metadata !93, metadata !7), !dbg !92
  %"b" = alloca i8
  store i8 %"b.arg", i8* %"b"
  call void @"llvm.dbg.declare"(metadata i8* %"b", metadata !94, metadata !7), !dbg !92
  %".11" = load i8, i8* %"r", !dbg !95
  %".12" = zext i8 %".11" to i32 , !dbg !95
  %".13" = load i8, i8* %"g", !dbg !96
  %".14" = zext i8 %".13" to i32 , !dbg !96
  %".15" = load i8, i8* %"b", !dbg !97
  %".16" = zext i8 %".15" to i32 , !dbg !97
  %".17" = zext i32 %".12" to i64 , !dbg !98
  %".18" = shl i64 %".17", 16, !dbg !98
  %".19" = add i64 4278190080, %".18", !dbg !98
  %".20" = zext i32 %".14" to i64 , !dbg !98
  %".21" = shl i64 %".20", 8, !dbg !98
  %".22" = add i64 %".19", %".21", !dbg !98
  %".23" = zext i32 %".16" to i64 , !dbg !98
  %".24" = add i64 %".22", %".23", !dbg !98
  %".25" = trunc i64 %".24" to i32 , !dbg !98
  %".26" = insertvalue %"struct.ritz_module_1.Color" undef, i32 %".25", 0 , !dbg !98
  ret %"struct.ritz_module_1.Color" %".26", !dbg !98
}

define i8 @"color_r"(%"struct.ritz_module_1.Color"* %"c.arg") !dbg !24
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Color"* %"c.arg", metadata !101, metadata !7), !dbg !102
  %".4" = getelementptr %"struct.ritz_module_1.Color", %"struct.ritz_module_1.Color"* %"c.arg", i32 0, i32 0 , !dbg !103
  %".5" = load i32, i32* %".4", !dbg !103
  %".6" = sext i32 %".5" to i64 , !dbg !103
  %".7" = ashr i64 %".6", 16, !dbg !103
  %".8" = srem i64 %".7", 256, !dbg !103
  %".9" = trunc i64 %".8" to i8 , !dbg !103
  ret i8 %".9", !dbg !103
}

define i8 @"color_g"(%"struct.ritz_module_1.Color"* %"c.arg") !dbg !25
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Color"* %"c.arg", metadata !104, metadata !7), !dbg !105
  %".4" = getelementptr %"struct.ritz_module_1.Color", %"struct.ritz_module_1.Color"* %"c.arg", i32 0, i32 0 , !dbg !106
  %".5" = load i32, i32* %".4", !dbg !106
  %".6" = sext i32 %".5" to i64 , !dbg !106
  %".7" = ashr i64 %".6", 8, !dbg !106
  %".8" = srem i64 %".7", 256, !dbg !106
  %".9" = trunc i64 %".8" to i8 , !dbg !106
  ret i8 %".9", !dbg !106
}

define i8 @"color_b"(%"struct.ritz_module_1.Color"* %"c.arg") !dbg !26
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Color"* %"c.arg", metadata !107, metadata !7), !dbg !108
  %".4" = getelementptr %"struct.ritz_module_1.Color", %"struct.ritz_module_1.Color"* %"c.arg", i32 0, i32 0 , !dbg !109
  %".5" = load i32, i32* %".4", !dbg !109
  %".6" = sext i32 %".5" to i64 , !dbg !109
  %".7" = srem i64 %".6", 256, !dbg !109
  %".8" = trunc i64 %".7" to i8 , !dbg !109
  ret i8 %".8", !dbg !109
}

define i32 @"test_color_rgb"() !dbg !27
{
entry:
  %".2" = trunc i64 255 to i8 , !dbg !110
  %".3" = trunc i64 128 to i8 , !dbg !110
  %".4" = trunc i64 64 to i8 , !dbg !110
  %".5" = call %"struct.ritz_module_1.Color" @"color_rgb"(i8 %".2", i8 %".3", i8 %".4"), !dbg !110
  %"c.addr" = alloca %"struct.ritz_module_1.Color", !dbg !111
  store %"struct.ritz_module_1.Color" %".5", %"struct.ritz_module_1.Color"* %"c.addr", !dbg !111
  %".7" = call i8 @"color_r"(%"struct.ritz_module_1.Color"* %"c.addr"), !dbg !111
  %".8" = zext i8 %".7" to i32 , !dbg !111
  %".9" = zext i32 %".8" to i64 , !dbg !111
  %".10" = icmp ne i64 %".9", 255 , !dbg !111
  br i1 %".10", label %"if.then", label %"if.end", !dbg !111
if.then:
  %".12" = trunc i64 1 to i32 , !dbg !112
  ret i32 %".12", !dbg !112
if.end:
  %"c.addr.1" = alloca %"struct.ritz_module_1.Color", !dbg !113
  store %"struct.ritz_module_1.Color" %".5", %"struct.ritz_module_1.Color"* %"c.addr.1", !dbg !113
  %".15" = call i8 @"color_g"(%"struct.ritz_module_1.Color"* %"c.addr.1"), !dbg !113
  %".16" = zext i8 %".15" to i32 , !dbg !113
  %".17" = zext i32 %".16" to i64 , !dbg !113
  %".18" = icmp ne i64 %".17", 128 , !dbg !113
  br i1 %".18", label %"if.then.1", label %"if.end.1", !dbg !113
if.then.1:
  %".20" = trunc i64 2 to i32 , !dbg !114
  ret i32 %".20", !dbg !114
if.end.1:
  %"c.addr.2" = alloca %"struct.ritz_module_1.Color", !dbg !115
  store %"struct.ritz_module_1.Color" %".5", %"struct.ritz_module_1.Color"* %"c.addr.2", !dbg !115
  %".23" = call i8 @"color_b"(%"struct.ritz_module_1.Color"* %"c.addr.2"), !dbg !115
  %".24" = zext i8 %".23" to i32 , !dbg !115
  %".25" = zext i32 %".24" to i64 , !dbg !115
  %".26" = icmp ne i64 %".25", 64 , !dbg !115
  br i1 %".26", label %"if.then.2", label %"if.end.2", !dbg !115
if.then.2:
  %".28" = trunc i64 3 to i32 , !dbg !116
  ret i32 %".28", !dbg !116
if.end.2:
  %".30" = trunc i64 0 to i32 , !dbg !117
  ret i32 %".30", !dbg !117
}

define i32 @"test_color_black"() !dbg !28
{
entry:
  %".2" = trunc i64 0 to i8 , !dbg !118
  %".3" = trunc i64 0 to i8 , !dbg !118
  %".4" = trunc i64 0 to i8 , !dbg !118
  %".5" = call %"struct.ritz_module_1.Color" @"color_rgb"(i8 %".2", i8 %".3", i8 %".4"), !dbg !118
  %"c.addr" = alloca %"struct.ritz_module_1.Color", !dbg !119
  store %"struct.ritz_module_1.Color" %".5", %"struct.ritz_module_1.Color"* %"c.addr", !dbg !119
  %".7" = call i8 @"color_r"(%"struct.ritz_module_1.Color"* %"c.addr"), !dbg !119
  %".8" = zext i8 %".7" to i32 , !dbg !119
  %".9" = zext i32 %".8" to i64 , !dbg !119
  %".10" = icmp ne i64 %".9", 0 , !dbg !119
  br i1 %".10", label %"if.then", label %"if.end", !dbg !119
if.then:
  %".12" = trunc i64 1 to i32 , !dbg !120
  ret i32 %".12", !dbg !120
if.end:
  %"c.addr.1" = alloca %"struct.ritz_module_1.Color", !dbg !121
  store %"struct.ritz_module_1.Color" %".5", %"struct.ritz_module_1.Color"* %"c.addr.1", !dbg !121
  %".15" = call i8 @"color_g"(%"struct.ritz_module_1.Color"* %"c.addr.1"), !dbg !121
  %".16" = zext i8 %".15" to i32 , !dbg !121
  %".17" = zext i32 %".16" to i64 , !dbg !121
  %".18" = icmp ne i64 %".17", 0 , !dbg !121
  br i1 %".18", label %"if.then.1", label %"if.end.1", !dbg !121
if.then.1:
  %".20" = trunc i64 2 to i32 , !dbg !122
  ret i32 %".20", !dbg !122
if.end.1:
  %"c.addr.2" = alloca %"struct.ritz_module_1.Color", !dbg !123
  store %"struct.ritz_module_1.Color" %".5", %"struct.ritz_module_1.Color"* %"c.addr.2", !dbg !123
  %".23" = call i8 @"color_b"(%"struct.ritz_module_1.Color"* %"c.addr.2"), !dbg !123
  %".24" = zext i8 %".23" to i32 , !dbg !123
  %".25" = zext i32 %".24" to i64 , !dbg !123
  %".26" = icmp ne i64 %".25", 0 , !dbg !123
  br i1 %".26", label %"if.then.2", label %"if.end.2", !dbg !123
if.then.2:
  %".28" = trunc i64 3 to i32 , !dbg !124
  ret i32 %".28", !dbg !124
if.end.2:
  %".30" = trunc i64 0 to i32 , !dbg !125
  ret i32 %".30", !dbg !125
}

define i32 @"test_color_white"() !dbg !29
{
entry:
  %".2" = trunc i64 255 to i8 , !dbg !126
  %".3" = trunc i64 255 to i8 , !dbg !126
  %".4" = trunc i64 255 to i8 , !dbg !126
  %".5" = call %"struct.ritz_module_1.Color" @"color_rgb"(i8 %".2", i8 %".3", i8 %".4"), !dbg !126
  %"c.addr" = alloca %"struct.ritz_module_1.Color", !dbg !127
  store %"struct.ritz_module_1.Color" %".5", %"struct.ritz_module_1.Color"* %"c.addr", !dbg !127
  %".7" = call i8 @"color_r"(%"struct.ritz_module_1.Color"* %"c.addr"), !dbg !127
  %".8" = zext i8 %".7" to i32 , !dbg !127
  %".9" = zext i32 %".8" to i64 , !dbg !127
  %".10" = icmp ne i64 %".9", 255 , !dbg !127
  br i1 %".10", label %"if.then", label %"if.end", !dbg !127
if.then:
  %".12" = trunc i64 1 to i32 , !dbg !128
  ret i32 %".12", !dbg !128
if.end:
  %"c.addr.1" = alloca %"struct.ritz_module_1.Color", !dbg !129
  store %"struct.ritz_module_1.Color" %".5", %"struct.ritz_module_1.Color"* %"c.addr.1", !dbg !129
  %".15" = call i8 @"color_g"(%"struct.ritz_module_1.Color"* %"c.addr.1"), !dbg !129
  %".16" = zext i8 %".15" to i32 , !dbg !129
  %".17" = zext i32 %".16" to i64 , !dbg !129
  %".18" = icmp ne i64 %".17", 255 , !dbg !129
  br i1 %".18", label %"if.then.1", label %"if.end.1", !dbg !129
if.then.1:
  %".20" = trunc i64 2 to i32 , !dbg !130
  ret i32 %".20", !dbg !130
if.end.1:
  %"c.addr.2" = alloca %"struct.ritz_module_1.Color", !dbg !131
  store %"struct.ritz_module_1.Color" %".5", %"struct.ritz_module_1.Color"* %"c.addr.2", !dbg !131
  %".23" = call i8 @"color_b"(%"struct.ritz_module_1.Color"* %"c.addr.2"), !dbg !131
  %".24" = zext i8 %".23" to i32 , !dbg !131
  %".25" = zext i32 %".24" to i64 , !dbg !131
  %".26" = icmp ne i64 %".25", 255 , !dbg !131
  br i1 %".26", label %"if.then.2", label %"if.end.2", !dbg !131
if.then.2:
  %".28" = trunc i64 3 to i32 , !dbg !132
  ret i32 %".28", !dbg !132
if.end.2:
  %".30" = trunc i64 0 to i32 , !dbg !133
  ret i32 %".30", !dbg !133
}

define %"struct.ritz_module_1.DamageRegion" @"damage_region_new"() !dbg !30
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !134
  %".3" = trunc i64 0 to i32 , !dbg !134
  %".4" = trunc i64 0 to i32 , !dbg !134
  %".5" = trunc i64 0 to i32 , !dbg !134
  %".6" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".2", 0 , !dbg !134
  %".7" = insertvalue %"struct.ritz_module_1.Rect" %".6", i32 %".3", 1 , !dbg !134
  %".8" = insertvalue %"struct.ritz_module_1.Rect" %".7", i32 %".4", 2 , !dbg !134
  %".9" = insertvalue %"struct.ritz_module_1.Rect" %".8", i32 %".5", 3 , !dbg !134
  %".10" = insertvalue [16 x %"struct.ritz_module_1.Rect"] undef, %"struct.ritz_module_1.Rect" %".9", 0 , !dbg !134
  %".11" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".10", %"struct.ritz_module_1.Rect" %".9", 1 , !dbg !134
  %".12" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".11", %"struct.ritz_module_1.Rect" %".9", 2 , !dbg !134
  %".13" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".12", %"struct.ritz_module_1.Rect" %".9", 3 , !dbg !134
  %".14" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".13", %"struct.ritz_module_1.Rect" %".9", 4 , !dbg !134
  %".15" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".14", %"struct.ritz_module_1.Rect" %".9", 5 , !dbg !134
  %".16" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".15", %"struct.ritz_module_1.Rect" %".9", 6 , !dbg !134
  %".17" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".16", %"struct.ritz_module_1.Rect" %".9", 7 , !dbg !134
  %".18" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".17", %"struct.ritz_module_1.Rect" %".9", 8 , !dbg !134
  %".19" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".18", %"struct.ritz_module_1.Rect" %".9", 9 , !dbg !134
  %".20" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".19", %"struct.ritz_module_1.Rect" %".9", 10 , !dbg !134
  %".21" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".20", %"struct.ritz_module_1.Rect" %".9", 11 , !dbg !134
  %".22" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".21", %"struct.ritz_module_1.Rect" %".9", 12 , !dbg !134
  %".23" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".22", %"struct.ritz_module_1.Rect" %".9", 13 , !dbg !134
  %".24" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".23", %"struct.ritz_module_1.Rect" %".9", 14 , !dbg !134
  %".25" = insertvalue [16 x %"struct.ritz_module_1.Rect"] %".24", %"struct.ritz_module_1.Rect" %".9", 15 , !dbg !134
  %".26" = trunc i64 0 to i32 , !dbg !134
  %".27" = insertvalue %"struct.ritz_module_1.DamageRegion" undef, [16 x %"struct.ritz_module_1.Rect"] %".25", 0 , !dbg !134
  %".28" = insertvalue %"struct.ritz_module_1.DamageRegion" %".27", i32 %".26", 1 , !dbg !134
  ret %"struct.ritz_module_1.DamageRegion" %".28", !dbg !134
}

define i32 @"damage_region_add"(%"struct.ritz_module_1.DamageRegion"* %"region.arg", %"struct.ritz_module_1.Rect" %"r.arg") !dbg !31
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.DamageRegion"* %"region.arg", metadata !136, metadata !7), !dbg !137
  %"r" = alloca %"struct.ritz_module_1.Rect"
  store %"struct.ritz_module_1.Rect" %"r.arg", %"struct.ritz_module_1.Rect"* %"r"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"r", metadata !139, metadata !7), !dbg !137
  %".7" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !140
  %".8" = load i32, i32* %".7", !dbg !140
  %".9" = zext i32 %".8" to i64 , !dbg !140
  %".10" = icmp ult i64 %".9", 16 , !dbg !140
  br i1 %".10", label %"if.then", label %"if.end", !dbg !140
if.then:
  %".12" = load %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"r", !dbg !141
  %".13" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !141
  %".14" = load i32, i32* %".13", !dbg !141
  %".15" = zext i32 %".14" to i64 , !dbg !141
  %".16" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 0 , !dbg !141
  %".17" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".16", i32 0, i64 %".15" , !dbg !141
  store %"struct.ritz_module_1.Rect" %".12", %"struct.ritz_module_1.Rect"* %".17", !dbg !141
  %".19" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !142
  %".20" = load i32, i32* %".19", !dbg !142
  %".21" = zext i32 %".20" to i64 , !dbg !142
  %".22" = add i64 %".21", 1, !dbg !142
  %".23" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", !dbg !142
  %".24" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !142
  %".25" = trunc i64 %".22" to i32 , !dbg !142
  store i32 %".25", i32* %".24", !dbg !142
  br label %"if.end", !dbg !142
if.end:
  ret i32 0, !dbg !142
}

define i32 @"damage_region_clear"(%"struct.ritz_module_1.DamageRegion"* %"region.arg") !dbg !32
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.DamageRegion"* %"region.arg", metadata !143, metadata !7), !dbg !144
  %".4" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", !dbg !145
  %".5" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !145
  %".6" = trunc i64 0 to i32 , !dbg !145
  store i32 %".6", i32* %".5", !dbg !145
  ret i32 0, !dbg !145
}

define i1 @"damage_region_is_empty"(%"struct.ritz_module_1.DamageRegion"* %"region.arg") !dbg !33
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.DamageRegion"* %"region.arg", metadata !147, metadata !7), !dbg !148
  %".4" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !149
  %".5" = load i32, i32* %".4", !dbg !149
  %".6" = sext i32 %".5" to i64 , !dbg !149
  %".7" = icmp eq i64 %".6", 0 , !dbg !149
  ret i1 %".7", !dbg !149
}

define i1 @"rects_intersect"(%"struct.ritz_module_1.Rect"* %"a.arg", %"struct.ritz_module_1.Rect"* %"b.arg") !dbg !34
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"a.arg", metadata !151, metadata !7), !dbg !152
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"b.arg", metadata !153, metadata !7), !dbg !152
  %".6" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 0 , !dbg !154
  %".7" = load i32, i32* %".6", !dbg !154
  %".8" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 2 , !dbg !154
  %".9" = load i32, i32* %".8", !dbg !154
  %".10" = add i32 %".7", %".9", !dbg !154
  %".11" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 1 , !dbg !155
  %".12" = load i32, i32* %".11", !dbg !155
  %".13" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 3 , !dbg !155
  %".14" = load i32, i32* %".13", !dbg !155
  %".15" = add i32 %".12", %".14", !dbg !155
  %".16" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 0 , !dbg !156
  %".17" = load i32, i32* %".16", !dbg !156
  %".18" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 2 , !dbg !156
  %".19" = load i32, i32* %".18", !dbg !156
  %".20" = add i32 %".17", %".19", !dbg !156
  %".21" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 1 , !dbg !157
  %".22" = load i32, i32* %".21", !dbg !157
  %".23" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 3 , !dbg !157
  %".24" = load i32, i32* %".23", !dbg !157
  %".25" = add i32 %".22", %".24", !dbg !157
  %".26" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 0 , !dbg !158
  %".27" = load i32, i32* %".26", !dbg !158
  %".28" = icmp slt i32 %".27", %".20" , !dbg !158
  br i1 %".28", label %"and.right", label %"and.merge", !dbg !158
and.right:
  %".30" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 0 , !dbg !158
  %".31" = load i32, i32* %".30", !dbg !158
  %".32" = icmp sgt i32 %".10", %".31" , !dbg !158
  br label %"and.merge", !dbg !158
and.merge:
  %".34" = phi  i1 [0, %"entry"], [%".32", %"and.right"] , !dbg !158
  br i1 %".34", label %"and.right.1", label %"and.merge.1", !dbg !158
and.right.1:
  %".36" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 1 , !dbg !158
  %".37" = load i32, i32* %".36", !dbg !158
  %".38" = icmp slt i32 %".37", %".25" , !dbg !158
  br label %"and.merge.1", !dbg !158
and.merge.1:
  %".40" = phi  i1 [0, %"and.merge"], [%".38", %"and.right.1"] , !dbg !158
  br i1 %".40", label %"and.right.2", label %"and.merge.2", !dbg !158
and.right.2:
  %".42" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 1 , !dbg !158
  %".43" = load i32, i32* %".42", !dbg !158
  %".44" = icmp sgt i32 %".15", %".43" , !dbg !158
  br label %"and.merge.2", !dbg !158
and.merge.2:
  %".46" = phi  i1 [0, %"and.merge.1"], [%".44", %"and.right.2"] , !dbg !158
  ret i1 %".46", !dbg !158
}

define i32 @"min_i32"(i32 %"a.arg", i32 %"b.arg") !dbg !35
{
entry:
  %"a" = alloca i32
  store i32 %"a.arg", i32* %"a"
  call void @"llvm.dbg.declare"(metadata i32* %"a", metadata !159, metadata !7), !dbg !160
  %"b" = alloca i32
  store i32 %"b.arg", i32* %"b"
  call void @"llvm.dbg.declare"(metadata i32* %"b", metadata !161, metadata !7), !dbg !160
  %".8" = load i32, i32* %"a", !dbg !162
  %".9" = load i32, i32* %"b", !dbg !162
  %".10" = icmp slt i32 %".8", %".9" , !dbg !162
  br i1 %".10", label %"if.then", label %"if.end", !dbg !162
if.then:
  %".12" = load i32, i32* %"a", !dbg !163
  ret i32 %".12", !dbg !163
if.end:
  %".14" = load i32, i32* %"b", !dbg !164
  ret i32 %".14", !dbg !164
}

define i32 @"max_i32"(i32 %"a.arg", i32 %"b.arg") !dbg !36
{
entry:
  %"a" = alloca i32
  store i32 %"a.arg", i32* %"a"
  call void @"llvm.dbg.declare"(metadata i32* %"a", metadata !165, metadata !7), !dbg !166
  %"b" = alloca i32
  store i32 %"b.arg", i32* %"b"
  call void @"llvm.dbg.declare"(metadata i32* %"b", metadata !167, metadata !7), !dbg !166
  %".8" = load i32, i32* %"a", !dbg !168
  %".9" = load i32, i32* %"b", !dbg !168
  %".10" = icmp sgt i32 %".8", %".9" , !dbg !168
  br i1 %".10", label %"if.then", label %"if.end", !dbg !168
if.then:
  %".12" = load i32, i32* %"a", !dbg !169
  ret i32 %".12", !dbg !169
if.end:
  %".14" = load i32, i32* %"b", !dbg !170
  ret i32 %".14", !dbg !170
}

define %"struct.ritz_module_1.Rect" @"rect_union"(%"struct.ritz_module_1.Rect"* %"a.arg", %"struct.ritz_module_1.Rect"* %"b.arg") !dbg !37
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"a.arg", metadata !171, metadata !7), !dbg !172
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Rect"* %"b.arg", metadata !173, metadata !7), !dbg !172
  %".6" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 0 , !dbg !174
  %".7" = load i32, i32* %".6", !dbg !174
  %".8" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 0 , !dbg !174
  %".9" = load i32, i32* %".8", !dbg !174
  %".10" = call i32 @"min_i32"(i32 %".7", i32 %".9"), !dbg !174
  %".11" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 1 , !dbg !175
  %".12" = load i32, i32* %".11", !dbg !175
  %".13" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 1 , !dbg !175
  %".14" = load i32, i32* %".13", !dbg !175
  %".15" = call i32 @"min_i32"(i32 %".12", i32 %".14"), !dbg !175
  %".16" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 0 , !dbg !176
  %".17" = load i32, i32* %".16", !dbg !176
  %".18" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 2 , !dbg !176
  %".19" = load i32, i32* %".18", !dbg !176
  %".20" = add i32 %".17", %".19", !dbg !176
  %".21" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 0 , !dbg !177
  %".22" = load i32, i32* %".21", !dbg !177
  %".23" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 2 , !dbg !177
  %".24" = load i32, i32* %".23", !dbg !177
  %".25" = add i32 %".22", %".24", !dbg !177
  %".26" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 1 , !dbg !178
  %".27" = load i32, i32* %".26", !dbg !178
  %".28" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"a.arg", i32 0, i32 3 , !dbg !178
  %".29" = load i32, i32* %".28", !dbg !178
  %".30" = add i32 %".27", %".29", !dbg !178
  %".31" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 1 , !dbg !179
  %".32" = load i32, i32* %".31", !dbg !179
  %".33" = getelementptr %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"b.arg", i32 0, i32 3 , !dbg !179
  %".34" = load i32, i32* %".33", !dbg !179
  %".35" = add i32 %".32", %".34", !dbg !179
  %".36" = call i32 @"max_i32"(i32 %".20", i32 %".25"), !dbg !180
  %".37" = call i32 @"max_i32"(i32 %".30", i32 %".35"), !dbg !181
  %".38" = sub i32 %".36", %".10", !dbg !182
  %".39" = sub i32 %".37", %".15", !dbg !182
  %".40" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".10", 0 , !dbg !182
  %".41" = insertvalue %"struct.ritz_module_1.Rect" %".40", i32 %".15", 1 , !dbg !182
  %".42" = insertvalue %"struct.ritz_module_1.Rect" %".41", i32 %".38", 2 , !dbg !182
  %".43" = insertvalue %"struct.ritz_module_1.Rect" %".42", i32 %".39", 3 , !dbg !182
  ret %"struct.ritz_module_1.Rect" %".43", !dbg !182
}

define %"struct.ritz_module_1.Rect" @"damage_region_bounds"(%"struct.ritz_module_1.DamageRegion"* %"region.arg") !dbg !38
{
entry:
  %"bounds.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !187
  %"i.addr" = alloca i32, !dbg !188
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.DamageRegion"* %"region.arg", metadata !183, metadata !7), !dbg !184
  %".4" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !185
  %".5" = load i32, i32* %".4", !dbg !185
  %".6" = sext i32 %".5" to i64 , !dbg !185
  %".7" = icmp eq i64 %".6", 0 , !dbg !185
  br i1 %".7", label %"if.then", label %"if.end", !dbg !185
if.then:
  %".9" = trunc i64 0 to i32 , !dbg !186
  %".10" = trunc i64 0 to i32 , !dbg !186
  %".11" = trunc i64 0 to i32 , !dbg !186
  %".12" = trunc i64 0 to i32 , !dbg !186
  %".13" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".9", 0 , !dbg !186
  %".14" = insertvalue %"struct.ritz_module_1.Rect" %".13", i32 %".10", 1 , !dbg !186
  %".15" = insertvalue %"struct.ritz_module_1.Rect" %".14", i32 %".11", 2 , !dbg !186
  %".16" = insertvalue %"struct.ritz_module_1.Rect" %".15", i32 %".12", 3 , !dbg !186
  ret %"struct.ritz_module_1.Rect" %".16", !dbg !186
if.end:
  %".18" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 0 , !dbg !187
  %".19" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".18", i32 0, i64 0 , !dbg !187
  %".20" = load %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %".19", !dbg !187
  store %"struct.ritz_module_1.Rect" %".20", %"struct.ritz_module_1.Rect"* %"bounds.addr", !dbg !187
  %".22" = trunc i64 1 to i32 , !dbg !188
  store i32 %".22", i32* %"i.addr", !dbg !188
  call void @"llvm.dbg.declare"(metadata i32* %"i.addr", metadata !189, metadata !7), !dbg !190
  br label %"while.cond", !dbg !191
while.cond:
  %".26" = load i32, i32* %"i.addr", !dbg !191
  %".27" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 1 , !dbg !191
  %".28" = load i32, i32* %".27", !dbg !191
  %".29" = icmp ult i32 %".26", %".28" , !dbg !191
  br i1 %".29", label %"while.body", label %"while.end", !dbg !191
while.body:
  %".31" = load i32, i32* %"i.addr", !dbg !192
  %".32" = zext i32 %".31" to i64 , !dbg !192
  %".33" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.arg", i32 0, i32 0 , !dbg !192
  %".34" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".33", i32 0, i64 %".32" , !dbg !192
  %".35" = call %"struct.ritz_module_1.Rect" @"rect_union"(%"struct.ritz_module_1.Rect"* %"bounds.addr", %"struct.ritz_module_1.Rect"* %".34"), !dbg !192
  store %"struct.ritz_module_1.Rect" %".35", %"struct.ritz_module_1.Rect"* %"bounds.addr", !dbg !192
  %".37" = load i32, i32* %"i.addr", !dbg !193
  %".38" = zext i32 %".37" to i64 , !dbg !193
  %".39" = add i64 %".38", 1, !dbg !193
  %".40" = trunc i64 %".39" to i32 , !dbg !193
  store i32 %".40", i32* %"i.addr", !dbg !193
  br label %"while.cond", !dbg !193
while.end:
  %".43" = load %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %"bounds.addr", !dbg !194
  ret %"struct.ritz_module_1.Rect" %".43", !dbg !194
}

define i32 @"test_damage_region_new"() !dbg !39
{
entry:
  %".2" = call %"struct.ritz_module_1.DamageRegion" @"damage_region_new"(), !dbg !195
  %".3" = extractvalue %"struct.ritz_module_1.DamageRegion" %".2", 1 , !dbg !196
  %".4" = zext i32 %".3" to i64 , !dbg !196
  %".5" = icmp ne i64 %".4", 0 , !dbg !196
  br i1 %".5", label %"if.then", label %"if.end", !dbg !196
if.then:
  %".7" = trunc i64 1 to i32 , !dbg !197
  ret i32 %".7", !dbg !197
if.end:
  %"region.addr" = alloca %"struct.ritz_module_1.DamageRegion", !dbg !198
  store %"struct.ritz_module_1.DamageRegion" %".2", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !198
  %".10" = call i1 @"damage_region_is_empty"(%"struct.ritz_module_1.DamageRegion"* %"region.addr"), !dbg !198
  %".11" = icmp eq i1 %".10", 0 , !dbg !198
  br i1 %".11", label %"if.then.1", label %"if.end.1", !dbg !198
if.then.1:
  %".13" = trunc i64 2 to i32 , !dbg !199
  ret i32 %".13", !dbg !199
if.end.1:
  %".15" = trunc i64 0 to i32 , !dbg !200
  ret i32 %".15", !dbg !200
}

define i32 @"test_damage_region_add"() !dbg !40
{
entry:
  %"region.addr" = alloca %"struct.ritz_module_1.DamageRegion", !dbg !201
  %".2" = call %"struct.ritz_module_1.DamageRegion" @"damage_region_new"(), !dbg !201
  store %"struct.ritz_module_1.DamageRegion" %".2", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !201
  %".4" = trunc i64 10 to i32 , !dbg !202
  %".5" = trunc i64 20 to i32 , !dbg !202
  %".6" = trunc i64 30 to i32 , !dbg !202
  %".7" = trunc i64 40 to i32 , !dbg !202
  %".8" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".4", 0 , !dbg !202
  %".9" = insertvalue %"struct.ritz_module_1.Rect" %".8", i32 %".5", 1 , !dbg !202
  %".10" = insertvalue %"struct.ritz_module_1.Rect" %".9", i32 %".6", 2 , !dbg !202
  %".11" = insertvalue %"struct.ritz_module_1.Rect" %".10", i32 %".7", 3 , !dbg !202
  %".12" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !203
  %".13" = load i32, i32* %".12", !dbg !203
  %".14" = zext i32 %".13" to i64 , !dbg !203
  %".15" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !203
  %".16" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".15", i32 0, i64 %".14" , !dbg !203
  store %"struct.ritz_module_1.Rect" %".11", %"struct.ritz_module_1.Rect"* %".16", !dbg !203
  %".18" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !204
  %".19" = load i32, i32* %".18", !dbg !204
  %".20" = zext i32 %".19" to i64 , !dbg !204
  %".21" = add i64 %".20", 1, !dbg !204
  %".22" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !204
  %".23" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !204
  %".24" = trunc i64 %".21" to i32 , !dbg !204
  store i32 %".24", i32* %".23", !dbg !204
  %".26" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !205
  %".27" = load i32, i32* %".26", !dbg !205
  %".28" = zext i32 %".27" to i64 , !dbg !205
  %".29" = icmp ne i64 %".28", 1 , !dbg !205
  br i1 %".29", label %"if.then", label %"if.end", !dbg !205
if.then:
  %".31" = trunc i64 1 to i32 , !dbg !206
  ret i32 %".31", !dbg !206
if.end:
  %".33" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !207
  %".34" = load i32, i32* %".33", !dbg !207
  %".35" = zext i32 %".34" to i64 , !dbg !207
  %".36" = icmp eq i64 %".35", 0 , !dbg !207
  br i1 %".36", label %"if.then.1", label %"if.end.1", !dbg !207
if.then.1:
  %".38" = trunc i64 2 to i32 , !dbg !208
  ret i32 %".38", !dbg !208
if.end.1:
  %".40" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !209
  %".41" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".40", i32 0, i64 0 , !dbg !209
  %".42" = load %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %".41", !dbg !209
  %".43" = extractvalue %"struct.ritz_module_1.Rect" %".42", 0 , !dbg !209
  %".44" = sext i32 %".43" to i64 , !dbg !209
  %".45" = icmp ne i64 %".44", 10 , !dbg !209
  br i1 %".45", label %"if.then.2", label %"if.end.2", !dbg !209
if.then.2:
  %".47" = trunc i64 3 to i32 , !dbg !210
  ret i32 %".47", !dbg !210
if.end.2:
  %".49" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !211
  %".50" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".49", i32 0, i64 0 , !dbg !211
  %".51" = load %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %".50", !dbg !211
  %".52" = extractvalue %"struct.ritz_module_1.Rect" %".51", 1 , !dbg !211
  %".53" = sext i32 %".52" to i64 , !dbg !211
  %".54" = icmp ne i64 %".53", 20 , !dbg !211
  br i1 %".54", label %"if.then.3", label %"if.end.3", !dbg !211
if.then.3:
  %".56" = trunc i64 4 to i32 , !dbg !212
  ret i32 %".56", !dbg !212
if.end.3:
  %".58" = trunc i64 0 to i32 , !dbg !213
  ret i32 %".58", !dbg !213
}

define i32 @"test_damage_region_clear"() !dbg !41
{
entry:
  %"region.addr" = alloca %"struct.ritz_module_1.DamageRegion", !dbg !214
  %".2" = call %"struct.ritz_module_1.DamageRegion" @"damage_region_new"(), !dbg !214
  store %"struct.ritz_module_1.DamageRegion" %".2", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !214
  %".4" = trunc i64 0 to i32 , !dbg !215
  %".5" = trunc i64 0 to i32 , !dbg !215
  %".6" = trunc i64 10 to i32 , !dbg !215
  %".7" = trunc i64 10 to i32 , !dbg !215
  %".8" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".4", 0 , !dbg !215
  %".9" = insertvalue %"struct.ritz_module_1.Rect" %".8", i32 %".5", 1 , !dbg !215
  %".10" = insertvalue %"struct.ritz_module_1.Rect" %".9", i32 %".6", 2 , !dbg !215
  %".11" = insertvalue %"struct.ritz_module_1.Rect" %".10", i32 %".7", 3 , !dbg !215
  %".12" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !215
  %".13" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".12", i32 0, i64 0 , !dbg !215
  store %"struct.ritz_module_1.Rect" %".11", %"struct.ritz_module_1.Rect"* %".13", !dbg !215
  %".15" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !216
  %".16" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !216
  %".17" = trunc i64 1 to i32 , !dbg !216
  store i32 %".17", i32* %".16", !dbg !216
  %".19" = trunc i64 20 to i32 , !dbg !217
  %".20" = trunc i64 20 to i32 , !dbg !217
  %".21" = trunc i64 10 to i32 , !dbg !217
  %".22" = trunc i64 10 to i32 , !dbg !217
  %".23" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".19", 0 , !dbg !217
  %".24" = insertvalue %"struct.ritz_module_1.Rect" %".23", i32 %".20", 1 , !dbg !217
  %".25" = insertvalue %"struct.ritz_module_1.Rect" %".24", i32 %".21", 2 , !dbg !217
  %".26" = insertvalue %"struct.ritz_module_1.Rect" %".25", i32 %".22", 3 , !dbg !217
  %".27" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !217
  %".28" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".27", i32 0, i64 1 , !dbg !217
  store %"struct.ritz_module_1.Rect" %".26", %"struct.ritz_module_1.Rect"* %".28", !dbg !217
  %".30" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !218
  %".31" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !218
  %".32" = trunc i64 2 to i32 , !dbg !218
  store i32 %".32", i32* %".31", !dbg !218
  %".34" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !219
  %".35" = load i32, i32* %".34", !dbg !219
  %".36" = zext i32 %".35" to i64 , !dbg !219
  %".37" = icmp ne i64 %".36", 2 , !dbg !219
  br i1 %".37", label %"if.then", label %"if.end", !dbg !219
if.then:
  %".39" = trunc i64 1 to i32 , !dbg !220
  ret i32 %".39", !dbg !220
if.end:
  %".41" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !221
  %".42" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !221
  %".43" = trunc i64 0 to i32 , !dbg !221
  store i32 %".43", i32* %".42", !dbg !221
  %".45" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !222
  %".46" = load i32, i32* %".45", !dbg !222
  %".47" = zext i32 %".46" to i64 , !dbg !222
  %".48" = icmp ne i64 %".47", 0 , !dbg !222
  br i1 %".48", label %"if.then.1", label %"if.end.1", !dbg !222
if.then.1:
  %".50" = trunc i64 2 to i32 , !dbg !223
  ret i32 %".50", !dbg !223
if.end.1:
  %".52" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !224
  %".53" = load i32, i32* %".52", !dbg !224
  %".54" = zext i32 %".53" to i64 , !dbg !224
  %".55" = icmp ne i64 %".54", 0 , !dbg !224
  br i1 %".55", label %"if.then.2", label %"if.end.2", !dbg !224
if.then.2:
  %".57" = trunc i64 3 to i32 , !dbg !225
  ret i32 %".57", !dbg !225
if.end.2:
  %".59" = trunc i64 0 to i32 , !dbg !226
  ret i32 %".59", !dbg !226
}

define i32 @"test_rects_intersect"() !dbg !42
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !227
  %".3" = trunc i64 0 to i32 , !dbg !227
  %".4" = trunc i64 100 to i32 , !dbg !227
  %".5" = trunc i64 100 to i32 , !dbg !227
  %".6" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".2", 0 , !dbg !227
  %".7" = insertvalue %"struct.ritz_module_1.Rect" %".6", i32 %".3", 1 , !dbg !227
  %".8" = insertvalue %"struct.ritz_module_1.Rect" %".7", i32 %".4", 2 , !dbg !227
  %".9" = insertvalue %"struct.ritz_module_1.Rect" %".8", i32 %".5", 3 , !dbg !227
  %".10" = trunc i64 50 to i32 , !dbg !228
  %".11" = trunc i64 50 to i32 , !dbg !228
  %".12" = trunc i64 100 to i32 , !dbg !228
  %".13" = trunc i64 100 to i32 , !dbg !228
  %".14" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".10", 0 , !dbg !228
  %".15" = insertvalue %"struct.ritz_module_1.Rect" %".14", i32 %".11", 1 , !dbg !228
  %".16" = insertvalue %"struct.ritz_module_1.Rect" %".15", i32 %".12", 2 , !dbg !228
  %".17" = insertvalue %"struct.ritz_module_1.Rect" %".16", i32 %".13", 3 , !dbg !228
  %".18" = trunc i64 200 to i32 , !dbg !229
  %".19" = trunc i64 200 to i32 , !dbg !229
  %".20" = trunc i64 10 to i32 , !dbg !229
  %".21" = trunc i64 10 to i32 , !dbg !229
  %".22" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".18", 0 , !dbg !229
  %".23" = insertvalue %"struct.ritz_module_1.Rect" %".22", i32 %".19", 1 , !dbg !229
  %".24" = insertvalue %"struct.ritz_module_1.Rect" %".23", i32 %".20", 2 , !dbg !229
  %".25" = insertvalue %"struct.ritz_module_1.Rect" %".24", i32 %".21", 3 , !dbg !229
  %"a.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !230
  store %"struct.ritz_module_1.Rect" %".9", %"struct.ritz_module_1.Rect"* %"a.addr", !dbg !230
  %"b.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !230
  store %"struct.ritz_module_1.Rect" %".17", %"struct.ritz_module_1.Rect"* %"b.addr", !dbg !230
  %".28" = call i1 @"rects_intersect"(%"struct.ritz_module_1.Rect"* %"a.addr", %"struct.ritz_module_1.Rect"* %"b.addr"), !dbg !230
  %".29" = icmp eq i1 %".28", 0 , !dbg !230
  br i1 %".29", label %"if.then", label %"if.end", !dbg !230
if.then:
  %".31" = trunc i64 1 to i32 , !dbg !231
  ret i32 %".31", !dbg !231
if.end:
  %"a.addr.1" = alloca %"struct.ritz_module_1.Rect", !dbg !232
  store %"struct.ritz_module_1.Rect" %".9", %"struct.ritz_module_1.Rect"* %"a.addr.1", !dbg !232
  %"c.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !232
  store %"struct.ritz_module_1.Rect" %".25", %"struct.ritz_module_1.Rect"* %"c.addr", !dbg !232
  %".35" = call i1 @"rects_intersect"(%"struct.ritz_module_1.Rect"* %"a.addr.1", %"struct.ritz_module_1.Rect"* %"c.addr"), !dbg !232
  br i1 %".35", label %"if.then.1", label %"if.end.1", !dbg !232
if.then.1:
  %".37" = trunc i64 2 to i32 , !dbg !233
  ret i32 %".37", !dbg !233
if.end.1:
  %"b.addr.1" = alloca %"struct.ritz_module_1.Rect", !dbg !234
  store %"struct.ritz_module_1.Rect" %".17", %"struct.ritz_module_1.Rect"* %"b.addr.1", !dbg !234
  %"c.addr.1" = alloca %"struct.ritz_module_1.Rect", !dbg !234
  store %"struct.ritz_module_1.Rect" %".25", %"struct.ritz_module_1.Rect"* %"c.addr.1", !dbg !234
  %".41" = call i1 @"rects_intersect"(%"struct.ritz_module_1.Rect"* %"b.addr.1", %"struct.ritz_module_1.Rect"* %"c.addr.1"), !dbg !234
  br i1 %".41", label %"if.then.2", label %"if.end.2", !dbg !234
if.then.2:
  %".43" = trunc i64 3 to i32 , !dbg !235
  ret i32 %".43", !dbg !235
if.end.2:
  %".45" = trunc i64 0 to i32 , !dbg !236
  ret i32 %".45", !dbg !236
}

define i32 @"test_rect_union"() !dbg !43
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !237
  %".3" = trunc i64 0 to i32 , !dbg !237
  %".4" = trunc i64 50 to i32 , !dbg !237
  %".5" = trunc i64 50 to i32 , !dbg !237
  %".6" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".2", 0 , !dbg !237
  %".7" = insertvalue %"struct.ritz_module_1.Rect" %".6", i32 %".3", 1 , !dbg !237
  %".8" = insertvalue %"struct.ritz_module_1.Rect" %".7", i32 %".4", 2 , !dbg !237
  %".9" = insertvalue %"struct.ritz_module_1.Rect" %".8", i32 %".5", 3 , !dbg !237
  %".10" = trunc i64 25 to i32 , !dbg !238
  %".11" = trunc i64 25 to i32 , !dbg !238
  %".12" = trunc i64 50 to i32 , !dbg !238
  %".13" = trunc i64 50 to i32 , !dbg !238
  %".14" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".10", 0 , !dbg !238
  %".15" = insertvalue %"struct.ritz_module_1.Rect" %".14", i32 %".11", 1 , !dbg !238
  %".16" = insertvalue %"struct.ritz_module_1.Rect" %".15", i32 %".12", 2 , !dbg !238
  %".17" = insertvalue %"struct.ritz_module_1.Rect" %".16", i32 %".13", 3 , !dbg !238
  %"a.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !239
  store %"struct.ritz_module_1.Rect" %".9", %"struct.ritz_module_1.Rect"* %"a.addr", !dbg !239
  %"b.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !239
  store %"struct.ritz_module_1.Rect" %".17", %"struct.ritz_module_1.Rect"* %"b.addr", !dbg !239
  %".20" = call %"struct.ritz_module_1.Rect" @"rect_union"(%"struct.ritz_module_1.Rect"* %"a.addr", %"struct.ritz_module_1.Rect"* %"b.addr"), !dbg !239
  %".21" = extractvalue %"struct.ritz_module_1.Rect" %".20", 0 , !dbg !240
  %".22" = sext i32 %".21" to i64 , !dbg !240
  %".23" = icmp ne i64 %".22", 0 , !dbg !240
  br i1 %".23", label %"if.then", label %"if.end", !dbg !240
if.then:
  %".25" = trunc i64 1 to i32 , !dbg !241
  ret i32 %".25", !dbg !241
if.end:
  %".27" = extractvalue %"struct.ritz_module_1.Rect" %".20", 1 , !dbg !242
  %".28" = sext i32 %".27" to i64 , !dbg !242
  %".29" = icmp ne i64 %".28", 0 , !dbg !242
  br i1 %".29", label %"if.then.1", label %"if.end.1", !dbg !242
if.then.1:
  %".31" = trunc i64 2 to i32 , !dbg !243
  ret i32 %".31", !dbg !243
if.end.1:
  %".33" = extractvalue %"struct.ritz_module_1.Rect" %".20", 2 , !dbg !244
  %".34" = zext i32 %".33" to i64 , !dbg !244
  %".35" = icmp ne i64 %".34", 75 , !dbg !244
  br i1 %".35", label %"if.then.2", label %"if.end.2", !dbg !244
if.then.2:
  %".37" = trunc i64 3 to i32 , !dbg !245
  ret i32 %".37", !dbg !245
if.end.2:
  %".39" = extractvalue %"struct.ritz_module_1.Rect" %".20", 3 , !dbg !246
  %".40" = zext i32 %".39" to i64 , !dbg !246
  %".41" = icmp ne i64 %".40", 75 , !dbg !246
  br i1 %".41", label %"if.then.3", label %"if.end.3", !dbg !246
if.then.3:
  %".43" = trunc i64 4 to i32 , !dbg !247
  ret i32 %".43", !dbg !247
if.end.3:
  %".45" = trunc i64 0 to i32 , !dbg !248
  ret i32 %".45", !dbg !248
}

define i32 @"test_damage_region_bounds"() !dbg !44
{
entry:
  %"region.addr" = alloca %"struct.ritz_module_1.DamageRegion", !dbg !249
  %".2" = call %"struct.ritz_module_1.DamageRegion" @"damage_region_new"(), !dbg !249
  store %"struct.ritz_module_1.DamageRegion" %".2", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !249
  %".4" = trunc i64 10 to i32 , !dbg !250
  %".5" = trunc i64 10 to i32 , !dbg !250
  %".6" = trunc i64 20 to i32 , !dbg !250
  %".7" = trunc i64 20 to i32 , !dbg !250
  %".8" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".4", 0 , !dbg !250
  %".9" = insertvalue %"struct.ritz_module_1.Rect" %".8", i32 %".5", 1 , !dbg !250
  %".10" = insertvalue %"struct.ritz_module_1.Rect" %".9", i32 %".6", 2 , !dbg !250
  %".11" = insertvalue %"struct.ritz_module_1.Rect" %".10", i32 %".7", 3 , !dbg !250
  %".12" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !250
  %".13" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".12", i32 0, i64 0 , !dbg !250
  store %"struct.ritz_module_1.Rect" %".11", %"struct.ritz_module_1.Rect"* %".13", !dbg !250
  %".15" = trunc i64 50 to i32 , !dbg !251
  %".16" = trunc i64 50 to i32 , !dbg !251
  %".17" = trunc i64 30 to i32 , !dbg !251
  %".18" = trunc i64 30 to i32 , !dbg !251
  %".19" = insertvalue %"struct.ritz_module_1.Rect" undef, i32 %".15", 0 , !dbg !251
  %".20" = insertvalue %"struct.ritz_module_1.Rect" %".19", i32 %".16", 1 , !dbg !251
  %".21" = insertvalue %"struct.ritz_module_1.Rect" %".20", i32 %".17", 2 , !dbg !251
  %".22" = insertvalue %"struct.ritz_module_1.Rect" %".21", i32 %".18", 3 , !dbg !251
  %".23" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !251
  %".24" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".23", i32 0, i64 1 , !dbg !251
  store %"struct.ritz_module_1.Rect" %".22", %"struct.ritz_module_1.Rect"* %".24", !dbg !251
  %".26" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !252
  %".27" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !252
  %".28" = trunc i64 2 to i32 , !dbg !252
  store i32 %".28", i32* %".27", !dbg !252
  %".30" = call %"struct.ritz_module_1.Rect" @"damage_region_bounds"(%"struct.ritz_module_1.DamageRegion"* %"region.addr"), !dbg !253
  %".31" = extractvalue %"struct.ritz_module_1.Rect" %".30", 0 , !dbg !254
  %".32" = sext i32 %".31" to i64 , !dbg !254
  %".33" = icmp ne i64 %".32", 10 , !dbg !254
  br i1 %".33", label %"if.then", label %"if.end", !dbg !254
if.then:
  %".35" = trunc i64 1 to i32 , !dbg !255
  ret i32 %".35", !dbg !255
if.end:
  %".37" = extractvalue %"struct.ritz_module_1.Rect" %".30", 1 , !dbg !256
  %".38" = sext i32 %".37" to i64 , !dbg !256
  %".39" = icmp ne i64 %".38", 10 , !dbg !256
  br i1 %".39", label %"if.then.1", label %"if.end.1", !dbg !256
if.then.1:
  %".41" = trunc i64 2 to i32 , !dbg !257
  ret i32 %".41", !dbg !257
if.end.1:
  %".43" = extractvalue %"struct.ritz_module_1.Rect" %".30", 2 , !dbg !258
  %".44" = zext i32 %".43" to i64 , !dbg !258
  %".45" = icmp ne i64 %".44", 70 , !dbg !258
  br i1 %".45", label %"if.then.2", label %"if.end.2", !dbg !258
if.then.2:
  %".47" = trunc i64 3 to i32 , !dbg !259
  ret i32 %".47", !dbg !259
if.end.2:
  %".49" = extractvalue %"struct.ritz_module_1.Rect" %".30", 3 , !dbg !260
  %".50" = zext i32 %".49" to i64 , !dbg !260
  %".51" = icmp ne i64 %".50", 70 , !dbg !260
  br i1 %".51", label %"if.then.3", label %"if.end.3", !dbg !260
if.then.3:
  %".53" = trunc i64 4 to i32 , !dbg !261
  ret i32 %".53", !dbg !261
if.end.3:
  %".55" = trunc i64 0 to i32 , !dbg !262
  ret i32 %".55", !dbg !262
}

define i32 @"print_result"(i8* %"name.arg", i32 %"result.arg") !dbg !45
{
entry:
  %"name" = alloca i8*
  %"buf.addr" = alloca [10 x i8], !dbg !271
  %"n.addr" = alloca i32, !dbg !277
  %"i.addr" = alloca i64, !dbg !280
  %"j.addr" = alloca i64, !dbg !290
  store i8* %"name.arg", i8** %"name"
  call void @"llvm.dbg.declare"(metadata i8** %"name", metadata !264, metadata !7), !dbg !265
  %"result" = alloca i32
  store i32 %"result.arg", i32* %"result"
  call void @"llvm.dbg.declare"(metadata i32* %"result", metadata !266, metadata !7), !dbg !265
  %".8" = load i32, i32* %"result", !dbg !267
  %".9" = sext i32 %".8" to i64 , !dbg !267
  %".10" = icmp eq i64 %".9", 0 , !dbg !267
  br i1 %".10", label %"if.then", label %"if.else", !dbg !267
if.then:
  %".12" = trunc i64 1 to i32 , !dbg !268
  %".13" = load i8*, i8** %"name", !dbg !268
  %".14" = call i64 @"sys_write"(i32 %".12", i8* %".13", i64 30), !dbg !268
  %".15" = trunc i64 1 to i32 , !dbg !268
  %".16" = getelementptr [7 x i8], [7 x i8]* @".str.0", i64 0, i64 0 , !dbg !268
  %".17" = call i64 @"sys_write"(i32 %".15", i8* %".16", i64 6), !dbg !268
  br label %"if.end", !dbg !298
if.else:
  %".18" = trunc i64 1 to i32 , !dbg !269
  %".19" = load i8*, i8** %"name", !dbg !269
  %".20" = call i64 @"sys_write"(i32 %".18", i8* %".19", i64 30), !dbg !269
  %".21" = trunc i64 1 to i32 , !dbg !270
  %".22" = getelementptr [8 x i8], [8 x i8]* @".str.1", i64 0, i64 0 , !dbg !270
  %".23" = call i64 @"sys_write"(i32 %".21", i8* %".22", i64 7), !dbg !270
  call void @"llvm.dbg.declare"(metadata [10 x i8]* %"buf.addr", metadata !275, metadata !7), !dbg !276
  %".25" = load i32, i32* %"result", !dbg !277
  store i32 %".25", i32* %"n.addr", !dbg !277
  call void @"llvm.dbg.declare"(metadata i32* %"n.addr", metadata !278, metadata !7), !dbg !279
  store i64 0, i64* %"i.addr", !dbg !280
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !281, metadata !7), !dbg !282
  %".30" = load i32, i32* %"n.addr", !dbg !283
  %".31" = sext i32 %".30" to i64 , !dbg !283
  %".32" = icmp eq i64 %".31", 0 , !dbg !283
  br i1 %".32", label %"if.then.1", label %"if.else.1", !dbg !283
if.end:
  %".101" = phi  i64 [%".17", %"if.then"], [%".98", %"if.end.1"] , !dbg !298
  %".102" = trunc i64 %".101" to i32 , !dbg !298
  ret i32 %".102", !dbg !298
if.then.1:
  %".34" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !284
  %".35" = trunc i64 48 to i8 , !dbg !284
  store i8 %".35", i8* %".34", !dbg !284
  store i64 1, i64* %"i.addr", !dbg !285
  br label %"if.end.1", !dbg !297
if.else.1:
  br label %"while.cond", !dbg !286
if.end.1:
  %".92" = trunc i64 1 to i32 , !dbg !298
  %".93" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !298
  %".94" = load i64, i64* %"i.addr", !dbg !298
  %".95" = call i64 @"sys_write"(i32 %".92", i8* %".93", i64 %".94"), !dbg !298
  %".96" = trunc i64 1 to i32 , !dbg !298
  %".97" = getelementptr [3 x i8], [3 x i8]* @".str.2", i64 0, i64 0 , !dbg !298
  %".98" = call i64 @"sys_write"(i32 %".96", i8* %".97", i64 2), !dbg !298
  br label %"if.end", !dbg !298
while.cond:
  %".39" = load i32, i32* %"n.addr", !dbg !286
  %".40" = sext i32 %".39" to i64 , !dbg !286
  %".41" = icmp sgt i64 %".40", 0 , !dbg !286
  br i1 %".41", label %"while.body", label %"while.end", !dbg !286
while.body:
  %".43" = load i32, i32* %"n.addr", !dbg !287
  %".44" = sext i32 %".43" to i64 , !dbg !287
  %".45" = srem i64 %".44", 10, !dbg !287
  %".46" = add i64 48, %".45", !dbg !287
  %".47" = trunc i64 %".46" to i8 , !dbg !287
  %".48" = load i64, i64* %"i.addr", !dbg !287
  %".49" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 %".48" , !dbg !287
  store i8 %".47", i8* %".49", !dbg !287
  %".51" = load i32, i32* %"n.addr", !dbg !288
  %".52" = sext i32 %".51" to i64 , !dbg !288
  %".53" = sdiv i64 %".52", 10, !dbg !288
  %".54" = trunc i64 %".53" to i32 , !dbg !288
  store i32 %".54", i32* %"n.addr", !dbg !288
  %".56" = load i64, i64* %"i.addr", !dbg !289
  %".57" = add i64 %".56", 1, !dbg !289
  store i64 %".57", i64* %"i.addr", !dbg !289
  br label %"while.cond", !dbg !289
while.end:
  store i64 0, i64* %"j.addr", !dbg !290
  call void @"llvm.dbg.declare"(metadata i64* %"j.addr", metadata !291, metadata !7), !dbg !292
  br label %"while.cond.1", !dbg !293
while.cond.1:
  %".63" = load i64, i64* %"j.addr", !dbg !293
  %".64" = load i64, i64* %"i.addr", !dbg !293
  %".65" = sdiv i64 %".64", 2, !dbg !293
  %".66" = icmp slt i64 %".63", %".65" , !dbg !293
  br i1 %".66", label %"while.body.1", label %"while.end.1", !dbg !293
while.body.1:
  %".68" = load i64, i64* %"j.addr", !dbg !294
  %".69" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 %".68" , !dbg !294
  %".70" = load i8, i8* %".69", !dbg !294
  %".71" = load i64, i64* %"i.addr", !dbg !295
  %".72" = sub i64 %".71", 1, !dbg !295
  %".73" = load i64, i64* %"j.addr", !dbg !295
  %".74" = sub i64 %".72", %".73", !dbg !295
  %".75" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 %".74" , !dbg !295
  %".76" = load i8, i8* %".75", !dbg !295
  %".77" = load i64, i64* %"j.addr", !dbg !295
  %".78" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 %".77" , !dbg !295
  store i8 %".76", i8* %".78", !dbg !295
  %".80" = load i64, i64* %"i.addr", !dbg !296
  %".81" = sub i64 %".80", 1, !dbg !296
  %".82" = load i64, i64* %"j.addr", !dbg !296
  %".83" = sub i64 %".81", %".82", !dbg !296
  %".84" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 %".83" , !dbg !296
  store i8 %".70", i8* %".84", !dbg !296
  %".86" = load i64, i64* %"j.addr", !dbg !297
  %".87" = add i64 %".86", 1, !dbg !297
  store i64 %".87", i64* %"j.addr", !dbg !297
  br label %"while.cond.1", !dbg !297
while.end.1:
  br label %"if.end.1", !dbg !297
}

define i32 @"main"() !dbg !46
{
entry:
  %"failed.addr" = alloca i32, !dbg !299
  %"total.addr" = alloca i32, !dbg !302
  %"result.addr" = alloca i32, !dbg !305
  %".2" = trunc i64 0 to i32 , !dbg !299
  store i32 %".2", i32* %"failed.addr", !dbg !299
  call void @"llvm.dbg.declare"(metadata i32* %"failed.addr", metadata !300, metadata !7), !dbg !301
  %".5" = trunc i64 0 to i32 , !dbg !302
  store i32 %".5", i32* %"total.addr", !dbg !302
  call void @"llvm.dbg.declare"(metadata i32* %"total.addr", metadata !303, metadata !7), !dbg !304
  %".8" = trunc i64 0 to i32 , !dbg !305
  store i32 %".8", i32* %"result.addr", !dbg !305
  call void @"llvm.dbg.declare"(metadata i32* %"result.addr", metadata !306, metadata !7), !dbg !307
  %".11" = trunc i64 1 to i32 , !dbg !308
  %".12" = getelementptr [28 x i8], [28 x i8]* @".str.3", i64 0, i64 0 , !dbg !308
  %".13" = call i64 @"sys_write"(i32 %".11", i8* %".12", i64 27), !dbg !308
  %".14" = call i32 @"test_point_creation"(), !dbg !309
  store i32 %".14", i32* %"result.addr", !dbg !309
  %".16" = getelementptr [27 x i8], [27 x i8]* @".str.4", i64 0, i64 0 , !dbg !310
  %".17" = load i32, i32* %"result.addr", !dbg !310
  %".18" = call i32 @"print_result"(i8* %".16", i32 %".17"), !dbg !310
  %".19" = load i32, i32* %"result.addr", !dbg !311
  %".20" = sext i32 %".19" to i64 , !dbg !311
  %".21" = icmp ne i64 %".20", 0 , !dbg !311
  br i1 %".21", label %"if.then", label %"if.end", !dbg !311
if.then:
  %".23" = load i32, i32* %"failed.addr", !dbg !312
  %".24" = sext i32 %".23" to i64 , !dbg !312
  %".25" = add i64 %".24", 1, !dbg !312
  %".26" = trunc i64 %".25" to i32 , !dbg !312
  store i32 %".26", i32* %"failed.addr", !dbg !312
  br label %"if.end", !dbg !312
if.end:
  %".29" = load i32, i32* %"total.addr", !dbg !313
  %".30" = sext i32 %".29" to i64 , !dbg !313
  %".31" = add i64 %".30", 1, !dbg !313
  %".32" = trunc i64 %".31" to i32 , !dbg !313
  store i32 %".32", i32* %"total.addr", !dbg !313
  %".34" = call i32 @"test_point_zero"(), !dbg !314
  store i32 %".34", i32* %"result.addr", !dbg !314
  %".36" = getelementptr [27 x i8], [27 x i8]* @".str.5", i64 0, i64 0 , !dbg !315
  %".37" = load i32, i32* %"result.addr", !dbg !315
  %".38" = call i32 @"print_result"(i8* %".36", i32 %".37"), !dbg !315
  %".39" = load i32, i32* %"result.addr", !dbg !316
  %".40" = sext i32 %".39" to i64 , !dbg !316
  %".41" = icmp ne i64 %".40", 0 , !dbg !316
  br i1 %".41", label %"if.then.1", label %"if.end.1", !dbg !316
if.then.1:
  %".43" = load i32, i32* %"failed.addr", !dbg !317
  %".44" = sext i32 %".43" to i64 , !dbg !317
  %".45" = add i64 %".44", 1, !dbg !317
  %".46" = trunc i64 %".45" to i32 , !dbg !317
  store i32 %".46", i32* %"failed.addr", !dbg !317
  br label %"if.end.1", !dbg !317
if.end.1:
  %".49" = load i32, i32* %"total.addr", !dbg !318
  %".50" = sext i32 %".49" to i64 , !dbg !318
  %".51" = add i64 %".50", 1, !dbg !318
  %".52" = trunc i64 %".51" to i32 , !dbg !318
  store i32 %".52", i32* %"total.addr", !dbg !318
  %".54" = call i32 @"test_size_creation"(), !dbg !319
  store i32 %".54", i32* %"result.addr", !dbg !319
  %".56" = getelementptr [27 x i8], [27 x i8]* @".str.6", i64 0, i64 0 , !dbg !320
  %".57" = load i32, i32* %"result.addr", !dbg !320
  %".58" = call i32 @"print_result"(i8* %".56", i32 %".57"), !dbg !320
  %".59" = load i32, i32* %"result.addr", !dbg !321
  %".60" = sext i32 %".59" to i64 , !dbg !321
  %".61" = icmp ne i64 %".60", 0 , !dbg !321
  br i1 %".61", label %"if.then.2", label %"if.end.2", !dbg !321
if.then.2:
  %".63" = load i32, i32* %"failed.addr", !dbg !322
  %".64" = sext i32 %".63" to i64 , !dbg !322
  %".65" = add i64 %".64", 1, !dbg !322
  %".66" = trunc i64 %".65" to i32 , !dbg !322
  store i32 %".66", i32* %"failed.addr", !dbg !322
  br label %"if.end.2", !dbg !322
if.end.2:
  %".69" = load i32, i32* %"total.addr", !dbg !323
  %".70" = sext i32 %".69" to i64 , !dbg !323
  %".71" = add i64 %".70", 1, !dbg !323
  %".72" = trunc i64 %".71" to i32 , !dbg !323
  store i32 %".72", i32* %"total.addr", !dbg !323
  %".74" = call i32 @"test_size_area"(), !dbg !324
  store i32 %".74", i32* %"result.addr", !dbg !324
  %".76" = getelementptr [27 x i8], [27 x i8]* @".str.7", i64 0, i64 0 , !dbg !325
  %".77" = load i32, i32* %"result.addr", !dbg !325
  %".78" = call i32 @"print_result"(i8* %".76", i32 %".77"), !dbg !325
  %".79" = load i32, i32* %"result.addr", !dbg !326
  %".80" = sext i32 %".79" to i64 , !dbg !326
  %".81" = icmp ne i64 %".80", 0 , !dbg !326
  br i1 %".81", label %"if.then.3", label %"if.end.3", !dbg !326
if.then.3:
  %".83" = load i32, i32* %"failed.addr", !dbg !327
  %".84" = sext i32 %".83" to i64 , !dbg !327
  %".85" = add i64 %".84", 1, !dbg !327
  %".86" = trunc i64 %".85" to i32 , !dbg !327
  store i32 %".86", i32* %"failed.addr", !dbg !327
  br label %"if.end.3", !dbg !327
if.end.3:
  %".89" = load i32, i32* %"total.addr", !dbg !328
  %".90" = sext i32 %".89" to i64 , !dbg !328
  %".91" = add i64 %".90", 1, !dbg !328
  %".92" = trunc i64 %".91" to i32 , !dbg !328
  store i32 %".92", i32* %"total.addr", !dbg !328
  %".94" = call i32 @"test_rect_creation"(), !dbg !329
  store i32 %".94", i32* %"result.addr", !dbg !329
  %".96" = getelementptr [27 x i8], [27 x i8]* @".str.8", i64 0, i64 0 , !dbg !330
  %".97" = load i32, i32* %"result.addr", !dbg !330
  %".98" = call i32 @"print_result"(i8* %".96", i32 %".97"), !dbg !330
  %".99" = load i32, i32* %"result.addr", !dbg !331
  %".100" = sext i32 %".99" to i64 , !dbg !331
  %".101" = icmp ne i64 %".100", 0 , !dbg !331
  br i1 %".101", label %"if.then.4", label %"if.end.4", !dbg !331
if.then.4:
  %".103" = load i32, i32* %"failed.addr", !dbg !332
  %".104" = sext i32 %".103" to i64 , !dbg !332
  %".105" = add i64 %".104", 1, !dbg !332
  %".106" = trunc i64 %".105" to i32 , !dbg !332
  store i32 %".106", i32* %"failed.addr", !dbg !332
  br label %"if.end.4", !dbg !332
if.end.4:
  %".109" = load i32, i32* %"total.addr", !dbg !333
  %".110" = sext i32 %".109" to i64 , !dbg !333
  %".111" = add i64 %".110", 1, !dbg !333
  %".112" = trunc i64 %".111" to i32 , !dbg !333
  store i32 %".112", i32* %"total.addr", !dbg !333
  %".114" = call i32 @"test_rect_contains_point"(), !dbg !334
  store i32 %".114", i32* %"result.addr", !dbg !334
  %".116" = getelementptr [27 x i8], [27 x i8]* @".str.9", i64 0, i64 0 , !dbg !335
  %".117" = load i32, i32* %"result.addr", !dbg !335
  %".118" = call i32 @"print_result"(i8* %".116", i32 %".117"), !dbg !335
  %".119" = load i32, i32* %"result.addr", !dbg !336
  %".120" = sext i32 %".119" to i64 , !dbg !336
  %".121" = icmp ne i64 %".120", 0 , !dbg !336
  br i1 %".121", label %"if.then.5", label %"if.end.5", !dbg !336
if.then.5:
  %".123" = load i32, i32* %"failed.addr", !dbg !337
  %".124" = sext i32 %".123" to i64 , !dbg !337
  %".125" = add i64 %".124", 1, !dbg !337
  %".126" = trunc i64 %".125" to i32 , !dbg !337
  store i32 %".126", i32* %"failed.addr", !dbg !337
  br label %"if.end.5", !dbg !337
if.end.5:
  %".129" = load i32, i32* %"total.addr", !dbg !338
  %".130" = sext i32 %".129" to i64 , !dbg !338
  %".131" = add i64 %".130", 1, !dbg !338
  %".132" = trunc i64 %".131" to i32 , !dbg !338
  store i32 %".132", i32* %"total.addr", !dbg !338
  %".134" = call i32 @"test_color_rgb"(), !dbg !339
  store i32 %".134", i32* %"result.addr", !dbg !339
  %".136" = getelementptr [27 x i8], [27 x i8]* @".str.10", i64 0, i64 0 , !dbg !340
  %".137" = load i32, i32* %"result.addr", !dbg !340
  %".138" = call i32 @"print_result"(i8* %".136", i32 %".137"), !dbg !340
  %".139" = load i32, i32* %"result.addr", !dbg !341
  %".140" = sext i32 %".139" to i64 , !dbg !341
  %".141" = icmp ne i64 %".140", 0 , !dbg !341
  br i1 %".141", label %"if.then.6", label %"if.end.6", !dbg !341
if.then.6:
  %".143" = load i32, i32* %"failed.addr", !dbg !342
  %".144" = sext i32 %".143" to i64 , !dbg !342
  %".145" = add i64 %".144", 1, !dbg !342
  %".146" = trunc i64 %".145" to i32 , !dbg !342
  store i32 %".146", i32* %"failed.addr", !dbg !342
  br label %"if.end.6", !dbg !342
if.end.6:
  %".149" = load i32, i32* %"total.addr", !dbg !343
  %".150" = sext i32 %".149" to i64 , !dbg !343
  %".151" = add i64 %".150", 1, !dbg !343
  %".152" = trunc i64 %".151" to i32 , !dbg !343
  store i32 %".152", i32* %"total.addr", !dbg !343
  %".154" = call i32 @"test_color_black"(), !dbg !344
  store i32 %".154", i32* %"result.addr", !dbg !344
  %".156" = getelementptr [27 x i8], [27 x i8]* @".str.11", i64 0, i64 0 , !dbg !345
  %".157" = load i32, i32* %"result.addr", !dbg !345
  %".158" = call i32 @"print_result"(i8* %".156", i32 %".157"), !dbg !345
  %".159" = load i32, i32* %"result.addr", !dbg !346
  %".160" = sext i32 %".159" to i64 , !dbg !346
  %".161" = icmp ne i64 %".160", 0 , !dbg !346
  br i1 %".161", label %"if.then.7", label %"if.end.7", !dbg !346
if.then.7:
  %".163" = load i32, i32* %"failed.addr", !dbg !347
  %".164" = sext i32 %".163" to i64 , !dbg !347
  %".165" = add i64 %".164", 1, !dbg !347
  %".166" = trunc i64 %".165" to i32 , !dbg !347
  store i32 %".166", i32* %"failed.addr", !dbg !347
  br label %"if.end.7", !dbg !347
if.end.7:
  %".169" = load i32, i32* %"total.addr", !dbg !348
  %".170" = sext i32 %".169" to i64 , !dbg !348
  %".171" = add i64 %".170", 1, !dbg !348
  %".172" = trunc i64 %".171" to i32 , !dbg !348
  store i32 %".172", i32* %"total.addr", !dbg !348
  %".174" = call i32 @"test_color_white"(), !dbg !349
  store i32 %".174", i32* %"result.addr", !dbg !349
  %".176" = getelementptr [27 x i8], [27 x i8]* @".str.12", i64 0, i64 0 , !dbg !350
  %".177" = load i32, i32* %"result.addr", !dbg !350
  %".178" = call i32 @"print_result"(i8* %".176", i32 %".177"), !dbg !350
  %".179" = load i32, i32* %"result.addr", !dbg !351
  %".180" = sext i32 %".179" to i64 , !dbg !351
  %".181" = icmp ne i64 %".180", 0 , !dbg !351
  br i1 %".181", label %"if.then.8", label %"if.end.8", !dbg !351
if.then.8:
  %".183" = load i32, i32* %"failed.addr", !dbg !352
  %".184" = sext i32 %".183" to i64 , !dbg !352
  %".185" = add i64 %".184", 1, !dbg !352
  %".186" = trunc i64 %".185" to i32 , !dbg !352
  store i32 %".186", i32* %"failed.addr", !dbg !352
  br label %"if.end.8", !dbg !352
if.end.8:
  %".189" = load i32, i32* %"total.addr", !dbg !353
  %".190" = sext i32 %".189" to i64 , !dbg !353
  %".191" = add i64 %".190", 1, !dbg !353
  %".192" = trunc i64 %".191" to i32 , !dbg !353
  store i32 %".192", i32* %"total.addr", !dbg !353
  %".194" = call i32 @"test_damage_region_new"(), !dbg !354
  store i32 %".194", i32* %"result.addr", !dbg !354
  %".196" = getelementptr [27 x i8], [27 x i8]* @".str.13", i64 0, i64 0 , !dbg !355
  %".197" = load i32, i32* %"result.addr", !dbg !355
  %".198" = call i32 @"print_result"(i8* %".196", i32 %".197"), !dbg !355
  %".199" = load i32, i32* %"result.addr", !dbg !356
  %".200" = sext i32 %".199" to i64 , !dbg !356
  %".201" = icmp ne i64 %".200", 0 , !dbg !356
  br i1 %".201", label %"if.then.9", label %"if.end.9", !dbg !356
if.then.9:
  %".203" = load i32, i32* %"failed.addr", !dbg !357
  %".204" = sext i32 %".203" to i64 , !dbg !357
  %".205" = add i64 %".204", 1, !dbg !357
  %".206" = trunc i64 %".205" to i32 , !dbg !357
  store i32 %".206", i32* %"failed.addr", !dbg !357
  br label %"if.end.9", !dbg !357
if.end.9:
  %".209" = load i32, i32* %"total.addr", !dbg !358
  %".210" = sext i32 %".209" to i64 , !dbg !358
  %".211" = add i64 %".210", 1, !dbg !358
  %".212" = trunc i64 %".211" to i32 , !dbg !358
  store i32 %".212", i32* %"total.addr", !dbg !358
  %".214" = call i32 @"test_damage_region_add"(), !dbg !359
  store i32 %".214", i32* %"result.addr", !dbg !359
  %".216" = getelementptr [27 x i8], [27 x i8]* @".str.14", i64 0, i64 0 , !dbg !360
  %".217" = load i32, i32* %"result.addr", !dbg !360
  %".218" = call i32 @"print_result"(i8* %".216", i32 %".217"), !dbg !360
  %".219" = load i32, i32* %"result.addr", !dbg !361
  %".220" = sext i32 %".219" to i64 , !dbg !361
  %".221" = icmp ne i64 %".220", 0 , !dbg !361
  br i1 %".221", label %"if.then.10", label %"if.end.10", !dbg !361
if.then.10:
  %".223" = load i32, i32* %"failed.addr", !dbg !362
  %".224" = sext i32 %".223" to i64 , !dbg !362
  %".225" = add i64 %".224", 1, !dbg !362
  %".226" = trunc i64 %".225" to i32 , !dbg !362
  store i32 %".226", i32* %"failed.addr", !dbg !362
  br label %"if.end.10", !dbg !362
if.end.10:
  %".229" = load i32, i32* %"total.addr", !dbg !363
  %".230" = sext i32 %".229" to i64 , !dbg !363
  %".231" = add i64 %".230", 1, !dbg !363
  %".232" = trunc i64 %".231" to i32 , !dbg !363
  store i32 %".232", i32* %"total.addr", !dbg !363
  %".234" = call i32 @"test_damage_region_clear"(), !dbg !364
  store i32 %".234", i32* %"result.addr", !dbg !364
  %".236" = getelementptr [27 x i8], [27 x i8]* @".str.15", i64 0, i64 0 , !dbg !365
  %".237" = load i32, i32* %"result.addr", !dbg !365
  %".238" = call i32 @"print_result"(i8* %".236", i32 %".237"), !dbg !365
  %".239" = load i32, i32* %"result.addr", !dbg !366
  %".240" = sext i32 %".239" to i64 , !dbg !366
  %".241" = icmp ne i64 %".240", 0 , !dbg !366
  br i1 %".241", label %"if.then.11", label %"if.end.11", !dbg !366
if.then.11:
  %".243" = load i32, i32* %"failed.addr", !dbg !367
  %".244" = sext i32 %".243" to i64 , !dbg !367
  %".245" = add i64 %".244", 1, !dbg !367
  %".246" = trunc i64 %".245" to i32 , !dbg !367
  store i32 %".246", i32* %"failed.addr", !dbg !367
  br label %"if.end.11", !dbg !367
if.end.11:
  %".249" = load i32, i32* %"total.addr", !dbg !368
  %".250" = sext i32 %".249" to i64 , !dbg !368
  %".251" = add i64 %".250", 1, !dbg !368
  %".252" = trunc i64 %".251" to i32 , !dbg !368
  store i32 %".252", i32* %"total.addr", !dbg !368
  %".254" = call i32 @"test_rects_intersect"(), !dbg !369
  store i32 %".254", i32* %"result.addr", !dbg !369
  %".256" = getelementptr [27 x i8], [27 x i8]* @".str.16", i64 0, i64 0 , !dbg !370
  %".257" = load i32, i32* %"result.addr", !dbg !370
  %".258" = call i32 @"print_result"(i8* %".256", i32 %".257"), !dbg !370
  %".259" = load i32, i32* %"result.addr", !dbg !371
  %".260" = sext i32 %".259" to i64 , !dbg !371
  %".261" = icmp ne i64 %".260", 0 , !dbg !371
  br i1 %".261", label %"if.then.12", label %"if.end.12", !dbg !371
if.then.12:
  %".263" = load i32, i32* %"failed.addr", !dbg !372
  %".264" = sext i32 %".263" to i64 , !dbg !372
  %".265" = add i64 %".264", 1, !dbg !372
  %".266" = trunc i64 %".265" to i32 , !dbg !372
  store i32 %".266", i32* %"failed.addr", !dbg !372
  br label %"if.end.12", !dbg !372
if.end.12:
  %".269" = load i32, i32* %"total.addr", !dbg !373
  %".270" = sext i32 %".269" to i64 , !dbg !373
  %".271" = add i64 %".270", 1, !dbg !373
  %".272" = trunc i64 %".271" to i32 , !dbg !373
  store i32 %".272", i32* %"total.addr", !dbg !373
  %".274" = call i32 @"test_rect_union"(), !dbg !374
  store i32 %".274", i32* %"result.addr", !dbg !374
  %".276" = getelementptr [27 x i8], [27 x i8]* @".str.17", i64 0, i64 0 , !dbg !375
  %".277" = load i32, i32* %"result.addr", !dbg !375
  %".278" = call i32 @"print_result"(i8* %".276", i32 %".277"), !dbg !375
  %".279" = load i32, i32* %"result.addr", !dbg !376
  %".280" = sext i32 %".279" to i64 , !dbg !376
  %".281" = icmp ne i64 %".280", 0 , !dbg !376
  br i1 %".281", label %"if.then.13", label %"if.end.13", !dbg !376
if.then.13:
  %".283" = load i32, i32* %"failed.addr", !dbg !377
  %".284" = sext i32 %".283" to i64 , !dbg !377
  %".285" = add i64 %".284", 1, !dbg !377
  %".286" = trunc i64 %".285" to i32 , !dbg !377
  store i32 %".286", i32* %"failed.addr", !dbg !377
  br label %"if.end.13", !dbg !377
if.end.13:
  %".289" = load i32, i32* %"total.addr", !dbg !378
  %".290" = sext i32 %".289" to i64 , !dbg !378
  %".291" = add i64 %".290", 1, !dbg !378
  %".292" = trunc i64 %".291" to i32 , !dbg !378
  store i32 %".292", i32* %"total.addr", !dbg !378
  %".294" = call i32 @"test_damage_region_bounds"(), !dbg !379
  store i32 %".294", i32* %"result.addr", !dbg !379
  %".296" = getelementptr [27 x i8], [27 x i8]* @".str.18", i64 0, i64 0 , !dbg !380
  %".297" = load i32, i32* %"result.addr", !dbg !380
  %".298" = call i32 @"print_result"(i8* %".296", i32 %".297"), !dbg !380
  %".299" = load i32, i32* %"result.addr", !dbg !381
  %".300" = sext i32 %".299" to i64 , !dbg !381
  %".301" = icmp ne i64 %".300", 0 , !dbg !381
  br i1 %".301", label %"if.then.14", label %"if.end.14", !dbg !381
if.then.14:
  %".303" = load i32, i32* %"failed.addr", !dbg !382
  %".304" = sext i32 %".303" to i64 , !dbg !382
  %".305" = add i64 %".304", 1, !dbg !382
  %".306" = trunc i64 %".305" to i32 , !dbg !382
  store i32 %".306", i32* %"failed.addr", !dbg !382
  br label %"if.end.14", !dbg !382
if.end.14:
  %".309" = load i32, i32* %"total.addr", !dbg !383
  %".310" = sext i32 %".309" to i64 , !dbg !383
  %".311" = add i64 %".310", 1, !dbg !383
  %".312" = trunc i64 %".311" to i32 , !dbg !383
  store i32 %".312", i32* %"total.addr", !dbg !383
  %".314" = trunc i64 1 to i32 , !dbg !384
  %".315" = getelementptr [29 x i8], [29 x i8]* @".str.19", i64 0, i64 0 , !dbg !384
  %".316" = call i64 @"sys_write"(i32 %".314", i8* %".315", i64 28), !dbg !384
  %".317" = load i32, i32* %"failed.addr", !dbg !385
  %".318" = sext i32 %".317" to i64 , !dbg !385
  %".319" = icmp eq i64 %".318", 0 , !dbg !385
  br i1 %".319", label %"if.then.15", label %"if.else", !dbg !385
if.then.15:
  %".321" = trunc i64 1 to i32 , !dbg !385
  %".322" = getelementptr [20 x i8], [20 x i8]* @".str.20", i64 0, i64 0 , !dbg !385
  %".323" = call i64 @"sys_write"(i32 %".321", i8* %".322", i64 19), !dbg !385
  br label %"if.end.15", !dbg !385
if.else:
  %".324" = trunc i64 1 to i32 , !dbg !385
  %".325" = getelementptr [21 x i8], [21 x i8]* @".str.21", i64 0, i64 0 , !dbg !385
  %".326" = call i64 @"sys_write"(i32 %".324", i8* %".325", i64 20), !dbg !385
  br label %"if.end.15", !dbg !385
if.end.15:
  %".329" = phi  i64 [%".323", %"if.then.15"], [%".326", %"if.else"] , !dbg !385
  %".330" = load i32, i32* %"failed.addr", !dbg !386
  ret i32 %".330", !dbg !386
}

@".str.0" = private constant [7 x i8] c" PASS\0a\00"
@".str.1" = private constant [8 x i8] c" FAIL (\00"
@".str.2" = private constant [3 x i8] c")\0a\00"
@".str.3" = private constant [28 x i8] c"\0a=== Prism Core Tests ===\0a\0a\00"
@".str.4" = private constant [27 x i8] c"test_point_creation       \00"
@".str.5" = private constant [27 x i8] c"test_point_zero           \00"
@".str.6" = private constant [27 x i8] c"test_size_creation        \00"
@".str.7" = private constant [27 x i8] c"test_size_area            \00"
@".str.8" = private constant [27 x i8] c"test_rect_creation        \00"
@".str.9" = private constant [27 x i8] c"test_rect_contains_point  \00"
@".str.10" = private constant [27 x i8] c"test_color_rgb            \00"
@".str.11" = private constant [27 x i8] c"test_color_black          \00"
@".str.12" = private constant [27 x i8] c"test_color_white          \00"
@".str.13" = private constant [27 x i8] c"test_damage_region_new    \00"
@".str.14" = private constant [27 x i8] c"test_damage_region_add    \00"
@".str.15" = private constant [27 x i8] c"test_damage_region_clear  \00"
@".str.16" = private constant [27 x i8] c"test_rects_intersect      \00"
@".str.17" = private constant [27 x i8] c"test_rect_union           \00"
@".str.18" = private constant [27 x i8] c"test_damage_region_bounds \00"
@".str.19" = private constant [29 x i8] c"\0a--------------------------\0a\00"
@".str.20" = private constant [20 x i8] c"All tests passed!\0a\0a\00"
@".str.21" = private constant [21 x i8] c"Some tests failed!\0a\0a\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/prism/test", filename: "simple_test.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 16, name: "test_point_creation", scopeLine: 16, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 24, name: "test_point_zero", scopeLine: 24, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 40, name: "test_size_creation", scopeLine: 40, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 48, name: "test_size_area", scopeLine: 48, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 65, name: "test_rect_creation", scopeLine: 65, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 77, name: "test_rect_contains_point", scopeLine: 77, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 102, name: "color_rgb", scopeLine: 102, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 108, name: "color_r", scopeLine: 108, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 111, name: "color_g", scopeLine: 111, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 114, name: "color_b", scopeLine: 114, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 117, name: "test_color_rgb", scopeLine: 117, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 127, name: "test_color_black", scopeLine: 127, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 137, name: "test_color_white", scopeLine: 137, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 155, name: "damage_region_new", scopeLine: 155, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 161, name: "damage_region_add", scopeLine: 161, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 166, name: "damage_region_clear", scopeLine: 166, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 169, name: "damage_region_is_empty", scopeLine: 169, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 172, name: "rects_intersect", scopeLine: 172, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 181, name: "min_i32", scopeLine: 181, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 186, name: "max_i32", scopeLine: 186, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 191, name: "rect_union", scopeLine: 191, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 208, name: "damage_region_bounds", scopeLine: 208, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "test_damage_region_new", scopeLine: 219, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 227, name: "test_damage_region_add", scopeLine: 227, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 245, name: "test_damage_region_clear", scopeLine: 245, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 266, name: "test_rects_intersect", scopeLine: 266, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 285, name: "test_rect_union", scopeLine: 285, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 301, name: "test_damage_region_bounds", scopeLine: 301, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 326, name: "print_result", scopeLine: 326, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 355, name: "main", scopeLine: 355, type: !4, unit: !1)
!47 = !DILocation(column: 5, line: 17, scope: !17)
!48 = !DILocation(column: 5, line: 18, scope: !17)
!49 = !DILocation(column: 9, line: 19, scope: !17)
!50 = !DILocation(column: 5, line: 20, scope: !17)
!51 = !DILocation(column: 9, line: 21, scope: !17)
!52 = !DILocation(column: 5, line: 22, scope: !17)
!53 = !DILocation(column: 5, line: 25, scope: !18)
!54 = !DILocation(column: 5, line: 26, scope: !18)
!55 = !DILocation(column: 9, line: 27, scope: !18)
!56 = !DILocation(column: 5, line: 28, scope: !18)
!57 = !DILocation(column: 9, line: 29, scope: !18)
!58 = !DILocation(column: 5, line: 30, scope: !18)
!59 = !DILocation(column: 5, line: 41, scope: !19)
!60 = !DILocation(column: 5, line: 42, scope: !19)
!61 = !DILocation(column: 9, line: 43, scope: !19)
!62 = !DILocation(column: 5, line: 44, scope: !19)
!63 = !DILocation(column: 9, line: 45, scope: !19)
!64 = !DILocation(column: 5, line: 46, scope: !19)
!65 = !DILocation(column: 5, line: 49, scope: !20)
!66 = !DILocation(column: 5, line: 50, scope: !20)
!67 = !DILocation(column: 5, line: 51, scope: !20)
!68 = !DILocation(column: 9, line: 52, scope: !20)
!69 = !DILocation(column: 5, line: 53, scope: !20)
!70 = !DILocation(column: 5, line: 66, scope: !21)
!71 = !DILocation(column: 5, line: 67, scope: !21)
!72 = !DILocation(column: 9, line: 68, scope: !21)
!73 = !DILocation(column: 5, line: 69, scope: !21)
!74 = !DILocation(column: 9, line: 70, scope: !21)
!75 = !DILocation(column: 5, line: 71, scope: !21)
!76 = !DILocation(column: 9, line: 72, scope: !21)
!77 = !DILocation(column: 5, line: 73, scope: !21)
!78 = !DILocation(column: 9, line: 74, scope: !21)
!79 = !DILocation(column: 5, line: 75, scope: !21)
!80 = !DILocation(column: 5, line: 78, scope: !22)
!81 = !DILocation(column: 5, line: 81, scope: !22)
!82 = !DILocation(column: 5, line: 82, scope: !22)
!83 = !DILocation(column: 5, line: 83, scope: !22)
!84 = !DILocation(column: 9, line: 84, scope: !22)
!85 = !DILocation(column: 5, line: 85, scope: !22)
!86 = !DILocation(column: 9, line: 86, scope: !22)
!87 = !DILocation(column: 5, line: 89, scope: !22)
!88 = !DILocation(column: 5, line: 90, scope: !22)
!89 = !DILocation(column: 9, line: 91, scope: !22)
!90 = !DILocation(column: 5, line: 93, scope: !22)
!91 = !DILocalVariable(file: !0, line: 102, name: "r", scope: !23, type: !12)
!92 = !DILocation(column: 1, line: 102, scope: !23)
!93 = !DILocalVariable(file: !0, line: 102, name: "g", scope: !23, type: !12)
!94 = !DILocalVariable(file: !0, line: 102, name: "b", scope: !23, type: !12)
!95 = !DILocation(column: 5, line: 103, scope: !23)
!96 = !DILocation(column: 5, line: 104, scope: !23)
!97 = !DILocation(column: 5, line: 105, scope: !23)
!98 = !DILocation(column: 5, line: 106, scope: !23)
!99 = !DICompositeType(align: 32, file: !0, name: "Color", size: 32, tag: DW_TAG_structure_type)
!100 = !DIDerivedType(baseType: !99, size: 64, tag: DW_TAG_reference_type)
!101 = !DILocalVariable(file: !0, line: 108, name: "c", scope: !24, type: !100)
!102 = !DILocation(column: 1, line: 108, scope: !24)
!103 = !DILocation(column: 7, line: 109, scope: !24)
!104 = !DILocalVariable(file: !0, line: 111, name: "c", scope: !25, type: !100)
!105 = !DILocation(column: 1, line: 111, scope: !25)
!106 = !DILocation(column: 7, line: 112, scope: !25)
!107 = !DILocalVariable(file: !0, line: 114, name: "c", scope: !26, type: !100)
!108 = !DILocation(column: 1, line: 114, scope: !26)
!109 = !DILocation(column: 6, line: 115, scope: !26)
!110 = !DILocation(column: 5, line: 118, scope: !27)
!111 = !DILocation(column: 5, line: 119, scope: !27)
!112 = !DILocation(column: 9, line: 120, scope: !27)
!113 = !DILocation(column: 5, line: 121, scope: !27)
!114 = !DILocation(column: 9, line: 122, scope: !27)
!115 = !DILocation(column: 5, line: 123, scope: !27)
!116 = !DILocation(column: 9, line: 124, scope: !27)
!117 = !DILocation(column: 5, line: 125, scope: !27)
!118 = !DILocation(column: 5, line: 128, scope: !28)
!119 = !DILocation(column: 5, line: 129, scope: !28)
!120 = !DILocation(column: 9, line: 130, scope: !28)
!121 = !DILocation(column: 5, line: 131, scope: !28)
!122 = !DILocation(column: 9, line: 132, scope: !28)
!123 = !DILocation(column: 5, line: 133, scope: !28)
!124 = !DILocation(column: 9, line: 134, scope: !28)
!125 = !DILocation(column: 5, line: 135, scope: !28)
!126 = !DILocation(column: 5, line: 138, scope: !29)
!127 = !DILocation(column: 5, line: 139, scope: !29)
!128 = !DILocation(column: 9, line: 140, scope: !29)
!129 = !DILocation(column: 5, line: 141, scope: !29)
!130 = !DILocation(column: 9, line: 142, scope: !29)
!131 = !DILocation(column: 5, line: 143, scope: !29)
!132 = !DILocation(column: 9, line: 144, scope: !29)
!133 = !DILocation(column: 5, line: 145, scope: !29)
!134 = !DILocation(column: 5, line: 156, scope: !30)
!135 = !DICompositeType(align: 32, file: !0, name: "DamageRegion", size: 2080, tag: DW_TAG_structure_type)
!136 = !DILocalVariable(file: !0, line: 161, name: "region", scope: !31, type: !135)
!137 = !DILocation(column: 1, line: 161, scope: !31)
!138 = !DICompositeType(align: 32, file: !0, name: "Rect", size: 128, tag: DW_TAG_structure_type)
!139 = !DILocalVariable(file: !0, line: 161, name: "r", scope: !31, type: !138)
!140 = !DILocation(column: 5, line: 162, scope: !31)
!141 = !DILocation(column: 9, line: 163, scope: !31)
!142 = !DILocation(column: 9, line: 164, scope: !31)
!143 = !DILocalVariable(file: !0, line: 166, name: "region", scope: !32, type: !135)
!144 = !DILocation(column: 1, line: 166, scope: !32)
!145 = !DILocation(column: 5, line: 167, scope: !32)
!146 = !DIDerivedType(baseType: !135, size: 64, tag: DW_TAG_reference_type)
!147 = !DILocalVariable(file: !0, line: 169, name: "region", scope: !33, type: !146)
!148 = !DILocation(column: 1, line: 169, scope: !33)
!149 = !DILocation(column: 5, line: 170, scope: !33)
!150 = !DIDerivedType(baseType: !138, size: 64, tag: DW_TAG_reference_type)
!151 = !DILocalVariable(file: !0, line: 172, name: "a", scope: !34, type: !150)
!152 = !DILocation(column: 1, line: 172, scope: !34)
!153 = !DILocalVariable(file: !0, line: 172, name: "b", scope: !34, type: !150)
!154 = !DILocation(column: 5, line: 174, scope: !34)
!155 = !DILocation(column: 5, line: 175, scope: !34)
!156 = !DILocation(column: 5, line: 176, scope: !34)
!157 = !DILocation(column: 5, line: 177, scope: !34)
!158 = !DILocation(column: 5, line: 179, scope: !34)
!159 = !DILocalVariable(file: !0, line: 181, name: "a", scope: !35, type: !10)
!160 = !DILocation(column: 1, line: 181, scope: !35)
!161 = !DILocalVariable(file: !0, line: 181, name: "b", scope: !35, type: !10)
!162 = !DILocation(column: 5, line: 182, scope: !35)
!163 = !DILocation(column: 9, line: 183, scope: !35)
!164 = !DILocation(column: 5, line: 184, scope: !35)
!165 = !DILocalVariable(file: !0, line: 186, name: "a", scope: !36, type: !10)
!166 = !DILocation(column: 1, line: 186, scope: !36)
!167 = !DILocalVariable(file: !0, line: 186, name: "b", scope: !36, type: !10)
!168 = !DILocation(column: 5, line: 187, scope: !36)
!169 = !DILocation(column: 9, line: 188, scope: !36)
!170 = !DILocation(column: 5, line: 189, scope: !36)
!171 = !DILocalVariable(file: !0, line: 191, name: "a", scope: !37, type: !150)
!172 = !DILocation(column: 1, line: 191, scope: !37)
!173 = !DILocalVariable(file: !0, line: 191, name: "b", scope: !37, type: !150)
!174 = !DILocation(column: 5, line: 192, scope: !37)
!175 = !DILocation(column: 5, line: 193, scope: !37)
!176 = !DILocation(column: 5, line: 194, scope: !37)
!177 = !DILocation(column: 5, line: 195, scope: !37)
!178 = !DILocation(column: 5, line: 196, scope: !37)
!179 = !DILocation(column: 5, line: 197, scope: !37)
!180 = !DILocation(column: 5, line: 198, scope: !37)
!181 = !DILocation(column: 5, line: 199, scope: !37)
!182 = !DILocation(column: 5, line: 201, scope: !37)
!183 = !DILocalVariable(file: !0, line: 208, name: "region", scope: !38, type: !146)
!184 = !DILocation(column: 1, line: 208, scope: !38)
!185 = !DILocation(column: 5, line: 209, scope: !38)
!186 = !DILocation(column: 9, line: 210, scope: !38)
!187 = !DILocation(column: 5, line: 212, scope: !38)
!188 = !DILocation(column: 5, line: 213, scope: !38)
!189 = !DILocalVariable(file: !0, line: 213, name: "i", scope: !38, type: !14)
!190 = !DILocation(column: 1, line: 213, scope: !38)
!191 = !DILocation(column: 5, line: 214, scope: !38)
!192 = !DILocation(column: 9, line: 215, scope: !38)
!193 = !DILocation(column: 9, line: 216, scope: !38)
!194 = !DILocation(column: 5, line: 217, scope: !38)
!195 = !DILocation(column: 5, line: 220, scope: !39)
!196 = !DILocation(column: 5, line: 221, scope: !39)
!197 = !DILocation(column: 9, line: 222, scope: !39)
!198 = !DILocation(column: 5, line: 223, scope: !39)
!199 = !DILocation(column: 9, line: 224, scope: !39)
!200 = !DILocation(column: 5, line: 225, scope: !39)
!201 = !DILocation(column: 5, line: 228, scope: !40)
!202 = !DILocation(column: 5, line: 229, scope: !40)
!203 = !DILocation(column: 5, line: 232, scope: !40)
!204 = !DILocation(column: 5, line: 233, scope: !40)
!205 = !DILocation(column: 5, line: 235, scope: !40)
!206 = !DILocation(column: 9, line: 236, scope: !40)
!207 = !DILocation(column: 5, line: 237, scope: !40)
!208 = !DILocation(column: 9, line: 238, scope: !40)
!209 = !DILocation(column: 5, line: 239, scope: !40)
!210 = !DILocation(column: 9, line: 240, scope: !40)
!211 = !DILocation(column: 5, line: 241, scope: !40)
!212 = !DILocation(column: 9, line: 242, scope: !40)
!213 = !DILocation(column: 5, line: 243, scope: !40)
!214 = !DILocation(column: 5, line: 246, scope: !41)
!215 = !DILocation(column: 5, line: 249, scope: !41)
!216 = !DILocation(column: 5, line: 250, scope: !41)
!217 = !DILocation(column: 5, line: 251, scope: !41)
!218 = !DILocation(column: 5, line: 252, scope: !41)
!219 = !DILocation(column: 5, line: 254, scope: !41)
!220 = !DILocation(column: 9, line: 255, scope: !41)
!221 = !DILocation(column: 5, line: 258, scope: !41)
!222 = !DILocation(column: 5, line: 260, scope: !41)
!223 = !DILocation(column: 9, line: 261, scope: !41)
!224 = !DILocation(column: 5, line: 262, scope: !41)
!225 = !DILocation(column: 9, line: 263, scope: !41)
!226 = !DILocation(column: 5, line: 264, scope: !41)
!227 = !DILocation(column: 5, line: 267, scope: !42)
!228 = !DILocation(column: 5, line: 268, scope: !42)
!229 = !DILocation(column: 5, line: 269, scope: !42)
!230 = !DILocation(column: 5, line: 272, scope: !42)
!231 = !DILocation(column: 9, line: 273, scope: !42)
!232 = !DILocation(column: 5, line: 276, scope: !42)
!233 = !DILocation(column: 9, line: 277, scope: !42)
!234 = !DILocation(column: 5, line: 280, scope: !42)
!235 = !DILocation(column: 9, line: 281, scope: !42)
!236 = !DILocation(column: 5, line: 283, scope: !42)
!237 = !DILocation(column: 5, line: 286, scope: !43)
!238 = !DILocation(column: 5, line: 287, scope: !43)
!239 = !DILocation(column: 5, line: 289, scope: !43)
!240 = !DILocation(column: 5, line: 291, scope: !43)
!241 = !DILocation(column: 9, line: 292, scope: !43)
!242 = !DILocation(column: 5, line: 293, scope: !43)
!243 = !DILocation(column: 9, line: 294, scope: !43)
!244 = !DILocation(column: 5, line: 295, scope: !43)
!245 = !DILocation(column: 9, line: 296, scope: !43)
!246 = !DILocation(column: 5, line: 297, scope: !43)
!247 = !DILocation(column: 9, line: 298, scope: !43)
!248 = !DILocation(column: 5, line: 299, scope: !43)
!249 = !DILocation(column: 5, line: 302, scope: !44)
!250 = !DILocation(column: 5, line: 305, scope: !44)
!251 = !DILocation(column: 5, line: 306, scope: !44)
!252 = !DILocation(column: 5, line: 307, scope: !44)
!253 = !DILocation(column: 5, line: 309, scope: !44)
!254 = !DILocation(column: 5, line: 312, scope: !44)
!255 = !DILocation(column: 9, line: 313, scope: !44)
!256 = !DILocation(column: 5, line: 314, scope: !44)
!257 = !DILocation(column: 9, line: 315, scope: !44)
!258 = !DILocation(column: 5, line: 316, scope: !44)
!259 = !DILocation(column: 9, line: 317, scope: !44)
!260 = !DILocation(column: 5, line: 318, scope: !44)
!261 = !DILocation(column: 9, line: 319, scope: !44)
!262 = !DILocation(column: 5, line: 320, scope: !44)
!263 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!264 = !DILocalVariable(file: !0, line: 326, name: "name", scope: !45, type: !263)
!265 = !DILocation(column: 1, line: 326, scope: !45)
!266 = !DILocalVariable(file: !0, line: 326, name: "result", scope: !45, type: !10)
!267 = !DILocation(column: 5, line: 327, scope: !45)
!268 = !DILocation(column: 9, line: 328, scope: !45)
!269 = !DILocation(column: 9, line: 331, scope: !45)
!270 = !DILocation(column: 9, line: 332, scope: !45)
!271 = !DILocation(column: 9, line: 334, scope: !45)
!272 = !DISubrange(count: 10)
!273 = !{ !272 }
!274 = !DICompositeType(baseType: !12, elements: !273, size: 80, tag: DW_TAG_array_type)
!275 = !DILocalVariable(file: !0, line: 334, name: "buf", scope: !45, type: !274)
!276 = !DILocation(column: 1, line: 334, scope: !45)
!277 = !DILocation(column: 9, line: 335, scope: !45)
!278 = !DILocalVariable(file: !0, line: 335, name: "n", scope: !45, type: !10)
!279 = !DILocation(column: 1, line: 335, scope: !45)
!280 = !DILocation(column: 9, line: 336, scope: !45)
!281 = !DILocalVariable(file: !0, line: 336, name: "i", scope: !45, type: !11)
!282 = !DILocation(column: 1, line: 336, scope: !45)
!283 = !DILocation(column: 9, line: 337, scope: !45)
!284 = !DILocation(column: 13, line: 338, scope: !45)
!285 = !DILocation(column: 13, line: 339, scope: !45)
!286 = !DILocation(column: 13, line: 341, scope: !45)
!287 = !DILocation(column: 17, line: 342, scope: !45)
!288 = !DILocation(column: 17, line: 343, scope: !45)
!289 = !DILocation(column: 17, line: 344, scope: !45)
!290 = !DILocation(column: 13, line: 346, scope: !45)
!291 = !DILocalVariable(file: !0, line: 346, name: "j", scope: !45, type: !11)
!292 = !DILocation(column: 1, line: 346, scope: !45)
!293 = !DILocation(column: 13, line: 347, scope: !45)
!294 = !DILocation(column: 17, line: 348, scope: !45)
!295 = !DILocation(column: 17, line: 349, scope: !45)
!296 = !DILocation(column: 17, line: 350, scope: !45)
!297 = !DILocation(column: 17, line: 351, scope: !45)
!298 = !DILocation(column: 9, line: 352, scope: !45)
!299 = !DILocation(column: 5, line: 356, scope: !46)
!300 = !DILocalVariable(file: !0, line: 356, name: "failed", scope: !46, type: !10)
!301 = !DILocation(column: 1, line: 356, scope: !46)
!302 = !DILocation(column: 5, line: 357, scope: !46)
!303 = !DILocalVariable(file: !0, line: 357, name: "total", scope: !46, type: !10)
!304 = !DILocation(column: 1, line: 357, scope: !46)
!305 = !DILocation(column: 5, line: 358, scope: !46)
!306 = !DILocalVariable(file: !0, line: 358, name: "result", scope: !46, type: !10)
!307 = !DILocation(column: 1, line: 358, scope: !46)
!308 = !DILocation(column: 5, line: 360, scope: !46)
!309 = !DILocation(column: 5, line: 362, scope: !46)
!310 = !DILocation(column: 5, line: 363, scope: !46)
!311 = !DILocation(column: 5, line: 364, scope: !46)
!312 = !DILocation(column: 9, line: 365, scope: !46)
!313 = !DILocation(column: 5, line: 366, scope: !46)
!314 = !DILocation(column: 5, line: 368, scope: !46)
!315 = !DILocation(column: 5, line: 369, scope: !46)
!316 = !DILocation(column: 5, line: 370, scope: !46)
!317 = !DILocation(column: 9, line: 371, scope: !46)
!318 = !DILocation(column: 5, line: 372, scope: !46)
!319 = !DILocation(column: 5, line: 374, scope: !46)
!320 = !DILocation(column: 5, line: 375, scope: !46)
!321 = !DILocation(column: 5, line: 376, scope: !46)
!322 = !DILocation(column: 9, line: 377, scope: !46)
!323 = !DILocation(column: 5, line: 378, scope: !46)
!324 = !DILocation(column: 5, line: 380, scope: !46)
!325 = !DILocation(column: 5, line: 381, scope: !46)
!326 = !DILocation(column: 5, line: 382, scope: !46)
!327 = !DILocation(column: 9, line: 383, scope: !46)
!328 = !DILocation(column: 5, line: 384, scope: !46)
!329 = !DILocation(column: 5, line: 386, scope: !46)
!330 = !DILocation(column: 5, line: 387, scope: !46)
!331 = !DILocation(column: 5, line: 388, scope: !46)
!332 = !DILocation(column: 9, line: 389, scope: !46)
!333 = !DILocation(column: 5, line: 390, scope: !46)
!334 = !DILocation(column: 5, line: 392, scope: !46)
!335 = !DILocation(column: 5, line: 393, scope: !46)
!336 = !DILocation(column: 5, line: 394, scope: !46)
!337 = !DILocation(column: 9, line: 395, scope: !46)
!338 = !DILocation(column: 5, line: 396, scope: !46)
!339 = !DILocation(column: 5, line: 398, scope: !46)
!340 = !DILocation(column: 5, line: 399, scope: !46)
!341 = !DILocation(column: 5, line: 400, scope: !46)
!342 = !DILocation(column: 9, line: 401, scope: !46)
!343 = !DILocation(column: 5, line: 402, scope: !46)
!344 = !DILocation(column: 5, line: 404, scope: !46)
!345 = !DILocation(column: 5, line: 405, scope: !46)
!346 = !DILocation(column: 5, line: 406, scope: !46)
!347 = !DILocation(column: 9, line: 407, scope: !46)
!348 = !DILocation(column: 5, line: 408, scope: !46)
!349 = !DILocation(column: 5, line: 410, scope: !46)
!350 = !DILocation(column: 5, line: 411, scope: !46)
!351 = !DILocation(column: 5, line: 412, scope: !46)
!352 = !DILocation(column: 9, line: 413, scope: !46)
!353 = !DILocation(column: 5, line: 414, scope: !46)
!354 = !DILocation(column: 5, line: 417, scope: !46)
!355 = !DILocation(column: 5, line: 418, scope: !46)
!356 = !DILocation(column: 5, line: 419, scope: !46)
!357 = !DILocation(column: 9, line: 420, scope: !46)
!358 = !DILocation(column: 5, line: 421, scope: !46)
!359 = !DILocation(column: 5, line: 423, scope: !46)
!360 = !DILocation(column: 5, line: 424, scope: !46)
!361 = !DILocation(column: 5, line: 425, scope: !46)
!362 = !DILocation(column: 9, line: 426, scope: !46)
!363 = !DILocation(column: 5, line: 427, scope: !46)
!364 = !DILocation(column: 5, line: 429, scope: !46)
!365 = !DILocation(column: 5, line: 430, scope: !46)
!366 = !DILocation(column: 5, line: 431, scope: !46)
!367 = !DILocation(column: 9, line: 432, scope: !46)
!368 = !DILocation(column: 5, line: 433, scope: !46)
!369 = !DILocation(column: 5, line: 435, scope: !46)
!370 = !DILocation(column: 5, line: 436, scope: !46)
!371 = !DILocation(column: 5, line: 437, scope: !46)
!372 = !DILocation(column: 9, line: 438, scope: !46)
!373 = !DILocation(column: 5, line: 439, scope: !46)
!374 = !DILocation(column: 5, line: 441, scope: !46)
!375 = !DILocation(column: 5, line: 442, scope: !46)
!376 = !DILocation(column: 5, line: 443, scope: !46)
!377 = !DILocation(column: 9, line: 444, scope: !46)
!378 = !DILocation(column: 5, line: 445, scope: !46)
!379 = !DILocation(column: 5, line: 447, scope: !46)
!380 = !DILocation(column: 5, line: 448, scope: !46)
!381 = !DILocation(column: 5, line: 449, scope: !46)
!382 = !DILocation(column: 9, line: 450, scope: !46)
!383 = !DILocation(column: 5, line: 451, scope: !46)
!384 = !DILocation(column: 5, line: 453, scope: !46)
!385 = !DILocation(column: 5, line: 454, scope: !46)
!386 = !DILocation(column: 5, line: 459, scope: !46)