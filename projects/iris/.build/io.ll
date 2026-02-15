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

define i32 @"prints"(%"struct.ritz_module_1.StrView" %"s.arg") !dbg !17
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"
  store %"struct.ritz_module_1.StrView" %"s.arg", %"struct.ritz_module_1.StrView"* %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s", metadata !55, metadata !7), !dbg !56
  %".5" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s", i32 0, i32 0 , !dbg !57
  %".6" = load i8*, i8** %".5", !dbg !57
  %".7" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s", i32 0, i32 1 , !dbg !57
  %".8" = load i64, i64* %".7", !dbg !57
  %".9" = call i64 @"sys_write"(i32 1, i8* %".6", i64 %".8"), !dbg !57
  %".10" = trunc i64 %".9" to i32 , !dbg !57
  ret i32 %".10", !dbg !57
}

define i32 @"eprints"(%"struct.ritz_module_1.StrView" %"s.arg") !dbg !18
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"
  store %"struct.ritz_module_1.StrView" %"s.arg", %"struct.ritz_module_1.StrView"* %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s", metadata !58, metadata !7), !dbg !59
  %".5" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s", i32 0, i32 0 , !dbg !60
  %".6" = load i8*, i8** %".5", !dbg !60
  %".7" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s", i32 0, i32 1 , !dbg !60
  %".8" = load i64, i64* %".7", !dbg !60
  %".9" = call i64 @"sys_write"(i32 2, i8* %".6", i64 %".8"), !dbg !60
  %".10" = trunc i64 %".9" to i32 , !dbg !60
  ret i32 %".10", !dbg !60
}

define i32 @"prints_cstr"(i8* %"s.arg") !dbg !19
{
entry:
  %"s" = alloca i8*
  %"len.addr" = alloca i64, !dbg !64
  store i8* %"s.arg", i8** %"s"
  call void @"llvm.dbg.declare"(metadata i8** %"s", metadata !62, metadata !7), !dbg !63
  store i64 0, i64* %"len.addr", !dbg !64
  call void @"llvm.dbg.declare"(metadata i64* %"len.addr", metadata !65, metadata !7), !dbg !66
  br label %"while.cond", !dbg !67
while.cond:
  %".8" = load i8*, i8** %"s", !dbg !67
  %".9" = load i64, i64* %"len.addr", !dbg !67
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !67
  %".11" = load i8, i8* %".10", !dbg !67
  %".12" = zext i8 %".11" to i64 , !dbg !67
  %".13" = icmp ne i64 %".12", 0 , !dbg !67
  br i1 %".13", label %"while.body", label %"while.end", !dbg !67
while.body:
  %".15" = load i64, i64* %"len.addr", !dbg !68
  %".16" = add i64 %".15", 1, !dbg !68
  store i64 %".16", i64* %"len.addr", !dbg !68
  br label %"while.cond", !dbg !68
while.end:
  %".19" = load i8*, i8** %"s", !dbg !69
  %".20" = load i64, i64* %"len.addr", !dbg !69
  %".21" = call i64 @"sys_write"(i32 1, i8* %".19", i64 %".20"), !dbg !69
  %".22" = trunc i64 %".21" to i32 , !dbg !69
  ret i32 %".22", !dbg !69
}

define i32 @"eprints_cstr"(i8* %"s.arg") !dbg !20
{
entry:
  %"s" = alloca i8*
  %"len.addr" = alloca i64, !dbg !72
  store i8* %"s.arg", i8** %"s"
  call void @"llvm.dbg.declare"(metadata i8** %"s", metadata !70, metadata !7), !dbg !71
  store i64 0, i64* %"len.addr", !dbg !72
  call void @"llvm.dbg.declare"(metadata i64* %"len.addr", metadata !73, metadata !7), !dbg !74
  br label %"while.cond", !dbg !75
while.cond:
  %".8" = load i8*, i8** %"s", !dbg !75
  %".9" = load i64, i64* %"len.addr", !dbg !75
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !75
  %".11" = load i8, i8* %".10", !dbg !75
  %".12" = zext i8 %".11" to i64 , !dbg !75
  %".13" = icmp ne i64 %".12", 0 , !dbg !75
  br i1 %".13", label %"while.body", label %"while.end", !dbg !75
while.body:
  %".15" = load i64, i64* %"len.addr", !dbg !76
  %".16" = add i64 %".15", 1, !dbg !76
  store i64 %".16", i64* %"len.addr", !dbg !76
  br label %"while.cond", !dbg !76
while.end:
  %".19" = load i8*, i8** %"s", !dbg !77
  %".20" = load i64, i64* %"len.addr", !dbg !77
  %".21" = call i64 @"sys_write"(i32 2, i8* %".19", i64 %".20"), !dbg !77
  %".22" = trunc i64 %".21" to i32 , !dbg !77
  ret i32 %".22", !dbg !77
}

