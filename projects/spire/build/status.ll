; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Stat" = type {i64, i64, i64, i32, i32, i32, i32, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64}
%"struct.ritz_module_1.Dirent64" = type {i64, i64, i16, i8}
%"struct.ritz_module_1.Timeval" = type {i64, i64}
%"struct.ritz_module_1.Arena" = type {i8*, i64, i64}
%"struct.ritz_module_1.BlockHeader" = type {i64}
%"struct.ritz_module_1.FreeNode" = type {%"struct.ritz_module_1.FreeNode"*}
%"struct.ritz_module_1.SizeBin" = type {%"struct.ritz_module_1.FreeNode"*, i64, i8*, i64, i64}
%"struct.ritz_module_1.GlobalAlloc" = type {[9 x %"struct.ritz_module_1.SizeBin"], i32}
%"struct.ritz_module_1.StrView" = type {i8*, i64}
%"struct.ritz_module_1.Status" = type {i16, %"struct.ritz_module_1.StrView"}
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

define %"struct.ritz_module_1.Status" @"status_continue"() !dbg !17
{
entry:
  %".2" = trunc i64 100 to i16 , !dbg !61
  %".3" = getelementptr [9 x i8], [9 x i8]* @".str.0", i64 0, i64 0 , !dbg !61
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !61
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 8, 1 , !dbg !61
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !61
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !61
  ret %"struct.ritz_module_1.Status" %".7", !dbg !61
}

define %"struct.ritz_module_1.Status" @"status_switching_protocols"() !dbg !18
{
entry:
  %".2" = trunc i64 101 to i16 , !dbg !62
  %".3" = getelementptr [20 x i8], [20 x i8]* @".str.1", i64 0, i64 0 , !dbg !62
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !62
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 19, 1 , !dbg !62
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !62
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !62
  ret %"struct.ritz_module_1.Status" %".7", !dbg !62
}

define %"struct.ritz_module_1.Status" @"status_ok"() !dbg !19
{
entry:
  %".2" = trunc i64 200 to i16 , !dbg !63
  %".3" = getelementptr [3 x i8], [3 x i8]* @".str.2", i64 0, i64 0 , !dbg !63
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !63
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 2, 1 , !dbg !63
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !63
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !63
  ret %"struct.ritz_module_1.Status" %".7", !dbg !63
}

define %"struct.ritz_module_1.Status" @"status_created"() !dbg !20
{
entry:
  %".2" = trunc i64 201 to i16 , !dbg !64
  %".3" = getelementptr [8 x i8], [8 x i8]* @".str.3", i64 0, i64 0 , !dbg !64
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !64
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 7, 1 , !dbg !64
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !64
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !64
  ret %"struct.ritz_module_1.Status" %".7", !dbg !64
}

define %"struct.ritz_module_1.Status" @"status_accepted"() !dbg !21
{
entry:
  %".2" = trunc i64 202 to i16 , !dbg !65
  %".3" = getelementptr [9 x i8], [9 x i8]* @".str.4", i64 0, i64 0 , !dbg !65
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !65
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 8, 1 , !dbg !65
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !65
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !65
  ret %"struct.ritz_module_1.Status" %".7", !dbg !65
}

define %"struct.ritz_module_1.Status" @"status_no_content"() !dbg !22
{
entry:
  %".2" = trunc i64 204 to i16 , !dbg !66
  %".3" = getelementptr [11 x i8], [11 x i8]* @".str.5", i64 0, i64 0 , !dbg !66
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !66
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 10, 1 , !dbg !66
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !66
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !66
  ret %"struct.ritz_module_1.Status" %".7", !dbg !66
}

define %"struct.ritz_module_1.Status" @"status_reset_content"() !dbg !23
{
entry:
  %".2" = trunc i64 205 to i16 , !dbg !67
  %".3" = getelementptr [14 x i8], [14 x i8]* @".str.6", i64 0, i64 0 , !dbg !67
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !67
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 13, 1 , !dbg !67
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !67
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !67
  ret %"struct.ritz_module_1.Status" %".7", !dbg !67
}

define %"struct.ritz_module_1.Status" @"status_partial_content"() !dbg !24
{
entry:
  %".2" = trunc i64 206 to i16 , !dbg !68
  %".3" = getelementptr [16 x i8], [16 x i8]* @".str.7", i64 0, i64 0 , !dbg !68
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !68
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 15, 1 , !dbg !68
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !68
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !68
  ret %"struct.ritz_module_1.Status" %".7", !dbg !68
}

define %"struct.ritz_module_1.Status" @"status_moved_permanently"() !dbg !25
{
entry:
  %".2" = trunc i64 301 to i16 , !dbg !69
  %".3" = getelementptr [18 x i8], [18 x i8]* @".str.8", i64 0, i64 0 , !dbg !69
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !69
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 17, 1 , !dbg !69
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !69
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !69
  ret %"struct.ritz_module_1.Status" %".7", !dbg !69
}

define %"struct.ritz_module_1.Status" @"status_found"() !dbg !26
{
entry:
  %".2" = trunc i64 302 to i16 , !dbg !70
  %".3" = getelementptr [6 x i8], [6 x i8]* @".str.9", i64 0, i64 0 , !dbg !70
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !70
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 5, 1 , !dbg !70
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !70
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !70
  ret %"struct.ritz_module_1.Status" %".7", !dbg !70
}

define %"struct.ritz_module_1.Status" @"status_see_other"() !dbg !27
{
entry:
  %".2" = trunc i64 303 to i16 , !dbg !71
  %".3" = getelementptr [10 x i8], [10 x i8]* @".str.10", i64 0, i64 0 , !dbg !71
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !71
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 9, 1 , !dbg !71
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !71
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !71
  ret %"struct.ritz_module_1.Status" %".7", !dbg !71
}

