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

define %"struct.ritz_module_1.LayoutConstraints" @"layout_constraints_new"(double %"vp_width.arg", double %"vp_height.arg", double %"root_font_size.arg") !dbg !17
{
entry:
  %"vp_width" = alloca double
  %"c.addr" = alloca %"struct.ritz_module_1.LayoutConstraints", !dbg !29
  store double %"vp_width.arg", double* %"vp_width"
  %"vp_height" = alloca double
  store double %"vp_height.arg", double* %"vp_height"
  %"root_font_size" = alloca double
  store double %"root_font_size.arg", double* %"root_font_size"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", metadata !31, metadata !7), !dbg !32
  %".9" = load double, double* %"vp_width", !dbg !33
  %".10" = load %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", !dbg !33
  %".11" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", i32 0, i32 0 , !dbg !33
  store double %".9", double* %".11", !dbg !33
  %".13" = load double, double* %"vp_height", !dbg !34
  %".14" = load %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", !dbg !34
  %".15" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", i32 0, i32 1 , !dbg !34
  store double %".13", double* %".15", !dbg !34
  %".17" = load double, double* %"vp_width", !dbg !35
  %".18" = load %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", !dbg !35
  %".19" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", i32 0, i32 2 , !dbg !35
  store double %".17", double* %".19", !dbg !35
  %".21" = load double, double* %"vp_height", !dbg !36
  %".22" = load %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", !dbg !36
  %".23" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", i32 0, i32 3 , !dbg !36
  store double %".21", double* %".23", !dbg !36
  %".25" = load double, double* %"root_font_size", !dbg !37
  %".26" = load %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", !dbg !37
  %".27" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", i32 0, i32 4 , !dbg !37
  store double %".25", double* %".27", !dbg !37
  %".29" = load double, double* %"root_font_size", !dbg !38
  %".30" = load %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", !dbg !38
  %".31" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", i32 0, i32 5 , !dbg !38
  store double %".29", double* %".31", !dbg !38
  %".33" = load %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", !dbg !39
  %".34" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", i32 0, i32 6 , !dbg !39
  %".35" = trunc i64 1 to i32 , !dbg !39
  store i32 %".35", i32* %".34", !dbg !39
  %".37" = load %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", !dbg !40
  %".38" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", i32 0, i32 7 , !dbg !40
  %".39" = trunc i64 1 to i32 , !dbg !40
  store i32 %".39", i32* %".38", !dbg !40
  %".41" = load %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.addr", !dbg !41
  ret %"struct.ritz_module_1.LayoutConstraints" %".41", !dbg !41
}

define double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %"dim.arg", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %"for_width.arg") !dbg !18
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Dimension"* %"dim.arg", metadata !44, metadata !7), !dbg !45
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", metadata !47, metadata !7), !dbg !45
  %"for_width" = alloca i32
  store i32 %"for_width.arg", i32* %"for_width"
  call void @"llvm.dbg.declare"(metadata i32* %"for_width", metadata !48, metadata !7), !dbg !45
  %".9" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 1 , !dbg !49
  %".10" = load i32, i32* %".9", !dbg !49
  %".11" = icmp eq i32 %".10", 0 , !dbg !49
  br i1 %".11", label %"if.then", label %"if.end", !dbg !49
if.then:
  %".13" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 0 , !dbg !50
  %".14" = load double, double* %".13", !dbg !50
  ret double %".14", !dbg !50
if.end:
  %".16" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 1 , !dbg !51
  %".17" = load i32, i32* %".16", !dbg !51
  %".18" = icmp eq i32 %".17", 1 , !dbg !51
  br i1 %".18", label %"if.then.1", label %"if.end.1", !dbg !51
if.then.1:
  %".20" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 0 , !dbg !52
  %".21" = load double, double* %".20", !dbg !52
  %".22" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 0, i32 4 , !dbg !52
  %".23" = load double, double* %".22", !dbg !52
  %".24" = fmul double %".21", %".23", !dbg !52
  ret double %".24", !dbg !52
if.end.1:
  %".26" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 1 , !dbg !53
  %".27" = load i32, i32* %".26", !dbg !53
  %".28" = icmp eq i32 %".27", 2 , !dbg !53
  br i1 %".28", label %"if.then.2", label %"if.end.2", !dbg !53
if.then.2:
  %".30" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 0 , !dbg !54
  %".31" = load double, double* %".30", !dbg !54
  %".32" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 0, i32 5 , !dbg !54
  %".33" = load double, double* %".32", !dbg !54
  %".34" = fmul double %".31", %".33", !dbg !54
  ret double %".34", !dbg !54
if.end.2:
  %".36" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 1 , !dbg !55
  %".37" = load i32, i32* %".36", !dbg !55
  %".38" = icmp eq i32 %".37", 3 , !dbg !55
  br i1 %".38", label %"if.then.3", label %"if.end.3", !dbg !55
if.then.3:
  %".40" = load i32, i32* %"for_width", !dbg !55
  %".41" = sext i32 %".40" to i64 , !dbg !55
  %".42" = icmp ne i64 %".41", 0 , !dbg !55
  br i1 %".42", label %"if.then.4", label %"if.else", !dbg !55
if.end.3:
  %".59" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 1 , !dbg !58
  %".60" = load i32, i32* %".59", !dbg !58
  %".61" = icmp eq i32 %".60", 4 , !dbg !58
  br i1 %".61", label %"if.then.5", label %"if.end.5", !dbg !58
