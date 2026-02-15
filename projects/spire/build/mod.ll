; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Vec$u8" = type {i8*, i64, i64}
%"struct.ritz_module_1.Vec$LineBounds" = type {%"struct.ritz_module_1.LineBounds"*, i64, i64}
%"struct.ritz_module_1.Vec$Condition" = type {%"struct.ritz_module_1.Condition"*, i64, i64}
%"enum.ritz_module_1.Option$i64" = type {i8, [7 x i8], [8 x i8]}
%"enum.ritz_module_1.Option$Uuid" = type {i8, [7 x i8], [8 x i8]}
%"enum.ritz_module_1.Option$OrderBy" = type {i8, [7 x i8], [8 x i8]}
%"struct.ritz_module_1.Stat" = type {i64, i64, i64, i32, i32, i32, i32, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64}
%"struct.ritz_module_1.Dirent64" = type {i64, i64, i16, i8}
%"struct.ritz_module_1.Timeval" = type {i64, i64}
%"struct.ritz_module_1.Arena" = type {i8*, i64, i64}
%"struct.ritz_module_1.BlockHeader" = type {i64}
%"struct.ritz_module_1.FreeNode" = type {%"struct.ritz_module_1.FreeNode"*}
%"struct.ritz_module_1.SizeBin" = type {%"struct.ritz_module_1.FreeNode"*, i64, i8*, i64, i64}
%"struct.ritz_module_1.GlobalAlloc" = type {[9 x %"struct.ritz_module_1.SizeBin"], i32}
%"struct.ritz_module_1.StrView" = type {i8*, i64}
%"struct.ritz_module_1.LineBounds" = type {i64, i64}
%"struct.ritz_module_1.String" = type {%"struct.ritz_module_1.Vec$u8"}
%"struct.ritz_module_1.Uuid" = type {[16 x i8]}
%"struct.ritz_module_1.Condition" = type {%"struct.ritz_module_1.String", %"enum.ritz_module_1.ConditionOp", %"struct.ritz_module_1.String"}
%"struct.ritz_module_1.OrderBy" = type {%"struct.ritz_module_1.String", %"enum.ritz_module_1.SortDir"}
%"enum.ritz_module_1.RepoError" = type {i8, [7 x i8], [24 x i8]}
%"enum.ritz_module_1.SortDir" = type {i8}
%"enum.ritz_module_1.ConditionOp" = type {i8}
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

declare i32 @"vec_push_str"(%"struct.ritz_module_1.Vec$u8"** %".1", i8* %".2")

declare i8* @"vec_as_str"(%"struct.ritz_module_1.Vec$u8"** %".1")

declare i64 @"vec_read_all_fd"(i32 %".1", %"struct.ritz_module_1.Vec$u8"** %".2")

declare i32 @"vec_find_lines"(%"struct.ritz_module_1.Vec$u8"* %".1", %"struct.ritz_module_1.Vec$LineBounds"** %".2")

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

declare i32 @"string_drop"(%"struct.ritz_module_1.String"** %".1")

declare i64 @"string_len"(%"struct.ritz_module_1.String"* %".1")

declare i64 @"string_cap"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"string_is_empty"(%"struct.ritz_module_1.String"* %".1")

declare i8* @"string_as_ptr"(%"struct.ritz_module_1.String"** %".1")

declare i8 @"string_get"(%"struct.ritz_module_1.String"* %".1", i64 %".2")

declare i32 @"string_push"(%"struct.ritz_module_1.String"** %".1", i8 %".2")

declare i32 @"string_push_str"(%"struct.ritz_module_1.String"** %".1", i8* %".2")

declare i32 @"string_push_string"(%"struct.ritz_module_1.String"** %".1", %"struct.ritz_module_1.String"* %".2")

declare i32 @"string_push_bytes"(%"struct.ritz_module_1.String"** %".1", i8* %".2", i64 %".3")

declare i32 @"string_clear"(%"struct.ritz_module_1.String"** %".1")

declare i8 @"string_pop"(%"struct.ritz_module_1.String"** %".1")

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

declare i32 @"string_set_char"(%"struct.ritz_module_1.String"** %".1", i64 %".2", i8 %".3")

declare i32 @"string_starts_with"(%"struct.ritz_module_1.String"* %".1", i8* %".2")

declare i32 @"string_ends_with"(%"struct.ritz_module_1.String"* %".1", i8* %".2")

declare i32 @"string_contains"(%"struct.ritz_module_1.String"* %".1", i8* %".2")

declare %"struct.ritz_module_1.String" @"string_from_i64"(i64 %".1")

declare i32 @"string_push_i64"(%"struct.ritz_module_1.String"** %".1", i64 %".2")

declare %"struct.ritz_module_1.String" @"string_from_hex"(i64 %".1")

declare %"struct.ritz_module_1.Uuid" @"uuid_zero"()

declare %"struct.ritz_module_1.Uuid" @"uuid_new_v4"()

declare %"enum.ritz_module_1.Option$Uuid" @"uuid_from_str"(%"struct.ritz_module_1.StrView"* %".1")

declare %"struct.ritz_module_1.String" @"uuid_to_string"(%"struct.ritz_module_1.Uuid"* %".1")

declare i32 @"uuid_eq"(%"struct.ritz_module_1.Uuid"* %".1", %"struct.ritz_module_1.Uuid"* %".2")

declare i32 @"uuid_is_zero"(%"struct.ritz_module_1.Uuid"* %".1")

declare i32 @"hex_char_to_val"(i8 %".1")

declare i8 @"val_to_hex_char"(i8 %".1")

declare %"struct.ritz_module_1.StrView" @"string_as_strview"(%"struct.ritz_module_1.String"* %".1")