define %"struct.ritz_module_1.Status" @"status_not_modified"() !dbg !28
{
entry:
  %".2" = trunc i64 304 to i16 , !dbg !72
  %".3" = getelementptr [13 x i8], [13 x i8]* @".str.11", i64 0, i64 0 , !dbg !72
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !72
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 12, 1 , !dbg !72
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !72
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !72
  ret %"struct.ritz_module_1.Status" %".7", !dbg !72
}

define %"struct.ritz_module_1.Status" @"status_temporary_redirect"() !dbg !29
{
entry:
  %".2" = trunc i64 307 to i16 , !dbg !73
  %".3" = getelementptr [19 x i8], [19 x i8]* @".str.12", i64 0, i64 0 , !dbg !73
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !73
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 18, 1 , !dbg !73
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !73
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !73
  ret %"struct.ritz_module_1.Status" %".7", !dbg !73
}

define %"struct.ritz_module_1.Status" @"status_permanent_redirect"() !dbg !30
{
entry:
  %".2" = trunc i64 308 to i16 , !dbg !74
  %".3" = getelementptr [19 x i8], [19 x i8]* @".str.13", i64 0, i64 0 , !dbg !74
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !74
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 18, 1 , !dbg !74
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !74
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !74
  ret %"struct.ritz_module_1.Status" %".7", !dbg !74
}

define %"struct.ritz_module_1.Status" @"status_bad_request"() !dbg !31
{
entry:
  %".2" = trunc i64 400 to i16 , !dbg !75
  %".3" = getelementptr [12 x i8], [12 x i8]* @".str.14", i64 0, i64 0 , !dbg !75
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !75
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 11, 1 , !dbg !75
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !75
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !75
  ret %"struct.ritz_module_1.Status" %".7", !dbg !75
}

define %"struct.ritz_module_1.Status" @"status_unauthorized"() !dbg !32
{
entry:
  %".2" = trunc i64 401 to i16 , !dbg !76
  %".3" = getelementptr [13 x i8], [13 x i8]* @".str.15", i64 0, i64 0 , !dbg !76
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !76
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 12, 1 , !dbg !76
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !76
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !76
  ret %"struct.ritz_module_1.Status" %".7", !dbg !76
}

define %"struct.ritz_module_1.Status" @"status_payment_required"() !dbg !33
{
entry:
  %".2" = trunc i64 402 to i16 , !dbg !77
  %".3" = getelementptr [17 x i8], [17 x i8]* @".str.16", i64 0, i64 0 , !dbg !77
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !77
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 16, 1 , !dbg !77
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !77
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !77
  ret %"struct.ritz_module_1.Status" %".7", !dbg !77
}

define %"struct.ritz_module_1.Status" @"status_forbidden"() !dbg !34
{
entry:
  %".2" = trunc i64 403 to i16 , !dbg !78
  %".3" = getelementptr [10 x i8], [10 x i8]* @".str.17", i64 0, i64 0 , !dbg !78
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !78
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 9, 1 , !dbg !78
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !78
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !78
  ret %"struct.ritz_module_1.Status" %".7", !dbg !78
}

define %"struct.ritz_module_1.Status" @"status_not_found"() !dbg !35
{
entry:
  %".2" = trunc i64 404 to i16 , !dbg !79
  %".3" = getelementptr [10 x i8], [10 x i8]* @".str.18", i64 0, i64 0 , !dbg !79
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !79
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 9, 1 , !dbg !79
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !79
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !79
  ret %"struct.ritz_module_1.Status" %".7", !dbg !79
}

define %"struct.ritz_module_1.Status" @"status_method_not_allowed"() !dbg !36
{
entry:
  %".2" = trunc i64 405 to i16 , !dbg !80
  %".3" = getelementptr [19 x i8], [19 x i8]* @".str.19", i64 0, i64 0 , !dbg !80
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !80
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 18, 1 , !dbg !80
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !80
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !80
  ret %"struct.ritz_module_1.Status" %".7", !dbg !80
}

define %"struct.ritz_module_1.Status" @"status_not_acceptable"() !dbg !37
{
entry:
  %".2" = trunc i64 406 to i16 , !dbg !81
  %".3" = getelementptr [15 x i8], [15 x i8]* @".str.20", i64 0, i64 0 , !dbg !81
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !81
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 14, 1 , !dbg !81
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !81
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !81
  ret %"struct.ritz_module_1.Status" %".7", !dbg !81
}

define %"struct.ritz_module_1.Status" @"status_request_timeout"() !dbg !38
{
entry:
  %".2" = trunc i64 408 to i16 , !dbg !82
  %".3" = getelementptr [16 x i8], [16 x i8]* @".str.21", i64 0, i64 0 , !dbg !82
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !82
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 15, 1 , !dbg !82
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !82
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !82
  ret %"struct.ritz_module_1.Status" %".7", !dbg !82
}

define %"struct.ritz_module_1.Status" @"status_conflict"() !dbg !39
{
entry:
  %".2" = trunc i64 409 to i16 , !dbg !83
  %".3" = getelementptr [9 x i8], [9 x i8]* @".str.22", i64 0, i64 0 , !dbg !83
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !83
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 8, 1 , !dbg !83
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !83
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !83
  ret %"struct.ritz_module_1.Status" %".7", !dbg !83
}

