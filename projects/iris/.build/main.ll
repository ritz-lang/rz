; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Vec$Layer" = type {%"struct.ritz_module_1.Layer"*, i64, i64}
%"struct.ritz_module_1.Vec$u8" = type {i8*, i64, i64}
%"struct.ritz_module_1.Vec$RenderNode" = type {%"struct.ritz_module_1.RenderNode"*, i64, i64}
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
%"struct.ritz_module_1.StrView" = type {i8*, i64}
%"struct.ritz_module_1.String" = type {%"struct.ritz_module_1.Vec$u8"}
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
%"struct.ritz_module_1.HashMapEntryI64" = type {i64, i64, i32}
%"struct.ritz_module_1.HashMapI64" = type {%"struct.ritz_module_1.HashMapEntryI64"*, i64, i64, i64}
%"struct.ritz_module_1.DirtyFlags" = type {i32, i32, i32, i32}
%"struct.ritz_module_1.LayoutResult" = type {i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32, i32}
%"struct.ritz_module_1.RenderNode" = type {%"struct.ritz_module_1.NodeId", i32, i32, i8*, i32, i32, i32, i32, %"struct.ritz_module_1.ComputedStyle", %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId", %"struct.ritz_module_1.NodeId", i32, %"struct.ritz_module_1.LayoutResult", %"struct.ritz_module_1.DirtyFlags", i64}
%"struct.ritz_module_1.RenderTree" = type {%"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.NodeId"}
%"struct.ritz_module_1.LayoutConstraints" = type {double, double, double, double, double, double, i32, i32}
%"struct.ritz_module_1.BoxDimensions" = type {double, double, double, double, double, double, double, double, double, double, double, double, double, double}
%"struct.ritz_module_1.LayerId" = type {i64}
%"struct.ritz_module_1.LayerRect" = type {i32, i32, i32, i32}
%"struct.ritz_module_1.LayerPoint" = type {i32, i32}
%"struct.ritz_module_1.Layer" = type {%"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.NodeId", i32, %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerId", %"struct.ritz_module_1.LayerRect", %"struct.ritz_module_1.Transform", double, i32, %"struct.ritz_module_1.LayerPoint", %"struct.ritz_module_1.LayerRect", i32, i32, i64}
%"struct.ritz_module_1.LayerTree" = type {%"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.LayerId", i64}
declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

@"BLOCK_SIZES" = internal constant [9 x i64] [i64 32, i64 48, i64 80, i64 144, i64 272, i64 528, i64 1040, i64 2064, i64 0]
@"g_alloc" = internal global %"struct.ritz_module_1.GlobalAlloc" zeroinitializer
declare i64 @"StrView_len"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"StrView_is_empty"(%"struct.ritz_module_1.StrView"* %".1")

declare i8 @"StrView_get"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2")

declare i8* @"StrView_as_ptr"(%"struct.ritz_module_1.StrView"* %".1")

declare %"struct.ritz_module_1.StrView" @"StrView_slice"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2", i64 %".3")

declare %"struct.ritz_module_1.StrView" @"StrView_take"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2")

declare %"struct.ritz_module_1.StrView" @"StrView_skip"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2")

declare i32 @"StrView_starts_with"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i32 @"StrView_ends_with"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i32 @"StrView_contains"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i64 @"StrView_find"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i64 @"StrView_find_byte"(%"struct.ritz_module_1.StrView"* %".1", i8 %".2")

declare %"struct.ritz_module_1.StrView" @"StrView_trim"(%"struct.ritz_module_1.StrView"* %".1")

declare %"struct.ritz_module_1.StrView" @"StrView_trim_start"(%"struct.ritz_module_1.StrView"* %".1")

declare %"struct.ritz_module_1.StrView" @"StrView_trim_end"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"StrView_eq"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i32 @"StrView_eq_cstr"(%"struct.ritz_module_1.StrView"* %".1", i8* %".2")

declare i8* @"StrView_to_cstr"(%"struct.ritz_module_1.StrView"* %".1")

declare i8* @"StrView_as_cstr_unchecked"(%"struct.ritz_module_1.StrView"* %".1")

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

declare %"struct.ritz_module_1.String" @"string_new"()

declare %"struct.ritz_module_1.String" @"string_with_cap"(i64 %".1")

declare %"struct.ritz_module_1.String" @"string_from"(%"struct.ritz_module_1.StrView" %".1")

declare %"struct.ritz_module_1.String" @"string_from_cstr"(i8* %".1")

declare %"struct.ritz_module_1.String" @"string_from_bytes"(i8* %".1", i64 %".2")

declare %"struct.ritz_module_1.String" @"string_from_strview"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"string_drop"(%"struct.ritz_module_1.String"* %".1")

declare i64 @"string_len"(%"struct.ritz_module_1.String"* %".1")

declare i64 @"string_cap"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"string_is_empty"(%"struct.ritz_module_1.String"* %".1")

declare i8* @"string_as_ptr"(%"struct.ritz_module_1.String"* %".1")

declare i8 @"string_get"(%"struct.ritz_module_1.String"* %".1", i64 %".2")

declare i32 @"string_push"(%"struct.ritz_module_1.String"* %".1", i8 %".2")

declare i32 @"string_push_str"(%"struct.ritz_module_1.String"* %".1", i8* %".2")

declare i32 @"string_push_string"(%"struct.ritz_module_1.String"* %".1", %"struct.ritz_module_1.String"* %".2")

declare i32 @"string_push_bytes"(%"struct.ritz_module_1.String"* %".1", i8* %".2", i64 %".3")

declare i32 @"string_clear"(%"struct.ritz_module_1.String"* %".1")

declare i8 @"string_pop"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"string_eq"(%"struct.ritz_module_1.String"* %".1", %"struct.ritz_module_1.String"* %".2")

declare i64 @"string_hash"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"string_eq_cstr"(%"struct.ritz_module_1.String"* %".1", i8* %".2")

declare %"struct.ritz_module_1.String" @"string_clone"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"string_starts_with_string"(%"struct.ritz_module_1.String"* %".1", %"struct.ritz_module_1.String"* %".2")

declare i32 @"string_ends_with_string"(%"struct.ritz_module_1.String"* %".1", %"struct.ritz_module_1.String"* %".2")

declare i32 @"string_contains_string"(%"struct.ritz_module_1.String"* %".1", %"struct.ritz_module_1.String"* %".2")

declare i64 @"string_find"(%"struct.ritz_module_1.String"* %".1", %"struct.ritz_module_1.String"* %".2")

declare %"struct.ritz_module_1.String" @"string_slice"(%"struct.ritz_module_1.String"* %".1", i64 %".2", i64 %".3")

declare i8 @"string_char_at"(%"struct.ritz_module_1.String"* %".1", i64 %".2")

declare i32 @"string_set_char"(%"struct.ritz_module_1.String"* %".1", i64 %".2", i8 %".3")

declare i32 @"string_starts_with"(%"struct.ritz_module_1.String"* %".1", i8* %".2")

declare i32 @"string_ends_with"(%"struct.ritz_module_1.String"* %".1", i8* %".2")

declare i32 @"string_contains"(%"struct.ritz_module_1.String"* %".1", i8* %".2")

declare %"struct.ritz_module_1.String" @"string_from_i64"(i64 %".1")

declare i32 @"string_push_i64"(%"struct.ritz_module_1.String"* %".1", i64 %".2")

declare %"struct.ritz_module_1.String" @"string_from_hex"(i64 %".1")

declare %"struct.ritz_module_1.StrView" @"strview_empty"()

declare %"struct.ritz_module_1.StrView" @"strview_from_ptr"(i8* %".1", i64 %".2")

declare %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".1")

declare i64 @"strview_len"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"strview_is_empty"(%"struct.ritz_module_1.StrView"* %".1")

declare i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2")

declare i8* @"strview_as_ptr"(%"struct.ritz_module_1.StrView"* %".1")

declare i8* @"strview_to_cstr"(%"struct.ritz_module_1.StrView"* %".1")

declare i8* @"strview_as_cstr_unchecked"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i32 @"strview_eq_cstr"(%"struct.ritz_module_1.StrView"* %".1", i8* %".2")

declare %"struct.ritz_module_1.StrView" @"strview_slice"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2", i64 %".3")

declare %"struct.ritz_module_1.StrView" @"strview_take"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2")

declare %"struct.ritz_module_1.StrView" @"strview_skip"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2")

declare i32 @"strview_starts_with"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i32 @"strview_starts_with_cstr"(%"struct.ritz_module_1.StrView"* %".1", i8* %".2")

declare i32 @"strview_ends_with"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i32 @"strview_contains"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i64 @"strview_find"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i64 @"strview_find_byte"(%"struct.ritz_module_1.StrView"* %".1", i8 %".2")

declare i32 @"strview_split_once"(%"struct.ritz_module_1.StrView"* %".1", i8 %".2", %"struct.ritz_module_1.StrView"* %".3", %"struct.ritz_module_1.StrView"* %".4")

declare %"struct.ritz_module_1.StrView" @"strview_trim_start"(%"struct.ritz_module_1.StrView"* %".1")

declare %"struct.ritz_module_1.StrView" @"strview_trim_end"(%"struct.ritz_module_1.StrView"* %".1")

declare %"struct.ritz_module_1.StrView" @"strview_trim"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"prints"(%"struct.ritz_module_1.StrView" %".1")

declare i32 @"eprints"(%"struct.ritz_module_1.StrView" %".1")

declare i32 @"prints_cstr"(i8* %".1")

declare i32 @"eprints_cstr"(i8* %".1")

declare i32 @"print_char"(i8 %".1")

declare i32 @"eprint_char"(i8 %".1")

declare i32 @"print_int"(i64 %".1")

declare i32 @"eprint_int"(i64 %".1")

declare i32 @"print_hex"(i64 %".1")

declare i32 @"print_size_human"(i64 %".1")

declare i32 @"println"(%"struct.ritz_module_1.StrView" %".1")

declare i32 @"eprintln"(%"struct.ritz_module_1.StrView" %".1")

declare i32 @"newline"()

declare i32 @"print_string"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"eprint_string"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"println_string"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"eprintln_string"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"print_i64"(i64 %".1")

declare i32 @"println_i64"(i64 %".1")

declare i32 @"eprint_i64"(i64 %".1")

declare i32 @"eprintln_i64"(i64 %".1")

declare i32 @"print_hex64"(i64 %".1")

declare i32 @"println_hex64"(i64 %".1")

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

declare %"struct.ritz_module_1.LayerId" @"layer_id_new"(i64 %".1")

declare %"struct.ritz_module_1.LayerId" @"layer_id_invalid"()

declare i32 @"layer_id_is_valid"(%"struct.ritz_module_1.LayerId"* %".1")

declare i32 @"layer_id_eq"(%"struct.ritz_module_1.LayerId"* %".1", %"struct.ritz_module_1.LayerId"* %".2")

declare %"struct.ritz_module_1.LayerRect" @"layer_rect_new"(i32 %".1", i32 %".2", i32 %".3", i32 %".4")

declare %"struct.ritz_module_1.LayerRect" @"layer_rect_zero"()

declare %"struct.ritz_module_1.LayerPoint" @"layer_point_new"(i32 %".1", i32 %".2")

declare %"struct.ritz_module_1.LayerPoint" @"layer_point_zero"()

declare %"struct.ritz_module_1.Layer" @"layer_new"(%"struct.ritz_module_1.LayerId" %".1", %"struct.ritz_module_1.NodeId" %".2", i32 %".3")

declare i32 @"layer_is_scrollable"(%"struct.ritz_module_1.Layer"* %".1")

declare i32 @"layer_has_transform"(%"struct.ritz_module_1.Layer"* %".1")

declare i32 @"layer_is_opaque"(%"struct.ritz_module_1.Layer"* %".1")

declare %"struct.ritz_module_1.LayerTree" @"layer_tree_new"()

declare %"struct.ritz_module_1.LayerId" @"layer_tree_create_root"(%"struct.ritz_module_1.LayerTree"* %".1", %"struct.ritz_module_1.NodeId" %".2", %"struct.ritz_module_1.LayerRect" %".3")

declare %"struct.ritz_module_1.LayerId" @"layer_tree_create"(%"struct.ritz_module_1.LayerTree"* %".1", %"struct.ritz_module_1.NodeId" %".2", i32 %".3")

declare %"struct.ritz_module_1.Layer"* @"layer_tree_get"(%"struct.ritz_module_1.LayerTree"* %".1", %"struct.ritz_module_1.LayerId"* %".2")

declare %"struct.ritz_module_1.Layer"* @"layer_tree_get_mut"(%"struct.ritz_module_1.LayerTree"* %".1", %"struct.ritz_module_1.LayerId"* %".2")

declare %"struct.ritz_module_1.Layer"* @"layer_tree_root"(%"struct.ritz_module_1.LayerTree"* %".1")

declare i32 @"layer_tree_count"(%"struct.ritz_module_1.LayerTree"* %".1")

declare i32 @"layer_tree_mark_dirty"(%"struct.ritz_module_1.LayerTree"* %".1", %"struct.ritz_module_1.LayerId"* %".2")

declare i32 @"layer_tree_clear_dirty"(%"struct.ritz_module_1.LayerTree"* %".1")

declare i32 @"layer_tree_scroll"(%"struct.ritz_module_1.LayerTree"* %".1", %"struct.ritz_module_1.LayerId"* %".2", i32 %".3", i32 %".4")

declare i32 @"should_create_layer"(%"struct.ritz_module_1.ComputedStyle"* %".1")

define i32 @"main"() !dbg !17
{
entry:
  %"tree.addr" = alloca %"struct.ritz_module_1.RenderTree", !dbg !48
  %"constraints.addr" = alloca %"struct.ritz_module_1.LayoutConstraints", !dbg !58
  %"default_style.addr" = alloca %"struct.ritz_module_1.ComputedStyle", !dbg !60
  %"layer_tree.addr" = alloca %"struct.ritz_module_1.LayerTree", !dbg !64
  %".2" = getelementptr [30 x i8], [30 x i8]* @".str.0", i64 0, i64 0 , !dbg !40
  %".3" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".2", 0 , !dbg !40
  %".4" = insertvalue %"struct.ritz_module_1.StrView" %".3", i64 29, 1 , !dbg !40
  %".5" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".4"), !dbg !40
  %".6" = getelementptr [37 x i8], [37 x i8]* @".str.1", i64 0, i64 0 , !dbg !41
  %".7" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".6", 0 , !dbg !41
  %".8" = insertvalue %"struct.ritz_module_1.StrView" %".7", i64 36, 1 , !dbg !41
  %".9" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".8"), !dbg !41
  %".10" = getelementptr [24 x i8], [24 x i8]* @".str.2", i64 0, i64 0 , !dbg !42
  %".11" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".10", 0 , !dbg !42
  %".12" = insertvalue %"struct.ritz_module_1.StrView" %".11", i64 23, 1 , !dbg !42
  %".13" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".12"), !dbg !42
  %".14" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double 0x4059000000000000), !dbg !43
  %".15" = getelementptr [28 x i8], [28 x i8]* @".str.3", i64 0, i64 0 , !dbg !44
  %".16" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".15", 0 , !dbg !44
  %".17" = insertvalue %"struct.ritz_module_1.StrView" %".16", i64 27, 1 , !dbg !44
  %".18" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".17"), !dbg !44
  %".19" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !45
  %".20" = getelementptr [34 x i8], [34 x i8]* @".str.4", i64 0, i64 0 , !dbg !46
  %".21" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".20", 0 , !dbg !46
  %".22" = insertvalue %"struct.ritz_module_1.StrView" %".21", i64 33, 1 , !dbg !46
  %".23" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".22"), !dbg !46
  %".24" = getelementptr [25 x i8], [25 x i8]* @".str.5", i64 0, i64 0 , !dbg !47
  %".25" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".24", 0 , !dbg !47
  %".26" = insertvalue %"struct.ritz_module_1.StrView" %".25", i64 24, 1 , !dbg !47
  %".27" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".26"), !dbg !47
  %".28" = call %"struct.ritz_module_1.RenderTree" @"render_tree_new"(), !dbg !48
  store %"struct.ritz_module_1.RenderTree" %".28", %"struct.ritz_module_1.RenderTree"* %"tree.addr", !dbg !48
  %".30" = getelementptr [29 x i8], [29 x i8]* @".str.6", i64 0, i64 0 , !dbg !49
  %".31" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".30", 0 , !dbg !49
  %".32" = insertvalue %"struct.ritz_module_1.StrView" %".31", i64 28, 1 , !dbg !49
  %".33" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".32"), !dbg !49
  %".34" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !50
  %".35" = call %"struct.ritz_module_1.RenderNode" @"render_node_new"(%"struct.ritz_module_1.NodeId" %".34", i32 0, %"struct.ritz_module_1.ComputedStyle" %".19"), !dbg !50
  %".36" = call i32 @"render_tree_insert"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.RenderNode" %".35"), !dbg !51
  %".37" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !52
  %".38" = call i32 @"render_tree_set_root"(%"struct.ritz_module_1.RenderTree"* %"tree.addr", %"struct.ritz_module_1.NodeId" %".37"), !dbg !52
  %".39" = getelementptr [27 x i8], [27 x i8]* @".str.7", i64 0, i64 0 , !dbg !53
  %".40" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".39", 0 , !dbg !53
  %".41" = insertvalue %"struct.ritz_module_1.StrView" %".40", i64 26, 1 , !dbg !53
  %".42" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".41"), !dbg !53
  %".43" = call i32 @"render_tree_is_empty"(%"struct.ritz_module_1.RenderTree"* %"tree.addr"), !dbg !54
  %".44" = sext i32 %".43" to i64 , !dbg !54
  %".45" = icmp eq i64 %".44", 0 , !dbg !54
  br i1 %".45", label %"if.then", label %"if.end", !dbg !54