define %"struct.ritz_module_1.StrView" @"repo_error_message"(%"enum.ritz_module_1.RepoError"* %"err.arg") !dbg !17
{
entry:
  %"err" = alloca %"enum.ritz_module_1.RepoError"*
  store %"enum.ritz_module_1.RepoError"* %"err.arg", %"enum.ritz_module_1.RepoError"** %"err"
  call void @"llvm.dbg.declare"(metadata %"enum.ritz_module_1.RepoError"** %"err", metadata !39, metadata !7), !dbg !40
  %".5" = load %"enum.ritz_module_1.RepoError"*, %"enum.ritz_module_1.RepoError"** %"err", !dbg !41
  %".6" = load %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %".5", !dbg !41
  %"match.enum" = alloca %"enum.ritz_module_1.RepoError", !dbg !41
  store %"enum.ritz_module_1.RepoError" %".6", %"enum.ritz_module_1.RepoError"* %"match.enum", !dbg !41
  %".8" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"match.enum", i32 0, i32 0 , !dbg !41
  %".9" = load i8, i8* %".8", !dbg !41
  switch i8 %".9", label %"match.unreachable" [i8 0, label %"match.arm.0" i8 1, label %"match.arm.1" i8 2, label %"match.arm.2" i8 3, label %"match.arm.3" i8 4, label %"match.arm.4" i8 5, label %"match.arm.5"]  , !dbg !41
match.arm.0:
  %".12" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"match.enum", i32 0, i32 2 , !dbg !41
  %".13" = getelementptr [24 x i8], [24 x i8]* %".12", i32 0 , !dbg !41
  %".14" = bitcast [24 x i8]* %".13" to %"struct.ritz_module_1.String"* , !dbg !41
  %".15" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %".14", !dbg !41
  %"msg.addr" = alloca %"struct.ritz_module_1.String", !dbg !41
  store %"struct.ritz_module_1.String" %".15", %"struct.ritz_module_1.String"* %"msg.addr", !dbg !41
  %".17" = call %"struct.ritz_module_1.StrView" @"string_as_strview"(%"struct.ritz_module_1.String"* %"msg.addr"), !dbg !41
  br label %"match.merge", !dbg !41
match.arm.1:
  %".19" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"match.enum", i32 0, i32 2 , !dbg !41
  %".20" = getelementptr [24 x i8], [24 x i8]* %".19", i32 0 , !dbg !41
  %".21" = bitcast [24 x i8]* %".20" to %"struct.ritz_module_1.String"* , !dbg !41
  %".22" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %".21", !dbg !41
  %"msg.addr.1" = alloca %"struct.ritz_module_1.String", !dbg !41
  store %"struct.ritz_module_1.String" %".22", %"struct.ritz_module_1.String"* %"msg.addr.1", !dbg !41
  %".24" = call %"struct.ritz_module_1.StrView" @"string_as_strview"(%"struct.ritz_module_1.String"* %"msg.addr.1"), !dbg !41
  br label %"match.merge", !dbg !41
match.arm.2:
  %".26" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"match.enum", i32 0, i32 2 , !dbg !41
  %".27" = getelementptr [24 x i8], [24 x i8]* %".26", i32 0 , !dbg !41
  %".28" = bitcast [24 x i8]* %".27" to %"struct.ritz_module_1.String"* , !dbg !41
  %".29" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %".28", !dbg !41
  %"msg.addr.2" = alloca %"struct.ritz_module_1.String", !dbg !41
  store %"struct.ritz_module_1.String" %".29", %"struct.ritz_module_1.String"* %"msg.addr.2", !dbg !41
  %".31" = call %"struct.ritz_module_1.StrView" @"string_as_strview"(%"struct.ritz_module_1.String"* %"msg.addr.2"), !dbg !41
  br label %"match.merge", !dbg !41
match.arm.3:
  %".33" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"match.enum", i32 0, i32 2 , !dbg !41
  %".34" = getelementptr [24 x i8], [24 x i8]* %".33", i32 0 , !dbg !41
  %".35" = bitcast [24 x i8]* %".34" to %"struct.ritz_module_1.String"* , !dbg !41
  %".36" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %".35", !dbg !41
  %"msg.addr.3" = alloca %"struct.ritz_module_1.String", !dbg !41
  store %"struct.ritz_module_1.String" %".36", %"struct.ritz_module_1.String"* %"msg.addr.3", !dbg !41
  %".38" = call %"struct.ritz_module_1.StrView" @"string_as_strview"(%"struct.ritz_module_1.String"* %"msg.addr.3"), !dbg !41
  br label %"match.merge", !dbg !41
match.arm.4:
  %".40" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"match.enum", i32 0, i32 2 , !dbg !41
  %".41" = getelementptr [24 x i8], [24 x i8]* %".40", i32 0 , !dbg !41
  %".42" = bitcast [24 x i8]* %".41" to %"struct.ritz_module_1.String"* , !dbg !41
  %".43" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %".42", !dbg !41
  %"msg.addr.4" = alloca %"struct.ritz_module_1.String", !dbg !41
  store %"struct.ritz_module_1.String" %".43", %"struct.ritz_module_1.String"* %"msg.addr.4", !dbg !41
  %".45" = call %"struct.ritz_module_1.StrView" @"string_as_strview"(%"struct.ritz_module_1.String"* %"msg.addr.4"), !dbg !41
  br label %"match.merge", !dbg !41
match.arm.5:
  %".47" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"match.enum", i32 0, i32 2 , !dbg !41
  %".48" = getelementptr [24 x i8], [24 x i8]* %".47", i32 0 , !dbg !41
  %".49" = bitcast [24 x i8]* %".48" to %"struct.ritz_module_1.String"* , !dbg !41
  %".50" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %".49", !dbg !41
  %"msg.addr.5" = alloca %"struct.ritz_module_1.String", !dbg !41
  store %"struct.ritz_module_1.String" %".50", %"struct.ritz_module_1.String"* %"msg.addr.5", !dbg !41
  %".52" = call %"struct.ritz_module_1.StrView" @"string_as_strview"(%"struct.ritz_module_1.String"* %"msg.addr.5"), !dbg !41
  br label %"match.merge", !dbg !41
match.merge:
  %".54" = phi  %"struct.ritz_module_1.StrView" [%".17", %"match.arm.0"], [%".24", %"match.arm.1"], [%".31", %"match.arm.2"], [%".38", %"match.arm.3"], [%".45", %"match.arm.4"], [%".52", %"match.arm.5"] , !dbg !41
  ret %"struct.ritz_module_1.StrView" %".54", !dbg !41
match.unreachable:
  unreachable
}