if.then.4:
  %".44" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 0 , !dbg !56
  %".45" = load double, double* %".44", !dbg !56
  %".46" = fdiv double %".45", 0x4059000000000000, !dbg !56
  %".47" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 0, i32 0 , !dbg !56
  %".48" = load double, double* %".47", !dbg !56
  %".49" = fmul double %".46", %".48", !dbg !56
  ret double %".49", !dbg !56
if.else:
  %".51" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 0 , !dbg !57
  %".52" = load double, double* %".51", !dbg !57
  %".53" = fdiv double %".52", 0x4059000000000000, !dbg !57
  %".54" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 0, i32 1 , !dbg !57
  %".55" = load double, double* %".54", !dbg !57
  %".56" = fmul double %".53", %".55", !dbg !57
  ret double %".56", !dbg !57
if.end.4:
  br label %"if.end.3", !dbg !57
if.then.5:
  %".63" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 0 , !dbg !59
  %".64" = load double, double* %".63", !dbg !59
  %".65" = fdiv double %".64", 0x4059000000000000, !dbg !59
  %".66" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 0, i32 2 , !dbg !59
  %".67" = load double, double* %".66", !dbg !59
  %".68" = fmul double %".65", %".67", !dbg !59
  ret double %".68", !dbg !59
if.end.5:
  %".70" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 1 , !dbg !60
  %".71" = load i32, i32* %".70", !dbg !60
  %".72" = icmp eq i32 %".71", 5 , !dbg !60
  br i1 %".72", label %"if.then.6", label %"if.end.6", !dbg !60
if.then.6:
  %".74" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 0 , !dbg !61
  %".75" = load double, double* %".74", !dbg !61
  %".76" = fdiv double %".75", 0x4059000000000000, !dbg !61
  %".77" = getelementptr %"struct.ritz_module_1.LayoutConstraints", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 0, i32 3 , !dbg !61
  %".78" = load double, double* %".77", !dbg !61
  %".79" = fmul double %".76", %".78", !dbg !61
  ret double %".79", !dbg !61
if.end.6:
  %".81" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 1 , !dbg !62
  %".82" = load i32, i32* %".81", !dbg !62
  %".83" = icmp eq i32 %".82", 6 , !dbg !62
  br i1 %".83", label %"if.then.7", label %"if.end.7", !dbg !62
if.then.7:
  ret double              0x0, !dbg !63
if.end.7:
  ret double              0x0, !dbg !64
}

define double @"resolve_dimension_or"(%"struct.ritz_module_1.Dimension"* %"dim.arg", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %"for_width.arg", double %"fallback.arg") !dbg !19
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Dimension"* %"dim.arg", metadata !65, metadata !7), !dbg !66
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", metadata !67, metadata !7), !dbg !66
  %"for_width" = alloca i32
  store i32 %"for_width.arg", i32* %"for_width"
  call void @"llvm.dbg.declare"(metadata i32* %"for_width", metadata !68, metadata !7), !dbg !66
  %"fallback" = alloca double
  store double %"fallback.arg", double* %"fallback"
  %".11" = getelementptr %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %"dim.arg", i32 0, i32 1 , !dbg !69
  %".12" = load i32, i32* %".11", !dbg !69
  %".13" = icmp eq i32 %".12", 6 , !dbg !69
  br i1 %".13", label %"if.then", label %"if.end", !dbg !69
if.then:
  %".15" = load double, double* %"fallback", !dbg !70
  ret double %".15", !dbg !70
if.end:
  %".17" = load i32, i32* %"for_width", !dbg !71
  %".18" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %"dim.arg", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".17"), !dbg !71
  ret double %".18", !dbg !71
}

define %"struct.ritz_module_1.BoxDimensions" @"box_dimensions_zero"() !dbg !20
{
entry:
  %".2" = insertvalue %"struct.ritz_module_1.BoxDimensions" undef, double              0x0, 0 , !dbg !72
  %".3" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".2", double              0x0, 1 , !dbg !72
  %".4" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".3", double              0x0, 2 , !dbg !72
  %".5" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".4", double              0x0, 3 , !dbg !72
  %".6" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".5", double              0x0, 4 , !dbg !72
  %".7" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".6", double              0x0, 5 , !dbg !72
  %".8" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".7", double              0x0, 6 , !dbg !72
  %".9" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".8", double              0x0, 7 , !dbg !72
  %".10" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".9", double              0x0, 8 , !dbg !72
  %".11" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".10", double              0x0, 9 , !dbg !72
  %".12" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".11", double              0x0, 10 , !dbg !72
  %".13" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".12", double              0x0, 11 , !dbg !72
  %".14" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".13", double              0x0, 12 , !dbg !72
  %".15" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".14", double              0x0, 13 , !dbg !72
  ret %"struct.ritz_module_1.BoxDimensions" %".15", !dbg !72
}

