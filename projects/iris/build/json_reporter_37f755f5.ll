; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Vec$LineBounds" = type {%"struct.ritz_module_1.LineBounds"*, i64, i64}
%"struct.ritz_module_1.Vec$u8" = type {i8*, i64, i64}
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
%"struct.ritz_module_1.JsonTestResult" = type {%"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView", i64, i32, i32}
declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

@"BLOCK_SIZES" = internal constant [9 x i64] [i64 32, i64 48, i64 80, i64 144, i64 272, i64 528, i64 1040, i64 2064, i64 0]
@"g_alloc" = internal global %"struct.ritz_module_1.GlobalAlloc" zeroinitializer
@"g_json_results" = internal global [1024 x %"struct.ritz_module_1.JsonTestResult"] zeroinitializer
@"g_json_result_count" = internal global i32 0
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

define %"struct.ritz_module_1.StrView" @"status_pass"() !dbg !17
{
entry:
  %".2" = getelementptr [5 x i8], [5 x i8]* @".str.0", i64 0, i64 0 , !dbg !46
  %".3" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".2"), !dbg !46
  ret %"struct.ritz_module_1.StrView" %".3", !dbg !46
}

define %"struct.ritz_module_1.StrView" @"status_fail"() !dbg !18
{
entry:
  %".2" = getelementptr [5 x i8], [5 x i8]* @".str.1", i64 0, i64 0 , !dbg !47
  %".3" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".2"), !dbg !47
  ret %"struct.ritz_module_1.StrView" %".3", !dbg !47
}

define %"struct.ritz_module_1.StrView" @"status_crash"() !dbg !19
{
entry:
  %".2" = getelementptr [6 x i8], [6 x i8]* @".str.2", i64 0, i64 0 , !dbg !48
  %".3" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".2"), !dbg !48
  ret %"struct.ritz_module_1.StrView" %".3", !dbg !48
}

define %"struct.ritz_module_1.StrView" @"status_timeout"() !dbg !20
{
entry:
  %".2" = getelementptr [8 x i8], [8 x i8]* @".str.3", i64 0, i64 0 , !dbg !49
  %".3" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".2"), !dbg !49
  ret %"struct.ritz_module_1.StrView" %".3", !dbg !49
}

define %"struct.ritz_module_1.StrView" @"status_skip"() !dbg !21
{
entry:
  %".2" = getelementptr [5 x i8], [5 x i8]* @".str.4", i64 0, i64 0 , !dbg !50
  %".3" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".2"), !dbg !50
  ret %"struct.ritz_module_1.StrView" %".3", !dbg !50
}

define i32 @"json_record_result"(%"struct.ritz_module_1.StrView"* %"name.arg", %"struct.ritz_module_1.StrView"* %"status.arg", i64 %"duration_ms.arg", i32 %"exit_code.arg", i32 %"signal.arg") !dbg !22
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name.arg", metadata !53, metadata !7), !dbg !54
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"status.arg", metadata !55, metadata !7), !dbg !54
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !56, metadata !7), !dbg !54
  %"exit_code" = alloca i32
  store i32 %"exit_code.arg", i32* %"exit_code"
  call void @"llvm.dbg.declare"(metadata i32* %"exit_code", metadata !57, metadata !7), !dbg !54
  %"signal" = alloca i32
  store i32 %"signal.arg", i32* %"signal"
  call void @"llvm.dbg.declare"(metadata i32* %"signal", metadata !58, metadata !7), !dbg !54
  %".15" = load i32, i32* @"g_json_result_count", !dbg !59
  %".16" = sext i32 %".15" to i64 , !dbg !59
  %".17" = icmp sge i64 %".16", 1024 , !dbg !59
  br i1 %".17", label %"if.then", label %"if.end", !dbg !59
if.then:
  ret i32 0, !dbg !60
if.end:
  %".20" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name.arg", !dbg !61
  %".21" = load i32, i32* @"g_json_result_count", !dbg !61
  %".22" = getelementptr [1024 x %"struct.ritz_module_1.JsonTestResult"], [1024 x %"struct.ritz_module_1.JsonTestResult"]* @"g_json_results", i32 0, i32 %".21" , !dbg !61
  %".23" = load %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".22", !dbg !61
  %".24" = load i32, i32* @"g_json_result_count", !dbg !61
  %".25" = getelementptr [1024 x %"struct.ritz_module_1.JsonTestResult"], [1024 x %"struct.ritz_module_1.JsonTestResult"]* @"g_json_results", i32 0, i32 %".24" , !dbg !61
  %".26" = getelementptr %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".25", i32 0, i32 0 , !dbg !61
  store %"struct.ritz_module_1.StrView" %".20", %"struct.ritz_module_1.StrView"* %".26", !dbg !61
  %".28" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"status.arg", !dbg !62
  %".29" = load i32, i32* @"g_json_result_count", !dbg !62
  %".30" = getelementptr [1024 x %"struct.ritz_module_1.JsonTestResult"], [1024 x %"struct.ritz_module_1.JsonTestResult"]* @"g_json_results", i32 0, i32 %".29" , !dbg !62
  %".31" = load %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".30", !dbg !62
  %".32" = load i32, i32* @"g_json_result_count", !dbg !62
  %".33" = getelementptr [1024 x %"struct.ritz_module_1.JsonTestResult"], [1024 x %"struct.ritz_module_1.JsonTestResult"]* @"g_json_results", i32 0, i32 %".32" , !dbg !62
  %".34" = getelementptr %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".33", i32 0, i32 1 , !dbg !62
  store %"struct.ritz_module_1.StrView" %".28", %"struct.ritz_module_1.StrView"* %".34", !dbg !62
  %".36" = load i64, i64* %"duration_ms", !dbg !63
  %".37" = load i32, i32* @"g_json_result_count", !dbg !63
  %".38" = getelementptr [1024 x %"struct.ritz_module_1.JsonTestResult"], [1024 x %"struct.ritz_module_1.JsonTestResult"]* @"g_json_results", i32 0, i32 %".37" , !dbg !63
  %".39" = load %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".38", !dbg !63
  %".40" = load i32, i32* @"g_json_result_count", !dbg !63
  %".41" = getelementptr [1024 x %"struct.ritz_module_1.JsonTestResult"], [1024 x %"struct.ritz_module_1.JsonTestResult"]* @"g_json_results", i32 0, i32 %".40" , !dbg !63
  %".42" = getelementptr %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".41", i32 0, i32 2 , !dbg !63
  store i64 %".36", i64* %".42", !dbg !63
  %".44" = load i32, i32* %"exit_code", !dbg !64
  %".45" = load i32, i32* @"g_json_result_count", !dbg !64
  %".46" = getelementptr [1024 x %"struct.ritz_module_1.JsonTestResult"], [1024 x %"struct.ritz_module_1.JsonTestResult"]* @"g_json_results", i32 0, i32 %".45" , !dbg !64
  %".47" = load %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".46", !dbg !64
  %".48" = load i32, i32* @"g_json_result_count", !dbg !64
  %".49" = getelementptr [1024 x %"struct.ritz_module_1.JsonTestResult"], [1024 x %"struct.ritz_module_1.JsonTestResult"]* @"g_json_results", i32 0, i32 %".48" , !dbg !64
  %".50" = getelementptr %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".49", i32 0, i32 3 , !dbg !64
  store i32 %".44", i32* %".50", !dbg !64
  %".52" = load i32, i32* %"signal", !dbg !65
  %".53" = load i32, i32* @"g_json_result_count", !dbg !65
  %".54" = getelementptr [1024 x %"struct.ritz_module_1.JsonTestResult"], [1024 x %"struct.ritz_module_1.JsonTestResult"]* @"g_json_results", i32 0, i32 %".53" , !dbg !65
  %".55" = load %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".54", !dbg !65
  %".56" = load i32, i32* @"g_json_result_count", !dbg !65
  %".57" = getelementptr [1024 x %"struct.ritz_module_1.JsonTestResult"], [1024 x %"struct.ritz_module_1.JsonTestResult"]* @"g_json_results", i32 0, i32 %".56" , !dbg !65
  %".58" = getelementptr %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".57", i32 0, i32 4 , !dbg !65
  store i32 %".52", i32* %".58", !dbg !65
  %".60" = load i32, i32* @"g_json_result_count", !dbg !66
  %".61" = sext i32 %".60" to i64 , !dbg !66
  %".62" = add i64 %".61", 1, !dbg !66
  %".63" = trunc i64 %".62" to i32 , !dbg !66
  store i32 %".63", i32* @"g_json_result_count", !dbg !66
  ret i32 0, !dbg !66
}

