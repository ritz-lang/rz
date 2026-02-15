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

declare %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 %".1")

declare %"struct.ritz_module_1.NodeId" @"node_id_invalid"()

declare i32 @"node_id_is_valid"(%"struct.ritz_module_1.NodeId"* %".1")

declare i32 @"node_id_eq"(%"struct.ritz_module_1.NodeId"* %".1", %"struct.ritz_module_1.NodeId"* %".2")

declare %"struct.ritz_module_1.Dimension" @"dimension_px"(double %".1")

declare %"struct.ritz_module_1.Dimension" @"dimension_percent"(double %".1")

declare %"struct.ritz_module_1.Dimension" @"dimension_auto"()

declare i32 @"dimension_is_auto"(%"struct.ritz_module_1.Dimension" %".1")

declare %"struct.ritz_module_1.EdgeSizes" @"edge_sizes_zero"()

declare %"struct.ritz_module_1.EdgeSizes" @"edge_sizes_all"(double %".1")

declare %"struct.ritz_module_1.EdgeSizes" @"edge_sizes_symmetric"(double %".1", double %".2")

declare %"struct.ritz_module_1.Color" @"color_rgb"(i8 %".1", i8 %".2", i8 %".3")

declare %"struct.ritz_module_1.Color" @"color_rgba"(i8 %".1", i8 %".2", i8 %".3", i8 %".4")

declare %"struct.ritz_module_1.Color" @"color_black"()

declare %"struct.ritz_module_1.Color" @"color_white"()

declare %"struct.ritz_module_1.Color" @"color_transparent"()

declare i32 @"color_is_transparent"(%"struct.ritz_module_1.Color"* %".1")

declare %"struct.ritz_module_1.BorderEdge" @"border_edge_none"()

declare %"struct.ritz_module_1.Border" @"border_none"()

declare %"struct.ritz_module_1.TextStyle" @"text_style_default"()

declare %"struct.ritz_module_1.FlexStyle" @"flex_style_default"()

declare %"struct.ritz_module_1.Transform" @"transform_identity"()

declare %"struct.ritz_module_1.Transform" @"transform_translate"(double %".1", double %".2")

declare %"struct.ritz_module_1.Transform" @"transform_scale"(double %".1", double %".2")

declare i32 @"transform_is_identity"(%"struct.ritz_module_1.Transform" %".1")

declare %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"()

define i32 @"test_node_id_new"() !dbg !17
{
entry:
  %".2" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 42), !dbg !28
  %".3" = extractvalue %"struct.ritz_module_1.NodeId" %".2", 0 , !dbg !29
  %".4" = icmp ne i64 %".3", 42 , !dbg !29
  br i1 %".4", label %"if.then", label %"if.end", !dbg !29
if.then:
  %".6" = trunc i64 1 to i32 , !dbg !30
  ret i32 %".6", !dbg !30
if.end:
  %".8" = trunc i64 0 to i32 , !dbg !31
  ret i32 %".8", !dbg !31
}

define i32 @"test_node_id_invalid"() !dbg !18
{
entry:
  %".2" = call %"struct.ritz_module_1.NodeId" @"node_id_invalid"(), !dbg !32
  %"id.addr" = alloca %"struct.ritz_module_1.NodeId", !dbg !33
  store %"struct.ritz_module_1.NodeId" %".2", %"struct.ritz_module_1.NodeId"* %"id.addr", !dbg !33
  %".4" = call i32 @"node_id_is_valid"(%"struct.ritz_module_1.NodeId"* %"id.addr"), !dbg !33
  %".5" = sext i32 %".4" to i64 , !dbg !33
  %".6" = icmp ne i64 %".5", 0 , !dbg !33
  br i1 %".6", label %"if.then", label %"if.end", !dbg !33
if.then:
  %".8" = trunc i64 1 to i32 , !dbg !34
  ret i32 %".8", !dbg !34
if.end:
  %".10" = trunc i64 0 to i32 , !dbg !35
  ret i32 %".10", !dbg !35
}

