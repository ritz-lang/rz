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

define i8 @"get_char_row"(i8 %"ch.arg", i32 %"row.arg") !dbg !17
{
entry:
  %"ch" = alloca i8
  store i8 %"ch.arg", i8* %"ch"
  call void @"llvm.dbg.declare"(metadata i8* %"ch", metadata !25, metadata !7), !dbg !26
  %"row" = alloca i32
  store i32 %"row.arg", i32* %"row"
  call void @"llvm.dbg.declare"(metadata i32* %"row", metadata !27, metadata !7), !dbg !26
  %".8" = load i8, i8* %"ch", !dbg !28
  %".9" = zext i8 %".8" to i32 , !dbg !28
  %".10" = zext i32 %".9" to i64 , !dbg !28
  %".11" = icmp eq i64 %".10", 72 , !dbg !28
  br i1 %".11", label %"if.then", label %"if.end", !dbg !28
if.then:
  %".13" = load i32, i32* %"row", !dbg !29
  %".14" = sext i32 %".13" to i64 , !dbg !29
  %".15" = icmp eq i64 %".14", 0 , !dbg !29
  br i1 %".15", label %"if.then.1", label %"if.end.1", !dbg !29
if.end:
  %".57" = load i8, i8* %"ch", !dbg !44
  %".58" = zext i8 %".57" to i32 , !dbg !44
  %".59" = zext i32 %".58" to i64 , !dbg !44
  %".60" = icmp eq i64 %".59", 101 , !dbg !44
  br i1 %".60", label %"if.then.8", label %"if.end.8", !dbg !44
if.then.1:
  %".17" = trunc i64 17 to i8 , !dbg !30
  ret i8 %".17", !dbg !30
if.end.1:
  %".19" = load i32, i32* %"row", !dbg !31
  %".20" = sext i32 %".19" to i64 , !dbg !31
  %".21" = icmp eq i64 %".20", 1 , !dbg !31
  br i1 %".21", label %"if.then.2", label %"if.end.2", !dbg !31
if.then.2:
  %".23" = trunc i64 17 to i8 , !dbg !32
  ret i8 %".23", !dbg !32
if.end.2:
  %".25" = load i32, i32* %"row", !dbg !33
  %".26" = sext i32 %".25" to i64 , !dbg !33
  %".27" = icmp eq i64 %".26", 2 , !dbg !33
  br i1 %".27", label %"if.then.3", label %"if.end.3", !dbg !33
if.then.3:
  %".29" = trunc i64 17 to i8 , !dbg !34
  ret i8 %".29", !dbg !34
if.end.3:
  %".31" = load i32, i32* %"row", !dbg !35
  %".32" = sext i32 %".31" to i64 , !dbg !35
  %".33" = icmp eq i64 %".32", 3 , !dbg !35
  br i1 %".33", label %"if.then.4", label %"if.end.4", !dbg !35
if.then.4:
  %".35" = trunc i64 31 to i8 , !dbg !36
  ret i8 %".35", !dbg !36
if.end.4:
  %".37" = load i32, i32* %"row", !dbg !37
  %".38" = sext i32 %".37" to i64 , !dbg !37
  %".39" = icmp eq i64 %".38", 4 , !dbg !37
  br i1 %".39", label %"if.then.5", label %"if.end.5", !dbg !37
if.then.5:
  %".41" = trunc i64 17 to i8 , !dbg !38
  ret i8 %".41", !dbg !38
if.end.5:
  %".43" = load i32, i32* %"row", !dbg !39
  %".44" = sext i32 %".43" to i64 , !dbg !39
  %".45" = icmp eq i64 %".44", 5 , !dbg !39
  br i1 %".45", label %"if.then.6", label %"if.end.6", !dbg !39
if.then.6:
  %".47" = trunc i64 17 to i8 , !dbg !40
  ret i8 %".47", !dbg !40
if.end.6:
  %".49" = load i32, i32* %"row", !dbg !41
  %".50" = sext i32 %".49" to i64 , !dbg !41
  %".51" = icmp eq i64 %".50", 6 , !dbg !41
  br i1 %".51", label %"if.then.7", label %"if.end.7", !dbg !41
if.then.7:
  %".53" = trunc i64 17 to i8 , !dbg !42
  ret i8 %".53", !dbg !42
if.end.7:
  %".55" = trunc i64 0 to i8 , !dbg !43
  ret i8 %".55", !dbg !43
if.then.8:
  %".62" = load i32, i32* %"row", !dbg !45
  %".63" = sext i32 %".62" to i64 , !dbg !45
  %".64" = icmp eq i64 %".63", 0 , !dbg !45
  br i1 %".64", label %"if.then.9", label %"if.end.9", !dbg !45
if.end.8:
  %".106" = load i8, i8* %"ch", !dbg !60
  %".107" = zext i8 %".106" to i32 , !dbg !60
  %".108" = zext i32 %".107" to i64 , !dbg !60
  %".109" = icmp eq i64 %".108", 108 , !dbg !60
  br i1 %".109", label %"if.then.16", label %"if.end.16", !dbg !60
if.then.9:
  %".66" = trunc i64 0 to i8 , !dbg !46
  ret i8 %".66", !dbg !46
if.end.9:
  %".68" = load i32, i32* %"row", !dbg !47
  %".69" = sext i32 %".68" to i64 , !dbg !47
  %".70" = icmp eq i64 %".69", 1 , !dbg !47
  br i1 %".70", label %"if.then.10", label %"if.end.10", !dbg !47
if.then.10:
  %".72" = trunc i64 0 to i8 , !dbg !48
  ret i8 %".72", !dbg !48
if.end.10:
  %".74" = load i32, i32* %"row", !dbg !49
  %".75" = sext i32 %".74" to i64 , !dbg !49
  %".76" = icmp eq i64 %".75", 2 , !dbg !49
  br i1 %".76", label %"if.then.11", label %"if.end.11", !dbg !49
if.then.11:
  %".78" = trunc i64 14 to i8 , !dbg !50
  ret i8 %".78", !dbg !50
if.end.11:
  %".80" = load i32, i32* %"row", !dbg !51
  %".81" = sext i32 %".80" to i64 , !dbg !51
  %".82" = icmp eq i64 %".81", 3 , !dbg !51
  br i1 %".82", label %"if.then.12", label %"if.end.12", !dbg !51
if.then.12:
  %".84" = trunc i64 17 to i8 , !dbg !52
  ret i8 %".84", !dbg !52
if.end.12:
  %".86" = load i32, i32* %"row", !dbg !53
  %".87" = sext i32 %".86" to i64 , !dbg !53
  %".88" = icmp eq i64 %".87", 4 , !dbg !53
  br i1 %".88", label %"if.then.13", label %"if.end.13", !dbg !53
if.then.13:
  %".90" = trunc i64 31 to i8 , !dbg !54
  ret i8 %".90", !dbg !54
if.end.13:
  %".92" = load i32, i32* %"row", !dbg !55
  %".93" = sext i32 %".92" to i64 , !dbg !55
  %".94" = icmp eq i64 %".93", 5 , !dbg !55
  br i1 %".94", label %"if.then.14", label %"if.end.14", !dbg !55
if.then.14:
  %".96" = trunc i64 16 to i8 , !dbg !56
  ret i8 %".96", !dbg !56
if.end.14:
  %".98" = load i32, i32* %"row", !dbg !57
  %".99" = sext i32 %".98" to i64 , !dbg !57
  %".100" = icmp eq i64 %".99", 6 , !dbg !57
  br i1 %".100", label %"if.then.15", label %"if.end.15", !dbg !57
if.then.15:
  %".102" = trunc i64 14 to i8 , !dbg !58
  ret i8 %".102", !dbg !58
if.end.15:
  %".104" = trunc i64 0 to i8 , !dbg !59
  ret i8 %".104", !dbg !59
if.then.16:
  %".111" = load i32, i32* %"row", !dbg !61
  %".112" = sext i32 %".111" to i64 , !dbg !61
  %".113" = icmp eq i64 %".112", 0 , !dbg !61
  br i1 %".113", label %"if.then.17", label %"if.end.17", !dbg !61
if.end.16:
  %".155" = load i8, i8* %"ch", !dbg !76
  %".156" = zext i8 %".155" to i32 , !dbg !76
  %".157" = zext i32 %".156" to i64 , !dbg !76
  %".158" = icmp eq i64 %".157", 111 , !dbg !76
  br i1 %".158", label %"if.then.24", label %"if.end.24", !dbg !76
if.then.17:
  %".115" = trunc i64 12 to i8 , !dbg !62
  ret i8 %".115", !dbg !62
if.end.17:
  %".117" = load i32, i32* %"row", !dbg !63
  %".118" = sext i32 %".117" to i64 , !dbg !63
  %".119" = icmp eq i64 %".118", 1 , !dbg !63
  br i1 %".119", label %"if.then.18", label %"if.end.18", !dbg !63
if.then.18:
  %".121" = trunc i64 4 to i8 , !dbg !64
  ret i8 %".121", !dbg !64
if.end.18:
  %".123" = load i32, i32* %"row", !dbg !65
  %".124" = sext i32 %".123" to i64 , !dbg !65
  %".125" = icmp eq i64 %".124", 2 , !dbg !65
  br i1 %".125", label %"if.then.19", label %"if.end.19", !dbg !65
if.then.19:
  %".127" = trunc i64 4 to i8 , !dbg !66
  ret i8 %".127", !dbg !66
if.end.19:
  %".129" = load i32, i32* %"row", !dbg !67
  %".130" = sext i32 %".129" to i64 , !dbg !67
  %".131" = icmp eq i64 %".130", 3 , !dbg !67
  br i1 %".131", label %"if.then.20", label %"if.end.20", !dbg !67
if.then.20:
  %".133" = trunc i64 4 to i8 , !dbg !68
  ret i8 %".133", !dbg !68
if.end.20:
  %".135" = load i32, i32* %"row", !dbg !69
  %".136" = sext i32 %".135" to i64 , !dbg !69
  %".137" = icmp eq i64 %".136", 4 , !dbg !69
  br i1 %".137", label %"if.then.21", label %"if.end.21", !dbg !69
if.then.21:
  %".139" = trunc i64 4 to i8 , !dbg !70
  ret i8 %".139", !dbg !70
if.end.21:
  %".141" = load i32, i32* %"row", !dbg !71
  %".142" = sext i32 %".141" to i64 , !dbg !71
  %".143" = icmp eq i64 %".142", 5 , !dbg !71
  br i1 %".143", label %"if.then.22", label %"if.end.22", !dbg !71
if.then.22:
  %".145" = trunc i64 4 to i8 , !dbg !72
  ret i8 %".145", !dbg !72
if.end.22:
  %".147" = load i32, i32* %"row", !dbg !73
  %".148" = sext i32 %".147" to i64 , !dbg !73
  %".149" = icmp eq i64 %".148", 6 , !dbg !73
  br i1 %".149", label %"if.then.23", label %"if.end.23", !dbg !73
if.then.23:
  %".151" = trunc i64 14 to i8 , !dbg !74
  ret i8 %".151", !dbg !74
if.end.23:
  %".153" = trunc i64 0 to i8 , !dbg !75
  ret i8 %".153", !dbg !75
if.then.24:
  %".160" = load i32, i32* %"row", !dbg !77
  %".161" = sext i32 %".160" to i64 , !dbg !77
  %".162" = icmp eq i64 %".161", 0 , !dbg !77
  br i1 %".162", label %"if.then.25", label %"if.end.25", !dbg !77
if.end.24:
  %".204" = load i8, i8* %"ch", !dbg !92
  %".205" = zext i8 %".204" to i32 , !dbg !92
  %".206" = zext i32 %".205" to i64 , !dbg !92
  %".207" = icmp eq i64 %".206", 32 , !dbg !92
  br i1 %".207", label %"if.then.32", label %"if.end.32", !dbg !92
if.then.25:
  %".164" = trunc i64 0 to i8 , !dbg !78
  ret i8 %".164", !dbg !78
if.end.25:
  %".166" = load i32, i32* %"row", !dbg !79
  %".167" = sext i32 %".166" to i64 , !dbg !79
  %".168" = icmp eq i64 %".167", 1 , !dbg !79
  br i1 %".168", label %"if.then.26", label %"if.end.26", !dbg !79
if.then.26:
  %".170" = trunc i64 0 to i8 , !dbg !80
  ret i8 %".170", !dbg !80
if.end.26:
  %".172" = load i32, i32* %"row", !dbg !81
  %".173" = sext i32 %".172" to i64 , !dbg !81
  %".174" = icmp eq i64 %".173", 2 , !dbg !81
  br i1 %".174", label %"if.then.27", label %"if.end.27", !dbg !81
if.then.27:
  %".176" = trunc i64 14 to i8 , !dbg !82
  ret i8 %".176", !dbg !82
if.end.27:
  %".178" = load i32, i32* %"row", !dbg !83
  %".179" = sext i32 %".178" to i64 , !dbg !83
  %".180" = icmp eq i64 %".179", 3 , !dbg !83
  br i1 %".180", label %"if.then.28", label %"if.end.28", !dbg !83
if.then.28:
  %".182" = trunc i64 17 to i8 , !dbg !84
  ret i8 %".182", !dbg !84
if.end.28:
  %".184" = load i32, i32* %"row", !dbg !85
  %".185" = sext i32 %".184" to i64 , !dbg !85
  %".186" = icmp eq i64 %".185", 4 , !dbg !85
  br i1 %".186", label %"if.then.29", label %"if.end.29", !dbg !85
if.then.29:
  %".188" = trunc i64 17 to i8 , !dbg !86
  ret i8 %".188", !dbg !86
if.end.29:
  %".190" = load i32, i32* %"row", !dbg !87
  %".191" = sext i32 %".190" to i64 , !dbg !87
  %".192" = icmp eq i64 %".191", 5 , !dbg !87
  br i1 %".192", label %"if.then.30", label %"if.end.30", !dbg !87
if.then.30:
  %".194" = trunc i64 17 to i8 , !dbg !88
  ret i8 %".194", !dbg !88
if.end.30:
  %".196" = load i32, i32* %"row", !dbg !89
  %".197" = sext i32 %".196" to i64 , !dbg !89
  %".198" = icmp eq i64 %".197", 6 , !dbg !89
  br i1 %".198", label %"if.then.31", label %"if.end.31", !dbg !89
if.then.31:
  %".200" = trunc i64 14 to i8 , !dbg !90
  ret i8 %".200", !dbg !90
if.end.31:
  %".202" = trunc i64 0 to i8 , !dbg !91
  ret i8 %".202", !dbg !91
if.then.32:
  %".209" = trunc i64 0 to i8 , !dbg !93
  ret i8 %".209", !dbg !93
if.end.32:
  %".211" = load i8, i8* %"ch", !dbg !94
  %".212" = zext i8 %".211" to i32 , !dbg !94
  %".213" = zext i32 %".212" to i64 , !dbg !94
  %".214" = icmp eq i64 %".213", 87 , !dbg !94
  br i1 %".214", label %"if.then.33", label %"if.end.33", !dbg !94
if.then.33:
  %".216" = load i32, i32* %"row", !dbg !95
  %".217" = sext i32 %".216" to i64 , !dbg !95
  %".218" = icmp eq i64 %".217", 0 , !dbg !95
  br i1 %".218", label %"if.then.34", label %"if.end.34", !dbg !95
if.end.33:
  %".260" = load i8, i8* %"ch", !dbg !110
  %".261" = zext i8 %".260" to i32 , !dbg !110
  %".262" = zext i32 %".261" to i64 , !dbg !110
  %".263" = icmp eq i64 %".262", 114 , !dbg !110
  br i1 %".263", label %"if.then.41", label %"if.end.41", !dbg !110
if.then.34:
  %".220" = trunc i64 17 to i8 , !dbg !96
  ret i8 %".220", !dbg !96
if.end.34:
  %".222" = load i32, i32* %"row", !dbg !97
  %".223" = sext i32 %".222" to i64 , !dbg !97
  %".224" = icmp eq i64 %".223", 1 , !dbg !97
  br i1 %".224", label %"if.then.35", label %"if.end.35", !dbg !97
if.then.35:
  %".226" = trunc i64 17 to i8 , !dbg !98
  ret i8 %".226", !dbg !98
if.end.35:
  %".228" = load i32, i32* %"row", !dbg !99
  %".229" = sext i32 %".228" to i64 , !dbg !99
  %".230" = icmp eq i64 %".229", 2 , !dbg !99
  br i1 %".230", label %"if.then.36", label %"if.end.36", !dbg !99
if.then.36:
  %".232" = trunc i64 17 to i8 , !dbg !100
  ret i8 %".232", !dbg !100
if.end.36:
  %".234" = load i32, i32* %"row", !dbg !101
  %".235" = sext i32 %".234" to i64 , !dbg !101
  %".236" = icmp eq i64 %".235", 3 , !dbg !101
  br i1 %".236", label %"if.then.37", label %"if.end.37", !dbg !101
if.then.37:
  %".238" = trunc i64 21 to i8 , !dbg !102
  ret i8 %".238", !dbg !102
if.end.37:
  %".240" = load i32, i32* %"row", !dbg !103
  %".241" = sext i32 %".240" to i64 , !dbg !103
  %".242" = icmp eq i64 %".241", 4 , !dbg !103
  br i1 %".242", label %"if.then.38", label %"if.end.38", !dbg !103
if.then.38:
  %".244" = trunc i64 21 to i8 , !dbg !104
  ret i8 %".244", !dbg !104
if.end.38:
  %".246" = load i32, i32* %"row", !dbg !105
  %".247" = sext i32 %".246" to i64 , !dbg !105
  %".248" = icmp eq i64 %".247", 5 , !dbg !105
  br i1 %".248", label %"if.then.39", label %"if.end.39", !dbg !105
if.then.39:
  %".250" = trunc i64 21 to i8 , !dbg !106
  ret i8 %".250", !dbg !106
if.end.39:
  %".252" = load i32, i32* %"row", !dbg !107
  %".253" = sext i32 %".252" to i64 , !dbg !107
  %".254" = icmp eq i64 %".253", 6 , !dbg !107
  br i1 %".254", label %"if.then.40", label %"if.end.40", !dbg !107
if.then.40:
  %".256" = trunc i64 10 to i8 , !dbg !108
  ret i8 %".256", !dbg !108
if.end.40:
  %".258" = trunc i64 0 to i8 , !dbg !109
  ret i8 %".258", !dbg !109
if.then.41:
  %".265" = load i32, i32* %"row", !dbg !111
  %".266" = sext i32 %".265" to i64 , !dbg !111
  %".267" = icmp eq i64 %".266", 0 , !dbg !111
  br i1 %".267", label %"if.then.42", label %"if.end.42", !dbg !111
if.end.41:
  %".309" = load i8, i8* %"ch", !dbg !126
  %".310" = zext i8 %".309" to i32 , !dbg !126
  %".311" = zext i32 %".310" to i64 , !dbg !126
  %".312" = icmp eq i64 %".311", 100 , !dbg !126
  br i1 %".312", label %"if.then.49", label %"if.end.49", !dbg !126
if.then.42:
  %".269" = trunc i64 0 to i8 , !dbg !112
  ret i8 %".269", !dbg !112
if.end.42:
  %".271" = load i32, i32* %"row", !dbg !113
  %".272" = sext i32 %".271" to i64 , !dbg !113
  %".273" = icmp eq i64 %".272", 1 , !dbg !113
  br i1 %".273", label %"if.then.43", label %"if.end.43", !dbg !113
if.then.43:
  %".275" = trunc i64 0 to i8 , !dbg !114
  ret i8 %".275", !dbg !114
if.end.43:
  %".277" = load i32, i32* %"row", !dbg !115
  %".278" = sext i32 %".277" to i64 , !dbg !115
  %".279" = icmp eq i64 %".278", 2 , !dbg !115
  br i1 %".279", label %"if.then.44", label %"if.end.44", !dbg !115
if.then.44:
  %".281" = trunc i64 22 to i8 , !dbg !116
  ret i8 %".281", !dbg !116
if.end.44:
  %".283" = load i32, i32* %"row", !dbg !117
  %".284" = sext i32 %".283" to i64 , !dbg !117
  %".285" = icmp eq i64 %".284", 3 , !dbg !117
  br i1 %".285", label %"if.then.45", label %"if.end.45", !dbg !117
if.then.45:
  %".287" = trunc i64 25 to i8 , !dbg !118
  ret i8 %".287", !dbg !118
if.end.45:
  %".289" = load i32, i32* %"row", !dbg !119
  %".290" = sext i32 %".289" to i64 , !dbg !119
  %".291" = icmp eq i64 %".290", 4 , !dbg !119
  br i1 %".291", label %"if.then.46", label %"if.end.46", !dbg !119
if.then.46:
  %".293" = trunc i64 16 to i8 , !dbg !120
  ret i8 %".293", !dbg !120
if.end.46:
  %".295" = load i32, i32* %"row", !dbg !121
  %".296" = sext i32 %".295" to i64 , !dbg !121
  %".297" = icmp eq i64 %".296", 5 , !dbg !121
  br i1 %".297", label %"if.then.47", label %"if.end.47", !dbg !121
if.then.47:
  %".299" = trunc i64 16 to i8 , !dbg !122
  ret i8 %".299", !dbg !122
if.end.47:
  %".301" = load i32, i32* %"row", !dbg !123
  %".302" = sext i32 %".301" to i64 , !dbg !123
  %".303" = icmp eq i64 %".302", 6 , !dbg !123
  br i1 %".303", label %"if.then.48", label %"if.end.48", !dbg !123
if.then.48:
  %".305" = trunc i64 16 to i8 , !dbg !124
  ret i8 %".305", !dbg !124
if.end.48:
  %".307" = trunc i64 0 to i8 , !dbg !125
  ret i8 %".307", !dbg !125
if.then.49:
  %".314" = load i32, i32* %"row", !dbg !127
  %".315" = sext i32 %".314" to i64 , !dbg !127
  %".316" = icmp eq i64 %".315", 0 , !dbg !127
  br i1 %".316", label %"if.then.50", label %"if.end.50", !dbg !127
if.end.49:
  %".358" = load i8, i8* %"ch", !dbg !142
  %".359" = zext i8 %".358" to i32 , !dbg !142
  %".360" = zext i32 %".359" to i64 , !dbg !142
  %".361" = icmp eq i64 %".360", 33 , !dbg !142
  br i1 %".361", label %"if.then.57", label %"if.end.57", !dbg !142
if.then.50:
  %".318" = trunc i64 1 to i8 , !dbg !128
  ret i8 %".318", !dbg !128
if.end.50:
  %".320" = load i32, i32* %"row", !dbg !129
  %".321" = sext i32 %".320" to i64 , !dbg !129
  %".322" = icmp eq i64 %".321", 1 , !dbg !129
  br i1 %".322", label %"if.then.51", label %"if.end.51", !dbg !129
if.then.51:
  %".324" = trunc i64 1 to i8 , !dbg !130
  ret i8 %".324", !dbg !130
if.end.51:
  %".326" = load i32, i32* %"row", !dbg !131
  %".327" = sext i32 %".326" to i64 , !dbg !131
  %".328" = icmp eq i64 %".327", 2 , !dbg !131
  br i1 %".328", label %"if.then.52", label %"if.end.52", !dbg !131
if.then.52:
  %".330" = trunc i64 13 to i8 , !dbg !132
  ret i8 %".330", !dbg !132
if.end.52:
  %".332" = load i32, i32* %"row", !dbg !133
  %".333" = sext i32 %".332" to i64 , !dbg !133
  %".334" = icmp eq i64 %".333", 3 , !dbg !133
  br i1 %".334", label %"if.then.53", label %"if.end.53", !dbg !133
if.then.53:
  %".336" = trunc i64 19 to i8 , !dbg !134
  ret i8 %".336", !dbg !134
if.end.53:
  %".338" = load i32, i32* %"row", !dbg !135
  %".339" = sext i32 %".338" to i64 , !dbg !135
  %".340" = icmp eq i64 %".339", 4 , !dbg !135
  br i1 %".340", label %"if.then.54", label %"if.end.54", !dbg !135
if.then.54:
  %".342" = trunc i64 17 to i8 , !dbg !136
  ret i8 %".342", !dbg !136
if.end.54:
  %".344" = load i32, i32* %"row", !dbg !137
  %".345" = sext i32 %".344" to i64 , !dbg !137
  %".346" = icmp eq i64 %".345", 5 , !dbg !137
  br i1 %".346", label %"if.then.55", label %"if.end.55", !dbg !137
if.then.55:
  %".348" = trunc i64 19 to i8 , !dbg !138
  ret i8 %".348", !dbg !138
if.end.55:
  %".350" = load i32, i32* %"row", !dbg !139
  %".351" = sext i32 %".350" to i64 , !dbg !139
  %".352" = icmp eq i64 %".351", 6 , !dbg !139
  br i1 %".352", label %"if.then.56", label %"if.end.56", !dbg !139
if.then.56:
  %".354" = trunc i64 13 to i8 , !dbg !140
  ret i8 %".354", !dbg !140
if.end.56:
  %".356" = trunc i64 0 to i8 , !dbg !141
  ret i8 %".356", !dbg !141
if.then.57:
  %".363" = load i32, i32* %"row", !dbg !143
  %".364" = sext i32 %".363" to i64 , !dbg !143
  %".365" = icmp eq i64 %".364", 0 , !dbg !143
  br i1 %".365", label %"if.then.58", label %"if.end.58", !dbg !143
if.end.57:
  %".407" = trunc i64 31 to i8 , !dbg !158
  ret i8 %".407", !dbg !158
if.then.58:
  %".367" = trunc i64 4 to i8 , !dbg !144
  ret i8 %".367", !dbg !144
if.end.58:
  %".369" = load i32, i32* %"row", !dbg !145
  %".370" = sext i32 %".369" to i64 , !dbg !145
  %".371" = icmp eq i64 %".370", 1 , !dbg !145
  br i1 %".371", label %"if.then.59", label %"if.end.59", !dbg !145
if.then.59:
  %".373" = trunc i64 4 to i8 , !dbg !146
  ret i8 %".373", !dbg !146
if.end.59:
  %".375" = load i32, i32* %"row", !dbg !147
  %".376" = sext i32 %".375" to i64 , !dbg !147
  %".377" = icmp eq i64 %".376", 2 , !dbg !147
  br i1 %".377", label %"if.then.60", label %"if.end.60", !dbg !147
if.then.60:
  %".379" = trunc i64 4 to i8 , !dbg !148
  ret i8 %".379", !dbg !148
if.end.60:
  %".381" = load i32, i32* %"row", !dbg !149
  %".382" = sext i32 %".381" to i64 , !dbg !149
  %".383" = icmp eq i64 %".382", 3 , !dbg !149
  br i1 %".383", label %"if.then.61", label %"if.end.61", !dbg !149
if.then.61:
  %".385" = trunc i64 4 to i8 , !dbg !150
  ret i8 %".385", !dbg !150
if.end.61:
  %".387" = load i32, i32* %"row", !dbg !151
  %".388" = sext i32 %".387" to i64 , !dbg !151
  %".389" = icmp eq i64 %".388", 4 , !dbg !151
  br i1 %".389", label %"if.then.62", label %"if.end.62", !dbg !151
if.then.62:
  %".391" = trunc i64 4 to i8 , !dbg !152
  ret i8 %".391", !dbg !152
if.end.62:
  %".393" = load i32, i32* %"row", !dbg !153
  %".394" = sext i32 %".393" to i64 , !dbg !153
  %".395" = icmp eq i64 %".394", 5 , !dbg !153
  br i1 %".395", label %"if.then.63", label %"if.end.63", !dbg !153
if.then.63:
  %".397" = trunc i64 0 to i8 , !dbg !154
  ret i8 %".397", !dbg !154
if.end.63:
  %".399" = load i32, i32* %"row", !dbg !155
  %".400" = sext i32 %".399" to i64 , !dbg !155
  %".401" = icmp eq i64 %".400", 6 , !dbg !155
  br i1 %".401", label %"if.then.64", label %"if.end.64", !dbg !155
if.then.64:
  %".403" = trunc i64 4 to i8 , !dbg !156
  ret i8 %".403", !dbg !156
if.end.64:
  %".405" = trunc i64 0 to i8 , !dbg !157
  ret i8 %".405", !dbg !157
}

