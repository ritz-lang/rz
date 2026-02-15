; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Vec$LineBounds" = type {%"struct.ritz_module_1.LineBounds"*, i64, i64}
%"struct.ritz_module_1.Vec$u8" = type {i8*, i64, i64}
%"struct.ritz_module_1.Vec$RenderNode" = type {%"struct.ritz_module_1.RenderNode"*, i64, i64}
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
%"struct.ritz_module_1.Arena" = type {i8*, i64, i64}
%"struct.ritz_module_1.BlockHeader" = type {i64}
%"struct.ritz_module_1.FreeNode" = type {%"struct.ritz_module_1.FreeNode"*}
%"struct.ritz_module_1.SizeBin" = type {%"struct.ritz_module_1.FreeNode"*, i64, i8*, i64, i64}
%"struct.ritz_module_1.GlobalAlloc" = type {[9 x %"struct.ritz_module_1.SizeBin"], i32}
%"struct.ritz_module_1.LineBounds" = type {i64, i64}
%"struct.ritz_module_1.HashMapEntryI64" = type {i64, i64, i32}
%"struct.ritz_module_1.HashMapI64" = type {%"struct.ritz_module_1.HashMapEntryI64"*, i64, i64, i64}
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

declare %"struct.ritz_module_1.DirtyFlags" @"dirty_flags_none"()

declare %"struct.ritz_module_1.DirtyFlags" @"dirty_flags_all"()

declare i32 @"dirty_flags_is_clean"(%"struct.ritz_module_1.DirtyFlags" %".1")

declare i32 @"dirty_flags_needs_layout"(%"struct.ritz_module_1.DirtyFlags" %".1")

declare i32 @"dirty_flags_needs_paint"(%"struct.ritz_module_1.DirtyFlags" %".1")

declare %"struct.ritz_module_1.LayoutResult" @"layout_result_empty"()

declare i32 @"layout_result_outer_width"(%"struct.ritz_module_1.LayoutResult" %".1")

declare i32 @"layout_result_outer_height"(%"struct.ritz_module_1.LayoutResult" %".1")

declare %"struct.ritz_module_1.RenderNode" @"render_node_new"(%"struct.ritz_module_1.NodeId" %".1", i32 %".2", %"struct.ritz_module_1.ComputedStyle" %".3")

declare %"struct.ritz_module_1.RenderNode" @"render_node_new_text"(%"struct.ritz_module_1.NodeId" %".1", i8* %".2", i32 %".3", %"struct.ritz_module_1.ComputedStyle" %".4")

declare i32 @"render_node_is_text"(%"struct.ritz_module_1.RenderNode" %".1")

declare i32 @"render_node_is_replaced"(%"struct.ritz_module_1.RenderNode" %".1")

declare i32 @"render_node_has_children"(%"struct.ritz_module_1.RenderNode" %".1")

declare i32 @"render_node_is_block"(%"struct.ritz_module_1.RenderNode" %".1")

declare i32 @"render_node_is_inline"(%"struct.ritz_module_1.RenderNode" %".1")

declare i32 @"render_node_generates_layer"(%"struct.ritz_module_1.RenderNode" %".1")

declare %"struct.ritz_module_1.RenderTree" @"render_tree_new"()

declare %"struct.ritz_module_1.RenderNode"* @"render_tree_get"(%"struct.ritz_module_1.RenderTree"* %".1", %"struct.ritz_module_1.NodeId"* %".2")

declare %"struct.ritz_module_1.RenderNode"* @"render_tree_get_mut"(%"struct.ritz_module_1.RenderTree"* %".1", %"struct.ritz_module_1.NodeId"* %".2")

declare i32 @"render_tree_insert"(%"struct.ritz_module_1.RenderTree"* %".1", %"struct.ritz_module_1.RenderNode" %".2")

declare i32 @"render_tree_set_root"(%"struct.ritz_module_1.RenderTree"* %".1", %"struct.ritz_module_1.NodeId" %".2")

declare %"struct.ritz_module_1.RenderNode"* @"render_tree_root"(%"struct.ritz_module_1.RenderTree"* %".1")

declare i32 @"render_tree_count"(%"struct.ritz_module_1.RenderTree"* %".1")

declare i32 @"render_tree_is_empty"(%"struct.ritz_module_1.RenderTree"* %".1")

declare i32 @"render_tree_mark_dirty"(%"struct.ritz_module_1.RenderTree"* %".1", %"struct.ritz_module_1.NodeId" %".2", %"struct.ritz_module_1.DirtyFlags" %".3")

declare i32 @"render_tree_clear_dirty"(%"struct.ritz_module_1.RenderTree"* %".1", %"struct.ritz_module_1.NodeId" %".2")

define i32 @"test_render_node_new"() !dbg !17
{
entry:
  %".2" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !38
  %".3" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !39
  %".4" = call %"struct.ritz_module_1.RenderNode" @"render_node_new"(%"struct.ritz_module_1.NodeId" %".2", i32 0, %"struct.ritz_module_1.ComputedStyle" %".3"), !dbg !40
  %".5" = extractvalue %"struct.ritz_module_1.RenderNode" %".4", 0 , !dbg !41
  %".6" = extractvalue %"struct.ritz_module_1.NodeId" %".5", 0 , !dbg !41
  %".7" = icmp ne i64 %".6", 1 , !dbg !41
  br i1 %".7", label %"if.then", label %"if.end", !dbg !41
if.then:
  %".9" = trunc i64 1 to i32 , !dbg !42
  ret i32 %".9", !dbg !42
if.end:
  %".11" = extractvalue %"struct.ritz_module_1.RenderNode" %".4", 1 , !dbg !43
  %".12" = icmp ne i32 %".11", 0 , !dbg !43
  br i1 %".12", label %"if.then.1", label %"if.end.1", !dbg !43
if.then.1:
  %".14" = trunc i64 2 to i32 , !dbg !44
  ret i32 %".14", !dbg !44
if.end.1:
  %".16" = extractvalue %"struct.ritz_module_1.RenderNode" %".4", 16 , !dbg !45
  %".17" = call i32 @"dirty_flags_is_clean"(%"struct.ritz_module_1.DirtyFlags" %".16"), !dbg !45
  %".18" = sext i32 %".17" to i64 , !dbg !45
  %".19" = icmp ne i64 %".18", 0 , !dbg !45
  br i1 %".19", label %"if.then.2", label %"if.end.2", !dbg !45
if.then.2:
  %".21" = trunc i64 3 to i32 , !dbg !46
  ret i32 %".21", !dbg !46
if.end.2:
  %".23" = trunc i64 0 to i32 , !dbg !47
  ret i32 %".23", !dbg !47
}