define i32 @"json_record_pass"(%"struct.ritz_module_1.StrView"* %"name.arg", i64 %"duration_ms.arg") !dbg !23
{
entry:
  %"st.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !70
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name.arg", metadata !67, metadata !7), !dbg !68
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !69, metadata !7), !dbg !68
  %".7" = call %"struct.ritz_module_1.StrView" @"status_pass"(), !dbg !70
  store %"struct.ritz_module_1.StrView" %".7", %"struct.ritz_module_1.StrView"* %"st.addr", !dbg !70
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"st.addr", metadata !71, metadata !7), !dbg !72
  %".10" = load i64, i64* %"duration_ms", !dbg !73
  %".11" = trunc i64 0 to i32 , !dbg !73
  %".12" = trunc i64 0 to i32 , !dbg !73
  %".13" = call i32 @"json_record_result"(%"struct.ritz_module_1.StrView"* %"name.arg", %"struct.ritz_module_1.StrView"* %"st.addr", i64 %".10", i32 %".11", i32 %".12"), !dbg !73
  ret i32 %".13", !dbg !73
}

define i32 @"json_record_fail"(%"struct.ritz_module_1.StrView"* %"name.arg", i64 %"duration_ms.arg", i32 %"exit_code.arg") !dbg !24
{
entry:
  %"st.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !78
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name.arg", metadata !74, metadata !7), !dbg !75
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !76, metadata !7), !dbg !75
  %"exit_code" = alloca i32
  store i32 %"exit_code.arg", i32* %"exit_code"
  call void @"llvm.dbg.declare"(metadata i32* %"exit_code", metadata !77, metadata !7), !dbg !75
  %".10" = call %"struct.ritz_module_1.StrView" @"status_fail"(), !dbg !78
  store %"struct.ritz_module_1.StrView" %".10", %"struct.ritz_module_1.StrView"* %"st.addr", !dbg !78
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"st.addr", metadata !79, metadata !7), !dbg !80
  %".13" = load i64, i64* %"duration_ms", !dbg !81
  %".14" = load i32, i32* %"exit_code", !dbg !81
  %".15" = trunc i64 0 to i32 , !dbg !81
  %".16" = call i32 @"json_record_result"(%"struct.ritz_module_1.StrView"* %"name.arg", %"struct.ritz_module_1.StrView"* %"st.addr", i64 %".13", i32 %".14", i32 %".15"), !dbg !81
  ret i32 %".16", !dbg !81
}

define i32 @"json_record_crash"(%"struct.ritz_module_1.StrView"* %"name.arg", i64 %"duration_ms.arg", i32 %"signal.arg") !dbg !25
{
entry:
  %"st.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !86
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name.arg", metadata !82, metadata !7), !dbg !83
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !84, metadata !7), !dbg !83
  %"signal" = alloca i32
  store i32 %"signal.arg", i32* %"signal"
  call void @"llvm.dbg.declare"(metadata i32* %"signal", metadata !85, metadata !7), !dbg !83
  %".10" = call %"struct.ritz_module_1.StrView" @"status_crash"(), !dbg !86
  store %"struct.ritz_module_1.StrView" %".10", %"struct.ritz_module_1.StrView"* %"st.addr", !dbg !86
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"st.addr", metadata !87, metadata !7), !dbg !88
  %".13" = load i64, i64* %"duration_ms", !dbg !89
  %".14" = trunc i64 0 to i32 , !dbg !89
  %".15" = load i32, i32* %"signal", !dbg !89
  %".16" = call i32 @"json_record_result"(%"struct.ritz_module_1.StrView"* %"name.arg", %"struct.ritz_module_1.StrView"* %"st.addr", i64 %".13", i32 %".14", i32 %".15"), !dbg !89
  ret i32 %".16", !dbg !89
}

define i32 @"json_record_timeout"(%"struct.ritz_module_1.StrView"* %"name.arg", i64 %"duration_ms.arg") !dbg !26
{
entry:
  %"st.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !93
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name.arg", metadata !90, metadata !7), !dbg !91
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !92, metadata !7), !dbg !91
  %".7" = call %"struct.ritz_module_1.StrView" @"status_timeout"(), !dbg !93
  store %"struct.ritz_module_1.StrView" %".7", %"struct.ritz_module_1.StrView"* %"st.addr", !dbg !93
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"st.addr", metadata !94, metadata !7), !dbg !95
  %".10" = load i64, i64* %"duration_ms", !dbg !96
  %".11" = trunc i64 0 to i32 , !dbg !96
  %".12" = trunc i64 0 to i32 , !dbg !96
  %".13" = call i32 @"json_record_result"(%"struct.ritz_module_1.StrView"* %"name.arg", %"struct.ritz_module_1.StrView"* %"st.addr", i64 %".10", i32 %".11", i32 %".12"), !dbg !96
  ret i32 %".13", !dbg !96
}

define i32 @"json_print_char"(i8 %"c.arg") !dbg !27
{
entry:
  %"c" = alloca i8
  %"buf.addr" = alloca [2 x i8], !dbg !99
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !97, metadata !7), !dbg !98
  call void @"llvm.dbg.declare"(metadata [2 x i8]* %"buf.addr", metadata !103, metadata !7), !dbg !104
  %".6" = load i8, i8* %"c", !dbg !105
  %".7" = getelementptr [2 x i8], [2 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !105
  store i8 %".6", i8* %".7", !dbg !105
  %".9" = getelementptr [2 x i8], [2 x i8]* %"buf.addr", i32 0, i64 1 , !dbg !106
  %".10" = trunc i64 0 to i8 , !dbg !106
  store i8 %".10", i8* %".9", !dbg !106
  %".12" = getelementptr [2 x i8], [2 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !107
  %".13" = call i32 @"prints_cstr"(i8* %".12"), !dbg !107
  ret i32 %".13", !dbg !107
}

define i32 @"print_quote"() !dbg !28
{
entry:
  %".2" = trunc i64 34 to i8 , !dbg !108
  %".3" = call i32 @"json_print_char"(i8 %".2"), !dbg !108
  ret i32 %".3", !dbg !108
}

define i32 @"print_json_string_sv"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !29
{
entry:
  %"i" = alloca i64, !dbg !112
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !109, metadata !7), !dbg !110
  %".4" = call i32 @"print_quote"(), !dbg !111
  %".5" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !112
  %".6" = load i64, i64* %".5", !dbg !112
  store i64 0, i64* %"i", !dbg !112
  br label %"for.cond", !dbg !112
for.cond:
  %".9" = load i64, i64* %"i", !dbg !112
  %".10" = icmp slt i64 %".9", %".6" , !dbg !112
  br i1 %".10", label %"for.body", label %"for.end", !dbg !112
for.body:
  %".12" = load i64, i64* %"i", !dbg !113
  %".13" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %".12"), !dbg !113
  %".14" = zext i8 %".13" to i64 , !dbg !113
  %".15" = icmp eq i64 %".14", 34 , !dbg !113
  br i1 %".15", label %"if.then", label %"if.else", !dbg !113
for.incr:
  %".56" = load i64, i64* %"i", !dbg !117
  %".57" = add i64 %".56", 1, !dbg !117
  store i64 %".57", i64* %"i", !dbg !117
  br label %"for.cond", !dbg !117
for.end:
  %".60" = call i32 @"print_quote"(), !dbg !118
  ret i32 %".60", !dbg !118
if.then:
  %".17" = trunc i64 92 to i8 , !dbg !114
  %".18" = call i32 @"json_print_char"(i8 %".17"), !dbg !114
  %".19" = trunc i64 34 to i8 , !dbg !114
  %".20" = call i32 @"json_print_char"(i8 %".19"), !dbg !114
  br label %"if.end", !dbg !117