define i32 @"set_pixel"(i8* %"buffer.arg", i32 %"x.arg", i32 %"y.arg", i32 %"color.arg") !dbg !18
{
entry:
  %"buffer" = alloca i8*
  store i8* %"buffer.arg", i8** %"buffer"
  call void @"llvm.dbg.declare"(metadata i8** %"buffer", metadata !160, metadata !7), !dbg !161
  %"x" = alloca i32
  store i32 %"x.arg", i32* %"x"
  call void @"llvm.dbg.declare"(metadata i32* %"x", metadata !162, metadata !7), !dbg !161
  %"y" = alloca i32
  store i32 %"y.arg", i32* %"y"
  call void @"llvm.dbg.declare"(metadata i32* %"y", metadata !163, metadata !7), !dbg !161
  %"color" = alloca i32
  store i32 %"color.arg", i32* %"color"
  call void @"llvm.dbg.declare"(metadata i32* %"color", metadata !164, metadata !7), !dbg !161
  %".14" = load i32, i32* %"x", !dbg !165
  %".15" = icmp uge i32 %".14", 200 , !dbg !165
  br i1 %".15", label %"or.merge", label %"or.right", !dbg !165
or.right:
  %".17" = load i32, i32* %"y", !dbg !165
  %".18" = icmp uge i32 %".17", 50 , !dbg !165
  br label %"or.merge", !dbg !165
or.merge:
  %".20" = phi  i1 [1, %"entry"], [%".18", %"or.right"] , !dbg !165
  br i1 %".20", label %"if.then", label %"if.end", !dbg !165
if.then:
  ret i32 0, !dbg !166
if.end:
  %".23" = load i32, i32* %"y", !dbg !167
  %".24" = mul i32 %".23", 200, !dbg !167
  %".25" = load i32, i32* %"x", !dbg !167
  %".26" = add i32 %".24", %".25", !dbg !167
  %".27" = sext i32 %".26" to i64 , !dbg !167
  %".28" = mul i64 %".27", 3, !dbg !167
  %".29" = load i32, i32* %"color", !dbg !168
  %".30" = zext i32 %".29" to i64 , !dbg !168
  %".31" = lshr i64 %".30", 16, !dbg !168
  %".32" = sdiv i64 %".31", 256, !dbg !168
  %".33" = mul i64 %".32", 256, !dbg !168
  %".34" = load i32, i32* %"color", !dbg !168
  %".35" = zext i32 %".34" to i64 , !dbg !168
  %".36" = lshr i64 %".35", 16, !dbg !168
  %".37" = srem i64 %".36", 256, !dbg !168
  %".38" = add i64 %".33", %".37", !dbg !168
  %".39" = trunc i64 %".38" to i8 , !dbg !168
  %".40" = load i32, i32* %"color", !dbg !169
  %".41" = zext i32 %".40" to i64 , !dbg !169
  %".42" = lshr i64 %".41", 8, !dbg !169
  %".43" = srem i64 %".42", 256, !dbg !169
  %".44" = trunc i64 %".43" to i8 , !dbg !169
  %".45" = load i32, i32* %"color", !dbg !170
  %".46" = zext i32 %".45" to i64 , !dbg !170
  %".47" = urem i64 %".46", 256, !dbg !170
  %".48" = trunc i64 %".47" to i8 , !dbg !170
  %".49" = load i32, i32* %"color", !dbg !171
  %".50" = zext i32 %".49" to i64 , !dbg !171
  %".51" = lshr i64 %".50", 16, !dbg !171
  %".52" = trunc i64 %".51" to i32 , !dbg !171
  %".53" = zext i32 %".52" to i64 , !dbg !171
  %".54" = urem i64 %".53", 256, !dbg !171
  %".55" = trunc i64 %".54" to i8 , !dbg !171
  %".56" = load i8*, i8** %"buffer", !dbg !171
  %".57" = getelementptr i8, i8* %".56", i64 %".28" , !dbg !171
  store i8 %".55", i8* %".57", !dbg !171
  %".59" = load i32, i32* %"color", !dbg !172
  %".60" = zext i32 %".59" to i64 , !dbg !172
  %".61" = lshr i64 %".60", 8, !dbg !172
  %".62" = trunc i64 %".61" to i32 , !dbg !172
  %".63" = zext i32 %".62" to i64 , !dbg !172
  %".64" = urem i64 %".63", 256, !dbg !172
  %".65" = trunc i64 %".64" to i8 , !dbg !172
  %".66" = load i8*, i8** %"buffer", !dbg !172
  %".67" = getelementptr i8, i8* %".66", i64 %".28" , !dbg !172
  %".68" = getelementptr i8, i8* %".67", i64 1 , !dbg !172
  store i8 %".65", i8* %".68", !dbg !172
  %".70" = load i32, i32* %"color", !dbg !173
  %".71" = zext i32 %".70" to i64 , !dbg !173
  %".72" = urem i64 %".71", 256, !dbg !173
  %".73" = trunc i64 %".72" to i8 , !dbg !173
  %".74" = load i8*, i8** %"buffer", !dbg !173
  %".75" = getelementptr i8, i8* %".74", i64 %".28" , !dbg !173
  %".76" = getelementptr i8, i8* %".75", i64 2 , !dbg !173
  store i8 %".73", i8* %".76", !dbg !173
  ret i32 0, !dbg !173
}