define %"struct.ritz_module_1.Status" @"status_gone"() !dbg !40
{
entry:
  %".2" = trunc i64 410 to i16 , !dbg !84
  %".3" = getelementptr [5 x i8], [5 x i8]* @".str.23", i64 0, i64 0 , !dbg !84
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !84
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 4, 1 , !dbg !84
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !84
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !84
  ret %"struct.ritz_module_1.Status" %".7", !dbg !84
}

define %"struct.ritz_module_1.Status" @"status_length_required"() !dbg !41
{
entry:
  %".2" = trunc i64 411 to i16 , !dbg !85
  %".3" = getelementptr [16 x i8], [16 x i8]* @".str.24", i64 0, i64 0 , !dbg !85
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !85
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 15, 1 , !dbg !85
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !85
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !85
  ret %"struct.ritz_module_1.Status" %".7", !dbg !85
}

define %"struct.ritz_module_1.Status" @"status_precondition_failed"() !dbg !42
{
entry:
  %".2" = trunc i64 412 to i16 , !dbg !86
  %".3" = getelementptr [20 x i8], [20 x i8]* @".str.25", i64 0, i64 0 , !dbg !86
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !86
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 19, 1 , !dbg !86
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !86
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !86
  ret %"struct.ritz_module_1.Status" %".7", !dbg !86
}

define %"struct.ritz_module_1.Status" @"status_payload_too_large"() !dbg !43
{
entry:
  %".2" = trunc i64 413 to i16 , !dbg !87
  %".3" = getelementptr [18 x i8], [18 x i8]* @".str.26", i64 0, i64 0 , !dbg !87
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !87
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 17, 1 , !dbg !87
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !87
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !87
  ret %"struct.ritz_module_1.Status" %".7", !dbg !87
}

define %"struct.ritz_module_1.Status" @"status_uri_too_long"() !dbg !44
{
entry:
  %".2" = trunc i64 414 to i16 , !dbg !88
  %".3" = getelementptr [13 x i8], [13 x i8]* @".str.27", i64 0, i64 0 , !dbg !88
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !88
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 12, 1 , !dbg !88
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !88
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !88
  ret %"struct.ritz_module_1.Status" %".7", !dbg !88
}

define %"struct.ritz_module_1.Status" @"status_unsupported_media_type"() !dbg !45
{
entry:
  %".2" = trunc i64 415 to i16 , !dbg !89
  %".3" = getelementptr [23 x i8], [23 x i8]* @".str.28", i64 0, i64 0 , !dbg !89
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !89
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 22, 1 , !dbg !89
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !89
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !89
  ret %"struct.ritz_module_1.Status" %".7", !dbg !89
}

define %"struct.ritz_module_1.Status" @"status_unprocessable_entity"() !dbg !46
{
entry:
  %".2" = trunc i64 422 to i16 , !dbg !90
  %".3" = getelementptr [21 x i8], [21 x i8]* @".str.29", i64 0, i64 0 , !dbg !90
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !90
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 20, 1 , !dbg !90
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !90
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !90
  ret %"struct.ritz_module_1.Status" %".7", !dbg !90
}

define %"struct.ritz_module_1.Status" @"status_too_many_requests"() !dbg !47
{
entry:
  %".2" = trunc i64 429 to i16 , !dbg !91
  %".3" = getelementptr [18 x i8], [18 x i8]* @".str.30", i64 0, i64 0 , !dbg !91
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !91
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 17, 1 , !dbg !91
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !91
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !91
  ret %"struct.ritz_module_1.Status" %".7", !dbg !91
}

define %"struct.ritz_module_1.Status" @"status_internal_server_error"() !dbg !48
{
entry:
  %".2" = trunc i64 500 to i16 , !dbg !92
  %".3" = getelementptr [22 x i8], [22 x i8]* @".str.31", i64 0, i64 0 , !dbg !92
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !92
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 21, 1 , !dbg !92
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !92
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !92
  ret %"struct.ritz_module_1.Status" %".7", !dbg !92
}

define %"struct.ritz_module_1.Status" @"status_not_implemented"() !dbg !49
{
entry:
  %".2" = trunc i64 501 to i16 , !dbg !93
  %".3" = getelementptr [16 x i8], [16 x i8]* @".str.32", i64 0, i64 0 , !dbg !93
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !93
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 15, 1 , !dbg !93
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !93
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !93
  ret %"struct.ritz_module_1.Status" %".7", !dbg !93
}

define %"struct.ritz_module_1.Status" @"status_bad_gateway"() !dbg !50
{
entry:
  %".2" = trunc i64 502 to i16 , !dbg !94
  %".3" = getelementptr [12 x i8], [12 x i8]* @".str.33", i64 0, i64 0 , !dbg !94
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !94
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 11, 1 , !dbg !94
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !94
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !94
  ret %"struct.ritz_module_1.Status" %".7", !dbg !94
}

define %"struct.ritz_module_1.Status" @"status_service_unavailable"() !dbg !51
{
entry:
  %".2" = trunc i64 503 to i16 , !dbg !95
  %".3" = getelementptr [20 x i8], [20 x i8]* @".str.34", i64 0, i64 0 , !dbg !95
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !95
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 19, 1 , !dbg !95
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !95
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !95
  ret %"struct.ritz_module_1.Status" %".7", !dbg !95
}

define %"struct.ritz_module_1.Status" @"status_gateway_timeout"() !dbg !52
{
entry:
  %".2" = trunc i64 504 to i16 , !dbg !96
  %".3" = getelementptr [16 x i8], [16 x i8]* @".str.35", i64 0, i64 0 , !dbg !96
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !96
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 15, 1 , !dbg !96
  %".6" = insertvalue %"struct.ritz_module_1.Status" undef, i16 %".2", 0 , !dbg !96
  %".7" = insertvalue %"struct.ritz_module_1.Status" %".6", %"struct.ritz_module_1.StrView" %".5", 1 , !dbg !96
  ret %"struct.ritz_module_1.Status" %".7", !dbg !96
}