if.then:
  %".47" = getelementptr [27 x i8], [27 x i8]* @".str.8", i64 0, i64 0 , !dbg !55
  %".48" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".47", 0 , !dbg !55
  %".49" = insertvalue %"struct.ritz_module_1.StrView" %".48", i64 26, 1 , !dbg !55
  %".50" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".49"), !dbg !55
  %".51" = call i32 @"render_tree_count"(%"struct.ritz_module_1.RenderTree"* %"tree.addr"), !dbg !56
  %".52" = sext i32 %".51" to i64 , !dbg !56
  %".53" = call i32 @"print_i64"(i64 %".52"), !dbg !56
  %".54" = getelementptr [2 x i8], [2 x i8]* @".str.9", i64 0, i64 0 , !dbg !56
  %".55" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".54", 0 , !dbg !56
  %".56" = insertvalue %"struct.ritz_module_1.StrView" %".55", i64 1, 1 , !dbg !56
  %".57" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".56"), !dbg !56
  br label %"if.end", !dbg !56
if.end:
  %".59" = getelementptr [20 x i8], [20 x i8]* @".str.10", i64 0, i64 0 , !dbg !57
  %".60" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".59", 0 , !dbg !57
  %".61" = insertvalue %"struct.ritz_module_1.StrView" %".60", i64 19, 1 , !dbg !57
  %".62" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".61"), !dbg !57
  %".63" = call %"struct.ritz_module_1.LayoutConstraints" @"layout_constraints_new"(double 0x4089000000000000, double 0x4082c00000000000, double 0x4030000000000000), !dbg !58
  store %"struct.ritz_module_1.LayoutConstraints" %".63", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr", !dbg !58
  %".65" = getelementptr [48 x i8], [48 x i8]* @".str.11", i64 0, i64 0 , !dbg !59
  %".66" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".65", 0 , !dbg !59
  %".67" = insertvalue %"struct.ritz_module_1.StrView" %".66", i64 47, 1 , !dbg !59
  %".68" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".67"), !dbg !59
  %".69" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !60
  store %"struct.ritz_module_1.ComputedStyle" %".69", %"struct.ritz_module_1.ComputedStyle"* %"default_style.addr", !dbg !60
  %".71" = call %"struct.ritz_module_1.BoxDimensions" @"resolve_box_model"(%"struct.ritz_module_1.ComputedStyle"* %"default_style.addr", %"struct.ritz_module_1.LayoutConstraints"* %"constraints.addr"), !dbg !61
  %".72" = getelementptr [35 x i8], [35 x i8]* @".str.12", i64 0, i64 0 , !dbg !62
  %".73" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".72", 0 , !dbg !62
  %".74" = insertvalue %"struct.ritz_module_1.StrView" %".73", i64 34, 1 , !dbg !62
  %".75" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".74"), !dbg !62
  %".76" = getelementptr [24 x i8], [24 x i8]* @".str.13", i64 0, i64 0 , !dbg !63
  %".77" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".76", 0 , !dbg !63
  %".78" = insertvalue %"struct.ritz_module_1.StrView" %".77", i64 23, 1 , !dbg !63
  %".79" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".78"), !dbg !63
  %".80" = call %"struct.ritz_module_1.LayerTree" @"layer_tree_new"(), !dbg !64
  store %"struct.ritz_module_1.LayerTree" %".80", %"struct.ritz_module_1.LayerTree"* %"layer_tree.addr", !dbg !64
  %".82" = getelementptr [28 x i8], [28 x i8]* @".str.14", i64 0, i64 0 , !dbg !65
  %".83" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".82", 0 , !dbg !65
  %".84" = insertvalue %"struct.ritz_module_1.StrView" %".83", i64 27, 1 , !dbg !65
  %".85" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".84"), !dbg !65
  %".86" = trunc i64 0 to i32 , !dbg !66
  %".87" = trunc i64 0 to i32 , !dbg !66
  %".88" = trunc i64 800 to i32 , !dbg !66
  %".89" = trunc i64 600 to i32 , !dbg !66
  %".90" = call %"struct.ritz_module_1.LayerRect" @"layer_rect_new"(i32 %".86", i32 %".87", i32 %".88", i32 %".89"), !dbg !66
  %".91" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !67
  %".92" = call %"struct.ritz_module_1.LayerId" @"layer_tree_create_root"(%"struct.ritz_module_1.LayerTree"* %"layer_tree.addr", %"struct.ritz_module_1.NodeId" %".91", %"struct.ritz_module_1.LayerRect" %".90"), !dbg !67
  %".93" = getelementptr [22 x i8], [22 x i8]* @".str.15", i64 0, i64 0 , !dbg !68
  %".94" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".93", 0 , !dbg !68
  %".95" = insertvalue %"struct.ritz_module_1.StrView" %".94", i64 21, 1 , !dbg !68
  %".96" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".95"), !dbg !68
  %".97" = getelementptr [16 x i8], [16 x i8]* @".str.16", i64 0, i64 0 , !dbg !69
  %".98" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".97", 0 , !dbg !69
  %".99" = insertvalue %"struct.ritz_module_1.StrView" %".98", i64 15, 1 , !dbg !69
  %".100" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".99"), !dbg !69
  %".101" = call i32 @"layer_tree_count"(%"struct.ritz_module_1.LayerTree"* %"layer_tree.addr"), !dbg !70
  %".102" = sext i32 %".101" to i64 , !dbg !70
  %".103" = call i32 @"print_i64"(i64 %".102"), !dbg !70
  %".104" = getelementptr [2 x i8], [2 x i8]* @".str.17", i64 0, i64 0 , !dbg !71
  %".105" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".104", 0 , !dbg !71
  %".106" = insertvalue %"struct.ritz_module_1.StrView" %".105", i64 1, 1 , !dbg !71
  %".107" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".106"), !dbg !71
  %".108" = getelementptr [33 x i8], [33 x i8]* @".str.18", i64 0, i64 0 , !dbg !72
  %".109" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".108", 0 , !dbg !72
  %".110" = insertvalue %"struct.ritz_module_1.StrView" %".109", i64 32, 1 , !dbg !72
  %".111" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".110"), !dbg !72
  %".112" = getelementptr [55 x i8], [55 x i8]* @".str.19", i64 0, i64 0 , !dbg !73
  %".113" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".112", 0 , !dbg !73
  %".114" = insertvalue %"struct.ritz_module_1.StrView" %".113", i64 54, 1 , !dbg !73
  %".115" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".114"), !dbg !73
  %".116" = trunc i64 0 to i32 , !dbg !74
  ret i32 %".116", !dbg !74
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !18
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !77, metadata !7), !dbg !78
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !79
  store i64 0, i64* %".4", !dbg !79
  ret i32 0, !dbg !79
}

