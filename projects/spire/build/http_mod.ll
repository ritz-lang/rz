; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Vec$LineBounds" = type {%"struct.ritz_module_1.LineBounds"*, i64, i64}
%"struct.ritz_module_1.Vec$u8" = type {i8*, i64, i64}
%"struct.ritz_module_1.Span$u8" = type {i8*, i64}
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
%"struct.ritz_module_1.Header" = type {[128 x i8], i64, [1024 x i8], i64}
%"struct.ritz_module_1.Headers" = type {[64 x %"struct.ritz_module_1.Header"], i64}
%"struct.ritz_module_1.String" = type {%"struct.ritz_module_1.Vec$u8"}
%"struct.ritz_module_1.RouteParam" = type {[64 x i8], i64, [256 x i8], i64}
%"struct.ritz_module_1.Request" = type {i32, [1024 x i8], i64, [1024 x i8], i64, [64 x %"struct.ritz_module_1.RouteParam"], i64, [16 x %"struct.ritz_module_1.RouteParam"], i64, [65536 x i8], i64}
%"struct.ritz_module_1.ResponseHeader" = type {[128 x i8], i64, [512 x i8], i64}
%"struct.ritz_module_1.Response" = type {i32, [32 x %"struct.ritz_module_1.ResponseHeader"], i64, [65536 x i8], i64}
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

define linkonce_odr i64 @"Span$u8_len"(%"struct.ritz_module_1.Span$u8"* %"self.arg") !dbg !17
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !212, metadata !7), !dbg !213
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !214
  %".6" = call i64 @"span_len$u8"(%"struct.ritz_module_1.Span$u8"* %".5"), !dbg !214
  ret i64 %".6", !dbg !214
}

define linkonce_odr i32 @"Span$u8_is_empty"(%"struct.ritz_module_1.Span$u8"* %"self.arg") !dbg !18
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !215, metadata !7), !dbg !216
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !217
  %".6" = call i32 @"span_is_empty$u8"(%"struct.ritz_module_1.Span$u8"* %".5"), !dbg !217
  ret i32 %".6", !dbg !217
}

define linkonce_odr i8 @"Span$u8_get"(%"struct.ritz_module_1.Span$u8"* %"self.arg", i64 %"idx.arg") !dbg !19
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !218, metadata !7), !dbg !219
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !220, metadata !7), !dbg !219
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !221
  %".9" = load i64, i64* %"idx", !dbg !221
  %".10" = call i8 @"span_get$u8"(%"struct.ritz_module_1.Span$u8"* %".8", i64 %".9"), !dbg !221
  ret i8 %".10", !dbg !221
}

define linkonce_odr i8* @"Span$u8_get_ptr"(%"struct.ritz_module_1.Span$u8"* %"self.arg", i64 %"idx.arg") !dbg !20
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !222, metadata !7), !dbg !223
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !224, metadata !7), !dbg !223
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !225
  %".9" = load i64, i64* %"idx", !dbg !225
  %".10" = call i8* @"span_get_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %".8", i64 %".9"), !dbg !225
  ret i8* %".10", !dbg !225
}

define linkonce_odr i8* @"Span$u8_as_ptr"(%"struct.ritz_module_1.Span$u8"* %"self.arg") !dbg !21
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !226, metadata !7), !dbg !227
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !228
  %".6" = call i8* @"span_as_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %".5"), !dbg !228
  ret i8* %".6", !dbg !228
}

define linkonce_odr %"struct.ritz_module_1.Span$u8" @"Span$u8_slice"(%"struct.ritz_module_1.Span$u8"* %"self.arg", i64 %"start.arg", i64 %"end.arg") !dbg !22
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !229, metadata !7), !dbg !230
  %"start" = alloca i64
  store i64 %"start.arg", i64* %"start"
  call void @"llvm.dbg.declare"(metadata i64* %"start", metadata !231, metadata !7), !dbg !230
  %"end" = alloca i64
  store i64 %"end.arg", i64* %"end"
  call void @"llvm.dbg.declare"(metadata i64* %"end", metadata !232, metadata !7), !dbg !230
  %".11" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !233
  %".12" = load i64, i64* %"start", !dbg !233
  %".13" = load i64, i64* %"end", !dbg !233
  %".14" = call %"struct.ritz_module_1.Span$u8" @"span_slice$u8"(%"struct.ritz_module_1.Span$u8"* %".11", i64 %".12", i64 %".13"), !dbg !233
  ret %"struct.ritz_module_1.Span$u8" %".14", !dbg !233
}

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

declare i32 @"vec_push_str"(%"struct.ritz_module_1.Vec$u8"** %".1", i8* %".2")

declare i8* @"vec_as_str"(%"struct.ritz_module_1.Vec$u8"** %".1")

declare i64 @"vec_read_all_fd"(i32 %".1", %"struct.ritz_module_1.Vec$u8"** %".2")

declare i32 @"vec_find_lines"(%"struct.ritz_module_1.Vec$u8"* %".1", %"struct.ritz_module_1.Vec$LineBounds"** %".2")

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

declare %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".1")