define %"struct.ritz_module_1.Status" @"status_unknown"(i16 %"code.arg") !dbg !53
{
entry:
  %"code" = alloca i16
  %"s.addr" = alloca %"struct.ritz_module_1.Status", !dbg !99
  store i16 %"code.arg", i16* %"code"
  call void @"llvm.dbg.declare"(metadata i16* %"code", metadata !97, metadata !7), !dbg !98
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Status"* %"s.addr", metadata !101, metadata !7), !dbg !102
  %".6" = load i16, i16* %"code", !dbg !103
  %".7" = load %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %"s.addr", !dbg !103
  %".8" = getelementptr %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %"s.addr", i32 0, i32 0 , !dbg !103
  store i16 %".6", i16* %".8", !dbg !103
  %".10" = getelementptr [8 x i8], [8 x i8]* @".str.36", i64 0, i64 0 , !dbg !104
  %".11" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".10", 0 , !dbg !104
  %".12" = insertvalue %"struct.ritz_module_1.StrView" %".11", i64 7, 1 , !dbg !104
  %".13" = load %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %"s.addr", !dbg !104
  %".14" = getelementptr %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %"s.addr", i32 0, i32 1 , !dbg !104
  store %"struct.ritz_module_1.StrView" %".12", %"struct.ritz_module_1.StrView"* %".14", !dbg !104
  %".16" = load %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %"s.addr", !dbg !105
  ret %"struct.ritz_module_1.Status" %".16", !dbg !105
}

define %"struct.ritz_module_1.Status" @"status_from_code"(i16 %"code.arg") !dbg !54
{
entry:
  %"code" = alloca i16
  store i16 %"code.arg", i16* %"code"
  call void @"llvm.dbg.declare"(metadata i16* %"code", metadata !106, metadata !7), !dbg !107
  %".5" = load i16, i16* %"code", !dbg !108
  switch i16 %".5", label %"match.arm.26" [i16 100, label %"match.arm.0" i16 101, label %"match.arm.1" i16 200, label %"match.arm.2" i16 201, label %"match.arm.3" i16 202, label %"match.arm.4" i16 204, label %"match.arm.5" i16 301, label %"match.arm.6" i16 302, label %"match.arm.7" i16 303, label %"match.arm.8" i16 304, label %"match.arm.9" i16 307, label %"match.arm.10" i16 308, label %"match.arm.11" i16 400, label %"match.arm.12" i16 401, label %"match.arm.13" i16 403, label %"match.arm.14" i16 404, label %"match.arm.15" i16 405, label %"match.arm.16" i16 408, label %"match.arm.17" i16 409, label %"match.arm.18" i16 422, label %"match.arm.19" i16 429, label %"match.arm.20" i16 500, label %"match.arm.21" i16 501, label %"match.arm.22" i16 502, label %"match.arm.23" i16 503, label %"match.arm.24" i16 504, label %"match.arm.25"]  , !dbg !108
match.arm.0:
  %".7" = call %"struct.ritz_module_1.Status" @"status_continue"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.1:
  %".9" = call %"struct.ritz_module_1.Status" @"status_switching_protocols"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.2:
  %".11" = call %"struct.ritz_module_1.Status" @"status_ok"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.3:
  %".13" = call %"struct.ritz_module_1.Status" @"status_created"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.4:
  %".15" = call %"struct.ritz_module_1.Status" @"status_accepted"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.5:
  %".17" = call %"struct.ritz_module_1.Status" @"status_no_content"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.6:
  %".19" = call %"struct.ritz_module_1.Status" @"status_moved_permanently"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.7:
  %".21" = call %"struct.ritz_module_1.Status" @"status_found"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.8:
  %".23" = call %"struct.ritz_module_1.Status" @"status_see_other"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.9:
  %".25" = call %"struct.ritz_module_1.Status" @"status_not_modified"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.10:
  %".27" = call %"struct.ritz_module_1.Status" @"status_temporary_redirect"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.11:
  %".29" = call %"struct.ritz_module_1.Status" @"status_permanent_redirect"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.12:
  %".31" = call %"struct.ritz_module_1.Status" @"status_bad_request"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.13:
  %".33" = call %"struct.ritz_module_1.Status" @"status_unauthorized"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.14:
  %".35" = call %"struct.ritz_module_1.Status" @"status_forbidden"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.15:
  %".37" = call %"struct.ritz_module_1.Status" @"status_not_found"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.16:
  %".39" = call %"struct.ritz_module_1.Status" @"status_method_not_allowed"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.17:
  %".41" = call %"struct.ritz_module_1.Status" @"status_request_timeout"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.18:
  %".43" = call %"struct.ritz_module_1.Status" @"status_conflict"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.19:
  %".45" = call %"struct.ritz_module_1.Status" @"status_unprocessable_entity"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.20:
  %".47" = call %"struct.ritz_module_1.Status" @"status_too_many_requests"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.21:
  %".49" = call %"struct.ritz_module_1.Status" @"status_internal_server_error"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.22:
  %".51" = call %"struct.ritz_module_1.Status" @"status_not_implemented"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.23:
  %".53" = call %"struct.ritz_module_1.Status" @"status_bad_gateway"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.24:
  %".55" = call %"struct.ritz_module_1.Status" @"status_service_unavailable"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.25:
  %".57" = call %"struct.ritz_module_1.Status" @"status_gateway_timeout"(), !dbg !108
  br label %"match.merge", !dbg !108
match.arm.26:
  %".59" = load i16, i16* %"code", !dbg !108
  %".60" = call %"struct.ritz_module_1.Status" @"status_unknown"(i16 %".59"), !dbg !108
  br label %"match.merge", !dbg !108
match.merge:
  %".62" = phi  %"struct.ritz_module_1.Status" [%".7", %"match.arm.0"], [%".9", %"match.arm.1"], [%".11", %"match.arm.2"], [%".13", %"match.arm.3"], [%".15", %"match.arm.4"], [%".17", %"match.arm.5"], [%".19", %"match.arm.6"], [%".21", %"match.arm.7"], [%".23", %"match.arm.8"], [%".25", %"match.arm.9"], [%".27", %"match.arm.10"], [%".29", %"match.arm.11"], [%".31", %"match.arm.12"], [%".33", %"match.arm.13"], [%".35", %"match.arm.14"], [%".37", %"match.arm.15"], [%".39", %"match.arm.16"], [%".41", %"match.arm.17"], [%".43", %"match.arm.18"], [%".45", %"match.arm.19"], [%".47", %"match.arm.20"], [%".49", %"match.arm.21"], [%".51", %"match.arm.22"], [%".53", %"match.arm.23"], [%".55", %"match.arm.24"], [%".57", %"match.arm.25"], [%".60", %"match.arm.26"] , !dbg !108
  ret %"struct.ritz_module_1.Status" %".62", !dbg !108
}

