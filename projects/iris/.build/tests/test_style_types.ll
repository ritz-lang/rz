; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

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

define internal i32 @"test_node_id_new"() !dbg !17
{
entry:
  %".2" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 42), !dbg !44
  %".3" = extractvalue %"struct.ritz_module_1.NodeId" %".2", 0 , !dbg !45
  %".4" = icmp ne i64 %".3", 42 , !dbg !45
  br i1 %".4", label %"if.then", label %"if.end", !dbg !45
if.then:
  %".6" = trunc i64 1 to i32 , !dbg !46
  ret i32 %".6", !dbg !46
if.end:
  %".8" = trunc i64 0 to i32 , !dbg !47
  ret i32 %".8", !dbg !47
}

define internal i32 @"test_node_id_invalid"() !dbg !18
{
entry:
  %".2" = call %"struct.ritz_module_1.NodeId" @"node_id_invalid"(), !dbg !48
  %"id.addr" = alloca %"struct.ritz_module_1.NodeId", !dbg !49
  store %"struct.ritz_module_1.NodeId" %".2", %"struct.ritz_module_1.NodeId"* %"id.addr", !dbg !49
  %".4" = call i32 @"node_id_is_valid"(%"struct.ritz_module_1.NodeId"* %"id.addr"), !dbg !49
  %".5" = sext i32 %".4" to i64 , !dbg !49
  %".6" = icmp ne i64 %".5", 0 , !dbg !49
  br i1 %".6", label %"if.then", label %"if.end", !dbg !49
if.then:
  %".8" = trunc i64 1 to i32 , !dbg !50
  ret i32 %".8", !dbg !50
if.end:
  %".10" = trunc i64 0 to i32 , !dbg !51
  ret i32 %".10", !dbg !51
}

define internal i32 @"test_node_id_valid"() !dbg !19
{
entry:
  %".2" = call %"struct.ritz_module_1.NodeId" @"node_id_new"(i64 1), !dbg !52
  %"id.addr" = alloca %"struct.ritz_module_1.NodeId", !dbg !53
  store %"struct.ritz_module_1.NodeId" %".2", %"struct.ritz_module_1.NodeId"* %"id.addr", !dbg !53
  %".4" = call i32 @"node_id_is_valid"(%"struct.ritz_module_1.NodeId"* %"id.addr"), !dbg !53
  %".5" = sext i32 %".4" to i64 , !dbg !53
  %".6" = icmp eq i64 %".5", 0 , !dbg !53
  br i1 %".6", label %"if.then", label %"if.end", !dbg !53
if.then:
  %".8" = trunc i64 1 to i32 , !dbg !54
  ret i32 %".8", !dbg !54
if.end:
  %".10" = trunc i64 0 to i32 , !dbg !55
  ret i32 %".10", !dbg !55
}

define internal i32 @"test_dimension_px"() !dbg !20
{
entry:
  %".2" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double 0x4059000000000000), !dbg !56
  %".3" = extractvalue %"struct.ritz_module_1.Dimension" %".2", 0 , !dbg !57
  %".4" = fcmp one double %".3", 0x4059000000000000 , !dbg !57
  br i1 %".4", label %"if.then", label %"if.end", !dbg !57
if.then:
  %".6" = trunc i64 1 to i32 , !dbg !58
  ret i32 %".6", !dbg !58
if.end:
  %".8" = extractvalue %"struct.ritz_module_1.Dimension" %".2", 1 , !dbg !59
  %".9" = icmp ne i32 %".8", 0 , !dbg !59
  br i1 %".9", label %"if.then.1", label %"if.end.1", !dbg !59
if.then.1:
  %".11" = trunc i64 2 to i32 , !dbg !60
  ret i32 %".11", !dbg !60
if.end.1:
  %".13" = trunc i64 0 to i32 , !dbg !61
  ret i32 %".13", !dbg !61
}

define internal i32 @"test_dimension_percent"() !dbg !21
{
entry:
  %".2" = call %"struct.ritz_module_1.Dimension" @"dimension_percent"(double 0x4049000000000000), !dbg !62
  %".3" = extractvalue %"struct.ritz_module_1.Dimension" %".2", 0 , !dbg !63
  %".4" = fcmp one double %".3", 0x4049000000000000 , !dbg !63
  br i1 %".4", label %"if.then", label %"if.end", !dbg !63
if.then:
  %".6" = trunc i64 1 to i32 , !dbg !64
  ret i32 %".6", !dbg !64
if.end:
  %".8" = extractvalue %"struct.ritz_module_1.Dimension" %".2", 1 , !dbg !65
  %".9" = icmp ne i32 %".8", 3 , !dbg !65
  br i1 %".9", label %"if.then.1", label %"if.end.1", !dbg !65
if.then.1:
  %".11" = trunc i64 2 to i32 , !dbg !66
  ret i32 %".11", !dbg !66
if.end.1:
  %".13" = trunc i64 0 to i32 , !dbg !67
  ret i32 %".13", !dbg !67
}

define internal i32 @"test_dimension_auto"() !dbg !22
{
entry:
  %".2" = call %"struct.ritz_module_1.Dimension" @"dimension_auto"(), !dbg !68
  %".3" = call i32 @"dimension_is_auto"(%"struct.ritz_module_1.Dimension" %".2"), !dbg !69
  %".4" = sext i32 %".3" to i64 , !dbg !69
  %".5" = icmp eq i64 %".4", 0 , !dbg !69
  br i1 %".5", label %"if.then", label %"if.end", !dbg !69
if.then:
  %".7" = trunc i64 1 to i32 , !dbg !70
  ret i32 %".7", !dbg !70
if.end:
  %".9" = trunc i64 0 to i32 , !dbg !71
  ret i32 %".9", !dbg !71
}

define internal i32 @"test_dimension_is_auto_false"() !dbg !23
{
entry:
  %".2" = call %"struct.ritz_module_1.Dimension" @"dimension_px"(double 0x4024000000000000), !dbg !72
  %".3" = call i32 @"dimension_is_auto"(%"struct.ritz_module_1.Dimension" %".2"), !dbg !73
  %".4" = sext i32 %".3" to i64 , !dbg !73
  %".5" = icmp ne i64 %".4", 0 , !dbg !73
  br i1 %".5", label %"if.then", label %"if.end", !dbg !73
if.then:
  %".7" = trunc i64 1 to i32 , !dbg !74
  ret i32 %".7", !dbg !74
if.end:
  %".9" = trunc i64 0 to i32 , !dbg !75
  ret i32 %".9", !dbg !75
}

