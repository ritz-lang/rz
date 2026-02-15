; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Stat" = type {i64, i64, i64, i32, i32, i32, i32, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64}
%"struct.ritz_module_1.Dirent64" = type {i64, i64, i16, i8}
%"struct.ritz_module_1.Timeval" = type {i64, i64}
%"struct.ritz_module_1.NodeId" = type {i64}
%"struct.ritz_module_1.Dimension" = type {double, i32}
%"struct.ritz_module_1.EdgeSizes" = type {%"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"}
%"struct.ritz_module_1.Color" = type {i8, i8, i8, i8}
%"struct.ritz_module_1.BorderEdge" = type {double, i32, %"struct.ritz_module_1.Color"}
%"struct.ritz_module_1.Border" = type {%"struct.ritz_module_1.BorderEdge", %"struct.ritz_module_1.BorderEdge", %"struct.ritz_module_1.BorderEdge", %"struct.ritz_module_1.BorderEdge"}
%"struct.ritz_module_1.TextStyle" = type {double, i32, i32, double, double, i32, %"struct.ritz_module_1.Color"}
%"struct.ritz_module_1.FlexStyle" = type {i32, i32, i32, double, double, %"struct.ritz_module_1.Dimension", i32}
%"struct.ritz_module_1.Transform" = type {double, double, double, double, double, double}
%"struct.ritz_module_1.ComputedStyle" = type {i32, i32, i32, i32, i32, i32, i32, %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.EdgeSizes", %"struct.ritz_module_1.EdgeSizes", %"struct.ritz_module_1.Border", %"struct.ritz_module_1.TextStyle", %"struct.ritz_module_1.FlexStyle", %"struct.ritz_module_1.Color", double, %"struct.ritz_module_1.Transform"}
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

define %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 %"value.arg") !dbg !17
{
entry:
  %"value" = alloca i64
  store i64 %"value.arg", i64* %"value"
  call void @"llvm.dbg.declare"(metadata i64* %"value", metadata !43, metadata !7), !dbg !44
  %".5" = load i64, i64* %"value", !dbg !45
  %".6" = insertvalue %"struct.ritz_module_1.NodeId" undef, i64 %".5", 0 , !dbg !45
  ret %"struct.ritz_module_1.NodeId" %".6", !dbg !45
}

define %"struct.ritz_module_1.NodeId" @"node_id_invalid"() !dbg !18
{
entry:
  %".2" = insertvalue %"struct.ritz_module_1.NodeId" undef, i64 0, 0 , !dbg !46
  ret %"struct.ritz_module_1.NodeId" %".2", !dbg !46
}

define i32 @"node_id_is_valid"(%"struct.ritz_module_1.NodeId"* %"id.arg") !dbg !19
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.NodeId"* %"id.arg", metadata !49, metadata !7), !dbg !50
  %".4" = getelementptr %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %"id.arg", i32 0, i32 0 , !dbg !51
  %".5" = load i64, i64* %".4", !dbg !51
  %".6" = icmp ne i64 %".5", 0 , !dbg !51
  br i1 %".6", label %"if.then", label %"if.end", !dbg !51
if.then:
  %".8" = trunc i64 1 to i32 , !dbg !52
  ret i32 %".8", !dbg !52
if.end:
  %".10" = trunc i64 0 to i32 , !dbg !53
  ret i32 %".10", !dbg !53
}

define i32 @"node_id_eq"(%"struct.ritz_module_1.NodeId"* %"a.arg", %"struct.ritz_module_1.NodeId"* %"b.arg") !dbg !20
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.NodeId"* %"a.arg", metadata !54, metadata !7), !dbg !55
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.NodeId"* %"b.arg", metadata !56, metadata !7), !dbg !55
  %".6" = getelementptr %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %"a.arg", i32 0, i32 0 , !dbg !57
  %".7" = load i64, i64* %".6", !dbg !57
  %".8" = getelementptr %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %"b.arg", i32 0, i32 0 , !dbg !57
  %".9" = load i64, i64* %".8", !dbg !57
  %".10" = icmp eq i64 %".7", %".9" , !dbg !57
  br i1 %".10", label %"if.then", label %"if.end", !dbg !57
if.then:
  %".12" = trunc i64 1 to i32 , !dbg !58
  ret i32 %".12", !dbg !58
if.end:
  %".14" = trunc i64 0 to i32 , !dbg !59
  ret i32 %".14", !dbg !59
}

define %"struct.ritz_module_1.Dimension" @"dimension_px"(double %"value.arg") !dbg !21
{
entry:
  %"value" = alloca double
  store double %"value.arg", double* %"value"
  %".4" = load double, double* %"value", !dbg !60
  %".5" = insertvalue %"struct.ritz_module_1.Dimension" undef, double %".4", 0 , !dbg !60
  %".6" = insertvalue %"struct.ritz_module_1.Dimension" %".5", i32 0, 1 , !dbg !60
  ret %"struct.ritz_module_1.Dimension" %".6", !dbg !60
}