define i32 @"print_char"(i8 %"c.arg") !dbg !21
{
entry:
  %"c" = alloca i8
  %"buf.addr" = alloca [1 x i8], !dbg !80
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !78, metadata !7), !dbg !79
  call void @"llvm.dbg.declare"(metadata [1 x i8]* %"buf.addr", metadata !84, metadata !7), !dbg !85
  %".6" = load i8, i8* %"c", !dbg !86
  %".7" = getelementptr [1 x i8], [1 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !86
  store i8 %".6", i8* %".7", !dbg !86
  %".9" = getelementptr [1 x i8], [1 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !87
  %".10" = call i64 @"sys_write"(i32 1, i8* %".9", i64 1), !dbg !87
  %".11" = trunc i64 %".10" to i32 , !dbg !87
  ret i32 %".11", !dbg !87
}

define i32 @"eprint_char"(i8 %"c.arg") !dbg !22
{
entry:
  %"c" = alloca i8
  %"buf.addr" = alloca [1 x i8], !dbg !90
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !88, metadata !7), !dbg !89
  call void @"llvm.dbg.declare"(metadata [1 x i8]* %"buf.addr", metadata !91, metadata !7), !dbg !92
  %".6" = load i8, i8* %"c", !dbg !93
  %".7" = getelementptr [1 x i8], [1 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !93
  store i8 %".6", i8* %".7", !dbg !93
  %".9" = getelementptr [1 x i8], [1 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !94
  %".10" = call i64 @"sys_write"(i32 2, i8* %".9", i64 1), !dbg !94
  %".11" = trunc i64 %".10" to i32 , !dbg !94
  ret i32 %".11", !dbg !94
}

define i32 @"print_int"(i64 %"n.arg") !dbg !23
{
entry:
  %"n" = alloca i64
  %"buf.addr" = alloca [20 x i8], !dbg !103
  %"len.addr" = alloca i64, !dbg !109
  %"tmp.addr" = alloca i64, !dbg !112
  %"i.addr" = alloca i64, !dbg !118
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !95, metadata !7), !dbg !96
  %".5" = load i64, i64* %"n", !dbg !97
  %".6" = icmp slt i64 %".5", 0 , !dbg !97
  br i1 %".6", label %"if.then", label %"if.end", !dbg !97
if.then:
  %".8" = trunc i64 45 to i8 , !dbg !98
  %".9" = call i32 @"print_char"(i8 %".8"), !dbg !98
  %".10" = load i64, i64* %"n", !dbg !99
  %".11" = sub i64 0, %".10", !dbg !99
  store i64 %".11", i64* %"n", !dbg !99
  br label %"if.end", !dbg !99
if.end:
  %".14" = load i64, i64* %"n", !dbg !100
  %".15" = icmp eq i64 %".14", 0 , !dbg !100
  br i1 %".15", label %"if.then.1", label %"if.end.1", !dbg !100
if.then.1:
  %".17" = trunc i64 48 to i8 , !dbg !101
  %".18" = call i32 @"print_char"(i8 %".17"), !dbg !101
  ret i32 0, !dbg !102
if.end.1:
  call void @"llvm.dbg.declare"(metadata [20 x i8]* %"buf.addr", metadata !107, metadata !7), !dbg !108
  store i64 0, i64* %"len.addr", !dbg !109
  call void @"llvm.dbg.declare"(metadata i64* %"len.addr", metadata !110, metadata !7), !dbg !111
  %".23" = load i64, i64* %"n", !dbg !112
  store i64 %".23", i64* %"tmp.addr", !dbg !112
  call void @"llvm.dbg.declare"(metadata i64* %"tmp.addr", metadata !113, metadata !7), !dbg !114
  br label %"while.cond", !dbg !115
while.cond:
  %".27" = load i64, i64* %"tmp.addr", !dbg !115
  %".28" = icmp sgt i64 %".27", 0 , !dbg !115
  br i1 %".28", label %"while.body", label %"while.end", !dbg !115
while.body:
  %".30" = load i64, i64* %"len.addr", !dbg !116
  %".31" = add i64 %".30", 1, !dbg !116
  store i64 %".31", i64* %"len.addr", !dbg !116
  %".33" = load i64, i64* %"tmp.addr", !dbg !117
  %".34" = sdiv i64 %".33", 10, !dbg !117
  store i64 %".34", i64* %"tmp.addr", !dbg !117
  br label %"while.cond", !dbg !117
while.end:
  %".37" = load i64, i64* %"len.addr", !dbg !118
  %".38" = sub i64 %".37", 1, !dbg !118
  store i64 %".38", i64* %"i.addr", !dbg !118
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !119, metadata !7), !dbg !120
  br label %"while.cond.1", !dbg !121
while.cond.1:
  %".42" = load i64, i64* %"n", !dbg !121
  %".43" = icmp sgt i64 %".42", 0 , !dbg !121
  br i1 %".43", label %"while.body.1", label %"while.end.1", !dbg !121
while.body.1:
  %".45" = load i64, i64* %"n", !dbg !122
  %".46" = srem i64 %".45", 10, !dbg !122
  %".47" = zext i8 48 to i64 , !dbg !122
  %".48" = add i64 %".46", %".47", !dbg !122
  %".49" = trunc i64 %".48" to i8 , !dbg !122
  %".50" = load i64, i64* %"i.addr", !dbg !122
  %".51" = getelementptr [20 x i8], [20 x i8]* %"buf.addr", i32 0, i64 %".50" , !dbg !122
  store i8 %".49", i8* %".51", !dbg !122
  %".53" = load i64, i64* %"n", !dbg !123
  %".54" = sdiv i64 %".53", 10, !dbg !123
  store i64 %".54", i64* %"n", !dbg !123
  %".56" = load i64, i64* %"i.addr", !dbg !124
  %".57" = sub i64 %".56", 1, !dbg !124
  store i64 %".57", i64* %"i.addr", !dbg !124
  br label %"while.cond.1", !dbg !124
while.end.1:
  %".60" = getelementptr [20 x i8], [20 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !125
  %".61" = load i64, i64* %"len.addr", !dbg !125
  %".62" = call i64 @"sys_write"(i32 1, i8* %".60", i64 %".61"), !dbg !125
  %".63" = trunc i64 %".62" to i32 , !dbg !125
  ret i32 %".63", !dbg !125
}

define i32 @"eprint_int"(i64 %"n.arg") !dbg !24
{
entry:
  %"n" = alloca i64
  %"buf.addr" = alloca [20 x i8], !dbg !134
  %"len.addr" = alloca i64, !dbg !137
  %"tmp.addr" = alloca i64, !dbg !140
  %"i.addr" = alloca i64, !dbg !146
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !126, metadata !7), !dbg !127
  %".5" = load i64, i64* %"n", !dbg !128
  %".6" = icmp slt i64 %".5", 0 , !dbg !128
  br i1 %".6", label %"if.then", label %"if.end", !dbg !128
if.then:
  %".8" = trunc i64 45 to i8 , !dbg !129
  %".9" = call i32 @"eprint_char"(i8 %".8"), !dbg !129
  %".10" = load i64, i64* %"n", !dbg !130
  %".11" = sub i64 0, %".10", !dbg !130
  store i64 %".11", i64* %"n", !dbg !130
  br label %"if.end", !dbg !130
if.end:
  %".14" = load i64, i64* %"n", !dbg !131
  %".15" = icmp eq i64 %".14", 0 , !dbg !131
  br i1 %".15", label %"if.then.1", label %"if.end.1", !dbg !131
if.then.1:
  %".17" = trunc i64 48 to i8 , !dbg !132
  %".18" = call i32 @"eprint_char"(i8 %".17"), !dbg !132
  ret i32 0, !dbg !133
if.end.1:
  call void @"llvm.dbg.declare"(metadata [20 x i8]* %"buf.addr", metadata !135, metadata !7), !dbg !136
  store i64 0, i64* %"len.addr", !dbg !137
  call void @"llvm.dbg.declare"(metadata i64* %"len.addr", metadata !138, metadata !7), !dbg !139
  %".23" = load i64, i64* %"n", !dbg !140
  store i64 %".23", i64* %"tmp.addr", !dbg !140
  call void @"llvm.dbg.declare"(metadata i64* %"tmp.addr", metadata !141, metadata !7), !dbg !142
  br label %"while.cond", !dbg !143
while.cond:
  %".27" = load i64, i64* %"tmp.addr", !dbg !143
  %".28" = icmp sgt i64 %".27", 0 , !dbg !143
  br i1 %".28", label %"while.body", label %"while.end", !dbg !143
while.body:
  %".30" = load i64, i64* %"len.addr", !dbg !144
  %".31" = add i64 %".30", 1, !dbg !144
  store i64 %".31", i64* %"len.addr", !dbg !144
  %".33" = load i64, i64* %"tmp.addr", !dbg !145
  %".34" = sdiv i64 %".33", 10, !dbg !145
  store i64 %".34", i64* %"tmp.addr", !dbg !145
  br label %"while.cond", !dbg !145
while.end:
  %".37" = load i64, i64* %"len.addr", !dbg !146
  %".38" = sub i64 %".37", 1, !dbg !146
  store i64 %".38", i64* %"i.addr", !dbg !146
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !147, metadata !7), !dbg !148
  br label %"while.cond.1", !dbg !149
while.cond.1:
  %".42" = load i64, i64* %"n", !dbg !149
  %".43" = icmp sgt i64 %".42", 0 , !dbg !149
  br i1 %".43", label %"while.body.1", label %"while.end.1", !dbg !149
while.body.1:
  %".45" = load i64, i64* %"n", !dbg !150
  %".46" = srem i64 %".45", 10, !dbg !150
  %".47" = zext i8 48 to i64 , !dbg !150
  %".48" = add i64 %".46", %".47", !dbg !150
  %".49" = trunc i64 %".48" to i8 , !dbg !150
  %".50" = load i64, i64* %"i.addr", !dbg !150
  %".51" = getelementptr [20 x i8], [20 x i8]* %"buf.addr", i32 0, i64 %".50" , !dbg !150
  store i8 %".49", i8* %".51", !dbg !150
  %".53" = load i64, i64* %"n", !dbg !151
  %".54" = sdiv i64 %".53", 10, !dbg !151
  store i64 %".54", i64* %"n", !dbg !151
  %".56" = load i64, i64* %"i.addr", !dbg !152
  %".57" = sub i64 %".56", 1, !dbg !152
  store i64 %".57", i64* %"i.addr", !dbg !152
  br label %"while.cond.1", !dbg !152
while.end.1:
  %".60" = getelementptr [20 x i8], [20 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !153
  %".61" = load i64, i64* %"len.addr", !dbg !153
  %".62" = call i64 @"sys_write"(i32 2, i8* %".60", i64 %".61"), !dbg !153
  %".63" = trunc i64 %".62" to i32 , !dbg !153
  ret i32 %".63", !dbg !153
}

define i32 @"print_hex"(i64 %"n.arg") !dbg !25
{
entry:
  %"n" = alloca i64
  %"buf.addr" = alloca [16 x i8], !dbg !160
  %"len.addr" = alloca i64, !dbg !166
  %"tmp.addr" = alloca i64, !dbg !169
  %"i.addr" = alloca i64, !dbg !175
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !154, metadata !7), !dbg !155
  %".5" = load i64, i64* %"n", !dbg !156
  %".6" = icmp eq i64 %".5", 0 , !dbg !156
  br i1 %".6", label %"if.then", label %"if.end", !dbg !156
if.then:
  %".8" = getelementptr [4 x i8], [4 x i8]* @".str.0", i64 0, i64 0 , !dbg !157
  %".9" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".8", 0 , !dbg !157
  %".10" = insertvalue %"struct.ritz_module_1.StrView" %".9", i64 3, 1 , !dbg !157
  %".11" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".10"), !dbg !157
  ret i32 0, !dbg !158
if.end:
  %".13" = getelementptr [3 x i8], [3 x i8]* @".str.1", i64 0, i64 0 , !dbg !159
  %".14" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".13", 0 , !dbg !159
  %".15" = insertvalue %"struct.ritz_module_1.StrView" %".14", i64 2, 1 , !dbg !159
  %".16" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".15"), !dbg !159
  call void @"llvm.dbg.declare"(metadata [16 x i8]* %"buf.addr", metadata !164, metadata !7), !dbg !165
  store i64 0, i64* %"len.addr", !dbg !166
  call void @"llvm.dbg.declare"(metadata i64* %"len.addr", metadata !167, metadata !7), !dbg !168
  %".20" = load i64, i64* %"n", !dbg !169
  store i64 %".20", i64* %"tmp.addr", !dbg !169
  call void @"llvm.dbg.declare"(metadata i64* %"tmp.addr", metadata !170, metadata !7), !dbg !171
  br label %"while.cond", !dbg !172
while.cond:
  %".24" = load i64, i64* %"tmp.addr", !dbg !172
  %".25" = icmp sgt i64 %".24", 0 , !dbg !172
  br i1 %".25", label %"while.body", label %"while.end", !dbg !172
while.body:
  %".27" = load i64, i64* %"len.addr", !dbg !173
  %".28" = add i64 %".27", 1, !dbg !173
  store i64 %".28", i64* %"len.addr", !dbg !173
  %".30" = load i64, i64* %"tmp.addr", !dbg !174
  %".31" = sdiv i64 %".30", 16, !dbg !174
  store i64 %".31", i64* %"tmp.addr", !dbg !174
  br label %"while.cond", !dbg !174