define internal i32 @"test_transform_identity"() !dbg !24
{
entry:
  %".2" = call %"struct.ritz_module_1.Transform" @"transform_identity"(), !dbg !76
  %".3" = extractvalue %"struct.ritz_module_1.Transform" %".2", 0 , !dbg !77
  %".4" = fcmp one double %".3", 0x3ff0000000000000 , !dbg !77
  br i1 %".4", label %"if.then", label %"if.end", !dbg !77
if.then:
  %".6" = trunc i64 1 to i32 , !dbg !78
  ret i32 %".6", !dbg !78
if.end:
  %".8" = extractvalue %"struct.ritz_module_1.Transform" %".2", 3 , !dbg !79
  %".9" = fcmp one double %".8", 0x3ff0000000000000 , !dbg !79
  br i1 %".9", label %"if.then.1", label %"if.end.1", !dbg !79
if.then.1:
  %".11" = trunc i64 2 to i32 , !dbg !80
  ret i32 %".11", !dbg !80
if.end.1:
  %".13" = extractvalue %"struct.ritz_module_1.Transform" %".2", 1 , !dbg !81
  %".14" = fcmp one double %".13",              0x0 , !dbg !81
  br i1 %".14", label %"if.then.2", label %"if.end.2", !dbg !81
if.then.2:
  %".16" = trunc i64 3 to i32 , !dbg !82
  ret i32 %".16", !dbg !82
if.end.2:
  %".18" = extractvalue %"struct.ritz_module_1.Transform" %".2", 2 , !dbg !83
  %".19" = fcmp one double %".18",              0x0 , !dbg !83
  br i1 %".19", label %"if.then.3", label %"if.end.3", !dbg !83
if.then.3:
  %".21" = trunc i64 4 to i32 , !dbg !84
  ret i32 %".21", !dbg !84
if.end.3:
  %".23" = extractvalue %"struct.ritz_module_1.Transform" %".2", 4 , !dbg !85
  %".24" = fcmp one double %".23",              0x0 , !dbg !85
  br i1 %".24", label %"if.then.4", label %"if.end.4", !dbg !85
if.then.4:
  %".26" = trunc i64 5 to i32 , !dbg !86
  ret i32 %".26", !dbg !86
if.end.4:
  %".28" = extractvalue %"struct.ritz_module_1.Transform" %".2", 5 , !dbg !87
  %".29" = fcmp one double %".28",              0x0 , !dbg !87
  br i1 %".29", label %"if.then.5", label %"if.end.5", !dbg !87
if.then.5:
  %".31" = trunc i64 6 to i32 , !dbg !88
  ret i32 %".31", !dbg !88
if.end.5:
  %".33" = trunc i64 0 to i32 , !dbg !89
  ret i32 %".33", !dbg !89
}

define internal i32 @"test_transform_is_identity"() !dbg !25
{
entry:
  %".2" = call %"struct.ritz_module_1.Transform" @"transform_identity"(), !dbg !90
  %".3" = call i32 @"transform_is_identity"(%"struct.ritz_module_1.Transform" %".2"), !dbg !91
  %".4" = sext i32 %".3" to i64 , !dbg !91
  %".5" = icmp eq i64 %".4", 0 , !dbg !91
  br i1 %".5", label %"if.then", label %"if.end", !dbg !91
if.then:
  %".7" = trunc i64 1 to i32 , !dbg !92
  ret i32 %".7", !dbg !92
if.end:
  %".9" = trunc i64 0 to i32 , !dbg !93
  ret i32 %".9", !dbg !93
}

define internal i32 @"test_transform_translate"() !dbg !26
{
entry:
  %".2" = call %"struct.ritz_module_1.Transform" @"transform_translate"(double 0x4024000000000000, double 0x4034000000000000), !dbg !94
  %".3" = extractvalue %"struct.ritz_module_1.Transform" %".2", 4 , !dbg !95
  %".4" = fcmp one double %".3", 0x4024000000000000 , !dbg !95
  br i1 %".4", label %"if.then", label %"if.end", !dbg !95
if.then:
  %".6" = trunc i64 1 to i32 , !dbg !96
  ret i32 %".6", !dbg !96
if.end:
  %".8" = extractvalue %"struct.ritz_module_1.Transform" %".2", 5 , !dbg !97
  %".9" = fcmp one double %".8", 0x4034000000000000 , !dbg !97
  br i1 %".9", label %"if.then.1", label %"if.end.1", !dbg !97
if.then.1:
  %".11" = trunc i64 2 to i32 , !dbg !98
  ret i32 %".11", !dbg !98
if.end.1:
  %".13" = call i32 @"transform_is_identity"(%"struct.ritz_module_1.Transform" %".2"), !dbg !99
  %".14" = sext i32 %".13" to i64 , !dbg !99
  %".15" = icmp ne i64 %".14", 0 , !dbg !99
  br i1 %".15", label %"if.then.2", label %"if.end.2", !dbg !99
if.then.2:
  %".17" = trunc i64 3 to i32 , !dbg !100
  ret i32 %".17", !dbg !100
if.end.2:
  %".19" = trunc i64 0 to i32 , !dbg !101
  ret i32 %".19", !dbg !101
}

define internal i32 @"test_computed_style_default"() !dbg !27
{
entry:
  %".2" = call %"struct.ritz_module_1.ComputedStyle" @"computed_style_default"(), !dbg !102
  %".3" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".2", 0 , !dbg !103
  %".4" = icmp ne i32 %".3", 1 , !dbg !103
  br i1 %".4", label %"if.then", label %"if.end", !dbg !103
if.then:
  %".6" = trunc i64 1 to i32 , !dbg !104
  ret i32 %".6", !dbg !104
if.end:
  %".8" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".2", 1 , !dbg !105
  %".9" = icmp ne i32 %".8", 0 , !dbg !105
  br i1 %".9", label %"if.then.1", label %"if.end.1", !dbg !105
if.then.1:
  %".11" = trunc i64 2 to i32 , !dbg !106
  ret i32 %".11", !dbg !106
if.end.1:
  %".13" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".2", 19 , !dbg !107
  %".14" = fcmp one double %".13", 0x3ff0000000000000 , !dbg !107
  br i1 %".14", label %"if.then.2", label %"if.end.2", !dbg !107
if.then.2:
  %".16" = trunc i64 3 to i32 , !dbg !108
  ret i32 %".16", !dbg !108
if.end.2:
  %".18" = extractvalue %"struct.ritz_module_1.ComputedStyle" %".2", 16 , !dbg !109
  %".19" = extractvalue %"struct.ritz_module_1.TextStyle" %".18", 0 , !dbg !109
  %".20" = fcmp one double %".19", 0x4030000000000000 , !dbg !109
  br i1 %".20", label %"if.then.3", label %"if.end.3", !dbg !109
if.then.3:
  %".22" = trunc i64 4 to i32 , !dbg !110
  ret i32 %".22", !dbg !110
if.end.3:
  %".24" = trunc i64 0 to i32 , !dbg !111
  ret i32 %".24", !dbg !111
}