define %"enum.ritz_module_1.RepoError" @"repo_error_not_found"(%"struct.ritz_module_1.StrView"* %"msg.arg") !dbg !18
{
entry:
  %"msg" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"msg.arg", %"struct.ritz_module_1.StrView"** %"msg"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"msg", metadata !44, metadata !7), !dbg !45
  %"NotFound.alloca" = alloca %"enum.ritz_module_1.RepoError", !dbg !46
  %".5" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"NotFound.alloca", i32 0, i32 0 , !dbg !46
  store i8 0, i8* %".5", !dbg !46
  %".7" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"NotFound.alloca", i32 0, i32 2 , !dbg !46
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"msg", !dbg !46
  %".9" = call %"struct.ritz_module_1.String" @"string_from_strview"(%"struct.ritz_module_1.StrView"* %".8"), !dbg !46
  %".10" = getelementptr [24 x i8], [24 x i8]* %".7", i32 0 , !dbg !46
  %".11" = bitcast [24 x i8]* %".10" to %"struct.ritz_module_1.String"* , !dbg !46
  store %"struct.ritz_module_1.String" %".9", %"struct.ritz_module_1.String"* %".11", !dbg !46
  %".13" = load %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"NotFound.alloca", !dbg !46
  ret %"enum.ritz_module_1.RepoError" %".13", !dbg !46
}

define %"enum.ritz_module_1.RepoError" @"repo_error_duplicate"(%"struct.ritz_module_1.StrView"* %"msg.arg") !dbg !19
{
entry:
  %"msg" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"msg.arg", %"struct.ritz_module_1.StrView"** %"msg"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"msg", metadata !47, metadata !7), !dbg !48
  %"DuplicateKey.alloca" = alloca %"enum.ritz_module_1.RepoError", !dbg !49
  %".5" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"DuplicateKey.alloca", i32 0, i32 0 , !dbg !49
  store i8 1, i8* %".5", !dbg !49
  %".7" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"DuplicateKey.alloca", i32 0, i32 2 , !dbg !49
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"msg", !dbg !49
  %".9" = call %"struct.ritz_module_1.String" @"string_from_strview"(%"struct.ritz_module_1.StrView"* %".8"), !dbg !49
  %".10" = getelementptr [24 x i8], [24 x i8]* %".7", i32 0 , !dbg !49
  %".11" = bitcast [24 x i8]* %".10" to %"struct.ritz_module_1.String"* , !dbg !49
  store %"struct.ritz_module_1.String" %".9", %"struct.ritz_module_1.String"* %".11", !dbg !49
  %".13" = load %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"DuplicateKey.alloca", !dbg !49
  ret %"enum.ritz_module_1.RepoError" %".13", !dbg !49
}

define %"enum.ritz_module_1.RepoError" @"repo_error_query"(%"struct.ritz_module_1.StrView"* %"msg.arg") !dbg !20
{
entry:
  %"msg" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"msg.arg", %"struct.ritz_module_1.StrView"** %"msg"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"msg", metadata !50, metadata !7), !dbg !51
  %"QueryFailed.alloca" = alloca %"enum.ritz_module_1.RepoError", !dbg !52
  %".5" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"QueryFailed.alloca", i32 0, i32 0 , !dbg !52
  store i8 3, i8* %".5", !dbg !52
  %".7" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"QueryFailed.alloca", i32 0, i32 2 , !dbg !52
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"msg", !dbg !52
  %".9" = call %"struct.ritz_module_1.String" @"string_from_strview"(%"struct.ritz_module_1.StrView"* %".8"), !dbg !52
  %".10" = getelementptr [24 x i8], [24 x i8]* %".7", i32 0 , !dbg !52
  %".11" = bitcast [24 x i8]* %".10" to %"struct.ritz_module_1.String"* , !dbg !52
  store %"struct.ritz_module_1.String" %".9", %"struct.ritz_module_1.String"* %".11", !dbg !52
  %".13" = load %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"QueryFailed.alloca", !dbg !52
  ret %"enum.ritz_module_1.RepoError" %".13", !dbg !52
}

define %"enum.ritz_module_1.RepoError" @"repo_error_connection"(%"struct.ritz_module_1.StrView"* %"msg.arg") !dbg !21
{
entry:
  %"msg" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"msg.arg", %"struct.ritz_module_1.StrView"** %"msg"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"msg", metadata !53, metadata !7), !dbg !54
  %"ConnectionFailed.alloca" = alloca %"enum.ritz_module_1.RepoError", !dbg !55
  %".5" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"ConnectionFailed.alloca", i32 0, i32 0 , !dbg !55
  store i8 2, i8* %".5", !dbg !55
  %".7" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"ConnectionFailed.alloca", i32 0, i32 2 , !dbg !55
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"msg", !dbg !55
  %".9" = call %"struct.ritz_module_1.String" @"string_from_strview"(%"struct.ritz_module_1.StrView"* %".8"), !dbg !55
  %".10" = getelementptr [24 x i8], [24 x i8]* %".7", i32 0 , !dbg !55
  %".11" = bitcast [24 x i8]* %".10" to %"struct.ritz_module_1.String"* , !dbg !55
  store %"struct.ritz_module_1.String" %".9", %"struct.ritz_module_1.String"* %".11", !dbg !55
  %".13" = load %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"ConnectionFailed.alloca", !dbg !55
  ret %"enum.ritz_module_1.RepoError" %".13", !dbg !55
}