while.end:
  %".34" = load i64, i64* %"len.addr", !dbg !175
  %".35" = sub i64 %".34", 1, !dbg !175
  store i64 %".35", i64* %"i.addr", !dbg !175
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !176, metadata !7), !dbg !177
  br label %"while.cond.1", !dbg !178
while.cond.1:
  %".39" = load i64, i64* %"n", !dbg !178
  %".40" = icmp sgt i64 %".39", 0 , !dbg !178
  br i1 %".40", label %"while.body.1", label %"while.end.1", !dbg !178
while.body.1:
  %".42" = load i64, i64* %"n", !dbg !179
  %".43" = srem i64 %".42", 16, !dbg !179
  %".44" = icmp slt i64 %".43", 10 , !dbg !180
  br i1 %".44", label %"if.then.1", label %"if.else", !dbg !180
while.end.1:
  %".67" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !185
  %".68" = load i64, i64* %"len.addr", !dbg !185
  %".69" = call i64 @"sys_write"(i32 1, i8* %".67", i64 %".68"), !dbg !185
  %".70" = trunc i64 %".69" to i32 , !dbg !185
  ret i32 %".70", !dbg !185
if.then.1:
  %".46" = zext i8 48 to i64 , !dbg !181
  %".47" = add i64 %".43", %".46", !dbg !181
  %".48" = trunc i64 %".47" to i8 , !dbg !181
  %".49" = load i64, i64* %"i.addr", !dbg !181
  %".50" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 %".49" , !dbg !181
  store i8 %".48", i8* %".50", !dbg !181
  br label %"if.end.1", !dbg !182
if.else:
  %".52" = sub i64 %".43", 10, !dbg !182
  %".53" = add i64 %".52", 97, !dbg !182
  %".54" = trunc i64 %".53" to i8 , !dbg !182
  %".55" = load i64, i64* %"i.addr", !dbg !182
  %".56" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 %".55" , !dbg !182
  store i8 %".54", i8* %".56", !dbg !182
  br label %"if.end.1", !dbg !182
if.end.1:
  %".60" = load i64, i64* %"n", !dbg !183
  %".61" = sdiv i64 %".60", 16, !dbg !183
  store i64 %".61", i64* %"n", !dbg !183
  %".63" = load i64, i64* %"i.addr", !dbg !184
  %".64" = sub i64 %".63", 1, !dbg !184
  store i64 %".64", i64* %"i.addr", !dbg !184
  br label %"while.cond.1", !dbg !184
}

define i32 @"print_size_human"(i64 %"size.arg") !dbg !26
{
entry:
  %"size" = alloca i64
  %"units.addr" = alloca [4 x i8], !dbg !191
  %"s.addr" = alloca i64, !dbg !201
  %"unit.addr" = alloca i32, !dbg !204
  store i64 %"size.arg", i64* %"size"
  call void @"llvm.dbg.declare"(metadata i64* %"size", metadata !186, metadata !7), !dbg !187
  %".5" = load i64, i64* %"size", !dbg !188
  %".6" = icmp slt i64 %".5", 1024 , !dbg !188
  br i1 %".6", label %"if.then", label %"if.end", !dbg !188
if.then:
  %".8" = load i64, i64* %"size", !dbg !189
  %".9" = call i32 @"print_int"(i64 %".8"), !dbg !189
  ret i32 0, !dbg !190
if.end:
  call void @"llvm.dbg.declare"(metadata [4 x i8]* %"units.addr", metadata !195, metadata !7), !dbg !196
  %".12" = getelementptr [4 x i8], [4 x i8]* %"units.addr", i32 0, i64 0 , !dbg !197
  %".13" = trunc i64 75 to i8 , !dbg !197
  store i8 %".13", i8* %".12", !dbg !197
  %".15" = getelementptr [4 x i8], [4 x i8]* %"units.addr", i32 0, i64 1 , !dbg !198
  %".16" = trunc i64 77 to i8 , !dbg !198
  store i8 %".16", i8* %".15", !dbg !198
  %".18" = getelementptr [4 x i8], [4 x i8]* %"units.addr", i32 0, i64 2 , !dbg !199
  %".19" = trunc i64 71 to i8 , !dbg !199
  store i8 %".19", i8* %".18", !dbg !199
  %".21" = getelementptr [4 x i8], [4 x i8]* %"units.addr", i32 0, i64 3 , !dbg !200
  %".22" = trunc i64 84 to i8 , !dbg !200
  store i8 %".22", i8* %".21", !dbg !200
  %".24" = load i64, i64* %"size", !dbg !201
  store i64 %".24", i64* %"s.addr", !dbg !201
  call void @"llvm.dbg.declare"(metadata i64* %"s.addr", metadata !202, metadata !7), !dbg !203
  %".27" = trunc i64 0 to i32 , !dbg !204
  store i32 %".27", i32* %"unit.addr", !dbg !204
  call void @"llvm.dbg.declare"(metadata i32* %"unit.addr", metadata !205, metadata !7), !dbg !206
  %".30" = load i64, i64* %"s.addr", !dbg !207
  %".31" = sdiv i64 %".30", 1024, !dbg !207
  store i64 %".31", i64* %"s.addr", !dbg !207
  br label %"while.cond", !dbg !208
while.cond:
  %".34" = load i64, i64* %"s.addr", !dbg !208
  %".35" = icmp sge i64 %".34", 1024 , !dbg !208
  br i1 %".35", label %"and.right", label %"and.merge", !dbg !208
while.body:
  %".43" = load i64, i64* %"s.addr", !dbg !209
  %".44" = sdiv i64 %".43", 1024, !dbg !209
  store i64 %".44", i64* %"s.addr", !dbg !209
  %".46" = load i32, i32* %"unit.addr", !dbg !210
  %".47" = sext i32 %".46" to i64 , !dbg !210
  %".48" = add i64 %".47", 1, !dbg !210
  %".49" = trunc i64 %".48" to i32 , !dbg !210
  store i32 %".49", i32* %"unit.addr", !dbg !210
  br label %"while.cond", !dbg !210
while.end:
  %".52" = load i64, i64* %"s.addr", !dbg !211
  %".53" = call i32 @"print_int"(i64 %".52"), !dbg !211
  %".54" = load i32, i32* %"unit.addr", !dbg !212
  %".55" = getelementptr [4 x i8], [4 x i8]* %"units.addr", i32 0, i32 %".54" , !dbg !212
  %".56" = load i8, i8* %".55", !dbg !212
  %".57" = call i32 @"print_char"(i8 %".56"), !dbg !212
  ret i32 %".57", !dbg !212
and.right:
  %".37" = load i32, i32* %"unit.addr", !dbg !208
  %".38" = sext i32 %".37" to i64 , !dbg !208
  %".39" = icmp slt i64 %".38", 3 , !dbg !208
  br label %"and.merge", !dbg !208
and.merge:
  %".41" = phi  i1 [0, %"while.cond"], [%".39", %"and.right"] , !dbg !208
  br i1 %".41", label %"while.body", label %"while.end", !dbg !208
}

define i32 @"println"(%"struct.ritz_module_1.StrView" %"s.arg") !dbg !27
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"
  store %"struct.ritz_module_1.StrView" %"s.arg", %"struct.ritz_module_1.StrView"* %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s", metadata !213, metadata !7), !dbg !214
  %".5" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s", !dbg !215
  %".6" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".5"), !dbg !215
  %".7" = trunc i64 10 to i8 , !dbg !216
  %".8" = call i32 @"print_char"(i8 %".7"), !dbg !216
  ret i32 %".8", !dbg !216
}

define i32 @"eprintln"(%"struct.ritz_module_1.StrView" %"s.arg") !dbg !28
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"
  store %"struct.ritz_module_1.StrView" %"s.arg", %"struct.ritz_module_1.StrView"* %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s", metadata !217, metadata !7), !dbg !218
  %".5" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s", !dbg !219
  %".6" = call i32 @"eprints"(%"struct.ritz_module_1.StrView" %".5"), !dbg !219
  %".7" = trunc i64 10 to i8 , !dbg !220
  %".8" = call i32 @"eprint_char"(i8 %".7"), !dbg !220
  ret i32 %".8", !dbg !220
}

define i32 @"newline"() !dbg !29
{
entry:
  %".2" = trunc i64 10 to i8 , !dbg !221
  %".3" = call i32 @"print_char"(i8 %".2"), !dbg !221
  ret i32 %".3", !dbg !221
}