define linkonce_odr i32 @"vec_push$Layer"(%"struct.ritz_module_1.Vec$Layer"* %"v.arg", %"struct.ritz_module_1.Layer" %"item.arg") !dbg !19
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$Layer"* %"v.arg", metadata !82, metadata !7), !dbg !83
  %"item" = alloca %"struct.ritz_module_1.Layer"
  store %"struct.ritz_module_1.Layer" %"item.arg", %"struct.ritz_module_1.Layer"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Layer"* %"item", metadata !85, metadata !7), !dbg !83
  %".7" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 1 , !dbg !86
  %".8" = load i64, i64* %".7", !dbg !86
  %".9" = add i64 %".8", 1, !dbg !86
  %".10" = call i32 @"vec_ensure_cap$Layer"(%"struct.ritz_module_1.Vec$Layer"* %"v.arg", i64 %".9"), !dbg !86
  %".11" = sext i32 %".10" to i64 , !dbg !86
  %".12" = icmp ne i64 %".11", 0 , !dbg !86
  br i1 %".12", label %"if.then", label %"if.end", !dbg !86
if.then:
  %".14" = sub i64 0, 1, !dbg !87
  %".15" = trunc i64 %".14" to i32 , !dbg !87
  ret i32 %".15", !dbg !87
if.end:
  %".17" = load %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %"item", !dbg !88
  %".18" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 0 , !dbg !88
  %".19" = load %"struct.ritz_module_1.Layer"*, %"struct.ritz_module_1.Layer"** %".18", !dbg !88
  %".20" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 1 , !dbg !88
  %".21" = load i64, i64* %".20", !dbg !88
  %".22" = getelementptr %"struct.ritz_module_1.Layer", %"struct.ritz_module_1.Layer"* %".19", i64 %".21" , !dbg !88
  store %"struct.ritz_module_1.Layer" %".17", %"struct.ritz_module_1.Layer"* %".22", !dbg !88
  %".24" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 1 , !dbg !89
  %".25" = load i64, i64* %".24", !dbg !89
  %".26" = add i64 %".25", 1, !dbg !89
  %".27" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 1 , !dbg !89
  store i64 %".26", i64* %".27", !dbg !89
  %".29" = trunc i64 0 to i32 , !dbg !90
  ret i32 %".29", !dbg !90
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !20
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !96
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !91, metadata !7), !dbg !92
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !93, metadata !7), !dbg !92
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !94
  %".8" = load i64, i64* %".7", !dbg !94
  %".9" = load i64, i64* %"needed", !dbg !94
  %".10" = icmp sge i64 %".8", %".9" , !dbg !94
  br i1 %".10", label %"if.then", label %"if.end", !dbg !94
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !95
  ret i32 %".12", !dbg !95
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !96
  %".15" = load i64, i64* %".14", !dbg !96
  store i64 %".15", i64* %"new_cap.addr", !dbg !96
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !97, metadata !7), !dbg !98
  %".18" = load i64, i64* %"new_cap.addr", !dbg !99
  %".19" = icmp eq i64 %".18", 0 , !dbg !99
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !99
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !100
  br label %"if.end.1", !dbg !100
