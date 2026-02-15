; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Stat" = type {i64, i64, i64, i32, i32, i32, i32, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64}
%"struct.ritz_module_1.Dirent64" = type {i64, i64, i16, i8}
%"struct.ritz_module_1.Timeval" = type {i64, i64}
%"struct.ritz_module_1.Rect" = type {i32, i32, i32, i32}
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

declare i32 @"min_i32"(i32 %".1", i32 %".2")

declare i32 @"max_i32"(i32 %".1", i32 %".2")

declare %"struct.ritz_module_1.DamageRegion" @"damage_region_new"()

declare i32 @"damage_region_add"(%"struct.ritz_module_1.DamageRegion"* %".1", %"struct.ritz_module_1.Rect" %".2")

declare i32 @"damage_region_clear"(%"struct.ritz_module_1.DamageRegion"* %".1")

declare i1 @"damage_region_is_empty"(%"struct.ritz_module_1.DamageRegion"* %".1")

declare i32 @"damage_region_count"(%"struct.ritz_module_1.DamageRegion"* %".1")

declare %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".1", i32 %".2", i32 %".3", i32 %".4")

declare %"struct.ritz_module_1.Rect" @"rect_zero"()

declare i1 @"rects_intersect"(%"struct.ritz_module_1.Rect"* %".1", %"struct.ritz_module_1.Rect"* %".2")

declare %"struct.ritz_module_1.Rect" @"rect_union"(%"struct.ritz_module_1.Rect"* %".1", %"struct.ritz_module_1.Rect"* %".2")

declare %"struct.ritz_module_1.Rect" @"rect_intersection"(%"struct.ritz_module_1.Rect"* %".1", %"struct.ritz_module_1.Rect"* %".2")

declare i1 @"rect_contains_point"(%"struct.ritz_module_1.Rect"* %".1", i32 %".2", i32 %".3")

declare i32 @"rect_area"(%"struct.ritz_module_1.Rect"* %".1")

declare i1 @"rect_is_empty"(%"struct.ritz_module_1.Rect"* %".1")

declare %"struct.ritz_module_1.Rect" @"damage_region_bounds"(%"struct.ritz_module_1.DamageRegion"* %".1")

define i32 @"test_rect_new"() !dbg !17
{
entry:
  %".2" = trunc i64 10 to i32 , !dbg !39
  %".3" = trunc i64 20 to i32 , !dbg !39
  %".4" = trunc i64 100 to i32 , !dbg !39
  %".5" = trunc i64 50 to i32 , !dbg !39
  %".6" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".2", i32 %".3", i32 %".4", i32 %".5"), !dbg !39
  %".7" = extractvalue %"struct.ritz_module_1.Rect" %".6", 0 , !dbg !40
  %".8" = sext i32 %".7" to i64 , !dbg !40
  %".9" = icmp ne i64 %".8", 10 , !dbg !40
  br i1 %".9", label %"if.then", label %"if.end", !dbg !40
if.then:
  %".11" = trunc i64 1 to i32 , !dbg !41
  ret i32 %".11", !dbg !41
if.end:
  %".13" = extractvalue %"struct.ritz_module_1.Rect" %".6", 1 , !dbg !42
  %".14" = sext i32 %".13" to i64 , !dbg !42
  %".15" = icmp ne i64 %".14", 20 , !dbg !42
  br i1 %".15", label %"if.then.1", label %"if.end.1", !dbg !42
if.then.1:
  %".17" = trunc i64 2 to i32 , !dbg !43
  ret i32 %".17", !dbg !43
if.end.1:
  %".19" = extractvalue %"struct.ritz_module_1.Rect" %".6", 2 , !dbg !44
  %".20" = zext i32 %".19" to i64 , !dbg !44
  %".21" = icmp ne i64 %".20", 100 , !dbg !44
  br i1 %".21", label %"if.then.2", label %"if.end.2", !dbg !44
if.then.2:
  %".23" = trunc i64 3 to i32 , !dbg !45
  ret i32 %".23", !dbg !45
if.end.2:
  %".25" = extractvalue %"struct.ritz_module_1.Rect" %".6", 3 , !dbg !46
  %".26" = zext i32 %".25" to i64 , !dbg !46
  %".27" = icmp ne i64 %".26", 50 , !dbg !46
  br i1 %".27", label %"if.then.3", label %"if.end.3", !dbg !46
if.then.3:
  %".29" = trunc i64 4 to i32 , !dbg !47
  ret i32 %".29", !dbg !47
if.end.3:
  %".31" = trunc i64 0 to i32 , !dbg !48
  ret i32 %".31", !dbg !48
}

define i32 @"test_rect_zero"() !dbg !18
{
entry:
  %".2" = call %"struct.ritz_module_1.Rect" @"rect_zero"(), !dbg !49
  %".3" = extractvalue %"struct.ritz_module_1.Rect" %".2", 0 , !dbg !50
  %".4" = sext i32 %".3" to i64 , !dbg !50
  %".5" = icmp ne i64 %".4", 0 , !dbg !50
  br i1 %".5", label %"if.then", label %"if.end", !dbg !50
if.then:
  %".7" = trunc i64 1 to i32 , !dbg !51
  ret i32 %".7", !dbg !51
if.end:
  %".9" = extractvalue %"struct.ritz_module_1.Rect" %".2", 1 , !dbg !52
  %".10" = sext i32 %".9" to i64 , !dbg !52
  %".11" = icmp ne i64 %".10", 0 , !dbg !52
  br i1 %".11", label %"if.then.1", label %"if.end.1", !dbg !52
if.then.1:
  %".13" = trunc i64 2 to i32 , !dbg !53
  ret i32 %".13", !dbg !53
if.end.1:
  %".15" = extractvalue %"struct.ritz_module_1.Rect" %".2", 2 , !dbg !54
  %".16" = zext i32 %".15" to i64 , !dbg !54
  %".17" = icmp ne i64 %".16", 0 , !dbg !54
  br i1 %".17", label %"if.then.2", label %"if.end.2", !dbg !54
if.then.2:
  %".19" = trunc i64 3 to i32 , !dbg !55
  ret i32 %".19", !dbg !55
if.end.2:
  %".21" = extractvalue %"struct.ritz_module_1.Rect" %".2", 3 , !dbg !56
  %".22" = zext i32 %".21" to i64 , !dbg !56
  %".23" = icmp ne i64 %".22", 0 , !dbg !56
  br i1 %".23", label %"if.then.3", label %"if.end.3", !dbg !56
if.then.3:
  %".25" = trunc i64 4 to i32 , !dbg !57
  ret i32 %".25", !dbg !57
if.end.3:
  %".27" = trunc i64 0 to i32 , !dbg !58
  ret i32 %".27", !dbg !58
}

define i32 @"test_rect_area"() !dbg !19
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !59
  %".3" = trunc i64 0 to i32 , !dbg !59
  %".4" = trunc i64 10 to i32 , !dbg !59
  %".5" = trunc i64 20 to i32 , !dbg !59
  %".6" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".2", i32 %".3", i32 %".4", i32 %".5"), !dbg !59
  %"r.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !60
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"r.addr", !dbg !60
  %".8" = call i32 @"rect_area"(%"struct.ritz_module_1.Rect"* %"r.addr"), !dbg !60
  %".9" = sext i32 %".8" to i64 , !dbg !60
  %".10" = icmp ne i64 %".9", 200 , !dbg !60
  br i1 %".10", label %"if.then", label %"if.end", !dbg !60
if.then:
  %".12" = trunc i64 1 to i32 , !dbg !61
  ret i32 %".12", !dbg !61
if.end:
  %".14" = call %"struct.ritz_module_1.Rect" @"rect_zero"(), !dbg !62
  %"empty.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !63
  store %"struct.ritz_module_1.Rect" %".14", %"struct.ritz_module_1.Rect"* %"empty.addr", !dbg !63
  %".16" = call i32 @"rect_area"(%"struct.ritz_module_1.Rect"* %"empty.addr"), !dbg !63
  %".17" = sext i32 %".16" to i64 , !dbg !63
  %".18" = icmp ne i64 %".17", 0 , !dbg !63
  br i1 %".18", label %"if.then.1", label %"if.end.1", !dbg !63
if.then.1:
  %".20" = trunc i64 2 to i32 , !dbg !64
  ret i32 %".20", !dbg !64
if.end.1:
  %".22" = trunc i64 0 to i32 , !dbg !65
  ret i32 %".22", !dbg !65
}

define i32 @"test_rect_is_empty"() !dbg !20
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !66
  %".3" = trunc i64 0 to i32 , !dbg !66
  %".4" = trunc i64 10 to i32 , !dbg !66
  %".5" = trunc i64 20 to i32 , !dbg !66
  %".6" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".2", i32 %".3", i32 %".4", i32 %".5"), !dbg !66
  %"r.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !67
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"r.addr", !dbg !67
  %".8" = call i1 @"rect_is_empty"(%"struct.ritz_module_1.Rect"* %"r.addr"), !dbg !67
  br i1 %".8", label %"if.then", label %"if.end", !dbg !67
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !68
  ret i32 %".10", !dbg !68
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !69
  %".13" = trunc i64 0 to i32 , !dbg !69
  %".14" = trunc i64 0 to i32 , !dbg !69
  %".15" = trunc i64 10 to i32 , !dbg !69
  %".16" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".12", i32 %".13", i32 %".14", i32 %".15"), !dbg !69
  %"zero_width.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !70
  store %"struct.ritz_module_1.Rect" %".16", %"struct.ritz_module_1.Rect"* %"zero_width.addr", !dbg !70
  %".18" = call i1 @"rect_is_empty"(%"struct.ritz_module_1.Rect"* %"zero_width.addr"), !dbg !70
  %".19" = icmp eq i1 %".18", 0 , !dbg !70
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !70
if.then.1:
  %".21" = trunc i64 2 to i32 , !dbg !71
  ret i32 %".21", !dbg !71
if.end.1:
  %".23" = trunc i64 0 to i32 , !dbg !72
  %".24" = trunc i64 0 to i32 , !dbg !72
  %".25" = trunc i64 10 to i32 , !dbg !72
  %".26" = trunc i64 0 to i32 , !dbg !72
  %".27" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".23", i32 %".24", i32 %".25", i32 %".26"), !dbg !72
  %"zero_height.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !73
  store %"struct.ritz_module_1.Rect" %".27", %"struct.ritz_module_1.Rect"* %"zero_height.addr", !dbg !73
  %".29" = call i1 @"rect_is_empty"(%"struct.ritz_module_1.Rect"* %"zero_height.addr"), !dbg !73
  %".30" = icmp eq i1 %".29", 0 , !dbg !73
  br i1 %".30", label %"if.then.2", label %"if.end.2", !dbg !73
if.then.2:
  %".32" = trunc i64 3 to i32 , !dbg !74
  ret i32 %".32", !dbg !74
if.end.2:
  %".34" = trunc i64 0 to i32 , !dbg !75
  ret i32 %".34", !dbg !75
}

define i32 @"test_rect_contains_point_inside"() !dbg !21
{
entry:
  %".2" = trunc i64 10 to i32 , !dbg !76
  %".3" = trunc i64 10 to i32 , !dbg !76
  %".4" = trunc i64 100 to i32 , !dbg !76
  %".5" = trunc i64 100 to i32 , !dbg !76
  %".6" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".2", i32 %".3", i32 %".4", i32 %".5"), !dbg !76
  %"r.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !77
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"r.addr", !dbg !77
  %".8" = trunc i64 60 to i32 , !dbg !77
  %".9" = trunc i64 60 to i32 , !dbg !77
  %".10" = call i1 @"rect_contains_point"(%"struct.ritz_module_1.Rect"* %"r.addr", i32 %".8", i32 %".9"), !dbg !77
  %".11" = icmp eq i1 %".10", 0 , !dbg !77
  br i1 %".11", label %"if.then", label %"if.end", !dbg !77
if.then:
  %".13" = trunc i64 1 to i32 , !dbg !78
  ret i32 %".13", !dbg !78
if.end:
  %"r.addr.1" = alloca %"struct.ritz_module_1.Rect", !dbg !79
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"r.addr.1", !dbg !79
  %".16" = trunc i64 10 to i32 , !dbg !79
  %".17" = trunc i64 10 to i32 , !dbg !79
  %".18" = call i1 @"rect_contains_point"(%"struct.ritz_module_1.Rect"* %"r.addr.1", i32 %".16", i32 %".17"), !dbg !79
  %".19" = icmp eq i1 %".18", 0 , !dbg !79
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !79
if.then.1:
  %".21" = trunc i64 2 to i32 , !dbg !80
  ret i32 %".21", !dbg !80
if.end.1:
  %"r.addr.2" = alloca %"struct.ritz_module_1.Rect", !dbg !81
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"r.addr.2", !dbg !81
  %".24" = trunc i64 109 to i32 , !dbg !81
  %".25" = trunc i64 109 to i32 , !dbg !81
  %".26" = call i1 @"rect_contains_point"(%"struct.ritz_module_1.Rect"* %"r.addr.2", i32 %".24", i32 %".25"), !dbg !81
  %".27" = icmp eq i1 %".26", 0 , !dbg !81
  br i1 %".27", label %"if.then.2", label %"if.end.2", !dbg !81
if.then.2:
  %".29" = trunc i64 3 to i32 , !dbg !82
  ret i32 %".29", !dbg !82
if.end.2:
  %".31" = trunc i64 0 to i32 , !dbg !83
  ret i32 %".31", !dbg !83
}