define i32 @"fill_rect"(i8* %"buffer.arg", i32 %"x.arg", i32 %"y.arg", i32 %"w.arg", i32 %"h.arg", i32 %"color.arg") !dbg !19
{
entry:
  %"buffer" = alloca i8*
  %"py.addr" = alloca i32, !dbg !181
  %"px.addr" = alloca i32, !dbg !185
  store i8* %"buffer.arg", i8** %"buffer"
  call void @"llvm.dbg.declare"(metadata i8** %"buffer", metadata !174, metadata !7), !dbg !175
  %"x" = alloca i32
  store i32 %"x.arg", i32* %"x"
  call void @"llvm.dbg.declare"(metadata i32* %"x", metadata !176, metadata !7), !dbg !175
  %"y" = alloca i32
  store i32 %"y.arg", i32* %"y"
  call void @"llvm.dbg.declare"(metadata i32* %"y", metadata !177, metadata !7), !dbg !175
  %"w" = alloca i32
  store i32 %"w.arg", i32* %"w"
  call void @"llvm.dbg.declare"(metadata i32* %"w", metadata !178, metadata !7), !dbg !175
  %"h" = alloca i32
  store i32 %"h.arg", i32* %"h"
  call void @"llvm.dbg.declare"(metadata i32* %"h", metadata !179, metadata !7), !dbg !175
  %"color" = alloca i32
  store i32 %"color.arg", i32* %"color"
  call void @"llvm.dbg.declare"(metadata i32* %"color", metadata !180, metadata !7), !dbg !175
  %".20" = trunc i64 0 to i32 , !dbg !181
  store i32 %".20", i32* %"py.addr", !dbg !181
  call void @"llvm.dbg.declare"(metadata i32* %"py.addr", metadata !182, metadata !7), !dbg !183
  br label %"while.cond", !dbg !184
while.cond:
  %".24" = load i32, i32* %"py.addr", !dbg !184
  %".25" = load i32, i32* %"h", !dbg !184
  %".26" = icmp ult i32 %".24", %".25" , !dbg !184
  br i1 %".26", label %"while.body", label %"while.end", !dbg !184
while.body:
  %".28" = trunc i64 0 to i32 , !dbg !185
  store i32 %".28", i32* %"px.addr", !dbg !185
  call void @"llvm.dbg.declare"(metadata i32* %"px.addr", metadata !186, metadata !7), !dbg !187
  br label %"while.cond.1", !dbg !188
while.end:
  ret i32 0, !dbg !191
while.cond.1:
  %".32" = load i32, i32* %"px.addr", !dbg !188
  %".33" = load i32, i32* %"w", !dbg !188
  %".34" = icmp ult i32 %".32", %".33" , !dbg !188
  br i1 %".34", label %"while.body.1", label %"while.end.1", !dbg !188
while.body.1:
  %".36" = load i8*, i8** %"buffer", !dbg !189
  %".37" = load i32, i32* %"x", !dbg !189
  %".38" = load i32, i32* %"px.addr", !dbg !189
  %".39" = add i32 %".37", %".38", !dbg !189
  %".40" = load i32, i32* %"y", !dbg !189
  %".41" = load i32, i32* %"py.addr", !dbg !189
  %".42" = add i32 %".40", %".41", !dbg !189
  %".43" = load i32, i32* %"color", !dbg !189
  %".44" = call i32 @"set_pixel"(i8* %".36", i32 %".39", i32 %".42", i32 %".43"), !dbg !189
  %".45" = load i32, i32* %"px.addr", !dbg !190
  %".46" = zext i32 %".45" to i64 , !dbg !190
  %".47" = add i64 %".46", 1, !dbg !190
  %".48" = trunc i64 %".47" to i32 , !dbg !190
  store i32 %".48", i32* %"px.addr", !dbg !190
  br label %"while.cond.1", !dbg !190
while.end.1:
  %".51" = load i32, i32* %"py.addr", !dbg !191
  %".52" = zext i32 %".51" to i64 , !dbg !191
  %".53" = add i64 %".52", 1, !dbg !191
  %".54" = trunc i64 %".53" to i32 , !dbg !191
  store i32 %".54", i32* %"py.addr", !dbg !191
  br label %"while.cond", !dbg !191
}