if.else:
  %".21" = zext i8 %".13" to i64 , !dbg !114
  %".22" = icmp eq i64 %".21", 92 , !dbg !114
  br i1 %".22", label %"if.then.1", label %"if.else.1", !dbg !114
if.end:
  %".54" = phi  i32 [%".20", %"if.then"], [%".51", %"if.end.1"] , !dbg !117
  br label %"for.incr", !dbg !117
if.then.1:
  %".24" = trunc i64 92 to i8 , !dbg !115
  %".25" = call i32 @"json_print_char"(i8 %".24"), !dbg !115
  %".26" = trunc i64 92 to i8 , !dbg !115
  %".27" = call i32 @"json_print_char"(i8 %".26"), !dbg !115
  br label %"if.end.1", !dbg !117
if.else.1:
  %".28" = zext i8 %".13" to i64 , !dbg !115
  %".29" = icmp eq i64 %".28", 10 , !dbg !115
  br i1 %".29", label %"if.then.2", label %"if.else.2", !dbg !115
if.end.1:
  %".51" = phi  i32 [%".27", %"if.then.1"], [%".48", %"if.end.2"] , !dbg !117
  br label %"if.end", !dbg !117
if.then.2:
  %".31" = trunc i64 92 to i8 , !dbg !116
  %".32" = call i32 @"json_print_char"(i8 %".31"), !dbg !116
  %".33" = trunc i64 110 to i8 , !dbg !116
  %".34" = call i32 @"json_print_char"(i8 %".33"), !dbg !116
  br label %"if.end.2", !dbg !117
if.else.2:
  %".35" = zext i8 %".13" to i64 , !dbg !116
  %".36" = icmp eq i64 %".35", 9 , !dbg !116
  br i1 %".36", label %"if.then.3", label %"if.else.3", !dbg !116
if.end.2:
  %".48" = phi  i32 [%".34", %"if.then.2"], [%".45", %"if.end.3"] , !dbg !117
  br label %"if.end.1", !dbg !117
if.then.3:
  %".38" = trunc i64 92 to i8 , !dbg !117
  %".39" = call i32 @"json_print_char"(i8 %".38"), !dbg !117
  %".40" = trunc i64 116 to i8 , !dbg !117
  %".41" = call i32 @"json_print_char"(i8 %".40"), !dbg !117
  br label %"if.end.3", !dbg !117
if.else.3:
  %".42" = call i32 @"json_print_char"(i8 %".13"), !dbg !117
  br label %"if.end.3", !dbg !117
if.end.3:
  %".45" = phi  i32 [%".41", %"if.then.3"], [%".42", %"if.else.3"] , !dbg !117
  br label %"if.end.2", !dbg !117
}

define i32 @"json_print_report"(i32 %"total.arg", i32 %"passed.arg", i32 %"failed.arg", i32 %"crashed.arg", i32 %"timeout.arg", i32 %"skipped.arg", i64 %"duration_ms.arg") !dbg !30
{
entry:
  %"total" = alloca i32
  %"i" = alloca i32, !dbg !146
  store i32 %"total.arg", i32* %"total"
  call void @"llvm.dbg.declare"(metadata i32* %"total", metadata !119, metadata !7), !dbg !120
  %"passed" = alloca i32
  store i32 %"passed.arg", i32* %"passed"
  call void @"llvm.dbg.declare"(metadata i32* %"passed", metadata !121, metadata !7), !dbg !120
  %"failed" = alloca i32
  store i32 %"failed.arg", i32* %"failed"
  call void @"llvm.dbg.declare"(metadata i32* %"failed", metadata !122, metadata !7), !dbg !120
  %"crashed" = alloca i32
  store i32 %"crashed.arg", i32* %"crashed"
  call void @"llvm.dbg.declare"(metadata i32* %"crashed", metadata !123, metadata !7), !dbg !120
  %"timeout" = alloca i32
  store i32 %"timeout.arg", i32* %"timeout"
  call void @"llvm.dbg.declare"(metadata i32* %"timeout", metadata !124, metadata !7), !dbg !120
  %"skipped" = alloca i32
  store i32 %"skipped.arg", i32* %"skipped"
  call void @"llvm.dbg.declare"(metadata i32* %"skipped", metadata !125, metadata !7), !dbg !120
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !126, metadata !7), !dbg !120
  %".23" = getelementptr [3 x i8], [3 x i8]* @".str.5", i64 0, i64 0 , !dbg !127
  %".24" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".23", 0 , !dbg !127
  %".25" = insertvalue %"struct.ritz_module_1.StrView" %".24", i64 2, 1 , !dbg !127
  %".26" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".25"), !dbg !127
  %".27" = getelementptr [23 x i8], [23 x i8]* @".str.6", i64 0, i64 0 , !dbg !128
  %".28" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".27", 0 , !dbg !128
  %".29" = insertvalue %"struct.ritz_module_1.StrView" %".28", i64 22, 1 , !dbg !128
  %".30" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".29"), !dbg !128
  %".31" = getelementptr [16 x i8], [16 x i8]* @".str.7", i64 0, i64 0 , !dbg !129
  %".32" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".31", 0 , !dbg !129
  %".33" = insertvalue %"struct.ritz_module_1.StrView" %".32", i64 15, 1 , !dbg !129
  %".34" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".33"), !dbg !129
  %".35" = getelementptr [14 x i8], [14 x i8]* @".str.8", i64 0, i64 0 , !dbg !130
  %".36" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".35", 0 , !dbg !130
  %".37" = insertvalue %"struct.ritz_module_1.StrView" %".36", i64 13, 1 , !dbg !130
  %".38" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".37"), !dbg !130
  %".39" = load i32, i32* %"total", !dbg !131
  %".40" = sext i32 %".39" to i64 , !dbg !131
  %".41" = call i32 @"print_int"(i64 %".40"), !dbg !131
  %".42" = getelementptr [17 x i8], [17 x i8]* @".str.9", i64 0, i64 0 , !dbg !132
  %".43" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".42", 0 , !dbg !132
  %".44" = insertvalue %"struct.ritz_module_1.StrView" %".43", i64 16, 1 , !dbg !132
  %".45" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".44"), !dbg !132
  %".46" = load i32, i32* %"passed", !dbg !133
  %".47" = sext i32 %".46" to i64 , !dbg !133
  %".48" = call i32 @"print_int"(i64 %".47"), !dbg !133
  %".49" = getelementptr [17 x i8], [17 x i8]* @".str.10", i64 0, i64 0 , !dbg !134
  %".50" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".49", 0 , !dbg !134
  %".51" = insertvalue %"struct.ritz_module_1.StrView" %".50", i64 16, 1 , !dbg !134
  %".52" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".51"), !dbg !134
  %".53" = load i32, i32* %"failed", !dbg !135
  %".54" = sext i32 %".53" to i64 , !dbg !135
  %".55" = call i32 @"print_int"(i64 %".54"), !dbg !135
  %".56" = getelementptr [18 x i8], [18 x i8]* @".str.11", i64 0, i64 0 , !dbg !136
  %".57" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".56", 0 , !dbg !136
  %".58" = insertvalue %"struct.ritz_module_1.StrView" %".57", i64 17, 1 , !dbg !136
  %".59" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".58"), !dbg !136
  %".60" = load i32, i32* %"crashed", !dbg !137
  %".61" = sext i32 %".60" to i64 , !dbg !137
  %".62" = call i32 @"print_int"(i64 %".61"), !dbg !137
  %".63" = getelementptr [18 x i8], [18 x i8]* @".str.12", i64 0, i64 0 , !dbg !138
  %".64" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".63", 0 , !dbg !138
  %".65" = insertvalue %"struct.ritz_module_1.StrView" %".64", i64 17, 1 , !dbg !138
  %".66" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".65"), !dbg !138
  %".67" = load i32, i32* %"timeout", !dbg !139
  %".68" = sext i32 %".67" to i64 , !dbg !139
  %".69" = call i32 @"print_int"(i64 %".68"), !dbg !139
  %".70" = getelementptr [18 x i8], [18 x i8]* @".str.13", i64 0, i64 0 , !dbg !140
  %".71" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".70", 0 , !dbg !140
  %".72" = insertvalue %"struct.ritz_module_1.StrView" %".71", i64 17, 1 , !dbg !140
  %".73" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".72"), !dbg !140
  %".74" = load i32, i32* %"skipped", !dbg !141
  %".75" = sext i32 %".74" to i64 , !dbg !141
  %".76" = call i32 @"print_int"(i64 %".75"), !dbg !141
  %".77" = getelementptr [22 x i8], [22 x i8]* @".str.14", i64 0, i64 0 , !dbg !142
  %".78" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".77", 0 , !dbg !142
  %".79" = insertvalue %"struct.ritz_module_1.StrView" %".78", i64 21, 1 , !dbg !142
  %".80" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".79"), !dbg !142
  %".81" = load i64, i64* %"duration_ms", !dbg !143
  %".82" = call i32 @"print_int"(i64 %".81"), !dbg !143
  %".83" = getelementptr [7 x i8], [7 x i8]* @".str.15", i64 0, i64 0 , !dbg !144
  %".84" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".83", 0 , !dbg !144
  %".85" = insertvalue %"struct.ritz_module_1.StrView" %".84", i64 6, 1 , !dbg !144
  %".86" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".85"), !dbg !144
  %".87" = getelementptr [14 x i8], [14 x i8]* @".str.16", i64 0, i64 0 , !dbg !145
  %".88" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".87", 0 , !dbg !145
  %".89" = insertvalue %"struct.ritz_module_1.StrView" %".88", i64 13, 1 , !dbg !145
  %".90" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".89"), !dbg !145
  %".91" = load i32, i32* @"g_json_result_count", !dbg !146
  store i32 0, i32* %"i", !dbg !146
  br label %"for.cond", !dbg !146