define i32 @"test_render_node_new_text"() !dbg !18
{
entry:
  %".2" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 2), !dbg !48
  %".3" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !49
  %".4" = getelementptr [6 x i8], [6 x i8]* @".str.0", i64 0, i64 0 , !dbg !50
  %".5" = trunc i64 5 to i32 , !dbg !51
  %".6" = call %"struct.ritz_module_1.RenderNode" @"render_node_new_text"(%"struct.ritz_module_1.NodeId" %".2", i8* %".4", i32 %".5", %"struct.ritz_module_1.ComputedStyle" %".3"), !dbg !51
  %".7" = call i32 @"render_node_is_text"(%"struct.ritz_module_1.RenderNode" %".6"), !dbg !52
  %".8" = sext i32 %".7" to i64 , !dbg !52
  %".9" = icmp eq i64 %".8", 0 , !dbg !52
  br i1 %".9", label %"if.then", label %"if.end", !dbg !52
if.then:
  %".11" = trunc i64 1 to i32 , !dbg !53
  ret i32 %".11", !dbg !53
if.end:
  %".13" = trunc i64 0 to i32 , !dbg !54
  ret i32 %".13", !dbg !54
}

define i32 @"test_render_tree_new"() !dbg !19
{
entry:
  %".2" = call %"struct.ritz_module_1.RenderTree" @"render_tree_new"(), !dbg !55
  %"tree.addr" = alloca %"struct.ritz_module_1.RenderTree", !dbg !56
  store %"struct.ritz_module_1.RenderTree" %".2", %"struct.ritz_module_1.RenderTree"* %"tree.addr", !dbg !56
  %".4" = call i32 @"render_tree_is_empty"(%"struct.ritz_module_1.RenderTree"* %"tree.addr"), !dbg !56
  %".5" = sext i32 %".4" to i64 , !dbg !56
  %".6" = icmp eq i64 %".5", 0 , !dbg !56
  br i1 %".6", label %"if.then", label %"if.end", !dbg !56
if.then:
  %".8" = trunc i64 1 to i32 , !dbg !57
  ret i32 %".8", !dbg !57
if.end:
  %"tree.addr.1" = alloca %"struct.ritz_module_1.RenderTree", !dbg !58
  store %"struct.ritz_module_1.RenderTree" %".2", %"struct.ritz_module_1.RenderTree"* %"tree.addr.1", !dbg !58
  %".11" = call i32 @"render_tree_count"(%"struct.ritz_module_1.RenderTree"* %"tree.addr.1"), !dbg !58
  %".12" = sext i32 %".11" to i64 , !dbg !58
  %".13" = icmp ne i64 %".12", 0 , !dbg !58
  br i1 %".13", label %"if.then.1", label %"if.end.1", !dbg !58
if.then.1:
  %".15" = trunc i64 2 to i32 , !dbg !59
  ret i32 %".15", !dbg !59
if.end.1:
  %".17" = trunc i64 0 to i32 , !dbg !60
  ret i32 %".17", !dbg !60
}

define i32 @"test_render_tree_insert_and_get"() !dbg !20
{
entry:
  %"tree.addr" = alloca %"struct.ritz_module_1.RenderTree", !dbg !61
  %".2" = call %"struct.ritz_module_1.RenderTree" @"render_tree_new"(), !dbg !61
  store %"struct.ritz_module_1.RenderTree" %".2", %"struct.ritz_module_1.RenderTree"* %"tree.addr", !dbg !61
  %".4" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 42), !dbg !62
  %".5" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !63
  %".6" = call %"struct.ritz_module_1.RenderNode" @"render_node_new"(%"struct.ritz_module_1.NodeId" %".4", i32 1, %"struct.ritz_module_1.ComputedStyle" %".5"), !dbg !64
  %".7" = call i32 @"render_tree_insert"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.RenderNode" %".6"), !dbg !65
  %".8" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 42), !dbg !66
  %"lookup_id.addr" = alloca %"struct.ritz_module_1.NodeId", !dbg !67
  store %"struct.ritz_module_1.NodeId" %".8", %"struct.ritz_module_1.NodeId"* %"lookup_id.addr", !dbg !67
  %".10" = call %"struct.ritz_module_1.RenderNode"* @"render_tree_get"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.NodeId"* %"lookup_id.addr"), !dbg !67
  %".11" = icmp eq %"struct.ritz_module_1.RenderNode"* %".10", null , !dbg !68
  br i1 %".11", label %"if.then", label %"if.end", !dbg !68
if.then:
  %".13" = trunc i64 1 to i32 , !dbg !69
  ret i32 %".13", !dbg !69
if.end:
  %".15" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".10", i32 0, i32 0 , !dbg !70
  %".16" = load %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %".15", !dbg !70
  %".17" = extractvalue %"struct.ritz_module_1.NodeId" %".16", 0 , !dbg !70
  %".18" = icmp ne i64 %".17", 42 , !dbg !70
  br i1 %".18", label %"if.then.1", label %"if.end.1", !dbg !70
if.then.1:
  %".20" = trunc i64 2 to i32 , !dbg !71
  ret i32 %".20", !dbg !71
if.end.1:
  %".22" = trunc i64 0 to i32 , !dbg !72
  ret i32 %".22", !dbg !72
}

define i32 @"test_render_tree_set_root"() !dbg !21
{
entry:
  %"tree.addr" = alloca %"struct.ritz_module_1.RenderTree", !dbg !73
  %".2" = call %"struct.ritz_module_1.RenderTree" @"render_tree_new"(), !dbg !73
  store %"struct.ritz_module_1.RenderTree" %".2", %"struct.ritz_module_1.RenderTree"* %"tree.addr", !dbg !73
  %".4" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !74
  %".5" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !75
  %".6" = call %"struct.ritz_module_1.RenderNode" @"render_node_new"(%"struct.ritz_module_1.NodeId" %".4", i32 0, %"struct.ritz_module_1.ComputedStyle" %".5"), !dbg !76
  %".7" = call i32 @"render_tree_insert"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.RenderNode" %".6"), !dbg !77
  %".8" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !78
  %".9" = call i32 @"render_tree_set_root"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.NodeId" %".8"), !dbg !78
  %".10" = call %"struct.ritz_module_1.RenderNode"* @"render_tree_root"(%"struct.ritz_module_1.RenderTree"* %"tree.addr"), !dbg !79
  %".11" = icmp eq %"struct.ritz_module_1.RenderNode"* %".10", null , !dbg !80
  br i1 %".11", label %"if.then", label %"if.end", !dbg !80
if.then:
  %".13" = trunc i64 1 to i32 , !dbg !81
  ret i32 %".13", !dbg !81
if.end:
  %".15" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".10", i32 0, i32 0 , !dbg !82
  %".16" = load %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId"* %".15", !dbg !82
  %".17" = extractvalue %"struct.ritz_module_1.NodeId" %".16", 0 , !dbg !82
  %".18" = icmp ne i64 %".17", 1 , !dbg !82
  br i1 %".18", label %"if.then.1", label %"if.end.1", !dbg !82
if.then.1:
  %".20" = trunc i64 2 to i32 , !dbg !83
  ret i32 %".20", !dbg !83
if.end.1:
  %".22" = trunc i64 0 to i32 , !dbg !84
  ret i32 %".22", !dbg !84
}