define internal i32 @"run_test"(i8* %"name.arg", i32 ()* %"f.arg") !dbg !28
{
entry:
  %"name" = alloca i8*
  store i8* %"name.arg", i8** %"name"
  call void @"llvm.dbg.declare"(metadata i8** %"name", metadata !113, metadata !7), !dbg !114
  %"f" = alloca i32 ()*
  store i32 ()* %"f.arg", i32 ()** %"f"
  %".7" = load i8*, i8** %"name", !dbg !115
  %".8" = call i32 @"prints_cstr"(i8* %".7"), !dbg !115
  %".9" = getelementptr [3 x i8], [3 x i8]* @".str.0", i64 0, i64 0 , !dbg !116
  %".10" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".9", 0 , !dbg !116
  %".11" = insertvalue %"struct.ritz_module_1.StrView" %".10", i64 2, 1 , !dbg !116
  %".12" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".11"), !dbg !116
  %".13" = load i32 ()*, i32 ()** %"f", !dbg !117
  %".14" = call i32 %".13"(), !dbg !117
  %".15" = sext i32 %".14" to i64 , !dbg !118
  %".16" = icmp eq i64 %".15", 0 , !dbg !118
  br i1 %".16", label %"if.then", label %"if.else", !dbg !118
if.then:
  %".18" = getelementptr [6 x i8], [6 x i8]* @".str.1", i64 0, i64 0 , !dbg !119
  %".19" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".18", 0 , !dbg !119
  %".20" = insertvalue %"struct.ritz_module_1.StrView" %".19", i64 5, 1 , !dbg !119
  %".21" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".20"), !dbg !119
  %".22" = trunc i64 0 to i32 , !dbg !120
  ret i32 %".22", !dbg !120
if.else:
  %".24" = getelementptr [13 x i8], [13 x i8]* @".str.2", i64 0, i64 0 , !dbg !121
  %".25" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".24", 0 , !dbg !121
  %".26" = insertvalue %"struct.ritz_module_1.StrView" %".25", i64 12, 1 , !dbg !121
  %".27" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".26"), !dbg !121
  %".28" = sext i32 %".14" to i64 , !dbg !122
  %".29" = call i32 @"print_i64"(i64 %".28"), !dbg !122
  %".30" = getelementptr [3 x i8], [3 x i8]* @".str.3", i64 0, i64 0 , !dbg !123
  %".31" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".30", 0 , !dbg !123
  %".32" = insertvalue %"struct.ritz_module_1.StrView" %".31", i64 2, 1 , !dbg !123
  %".33" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".32"), !dbg !123
  %".34" = trunc i64 1 to i32 , !dbg !124
  ret i32 %".34", !dbg !124
if.end:
  ret i32 0, !dbg !124
}

define i32 @"main"() !dbg !29
{
entry:
  %"failed.addr" = alloca i32, !dbg !126
  %".2" = getelementptr [31 x i8], [31 x i8]* @".str.4", i64 0, i64 0 , !dbg !125
  %".3" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".2", 0 , !dbg !125
  %".4" = insertvalue %"struct.ritz_module_1.StrView" %".3", i64 30, 1 , !dbg !125
  %".5" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".4"), !dbg !125
  %".6" = trunc i64 0 to i32 , !dbg !126
  store i32 %".6", i32* %"failed.addr", !dbg !126
  call void @"llvm.dbg.declare"(metadata i32* %"failed.addr", metadata !127, metadata !7), !dbg !128
  %".9" = load i32, i32* %"failed.addr", !dbg !129
  %".10" = getelementptr [17 x i8], [17 x i8]* @".str.5", i64 0, i64 0 , !dbg !129
  %".11" = call i32 @"run_test"(i8* %".10", i32 ()* @"test_node_id_new"), !dbg !129
  %".12" = add i32 %".9", %".11", !dbg !129
  store i32 %".12", i32* %"failed.addr", !dbg !129
  %".14" = load i32, i32* %"failed.addr", !dbg !130
  %".15" = getelementptr [21 x i8], [21 x i8]* @".str.6", i64 0, i64 0 , !dbg !130
  %".16" = call i32 @"run_test"(i8* %".15", i32 ()* @"test_node_id_invalid"), !dbg !130
  %".17" = add i32 %".14", %".16", !dbg !130
  store i32 %".17", i32* %"failed.addr", !dbg !130
  %".19" = load i32, i32* %"failed.addr", !dbg !131
  %".20" = getelementptr [19 x i8], [19 x i8]* @".str.7", i64 0, i64 0 , !dbg !131
  %".21" = call i32 @"run_test"(i8* %".20", i32 ()* @"test_node_id_valid"), !dbg !131
  %".22" = add i32 %".19", %".21", !dbg !131
  store i32 %".22", i32* %"failed.addr", !dbg !131
  %".24" = load i32, i32* %"failed.addr", !dbg !132
  %".25" = getelementptr [18 x i8], [18 x i8]* @".str.8", i64 0, i64 0 , !dbg !132
  %".26" = call i32 @"run_test"(i8* %".25", i32 ()* @"test_dimension_px"), !dbg !132
  %".27" = add i32 %".24", %".26", !dbg !132
  store i32 %".27", i32* %"failed.addr", !dbg !132
  %".29" = load i32, i32* %"failed.addr", !dbg !133
  %".30" = getelementptr [23 x i8], [23 x i8]* @".str.9", i64 0, i64 0 , !dbg !133
  %".31" = call i32 @"run_test"(i8* %".30", i32 ()* @"test_dimension_percent"), !dbg !133
  %".32" = add i32 %".29", %".31", !dbg !133
  store i32 %".32", i32* %"failed.addr", !dbg !133
  %".34" = load i32, i32* %"failed.addr", !dbg !134
  %".35" = getelementptr [20 x i8], [20 x i8]* @".str.10", i64 0, i64 0 , !dbg !134
  %".36" = call i32 @"run_test"(i8* %".35", i32 ()* @"test_dimension_auto"), !dbg !134
  %".37" = add i32 %".34", %".36", !dbg !134
  store i32 %".37", i32* %"failed.addr", !dbg !134
  %".39" = load i32, i32* %"failed.addr", !dbg !135
  %".40" = getelementptr [29 x i8], [29 x i8]* @".str.11", i64 0, i64 0 , !dbg !135
  %".41" = call i32 @"run_test"(i8* %".40", i32 ()* @"test_dimension_is_auto_false"), !dbg !135
  %".42" = add i32 %".39", %".41", !dbg !135
  store i32 %".42", i32* %"failed.addr", !dbg !135
  %".44" = load i32, i32* %"failed.addr", !dbg !136
  %".45" = getelementptr [24 x i8], [24 x i8]* @".str.12", i64 0, i64 0 , !dbg !136
  %".46" = call i32 @"run_test"(i8* %".45", i32 ()* @"test_transform_identity"), !dbg !136
  %".47" = add i32 %".44", %".46", !dbg !136
  store i32 %".47", i32* %"failed.addr", !dbg !136
  %".49" = load i32, i32* %"failed.addr", !dbg !137
  %".50" = getelementptr [27 x i8], [27 x i8]* @".str.13", i64 0, i64 0 , !dbg !137
  %".51" = call i32 @"run_test"(i8* %".50", i32 ()* @"test_transform_is_identity"), !dbg !137
  %".52" = add i32 %".49", %".51", !dbg !137
  store i32 %".52", i32* %"failed.addr", !dbg !137
  %".54" = load i32, i32* %"failed.addr", !dbg !138
  %".55" = getelementptr [25 x i8], [25 x i8]* @".str.14", i64 0, i64 0 , !dbg !138
  %".56" = call i32 @"run_test"(i8* %".55", i32 ()* @"test_transform_translate"), !dbg !138
  %".57" = add i32 %".54", %".56", !dbg !138
  store i32 %".57", i32* %"failed.addr", !dbg !138
  %".59" = load i32, i32* %"failed.addr", !dbg !139
  %".60" = getelementptr [28 x i8], [28 x i8]* @".str.15", i64 0, i64 0 , !dbg !139
  %".61" = call i32 @"run_test"(i8* %".60", i32 ()* @"test_computed_style_default"), !dbg !139
  %".62" = add i32 %".59", %".61", !dbg !139
  store i32 %".62", i32* %"failed.addr", !dbg !139
  %".64" = getelementptr [2 x i8], [2 x i8]* @".str.16", i64 0, i64 0 , !dbg !140
  %".65" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".64", 0 , !dbg !140
  %".66" = insertvalue %"struct.ritz_module_1.StrView" %".65", i64 1, 1 , !dbg !140
  %".67" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".66"), !dbg !140
  %".68" = load i32, i32* %"failed.addr", !dbg !141
  %".69" = sext i32 %".68" to i64 , !dbg !141
  %".70" = icmp eq i64 %".69", 0 , !dbg !141
  br i1 %".70", label %"if.then", label %"if.else", !dbg !141