define %"enum.ritz_module_1.RepoError" @"repo_error_transaction"(%"struct.ritz_module_1.StrView"* %"msg.arg") !dbg !22
{
entry:
  %"msg" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"msg.arg", %"struct.ritz_module_1.StrView"** %"msg"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"msg", metadata !56, metadata !7), !dbg !57
  %"TransactionFailed.alloca" = alloca %"enum.ritz_module_1.RepoError", !dbg !58
  %".5" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"TransactionFailed.alloca", i32 0, i32 0 , !dbg !58
  store i8 4, i8* %".5", !dbg !58
  %".7" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"TransactionFailed.alloca", i32 0, i32 2 , !dbg !58
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"msg", !dbg !58
  %".9" = call %"struct.ritz_module_1.String" @"string_from_strview"(%"struct.ritz_module_1.StrView"* %".8"), !dbg !58
  %".10" = getelementptr [24 x i8], [24 x i8]* %".7", i32 0 , !dbg !58
  %".11" = bitcast [24 x i8]* %".10" to %"struct.ritz_module_1.String"* , !dbg !58
  store %"struct.ritz_module_1.String" %".9", %"struct.ritz_module_1.String"* %".11", !dbg !58
  %".13" = load %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"TransactionFailed.alloca", !dbg !58
  ret %"enum.ritz_module_1.RepoError" %".13", !dbg !58
}

define %"enum.ritz_module_1.RepoError" @"repo_error_validation"(%"struct.ritz_module_1.StrView"* %"msg.arg") !dbg !23
{
entry:
  %"msg" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"msg.arg", %"struct.ritz_module_1.StrView"** %"msg"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"msg", metadata !59, metadata !7), !dbg !60
  %"ValidationFailed.alloca" = alloca %"enum.ritz_module_1.RepoError", !dbg !61
  %".5" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"ValidationFailed.alloca", i32 0, i32 0 , !dbg !61
  store i8 5, i8* %".5", !dbg !61
  %".7" = getelementptr %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"ValidationFailed.alloca", i32 0, i32 2 , !dbg !61
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"msg", !dbg !61
  %".9" = call %"struct.ritz_module_1.String" @"string_from_strview"(%"struct.ritz_module_1.StrView"* %".8"), !dbg !61
  %".10" = getelementptr [24 x i8], [24 x i8]* %".7", i32 0 , !dbg !61
  %".11" = bitcast [24 x i8]* %".10" to %"struct.ritz_module_1.String"* , !dbg !61
  store %"struct.ritz_module_1.String" %".9", %"struct.ritz_module_1.String"* %".11", !dbg !61
  %".13" = load %"enum.ritz_module_1.RepoError", %"enum.ritz_module_1.RepoError"* %"ValidationFailed.alloca", !dbg !61
  ret %"enum.ritz_module_1.RepoError" %".13", !dbg !61
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !24
{
entry:
  %"i" = alloca i64, !dbg !70
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !65, metadata !7), !dbg !66
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !68, metadata !7), !dbg !66
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !69, metadata !7), !dbg !66
  %".10" = load i64, i64* %"len", !dbg !70
  store i64 0, i64* %"i", !dbg !70
  br label %"for.cond", !dbg !70
for.cond:
  %".13" = load i64, i64* %"i", !dbg !70
  %".14" = icmp slt i64 %".13", %".10" , !dbg !70
  br i1 %".14", label %"for.body", label %"for.end", !dbg !70
for.body:
  %".16" = load i8*, i8** %"data", !dbg !70
  %".17" = load i64, i64* %"i", !dbg !70
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !70
  %".19" = load i8, i8* %".18", !dbg !70
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8 %".19"), !dbg !70
  %".21" = sext i32 %".20" to i64 , !dbg !70
  %".22" = icmp ne i64 %".21", 0 , !dbg !70
  br i1 %".22", label %"if.then", label %"if.end", !dbg !70
for.incr:
  %".28" = load i64, i64* %"i", !dbg !71
  %".29" = add i64 %".28", 1, !dbg !71
  store i64 %".29", i64* %"i", !dbg !71
  br label %"for.cond", !dbg !71
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !72
  ret i32 %".32", !dbg !72
if.then:
  %".24" = sub i64 0, 1, !dbg !71
  %".25" = trunc i64 %".24" to i32 , !dbg !71
  ret i32 %".25", !dbg !71
if.end:
  br label %"for.incr", !dbg !71
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg") !dbg !25
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !73, metadata !7), !dbg !74
  %".4" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !75
  %".5" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", i32 0, i32 1 , !dbg !75
  store i64 0, i64* %".5", !dbg !75
  ret i32 0, !dbg !75
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !26
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !76
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !77, metadata !7), !dbg !78
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !79
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !79
  store i8* null, i8** %".4", !dbg !79
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !80
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !80
  store i64 0, i64* %".7", !dbg !80
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !81
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !81
  store i64 0, i64* %".10", !dbg !81
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !82
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !82
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8 %"item.arg") !dbg !27
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !83, metadata !7), !dbg !84
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !85, metadata !7), !dbg !84
  %".7" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !86
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", i32 0, i32 1 , !dbg !86
  %".9" = load i64, i64* %".8", !dbg !86
  %".10" = add i64 %".9", 1, !dbg !86
  %".11" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %".10"), !dbg !86
  %".12" = sext i32 %".11" to i64 , !dbg !86
  %".13" = icmp ne i64 %".12", 0 , !dbg !86
  br i1 %".13", label %"if.then", label %"if.end", !dbg !86
if.then:
  %".15" = sub i64 0, 1, !dbg !87
  %".16" = trunc i64 %".15" to i32 , !dbg !87
  ret i32 %".16", !dbg !87
