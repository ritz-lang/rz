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
%"struct.ritz_module_1.Elf64_Ehdr" = type {[16 x i8], i16, i16, i32, i64, i64, i64, i32, i16, i16, i16, i16, i16, i16}
%"struct.ritz_module_1.Elf64_Shdr" = type {i32, i32, i64, i64, i64, i64, i32, i32, i64, i64}
%"struct.ritz_module_1.Elf64_Sym" = type {i32, i8, i8, i16, i64, i64}
%"struct.ritz_module_1.ElfReader" = type {i8*, i64, %"struct.ritz_module_1.Elf64_Ehdr"*, %"struct.ritz_module_1.Elf64_Shdr"*, %"struct.ritz_module_1.Elf64_Sym"*, i64, i8*}
%"struct.ritz_module_1.OptDef" = type {i8, i8*, i8*, i8*, i8*, i32, i32, i8*}
%"struct.ritz_module_1.PosDef" = type {i8*, i8*, i32, i32}
%"struct.ritz_module_1.ArgParser" = type {i8*, i8*, [32 x %"struct.ritz_module_1.OptDef"], i32, [8 x %"struct.ritz_module_1.PosDef"], i32, [256 x i8*], i32, i8*}
%"struct.ritz_module_1.TestResult" = type {%"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8", i32, i64, i32}
%"struct.ritz_module_1.TestSummary" = type {i32, i32, i32, i32, i32, i32, i64}
%"struct.ritz_module_1.JsonTestResult" = type {%"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView", i64, i32, i32}
%"struct.ritz_module_1.JunitTestResult" = type {%"struct.ritz_module_1.StrView", i32, i64, i32, i32, %"struct.ritz_module_1.StrView"}
%"struct.ritz_module_1.TestEntry" = type {i8*, i64}
%"struct.ritz_module_1.TestRunResult" = type {i32, i32, i32}
declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

@"BLOCK_SIZES" = internal constant [9 x i64] [i64 32, i64 48, i64 80, i64 144, i64 272, i64 528, i64 1040, i64 2064, i64 0]
@"g_alloc" = internal global %"struct.ritz_module_1.GlobalAlloc" zeroinitializer
@"g_color_initialized" = internal global i32 0
@"g_use_color" = internal global i32 0
@"g_color_forced" = internal global i32 0
@"g_json_results" = internal global [1024 x %"struct.ritz_module_1.JsonTestResult"] zeroinitializer
@"g_json_result_count" = internal global i32 0
@"g_junit_results" = internal global [1024 x %"struct.ritz_module_1.JunitTestResult"] zeroinitializer
@"g_junit_result_count" = internal global i32 0
@"g_verbose" = internal global i32 0
@"g_quiet" = internal global i32 0
@"g_list_only" = internal global i32 0
@"g_filter" = internal global i8* null
@"g_timeout_ms" = internal global i64 5000
@"g_no_fork" = internal global i32 0
@"g_fail_fast" = internal global i32 0
@"g_shuffle" = internal global i32 0
@"g_seed" = internal global i64 0
@"g_json" = internal global i32 0
@"g_junit" = internal global i32 0
@"g_color" = internal global i32 0
@"g_tests" = internal global [1024 x %"struct.ritz_module_1.TestEntry"] zeroinitializer
@"g_test_count" = internal global i32 0
@"g_base_addr" = internal global i64 0
@"g_rng_state" = internal global i64 0
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

declare i32 @"elf_init"(%"struct.ritz_module_1.ElfReader"* %".1", i8* %".2", i64 %".3")

declare i32 @"read_u16"(i8* %".1")

declare i32 @"read_u32"(i8* %".1")

declare i64 @"read_u64"(i8* %".1")

declare i32 @"elf_parse_sections"(%"struct.ritz_module_1.ElfReader"* %".1")

declare i8* @"elf_get_symbol_name"(%"struct.ritz_module_1.ElfReader"* %".1", i64 %".2")

declare i8 @"elf_get_symbol_info"(%"struct.ritz_module_1.ElfReader"* %".1", i64 %".2")

declare i32 @"elf_is_function"(i8 %".1")

declare i32 @"elf_is_global"(i8 %".1")

declare i64 @"elf_symbol_count"(%"struct.ritz_module_1.ElfReader"* %".1")

declare i32 @"starts_with"(i8* %".1", i8* %".2")

declare i32 @"elf_find_test_functions"(%"struct.ritz_module_1.ElfReader"* %".1", i8* %".2", i8* %".3")

declare i32 @"elf_print_test_functions"(%"struct.ritz_module_1.ElfReader"* %".1")

declare i32 @"args_init"(%"struct.ritz_module_1.ArgParser"* %".1", i8* %".2", i8* %".3")

declare i32 @"args_flag"(%"struct.ritz_module_1.ArgParser"* %".1", i8 %".2", i8* %".3", i8* %".4")

declare i32 @"args_option"(%"struct.ritz_module_1.ArgParser"* %".1", i8 %".2", i8* %".3", i8* %".4", i8* %".5", i8* %".6")

declare i32 @"args_positional"(%"struct.ritz_module_1.ArgParser"* %".1", i8* %".2", i8* %".3", i32 %".4", i32 %".5")

declare i32 @"find_option_short"(%"struct.ritz_module_1.ArgParser"* %".1", i8 %".2")

declare i32 @"find_option_long"(%"struct.ritz_module_1.ArgParser"* %".1", i8* %".2")

declare i32 @"args_parse"(%"struct.ritz_module_1.ArgParser"* %".1", i32 %".2", i8** %".3")

declare i32 @"args_get_flag"(%"struct.ritz_module_1.ArgParser"* %".1", i8 %".2")

declare i32 @"args_get_flag_long"(%"struct.ritz_module_1.ArgParser"* %".1", i8* %".2")

declare i8* @"args_get_str"(%"struct.ritz_module_1.ArgParser"* %".1", i8 %".2")

declare i8* @"args_get_str_long"(%"struct.ritz_module_1.ArgParser"* %".1", i8* %".2")

declare i64 @"args_get_int"(%"struct.ritz_module_1.ArgParser"* %".1", i8 %".2")

declare i64 @"args_get_int_long"(%"struct.ritz_module_1.ArgParser"* %".1", i8* %".2")

declare i8* @"args_get_positional"(%"struct.ritz_module_1.ArgParser"* %".1", i32 %".2")

declare i32 @"args_is_set"(%"struct.ritz_module_1.ArgParser"* %".1", i8 %".2")

declare i32 @"args_is_set_long"(%"struct.ritz_module_1.ArgParser"* %".1", i8* %".2")

declare i32 @"args_print_usage"(%"struct.ritz_module_1.ArgParser"* %".1")

declare i32 @"args_print_help"(%"struct.ritz_module_1.ArgParser"* %".1")

declare i32 @"isatty"(i32 %".1")

declare i32 @"set_color_mode"(i32 %".1")

declare i32 @"init_color"()

declare i32 @"use_color"()

declare i32 @"print_esc"()

declare i32 @"color_reset"()

declare i32 @"color_green"()

declare i32 @"color_red"()

declare i32 @"color_yellow"()

declare i32 @"color_bold"()

declare i32 @"color_dim"()

declare i32 @"print_banner"()

declare i32 @"print_suite_header"(%"struct.ritz_module_1.StrView" %".1")

declare i32 @"print_suite_divider"()

declare i32 @"print_grand_divider"()

declare i32 @"print_dots"(i32 %".1")

declare i32 @"print_test_line"(%"struct.ritz_module_1.StrView" %".1", %"struct.ritz_module_1.StrView" %".2", i64 %".3")

declare i32 @"print_test_pass"(%"struct.ritz_module_1.StrView" %".1", i64 %".2")

declare i32 @"print_test_fail"(%"struct.ritz_module_1.StrView" %".1", i64 %".2", i32 %".3")

declare i32 @"print_test_crash"(%"struct.ritz_module_1.StrView" %".1", i64 %".2", i32 %".3", %"struct.ritz_module_1.StrView" %".4")

declare i32 @"print_test_timeout"(%"struct.ritz_module_1.StrView" %".1", i64 %".2")

declare i32 @"print_test_skip"(%"struct.ritz_module_1.StrView" %".1", %"struct.ritz_module_1.StrView" %".2")

declare i32 @"print_suite_summary"(i32 %".1", i32 %".2", i32 %".3", i32 %".4", i32 %".5", i64 %".6")

declare i32 @"print_grand_summary"(i32 %".1", i32 %".2", i32 %".3", i32 %".4", i32 %".5", i32 %".6", i64 %".7")

declare i32 @"print_divider"()

declare i32 @"print_summary"(i32 %".1", i32 %".2", i32 %".3", i64 %".4")

declare %"struct.ritz_module_1.TestSummary" @"summary_new"()

declare i32 @"summary_record"(%"struct.ritz_module_1.TestSummary"* %".1", i32 %".2", i64 %".3")

declare i32 @"summary_merge"(%"struct.ritz_module_1.TestSummary"* %".1", %"struct.ritz_module_1.TestSummary"* %".2")

declare i32 @"is_space"(i8 %".1")

declare i32 @"starts_with_keyword"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i64 @"find_keyword"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i64 @"find_and"(%"struct.ritz_module_1.StrView"* %".1")

declare i64 @"find_or"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"starts_with_not"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"has_bool_operators"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"has_glob_chars"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"has_suite_separator"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"is_attribute"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"contains_substring"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i32 @"match_attribute"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i32 @"glob_match"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i32 @"match_suite_pattern"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i32 @"match_simple_pattern"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i32 @"match_bool_expr"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i32 @"filter_type_sv"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"filter_match_sv"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2")

declare i32 @"filter_match"(i8* %".1", i8* %".2")

declare i32 @"filter_type"(i8* %".1")

declare %"struct.ritz_module_1.StrView" @"status_pass"()

declare %"struct.ritz_module_1.StrView" @"status_fail"()

declare %"struct.ritz_module_1.StrView" @"status_crash"()

declare %"struct.ritz_module_1.StrView" @"status_timeout"()

declare %"struct.ritz_module_1.StrView" @"status_skip"()

declare i32 @"json_record_result"(%"struct.ritz_module_1.StrView"* %".1", %"struct.ritz_module_1.StrView"* %".2", i64 %".3", i32 %".4", i32 %".5")

declare i32 @"json_record_pass"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2")

declare i32 @"json_record_fail"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2", i32 %".3")

declare i32 @"json_record_crash"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2", i32 %".3")

declare i32 @"json_record_timeout"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2")

declare i32 @"json_print_char"(i8 %".1")

declare i32 @"print_quote"()

declare i32 @"print_json_string_sv"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"json_print_report"(i32 %".1", i32 %".2", i32 %".3", i32 %".4", i32 %".5", i32 %".6", i64 %".7")

declare i32 @"json_reset"()

declare i32 @"junit_record_result"(%"struct.ritz_module_1.StrView"* %".1", i32 %".2", i64 %".3", i32 %".4", i32 %".5", %"struct.ritz_module_1.StrView"* %".6")

declare i32 @"junit_record_pass"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2")

declare i32 @"junit_record_fail"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2", i32 %".3")

declare i32 @"junit_record_crash"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2", i32 %".3", %"struct.ritz_module_1.StrView"* %".4")

declare i32 @"junit_record_timeout"(%"struct.ritz_module_1.StrView"* %".1", i64 %".2")

declare i32 @"jprint_char"(i8 %".1")

declare i32 @"print_xml_escaped_sv"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"print_time_seconds"(i64 %".1")

declare i32 @"junit_print_report"(i32 %".1", i32 %".2", i32 %".3", i32 %".4", i64 %".5")

declare i32 @"junit_reset"()

define i32 @"WIFEXITED"(i32 %"status.arg") !dbg !17
{
entry:
  %"status" = alloca i32
  store i32 %"status.arg", i32* %"status"
  call void @"llvm.dbg.declare"(metadata i32* %"status", metadata !52, metadata !7), !dbg !53
  %".5" = load i32, i32* %"status", !dbg !54
  %".6" = sext i32 %".5" to i64 , !dbg !54
  %".7" = and i64 %".6", 127, !dbg !54
  %".8" = icmp eq i64 %".7", 0 , !dbg !54
  %".9" = zext i1 %".8" to i32 , !dbg !54
  ret i32 %".9", !dbg !54
}

define i32 @"WEXITSTATUS"(i32 %"status.arg") !dbg !18
{
entry:
  %"status" = alloca i32
  store i32 %"status.arg", i32* %"status"
  call void @"llvm.dbg.declare"(metadata i32* %"status", metadata !55, metadata !7), !dbg !56
  %".5" = load i32, i32* %"status", !dbg !57
  %".6" = sext i32 %".5" to i64 , !dbg !57
  %".7" = ashr i64 %".6", 8, !dbg !57
  %".8" = and i64 %".7", 255, !dbg !57
  %".9" = trunc i64 %".8" to i32 , !dbg !57
  ret i32 %".9", !dbg !57
}

define i32 @"WIFSIGNALED"(i32 %"status.arg") !dbg !19
{
entry:
  %"status" = alloca i32
  store i32 %"status.arg", i32* %"status"
  call void @"llvm.dbg.declare"(metadata i32* %"status", metadata !58, metadata !7), !dbg !59
  %".5" = load i32, i32* %"status", !dbg !60
  %".6" = sext i32 %".5" to i64 , !dbg !60
  %".7" = and i64 %".6", 127, !dbg !60
  %".8" = trunc i64 %".7" to i32 , !dbg !60
  %".9" = sext i32 %".8" to i64 , !dbg !61
  %".10" = icmp ne i64 %".9", 0 , !dbg !61
  br i1 %".10", label %"and.right", label %"and.merge", !dbg !61
and.right:
  %".12" = sext i32 %".8" to i64 , !dbg !61
  %".13" = icmp ne i64 %".12", 127 , !dbg !61
  br label %"and.merge", !dbg !61
and.merge:
  %".15" = phi  i1 [0, %"entry"], [%".13", %"and.right"] , !dbg !61
  %".16" = zext i1 %".15" to i32 , !dbg !61
  ret i32 %".16", !dbg !61
}

define i32 @"WTERMSIG"(i32 %"status.arg") !dbg !20
{
entry:
  %"status" = alloca i32
  store i32 %"status.arg", i32* %"status"
  call void @"llvm.dbg.declare"(metadata i32* %"status", metadata !62, metadata !7), !dbg !63
  %".5" = load i32, i32* %"status", !dbg !64
  %".6" = sext i32 %".5" to i64 , !dbg !64
  %".7" = and i64 %".6", 127, !dbg !64
  %".8" = trunc i64 %".7" to i32 , !dbg !64
  ret i32 %".8", !dbg !64
}

define i64 @"detect_base_address"() !dbg !21
{
entry:
  %"buf.addr" = alloca [4096 x i8], !dbg !68
  %"addr.addr" = alloca i64, !dbg !78
  %"i" = alloca i64, !dbg !81
  %".2" = getelementptr [16 x i8], [16 x i8]* @".str.0", i64 0, i64 0 , !dbg !65
  %".3" = call i32 @"sys_open"(i8* %".2", i32 0), !dbg !65
  %".4" = sext i32 %".3" to i64 , !dbg !66
  %".5" = icmp slt i64 %".4", 0 , !dbg !66
  br i1 %".5", label %"if.then", label %"if.end", !dbg !66
if.then:
  ret i64 0, !dbg !67
if.end:
  call void @"llvm.dbg.declare"(metadata [4096 x i8]* %"buf.addr", metadata !72, metadata !7), !dbg !73
  %".9" = bitcast [4096 x i8]* %"buf.addr" to i8* , !dbg !74
  %".10" = call i64 @"sys_read"(i32 %".3", i8* %".9", i64 4096), !dbg !74
  %".11" = call i32 @"sys_close"(i32 %".3"), !dbg !75
  %".12" = icmp sle i64 %".10", 0 , !dbg !76
  br i1 %".12", label %"if.then.1", label %"if.end.1", !dbg !76
if.then.1:
  ret i64 0, !dbg !77
if.end.1:
  store i64 0, i64* %"addr.addr", !dbg !78
  call void @"llvm.dbg.declare"(metadata i64* %"addr.addr", metadata !79, metadata !7), !dbg !80
  store i64 0, i64* %"i", !dbg !81
  br label %"for.cond", !dbg !81
for.cond:
  %".19" = load i64, i64* %"i", !dbg !81
  %".20" = icmp slt i64 %".19", %".10" , !dbg !81
  br i1 %".20", label %"for.body", label %"for.end", !dbg !81
for.body:
  %".22" = load i64, i64* %"i", !dbg !82
  %".23" = getelementptr [4096 x i8], [4096 x i8]* %"buf.addr", i32 0, i64 %".22" , !dbg !82
  %".24" = load i8, i8* %".23", !dbg !82
  %".25" = icmp eq i8 %".24", 45 , !dbg !83
  br i1 %".25", label %"if.then.2", label %"if.end.2", !dbg !83
for.incr:
  %".58" = load i64, i64* %"i", !dbg !86
  %".59" = add i64 %".58", 1, !dbg !86
  store i64 %".59", i64* %"i", !dbg !86
  br label %"for.cond", !dbg !86
for.end:
  %".62" = load i64, i64* %"addr.addr", !dbg !87
  ret i64 %".62", !dbg !87
if.then.2:
  %".27" = load i64, i64* %"addr.addr", !dbg !84
  ret i64 %".27", !dbg !84
if.end.2:
  %".29" = icmp uge i8 %".24", 48 , !dbg !84
  br i1 %".29", label %"and.right", label %"and.merge", !dbg !84
and.right:
  %".31" = icmp ule i8 %".24", 57 , !dbg !84
  br label %"and.merge", !dbg !84
and.merge:
  %".33" = phi  i1 [0, %"if.end.2"], [%".31", %"and.right"] , !dbg !84
  br i1 %".33", label %"if.then.3", label %"if.else", !dbg !84
if.then.3:
  %".35" = load i64, i64* %"addr.addr", !dbg !85
  %".36" = mul i64 %".35", 16, !dbg !85
  %".37" = sub i8 %".24", 48, !dbg !85
  %".38" = sext i8 %".37" to i64 , !dbg !85
  %".39" = add i64 %".36", %".38", !dbg !85
  store i64 %".39", i64* %"addr.addr", !dbg !85
  br label %"if.end.3", !dbg !86
if.else:
  %".41" = icmp uge i8 %".24", 97 , !dbg !85
  br i1 %".41", label %"and.right.1", label %"and.merge.1", !dbg !85
if.end.3:
  br label %"for.incr", !dbg !86
and.right.1:
  %".43" = icmp ule i8 %".24", 102 , !dbg !85
  br label %"and.merge.1", !dbg !85
and.merge.1:
  %".45" = phi  i1 [0, %"if.else"], [%".43", %"and.right.1"] , !dbg !85
  br i1 %".45", label %"if.then.4", label %"if.end.4", !dbg !85
if.then.4:
  %".47" = load i64, i64* %"addr.addr", !dbg !86
  %".48" = mul i64 %".47", 16, !dbg !86
  %".49" = sub i8 %".24", 97, !dbg !86
  %".50" = sext i8 %".49" to i64 , !dbg !86
  %".51" = add i64 %".50", 10, !dbg !86
  %".52" = add i64 %".48", %".51", !dbg !86
  store i64 %".52", i64* %"addr.addr", !dbg !86
  br label %"if.end.4", !dbg !86
if.end.4:
  br label %"if.end.3", !dbg !86
}

define i64 @"get_time_ms"() !dbg !22
{
entry:
  %"tv.addr" = alloca %"struct.ritz_module_1.Timeval", !dbg !88
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Timeval"* %"tv.addr", metadata !90, metadata !7), !dbg !91
  %".3" = call i32 @"sys_gettimeofday"(%"struct.ritz_module_1.Timeval"* %"tv.addr", i8* null), !dbg !92
  %".4" = getelementptr %"struct.ritz_module_1.Timeval", %"struct.ritz_module_1.Timeval"* %"tv.addr", i32 0, i32 0 , !dbg !93
  %".5" = load i64, i64* %".4", !dbg !93
  %".6" = mul i64 %".5", 1000, !dbg !93
  %".7" = getelementptr %"struct.ritz_module_1.Timeval", %"struct.ritz_module_1.Timeval"* %"tv.addr", i32 0, i32 1 , !dbg !93
  %".8" = load i64, i64* %".7", !dbg !93
  %".9" = sdiv i64 %".8", 1000, !dbg !93
  %".10" = add i64 %".6", %".9", !dbg !93
  ret i64 %".10", !dbg !93
}

