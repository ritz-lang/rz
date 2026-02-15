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
%"struct.ritz_module_1.JunitTestResult" = type {%"struct.ritz_module_1.StrView", i32, i64, i32, i32, %"struct.ritz_module_1.StrView"}
declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

@"BLOCK_SIZES" = internal constant [9 x i64] [i64 32, i64 48, i64 80, i64 144, i64 272, i64 528, i64 1040, i64 2064, i64 0]
@"g_alloc" = internal global %"struct.ritz_module_1.GlobalAlloc" zeroinitializer
@"g_junit_results" = internal global [1024 x %"struct.ritz_module_1.JunitTestResult"] zeroinitializer
@"g_junit_result_count" = internal global i32 0
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

define i32 @"junit_record_result"(%"struct.ritz_module_1.StrView"* %"name.arg", i32 %"status.arg", i64 %"duration_ms.arg", i32 %"exit_code.arg", i32 %"signal.arg", %"struct.ritz_module_1.StrView"* %"message.arg") !dbg !17
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name.arg", metadata !43, metadata !7), !dbg !44
  %"status" = alloca i32
  store i32 %"status.arg", i32* %"status"
  call void @"llvm.dbg.declare"(metadata i32* %"status", metadata !45, metadata !7), !dbg !44
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !46, metadata !7), !dbg !44
  %"exit_code" = alloca i32
  store i32 %"exit_code.arg", i32* %"exit_code"
  call void @"llvm.dbg.declare"(metadata i32* %"exit_code", metadata !47, metadata !7), !dbg !44
  %"signal" = alloca i32
  store i32 %"signal.arg", i32* %"signal"
  call void @"llvm.dbg.declare"(metadata i32* %"signal", metadata !48, metadata !7), !dbg !44
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"message.arg", metadata !49, metadata !7), !dbg !44
  %".18" = load i32, i32* @"g_junit_result_count", !dbg !50
  %".19" = sext i32 %".18" to i64 , !dbg !50
  %".20" = icmp sge i64 %".19", 1024 , !dbg !50
  br i1 %".20", label %"if.then", label %"if.end", !dbg !50
if.then:
  ret i32 0, !dbg !51
if.end:
  %".23" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name.arg", !dbg !52
  %".24" = load i32, i32* @"g_junit_result_count", !dbg !52
  %".25" = getelementptr [1024 x %"struct.ritz_module_1.JunitTestResult"], [1024 x %"struct.ritz_module_1.JunitTestResult"]* @"g_junit_results", i32 0, i32 %".24" , !dbg !52
  %".26" = load %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".25", !dbg !52
  %".27" = load i32, i32* @"g_junit_result_count", !dbg !52
  %".28" = getelementptr [1024 x %"struct.ritz_module_1.JunitTestResult"], [1024 x %"struct.ritz_module_1.JunitTestResult"]* @"g_junit_results", i32 0, i32 %".27" , !dbg !52
  %".29" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".28", i32 0, i32 0 , !dbg !52
  store %"struct.ritz_module_1.StrView" %".23", %"struct.ritz_module_1.StrView"* %".29", !dbg !52
  %".31" = load i32, i32* %"status", !dbg !53
  %".32" = load i32, i32* @"g_junit_result_count", !dbg !53
  %".33" = getelementptr [1024 x %"struct.ritz_module_1.JunitTestResult"], [1024 x %"struct.ritz_module_1.JunitTestResult"]* @"g_junit_results", i32 0, i32 %".32" , !dbg !53
  %".34" = load %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".33", !dbg !53
  %".35" = load i32, i32* @"g_junit_result_count", !dbg !53
  %".36" = getelementptr [1024 x %"struct.ritz_module_1.JunitTestResult"], [1024 x %"struct.ritz_module_1.JunitTestResult"]* @"g_junit_results", i32 0, i32 %".35" , !dbg !53
  %".37" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".36", i32 0, i32 1 , !dbg !53
  store i32 %".31", i32* %".37", !dbg !53
  %".39" = load i64, i64* %"duration_ms", !dbg !54
  %".40" = load i32, i32* @"g_junit_result_count", !dbg !54
  %".41" = getelementptr [1024 x %"struct.ritz_module_1.JunitTestResult"], [1024 x %"struct.ritz_module_1.JunitTestResult"]* @"g_junit_results", i32 0, i32 %".40" , !dbg !54
  %".42" = load %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".41", !dbg !54
  %".43" = load i32, i32* @"g_junit_result_count", !dbg !54
  %".44" = getelementptr [1024 x %"struct.ritz_module_1.JunitTestResult"], [1024 x %"struct.ritz_module_1.JunitTestResult"]* @"g_junit_results", i32 0, i32 %".43" , !dbg !54
  %".45" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".44", i32 0, i32 2 , !dbg !54
  store i64 %".39", i64* %".45", !dbg !54
  %".47" = load i32, i32* %"exit_code", !dbg !55
  %".48" = load i32, i32* @"g_junit_result_count", !dbg !55
  %".49" = getelementptr [1024 x %"struct.ritz_module_1.JunitTestResult"], [1024 x %"struct.ritz_module_1.JunitTestResult"]* @"g_junit_results", i32 0, i32 %".48" , !dbg !55
  %".50" = load %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".49", !dbg !55
  %".51" = load i32, i32* @"g_junit_result_count", !dbg !55
  %".52" = getelementptr [1024 x %"struct.ritz_module_1.JunitTestResult"], [1024 x %"struct.ritz_module_1.JunitTestResult"]* @"g_junit_results", i32 0, i32 %".51" , !dbg !55
  %".53" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".52", i32 0, i32 3 , !dbg !55
  store i32 %".47", i32* %".53", !dbg !55
  %".55" = load i32, i32* %"signal", !dbg !56
  %".56" = load i32, i32* @"g_junit_result_count", !dbg !56
  %".57" = getelementptr [1024 x %"struct.ritz_module_1.JunitTestResult"], [1024 x %"struct.ritz_module_1.JunitTestResult"]* @"g_junit_results", i32 0, i32 %".56" , !dbg !56
  %".58" = load %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".57", !dbg !56
  %".59" = load i32, i32* @"g_junit_result_count", !dbg !56
  %".60" = getelementptr [1024 x %"struct.ritz_module_1.JunitTestResult"], [1024 x %"struct.ritz_module_1.JunitTestResult"]* @"g_junit_results", i32 0, i32 %".59" , !dbg !56
  %".61" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".60", i32 0, i32 4 , !dbg !56
  store i32 %".55", i32* %".61", !dbg !56
  %".63" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"message.arg", !dbg !57
  %".64" = load i32, i32* @"g_junit_result_count", !dbg !57
  %".65" = getelementptr [1024 x %"struct.ritz_module_1.JunitTestResult"], [1024 x %"struct.ritz_module_1.JunitTestResult"]* @"g_junit_results", i32 0, i32 %".64" , !dbg !57
  %".66" = load %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".65", !dbg !57
  %".67" = load i32, i32* @"g_junit_result_count", !dbg !57
  %".68" = getelementptr [1024 x %"struct.ritz_module_1.JunitTestResult"], [1024 x %"struct.ritz_module_1.JunitTestResult"]* @"g_junit_results", i32 0, i32 %".67" , !dbg !57
  %".69" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".68", i32 0, i32 5 , !dbg !57
  store %"struct.ritz_module_1.StrView" %".63", %"struct.ritz_module_1.StrView"* %".69", !dbg !57
  %".71" = load i32, i32* @"g_junit_result_count", !dbg !58
  %".72" = sext i32 %".71" to i64 , !dbg !58
  %".73" = add i64 %".72", 1, !dbg !58
  %".74" = trunc i64 %".73" to i32 , !dbg !58
  store i32 %".74", i32* @"g_junit_result_count", !dbg !58
  ret i32 0, !dbg !58
}