define i32 @"test_node_id_valid"() !dbg !19
{
entry:
  %".2" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !36
  %"id.addr" = alloca %"struct.ritz_module_1.NodeId", !dbg !37
  store %"struct.ritz_module_1.NodeId" %".2", %"struct.ritz_module_1.NodeId"* %"id.addr", !dbg !37
  %".4" = call i32 @"node_id_is_valid"(%"struct.ritz_module_1.NodeId"* %"id.addr"), !dbg !37
  %".5" = sext i32 %".4" to i64 , !dbg !37
  %".6" = icmp eq i64 %".5", 0 , !dbg !37
  br i1 %".6", label %"if.then", label %"if.end", !dbg !37
if.then:
  %".8" = trunc i64 1 to i32 , !dbg !38
  ret i32 %".8", !dbg !38
if.end:
  %".10" = trunc i64 0 to i32 , !dbg !39
  ret i32 %".10", !dbg !39
}

define i32 @"test_dimension_px"() !dbg !20
{
entry:
  %".2" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double 0x4059000000000000), !dbg !40
  %".3" = extractvalue %"struct.ritz_module_1.Dimension" %".2", 0 , !dbg !41
  %".4" = fcmp one double %".3", 0x4059000000000000 , !dbg !41
  br i1 %".4", label %"if.then", label %"if.end", !dbg !41
if.then:
  %".6" = trunc i64 1 to i32 , !dbg !42
  ret i32 %".6", !dbg !42
if.end:
  %".8" = extractvalue %"struct.ritz_module_1.Dimension" %".2", 1 , !dbg !43
  %".9" = icmp ne i32 %".8", 0 , !dbg !43
  br i1 %".9", label %"if.then.1", label %"if.end.1", !dbg !43
if.then.1:
  %".11" = trunc i64 2 to i32 , !dbg !44
  ret i32 %".11", !dbg !44
if.end.1:
  %".13" = trunc i64 0 to i32 , !dbg !45
  ret i32 %".13", !dbg !45
}

define i32 @"test_dimension_percent"() !dbg !21
{
entry:
  %".2" = call %"struct.ritz_module_1.Dimension" @"dimension_percent"(double 0x4049000000000000), !dbg !46
  %".3" = extractvalue %"struct.ritz_module_1.Dimension" %".2", 0 , !dbg !47
  %".4" = fcmp one double %".3", 0x4049000000000000 , !dbg !47
  br i1 %".4", label %"if.then", label %"if.end", !dbg !47
if.then:
  %".6" = trunc i64 1 to i32 , !dbg !48
  ret i32 %".6", !dbg !48
if.end:
  %".8" = extractvalue %"struct.ritz_module_1.Dimension" %".2", 1 , !dbg !49
  %".9" = icmp ne i32 %".8", 3 , !dbg !49
  br i1 %".9", label %"if.then.1", label %"if.end.1", !dbg !49
if.then.1:
  %".11" = trunc i64 2 to i32 , !dbg !50
  ret i32 %".11", !dbg !50
if.end.1:
  %".13" = trunc i64 0 to i32 , !dbg !51
  ret i32 %".13", !dbg !51
}

define i32 @"test_dimension_auto"() !dbg !22
{
entry:
  %".2" = call %"struct.ritz_module_1.Dimension" @"dimension_auto"(), !dbg !52
  %".3" = call i32 @"dimension_is_auto"(%"struct.ritz_module_1.Dimension" %".2"), !dbg !53
  %".4" = sext i32 %".3" to i64 , !dbg !53
  %".5" = icmp eq i64 %".4", 0 , !dbg !53
  br i1 %".5", label %"if.then", label %"if.end", !dbg !53
if.then:
  %".7" = trunc i64 1 to i32 , !dbg !54
  ret i32 %".7", !dbg !54
if.end:
  %".9" = trunc i64 0 to i32 , !dbg !55
  ret i32 %".9", !dbg !55
}

define i32 @"test_dimension_is_auto_false"() !dbg !23
{
entry:
  %".2" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double 0x4024000000000000), !dbg !56
  %".3" = call i32 @"dimension_is_auto"(%"struct.ritz_module_1.Dimension" %".2"), !dbg !57
  %".4" = sext i32 %".3" to i64 , !dbg !57
  %".5" = icmp ne i64 %".4", 0 , !dbg !57
  br i1 %".5", label %"if.then", label %"if.end", !dbg !57