define i64 @"get_time_us"() !dbg !23
{
entry:
  %"tv.addr" = alloca %"struct.ritz_module_1.Timeval", !dbg !94
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Timeval"* %"tv.addr", metadata !95, metadata !7), !dbg !96
  %".3" = call i32 @"sys_gettimeofday"(%"struct.ritz_module_1.Timeval"* %"tv.addr", i8* null), !dbg !97
  %".4" = getelementptr %"struct.ritz_module_1.Timeval", %"struct.ritz_module_1.Timeval"* %"tv.addr", i32 0, i32 0 , !dbg !98
  %".5" = load i64, i64* %".4", !dbg !98
  %".6" = mul i64 %".5", 1000000, !dbg !98
  %".7" = getelementptr %"struct.ritz_module_1.Timeval", %"struct.ritz_module_1.Timeval"* %"tv.addr", i32 0, i32 1 , !dbg !98
  %".8" = load i64, i64* %".7", !dbg !98
  %".9" = add i64 %".6", %".8", !dbg !98
  ret i64 %".9", !dbg !98
}

define i32 @"rng_seed"(i64 %"seed.arg") !dbg !24
{
entry:
  %"seed" = alloca i64
  store i64 %"seed.arg", i64* %"seed"
  call void @"llvm.dbg.declare"(metadata i64* %"seed", metadata !99, metadata !7), !dbg !100
  %".5" = load i64, i64* %"seed", !dbg !101
  store i64 %".5", i64* @"g_rng_state", !dbg !101
  %".7" = load i64, i64* @"g_rng_state", !dbg !102
  %".8" = icmp eq i64 %".7", 0 , !dbg !102
  br i1 %".8", label %"if.then", label %"if.end", !dbg !102
if.then:
  store i64 1, i64* @"g_rng_state", !dbg !103
  br label %"if.end", !dbg !103
if.end:
  ret i32 0, !dbg !103
}

define i64 @"rng_next"() !dbg !25
{
entry:
  %".2" = load i64, i64* @"g_rng_state", !dbg !104
  %".3" = mul i64 %".2", 48271, !dbg !104
  %".4" = srem i64 %".3", 2147483647, !dbg !104
  store i64 %".4", i64* @"g_rng_state", !dbg !104
  %".6" = load i64, i64* @"g_rng_state", !dbg !105
  ret i64 %".6", !dbg !105
}

define i32 @"shuffle_tests"(i32 %"count.arg") !dbg !26
{
entry:
  %"count" = alloca i32
  %"i" = alloca i64, !dbg !110
  store i32 %"count.arg", i32* %"count"
  call void @"llvm.dbg.declare"(metadata i32* %"count", metadata !106, metadata !7), !dbg !107
  %".5" = load i32, i32* %"count", !dbg !108
  %".6" = sext i32 %".5" to i64 , !dbg !108
  %".7" = icmp sle i64 %".6", 1 , !dbg !108
  br i1 %".7", label %"if.then", label %"if.end", !dbg !108
if.then:
  ret i32 0, !dbg !109
if.end:
  %".10" = load i32, i32* %"count", !dbg !110
  %".11" = sext i32 %".10" to i64 , !dbg !110
  %".12" = sub i64 %".11", 1, !dbg !110
  store i64 0, i64* %"i", !dbg !110
  br label %"for.cond", !dbg !110
for.cond:
  %".15" = load i64, i64* %"i", !dbg !110
  %".16" = icmp slt i64 %".15", %".12" , !dbg !110
  br i1 %".16", label %"for.body", label %"for.end", !dbg !110
for.body:
  %".18" = load i64, i64* %"i", !dbg !111
  %".19" = call i64 @"rng_next"(), !dbg !111
  %".20" = load i32, i32* %"count", !dbg !111
  %".21" = load i64, i64* %"i", !dbg !111
  %".22" = sext i32 %".20" to i64 , !dbg !111
  %".23" = sub i64 %".22", %".21", !dbg !111
  %".24" = srem i64 %".19", %".23", !dbg !111
  %".25" = add i64 %".18", %".24", !dbg !111
  %".26" = load i64, i64* %"i", !dbg !112
  %".27" = getelementptr [1024 x %"struct.ritz_module_1.TestEntry"], [1024 x %"struct.ritz_module_1.TestEntry"]* @"g_tests", i32 0, i64 %".26" , !dbg !112
  %".28" = load %"struct.ritz_module_1.TestEntry", %"struct.ritz_module_1.TestEntry"* %".27", !dbg !112
  %".29" = trunc i64 %".25" to i32 , !dbg !113
  %".30" = getelementptr [1024 x %"struct.ritz_module_1.TestEntry"], [1024 x %"struct.ritz_module_1.TestEntry"]* @"g_tests", i32 0, i32 %".29" , !dbg !113
  %".31" = load %"struct.ritz_module_1.TestEntry", %"struct.ritz_module_1.TestEntry"* %".30", !dbg !113
  %".32" = load i64, i64* %"i", !dbg !113
  %".33" = getelementptr [1024 x %"struct.ritz_module_1.TestEntry"], [1024 x %"struct.ritz_module_1.TestEntry"]* @"g_tests", i32 0, i64 %".32" , !dbg !113
  store %"struct.ritz_module_1.TestEntry" %".31", %"struct.ritz_module_1.TestEntry"* %".33", !dbg !113
  %".35" = trunc i64 %".25" to i32 , !dbg !114
  %".36" = getelementptr [1024 x %"struct.ritz_module_1.TestEntry"], [1024 x %"struct.ritz_module_1.TestEntry"]* @"g_tests", i32 0, i32 %".35" , !dbg !114
  store %"struct.ritz_module_1.TestEntry" %".28", %"struct.ritz_module_1.TestEntry"* %".36", !dbg !114
  br label %"for.incr", !dbg !114
for.incr:
  %".39" = load i64, i64* %"i", !dbg !114
  %".40" = add i64 %".39", 1, !dbg !114
  store i64 %".40", i64* %"i", !dbg !114
  br label %"for.cond", !dbg !114
for.end:
  ret i32 0, !dbg !114
}

define i32 @"run_test_direct"(%"struct.ritz_module_1.TestEntry"* %"entry.arg") !dbg !27
{
entry:
  %"entry.1" = alloca %"struct.ritz_module_1.TestEntry"*
  store %"struct.ritz_module_1.TestEntry"* %"entry.arg", %"struct.ritz_module_1.TestEntry"** %"entry.1"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.TestEntry"** %"entry.1", metadata !117, metadata !7), !dbg !118
  %".5" = load i64, i64* @"g_base_addr", !dbg !119
  %".6" = load %"struct.ritz_module_1.TestEntry"*, %"struct.ritz_module_1.TestEntry"** %"entry.1", !dbg !119
  %".7" = getelementptr %"struct.ritz_module_1.TestEntry", %"struct.ritz_module_1.TestEntry"* %".6", i32 0, i32 1 , !dbg !119
  %".8" = load i64, i64* %".7", !dbg !119
  %".9" = add i64 %".5", %".8", !dbg !119
  %".10" = inttoptr i64 %".9" to i32 ()* , !dbg !120
  %".11" = call i32 %".10"(), !dbg !121
  ret i32 %".11", !dbg !121
}

define i32 @"run_test_forked"(%"struct.ritz_module_1.TestEntry"* %"entry.arg", %"struct.ritz_module_1.TestRunResult"* %"result.arg") !dbg !28
{
entry:
  %"entry.1" = alloca %"struct.ritz_module_1.TestEntry"*
  %"status.addr" = alloca i32, !dbg !140
  %"req.addr" = alloca [2 x i64], !dbg !170
  store %"struct.ritz_module_1.TestEntry"* %"entry.arg", %"struct.ritz_module_1.TestEntry"** %"entry.1"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.TestEntry"** %"entry.1", metadata !122, metadata !7), !dbg !123
  %"result" = alloca %"struct.ritz_module_1.TestRunResult"*
  store %"struct.ritz_module_1.TestRunResult"* %"result.arg", %"struct.ritz_module_1.TestRunResult"** %"result"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.TestRunResult"** %"result", metadata !126, metadata !7), !dbg !123
  %".8" = call i32 @"sys_fork"(), !dbg !127
  %".9" = sext i32 %".8" to i64 , !dbg !128
  %".10" = icmp slt i64 %".9", 0 , !dbg !128
  br i1 %".10", label %"if.then", label %"if.end", !dbg !128
if.then:
  %".12" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !129
  %".13" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".12", i32 0, i32 0 , !dbg !129
  store i32 1, i32* %".13", !dbg !129
  %".15" = sub i64 0, 1, !dbg !130
  %".16" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !130
  %".17" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".16", i32 0, i32 1 , !dbg !130
  %".18" = trunc i64 %".15" to i32 , !dbg !130
  store i32 %".18", i32* %".17", !dbg !130
  %".20" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !131
  %".21" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".20", i32 0, i32 2 , !dbg !131
  %".22" = trunc i64 0 to i32 , !dbg !131
  store i32 %".22", i32* %".21", !dbg !131
  %".24" = sub i64 0, 1, !dbg !132
  %".25" = trunc i64 %".24" to i32 , !dbg !132
  ret i32 %".25", !dbg !132
if.end:
  %".27" = sext i32 %".8" to i64 , !dbg !133
  %".28" = icmp eq i64 %".27", 0 , !dbg !133
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !133
if.then.1:
  %".30" = load i64, i64* @"g_base_addr", !dbg !134
  %".31" = load %"struct.ritz_module_1.TestEntry"*, %"struct.ritz_module_1.TestEntry"** %"entry.1", !dbg !134
  %".32" = getelementptr %"struct.ritz_module_1.TestEntry", %"struct.ritz_module_1.TestEntry"* %".31", i32 0, i32 1 , !dbg !134
  %".33" = load i64, i64* %".32", !dbg !134
  %".34" = add i64 %".30", %".33", !dbg !134
  %".35" = inttoptr i64 %".34" to i32 ()* , !dbg !135
  %".36" = call i32 %".35"(), !dbg !136
  %".37" = call i32 @"sys_exit"(i32 %".36"), !dbg !137
  %".38" = trunc i64 0 to i32 , !dbg !138
  ret i32 %".38", !dbg !138
if.end.1:
  %".40" = call i64 @"get_time_ms"(), !dbg !139
  %".41" = trunc i64 0 to i32 , !dbg !140
  store i32 %".41", i32* %"status.addr", !dbg !140
  call void @"llvm.dbg.declare"(metadata i32* %"status.addr", metadata !141, metadata !7), !dbg !142
  br label %"while.cond", !dbg !143
while.cond:
  br i1 1, label %"while.body", label %"while.end", !dbg !143
while.body:
  %".46" = call i32 @"sys_wait4"(i32 %".8", i32* %"status.addr", i32 1, i8* null), !dbg !144
  %".47" = sext i32 %".46" to i64 , !dbg !145
  %".48" = icmp sgt i64 %".47", 0 , !dbg !145
  br i1 %".48", label %"if.then.2", label %"if.end.2", !dbg !145
while.end:
  %".146" = trunc i64 0 to i32 , !dbg !178
  ret i32 %".146", !dbg !178
if.then.2:
  %".50" = load i32, i32* %"status.addr", !dbg !145
  %".51" = call i32 @"WIFEXITED"(i32 %".50"), !dbg !145
  %".52" = sext i32 %".51" to i64 , !dbg !145
  %".53" = icmp ne i64 %".52", 0 , !dbg !145
  br i1 %".53", label %"if.then.3", label %"if.else", !dbg !145
if.end.2:
  %".98" = sext i32 %".46" to i64 , !dbg !157
  %".99" = icmp slt i64 %".98", 0 , !dbg !157
  br i1 %".99", label %"if.then.6", label %"if.end.6", !dbg !157
if.then.3:
  %".55" = load i32, i32* %"status.addr", !dbg !146
  %".56" = call i32 @"WEXITSTATUS"(i32 %".55"), !dbg !146
  %".57" = sext i32 %".56" to i64 , !dbg !147
  %".58" = icmp eq i64 %".57", 0 , !dbg !147
  br i1 %".58", label %"if.then.4", label %"if.else.1", !dbg !147
if.else:
  %".77" = load i32, i32* %"status.addr", !dbg !152
  %".78" = call i32 @"WIFSIGNALED"(i32 %".77"), !dbg !152
  %".79" = sext i32 %".78" to i64 , !dbg !152
  %".80" = icmp ne i64 %".79", 0 , !dbg !152
  br i1 %".80", label %"if.then.5", label %"if.end.5", !dbg !152
if.end.3:
  br label %"if.end.2", !dbg !156
if.then.4:
  %".60" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !148
  %".61" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".60", i32 0, i32 0 , !dbg !148
  store i32 0, i32* %".61", !dbg !148
  br label %"if.end.4", !dbg !149
if.else.1:
  %".63" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !149
  %".64" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".63", i32 0, i32 0 , !dbg !149
  store i32 1, i32* %".64", !dbg !149
  br label %"if.end.4", !dbg !149
if.end.4:
  %".68" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !150
  %".69" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".68", i32 0, i32 1 , !dbg !150
  store i32 %".56", i32* %".69", !dbg !150
  %".71" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !151
  %".72" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".71", i32 0, i32 2 , !dbg !151
  %".73" = trunc i64 0 to i32 , !dbg !151
  store i32 %".73", i32* %".72", !dbg !151
  %".75" = trunc i64 0 to i32 , !dbg !152
  ret i32 %".75", !dbg !152
if.then.5:
  %".82" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !153
  %".83" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".82", i32 0, i32 0 , !dbg !153
  store i32 2, i32* %".83", !dbg !153
  %".85" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !154
  %".86" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".85", i32 0, i32 1 , !dbg !154
  %".87" = trunc i64 0 to i32 , !dbg !154
  store i32 %".87", i32* %".86", !dbg !154
  %".89" = load i32, i32* %"status.addr", !dbg !155
  %".90" = call i32 @"WTERMSIG"(i32 %".89"), !dbg !155
  %".91" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !155
  %".92" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".91", i32 0, i32 2 , !dbg !155
  store i32 %".90", i32* %".92", !dbg !155
  %".94" = trunc i64 0 to i32 , !dbg !156
  ret i32 %".94", !dbg !156
if.end.5:
  br label %"if.end.3", !dbg !156
if.then.6:
  %".101" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !158
  %".102" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".101", i32 0, i32 0 , !dbg !158
  store i32 1, i32* %".102", !dbg !158
  %".104" = sub i64 0, 1, !dbg !159
  %".105" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !159
  %".106" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".105", i32 0, i32 1 , !dbg !159
  %".107" = trunc i64 %".104" to i32 , !dbg !159
  store i32 %".107", i32* %".106", !dbg !159
  %".109" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !160
  %".110" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".109", i32 0, i32 2 , !dbg !160
  %".111" = trunc i64 0 to i32 , !dbg !160
  store i32 %".111", i32* %".110", !dbg !160
  %".113" = sub i64 0, 1, !dbg !161
  %".114" = trunc i64 %".113" to i32 , !dbg !161
  ret i32 %".114", !dbg !161
if.end.6:
  %".116" = call i64 @"get_time_ms"(), !dbg !162
  %".117" = sub i64 %".116", %".40", !dbg !162
  %".118" = load i64, i64* @"g_timeout_ms", !dbg !163
  %".119" = icmp sge i64 %".117", %".118" , !dbg !163
  br i1 %".119", label %"if.then.7", label %"if.end.7", !dbg !163
if.then.7:
  %".121" = call i32 @"sys_kill"(i32 %".8", i32 9), !dbg !164
  %".122" = trunc i64 0 to i32 , !dbg !165
  %".123" = call i32 @"sys_wait4"(i32 %".8", i32* %"status.addr", i32 %".122", i8* null), !dbg !165
  %".124" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !166
  %".125" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".124", i32 0, i32 0 , !dbg !166
  store i32 3, i32* %".125", !dbg !166
  %".127" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !167
  %".128" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".127", i32 0, i32 1 , !dbg !167
  %".129" = trunc i64 0 to i32 , !dbg !167
  store i32 %".129", i32* %".128", !dbg !167
  %".131" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !168
  %".132" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".131", i32 0, i32 2 , !dbg !168
  %".133" = trunc i64 0 to i32 , !dbg !168
  store i32 %".133", i32* %".132", !dbg !168
  %".135" = trunc i64 0 to i32 , !dbg !169
  ret i32 %".135", !dbg !169
if.end.7:
  call void @"llvm.dbg.declare"(metadata [2 x i64]* %"req.addr", metadata !174, metadata !7), !dbg !175
  %".138" = getelementptr [2 x i64], [2 x i64]* %"req.addr", i32 0, i64 0 , !dbg !176
  store i64 0, i64* %".138", !dbg !176
  %".140" = getelementptr [2 x i64], [2 x i64]* %"req.addr", i32 0, i64 1 , !dbg !177
  store i64 1000000, i64* %".140", !dbg !177
  %".142" = getelementptr [2 x i64], [2 x i64]* %"req.addr", i32 0, i64 0 , !dbg !177
  %".143" = bitcast i8* null to i64* , !dbg !177
  %".144" = call i32 @"sys_nanosleep"(i64* %".142", i64* %".143"), !dbg !177
  br label %"while.cond", !dbg !177
}

define i32 @"run_test"(%"struct.ritz_module_1.TestEntry"* %"entry.arg") !dbg !29
{
entry:
  %"entry.1" = alloca %"struct.ritz_module_1.TestEntry"*
  %"result.addr" = alloca %"struct.ritz_module_1.TestRunResult", !dbg !183
  store %"struct.ritz_module_1.TestEntry"* %"entry.arg", %"struct.ritz_module_1.TestEntry"** %"entry.1"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.TestEntry"** %"entry.1", metadata !179, metadata !7), !dbg !180
  %".5" = load i32, i32* @"g_no_fork", !dbg !181
  %".6" = sext i32 %".5" to i64 , !dbg !181
  %".7" = icmp ne i64 %".6", 0 , !dbg !181
  br i1 %".7", label %"if.then", label %"if.end", !dbg !181
if.then:
  %".9" = load %"struct.ritz_module_1.TestEntry"*, %"struct.ritz_module_1.TestEntry"** %"entry.1", !dbg !182
  %".10" = call i32 @"run_test_direct"(%"struct.ritz_module_1.TestEntry"* %".9"), !dbg !182
  ret i32 %".10", !dbg !182
if.end:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.TestRunResult"* %"result.addr", metadata !184, metadata !7), !dbg !185
  %".13" = load %"struct.ritz_module_1.TestEntry"*, %"struct.ritz_module_1.TestEntry"** %"entry.1", !dbg !186
  %".14" = call i32 @"run_test_forked"(%"struct.ritz_module_1.TestEntry"* %".13", %"struct.ritz_module_1.TestRunResult"* %"result.addr"), !dbg !186
  %".15" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %"result.addr", i32 0, i32 0 , !dbg !187
  %".16" = load i32, i32* %".15", !dbg !187
  %".17" = icmp eq i32 %".16", 0 , !dbg !187
  br i1 %".17", label %"if.then.1", label %"if.end.1", !dbg !187
if.then.1:
  %".19" = trunc i64 0 to i32 , !dbg !188
  ret i32 %".19", !dbg !188
if.end.1:
  %".21" = trunc i64 1 to i32 , !dbg !189
  ret i32 %".21", !dbg !189
}

define i32 @"run_test_with_result"(%"struct.ritz_module_1.TestEntry"* %"entry.arg", %"struct.ritz_module_1.TestRunResult"* %"result.arg") !dbg !30
{
entry:
  %"entry.1" = alloca %"struct.ritz_module_1.TestEntry"*
  store %"struct.ritz_module_1.TestEntry"* %"entry.arg", %"struct.ritz_module_1.TestEntry"** %"entry.1"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.TestEntry"** %"entry.1", metadata !190, metadata !7), !dbg !191
  %"result" = alloca %"struct.ritz_module_1.TestRunResult"*
  store %"struct.ritz_module_1.TestRunResult"* %"result.arg", %"struct.ritz_module_1.TestRunResult"** %"result"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.TestRunResult"** %"result", metadata !192, metadata !7), !dbg !191
  %".8" = load i32, i32* @"g_no_fork", !dbg !193
  %".9" = sext i32 %".8" to i64 , !dbg !193
  %".10" = icmp ne i64 %".9", 0 , !dbg !193
  br i1 %".10", label %"if.then", label %"if.else", !dbg !193
if.then:
  %".12" = load %"struct.ritz_module_1.TestEntry"*, %"struct.ritz_module_1.TestEntry"** %"entry.1", !dbg !194
  %".13" = call i32 @"run_test_direct"(%"struct.ritz_module_1.TestEntry"* %".12"), !dbg !194
  %".14" = sext i32 %".13" to i64 , !dbg !195
  %".15" = icmp eq i64 %".14", 0 , !dbg !195
  br i1 %".15", label %"if.then.1", label %"if.else.1", !dbg !195
if.else:
  %".32" = load %"struct.ritz_module_1.TestEntry"*, %"struct.ritz_module_1.TestEntry"** %"entry.1", !dbg !199
  %".33" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !199
  %".34" = call i32 @"run_test_forked"(%"struct.ritz_module_1.TestEntry"* %".32", %"struct.ritz_module_1.TestRunResult"* %".33"), !dbg !199
  br label %"if.end", !dbg !199
if.end:
  ret i32 0, !dbg !199
if.then.1:
  %".17" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !196
  %".18" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".17", i32 0, i32 0 , !dbg !196
  store i32 0, i32* %".18", !dbg !196
  br label %"if.end.1", !dbg !197
if.else.1:
  %".20" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !197
  %".21" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".20", i32 0, i32 0 , !dbg !197
  store i32 1, i32* %".21", !dbg !197
  br label %"if.end.1", !dbg !197
if.end.1:
  %".25" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !198
  %".26" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".25", i32 0, i32 1 , !dbg !198
  store i32 %".13", i32* %".26", !dbg !198
  %".28" = load %"struct.ritz_module_1.TestRunResult"*, %"struct.ritz_module_1.TestRunResult"** %"result", !dbg !199
  %".29" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %".28", i32 0, i32 2 , !dbg !199
  %".30" = trunc i64 0 to i32 , !dbg !199
  store i32 %".30", i32* %".29", !dbg !199
  br label %"if.end", !dbg !199
}