if.end:
  %".18" = load i8, i8* %"item", !dbg !88
  %".19" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !88
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".19", i32 0, i32 0 , !dbg !88
  %".21" = load i8*, i8** %".20", !dbg !88
  %".22" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !88
  %".23" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".22", i32 0, i32 1 , !dbg !88
  %".24" = load i64, i64* %".23", !dbg !88
  %".25" = getelementptr i8, i8* %".21", i64 %".24" , !dbg !88
  store i8 %".18", i8* %".25", !dbg !88
  %".27" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !89
  %".28" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".27", i32 0, i32 1 , !dbg !89
  %".29" = load i64, i64* %".28", !dbg !89
  %".30" = add i64 %".29", 1, !dbg !89
  %".31" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !89
  %".32" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".31", i32 0, i32 1 , !dbg !89
  store i64 %".30", i64* %".32", !dbg !89
  %".34" = trunc i64 0 to i32 , !dbg !90
  ret i32 %".34", !dbg !90
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !28
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !91, metadata !7), !dbg !92
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !93, metadata !7), !dbg !92
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !94, metadata !7), !dbg !92
  %".10" = load i8, i8* %"item", !dbg !95
  %".11" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !95
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".11", i32 0, i32 0 , !dbg !95
  %".13" = load i8*, i8** %".12", !dbg !95
  %".14" = load i64, i64* %"idx", !dbg !95
  %".15" = getelementptr i8, i8* %".13", i64 %".14" , !dbg !95
  store i8 %".10", i8* %".15", !dbg !95
  %".17" = trunc i64 0 to i32 , !dbg !96
  ret i32 %".17", !dbg !96
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !29
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !97, metadata !7), !dbg !98
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !99, metadata !7), !dbg !98
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !100
  %".8" = load i8*, i8** %".7", !dbg !100
  %".9" = load i64, i64* %"idx", !dbg !100
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !100
  %".11" = load i8, i8* %".10", !dbg !100
  ret i8 %".11", !dbg !100
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !30
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !103
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !101, metadata !7), !dbg !102
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !104, metadata !7), !dbg !105
  %".6" = load i64, i64* %"cap", !dbg !106
  %".7" = icmp sle i64 %".6", 0 , !dbg !106
  br i1 %".7", label %"if.then", label %"if.end", !dbg !106
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !107
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !107
  store i8* null, i8** %".10", !dbg !107
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !108
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !108
  store i64 0, i64* %".13", !dbg !108
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !109
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !109
  store i64 0, i64* %".16", !dbg !109
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !110
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !110
if.end:
  %".20" = load i64, i64* %"cap", !dbg !111
  %".21" = mul i64 %".20", 1, !dbg !111
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !112
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !112
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !112
  store i8* %".22", i8** %".24", !dbg !112
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !113
  %".27" = load i8*, i8** %".26", !dbg !113
  %".28" = icmp eq i8* %".27", null , !dbg !113
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !113
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !114
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !114
  store i64 0, i64* %".31", !dbg !114
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !115
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !115
  store i64 0, i64* %".34", !dbg !115
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !116
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !116
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !117
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !117
  store i64 0, i64* %".39", !dbg !117
  %".41" = load i64, i64* %"cap", !dbg !118
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !118
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !118
  store i64 %".41", i64* %".43", !dbg !118
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !119
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !119
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"needed.arg") !dbg !31
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !125
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !120, metadata !7), !dbg !121
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !122, metadata !7), !dbg !121
  %".7" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !123
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", i32 0, i32 2 , !dbg !123
  %".9" = load i64, i64* %".8", !dbg !123
  %".10" = load i64, i64* %"needed", !dbg !123
  %".11" = icmp sge i64 %".9", %".10" , !dbg !123
  br i1 %".11", label %"if.then", label %"if.end", !dbg !123
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !124
  ret i32 %".13", !dbg !124
if.end:
  %".15" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !125
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".15", i32 0, i32 2 , !dbg !125
  %".17" = load i64, i64* %".16", !dbg !125
  store i64 %".17", i64* %"new_cap.addr", !dbg !125
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !126, metadata !7), !dbg !127
  %".20" = load i64, i64* %"new_cap.addr", !dbg !128
  %".21" = icmp eq i64 %".20", 0 , !dbg !128
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !128
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !129
  br label %"if.end.1", !dbg !129
if.end.1:
  br label %"while.cond", !dbg !130
while.cond:
  %".26" = load i64, i64* %"new_cap.addr", !dbg !130
  %".27" = load i64, i64* %"needed", !dbg !130
  %".28" = icmp slt i64 %".26", %".27" , !dbg !130
  br i1 %".28", label %"while.body", label %"while.end", !dbg !130
while.body:
  %".30" = load i64, i64* %"new_cap.addr", !dbg !131
  %".31" = mul i64 %".30", 2, !dbg !131
  store i64 %".31", i64* %"new_cap.addr", !dbg !131
  br label %"while.cond", !dbg !131
while.end:
  %".34" = load i64, i64* %"new_cap.addr", !dbg !132
  %".35" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %".34"), !dbg !132
  ret i32 %".35", !dbg !132
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !32
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !136, metadata !7), !dbg !137
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !139, metadata !7), !dbg !137
  %".7" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !140
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".7", i32 0, i32 1 , !dbg !140
  %".9" = load i64, i64* %".8", !dbg !140
  %".10" = add i64 %".9", 1, !dbg !140
  %".11" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %".10"), !dbg !140
  %".12" = sext i32 %".11" to i64 , !dbg !140
  %".13" = icmp ne i64 %".12", 0 , !dbg !140
  br i1 %".13", label %"if.then", label %"if.end", !dbg !140
if.then:
  %".15" = sub i64 0, 1, !dbg !141
  %".16" = trunc i64 %".15" to i32 , !dbg !141
  ret i32 %".16", !dbg !141
