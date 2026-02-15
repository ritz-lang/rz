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
%"struct.ritz_module_1.OptDef" = type {i8, i8*, i8*, i8*, i8*, i32, i32, i8*}
%"struct.ritz_module_1.PosDef" = type {i8*, i8*, i32, i32}
%"struct.ritz_module_1.ArgParser" = type {i8*, i8*, [32 x %"struct.ritz_module_1.OptDef"], i32, [8 x %"struct.ritz_module_1.PosDef"], i32, [256 x i8*], i32, i8*}
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

define i32 @"args_init"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8* %"program.arg", i8* %"desc.arg") !dbg !17
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !51, metadata !7), !dbg !52
  %"program" = alloca i8*
  store i8* %"program.arg", i8** %"program"
  call void @"llvm.dbg.declare"(metadata i8** %"program", metadata !54, metadata !7), !dbg !52
  %"desc" = alloca i8*
  store i8* %"desc.arg", i8** %"desc"
  call void @"llvm.dbg.declare"(metadata i8** %"desc", metadata !55, metadata !7), !dbg !52
  %".11" = load i8*, i8** %"program", !dbg !56
  %".12" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !56
  %".13" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".12", i32 0, i32 0 , !dbg !56
  store i8* %".11", i8** %".13", !dbg !56
  %".15" = load i8*, i8** %"desc", !dbg !57
  %".16" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !57
  %".17" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".16", i32 0, i32 1 , !dbg !57
  store i8* %".15", i8** %".17", !dbg !57
  %".19" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !58
  %".20" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".19", i32 0, i32 3 , !dbg !58
  %".21" = trunc i64 0 to i32 , !dbg !58
  store i32 %".21", i32* %".20", !dbg !58
  %".23" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !59
  %".24" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".23", i32 0, i32 5 , !dbg !59
  %".25" = trunc i64 0 to i32 , !dbg !59
  store i32 %".25", i32* %".24", !dbg !59
  %".27" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !60
  %".28" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".27", i32 0, i32 7 , !dbg !60
  %".29" = trunc i64 0 to i32 , !dbg !60
  store i32 %".29", i32* %".28", !dbg !60
  %".31" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !61
  %".32" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".31", i32 0, i32 8 , !dbg !61
  store i8* null, i8** %".32", !dbg !61
  ret i32 0, !dbg !61
}

define i32 @"args_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8 %"short.arg", i8* %"long.arg", i8* %"desc.arg") !dbg !18
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !62, metadata !7), !dbg !63
  %"short" = alloca i8
  store i8 %"short.arg", i8* %"short"
  call void @"llvm.dbg.declare"(metadata i8* %"short", metadata !64, metadata !7), !dbg !63
  %"long" = alloca i8*
  store i8* %"long.arg", i8** %"long"
  call void @"llvm.dbg.declare"(metadata i8** %"long", metadata !65, metadata !7), !dbg !63
  %"desc" = alloca i8*
  store i8* %"desc.arg", i8** %"desc"
  call void @"llvm.dbg.declare"(metadata i8** %"desc", metadata !66, metadata !7), !dbg !63
  %".14" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !67
  %".15" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".14", i32 0, i32 3 , !dbg !67
  %".16" = load i32, i32* %".15", !dbg !67
  %".17" = icmp sge i32 %".16", 32 , !dbg !67
  br i1 %".17", label %"if.then", label %"if.end", !dbg !67
if.then:
  ret i32 0, !dbg !68
if.end:
  %".20" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !69
  %".21" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".20", i32 0, i32 3 , !dbg !69
  %".22" = load i32, i32* %".21", !dbg !69
  %".23" = load i8, i8* %"short", !dbg !70
  %".24" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !70
  %".25" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".24", i32 0, i32 2 , !dbg !70
  %".26" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".25", i32 0, i32 %".22" , !dbg !70
  %".27" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".26", !dbg !70
  %".28" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !70
  %".29" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".28", i32 0, i32 2 , !dbg !70
  %".30" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".29", i32 0, i32 %".22" , !dbg !70
  %".31" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".30", i32 0, i32 0 , !dbg !70
  store i8 %".23", i8* %".31", !dbg !70
  %".33" = load i8*, i8** %"long", !dbg !71
  %".34" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !71
  %".35" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".34", i32 0, i32 2 , !dbg !71
  %".36" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".35", i32 0, i32 %".22" , !dbg !71
  %".37" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".36", !dbg !71
  %".38" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !71
  %".39" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".38", i32 0, i32 2 , !dbg !71
  %".40" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".39", i32 0, i32 %".22" , !dbg !71
  %".41" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".40", i32 0, i32 1 , !dbg !71
  store i8* %".33", i8** %".41", !dbg !71
  %".43" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !72
  %".44" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".43", i32 0, i32 2 , !dbg !72
  %".45" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".44", i32 0, i32 %".22" , !dbg !72
  %".46" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".45", !dbg !72
  %".47" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !72
  %".48" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".47", i32 0, i32 2 , !dbg !72
  %".49" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".48", i32 0, i32 %".22" , !dbg !72
  %".50" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".49", i32 0, i32 2 , !dbg !72
  store i8* null, i8** %".50", !dbg !72
  %".52" = load i8*, i8** %"desc", !dbg !73
  %".53" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !73
  %".54" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".53", i32 0, i32 2 , !dbg !73
  %".55" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".54", i32 0, i32 %".22" , !dbg !73
  %".56" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".55", !dbg !73
  %".57" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !73
  %".58" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".57", i32 0, i32 2 , !dbg !73
  %".59" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".58", i32 0, i32 %".22" , !dbg !73
  %".60" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".59", i32 0, i32 3 , !dbg !73
  store i8* %".52", i8** %".60", !dbg !73
  %".62" = getelementptr [2 x i8], [2 x i8]* @".str.0", i64 0, i64 0 , !dbg !74
  %".63" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !74
  %".64" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".63", i32 0, i32 2 , !dbg !74
  %".65" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".64", i32 0, i32 %".22" , !dbg !74
  %".66" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".65", !dbg !74
  %".67" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !74
  %".68" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".67", i32 0, i32 2 , !dbg !74
  %".69" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".68", i32 0, i32 %".22" , !dbg !74
  %".70" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".69", i32 0, i32 4 , !dbg !74
  store i8* %".62", i8** %".70", !dbg !74
  %".72" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !75
  %".73" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".72", i32 0, i32 2 , !dbg !75
  %".74" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".73", i32 0, i32 %".22" , !dbg !75
  %".75" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".74", !dbg !75
  %".76" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !75
  %".77" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".76", i32 0, i32 2 , !dbg !75
  %".78" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".77", i32 0, i32 %".22" , !dbg !75
  %".79" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".78", i32 0, i32 5 , !dbg !75
  store i32 0, i32* %".79", !dbg !75
  %".81" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !76
  %".82" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".81", i32 0, i32 2 , !dbg !76
  %".83" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".82", i32 0, i32 %".22" , !dbg !76
  %".84" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".83", !dbg !76
  %".85" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !76
  %".86" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".85", i32 0, i32 2 , !dbg !76
  %".87" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".86", i32 0, i32 %".22" , !dbg !76
  %".88" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".87", i32 0, i32 6 , !dbg !76
  %".89" = trunc i64 0 to i32 , !dbg !76
  store i32 %".89", i32* %".88", !dbg !76
  %".91" = getelementptr [2 x i8], [2 x i8]* @".str.1", i64 0, i64 0 , !dbg !77
  %".92" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !77
  %".93" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".92", i32 0, i32 2 , !dbg !77
  %".94" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".93", i32 0, i32 %".22" , !dbg !77
  %".95" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".94", !dbg !77
  %".96" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !77
  %".97" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".96", i32 0, i32 2 , !dbg !77
  %".98" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".97", i32 0, i32 %".22" , !dbg !77
  %".99" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".98", i32 0, i32 7 , !dbg !77
  store i8* %".91", i8** %".99", !dbg !77
  %".101" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !78
  %".102" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".101", i32 0, i32 3 , !dbg !78
  %".103" = load i32, i32* %".102", !dbg !78
  %".104" = sext i32 %".103" to i64 , !dbg !78
  %".105" = add i64 %".104", 1, !dbg !78
  %".106" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !78
  %".107" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".106", i32 0, i32 3 , !dbg !78
  %".108" = trunc i64 %".105" to i32 , !dbg !78
  store i32 %".108", i32* %".107", !dbg !78
  ret i32 0, !dbg !78
}

define i32 @"args_option"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8 %"short.arg", i8* %"long.arg", i8* %"value_name.arg", i8* %"desc.arg", i8* %"default.arg") !dbg !19
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !79, metadata !7), !dbg !80
  %"short" = alloca i8
  store i8 %"short.arg", i8* %"short"
  call void @"llvm.dbg.declare"(metadata i8* %"short", metadata !81, metadata !7), !dbg !80
  %"long" = alloca i8*
  store i8* %"long.arg", i8** %"long"
  call void @"llvm.dbg.declare"(metadata i8** %"long", metadata !82, metadata !7), !dbg !80
  %"value_name" = alloca i8*
  store i8* %"value_name.arg", i8** %"value_name"
  call void @"llvm.dbg.declare"(metadata i8** %"value_name", metadata !83, metadata !7), !dbg !80
  %"desc" = alloca i8*
  store i8* %"desc.arg", i8** %"desc"
  call void @"llvm.dbg.declare"(metadata i8** %"desc", metadata !84, metadata !7), !dbg !80
  %"default" = alloca i8*
  store i8* %"default.arg", i8** %"default"
  call void @"llvm.dbg.declare"(metadata i8** %"default", metadata !85, metadata !7), !dbg !80
  %".20" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !86
  %".21" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".20", i32 0, i32 3 , !dbg !86
  %".22" = load i32, i32* %".21", !dbg !86
  %".23" = icmp sge i32 %".22", 32 , !dbg !86
  br i1 %".23", label %"if.then", label %"if.end", !dbg !86
if.then:
  ret i32 0, !dbg !87
if.end:
  %".26" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !88
  %".27" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".26", i32 0, i32 3 , !dbg !88
  %".28" = load i32, i32* %".27", !dbg !88
  %".29" = load i8, i8* %"short", !dbg !89
  %".30" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !89
  %".31" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".30", i32 0, i32 2 , !dbg !89
  %".32" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".31", i32 0, i32 %".28" , !dbg !89
  %".33" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".32", !dbg !89
  %".34" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !89
  %".35" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".34", i32 0, i32 2 , !dbg !89
  %".36" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".35", i32 0, i32 %".28" , !dbg !89
  %".37" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".36", i32 0, i32 0 , !dbg !89
  store i8 %".29", i8* %".37", !dbg !89
  %".39" = load i8*, i8** %"long", !dbg !90
  %".40" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !90
  %".41" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".40", i32 0, i32 2 , !dbg !90
  %".42" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".41", i32 0, i32 %".28" , !dbg !90
  %".43" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".42", !dbg !90
  %".44" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !90
  %".45" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".44", i32 0, i32 2 , !dbg !90
  %".46" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".45", i32 0, i32 %".28" , !dbg !90
  %".47" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".46", i32 0, i32 1 , !dbg !90
  store i8* %".39", i8** %".47", !dbg !90
  %".49" = load i8*, i8** %"value_name", !dbg !91
  %".50" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !91
  %".51" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".50", i32 0, i32 2 , !dbg !91
  %".52" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".51", i32 0, i32 %".28" , !dbg !91
  %".53" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".52", !dbg !91
  %".54" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !91
  %".55" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".54", i32 0, i32 2 , !dbg !91
  %".56" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".55", i32 0, i32 %".28" , !dbg !91
  %".57" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".56", i32 0, i32 2 , !dbg !91
  store i8* %".49", i8** %".57", !dbg !91
  %".59" = load i8*, i8** %"desc", !dbg !92
  %".60" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !92
  %".61" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".60", i32 0, i32 2 , !dbg !92
  %".62" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".61", i32 0, i32 %".28" , !dbg !92
  %".63" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".62", !dbg !92
  %".64" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !92
  %".65" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".64", i32 0, i32 2 , !dbg !92
  %".66" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".65", i32 0, i32 %".28" , !dbg !92
  %".67" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".66", i32 0, i32 3 , !dbg !92
  store i8* %".59", i8** %".67", !dbg !92
  %".69" = load i8*, i8** %"default", !dbg !93
  %".70" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !93
  %".71" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".70", i32 0, i32 2 , !dbg !93
  %".72" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".71", i32 0, i32 %".28" , !dbg !93
  %".73" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".72", !dbg !93
  %".74" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !93
  %".75" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".74", i32 0, i32 2 , !dbg !93
  %".76" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".75", i32 0, i32 %".28" , !dbg !93
  %".77" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".76", i32 0, i32 4 , !dbg !93
  store i8* %".69", i8** %".77", !dbg !93
  %".79" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !94
  %".80" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".79", i32 0, i32 2 , !dbg !94
  %".81" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".80", i32 0, i32 %".28" , !dbg !94
  %".82" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".81", !dbg !94
  %".83" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !94
  %".84" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".83", i32 0, i32 2 , !dbg !94
  %".85" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".84", i32 0, i32 %".28" , !dbg !94
  %".86" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".85", i32 0, i32 5 , !dbg !94
  store i32 1, i32* %".86", !dbg !94
  %".88" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !95
  %".89" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".88", i32 0, i32 2 , !dbg !95
  %".90" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".89", i32 0, i32 %".28" , !dbg !95
  %".91" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".90", !dbg !95
  %".92" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !95
  %".93" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".92", i32 0, i32 2 , !dbg !95
  %".94" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".93", i32 0, i32 %".28" , !dbg !95
  %".95" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".94", i32 0, i32 6 , !dbg !95
  %".96" = trunc i64 0 to i32 , !dbg !95
  store i32 %".96", i32* %".95", !dbg !95
  %".98" = load i8*, i8** %"default", !dbg !96
  %".99" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !96
  %".100" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".99", i32 0, i32 2 , !dbg !96
  %".101" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".100", i32 0, i32 %".28" , !dbg !96
  %".102" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".101", !dbg !96
  %".103" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !96
  %".104" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".103", i32 0, i32 2 , !dbg !96
  %".105" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".104", i32 0, i32 %".28" , !dbg !96
  %".106" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".105", i32 0, i32 7 , !dbg !96
  store i8* %".98", i8** %".106", !dbg !96
  %".108" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !97
  %".109" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".108", i32 0, i32 3 , !dbg !97
  %".110" = load i32, i32* %".109", !dbg !97
  %".111" = sext i32 %".110" to i64 , !dbg !97
  %".112" = add i64 %".111", 1, !dbg !97
  %".113" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !97
  %".114" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".113", i32 0, i32 3 , !dbg !97
  %".115" = trunc i64 %".112" to i32 , !dbg !97
  store i32 %".115", i32* %".114", !dbg !97
  ret i32 0, !dbg !97
}

define i32 @"args_positional"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8* %"name.arg", i8* %"desc.arg", i32 %"min.arg", i32 %"max.arg") !dbg !20
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !98, metadata !7), !dbg !99
  %"name" = alloca i8*
  store i8* %"name.arg", i8** %"name"
  call void @"llvm.dbg.declare"(metadata i8** %"name", metadata !100, metadata !7), !dbg !99
  %"desc" = alloca i8*
  store i8* %"desc.arg", i8** %"desc"
  call void @"llvm.dbg.declare"(metadata i8** %"desc", metadata !101, metadata !7), !dbg !99
  %"min" = alloca i32
  store i32 %"min.arg", i32* %"min"
  call void @"llvm.dbg.declare"(metadata i32* %"min", metadata !102, metadata !7), !dbg !99
  %"max" = alloca i32
  store i32 %"max.arg", i32* %"max"
  call void @"llvm.dbg.declare"(metadata i32* %"max", metadata !103, metadata !7), !dbg !99
  %".17" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !104
  %".18" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".17", i32 0, i32 5 , !dbg !104
  %".19" = load i32, i32* %".18", !dbg !104
  %".20" = sext i32 %".19" to i64 , !dbg !104
  %".21" = icmp sge i64 %".20", 8 , !dbg !104
  br i1 %".21", label %"if.then", label %"if.end", !dbg !104
if.then:
  ret i32 0, !dbg !105
if.end:
  %".24" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !106
  %".25" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".24", i32 0, i32 5 , !dbg !106
  %".26" = load i32, i32* %".25", !dbg !106
  %".27" = load i8*, i8** %"name", !dbg !107
  %".28" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !107
  %".29" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".28", i32 0, i32 4 , !dbg !107
  %".30" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".29", i32 0, i32 %".26" , !dbg !107
  %".31" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".30", !dbg !107
  %".32" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !107
  %".33" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".32", i32 0, i32 4 , !dbg !107
  %".34" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".33", i32 0, i32 %".26" , !dbg !107
  %".35" = getelementptr %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".34", i32 0, i32 0 , !dbg !107
  store i8* %".27", i8** %".35", !dbg !107
  %".37" = load i8*, i8** %"desc", !dbg !108
  %".38" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !108
  %".39" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".38", i32 0, i32 4 , !dbg !108
  %".40" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".39", i32 0, i32 %".26" , !dbg !108
  %".41" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".40", !dbg !108
  %".42" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !108
  %".43" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".42", i32 0, i32 4 , !dbg !108
  %".44" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".43", i32 0, i32 %".26" , !dbg !108
  %".45" = getelementptr %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".44", i32 0, i32 1 , !dbg !108
  store i8* %".37", i8** %".45", !dbg !108
  %".47" = load i32, i32* %"min", !dbg !109
  %".48" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !109
  %".49" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".48", i32 0, i32 4 , !dbg !109
  %".50" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".49", i32 0, i32 %".26" , !dbg !109
  %".51" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".50", !dbg !109
  %".52" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !109
  %".53" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".52", i32 0, i32 4 , !dbg !109
  %".54" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".53", i32 0, i32 %".26" , !dbg !109
  %".55" = getelementptr %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".54", i32 0, i32 2 , !dbg !109
  store i32 %".47", i32* %".55", !dbg !109
  %".57" = load i32, i32* %"max", !dbg !110
  %".58" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !110
  %".59" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".58", i32 0, i32 4 , !dbg !110
  %".60" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".59", i32 0, i32 %".26" , !dbg !110
  %".61" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".60", !dbg !110
  %".62" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !110
  %".63" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".62", i32 0, i32 4 , !dbg !110
  %".64" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".63", i32 0, i32 %".26" , !dbg !110
  %".65" = getelementptr %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".64", i32 0, i32 3 , !dbg !110
  store i32 %".57", i32* %".65", !dbg !110
  %".67" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !111
  %".68" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".67", i32 0, i32 5 , !dbg !111
  %".69" = load i32, i32* %".68", !dbg !111
  %".70" = sext i32 %".69" to i64 , !dbg !111
  %".71" = add i64 %".70", 1, !dbg !111
  %".72" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !111
  %".73" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".72", i32 0, i32 5 , !dbg !111
  %".74" = trunc i64 %".71" to i32 , !dbg !111
  store i32 %".74", i32* %".73", !dbg !111
  ret i32 0, !dbg !111
}

