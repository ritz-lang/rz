; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Vec$LineBounds" = type {%"struct.ritz_module_1.LineBounds"*, i64, i64}
%"struct.ritz_module_1.Vec$u8" = type {i8*, i64, i64}
%"struct.ritz_module_1.Vec$Layer" = type {%"struct.ritz_module_1.Layer"*, i64, i64}
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
%"struct.ritz_module_1.LayerId" = type {i64}
%"struct.ritz_module_1.LayerRect" = type {i32, i32, i32, i32}
%"struct.ritz_module_1.LayerPoint" = type {i32, i32}
%"struct.ritz_module_1.Layer" = type {%"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.NodeId", i32, %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerRect", %"struct.ritz_module_1.Transform", double, i32, %"struct.ritz_module_1.LayerPoint", %"struct.ritz_module_1.LayerRect", i32, i32, i64}
%"struct.ritz_module_1.LayerTree" = type {%"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.LayerId", i64}
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

define %"struct.ritz_module_1.LayerId" @"layer_id_new"(i64 %"value.arg") !dbg !17
{
entry:
  %"value" = alloca i64
  store i64 %"value.arg", i64* %"value"
  call void @"llvm.dbg.declare"(metadata i64* %"value", metadata !51, metadata !7), !dbg !52
  %".5" = load i64, i64* %"value", !dbg !53
  %".6" = insertvalue %"struct.ritz_module_1.LayerId" undef, i64 %".5", 0 , !dbg !53
  ret %"struct.ritz_module_1.LayerId" %".6", !dbg !53
}

define %"struct.ritz_module_1.LayerId" @"layer_id_invalid"() !dbg !18
{
entry:
  %".2" = insertvalue %"struct.ritz_module_1.LayerId" undef, i64 0, 0 , !dbg !54
  ret %"struct.ritz_module_1.LayerId" %".2", !dbg !54
}

define i32 @"layer_id_is_valid"(%"struct.ritz_module_1.LayerId"* %"id.arg") !dbg !19
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerId"* %"id.arg", metadata !57, metadata !7), !dbg !58
  %".4" = getelementptr %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId"* %"id.arg", i32 0, i32 0 , !dbg !59
  %".5" = load i64, i64* %".4", !dbg !59
  %".6" = icmp ne i64 %".5", 0 , !dbg !59
  br i1 %".6", label %"if.then", label %"if.end", !dbg !59
if.then:
  %".8" = trunc i64 1 to i32 , !dbg !60
  ret i32 %".8", !dbg !60
if.end:
  %".10" = trunc i64 0 to i32 , !dbg !61
  ret i32 %".10", !dbg !61
}

define i32 @"layer_id_eq"(%"struct.ritz_module_1.LayerId"* %"a.arg", %"struct.ritz_module_1.LayerId"* %"b.arg") !dbg !20
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerId"* %"a.arg", metadata !62, metadata !7), !dbg !63
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerId"* %"b.arg", metadata !64, metadata !7), !dbg !63
  %".6" = getelementptr %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId"* %"a.arg", i32 0, i32 0 , !dbg !65
  %".7" = load i64, i64* %".6", !dbg !65
  %".8" = getelementptr %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId"* %"b.arg", i32 0, i32 0 , !dbg !65
  %".9" = load i64, i64* %".8", !dbg !65
  %".10" = icmp eq i64 %".7", %".9" , !dbg !65
  br i1 %".10", label %"if.then", label %"if.end", !dbg !65
if.then:
  %".12" = trunc i64 1 to i32 , !dbg !66
  ret i32 %".12", !dbg !66
if.end:
  %".14" = trunc i64 0 to i32 , !dbg !67
  ret i32 %".14", !dbg !67
}

define %"struct.ritz_module_1.LayerRect" @"layer_rect_new"(i32 %"x.arg", i32 %"y.arg", i32 %"width.arg", i32 %"height.arg") !dbg !21
{
entry:
  %"x" = alloca i32
  store i32 %"x.arg", i32* %"x"
  call void @"llvm.dbg.declare"(metadata i32* %"x", metadata !68, metadata !7), !dbg !69
  %"y" = alloca i32
  store i32 %"y.arg", i32* %"y"
  call void @"llvm.dbg.declare"(metadata i32* %"y", metadata !70, metadata !7), !dbg !69
  %"width" = alloca i32
  store i32 %"width.arg", i32* %"width"
  call void @"llvm.dbg.declare"(metadata i32* %"width", metadata !71, metadata !7), !dbg !69
  %"height" = alloca i32
  store i32 %"height.arg", i32* %"height"
  call void @"llvm.dbg.declare"(metadata i32* %"height", metadata !72, metadata !7), !dbg !69
  %".14" = load i32, i32* %"x", !dbg !73
  %".15" = load i32, i32* %"y", !dbg !73
  %".16" = load i32, i32* %"width", !dbg !73
  %".17" = load i32, i32* %"height", !dbg !73
  %".18" = insertvalue %"struct.ritz_module_1.LayerRect" undef, i32 %".14", 0 , !dbg !73
  %".19" = insertvalue %"struct.ritz_module_1.LayerRect" %".18", i32 %".15", 1 , !dbg !73
  %".20" = insertvalue %"struct.ritz_module_1.LayerRect" %".19", i32 %".16", 2 , !dbg !73
  %".21" = insertvalue %"struct.ritz_module_1.LayerRect" %".20", i32 %".17", 3 , !dbg !73
  ret %"struct.ritz_module_1.LayerRect" %".21", !dbg !73
}

define %"struct.ritz_module_1.LayerRect" @"layer_rect_zero"() !dbg !22
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !74
  %".3" = trunc i64 0 to i32 , !dbg !74
  %".4" = trunc i64 0 to i32 , !dbg !74
  %".5" = trunc i64 0 to i32 , !dbg !74
  %".6" = insertvalue %"struct.ritz_module_1.LayerRect" undef, i32 %".2", 0 , !dbg !74
  %".7" = insertvalue %"struct.ritz_module_1.LayerRect" %".6", i32 %".3", 1 , !dbg !74
  %".8" = insertvalue %"struct.ritz_module_1.LayerRect" %".7", i32 %".4", 2 , !dbg !74
  %".9" = insertvalue %"struct.ritz_module_1.LayerRect" %".8", i32 %".5", 3 , !dbg !74
  ret %"struct.ritz_module_1.LayerRect" %".9", !dbg !74
}

define %"struct.ritz_module_1.LayerPoint" @"layer_point_new"(i32 %"x.arg", i32 %"y.arg") !dbg !23
{
entry:
  %"x" = alloca i32
  store i32 %"x.arg", i32* %"x"
  call void @"llvm.dbg.declare"(metadata i32* %"x", metadata !75, metadata !7), !dbg !76
  %"y" = alloca i32
  store i32 %"y.arg", i32* %"y"
  call void @"llvm.dbg.declare"(metadata i32* %"y", metadata !77, metadata !7), !dbg !76
  %".8" = load i32, i32* %"x", !dbg !78
  %".9" = load i32, i32* %"y", !dbg !78
  %".10" = insertvalue %"struct.ritz_module_1.LayerPoint" undef, i32 %".8", 0 , !dbg !78
  %".11" = insertvalue %"struct.ritz_module_1.LayerPoint" %".10", i32 %".9", 1 , !dbg !78
  ret %"struct.ritz_module_1.LayerPoint" %".11", !dbg !78
}

define %"struct.ritz_module_1.LayerPoint" @"layer_point_zero"() !dbg !24
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !79
  %".3" = trunc i64 0 to i32 , !dbg !79
  %".4" = insertvalue %"struct.ritz_module_1.LayerPoint" undef, i32 %".2", 0 , !dbg !79
  %".5" = insertvalue %"struct.ritz_module_1.LayerPoint" %".4", i32 %".3", 1 , !dbg !79
  ret %"struct.ritz_module_1.LayerPoint" %".5", !dbg !79
}