declare %"struct.ritz_module_1.Span$u8" @"span_from_strview"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"span_eq"(%"struct.ritz_module_1.Span$u8"* %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare i32 @"span_contains"(%"struct.ritz_module_1.Span$u8"* %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare i32 @"span_starts_with"(%"struct.ritz_module_1.Span$u8"* %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare i32 @"span_ends_with"(%"struct.ritz_module_1.Span$u8"* %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare i64 @"span_find"(%"struct.ritz_module_1.Span$u8"* %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare i64 @"span_find_byte"(%"struct.ritz_module_1.Span$u8"* %".1", i8 %".2")

declare i32 @"span_eq_cstr"(%"struct.ritz_module_1.Span$u8"* %".1", i8* %".2")

declare %"struct.ritz_module_1.Span$u8" @"span_take"(%"struct.ritz_module_1.Span$u8"* %".1", i64 %".2")

declare %"struct.ritz_module_1.Span$u8" @"span_skip"(%"struct.ritz_module_1.Span$u8"* %".1", i64 %".2")

declare %"struct.ritz_module_1.Span$u8" @"span_from_bytes"(i8* %".1", i64 %".2")

declare %"struct.ritz_module_1.Span$u8" @"span_literal"(i8* %".1", i64 %".2")

declare %"struct.ritz_module_1.Span$u8" @"http_200_ok"()

declare %"struct.ritz_module_1.Span$u8" @"http_404_not_found"()

declare %"struct.ritz_module_1.Span$u8" @"http_400_bad_request"()

declare %"struct.ritz_module_1.Span$u8" @"http_500_internal_error"()

declare %"struct.ritz_module_1.Span$u8" @"http_content_length"()

declare %"struct.ritz_module_1.Span$u8" @"http_content_type_text"()

declare %"struct.ritz_module_1.Span$u8" @"http_content_type_html"()

declare %"struct.ritz_module_1.Span$u8" @"http_content_type_json"()

declare %"struct.ritz_module_1.Span$u8" @"http_connection_close"()

declare %"struct.ritz_module_1.Span$u8" @"http_connection_keepalive"()

declare %"struct.ritz_module_1.Span$u8" @"http_crlf"()

declare %"struct.ritz_module_1.Span$u8" @"http_hello_world"()

declare %"struct.ritz_module_1.Span$u8" @"http_not_found_body"()

declare i32 @"method_from_span"(%"struct.ritz_module_1.Span$u8"* %".1")

declare %"struct.ritz_module_1.Span$u8" @"method_to_span"(i32 %".1")

declare i32 @"version_from_span"(%"struct.ritz_module_1.Span$u8"* %".1")

declare %"struct.ritz_module_1.Span$u8" @"version_to_span"(i32 %".1")

declare %"struct.ritz_module_1.Span$u8" @"status_reason"(i32 %".1")

declare i32 @"status_is_info"(i32 %".1")

declare i32 @"status_is_success"(i32 %".1")

declare i32 @"status_is_redirect"(i32 %".1")

declare i32 @"status_is_client_error"(i32 %".1")

declare i32 @"status_is_server_error"(i32 %".1")

declare %"struct.ritz_module_1.Headers" @"headers_new"()

declare i32 @"headers_add"(%"struct.ritz_module_1.Headers"* %".1", %"struct.ritz_module_1.Span$u8"* %".2", %"struct.ritz_module_1.Span$u8"* %".3")

declare i32 @"headers_set"(%"struct.ritz_module_1.Headers"* %".1", %"struct.ritz_module_1.Span$u8"* %".2", %"struct.ritz_module_1.Span$u8"* %".3")

declare i32 @"headers_get"(%"struct.ritz_module_1.Headers"* %".1", %"struct.ritz_module_1.Span$u8"* %".2", %"struct.ritz_module_1.Span$u8"* %".3")

declare i32 @"headers_contains"(%"struct.ritz_module_1.Headers"* %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare i32 @"headers_remove"(%"struct.ritz_module_1.Headers"* %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare i64 @"headers_len"(%"struct.ritz_module_1.Headers"* %".1")

declare i32 @"header_name_eq"(%"struct.ritz_module_1.Span$u8"* %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare i8 @"to_lower"(i8 %".1")

declare %"struct.ritz_module_1.Span$u8" @"header_content_type"()

declare %"struct.ritz_module_1.Span$u8" @"header_content_length"()

declare %"struct.ritz_module_1.Span$u8" @"header_accept"()

declare %"struct.ritz_module_1.Span$u8" @"header_authorization"()

declare %"struct.ritz_module_1.Span$u8" @"header_cookie"()

declare %"struct.ritz_module_1.Span$u8" @"header_set_cookie"()

declare %"struct.ritz_module_1.Span$u8" @"header_location"()

declare %"struct.ritz_module_1.Span$u8" @"header_host"()

declare %"struct.ritz_module_1.Span$u8" @"header_user_agent"()

declare %"struct.ritz_module_1.Span$u8" @"content_type_html"()

declare %"struct.ritz_module_1.Span$u8" @"content_type_json"()

declare %"struct.ritz_module_1.Span$u8" @"content_type_text"()

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

declare %"struct.ritz_module_1.Request" @"request_new"()

declare %"struct.ritz_module_1.Request" @"request_with"(i32 %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare i32 @"request_method"(%"struct.ritz_module_1.Request"* %".1")

declare %"struct.ritz_module_1.Span$u8" @"request_path"(%"struct.ritz_module_1.Request"* %".1")

declare i32 @"request_param"(%"struct.ritz_module_1.Request"* %".1", %"struct.ritz_module_1.Span$u8"* %".2", %"struct.ritz_module_1.Span$u8"* %".3")

declare i32 @"request_query_param"(%"struct.ritz_module_1.Request"* %".1", %"struct.ritz_module_1.Span$u8"* %".2", %"struct.ritz_module_1.Span$u8"* %".3")

declare i32 @"request_header"(%"struct.ritz_module_1.Request"* %".1", %"struct.ritz_module_1.Span$u8"* %".2", %"struct.ritz_module_1.Span$u8"* %".3")

declare %"struct.ritz_module_1.Span$u8" @"request_body_str"(%"struct.ritz_module_1.Request"* %".1")

declare i64 @"request_body_len"(%"struct.ritz_module_1.Request"* %".1")

declare i32 @"request_wants_json"(%"struct.ritz_module_1.Request"* %".1")

declare i32 @"request_wants_html"(%"struct.ritz_module_1.Request"* %".1")

declare i32 @"request_content_type"(%"struct.ritz_module_1.Request"* %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare i32 @"request_is_json"(%"struct.ritz_module_1.Request"* %".1")

declare i32 @"request_is_form"(%"struct.ritz_module_1.Request"* %".1")

declare i32 @"request_set_method"(%"struct.ritz_module_1.Request"* %".1", i32 %".2")

declare i32 @"request_set_path"(%"struct.ritz_module_1.Request"* %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare i32 @"request_set_header"(%"struct.ritz_module_1.Request"* %".1", %"struct.ritz_module_1.Span$u8"* %".2", %"struct.ritz_module_1.Span$u8"* %".3")

declare i32 @"request_set_param"(%"struct.ritz_module_1.Request"* %".1", %"struct.ritz_module_1.Span$u8"* %".2", %"struct.ritz_module_1.Span$u8"* %".3")

declare i32 @"request_set_body"(%"struct.ritz_module_1.Request"* %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare i32 @"span_eq_ci"(%"struct.ritz_module_1.Span$u8"* %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare %"struct.ritz_module_1.Response" @"response_new"()

declare %"struct.ritz_module_1.Response" @"response_with_status"(i32 %".1")

declare %"struct.ritz_module_1.Response" @"response_ok"()

declare %"struct.ritz_module_1.Response" @"response_created"()

declare %"struct.ritz_module_1.Response" @"response_no_content"()

declare %"struct.ritz_module_1.Response" @"response_bad_request"()

declare %"struct.ritz_module_1.Response" @"response_unauthorized"()

declare %"struct.ritz_module_1.Response" @"response_forbidden"()

declare %"struct.ritz_module_1.Response" @"response_not_found"()

declare %"struct.ritz_module_1.Response" @"response_internal_error"()

declare %"struct.ritz_module_1.Response" @"response_html"(%"struct.ritz_module_1.Span$u8"* %".1")

declare %"struct.ritz_module_1.Response" @"response_json_str"(%"struct.ritz_module_1.Span$u8"* %".1")

declare %"struct.ritz_module_1.Response" @"response_text"(%"struct.ritz_module_1.Span$u8"* %".1")

declare %"struct.ritz_module_1.Response" @"response_redirect"(%"struct.ritz_module_1.Span$u8"* %".1")

declare %"struct.ritz_module_1.Response" @"response_redirect_permanent"(%"struct.ritz_module_1.Span$u8"* %".1")

declare i32 @"response_status"(%"struct.ritz_module_1.Response"* %".1")

declare %"struct.ritz_module_1.Span$u8" @"response_body"(%"struct.ritz_module_1.Response"* %".1")

declare i64 @"response_body_len"(%"struct.ritz_module_1.Response"* %".1")

declare i32 @"response_set_status"(%"struct.ritz_module_1.Response"* %".1", i32 %".2")

declare i32 @"response_set_header"(%"struct.ritz_module_1.Response"* %".1", %"struct.ritz_module_1.Span$u8" %".2", %"struct.ritz_module_1.Span$u8" %".3")

declare i32 @"response_set_body"(%"struct.ritz_module_1.Response"* %".1", %"struct.ritz_module_1.Span$u8"* %".2")

declare i64 @"response_header_count"(%"struct.ritz_module_1.Response"* %".1")

declare %"struct.ritz_module_1.Span$u8" @"response_header_name"(%"struct.ritz_module_1.Response"* %".1", i64 %".2")

declare %"struct.ritz_module_1.Span$u8" @"response_header_value"(%"struct.ritz_module_1.Response"* %".1", i64 %".2")

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg") !dbg !23
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !46, metadata !7), !dbg !47
  %".4" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !48
  %".5" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", i32 0, i32 1 , !dbg !48
  %".6" = load i64, i64* %".5", !dbg !48
  %".7" = sub i64 %".6", 1, !dbg !48
  %".8" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !48
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".8", i32 0, i32 1 , !dbg !48
  store i64 %".7", i64* %".9", !dbg !48
  %".11" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !49
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".11", i32 0, i32 0 , !dbg !49
  %".13" = load i8*, i8** %".12", !dbg !49
  %".14" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !49
  %".15" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".14", i32 0, i32 1 , !dbg !49
  %".16" = load i64, i64* %".15", !dbg !49
  %".17" = getelementptr i8, i8* %".13", i64 %".16" , !dbg !49
  %".18" = load i8, i8* %".17", !dbg !49
  ret i8 %".18", !dbg !49
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !24
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !50
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !51, metadata !7), !dbg !52
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !53
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !53
  store i8* null, i8** %".4", !dbg !53
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !54
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !54
  store i64 0, i64* %".7", !dbg !54
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !55
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !55
  store i64 0, i64* %".10", !dbg !55
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !56
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !56
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !25
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !60, metadata !7), !dbg !61
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !63, metadata !7), !dbg !61
  %".7" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !64
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".7", i32 0, i32 1 , !dbg !64
  %".9" = load i64, i64* %".8", !dbg !64
  %".10" = add i64 %".9", 1, !dbg !64
  %".11" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %".10"), !dbg !64
  %".12" = sext i32 %".11" to i64 , !dbg !64
  %".13" = icmp ne i64 %".12", 0 , !dbg !64
  br i1 %".13", label %"if.then", label %"if.end", !dbg !64
if.then:
  %".15" = sub i64 0, 1, !dbg !65
  %".16" = trunc i64 %".15" to i32 , !dbg !65
  ret i32 %".16", !dbg !65
if.end:
  %".18" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !66
  %".19" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !66
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".19", i32 0, i32 0 , !dbg !66
  %".21" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".20", !dbg !66
  %".22" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !66
  %".23" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".22", i32 0, i32 1 , !dbg !66
  %".24" = load i64, i64* %".23", !dbg !66
  %".25" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".21", i64 %".24" , !dbg !66
  store %"struct.ritz_module_1.LineBounds" %".18", %"struct.ritz_module_1.LineBounds"* %".25", !dbg !66
  %".27" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !67
  %".28" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".27", i32 0, i32 1 , !dbg !67
  %".29" = load i64, i64* %".28", !dbg !67
  %".30" = add i64 %".29", 1, !dbg !67
  %".31" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !67
  %".32" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".31", i32 0, i32 1 , !dbg !67
  store i64 %".30", i64* %".32", !dbg !67
  %".34" = trunc i64 0 to i32 , !dbg !68
  ret i32 %".34", !dbg !68
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"needed.arg") !dbg !26
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !74
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !69, metadata !7), !dbg !70
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !71, metadata !7), !dbg !70
  %".7" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !72
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", i32 0, i32 2 , !dbg !72
  %".9" = load i64, i64* %".8", !dbg !72
  %".10" = load i64, i64* %"needed", !dbg !72
  %".11" = icmp sge i64 %".9", %".10" , !dbg !72
  br i1 %".11", label %"if.then", label %"if.end", !dbg !72
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !73
  ret i32 %".13", !dbg !73
if.end:
  %".15" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !74
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".15", i32 0, i32 2 , !dbg !74
  %".17" = load i64, i64* %".16", !dbg !74
  store i64 %".17", i64* %"new_cap.addr", !dbg !74
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !75, metadata !7), !dbg !76
  %".20" = load i64, i64* %"new_cap.addr", !dbg !77
  %".21" = icmp eq i64 %".20", 0 , !dbg !77
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !77
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !78
  br label %"if.end.1", !dbg !78
if.end.1:
  br label %"while.cond", !dbg !79
while.cond:
  %".26" = load i64, i64* %"new_cap.addr", !dbg !79
  %".27" = load i64, i64* %"needed", !dbg !79
  %".28" = icmp slt i64 %".26", %".27" , !dbg !79
  br i1 %".28", label %"while.body", label %"while.end", !dbg !79
while.body:
  %".30" = load i64, i64* %"new_cap.addr", !dbg !80
  %".31" = mul i64 %".30", 2, !dbg !80
  store i64 %".31", i64* %"new_cap.addr", !dbg !80
  br label %"while.cond", !dbg !80
while.end:
  %".34" = load i64, i64* %"new_cap.addr", !dbg !81
  %".35" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %".34"), !dbg !81
  ret i32 %".35", !dbg !81
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !27
{
entry:
  %"i" = alloca i64, !dbg !87
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !82, metadata !7), !dbg !83
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !85, metadata !7), !dbg !83
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !86, metadata !7), !dbg !83
  %".10" = load i64, i64* %"len", !dbg !87
  store i64 0, i64* %"i", !dbg !87
  br label %"for.cond", !dbg !87
for.cond:
  %".13" = load i64, i64* %"i", !dbg !87
  %".14" = icmp slt i64 %".13", %".10" , !dbg !87
  br i1 %".14", label %"for.body", label %"for.end", !dbg !87
for.body:
  %".16" = load i8*, i8** %"data", !dbg !87
  %".17" = load i64, i64* %"i", !dbg !87
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !87
  %".19" = load i8, i8* %".18", !dbg !87
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8 %".19"), !dbg !87
  %".21" = sext i32 %".20" to i64 , !dbg !87
  %".22" = icmp ne i64 %".21", 0 , !dbg !87
  br i1 %".22", label %"if.then", label %"if.end", !dbg !87