if.end:
  %".18" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !142
  %".19" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !142
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".19", i32 0, i32 0 , !dbg !142
  %".21" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".20", !dbg !142
  %".22" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !142
  %".23" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".22", i32 0, i32 1 , !dbg !142
  %".24" = load i64, i64* %".23", !dbg !142
  %".25" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".21", i64 %".24" , !dbg !142
  store %"struct.ritz_module_1.LineBounds" %".18", %"struct.ritz_module_1.LineBounds"* %".25", !dbg !142
  %".27" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !143
  %".28" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".27", i32 0, i32 1 , !dbg !143
  %".29" = load i64, i64* %".28", !dbg !143
  %".30" = add i64 %".29", 1, !dbg !143
  %".31" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !143
  %".32" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".31", i32 0, i32 1 , !dbg !143
  store i64 %".30", i64* %".32", !dbg !143
  %".34" = trunc i64 0 to i32 , !dbg !144
  ret i32 %".34", !dbg !144
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg") !dbg !33
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !145, metadata !7), !dbg !146
  %".4" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !147
  %".5" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", i32 0, i32 1 , !dbg !147
  %".6" = load i64, i64* %".5", !dbg !147
  %".7" = sub i64 %".6", 1, !dbg !147
  %".8" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !147
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".8", i32 0, i32 1 , !dbg !147
  store i64 %".7", i64* %".9", !dbg !147
  %".11" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !148
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".11", i32 0, i32 0 , !dbg !148
  %".13" = load i8*, i8** %".12", !dbg !148
  %".14" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !148
  %".15" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".14", i32 0, i32 1 , !dbg !148
  %".16" = load i64, i64* %".15", !dbg !148
  %".17" = getelementptr i8, i8* %".13", i64 %".16" , !dbg !148
  %".18" = load i8, i8* %".17", !dbg !148
  ret i8 %".18", !dbg !148
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg") !dbg !34
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !149, metadata !7), !dbg !150
  %".4" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !151
  %".5" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", i32 0, i32 0 , !dbg !151
  %".6" = load i8*, i8** %".5", !dbg !151
  %".7" = icmp ne i8* %".6", null , !dbg !151
  br i1 %".7", label %"if.then", label %"if.end", !dbg !151
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !151
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".9", i32 0, i32 0 , !dbg !151
  %".11" = load i8*, i8** %".10", !dbg !151
  %".12" = call i32 @"free"(i8* %".11"), !dbg !151
  br label %"if.end", !dbg !151
if.end:
  %".14" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !152
  %".15" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".14", i32 0, i32 0 , !dbg !152
  store i8* null, i8** %".15", !dbg !152
  %".17" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !153
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".17", i32 0, i32 1 , !dbg !153
  store i64 0, i64* %".18", !dbg !153
  %".20" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !154
  %".21" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".20", i32 0, i32 2 , !dbg !154
  store i64 0, i64* %".21", !dbg !154
  ret i32 0, !dbg !154
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %"needed.arg") !dbg !35
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !160
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !155, metadata !7), !dbg !156
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !157, metadata !7), !dbg !156
  %".7" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !158
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".7", i32 0, i32 2 , !dbg !158
  %".9" = load i64, i64* %".8", !dbg !158
  %".10" = load i64, i64* %"needed", !dbg !158
  %".11" = icmp sge i64 %".9", %".10" , !dbg !158
  br i1 %".11", label %"if.then", label %"if.end", !dbg !158
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !159
  ret i32 %".13", !dbg !159
if.end:
  %".15" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !160
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".15", i32 0, i32 2 , !dbg !160
  %".17" = load i64, i64* %".16", !dbg !160
  store i64 %".17", i64* %"new_cap.addr", !dbg !160
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !161, metadata !7), !dbg !162
  %".20" = load i64, i64* %"new_cap.addr", !dbg !163
  %".21" = icmp eq i64 %".20", 0 , !dbg !163
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !163
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !164
  br label %"if.end.1", !dbg !164
if.end.1:
  br label %"while.cond", !dbg !165
while.cond:
  %".26" = load i64, i64* %"new_cap.addr", !dbg !165
  %".27" = load i64, i64* %"needed", !dbg !165
  %".28" = icmp slt i64 %".26", %".27" , !dbg !165
  br i1 %".28", label %"while.body", label %"while.end", !dbg !165
while.body:
  %".30" = load i64, i64* %"new_cap.addr", !dbg !166
  %".31" = mul i64 %".30", 2, !dbg !166
  store i64 %".31", i64* %"new_cap.addr", !dbg !166
  br label %"while.cond", !dbg !166
while.end:
  %".34" = load i64, i64* %"new_cap.addr", !dbg !167
  %".35" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %".34"), !dbg !167
  ret i32 %".35", !dbg !167
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"new_cap.arg") !dbg !36
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !168, metadata !7), !dbg !169
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !170, metadata !7), !dbg !169
  %".7" = load i64, i64* %"new_cap", !dbg !171
  %".8" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !171
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".8", i32 0, i32 2 , !dbg !171
  %".10" = load i64, i64* %".9", !dbg !171
  %".11" = icmp sle i64 %".7", %".10" , !dbg !171
  br i1 %".11", label %"if.then", label %"if.end", !dbg !171
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !172
  ret i32 %".13", !dbg !172
if.end:
  %".15" = load i64, i64* %"new_cap", !dbg !173
  %".16" = mul i64 %".15", 1, !dbg !173
  %".17" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !174
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".17", i32 0, i32 0 , !dbg !174
  %".19" = load i8*, i8** %".18", !dbg !174
  %".20" = call i8* @"realloc"(i8* %".19", i64 %".16"), !dbg !174
  %".21" = icmp eq i8* %".20", null , !dbg !175
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !175
if.then.1:
  %".23" = sub i64 0, 1, !dbg !176
  %".24" = trunc i64 %".23" to i32 , !dbg !176
  ret i32 %".24", !dbg !176
if.end.1:
  %".26" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !177
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".26", i32 0, i32 0 , !dbg !177
  store i8* %".20", i8** %".27", !dbg !177
  %".29" = load i64, i64* %"new_cap", !dbg !178
  %".30" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !178
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".30", i32 0, i32 2 , !dbg !178
  store i64 %".29", i64* %".31", !dbg !178
  %".33" = trunc i64 0 to i32 , !dbg !179
  ret i32 %".33", !dbg !179
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %"new_cap.arg") !dbg !37
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !180, metadata !7), !dbg !181
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !182, metadata !7), !dbg !181
  %".7" = load i64, i64* %"new_cap", !dbg !183
  %".8" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !183
  %".9" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".8", i32 0, i32 2 , !dbg !183
  %".10" = load i64, i64* %".9", !dbg !183
  %".11" = icmp sle i64 %".7", %".10" , !dbg !183
  br i1 %".11", label %"if.then", label %"if.end", !dbg !183
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !184
  ret i32 %".13", !dbg !184