define i32 @"print_string"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !30
{
entry:
  %"s" = alloca %"struct.ritz_module_1.String"*
  store %"struct.ritz_module_1.String"* %"s.arg", %"struct.ritz_module_1.String"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"** %"s", metadata !224, metadata !7), !dbg !225
  %".5" = load %"struct.ritz_module_1.String"*, %"struct.ritz_module_1.String"** %"s", !dbg !226
  %".6" = call i8* @"string_as_ptr"(%"struct.ritz_module_1.String"* %".5"), !dbg !226
  %".7" = load %"struct.ritz_module_1.String"*, %"struct.ritz_module_1.String"** %"s", !dbg !226
  %".8" = call i64 @"string_len"(%"struct.ritz_module_1.String"* %".7"), !dbg !226
  %".9" = call i64 @"sys_write"(i32 1, i8* %".6", i64 %".8"), !dbg !226
  %".10" = trunc i64 %".9" to i32 , !dbg !226
  ret i32 %".10", !dbg !226
}

define i32 @"eprint_string"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !31
{
entry:
  %"s" = alloca %"struct.ritz_module_1.String"*
  store %"struct.ritz_module_1.String"* %"s.arg", %"struct.ritz_module_1.String"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"** %"s", metadata !227, metadata !7), !dbg !228
  %".5" = load %"struct.ritz_module_1.String"*, %"struct.ritz_module_1.String"** %"s", !dbg !229
  %".6" = call i8* @"string_as_ptr"(%"struct.ritz_module_1.String"* %".5"), !dbg !229
  %".7" = load %"struct.ritz_module_1.String"*, %"struct.ritz_module_1.String"** %"s", !dbg !229
  %".8" = call i64 @"string_len"(%"struct.ritz_module_1.String"* %".7"), !dbg !229
  %".9" = call i64 @"sys_write"(i32 2, i8* %".6", i64 %".8"), !dbg !229
  %".10" = trunc i64 %".9" to i32 , !dbg !229
  ret i32 %".10", !dbg !229
}

define i32 @"println_string"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !32
{
entry:
  %"s" = alloca %"struct.ritz_module_1.String"*
  store %"struct.ritz_module_1.String"* %"s.arg", %"struct.ritz_module_1.String"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"** %"s", metadata !230, metadata !7), !dbg !231
  %".5" = load %"struct.ritz_module_1.String"*, %"struct.ritz_module_1.String"** %"s", !dbg !232
  %".6" = call i32 @"print_string"(%"struct.ritz_module_1.String"* %".5"), !dbg !232
  %".7" = trunc i64 10 to i8 , !dbg !233
  %".8" = call i32 @"print_char"(i8 %".7"), !dbg !233
  ret i32 %".8", !dbg !233
}

define i32 @"eprintln_string"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !33
{
entry:
  %"s" = alloca %"struct.ritz_module_1.String"*
  store %"struct.ritz_module_1.String"* %"s.arg", %"struct.ritz_module_1.String"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"** %"s", metadata !234, metadata !7), !dbg !235
  %".5" = load %"struct.ritz_module_1.String"*, %"struct.ritz_module_1.String"** %"s", !dbg !236
  %".6" = call i32 @"eprint_string"(%"struct.ritz_module_1.String"* %".5"), !dbg !236
  %".7" = trunc i64 10 to i8 , !dbg !237
  %".8" = call i32 @"eprint_char"(i8 %".7"), !dbg !237
  ret i32 %".8", !dbg !237
}

define i32 @"print_i64"(i64 %"n.arg") !dbg !34
{
entry:
  %"n" = alloca i64
  %"s.addr" = alloca %"struct.ritz_module_1.String", !dbg !240
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !238, metadata !7), !dbg !239
  %".5" = load i64, i64* %"n", !dbg !240
  %".6" = call %"struct.ritz_module_1.String" @"string_from_i64"(i64 %".5"), !dbg !240
  store %"struct.ritz_module_1.String" %".6", %"struct.ritz_module_1.String"* %"s.addr", !dbg !240
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.addr", metadata !241, metadata !7), !dbg !242
  %".9" = call i32 @"print_string"(%"struct.ritz_module_1.String"* %"s.addr"), !dbg !243
  ret i32 %".9", !dbg !243
}

define i32 @"println_i64"(i64 %"n.arg") !dbg !35
{
entry:
  %"n" = alloca i64
  %"s.addr" = alloca %"struct.ritz_module_1.String", !dbg !246
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !244, metadata !7), !dbg !245
  %".5" = load i64, i64* %"n", !dbg !246
  %".6" = call %"struct.ritz_module_1.String" @"string_from_i64"(i64 %".5"), !dbg !246
  store %"struct.ritz_module_1.String" %".6", %"struct.ritz_module_1.String"* %"s.addr", !dbg !246
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.addr", metadata !247, metadata !7), !dbg !248
  %".9" = call i32 @"println_string"(%"struct.ritz_module_1.String"* %"s.addr"), !dbg !249
  ret i32 %".9", !dbg !249
}

define i32 @"eprint_i64"(i64 %"n.arg") !dbg !36
{
entry:
  %"n" = alloca i64
  %"s.addr" = alloca %"struct.ritz_module_1.String", !dbg !252
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !250, metadata !7), !dbg !251
  %".5" = load i64, i64* %"n", !dbg !252
  %".6" = call %"struct.ritz_module_1.String" @"string_from_i64"(i64 %".5"), !dbg !252
  store %"struct.ritz_module_1.String" %".6", %"struct.ritz_module_1.String"* %"s.addr", !dbg !252
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.addr", metadata !253, metadata !7), !dbg !254
  %".9" = call i32 @"eprint_string"(%"struct.ritz_module_1.String"* %"s.addr"), !dbg !255
  ret i32 %".9", !dbg !255
}

define i32 @"eprintln_i64"(i64 %"n.arg") !dbg !37
{
entry:
  %"n" = alloca i64
  %"s.addr" = alloca %"struct.ritz_module_1.String", !dbg !258
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !256, metadata !7), !dbg !257
  %".5" = load i64, i64* %"n", !dbg !258
  %".6" = call %"struct.ritz_module_1.String" @"string_from_i64"(i64 %".5"), !dbg !258
  store %"struct.ritz_module_1.String" %".6", %"struct.ritz_module_1.String"* %"s.addr", !dbg !258
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.addr", metadata !259, metadata !7), !dbg !260
  %".9" = call i32 @"eprintln_string"(%"struct.ritz_module_1.String"* %"s.addr"), !dbg !261
  ret i32 %".9", !dbg !261
}

define i32 @"print_hex64"(i64 %"n.arg") !dbg !38
{
entry:
  %"n" = alloca i64
  %"s.addr" = alloca %"struct.ritz_module_1.String", !dbg !264
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !262, metadata !7), !dbg !263
  %".5" = load i64, i64* %"n", !dbg !264
  %".6" = call %"struct.ritz_module_1.String" @"string_from_hex"(i64 %".5"), !dbg !264
  store %"struct.ritz_module_1.String" %".6", %"struct.ritz_module_1.String"* %"s.addr", !dbg !264
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.addr", metadata !265, metadata !7), !dbg !266
  %".9" = call i32 @"print_string"(%"struct.ritz_module_1.String"* %"s.addr"), !dbg !267
  ret i32 %".9", !dbg !267
}

define i32 @"println_hex64"(i64 %"n.arg") !dbg !39
{
entry:
  %"n" = alloca i64
  %"s.addr" = alloca %"struct.ritz_module_1.String", !dbg !270
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !268, metadata !7), !dbg !269
  %".5" = load i64, i64* %"n", !dbg !270
  %".6" = call %"struct.ritz_module_1.String" @"string_from_hex"(i64 %".5"), !dbg !270
  store %"struct.ritz_module_1.String" %".6", %"struct.ritz_module_1.String"* %"s.addr", !dbg !270
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.addr", metadata !271, metadata !7), !dbg !272
  %".9" = call i32 @"println_string"(%"struct.ritz_module_1.String"* %"s.addr"), !dbg !273
  ret i32 %".9", !dbg !273
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !40
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !276, metadata !7), !dbg !277
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !278
  %".5" = load i8*, i8** %".4", !dbg !278
  %".6" = icmp ne i8* %".5", null , !dbg !278
  br i1 %".6", label %"if.then", label %"if.end", !dbg !278
if.then:
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !278
  %".9" = load i8*, i8** %".8", !dbg !278
  %".10" = call i32 @"free"(i8* %".9"), !dbg !278
  br label %"if.end", !dbg !278
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !279
  store i8* null, i8** %".12", !dbg !279
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !280
  store i64 0, i64* %".14", !dbg !280
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !281
  store i64 0, i64* %".16", !dbg !281
  ret i32 0, !dbg !281
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !41
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !284, metadata !7), !dbg !285
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !287, metadata !7), !dbg !285
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !288
  %".8" = load i64, i64* %".7", !dbg !288
  %".9" = add i64 %".8", 1, !dbg !288
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !288
  %".11" = sext i32 %".10" to i64 , !dbg !288
  %".12" = icmp ne i64 %".11", 0 , !dbg !288
  br i1 %".12", label %"if.then", label %"if.end", !dbg !288