define %"struct.ritz_module_1.Layer" @"layer_new"(%"struct.ritz_module_1.LayerId" %"id.arg", %"struct.ritz_module_1.NodeId" %"node_id.arg", i32 %"reason.arg") !dbg !25
{
entry:
  %"id" = alloca %"struct.ritz_module_1.LayerId"
  store %"struct.ritz_module_1.LayerId" %"id.arg", %"struct.ritz_module_1.LayerId"* %"id"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerId"* %"id", metadata !80, metadata !7), !dbg !81
  %"node_id" = alloca %"struct.ritz_module_1.NodeId"
  store %"struct.ritz_module_1.NodeId" %"node_id.arg", %"struct.ritz_module_1.NodeId"* %"node_id"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.NodeId"* %"node_id", metadata !83, metadata !7), !dbg !81
  %"reason" = alloca i32
  store i32 %"reason.arg", i32* %"reason"
  call void @"llvm.dbg.declare"(metadata i32* %"reason", metadata !84, metadata !7), !dbg !81
  %".11" = load %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId"* %"id", !dbg !85
  %".12" = load %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %"node_id", !dbg !85
  %".13" = load i32, i32* %"reason", !dbg !85
  %".14" = call %"struct.ritz_module_1.LayerId" @"layer_id_invalid"(), !dbg !85
  %".15" = call %"struct.ritz_module_1.LayerId" @"layer_id_invalid"(), !dbg !85
  %".16" = call %"struct.ritz_module_1.LayerId" @"layer_id_invalid"(), !dbg !85
  %".17" = call %"struct.ritz_module_1.LayerId" @"layer_id_invalid"(), !dbg !85
  %".18" = call %"struct.ritz_module_1.LayerId" @"layer_id_invalid"(), !dbg !85
  %".19" = call %"struct.ritz_module_1.LayerRect" @"layer_rect_zero"(), !dbg !85
  %".20" = call %"struct.ritz_module_1.Transform" @"transform_identity"(), !dbg !85
  %".21" = call %"struct.ritz_module_1.LayerPoint" @"layer_point_zero"(), !dbg !85
  %".22" = call %"struct.ritz_module_1.LayerRect" @"layer_rect_zero"(), !dbg !85
  %".23" = trunc i64 1 to i32 , !dbg !85
  %".24" = trunc i64 1 to i32 , !dbg !85
  %".25" = insertvalue %"struct.ritz_module_1.Layer" undef, %"struct.ritz_module_1.LayerId" %".11", 0 , !dbg !85
  %".26" = insertvalue %"struct.ritz_module_1.Layer" %".25", %"struct.ritz_module_1.NodeId" %".12", 1 , !dbg !85
  %".27" = insertvalue %"struct.ritz_module_1.Layer" %".26", i32 %".13", 2 , !dbg !85
  %".28" = insertvalue %"struct.ritz_module_1.Layer" %".27", %"struct.ritz_module_1.LayerId" %".14", 3 , !dbg !85
  %".29" = insertvalue %"struct.ritz_module_1.Layer" %".28", %"struct.ritz_module_1.LayerId" %".15", 4 , !dbg !85
  %".30" = insertvalue %"struct.ritz_module_1.Layer" %".29", %"struct.ritz_module_1.LayerId" %".16", 5 , !dbg !85
  %".31" = insertvalue %"struct.ritz_module_1.Layer" %".30", %"struct.ritz_module_1.LayerId" %".17", 6 , !dbg !85
  %".32" = insertvalue %"struct.ritz_module_1.Layer" %".31", %"struct.ritz_module_1.LayerId" %".18", 7 , !dbg !85
  %".33" = insertvalue %"struct.ritz_module_1.Layer" %".32", %"struct.ritz_module_1.LayerRect" %".19", 8 , !dbg !85
  %".34" = insertvalue %"struct.ritz_module_1.Layer" %".33", %"struct.ritz_module_1.Transform" %".20", 9 , !dbg !85
  %".35" = insertvalue %"struct.ritz_module_1.Layer" %".34", double 0x3ff0000000000000, 10 , !dbg !85
  %".36" = insertvalue %"struct.ritz_module_1.Layer" %".35", i32 0, 11 , !dbg !85
  %".37" = insertvalue %"struct.ritz_module_1.Layer" %".36", %"struct.ritz_module_1.LayerPoint" %".21", 12 , !dbg !85
  %".38" = insertvalue %"struct.ritz_module_1.Layer" %".37", %"struct.ritz_module_1.LayerRect" %".22", 13 , !dbg !85
  %".39" = insertvalue %"struct.ritz_module_1.Layer" %".38", i32 %".23", 14 , !dbg !85
  %".40" = insertvalue %"struct.ritz_module_1.Layer" %".39", i32 %".24", 15 , !dbg !85
  %".41" = insertvalue %"struct.ritz_module_1.Layer" %".40", i64 0, 16 , !dbg !85
  ret %"struct.ritz_module_1.Layer" %".41", !dbg !85
}

define i32 @"layer_is_scrollable"(%"struct.ritz_module_1.Layer"* %"layer.arg") !dbg !26
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Layer"* %"layer.arg", metadata !88, metadata !7), !dbg !89
  %".4" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %"layer.arg", i32 0, i32 2 , !dbg !90
  %".5" = load i32, i32* %".4", !dbg !90
  %".6" = icmp eq i32 %".5", 7 , !dbg !90
  br i1 %".6", label %"if.then", label %"if.end", !dbg !90
if.then:
  %".8" = trunc i64 1 to i32 , !dbg !91
  ret i32 %".8", !dbg !91
if.end:
  %".10" = trunc i64 0 to i32 , !dbg !92
  ret i32 %".10", !dbg !92
}

define i32 @"layer_has_transform"(%"struct.ritz_module_1.Layer"* %"layer.arg") !dbg !27
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Layer"* %"layer.arg", metadata !93, metadata !7), !dbg !94
  %".4" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %"layer.arg", i32 0, i32 9 , !dbg !95
  %".5" = load %"struct.ritz_module_1.Transform", %"struct.ritz_module_1.Transform"* %".4", !dbg !95
  %".6" = call i32 @"transform_is_identity"(%"struct.ritz_module_1.Transform" %".5"), !dbg !95
  %".7" = sext i32 %".6" to i64 , !dbg !95
  %".8" = icmp eq i64 %".7", 0 , !dbg !95
  br i1 %".8", label %"if.then", label %"if.end", !dbg !95
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !96
  ret i32 %".10", !dbg !96
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !97
  ret i32 %".12", !dbg !97
}

define i32 @"layer_is_opaque"(%"struct.ritz_module_1.Layer"* %"layer.arg") !dbg !28
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Layer"* %"layer.arg", metadata !98, metadata !7), !dbg !99
  %".4" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %"layer.arg", i32 0, i32 10 , !dbg !100
  %".5" = load double, double* %".4", !dbg !100
  %".6" = fcmp oge double %".5", 0x3ff0000000000000 , !dbg !100
  br i1 %".6", label %"if.then", label %"if.end", !dbg !100
if.then:
  %".8" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %"layer.arg", i32 0, i32 11 , !dbg !100
  %".9" = load i32, i32* %".8", !dbg !100
  %".10" = icmp eq i32 %".9", 0 , !dbg !100
  br i1 %".10", label %"if.then.1", label %"if.end.1", !dbg !100
if.end:
  %".15" = trunc i64 0 to i32 , !dbg !102
  ret i32 %".15", !dbg !102
if.then.1:
  %".12" = trunc i64 1 to i32 , !dbg !101
  ret i32 %".12", !dbg !101
if.end.1:
  br label %"if.end", !dbg !101
}

define %"struct.ritz_module_1.LayerTree" @"layer_tree_new"() !dbg !29
{
entry:
  %".2" = call %"struct.ritz_module_1.Vec$Layer" @"vec_new$Layer"(), !dbg !103
  %".3" = call %"struct.ritz_module_1.HashMapI64" @"hashmap_i64_new"(), !dbg !103
  %".4" = call %"struct.ritz_module_1.LayerId" @"layer_id_invalid"(), !dbg !103
  %".5" = insertvalue %"struct.ritz_module_1.LayerTree" undef, %"struct.ritz_module_1.Vec$Layer" %".2", 0 , !dbg !103
  %".6" = insertvalue %"struct.ritz_module_1.LayerTree" %".5", %"struct.ritz_module_1.HashMapI64" %".3", 1 , !dbg !103
  %".7" = insertvalue %"struct.ritz_module_1.LayerTree" %".6", %"struct.ritz_module_1.LayerId" %".4", 2 , !dbg !103
  %".8" = insertvalue %"struct.ritz_module_1.LayerTree" %".7", i64 1, 3 , !dbg !103
  ret %"struct.ritz_module_1.LayerTree" %".8", !dbg !103
}

