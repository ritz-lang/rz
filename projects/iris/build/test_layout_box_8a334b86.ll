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
%"struct.ritz_module_1.LayoutConstraints" = type {double, double, double, double, double, double, i32, i32}
%"struct.ritz_module_1.BoxDimensions" = type {double, double, double, double, double, double, double, double, double, double, double, double, double, double}
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

declare %"struct.ritz_module_1.LayoutConstraints" @"layout_constraints_new"(double %".1", double %".2", double %".3")

declare double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %".1", %"struct.ritz_module_1.LayoutConstraints"* %".2", i32 %".3")

declare double @"resolve_dimension_or"(%"struct.ritz_module_1.Dimension"* %".1", %"struct.ritz_module_1.LayoutConstraints"* %".2", i32 %".3", double %".4")

declare %"struct.ritz_module_1.BoxDimensions" @"box_dimensions_zero"()

declare double @"box_dimensions_border_width"(%"struct.ritz_module_1.BoxDimensions"* %".1")

declare double @"box_dimensions_border_height"(%"struct.ritz_module_1.BoxDimensions"* %".1")

declare double @"box_dimensions_margin_width"(%"struct.ritz_module_1.BoxDimensions"* %".1")

declare double @"box_dimensions_margin_height"(%"struct.ritz_module_1.BoxDimensions"* %".1")

declare %"struct.ritz_module_1.BoxDimensions" @"resolve_padding"(%"struct.ritz_module_1.ComputedStyle"* %".1", %"struct.ritz_module_1.LayoutConstraints"* %".2")

declare %"struct.ritz_module_1.BoxDimensions" @"resolve_border"(%"struct.ritz_module_1.ComputedStyle"* %".1", %"struct.ritz_module_1.LayoutConstraints"* %".2")

declare %"struct.ritz_module_1.BoxDimensions" @"resolve_margin"(%"struct.ritz_module_1.ComputedStyle"* %".1", %"struct.ritz_module_1.LayoutConstraints"* %".2")

declare %"struct.ritz_module_1.BoxDimensions" @"resolve_box_model"(%"struct.ritz_module_1.ComputedStyle"* %".1", %"struct.ritz_module_1.LayoutConstraints"* %".2")

define i32 @"test_resolve_dimension_px"() !dbg !17
{
entry:
  %".2" = call %"struct.ritz_module_1.LayoutConstraints" @"layout_constraints_new"(double 0x4089000000000000, double 0x4082c00000000000, double 0x4030000000000000), !dbg !26
  %".3" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double 0x4059000000000000), !dbg !27
  %"d.addr" = alloca %"struct.ritz_module_1.Dimension", !dbg !28
  store %"struct.ritz_module_1.Dimension" %".3", %"struct.ritz_module_1.Dimension"* %"d.addr", !dbg !28
  %"constraints.addr" = alloca %"struct.ritz_module_1.LayoutConstraints", !dbg !28
  store %"struct.ritz_module_1.LayoutConstraints" %".2", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr", !dbg !28
  %".6" = trunc i64 1 to i32 , !dbg !28
  %".7" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %"d.addr", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr", i32 %".6"), !dbg !28
  %".8" = fcmp one double %".7", 0x4059000000000000 , !dbg !29
  br i1 %".8", label %"if.then", label %"if.end", !dbg !29
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !30
  ret i32 %".10", !dbg !30
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !31
  ret i32 %".12", !dbg !31
}