define i32 @"find_option_short"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8 %"short.arg") !dbg !21
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  %"i" = alloca i32, !dbg !115
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !112, metadata !7), !dbg !113
  %"short" = alloca i8
  store i8 %"short.arg", i8* %"short"
  call void @"llvm.dbg.declare"(metadata i8* %"short", metadata !114, metadata !7), !dbg !113
  %".8" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !115
  %".9" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".8", i32 0, i32 3 , !dbg !115
  %".10" = load i32, i32* %".9", !dbg !115
  store i32 0, i32* %"i", !dbg !115
  br label %"for.cond", !dbg !115
for.cond:
  %".13" = load i32, i32* %"i", !dbg !115
  %".14" = icmp slt i32 %".13", %".10" , !dbg !115
  br i1 %".14", label %"for.body", label %"for.end", !dbg !115
for.body:
  %".16" = load i32, i32* %"i", !dbg !115
  %".17" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !115
  %".18" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".17", i32 0, i32 2 , !dbg !115
  %".19" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".18", i32 0, i32 %".16" , !dbg !115
  %".20" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".19", !dbg !115
  %".21" = extractvalue %"struct.ritz_module_1.OptDef" %".20", 0 , !dbg !115
  %".22" = load i8, i8* %"short", !dbg !115
  %".23" = icmp eq i8 %".21", %".22" , !dbg !115
  br i1 %".23", label %"if.then", label %"if.end", !dbg !115
for.incr:
  %".28" = load i32, i32* %"i", !dbg !116
  %".29" = add i32 %".28", 1, !dbg !116
  store i32 %".29", i32* %"i", !dbg !116
  br label %"for.cond", !dbg !116
for.end:
  %".32" = sub i64 0, 1, !dbg !117
  %".33" = trunc i64 %".32" to i32 , !dbg !117
  ret i32 %".33", !dbg !117
if.then:
  %".25" = load i32, i32* %"i", !dbg !116
  ret i32 %".25", !dbg !116
if.end:
  br label %"for.incr", !dbg !116
}

define i32 @"find_option_long"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8* %"long.arg") !dbg !22
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  %"i" = alloca i32, !dbg !121
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !118, metadata !7), !dbg !119
  %"long" = alloca i8*
  store i8* %"long.arg", i8** %"long"
  call void @"llvm.dbg.declare"(metadata i8** %"long", metadata !120, metadata !7), !dbg !119
  %".8" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !121
  %".9" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".8", i32 0, i32 3 , !dbg !121
  %".10" = load i32, i32* %".9", !dbg !121
  store i32 0, i32* %"i", !dbg !121
  br label %"for.cond", !dbg !121
for.cond:
  %".13" = load i32, i32* %"i", !dbg !121
  %".14" = icmp slt i32 %".13", %".10" , !dbg !121
  br i1 %".14", label %"for.body", label %"for.end", !dbg !121
for.body:
  %".16" = load i32, i32* %"i", !dbg !121
  %".17" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !121
  %".18" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".17", i32 0, i32 2 , !dbg !121
  %".19" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".18", i32 0, i32 %".16" , !dbg !121
  %".20" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".19", !dbg !121
  %".21" = extractvalue %"struct.ritz_module_1.OptDef" %".20", 1 , !dbg !121
  %".22" = icmp ne i8* %".21", null , !dbg !121
  br i1 %".22", label %"if.then", label %"if.end", !dbg !121
for.incr:
  %".39" = load i32, i32* %"i", !dbg !122
  %".40" = add i32 %".39", 1, !dbg !122
  store i32 %".40", i32* %"i", !dbg !122
  br label %"for.cond", !dbg !122
for.end:
  %".43" = sub i64 0, 1, !dbg !123
  %".44" = trunc i64 %".43" to i32 , !dbg !123
  ret i32 %".44", !dbg !123
if.then:
  %".24" = load i32, i32* %"i", !dbg !121
  %".25" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !121
  %".26" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".25", i32 0, i32 2 , !dbg !121
  %".27" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".26", i32 0, i32 %".24" , !dbg !121
  %".28" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".27", !dbg !121
  %".29" = extractvalue %"struct.ritz_module_1.OptDef" %".28", 1 , !dbg !121
  %".30" = load i8*, i8** %"long", !dbg !121
  %".31" = call i32 @"streq"(i8* %".29", i8* %".30"), !dbg !121
  %".32" = sext i32 %".31" to i64 , !dbg !121
  %".33" = icmp ne i64 %".32", 0 , !dbg !121
  br i1 %".33", label %"if.then.1", label %"if.end.1", !dbg !121
if.end:
  br label %"for.incr", !dbg !122
if.then.1:
  %".35" = load i32, i32* %"i", !dbg !122
  ret i32 %".35", !dbg !122
if.end.1:
  br label %"if.end", !dbg !122
}

define i32 @"args_parse"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i32 %"argc.arg", i8** %"argv.arg") !dbg !23
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  %"i.addr" = alloca i32, !dbg !129
  %"stop_options.addr" = alloca i32, !dbg !132
  %"eq_pos.addr" = alloca i64, !dbg !143
  %"j.addr" = alloca i64, !dbg !146
  %"opt_name.addr" = alloca [64 x i8], !dbg !155
  %"k.addr" = alloca i64, !dbg !161
  %"j.addr.1" = alloca i32, !dbg !204
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !124, metadata !7), !dbg !125
  %"argc" = alloca i32
  store i32 %"argc.arg", i32* %"argc"
  call void @"llvm.dbg.declare"(metadata i32* %"argc", metadata !126, metadata !7), !dbg !125
  %"argv" = alloca i8**
  store i8** %"argv.arg", i8*** %"argv"
  call void @"llvm.dbg.declare"(metadata i8*** %"argv", metadata !128, metadata !7), !dbg !125
  %".11" = trunc i64 1 to i32 , !dbg !129
  store i32 %".11", i32* %"i.addr", !dbg !129
  call void @"llvm.dbg.declare"(metadata i32* %"i.addr", metadata !130, metadata !7), !dbg !131
  %".14" = trunc i64 0 to i32 , !dbg !132
  store i32 %".14", i32* %"stop_options.addr", !dbg !132
  call void @"llvm.dbg.declare"(metadata i32* %"stop_options.addr", metadata !133, metadata !7), !dbg !134
  br label %"while.cond", !dbg !135
while.cond:
  %".18" = load i32, i32* %"i.addr", !dbg !135
  %".19" = load i32, i32* %"argc", !dbg !135
  %".20" = icmp slt i32 %".18", %".19" , !dbg !135
  br i1 %".20", label %"while.body", label %"while.end", !dbg !135
while.body:
  %".22" = load i8**, i8*** %"argv", !dbg !136
  %".23" = load i32, i32* %"i.addr", !dbg !136
  %".24" = getelementptr i8*, i8** %".22", i32 %".23" , !dbg !136
  %".25" = load i8*, i8** %".24", !dbg !136
  %".26" = load i32, i32* %"stop_options.addr", !dbg !137
  %".27" = sext i32 %".26" to i64 , !dbg !137
  %".28" = icmp eq i64 %".27", 0 , !dbg !137
  br i1 %".28", label %"and.right", label %"and.merge", !dbg !137
while.end:
  %".481" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !238
  %".482" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".481", i32 0, i32 5 , !dbg !238
  %".483" = load i32, i32* %".482", !dbg !238
  %".484" = sext i32 %".483" to i64 , !dbg !238
  %".485" = icmp sgt i64 %".484", 0 , !dbg !238
  br i1 %".485", label %"if.then.15", label %"if.end.15", !dbg !238
and.right:
  %".30" = getelementptr [3 x i8], [3 x i8]* @".str.2", i64 0, i64 0 , !dbg !137
  %".31" = call i32 @"streq"(i8* %".25", i8* %".30"), !dbg !137
  %".32" = sext i32 %".31" to i64 , !dbg !137
  %".33" = icmp ne i64 %".32", 0 , !dbg !137
  br label %"and.merge", !dbg !137
and.merge:
  %".35" = phi  i1 [0, %"while.body"], [%".33", %"and.right"] , !dbg !137
  br i1 %".35", label %"if.then", label %"if.end", !dbg !137
if.then:
  %".37" = trunc i64 1 to i32 , !dbg !138
  store i32 %".37", i32* %"stop_options.addr", !dbg !138
  %".39" = load i32, i32* %"i.addr", !dbg !139
  %".40" = sext i32 %".39" to i64 , !dbg !139
  %".41" = add i64 %".40", 1, !dbg !139
  %".42" = trunc i64 %".41" to i32 , !dbg !139
  store i32 %".42", i32* %"i.addr", !dbg !139
  br label %"while.cond", !dbg !140
if.end:
  %".45" = load i32, i32* %"stop_options.addr", !dbg !141
  %".46" = sext i32 %".45" to i64 , !dbg !141
  %".47" = icmp eq i64 %".46", 0 , !dbg !141
  br i1 %".47", label %"and.right.1", label %"and.merge.1", !dbg !141
and.right.1:
  %".49" = load i8, i8* %".25", !dbg !141
  %".50" = icmp eq i8 %".49", 45 , !dbg !141
  br label %"and.merge.1", !dbg !141
and.merge.1:
  %".52" = phi  i1 [0, %"if.end"], [%".50", %"and.right.1"] , !dbg !141
  br i1 %".52", label %"and.right.2", label %"and.merge.2", !dbg !141
and.right.2:
  %".54" = getelementptr i8, i8* %".25", i64 1 , !dbg !141
  %".55" = load i8, i8* %".54", !dbg !141
  %".56" = icmp eq i8 %".55", 45 , !dbg !141
  br label %"and.merge.2", !dbg !141
and.merge.2:
  %".58" = phi  i1 [0, %"and.merge.1"], [%".56", %"and.right.2"] , !dbg !141
  br i1 %".58", label %"if.then.1", label %"if.end.1", !dbg !141
if.then.1:
  %".60" = getelementptr i8, i8* %".25", i64 2 , !dbg !142
  store i64 0, i64* %"eq_pos.addr", !dbg !143
  call void @"llvm.dbg.declare"(metadata i64* %"eq_pos.addr", metadata !144, metadata !7), !dbg !145
  store i64 0, i64* %"j.addr", !dbg !146
  call void @"llvm.dbg.declare"(metadata i64* %"j.addr", metadata !147, metadata !7), !dbg !148
  br label %"while.cond.1", !dbg !149
if.end.1:
  %".285" = load i32, i32* %"stop_options.addr", !dbg !203
  %".286" = sext i32 %".285" to i64 , !dbg !203
  %".287" = icmp eq i64 %".286", 0 , !dbg !203
  br i1 %".287", label %"and.right.4", label %"and.merge.4", !dbg !203
while.cond.1:
  %".66" = load i64, i64* %"j.addr", !dbg !149
  %".67" = getelementptr i8, i8* %".60", i64 %".66" , !dbg !149
  %".68" = load i8, i8* %".67", !dbg !149
  %".69" = zext i8 %".68" to i64 , !dbg !149
  %".70" = icmp ne i64 %".69", 0 , !dbg !149
  br i1 %".70", label %"while.body.1", label %"while.end.1", !dbg !149
while.body.1:
  %".72" = load i64, i64* %"j.addr", !dbg !150
  %".73" = getelementptr i8, i8* %".60", i64 %".72" , !dbg !150
  %".74" = load i8, i8* %".73", !dbg !150
  %".75" = icmp eq i8 %".74", 61 , !dbg !150
  br i1 %".75", label %"if.then.2", label %"if.end.2", !dbg !150
while.end.1:
  %".84" = load i64, i64* %"eq_pos.addr", !dbg !154
  %".85" = icmp sgt i64 %".84", 0 , !dbg !154
  br i1 %".85", label %"if.then.3", label %"if.else", !dbg !154
if.then.2:
  %".77" = load i64, i64* %"j.addr", !dbg !151
  store i64 %".77", i64* %"eq_pos.addr", !dbg !151
  br label %"while.end.1", !dbg !152
if.end.2:
  %".80" = load i64, i64* %"j.addr", !dbg !153
  %".81" = add i64 %".80", 1, !dbg !153
  store i64 %".81", i64* %"j.addr", !dbg !153
  br label %"while.cond.1", !dbg !153
if.then.3:
  call void @"llvm.dbg.declare"(metadata [64 x i8]* %"opt_name.addr", metadata !159, metadata !7), !dbg !160
  store i64 0, i64* %"k.addr", !dbg !161
  call void @"llvm.dbg.declare"(metadata i64* %"k.addr", metadata !162, metadata !7), !dbg !163
  br label %"while.cond.2", !dbg !164
if.else:
  %".181" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !183
  %".182" = call i32 @"find_option_long"(%"struct.ritz_module_1.ArgParser"* %".181", i8* %".60"), !dbg !183
  %".183" = sext i32 %".182" to i64 , !dbg !184
  %".184" = icmp slt i64 %".183", 0 , !dbg !184
  br i1 %".184", label %"if.then.6", label %"if.end.6", !dbg !184
if.end.3:
  %".279" = load i32, i32* %"i.addr", !dbg !201
  %".280" = sext i32 %".279" to i64 , !dbg !201
  %".281" = add i64 %".280", 1, !dbg !201
  %".282" = trunc i64 %".281" to i32 , !dbg !201
  store i32 %".282", i32* %"i.addr", !dbg !201
  br label %"while.cond", !dbg !202
while.cond.2:
  %".91" = load i64, i64* %"k.addr", !dbg !164
  %".92" = load i64, i64* %"eq_pos.addr", !dbg !164
  %".93" = icmp slt i64 %".91", %".92" , !dbg !164
  br i1 %".93", label %"and.right.3", label %"and.merge.3", !dbg !164
while.body.2:
  %".100" = load i64, i64* %"k.addr", !dbg !165
  %".101" = getelementptr i8, i8* %".60", i64 %".100" , !dbg !165
  %".102" = load i8, i8* %".101", !dbg !165
  %".103" = load i64, i64* %"k.addr", !dbg !165
  %".104" = getelementptr [64 x i8], [64 x i8]* %"opt_name.addr", i32 0, i64 %".103" , !dbg !165
  store i8 %".102", i8* %".104", !dbg !165
  %".106" = load i64, i64* %"k.addr", !dbg !166
  %".107" = add i64 %".106", 1, !dbg !166
  store i64 %".107", i64* %"k.addr", !dbg !166
  br label %"while.cond.2", !dbg !166
while.end.2:
  %".110" = load i64, i64* %"k.addr", !dbg !167
  %".111" = getelementptr [64 x i8], [64 x i8]* %"opt_name.addr", i32 0, i64 %".110" , !dbg !167
  %".112" = trunc i64 0 to i8 , !dbg !167
  store i8 %".112", i8* %".111", !dbg !167
  %".114" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !168
  %".115" = getelementptr [64 x i8], [64 x i8]* %"opt_name.addr", i32 0, i64 0 , !dbg !168
  %".116" = call i32 @"find_option_long"(%"struct.ritz_module_1.ArgParser"* %".114", i8* %".115"), !dbg !168
  %".117" = sext i32 %".116" to i64 , !dbg !169
  %".118" = icmp slt i64 %".117", 0 , !dbg !169
  br i1 %".118", label %"if.then.4", label %"if.end.4", !dbg !169
and.right.3:
  %".95" = load i64, i64* %"k.addr", !dbg !164
  %".96" = icmp slt i64 %".95", 63 , !dbg !164
  br label %"and.merge.3", !dbg !164
and.merge.3:
  %".98" = phi  i1 [0, %"while.cond.2"], [%".96", %"and.right.3"] , !dbg !164
  br i1 %".98", label %"while.body.2", label %"while.end.2", !dbg !164
if.then.4:
  %".120" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !170
  %".121" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".120", i32 0, i32 0 , !dbg !170
  %".122" = load i8*, i8** %".121", !dbg !170
  %".123" = call i32 @"eprints_cstr"(i8* %".122"), !dbg !170
  %".124" = getelementptr [21 x i8], [21 x i8]* @".str.3", i64 0, i64 0 , !dbg !171
  %".125" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".124", 0 , !dbg !171
  %".126" = insertvalue %"struct.ritz_module_1.StrView" %".125", i64 20, 1 , !dbg !171
  %".127" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".126"), !dbg !171
  %".128" = getelementptr [64 x i8], [64 x i8]* %"opt_name.addr", i32 0, i64 0 , !dbg !172
  %".129" = call i32 @"eprints_cstr"(i8* %".128"), !dbg !172
  %".130" = getelementptr [3 x i8], [3 x i8]* @".str.4", i64 0, i64 0 , !dbg !173
  %".131" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".130", 0 , !dbg !173
  %".132" = insertvalue %"struct.ritz_module_1.StrView" %".131", i64 2, 1 , !dbg !173
  %".133" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".132"), !dbg !173
  %".134" = trunc i64 1 to i32 , !dbg !174
  ret i32 %".134", !dbg !174