if.then:
  %".7" = trunc i64 1 to i32 , !dbg !58
  ret i32 %".7", !dbg !58
if.end:
  %".9" = trunc i64 0 to i32 , !dbg !59
  ret i32 %".9", !dbg !59
}

define i32 @"test_transform_identity"() !dbg !24
{
entry:
  %".2" = call %"struct.ritz_module_1.Transform" @"transform_identity"(), !dbg !60
  %".3" = extractvalue %"struct.ritz_module_1.Transform" %".2", 0 , !dbg !61
  %".4" = fcmp one double %".3", 0x3ff0000000000000 , !dbg !61
  br i1 %".4", label %"if.then", label %"if.end", !dbg !61
if.then:
  %".6" = trunc i64 1 to i32 , !dbg !62
  ret i32 %".6", !dbg !62
if.end:
  %".8" = extractvalue %"struct.ritz_module_1.Transform" %".2", 3 , !dbg !63
  %".9" = fcmp one double %".8", 0x3ff0000000000000 , !dbg !63
  br i1 %".9", label %"if.then.1", label %"if.end.1", !dbg !63
if.then.1:
  %".11" = trunc i64 2 to i32 , !dbg !64
  ret i32 %".11", !dbg !64
if.end.1:
  %".13" = extractvalue %"struct.ritz_module_1.Transform" %".2", 1 , !dbg !65
  %".14" = fcmp one double %".13",              0x0 , !dbg !65
  br i1 %".14", label %"if.then.2", label %"if.end.2", !dbg !65
if.then.2:
  %".16" = trunc i64 3 to i32 , !dbg !66
  ret i32 %".16", !dbg !66
if.end.2:
  %".18" = extractvalue %"struct.ritz_module_1.Transform" %".2", 2 , !dbg !67
  %".19" = fcmp one double %".18",              0x0 , !dbg !67
  br i1 %".19", label %"if.then.3", label %"if.end.3", !dbg !67
if.then.3:
  %".21" = trunc i64 4 to i32 , !dbg !68
  ret i32 %".21", !dbg !68
if.end.3:
  %".23" = extractvalue %"struct.ritz_module_1.Transform" %".2", 4 , !dbg !69
  %".24" = fcmp one double %".23",              0x0 , !dbg !69
  br i1 %".24", label %"if.then.4", label %"if.end.4", !dbg !69
if.then.4:
  %".26" = trunc i64 5 to i32 , !dbg !70
  ret i32 %".26", !dbg !70
if.end.4:
  %".28" = extractvalue %"struct.ritz_module_1.Transform" %".2", 5 , !dbg !71
  %".29" = fcmp one double %".28",              0x0 , !dbg !71
  br i1 %".29", label %"if.then.5", label %"if.end.5", !dbg !71
if.then.5:
  %".31" = trunc i64 6 to i32 , !dbg !72
  ret i32 %".31", !dbg !72
if.end.5:
  %".33" = trunc i64 0 to i32 , !dbg !73
  ret i32 %".33", !dbg !73
}

define i32 @"test_transform_is_identity"() !dbg !25
{
entry:
  %".2" = call %"struct.ritz_module_1.Transform" @"transform_identity"(), !dbg !74
  %".3" = call i32 @"transform_is_identity"(%"struct.ritz_module_1.Transform" %".2"), !dbg !75
  %".4" = sext i32 %".3" to i64 , !dbg !75
  %".5" = icmp eq i64 %".4", 0 , !dbg !75
  br i1 %".5", label %"if.then", label %"if.end", !dbg !75
if.then:
  %".7" = trunc i64 1 to i32 , !dbg !76
  ret i32 %".7", !dbg !76
if.end:
  %".9" = trunc i64 0 to i32 , !dbg !77
  ret i32 %".9", !dbg !77
}

