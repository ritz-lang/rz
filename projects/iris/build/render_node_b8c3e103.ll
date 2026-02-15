; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Vec$RenderNode" = type {%"struct.ritz_module_1.RenderNode"*, i64, i64}
%"struct.ritz_module_1.Vec$u8" = type {i8*, i64, i64}
%"struct.ritz_module_1.Vec$LineBounds" = type {%"struct.ritz_module_1.LineBounds"*, i64, i64}
%"struct.ritz_module_1.Stat" = type {i64, i64, i64, i32, i32, i32, i32, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64}
%"struct.ritz_module_1.Dirent64" = type {i64, i64, i16, i8}
%"struct.ritz_module_1.Timeval" = type {i64, i64}
%"struct.ritz_module_1.Arena" = type {i8*, i64, i64}
%"struct.ritz_module_1.BlockHeader" = type {i64}
%"struct.ritz_module_1.FreeNode" = type {%"struct.ritz_module_1.FreeNode"*}
%"struct.ritz_module_1.SizeBin" = type {%"struct.ritz_module_1.FreeNode"*, i64, i8*, i64, i64}
%"struct.ritz_module_1.GlobalAlloc" = type {[9 x %"struct.ritz_module_1.SizeBin"], i32}
%"struct.ritz_module_1.LineBounds" = type {i64, i64}
%"struct.ritz_module_1.HashMapEntryI64" = type {i64, i64, i32}
%"struct.ritz_module_1.HashMapI64" = type {%"struct.ritz_module_1.HashMapEntryI64"*, i64, i64, i64}
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
%"struct.ritz_module_1.DirtyFlags" = type {i32, i32, i32, i32}
%"struct.ritz_module_1.LayoutResult" = type {i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32}
%"struct.ritz_module_1.RenderNode" = type {%"struct.ritz_module_1.NodeId", i32, i32, i8*, i32, i32, i32, i32, %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId", i32, %"struct.ritz_module_1.LayoutResult", %"struct.ritz_module_1.DirtyFlags", i64}
%"struct.ritz_module_1.RenderTree" = type {%"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.NodeId"}
declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

@"BLOCK_SIZES" = internal constant [9 x i64] [i64 32, i64 48, i64 80, i64 144, i64 272, i64 528, i64 1040, i64 2064, i64 0]
@"g_alloc" = internal global %"struct.ritz_module_1.GlobalAlloc" zeroinitializer
declare i32 @"HashMapI64_drop"(%"struct.ritz_module_1.HashMapI64"* %".1")

declare i64 @"HashMapI64_len"(%"struct.ritz_module_1.HashMapI64"* %".1")

declare i64 @"HashMapI64_cap"(%"struct.ritz_module_1.HashMapI64"* %".1")

declare i32 @"HashMapI64_is_empty"(%"struct.ritz_module_1.HashMapI64"* %".1")

declare i32 @"HashMapI64_insert"(%"struct.ritz_module_1.HashMapI64"* %".1", i64 %".2", i64 %".3")

declare i64 @"HashMapI64_get"(%"struct.ritz_module_1.HashMapI64"* %".1", i64 %".2")

declare i32 @"HashMapI64_contains"(%"struct.ritz_module_1.HashMapI64"* %".1", i64 %".2")

declare i32 @"HashMapI64_remove"(%"struct.ritz_module_1.HashMapI64"* %".1", i64 %".2")

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

declare i64 @"strlen"(i8* %".1")

declare i32 @"streq"(i8* %".1", i8* %".2")

declare i32 @"strneq"(i8* %".1", i8* %".2", i64 %".3")

declare i32 @"strcmp"(i8* %".1", i8* %".2")

declare i8* @"strchr"(i8* %".1", i8 %".2")

declare i8* @"strrchr"(i8* %".1", i8 %".2")

declare i8* @"strstr"(i8* %".1", i8* %".2")

declare i8* @"strcpy"(i8* %".1", i8* %".2")

declare i8* @"strncpy"(i8* %".1", i8* %".2", i64 %".3")

declare i8* @"strcat"(i8* %".1", i8* %".2")

declare i64 @"atoi"(i8* %".1")

declare i8* @"itoa"(i64 %".1", i8* %".2")

declare i32 @"isdigit"(i8 %".1")

declare i32 @"isalpha"(i8 %".1")

declare i32 @"isalnum"(i8 %".1")

declare i32 @"isspace"(i8 %".1")

declare i32 @"isupper"(i8 %".1")

declare i32 @"islower"(i8 %".1")

declare i8 @"toupper"(i8 %".1")

declare i8 @"tolower"(i8 %".1")

declare i8* @"memset"(i8* %".1", i8 %".2", i64 %".3")

declare i8* @"memcpy"(i8* %".1", i8* %".2", i64 %".3")

declare i32 @"memcmp"(i8* %".1", i8* %".2", i64 %".3")

declare %"struct.ritz_module_1.Arena" @"arena_new"(i64 %".1")

declare %"struct.ritz_module_1.Arena" @"arena_default"()

declare i8* @"arena_alloc"(%"struct.ritz_module_1.Arena"* %".1", i64 %".2")

declare i8* @"arena_alloc_zero"(%"struct.ritz_module_1.Arena"* %".1", i64 %".2")

declare i8* @"arena_alloc_array"(%"struct.ritz_module_1.Arena"* %".1", i64 %".2", i64 %".3")

declare i32 @"arena_reset"(%"struct.ritz_module_1.Arena"* %".1")

declare i32 @"arena_destroy"(%"struct.ritz_module_1.Arena"* %".1")

declare i64 @"arena_used"(%"struct.ritz_module_1.Arena"* %".1")

declare i64 @"arena_remaining"(%"struct.ritz_module_1.Arena"* %".1")

declare i32 @"arena_valid"(%"struct.ritz_module_1.Arena"* %".1")

declare i8* @"heap_alloc"(i64 %".1")

declare i32 @"heap_free"(i8* %".1", i64 %".2")

declare i8* @"heap_realloc"(i8* %".1", i64 %".2", i64 %".3")

declare i32 @"memzero"(i8* %".1", i64 %".2")

declare i64 @"get_block_size"(i32 %".1")

declare i32 @"get_size_class"(i64 %".1")

declare i32 @"bin_init"(%"struct.ritz_module_1.SizeBin"* %".1", i64 %".2")

declare i32 @"bin_new_slab"(%"struct.ritz_module_1.SizeBin"* %".1")

declare i8* @"bin_alloc"(%"struct.ritz_module_1.SizeBin"* %".1", i32 %".2")

declare i32 @"bin_free"(%"struct.ritz_module_1.SizeBin"* %".1", i8* %".2")

declare i32 @"alloc_init"()

declare i8* @"malloc"(i64 %".1")

declare i32 @"free"(i8* %".1")

declare i8* @"realloc"(i8* %".1", i64 %".2")

declare i8* @"calloc"(i64 %".1", i64 %".2")

declare i32 @"vec_push_str"(%"struct.ritz_module_1.Vec$u8"* %".1", i8* %".2")

declare i8* @"vec_as_str"(%"struct.ritz_module_1.Vec$u8"* %".1")

declare i64 @"vec_read_all_fd"(i32 %".1", %"struct.ritz_module_1.Vec$u8"* %".2")

declare i32 @"vec_find_lines"(%"struct.ritz_module_1.Vec$u8"* %".1", %"struct.ritz_module_1.Vec$LineBounds"* %".2")

declare i64 @"fnv1a_init"()

declare i64 @"fnv1a_byte"(i64 %".1", i8 %".2")

declare i64 @"fnv1a_i32"(i64 %".1", i32 %".2")

declare i64 @"fnv1a_i64"(i64 %".1", i64 %".2")

declare i64 @"fnv1a_u64"(i64 %".1", i64 %".2")

declare i64 @"hash_i32"(i32 %".1")

declare i64 @"hash_i64"(i64 %".1")

declare i64 @"hash_u64"(i64 %".1")

declare i32 @"eq_i32"(i32 %".1", i32 %".2")

declare i32 @"eq_i64"(i64 %".1", i64 %".2")

declare i32 @"eq_u64"(i64 %".1", i64 %".2")

declare %"struct.ritz_module_1.HashMapI64" @"hashmap_i64_new"()

declare %"struct.ritz_module_1.HashMapI64" @"hashmap_i64_with_cap"(i64 %".1")

declare i64 @"hashmap_i64_len"(%"struct.ritz_module_1.HashMapI64"* %".1")

declare i64 @"hashmap_i64_cap"(%"struct.ritz_module_1.HashMapI64"* %".1")

declare i32 @"hashmap_i64_is_empty"(%"struct.ritz_module_1.HashMapI64"* %".1")

declare i32 @"hashmap_i64_drop"(%"struct.ritz_module_1.HashMapI64"* %".1")

declare i64 @"hashmap_i64_find_slot"(%"struct.ritz_module_1.HashMapI64"* %".1", i64 %".2")

declare i32 @"hashmap_i64_insert"(%"struct.ritz_module_1.HashMapI64"* %".1", i64 %".2", i64 %".3")

declare i64 @"hashmap_i64_get"(%"struct.ritz_module_1.HashMapI64"* %".1", i64 %".2")

declare i32 @"hashmap_i64_contains"(%"struct.ritz_module_1.HashMapI64"* %".1", i64 %".2")

declare i32 @"hashmap_i64_remove"(%"struct.ritz_module_1.HashMapI64"* %".1", i64 %".2")

declare i32 @"hashmap_i64_grow"(%"struct.ritz_module_1.HashMapI64"* %".1")

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

define %"struct.ritz_module_1.DirtyFlags" @"dirty_flags_none"() !dbg !17
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !54
  %".3" = trunc i64 0 to i32 , !dbg !54
  %".4" = trunc i64 0 to i32 , !dbg !54
  %".5" = trunc i64 0 to i32 , !dbg !54
  %".6" = insertvalue %"struct.ritz_module_1.DirtyFlags" undef, i32 %".2", 0 , !dbg !54
  %".7" = insertvalue %"struct.ritz_module_1.DirtyFlags" %".6", i32 %".3", 1 , !dbg !54
  %".8" = insertvalue %"struct.ritz_module_1.DirtyFlags" %".7", i32 %".4", 2 , !dbg !54
  %".9" = insertvalue %"struct.ritz_module_1.DirtyFlags" %".8", i32 %".5", 3 , !dbg !54
  ret %"struct.ritz_module_1.DirtyFlags" %".9", !dbg !54
}

define %"struct.ritz_module_1.DirtyFlags" @"dirty_flags_all"() !dbg !18
{
entry:
  %".2" = trunc i64 1 to i32 , !dbg !55
  %".3" = trunc i64 1 to i32 , !dbg !55
  %".4" = trunc i64 1 to i32 , !dbg !55
  %".5" = trunc i64 1 to i32 , !dbg !55
  %".6" = insertvalue %"struct.ritz_module_1.DirtyFlags" undef, i32 %".2", 0 , !dbg !55
  %".7" = insertvalue %"struct.ritz_module_1.DirtyFlags" %".6", i32 %".3", 1 , !dbg !55
  %".8" = insertvalue %"struct.ritz_module_1.DirtyFlags" %".7", i32 %".4", 2 , !dbg !55
  %".9" = insertvalue %"struct.ritz_module_1.DirtyFlags" %".8", i32 %".5", 3 , !dbg !55
  ret %"struct.ritz_module_1.DirtyFlags" %".9", !dbg !55
}