define %"struct.ritz_module_1.LayerId" @"layer_tree_create_root"(%"struct.ritz_module_1.LayerTree"* %"tree.arg", %"struct.ritz_module_1.NodeId" %"node_id.arg", %"struct.ritz_module_1.LayerRect" %"bounds.arg") !dbg !30
{
entry:
  %"layer.addr" = alloca %"struct.ritz_module_1.Layer", !dbg !114
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerTree"* %"tree.arg", metadata !106, metadata !7), !dbg !107
  %"node_id" = alloca %"struct.ritz_module_1.NodeId"
  store %"struct.ritz_module_1.NodeId" %"node_id.arg", %"struct.ritz_module_1.NodeId"* %"node_id"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.NodeId"* %"node_id", metadata !108, metadata !7), !dbg !107
  %"bounds" = alloca %"struct.ritz_module_1.LayerRect"
  store %"struct.ritz_module_1.LayerRect" %"bounds.arg", %"struct.ritz_module_1.LayerRect"* %"bounds"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerRect"* %"bounds", metadata !110, metadata !7), !dbg !107
  %".10" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 3 , !dbg !111
  %".11" = load i64, i64* %".10", !dbg !111
  %".12" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 3 , !dbg !112
  %".13" = load i64, i64* %".12", !dbg !112
  %".14" = add i64 %".13", 1, !dbg !112
  %".15" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 3 , !dbg !112
  store i64 %".14", i64* %".15", !dbg !112
  %".17" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 3 , !dbg !113
  %".18" = load i64, i64* %".17", !dbg !113
  %".19" = sub i64 %".18", 1, !dbg !113
  %".20" = call %"struct.ritz_module_1.LayerId" @"layer_id_new"(i64 %".19"), !dbg !113
  %".21" = load %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %"node_id", !dbg !114
  %".22" = call %"struct.ritz_module_1.Layer" @"layer_new"(%"struct.ritz_module_1.LayerId" %".20", %"struct.ritz_module_1.NodeId" %".21", i32 0), !dbg !114
  store %"struct.ritz_module_1.Layer" %".22", %"struct.ritz_module_1.Layer"* %"layer.addr", !dbg !114
  %".24" = load %"struct.ritz_module_1.LayerRect", %"struct.ritz_module_1.LayerRect"* %"bounds", !dbg !115
  %".25" = load %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %"layer.addr", !dbg !115
  %".26" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %"layer.addr", i32 0, i32 8 , !dbg !115
  store %"struct.ritz_module_1.LayerRect" %".24", %"struct.ritz_module_1.LayerRect"* %".26", !dbg !115
  %".28" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 0 , !dbg !116
  %".29" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %".28", !dbg !116
  %".30" = extractvalue %"struct.ritz_module_1.Vec$Layer" %".29", 1 , !dbg !116
  %".31" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 1 , !dbg !117
  %".32" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 3 , !dbg !117
  %".33" = load i64, i64* %".32", !dbg !117
  %".34" = sub i64 %".33", 1, !dbg !117
  %".35" = call i32 @"hashmap_i64_insert"(%"struct.ritz_module_1.HashMapI64"* %".31", i64 %".34", i64 %".30"), !dbg !117
  %".36" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 0 , !dbg !118
  %".37" = load %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %"layer.addr", !dbg !118
  %".38" = call i32 @"vec_push$Layer"(%"struct.ritz_module_1.Vec$Layer"* %".36", %"struct.ritz_module_1.Layer" %".37"), !dbg !118
  %".39" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 3 , !dbg !119
  %".40" = load i64, i64* %".39", !dbg !119
  %".41" = sub i64 %".40", 1, !dbg !119
  %".42" = call %"struct.ritz_module_1.LayerId" @"layer_id_new"(i64 %".41"), !dbg !119
  %".43" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 2 , !dbg !119
  store %"struct.ritz_module_1.LayerId" %".42", %"struct.ritz_module_1.LayerId"* %".43", !dbg !119
  %".45" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 3 , !dbg !120
  %".46" = load i64, i64* %".45", !dbg !120
  %".47" = sub i64 %".46", 1, !dbg !120
  %".48" = call %"struct.ritz_module_1.LayerId" @"layer_id_new"(i64 %".47"), !dbg !120
  ret %"struct.ritz_module_1.LayerId" %".48", !dbg !120
}

define %"struct.ritz_module_1.LayerId" @"layer_tree_create"(%"struct.ritz_module_1.LayerTree"* %"tree.arg", %"struct.ritz_module_1.NodeId" %"node_id.arg", i32 %"reason.arg") !dbg !31
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerTree"* %"tree.arg", metadata !121, metadata !7), !dbg !122
  %"node_id" = alloca %"struct.ritz_module_1.NodeId"
  store %"struct.ritz_module_1.NodeId" %"node_id.arg", %"struct.ritz_module_1.NodeId"* %"node_id"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.NodeId"* %"node_id", metadata !123, metadata !7), !dbg !122
  %"reason" = alloca i32
  store i32 %"reason.arg", i32* %"reason"
  call void @"llvm.dbg.declare"(metadata i32* %"reason", metadata !124, metadata !7), !dbg !122
  %".10" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 3 , !dbg !125
  %".11" = load i64, i64* %".10", !dbg !125
  %".12" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 3 , !dbg !126
  %".13" = load i64, i64* %".12", !dbg !126
  %".14" = add i64 %".13", 1, !dbg !126
  %".15" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 3 , !dbg !126
  store i64 %".14", i64* %".15", !dbg !126
  %".17" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 3 , !dbg !127
  %".18" = load i64, i64* %".17", !dbg !127
  %".19" = sub i64 %".18", 1, !dbg !127
  %".20" = call %"struct.ritz_module_1.LayerId" @"layer_id_new"(i64 %".19"), !dbg !127
  %".21" = load %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %"node_id", !dbg !128
  %".22" = load i32, i32* %"reason", !dbg !128
  %".23" = call %"struct.ritz_module_1.Layer" @"layer_new"(%"struct.ritz_module_1.LayerId" %".20", %"struct.ritz_module_1.NodeId" %".21", i32 %".22"), !dbg !128
  %".24" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 0 , !dbg !129
  %".25" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %".24", !dbg !129
  %".26" = extractvalue %"struct.ritz_module_1.Vec$Layer" %".25", 1 , !dbg !129
  %".27" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 1 , !dbg !130
  %".28" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 3 , !dbg !130
  %".29" = load i64, i64* %".28", !dbg !130
  %".30" = sub i64 %".29", 1, !dbg !130
  %".31" = call i32 @"hashmap_i64_insert"(%"struct.ritz_module_1.HashMapI64"* %".27", i64 %".30", i64 %".26"), !dbg !130
  %".32" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 0 , !dbg !131
  %".33" = call i32 @"vec_push$Layer"(%"struct.ritz_module_1.Vec$Layer"* %".32", %"struct.ritz_module_1.Layer" %".23"), !dbg !131
  %".34" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 3 , !dbg !132
  %".35" = load i64, i64* %".34", !dbg !132
  %".36" = sub i64 %".35", 1, !dbg !132
  %".37" = call %"struct.ritz_module_1.LayerId" @"layer_id_new"(i64 %".36"), !dbg !132
  ret %"struct.ritz_module_1.LayerId" %".37", !dbg !132
}

define %"struct.ritz_module_1.Layer"* @"layer_tree_get"(%"struct.ritz_module_1.LayerTree"* %"tree.arg", %"struct.ritz_module_1.LayerId"* %"id.arg") !dbg !32
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerTree"* %"tree.arg", metadata !133, metadata !7), !dbg !134
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerId"* %"id.arg", metadata !135, metadata !7), !dbg !134
  %".6" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 1 , !dbg !136
  %".7" = getelementptr %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId"* %"id.arg", i32 0, i32 0 , !dbg !136
  %".8" = load i64, i64* %".7", !dbg !136
  %".9" = call i64 @"hashmap_i64_get"(%"struct.ritz_module_1.HashMapI64"* %".6", i64 %".8"), !dbg !136
  %".10" = icmp slt i64 %".9", 0 , !dbg !137
  br i1 %".10", label %"if.then", label %"if.end", !dbg !137
if.then:
  %".12" = bitcast i8* null to %"struct.ritz_module_1.Layer"* , !dbg !138
  ret %"struct.ritz_module_1.Layer"* %".12", !dbg !138
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 0 , !dbg !139
  %".15" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %".14", !dbg !139
  %".16" = extractvalue %"struct.ritz_module_1.Vec$Layer" %".15", 1 , !dbg !139
  %".17" = icmp sge i64 %".9", %".16" , !dbg !139
  br i1 %".17", label %"if.then.1", label %"if.end.1", !dbg !139
if.then.1:
  %".19" = bitcast i8* null to %"struct.ritz_module_1.Layer"* , !dbg !140
  ret %"struct.ritz_module_1.Layer"* %".19", !dbg !140
if.end.1:
  %".21" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 0 , !dbg !141
  %".22" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %".21", !dbg !141
  %".23" = extractvalue %"struct.ritz_module_1.Vec$Layer" %".22", 0 , !dbg !141
  %".24" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".23", i64 %".9" , !dbg !141
  ret %"struct.ritz_module_1.Layer"* %".24", !dbg !141
}

define %"struct.ritz_module_1.Layer"* @"layer_tree_get_mut"(%"struct.ritz_module_1.LayerTree"* %"tree.arg", %"struct.ritz_module_1.LayerId"* %"id.arg") !dbg !33
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerTree"* %"tree.arg", metadata !142, metadata !7), !dbg !143
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerId"* %"id.arg", metadata !144, metadata !7), !dbg !143
  %".6" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 1 , !dbg !145
  %".7" = getelementptr %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId"* %"id.arg", i32 0, i32 0 , !dbg !145
  %".8" = load i64, i64* %".7", !dbg !145
  %".9" = call i64 @"hashmap_i64_get"(%"struct.ritz_module_1.HashMapI64"* %".6", i64 %".8"), !dbg !145
  %".10" = icmp slt i64 %".9", 0 , !dbg !146
  br i1 %".10", label %"if.then", label %"if.end", !dbg !146