define i32 @"junit_record_pass"(%"struct.ritz_module_1.StrView"* %"name.arg", i64 %"duration_ms.arg") !dbg !18
{
entry:
  %"empty.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !62
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name.arg", metadata !59, metadata !7), !dbg !60
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !61, metadata !7), !dbg !60
  %".7" = call %"struct.ritz_module_1.StrView" @"strview_empty"(), !dbg !62
  store %"struct.ritz_module_1.StrView" %".7", %"struct.ritz_module_1.StrView"* %"empty.addr", !dbg !62
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"empty.addr", metadata !63, metadata !7), !dbg !64
  %".10" = load i64, i64* %"duration_ms", !dbg !65
  %".11" = trunc i64 0 to i32 , !dbg !65
  %".12" = trunc i64 0 to i32 , !dbg !65
  %".13" = call i32 @"junit_record_result"(%"struct.ritz_module_1.StrView"* %"name.arg", i32 0, i64 %".10", i32 %".11", i32 %".12", %"struct.ritz_module_1.StrView"* %"empty.addr"), !dbg !65
  ret i32 %".13", !dbg !65
}

define i32 @"junit_record_fail"(%"struct.ritz_module_1.StrView"* %"name.arg", i64 %"duration_ms.arg", i32 %"exit_code.arg") !dbg !19
{
entry:
  %"msg.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !70
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name.arg", metadata !66, metadata !7), !dbg !67
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !68, metadata !7), !dbg !67
  %"exit_code" = alloca i32
  store i32 %"exit_code.arg", i32* %"exit_code"
  call void @"llvm.dbg.declare"(metadata i32* %"exit_code", metadata !69, metadata !7), !dbg !67
  %".10" = getelementptr [22 x i8], [22 x i8]* @".str.0", i64 0, i64 0 , !dbg !70
  %".11" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".10"), !dbg !70
  store %"struct.ritz_module_1.StrView" %".11", %"struct.ritz_module_1.StrView"* %"msg.addr", !dbg !70
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"msg.addr", metadata !71, metadata !7), !dbg !72
  %".14" = load i64, i64* %"duration_ms", !dbg !73
  %".15" = load i32, i32* %"exit_code", !dbg !73
  %".16" = trunc i64 0 to i32 , !dbg !73
  %".17" = call i32 @"junit_record_result"(%"struct.ritz_module_1.StrView"* %"name.arg", i32 1, i64 %".14", i32 %".15", i32 %".16", %"struct.ritz_module_1.StrView"* %"msg.addr"), !dbg !73
  ret i32 %".17", !dbg !73
}

define i32 @"junit_record_crash"(%"struct.ritz_module_1.StrView"* %"name.arg", i64 %"duration_ms.arg", i32 %"signal.arg", %"struct.ritz_module_1.StrView"* %"signal_name.arg") !dbg !20
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name.arg", metadata !74, metadata !7), !dbg !75
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !76, metadata !7), !dbg !75
  %"signal" = alloca i32
  store i32 %"signal.arg", i32* %"signal"
  call void @"llvm.dbg.declare"(metadata i32* %"signal", metadata !77, metadata !7), !dbg !75
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"signal_name.arg", metadata !78, metadata !7), !dbg !75
  %".12" = load i64, i64* %"duration_ms", !dbg !79
  %".13" = trunc i64 0 to i32 , !dbg !79
  %".14" = load i32, i32* %"signal", !dbg !79
  %".15" = call i32 @"junit_record_result"(%"struct.ritz_module_1.StrView"* %"name.arg", i32 2, i64 %".12", i32 %".13", i32 %".14", %"struct.ritz_module_1.StrView"* %"signal_name.arg"), !dbg !79
  ret i32 %".15", !dbg !79
}

define i32 @"junit_record_timeout"(%"struct.ritz_module_1.StrView"* %"name.arg", i64 %"duration_ms.arg") !dbg !21
{
entry:
  %"msg.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !83
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name.arg", metadata !80, metadata !7), !dbg !81
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !82, metadata !7), !dbg !81
  %".7" = getelementptr [15 x i8], [15 x i8]* @".str.1", i64 0, i64 0 , !dbg !83
  %".8" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".7"), !dbg !83
  store %"struct.ritz_module_1.StrView" %".8", %"struct.ritz_module_1.StrView"* %"msg.addr", !dbg !83
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"msg.addr", metadata !84, metadata !7), !dbg !85
  %".11" = load i64, i64* %"duration_ms", !dbg !86
  %".12" = trunc i64 0 to i32 , !dbg !86
  %".13" = trunc i64 0 to i32 , !dbg !86
  %".14" = call i32 @"junit_record_result"(%"struct.ritz_module_1.StrView"* %"name.arg", i32 2, i64 %".11", i32 %".12", i32 %".13", %"struct.ritz_module_1.StrView"* %"msg.addr"), !dbg !86
  ret i32 %".14", !dbg !86
}

define i32 @"jprint_char"(i8 %"c.arg") !dbg !22
{
entry:
  %"c" = alloca i8
  %"buf.addr" = alloca [2 x i8], !dbg !89
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !87, metadata !7), !dbg !88
  call void @"llvm.dbg.declare"(metadata [2 x i8]* %"buf.addr", metadata !93, metadata !7), !dbg !94
  %".6" = load i8, i8* %"c", !dbg !95
  %".7" = getelementptr [2 x i8], [2 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !95
  store i8 %".6", i8* %".7", !dbg !95
  %".9" = getelementptr [2 x i8], [2 x i8]* %"buf.addr", i32 0, i64 1 , !dbg !96
  %".10" = trunc i64 0 to i8 , !dbg !96
  store i8 %".10", i8* %".9", !dbg !96
  %".12" = getelementptr [2 x i8], [2 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !97
  %".13" = call i32 @"prints_cstr"(i8* %".12"), !dbg !97
  ret i32 %".13", !dbg !97
}

define i32 @"print_xml_escaped_sv"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !23
{
entry:
  %"i" = alloca i64, !dbg !102
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !98, metadata !7), !dbg !99
  %".4" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !100
  %".5" = load i64, i64* %".4", !dbg !100
  %".6" = icmp eq i64 %".5", 0 , !dbg !100
  br i1 %".6", label %"if.then", label %"if.end", !dbg !100
if.then:
  ret i32 0, !dbg !101
if.end:
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !102
  %".10" = load i64, i64* %".9", !dbg !102
  store i64 0, i64* %"i", !dbg !102
  br label %"for.cond", !dbg !102
for.cond:
  %".13" = load i64, i64* %"i", !dbg !102
  %".14" = icmp slt i64 %".13", %".10" , !dbg !102
  br i1 %".14", label %"for.body", label %"for.end", !dbg !102
for.body:
  %".16" = load i64, i64* %"i", !dbg !103
  %".17" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %".16"), !dbg !103
  %".18" = icmp eq i8 %".17", 60 , !dbg !103
  br i1 %".18", label %"if.then.1", label %"if.else", !dbg !103
for.incr:
  %".67" = load i64, i64* %"i", !dbg !103
  %".68" = add i64 %".67", 1, !dbg !103
  store i64 %".68", i64* %"i", !dbg !103
  br label %"for.cond", !dbg !103
for.end:
  ret i32 0, !dbg !103
if.then.1:
  %".20" = getelementptr [5 x i8], [5 x i8]* @".str.2", i64 0, i64 0 , !dbg !103
  %".21" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".20", 0 , !dbg !103
  %".22" = insertvalue %"struct.ritz_module_1.StrView" %".21", i64 4, 1 , !dbg !103
  %".23" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".22"), !dbg !103
  br label %"if.end.1", !dbg !103
if.else:
  %".24" = icmp eq i8 %".17", 62 , !dbg !103
  br i1 %".24", label %"if.then.2", label %"if.else.1", !dbg !103
if.end.1:
  %".65" = phi  i32 [%".23", %"if.then.1"], [%".62", %"if.end.2"] , !dbg !103
  br label %"for.incr", !dbg !103
if.then.2:
  %".26" = getelementptr [5 x i8], [5 x i8]* @".str.3", i64 0, i64 0 , !dbg !103
  %".27" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".26", 0 , !dbg !103
  %".28" = insertvalue %"struct.ritz_module_1.StrView" %".27", i64 4, 1 , !dbg !103
  %".29" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".28"), !dbg !103
  br label %"if.end.2", !dbg !103