define i32 @"dirty_flags_is_clean"(%"struct.ritz_module_1.DirtyFlags" %"flags.arg") !dbg !19
{
entry:
  %"flags" = alloca %"struct.ritz_module_1.DirtyFlags"
  store %"struct.ritz_module_1.DirtyFlags" %"flags.arg", %"struct.ritz_module_1.DirtyFlags"* %"flags"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.DirtyFlags"* %"flags", metadata !57, metadata !7), !dbg !58
  %".5" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 0 , !dbg !59
  %".6" = load i32, i32* %".5", !dbg !59
  %".7" = sext i32 %".6" to i64 , !dbg !59
  %".8" = icmp ne i64 %".7", 0 , !dbg !59
  br i1 %".8", label %"if.then", label %"if.end", !dbg !59
if.then:
  %".10" = trunc i64 0 to i32 , !dbg !60
  ret i32 %".10", !dbg !60
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 1 , !dbg !61
  %".13" = load i32, i32* %".12", !dbg !61
  %".14" = sext i32 %".13" to i64 , !dbg !61
  %".15" = icmp ne i64 %".14", 0 , !dbg !61
  br i1 %".15", label %"if.then.1", label %"if.end.1", !dbg !61
if.then.1:
  %".17" = trunc i64 0 to i32 , !dbg !62
  ret i32 %".17", !dbg !62
if.end.1:
  %".19" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 2 , !dbg !63
  %".20" = load i32, i32* %".19", !dbg !63
  %".21" = sext i32 %".20" to i64 , !dbg !63
  %".22" = icmp ne i64 %".21", 0 , !dbg !63
  br i1 %".22", label %"if.then.2", label %"if.end.2", !dbg !63
if.then.2:
  %".24" = trunc i64 0 to i32 , !dbg !64
  ret i32 %".24", !dbg !64
if.end.2:
  %".26" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 3 , !dbg !65
  %".27" = load i32, i32* %".26", !dbg !65
  %".28" = sext i32 %".27" to i64 , !dbg !65
  %".29" = icmp ne i64 %".28", 0 , !dbg !65
  br i1 %".29", label %"if.then.3", label %"if.end.3", !dbg !65
if.then.3:
  %".31" = trunc i64 0 to i32 , !dbg !66
  ret i32 %".31", !dbg !66
if.end.3:
  %".33" = trunc i64 1 to i32 , !dbg !67
  ret i32 %".33", !dbg !67
}

define i32 @"dirty_flags_needs_layout"(%"struct.ritz_module_1.DirtyFlags" %"flags.arg") !dbg !20
{
entry:
  %"flags" = alloca %"struct.ritz_module_1.DirtyFlags"
  store %"struct.ritz_module_1.DirtyFlags" %"flags.arg", %"struct.ritz_module_1.DirtyFlags"* %"flags"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.DirtyFlags"* %"flags", metadata !68, metadata !7), !dbg !69
  %".5" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 0 , !dbg !70
  %".6" = load i32, i32* %".5", !dbg !70
  %".7" = sext i32 %".6" to i64 , !dbg !70
  %".8" = icmp ne i64 %".7", 0 , !dbg !70
  br i1 %".8", label %"if.then", label %"if.end", !dbg !70
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !71
  ret i32 %".10", !dbg !71
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 1 , !dbg !72
  %".13" = load i32, i32* %".12", !dbg !72
  %".14" = sext i32 %".13" to i64 , !dbg !72
  %".15" = icmp ne i64 %".14", 0 , !dbg !72
  br i1 %".15", label %"if.then.1", label %"if.end.1", !dbg !72
if.then.1:
  %".17" = trunc i64 1 to i32 , !dbg !73
  ret i32 %".17", !dbg !73
if.end.1:
  %".19" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 2 , !dbg !74
  %".20" = load i32, i32* %".19", !dbg !74
  %".21" = sext i32 %".20" to i64 , !dbg !74
  %".22" = icmp ne i64 %".21", 0 , !dbg !74
  br i1 %".22", label %"if.then.2", label %"if.end.2", !dbg !74
if.then.2:
  %".24" = trunc i64 1 to i32 , !dbg !75
  ret i32 %".24", !dbg !75
if.end.2:
  %".26" = trunc i64 0 to i32 , !dbg !76
  ret i32 %".26", !dbg !76
}

define i32 @"dirty_flags_needs_paint"(%"struct.ritz_module_1.DirtyFlags" %"flags.arg") !dbg !21
{
entry:
  %"flags" = alloca %"struct.ritz_module_1.DirtyFlags"
  store %"struct.ritz_module_1.DirtyFlags" %"flags.arg", %"struct.ritz_module_1.DirtyFlags"* %"flags"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.DirtyFlags"* %"flags", metadata !77, metadata !7), !dbg !78
  %".5" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 0 , !dbg !79
  %".6" = load i32, i32* %".5", !dbg !79
  %".7" = sext i32 %".6" to i64 , !dbg !79
  %".8" = icmp ne i64 %".7", 0 , !dbg !79
  br i1 %".8", label %"if.then", label %"if.end", !dbg !79
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !80
  ret i32 %".10", !dbg !80
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 1 , !dbg !81
  %".13" = load i32, i32* %".12", !dbg !81
  %".14" = sext i32 %".13" to i64 , !dbg !81
  %".15" = icmp ne i64 %".14", 0 , !dbg !81
  br i1 %".15", label %"if.then.1", label %"if.end.1", !dbg !81
if.then.1:
  %".17" = trunc i64 1 to i32 , !dbg !82
  ret i32 %".17", !dbg !82
if.end.1:
  %".19" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 2 , !dbg !83
  %".20" = load i32, i32* %".19", !dbg !83
  %".21" = sext i32 %".20" to i64 , !dbg !83
  %".22" = icmp ne i64 %".21", 0 , !dbg !83
  br i1 %".22", label %"if.then.2", label %"if.end.2", !dbg !83
if.then.2:
  %".24" = trunc i64 1 to i32 , !dbg !84
  ret i32 %".24", !dbg !84
if.end.2:
  %".26" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 3 , !dbg !85
  %".27" = load i32, i32* %".26", !dbg !85
  %".28" = sext i32 %".27" to i64 , !dbg !85
  %".29" = icmp ne i64 %".28", 0 , !dbg !85
  br i1 %".29", label %"if.then.3", label %"if.end.3", !dbg !85
if.then.3:
  %".31" = trunc i64 1 to i32 , !dbg !86
  ret i32 %".31", !dbg !86
if.end.3:
  %".33" = trunc i64 0 to i32 , !dbg !87
  ret i32 %".33", !dbg !87
}

define %"struct.ritz_module_1.LayoutResult" @"layout_result_empty"() !dbg !22
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !88
  %".3" = trunc i64 0 to i32 , !dbg !88
  %".4" = trunc i64 0 to i32 , !dbg !88
  %".5" = trunc i64 0 to i32 , !dbg !88
  %".6" = trunc i64 0 to i32 , !dbg !88
  %".7" = trunc i64 0 to i32 , !dbg !88
  %".8" = trunc i64 0 to i32 , !dbg !88
  %".9" = trunc i64 0 to i32 , !dbg !88
  %".10" = trunc i64 0 to i32 , !dbg !88
  %".11" = trunc i64 0 to i32 , !dbg !88
  %".12" = trunc i64 0 to i32 , !dbg !88
  %".13" = trunc i64 0 to i32 , !dbg !88
  %".14" = trunc i64 0 to i32 , !dbg !88
  %".15" = trunc i64 0 to i32 , !dbg !88
  %".16" = trunc i64 0 to i32 , !dbg !88
  %".17" = trunc i64 0 to i32 , !dbg !88
  %".18" = trunc i64 0 to i32 , !dbg !88
  %".19" = insertvalue %"struct.ritz_module_1.LayoutResult" undef, i32 %".2", 0 , !dbg !88
  %".20" = insertvalue %"struct.ritz_module_1.LayoutResult" %".19", i32 %".3", 1 , !dbg !88
  %".21" = insertvalue %"struct.ritz_module_1.LayoutResult" %".20", i32 %".4", 2 , !dbg !88
  %".22" = insertvalue %"struct.ritz_module_1.LayoutResult" %".21", i32 %".5", 3 , !dbg !88
  %".23" = insertvalue %"struct.ritz_module_1.LayoutResult" %".22", i32 %".6", 4 , !dbg !88
  %".24" = insertvalue %"struct.ritz_module_1.LayoutResult" %".23", i32 %".7", 5 , !dbg !88
  %".25" = insertvalue %"struct.ritz_module_1.LayoutResult" %".24", i32 %".8", 6 , !dbg !88
  %".26" = insertvalue %"struct.ritz_module_1.LayoutResult" %".25", i32 %".9", 7 , !dbg !88
  %".27" = insertvalue %"struct.ritz_module_1.LayoutResult" %".26", i32 %".10", 8 , !dbg !88
  %".28" = insertvalue %"struct.ritz_module_1.LayoutResult" %".27", i32 %".11", 9 , !dbg !88
  %".29" = insertvalue %"struct.ritz_module_1.LayoutResult" %".28", i32 %".12", 10 , !dbg !88
  %".30" = insertvalue %"struct.ritz_module_1.LayoutResult" %".29", i32 %".13", 11 , !dbg !88
  %".31" = insertvalue %"struct.ritz_module_1.LayoutResult" %".30", i32 %".14", 12 , !dbg !88
  %".32" = insertvalue %"struct.ritz_module_1.LayoutResult" %".31", i32 %".15", 13 , !dbg !88
  %".33" = insertvalue %"struct.ritz_module_1.LayoutResult" %".32", i32 %".16", 14 , !dbg !88
  %".34" = insertvalue %"struct.ritz_module_1.LayoutResult" %".33", i32 %".17", 15 , !dbg !88
  %".35" = insertvalue %"struct.ritz_module_1.LayoutResult" %".34", i32 %".18", 16 , !dbg !88
  ret %"struct.ritz_module_1.LayoutResult" %".35", !dbg !88
}

define i32 @"layout_result_outer_width"(%"struct.ritz_module_1.LayoutResult" %"layout.arg") !dbg !23
{
entry:
  %"layout" = alloca %"struct.ritz_module_1.LayoutResult"
  store %"struct.ritz_module_1.LayoutResult" %"layout.arg", %"struct.ritz_module_1.LayoutResult"* %"layout"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayoutResult"* %"layout", metadata !90, metadata !7), !dbg !91
  %".5" = getelementptr %"struct.ritz_module_1.LayoutResult", %"struct.ritz_module_1.LayoutResult"* %"layout", i32 0, i32 7 , !dbg !92
  %".6" = load i32, i32* %".5", !dbg !92
  %".7" = getelementptr %"struct.ritz_module_1.LayoutResult", %"struct.ritz_module_1.LayoutResult"* %"layout", i32 0, i32 5 , !dbg !92
  %".8" = load i32, i32* %".7", !dbg !92
  %".9" = add i32 %".6", %".8", !dbg !92
  %".10" = getelementptr %"struct.ritz_module_1.LayoutResult", %"struct.ritz_module_1.LayoutResult"* %"layout", i32 0, i32 11 , !dbg !92
  %".11" = load i32, i32* %".10", !dbg !92
  %".12" = add i32 %".9", %".11", !dbg !92
  %".13" = getelementptr %"struct.ritz_module_1.LayoutResult", %"struct.ritz_module_1.LayoutResult"* %"layout", i32 0, i32 9 , !dbg !92
  %".14" = load i32, i32* %".13", !dbg !92
  %".15" = add i32 %".12", %".14", !dbg !92
  %".16" = getelementptr %"struct.ritz_module_1.LayoutResult", %"struct.ritz_module_1.LayoutResult"* %"layout", i32 0, i32 2 , !dbg !93
  %".17" = load i32, i32* %".16", !dbg !93
  %".18" = add i32 %".17", %".15", !dbg !93
  ret i32 %".18", !dbg !93
}