for.incr:
  %".28" = load i64, i64* %"i", !dbg !88
  %".29" = add i64 %".28", 1, !dbg !88
  store i64 %".29", i64* %"i", !dbg !88
  br label %"for.cond", !dbg !88
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !89
  ret i32 %".32", !dbg !89
if.then:
  %".24" = sub i64 0, 1, !dbg !88
  %".25" = trunc i64 %".24" to i32 , !dbg !88
  ret i32 %".25", !dbg !88
if.end:
  br label %"for.incr", !dbg !88
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !28
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !90, metadata !7), !dbg !91
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !92, metadata !7), !dbg !91
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !93
  %".8" = load i8*, i8** %".7", !dbg !93
  %".9" = load i64, i64* %"idx", !dbg !93
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !93
  %".11" = load i8, i8* %".10", !dbg !93
  ret i8 %".11", !dbg !93
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg") !dbg !29
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !94, metadata !7), !dbg !95
  %".4" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !96
  %".5" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", i32 0, i32 0 , !dbg !96
  %".6" = load i8*, i8** %".5", !dbg !96
  %".7" = icmp ne i8* %".6", null , !dbg !96
  br i1 %".7", label %"if.then", label %"if.end", !dbg !96
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !96
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".9", i32 0, i32 0 , !dbg !96
  %".11" = load i8*, i8** %".10", !dbg !96
  %".12" = call i32 @"free"(i8* %".11"), !dbg !96
  br label %"if.end", !dbg !96