if.else.1:
  %".30" = icmp eq i8 %".17", 38 , !dbg !103
  br i1 %".30", label %"if.then.3", label %"if.else.2", !dbg !103
if.end.2:
  %".62" = phi  i32 [%".29", %"if.then.2"], [%".59", %"if.end.3"] , !dbg !103
  br label %"if.end.1", !dbg !103
if.then.3:
  %".32" = getelementptr [6 x i8], [6 x i8]* @".str.4", i64 0, i64 0 , !dbg !103
  %".33" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".32", 0 , !dbg !103
  %".34" = insertvalue %"struct.ritz_module_1.StrView" %".33", i64 5, 1 , !dbg !103
  %".35" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".34"), !dbg !103
  br label %"if.end.3", !dbg !103
if.else.2:
  %".36" = zext i8 %".17" to i64 , !dbg !103
  %".37" = icmp eq i64 %".36", 34 , !dbg !103
  br i1 %".37", label %"if.then.4", label %"if.else.3", !dbg !103
if.end.3:
  %".59" = phi  i32 [%".35", %"if.then.3"], [%".56", %"if.end.4"] , !dbg !103
  br label %"if.end.2", !dbg !103
if.then.4:
  %".39" = getelementptr [7 x i8], [7 x i8]* @".str.5", i64 0, i64 0 , !dbg !103
  %".40" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".39", 0 , !dbg !103
  %".41" = insertvalue %"struct.ritz_module_1.StrView" %".40", i64 6, 1 , !dbg !103
  %".42" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".41"), !dbg !103
  br label %"if.end.4", !dbg !103
if.else.3:
  %".43" = zext i8 %".17" to i64 , !dbg !103
  %".44" = icmp eq i64 %".43", 39 , !dbg !103
  br i1 %".44", label %"if.then.5", label %"if.else.4", !dbg !103
if.end.4:
  %".56" = phi  i32 [%".42", %"if.then.4"], [%".53", %"if.end.5"] , !dbg !103
  br label %"if.end.3", !dbg !103
if.then.5:
  %".46" = getelementptr [7 x i8], [7 x i8]* @".str.6", i64 0, i64 0 , !dbg !103
  %".47" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".46", 0 , !dbg !103
  %".48" = insertvalue %"struct.ritz_module_1.StrView" %".47", i64 6, 1 , !dbg !103
  %".49" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".48"), !dbg !103
  br label %"if.end.5", !dbg !103
if.else.4:
  %".50" = call i32 @"jprint_char"(i8 %".17"), !dbg !103
  br label %"if.end.5", !dbg !103
if.end.5:
  %".53" = phi  i32 [%".49", %"if.then.5"], [%".50", %"if.else.4"] , !dbg !103
  br label %"if.end.4", !dbg !103
}

define i32 @"print_time_seconds"(i64 %"ms.arg") !dbg !24
{
entry:
  %"ms" = alloca i64
  store i64 %"ms.arg", i64* %"ms"
  call void @"llvm.dbg.declare"(metadata i64* %"ms", metadata !104, metadata !7), !dbg !105
  %".5" = load i64, i64* %"ms", !dbg !106
  %".6" = sdiv i64 %".5", 1000, !dbg !106
  %".7" = load i64, i64* %"ms", !dbg !107
  %".8" = srem i64 %".7", 1000, !dbg !107
  %".9" = call i32 @"print_int"(i64 %".6"), !dbg !108
  %".10" = call i32 @"jprint_char"(i8 46), !dbg !109
  %".11" = icmp slt i64 %".8", 100 , !dbg !110
  br i1 %".11", label %"if.then", label %"if.end", !dbg !110
if.then:
  %".13" = call i32 @"jprint_char"(i8 48), !dbg !110
  br label %"if.end", !dbg !110
if.end:
  %".15" = icmp slt i64 %".8", 10 , !dbg !111
  br i1 %".15", label %"if.then.1", label %"if.end.1", !dbg !111
if.then.1:
  %".17" = call i32 @"jprint_char"(i8 48), !dbg !111
  br label %"if.end.1", !dbg !111
if.end.1:
  %".19" = call i32 @"print_int"(i64 %".8"), !dbg !112
  ret i32 %".19", !dbg !112
}

define i32 @"junit_print_report"(i32 %"total.arg", i32 %"passed.arg", i32 %"failed.arg", i32 %"errors.arg", i64 %"duration_ms.arg") !dbg !25
{
entry:
  %"total" = alloca i32
  %"i" = alloca i32, !dbg !129
  store i32 %"total.arg", i32* %"total"
  call void @"llvm.dbg.declare"(metadata i32* %"total", metadata !113, metadata !7), !dbg !114
  %"passed" = alloca i32
  store i32 %"passed.arg", i32* %"passed"
  call void @"llvm.dbg.declare"(metadata i32* %"passed", metadata !115, metadata !7), !dbg !114
  %"failed" = alloca i32
  store i32 %"failed.arg", i32* %"failed"
  call void @"llvm.dbg.declare"(metadata i32* %"failed", metadata !116, metadata !7), !dbg !114
  %"errors" = alloca i32
  store i32 %"errors.arg", i32* %"errors"
  call void @"llvm.dbg.declare"(metadata i32* %"errors", metadata !117, metadata !7), !dbg !114
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !118, metadata !7), !dbg !114
  %".17" = getelementptr [40 x i8], [40 x i8]* @".str.7", i64 0, i64 0 , !dbg !119
  %".18" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".17", 0 , !dbg !119
  %".19" = insertvalue %"struct.ritz_module_1.StrView" %".18", i64 39, 1 , !dbg !119
  %".20" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".19"), !dbg !119
  %".21" = getelementptr [35 x i8], [35 x i8]* @".str.8", i64 0, i64 0 , !dbg !120
  %".22" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".21", 0 , !dbg !120
  %".23" = insertvalue %"struct.ritz_module_1.StrView" %".22", i64 34, 1 , !dbg !120
  %".24" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".23"), !dbg !120
  %".25" = load i32, i32* %"total", !dbg !121
  %".26" = sext i32 %".25" to i64 , !dbg !121
  %".27" = call i32 @"print_int"(i64 %".26"), !dbg !121
  %".28" = getelementptr [13 x i8], [13 x i8]* @".str.9", i64 0, i64 0 , !dbg !122
  %".29" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".28", 0 , !dbg !122
  %".30" = insertvalue %"struct.ritz_module_1.StrView" %".29", i64 12, 1 , !dbg !122
  %".31" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".30"), !dbg !122
  %".32" = load i32, i32* %"failed", !dbg !123
  %".33" = sext i32 %".32" to i64 , !dbg !123
  %".34" = call i32 @"print_int"(i64 %".33"), !dbg !123
  %".35" = getelementptr [11 x i8], [11 x i8]* @".str.10", i64 0, i64 0 , !dbg !124
  %".36" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".35", 0 , !dbg !124
  %".37" = insertvalue %"struct.ritz_module_1.StrView" %".36", i64 10, 1 , !dbg !124
  %".38" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".37"), !dbg !124
  %".39" = load i32, i32* %"errors", !dbg !125
  %".40" = sext i32 %".39" to i64 , !dbg !125
  %".41" = call i32 @"print_int"(i64 %".40"), !dbg !125
  %".42" = getelementptr [9 x i8], [9 x i8]* @".str.11", i64 0, i64 0 , !dbg !126
  %".43" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".42", 0 , !dbg !126
  %".44" = insertvalue %"struct.ritz_module_1.StrView" %".43", i64 8, 1 , !dbg !126
  %".45" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".44"), !dbg !126
  %".46" = load i64, i64* %"duration_ms", !dbg !127
  %".47" = call i32 @"print_time_seconds"(i64 %".46"), !dbg !127
  %".48" = getelementptr [4 x i8], [4 x i8]* @".str.12", i64 0, i64 0 , !dbg !128
  %".49" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".48", 0 , !dbg !128
  %".50" = insertvalue %"struct.ritz_module_1.StrView" %".49", i64 3, 1 , !dbg !128
  %".51" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".50"), !dbg !128
  %".52" = load i32, i32* @"g_junit_result_count", !dbg !129
  store i32 0, i32* %"i", !dbg !129
  br label %"for.cond", !dbg !129
