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
declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

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

declare i32 @"mem_zero"(i8* %".1", i64 %".2")

declare i32 @"mem_eq"(i8* %".1", i8* %".2", i64 %".3")

declare i32 @"mem_copy"(i8* %".1", i8* %".2", i64 %".3")

declare i8 @"ct_select_u8"(i8 %".1", i8 %".2", i32 %".3")

declare i64 @"ct_select_u64"(i64 %".1", i64 %".2", i32 %".3")

declare i32 @"ct_is_zero_u64"(i64 %".1")

declare i32 @"mem_is_zero"(i8* %".1", i64 %".2")

define internal i32 @"test_mem_zero_basic"() !dbg !17
{
entry:
  %"buf.addr" = alloca [16 x i8], !dbg !52
  call void @"llvm.dbg.declare"(metadata [16 x i8]* %"buf.addr", metadata !56, metadata !7), !dbg !57
  %".3" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !58
  %".4" = trunc i64 170 to i8 , !dbg !58
  store i8 %".4", i8* %".3", !dbg !58
  %".6" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 1 , !dbg !59
  %".7" = trunc i64 187 to i8 , !dbg !59
  store i8 %".7", i8* %".6", !dbg !59
  %".9" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 15 , !dbg !60
  %".10" = trunc i64 255 to i8 , !dbg !60
  store i8 %".10", i8* %".9", !dbg !60
  %".12" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !61
  %".13" = call i32 @"mem_zero"(i8* %".12", i64 16), !dbg !61
  %".14" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !62
  %".15" = load i8, i8* %".14", !dbg !62
  %".16" = zext i8 %".15" to i64 , !dbg !62
  %".17" = icmp eq i64 %".16", 0 , !dbg !62
  br i1 %".17", label %"assert.pass", label %"assert.fail", !dbg !62
assert.pass:
  %".21" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 1 , !dbg !63
  %".22" = load i8, i8* %".21", !dbg !63
  %".23" = zext i8 %".22" to i64 , !dbg !63
  %".24" = icmp eq i64 %".23", 0 , !dbg !63
  br i1 %".24", label %"assert.pass.1", label %"assert.fail.1", !dbg !63
assert.fail:
  %".19" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !62
  unreachable
assert.pass.1:
  %".28" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 15 , !dbg !64
  %".29" = load i8, i8* %".28", !dbg !64
  %".30" = zext i8 %".29" to i64 , !dbg !64
  %".31" = icmp eq i64 %".30", 0 , !dbg !64
  br i1 %".31", label %"assert.pass.2", label %"assert.fail.2", !dbg !64
assert.fail.1:
  %".26" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !63
  unreachable
assert.pass.2:
  %".35" = trunc i64 0 to i32 , !dbg !65
  ret i32 %".35", !dbg !65
assert.fail.2:
  %".33" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !64
  unreachable
}

define internal i32 @"test_mem_zero_partial"() !dbg !18
{
entry:
  %"buf.addr" = alloca [16 x i8], !dbg !66
  %"i" = alloca i64, !dbg !69
  call void @"llvm.dbg.declare"(metadata [16 x i8]* %"buf.addr", metadata !67, metadata !7), !dbg !68
  store i64 0, i64* %"i", !dbg !69
  br label %"for.cond", !dbg !69
for.cond:
  %".5" = load i64, i64* %"i", !dbg !69
  %".6" = icmp slt i64 %".5", 16 , !dbg !69
  br i1 %".6", label %"for.body", label %"for.end", !dbg !69
for.body:
  %".8" = load i64, i64* %"i", !dbg !70
  %".9" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 %".8" , !dbg !70
  %".10" = trunc i64 255 to i8 , !dbg !70
  store i8 %".10", i8* %".9", !dbg !70
  br label %"for.incr", !dbg !70
for.incr:
  %".13" = load i64, i64* %"i", !dbg !70
  %".14" = add i64 %".13", 1, !dbg !70
  store i64 %".14", i64* %"i", !dbg !70
  br label %"for.cond", !dbg !70
for.end:
  %".17" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 4 , !dbg !71
  %".18" = call i32 @"mem_zero"(i8* %".17", i64 8), !dbg !71
  %".19" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !72
  %".20" = load i8, i8* %".19", !dbg !72
  %".21" = zext i8 %".20" to i64 , !dbg !72
  %".22" = icmp eq i64 %".21", 255 , !dbg !72
  br i1 %".22", label %"assert.pass", label %"assert.fail", !dbg !72
assert.pass:
  %".26" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 3 , !dbg !73
  %".27" = load i8, i8* %".26", !dbg !73
  %".28" = zext i8 %".27" to i64 , !dbg !73
  %".29" = icmp eq i64 %".28", 255 , !dbg !73
  br i1 %".29", label %"assert.pass.1", label %"assert.fail.1", !dbg !73
assert.fail:
  %".24" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !72
  unreachable
assert.pass.1:
  %".33" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 4 , !dbg !74
  %".34" = load i8, i8* %".33", !dbg !74
  %".35" = zext i8 %".34" to i64 , !dbg !74
  %".36" = icmp eq i64 %".35", 0 , !dbg !74
  br i1 %".36", label %"assert.pass.2", label %"assert.fail.2", !dbg !74
assert.fail.1:
  %".31" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !73
  unreachable
assert.pass.2:
  %".40" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 11 , !dbg !75
  %".41" = load i8, i8* %".40", !dbg !75
  %".42" = zext i8 %".41" to i64 , !dbg !75
  %".43" = icmp eq i64 %".42", 0 , !dbg !75
  br i1 %".43", label %"assert.pass.3", label %"assert.fail.3", !dbg !75
assert.fail.2:
  %".38" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !74
  unreachable
assert.pass.3:
  %".47" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 12 , !dbg !76
  %".48" = load i8, i8* %".47", !dbg !76
  %".49" = zext i8 %".48" to i64 , !dbg !76
  %".50" = icmp eq i64 %".49", 255 , !dbg !76
  br i1 %".50", label %"assert.pass.4", label %"assert.fail.4", !dbg !76
assert.fail.3:
  %".45" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !75
  unreachable
assert.pass.4:
  %".54" = trunc i64 0 to i32 , !dbg !77
  ret i32 %".54", !dbg !77
assert.fail.4:
  %".52" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !76
  unreachable
}