for.cond:
  %".94" = load i32, i32* %"i", !dbg !146
  %".95" = icmp slt i32 %".94", %".91" , !dbg !146
  br i1 %".95", label %"for.body", label %"for.end", !dbg !146
for.body:
  %".97" = load i32, i32* %"i", !dbg !147
  %".98" = getelementptr [1024 x %"struct.ritz_module_1.JsonTestResult"], [1024 x %"struct.ritz_module_1.JsonTestResult"]* @"g_json_results", i32 0, i32 %".97" , !dbg !147
  %".99" = getelementptr [14 x i8], [14 x i8]* @".str.17", i64 0, i64 0 , !dbg !148
  %".100" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".99", 0 , !dbg !148
  %".101" = insertvalue %"struct.ritz_module_1.StrView" %".100", i64 13, 1 , !dbg !148
  %".102" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".101"), !dbg !148
  %".103" = getelementptr %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".98", i32 0, i32 0 , !dbg !149
  %".104" = call i32 @"print_json_string_sv"(%"struct.ritz_module_1.StrView"* %".103"), !dbg !149
  %".105" = getelementptr [13 x i8], [13 x i8]* @".str.18", i64 0, i64 0 , !dbg !150
  %".106" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".105", 0 , !dbg !150
  %".107" = insertvalue %"struct.ritz_module_1.StrView" %".106", i64 12, 1 , !dbg !150
  %".108" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".107"), !dbg !150
  %".109" = getelementptr %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".98", i32 0, i32 1 , !dbg !151
  %".110" = call i32 @"print_json_string_sv"(%"struct.ritz_module_1.StrView"* %".109"), !dbg !151
  %".111" = getelementptr [18 x i8], [18 x i8]* @".str.19", i64 0, i64 0 , !dbg !152
  %".112" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".111", 0 , !dbg !152
  %".113" = insertvalue %"struct.ritz_module_1.StrView" %".112", i64 17, 1 , !dbg !152
  %".114" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".113"), !dbg !152
  %".115" = getelementptr %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".98", i32 0, i32 2 , !dbg !153
  %".116" = load i64, i64* %".115", !dbg !153
  %".117" = call i32 @"print_int"(i64 %".116"), !dbg !153
  %".118" = getelementptr %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".98", i32 0, i32 3 , !dbg !154
  %".119" = load i32, i32* %".118", !dbg !154
  %".120" = sext i32 %".119" to i64 , !dbg !154
  %".121" = icmp ne i64 %".120", 0 , !dbg !154
  br i1 %".121", label %"if.then", label %"if.end", !dbg !154
for.incr:
  %".167" = load i32, i32* %"i", !dbg !159
  %".168" = add i32 %".167", 1, !dbg !159
  store i32 %".168", i32* %"i", !dbg !159
  br label %"for.cond", !dbg !159
for.end:
  %".171" = getelementptr [5 x i8], [5 x i8]* @".str.25", i64 0, i64 0 , !dbg !160
  %".172" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".171", 0 , !dbg !160
  %".173" = insertvalue %"struct.ritz_module_1.StrView" %".172", i64 4, 1 , !dbg !160
  %".174" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".173"), !dbg !160
  %".175" = getelementptr [3 x i8], [3 x i8]* @".str.26", i64 0, i64 0 , !dbg !161
  %".176" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".175", 0 , !dbg !161
  %".177" = insertvalue %"struct.ritz_module_1.StrView" %".176", i64 2, 1 , !dbg !161
  %".178" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".177"), !dbg !161
  ret i32 %".178", !dbg !161
if.then:
  %".123" = getelementptr [16 x i8], [16 x i8]* @".str.20", i64 0, i64 0 , !dbg !155
  %".124" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".123", 0 , !dbg !155
  %".125" = insertvalue %"struct.ritz_module_1.StrView" %".124", i64 15, 1 , !dbg !155
  %".126" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".125"), !dbg !155
  %".127" = getelementptr %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".98", i32 0, i32 3 , !dbg !155
  %".128" = load i32, i32* %".127", !dbg !155
  %".129" = sext i32 %".128" to i64 , !dbg !155
  %".130" = call i32 @"print_int"(i64 %".129"), !dbg !155
  br label %"if.end", !dbg !155
if.end:
  %".132" = getelementptr %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".98", i32 0, i32 4 , !dbg !156
  %".133" = load i32, i32* %".132", !dbg !156
  %".134" = sext i32 %".133" to i64 , !dbg !156
  %".135" = icmp ne i64 %".134", 0 , !dbg !156
  br i1 %".135", label %"if.then.1", label %"if.end.1", !dbg !156
if.then.1:
  %".137" = getelementptr [13 x i8], [13 x i8]* @".str.21", i64 0, i64 0 , !dbg !157
  %".138" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".137", 0 , !dbg !157
  %".139" = insertvalue %"struct.ritz_module_1.StrView" %".138", i64 12, 1 , !dbg !157
  %".140" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".139"), !dbg !157
  %".141" = getelementptr %"struct.ritz_module_1.JsonTestResult", %"struct.ritz_module_1.JsonTestResult"* %".98", i32 0, i32 4 , !dbg !157
  %".142" = load i32, i32* %".141", !dbg !157
  %".143" = sext i32 %".142" to i64 , !dbg !157
  %".144" = call i32 @"print_int"(i64 %".143"), !dbg !157
  br label %"if.end.1", !dbg !157
if.end.1:
  %".146" = getelementptr [2 x i8], [2 x i8]* @".str.22", i64 0, i64 0 , !dbg !158
  %".147" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".146", 0 , !dbg !158
  %".148" = insertvalue %"struct.ritz_module_1.StrView" %".147", i64 1, 1 , !dbg !158
  %".149" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".148"), !dbg !158
  %".150" = load i32, i32* %"i", !dbg !159
  %".151" = load i32, i32* @"g_json_result_count", !dbg !159
  %".152" = sext i32 %".151" to i64 , !dbg !159
  %".153" = sub i64 %".152", 1, !dbg !159
  %".154" = sext i32 %".150" to i64 , !dbg !159
  %".155" = icmp slt i64 %".154", %".153" , !dbg !159
  br i1 %".155", label %"if.then.2", label %"if.end.2", !dbg !159
if.then.2:
  %".157" = getelementptr [2 x i8], [2 x i8]* @".str.23", i64 0, i64 0 , !dbg !159
  %".158" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".157", 0 , !dbg !159
  %".159" = insertvalue %"struct.ritz_module_1.StrView" %".158", i64 1, 1 , !dbg !159
  %".160" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".159"), !dbg !159
  br label %"if.end.2", !dbg !159