define %"struct.ritz_module_1.Dimension" @"dimension_percent"(double %"value.arg") !dbg !22
{
entry:
  %"value" = alloca double
  store double %"value.arg", double* %"value"
  %".4" = load double, double* %"value", !dbg !61
  %".5" = insertvalue %"struct.ritz_module_1.Dimension" undef, double %".4", 0 , !dbg !61
  %".6" = insertvalue %"struct.ritz_module_1.Dimension" %".5", i32 3, 1 , !dbg !61
  ret %"struct.ritz_module_1.Dimension" %".6", !dbg !61
}

define %"struct.ritz_module_1.Dimension" @"dimension_auto"() !dbg !23
{
entry:
  %".2" = insertvalue %"struct.ritz_module_1.Dimension" undef, double              0x0, 0 , !dbg !62
  %".3" = insertvalue %"struct.ritz_module_1.Dimension" %".2", i32 6, 1 , !dbg !62
  ret %"struct.ritz_module_1.Dimension" %".3", !dbg !62
}

define i32 @"dimension_is_auto"(%"struct.ritz_module_1.Dimension" %"d.arg") !dbg !24
{
entry:
  %"d" = alloca %"struct.ritz_module_1.Dimension"
  store %"struct.ritz_module_1.Dimension" %"d.arg", %"struct.ritz_module_1.Dimension"* %"d"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Dimension"* %"d", metadata !64, metadata !7), !dbg !65
  %".5" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"d", i32 0, i32 1 , !dbg !66
  %".6" = load i32, i32* %".5", !dbg !66
  %".7" = icmp eq i32 %".6", 6 , !dbg !66
  br i1 %".7", label %"if.then", label %"if.end", !dbg !66
if.then:
  %".9" = trunc i64 1 to i32 , !dbg !67
  ret i32 %".9", !dbg !67
if.end:
  %".11" = trunc i64 0 to i32 , !dbg !68
  ret i32 %".11", !dbg !68
}

define %"struct.ritz_module_1.EdgeSizes" @"edge_sizes_zero"() !dbg !25
{
entry:
  %".2" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double              0x0), !dbg !69
  %".3" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double              0x0), !dbg !69
  %".4" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double              0x0), !dbg !69
  %".5" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double              0x0), !dbg !69
  %".6" = insertvalue %"struct.ritz_module_1.EdgeSizes" undef, %"struct.ritz_module_1.Dimension" %".2", 0 , !dbg !69
  %".7" = insertvalue %"struct.ritz_module_1.EdgeSizes" %".6", %"struct.ritz_module_1.Dimension" %".3", 1 , !dbg !69
  %".8" = insertvalue %"struct.ritz_module_1.EdgeSizes" %".7", %"struct.ritz_module_1.Dimension" %".4", 2 , !dbg !69
  %".9" = insertvalue %"struct.ritz_module_1.EdgeSizes" %".8", %"struct.ritz_module_1.Dimension" %".5", 3 , !dbg !69
  ret %"struct.ritz_module_1.EdgeSizes" %".9", !dbg !69
}

define %"struct.ritz_module_1.EdgeSizes" @"edge_sizes_all"(double %"v.arg") !dbg !26
{
entry:
  %"v" = alloca double
  store double %"v.arg", double* %"v"
  %".4" = load double, double* %"v", !dbg !70
  %".5" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double %".4"), !dbg !70
  %".6" = load double, double* %"v", !dbg !70
  %".7" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double %".6"), !dbg !70
  %".8" = load double, double* %"v", !dbg !70
  %".9" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double %".8"), !dbg !70
  %".10" = load double, double* %"v", !dbg !70
  %".11" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double %".10"), !dbg !70
  %".12" = insertvalue %"struct.ritz_module_1.EdgeSizes" undef, %"struct.ritz_module_1.Dimension" %".5", 0 , !dbg !70
  %".13" = insertvalue %"struct.ritz_module_1.EdgeSizes" %".12", %"struct.ritz_module_1.Dimension" %".7", 1 , !dbg !70
  %".14" = insertvalue %"struct.ritz_module_1.EdgeSizes" %".13", %"struct.ritz_module_1.Dimension" %".9", 2 , !dbg !70
  %".15" = insertvalue %"struct.ritz_module_1.EdgeSizes" %".14", %"struct.ritz_module_1.Dimension" %".11", 3 , !dbg !70
  ret %"struct.ritz_module_1.EdgeSizes" %".15", !dbg !70
}