if.then:
  %".12" = bitcast i8* null to %"struct.ritz_module_1.Layer"* , !dbg !147
  ret %"struct.ritz_module_1.Layer"* %".12", !dbg !147
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 0 , !dbg !148
  %".15" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %".14", !dbg !148
  %".16" = extractvalue %"struct.ritz_module_1.Vec$Layer" %".15", 1 , !dbg !148
  %".17" = icmp sge i64 %".9", %".16" , !dbg !148
  br i1 %".17", label %"if.then.1", label %"if.end.1", !dbg !148
if.then.1:
  %".19" = bitcast i8* null to %"struct.ritz_module_1.Layer"* , !dbg !149
  ret %"struct.ritz_module_1.Layer"* %".19", !dbg !149
if.end.1:
  %".21" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 0 , !dbg !150
  %".22" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %".21", !dbg !150
  %".23" = extractvalue %"struct.ritz_module_1.Vec$Layer" %".22", 0 , !dbg !150
  %".24" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".23", i64 %".9" , !dbg !150
  ret %"struct.ritz_module_1.Layer"* %".24", !dbg !150
}

define %"struct.ritz_module_1.Layer"* @"layer_tree_root"(%"struct.ritz_module_1.LayerTree"* %"tree.arg") !dbg !34
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerTree"* %"tree.arg", metadata !151, metadata !7), !dbg !152
  %".4" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 2 , !dbg !153
  %".5" = call %"struct.ritz_module_1.Layer"* @"layer_tree_get"(%"struct.ritz_module_1.LayerTree"* %"tree.arg", %"struct.ritz_module_1.LayerId"* %".4"), !dbg !153
  ret %"struct.ritz_module_1.Layer"* %".5", !dbg !153
}

define i32 @"layer_tree_count"(%"struct.ritz_module_1.LayerTree"* %"tree.arg") !dbg !35
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerTree"* %"tree.arg", metadata !154, metadata !7), !dbg !155
  %".4" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 1 , !dbg !156
  %".5" = load %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %".4", !dbg !156
  %".6" = extractvalue %"struct.ritz_module_1.HashMapI64" %".5", 2 , !dbg !156
  %".7" = trunc i64 %".6" to i32 , !dbg !156
  ret i32 %".7", !dbg !156
}

define i32 @"layer_tree_mark_dirty"(%"struct.ritz_module_1.LayerTree"* %"tree.arg", %"struct.ritz_module_1.LayerId"* %"id.arg") !dbg !36
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerTree"* %"tree.arg", metadata !157, metadata !7), !dbg !158
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerId"* %"id.arg", metadata !159, metadata !7), !dbg !158
  %".6" = call %"struct.ritz_module_1.Layer"* @"layer_tree_get_mut"(%"struct.ritz_module_1.LayerTree"* %"tree.arg", %"struct.ritz_module_1.LayerId"* %"id.arg"), !dbg !160
  %".7" = icmp ne %"struct.ritz_module_1.Layer"* %".6", null , !dbg !161
  br i1 %".7", label %"if.then", label %"if.end", !dbg !161
if.then:
  %".9" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".6", i32 0, i32 14 , !dbg !162
  %".10" = trunc i64 1 to i32 , !dbg !162
  store i32 %".10", i32* %".9", !dbg !162
  %".12" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".6", i32 0, i32 15 , !dbg !163
  %".13" = trunc i64 1 to i32 , !dbg !163
  store i32 %".13", i32* %".12", !dbg !163
  br label %"if.end", !dbg !163
if.end:
  ret i32 0, !dbg !163
}

define i32 @"layer_tree_clear_dirty"(%"struct.ritz_module_1.LayerTree"* %"tree.arg") !dbg !37
{
entry:
  %"i.addr" = alloca i64, !dbg !166
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerTree"* %"tree.arg", metadata !164, metadata !7), !dbg !165
  store i64 0, i64* %"i.addr", !dbg !166
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !167, metadata !7), !dbg !168
  br label %"while.cond", !dbg !169
while.cond:
  %".7" = load i64, i64* %"i.addr", !dbg !169
  %".8" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 0 , !dbg !169
  %".9" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %".8", !dbg !169
  %".10" = extractvalue %"struct.ritz_module_1.Vec$Layer" %".9", 1 , !dbg !169
  %".11" = icmp slt i64 %".7", %".10" , !dbg !169
  br i1 %".11", label %"while.body", label %"while.end", !dbg !169
while.body:
  %".13" = getelementptr %"struct.ritz_module_1.LayerTree", %"struct.ritz_module_1.LayerTree"* %"tree.arg", i32 0, i32 0 , !dbg !170
  %".14" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %".13", !dbg !170
  %".15" = extractvalue %"struct.ritz_module_1.Vec$Layer" %".14", 0 , !dbg !170
  %".16" = load i64, i64* %"i.addr", !dbg !170
  %".17" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".15", i64 %".16" , !dbg !170
  %".18" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".17", i32 0, i32 14 , !dbg !171
  %".19" = trunc i64 0 to i32 , !dbg !171
  store i32 %".19", i32* %".18", !dbg !171
  %".21" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".17", i32 0, i32 15 , !dbg !172
  %".22" = trunc i64 0 to i32 , !dbg !172
  store i32 %".22", i32* %".21", !dbg !172
  %".24" = load i64, i64* %"i.addr", !dbg !173
  %".25" = add i64 %".24", 1, !dbg !173
  store i64 %".25", i64* %"i.addr", !dbg !173
  br label %"while.cond", !dbg !173
while.end:
  ret i32 0, !dbg !173
}

define i32 @"layer_tree_scroll"(%"struct.ritz_module_1.LayerTree"* %"tree.arg", %"struct.ritz_module_1.LayerId"* %"id.arg", i32 %"offset_x.arg", i32 %"offset_y.arg") !dbg !38
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerTree"* %"tree.arg", metadata !174, metadata !7), !dbg !175
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LayerId"* %"id.arg", metadata !176, metadata !7), !dbg !175
  %"offset_x" = alloca i32
  store i32 %"offset_x.arg", i32* %"offset_x"
  call void @"llvm.dbg.declare"(metadata i32* %"offset_x", metadata !177, metadata !7), !dbg !175
  %"offset_y" = alloca i32
  store i32 %"offset_y.arg", i32* %"offset_y"
  call void @"llvm.dbg.declare"(metadata i32* %"offset_y", metadata !178, metadata !7), !dbg !175
  %".12" = call %"struct.ritz_module_1.Layer"* @"layer_tree_get_mut"(%"struct.ritz_module_1.LayerTree"* %"tree.arg", %"struct.ritz_module_1.LayerId"* %"id.arg"), !dbg !179
  %".13" = icmp ne %"struct.ritz_module_1.Layer"* %".12", null , !dbg !180
  br i1 %".13", label %"if.then", label %"if.end", !dbg !180
if.then:
  %".15" = call i32 @"layer_is_scrollable"(%"struct.ritz_module_1.Layer"* %".12"), !dbg !180
  %".16" = sext i32 %".15" to i64 , !dbg !180
  %".17" = icmp ne i64 %".16", 0 , !dbg !180
  br i1 %".17", label %"if.then.1", label %"if.end.1", !dbg !180
if.end:
  ret i32 0, !dbg !183
if.then.1:
  %".19" = load i32, i32* %"offset_x", !dbg !181
  %".20" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".12", i32 0, i32 12 , !dbg !181
  %".21" = load %"struct.ritz_module_1.LayerPoint", %"struct.ritz_module_1.LayerPoint"* %".20", !dbg !181
  %".22" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".12", i32 0, i32 12 , !dbg !181
  %".23" = getelementptr %"struct.ritz_module_1.LayerPoint", %"struct.ritz_module_1.LayerPoint"* %".22", i32 0, i32 0 , !dbg !181
  store i32 %".19", i32* %".23", !dbg !181
  %".25" = load i32, i32* %"offset_y", !dbg !182
  %".26" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".12", i32 0, i32 12 , !dbg !182
  %".27" = load %"struct.ritz_module_1.LayerPoint", %"struct.ritz_module_1.LayerPoint"* %".26", !dbg !182
  %".28" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".12", i32 0, i32 12 , !dbg !182
  %".29" = getelementptr %"struct.ritz_module_1.LayerPoint", %"struct.ritz_module_1.LayerPoint"* %".28", i32 0, i32 1 , !dbg !182
  store i32 %".25", i32* %".29", !dbg !182
  %".31" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".12", i32 0, i32 15 , !dbg !183
  %".32" = trunc i64 1 to i32 , !dbg !183
  store i32 %".32", i32* %".31", !dbg !183
  br label %"if.end.1", !dbg !183
if.end.1:
  br label %"if.end", !dbg !183
}

define i32 @"should_create_layer"(%"struct.ritz_module_1.ComputedStyle"* %"style.arg") !dbg !39
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ComputedStyle"* %"style.arg", metadata !186, metadata !7), !dbg !187
  %".4" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 19 , !dbg !188
  %".5" = load double, double* %".4", !dbg !188
  %".6" = fcmp olt double %".5", 0x3ff0000000000000 , !dbg !188
  br i1 %".6", label %"if.then", label %"if.end", !dbg !188