for.cond:
  %".55" = load i32, i32* %"i", !dbg !129
  %".56" = icmp slt i32 %".55", %".52" , !dbg !129
  br i1 %".56", label %"for.body", label %"for.end", !dbg !129
for.body:
  %".58" = load i32, i32* %"i", !dbg !130
  %".59" = getelementptr [1024 x %"struct.ritz_module_1.JunitTestResult"], [1024 x %"struct.ritz_module_1.JunitTestResult"]* @"g_junit_results", i32 0, i32 %".58" , !dbg !130
  %".60" = getelementptr [19 x i8], [19 x i8]* @".str.13", i64 0, i64 0 , !dbg !131
  %".61" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".60", 0 , !dbg !131
  %".62" = insertvalue %"struct.ritz_module_1.StrView" %".61", i64 18, 1 , !dbg !131
  %".63" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".62"), !dbg !131
  %".64" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".59", i32 0, i32 0 , !dbg !132
  %".65" = call i32 @"print_xml_escaped_sv"(%"struct.ritz_module_1.StrView"* %".64"), !dbg !132
  %".66" = getelementptr [9 x i8], [9 x i8]* @".str.14", i64 0, i64 0 , !dbg !133
  %".67" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".66", 0 , !dbg !133
  %".68" = insertvalue %"struct.ritz_module_1.StrView" %".67", i64 8, 1 , !dbg !133
  %".69" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".68"), !dbg !133
  %".70" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".59", i32 0, i32 2 , !dbg !134
  %".71" = load i64, i64* %".70", !dbg !134
  %".72" = call i32 @"print_time_seconds"(i64 %".71"), !dbg !134
  %".73" = getelementptr [2 x i8], [2 x i8]* @".str.15", i64 0, i64 0 , !dbg !135
  %".74" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".73", 0 , !dbg !135
  %".75" = insertvalue %"struct.ritz_module_1.StrView" %".74", i64 1, 1 , !dbg !135
  %".76" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".75"), !dbg !135
  %".77" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".59", i32 0, i32 1 , !dbg !135
  %".78" = load i32, i32* %".77", !dbg !135
  %".79" = icmp eq i32 %".78", 0 , !dbg !135
  br i1 %".79", label %"if.then", label %"if.else", !dbg !135
for.incr:
  %".164" = load i32, i32* %"i", !dbg !148
  %".165" = add i32 %".164", 1, !dbg !148
  store i32 %".165", i32* %"i", !dbg !148
  br label %"for.cond", !dbg !148
for.end:
  %".168" = getelementptr [14 x i8], [14 x i8]* @".str.29", i64 0, i64 0 , !dbg !149
  %".169" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".168", 0 , !dbg !149
  %".170" = insertvalue %"struct.ritz_module_1.StrView" %".169", i64 13, 1 , !dbg !149
  %".171" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".170"), !dbg !149
  ret i32 %".171", !dbg !149
if.then:
  %".81" = getelementptr [4 x i8], [4 x i8]* @".str.16", i64 0, i64 0 , !dbg !135
  %".82" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".81", 0 , !dbg !135
  %".83" = insertvalue %"struct.ritz_module_1.StrView" %".82", i64 3, 1 , !dbg !135
  %".84" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".83"), !dbg !135
  br label %"if.end", !dbg !148
if.else:
  %".85" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".59", i32 0, i32 1 , !dbg !135
  %".86" = load i32, i32* %".85", !dbg !135
  %".87" = icmp eq i32 %".86", 1 , !dbg !135
  br i1 %".87", label %"if.then.1", label %"if.else.1", !dbg !135
if.end:
  %".162" = phi  i32 [%".84", %"if.then"], [%".159", %"if.end.1"] , !dbg !148
  br label %"for.incr", !dbg !148
if.then.1:
  %".89" = getelementptr [3 x i8], [3 x i8]* @".str.17", i64 0, i64 0 , !dbg !136
  %".90" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".89", 0 , !dbg !136
  %".91" = insertvalue %"struct.ritz_module_1.StrView" %".90", i64 2, 1 , !dbg !136
  %".92" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".91"), !dbg !136
  %".93" = getelementptr [33 x i8], [33 x i8]* @".str.18", i64 0, i64 0 , !dbg !137
  %".94" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".93", 0 , !dbg !137
  %".95" = insertvalue %"struct.ritz_module_1.StrView" %".94", i64 32, 1 , !dbg !137
  %".96" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".95"), !dbg !137
  %".97" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".59", i32 0, i32 3 , !dbg !138
  %".98" = load i32, i32* %".97", !dbg !138
  %".99" = sext i32 %".98" to i64 , !dbg !138
  %".100" = call i32 @"print_int"(i64 %".99"), !dbg !138
  %".101" = getelementptr [3 x i8], [3 x i8]* @".str.19", i64 0, i64 0 , !dbg !139
  %".102" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".101", 0 , !dbg !139
  %".103" = insertvalue %"struct.ritz_module_1.StrView" %".102", i64 2, 1 , !dbg !139
  %".104" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".103"), !dbg !139
  %".105" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".59", i32 0, i32 5 , !dbg !140
  %".106" = call i32 @"print_xml_escaped_sv"(%"struct.ritz_module_1.StrView"* %".105"), !dbg !140
  %".107" = getelementptr [12 x i8], [12 x i8]* @".str.20", i64 0, i64 0 , !dbg !141
  %".108" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".107", 0 , !dbg !141
  %".109" = insertvalue %"struct.ritz_module_1.StrView" %".108", i64 11, 1 , !dbg !141
  %".110" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".109"), !dbg !141
  %".111" = getelementptr [15 x i8], [15 x i8]* @".str.21", i64 0, i64 0 , !dbg !141
  %".112" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".111", 0 , !dbg !141
  %".113" = insertvalue %"struct.ritz_module_1.StrView" %".112", i64 14, 1 , !dbg !141
  %".114" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".113"), !dbg !141
  br label %"if.end.1", !dbg !148
if.else.1:
  %".115" = getelementptr [3 x i8], [3 x i8]* @".str.22", i64 0, i64 0 , !dbg !142
  %".116" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".115", 0 , !dbg !142
  %".117" = insertvalue %"struct.ritz_module_1.StrView" %".116", i64 2, 1 , !dbg !142
  %".118" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".117"), !dbg !142
  %".119" = getelementptr [21 x i8], [21 x i8]* @".str.23", i64 0, i64 0 , !dbg !143
  %".120" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".119", 0 , !dbg !143
  %".121" = insertvalue %"struct.ritz_module_1.StrView" %".120", i64 20, 1 , !dbg !143
  %".122" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".121"), !dbg !143
  %".123" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".59", i32 0, i32 4 , !dbg !144
  %".124" = load i32, i32* %".123", !dbg !144
  %".125" = sext i32 %".124" to i64 , !dbg !144
  %".126" = icmp ne i64 %".125", 0 , !dbg !144
  br i1 %".126", label %"if.then.2", label %"if.else.2", !dbg !144
if.end.1:
  %".159" = phi  i32 [%".114", %"if.then.1"], [%".156", %"if.end.2"] , !dbg !148
  br label %"if.end", !dbg !148
if.then.2:
  %".128" = getelementptr [8 x i8], [8 x i8]* @".str.24", i64 0, i64 0 , !dbg !145
  %".129" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".128", 0 , !dbg !145
  %".130" = insertvalue %"struct.ritz_module_1.StrView" %".129", i64 7, 1 , !dbg !145
  %".131" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".130"), !dbg !145
  %".132" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".59", i32 0, i32 4 , !dbg !145
  %".133" = load i32, i32* %".132", !dbg !145
  %".134" = sext i32 %".133" to i64 , !dbg !145
  %".135" = call i32 @"print_int"(i64 %".134"), !dbg !145
  br label %"if.end.2", !dbg !145