if.then:
  %".72" = getelementptr [19 x i8], [19 x i8]* @".str.17", i64 0, i64 0 , !dbg !142
  %".73" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".72", 0 , !dbg !142
  %".74" = insertvalue %"struct.ritz_module_1.StrView" %".73", i64 18, 1 , !dbg !142
  %".75" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".74"), !dbg !142
  %".76" = trunc i64 0 to i32 , !dbg !143
  ret i32 %".76", !dbg !143
if.else:
  %".78" = getelementptr [9 x i8], [9 x i8]* @".str.18", i64 0, i64 0 , !dbg !144
  %".79" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".78", 0 , !dbg !144
  %".80" = insertvalue %"struct.ritz_module_1.StrView" %".79", i64 8, 1 , !dbg !144
  %".81" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".80"), !dbg !144
  %".82" = load i32, i32* %"failed.addr", !dbg !145
  %".83" = sext i32 %".82" to i64 , !dbg !145
  %".84" = call i32 @"print_i64"(i64 %".83"), !dbg !145
  %".85" = getelementptr [17 x i8], [17 x i8]* @".str.19", i64 0, i64 0 , !dbg !146
  %".86" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".85", 0 , !dbg !146
  %".87" = insertvalue %"struct.ritz_module_1.StrView" %".86", i64 16, 1 , !dbg !146
  %".88" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".87"), !dbg !146
  %".89" = trunc i64 1 to i32 , !dbg !147
  ret i32 %".89", !dbg !147
if.end:
  ret i32 0, !dbg !147
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !30
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !150
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !148, metadata !7), !dbg !149
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !152, metadata !7), !dbg !153
  %".6" = load i64, i64* %"cap", !dbg !154
  %".7" = icmp sle i64 %".6", 0 , !dbg !154
  br i1 %".7", label %"if.then", label %"if.end", !dbg !154
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !155
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !155
  store i8* null, i8** %".10", !dbg !155
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !156
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !156
  store i64 0, i64* %".13", !dbg !156
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !157
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !157
  store i64 0, i64* %".16", !dbg !157
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !158
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !158
if.end:
  %".20" = load i64, i64* %"cap", !dbg !159
  %".21" = mul i64 %".20", 1, !dbg !159
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !160
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !160
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !160
  store i8* %".22", i8** %".24", !dbg !160
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !161
  %".27" = load i8*, i8** %".26", !dbg !161
  %".28" = icmp eq i8* %".27", null , !dbg !161
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !161
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !162
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !162
  store i64 0, i64* %".31", !dbg !162
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !163
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !163
  store i64 0, i64* %".34", !dbg !163
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !164
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !164
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !165
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !165
  store i64 0, i64* %".39", !dbg !165
  %".41" = load i64, i64* %"cap", !dbg !166
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !166
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !166
  store i64 %".41", i64* %".43", !dbg !166
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !167
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !167
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !31
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !169, metadata !7), !dbg !170
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !171, metadata !7), !dbg !170
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !172
  %".8" = load i8*, i8** %".7", !dbg !172
  %".9" = load i64, i64* %"idx", !dbg !172
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !172
  %".11" = load i8, i8* %".10", !dbg !172
  ret i8 %".11", !dbg !172
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !32
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !173
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !174, metadata !7), !dbg !175
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !176
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !176
  store i8* null, i8** %".4", !dbg !176
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !177
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !177
  store i64 0, i64* %".7", !dbg !177
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !178
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !178
  store i64 0, i64* %".10", !dbg !178
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !179
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !179
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !33
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !185
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !180, metadata !7), !dbg !181
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !182, metadata !7), !dbg !181
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !183
  %".8" = load i64, i64* %".7", !dbg !183
  %".9" = load i64, i64* %"needed", !dbg !183
  %".10" = icmp sge i64 %".8", %".9" , !dbg !183
  br i1 %".10", label %"if.then", label %"if.end", !dbg !183
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !184
  ret i32 %".12", !dbg !184
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !185
  %".15" = load i64, i64* %".14", !dbg !185
  store i64 %".15", i64* %"new_cap.addr", !dbg !185
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !186, metadata !7), !dbg !187
  %".18" = load i64, i64* %"new_cap.addr", !dbg !188
  %".19" = icmp eq i64 %".18", 0 , !dbg !188
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !188
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !189
  br label %"if.end.1", !dbg !189