define %"struct.ritz_module_1.EdgeSizes" @"edge_sizes_symmetric"(double %"vert.arg", double %"horiz.arg") !dbg !27
{
entry:
  %"vert" = alloca double
  store double %"vert.arg", double* %"vert"
  %"horiz" = alloca double
  store double %"horiz.arg", double* %"horiz"
  %".6" = load double, double* %"vert", !dbg !71
  %".7" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double %".6"), !dbg !71
  %".8" = load double, double* %"horiz", !dbg !71
  %".9" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double %".8"), !dbg !71
  %".10" = load double, double* %"vert", !dbg !71
  %".11" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double %".10"), !dbg !71
  %".12" = load double, double* %"horiz", !dbg !71
  %".13" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double %".12"), !dbg !71
  %".14" = insertvalue %"struct.ritz_module_1.EdgeSizes" undef, %"struct.ritz_module_1.Dimension" %".7", 0 , !dbg !71
  %".15" = insertvalue %"struct.ritz_module_1.EdgeSizes" %".14", %"struct.ritz_module_1.Dimension" %".9", 1 , !dbg !71
  %".16" = insertvalue %"struct.ritz_module_1.EdgeSizes" %".15", %"struct.ritz_module_1.Dimension" %".11", 2 , !dbg !71
  %".17" = insertvalue %"struct.ritz_module_1.EdgeSizes" %".16", %"struct.ritz_module_1.Dimension" %".13", 3 , !dbg !71
  ret %"struct.ritz_module_1.EdgeSizes" %".17", !dbg !71
}

define %"struct.ritz_module_1.Color" @"color_rgb"(i8 %"r.arg", i8 %"g.arg", i8 %"b.arg") !dbg !28
{
entry:
  %"r" = alloca i8
  store i8 %"r.arg", i8* %"r"
  call void @"llvm.dbg.declare"(metadata i8* %"r", metadata !72, metadata !7), !dbg !73
  %"g" = alloca i8
  store i8 %"g.arg", i8* %"g"
  call void @"llvm.dbg.declare"(metadata i8* %"g", metadata !74, metadata !7), !dbg !73
  %"b" = alloca i8
  store i8 %"b.arg", i8* %"b"
  call void @"llvm.dbg.declare"(metadata i8* %"b", metadata !75, metadata !7), !dbg !73
  %".11" = load i8, i8* %"r", !dbg !76
  %".12" = load i8, i8* %"g", !dbg !76
  %".13" = load i8, i8* %"b", !dbg !76
  %".14" = trunc i64 255 to i8 , !dbg !76
  %".15" = insertvalue %"struct.ritz_module_1.Color" undef, i8 %".11", 0 , !dbg !76
  %".16" = insertvalue %"struct.ritz_module_1.Color" %".15", i8 %".12", 1 , !dbg !76
  %".17" = insertvalue %"struct.ritz_module_1.Color" %".16", i8 %".13", 2 , !dbg !76
  %".18" = insertvalue %"struct.ritz_module_1.Color" %".17", i8 %".14", 3 , !dbg !76
  ret %"struct.ritz_module_1.Color" %".18", !dbg !76
}

define %"struct.ritz_module_1.Color" @"color_rgba"(i8 %"r.arg", i8 %"g.arg", i8 %"b.arg", i8 %"a.arg") !dbg !29
{
entry:
  %"r" = alloca i8
  store i8 %"r.arg", i8* %"r"
  call void @"llvm.dbg.declare"(metadata i8* %"r", metadata !77, metadata !7), !dbg !78
  %"g" = alloca i8
  store i8 %"g.arg", i8* %"g"
  call void @"llvm.dbg.declare"(metadata i8* %"g", metadata !79, metadata !7), !dbg !78
  %"b" = alloca i8
  store i8 %"b.arg", i8* %"b"
  call void @"llvm.dbg.declare"(metadata i8* %"b", metadata !80, metadata !7), !dbg !78
  %"a" = alloca i8
  store i8 %"a.arg", i8* %"a"
  call void @"llvm.dbg.declare"(metadata i8* %"a", metadata !81, metadata !7), !dbg !78
  %".14" = load i8, i8* %"r", !dbg !82
  %".15" = load i8, i8* %"g", !dbg !82
  %".16" = load i8, i8* %"b", !dbg !82
  %".17" = load i8, i8* %"a", !dbg !82
  %".18" = insertvalue %"struct.ritz_module_1.Color" undef, i8 %".14", 0 , !dbg !82
  %".19" = insertvalue %"struct.ritz_module_1.Color" %".18", i8 %".15", 1 , !dbg !82
  %".20" = insertvalue %"struct.ritz_module_1.Color" %".19", i8 %".16", 2 , !dbg !82
  %".21" = insertvalue %"struct.ritz_module_1.Color" %".20", i8 %".17", 3 , !dbg !82
  ret %"struct.ritz_module_1.Color" %".21", !dbg !82
}

define %"struct.ritz_module_1.Color" @"color_black"() !dbg !30
{
entry:
  %".2" = trunc i64 0 to i8 , !dbg !83
  %".3" = trunc i64 0 to i8 , !dbg !83
  %".4" = trunc i64 0 to i8 , !dbg !83
  %".5" = trunc i64 255 to i8 , !dbg !83
  %".6" = insertvalue %"struct.ritz_module_1.Color" undef, i8 %".2", 0 , !dbg !83
  %".7" = insertvalue %"struct.ritz_module_1.Color" %".6", i8 %".3", 1 , !dbg !83
  %".8" = insertvalue %"struct.ritz_module_1.Color" %".7", i8 %".4", 2 , !dbg !83
  %".9" = insertvalue %"struct.ritz_module_1.Color" %".8", i8 %".5", 3 , !dbg !83
  ret %"struct.ritz_module_1.Color" %".9", !dbg !83
}