define i32 @"draw_char"(i8* %"buffer.arg", i8 %"ch.arg", i32 %"x.arg", i32 %"y.arg", i32 %"color.arg", i32 %"scale.arg") !dbg !20
{
entry:
  %"buffer" = alloca i8*
  %"row.addr" = alloca i32, !dbg !199
  %"col.addr" = alloca i32, !dbg !204
  %"shifted.addr" = alloca i8, !dbg !210
  %"i.addr" = alloca i32, !dbg !213
  %"sy.addr" = alloca i32, !dbg !220
  %"sx.addr" = alloca i32, !dbg !224
  store i8* %"buffer.arg", i8** %"buffer"
  call void @"llvm.dbg.declare"(metadata i8** %"buffer", metadata !192, metadata !7), !dbg !193
  %"ch" = alloca i8
  store i8 %"ch.arg", i8* %"ch"
  call void @"llvm.dbg.declare"(metadata i8* %"ch", metadata !194, metadata !7), !dbg !193
  %"x" = alloca i32
  store i32 %"x.arg", i32* %"x"
  call void @"llvm.dbg.declare"(metadata i32* %"x", metadata !195, metadata !7), !dbg !193
  %"y" = alloca i32
  store i32 %"y.arg", i32* %"y"
  call void @"llvm.dbg.declare"(metadata i32* %"y", metadata !196, metadata !7), !dbg !193
  %"color" = alloca i32
  store i32 %"color.arg", i32* %"color"
  call void @"llvm.dbg.declare"(metadata i32* %"color", metadata !197, metadata !7), !dbg !193
  %"scale" = alloca i32
  store i32 %"scale.arg", i32* %"scale"
  call void @"llvm.dbg.declare"(metadata i32* %"scale", metadata !198, metadata !7), !dbg !193
  %".20" = trunc i64 0 to i32 , !dbg !199
  store i32 %".20", i32* %"row.addr", !dbg !199
  call void @"llvm.dbg.declare"(metadata i32* %"row.addr", metadata !200, metadata !7), !dbg !201
  br label %"while.cond", !dbg !202
while.cond:
  %".24" = load i32, i32* %"row.addr", !dbg !202
  %".25" = sext i32 %".24" to i64 , !dbg !202
  %".26" = icmp slt i64 %".25", 7 , !dbg !202
  br i1 %".26", label %"while.body", label %"while.end", !dbg !202
while.body:
  %".28" = load i8, i8* %"ch", !dbg !203
  %".29" = load i32, i32* %"row.addr", !dbg !203
  %".30" = call i8 @"get_char_row"(i8 %".28", i32 %".29"), !dbg !203
  %".31" = trunc i64 0 to i32 , !dbg !204
  store i32 %".31", i32* %"col.addr", !dbg !204
  call void @"llvm.dbg.declare"(metadata i32* %"col.addr", metadata !205, metadata !7), !dbg !206
  br label %"while.cond.1", !dbg !207
while.end:
  ret i32 0, !dbg !232
while.cond.1:
  %".35" = load i32, i32* %"col.addr", !dbg !207
  %".36" = sext i32 %".35" to i64 , !dbg !207
  %".37" = icmp slt i64 %".36", 5 , !dbg !207
  br i1 %".37", label %"while.body.1", label %"while.end.1", !dbg !207
while.body.1:
  %".39" = load i32, i32* %"col.addr", !dbg !208
  %".40" = sext i32 %".39" to i64 , !dbg !208
  %".41" = sub i64 4, %".40", !dbg !208
  %".42" = trunc i64 %".41" to i32 , !dbg !208
  %".43" = trunc i64 1 to i8 , !dbg !209
  store i8 %".43", i8* %"shifted.addr", !dbg !210
  call void @"llvm.dbg.declare"(metadata i8* %"shifted.addr", metadata !211, metadata !7), !dbg !212
  %".46" = trunc i64 0 to i32 , !dbg !213
  store i32 %".46", i32* %"i.addr", !dbg !213
  call void @"llvm.dbg.declare"(metadata i32* %"i.addr", metadata !214, metadata !7), !dbg !215
  br label %"while.cond.2", !dbg !216
while.end.1:
  %".124" = load i32, i32* %"row.addr", !dbg !232
  %".125" = sext i32 %".124" to i64 , !dbg !232
  %".126" = add i64 %".125", 1, !dbg !232
  %".127" = trunc i64 %".126" to i32 , !dbg !232
  store i32 %".127", i32* %"row.addr", !dbg !232
  br label %"while.cond", !dbg !232
while.cond.2:
  %".50" = load i32, i32* %"i.addr", !dbg !216
  %".51" = icmp slt i32 %".50", %".42" , !dbg !216
  br i1 %".51", label %"while.body.2", label %"while.end.2", !dbg !216
while.body.2:
  %".53" = load i8, i8* %"shifted.addr", !dbg !217
  %".54" = zext i8 %".53" to i64 , !dbg !217
  %".55" = mul i64 %".54", 2, !dbg !217
  %".56" = trunc i64 %".55" to i8 , !dbg !217
  store i8 %".56", i8* %"shifted.addr", !dbg !217
  %".58" = load i32, i32* %"i.addr", !dbg !218
  %".59" = sext i32 %".58" to i64 , !dbg !218
  %".60" = add i64 %".59", 1, !dbg !218
  %".61" = trunc i64 %".60" to i32 , !dbg !218
  store i32 %".61", i32* %"i.addr", !dbg !218
  br label %"while.cond.2", !dbg !218
while.end.2:
  %".64" = zext i8 %".30" to i32 , !dbg !219
  %".65" = load i8, i8* %"shifted.addr", !dbg !219
  %".66" = zext i8 %".65" to i32 , !dbg !219
  %".67" = udiv i32 %".64", %".66", !dbg !219
  %".68" = sext i32 %".67" to i64 , !dbg !219
  %".69" = srem i64 %".68", 2, !dbg !219
  %".70" = icmp eq i64 %".69", 1 , !dbg !219
  br i1 %".70", label %"if.then", label %"if.end", !dbg !219
if.then:
  %".72" = trunc i64 0 to i32 , !dbg !220
  store i32 %".72", i32* %"sy.addr", !dbg !220
  call void @"llvm.dbg.declare"(metadata i32* %"sy.addr", metadata !221, metadata !7), !dbg !222
  br label %"while.cond.3", !dbg !223
if.end:
  %".118" = load i32, i32* %"col.addr", !dbg !231
  %".119" = sext i32 %".118" to i64 , !dbg !231
  %".120" = add i64 %".119", 1, !dbg !231
  %".121" = trunc i64 %".120" to i32 , !dbg !231
  store i32 %".121", i32* %"col.addr", !dbg !231
  br label %"while.cond.1", !dbg !231
while.cond.3:
  %".76" = load i32, i32* %"sy.addr", !dbg !223
  %".77" = load i32, i32* %"scale", !dbg !223
  %".78" = icmp ult i32 %".76", %".77" , !dbg !223
  br i1 %".78", label %"while.body.3", label %"while.end.3", !dbg !223
while.body.3:
  %".80" = trunc i64 0 to i32 , !dbg !224
  store i32 %".80", i32* %"sx.addr", !dbg !224
  call void @"llvm.dbg.declare"(metadata i32* %"sx.addr", metadata !225, metadata !7), !dbg !226
  br label %"while.cond.4", !dbg !227
while.end.3:
  br label %"if.end", !dbg !230
while.cond.4:
  %".84" = load i32, i32* %"sx.addr", !dbg !227
  %".85" = load i32, i32* %"scale", !dbg !227
  %".86" = icmp ult i32 %".84", %".85" , !dbg !227
  br i1 %".86", label %"while.body.4", label %"while.end.4", !dbg !227
while.body.4:
  %".88" = load i8*, i8** %"buffer", !dbg !228
  %".89" = load i32, i32* %"x", !dbg !228
  %".90" = load i32, i32* %"col.addr", !dbg !228
  %".91" = load i32, i32* %"scale", !dbg !228
  %".92" = mul i32 %".90", %".91", !dbg !228
  %".93" = add i32 %".89", %".92", !dbg !228
  %".94" = load i32, i32* %"sx.addr", !dbg !228
  %".95" = add i32 %".93", %".94", !dbg !228
  %".96" = load i32, i32* %"y", !dbg !228
  %".97" = load i32, i32* %"row.addr", !dbg !228
  %".98" = load i32, i32* %"scale", !dbg !228
  %".99" = mul i32 %".97", %".98", !dbg !228
  %".100" = add i32 %".96", %".99", !dbg !228
  %".101" = load i32, i32* %"sy.addr", !dbg !228
  %".102" = add i32 %".100", %".101", !dbg !228
  %".103" = load i32, i32* %"color", !dbg !228
  %".104" = call i32 @"set_pixel"(i8* %".88", i32 %".95", i32 %".102", i32 %".103"), !dbg !228
  %".105" = load i32, i32* %"sx.addr", !dbg !229
  %".106" = zext i32 %".105" to i64 , !dbg !229
  %".107" = add i64 %".106", 1, !dbg !229
  %".108" = trunc i64 %".107" to i32 , !dbg !229
  store i32 %".108", i32* %"sx.addr", !dbg !229
  br label %"while.cond.4", !dbg !229
while.end.4:
  %".111" = load i32, i32* %"sy.addr", !dbg !230
  %".112" = zext i32 %".111" to i64 , !dbg !230
  %".113" = add i64 %".112", 1, !dbg !230
  %".114" = trunc i64 %".113" to i32 , !dbg !230
  store i32 %".114", i32* %"sy.addr", !dbg !230
  br label %"while.cond.3", !dbg !230
}