if.end.1:
  br label %"while.cond", !dbg !190
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !190
  %".25" = load i64, i64* %"needed", !dbg !190
  %".26" = icmp slt i64 %".24", %".25" , !dbg !190
  br i1 %".26", label %"while.body", label %"while.end", !dbg !190
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !191
  %".29" = mul i64 %".28", 2, !dbg !191
  store i64 %".29", i64* %"new_cap.addr", !dbg !191
  br label %"while.cond", !dbg !191
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !192
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !192
  ret i32 %".33", !dbg !192
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !34
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !195, metadata !7), !dbg !196
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !198, metadata !7), !dbg !196
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !199
  %".8" = load i64, i64* %".7", !dbg !199
  %".9" = add i64 %".8", 1, !dbg !199
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !199
  %".11" = sext i32 %".10" to i64 , !dbg !199
  %".12" = icmp ne i64 %".11", 0 , !dbg !199
  br i1 %".12", label %"if.then", label %"if.end", !dbg !199
if.then:
  %".14" = sub i64 0, 1, !dbg !200
  %".15" = trunc i64 %".14" to i32 , !dbg !200
  ret i32 %".15", !dbg !200
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !201
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !201
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !201
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !201
  %".21" = load i64, i64* %".20", !dbg !201
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !201
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !201
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !202
  %".25" = load i64, i64* %".24", !dbg !202
  %".26" = add i64 %".25", 1, !dbg !202
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !202
  store i64 %".26", i64* %".27", !dbg !202
  %".29" = trunc i64 0 to i32 , !dbg !203
  ret i32 %".29", !dbg !203
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !35
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !204, metadata !7), !dbg !205
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !206
  %".5" = load i8*, i8** %".4", !dbg !206
  %".6" = icmp ne i8* %".5", null , !dbg !206
  br i1 %".6", label %"if.then", label %"if.end", !dbg !206
if.then:
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !206
  %".9" = load i8*, i8** %".8", !dbg !206
  %".10" = call i32 @"free"(i8* %".9"), !dbg !206
  br label %"if.end", !dbg !206
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !207
  store i8* null, i8** %".12", !dbg !207
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !208
  store i64 0, i64* %".14", !dbg !208
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !209
  store i64 0, i64* %".16", !dbg !209
  ret i32 0, !dbg !209
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !36
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !210, metadata !7), !dbg !211
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !212
  store i64 0, i64* %".4", !dbg !212
  ret i32 0, !dbg !212
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !37
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !213, metadata !7), !dbg !214
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !215, metadata !7), !dbg !214
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !216, metadata !7), !dbg !214
  %".10" = load i8, i8* %"item", !dbg !217
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !217
  %".12" = load i8*, i8** %".11", !dbg !217
  %".13" = load i64, i64* %"idx", !dbg !217
  %".14" = getelementptr i8, i8* %".12", i64 %".13" , !dbg !217
  store i8 %".10", i8* %".14", !dbg !217
  %".16" = trunc i64 0 to i32 , !dbg !218
  ret i32 %".16", !dbg !218
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !38
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !219, metadata !7), !dbg !220
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !221
  %".5" = load i64, i64* %".4", !dbg !221
  %".6" = sub i64 %".5", 1, !dbg !221
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !221
  store i64 %".6", i64* %".7", !dbg !221
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !222
  %".10" = load i8*, i8** %".9", !dbg !222
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !222
  %".12" = load i64, i64* %".11", !dbg !222
  %".13" = getelementptr i8, i8* %".10", i64 %".12" , !dbg !222
  %".14" = load i8, i8* %".13", !dbg !222
  ret i8 %".14", !dbg !222
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !39
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !223, metadata !7), !dbg !224
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !225, metadata !7), !dbg !224
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !226
  %".8" = load i64, i64* %".7", !dbg !226
  %".9" = add i64 %".8", 1, !dbg !226
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !226
  %".11" = sext i32 %".10" to i64 , !dbg !226
  %".12" = icmp ne i64 %".11", 0 , !dbg !226
  br i1 %".12", label %"if.then", label %"if.end", !dbg !226
if.then:
  %".14" = sub i64 0, 1, !dbg !227
  %".15" = trunc i64 %".14" to i32 , !dbg !227
  ret i32 %".15", !dbg !227
if.end:
  %".17" = load i8, i8* %"item", !dbg !228
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !228
  %".19" = load i8*, i8** %".18", !dbg !228
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !228
  %".21" = load i64, i64* %".20", !dbg !228
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !228
  store i8 %".17", i8* %".22", !dbg !228
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !229
  %".25" = load i64, i64* %".24", !dbg !229
  %".26" = add i64 %".25", 1, !dbg !229
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !229
  store i64 %".26", i64* %".27", !dbg !229
  %".29" = trunc i64 0 to i32 , !dbg !230
  ret i32 %".29", !dbg !230
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !40
{
entry:
  %"i" = alloca i64, !dbg !235
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !231, metadata !7), !dbg !232
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !233, metadata !7), !dbg !232
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !234, metadata !7), !dbg !232
  %".10" = load i64, i64* %"len", !dbg !235
  store i64 0, i64* %"i", !dbg !235
  br label %"for.cond", !dbg !235
for.cond:
  %".13" = load i64, i64* %"i", !dbg !235
  %".14" = icmp slt i64 %".13", %".10" , !dbg !235
  br i1 %".14", label %"for.body", label %"for.end", !dbg !235
for.body:
  %".16" = load i8*, i8** %"data", !dbg !235
  %".17" = load i64, i64* %"i", !dbg !235
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !235
  %".19" = load i8, i8* %".18", !dbg !235
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !235
  %".21" = sext i32 %".20" to i64 , !dbg !235
  %".22" = icmp ne i64 %".21", 0 , !dbg !235
  br i1 %".22", label %"if.then", label %"if.end", !dbg !235
for.incr:
  %".28" = load i64, i64* %"i", !dbg !236
  %".29" = add i64 %".28", 1, !dbg !236
  store i64 %".29", i64* %"i", !dbg !236
  br label %"for.cond", !dbg !236
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !237
  ret i32 %".32", !dbg !237
if.then:
  %".24" = sub i64 0, 1, !dbg !236
  %".25" = trunc i64 %".24" to i32 , !dbg !236
  ret i32 %".25", !dbg !236