if.end:
  %".14" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !97
  %".15" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".14", i32 0, i32 0 , !dbg !97
  store i8* null, i8** %".15", !dbg !97
  %".17" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !98
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".17", i32 0, i32 1 , !dbg !98
  store i64 0, i64* %".18", !dbg !98
  %".20" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !99
  %".21" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".20", i32 0, i32 2 , !dbg !99
  store i64 0, i64* %".21", !dbg !99
  ret i32 0, !dbg !99
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !30
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !102
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !100, metadata !7), !dbg !101
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !103, metadata !7), !dbg !104
  %".6" = load i64, i64* %"cap", !dbg !105
  %".7" = icmp sle i64 %".6", 0 , !dbg !105
  br i1 %".7", label %"if.then", label %"if.end", !dbg !105
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !106
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !106
  store i8* null, i8** %".10", !dbg !106
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !107
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !107
  store i64 0, i64* %".13", !dbg !107
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !108
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !108
  store i64 0, i64* %".16", !dbg !108
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !109
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !109
if.end:
  %".20" = load i64, i64* %"cap", !dbg !110
  %".21" = mul i64 %".20", 1, !dbg !110
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !111
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !111
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !111
  store i8* %".22", i8** %".24", !dbg !111
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !112
  %".27" = load i8*, i8** %".26", !dbg !112
  %".28" = icmp eq i8* %".27", null , !dbg !112
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !112
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !113
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !113
  store i64 0, i64* %".31", !dbg !113
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !114
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !114
  store i64 0, i64* %".34", !dbg !114
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !115
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !115
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !116
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !116
  store i64 0, i64* %".39", !dbg !116
  %".41" = load i64, i64* %"cap", !dbg !117
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !117
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !117
  store i64 %".41", i64* %".43", !dbg !117
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !118
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !118
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg") !dbg !31
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !119, metadata !7), !dbg !120
  %".4" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !121
  %".5" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", i32 0, i32 1 , !dbg !121
  store i64 0, i64* %".5", !dbg !121
  ret i32 0, !dbg !121
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8 %"item.arg") !dbg !32
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !122, metadata !7), !dbg !123
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !124, metadata !7), !dbg !123
  %".7" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !125
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", i32 0, i32 1 , !dbg !125
  %".9" = load i64, i64* %".8", !dbg !125
  %".10" = add i64 %".9", 1, !dbg !125
  %".11" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %".10"), !dbg !125
  %".12" = sext i32 %".11" to i64 , !dbg !125
  %".13" = icmp ne i64 %".12", 0 , !dbg !125
  br i1 %".13", label %"if.then", label %"if.end", !dbg !125
if.then:
  %".15" = sub i64 0, 1, !dbg !126
  %".16" = trunc i64 %".15" to i32 , !dbg !126
  ret i32 %".16", !dbg !126