if.then:
  ret i32 3, !dbg !189
if.end:
  %".9" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 20 , !dbg !190
  %".10" = load %"struct.ritz_module_1.Transform", %"struct.ritz_module_1.Transform"* %".9", !dbg !190
  %".11" = call i32 @"transform_is_identity"(%"struct.ritz_module_1.Transform" %".10"), !dbg !190
  %".12" = sext i32 %".11" to i64 , !dbg !190
  %".13" = icmp eq i64 %".12", 0 , !dbg !190
  br i1 %".13", label %"if.then.1", label %"if.end.1", !dbg !190
if.then.1:
  ret i32 2, !dbg !191
if.end.1:
  %".16" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 1 , !dbg !192
  %".17" = load i32, i32* %".16", !dbg !192
  %".18" = icmp eq i32 %".17", 3 , !dbg !192
  br i1 %".18", label %"if.then.2", label %"if.end.2", !dbg !192
if.then.2:
  ret i32 5, !dbg !193
if.end.2:
  %".21" = getelementptr %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.ComputedStyle"* %"style.arg", i32 0, i32 1 , !dbg !194
  %".22" = load i32, i32* %".21", !dbg !194
  %".23" = icmp eq i32 %".22", 4 , !dbg !194
  br i1 %".23", label %"if.then.3", label %"if.end.3", !dbg !194
if.then.3:
  ret i32 6, !dbg !195
if.end.3:
  %".26" = sub i64 0, 1, !dbg !196
  %".27" = trunc i64 %".26" to i32 , !dbg !196
  ret i32 %".27", !dbg !196
}

define linkonce_odr i32 @"vec_push$Layer"(%"struct.ritz_module_1.Vec$Layer"* %"v.arg", %"struct.ritz_module_1.Layer" %"item.arg") !dbg !40
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$Layer"* %"v.arg", metadata !199, metadata !7), !dbg !200
  %"item" = alloca %"struct.ritz_module_1.Layer"
  store %"struct.ritz_module_1.Layer" %"item.arg", %"struct.ritz_module_1.Layer"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Layer"* %"item", metadata !201, metadata !7), !dbg !200
  %".7" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 1 , !dbg !202
  %".8" = load i64, i64* %".7", !dbg !202
  %".9" = add i64 %".8", 1, !dbg !202
  %".10" = call i32 @"vec_ensure_cap$Layer"(%"struct.ritz_module_1.Vec$Layer"* %"v.arg", i64 %".9"), !dbg !202
  %".11" = sext i32 %".10" to i64 , !dbg !202
  %".12" = icmp ne i64 %".11", 0 , !dbg !202
  br i1 %".12", label %"if.then", label %"if.end", !dbg !202
if.then:
  %".14" = sub i64 0, 1, !dbg !203
  %".15" = trunc i64 %".14" to i32 , !dbg !203
  ret i32 %".15", !dbg !203
if.end:
  %".17" = load %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %"item", !dbg !204
  %".18" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 0 , !dbg !204
  %".19" = load %"struct.ritz_module_1.Layer"*, %"struct.ritz_module_1.Layer"** %".18", !dbg !204
  %".20" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 1 , !dbg !204
  %".21" = load i64, i64* %".20", !dbg !204
  %".22" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".19", i64 %".21" , !dbg !204
  store %"struct.ritz_module_1.Layer" %".17", %"struct.ritz_module_1.Layer"* %".22", !dbg !204
  %".24" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 1 , !dbg !205
  %".25" = load i64, i64* %".24", !dbg !205
  %".26" = add i64 %".25", 1, !dbg !205
  %".27" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 1 , !dbg !205
  store i64 %".26", i64* %".27", !dbg !205
  %".29" = trunc i64 0 to i32 , !dbg !206
  ret i32 %".29", !dbg !206
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !41
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !214
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !209, metadata !7), !dbg !210
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !211, metadata !7), !dbg !210
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !212
  %".8" = load i64, i64* %".7", !dbg !212
  %".9" = load i64, i64* %"needed", !dbg !212
  %".10" = icmp sge i64 %".8", %".9" , !dbg !212
  br i1 %".10", label %"if.then", label %"if.end", !dbg !212
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !213
  ret i32 %".12", !dbg !213
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !214
  %".15" = load i64, i64* %".14", !dbg !214
  store i64 %".15", i64* %"new_cap.addr", !dbg !214
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !215, metadata !7), !dbg !216
  %".18" = load i64, i64* %"new_cap.addr", !dbg !217
  %".19" = icmp eq i64 %".18", 0 , !dbg !217
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !217
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !218
  br label %"if.end.1", !dbg !218
if.end.1:
  br label %"while.cond", !dbg !219
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !219
  %".25" = load i64, i64* %"needed", !dbg !219
  %".26" = icmp slt i64 %".24", %".25" , !dbg !219
  br i1 %".26", label %"while.body", label %"while.end", !dbg !219
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !220
  %".29" = mul i64 %".28", 2, !dbg !220
  store i64 %".29", i64* %"new_cap.addr", !dbg !220
  br label %"while.cond", !dbg !220
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !221
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !221
  ret i32 %".33", !dbg !221
}

define linkonce_odr %"struct.ritz_module_1.Vec$Layer" @"vec_new$Layer"() !dbg !42
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$Layer", !dbg !222
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$Layer"* %"v.addr", metadata !223, metadata !7), !dbg !224
  %".3" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", !dbg !225
  %".4" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", i32 0, i32 0 , !dbg !225
  %".5" = bitcast i8* null to %"struct.ritz_module_1.Layer"* , !dbg !225
  store %"struct.ritz_module_1.Layer"* %".5", %"struct.ritz_module_1.Layer"** %".4", !dbg !225
  %".7" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", !dbg !226
  %".8" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", i32 0, i32 1 , !dbg !226
  store i64 0, i64* %".8", !dbg !226
  %".10" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", !dbg !227
  %".11" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", i32 0, i32 2 , !dbg !227
  store i64 0, i64* %".11", !dbg !227
  %".13" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", !dbg !228
  ret %"struct.ritz_module_1.Vec$Layer" %".13", !dbg !228
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !43
{
entry:
  %"i" = alloca i64, !dbg !234
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !229, metadata !7), !dbg !230
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !232, metadata !7), !dbg !230
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !233, metadata !7), !dbg !230
  %".10" = load i64, i64* %"len", !dbg !234
  store i64 0, i64* %"i", !dbg !234
  br label %"for.cond", !dbg !234
for.cond:
  %".13" = load i64, i64* %"i", !dbg !234
  %".14" = icmp slt i64 %".13", %".10" , !dbg !234
  br i1 %".14", label %"for.body", label %"for.end", !dbg !234
for.body:
  %".16" = load i8*, i8** %"data", !dbg !234
  %".17" = load i64, i64* %"i", !dbg !234
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !234
  %".19" = load i8, i8* %".18", !dbg !234
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !234
  %".21" = sext i32 %".20" to i64 , !dbg !234
  %".22" = icmp ne i64 %".21", 0 , !dbg !234
  br i1 %".22", label %"if.then", label %"if.end", !dbg !234
for.incr:
  %".28" = load i64, i64* %"i", !dbg !235
  %".29" = add i64 %".28", 1, !dbg !235
  store i64 %".29", i64* %"i", !dbg !235
  br label %"for.cond", !dbg !235
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !236
  ret i32 %".32", !dbg !236
if.then:
  %".24" = sub i64 0, 1, !dbg !235
  %".25" = trunc i64 %".24" to i32 , !dbg !235
  ret i32 %".25", !dbg !235
if.end:
  br label %"for.incr", !dbg !235
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !44
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !239, metadata !7), !dbg !240
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !242, metadata !7), !dbg !240
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !243
  %".8" = load i64, i64* %".7", !dbg !243
  %".9" = add i64 %".8", 1, !dbg !243
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !243
  %".11" = sext i32 %".10" to i64 , !dbg !243
  %".12" = icmp ne i64 %".11", 0 , !dbg !243
  br i1 %".12", label %"if.then", label %"if.end", !dbg !243
if.then:
  %".14" = sub i64 0, 1, !dbg !244
  %".15" = trunc i64 %".14" to i32 , !dbg !244
  ret i32 %".15", !dbg !244
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !245
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !245
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !245
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !245
  %".21" = load i64, i64* %".20", !dbg !245
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !245
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !245
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !246
  %".25" = load i64, i64* %".24", !dbg !246
  %".26" = add i64 %".25", 1, !dbg !246
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !246
  store i64 %".26", i64* %".27", !dbg !246
  %".29" = trunc i64 0 to i32 , !dbg !247
  ret i32 %".29", !dbg !247
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !45
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !248, metadata !7), !dbg !249
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !250, metadata !7), !dbg !249
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !251
  %".8" = load i64, i64* %".7", !dbg !251
  %".9" = add i64 %".8", 1, !dbg !251
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !251
  %".11" = sext i32 %".10" to i64 , !dbg !251
  %".12" = icmp ne i64 %".11", 0 , !dbg !251
  br i1 %".12", label %"if.then", label %"if.end", !dbg !251