if.end:
  br label %"for.incr", !dbg !236
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !41
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !243
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !238, metadata !7), !dbg !239
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !240, metadata !7), !dbg !239
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !241
  %".8" = load i64, i64* %".7", !dbg !241
  %".9" = load i64, i64* %"needed", !dbg !241
  %".10" = icmp sge i64 %".8", %".9" , !dbg !241
  br i1 %".10", label %"if.then", label %"if.end", !dbg !241
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !242
  ret i32 %".12", !dbg !242
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !243
  %".15" = load i64, i64* %".14", !dbg !243
  store i64 %".15", i64* %"new_cap.addr", !dbg !243
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !244, metadata !7), !dbg !245
  %".18" = load i64, i64* %"new_cap.addr", !dbg !246
  %".19" = icmp eq i64 %".18", 0 , !dbg !246
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !246
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !247
  br label %"if.end.1", !dbg !247
if.end.1:
  br label %"while.cond", !dbg !248
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !248
  %".25" = load i64, i64* %"needed", !dbg !248
  %".26" = icmp slt i64 %".24", %".25" , !dbg !248
  br i1 %".26", label %"while.body", label %"while.end", !dbg !248
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !249
  %".29" = mul i64 %".28", 2, !dbg !249
  store i64 %".29", i64* %"new_cap.addr", !dbg !249
  br label %"while.cond", !dbg !249
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !250
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !250
  ret i32 %".33", !dbg !250
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !42
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !251, metadata !7), !dbg !252
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !253, metadata !7), !dbg !252
  %".7" = load i64, i64* %"new_cap", !dbg !254
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !254
  %".9" = load i64, i64* %".8", !dbg !254
  %".10" = icmp sle i64 %".7", %".9" , !dbg !254
  br i1 %".10", label %"if.then", label %"if.end", !dbg !254
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !255
  ret i32 %".12", !dbg !255
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !256
  %".15" = mul i64 %".14", 1, !dbg !256
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !257
  %".17" = load i8*, i8** %".16", !dbg !257
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !257
  %".19" = icmp eq i8* %".18", null , !dbg !258
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !258
if.then.1:
  %".21" = sub i64 0, 1, !dbg !259
  %".22" = trunc i64 %".21" to i32 , !dbg !259
  ret i32 %".22", !dbg !259
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !260
  store i8* %".18", i8** %".24", !dbg !260
  %".26" = load i64, i64* %"new_cap", !dbg !261
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !261
  store i64 %".26", i64* %".27", !dbg !261
  %".29" = trunc i64 0 to i32 , !dbg !262
  ret i32 %".29", !dbg !262
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !43
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !263, metadata !7), !dbg !264
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !265, metadata !7), !dbg !264
  %".7" = load i64, i64* %"new_cap", !dbg !266
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !266
  %".9" = load i64, i64* %".8", !dbg !266
  %".10" = icmp sle i64 %".7", %".9" , !dbg !266
  br i1 %".10", label %"if.then", label %"if.end", !dbg !266
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !267
  ret i32 %".12", !dbg !267
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !268
  %".15" = mul i64 %".14", 16, !dbg !268
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !269
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !269
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !269
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !269
  %".20" = icmp eq i8* %".19", null , !dbg !270
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !270
if.then.1:
  %".22" = sub i64 0, 1, !dbg !271
  %".23" = trunc i64 %".22" to i32 , !dbg !271
  ret i32 %".23", !dbg !271
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !272
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !272
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !272
  %".28" = load i64, i64* %"new_cap", !dbg !273
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !273
  store i64 %".28", i64* %".29", !dbg !273
  %".31" = trunc i64 0 to i32 , !dbg !274
  ret i32 %".31", !dbg !274
}