define i32 @"draw_string"(i8* %"buffer.arg", i8* %"text.arg", i64 %"text_len.arg", i32 %"x.arg", i32 %"y.arg", i32 %"color.arg", i32 %"scale.arg") !dbg !21
{
entry:
  %"buffer" = alloca i8*
  %"cursor_x.addr" = alloca i32, !dbg !241
  %"i.addr" = alloca i64, !dbg !244
  store i8* %"buffer.arg", i8** %"buffer"
  call void @"llvm.dbg.declare"(metadata i8** %"buffer", metadata !233, metadata !7), !dbg !234
  %"text" = alloca i8*
  store i8* %"text.arg", i8** %"text"
  call void @"llvm.dbg.declare"(metadata i8** %"text", metadata !235, metadata !7), !dbg !234
  %"text_len" = alloca i64
  store i64 %"text_len.arg", i64* %"text_len"
  call void @"llvm.dbg.declare"(metadata i64* %"text_len", metadata !236, metadata !7), !dbg !234
  %"x" = alloca i32
  store i32 %"x.arg", i32* %"x"
  call void @"llvm.dbg.declare"(metadata i32* %"x", metadata !237, metadata !7), !dbg !234
  %"y" = alloca i32
  store i32 %"y.arg", i32* %"y"
  call void @"llvm.dbg.declare"(metadata i32* %"y", metadata !238, metadata !7), !dbg !234
  %"color" = alloca i32
  store i32 %"color.arg", i32* %"color"
  call void @"llvm.dbg.declare"(metadata i32* %"color", metadata !239, metadata !7), !dbg !234
  %"scale" = alloca i32
  store i32 %"scale.arg", i32* %"scale"
  call void @"llvm.dbg.declare"(metadata i32* %"scale", metadata !240, metadata !7), !dbg !234
  %".23" = load i32, i32* %"x", !dbg !241
  store i32 %".23", i32* %"cursor_x.addr", !dbg !241
  call void @"llvm.dbg.declare"(metadata i32* %"cursor_x.addr", metadata !242, metadata !7), !dbg !243
  store i64 0, i64* %"i.addr", !dbg !244
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !245, metadata !7), !dbg !246
  br label %"while.cond", !dbg !247
while.cond:
  %".29" = load i64, i64* %"i.addr", !dbg !247
  %".30" = load i64, i64* %"text_len", !dbg !247
  %".31" = icmp slt i64 %".29", %".30" , !dbg !247
  br i1 %".31", label %"while.body", label %"while.end", !dbg !247
while.body:
  %".33" = load i8*, i8** %"text", !dbg !248
  %".34" = load i64, i64* %"i.addr", !dbg !248
  %".35" = getelementptr i8, i8* %".33", i64 %".34" , !dbg !248
  %".36" = load i8, i8* %".35", !dbg !248
  %".37" = load i8*, i8** %"buffer", !dbg !249
  %".38" = load i32, i32* %"cursor_x.addr", !dbg !249
  %".39" = load i32, i32* %"y", !dbg !249
  %".40" = load i32, i32* %"color", !dbg !249
  %".41" = load i32, i32* %"scale", !dbg !249
  %".42" = call i32 @"draw_char"(i8* %".37", i8 %".36", i32 %".38", i32 %".39", i32 %".40", i32 %".41"), !dbg !249
  %".43" = load i32, i32* %"cursor_x.addr", !dbg !250
  %".44" = load i32, i32* %"scale", !dbg !250
  %".45" = zext i32 %".44" to i64 , !dbg !250
  %".46" = mul i64 6, %".45", !dbg !250
  %".47" = zext i32 %".43" to i64 , !dbg !250
  %".48" = add i64 %".47", %".46", !dbg !250
  %".49" = trunc i64 %".48" to i32 , !dbg !250
  store i32 %".49", i32* %"cursor_x.addr", !dbg !250
  %".51" = load i64, i64* %"i.addr", !dbg !251
  %".52" = add i64 %".51", 1, !dbg !251
  store i64 %".52", i64* %"i.addr", !dbg !251
  br label %"while.cond", !dbg !251
while.end:
  ret i32 0, !dbg !251
}

define i32 @"write_ppm_header"(i32 %"fd.arg", i32 %"width.arg", i32 %"height.arg") !dbg !22
{
entry:
  %"fd" = alloca i32
  %"header.addr" = alloca [3 x i8], !dbg !256
  %"space.addr" = alloca i8, !dbg !267
  %"trailer.addr" = alloca [5 x i8], !dbg !272
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !252, metadata !7), !dbg !253
  %"width" = alloca i32
  store i32 %"width.arg", i32* %"width"
  call void @"llvm.dbg.declare"(metadata i32* %"width", metadata !254, metadata !7), !dbg !253
  %"height" = alloca i32
  store i32 %"height.arg", i32* %"height"
  call void @"llvm.dbg.declare"(metadata i32* %"height", metadata !255, metadata !7), !dbg !253
  call void @"llvm.dbg.declare"(metadata [3 x i8]* %"header.addr", metadata !260, metadata !7), !dbg !261
  %".12" = getelementptr [3 x i8], [3 x i8]* %"header.addr", i32 0, i64 0 , !dbg !262
  %".13" = trunc i64 80 to i8 , !dbg !262
  store i8 %".13", i8* %".12", !dbg !262
  %".15" = getelementptr [3 x i8], [3 x i8]* %"header.addr", i32 0, i64 1 , !dbg !263
  %".16" = trunc i64 54 to i8 , !dbg !263
  store i8 %".16", i8* %".15", !dbg !263
  %".18" = getelementptr [3 x i8], [3 x i8]* %"header.addr", i32 0, i64 2 , !dbg !264
  %".19" = trunc i64 10 to i8 , !dbg !264
  store i8 %".19", i8* %".18", !dbg !264
  %".21" = load i32, i32* %"fd", !dbg !265
  %".22" = getelementptr [3 x i8], [3 x i8]* %"header.addr", i32 0, i64 0 , !dbg !265
  %".23" = call i64 @"sys_write"(i32 %".21", i8* %".22", i64 3), !dbg !265
  %".24" = load i32, i32* %"fd", !dbg !266
  %".25" = load i32, i32* %"width", !dbg !266
  %".26" = call i32 @"write_number"(i32 %".24", i32 %".25"), !dbg !266
  %".27" = trunc i64 32 to i8 , !dbg !267
  store i8 %".27", i8* %"space.addr", !dbg !267
  call void @"llvm.dbg.declare"(metadata i8* %"space.addr", metadata !268, metadata !7), !dbg !269
  %".30" = load i32, i32* %"fd", !dbg !270
  %".31" = call i64 @"sys_write"(i32 %".30", i8* %"space.addr", i64 1), !dbg !270
  %".32" = load i32, i32* %"fd", !dbg !271
  %".33" = load i32, i32* %"height", !dbg !271
  %".34" = call i32 @"write_number"(i32 %".32", i32 %".33"), !dbg !271
  call void @"llvm.dbg.declare"(metadata [5 x i8]* %"trailer.addr", metadata !276, metadata !7), !dbg !277
  %".36" = getelementptr [5 x i8], [5 x i8]* %"trailer.addr", i32 0, i64 0 , !dbg !278
  %".37" = trunc i64 10 to i8 , !dbg !278
  store i8 %".37", i8* %".36", !dbg !278
  %".39" = getelementptr [5 x i8], [5 x i8]* %"trailer.addr", i32 0, i64 1 , !dbg !279
  %".40" = trunc i64 50 to i8 , !dbg !279
  store i8 %".40", i8* %".39", !dbg !279
  %".42" = getelementptr [5 x i8], [5 x i8]* %"trailer.addr", i32 0, i64 2 , !dbg !280
  %".43" = trunc i64 53 to i8 , !dbg !280
  store i8 %".43", i8* %".42", !dbg !280
  %".45" = getelementptr [5 x i8], [5 x i8]* %"trailer.addr", i32 0, i64 3 , !dbg !281
  %".46" = trunc i64 53 to i8 , !dbg !281
  store i8 %".46", i8* %".45", !dbg !281
  %".48" = getelementptr [5 x i8], [5 x i8]* %"trailer.addr", i32 0, i64 4 , !dbg !282
  %".49" = trunc i64 10 to i8 , !dbg !282
  store i8 %".49", i8* %".48", !dbg !282
  %".51" = load i32, i32* %"fd", !dbg !283
  %".52" = getelementptr [5 x i8], [5 x i8]* %"trailer.addr", i32 0, i64 0 , !dbg !283
  %".53" = call i64 @"sys_write"(i32 %".51", i8* %".52", i64 5), !dbg !283
  %".54" = trunc i64 %".53" to i32 , !dbg !283
  ret i32 %".54", !dbg !283
}

define i32 @"write_number"(i32 %"fd.arg", i32 %"n.arg") !dbg !23
{
entry:
  %"fd" = alloca i32
  %"zero.addr" = alloca i8, !dbg !288
  %"buf.addr" = alloca [10 x i8], !dbg !293
  %"temp.addr" = alloca i32, !dbg !299
  %"count.addr" = alloca i64, !dbg !302
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !284, metadata !7), !dbg !285
  %"n" = alloca i32
  store i32 %"n.arg", i32* %"n"
  call void @"llvm.dbg.declare"(metadata i32* %"n", metadata !286, metadata !7), !dbg !285
  %".8" = load i32, i32* %"n", !dbg !287
  %".9" = zext i32 %".8" to i64 , !dbg !287
  %".10" = icmp eq i64 %".9", 0 , !dbg !287
  br i1 %".10", label %"if.then", label %"if.end", !dbg !287
if.then:
  %".12" = trunc i64 48 to i8 , !dbg !288
  store i8 %".12", i8* %"zero.addr", !dbg !288
  call void @"llvm.dbg.declare"(metadata i8* %"zero.addr", metadata !289, metadata !7), !dbg !290
  %".15" = load i32, i32* %"fd", !dbg !291
  %".16" = call i64 @"sys_write"(i32 %".15", i8* %"zero.addr", i64 1), !dbg !291
  ret i32 0, !dbg !292
if.end:
  call void @"llvm.dbg.declare"(metadata [10 x i8]* %"buf.addr", metadata !297, metadata !7), !dbg !298
  %".19" = load i32, i32* %"n", !dbg !299
  store i32 %".19", i32* %"temp.addr", !dbg !299
  call void @"llvm.dbg.declare"(metadata i32* %"temp.addr", metadata !300, metadata !7), !dbg !301
  store i64 0, i64* %"count.addr", !dbg !302
  call void @"llvm.dbg.declare"(metadata i64* %"count.addr", metadata !303, metadata !7), !dbg !304
  br label %"while.cond", !dbg !305