define i32 @"test_rect_contains_point_outside"() !dbg !22
{
entry:
  %".2" = trunc i64 10 to i32 , !dbg !84
  %".3" = trunc i64 10 to i32 , !dbg !84
  %".4" = trunc i64 100 to i32 , !dbg !84
  %".5" = trunc i64 100 to i32 , !dbg !84
  %".6" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".2", i32 %".3", i32 %".4", i32 %".5"), !dbg !84
  %"r.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !85
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"r.addr", !dbg !85
  %".8" = trunc i64 9 to i32 , !dbg !85
  %".9" = trunc i64 50 to i32 , !dbg !85
  %".10" = call i1 @"rect_contains_point"(%"struct.ritz_module_1.Rect"* %"r.addr", i32 %".8", i32 %".9"), !dbg !85
  br i1 %".10", label %"if.then", label %"if.end", !dbg !85
if.then:
  %".12" = trunc i64 1 to i32 , !dbg !86
  ret i32 %".12", !dbg !86
if.end:
  %"r.addr.1" = alloca %"struct.ritz_module_1.Rect", !dbg !87
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"r.addr.1", !dbg !87
  %".15" = trunc i64 110 to i32 , !dbg !87
  %".16" = trunc i64 50 to i32 , !dbg !87
  %".17" = call i1 @"rect_contains_point"(%"struct.ritz_module_1.Rect"* %"r.addr.1", i32 %".15", i32 %".16"), !dbg !87
  br i1 %".17", label %"if.then.1", label %"if.end.1", !dbg !87
if.then.1:
  %".19" = trunc i64 2 to i32 , !dbg !88
  ret i32 %".19", !dbg !88
if.end.1:
  %"r.addr.2" = alloca %"struct.ritz_module_1.Rect", !dbg !89
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"r.addr.2", !dbg !89
  %".22" = trunc i64 50 to i32 , !dbg !89
  %".23" = trunc i64 9 to i32 , !dbg !89
  %".24" = call i1 @"rect_contains_point"(%"struct.ritz_module_1.Rect"* %"r.addr.2", i32 %".22", i32 %".23"), !dbg !89
  br i1 %".24", label %"if.then.2", label %"if.end.2", !dbg !89
if.then.2:
  %".26" = trunc i64 3 to i32 , !dbg !90
  ret i32 %".26", !dbg !90
if.end.2:
  %"r.addr.3" = alloca %"struct.ritz_module_1.Rect", !dbg !91
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"r.addr.3", !dbg !91
  %".29" = trunc i64 50 to i32 , !dbg !91
  %".30" = trunc i64 110 to i32 , !dbg !91
  %".31" = call i1 @"rect_contains_point"(%"struct.ritz_module_1.Rect"* %"r.addr.3", i32 %".29", i32 %".30"), !dbg !91
  br i1 %".31", label %"if.then.3", label %"if.end.3", !dbg !91
if.then.3:
  %".33" = trunc i64 4 to i32 , !dbg !92
  ret i32 %".33", !dbg !92
if.end.3:
  %".35" = trunc i64 0 to i32 , !dbg !93
  ret i32 %".35", !dbg !93
}

define i32 @"test_rects_intersect_overlapping"() !dbg !23
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !94
  %".3" = trunc i64 0 to i32 , !dbg !94
  %".4" = trunc i64 100 to i32 , !dbg !94
  %".5" = trunc i64 100 to i32 , !dbg !94
  %".6" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".2", i32 %".3", i32 %".4", i32 %".5"), !dbg !94
  %".7" = trunc i64 50 to i32 , !dbg !95
  %".8" = trunc i64 50 to i32 , !dbg !95
  %".9" = trunc i64 100 to i32 , !dbg !95
  %".10" = trunc i64 100 to i32 , !dbg !95
  %".11" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".7", i32 %".8", i32 %".9", i32 %".10"), !dbg !95
  %"a.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !96
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"a.addr", !dbg !96
  %"b.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !96
  store %"struct.ritz_module_1.Rect" %".11", %"struct.ritz_module_1.Rect"* %"b.addr", !dbg !96
  %".14" = call i1 @"rects_intersect"(%"struct.ritz_module_1.Rect"* %"a.addr", %"struct.ritz_module_1.Rect"* %"b.addr"), !dbg !96
  %".15" = icmp eq i1 %".14", 0 , !dbg !96
  br i1 %".15", label %"if.then", label %"if.end", !dbg !96
if.then:
  %".17" = trunc i64 1 to i32 , !dbg !97
  ret i32 %".17", !dbg !97
if.end:
  %"b.addr.1" = alloca %"struct.ritz_module_1.Rect", !dbg !98
  store %"struct.ritz_module_1.Rect" %".11", %"struct.ritz_module_1.Rect"* %"b.addr.1", !dbg !98
  %"a.addr.1" = alloca %"struct.ritz_module_1.Rect", !dbg !98
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"a.addr.1", !dbg !98
  %".21" = call i1 @"rects_intersect"(%"struct.ritz_module_1.Rect"* %"b.addr.1", %"struct.ritz_module_1.Rect"* %"a.addr.1"), !dbg !98
  %".22" = icmp eq i1 %".21", 0 , !dbg !98
  br i1 %".22", label %"if.then.1", label %"if.end.1", !dbg !98
if.then.1:
  %".24" = trunc i64 2 to i32 , !dbg !99
  ret i32 %".24", !dbg !99
if.end.1:
  %".26" = trunc i64 0 to i32 , !dbg !100
  ret i32 %".26", !dbg !100
}

define i32 @"test_rects_intersect_adjacent"() !dbg !24
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !101
  %".3" = trunc i64 0 to i32 , !dbg !101
  %".4" = trunc i64 100 to i32 , !dbg !101
  %".5" = trunc i64 100 to i32 , !dbg !101
  %".6" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".2", i32 %".3", i32 %".4", i32 %".5"), !dbg !101
  %".7" = trunc i64 100 to i32 , !dbg !102
  %".8" = trunc i64 0 to i32 , !dbg !102
  %".9" = trunc i64 100 to i32 , !dbg !102
  %".10" = trunc i64 100 to i32 , !dbg !102
  %".11" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".7", i32 %".8", i32 %".9", i32 %".10"), !dbg !102
  %"a.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !103
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"a.addr", !dbg !103
  %"b.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !103
  store %"struct.ritz_module_1.Rect" %".11", %"struct.ritz_module_1.Rect"* %"b.addr", !dbg !103
  %".14" = call i1 @"rects_intersect"(%"struct.ritz_module_1.Rect"* %"a.addr", %"struct.ritz_module_1.Rect"* %"b.addr"), !dbg !103
  br i1 %".14", label %"if.then", label %"if.end", !dbg !103
if.then:
  %".16" = trunc i64 1 to i32 , !dbg !104
  ret i32 %".16", !dbg !104
if.end:
  %".18" = trunc i64 0 to i32 , !dbg !105
  ret i32 %".18", !dbg !105
}

define i32 @"test_rects_intersect_separate"() !dbg !25
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !106
  %".3" = trunc i64 0 to i32 , !dbg !106
  %".4" = trunc i64 50 to i32 , !dbg !106
  %".5" = trunc i64 50 to i32 , !dbg !106
  %".6" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".2", i32 %".3", i32 %".4", i32 %".5"), !dbg !106
  %".7" = trunc i64 100 to i32 , !dbg !107
  %".8" = trunc i64 100 to i32 , !dbg !107
  %".9" = trunc i64 50 to i32 , !dbg !107
  %".10" = trunc i64 50 to i32 , !dbg !107
  %".11" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".7", i32 %".8", i32 %".9", i32 %".10"), !dbg !107
  %"a.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !108
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"a.addr", !dbg !108
  %"b.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !108
  store %"struct.ritz_module_1.Rect" %".11", %"struct.ritz_module_1.Rect"* %"b.addr", !dbg !108
  %".14" = call i1 @"rects_intersect"(%"struct.ritz_module_1.Rect"* %"a.addr", %"struct.ritz_module_1.Rect"* %"b.addr"), !dbg !108
  br i1 %".14", label %"if.then", label %"if.end", !dbg !108
if.then:
  %".16" = trunc i64 1 to i32 , !dbg !109
  ret i32 %".16", !dbg !109
if.end:
  %".18" = trunc i64 0 to i32 , !dbg !110
  ret i32 %".18", !dbg !110
}

define i32 @"test_rect_union_overlapping"() !dbg !26
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !111
  %".3" = trunc i64 0 to i32 , !dbg !111
  %".4" = trunc i64 50 to i32 , !dbg !111
  %".5" = trunc i64 50 to i32 , !dbg !111
  %".6" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".2", i32 %".3", i32 %".4", i32 %".5"), !dbg !111
  %".7" = trunc i64 25 to i32 , !dbg !112
  %".8" = trunc i64 25 to i32 , !dbg !112
  %".9" = trunc i64 50 to i32 , !dbg !112
  %".10" = trunc i64 50 to i32 , !dbg !112
  %".11" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".7", i32 %".8", i32 %".9", i32 %".10"), !dbg !112
  %"a.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !113
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"a.addr", !dbg !113
  %"b.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !113
  store %"struct.ritz_module_1.Rect" %".11", %"struct.ritz_module_1.Rect"* %"b.addr", !dbg !113
  %".14" = call %"struct.ritz_module_1.Rect" @"rect_union"(%"struct.ritz_module_1.Rect"* %"a.addr", %"struct.ritz_module_1.Rect"* %"b.addr"), !dbg !113
  %".15" = extractvalue %"struct.ritz_module_1.Rect" %".14", 0 , !dbg !114
  %".16" = sext i32 %".15" to i64 , !dbg !114
  %".17" = icmp ne i64 %".16", 0 , !dbg !114
  br i1 %".17", label %"if.then", label %"if.end", !dbg !114
if.then:
  %".19" = trunc i64 1 to i32 , !dbg !115
  ret i32 %".19", !dbg !115
if.end:
  %".21" = extractvalue %"struct.ritz_module_1.Rect" %".14", 1 , !dbg !116
  %".22" = sext i32 %".21" to i64 , !dbg !116
  %".23" = icmp ne i64 %".22", 0 , !dbg !116
  br i1 %".23", label %"if.then.1", label %"if.end.1", !dbg !116
if.then.1:
  %".25" = trunc i64 2 to i32 , !dbg !117
  ret i32 %".25", !dbg !117
if.end.1:
  %".27" = extractvalue %"struct.ritz_module_1.Rect" %".14", 2 , !dbg !118
  %".28" = zext i32 %".27" to i64 , !dbg !118
  %".29" = icmp ne i64 %".28", 75 , !dbg !118
  br i1 %".29", label %"if.then.2", label %"if.end.2", !dbg !118
if.then.2:
  %".31" = trunc i64 3 to i32 , !dbg !119
  ret i32 %".31", !dbg !119
if.end.2:
  %".33" = extractvalue %"struct.ritz_module_1.Rect" %".14", 3 , !dbg !120
  %".34" = zext i32 %".33" to i64 , !dbg !120
  %".35" = icmp ne i64 %".34", 75 , !dbg !120
  br i1 %".35", label %"if.then.3", label %"if.end.3", !dbg !120
if.then.3:
  %".37" = trunc i64 4 to i32 , !dbg !121
  ret i32 %".37", !dbg !121
if.end.3:
  %".39" = trunc i64 0 to i32 , !dbg !122
  ret i32 %".39", !dbg !122
}

define i32 @"test_rect_union_separate"() !dbg !27
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !123
  %".3" = trunc i64 0 to i32 , !dbg !123
  %".4" = trunc i64 10 to i32 , !dbg !123
  %".5" = trunc i64 10 to i32 , !dbg !123
  %".6" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".2", i32 %".3", i32 %".4", i32 %".5"), !dbg !123
  %".7" = trunc i64 90 to i32 , !dbg !124
  %".8" = trunc i64 90 to i32 , !dbg !124
  %".9" = trunc i64 10 to i32 , !dbg !124
  %".10" = trunc i64 10 to i32 , !dbg !124
  %".11" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".7", i32 %".8", i32 %".9", i32 %".10"), !dbg !124
  %"a.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !125
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"a.addr", !dbg !125
  %"b.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !125
  store %"struct.ritz_module_1.Rect" %".11", %"struct.ritz_module_1.Rect"* %"b.addr", !dbg !125
  %".14" = call %"struct.ritz_module_1.Rect" @"rect_union"(%"struct.ritz_module_1.Rect"* %"a.addr", %"struct.ritz_module_1.Rect"* %"b.addr"), !dbg !125
  %".15" = extractvalue %"struct.ritz_module_1.Rect" %".14", 0 , !dbg !126
  %".16" = sext i32 %".15" to i64 , !dbg !126
  %".17" = icmp ne i64 %".16", 0 , !dbg !126
  br i1 %".17", label %"if.then", label %"if.end", !dbg !126
if.then:
  %".19" = trunc i64 1 to i32 , !dbg !127
  ret i32 %".19", !dbg !127
if.end:
  %".21" = extractvalue %"struct.ritz_module_1.Rect" %".14", 1 , !dbg !128
  %".22" = sext i32 %".21" to i64 , !dbg !128
  %".23" = icmp ne i64 %".22", 0 , !dbg !128
  br i1 %".23", label %"if.then.1", label %"if.end.1", !dbg !128
if.then.1:
  %".25" = trunc i64 2 to i32 , !dbg !129
  ret i32 %".25", !dbg !129
if.end.1:
  %".27" = extractvalue %"struct.ritz_module_1.Rect" %".14", 2 , !dbg !130
  %".28" = zext i32 %".27" to i64 , !dbg !130
  %".29" = icmp ne i64 %".28", 100 , !dbg !130
  br i1 %".29", label %"if.then.2", label %"if.end.2", !dbg !130