define double @"box_dimensions_border_width"(%"struct.ritz_module_1.BoxDimensions"* %"b.arg") !dbg !21
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.BoxDimensions"* %"b.arg", metadata !75, metadata !7), !dbg !76
  %".4" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 0 , !dbg !77
  %".5" = load double, double* %".4", !dbg !77
  %".6" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 5 , !dbg !77
  %".7" = load double, double* %".6", !dbg !77
  %".8" = fadd double %".5", %".7", !dbg !77
  %".9" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 3 , !dbg !77
  %".10" = load double, double* %".9", !dbg !77
  %".11" = fadd double %".8", %".10", !dbg !77
  %".12" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 9 , !dbg !77
  %".13" = load double, double* %".12", !dbg !77
  %".14" = fadd double %".11", %".13", !dbg !77
  %".15" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 7 , !dbg !77
  %".16" = load double, double* %".15", !dbg !77
  %".17" = fadd double %".14", %".16", !dbg !77
  ret double %".17", !dbg !77
}

define double @"box_dimensions_border_height"(%"struct.ritz_module_1.BoxDimensions"* %"b.arg") !dbg !22
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.BoxDimensions"* %"b.arg", metadata !78, metadata !7), !dbg !79
  %".4" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 1 , !dbg !80
  %".5" = load double, double* %".4", !dbg !80
  %".6" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 2 , !dbg !80
  %".7" = load double, double* %".6", !dbg !80
  %".8" = fadd double %".5", %".7", !dbg !80
  %".9" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 4 , !dbg !80
  %".10" = load double, double* %".9", !dbg !80
  %".11" = fadd double %".8", %".10", !dbg !80
  %".12" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 6 , !dbg !80
  %".13" = load double, double* %".12", !dbg !80
  %".14" = fadd double %".11", %".13", !dbg !80
  %".15" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 8 , !dbg !80
  %".16" = load double, double* %".15", !dbg !80
  %".17" = fadd double %".14", %".16", !dbg !80
  ret double %".17", !dbg !80
}

define double @"box_dimensions_margin_width"(%"struct.ritz_module_1.BoxDimensions"* %"b.arg") !dbg !23
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.BoxDimensions"* %"b.arg", metadata !81, metadata !7), !dbg !82
  %".4" = call double @"box_dimensions_border_width"(%"struct.ritz_module_1.BoxDimensions"* %"b.arg"), !dbg !83
  %".5" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 13 , !dbg !84
  %".6" = load double, double* %".5", !dbg !84
  %".7" = fadd double %".4", %".6", !dbg !84
  %".8" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 11 , !dbg !84
  %".9" = load double, double* %".8", !dbg !84
  %".10" = fadd double %".7", %".9", !dbg !84
  ret double %".10", !dbg !84
}

define double @"box_dimensions_margin_height"(%"struct.ritz_module_1.BoxDimensions"* %"b.arg") !dbg !24
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.BoxDimensions"* %"b.arg", metadata !85, metadata !7), !dbg !86
  %".4" = call double @"box_dimensions_border_height"(%"struct.ritz_module_1.BoxDimensions"* %"b.arg"), !dbg !87
  %".5" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 10 , !dbg !88
  %".6" = load double, double* %".5", !dbg !88
  %".7" = fadd double %".4", %".6", !dbg !88
  %".8" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.arg", i32 0, i32 12 , !dbg !88
  %".9" = load double, double* %".8", !dbg !88
  %".10" = fadd double %".7", %".9", !dbg !88
  ret double %".10", !dbg !88
}

define %"struct.ritz_module_1.BoxDimensions" @"resolve_padding"(%"struct.ritz_module_1.ComputedStyle"* %"style.arg", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg") !dbg !25
{
entry:
  %"b.addr" = alloca %"struct.ritz_module_1.BoxDimensions", !dbg !94
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ComputedStyle"* %"style.arg", metadata !91, metadata !7), !dbg !92
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", metadata !93, metadata !7), !dbg !92
  %".6" = call %"struct.ritz_module_1.BoxDimensions" @"box_dimensions_zero"(), !dbg !94
  store %"struct.ritz_module_1.BoxDimensions" %".6", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !94
  %".8" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 14 , !dbg !95
  %".9" = getelementptr %"struct.ritz_module_1.EdgeSizes", %"struct.ritz_module_1.EdgeSizes"* %".8", i32 0, i32 0 , !dbg !95
  %".10" = trunc i64 0 to i32 , !dbg !95
  %".11" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %".9", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".10"), !dbg !95
  %".12" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !95
  %".13" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", i32 0, i32 2 , !dbg !95
  store double %".11", double* %".13", !dbg !95
  %".15" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 14 , !dbg !96
  %".16" = getelementptr %"struct.ritz_module_1.EdgeSizes", %"struct.ritz_module_1.EdgeSizes"* %".15", i32 0, i32 1 , !dbg !96
  %".17" = trunc i64 1 to i32 , !dbg !96
  %".18" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %".16", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".17"), !dbg !96
  %".19" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !96
  %".20" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", i32 0, i32 3 , !dbg !96
  store double %".18", double* %".20", !dbg !96
  %".22" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 14 , !dbg !97
  %".23" = getelementptr %"struct.ritz_module_1.EdgeSizes", %"struct.ritz_module_1.EdgeSizes"* %".22", i32 0, i32 2 , !dbg !97
  %".24" = trunc i64 0 to i32 , !dbg !97
  %".25" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %".23", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".24"), !dbg !97
  %".26" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !97
  %".27" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", i32 0, i32 4 , !dbg !97
  store double %".25", double* %".27", !dbg !97
  %".29" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 14 , !dbg !98
  %".30" = getelementptr %"struct.ritz_module_1.EdgeSizes", %"struct.ritz_module_1.EdgeSizes"* %".29", i32 0, i32 3 , !dbg !98
  %".31" = trunc i64 1 to i32 , !dbg !98
  %".32" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %".30", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".31"), !dbg !98
  %".33" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !98
  %".34" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", i32 0, i32 5 , !dbg !98
  store double %".32", double* %".34", !dbg !98
  %".36" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !99
  ret %"struct.ritz_module_1.BoxDimensions" %".36", !dbg !99
}