define i32 @"test_render_tree_count"() !dbg !22
{
entry:
  %"tree.addr" = alloca %"struct.ritz_module_1.RenderTree", !dbg !85
  %".2" = call %"struct.ritz_module_1.RenderTree" @"render_tree_new"(), !dbg !85
  store %"struct.ritz_module_1.RenderTree" %".2", %"struct.ritz_module_1.RenderTree"* %"tree.addr", !dbg !85
  %".4" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !86
  %".5" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 2), !dbg !87
  %".6" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !88
  %".7" = call %"struct.ritz_module_1.RenderNode" @"render_node_new"(%"struct.ritz_module_1.NodeId" %".4", i32 0, %"struct.ritz_module_1.ComputedStyle" %".6"), !dbg !89
  %".8" = call i32 @"render_tree_insert"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.RenderNode" %".7"), !dbg !89
  %".9" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !90
  %".10" = call %"struct.ritz_module_1.RenderNode" @"render_node_new"(%"struct.ritz_module_1.NodeId" %".5", i32 0, %"struct.ritz_module_1.ComputedStyle" %".9"), !dbg !91
  %".11" = call i32 @"render_tree_insert"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.RenderNode" %".10"), !dbg !91
  %".12" = call i32 @"render_tree_count"(%"struct.ritz_module_1.RenderTree"* %"tree.addr"), !dbg !92
  %".13" = sext i32 %".12" to i64 , !dbg !92
  %".14" = icmp ne i64 %".13", 2 , !dbg !92
  br i1 %".14", label %"if.then", label %"if.end", !dbg !92
if.then:
  %".16" = trunc i64 1 to i32 , !dbg !93
  ret i32 %".16", !dbg !93
if.end:
  %".18" = trunc i64 0 to i32 , !dbg !94
  ret i32 %".18", !dbg !94
}

define i32 @"test_dirty_flags_none"() !dbg !23
{
entry:
  %".2" = call %"struct.ritz_module_1.DirtyFlags" @"dirty_flags_none"(), !dbg !95
  %".3" = call i32 @"dirty_flags_is_clean"(%"struct.ritz_module_1.DirtyFlags" %".2"), !dbg !96
  %".4" = sext i32 %".3" to i64 , !dbg !96
  %".5" = icmp eq i64 %".4", 0 , !dbg !96
  br i1 %".5", label %"if.then", label %"if.end", !dbg !96
if.then:
  %".7" = trunc i64 1 to i32 , !dbg !97
  ret i32 %".7", !dbg !97
if.end:
  %".9" = trunc i64 0 to i32 , !dbg !98
  ret i32 %".9", !dbg !98
}

define i32 @"test_dirty_flags_all"() !dbg !24
{
entry:
  %".2" = call %"struct.ritz_module_1.DirtyFlags" @"dirty_flags_all"(), !dbg !99
  %".3" = extractvalue %"struct.ritz_module_1.DirtyFlags" %".2", 0 , !dbg !100
  %".4" = sext i32 %".3" to i64 , !dbg !100
  %".5" = icmp eq i64 %".4", 0 , !dbg !100
  br i1 %".5", label %"if.then", label %"if.end", !dbg !100
if.then:
  %".7" = trunc i64 2 to i32 , !dbg !101
  ret i32 %".7", !dbg !101
if.end:
  %".9" = extractvalue %"struct.ritz_module_1.DirtyFlags" %".2", 1 , !dbg !102
  %".10" = sext i32 %".9" to i64 , !dbg !102
  %".11" = icmp eq i64 %".10", 0 , !dbg !102
  br i1 %".11", label %"if.then.1", label %"if.end.1", !dbg !102
if.then.1:
  %".13" = trunc i64 3 to i32 , !dbg !103
  ret i32 %".13", !dbg !103
if.end.1:
  %".15" = extractvalue %"struct.ritz_module_1.DirtyFlags" %".2", 2 , !dbg !104
  %".16" = sext i32 %".15" to i64 , !dbg !104
  %".17" = icmp eq i64 %".16", 0 , !dbg !104
  br i1 %".17", label %"if.then.2", label %"if.end.2", !dbg !104
if.then.2:
  %".19" = trunc i64 4 to i32 , !dbg !105
  ret i32 %".19", !dbg !105
if.end.2:
  %".21" = extractvalue %"struct.ritz_module_1.DirtyFlags" %".2", 3 , !dbg !106
  %".22" = sext i32 %".21" to i64 , !dbg !106
  %".23" = icmp eq i64 %".22", 0 , !dbg !106
  br i1 %".23", label %"if.then.3", label %"if.end.3", !dbg !106
if.then.3:
  %".25" = trunc i64 5 to i32 , !dbg !107
  ret i32 %".25", !dbg !107
if.end.3:
  %".27" = call %"struct.ritz_module_1.DirtyFlags" @"dirty_flags_all"(), !dbg !108
  %".28" = call i32 @"dirty_flags_is_clean"(%"struct.ritz_module_1.DirtyFlags" %".27"), !dbg !109
  %".29" = sext i32 %".28" to i64 , !dbg !109
  %".30" = icmp ne i64 %".29", 0 , !dbg !109
  br i1 %".30", label %"if.then.4", label %"if.end.4", !dbg !109
if.then.4:
  %".32" = trunc i64 1 to i32 , !dbg !110
  ret i32 %".32", !dbg !110
if.end.4:
  %".34" = trunc i64 0 to i32 , !dbg !111
  ret i32 %".34", !dbg !111
}