if.then.2:
  %".31" = trunc i64 3 to i32 , !dbg !131
  ret i32 %".31", !dbg !131
if.end.2:
  %".33" = extractvalue %"struct.ritz_module_1.Rect" %".14", 3 , !dbg !132
  %".34" = zext i32 %".33" to i64 , !dbg !132
  %".35" = icmp ne i64 %".34", 100 , !dbg !132
  br i1 %".35", label %"if.then.3", label %"if.end.3", !dbg !132
if.then.3:
  %".37" = trunc i64 4 to i32 , !dbg !133
  ret i32 %".37", !dbg !133
if.end.3:
  %".39" = trunc i64 0 to i32 , !dbg !134
  ret i32 %".39", !dbg !134
}

define i32 @"test_rect_intersection_overlapping"() !dbg !28
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !135
  %".3" = trunc i64 0 to i32 , !dbg !135
  %".4" = trunc i64 100 to i32 , !dbg !135
  %".5" = trunc i64 100 to i32 , !dbg !135
  %".6" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".2", i32 %".3", i32 %".4", i32 %".5"), !dbg !135
  %".7" = trunc i64 50 to i32 , !dbg !136
  %".8" = trunc i64 50 to i32 , !dbg !136
  %".9" = trunc i64 100 to i32 , !dbg !136
  %".10" = trunc i64 100 to i32 , !dbg !136
  %".11" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".7", i32 %".8", i32 %".9", i32 %".10"), !dbg !136
  %"a.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !137
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"a.addr", !dbg !137
  %"b.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !137
  store %"struct.ritz_module_1.Rect" %".11", %"struct.ritz_module_1.Rect"* %"b.addr", !dbg !137
  %".14" = call %"struct.ritz_module_1.Rect" @"rect_intersection"(%"struct.ritz_module_1.Rect"* %"a.addr", %"struct.ritz_module_1.Rect"* %"b.addr"), !dbg !137
  %".15" = extractvalue %"struct.ritz_module_1.Rect" %".14", 0 , !dbg !138
  %".16" = sext i32 %".15" to i64 , !dbg !138
  %".17" = icmp ne i64 %".16", 50 , !dbg !138
  br i1 %".17", label %"if.then", label %"if.end", !dbg !138
if.then:
  %".19" = trunc i64 1 to i32 , !dbg !139
  ret i32 %".19", !dbg !139
if.end:
  %".21" = extractvalue %"struct.ritz_module_1.Rect" %".14", 1 , !dbg !140
  %".22" = sext i32 %".21" to i64 , !dbg !140
  %".23" = icmp ne i64 %".22", 50 , !dbg !140
  br i1 %".23", label %"if.then.1", label %"if.end.1", !dbg !140
if.then.1:
  %".25" = trunc i64 2 to i32 , !dbg !141
  ret i32 %".25", !dbg !141
if.end.1:
  %".27" = extractvalue %"struct.ritz_module_1.Rect" %".14", 2 , !dbg !142
  %".28" = zext i32 %".27" to i64 , !dbg !142
  %".29" = icmp ne i64 %".28", 50 , !dbg !142
  br i1 %".29", label %"if.then.2", label %"if.end.2", !dbg !142
if.then.2:
  %".31" = trunc i64 3 to i32 , !dbg !143
  ret i32 %".31", !dbg !143
if.end.2:
  %".33" = extractvalue %"struct.ritz_module_1.Rect" %".14", 3 , !dbg !144
  %".34" = zext i32 %".33" to i64 , !dbg !144
  %".35" = icmp ne i64 %".34", 50 , !dbg !144
  br i1 %".35", label %"if.then.3", label %"if.end.3", !dbg !144
if.then.3:
  %".37" = trunc i64 4 to i32 , !dbg !145
  ret i32 %".37", !dbg !145
if.end.3:
  %".39" = trunc i64 0 to i32 , !dbg !146
  ret i32 %".39", !dbg !146
}

define i32 @"test_rect_intersection_no_overlap"() !dbg !29
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !147
  %".3" = trunc i64 0 to i32 , !dbg !147
  %".4" = trunc i64 50 to i32 , !dbg !147
  %".5" = trunc i64 50 to i32 , !dbg !147
  %".6" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".2", i32 %".3", i32 %".4", i32 %".5"), !dbg !147
  %".7" = trunc i64 100 to i32 , !dbg !148
  %".8" = trunc i64 100 to i32 , !dbg !148
  %".9" = trunc i64 50 to i32 , !dbg !148
  %".10" = trunc i64 50 to i32 , !dbg !148
  %".11" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".7", i32 %".8", i32 %".9", i32 %".10"), !dbg !148
  %"a.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !149
  store %"struct.ritz_module_1.Rect" %".6", %"struct.ritz_module_1.Rect"* %"a.addr", !dbg !149
  %"b.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !149
  store %"struct.ritz_module_1.Rect" %".11", %"struct.ritz_module_1.Rect"* %"b.addr", !dbg !149
  %".14" = call %"struct.ritz_module_1.Rect" @"rect_intersection"(%"struct.ritz_module_1.Rect"* %"a.addr", %"struct.ritz_module_1.Rect"* %"b.addr"), !dbg !149
  %"i.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !150
  store %"struct.ritz_module_1.Rect" %".14", %"struct.ritz_module_1.Rect"* %"i.addr", !dbg !150
  %".16" = call i1 @"rect_is_empty"(%"struct.ritz_module_1.Rect"* %"i.addr"), !dbg !150
  %".17" = icmp eq i1 %".16", 0 , !dbg !150
  br i1 %".17", label %"if.then", label %"if.end", !dbg !150
if.then:
  %".19" = trunc i64 1 to i32 , !dbg !151
  ret i32 %".19", !dbg !151
if.end:
  %".21" = trunc i64 0 to i32 , !dbg !152
  ret i32 %".21", !dbg !152
}

define i32 @"test_damage_region_new_empty"() !dbg !30
{
entry:
  %".2" = call %"struct.ritz_module_1.DamageRegion" @"damage_region_new"(), !dbg !153
  %"region.addr" = alloca %"struct.ritz_module_1.DamageRegion", !dbg !154
  store %"struct.ritz_module_1.DamageRegion" %".2", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !154
  %".4" = call i1 @"damage_region_is_empty"(%"struct.ritz_module_1.DamageRegion"* %"region.addr"), !dbg !154
  %".5" = icmp eq i1 %".4", 0 , !dbg !154
  br i1 %".5", label %"if.then", label %"if.end", !dbg !154
if.then:
  %".7" = trunc i64 1 to i32 , !dbg !155
  ret i32 %".7", !dbg !155
if.end:
  %"region.addr.1" = alloca %"struct.ritz_module_1.DamageRegion", !dbg !156
  store %"struct.ritz_module_1.DamageRegion" %".2", %"struct.ritz_module_1.DamageRegion"* %"region.addr.1", !dbg !156
  %".10" = call i32 @"damage_region_count"(%"struct.ritz_module_1.DamageRegion"* %"region.addr.1"), !dbg !156
  %".11" = sext i32 %".10" to i64 , !dbg !156
  %".12" = icmp ne i64 %".11", 0 , !dbg !156
  br i1 %".12", label %"if.then.1", label %"if.end.1", !dbg !156
if.then.1:
  %".14" = trunc i64 2 to i32 , !dbg !157
  ret i32 %".14", !dbg !157
if.end.1:
  %".16" = trunc i64 0 to i32 , !dbg !158
  ret i32 %".16", !dbg !158
}

define i32 @"test_damage_region_add_single"() !dbg !31
{
entry:
  %"region.addr" = alloca %"struct.ritz_module_1.DamageRegion", !dbg !159
  %".2" = call %"struct.ritz_module_1.DamageRegion" @"damage_region_new"(), !dbg !159
  store %"struct.ritz_module_1.DamageRegion" %".2", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !159
  %".4" = trunc i64 10 to i32 , !dbg !160
  %".5" = trunc i64 20 to i32 , !dbg !160
  %".6" = trunc i64 30 to i32 , !dbg !160
  %".7" = trunc i64 40 to i32 , !dbg !160
  %".8" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".4", i32 %".5", i32 %".6", i32 %".7"), !dbg !160
  %".9" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !161
  %".10" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".9", i32 0, i64 0 , !dbg !161
  store %"struct.ritz_module_1.Rect" %".8", %"struct.ritz_module_1.Rect"* %".10", !dbg !161
  %".12" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !162
  %".13" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !162
  %".14" = trunc i64 1 to i32 , !dbg !162
  store i32 %".14", i32* %".13", !dbg !162
  %".16" = call i1 @"damage_region_is_empty"(%"struct.ritz_module_1.DamageRegion"* %"region.addr"), !dbg !163
  br i1 %".16", label %"if.then", label %"if.end", !dbg !163
if.then:
  %".18" = trunc i64 1 to i32 , !dbg !164
  ret i32 %".18", !dbg !164
if.end:
  %".20" = call i32 @"damage_region_count"(%"struct.ritz_module_1.DamageRegion"* %"region.addr"), !dbg !165
  %".21" = sext i32 %".20" to i64 , !dbg !165
  %".22" = icmp ne i64 %".21", 1 , !dbg !165
  br i1 %".22", label %"if.then.1", label %"if.end.1", !dbg !165
if.then.1:
  %".24" = trunc i64 2 to i32 , !dbg !166
  ret i32 %".24", !dbg !166
if.end.1:
  %".26" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !167
  %".27" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".26", i32 0, i64 0 , !dbg !167
  %".28" = load %"struct.ritz_module_1.Rect", %"struct.ritz_module_1.Rect"* %".27", !dbg !167
  %".29" = extractvalue %"struct.ritz_module_1.Rect" %".28", 0 , !dbg !167
  %".30" = sext i32 %".29" to i64 , !dbg !167
  %".31" = icmp ne i64 %".30", 10 , !dbg !167
  br i1 %".31", label %"if.then.2", label %"if.end.2", !dbg !167
if.then.2:
  %".33" = trunc i64 3 to i32 , !dbg !168
  ret i32 %".33", !dbg !168
if.end.2:
  %".35" = trunc i64 0 to i32 , !dbg !169
  ret i32 %".35", !dbg !169
}

define i32 @"test_damage_region_add_multiple"() !dbg !32
{
entry:
  %"region.addr" = alloca %"struct.ritz_module_1.DamageRegion", !dbg !170
  %".2" = call %"struct.ritz_module_1.DamageRegion" @"damage_region_new"(), !dbg !170
  store %"struct.ritz_module_1.DamageRegion" %".2", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !170
  %".4" = trunc i64 0 to i32 , !dbg !171
  %".5" = trunc i64 0 to i32 , !dbg !171
  %".6" = trunc i64 10 to i32 , !dbg !171
  %".7" = trunc i64 10 to i32 , !dbg !171
  %".8" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".4", i32 %".5", i32 %".6", i32 %".7"), !dbg !171
  %".9" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !171
  %".10" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".9", i32 0, i64 0 , !dbg !171
  store %"struct.ritz_module_1.Rect" %".8", %"struct.ritz_module_1.Rect"* %".10", !dbg !171
  %".12" = trunc i64 20 to i32 , !dbg !172
  %".13" = trunc i64 20 to i32 , !dbg !172
  %".14" = trunc i64 10 to i32 , !dbg !172
  %".15" = trunc i64 10 to i32 , !dbg !172
  %".16" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".12", i32 %".13", i32 %".14", i32 %".15"), !dbg !172
  %".17" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !172
  %".18" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".17", i32 0, i64 1 , !dbg !172
  store %"struct.ritz_module_1.Rect" %".16", %"struct.ritz_module_1.Rect"* %".18", !dbg !172
  %".20" = trunc i64 40 to i32 , !dbg !173
  %".21" = trunc i64 40 to i32 , !dbg !173
  %".22" = trunc i64 10 to i32 , !dbg !173
  %".23" = trunc i64 10 to i32 , !dbg !173
  %".24" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".20", i32 %".21", i32 %".22", i32 %".23"), !dbg !173
  %".25" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !173
  %".26" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".25", i32 0, i64 2 , !dbg !173
  store %"struct.ritz_module_1.Rect" %".24", %"struct.ritz_module_1.Rect"* %".26", !dbg !173
  %".28" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !174
  %".29" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !174
  %".30" = trunc i64 3 to i32 , !dbg !174
  store i32 %".30", i32* %".29", !dbg !174
  %".32" = call i32 @"damage_region_count"(%"struct.ritz_module_1.DamageRegion"* %"region.addr"), !dbg !175
  %".33" = sext i32 %".32" to i64 , !dbg !175
  %".34" = icmp ne i64 %".33", 3 , !dbg !175
  br i1 %".34", label %"if.then", label %"if.end", !dbg !175
if.then:
  %".36" = trunc i64 1 to i32 , !dbg !176
  ret i32 %".36", !dbg !176
if.end:
  %".38" = trunc i64 0 to i32 , !dbg !177
  ret i32 %".38", !dbg !177
}