define i32 @"test_resolve_dimension_percent_width"() !dbg !18
{
entry:
  %".2" = call %"struct.ritz_module_1.LayoutConstraints" @"layout_constraints_new"(double 0x4089000000000000, double 0x4082c00000000000, double 0x4030000000000000), !dbg !32
  %".3" = call %"struct.ritz_module_1.Dimension" @"dimension_percent"(double 0x4049000000000000), !dbg !33
  %"d.addr" = alloca %"struct.ritz_module_1.Dimension", !dbg !34
  store %"struct.ritz_module_1.Dimension" %".3", %"struct.ritz_module_1.Dimension"* %"d.addr", !dbg !34
  %"constraints.addr" = alloca %"struct.ritz_module_1.LayoutConstraints", !dbg !34
  store %"struct.ritz_module_1.LayoutConstraints" %".2", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr", !dbg !34
  %".6" = trunc i64 1 to i32 , !dbg !34
  %".7" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %"d.addr", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr", i32 %".6"), !dbg !34
  %".8" = fcmp one double %".7", 0x4079000000000000 , !dbg !35
  br i1 %".8", label %"if.then", label %"if.end", !dbg !35
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !36
  ret i32 %".10", !dbg !36
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !37
  ret i32 %".12", !dbg !37
}

define i32 @"test_resolve_dimension_percent_height"() !dbg !19
{
entry:
  %".2" = call %"struct.ritz_module_1.LayoutConstraints" @"layout_constraints_new"(double 0x4089000000000000, double 0x4082c00000000000, double 0x4030000000000000), !dbg !38
  %".3" = call %"struct.ritz_module_1.Dimension" @"dimension_percent"(double 0x4049000000000000), !dbg !39
  %"d.addr" = alloca %"struct.ritz_module_1.Dimension", !dbg !40
  store %"struct.ritz_module_1.Dimension" %".3", %"struct.ritz_module_1.Dimension"* %"d.addr", !dbg !40
  %"constraints.addr" = alloca %"struct.ritz_module_1.LayoutConstraints", !dbg !40
  store %"struct.ritz_module_1.LayoutConstraints" %".2", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr", !dbg !40
  %".6" = trunc i64 0 to i32 , !dbg !40
  %".7" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %"d.addr", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr", i32 %".6"), !dbg !40
  %".8" = fcmp one double %".7", 0x4072c00000000000 , !dbg !41
  br i1 %".8", label %"if.then", label %"if.end", !dbg !41
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !42
  ret i32 %".10", !dbg !42
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !43
  ret i32 %".12", !dbg !43
}