define %"struct.ritz_module_1.BoxDimensions" @"resolve_border"(%"struct.ritz_module_1.ComputedStyle"* %"style.arg", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg") !dbg !26
{
entry:
  %"b.addr" = alloca %"struct.ritz_module_1.BoxDimensions", !dbg !103
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ComputedStyle"* %"style.arg", metadata !100, metadata !7), !dbg !101
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", metadata !102, metadata !7), !dbg !101
  %".6" = call %"struct.ritz_module_1.BoxDimensions" @"box_dimensions_zero"(), !dbg !103
  store %"struct.ritz_module_1.BoxDimensions" %".6", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !103
  %".8" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 15 , !dbg !104
  %".9" = load %"struct.ritz_module_1.Border", %"struct.ritz_module_1.Border"* %".8", !dbg !104
  %".10" = extractvalue %"struct.ritz_module_1.Border" %".9", 0 , !dbg !104
  %".11" = extractvalue %"struct.ritz_module_1.BorderEdge" %".10", 0 , !dbg !104
  %".12" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !104
  %".13" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", i32 0, i32 6 , !dbg !104
  store double %".11", double* %".13", !dbg !104
  %".15" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 15 , !dbg !105
  %".16" = load %"struct.ritz_module_1.Border", %"struct.ritz_module_1.Border"* %".15", !dbg !105
  %".17" = extractvalue %"struct.ritz_module_1.Border" %".16", 1 , !dbg !105
  %".18" = extractvalue %"struct.ritz_module_1.BorderEdge" %".17", 0 , !dbg !105
  %".19" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !105
  %".20" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", i32 0, i32 7 , !dbg !105
  store double %".18", double* %".20", !dbg !105
  %".22" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 15 , !dbg !106
  %".23" = load %"struct.ritz_module_1.Border", %"struct.ritz_module_1.Border"* %".22", !dbg !106
  %".24" = extractvalue %"struct.ritz_module_1.Border" %".23", 2 , !dbg !106
  %".25" = extractvalue %"struct.ritz_module_1.BorderEdge" %".24", 0 , !dbg !106
  %".26" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !106
  %".27" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", i32 0, i32 8 , !dbg !106
  store double %".25", double* %".27", !dbg !106
  %".29" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 15 , !dbg !107
  %".30" = load %"struct.ritz_module_1.Border", %"struct.ritz_module_1.Border"* %".29", !dbg !107
  %".31" = extractvalue %"struct.ritz_module_1.Border" %".30", 3 , !dbg !107
  %".32" = extractvalue %"struct.ritz_module_1.BorderEdge" %".31", 0 , !dbg !107
  %".33" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !107
  %".34" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", i32 0, i32 9 , !dbg !107
  store double %".32", double* %".34", !dbg !107
  %".36" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !108
  ret %"struct.ritz_module_1.BoxDimensions" %".36", !dbg !108
}

define %"struct.ritz_module_1.BoxDimensions" @"resolve_margin"(%"struct.ritz_module_1.ComputedStyle"* %"style.arg", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg") !dbg !27
{
entry:
  %"b.addr" = alloca %"struct.ritz_module_1.BoxDimensions", !dbg !112
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ComputedStyle"* %"style.arg", metadata !109, metadata !7), !dbg !110
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", metadata !111, metadata !7), !dbg !110
  %".6" = call %"struct.ritz_module_1.BoxDimensions" @"box_dimensions_zero"(), !dbg !112
  store %"struct.ritz_module_1.BoxDimensions" %".6", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !112
  %".8" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 13 , !dbg !113
  %".9" = getelementptr %"struct.ritz_module_1.EdgeSizes", %"struct.ritz_module_1.EdgeSizes"* %".8", i32 0, i32 0 , !dbg !113
  %".10" = trunc i64 0 to i32 , !dbg !113
  %".11" = call double @"resolve_dimension_or"(%"struct.ritz_module_1.Dimension"* %".9", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".10", double              0x0), !dbg !113
  %".12" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !113
  %".13" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", i32 0, i32 10 , !dbg !113
  store double %".11", double* %".13", !dbg !113
  %".15" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 13 , !dbg !114
  %".16" = getelementptr %"struct.ritz_module_1.EdgeSizes", %"struct.ritz_module_1.EdgeSizes"* %".15", i32 0, i32 1 , !dbg !114
  %".17" = trunc i64 1 to i32 , !dbg !114
  %".18" = call double @"resolve_dimension_or"(%"struct.ritz_module_1.Dimension"* %".16", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".17", double              0x0), !dbg !114
  %".19" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !114
  %".20" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", i32 0, i32 11 , !dbg !114
  store double %".18", double* %".20", !dbg !114
  %".22" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 13 , !dbg !115
  %".23" = getelementptr %"struct.ritz_module_1.EdgeSizes", %"struct.ritz_module_1.EdgeSizes"* %".22", i32 0, i32 2 , !dbg !115
  %".24" = trunc i64 0 to i32 , !dbg !115
  %".25" = call double @"resolve_dimension_or"(%"struct.ritz_module_1.Dimension"* %".23", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".24", double              0x0), !dbg !115
  %".26" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !115
  %".27" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", i32 0, i32 12 , !dbg !115
  store double %".25", double* %".27", !dbg !115
  %".29" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 13 , !dbg !116
  %".30" = getelementptr %"struct.ritz_module_1.EdgeSizes", %"struct.ritz_module_1.EdgeSizes"* %".29", i32 0, i32 3 , !dbg !116
  %".31" = trunc i64 1 to i32 , !dbg !116
  %".32" = call double @"resolve_dimension_or"(%"struct.ritz_module_1.Dimension"* %".30", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".31", double              0x0), !dbg !116
  %".33" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !116
  %".34" = getelementptr %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", i32 0, i32 13 , !dbg !116
  store double %".32", double* %".34", !dbg !116
  %".36" = load %"struct.ritz_module_1.BoxDimensions", %"struct.ritz_module_1.BoxDimensions"* %"b.addr", !dbg !117
  ret %"struct.ritz_module_1.BoxDimensions" %".36", !dbg !117
}

define %"struct.ritz_module_1.BoxDimensions" @"resolve_box_model"(%"struct.ritz_module_1.ComputedStyle"* %"style.arg", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg") !dbg !28
{
entry:
  %"content_width.addr" = alloca double, !dbg !126
  %"content_height.addr" = alloca double, !dbg !137
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ComputedStyle"* %"style.arg", metadata !118, metadata !7), !dbg !119
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", metadata !120, metadata !7), !dbg !119
  %".6" = call %"struct.ritz_module_1.BoxDimensions" @"resolve_padding"(%"struct.ritz_module_1.ComputedStyle"* %"style.arg", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg"), !dbg !121
  %".7" = call %"struct.ritz_module_1.BoxDimensions" @"resolve_border"(%"struct.ritz_module_1.ComputedStyle"* %"style.arg", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg"), !dbg !122
  %".8" = call %"struct.ritz_module_1.BoxDimensions" @"resolve_margin"(%"struct.ritz_module_1.ComputedStyle"* %"style.arg", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg"), !dbg !123
  %".9" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".6", 5 , !dbg !124
  %".10" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".6", 3 , !dbg !124
  %".11" = fadd double %".9", %".10", !dbg !124
  %".12" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".7", 9 , !dbg !124
  %".13" = fadd double %".11", %".12", !dbg !124
  %".14" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".7", 7 , !dbg !124
  %".15" = fadd double %".13", %".14", !dbg !124
  %".16" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".6", 2 , !dbg !125
  %".17" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".6", 4 , !dbg !125
  %".18" = fadd double %".16", %".17", !dbg !125
  %".19" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".7", 6 , !dbg !125
  %".20" = fadd double %".18", %".19", !dbg !125
  %".21" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".7", 8 , !dbg !125
  %".22" = fadd double %".20", %".21", !dbg !125
  store double              0x0, double* %"content_width.addr", !dbg !126
  %".24" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 7 , !dbg !127
  %".25" = load %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %".24", !dbg !127
  %".26" = extractvalue %"struct.ritz_module_1.Dimension" %".25", 1 , !dbg !127
  %".27" = icmp ne i32 %".26", 6 , !dbg !127
  br i1 %".27", label %"if.then", label %"if.end", !dbg !127
if.then:
  %".29" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 7 , !dbg !128
  %".30" = trunc i64 1 to i32 , !dbg !128
  %".31" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %".29", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".30"), !dbg !128
  %".32" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 2 , !dbg !128
  %".33" = load i32, i32* %".32", !dbg !128
  %".34" = icmp eq i32 %".33", 0 , !dbg !128
  br i1 %".34", label %"if.then.1", label %"if.else", !dbg !128
if.end:
  %".42" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 9 , !dbg !131
  %".43" = load %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %".42", !dbg !131
  %".44" = extractvalue %"struct.ritz_module_1.Dimension" %".43", 1 , !dbg !131
  %".45" = icmp ne i32 %".44", 6 , !dbg !131
  br i1 %".45", label %"if.then.2", label %"if.end.2", !dbg !131
if.then.1:
  store double %".31", double* %"content_width.addr", !dbg !129
  br label %"if.end.1", !dbg !130
if.else:
  %".37" = fsub double %".31", %".15", !dbg !130
  store double %".37", double* %"content_width.addr", !dbg !130
  br label %"if.end.1", !dbg !130
if.end.1:
  br label %"if.end", !dbg !130
if.then.2:
  %".47" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 9 , !dbg !132
  %".48" = trunc i64 1 to i32 , !dbg !132
  %".49" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %".47", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".48"), !dbg !132
  %".50" = load double, double* %"content_width.addr", !dbg !132
  %".51" = fcmp olt double %".50", %".49" , !dbg !132
  br i1 %".51", label %"if.then.3", label %"if.end.3", !dbg !132
if.end.2:
  %".56" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 11 , !dbg !134
  %".57" = load %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %".56", !dbg !134
  %".58" = extractvalue %"struct.ritz_module_1.Dimension" %".57", 1 , !dbg !134
  %".59" = icmp ne i32 %".58", 6 , !dbg !134
  br i1 %".59", label %"if.then.4", label %"if.end.4", !dbg !134
if.then.3:
  store double %".49", double* %"content_width.addr", !dbg !133
  br label %"if.end.3", !dbg !133
if.end.3:
  br label %"if.end.2", !dbg !133
if.then.4:
  %".61" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 11 , !dbg !135
  %".62" = trunc i64 1 to i32 , !dbg !135
  %".63" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %".61", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".62"), !dbg !135
  %".64" = load double, double* %"content_width.addr", !dbg !135
  %".65" = fcmp ogt double %".64", %".63" , !dbg !135
  br i1 %".65", label %"if.then.5", label %"if.end.5", !dbg !135
if.end.4:
  store double              0x0, double* %"content_height.addr", !dbg !137
  %".71" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 8 , !dbg !138
  %".72" = load %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %".71", !dbg !138
  %".73" = extractvalue %"struct.ritz_module_1.Dimension" %".72", 1 , !dbg !138
  %".74" = icmp ne i32 %".73", 6 , !dbg !138
  br i1 %".74", label %"if.then.6", label %"if.end.6", !dbg !138
if.then.5:
  store double %".63", double* %"content_width.addr", !dbg !136
  br label %"if.end.5", !dbg !136
if.end.5:
  br label %"if.end.4", !dbg !136
if.then.6:
  %".76" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 8 , !dbg !139
  %".77" = trunc i64 0 to i32 , !dbg !139
  %".78" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %".76", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".77"), !dbg !139
  %".79" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 2 , !dbg !139
  %".80" = load i32, i32* %".79", !dbg !139
  %".81" = icmp eq i32 %".80", 0 , !dbg !139
  br i1 %".81", label %"if.then.7", label %"if.else.1", !dbg !139
if.end.6:
  %".89" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 10 , !dbg !142
  %".90" = load %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %".89", !dbg !142
  %".91" = extractvalue %"struct.ritz_module_1.Dimension" %".90", 1 , !dbg !142
  %".92" = icmp ne i32 %".91", 6 , !dbg !142
  br i1 %".92", label %"if.then.8", label %"if.end.8", !dbg !142
if.then.7:
  store double %".78", double* %"content_height.addr", !dbg !140
  br label %"if.end.7", !dbg !141
if.else.1:
  %".84" = fsub double %".78", %".22", !dbg !141
  store double %".84", double* %"content_height.addr", !dbg !141
  br label %"if.end.7", !dbg !141
if.end.7:
  br label %"if.end.6", !dbg !141
if.then.8:
  %".94" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 10 , !dbg !143
  %".95" = trunc i64 0 to i32 , !dbg !143
  %".96" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %".94", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".95"), !dbg !143
  %".97" = load double, double* %"content_height.addr", !dbg !143
  %".98" = fcmp olt double %".97", %".96" , !dbg !143
  br i1 %".98", label %"if.then.9", label %"if.end.9", !dbg !143
if.end.8:
  %".103" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 12 , !dbg !145
  %".104" = load %"struct.ritz_module_1.Dimension", %"struct.ritz_module_1.Dimension"* %".103", !dbg !145
  %".105" = extractvalue %"struct.ritz_module_1.Dimension" %".104", 1 , !dbg !145
  %".106" = icmp ne i32 %".105", 6 , !dbg !145
  br i1 %".106", label %"if.then.10", label %"if.end.10", !dbg !145
if.then.9:
  store double %".96", double* %"content_height.addr", !dbg !144
  br label %"if.end.9", !dbg !144
if.end.9:
  br label %"if.end.8", !dbg !144
if.then.10:
  %".108" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 12 , !dbg !146
  %".109" = trunc i64 0 to i32 , !dbg !146
  %".110" = call double @"resolve_dimension"(%"struct.ritz_module_1.Dimension"* %".108", %"struct.ritz_module_1.LayoutConstraints"* %"c.arg", i32 %".109"), !dbg !146
  %".111" = load double, double* %"content_height.addr", !dbg !146
  %".112" = fcmp ogt double %".111", %".110" , !dbg !146
  br i1 %".112", label %"if.then.11", label %"if.end.11", !dbg !146
if.end.10:
  %".117" = load double, double* %"content_width.addr", !dbg !148
  %".118" = load double, double* %"content_height.addr", !dbg !148
  %".119" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".6", 2 , !dbg !148
  %".120" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".6", 3 , !dbg !148
  %".121" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".6", 4 , !dbg !148
  %".122" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".6", 5 , !dbg !148
  %".123" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".7", 6 , !dbg !148
  %".124" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".7", 7 , !dbg !148
  %".125" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".7", 8 , !dbg !148
  %".126" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".7", 9 , !dbg !148
  %".127" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".8", 10 , !dbg !148
  %".128" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".8", 11 , !dbg !148
  %".129" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".8", 12 , !dbg !148
  %".130" = extractvalue %"struct.ritz_module_1.BoxDimensions" %".8", 13 , !dbg !148
  %".131" = insertvalue %"struct.ritz_module_1.BoxDimensions" undef, double %".117", 0 , !dbg !148
  %".132" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".131", double %".118", 1 , !dbg !148
  %".133" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".132", double %".119", 2 , !dbg !148
  %".134" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".133", double %".120", 3 , !dbg !148
  %".135" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".134", double %".121", 4 , !dbg !148
  %".136" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".135", double %".122", 5 , !dbg !148
  %".137" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".136", double %".123", 6 , !dbg !148
  %".138" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".137", double %".124", 7 , !dbg !148
  %".139" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".138", double %".125", 8 , !dbg !148
  %".140" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".139", double %".126", 9 , !dbg !148
  %".141" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".140", double %".127", 10 , !dbg !148
  %".142" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".141", double %".128", 11 , !dbg !148
  %".143" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".142", double %".129", 12 , !dbg !148
  %".144" = insertvalue %"struct.ritz_module_1.BoxDimensions" %".143", double %".130", 13 , !dbg !148
  ret %"struct.ritz_module_1.BoxDimensions" %".144", !dbg !148
if.then.11:
  store double %".110", double* %"content_height.addr", !dbg !147
  br label %"if.end.11", !dbg !147
if.end.11:
  br label %"if.end.10", !dbg !147
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/lib/layout", filename: "box.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 29, name: "layout_constraints_new", scopeLine: 29, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 47, name: "resolve_dimension", scopeLine: 47, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 68, name: "resolve_dimension_or", scopeLine: 68, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 98, name: "box_dimensions_zero", scopeLine: 98, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 107, name: "box_dimensions_border_width", scopeLine: 107, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 111, name: "box_dimensions_border_height", scopeLine: 111, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 115, name: "box_dimensions_margin_width", scopeLine: 115, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 120, name: "box_dimensions_margin_height", scopeLine: 120, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 129, name: "resolve_padding", scopeLine: 129, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 138, name: "resolve_border", scopeLine: 138, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "resolve_margin", scopeLine: 148, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 157, name: "resolve_box_model", scopeLine: 157, type: !4, unit: !1)
!29 = !DILocation(column: 5, line: 30, scope: !17)
!30 = !DICompositeType(align: 64, file: !0, name: "LayoutConstraints", size: 448, tag: DW_TAG_structure_type)
!31 = !DILocalVariable(file: !0, line: 30, name: "c", scope: !17, type: !30)
!32 = !DILocation(column: 1, line: 30, scope: !17)
!33 = !DILocation(column: 5, line: 31, scope: !17)
!34 = !DILocation(column: 5, line: 32, scope: !17)
!35 = !DILocation(column: 5, line: 33, scope: !17)
!36 = !DILocation(column: 5, line: 34, scope: !17)
!37 = !DILocation(column: 5, line: 35, scope: !17)
!38 = !DILocation(column: 5, line: 36, scope: !17)
!39 = !DILocation(column: 5, line: 37, scope: !17)
!40 = !DILocation(column: 5, line: 38, scope: !17)
!41 = !DILocation(column: 5, line: 39, scope: !17)
!42 = !DICompositeType(align: 64, file: !0, name: "Dimension", size: 128, tag: DW_TAG_structure_type)
!43 = !DIDerivedType(baseType: !42, size: 64, tag: DW_TAG_reference_type)
!44 = !DILocalVariable(file: !0, line: 47, name: "dim", scope: !18, type: !43)
!45 = !DILocation(column: 1, line: 47, scope: !18)
!46 = !DIDerivedType(baseType: !30, size: 64, tag: DW_TAG_reference_type)
!47 = !DILocalVariable(file: !0, line: 47, name: "c", scope: !18, type: !46)
!48 = !DILocalVariable(file: !0, line: 47, name: "for_width", scope: !18, type: !10)
!49 = !DILocation(column: 5, line: 48, scope: !18)
!50 = !DILocation(column: 9, line: 49, scope: !18)
!51 = !DILocation(column: 5, line: 50, scope: !18)
!52 = !DILocation(column: 9, line: 51, scope: !18)
!53 = !DILocation(column: 5, line: 52, scope: !18)
!54 = !DILocation(column: 9, line: 53, scope: !18)
!55 = !DILocation(column: 5, line: 54, scope: !18)
!56 = !DILocation(column: 13, line: 56, scope: !18)
!57 = !DILocation(column: 13, line: 58, scope: !18)
!58 = !DILocation(column: 5, line: 59, scope: !18)
!59 = !DILocation(column: 9, line: 60, scope: !18)
!60 = !DILocation(column: 5, line: 61, scope: !18)
!61 = !DILocation(column: 9, line: 62, scope: !18)
!62 = !DILocation(column: 5, line: 63, scope: !18)
!63 = !DILocation(column: 9, line: 64, scope: !18)
!64 = !DILocation(column: 5, line: 65, scope: !18)
!65 = !DILocalVariable(file: !0, line: 68, name: "dim", scope: !19, type: !43)
!66 = !DILocation(column: 1, line: 68, scope: !19)
!67 = !DILocalVariable(file: !0, line: 68, name: "c", scope: !19, type: !46)
!68 = !DILocalVariable(file: !0, line: 68, name: "for_width", scope: !19, type: !10)
!69 = !DILocation(column: 5, line: 69, scope: !19)
!70 = !DILocation(column: 9, line: 70, scope: !19)
!71 = !DILocation(column: 5, line: 71, scope: !19)
!72 = !DILocation(column: 5, line: 99, scope: !20)
!73 = !DICompositeType(align: 64, file: !0, name: "BoxDimensions", size: 896, tag: DW_TAG_structure_type)
!74 = !DIDerivedType(baseType: !73, size: 64, tag: DW_TAG_reference_type)
!75 = !DILocalVariable(file: !0, line: 107, name: "b", scope: !21, type: !74)
!76 = !DILocation(column: 1, line: 107, scope: !21)
!77 = !DILocation(column: 5, line: 108, scope: !21)
!78 = !DILocalVariable(file: !0, line: 111, name: "b", scope: !22, type: !74)
!79 = !DILocation(column: 1, line: 111, scope: !22)
!80 = !DILocation(column: 5, line: 112, scope: !22)
!81 = !DILocalVariable(file: !0, line: 115, name: "b", scope: !23, type: !74)
!82 = !DILocation(column: 1, line: 115, scope: !23)
!83 = !DILocation(column: 5, line: 116, scope: !23)
!84 = !DILocation(column: 5, line: 117, scope: !23)
!85 = !DILocalVariable(file: !0, line: 120, name: "b", scope: !24, type: !74)
!86 = !DILocation(column: 1, line: 120, scope: !24)
!87 = !DILocation(column: 5, line: 121, scope: !24)
!88 = !DILocation(column: 5, line: 122, scope: !24)
!89 = !DICompositeType(align: 64, file: !0, name: "ComputedStyle", size: 3840, tag: DW_TAG_structure_type)
!90 = !DIDerivedType(baseType: !89, size: 64, tag: DW_TAG_reference_type)
!91 = !DILocalVariable(file: !0, line: 129, name: "style", scope: !25, type: !90)
!92 = !DILocation(column: 1, line: 129, scope: !25)
!93 = !DILocalVariable(file: !0, line: 129, name: "c", scope: !25, type: !46)
!94 = !DILocation(column: 5, line: 130, scope: !25)
!95 = !DILocation(column: 5, line: 131, scope: !25)
!96 = !DILocation(column: 5, line: 132, scope: !25)
!97 = !DILocation(column: 5, line: 133, scope: !25)
!98 = !DILocation(column: 5, line: 134, scope: !25)
!99 = !DILocation(column: 5, line: 135, scope: !25)
!100 = !DILocalVariable(file: !0, line: 138, name: "style", scope: !26, type: !90)
!101 = !DILocation(column: 1, line: 138, scope: !26)
!102 = !DILocalVariable(file: !0, line: 138, name: "c", scope: !26, type: !46)
!103 = !DILocation(column: 5, line: 139, scope: !26)
!104 = !DILocation(column: 5, line: 141, scope: !26)
!105 = !DILocation(column: 5, line: 142, scope: !26)
!106 = !DILocation(column: 5, line: 143, scope: !26)
!107 = !DILocation(column: 5, line: 144, scope: !26)
!108 = !DILocation(column: 5, line: 145, scope: !26)
!109 = !DILocalVariable(file: !0, line: 148, name: "style", scope: !27, type: !90)
!110 = !DILocation(column: 1, line: 148, scope: !27)
!111 = !DILocalVariable(file: !0, line: 148, name: "c", scope: !27, type: !46)
!112 = !DILocation(column: 5, line: 149, scope: !27)
!113 = !DILocation(column: 5, line: 150, scope: !27)
!114 = !DILocation(column: 5, line: 151, scope: !27)
!115 = !DILocation(column: 5, line: 152, scope: !27)
!116 = !DILocation(column: 5, line: 153, scope: !27)
!117 = !DILocation(column: 5, line: 154, scope: !27)
!118 = !DILocalVariable(file: !0, line: 157, name: "style", scope: !28, type: !90)
!119 = !DILocation(column: 1, line: 157, scope: !28)
!120 = !DILocalVariable(file: !0, line: 157, name: "c", scope: !28, type: !46)
!121 = !DILocation(column: 5, line: 158, scope: !28)
!122 = !DILocation(column: 5, line: 159, scope: !28)
!123 = !DILocation(column: 5, line: 160, scope: !28)
!124 = !DILocation(column: 5, line: 163, scope: !28)
!125 = !DILocation(column: 5, line: 164, scope: !28)
!126 = !DILocation(column: 5, line: 167, scope: !28)
!127 = !DILocation(column: 5, line: 168, scope: !28)
!128 = !DILocation(column: 9, line: 169, scope: !28)
!129 = !DILocation(column: 13, line: 171, scope: !28)
!130 = !DILocation(column: 13, line: 173, scope: !28)
!131 = !DILocation(column: 5, line: 176, scope: !28)
!132 = !DILocation(column: 9, line: 177, scope: !28)
!133 = !DILocation(column: 13, line: 179, scope: !28)
!134 = !DILocation(column: 5, line: 180, scope: !28)
!135 = !DILocation(column: 9, line: 181, scope: !28)
!136 = !DILocation(column: 13, line: 183, scope: !28)
!137 = !DILocation(column: 5, line: 186, scope: !28)
!138 = !DILocation(column: 5, line: 187, scope: !28)
!139 = !DILocation(column: 9, line: 188, scope: !28)
!140 = !DILocation(column: 13, line: 190, scope: !28)
!141 = !DILocation(column: 13, line: 192, scope: !28)
!142 = !DILocation(column: 5, line: 195, scope: !28)
!143 = !DILocation(column: 9, line: 196, scope: !28)
!144 = !DILocation(column: 13, line: 198, scope: !28)
!145 = !DILocation(column: 5, line: 199, scope: !28)
!146 = !DILocation(column: 9, line: 200, scope: !28)
!147 = !DILocation(column: 13, line: 202, scope: !28)
!148 = !DILocation(column: 5, line: 204, scope: !28)