if.else.2:
  %".136" = getelementptr [8 x i8], [8 x i8]* @".str.25", i64 0, i64 0 , !dbg !145
  %".137" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".136", 0 , !dbg !145
  %".138" = insertvalue %"struct.ritz_module_1.StrView" %".137", i64 7, 1 , !dbg !145
  %".139" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".138"), !dbg !145
  br label %"if.end.2", !dbg !145
if.end.2:
  %".142" = phi  i32 [%".135", %"if.then.2"], [%".139", %"if.else.2"] , !dbg !145
  %".143" = getelementptr [3 x i8], [3 x i8]* @".str.26", i64 0, i64 0 , !dbg !146
  %".144" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".143", 0 , !dbg !146
  %".145" = insertvalue %"struct.ritz_module_1.StrView" %".144", i64 2, 1 , !dbg !146
  %".146" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".145"), !dbg !146
  %".147" = getelementptr %"struct.ritz_module_1.JunitTestResult", %"struct.ritz_module_1.JunitTestResult"* %".59", i32 0, i32 5 , !dbg !147
  %".148" = call i32 @"print_xml_escaped_sv"(%"struct.ritz_module_1.StrView"* %".147"), !dbg !147
  %".149" = getelementptr [10 x i8], [10 x i8]* @".str.27", i64 0, i64 0 , !dbg !148
  %".150" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".149", 0 , !dbg !148
  %".151" = insertvalue %"struct.ritz_module_1.StrView" %".150", i64 9, 1 , !dbg !148
  %".152" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".151"), !dbg !148
  %".153" = getelementptr [15 x i8], [15 x i8]* @".str.28", i64 0, i64 0 , !dbg !148
  %".154" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".153", 0 , !dbg !148
  %".155" = insertvalue %"struct.ritz_module_1.StrView" %".154", i64 14, 1 , !dbg !148
  %".156" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".155"), !dbg !148
  br label %"if.end.1", !dbg !148
}

define i32 @"junit_reset"() !dbg !26
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !150
  store i32 %".2", i32* @"g_junit_result_count", !dbg !150
  ret i32 0, !dbg !150
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !27
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !153, metadata !7), !dbg !154
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !156, metadata !7), !dbg !154
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !157
  %".8" = load i64, i64* %".7", !dbg !157
  %".9" = add i64 %".8", 1, !dbg !157
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !157
  %".11" = sext i32 %".10" to i64 , !dbg !157
  %".12" = icmp ne i64 %".11", 0 , !dbg !157
  br i1 %".12", label %"if.then", label %"if.end", !dbg !157
if.then:
  %".14" = sub i64 0, 1, !dbg !158
  %".15" = trunc i64 %".14" to i32 , !dbg !158
  ret i32 %".15", !dbg !158
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !159
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !159
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !159
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !159
  %".21" = load i64, i64* %".20", !dbg !159
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !159
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !159
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !160
  %".25" = load i64, i64* %".24", !dbg !160
  %".26" = add i64 %".25", 1, !dbg !160
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !160
  store i64 %".26", i64* %".27", !dbg !160
  %".29" = trunc i64 0 to i32 , !dbg !161
  ret i32 %".29", !dbg !161
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

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !29
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !172, metadata !7), !dbg !173
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !174
  store i64 0, i64* %".4", !dbg !174
  ret i32 0, !dbg !174
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !30
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !175, metadata !7), !dbg !176
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !177, metadata !7), !dbg !176
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !178, metadata !7), !dbg !176
  %".10" = load i8, i8* %"item", !dbg !179
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !179
  %".12" = load i8*, i8** %".11", !dbg !179
  %".13" = load i64, i64* %"idx", !dbg !179
  %".14" = getelementptr i8, i8* %".12", i64 %".13" , !dbg !179
  store i8 %".10", i8* %".14", !dbg !179
  %".16" = trunc i64 0 to i32 , !dbg !180
  ret i32 %".16", !dbg !180
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !31
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !181, metadata !7), !dbg !182
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !183, metadata !7), !dbg !182
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !184
  %".8" = load i8*, i8** %".7", !dbg !184
  %".9" = load i64, i64* %"idx", !dbg !184
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !184
  %".11" = load i8, i8* %".10", !dbg !184
  ret i8 %".11", !dbg !184
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !32
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !190
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !185, metadata !7), !dbg !186
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !187, metadata !7), !dbg !186
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !188
  %".8" = load i64, i64* %".7", !dbg !188
  %".9" = load i64, i64* %"needed", !dbg !188
  %".10" = icmp sge i64 %".8", %".9" , !dbg !188
  br i1 %".10", label %"if.then", label %"if.end", !dbg !188
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !189
  ret i32 %".12", !dbg !189
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !190
  %".15" = load i64, i64* %".14", !dbg !190
  store i64 %".15", i64* %"new_cap.addr", !dbg !190
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !191, metadata !7), !dbg !192
  %".18" = load i64, i64* %"new_cap.addr", !dbg !193
  %".19" = icmp eq i64 %".18", 0 , !dbg !193
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !193
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !194
  br label %"if.end.1", !dbg !194
if.end.1:
  br label %"while.cond", !dbg !195
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !195
  %".25" = load i64, i64* %"needed", !dbg !195
  %".26" = icmp slt i64 %".24", %".25" , !dbg !195
  br i1 %".26", label %"while.body", label %"while.end", !dbg !195
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !196
  %".29" = mul i64 %".28", 2, !dbg !196
  store i64 %".29", i64* %"new_cap.addr", !dbg !196
  br label %"while.cond", !dbg !196
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !197
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !197
  ret i32 %".33", !dbg !197
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !33
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !198
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !199, metadata !7), !dbg !200
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !201
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !201
  store i8* null, i8** %".4", !dbg !201
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !202
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !202
  store i64 0, i64* %".7", !dbg !202
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !203
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !203
  store i64 0, i64* %".10", !dbg !203
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !204
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !204
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !34
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !205, metadata !7), !dbg !206
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !207
  %".5" = load i64, i64* %".4", !dbg !207
  %".6" = sub i64 %".5", 1, !dbg !207
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !207
  store i64 %".6", i64* %".7", !dbg !207
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !208
  %".10" = load i8*, i8** %".9", !dbg !208
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !208
  %".12" = load i64, i64* %".11", !dbg !208
  %".13" = getelementptr i8, i8* %".10", i64 %".12" , !dbg !208
  %".14" = load i8, i8* %".13", !dbg !208
  ret i8 %".14", !dbg !208
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !35
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !211
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !209, metadata !7), !dbg !210
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !212, metadata !7), !dbg !213
  %".6" = load i64, i64* %"cap", !dbg !214
  %".7" = icmp sle i64 %".6", 0 , !dbg !214
  br i1 %".7", label %"if.then", label %"if.end", !dbg !214
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !215
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !215
  store i8* null, i8** %".10", !dbg !215
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !216
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !216
  store i64 0, i64* %".13", !dbg !216
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !217
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !217
  store i64 0, i64* %".16", !dbg !217
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !218
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !218
if.end:
  %".20" = load i64, i64* %"cap", !dbg !219
  %".21" = mul i64 %".20", 1, !dbg !219
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !220
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !220
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !220
  store i8* %".22", i8** %".24", !dbg !220
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !221
  %".27" = load i8*, i8** %".26", !dbg !221
  %".28" = icmp eq i8* %".27", null , !dbg !221
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !221
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !222
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !222
  store i64 0, i64* %".31", !dbg !222
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !223
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !223
  store i64 0, i64* %".34", !dbg !223
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !224
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !224
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !225
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !225
  store i64 0, i64* %".39", !dbg !225
  %".41" = load i64, i64* %"cap", !dbg !226
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !226
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !226
  store i64 %".41", i64* %".43", !dbg !226
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !227
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !227
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !36
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !228, metadata !7), !dbg !229
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !230
  %".5" = load i8*, i8** %".4", !dbg !230
  %".6" = icmp ne i8* %".5", null , !dbg !230
  br i1 %".6", label %"if.then", label %"if.end", !dbg !230