if.end.4:
  %".136" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !175
  %".137" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".136", i32 0, i32 2 , !dbg !175
  %".138" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".137", i32 0, i32 %".116" , !dbg !175
  %".139" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".138", !dbg !175
  %".140" = extractvalue %"struct.ritz_module_1.OptDef" %".139", 5 , !dbg !175
  %".141" = icmp eq i32 %".140", 0 , !dbg !175
  br i1 %".141", label %"if.then.5", label %"if.end.5", !dbg !175
if.then.5:
  %".143" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !176
  %".144" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".143", i32 0, i32 0 , !dbg !176
  %".145" = load i8*, i8** %".144", !dbg !176
  %".146" = call i32 @"eprints_cstr"(i8* %".145"), !dbg !176
  %".147" = getelementptr [13 x i8], [13 x i8]* @".str.5", i64 0, i64 0 , !dbg !177
  %".148" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".147", 0 , !dbg !177
  %".149" = insertvalue %"struct.ritz_module_1.StrView" %".148", i64 12, 1 , !dbg !177
  %".150" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".149"), !dbg !177
  %".151" = getelementptr [64 x i8], [64 x i8]* %"opt_name.addr", i32 0, i64 0 , !dbg !178
  %".152" = call i32 @"eprints_cstr"(i8* %".151"), !dbg !178
  %".153" = getelementptr [26 x i8], [26 x i8]* @".str.6", i64 0, i64 0 , !dbg !179
  %".154" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".153", 0 , !dbg !179
  %".155" = insertvalue %"struct.ritz_module_1.StrView" %".154", i64 25, 1 , !dbg !179
  %".156" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".155"), !dbg !179
  %".157" = trunc i64 1 to i32 , !dbg !180
  ret i32 %".157", !dbg !180
if.end.5:
  %".159" = load i64, i64* %"eq_pos.addr", !dbg !181
  %".160" = getelementptr i8, i8* %".60", i64 %".159" , !dbg !181
  %".161" = getelementptr i8, i8* %".160", i64 1 , !dbg !181
  %".162" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !181
  %".163" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".162", i32 0, i32 2 , !dbg !181
  %".164" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".163", i32 0, i32 %".116" , !dbg !181
  %".165" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".164", !dbg !181
  %".166" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !181
  %".167" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".166", i32 0, i32 2 , !dbg !181
  %".168" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".167", i32 0, i32 %".116" , !dbg !181
  %".169" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".168", i32 0, i32 7 , !dbg !181
  store i8* %".161", i8** %".169", !dbg !181
  %".171" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !182
  %".172" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".171", i32 0, i32 2 , !dbg !182
  %".173" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".172", i32 0, i32 %".116" , !dbg !182
  %".174" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".173", !dbg !182
  %".175" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !182
  %".176" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".175", i32 0, i32 2 , !dbg !182
  %".177" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".176", i32 0, i32 %".116" , !dbg !182
  %".178" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".177", i32 0, i32 6 , !dbg !182
  %".179" = trunc i64 1 to i32 , !dbg !182
  store i32 %".179", i32* %".178", !dbg !182
  br label %"if.end.3", !dbg !200
if.then.6:
  %".186" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !185
  %".187" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".186", i32 0, i32 0 , !dbg !185
  %".188" = load i8*, i8** %".187", !dbg !185
  %".189" = call i32 @"eprints_cstr"(i8* %".188"), !dbg !185
  %".190" = getelementptr [21 x i8], [21 x i8]* @".str.7", i64 0, i64 0 , !dbg !186
  %".191" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".190", 0 , !dbg !186
  %".192" = insertvalue %"struct.ritz_module_1.StrView" %".191", i64 20, 1 , !dbg !186
  %".193" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".192"), !dbg !186
  %".194" = call i32 @"eprints_cstr"(i8* %".60"), !dbg !187
  %".195" = getelementptr [3 x i8], [3 x i8]* @".str.8", i64 0, i64 0 , !dbg !188
  %".196" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".195", 0 , !dbg !188
  %".197" = insertvalue %"struct.ritz_module_1.StrView" %".196", i64 2, 1 , !dbg !188
  %".198" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".197"), !dbg !188
  %".199" = trunc i64 1 to i32 , !dbg !189
  ret i32 %".199", !dbg !189
if.end.6:
  %".201" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !189
  %".202" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".201", i32 0, i32 2 , !dbg !189
  %".203" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".202", i32 0, i32 %".182" , !dbg !189
  %".204" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".203", !dbg !189
  %".205" = extractvalue %"struct.ritz_module_1.OptDef" %".204", 5 , !dbg !189
  %".206" = icmp eq i32 %".205", 0 , !dbg !189
  br i1 %".206", label %"if.then.7", label %"if.else.1", !dbg !189
if.then.7:
  %".208" = getelementptr [2 x i8], [2 x i8]* @".str.9", i64 0, i64 0 , !dbg !190
  %".209" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !190
  %".210" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".209", i32 0, i32 2 , !dbg !190
  %".211" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".210", i32 0, i32 %".182" , !dbg !190
  %".212" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".211", !dbg !190
  %".213" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !190
  %".214" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".213", i32 0, i32 2 , !dbg !190
  %".215" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".214", i32 0, i32 %".182" , !dbg !190
  %".216" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".215", i32 0, i32 7 , !dbg !190
  store i8* %".208", i8** %".216", !dbg !190
  %".218" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !191
  %".219" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".218", i32 0, i32 2 , !dbg !191
  %".220" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".219", i32 0, i32 %".182" , !dbg !191
  %".221" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".220", !dbg !191
  %".222" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !191
  %".223" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".222", i32 0, i32 2 , !dbg !191
  %".224" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".223", i32 0, i32 %".182" , !dbg !191
  %".225" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".224", i32 0, i32 6 , !dbg !191
  %".226" = trunc i64 1 to i32 , !dbg !191
  store i32 %".226", i32* %".225", !dbg !191
  br label %"if.end.7", !dbg !200
if.else.1:
  %".228" = load i32, i32* %"i.addr", !dbg !192
  %".229" = sext i32 %".228" to i64 , !dbg !192
  %".230" = add i64 %".229", 1, !dbg !192
  %".231" = trunc i64 %".230" to i32 , !dbg !192
  store i32 %".231", i32* %"i.addr", !dbg !192
  %".233" = load i32, i32* %"i.addr", !dbg !193
  %".234" = load i32, i32* %"argc", !dbg !193
  %".235" = icmp sge i32 %".233", %".234" , !dbg !193
  br i1 %".235", label %"if.then.8", label %"if.end.8", !dbg !193
if.end.7:
  br label %"if.end.3", !dbg !200
if.then.8:
  %".237" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !194
  %".238" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".237", i32 0, i32 0 , !dbg !194
  %".239" = load i8*, i8** %".238", !dbg !194
  %".240" = call i32 @"eprints_cstr"(i8* %".239"), !dbg !194
  %".241" = getelementptr [13 x i8], [13 x i8]* @".str.10", i64 0, i64 0 , !dbg !195
  %".242" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".241", 0 , !dbg !195
  %".243" = insertvalue %"struct.ritz_module_1.StrView" %".242", i64 12, 1 , !dbg !195
  %".244" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".243"), !dbg !195
  %".245" = call i32 @"eprints_cstr"(i8* %".60"), !dbg !196
  %".246" = getelementptr [20 x i8], [20 x i8]* @".str.11", i64 0, i64 0 , !dbg !197
  %".247" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".246", 0 , !dbg !197
  %".248" = insertvalue %"struct.ritz_module_1.StrView" %".247", i64 19, 1 , !dbg !197
  %".249" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".248"), !dbg !197
  %".250" = trunc i64 1 to i32 , !dbg !198
  ret i32 %".250", !dbg !198
if.end.8:
  %".252" = load i8**, i8*** %"argv", !dbg !199
  %".253" = load i32, i32* %"i.addr", !dbg !199
  %".254" = getelementptr i8*, i8** %".252", i32 %".253" , !dbg !199
  %".255" = load i8*, i8** %".254", !dbg !199
  %".256" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !199
  %".257" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".256", i32 0, i32 2 , !dbg !199
  %".258" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".257", i32 0, i32 %".182" , !dbg !199
  %".259" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".258", !dbg !199
  %".260" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !199
  %".261" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".260", i32 0, i32 2 , !dbg !199
  %".262" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".261", i32 0, i32 %".182" , !dbg !199
  %".263" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".262", i32 0, i32 7 , !dbg !199
  store i8* %".255", i8** %".263", !dbg !199
  %".265" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !200
  %".266" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".265", i32 0, i32 2 , !dbg !200
  %".267" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".266", i32 0, i32 %".182" , !dbg !200
  %".268" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".267", !dbg !200
  %".269" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !200
  %".270" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".269", i32 0, i32 2 , !dbg !200
  %".271" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".270", i32 0, i32 %".182" , !dbg !200
  %".272" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".271", i32 0, i32 6 , !dbg !200
  %".273" = trunc i64 1 to i32 , !dbg !200
  store i32 %".273", i32* %".272", !dbg !200
  br label %"if.end.7", !dbg !200
and.right.4:
  %".289" = load i8, i8* %".25", !dbg !203
  %".290" = icmp eq i8 %".289", 45 , !dbg !203
  br label %"and.merge.4", !dbg !203
and.merge.4:
  %".292" = phi  i1 [0, %"if.end.1"], [%".290", %"and.right.4"] , !dbg !203
  br i1 %".292", label %"and.right.5", label %"and.merge.5", !dbg !203
and.right.5:
  %".294" = getelementptr i8, i8* %".25", i64 1 , !dbg !203
  %".295" = load i8, i8* %".294", !dbg !203
  %".296" = zext i8 %".295" to i64 , !dbg !203
  %".297" = icmp ne i64 %".296", 0 , !dbg !203
  br label %"and.merge.5", !dbg !203
and.merge.5:
  %".299" = phi  i1 [0, %"and.merge.4"], [%".297", %"and.right.5"] , !dbg !203
  br i1 %".299", label %"if.then.9", label %"if.end.9", !dbg !203
if.then.9:
  %".301" = trunc i64 1 to i32 , !dbg !204
  store i32 %".301", i32* %"j.addr.1", !dbg !204
  call void @"llvm.dbg.declare"(metadata i32* %"j.addr.1", metadata !205, metadata !7), !dbg !206
  br label %"while.cond.3", !dbg !207
if.end.9:
  %".453" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !234
  %".454" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".453", i32 0, i32 7 , !dbg !234
  %".455" = load i32, i32* %".454", !dbg !234
  %".456" = icmp slt i32 %".455", 256 , !dbg !234
  br i1 %".456", label %"if.then.14", label %"if.end.14", !dbg !234
while.cond.3:
  %".305" = load i32, i32* %"j.addr.1", !dbg !207
  %".306" = getelementptr i8, i8* %".25", i32 %".305" , !dbg !207
  %".307" = load i8, i8* %".306", !dbg !207
  %".308" = zext i8 %".307" to i64 , !dbg !207
  %".309" = icmp ne i64 %".308", 0 , !dbg !207
  br i1 %".309", label %"while.body.3", label %"while.end.3", !dbg !207
while.body.3:
  %".311" = load i32, i32* %"j.addr.1", !dbg !208
  %".312" = getelementptr i8, i8* %".25", i32 %".311" , !dbg !208
  %".313" = load i8, i8* %".312", !dbg !208
  %".314" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !209
  %".315" = call i32 @"find_option_short"(%"struct.ritz_module_1.ArgParser"* %".314", i8 %".313"), !dbg !209
  %".316" = sext i32 %".315" to i64 , !dbg !210
  %".317" = icmp slt i64 %".316", 0 , !dbg !210
  br i1 %".317", label %"if.then.10", label %"if.end.10", !dbg !210
while.end.3:
  %".447" = load i32, i32* %"i.addr", !dbg !232
  %".448" = sext i32 %".447" to i64 , !dbg !232
  %".449" = add i64 %".448", 1, !dbg !232
  %".450" = trunc i64 %".449" to i32 , !dbg !232
  store i32 %".450", i32* %"i.addr", !dbg !232
  br label %"while.cond", !dbg !233
if.then.10:
  %".319" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !211
  %".320" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".319", i32 0, i32 0 , !dbg !211
  %".321" = load i8*, i8** %".320", !dbg !211
  %".322" = call i32 @"eprints_cstr"(i8* %".321"), !dbg !211
  %".323" = getelementptr [20 x i8], [20 x i8]* @".str.12", i64 0, i64 0 , !dbg !212
  %".324" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".323", 0 , !dbg !212
  %".325" = insertvalue %"struct.ritz_module_1.StrView" %".324", i64 19, 1 , !dbg !212
  %".326" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".325"), !dbg !212
  %".327" = call i32 @"print_char"(i8 %".313"), !dbg !213
  %".328" = getelementptr [3 x i8], [3 x i8]* @".str.13", i64 0, i64 0 , !dbg !214
  %".329" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".328", 0 , !dbg !214
  %".330" = insertvalue %"struct.ritz_module_1.StrView" %".329", i64 2, 1 , !dbg !214
  %".331" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".330"), !dbg !214
  %".332" = trunc i64 1 to i32 , !dbg !215
  ret i32 %".332", !dbg !215
if.end.10:
  %".334" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !215
  %".335" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".334", i32 0, i32 2 , !dbg !215
  %".336" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".335", i32 0, i32 %".315" , !dbg !215
  %".337" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".336", !dbg !215
  %".338" = extractvalue %"struct.ritz_module_1.OptDef" %".337", 5 , !dbg !215
  %".339" = icmp eq i32 %".338", 0 , !dbg !215
  br i1 %".339", label %"if.then.11", label %"if.else.2", !dbg !215
if.then.11:
  %".341" = getelementptr [2 x i8], [2 x i8]* @".str.14", i64 0, i64 0 , !dbg !216
  %".342" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !216
  %".343" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".342", i32 0, i32 2 , !dbg !216
  %".344" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".343", i32 0, i32 %".315" , !dbg !216
  %".345" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".344", !dbg !216
  %".346" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !216
  %".347" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".346", i32 0, i32 2 , !dbg !216
  %".348" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".347", i32 0, i32 %".315" , !dbg !216
  %".349" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".348", i32 0, i32 7 , !dbg !216
  store i8* %".341", i8** %".349", !dbg !216
  %".351" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !217
  %".352" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".351", i32 0, i32 2 , !dbg !217
  %".353" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".352", i32 0, i32 %".315" , !dbg !217
  %".354" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".353", !dbg !217
  %".355" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !217
  %".356" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".355", i32 0, i32 2 , !dbg !217
  %".357" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".356", i32 0, i32 %".315" , !dbg !217
  %".358" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".357", i32 0, i32 6 , !dbg !217
  %".359" = trunc i64 1 to i32 , !dbg !217
  store i32 %".359", i32* %".358", !dbg !217
  %".361" = load i32, i32* %"j.addr.1", !dbg !218
  %".362" = sext i32 %".361" to i64 , !dbg !218
  %".363" = add i64 %".362", 1, !dbg !218
  %".364" = trunc i64 %".363" to i32 , !dbg !218
  store i32 %".364", i32* %"j.addr.1", !dbg !218
  br label %"if.end.11", !dbg !231
if.else.2:
  %".366" = load i32, i32* %"j.addr.1", !dbg !218
  %".367" = getelementptr i8, i8* %".25", i32 %".366" , !dbg !218
  %".368" = getelementptr i8, i8* %".367", i64 1 , !dbg !218
  %".369" = load i8, i8* %".368", !dbg !218
  %".370" = sext i8 %".369" to i64 , !dbg !218
  %".371" = icmp ne i64 %".370", 0 , !dbg !218
  br i1 %".371", label %"if.then.12", label %"if.else.3", !dbg !218
if.end.11:
  br label %"while.cond.3", !dbg !231
if.then.12:
  %".373" = load i32, i32* %"j.addr.1", !dbg !219
  %".374" = getelementptr i8, i8* %".25", i32 %".373" , !dbg !219
  %".375" = getelementptr i8, i8* %".374", i64 1 , !dbg !219
  %".376" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !219
  %".377" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".376", i32 0, i32 2 , !dbg !219
  %".378" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".377", i32 0, i32 %".315" , !dbg !219
  %".379" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".378", !dbg !219
  %".380" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !219
  %".381" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".380", i32 0, i32 2 , !dbg !219
  %".382" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".381", i32 0, i32 %".315" , !dbg !219
  %".383" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".382", i32 0, i32 7 , !dbg !219
  store i8* %".375", i8** %".383", !dbg !219
  %".385" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !220
  %".386" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".385", i32 0, i32 2 , !dbg !220
  %".387" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".386", i32 0, i32 %".315" , !dbg !220
  %".388" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".387", !dbg !220
  %".389" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !220
  %".390" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".389", i32 0, i32 2 , !dbg !220
  %".391" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".390", i32 0, i32 %".315" , !dbg !220
  %".392" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".391", i32 0, i32 6 , !dbg !220
  %".393" = trunc i64 1 to i32 , !dbg !220
  store i32 %".393", i32* %".392", !dbg !220
  br label %"while.end.3", !dbg !221