define i32 @"status_is_informational"(%"struct.ritz_module_1.Status"* %"s.arg") !dbg !55
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Status"*
  store %"struct.ritz_module_1.Status"* %"s.arg", %"struct.ritz_module_1.Status"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Status"** %"s", metadata !110, metadata !7), !dbg !111
  %".5" = load %"struct.ritz_module_1.Status"*, %"struct.ritz_module_1.Status"** %"s", !dbg !112
  %".6" = getelementptr %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %".5", i32 0, i32 0 , !dbg !112
  %".7" = load i16, i16* %".6", !dbg !112
  %".8" = zext i16 %".7" to i64 , !dbg !112
  %".9" = icmp uge i64 %".8", 100 , !dbg !112
  br i1 %".9", label %"and.right", label %"and.merge", !dbg !112
and.right:
  %".11" = load %"struct.ritz_module_1.Status"*, %"struct.ritz_module_1.Status"** %"s", !dbg !112
  %".12" = getelementptr %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %".11", i32 0, i32 0 , !dbg !112
  %".13" = load i16, i16* %".12", !dbg !112
  %".14" = zext i16 %".13" to i64 , !dbg !112
  %".15" = icmp ult i64 %".14", 200 , !dbg !112
  br label %"and.merge", !dbg !112
and.merge:
  %".17" = phi  i1 [0, %"entry"], [%".15", %"and.right"] , !dbg !112
  br i1 %".17", label %"if.then", label %"if.end", !dbg !112
if.then:
  %".19" = trunc i64 1 to i32 , !dbg !113
  ret i32 %".19", !dbg !113
if.end:
  %".21" = trunc i64 0 to i32 , !dbg !114
  ret i32 %".21", !dbg !114
}

define i32 @"status_is_success"(%"struct.ritz_module_1.Status"* %"s.arg") !dbg !56
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Status"*
  store %"struct.ritz_module_1.Status"* %"s.arg", %"struct.ritz_module_1.Status"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Status"** %"s", metadata !115, metadata !7), !dbg !116
  %".5" = load %"struct.ritz_module_1.Status"*, %"struct.ritz_module_1.Status"** %"s", !dbg !117
  %".6" = getelementptr %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %".5", i32 0, i32 0 , !dbg !117
  %".7" = load i16, i16* %".6", !dbg !117
  %".8" = zext i16 %".7" to i64 , !dbg !117
  %".9" = icmp uge i64 %".8", 200 , !dbg !117
  br i1 %".9", label %"and.right", label %"and.merge", !dbg !117
and.right:
  %".11" = load %"struct.ritz_module_1.Status"*, %"struct.ritz_module_1.Status"** %"s", !dbg !117
  %".12" = getelementptr %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %".11", i32 0, i32 0 , !dbg !117
  %".13" = load i16, i16* %".12", !dbg !117
  %".14" = zext i16 %".13" to i64 , !dbg !117
  %".15" = icmp ult i64 %".14", 300 , !dbg !117
  br label %"and.merge", !dbg !117
and.merge:
  %".17" = phi  i1 [0, %"entry"], [%".15", %"and.right"] , !dbg !117
  br i1 %".17", label %"if.then", label %"if.end", !dbg !117
if.then:
  %".19" = trunc i64 1 to i32 , !dbg !118
  ret i32 %".19", !dbg !118
if.end:
  %".21" = trunc i64 0 to i32 , !dbg !119
  ret i32 %".21", !dbg !119
}

define i32 @"status_is_redirect"(%"struct.ritz_module_1.Status"* %"s.arg") !dbg !57
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Status"*
  store %"struct.ritz_module_1.Status"* %"s.arg", %"struct.ritz_module_1.Status"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Status"** %"s", metadata !120, metadata !7), !dbg !121
  %".5" = load %"struct.ritz_module_1.Status"*, %"struct.ritz_module_1.Status"** %"s", !dbg !122
  %".6" = getelementptr %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %".5", i32 0, i32 0 , !dbg !122
  %".7" = load i16, i16* %".6", !dbg !122
  %".8" = zext i16 %".7" to i64 , !dbg !122
  %".9" = icmp uge i64 %".8", 300 , !dbg !122
  br i1 %".9", label %"and.right", label %"and.merge", !dbg !122