if.end.1:
  br label %"while.cond", !dbg !101
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !101
  %".25" = load i64, i64* %"needed", !dbg !101
  %".26" = icmp slt i64 %".24", %".25" , !dbg !101
  br i1 %".26", label %"while.body", label %"while.end", !dbg !101
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !102
  %".29" = mul i64 %".28", 2, !dbg !102
  store i64 %".29", i64* %"new_cap.addr", !dbg !102
  br label %"while.cond", !dbg !102
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !103
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !103
  ret i32 %".33", !dbg !103
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !21
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !106
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !104, metadata !7), !dbg !105
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !107, metadata !7), !dbg !108
  %".6" = load i64, i64* %"cap", !dbg !109
  %".7" = icmp sle i64 %".6", 0 , !dbg !109
  br i1 %".7", label %"if.then", label %"if.end", !dbg !109
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !110
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !110
  store i8* null, i8** %".10", !dbg !110
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !111
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !111
  store i64 0, i64* %".13", !dbg !111
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !112
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !112
  store i64 0, i64* %".16", !dbg !112
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !113
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !113
if.end:
  %".20" = load i64, i64* %"cap", !dbg !114
  %".21" = mul i64 %".20", 1, !dbg !114
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !115
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !115
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !115
  store i8* %".22", i8** %".24", !dbg !115
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !116
  %".27" = load i8*, i8** %".26", !dbg !116
  %".28" = icmp eq i8* %".27", null , !dbg !116
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !116
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !117
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !117
  store i64 0, i64* %".31", !dbg !117
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !118
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !118
  store i64 0, i64* %".34", !dbg !118
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !119
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !119
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !120
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !120
  store i64 0, i64* %".39", !dbg !120
  %".41" = load i64, i64* %"cap", !dbg !121
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !121
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !121
  store i64 %".41", i64* %".43", !dbg !121
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !122
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !122
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !22
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !123, metadata !7), !dbg !124
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !125
  %".5" = load i8*, i8** %".4", !dbg !125
  %".6" = icmp ne i8* %".5", null , !dbg !125
  br i1 %".6", label %"if.then", label %"if.end", !dbg !125
if.then:
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !125
  %".9" = load i8*, i8** %".8", !dbg !125
  %".10" = call i32 @"free"(i8* %".9"), !dbg !125
  br label %"if.end", !dbg !125
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !126
  store i8* null, i8** %".12", !dbg !126
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !127
  store i64 0, i64* %".14", !dbg !127
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !128
  store i64 0, i64* %".16", !dbg !128
  ret i32 0, !dbg !128
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !23
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !129
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !130, metadata !7), !dbg !131
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !132
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !132
  store i8* null, i8** %".4", !dbg !132
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !133
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !133
  store i64 0, i64* %".7", !dbg !133
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !134
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !134
  store i64 0, i64* %".10", !dbg !134
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !135
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !135
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !24
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !136, metadata !7), !dbg !137
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !138, metadata !7), !dbg !137
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !139
  %".8" = load i8*, i8** %".7", !dbg !139
  %".9" = load i64, i64* %"idx", !dbg !139
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !139
  %".11" = load i8, i8* %".10", !dbg !139
  ret i8 %".11", !dbg !139
}

define linkonce_odr %"struct.ritz_module_1.Vec$RenderNode" @"vec_new$RenderNode"() !dbg !25
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$RenderNode", !dbg !140
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", metadata !142, metadata !7), !dbg !143
  %".3" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", !dbg !144
  %".4" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", i32 0, i32 0 , !dbg !144
  %".5" = bitcast i8* null to %"struct.ritz_module_1.RenderNode"* , !dbg !144
  store %"struct.ritz_module_1.RenderNode"* %".5", %"struct.ritz_module_1.RenderNode"** %".4", !dbg !144
  %".7" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", !dbg !145
  %".8" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", i32 0, i32 1 , !dbg !145
  store i64 0, i64* %".8", !dbg !145
  %".10" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", !dbg !146
  %".11" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", i32 0, i32 2 , !dbg !146
  store i64 0, i64* %".11", !dbg !146
  %".13" = load %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.addr", !dbg !147
  ret %"struct.ritz_module_1.Vec$RenderNode" %".13", !dbg !147
}

define linkonce_odr i32 @"vec_push$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", %"struct.ritz_module_1.RenderNode" %"item.arg") !dbg !26
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", metadata !149, metadata !7), !dbg !150
  %"item" = alloca %"struct.ritz_module_1.RenderNode"
  store %"struct.ritz_module_1.RenderNode" %"item.arg", %"struct.ritz_module_1.RenderNode"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.RenderNode"* %"item", metadata !152, metadata !7), !dbg !150
  %".7" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 1 , !dbg !153
  %".8" = load i64, i64* %".7", !dbg !153
  %".9" = add i64 %".8", 1, !dbg !153
  %".10" = call i32 @"vec_ensure_cap$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i64 %".9"), !dbg !153
  %".11" = sext i32 %".10" to i64 , !dbg !153
  %".12" = icmp ne i64 %".11", 0 , !dbg !153
  br i1 %".12", label %"if.then", label %"if.end", !dbg !153
if.then:
  %".14" = sub i64 0, 1, !dbg !154
  %".15" = trunc i64 %".14" to i32 , !dbg !154
  ret i32 %".15", !dbg !154