while.cond:
  %".25" = load i32, i32* %"temp.addr", !dbg !305
  %".26" = zext i32 %".25" to i64 , !dbg !305
  %".27" = icmp ugt i64 %".26", 0 , !dbg !305
  br i1 %".27", label %"while.body", label %"while.end", !dbg !305
while.body:
  %".29" = load i32, i32* %"temp.addr", !dbg !306
  %".30" = zext i32 %".29" to i64 , !dbg !306
  %".31" = urem i64 %".30", 10, !dbg !306
  %".32" = add i64 48, %".31", !dbg !306
  %".33" = trunc i64 %".32" to i8 , !dbg !306
  %".34" = load i64, i64* %"count.addr", !dbg !306
  %".35" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 %".34" , !dbg !306
  store i8 %".33", i8* %".35", !dbg !306
  %".37" = load i32, i32* %"temp.addr", !dbg !307
  %".38" = zext i32 %".37" to i64 , !dbg !307
  %".39" = udiv i64 %".38", 10, !dbg !307
  %".40" = trunc i64 %".39" to i32 , !dbg !307
  store i32 %".40", i32* %"temp.addr", !dbg !307
  %".42" = load i64, i64* %"count.addr", !dbg !308
  %".43" = add i64 %".42", 1, !dbg !308
  store i64 %".43", i64* %"count.addr", !dbg !308
  br label %"while.cond", !dbg !308
while.end:
  br label %"while.cond.1", !dbg !309
while.cond.1:
  %".47" = load i64, i64* %"count.addr", !dbg !309
  %".48" = icmp sgt i64 %".47", 0 , !dbg !309
  br i1 %".48", label %"while.body.1", label %"while.end.1", !dbg !309
while.body.1:
  %".50" = load i64, i64* %"count.addr", !dbg !310
  %".51" = sub i64 %".50", 1, !dbg !310
  store i64 %".51", i64* %"count.addr", !dbg !310
  %".53" = load i32, i32* %"fd", !dbg !310
  %".54" = load i64, i64* %"count.addr", !dbg !310
  %".55" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 %".54" , !dbg !310
  %".56" = call i64 @"sys_write"(i32 %".53", i8* %".55", i64 1), !dbg !310
  br label %"while.cond.1", !dbg !310
while.end.1:
  ret i32 0, !dbg !310
}