define i32 @"is_test_name"(i8* %"name.arg") !dbg !31
{
entry:
  %"name" = alloca i8*
  store i8* %"name.arg", i8** %"name"
  call void @"llvm.dbg.declare"(metadata i8** %"name", metadata !201, metadata !7), !dbg !202
  %".5" = load i8*, i8** %"name", !dbg !203
  %".6" = load i8, i8* %".5", !dbg !203
  %".7" = icmp ne i8 %".6", 116 , !dbg !203
  br i1 %".7", label %"if.then", label %"if.end", !dbg !203
if.then:
  %".9" = trunc i64 0 to i32 , !dbg !204
  ret i32 %".9", !dbg !204
if.end:
  %".11" = load i8*, i8** %"name", !dbg !205
  %".12" = getelementptr i8, i8* %".11", i64 1 , !dbg !205
  %".13" = load i8, i8* %".12", !dbg !205
  %".14" = icmp ne i8 %".13", 101 , !dbg !205
  br i1 %".14", label %"if.then.1", label %"if.end.1", !dbg !205
if.then.1:
  %".16" = trunc i64 0 to i32 , !dbg !206
  ret i32 %".16", !dbg !206
if.end.1:
  %".18" = load i8*, i8** %"name", !dbg !207
  %".19" = getelementptr i8, i8* %".18", i64 2 , !dbg !207
  %".20" = load i8, i8* %".19", !dbg !207
  %".21" = icmp ne i8 %".20", 115 , !dbg !207
  br i1 %".21", label %"if.then.2", label %"if.end.2", !dbg !207
if.then.2:
  %".23" = trunc i64 0 to i32 , !dbg !208
  ret i32 %".23", !dbg !208
if.end.2:
  %".25" = load i8*, i8** %"name", !dbg !209
  %".26" = getelementptr i8, i8* %".25", i64 3 , !dbg !209
  %".27" = load i8, i8* %".26", !dbg !209
  %".28" = icmp ne i8 %".27", 116 , !dbg !209
  br i1 %".28", label %"if.then.3", label %"if.end.3", !dbg !209
if.then.3:
  %".30" = trunc i64 0 to i32 , !dbg !210
  ret i32 %".30", !dbg !210
if.end.3:
  %".32" = load i8*, i8** %"name", !dbg !211
  %".33" = getelementptr i8, i8* %".32", i64 4 , !dbg !211
  %".34" = load i8, i8* %".33", !dbg !211
  %".35" = icmp ne i8 %".34", 95 , !dbg !211
  br i1 %".35", label %"if.then.4", label %"if.end.4", !dbg !211
if.then.4:
  %".37" = trunc i64 0 to i32 , !dbg !212
  ret i32 %".37", !dbg !212
if.end.4:
  %".39" = trunc i64 1 to i32 , !dbg !213
  ret i32 %".39", !dbg !213
}

define i32 @"discover_tests"() !dbg !32
{
entry:
  %"reader.addr" = alloca %"struct.ritz_module_1.ElfReader", !dbg !236
  %"i.addr" = alloca i64, !dbg !249
  %".2" = call i64 @"detect_base_address"(), !dbg !214
  store i64 %".2", i64* @"g_base_addr", !dbg !214
  %".4" = getelementptr [15 x i8], [15 x i8]* @".str.1", i64 0, i64 0 , !dbg !215
  %".5" = call i32 @"sys_open"(i8* %".4", i32 0), !dbg !215
  %".6" = sext i32 %".5" to i64 , !dbg !216
  %".7" = icmp slt i64 %".6", 0 , !dbg !216
  br i1 %".7", label %"if.then", label %"if.end", !dbg !216
if.then:
  %".9" = getelementptr [41 x i8], [41 x i8]* @".str.2", i64 0, i64 0 , !dbg !217
  %".10" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".9", 0 , !dbg !217
  %".11" = insertvalue %"struct.ritz_module_1.StrView" %".10", i64 40, 1 , !dbg !217
  %".12" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".11"), !dbg !217
  %".13" = sub i64 0, 1, !dbg !218
  %".14" = trunc i64 %".13" to i32 , !dbg !218
  ret i32 %".14", !dbg !218
if.end:
  %".16" = call i64 @"sys_lseek"(i32 %".5", i64 0, i32 2), !dbg !219
  %".17" = call i64 @"sys_lseek"(i32 %".5", i64 0, i32 0), !dbg !220
  %".18" = icmp sle i64 %".16", 0 , !dbg !221
  br i1 %".18", label %"if.then.1", label %"if.end.1", !dbg !221
if.then.1:
  %".20" = call i32 @"sys_close"(i32 %".5"), !dbg !222
  %".21" = getelementptr [37 x i8], [37 x i8]* @".str.3", i64 0, i64 0 , !dbg !223
  %".22" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".21", 0 , !dbg !223
  %".23" = insertvalue %"struct.ritz_module_1.StrView" %".22", i64 36, 1 , !dbg !223
  %".24" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".23"), !dbg !223
  %".25" = sub i64 0, 1, !dbg !224
  %".26" = trunc i64 %".25" to i32 , !dbg !224
  ret i32 %".26", !dbg !224
if.end.1:
  %".28" = call i8* @"malloc"(i64 %".16"), !dbg !225
  %".29" = icmp eq i8* %".28", null , !dbg !226
  br i1 %".29", label %"if.then.2", label %"if.end.2", !dbg !226
if.then.2:
  %".31" = call i32 @"sys_close"(i32 %".5"), !dbg !227
  %".32" = getelementptr [37 x i8], [37 x i8]* @".str.4", i64 0, i64 0 , !dbg !228
  %".33" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".32", 0 , !dbg !228
  %".34" = insertvalue %"struct.ritz_module_1.StrView" %".33", i64 36, 1 , !dbg !228
  %".35" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".34"), !dbg !228
  %".36" = sub i64 0, 1, !dbg !229
  %".37" = trunc i64 %".36" to i32 , !dbg !229
  ret i32 %".37", !dbg !229
if.end.2:
  %".39" = call i64 @"sys_read"(i32 %".5", i8* %".28", i64 %".16"), !dbg !230
  %".40" = call i32 @"sys_close"(i32 %".5"), !dbg !231
  %".41" = icmp ne i64 %".39", %".16" , !dbg !232
  br i1 %".41", label %"if.then.3", label %"if.end.3", !dbg !232
if.then.3:
  %".43" = call i32 @"free"(i8* %".28"), !dbg !233
  %".44" = getelementptr [33 x i8], [33 x i8]* @".str.5", i64 0, i64 0 , !dbg !234
  %".45" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".44", 0 , !dbg !234
  %".46" = insertvalue %"struct.ritz_module_1.StrView" %".45", i64 32, 1 , !dbg !234
  %".47" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".46"), !dbg !234
  %".48" = sub i64 0, 1, !dbg !235
  %".49" = trunc i64 %".48" to i32 , !dbg !235
  ret i32 %".49", !dbg !235
if.end.3:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ElfReader"* %"reader.addr", metadata !238, metadata !7), !dbg !239
  %".52" = call i32 @"elf_init"(%"struct.ritz_module_1.ElfReader"* %"reader.addr", i8* %".28", i64 %".16"), !dbg !240
  %".53" = sext i32 %".52" to i64 , !dbg !240
  %".54" = icmp ne i64 %".53", 0 , !dbg !240
  br i1 %".54", label %"if.then.4", label %"if.end.4", !dbg !240
if.then.4:
  %".56" = call i32 @"free"(i8* %".28"), !dbg !241
  %".57" = getelementptr [36 x i8], [36 x i8]* @".str.6", i64 0, i64 0 , !dbg !242
  %".58" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".57", 0 , !dbg !242
  %".59" = insertvalue %"struct.ritz_module_1.StrView" %".58", i64 35, 1 , !dbg !242
  %".60" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".59"), !dbg !242
  %".61" = sub i64 0, 1, !dbg !243
  %".62" = trunc i64 %".61" to i32 , !dbg !243
  ret i32 %".62", !dbg !243
if.end.4:
  %".64" = call i32 @"elf_parse_sections"(%"struct.ritz_module_1.ElfReader"* %"reader.addr"), !dbg !244
  %".65" = sext i32 %".64" to i64 , !dbg !244
  %".66" = icmp ne i64 %".65", 0 , !dbg !244
  br i1 %".66", label %"if.then.5", label %"if.end.5", !dbg !244
if.then.5:
  %".68" = call i32 @"free"(i8* %".28"), !dbg !245
  %".69" = getelementptr [40 x i8], [40 x i8]* @".str.7", i64 0, i64 0 , !dbg !246
  %".70" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".69", 0 , !dbg !246
  %".71" = insertvalue %"struct.ritz_module_1.StrView" %".70", i64 39, 1 , !dbg !246
  %".72" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".71"), !dbg !246
  %".73" = sub i64 0, 1, !dbg !247
  %".74" = trunc i64 %".73" to i32 , !dbg !247
  ret i32 %".74", !dbg !247
if.end.5:
  %".76" = trunc i64 0 to i32 , !dbg !248
  store i32 %".76", i32* @"g_test_count", !dbg !248
  store i64 0, i64* %"i.addr", !dbg !249
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !250, metadata !7), !dbg !251
  br label %"while.cond", !dbg !252
while.cond:
  %".81" = load i64, i64* %"i.addr", !dbg !252
  %".82" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %"reader.addr", i32 0, i32 5 , !dbg !252
  %".83" = load i64, i64* %".82", !dbg !252
  %".84" = icmp slt i64 %".81", %".83" , !dbg !252
  br i1 %".84", label %"and.right", label %"and.merge", !dbg !252
while.body:
  %".91" = load i64, i64* %"i.addr", !dbg !253
  %".92" = call i8 @"elf_get_symbol_info"(%"struct.ritz_module_1.ElfReader"* %"reader.addr", i64 %".91"), !dbg !253
  %".93" = call i32 @"elf_is_function"(i8 %".92"), !dbg !254
  %".94" = sext i32 %".93" to i64 , !dbg !254
  %".95" = icmp ne i64 %".94", 0 , !dbg !254
  br i1 %".95", label %"if.then.6", label %"if.end.6", !dbg !254
while.end:
  %".140" = load i32, i32* @"g_test_count", !dbg !262
  ret i32 %".140", !dbg !262
and.right:
  %".86" = load i32, i32* @"g_test_count", !dbg !252
  %".87" = icmp slt i32 %".86", 1024 , !dbg !252
  br label %"and.merge", !dbg !252
and.merge:
  %".89" = phi  i1 [0, %"while.cond"], [%".87", %"and.right"] , !dbg !252
  br i1 %".89", label %"while.body", label %"while.end", !dbg !252
if.then.6:
  %".97" = load i64, i64* %"i.addr", !dbg !255
  %".98" = call i8* @"elf_get_symbol_name"(%"struct.ritz_module_1.ElfReader"* %"reader.addr", i64 %".97"), !dbg !255
  %".99" = icmp ne i8* %".98", null , !dbg !255
  br i1 %".99", label %"and.right.1", label %"and.merge.1", !dbg !255
if.end.6:
  %".136" = load i64, i64* %"i.addr", !dbg !261
  %".137" = add i64 %".136", 1, !dbg !261
  store i64 %".137", i64* %"i.addr", !dbg !261
  br label %"while.cond", !dbg !261
and.right.1:
  %".101" = call i32 @"is_test_name"(i8* %".98"), !dbg !255
  %".102" = sext i32 %".101" to i64 , !dbg !255
  %".103" = icmp ne i64 %".102", 0 , !dbg !255
  br label %"and.merge.1", !dbg !255
and.merge.1:
  %".105" = phi  i1 [0, %"if.then.6"], [%".103", %"and.right.1"] , !dbg !255
  br i1 %".105", label %"if.then.7", label %"if.end.7", !dbg !255
if.then.7:
  %".107" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %"reader.addr", i32 0, i32 4 , !dbg !256
  %".108" = load %"struct.ritz_module_1.Elf64_Sym"*, %"struct.ritz_module_1.Elf64_Sym"** %".107", !dbg !256
  %".109" = bitcast %"struct.ritz_module_1.Elf64_Sym"* %".108" to i8* , !dbg !256
  %".110" = load i64, i64* %"i.addr", !dbg !256
  %".111" = mul i64 %".110", 24, !dbg !256
  %".112" = getelementptr i8, i8* %".109", i64 %".111" , !dbg !256
  %".113" = getelementptr i8, i8* %".112", i64 8 , !dbg !257
  %".114" = call i64 @"read_u64"(i8* %".113"), !dbg !257
  %".115" = load i32, i32* @"g_test_count", !dbg !258
  %".116" = getelementptr [1024 x %"struct.ritz_module_1.TestEntry"], [1024 x %"struct.ritz_module_1.TestEntry"]* @"g_tests", i32 0, i32 %".115" , !dbg !258
  %".117" = load %"struct.ritz_module_1.TestEntry", %"struct.ritz_module_1.TestEntry"* %".116", !dbg !258
  %".118" = load i32, i32* @"g_test_count", !dbg !258
  %".119" = getelementptr [1024 x %"struct.ritz_module_1.TestEntry"], [1024 x %"struct.ritz_module_1.TestEntry"]* @"g_tests", i32 0, i32 %".118" , !dbg !258
  %".120" = getelementptr %"struct.ritz_module_1.TestEntry", %"struct.ritz_module_1.TestEntry"* %".119", i32 0, i32 0 , !dbg !258
  store i8* %".98", i8** %".120", !dbg !258
  %".122" = load i32, i32* @"g_test_count", !dbg !259
  %".123" = getelementptr [1024 x %"struct.ritz_module_1.TestEntry"], [1024 x %"struct.ritz_module_1.TestEntry"]* @"g_tests", i32 0, i32 %".122" , !dbg !259
  %".124" = load %"struct.ritz_module_1.TestEntry", %"struct.ritz_module_1.TestEntry"* %".123", !dbg !259
  %".125" = load i32, i32* @"g_test_count", !dbg !259
  %".126" = getelementptr [1024 x %"struct.ritz_module_1.TestEntry"], [1024 x %"struct.ritz_module_1.TestEntry"]* @"g_tests", i32 0, i32 %".125" , !dbg !259
  %".127" = getelementptr %"struct.ritz_module_1.TestEntry", %"struct.ritz_module_1.TestEntry"* %".126", i32 0, i32 1 , !dbg !259
  store i64 %".114", i64* %".127", !dbg !259
  %".129" = load i32, i32* @"g_test_count", !dbg !260
  %".130" = sext i32 %".129" to i64 , !dbg !260
  %".131" = add i64 %".130", 1, !dbg !260
  %".132" = trunc i64 %".131" to i32 , !dbg !260
  store i32 %".132", i32* @"g_test_count", !dbg !260
  br label %"if.end.7", !dbg !260
if.end.7:
  br label %"if.end.6", !dbg !260
}

define %"struct.ritz_module_1.StrView" @"signal_name"(i32 %"sig.arg") !dbg !33
{
entry:
  %"sig" = alloca i32
  store i32 %"sig.arg", i32* %"sig"
  call void @"llvm.dbg.declare"(metadata i32* %"sig", metadata !263, metadata !7), !dbg !264
  %".5" = load i32, i32* %"sig", !dbg !265
  %".6" = icmp eq i32 %".5", 11 , !dbg !265
  br i1 %".6", label %"if.then", label %"if.end", !dbg !265
if.then:
  %".8" = getelementptr [8 x i8], [8 x i8]* @".str.8", i64 0, i64 0 , !dbg !266
  %".9" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".8", 0 , !dbg !266
  %".10" = insertvalue %"struct.ritz_module_1.StrView" %".9", i64 7, 1 , !dbg !266
  ret %"struct.ritz_module_1.StrView" %".10", !dbg !266
if.end:
  %".12" = load i32, i32* %"sig", !dbg !267
  %".13" = icmp eq i32 %".12", 6 , !dbg !267
  br i1 %".13", label %"if.then.1", label %"if.end.1", !dbg !267
if.then.1:
  %".15" = getelementptr [8 x i8], [8 x i8]* @".str.9", i64 0, i64 0 , !dbg !268
  %".16" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".15", 0 , !dbg !268
  %".17" = insertvalue %"struct.ritz_module_1.StrView" %".16", i64 7, 1 , !dbg !268
  ret %"struct.ritz_module_1.StrView" %".17", !dbg !268
if.end.1:
  %".19" = load i32, i32* %"sig", !dbg !269
  %".20" = icmp eq i32 %".19", 8 , !dbg !269
  br i1 %".20", label %"if.then.2", label %"if.end.2", !dbg !269
if.then.2:
  %".22" = getelementptr [7 x i8], [7 x i8]* @".str.10", i64 0, i64 0 , !dbg !270
  %".23" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".22", 0 , !dbg !270
  %".24" = insertvalue %"struct.ritz_module_1.StrView" %".23", i64 6, 1 , !dbg !270
  ret %"struct.ritz_module_1.StrView" %".24", !dbg !270
if.end.2:
  %".26" = load i32, i32* %"sig", !dbg !271
  %".27" = icmp eq i32 %".26", 4 , !dbg !271
  br i1 %".27", label %"if.then.3", label %"if.end.3", !dbg !271
if.then.3:
  %".29" = getelementptr [7 x i8], [7 x i8]* @".str.11", i64 0, i64 0 , !dbg !272
  %".30" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".29", 0 , !dbg !272
  %".31" = insertvalue %"struct.ritz_module_1.StrView" %".30", i64 6, 1 , !dbg !272
  ret %"struct.ritz_module_1.StrView" %".31", !dbg !272
if.end.3:
  %".33" = load i32, i32* %"sig", !dbg !273
  %".34" = icmp eq i32 %".33", 7 , !dbg !273
  br i1 %".34", label %"if.then.4", label %"if.end.4", !dbg !273
if.then.4:
  %".36" = getelementptr [7 x i8], [7 x i8]* @".str.12", i64 0, i64 0 , !dbg !274
  %".37" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".36", 0 , !dbg !274
  %".38" = insertvalue %"struct.ritz_module_1.StrView" %".37", i64 6, 1 , !dbg !274
  ret %"struct.ritz_module_1.StrView" %".38", !dbg !274
if.end.4:
  %".40" = load i32, i32* %"sig", !dbg !275
  %".41" = icmp eq i32 %".40", 9 , !dbg !275
  br i1 %".41", label %"if.then.5", label %"if.end.5", !dbg !275
if.then.5:
  %".43" = getelementptr [8 x i8], [8 x i8]* @".str.13", i64 0, i64 0 , !dbg !276
  %".44" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".43", 0 , !dbg !276
  %".45" = insertvalue %"struct.ritz_module_1.StrView" %".44", i64 7, 1 , !dbg !276
  ret %"struct.ritz_module_1.StrView" %".45", !dbg !276
if.end.5:
  %".47" = load i32, i32* %"sig", !dbg !277
  %".48" = icmp eq i32 %".47", 15 , !dbg !277
  br i1 %".48", label %"if.then.6", label %"if.end.6", !dbg !277
if.then.6:
  %".50" = getelementptr [8 x i8], [8 x i8]* @".str.14", i64 0, i64 0 , !dbg !278
  %".51" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".50", 0 , !dbg !278
  %".52" = insertvalue %"struct.ritz_module_1.StrView" %".51", i64 7, 1 , !dbg !278
  ret %"struct.ritz_module_1.StrView" %".52", !dbg !278
if.end.6:
  %".54" = load i32, i32* %"sig", !dbg !279
  %".55" = icmp eq i32 %".54", 2 , !dbg !279
  br i1 %".55", label %"if.then.7", label %"if.end.7", !dbg !279
if.then.7:
  %".57" = getelementptr [7 x i8], [7 x i8]* @".str.15", i64 0, i64 0 , !dbg !280
  %".58" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".57", 0 , !dbg !280
  %".59" = insertvalue %"struct.ritz_module_1.StrView" %".58", i64 6, 1 , !dbg !280
  ret %"struct.ritz_module_1.StrView" %".59", !dbg !280
if.end.7:
  %".61" = load i32, i32* %"sig", !dbg !281
  %".62" = icmp eq i32 %".61", 5 , !dbg !281
  br i1 %".62", label %"if.then.8", label %"if.end.8", !dbg !281
if.then.8:
  %".64" = getelementptr [8 x i8], [8 x i8]* @".str.16", i64 0, i64 0 , !dbg !282
  %".65" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".64", 0 , !dbg !282
  %".66" = insertvalue %"struct.ritz_module_1.StrView" %".65", i64 7, 1 , !dbg !282
  ret %"struct.ritz_module_1.StrView" %".66", !dbg !282
if.end.8:
  %".68" = load i32, i32* %"sig", !dbg !283
  %".69" = icmp eq i32 %".68", 13 , !dbg !283
  br i1 %".69", label %"if.then.9", label %"if.end.9", !dbg !283
if.then.9:
  %".71" = getelementptr [8 x i8], [8 x i8]* @".str.17", i64 0, i64 0 , !dbg !284
  %".72" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".71", 0 , !dbg !284
  %".73" = insertvalue %"struct.ritz_module_1.StrView" %".72", i64 7, 1 , !dbg !284
  ret %"struct.ritz_module_1.StrView" %".73", !dbg !284
if.end.9:
  %".75" = getelementptr [7 x i8], [7 x i8]* @".str.18", i64 0, i64 0 , !dbg !285
  %".76" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".75", 0 , !dbg !285
  %".77" = insertvalue %"struct.ritz_module_1.StrView" %".76", i64 6, 1 , !dbg !285
  ret %"struct.ritz_module_1.StrView" %".77", !dbg !285
}