if.else.3:
  %".396" = load i32, i32* %"i.addr", !dbg !222
  %".397" = sext i32 %".396" to i64 , !dbg !222
  %".398" = add i64 %".397", 1, !dbg !222
  %".399" = trunc i64 %".398" to i32 , !dbg !222
  store i32 %".399", i32* %"i.addr", !dbg !222
  %".401" = load i32, i32* %"i.addr", !dbg !223
  %".402" = load i32, i32* %"argc", !dbg !223
  %".403" = icmp sge i32 %".401", %".402" , !dbg !223
  br i1 %".403", label %"if.then.13", label %"if.end.13", !dbg !223
if.end.12:
  br label %"if.end.11", !dbg !231
if.then.13:
  %".405" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !224
  %".406" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".405", i32 0, i32 0 , !dbg !224
  %".407" = load i8*, i8** %".406", !dbg !224
  %".408" = call i32 @"eprints_cstr"(i8* %".407"), !dbg !224
  %".409" = getelementptr [12 x i8], [12 x i8]* @".str.15", i64 0, i64 0 , !dbg !225
  %".410" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".409", 0 , !dbg !225
  %".411" = insertvalue %"struct.ritz_module_1.StrView" %".410", i64 11, 1 , !dbg !225
  %".412" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".411"), !dbg !225
  %".413" = call i32 @"print_char"(i8 %".313"), !dbg !226
  %".414" = getelementptr [20 x i8], [20 x i8]* @".str.16", i64 0, i64 0 , !dbg !227
  %".415" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".414", 0 , !dbg !227
  %".416" = insertvalue %"struct.ritz_module_1.StrView" %".415", i64 19, 1 , !dbg !227
  %".417" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".416"), !dbg !227
  %".418" = trunc i64 1 to i32 , !dbg !228
  ret i32 %".418", !dbg !228
if.end.13:
  %".420" = load i8**, i8*** %"argv", !dbg !229
  %".421" = load i32, i32* %"i.addr", !dbg !229
  %".422" = getelementptr i8*, i8** %".420", i32 %".421" , !dbg !229
  %".423" = load i8*, i8** %".422", !dbg !229
  %".424" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !229
  %".425" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".424", i32 0, i32 2 , !dbg !229
  %".426" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".425", i32 0, i32 %".315" , !dbg !229
  %".427" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".426", !dbg !229
  %".428" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !229
  %".429" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".428", i32 0, i32 2 , !dbg !229
  %".430" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".429", i32 0, i32 %".315" , !dbg !229
  %".431" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".430", i32 0, i32 7 , !dbg !229
  store i8* %".423", i8** %".431", !dbg !229
  %".433" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !230
  %".434" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".433", i32 0, i32 2 , !dbg !230
  %".435" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".434", i32 0, i32 %".315" , !dbg !230
  %".436" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".435", !dbg !230
  %".437" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !230
  %".438" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".437", i32 0, i32 2 , !dbg !230
  %".439" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".438", i32 0, i32 %".315" , !dbg !230
  %".440" = getelementptr %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".439", i32 0, i32 6 , !dbg !230
  %".441" = trunc i64 1 to i32 , !dbg !230
  store i32 %".441", i32* %".440", !dbg !230
  br label %"while.end.3", !dbg !231
if.then.14:
  %".458" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !235
  %".459" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".458", i32 0, i32 7 , !dbg !235
  %".460" = load i32, i32* %".459", !dbg !235
  %".461" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !235
  %".462" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".461", i32 0, i32 6 , !dbg !235
  %".463" = getelementptr [256 x i8*], [256 x i8*]* %".462", i32 0, i32 %".460" , !dbg !235
  store i8* %".25", i8** %".463", !dbg !235
  %".465" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !236
  %".466" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".465", i32 0, i32 7 , !dbg !236
  %".467" = load i32, i32* %".466", !dbg !236
  %".468" = sext i32 %".467" to i64 , !dbg !236
  %".469" = add i64 %".468", 1, !dbg !236
  %".470" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !236
  %".471" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".470", i32 0, i32 7 , !dbg !236
  %".472" = trunc i64 %".469" to i32 , !dbg !236
  store i32 %".472", i32* %".471", !dbg !236
  br label %"if.end.14", !dbg !236
if.end.14:
  %".475" = load i32, i32* %"i.addr", !dbg !237
  %".476" = sext i32 %".475" to i64 , !dbg !237
  %".477" = add i64 %".476", 1, !dbg !237
  %".478" = trunc i64 %".477" to i32 , !dbg !237
  store i32 %".478", i32* %"i.addr", !dbg !237
  br label %"while.cond", !dbg !237
if.then.15:
  %".487" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !239
  %".488" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".487", i32 0, i32 4 , !dbg !239
  %".489" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".488", i32 0, i64 0 , !dbg !239
  %".490" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".489", !dbg !239
  %".491" = extractvalue %"struct.ritz_module_1.PosDef" %".490", 2 , !dbg !239
  %".492" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !240
  %".493" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".492", i32 0, i32 4 , !dbg !240
  %".494" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".493", i32 0, i64 0 , !dbg !240
  %".495" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".494", !dbg !240
  %".496" = extractvalue %"struct.ritz_module_1.PosDef" %".495", 3 , !dbg !240
  %".497" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !241
  %".498" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".497", i32 0, i32 7 , !dbg !241
  %".499" = load i32, i32* %".498", !dbg !241
  %".500" = icmp slt i32 %".499", %".491" , !dbg !241
  br i1 %".500", label %"if.then.16", label %"if.end.16", !dbg !241
if.end.15:
  %".543" = trunc i64 0 to i32 , !dbg !250
  ret i32 %".543", !dbg !250
if.then.16:
  %".502" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !242
  %".503" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".502", i32 0, i32 0 , !dbg !242
  %".504" = load i8*, i8** %".503", !dbg !242
  %".505" = call i32 @"eprints_cstr"(i8* %".504"), !dbg !242
  %".506" = getelementptr [30 x i8], [30 x i8]* @".str.17", i64 0, i64 0 , !dbg !243
  %".507" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".506", 0 , !dbg !243
  %".508" = insertvalue %"struct.ritz_module_1.StrView" %".507", i64 29, 1 , !dbg !243
  %".509" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".508"), !dbg !243
  %".510" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !244
  %".511" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".510", i32 0, i32 4 , !dbg !244
  %".512" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".511", i32 0, i64 0 , !dbg !244
  %".513" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".512", !dbg !244
  %".514" = extractvalue %"struct.ritz_module_1.PosDef" %".513", 0 , !dbg !244
  %".515" = call i32 @"eprints_cstr"(i8* %".514"), !dbg !244
  %".516" = getelementptr [3 x i8], [3 x i8]* @".str.18", i64 0, i64 0 , !dbg !245
  %".517" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".516", 0 , !dbg !245
  %".518" = insertvalue %"struct.ritz_module_1.StrView" %".517", i64 2, 1 , !dbg !245
  %".519" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".518"), !dbg !245
  %".520" = trunc i64 1 to i32 , !dbg !246
  ret i32 %".520", !dbg !246
if.end.16:
  %".522" = sext i32 %".496" to i64 , !dbg !246
  %".523" = icmp sge i64 %".522", 0 , !dbg !246
  br i1 %".523", label %"and.right.6", label %"and.merge.6", !dbg !246
and.right.6:
  %".525" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !246
  %".526" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".525", i32 0, i32 7 , !dbg !246
  %".527" = load i32, i32* %".526", !dbg !246
  %".528" = icmp sgt i32 %".527", %".496" , !dbg !246
  br label %"and.merge.6", !dbg !246
and.merge.6:
  %".530" = phi  i1 [0, %"if.end.16"], [%".528", %"and.right.6"] , !dbg !246
  br i1 %".530", label %"if.then.17", label %"if.end.17", !dbg !246
if.then.17:
  %".532" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !247
  %".533" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".532", i32 0, i32 0 , !dbg !247
  %".534" = load i8*, i8** %".533", !dbg !247
  %".535" = call i32 @"eprints_cstr"(i8* %".534"), !dbg !247
  %".536" = getelementptr [22 x i8], [22 x i8]* @".str.19", i64 0, i64 0 , !dbg !248
  %".537" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".536", 0 , !dbg !248
  %".538" = insertvalue %"struct.ritz_module_1.StrView" %".537", i64 21, 1 , !dbg !248
  %".539" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".538"), !dbg !248
  %".540" = trunc i64 1 to i32 , !dbg !249
  ret i32 %".540", !dbg !249
if.end.17:
  br label %"if.end.15", !dbg !249
}

define i32 @"args_get_flag"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8 %"short.arg") !dbg !24
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !251, metadata !7), !dbg !252
  %"short" = alloca i8
  store i8 %"short.arg", i8* %"short"
  call void @"llvm.dbg.declare"(metadata i8* %"short", metadata !253, metadata !7), !dbg !252
  %".8" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !254
  %".9" = load i8, i8* %"short", !dbg !254
  %".10" = call i32 @"find_option_short"(%"struct.ritz_module_1.ArgParser"* %".8", i8 %".9"), !dbg !254
  %".11" = sext i32 %".10" to i64 , !dbg !255
  %".12" = icmp slt i64 %".11", 0 , !dbg !255
  br i1 %".12", label %"if.then", label %"if.end", !dbg !255
if.then:
  %".14" = trunc i64 0 to i32 , !dbg !256
  ret i32 %".14", !dbg !256
if.end:
  %".16" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !257
  %".17" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".16", i32 0, i32 2 , !dbg !257
  %".18" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".17", i32 0, i32 %".10" , !dbg !257
  %".19" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".18", !dbg !257
  %".20" = extractvalue %"struct.ritz_module_1.OptDef" %".19", 7 , !dbg !257
  %".21" = getelementptr [2 x i8], [2 x i8]* @".str.20", i64 0, i64 0 , !dbg !257
  %".22" = call i32 @"streq"(i8* %".20", i8* %".21"), !dbg !257
  ret i32 %".22", !dbg !257
}

define i32 @"args_get_flag_long"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8* %"long.arg") !dbg !25
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !258, metadata !7), !dbg !259
  %"long" = alloca i8*
  store i8* %"long.arg", i8** %"long"
  call void @"llvm.dbg.declare"(metadata i8** %"long", metadata !260, metadata !7), !dbg !259
  %".8" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !261
  %".9" = load i8*, i8** %"long", !dbg !261
  %".10" = call i32 @"find_option_long"(%"struct.ritz_module_1.ArgParser"* %".8", i8* %".9"), !dbg !261
  %".11" = sext i32 %".10" to i64 , !dbg !262
  %".12" = icmp slt i64 %".11", 0 , !dbg !262
  br i1 %".12", label %"if.then", label %"if.end", !dbg !262
if.then:
  %".14" = trunc i64 0 to i32 , !dbg !263
  ret i32 %".14", !dbg !263
if.end:
  %".16" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !264
  %".17" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".16", i32 0, i32 2 , !dbg !264
  %".18" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".17", i32 0, i32 %".10" , !dbg !264
  %".19" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".18", !dbg !264
  %".20" = extractvalue %"struct.ritz_module_1.OptDef" %".19", 7 , !dbg !264
  %".21" = getelementptr [2 x i8], [2 x i8]* @".str.21", i64 0, i64 0 , !dbg !264
  %".22" = call i32 @"streq"(i8* %".20", i8* %".21"), !dbg !264
  ret i32 %".22", !dbg !264
}

define i8* @"args_get_str"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8 %"short.arg") !dbg !26
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !265, metadata !7), !dbg !266
  %"short" = alloca i8
  store i8 %"short.arg", i8* %"short"
  call void @"llvm.dbg.declare"(metadata i8* %"short", metadata !267, metadata !7), !dbg !266
  %".8" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !268
  %".9" = load i8, i8* %"short", !dbg !268
  %".10" = call i32 @"find_option_short"(%"struct.ritz_module_1.ArgParser"* %".8", i8 %".9"), !dbg !268
  %".11" = sext i32 %".10" to i64 , !dbg !269
  %".12" = icmp slt i64 %".11", 0 , !dbg !269
  br i1 %".12", label %"if.then", label %"if.end", !dbg !269
if.then:
  ret i8* null, !dbg !270
if.end:
  %".15" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !271
  %".16" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".15", i32 0, i32 2 , !dbg !271
  %".17" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".16", i32 0, i32 %".10" , !dbg !271
  %".18" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".17", !dbg !271
  %".19" = extractvalue %"struct.ritz_module_1.OptDef" %".18", 7 , !dbg !271
  ret i8* %".19", !dbg !271
}

define i8* @"args_get_str_long"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8* %"long.arg") !dbg !27
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !272, metadata !7), !dbg !273
  %"long" = alloca i8*
  store i8* %"long.arg", i8** %"long"
  call void @"llvm.dbg.declare"(metadata i8** %"long", metadata !274, metadata !7), !dbg !273
  %".8" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !275
  %".9" = load i8*, i8** %"long", !dbg !275
  %".10" = call i32 @"find_option_long"(%"struct.ritz_module_1.ArgParser"* %".8", i8* %".9"), !dbg !275
  %".11" = sext i32 %".10" to i64 , !dbg !276
  %".12" = icmp slt i64 %".11", 0 , !dbg !276
  br i1 %".12", label %"if.then", label %"if.end", !dbg !276
if.then:
  ret i8* null, !dbg !277
if.end:
  %".15" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !278
  %".16" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".15", i32 0, i32 2 , !dbg !278
  %".17" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".16", i32 0, i32 %".10" , !dbg !278
  %".18" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".17", !dbg !278
  %".19" = extractvalue %"struct.ritz_module_1.OptDef" %".18", 7 , !dbg !278
  ret i8* %".19", !dbg !278
}

define i64 @"args_get_int"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8 %"short.arg") !dbg !28
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !279, metadata !7), !dbg !280
  %"short" = alloca i8
  store i8 %"short.arg", i8* %"short"
  call void @"llvm.dbg.declare"(metadata i8* %"short", metadata !281, metadata !7), !dbg !280
  %".8" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !282
  %".9" = load i8, i8* %"short", !dbg !282
  %".10" = call i8* @"args_get_str"(%"struct.ritz_module_1.ArgParser"* %".8", i8 %".9"), !dbg !282
  %".11" = icmp eq i8* %".10", null , !dbg !283
  br i1 %".11", label %"if.then", label %"if.end", !dbg !283
if.then:
  ret i64 0, !dbg !284
if.end:
  %".14" = call i64 @"atoi"(i8* %".10"), !dbg !285
  ret i64 %".14", !dbg !285
}

define i64 @"args_get_int_long"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8* %"long.arg") !dbg !29
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !286, metadata !7), !dbg !287
  %"long" = alloca i8*
  store i8* %"long.arg", i8** %"long"
  call void @"llvm.dbg.declare"(metadata i8** %"long", metadata !288, metadata !7), !dbg !287
  %".8" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !289
  %".9" = load i8*, i8** %"long", !dbg !289
  %".10" = call i8* @"args_get_str_long"(%"struct.ritz_module_1.ArgParser"* %".8", i8* %".9"), !dbg !289
  %".11" = icmp eq i8* %".10", null , !dbg !290
  br i1 %".11", label %"if.then", label %"if.end", !dbg !290
if.then:
  ret i64 0, !dbg !291
if.end:
  %".14" = call i64 @"atoi"(i8* %".10"), !dbg !292
  ret i64 %".14", !dbg !292
}

define i8* @"args_get_positional"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i32 %"idx.arg") !dbg !30
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !293, metadata !7), !dbg !294
  %"idx" = alloca i32
  store i32 %"idx.arg", i32* %"idx"
  call void @"llvm.dbg.declare"(metadata i32* %"idx", metadata !295, metadata !7), !dbg !294
  %".8" = load i32, i32* %"idx", !dbg !296
  %".9" = sext i32 %".8" to i64 , !dbg !296
  %".10" = icmp slt i64 %".9", 0 , !dbg !296
  br i1 %".10", label %"or.merge", label %"or.right", !dbg !296
or.right:
  %".12" = load i32, i32* %"idx", !dbg !296
  %".13" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !296
  %".14" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".13", i32 0, i32 7 , !dbg !296
  %".15" = load i32, i32* %".14", !dbg !296
  %".16" = icmp sge i32 %".12", %".15" , !dbg !296
  br label %"or.merge", !dbg !296
or.merge:
  %".18" = phi  i1 [1, %"entry"], [%".16", %"or.right"] , !dbg !296
  br i1 %".18", label %"if.then", label %"if.end", !dbg !296
if.then:
  ret i8* null, !dbg !297
if.end:
  %".21" = load i32, i32* %"idx", !dbg !298
  %".22" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !298
  %".23" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".22", i32 0, i32 6 , !dbg !298
  %".24" = getelementptr [256 x i8*], [256 x i8*]* %".23", i32 0, i32 %".21" , !dbg !298
  %".25" = load i8*, i8** %".24", !dbg !298
  ret i8* %".25", !dbg !298
}

define i32 @"args_is_set"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8 %"short.arg") !dbg !31
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !299, metadata !7), !dbg !300
  %"short" = alloca i8
  store i8 %"short.arg", i8* %"short"
  call void @"llvm.dbg.declare"(metadata i8* %"short", metadata !301, metadata !7), !dbg !300
  %".8" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !302
  %".9" = load i8, i8* %"short", !dbg !302
  %".10" = call i32 @"find_option_short"(%"struct.ritz_module_1.ArgParser"* %".8", i8 %".9"), !dbg !302
  %".11" = sext i32 %".10" to i64 , !dbg !303
  %".12" = icmp slt i64 %".11", 0 , !dbg !303
  br i1 %".12", label %"if.then", label %"if.end", !dbg !303
if.then:
  %".14" = trunc i64 0 to i32 , !dbg !304
  ret i32 %".14", !dbg !304