if.end:
  %".15" = load i64, i64* %"new_cap", !dbg !185
  %".16" = mul i64 %".15", 16, !dbg !185
  %".17" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !186
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".17", i32 0, i32 0 , !dbg !186
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !186
  %".20" = bitcast %"struct.ritz_module_1.LineBounds"* %".19" to i8* , !dbg !186
  %".21" = call i8* @"realloc"(i8* %".20", i64 %".16"), !dbg !186
  %".22" = icmp eq i8* %".21", null , !dbg !187
  br i1 %".22", label %"if.then.1", label %"if.end.1", !dbg !187
if.then.1:
  %".24" = sub i64 0, 1, !dbg !188
  %".25" = trunc i64 %".24" to i32 , !dbg !188
  ret i32 %".25", !dbg !188
if.end.1:
  %".27" = bitcast i8* %".21" to %"struct.ritz_module_1.LineBounds"* , !dbg !189
  %".28" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !189
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".28", i32 0, i32 0 , !dbg !189
  store %"struct.ritz_module_1.LineBounds"* %".27", %"struct.ritz_module_1.LineBounds"** %".29", !dbg !189
  %".31" = load i64, i64* %"new_cap", !dbg !190
  %".32" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !190
  %".33" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".32", i32 0, i32 2 , !dbg !190
  store i64 %".31", i64* %".33", !dbg !190
  %".35" = trunc i64 0 to i32 , !dbg !191
  ret i32 %".35", !dbg !191
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/spire/lib/repo", filename: "mod.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 44, name: "repo_error_message", scopeLine: 44, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 53, name: "repo_error_not_found", scopeLine: 53, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 56, name: "repo_error_duplicate", scopeLine: 56, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 59, name: "repo_error_query", scopeLine: 59, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 62, name: "repo_error_connection", scopeLine: 62, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 65, name: "repo_error_transaction", scopeLine: 65, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 68, name: "repo_error_validation", scopeLine: 68, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!38 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!39 = !DILocalVariable(file: !0, line: 44, name: "err", scope: !17, type: !38)
!40 = !DILocation(column: 1, line: 44, scope: !17)
!41 = !DILocation(column: 5, line: 45, scope: !17)
!42 = !DICompositeType(align: 64, file: !0, name: "StrView", size: 128, tag: DW_TAG_structure_type)
!43 = !DIDerivedType(baseType: !42, size: 64, tag: DW_TAG_pointer_type)
!44 = !DILocalVariable(file: !0, line: 53, name: "msg", scope: !18, type: !43)
!45 = !DILocation(column: 1, line: 53, scope: !18)
!46 = !DILocation(column: 5, line: 54, scope: !18)
!47 = !DILocalVariable(file: !0, line: 56, name: "msg", scope: !19, type: !43)
!48 = !DILocation(column: 1, line: 56, scope: !19)
!49 = !DILocation(column: 5, line: 57, scope: !19)
!50 = !DILocalVariable(file: !0, line: 59, name: "msg", scope: !20, type: !43)
!51 = !DILocation(column: 1, line: 59, scope: !20)
!52 = !DILocation(column: 5, line: 60, scope: !20)
!53 = !DILocalVariable(file: !0, line: 62, name: "msg", scope: !21, type: !43)
!54 = !DILocation(column: 1, line: 62, scope: !21)
!55 = !DILocation(column: 5, line: 63, scope: !21)
!56 = !DILocalVariable(file: !0, line: 65, name: "msg", scope: !22, type: !43)
!57 = !DILocation(column: 1, line: 65, scope: !22)
!58 = !DILocation(column: 5, line: 66, scope: !22)
!59 = !DILocalVariable(file: !0, line: 68, name: "msg", scope: !23, type: !43)
!60 = !DILocation(column: 1, line: 68, scope: !23)
!61 = !DILocation(column: 5, line: 69, scope: !23)
!62 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!63 = !DIDerivedType(baseType: !62, size: 64, tag: DW_TAG_reference_type)
!64 = !DIDerivedType(baseType: !63, size: 64, tag: DW_TAG_reference_type)
!65 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !24, type: !64)
!66 = !DILocation(column: 1, line: 288, scope: !24)
!67 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!68 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !24, type: !67)
!69 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !24, type: !11)
!70 = !DILocation(column: 5, line: 289, scope: !24)
!71 = !DILocation(column: 13, line: 291, scope: !24)
!72 = !DILocation(column: 5, line: 292, scope: !24)
!73 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !25, type: !64)
!74 = !DILocation(column: 1, line: 244, scope: !25)
!75 = !DILocation(column: 5, line: 245, scope: !25)
!76 = !DILocation(column: 5, line: 117, scope: !26)
!77 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !26, type: !62)
!78 = !DILocation(column: 1, line: 117, scope: !26)
!79 = !DILocation(column: 5, line: 118, scope: !26)
!80 = !DILocation(column: 5, line: 119, scope: !26)
!81 = !DILocation(column: 5, line: 120, scope: !26)
!82 = !DILocation(column: 5, line: 121, scope: !26)
!83 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !27, type: !64)
!84 = !DILocation(column: 1, line: 210, scope: !27)
!85 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !27, type: !12)
!86 = !DILocation(column: 5, line: 211, scope: !27)
!87 = !DILocation(column: 9, line: 212, scope: !27)
!88 = !DILocation(column: 5, line: 213, scope: !27)
!89 = !DILocation(column: 5, line: 214, scope: !27)
!90 = !DILocation(column: 5, line: 215, scope: !27)
!91 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !28, type: !64)
!92 = !DILocation(column: 1, line: 235, scope: !28)
!93 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !28, type: !11)
!94 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !28, type: !12)
!95 = !DILocation(column: 5, line: 236, scope: !28)
!96 = !DILocation(column: 5, line: 237, scope: !28)
!97 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !29, type: !63)
!98 = !DILocation(column: 1, line: 225, scope: !29)
!99 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !29, type: !11)
!100 = !DILocation(column: 5, line: 226, scope: !29)
!101 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !30, type: !11)
!102 = !DILocation(column: 1, line: 124, scope: !30)
!103 = !DILocation(column: 5, line: 125, scope: !30)
!104 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !30, type: !62)
!105 = !DILocation(column: 1, line: 125, scope: !30)
!106 = !DILocation(column: 5, line: 126, scope: !30)
!107 = !DILocation(column: 9, line: 127, scope: !30)
!108 = !DILocation(column: 9, line: 128, scope: !30)
!109 = !DILocation(column: 9, line: 129, scope: !30)
!110 = !DILocation(column: 9, line: 130, scope: !30)
!111 = !DILocation(column: 5, line: 132, scope: !30)
!112 = !DILocation(column: 5, line: 133, scope: !30)
!113 = !DILocation(column: 5, line: 134, scope: !30)
!114 = !DILocation(column: 9, line: 135, scope: !30)
!115 = !DILocation(column: 9, line: 136, scope: !30)
!116 = !DILocation(column: 9, line: 137, scope: !30)
!117 = !DILocation(column: 5, line: 139, scope: !30)
!118 = !DILocation(column: 5, line: 140, scope: !30)
!119 = !DILocation(column: 5, line: 141, scope: !30)
!120 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !31, type: !64)
!121 = !DILocation(column: 1, line: 193, scope: !31)
!122 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !31, type: !11)
!123 = !DILocation(column: 5, line: 194, scope: !31)
!124 = !DILocation(column: 9, line: 195, scope: !31)
!125 = !DILocation(column: 5, line: 197, scope: !31)
!126 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !31, type: !11)
!127 = !DILocation(column: 1, line: 197, scope: !31)
!128 = !DILocation(column: 5, line: 198, scope: !31)
!129 = !DILocation(column: 9, line: 199, scope: !31)
!130 = !DILocation(column: 5, line: 200, scope: !31)
!131 = !DILocation(column: 9, line: 201, scope: !31)
!132 = !DILocation(column: 5, line: 203, scope: !31)
!133 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!134 = !DIDerivedType(baseType: !133, size: 64, tag: DW_TAG_reference_type)
!135 = !DIDerivedType(baseType: !134, size: 64, tag: DW_TAG_reference_type)
!136 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !32, type: !135)
!137 = !DILocation(column: 1, line: 210, scope: !32)
!138 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!139 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !32, type: !138)
!140 = !DILocation(column: 5, line: 211, scope: !32)
!141 = !DILocation(column: 9, line: 212, scope: !32)
!142 = !DILocation(column: 5, line: 213, scope: !32)
!143 = !DILocation(column: 5, line: 214, scope: !32)
!144 = !DILocation(column: 5, line: 215, scope: !32)
!145 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !33, type: !64)
!146 = !DILocation(column: 1, line: 219, scope: !33)
!147 = !DILocation(column: 5, line: 220, scope: !33)
!148 = !DILocation(column: 5, line: 221, scope: !33)
!149 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !34, type: !64)
!150 = !DILocation(column: 1, line: 148, scope: !34)
!151 = !DILocation(column: 5, line: 149, scope: !34)
!152 = !DILocation(column: 5, line: 151, scope: !34)
!153 = !DILocation(column: 5, line: 152, scope: !34)
!154 = !DILocation(column: 5, line: 153, scope: !34)
!155 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !35, type: !135)
!156 = !DILocation(column: 1, line: 193, scope: !35)
!157 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !35, type: !11)
!158 = !DILocation(column: 5, line: 194, scope: !35)
!159 = !DILocation(column: 9, line: 195, scope: !35)
!160 = !DILocation(column: 5, line: 197, scope: !35)
!161 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !35, type: !11)
!162 = !DILocation(column: 1, line: 197, scope: !35)
!163 = !DILocation(column: 5, line: 198, scope: !35)
!164 = !DILocation(column: 9, line: 199, scope: !35)
!165 = !DILocation(column: 5, line: 200, scope: !35)
!166 = !DILocation(column: 9, line: 201, scope: !35)
!167 = !DILocation(column: 5, line: 203, scope: !35)
!168 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !36, type: !64)
!169 = !DILocation(column: 1, line: 179, scope: !36)
!170 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !36, type: !11)
!171 = !DILocation(column: 5, line: 180, scope: !36)
!172 = !DILocation(column: 9, line: 181, scope: !36)
!173 = !DILocation(column: 5, line: 183, scope: !36)
!174 = !DILocation(column: 5, line: 184, scope: !36)
!175 = !DILocation(column: 5, line: 185, scope: !36)
!176 = !DILocation(column: 9, line: 186, scope: !36)
!177 = !DILocation(column: 5, line: 188, scope: !36)
!178 = !DILocation(column: 5, line: 189, scope: !36)
!179 = !DILocation(column: 5, line: 190, scope: !36)
!180 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !37, type: !135)
!181 = !DILocation(column: 1, line: 179, scope: !37)
!182 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !37, type: !11)
!183 = !DILocation(column: 5, line: 180, scope: !37)
!184 = !DILocation(column: 9, line: 181, scope: !37)
!185 = !DILocation(column: 5, line: 183, scope: !37)
!186 = !DILocation(column: 5, line: 184, scope: !37)
!187 = !DILocation(column: 5, line: 185, scope: !37)
!188 = !DILocation(column: 9, line: 186, scope: !37)
!189 = !DILocation(column: 5, line: 188, scope: !37)
!190 = !DILocation(column: 5, line: 189, scope: !37)
!191 = !DILocation(column: 5, line: 190, scope: !37)