define i32 @"run_tests"() !dbg !34
{
entry:
  %"seed.addr" = alloca i64, !dbg !294
  %"i" = alloca i32, !dbg !307
  %"summary.addr" = alloca %"struct.ritz_module_1.TestSummary", !dbg !313
  %"skipped_by_filter.addr" = alloca i32, !dbg !317
  %"i.1" = alloca i32, !dbg !321
  %"name.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !327
  %"result.addr" = alloca %"struct.ritz_module_1.TestRunResult", !dbg !332
  %"failed_this_test.addr" = alloca i32, !dbg !337
  %"sig_name.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !342
  %".2" = load i32, i32* @"g_quiet", !dbg !286
  %".3" = sext i32 %".2" to i64 , !dbg !286
  %".4" = icmp eq i64 %".3", 0 , !dbg !286
  br i1 %".4", label %"and.right", label %"and.merge", !dbg !286
and.right:
  %".6" = load i32, i32* @"g_json", !dbg !286
  %".7" = sext i32 %".6" to i64 , !dbg !286
  %".8" = icmp eq i64 %".7", 0 , !dbg !286
  br label %"and.merge", !dbg !286
and.merge:
  %".10" = phi  i1 [0, %"entry"], [%".8", %"and.right"] , !dbg !286
  br i1 %".10", label %"if.then", label %"if.end", !dbg !286
if.then:
  %".12" = call i32 @"print_banner"(), !dbg !286
  br label %"if.end", !dbg !286
if.end:
  %".14" = call i32 @"discover_tests"(), !dbg !287
  %".15" = sext i32 %".14" to i64 , !dbg !288
  %".16" = icmp slt i64 %".15", 0 , !dbg !288
  br i1 %".16", label %"if.then.1", label %"if.end.1", !dbg !288
if.then.1:
  %".18" = trunc i64 1 to i32 , !dbg !289
  ret i32 %".18", !dbg !289
if.end.1:
  %".20" = sext i32 %".14" to i64 , !dbg !290
  %".21" = icmp eq i64 %".20", 0 , !dbg !290
  br i1 %".21", label %"if.then.2", label %"if.end.2", !dbg !290
if.then.2:
  %".23" = load i32, i32* @"g_json", !dbg !291
  %".24" = sext i32 %".23" to i64 , !dbg !291
  %".25" = icmp ne i64 %".24", 0 , !dbg !291
  br i1 %".25", label %"if.then.3", label %"if.else", !dbg !291
if.end.2:
  %".43" = load i32, i32* @"g_shuffle", !dbg !293
  %".44" = sext i32 %".43" to i64 , !dbg !293
  %".45" = icmp ne i64 %".44", 0 , !dbg !293
  br i1 %".45", label %"if.then.4", label %"if.end.4", !dbg !293
if.then.3:
  %".27" = trunc i64 0 to i32 , !dbg !291
  %".28" = trunc i64 0 to i32 , !dbg !291
  %".29" = trunc i64 0 to i32 , !dbg !291
  %".30" = trunc i64 0 to i32 , !dbg !291
  %".31" = trunc i64 0 to i32 , !dbg !291
  %".32" = trunc i64 0 to i32 , !dbg !291
  %".33" = call i32 @"json_print_report"(i32 %".27", i32 %".28", i32 %".29", i32 %".30", i32 %".31", i32 %".32", i64 0), !dbg !291
  br label %"if.end.3", !dbg !291
if.else:
  %".34" = getelementptr [17 x i8], [17 x i8]* @".str.19", i64 0, i64 0 , !dbg !291
  %".35" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".34", 0 , !dbg !291
  %".36" = insertvalue %"struct.ritz_module_1.StrView" %".35", i64 16, 1 , !dbg !291
  %".37" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".36"), !dbg !291
  br label %"if.end.3", !dbg !291
if.end.3:
  %".40" = phi  i32 [%".33", %"if.then.3"], [%".37", %"if.else"] , !dbg !291
  %".41" = trunc i64 0 to i32 , !dbg !292
  ret i32 %".41", !dbg !292
if.then.4:
  %".47" = load i64, i64* @"g_seed", !dbg !294
  store i64 %".47", i64* %"seed.addr", !dbg !294
  call void @"llvm.dbg.declare"(metadata i64* %"seed.addr", metadata !295, metadata !7), !dbg !296
  %".50" = load i64, i64* %"seed.addr", !dbg !297
  %".51" = icmp eq i64 %".50", 0 , !dbg !297
  br i1 %".51", label %"if.then.5", label %"if.end.5", !dbg !297
if.end.4:
  %".75" = load i32, i32* @"g_list_only", !dbg !303
  %".76" = sext i32 %".75" to i64 , !dbg !303
  %".77" = icmp ne i64 %".76", 0 , !dbg !303
  br i1 %".77", label %"if.then.7", label %"if.end.7", !dbg !303
if.then.5:
  %".53" = call i64 @"get_time_us"(), !dbg !298
  store i64 %".53", i64* %"seed.addr", !dbg !298
  br label %"if.end.5", !dbg !298
if.end.5:
  %".56" = load i64, i64* %"seed.addr", !dbg !299
  %".57" = call i32 @"rng_seed"(i64 %".56"), !dbg !299
  %".58" = call i32 @"shuffle_tests"(i32 %".14"), !dbg !300
  %".59" = load i32, i32* @"g_verbose", !dbg !300
  %".60" = sext i32 %".59" to i64 , !dbg !300
  %".61" = icmp ne i64 %".60", 0 , !dbg !300
  br i1 %".61", label %"if.then.6", label %"if.end.6", !dbg !300
if.then.6:
  %".63" = getelementptr [27 x i8], [27 x i8]* @".str.20", i64 0, i64 0 , !dbg !301
  %".64" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".63", 0 , !dbg !301
  %".65" = insertvalue %"struct.ritz_module_1.StrView" %".64", i64 26, 1 , !dbg !301
  %".66" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".65"), !dbg !301
  %".67" = load i64, i64* %"seed.addr", !dbg !302
  %".68" = call i32 @"print_int"(i64 %".67"), !dbg !302
  %".69" = getelementptr [2 x i8], [2 x i8]* @".str.21", i64 0, i64 0 , !dbg !302
  %".70" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".69", 0 , !dbg !302
  %".71" = insertvalue %"struct.ritz_module_1.StrView" %".70", i64 1, 1 , !dbg !302
  %".72" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".71"), !dbg !302
  br label %"if.end.6", !dbg !302
if.end.6:
  br label %"if.end.4", !dbg !302
if.then.7:
  %".79" = getelementptr [12 x i8], [12 x i8]* @".str.22", i64 0, i64 0 , !dbg !304
  %".80" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".79", 0 , !dbg !304
  %".81" = insertvalue %"struct.ritz_module_1.StrView" %".80", i64 11, 1 , !dbg !304
  %".82" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".81"), !dbg !304
  %".83" = sext i32 %".14" to i64 , !dbg !305
  %".84" = call i32 @"print_int"(i64 %".83"), !dbg !305
  %".85" = getelementptr [11 x i8], [11 x i8]* @".str.23", i64 0, i64 0 , !dbg !306
  %".86" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".85", 0 , !dbg !306
  %".87" = insertvalue %"struct.ritz_module_1.StrView" %".86", i64 10, 1 , !dbg !306
  %".88" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".87"), !dbg !306
  store i32 0, i32* %"i", !dbg !307
  br label %"for.cond", !dbg !307
if.end.7:
  %".121" = load i32, i32* @"g_quiet", !dbg !312
  %".122" = sext i32 %".121" to i64 , !dbg !312
  %".123" = icmp eq i64 %".122", 0 , !dbg !312
  br i1 %".123", label %"if.then.9", label %"if.end.9", !dbg !312
for.cond:
  %".91" = load i32, i32* %"i", !dbg !307
  %".92" = icmp slt i32 %".91", %".14" , !dbg !307
  br i1 %".92", label %"for.body", label %"for.end", !dbg !307
for.body:
  %".94" = load i32, i32* %"i", !dbg !308
  %".95" = getelementptr [1024 x %"struct.ritz_module_1.TestEntry"], [1024 x %"struct.ritz_module_1.TestEntry"]* @"g_tests", i32 0, i32 %".94" , !dbg !308
  %".96" = getelementptr %"struct.ritz_module_1.TestEntry", %"struct.ritz_module_1.TestEntry"* %".95", i32 0, i32 0 , !dbg !308
  %".97" = load i8*, i8** %".96", !dbg !308
  %".98" = call i32 @"matches_filter"(i8* %".97"), !dbg !308
  %".99" = sext i32 %".98" to i64 , !dbg !308
  %".100" = icmp ne i64 %".99", 0 , !dbg !308
  br i1 %".100", label %"if.then.8", label %"if.end.8", !dbg !308
for.incr:
  %".115" = load i32, i32* %"i", !dbg !310
  %".116" = add i32 %".115", 1, !dbg !310
  store i32 %".116", i32* %"i", !dbg !310
  br label %"for.cond", !dbg !310
for.end:
  %".119" = trunc i64 0 to i32 , !dbg !311
  ret i32 %".119", !dbg !311
if.then.8:
  %".102" = getelementptr [3 x i8], [3 x i8]* @".str.24", i64 0, i64 0 , !dbg !309
  %".103" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".102", 0 , !dbg !309
  %".104" = insertvalue %"struct.ritz_module_1.StrView" %".103", i64 2, 1 , !dbg !309
  %".105" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".104"), !dbg !309
  %".106" = getelementptr %"struct.ritz_module_1.TestEntry", %"struct.ritz_module_1.TestEntry"* %".95", i32 0, i32 0 , !dbg !310
  %".107" = load i8*, i8** %".106", !dbg !310
  %".108" = call i32 @"prints_cstr"(i8* %".107"), !dbg !310
  %".109" = getelementptr [2 x i8], [2 x i8]* @".str.25", i64 0, i64 0 , !dbg !310
  %".110" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".109", 0 , !dbg !310
  %".111" = insertvalue %"struct.ritz_module_1.StrView" %".110", i64 1, 1 , !dbg !310
  %".112" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".111"), !dbg !310
  br label %"if.end.8", !dbg !310
if.end.8:
  br label %"for.incr", !dbg !310
if.then.9:
  %".125" = getelementptr [6 x i8], [6 x i8]* @".str.26", i64 0, i64 0 , !dbg !312
  %".126" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".125"), !dbg !312
  %".127" = call i32 @"print_suite_header"(%"struct.ritz_module_1.StrView" %".126"), !dbg !312
  br label %"if.end.9", !dbg !312
if.end.9:
  %".129" = call %"struct.ritz_module_1.TestSummary" @"summary_new"(), !dbg !313
  store %"struct.ritz_module_1.TestSummary" %".129", %"struct.ritz_module_1.TestSummary"* %"summary.addr", !dbg !313
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.TestSummary"* %"summary.addr", metadata !315, metadata !7), !dbg !316
  %".132" = trunc i64 0 to i32 , !dbg !317
  store i32 %".132", i32* %"skipped_by_filter.addr", !dbg !317
  call void @"llvm.dbg.declare"(metadata i32* %"skipped_by_filter.addr", metadata !318, metadata !7), !dbg !319
  %".135" = call i64 @"get_time_ms"(), !dbg !320
  store i32 0, i32* %"i.1", !dbg !321
  br label %"for.cond.1", !dbg !321
for.cond.1:
  %".138" = load i32, i32* %"i.1", !dbg !321
  %".139" = icmp slt i32 %".138", %".14" , !dbg !321
  br i1 %".139", label %"for.body.1", label %"for.end.1", !dbg !321
for.body.1:
  %".141" = load i32, i32* %"i.1", !dbg !322
  %".142" = getelementptr [1024 x %"struct.ritz_module_1.TestEntry"], [1024 x %"struct.ritz_module_1.TestEntry"]* @"g_tests", i32 0, i32 %".141" , !dbg !322
  %".143" = getelementptr %"struct.ritz_module_1.TestEntry", %"struct.ritz_module_1.TestEntry"* %".142", i32 0, i32 0 , !dbg !323
  %".144" = load i8*, i8** %".143", !dbg !323
  %".145" = call i32 @"matches_filter"(i8* %".144"), !dbg !324
  %".146" = sext i32 %".145" to i64 , !dbg !324
  %".147" = icmp eq i64 %".146", 0 , !dbg !324
  br i1 %".147", label %"if.then.10", label %"if.end.10", !dbg !324
for.incr.1:
  %".302" = load i32, i32* %"i.1", !dbg !354
  %".303" = add i32 %".302", 1, !dbg !354
  store i32 %".303", i32* %"i.1", !dbg !354
  br label %"for.cond.1", !dbg !354
for.end.1:
  %".306" = call i64 @"get_time_ms"(), !dbg !355
  %".307" = sub i64 %".306", %".135", !dbg !355
  %".308" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", !dbg !356
  %".309" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 6 , !dbg !356
  store i64 %".307", i64* %".309", !dbg !356
  %".311" = load i32, i32* @"g_json", !dbg !357
  %".312" = sext i32 %".311" to i64 , !dbg !357
  %".313" = icmp ne i64 %".312", 0 , !dbg !357
  br i1 %".313", label %"if.then.24", label %"if.else.12", !dbg !357
if.then.10:
  %".149" = load i32, i32* %"skipped_by_filter.addr", !dbg !325
  %".150" = sext i32 %".149" to i64 , !dbg !325
  %".151" = add i64 %".150", 1, !dbg !325
  %".152" = trunc i64 %".151" to i32 , !dbg !325
  store i32 %".152", i32* %"skipped_by_filter.addr", !dbg !325
  br label %"for.incr.1", !dbg !326
if.end.10:
  %".155" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".144"), !dbg !327
  store %"struct.ritz_module_1.StrView" %".155", %"struct.ritz_module_1.StrView"* %"name.addr", !dbg !327
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name.addr", metadata !329, metadata !7), !dbg !330
  %".158" = call i64 @"get_time_ms"(), !dbg !331
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.TestRunResult"* %"result.addr", metadata !333, metadata !7), !dbg !334
  %".160" = call i32 @"run_test_with_result"(%"struct.ritz_module_1.TestEntry"* %".142", %"struct.ritz_module_1.TestRunResult"* %"result.addr"), !dbg !335
  %".161" = call i64 @"get_time_ms"(), !dbg !336
  %".162" = sub i64 %".161", %".158", !dbg !336
  %".163" = trunc i64 0 to i32 , !dbg !337
  store i32 %".163", i32* %"failed_this_test.addr", !dbg !337
  call void @"llvm.dbg.declare"(metadata i32* %"failed_this_test.addr", metadata !338, metadata !7), !dbg !339
  %".166" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %"result.addr", i32 0, i32 0 , !dbg !340
  %".167" = load i32, i32* %".166", !dbg !340
  %".168" = icmp eq i32 %".167", 0 , !dbg !340
  br i1 %".168", label %"if.then.11", label %"if.else.1", !dbg !340
if.then.11:
  %".170" = load i32, i32* @"g_json", !dbg !341
  %".171" = sext i32 %".170" to i64 , !dbg !341
  %".172" = icmp ne i64 %".171", 0 , !dbg !341
  br i1 %".172", label %"if.then.12", label %"if.else.2", !dbg !341
if.else.1:
  %".192" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %"result.addr", i32 0, i32 0 , !dbg !341
  %".193" = load i32, i32* %".192", !dbg !341
  %".194" = icmp eq i32 %".193", 2 , !dbg !341
  br i1 %".194", label %"if.then.15", label %"if.else.4", !dbg !341
if.end.11:
  %".290" = load i32, i32* @"g_fail_fast", !dbg !353
  %".291" = sext i32 %".290" to i64 , !dbg !353
  %".292" = icmp ne i64 %".291", 0 , !dbg !353
  br i1 %".292", label %"and.right.1", label %"and.merge.1", !dbg !353
if.then.12:
  %".174" = call i32 @"json_record_pass"(%"struct.ritz_module_1.StrView"* %"name.addr", i64 %".162"), !dbg !341
  br label %"if.end.12", !dbg !341
if.else.2:
  %".175" = load i32, i32* @"g_junit", !dbg !341
  %".176" = sext i32 %".175" to i64 , !dbg !341
  %".177" = icmp ne i64 %".176", 0 , !dbg !341
  br i1 %".177", label %"if.then.13", label %"if.else.3", !dbg !341
if.end.12:
  %".191" = call i32 @"summary_record"(%"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i64 %".162"), !dbg !341
  br label %"if.end.11", !dbg !353
if.then.13:
  %".179" = call i32 @"junit_record_pass"(%"struct.ritz_module_1.StrView"* %"name.addr", i64 %".162"), !dbg !341
  br label %"if.end.13", !dbg !341
if.else.3:
  %".180" = load i32, i32* @"g_quiet", !dbg !341
  %".181" = sext i32 %".180" to i64 , !dbg !341
  %".182" = icmp eq i64 %".181", 0 , !dbg !341
  br i1 %".182", label %"if.then.14", label %"if.end.14", !dbg !341
if.end.13:
  br label %"if.end.12", !dbg !341
if.then.14:
  %".184" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".144"), !dbg !341
  %".185" = call i32 @"print_test_pass"(%"struct.ritz_module_1.StrView" %".184", i64 %".162"), !dbg !341
  br label %"if.end.14", !dbg !341
if.end.14:
  br label %"if.end.13", !dbg !341
if.then.15:
  %".196" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %"result.addr", i32 0, i32 2 , !dbg !342
  %".197" = load i32, i32* %".196", !dbg !342
  %".198" = call %"struct.ritz_module_1.StrView" @"signal_name"(i32 %".197"), !dbg !342
  store %"struct.ritz_module_1.StrView" %".198", %"struct.ritz_module_1.StrView"* %"sig_name.addr", !dbg !342
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"sig_name.addr", metadata !343, metadata !7), !dbg !344
  %".201" = load i32, i32* @"g_json", !dbg !345
  %".202" = sext i32 %".201" to i64 , !dbg !345
  %".203" = icmp ne i64 %".202", 0 , !dbg !345
  br i1 %".203", label %"if.then.16", label %"if.else.5", !dbg !345
if.else.4:
  %".231" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %"result.addr", i32 0, i32 0 , !dbg !347
  %".232" = load i32, i32* %".231", !dbg !347
  %".233" = icmp eq i32 %".232", 3 , !dbg !347
  br i1 %".233", label %"if.then.18", label %"if.else.7", !dbg !347
if.end.15:
  br label %"if.end.11", !dbg !353
if.then.16:
  %".205" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %"result.addr", i32 0, i32 2 , !dbg !345
  %".206" = load i32, i32* %".205", !dbg !345
  %".207" = call i32 @"json_record_crash"(%"struct.ritz_module_1.StrView"* %"name.addr", i64 %".162", i32 %".206"), !dbg !345
  br label %"if.end.16", !dbg !345
if.else.5:
  %".208" = load i32, i32* @"g_junit", !dbg !345
  %".209" = sext i32 %".208" to i64 , !dbg !345
  %".210" = icmp ne i64 %".209", 0 , !dbg !345
  br i1 %".210", label %"if.then.17", label %"if.else.6", !dbg !345