define internal i32 @"test_mem_zero_empty"() !dbg !19
{
entry:
  %"buf.addr" = alloca [4 x i8], !dbg !78
  call void @"llvm.dbg.declare"(metadata [4 x i8]* %"buf.addr", metadata !82, metadata !7), !dbg !83
  %".3" = getelementptr [4 x i8], [4 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !84
  %".4" = trunc i64 170 to i8 , !dbg !84
  store i8 %".4", i8* %".3", !dbg !84
  %".6" = getelementptr [4 x i8], [4 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !85
  %".7" = call i32 @"mem_zero"(i8* %".6", i64 0), !dbg !85
  %".8" = getelementptr [4 x i8], [4 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !86
  %".9" = load i8, i8* %".8", !dbg !86
  %".10" = zext i8 %".9" to i64 , !dbg !86
  %".11" = icmp eq i64 %".10", 170 , !dbg !86
  br i1 %".11", label %"assert.pass", label %"assert.fail", !dbg !86
assert.pass:
  %".15" = trunc i64 0 to i32 , !dbg !87
  ret i32 %".15", !dbg !87
assert.fail:
  %".13" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !86
  unreachable
}

define internal i32 @"test_mem_eq_equal"() !dbg !20
{
entry:
  %"a.addr" = alloca [8 x i8], !dbg !88
  %"b.addr" = alloca [8 x i8], !dbg !94
  %"i" = alloca i64, !dbg !97
  call void @"llvm.dbg.declare"(metadata [8 x i8]* %"a.addr", metadata !92, metadata !7), !dbg !93
  call void @"llvm.dbg.declare"(metadata [8 x i8]* %"b.addr", metadata !95, metadata !7), !dbg !96
  store i64 0, i64* %"i", !dbg !97
  br label %"for.cond", !dbg !97
for.cond:
  %".6" = load i64, i64* %"i", !dbg !97
  %".7" = icmp slt i64 %".6", 8 , !dbg !97
  br i1 %".7", label %"for.body", label %"for.end", !dbg !97
for.body:
  %".9" = load i64, i64* %"i", !dbg !98
  %".10" = trunc i64 %".9" to i8 , !dbg !98
  %".11" = load i64, i64* %"i", !dbg !98
  %".12" = getelementptr [8 x i8], [8 x i8]* %"a.addr", i32 0, i64 %".11" , !dbg !98
  store i8 %".10", i8* %".12", !dbg !98
  %".14" = load i64, i64* %"i", !dbg !99
  %".15" = trunc i64 %".14" to i8 , !dbg !99
  %".16" = load i64, i64* %"i", !dbg !99
  %".17" = getelementptr [8 x i8], [8 x i8]* %"b.addr", i32 0, i64 %".16" , !dbg !99
  store i8 %".15", i8* %".17", !dbg !99
  br label %"for.incr", !dbg !99
for.incr:
  %".20" = load i64, i64* %"i", !dbg !99
  %".21" = add i64 %".20", 1, !dbg !99
  store i64 %".21", i64* %"i", !dbg !99
  br label %"for.cond", !dbg !99
for.end:
  %".24" = getelementptr [8 x i8], [8 x i8]* %"a.addr", i32 0, i64 0 , !dbg !100
  %".25" = getelementptr [8 x i8], [8 x i8]* %"b.addr", i32 0, i64 0 , !dbg !100
  %".26" = call i32 @"mem_eq"(i8* %".24", i8* %".25", i64 8), !dbg !100
  %".27" = sext i32 %".26" to i64 , !dbg !101
  %".28" = icmp eq i64 %".27", 1 , !dbg !101
  br i1 %".28", label %"assert.pass", label %"assert.fail", !dbg !101
assert.pass:
  %".32" = trunc i64 0 to i32 , !dbg !102
  ret i32 %".32", !dbg !102
assert.fail:
  %".30" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !101
  unreachable
}

define internal i32 @"test_mem_eq_different"() !dbg !21
{
entry:
  %"a.addr" = alloca [8 x i8], !dbg !103
  %"b.addr" = alloca [8 x i8], !dbg !106
  %"i" = alloca i64, !dbg !109
  call void @"llvm.dbg.declare"(metadata [8 x i8]* %"a.addr", metadata !104, metadata !7), !dbg !105
  call void @"llvm.dbg.declare"(metadata [8 x i8]* %"b.addr", metadata !107, metadata !7), !dbg !108
  store i64 0, i64* %"i", !dbg !109
  br label %"for.cond", !dbg !109
for.cond:
  %".6" = load i64, i64* %"i", !dbg !109
  %".7" = icmp slt i64 %".6", 8 , !dbg !109
  br i1 %".7", label %"for.body", label %"for.end", !dbg !109
for.body:
  %".9" = load i64, i64* %"i", !dbg !110
  %".10" = trunc i64 %".9" to i8 , !dbg !110
  %".11" = load i64, i64* %"i", !dbg !110
  %".12" = getelementptr [8 x i8], [8 x i8]* %"a.addr", i32 0, i64 %".11" , !dbg !110
  store i8 %".10", i8* %".12", !dbg !110
  %".14" = load i64, i64* %"i", !dbg !111
  %".15" = trunc i64 %".14" to i8 , !dbg !111
  %".16" = load i64, i64* %"i", !dbg !111
  %".17" = getelementptr [8 x i8], [8 x i8]* %"b.addr", i32 0, i64 %".16" , !dbg !111
  store i8 %".15", i8* %".17", !dbg !111
  br label %"for.incr", !dbg !111
for.incr:
  %".20" = load i64, i64* %"i", !dbg !111
  %".21" = add i64 %".20", 1, !dbg !111
  store i64 %".21", i64* %"i", !dbg !111
  br label %"for.cond", !dbg !111
for.end:
  %".24" = getelementptr [8 x i8], [8 x i8]* %"b.addr", i32 0, i64 4 , !dbg !112
  %".25" = trunc i64 255 to i8 , !dbg !112
  store i8 %".25", i8* %".24", !dbg !112
  %".27" = getelementptr [8 x i8], [8 x i8]* %"a.addr", i32 0, i64 0 , !dbg !113
  %".28" = getelementptr [8 x i8], [8 x i8]* %"b.addr", i32 0, i64 0 , !dbg !113
  %".29" = call i32 @"mem_eq"(i8* %".27", i8* %".28", i64 8), !dbg !113
  %".30" = sext i32 %".29" to i64 , !dbg !114
  %".31" = icmp eq i64 %".30", 0 , !dbg !114
  br i1 %".31", label %"assert.pass", label %"assert.fail", !dbg !114
assert.pass:
  %".35" = trunc i64 0 to i32 , !dbg !115
  ret i32 %".35", !dbg !115
assert.fail:
  %".33" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !114
  unreachable
}

define internal i32 @"test_mem_eq_first_byte_differs"() !dbg !22
{
entry:
  %"a.addr" = alloca [4 x i8], !dbg !116
  %"b.addr" = alloca [4 x i8], !dbg !119
  %".2" = insertvalue [4 x i64] undef, i64 1, 0 , !dbg !116
  %".3" = insertvalue [4 x i64] %".2", i64 2, 1 , !dbg !116
  %".4" = insertvalue [4 x i64] %".3", i64 3, 2 , !dbg !116
  %".5" = insertvalue [4 x i64] %".4", i64 4, 3 , !dbg !116
  %".6" = extractvalue [4 x i64] %".5", 0 , !dbg !116
  %".7" = trunc i64 %".6" to i8 , !dbg !116
  %".8" = insertvalue [4 x i8] undef, i8 %".7", 0 , !dbg !116
  %".9" = extractvalue [4 x i64] %".5", 1 , !dbg !116
  %".10" = trunc i64 %".9" to i8 , !dbg !116
  %".11" = insertvalue [4 x i8] %".8", i8 %".10", 1 , !dbg !116
  %".12" = extractvalue [4 x i64] %".5", 2 , !dbg !116
  %".13" = trunc i64 %".12" to i8 , !dbg !116
  %".14" = insertvalue [4 x i8] %".11", i8 %".13", 2 , !dbg !116
  %".15" = extractvalue [4 x i64] %".5", 3 , !dbg !116
  %".16" = trunc i64 %".15" to i8 , !dbg !116
  %".17" = insertvalue [4 x i8] %".14", i8 %".16", 3 , !dbg !116
  store [4 x i8] %".17", [4 x i8]* %"a.addr", !dbg !116
  call void @"llvm.dbg.declare"(metadata [4 x i8]* %"a.addr", metadata !117, metadata !7), !dbg !118
  %".20" = insertvalue [4 x i64] undef, i64 0, 0 , !dbg !119
  %".21" = insertvalue [4 x i64] %".20", i64 2, 1 , !dbg !119
  %".22" = insertvalue [4 x i64] %".21", i64 3, 2 , !dbg !119
  %".23" = insertvalue [4 x i64] %".22", i64 4, 3 , !dbg !119
  %".24" = extractvalue [4 x i64] %".23", 0 , !dbg !119
  %".25" = trunc i64 %".24" to i8 , !dbg !119
  %".26" = insertvalue [4 x i8] undef, i8 %".25", 0 , !dbg !119
  %".27" = extractvalue [4 x i64] %".23", 1 , !dbg !119
  %".28" = trunc i64 %".27" to i8 , !dbg !119
  %".29" = insertvalue [4 x i8] %".26", i8 %".28", 1 , !dbg !119
  %".30" = extractvalue [4 x i64] %".23", 2 , !dbg !119
  %".31" = trunc i64 %".30" to i8 , !dbg !119
  %".32" = insertvalue [4 x i8] %".29", i8 %".31", 2 , !dbg !119
  %".33" = extractvalue [4 x i64] %".23", 3 , !dbg !119
  %".34" = trunc i64 %".33" to i8 , !dbg !119
  %".35" = insertvalue [4 x i8] %".32", i8 %".34", 3 , !dbg !119
  store [4 x i8] %".35", [4 x i8]* %"b.addr", !dbg !119
  call void @"llvm.dbg.declare"(metadata [4 x i8]* %"b.addr", metadata !120, metadata !7), !dbg !121
  %".38" = getelementptr [4 x i8], [4 x i8]* %"a.addr", i32 0, i64 0 , !dbg !122
  %".39" = getelementptr [4 x i8], [4 x i8]* %"b.addr", i32 0, i64 0 , !dbg !122
  %".40" = call i32 @"mem_eq"(i8* %".38", i8* %".39", i64 4), !dbg !122
  %".41" = sext i32 %".40" to i64 , !dbg !123
  %".42" = icmp eq i64 %".41", 0 , !dbg !123
  br i1 %".42", label %"assert.pass", label %"assert.fail", !dbg !123
assert.pass:
  %".46" = trunc i64 0 to i32 , !dbg !124
  ret i32 %".46", !dbg !124
assert.fail:
  %".44" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !123
  unreachable
}

define internal i32 @"test_mem_eq_last_byte_differs"() !dbg !23
{
entry:
  %"a.addr" = alloca [4 x i8], !dbg !125
  %"b.addr" = alloca [4 x i8], !dbg !128
  %".2" = insertvalue [4 x i64] undef, i64 1, 0 , !dbg !125
  %".3" = insertvalue [4 x i64] %".2", i64 2, 1 , !dbg !125
  %".4" = insertvalue [4 x i64] %".3", i64 3, 2 , !dbg !125
  %".5" = insertvalue [4 x i64] %".4", i64 4, 3 , !dbg !125
  %".6" = extractvalue [4 x i64] %".5", 0 , !dbg !125
  %".7" = trunc i64 %".6" to i8 , !dbg !125
  %".8" = insertvalue [4 x i8] undef, i8 %".7", 0 , !dbg !125
  %".9" = extractvalue [4 x i64] %".5", 1 , !dbg !125
  %".10" = trunc i64 %".9" to i8 , !dbg !125
  %".11" = insertvalue [4 x i8] %".8", i8 %".10", 1 , !dbg !125
  %".12" = extractvalue [4 x i64] %".5", 2 , !dbg !125
  %".13" = trunc i64 %".12" to i8 , !dbg !125
  %".14" = insertvalue [4 x i8] %".11", i8 %".13", 2 , !dbg !125
  %".15" = extractvalue [4 x i64] %".5", 3 , !dbg !125
  %".16" = trunc i64 %".15" to i8 , !dbg !125
  %".17" = insertvalue [4 x i8] %".14", i8 %".16", 3 , !dbg !125
  store [4 x i8] %".17", [4 x i8]* %"a.addr", !dbg !125
  call void @"llvm.dbg.declare"(metadata [4 x i8]* %"a.addr", metadata !126, metadata !7), !dbg !127
  %".20" = insertvalue [4 x i64] undef, i64 1, 0 , !dbg !128
  %".21" = insertvalue [4 x i64] %".20", i64 2, 1 , !dbg !128
  %".22" = insertvalue [4 x i64] %".21", i64 3, 2 , !dbg !128
  %".23" = insertvalue [4 x i64] %".22", i64 5, 3 , !dbg !128
  %".24" = extractvalue [4 x i64] %".23", 0 , !dbg !128
  %".25" = trunc i64 %".24" to i8 , !dbg !128
  %".26" = insertvalue [4 x i8] undef, i8 %".25", 0 , !dbg !128
  %".27" = extractvalue [4 x i64] %".23", 1 , !dbg !128
  %".28" = trunc i64 %".27" to i8 , !dbg !128
  %".29" = insertvalue [4 x i8] %".26", i8 %".28", 1 , !dbg !128
  %".30" = extractvalue [4 x i64] %".23", 2 , !dbg !128
  %".31" = trunc i64 %".30" to i8 , !dbg !128
  %".32" = insertvalue [4 x i8] %".29", i8 %".31", 2 , !dbg !128
  %".33" = extractvalue [4 x i64] %".23", 3 , !dbg !128
  %".34" = trunc i64 %".33" to i8 , !dbg !128
  %".35" = insertvalue [4 x i8] %".32", i8 %".34", 3 , !dbg !128
  store [4 x i8] %".35", [4 x i8]* %"b.addr", !dbg !128
  call void @"llvm.dbg.declare"(metadata [4 x i8]* %"b.addr", metadata !129, metadata !7), !dbg !130
  %".38" = getelementptr [4 x i8], [4 x i8]* %"a.addr", i32 0, i64 0 , !dbg !131
  %".39" = getelementptr [4 x i8], [4 x i8]* %"b.addr", i32 0, i64 0 , !dbg !131
  %".40" = call i32 @"mem_eq"(i8* %".38", i8* %".39", i64 4), !dbg !131
  %".41" = sext i32 %".40" to i64 , !dbg !132
  %".42" = icmp eq i64 %".41", 0 , !dbg !132
  br i1 %".42", label %"assert.pass", label %"assert.fail", !dbg !132
assert.pass:
  %".46" = trunc i64 0 to i32 , !dbg !133
  ret i32 %".46", !dbg !133
assert.fail:
  %".44" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !132
  unreachable
}

define internal i32 @"test_mem_eq_empty"() !dbg !24
{
entry:
  %"a.addr" = alloca [4 x i8], !dbg !134
  %"b.addr" = alloca [4 x i8], !dbg !137
  %".2" = insertvalue [4 x i64] undef, i64 170, 0 , !dbg !134
  %".3" = insertvalue [4 x i64] %".2", i64 187, 1 , !dbg !134
  %".4" = insertvalue [4 x i64] %".3", i64 204, 2 , !dbg !134
  %".5" = insertvalue [4 x i64] %".4", i64 221, 3 , !dbg !134
  %".6" = extractvalue [4 x i64] %".5", 0 , !dbg !134
  %".7" = trunc i64 %".6" to i8 , !dbg !134
  %".8" = insertvalue [4 x i8] undef, i8 %".7", 0 , !dbg !134
  %".9" = extractvalue [4 x i64] %".5", 1 , !dbg !134
  %".10" = trunc i64 %".9" to i8 , !dbg !134
  %".11" = insertvalue [4 x i8] %".8", i8 %".10", 1 , !dbg !134
  %".12" = extractvalue [4 x i64] %".5", 2 , !dbg !134
  %".13" = trunc i64 %".12" to i8 , !dbg !134
  %".14" = insertvalue [4 x i8] %".11", i8 %".13", 2 , !dbg !134
  %".15" = extractvalue [4 x i64] %".5", 3 , !dbg !134
  %".16" = trunc i64 %".15" to i8 , !dbg !134
  %".17" = insertvalue [4 x i8] %".14", i8 %".16", 3 , !dbg !134
  store [4 x i8] %".17", [4 x i8]* %"a.addr", !dbg !134
  call void @"llvm.dbg.declare"(metadata [4 x i8]* %"a.addr", metadata !135, metadata !7), !dbg !136
  %".20" = insertvalue [4 x i64] undef, i64 17, 0 , !dbg !137
  %".21" = insertvalue [4 x i64] %".20", i64 34, 1 , !dbg !137
  %".22" = insertvalue [4 x i64] %".21", i64 51, 2 , !dbg !137
  %".23" = insertvalue [4 x i64] %".22", i64 68, 3 , !dbg !137
  %".24" = extractvalue [4 x i64] %".23", 0 , !dbg !137
  %".25" = trunc i64 %".24" to i8 , !dbg !137
  %".26" = insertvalue [4 x i8] undef, i8 %".25", 0 , !dbg !137
  %".27" = extractvalue [4 x i64] %".23", 1 , !dbg !137
  %".28" = trunc i64 %".27" to i8 , !dbg !137
  %".29" = insertvalue [4 x i8] %".26", i8 %".28", 1 , !dbg !137
  %".30" = extractvalue [4 x i64] %".23", 2 , !dbg !137
  %".31" = trunc i64 %".30" to i8 , !dbg !137
  %".32" = insertvalue [4 x i8] %".29", i8 %".31", 2 , !dbg !137
  %".33" = extractvalue [4 x i64] %".23", 3 , !dbg !137
  %".34" = trunc i64 %".33" to i8 , !dbg !137
  %".35" = insertvalue [4 x i8] %".32", i8 %".34", 3 , !dbg !137
  store [4 x i8] %".35", [4 x i8]* %"b.addr", !dbg !137
  call void @"llvm.dbg.declare"(metadata [4 x i8]* %"b.addr", metadata !138, metadata !7), !dbg !139
  %".38" = getelementptr [4 x i8], [4 x i8]* %"a.addr", i32 0, i64 0 , !dbg !140
  %".39" = getelementptr [4 x i8], [4 x i8]* %"b.addr", i32 0, i64 0 , !dbg !140
  %".40" = call i32 @"mem_eq"(i8* %".38", i8* %".39", i64 0), !dbg !140
  %".41" = sext i32 %".40" to i64 , !dbg !141
  %".42" = icmp eq i64 %".41", 1 , !dbg !141
  br i1 %".42", label %"assert.pass", label %"assert.fail", !dbg !141
assert.pass:
  %".46" = trunc i64 0 to i32 , !dbg !142
  ret i32 %".46", !dbg !142
assert.fail:
  %".44" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !141
  unreachable
}

define internal i32 @"test_mem_copy_basic"() !dbg !25
{
entry:
  %"src.addr" = alloca [8 x i8], !dbg !143
  %"dst.addr" = alloca [8 x i8], !dbg !146
  %"i" = alloca i64, !dbg !149
  %".2" = insertvalue [8 x i64] undef, i64 1, 0 , !dbg !143
  %".3" = insertvalue [8 x i64] %".2", i64 2, 1 , !dbg !143
  %".4" = insertvalue [8 x i64] %".3", i64 3, 2 , !dbg !143
  %".5" = insertvalue [8 x i64] %".4", i64 4, 3 , !dbg !143
  %".6" = insertvalue [8 x i64] %".5", i64 5, 4 , !dbg !143
  %".7" = insertvalue [8 x i64] %".6", i64 6, 5 , !dbg !143
  %".8" = insertvalue [8 x i64] %".7", i64 7, 6 , !dbg !143
  %".9" = insertvalue [8 x i64] %".8", i64 8, 7 , !dbg !143
  %".10" = extractvalue [8 x i64] %".9", 0 , !dbg !143
  %".11" = trunc i64 %".10" to i8 , !dbg !143
  %".12" = insertvalue [8 x i8] undef, i8 %".11", 0 , !dbg !143
  %".13" = extractvalue [8 x i64] %".9", 1 , !dbg !143
  %".14" = trunc i64 %".13" to i8 , !dbg !143
  %".15" = insertvalue [8 x i8] %".12", i8 %".14", 1 , !dbg !143
  %".16" = extractvalue [8 x i64] %".9", 2 , !dbg !143
  %".17" = trunc i64 %".16" to i8 , !dbg !143
  %".18" = insertvalue [8 x i8] %".15", i8 %".17", 2 , !dbg !143
  %".19" = extractvalue [8 x i64] %".9", 3 , !dbg !143
  %".20" = trunc i64 %".19" to i8 , !dbg !143
  %".21" = insertvalue [8 x i8] %".18", i8 %".20", 3 , !dbg !143
  %".22" = extractvalue [8 x i64] %".9", 4 , !dbg !143
  %".23" = trunc i64 %".22" to i8 , !dbg !143
  %".24" = insertvalue [8 x i8] %".21", i8 %".23", 4 , !dbg !143
  %".25" = extractvalue [8 x i64] %".9", 5 , !dbg !143
  %".26" = trunc i64 %".25" to i8 , !dbg !143
  %".27" = insertvalue [8 x i8] %".24", i8 %".26", 5 , !dbg !143
  %".28" = extractvalue [8 x i64] %".9", 6 , !dbg !143
  %".29" = trunc i64 %".28" to i8 , !dbg !143
  %".30" = insertvalue [8 x i8] %".27", i8 %".29", 6 , !dbg !143
  %".31" = extractvalue [8 x i64] %".9", 7 , !dbg !143
  %".32" = trunc i64 %".31" to i8 , !dbg !143
  %".33" = insertvalue [8 x i8] %".30", i8 %".32", 7 , !dbg !143
  store [8 x i8] %".33", [8 x i8]* %"src.addr", !dbg !143
  call void @"llvm.dbg.declare"(metadata [8 x i8]* %"src.addr", metadata !144, metadata !7), !dbg !145
  call void @"llvm.dbg.declare"(metadata [8 x i8]* %"dst.addr", metadata !147, metadata !7), !dbg !148
  store i64 0, i64* %"i", !dbg !149
  br label %"for.cond", !dbg !149
for.cond:
  %".39" = load i64, i64* %"i", !dbg !149
  %".40" = icmp slt i64 %".39", 8 , !dbg !149
  br i1 %".40", label %"for.body", label %"for.end", !dbg !149
for.body:
  %".42" = load i64, i64* %"i", !dbg !150
  %".43" = getelementptr [8 x i8], [8 x i8]* %"dst.addr", i32 0, i64 %".42" , !dbg !150
  %".44" = trunc i64 0 to i8 , !dbg !150
  store i8 %".44", i8* %".43", !dbg !150
  br label %"for.incr", !dbg !150
for.incr:
  %".47" = load i64, i64* %"i", !dbg !150
  %".48" = add i64 %".47", 1, !dbg !150
  store i64 %".48", i64* %"i", !dbg !150
  br label %"for.cond", !dbg !150
for.end:
  %".51" = getelementptr [8 x i8], [8 x i8]* %"dst.addr", i32 0, i64 0 , !dbg !151
  %".52" = getelementptr [8 x i8], [8 x i8]* %"src.addr", i32 0, i64 0 , !dbg !151
  %".53" = call i32 @"mem_copy"(i8* %".51", i8* %".52", i64 8), !dbg !151
  %".54" = getelementptr [8 x i8], [8 x i8]* %"dst.addr", i32 0, i64 0 , !dbg !152
  %".55" = load i8, i8* %".54", !dbg !152
  %".56" = zext i8 %".55" to i64 , !dbg !152
  %".57" = icmp eq i64 %".56", 1 , !dbg !152
  br i1 %".57", label %"assert.pass", label %"assert.fail", !dbg !152
assert.pass:
  %".61" = getelementptr [8 x i8], [8 x i8]* %"dst.addr", i32 0, i64 7 , !dbg !153
  %".62" = load i8, i8* %".61", !dbg !153
  %".63" = zext i8 %".62" to i64 , !dbg !153
  %".64" = icmp eq i64 %".63", 8 , !dbg !153
  br i1 %".64", label %"assert.pass.1", label %"assert.fail.1", !dbg !153
assert.fail:
  %".59" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !152
  unreachable
assert.pass.1:
  %".68" = trunc i64 0 to i32 , !dbg !154
  ret i32 %".68", !dbg !154
assert.fail.1:
  %".66" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !153
  unreachable
}

define internal i32 @"test_mem_copy_partial"() !dbg !26
{
entry:
  %"src.addr" = alloca [8 x i8], !dbg !155
  %"dst.addr" = alloca [8 x i8], !dbg !158
  %"i" = alloca i64, !dbg !161
  %".2" = insertvalue [8 x i64] undef, i64 170, 0 , !dbg !155
  %".3" = insertvalue [8 x i64] %".2", i64 187, 1 , !dbg !155
  %".4" = insertvalue [8 x i64] %".3", i64 204, 2 , !dbg !155
  %".5" = insertvalue [8 x i64] %".4", i64 221, 3 , !dbg !155
  %".6" = insertvalue [8 x i64] %".5", i64 238, 4 , !dbg !155
  %".7" = insertvalue [8 x i64] %".6", i64 255, 5 , !dbg !155
  %".8" = insertvalue [8 x i64] %".7", i64 17, 6 , !dbg !155
  %".9" = insertvalue [8 x i64] %".8", i64 34, 7 , !dbg !155
  %".10" = extractvalue [8 x i64] %".9", 0 , !dbg !155
  %".11" = trunc i64 %".10" to i8 , !dbg !155
  %".12" = insertvalue [8 x i8] undef, i8 %".11", 0 , !dbg !155
  %".13" = extractvalue [8 x i64] %".9", 1 , !dbg !155
  %".14" = trunc i64 %".13" to i8 , !dbg !155
  %".15" = insertvalue [8 x i8] %".12", i8 %".14", 1 , !dbg !155
  %".16" = extractvalue [8 x i64] %".9", 2 , !dbg !155
  %".17" = trunc i64 %".16" to i8 , !dbg !155
  %".18" = insertvalue [8 x i8] %".15", i8 %".17", 2 , !dbg !155
  %".19" = extractvalue [8 x i64] %".9", 3 , !dbg !155
  %".20" = trunc i64 %".19" to i8 , !dbg !155
  %".21" = insertvalue [8 x i8] %".18", i8 %".20", 3 , !dbg !155
  %".22" = extractvalue [8 x i64] %".9", 4 , !dbg !155
  %".23" = trunc i64 %".22" to i8 , !dbg !155
  %".24" = insertvalue [8 x i8] %".21", i8 %".23", 4 , !dbg !155
  %".25" = extractvalue [8 x i64] %".9", 5 , !dbg !155
  %".26" = trunc i64 %".25" to i8 , !dbg !155
  %".27" = insertvalue [8 x i8] %".24", i8 %".26", 5 , !dbg !155
  %".28" = extractvalue [8 x i64] %".9", 6 , !dbg !155
  %".29" = trunc i64 %".28" to i8 , !dbg !155
  %".30" = insertvalue [8 x i8] %".27", i8 %".29", 6 , !dbg !155
  %".31" = extractvalue [8 x i64] %".9", 7 , !dbg !155
  %".32" = trunc i64 %".31" to i8 , !dbg !155
  %".33" = insertvalue [8 x i8] %".30", i8 %".32", 7 , !dbg !155
  store [8 x i8] %".33", [8 x i8]* %"src.addr", !dbg !155
  call void @"llvm.dbg.declare"(metadata [8 x i8]* %"src.addr", metadata !156, metadata !7), !dbg !157
  call void @"llvm.dbg.declare"(metadata [8 x i8]* %"dst.addr", metadata !159, metadata !7), !dbg !160
  store i64 0, i64* %"i", !dbg !161
  br label %"for.cond", !dbg !161
for.cond:
  %".39" = load i64, i64* %"i", !dbg !161
  %".40" = icmp slt i64 %".39", 8 , !dbg !161
  br i1 %".40", label %"for.body", label %"for.end", !dbg !161
for.body:
  %".42" = load i64, i64* %"i", !dbg !162
  %".43" = getelementptr [8 x i8], [8 x i8]* %"dst.addr", i32 0, i64 %".42" , !dbg !162
  %".44" = trunc i64 0 to i8 , !dbg !162
  store i8 %".44", i8* %".43", !dbg !162
  br label %"for.incr", !dbg !162
for.incr:
  %".47" = load i64, i64* %"i", !dbg !162
  %".48" = add i64 %".47", 1, !dbg !162
  store i64 %".48", i64* %"i", !dbg !162
  br label %"for.cond", !dbg !162
for.end:
  %".51" = getelementptr [8 x i8], [8 x i8]* %"dst.addr", i32 0, i64 2 , !dbg !163
  %".52" = getelementptr [8 x i8], [8 x i8]* %"src.addr", i32 0, i64 2 , !dbg !163
  %".53" = call i32 @"mem_copy"(i8* %".51", i8* %".52", i64 4), !dbg !163
  %".54" = getelementptr [8 x i8], [8 x i8]* %"dst.addr", i32 0, i64 0 , !dbg !164
  %".55" = load i8, i8* %".54", !dbg !164
  %".56" = zext i8 %".55" to i64 , !dbg !164
  %".57" = icmp eq i64 %".56", 0 , !dbg !164
  br i1 %".57", label %"assert.pass", label %"assert.fail", !dbg !164
assert.pass:
  %".61" = getelementptr [8 x i8], [8 x i8]* %"dst.addr", i32 0, i64 1 , !dbg !165
  %".62" = load i8, i8* %".61", !dbg !165
  %".63" = zext i8 %".62" to i64 , !dbg !165
  %".64" = icmp eq i64 %".63", 0 , !dbg !165
  br i1 %".64", label %"assert.pass.1", label %"assert.fail.1", !dbg !165
assert.fail:
  %".59" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !164
  unreachable
assert.pass.1:
  %".68" = getelementptr [8 x i8], [8 x i8]* %"dst.addr", i32 0, i64 2 , !dbg !166
  %".69" = load i8, i8* %".68", !dbg !166
  %".70" = zext i8 %".69" to i64 , !dbg !166
  %".71" = icmp eq i64 %".70", 204 , !dbg !166
  br i1 %".71", label %"assert.pass.2", label %"assert.fail.2", !dbg !166
assert.fail.1:
  %".66" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !165
  unreachable
assert.pass.2:
  %".75" = getelementptr [8 x i8], [8 x i8]* %"dst.addr", i32 0, i64 5 , !dbg !167
  %".76" = load i8, i8* %".75", !dbg !167
  %".77" = zext i8 %".76" to i64 , !dbg !167
  %".78" = icmp eq i64 %".77", 255 , !dbg !167
  br i1 %".78", label %"assert.pass.3", label %"assert.fail.3", !dbg !167
assert.fail.2:
  %".73" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !166
  unreachable
assert.pass.3:
  %".82" = getelementptr [8 x i8], [8 x i8]* %"dst.addr", i32 0, i64 6 , !dbg !168
  %".83" = load i8, i8* %".82", !dbg !168
  %".84" = zext i8 %".83" to i64 , !dbg !168
  %".85" = icmp eq i64 %".84", 0 , !dbg !168
  br i1 %".85", label %"assert.pass.4", label %"assert.fail.4", !dbg !168
assert.fail.3:
  %".80" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !167
  unreachable
assert.pass.4:
  %".89" = trunc i64 0 to i32 , !dbg !169
  ret i32 %".89", !dbg !169
assert.fail.4:
  %".87" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !168
  unreachable
}

define internal i32 @"test_mem_copy_empty"() !dbg !27
{
entry:
  %"src.addr" = alloca [4 x i8], !dbg !170
  %"dst.addr" = alloca [4 x i8], !dbg !173
  %".2" = insertvalue [4 x i64] undef, i64 1, 0 , !dbg !170
  %".3" = insertvalue [4 x i64] %".2", i64 2, 1 , !dbg !170
  %".4" = insertvalue [4 x i64] %".3", i64 3, 2 , !dbg !170
  %".5" = insertvalue [4 x i64] %".4", i64 4, 3 , !dbg !170
  %".6" = extractvalue [4 x i64] %".5", 0 , !dbg !170
  %".7" = trunc i64 %".6" to i8 , !dbg !170
  %".8" = insertvalue [4 x i8] undef, i8 %".7", 0 , !dbg !170
  %".9" = extractvalue [4 x i64] %".5", 1 , !dbg !170
  %".10" = trunc i64 %".9" to i8 , !dbg !170
  %".11" = insertvalue [4 x i8] %".8", i8 %".10", 1 , !dbg !170
  %".12" = extractvalue [4 x i64] %".5", 2 , !dbg !170
  %".13" = trunc i64 %".12" to i8 , !dbg !170
  %".14" = insertvalue [4 x i8] %".11", i8 %".13", 2 , !dbg !170
  %".15" = extractvalue [4 x i64] %".5", 3 , !dbg !170
  %".16" = trunc i64 %".15" to i8 , !dbg !170
  %".17" = insertvalue [4 x i8] %".14", i8 %".16", 3 , !dbg !170
  store [4 x i8] %".17", [4 x i8]* %"src.addr", !dbg !170
  call void @"llvm.dbg.declare"(metadata [4 x i8]* %"src.addr", metadata !171, metadata !7), !dbg !172
  %".20" = insertvalue [4 x i64] undef, i64 170, 0 , !dbg !173
  %".21" = insertvalue [4 x i64] %".20", i64 187, 1 , !dbg !173
  %".22" = insertvalue [4 x i64] %".21", i64 204, 2 , !dbg !173
  %".23" = insertvalue [4 x i64] %".22", i64 221, 3 , !dbg !173
  %".24" = extractvalue [4 x i64] %".23", 0 , !dbg !173
  %".25" = trunc i64 %".24" to i8 , !dbg !173
  %".26" = insertvalue [4 x i8] undef, i8 %".25", 0 , !dbg !173
  %".27" = extractvalue [4 x i64] %".23", 1 , !dbg !173
  %".28" = trunc i64 %".27" to i8 , !dbg !173
  %".29" = insertvalue [4 x i8] %".26", i8 %".28", 1 , !dbg !173
  %".30" = extractvalue [4 x i64] %".23", 2 , !dbg !173
  %".31" = trunc i64 %".30" to i8 , !dbg !173
  %".32" = insertvalue [4 x i8] %".29", i8 %".31", 2 , !dbg !173
  %".33" = extractvalue [4 x i64] %".23", 3 , !dbg !173
  %".34" = trunc i64 %".33" to i8 , !dbg !173
  %".35" = insertvalue [4 x i8] %".32", i8 %".34", 3 , !dbg !173
  store [4 x i8] %".35", [4 x i8]* %"dst.addr", !dbg !173
  call void @"llvm.dbg.declare"(metadata [4 x i8]* %"dst.addr", metadata !174, metadata !7), !dbg !175
  %".38" = getelementptr [4 x i8], [4 x i8]* %"dst.addr", i32 0, i64 0 , !dbg !176
  %".39" = getelementptr [4 x i8], [4 x i8]* %"src.addr", i32 0, i64 0 , !dbg !176
  %".40" = call i32 @"mem_copy"(i8* %".38", i8* %".39", i64 0), !dbg !176
  %".41" = getelementptr [4 x i8], [4 x i8]* %"dst.addr", i32 0, i64 0 , !dbg !177
  %".42" = load i8, i8* %".41", !dbg !177
  %".43" = zext i8 %".42" to i64 , !dbg !177
  %".44" = icmp eq i64 %".43", 170 , !dbg !177
  br i1 %".44", label %"assert.pass", label %"assert.fail", !dbg !177
assert.pass:
  %".48" = trunc i64 0 to i32 , !dbg !178
  ret i32 %".48", !dbg !178
assert.fail:
  %".46" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !177
  unreachable
}

define internal i32 @"test_ct_select_u8_true"() !dbg !28
{
entry:
  %".2" = trunc i64 170 to i8 , !dbg !179
  %".3" = trunc i64 187 to i8 , !dbg !180
  %".4" = trunc i64 1 to i32 , !dbg !181
  %".5" = call i8 @"ct_select_u8"(i8 %".2", i8 %".3", i32 %".4"), !dbg !181
  %".6" = zext i8 %".5" to i64 , !dbg !182
  %".7" = icmp eq i64 %".6", 170 , !dbg !182
  br i1 %".7", label %"assert.pass", label %"assert.fail", !dbg !182
assert.pass:
  %".11" = trunc i64 0 to i32 , !dbg !183
  ret i32 %".11", !dbg !183
assert.fail:
  %".9" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !182
  unreachable
}

define internal i32 @"test_ct_select_u8_false"() !dbg !29
{
entry:
  %".2" = trunc i64 170 to i8 , !dbg !184
  %".3" = trunc i64 187 to i8 , !dbg !185
  %".4" = trunc i64 0 to i32 , !dbg !186
  %".5" = call i8 @"ct_select_u8"(i8 %".2", i8 %".3", i32 %".4"), !dbg !186
  %".6" = zext i8 %".5" to i64 , !dbg !187
  %".7" = icmp eq i64 %".6", 187 , !dbg !187
  br i1 %".7", label %"assert.pass", label %"assert.fail", !dbg !187
assert.pass:
  %".11" = trunc i64 0 to i32 , !dbg !188
  ret i32 %".11", !dbg !188
assert.fail:
  %".9" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !187
  unreachable
}

define internal i32 @"test_ct_select_u64_true"() !dbg !30
{
entry:
  %".2" = trunc i64 1 to i32 , !dbg !191
  %".3" = call i64 @"ct_select_u64"(i64 16045690984503098046, i64 1311768467294899695, i32 %".2"), !dbg !191
  %".4" = icmp eq i64 %".3", 16045690984503098046 , !dbg !192
  br i1 %".4", label %"assert.pass", label %"assert.fail", !dbg !192
assert.pass:
  %".8" = trunc i64 0 to i32 , !dbg !193
  ret i32 %".8", !dbg !193
assert.fail:
  %".6" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !192
  unreachable
}

define internal i32 @"test_ct_select_u64_false"() !dbg !31
{
entry:
  %".2" = trunc i64 0 to i32 , !dbg !196
  %".3" = call i64 @"ct_select_u64"(i64 16045690984503098046, i64 1311768467294899695, i32 %".2"), !dbg !196
  %".4" = icmp eq i64 %".3", 1311768467294899695 , !dbg !197
  br i1 %".4", label %"assert.pass", label %"assert.fail", !dbg !197
assert.pass:
  %".8" = trunc i64 0 to i32 , !dbg !198
  ret i32 %".8", !dbg !198
assert.fail:
  %".6" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !197
  unreachable
}

define internal i32 @"test_ct_is_zero_zero"() !dbg !32
{
entry:
  %".2" = call i32 @"ct_is_zero_u64"(i64 0), !dbg !199
  %".3" = sext i32 %".2" to i64 , !dbg !200
  %".4" = icmp eq i64 %".3", 1 , !dbg !200
  br i1 %".4", label %"assert.pass", label %"assert.fail", !dbg !200
assert.pass:
  %".8" = trunc i64 0 to i32 , !dbg !201
  ret i32 %".8", !dbg !201
assert.fail:
  %".6" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !200
  unreachable
}

define internal i32 @"test_ct_is_zero_nonzero"() !dbg !33
{
entry:
  %".2" = call i32 @"ct_is_zero_u64"(i64 1), !dbg !202
  %".3" = sext i32 %".2" to i64 , !dbg !203
  %".4" = icmp eq i64 %".3", 0 , !dbg !203
  br i1 %".4", label %"assert.pass", label %"assert.fail", !dbg !203
assert.pass:
  %".8" = call i32 @"ct_is_zero_u64"(i64 18446744073709551615), !dbg !204
  %".9" = sext i32 %".8" to i64 , !dbg !205
  %".10" = icmp eq i64 %".9", 0 , !dbg !205
  br i1 %".10", label %"assert.pass.1", label %"assert.fail.1", !dbg !205
assert.fail:
  %".6" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !203
  unreachable
assert.pass.1:
  %".14" = trunc i64 0 to i32 , !dbg !206
  ret i32 %".14", !dbg !206
assert.fail.1:
  %".12" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !205
  unreachable
}

define internal i32 @"test_mem_is_zero_all_zeros"() !dbg !34
{
entry:
  %"buf.addr" = alloca [16 x i8], !dbg !207
  %"i" = alloca i64, !dbg !210
  call void @"llvm.dbg.declare"(metadata [16 x i8]* %"buf.addr", metadata !208, metadata !7), !dbg !209
  store i64 0, i64* %"i", !dbg !210
  br label %"for.cond", !dbg !210
for.cond:
  %".5" = load i64, i64* %"i", !dbg !210
  %".6" = icmp slt i64 %".5", 16 , !dbg !210
  br i1 %".6", label %"for.body", label %"for.end", !dbg !210
for.body:
  %".8" = load i64, i64* %"i", !dbg !211
  %".9" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 %".8" , !dbg !211
  %".10" = trunc i64 0 to i8 , !dbg !211
  store i8 %".10", i8* %".9", !dbg !211
  br label %"for.incr", !dbg !211
for.incr:
  %".13" = load i64, i64* %"i", !dbg !211
  %".14" = add i64 %".13", 1, !dbg !211
  store i64 %".14", i64* %"i", !dbg !211
  br label %"for.cond", !dbg !211
for.end:
  %".17" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !212
  %".18" = call i32 @"mem_is_zero"(i8* %".17", i64 16), !dbg !212
  %".19" = sext i32 %".18" to i64 , !dbg !213
  %".20" = icmp eq i64 %".19", 1 , !dbg !213
  br i1 %".20", label %"assert.pass", label %"assert.fail", !dbg !213
assert.pass:
  %".24" = trunc i64 0 to i32 , !dbg !214
  ret i32 %".24", !dbg !214
assert.fail:
  %".22" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !213
  unreachable
}

define internal i32 @"test_mem_is_zero_has_nonzero"() !dbg !35
{
entry:
  %"buf.addr" = alloca [16 x i8], !dbg !215
  %"i" = alloca i64, !dbg !218
  call void @"llvm.dbg.declare"(metadata [16 x i8]* %"buf.addr", metadata !216, metadata !7), !dbg !217
  store i64 0, i64* %"i", !dbg !218
  br label %"for.cond", !dbg !218
for.cond:
  %".5" = load i64, i64* %"i", !dbg !218
  %".6" = icmp slt i64 %".5", 16 , !dbg !218
  br i1 %".6", label %"for.body", label %"for.end", !dbg !218
for.body:
  %".8" = load i64, i64* %"i", !dbg !219
  %".9" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 %".8" , !dbg !219
  %".10" = trunc i64 0 to i8 , !dbg !219
  store i8 %".10", i8* %".9", !dbg !219
  br label %"for.incr", !dbg !219
for.incr:
  %".13" = load i64, i64* %"i", !dbg !219
  %".14" = add i64 %".13", 1, !dbg !219
  store i64 %".14", i64* %"i", !dbg !219
  br label %"for.cond", !dbg !219
for.end:
  %".17" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 8 , !dbg !220
  %".18" = trunc i64 1 to i8 , !dbg !220
  store i8 %".18", i8* %".17", !dbg !220
  %".20" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !221
  %".21" = call i32 @"mem_is_zero"(i8* %".20", i64 16), !dbg !221
  %".22" = sext i32 %".21" to i64 , !dbg !222
  %".23" = icmp eq i64 %".22", 0 , !dbg !222
  br i1 %".23", label %"assert.pass", label %"assert.fail", !dbg !222
assert.pass:
  %".27" = trunc i64 0 to i32 , !dbg !223
  ret i32 %".27", !dbg !223
assert.fail:
  %".25" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !222
  unreachable
}

define internal i32 @"test_mem_is_zero_empty"() !dbg !36
{
entry:
  %"buf.addr" = alloca [4 x i8], !dbg !224
  %".2" = insertvalue [4 x i64] undef, i64 255, 0 , !dbg !224
  %".3" = insertvalue [4 x i64] %".2", i64 255, 1 , !dbg !224
  %".4" = insertvalue [4 x i64] %".3", i64 255, 2 , !dbg !224
  %".5" = insertvalue [4 x i64] %".4", i64 255, 3 , !dbg !224
  %".6" = extractvalue [4 x i64] %".5", 0 , !dbg !224
  %".7" = trunc i64 %".6" to i8 , !dbg !224
  %".8" = insertvalue [4 x i8] undef, i8 %".7", 0 , !dbg !224
  %".9" = extractvalue [4 x i64] %".5", 1 , !dbg !224
  %".10" = trunc i64 %".9" to i8 , !dbg !224
  %".11" = insertvalue [4 x i8] %".8", i8 %".10", 1 , !dbg !224
  %".12" = extractvalue [4 x i64] %".5", 2 , !dbg !224
  %".13" = trunc i64 %".12" to i8 , !dbg !224
  %".14" = insertvalue [4 x i8] %".11", i8 %".13", 2 , !dbg !224
  %".15" = extractvalue [4 x i64] %".5", 3 , !dbg !224
  %".16" = trunc i64 %".15" to i8 , !dbg !224
  %".17" = insertvalue [4 x i8] %".14", i8 %".16", 3 , !dbg !224
  store [4 x i8] %".17", [4 x i8]* %"buf.addr", !dbg !224
  call void @"llvm.dbg.declare"(metadata [4 x i8]* %"buf.addr", metadata !225, metadata !7), !dbg !226
  %".20" = getelementptr [4 x i8], [4 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !227
  %".21" = call i32 @"mem_is_zero"(i8* %".20", i64 0), !dbg !227
  %".22" = sext i32 %".21" to i64 , !dbg !228
  %".23" = icmp eq i64 %".22", 1 , !dbg !228
  br i1 %".23", label %"assert.pass", label %"assert.fail", !dbg !228
assert.pass:
  %".27" = trunc i64 0 to i32 , !dbg !229
  ret i32 %".27", !dbg !229
assert.fail:
  %".25" = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 1), !dbg !228
  unreachable
}

define i32 @"main"() !dbg !37
{
entry:
  %".2" = call i32 @"test_mem_is_zero_empty"(), !dbg !230
  ret i32 %".2", !dbg !230
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !38
{
entry:
  %"i" = alloca i64, !dbg !238
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !233, metadata !7), !dbg !234
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !236, metadata !7), !dbg !234
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !237, metadata !7), !dbg !234
  %".10" = load i64, i64* %"len", !dbg !238
  store i64 0, i64* %"i", !dbg !238
  br label %"for.cond", !dbg !238
for.cond:
  %".13" = load i64, i64* %"i", !dbg !238
  %".14" = icmp slt i64 %".13", %".10" , !dbg !238
  br i1 %".14", label %"for.body", label %"for.end", !dbg !238
for.body:
  %".16" = load i8*, i8** %"data", !dbg !238
  %".17" = load i64, i64* %"i", !dbg !238
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !238
  %".19" = load i8, i8* %".18", !dbg !238
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !238
  %".21" = sext i32 %".20" to i64 , !dbg !238
  %".22" = icmp ne i64 %".21", 0 , !dbg !238
  br i1 %".22", label %"if.then", label %"if.end", !dbg !238
for.incr:
  %".28" = load i64, i64* %"i", !dbg !239
  %".29" = add i64 %".28", 1, !dbg !239
  store i64 %".29", i64* %"i", !dbg !239
  br label %"for.cond", !dbg !239
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !240
  ret i32 %".32", !dbg !240
if.then:
  %".24" = sub i64 0, 1, !dbg !239
  %".25" = trunc i64 %".24" to i32 , !dbg !239
  ret i32 %".25", !dbg !239
if.end:
  br label %"for.incr", !dbg !239
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !39
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !241, metadata !7), !dbg !242
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !243
  store i64 0, i64* %".4", !dbg !243
  ret i32 0, !dbg !243
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !40
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !244, metadata !7), !dbg !245
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !246
  %".5" = load i64, i64* %".4", !dbg !246
  %".6" = sub i64 %".5", 1, !dbg !246
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !246
  store i64 %".6", i64* %".7", !dbg !246
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !247
  %".10" = load i8*, i8** %".9", !dbg !247
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !247
  %".12" = load i64, i64* %".11", !dbg !247
  %".13" = getelementptr i8, i8* %".10", i64 %".12" , !dbg !247
  %".14" = load i8, i8* %".13", !dbg !247
  ret i8 %".14", !dbg !247
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !41
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !250
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !248, metadata !7), !dbg !249
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !251, metadata !7), !dbg !252
  %".6" = load i64, i64* %"cap", !dbg !253
  %".7" = icmp sle i64 %".6", 0 , !dbg !253
  br i1 %".7", label %"if.then", label %"if.end", !dbg !253
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !254
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !254
  store i8* null, i8** %".10", !dbg !254
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !255
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !255
  store i64 0, i64* %".13", !dbg !255
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !256
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !256
  store i64 0, i64* %".16", !dbg !256
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !257
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !257
if.end:
  %".20" = load i64, i64* %"cap", !dbg !258
  %".21" = mul i64 %".20", 1, !dbg !258
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !259
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !259
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !259
  store i8* %".22", i8** %".24", !dbg !259
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !260
  %".27" = load i8*, i8** %".26", !dbg !260
  %".28" = icmp eq i8* %".27", null , !dbg !260
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !260
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !261
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !261
  store i64 0, i64* %".31", !dbg !261
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !262
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !262
  store i64 0, i64* %".34", !dbg !262
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !263
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !263
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !264
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !264
  store i64 0, i64* %".39", !dbg !264
  %".41" = load i64, i64* %"cap", !dbg !265
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !265
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !265
  store i64 %".41", i64* %".43", !dbg !265
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !266
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !266
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !42
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !267, metadata !7), !dbg !268
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !269, metadata !7), !dbg !268
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !270, metadata !7), !dbg !268
  %".10" = load i8, i8* %"item", !dbg !271
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !271
  %".12" = load i8*, i8** %".11", !dbg !271
  %".13" = load i64, i64* %"idx", !dbg !271
  %".14" = getelementptr i8, i8* %".12", i64 %".13" , !dbg !271
  store i8 %".10", i8* %".14", !dbg !271
  %".16" = trunc i64 0 to i32 , !dbg !272
  ret i32 %".16", !dbg !272
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !43
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !273, metadata !7), !dbg !274
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !275
  %".5" = load i8*, i8** %".4", !dbg !275
  %".6" = icmp ne i8* %".5", null , !dbg !275
  br i1 %".6", label %"if.then", label %"if.end", !dbg !275