if.end:
  %".17" = load %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %"item", !dbg !155
  %".18" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 0 , !dbg !155
  %".19" = load %"struct.ritz_module_1.RenderNode"*, %"struct.ritz_module_1.RenderNode"** %".18", !dbg !155
  %".20" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 1 , !dbg !155
  %".21" = load i64, i64* %".20", !dbg !155
  %".22" = getelementptr %"struct.ritz_module_1.RenderNode", %"struct.ritz_module_1.RenderNode"* %".19", i64 %".21" , !dbg !155
  store %"struct.ritz_module_1.RenderNode" %".17", %"struct.ritz_module_1.RenderNode"* %".22", !dbg !155
  %".24" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 1 , !dbg !156
  %".25" = load i64, i64* %".24", !dbg !156
  %".26" = add i64 %".25", 1, !dbg !156
  %".27" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 1 , !dbg !156
  store i64 %".26", i64* %".27", !dbg !156
  %".29" = trunc i64 0 to i32 , !dbg !157
  ret i32 %".29", !dbg !157
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !27
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !158, metadata !7), !dbg !159
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !160, metadata !7), !dbg !159
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !161, metadata !7), !dbg !159
  %".10" = load i8, i8* %"item", !dbg !162
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !162
  %".12" = load i8*, i8** %".11", !dbg !162
  %".13" = load i64, i64* %"idx", !dbg !162
  %".14" = getelementptr i8, i8* %".12", i64 %".13" , !dbg !162
  store i8 %".10", i8* %".14", !dbg !162
  %".16" = trunc i64 0 to i32 , !dbg !163
  ret i32 %".16", !dbg !163
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !28
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !164, metadata !7), !dbg !165
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !166, metadata !7), !dbg !165
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !167
  %".8" = load i64, i64* %".7", !dbg !167
  %".9" = add i64 %".8", 1, !dbg !167
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !167
  %".11" = sext i32 %".10" to i64 , !dbg !167
  %".12" = icmp ne i64 %".11", 0 , !dbg !167
  br i1 %".12", label %"if.then", label %"if.end", !dbg !167
if.then:
  %".14" = sub i64 0, 1, !dbg !168
  %".15" = trunc i64 %".14" to i32 , !dbg !168
  ret i32 %".15", !dbg !168
if.end:
  %".17" = load i8, i8* %"item", !dbg !169
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !169
  %".19" = load i8*, i8** %".18", !dbg !169
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !169
  %".21" = load i64, i64* %".20", !dbg !169
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !169
  store i8 %".17", i8* %".22", !dbg !169
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !170
  %".25" = load i64, i64* %".24", !dbg !170
  %".26" = add i64 %".25", 1, !dbg !170
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !170
  store i64 %".26", i64* %".27", !dbg !170
  %".29" = trunc i64 0 to i32 , !dbg !171
  ret i32 %".29", !dbg !171
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !29
{
entry:
  %"i" = alloca i64, !dbg !177
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !172, metadata !7), !dbg !173
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !175, metadata !7), !dbg !173
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !176, metadata !7), !dbg !173
  %".10" = load i64, i64* %"len", !dbg !177
  store i64 0, i64* %"i", !dbg !177
  br label %"for.cond", !dbg !177
for.cond:
  %".13" = load i64, i64* %"i", !dbg !177
  %".14" = icmp slt i64 %".13", %".10" , !dbg !177
  br i1 %".14", label %"for.body", label %"for.end", !dbg !177
for.body:
  %".16" = load i8*, i8** %"data", !dbg !177
  %".17" = load i64, i64* %"i", !dbg !177
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !177
  %".19" = load i8, i8* %".18", !dbg !177
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !177
  %".21" = sext i32 %".20" to i64 , !dbg !177
  %".22" = icmp ne i64 %".21", 0 , !dbg !177
  br i1 %".22", label %"if.then", label %"if.end", !dbg !177
for.incr:
  %".28" = load i64, i64* %"i", !dbg !178
  %".29" = add i64 %".28", 1, !dbg !178
  store i64 %".29", i64* %"i", !dbg !178
  br label %"for.cond", !dbg !178
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !179
  ret i32 %".32", !dbg !179
if.then:
  %".24" = sub i64 0, 1, !dbg !178
  %".25" = trunc i64 %".24" to i32 , !dbg !178
  ret i32 %".25", !dbg !178
if.end:
  br label %"for.incr", !dbg !178
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !30
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !180, metadata !7), !dbg !181
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !182
  %".5" = load i64, i64* %".4", !dbg !182
  %".6" = sub i64 %".5", 1, !dbg !182
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !182
  store i64 %".6", i64* %".7", !dbg !182
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !183
  %".10" = load i8*, i8** %".9", !dbg !183
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !183
  %".12" = load i64, i64* %".11", !dbg !183
  %".13" = getelementptr i8, i8* %".10", i64 %".12" , !dbg !183
  %".14" = load i8, i8* %".13", !dbg !183
  ret i8 %".14", !dbg !183
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !31
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !186, metadata !7), !dbg !187
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !189, metadata !7), !dbg !187
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !190
  %".8" = load i64, i64* %".7", !dbg !190
  %".9" = add i64 %".8", 1, !dbg !190
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !190
  %".11" = sext i32 %".10" to i64 , !dbg !190
  %".12" = icmp ne i64 %".11", 0 , !dbg !190
  br i1 %".12", label %"if.then", label %"if.end", !dbg !190
if.then:
  %".14" = sub i64 0, 1, !dbg !191
  %".15" = trunc i64 %".14" to i32 , !dbg !191
  ret i32 %".15", !dbg !191
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !192
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !192
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !192
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !192
  %".21" = load i64, i64* %".20", !dbg !192
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !192
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !192
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !193
  %".25" = load i64, i64* %".24", !dbg !193
  %".26" = add i64 %".25", 1, !dbg !193
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !193
  store i64 %".26", i64* %".27", !dbg !193
  %".29" = trunc i64 0 to i32 , !dbg !194
  ret i32 %".29", !dbg !194
}

define linkonce_odr %"struct.ritz_module_1.Vec$Layer" @"vec_new$Layer"() !dbg !32
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$Layer", !dbg !195
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$Layer"* %"v.addr", metadata !196, metadata !7), !dbg !197
  %".3" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", !dbg !198
  %".4" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", i32 0, i32 0 , !dbg !198
  %".5" = bitcast i8* null to %"struct.ritz_module_1.Layer"* , !dbg !198
  store %"struct.ritz_module_1.Layer"* %".5", %"struct.ritz_module_1.Layer"** %".4", !dbg !198
  %".7" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", !dbg !199
  %".8" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", i32 0, i32 1 , !dbg !199
  store i64 0, i64* %".8", !dbg !199
  %".10" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", !dbg !200
  %".11" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", i32 0, i32 2 , !dbg !200
  store i64 0, i64* %".11", !dbg !200
  %".13" = load %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.addr", !dbg !201
  ret %"struct.ritz_module_1.Vec$Layer" %".13", !dbg !201
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

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !34
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !220
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !215, metadata !7), !dbg !216
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !217, metadata !7), !dbg !216
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !218
  %".8" = load i64, i64* %".7", !dbg !218
  %".9" = load i64, i64* %"needed", !dbg !218
  %".10" = icmp sge i64 %".8", %".9" , !dbg !218
  br i1 %".10", label %"if.then", label %"if.end", !dbg !218
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !219
  ret i32 %".12", !dbg !219
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !220
  %".15" = load i64, i64* %".14", !dbg !220
  store i64 %".15", i64* %"new_cap.addr", !dbg !220
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !221, metadata !7), !dbg !222
  %".18" = load i64, i64* %"new_cap.addr", !dbg !223
  %".19" = icmp eq i64 %".18", 0 , !dbg !223
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !223
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !224
  br label %"if.end.1", !dbg !224
if.end.1:
  br label %"while.cond", !dbg !225
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !225
  %".25" = load i64, i64* %"needed", !dbg !225
  %".26" = icmp slt i64 %".24", %".25" , !dbg !225
  br i1 %".26", label %"while.body", label %"while.end", !dbg !225
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !226
  %".29" = mul i64 %".28", 2, !dbg !226
  store i64 %".29", i64* %"new_cap.addr", !dbg !226
  br label %"while.cond", !dbg !226
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !227
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !227
  ret i32 %".33", !dbg !227
}