define i32 @"test_resolve_dimension_auto_fallback"() !dbg !20
{
entry:
  %".2" = call %"struct.ritz_module_1.LayoutConstraints" @"layout_constraints_new"(double 0x4089000000000000, double 0x4082c00000000000, double 0x4030000000000000), !dbg !44
  %".3" = call %"struct.ritz_module_1.Dimension" @"dimension_auto"(), !dbg !45
  %"d.addr" = alloca %"struct.ritz_module_1.Dimension", !dbg !46
  store %"struct.ritz_module_1.Dimension" %".3", %"struct.ritz_module_1.Dimension"* %"d.addr", !dbg !46
  %"constraints.addr" = alloca %"struct.ritz_module_1.LayoutConstraints", !dbg !46
  store %"struct.ritz_module_1.LayoutConstraints" %".2", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr", !dbg !46
  %".6" = trunc i64 1 to i32 , !dbg !46
  %".7" = call double @"resolve_dimension_or"(%"struct.ritz_module_1.Dimension"* %"d.addr", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr", i32 %".6", double 0x408f380000000000), !dbg !46
  %".8" = fcmp one double %".7", 0x408f380000000000 , !dbg !47
  br i1 %".8", label %"if.then", label %"if.end", !dbg !47
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !48
  ret i32 %".10", !dbg !48
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !49
  ret i32 %".12", !dbg !49
}

define i32 @"test_box_dimensions_zero"() !dbg !21
{
entry:
  %".2" = call %"struct.ritz_module_1.BoxDimensions" @"box_dimensions_zero"(), !dbg !50
  %".3" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".2", 0 , !dbg !51
  %".4" = fcmp one double %".3",              0x0 , !dbg !51
  br i1 %".4", label %"if.then", label %"if.end", !dbg !51
if.then:
  %".6" = trunc i64 1 to i32 , !dbg !52
  ret i32 %".6", !dbg !52
if.end:
  %".8" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".2", 1 , !dbg !53
  %".9" = fcmp one double %".8",              0x0 , !dbg !53
  br i1 %".9", label %"if.then.1", label %"if.end.1", !dbg !53
if.then.1:
  %".11" = trunc i64 2 to i32 , !dbg !54
  ret i32 %".11", !dbg !54
if.end.1:
  %".13" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".2", 2 , !dbg !55
  %".14" = fcmp one double %".13",              0x0 , !dbg !55
  br i1 %".14", label %"if.then.2", label %"if.end.2", !dbg !55
if.then.2:
  %".16" = trunc i64 3 to i32 , !dbg !56
  ret i32 %".16", !dbg !56
if.end.2:
  %".18" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".2", 13 , !dbg !57
  %".19" = fcmp one double %".18",              0x0 , !dbg !57
  br i1 %".19", label %"if.then.3", label %"if.end.3", !dbg !57
if.then.3:
  %".21" = trunc i64 4 to i32 , !dbg !58
  ret i32 %".21", !dbg !58
if.end.3:
  %".23" = trunc i64 0 to i32 , !dbg !59
  ret i32 %".23", !dbg !59
}

define i32 @"test_box_dimensions_border_width"() !dbg !22
{
entry:
  %"box.addr" = alloca %"struct.ritz_module_1.BoxDimensions", !dbg !60
  %".2" = call %"struct.ritz_module_1.BoxDimensions" @"box_dimensions_zero"(), !dbg !60
  store %"struct.ritz_module_1.BoxDimensions" %".2", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !60
  %".4" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !61
  %".5" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", i32 0, i32 0 , !dbg !61
  store double 0x4059000000000000, double* %".5", !dbg !61
  %".7" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !62
  %".8" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", i32 0, i32 5 , !dbg !62
  store double 0x4024000000000000, double* %".8", !dbg !62
  %".10" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !63
  %".11" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", i32 0, i32 3 , !dbg !63
  store double 0x4024000000000000, double* %".11", !dbg !63
  %".13" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !64
  %".14" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", i32 0, i32 9 , !dbg !64
  store double 0x3ff0000000000000, double* %".14", !dbg !64
  %".16" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !65
  %".17" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", i32 0, i32 7 , !dbg !65
  store double 0x3ff0000000000000, double* %".17", !dbg !65
  %".19" = call double @"box_dimensions_border_width"(%"struct.ritz_module_1.BoxDimensions"* %"box.addr"), !dbg !66
  %".20" = fcmp one double %".19", 0x405e800000000000 , !dbg !67
  br i1 %".20", label %"if.then", label %"if.end", !dbg !67
if.then:
  %".22" = trunc i64 1 to i32 , !dbg !68
  ret i32 %".22", !dbg !68
if.end:
  %".24" = trunc i64 0 to i32 , !dbg !69
  ret i32 %".24", !dbg !69
}

define i32 @"test_box_dimensions_margin_width"() !dbg !23
{
entry:
  %"box.addr" = alloca %"struct.ritz_module_1.BoxDimensions", !dbg !70
  %".2" = call %"struct.ritz_module_1.BoxDimensions" @"box_dimensions_zero"(), !dbg !70
  store %"struct.ritz_module_1.BoxDimensions" %".2", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !70
  %".4" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !71
  %".5" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", i32 0, i32 0 , !dbg !71
  store double 0x4059000000000000, double* %".5", !dbg !71
  %".7" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !72
  %".8" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", i32 0, i32 5 , !dbg !72
  store double 0x4024000000000000, double* %".8", !dbg !72
  %".10" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !73
  %".11" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", i32 0, i32 3 , !dbg !73
  store double 0x4024000000000000, double* %".11", !dbg !73
  %".13" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !74
  %".14" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", i32 0, i32 9 , !dbg !74
  store double 0x3ff0000000000000, double* %".14", !dbg !74
  %".16" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !75
  %".17" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", i32 0, i32 7 , !dbg !75
  store double 0x3ff0000000000000, double* %".17", !dbg !75
  %".19" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !76
  %".20" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", i32 0, i32 13 , !dbg !76
  store double 0x4034000000000000, double* %".20", !dbg !76
  %".22" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", !dbg !77
  %".23" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"box.addr", i32 0, i32 11 , !dbg !77
  store double 0x4034000000000000, double* %".23", !dbg !77
  %".25" = call double @"box_dimensions_margin_width"(%"struct.ritz_module_1.BoxDimensions"* %"box.addr"), !dbg !78
  %".26" = fcmp one double %".25", 0x4064400000000000 , !dbg !79
  br i1 %".26", label %"if.then", label %"if.end", !dbg !79
if.then:
  %".28" = trunc i64 1 to i32 , !dbg !80
  ret i32 %".28", !dbg !80
if.end:
  %".30" = trunc i64 0 to i32 , !dbg !81
  ret i32 %".30", !dbg !81
}

define i32 @"test_resolve_box_model_simple"() !dbg !24
{
entry:
  %"style.addr" = alloca %"struct.ritz_module_1.ComputedStyle", !dbg !83
  %".2" = call %"struct.ritz_module_1.LayoutConstraints" @"layout_constraints_new"(double 0x4089000000000000, double 0x4082c00000000000, double 0x4030000000000000), !dbg !82
  %".3" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !83
  store %"struct.ritz_module_1.ComputedStyle" %".3", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", !dbg !83
  %".5" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double 0x4069000000000000), !dbg !84
  %".6" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", !dbg !84
  %".7" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 7 , !dbg !84
  store %"struct.ritz_module_1.Dimension" %".5", %"struct.ritz_module_1.Dimension"* %".7", !dbg !84
  %".9" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double 0x4059000000000000), !dbg !85
  %".10" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", !dbg !85
  %".11" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 8 , !dbg !85
  store %"struct.ritz_module_1.Dimension" %".9", %"struct.ritz_module_1.Dimension"* %".11", !dbg !85
  %".13" = call %"struct.ritz_module_1.EdgeSizes" @"edge_sizes_all"(double 0x4024000000000000), !dbg !86
  %".14" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", !dbg !86
  %".15" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 14 , !dbg !86
  store %"struct.ritz_module_1.EdgeSizes" %".13", %"struct.ritz_module_1.EdgeSizes"* %".15", !dbg !86
  %"constraints.addr" = alloca %"struct.ritz_module_1.LayoutConstraints", !dbg !87
  store %"struct.ritz_module_1.LayoutConstraints" %".2", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr", !dbg !87
  %".18" = call %"struct.ritz_module_1.BoxDimensions" @"resolve_box_model"(%"struct.ritz_module_1.ComputedStyle"* %"style.addr", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr"), !dbg !87
  %".19" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".18", 0 , !dbg !88
  %".20" = fcmp one double %".19", 0x4069000000000000 , !dbg !88
  br i1 %".20", label %"if.then", label %"if.end", !dbg !88
if.then:
  %".22" = trunc i64 1 to i32 , !dbg !89
  ret i32 %".22", !dbg !89
if.end:
  %".24" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".18", 1 , !dbg !90
  %".25" = fcmp one double %".24", 0x4059000000000000 , !dbg !90
  br i1 %".25", label %"if.then.1", label %"if.end.1", !dbg !90
if.then.1:
  %".27" = trunc i64 2 to i32 , !dbg !91
  ret i32 %".27", !dbg !91
if.end.1:
  %".29" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".18", 2 , !dbg !92
  %".30" = fcmp one double %".29", 0x4024000000000000 , !dbg !92
  br i1 %".30", label %"if.then.2", label %"if.end.2", !dbg !92
if.then.2:
  %".32" = trunc i64 3 to i32 , !dbg !93
  ret i32 %".32", !dbg !93
if.end.2:
  %".34" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".18", 3 , !dbg !94
  %".35" = fcmp one double %".34", 0x4024000000000000 , !dbg !94
  br i1 %".35", label %"if.then.3", label %"if.end.3", !dbg !94
if.then.3:
  %".37" = trunc i64 4 to i32 , !dbg !95
  ret i32 %".37", !dbg !95
if.end.3:
  %".39" = trunc i64 0 to i32 , !dbg !96
  ret i32 %".39", !dbg !96
}