if.then:
  %".14" = sub i64 0, 1, !dbg !289
  %".15" = trunc i64 %".14" to i32 , !dbg !289
  ret i32 %".15", !dbg !289
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !290
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !290
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !290
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !290
  %".21" = load i64, i64* %".20", !dbg !290
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !290
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !290
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !291
  %".25" = load i64, i64* %".24", !dbg !291
  %".26" = add i64 %".25", 1, !dbg !291
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !291
  store i64 %".26", i64* %".27", !dbg !291
  %".29" = trunc i64 0 to i32 , !dbg !292
  ret i32 %".29", !dbg !292
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !42
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !293, metadata !7), !dbg !294
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !295
  store i64 0, i64* %".4", !dbg !295
  ret i32 0, !dbg !295
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !43
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !296, metadata !7), !dbg !297
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !298, metadata !7), !dbg !297
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !299
  %".8" = load i64, i64* %".7", !dbg !299
  %".9" = add i64 %".8", 1, !dbg !299
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !299
  %".11" = sext i32 %".10" to i64 , !dbg !299
  %".12" = icmp ne i64 %".11", 0 , !dbg !299
  br i1 %".12", label %"if.then", label %"if.end", !dbg !299
if.then:
  %".14" = sub i64 0, 1, !dbg !300
  %".15" = trunc i64 %".14" to i32 , !dbg !300
  ret i32 %".15", !dbg !300
if.end:
  %".17" = load i8, i8* %"item", !dbg !301
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !301
  %".19" = load i8*, i8** %".18", !dbg !301
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !301
  %".21" = load i64, i64* %".20", !dbg !301
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !301
  store i8 %".17", i8* %".22", !dbg !301
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !302
  %".25" = load i64, i64* %".24", !dbg !302
  %".26" = add i64 %".25", 1, !dbg !302
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !302
  store i64 %".26", i64* %".27", !dbg !302
  %".29" = trunc i64 0 to i32 , !dbg !303
  ret i32 %".29", !dbg !303
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !44
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !304
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !305, metadata !7), !dbg !306
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !307
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !307
  store i8* null, i8** %".4", !dbg !307
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !308
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !308
  store i64 0, i64* %".7", !dbg !308
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !309
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !309
  store i64 0, i64* %".10", !dbg !309
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !310
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !310
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !45
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !311, metadata !7), !dbg !312
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !313, metadata !7), !dbg !312
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !314
  %".8" = load i8*, i8** %".7", !dbg !314
  %".9" = load i64, i64* %"idx", !dbg !314
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !314
  %".11" = load i8, i8* %".10", !dbg !314
  ret i8 %".11", !dbg !314
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !46
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !315, metadata !7), !dbg !316
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !317, metadata !7), !dbg !316
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !318, metadata !7), !dbg !316
  %".10" = load i8, i8* %"item", !dbg !319
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !319
  %".12" = load i8*, i8** %".11", !dbg !319
  %".13" = load i64, i64* %"idx", !dbg !319
  %".14" = getelementptr i8, i8* %".12", i64 %".13" , !dbg !319
  store i8 %".10", i8* %".14", !dbg !319
  %".16" = trunc i64 0 to i32 , !dbg !320
  ret i32 %".16", !dbg !320
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !47
{
entry:
  %"i" = alloca i64, !dbg !325
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !321, metadata !7), !dbg !322
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !323, metadata !7), !dbg !322
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !324, metadata !7), !dbg !322
  %".10" = load i64, i64* %"len", !dbg !325
  store i64 0, i64* %"i", !dbg !325
  br label %"for.cond", !dbg !325
for.cond:
  %".13" = load i64, i64* %"i", !dbg !325
  %".14" = icmp slt i64 %".13", %".10" , !dbg !325
  br i1 %".14", label %"for.body", label %"for.end", !dbg !325
for.body:
  %".16" = load i8*, i8** %"data", !dbg !325
  %".17" = load i64, i64* %"i", !dbg !325
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !325
  %".19" = load i8, i8* %".18", !dbg !325
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !325
  %".21" = sext i32 %".20" to i64 , !dbg !325
  %".22" = icmp ne i64 %".21", 0 , !dbg !325
  br i1 %".22", label %"if.then", label %"if.end", !dbg !325
for.incr:
  %".28" = load i64, i64* %"i", !dbg !326
  %".29" = add i64 %".28", 1, !dbg !326
  store i64 %".29", i64* %"i", !dbg !326
  br label %"for.cond", !dbg !326
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !327
  ret i32 %".32", !dbg !327
if.then:
  %".24" = sub i64 0, 1, !dbg !326
  %".25" = trunc i64 %".24" to i32 , !dbg !326
  ret i32 %".25", !dbg !326
if.end:
  br label %"for.incr", !dbg !326
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !48
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !330
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !328, metadata !7), !dbg !329
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !331, metadata !7), !dbg !332
  %".6" = load i64, i64* %"cap", !dbg !333
  %".7" = icmp sle i64 %".6", 0 , !dbg !333
  br i1 %".7", label %"if.then", label %"if.end", !dbg !333
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !334
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !334
  store i8* null, i8** %".10", !dbg !334
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !335
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !335
  store i64 0, i64* %".13", !dbg !335
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !336
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !336
  store i64 0, i64* %".16", !dbg !336
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !337
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !337
if.end:
  %".20" = load i64, i64* %"cap", !dbg !338
  %".21" = mul i64 %".20", 1, !dbg !338
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !339
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !339
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !339
  store i8* %".22", i8** %".24", !dbg !339
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !340
  %".27" = load i8*, i8** %".26", !dbg !340
  %".28" = icmp eq i8* %".27", null , !dbg !340
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !340
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !341
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !341
  store i64 0, i64* %".31", !dbg !341
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !342
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !342
  store i64 0, i64* %".34", !dbg !342
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !343
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !343
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !344
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !344
  store i64 0, i64* %".39", !dbg !344
  %".41" = load i64, i64* %"cap", !dbg !345
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !345
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !345
  store i64 %".41", i64* %".43", !dbg !345
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !346
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !346
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !49
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !352
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !347, metadata !7), !dbg !348
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !349, metadata !7), !dbg !348
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !350
  %".8" = load i64, i64* %".7", !dbg !350
  %".9" = load i64, i64* %"needed", !dbg !350
  %".10" = icmp sge i64 %".8", %".9" , !dbg !350
  br i1 %".10", label %"if.then", label %"if.end", !dbg !350
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !351
  ret i32 %".12", !dbg !351
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !352
  %".15" = load i64, i64* %".14", !dbg !352
  store i64 %".15", i64* %"new_cap.addr", !dbg !352
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !353, metadata !7), !dbg !354
  %".18" = load i64, i64* %"new_cap.addr", !dbg !355
  %".19" = icmp eq i64 %".18", 0 , !dbg !355
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !355
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !356
  br label %"if.end.1", !dbg !356
if.end.1:
  br label %"while.cond", !dbg !357
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !357
  %".25" = load i64, i64* %"needed", !dbg !357
  %".26" = icmp slt i64 %".24", %".25" , !dbg !357
  br i1 %".26", label %"while.body", label %"while.end", !dbg !357
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !358
  %".29" = mul i64 %".28", 2, !dbg !358
  store i64 %".29", i64* %"new_cap.addr", !dbg !358
  br label %"while.cond", !dbg !358
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !359
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !359
  ret i32 %".33", !dbg !359
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !50
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !360, metadata !7), !dbg !361
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !362
  %".5" = load i64, i64* %".4", !dbg !362
  %".6" = sub i64 %".5", 1, !dbg !362
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !362
  store i64 %".6", i64* %".7", !dbg !362
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !363
  %".10" = load i8*, i8** %".9", !dbg !363
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !363
  %".12" = load i64, i64* %".11", !dbg !363
  %".13" = getelementptr i8, i8* %".10", i64 %".12" , !dbg !363
  %".14" = load i8, i8* %".13", !dbg !363
  ret i8 %".14", !dbg !363
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !51
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !369
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !364, metadata !7), !dbg !365
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !366, metadata !7), !dbg !365
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !367
  %".8" = load i64, i64* %".7", !dbg !367
  %".9" = load i64, i64* %"needed", !dbg !367
  %".10" = icmp sge i64 %".8", %".9" , !dbg !367
  br i1 %".10", label %"if.then", label %"if.end", !dbg !367
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !368
  ret i32 %".12", !dbg !368
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !369
  %".15" = load i64, i64* %".14", !dbg !369
  store i64 %".15", i64* %"new_cap.addr", !dbg !369
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !370, metadata !7), !dbg !371
  %".18" = load i64, i64* %"new_cap.addr", !dbg !372
  %".19" = icmp eq i64 %".18", 0 , !dbg !372
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !372
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !373
  br label %"if.end.1", !dbg !373