define %"struct.ritz_module_1.Color" @"color_white"() !dbg !31
{
entry:
  %".2" = trunc i64 255 to i8 , !dbg !84
  %".3" = trunc i64 255 to i8 , !dbg !84
  %".4" = trunc i64 255 to i8 , !dbg !84
  %".5" = trunc i64 255 to i8 , !dbg !84
  %".6" = insertvalue %"struct.ritz_module_1.Color" undef, i8 %".2", 0 , !dbg !84
  %".7" = insertvalue %"struct.ritz_module_1.Color" %".6", i8 %".3", 1 , !dbg !84
  %".8" = insertvalue %"struct.ritz_module_1.Color" %".7", i8 %".4", 2 , !dbg !84
  %".9" = insertvalue %"struct.ritz_module_1.Color" %".8", i8 %".5", 3 , !dbg !84
  ret %"struct.ritz_module_1.Color" %".9", !dbg !84
}

define %"struct.ritz_module_1.Color" @"color_transparent"() !dbg !32
{
entry:
  %".2" = trunc i64 0 to i8 , !dbg !85
  %".3" = trunc i64 0 to i8 , !dbg !85
  %".4" = trunc i64 0 to i8 , !dbg !85
  %".5" = trunc i64 0 to i8 , !dbg !85
  %".6" = insertvalue %"struct.ritz_module_1.Color" undef, i8 %".2", 0 , !dbg !85
  %".7" = insertvalue %"struct.ritz_module_1.Color" %".6", i8 %".3", 1 , !dbg !85
  %".8" = insertvalue %"struct.ritz_module_1.Color" %".7", i8 %".4", 2 , !dbg !85
  %".9" = insertvalue %"struct.ritz_module_1.Color" %".8", i8 %".5", 3 , !dbg !85
  ret %"struct.ritz_module_1.Color" %".9", !dbg !85
}

define i32 @"color_is_transparent"(%"struct.ritz_module_1.Color"* %"c.arg") !dbg !33
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Color"* %"c.arg", metadata !88, metadata !7), !dbg !89
  %".4" = getelementptr %"struct.ritz_module_1.Color", %"struct.ritz_module_1.Color"* %"c.arg", i32 0, i32 3 , !dbg !90
  %".5" = load i8, i8* %".4", !dbg !90
  %".6" = sext i8 %".5" to i64 , !dbg !90
  %".7" = icmp eq i64 %".6", 0 , !dbg !90
  br i1 %".7", label %"if.then", label %"if.end", !dbg !90
if.then:
  %".9" = trunc i64 1 to i32 , !dbg !91
  ret i32 %".9", !dbg !91
if.end:
  %".11" = trunc i64 0 to i32 , !dbg !92
  ret i32 %".11", !dbg !92
}

define %"struct.ritz_module_1.BorderEdge" @"border_edge_none"() !dbg !34
{
entry:
  %".2" = call %"struct.ritz_module_1.Color" @"color_transparent"(), !dbg !93
  %".3" = insertvalue %"struct.ritz_module_1.BorderEdge" undef, double              0x0, 0 , !dbg !93
  %".4" = insertvalue %"struct.ritz_module_1.BorderEdge" %".3", i32 0, 1 , !dbg !93
  %".5" = insertvalue %"struct.ritz_module_1.BorderEdge" %".4", %"struct.ritz_module_1.Color" %".2", 2 , !dbg !93
  ret %"struct.ritz_module_1.BorderEdge" %".5", !dbg !93
}

define %"struct.ritz_module_1.Border" @"border_none"() !dbg !35
{
entry:
  %".2" = call %"struct.ritz_module_1.BorderEdge" @"border_edge_none"(), !dbg !94
  %".3" = call %"struct.ritz_module_1.BorderEdge" @"border_edge_none"(), !dbg !94
  %".4" = call %"struct.ritz_module_1.BorderEdge" @"border_edge_none"(), !dbg !94
  %".5" = call %"struct.ritz_module_1.BorderEdge" @"border_edge_none"(), !dbg !94
  %".6" = insertvalue %"struct.ritz_module_1.Border" undef, %"struct.ritz_module_1.BorderEdge" %".2", 0 , !dbg !94
  %".7" = insertvalue %"struct.ritz_module_1.Border" %".6", %"struct.ritz_module_1.BorderEdge" %".3", 1 , !dbg !94
  %".8" = insertvalue %"struct.ritz_module_1.Border" %".7", %"struct.ritz_module_1.BorderEdge" %".4", 2 , !dbg !94
  %".9" = insertvalue %"struct.ritz_module_1.Border" %".8", %"struct.ritz_module_1.BorderEdge" %".5", 3 , !dbg !94
  ret %"struct.ritz_module_1.Border" %".9", !dbg !94
}