if.end.16:
  %".227" = phi  i32 [%".207", %"if.then.16"], [%".224", %"if.end.17"] , !dbg !345
  %".228" = call i32 @"summary_record"(%"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 4, i64 %".162"), !dbg !346
  %".229" = trunc i64 1 to i32 , !dbg !347
  store i32 %".229", i32* %"failed_this_test.addr", !dbg !347
  br label %"if.end.15", !dbg !353
if.then.17:
  %".212" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %"result.addr", i32 0, i32 2 , !dbg !345
  %".213" = load i32, i32* %".212", !dbg !345
  %".214" = call i32 @"junit_record_crash"(%"struct.ritz_module_1.StrView"* %"name.addr", i64 %".162", i32 %".213", %"struct.ritz_module_1.StrView"* %"sig_name.addr"), !dbg !345
  br label %"if.end.17", !dbg !345
if.else.6:
  %".215" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".144"), !dbg !345
  %".216" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %"result.addr", i32 0, i32 2 , !dbg !345
  %".217" = load i32, i32* %".216", !dbg !345
  %".218" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %"result.addr", i32 0, i32 2 , !dbg !345
  %".219" = load i32, i32* %".218", !dbg !345
  %".220" = call %"struct.ritz_module_1.StrView" @"signal_name"(i32 %".219"), !dbg !345
  %".221" = call i32 @"print_test_crash"(%"struct.ritz_module_1.StrView" %".215", i64 %".162", i32 %".217", %"struct.ritz_module_1.StrView" %".220"), !dbg !345
  br label %"if.end.17", !dbg !345
if.end.17:
  %".224" = phi  i32 [%".214", %"if.then.17"], [%".221", %"if.else.6"] , !dbg !345
  br label %"if.end.16", !dbg !345
if.then.18:
  %".235" = load i32, i32* @"g_json", !dbg !348
  %".236" = sext i32 %".235" to i64 , !dbg !348
  %".237" = icmp ne i64 %".236", 0 , !dbg !348
  br i1 %".237", label %"if.then.19", label %"if.else.8", !dbg !348
if.else.7:
  %".257" = load i32, i32* @"g_json", !dbg !351
  %".258" = sext i32 %".257" to i64 , !dbg !351
  %".259" = icmp ne i64 %".258", 0 , !dbg !351
  br i1 %".259", label %"if.then.21", label %"if.else.10", !dbg !351
if.end.18:
  br label %"if.end.15", !dbg !353
if.then.19:
  %".239" = call i32 @"json_record_timeout"(%"struct.ritz_module_1.StrView"* %"name.addr", i64 %".162"), !dbg !348
  br label %"if.end.19", !dbg !348
if.else.8:
  %".240" = load i32, i32* @"g_junit", !dbg !348
  %".241" = sext i32 %".240" to i64 , !dbg !348
  %".242" = icmp ne i64 %".241", 0 , !dbg !348
  br i1 %".242", label %"if.then.20", label %"if.else.9", !dbg !348
if.end.19:
  %".253" = phi  i32 [%".239", %"if.then.19"], [%".250", %"if.end.20"] , !dbg !348
  %".254" = call i32 @"summary_record"(%"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 3, i64 %".162"), !dbg !349
  %".255" = trunc i64 1 to i32 , !dbg !350
  store i32 %".255", i32* %"failed_this_test.addr", !dbg !350
  br label %"if.end.18", !dbg !353
if.then.20:
  %".244" = call i32 @"junit_record_timeout"(%"struct.ritz_module_1.StrView"* %"name.addr", i64 %".162"), !dbg !348
  br label %"if.end.20", !dbg !348
if.else.9:
  %".245" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".144"), !dbg !348
  %".246" = load i64, i64* @"g_timeout_ms", !dbg !348
  %".247" = call i32 @"print_test_timeout"(%"struct.ritz_module_1.StrView" %".245", i64 %".246"), !dbg !348
  br label %"if.end.20", !dbg !348
if.end.20:
  %".250" = phi  i32 [%".244", %"if.then.20"], [%".247", %"if.else.9"] , !dbg !348
  br label %"if.end.19", !dbg !348
if.then.21:
  %".261" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %"result.addr", i32 0, i32 1 , !dbg !351
  %".262" = load i32, i32* %".261", !dbg !351
  %".263" = call i32 @"json_record_fail"(%"struct.ritz_module_1.StrView"* %"name.addr", i64 %".162", i32 %".262"), !dbg !351
  br label %"if.end.21", !dbg !351
if.else.10:
  %".264" = load i32, i32* @"g_junit", !dbg !351
  %".265" = sext i32 %".264" to i64 , !dbg !351
  %".266" = icmp ne i64 %".265", 0 , !dbg !351
  br i1 %".266", label %"if.then.22", label %"if.else.11", !dbg !351
if.end.21:
  %".280" = phi  i32 [%".263", %"if.then.21"], [%".277", %"if.end.22"] , !dbg !351
  %".281" = call i32 @"summary_record"(%"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 1, i64 %".162"), !dbg !352
  %".282" = trunc i64 1 to i32 , !dbg !353
  store i32 %".282", i32* %"failed_this_test.addr", !dbg !353
  br label %"if.end.18", !dbg !353
if.then.22:
  %".268" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %"result.addr", i32 0, i32 1 , !dbg !351
  %".269" = load i32, i32* %".268", !dbg !351
  %".270" = call i32 @"junit_record_fail"(%"struct.ritz_module_1.StrView"* %"name.addr", i64 %".162", i32 %".269"), !dbg !351
  br label %"if.end.22", !dbg !351
if.else.11:
  %".271" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".144"), !dbg !351
  %".272" = getelementptr %"struct.ritz_module_1.TestRunResult", %"struct.ritz_module_1.TestRunResult"* %"result.addr", i32 0, i32 1 , !dbg !351
  %".273" = load i32, i32* %".272", !dbg !351
  %".274" = call i32 @"print_test_fail"(%"struct.ritz_module_1.StrView" %".271", i64 %".162", i32 %".273"), !dbg !351
  br label %"if.end.22", !dbg !351
if.end.22:
  %".277" = phi  i32 [%".270", %"if.then.22"], [%".274", %"if.else.11"] , !dbg !351
  br label %"if.end.21", !dbg !351
and.right.1:
  %".294" = load i32, i32* %"failed_this_test.addr", !dbg !353
  %".295" = sext i32 %".294" to i64 , !dbg !353
  %".296" = icmp ne i64 %".295", 0 , !dbg !353
  br label %"and.merge.1", !dbg !353
and.merge.1:
  %".298" = phi  i1 [0, %"if.end.11"], [%".296", %"and.right.1"] , !dbg !353
  br i1 %".298", label %"if.then.23", label %"if.end.23", !dbg !353
if.then.23:
  br label %"for.end.1", !dbg !354
if.end.23:
  br label %"for.incr.1", !dbg !354
if.then.24:
  %".315" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 0 , !dbg !357
  %".316" = load i32, i32* %".315", !dbg !357
  %".317" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 1 , !dbg !357
  %".318" = load i32, i32* %".317", !dbg !357
  %".319" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 2 , !dbg !357
  %".320" = load i32, i32* %".319", !dbg !357
  %".321" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 3 , !dbg !357
  %".322" = load i32, i32* %".321", !dbg !357
  %".323" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 4 , !dbg !357
  %".324" = load i32, i32* %".323", !dbg !357
  %".325" = load i32, i32* %"skipped_by_filter.addr", !dbg !357
  %".326" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 6 , !dbg !357
  %".327" = load i64, i64* %".326", !dbg !357
  %".328" = call i32 @"json_print_report"(i32 %".316", i32 %".318", i32 %".320", i32 %".322", i32 %".324", i32 %".325", i64 %".327"), !dbg !357
  br label %"if.end.24", !dbg !360
if.else.12:
  %".329" = load i32, i32* @"g_junit", !dbg !357
  %".330" = sext i32 %".329" to i64 , !dbg !357
  %".331" = icmp ne i64 %".330", 0 , !dbg !357
  br i1 %".331", label %"if.then.25", label %"if.else.13", !dbg !357
if.end.24:
  %".385" = phi  i32 [%".328", %"if.then.24"], [%".382", %"if.end.25"] , !dbg !360
  %".386" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 2 , !dbg !361
  %".387" = load i32, i32* %".386", !dbg !361
  %".388" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 3 , !dbg !361
  %".389" = load i32, i32* %".388", !dbg !361
  %".390" = add i32 %".387", %".389", !dbg !361
  %".391" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 4 , !dbg !361
  %".392" = load i32, i32* %".391", !dbg !361
  %".393" = add i32 %".390", %".392", !dbg !361
  ret i32 %".393", !dbg !361
if.then.25:
  %".333" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 3 , !dbg !358
  %".334" = load i32, i32* %".333", !dbg !358
  %".335" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 4 , !dbg !358
  %".336" = load i32, i32* %".335", !dbg !358
  %".337" = add i32 %".334", %".336", !dbg !358
  %".338" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 0 , !dbg !358
  %".339" = load i32, i32* %".338", !dbg !358
  %".340" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 1 , !dbg !358
  %".341" = load i32, i32* %".340", !dbg !358
  %".342" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 2 , !dbg !358
  %".343" = load i32, i32* %".342", !dbg !358
  %".344" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 6 , !dbg !358
  %".345" = load i64, i64* %".344", !dbg !358
  %".346" = call i32 @"junit_print_report"(i32 %".339", i32 %".341", i32 %".343", i32 %".337", i64 %".345"), !dbg !358
  br label %"if.end.25", !dbg !360
if.else.13:
  %".347" = load i32, i32* @"g_quiet", !dbg !359
  %".348" = sext i32 %".347" to i64 , !dbg !359
  %".349" = icmp eq i64 %".348", 0 , !dbg !359
  br i1 %".349", label %"if.then.26", label %"if.end.26", !dbg !359
if.end.25:
  %".382" = phi  i32 [%".346", %"if.then.25"], [%".379", %"if.end.26"] , !dbg !360
  br label %"if.end.24", !dbg !360
if.then.26:
  %".351" = call i32 @"print_suite_divider"(), !dbg !360
  %".352" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 0 , !dbg !360
  %".353" = load i32, i32* %".352", !dbg !360
  %".354" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 1 , !dbg !360
  %".355" = load i32, i32* %".354", !dbg !360
  %".356" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 2 , !dbg !360
  %".357" = load i32, i32* %".356", !dbg !360
  %".358" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 3 , !dbg !360
  %".359" = load i32, i32* %".358", !dbg !360
  %".360" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 4 , !dbg !360
  %".361" = load i32, i32* %".360", !dbg !360
  %".362" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 6 , !dbg !360
  %".363" = load i64, i64* %".362", !dbg !360
  %".364" = call i32 @"print_suite_summary"(i32 %".353", i32 %".355", i32 %".357", i32 %".359", i32 %".361", i64 %".363"), !dbg !360
  br label %"if.end.26", !dbg !360
if.end.26:
  %".366" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 0 , !dbg !360
  %".367" = load i32, i32* %".366", !dbg !360
  %".368" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 1 , !dbg !360
  %".369" = load i32, i32* %".368", !dbg !360
  %".370" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 2 , !dbg !360
  %".371" = load i32, i32* %".370", !dbg !360
  %".372" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 3 , !dbg !360
  %".373" = load i32, i32* %".372", !dbg !360
  %".374" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 4 , !dbg !360
  %".375" = load i32, i32* %".374", !dbg !360
  %".376" = load i32, i32* %"skipped_by_filter.addr", !dbg !360
  %".377" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"summary.addr", i32 0, i32 6 , !dbg !360
  %".378" = load i64, i64* %".377", !dbg !360
  %".379" = call i32 @"print_grand_summary"(i32 %".367", i32 %".369", i32 %".371", i32 %".373", i32 %".375", i32 %".376", i64 %".378"), !dbg !360
  br label %"if.end.25", !dbg !360
}

define i32 @"parse_args"(i32 %"argc.arg", i8** %"argv.arg") !dbg !35
{
entry:
  %"argc" = alloca i32
  %"parser.addr" = alloca %"struct.ritz_module_1.ArgParser", !dbg !366
  store i32 %"argc.arg", i32* %"argc"
  call void @"llvm.dbg.declare"(metadata i32* %"argc", metadata !362, metadata !7), !dbg !363
  %"argv" = alloca i8**
  store i8** %"argv.arg", i8*** %"argv"
  call void @"llvm.dbg.declare"(metadata i8*** %"argv", metadata !365, metadata !7), !dbg !363
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"* %"parser.addr", metadata !368, metadata !7), !dbg !369
  %".9" = getelementptr [9 x i8], [9 x i8]* @".str.27", i64 0, i64 0 , !dbg !370
  %".10" = getelementptr [29 x i8], [29 x i8]* @".str.28", i64 0, i64 0 , !dbg !370
  %".11" = call i32 @"args_init"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8* %".9", i8* %".10"), !dbg !370
  %".12" = getelementptr [8 x i8], [8 x i8]* @".str.29", i64 0, i64 0 , !dbg !371
  %".13" = getelementptr [21 x i8], [21 x i8]* @".str.30", i64 0, i64 0 , !dbg !371
  %".14" = call i32 @"args_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 118, i8* %".12", i8* %".13"), !dbg !371
  %".15" = getelementptr [6 x i8], [6 x i8]* @".str.31", i64 0, i64 0 , !dbg !372
  %".16" = getelementptr [43 x i8], [43 x i8]* @".str.32", i64 0, i64 0 , !dbg !372
  %".17" = call i32 @"args_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 113, i8* %".15", i8* %".16"), !dbg !372
  %".18" = getelementptr [5 x i8], [5 x i8]* @".str.33", i64 0, i64 0 , !dbg !373
  %".19" = getelementptr [32 x i8], [32 x i8]* @".str.34", i64 0, i64 0 , !dbg !373
  %".20" = call i32 @"args_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 108, i8* %".18", i8* %".19"), !dbg !373
  %".21" = getelementptr [5 x i8], [5 x i8]* @".str.35", i64 0, i64 0 , !dbg !374
  %".22" = getelementptr [23 x i8], [23 x i8]* @".str.36", i64 0, i64 0 , !dbg !374
  %".23" = call i32 @"args_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 104, i8* %".21", i8* %".22"), !dbg !374
  %".24" = getelementptr [7 x i8], [7 x i8]* @".str.37", i64 0, i64 0 , !dbg !375
  %".25" = getelementptr [5 x i8], [5 x i8]* @".str.38", i64 0, i64 0 , !dbg !375
  %".26" = getelementptr [41 x i8], [41 x i8]* @".str.39", i64 0, i64 0 , !dbg !375
  %".27" = call i32 @"args_option"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 102, i8* %".24", i8* %".25", i8* %".26", i8* null), !dbg !375
  %".28" = getelementptr [8 x i8], [8 x i8]* @".str.40", i64 0, i64 0 , !dbg !376
  %".29" = getelementptr [3 x i8], [3 x i8]* @".str.41", i64 0, i64 0 , !dbg !376
  %".30" = getelementptr [33 x i8], [33 x i8]* @".str.42", i64 0, i64 0 , !dbg !376
  %".31" = getelementptr [5 x i8], [5 x i8]* @".str.43", i64 0, i64 0 , !dbg !376
  %".32" = call i32 @"args_option"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 116, i8* %".28", i8* %".29", i8* %".30", i8* %".31"), !dbg !376
  %".33" = trunc i64 0 to i8 , !dbg !377
  %".34" = getelementptr [8 x i8], [8 x i8]* @".str.44", i64 0, i64 0 , !dbg !377
  %".35" = getelementptr [51 x i8], [51 x i8]* @".str.45", i64 0, i64 0 , !dbg !377
  %".36" = call i32 @"args_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 %".33", i8* %".34", i8* %".35"), !dbg !377
  %".37" = getelementptr [10 x i8], [10 x i8]* @".str.46", i64 0, i64 0 , !dbg !378
  %".38" = getelementptr [27 x i8], [27 x i8]* @".str.47", i64 0, i64 0 , !dbg !378
  %".39" = call i32 @"args_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 120, i8* %".37", i8* %".38"), !dbg !378
  %".40" = getelementptr [8 x i8], [8 x i8]* @".str.48", i64 0, i64 0 , !dbg !379
  %".41" = getelementptr [31 x i8], [31 x i8]* @".str.49", i64 0, i64 0 , !dbg !379
  %".42" = call i32 @"args_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 115, i8* %".40", i8* %".41"), !dbg !379
  %".43" = trunc i64 0 to i8 , !dbg !380
  %".44" = getelementptr [5 x i8], [5 x i8]* @".str.50", i64 0, i64 0 , !dbg !380
  %".45" = getelementptr [2 x i8], [2 x i8]* @".str.51", i64 0, i64 0 , !dbg !380
  %".46" = getelementptr [37 x i8], [37 x i8]* @".str.52", i64 0, i64 0 , !dbg !380
  %".47" = getelementptr [2 x i8], [2 x i8]* @".str.53", i64 0, i64 0 , !dbg !380
  %".48" = call i32 @"args_option"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 %".43", i8* %".44", i8* %".45", i8* %".46", i8* %".47"), !dbg !380
  %".49" = getelementptr [5 x i8], [5 x i8]* @".str.54", i64 0, i64 0 , !dbg !381
  %".50" = getelementptr [30 x i8], [30 x i8]* @".str.55", i64 0, i64 0 , !dbg !381
  %".51" = call i32 @"args_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 106, i8* %".49", i8* %".50"), !dbg !381
  %".52" = trunc i64 0 to i8 , !dbg !382
  %".53" = getelementptr [6 x i8], [6 x i8]* @".str.56", i64 0, i64 0 , !dbg !382
  %".54" = getelementptr [35 x i8], [35 x i8]* @".str.57", i64 0, i64 0 , !dbg !382
  %".55" = call i32 @"args_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 %".52", i8* %".53", i8* %".54"), !dbg !382
  %".56" = trunc i64 0 to i8 , !dbg !383
  %".57" = getelementptr [6 x i8], [6 x i8]* @".str.58", i64 0, i64 0 , !dbg !383
  %".58" = getelementptr [43 x i8], [43 x i8]* @".str.59", i64 0, i64 0 , !dbg !383
  %".59" = call i32 @"args_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 %".56", i8* %".57", i8* %".58"), !dbg !383
  %".60" = trunc i64 0 to i8 , !dbg !384
  %".61" = getelementptr [9 x i8], [9 x i8]* @".str.60", i64 0, i64 0 , !dbg !384
  %".62" = getelementptr [23 x i8], [23 x i8]* @".str.61", i64 0, i64 0 , !dbg !384
  %".63" = call i32 @"args_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 %".60", i8* %".61", i8* %".62"), !dbg !384
  %".64" = load i32, i32* %"argc", !dbg !385
  %".65" = load i8**, i8*** %"argv", !dbg !385
  %".66" = call i32 @"args_parse"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i32 %".64", i8** %".65"), !dbg !385
  %".67" = sext i32 %".66" to i64 , !dbg !385
  %".68" = icmp ne i64 %".67", 0 , !dbg !385
  br i1 %".68", label %"if.then", label %"if.end", !dbg !385
if.then:
  %".70" = sub i64 0, 1, !dbg !386
  %".71" = trunc i64 %".70" to i32 , !dbg !386
  ret i32 %".71", !dbg !386
if.end:
  %".73" = call i32 @"args_get_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 104), !dbg !387
  %".74" = sext i32 %".73" to i64 , !dbg !387
  %".75" = icmp ne i64 %".74", 0 , !dbg !387
  br i1 %".75", label %"if.then.1", label %"if.end.1", !dbg !387
if.then.1:
  %".77" = call i32 @"args_print_help"(%"struct.ritz_module_1.ArgParser"* %"parser.addr"), !dbg !388
  %".78" = trunc i64 1 to i32 , !dbg !389
  ret i32 %".78", !dbg !389