if.then:
  %".14" = sub i64 0, 1, !dbg !252
  %".15" = trunc i64 %".14" to i32 , !dbg !252
  ret i32 %".15", !dbg !252
if.end:
  %".17" = load i8, i8* %"item", !dbg !253
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !253
  %".19" = load i8*, i8** %".18", !dbg !253
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !253
  %".21" = load i64, i64* %".20", !dbg !253
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !253
  store i8 %".17", i8* %".22", !dbg !253
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !254
  %".25" = load i64, i64* %".24", !dbg !254
  %".26" = add i64 %".25", 1, !dbg !254
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !254
  store i64 %".26", i64* %".27", !dbg !254
  %".29" = trunc i64 0 to i32 , !dbg !255
  ret i32 %".29", !dbg !255
}

define linkonce_odr i32 @"vec_ensure_cap$Layer"(%"struct.ritz_module_1.Vec$Layer"* %"v.arg", i64 %"needed.arg") !dbg !46
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !261
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$Layer"* %"v.arg", metadata !256, metadata !7), !dbg !257
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !258, metadata !7), !dbg !257
  %".7" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 2 , !dbg !259
  %".8" = load i64, i64* %".7", !dbg !259
  %".9" = load i64, i64* %"needed", !dbg !259
  %".10" = icmp sge i64 %".8", %".9" , !dbg !259
  br i1 %".10", label %"if.then", label %"if.end", !dbg !259
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !260
  ret i32 %".12", !dbg !260
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 2 , !dbg !261
  %".15" = load i64, i64* %".14", !dbg !261
  store i64 %".15", i64* %"new_cap.addr", !dbg !261
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !262, metadata !7), !dbg !263
  %".18" = load i64, i64* %"new_cap.addr", !dbg !264
  %".19" = icmp eq i64 %".18", 0 , !dbg !264
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !264
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !265
  br label %"if.end.1", !dbg !265
if.end.1:
  br label %"while.cond", !dbg !266
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !266
  %".25" = load i64, i64* %"needed", !dbg !266
  %".26" = icmp slt i64 %".24", %".25" , !dbg !266
  br i1 %".26", label %"while.body", label %"while.end", !dbg !266
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !267
  %".29" = mul i64 %".28", 2, !dbg !267
  store i64 %".29", i64* %"new_cap.addr", !dbg !267
  br label %"while.cond", !dbg !267
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !268
  %".33" = call i32 @"vec_grow$Layer"(%"struct.ritz_module_1.Vec$Layer"* %"v.arg", i64 %".32"), !dbg !268
  ret i32 %".33", !dbg !268
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !47
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !274
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !269, metadata !7), !dbg !270
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !271, metadata !7), !dbg !270
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !272
  %".8" = load i64, i64* %".7", !dbg !272
  %".9" = load i64, i64* %"needed", !dbg !272
  %".10" = icmp sge i64 %".8", %".9" , !dbg !272
  br i1 %".10", label %"if.then", label %"if.end", !dbg !272
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !273
  ret i32 %".12", !dbg !273
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !274
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
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !281
  ret i32 %".33", !dbg !281
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !48
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !282, metadata !7), !dbg !283
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !284, metadata !7), !dbg !283
  %".7" = load i64, i64* %"new_cap", !dbg !285
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !285
  %".9" = load i64, i64* %".8", !dbg !285
  %".10" = icmp sle i64 %".7", %".9" , !dbg !285
  br i1 %".10", label %"if.then", label %"if.end", !dbg !285
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !286
  ret i32 %".12", !dbg !286
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !287
  %".15" = mul i64 %".14", 1, !dbg !287
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !288
  %".17" = load i8*, i8** %".16", !dbg !288
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !288
  %".19" = icmp eq i8* %".18", null , !dbg !289
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !289
if.then.1:
  %".21" = sub i64 0, 1, !dbg !290
  %".22" = trunc i64 %".21" to i32 , !dbg !290
  ret i32 %".22", !dbg !290
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !291
  store i8* %".18", i8** %".24", !dbg !291
  %".26" = load i64, i64* %"new_cap", !dbg !292
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !292
  store i64 %".26", i64* %".27", !dbg !292
  %".29" = trunc i64 0 to i32 , !dbg !293
  ret i32 %".29", !dbg !293
}