define i32 @"test_render_tree_mark_dirty"() !dbg !25
{
entry:
  %"tree.addr" = alloca %"struct.ritz_module_1.RenderTree", !dbg !112
  %"node.addr" = alloca %"struct.ritz_module_1.RenderNode", !dbg !115
  %".2" = call %"struct.ritz_module_1.RenderTree" @"render_tree_new"(), !dbg !112
  store %"struct.ritz_module_1.RenderTree" %".2", %"struct.ritz_module_1.RenderTree"* %"tree.addr", !dbg !112
  %".4" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !113
  %".5" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !114
  %".6" = call %"struct.ritz_module_1.RenderNode" @"render_node_new"(%"struct.ritz_module_1.NodeId" %".4", i32 0, %"struct.ritz_module_1.ComputedStyle" %".5"), !dbg !115
  store %"struct.ritz_module_1.RenderNode" %".6", %"struct.ritz_module_1.RenderNode"* %"node.addr", !dbg !115
  %".8" = call %"struct.ritz_module_1.DirtyFlags" @"dirty_flags_none"(), !dbg !116
  %".9" = load %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node.addr", !dbg !116
  %".10" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node.addr", i32 0, i32 16 , !dbg !116
  store %"struct.ritz_module_1.DirtyFlags" %".8", %"struct.ritz_module_1.DirtyFlags"* %".10", !dbg !116
  %".12" = load %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"node.addr", !dbg !117
  %".13" = call i32 @"render_tree_insert"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.RenderNode" %".12"), !dbg !117
  %".14" = trunc i64 0 to i32 , !dbg !118
  %".15" = trunc i64 0 to i32 , !dbg !118
  %".16" = trunc i64 1 to i32 , !dbg !118
  %".17" = trunc i64 1 to i32 , !dbg !118
  %".18" = insertvalue %"struct.ritz_module_1.DirtyFlags" undef, i32 %".14", 0 , !dbg !118
  %".19" = insertvalue %"struct.ritz_module_1.DirtyFlags" %".18", i32 %".15", 1 , !dbg !118
  %".20" = insertvalue %"struct.ritz_module_1.DirtyFlags" %".19", i32 %".16", 2 , !dbg !118
  %".21" = insertvalue %"struct.ritz_module_1.DirtyFlags" %".20", i32 %".17", 3 , !dbg !118
  %".22" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !119
  %".23" = call i32 @"render_tree_mark_dirty"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.NodeId" %".22", %"struct.ritz_module_1.DirtyFlags" %".21"), !dbg !119
  %".24" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !120
  %"lookup_id.addr" = alloca %"struct.ritz_module_1.NodeId", !dbg !121
  store %"struct.ritz_module_1.NodeId" %".24", %"struct.ritz_module_1.NodeId"* %"lookup_id.addr", !dbg !121
  %".26" = call %"struct.ritz_module_1.RenderNode"* @"render_tree_get"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.NodeId"* %"lookup_id.addr"), !dbg !121
  %".27" = icmp eq %"struct.ritz_module_1.RenderNode"* %".26", null , !dbg !122
  br i1 %".27", label %"if.then", label %"if.end", !dbg !122
if.then:
  %".29" = trunc i64 3 to i32 , !dbg !123
  ret i32 %".29", !dbg !123
if.end:
  %".31" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".26", i32 0, i32 16 , !dbg !124
  %".32" = load %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %".31", !dbg !124
  %".33" = extractvalue %"struct.ritz_module_1.DirtyFlags" %".32", 2 , !dbg !124
  %".34" = sext i32 %".33" to i64 , !dbg !124
  %".35" = icmp eq i64 %".34", 0 , !dbg !124
  br i1 %".35", label %"if.then.1", label %"if.end.1", !dbg !124
if.then.1:
  %".37" = trunc i64 1 to i32 , !dbg !125
  ret i32 %".37", !dbg !125
if.end.1:
  %".39" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".26", i32 0, i32 16 , !dbg !126
  %".40" = load %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %".39", !dbg !126
  %".41" = extractvalue %"struct.ritz_module_1.DirtyFlags" %".40", 3 , !dbg !126
  %".42" = sext i32 %".41" to i64 , !dbg !126
  %".43" = icmp eq i64 %".42", 0 , !dbg !126
  br i1 %".43", label %"if.then.2", label %"if.end.2", !dbg !126
if.then.2:
  %".45" = trunc i64 2 to i32 , !dbg !127
  ret i32 %".45", !dbg !127
if.end.2:
  %".47" = trunc i64 0 to i32 , !dbg !128
  ret i32 %".47", !dbg !128
}

define i32 @"test_render_tree_clear_dirty"() !dbg !26
{
entry:
  %"tree.addr" = alloca %"struct.ritz_module_1.RenderTree", !dbg !129
  %".2" = call %"struct.ritz_module_1.RenderTree" @"render_tree_new"(), !dbg !129
  store %"struct.ritz_module_1.RenderTree" %".2", %"struct.ritz_module_1.RenderTree"* %"tree.addr", !dbg !129
  %".4" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !130
  %".5" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !131
  %".6" = call %"struct.ritz_module_1.RenderNode" @"render_node_new"(%"struct.ritz_module_1.NodeId" %".4", i32 0, %"struct.ritz_module_1.ComputedStyle" %".5"), !dbg !132
  %".7" = call i32 @"render_tree_insert"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.RenderNode" %".6"), !dbg !133
  %".8" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !134
  %".9" = call i32 @"render_tree_clear_dirty"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.NodeId" %".8"), !dbg !134
  %".10" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !135
  %"lookup_id.addr" = alloca %"struct.ritz_module_1.NodeId", !dbg !136
  store %"struct.ritz_module_1.NodeId" %".10", %"struct.ritz_module_1.NodeId"* %"lookup_id.addr", !dbg !136
  %".12" = call %"struct.ritz_module_1.RenderNode"* @"render_tree_get"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.NodeId"* %"lookup_id.addr"), !dbg !136
  %".13" = icmp eq %"struct.ritz_module_1.RenderNode"* %".12", null , !dbg !137
  br i1 %".13", label %"if.then", label %"if.end", !dbg !137
if.then:
  %".15" = trunc i64 2 to i32 , !dbg !138
  ret i32 %".15", !dbg !138
if.end:
  %".17" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".12", i32 0, i32 16 , !dbg !139
  %".18" = load %"struct.ritz_module_1.DirtyFlags", %"struct.ritz_module_1.DirtyFlags"* %".17", !dbg !139
  %".19" = call i32 @"dirty_flags_is_clean"(%"struct.ritz_module_1.DirtyFlags" %".18"), !dbg !139
  %".20" = sext i32 %".19" to i64 , !dbg !139
  %".21" = icmp eq i64 %".20", 0 , !dbg !139
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !139
if.then.1:
  %".23" = trunc i64 1 to i32 , !dbg !140
  ret i32 %".23", !dbg !140
if.end.1:
  %".25" = trunc i64 0 to i32 , !dbg !141
  ret i32 %".25", !dbg !141
}

define linkonce_odr i32 @"vec_push$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", %"struct.ritz_module_1.RenderNode" %"item.arg") !dbg !27
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", metadata !144, metadata !7), !dbg !145
  %"item" = alloca %"struct.ritz_module_1.RenderNode"
  store %"struct.ritz_module_1.RenderNode" %"item.arg", %"struct.ritz_module_1.RenderNode"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderNode"* %"item", metadata !147, metadata !7), !dbg !145
  %".7" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 1 , !dbg !148
  %".8" = load i64, i64* %".7", !dbg !148
  %".9" = add i64 %".8", 1, !dbg !148
  %".10" = call i32 @"vec_ensure_cap$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i64 %".9"), !dbg !148
  %".11" = sext i32 %".10" to i64 , !dbg !148
  %".12" = icmp ne i64 %".11", 0 , !dbg !148
  br i1 %".12", label %"if.then", label %"if.end", !dbg !148
if.then:
  %".14" = sub i64 0, 1, !dbg !149
  %".15" = trunc i64 %".14" to i32 , !dbg !149
  ret i32 %".15", !dbg !149
if.end:
  %".17" = load %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"item", !dbg !150
  %".18" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 0 , !dbg !150
  %".19" = load %"struct.ritz_module_1.RenderNode"*, %"struct.ritz_module_1.RenderNode"** %".18", !dbg !150
  %".20" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 1 , !dbg !150
  %".21" = load i64, i64* %".20", !dbg !150
  %".22" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".19", i64 %".21" , !dbg !150
  store %"struct.ritz_module_1.RenderNode" %".17", %"struct.ritz_module_1.RenderNode"* %".22", !dbg !150
  %".24" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 1 , !dbg !151
  %".25" = load i64, i64* %".24", !dbg !151
  %".26" = add i64 %".25", 1, !dbg !151
  %".27" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 1 , !dbg !151
  store i64 %".26", i64* %".27", !dbg !151
  %".29" = trunc i64 0 to i32 , !dbg !152
  ret i32 %".29", !dbg !152
}