if.end:
  %".16" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !305
  %".17" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".16", i32 0, i32 2 , !dbg !305
  %".18" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".17", i32 0, i32 %".10" , !dbg !305
  %".19" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".18", !dbg !305
  %".20" = extractvalue %"struct.ritz_module_1.OptDef" %".19", 6 , !dbg !305
  ret i32 %".20", !dbg !305
}

define i32 @"args_is_set_long"(%"struct.ritz_module_1.ArgParser"* %"parser.arg", i8* %"long.arg") !dbg !32
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !306, metadata !7), !dbg !307
  %"long" = alloca i8*
  store i8* %"long.arg", i8** %"long"
  call void @"llvm.dbg.declare"(metadata i8** %"long", metadata !308, metadata !7), !dbg !307
  %".8" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !309
  %".9" = load i8*, i8** %"long", !dbg !309
  %".10" = call i32 @"find_option_long"(%"struct.ritz_module_1.ArgParser"* %".8", i8* %".9"), !dbg !309
  %".11" = sext i32 %".10" to i64 , !dbg !310
  %".12" = icmp slt i64 %".11", 0 , !dbg !310
  br i1 %".12", label %"if.then", label %"if.end", !dbg !310
if.then:
  %".14" = trunc i64 0 to i32 , !dbg !311
  ret i32 %".14", !dbg !311
if.end:
  %".16" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !312
  %".17" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".16", i32 0, i32 2 , !dbg !312
  %".18" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".17", i32 0, i32 %".10" , !dbg !312
  %".19" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".18", !dbg !312
  %".20" = extractvalue %"struct.ritz_module_1.OptDef" %".19", 6 , !dbg !312
  ret i32 %".20", !dbg !312
}

define i32 @"args_print_usage"(%"struct.ritz_module_1.ArgParser"* %"parser.arg") !dbg !33
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  %"i" = alloca i32, !dbg !318
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !313, metadata !7), !dbg !314
  %".5" = getelementptr [8 x i8], [8 x i8]* @".str.22", i64 0, i64 0 , !dbg !315
  %".6" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".5", 0 , !dbg !315
  %".7" = insertvalue %"struct.ritz_module_1.StrView" %".6", i64 7, 1 , !dbg !315
  %".8" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".7"), !dbg !315
  %".9" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !316
  %".10" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".9", i32 0, i32 0 , !dbg !316
  %".11" = load i8*, i8** %".10", !dbg !316
  %".12" = call i32 @"prints_cstr"(i8* %".11"), !dbg !316
  %".13" = getelementptr [11 x i8], [11 x i8]* @".str.23", i64 0, i64 0 , !dbg !317
  %".14" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".13", 0 , !dbg !317
  %".15" = insertvalue %"struct.ritz_module_1.StrView" %".14", i64 10, 1 , !dbg !317
  %".16" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".15"), !dbg !317
  %".17" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !318
  %".18" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".17", i32 0, i32 5 , !dbg !318
  %".19" = load i32, i32* %".18", !dbg !318
  store i32 0, i32* %"i", !dbg !318
  br label %"for.cond", !dbg !318
for.cond:
  %".22" = load i32, i32* %"i", !dbg !318
  %".23" = icmp slt i32 %".22", %".19" , !dbg !318
  br i1 %".23", label %"for.body", label %"for.end", !dbg !318
for.body:
  %".25" = getelementptr [2 x i8], [2 x i8]* @".str.24", i64 0, i64 0 , !dbg !319
  %".26" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".25", 0 , !dbg !319
  %".27" = insertvalue %"struct.ritz_module_1.StrView" %".26", i64 1, 1 , !dbg !319
  %".28" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".27"), !dbg !319
  %".29" = load i32, i32* %"i", !dbg !320
  %".30" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !320
  %".31" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".30", i32 0, i32 4 , !dbg !320
  %".32" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".31", i32 0, i32 %".29" , !dbg !320
  %".33" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".32", !dbg !320
  %".34" = extractvalue %"struct.ritz_module_1.PosDef" %".33", 2 , !dbg !320
  %".35" = sext i32 %".34" to i64 , !dbg !320
  %".36" = icmp eq i64 %".35", 0 , !dbg !320
  br i1 %".36", label %"if.then", label %"if.end", !dbg !320
for.incr:
  %".90" = load i32, i32* %"i", !dbg !322
  %".91" = add i32 %".90", 1, !dbg !322
  store i32 %".91", i32* %"i", !dbg !322
  br label %"for.cond", !dbg !322
for.end:
  %".94" = getelementptr [2 x i8], [2 x i8]* @".str.28", i64 0, i64 0 , !dbg !323
  %".95" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".94", 0 , !dbg !323
  %".96" = insertvalue %"struct.ritz_module_1.StrView" %".95", i64 1, 1 , !dbg !323
  %".97" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".96"), !dbg !323
  ret i32 %".97", !dbg !323
if.then:
  %".38" = getelementptr [2 x i8], [2 x i8]* @".str.25", i64 0, i64 0 , !dbg !320
  %".39" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".38", 0 , !dbg !320
  %".40" = insertvalue %"struct.ritz_module_1.StrView" %".39", i64 1, 1 , !dbg !320
  %".41" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".40"), !dbg !320
  br label %"if.end", !dbg !320
if.end:
  %".43" = load i32, i32* %"i", !dbg !321
  %".44" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !321
  %".45" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".44", i32 0, i32 4 , !dbg !321
  %".46" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".45", i32 0, i32 %".43" , !dbg !321
  %".47" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".46", !dbg !321
  %".48" = extractvalue %"struct.ritz_module_1.PosDef" %".47", 0 , !dbg !321
  %".49" = call i32 @"prints_cstr"(i8* %".48"), !dbg !321
  %".50" = load i32, i32* %"i", !dbg !322
  %".51" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !322
  %".52" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".51", i32 0, i32 4 , !dbg !322
  %".53" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".52", i32 0, i32 %".50" , !dbg !322
  %".54" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".53", !dbg !322
  %".55" = extractvalue %"struct.ritz_module_1.PosDef" %".54", 3 , !dbg !322
  %".56" = sext i32 %".55" to i64 , !dbg !322
  %".57" = icmp slt i64 %".56", 0 , !dbg !322
  br i1 %".57", label %"or.merge", label %"or.right", !dbg !322
or.right:
  %".59" = load i32, i32* %"i", !dbg !322
  %".60" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !322
  %".61" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".60", i32 0, i32 4 , !dbg !322
  %".62" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".61", i32 0, i32 %".59" , !dbg !322
  %".63" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".62", !dbg !322
  %".64" = extractvalue %"struct.ritz_module_1.PosDef" %".63", 3 , !dbg !322
  %".65" = sext i32 %".64" to i64 , !dbg !322
  %".66" = icmp sgt i64 %".65", 1 , !dbg !322
  br label %"or.merge", !dbg !322
or.merge:
  %".68" = phi  i1 [1, %"if.end"], [%".66", %"or.right"] , !dbg !322
  br i1 %".68", label %"if.then.1", label %"if.end.1", !dbg !322
if.then.1:
  %".70" = getelementptr [4 x i8], [4 x i8]* @".str.26", i64 0, i64 0 , !dbg !322
  %".71" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".70", 0 , !dbg !322
  %".72" = insertvalue %"struct.ritz_module_1.StrView" %".71", i64 3, 1 , !dbg !322
  %".73" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".72"), !dbg !322
  br label %"if.end.1", !dbg !322
if.end.1:
  %".75" = load i32, i32* %"i", !dbg !322
  %".76" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !322
  %".77" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".76", i32 0, i32 4 , !dbg !322
  %".78" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".77", i32 0, i32 %".75" , !dbg !322
  %".79" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".78", !dbg !322
  %".80" = extractvalue %"struct.ritz_module_1.PosDef" %".79", 2 , !dbg !322
  %".81" = sext i32 %".80" to i64 , !dbg !322
  %".82" = icmp eq i64 %".81", 0 , !dbg !322
  br i1 %".82", label %"if.then.2", label %"if.end.2", !dbg !322
if.then.2:
  %".84" = getelementptr [2 x i8], [2 x i8]* @".str.27", i64 0, i64 0 , !dbg !322
  %".85" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".84", 0 , !dbg !322
  %".86" = insertvalue %"struct.ritz_module_1.StrView" %".85", i64 1, 1 , !dbg !322
  %".87" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".86"), !dbg !322
  br label %"if.end.2", !dbg !322
if.end.2:
  br label %"for.incr", !dbg !322
}

define i32 @"args_print_help"(%"struct.ritz_module_1.ArgParser"* %"parser.arg") !dbg !34
{
entry:
  %"parser" = alloca %"struct.ritz_module_1.ArgParser"*
  %"i" = alloca i32, !dbg !332
  %"i.1" = alloca i32, !dbg !348
  store %"struct.ritz_module_1.ArgParser"* %"parser.arg", %"struct.ritz_module_1.ArgParser"** %"parser"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ArgParser"** %"parser", metadata !324, metadata !7), !dbg !325
  %".5" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !326
  %".6" = call i32 @"args_print_usage"(%"struct.ritz_module_1.ArgParser"* %".5"), !dbg !326
  %".7" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !327
  %".8" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".7", i32 0, i32 1 , !dbg !327
  %".9" = load i8*, i8** %".8", !dbg !327
  %".10" = icmp ne i8* %".9", null , !dbg !327
  br i1 %".10", label %"if.then", label %"if.end", !dbg !327
if.then:
  %".12" = getelementptr [2 x i8], [2 x i8]* @".str.29", i64 0, i64 0 , !dbg !328
  %".13" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".12", 0 , !dbg !328
  %".14" = insertvalue %"struct.ritz_module_1.StrView" %".13", i64 1, 1 , !dbg !328
  %".15" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".14"), !dbg !328
  %".16" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !329
  %".17" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".16", i32 0, i32 1 , !dbg !329
  %".18" = load i8*, i8** %".17", !dbg !329
  %".19" = call i32 @"prints_cstr"(i8* %".18"), !dbg !329
  %".20" = getelementptr [2 x i8], [2 x i8]* @".str.30", i64 0, i64 0 , !dbg !329
  %".21" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".20", 0 , !dbg !329
  %".22" = insertvalue %"struct.ritz_module_1.StrView" %".21", i64 1, 1 , !dbg !329
  %".23" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".22"), !dbg !329
  br label %"if.end", !dbg !329
if.end:
  %".25" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !330
  %".26" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".25", i32 0, i32 3 , !dbg !330
  %".27" = load i32, i32* %".26", !dbg !330
  %".28" = sext i32 %".27" to i64 , !dbg !330
  %".29" = icmp sgt i64 %".28", 0 , !dbg !330
  br i1 %".29", label %"if.then.1", label %"if.end.1", !dbg !330
if.then.1:
  %".31" = getelementptr [11 x i8], [11 x i8]* @".str.31", i64 0, i64 0 , !dbg !331
  %".32" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".31", 0 , !dbg !331
  %".33" = insertvalue %"struct.ritz_module_1.StrView" %".32", i64 10, 1 , !dbg !331
  %".34" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".33"), !dbg !331
  %".35" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !332
  %".36" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".35", i32 0, i32 3 , !dbg !332
  %".37" = load i32, i32* %".36", !dbg !332
  store i32 0, i32* %"i", !dbg !332
  br label %"for.cond", !dbg !332
if.end.1:
  %".180" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !346
  %".181" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".180", i32 0, i32 5 , !dbg !346
  %".182" = load i32, i32* %".181", !dbg !346
  %".183" = sext i32 %".182" to i64 , !dbg !346
  %".184" = icmp sgt i64 %".183", 0 , !dbg !346
  br i1 %".184", label %"if.then.8", label %"if.end.8", !dbg !346
for.cond:
  %".40" = load i32, i32* %"i", !dbg !332
  %".41" = icmp slt i32 %".40", %".37" , !dbg !332
  br i1 %".41", label %"for.body", label %"for.end", !dbg !332
for.body:
  %".43" = getelementptr [3 x i8], [3 x i8]* @".str.32", i64 0, i64 0 , !dbg !333
  %".44" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".43", 0 , !dbg !333
  %".45" = insertvalue %"struct.ritz_module_1.StrView" %".44", i64 2, 1 , !dbg !333
  %".46" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".45"), !dbg !333
  %".47" = load i32, i32* %"i", !dbg !334
  %".48" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !334
  %".49" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".48", i32 0, i32 2 , !dbg !334
  %".50" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".49", i32 0, i32 %".47" , !dbg !334
  %".51" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".50", !dbg !334
  %".52" = extractvalue %"struct.ritz_module_1.OptDef" %".51", 0 , !dbg !334
  %".53" = sext i8 %".52" to i64 , !dbg !334
  %".54" = icmp ne i64 %".53", 0 , !dbg !334
  br i1 %".54", label %"if.then.2", label %"if.else", !dbg !334
for.incr:
  %".175" = load i32, i32* %"i", !dbg !345
  %".176" = add i32 %".175", 1, !dbg !345
  store i32 %".176", i32* %"i", !dbg !345
  br label %"for.cond", !dbg !345
for.end:
  br label %"if.end.1", !dbg !345
if.then.2:
  %".56" = getelementptr [2 x i8], [2 x i8]* @".str.33", i64 0, i64 0 , !dbg !335
  %".57" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".56", 0 , !dbg !335
  %".58" = insertvalue %"struct.ritz_module_1.StrView" %".57", i64 1, 1 , !dbg !335
  %".59" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".58"), !dbg !335
  %".60" = load i32, i32* %"i", !dbg !336
  %".61" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !336
  %".62" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".61", i32 0, i32 2 , !dbg !336
  %".63" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".62", i32 0, i32 %".60" , !dbg !336
  %".64" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".63", !dbg !336
  %".65" = extractvalue %"struct.ritz_module_1.OptDef" %".64", 0 , !dbg !336
  %".66" = call i32 @"print_char"(i8 %".65"), !dbg !336
  %".67" = load i32, i32* %"i", !dbg !336
  %".68" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !336
  %".69" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".68", i32 0, i32 2 , !dbg !336
  %".70" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".69", i32 0, i32 %".67" , !dbg !336
  %".71" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".70", !dbg !336
  %".72" = extractvalue %"struct.ritz_module_1.OptDef" %".71", 1 , !dbg !336
  %".73" = icmp ne i8* %".72", null , !dbg !336
  br i1 %".73", label %"if.then.3", label %"if.end.3", !dbg !336
if.else:
  %".80" = getelementptr [5 x i8], [5 x i8]* @".str.35", i64 0, i64 0 , !dbg !336
  %".81" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".80", 0 , !dbg !336
  %".82" = insertvalue %"struct.ritz_module_1.StrView" %".81", i64 4, 1 , !dbg !336
  %".83" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".82"), !dbg !336
  br label %"if.end.2", !dbg !336
if.end.2:
  %".86" = load i32, i32* %"i", !dbg !337
  %".87" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !337
  %".88" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".87", i32 0, i32 2 , !dbg !337
  %".89" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".88", i32 0, i32 %".86" , !dbg !337
  %".90" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".89", !dbg !337
  %".91" = extractvalue %"struct.ritz_module_1.OptDef" %".90", 1 , !dbg !337
  %".92" = icmp ne i8* %".91", null , !dbg !337
  br i1 %".92", label %"if.then.4", label %"if.end.4", !dbg !337
if.then.3:
  %".75" = getelementptr [3 x i8], [3 x i8]* @".str.34", i64 0, i64 0 , !dbg !336
  %".76" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".75", 0 , !dbg !336
  %".77" = insertvalue %"struct.ritz_module_1.StrView" %".76", i64 2, 1 , !dbg !336
  %".78" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".77"), !dbg !336
  br label %"if.end.3", !dbg !336
if.end.3:
  br label %"if.end.2", !dbg !336
if.then.4:
  %".94" = getelementptr [3 x i8], [3 x i8]* @".str.36", i64 0, i64 0 , !dbg !338
  %".95" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".94", 0 , !dbg !338
  %".96" = insertvalue %"struct.ritz_module_1.StrView" %".95", i64 2, 1 , !dbg !338
  %".97" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".96"), !dbg !338
  %".98" = load i32, i32* %"i", !dbg !339
  %".99" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !339
  %".100" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".99", i32 0, i32 2 , !dbg !339
  %".101" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".100", i32 0, i32 %".98" , !dbg !339
  %".102" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".101", !dbg !339
  %".103" = extractvalue %"struct.ritz_module_1.OptDef" %".102", 1 , !dbg !339
  %".104" = call i32 @"prints_cstr"(i8* %".103"), !dbg !339
  %".105" = load i32, i32* %"i", !dbg !339
  %".106" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !339
  %".107" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".106", i32 0, i32 2 , !dbg !339
  %".108" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".107", i32 0, i32 %".105" , !dbg !339
  %".109" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".108", !dbg !339
  %".110" = extractvalue %"struct.ritz_module_1.OptDef" %".109", 2 , !dbg !339
  %".111" = icmp ne i8* %".110", null , !dbg !339
  br i1 %".111", label %"if.then.5", label %"if.end.5", !dbg !339
if.end.4:
  %".126" = getelementptr [10 x i8], [10 x i8]* @".str.38", i64 0, i64 0 , !dbg !341
  %".127" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".126", 0 , !dbg !341
  %".128" = insertvalue %"struct.ritz_module_1.StrView" %".127", i64 9, 1 , !dbg !341
  %".129" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".128"), !dbg !341
  %".130" = load i32, i32* %"i", !dbg !342
  %".131" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !342
  %".132" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".131", i32 0, i32 2 , !dbg !342
  %".133" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".132", i32 0, i32 %".130" , !dbg !342
  %".134" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".133", !dbg !342
  %".135" = extractvalue %"struct.ritz_module_1.OptDef" %".134", 3 , !dbg !342
  %".136" = call i32 @"prints_cstr"(i8* %".135"), !dbg !342
  %".137" = load i32, i32* %"i", !dbg !343
  %".138" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !343
  %".139" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".138", i32 0, i32 2 , !dbg !343
  %".140" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".139", i32 0, i32 %".137" , !dbg !343
  %".141" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".140", !dbg !343
  %".142" = extractvalue %"struct.ritz_module_1.OptDef" %".141", 4 , !dbg !343
  %".143" = icmp ne i8* %".142", null , !dbg !343
  br i1 %".143", label %"if.then.6", label %"if.end.6", !dbg !343