if.end.2:
  %".162" = getelementptr [2 x i8], [2 x i8]* @".str.24", i64 0, i64 0 , !dbg !159
  %".163" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".162", 0 , !dbg !159
  %".164" = insertvalue %"struct.ritz_module_1.StrView" %".163", i64 1, 1 , !dbg !159
  %".165" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".164"), !dbg !159
  br label %"for.incr", !dbg !159
}

define i32 @"json_reset"() !dbg !31
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !162
  store i32 %".2", i32* @"g_json_result_count", !dbg !162
  ret i32 0, !dbg !162
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !32
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !165, metadata !7), !dbg !166
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !168, metadata !7), !dbg !166
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !169
  %".8" = load i64, i64* %".7", !dbg !169
  %".9" = add i64 %".8", 1, !dbg !169
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !169
  %".11" = sext i32 %".10" to i64 , !dbg !169
  %".12" = icmp ne i64 %".11", 0 , !dbg !169
  br i1 %".12", label %"if.then", label %"if.end", !dbg !169
if.then:
  %".14" = sub i64 0, 1, !dbg !170
  %".15" = trunc i64 %".14" to i32 , !dbg !170
  ret i32 %".15", !dbg !170
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !171
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !171
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !171
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !171
  %".21" = load i64, i64* %".20", !dbg !171
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !171
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !171
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !172
  %".25" = load i64, i64* %".24", !dbg !172
  %".26" = add i64 %".25", 1, !dbg !172
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !172
  store i64 %".26", i64* %".27", !dbg !172
  %".29" = trunc i64 0 to i32 , !dbg !173
  ret i32 %".29", !dbg !173
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !33
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !176, metadata !7), !dbg !177
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !178
  store i64 0, i64* %".4", !dbg !178
  ret i32 0, !dbg !178
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !34
{
entry:
  %"i" = alloca i64, !dbg !184
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !179, metadata !7), !dbg !180
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !182, metadata !7), !dbg !180
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !183, metadata !7), !dbg !180
  %".10" = load i64, i64* %"len", !dbg !184
  store i64 0, i64* %"i", !dbg !184
  br label %"for.cond", !dbg !184
for.cond:
  %".13" = load i64, i64* %"i", !dbg !184
  %".14" = icmp slt i64 %".13", %".10" , !dbg !184
  br i1 %".14", label %"for.body", label %"for.end", !dbg !184
for.body:
  %".16" = load i8*, i8** %"data", !dbg !184
  %".17" = load i64, i64* %"i", !dbg !184
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !184
  %".19" = load i8, i8* %".18", !dbg !184
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !184
  %".21" = sext i32 %".20" to i64 , !dbg !184
  %".22" = icmp ne i64 %".21", 0 , !dbg !184
  br i1 %".22", label %"if.then", label %"if.end", !dbg !184
for.incr:
  %".28" = load i64, i64* %"i", !dbg !185
  %".29" = add i64 %".28", 1, !dbg !185
  store i64 %".29", i64* %"i", !dbg !185
  br label %"for.cond", !dbg !185
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !186
  ret i32 %".32", !dbg !186
if.then:
  %".24" = sub i64 0, 1, !dbg !185
  %".25" = trunc i64 %".24" to i32 , !dbg !185
  ret i32 %".25", !dbg !185
if.end:
  br label %"for.incr", !dbg !185
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !35
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !187, metadata !7), !dbg !188
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !189, metadata !7), !dbg !188
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !190
  %".8" = load i8*, i8** %".7", !dbg !190
  %".9" = load i64, i64* %"idx", !dbg !190
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !190
  %".11" = load i8, i8* %".10", !dbg !190
  ret i8 %".11", !dbg !190
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !36
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !191, metadata !7), !dbg !192
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !193
  %".5" = load i8*, i8** %".4", !dbg !193
  %".6" = icmp ne i8* %".5", null , !dbg !193
  br i1 %".6", label %"if.then", label %"if.end", !dbg !193
if.then:
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !193
  %".9" = load i8*, i8** %".8", !dbg !193
  %".10" = call i32 @"free"(i8* %".9"), !dbg !193
  br label %"if.end", !dbg !193
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !194
  store i8* null, i8** %".12", !dbg !194
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !195
  store i64 0, i64* %".14", !dbg !195
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !196
  store i64 0, i64* %".16", !dbg !196
  ret i32 0, !dbg !196
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !37
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !199
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !197, metadata !7), !dbg !198
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !200, metadata !7), !dbg !201
  %".6" = load i64, i64* %"cap", !dbg !202
  %".7" = icmp sle i64 %".6", 0 , !dbg !202
  br i1 %".7", label %"if.then", label %"if.end", !dbg !202
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !203
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !203
  store i8* null, i8** %".10", !dbg !203
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !204
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !204
  store i64 0, i64* %".13", !dbg !204
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !205
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !205
  store i64 0, i64* %".16", !dbg !205
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !206
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !206
if.end:
  %".20" = load i64, i64* %"cap", !dbg !207
  %".21" = mul i64 %".20", 1, !dbg !207
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !208
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !208
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !208
  store i8* %".22", i8** %".24", !dbg !208
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !209
  %".27" = load i8*, i8** %".26", !dbg !209
  %".28" = icmp eq i8* %".27", null , !dbg !209
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !209
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !210
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !210
  store i64 0, i64* %".31", !dbg !210
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !211
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !211
  store i64 0, i64* %".34", !dbg !211
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !212
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !212
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !213
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !213
  store i64 0, i64* %".39", !dbg !213
  %".41" = load i64, i64* %"cap", !dbg !214
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !214
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !214
  store i64 %".41", i64* %".43", !dbg !214
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !215
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !215
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !38
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !221
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !216, metadata !7), !dbg !217
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !218, metadata !7), !dbg !217
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !219
  %".8" = load i64, i64* %".7", !dbg !219
  %".9" = load i64, i64* %"needed", !dbg !219
  %".10" = icmp sge i64 %".8", %".9" , !dbg !219
  br i1 %".10", label %"if.then", label %"if.end", !dbg !219
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !220
  ret i32 %".12", !dbg !220
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !221
  %".15" = load i64, i64* %".14", !dbg !221
  store i64 %".15", i64* %"new_cap.addr", !dbg !221
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !222, metadata !7), !dbg !223
  %".18" = load i64, i64* %"new_cap.addr", !dbg !224
  %".19" = icmp eq i64 %".18", 0 , !dbg !224
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !224
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !225
  br label %"if.end.1", !dbg !225
if.end.1:
  br label %"while.cond", !dbg !226
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !226
  %".25" = load i64, i64* %"needed", !dbg !226
  %".26" = icmp slt i64 %".24", %".25" , !dbg !226
  br i1 %".26", label %"while.body", label %"while.end", !dbg !226
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !227
  %".29" = mul i64 %".28", 2, !dbg !227
  store i64 %".29", i64* %"new_cap.addr", !dbg !227
  br label %"while.cond", !dbg !227
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !228
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !228
  ret i32 %".33", !dbg !228
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !39
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !229, metadata !7), !dbg !230
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !231
  %".5" = load i64, i64* %".4", !dbg !231
  %".6" = sub i64 %".5", 1, !dbg !231
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !231
  store i64 %".6", i64* %".7", !dbg !231
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !232
  %".10" = load i8*, i8** %".9", !dbg !232
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !232
  %".12" = load i64, i64* %".11", !dbg !232
  %".13" = getelementptr i8, i8* %".10", i64 %".12" , !dbg !232
  %".14" = load i8, i8* %".13", !dbg !232
  ret i8 %".14", !dbg !232
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !40
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !233
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !234, metadata !7), !dbg !235
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !236
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !236
  store i8* null, i8** %".4", !dbg !236
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !237
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !237
  store i64 0, i64* %".7", !dbg !237
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !238
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !238
  store i64 0, i64* %".10", !dbg !238
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !239
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !239
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !41
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !240, metadata !7), !dbg !241
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !242, metadata !7), !dbg !241
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !243, metadata !7), !dbg !241
  %".10" = load i8, i8* %"item", !dbg !244
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !244
  %".12" = load i8*, i8** %".11", !dbg !244
  %".13" = load i64, i64* %"idx", !dbg !244
  %".14" = getelementptr i8, i8* %".12", i64 %".13" , !dbg !244
  store i8 %".10", i8* %".14", !dbg !244
  %".16" = trunc i64 0 to i32 , !dbg !245
  ret i32 %".16", !dbg !245
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !42
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !246, metadata !7), !dbg !247
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !248, metadata !7), !dbg !247
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !249
  %".8" = load i64, i64* %".7", !dbg !249
  %".9" = add i64 %".8", 1, !dbg !249
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !249
  %".11" = sext i32 %".10" to i64 , !dbg !249
  %".12" = icmp ne i64 %".11", 0 , !dbg !249
  br i1 %".12", label %"if.then", label %"if.end", !dbg !249