define linkonce_odr %"struct.ritz_module_1.Vec$RenderNode" @"vec_new$RenderNode"() !dbg !28
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$RenderNode", !dbg !153
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", metadata !154, metadata !7), !dbg !155
  %".3" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", !dbg !156
  %".4" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", i32 0, i32 0 , !dbg !156
  %".5" = bitcast i8* null to %"struct.ritz_module_1.RenderNode"* , !dbg !156
  store %"struct.ritz_module_1.RenderNode"* %".5", %"struct.ritz_module_1.RenderNode"** %".4", !dbg !156
  %".7" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", !dbg !157
  %".8" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", i32 0, i32 1 , !dbg !157
  store i64 0, i64* %".8", !dbg !157
  %".10" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", !dbg !158
  %".11" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", i32 0, i32 2 , !dbg !158
  store i64 0, i64* %".11", !dbg !158
  %".13" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", !dbg !159
  ret %"struct.ritz_module_1.Vec$RenderNode" %".13", !dbg !159
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !29
{
entry:
  %"i" = alloca i64, !dbg !167
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !162, metadata !7), !dbg !163
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !165, metadata !7), !dbg !163
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !166, metadata !7), !dbg !163
  %".10" = load i64, i64* %"len", !dbg !167
  store i64 0, i64* %"i", !dbg !167
  br label %"for.cond", !dbg !167
for.cond:
  %".13" = load i64, i64* %"i", !dbg !167
  %".14" = icmp slt i64 %".13", %".10" , !dbg !167
  br i1 %".14", label %"for.body", label %"for.end", !dbg !167
for.body:
  %".16" = load i8*, i8** %"data", !dbg !167
  %".17" = load i64, i64* %"i", !dbg !167
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !167
  %".19" = load i8, i8* %".18", !dbg !167
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !167
  %".21" = sext i32 %".20" to i64 , !dbg !167
  %".22" = icmp ne i64 %".21", 0 , !dbg !167
  br i1 %".22", label %"if.then", label %"if.end", !dbg !167
for.incr:
  %".28" = load i64, i64* %"i", !dbg !168
  %".29" = add i64 %".28", 1, !dbg !168
  store i64 %".29", i64* %"i", !dbg !168
  br label %"for.cond", !dbg !168
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !169
  ret i32 %".32", !dbg !169
if.then:
  %".24" = sub i64 0, 1, !dbg !168
  %".25" = trunc i64 %".24" to i32 , !dbg !168
  ret i32 %".25", !dbg !168
if.end:
  br label %"for.incr", !dbg !168
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !30
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !172, metadata !7), !dbg !173
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !175, metadata !7), !dbg !173
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !176
  %".8" = load i64, i64* %".7", !dbg !176
  %".9" = add i64 %".8", 1, !dbg !176
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !176
  %".11" = sext i32 %".10" to i64 , !dbg !176
  %".12" = icmp ne i64 %".11", 0 , !dbg !176
  br i1 %".12", label %"if.then", label %"if.end", !dbg !176
if.then:
  %".14" = sub i64 0, 1, !dbg !177
  %".15" = trunc i64 %".14" to i32 , !dbg !177
  ret i32 %".15", !dbg !177
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !178
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !178
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !178
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !178
  %".21" = load i64, i64* %".20", !dbg !178
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !178
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !178
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !179
  %".25" = load i64, i64* %".24", !dbg !179
  %".26" = add i64 %".25", 1, !dbg !179
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !179
  store i64 %".26", i64* %".27", !dbg !179
  %".29" = trunc i64 0 to i32 , !dbg !180
  ret i32 %".29", !dbg !180
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !31
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !186
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !181, metadata !7), !dbg !182
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !183, metadata !7), !dbg !182
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !184
  %".8" = load i64, i64* %".7", !dbg !184
  %".9" = load i64, i64* %"needed", !dbg !184
  %".10" = icmp sge i64 %".8", %".9" , !dbg !184
  br i1 %".10", label %"if.then", label %"if.end", !dbg !184
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !185
  ret i32 %".12", !dbg !185
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !186
  %".15" = load i64, i64* %".14", !dbg !186
  store i64 %".15", i64* %"new_cap.addr", !dbg !186
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !187, metadata !7), !dbg !188
  %".18" = load i64, i64* %"new_cap.addr", !dbg !189
  %".19" = icmp eq i64 %".18", 0 , !dbg !189
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !189
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !190
  br label %"if.end.1", !dbg !190
if.end.1:
  br label %"while.cond", !dbg !191
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !191
  %".25" = load i64, i64* %"needed", !dbg !191
  %".26" = icmp slt i64 %".24", %".25" , !dbg !191
  br i1 %".26", label %"while.body", label %"while.end", !dbg !191
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !192
  %".29" = mul i64 %".28", 2, !dbg !192
  store i64 %".29", i64* %"new_cap.addr", !dbg !192
  br label %"while.cond", !dbg !192
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !193
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !193
  ret i32 %".33", !dbg !193
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !32
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !194, metadata !7), !dbg !195
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !196, metadata !7), !dbg !195
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !197
  %".8" = load i64, i64* %".7", !dbg !197
  %".9" = add i64 %".8", 1, !dbg !197
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !197
  %".11" = sext i32 %".10" to i64 , !dbg !197
  %".12" = icmp ne i64 %".11", 0 , !dbg !197
  br i1 %".12", label %"if.then", label %"if.end", !dbg !197
if.then:
  %".14" = sub i64 0, 1, !dbg !198
  %".15" = trunc i64 %".14" to i32 , !dbg !198
  ret i32 %".15", !dbg !198
if.end:
  %".17" = load i8, i8* %"item", !dbg !199
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !199
  %".19" = load i8*, i8** %".18", !dbg !199
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !199
  %".21" = load i64, i64* %".20", !dbg !199
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !199
  store i8 %".17", i8* %".22", !dbg !199
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !200
  %".25" = load i64, i64* %".24", !dbg !200
  %".26" = add i64 %".25", 1, !dbg !200
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !200
  store i64 %".26", i64* %".27", !dbg !200
  %".29" = trunc i64 0 to i32 , !dbg !201
  ret i32 %".29", !dbg !201
}

define linkonce_odr i32 @"vec_ensure_cap$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i64 %"needed.arg") !dbg !33
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !207
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", metadata !202, metadata !7), !dbg !203
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !204, metadata !7), !dbg !203
  %".7" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 2 , !dbg !205
  %".8" = load i64, i64* %".7", !dbg !205
  %".9" = load i64, i64* %"needed", !dbg !205
  %".10" = icmp sge i64 %".8", %".9" , !dbg !205
  br i1 %".10", label %"if.then", label %"if.end", !dbg !205
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !206
  ret i32 %".12", !dbg !206
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 2 , !dbg !207
  %".15" = load i64, i64* %".14", !dbg !207
  store i64 %".15", i64* %"new_cap.addr", !dbg !207
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !208, metadata !7), !dbg !209
  %".18" = load i64, i64* %"new_cap.addr", !dbg !210
  %".19" = icmp eq i64 %".18", 0 , !dbg !210
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !210
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !211
  br label %"if.end.1", !dbg !211