if.end.1:
  br label %"while.cond", !dbg !374
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !374
  %".25" = load i64, i64* %"needed", !dbg !374
  %".26" = icmp slt i64 %".24", %".25" , !dbg !374
  br i1 %".26", label %"while.body", label %"while.end", !dbg !374
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !375
  %".29" = mul i64 %".28", 2, !dbg !375
  store i64 %".29", i64* %"new_cap.addr", !dbg !375
  br label %"while.cond", !dbg !375
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !376
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !376
  ret i32 %".33", !dbg !376
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !52
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !377, metadata !7), !dbg !378
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !379, metadata !7), !dbg !378
  %".7" = load i64, i64* %"new_cap", !dbg !380
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !380
  %".9" = load i64, i64* %".8", !dbg !380
  %".10" = icmp sle i64 %".7", %".9" , !dbg !380
  br i1 %".10", label %"if.then", label %"if.end", !dbg !380
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !381
  ret i32 %".12", !dbg !381
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !382
  %".15" = mul i64 %".14", 1, !dbg !382
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !383
  %".17" = load i8*, i8** %".16", !dbg !383
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !383
  %".19" = icmp eq i8* %".18", null , !dbg !384
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !384
if.then.1:
  %".21" = sub i64 0, 1, !dbg !385
  %".22" = trunc i64 %".21" to i32 , !dbg !385
  ret i32 %".22", !dbg !385
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !386
  store i8* %".18", i8** %".24", !dbg !386
  %".26" = load i64, i64* %"new_cap", !dbg !387
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !387
  store i64 %".26", i64* %".27", !dbg !387
  %".29" = trunc i64 0 to i32 , !dbg !388
  ret i32 %".29", !dbg !388
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !53
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !389, metadata !7), !dbg !390
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !391, metadata !7), !dbg !390
  %".7" = load i64, i64* %"new_cap", !dbg !392
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !392
  %".9" = load i64, i64* %".8", !dbg !392
  %".10" = icmp sle i64 %".7", %".9" , !dbg !392
  br i1 %".10", label %"if.then", label %"if.end", !dbg !392
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !393
  ret i32 %".12", !dbg !393
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !394
  %".15" = mul i64 %".14", 16, !dbg !394
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !395
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !395
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !395
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !395
  %".20" = icmp eq i8* %".19", null , !dbg !396
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !396
if.then.1:
  %".22" = sub i64 0, 1, !dbg !397
  %".23" = trunc i64 %".22" to i32 , !dbg !397
  ret i32 %".23", !dbg !397
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !398
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !398
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !398
  %".28" = load i64, i64* %"new_cap", !dbg !399
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !399
  store i64 %".28", i64* %".29", !dbg !399
  %".31" = trunc i64 0 to i32 , !dbg !400
  ret i32 %".31", !dbg !400
}