if.then:
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !230
  %".9" = load i8*, i8** %".8", !dbg !230
  %".10" = call i32 @"free"(i8* %".9"), !dbg !230
  br label %"if.end", !dbg !230
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !231
  store i8* null, i8** %".12", !dbg !231
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !232
  store i64 0, i64* %".14", !dbg !232
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !233
  store i64 0, i64* %".16", !dbg !233
  ret i32 0, !dbg !233
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !37
{
entry:
  %"i" = alloca i64, !dbg !239
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !234, metadata !7), !dbg !235
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !237, metadata !7), !dbg !235
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !238, metadata !7), !dbg !235
  %".10" = load i64, i64* %"len", !dbg !239
  store i64 0, i64* %"i", !dbg !239
  br label %"for.cond", !dbg !239
for.cond:
  %".13" = load i64, i64* %"i", !dbg !239
  %".14" = icmp slt i64 %".13", %".10" , !dbg !239
  br i1 %".14", label %"for.body", label %"for.end", !dbg !239
for.body:
  %".16" = load i8*, i8** %"data", !dbg !239
  %".17" = load i64, i64* %"i", !dbg !239
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !239
  %".19" = load i8, i8* %".18", !dbg !239
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !239
  %".21" = sext i32 %".20" to i64 , !dbg !239
  %".22" = icmp ne i64 %".21", 0 , !dbg !239
  br i1 %".22", label %"if.then", label %"if.end", !dbg !239
for.incr:
  %".28" = load i64, i64* %"i", !dbg !240
  %".29" = add i64 %".28", 1, !dbg !240
  store i64 %".29", i64* %"i", !dbg !240
  br label %"for.cond", !dbg !240
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !241
  ret i32 %".32", !dbg !241
if.then:
  %".24" = sub i64 0, 1, !dbg !240
  %".25" = trunc i64 %".24" to i32 , !dbg !240
  ret i32 %".25", !dbg !240
if.end:
  br label %"for.incr", !dbg !240
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !38
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !247
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !242, metadata !7), !dbg !243
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !244, metadata !7), !dbg !243
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !245
  %".8" = load i64, i64* %".7", !dbg !245
  %".9" = load i64, i64* %"needed", !dbg !245
  %".10" = icmp sge i64 %".8", %".9" , !dbg !245
  br i1 %".10", label %"if.then", label %"if.end", !dbg !245
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !246
  ret i32 %".12", !dbg !246
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !247
  %".15" = load i64, i64* %".14", !dbg !247
  store i64 %".15", i64* %"new_cap.addr", !dbg !247
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !248, metadata !7), !dbg !249
  %".18" = load i64, i64* %"new_cap.addr", !dbg !250
  %".19" = icmp eq i64 %".18", 0 , !dbg !250
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !250
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !251
  br label %"if.end.1", !dbg !251
if.end.1:
  br label %"while.cond", !dbg !252
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !252
  %".25" = load i64, i64* %"needed", !dbg !252
  %".26" = icmp slt i64 %".24", %".25" , !dbg !252
  br i1 %".26", label %"while.body", label %"while.end", !dbg !252
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !253
  %".29" = mul i64 %".28", 2, !dbg !253
  store i64 %".29", i64* %"new_cap.addr", !dbg !253
  br label %"while.cond", !dbg !253
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !254
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !254
  ret i32 %".33", !dbg !254
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !39
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !255, metadata !7), !dbg !256
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !257, metadata !7), !dbg !256
  %".7" = load i64, i64* %"new_cap", !dbg !258
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !258
  %".9" = load i64, i64* %".8", !dbg !258
  %".10" = icmp sle i64 %".7", %".9" , !dbg !258
  br i1 %".10", label %"if.then", label %"if.end", !dbg !258
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !259
  ret i32 %".12", !dbg !259
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !260
  %".15" = mul i64 %".14", 1, !dbg !260
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !261
  %".17" = load i8*, i8** %".16", !dbg !261
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !261
  %".19" = icmp eq i8* %".18", null , !dbg !262
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !262
if.then.1:
  %".21" = sub i64 0, 1, !dbg !263
  %".22" = trunc i64 %".21" to i32 , !dbg !263
  ret i32 %".22", !dbg !263
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !264
  store i8* %".18", i8** %".24", !dbg !264
  %".26" = load i64, i64* %"new_cap", !dbg !265
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !265
  store i64 %".26", i64* %".27", !dbg !265
  %".29" = trunc i64 0 to i32 , !dbg !266
  ret i32 %".29", !dbg !266
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !40
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !267, metadata !7), !dbg !268
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !269, metadata !7), !dbg !268
  %".7" = load i64, i64* %"new_cap", !dbg !270
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !270
  %".9" = load i64, i64* %".8", !dbg !270
  %".10" = icmp sle i64 %".7", %".9" , !dbg !270
  br i1 %".10", label %"if.then", label %"if.end", !dbg !270
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !271
  ret i32 %".12", !dbg !271
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !272
  %".15" = mul i64 %".14", 16, !dbg !272
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !273
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !273
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !273
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !273
  %".20" = icmp eq i8* %".19", null , !dbg !274
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !274
if.then.1:
  %".22" = sub i64 0, 1, !dbg !275
  %".23" = trunc i64 %".22" to i32 , !dbg !275
  ret i32 %".23", !dbg !275
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !276
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !276
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !276
  %".28" = load i64, i64* %"new_cap", !dbg !277
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !277
  store i64 %".28", i64* %".29", !dbg !277
  %".31" = trunc i64 0 to i32 , !dbg !278
  ret i32 %".31", !dbg !278
}