if.end.1:
  br label %"while.cond", !dbg !212
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !212
  %".25" = load i64, i64* %"needed", !dbg !212
  %".26" = icmp slt i64 %".24", %".25" , !dbg !212
  br i1 %".26", label %"while.body", label %"while.end", !dbg !212
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !213
  %".29" = mul i64 %".28", 2, !dbg !213
  store i64 %".29", i64* %"new_cap.addr", !dbg !213
  br label %"while.cond", !dbg !213
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !214
  %".33" = call i32 @"vec_grow$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i64 %".32"), !dbg !214
  ret i32 %".33", !dbg !214
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !34
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !215, metadata !7), !dbg !216
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !217, metadata !7), !dbg !216
  %".7" = load i64, i64* %"new_cap", !dbg !218
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !218
  %".9" = load i64, i64* %".8", !dbg !218
  %".10" = icmp sle i64 %".7", %".9" , !dbg !218
  br i1 %".10", label %"if.then", label %"if.end", !dbg !218
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !219
  ret i32 %".12", !dbg !219
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !220
  %".15" = mul i64 %".14", 1, !dbg !220
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !221
  %".17" = load i8*, i8** %".16", !dbg !221
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !221
  %".19" = icmp eq i8* %".18", null , !dbg !222
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !222
if.then.1:
  %".21" = sub i64 0, 1, !dbg !223
  %".22" = trunc i64 %".21" to i32 , !dbg !223
  ret i32 %".22", !dbg !223
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !224
  store i8* %".18", i8** %".24", !dbg !224
  %".26" = load i64, i64* %"new_cap", !dbg !225
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !225
  store i64 %".26", i64* %".27", !dbg !225
  %".29" = trunc i64 0 to i32 , !dbg !226
  ret i32 %".29", !dbg !226
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !35
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !232
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !227, metadata !7), !dbg !228
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !229, metadata !7), !dbg !228
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !230
  %".8" = load i64, i64* %".7", !dbg !230
  %".9" = load i64, i64* %"needed", !dbg !230
  %".10" = icmp sge i64 %".8", %".9" , !dbg !230
  br i1 %".10", label %"if.then", label %"if.end", !dbg !230
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !231
  ret i32 %".12", !dbg !231
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !232
  %".15" = load i64, i64* %".14", !dbg !232
  store i64 %".15", i64* %"new_cap.addr", !dbg !232
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !233, metadata !7), !dbg !234
  %".18" = load i64, i64* %"new_cap.addr", !dbg !235
  %".19" = icmp eq i64 %".18", 0 , !dbg !235
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !235
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !236
  br label %"if.end.1", !dbg !236
if.end.1:
  br label %"while.cond", !dbg !237
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !237
  %".25" = load i64, i64* %"needed", !dbg !237
  %".26" = icmp slt i64 %".24", %".25" , !dbg !237
  br i1 %".26", label %"while.body", label %"while.end", !dbg !237
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !238
  %".29" = mul i64 %".28", 2, !dbg !238
  store i64 %".29", i64* %"new_cap.addr", !dbg !238
  br label %"while.cond", !dbg !238
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !239
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !239
  ret i32 %".33", !dbg !239
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !36
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !240, metadata !7), !dbg !241
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !242, metadata !7), !dbg !241
  %".7" = load i64, i64* %"new_cap", !dbg !243
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !243
  %".9" = load i64, i64* %".8", !dbg !243
  %".10" = icmp sle i64 %".7", %".9" , !dbg !243
  br i1 %".10", label %"if.then", label %"if.end", !dbg !243
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !244
  ret i32 %".12", !dbg !244
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !245
  %".15" = mul i64 %".14", 16, !dbg !245
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !246
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !246
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !246
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !246
  %".20" = icmp eq i8* %".19", null , !dbg !247
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !247
if.then.1:
  %".22" = sub i64 0, 1, !dbg !248
  %".23" = trunc i64 %".22" to i32 , !dbg !248
  ret i32 %".23", !dbg !248
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !249
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !249
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !249
  %".28" = load i64, i64* %"new_cap", !dbg !250
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !250
  store i64 %".28", i64* %".29", !dbg !250
  %".31" = trunc i64 0 to i32 , !dbg !251
  ret i32 %".31", !dbg !251
}

define linkonce_odr i32 @"vec_grow$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i64 %"new_cap.arg") !dbg !37
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", metadata !252, metadata !7), !dbg !253
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !254, metadata !7), !dbg !253
  %".7" = load i64, i64* %"new_cap", !dbg !255
  %".8" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 2 , !dbg !255
  %".9" = load i64, i64* %".8", !dbg !255
  %".10" = icmp sle i64 %".7", %".9" , !dbg !255
  br i1 %".10", label %"if.then", label %"if.end", !dbg !255
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !256
  ret i32 %".12", !dbg !256
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !257
  %".15" = mul i64 %".14", 656, !dbg !257
  %".16" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 0 , !dbg !258
  %".17" = load %"struct.ritz_module_1.RenderNode"*, %"struct.ritz_module_1.RenderNode"** %".16", !dbg !258
  %".18" = bitcast %"struct.ritz_module_1.RenderNode"* %".17" to i8* , !dbg !258
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !258
  %".20" = icmp eq i8* %".19", null , !dbg !259
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !259
if.then.1:
  %".22" = sub i64 0, 1, !dbg !260
  %".23" = trunc i64 %".22" to i32 , !dbg !260
  ret i32 %".23", !dbg !260
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.RenderNode"* , !dbg !261
  %".26" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 0 , !dbg !261
  store %"struct.ritz_module_1.RenderNode"* %".25", %"struct.ritz_module_1.RenderNode"** %".26", !dbg !261
  %".28" = load i64, i64* %"new_cap", !dbg !262
  %".29" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 2 , !dbg !262
  store i64 %".28", i64* %".29", !dbg !262
  %".31" = trunc i64 0 to i32 , !dbg !263
  ret i32 %".31", !dbg !263
}