@".str.0" = private constant [4 x i8] c"0x0\00"
@".str.1" = private constant [3 x i8] c"0x\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/ritz/ritzlib", filename: "io.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 15, name: "prints", scopeLine: 15, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 19, name: "eprints", scopeLine: 19, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 24, name: "prints_cstr", scopeLine: 24, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 32, name: "eprints_cstr", scopeLine: 32, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 38, name: "print_char", scopeLine: 38, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 43, name: "eprint_char", scopeLine: 43, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 48, name: "print_int", scopeLine: 48, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 73, name: "eprint_int", scopeLine: 73, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 98, name: "print_hex", scopeLine: 98, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "print_size_human", scopeLine: 124, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 151, name: "println", scopeLine: 151, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 156, name: "eprintln", scopeLine: 156, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 160, name: "newline", scopeLine: 160, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 167, name: "print_string", scopeLine: 167, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 170, name: "eprint_string", scopeLine: 170, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 173, name: "println_string", scopeLine: 173, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 177, name: "eprintln_string", scopeLine: 177, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 182, name: "print_i64", scopeLine: 182, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 187, name: "println_i64", scopeLine: 187, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 192, name: "eprint_i64", scopeLine: 192, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 196, name: "eprintln_i64", scopeLine: 196, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 201, name: "print_hex64", scopeLine: 201, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 205, name: "println_hex64", scopeLine: 205, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!51 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!52 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!53 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!54 = !DICompositeType(align: 64, file: !0, name: "StrView", size: 128, tag: DW_TAG_structure_type)
!55 = !DILocalVariable(file: !0, line: 15, name: "s", scope: !17, type: !54)
!56 = !DILocation(column: 1, line: 15, scope: !17)
!57 = !DILocation(column: 5, line: 16, scope: !17)
!58 = !DILocalVariable(file: !0, line: 19, name: "s", scope: !18, type: !54)
!59 = !DILocation(column: 1, line: 19, scope: !18)
!60 = !DILocation(column: 5, line: 20, scope: !18)
!61 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!62 = !DILocalVariable(file: !0, line: 24, name: "s", scope: !19, type: !61)
!63 = !DILocation(column: 1, line: 24, scope: !19)
!64 = !DILocation(column: 5, line: 25, scope: !19)
!65 = !DILocalVariable(file: !0, line: 25, name: "len", scope: !19, type: !11)
!66 = !DILocation(column: 1, line: 25, scope: !19)
!67 = !DILocation(column: 5, line: 26, scope: !19)
!68 = !DILocation(column: 9, line: 27, scope: !19)
!69 = !DILocation(column: 5, line: 28, scope: !19)
!70 = !DILocalVariable(file: !0, line: 32, name: "s", scope: !20, type: !61)
!71 = !DILocation(column: 1, line: 32, scope: !20)
!72 = !DILocation(column: 5, line: 33, scope: !20)
!73 = !DILocalVariable(file: !0, line: 33, name: "len", scope: !20, type: !11)
!74 = !DILocation(column: 1, line: 33, scope: !20)
!75 = !DILocation(column: 5, line: 34, scope: !20)
!76 = !DILocation(column: 9, line: 35, scope: !20)
!77 = !DILocation(column: 5, line: 36, scope: !20)
!78 = !DILocalVariable(file: !0, line: 38, name: "c", scope: !21, type: !12)
!79 = !DILocation(column: 1, line: 38, scope: !21)
!80 = !DILocation(column: 5, line: 39, scope: !21)
!81 = !DISubrange(count: 1)
!82 = !{ !81 }
!83 = !DICompositeType(baseType: !12, elements: !82, size: 8, tag: DW_TAG_array_type)
!84 = !DILocalVariable(file: !0, line: 39, name: "buf", scope: !21, type: !83)
!85 = !DILocation(column: 1, line: 39, scope: !21)
!86 = !DILocation(column: 5, line: 40, scope: !21)
!87 = !DILocation(column: 5, line: 41, scope: !21)
!88 = !DILocalVariable(file: !0, line: 43, name: "c", scope: !22, type: !12)
!89 = !DILocation(column: 1, line: 43, scope: !22)
!90 = !DILocation(column: 5, line: 44, scope: !22)
!91 = !DILocalVariable(file: !0, line: 44, name: "buf", scope: !22, type: !83)
!92 = !DILocation(column: 1, line: 44, scope: !22)
!93 = !DILocation(column: 5, line: 45, scope: !22)
!94 = !DILocation(column: 5, line: 46, scope: !22)
!95 = !DILocalVariable(file: !0, line: 48, name: "n", scope: !23, type: !11)
!96 = !DILocation(column: 1, line: 48, scope: !23)
!97 = !DILocation(column: 5, line: 49, scope: !23)
!98 = !DILocation(column: 9, line: 50, scope: !23)
!99 = !DILocation(column: 9, line: 51, scope: !23)
!100 = !DILocation(column: 5, line: 53, scope: !23)
!101 = !DILocation(column: 9, line: 54, scope: !23)
!102 = !DILocation(column: 9, line: 55, scope: !23)
!103 = !DILocation(column: 5, line: 57, scope: !23)
!104 = !DISubrange(count: 20)
!105 = !{ !104 }
!106 = !DICompositeType(baseType: !12, elements: !105, size: 160, tag: DW_TAG_array_type)
!107 = !DILocalVariable(file: !0, line: 57, name: "buf", scope: !23, type: !106)
!108 = !DILocation(column: 1, line: 57, scope: !23)
!109 = !DILocation(column: 5, line: 58, scope: !23)
!110 = !DILocalVariable(file: !0, line: 58, name: "len", scope: !23, type: !11)
!111 = !DILocation(column: 1, line: 58, scope: !23)
!112 = !DILocation(column: 5, line: 60, scope: !23)
!113 = !DILocalVariable(file: !0, line: 60, name: "tmp", scope: !23, type: !11)
!114 = !DILocation(column: 1, line: 60, scope: !23)
!115 = !DILocation(column: 5, line: 61, scope: !23)
!116 = !DILocation(column: 9, line: 62, scope: !23)
!117 = !DILocation(column: 9, line: 63, scope: !23)
!118 = !DILocation(column: 5, line: 65, scope: !23)
!119 = !DILocalVariable(file: !0, line: 65, name: "i", scope: !23, type: !11)
!120 = !DILocation(column: 1, line: 65, scope: !23)
!121 = !DILocation(column: 5, line: 66, scope: !23)
!122 = !DILocation(column: 9, line: 67, scope: !23)
!123 = !DILocation(column: 9, line: 68, scope: !23)
!124 = !DILocation(column: 9, line: 69, scope: !23)
!125 = !DILocation(column: 5, line: 71, scope: !23)
!126 = !DILocalVariable(file: !0, line: 73, name: "n", scope: !24, type: !11)
!127 = !DILocation(column: 1, line: 73, scope: !24)
!128 = !DILocation(column: 5, line: 74, scope: !24)
!129 = !DILocation(column: 9, line: 75, scope: !24)
!130 = !DILocation(column: 9, line: 76, scope: !24)
!131 = !DILocation(column: 5, line: 78, scope: !24)
!132 = !DILocation(column: 9, line: 79, scope: !24)
!133 = !DILocation(column: 9, line: 80, scope: !24)
!134 = !DILocation(column: 5, line: 82, scope: !24)
!135 = !DILocalVariable(file: !0, line: 82, name: "buf", scope: !24, type: !106)
!136 = !DILocation(column: 1, line: 82, scope: !24)
!137 = !DILocation(column: 5, line: 83, scope: !24)
!138 = !DILocalVariable(file: !0, line: 83, name: "len", scope: !24, type: !11)
!139 = !DILocation(column: 1, line: 83, scope: !24)
!140 = !DILocation(column: 5, line: 85, scope: !24)
!141 = !DILocalVariable(file: !0, line: 85, name: "tmp", scope: !24, type: !11)
!142 = !DILocation(column: 1, line: 85, scope: !24)
!143 = !DILocation(column: 5, line: 86, scope: !24)
!144 = !DILocation(column: 9, line: 87, scope: !24)
!145 = !DILocation(column: 9, line: 88, scope: !24)
!146 = !DILocation(column: 5, line: 90, scope: !24)
!147 = !DILocalVariable(file: !0, line: 90, name: "i", scope: !24, type: !11)
!148 = !DILocation(column: 1, line: 90, scope: !24)
!149 = !DILocation(column: 5, line: 91, scope: !24)
!150 = !DILocation(column: 9, line: 92, scope: !24)
!151 = !DILocation(column: 9, line: 93, scope: !24)
!152 = !DILocation(column: 9, line: 94, scope: !24)
!153 = !DILocation(column: 5, line: 96, scope: !24)
!154 = !DILocalVariable(file: !0, line: 98, name: "n", scope: !25, type: !11)
!155 = !DILocation(column: 1, line: 98, scope: !25)
!156 = !DILocation(column: 5, line: 99, scope: !25)
!157 = !DILocation(column: 9, line: 100, scope: !25)
!158 = !DILocation(column: 9, line: 101, scope: !25)
!159 = !DILocation(column: 5, line: 103, scope: !25)
!160 = !DILocation(column: 5, line: 104, scope: !25)
!161 = !DISubrange(count: 16)
!162 = !{ !161 }
!163 = !DICompositeType(baseType: !12, elements: !162, size: 128, tag: DW_TAG_array_type)
!164 = !DILocalVariable(file: !0, line: 104, name: "buf", scope: !25, type: !163)
!165 = !DILocation(column: 1, line: 104, scope: !25)
!166 = !DILocation(column: 5, line: 105, scope: !25)
!167 = !DILocalVariable(file: !0, line: 105, name: "len", scope: !25, type: !11)
!168 = !DILocation(column: 1, line: 105, scope: !25)
!169 = !DILocation(column: 5, line: 107, scope: !25)
!170 = !DILocalVariable(file: !0, line: 107, name: "tmp", scope: !25, type: !11)
!171 = !DILocation(column: 1, line: 107, scope: !25)
!172 = !DILocation(column: 5, line: 108, scope: !25)
!173 = !DILocation(column: 9, line: 109, scope: !25)
!174 = !DILocation(column: 9, line: 110, scope: !25)
!175 = !DILocation(column: 5, line: 112, scope: !25)
!176 = !DILocalVariable(file: !0, line: 112, name: "i", scope: !25, type: !11)
!177 = !DILocation(column: 1, line: 112, scope: !25)
!178 = !DILocation(column: 5, line: 113, scope: !25)
!179 = !DILocation(column: 9, line: 114, scope: !25)
!180 = !DILocation(column: 9, line: 115, scope: !25)
!181 = !DILocation(column: 13, line: 116, scope: !25)
!182 = !DILocation(column: 13, line: 118, scope: !25)
!183 = !DILocation(column: 9, line: 119, scope: !25)
!184 = !DILocation(column: 9, line: 120, scope: !25)
!185 = !DILocation(column: 5, line: 122, scope: !25)
!186 = !DILocalVariable(file: !0, line: 124, name: "size", scope: !26, type: !11)
!187 = !DILocation(column: 1, line: 124, scope: !26)
!188 = !DILocation(column: 5, line: 125, scope: !26)
!189 = !DILocation(column: 9, line: 126, scope: !26)
!190 = !DILocation(column: 9, line: 127, scope: !26)
!191 = !DILocation(column: 5, line: 129, scope: !26)
!192 = !DISubrange(count: 4)
!193 = !{ !192 }
!194 = !DICompositeType(baseType: !12, elements: !193, size: 32, tag: DW_TAG_array_type)
!195 = !DILocalVariable(file: !0, line: 129, name: "units", scope: !26, type: !194)
!196 = !DILocation(column: 1, line: 129, scope: !26)
!197 = !DILocation(column: 5, line: 130, scope: !26)
!198 = !DILocation(column: 5, line: 131, scope: !26)
!199 = !DILocation(column: 5, line: 132, scope: !26)
!200 = !DILocation(column: 5, line: 133, scope: !26)
!201 = !DILocation(column: 5, line: 135, scope: !26)
!202 = !DILocalVariable(file: !0, line: 135, name: "s", scope: !26, type: !11)
!203 = !DILocation(column: 1, line: 135, scope: !26)
!204 = !DILocation(column: 5, line: 136, scope: !26)
!205 = !DILocalVariable(file: !0, line: 136, name: "unit", scope: !26, type: !10)
!206 = !DILocation(column: 1, line: 136, scope: !26)
!207 = !DILocation(column: 5, line: 137, scope: !26)
!208 = !DILocation(column: 5, line: 139, scope: !26)
!209 = !DILocation(column: 9, line: 140, scope: !26)
!210 = !DILocation(column: 9, line: 141, scope: !26)
!211 = !DILocation(column: 5, line: 143, scope: !26)
!212 = !DILocation(column: 5, line: 144, scope: !26)
!213 = !DILocalVariable(file: !0, line: 151, name: "s", scope: !27, type: !54)
!214 = !DILocation(column: 1, line: 151, scope: !27)
!215 = !DILocation(column: 5, line: 152, scope: !27)
!216 = !DILocation(column: 5, line: 153, scope: !27)
!217 = !DILocalVariable(file: !0, line: 156, name: "s", scope: !28, type: !54)
!218 = !DILocation(column: 1, line: 156, scope: !28)
!219 = !DILocation(column: 5, line: 157, scope: !28)
!220 = !DILocation(column: 5, line: 158, scope: !28)
!221 = !DILocation(column: 5, line: 161, scope: !29)
!222 = !DICompositeType(align: 64, file: !0, name: "String", size: 192, tag: DW_TAG_structure_type)
!223 = !DIDerivedType(baseType: !222, size: 64, tag: DW_TAG_pointer_type)
!224 = !DILocalVariable(file: !0, line: 167, name: "s", scope: !30, type: !223)
!225 = !DILocation(column: 1, line: 167, scope: !30)
!226 = !DILocation(column: 5, line: 168, scope: !30)
!227 = !DILocalVariable(file: !0, line: 170, name: "s", scope: !31, type: !223)
!228 = !DILocation(column: 1, line: 170, scope: !31)
!229 = !DILocation(column: 5, line: 171, scope: !31)
!230 = !DILocalVariable(file: !0, line: 173, name: "s", scope: !32, type: !223)
!231 = !DILocation(column: 1, line: 173, scope: !32)
!232 = !DILocation(column: 5, line: 174, scope: !32)
!233 = !DILocation(column: 5, line: 175, scope: !32)
!234 = !DILocalVariable(file: !0, line: 177, name: "s", scope: !33, type: !223)
!235 = !DILocation(column: 1, line: 177, scope: !33)
!236 = !DILocation(column: 5, line: 178, scope: !33)
!237 = !DILocation(column: 5, line: 179, scope: !33)
!238 = !DILocalVariable(file: !0, line: 182, name: "n", scope: !34, type: !11)
!239 = !DILocation(column: 1, line: 182, scope: !34)
!240 = !DILocation(column: 5, line: 183, scope: !34)
!241 = !DILocalVariable(file: !0, line: 183, name: "s", scope: !34, type: !222)
!242 = !DILocation(column: 1, line: 183, scope: !34)
!243 = !DILocation(column: 5, line: 184, scope: !34)
!244 = !DILocalVariable(file: !0, line: 187, name: "n", scope: !35, type: !11)
!245 = !DILocation(column: 1, line: 187, scope: !35)
!246 = !DILocation(column: 5, line: 188, scope: !35)
!247 = !DILocalVariable(file: !0, line: 188, name: "s", scope: !35, type: !222)
!248 = !DILocation(column: 1, line: 188, scope: !35)
!249 = !DILocation(column: 5, line: 189, scope: !35)
!250 = !DILocalVariable(file: !0, line: 192, name: "n", scope: !36, type: !11)
!251 = !DILocation(column: 1, line: 192, scope: !36)
!252 = !DILocation(column: 5, line: 193, scope: !36)
!253 = !DILocalVariable(file: !0, line: 193, name: "s", scope: !36, type: !222)
!254 = !DILocation(column: 1, line: 193, scope: !36)
!255 = !DILocation(column: 5, line: 194, scope: !36)
!256 = !DILocalVariable(file: !0, line: 196, name: "n", scope: !37, type: !11)
!257 = !DILocation(column: 1, line: 196, scope: !37)
!258 = !DILocation(column: 5, line: 197, scope: !37)
!259 = !DILocalVariable(file: !0, line: 197, name: "s", scope: !37, type: !222)
!260 = !DILocation(column: 1, line: 197, scope: !37)
!261 = !DILocation(column: 5, line: 198, scope: !37)
!262 = !DILocalVariable(file: !0, line: 201, name: "n", scope: !38, type: !15)
!263 = !DILocation(column: 1, line: 201, scope: !38)
!264 = !DILocation(column: 5, line: 202, scope: !38)
!265 = !DILocalVariable(file: !0, line: 202, name: "s", scope: !38, type: !222)
!266 = !DILocation(column: 1, line: 202, scope: !38)
!267 = !DILocation(column: 5, line: 203, scope: !38)
!268 = !DILocalVariable(file: !0, line: 205, name: "n", scope: !39, type: !15)
!269 = !DILocation(column: 1, line: 205, scope: !39)
!270 = !DILocation(column: 5, line: 206, scope: !39)
!271 = !DILocalVariable(file: !0, line: 206, name: "s", scope: !39, type: !222)
!272 = !DILocation(column: 1, line: 206, scope: !39)
!273 = !DILocation(column: 5, line: 207, scope: !39)
!274 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!275 = !DIDerivedType(baseType: !274, size: 64, tag: DW_TAG_reference_type)
!276 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !40, type: !275)
!277 = !DILocation(column: 1, line: 148, scope: !40)
!278 = !DILocation(column: 5, line: 149, scope: !40)
!279 = !DILocation(column: 5, line: 151, scope: !40)
!280 = !DILocation(column: 5, line: 152, scope: !40)
!281 = !DILocation(column: 5, line: 153, scope: !40)
!282 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!283 = !DIDerivedType(baseType: !282, size: 64, tag: DW_TAG_reference_type)
!284 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !41, type: !283)
!285 = !DILocation(column: 1, line: 210, scope: !41)
!286 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!287 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !41, type: !286)
!288 = !DILocation(column: 5, line: 211, scope: !41)
!289 = !DILocation(column: 9, line: 212, scope: !41)
!290 = !DILocation(column: 5, line: 213, scope: !41)
!291 = !DILocation(column: 5, line: 214, scope: !41)
!292 = !DILocation(column: 5, line: 215, scope: !41)
!293 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !42, type: !275)
!294 = !DILocation(column: 1, line: 244, scope: !42)
!295 = !DILocation(column: 5, line: 245, scope: !42)
!296 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !43, type: !275)
!297 = !DILocation(column: 1, line: 210, scope: !43)
!298 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !43, type: !12)
!299 = !DILocation(column: 5, line: 211, scope: !43)
!300 = !DILocation(column: 9, line: 212, scope: !43)
!301 = !DILocation(column: 5, line: 213, scope: !43)
!302 = !DILocation(column: 5, line: 214, scope: !43)
!303 = !DILocation(column: 5, line: 215, scope: !43)
!304 = !DILocation(column: 5, line: 117, scope: !44)
!305 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !44, type: !274)
!306 = !DILocation(column: 1, line: 117, scope: !44)
!307 = !DILocation(column: 5, line: 118, scope: !44)
!308 = !DILocation(column: 5, line: 119, scope: !44)
!309 = !DILocation(column: 5, line: 120, scope: !44)
!310 = !DILocation(column: 5, line: 121, scope: !44)
!311 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !45, type: !275)
!312 = !DILocation(column: 1, line: 225, scope: !45)
!313 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !45, type: !11)
!314 = !DILocation(column: 5, line: 226, scope: !45)
!315 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !46, type: !275)
!316 = !DILocation(column: 1, line: 235, scope: !46)
!317 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !46, type: !11)
!318 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !46, type: !12)
!319 = !DILocation(column: 5, line: 236, scope: !46)
!320 = !DILocation(column: 5, line: 237, scope: !46)
!321 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !47, type: !275)
!322 = !DILocation(column: 1, line: 288, scope: !47)
!323 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !47, type: !61)
!324 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !47, type: !11)
!325 = !DILocation(column: 5, line: 289, scope: !47)
!326 = !DILocation(column: 13, line: 291, scope: !47)
!327 = !DILocation(column: 5, line: 292, scope: !47)
!328 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !48, type: !11)
!329 = !DILocation(column: 1, line: 124, scope: !48)
!330 = !DILocation(column: 5, line: 125, scope: !48)
!331 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !48, type: !274)
!332 = !DILocation(column: 1, line: 125, scope: !48)
!333 = !DILocation(column: 5, line: 126, scope: !48)
!334 = !DILocation(column: 9, line: 127, scope: !48)
!335 = !DILocation(column: 9, line: 128, scope: !48)
!336 = !DILocation(column: 9, line: 129, scope: !48)
!337 = !DILocation(column: 9, line: 130, scope: !48)
!338 = !DILocation(column: 5, line: 132, scope: !48)
!339 = !DILocation(column: 5, line: 133, scope: !48)
!340 = !DILocation(column: 5, line: 134, scope: !48)
!341 = !DILocation(column: 9, line: 135, scope: !48)
!342 = !DILocation(column: 9, line: 136, scope: !48)
!343 = !DILocation(column: 9, line: 137, scope: !48)
!344 = !DILocation(column: 5, line: 139, scope: !48)
!345 = !DILocation(column: 5, line: 140, scope: !48)
!346 = !DILocation(column: 5, line: 141, scope: !48)
!347 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !49, type: !275)
!348 = !DILocation(column: 1, line: 193, scope: !49)
!349 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !49, type: !11)
!350 = !DILocation(column: 5, line: 194, scope: !49)
!351 = !DILocation(column: 9, line: 195, scope: !49)
!352 = !DILocation(column: 5, line: 197, scope: !49)
!353 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !49, type: !11)
!354 = !DILocation(column: 1, line: 197, scope: !49)
!355 = !DILocation(column: 5, line: 198, scope: !49)
!356 = !DILocation(column: 9, line: 199, scope: !49)
!357 = !DILocation(column: 5, line: 200, scope: !49)
!358 = !DILocation(column: 9, line: 201, scope: !49)
!359 = !DILocation(column: 5, line: 203, scope: !49)
!360 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !50, type: !275)
!361 = !DILocation(column: 1, line: 219, scope: !50)
!362 = !DILocation(column: 5, line: 220, scope: !50)
!363 = !DILocation(column: 5, line: 221, scope: !50)
!364 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !51, type: !283)
!365 = !DILocation(column: 1, line: 193, scope: !51)
!366 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !51, type: !11)
!367 = !DILocation(column: 5, line: 194, scope: !51)
!368 = !DILocation(column: 9, line: 195, scope: !51)
!369 = !DILocation(column: 5, line: 197, scope: !51)
!370 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !51, type: !11)
!371 = !DILocation(column: 1, line: 197, scope: !51)
!372 = !DILocation(column: 5, line: 198, scope: !51)
!373 = !DILocation(column: 9, line: 199, scope: !51)
!374 = !DILocation(column: 5, line: 200, scope: !51)
!375 = !DILocation(column: 9, line: 201, scope: !51)
!376 = !DILocation(column: 5, line: 203, scope: !51)
!377 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !52, type: !275)
!378 = !DILocation(column: 1, line: 179, scope: !52)
!379 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !52, type: !11)
!380 = !DILocation(column: 5, line: 180, scope: !52)
!381 = !DILocation(column: 9, line: 181, scope: !52)
!382 = !DILocation(column: 5, line: 183, scope: !52)
!383 = !DILocation(column: 5, line: 184, scope: !52)
!384 = !DILocation(column: 5, line: 185, scope: !52)
!385 = !DILocation(column: 9, line: 186, scope: !52)
!386 = !DILocation(column: 5, line: 188, scope: !52)
!387 = !DILocation(column: 5, line: 189, scope: !52)
!388 = !DILocation(column: 5, line: 190, scope: !52)
!389 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !53, type: !283)
!390 = !DILocation(column: 1, line: 179, scope: !53)
!391 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !53, type: !11)
!392 = !DILocation(column: 5, line: 180, scope: !53)
!393 = !DILocation(column: 9, line: 181, scope: !53)
!394 = !DILocation(column: 5, line: 183, scope: !53)
!395 = !DILocation(column: 5, line: 184, scope: !53)
!396 = !DILocation(column: 5, line: 185, scope: !53)
!397 = !DILocation(column: 9, line: 186, scope: !53)
!398 = !DILocation(column: 5, line: 188, scope: !53)
!399 = !DILocation(column: 5, line: 189, scope: !53)
!400 = !DILocation(column: 5, line: 190, scope: !53)