if.end.1:
  %".80" = call i32 @"args_get_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 118), !dbg !390
  store i32 %".80", i32* @"g_verbose", !dbg !390
  %".82" = call i32 @"args_get_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 113), !dbg !391
  store i32 %".82", i32* @"g_quiet", !dbg !391
  %".84" = call i32 @"args_get_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 108), !dbg !392
  store i32 %".84", i32* @"g_list_only", !dbg !392
  %".86" = call i8* @"args_get_str"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 102), !dbg !393
  store i8* %".86", i8** @"g_filter", !dbg !393
  %".88" = call i64 @"args_get_int"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 116), !dbg !394
  store i64 %".88", i64* @"g_timeout_ms", !dbg !394
  %".90" = getelementptr [8 x i8], [8 x i8]* @".str.62", i64 0, i64 0 , !dbg !395
  %".91" = call i32 @"args_get_flag_long"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8* %".90"), !dbg !395
  store i32 %".91", i32* @"g_no_fork", !dbg !395
  %".93" = call i32 @"args_get_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 120), !dbg !396
  store i32 %".93", i32* @"g_fail_fast", !dbg !396
  %".95" = call i32 @"args_get_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 115), !dbg !397
  store i32 %".95", i32* @"g_shuffle", !dbg !397
  %".97" = getelementptr [5 x i8], [5 x i8]* @".str.63", i64 0, i64 0 , !dbg !398
  %".98" = call i64 @"args_get_int_long"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8* %".97"), !dbg !398
  store i64 %".98", i64* @"g_seed", !dbg !398
  %".100" = call i32 @"args_get_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8 106), !dbg !399
  store i32 %".100", i32* @"g_json", !dbg !399
  %".102" = getelementptr [6 x i8], [6 x i8]* @".str.64", i64 0, i64 0 , !dbg !400
  %".103" = call i32 @"args_get_flag_long"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8* %".102"), !dbg !400
  store i32 %".103", i32* @"g_junit", !dbg !400
  %".105" = getelementptr [6 x i8], [6 x i8]* @".str.65", i64 0, i64 0 , !dbg !401
  %".106" = call i32 @"args_get_flag_long"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8* %".105"), !dbg !401
  %".107" = getelementptr [9 x i8], [9 x i8]* @".str.66", i64 0, i64 0 , !dbg !402
  %".108" = call i32 @"args_get_flag_long"(%"struct.ritz_module_1.ArgParser"* %"parser.addr", i8* %".107"), !dbg !402
  %".109" = sext i32 %".106" to i64 , !dbg !403
  %".110" = icmp ne i64 %".109", 0 , !dbg !403
  br i1 %".110", label %"and.right", label %"and.merge", !dbg !403
and.right:
  %".112" = sext i32 %".108" to i64 , !dbg !403
  %".113" = icmp ne i64 %".112", 0 , !dbg !403
  br label %"and.merge", !dbg !403
and.merge:
  %".115" = phi  i1 [0, %"if.end.1"], [%".113", %"and.right"] , !dbg !403
  br i1 %".115", label %"if.then.2", label %"if.end.2", !dbg !403
if.then.2:
  %".117" = getelementptr [57 x i8], [57 x i8]* @".str.67", i64 0, i64 0 , !dbg !404
  %".118" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".117", 0 , !dbg !404
  %".119" = insertvalue %"struct.ritz_module_1.StrView" %".118", i64 56, 1 , !dbg !404
  %".120" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".119"), !dbg !404
  %".121" = sub i64 0, 1, !dbg !405
  %".122" = trunc i64 %".121" to i32 , !dbg !405
  ret i32 %".122", !dbg !405
if.end.2:
  %".124" = sext i32 %".106" to i64 , !dbg !406
  %".125" = icmp ne i64 %".124", 0 , !dbg !406
  br i1 %".125", label %"if.then.3", label %"if.else", !dbg !406
if.then.3:
  %".127" = trunc i64 1 to i32 , !dbg !407
  store i32 %".127", i32* @"g_color", !dbg !407
  %".129" = trunc i64 1 to i32 , !dbg !407
  %".130" = call i32 @"set_color_mode"(i32 %".129"), !dbg !407
  br label %"if.end.3", !dbg !408
if.else:
  %".131" = sext i32 %".108" to i64 , !dbg !407
  %".132" = icmp ne i64 %".131", 0 , !dbg !407
  br i1 %".132", label %"if.then.4", label %"if.end.4", !dbg !407
if.end.3:
  %".143" = load i32, i32* @"g_verbose", !dbg !409
  %".144" = sext i32 %".143" to i64 , !dbg !409
  %".145" = icmp ne i64 %".144", 0 , !dbg !409
  br i1 %".145", label %"and.right.1", label %"and.merge.1", !dbg !409
if.then.4:
  %".134" = sub i64 0, 1, !dbg !408
  %".135" = trunc i64 %".134" to i32 , !dbg !408
  store i32 %".135", i32* @"g_color", !dbg !408
  %".137" = sub i64 0, 1, !dbg !408
  %".138" = trunc i64 %".137" to i32 , !dbg !408
  %".139" = call i32 @"set_color_mode"(i32 %".138"), !dbg !408
  br label %"if.end.4", !dbg !408
if.end.4:
  br label %"if.end.3", !dbg !408
and.right.1:
  %".147" = load i32, i32* @"g_quiet", !dbg !409
  %".148" = sext i32 %".147" to i64 , !dbg !409
  %".149" = icmp ne i64 %".148", 0 , !dbg !409
  br label %"and.merge.1", !dbg !409
and.merge.1:
  %".151" = phi  i1 [0, %"if.end.3"], [%".149", %"and.right.1"] , !dbg !409
  br i1 %".151", label %"if.then.5", label %"if.end.5", !dbg !409
if.then.5:
  %".153" = getelementptr [56 x i8], [56 x i8]* @".str.68", i64 0, i64 0 , !dbg !410
  %".154" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".153", 0 , !dbg !410
  %".155" = insertvalue %"struct.ritz_module_1.StrView" %".154", i64 55, 1 , !dbg !410
  %".156" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".155"), !dbg !410
  %".157" = sub i64 0, 1, !dbg !411
  %".158" = trunc i64 %".157" to i32 , !dbg !411
  ret i32 %".158", !dbg !411
if.end.5:
  %".160" = load i32, i32* @"g_json", !dbg !412
  %".161" = sext i32 %".160" to i64 , !dbg !412
  %".162" = icmp ne i64 %".161", 0 , !dbg !412
  br i1 %".162", label %"and.right.2", label %"and.merge.2", !dbg !412
and.right.2:
  %".164" = load i32, i32* @"g_junit", !dbg !412
  %".165" = sext i32 %".164" to i64 , !dbg !412
  %".166" = icmp ne i64 %".165", 0 , !dbg !412
  br label %"and.merge.2", !dbg !412
and.merge.2:
  %".168" = phi  i1 [0, %"if.end.5"], [%".166", %"and.right.2"] , !dbg !412
  br i1 %".168", label %"if.then.6", label %"if.end.6", !dbg !412
if.then.6:
  %".170" = getelementptr [53 x i8], [53 x i8]* @".str.69", i64 0, i64 0 , !dbg !413
  %".171" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".170", 0 , !dbg !413
  %".172" = insertvalue %"struct.ritz_module_1.StrView" %".171", i64 52, 1 , !dbg !413
  %".173" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".172"), !dbg !413
  %".174" = sub i64 0, 1, !dbg !414
  %".175" = trunc i64 %".174" to i32 , !dbg !414
  ret i32 %".175", !dbg !414
if.end.6:
  %".177" = load i32, i32* @"g_json", !dbg !415
  %".178" = sext i32 %".177" to i64 , !dbg !415
  %".179" = icmp ne i64 %".178", 0 , !dbg !415
  br i1 %".179", label %"or.merge", label %"or.right", !dbg !415
or.right:
  %".181" = load i32, i32* @"g_junit", !dbg !415
  %".182" = sext i32 %".181" to i64 , !dbg !415
  %".183" = icmp ne i64 %".182", 0 , !dbg !415
  br label %"or.merge", !dbg !415
or.merge:
  %".185" = phi  i1 [1, %"if.end.6"], [%".183", %"or.right"] , !dbg !415
  br i1 %".185", label %"if.then.7", label %"if.end.7", !dbg !415
if.then.7:
  %".187" = trunc i64 1 to i32 , !dbg !416
  store i32 %".187", i32* @"g_quiet", !dbg !416
  %".189" = sub i64 0, 1, !dbg !416
  %".190" = trunc i64 %".189" to i32 , !dbg !416
  %".191" = call i32 @"set_color_mode"(i32 %".190"), !dbg !416
  br label %"if.end.7", !dbg !416
if.end.7:
  %".193" = trunc i64 0 to i32 , !dbg !417
  ret i32 %".193", !dbg !417
}

define i32 @"matches_filter"(i8* %"name.arg") !dbg !36
{
entry:
  %"name" = alloca i8*
  store i8* %"name.arg", i8** %"name"
  call void @"llvm.dbg.declare"(metadata i8** %"name", metadata !418, metadata !7), !dbg !419
  %".5" = load i8*, i8** @"g_filter", !dbg !420
  %".6" = load i8*, i8** %"name", !dbg !420
  %".7" = call i32 @"filter_match"(i8* %".5", i8* %".6"), !dbg !420
  ret i32 %".7", !dbg !420
}

define i32 @"main"(i32 %"argc.arg", i8** %"argv.arg") !dbg !37
{
entry:
  %"argc" = alloca i32
  store i32 %"argc.arg", i32* %"argc"
  call void @"llvm.dbg.declare"(metadata i32* %"argc", metadata !421, metadata !7), !dbg !422
  %"argv" = alloca i8**
  store i8** %"argv.arg", i8*** %"argv"
  call void @"llvm.dbg.declare"(metadata i8*** %"argv", metadata !423, metadata !7), !dbg !422
  %".8" = load i32, i32* %"argc", !dbg !424
  %".9" = load i8**, i8*** %"argv", !dbg !424
  %".10" = call i32 @"parse_args"(i32 %".8", i8** %".9"), !dbg !424
  %".11" = sext i32 %".10" to i64 , !dbg !425
  %".12" = icmp ne i64 %".11", 0 , !dbg !425
  br i1 %".12", label %"if.then", label %"if.end", !dbg !425
if.then:
  %".14" = sext i32 %".10" to i64 , !dbg !426
  %".15" = icmp sgt i64 %".14", 0 , !dbg !426
  br i1 %".15", label %"if.then.1", label %"if.end.1", !dbg !426
if.end:
  %".21" = call i32 @"run_tests"(), !dbg !429
  ret i32 %".21", !dbg !429
if.then.1:
  %".17" = trunc i64 0 to i32 , !dbg !427
  ret i32 %".17", !dbg !427
if.end.1:
  %".19" = trunc i64 1 to i32 , !dbg !428
  ret i32 %".19", !dbg !428
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !38
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !432, metadata !7), !dbg !433
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !434
  %".5" = load i64, i64* %".4", !dbg !434
  %".6" = sub i64 %".5", 1, !dbg !434
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !434
  store i64 %".6", i64* %".7", !dbg !434
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !435
  %".10" = load i8*, i8** %".9", !dbg !435
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !435
  %".12" = load i64, i64* %".11", !dbg !435
  %".13" = getelementptr i8, i8* %".10", i64 %".12" , !dbg !435
  %".14" = load i8, i8* %".13", !dbg !435
  ret i8 %".14", !dbg !435
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !39
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !436
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !437, metadata !7), !dbg !438
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !439
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !439
  store i8* null, i8** %".4", !dbg !439
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !440
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !440
  store i64 0, i64* %".7", !dbg !440
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !441
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !441
  store i64 0, i64* %".10", !dbg !441
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !442
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !442
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !40
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !443, metadata !7), !dbg !444
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !445
  %".5" = load i8*, i8** %".4", !dbg !445
  %".6" = icmp ne i8* %".5", null , !dbg !445
  br i1 %".6", label %"if.then", label %"if.end", !dbg !445
if.then:
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !445
  %".9" = load i8*, i8** %".8", !dbg !445
  %".10" = call i32 @"free"(i8* %".9"), !dbg !445
  br label %"if.end", !dbg !445
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !446
  store i8* null, i8** %".12", !dbg !446
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !447
  store i64 0, i64* %".14", !dbg !447
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !448
  store i64 0, i64* %".16", !dbg !448
  ret i32 0, !dbg !448
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !41
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !449, metadata !7), !dbg !450
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !451
  store i64 0, i64* %".4", !dbg !451
  ret i32 0, !dbg !451
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !42
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !457
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !452, metadata !7), !dbg !453
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !454, metadata !7), !dbg !453
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !455
  %".8" = load i64, i64* %".7", !dbg !455
  %".9" = load i64, i64* %"needed", !dbg !455
  %".10" = icmp sge i64 %".8", %".9" , !dbg !455
  br i1 %".10", label %"if.then", label %"if.end", !dbg !455
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !456
  ret i32 %".12", !dbg !456
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !457
  %".15" = load i64, i64* %".14", !dbg !457
  store i64 %".15", i64* %"new_cap.addr", !dbg !457
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !458, metadata !7), !dbg !459
  %".18" = load i64, i64* %"new_cap.addr", !dbg !460
  %".19" = icmp eq i64 %".18", 0 , !dbg !460
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !460
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !461
  br label %"if.end.1", !dbg !461
if.end.1:
  br label %"while.cond", !dbg !462
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !462
  %".25" = load i64, i64* %"needed", !dbg !462
  %".26" = icmp slt i64 %".24", %".25" , !dbg !462
  br i1 %".26", label %"while.body", label %"while.end", !dbg !462
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !463
  %".29" = mul i64 %".28", 2, !dbg !463
  store i64 %".29", i64* %"new_cap.addr", !dbg !463
  br label %"while.cond", !dbg !463
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !464
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !464
  ret i32 %".33", !dbg !464
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !43
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !465, metadata !7), !dbg !466
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !467, metadata !7), !dbg !466
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !468
  %".8" = load i8*, i8** %".7", !dbg !468
  %".9" = load i64, i64* %"idx", !dbg !468
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !468
  %".11" = load i8, i8* %".10", !dbg !468
  ret i8 %".11", !dbg !468
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !44
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !469, metadata !7), !dbg !470
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !471, metadata !7), !dbg !470
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !472, metadata !7), !dbg !470
  %".10" = load i8, i8* %"item", !dbg !473
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !473
  %".12" = load i8*, i8** %".11", !dbg !473
  %".13" = load i64, i64* %"idx", !dbg !473
  %".14" = getelementptr i8, i8* %".12", i64 %".13" , !dbg !473
  store i8 %".10", i8* %".14", !dbg !473
  %".16" = trunc i64 0 to i32 , !dbg !474
  ret i32 %".16", !dbg !474
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !45
{
entry:
  %"i" = alloca i64, !dbg !479
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !475, metadata !7), !dbg !476
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !477, metadata !7), !dbg !476
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !478, metadata !7), !dbg !476
  %".10" = load i64, i64* %"len", !dbg !479
  store i64 0, i64* %"i", !dbg !479
  br label %"for.cond", !dbg !479
for.cond:
  %".13" = load i64, i64* %"i", !dbg !479
  %".14" = icmp slt i64 %".13", %".10" , !dbg !479
  br i1 %".14", label %"for.body", label %"for.end", !dbg !479
for.body:
  %".16" = load i8*, i8** %"data", !dbg !479
  %".17" = load i64, i64* %"i", !dbg !479
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !479
  %".19" = load i8, i8* %".18", !dbg !479
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !479
  %".21" = sext i32 %".20" to i64 , !dbg !479
  %".22" = icmp ne i64 %".21", 0 , !dbg !479
  br i1 %".22", label %"if.then", label %"if.end", !dbg !479
for.incr:
  %".28" = load i64, i64* %"i", !dbg !480
  %".29" = add i64 %".28", 1, !dbg !480
  store i64 %".29", i64* %"i", !dbg !480
  br label %"for.cond", !dbg !480
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !481
  ret i32 %".32", !dbg !481
if.then:
  %".24" = sub i64 0, 1, !dbg !480
  %".25" = trunc i64 %".24" to i32 , !dbg !480
  ret i32 %".25", !dbg !480
if.end:
  br label %"for.incr", !dbg !480
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !46
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !484, metadata !7), !dbg !485
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !487, metadata !7), !dbg !485
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !488
  %".8" = load i64, i64* %".7", !dbg !488
  %".9" = add i64 %".8", 1, !dbg !488
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !488
  %".11" = sext i32 %".10" to i64 , !dbg !488
  %".12" = icmp ne i64 %".11", 0 , !dbg !488
  br i1 %".12", label %"if.then", label %"if.end", !dbg !488
if.then:
  %".14" = sub i64 0, 1, !dbg !489
  %".15" = trunc i64 %".14" to i32 , !dbg !489
  ret i32 %".15", !dbg !489
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !490
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !490
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !490
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !490
  %".21" = load i64, i64* %".20", !dbg !490
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !490
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !490
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !491
  %".25" = load i64, i64* %".24", !dbg !491
  %".26" = add i64 %".25", 1, !dbg !491
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !491
  store i64 %".26", i64* %".27", !dbg !491
  %".29" = trunc i64 0 to i32 , !dbg !492
  ret i32 %".29", !dbg !492
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !47
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !493, metadata !7), !dbg !494
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !495, metadata !7), !dbg !494
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !496
  %".8" = load i64, i64* %".7", !dbg !496
  %".9" = add i64 %".8", 1, !dbg !496
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !496
  %".11" = sext i32 %".10" to i64 , !dbg !496
  %".12" = icmp ne i64 %".11", 0 , !dbg !496
  br i1 %".12", label %"if.then", label %"if.end", !dbg !496
if.then:
  %".14" = sub i64 0, 1, !dbg !497
  %".15" = trunc i64 %".14" to i32 , !dbg !497
  ret i32 %".15", !dbg !497
if.end:
  %".17" = load i8, i8* %"item", !dbg !498
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !498
  %".19" = load i8*, i8** %".18", !dbg !498
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !498
  %".21" = load i64, i64* %".20", !dbg !498
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !498
  store i8 %".17", i8* %".22", !dbg !498
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !499
  %".25" = load i64, i64* %".24", !dbg !499
  %".26" = add i64 %".25", 1, !dbg !499
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !499
  store i64 %".26", i64* %".27", !dbg !499
  %".29" = trunc i64 0 to i32 , !dbg !500
  ret i32 %".29", !dbg !500
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !48
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !503
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !501, metadata !7), !dbg !502
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !504, metadata !7), !dbg !505
  %".6" = load i64, i64* %"cap", !dbg !506
  %".7" = icmp sle i64 %".6", 0 , !dbg !506
  br i1 %".7", label %"if.then", label %"if.end", !dbg !506
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !507
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !507
  store i8* null, i8** %".10", !dbg !507
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !508
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !508
  store i64 0, i64* %".13", !dbg !508
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !509
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !509
  store i64 0, i64* %".16", !dbg !509
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !510
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !510
if.end:
  %".20" = load i64, i64* %"cap", !dbg !511
  %".21" = mul i64 %".20", 1, !dbg !511
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !512
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !512
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !512
  store i8* %".22", i8** %".24", !dbg !512
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !513
  %".27" = load i8*, i8** %".26", !dbg !513
  %".28" = icmp eq i8* %".27", null , !dbg !513
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !513
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !514
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !514
  store i64 0, i64* %".31", !dbg !514
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !515
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !515
  store i64 0, i64* %".34", !dbg !515
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !516
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !516
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !517
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !517
  store i64 0, i64* %".39", !dbg !517
  %".41" = load i64, i64* %"cap", !dbg !518
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !518
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !518
  store i64 %".41", i64* %".43", !dbg !518
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !519
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !519
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !49
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !520, metadata !7), !dbg !521
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !522, metadata !7), !dbg !521
  %".7" = load i64, i64* %"new_cap", !dbg !523
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !523
  %".9" = load i64, i64* %".8", !dbg !523
  %".10" = icmp sle i64 %".7", %".9" , !dbg !523
  br i1 %".10", label %"if.then", label %"if.end", !dbg !523
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !524
  ret i32 %".12", !dbg !524
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !525
  %".15" = mul i64 %".14", 1, !dbg !525
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !526
  %".17" = load i8*, i8** %".16", !dbg !526
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !526
  %".19" = icmp eq i8* %".18", null , !dbg !527
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !527
if.then.1:
  %".21" = sub i64 0, 1, !dbg !528
  %".22" = trunc i64 %".21" to i32 , !dbg !528
  ret i32 %".22", !dbg !528
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !529
  store i8* %".18", i8** %".24", !dbg !529
  %".26" = load i64, i64* %"new_cap", !dbg !530
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !530
  store i64 %".26", i64* %".27", !dbg !530
  %".29" = trunc i64 0 to i32 , !dbg !531
  ret i32 %".29", !dbg !531
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !50
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !537
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !532, metadata !7), !dbg !533
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !534, metadata !7), !dbg !533
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !535
  %".8" = load i64, i64* %".7", !dbg !535
  %".9" = load i64, i64* %"needed", !dbg !535
  %".10" = icmp sge i64 %".8", %".9" , !dbg !535
  br i1 %".10", label %"if.then", label %"if.end", !dbg !535
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !536
  ret i32 %".12", !dbg !536
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !537
  %".15" = load i64, i64* %".14", !dbg !537
  store i64 %".15", i64* %"new_cap.addr", !dbg !537
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !538, metadata !7), !dbg !539
  %".18" = load i64, i64* %"new_cap.addr", !dbg !540
  %".19" = icmp eq i64 %".18", 0 , !dbg !540
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !540
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !541
  br label %"if.end.1", !dbg !541