define i32 @"layout_result_outer_height"(%"struct.ritz_module_1.LayoutResult" %"layout.arg") !dbg !24
{
entry:
  %"layout" = alloca %"struct.ritz_module_1.LayoutResult"
  store %"struct.ritz_module_1.LayoutResult" %"layout.arg", %"struct.ritz_module_1.LayoutResult"* %"layout"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayoutResult"* %"layout", metadata !94, metadata !7), !dbg !95
  %".5" = getelementptr %"struct.ritz_module_1.LayoutResult", %"struct.ritz_module_1.LayoutResult"* %"layout", i32 0, i32 4 , !dbg !96
  %".6" = load i32, i32* %".5", !dbg !96
  %".7" = getelementptr %"struct.ritz_module_1.LayoutResult", %"struct.ritz_module_1.LayoutResult"* %"layout", i32 0, i32 6 , !dbg !96
  %".8" = load i32, i32* %".7", !dbg !96
  %".9" = add i32 %".6", %".8", !dbg !96
  %".10" = getelementptr %"struct.ritz_module_1.LayoutResult", %"struct.ritz_module_1.LayoutResult"* %"layout", i32 0, i32 8 , !dbg !96
  %".11" = load i32, i32* %".10", !dbg !96
  %".12" = add i32 %".9", %".11", !dbg !96
  %".13" = getelementptr %"struct.ritz_module_1.LayoutResult", %"struct.ritz_module_1.LayoutResult"* %"layout", i32 0, i32 10 , !dbg !96
  %".14" = load i32, i32* %".13", !dbg !96
  %".15" = add i32 %".12", %".14", !dbg !96
  %".16" = getelementptr %"struct.ritz_module_1.LayoutResult", %"struct.ritz_module_1.LayoutResult"* %"layout", i32 0, i32 3 , !dbg !97
  %".17" = load i32, i32* %".16", !dbg !97
  %".18" = add i32 %".17", %".15", !dbg !97
  ret i32 %".18", !dbg !97
}

define %"struct.ritz_module_1.RenderNode" @"render_node_new"(%"struct.ritz_module_1.NodeId" %"id.arg", i32 %"tag.arg", %"struct.ritz_module_1.ComputedStyle" %"style.arg") !dbg !25
{
entry:
  %"id" = alloca %"struct.ritz_module_1.NodeId"
  store %"struct.ritz_module_1.NodeId" %"id.arg", %"struct.ritz_module_1.NodeId"* %"id"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.NodeId"* %"id", metadata !99, metadata !7), !dbg !100
  %"tag" = alloca i32
  store i32 %"tag.arg", i32* %"tag"
  call void @"llvm.dbg.declare"(metadata i32* %"tag", metadata !101, metadata !7), !dbg !100
  %"style" = alloca %"struct.ritz_module_1.ComputedStyle"
  store %"struct.ritz_module_1.ComputedStyle" %"style.arg", %"struct.ritz_module_1.ComputedStyle"* %"style"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ComputedStyle"* %"style", metadata !103, metadata !7), !dbg !100
  %".11" = load %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %"id", !dbg !104
  %".12" = load i32, i32* %"tag", !dbg !104
  %".13" = trunc i64 0 to i32 , !dbg !104
  %".14" = trunc i64 0 to i32 , !dbg !104
  %".15" = trunc i64 0 to i32 , !dbg !104
  %".16" = trunc i64 0 to i32 , !dbg !104
  %".17" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style", !dbg !104
  %".18" = call %"struct.ritz_module_1.NodeId" @"node_id_invalid"(), !dbg !104
  %".19" = call %"struct.ritz_module_1.NodeId" @"node_id_invalid"(), !dbg !104
  %".20" = call %"struct.ritz_module_1.NodeId" @"node_id_invalid"(), !dbg !104
  %".21" = call %"struct.ritz_module_1.NodeId" @"node_id_invalid"(), !dbg !104
  %".22" = call %"struct.ritz_module_1.NodeId" @"node_id_invalid"(), !dbg !104
  %".23" = trunc i64 0 to i32 , !dbg !104
  %".24" = call %"struct.ritz_module_1.LayoutResult" @"layout_result_empty"(), !dbg !104
  %".25" = call %"struct.ritz_module_1.DirtyFlags" @"dirty_flags_all"(), !dbg !104
  %".26" = insertvalue %"struct.ritz_module_1.RenderNode" undef, %"struct.ritz_module_1.NodeId" %".11", 0 , !dbg !104
  %".27" = insertvalue %"struct.ritz_module_1.RenderNode" %".26", i32 %".12", 1 , !dbg !104
  %".28" = insertvalue %"struct.ritz_module_1.RenderNode" %".27", i32 0, 2 , !dbg !104
  %".29" = insertvalue %"struct.ritz_module_1.RenderNode" %".28", i8* null, 3 , !dbg !104
  %".30" = insertvalue %"struct.ritz_module_1.RenderNode" %".29", i32 %".13", 4 , !dbg !104
  %".31" = insertvalue %"struct.ritz_module_1.RenderNode" %".30", i32 %".14", 5 , !dbg !104
  %".32" = insertvalue %"struct.ritz_module_1.RenderNode" %".31", i32 %".15", 6 , !dbg !104
  %".33" = insertvalue %"struct.ritz_module_1.RenderNode" %".32", i32 %".16", 7 , !dbg !104
  %".34" = insertvalue %"struct.ritz_module_1.RenderNode" %".33", %"struct.ritz_module_1.ComputedStyle" %".17", 8 , !dbg !104
  %".35" = insertvalue %"struct.ritz_module_1.RenderNode" %".34", %"struct.ritz_module_1.NodeId" %".18", 9 , !dbg !104
  %".36" = insertvalue %"struct.ritz_module_1.RenderNode" %".35", %"struct.ritz_module_1.NodeId" %".19", 10 , !dbg !104
  %".37" = insertvalue %"struct.ritz_module_1.RenderNode" %".36", %"struct.ritz_module_1.NodeId" %".20", 11 , !dbg !104
  %".38" = insertvalue %"struct.ritz_module_1.RenderNode" %".37", %"struct.ritz_module_1.NodeId" %".21", 12 , !dbg !104
  %".39" = insertvalue %"struct.ritz_module_1.RenderNode" %".38", %"struct.ritz_module_1.NodeId" %".22", 13 , !dbg !104
  %".40" = insertvalue %"struct.ritz_module_1.RenderNode" %".39", i32 %".23", 14 , !dbg !104
  %".41" = insertvalue %"struct.ritz_module_1.RenderNode" %".40", %"struct.ritz_module_1.LayoutResult" %".24", 15 , !dbg !104
  %".42" = insertvalue %"struct.ritz_module_1.RenderNode" %".41", %"struct.ritz_module_1.DirtyFlags" %".25", 16 , !dbg !104
  %".43" = insertvalue %"struct.ritz_module_1.RenderNode" %".42", i64 0, 17 , !dbg !104
  ret %"struct.ritz_module_1.RenderNode" %".43", !dbg !104
}

define %"struct.ritz_module_1.RenderNode" @"render_node_new_text"(%"struct.ritz_module_1.NodeId" %"id.arg", i8* %"text_ptr.arg", i32 %"text_len.arg", %"struct.ritz_module_1.ComputedStyle" %"style.arg") !dbg !26
{
entry:
  %"id" = alloca %"struct.ritz_module_1.NodeId"
  %"node.addr" = alloca %"struct.ritz_module_1.RenderNode", !dbg !111
  store %"struct.ritz_module_1.NodeId" %"id.arg", %"struct.ritz_module_1.NodeId"* %"id"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.NodeId"* %"id", metadata !105, metadata !7), !dbg !106
  %"text_ptr" = alloca i8*
  store i8* %"text_ptr.arg", i8** %"text_ptr"
  call void @"llvm.dbg.declare"(metadata i8** %"text_ptr", metadata !108, metadata !7), !dbg !106
  %"text_len" = alloca i32
  store i32 %"text_len.arg", i32* %"text_len"
  call void @"llvm.dbg.declare"(metadata i32* %"text_len", metadata !109, metadata !7), !dbg !106
  %"style" = alloca %"struct.ritz_module_1.ComputedStyle"
  store %"struct.ritz_module_1.ComputedStyle" %"style.arg", %"struct.ritz_module_1.ComputedStyle"* %"style"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ComputedStyle"* %"style", metadata !110, metadata !7), !dbg !106
  %".14" = load %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %"id", !dbg !111
  %".15" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style", !dbg !111
  %".16" = call %"struct.ritz_module_1.RenderNode" @"render_node_new"(%"struct.ritz_module_1.NodeId" %".14", i32 100, %"struct.ritz_module_1.ComputedStyle" %".15"), !dbg !111
  store %"struct.ritz_module_1.RenderNode" %".16", %"struct.ritz_module_1.RenderNode"* %"node.addr", !dbg !111
  %".18" = load %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node.addr", !dbg !112
  %".19" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node.addr", i32 0, i32 2 , !dbg !112
  store i32 1, i32* %".19", !dbg !112
  %".21" = load i8*, i8** %"text_ptr", !dbg !113
  %".22" = load %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node.addr", !dbg !113
  %".23" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node.addr", i32 0, i32 3 , !dbg !113
  store i8* %".21", i8** %".23", !dbg !113
  %".25" = load i32, i32* %"text_len", !dbg !114
  %".26" = load %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node.addr", !dbg !114
  %".27" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node.addr", i32 0, i32 4 , !dbg !114
  store i32 %".25", i32* %".27", !dbg !114
  %".29" = load %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node.addr", !dbg !115
  ret %"struct.ritz_module_1.RenderNode" %".29", !dbg !115
}

define i32 @"render_node_is_text"(%"struct.ritz_module_1.RenderNode" %"node.arg") !dbg !27
{
entry:
  %"node" = alloca %"struct.ritz_module_1.RenderNode"
  store %"struct.ritz_module_1.RenderNode" %"node.arg", %"struct.ritz_module_1.RenderNode"* %"node"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderNode"* %"node", metadata !117, metadata !7), !dbg !118
  %".5" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node", i32 0, i32 2 , !dbg !119
  %".6" = load i32, i32* %".5", !dbg !119
  %".7" = icmp eq i32 %".6", 1 , !dbg !119
  br i1 %".7", label %"if.then", label %"if.end", !dbg !119
if.then:
  %".9" = trunc i64 1 to i32 , !dbg !120
  ret i32 %".9", !dbg !120
if.end:
  %".11" = trunc i64 0 to i32 , !dbg !121
  ret i32 %".11", !dbg !121
}

define i32 @"render_node_is_replaced"(%"struct.ritz_module_1.RenderNode" %"node.arg") !dbg !28
{
entry:
  %"node" = alloca %"struct.ritz_module_1.RenderNode"
  store %"struct.ritz_module_1.RenderNode" %"node.arg", %"struct.ritz_module_1.RenderNode"* %"node"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderNode"* %"node", metadata !122, metadata !7), !dbg !123
  %".5" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node", i32 0, i32 2 , !dbg !124
  %".6" = load i32, i32* %".5", !dbg !124
  %".7" = icmp eq i32 %".6", 2 , !dbg !124
  br i1 %".7", label %"if.then", label %"if.end", !dbg !124
if.then:
  %".9" = trunc i64 1 to i32 , !dbg !125
  ret i32 %".9", !dbg !125
if.end:
  %".11" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node", i32 0, i32 2 , !dbg !126
  %".12" = load i32, i32* %".11", !dbg !126
  %".13" = icmp eq i32 %".12", 3 , !dbg !126
  br i1 %".13", label %"if.then.1", label %"if.end.1", !dbg !126
if.then.1:
  %".15" = trunc i64 1 to i32 , !dbg !127
  ret i32 %".15", !dbg !127
if.end.1:
  %".17" = trunc i64 0 to i32 , !dbg !128
  ret i32 %".17", !dbg !128
}

define i32 @"render_node_has_children"(%"struct.ritz_module_1.RenderNode" %"node.arg") !dbg !29
{
entry:
  %"node" = alloca %"struct.ritz_module_1.RenderNode"
  store %"struct.ritz_module_1.RenderNode" %"node.arg", %"struct.ritz_module_1.RenderNode"* %"node"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderNode"* %"node", metadata !129, metadata !7), !dbg !130
  %".5" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node", i32 0, i32 14 , !dbg !131
  %".6" = load i32, i32* %".5", !dbg !131
  %".7" = zext i32 %".6" to i64 , !dbg !131
  %".8" = icmp ugt i64 %".7", 0 , !dbg !131
  br i1 %".8", label %"if.then", label %"if.end", !dbg !131
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !132
  ret i32 %".10", !dbg !132
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !133
  ret i32 %".12", !dbg !133
}