if.then.5:
  %".113" = getelementptr [2 x i8], [2 x i8]* @".str.37", i64 0, i64 0 , !dbg !340
  %".114" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".113", 0 , !dbg !340
  %".115" = insertvalue %"struct.ritz_module_1.StrView" %".114", i64 1, 1 , !dbg !340
  %".116" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".115"), !dbg !340
  %".117" = load i32, i32* %"i", !dbg !340
  %".118" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !340
  %".119" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".118", i32 0, i32 2 , !dbg !340
  %".120" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".119", i32 0, i32 %".117" , !dbg !340
  %".121" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".120", !dbg !340
  %".122" = extractvalue %"struct.ritz_module_1.OptDef" %".121", 2 , !dbg !340
  %".123" = call i32 @"prints_cstr"(i8* %".122"), !dbg !340
  br label %"if.end.5", !dbg !340
if.end.5:
  br label %"if.end.4", !dbg !340
if.then.6:
  %".145" = load i32, i32* %"i", !dbg !343
  %".146" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !343
  %".147" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".146", i32 0, i32 2 , !dbg !343
  %".148" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".147", i32 0, i32 %".145" , !dbg !343
  %".149" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".148", !dbg !343
  %".150" = extractvalue %"struct.ritz_module_1.OptDef" %".149", 5 , !dbg !343
  %".151" = icmp eq i32 %".150", 1 , !dbg !343
  br i1 %".151", label %"if.then.7", label %"if.end.7", !dbg !343
if.end.6:
  %".170" = getelementptr [2 x i8], [2 x i8]* @".str.41", i64 0, i64 0 , !dbg !345
  %".171" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".170", 0 , !dbg !345
  %".172" = insertvalue %"struct.ritz_module_1.StrView" %".171", i64 1, 1 , !dbg !345
  %".173" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".172"), !dbg !345
  br label %"for.incr", !dbg !345
if.then.7:
  %".153" = getelementptr [12 x i8], [12 x i8]* @".str.39", i64 0, i64 0 , !dbg !344
  %".154" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".153", 0 , !dbg !344
  %".155" = insertvalue %"struct.ritz_module_1.StrView" %".154", i64 11, 1 , !dbg !344
  %".156" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".155"), !dbg !344
  %".157" = load i32, i32* %"i", !dbg !345
  %".158" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !345
  %".159" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".158", i32 0, i32 2 , !dbg !345
  %".160" = getelementptr [32 x %"struct.ritz_module_1.OptDef"], [32 x %"struct.ritz_module_1.OptDef"]* %".159", i32 0, i32 %".157" , !dbg !345
  %".161" = load %"struct.ritz_module_1.OptDef", %"struct.ritz_module_1.OptDef"* %".160", !dbg !345
  %".162" = extractvalue %"struct.ritz_module_1.OptDef" %".161", 4 , !dbg !345
  %".163" = call i32 @"prints_cstr"(i8* %".162"), !dbg !345
  %".164" = getelementptr [2 x i8], [2 x i8]* @".str.40", i64 0, i64 0 , !dbg !345
  %".165" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".164", 0 , !dbg !345
  %".166" = insertvalue %"struct.ritz_module_1.StrView" %".165", i64 1, 1 , !dbg !345
  %".167" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".166"), !dbg !345
  br label %"if.end.7", !dbg !345
if.end.7:
  br label %"if.end.6", !dbg !345
if.then.8:
  %".186" = getelementptr [13 x i8], [13 x i8]* @".str.42", i64 0, i64 0 , !dbg !347
  %".187" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".186", 0 , !dbg !347
  %".188" = insertvalue %"struct.ritz_module_1.StrView" %".187", i64 12, 1 , !dbg !347
  %".189" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".188"), !dbg !347
  %".190" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !348
  %".191" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".190", i32 0, i32 5 , !dbg !348
  %".192" = load i32, i32* %".191", !dbg !348
  store i32 0, i32* %"i.1", !dbg !348
  br label %"for.cond.1", !dbg !348
if.end.8:
  ret i32 0, !dbg !352
for.cond.1:
  %".195" = load i32, i32* %"i.1", !dbg !348
  %".196" = icmp slt i32 %".195", %".192" , !dbg !348
  br i1 %".196", label %"for.body.1", label %"for.end.1", !dbg !348
for.body.1:
  %".198" = getelementptr [3 x i8], [3 x i8]* @".str.43", i64 0, i64 0 , !dbg !349
  %".199" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".198", 0 , !dbg !349
  %".200" = insertvalue %"struct.ritz_module_1.StrView" %".199", i64 2, 1 , !dbg !349
  %".201" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".200"), !dbg !349
  %".202" = load i32, i32* %"i.1", !dbg !350
  %".203" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !350
  %".204" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".203", i32 0, i32 4 , !dbg !350
  %".205" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".204", i32 0, i32 %".202" , !dbg !350
  %".206" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".205", !dbg !350
  %".207" = extractvalue %"struct.ritz_module_1.PosDef" %".206", 0 , !dbg !350
  %".208" = call i32 @"prints_cstr"(i8* %".207"), !dbg !350
  %".209" = getelementptr [10 x i8], [10 x i8]* @".str.44", i64 0, i64 0 , !dbg !351
  %".210" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".209", 0 , !dbg !351
  %".211" = insertvalue %"struct.ritz_module_1.StrView" %".210", i64 9, 1 , !dbg !351
  %".212" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".211"), !dbg !351
  %".213" = load i32, i32* %"i.1", !dbg !352
  %".214" = load %"struct.ritz_module_1.ArgParser"*, %"struct.ritz_module_1.ArgParser"** %"parser", !dbg !352
  %".215" = getelementptr %"struct.ritz_module_1.ArgParser", %"struct.ritz_module_1.ArgParser"* %".214", i32 0, i32 4 , !dbg !352
  %".216" = getelementptr [8 x %"struct.ritz_module_1.PosDef"], [8 x %"struct.ritz_module_1.PosDef"]* %".215", i32 0, i32 %".213" , !dbg !352
  %".217" = load %"struct.ritz_module_1.PosDef", %"struct.ritz_module_1.PosDef"* %".216", !dbg !352
  %".218" = extractvalue %"struct.ritz_module_1.PosDef" %".217", 1 , !dbg !352
  %".219" = call i32 @"prints_cstr"(i8* %".218"), !dbg !352
  %".220" = getelementptr [2 x i8], [2 x i8]* @".str.45", i64 0, i64 0 , !dbg !352
  %".221" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".220", 0 , !dbg !352
  %".222" = insertvalue %"struct.ritz_module_1.StrView" %".221", i64 1, 1 , !dbg !352
  %".223" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".222"), !dbg !352
  br label %"for.incr.1", !dbg !352
for.incr.1:
  %".225" = load i32, i32* %"i.1", !dbg !352
  %".226" = add i32 %".225", 1, !dbg !352
  store i32 %".226", i32* %"i.1", !dbg !352
  br label %"for.cond.1", !dbg !352
for.end.1:
  br label %"if.end.8", !dbg !352
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !35
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !355, metadata !7), !dbg !356
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !358, metadata !7), !dbg !356
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !359
  %".8" = load i64, i64* %".7", !dbg !359
  %".9" = add i64 %".8", 1, !dbg !359
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !359
  %".11" = sext i32 %".10" to i64 , !dbg !359
  %".12" = icmp ne i64 %".11", 0 , !dbg !359
  br i1 %".12", label %"if.then", label %"if.end", !dbg !359
if.then:
  %".14" = sub i64 0, 1, !dbg !360
  %".15" = trunc i64 %".14" to i32 , !dbg !360
  ret i32 %".15", !dbg !360
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !361
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !361
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !361
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !361
  %".21" = load i64, i64* %".20", !dbg !361
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !361
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !361
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !362
  %".25" = load i64, i64* %".24", !dbg !362
  %".26" = add i64 %".25", 1, !dbg !362
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !362
  store i64 %".26", i64* %".27", !dbg !362
  %".29" = trunc i64 0 to i32 , !dbg !363
  ret i32 %".29", !dbg !363
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !36
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !366, metadata !7), !dbg !367
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !368
  %".5" = load i8*, i8** %".4", !dbg !368
  %".6" = icmp ne i8* %".5", null , !dbg !368
  br i1 %".6", label %"if.then", label %"if.end", !dbg !368
if.then:
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !368
  %".9" = load i8*, i8** %".8", !dbg !368
  %".10" = call i32 @"free"(i8* %".9"), !dbg !368
  br label %"if.end", !dbg !368
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !369
  store i8* null, i8** %".12", !dbg !369
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !370
  store i64 0, i64* %".14", !dbg !370
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !371
  store i64 0, i64* %".16", !dbg !371
  ret i32 0, !dbg !371
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !37
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !372, metadata !7), !dbg !373
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !374, metadata !7), !dbg !373
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !375, metadata !7), !dbg !373
  %".10" = load i8, i8* %"item", !dbg !376
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !376
  %".12" = load i8*, i8** %".11", !dbg !376
  %".13" = load i64, i64* %"idx", !dbg !376
  %".14" = getelementptr i8, i8* %".12", i64 %".13" , !dbg !376
  store i8 %".10", i8* %".14", !dbg !376
  %".16" = trunc i64 0 to i32 , !dbg !377
  ret i32 %".16", !dbg !377
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !38
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !378, metadata !7), !dbg !379
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !380, metadata !7), !dbg !379
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !381
  %".8" = load i8*, i8** %".7", !dbg !381
  %".9" = load i64, i64* %"idx", !dbg !381
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !381
  %".11" = load i8, i8* %".10", !dbg !381
  ret i8 %".11", !dbg !381
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !39
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !382, metadata !7), !dbg !383
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !384
  %".5" = load i64, i64* %".4", !dbg !384
  %".6" = sub i64 %".5", 1, !dbg !384
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !384
  store i64 %".6", i64* %".7", !dbg !384
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !385
  %".10" = load i8*, i8** %".9", !dbg !385
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !385
  %".12" = load i64, i64* %".11", !dbg !385
  %".13" = getelementptr i8, i8* %".10", i64 %".12" , !dbg !385
  %".14" = load i8, i8* %".13", !dbg !385
  ret i8 %".14", !dbg !385
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !40
{
entry:
  %"i" = alloca i64, !dbg !390
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !386, metadata !7), !dbg !387
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !388, metadata !7), !dbg !387
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !389, metadata !7), !dbg !387
  %".10" = load i64, i64* %"len", !dbg !390
  store i64 0, i64* %"i", !dbg !390
  br label %"for.cond", !dbg !390
for.cond:
  %".13" = load i64, i64* %"i", !dbg !390
  %".14" = icmp slt i64 %".13", %".10" , !dbg !390
  br i1 %".14", label %"for.body", label %"for.end", !dbg !390
for.body:
  %".16" = load i8*, i8** %"data", !dbg !390
  %".17" = load i64, i64* %"i", !dbg !390
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !390
  %".19" = load i8, i8* %".18", !dbg !390
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !390
  %".21" = sext i32 %".20" to i64 , !dbg !390
  %".22" = icmp ne i64 %".21", 0 , !dbg !390
  br i1 %".22", label %"if.then", label %"if.end", !dbg !390
for.incr:
  %".28" = load i64, i64* %"i", !dbg !391
  %".29" = add i64 %".28", 1, !dbg !391
  store i64 %".29", i64* %"i", !dbg !391
  br label %"for.cond", !dbg !391
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !392
  ret i32 %".32", !dbg !392
if.then:
  %".24" = sub i64 0, 1, !dbg !391
  %".25" = trunc i64 %".24" to i32 , !dbg !391
  ret i32 %".25", !dbg !391
if.end:
  br label %"for.incr", !dbg !391
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !41
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !393, metadata !7), !dbg !394
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !395
  store i64 0, i64* %".4", !dbg !395
  ret i32 0, !dbg !395
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !42
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !401
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !396, metadata !7), !dbg !397
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !398, metadata !7), !dbg !397
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !399
  %".8" = load i64, i64* %".7", !dbg !399
  %".9" = load i64, i64* %"needed", !dbg !399
  %".10" = icmp sge i64 %".8", %".9" , !dbg !399
  br i1 %".10", label %"if.then", label %"if.end", !dbg !399
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !400
  ret i32 %".12", !dbg !400
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !401
  %".15" = load i64, i64* %".14", !dbg !401
  store i64 %".15", i64* %"new_cap.addr", !dbg !401
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !402, metadata !7), !dbg !403
  %".18" = load i64, i64* %"new_cap.addr", !dbg !404
  %".19" = icmp eq i64 %".18", 0 , !dbg !404
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !404
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !405
  br label %"if.end.1", !dbg !405
if.end.1:
  br label %"while.cond", !dbg !406
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !406
  %".25" = load i64, i64* %"needed", !dbg !406
  %".26" = icmp slt i64 %".24", %".25" , !dbg !406
  br i1 %".26", label %"while.body", label %"while.end", !dbg !406
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !407
  %".29" = mul i64 %".28", 2, !dbg !407
  store i64 %".29", i64* %"new_cap.addr", !dbg !407
  br label %"while.cond", !dbg !407
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !408
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !408
  ret i32 %".33", !dbg !408
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !43
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !411
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !409, metadata !7), !dbg !410
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !412, metadata !7), !dbg !413
  %".6" = load i64, i64* %"cap", !dbg !414
  %".7" = icmp sle i64 %".6", 0 , !dbg !414
  br i1 %".7", label %"if.then", label %"if.end", !dbg !414
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !415
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !415
  store i8* null, i8** %".10", !dbg !415
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !416
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !416
  store i64 0, i64* %".13", !dbg !416
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !417
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !417
  store i64 0, i64* %".16", !dbg !417
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !418
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !418
if.end:
  %".20" = load i64, i64* %"cap", !dbg !419
  %".21" = mul i64 %".20", 1, !dbg !419
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !420
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !420
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !420
  store i8* %".22", i8** %".24", !dbg !420
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !421
  %".27" = load i8*, i8** %".26", !dbg !421
  %".28" = icmp eq i8* %".27", null , !dbg !421
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !421
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !422
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !422
  store i64 0, i64* %".31", !dbg !422
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !423
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !423
  store i64 0, i64* %".34", !dbg !423
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !424
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !424
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !425
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !425
  store i64 0, i64* %".39", !dbg !425
  %".41" = load i64, i64* %"cap", !dbg !426
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !426
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !426
  store i64 %".41", i64* %".43", !dbg !426
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !427
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !427
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !44
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !428
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !429, metadata !7), !dbg !430
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !431
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !431
  store i8* null, i8** %".4", !dbg !431
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !432
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !432
  store i64 0, i64* %".7", !dbg !432
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !433
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !433
  store i64 0, i64* %".10", !dbg !433
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !434
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !434
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !45
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !435, metadata !7), !dbg !436
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !437, metadata !7), !dbg !436
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !438
  %".8" = load i64, i64* %".7", !dbg !438
  %".9" = add i64 %".8", 1, !dbg !438
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !438
  %".11" = sext i32 %".10" to i64 , !dbg !438
  %".12" = icmp ne i64 %".11", 0 , !dbg !438
  br i1 %".12", label %"if.then", label %"if.end", !dbg !438
if.then:
  %".14" = sub i64 0, 1, !dbg !439
  %".15" = trunc i64 %".14" to i32 , !dbg !439
  ret i32 %".15", !dbg !439
if.end:
  %".17" = load i8, i8* %"item", !dbg !440
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !440
  %".19" = load i8*, i8** %".18", !dbg !440
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !440
  %".21" = load i64, i64* %".20", !dbg !440
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !440
  store i8 %".17", i8* %".22", !dbg !440
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !441
  %".25" = load i64, i64* %".24", !dbg !441
  %".26" = add i64 %".25", 1, !dbg !441
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !441
  store i64 %".26", i64* %".27", !dbg !441
  %".29" = trunc i64 0 to i32 , !dbg !442
  ret i32 %".29", !dbg !442
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !46
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !448
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !443, metadata !7), !dbg !444
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !445, metadata !7), !dbg !444
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !446
  %".8" = load i64, i64* %".7", !dbg !446
  %".9" = load i64, i64* %"needed", !dbg !446
  %".10" = icmp sge i64 %".8", %".9" , !dbg !446
  br i1 %".10", label %"if.then", label %"if.end", !dbg !446
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !447
  ret i32 %".12", !dbg !447
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !448
  %".15" = load i64, i64* %".14", !dbg !448
  store i64 %".15", i64* %"new_cap.addr", !dbg !448
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !449, metadata !7), !dbg !450
  %".18" = load i64, i64* %"new_cap.addr", !dbg !451
  %".19" = icmp eq i64 %".18", 0 , !dbg !451
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !451
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !452
  br label %"if.end.1", !dbg !452