define i32 @"test_damage_region_clear_removes_all"() !dbg !33
{
entry:
  %"region.addr" = alloca %"struct.ritz_module_1.DamageRegion", !dbg !178
  %".2" = call %"struct.ritz_module_1.DamageRegion" @"damage_region_new"(), !dbg !178
  store %"struct.ritz_module_1.DamageRegion" %".2", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !178
  %".4" = trunc i64 0 to i32 , !dbg !179
  %".5" = trunc i64 0 to i32 , !dbg !179
  %".6" = trunc i64 10 to i32 , !dbg !179
  %".7" = trunc i64 10 to i32 , !dbg !179
  %".8" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".4", i32 %".5", i32 %".6", i32 %".7"), !dbg !179
  %".9" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !179
  %".10" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".9", i32 0, i64 0 , !dbg !179
  store %"struct.ritz_module_1.Rect" %".8", %"struct.ritz_module_1.Rect"* %".10", !dbg !179
  %".12" = trunc i64 20 to i32 , !dbg !180
  %".13" = trunc i64 20 to i32 , !dbg !180
  %".14" = trunc i64 10 to i32 , !dbg !180
  %".15" = trunc i64 10 to i32 , !dbg !180
  %".16" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".12", i32 %".13", i32 %".14", i32 %".15"), !dbg !180
  %".17" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !180
  %".18" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".17", i32 0, i64 1 , !dbg !180
  store %"struct.ritz_module_1.Rect" %".16", %"struct.ritz_module_1.Rect"* %".18", !dbg !180
  %".20" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !181
  %".21" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !181
  %".22" = trunc i64 2 to i32 , !dbg !181
  store i32 %".22", i32* %".21", !dbg !181
  %".24" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !182
  %".25" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !182
  %".26" = trunc i64 0 to i32 , !dbg !182
  store i32 %".26", i32* %".25", !dbg !182
  %".28" = call i1 @"damage_region_is_empty"(%"struct.ritz_module_1.DamageRegion"* %"region.addr"), !dbg !183
  %".29" = icmp eq i1 %".28", 0 , !dbg !183
  br i1 %".29", label %"if.then", label %"if.end", !dbg !183
if.then:
  %".31" = trunc i64 1 to i32 , !dbg !184
  ret i32 %".31", !dbg !184
if.end:
  %".33" = call i32 @"damage_region_count"(%"struct.ritz_module_1.DamageRegion"* %"region.addr"), !dbg !185
  %".34" = sext i32 %".33" to i64 , !dbg !185
  %".35" = icmp ne i64 %".34", 0 , !dbg !185
  br i1 %".35", label %"if.then.1", label %"if.end.1", !dbg !185
if.then.1:
  %".37" = trunc i64 2 to i32 , !dbg !186
  ret i32 %".37", !dbg !186
if.end.1:
  %".39" = trunc i64 0 to i32 , !dbg !187
  ret i32 %".39", !dbg !187
}

define i32 @"test_damage_region_bounds_single"() !dbg !34
{
entry:
  %"region.addr" = alloca %"struct.ritz_module_1.DamageRegion", !dbg !188
  %".2" = call %"struct.ritz_module_1.DamageRegion" @"damage_region_new"(), !dbg !188
  store %"struct.ritz_module_1.DamageRegion" %".2", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !188
  %".4" = trunc i64 10 to i32 , !dbg !189
  %".5" = trunc i64 20 to i32 , !dbg !189
  %".6" = trunc i64 30 to i32 , !dbg !189
  %".7" = trunc i64 40 to i32 , !dbg !189
  %".8" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".4", i32 %".5", i32 %".6", i32 %".7"), !dbg !189
  %".9" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !189
  %".10" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".9", i32 0, i64 0 , !dbg !189
  store %"struct.ritz_module_1.Rect" %".8", %"struct.ritz_module_1.Rect"* %".10", !dbg !189
  %".12" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !190
  %".13" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !190
  %".14" = trunc i64 1 to i32 , !dbg !190
  store i32 %".14", i32* %".13", !dbg !190
  %".16" = call %"struct.ritz_module_1.Rect" @"damage_region_bounds"(%"struct.ritz_module_1.DamageRegion"* %"region.addr"), !dbg !191
  %".17" = extractvalue %"struct.ritz_module_1.Rect" %".16", 0 , !dbg !192
  %".18" = sext i32 %".17" to i64 , !dbg !192
  %".19" = icmp ne i64 %".18", 10 , !dbg !192
  br i1 %".19", label %"if.then", label %"if.end", !dbg !192
if.then:
  %".21" = trunc i64 1 to i32 , !dbg !193
  ret i32 %".21", !dbg !193
if.end:
  %".23" = extractvalue %"struct.ritz_module_1.Rect" %".16", 1 , !dbg !194
  %".24" = sext i32 %".23" to i64 , !dbg !194
  %".25" = icmp ne i64 %".24", 20 , !dbg !194
  br i1 %".25", label %"if.then.1", label %"if.end.1", !dbg !194
if.then.1:
  %".27" = trunc i64 2 to i32 , !dbg !195
  ret i32 %".27", !dbg !195
if.end.1:
  %".29" = extractvalue %"struct.ritz_module_1.Rect" %".16", 2 , !dbg !196
  %".30" = zext i32 %".29" to i64 , !dbg !196
  %".31" = icmp ne i64 %".30", 30 , !dbg !196
  br i1 %".31", label %"if.then.2", label %"if.end.2", !dbg !196
if.then.2:
  %".33" = trunc i64 3 to i32 , !dbg !197
  ret i32 %".33", !dbg !197
if.end.2:
  %".35" = extractvalue %"struct.ritz_module_1.Rect" %".16", 3 , !dbg !198
  %".36" = zext i32 %".35" to i64 , !dbg !198
  %".37" = icmp ne i64 %".36", 40 , !dbg !198
  br i1 %".37", label %"if.then.3", label %"if.end.3", !dbg !198
if.then.3:
  %".39" = trunc i64 4 to i32 , !dbg !199
  ret i32 %".39", !dbg !199
if.end.3:
  %".41" = trunc i64 0 to i32 , !dbg !200
  ret i32 %".41", !dbg !200
}

define i32 @"test_damage_region_bounds_multiple"() !dbg !35
{
entry:
  %"region.addr" = alloca %"struct.ritz_module_1.DamageRegion", !dbg !201
  %".2" = call %"struct.ritz_module_1.DamageRegion" @"damage_region_new"(), !dbg !201
  store %"struct.ritz_module_1.DamageRegion" %".2", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !201
  %".4" = trunc i64 10 to i32 , !dbg !202
  %".5" = trunc i64 10 to i32 , !dbg !202
  %".6" = trunc i64 20 to i32 , !dbg !202
  %".7" = trunc i64 20 to i32 , !dbg !202
  %".8" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".4", i32 %".5", i32 %".6", i32 %".7"), !dbg !202
  %".9" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !202
  %".10" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".9", i32 0, i64 0 , !dbg !202
  store %"struct.ritz_module_1.Rect" %".8", %"struct.ritz_module_1.Rect"* %".10", !dbg !202
  %".12" = trunc i64 50 to i32 , !dbg !203
  %".13" = trunc i64 50 to i32 , !dbg !203
  %".14" = trunc i64 30 to i32 , !dbg !203
  %".15" = trunc i64 30 to i32 , !dbg !203
  %".16" = call %"struct.ritz_module_1.Rect" @"rect_new"(i32 %".12", i32 %".13", i32 %".14", i32 %".15"), !dbg !203
  %".17" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 0 , !dbg !203
  %".18" = getelementptr [16 x %"struct.ritz_module_1.Rect"], [16 x %"struct.ritz_module_1.Rect"]* %".17", i32 0, i64 1 , !dbg !203
  store %"struct.ritz_module_1.Rect" %".16", %"struct.ritz_module_1.Rect"* %".18", !dbg !203
  %".20" = load %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !204
  %".21" = getelementptr %"struct.ritz_module_1.DamageRegion", %"struct.ritz_module_1.DamageRegion"* %"region.addr", i32 0, i32 1 , !dbg !204
  %".22" = trunc i64 2 to i32 , !dbg !204
  store i32 %".22", i32* %".21", !dbg !204
  %".24" = call %"struct.ritz_module_1.Rect" @"damage_region_bounds"(%"struct.ritz_module_1.DamageRegion"* %"region.addr"), !dbg !205
  %".25" = extractvalue %"struct.ritz_module_1.Rect" %".24", 0 , !dbg !206
  %".26" = sext i32 %".25" to i64 , !dbg !206
  %".27" = icmp ne i64 %".26", 10 , !dbg !206
  br i1 %".27", label %"if.then", label %"if.end", !dbg !206
if.then:
  %".29" = trunc i64 1 to i32 , !dbg !207
  ret i32 %".29", !dbg !207
if.end:
  %".31" = extractvalue %"struct.ritz_module_1.Rect" %".24", 1 , !dbg !208
  %".32" = sext i32 %".31" to i64 , !dbg !208
  %".33" = icmp ne i64 %".32", 10 , !dbg !208
  br i1 %".33", label %"if.then.1", label %"if.end.1", !dbg !208
if.then.1:
  %".35" = trunc i64 2 to i32 , !dbg !209
  ret i32 %".35", !dbg !209
if.end.1:
  %".37" = extractvalue %"struct.ritz_module_1.Rect" %".24", 2 , !dbg !210
  %".38" = zext i32 %".37" to i64 , !dbg !210
  %".39" = icmp ne i64 %".38", 70 , !dbg !210
  br i1 %".39", label %"if.then.2", label %"if.end.2", !dbg !210
if.then.2:
  %".41" = trunc i64 3 to i32 , !dbg !211
  ret i32 %".41", !dbg !211
if.end.2:
  %".43" = extractvalue %"struct.ritz_module_1.Rect" %".24", 3 , !dbg !212
  %".44" = zext i32 %".43" to i64 , !dbg !212
  %".45" = icmp ne i64 %".44", 70 , !dbg !212
  br i1 %".45", label %"if.then.3", label %"if.end.3", !dbg !212
if.then.3:
  %".47" = trunc i64 4 to i32 , !dbg !213
  ret i32 %".47", !dbg !213
if.end.3:
  %".49" = trunc i64 0 to i32 , !dbg !214
  ret i32 %".49", !dbg !214
}

define i32 @"test_damage_region_bounds_empty"() !dbg !36
{
entry:
  %".2" = call %"struct.ritz_module_1.DamageRegion" @"damage_region_new"(), !dbg !215
  %"region.addr" = alloca %"struct.ritz_module_1.DamageRegion", !dbg !216
  store %"struct.ritz_module_1.DamageRegion" %".2", %"struct.ritz_module_1.DamageRegion"* %"region.addr", !dbg !216
  %".4" = call %"struct.ritz_module_1.Rect" @"damage_region_bounds"(%"struct.ritz_module_1.DamageRegion"* %"region.addr"), !dbg !216
  %"bounds.addr" = alloca %"struct.ritz_module_1.Rect", !dbg !217
  store %"struct.ritz_module_1.Rect" %".4", %"struct.ritz_module_1.Rect"* %"bounds.addr", !dbg !217
  %".6" = call i1 @"rect_is_empty"(%"struct.ritz_module_1.Rect"* %"bounds.addr"), !dbg !217
  %".7" = icmp eq i1 %".6", 0 , !dbg !217
  br i1 %".7", label %"if.then", label %"if.end", !dbg !217
if.then:
  %".9" = trunc i64 1 to i32 , !dbg !218
  ret i32 %".9", !dbg !218
if.end:
  %".11" = trunc i64 0 to i32 , !dbg !219
  ret i32 %".11", !dbg !219
}

define i32 @"print_result"(i8* %"name.arg", i32 %"result.arg") !dbg !37
{
entry:
  %"name" = alloca i8*
  %"buf.addr" = alloca [10 x i8], !dbg !228
  %"n.addr" = alloca i32, !dbg !234
  %"i.addr" = alloca i64, !dbg !237
  %"j.addr" = alloca i64, !dbg !247
  store i8* %"name.arg", i8** %"name"
  call void @"llvm.dbg.declare"(metadata i8** %"name", metadata !221, metadata !7), !dbg !222
  %"result" = alloca i32
  store i32 %"result.arg", i32* %"result"
  call void @"llvm.dbg.declare"(metadata i32* %"result", metadata !223, metadata !7), !dbg !222
  %".8" = load i32, i32* %"result", !dbg !224
  %".9" = sext i32 %".8" to i64 , !dbg !224
  %".10" = icmp eq i64 %".9", 0 , !dbg !224
  br i1 %".10", label %"if.then", label %"if.else", !dbg !224
if.then:
  %".12" = trunc i64 1 to i32 , !dbg !225
  %".13" = load i8*, i8** %"name", !dbg !225
  %".14" = call i64 @"sys_write"(i32 %".12", i8* %".13", i64 40), !dbg !225
  %".15" = trunc i64 1 to i32 , !dbg !225
  %".16" = getelementptr [7 x i8], [7 x i8]* @".str.0", i64 0, i64 0 , !dbg !225
  %".17" = call i64 @"sys_write"(i32 %".15", i8* %".16", i64 6), !dbg !225
  br label %"if.end", !dbg !255
if.else:
  %".18" = trunc i64 1 to i32 , !dbg !226
  %".19" = load i8*, i8** %"name", !dbg !226
  %".20" = call i64 @"sys_write"(i32 %".18", i8* %".19", i64 40), !dbg !226
  %".21" = trunc i64 1 to i32 , !dbg !227
  %".22" = getelementptr [8 x i8], [8 x i8]* @".str.1", i64 0, i64 0 , !dbg !227
  %".23" = call i64 @"sys_write"(i32 %".21", i8* %".22", i64 7), !dbg !227
  call void @"llvm.dbg.declare"(metadata [10 x i8]* %"buf.addr", metadata !232, metadata !7), !dbg !233
  %".25" = load i32, i32* %"result", !dbg !234
  store i32 %".25", i32* %"n.addr", !dbg !234
  call void @"llvm.dbg.declare"(metadata i32* %"n.addr", metadata !235, metadata !7), !dbg !236
  store i64 0, i64* %"i.addr", !dbg !237
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !238, metadata !7), !dbg !239
  %".30" = load i32, i32* %"n.addr", !dbg !240
  %".31" = sext i32 %".30" to i64 , !dbg !240
  %".32" = icmp eq i64 %".31", 0 , !dbg !240
  br i1 %".32", label %"if.then.1", label %"if.else.1", !dbg !240