if.end:
  %".18" = load i8, i8* %"item", !dbg !127
  %".19" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !127
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".19", i32 0, i32 0 , !dbg !127
  %".21" = load i8*, i8** %".20", !dbg !127
  %".22" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !127
  %".23" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".22", i32 0, i32 1 , !dbg !127
  %".24" = load i64, i64* %".23", !dbg !127
  %".25" = getelementptr i8, i8* %".21", i64 %".24" , !dbg !127
  store i8 %".18", i8* %".25", !dbg !127
  %".27" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !128
  %".28" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".27", i32 0, i32 1 , !dbg !128
  %".29" = load i64, i64* %".28", !dbg !128
  %".30" = add i64 %".29", 1, !dbg !128
  %".31" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !128
  %".32" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".31", i32 0, i32 1 , !dbg !128
  store i64 %".30", i64* %".32", !dbg !128
  %".34" = trunc i64 0 to i32 , !dbg !129
  ret i32 %".34", !dbg !129
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !33
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !130, metadata !7), !dbg !131
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !132, metadata !7), !dbg !131
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !133, metadata !7), !dbg !131
  %".10" = load i8, i8* %"item", !dbg !134
  %".11" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !134
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".11", i32 0, i32 0 , !dbg !134
  %".13" = load i8*, i8** %".12", !dbg !134
  %".14" = load i64, i64* %"idx", !dbg !134
  %".15" = getelementptr i8, i8* %".13", i64 %".14" , !dbg !134
  store i8 %".10", i8* %".15", !dbg !134
  %".17" = trunc i64 0 to i32 , !dbg !135
  ret i32 %".17", !dbg !135
}

define linkonce_odr i8 @"span_get$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg", i64 %"idx.arg") !dbg !34
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !138, metadata !7), !dbg !139
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !140, metadata !7), !dbg !139
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !141
  %".9" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".8", i32 0, i32 0 , !dbg !141
  %".10" = load i8*, i8** %".9", !dbg !141
  %".11" = load i64, i64* %"idx", !dbg !141
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !141
  %".13" = load i8, i8* %".12", !dbg !141
  ret i8 %".13", !dbg !141
}

define linkonce_odr %"struct.ritz_module_1.Span$u8" @"span_slice$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg", i64 %"start.arg", i64 %"end.arg") !dbg !35
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  %"result.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !146
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !142, metadata !7), !dbg !143
  %"start" = alloca i64
  store i64 %"start.arg", i64* %"start"
  call void @"llvm.dbg.declare"(metadata i64* %"start", metadata !144, metadata !7), !dbg !143
  %"end" = alloca i64
  store i64 %"end.arg", i64* %"end"
  call void @"llvm.dbg.declare"(metadata i64* %"end", metadata !145, metadata !7), !dbg !143
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"result.addr", metadata !147, metadata !7), !dbg !148
  %".12" = load i64, i64* %"start", !dbg !149
  %".13" = icmp slt i64 %".12", 0 , !dbg !149
  br i1 %".13", label %"if.then", label %"if.end", !dbg !149
if.then:
  store i64 0, i64* %"start", !dbg !150
  br label %"if.end", !dbg !150
if.end:
  %".17" = load i64, i64* %"end", !dbg !151
  %".18" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !151
  %".19" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".18", i32 0, i32 1 , !dbg !151
  %".20" = load i64, i64* %".19", !dbg !151
  %".21" = icmp sgt i64 %".17", %".20" , !dbg !151
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !151
if.then.1:
  %".23" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !152
  %".24" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".23", i32 0, i32 1 , !dbg !152
  %".25" = load i64, i64* %".24", !dbg !152
  store i64 %".25", i64* %"end", !dbg !152
  br label %"if.end.1", !dbg !152
if.end.1:
  %".28" = load i64, i64* %"start", !dbg !153
  %".29" = load i64, i64* %"end", !dbg !153
  %".30" = icmp sge i64 %".28", %".29" , !dbg !153
  br i1 %".30", label %"if.then.2", label %"if.end.2", !dbg !153
if.then.2:
  %".32" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !154
  %".33" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 0 , !dbg !154
  store i8* null, i8** %".33", !dbg !154
  %".35" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !155
  %".36" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 1 , !dbg !155
  store i64 0, i64* %".36", !dbg !155
  %".38" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !156
  ret %"struct.ritz_module_1.Span$u8" %".38", !dbg !156
if.end.2:
  %".40" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !157
  %".41" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".40", i32 0, i32 0 , !dbg !157
  %".42" = load i8*, i8** %".41", !dbg !157
  %".43" = load i64, i64* %"start", !dbg !157
  %".44" = getelementptr i8, i8* %".42", i64 %".43" , !dbg !157
  %".45" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !157
  %".46" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 0 , !dbg !157
  store i8* %".44", i8** %".46", !dbg !157
  %".48" = load i64, i64* %"end", !dbg !158
  %".49" = load i64, i64* %"start", !dbg !158
  %".50" = sub i64 %".48", %".49", !dbg !158
  %".51" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !158
  %".52" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 1 , !dbg !158
  store i64 %".50", i64* %".52", !dbg !158
  %".54" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !159
  ret %"struct.ritz_module_1.Span$u8" %".54", !dbg !159
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"new_cap.arg") !dbg !36
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !160, metadata !7), !dbg !161
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !162, metadata !7), !dbg !161
  %".7" = load i64, i64* %"new_cap", !dbg !163
  %".8" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !163
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".8", i32 0, i32 2 , !dbg !163
  %".10" = load i64, i64* %".9", !dbg !163
  %".11" = icmp sle i64 %".7", %".10" , !dbg !163
  br i1 %".11", label %"if.then", label %"if.end", !dbg !163
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !164
  ret i32 %".13", !dbg !164
if.end:
  %".15" = load i64, i64* %"new_cap", !dbg !165
  %".16" = mul i64 %".15", 1, !dbg !165
  %".17" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !166
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".17", i32 0, i32 0 , !dbg !166
  %".19" = load i8*, i8** %".18", !dbg !166
  %".20" = call i8* @"realloc"(i8* %".19", i64 %".16"), !dbg !166
  %".21" = icmp eq i8* %".20", null , !dbg !167
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !167
if.then.1:
  %".23" = sub i64 0, 1, !dbg !168
  %".24" = trunc i64 %".23" to i32 , !dbg !168
  ret i32 %".24", !dbg !168