define linkonce_odr i32 @"vec_grow$Layer"(%"struct.ritz_module_1.Vec$Layer"* %"v.arg", i64 %"new_cap.arg") !dbg !49
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$Layer"* %"v.arg", metadata !294, metadata !7), !dbg !295
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !296, metadata !7), !dbg !295
  %".7" = load i64, i64* %"new_cap", !dbg !297
  %".8" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 2 , !dbg !297
  %".9" = load i64, i64* %".8", !dbg !297
  %".10" = icmp sle i64 %".7", %".9" , !dbg !297
  br i1 %".10", label %"if.then", label %"if.end", !dbg !297
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !298
  ret i32 %".12", !dbg !298
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !299
  %".15" = mul i64 %".14", 184, !dbg !299
  %".16" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 0 , !dbg !300
  %".17" = load %"struct.ritz_module_1.Layer"*, %"struct.ritz_module_1.Layer"** %".16", !dbg !300
  %".18" = bitcast %"struct.ritz_module_1.Layer"* %".17" to i8* , !dbg !300
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !300
  %".20" = icmp eq i8* %".19", null , !dbg !301
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !301
if.then.1:
  %".22" = sub i64 0, 1, !dbg !302
  %".23" = trunc i64 %".22" to i32 , !dbg !302
  ret i32 %".23", !dbg !302
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.Layer"* , !dbg !303
  %".26" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 0 , !dbg !303
  store %"struct.ritz_module_1.Layer"* %".25", %"struct.ritz_module_1.Layer"** %".26", !dbg !303
  %".28" = load i64, i64* %"new_cap", !dbg !304
  %".29" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 2 , !dbg !304
  store i64 %".28", i64* %".29", !dbg !304
  %".31" = trunc i64 0 to i32 , !dbg !305
  ret i32 %".31", !dbg !305
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !50
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !306, metadata !7), !dbg !307
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !308, metadata !7), !dbg !307
  %".7" = load i64, i64* %"new_cap", !dbg !309
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !309
  %".9" = load i64, i64* %".8", !dbg !309
  %".10" = icmp sle i64 %".7", %".9" , !dbg !309
  br i1 %".10", label %"if.then", label %"if.end", !dbg !309
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !310
  ret i32 %".12", !dbg !310
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !311
  %".15" = mul i64 %".14", 16, !dbg !311
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !312
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !312
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !312
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !312
  %".20" = icmp eq i8* %".19", null , !dbg !313
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !313
if.then.1:
  %".22" = sub i64 0, 1, !dbg !314
  %".23" = trunc i64 %".22" to i32 , !dbg !314
  ret i32 %".23", !dbg !314
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !315
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !315
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !315
  %".28" = load i64, i64* %"new_cap", !dbg !316
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !316
  store i64 %".28", i64* %".29", !dbg !316
  %".31" = trunc i64 0 to i32 , !dbg !317
  ret i32 %".31", !dbg !317
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/lib/composite", filename: "layer.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 22, name: "layer_id_new", scopeLine: 22, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 25, name: "layer_id_invalid", scopeLine: 25, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 28, name: "layer_id_is_valid", scopeLine: 28, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 33, name: "layer_id_eq", scopeLine: 33, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 73, name: "layer_rect_new", scopeLine: 73, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 76, name: "layer_rect_zero", scopeLine: 76, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 87, name: "layer_point_new", scopeLine: 87, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 90, name: "layer_point_zero", scopeLine: 90, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 132, name: "layer_new", scopeLine: 132, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 153, name: "layer_is_scrollable", scopeLine: 153, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 158, name: "layer_has_transform", scopeLine: 158, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 163, name: "layer_is_opaque", scopeLine: 163, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "layer_tree_new", scopeLine: 179, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 187, name: "layer_tree_create_root", scopeLine: 187, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 202, name: "layer_tree_create", scopeLine: 202, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 215, name: "layer_tree_get", scopeLine: 215, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 223, name: "layer_tree_get_mut", scopeLine: 223, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 231, name: "layer_tree_root", scopeLine: 231, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 234, name: "layer_tree_count", scopeLine: 234, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 238, name: "layer_tree_mark_dirty", scopeLine: 238, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 245, name: "layer_tree_clear_dirty", scopeLine: 245, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 254, name: "layer_tree_scroll", scopeLine: 254, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 268, name: "should_create_layer", scopeLine: 268, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$Layer", scopeLine: 210, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$Layer", scopeLine: 116, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$Layer", scopeLine: 193, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$Layer", scopeLine: 179, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!51 = !DILocalVariable(file: !0, line: 22, name: "value", scope: !17, type: !15)
!52 = !DILocation(column: 1, line: 22, scope: !17)
!53 = !DILocation(column: 5, line: 23, scope: !17)
!54 = !DILocation(column: 5, line: 26, scope: !18)
!55 = !DICompositeType(align: 64, file: !0, name: "LayerId", size: 64, tag: DW_TAG_structure_type)
!56 = !DIDerivedType(baseType: !55, size: 64, tag: DW_TAG_reference_type)
!57 = !DILocalVariable(file: !0, line: 28, name: "id", scope: !19, type: !56)
!58 = !DILocation(column: 1, line: 28, scope: !19)
!59 = !DILocation(column: 5, line: 29, scope: !19)
!60 = !DILocation(column: 9, line: 30, scope: !19)
!61 = !DILocation(column: 5, line: 31, scope: !19)
!62 = !DILocalVariable(file: !0, line: 33, name: "a", scope: !20, type: !56)
!63 = !DILocation(column: 1, line: 33, scope: !20)
!64 = !DILocalVariable(file: !0, line: 33, name: "b", scope: !20, type: !56)
!65 = !DILocation(column: 5, line: 34, scope: !20)
!66 = !DILocation(column: 9, line: 35, scope: !20)
!67 = !DILocation(column: 5, line: 36, scope: !20)
!68 = !DILocalVariable(file: !0, line: 73, name: "x", scope: !21, type: !10)
!69 = !DILocation(column: 1, line: 73, scope: !21)
!70 = !DILocalVariable(file: !0, line: 73, name: "y", scope: !21, type: !10)
!71 = !DILocalVariable(file: !0, line: 73, name: "width", scope: !21, type: !14)
!72 = !DILocalVariable(file: !0, line: 73, name: "height", scope: !21, type: !14)
!73 = !DILocation(column: 5, line: 74, scope: !21)
!74 = !DILocation(column: 5, line: 77, scope: !22)
!75 = !DILocalVariable(file: !0, line: 87, name: "x", scope: !23, type: !10)
!76 = !DILocation(column: 1, line: 87, scope: !23)
!77 = !DILocalVariable(file: !0, line: 87, name: "y", scope: !23, type: !10)
!78 = !DILocation(column: 5, line: 88, scope: !23)
!79 = !DILocation(column: 5, line: 91, scope: !24)
!80 = !DILocalVariable(file: !0, line: 132, name: "id", scope: !25, type: !55)
!81 = !DILocation(column: 1, line: 132, scope: !25)
!82 = !DICompositeType(align: 64, file: !0, name: "NodeId", size: 64, tag: DW_TAG_structure_type)
!83 = !DILocalVariable(file: !0, line: 132, name: "node_id", scope: !25, type: !82)
!84 = !DILocalVariable(file: !0, line: 132, name: "reason", scope: !25, type: !10)
!85 = !DILocation(column: 5, line: 133, scope: !25)
!86 = !DICompositeType(align: 64, file: !0, name: "Layer", size: 1472, tag: DW_TAG_structure_type)
!87 = !DIDerivedType(baseType: !86, size: 64, tag: DW_TAG_reference_type)
!88 = !DILocalVariable(file: !0, line: 153, name: "layer", scope: !26, type: !87)
!89 = !DILocation(column: 1, line: 153, scope: !26)
!90 = !DILocation(column: 5, line: 154, scope: !26)
!91 = !DILocation(column: 9, line: 155, scope: !26)
!92 = !DILocation(column: 5, line: 156, scope: !26)
!93 = !DILocalVariable(file: !0, line: 158, name: "layer", scope: !27, type: !87)
!94 = !DILocation(column: 1, line: 158, scope: !27)
!95 = !DILocation(column: 5, line: 159, scope: !27)
!96 = !DILocation(column: 9, line: 160, scope: !27)
!97 = !DILocation(column: 5, line: 161, scope: !27)
!98 = !DILocalVariable(file: !0, line: 163, name: "layer", scope: !28, type: !87)
!99 = !DILocation(column: 1, line: 163, scope: !28)
!100 = !DILocation(column: 5, line: 164, scope: !28)
!101 = !DILocation(column: 13, line: 166, scope: !28)
!102 = !DILocation(column: 5, line: 167, scope: !28)
!103 = !DILocation(column: 5, line: 180, scope: !29)
!104 = !DICompositeType(align: 64, file: !0, name: "LayerTree", size: 576, tag: DW_TAG_structure_type)
!105 = !DIDerivedType(baseType: !104, size: 64, tag: DW_TAG_reference_type)
!106 = !DILocalVariable(file: !0, line: 187, name: "tree", scope: !30, type: !105)
!107 = !DILocation(column: 1, line: 187, scope: !30)
!108 = !DILocalVariable(file: !0, line: 187, name: "node_id", scope: !30, type: !82)
!109 = !DICompositeType(align: 32, file: !0, name: "LayerRect", size: 128, tag: DW_TAG_structure_type)
!110 = !DILocalVariable(file: !0, line: 187, name: "bounds", scope: !30, type: !109)
!111 = !DILocation(column: 5, line: 188, scope: !30)
!112 = !DILocation(column: 5, line: 189, scope: !30)
!113 = !DILocation(column: 5, line: 191, scope: !30)
!114 = !DILocation(column: 5, line: 192, scope: !30)
!115 = !DILocation(column: 5, line: 193, scope: !30)
!116 = !DILocation(column: 5, line: 195, scope: !30)
!117 = !DILocation(column: 5, line: 196, scope: !30)
!118 = !DILocation(column: 5, line: 197, scope: !30)
!119 = !DILocation(column: 5, line: 198, scope: !30)
!120 = !DILocation(column: 5, line: 200, scope: !30)
!121 = !DILocalVariable(file: !0, line: 202, name: "tree", scope: !31, type: !105)
!122 = !DILocation(column: 1, line: 202, scope: !31)
!123 = !DILocalVariable(file: !0, line: 202, name: "node_id", scope: !31, type: !82)
!124 = !DILocalVariable(file: !0, line: 202, name: "reason", scope: !31, type: !10)
!125 = !DILocation(column: 5, line: 203, scope: !31)
!126 = !DILocation(column: 5, line: 204, scope: !31)
!127 = !DILocation(column: 5, line: 206, scope: !31)
!128 = !DILocation(column: 5, line: 207, scope: !31)
!129 = !DILocation(column: 5, line: 209, scope: !31)
!130 = !DILocation(column: 5, line: 210, scope: !31)
!131 = !DILocation(column: 5, line: 211, scope: !31)
!132 = !DILocation(column: 5, line: 213, scope: !31)
!133 = !DILocalVariable(file: !0, line: 215, name: "tree", scope: !32, type: !105)
!134 = !DILocation(column: 1, line: 215, scope: !32)
!135 = !DILocalVariable(file: !0, line: 215, name: "id", scope: !32, type: !56)
!136 = !DILocation(column: 5, line: 216, scope: !32)
!137 = !DILocation(column: 5, line: 217, scope: !32)
!138 = !DILocation(column: 9, line: 218, scope: !32)
!139 = !DILocation(column: 5, line: 219, scope: !32)
!140 = !DILocation(column: 9, line: 220, scope: !32)
!141 = !DILocation(column: 5, line: 221, scope: !32)
!142 = !DILocalVariable(file: !0, line: 223, name: "tree", scope: !33, type: !105)
!143 = !DILocation(column: 1, line: 223, scope: !33)
!144 = !DILocalVariable(file: !0, line: 223, name: "id", scope: !33, type: !56)
!145 = !DILocation(column: 5, line: 224, scope: !33)
!146 = !DILocation(column: 5, line: 225, scope: !33)
!147 = !DILocation(column: 9, line: 226, scope: !33)
!148 = !DILocation(column: 5, line: 227, scope: !33)
!149 = !DILocation(column: 9, line: 228, scope: !33)
!150 = !DILocation(column: 5, line: 229, scope: !33)
!151 = !DILocalVariable(file: !0, line: 231, name: "tree", scope: !34, type: !105)
!152 = !DILocation(column: 1, line: 231, scope: !34)
!153 = !DILocation(column: 5, line: 232, scope: !34)
!154 = !DILocalVariable(file: !0, line: 234, name: "tree", scope: !35, type: !105)
!155 = !DILocation(column: 1, line: 234, scope: !35)
!156 = !DILocation(column: 5, line: 235, scope: !35)
!157 = !DILocalVariable(file: !0, line: 238, name: "tree", scope: !36, type: !105)
!158 = !DILocation(column: 1, line: 238, scope: !36)
!159 = !DILocalVariable(file: !0, line: 238, name: "id", scope: !36, type: !56)
!160 = !DILocation(column: 5, line: 239, scope: !36)
!161 = !DILocation(column: 5, line: 240, scope: !36)
!162 = !DILocation(column: 9, line: 241, scope: !36)
!163 = !DILocation(column: 9, line: 242, scope: !36)
!164 = !DILocalVariable(file: !0, line: 245, name: "tree", scope: !37, type: !105)
!165 = !DILocation(column: 1, line: 245, scope: !37)
!166 = !DILocation(column: 5, line: 246, scope: !37)
!167 = !DILocalVariable(file: !0, line: 246, name: "i", scope: !37, type: !11)
!168 = !DILocation(column: 1, line: 246, scope: !37)
!169 = !DILocation(column: 5, line: 247, scope: !37)
!170 = !DILocation(column: 9, line: 248, scope: !37)
!171 = !DILocation(column: 9, line: 249, scope: !37)
!172 = !DILocation(column: 9, line: 250, scope: !37)
!173 = !DILocation(column: 9, line: 251, scope: !37)
!174 = !DILocalVariable(file: !0, line: 254, name: "tree", scope: !38, type: !105)
!175 = !DILocation(column: 1, line: 254, scope: !38)
!176 = !DILocalVariable(file: !0, line: 254, name: "id", scope: !38, type: !56)
!177 = !DILocalVariable(file: !0, line: 254, name: "offset_x", scope: !38, type: !10)
!178 = !DILocalVariable(file: !0, line: 254, name: "offset_y", scope: !38, type: !10)
!179 = !DILocation(column: 5, line: 255, scope: !38)
!180 = !DILocation(column: 5, line: 256, scope: !38)
!181 = !DILocation(column: 13, line: 258, scope: !38)
!182 = !DILocation(column: 13, line: 259, scope: !38)
!183 = !DILocation(column: 13, line: 260, scope: !38)
!184 = !DICompositeType(align: 64, file: !0, name: "ComputedStyle", size: 3840, tag: DW_TAG_structure_type)
!185 = !DIDerivedType(baseType: !184, size: 64, tag: DW_TAG_reference_type)
!186 = !DILocalVariable(file: !0, line: 268, name: "style", scope: !39, type: !185)
!187 = !DILocation(column: 1, line: 268, scope: !39)
!188 = !DILocation(column: 5, line: 270, scope: !39)
!189 = !DILocation(column: 9, line: 271, scope: !39)
!190 = !DILocation(column: 5, line: 273, scope: !39)
!191 = !DILocation(column: 9, line: 274, scope: !39)
!192 = !DILocation(column: 5, line: 276, scope: !39)
!193 = !DILocation(column: 9, line: 277, scope: !39)
!194 = !DILocation(column: 5, line: 279, scope: !39)
!195 = !DILocation(column: 9, line: 280, scope: !39)
!196 = !DILocation(column: 5, line: 286, scope: !39)
!197 = !DICompositeType(align: 64, file: !0, name: "Vec$Layer", size: 192, tag: DW_TAG_structure_type)
!198 = !DIDerivedType(baseType: !197, size: 64, tag: DW_TAG_reference_type)
!199 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !40, type: !198)
!200 = !DILocation(column: 1, line: 210, scope: !40)
!201 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !40, type: !86)
!202 = !DILocation(column: 5, line: 211, scope: !40)
!203 = !DILocation(column: 9, line: 212, scope: !40)
!204 = !DILocation(column: 5, line: 213, scope: !40)
!205 = !DILocation(column: 5, line: 214, scope: !40)
!206 = !DILocation(column: 5, line: 215, scope: !40)
!207 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!208 = !DIDerivedType(baseType: !207, size: 64, tag: DW_TAG_reference_type)
!209 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !41, type: !208)
!210 = !DILocation(column: 1, line: 193, scope: !41)
!211 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !41, type: !11)
!212 = !DILocation(column: 5, line: 194, scope: !41)
!213 = !DILocation(column: 9, line: 195, scope: !41)
!214 = !DILocation(column: 5, line: 197, scope: !41)
!215 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !41, type: !11)
!216 = !DILocation(column: 1, line: 197, scope: !41)
!217 = !DILocation(column: 5, line: 198, scope: !41)
!218 = !DILocation(column: 9, line: 199, scope: !41)
!219 = !DILocation(column: 5, line: 200, scope: !41)
!220 = !DILocation(column: 9, line: 201, scope: !41)
!221 = !DILocation(column: 5, line: 203, scope: !41)
!222 = !DILocation(column: 5, line: 117, scope: !42)
!223 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !42, type: !197)
!224 = !DILocation(column: 1, line: 117, scope: !42)
!225 = !DILocation(column: 5, line: 118, scope: !42)
!226 = !DILocation(column: 5, line: 119, scope: !42)
!227 = !DILocation(column: 5, line: 120, scope: !42)
!228 = !DILocation(column: 5, line: 121, scope: !42)
!229 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !43, type: !208)
!230 = !DILocation(column: 1, line: 288, scope: !43)
!231 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!232 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !43, type: !231)
!233 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !43, type: !11)
!234 = !DILocation(column: 5, line: 289, scope: !43)
!235 = !DILocation(column: 13, line: 291, scope: !43)
!236 = !DILocation(column: 5, line: 292, scope: !43)
!237 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!238 = !DIDerivedType(baseType: !237, size: 64, tag: DW_TAG_reference_type)
!239 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !44, type: !238)
!240 = !DILocation(column: 1, line: 210, scope: !44)
!241 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!242 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !44, type: !241)
!243 = !DILocation(column: 5, line: 211, scope: !44)
!244 = !DILocation(column: 9, line: 212, scope: !44)
!245 = !DILocation(column: 5, line: 213, scope: !44)
!246 = !DILocation(column: 5, line: 214, scope: !44)
!247 = !DILocation(column: 5, line: 215, scope: !44)
!248 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !45, type: !208)
!249 = !DILocation(column: 1, line: 210, scope: !45)
!250 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !45, type: !12)
!251 = !DILocation(column: 5, line: 211, scope: !45)
!252 = !DILocation(column: 9, line: 212, scope: !45)
!253 = !DILocation(column: 5, line: 213, scope: !45)
!254 = !DILocation(column: 5, line: 214, scope: !45)
!255 = !DILocation(column: 5, line: 215, scope: !45)
!256 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !46, type: !198)
!257 = !DILocation(column: 1, line: 193, scope: !46)
!258 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !46, type: !11)
!259 = !DILocation(column: 5, line: 194, scope: !46)
!260 = !DILocation(column: 9, line: 195, scope: !46)
!261 = !DILocation(column: 5, line: 197, scope: !46)
!262 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !46, type: !11)
!263 = !DILocation(column: 1, line: 197, scope: !46)
!264 = !DILocation(column: 5, line: 198, scope: !46)
!265 = !DILocation(column: 9, line: 199, scope: !46)
!266 = !DILocation(column: 5, line: 200, scope: !46)
!267 = !DILocation(column: 9, line: 201, scope: !46)
!268 = !DILocation(column: 5, line: 203, scope: !46)
!269 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !47, type: !238)
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
!282 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !48, type: !208)
!283 = !DILocation(column: 1, line: 179, scope: !48)
!284 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !48, type: !11)
!285 = !DILocation(column: 5, line: 180, scope: !48)
!286 = !DILocation(column: 9, line: 181, scope: !48)
!287 = !DILocation(column: 5, line: 183, scope: !48)
!288 = !DILocation(column: 5, line: 184, scope: !48)
!289 = !DILocation(column: 5, line: 185, scope: !48)
!290 = !DILocation(column: 9, line: 186, scope: !48)
!291 = !DILocation(column: 5, line: 188, scope: !48)
!292 = !DILocation(column: 5, line: 189, scope: !48)
!293 = !DILocation(column: 5, line: 190, scope: !48)
!294 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !49, type: !198)
!295 = !DILocation(column: 1, line: 179, scope: !49)
!296 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !49, type: !11)
!297 = !DILocation(column: 5, line: 180, scope: !49)
!298 = !DILocation(column: 9, line: 181, scope: !49)
!299 = !DILocation(column: 5, line: 183, scope: !49)
!300 = !DILocation(column: 5, line: 184, scope: !49)
!301 = !DILocation(column: 5, line: 185, scope: !49)
!302 = !DILocation(column: 9, line: 186, scope: !49)
!303 = !DILocation(column: 5, line: 188, scope: !49)
!304 = !DILocation(column: 5, line: 189, scope: !49)
!305 = !DILocation(column: 5, line: 190, scope: !49)
!306 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !50, type: !238)
!307 = !DILocation(column: 1, line: 179, scope: !50)
!308 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !50, type: !11)
!309 = !DILocation(column: 5, line: 180, scope: !50)
!310 = !DILocation(column: 9, line: 181, scope: !50)
!311 = !DILocation(column: 5, line: 183, scope: !50)
!312 = !DILocation(column: 5, line: 184, scope: !50)
!313 = !DILocation(column: 5, line: 185, scope: !50)
!314 = !DILocation(column: 9, line: 186, scope: !50)
!315 = !DILocation(column: 5, line: 188, scope: !50)
!316 = !DILocation(column: 5, line: 189, scope: !50)
!317 = !DILocation(column: 5, line: 190, scope: !50)