define i32 @"render_node_is_block"(%"struct.ritz_module_1.RenderNode" %"node.arg") !dbg !30
{
entry:
  %"node" = alloca %"struct.ritz_module_1.RenderNode"
  store %"struct.ritz_module_1.RenderNode" %"node.arg", %"struct.ritz_module_1.RenderNode"* %"node"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderNode"* %"node", metadata !134, metadata !7), !dbg !135
  %".5" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node", i32 0, i32 8 , !dbg !136
  %".6" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %".5", !dbg !136
  %".7" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".6", 0 , !dbg !136
  %".8" = icmp eq i32 %".7", 1 , !dbg !137
  br i1 %".8", label %"if.then", label %"if.end", !dbg !137
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !138
  ret i32 %".10", !dbg !138
if.end:
  %".12" = icmp eq i32 %".7", 4 , !dbg !139
  br i1 %".12", label %"if.then.1", label %"if.end.1", !dbg !139
if.then.1:
  %".14" = trunc i64 1 to i32 , !dbg !140
  ret i32 %".14", !dbg !140
if.end.1:
  %".16" = icmp eq i32 %".7", 6 , !dbg !141
  br i1 %".16", label %"if.then.2", label %"if.end.2", !dbg !141
if.then.2:
  %".18" = trunc i64 1 to i32 , !dbg !142
  ret i32 %".18", !dbg !142
if.end.2:
  %".20" = trunc i64 0 to i32 , !dbg !143
  ret i32 %".20", !dbg !143
}

define i32 @"render_node_is_inline"(%"struct.ritz_module_1.RenderNode" %"node.arg") !dbg !31
{
entry:
  %"node" = alloca %"struct.ritz_module_1.RenderNode"
  store %"struct.ritz_module_1.RenderNode" %"node.arg", %"struct.ritz_module_1.RenderNode"* %"node"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderNode"* %"node", metadata !144, metadata !7), !dbg !145
  %".5" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node", i32 0, i32 8 , !dbg !146
  %".6" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %".5", !dbg !146
  %".7" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".6", 0 , !dbg !146
  %".8" = icmp eq i32 %".7", 2 , !dbg !147
  br i1 %".8", label %"if.then", label %"if.end", !dbg !147
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !148
  ret i32 %".10", !dbg !148
if.end:
  %".12" = icmp eq i32 %".7", 3 , !dbg !149
  br i1 %".12", label %"if.then.1", label %"if.end.1", !dbg !149
if.then.1:
  %".14" = trunc i64 1 to i32 , !dbg !150
  ret i32 %".14", !dbg !150
if.end.1:
  %".16" = icmp eq i32 %".7", 5 , !dbg !151
  br i1 %".16", label %"if.then.2", label %"if.end.2", !dbg !151
if.then.2:
  %".18" = trunc i64 1 to i32 , !dbg !152
  ret i32 %".18", !dbg !152
if.end.2:
  %".20" = icmp eq i32 %".7", 7 , !dbg !153
  br i1 %".20", label %"if.then.3", label %"if.end.3", !dbg !153
if.then.3:
  %".22" = trunc i64 1 to i32 , !dbg !154
  ret i32 %".22", !dbg !154
if.end.3:
  %".24" = trunc i64 0 to i32 , !dbg !155
  ret i32 %".24", !dbg !155
}

define i32 @"render_node_generates_layer"(%"struct.ritz_module_1.RenderNode" %"node.arg") !dbg !32
{
entry:
  %"node" = alloca %"struct.ritz_module_1.RenderNode"
  store %"struct.ritz_module_1.RenderNode" %"node.arg", %"struct.ritz_module_1.RenderNode"* %"node"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderNode"* %"node", metadata !156, metadata !7), !dbg !157
  %".5" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node", i32 0, i32 8 , !dbg !158
  %".6" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %".5", !dbg !158
  %".7" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".6", 19 , !dbg !158
  %".8" = fcmp olt double %".7", 0x3ff0000000000000 , !dbg !158
  br i1 %".8", label %"if.then", label %"if.end", !dbg !158
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !159
  ret i32 %".10", !dbg !159
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node", i32 0, i32 8 , !dbg !160
  %".13" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %".12", !dbg !160
  %".14" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".13", 20 , !dbg !160
  %".15" = call i32 @"transform_is_identity"(%"struct.ritz_module_1.Transform" %".14"), !dbg !160
  %".16" = sext i32 %".15" to i64 , !dbg !160
  %".17" = icmp eq i64 %".16", 0 , !dbg !160
  br i1 %".17", label %"if.then.1", label %"if.end.1", !dbg !160
if.then.1:
  %".19" = trunc i64 1 to i32 , !dbg !161
  ret i32 %".19", !dbg !161
if.end.1:
  %".21" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node", i32 0, i32 8 , !dbg !162
  %".22" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %".21", !dbg !162
  %".23" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".22", 1 , !dbg !162
  %".24" = icmp eq i32 %".23", 3 , !dbg !162
  br i1 %".24", label %"if.then.2", label %"if.end.2", !dbg !162
if.then.2:
  %".26" = trunc i64 1 to i32 , !dbg !163
  ret i32 %".26", !dbg !163
if.end.2:
  %".28" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node", i32 0, i32 8 , !dbg !164
  %".29" = load %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %".28", !dbg !164
  %".30" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".29", 1 , !dbg !164
  %".31" = icmp eq i32 %".30", 4 , !dbg !164
  br i1 %".31", label %"if.then.3", label %"if.end.3", !dbg !164
if.then.3:
  %".33" = trunc i64 1 to i32 , !dbg !165
  ret i32 %".33", !dbg !165
if.end.3:
  %".35" = trunc i64 0 to i32 , !dbg !166
  ret i32 %".35", !dbg !166
}

define %"struct.ritz_module_1.RenderTree" @"render_tree_new"() !dbg !33
{
entry:
  %".2" = call %"struct.ritz_module_1.Vec$RenderNode" @"vec_new$RenderNode"(), !dbg !167
  %".3" = call %"struct.ritz_module_1.HashMapI64" @"hashmap_i64_new"(), !dbg !167
  %".4" = call %"struct.ritz_module_1.NodeId" @"node_id_invalid"(), !dbg !167
  %".5" = insertvalue %"struct.ritz_module_1.RenderTree" undef, %"struct.ritz_module_1.Vec$RenderNode" %".2", 0 , !dbg !167
  %".6" = insertvalue %"struct.ritz_module_1.RenderTree" %".5", %"struct.ritz_module_1.HashMapI64" %".3", 1 , !dbg !167
  %".7" = insertvalue %"struct.ritz_module_1.RenderTree" %".6", %"struct.ritz_module_1.NodeId" %".4", 2 , !dbg !167
  ret %"struct.ritz_module_1.RenderTree" %".7", !dbg !167
}

define %"struct.ritz_module_1.RenderNode"* @"render_tree_get"(%"struct.ritz_module_1.RenderTree"* %"tree.arg", %"struct.ritz_module_1.NodeId"* %"id.arg") !dbg !34
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderTree"* %"tree.arg", metadata !170, metadata !7), !dbg !171
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.NodeId"* %"id.arg", metadata !173, metadata !7), !dbg !171
  %".6" = getelementptr %"struct.ritz_module_1.RenderTree", %"struct.ritz_module_1.RenderTree"* %"tree.arg", i32 0, i32 1 , !dbg !174
  %".7" = getelementptr %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %"id.arg", i32 0, i32 0 , !dbg !174
  %".8" = load i64, i64* %".7", !dbg !174
  %".9" = call i64 @"hashmap_i64_get"(%"struct.ritz_module_1.HashMapI64"* %".6", i64 %".8"), !dbg !174
  %".10" = icmp slt i64 %".9", 0 , !dbg !175
  br i1 %".10", label %"if.then", label %"if.end", !dbg !175
if.then:
  %".12" = bitcast i8* null to %"struct.ritz_module_1.RenderNode"* , !dbg !176
  ret %"struct.ritz_module_1.RenderNode"* %".12", !dbg !176
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.RenderTree", %"struct.ritz_module_1.RenderTree"* %"tree.arg", i32 0, i32 0 , !dbg !177
  %".15" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %".14", !dbg !177
  %".16" = extractvalue %"struct.ritz_module_1.Vec$RenderNode" %".15", 1 , !dbg !177
  %".17" = icmp sge i64 %".9", %".16" , !dbg !177
  br i1 %".17", label %"if.then.1", label %"if.end.1", !dbg !177
if.then.1:
  %".19" = bitcast i8* null to %"struct.ritz_module_1.RenderNode"* , !dbg !178
  ret %"struct.ritz_module_1.RenderNode"* %".19", !dbg !178
if.end.1:
  %".21" = getelementptr %"struct.ritz_module_1.RenderTree", %"struct.ritz_module_1.RenderTree"* %"tree.arg", i32 0, i32 0 , !dbg !179
  %".22" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %".21", !dbg !179
  %".23" = extractvalue %"struct.ritz_module_1.Vec$RenderNode" %".22", 0 , !dbg !179
  %".24" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".23", i64 %".9" , !dbg !179
  ret %"struct.ritz_module_1.RenderNode"* %".24", !dbg !179
}

define %"struct.ritz_module_1.RenderNode"* @"render_tree_get_mut"(%"struct.ritz_module_1.RenderTree"* %"tree.arg", %"struct.ritz_module_1.NodeId"* %"id.arg") !dbg !35
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderTree"* %"tree.arg", metadata !180, metadata !7), !dbg !181
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.NodeId"* %"id.arg", metadata !182, metadata !7), !dbg !181
  %".6" = getelementptr %"struct.ritz_module_1.RenderTree", %"struct.ritz_module_1.RenderTree"* %"tree.arg", i32 0, i32 1 , !dbg !183
  %".7" = getelementptr %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %"id.arg", i32 0, i32 0 , !dbg !183
  %".8" = load i64, i64* %".7", !dbg !183
  %".9" = call i64 @"hashmap_i64_get"(%"struct.ritz_module_1.HashMapI64"* %".6", i64 %".8"), !dbg !183
  %".10" = icmp slt i64 %".9", 0 , !dbg !184
  br i1 %".10", label %"if.then", label %"if.end", !dbg !184
if.then:
  %".12" = bitcast i8* null to %"struct.ritz_module_1.RenderNode"* , !dbg !185
  ret %"struct.ritz_module_1.RenderNode"* %".12", !dbg !185
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.RenderTree", %"struct.ritz_module_1.RenderTree"* %"tree.arg", i32 0, i32 0 , !dbg !186
  %".15" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %".14", !dbg !186
  %".16" = extractvalue %"struct.ritz_module_1.Vec$RenderNode" %".15", 1 , !dbg !186
  %".17" = icmp sge i64 %".9", %".16" , !dbg !186
  br i1 %".17", label %"if.then.1", label %"if.end.1", !dbg !186
if.then.1:
  %".19" = bitcast i8* null to %"struct.ritz_module_1.RenderNode"* , !dbg !187
  ret %"struct.ritz_module_1.RenderNode"* %".19", !dbg !187
if.end.1:
  %".21" = getelementptr %"struct.ritz_module_1.RenderTree", %"struct.ritz_module_1.RenderTree"* %"tree.arg", i32 0, i32 0 , !dbg !188
  %".22" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %".21", !dbg !188
  %".23" = extractvalue %"struct.ritz_module_1.Vec$RenderNode" %".22", 0 , !dbg !188
  %".24" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".23", i64 %".9" , !dbg !188
  ret %"struct.ritz_module_1.RenderNode"* %".24", !dbg !188
}