if.then:
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !275
  %".9" = load i8*, i8** %".8", !dbg !275
  %".10" = call i32 @"free"(i8* %".9"), !dbg !275
  br label %"if.end", !dbg !275
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !276
  store i8* null, i8** %".12", !dbg !276
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !277
  store i64 0, i64* %".14", !dbg !277
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !278
  store i64 0, i64* %".16", !dbg !278
  ret i32 0, !dbg !278
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !44
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !281, metadata !7), !dbg !282
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !284, metadata !7), !dbg !282
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !285
  %".8" = load i64, i64* %".7", !dbg !285
  %".9" = add i64 %".8", 1, !dbg !285
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !285
  %".11" = sext i32 %".10" to i64 , !dbg !285
  %".12" = icmp ne i64 %".11", 0 , !dbg !285
  br i1 %".12", label %"if.then", label %"if.end", !dbg !285
if.then:
  %".14" = sub i64 0, 1, !dbg !286
  %".15" = trunc i64 %".14" to i32 , !dbg !286
  ret i32 %".15", !dbg !286
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !287
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !287
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !287
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !287
  %".21" = load i64, i64* %".20", !dbg !287
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !287
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !287
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !288
  %".25" = load i64, i64* %".24", !dbg !288
  %".26" = add i64 %".25", 1, !dbg !288
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !288
  store i64 %".26", i64* %".27", !dbg !288
  %".29" = trunc i64 0 to i32 , !dbg !289
  ret i32 %".29", !dbg !289
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !45
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !290
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !291, metadata !7), !dbg !292
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !293
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !293
  store i8* null, i8** %".4", !dbg !293
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !294
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !294
  store i64 0, i64* %".7", !dbg !294
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !295
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !295
  store i64 0, i64* %".10", !dbg !295
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !296
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !296
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !46
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !302
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !297, metadata !7), !dbg !298
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !299, metadata !7), !dbg !298
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !300
  %".8" = load i64, i64* %".7", !dbg !300
  %".9" = load i64, i64* %"needed", !dbg !300
  %".10" = icmp sge i64 %".8", %".9" , !dbg !300
  br i1 %".10", label %"if.then", label %"if.end", !dbg !300
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !301
  ret i32 %".12", !dbg !301
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !302
  %".15" = load i64, i64* %".14", !dbg !302
  store i64 %".15", i64* %"new_cap.addr", !dbg !302
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !303, metadata !7), !dbg !304
  %".18" = load i64, i64* %"new_cap.addr", !dbg !305
  %".19" = icmp eq i64 %".18", 0 , !dbg !305
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !305
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !306
  br label %"if.end.1", !dbg !306