if.end:
  %".101" = phi  i64 [%".17", %"if.then"], [%".98", %"if.end.1"] , !dbg !255
  %".102" = trunc i64 %".101" to i32 , !dbg !255
  ret i32 %".102", !dbg !255
if.then.1:
  %".34" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !241
  %".35" = trunc i64 48 to i8 , !dbg !241
  store i8 %".35", i8* %".34", !dbg !241
  store i64 1, i64* %"i.addr", !dbg !242
  br label %"if.end.1", !dbg !254
if.else.1:
  br label %"while.cond", !dbg !243
if.end.1:
  %".92" = trunc i64 1 to i32 , !dbg !255
  %".93" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !255
  %".94" = load i64, i64* %"i.addr", !dbg !255
  %".95" = call i64 @"sys_write"(i32 %".92", i8* %".93", i64 %".94"), !dbg !255
  %".96" = trunc i64 1 to i32 , !dbg !255
  %".97" = getelementptr [3 x i8], [3 x i8]* @".str.2", i64 0, i64 0 , !dbg !255
  %".98" = call i64 @"sys_write"(i32 %".96", i8* %".97", i64 2), !dbg !255
  br label %"if.end", !dbg !255
while.cond:
  %".39" = load i32, i32* %"n.addr", !dbg !243
  %".40" = sext i32 %".39" to i64 , !dbg !243
  %".41" = icmp sgt i64 %".40", 0 , !dbg !243
  br i1 %".41", label %"while.body", label %"while.end", !dbg !243
while.body:
  %".43" = load i32, i32* %"n.addr", !dbg !244
  %".44" = sext i32 %".43" to i64 , !dbg !244
  %".45" = srem i64 %".44", 10, !dbg !244
  %".46" = add i64 48, %".45", !dbg !244
  %".47" = trunc i64 %".46" to i8 , !dbg !244
  %".48" = load i64, i64* %"i.addr", !dbg !244
  %".49" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 %".48" , !dbg !244
  store i8 %".47", i8* %".49", !dbg !244
  %".51" = load i32, i32* %"n.addr", !dbg !245
  %".52" = sext i32 %".51" to i64 , !dbg !245
  %".53" = sdiv i64 %".52", 10, !dbg !245
  %".54" = trunc i64 %".53" to i32 , !dbg !245
  store i32 %".54", i32* %"n.addr", !dbg !245
  %".56" = load i64, i64* %"i.addr", !dbg !246
  %".57" = add i64 %".56", 1, !dbg !246
  store i64 %".57", i64* %"i.addr", !dbg !246
  br label %"while.cond", !dbg !246
while.end:
  store i64 0, i64* %"j.addr", !dbg !247
  call void @"llvm.dbg.declare"(metadata i64* %"j.addr", metadata !248, metadata !7), !dbg !249
  br label %"while.cond.1", !dbg !250
while.cond.1:
  %".63" = load i64, i64* %"j.addr", !dbg !250
  %".64" = load i64, i64* %"i.addr", !dbg !250
  %".65" = sdiv i64 %".64", 2, !dbg !250
  %".66" = icmp slt i64 %".63", %".65" , !dbg !250
  br i1 %".66", label %"while.body.1", label %"while.end.1", !dbg !250
while.body.1:
  %".68" = load i64, i64* %"j.addr", !dbg !251
  %".69" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 %".68" , !dbg !251
  %".70" = load i8, i8* %".69", !dbg !251
  %".71" = load i64, i64* %"i.addr", !dbg !252
  %".72" = sub i64 %".71", 1, !dbg !252
  %".73" = load i64, i64* %"j.addr", !dbg !252
  %".74" = sub i64 %".72", %".73", !dbg !252
  %".75" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 %".74" , !dbg !252
  %".76" = load i8, i8* %".75", !dbg !252
  %".77" = load i64, i64* %"j.addr", !dbg !252
  %".78" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 %".77" , !dbg !252
  store i8 %".76", i8* %".78", !dbg !252
  %".80" = load i64, i64* %"i.addr", !dbg !253
  %".81" = sub i64 %".80", 1, !dbg !253
  %".82" = load i64, i64* %"j.addr", !dbg !253
  %".83" = sub i64 %".81", %".82", !dbg !253
  %".84" = getelementptr [10 x i8], [10 x i8]* %"buf.addr", i32 0, i64 %".83" , !dbg !253
  store i8 %".70", i8* %".84", !dbg !253
  %".86" = load i64, i64* %"j.addr", !dbg !254
  %".87" = add i64 %".86", 1, !dbg !254
  store i64 %".87", i64* %"j.addr", !dbg !254
  br label %"while.cond.1", !dbg !254
while.end.1:
  br label %"if.end.1", !dbg !254
}