define i32 @"render_tree_insert"(%"struct.ritz_module_1.RenderTree"* %"tree.arg", %"struct.ritz_module_1.RenderNode" %"node.arg") !dbg !36
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderTree"* %"tree.arg", metadata !189, metadata !7), !dbg !190
  %"node" = alloca %"struct.ritz_module_1.RenderNode"
  store %"struct.ritz_module_1.RenderNode" %"node.arg", %"struct.ritz_module_1.RenderNode"* %"node"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderNode"* %"node", metadata !191, metadata !7), !dbg !190
  %".7" = getelementptr %"struct.ritz_module_1.RenderTree", %"struct.ritz_module_1.RenderTree"* %"tree.arg", i32 0, i32 0 , !dbg !192
  %".8" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %".7", !dbg !192
  %".9" = extractvalue %"struct.ritz_module_1.Vec$RenderNode" %".8", 1 , !dbg !192
  %".10" = getelementptr %"struct.ritz_module_1.RenderTree", %"struct.ritz_module_1.RenderTree"* %"tree.arg", i32 0, i32 1 , !dbg !193
  %".11" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node", i32 0, i32 0 , !dbg !193
  %".12" = load %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %".11", !dbg !193
  %".13" = extractvalue %"struct.ritz_module_1.NodeId" %".12", 0 , !dbg !193
  %".14" = call i32 @"hashmap_i64_insert"(%"struct.ritz_module_1.HashMapI64"* %".10", i64 %".13", i64 %".9"), !dbg !193
  %".15" = getelementptr %"struct.ritz_module_1.RenderTree", %"struct.ritz_module_1.RenderTree"* %"tree.arg", i32 0, i32 0 , !dbg !194
  %".16" = load %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node", !dbg !194
  %".17" = call i32 @"vec_push$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %".15", %"struct.ritz_module_1.RenderNode" %".16"), !dbg !194
  ret i32 %".17", !dbg !194
}

define i32 @"render_tree_set_root"(%"struct.ritz_module_1.RenderTree"* %"tree.arg", %"struct.ritz_module_1.NodeId" %"id.arg") !dbg !37
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderTree"* %"tree.arg", metadata !195, metadata !7), !dbg !196
  %"id" = alloca %"struct.ritz_module_1.NodeId"
  store %"struct.ritz_module_1.NodeId" %"id.arg", %"struct.ritz_module_1.NodeId"* %"id"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.NodeId"* %"id", metadata !197, metadata !7), !dbg !196
  %".7" = load %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %"id", !dbg !198
  %".8" = getelementptr %"struct.ritz_module_1.RenderTree", %"struct.ritz_module_1.RenderTree"* %"tree.arg", i32 0, i32 2 , !dbg !198
  store %"struct.ritz_module_1.NodeId" %".7", %"struct.ritz_module_1.NodeId"* %".8", !dbg !198
  ret i32 0, !dbg !198
}

define %"struct.ritz_module_1.RenderNode"* @"render_tree_root"(%"struct.ritz_module_1.RenderTree"* %"tree.arg") !dbg !38
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderTree"* %"tree.arg", metadata !199, metadata !7), !dbg !200
  %".4" = getelementptr %"struct.ritz_module_1.RenderTree", %"struct.ritz_module_1.RenderTree"* %"tree.arg", i32 0, i32 2 , !dbg !201
  %".5" = call %"struct.ritz_module_1.RenderNode"* @"render_tree_get"(%"struct.ritz_module_1.RenderTree"* %"tree.arg", %"struct.ritz_module_1.NodeId"* %".4"), !dbg !201
  ret %"struct.ritz_module_1.RenderNode"* %".5", !dbg !201
}

define i32 @"render_tree_count"(%"struct.ritz_module_1.RenderTree"* %"tree.arg") !dbg !39
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderTree"* %"tree.arg", metadata !202, metadata !7), !dbg !203
  %".4" = getelementptr %"struct.ritz_module_1.RenderTree", %"struct.ritz_module_1.RenderTree"* %"tree.arg", i32 0, i32 1 , !dbg !204
  %".5" = load %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %".4", !dbg !204
  %".6" = extractvalue %"struct.ritz_module_1.HashMapI64" %".5", 2 , !dbg !204
  %".7" = trunc i64 %".6" to i32 , !dbg !204
  ret i32 %".7", !dbg !204
}

define i32 @"render_tree_is_empty"(%"struct.ritz_module_1.RenderTree"* %"tree.arg") !dbg !40
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderTree"* %"tree.arg", metadata !205, metadata !7), !dbg !206
  %".4" = getelementptr %"struct.ritz_module_1.RenderTree", %"struct.ritz_module_1.RenderTree"* %"tree.arg", i32 0, i32 2 , !dbg !207
  %".5" = call i32 @"node_id_is_valid"(%"struct.ritz_module_1.NodeId"* %".4"), !dbg !207
  %".6" = sext i32 %".5" to i64 , !dbg !207
  %".7" = icmp ne i64 %".6", 0 , !dbg !207
  br i1 %".7", label %"if.then", label %"if.end", !dbg !207
if.then:
  %".9" = trunc i64 0 to i32 , !dbg !208
  ret i32 %".9", !dbg !208
if.end:
  %".11" = trunc i64 1 to i32 , !dbg !209
  ret i32 %".11", !dbg !209
}

define i32 @"render_tree_mark_dirty"(%"struct.ritz_module_1.RenderTree"* %"tree.arg", %"struct.ritz_module_1.NodeId" %"id.arg", %"struct.ritz_module_1.DirtyFlags" %"flags.arg") !dbg !41
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderTree"* %"tree.arg", metadata !210, metadata !7), !dbg !211
  %"id" = alloca %"struct.ritz_module_1.NodeId"
  store %"struct.ritz_module_1.NodeId" %"id.arg", %"struct.ritz_module_1.NodeId"* %"id"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.NodeId"* %"id", metadata !212, metadata !7), !dbg !211
  %"flags" = alloca %"struct.ritz_module_1.DirtyFlags"
  store %"struct.ritz_module_1.DirtyFlags" %"flags.arg", %"struct.ritz_module_1.DirtyFlags"* %"flags"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.DirtyFlags"* %"flags", metadata !213, metadata !7), !dbg !211
  %".10" = call %"struct.ritz_module_1.RenderNode"* @"render_tree_get_mut"(%"struct.ritz_module_1.RenderTree"* %"tree.arg", %"struct.ritz_module_1.NodeId"* %"id"), !dbg !214
  %".11" = icmp eq %"struct.ritz_module_1.RenderNode"* %".10", null , !dbg !215
  br i1 %".11", label %"if.then", label %"if.end", !dbg !215
if.then:
  ret i32 0, !dbg !216
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 0 , !dbg !217
  %".15" = load i32, i32* %".14", !dbg !217
  %".16" = sext i32 %".15" to i64 , !dbg !217
  %".17" = icmp ne i64 %".16", 0 , !dbg !217
  br i1 %".17", label %"if.then.1", label %"if.end.1", !dbg !217
if.then.1:
  %".19" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".10", i32 0, i32 16 , !dbg !218
  %".20" = load %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %".19", !dbg !218
  %".21" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".10", i32 0, i32 16 , !dbg !218
  %".22" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %".21", i32 0, i32 0 , !dbg !218
  %".23" = trunc i64 1 to i32 , !dbg !218
  store i32 %".23", i32* %".22", !dbg !218
  br label %"if.end.1", !dbg !218
if.end.1:
  %".26" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 1 , !dbg !219
  %".27" = load i32, i32* %".26", !dbg !219
  %".28" = sext i32 %".27" to i64 , !dbg !219
  %".29" = icmp ne i64 %".28", 0 , !dbg !219
  br i1 %".29", label %"if.then.2", label %"if.end.2", !dbg !219
if.then.2:
  %".31" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".10", i32 0, i32 16 , !dbg !220
  %".32" = load %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %".31", !dbg !220
  %".33" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".10", i32 0, i32 16 , !dbg !220
  %".34" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %".33", i32 0, i32 1 , !dbg !220
  %".35" = trunc i64 1 to i32 , !dbg !220
  store i32 %".35", i32* %".34", !dbg !220
  br label %"if.end.2", !dbg !220
if.end.2:
  %".38" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 2 , !dbg !221
  %".39" = load i32, i32* %".38", !dbg !221
  %".40" = sext i32 %".39" to i64 , !dbg !221
  %".41" = icmp ne i64 %".40", 0 , !dbg !221
  br i1 %".41", label %"if.then.3", label %"if.end.3", !dbg !221
if.then.3:
  %".43" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".10", i32 0, i32 16 , !dbg !222
  %".44" = load %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %".43", !dbg !222
  %".45" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".10", i32 0, i32 16 , !dbg !222
  %".46" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %".45", i32 0, i32 2 , !dbg !222
  %".47" = trunc i64 1 to i32 , !dbg !222
  store i32 %".47", i32* %".46", !dbg !222
  br label %"if.end.3", !dbg !222
if.end.3:
  %".50" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %"flags", i32 0, i32 3 , !dbg !223
  %".51" = load i32, i32* %".50", !dbg !223
  %".52" = sext i32 %".51" to i64 , !dbg !223
  %".53" = icmp ne i64 %".52", 0 , !dbg !223
  br i1 %".53", label %"if.then.4", label %"if.end.4", !dbg !223
if.then.4:
  %".55" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".10", i32 0, i32 16 , !dbg !224
  %".56" = load %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %".55", !dbg !224
  %".57" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".10", i32 0, i32 16 , !dbg !224
  %".58" = getelementptr %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %".57", i32 0, i32 3 , !dbg !224
  %".59" = trunc i64 1 to i32 , !dbg !224
  store i32 %".59", i32* %".58", !dbg !224
  br label %"if.end.4", !dbg !224
if.end.4:
  ret i32 0, !dbg !224
}

define i32 @"render_tree_clear_dirty"(%"struct.ritz_module_1.RenderTree"* %"tree.arg", %"struct.ritz_module_1.NodeId" %"id.arg") !dbg !42
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderTree"* %"tree.arg", metadata !225, metadata !7), !dbg !226
  %"id" = alloca %"struct.ritz_module_1.NodeId"
  store %"struct.ritz_module_1.NodeId" %"id.arg", %"struct.ritz_module_1.NodeId"* %"id"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.NodeId"* %"id", metadata !227, metadata !7), !dbg !226
  %".7" = call %"struct.ritz_module_1.RenderNode"* @"render_tree_get_mut"(%"struct.ritz_module_1.RenderTree"* %"tree.arg", %"struct.ritz_module_1.NodeId"* %"id"), !dbg !228
  %".8" = icmp ne %"struct.ritz_module_1.RenderNode"* %".7", null , !dbg !229
  br i1 %".8", label %"if.then", label %"if.end", !dbg !229
if.then:
  %".10" = call %"struct.ritz_module_1.DirtyFlags" @"dirty_flags_none"(), !dbg !230
  %".11" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".7", i32 0, i32 16 , !dbg !230
  store %"struct.ritz_module_1.DirtyFlags" %".10", %"struct.ritz_module_1.DirtyFlags"* %".11", !dbg !230
  br label %"if.end", !dbg !230
if.end:
  ret i32 0, !dbg !230
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !43
{
entry:
  %"i" = alloca i64, !dbg !237
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !233, metadata !7), !dbg !234
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !235, metadata !7), !dbg !234
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !236, metadata !7), !dbg !234
  %".10" = load i64, i64* %"len", !dbg !237
  store i64 0, i64* %"i", !dbg !237
  br label %"for.cond", !dbg !237
for.cond:
  %".13" = load i64, i64* %"i", !dbg !237
  %".14" = icmp slt i64 %".13", %".10" , !dbg !237
  br i1 %".14", label %"for.body", label %"for.end", !dbg !237
for.body:
  %".16" = load i8*, i8** %"data", !dbg !237
  %".17" = load i64, i64* %"i", !dbg !237
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !237
  %".19" = load i8, i8* %".18", !dbg !237
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !237
  %".21" = sext i32 %".20" to i64 , !dbg !237
  %".22" = icmp ne i64 %".21", 0 , !dbg !237
  br i1 %".22", label %"if.then", label %"if.end", !dbg !237
for.incr:
  %".28" = load i64, i64* %"i", !dbg !238
  %".29" = add i64 %".28", 1, !dbg !238
  store i64 %".29", i64* %"i", !dbg !238
  br label %"for.cond", !dbg !238
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !239
  ret i32 %".32", !dbg !239