define i32 @"test_transform_translate"() !dbg !26
{
entry:
  %".2" = call %"struct.ritz_module_1.Transform" @"transform_translate"(double 0x4024000000000000, double 0x4034000000000000), !dbg !78
  %".3" = extractvalue %"struct.ritz_module_1.Transform" %".2", 4 , !dbg !79
  %".4" = fcmp one double %".3", 0x4024000000000000 , !dbg !79
  br i1 %".4", label %"if.then", label %"if.end", !dbg !79
if.then:
  %".6" = trunc i64 1 to i32 , !dbg !80
  ret i32 %".6", !dbg !80
if.end:
  %".8" = extractvalue %"struct.ritz_module_1.Transform" %".2", 5 , !dbg !81
  %".9" = fcmp one double %".8", 0x4034000000000000 , !dbg !81
  br i1 %".9", label %"if.then.1", label %"if.end.1", !dbg !81
if.then.1:
  %".11" = trunc i64 2 to i32 , !dbg !82
  ret i32 %".11", !dbg !82
if.end.1:
  %".13" = call i32 @"transform_is_identity"(%"struct.ritz_module_1.Transform" %".2"), !dbg !83
  %".14" = sext i32 %".13" to i64 , !dbg !83
  %".15" = icmp ne i64 %".14", 0 , !dbg !83
  br i1 %".15", label %"if.then.2", label %"if.end.2", !dbg !83
if.then.2:
  %".17" = trunc i64 3 to i32 , !dbg !84
  ret i32 %".17", !dbg !84
if.end.2:
  %".19" = trunc i64 0 to i32 , !dbg !85
  ret i32 %".19", !dbg !85
}