if.end.1:
  br label %"while.cond", !dbg !307
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !307
  %".25" = load i64, i64* %"needed", !dbg !307
  %".26" = icmp slt i64 %".24", %".25" , !dbg !307
  br i1 %".26", label %"while.body", label %"while.end", !dbg !307
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !308
  %".29" = mul i64 %".28", 2, !dbg !308
  store i64 %".29", i64* %"new_cap.addr", !dbg !308
  br label %"while.cond", !dbg !308
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !309
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !309
  ret i32 %".33", !dbg !309
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !47
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !310, metadata !7), !dbg !311
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !312, metadata !7), !dbg !311
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !313
  %".8" = load i64, i64* %".7", !dbg !313
  %".9" = add i64 %".8", 1, !dbg !313
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !313
  %".11" = sext i32 %".10" to i64 , !dbg !313
  %".12" = icmp ne i64 %".11", 0 , !dbg !313
  br i1 %".12", label %"if.then", label %"if.end", !dbg !313
if.then:
  %".14" = sub i64 0, 1, !dbg !314
  %".15" = trunc i64 %".14" to i32 , !dbg !314
  ret i32 %".15", !dbg !314
if.end:
  %".17" = load i8, i8* %"item", !dbg !315
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !315
  %".19" = load i8*, i8** %".18", !dbg !315
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !315
  %".21" = load i64, i64* %".20", !dbg !315
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !315
  store i8 %".17", i8* %".22", !dbg !315
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !316
  %".25" = load i64, i64* %".24", !dbg !316
  %".26" = add i64 %".25", 1, !dbg !316
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !316
  store i64 %".26", i64* %".27", !dbg !316
  %".29" = trunc i64 0 to i32 , !dbg !317
  ret i32 %".29", !dbg !317
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !48
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !318, metadata !7), !dbg !319
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !320, metadata !7), !dbg !319
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !321
  %".8" = load i8*, i8** %".7", !dbg !321
  %".9" = load i64, i64* %"idx", !dbg !321
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !321
  %".11" = load i8, i8* %".10", !dbg !321
  ret i8 %".11", !dbg !321
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !49
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !327
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !322, metadata !7), !dbg !323
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !324, metadata !7), !dbg !323
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !325
  %".8" = load i64, i64* %".7", !dbg !325
  %".9" = load i64, i64* %"needed", !dbg !325
  %".10" = icmp sge i64 %".8", %".9" , !dbg !325
  br i1 %".10", label %"if.then", label %"if.end", !dbg !325
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !326
  ret i32 %".12", !dbg !326
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !327
  %".15" = load i64, i64* %".14", !dbg !327
  store i64 %".15", i64* %"new_cap.addr", !dbg !327
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !328, metadata !7), !dbg !329
  %".18" = load i64, i64* %"new_cap.addr", !dbg !330
  %".19" = icmp eq i64 %".18", 0 , !dbg !330
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !330
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !331
  br label %"if.end.1", !dbg !331