if.then:
  %".14" = sub i64 0, 1, !dbg !250
  %".15" = trunc i64 %".14" to i32 , !dbg !250
  ret i32 %".15", !dbg !250
if.end:
  %".17" = load i8, i8* %"item", !dbg !251
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !251
  %".19" = load i8*, i8** %".18", !dbg !251
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !251
  %".21" = load i64, i64* %".20", !dbg !251
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !251
  store i8 %".17", i8* %".22", !dbg !251
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !252
  %".25" = load i64, i64* %".24", !dbg !252
  %".26" = add i64 %".25", 1, !dbg !252
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !252
  store i64 %".26", i64* %".27", !dbg !252
  %".29" = trunc i64 0 to i32 , !dbg !253
  ret i32 %".29", !dbg !253
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !43
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !254, metadata !7), !dbg !255
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !256, metadata !7), !dbg !255
  %".7" = load i64, i64* %"new_cap", !dbg !257
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !257
  %".9" = load i64, i64* %".8", !dbg !257
  %".10" = icmp sle i64 %".7", %".9" , !dbg !257
  br i1 %".10", label %"if.then", label %"if.end", !dbg !257
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !258
  ret i32 %".12", !dbg !258
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !259
  %".15" = mul i64 %".14", 1, !dbg !259
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !260
  %".17" = load i8*, i8** %".16", !dbg !260
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !260
  %".19" = icmp eq i8* %".18", null , !dbg !261
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !261
if.then.1:
  %".21" = sub i64 0, 1, !dbg !262
  %".22" = trunc i64 %".21" to i32 , !dbg !262
  ret i32 %".22", !dbg !262
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !263
  store i8* %".18", i8** %".24", !dbg !263
  %".26" = load i64, i64* %"new_cap", !dbg !264
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !264
  store i64 %".26", i64* %".27", !dbg !264
  %".29" = trunc i64 0 to i32 , !dbg !265
  ret i32 %".29", !dbg !265
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !44
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !271
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !266, metadata !7), !dbg !267
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !268, metadata !7), !dbg !267
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !269
  %".8" = load i64, i64* %".7", !dbg !269
  %".9" = load i64, i64* %"needed", !dbg !269
  %".10" = icmp sge i64 %".8", %".9" , !dbg !269
  br i1 %".10", label %"if.then", label %"if.end", !dbg !269
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !270
  ret i32 %".12", !dbg !270
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !271
  %".15" = load i64, i64* %".14", !dbg !271
  store i64 %".15", i64* %"new_cap.addr", !dbg !271
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !272, metadata !7), !dbg !273
  %".18" = load i64, i64* %"new_cap.addr", !dbg !274
  %".19" = icmp eq i64 %".18", 0 , !dbg !274
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !274
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !275
  br label %"if.end.1", !dbg !275
if.end.1:
  br label %"while.cond", !dbg !276
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !276
  %".25" = load i64, i64* %"needed", !dbg !276
  %".26" = icmp slt i64 %".24", %".25" , !dbg !276
  br i1 %".26", label %"while.body", label %"while.end", !dbg !276
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !277
  %".29" = mul i64 %".28", 2, !dbg !277
  store i64 %".29", i64* %"new_cap.addr", !dbg !277
  br label %"while.cond", !dbg !277
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !278
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !278
  ret i32 %".33", !dbg !278
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !45
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !279, metadata !7), !dbg !280
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !281, metadata !7), !dbg !280
  %".7" = load i64, i64* %"new_cap", !dbg !282
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !282
  %".9" = load i64, i64* %".8", !dbg !282
  %".10" = icmp sle i64 %".7", %".9" , !dbg !282
  br i1 %".10", label %"if.then", label %"if.end", !dbg !282
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !283
  ret i32 %".12", !dbg !283
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !284
  %".15" = mul i64 %".14", 16, !dbg !284
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !285
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !285
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !285
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !285
  %".20" = icmp eq i8* %".19", null , !dbg !286
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !286
if.then.1:
  %".22" = sub i64 0, 1, !dbg !287
  %".23" = trunc i64 %".22" to i32 , !dbg !287
  ret i32 %".23", !dbg !287
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !288
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !288
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !288
  %".28" = load i64, i64* %"new_cap", !dbg !289
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !289
  store i64 %".28", i64* %".29", !dbg !289
  %".31" = trunc i64 0 to i32 , !dbg !290
  ret i32 %".31", !dbg !290
}