define i32 @"test_computed_style_default"() !dbg !27
{
entry:
  %".2" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !86
  %".3" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".2", 0 , !dbg !87
  %".4" = icmp ne i32 %".3", 1 , !dbg !87
  br i1 %".4", label %"if.then", label %"if.end", !dbg !87
if.then:
  %".6" = trunc i64 1 to i32 , !dbg !88
  ret i32 %".6", !dbg !88
if.end:
  %".8" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".2", 1 , !dbg !89
  %".9" = icmp ne i32 %".8", 0 , !dbg !89
  br i1 %".9", label %"if.then.1", label %"if.end.1", !dbg !89
if.then.1:
  %".11" = trunc i64 2 to i32 , !dbg !90
  ret i32 %".11", !dbg !90
if.end.1:
  %".13" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".2", 19 , !dbg !91
  %".14" = fcmp one double %".13", 0x3ff0000000000000 , !dbg !91
  br i1 %".14", label %"if.then.2", label %"if.end.2", !dbg !91
if.then.2:
  %".16" = trunc i64 3 to i32 , !dbg !92
  ret i32 %".16", !dbg !92
if.end.2:
  %".18" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".2", 16 , !dbg !93
  %".19" = extractvalue %"struct.ritz_module_1.TextStyle" %".18", 0 , !dbg !93
  %".20" = fcmp one double %".19", 0x4030000000000000 , !dbg !93
  br i1 %".20", label %"if.then.3", label %"if.end.3", !dbg !93
if.then.3:
  %".22" = trunc i64 4 to i32 , !dbg !94
  ret i32 %".22", !dbg !94
if.end.3:
  %".24" = trunc i64 0 to i32 , !dbg !95
  ret i32 %".24", !dbg !95
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/tests", filename: "test_style_types.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 11, name: "test_node_id_new", scopeLine: 11, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 18, name: "test_node_id_invalid", scopeLine: 18, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 25, name: "test_node_id_valid", scopeLine: 25, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 36, name: "test_dimension_px", scopeLine: 36, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 45, name: "test_dimension_percent", scopeLine: 45, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 54, name: "test_dimension_auto", scopeLine: 54, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 61, name: "test_dimension_is_auto_false", scopeLine: 61, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 72, name: "test_transform_identity", scopeLine: 72, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 89, name: "test_transform_is_identity", scopeLine: 89, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 96, name: "test_transform_translate", scopeLine: 96, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 111, name: "test_computed_style_default", scopeLine: 111, type: !4, unit: !1)
!28 = !DILocation(column: 5, line: 12, scope: !17)
!29 = !DILocation(column: 5, line: 13, scope: !17)
!30 = !DILocation(column: 9, line: 14, scope: !17)
!31 = !DILocation(column: 5, line: 15, scope: !17)
!32 = !DILocation(column: 5, line: 19, scope: !18)
!33 = !DILocation(column: 5, line: 20, scope: !18)
!34 = !DILocation(column: 9, line: 21, scope: !18)
!35 = !DILocation(column: 5, line: 22, scope: !18)
!36 = !DILocation(column: 5, line: 26, scope: !19)
!37 = !DILocation(column: 5, line: 27, scope: !19)
!38 = !DILocation(column: 9, line: 28, scope: !19)
!39 = !DILocation(column: 5, line: 29, scope: !19)
!40 = !DILocation(column: 5, line: 37, scope: !20)
!41 = !DILocation(column: 5, line: 38, scope: !20)
!42 = !DILocation(column: 9, line: 39, scope: !20)
!43 = !DILocation(column: 5, line: 40, scope: !20)
!44 = !DILocation(column: 9, line: 41, scope: !20)
!45 = !DILocation(column: 5, line: 42, scope: !20)
!46 = !DILocation(column: 5, line: 46, scope: !21)
!47 = !DILocation(column: 5, line: 47, scope: !21)
!48 = !DILocation(column: 9, line: 48, scope: !21)
!49 = !DILocation(column: 5, line: 49, scope: !21)
!50 = !DILocation(column: 9, line: 50, scope: !21)
!51 = !DILocation(column: 5, line: 51, scope: !21)
!52 = !DILocation(column: 5, line: 55, scope: !22)
!53 = !DILocation(column: 5, line: 56, scope: !22)
!54 = !DILocation(column: 9, line: 57, scope: !22)
!55 = !DILocation(column: 5, line: 58, scope: !22)
!56 = !DILocation(column: 5, line: 62, scope: !23)
!57 = !DILocation(column: 5, line: 63, scope: !23)
!58 = !DILocation(column: 9, line: 64, scope: !23)
!59 = !DILocation(column: 5, line: 65, scope: !23)
!60 = !DILocation(column: 5, line: 73, scope: !24)
!61 = !DILocation(column: 5, line: 74, scope: !24)
!62 = !DILocation(column: 9, line: 75, scope: !24)
!63 = !DILocation(column: 5, line: 76, scope: !24)
!64 = !DILocation(column: 9, line: 77, scope: !24)
!65 = !DILocation(column: 5, line: 78, scope: !24)
!66 = !DILocation(column: 9, line: 79, scope: !24)
!67 = !DILocation(column: 5, line: 80, scope: !24)
!68 = !DILocation(column: 9, line: 81, scope: !24)
!69 = !DILocation(column: 5, line: 82, scope: !24)
!70 = !DILocation(column: 9, line: 83, scope: !24)
!71 = !DILocation(column: 5, line: 84, scope: !24)
!72 = !DILocation(column: 9, line: 85, scope: !24)
!73 = !DILocation(column: 5, line: 86, scope: !24)
!74 = !DILocation(column: 5, line: 90, scope: !25)
!75 = !DILocation(column: 5, line: 91, scope: !25)
!76 = !DILocation(column: 9, line: 92, scope: !25)
!77 = !DILocation(column: 5, line: 93, scope: !25)
!78 = !DILocation(column: 5, line: 97, scope: !26)
!79 = !DILocation(column: 5, line: 98, scope: !26)
!80 = !DILocation(column: 9, line: 99, scope: !26)
!81 = !DILocation(column: 5, line: 100, scope: !26)
!82 = !DILocation(column: 9, line: 101, scope: !26)
!83 = !DILocation(column: 5, line: 102, scope: !26)
!84 = !DILocation(column: 9, line: 103, scope: !26)
!85 = !DILocation(column: 5, line: 104, scope: !26)
!86 = !DILocation(column: 5, line: 112, scope: !27)
!87 = !DILocation(column: 5, line: 115, scope: !27)
!88 = !DILocation(column: 9, line: 116, scope: !27)
!89 = !DILocation(column: 5, line: 119, scope: !27)
!90 = !DILocation(column: 9, line: 120, scope: !27)
!91 = !DILocation(column: 5, line: 123, scope: !27)
!92 = !DILocation(column: 9, line: 124, scope: !27)
!93 = !DILocation(column: 5, line: 127, scope: !27)
!94 = !DILocation(column: 9, line: 128, scope: !27)
!95 = !DILocation(column: 5, line: 130, scope: !27)