if.then:
  %".24" = sub i64 0, 1, !dbg !238
  %".25" = trunc i64 %".24" to i32 , !dbg !238
  ret i32 %".25", !dbg !238
if.end:
  br label %"for.incr", !dbg !238
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !44
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !240, metadata !7), !dbg !241
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !242, metadata !7), !dbg !241
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !243
  %".8" = load i64, i64* %".7", !dbg !243
  %".9" = add i64 %".8", 1, !dbg !243
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !243
  %".11" = sext i32 %".10" to i64 , !dbg !243
  %".12" = icmp ne i64 %".11", 0 , !dbg !243
  br i1 %".12", label %"if.then", label %"if.end", !dbg !243
if.then:
  %".14" = sub i64 0, 1, !dbg !244
  %".15" = trunc i64 %".14" to i32 , !dbg !244
  ret i32 %".15", !dbg !244
if.end:
  %".17" = load i8, i8* %"item", !dbg !245
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !245
  %".19" = load i8*, i8** %".18", !dbg !245
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !245
  %".21" = load i64, i64* %".20", !dbg !245
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !245
  store i8 %".17", i8* %".22", !dbg !245
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !246
  %".25" = load i64, i64* %".24", !dbg !246
  %".26" = add i64 %".25", 1, !dbg !246
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !246
  store i64 %".26", i64* %".27", !dbg !246
  %".29" = trunc i64 0 to i32 , !dbg !247
  ret i32 %".29", !dbg !247
}

define linkonce_odr i32 @"vec_push$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", %"struct.ritz_module_1.RenderNode" %"item.arg") !dbg !45
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", metadata !250, metadata !7), !dbg !251
  %"item" = alloca %"struct.ritz_module_1.RenderNode"
  store %"struct.ritz_module_1.RenderNode" %"item.arg", %"struct.ritz_module_1.RenderNode"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderNode"* %"item", metadata !252, metadata !7), !dbg !251
  %".7" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 1 , !dbg !253
  %".8" = load i64, i64* %".7", !dbg !253
  %".9" = add i64 %".8", 1, !dbg !253
  %".10" = call i32 @"vec_ensure_cap$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i64 %".9"), !dbg !253
  %".11" = sext i32 %".10" to i64 , !dbg !253
  %".12" = icmp ne i64 %".11", 0 , !dbg !253
  br i1 %".12", label %"if.then", label %"if.end", !dbg !253
if.then:
  %".14" = sub i64 0, 1, !dbg !254
  %".15" = trunc i64 %".14" to i32 , !dbg !254
  ret i32 %".15", !dbg !254
if.end:
  %".17" = load %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"item", !dbg !255
  %".18" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 0 , !dbg !255
  %".19" = load %"struct.ritz_module_1.RenderNode"*, %"struct.ritz_module_1.RenderNode"** %".18", !dbg !255
  %".20" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 1 , !dbg !255
  %".21" = load i64, i64* %".20", !dbg !255
  %".22" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".19", i64 %".21" , !dbg !255
  store %"struct.ritz_module_1.RenderNode" %".17", %"struct.ritz_module_1.RenderNode"* %".22", !dbg !255
  %".24" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 1 , !dbg !256
  %".25" = load i64, i64* %".24", !dbg !256
  %".26" = add i64 %".25", 1, !dbg !256
  %".27" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 1 , !dbg !256
  store i64 %".26", i64* %".27", !dbg !256
  %".29" = trunc i64 0 to i32 , !dbg !257
  ret i32 %".29", !dbg !257
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !46
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !260, metadata !7), !dbg !261
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !263, metadata !7), !dbg !261
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !264
  %".8" = load i64, i64* %".7", !dbg !264
  %".9" = add i64 %".8", 1, !dbg !264
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !264
  %".11" = sext i32 %".10" to i64 , !dbg !264
  %".12" = icmp ne i64 %".11", 0 , !dbg !264
  br i1 %".12", label %"if.then", label %"if.end", !dbg !264
if.then:
  %".14" = sub i64 0, 1, !dbg !265
  %".15" = trunc i64 %".14" to i32 , !dbg !265
  ret i32 %".15", !dbg !265
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !266
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !266
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !266
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !266
  %".21" = load i64, i64* %".20", !dbg !266
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !266
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !266
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !267
  %".25" = load i64, i64* %".24", !dbg !267
  %".26" = add i64 %".25", 1, !dbg !267
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !267
  store i64 %".26", i64* %".27", !dbg !267
  %".29" = trunc i64 0 to i32 , !dbg !268
  ret i32 %".29", !dbg !268
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !47
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !274
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !269, metadata !7), !dbg !270
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !271, metadata !7), !dbg !270
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !272
  %".8" = load i64, i64* %".7", !dbg !272
  %".9" = load i64, i64* %"needed", !dbg !272
  %".10" = icmp sge i64 %".8", %".9" , !dbg !272
  br i1 %".10", label %"if.then", label %"if.end", !dbg !272
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !273
  ret i32 %".12", !dbg !273
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !274
  %".15" = load i64, i64* %".14", !dbg !274
  store i64 %".15", i64* %"new_cap.addr", !dbg !274
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !275, metadata !7), !dbg !276
  %".18" = load i64, i64* %"new_cap.addr", !dbg !277
  %".19" = icmp eq i64 %".18", 0 , !dbg !277
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !277
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !278
  br label %"if.end.1", !dbg !278
if.end.1:
  br label %"while.cond", !dbg !279
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !279
  %".25" = load i64, i64* %"needed", !dbg !279
  %".26" = icmp slt i64 %".24", %".25" , !dbg !279
  br i1 %".26", label %"while.body", label %"while.end", !dbg !279
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !280
  %".29" = mul i64 %".28", 2, !dbg !280
  store i64 %".29", i64* %"new_cap.addr", !dbg !280
  br label %"while.cond", !dbg !280
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !281
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !281
  ret i32 %".33", !dbg !281
}

define linkonce_odr %"struct.ritz_module_1.Vec$RenderNode" @"vec_new$RenderNode"() !dbg !48
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$RenderNode", !dbg !282
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", metadata !283, metadata !7), !dbg !284
  %".3" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", !dbg !285
  %".4" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", i32 0, i32 0 , !dbg !285
  %".5" = bitcast i8* null to %"struct.ritz_module_1.RenderNode"* , !dbg !285
  store %"struct.ritz_module_1.RenderNode"* %".5", %"struct.ritz_module_1.RenderNode"** %".4", !dbg !285
  %".7" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", !dbg !286
  %".8" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", i32 0, i32 1 , !dbg !286
  store i64 0, i64* %".8", !dbg !286
  %".10" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", !dbg !287
  %".11" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", i32 0, i32 2 , !dbg !287
  store i64 0, i64* %".11", !dbg !287
  %".13" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", !dbg !288
  ret %"struct.ritz_module_1.Vec$RenderNode" %".13", !dbg !288
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !49
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !294
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !289, metadata !7), !dbg !290
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !291, metadata !7), !dbg !290
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !292
  %".8" = load i64, i64* %".7", !dbg !292
  %".9" = load i64, i64* %"needed", !dbg !292
  %".10" = icmp sge i64 %".8", %".9" , !dbg !292
  br i1 %".10", label %"if.then", label %"if.end", !dbg !292
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !293
  ret i32 %".12", !dbg !293
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !294
  %".15" = load i64, i64* %".14", !dbg !294
  store i64 %".15", i64* %"new_cap.addr", !dbg !294
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !295, metadata !7), !dbg !296
  %".18" = load i64, i64* %"new_cap.addr", !dbg !297
  %".19" = icmp eq i64 %".18", 0 , !dbg !297
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !297
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !298
  br label %"if.end.1", !dbg !298
if.end.1:
  br label %"while.cond", !dbg !299
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !299
  %".25" = load i64, i64* %"needed", !dbg !299
  %".26" = icmp slt i64 %".24", %".25" , !dbg !299
  br i1 %".26", label %"while.body", label %"while.end", !dbg !299
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !300
  %".29" = mul i64 %".28", 2, !dbg !300
  store i64 %".29", i64* %"new_cap.addr", !dbg !300
  br label %"while.cond", !dbg !300
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !301
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !301
  ret i32 %".33", !dbg !301
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !50
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !302, metadata !7), !dbg !303
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !304, metadata !7), !dbg !303
  %".7" = load i64, i64* %"new_cap", !dbg !305
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !305
  %".9" = load i64, i64* %".8", !dbg !305
  %".10" = icmp sle i64 %".7", %".9" , !dbg !305
  br i1 %".10", label %"if.then", label %"if.end", !dbg !305
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !306
  ret i32 %".12", !dbg !306
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !307
  %".15" = mul i64 %".14", 1, !dbg !307
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !308
  %".17" = load i8*, i8** %".16", !dbg !308
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !308
  %".19" = icmp eq i8* %".18", null , !dbg !309
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !309
if.then.1:
  %".21" = sub i64 0, 1, !dbg !310
  %".22" = trunc i64 %".21" to i32 , !dbg !310
  ret i32 %".22", !dbg !310
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !311
  store i8* %".18", i8** %".24", !dbg !311
  %".26" = load i64, i64* %"new_cap", !dbg !312
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !312
  store i64 %".26", i64* %".27", !dbg !312
  %".29" = trunc i64 0 to i32 , !dbg !313
  ret i32 %".29", !dbg !313
}

define linkonce_odr i32 @"vec_ensure_cap$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i64 %"needed.arg") !dbg !51
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !319
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", metadata !314, metadata !7), !dbg !315
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !316, metadata !7), !dbg !315
  %".7" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 2 , !dbg !317
  %".8" = load i64, i64* %".7", !dbg !317
  %".9" = load i64, i64* %"needed", !dbg !317
  %".10" = icmp sge i64 %".8", %".9" , !dbg !317
  br i1 %".10", label %"if.then", label %"if.end", !dbg !317
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !318
  ret i32 %".12", !dbg !318
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 2 , !dbg !319
  %".15" = load i64, i64* %".14", !dbg !319
  store i64 %".15", i64* %"new_cap.addr", !dbg !319
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !320, metadata !7), !dbg !321
  %".18" = load i64, i64* %"new_cap.addr", !dbg !322
  %".19" = icmp eq i64 %".18", 0 , !dbg !322
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !322
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !323
  br label %"if.end.1", !dbg !323
if.end.1:
  br label %"while.cond", !dbg !324
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !324
  %".25" = load i64, i64* %"needed", !dbg !324
  %".26" = icmp slt i64 %".24", %".25" , !dbg !324
  br i1 %".26", label %"while.body", label %"while.end", !dbg !324
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !325
  %".29" = mul i64 %".28", 2, !dbg !325
  store i64 %".29", i64* %"new_cap.addr", !dbg !325
  br label %"while.cond", !dbg !325
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !326
  %".33" = call i32 @"vec_grow$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i64 %".32"), !dbg !326
  ret i32 %".33", !dbg !326
}