if.end.1:
  br label %"while.cond", !dbg !542
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !542
  %".25" = load i64, i64* %"needed", !dbg !542
  %".26" = icmp slt i64 %".24", %".25" , !dbg !542
  br i1 %".26", label %"while.body", label %"while.end", !dbg !542
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !543
  %".29" = mul i64 %".28", 2, !dbg !543
  store i64 %".29", i64* %"new_cap.addr", !dbg !543
  br label %"while.cond", !dbg !543
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !544
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !544
  ret i32 %".33", !dbg !544
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !51
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !545, metadata !7), !dbg !546
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !547, metadata !7), !dbg !546
  %".7" = load i64, i64* %"new_cap", !dbg !548
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !548
  %".9" = load i64, i64* %".8", !dbg !548
  %".10" = icmp sle i64 %".7", %".9" , !dbg !548
  br i1 %".10", label %"if.then", label %"if.end", !dbg !548
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !549
  ret i32 %".12", !dbg !549
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !550
  %".15" = mul i64 %".14", 16, !dbg !550
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !551
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !551
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !551
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !551
  %".20" = icmp eq i8* %".19", null , !dbg !552
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !552
if.then.1:
  %".22" = sub i64 0, 1, !dbg !553
  %".23" = trunc i64 %".22" to i32 , !dbg !553
  ret i32 %".23", !dbg !553
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !554
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !554
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !554
  %".28" = load i64, i64* %"new_cap", !dbg !555
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !555
  store i64 %".28", i64* %".29", !dbg !555
  %".31" = trunc i64 0 to i32 , !dbg !556
  ret i32 %".31", !dbg !556
}