define linkonce_odr i32 @"vec_ensure_cap$Layer"(%"struct.ritz_module_1.Vec$Layer"* %"v.arg", i64 %"needed.arg") !dbg !35
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !233
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$Layer"* %"v.arg", metadata !228, metadata !7), !dbg !229
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !230, metadata !7), !dbg !229
  %".7" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 2 , !dbg !231
  %".8" = load i64, i64* %".7", !dbg !231
  %".9" = load i64, i64* %"needed", !dbg !231
  %".10" = icmp sge i64 %".8", %".9" , !dbg !231
  br i1 %".10", label %"if.then", label %"if.end", !dbg !231
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !232
  ret i32 %".12", !dbg !232
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 2 , !dbg !233
  %".15" = load i64, i64* %".14", !dbg !233
  store i64 %".15", i64* %"new_cap.addr", !dbg !233
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !234, metadata !7), !dbg !235
  %".18" = load i64, i64* %"new_cap.addr", !dbg !236
  %".19" = icmp eq i64 %".18", 0 , !dbg !236
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !236
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !237
  br label %"if.end.1", !dbg !237
if.end.1:
  br label %"while.cond", !dbg !238
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !238
  %".25" = load i64, i64* %"needed", !dbg !238
  %".26" = icmp slt i64 %".24", %".25" , !dbg !238
  br i1 %".26", label %"while.body", label %"while.end", !dbg !238
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !239
  %".29" = mul i64 %".28", 2, !dbg !239
  store i64 %".29", i64* %"new_cap.addr", !dbg !239
  br label %"while.cond", !dbg !239
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !240
  %".33" = call i32 @"vec_grow$Layer"(%"struct.ritz_module_1.Vec$Layer"* %"v.arg", i64 %".32"), !dbg !240
  ret i32 %".33", !dbg !240
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !36
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !241, metadata !7), !dbg !242
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !243, metadata !7), !dbg !242
  %".7" = load i64, i64* %"new_cap", !dbg !244
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !244
  %".9" = load i64, i64* %".8", !dbg !244
  %".10" = icmp sle i64 %".7", %".9" , !dbg !244
  br i1 %".10", label %"if.then", label %"if.end", !dbg !244
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !245
  ret i32 %".12", !dbg !245
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !246
  %".15" = mul i64 %".14", 1, !dbg !246
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !247
  %".17" = load i8*, i8** %".16", !dbg !247
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !247
  %".19" = icmp eq i8* %".18", null , !dbg !248
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !248
if.then.1:
  %".21" = sub i64 0, 1, !dbg !249
  %".22" = trunc i64 %".21" to i32 , !dbg !249
  ret i32 %".22", !dbg !249
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !250
  store i8* %".18", i8** %".24", !dbg !250
  %".26" = load i64, i64* %"new_cap", !dbg !251
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !251
  store i64 %".26", i64* %".27", !dbg !251
  %".29" = trunc i64 0 to i32 , !dbg !252
  ret i32 %".29", !dbg !252
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !37
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !253, metadata !7), !dbg !254
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !255, metadata !7), !dbg !254
  %".7" = load i64, i64* %"new_cap", !dbg !256
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !256
  %".9" = load i64, i64* %".8", !dbg !256
  %".10" = icmp sle i64 %".7", %".9" , !dbg !256
  br i1 %".10", label %"if.then", label %"if.end", !dbg !256
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !257
  ret i32 %".12", !dbg !257
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !258
  %".15" = mul i64 %".14", 16, !dbg !258
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !259
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !259
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !259
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !259
  %".20" = icmp eq i8* %".19", null , !dbg !260
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !260
if.then.1:
  %".22" = sub i64 0, 1, !dbg !261
  %".23" = trunc i64 %".22" to i32 , !dbg !261
  ret i32 %".23", !dbg !261
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !262
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !262
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !262
  %".28" = load i64, i64* %"new_cap", !dbg !263
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !263
  store i64 %".28", i64* %".29", !dbg !263
  %".31" = trunc i64 0 to i32 , !dbg !264
  ret i32 %".31", !dbg !264
}

define linkonce_odr i32 @"vec_grow$RenderNode"(%"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i64 %"new_cap.arg") !dbg !38
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", metadata !265, metadata !7), !dbg !266
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !267, metadata !7), !dbg !266
  %".7" = load i64, i64* %"new_cap", !dbg !268
  %".8" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 2 , !dbg !268
  %".9" = load i64, i64* %".8", !dbg !268
  %".10" = icmp sle i64 %".7", %".9" , !dbg !268
  br i1 %".10", label %"if.then", label %"if.end", !dbg !268
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !269
  ret i32 %".12", !dbg !269
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !270
  %".15" = mul i64 %".14", 656, !dbg !270
  %".16" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 0 , !dbg !271
  %".17" = load %"struct.ritz_module_1.RenderNode"*, %"struct.ritz_module_1.RenderNode"** %".16", !dbg !271
  %".18" = bitcast %"struct.ritz_module_1.RenderNode"* %".17" to i8* , !dbg !271
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !271
  %".20" = icmp eq i8* %".19", null , !dbg !272
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !272
if.then.1:
  %".22" = sub i64 0, 1, !dbg !273
  %".23" = trunc i64 %".22" to i32 , !dbg !273
  ret i32 %".23", !dbg !273
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.RenderNode"* , !dbg !274
  %".26" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 0 , !dbg !274
  store %"struct.ritz_module_1.RenderNode"* %".25", %"struct.ritz_module_1.RenderNode"** %".26", !dbg !274
  %".28" = load i64, i64* %"new_cap", !dbg !275
  %".29" = getelementptr %"struct.ritz_module_1.Vec$RenderNode", %"struct.ritz_module_1.Vec$RenderNode"* %"v.arg", i32 0, i32 2 , !dbg !275
  store i64 %".28", i64* %".29", !dbg !275
  %".31" = trunc i64 0 to i32 , !dbg !276
  ret i32 %".31", !dbg !276
}

define linkonce_odr i32 @"vec_grow$Layer"(%"struct.ritz_module_1.Vec$Layer"* %"v.arg", i64 %"new_cap.arg") !dbg !39
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$Layer"* %"v.arg", metadata !277, metadata !7), !dbg !278
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !279, metadata !7), !dbg !278
  %".7" = load i64, i64* %"new_cap", !dbg !280
  %".8" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 2 , !dbg !280
  %".9" = load i64, i64* %".8", !dbg !280
  %".10" = icmp sle i64 %".7", %".9" , !dbg !280
  br i1 %".10", label %"if.then", label %"if.end", !dbg !280
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !281
  ret i32 %".12", !dbg !281
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !282
  %".15" = mul i64 %".14", 184, !dbg !282
  %".16" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 0 , !dbg !283
  %".17" = load %"struct.ritz_module_1.Layer"*, %"struct.ritz_module_1.Layer"** %".16", !dbg !283
  %".18" = bitcast %"struct.ritz_module_1.Layer"* %".17" to i8* , !dbg !283
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !283
  %".20" = icmp eq i8* %".19", null , !dbg !284
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !284
if.then.1:
  %".22" = sub i64 0, 1, !dbg !285
  %".23" = trunc i64 %".22" to i32 , !dbg !285
  ret i32 %".23", !dbg !285
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.Layer"* , !dbg !286
  %".26" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 0 , !dbg !286
  store %"struct.ritz_module_1.Layer"* %".25", %"struct.ritz_module_1.Layer"** %".26", !dbg !286
  %".28" = load i64, i64* %"new_cap", !dbg !287
  %".29" = getelementptr %"struct.ritz_module_1.Vec$Layer", %"struct.ritz_module_1.Vec$Layer"* %"v.arg", i32 0, i32 2 , !dbg !287
  store i64 %".28", i64* %".29", !dbg !287
  %".31" = trunc i64 0 to i32 , !dbg !288
  ret i32 %".31", !dbg !288
}