if.end.1:
  br label %"while.cond", !dbg !453
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !453
  %".25" = load i64, i64* %"needed", !dbg !453
  %".26" = icmp slt i64 %".24", %".25" , !dbg !453
  br i1 %".26", label %"while.body", label %"while.end", !dbg !453
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !454
  %".29" = mul i64 %".28", 2, !dbg !454
  store i64 %".29", i64* %"new_cap.addr", !dbg !454
  br label %"while.cond", !dbg !454
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !455
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !455
  ret i32 %".33", !dbg !455
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !47
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !456, metadata !7), !dbg !457
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !458, metadata !7), !dbg !457
  %".7" = load i64, i64* %"new_cap", !dbg !459
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !459
  %".9" = load i64, i64* %".8", !dbg !459
  %".10" = icmp sle i64 %".7", %".9" , !dbg !459
  br i1 %".10", label %"if.then", label %"if.end", !dbg !459
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !460
  ret i32 %".12", !dbg !460
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !461
  %".15" = mul i64 %".14", 1, !dbg !461
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !462
  %".17" = load i8*, i8** %".16", !dbg !462
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !462
  %".19" = icmp eq i8* %".18", null , !dbg !463
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !463
if.then.1:
  %".21" = sub i64 0, 1, !dbg !464
  %".22" = trunc i64 %".21" to i32 , !dbg !464
  ret i32 %".22", !dbg !464
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !465
  store i8* %".18", i8** %".24", !dbg !465
  %".26" = load i64, i64* %"new_cap", !dbg !466
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !466
  store i64 %".26", i64* %".27", !dbg !466
  %".29" = trunc i64 0 to i32 , !dbg !467
  ret i32 %".29", !dbg !467
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !48
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !468, metadata !7), !dbg !469
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !470, metadata !7), !dbg !469
  %".7" = load i64, i64* %"new_cap", !dbg !471
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !471
  %".9" = load i64, i64* %".8", !dbg !471
  %".10" = icmp sle i64 %".7", %".9" , !dbg !471
  br i1 %".10", label %"if.then", label %"if.end", !dbg !471
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !472
  ret i32 %".12", !dbg !472
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !473
  %".15" = mul i64 %".14", 16, !dbg !473
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !474
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !474
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !474
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !474
  %".20" = icmp eq i8* %".19", null , !dbg !475
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !475
if.then.1:
  %".22" = sub i64 0, 1, !dbg !476
  %".23" = trunc i64 %".22" to i32 , !dbg !476
  ret i32 %".23", !dbg !476
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !477
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !477
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !477
  %".28" = load i64, i64* %"new_cap", !dbg !478
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !478
  store i64 %".28", i64* %".29", !dbg !478
  %".31" = trunc i64 0 to i32 , !dbg !479
  ret i32 %".31", !dbg !479
}