@".str.0" = private constant [22 x i8] c"Test assertion failed\00"
@".str.1" = private constant [15 x i8] c"Test timed out\00"
@".str.2" = private constant [5 x i8] c"&lt;\00"
@".str.3" = private constant [5 x i8] c"&gt;\00"
@".str.4" = private constant [6 x i8] c"&amp;\00"
@".str.5" = private constant [7 x i8] c"&quot;\00"
@".str.6" = private constant [7 x i8] c"&apos;\00"
@".str.7" = private constant [40 x i8] c"<?xml version=\221.0\22 encoding=\22UTF-8\22?>\0a\00"
@".str.8" = private constant [35 x i8] c"<testsuite name=\22ritzunit\22 tests=\22\00"
@".str.9" = private constant [13 x i8] c"\22 failures=\22\00"
@".str.10" = private constant [11 x i8] c"\22 errors=\22\00"
@".str.11" = private constant [9 x i8] c"\22 time=\22\00"
@".str.12" = private constant [4 x i8] c"\22>\0a\00"
@".str.13" = private constant [19 x i8] c"  <testcase name=\22\00"
@".str.14" = private constant [9 x i8] c"\22 time=\22\00"
@".str.15" = private constant [2 x i8] c"\22\00"
@".str.16" = private constant [4 x i8] c"/>\0a\00"
@".str.17" = private constant [3 x i8] c">\0a\00"
@".str.18" = private constant [33 x i8] c"    <failure message=\22exit code \00"
@".str.19" = private constant [3 x i8] c"\22>\00"
@".str.20" = private constant [12 x i8] c"</failure>\0a\00"
@".str.21" = private constant [15 x i8] c"  </testcase>\0a\00"
@".str.22" = private constant [3 x i8] c">\0a\00"
@".str.23" = private constant [21 x i8] c"    <error message=\22\00"
@".str.24" = private constant [8 x i8] c"signal \00"
@".str.25" = private constant [8 x i8] c"timeout\00"
@".str.26" = private constant [3 x i8] c"\22>\00"
@".str.27" = private constant [10 x i8] c"</error>\0a\00"
@".str.28" = private constant [15 x i8] c"  </testcase>\0a\00"
@".str.29" = private constant [14 x i8] c"</testsuite>\0a\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/ritzunit/src", filename: "junit_reporter.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 46, name: "junit_record_result", scopeLine: 46, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 57, name: "junit_record_pass", scopeLine: 57, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 61, name: "junit_record_fail", scopeLine: 61, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 65, name: "junit_record_crash", scopeLine: 65, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 68, name: "junit_record_timeout", scopeLine: 68, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 77, name: "jprint_char", scopeLine: 77, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 84, name: "print_xml_escaped_sv", scopeLine: 84, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 103, name: "print_time_seconds", scopeLine: 103, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 122, name: "junit_print_report", scopeLine: 122, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 175, name: "junit_reset", scopeLine: 175, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!41 = !DICompositeType(align: 64, file: !0, name: "StrView", size: 128, tag: DW_TAG_structure_type)
!42 = !DIDerivedType(baseType: !41, size: 64, tag: DW_TAG_reference_type)
!43 = !DILocalVariable(file: !0, line: 46, name: "name", scope: !17, type: !42)
!44 = !DILocation(column: 1, line: 46, scope: !17)
!45 = !DILocalVariable(file: !0, line: 46, name: "status", scope: !17, type: !10)
!46 = !DILocalVariable(file: !0, line: 46, name: "duration_ms", scope: !17, type: !11)
!47 = !DILocalVariable(file: !0, line: 46, name: "exit_code", scope: !17, type: !10)
!48 = !DILocalVariable(file: !0, line: 46, name: "signal", scope: !17, type: !10)
!49 = !DILocalVariable(file: !0, line: 46, name: "message", scope: !17, type: !42)
!50 = !DILocation(column: 5, line: 47, scope: !17)
!51 = !DILocation(column: 9, line: 48, scope: !17)
!52 = !DILocation(column: 5, line: 49, scope: !17)
!53 = !DILocation(column: 5, line: 50, scope: !17)
!54 = !DILocation(column: 5, line: 51, scope: !17)
!55 = !DILocation(column: 5, line: 52, scope: !17)
!56 = !DILocation(column: 5, line: 53, scope: !17)
!57 = !DILocation(column: 5, line: 54, scope: !17)
!58 = !DILocation(column: 5, line: 55, scope: !17)
!59 = !DILocalVariable(file: !0, line: 57, name: "name", scope: !18, type: !42)
!60 = !DILocation(column: 1, line: 57, scope: !18)
!61 = !DILocalVariable(file: !0, line: 57, name: "duration_ms", scope: !18, type: !11)
!62 = !DILocation(column: 5, line: 58, scope: !18)
!63 = !DILocalVariable(file: !0, line: 58, name: "empty", scope: !18, type: !41)
!64 = !DILocation(column: 1, line: 58, scope: !18)
!65 = !DILocation(column: 5, line: 59, scope: !18)
!66 = !DILocalVariable(file: !0, line: 61, name: "name", scope: !19, type: !42)
!67 = !DILocation(column: 1, line: 61, scope: !19)
!68 = !DILocalVariable(file: !0, line: 61, name: "duration_ms", scope: !19, type: !11)
!69 = !DILocalVariable(file: !0, line: 61, name: "exit_code", scope: !19, type: !10)
!70 = !DILocation(column: 5, line: 62, scope: !19)
!71 = !DILocalVariable(file: !0, line: 62, name: "msg", scope: !19, type: !41)
!72 = !DILocation(column: 1, line: 62, scope: !19)
!73 = !DILocation(column: 5, line: 63, scope: !19)
!74 = !DILocalVariable(file: !0, line: 65, name: "name", scope: !20, type: !42)
!75 = !DILocation(column: 1, line: 65, scope: !20)
!76 = !DILocalVariable(file: !0, line: 65, name: "duration_ms", scope: !20, type: !11)
!77 = !DILocalVariable(file: !0, line: 65, name: "signal", scope: !20, type: !10)
!78 = !DILocalVariable(file: !0, line: 65, name: "signal_name", scope: !20, type: !42)
!79 = !DILocation(column: 5, line: 66, scope: !20)
!80 = !DILocalVariable(file: !0, line: 68, name: "name", scope: !21, type: !42)
!81 = !DILocation(column: 1, line: 68, scope: !21)
!82 = !DILocalVariable(file: !0, line: 68, name: "duration_ms", scope: !21, type: !11)
!83 = !DILocation(column: 5, line: 69, scope: !21)
!84 = !DILocalVariable(file: !0, line: 69, name: "msg", scope: !21, type: !41)
!85 = !DILocation(column: 1, line: 69, scope: !21)
!86 = !DILocation(column: 5, line: 70, scope: !21)
!87 = !DILocalVariable(file: !0, line: 77, name: "c", scope: !22, type: !12)
!88 = !DILocation(column: 1, line: 77, scope: !22)
!89 = !DILocation(column: 5, line: 78, scope: !22)
!90 = !DISubrange(count: 2)
!91 = !{ !90 }
!92 = !DICompositeType(baseType: !12, elements: !91, size: 16, tag: DW_TAG_array_type)
!93 = !DILocalVariable(file: !0, line: 78, name: "buf", scope: !22, type: !92)
!94 = !DILocation(column: 1, line: 78, scope: !22)
!95 = !DILocation(column: 5, line: 79, scope: !22)
!96 = !DILocation(column: 5, line: 80, scope: !22)
!97 = !DILocation(column: 5, line: 81, scope: !22)
!98 = !DILocalVariable(file: !0, line: 84, name: "s", scope: !23, type: !42)
!99 = !DILocation(column: 1, line: 84, scope: !23)
!100 = !DILocation(column: 5, line: 85, scope: !23)
!101 = !DILocation(column: 9, line: 86, scope: !23)
!102 = !DILocation(column: 5, line: 87, scope: !23)
!103 = !DILocation(column: 9, line: 88, scope: !23)
!104 = !DILocalVariable(file: !0, line: 103, name: "ms", scope: !24, type: !11)
!105 = !DILocation(column: 1, line: 103, scope: !24)
!106 = !DILocation(column: 5, line: 104, scope: !24)
!107 = !DILocation(column: 5, line: 105, scope: !24)
!108 = !DILocation(column: 5, line: 107, scope: !24)
!109 = !DILocation(column: 5, line: 108, scope: !24)
!110 = !DILocation(column: 5, line: 111, scope: !24)
!111 = !DILocation(column: 5, line: 113, scope: !24)
!112 = !DILocation(column: 5, line: 115, scope: !24)
!113 = !DILocalVariable(file: !0, line: 122, name: "total", scope: !25, type: !10)
!114 = !DILocation(column: 1, line: 122, scope: !25)
!115 = !DILocalVariable(file: !0, line: 122, name: "passed", scope: !25, type: !10)
!116 = !DILocalVariable(file: !0, line: 122, name: "failed", scope: !25, type: !10)
!117 = !DILocalVariable(file: !0, line: 122, name: "errors", scope: !25, type: !10)
!118 = !DILocalVariable(file: !0, line: 122, name: "duration_ms", scope: !25, type: !11)
!119 = !DILocation(column: 5, line: 124, scope: !25)
!120 = !DILocation(column: 5, line: 127, scope: !25)
!121 = !DILocation(column: 5, line: 128, scope: !25)
!122 = !DILocation(column: 5, line: 129, scope: !25)
!123 = !DILocation(column: 5, line: 130, scope: !25)
!124 = !DILocation(column: 5, line: 131, scope: !25)
!125 = !DILocation(column: 5, line: 132, scope: !25)
!126 = !DILocation(column: 5, line: 133, scope: !25)
!127 = !DILocation(column: 5, line: 134, scope: !25)
!128 = !DILocation(column: 5, line: 135, scope: !25)
!129 = !DILocation(column: 5, line: 138, scope: !25)
!130 = !DILocation(column: 9, line: 139, scope: !25)
!131 = !DILocation(column: 9, line: 141, scope: !25)
!132 = !DILocation(column: 9, line: 142, scope: !25)
!133 = !DILocation(column: 9, line: 143, scope: !25)
!134 = !DILocation(column: 9, line: 144, scope: !25)
!135 = !DILocation(column: 9, line: 145, scope: !25)
!136 = !DILocation(column: 13, line: 151, scope: !25)
!137 = !DILocation(column: 13, line: 152, scope: !25)
!138 = !DILocation(column: 13, line: 153, scope: !25)
!139 = !DILocation(column: 13, line: 154, scope: !25)
!140 = !DILocation(column: 13, line: 155, scope: !25)
!141 = !DILocation(column: 13, line: 156, scope: !25)
!142 = !DILocation(column: 13, line: 160, scope: !25)
!143 = !DILocation(column: 13, line: 161, scope: !25)
!144 = !DILocation(column: 13, line: 162, scope: !25)
!145 = !DILocation(column: 17, line: 163, scope: !25)
!146 = !DILocation(column: 13, line: 167, scope: !25)
!147 = !DILocation(column: 13, line: 168, scope: !25)
!148 = !DILocation(column: 13, line: 169, scope: !25)
!149 = !DILocation(column: 5, line: 172, scope: !25)
!150 = !DILocation(column: 5, line: 176, scope: !26)
!151 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!152 = !DIDerivedType(baseType: !151, size: 64, tag: DW_TAG_reference_type)
!153 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !27, type: !152)
!154 = !DILocation(column: 1, line: 210, scope: !27)
!155 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!156 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !27, type: !155)
!157 = !DILocation(column: 5, line: 211, scope: !27)
!158 = !DILocation(column: 9, line: 212, scope: !27)
!159 = !DILocation(column: 5, line: 213, scope: !27)
!160 = !DILocation(column: 5, line: 214, scope: !27)
!161 = !DILocation(column: 5, line: 215, scope: !27)
!162 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!163 = !DIDerivedType(baseType: !162, size: 64, tag: DW_TAG_reference_type)
!164 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !28, type: !163)
!165 = !DILocation(column: 1, line: 210, scope: !28)
!166 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !28, type: !12)
!167 = !DILocation(column: 5, line: 211, scope: !28)
!168 = !DILocation(column: 9, line: 212, scope: !28)
!169 = !DILocation(column: 5, line: 213, scope: !28)
!170 = !DILocation(column: 5, line: 214, scope: !28)
!171 = !DILocation(column: 5, line: 215, scope: !28)
!172 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !29, type: !163)
!173 = !DILocation(column: 1, line: 244, scope: !29)
!174 = !DILocation(column: 5, line: 245, scope: !29)
!175 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !30, type: !163)
!176 = !DILocation(column: 1, line: 235, scope: !30)
!177 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !30, type: !11)
!178 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !30, type: !12)
!179 = !DILocation(column: 5, line: 236, scope: !30)
!180 = !DILocation(column: 5, line: 237, scope: !30)
!181 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !31, type: !163)
!182 = !DILocation(column: 1, line: 225, scope: !31)
!183 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !31, type: !11)
!184 = !DILocation(column: 5, line: 226, scope: !31)
!185 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !32, type: !163)
!186 = !DILocation(column: 1, line: 193, scope: !32)
!187 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !32, type: !11)
!188 = !DILocation(column: 5, line: 194, scope: !32)
!189 = !DILocation(column: 9, line: 195, scope: !32)
!190 = !DILocation(column: 5, line: 197, scope: !32)
!191 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !32, type: !11)
!192 = !DILocation(column: 1, line: 197, scope: !32)
!193 = !DILocation(column: 5, line: 198, scope: !32)
!194 = !DILocation(column: 9, line: 199, scope: !32)
!195 = !DILocation(column: 5, line: 200, scope: !32)
!196 = !DILocation(column: 9, line: 201, scope: !32)
!197 = !DILocation(column: 5, line: 203, scope: !32)
!198 = !DILocation(column: 5, line: 117, scope: !33)
!199 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !33, type: !162)
!200 = !DILocation(column: 1, line: 117, scope: !33)
!201 = !DILocation(column: 5, line: 118, scope: !33)
!202 = !DILocation(column: 5, line: 119, scope: !33)
!203 = !DILocation(column: 5, line: 120, scope: !33)
!204 = !DILocation(column: 5, line: 121, scope: !33)
!205 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !34, type: !163)
!206 = !DILocation(column: 1, line: 219, scope: !34)
!207 = !DILocation(column: 5, line: 220, scope: !34)
!208 = !DILocation(column: 5, line: 221, scope: !34)
!209 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !35, type: !11)
!210 = !DILocation(column: 1, line: 124, scope: !35)
!211 = !DILocation(column: 5, line: 125, scope: !35)
!212 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !35, type: !162)
!213 = !DILocation(column: 1, line: 125, scope: !35)
!214 = !DILocation(column: 5, line: 126, scope: !35)
!215 = !DILocation(column: 9, line: 127, scope: !35)
!216 = !DILocation(column: 9, line: 128, scope: !35)
!217 = !DILocation(column: 9, line: 129, scope: !35)
!218 = !DILocation(column: 9, line: 130, scope: !35)
!219 = !DILocation(column: 5, line: 132, scope: !35)
!220 = !DILocation(column: 5, line: 133, scope: !35)
!221 = !DILocation(column: 5, line: 134, scope: !35)
!222 = !DILocation(column: 9, line: 135, scope: !35)
!223 = !DILocation(column: 9, line: 136, scope: !35)
!224 = !DILocation(column: 9, line: 137, scope: !35)
!225 = !DILocation(column: 5, line: 139, scope: !35)
!226 = !DILocation(column: 5, line: 140, scope: !35)
!227 = !DILocation(column: 5, line: 141, scope: !35)
!228 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !36, type: !163)
!229 = !DILocation(column: 1, line: 148, scope: !36)
!230 = !DILocation(column: 5, line: 149, scope: !36)
!231 = !DILocation(column: 5, line: 151, scope: !36)
!232 = !DILocation(column: 5, line: 152, scope: !36)
!233 = !DILocation(column: 5, line: 153, scope: !36)
!234 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !37, type: !163)
!235 = !DILocation(column: 1, line: 288, scope: !37)
!236 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!237 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !37, type: !236)
!238 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !37, type: !11)
!239 = !DILocation(column: 5, line: 289, scope: !37)
!240 = !DILocation(column: 13, line: 291, scope: !37)
!241 = !DILocation(column: 5, line: 292, scope: !37)
!242 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !38, type: !152)
!243 = !DILocation(column: 1, line: 193, scope: !38)
!244 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !38, type: !11)
!245 = !DILocation(column: 5, line: 194, scope: !38)
!246 = !DILocation(column: 9, line: 195, scope: !38)
!247 = !DILocation(column: 5, line: 197, scope: !38)
!248 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !38, type: !11)
!249 = !DILocation(column: 1, line: 197, scope: !38)
!250 = !DILocation(column: 5, line: 198, scope: !38)
!251 = !DILocation(column: 9, line: 199, scope: !38)
!252 = !DILocation(column: 5, line: 200, scope: !38)
!253 = !DILocation(column: 9, line: 201, scope: !38)
!254 = !DILocation(column: 5, line: 203, scope: !38)
!255 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !39, type: !163)
!256 = !DILocation(column: 1, line: 179, scope: !39)
!257 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !39, type: !11)
!258 = !DILocation(column: 5, line: 180, scope: !39)
!259 = !DILocation(column: 9, line: 181, scope: !39)
!260 = !DILocation(column: 5, line: 183, scope: !39)
!261 = !DILocation(column: 5, line: 184, scope: !39)
!262 = !DILocation(column: 5, line: 185, scope: !39)
!263 = !DILocation(column: 9, line: 186, scope: !39)
!264 = !DILocation(column: 5, line: 188, scope: !39)
!265 = !DILocation(column: 5, line: 189, scope: !39)
!266 = !DILocation(column: 5, line: 190, scope: !39)
!267 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !40, type: !152)
!268 = !DILocation(column: 1, line: 179, scope: !40)
!269 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !40, type: !11)
!270 = !DILocation(column: 5, line: 180, scope: !40)
!271 = !DILocation(column: 9, line: 181, scope: !40)
!272 = !DILocation(column: 5, line: 183, scope: !40)
!273 = !DILocation(column: 5, line: 184, scope: !40)
!274 = !DILocation(column: 5, line: 185, scope: !40)
!275 = !DILocation(column: 9, line: 186, scope: !40)
!276 = !DILocation(column: 5, line: 188, scope: !40)
!277 = !DILocation(column: 5, line: 189, scope: !40)
!278 = !DILocation(column: 5, line: 190, scope: !40)