@".str.0" = private constant [6 x i8] c"Hello\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/tests", filename: "test_render_tree.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 12, name: "test_render_node_new", scopeLine: 12, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 27, name: "test_render_node_new_text", scopeLine: 27, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 42, name: "test_render_tree_new", scopeLine: 42, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 51, name: "test_render_tree_insert_and_get", scopeLine: 51, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 69, name: "test_render_tree_set_root", scopeLine: 69, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 87, name: "test_render_tree_count", scopeLine: 87, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 107, name: "test_dirty_flags_none", scopeLine: 107, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 114, name: "test_dirty_flags_all", scopeLine: 114, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 132, name: "test_render_tree_mark_dirty", scopeLine: 132, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 156, name: "test_render_tree_clear_dirty", scopeLine: 156, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$RenderNode", scopeLine: 210, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$RenderNode", scopeLine: 116, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$RenderNode", scopeLine: 193, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$RenderNode", scopeLine: 179, type: !4, unit: !1)
!38 = !DILocation(column: 5, line: 13, scope: !17)
!39 = !DILocation(column: 5, line: 14, scope: !17)
!40 = !DILocation(column: 5, line: 15, scope: !17)
!41 = !DILocation(column: 5, line: 17, scope: !17)
!42 = !DILocation(column: 9, line: 18, scope: !17)
!43 = !DILocation(column: 5, line: 19, scope: !17)
!44 = !DILocation(column: 9, line: 20, scope: !17)
!45 = !DILocation(column: 5, line: 22, scope: !17)
!46 = !DILocation(column: 9, line: 23, scope: !17)
!47 = !DILocation(column: 5, line: 24, scope: !17)
!48 = !DILocation(column: 5, line: 28, scope: !18)
!49 = !DILocation(column: 5, line: 29, scope: !18)
!50 = !DILocation(column: 5, line: 30, scope: !18)
!51 = !DILocation(column: 5, line: 31, scope: !18)
!52 = !DILocation(column: 5, line: 33, scope: !18)
!53 = !DILocation(column: 9, line: 34, scope: !18)
!54 = !DILocation(column: 5, line: 35, scope: !18)
!55 = !DILocation(column: 5, line: 43, scope: !19)
!56 = !DILocation(column: 5, line: 44, scope: !19)
!57 = !DILocation(column: 9, line: 45, scope: !19)
!58 = !DILocation(column: 5, line: 46, scope: !19)
!59 = !DILocation(column: 9, line: 47, scope: !19)
!60 = !DILocation(column: 5, line: 48, scope: !19)
!61 = !DILocation(column: 5, line: 52, scope: !20)
!62 = !DILocation(column: 5, line: 53, scope: !20)
!63 = !DILocation(column: 5, line: 54, scope: !20)
!64 = !DILocation(column: 5, line: 55, scope: !20)
!65 = !DILocation(column: 5, line: 57, scope: !20)
!66 = !DILocation(column: 5, line: 60, scope: !20)
!67 = !DILocation(column: 5, line: 61, scope: !20)
!68 = !DILocation(column: 5, line: 62, scope: !20)
!69 = !DILocation(column: 9, line: 63, scope: !20)
!70 = !DILocation(column: 5, line: 64, scope: !20)
!71 = !DILocation(column: 9, line: 65, scope: !20)
!72 = !DILocation(column: 5, line: 66, scope: !20)
!73 = !DILocation(column: 5, line: 70, scope: !21)
!74 = !DILocation(column: 5, line: 71, scope: !21)
!75 = !DILocation(column: 5, line: 72, scope: !21)
!76 = !DILocation(column: 5, line: 73, scope: !21)
!77 = !DILocation(column: 5, line: 75, scope: !21)
!78 = !DILocation(column: 5, line: 77, scope: !21)
!79 = !DILocation(column: 5, line: 79, scope: !21)
!80 = !DILocation(column: 5, line: 80, scope: !21)
!81 = !DILocation(column: 9, line: 81, scope: !21)
!82 = !DILocation(column: 5, line: 82, scope: !21)
!83 = !DILocation(column: 9, line: 83, scope: !21)
!84 = !DILocation(column: 5, line: 84, scope: !21)
!85 = !DILocation(column: 5, line: 88, scope: !22)
!86 = !DILocation(column: 5, line: 90, scope: !22)
!87 = !DILocation(column: 5, line: 91, scope: !22)
!88 = !DILocation(column: 5, line: 92, scope: !22)
!89 = !DILocation(column: 5, line: 94, scope: !22)
!90 = !DILocation(column: 5, line: 95, scope: !22)
!91 = !DILocation(column: 5, line: 96, scope: !22)
!92 = !DILocation(column: 5, line: 98, scope: !22)
!93 = !DILocation(column: 9, line: 99, scope: !22)
!94 = !DILocation(column: 5, line: 100, scope: !22)
!95 = !DILocation(column: 5, line: 108, scope: !23)
!96 = !DILocation(column: 5, line: 109, scope: !23)
!97 = !DILocation(column: 9, line: 110, scope: !23)
!98 = !DILocation(column: 5, line: 111, scope: !23)
!99 = !DILocation(column: 5, line: 115, scope: !24)
!100 = !DILocation(column: 5, line: 117, scope: !24)
!101 = !DILocation(column: 9, line: 118, scope: !24)
!102 = !DILocation(column: 5, line: 119, scope: !24)
!103 = !DILocation(column: 9, line: 120, scope: !24)
!104 = !DILocation(column: 5, line: 121, scope: !24)
!105 = !DILocation(column: 9, line: 122, scope: !24)
!106 = !DILocation(column: 5, line: 123, scope: !24)
!107 = !DILocation(column: 9, line: 124, scope: !24)
!108 = !DILocation(column: 5, line: 126, scope: !24)
!109 = !DILocation(column: 5, line: 127, scope: !24)
!110 = !DILocation(column: 9, line: 128, scope: !24)
!111 = !DILocation(column: 5, line: 129, scope: !24)
!112 = !DILocation(column: 5, line: 133, scope: !25)
!113 = !DILocation(column: 5, line: 134, scope: !25)
!114 = !DILocation(column: 5, line: 135, scope: !25)
!115 = !DILocation(column: 5, line: 136, scope: !25)
!116 = !DILocation(column: 5, line: 137, scope: !25)
!117 = !DILocation(column: 5, line: 139, scope: !25)
!118 = !DILocation(column: 5, line: 142, scope: !25)
!119 = !DILocation(column: 5, line: 143, scope: !25)
!120 = !DILocation(column: 5, line: 145, scope: !25)
!121 = !DILocation(column: 5, line: 146, scope: !25)
!122 = !DILocation(column: 5, line: 147, scope: !25)
!123 = !DILocation(column: 9, line: 148, scope: !25)
!124 = !DILocation(column: 5, line: 149, scope: !25)
!125 = !DILocation(column: 9, line: 150, scope: !25)
!126 = !DILocation(column: 5, line: 151, scope: !25)
!127 = !DILocation(column: 9, line: 152, scope: !25)
!128 = !DILocation(column: 5, line: 153, scope: !25)
!129 = !DILocation(column: 5, line: 157, scope: !26)
!130 = !DILocation(column: 5, line: 158, scope: !26)
!131 = !DILocation(column: 5, line: 159, scope: !26)
!132 = !DILocation(column: 5, line: 160, scope: !26)
!133 = !DILocation(column: 5, line: 162, scope: !26)
!134 = !DILocation(column: 5, line: 163, scope: !26)
!135 = !DILocation(column: 5, line: 165, scope: !26)
!136 = !DILocation(column: 5, line: 166, scope: !26)
!137 = !DILocation(column: 5, line: 167, scope: !26)
!138 = !DILocation(column: 9, line: 168, scope: !26)
!139 = !DILocation(column: 5, line: 169, scope: !26)
!140 = !DILocation(column: 9, line: 170, scope: !26)
!141 = !DILocation(column: 5, line: 171, scope: !26)
!142 = !DICompositeType(align: 64, file: !0, name: "Vec$RenderNode", size: 192, tag: DW_TAG_structure_type)
!143 = !DIDerivedType(baseType: !142, size: 64, tag: DW_TAG_reference_type)
!144 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !27, type: !143)
!145 = !DILocation(column: 1, line: 210, scope: !27)
!146 = !DICompositeType(align: 64, file: !0, name: "RenderNode", size: 5248, tag: DW_TAG_structure_type)
!147 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !27, type: !146)
!148 = !DILocation(column: 5, line: 211, scope: !27)
!149 = !DILocation(column: 9, line: 212, scope: !27)
!150 = !DILocation(column: 5, line: 213, scope: !27)
!151 = !DILocation(column: 5, line: 214, scope: !27)
!152 = !DILocation(column: 5, line: 215, scope: !27)
!153 = !DILocation(column: 5, line: 117, scope: !28)
!154 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !28, type: !142)
!155 = !DILocation(column: 1, line: 117, scope: !28)
!156 = !DILocation(column: 5, line: 118, scope: !28)
!157 = !DILocation(column: 5, line: 119, scope: !28)
!158 = !DILocation(column: 5, line: 120, scope: !28)
!159 = !DILocation(column: 5, line: 121, scope: !28)
!160 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!161 = !DIDerivedType(baseType: !160, size: 64, tag: DW_TAG_reference_type)
!162 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !29, type: !161)
!163 = !DILocation(column: 1, line: 288, scope: !29)
!164 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!165 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !29, type: !164)
!166 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !29, type: !11)
!167 = !DILocation(column: 5, line: 289, scope: !29)
!168 = !DILocation(column: 13, line: 291, scope: !29)
!169 = !DILocation(column: 5, line: 292, scope: !29)
!170 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!171 = !DIDerivedType(baseType: !170, size: 64, tag: DW_TAG_reference_type)
!172 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !30, type: !171)
!173 = !DILocation(column: 1, line: 210, scope: !30)
!174 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!175 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !30, type: !174)
!176 = !DILocation(column: 5, line: 211, scope: !30)
!177 = !DILocation(column: 9, line: 212, scope: !30)
!178 = !DILocation(column: 5, line: 213, scope: !30)
!179 = !DILocation(column: 5, line: 214, scope: !30)
!180 = !DILocation(column: 5, line: 215, scope: !30)
!181 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !31, type: !161)
!182 = !DILocation(column: 1, line: 193, scope: !31)
!183 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !31, type: !11)
!184 = !DILocation(column: 5, line: 194, scope: !31)
!185 = !DILocation(column: 9, line: 195, scope: !31)
!186 = !DILocation(column: 5, line: 197, scope: !31)
!187 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !31, type: !11)
!188 = !DILocation(column: 1, line: 197, scope: !31)
!189 = !DILocation(column: 5, line: 198, scope: !31)
!190 = !DILocation(column: 9, line: 199, scope: !31)
!191 = !DILocation(column: 5, line: 200, scope: !31)
!192 = !DILocation(column: 9, line: 201, scope: !31)
!193 = !DILocation(column: 5, line: 203, scope: !31)
!194 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !32, type: !161)
!195 = !DILocation(column: 1, line: 210, scope: !32)
!196 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !32, type: !12)
!197 = !DILocation(column: 5, line: 211, scope: !32)
!198 = !DILocation(column: 9, line: 212, scope: !32)
!199 = !DILocation(column: 5, line: 213, scope: !32)
!200 = !DILocation(column: 5, line: 214, scope: !32)
!201 = !DILocation(column: 5, line: 215, scope: !32)
!202 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !33, type: !143)
!203 = !DILocation(column: 1, line: 193, scope: !33)
!204 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !33, type: !11)
!205 = !DILocation(column: 5, line: 194, scope: !33)
!206 = !DILocation(column: 9, line: 195, scope: !33)
!207 = !DILocation(column: 5, line: 197, scope: !33)
!208 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !33, type: !11)
!209 = !DILocation(column: 1, line: 197, scope: !33)
!210 = !DILocation(column: 5, line: 198, scope: !33)
!211 = !DILocation(column: 9, line: 199, scope: !33)
!212 = !DILocation(column: 5, line: 200, scope: !33)
!213 = !DILocation(column: 9, line: 201, scope: !33)
!214 = !DILocation(column: 5, line: 203, scope: !33)
!215 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !34, type: !161)
!216 = !DILocation(column: 1, line: 179, scope: !34)
!217 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !34, type: !11)
!218 = !DILocation(column: 5, line: 180, scope: !34)
!219 = !DILocation(column: 9, line: 181, scope: !34)
!220 = !DILocation(column: 5, line: 183, scope: !34)
!221 = !DILocation(column: 5, line: 184, scope: !34)
!222 = !DILocation(column: 5, line: 185, scope: !34)
!223 = !DILocation(column: 9, line: 186, scope: !34)
!224 = !DILocation(column: 5, line: 188, scope: !34)
!225 = !DILocation(column: 5, line: 189, scope: !34)
!226 = !DILocation(column: 5, line: 190, scope: !34)
!227 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !35, type: !171)
!228 = !DILocation(column: 1, line: 193, scope: !35)
!229 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !35, type: !11)
!230 = !DILocation(column: 5, line: 194, scope: !35)
!231 = !DILocation(column: 9, line: 195, scope: !35)
!232 = !DILocation(column: 5, line: 197, scope: !35)
!233 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !35, type: !11)
!234 = !DILocation(column: 1, line: 197, scope: !35)
!235 = !DILocation(column: 5, line: 198, scope: !35)
!236 = !DILocation(column: 9, line: 199, scope: !35)
!237 = !DILocation(column: 5, line: 200, scope: !35)
!238 = !DILocation(column: 9, line: 201, scope: !35)
!239 = !DILocation(column: 5, line: 203, scope: !35)
!240 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !36, type: !171)
!241 = !DILocation(column: 1, line: 179, scope: !36)
!242 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !36, type: !11)
!243 = !DILocation(column: 5, line: 180, scope: !36)
!244 = !DILocation(column: 9, line: 181, scope: !36)
!245 = !DILocation(column: 5, line: 183, scope: !36)
!246 = !DILocation(column: 5, line: 184, scope: !36)
!247 = !DILocation(column: 5, line: 185, scope: !36)
!248 = !DILocation(column: 9, line: 186, scope: !36)
!249 = !DILocation(column: 5, line: 188, scope: !36)
!250 = !DILocation(column: 5, line: 189, scope: !36)
!251 = !DILocation(column: 5, line: 190, scope: !36)
!252 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !37, type: !143)
!253 = !DILocation(column: 1, line: 179, scope: !37)
!254 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !37, type: !11)
!255 = !DILocation(column: 5, line: 180, scope: !37)
!256 = !DILocation(column: 9, line: 181, scope: !37)
!257 = !DILocation(column: 5, line: 183, scope: !37)
!258 = !DILocation(column: 5, line: 184, scope: !37)
!259 = !DILocation(column: 5, line: 185, scope: !37)
!260 = !DILocation(column: 9, line: 186, scope: !37)
!261 = !DILocation(column: 5, line: 188, scope: !37)
!262 = !DILocation(column: 5, line: 189, scope: !37)
!263 = !DILocation(column: 5, line: 190, scope: !37)