define %"struct.ritz_module_1.TextStyle" @"text_style_default"() !dbg !36
{
entry:
  %".2" = call %"struct.ritz_module_1.Color" @"color_black"(), !dbg !95
  %".3" = insertvalue %"struct.ritz_module_1.TextStyle" undef, double 0x4030000000000000, 0 , !dbg !95
  %".4" = insertvalue %"struct.ritz_module_1.TextStyle" %".3", i32 400, 1 , !dbg !95
  %".5" = insertvalue %"struct.ritz_module_1.TextStyle" %".4", i32 0, 2 , !dbg !95
  %".6" = insertvalue %"struct.ritz_module_1.TextStyle" %".5", double 0x3ff3333333333333, 3 , !dbg !95
  %".7" = insertvalue %"struct.ritz_module_1.TextStyle" %".6", double              0x0, 4 , !dbg !95
  %".8" = insertvalue %"struct.ritz_module_1.TextStyle" %".7", i32 0, 5 , !dbg !95
  %".9" = insertvalue %"struct.ritz_module_1.TextStyle" %".8", %"struct.ritz_module_1.Color" %".2", 6 , !dbg !95
  ret %"struct.ritz_module_1.TextStyle" %".9", !dbg !95
}

define %"struct.ritz_module_1.FlexStyle" @"flex_style_default"() !dbg !37
{
entry:
  %".2" = call %"struct.ritz_module_1.Dimension" @"dimension_auto"(), !dbg !96
  %".3" = trunc i64 0 to i32 , !dbg !96
  %".4" = insertvalue %"struct.ritz_module_1.FlexStyle" undef, i32 0, 0 , !dbg !96
  %".5" = insertvalue %"struct.ritz_module_1.FlexStyle" %".4", i32 0, 1 , !dbg !96
  %".6" = insertvalue %"struct.ritz_module_1.FlexStyle" %".5", i32 4, 2 , !dbg !96
  %".7" = insertvalue %"struct.ritz_module_1.FlexStyle" %".6", double              0x0, 3 , !dbg !96
  %".8" = insertvalue %"struct.ritz_module_1.FlexStyle" %".7", double 0x3ff0000000000000, 4 , !dbg !96
  %".9" = insertvalue %"struct.ritz_module_1.FlexStyle" %".8", %"struct.ritz_module_1.Dimension" %".2", 5 , !dbg !96
  %".10" = insertvalue %"struct.ritz_module_1.FlexStyle" %".9", i32 %".3", 6 , !dbg !96
  ret %"struct.ritz_module_1.FlexStyle" %".10", !dbg !96
}

define %"struct.ritz_module_1.Transform" @"transform_identity"() !dbg !38
{
entry:
  %".2" = insertvalue %"struct.ritz_module_1.Transform" undef, double 0x3ff0000000000000, 0 , !dbg !97
  %".3" = insertvalue %"struct.ritz_module_1.Transform" %".2", double              0x0, 1 , !dbg !97
  %".4" = insertvalue %"struct.ritz_module_1.Transform" %".3", double              0x0, 2 , !dbg !97
  %".5" = insertvalue %"struct.ritz_module_1.Transform" %".4", double 0x3ff0000000000000, 3 , !dbg !97
  %".6" = insertvalue %"struct.ritz_module_1.Transform" %".5", double              0x0, 4 , !dbg !97
  %".7" = insertvalue %"struct.ritz_module_1.Transform" %".6", double              0x0, 5 , !dbg !97
  ret %"struct.ritz_module_1.Transform" %".7", !dbg !97
}

define %"struct.ritz_module_1.Transform" @"transform_translate"(double %"x.arg", double %"y.arg") !dbg !39
{
entry:
  %"x" = alloca double
  store double %"x.arg", double* %"x"
  %"y" = alloca double
  store double %"y.arg", double* %"y"
  %".6" = load double, double* %"x", !dbg !98
  %".7" = load double, double* %"y", !dbg !98
  %".8" = insertvalue %"struct.ritz_module_1.Transform" undef, double 0x3ff0000000000000, 0 , !dbg !98
  %".9" = insertvalue %"struct.ritz_module_1.Transform" %".8", double              0x0, 1 , !dbg !98
  %".10" = insertvalue %"struct.ritz_module_1.Transform" %".9", double              0x0, 2 , !dbg !98
  %".11" = insertvalue %"struct.ritz_module_1.Transform" %".10", double 0x3ff0000000000000, 3 , !dbg !98
  %".12" = insertvalue %"struct.ritz_module_1.Transform" %".11", double %".6", 4 , !dbg !98
  %".13" = insertvalue %"struct.ritz_module_1.Transform" %".12", double %".7", 5 , !dbg !98
  ret %"struct.ritz_module_1.Transform" %".13", !dbg !98
}