if.end.1:
  %".26" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !169
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".26", i32 0, i32 0 , !dbg !169
  store i8* %".20", i8** %".27", !dbg !169
  %".29" = load i64, i64* %"new_cap", !dbg !170
  %".30" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !170
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".30", i32 0, i32 2 , !dbg !170
  store i64 %".29", i64* %".31", !dbg !170
  %".33" = trunc i64 0 to i32 , !dbg !171
  ret i32 %".33", !dbg !171
}

define linkonce_odr i32 @"span_is_empty$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg") !dbg !37
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !172, metadata !7), !dbg !173
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !174
  %".6" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".5", i32 0, i32 1 , !dbg !174
  %".7" = load i64, i64* %".6", !dbg !174
  %".8" = icmp eq i64 %".7", 0 , !dbg !174
  br i1 %".8", label %"if.then", label %"if.end", !dbg !174
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !175
  ret i32 %".10", !dbg !175
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !176
  ret i32 %".12", !dbg !176
}

define linkonce_odr i8* @"span_as_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg") !dbg !38
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !177, metadata !7), !dbg !178
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !179
  %".6" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".5", i32 0, i32 0 , !dbg !179
  %".7" = load i8*, i8** %".6", !dbg !179
  ret i8* %".7", !dbg !179
}

define linkonce_odr i8* @"span_get_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg", i64 %"idx.arg") !dbg !39
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !180, metadata !7), !dbg !181
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !182, metadata !7), !dbg !181
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !183
  %".9" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".8", i32 0, i32 0 , !dbg !183
  %".10" = load i8*, i8** %".9", !dbg !183
  %".11" = load i64, i64* %"idx", !dbg !183
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !183
  ret i8* %".12", !dbg !183
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %"needed.arg") !dbg !40
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !189
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !184, metadata !7), !dbg !185
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !186, metadata !7), !dbg !185
  %".7" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !187
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".7", i32 0, i32 2 , !dbg !187
  %".9" = load i64, i64* %".8", !dbg !187
  %".10" = load i64, i64* %"needed", !dbg !187
  %".11" = icmp sge i64 %".9", %".10" , !dbg !187
  br i1 %".11", label %"if.then", label %"if.end", !dbg !187
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !188
  ret i32 %".13", !dbg !188
if.end:
  %".15" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !189
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".15", i32 0, i32 2 , !dbg !189
  %".17" = load i64, i64* %".16", !dbg !189
  store i64 %".17", i64* %"new_cap.addr", !dbg !189
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !190, metadata !7), !dbg !191
  %".20" = load i64, i64* %"new_cap.addr", !dbg !192
  %".21" = icmp eq i64 %".20", 0 , !dbg !192
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !192
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !193
  br label %"if.end.1", !dbg !193
if.end.1:
  br label %"while.cond", !dbg !194
while.cond:
  %".26" = load i64, i64* %"new_cap.addr", !dbg !194
  %".27" = load i64, i64* %"needed", !dbg !194
  %".28" = icmp slt i64 %".26", %".27" , !dbg !194
  br i1 %".28", label %"while.body", label %"while.end", !dbg !194
while.body:
  %".30" = load i64, i64* %"new_cap.addr", !dbg !195
  %".31" = mul i64 %".30", 2, !dbg !195
  store i64 %".31", i64* %"new_cap.addr", !dbg !195
  br label %"while.cond", !dbg !195
while.end:
  %".34" = load i64, i64* %"new_cap.addr", !dbg !196
  %".35" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %".34"), !dbg !196
  ret i32 %".35", !dbg !196
}

define linkonce_odr i64 @"span_len$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg") !dbg !41
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !197, metadata !7), !dbg !198
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !199
  %".6" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".5", i32 0, i32 1 , !dbg !199
  %".7" = load i64, i64* %".6", !dbg !199
  ret i64 %".7", !dbg !199
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %"new_cap.arg") !dbg !42
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !200, metadata !7), !dbg !201
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !202, metadata !7), !dbg !201
  %".7" = load i64, i64* %"new_cap", !dbg !203
  %".8" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !203
  %".9" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".8", i32 0, i32 2 , !dbg !203
  %".10" = load i64, i64* %".9", !dbg !203
  %".11" = icmp sle i64 %".7", %".10" , !dbg !203
  br i1 %".11", label %"if.then", label %"if.end", !dbg !203
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !204
  ret i32 %".13", !dbg !204
if.end:
  %".15" = load i64, i64* %"new_cap", !dbg !205
  %".16" = mul i64 %".15", 16, !dbg !205
  %".17" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !206
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".17", i32 0, i32 0 , !dbg !206
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !206
  %".20" = bitcast %"struct.ritz_module_1.LineBounds"* %".19" to i8* , !dbg !206
  %".21" = call i8* @"realloc"(i8* %".20", i64 %".16"), !dbg !206
  %".22" = icmp eq i8* %".21", null , !dbg !207
  br i1 %".22", label %"if.then.1", label %"if.end.1", !dbg !207
if.then.1:
  %".24" = sub i64 0, 1, !dbg !208
  %".25" = trunc i64 %".24" to i32 , !dbg !208
  ret i32 %".25", !dbg !208