and.right:
  %".11" = load %"struct.ritz_module_1.Status"*, %"struct.ritz_module_1.Status"** %"s", !dbg !122
  %".12" = getelementptr %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %".11", i32 0, i32 0 , !dbg !122
  %".13" = load i16, i16* %".12", !dbg !122
  %".14" = zext i16 %".13" to i64 , !dbg !122
  %".15" = icmp ult i64 %".14", 400 , !dbg !122
  br label %"and.merge", !dbg !122
and.merge:
  %".17" = phi  i1 [0, %"entry"], [%".15", %"and.right"] , !dbg !122
  br i1 %".17", label %"if.then", label %"if.end", !dbg !122
if.then:
  %".19" = trunc i64 1 to i32 , !dbg !123
  ret i32 %".19", !dbg !123
if.end:
  %".21" = trunc i64 0 to i32 , !dbg !124
  ret i32 %".21", !dbg !124
}

define i32 @"status_is_client_error"(%"struct.ritz_module_1.Status"* %"s.arg") !dbg !58
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Status"*
  store %"struct.ritz_module_1.Status"* %"s.arg", %"struct.ritz_module_1.Status"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Status"** %"s", metadata !125, metadata !7), !dbg !126
  %".5" = load %"struct.ritz_module_1.Status"*, %"struct.ritz_module_1.Status"** %"s", !dbg !127
  %".6" = getelementptr %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %".5", i32 0, i32 0 , !dbg !127
  %".7" = load i16, i16* %".6", !dbg !127
  %".8" = zext i16 %".7" to i64 , !dbg !127
  %".9" = icmp uge i64 %".8", 400 , !dbg !127
  br i1 %".9", label %"and.right", label %"and.merge", !dbg !127
and.right:
  %".11" = load %"struct.ritz_module_1.Status"*, %"struct.ritz_module_1.Status"** %"s", !dbg !127
  %".12" = getelementptr %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %".11", i32 0, i32 0 , !dbg !127
  %".13" = load i16, i16* %".12", !dbg !127
  %".14" = zext i16 %".13" to i64 , !dbg !127
  %".15" = icmp ult i64 %".14", 500 , !dbg !127
  br label %"and.merge", !dbg !127
and.merge:
  %".17" = phi  i1 [0, %"entry"], [%".15", %"and.right"] , !dbg !127
  br i1 %".17", label %"if.then", label %"if.end", !dbg !127
if.then:
  %".19" = trunc i64 1 to i32 , !dbg !128
  ret i32 %".19", !dbg !128
if.end:
  %".21" = trunc i64 0 to i32 , !dbg !129
  ret i32 %".21", !dbg !129
}

define i32 @"status_is_server_error"(%"struct.ritz_module_1.Status"* %"s.arg") !dbg !59
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Status"*
  store %"struct.ritz_module_1.Status"* %"s.arg", %"struct.ritz_module_1.Status"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Status"** %"s", metadata !130, metadata !7), !dbg !131
  %".5" = load %"struct.ritz_module_1.Status"*, %"struct.ritz_module_1.Status"** %"s", !dbg !132
  %".6" = getelementptr %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %".5", i32 0, i32 0 , !dbg !132
  %".7" = load i16, i16* %".6", !dbg !132
  %".8" = zext i16 %".7" to i64 , !dbg !132
  %".9" = icmp uge i64 %".8", 500 , !dbg !132
  br i1 %".9", label %"and.right", label %"and.merge", !dbg !132
and.right:
  %".11" = load %"struct.ritz_module_1.Status"*, %"struct.ritz_module_1.Status"** %"s", !dbg !132
  %".12" = getelementptr %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %".11", i32 0, i32 0 , !dbg !132
  %".13" = load i16, i16* %".12", !dbg !132
  %".14" = zext i16 %".13" to i64 , !dbg !132
  %".15" = icmp ult i64 %".14", 600 , !dbg !132
  br label %"and.merge", !dbg !132
and.merge:
  %".17" = phi  i1 [0, %"entry"], [%".15", %"and.right"] , !dbg !132
  br i1 %".17", label %"if.then", label %"if.end", !dbg !132
if.then:
  %".19" = trunc i64 1 to i32 , !dbg !133
  ret i32 %".19", !dbg !133
if.end:
  %".21" = trunc i64 0 to i32 , !dbg !134
  ret i32 %".21", !dbg !134
}

define i32 @"status_is_error"(%"struct.ritz_module_1.Status"* %"s.arg") !dbg !60
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Status"*
  store %"struct.ritz_module_1.Status"* %"s.arg", %"struct.ritz_module_1.Status"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Status"** %"s", metadata !135, metadata !7), !dbg !136
  %".5" = load %"struct.ritz_module_1.Status"*, %"struct.ritz_module_1.Status"** %"s", !dbg !137
  %".6" = getelementptr %"struct.ritz_module_1.Status", %"struct.ritz_module_1.Status"* %".5", i32 0, i32 0 , !dbg !137
  %".7" = load i16, i16* %".6", !dbg !137
  %".8" = zext i16 %".7" to i64 , !dbg !137
  %".9" = icmp uge i64 %".8", 400 , !dbg !137
  br i1 %".9", label %"if.then", label %"if.end", !dbg !137
if.then:
  %".11" = trunc i64 1 to i32 , !dbg !138
  ret i32 %".11", !dbg !138
if.end:
  %".13" = trunc i64 0 to i32 , !dbg !139
  ret i32 %".13", !dbg !139
}