define %"struct.ritz_module_1.Transform" @"transform_scale"(double %"sx.arg", double %"sy.arg") !dbg !40
{
entry:
  %"sx" = alloca double
  store double %"sx.arg", double* %"sx"
  %"sy" = alloca double
  store double %"sy.arg", double* %"sy"
  %".6" = load double, double* %"sx", !dbg !99
  %".7" = load double, double* %"sy", !dbg !99
  %".8" = insertvalue %"struct.ritz_module_1.Transform" undef, double %".6", 0 , !dbg !99
  %".9" = insertvalue %"struct.ritz_module_1.Transform" %".8", double              0x0, 1 , !dbg !99
  %".10" = insertvalue %"struct.ritz_module_1.Transform" %".9", double              0x0, 2 , !dbg !99
  %".11" = insertvalue %"struct.ritz_module_1.Transform" %".10", double %".7", 3 , !dbg !99
  %".12" = insertvalue %"struct.ritz_module_1.Transform" %".11", double              0x0, 4 , !dbg !99
  %".13" = insertvalue %"struct.ritz_module_1.Transform" %".12", double              0x0, 5 , !dbg !99
  ret %"struct.ritz_module_1.Transform" %".13", !dbg !99
}

define i32 @"transform_is_identity"(%"struct.ritz_module_1.Transform" %"t.arg") !dbg !41
{
entry:
  %"t" = alloca %"struct.ritz_module_1.Transform"
  store %"struct.ritz_module_1.Transform" %"t.arg", %"struct.ritz_module_1.Transform"* %"t"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Transform"* %"t", metadata !101, metadata !7), !dbg !102
  %".5" = getelementptr %"struct.ritz_module_1.Transform", %"struct.ritz_module_1.Transform"* %"t", i32 0, i32 0 , !dbg !103
  %".6" = load double, double* %".5", !dbg !103
  %".7" = fcmp one double %".6", 0x3ff0000000000000 , !dbg !103
  br i1 %".7", label %"if.then", label %"if.end", !dbg !103
if.then:
  %".9" = trunc i64 0 to i32 , !dbg !104
  ret i32 %".9", !dbg !104
if.end:
  %".11" = getelementptr %"struct.ritz_module_1.Transform", %"struct.ritz_module_1.Transform"* %"t", i32 0, i32 1 , !dbg !105
  %".12" = load double, double* %".11", !dbg !105
  %".13" = fcmp one double %".12",              0x0 , !dbg !105
  br i1 %".13", label %"if.then.1", label %"if.end.1", !dbg !105
if.then.1:
  %".15" = trunc i64 0 to i32 , !dbg !106
  ret i32 %".15", !dbg !106
if.end.1:
  %".17" = getelementptr %"struct.ritz_module_1.Transform", %"struct.ritz_module_1.Transform"* %"t", i32 0, i32 2 , !dbg !107
  %".18" = load double, double* %".17", !dbg !107
  %".19" = fcmp one double %".18",              0x0 , !dbg !107
  br i1 %".19", label %"if.then.2", label %"if.end.2", !dbg !107
if.then.2:
  %".21" = trunc i64 0 to i32 , !dbg !108
  ret i32 %".21", !dbg !108
if.end.2:
  %".23" = getelementptr %"struct.ritz_module_1.Transform", %"struct.ritz_module_1.Transform"* %"t", i32 0, i32 3 , !dbg !109
  %".24" = load double, double* %".23", !dbg !109
  %".25" = fcmp one double %".24", 0x3ff0000000000000 , !dbg !109
  br i1 %".25", label %"if.then.3", label %"if.end.3", !dbg !109
if.then.3:
  %".27" = trunc i64 0 to i32 , !dbg !110
  ret i32 %".27", !dbg !110
if.end.3:
  %".29" = getelementptr %"struct.ritz_module_1.Transform", %"struct.ritz_module_1.Transform"* %"t", i32 0, i32 4 , !dbg !111
  %".30" = load double, double* %".29", !dbg !111
  %".31" = fcmp one double %".30",              0x0 , !dbg !111
  br i1 %".31", label %"if.then.4", label %"if.end.4", !dbg !111
if.then.4:
  %".33" = trunc i64 0 to i32 , !dbg !112
  ret i32 %".33", !dbg !112
if.end.4:
  %".35" = getelementptr %"struct.ritz_module_1.Transform", %"struct.ritz_module_1.Transform"* %"t", i32 0, i32 5 , !dbg !113
  %".36" = load double, double* %".35", !dbg !113
  %".37" = fcmp one double %".36",              0x0 , !dbg !113
  br i1 %".37", label %"if.then.5", label %"if.end.5", !dbg !113
if.then.5:
  %".39" = trunc i64 0 to i32 , !dbg !114
  ret i32 %".39", !dbg !114
if.end.5:
  %".41" = trunc i64 1 to i32 , !dbg !115
  ret i32 %".41", !dbg !115
}