if.end.1:
  %".27" = bitcast i8* %".21" to %"struct.ritz_module_1.LineBounds"* , !dbg !209
  %".28" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !209
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".28", i32 0, i32 0 , !dbg !209
  store %"struct.ritz_module_1.LineBounds"* %".27", %"struct.ritz_module_1.LineBounds"** %".29", !dbg !209
  %".31" = load i64, i64* %"new_cap", !dbg !210
  %".32" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !210
  %".33" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".32", i32 0, i32 2 , !dbg !210
  store i64 %".31", i64* %".33", !dbg !210
  %".35" = trunc i64 0 to i32 , !dbg !211
  ret i32 %".35", !dbg !211
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/spire/lib/http", filename: "mod.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 208, name: "Span$u8_len", scopeLine: 208, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 211, name: "Span$u8_is_empty", scopeLine: 211, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 214, name: "Span$u8_get", scopeLine: 214, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 217, name: "Span$u8_get_ptr", scopeLine: 217, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 220, name: "Span$u8_as_ptr", scopeLine: 220, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 223, name: "Span$u8_slice", scopeLine: 223, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 89, name: "span_get$u8", scopeLine: 89, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 105, name: "span_slice$u8", scopeLine: 105, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 83, name: "span_is_empty$u8", scopeLine: 83, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 97, name: "span_as_ptr$u8", scopeLine: 97, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 93, name: "span_get_ptr$u8", scopeLine: 93, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 79, name: "span_len$u8", scopeLine: 79, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!43 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!44 = !DIDerivedType(baseType: !43, size: 64, tag: DW_TAG_reference_type)
!45 = !DIDerivedType(baseType: !44, size: 64, tag: DW_TAG_reference_type)
!46 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !23, type: !45)
!47 = !DILocation(column: 1, line: 219, scope: !23)
!48 = !DILocation(column: 5, line: 220, scope: !23)
!49 = !DILocation(column: 5, line: 221, scope: !23)
!50 = !DILocation(column: 5, line: 117, scope: !24)
!51 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !24, type: !43)
!52 = !DILocation(column: 1, line: 117, scope: !24)
!53 = !DILocation(column: 5, line: 118, scope: !24)
!54 = !DILocation(column: 5, line: 119, scope: !24)
!55 = !DILocation(column: 5, line: 120, scope: !24)
!56 = !DILocation(column: 5, line: 121, scope: !24)
!57 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!58 = !DIDerivedType(baseType: !57, size: 64, tag: DW_TAG_reference_type)
!59 = !DIDerivedType(baseType: !58, size: 64, tag: DW_TAG_reference_type)
!60 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !25, type: !59)
!61 = !DILocation(column: 1, line: 210, scope: !25)
!62 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!63 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !25, type: !62)
!64 = !DILocation(column: 5, line: 211, scope: !25)
!65 = !DILocation(column: 9, line: 212, scope: !25)
!66 = !DILocation(column: 5, line: 213, scope: !25)
!67 = !DILocation(column: 5, line: 214, scope: !25)
!68 = !DILocation(column: 5, line: 215, scope: !25)
!69 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !26, type: !45)
!70 = !DILocation(column: 1, line: 193, scope: !26)
!71 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !26, type: !11)
!72 = !DILocation(column: 5, line: 194, scope: !26)
!73 = !DILocation(column: 9, line: 195, scope: !26)
!74 = !DILocation(column: 5, line: 197, scope: !26)
!75 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !26, type: !11)
!76 = !DILocation(column: 1, line: 197, scope: !26)
!77 = !DILocation(column: 5, line: 198, scope: !26)
!78 = !DILocation(column: 9, line: 199, scope: !26)
!79 = !DILocation(column: 5, line: 200, scope: !26)
!80 = !DILocation(column: 9, line: 201, scope: !26)
!81 = !DILocation(column: 5, line: 203, scope: !26)
!82 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !27, type: !45)
!83 = !DILocation(column: 1, line: 288, scope: !27)
!84 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!85 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !27, type: !84)
!86 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !27, type: !11)
!87 = !DILocation(column: 5, line: 289, scope: !27)
!88 = !DILocation(column: 13, line: 291, scope: !27)
!89 = !DILocation(column: 5, line: 292, scope: !27)
!90 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !28, type: !44)
!91 = !DILocation(column: 1, line: 225, scope: !28)
!92 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !28, type: !11)
!93 = !DILocation(column: 5, line: 226, scope: !28)
!94 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !29, type: !45)
!95 = !DILocation(column: 1, line: 148, scope: !29)
!96 = !DILocation(column: 5, line: 149, scope: !29)
!97 = !DILocation(column: 5, line: 151, scope: !29)
!98 = !DILocation(column: 5, line: 152, scope: !29)
!99 = !DILocation(column: 5, line: 153, scope: !29)
!100 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !30, type: !11)
!101 = !DILocation(column: 1, line: 124, scope: !30)
!102 = !DILocation(column: 5, line: 125, scope: !30)
!103 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !30, type: !43)
!104 = !DILocation(column: 1, line: 125, scope: !30)
!105 = !DILocation(column: 5, line: 126, scope: !30)
!106 = !DILocation(column: 9, line: 127, scope: !30)
!107 = !DILocation(column: 9, line: 128, scope: !30)
!108 = !DILocation(column: 9, line: 129, scope: !30)
!109 = !DILocation(column: 9, line: 130, scope: !30)
!110 = !DILocation(column: 5, line: 132, scope: !30)
!111 = !DILocation(column: 5, line: 133, scope: !30)
!112 = !DILocation(column: 5, line: 134, scope: !30)
!113 = !DILocation(column: 9, line: 135, scope: !30)
!114 = !DILocation(column: 9, line: 136, scope: !30)
!115 = !DILocation(column: 9, line: 137, scope: !30)
!116 = !DILocation(column: 5, line: 139, scope: !30)
!117 = !DILocation(column: 5, line: 140, scope: !30)
!118 = !DILocation(column: 5, line: 141, scope: !30)
!119 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !31, type: !45)
!120 = !DILocation(column: 1, line: 244, scope: !31)
!121 = !DILocation(column: 5, line: 245, scope: !31)
!122 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !32, type: !45)
!123 = !DILocation(column: 1, line: 210, scope: !32)
!124 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !32, type: !12)
!125 = !DILocation(column: 5, line: 211, scope: !32)
!126 = !DILocation(column: 9, line: 212, scope: !32)
!127 = !DILocation(column: 5, line: 213, scope: !32)
!128 = !DILocation(column: 5, line: 214, scope: !32)
!129 = !DILocation(column: 5, line: 215, scope: !32)
!130 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !33, type: !45)
!131 = !DILocation(column: 1, line: 235, scope: !33)
!132 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !33, type: !11)
!133 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !33, type: !12)
!134 = !DILocation(column: 5, line: 236, scope: !33)
!135 = !DILocation(column: 5, line: 237, scope: !33)
!136 = !DICompositeType(align: 64, file: !0, name: "Span$u8", size: 128, tag: DW_TAG_structure_type)
!137 = !DIDerivedType(baseType: !136, size: 64, tag: DW_TAG_pointer_type)
!138 = !DILocalVariable(file: !0, line: 89, name: "s", scope: !34, type: !137)
!139 = !DILocation(column: 1, line: 89, scope: !34)
!140 = !DILocalVariable(file: !0, line: 89, name: "idx", scope: !34, type: !11)
!141 = !DILocation(column: 5, line: 90, scope: !34)
!142 = !DILocalVariable(file: !0, line: 105, name: "s", scope: !35, type: !137)
!143 = !DILocation(column: 1, line: 105, scope: !35)
!144 = !DILocalVariable(file: !0, line: 105, name: "start", scope: !35, type: !11)
!145 = !DILocalVariable(file: !0, line: 105, name: "end", scope: !35, type: !11)
!146 = !DILocation(column: 5, line: 106, scope: !35)
!147 = !DILocalVariable(file: !0, line: 106, name: "result", scope: !35, type: !136)
!148 = !DILocation(column: 1, line: 106, scope: !35)
!149 = !DILocation(column: 5, line: 107, scope: !35)
!150 = !DILocation(column: 9, line: 108, scope: !35)
!151 = !DILocation(column: 5, line: 109, scope: !35)
!152 = !DILocation(column: 9, line: 110, scope: !35)
!153 = !DILocation(column: 5, line: 111, scope: !35)
!154 = !DILocation(column: 9, line: 112, scope: !35)
!155 = !DILocation(column: 9, line: 113, scope: !35)
!156 = !DILocation(column: 9, line: 114, scope: !35)
!157 = !DILocation(column: 5, line: 115, scope: !35)
!158 = !DILocation(column: 5, line: 116, scope: !35)
!159 = !DILocation(column: 5, line: 117, scope: !35)
!160 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !36, type: !45)
!161 = !DILocation(column: 1, line: 179, scope: !36)
!162 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !36, type: !11)
!163 = !DILocation(column: 5, line: 180, scope: !36)
!164 = !DILocation(column: 9, line: 181, scope: !36)
!165 = !DILocation(column: 5, line: 183, scope: !36)
!166 = !DILocation(column: 5, line: 184, scope: !36)
!167 = !DILocation(column: 5, line: 185, scope: !36)
!168 = !DILocation(column: 9, line: 186, scope: !36)
!169 = !DILocation(column: 5, line: 188, scope: !36)
!170 = !DILocation(column: 5, line: 189, scope: !36)
!171 = !DILocation(column: 5, line: 190, scope: !36)
!172 = !DILocalVariable(file: !0, line: 83, name: "s", scope: !37, type: !137)
!173 = !DILocation(column: 1, line: 83, scope: !37)
!174 = !DILocation(column: 5, line: 84, scope: !37)
!175 = !DILocation(column: 9, line: 85, scope: !37)
!176 = !DILocation(column: 5, line: 86, scope: !37)
!177 = !DILocalVariable(file: !0, line: 97, name: "s", scope: !38, type: !137)
!178 = !DILocation(column: 1, line: 97, scope: !38)
!179 = !DILocation(column: 5, line: 98, scope: !38)
!180 = !DILocalVariable(file: !0, line: 93, name: "s", scope: !39, type: !137)
!181 = !DILocation(column: 1, line: 93, scope: !39)
!182 = !DILocalVariable(file: !0, line: 93, name: "idx", scope: !39, type: !11)
!183 = !DILocation(column: 5, line: 94, scope: !39)
!184 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !40, type: !59)
!185 = !DILocation(column: 1, line: 193, scope: !40)
!186 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !40, type: !11)
!187 = !DILocation(column: 5, line: 194, scope: !40)
!188 = !DILocation(column: 9, line: 195, scope: !40)
!189 = !DILocation(column: 5, line: 197, scope: !40)
!190 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !40, type: !11)
!191 = !DILocation(column: 1, line: 197, scope: !40)
!192 = !DILocation(column: 5, line: 198, scope: !40)
!193 = !DILocation(column: 9, line: 199, scope: !40)
!194 = !DILocation(column: 5, line: 200, scope: !40)
!195 = !DILocation(column: 9, line: 201, scope: !40)
!196 = !DILocation(column: 5, line: 203, scope: !40)
!197 = !DILocalVariable(file: !0, line: 79, name: "s", scope: !41, type: !137)
!198 = !DILocation(column: 1, line: 79, scope: !41)
!199 = !DILocation(column: 5, line: 80, scope: !41)
!200 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !42, type: !59)
!201 = !DILocation(column: 1, line: 179, scope: !42)
!202 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !42, type: !11)
!203 = !DILocation(column: 5, line: 180, scope: !42)
!204 = !DILocation(column: 9, line: 181, scope: !42)
!205 = !DILocation(column: 5, line: 183, scope: !42)
!206 = !DILocation(column: 5, line: 184, scope: !42)
!207 = !DILocation(column: 5, line: 185, scope: !42)
!208 = !DILocation(column: 9, line: 186, scope: !42)
!209 = !DILocation(column: 5, line: 188, scope: !42)
!210 = !DILocation(column: 5, line: 189, scope: !42)
!211 = !DILocation(column: 5, line: 190, scope: !42)
!212 = !DILocalVariable(file: !0, line: 208, name: "self", scope: !17, type: !137)
!213 = !DILocation(column: 1, line: 208, scope: !17)
!214 = !DILocation(column: 9, line: 209, scope: !17)
!215 = !DILocalVariable(file: !0, line: 211, name: "self", scope: !18, type: !137)
!216 = !DILocation(column: 1, line: 211, scope: !18)
!217 = !DILocation(column: 9, line: 212, scope: !18)
!218 = !DILocalVariable(file: !0, line: 214, name: "self", scope: !19, type: !137)
!219 = !DILocation(column: 1, line: 214, scope: !19)
!220 = !DILocalVariable(file: !0, line: 214, name: "idx", scope: !19, type: !11)
!221 = !DILocation(column: 9, line: 215, scope: !19)
!222 = !DILocalVariable(file: !0, line: 217, name: "self", scope: !20, type: !137)
!223 = !DILocation(column: 1, line: 217, scope: !20)
!224 = !DILocalVariable(file: !0, line: 217, name: "idx", scope: !20, type: !11)
!225 = !DILocation(column: 9, line: 218, scope: !20)
!226 = !DILocalVariable(file: !0, line: 220, name: "self", scope: !21, type: !137)
!227 = !DILocation(column: 1, line: 220, scope: !21)
!228 = !DILocation(column: 9, line: 221, scope: !21)
!229 = !DILocalVariable(file: !0, line: 223, name: "self", scope: !22, type: !137)
!230 = !DILocation(column: 1, line: 223, scope: !22)
!231 = !DILocalVariable(file: !0, line: 223, name: "start", scope: !22, type: !11)
!232 = !DILocalVariable(file: !0, line: 223, name: "end", scope: !22, type: !11)
!233 = !DILocation(column: 9, line: 224, scope: !22)