define i32 @"main"() !dbg !24
{
entry:
  %"text.addr" = alloca [12 x i8], !dbg !315
  %"path.addr" = alloca [32 x i8], !dbg !334
  %".2" = trunc i64 3 to i32 , !dbg !311
  %".3" = trunc i64 34 to i32 , !dbg !311
  %".4" = sub i64 0, 1, !dbg !311
  %".5" = trunc i64 %".4" to i32 , !dbg !311
  %".6" = call i8* @"sys_mmap"(i64 0, i64 30000, i32 %".2", i32 %".3", i32 %".5", i64 0), !dbg !311
  %".7" = ptrtoint i8* %".6" to i64 , !dbg !312
  %".8" = icmp slt i64 %".7", 0 , !dbg !312
  br i1 %".8", label %"if.then", label %"if.end", !dbg !312
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !313
  ret i32 %".10", !dbg !313
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !314
  %".13" = trunc i64 0 to i32 , !dbg !314
  %".14" = call i32 @"fill_rect"(i8* %".6", i32 %".12", i32 %".13", i32 200, i32 50, i32 4281150765), !dbg !314
  call void @"llvm.dbg.declare"(metadata [12 x i8]* %"text.addr", metadata !319, metadata !7), !dbg !320
  %".16" = getelementptr [12 x i8], [12 x i8]* %"text.addr", i32 0, i64 0 , !dbg !321
  %".17" = trunc i64 72 to i8 , !dbg !321
  store i8 %".17", i8* %".16", !dbg !321
  %".19" = getelementptr [12 x i8], [12 x i8]* %"text.addr", i32 0, i64 1 , !dbg !322
  %".20" = trunc i64 101 to i8 , !dbg !322
  store i8 %".20", i8* %".19", !dbg !322
  %".22" = getelementptr [12 x i8], [12 x i8]* %"text.addr", i32 0, i64 2 , !dbg !323
  %".23" = trunc i64 108 to i8 , !dbg !323
  store i8 %".23", i8* %".22", !dbg !323
  %".25" = getelementptr [12 x i8], [12 x i8]* %"text.addr", i32 0, i64 3 , !dbg !324
  %".26" = trunc i64 108 to i8 , !dbg !324
  store i8 %".26", i8* %".25", !dbg !324
  %".28" = getelementptr [12 x i8], [12 x i8]* %"text.addr", i32 0, i64 4 , !dbg !325
  %".29" = trunc i64 111 to i8 , !dbg !325
  store i8 %".29", i8* %".28", !dbg !325
  %".31" = getelementptr [12 x i8], [12 x i8]* %"text.addr", i32 0, i64 5 , !dbg !326
  %".32" = trunc i64 32 to i8 , !dbg !326
  store i8 %".32", i8* %".31", !dbg !326
  %".34" = getelementptr [12 x i8], [12 x i8]* %"text.addr", i32 0, i64 6 , !dbg !327
  %".35" = trunc i64 87 to i8 , !dbg !327
  store i8 %".35", i8* %".34", !dbg !327
  %".37" = getelementptr [12 x i8], [12 x i8]* %"text.addr", i32 0, i64 7 , !dbg !328
  %".38" = trunc i64 111 to i8 , !dbg !328
  store i8 %".38", i8* %".37", !dbg !328
  %".40" = getelementptr [12 x i8], [12 x i8]* %"text.addr", i32 0, i64 8 , !dbg !329
  %".41" = trunc i64 114 to i8 , !dbg !329
  store i8 %".41", i8* %".40", !dbg !329
  %".43" = getelementptr [12 x i8], [12 x i8]* %"text.addr", i32 0, i64 9 , !dbg !330
  %".44" = trunc i64 108 to i8 , !dbg !330
  store i8 %".44", i8* %".43", !dbg !330
  %".46" = getelementptr [12 x i8], [12 x i8]* %"text.addr", i32 0, i64 10 , !dbg !331
  %".47" = trunc i64 100 to i8 , !dbg !331
  store i8 %".47", i8* %".46", !dbg !331
  %".49" = getelementptr [12 x i8], [12 x i8]* %"text.addr", i32 0, i64 11 , !dbg !332
  %".50" = trunc i64 33 to i8 , !dbg !332
  store i8 %".50", i8* %".49", !dbg !332
  %".52" = getelementptr [12 x i8], [12 x i8]* %"text.addr", i32 0, i64 0 , !dbg !333
  %".53" = trunc i64 10 to i32 , !dbg !333
  %".54" = trunc i64 18 to i32 , !dbg !333
  %".55" = trunc i64 2 to i32 , !dbg !333
  %".56" = call i32 @"draw_string"(i8* %".6", i8* %".52", i64 12, i32 %".53", i32 %".54", i32 4294967295, i32 %".55"), !dbg !333
  call void @"llvm.dbg.declare"(metadata [32 x i8]* %"path.addr", metadata !338, metadata !7), !dbg !339
  %".58" = getelementptr [32 x i8], [32 x i8]* %"path.addr", i32 0, i64 0 , !dbg !340
  %".59" = trunc i64 104 to i8 , !dbg !340
  store i8 %".59", i8* %".58", !dbg !340
  %".61" = getelementptr [32 x i8], [32 x i8]* %"path.addr", i32 0, i64 1 , !dbg !341
  %".62" = trunc i64 101 to i8 , !dbg !341
  store i8 %".62", i8* %".61", !dbg !341
  %".64" = getelementptr [32 x i8], [32 x i8]* %"path.addr", i32 0, i64 2 , !dbg !342
  %".65" = trunc i64 108 to i8 , !dbg !342
  store i8 %".65", i8* %".64", !dbg !342
  %".67" = getelementptr [32 x i8], [32 x i8]* %"path.addr", i32 0, i64 3 , !dbg !343
  %".68" = trunc i64 108 to i8 , !dbg !343
  store i8 %".68", i8* %".67", !dbg !343
  %".70" = getelementptr [32 x i8], [32 x i8]* %"path.addr", i32 0, i64 4 , !dbg !344
  %".71" = trunc i64 111 to i8 , !dbg !344
  store i8 %".71", i8* %".70", !dbg !344
  %".73" = getelementptr [32 x i8], [32 x i8]* %"path.addr", i32 0, i64 5 , !dbg !345
  %".74" = trunc i64 46 to i8 , !dbg !345
  store i8 %".74", i8* %".73", !dbg !345
  %".76" = getelementptr [32 x i8], [32 x i8]* %"path.addr", i32 0, i64 6 , !dbg !346
  %".77" = trunc i64 112 to i8 , !dbg !346
  store i8 %".77", i8* %".76", !dbg !346
  %".79" = getelementptr [32 x i8], [32 x i8]* %"path.addr", i32 0, i64 7 , !dbg !347
  %".80" = trunc i64 112 to i8 , !dbg !347
  store i8 %".80", i8* %".79", !dbg !347
  %".82" = getelementptr [32 x i8], [32 x i8]* %"path.addr", i32 0, i64 8 , !dbg !348
  %".83" = trunc i64 109 to i8 , !dbg !348
  store i8 %".83", i8* %".82", !dbg !348
  %".85" = getelementptr [32 x i8], [32 x i8]* %"path.addr", i32 0, i64 9 , !dbg !349
  %".86" = trunc i64 0 to i8 , !dbg !349
  store i8 %".86", i8* %".85", !dbg !349
  %".88" = getelementptr [32 x i8], [32 x i8]* %"path.addr", i32 0, i64 0 , !dbg !350
  %".89" = trunc i64 577 to i32 , !dbg !350
  %".90" = trunc i64 420 to i32 , !dbg !350
  %".91" = call i32 @"sys_open3"(i8* %".88", i32 %".89", i32 %".90"), !dbg !350
  %".92" = sext i32 %".91" to i64 , !dbg !351
  %".93" = icmp slt i64 %".92", 0 , !dbg !351
  br i1 %".93", label %"if.then.1", label %"if.end.1", !dbg !351
if.then.1:
  %".95" = call i32 @"sys_munmap"(i8* %".6", i64 30000), !dbg !352
  %".96" = trunc i64 2 to i32 , !dbg !353
  ret i32 %".96", !dbg !353
if.end.1:
  %".98" = call i32 @"write_ppm_header"(i32 %".91", i32 200, i32 50), !dbg !354
  %".99" = call i64 @"sys_write"(i32 %".91", i8* %".6", i64 30000), !dbg !355
  %".100" = call i32 @"sys_close"(i32 %".91"), !dbg !356
  %".101" = call i32 @"sys_munmap"(i8* %".6", i64 30000), !dbg !357
  %".102" = trunc i64 0 to i32 , !dbg !358
  ret i32 %".102", !dbg !358
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/prism/tools", filename: "render_test.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 29, name: "get_char_row", scopeLine: 29, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 188, name: "set_pixel", scopeLine: 188, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 202, name: "fill_rect", scopeLine: 202, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 211, name: "draw_char", scopeLine: 211, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 238, name: "draw_string", scopeLine: 238, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 251, name: "write_ppm_header", scopeLine: 251, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 278, name: "write_number", scopeLine: 278, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 303, name: "main", scopeLine: 303, type: !4, unit: !1)
!25 = !DILocalVariable(file: !0, line: 29, name: "ch", scope: !17, type: !12)
!26 = !DILocation(column: 1, line: 29, scope: !17)
!27 = !DILocalVariable(file: !0, line: 29, name: "row", scope: !17, type: !10)
!28 = !DILocation(column: 5, line: 34, scope: !17)
!29 = !DILocation(column: 9, line: 35, scope: !17)
!30 = !DILocation(column: 13, line: 36, scope: !17)
!31 = !DILocation(column: 9, line: 37, scope: !17)
!32 = !DILocation(column: 13, line: 38, scope: !17)
!33 = !DILocation(column: 9, line: 39, scope: !17)
!34 = !DILocation(column: 13, line: 40, scope: !17)
!35 = !DILocation(column: 9, line: 41, scope: !17)
!36 = !DILocation(column: 13, line: 42, scope: !17)
!37 = !DILocation(column: 9, line: 43, scope: !17)
!38 = !DILocation(column: 13, line: 44, scope: !17)
!39 = !DILocation(column: 9, line: 45, scope: !17)
!40 = !DILocation(column: 13, line: 46, scope: !17)
!41 = !DILocation(column: 9, line: 47, scope: !17)
!42 = !DILocation(column: 13, line: 48, scope: !17)
!43 = !DILocation(column: 9, line: 49, scope: !17)
!44 = !DILocation(column: 5, line: 52, scope: !17)
!45 = !DILocation(column: 9, line: 53, scope: !17)
!46 = !DILocation(column: 13, line: 54, scope: !17)
!47 = !DILocation(column: 9, line: 55, scope: !17)
!48 = !DILocation(column: 13, line: 56, scope: !17)
!49 = !DILocation(column: 9, line: 57, scope: !17)
!50 = !DILocation(column: 13, line: 58, scope: !17)
!51 = !DILocation(column: 9, line: 59, scope: !17)
!52 = !DILocation(column: 13, line: 60, scope: !17)
!53 = !DILocation(column: 9, line: 61, scope: !17)
!54 = !DILocation(column: 13, line: 62, scope: !17)
!55 = !DILocation(column: 9, line: 63, scope: !17)
!56 = !DILocation(column: 13, line: 64, scope: !17)
!57 = !DILocation(column: 9, line: 65, scope: !17)
!58 = !DILocation(column: 13, line: 66, scope: !17)
!59 = !DILocation(column: 9, line: 67, scope: !17)
!60 = !DILocation(column: 5, line: 70, scope: !17)
!61 = !DILocation(column: 9, line: 71, scope: !17)
!62 = !DILocation(column: 13, line: 72, scope: !17)
!63 = !DILocation(column: 9, line: 73, scope: !17)
!64 = !DILocation(column: 13, line: 74, scope: !17)
!65 = !DILocation(column: 9, line: 75, scope: !17)
!66 = !DILocation(column: 13, line: 76, scope: !17)
!67 = !DILocation(column: 9, line: 77, scope: !17)
!68 = !DILocation(column: 13, line: 78, scope: !17)
!69 = !DILocation(column: 9, line: 79, scope: !17)
!70 = !DILocation(column: 13, line: 80, scope: !17)
!71 = !DILocation(column: 9, line: 81, scope: !17)
!72 = !DILocation(column: 13, line: 82, scope: !17)
!73 = !DILocation(column: 9, line: 83, scope: !17)
!74 = !DILocation(column: 13, line: 84, scope: !17)
!75 = !DILocation(column: 9, line: 85, scope: !17)
!76 = !DILocation(column: 5, line: 88, scope: !17)
!77 = !DILocation(column: 9, line: 89, scope: !17)
!78 = !DILocation(column: 13, line: 90, scope: !17)
!79 = !DILocation(column: 9, line: 91, scope: !17)
!80 = !DILocation(column: 13, line: 92, scope: !17)
!81 = !DILocation(column: 9, line: 93, scope: !17)
!82 = !DILocation(column: 13, line: 94, scope: !17)
!83 = !DILocation(column: 9, line: 95, scope: !17)
!84 = !DILocation(column: 13, line: 96, scope: !17)
!85 = !DILocation(column: 9, line: 97, scope: !17)
!86 = !DILocation(column: 13, line: 98, scope: !17)
!87 = !DILocation(column: 9, line: 99, scope: !17)
!88 = !DILocation(column: 13, line: 100, scope: !17)
!89 = !DILocation(column: 9, line: 101, scope: !17)
!90 = !DILocation(column: 13, line: 102, scope: !17)
!91 = !DILocation(column: 9, line: 103, scope: !17)
!92 = !DILocation(column: 5, line: 106, scope: !17)
!93 = !DILocation(column: 9, line: 107, scope: !17)
!94 = !DILocation(column: 5, line: 110, scope: !17)
!95 = !DILocation(column: 9, line: 111, scope: !17)
!96 = !DILocation(column: 13, line: 112, scope: !17)
!97 = !DILocation(column: 9, line: 113, scope: !17)
!98 = !DILocation(column: 13, line: 114, scope: !17)
!99 = !DILocation(column: 9, line: 115, scope: !17)
!100 = !DILocation(column: 13, line: 116, scope: !17)
!101 = !DILocation(column: 9, line: 117, scope: !17)
!102 = !DILocation(column: 13, line: 118, scope: !17)
!103 = !DILocation(column: 9, line: 119, scope: !17)
!104 = !DILocation(column: 13, line: 120, scope: !17)
!105 = !DILocation(column: 9, line: 121, scope: !17)
!106 = !DILocation(column: 13, line: 122, scope: !17)
!107 = !DILocation(column: 9, line: 123, scope: !17)
!108 = !DILocation(column: 13, line: 124, scope: !17)
!109 = !DILocation(column: 9, line: 125, scope: !17)
!110 = !DILocation(column: 5, line: 128, scope: !17)
!111 = !DILocation(column: 9, line: 129, scope: !17)
!112 = !DILocation(column: 13, line: 130, scope: !17)
!113 = !DILocation(column: 9, line: 131, scope: !17)
!114 = !DILocation(column: 13, line: 132, scope: !17)
!115 = !DILocation(column: 9, line: 133, scope: !17)
!116 = !DILocation(column: 13, line: 134, scope: !17)
!117 = !DILocation(column: 9, line: 135, scope: !17)
!118 = !DILocation(column: 13, line: 136, scope: !17)
!119 = !DILocation(column: 9, line: 137, scope: !17)
!120 = !DILocation(column: 13, line: 138, scope: !17)
!121 = !DILocation(column: 9, line: 139, scope: !17)
!122 = !DILocation(column: 13, line: 140, scope: !17)
!123 = !DILocation(column: 9, line: 141, scope: !17)
!124 = !DILocation(column: 13, line: 142, scope: !17)
!125 = !DILocation(column: 9, line: 143, scope: !17)
!126 = !DILocation(column: 5, line: 146, scope: !17)
!127 = !DILocation(column: 9, line: 147, scope: !17)
!128 = !DILocation(column: 13, line: 148, scope: !17)
!129 = !DILocation(column: 9, line: 149, scope: !17)
!130 = !DILocation(column: 13, line: 150, scope: !17)
!131 = !DILocation(column: 9, line: 151, scope: !17)
!132 = !DILocation(column: 13, line: 152, scope: !17)
!133 = !DILocation(column: 9, line: 153, scope: !17)
!134 = !DILocation(column: 13, line: 154, scope: !17)
!135 = !DILocation(column: 9, line: 155, scope: !17)
!136 = !DILocation(column: 13, line: 156, scope: !17)
!137 = !DILocation(column: 9, line: 157, scope: !17)
!138 = !DILocation(column: 13, line: 158, scope: !17)
!139 = !DILocation(column: 9, line: 159, scope: !17)
!140 = !DILocation(column: 13, line: 160, scope: !17)
!141 = !DILocation(column: 9, line: 161, scope: !17)
!142 = !DILocation(column: 5, line: 164, scope: !17)
!143 = !DILocation(column: 9, line: 165, scope: !17)
!144 = !DILocation(column: 13, line: 166, scope: !17)
!145 = !DILocation(column: 9, line: 167, scope: !17)
!146 = !DILocation(column: 13, line: 168, scope: !17)
!147 = !DILocation(column: 9, line: 169, scope: !17)
!148 = !DILocation(column: 13, line: 170, scope: !17)
!149 = !DILocation(column: 9, line: 171, scope: !17)
!150 = !DILocation(column: 13, line: 172, scope: !17)
!151 = !DILocation(column: 9, line: 173, scope: !17)
!152 = !DILocation(column: 13, line: 174, scope: !17)
!153 = !DILocation(column: 9, line: 175, scope: !17)
!154 = !DILocation(column: 13, line: 176, scope: !17)
!155 = !DILocation(column: 9, line: 177, scope: !17)
!156 = !DILocation(column: 13, line: 178, scope: !17)
!157 = !DILocation(column: 9, line: 179, scope: !17)
!158 = !DILocation(column: 5, line: 182, scope: !17)
!159 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!160 = !DILocalVariable(file: !0, line: 188, name: "buffer", scope: !18, type: !159)
!161 = !DILocation(column: 1, line: 188, scope: !18)
!162 = !DILocalVariable(file: !0, line: 188, name: "x", scope: !18, type: !14)
!163 = !DILocalVariable(file: !0, line: 188, name: "y", scope: !18, type: !14)
!164 = !DILocalVariable(file: !0, line: 188, name: "color", scope: !18, type: !14)
!165 = !DILocation(column: 5, line: 189, scope: !18)
!166 = !DILocation(column: 9, line: 190, scope: !18)
!167 = !DILocation(column: 5, line: 192, scope: !18)
!168 = !DILocation(column: 5, line: 193, scope: !18)
!169 = !DILocation(column: 5, line: 194, scope: !18)
!170 = !DILocation(column: 5, line: 195, scope: !18)
!171 = !DILocation(column: 5, line: 198, scope: !18)
!172 = !DILocation(column: 5, line: 199, scope: !18)
!173 = !DILocation(column: 5, line: 200, scope: !18)
!174 = !DILocalVariable(file: !0, line: 202, name: "buffer", scope: !19, type: !159)
!175 = !DILocation(column: 1, line: 202, scope: !19)
!176 = !DILocalVariable(file: !0, line: 202, name: "x", scope: !19, type: !14)
!177 = !DILocalVariable(file: !0, line: 202, name: "y", scope: !19, type: !14)
!178 = !DILocalVariable(file: !0, line: 202, name: "w", scope: !19, type: !14)
!179 = !DILocalVariable(file: !0, line: 202, name: "h", scope: !19, type: !14)
!180 = !DILocalVariable(file: !0, line: 202, name: "color", scope: !19, type: !14)
!181 = !DILocation(column: 5, line: 203, scope: !19)
!182 = !DILocalVariable(file: !0, line: 203, name: "py", scope: !19, type: !14)
!183 = !DILocation(column: 1, line: 203, scope: !19)
!184 = !DILocation(column: 5, line: 204, scope: !19)
!185 = !DILocation(column: 9, line: 205, scope: !19)
!186 = !DILocalVariable(file: !0, line: 205, name: "px", scope: !19, type: !14)
!187 = !DILocation(column: 1, line: 205, scope: !19)
!188 = !DILocation(column: 9, line: 206, scope: !19)
!189 = !DILocation(column: 13, line: 207, scope: !19)
!190 = !DILocation(column: 13, line: 208, scope: !19)
!191 = !DILocation(column: 9, line: 209, scope: !19)
!192 = !DILocalVariable(file: !0, line: 211, name: "buffer", scope: !20, type: !159)
!193 = !DILocation(column: 1, line: 211, scope: !20)
!194 = !DILocalVariable(file: !0, line: 211, name: "ch", scope: !20, type: !12)
!195 = !DILocalVariable(file: !0, line: 211, name: "x", scope: !20, type: !14)
!196 = !DILocalVariable(file: !0, line: 211, name: "y", scope: !20, type: !14)
!197 = !DILocalVariable(file: !0, line: 211, name: "color", scope: !20, type: !14)
!198 = !DILocalVariable(file: !0, line: 211, name: "scale", scope: !20, type: !14)
!199 = !DILocation(column: 5, line: 212, scope: !20)
!200 = !DILocalVariable(file: !0, line: 212, name: "row", scope: !20, type: !10)
!201 = !DILocation(column: 1, line: 212, scope: !20)
!202 = !DILocation(column: 5, line: 213, scope: !20)
!203 = !DILocation(column: 9, line: 214, scope: !20)
!204 = !DILocation(column: 9, line: 215, scope: !20)
!205 = !DILocalVariable(file: !0, line: 215, name: "col", scope: !20, type: !10)
!206 = !DILocation(column: 1, line: 215, scope: !20)
!207 = !DILocation(column: 9, line: 216, scope: !20)
!208 = !DILocation(column: 13, line: 218, scope: !20)
!209 = !DILocation(column: 13, line: 219, scope: !20)
!210 = !DILocation(column: 13, line: 220, scope: !20)
!211 = !DILocalVariable(file: !0, line: 220, name: "shifted", scope: !20, type: !12)
!212 = !DILocation(column: 1, line: 220, scope: !20)
!213 = !DILocation(column: 13, line: 221, scope: !20)
!214 = !DILocalVariable(file: !0, line: 221, name: "i", scope: !20, type: !10)
!215 = !DILocation(column: 1, line: 221, scope: !20)
!216 = !DILocation(column: 13, line: 222, scope: !20)
!217 = !DILocation(column: 17, line: 223, scope: !20)
!218 = !DILocation(column: 17, line: 224, scope: !20)
!219 = !DILocation(column: 13, line: 226, scope: !20)
!220 = !DILocation(column: 17, line: 228, scope: !20)
!221 = !DILocalVariable(file: !0, line: 228, name: "sy", scope: !20, type: !14)
!222 = !DILocation(column: 1, line: 228, scope: !20)
!223 = !DILocation(column: 17, line: 229, scope: !20)
!224 = !DILocation(column: 21, line: 230, scope: !20)
!225 = !DILocalVariable(file: !0, line: 230, name: "sx", scope: !20, type: !14)
!226 = !DILocation(column: 1, line: 230, scope: !20)
!227 = !DILocation(column: 21, line: 231, scope: !20)
!228 = !DILocation(column: 25, line: 232, scope: !20)
!229 = !DILocation(column: 25, line: 233, scope: !20)
!230 = !DILocation(column: 21, line: 234, scope: !20)
!231 = !DILocation(column: 13, line: 235, scope: !20)
!232 = !DILocation(column: 9, line: 236, scope: !20)
!233 = !DILocalVariable(file: !0, line: 238, name: "buffer", scope: !21, type: !159)
!234 = !DILocation(column: 1, line: 238, scope: !21)
!235 = !DILocalVariable(file: !0, line: 238, name: "text", scope: !21, type: !159)
!236 = !DILocalVariable(file: !0, line: 238, name: "text_len", scope: !21, type: !11)
!237 = !DILocalVariable(file: !0, line: 238, name: "x", scope: !21, type: !14)
!238 = !DILocalVariable(file: !0, line: 238, name: "y", scope: !21, type: !14)
!239 = !DILocalVariable(file: !0, line: 238, name: "color", scope: !21, type: !14)
!240 = !DILocalVariable(file: !0, line: 238, name: "scale", scope: !21, type: !14)
!241 = !DILocation(column: 5, line: 239, scope: !21)
!242 = !DILocalVariable(file: !0, line: 239, name: "cursor_x", scope: !21, type: !14)
!243 = !DILocation(column: 1, line: 239, scope: !21)
!244 = !DILocation(column: 5, line: 240, scope: !21)
!245 = !DILocalVariable(file: !0, line: 240, name: "i", scope: !21, type: !11)
!246 = !DILocation(column: 1, line: 240, scope: !21)
!247 = !DILocation(column: 5, line: 241, scope: !21)
!248 = !DILocation(column: 9, line: 242, scope: !21)
!249 = !DILocation(column: 9, line: 243, scope: !21)
!250 = !DILocation(column: 9, line: 244, scope: !21)
!251 = !DILocation(column: 9, line: 245, scope: !21)
!252 = !DILocalVariable(file: !0, line: 251, name: "fd", scope: !22, type: !10)
!253 = !DILocation(column: 1, line: 251, scope: !22)
!254 = !DILocalVariable(file: !0, line: 251, name: "width", scope: !22, type: !14)
!255 = !DILocalVariable(file: !0, line: 251, name: "height", scope: !22, type: !14)
!256 = !DILocation(column: 5, line: 253, scope: !22)
!257 = !DISubrange(count: 3)
!258 = !{ !257 }
!259 = !DICompositeType(baseType: !12, elements: !258, size: 24, tag: DW_TAG_array_type)
!260 = !DILocalVariable(file: !0, line: 253, name: "header", scope: !22, type: !259)
!261 = !DILocation(column: 1, line: 253, scope: !22)
!262 = !DILocation(column: 5, line: 254, scope: !22)
!263 = !DILocation(column: 5, line: 255, scope: !22)
!264 = !DILocation(column: 5, line: 256, scope: !22)
!265 = !DILocation(column: 5, line: 257, scope: !22)
!266 = !DILocation(column: 5, line: 260, scope: !22)
!267 = !DILocation(column: 5, line: 263, scope: !22)
!268 = !DILocalVariable(file: !0, line: 263, name: "space", scope: !22, type: !12)
!269 = !DILocation(column: 1, line: 263, scope: !22)
!270 = !DILocation(column: 5, line: 264, scope: !22)
!271 = !DILocation(column: 5, line: 267, scope: !22)
!272 = !DILocation(column: 5, line: 270, scope: !22)
!273 = !DISubrange(count: 5)
!274 = !{ !273 }
!275 = !DICompositeType(baseType: !12, elements: !274, size: 40, tag: DW_TAG_array_type)
!276 = !DILocalVariable(file: !0, line: 270, name: "trailer", scope: !22, type: !275)
!277 = !DILocation(column: 1, line: 270, scope: !22)
!278 = !DILocation(column: 5, line: 271, scope: !22)
!279 = !DILocation(column: 5, line: 272, scope: !22)
!280 = !DILocation(column: 5, line: 273, scope: !22)
!281 = !DILocation(column: 5, line: 274, scope: !22)
!282 = !DILocation(column: 5, line: 275, scope: !22)
!283 = !DILocation(column: 5, line: 276, scope: !22)
!284 = !DILocalVariable(file: !0, line: 278, name: "fd", scope: !23, type: !10)
!285 = !DILocation(column: 1, line: 278, scope: !23)
!286 = !DILocalVariable(file: !0, line: 278, name: "n", scope: !23, type: !14)
!287 = !DILocation(column: 5, line: 279, scope: !23)
!288 = !DILocation(column: 9, line: 280, scope: !23)
!289 = !DILocalVariable(file: !0, line: 280, name: "zero", scope: !23, type: !12)
!290 = !DILocation(column: 1, line: 280, scope: !23)
!291 = !DILocation(column: 9, line: 281, scope: !23)
!292 = !DILocation(column: 9, line: 282, scope: !23)
!293 = !DILocation(column: 5, line: 285, scope: !23)
!294 = !DISubrange(count: 10)
!295 = !{ !294 }
!296 = !DICompositeType(baseType: !12, elements: !295, size: 80, tag: DW_TAG_array_type)
!297 = !DILocalVariable(file: !0, line: 285, name: "buf", scope: !23, type: !296)
!298 = !DILocation(column: 1, line: 285, scope: !23)
!299 = !DILocation(column: 5, line: 286, scope: !23)
!300 = !DILocalVariable(file: !0, line: 286, name: "temp", scope: !23, type: !14)
!301 = !DILocation(column: 1, line: 286, scope: !23)
!302 = !DILocation(column: 5, line: 287, scope: !23)
!303 = !DILocalVariable(file: !0, line: 287, name: "count", scope: !23, type: !11)
!304 = !DILocation(column: 1, line: 287, scope: !23)
!305 = !DILocation(column: 5, line: 289, scope: !23)
!306 = !DILocation(column: 9, line: 290, scope: !23)
!307 = !DILocation(column: 9, line: 291, scope: !23)
!308 = !DILocation(column: 9, line: 292, scope: !23)
!309 = !DILocation(column: 5, line: 295, scope: !23)
!310 = !DILocation(column: 9, line: 296, scope: !23)
!311 = !DILocation(column: 5, line: 305, scope: !24)
!312 = !DILocation(column: 5, line: 306, scope: !24)
!313 = !DILocation(column: 9, line: 307, scope: !24)
!314 = !DILocation(column: 5, line: 310, scope: !24)
!315 = !DILocation(column: 5, line: 317, scope: !24)
!316 = !DISubrange(count: 12)
!317 = !{ !316 }
!318 = !DICompositeType(baseType: !12, elements: !317, size: 96, tag: DW_TAG_array_type)
!319 = !DILocalVariable(file: !0, line: 317, name: "text", scope: !24, type: !318)
!320 = !DILocation(column: 1, line: 317, scope: !24)
!321 = !DILocation(column: 5, line: 318, scope: !24)
!322 = !DILocation(column: 5, line: 319, scope: !24)
!323 = !DILocation(column: 5, line: 320, scope: !24)
!324 = !DILocation(column: 5, line: 321, scope: !24)
!325 = !DILocation(column: 5, line: 322, scope: !24)
!326 = !DILocation(column: 5, line: 323, scope: !24)
!327 = !DILocation(column: 5, line: 324, scope: !24)
!328 = !DILocation(column: 5, line: 325, scope: !24)
!329 = !DILocation(column: 5, line: 326, scope: !24)
!330 = !DILocation(column: 5, line: 327, scope: !24)
!331 = !DILocation(column: 5, line: 328, scope: !24)
!332 = !DILocation(column: 5, line: 329, scope: !24)
!333 = !DILocation(column: 5, line: 331, scope: !24)
!334 = !DILocation(column: 5, line: 335, scope: !24)
!335 = !DISubrange(count: 32)
!336 = !{ !335 }
!337 = !DICompositeType(baseType: !12, elements: !336, size: 256, tag: DW_TAG_array_type)
!338 = !DILocalVariable(file: !0, line: 335, name: "path", scope: !24, type: !337)
!339 = !DILocation(column: 1, line: 335, scope: !24)
!340 = !DILocation(column: 5, line: 336, scope: !24)
!341 = !DILocation(column: 5, line: 337, scope: !24)
!342 = !DILocation(column: 5, line: 338, scope: !24)
!343 = !DILocation(column: 5, line: 339, scope: !24)
!344 = !DILocation(column: 5, line: 340, scope: !24)
!345 = !DILocation(column: 5, line: 341, scope: !24)
!346 = !DILocation(column: 5, line: 342, scope: !24)
!347 = !DILocation(column: 5, line: 343, scope: !24)
!348 = !DILocation(column: 5, line: 344, scope: !24)
!349 = !DILocation(column: 5, line: 345, scope: !24)
!350 = !DILocation(column: 5, line: 347, scope: !24)
!351 = !DILocation(column: 5, line: 348, scope: !24)
!352 = !DILocation(column: 9, line: 349, scope: !24)
!353 = !DILocation(column: 9, line: 350, scope: !24)
!354 = !DILocation(column: 5, line: 353, scope: !24)
!355 = !DILocation(column: 5, line: 356, scope: !24)
!356 = !DILocation(column: 5, line: 359, scope: !24)
!357 = !DILocation(column: 5, line: 360, scope: !24)
!358 = !DILocation(column: 5, line: 362, scope: !24)