@".str.0" = private constant [2 x i8] c"0\00"
@".str.1" = private constant [2 x i8] c"0\00"
@".str.2" = private constant [3 x i8] c"--\00"
@".str.3" = private constant [21 x i8] c": unknown option '--\00"
@".str.4" = private constant [3 x i8] c"'\0a\00"
@".str.5" = private constant [13 x i8] c": option '--\00"
@".str.6" = private constant [26 x i8] c"' doesn't accept a value\0a\00"
@".str.7" = private constant [21 x i8] c": unknown option '--\00"
@".str.8" = private constant [3 x i8] c"'\0a\00"
@".str.9" = private constant [2 x i8] c"1\00"
@".str.10" = private constant [13 x i8] c": option '--\00"
@".str.11" = private constant [20 x i8] c"' requires a value\0a\00"
@".str.12" = private constant [20 x i8] c": unknown option '-\00"
@".str.13" = private constant [3 x i8] c"'\0a\00"
@".str.14" = private constant [2 x i8] c"1\00"
@".str.15" = private constant [12 x i8] c": option '-\00"
@".str.16" = private constant [20 x i8] c"' requires a value\0a\00"
@".str.17" = private constant [30 x i8] c": missing required argument '\00"
@".str.18" = private constant [3 x i8] c"'\0a\00"
@".str.19" = private constant [22 x i8] c": too many arguments\0a\00"
@".str.20" = private constant [2 x i8] c"1\00"
@".str.21" = private constant [2 x i8] c"1\00"
@".str.22" = private constant [8 x i8] c"Usage: \00"
@".str.23" = private constant [11 x i8] c" [OPTIONS]\00"
@".str.24" = private constant [2 x i8] c" \00"
@".str.25" = private constant [2 x i8] c"[\00"
@".str.26" = private constant [4 x i8] c"...\00"
@".str.27" = private constant [2 x i8] c"]\00"
@".str.28" = private constant [2 x i8] c"\0a\00"
@".str.29" = private constant [2 x i8] c"\0a\00"
@".str.30" = private constant [2 x i8] c"\0a\00"
@".str.31" = private constant [11 x i8] c"\0aOptions:\0a\00"
@".str.32" = private constant [3 x i8] c"  \00"
@".str.33" = private constant [2 x i8] c"-\00"
@".str.34" = private constant [3 x i8] c", \00"
@".str.35" = private constant [5 x i8] c"    \00"
@".str.36" = private constant [3 x i8] c"--\00"
@".str.37" = private constant [2 x i8] c"=\00"
@".str.38" = private constant [10 x i8] c"\0a        \00"
@".str.39" = private constant [12 x i8] c" (default: \00"
@".str.40" = private constant [2 x i8] c")\00"
@".str.41" = private constant [2 x i8] c"\0a\00"
@".str.42" = private constant [13 x i8] c"\0aArguments:\0a\00"
@".str.43" = private constant [3 x i8] c"  \00"
@".str.44" = private constant [10 x i8] c"\0a        \00"
@".str.45" = private constant [2 x i8] c"\0a\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/ritzunit/ritz/ritzlib", filename: "args.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 78, name: "args_init", scopeLine: 78, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 90, name: "args_flag", scopeLine: 90, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 105, name: "args_option", scopeLine: 105, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 120, name: "args_positional", scopeLine: 120, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 135, name: "find_option_short", scopeLine: 135, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 141, name: "find_option_long", scopeLine: 141, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 152, name: "args_parse", scopeLine: 152, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 304, name: "args_get_flag", scopeLine: 304, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 310, name: "args_get_flag_long", scopeLine: 310, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 316, name: "args_get_str", scopeLine: 316, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 322, name: "args_get_str_long", scopeLine: 322, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 328, name: "args_get_int", scopeLine: 328, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 334, name: "args_get_int_long", scopeLine: 334, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 340, name: "args_get_positional", scopeLine: 340, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 345, name: "args_is_set", scopeLine: 345, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 351, name: "args_is_set_long", scopeLine: 351, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 361, name: "args_print_usage", scopeLine: 361, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 378, name: "args_print_help", scopeLine: 378, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!49 = !DICompositeType(align: 64, file: !0, name: "ArgParser", size: 32640, tag: DW_TAG_structure_type)
!50 = !DIDerivedType(baseType: !49, size: 64, tag: DW_TAG_pointer_type)
!51 = !DILocalVariable(file: !0, line: 78, name: "parser", scope: !17, type: !50)
!52 = !DILocation(column: 1, line: 78, scope: !17)
!53 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!54 = !DILocalVariable(file: !0, line: 78, name: "program", scope: !17, type: !53)
!55 = !DILocalVariable(file: !0, line: 78, name: "desc", scope: !17, type: !53)
!56 = !DILocation(column: 5, line: 79, scope: !17)
!57 = !DILocation(column: 5, line: 80, scope: !17)
!58 = !DILocation(column: 5, line: 81, scope: !17)
!59 = !DILocation(column: 5, line: 82, scope: !17)
!60 = !DILocation(column: 5, line: 83, scope: !17)
!61 = !DILocation(column: 5, line: 84, scope: !17)
!62 = !DILocalVariable(file: !0, line: 90, name: "parser", scope: !18, type: !50)
!63 = !DILocation(column: 1, line: 90, scope: !18)
!64 = !DILocalVariable(file: !0, line: 90, name: "short", scope: !18, type: !12)
!65 = !DILocalVariable(file: !0, line: 90, name: "long", scope: !18, type: !53)
!66 = !DILocalVariable(file: !0, line: 90, name: "desc", scope: !18, type: !53)
!67 = !DILocation(column: 5, line: 91, scope: !18)
!68 = !DILocation(column: 9, line: 92, scope: !18)
!69 = !DILocation(column: 5, line: 94, scope: !18)
!70 = !DILocation(column: 5, line: 95, scope: !18)
!71 = !DILocation(column: 5, line: 96, scope: !18)
!72 = !DILocation(column: 5, line: 97, scope: !18)
!73 = !DILocation(column: 5, line: 98, scope: !18)
!74 = !DILocation(column: 5, line: 99, scope: !18)
!75 = !DILocation(column: 5, line: 100, scope: !18)
!76 = !DILocation(column: 5, line: 101, scope: !18)
!77 = !DILocation(column: 5, line: 102, scope: !18)
!78 = !DILocation(column: 5, line: 103, scope: !18)
!79 = !DILocalVariable(file: !0, line: 105, name: "parser", scope: !19, type: !50)
!80 = !DILocation(column: 1, line: 105, scope: !19)
!81 = !DILocalVariable(file: !0, line: 105, name: "short", scope: !19, type: !12)
!82 = !DILocalVariable(file: !0, line: 105, name: "long", scope: !19, type: !53)
!83 = !DILocalVariable(file: !0, line: 105, name: "value_name", scope: !19, type: !53)
!84 = !DILocalVariable(file: !0, line: 105, name: "desc", scope: !19, type: !53)
!85 = !DILocalVariable(file: !0, line: 105, name: "default", scope: !19, type: !53)
!86 = !DILocation(column: 5, line: 106, scope: !19)
!87 = !DILocation(column: 9, line: 107, scope: !19)
!88 = !DILocation(column: 5, line: 109, scope: !19)
!89 = !DILocation(column: 5, line: 110, scope: !19)
!90 = !DILocation(column: 5, line: 111, scope: !19)
!91 = !DILocation(column: 5, line: 112, scope: !19)
!92 = !DILocation(column: 5, line: 113, scope: !19)
!93 = !DILocation(column: 5, line: 114, scope: !19)
!94 = !DILocation(column: 5, line: 115, scope: !19)
!95 = !DILocation(column: 5, line: 116, scope: !19)
!96 = !DILocation(column: 5, line: 117, scope: !19)
!97 = !DILocation(column: 5, line: 118, scope: !19)
!98 = !DILocalVariable(file: !0, line: 120, name: "parser", scope: !20, type: !50)
!99 = !DILocation(column: 1, line: 120, scope: !20)
!100 = !DILocalVariable(file: !0, line: 120, name: "name", scope: !20, type: !53)
!101 = !DILocalVariable(file: !0, line: 120, name: "desc", scope: !20, type: !53)
!102 = !DILocalVariable(file: !0, line: 120, name: "min", scope: !20, type: !10)
!103 = !DILocalVariable(file: !0, line: 120, name: "max", scope: !20, type: !10)
!104 = !DILocation(column: 5, line: 121, scope: !20)
!105 = !DILocation(column: 9, line: 122, scope: !20)
!106 = !DILocation(column: 5, line: 124, scope: !20)
!107 = !DILocation(column: 5, line: 125, scope: !20)
!108 = !DILocation(column: 5, line: 126, scope: !20)
!109 = !DILocation(column: 5, line: 127, scope: !20)
!110 = !DILocation(column: 5, line: 128, scope: !20)
!111 = !DILocation(column: 5, line: 129, scope: !20)
!112 = !DILocalVariable(file: !0, line: 135, name: "parser", scope: !21, type: !50)
!113 = !DILocation(column: 1, line: 135, scope: !21)
!114 = !DILocalVariable(file: !0, line: 135, name: "short", scope: !21, type: !12)
!115 = !DILocation(column: 5, line: 136, scope: !21)
!116 = !DILocation(column: 13, line: 138, scope: !21)
!117 = !DILocation(column: 5, line: 139, scope: !21)
!118 = !DILocalVariable(file: !0, line: 141, name: "parser", scope: !22, type: !50)
!119 = !DILocation(column: 1, line: 141, scope: !22)
!120 = !DILocalVariable(file: !0, line: 141, name: "long", scope: !22, type: !53)
!121 = !DILocation(column: 5, line: 142, scope: !22)
!122 = !DILocation(column: 17, line: 145, scope: !22)
!123 = !DILocation(column: 5, line: 146, scope: !22)
!124 = !DILocalVariable(file: !0, line: 152, name: "parser", scope: !23, type: !50)
!125 = !DILocation(column: 1, line: 152, scope: !23)
!126 = !DILocalVariable(file: !0, line: 152, name: "argc", scope: !23, type: !10)
!127 = !DIDerivedType(baseType: !53, size: 64, tag: DW_TAG_pointer_type)
!128 = !DILocalVariable(file: !0, line: 152, name: "argv", scope: !23, type: !127)
!129 = !DILocation(column: 5, line: 153, scope: !23)
!130 = !DILocalVariable(file: !0, line: 153, name: "i", scope: !23, type: !10)
!131 = !DILocation(column: 1, line: 153, scope: !23)
!132 = !DILocation(column: 5, line: 154, scope: !23)
!133 = !DILocalVariable(file: !0, line: 154, name: "stop_options", scope: !23, type: !10)
!134 = !DILocation(column: 1, line: 154, scope: !23)
!135 = !DILocation(column: 5, line: 156, scope: !23)
!136 = !DILocation(column: 9, line: 157, scope: !23)
!137 = !DILocation(column: 9, line: 160, scope: !23)
!138 = !DILocation(column: 13, line: 161, scope: !23)
!139 = !DILocation(column: 13, line: 162, scope: !23)
!140 = !DILocation(column: 13, line: 163, scope: !23)
!141 = !DILocation(column: 9, line: 166, scope: !23)
!142 = !DILocation(column: 13, line: 168, scope: !23)
!143 = !DILocation(column: 13, line: 171, scope: !23)
!144 = !DILocalVariable(file: !0, line: 171, name: "eq_pos", scope: !23, type: !11)
!145 = !DILocation(column: 1, line: 171, scope: !23)
!146 = !DILocation(column: 13, line: 172, scope: !23)
!147 = !DILocalVariable(file: !0, line: 172, name: "j", scope: !23, type: !11)
!148 = !DILocation(column: 1, line: 172, scope: !23)
!149 = !DILocation(column: 13, line: 173, scope: !23)
!150 = !DILocation(column: 17, line: 174, scope: !23)
!151 = !DILocation(column: 21, line: 175, scope: !23)
!152 = !DILocation(column: 21, line: 176, scope: !23)
!153 = !DILocation(column: 17, line: 177, scope: !23)
!154 = !DILocation(column: 13, line: 179, scope: !23)
!155 = !DILocation(column: 17, line: 181, scope: !23)
!156 = !DISubrange(count: 64)
!157 = !{ !156 }
!158 = !DICompositeType(baseType: !12, elements: !157, size: 512, tag: DW_TAG_array_type)
!159 = !DILocalVariable(file: !0, line: 181, name: "opt_name", scope: !23, type: !158)
!160 = !DILocation(column: 1, line: 181, scope: !23)
!161 = !DILocation(column: 17, line: 182, scope: !23)
!162 = !DILocalVariable(file: !0, line: 182, name: "k", scope: !23, type: !11)
!163 = !DILocation(column: 1, line: 182, scope: !23)
!164 = !DILocation(column: 17, line: 183, scope: !23)
!165 = !DILocation(column: 21, line: 184, scope: !23)
!166 = !DILocation(column: 21, line: 185, scope: !23)
!167 = !DILocation(column: 17, line: 186, scope: !23)
!168 = !DILocation(column: 17, line: 188, scope: !23)
!169 = !DILocation(column: 17, line: 189, scope: !23)
!170 = !DILocation(column: 21, line: 190, scope: !23)
!171 = !DILocation(column: 21, line: 191, scope: !23)
!172 = !DILocation(column: 21, line: 192, scope: !23)
!173 = !DILocation(column: 21, line: 193, scope: !23)
!174 = !DILocation(column: 21, line: 194, scope: !23)
!175 = !DILocation(column: 17, line: 196, scope: !23)
!176 = !DILocation(column: 21, line: 197, scope: !23)
!177 = !DILocation(column: 21, line: 198, scope: !23)
!178 = !DILocation(column: 21, line: 199, scope: !23)
!179 = !DILocation(column: 21, line: 200, scope: !23)
!180 = !DILocation(column: 21, line: 201, scope: !23)
!181 = !DILocation(column: 17, line: 203, scope: !23)
!182 = !DILocation(column: 17, line: 204, scope: !23)
!183 = !DILocation(column: 17, line: 207, scope: !23)
!184 = !DILocation(column: 17, line: 208, scope: !23)
!185 = !DILocation(column: 21, line: 209, scope: !23)
!186 = !DILocation(column: 21, line: 210, scope: !23)
!187 = !DILocation(column: 21, line: 211, scope: !23)
!188 = !DILocation(column: 21, line: 212, scope: !23)
!189 = !DILocation(column: 21, line: 213, scope: !23)
!190 = !DILocation(column: 21, line: 216, scope: !23)
!191 = !DILocation(column: 21, line: 217, scope: !23)
!192 = !DILocation(column: 21, line: 220, scope: !23)
!193 = !DILocation(column: 21, line: 221, scope: !23)
!194 = !DILocation(column: 25, line: 222, scope: !23)
!195 = !DILocation(column: 25, line: 223, scope: !23)
!196 = !DILocation(column: 25, line: 224, scope: !23)
!197 = !DILocation(column: 25, line: 225, scope: !23)
!198 = !DILocation(column: 25, line: 226, scope: !23)
!199 = !DILocation(column: 21, line: 227, scope: !23)
!200 = !DILocation(column: 21, line: 228, scope: !23)
!201 = !DILocation(column: 13, line: 230, scope: !23)
!202 = !DILocation(column: 13, line: 231, scope: !23)
!203 = !DILocation(column: 9, line: 234, scope: !23)
!204 = !DILocation(column: 13, line: 236, scope: !23)
!205 = !DILocalVariable(file: !0, line: 236, name: "j", scope: !23, type: !10)
!206 = !DILocation(column: 1, line: 236, scope: !23)
!207 = !DILocation(column: 13, line: 237, scope: !23)
!208 = !DILocation(column: 17, line: 238, scope: !23)
!209 = !DILocation(column: 17, line: 239, scope: !23)
!210 = !DILocation(column: 17, line: 241, scope: !23)
!211 = !DILocation(column: 21, line: 242, scope: !23)
!212 = !DILocation(column: 21, line: 243, scope: !23)
!213 = !DILocation(column: 21, line: 244, scope: !23)
!214 = !DILocation(column: 21, line: 245, scope: !23)
!215 = !DILocation(column: 21, line: 246, scope: !23)
!216 = !DILocation(column: 21, line: 249, scope: !23)
!217 = !DILocation(column: 21, line: 250, scope: !23)
!218 = !DILocation(column: 21, line: 251, scope: !23)
!219 = !DILocation(column: 25, line: 256, scope: !23)
!220 = !DILocation(column: 25, line: 257, scope: !23)
!221 = !DILocation(column: 25, line: 258, scope: !23)
!222 = !DILocation(column: 25, line: 261, scope: !23)
!223 = !DILocation(column: 25, line: 262, scope: !23)
!224 = !DILocation(column: 29, line: 263, scope: !23)
!225 = !DILocation(column: 29, line: 264, scope: !23)
!226 = !DILocation(column: 29, line: 265, scope: !23)
!227 = !DILocation(column: 29, line: 266, scope: !23)
!228 = !DILocation(column: 29, line: 267, scope: !23)
!229 = !DILocation(column: 25, line: 268, scope: !23)
!230 = !DILocation(column: 25, line: 269, scope: !23)
!231 = !DILocation(column: 25, line: 270, scope: !23)
!232 = !DILocation(column: 13, line: 272, scope: !23)
!233 = !DILocation(column: 13, line: 273, scope: !23)
!234 = !DILocation(column: 9, line: 276, scope: !23)
!235 = !DILocation(column: 13, line: 277, scope: !23)
!236 = !DILocation(column: 13, line: 278, scope: !23)
!237 = !DILocation(column: 9, line: 280, scope: !23)
!238 = !DILocation(column: 5, line: 283, scope: !23)
!239 = !DILocation(column: 9, line: 285, scope: !23)
!240 = !DILocation(column: 9, line: 286, scope: !23)
!241 = !DILocation(column: 9, line: 287, scope: !23)
!242 = !DILocation(column: 13, line: 288, scope: !23)
!243 = !DILocation(column: 13, line: 289, scope: !23)
!244 = !DILocation(column: 13, line: 290, scope: !23)
!245 = !DILocation(column: 13, line: 291, scope: !23)
!246 = !DILocation(column: 13, line: 292, scope: !23)
!247 = !DILocation(column: 13, line: 294, scope: !23)
!248 = !DILocation(column: 13, line: 295, scope: !23)
!249 = !DILocation(column: 13, line: 296, scope: !23)
!250 = !DILocation(column: 5, line: 298, scope: !23)
!251 = !DILocalVariable(file: !0, line: 304, name: "parser", scope: !24, type: !50)
!252 = !DILocation(column: 1, line: 304, scope: !24)
!253 = !DILocalVariable(file: !0, line: 304, name: "short", scope: !24, type: !12)
!254 = !DILocation(column: 5, line: 305, scope: !24)
!255 = !DILocation(column: 5, line: 306, scope: !24)
!256 = !DILocation(column: 9, line: 307, scope: !24)
!257 = !DILocation(column: 5, line: 308, scope: !24)
!258 = !DILocalVariable(file: !0, line: 310, name: "parser", scope: !25, type: !50)
!259 = !DILocation(column: 1, line: 310, scope: !25)
!260 = !DILocalVariable(file: !0, line: 310, name: "long", scope: !25, type: !53)
!261 = !DILocation(column: 5, line: 311, scope: !25)
!262 = !DILocation(column: 5, line: 312, scope: !25)
!263 = !DILocation(column: 9, line: 313, scope: !25)
!264 = !DILocation(column: 5, line: 314, scope: !25)
!265 = !DILocalVariable(file: !0, line: 316, name: "parser", scope: !26, type: !50)
!266 = !DILocation(column: 1, line: 316, scope: !26)
!267 = !DILocalVariable(file: !0, line: 316, name: "short", scope: !26, type: !12)
!268 = !DILocation(column: 5, line: 317, scope: !26)
!269 = !DILocation(column: 5, line: 318, scope: !26)
!270 = !DILocation(column: 9, line: 319, scope: !26)
!271 = !DILocation(column: 5, line: 320, scope: !26)
!272 = !DILocalVariable(file: !0, line: 322, name: "parser", scope: !27, type: !50)
!273 = !DILocation(column: 1, line: 322, scope: !27)
!274 = !DILocalVariable(file: !0, line: 322, name: "long", scope: !27, type: !53)
!275 = !DILocation(column: 5, line: 323, scope: !27)
!276 = !DILocation(column: 5, line: 324, scope: !27)
!277 = !DILocation(column: 9, line: 325, scope: !27)
!278 = !DILocation(column: 5, line: 326, scope: !27)
!279 = !DILocalVariable(file: !0, line: 328, name: "parser", scope: !28, type: !50)
!280 = !DILocation(column: 1, line: 328, scope: !28)
!281 = !DILocalVariable(file: !0, line: 328, name: "short", scope: !28, type: !12)
!282 = !DILocation(column: 5, line: 329, scope: !28)
!283 = !DILocation(column: 5, line: 330, scope: !28)
!284 = !DILocation(column: 9, line: 331, scope: !28)
!285 = !DILocation(column: 5, line: 332, scope: !28)
!286 = !DILocalVariable(file: !0, line: 334, name: "parser", scope: !29, type: !50)
!287 = !DILocation(column: 1, line: 334, scope: !29)
!288 = !DILocalVariable(file: !0, line: 334, name: "long", scope: !29, type: !53)
!289 = !DILocation(column: 5, line: 335, scope: !29)
!290 = !DILocation(column: 5, line: 336, scope: !29)
!291 = !DILocation(column: 9, line: 337, scope: !29)
!292 = !DILocation(column: 5, line: 338, scope: !29)
!293 = !DILocalVariable(file: !0, line: 340, name: "parser", scope: !30, type: !50)
!294 = !DILocation(column: 1, line: 340, scope: !30)
!295 = !DILocalVariable(file: !0, line: 340, name: "idx", scope: !30, type: !10)
!296 = !DILocation(column: 5, line: 341, scope: !30)
!297 = !DILocation(column: 9, line: 342, scope: !30)
!298 = !DILocation(column: 5, line: 343, scope: !30)
!299 = !DILocalVariable(file: !0, line: 345, name: "parser", scope: !31, type: !50)
!300 = !DILocation(column: 1, line: 345, scope: !31)
!301 = !DILocalVariable(file: !0, line: 345, name: "short", scope: !31, type: !12)
!302 = !DILocation(column: 5, line: 346, scope: !31)
!303 = !DILocation(column: 5, line: 347, scope: !31)
!304 = !DILocation(column: 9, line: 348, scope: !31)
!305 = !DILocation(column: 5, line: 349, scope: !31)
!306 = !DILocalVariable(file: !0, line: 351, name: "parser", scope: !32, type: !50)
!307 = !DILocation(column: 1, line: 351, scope: !32)
!308 = !DILocalVariable(file: !0, line: 351, name: "long", scope: !32, type: !53)
!309 = !DILocation(column: 5, line: 352, scope: !32)
!310 = !DILocation(column: 5, line: 353, scope: !32)
!311 = !DILocation(column: 9, line: 354, scope: !32)
!312 = !DILocation(column: 5, line: 355, scope: !32)
!313 = !DILocalVariable(file: !0, line: 361, name: "parser", scope: !33, type: !50)
!314 = !DILocation(column: 1, line: 361, scope: !33)
!315 = !DILocation(column: 5, line: 362, scope: !33)
!316 = !DILocation(column: 5, line: 363, scope: !33)
!317 = !DILocation(column: 5, line: 364, scope: !33)
!318 = !DILocation(column: 5, line: 366, scope: !33)
!319 = !DILocation(column: 9, line: 367, scope: !33)
!320 = !DILocation(column: 9, line: 368, scope: !33)
!321 = !DILocation(column: 9, line: 370, scope: !33)
!322 = !DILocation(column: 9, line: 371, scope: !33)
!323 = !DILocation(column: 5, line: 376, scope: !33)
!324 = !DILocalVariable(file: !0, line: 378, name: "parser", scope: !34, type: !50)
!325 = !DILocation(column: 1, line: 378, scope: !34)
!326 = !DILocation(column: 5, line: 379, scope: !34)
!327 = !DILocation(column: 5, line: 381, scope: !34)
!328 = !DILocation(column: 9, line: 382, scope: !34)
!329 = !DILocation(column: 9, line: 383, scope: !34)
!330 = !DILocation(column: 5, line: 386, scope: !34)
!331 = !DILocation(column: 9, line: 387, scope: !34)
!332 = !DILocation(column: 9, line: 388, scope: !34)
!333 = !DILocation(column: 13, line: 389, scope: !34)
!334 = !DILocation(column: 13, line: 391, scope: !34)
!335 = !DILocation(column: 17, line: 392, scope: !34)
!336 = !DILocation(column: 17, line: 393, scope: !34)
!337 = !DILocation(column: 13, line: 399, scope: !34)
!338 = !DILocation(column: 17, line: 400, scope: !34)
!339 = !DILocation(column: 17, line: 401, scope: !34)
!340 = !DILocation(column: 21, line: 403, scope: !34)
!341 = !DILocation(column: 13, line: 406, scope: !34)
!342 = !DILocation(column: 13, line: 407, scope: !34)
!343 = !DILocation(column: 13, line: 409, scope: !34)
!344 = !DILocation(column: 21, line: 411, scope: !34)
!345 = !DILocation(column: 21, line: 412, scope: !34)
!346 = !DILocation(column: 5, line: 417, scope: !34)
!347 = !DILocation(column: 9, line: 418, scope: !34)
!348 = !DILocation(column: 9, line: 419, scope: !34)
!349 = !DILocation(column: 13, line: 420, scope: !34)
!350 = !DILocation(column: 13, line: 421, scope: !34)
!351 = !DILocation(column: 13, line: 422, scope: !34)
!352 = !DILocation(column: 13, line: 423, scope: !34)
!353 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!354 = !DIDerivedType(baseType: !353, size: 64, tag: DW_TAG_reference_type)
!355 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !35, type: !354)
!356 = !DILocation(column: 1, line: 210, scope: !35)
!357 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!358 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !35, type: !357)
!359 = !DILocation(column: 5, line: 211, scope: !35)
!360 = !DILocation(column: 9, line: 212, scope: !35)
!361 = !DILocation(column: 5, line: 213, scope: !35)
!362 = !DILocation(column: 5, line: 214, scope: !35)
!363 = !DILocation(column: 5, line: 215, scope: !35)
!364 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!365 = !DIDerivedType(baseType: !364, size: 64, tag: DW_TAG_reference_type)
!366 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !36, type: !365)
!367 = !DILocation(column: 1, line: 148, scope: !36)
!368 = !DILocation(column: 5, line: 149, scope: !36)
!369 = !DILocation(column: 5, line: 151, scope: !36)
!370 = !DILocation(column: 5, line: 152, scope: !36)
!371 = !DILocation(column: 5, line: 153, scope: !36)
!372 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !37, type: !365)
!373 = !DILocation(column: 1, line: 235, scope: !37)
!374 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !37, type: !11)
!375 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !37, type: !12)
!376 = !DILocation(column: 5, line: 236, scope: !37)
!377 = !DILocation(column: 5, line: 237, scope: !37)
!378 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !38, type: !365)
!379 = !DILocation(column: 1, line: 225, scope: !38)
!380 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !38, type: !11)
!381 = !DILocation(column: 5, line: 226, scope: !38)
!382 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !39, type: !365)
!383 = !DILocation(column: 1, line: 219, scope: !39)
!384 = !DILocation(column: 5, line: 220, scope: !39)
!385 = !DILocation(column: 5, line: 221, scope: !39)
!386 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !40, type: !365)
!387 = !DILocation(column: 1, line: 288, scope: !40)
!388 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !40, type: !53)
!389 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !40, type: !11)
!390 = !DILocation(column: 5, line: 289, scope: !40)
!391 = !DILocation(column: 13, line: 291, scope: !40)
!392 = !DILocation(column: 5, line: 292, scope: !40)
!393 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !41, type: !365)
!394 = !DILocation(column: 1, line: 244, scope: !41)
!395 = !DILocation(column: 5, line: 245, scope: !41)
!396 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !42, type: !365)
!397 = !DILocation(column: 1, line: 193, scope: !42)
!398 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !42, type: !11)
!399 = !DILocation(column: 5, line: 194, scope: !42)
!400 = !DILocation(column: 9, line: 195, scope: !42)
!401 = !DILocation(column: 5, line: 197, scope: !42)
!402 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !42, type: !11)
!403 = !DILocation(column: 1, line: 197, scope: !42)
!404 = !DILocation(column: 5, line: 198, scope: !42)
!405 = !DILocation(column: 9, line: 199, scope: !42)
!406 = !DILocation(column: 5, line: 200, scope: !42)
!407 = !DILocation(column: 9, line: 201, scope: !42)
!408 = !DILocation(column: 5, line: 203, scope: !42)
!409 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !43, type: !11)
!410 = !DILocation(column: 1, line: 124, scope: !43)
!411 = !DILocation(column: 5, line: 125, scope: !43)
!412 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !43, type: !364)
!413 = !DILocation(column: 1, line: 125, scope: !43)
!414 = !DILocation(column: 5, line: 126, scope: !43)
!415 = !DILocation(column: 9, line: 127, scope: !43)
!416 = !DILocation(column: 9, line: 128, scope: !43)
!417 = !DILocation(column: 9, line: 129, scope: !43)
!418 = !DILocation(column: 9, line: 130, scope: !43)
!419 = !DILocation(column: 5, line: 132, scope: !43)
!420 = !DILocation(column: 5, line: 133, scope: !43)
!421 = !DILocation(column: 5, line: 134, scope: !43)
!422 = !DILocation(column: 9, line: 135, scope: !43)
!423 = !DILocation(column: 9, line: 136, scope: !43)
!424 = !DILocation(column: 9, line: 137, scope: !43)
!425 = !DILocation(column: 5, line: 139, scope: !43)
!426 = !DILocation(column: 5, line: 140, scope: !43)
!427 = !DILocation(column: 5, line: 141, scope: !43)
!428 = !DILocation(column: 5, line: 117, scope: !44)
!429 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !44, type: !364)
!430 = !DILocation(column: 1, line: 117, scope: !44)
!431 = !DILocation(column: 5, line: 118, scope: !44)
!432 = !DILocation(column: 5, line: 119, scope: !44)
!433 = !DILocation(column: 5, line: 120, scope: !44)
!434 = !DILocation(column: 5, line: 121, scope: !44)
!435 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !45, type: !365)
!436 = !DILocation(column: 1, line: 210, scope: !45)
!437 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !45, type: !12)
!438 = !DILocation(column: 5, line: 211, scope: !45)
!439 = !DILocation(column: 9, line: 212, scope: !45)
!440 = !DILocation(column: 5, line: 213, scope: !45)
!441 = !DILocation(column: 5, line: 214, scope: !45)
!442 = !DILocation(column: 5, line: 215, scope: !45)
!443 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !46, type: !354)
!444 = !DILocation(column: 1, line: 193, scope: !46)
!445 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !46, type: !11)
!446 = !DILocation(column: 5, line: 194, scope: !46)
!447 = !DILocation(column: 9, line: 195, scope: !46)
!448 = !DILocation(column: 5, line: 197, scope: !46)
!449 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !46, type: !11)
!450 = !DILocation(column: 1, line: 197, scope: !46)
!451 = !DILocation(column: 5, line: 198, scope: !46)
!452 = !DILocation(column: 9, line: 199, scope: !46)
!453 = !DILocation(column: 5, line: 200, scope: !46)
!454 = !DILocation(column: 9, line: 201, scope: !46)
!455 = !DILocation(column: 5, line: 203, scope: !46)
!456 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !47, type: !365)
!457 = !DILocation(column: 1, line: 179, scope: !47)
!458 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !47, type: !11)
!459 = !DILocation(column: 5, line: 180, scope: !47)
!460 = !DILocation(column: 9, line: 181, scope: !47)
!461 = !DILocation(column: 5, line: 183, scope: !47)
!462 = !DILocation(column: 5, line: 184, scope: !47)
!463 = !DILocation(column: 5, line: 185, scope: !47)
!464 = !DILocation(column: 9, line: 186, scope: !47)
!465 = !DILocation(column: 5, line: 188, scope: !47)
!466 = !DILocation(column: 5, line: 189, scope: !47)
!467 = !DILocation(column: 5, line: 190, scope: !47)
!468 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !48, type: !354)
!469 = !DILocation(column: 1, line: 179, scope: !48)
!470 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !48, type: !11)
!471 = !DILocation(column: 5, line: 180, scope: !48)
!472 = !DILocation(column: 9, line: 181, scope: !48)
!473 = !DILocation(column: 5, line: 183, scope: !48)
!474 = !DILocation(column: 5, line: 184, scope: !48)
!475 = !DILocation(column: 5, line: 185, scope: !48)
!476 = !DILocation(column: 9, line: 186, scope: !48)
!477 = !DILocation(column: 5, line: 188, scope: !48)
!478 = !DILocation(column: 5, line: 189, scope: !48)
!479 = !DILocation(column: 5, line: 190, scope: !48)