define i32 @"main"() !dbg !38
{
entry:
  %"failed.addr" = alloca i32, !dbg !256
  %"result.addr" = alloca i32, !dbg !259
  %".2" = trunc i64 0 to i32 , !dbg !256
  store i32 %".2", i32* %"failed.addr", !dbg !256
  call void @"llvm.dbg.declare"(metadata i32* %"failed.addr", metadata !257, metadata !7), !dbg !258
  %".5" = trunc i64 0 to i32 , !dbg !259
  store i32 %".5", i32* %"result.addr", !dbg !259
  call void @"llvm.dbg.declare"(metadata i32* %"result.addr", metadata !260, metadata !7), !dbg !261
  %".8" = trunc i64 1 to i32 , !dbg !262
  %".9" = getelementptr [33 x i8], [33 x i8]* @".str.3", i64 0, i64 0 , !dbg !262
  %".10" = call i64 @"sys_write"(i32 %".8", i8* %".9", i64 33), !dbg !262
  %".11" = call i32 @"test_rect_new"(), !dbg !263
  store i32 %".11", i32* %"result.addr", !dbg !263
  %".13" = getelementptr [41 x i8], [41 x i8]* @".str.4", i64 0, i64 0 , !dbg !264
  %".14" = load i32, i32* %"result.addr", !dbg !264
  %".15" = call i32 @"print_result"(i8* %".13", i32 %".14"), !dbg !264
  %".16" = load i32, i32* %"result.addr", !dbg !265
  %".17" = sext i32 %".16" to i64 , !dbg !265
  %".18" = icmp ne i64 %".17", 0 , !dbg !265
  br i1 %".18", label %"if.then", label %"if.end", !dbg !265
if.then:
  %".20" = load i32, i32* %"failed.addr", !dbg !266
  %".21" = sext i32 %".20" to i64 , !dbg !266
  %".22" = add i64 %".21", 1, !dbg !266
  %".23" = trunc i64 %".22" to i32 , !dbg !266
  store i32 %".23", i32* %"failed.addr", !dbg !266
  br label %"if.end", !dbg !266
if.end:
  %".26" = call i32 @"test_rect_zero"(), !dbg !267
  store i32 %".26", i32* %"result.addr", !dbg !267
  %".28" = getelementptr [41 x i8], [41 x i8]* @".str.5", i64 0, i64 0 , !dbg !268
  %".29" = load i32, i32* %"result.addr", !dbg !268
  %".30" = call i32 @"print_result"(i8* %".28", i32 %".29"), !dbg !268
  %".31" = load i32, i32* %"result.addr", !dbg !269
  %".32" = sext i32 %".31" to i64 , !dbg !269
  %".33" = icmp ne i64 %".32", 0 , !dbg !269
  br i1 %".33", label %"if.then.1", label %"if.end.1", !dbg !269
if.then.1:
  %".35" = load i32, i32* %"failed.addr", !dbg !270
  %".36" = sext i32 %".35" to i64 , !dbg !270
  %".37" = add i64 %".36", 1, !dbg !270
  %".38" = trunc i64 %".37" to i32 , !dbg !270
  store i32 %".38", i32* %"failed.addr", !dbg !270
  br label %"if.end.1", !dbg !270
if.end.1:
  %".41" = call i32 @"test_rect_area"(), !dbg !271
  store i32 %".41", i32* %"result.addr", !dbg !271
  %".43" = getelementptr [41 x i8], [41 x i8]* @".str.6", i64 0, i64 0 , !dbg !272
  %".44" = load i32, i32* %"result.addr", !dbg !272
  %".45" = call i32 @"print_result"(i8* %".43", i32 %".44"), !dbg !272
  %".46" = load i32, i32* %"result.addr", !dbg !273
  %".47" = sext i32 %".46" to i64 , !dbg !273
  %".48" = icmp ne i64 %".47", 0 , !dbg !273
  br i1 %".48", label %"if.then.2", label %"if.end.2", !dbg !273
if.then.2:
  %".50" = load i32, i32* %"failed.addr", !dbg !274
  %".51" = sext i32 %".50" to i64 , !dbg !274
  %".52" = add i64 %".51", 1, !dbg !274
  %".53" = trunc i64 %".52" to i32 , !dbg !274
  store i32 %".53", i32* %"failed.addr", !dbg !274
  br label %"if.end.2", !dbg !274
if.end.2:
  %".56" = call i32 @"test_rect_is_empty"(), !dbg !275
  store i32 %".56", i32* %"result.addr", !dbg !275
  %".58" = getelementptr [41 x i8], [41 x i8]* @".str.7", i64 0, i64 0 , !dbg !276
  %".59" = load i32, i32* %"result.addr", !dbg !276
  %".60" = call i32 @"print_result"(i8* %".58", i32 %".59"), !dbg !276
  %".61" = load i32, i32* %"result.addr", !dbg !277
  %".62" = sext i32 %".61" to i64 , !dbg !277
  %".63" = icmp ne i64 %".62", 0 , !dbg !277
  br i1 %".63", label %"if.then.3", label %"if.end.3", !dbg !277
if.then.3:
  %".65" = load i32, i32* %"failed.addr", !dbg !278
  %".66" = sext i32 %".65" to i64 , !dbg !278
  %".67" = add i64 %".66", 1, !dbg !278
  %".68" = trunc i64 %".67" to i32 , !dbg !278
  store i32 %".68", i32* %"failed.addr", !dbg !278
  br label %"if.end.3", !dbg !278
if.end.3:
  %".71" = call i32 @"test_rect_contains_point_inside"(), !dbg !279
  store i32 %".71", i32* %"result.addr", !dbg !279
  %".73" = getelementptr [41 x i8], [41 x i8]* @".str.8", i64 0, i64 0 , !dbg !280
  %".74" = load i32, i32* %"result.addr", !dbg !280
  %".75" = call i32 @"print_result"(i8* %".73", i32 %".74"), !dbg !280
  %".76" = load i32, i32* %"result.addr", !dbg !281
  %".77" = sext i32 %".76" to i64 , !dbg !281
  %".78" = icmp ne i64 %".77", 0 , !dbg !281
  br i1 %".78", label %"if.then.4", label %"if.end.4", !dbg !281
if.then.4:
  %".80" = load i32, i32* %"failed.addr", !dbg !282
  %".81" = sext i32 %".80" to i64 , !dbg !282
  %".82" = add i64 %".81", 1, !dbg !282
  %".83" = trunc i64 %".82" to i32 , !dbg !282
  store i32 %".83", i32* %"failed.addr", !dbg !282
  br label %"if.end.4", !dbg !282
if.end.4:
  %".86" = call i32 @"test_rect_contains_point_outside"(), !dbg !283
  store i32 %".86", i32* %"result.addr", !dbg !283
  %".88" = getelementptr [41 x i8], [41 x i8]* @".str.9", i64 0, i64 0 , !dbg !284
  %".89" = load i32, i32* %"result.addr", !dbg !284
  %".90" = call i32 @"print_result"(i8* %".88", i32 %".89"), !dbg !284
  %".91" = load i32, i32* %"result.addr", !dbg !285
  %".92" = sext i32 %".91" to i64 , !dbg !285
  %".93" = icmp ne i64 %".92", 0 , !dbg !285
  br i1 %".93", label %"if.then.5", label %"if.end.5", !dbg !285
if.then.5:
  %".95" = load i32, i32* %"failed.addr", !dbg !286
  %".96" = sext i32 %".95" to i64 , !dbg !286
  %".97" = add i64 %".96", 1, !dbg !286
  %".98" = trunc i64 %".97" to i32 , !dbg !286
  store i32 %".98", i32* %"failed.addr", !dbg !286
  br label %"if.end.5", !dbg !286
if.end.5:
  %".101" = call i32 @"test_rects_intersect_overlapping"(), !dbg !287
  store i32 %".101", i32* %"result.addr", !dbg !287
  %".103" = getelementptr [41 x i8], [41 x i8]* @".str.10", i64 0, i64 0 , !dbg !288
  %".104" = load i32, i32* %"result.addr", !dbg !288
  %".105" = call i32 @"print_result"(i8* %".103", i32 %".104"), !dbg !288
  %".106" = load i32, i32* %"result.addr", !dbg !289
  %".107" = sext i32 %".106" to i64 , !dbg !289
  %".108" = icmp ne i64 %".107", 0 , !dbg !289
  br i1 %".108", label %"if.then.6", label %"if.end.6", !dbg !289
if.then.6:
  %".110" = load i32, i32* %"failed.addr", !dbg !290
  %".111" = sext i32 %".110" to i64 , !dbg !290
  %".112" = add i64 %".111", 1, !dbg !290
  %".113" = trunc i64 %".112" to i32 , !dbg !290
  store i32 %".113", i32* %"failed.addr", !dbg !290
  br label %"if.end.6", !dbg !290
if.end.6:
  %".116" = call i32 @"test_rects_intersect_adjacent"(), !dbg !291
  store i32 %".116", i32* %"result.addr", !dbg !291
  %".118" = getelementptr [41 x i8], [41 x i8]* @".str.11", i64 0, i64 0 , !dbg !292
  %".119" = load i32, i32* %"result.addr", !dbg !292
  %".120" = call i32 @"print_result"(i8* %".118", i32 %".119"), !dbg !292
  %".121" = load i32, i32* %"result.addr", !dbg !293
  %".122" = sext i32 %".121" to i64 , !dbg !293
  %".123" = icmp ne i64 %".122", 0 , !dbg !293
  br i1 %".123", label %"if.then.7", label %"if.end.7", !dbg !293
if.then.7:
  %".125" = load i32, i32* %"failed.addr", !dbg !294
  %".126" = sext i32 %".125" to i64 , !dbg !294
  %".127" = add i64 %".126", 1, !dbg !294
  %".128" = trunc i64 %".127" to i32 , !dbg !294
  store i32 %".128", i32* %"failed.addr", !dbg !294
  br label %"if.end.7", !dbg !294
if.end.7:
  %".131" = call i32 @"test_rects_intersect_separate"(), !dbg !295
  store i32 %".131", i32* %"result.addr", !dbg !295
  %".133" = getelementptr [41 x i8], [41 x i8]* @".str.12", i64 0, i64 0 , !dbg !296
  %".134" = load i32, i32* %"result.addr", !dbg !296
  %".135" = call i32 @"print_result"(i8* %".133", i32 %".134"), !dbg !296
  %".136" = load i32, i32* %"result.addr", !dbg !297
  %".137" = sext i32 %".136" to i64 , !dbg !297
  %".138" = icmp ne i64 %".137", 0 , !dbg !297
  br i1 %".138", label %"if.then.8", label %"if.end.8", !dbg !297
if.then.8:
  %".140" = load i32, i32* %"failed.addr", !dbg !298
  %".141" = sext i32 %".140" to i64 , !dbg !298
  %".142" = add i64 %".141", 1, !dbg !298
  %".143" = trunc i64 %".142" to i32 , !dbg !298
  store i32 %".143", i32* %"failed.addr", !dbg !298
  br label %"if.end.8", !dbg !298
if.end.8:
  %".146" = call i32 @"test_rect_union_overlapping"(), !dbg !299
  store i32 %".146", i32* %"result.addr", !dbg !299
  %".148" = getelementptr [41 x i8], [41 x i8]* @".str.13", i64 0, i64 0 , !dbg !300
  %".149" = load i32, i32* %"result.addr", !dbg !300
  %".150" = call i32 @"print_result"(i8* %".148", i32 %".149"), !dbg !300
  %".151" = load i32, i32* %"result.addr", !dbg !301
  %".152" = sext i32 %".151" to i64 , !dbg !301
  %".153" = icmp ne i64 %".152", 0 , !dbg !301
  br i1 %".153", label %"if.then.9", label %"if.end.9", !dbg !301
if.then.9:
  %".155" = load i32, i32* %"failed.addr", !dbg !302
  %".156" = sext i32 %".155" to i64 , !dbg !302
  %".157" = add i64 %".156", 1, !dbg !302
  %".158" = trunc i64 %".157" to i32 , !dbg !302
  store i32 %".158", i32* %"failed.addr", !dbg !302
  br label %"if.end.9", !dbg !302
if.end.9:
  %".161" = call i32 @"test_rect_union_separate"(), !dbg !303
  store i32 %".161", i32* %"result.addr", !dbg !303
  %".163" = getelementptr [41 x i8], [41 x i8]* @".str.14", i64 0, i64 0 , !dbg !304
  %".164" = load i32, i32* %"result.addr", !dbg !304
  %".165" = call i32 @"print_result"(i8* %".163", i32 %".164"), !dbg !304
  %".166" = load i32, i32* %"result.addr", !dbg !305
  %".167" = sext i32 %".166" to i64 , !dbg !305
  %".168" = icmp ne i64 %".167", 0 , !dbg !305
  br i1 %".168", label %"if.then.10", label %"if.end.10", !dbg !305
if.then.10:
  %".170" = load i32, i32* %"failed.addr", !dbg !306
  %".171" = sext i32 %".170" to i64 , !dbg !306
  %".172" = add i64 %".171", 1, !dbg !306
  %".173" = trunc i64 %".172" to i32 , !dbg !306
  store i32 %".173", i32* %"failed.addr", !dbg !306
  br label %"if.end.10", !dbg !306
if.end.10:
  %".176" = call i32 @"test_rect_intersection_overlapping"(), !dbg !307
  store i32 %".176", i32* %"result.addr", !dbg !307
  %".178" = getelementptr [41 x i8], [41 x i8]* @".str.15", i64 0, i64 0 , !dbg !308
  %".179" = load i32, i32* %"result.addr", !dbg !308
  %".180" = call i32 @"print_result"(i8* %".178", i32 %".179"), !dbg !308
  %".181" = load i32, i32* %"result.addr", !dbg !309
  %".182" = sext i32 %".181" to i64 , !dbg !309
  %".183" = icmp ne i64 %".182", 0 , !dbg !309
  br i1 %".183", label %"if.then.11", label %"if.end.11", !dbg !309
if.then.11:
  %".185" = load i32, i32* %"failed.addr", !dbg !310
  %".186" = sext i32 %".185" to i64 , !dbg !310
  %".187" = add i64 %".186", 1, !dbg !310
  %".188" = trunc i64 %".187" to i32 , !dbg !310
  store i32 %".188", i32* %"failed.addr", !dbg !310
  br label %"if.end.11", !dbg !310
if.end.11:
  %".191" = call i32 @"test_rect_intersection_no_overlap"(), !dbg !311
  store i32 %".191", i32* %"result.addr", !dbg !311
  %".193" = getelementptr [41 x i8], [41 x i8]* @".str.16", i64 0, i64 0 , !dbg !312
  %".194" = load i32, i32* %"result.addr", !dbg !312
  %".195" = call i32 @"print_result"(i8* %".193", i32 %".194"), !dbg !312
  %".196" = load i32, i32* %"result.addr", !dbg !313
  %".197" = sext i32 %".196" to i64 , !dbg !313
  %".198" = icmp ne i64 %".197", 0 , !dbg !313
  br i1 %".198", label %"if.then.12", label %"if.end.12", !dbg !313
if.then.12:
  %".200" = load i32, i32* %"failed.addr", !dbg !314
  %".201" = sext i32 %".200" to i64 , !dbg !314
  %".202" = add i64 %".201", 1, !dbg !314
  %".203" = trunc i64 %".202" to i32 , !dbg !314
  store i32 %".203", i32* %"failed.addr", !dbg !314
  br label %"if.end.12", !dbg !314
if.end.12:
  %".206" = call i32 @"test_damage_region_new_empty"(), !dbg !315
  store i32 %".206", i32* %"result.addr", !dbg !315
  %".208" = getelementptr [41 x i8], [41 x i8]* @".str.17", i64 0, i64 0 , !dbg !316
  %".209" = load i32, i32* %"result.addr", !dbg !316
  %".210" = call i32 @"print_result"(i8* %".208", i32 %".209"), !dbg !316
  %".211" = load i32, i32* %"result.addr", !dbg !317
  %".212" = sext i32 %".211" to i64 , !dbg !317
  %".213" = icmp ne i64 %".212", 0 , !dbg !317
  br i1 %".213", label %"if.then.13", label %"if.end.13", !dbg !317
if.then.13:
  %".215" = load i32, i32* %"failed.addr", !dbg !318
  %".216" = sext i32 %".215" to i64 , !dbg !318
  %".217" = add i64 %".216", 1, !dbg !318
  %".218" = trunc i64 %".217" to i32 , !dbg !318
  store i32 %".218", i32* %"failed.addr", !dbg !318
  br label %"if.end.13", !dbg !318
if.end.13:
  %".221" = call i32 @"test_damage_region_add_single"(), !dbg !319
  store i32 %".221", i32* %"result.addr", !dbg !319
  %".223" = getelementptr [41 x i8], [41 x i8]* @".str.18", i64 0, i64 0 , !dbg !320
  %".224" = load i32, i32* %"result.addr", !dbg !320
  %".225" = call i32 @"print_result"(i8* %".223", i32 %".224"), !dbg !320
  %".226" = load i32, i32* %"result.addr", !dbg !321
  %".227" = sext i32 %".226" to i64 , !dbg !321
  %".228" = icmp ne i64 %".227", 0 , !dbg !321
  br i1 %".228", label %"if.then.14", label %"if.end.14", !dbg !321
if.then.14:
  %".230" = load i32, i32* %"failed.addr", !dbg !322
  %".231" = sext i32 %".230" to i64 , !dbg !322
  %".232" = add i64 %".231", 1, !dbg !322
  %".233" = trunc i64 %".232" to i32 , !dbg !322
  store i32 %".233", i32* %"failed.addr", !dbg !322
  br label %"if.end.14", !dbg !322
if.end.14:
  %".236" = call i32 @"test_damage_region_add_multiple"(), !dbg !323
  store i32 %".236", i32* %"result.addr", !dbg !323
  %".238" = getelementptr [41 x i8], [41 x i8]* @".str.19", i64 0, i64 0 , !dbg !324
  %".239" = load i32, i32* %"result.addr", !dbg !324
  %".240" = call i32 @"print_result"(i8* %".238", i32 %".239"), !dbg !324
  %".241" = load i32, i32* %"result.addr", !dbg !325
  %".242" = sext i32 %".241" to i64 , !dbg !325
  %".243" = icmp ne i64 %".242", 0 , !dbg !325
  br i1 %".243", label %"if.then.15", label %"if.end.15", !dbg !325
if.then.15:
  %".245" = load i32, i32* %"failed.addr", !dbg !326
  %".246" = sext i32 %".245" to i64 , !dbg !326
  %".247" = add i64 %".246", 1, !dbg !326
  %".248" = trunc i64 %".247" to i32 , !dbg !326
  store i32 %".248", i32* %"failed.addr", !dbg !326
  br label %"if.end.15", !dbg !326
if.end.15:
  %".251" = call i32 @"test_damage_region_clear_removes_all"(), !dbg !327
  store i32 %".251", i32* %"result.addr", !dbg !327
  %".253" = getelementptr [41 x i8], [41 x i8]* @".str.20", i64 0, i64 0 , !dbg !328
  %".254" = load i32, i32* %"result.addr", !dbg !328
  %".255" = call i32 @"print_result"(i8* %".253", i32 %".254"), !dbg !328
  %".256" = load i32, i32* %"result.addr", !dbg !329
  %".257" = sext i32 %".256" to i64 , !dbg !329
  %".258" = icmp ne i64 %".257", 0 , !dbg !329
  br i1 %".258", label %"if.then.16", label %"if.end.16", !dbg !329
if.then.16:
  %".260" = load i32, i32* %"failed.addr", !dbg !330
  %".261" = sext i32 %".260" to i64 , !dbg !330
  %".262" = add i64 %".261", 1, !dbg !330
  %".263" = trunc i64 %".262" to i32 , !dbg !330
  store i32 %".263", i32* %"failed.addr", !dbg !330
  br label %"if.end.16", !dbg !330
if.end.16:
  %".266" = call i32 @"test_damage_region_bounds_single"(), !dbg !331
  store i32 %".266", i32* %"result.addr", !dbg !331
  %".268" = getelementptr [41 x i8], [41 x i8]* @".str.21", i64 0, i64 0 , !dbg !332
  %".269" = load i32, i32* %"result.addr", !dbg !332
  %".270" = call i32 @"print_result"(i8* %".268", i32 %".269"), !dbg !332
  %".271" = load i32, i32* %"result.addr", !dbg !333
  %".272" = sext i32 %".271" to i64 , !dbg !333
  %".273" = icmp ne i64 %".272", 0 , !dbg !333
  br i1 %".273", label %"if.then.17", label %"if.end.17", !dbg !333
if.then.17:
  %".275" = load i32, i32* %"failed.addr", !dbg !334
  %".276" = sext i32 %".275" to i64 , !dbg !334
  %".277" = add i64 %".276", 1, !dbg !334
  %".278" = trunc i64 %".277" to i32 , !dbg !334
  store i32 %".278", i32* %"failed.addr", !dbg !334
  br label %"if.end.17", !dbg !334
if.end.17:
  %".281" = call i32 @"test_damage_region_bounds_multiple"(), !dbg !335
  store i32 %".281", i32* %"result.addr", !dbg !335
  %".283" = getelementptr [41 x i8], [41 x i8]* @".str.22", i64 0, i64 0 , !dbg !336
  %".284" = load i32, i32* %"result.addr", !dbg !336
  %".285" = call i32 @"print_result"(i8* %".283", i32 %".284"), !dbg !336
  %".286" = load i32, i32* %"result.addr", !dbg !337
  %".287" = sext i32 %".286" to i64 , !dbg !337
  %".288" = icmp ne i64 %".287", 0 , !dbg !337
  br i1 %".288", label %"if.then.18", label %"if.end.18", !dbg !337
if.then.18:
  %".290" = load i32, i32* %"failed.addr", !dbg !338
  %".291" = sext i32 %".290" to i64 , !dbg !338
  %".292" = add i64 %".291", 1, !dbg !338
  %".293" = trunc i64 %".292" to i32 , !dbg !338
  store i32 %".293", i32* %"failed.addr", !dbg !338
  br label %"if.end.18", !dbg !338
if.end.18:
  %".296" = call i32 @"test_damage_region_bounds_empty"(), !dbg !339
  store i32 %".296", i32* %"result.addr", !dbg !339
  %".298" = getelementptr [41 x i8], [41 x i8]* @".str.23", i64 0, i64 0 , !dbg !340
  %".299" = load i32, i32* %"result.addr", !dbg !340
  %".300" = call i32 @"print_result"(i8* %".298", i32 %".299"), !dbg !340
  %".301" = load i32, i32* %"result.addr", !dbg !341
  %".302" = sext i32 %".301" to i64 , !dbg !341
  %".303" = icmp ne i64 %".302", 0 , !dbg !341
  br i1 %".303", label %"if.then.19", label %"if.end.19", !dbg !341
if.then.19:
  %".305" = load i32, i32* %"failed.addr", !dbg !342
  %".306" = sext i32 %".305" to i64 , !dbg !342
  %".307" = add i64 %".306", 1, !dbg !342
  %".308" = trunc i64 %".307" to i32 , !dbg !342
  store i32 %".308", i32* %"failed.addr", !dbg !342
  br label %"if.end.19", !dbg !342
if.end.19:
  %".311" = trunc i64 1 to i32 , !dbg !343
  %".312" = getelementptr [49 x i8], [49 x i8]* @".str.24", i64 0, i64 0 , !dbg !343
  %".313" = call i64 @"sys_write"(i32 %".311", i8* %".312", i64 48), !dbg !343
  %".314" = load i32, i32* %"failed.addr", !dbg !344
  %".315" = sext i32 %".314" to i64 , !dbg !344
  %".316" = icmp eq i64 %".315", 0 , !dbg !344
  br i1 %".316", label %"if.then.20", label %"if.else", !dbg !344
if.then.20:
  %".318" = trunc i64 1 to i32 , !dbg !344
  %".319" = getelementptr [20 x i8], [20 x i8]* @".str.25", i64 0, i64 0 , !dbg !344
  %".320" = call i64 @"sys_write"(i32 %".318", i8* %".319", i64 19), !dbg !344
  br label %"if.end.20", !dbg !344
if.else:
  %".321" = trunc i64 1 to i32 , !dbg !344
  %".322" = getelementptr [21 x i8], [21 x i8]* @".str.26", i64 0, i64 0 , !dbg !344
  %".323" = call i64 @"sys_write"(i32 %".321", i8* %".322", i64 20), !dbg !344
  br label %"if.end.20", !dbg !344
if.end.20:
  %".326" = phi  i64 [%".320", %"if.then.20"], [%".323", %"if.else"] , !dbg !344
  %".327" = load i32, i32* %"failed.addr", !dbg !345
  ret i32 %".327", !dbg !345
}