@".str.0" = private constant [9 x i8] c"Continue\00"
@".str.1" = private constant [20 x i8] c"Switching Protocols\00"
@".str.2" = private constant [3 x i8] c"OK\00"
@".str.3" = private constant [8 x i8] c"Created\00"
@".str.4" = private constant [9 x i8] c"Accepted\00"
@".str.5" = private constant [11 x i8] c"No Content\00"
@".str.6" = private constant [14 x i8] c"Reset Content\00"
@".str.7" = private constant [16 x i8] c"Partial Content\00"
@".str.8" = private constant [18 x i8] c"Moved Permanently\00"
@".str.9" = private constant [6 x i8] c"Found\00"
@".str.10" = private constant [10 x i8] c"See Other\00"
@".str.11" = private constant [13 x i8] c"Not Modified\00"
@".str.12" = private constant [19 x i8] c"Temporary Redirect\00"
@".str.13" = private constant [19 x i8] c"Permanent Redirect\00"
@".str.14" = private constant [12 x i8] c"Bad Request\00"
@".str.15" = private constant [13 x i8] c"Unauthorized\00"
@".str.16" = private constant [17 x i8] c"Payment Required\00"
@".str.17" = private constant [10 x i8] c"Forbidden\00"
@".str.18" = private constant [10 x i8] c"Not Found\00"
@".str.19" = private constant [19 x i8] c"Method Not Allowed\00"
@".str.20" = private constant [15 x i8] c"Not Acceptable\00"
@".str.21" = private constant [16 x i8] c"Request Timeout\00"
@".str.22" = private constant [9 x i8] c"Conflict\00"
@".str.23" = private constant [5 x i8] c"Gone\00"
@".str.24" = private constant [16 x i8] c"Length Required\00"
@".str.25" = private constant [20 x i8] c"Precondition Failed\00"
@".str.26" = private constant [18 x i8] c"Payload Too Large\00"
@".str.27" = private constant [13 x i8] c"URI Too Long\00"
@".str.28" = private constant [23 x i8] c"Unsupported Media Type\00"
@".str.29" = private constant [21 x i8] c"Unprocessable Entity\00"
@".str.30" = private constant [18 x i8] c"Too Many Requests\00"
@".str.31" = private constant [22 x i8] c"Internal Server Error\00"
@".str.32" = private constant [16 x i8] c"Not Implemented\00"
@".str.33" = private constant [12 x i8] c"Bad Gateway\00"
@".str.34" = private constant [20 x i8] c"Service Unavailable\00"
@".str.35" = private constant [16 x i8] c"Gateway Timeout\00"
@".str.36" = private constant [8 x i8] c"Unknown\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/spire/lib/http", filename: "status.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 15, name: "status_continue", scopeLine: 15, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 18, name: "status_switching_protocols", scopeLine: 18, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 22, name: "status_ok", scopeLine: 22, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 25, name: "status_created", scopeLine: 25, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 28, name: "status_accepted", scopeLine: 28, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 31, name: "status_no_content", scopeLine: 31, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 34, name: "status_reset_content", scopeLine: 34, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 37, name: "status_partial_content", scopeLine: 37, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 41, name: "status_moved_permanently", scopeLine: 41, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 44, name: "status_found", scopeLine: 44, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 47, name: "status_see_other", scopeLine: 47, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 50, name: "status_not_modified", scopeLine: 50, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 53, name: "status_temporary_redirect", scopeLine: 53, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 56, name: "status_permanent_redirect", scopeLine: 56, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 60, name: "status_bad_request", scopeLine: 60, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 63, name: "status_unauthorized", scopeLine: 63, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 66, name: "status_payment_required", scopeLine: 66, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 69, name: "status_forbidden", scopeLine: 69, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 72, name: "status_not_found", scopeLine: 72, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 75, name: "status_method_not_allowed", scopeLine: 75, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 78, name: "status_not_acceptable", scopeLine: 78, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 81, name: "status_request_timeout", scopeLine: 81, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 84, name: "status_conflict", scopeLine: 84, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 87, name: "status_gone", scopeLine: 87, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 90, name: "status_length_required", scopeLine: 90, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 93, name: "status_precondition_failed", scopeLine: 93, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 96, name: "status_payload_too_large", scopeLine: 96, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 99, name: "status_uri_too_long", scopeLine: 99, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 102, name: "status_unsupported_media_type", scopeLine: 102, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 105, name: "status_unprocessable_entity", scopeLine: 105, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 108, name: "status_too_many_requests", scopeLine: 108, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 112, name: "status_internal_server_error", scopeLine: 112, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 115, name: "status_not_implemented", scopeLine: 115, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 118, name: "status_bad_gateway", scopeLine: 118, type: !4, unit: !1)
!51 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 121, name: "status_service_unavailable", scopeLine: 121, type: !4, unit: !1)
!52 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "status_gateway_timeout", scopeLine: 124, type: !4, unit: !1)
!53 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 127, name: "status_unknown", scopeLine: 127, type: !4, unit: !1)
!54 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 134, name: "status_from_code", scopeLine: 134, type: !4, unit: !1)
!55 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 169, name: "status_is_informational", scopeLine: 169, type: !4, unit: !1)
!56 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 175, name: "status_is_success", scopeLine: 175, type: !4, unit: !1)
!57 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 181, name: "status_is_redirect", scopeLine: 181, type: !4, unit: !1)
!58 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 187, name: "status_is_client_error", scopeLine: 187, type: !4, unit: !1)
!59 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "status_is_server_error", scopeLine: 193, type: !4, unit: !1)
!60 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 199, name: "status_is_error", scopeLine: 199, type: !4, unit: !1)
!61 = !DILocation(column: 5, line: 16, scope: !17)
!62 = !DILocation(column: 5, line: 19, scope: !18)
!63 = !DILocation(column: 5, line: 23, scope: !19)
!64 = !DILocation(column: 5, line: 26, scope: !20)
!65 = !DILocation(column: 5, line: 29, scope: !21)
!66 = !DILocation(column: 5, line: 32, scope: !22)
!67 = !DILocation(column: 5, line: 35, scope: !23)
!68 = !DILocation(column: 5, line: 38, scope: !24)
!69 = !DILocation(column: 5, line: 42, scope: !25)
!70 = !DILocation(column: 5, line: 45, scope: !26)
!71 = !DILocation(column: 5, line: 48, scope: !27)
!72 = !DILocation(column: 5, line: 51, scope: !28)
!73 = !DILocation(column: 5, line: 54, scope: !29)
!74 = !DILocation(column: 5, line: 57, scope: !30)
!75 = !DILocation(column: 5, line: 61, scope: !31)
!76 = !DILocation(column: 5, line: 64, scope: !32)
!77 = !DILocation(column: 5, line: 67, scope: !33)
!78 = !DILocation(column: 5, line: 70, scope: !34)
!79 = !DILocation(column: 5, line: 73, scope: !35)
!80 = !DILocation(column: 5, line: 76, scope: !36)
!81 = !DILocation(column: 5, line: 79, scope: !37)
!82 = !DILocation(column: 5, line: 82, scope: !38)
!83 = !DILocation(column: 5, line: 85, scope: !39)
!84 = !DILocation(column: 5, line: 88, scope: !40)
!85 = !DILocation(column: 5, line: 91, scope: !41)
!86 = !DILocation(column: 5, line: 94, scope: !42)
!87 = !DILocation(column: 5, line: 97, scope: !43)
!88 = !DILocation(column: 5, line: 100, scope: !44)
!89 = !DILocation(column: 5, line: 103, scope: !45)
!90 = !DILocation(column: 5, line: 106, scope: !46)
!91 = !DILocation(column: 5, line: 109, scope: !47)
!92 = !DILocation(column: 5, line: 113, scope: !48)
!93 = !DILocation(column: 5, line: 116, scope: !49)
!94 = !DILocation(column: 5, line: 119, scope: !50)
!95 = !DILocation(column: 5, line: 122, scope: !51)
!96 = !DILocation(column: 5, line: 125, scope: !52)
!97 = !DILocalVariable(file: !0, line: 127, name: "code", scope: !53, type: !13)
!98 = !DILocation(column: 1, line: 127, scope: !53)
!99 = !DILocation(column: 5, line: 128, scope: !53)
!100 = !DICompositeType(align: 64, file: !0, name: "Status", size: 192, tag: DW_TAG_structure_type)
!101 = !DILocalVariable(file: !0, line: 128, name: "s", scope: !53, type: !100)
!102 = !DILocation(column: 1, line: 128, scope: !53)
!103 = !DILocation(column: 5, line: 129, scope: !53)
!104 = !DILocation(column: 5, line: 130, scope: !53)
!105 = !DILocation(column: 5, line: 131, scope: !53)
!106 = !DILocalVariable(file: !0, line: 134, name: "code", scope: !54, type: !13)
!107 = !DILocation(column: 1, line: 134, scope: !54)
!108 = !DILocation(column: 5, line: 135, scope: !54)
!109 = !DIDerivedType(baseType: !100, size: 64, tag: DW_TAG_pointer_type)
!110 = !DILocalVariable(file: !0, line: 169, name: "s", scope: !55, type: !109)
!111 = !DILocation(column: 1, line: 169, scope: !55)
!112 = !DILocation(column: 5, line: 170, scope: !55)
!113 = !DILocation(column: 9, line: 171, scope: !55)
!114 = !DILocation(column: 5, line: 172, scope: !55)
!115 = !DILocalVariable(file: !0, line: 175, name: "s", scope: !56, type: !109)
!116 = !DILocation(column: 1, line: 175, scope: !56)
!117 = !DILocation(column: 5, line: 176, scope: !56)
!118 = !DILocation(column: 9, line: 177, scope: !56)
!119 = !DILocation(column: 5, line: 178, scope: !56)
!120 = !DILocalVariable(file: !0, line: 181, name: "s", scope: !57, type: !109)
!121 = !DILocation(column: 1, line: 181, scope: !57)
!122 = !DILocation(column: 5, line: 182, scope: !57)
!123 = !DILocation(column: 9, line: 183, scope: !57)
!124 = !DILocation(column: 5, line: 184, scope: !57)
!125 = !DILocalVariable(file: !0, line: 187, name: "s", scope: !58, type: !109)
!126 = !DILocation(column: 1, line: 187, scope: !58)
!127 = !DILocation(column: 5, line: 188, scope: !58)
!128 = !DILocation(column: 9, line: 189, scope: !58)
!129 = !DILocation(column: 5, line: 190, scope: !58)
!130 = !DILocalVariable(file: !0, line: 193, name: "s", scope: !59, type: !109)
!131 = !DILocation(column: 1, line: 193, scope: !59)
!132 = !DILocation(column: 5, line: 194, scope: !59)
!133 = !DILocation(column: 9, line: 195, scope: !59)
!134 = !DILocation(column: 5, line: 196, scope: !59)
!135 = !DILocalVariable(file: !0, line: 199, name: "s", scope: !60, type: !109)
!136 = !DILocation(column: 1, line: 199, scope: !60)
!137 = !DILocation(column: 5, line: 200, scope: !60)
!138 = !DILocation(column: 9, line: 201, scope: !60)
!139 = !DILocation(column: 5, line: 202, scope: !60)