@".str.0" = private constant [3 x i8] c": \00"
@".str.1" = private constant [6 x i8] c"PASS\0a\00"
@".str.2" = private constant [13 x i8] c"FAIL (code: \00"
@".str.3" = private constant [3 x i8] c")\0a\00"
@".str.4" = private constant [31 x i8] c"Running style types tests...\0a\0a\00"
@".str.5" = private constant [17 x i8] c"test_node_id_new\00"
@".str.6" = private constant [21 x i8] c"test_node_id_invalid\00"
@".str.7" = private constant [19 x i8] c"test_node_id_valid\00"
@".str.8" = private constant [18 x i8] c"test_dimension_px\00"
@".str.9" = private constant [23 x i8] c"test_dimension_percent\00"
@".str.10" = private constant [20 x i8] c"test_dimension_auto\00"
@".str.11" = private constant [29 x i8] c"test_dimension_is_auto_false\00"
@".str.12" = private constant [24 x i8] c"test_transform_identity\00"
@".str.13" = private constant [27 x i8] c"test_transform_is_identity\00"
@".str.14" = private constant [25 x i8] c"test_transform_translate\00"
@".str.15" = private constant [28 x i8] c"test_computed_style_default\00"
@".str.16" = private constant [2 x i8] c"\0a\00"
@".str.17" = private constant [19 x i8] c"All tests passed!\0a\00"
@".str.18" = private constant [9 x i8] c"FAILED: \00"
@".str.19" = private constant [17 x i8] c" test(s) failed\0a\00"
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 12, name: "test_node_id_new", scopeLine: 12, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 19, name: "test_node_id_invalid", scopeLine: 19, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 26, name: "test_node_id_valid", scopeLine: 26, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 37, name: "test_dimension_px", scopeLine: 37, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 46, name: "test_dimension_percent", scopeLine: 46, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 55, name: "test_dimension_auto", scopeLine: 55, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 62, name: "test_dimension_is_auto_false", scopeLine: 62, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 73, name: "test_transform_identity", scopeLine: 73, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 90, name: "test_transform_is_identity", scopeLine: 90, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 97, name: "test_transform_translate", scopeLine: 97, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 112, name: "test_computed_style_default", scopeLine: 112, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 137, name: "run_test", scopeLine: 137, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 150, name: "main", scopeLine: 150, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!44 = !DILocation(column: 5, line: 13, scope: !17)
!45 = !DILocation(column: 5, line: 14, scope: !17)
!46 = !DILocation(column: 9, line: 15, scope: !17)
!47 = !DILocation(column: 5, line: 16, scope: !17)
!48 = !DILocation(column: 5, line: 20, scope: !18)
!49 = !DILocation(column: 5, line: 21, scope: !18)
!50 = !DILocation(column: 9, line: 22, scope: !18)
!51 = !DILocation(column: 5, line: 23, scope: !18)
!52 = !DILocation(column: 5, line: 27, scope: !19)
!53 = !DILocation(column: 5, line: 28, scope: !19)
!54 = !DILocation(column: 9, line: 29, scope: !19)
!55 = !DILocation(column: 5, line: 30, scope: !19)
!56 = !DILocation(column: 5, line: 38, scope: !20)
!57 = !DILocation(column: 5, line: 39, scope: !20)
!58 = !DILocation(column: 9, line: 40, scope: !20)
!59 = !DILocation(column: 5, line: 41, scope: !20)
!60 = !DILocation(column: 9, line: 42, scope: !20)
!61 = !DILocation(column: 5, line: 43, scope: !20)
!62 = !DILocation(column: 5, line: 47, scope: !21)
!63 = !DILocation(column: 5, line: 48, scope: !21)
!64 = !DILocation(column: 9, line: 49, scope: !21)
!65 = !DILocation(column: 5, line: 50, scope: !21)
!66 = !DILocation(column: 9, line: 51, scope: !21)
!67 = !DILocation(column: 5, line: 52, scope: !21)
!68 = !DILocation(column: 5, line: 56, scope: !22)
!69 = !DILocation(column: 5, line: 57, scope: !22)
!70 = !DILocation(column: 9, line: 58, scope: !22)
!71 = !DILocation(column: 5, line: 59, scope: !22)
!72 = !DILocation(column: 5, line: 63, scope: !23)
!73 = !DILocation(column: 5, line: 64, scope: !23)
!74 = !DILocation(column: 9, line: 65, scope: !23)
!75 = !DILocation(column: 5, line: 66, scope: !23)
!76 = !DILocation(column: 5, line: 74, scope: !24)
!77 = !DILocation(column: 5, line: 75, scope: !24)
!78 = !DILocation(column: 9, line: 76, scope: !24)
!79 = !DILocation(column: 5, line: 77, scope: !24)
!80 = !DILocation(column: 9, line: 78, scope: !24)
!81 = !DILocation(column: 5, line: 79, scope: !24)
!82 = !DILocation(column: 9, line: 80, scope: !24)
!83 = !DILocation(column: 5, line: 81, scope: !24)
!84 = !DILocation(column: 9, line: 82, scope: !24)
!85 = !DILocation(column: 5, line: 83, scope: !24)
!86 = !DILocation(column: 9, line: 84, scope: !24)
!87 = !DILocation(column: 5, line: 85, scope: !24)
!88 = !DILocation(column: 9, line: 86, scope: !24)
!89 = !DILocation(column: 5, line: 87, scope: !24)
!90 = !DILocation(column: 5, line: 91, scope: !25)
!91 = !DILocation(column: 5, line: 92, scope: !25)
!92 = !DILocation(column: 9, line: 93, scope: !25)
!93 = !DILocation(column: 5, line: 94, scope: !25)
!94 = !DILocation(column: 5, line: 98, scope: !26)
!95 = !DILocation(column: 5, line: 99, scope: !26)
!96 = !DILocation(column: 9, line: 100, scope: !26)
!97 = !DILocation(column: 5, line: 101, scope: !26)
!98 = !DILocation(column: 9, line: 102, scope: !26)
!99 = !DILocation(column: 5, line: 103, scope: !26)
!100 = !DILocation(column: 9, line: 104, scope: !26)
!101 = !DILocation(column: 5, line: 105, scope: !26)
!102 = !DILocation(column: 5, line: 113, scope: !27)
!103 = !DILocation(column: 5, line: 116, scope: !27)
!104 = !DILocation(column: 9, line: 117, scope: !27)
!105 = !DILocation(column: 5, line: 120, scope: !27)
!106 = !DILocation(column: 9, line: 121, scope: !27)
!107 = !DILocation(column: 5, line: 124, scope: !27)
!108 = !DILocation(column: 9, line: 125, scope: !27)
!109 = !DILocation(column: 5, line: 128, scope: !27)
!110 = !DILocation(column: 9, line: 129, scope: !27)
!111 = !DILocation(column: 5, line: 131, scope: !27)
!112 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!113 = !DILocalVariable(file: !0, line: 137, name: "name", scope: !28, type: !112)
!114 = !DILocation(column: 1, line: 137, scope: !28)
!115 = !DILocation(column: 5, line: 138, scope: !28)
!116 = !DILocation(column: 5, line: 139, scope: !28)
!117 = !DILocation(column: 5, line: 140, scope: !28)
!118 = !DILocation(column: 5, line: 141, scope: !28)
!119 = !DILocation(column: 9, line: 142, scope: !28)
!120 = !DILocation(column: 9, line: 143, scope: !28)
!121 = !DILocation(column: 9, line: 145, scope: !28)
!122 = !DILocation(column: 9, line: 146, scope: !28)
!123 = !DILocation(column: 9, line: 147, scope: !28)
!124 = !DILocation(column: 9, line: 148, scope: !28)
!125 = !DILocation(column: 5, line: 151, scope: !29)
!126 = !DILocation(column: 5, line: 153, scope: !29)
!127 = !DILocalVariable(file: !0, line: 153, name: "failed", scope: !29, type: !10)
!128 = !DILocation(column: 1, line: 153, scope: !29)
!129 = !DILocation(column: 5, line: 154, scope: !29)
!130 = !DILocation(column: 5, line: 155, scope: !29)
!131 = !DILocation(column: 5, line: 156, scope: !29)
!132 = !DILocation(column: 5, line: 157, scope: !29)
!133 = !DILocation(column: 5, line: 158, scope: !29)
!134 = !DILocation(column: 5, line: 159, scope: !29)
!135 = !DILocation(column: 5, line: 160, scope: !29)
!136 = !DILocation(column: 5, line: 161, scope: !29)
!137 = !DILocation(column: 5, line: 162, scope: !29)
!138 = !DILocation(column: 5, line: 163, scope: !29)
!139 = !DILocation(column: 5, line: 164, scope: !29)
!140 = !DILocation(column: 5, line: 166, scope: !29)
!141 = !DILocation(column: 5, line: 167, scope: !29)
!142 = !DILocation(column: 9, line: 168, scope: !29)
!143 = !DILocation(column: 9, line: 169, scope: !29)
!144 = !DILocation(column: 9, line: 171, scope: !29)
!145 = !DILocation(column: 9, line: 172, scope: !29)
!146 = !DILocation(column: 9, line: 173, scope: !29)
!147 = !DILocation(column: 9, line: 174, scope: !29)
!148 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !30, type: !11)
!149 = !DILocation(column: 1, line: 124, scope: !30)
!150 = !DILocation(column: 5, line: 125, scope: !30)
!151 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!152 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !30, type: !151)
!153 = !DILocation(column: 1, line: 125, scope: !30)
!154 = !DILocation(column: 5, line: 126, scope: !30)
!155 = !DILocation(column: 9, line: 127, scope: !30)
!156 = !DILocation(column: 9, line: 128, scope: !30)
!157 = !DILocation(column: 9, line: 129, scope: !30)
!158 = !DILocation(column: 9, line: 130, scope: !30)
!159 = !DILocation(column: 5, line: 132, scope: !30)
!160 = !DILocation(column: 5, line: 133, scope: !30)
!161 = !DILocation(column: 5, line: 134, scope: !30)
!162 = !DILocation(column: 9, line: 135, scope: !30)
!163 = !DILocation(column: 9, line: 136, scope: !30)
!164 = !DILocation(column: 9, line: 137, scope: !30)
!165 = !DILocation(column: 5, line: 139, scope: !30)
!166 = !DILocation(column: 5, line: 140, scope: !30)
!167 = !DILocation(column: 5, line: 141, scope: !30)
!168 = !DIDerivedType(baseType: !151, size: 64, tag: DW_TAG_reference_type)
!169 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !31, type: !168)
!170 = !DILocation(column: 1, line: 225, scope: !31)
!171 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !31, type: !11)
!172 = !DILocation(column: 5, line: 226, scope: !31)
!173 = !DILocation(column: 5, line: 117, scope: !32)
!174 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !32, type: !151)
!175 = !DILocation(column: 1, line: 117, scope: !32)
!176 = !DILocation(column: 5, line: 118, scope: !32)
!177 = !DILocation(column: 5, line: 119, scope: !32)
!178 = !DILocation(column: 5, line: 120, scope: !32)
!179 = !DILocation(column: 5, line: 121, scope: !32)
!180 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !33, type: !168)
!181 = !DILocation(column: 1, line: 193, scope: !33)
!182 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !33, type: !11)
!183 = !DILocation(column: 5, line: 194, scope: !33)
!184 = !DILocation(column: 9, line: 195, scope: !33)
!185 = !DILocation(column: 5, line: 197, scope: !33)
!186 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !33, type: !11)
!187 = !DILocation(column: 1, line: 197, scope: !33)
!188 = !DILocation(column: 5, line: 198, scope: !33)
!189 = !DILocation(column: 9, line: 199, scope: !33)
!190 = !DILocation(column: 5, line: 200, scope: !33)
!191 = !DILocation(column: 9, line: 201, scope: !33)
!192 = !DILocation(column: 5, line: 203, scope: !33)
!193 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!194 = !DIDerivedType(baseType: !193, size: 64, tag: DW_TAG_reference_type)
!195 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !34, type: !194)
!196 = !DILocation(column: 1, line: 210, scope: !34)
!197 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!198 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !34, type: !197)
!199 = !DILocation(column: 5, line: 211, scope: !34)
!200 = !DILocation(column: 9, line: 212, scope: !34)
!201 = !DILocation(column: 5, line: 213, scope: !34)
!202 = !DILocation(column: 5, line: 214, scope: !34)
!203 = !DILocation(column: 5, line: 215, scope: !34)
!204 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !35, type: !168)
!205 = !DILocation(column: 1, line: 148, scope: !35)
!206 = !DILocation(column: 5, line: 149, scope: !35)
!207 = !DILocation(column: 5, line: 151, scope: !35)
!208 = !DILocation(column: 5, line: 152, scope: !35)
!209 = !DILocation(column: 5, line: 153, scope: !35)
!210 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !36, type: !168)
!211 = !DILocation(column: 1, line: 244, scope: !36)
!212 = !DILocation(column: 5, line: 245, scope: !36)
!213 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !37, type: !168)
!214 = !DILocation(column: 1, line: 235, scope: !37)
!215 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !37, type: !11)
!216 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !37, type: !12)
!217 = !DILocation(column: 5, line: 236, scope: !37)
!218 = !DILocation(column: 5, line: 237, scope: !37)
!219 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !38, type: !168)
!220 = !DILocation(column: 1, line: 219, scope: !38)
!221 = !DILocation(column: 5, line: 220, scope: !38)
!222 = !DILocation(column: 5, line: 221, scope: !38)
!223 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !39, type: !168)
!224 = !DILocation(column: 1, line: 210, scope: !39)
!225 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !39, type: !12)
!226 = !DILocation(column: 5, line: 211, scope: !39)
!227 = !DILocation(column: 9, line: 212, scope: !39)
!228 = !DILocation(column: 5, line: 213, scope: !39)
!229 = !DILocation(column: 5, line: 214, scope: !39)
!230 = !DILocation(column: 5, line: 215, scope: !39)
!231 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !40, type: !168)
!232 = !DILocation(column: 1, line: 288, scope: !40)
!233 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !40, type: !112)
!234 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !40, type: !11)
!235 = !DILocation(column: 5, line: 289, scope: !40)
!236 = !DILocation(column: 13, line: 291, scope: !40)
!237 = !DILocation(column: 5, line: 292, scope: !40)
!238 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !41, type: !194)
!239 = !DILocation(column: 1, line: 193, scope: !41)
!240 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !41, type: !11)
!241 = !DILocation(column: 5, line: 194, scope: !41)
!242 = !DILocation(column: 9, line: 195, scope: !41)
!243 = !DILocation(column: 5, line: 197, scope: !41)
!244 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !41, type: !11)
!245 = !DILocation(column: 1, line: 197, scope: !41)
!246 = !DILocation(column: 5, line: 198, scope: !41)
!247 = !DILocation(column: 9, line: 199, scope: !41)
!248 = !DILocation(column: 5, line: 200, scope: !41)
!249 = !DILocation(column: 9, line: 201, scope: !41)
!250 = !DILocation(column: 5, line: 203, scope: !41)
!251 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !42, type: !168)
!252 = !DILocation(column: 1, line: 179, scope: !42)
!253 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !42, type: !11)
!254 = !DILocation(column: 5, line: 180, scope: !42)
!255 = !DILocation(column: 9, line: 181, scope: !42)
!256 = !DILocation(column: 5, line: 183, scope: !42)
!257 = !DILocation(column: 5, line: 184, scope: !42)
!258 = !DILocation(column: 5, line: 185, scope: !42)
!259 = !DILocation(column: 9, line: 186, scope: !42)
!260 = !DILocation(column: 5, line: 188, scope: !42)
!261 = !DILocation(column: 5, line: 189, scope: !42)
!262 = !DILocation(column: 5, line: 190, scope: !42)
!263 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !43, type: !194)
!264 = !DILocation(column: 1, line: 179, scope: !43)
!265 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !43, type: !11)
!266 = !DILocation(column: 5, line: 180, scope: !43)
!267 = !DILocation(column: 9, line: 181, scope: !43)
!268 = !DILocation(column: 5, line: 183, scope: !43)
!269 = !DILocation(column: 5, line: 184, scope: !43)
!270 = !DILocation(column: 5, line: 185, scope: !43)
!271 = !DILocation(column: 9, line: 186, scope: !43)
!272 = !DILocation(column: 5, line: 188, scope: !43)
!273 = !DILocation(column: 5, line: 189, scope: !43)
!274 = !DILocation(column: 5, line: 190, scope: !43)