if.end.1:
  br label %"while.cond", !dbg !332
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !332
  %".25" = load i64, i64* %"needed", !dbg !332
  %".26" = icmp slt i64 %".24", %".25" , !dbg !332
  br i1 %".26", label %"while.body", label %"while.end", !dbg !332
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !333
  %".29" = mul i64 %".28", 2, !dbg !333
  store i64 %".29", i64* %"new_cap.addr", !dbg !333
  br label %"while.cond", !dbg !333
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !334
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !334
  ret i32 %".33", !dbg !334
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !50
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !335, metadata !7), !dbg !336
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !337, metadata !7), !dbg !336
  %".7" = load i64, i64* %"new_cap", !dbg !338
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !338
  %".9" = load i64, i64* %".8", !dbg !338
  %".10" = icmp sle i64 %".7", %".9" , !dbg !338
  br i1 %".10", label %"if.then", label %"if.end", !dbg !338
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !339
  ret i32 %".12", !dbg !339
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !340
  %".15" = mul i64 %".14", 1, !dbg !340
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !341
  %".17" = load i8*, i8** %".16", !dbg !341
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !341
  %".19" = icmp eq i8* %".18", null , !dbg !342
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !342
if.then.1:
  %".21" = sub i64 0, 1, !dbg !343
  %".22" = trunc i64 %".21" to i32 , !dbg !343
  ret i32 %".22", !dbg !343
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !344
  store i8* %".18", i8** %".24", !dbg !344
  %".26" = load i64, i64* %"new_cap", !dbg !345
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !345
  store i64 %".26", i64* %".27", !dbg !345
  %".29" = trunc i64 0 to i32 , !dbg !346
  ret i32 %".29", !dbg !346
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !51
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !347, metadata !7), !dbg !348
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !349, metadata !7), !dbg !348
  %".7" = load i64, i64* %"new_cap", !dbg !350
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !350
  %".9" = load i64, i64* %".8", !dbg !350
  %".10" = icmp sle i64 %".7", %".9" , !dbg !350
  br i1 %".10", label %"if.then", label %"if.end", !dbg !350
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !351
  ret i32 %".12", !dbg !351
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !352
  %".15" = mul i64 %".14", 16, !dbg !352
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !353
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !353
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !353
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !353
  %".20" = icmp eq i8* %".19", null , !dbg !354
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !354
if.then.1:
  %".22" = sub i64 0, 1, !dbg !355
  %".23" = trunc i64 %".22" to i32 , !dbg !355
  ret i32 %".23", !dbg !355
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !356
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !356
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !356
  %".28" = load i64, i64* %"new_cap", !dbg !357
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !357
  store i64 %".28", i64* %".29", !dbg !357
  %".31" = trunc i64 0 to i32 , !dbg !358
  ret i32 %".31", !dbg !358
}

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
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/cryptosec/tmp5f6j9sju", filename: "test_main.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 20, name: "test_mem_zero_basic", scopeLine: 20, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 35, name: "test_mem_zero_partial", scopeLine: 35, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 52, name: "test_mem_zero_empty", scopeLine: 52, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 67, name: "test_mem_eq_equal", scopeLine: 67, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 80, name: "test_mem_eq_different", scopeLine: 80, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 96, name: "test_mem_eq_first_byte_differs", scopeLine: 96, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 105, name: "test_mem_eq_last_byte_differs", scopeLine: 105, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 114, name: "test_mem_eq_empty", scopeLine: 114, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 128, name: "test_mem_copy_basic", scopeLine: 128, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 142, name: "test_mem_copy_partial", scopeLine: 142, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 160, name: "test_mem_copy_empty", scopeLine: 160, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 174, name: "test_ct_select_u8_true", scopeLine: 174, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 184, name: "test_ct_select_u8_false", scopeLine: 184, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 194, name: "test_ct_select_u64_true", scopeLine: 194, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 203, name: "test_ct_select_u64_false", scopeLine: 203, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 216, name: "test_ct_is_zero_zero", scopeLine: 216, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 222, name: "test_ct_is_zero_nonzero", scopeLine: 222, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "test_mem_is_zero_all_zeros", scopeLine: 235, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 245, name: "test_mem_is_zero_has_nonzero", scopeLine: 245, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 256, name: "test_mem_is_zero_empty", scopeLine: 256, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 264, name: "main", scopeLine: 264, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!51 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!52 = !DILocation(column: 5, line: 22, scope: !17)
!53 = !DISubrange(count: 16)
!54 = !{ !53 }
!55 = !DICompositeType(baseType: !12, elements: !54, size: 128, tag: DW_TAG_array_type)
!56 = !DILocalVariable(file: !0, line: 22, name: "buf", scope: !17, type: !55)
!57 = !DILocation(column: 1, line: 22, scope: !17)
!58 = !DILocation(column: 5, line: 23, scope: !17)
!59 = !DILocation(column: 5, line: 24, scope: !17)
!60 = !DILocation(column: 5, line: 25, scope: !17)
!61 = !DILocation(column: 5, line: 27, scope: !17)
!62 = !DILocation(column: 5, line: 29, scope: !17)
!63 = !DILocation(column: 5, line: 30, scope: !17)
!64 = !DILocation(column: 5, line: 31, scope: !17)
!65 = !DILocation(column: 5, line: 32, scope: !17)
!66 = !DILocation(column: 5, line: 37, scope: !18)
!67 = !DILocalVariable(file: !0, line: 37, name: "buf", scope: !18, type: !55)
!68 = !DILocation(column: 1, line: 37, scope: !18)
!69 = !DILocation(column: 5, line: 38, scope: !18)
!70 = !DILocation(column: 9, line: 39, scope: !18)
!71 = !DILocation(column: 5, line: 42, scope: !18)
!72 = !DILocation(column: 5, line: 44, scope: !18)
!73 = !DILocation(column: 5, line: 45, scope: !18)
!74 = !DILocation(column: 5, line: 46, scope: !18)
!75 = !DILocation(column: 5, line: 47, scope: !18)
!76 = !DILocation(column: 5, line: 48, scope: !18)
!77 = !DILocation(column: 5, line: 49, scope: !18)
!78 = !DILocation(column: 5, line: 54, scope: !19)
!79 = !DISubrange(count: 4)
!80 = !{ !79 }
!81 = !DICompositeType(baseType: !12, elements: !80, size: 32, tag: DW_TAG_array_type)
!82 = !DILocalVariable(file: !0, line: 54, name: "buf", scope: !19, type: !81)
!83 = !DILocation(column: 1, line: 54, scope: !19)
!84 = !DILocation(column: 5, line: 55, scope: !19)
!85 = !DILocation(column: 5, line: 57, scope: !19)
!86 = !DILocation(column: 5, line: 59, scope: !19)
!87 = !DILocation(column: 5, line: 60, scope: !19)
!88 = !DILocation(column: 5, line: 68, scope: !20)
!89 = !DISubrange(count: 8)
!90 = !{ !89 }
!91 = !DICompositeType(baseType: !12, elements: !90, size: 64, tag: DW_TAG_array_type)
!92 = !DILocalVariable(file: !0, line: 68, name: "a", scope: !20, type: !91)
!93 = !DILocation(column: 1, line: 68, scope: !20)
!94 = !DILocation(column: 5, line: 69, scope: !20)
!95 = !DILocalVariable(file: !0, line: 69, name: "b", scope: !20, type: !91)
!96 = !DILocation(column: 1, line: 69, scope: !20)
!97 = !DILocation(column: 5, line: 71, scope: !20)
!98 = !DILocation(column: 9, line: 72, scope: !20)
!99 = !DILocation(column: 9, line: 73, scope: !20)
!100 = !DILocation(column: 5, line: 75, scope: !20)
!101 = !DILocation(column: 5, line: 76, scope: !20)
!102 = !DILocation(column: 5, line: 77, scope: !20)
!103 = !DILocation(column: 5, line: 81, scope: !21)
!104 = !DILocalVariable(file: !0, line: 81, name: "a", scope: !21, type: !91)
!105 = !DILocation(column: 1, line: 81, scope: !21)
!106 = !DILocation(column: 5, line: 82, scope: !21)
!107 = !DILocalVariable(file: !0, line: 82, name: "b", scope: !21, type: !91)
!108 = !DILocation(column: 1, line: 82, scope: !21)
!109 = !DILocation(column: 5, line: 84, scope: !21)
!110 = !DILocation(column: 9, line: 85, scope: !21)
!111 = !DILocation(column: 9, line: 86, scope: !21)
!112 = !DILocation(column: 5, line: 89, scope: !21)
!113 = !DILocation(column: 5, line: 91, scope: !21)
!114 = !DILocation(column: 5, line: 92, scope: !21)
!115 = !DILocation(column: 5, line: 93, scope: !21)
!116 = !DILocation(column: 5, line: 97, scope: !22)
!117 = !DILocalVariable(file: !0, line: 97, name: "a", scope: !22, type: !81)
!118 = !DILocation(column: 1, line: 97, scope: !22)
!119 = !DILocation(column: 5, line: 98, scope: !22)
!120 = !DILocalVariable(file: !0, line: 98, name: "b", scope: !22, type: !81)
!121 = !DILocation(column: 1, line: 98, scope: !22)
!122 = !DILocation(column: 5, line: 100, scope: !22)
!123 = !DILocation(column: 5, line: 101, scope: !22)
!124 = !DILocation(column: 5, line: 102, scope: !22)
!125 = !DILocation(column: 5, line: 106, scope: !23)
!126 = !DILocalVariable(file: !0, line: 106, name: "a", scope: !23, type: !81)
!127 = !DILocation(column: 1, line: 106, scope: !23)
!128 = !DILocation(column: 5, line: 107, scope: !23)
!129 = !DILocalVariable(file: !0, line: 107, name: "b", scope: !23, type: !81)
!130 = !DILocation(column: 1, line: 107, scope: !23)
!131 = !DILocation(column: 5, line: 109, scope: !23)
!132 = !DILocation(column: 5, line: 110, scope: !23)
!133 = !DILocation(column: 5, line: 111, scope: !23)
!134 = !DILocation(column: 5, line: 115, scope: !24)
!135 = !DILocalVariable(file: !0, line: 115, name: "a", scope: !24, type: !81)
!136 = !DILocation(column: 1, line: 115, scope: !24)
!137 = !DILocation(column: 5, line: 116, scope: !24)
!138 = !DILocalVariable(file: !0, line: 116, name: "b", scope: !24, type: !81)
!139 = !DILocation(column: 1, line: 116, scope: !24)
!140 = !DILocation(column: 5, line: 119, scope: !24)
!141 = !DILocation(column: 5, line: 120, scope: !24)
!142 = !DILocation(column: 5, line: 121, scope: !24)
!143 = !DILocation(column: 5, line: 129, scope: !25)
!144 = !DILocalVariable(file: !0, line: 129, name: "src", scope: !25, type: !91)
!145 = !DILocation(column: 1, line: 129, scope: !25)
!146 = !DILocation(column: 5, line: 130, scope: !25)
!147 = !DILocalVariable(file: !0, line: 130, name: "dst", scope: !25, type: !91)
!148 = !DILocation(column: 1, line: 130, scope: !25)
!149 = !DILocation(column: 5, line: 132, scope: !25)
!150 = !DILocation(column: 9, line: 133, scope: !25)
!151 = !DILocation(column: 5, line: 135, scope: !25)
!152 = !DILocation(column: 5, line: 137, scope: !25)
!153 = !DILocation(column: 5, line: 138, scope: !25)
!154 = !DILocation(column: 5, line: 139, scope: !25)
!155 = !DILocation(column: 5, line: 143, scope: !26)
!156 = !DILocalVariable(file: !0, line: 143, name: "src", scope: !26, type: !91)
!157 = !DILocation(column: 1, line: 143, scope: !26)
!158 = !DILocation(column: 5, line: 144, scope: !26)
!159 = !DILocalVariable(file: !0, line: 144, name: "dst", scope: !26, type: !91)
!160 = !DILocation(column: 1, line: 144, scope: !26)
!161 = !DILocation(column: 5, line: 146, scope: !26)
!162 = !DILocation(column: 9, line: 147, scope: !26)
!163 = !DILocation(column: 5, line: 150, scope: !26)
!164 = !DILocation(column: 5, line: 152, scope: !26)
!165 = !DILocation(column: 5, line: 153, scope: !26)
!166 = !DILocation(column: 5, line: 154, scope: !26)
!167 = !DILocation(column: 5, line: 155, scope: !26)
!168 = !DILocation(column: 5, line: 156, scope: !26)
!169 = !DILocation(column: 5, line: 157, scope: !26)
!170 = !DILocation(column: 5, line: 161, scope: !27)
!171 = !DILocalVariable(file: !0, line: 161, name: "src", scope: !27, type: !81)
!172 = !DILocation(column: 1, line: 161, scope: !27)
!173 = !DILocation(column: 5, line: 162, scope: !27)
!174 = !DILocalVariable(file: !0, line: 162, name: "dst", scope: !27, type: !81)
!175 = !DILocation(column: 1, line: 162, scope: !27)
!176 = !DILocation(column: 5, line: 164, scope: !27)
!177 = !DILocation(column: 5, line: 166, scope: !27)
!178 = !DILocation(column: 5, line: 167, scope: !27)
!179 = !DILocation(column: 5, line: 175, scope: !28)
!180 = !DILocation(column: 5, line: 176, scope: !28)
!181 = !DILocation(column: 5, line: 179, scope: !28)
!182 = !DILocation(column: 5, line: 180, scope: !28)
!183 = !DILocation(column: 5, line: 181, scope: !28)
!184 = !DILocation(column: 5, line: 185, scope: !29)
!185 = !DILocation(column: 5, line: 186, scope: !29)
!186 = !DILocation(column: 5, line: 189, scope: !29)
!187 = !DILocation(column: 5, line: 190, scope: !29)
!188 = !DILocation(column: 5, line: 191, scope: !29)
!189 = !DILocation(column: 5, line: 195, scope: !30)
!190 = !DILocation(column: 5, line: 196, scope: !30)
!191 = !DILocation(column: 5, line: 198, scope: !30)
!192 = !DILocation(column: 5, line: 199, scope: !30)
!193 = !DILocation(column: 5, line: 200, scope: !30)
!194 = !DILocation(column: 5, line: 204, scope: !31)
!195 = !DILocation(column: 5, line: 205, scope: !31)
!196 = !DILocation(column: 5, line: 207, scope: !31)
!197 = !DILocation(column: 5, line: 208, scope: !31)
!198 = !DILocation(column: 5, line: 209, scope: !31)
!199 = !DILocation(column: 5, line: 217, scope: !32)
!200 = !DILocation(column: 5, line: 218, scope: !32)
!201 = !DILocation(column: 5, line: 219, scope: !32)
!202 = !DILocation(column: 5, line: 223, scope: !33)
!203 = !DILocation(column: 5, line: 224, scope: !33)
!204 = !DILocation(column: 5, line: 226, scope: !33)
!205 = !DILocation(column: 5, line: 227, scope: !33)
!206 = !DILocation(column: 5, line: 228, scope: !33)
!207 = !DILocation(column: 5, line: 236, scope: !34)
!208 = !DILocalVariable(file: !0, line: 236, name: "buf", scope: !34, type: !55)
!209 = !DILocation(column: 1, line: 236, scope: !34)
!210 = !DILocation(column: 5, line: 237, scope: !34)
!211 = !DILocation(column: 9, line: 238, scope: !34)
!212 = !DILocation(column: 5, line: 240, scope: !34)
!213 = !DILocation(column: 5, line: 241, scope: !34)
!214 = !DILocation(column: 5, line: 242, scope: !34)
!215 = !DILocation(column: 5, line: 246, scope: !35)
!216 = !DILocalVariable(file: !0, line: 246, name: "buf", scope: !35, type: !55)
!217 = !DILocation(column: 1, line: 246, scope: !35)
!218 = !DILocation(column: 5, line: 247, scope: !35)
!219 = !DILocation(column: 9, line: 248, scope: !35)
!220 = !DILocation(column: 5, line: 249, scope: !35)
!221 = !DILocation(column: 5, line: 251, scope: !35)
!222 = !DILocation(column: 5, line: 252, scope: !35)
!223 = !DILocation(column: 5, line: 253, scope: !35)
!224 = !DILocation(column: 5, line: 257, scope: !36)
!225 = !DILocalVariable(file: !0, line: 257, name: "buf", scope: !36, type: !81)
!226 = !DILocation(column: 1, line: 257, scope: !36)
!227 = !DILocation(column: 5, line: 259, scope: !36)
!228 = !DILocation(column: 5, line: 260, scope: !36)
!229 = !DILocation(column: 5, line: 261, scope: !36)
!230 = !DILocation(column: 3, line: 265, scope: !37)
!231 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!232 = !DIDerivedType(baseType: !231, size: 64, tag: DW_TAG_reference_type)
!233 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !38, type: !232)
!234 = !DILocation(column: 1, line: 288, scope: !38)
!235 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!236 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !38, type: !235)
!237 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !38, type: !11)
!238 = !DILocation(column: 5, line: 289, scope: !38)
!239 = !DILocation(column: 13, line: 291, scope: !38)
!240 = !DILocation(column: 5, line: 292, scope: !38)
!241 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !39, type: !232)
!242 = !DILocation(column: 1, line: 244, scope: !39)
!243 = !DILocation(column: 5, line: 245, scope: !39)
!244 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !40, type: !232)
!245 = !DILocation(column: 1, line: 219, scope: !40)
!246 = !DILocation(column: 5, line: 220, scope: !40)
!247 = !DILocation(column: 5, line: 221, scope: !40)
!248 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !41, type: !11)
!249 = !DILocation(column: 1, line: 124, scope: !41)
!250 = !DILocation(column: 5, line: 125, scope: !41)
!251 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !41, type: !231)
!252 = !DILocation(column: 1, line: 125, scope: !41)
!253 = !DILocation(column: 5, line: 126, scope: !41)
!254 = !DILocation(column: 9, line: 127, scope: !41)
!255 = !DILocation(column: 9, line: 128, scope: !41)
!256 = !DILocation(column: 9, line: 129, scope: !41)
!257 = !DILocation(column: 9, line: 130, scope: !41)
!258 = !DILocation(column: 5, line: 132, scope: !41)
!259 = !DILocation(column: 5, line: 133, scope: !41)
!260 = !DILocation(column: 5, line: 134, scope: !41)
!261 = !DILocation(column: 9, line: 135, scope: !41)
!262 = !DILocation(column: 9, line: 136, scope: !41)
!263 = !DILocation(column: 9, line: 137, scope: !41)
!264 = !DILocation(column: 5, line: 139, scope: !41)
!265 = !DILocation(column: 5, line: 140, scope: !41)
!266 = !DILocation(column: 5, line: 141, scope: !41)
!267 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !42, type: !232)
!268 = !DILocation(column: 1, line: 235, scope: !42)
!269 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !42, type: !11)
!270 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !42, type: !12)
!271 = !DILocation(column: 5, line: 236, scope: !42)
!272 = !DILocation(column: 5, line: 237, scope: !42)
!273 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !43, type: !232)
!274 = !DILocation(column: 1, line: 148, scope: !43)
!275 = !DILocation(column: 5, line: 149, scope: !43)
!276 = !DILocation(column: 5, line: 151, scope: !43)
!277 = !DILocation(column: 5, line: 152, scope: !43)
!278 = !DILocation(column: 5, line: 153, scope: !43)
!279 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!280 = !DIDerivedType(baseType: !279, size: 64, tag: DW_TAG_reference_type)
!281 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !44, type: !280)
!282 = !DILocation(column: 1, line: 210, scope: !44)
!283 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!284 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !44, type: !283)
!285 = !DILocation(column: 5, line: 211, scope: !44)
!286 = !DILocation(column: 9, line: 212, scope: !44)
!287 = !DILocation(column: 5, line: 213, scope: !44)
!288 = !DILocation(column: 5, line: 214, scope: !44)
!289 = !DILocation(column: 5, line: 215, scope: !44)
!290 = !DILocation(column: 5, line: 117, scope: !45)
!291 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !45, type: !231)
!292 = !DILocation(column: 1, line: 117, scope: !45)
!293 = !DILocation(column: 5, line: 118, scope: !45)
!294 = !DILocation(column: 5, line: 119, scope: !45)
!295 = !DILocation(column: 5, line: 120, scope: !45)
!296 = !DILocation(column: 5, line: 121, scope: !45)
!297 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !46, type: !232)
!298 = !DILocation(column: 1, line: 193, scope: !46)
!299 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !46, type: !11)
!300 = !DILocation(column: 5, line: 194, scope: !46)
!301 = !DILocation(column: 9, line: 195, scope: !46)
!302 = !DILocation(column: 5, line: 197, scope: !46)
!303 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !46, type: !11)
!304 = !DILocation(column: 1, line: 197, scope: !46)
!305 = !DILocation(column: 5, line: 198, scope: !46)
!306 = !DILocation(column: 9, line: 199, scope: !46)
!307 = !DILocation(column: 5, line: 200, scope: !46)
!308 = !DILocation(column: 9, line: 201, scope: !46)
!309 = !DILocation(column: 5, line: 203, scope: !46)
!310 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !47, type: !232)
!311 = !DILocation(column: 1, line: 210, scope: !47)
!312 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !47, type: !12)
!313 = !DILocation(column: 5, line: 211, scope: !47)
!314 = !DILocation(column: 9, line: 212, scope: !47)
!315 = !DILocation(column: 5, line: 213, scope: !47)
!316 = !DILocation(column: 5, line: 214, scope: !47)
!317 = !DILocation(column: 5, line: 215, scope: !47)
!318 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !48, type: !232)
!319 = !DILocation(column: 1, line: 225, scope: !48)
!320 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !48, type: !11)
!321 = !DILocation(column: 5, line: 226, scope: !48)
!322 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !49, type: !280)
!323 = !DILocation(column: 1, line: 193, scope: !49)
!324 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !49, type: !11)
!325 = !DILocation(column: 5, line: 194, scope: !49)
!326 = !DILocation(column: 9, line: 195, scope: !49)
!327 = !DILocation(column: 5, line: 197, scope: !49)
!328 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !49, type: !11)
!329 = !DILocation(column: 1, line: 197, scope: !49)
!330 = !DILocation(column: 5, line: 198, scope: !49)
!331 = !DILocation(column: 9, line: 199, scope: !49)
!332 = !DILocation(column: 5, line: 200, scope: !49)
!333 = !DILocation(column: 9, line: 201, scope: !49)
!334 = !DILocation(column: 5, line: 203, scope: !49)
!335 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !50, type: !232)
!336 = !DILocation(column: 1, line: 179, scope: !50)
!337 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !50, type: !11)
!338 = !DILocation(column: 5, line: 180, scope: !50)
!339 = !DILocation(column: 9, line: 181, scope: !50)
!340 = !DILocation(column: 5, line: 183, scope: !50)
!341 = !DILocation(column: 5, line: 184, scope: !50)
!342 = !DILocation(column: 5, line: 185, scope: !50)
!343 = !DILocation(column: 9, line: 186, scope: !50)
!344 = !DILocation(column: 5, line: 188, scope: !50)
!345 = !DILocation(column: 5, line: 189, scope: !50)
!346 = !DILocation(column: 5, line: 190, scope: !50)
!347 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !51, type: !280)
!348 = !DILocation(column: 1, line: 179, scope: !51)
!349 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !51, type: !11)
!350 = !DILocation(column: 5, line: 180, scope: !51)
!351 = !DILocation(column: 9, line: 181, scope: !51)
!352 = !DILocation(column: 5, line: 183, scope: !51)
!353 = !DILocation(column: 5, line: 184, scope: !51)
!354 = !DILocation(column: 5, line: 185, scope: !51)
!355 = !DILocation(column: 9, line: 186, scope: !51)
!356 = !DILocation(column: 5, line: 188, scope: !51)
!357 = !DILocation(column: 5, line: 189, scope: !51)
!358 = !DILocation(column: 5, line: 190, scope: !51)