@".str.0" = private constant [16 x i8] c"/proc/self/maps\00"
@".str.1" = private constant [15 x i8] c"/proc/self/exe\00"
@".str.2" = private constant [41 x i8] c"ritzunit: failed to open /proc/self/exe\0a\00"
@".str.3" = private constant [37 x i8] c"ritzunit: failed to get binary size\0a\00"
@".str.4" = private constant [37 x i8] c"ritzunit: failed to allocate memory\0a\00"
@".str.5" = private constant [33 x i8] c"ritzunit: failed to read binary\0a\00"
@".str.6" = private constant [36 x i8] c"ritzunit: not a valid ELF64 binary\0a\00"
@".str.7" = private constant [40 x i8] c"ritzunit: failed to parse ELF sections\0a\00"
@".str.8" = private constant [8 x i8] c"SIGSEGV\00"
@".str.9" = private constant [8 x i8] c"SIGABRT\00"
@".str.10" = private constant [7 x i8] c"SIGFPE\00"
@".str.11" = private constant [7 x i8] c"SIGILL\00"
@".str.12" = private constant [7 x i8] c"SIGBUS\00"
@".str.13" = private constant [8 x i8] c"SIGKILL\00"
@".str.14" = private constant [8 x i8] c"SIGTERM\00"
@".str.15" = private constant [7 x i8] c"SIGINT\00"
@".str.16" = private constant [8 x i8] c"SIGTRAP\00"
@".str.17" = private constant [8 x i8] c"SIGPIPE\00"
@".str.18" = private constant [7 x i8] c"signal\00"
@".str.19" = private constant [17 x i8] c"No tests found.\0a\00"
@".str.20" = private constant [27 x i8] c"Shuffled tests with seed: \00"
@".str.21" = private constant [2 x i8] c"\0a\00"
@".str.22" = private constant [12 x i8] c"Discovered \00"
@".str.23" = private constant [11 x i8] c" test(s):\0a\00"
@".str.24" = private constant [3 x i8] c"  \00"
@".str.25" = private constant [2 x i8] c"\0a\00"
@".str.26" = private constant [6 x i8] c"tests\00"
@".str.27" = private constant [9 x i8] c"ritzunit\00"
@".str.28" = private constant [29 x i8] c"Unit test framework for Ritz\00"
@".str.29" = private constant [8 x i8] c"verbose\00"
@".str.30" = private constant [21 x i8] c"Show detailed output\00"
@".str.31" = private constant [6 x i8] c"quiet\00"
@".str.32" = private constant [43 x i8] c"Minimal output - only failures and summary\00"
@".str.33" = private constant [5 x i8] c"list\00"
@".str.34" = private constant [32 x i8] c"List tests without running them\00"
@".str.35" = private constant [5 x i8] c"help\00"
@".str.36" = private constant [23 x i8] c"Show this help message\00"
@".str.37" = private constant [7 x i8] c"filter\00"
@".str.38" = private constant [5 x i8] c"EXPR\00"
@".str.39" = private constant [41 x i8] c"Filter tests by EXPR (glob, @attr, bool)\00"
@".str.40" = private constant [8 x i8] c"timeout\00"
@".str.41" = private constant [3 x i8] c"MS\00"
@".str.42" = private constant [33 x i8] c"Timeout per test in milliseconds\00"
@".str.43" = private constant [5 x i8] c"5000\00"
@".str.44" = private constant [8 x i8] c"no-fork\00"
@".str.45" = private constant [51 x i8] c"Disable fork isolation (run tests in main process)\00"
@".str.46" = private constant [10 x i8] c"fail-fast\00"
@".str.47" = private constant [27 x i8] c"Stop on first test failure\00"
@".str.48" = private constant [8 x i8] c"shuffle\00"
@".str.49" = private constant [31 x i8] c"Randomize test execution order\00"
@".str.50" = private constant [5 x i8] c"seed\00"
@".str.51" = private constant [2 x i8] c"N\00"
@".str.52" = private constant [37 x i8] c"Random seed for shuffling (0 = auto)\00"
@".str.53" = private constant [2 x i8] c"0\00"
@".str.54" = private constant [5 x i8] c"json\00"
@".str.55" = private constant [30 x i8] c"Output results in JSON format\00"
@".str.56" = private constant [6 x i8] c"junit\00"
@".str.57" = private constant [35 x i8] c"Output results in JUnit XML format\00"
@".str.58" = private constant [6 x i8] c"color\00"
@".str.59" = private constant [43 x i8] c"Force colored output (even when not a TTY)\00"
@".str.60" = private constant [9 x i8] c"no-color\00"
@".str.61" = private constant [23 x i8] c"Disable colored output\00"
@".str.62" = private constant [8 x i8] c"no-fork\00"
@".str.63" = private constant [5 x i8] c"seed\00"
@".str.64" = private constant [6 x i8] c"junit\00"
@".str.65" = private constant [6 x i8] c"color\00"
@".str.66" = private constant [9 x i8] c"no-color\00"
@".str.67" = private constant [57 x i8] c"ritzunit: --color and --no-color are mutually exclusive\0a\00"
@".str.68" = private constant [56 x i8] c"ritzunit: --verbose and --quiet are mutually exclusive\0a\00"
@".str.69" = private constant [53 x i8] c"ritzunit: --json and --junit are mutually exclusive\0a\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/ritzunit/src", filename: "runner.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 48, name: "WIFEXITED", scopeLine: 48, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 51, name: "WEXITSTATUS", scopeLine: 51, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 54, name: "WIFSIGNALED", scopeLine: 54, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 58, name: "WTERMSIG", scopeLine: 58, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 103, name: "detect_base_address", scopeLine: 103, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 135, name: "get_time_ms", scopeLine: 135, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 141, name: "get_time_us", scopeLine: 141, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 153, name: "rng_seed", scopeLine: 153, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 158, name: "rng_next", scopeLine: 158, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 164, name: "shuffle_tests", scopeLine: 164, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 195, name: "run_test_direct", scopeLine: 195, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 203, name: "run_test_forked", scopeLine: 203, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 278, name: "run_test", scopeLine: 278, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 290, name: "run_test_with_result", scopeLine: 290, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 307, name: "is_test_name", scopeLine: 307, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 322, name: "discover_tests", scopeLine: 322, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 412, name: "signal_name", scopeLine: 412, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 440, name: "run_tests", scopeLine: 440, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 577, name: "parse_args", scopeLine: 577, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 653, name: "matches_filter", scopeLine: 653, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 662, name: "main", scopeLine: 662, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!51 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!52 = !DILocalVariable(file: !0, line: 48, name: "status", scope: !17, type: !10)
!53 = !DILocation(column: 1, line: 48, scope: !17)
!54 = !DILocation(column: 5, line: 49, scope: !17)
!55 = !DILocalVariable(file: !0, line: 51, name: "status", scope: !18, type: !10)
!56 = !DILocation(column: 1, line: 51, scope: !18)
!57 = !DILocation(column: 5, line: 52, scope: !18)
!58 = !DILocalVariable(file: !0, line: 54, name: "status", scope: !19, type: !10)
!59 = !DILocation(column: 1, line: 54, scope: !19)
!60 = !DILocation(column: 5, line: 55, scope: !19)
!61 = !DILocation(column: 5, line: 56, scope: !19)
!62 = !DILocalVariable(file: !0, line: 58, name: "status", scope: !20, type: !10)
!63 = !DILocation(column: 1, line: 58, scope: !20)
!64 = !DILocation(column: 5, line: 59, scope: !20)
!65 = !DILocation(column: 5, line: 104, scope: !21)
!66 = !DILocation(column: 5, line: 105, scope: !21)
!67 = !DILocation(column: 9, line: 106, scope: !21)
!68 = !DILocation(column: 5, line: 108, scope: !21)
!69 = !DISubrange(count: 4096)
!70 = !{ !69 }
!71 = !DICompositeType(baseType: !12, elements: !70, size: 32768, tag: DW_TAG_array_type)
!72 = !DILocalVariable(file: !0, line: 108, name: "buf", scope: !21, type: !71)
!73 = !DILocation(column: 1, line: 108, scope: !21)
!74 = !DILocation(column: 5, line: 109, scope: !21)
!75 = !DILocation(column: 5, line: 110, scope: !21)
!76 = !DILocation(column: 5, line: 112, scope: !21)
!77 = !DILocation(column: 9, line: 113, scope: !21)
!78 = !DILocation(column: 5, line: 118, scope: !21)
!79 = !DILocalVariable(file: !0, line: 118, name: "addr", scope: !21, type: !11)
!80 = !DILocation(column: 1, line: 118, scope: !21)
!81 = !DILocation(column: 5, line: 119, scope: !21)
!82 = !DILocation(column: 9, line: 120, scope: !21)
!83 = !DILocation(column: 9, line: 121, scope: !21)
!84 = !DILocation(column: 13, line: 122, scope: !21)
!85 = !DILocation(column: 13, line: 124, scope: !21)
!86 = !DILocation(column: 13, line: 126, scope: !21)
!87 = !DILocation(column: 5, line: 128, scope: !21)
!88 = !DILocation(column: 5, line: 136, scope: !22)
!89 = !DICompositeType(align: 64, file: !0, name: "Timeval", size: 128, tag: DW_TAG_structure_type)
!90 = !DILocalVariable(file: !0, line: 136, name: "tv", scope: !22, type: !89)
!91 = !DILocation(column: 1, line: 136, scope: !22)
!92 = !DILocation(column: 5, line: 137, scope: !22)
!93 = !DILocation(column: 5, line: 138, scope: !22)
!94 = !DILocation(column: 5, line: 142, scope: !23)
!95 = !DILocalVariable(file: !0, line: 142, name: "tv", scope: !23, type: !89)
!96 = !DILocation(column: 1, line: 142, scope: !23)
!97 = !DILocation(column: 5, line: 143, scope: !23)
!98 = !DILocation(column: 5, line: 144, scope: !23)
!99 = !DILocalVariable(file: !0, line: 153, name: "seed", scope: !24, type: !11)
!100 = !DILocation(column: 1, line: 153, scope: !24)
!101 = !DILocation(column: 5, line: 154, scope: !24)
!102 = !DILocation(column: 5, line: 155, scope: !24)
!103 = !DILocation(column: 9, line: 156, scope: !24)
!104 = !DILocation(column: 5, line: 160, scope: !25)
!105 = !DILocation(column: 5, line: 161, scope: !25)
!106 = !DILocalVariable(file: !0, line: 164, name: "count", scope: !26, type: !10)
!107 = !DILocation(column: 1, line: 164, scope: !26)
!108 = !DILocation(column: 5, line: 165, scope: !26)
!109 = !DILocation(column: 9, line: 166, scope: !26)
!110 = !DILocation(column: 5, line: 167, scope: !26)
!111 = !DILocation(column: 9, line: 169, scope: !26)
!112 = !DILocation(column: 9, line: 171, scope: !26)
!113 = !DILocation(column: 9, line: 172, scope: !26)
!114 = !DILocation(column: 9, line: 173, scope: !26)
!115 = !DICompositeType(align: 64, file: !0, name: "TestEntry", size: 128, tag: DW_TAG_structure_type)
!116 = !DIDerivedType(baseType: !115, size: 64, tag: DW_TAG_pointer_type)
!117 = !DILocalVariable(file: !0, line: 195, name: "entry", scope: !27, type: !116)
!118 = !DILocation(column: 1, line: 195, scope: !27)
!119 = !DILocation(column: 5, line: 196, scope: !27)
!120 = !DILocation(column: 5, line: 197, scope: !27)
!121 = !DILocation(column: 5, line: 198, scope: !27)
!122 = !DILocalVariable(file: !0, line: 203, name: "entry", scope: !28, type: !116)
!123 = !DILocation(column: 1, line: 203, scope: !28)
!124 = !DICompositeType(align: 32, file: !0, name: "TestRunResult", size: 96, tag: DW_TAG_structure_type)
!125 = !DIDerivedType(baseType: !124, size: 64, tag: DW_TAG_pointer_type)
!126 = !DILocalVariable(file: !0, line: 203, name: "result", scope: !28, type: !125)
!127 = !DILocation(column: 5, line: 204, scope: !28)
!128 = !DILocation(column: 5, line: 206, scope: !28)
!129 = !DILocation(column: 9, line: 208, scope: !28)
!130 = !DILocation(column: 9, line: 209, scope: !28)
!131 = !DILocation(column: 9, line: 210, scope: !28)
!132 = !DILocation(column: 9, line: 211, scope: !28)
!133 = !DILocation(column: 5, line: 213, scope: !28)
!134 = !DILocation(column: 9, line: 216, scope: !28)
!135 = !DILocation(column: 9, line: 217, scope: !28)
!136 = !DILocation(column: 9, line: 218, scope: !28)
!137 = !DILocation(column: 9, line: 219, scope: !28)
!138 = !DILocation(column: 9, line: 221, scope: !28)
!139 = !DILocation(column: 5, line: 225, scope: !28)
!140 = !DILocation(column: 5, line: 226, scope: !28)
!141 = !DILocalVariable(file: !0, line: 226, name: "status", scope: !28, type: !10)
!142 = !DILocation(column: 1, line: 226, scope: !28)
!143 = !DILocation(column: 5, line: 228, scope: !28)
!144 = !DILocation(column: 9, line: 229, scope: !28)
!145 = !DILocation(column: 9, line: 231, scope: !28)
!146 = !DILocation(column: 17, line: 234, scope: !28)
!147 = !DILocation(column: 17, line: 235, scope: !28)
!148 = !DILocation(column: 21, line: 236, scope: !28)
!149 = !DILocation(column: 21, line: 238, scope: !28)
!150 = !DILocation(column: 17, line: 239, scope: !28)
!151 = !DILocation(column: 17, line: 240, scope: !28)
!152 = !DILocation(column: 17, line: 241, scope: !28)
!153 = !DILocation(column: 17, line: 243, scope: !28)
!154 = !DILocation(column: 17, line: 244, scope: !28)
!155 = !DILocation(column: 17, line: 245, scope: !28)
!156 = !DILocation(column: 17, line: 246, scope: !28)
!157 = !DILocation(column: 9, line: 248, scope: !28)
!158 = !DILocation(column: 13, line: 250, scope: !28)
!159 = !DILocation(column: 13, line: 251, scope: !28)
!160 = !DILocation(column: 13, line: 252, scope: !28)
!161 = !DILocation(column: 13, line: 253, scope: !28)
!162 = !DILocation(column: 9, line: 256, scope: !28)
!163 = !DILocation(column: 9, line: 257, scope: !28)
!164 = !DILocation(column: 13, line: 259, scope: !28)
!165 = !DILocation(column: 13, line: 261, scope: !28)
!166 = !DILocation(column: 13, line: 262, scope: !28)
!167 = !DILocation(column: 13, line: 263, scope: !28)
!168 = !DILocation(column: 13, line: 264, scope: !28)
!169 = !DILocation(column: 13, line: 265, scope: !28)
!170 = !DILocation(column: 9, line: 268, scope: !28)
!171 = !DISubrange(count: 2)
!172 = !{ !171 }
!173 = !DICompositeType(baseType: !11, elements: !172, size: 128, tag: DW_TAG_array_type)
!174 = !DILocalVariable(file: !0, line: 268, name: "req", scope: !28, type: !173)
!175 = !DILocation(column: 1, line: 268, scope: !28)
!176 = !DILocation(column: 9, line: 269, scope: !28)
!177 = !DILocation(column: 9, line: 270, scope: !28)
!178 = !DILocation(column: 5, line: 273, scope: !28)
!179 = !DILocalVariable(file: !0, line: 278, name: "entry", scope: !29, type: !116)
!180 = !DILocation(column: 1, line: 278, scope: !29)
!181 = !DILocation(column: 5, line: 279, scope: !29)
!182 = !DILocation(column: 9, line: 280, scope: !29)
!183 = !DILocation(column: 5, line: 282, scope: !29)
!184 = !DILocalVariable(file: !0, line: 282, name: "result", scope: !29, type: !124)
!185 = !DILocation(column: 1, line: 282, scope: !29)
!186 = !DILocation(column: 5, line: 283, scope: !29)
!187 = !DILocation(column: 5, line: 285, scope: !29)
!188 = !DILocation(column: 9, line: 286, scope: !29)
!189 = !DILocation(column: 5, line: 287, scope: !29)
!190 = !DILocalVariable(file: !0, line: 290, name: "entry", scope: !30, type: !116)
!191 = !DILocation(column: 1, line: 290, scope: !30)
!192 = !DILocalVariable(file: !0, line: 290, name: "result", scope: !30, type: !125)
!193 = !DILocation(column: 5, line: 291, scope: !30)
!194 = !DILocation(column: 9, line: 292, scope: !30)
!195 = !DILocation(column: 9, line: 293, scope: !30)
!196 = !DILocation(column: 13, line: 294, scope: !30)
!197 = !DILocation(column: 13, line: 296, scope: !30)
!198 = !DILocation(column: 9, line: 297, scope: !30)
!199 = !DILocation(column: 9, line: 298, scope: !30)
!200 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!201 = !DILocalVariable(file: !0, line: 307, name: "name", scope: !31, type: !200)
!202 = !DILocation(column: 1, line: 307, scope: !31)
!203 = !DILocation(column: 5, line: 308, scope: !31)
!204 = !DILocation(column: 9, line: 309, scope: !31)
!205 = !DILocation(column: 5, line: 310, scope: !31)
!206 = !DILocation(column: 9, line: 311, scope: !31)
!207 = !DILocation(column: 5, line: 312, scope: !31)
!208 = !DILocation(column: 9, line: 313, scope: !31)
!209 = !DILocation(column: 5, line: 314, scope: !31)
!210 = !DILocation(column: 9, line: 315, scope: !31)
!211 = !DILocation(column: 5, line: 316, scope: !31)
!212 = !DILocation(column: 9, line: 317, scope: !31)
!213 = !DILocation(column: 5, line: 318, scope: !31)
!214 = !DILocation(column: 5, line: 324, scope: !32)
!215 = !DILocation(column: 5, line: 327, scope: !32)
!216 = !DILocation(column: 5, line: 328, scope: !32)
!217 = !DILocation(column: 9, line: 329, scope: !32)
!218 = !DILocation(column: 9, line: 330, scope: !32)
!219 = !DILocation(column: 5, line: 333, scope: !32)
!220 = !DILocation(column: 5, line: 334, scope: !32)
!221 = !DILocation(column: 5, line: 336, scope: !32)
!222 = !DILocation(column: 9, line: 337, scope: !32)
!223 = !DILocation(column: 9, line: 338, scope: !32)
!224 = !DILocation(column: 9, line: 339, scope: !32)
!225 = !DILocation(column: 5, line: 342, scope: !32)
!226 = !DILocation(column: 5, line: 343, scope: !32)
!227 = !DILocation(column: 9, line: 344, scope: !32)
!228 = !DILocation(column: 9, line: 345, scope: !32)
!229 = !DILocation(column: 9, line: 346, scope: !32)
!230 = !DILocation(column: 5, line: 348, scope: !32)
!231 = !DILocation(column: 5, line: 349, scope: !32)
!232 = !DILocation(column: 5, line: 351, scope: !32)
!233 = !DILocation(column: 9, line: 352, scope: !32)
!234 = !DILocation(column: 9, line: 353, scope: !32)
!235 = !DILocation(column: 9, line: 354, scope: !32)
!236 = !DILocation(column: 5, line: 357, scope: !32)
!237 = !DICompositeType(align: 64, file: !0, name: "ElfReader", size: 448, tag: DW_TAG_structure_type)
!238 = !DILocalVariable(file: !0, line: 357, name: "reader", scope: !32, type: !237)
!239 = !DILocation(column: 1, line: 357, scope: !32)
!240 = !DILocation(column: 5, line: 358, scope: !32)
!241 = !DILocation(column: 9, line: 359, scope: !32)
!242 = !DILocation(column: 9, line: 360, scope: !32)
!243 = !DILocation(column: 9, line: 361, scope: !32)
!244 = !DILocation(column: 5, line: 364, scope: !32)
!245 = !DILocation(column: 9, line: 365, scope: !32)
!246 = !DILocation(column: 9, line: 366, scope: !32)
!247 = !DILocation(column: 9, line: 367, scope: !32)
!248 = !DILocation(column: 5, line: 372, scope: !32)
!249 = !DILocation(column: 5, line: 373, scope: !32)
!250 = !DILocalVariable(file: !0, line: 373, name: "i", scope: !32, type: !11)
!251 = !DILocation(column: 1, line: 373, scope: !32)
!252 = !DILocation(column: 5, line: 375, scope: !32)
!253 = !DILocation(column: 9, line: 376, scope: !32)
!254 = !DILocation(column: 9, line: 379, scope: !32)
!255 = !DILocation(column: 13, line: 380, scope: !32)
!256 = !DILocation(column: 17, line: 383, scope: !32)
!257 = !DILocation(column: 17, line: 384, scope: !32)
!258 = !DILocation(column: 17, line: 386, scope: !32)
!259 = !DILocation(column: 17, line: 387, scope: !32)
!260 = !DILocation(column: 17, line: 388, scope: !32)
!261 = !DILocation(column: 9, line: 390, scope: !32)
!262 = !DILocation(column: 5, line: 395, scope: !32)
!263 = !DILocalVariable(file: !0, line: 412, name: "sig", scope: !33, type: !10)
!264 = !DILocation(column: 1, line: 412, scope: !33)
!265 = !DILocation(column: 5, line: 413, scope: !33)
!266 = !DILocation(column: 9, line: 414, scope: !33)
!267 = !DILocation(column: 5, line: 415, scope: !33)
!268 = !DILocation(column: 9, line: 416, scope: !33)
!269 = !DILocation(column: 5, line: 417, scope: !33)
!270 = !DILocation(column: 9, line: 418, scope: !33)
!271 = !DILocation(column: 5, line: 419, scope: !33)
!272 = !DILocation(column: 9, line: 420, scope: !33)
!273 = !DILocation(column: 5, line: 421, scope: !33)
!274 = !DILocation(column: 9, line: 422, scope: !33)
!275 = !DILocation(column: 5, line: 423, scope: !33)
!276 = !DILocation(column: 9, line: 424, scope: !33)
!277 = !DILocation(column: 5, line: 425, scope: !33)
!278 = !DILocation(column: 9, line: 426, scope: !33)
!279 = !DILocation(column: 5, line: 427, scope: !33)
!280 = !DILocation(column: 9, line: 428, scope: !33)
!281 = !DILocation(column: 5, line: 429, scope: !33)
!282 = !DILocation(column: 9, line: 430, scope: !33)
!283 = !DILocation(column: 5, line: 431, scope: !33)
!284 = !DILocation(column: 9, line: 432, scope: !33)
!285 = !DILocation(column: 5, line: 433, scope: !33)
!286 = !DILocation(column: 5, line: 441, scope: !34)
!287 = !DILocation(column: 5, line: 445, scope: !34)
!288 = !DILocation(column: 5, line: 446, scope: !34)
!289 = !DILocation(column: 9, line: 447, scope: !34)
!290 = !DILocation(column: 5, line: 449, scope: !34)
!291 = !DILocation(column: 9, line: 450, scope: !34)
!292 = !DILocation(column: 9, line: 454, scope: !34)
!293 = !DILocation(column: 5, line: 457, scope: !34)
!294 = !DILocation(column: 9, line: 458, scope: !34)
!295 = !DILocalVariable(file: !0, line: 458, name: "seed", scope: !34, type: !11)
!296 = !DILocation(column: 1, line: 458, scope: !34)
!297 = !DILocation(column: 9, line: 459, scope: !34)
!298 = !DILocation(column: 13, line: 460, scope: !34)
!299 = !DILocation(column: 9, line: 461, scope: !34)
!300 = !DILocation(column: 9, line: 462, scope: !34)
!301 = !DILocation(column: 13, line: 464, scope: !34)
!302 = !DILocation(column: 13, line: 465, scope: !34)
!303 = !DILocation(column: 5, line: 469, scope: !34)
!304 = !DILocation(column: 9, line: 470, scope: !34)
!305 = !DILocation(column: 9, line: 471, scope: !34)
!306 = !DILocation(column: 9, line: 472, scope: !34)
!307 = !DILocation(column: 9, line: 473, scope: !34)
!308 = !DILocation(column: 13, line: 474, scope: !34)
!309 = !DILocation(column: 17, line: 476, scope: !34)
!310 = !DILocation(column: 17, line: 477, scope: !34)
!311 = !DILocation(column: 9, line: 479, scope: !34)
!312 = !DILocation(column: 5, line: 481, scope: !34)
!313 = !DILocation(column: 5, line: 484, scope: !34)
!314 = !DICompositeType(align: 64, file: !0, name: "TestSummary", size: 256, tag: DW_TAG_structure_type)
!315 = !DILocalVariable(file: !0, line: 484, name: "summary", scope: !34, type: !314)
!316 = !DILocation(column: 1, line: 484, scope: !34)
!317 = !DILocation(column: 5, line: 485, scope: !34)
!318 = !DILocalVariable(file: !0, line: 485, name: "skipped_by_filter", scope: !34, type: !10)
!319 = !DILocation(column: 1, line: 485, scope: !34)
!320 = !DILocation(column: 5, line: 486, scope: !34)
!321 = !DILocation(column: 5, line: 488, scope: !34)
!322 = !DILocation(column: 9, line: 489, scope: !34)
!323 = !DILocation(column: 9, line: 490, scope: !34)
!324 = !DILocation(column: 9, line: 493, scope: !34)
!325 = !DILocation(column: 13, line: 494, scope: !34)
!326 = !DILocation(column: 13, line: 495, scope: !34)
!327 = !DILocation(column: 9, line: 498, scope: !34)
!328 = !DICompositeType(align: 64, file: !0, name: "StrView", size: 128, tag: DW_TAG_structure_type)
!329 = !DILocalVariable(file: !0, line: 498, name: "name", scope: !34, type: !328)
!330 = !DILocation(column: 1, line: 498, scope: !34)
!331 = !DILocation(column: 9, line: 500, scope: !34)
!332 = !DILocation(column: 9, line: 501, scope: !34)
!333 = !DILocalVariable(file: !0, line: 501, name: "result", scope: !34, type: !124)
!334 = !DILocation(column: 1, line: 501, scope: !34)
!335 = !DILocation(column: 9, line: 502, scope: !34)
!336 = !DILocation(column: 9, line: 503, scope: !34)
!337 = !DILocation(column: 9, line: 505, scope: !34)
!338 = !DILocalVariable(file: !0, line: 505, name: "failed_this_test", scope: !34, type: !10)
!339 = !DILocation(column: 1, line: 505, scope: !34)
!340 = !DILocation(column: 9, line: 506, scope: !34)
!341 = !DILocation(column: 13, line: 507, scope: !34)
!342 = !DILocation(column: 13, line: 517, scope: !34)
!343 = !DILocalVariable(file: !0, line: 517, name: "sig_name", scope: !34, type: !328)
!344 = !DILocation(column: 1, line: 517, scope: !34)
!345 = !DILocation(column: 13, line: 518, scope: !34)
!346 = !DILocation(column: 13, line: 525, scope: !34)
!347 = !DILocation(column: 13, line: 526, scope: !34)
!348 = !DILocation(column: 13, line: 529, scope: !34)
!349 = !DILocation(column: 13, line: 536, scope: !34)
!350 = !DILocation(column: 13, line: 537, scope: !34)
!351 = !DILocation(column: 13, line: 540, scope: !34)
!352 = !DILocation(column: 13, line: 547, scope: !34)
!353 = !DILocation(column: 13, line: 548, scope: !34)
!354 = !DILocation(column: 13, line: 552, scope: !34)
!355 = !DILocation(column: 5, line: 554, scope: !34)
!356 = !DILocation(column: 5, line: 555, scope: !34)
!357 = !DILocation(column: 5, line: 558, scope: !34)
!358 = !DILocation(column: 9, line: 562, scope: !34)
!359 = !DILocation(column: 9, line: 565, scope: !34)
!360 = !DILocation(column: 13, line: 566, scope: !34)
!361 = !DILocation(column: 5, line: 571, scope: !34)
!362 = !DILocalVariable(file: !0, line: 577, name: "argc", scope: !35, type: !10)
!363 = !DILocation(column: 1, line: 577, scope: !35)
!364 = !DIDerivedType(baseType: !200, size: 64, tag: DW_TAG_pointer_type)
!365 = !DILocalVariable(file: !0, line: 577, name: "argv", scope: !35, type: !364)
!366 = !DILocation(column: 5, line: 578, scope: !35)
!367 = !DICompositeType(align: 64, file: !0, name: "ArgParser", size: 32640, tag: DW_TAG_structure_type)
!368 = !DILocalVariable(file: !0, line: 578, name: "parser", scope: !35, type: !367)
!369 = !DILocation(column: 1, line: 578, scope: !35)
!370 = !DILocation(column: 5, line: 579, scope: !35)
!371 = !DILocation(column: 5, line: 581, scope: !35)
!372 = !DILocation(column: 5, line: 582, scope: !35)
!373 = !DILocation(column: 5, line: 583, scope: !35)
!374 = !DILocation(column: 5, line: 584, scope: !35)
!375 = !DILocation(column: 5, line: 585, scope: !35)
!376 = !DILocation(column: 5, line: 586, scope: !35)
!377 = !DILocation(column: 5, line: 587, scope: !35)
!378 = !DILocation(column: 5, line: 588, scope: !35)
!379 = !DILocation(column: 5, line: 589, scope: !35)
!380 = !DILocation(column: 5, line: 590, scope: !35)
!381 = !DILocation(column: 5, line: 591, scope: !35)
!382 = !DILocation(column: 5, line: 592, scope: !35)
!383 = !DILocation(column: 5, line: 593, scope: !35)
!384 = !DILocation(column: 5, line: 594, scope: !35)
!385 = !DILocation(column: 5, line: 596, scope: !35)
!386 = !DILocation(column: 9, line: 597, scope: !35)
!387 = !DILocation(column: 5, line: 600, scope: !35)
!388 = !DILocation(column: 9, line: 601, scope: !35)
!389 = !DILocation(column: 9, line: 602, scope: !35)
!390 = !DILocation(column: 5, line: 605, scope: !35)
!391 = !DILocation(column: 5, line: 606, scope: !35)
!392 = !DILocation(column: 5, line: 607, scope: !35)
!393 = !DILocation(column: 5, line: 608, scope: !35)
!394 = !DILocation(column: 5, line: 609, scope: !35)
!395 = !DILocation(column: 5, line: 610, scope: !35)
!396 = !DILocation(column: 5, line: 611, scope: !35)
!397 = !DILocation(column: 5, line: 612, scope: !35)
!398 = !DILocation(column: 5, line: 613, scope: !35)
!399 = !DILocation(column: 5, line: 614, scope: !35)
!400 = !DILocation(column: 5, line: 615, scope: !35)
!401 = !DILocation(column: 5, line: 618, scope: !35)
!402 = !DILocation(column: 5, line: 619, scope: !35)
!403 = !DILocation(column: 5, line: 621, scope: !35)
!404 = !DILocation(column: 9, line: 622, scope: !35)
!405 = !DILocation(column: 9, line: 623, scope: !35)
!406 = !DILocation(column: 5, line: 625, scope: !35)
!407 = !DILocation(column: 9, line: 626, scope: !35)
!408 = !DILocation(column: 9, line: 629, scope: !35)
!409 = !DILocation(column: 5, line: 633, scope: !35)
!410 = !DILocation(column: 9, line: 634, scope: !35)
!411 = !DILocation(column: 9, line: 635, scope: !35)
!412 = !DILocation(column: 5, line: 638, scope: !35)
!413 = !DILocation(column: 9, line: 639, scope: !35)
!414 = !DILocation(column: 9, line: 640, scope: !35)
!415 = !DILocation(column: 5, line: 643, scope: !35)
!416 = !DILocation(column: 9, line: 644, scope: !35)
!417 = !DILocation(column: 5, line: 647, scope: !35)
!418 = !DILocalVariable(file: !0, line: 653, name: "name", scope: !36, type: !200)
!419 = !DILocation(column: 1, line: 653, scope: !36)
!420 = !DILocation(column: 5, line: 655, scope: !36)
!421 = !DILocalVariable(file: !0, line: 662, name: "argc", scope: !37, type: !10)
!422 = !DILocation(column: 1, line: 662, scope: !37)
!423 = !DILocalVariable(file: !0, line: 662, name: "argv", scope: !37, type: !364)
!424 = !DILocation(column: 5, line: 663, scope: !37)
!425 = !DILocation(column: 5, line: 664, scope: !37)
!426 = !DILocation(column: 9, line: 665, scope: !37)
!427 = !DILocation(column: 13, line: 666, scope: !37)
!428 = !DILocation(column: 9, line: 667, scope: !37)
!429 = !DILocation(column: 5, line: 669, scope: !37)
!430 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!431 = !DIDerivedType(baseType: !430, size: 64, tag: DW_TAG_reference_type)
!432 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !38, type: !431)
!433 = !DILocation(column: 1, line: 219, scope: !38)
!434 = !DILocation(column: 5, line: 220, scope: !38)
!435 = !DILocation(column: 5, line: 221, scope: !38)
!436 = !DILocation(column: 5, line: 117, scope: !39)
!437 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !39, type: !430)
!438 = !DILocation(column: 1, line: 117, scope: !39)
!439 = !DILocation(column: 5, line: 118, scope: !39)
!440 = !DILocation(column: 5, line: 119, scope: !39)
!441 = !DILocation(column: 5, line: 120, scope: !39)
!442 = !DILocation(column: 5, line: 121, scope: !39)
!443 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !40, type: !431)
!444 = !DILocation(column: 1, line: 148, scope: !40)
!445 = !DILocation(column: 5, line: 149, scope: !40)
!446 = !DILocation(column: 5, line: 151, scope: !40)
!447 = !DILocation(column: 5, line: 152, scope: !40)
!448 = !DILocation(column: 5, line: 153, scope: !40)
!449 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !41, type: !431)
!450 = !DILocation(column: 1, line: 244, scope: !41)
!451 = !DILocation(column: 5, line: 245, scope: !41)
!452 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !42, type: !431)
!453 = !DILocation(column: 1, line: 193, scope: !42)
!454 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !42, type: !11)
!455 = !DILocation(column: 5, line: 194, scope: !42)
!456 = !DILocation(column: 9, line: 195, scope: !42)
!457 = !DILocation(column: 5, line: 197, scope: !42)
!458 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !42, type: !11)
!459 = !DILocation(column: 1, line: 197, scope: !42)
!460 = !DILocation(column: 5, line: 198, scope: !42)
!461 = !DILocation(column: 9, line: 199, scope: !42)
!462 = !DILocation(column: 5, line: 200, scope: !42)
!463 = !DILocation(column: 9, line: 201, scope: !42)
!464 = !DILocation(column: 5, line: 203, scope: !42)
!465 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !43, type: !431)
!466 = !DILocation(column: 1, line: 225, scope: !43)
!467 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !43, type: !11)
!468 = !DILocation(column: 5, line: 226, scope: !43)
!469 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !44, type: !431)
!470 = !DILocation(column: 1, line: 235, scope: !44)
!471 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !44, type: !11)
!472 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !44, type: !12)
!473 = !DILocation(column: 5, line: 236, scope: !44)
!474 = !DILocation(column: 5, line: 237, scope: !44)
!475 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !45, type: !431)
!476 = !DILocation(column: 1, line: 288, scope: !45)
!477 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !45, type: !200)
!478 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !45, type: !11)
!479 = !DILocation(column: 5, line: 289, scope: !45)
!480 = !DILocation(column: 13, line: 291, scope: !45)
!481 = !DILocation(column: 5, line: 292, scope: !45)
!482 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!483 = !DIDerivedType(baseType: !482, size: 64, tag: DW_TAG_reference_type)
!484 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !46, type: !483)
!485 = !DILocation(column: 1, line: 210, scope: !46)
!486 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!487 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !46, type: !486)
!488 = !DILocation(column: 5, line: 211, scope: !46)
!489 = !DILocation(column: 9, line: 212, scope: !46)
!490 = !DILocation(column: 5, line: 213, scope: !46)
!491 = !DILocation(column: 5, line: 214, scope: !46)
!492 = !DILocation(column: 5, line: 215, scope: !46)
!493 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !47, type: !431)
!494 = !DILocation(column: 1, line: 210, scope: !47)
!495 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !47, type: !12)
!496 = !DILocation(column: 5, line: 211, scope: !47)
!497 = !DILocation(column: 9, line: 212, scope: !47)
!498 = !DILocation(column: 5, line: 213, scope: !47)
!499 = !DILocation(column: 5, line: 214, scope: !47)
!500 = !DILocation(column: 5, line: 215, scope: !47)
!501 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !48, type: !11)
!502 = !DILocation(column: 1, line: 124, scope: !48)
!503 = !DILocation(column: 5, line: 125, scope: !48)
!504 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !48, type: !430)
!505 = !DILocation(column: 1, line: 125, scope: !48)
!506 = !DILocation(column: 5, line: 126, scope: !48)
!507 = !DILocation(column: 9, line: 127, scope: !48)
!508 = !DILocation(column: 9, line: 128, scope: !48)
!509 = !DILocation(column: 9, line: 129, scope: !48)
!510 = !DILocation(column: 9, line: 130, scope: !48)
!511 = !DILocation(column: 5, line: 132, scope: !48)
!512 = !DILocation(column: 5, line: 133, scope: !48)
!513 = !DILocation(column: 5, line: 134, scope: !48)
!514 = !DILocation(column: 9, line: 135, scope: !48)
!515 = !DILocation(column: 9, line: 136, scope: !48)
!516 = !DILocation(column: 9, line: 137, scope: !48)
!517 = !DILocation(column: 5, line: 139, scope: !48)
!518 = !DILocation(column: 5, line: 140, scope: !48)
!519 = !DILocation(column: 5, line: 141, scope: !48)
!520 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !49, type: !431)
!521 = !DILocation(column: 1, line: 179, scope: !49)
!522 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !49, type: !11)
!523 = !DILocation(column: 5, line: 180, scope: !49)
!524 = !DILocation(column: 9, line: 181, scope: !49)
!525 = !DILocation(column: 5, line: 183, scope: !49)
!526 = !DILocation(column: 5, line: 184, scope: !49)
!527 = !DILocation(column: 5, line: 185, scope: !49)
!528 = !DILocation(column: 9, line: 186, scope: !49)
!529 = !DILocation(column: 5, line: 188, scope: !49)
!530 = !DILocation(column: 5, line: 189, scope: !49)
!531 = !DILocation(column: 5, line: 190, scope: !49)
!532 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !50, type: !483)
!533 = !DILocation(column: 1, line: 193, scope: !50)
!534 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !50, type: !11)
!535 = !DILocation(column: 5, line: 194, scope: !50)
!536 = !DILocation(column: 9, line: 195, scope: !50)
!537 = !DILocation(column: 5, line: 197, scope: !50)
!538 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !50, type: !11)
!539 = !DILocation(column: 1, line: 197, scope: !50)
!540 = !DILocation(column: 5, line: 198, scope: !50)
!541 = !DILocation(column: 9, line: 199, scope: !50)
!542 = !DILocation(column: 5, line: 200, scope: !50)
!543 = !DILocation(column: 9, line: 201, scope: !50)
!544 = !DILocation(column: 5, line: 203, scope: !50)
!545 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !51, type: !483)
!546 = !DILocation(column: 1, line: 179, scope: !51)
!547 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !51, type: !11)
!548 = !DILocation(column: 5, line: 180, scope: !51)
!549 = !DILocation(column: 9, line: 181, scope: !51)
!550 = !DILocation(column: 5, line: 183, scope: !51)
!551 = !DILocation(column: 5, line: 184, scope: !51)
!552 = !DILocation(column: 5, line: 185, scope: !51)
!553 = !DILocation(column: 9, line: 186, scope: !51)
!554 = !DILocation(column: 5, line: 188, scope: !51)
!555 = !DILocation(column: 5, line: 189, scope: !51)
!556 = !DILocation(column: 5, line: 190, scope: !51)