@".str.0" = private constant [5 x i8] c"pass\00"
@".str.1" = private constant [5 x i8] c"fail\00"
@".str.2" = private constant [6 x i8] c"crash\00"
@".str.3" = private constant [8 x i8] c"timeout\00"
@".str.4" = private constant [5 x i8] c"skip\00"
@".str.5" = private constant [3 x i8] c"{\0a\00"
@".str.6" = private constant [23 x i8] c"  \22version\22: \220.1.0\22,\0a\00"
@".str.7" = private constant [16 x i8] c"  \22summary\22: {\0a\00"
@".str.8" = private constant [14 x i8] c"    \22total\22: \00"
@".str.9" = private constant [17 x i8] c",\0a    \22passed\22: \00"
@".str.10" = private constant [17 x i8] c",\0a    \22failed\22: \00"
@".str.11" = private constant [18 x i8] c",\0a    \22crashed\22: \00"
@".str.12" = private constant [18 x i8] c",\0a    \22timeout\22: \00"
@".str.13" = private constant [18 x i8] c",\0a    \22skipped\22: \00"
@".str.14" = private constant [22 x i8] c",\0a    \22duration_ms\22: \00"
@".str.15" = private constant [7 x i8] c"\0a  },\0a\00"
@".str.16" = private constant [14 x i8] c"  \22tests\22: [\0a\00"
@".str.17" = private constant [14 x i8] c"    {\22name\22: \00"
@".str.18" = private constant [13 x i8] c", \22status\22: \00"
@".str.19" = private constant [18 x i8] c", \22duration_ms\22: \00"
@".str.20" = private constant [16 x i8] c", \22exit_code\22: \00"
@".str.21" = private constant [13 x i8] c", \22signal\22: \00"
@".str.22" = private constant [2 x i8] c"}\00"
@".str.23" = private constant [2 x i8] c",\00"
@".str.24" = private constant [2 x i8] c"\0a\00"
@".str.25" = private constant [5 x i8] c"  ]\0a\00"
@".str.26" = private constant [3 x i8] c"}\0a\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/ritzunit/src", filename: "json_reporter.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 25, name: "status_pass", scopeLine: 25, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 28, name: "status_fail", scopeLine: 28, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 31, name: "status_crash", scopeLine: 31, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 34, name: "status_timeout", scopeLine: 34, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 37, name: "status_skip", scopeLine: 37, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 56, name: "json_record_result", scopeLine: 56, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 66, name: "json_record_pass", scopeLine: 66, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 70, name: "json_record_fail", scopeLine: 70, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 74, name: "json_record_crash", scopeLine: 74, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 78, name: "json_record_timeout", scopeLine: 78, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 87, name: "json_print_char", scopeLine: 87, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 94, name: "print_quote", scopeLine: 94, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 98, name: "print_json_string_sv", scopeLine: 98, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 123, name: "json_print_report", scopeLine: 123, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 180, name: "json_reset", scopeLine: 180, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!46 = !DILocation(column: 5, line: 26, scope: !17)
!47 = !DILocation(column: 5, line: 29, scope: !18)
!48 = !DILocation(column: 5, line: 32, scope: !19)
!49 = !DILocation(column: 5, line: 35, scope: !20)
!50 = !DILocation(column: 5, line: 38, scope: !21)
!51 = !DICompositeType(align: 64, file: !0, name: "StrView", size: 128, tag: DW_TAG_structure_type)
!52 = !DIDerivedType(baseType: !51, size: 64, tag: DW_TAG_reference_type)
!53 = !DILocalVariable(file: !0, line: 56, name: "name", scope: !22, type: !52)
!54 = !DILocation(column: 1, line: 56, scope: !22)
!55 = !DILocalVariable(file: !0, line: 56, name: "status", scope: !22, type: !52)
!56 = !DILocalVariable(file: !0, line: 56, name: "duration_ms", scope: !22, type: !11)
!57 = !DILocalVariable(file: !0, line: 56, name: "exit_code", scope: !22, type: !10)
!58 = !DILocalVariable(file: !0, line: 56, name: "signal", scope: !22, type: !10)
!59 = !DILocation(column: 5, line: 57, scope: !22)
!60 = !DILocation(column: 9, line: 58, scope: !22)
!61 = !DILocation(column: 5, line: 59, scope: !22)
!62 = !DILocation(column: 5, line: 60, scope: !22)
!63 = !DILocation(column: 5, line: 61, scope: !22)
!64 = !DILocation(column: 5, line: 62, scope: !22)
!65 = !DILocation(column: 5, line: 63, scope: !22)
!66 = !DILocation(column: 5, line: 64, scope: !22)
!67 = !DILocalVariable(file: !0, line: 66, name: "name", scope: !23, type: !52)
!68 = !DILocation(column: 1, line: 66, scope: !23)
!69 = !DILocalVariable(file: !0, line: 66, name: "duration_ms", scope: !23, type: !11)
!70 = !DILocation(column: 5, line: 67, scope: !23)
!71 = !DILocalVariable(file: !0, line: 67, name: "st", scope: !23, type: !51)
!72 = !DILocation(column: 1, line: 67, scope: !23)
!73 = !DILocation(column: 5, line: 68, scope: !23)
!74 = !DILocalVariable(file: !0, line: 70, name: "name", scope: !24, type: !52)
!75 = !DILocation(column: 1, line: 70, scope: !24)
!76 = !DILocalVariable(file: !0, line: 70, name: "duration_ms", scope: !24, type: !11)
!77 = !DILocalVariable(file: !0, line: 70, name: "exit_code", scope: !24, type: !10)
!78 = !DILocation(column: 5, line: 71, scope: !24)
!79 = !DILocalVariable(file: !0, line: 71, name: "st", scope: !24, type: !51)
!80 = !DILocation(column: 1, line: 71, scope: !24)
!81 = !DILocation(column: 5, line: 72, scope: !24)
!82 = !DILocalVariable(file: !0, line: 74, name: "name", scope: !25, type: !52)
!83 = !DILocation(column: 1, line: 74, scope: !25)
!84 = !DILocalVariable(file: !0, line: 74, name: "duration_ms", scope: !25, type: !11)
!85 = !DILocalVariable(file: !0, line: 74, name: "signal", scope: !25, type: !10)
!86 = !DILocation(column: 5, line: 75, scope: !25)
!87 = !DILocalVariable(file: !0, line: 75, name: "st", scope: !25, type: !51)
!88 = !DILocation(column: 1, line: 75, scope: !25)
!89 = !DILocation(column: 5, line: 76, scope: !25)
!90 = !DILocalVariable(file: !0, line: 78, name: "name", scope: !26, type: !52)
!91 = !DILocation(column: 1, line: 78, scope: !26)
!92 = !DILocalVariable(file: !0, line: 78, name: "duration_ms", scope: !26, type: !11)
!93 = !DILocation(column: 5, line: 79, scope: !26)
!94 = !DILocalVariable(file: !0, line: 79, name: "st", scope: !26, type: !51)
!95 = !DILocation(column: 1, line: 79, scope: !26)
!96 = !DILocation(column: 5, line: 80, scope: !26)
!97 = !DILocalVariable(file: !0, line: 87, name: "c", scope: !27, type: !12)
!98 = !DILocation(column: 1, line: 87, scope: !27)
!99 = !DILocation(column: 5, line: 88, scope: !27)
!100 = !DISubrange(count: 2)
!101 = !{ !100 }
!102 = !DICompositeType(baseType: !12, elements: !101, size: 16, tag: DW_TAG_array_type)
!103 = !DILocalVariable(file: !0, line: 88, name: "buf", scope: !27, type: !102)
!104 = !DILocation(column: 1, line: 88, scope: !27)
!105 = !DILocation(column: 5, line: 89, scope: !27)
!106 = !DILocation(column: 5, line: 90, scope: !27)
!107 = !DILocation(column: 5, line: 91, scope: !27)
!108 = !DILocation(column: 5, line: 95, scope: !28)
!109 = !DILocalVariable(file: !0, line: 98, name: "s", scope: !29, type: !52)
!110 = !DILocation(column: 1, line: 98, scope: !29)
!111 = !DILocation(column: 5, line: 99, scope: !29)
!112 = !DILocation(column: 5, line: 100, scope: !29)
!113 = !DILocation(column: 9, line: 101, scope: !29)
!114 = !DILocation(column: 13, line: 103, scope: !29)
!115 = !DILocation(column: 13, line: 106, scope: !29)
!116 = !DILocation(column: 13, line: 109, scope: !29)
!117 = !DILocation(column: 13, line: 112, scope: !29)
!118 = !DILocation(column: 5, line: 116, scope: !29)
!119 = !DILocalVariable(file: !0, line: 123, name: "total", scope: !30, type: !10)
!120 = !DILocation(column: 1, line: 123, scope: !30)
!121 = !DILocalVariable(file: !0, line: 123, name: "passed", scope: !30, type: !10)
!122 = !DILocalVariable(file: !0, line: 123, name: "failed", scope: !30, type: !10)
!123 = !DILocalVariable(file: !0, line: 123, name: "crashed", scope: !30, type: !10)
!124 = !DILocalVariable(file: !0, line: 123, name: "timeout", scope: !30, type: !10)
!125 = !DILocalVariable(file: !0, line: 123, name: "skipped", scope: !30, type: !10)
!126 = !DILocalVariable(file: !0, line: 123, name: "duration_ms", scope: !30, type: !11)
!127 = !DILocation(column: 5, line: 125, scope: !30)
!128 = !DILocation(column: 5, line: 126, scope: !30)
!129 = !DILocation(column: 5, line: 129, scope: !30)
!130 = !DILocation(column: 5, line: 131, scope: !30)
!131 = !DILocation(column: 5, line: 132, scope: !30)
!132 = !DILocation(column: 5, line: 134, scope: !30)
!133 = !DILocation(column: 5, line: 135, scope: !30)
!134 = !DILocation(column: 5, line: 137, scope: !30)
!135 = !DILocation(column: 5, line: 138, scope: !30)
!136 = !DILocation(column: 5, line: 140, scope: !30)
!137 = !DILocation(column: 5, line: 141, scope: !30)
!138 = !DILocation(column: 5, line: 143, scope: !30)
!139 = !DILocation(column: 5, line: 144, scope: !30)
!140 = !DILocation(column: 5, line: 146, scope: !30)
!141 = !DILocation(column: 5, line: 147, scope: !30)
!142 = !DILocation(column: 5, line: 149, scope: !30)
!143 = !DILocation(column: 5, line: 150, scope: !30)
!144 = !DILocation(column: 5, line: 152, scope: !30)
!145 = !DILocation(column: 5, line: 155, scope: !30)
!146 = !DILocation(column: 5, line: 157, scope: !30)
!147 = !DILocation(column: 9, line: 158, scope: !30)
!148 = !DILocation(column: 9, line: 159, scope: !30)
!149 = !DILocation(column: 9, line: 160, scope: !30)
!150 = !DILocation(column: 9, line: 161, scope: !30)
!151 = !DILocation(column: 9, line: 162, scope: !30)
!152 = !DILocation(column: 9, line: 163, scope: !30)
!153 = !DILocation(column: 9, line: 164, scope: !30)
!154 = !DILocation(column: 9, line: 165, scope: !30)
!155 = !DILocation(column: 13, line: 166, scope: !30)
!156 = !DILocation(column: 9, line: 168, scope: !30)
!157 = !DILocation(column: 13, line: 169, scope: !30)
!158 = !DILocation(column: 9, line: 171, scope: !30)
!159 = !DILocation(column: 9, line: 172, scope: !30)
!160 = !DILocation(column: 5, line: 176, scope: !30)
!161 = !DILocation(column: 5, line: 177, scope: !30)
!162 = !DILocation(column: 5, line: 181, scope: !31)
!163 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!164 = !DIDerivedType(baseType: !163, size: 64, tag: DW_TAG_reference_type)
!165 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !32, type: !164)
!166 = !DILocation(column: 1, line: 210, scope: !32)
!167 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!168 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !32, type: !167)
!169 = !DILocation(column: 5, line: 211, scope: !32)
!170 = !DILocation(column: 9, line: 212, scope: !32)
!171 = !DILocation(column: 5, line: 213, scope: !32)
!172 = !DILocation(column: 5, line: 214, scope: !32)
!173 = !DILocation(column: 5, line: 215, scope: !32)
!174 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!175 = !DIDerivedType(baseType: !174, size: 64, tag: DW_TAG_reference_type)
!176 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !33, type: !175)
!177 = !DILocation(column: 1, line: 244, scope: !33)
!178 = !DILocation(column: 5, line: 245, scope: !33)
!179 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !34, type: !175)
!180 = !DILocation(column: 1, line: 288, scope: !34)
!181 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!182 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !34, type: !181)
!183 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !34, type: !11)
!184 = !DILocation(column: 5, line: 289, scope: !34)
!185 = !DILocation(column: 13, line: 291, scope: !34)
!186 = !DILocation(column: 5, line: 292, scope: !34)
!187 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !35, type: !175)
!188 = !DILocation(column: 1, line: 225, scope: !35)
!189 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !35, type: !11)
!190 = !DILocation(column: 5, line: 226, scope: !35)
!191 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !36, type: !175)
!192 = !DILocation(column: 1, line: 148, scope: !36)
!193 = !DILocation(column: 5, line: 149, scope: !36)
!194 = !DILocation(column: 5, line: 151, scope: !36)
!195 = !DILocation(column: 5, line: 152, scope: !36)
!196 = !DILocation(column: 5, line: 153, scope: !36)
!197 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !37, type: !11)
!198 = !DILocation(column: 1, line: 124, scope: !37)
!199 = !DILocation(column: 5, line: 125, scope: !37)
!200 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !37, type: !174)
!201 = !DILocation(column: 1, line: 125, scope: !37)
!202 = !DILocation(column: 5, line: 126, scope: !37)
!203 = !DILocation(column: 9, line: 127, scope: !37)
!204 = !DILocation(column: 9, line: 128, scope: !37)
!205 = !DILocation(column: 9, line: 129, scope: !37)
!206 = !DILocation(column: 9, line: 130, scope: !37)
!207 = !DILocation(column: 5, line: 132, scope: !37)
!208 = !DILocation(column: 5, line: 133, scope: !37)
!209 = !DILocation(column: 5, line: 134, scope: !37)
!210 = !DILocation(column: 9, line: 135, scope: !37)
!211 = !DILocation(column: 9, line: 136, scope: !37)
!212 = !DILocation(column: 9, line: 137, scope: !37)
!213 = !DILocation(column: 5, line: 139, scope: !37)
!214 = !DILocation(column: 5, line: 140, scope: !37)
!215 = !DILocation(column: 5, line: 141, scope: !37)
!216 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !38, type: !175)
!217 = !DILocation(column: 1, line: 193, scope: !38)
!218 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !38, type: !11)
!219 = !DILocation(column: 5, line: 194, scope: !38)
!220 = !DILocation(column: 9, line: 195, scope: !38)
!221 = !DILocation(column: 5, line: 197, scope: !38)
!222 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !38, type: !11)
!223 = !DILocation(column: 1, line: 197, scope: !38)
!224 = !DILocation(column: 5, line: 198, scope: !38)
!225 = !DILocation(column: 9, line: 199, scope: !38)
!226 = !DILocation(column: 5, line: 200, scope: !38)
!227 = !DILocation(column: 9, line: 201, scope: !38)
!228 = !DILocation(column: 5, line: 203, scope: !38)
!229 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !39, type: !175)
!230 = !DILocation(column: 1, line: 219, scope: !39)
!231 = !DILocation(column: 5, line: 220, scope: !39)
!232 = !DILocation(column: 5, line: 221, scope: !39)
!233 = !DILocation(column: 5, line: 117, scope: !40)
!234 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !40, type: !174)
!235 = !DILocation(column: 1, line: 117, scope: !40)
!236 = !DILocation(column: 5, line: 118, scope: !40)
!237 = !DILocation(column: 5, line: 119, scope: !40)
!238 = !DILocation(column: 5, line: 120, scope: !40)
!239 = !DILocation(column: 5, line: 121, scope: !40)
!240 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !41, type: !175)
!241 = !DILocation(column: 1, line: 235, scope: !41)
!242 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !41, type: !11)
!243 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !41, type: !12)
!244 = !DILocation(column: 5, line: 236, scope: !41)
!245 = !DILocation(column: 5, line: 237, scope: !41)
!246 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !42, type: !175)
!247 = !DILocation(column: 1, line: 210, scope: !42)
!248 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !42, type: !12)
!249 = !DILocation(column: 5, line: 211, scope: !42)
!250 = !DILocation(column: 9, line: 212, scope: !42)
!251 = !DILocation(column: 5, line: 213, scope: !42)
!252 = !DILocation(column: 5, line: 214, scope: !42)
!253 = !DILocation(column: 5, line: 215, scope: !42)
!254 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !43, type: !175)
!255 = !DILocation(column: 1, line: 179, scope: !43)
!256 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !43, type: !11)
!257 = !DILocation(column: 5, line: 180, scope: !43)
!258 = !DILocation(column: 9, line: 181, scope: !43)
!259 = !DILocation(column: 5, line: 183, scope: !43)
!260 = !DILocation(column: 5, line: 184, scope: !43)
!261 = !DILocation(column: 5, line: 185, scope: !43)
!262 = !DILocation(column: 9, line: 186, scope: !43)
!263 = !DILocation(column: 5, line: 188, scope: !43)
!264 = !DILocation(column: 5, line: 189, scope: !43)
!265 = !DILocation(column: 5, line: 190, scope: !43)
!266 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !44, type: !164)
!267 = !DILocation(column: 1, line: 193, scope: !44)
!268 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !44, type: !11)
!269 = !DILocation(column: 5, line: 194, scope: !44)
!270 = !DILocation(column: 9, line: 195, scope: !44)
!271 = !DILocation(column: 5, line: 197, scope: !44)
!272 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !44, type: !11)
!273 = !DILocation(column: 1, line: 197, scope: !44)
!274 = !DILocation(column: 5, line: 198, scope: !44)
!275 = !DILocation(column: 9, line: 199, scope: !44)
!276 = !DILocation(column: 5, line: 200, scope: !44)
!277 = !DILocation(column: 9, line: 201, scope: !44)
!278 = !DILocation(column: 5, line: 203, scope: !44)
!279 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !45, type: !164)
!280 = !DILocation(column: 1, line: 179, scope: !45)
!281 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !45, type: !11)
!282 = !DILocation(column: 5, line: 180, scope: !45)
!283 = !DILocation(column: 9, line: 181, scope: !45)
!284 = !DILocation(column: 5, line: 183, scope: !45)
!285 = !DILocation(column: 5, line: 184, scope: !45)
!286 = !DILocation(column: 5, line: 185, scope: !45)
!287 = !DILocation(column: 9, line: 186, scope: !45)
!288 = !DILocation(column: 5, line: 188, scope: !45)
!289 = !DILocation(column: 5, line: 189, scope: !45)
!290 = !DILocation(column: 5, line: 190, scope: !45)