@".str.0" = private constant [30 x i8] c"Iris rendering engine v0.1.0\0a\00"
@".str.1" = private constant [37 x i8] c"Usage: iris [--test|--demo|--help]\0a\0a\00"
@".str.2" = private constant [24 x i8] c"Testing style types...\0a\00"
@".str.3" = private constant [28 x i8] c"  Created dimension: 100px\0a\00"
@".str.4" = private constant [34 x i8] c"  Created default computed style\0a\00"
@".str.5" = private constant [25 x i8] c"\0aTesting render tree...\0a\00"
@".str.6" = private constant [29 x i8] c"  Created empty render tree\0a\00"
@".str.7" = private constant [27 x i8] c"  Added root node to tree\0a\00"
@".str.8" = private constant [27 x i8] c"  Tree has nodes: count = \00"
@".str.9" = private constant [2 x i8] c"\0a\00"
@".str.10" = private constant [20 x i8] c"\0aTesting layout...\0a\00"
@".str.11" = private constant [48 x i8] c"  Created layout constraints: 800x600 viewport\0a\00"
@".str.12" = private constant [35 x i8] c"  Box model resolved successfully\0a\00"
@".str.13" = private constant [24 x i8] c"\0aTesting layer tree...\0a\00"
@".str.14" = private constant [28 x i8] c"  Created empty layer tree\0a\00"
@".str.15" = private constant [22 x i8] c"  Created root layer\0a\00"
@".str.16" = private constant [16 x i8] c"  Layer count: \00"
@".str.17" = private constant [2 x i8] c"\0a\00"
@".str.18" = private constant [33 x i8] c"\0aIris initialized successfully!\0a\00"
@".str.19" = private constant [55 x i8] c"Core modules tested (paint/hit temporarily disabled).\0a\00"
define void @_start() naked
{
entry:
  call void asm sideeffect "
    andq $$-16, %rsp
    call main
    movq %rax, %rdi
    movq $$60, %rax
    syscall
  ", "~{rax},~{rdi},~{rsi},~{rdx},~{rsp},~{rcx},~{r11},~{memory}"()
  unreachable
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/src", filename: "main.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 22, name: "main", scopeLine: 22, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$Layer", scopeLine: 210, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$RenderNode", scopeLine: 116, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$RenderNode", scopeLine: 210, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$Layer", scopeLine: 116, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$RenderNode", scopeLine: 193, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$Layer", scopeLine: 193, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$RenderNode", scopeLine: 179, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$Layer", scopeLine: 179, type: !4, unit: !1)
!40 = !DILocation(column: 5, line: 23, scope: !17)
!41 = !DILocation(column: 5, line: 24, scope: !17)
!42 = !DILocation(column: 5, line: 29, scope: !17)
!43 = !DILocation(column: 5, line: 30, scope: !17)
!44 = !DILocation(column: 5, line: 31, scope: !17)
!45 = !DILocation(column: 5, line: 33, scope: !17)
!46 = !DILocation(column: 5, line: 34, scope: !17)
!47 = !DILocation(column: 5, line: 39, scope: !17)
!48 = !DILocation(column: 5, line: 40, scope: !17)
!49 = !DILocation(column: 5, line: 41, scope: !17)
!50 = !DILocation(column: 5, line: 43, scope: !17)
!51 = !DILocation(column: 5, line: 44, scope: !17)
!52 = !DILocation(column: 5, line: 45, scope: !17)
!53 = !DILocation(column: 5, line: 46, scope: !17)
!54 = !DILocation(column: 5, line: 48, scope: !17)
!55 = !DILocation(column: 9, line: 49, scope: !17)
!56 = !DILocation(column: 9, line: 50, scope: !17)
!57 = !DILocation(column: 5, line: 56, scope: !17)
!58 = !DILocation(column: 5, line: 57, scope: !17)
!59 = !DILocation(column: 5, line: 58, scope: !17)
!60 = !DILocation(column: 5, line: 60, scope: !17)
!61 = !DILocation(column: 5, line: 61, scope: !17)
!62 = !DILocation(column: 5, line: 62, scope: !17)
!63 = !DILocation(column: 5, line: 67, scope: !17)
!64 = !DILocation(column: 5, line: 68, scope: !17)
!65 = !DILocation(column: 5, line: 69, scope: !17)
!66 = !DILocation(column: 5, line: 71, scope: !17)
!67 = !DILocation(column: 5, line: 72, scope: !17)
!68 = !DILocation(column: 5, line: 73, scope: !17)
!69 = !DILocation(column: 5, line: 75, scope: !17)
!70 = !DILocation(column: 5, line: 76, scope: !17)
!71 = !DILocation(column: 5, line: 77, scope: !17)
!72 = !DILocation(column: 5, line: 82, scope: !17)
!73 = !DILocation(column: 5, line: 83, scope: !17)
!74 = !DILocation(column: 5, line: 84, scope: !17)
!75 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!76 = !DIDerivedType(baseType: !75, size: 64, tag: DW_TAG_reference_type)
!77 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !18, type: !76)
!78 = !DILocation(column: 1, line: 244, scope: !18)
!79 = !DILocation(column: 5, line: 245, scope: !18)
!80 = !DICompositeType(align: 64, file: !0, name: "Vec$Layer", size: 192, tag: DW_TAG_structure_type)
!81 = !DIDerivedType(baseType: !80, size: 64, tag: DW_TAG_reference_type)
!82 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !19, type: !81)
!83 = !DILocation(column: 1, line: 210, scope: !19)
!84 = !DICompositeType(align: 64, file: !0, name: "Layer", size: 1472, tag: DW_TAG_structure_type)
!85 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !19, type: !84)
!86 = !DILocation(column: 5, line: 211, scope: !19)
!87 = !DILocation(column: 9, line: 212, scope: !19)
!88 = !DILocation(column: 5, line: 213, scope: !19)
!89 = !DILocation(column: 5, line: 214, scope: !19)
!90 = !DILocation(column: 5, line: 215, scope: !19)
!91 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !20, type: !76)
!92 = !DILocation(column: 1, line: 193, scope: !20)
!93 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !20, type: !11)
!94 = !DILocation(column: 5, line: 194, scope: !20)
!95 = !DILocation(column: 9, line: 195, scope: !20)
!96 = !DILocation(column: 5, line: 197, scope: !20)
!97 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !20, type: !11)
!98 = !DILocation(column: 1, line: 197, scope: !20)
!99 = !DILocation(column: 5, line: 198, scope: !20)
!100 = !DILocation(column: 9, line: 199, scope: !20)
!101 = !DILocation(column: 5, line: 200, scope: !20)
!102 = !DILocation(column: 9, line: 201, scope: !20)
!103 = !DILocation(column: 5, line: 203, scope: !20)
!104 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !21, type: !11)
!105 = !DILocation(column: 1, line: 124, scope: !21)
!106 = !DILocation(column: 5, line: 125, scope: !21)
!107 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !21, type: !75)
!108 = !DILocation(column: 1, line: 125, scope: !21)
!109 = !DILocation(column: 5, line: 126, scope: !21)
!110 = !DILocation(column: 9, line: 127, scope: !21)
!111 = !DILocation(column: 9, line: 128, scope: !21)
!112 = !DILocation(column: 9, line: 129, scope: !21)
!113 = !DILocation(column: 9, line: 130, scope: !21)
!114 = !DILocation(column: 5, line: 132, scope: !21)
!115 = !DILocation(column: 5, line: 133, scope: !21)
!116 = !DILocation(column: 5, line: 134, scope: !21)
!117 = !DILocation(column: 9, line: 135, scope: !21)
!118 = !DILocation(column: 9, line: 136, scope: !21)
!119 = !DILocation(column: 9, line: 137, scope: !21)
!120 = !DILocation(column: 5, line: 139, scope: !21)
!121 = !DILocation(column: 5, line: 140, scope: !21)
!122 = !DILocation(column: 5, line: 141, scope: !21)
!123 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !22, type: !76)
!124 = !DILocation(column: 1, line: 148, scope: !22)
!125 = !DILocation(column: 5, line: 149, scope: !22)
!126 = !DILocation(column: 5, line: 151, scope: !22)
!127 = !DILocation(column: 5, line: 152, scope: !22)
!128 = !DILocation(column: 5, line: 153, scope: !22)
!129 = !DILocation(column: 5, line: 117, scope: !23)
!130 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !23, type: !75)
!131 = !DILocation(column: 1, line: 117, scope: !23)
!132 = !DILocation(column: 5, line: 118, scope: !23)
!133 = !DILocation(column: 5, line: 119, scope: !23)
!134 = !DILocation(column: 5, line: 120, scope: !23)
!135 = !DILocation(column: 5, line: 121, scope: !23)
!136 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !24, type: !76)
!137 = !DILocation(column: 1, line: 225, scope: !24)
!138 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !24, type: !11)
!139 = !DILocation(column: 5, line: 226, scope: !24)
!140 = !DILocation(column: 5, line: 117, scope: !25)
!141 = !DICompositeType(align: 64, file: !0, name: "Vec$RenderNode", size: 192, tag: DW_TAG_structure_type)
!142 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !25, type: !141)
!143 = !DILocation(column: 1, line: 117, scope: !25)
!144 = !DILocation(column: 5, line: 118, scope: !25)
!145 = !DILocation(column: 5, line: 119, scope: !25)
!146 = !DILocation(column: 5, line: 120, scope: !25)
!147 = !DILocation(column: 5, line: 121, scope: !25)
!148 = !DIDerivedType(baseType: !141, size: 64, tag: DW_TAG_reference_type)
!149 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !26, type: !148)
!150 = !DILocation(column: 1, line: 210, scope: !26)
!151 = !DICompositeType(align: 64, file: !0, name: "RenderNode", size: 5248, tag: DW_TAG_structure_type)
!152 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !26, type: !151)
!153 = !DILocation(column: 5, line: 211, scope: !26)
!154 = !DILocation(column: 9, line: 212, scope: !26)
!155 = !DILocation(column: 5, line: 213, scope: !26)
!156 = !DILocation(column: 5, line: 214, scope: !26)
!157 = !DILocation(column: 5, line: 215, scope: !26)
!158 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !27, type: !76)
!159 = !DILocation(column: 1, line: 235, scope: !27)
!160 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !27, type: !11)
!161 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !27, type: !12)
!162 = !DILocation(column: 5, line: 236, scope: !27)
!163 = !DILocation(column: 5, line: 237, scope: !27)
!164 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !28, type: !76)
!165 = !DILocation(column: 1, line: 210, scope: !28)
!166 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !28, type: !12)
!167 = !DILocation(column: 5, line: 211, scope: !28)
!168 = !DILocation(column: 9, line: 212, scope: !28)
!169 = !DILocation(column: 5, line: 213, scope: !28)
!170 = !DILocation(column: 5, line: 214, scope: !28)
!171 = !DILocation(column: 5, line: 215, scope: !28)
!172 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !29, type: !76)
!173 = !DILocation(column: 1, line: 288, scope: !29)
!174 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!175 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !29, type: !174)
!176 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !29, type: !11)
!177 = !DILocation(column: 5, line: 289, scope: !29)
!178 = !DILocation(column: 13, line: 291, scope: !29)
!179 = !DILocation(column: 5, line: 292, scope: !29)
!180 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !30, type: !76)
!181 = !DILocation(column: 1, line: 219, scope: !30)
!182 = !DILocation(column: 5, line: 220, scope: !30)
!183 = !DILocation(column: 5, line: 221, scope: !30)
!184 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!185 = !DIDerivedType(baseType: !184, size: 64, tag: DW_TAG_reference_type)
!186 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !31, type: !185)
!187 = !DILocation(column: 1, line: 210, scope: !31)
!188 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!189 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !31, type: !188)
!190 = !DILocation(column: 5, line: 211, scope: !31)
!191 = !DILocation(column: 9, line: 212, scope: !31)
!192 = !DILocation(column: 5, line: 213, scope: !31)
!193 = !DILocation(column: 5, line: 214, scope: !31)
!194 = !DILocation(column: 5, line: 215, scope: !31)
!195 = !DILocation(column: 5, line: 117, scope: !32)
!196 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !32, type: !80)
!197 = !DILocation(column: 1, line: 117, scope: !32)
!198 = !DILocation(column: 5, line: 118, scope: !32)
!199 = !DILocation(column: 5, line: 119, scope: !32)
!200 = !DILocation(column: 5, line: 120, scope: !32)
!201 = !DILocation(column: 5, line: 121, scope: !32)
!202 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !33, type: !148)
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
!215 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !34, type: !185)
!216 = !DILocation(column: 1, line: 193, scope: !34)
!217 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !34, type: !11)
!218 = !DILocation(column: 5, line: 194, scope: !34)
!219 = !DILocation(column: 9, line: 195, scope: !34)
!220 = !DILocation(column: 5, line: 197, scope: !34)
!221 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !34, type: !11)
!222 = !DILocation(column: 1, line: 197, scope: !34)
!223 = !DILocation(column: 5, line: 198, scope: !34)
!224 = !DILocation(column: 9, line: 199, scope: !34)
!225 = !DILocation(column: 5, line: 200, scope: !34)
!226 = !DILocation(column: 9, line: 201, scope: !34)
!227 = !DILocation(column: 5, line: 203, scope: !34)
!228 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !35, type: !81)
!229 = !DILocation(column: 1, line: 193, scope: !35)
!230 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !35, type: !11)
!231 = !DILocation(column: 5, line: 194, scope: !35)
!232 = !DILocation(column: 9, line: 195, scope: !35)
!233 = !DILocation(column: 5, line: 197, scope: !35)
!234 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !35, type: !11)
!235 = !DILocation(column: 1, line: 197, scope: !35)
!236 = !DILocation(column: 5, line: 198, scope: !35)
!237 = !DILocation(column: 9, line: 199, scope: !35)
!238 = !DILocation(column: 5, line: 200, scope: !35)
!239 = !DILocation(column: 9, line: 201, scope: !35)
!240 = !DILocation(column: 5, line: 203, scope: !35)
!241 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !36, type: !76)
!242 = !DILocation(column: 1, line: 179, scope: !36)
!243 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !36, type: !11)
!244 = !DILocation(column: 5, line: 180, scope: !36)
!245 = !DILocation(column: 9, line: 181, scope: !36)
!246 = !DILocation(column: 5, line: 183, scope: !36)
!247 = !DILocation(column: 5, line: 184, scope: !36)
!248 = !DILocation(column: 5, line: 185, scope: !36)
!249 = !DILocation(column: 9, line: 186, scope: !36)
!250 = !DILocation(column: 5, line: 188, scope: !36)
!251 = !DILocation(column: 5, line: 189, scope: !36)
!252 = !DILocation(column: 5, line: 190, scope: !36)
!253 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !37, type: !185)
!254 = !DILocation(column: 1, line: 179, scope: !37)
!255 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !37, type: !11)
!256 = !DILocation(column: 5, line: 180, scope: !37)
!257 = !DILocation(column: 9, line: 181, scope: !37)
!258 = !DILocation(column: 5, line: 183, scope: !37)
!259 = !DILocation(column: 5, line: 184, scope: !37)
!260 = !DILocation(column: 5, line: 185, scope: !37)
!261 = !DILocation(column: 9, line: 186, scope: !37)
!262 = !DILocation(column: 5, line: 188, scope: !37)
!263 = !DILocation(column: 5, line: 189, scope: !37)
!264 = !DILocation(column: 5, line: 190, scope: !37)
!265 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !38, type: !148)
!266 = !DILocation(column: 1, line: 179, scope: !38)
!267 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !38, type: !11)
!268 = !DILocation(column: 5, line: 180, scope: !38)
!269 = !DILocation(column: 9, line: 181, scope: !38)
!270 = !DILocation(column: 5, line: 183, scope: !38)
!271 = !DILocation(column: 5, line: 184, scope: !38)
!272 = !DILocation(column: 5, line: 185, scope: !38)
!273 = !DILocation(column: 9, line: 186, scope: !38)
!274 = !DILocation(column: 5, line: 188, scope: !38)
!275 = !DILocation(column: 5, line: 189, scope: !38)
!276 = !DILocation(column: 5, line: 190, scope: !38)
!277 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !39, type: !81)
!278 = !DILocation(column: 1, line: 179, scope: !39)
!279 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !39, type: !11)
!280 = !DILocation(column: 5, line: 180, scope: !39)
!281 = !DILocation(column: 9, line: 181, scope: !39)
!282 = !DILocation(column: 5, line: 183, scope: !39)
!283 = !DILocation(column: 5, line: 184, scope: !39)
!284 = !DILocation(column: 5, line: 185, scope: !39)
!285 = !DILocation(column: 9, line: 186, scope: !39)
!286 = !DILocation(column: 5, line: 188, scope: !39)
!287 = !DILocation(column: 5, line: 189, scope: !39)
!288 = !DILocation(column: 5, line: 190, scope: !39)