@".str.0" = private constant [7 x i8] c" PASS\0a\00"
@".str.1" = private constant [8 x i8] c" FAIL (\00"
@".str.2" = private constant [3 x i8] c")\0a\00"
@".str.3" = private constant [33 x i8] c"\0a=== Damage Tracking Tests ===\0a\0a\00"
@".str.4" = private constant [41 x i8] c"test_rect_new                           \00"
@".str.5" = private constant [41 x i8] c"test_rect_zero                          \00"
@".str.6" = private constant [41 x i8] c"test_rect_area                          \00"
@".str.7" = private constant [41 x i8] c"test_rect_is_empty                      \00"
@".str.8" = private constant [41 x i8] c"test_rect_contains_point_inside         \00"
@".str.9" = private constant [41 x i8] c"test_rect_contains_point_outside        \00"
@".str.10" = private constant [41 x i8] c"test_rects_intersect_overlapping        \00"
@".str.11" = private constant [41 x i8] c"test_rects_intersect_adjacent           \00"
@".str.12" = private constant [41 x i8] c"test_rects_intersect_separate           \00"
@".str.13" = private constant [41 x i8] c"test_rect_union_overlapping             \00"
@".str.14" = private constant [41 x i8] c"test_rect_union_separate                \00"
@".str.15" = private constant [41 x i8] c"test_rect_intersection_overlapping      \00"
@".str.16" = private constant [41 x i8] c"test_rect_intersection_no_overlap       \00"
@".str.17" = private constant [41 x i8] c"test_damage_region_new_empty            \00"
@".str.18" = private constant [41 x i8] c"test_damage_region_add_single           \00"
@".str.19" = private constant [41 x i8] c"test_damage_region_add_multiple         \00"
@".str.20" = private constant [41 x i8] c"test_damage_region_clear_removes_all    \00"
@".str.21" = private constant [41 x i8] c"test_damage_region_bounds_single        \00"
@".str.22" = private constant [41 x i8] c"test_damage_region_bounds_multiple      \00"
@".str.23" = private constant [41 x i8] c"test_damage_region_bounds_empty         \00"
@".str.24" = private constant [49 x i8] c"\0a----------------------------------------------\0a\00"
@".str.25" = private constant [20 x i8] c"All tests passed!\0a\0a\00"
@".str.26" = private constant [21 x i8] c"Some tests failed!\0a\0a\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/prism/test", filename: "test_damage.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 13, name: "test_rect_new", scopeLine: 13, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 25, name: "test_rect_zero", scopeLine: 25, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 37, name: "test_rect_area", scopeLine: 37, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 47, name: "test_rect_is_empty", scopeLine: 47, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 61, name: "test_rect_contains_point_inside", scopeLine: 61, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 77, name: "test_rect_contains_point_outside", scopeLine: 77, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 97, name: "test_rects_intersect_overlapping", scopeLine: 97, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 107, name: "test_rects_intersect_adjacent", scopeLine: 107, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "test_rects_intersect_separate", scopeLine: 116, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "test_rect_union_overlapping", scopeLine: 124, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 140, name: "test_rect_union_separate", scopeLine: 140, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 156, name: "test_rect_intersection_overlapping", scopeLine: 156, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 172, name: "test_rect_intersection_no_overlap", scopeLine: 172, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 186, name: "test_damage_region_new_empty", scopeLine: 186, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 195, name: "test_damage_region_add_single", scopeLine: 195, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "test_damage_region_add_multiple", scopeLine: 210, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 222, name: "test_damage_region_clear_removes_all", scopeLine: 222, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 237, name: "test_damage_region_bounds_single", scopeLine: 237, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 254, name: "test_damage_region_bounds_multiple", scopeLine: 254, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 273, name: "test_damage_region_bounds_empty", scopeLine: 273, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 285, name: "print_result", scopeLine: 285, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 312, name: "main", scopeLine: 312, type: !4, unit: !1)
!39 = !DILocation(column: 5, line: 14, scope: !17)
!40 = !DILocation(column: 5, line: 15, scope: !17)
!41 = !DILocation(column: 9, line: 16, scope: !17)
!42 = !DILocation(column: 5, line: 17, scope: !17)
!43 = !DILocation(column: 9, line: 18, scope: !17)
!44 = !DILocation(column: 5, line: 19, scope: !17)
!45 = !DILocation(column: 9, line: 20, scope: !17)
!46 = !DILocation(column: 5, line: 21, scope: !17)
!47 = !DILocation(column: 9, line: 22, scope: !17)
!48 = !DILocation(column: 5, line: 23, scope: !17)
!49 = !DILocation(column: 5, line: 26, scope: !18)
!50 = !DILocation(column: 5, line: 27, scope: !18)
!51 = !DILocation(column: 9, line: 28, scope: !18)
!52 = !DILocation(column: 5, line: 29, scope: !18)
!53 = !DILocation(column: 9, line: 30, scope: !18)
!54 = !DILocation(column: 5, line: 31, scope: !18)
!55 = !DILocation(column: 9, line: 32, scope: !18)
!56 = !DILocation(column: 5, line: 33, scope: !18)
!57 = !DILocation(column: 9, line: 34, scope: !18)
!58 = !DILocation(column: 5, line: 35, scope: !18)
!59 = !DILocation(column: 5, line: 38, scope: !19)
!60 = !DILocation(column: 5, line: 39, scope: !19)
!61 = !DILocation(column: 9, line: 40, scope: !19)
!62 = !DILocation(column: 5, line: 42, scope: !19)
!63 = !DILocation(column: 5, line: 43, scope: !19)
!64 = !DILocation(column: 9, line: 44, scope: !19)
!65 = !DILocation(column: 5, line: 45, scope: !19)
!66 = !DILocation(column: 5, line: 48, scope: !20)
!67 = !DILocation(column: 5, line: 49, scope: !20)
!68 = !DILocation(column: 9, line: 50, scope: !20)
!69 = !DILocation(column: 5, line: 52, scope: !20)
!70 = !DILocation(column: 5, line: 53, scope: !20)
!71 = !DILocation(column: 9, line: 54, scope: !20)
!72 = !DILocation(column: 5, line: 56, scope: !20)
!73 = !DILocation(column: 5, line: 57, scope: !20)
!74 = !DILocation(column: 9, line: 58, scope: !20)
!75 = !DILocation(column: 5, line: 59, scope: !20)
!76 = !DILocation(column: 5, line: 62, scope: !21)
!77 = !DILocation(column: 5, line: 65, scope: !21)
!78 = !DILocation(column: 9, line: 66, scope: !21)
!79 = !DILocation(column: 5, line: 69, scope: !21)
!80 = !DILocation(column: 9, line: 70, scope: !21)
!81 = !DILocation(column: 5, line: 73, scope: !21)
!82 = !DILocation(column: 9, line: 74, scope: !21)
!83 = !DILocation(column: 5, line: 75, scope: !21)
!84 = !DILocation(column: 5, line: 78, scope: !22)
!85 = !DILocation(column: 5, line: 81, scope: !22)
!86 = !DILocation(column: 9, line: 82, scope: !22)
!87 = !DILocation(column: 5, line: 85, scope: !22)
!88 = !DILocation(column: 9, line: 86, scope: !22)
!89 = !DILocation(column: 5, line: 89, scope: !22)
!90 = !DILocation(column: 9, line: 90, scope: !22)
!91 = !DILocation(column: 5, line: 93, scope: !22)
!92 = !DILocation(column: 9, line: 94, scope: !22)
!93 = !DILocation(column: 5, line: 95, scope: !22)
!94 = !DILocation(column: 5, line: 98, scope: !23)
!95 = !DILocation(column: 5, line: 99, scope: !23)
!96 = !DILocation(column: 5, line: 101, scope: !23)
!97 = !DILocation(column: 9, line: 102, scope: !23)
!98 = !DILocation(column: 5, line: 103, scope: !23)
!99 = !DILocation(column: 9, line: 104, scope: !23)
!100 = !DILocation(column: 5, line: 105, scope: !23)
!101 = !DILocation(column: 5, line: 108, scope: !24)
!102 = !DILocation(column: 5, line: 109, scope: !24)
!103 = !DILocation(column: 5, line: 112, scope: !24)
!104 = !DILocation(column: 9, line: 113, scope: !24)
!105 = !DILocation(column: 5, line: 114, scope: !24)
!106 = !DILocation(column: 5, line: 117, scope: !25)
!107 = !DILocation(column: 5, line: 118, scope: !25)
!108 = !DILocation(column: 5, line: 120, scope: !25)
!109 = !DILocation(column: 9, line: 121, scope: !25)
!110 = !DILocation(column: 5, line: 122, scope: !25)
!111 = !DILocation(column: 5, line: 125, scope: !26)
!112 = !DILocation(column: 5, line: 126, scope: !26)
!113 = !DILocation(column: 5, line: 128, scope: !26)
!114 = !DILocation(column: 5, line: 130, scope: !26)
!115 = !DILocation(column: 9, line: 131, scope: !26)
!116 = !DILocation(column: 5, line: 132, scope: !26)
!117 = !DILocation(column: 9, line: 133, scope: !26)
!118 = !DILocation(column: 5, line: 134, scope: !26)
!119 = !DILocation(column: 9, line: 135, scope: !26)
!120 = !DILocation(column: 5, line: 136, scope: !26)
!121 = !DILocation(column: 9, line: 137, scope: !26)
!122 = !DILocation(column: 5, line: 138, scope: !26)
!123 = !DILocation(column: 5, line: 141, scope: !27)
!124 = !DILocation(column: 5, line: 142, scope: !27)
!125 = !DILocation(column: 5, line: 144, scope: !27)
!126 = !DILocation(column: 5, line: 146, scope: !27)
!127 = !DILocation(column: 9, line: 147, scope: !27)
!128 = !DILocation(column: 5, line: 148, scope: !27)
!129 = !DILocation(column: 9, line: 149, scope: !27)
!130 = !DILocation(column: 5, line: 150, scope: !27)
!131 = !DILocation(column: 9, line: 151, scope: !27)
!132 = !DILocation(column: 5, line: 152, scope: !27)
!133 = !DILocation(column: 9, line: 153, scope: !27)
!134 = !DILocation(column: 5, line: 154, scope: !27)
!135 = !DILocation(column: 5, line: 157, scope: !28)
!136 = !DILocation(column: 5, line: 158, scope: !28)
!137 = !DILocation(column: 5, line: 160, scope: !28)
!138 = !DILocation(column: 5, line: 162, scope: !28)
!139 = !DILocation(column: 9, line: 163, scope: !28)
!140 = !DILocation(column: 5, line: 164, scope: !28)
!141 = !DILocation(column: 9, line: 165, scope: !28)
!142 = !DILocation(column: 5, line: 166, scope: !28)
!143 = !DILocation(column: 9, line: 167, scope: !28)
!144 = !DILocation(column: 5, line: 168, scope: !28)
!145 = !DILocation(column: 9, line: 169, scope: !28)
!146 = !DILocation(column: 5, line: 170, scope: !28)
!147 = !DILocation(column: 5, line: 173, scope: !29)
!148 = !DILocation(column: 5, line: 174, scope: !29)
!149 = !DILocation(column: 5, line: 176, scope: !29)
!150 = !DILocation(column: 5, line: 178, scope: !29)
!151 = !DILocation(column: 9, line: 179, scope: !29)
!152 = !DILocation(column: 5, line: 180, scope: !29)
!153 = !DILocation(column: 5, line: 187, scope: !30)
!154 = !DILocation(column: 5, line: 189, scope: !30)
!155 = !DILocation(column: 9, line: 190, scope: !30)
!156 = !DILocation(column: 5, line: 191, scope: !30)
!157 = !DILocation(column: 9, line: 192, scope: !30)
!158 = !DILocation(column: 5, line: 193, scope: !30)
!159 = !DILocation(column: 5, line: 196, scope: !31)
!160 = !DILocation(column: 5, line: 197, scope: !31)
!161 = !DILocation(column: 5, line: 199, scope: !31)
!162 = !DILocation(column: 5, line: 200, scope: !31)
!163 = !DILocation(column: 5, line: 202, scope: !31)
!164 = !DILocation(column: 9, line: 203, scope: !31)
!165 = !DILocation(column: 5, line: 204, scope: !31)
!166 = !DILocation(column: 9, line: 205, scope: !31)
!167 = !DILocation(column: 5, line: 206, scope: !31)
!168 = !DILocation(column: 9, line: 207, scope: !31)
!169 = !DILocation(column: 5, line: 208, scope: !31)
!170 = !DILocation(column: 5, line: 211, scope: !32)
!171 = !DILocation(column: 5, line: 213, scope: !32)
!172 = !DILocation(column: 5, line: 214, scope: !32)
!173 = !DILocation(column: 5, line: 215, scope: !32)
!174 = !DILocation(column: 5, line: 216, scope: !32)
!175 = !DILocation(column: 5, line: 218, scope: !32)
!176 = !DILocation(column: 9, line: 219, scope: !32)
!177 = !DILocation(column: 5, line: 220, scope: !32)
!178 = !DILocation(column: 5, line: 223, scope: !33)
!179 = !DILocation(column: 5, line: 225, scope: !33)
!180 = !DILocation(column: 5, line: 226, scope: !33)
!181 = !DILocation(column: 5, line: 227, scope: !33)
!182 = !DILocation(column: 5, line: 229, scope: !33)
!183 = !DILocation(column: 5, line: 231, scope: !33)
!184 = !DILocation(column: 9, line: 232, scope: !33)
!185 = !DILocation(column: 5, line: 233, scope: !33)
!186 = !DILocation(column: 9, line: 234, scope: !33)
!187 = !DILocation(column: 5, line: 235, scope: !33)
!188 = !DILocation(column: 5, line: 238, scope: !34)
!189 = !DILocation(column: 5, line: 239, scope: !34)
!190 = !DILocation(column: 5, line: 240, scope: !34)
!191 = !DILocation(column: 5, line: 242, scope: !34)
!192 = !DILocation(column: 5, line: 244, scope: !34)
!193 = !DILocation(column: 9, line: 245, scope: !34)
!194 = !DILocation(column: 5, line: 246, scope: !34)
!195 = !DILocation(column: 9, line: 247, scope: !34)
!196 = !DILocation(column: 5, line: 248, scope: !34)
!197 = !DILocation(column: 9, line: 249, scope: !34)
!198 = !DILocation(column: 5, line: 250, scope: !34)
!199 = !DILocation(column: 9, line: 251, scope: !34)
!200 = !DILocation(column: 5, line: 252, scope: !34)
!201 = !DILocation(column: 5, line: 255, scope: !35)
!202 = !DILocation(column: 5, line: 256, scope: !35)
!203 = !DILocation(column: 5, line: 257, scope: !35)
!204 = !DILocation(column: 5, line: 258, scope: !35)
!205 = !DILocation(column: 5, line: 260, scope: !35)
!206 = !DILocation(column: 5, line: 263, scope: !35)
!207 = !DILocation(column: 9, line: 264, scope: !35)
!208 = !DILocation(column: 5, line: 265, scope: !35)
!209 = !DILocation(column: 9, line: 266, scope: !35)
!210 = !DILocation(column: 5, line: 267, scope: !35)
!211 = !DILocation(column: 9, line: 268, scope: !35)
!212 = !DILocation(column: 5, line: 269, scope: !35)
!213 = !DILocation(column: 9, line: 270, scope: !35)
!214 = !DILocation(column: 5, line: 271, scope: !35)
!215 = !DILocation(column: 5, line: 274, scope: !36)
!216 = !DILocation(column: 5, line: 275, scope: !36)
!217 = !DILocation(column: 5, line: 277, scope: !36)
!218 = !DILocation(column: 9, line: 278, scope: !36)
!219 = !DILocation(column: 5, line: 279, scope: !36)
!220 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!221 = !DILocalVariable(file: !0, line: 285, name: "name", scope: !37, type: !220)
!222 = !DILocation(column: 1, line: 285, scope: !37)
!223 = !DILocalVariable(file: !0, line: 285, name: "result", scope: !37, type: !10)
!224 = !DILocation(column: 5, line: 286, scope: !37)
!225 = !DILocation(column: 9, line: 287, scope: !37)
!226 = !DILocation(column: 9, line: 290, scope: !37)
!227 = !DILocation(column: 9, line: 291, scope: !37)
!228 = !DILocation(column: 9, line: 292, scope: !37)
!229 = !DISubrange(count: 10)
!230 = !{ !229 }
!231 = !DICompositeType(baseType: !12, elements: !230, size: 80, tag: DW_TAG_array_type)
!232 = !DILocalVariable(file: !0, line: 292, name: "buf", scope: !37, type: !231)
!233 = !DILocation(column: 1, line: 292, scope: !37)
!234 = !DILocation(column: 9, line: 293, scope: !37)
!235 = !DILocalVariable(file: !0, line: 293, name: "n", scope: !37, type: !10)
!236 = !DILocation(column: 1, line: 293, scope: !37)
!237 = !DILocation(column: 9, line: 294, scope: !37)
!238 = !DILocalVariable(file: !0, line: 294, name: "i", scope: !37, type: !11)
!239 = !DILocation(column: 1, line: 294, scope: !37)
!240 = !DILocation(column: 9, line: 295, scope: !37)
!241 = !DILocation(column: 13, line: 296, scope: !37)
!242 = !DILocation(column: 13, line: 297, scope: !37)
!243 = !DILocation(column: 13, line: 299, scope: !37)
!244 = !DILocation(column: 17, line: 300, scope: !37)
!245 = !DILocation(column: 17, line: 301, scope: !37)
!246 = !DILocation(column: 17, line: 302, scope: !37)
!247 = !DILocation(column: 13, line: 303, scope: !37)
!248 = !DILocalVariable(file: !0, line: 303, name: "j", scope: !37, type: !11)
!249 = !DILocation(column: 1, line: 303, scope: !37)
!250 = !DILocation(column: 13, line: 304, scope: !37)
!251 = !DILocation(column: 17, line: 305, scope: !37)
!252 = !DILocation(column: 17, line: 306, scope: !37)
!253 = !DILocation(column: 17, line: 307, scope: !37)
!254 = !DILocation(column: 17, line: 308, scope: !37)
!255 = !DILocation(column: 9, line: 309, scope: !37)
!256 = !DILocation(column: 5, line: 313, scope: !38)
!257 = !DILocalVariable(file: !0, line: 313, name: "failed", scope: !38, type: !10)
!258 = !DILocation(column: 1, line: 313, scope: !38)
!259 = !DILocation(column: 5, line: 314, scope: !38)
!260 = !DILocalVariable(file: !0, line: 314, name: "result", scope: !38, type: !10)
!261 = !DILocation(column: 1, line: 314, scope: !38)
!262 = !DILocation(column: 5, line: 316, scope: !38)
!263 = !DILocation(column: 5, line: 319, scope: !38)
!264 = !DILocation(column: 5, line: 320, scope: !38)
!265 = !DILocation(column: 5, line: 321, scope: !38)
!266 = !DILocation(column: 9, line: 322, scope: !38)
!267 = !DILocation(column: 5, line: 324, scope: !38)
!268 = !DILocation(column: 5, line: 325, scope: !38)
!269 = !DILocation(column: 5, line: 326, scope: !38)
!270 = !DILocation(column: 9, line: 327, scope: !38)
!271 = !DILocation(column: 5, line: 329, scope: !38)
!272 = !DILocation(column: 5, line: 330, scope: !38)
!273 = !DILocation(column: 5, line: 331, scope: !38)
!274 = !DILocation(column: 9, line: 332, scope: !38)
!275 = !DILocation(column: 5, line: 334, scope: !38)
!276 = !DILocation(column: 5, line: 335, scope: !38)
!277 = !DILocation(column: 5, line: 336, scope: !38)
!278 = !DILocation(column: 9, line: 337, scope: !38)
!279 = !DILocation(column: 5, line: 339, scope: !38)
!280 = !DILocation(column: 5, line: 340, scope: !38)
!281 = !DILocation(column: 5, line: 341, scope: !38)
!282 = !DILocation(column: 9, line: 342, scope: !38)
!283 = !DILocation(column: 5, line: 344, scope: !38)
!284 = !DILocation(column: 5, line: 345, scope: !38)
!285 = !DILocation(column: 5, line: 346, scope: !38)
!286 = !DILocation(column: 9, line: 347, scope: !38)
!287 = !DILocation(column: 5, line: 349, scope: !38)
!288 = !DILocation(column: 5, line: 350, scope: !38)
!289 = !DILocation(column: 5, line: 351, scope: !38)
!290 = !DILocation(column: 9, line: 352, scope: !38)
!291 = !DILocation(column: 5, line: 354, scope: !38)
!292 = !DILocation(column: 5, line: 355, scope: !38)
!293 = !DILocation(column: 5, line: 356, scope: !38)
!294 = !DILocation(column: 9, line: 357, scope: !38)
!295 = !DILocation(column: 5, line: 359, scope: !38)
!296 = !DILocation(column: 5, line: 360, scope: !38)
!297 = !DILocation(column: 5, line: 361, scope: !38)
!298 = !DILocation(column: 9, line: 362, scope: !38)
!299 = !DILocation(column: 5, line: 364, scope: !38)
!300 = !DILocation(column: 5, line: 365, scope: !38)
!301 = !DILocation(column: 5, line: 366, scope: !38)
!302 = !DILocation(column: 9, line: 367, scope: !38)
!303 = !DILocation(column: 5, line: 369, scope: !38)
!304 = !DILocation(column: 5, line: 370, scope: !38)
!305 = !DILocation(column: 5, line: 371, scope: !38)
!306 = !DILocation(column: 9, line: 372, scope: !38)
!307 = !DILocation(column: 5, line: 374, scope: !38)
!308 = !DILocation(column: 5, line: 375, scope: !38)
!309 = !DILocation(column: 5, line: 376, scope: !38)
!310 = !DILocation(column: 9, line: 377, scope: !38)
!311 = !DILocation(column: 5, line: 379, scope: !38)
!312 = !DILocation(column: 5, line: 380, scope: !38)
!313 = !DILocation(column: 5, line: 381, scope: !38)
!314 = !DILocation(column: 9, line: 382, scope: !38)
!315 = !DILocation(column: 5, line: 385, scope: !38)
!316 = !DILocation(column: 5, line: 386, scope: !38)
!317 = !DILocation(column: 5, line: 387, scope: !38)
!318 = !DILocation(column: 9, line: 388, scope: !38)
!319 = !DILocation(column: 5, line: 390, scope: !38)
!320 = !DILocation(column: 5, line: 391, scope: !38)
!321 = !DILocation(column: 5, line: 392, scope: !38)
!322 = !DILocation(column: 9, line: 393, scope: !38)
!323 = !DILocation(column: 5, line: 395, scope: !38)
!324 = !DILocation(column: 5, line: 396, scope: !38)
!325 = !DILocation(column: 5, line: 397, scope: !38)
!326 = !DILocation(column: 9, line: 398, scope: !38)
!327 = !DILocation(column: 5, line: 400, scope: !38)
!328 = !DILocation(column: 5, line: 401, scope: !38)
!329 = !DILocation(column: 5, line: 402, scope: !38)
!330 = !DILocation(column: 9, line: 403, scope: !38)
!331 = !DILocation(column: 5, line: 405, scope: !38)
!332 = !DILocation(column: 5, line: 406, scope: !38)
!333 = !DILocation(column: 5, line: 407, scope: !38)
!334 = !DILocation(column: 9, line: 408, scope: !38)
!335 = !DILocation(column: 5, line: 410, scope: !38)
!336 = !DILocation(column: 5, line: 411, scope: !38)
!337 = !DILocation(column: 5, line: 412, scope: !38)
!338 = !DILocation(column: 9, line: 413, scope: !38)
!339 = !DILocation(column: 5, line: 415, scope: !38)
!340 = !DILocation(column: 5, line: 416, scope: !38)
!341 = !DILocation(column: 5, line: 417, scope: !38)
!342 = !DILocation(column: 9, line: 418, scope: !38)
!343 = !DILocation(column: 5, line: 420, scope: !38)
!344 = !DILocation(column: 5, line: 421, scope: !38)
!345 = !DILocation(column: 5, line: 426, scope: !38)