define %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"() !dbg !42
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !116
  %".3" = call %"struct.ritz_module_1.Dimension" @"dimension_auto"(), !dbg !116
  %".4" = call %"struct.ritz_module_1.Dimension" @"dimension_auto"(), !dbg !116
  %".5" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double              0x0), !dbg !116
  %".6" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double              0x0), !dbg !116
  %".7" = call %"struct.ritz_module_1.Dimension" @"dimension_auto"(), !dbg !116
  %".8" = call %"struct.ritz_module_1.Dimension" @"dimension_auto"(), !dbg !116
  %".9" = call %"struct.ritz_module_1.EdgeSizes" @"edge_sizes_zero"(), !dbg !116
  %".10" = call %"struct.ritz_module_1.EdgeSizes" @"edge_sizes_zero"(), !dbg !116
  %".11" = call %"struct.ritz_module_1.Border" @"border_none"(), !dbg !116
  %".12" = call %"struct.ritz_module_1.TextStyle" @"text_style_default"(), !dbg !116
  %".13" = call %"struct.ritz_module_1.FlexStyle" @"flex_style_default"(), !dbg !116
  %".14" = call %"struct.ritz_module_1.Color" @"color_transparent"(), !dbg !116
  %".15" = call %"struct.ritz_module_1.Transform" @"transform_identity"(), !dbg !116
  %".16" = insertvalue %"struct.ritz_module_1.ComputedStyle" undef, i32 1, 0 , !dbg !116
  %".17" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".16", i32 0, 1 , !dbg !116
  %".18" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".17", i32 0, 2 , !dbg !116
  %".19" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".18", i32 0, 3 , !dbg !116
  %".20" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".19", i32 0, 4 , !dbg !116
  %".21" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".20", i32 0, 5 , !dbg !116
  %".22" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".21", i32 %".2", 6 , !dbg !116
  %".23" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".22", %"struct.ritz_module_1.Dimension" %".3", 7 , !dbg !116
  %".24" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".23", %"struct.ritz_module_1.Dimension" %".4", 8 , !dbg !116
  %".25" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".24", %"struct.ritz_module_1.Dimension" %".5", 9 , !dbg !116
  %".26" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".25", %"struct.ritz_module_1.Dimension" %".6", 10 , !dbg !116
  %".27" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".26", %"struct.ritz_module_1.Dimension" %".7", 11 , !dbg !116
  %".28" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".27", %"struct.ritz_module_1.Dimension" %".8", 12 , !dbg !116
  %".29" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".28", %"struct.ritz_module_1.EdgeSizes" %".9", 13 , !dbg !116
  %".30" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".29", %"struct.ritz_module_1.EdgeSizes" %".10", 14 , !dbg !116
  %".31" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".30", %"struct.ritz_module_1.Border" %".11", 15 , !dbg !116
  %".32" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".31", %"struct.ritz_module_1.TextStyle" %".12", 16 , !dbg !116
  %".33" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".32", %"struct.ritz_module_1.FlexStyle" %".13", 17 , !dbg !116
  %".34" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".33", %"struct.ritz_module_1.Color" %".14", 18 , !dbg !116
  %".35" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".34", double 0x3ff0000000000000, 19 , !dbg !116
  %".36" = insertvalue %"struct.ritz_module_1.ComputedStyle" %".35", %"struct.ritz_module_1.Transform" %".15", 20 , !dbg !116
  ret %"struct.ritz_module_1.ComputedStyle" %".36", !dbg !116
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/lib/style", filename: "types.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 20, name: "node_id_new", scopeLine: 20, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 23, name: "node_id_invalid", scopeLine: 23, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 26, name: "node_id_is_valid", scopeLine: 26, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 31, name: "node_id_eq", scopeLine: 31, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 90, name: "dimension_px", scopeLine: 90, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 93, name: "dimension_percent", scopeLine: 93, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 96, name: "dimension_auto", scopeLine: 96, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 99, name: "dimension_is_auto", scopeLine: 99, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 114, name: "edge_sizes_zero", scopeLine: 114, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 122, name: "edge_sizes_all", scopeLine: 122, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 130, name: "edge_sizes_symmetric", scopeLine: 130, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 154, name: "color_rgb", scopeLine: 154, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 157, name: "color_rgba", scopeLine: 157, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 160, name: "color_black", scopeLine: 160, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 163, name: "color_white", scopeLine: 163, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 166, name: "color_transparent", scopeLine: 166, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 169, name: "color_is_transparent", scopeLine: 169, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "border_edge_none", scopeLine: 179, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 192, name: "border_none", scopeLine: 192, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 224, name: "text_style_default", scopeLine: 224, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 266, name: "flex_style_default", scopeLine: 266, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 293, name: "transform_identity", scopeLine: 293, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 296, name: "transform_translate", scopeLine: 296, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 299, name: "transform_scale", scopeLine: 299, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 302, name: "transform_is_identity", scopeLine: 302, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 355, name: "computed_style_default", scopeLine: 355, type: !4, unit: !1)
!43 = !DILocalVariable(file: !0, line: 20, name: "value", scope: !17, type: !15)
!44 = !DILocation(column: 1, line: 20, scope: !17)
!45 = !DILocation(column: 5, line: 21, scope: !17)
!46 = !DILocation(column: 5, line: 24, scope: !18)
!47 = !DICompositeType(align: 64, file: !0, name: "NodeId", size: 64, tag: DW_TAG_structure_type)
!48 = !DIDerivedType(baseType: !47, size: 64, tag: DW_TAG_reference_type)
!49 = !DILocalVariable(file: !0, line: 26, name: "id", scope: !19, type: !48)
!50 = !DILocation(column: 1, line: 26, scope: !19)
!51 = !DILocation(column: 5, line: 27, scope: !19)
!52 = !DILocation(column: 9, line: 28, scope: !19)
!53 = !DILocation(column: 5, line: 29, scope: !19)
!54 = !DILocalVariable(file: !0, line: 31, name: "a", scope: !20, type: !48)
!55 = !DILocation(column: 1, line: 31, scope: !20)
!56 = !DILocalVariable(file: !0, line: 31, name: "b", scope: !20, type: !48)
!57 = !DILocation(column: 5, line: 32, scope: !20)
!58 = !DILocation(column: 9, line: 33, scope: !20)
!59 = !DILocation(column: 5, line: 34, scope: !20)
!60 = !DILocation(column: 5, line: 91, scope: !21)
!61 = !DILocation(column: 5, line: 94, scope: !22)
!62 = !DILocation(column: 5, line: 97, scope: !23)
!63 = !DICompositeType(align: 64, file: !0, name: "Dimension", size: 128, tag: DW_TAG_structure_type)
!64 = !DILocalVariable(file: !0, line: 99, name: "d", scope: !24, type: !63)
!65 = !DILocation(column: 1, line: 99, scope: !24)
!66 = !DILocation(column: 5, line: 100, scope: !24)
!67 = !DILocation(column: 9, line: 101, scope: !24)
!68 = !DILocation(column: 5, line: 102, scope: !24)
!69 = !DILocation(column: 5, line: 115, scope: !25)
!70 = !DILocation(column: 5, line: 123, scope: !26)
!71 = !DILocation(column: 5, line: 131, scope: !27)
!72 = !DILocalVariable(file: !0, line: 154, name: "r", scope: !28, type: !12)
!73 = !DILocation(column: 1, line: 154, scope: !28)
!74 = !DILocalVariable(file: !0, line: 154, name: "g", scope: !28, type: !12)
!75 = !DILocalVariable(file: !0, line: 154, name: "b", scope: !28, type: !12)
!76 = !DILocation(column: 5, line: 155, scope: !28)
!77 = !DILocalVariable(file: !0, line: 157, name: "r", scope: !29, type: !12)
!78 = !DILocation(column: 1, line: 157, scope: !29)
!79 = !DILocalVariable(file: !0, line: 157, name: "g", scope: !29, type: !12)
!80 = !DILocalVariable(file: !0, line: 157, name: "b", scope: !29, type: !12)
!81 = !DILocalVariable(file: !0, line: 157, name: "a", scope: !29, type: !12)
!82 = !DILocation(column: 5, line: 158, scope: !29)
!83 = !DILocation(column: 5, line: 161, scope: !30)
!84 = !DILocation(column: 5, line: 164, scope: !31)
!85 = !DILocation(column: 5, line: 167, scope: !32)
!86 = !DICompositeType(align: 8, file: !0, name: "Color", size: 32, tag: DW_TAG_structure_type)
!87 = !DIDerivedType(baseType: !86, size: 64, tag: DW_TAG_reference_type)
!88 = !DILocalVariable(file: !0, line: 169, name: "c", scope: !33, type: !87)
!89 = !DILocation(column: 1, line: 169, scope: !33)
!90 = !DILocation(column: 5, line: 170, scope: !33)
!91 = !DILocation(column: 9, line: 171, scope: !33)
!92 = !DILocation(column: 5, line: 172, scope: !33)
!93 = !DILocation(column: 5, line: 180, scope: !34)
!94 = !DILocation(column: 5, line: 193, scope: !35)
!95 = !DILocation(column: 5, line: 225, scope: !36)
!96 = !DILocation(column: 5, line: 267, scope: !37)
!97 = !DILocation(column: 5, line: 294, scope: !38)
!98 = !DILocation(column: 5, line: 297, scope: !39)
!99 = !DILocation(column: 5, line: 300, scope: !40)
!100 = !DICompositeType(align: 64, file: !0, name: "Transform", size: 384, tag: DW_TAG_structure_type)
!101 = !DILocalVariable(file: !0, line: 302, name: "t", scope: !41, type: !100)
!102 = !DILocation(column: 1, line: 302, scope: !41)
!103 = !DILocation(column: 5, line: 303, scope: !41)
!104 = !DILocation(column: 9, line: 304, scope: !41)
!105 = !DILocation(column: 5, line: 305, scope: !41)
!106 = !DILocation(column: 9, line: 306, scope: !41)
!107 = !DILocation(column: 5, line: 307, scope: !41)
!108 = !DILocation(column: 9, line: 308, scope: !41)
!109 = !DILocation(column: 5, line: 309, scope: !41)
!110 = !DILocation(column: 9, line: 310, scope: !41)
!111 = !DILocation(column: 5, line: 311, scope: !41)
!112 = !DILocation(column: 9, line: 312, scope: !41)
!113 = !DILocation(column: 5, line: 313, scope: !41)
!114 = !DILocation(column: 9, line: 314, scope: !41)
!115 = !DILocation(column: 5, line: 315, scope: !41)
!116 = !DILocation(column: 5, line: 356, scope: !42)