define linkonce_odr i32 @"vec_grow$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i64 %"new_cap.arg") !dbg !52
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", metadata !327, metadata !7), !dbg !328
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !329, metadata !7), !dbg !328
  %".7" = load i64, i64* %"new_cap", !dbg !330
  %".8" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 2 , !dbg !330
  %".9" = load i64, i64* %".8", !dbg !330
  %".10" = icmp sle i64 %".7", %".9" , !dbg !330
  br i1 %".10", label %"if.then", label %"if.end", !dbg !330
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !331
  ret i32 %".12", !dbg !331
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !332
  %".15" = mul i64 %".14", 656, !dbg !332
  %".16" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 0 , !dbg !333
  %".17" = load %"struct.ritz_module_1.RenderNode"*, %"struct.ritz_module_1.RenderNode"** %".16", !dbg !333
  %".18" = bitcast %"struct.ritz_module_1.RenderNode"* %".17" to i8* , !dbg !333
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !333
  %".20" = icmp eq i8* %".19", null , !dbg !334
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !334
if.then.1:
  %".22" = sub i64 0, 1, !dbg !335
  %".23" = trunc i64 %".22" to i32 , !dbg !335
  ret i32 %".23", !dbg !335
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.RenderNode"* , !dbg !336
  %".26" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 0 , !dbg !336
  store %"struct.ritz_module_1.RenderNode"* %".25", %"struct.ritz_module_1.RenderNode"** %".26", !dbg !336
  %".28" = load i64, i64* %"new_cap", !dbg !337
  %".29" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 2 , !dbg !337
  store i64 %".28", i64* %".29", !dbg !337
  %".31" = trunc i64 0 to i32 , !dbg !338
  ret i32 %".31", !dbg !338
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !53
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !339, metadata !7), !dbg !340
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !341, metadata !7), !dbg !340
  %".7" = load i64, i64* %"new_cap", !dbg !342
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !342
  %".9" = load i64, i64* %".8", !dbg !342
  %".10" = icmp sle i64 %".7", %".9" , !dbg !342
  br i1 %".10", label %"if.then", label %"if.end", !dbg !342
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !343
  ret i32 %".12", !dbg !343
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !344
  %".15" = mul i64 %".14", 16, !dbg !344
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !345
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !345
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !345
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !345
  %".20" = icmp eq i8* %".19", null , !dbg !346
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !346
if.then.1:
  %".22" = sub i64 0, 1, !dbg !347
  %".23" = trunc i64 %".22" to i32 , !dbg !347
  ret i32 %".23", !dbg !347
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !348
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !348
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !348
  %".28" = load i64, i64* %"new_cap", !dbg !349
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !349
  store i64 %".28", i64* %".29", !dbg !349
  %".31" = trunc i64 0 to i32 , !dbg !350
  ret i32 %".31", !dbg !350
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/lib/tree", filename: "render_node.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 40, name: "dirty_flags_none", scopeLine: 40, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 43, name: "dirty_flags_all", scopeLine: 43, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 46, name: "dirty_flags_is_clean", scopeLine: 46, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 57, name: "dirty_flags_needs_layout", scopeLine: 57, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 66, name: "dirty_flags_needs_paint", scopeLine: 66, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 107, name: "layout_result_empty", scopeLine: 107, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 117, name: "layout_result_outer_width", scopeLine: 117, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 122, name: "layout_result_outer_height", scopeLine: 122, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 180, name: "render_node_new", scopeLine: 180, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 202, name: "render_node_new_text", scopeLine: 202, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 209, name: "render_node_is_text", scopeLine: 209, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 214, name: "render_node_is_replaced", scopeLine: 214, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 221, name: "render_node_has_children", scopeLine: 221, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 226, name: "render_node_is_block", scopeLine: 226, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 236, name: "render_node_is_inline", scopeLine: 236, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 248, name: "render_node_generates_layer", scopeLine: 248, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 271, name: "render_tree_new", scopeLine: 271, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 278, name: "render_tree_get", scopeLine: 278, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 287, name: "render_tree_get_mut", scopeLine: 287, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 296, name: "render_tree_insert", scopeLine: 296, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 301, name: "render_tree_set_root", scopeLine: 301, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 304, name: "render_tree_root", scopeLine: 304, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 307, name: "render_tree_count", scopeLine: 307, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 310, name: "render_tree_is_empty", scopeLine: 310, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 317, name: "render_tree_mark_dirty", scopeLine: 317, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 332, name: "render_tree_clear_dirty", scopeLine: 332, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$RenderNode", scopeLine: 210, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$RenderNode", scopeLine: 116, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!51 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$RenderNode", scopeLine: 193, type: !4, unit: !1)
!52 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$RenderNode", scopeLine: 179, type: !4, unit: !1)
!53 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!54 = !DILocation(column: 5, line: 41, scope: !17)
!55 = !DILocation(column: 5, line: 44, scope: !18)
!56 = !DICompositeType(align: 32, file: !0, name: "DirtyFlags", size: 128, tag: DW_TAG_structure_type)
!57 = !DILocalVariable(file: !0, line: 46, name: "flags", scope: !19, type: !56)
!58 = !DILocation(column: 1, line: 46, scope: !19)
!59 = !DILocation(column: 5, line: 47, scope: !19)
!60 = !DILocation(column: 9, line: 48, scope: !19)
!61 = !DILocation(column: 5, line: 49, scope: !19)
!62 = !DILocation(column: 9, line: 50, scope: !19)
!63 = !DILocation(column: 5, line: 51, scope: !19)
!64 = !DILocation(column: 9, line: 52, scope: !19)
!65 = !DILocation(column: 5, line: 53, scope: !19)
!66 = !DILocation(column: 9, line: 54, scope: !19)
!67 = !DILocation(column: 5, line: 55, scope: !19)
!68 = !DILocalVariable(file: !0, line: 57, name: "flags", scope: !20, type: !56)
!69 = !DILocation(column: 1, line: 57, scope: !20)
!70 = !DILocation(column: 5, line: 58, scope: !20)
!71 = !DILocation(column: 9, line: 59, scope: !20)
!72 = !DILocation(column: 5, line: 60, scope: !20)
!73 = !DILocation(column: 9, line: 61, scope: !20)
!74 = !DILocation(column: 5, line: 62, scope: !20)
!75 = !DILocation(column: 9, line: 63, scope: !20)
!76 = !DILocation(column: 5, line: 64, scope: !20)
!77 = !DILocalVariable(file: !0, line: 66, name: "flags", scope: !21, type: !56)
!78 = !DILocation(column: 1, line: 66, scope: !21)
!79 = !DILocation(column: 5, line: 67, scope: !21)
!80 = !DILocation(column: 9, line: 68, scope: !21)
!81 = !DILocation(column: 5, line: 69, scope: !21)
!82 = !DILocation(column: 9, line: 70, scope: !21)
!83 = !DILocation(column: 5, line: 71, scope: !21)
!84 = !DILocation(column: 9, line: 72, scope: !21)
!85 = !DILocation(column: 5, line: 73, scope: !21)
!86 = !DILocation(column: 9, line: 74, scope: !21)
!87 = !DILocation(column: 5, line: 75, scope: !21)
!88 = !DILocation(column: 5, line: 108, scope: !22)
!89 = !DICompositeType(align: 32, file: !0, name: "LayoutResult", size: 544, tag: DW_TAG_structure_type)
!90 = !DILocalVariable(file: !0, line: 117, name: "layout", scope: !23, type: !89)
!91 = !DILocation(column: 1, line: 117, scope: !23)
!92 = !DILocation(column: 5, line: 118, scope: !23)
!93 = !DILocation(column: 5, line: 119, scope: !23)
!94 = !DILocalVariable(file: !0, line: 122, name: "layout", scope: !24, type: !89)
!95 = !DILocation(column: 1, line: 122, scope: !24)
!96 = !DILocation(column: 5, line: 123, scope: !24)
!97 = !DILocation(column: 5, line: 124, scope: !24)
!98 = !DICompositeType(align: 64, file: !0, name: "NodeId", size: 64, tag: DW_TAG_structure_type)
!99 = !DILocalVariable(file: !0, line: 180, name: "id", scope: !25, type: !98)
!100 = !DILocation(column: 1, line: 180, scope: !25)
!101 = !DILocalVariable(file: !0, line: 180, name: "tag", scope: !25, type: !10)
!102 = !DICompositeType(align: 64, file: !0, name: "ComputedStyle", size: 3840, tag: DW_TAG_structure_type)
!103 = !DILocalVariable(file: !0, line: 180, name: "style", scope: !25, type: !102)
!104 = !DILocation(column: 5, line: 181, scope: !25)
!105 = !DILocalVariable(file: !0, line: 202, name: "id", scope: !26, type: !98)
!106 = !DILocation(column: 1, line: 202, scope: !26)
!107 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!108 = !DILocalVariable(file: !0, line: 202, name: "text_ptr", scope: !26, type: !107)
!109 = !DILocalVariable(file: !0, line: 202, name: "text_len", scope: !26, type: !10)
!110 = !DILocalVariable(file: !0, line: 202, name: "style", scope: !26, type: !102)
!111 = !DILocation(column: 5, line: 203, scope: !26)
!112 = !DILocation(column: 5, line: 204, scope: !26)
!113 = !DILocation(column: 5, line: 205, scope: !26)
!114 = !DILocation(column: 5, line: 206, scope: !26)
!115 = !DILocation(column: 5, line: 207, scope: !26)
!116 = !DICompositeType(align: 64, file: !0, name: "RenderNode", size: 5248, tag: DW_TAG_structure_type)
!117 = !DILocalVariable(file: !0, line: 209, name: "node", scope: !27, type: !116)
!118 = !DILocation(column: 1, line: 209, scope: !27)
!119 = !DILocation(column: 5, line: 210, scope: !27)
!120 = !DILocation(column: 9, line: 211, scope: !27)
!121 = !DILocation(column: 5, line: 212, scope: !27)
!122 = !DILocalVariable(file: !0, line: 214, name: "node", scope: !28, type: !116)
!123 = !DILocation(column: 1, line: 214, scope: !28)
!124 = !DILocation(column: 5, line: 215, scope: !28)
!125 = !DILocation(column: 9, line: 216, scope: !28)
!126 = !DILocation(column: 5, line: 217, scope: !28)
!127 = !DILocation(column: 9, line: 218, scope: !28)
!128 = !DILocation(column: 5, line: 219, scope: !28)
!129 = !DILocalVariable(file: !0, line: 221, name: "node", scope: !29, type: !116)
!130 = !DILocation(column: 1, line: 221, scope: !29)
!131 = !DILocation(column: 5, line: 222, scope: !29)
!132 = !DILocation(column: 9, line: 223, scope: !29)
!133 = !DILocation(column: 5, line: 224, scope: !29)
!134 = !DILocalVariable(file: !0, line: 226, name: "node", scope: !30, type: !116)
!135 = !DILocation(column: 1, line: 226, scope: !30)
!136 = !DILocation(column: 5, line: 227, scope: !30)
!137 = !DILocation(column: 5, line: 228, scope: !30)
!138 = !DILocation(column: 9, line: 229, scope: !30)
!139 = !DILocation(column: 5, line: 230, scope: !30)
!140 = !DILocation(column: 9, line: 231, scope: !30)
!141 = !DILocation(column: 5, line: 232, scope: !30)
!142 = !DILocation(column: 9, line: 233, scope: !30)
!143 = !DILocation(column: 5, line: 234, scope: !30)
!144 = !DILocalVariable(file: !0, line: 236, name: "node", scope: !31, type: !116)
!145 = !DILocation(column: 1, line: 236, scope: !31)
!146 = !DILocation(column: 5, line: 237, scope: !31)
!147 = !DILocation(column: 5, line: 238, scope: !31)
!148 = !DILocation(column: 9, line: 239, scope: !31)
!149 = !DILocation(column: 5, line: 240, scope: !31)
!150 = !DILocation(column: 9, line: 241, scope: !31)
!151 = !DILocation(column: 5, line: 242, scope: !31)
!152 = !DILocation(column: 9, line: 243, scope: !31)
!153 = !DILocation(column: 5, line: 244, scope: !31)
!154 = !DILocation(column: 9, line: 245, scope: !31)
!155 = !DILocation(column: 5, line: 246, scope: !31)
!156 = !DILocalVariable(file: !0, line: 248, name: "node", scope: !32, type: !116)
!157 = !DILocation(column: 1, line: 248, scope: !32)
!158 = !DILocation(column: 5, line: 250, scope: !32)
!159 = !DILocation(column: 9, line: 251, scope: !32)
!160 = !DILocation(column: 5, line: 252, scope: !32)
!161 = !DILocation(column: 9, line: 253, scope: !32)
!162 = !DILocation(column: 5, line: 254, scope: !32)
!163 = !DILocation(column: 9, line: 255, scope: !32)
!164 = !DILocation(column: 5, line: 256, scope: !32)
!165 = !DILocation(column: 9, line: 257, scope: !32)
!166 = !DILocation(column: 5, line: 258, scope: !32)
!167 = !DILocation(column: 5, line: 272, scope: !33)
!168 = !DICompositeType(align: 64, file: !0, name: "RenderTree", size: 512, tag: DW_TAG_structure_type)
!169 = !DIDerivedType(baseType: !168, size: 64, tag: DW_TAG_reference_type)
!170 = !DILocalVariable(file: !0, line: 278, name: "tree", scope: !34, type: !169)
!171 = !DILocation(column: 1, line: 278, scope: !34)
!172 = !DIDerivedType(baseType: !98, size: 64, tag: DW_TAG_reference_type)
!173 = !DILocalVariable(file: !0, line: 278, name: "id", scope: !34, type: !172)
!174 = !DILocation(column: 5, line: 280, scope: !34)
!175 = !DILocation(column: 5, line: 281, scope: !34)
!176 = !DILocation(column: 9, line: 282, scope: !34)
!177 = !DILocation(column: 5, line: 283, scope: !34)
!178 = !DILocation(column: 9, line: 284, scope: !34)
!179 = !DILocation(column: 5, line: 285, scope: !34)
!180 = !DILocalVariable(file: !0, line: 287, name: "tree", scope: !35, type: !169)
!181 = !DILocation(column: 1, line: 287, scope: !35)
!182 = !DILocalVariable(file: !0, line: 287, name: "id", scope: !35, type: !172)
!183 = !DILocation(column: 5, line: 289, scope: !35)
!184 = !DILocation(column: 5, line: 290, scope: !35)
!185 = !DILocation(column: 9, line: 291, scope: !35)
!186 = !DILocation(column: 5, line: 292, scope: !35)
!187 = !DILocation(column: 9, line: 293, scope: !35)
!188 = !DILocation(column: 5, line: 294, scope: !35)
!189 = !DILocalVariable(file: !0, line: 296, name: "tree", scope: !36, type: !169)
!190 = !DILocation(column: 1, line: 296, scope: !36)
!191 = !DILocalVariable(file: !0, line: 296, name: "node", scope: !36, type: !116)
!192 = !DILocation(column: 5, line: 297, scope: !36)
!193 = !DILocation(column: 5, line: 298, scope: !36)
!194 = !DILocation(column: 5, line: 299, scope: !36)
!195 = !DILocalVariable(file: !0, line: 301, name: "tree", scope: !37, type: !169)
!196 = !DILocation(column: 1, line: 301, scope: !37)
!197 = !DILocalVariable(file: !0, line: 301, name: "id", scope: !37, type: !98)
!198 = !DILocation(column: 5, line: 302, scope: !37)
!199 = !DILocalVariable(file: !0, line: 304, name: "tree", scope: !38, type: !169)
!200 = !DILocation(column: 1, line: 304, scope: !38)
!201 = !DILocation(column: 5, line: 305, scope: !38)
!202 = !DILocalVariable(file: !0, line: 307, name: "tree", scope: !39, type: !169)
!203 = !DILocation(column: 1, line: 307, scope: !39)
!204 = !DILocation(column: 5, line: 308, scope: !39)
!205 = !DILocalVariable(file: !0, line: 310, name: "tree", scope: !40, type: !169)
!206 = !DILocation(column: 1, line: 310, scope: !40)
!207 = !DILocation(column: 5, line: 311, scope: !40)
!208 = !DILocation(column: 9, line: 312, scope: !40)
!209 = !DILocation(column: 5, line: 313, scope: !40)
!210 = !DILocalVariable(file: !0, line: 317, name: "tree", scope: !41, type: !169)
!211 = !DILocation(column: 1, line: 317, scope: !41)
!212 = !DILocalVariable(file: !0, line: 317, name: "id", scope: !41, type: !98)
!213 = !DILocalVariable(file: !0, line: 317, name: "flags", scope: !41, type: !56)
!214 = !DILocation(column: 5, line: 318, scope: !41)
!215 = !DILocation(column: 5, line: 319, scope: !41)
!216 = !DILocation(column: 9, line: 320, scope: !41)
!217 = !DILocation(column: 5, line: 322, scope: !41)
!218 = !DILocation(column: 9, line: 323, scope: !41)
!219 = !DILocation(column: 5, line: 324, scope: !41)
!220 = !DILocation(column: 9, line: 325, scope: !41)
!221 = !DILocation(column: 5, line: 326, scope: !41)
!222 = !DILocation(column: 9, line: 327, scope: !41)
!223 = !DILocation(column: 5, line: 328, scope: !41)
!224 = !DILocation(column: 9, line: 329, scope: !41)
!225 = !DILocalVariable(file: !0, line: 332, name: "tree", scope: !42, type: !169)
!226 = !DILocation(column: 1, line: 332, scope: !42)
!227 = !DILocalVariable(file: !0, line: 332, name: "id", scope: !42, type: !98)
!228 = !DILocation(column: 5, line: 333, scope: !42)
!229 = !DILocation(column: 5, line: 334, scope: !42)
!230 = !DILocation(column: 9, line: 335, scope: !42)
!231 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!232 = !DIDerivedType(baseType: !231, size: 64, tag: DW_TAG_reference_type)
!233 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !43, type: !232)
!234 = !DILocation(column: 1, line: 288, scope: !43)
!235 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !43, type: !107)
!236 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !43, type: !11)
!237 = !DILocation(column: 5, line: 289, scope: !43)
!238 = !DILocation(column: 13, line: 291, scope: !43)
!239 = !DILocation(column: 5, line: 292, scope: !43)
!240 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !44, type: !232)
!241 = !DILocation(column: 1, line: 210, scope: !44)
!242 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !44, type: !12)
!243 = !DILocation(column: 5, line: 211, scope: !44)
!244 = !DILocation(column: 9, line: 212, scope: !44)
!245 = !DILocation(column: 5, line: 213, scope: !44)
!246 = !DILocation(column: 5, line: 214, scope: !44)
!247 = !DILocation(column: 5, line: 215, scope: !44)
!248 = !DICompositeType(align: 64, file: !0, name: "Vec$RenderNode", size: 192, tag: DW_TAG_structure_type)
!249 = !DIDerivedType(baseType: !248, size: 64, tag: DW_TAG_reference_type)
!250 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !45, type: !249)
!251 = !DILocation(column: 1, line: 210, scope: !45)
!252 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !45, type: !116)
!253 = !DILocation(column: 5, line: 211, scope: !45)
!254 = !DILocation(column: 9, line: 212, scope: !45)
!255 = !DILocation(column: 5, line: 213, scope: !45)
!256 = !DILocation(column: 5, line: 214, scope: !45)
!257 = !DILocation(column: 5, line: 215, scope: !45)
!258 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!259 = !DIDerivedType(baseType: !258, size: 64, tag: DW_TAG_reference_type)
!260 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !46, type: !259)
!261 = !DILocation(column: 1, line: 210, scope: !46)
!262 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!263 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !46, type: !262)
!264 = !DILocation(column: 5, line: 211, scope: !46)
!265 = !DILocation(column: 9, line: 212, scope: !46)
!266 = !DILocation(column: 5, line: 213, scope: !46)
!267 = !DILocation(column: 5, line: 214, scope: !46)
!268 = !DILocation(column: 5, line: 215, scope: !46)
!269 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !47, type: !232)
!270 = !DILocation(column: 1, line: 193, scope: !47)
!271 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !47, type: !11)
!272 = !DILocation(column: 5, line: 194, scope: !47)
!273 = !DILocation(column: 9, line: 195, scope: !47)
!274 = !DILocation(column: 5, line: 197, scope: !47)
!275 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !47, type: !11)
!276 = !DILocation(column: 1, line: 197, scope: !47)
!277 = !DILocation(column: 5, line: 198, scope: !47)
!278 = !DILocation(column: 9, line: 199, scope: !47)
!279 = !DILocation(column: 5, line: 200, scope: !47)
!280 = !DILocation(column: 9, line: 201, scope: !47)
!281 = !DILocation(column: 5, line: 203, scope: !47)
!282 = !DILocation(column: 5, line: 117, scope: !48)
!283 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !48, type: !248)
!284 = !DILocation(column: 1, line: 117, scope: !48)
!285 = !DILocation(column: 5, line: 118, scope: !48)
!286 = !DILocation(column: 5, line: 119, scope: !48)
!287 = !DILocation(column: 5, line: 120, scope: !48)
!288 = !DILocation(column: 5, line: 121, scope: !48)
!289 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !49, type: !259)
!290 = !DILocation(column: 1, line: 193, scope: !49)
!291 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !49, type: !11)
!292 = !DILocation(column: 5, line: 194, scope: !49)
!293 = !DILocation(column: 9, line: 195, scope: !49)
!294 = !DILocation(column: 5, line: 197, scope: !49)
!295 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !49, type: !11)
!296 = !DILocation(column: 1, line: 197, scope: !49)
!297 = !DILocation(column: 5, line: 198, scope: !49)
!298 = !DILocation(column: 9, line: 199, scope: !49)
!299 = !DILocation(column: 5, line: 200, scope: !49)
!300 = !DILocation(column: 9, line: 201, scope: !49)
!301 = !DILocation(column: 5, line: 203, scope: !49)
!302 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !50, type: !232)
!303 = !DILocation(column: 1, line: 179, scope: !50)
!304 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !50, type: !11)
!305 = !DILocation(column: 5, line: 180, scope: !50)
!306 = !DILocation(column: 9, line: 181, scope: !50)
!307 = !DILocation(column: 5, line: 183, scope: !50)
!308 = !DILocation(column: 5, line: 184, scope: !50)
!309 = !DILocation(column: 5, line: 185, scope: !50)
!310 = !DILocation(column: 9, line: 186, scope: !50)
!311 = !DILocation(column: 5, line: 188, scope: !50)
!312 = !DILocation(column: 5, line: 189, scope: !50)
!313 = !DILocation(column: 5, line: 190, scope: !50)
!314 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !51, type: !249)
!315 = !DILocation(column: 1, line: 193, scope: !51)
!316 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !51, type: !11)
!317 = !DILocation(column: 5, line: 194, scope: !51)
!318 = !DILocation(column: 9, line: 195, scope: !51)
!319 = !DILocation(column: 5, line: 197, scope: !51)
!320 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !51, type: !11)
!321 = !DILocation(column: 1, line: 197, scope: !51)
!322 = !DILocation(column: 5, line: 198, scope: !51)
!323 = !DILocation(column: 9, line: 199, scope: !51)
!324 = !DILocation(column: 5, line: 200, scope: !51)
!325 = !DILocation(column: 9, line: 201, scope: !51)
!326 = !DILocation(column: 5, line: 203, scope: !51)
!327 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !52, type: !249)
!328 = !DILocation(column: 1, line: 179, scope: !52)
!329 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !52, type: !11)
!330 = !DILocation(column: 5, line: 180, scope: !52)
!331 = !DILocation(column: 9, line: 181, scope: !52)
!332 = !DILocation(column: 5, line: 183, scope: !52)
!333 = !DILocation(column: 5, line: 184, scope: !52)
!334 = !DILocation(column: 5, line: 185, scope: !52)
!335 = !DILocation(column: 9, line: 186, scope: !52)
!336 = !DILocation(column: 5, line: 188, scope: !52)
!337 = !DILocation(column: 5, line: 189, scope: !52)
!338 = !DILocation(column: 5, line: 190, scope: !52)
!339 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !53, type: !259)
!340 = !DILocation(column: 1, line: 179, scope: !53)
!341 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !53, type: !11)
!342 = !DILocation(column: 5, line: 180, scope: !53)
!343 = !DILocation(column: 9, line: 181, scope: !53)
!344 = !DILocation(column: 5, line: 183, scope: !53)
!345 = !DILocation(column: 5, line: 184, scope: !53)
!346 = !DILocation(column: 5, line: 185, scope: !53)
!347 = !DILocation(column: 9, line: 186, scope: !53)
!348 = !DILocation(column: 5, line: 188, scope: !53)
!349 = !DILocation(column: 5, line: 189, scope: !53)
!350 = !DILocation(column: 5, line: 190, scope: !53)