define i32 @"test_resolve_box_model_border_box"() !dbg !25
{
entry:
  %"style.addr" = alloca %"struct.ritz_module_1.ComputedStyle", !dbg !98
  %".2" = call %"struct.ritz_module_1.LayoutConstraints" @"layout_constraints_new"(double 0x4089000000000000, double 0x4082c00000000000, double 0x4030000000000000), !dbg !97
  %".3" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !98
  store %"struct.ritz_module_1.ComputedStyle" %".3", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", !dbg !98
  %".5" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", !dbg !99
  %".6" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 2 , !dbg !99
  store i32 1, i32* %".6", !dbg !99
  %".8" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double 0x4069000000000000), !dbg !100
  %".9" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", !dbg !100
  %".10" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 7 , !dbg !100
  store %"struct.ritz_module_1.Dimension" %".8", %"struct.ritz_module_1.Dimension"* %".10", !dbg !100
  %".12" = call %"struct.ritz_module_1.EdgeSizes" @"edge_sizes_all"(double 0x4034000000000000), !dbg !101
  %".13" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", !dbg !101
  %".14" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 14 , !dbg !101
  store %"struct.ritz_module_1.EdgeSizes" %".12", %"struct.ritz_module_1.EdgeSizes"* %".14", !dbg !101
  %".16" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 15 , !dbg !102
  %".17" = load %"struct.ritz_module_1.Border", %"struct.ritz_module_1.Border"* %".16", !dbg !102
  %".18" = extractvalue %"struct.ritz_module_1.Border" %".17", 0 , !dbg !102
  %".19" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 15 , !dbg !102
  %".20" = getelementptr %"struct.ritz_module_1.Border", %"struct.ritz_module_1.Border"* %".19", i32 0, i32 0 , !dbg !102
  %".21" = getelementptr %"struct.ritz_module_1.BorderEdge", %"struct.ritz_module_1.BorderEdge"* %".20", i32 0, i32 0 , !dbg !102
  store double 0x4000000000000000, double* %".21", !dbg !102
  %".23" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 15 , !dbg !103
  %".24" = load %"struct.ritz_module_1.Border", %"struct.ritz_module_1.Border"* %".23", !dbg !103
  %".25" = extractvalue %"struct.ritz_module_1.Border" %".24", 1 , !dbg !103
  %".26" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 15 , !dbg !103
  %".27" = getelementptr %"struct.ritz_module_1.Border", %"struct.ritz_module_1.Border"* %".26", i32 0, i32 1 , !dbg !103
  %".28" = getelementptr %"struct.ritz_module_1.BorderEdge", %"struct.ritz_module_1.BorderEdge"* %".27", i32 0, i32 0 , !dbg !103
  store double 0x4000000000000000, double* %".28", !dbg !103
  %".30" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 15 , !dbg !104
  %".31" = load %"struct.ritz_module_1.Border", %"struct.ritz_module_1.Border"* %".30", !dbg !104
  %".32" = extractvalue %"struct.ritz_module_1.Border" %".31", 2 , !dbg !104
  %".33" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 15 , !dbg !104
  %".34" = getelementptr %"struct.ritz_module_1.Border", %"struct.ritz_module_1.Border"* %".33", i32 0, i32 2 , !dbg !104
  %".35" = getelementptr %"struct.ritz_module_1.BorderEdge", %"struct.ritz_module_1.BorderEdge"* %".34", i32 0, i32 0 , !dbg !104
  store double 0x4000000000000000, double* %".35", !dbg !104
  %".37" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 15 , !dbg !105
  %".38" = load %"struct.ritz_module_1.Border", %"struct.ritz_module_1.Border"* %".37", !dbg !105
  %".39" = extractvalue %"struct.ritz_module_1.Border" %".38", 3 , !dbg !105
  %".40" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.addr", i32 0, i32 15 , !dbg !105
  %".41" = getelementptr %"struct.ritz_module_1.Border", %"struct.ritz_module_1.Border"* %".40", i32 0, i32 3 , !dbg !105
  %".42" = getelementptr %"struct.ritz_module_1.BorderEdge", %"struct.ritz_module_1.BorderEdge"* %".41", i32 0, i32 0 , !dbg !105
  store double 0x4000000000000000, double* %".42", !dbg !105
  %"constraints.addr" = alloca %"struct.ritz_module_1.LayoutConstraints", !dbg !106
  store %"struct.ritz_module_1.LayoutConstraints" %".2", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr", !dbg !106
  %".45" = call %"struct.ritz_module_1.BoxDimensions" @"resolve_box_model"(%"struct.ritz_module_1.ComputedStyle"* %"style.addr", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr"), !dbg !106
  %".46" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".45", 0 , !dbg !107
  %".47" = fcmp one double %".46", 0x4063800000000000 , !dbg !107
  br i1 %".47", label %"if.then", label %"if.end", !dbg !107
if.then:
  %".49" = trunc i64 1 to i32 , !dbg !108
  ret i32 %".49", !dbg !108
if.end:
  %".51" = trunc i64 0 to i32 , !dbg !109
  ret i32 %".51", !dbg !109
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/tests", filename: "test_layout_box.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 12, name: "test_resolve_dimension_px", scopeLine: 12, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 22, name: "test_resolve_dimension_percent_width", scopeLine: 22, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 33, name: "test_resolve_dimension_percent_height", scopeLine: 33, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 44, name: "test_resolve_dimension_auto_fallback", scopeLine: 44, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 58, name: "test_box_dimensions_zero", scopeLine: 58, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 71, name: "test_box_dimensions_border_width", scopeLine: 71, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 86, name: "test_box_dimensions_margin_width", scopeLine: 86, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 107, name: "test_resolve_box_model_simple", scopeLine: 107, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 128, name: "test_resolve_box_model_border_box", scopeLine: 128, type: !4, unit: !1)
!26 = !DILocation(column: 5, line: 13, scope: !17)
!27 = !DILocation(column: 5, line: 14, scope: !17)
!28 = !DILocation(column: 5, line: 16, scope: !17)
!29 = !DILocation(column: 5, line: 17, scope: !17)
!30 = !DILocation(column: 9, line: 18, scope: !17)
!31 = !DILocation(column: 5, line: 19, scope: !17)
!32 = !DILocation(column: 5, line: 23, scope: !18)
!33 = !DILocation(column: 5, line: 24, scope: !18)
!34 = !DILocation(column: 5, line: 26, scope: !18)
!35 = !DILocation(column: 5, line: 28, scope: !18)
!36 = !DILocation(column: 9, line: 29, scope: !18)
!37 = !DILocation(column: 5, line: 30, scope: !18)
!38 = !DILocation(column: 5, line: 34, scope: !19)
!39 = !DILocation(column: 5, line: 35, scope: !19)
!40 = !DILocation(column: 5, line: 37, scope: !19)
!41 = !DILocation(column: 5, line: 39, scope: !19)
!42 = !DILocation(column: 9, line: 40, scope: !19)
!43 = !DILocation(column: 5, line: 41, scope: !19)
!44 = !DILocation(column: 5, line: 45, scope: !20)
!45 = !DILocation(column: 5, line: 46, scope: !20)
!46 = !DILocation(column: 5, line: 48, scope: !20)
!47 = !DILocation(column: 5, line: 49, scope: !20)
!48 = !DILocation(column: 9, line: 50, scope: !20)
!49 = !DILocation(column: 5, line: 51, scope: !20)
!50 = !DILocation(column: 5, line: 59, scope: !21)
!51 = !DILocation(column: 5, line: 60, scope: !21)
!52 = !DILocation(column: 9, line: 61, scope: !21)
!53 = !DILocation(column: 5, line: 62, scope: !21)
!54 = !DILocation(column: 9, line: 63, scope: !21)
!55 = !DILocation(column: 5, line: 64, scope: !21)
!56 = !DILocation(column: 9, line: 65, scope: !21)
!57 = !DILocation(column: 5, line: 66, scope: !21)
!58 = !DILocation(column: 9, line: 67, scope: !21)
!59 = !DILocation(column: 5, line: 68, scope: !21)
!60 = !DILocation(column: 5, line: 72, scope: !22)
!61 = !DILocation(column: 5, line: 73, scope: !22)
!62 = !DILocation(column: 5, line: 74, scope: !22)
!63 = !DILocation(column: 5, line: 75, scope: !22)
!64 = !DILocation(column: 5, line: 76, scope: !22)
!65 = !DILocation(column: 5, line: 77, scope: !22)
!66 = !DILocation(column: 5, line: 79, scope: !22)
!67 = !DILocation(column: 5, line: 81, scope: !22)
!68 = !DILocation(column: 9, line: 82, scope: !22)
!69 = !DILocation(column: 5, line: 83, scope: !22)
!70 = !DILocation(column: 5, line: 87, scope: !23)
!71 = !DILocation(column: 5, line: 88, scope: !23)
!72 = !DILocation(column: 5, line: 89, scope: !23)
!73 = !DILocation(column: 5, line: 90, scope: !23)
!74 = !DILocation(column: 5, line: 91, scope: !23)
!75 = !DILocation(column: 5, line: 92, scope: !23)
!76 = !DILocation(column: 5, line: 93, scope: !23)
!77 = !DILocation(column: 5, line: 94, scope: !23)
!78 = !DILocation(column: 5, line: 96, scope: !23)
!79 = !DILocation(column: 5, line: 98, scope: !23)
!80 = !DILocation(column: 9, line: 99, scope: !23)
!81 = !DILocation(column: 5, line: 100, scope: !23)
!82 = !DILocation(column: 5, line: 108, scope: !24)
!83 = !DILocation(column: 5, line: 110, scope: !24)
!84 = !DILocation(column: 5, line: 111, scope: !24)
!85 = !DILocation(column: 5, line: 112, scope: !24)
!86 = !DILocation(column: 5, line: 113, scope: !24)
!87 = !DILocation(column: 5, line: 115, scope: !24)
!88 = !DILocation(column: 5, line: 117, scope: !24)
!89 = !DILocation(column: 9, line: 118, scope: !24)
!90 = !DILocation(column: 5, line: 119, scope: !24)
!91 = !DILocation(column: 9, line: 120, scope: !24)
!92 = !DILocation(column: 5, line: 121, scope: !24)
!93 = !DILocation(column: 9, line: 122, scope: !24)
!94 = !DILocation(column: 5, line: 123, scope: !24)
!95 = !DILocation(column: 9, line: 124, scope: !24)
!96 = !DILocation(column: 5, line: 125, scope: !24)
!97 = !DILocation(column: 5, line: 129, scope: !25)
!98 = !DILocation(column: 5, line: 131, scope: !25)
!99 = !DILocation(column: 5, line: 132, scope: !25)
!100 = !DILocation(column: 5, line: 133, scope: !25)
!101 = !DILocation(column: 5, line: 134, scope: !25)
!102 = !DILocation(column: 5, line: 135, scope: !25)
!103 = !DILocation(column: 5, line: 136, scope: !25)
!104 = !DILocation(column: 5, line: 137, scope: !25)
!105 = !DILocation(column: 5, line: 138, scope: !25)
!106 = !DILocation(column: 5, line: 140, scope: !25)
!107 = !DILocation(column: 5, line: 143, scope: !25)
!108 = !DILocation(column: 9, line: 144, scope: !25)
!109 = !DILocation(column: 5, line: 145, scope: !25)