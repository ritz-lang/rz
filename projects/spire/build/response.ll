; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Vec$LineBounds" = type {%"struct.ritz_module_1.LineBounds"*, i64, i64}
%"struct.ritz_module_1.Span$u8" = type {i8*, i64}
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
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !319, metadata !7), !dbg !320
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !321
  %".6" = call i64 @"span_len$u8"(%"struct.ritz_module_1.Span$u8"* %".5"), !dbg !321
  ret i64 %".6", !dbg !321
}

define linkonce_odr i32 @"Span$u8_is_empty"(%"struct.ritz_module_1.Span$u8"* %"self.arg") !dbg !18
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !322, metadata !7), !dbg !323
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !324
  %".6" = call i32 @"span_is_empty$u8"(%"struct.ritz_module_1.Span$u8"* %".5"), !dbg !324
  ret i32 %".6", !dbg !324
}

define linkonce_odr i8 @"Span$u8_get"(%"struct.ritz_module_1.Span$u8"* %"self.arg", i64 %"idx.arg") !dbg !19
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !325, metadata !7), !dbg !326
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !327, metadata !7), !dbg !326
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !328
  %".9" = load i64, i64* %"idx", !dbg !328
  %".10" = call i8 @"span_get$u8"(%"struct.ritz_module_1.Span$u8"* %".8", i64 %".9"), !dbg !328
  ret i8 %".10", !dbg !328
}

define linkonce_odr i8* @"Span$u8_get_ptr"(%"struct.ritz_module_1.Span$u8"* %"self.arg", i64 %"idx.arg") !dbg !20
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !329, metadata !7), !dbg !330
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !331, metadata !7), !dbg !330
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !332
  %".9" = load i64, i64* %"idx", !dbg !332
  %".10" = call i8* @"span_get_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %".8", i64 %".9"), !dbg !332
  ret i8* %".10", !dbg !332
}

define linkonce_odr i8* @"Span$u8_as_ptr"(%"struct.ritz_module_1.Span$u8"* %"self.arg") !dbg !21
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !333, metadata !7), !dbg !334
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !335
  %".6" = call i8* @"span_as_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %".5"), !dbg !335
  ret i8* %".6", !dbg !335
}

define linkonce_odr %"struct.ritz_module_1.Span$u8" @"Span$u8_slice"(%"struct.ritz_module_1.Span$u8"* %"self.arg", i64 %"start.arg", i64 %"end.arg") !dbg !22
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !336, metadata !7), !dbg !337
  %"start" = alloca i64
  store i64 %"start.arg", i64* %"start"
  call void @"llvm.dbg.declare"(metadata i64* %"start", metadata !338, metadata !7), !dbg !337
  %"end" = alloca i64
  store i64 %"end.arg", i64* %"end"
  call void @"llvm.dbg.declare"(metadata i64* %"end", metadata !339, metadata !7), !dbg !337
  %".11" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !340
  %".12" = load i64, i64* %"start", !dbg !340
  %".13" = load i64, i64* %"end", !dbg !340
  %".14" = call %"struct.ritz_module_1.Span$u8" @"span_slice$u8"(%"struct.ritz_module_1.Span$u8"* %".11", i64 %".12", i64 %".13"), !dbg !340
  ret %"struct.ritz_module_1.Span$u8" %".14", !dbg !340
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

define %"struct.ritz_module_1.Response" @"response_new"() !dbg !23
{
entry:
  %"res.addr" = alloca %"struct.ritz_module_1.Response", !dbg !60
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"* %"res.addr", metadata !62, metadata !7), !dbg !63
  %".3" = load %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !64
  %".4" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", i32 0, i32 0 , !dbg !64
  store i32 200, i32* %".4", !dbg !64
  %".6" = load %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !65
  %".7" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", i32 0, i32 2 , !dbg !65
  store i64 0, i64* %".7", !dbg !65
  %".9" = load %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !66
  %".10" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", i32 0, i32 4 , !dbg !66
  store i64 0, i64* %".10", !dbg !66
  %".12" = load %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !67
  ret %"struct.ritz_module_1.Response" %".12", !dbg !67
}

define %"struct.ritz_module_1.Response" @"response_with_status"(i32 %"status.arg") !dbg !24
{
entry:
  %"status" = alloca i32
  %"res.addr" = alloca %"struct.ritz_module_1.Response", !dbg !70
  store i32 %"status.arg", i32* %"status"
  call void @"llvm.dbg.declare"(metadata i32* %"status", metadata !68, metadata !7), !dbg !69
  %".5" = call %"struct.ritz_module_1.Response" @"response_new"(), !dbg !70
  store %"struct.ritz_module_1.Response" %".5", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !70
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"* %"res.addr", metadata !71, metadata !7), !dbg !72
  %".8" = load i32, i32* %"status", !dbg !73
  %".9" = load %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !73
  %".10" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", i32 0, i32 0 , !dbg !73
  store i32 %".8", i32* %".10", !dbg !73
  %".12" = load %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !74
  ret %"struct.ritz_module_1.Response" %".12", !dbg !74
}

define %"struct.ritz_module_1.Response" @"response_ok"() !dbg !25
{
entry:
  %".2" = call %"struct.ritz_module_1.Response" @"response_with_status"(i32 200), !dbg !75
  ret %"struct.ritz_module_1.Response" %".2", !dbg !75
}

define %"struct.ritz_module_1.Response" @"response_created"() !dbg !26
{
entry:
  %".2" = call %"struct.ritz_module_1.Response" @"response_with_status"(i32 201), !dbg !76
  ret %"struct.ritz_module_1.Response" %".2", !dbg !76
}

define %"struct.ritz_module_1.Response" @"response_no_content"() !dbg !27
{
entry:
  %".2" = call %"struct.ritz_module_1.Response" @"response_with_status"(i32 204), !dbg !77
  ret %"struct.ritz_module_1.Response" %".2", !dbg !77
}

define %"struct.ritz_module_1.Response" @"response_bad_request"() !dbg !28
{
entry:
  %".2" = call %"struct.ritz_module_1.Response" @"response_with_status"(i32 400), !dbg !78
  ret %"struct.ritz_module_1.Response" %".2", !dbg !78
}

define %"struct.ritz_module_1.Response" @"response_unauthorized"() !dbg !29
{
entry:
  %".2" = call %"struct.ritz_module_1.Response" @"response_with_status"(i32 401), !dbg !79
  ret %"struct.ritz_module_1.Response" %".2", !dbg !79
}

define %"struct.ritz_module_1.Response" @"response_forbidden"() !dbg !30
{
entry:
  %".2" = call %"struct.ritz_module_1.Response" @"response_with_status"(i32 403), !dbg !80
  ret %"struct.ritz_module_1.Response" %".2", !dbg !80
}

define %"struct.ritz_module_1.Response" @"response_not_found"() !dbg !31
{
entry:
  %".2" = call %"struct.ritz_module_1.Response" @"response_with_status"(i32 404), !dbg !81
  ret %"struct.ritz_module_1.Response" %".2", !dbg !81
}

define %"struct.ritz_module_1.Response" @"response_internal_error"() !dbg !32
{
entry:
  %".2" = call %"struct.ritz_module_1.Response" @"response_with_status"(i32 500), !dbg !82
  ret %"struct.ritz_module_1.Response" %".2", !dbg !82
}

define %"struct.ritz_module_1.Response" @"response_html"(%"struct.ritz_module_1.Span$u8"* %"body.arg") !dbg !33
{
entry:
  %"body" = alloca %"struct.ritz_module_1.Span$u8"*
  %"res.addr" = alloca %"struct.ritz_module_1.Response", !dbg !87
  store %"struct.ritz_module_1.Span$u8"* %"body.arg", %"struct.ritz_module_1.Span$u8"** %"body"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"body", metadata !85, metadata !7), !dbg !86
  %".5" = call %"struct.ritz_module_1.Response" @"response_ok"(), !dbg !87
  store %"struct.ritz_module_1.Response" %".5", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !87
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"* %"res.addr", metadata !88, metadata !7), !dbg !89
  %".8" = getelementptr [13 x i8], [13 x i8]* @".str.0", i64 0, i64 0 , !dbg !90
  %".9" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".8"), !dbg !90
  %".10" = getelementptr [25 x i8], [25 x i8]* @".str.1", i64 0, i64 0 , !dbg !90
  %".11" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".10"), !dbg !90
  %".12" = call i32 @"response_set_header"(%"struct.ritz_module_1.Response"* %"res.addr", %"struct.ritz_module_1.Span$u8" %".9", %"struct.ritz_module_1.Span$u8" %".11"), !dbg !90
  %".13" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"body", !dbg !91
  %".14" = call i32 @"response_set_body"(%"struct.ritz_module_1.Response"* %"res.addr", %"struct.ritz_module_1.Span$u8"* %".13"), !dbg !91
  %".15" = load %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !92
  ret %"struct.ritz_module_1.Response" %".15", !dbg !92
}

define %"struct.ritz_module_1.Response" @"response_json_str"(%"struct.ritz_module_1.Span$u8"* %"body.arg") !dbg !34
{
entry:
  %"body" = alloca %"struct.ritz_module_1.Span$u8"*
  %"res.addr" = alloca %"struct.ritz_module_1.Response", !dbg !95
  store %"struct.ritz_module_1.Span$u8"* %"body.arg", %"struct.ritz_module_1.Span$u8"** %"body"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"body", metadata !93, metadata !7), !dbg !94
  %".5" = call %"struct.ritz_module_1.Response" @"response_ok"(), !dbg !95
  store %"struct.ritz_module_1.Response" %".5", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !95
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"* %"res.addr", metadata !96, metadata !7), !dbg !97
  %".8" = getelementptr [13 x i8], [13 x i8]* @".str.2", i64 0, i64 0 , !dbg !98
  %".9" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".8"), !dbg !98
  %".10" = getelementptr [17 x i8], [17 x i8]* @".str.3", i64 0, i64 0 , !dbg !98
  %".11" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".10"), !dbg !98
  %".12" = call i32 @"response_set_header"(%"struct.ritz_module_1.Response"* %"res.addr", %"struct.ritz_module_1.Span$u8" %".9", %"struct.ritz_module_1.Span$u8" %".11"), !dbg !98
  %".13" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"body", !dbg !99
  %".14" = call i32 @"response_set_body"(%"struct.ritz_module_1.Response"* %"res.addr", %"struct.ritz_module_1.Span$u8"* %".13"), !dbg !99
  %".15" = load %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !100
  ret %"struct.ritz_module_1.Response" %".15", !dbg !100
}

define %"struct.ritz_module_1.Response" @"response_text"(%"struct.ritz_module_1.Span$u8"* %"body.arg") !dbg !35
{
entry:
  %"body" = alloca %"struct.ritz_module_1.Span$u8"*
  %"res.addr" = alloca %"struct.ritz_module_1.Response", !dbg !103
  store %"struct.ritz_module_1.Span$u8"* %"body.arg", %"struct.ritz_module_1.Span$u8"** %"body"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"body", metadata !101, metadata !7), !dbg !102
  %".5" = call %"struct.ritz_module_1.Response" @"response_ok"(), !dbg !103
  store %"struct.ritz_module_1.Response" %".5", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !103
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"* %"res.addr", metadata !104, metadata !7), !dbg !105
  %".8" = getelementptr [13 x i8], [13 x i8]* @".str.4", i64 0, i64 0 , !dbg !106
  %".9" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".8"), !dbg !106
  %".10" = getelementptr [26 x i8], [26 x i8]* @".str.5", i64 0, i64 0 , !dbg !106
  %".11" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".10"), !dbg !106
  %".12" = call i32 @"response_set_header"(%"struct.ritz_module_1.Response"* %"res.addr", %"struct.ritz_module_1.Span$u8" %".9", %"struct.ritz_module_1.Span$u8" %".11"), !dbg !106
  %".13" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"body", !dbg !107
  %".14" = call i32 @"response_set_body"(%"struct.ritz_module_1.Response"* %"res.addr", %"struct.ritz_module_1.Span$u8"* %".13"), !dbg !107
  %".15" = load %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !108
  ret %"struct.ritz_module_1.Response" %".15", !dbg !108
}

define %"struct.ritz_module_1.Response" @"response_redirect"(%"struct.ritz_module_1.Span$u8"* %"location.arg") !dbg !36
{
entry:
  %"location" = alloca %"struct.ritz_module_1.Span$u8"*
  %"res.addr" = alloca %"struct.ritz_module_1.Response", !dbg !111
  store %"struct.ritz_module_1.Span$u8"* %"location.arg", %"struct.ritz_module_1.Span$u8"** %"location"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"location", metadata !109, metadata !7), !dbg !110
  %".5" = call %"struct.ritz_module_1.Response" @"response_with_status"(i32 302), !dbg !111
  store %"struct.ritz_module_1.Response" %".5", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !111
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"* %"res.addr", metadata !112, metadata !7), !dbg !113
  %".8" = getelementptr [9 x i8], [9 x i8]* @".str.6", i64 0, i64 0 , !dbg !114
  %".9" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".8"), !dbg !114
  %".10" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"location", !dbg !114
  %".11" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".10", !dbg !114
  %".12" = call i32 @"response_set_header"(%"struct.ritz_module_1.Response"* %"res.addr", %"struct.ritz_module_1.Span$u8" %".9", %"struct.ritz_module_1.Span$u8" %".11"), !dbg !114
  %".13" = load %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !115
  ret %"struct.ritz_module_1.Response" %".13", !dbg !115
}

define %"struct.ritz_module_1.Response" @"response_redirect_permanent"(%"struct.ritz_module_1.Span$u8"* %"location.arg") !dbg !37
{
entry:
  %"location" = alloca %"struct.ritz_module_1.Span$u8"*
  %"res.addr" = alloca %"struct.ritz_module_1.Response", !dbg !118
  store %"struct.ritz_module_1.Span$u8"* %"location.arg", %"struct.ritz_module_1.Span$u8"** %"location"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"location", metadata !116, metadata !7), !dbg !117
  %".5" = call %"struct.ritz_module_1.Response" @"response_with_status"(i32 301), !dbg !118
  store %"struct.ritz_module_1.Response" %".5", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !118
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"* %"res.addr", metadata !119, metadata !7), !dbg !120
  %".8" = getelementptr [9 x i8], [9 x i8]* @".str.7", i64 0, i64 0 , !dbg !121
  %".9" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".8"), !dbg !121
  %".10" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"location", !dbg !121
  %".11" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".10", !dbg !121
  %".12" = call i32 @"response_set_header"(%"struct.ritz_module_1.Response"* %"res.addr", %"struct.ritz_module_1.Span$u8" %".9", %"struct.ritz_module_1.Span$u8" %".11"), !dbg !121
  %".13" = load %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %"res.addr", !dbg !122
  ret %"struct.ritz_module_1.Response" %".13", !dbg !122
}

define i32 @"response_status"(%"struct.ritz_module_1.Response"* %"self.arg") !dbg !38
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Response"*
  store %"struct.ritz_module_1.Response"* %"self.arg", %"struct.ritz_module_1.Response"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"** %"self", metadata !124, metadata !7), !dbg !125
  %".5" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !126
  %".6" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".5", i32 0, i32 0 , !dbg !126
  %".7" = load i32, i32* %".6", !dbg !126
  ret i32 %".7", !dbg !126
}

define %"struct.ritz_module_1.Span$u8" @"response_body"(%"struct.ritz_module_1.Response"* %"self.arg") !dbg !39
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Response"*
  %"sp.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !129
  store %"struct.ritz_module_1.Response"* %"self.arg", %"struct.ritz_module_1.Response"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"** %"self", metadata !127, metadata !7), !dbg !128
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"sp.addr", metadata !130, metadata !7), !dbg !131
  %".6" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !132
  %".7" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".6", i32 0, i32 3 , !dbg !132
  %".8" = getelementptr [65536 x i8], [65536 x i8]* %".7", i32 0, i64 0 , !dbg !132
  %".9" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !132
  %".10" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 0 , !dbg !132
  store i8* %".8", i8** %".10", !dbg !132
  %".12" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !133
  %".13" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".12", i32 0, i32 4 , !dbg !133
  %".14" = load i64, i64* %".13", !dbg !133
  %".15" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !133
  %".16" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 1 , !dbg !133
  store i64 %".14", i64* %".16", !dbg !133
  %".18" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !134
  ret %"struct.ritz_module_1.Span$u8" %".18", !dbg !134
}

define i64 @"response_body_len"(%"struct.ritz_module_1.Response"* %"self.arg") !dbg !40
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Response"*
  store %"struct.ritz_module_1.Response"* %"self.arg", %"struct.ritz_module_1.Response"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"** %"self", metadata !135, metadata !7), !dbg !136
  %".5" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !137
  %".6" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".5", i32 0, i32 4 , !dbg !137
  %".7" = load i64, i64* %".6", !dbg !137
  ret i64 %".7", !dbg !137
}

define i32 @"response_set_status"(%"struct.ritz_module_1.Response"* %"self.arg", i32 %"status.arg") !dbg !41
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Response"*
  store %"struct.ritz_module_1.Response"* %"self.arg", %"struct.ritz_module_1.Response"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"** %"self", metadata !138, metadata !7), !dbg !139
  %"status" = alloca i32
  store i32 %"status.arg", i32* %"status"
  call void @"llvm.dbg.declare"(metadata i32* %"status", metadata !140, metadata !7), !dbg !139
  %".8" = load i32, i32* %"status", !dbg !141
  %".9" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !141
  %".10" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".9", i32 0, i32 0 , !dbg !141
  store i32 %".8", i32* %".10", !dbg !141
  ret i32 0, !dbg !141
}

define i32 @"response_set_header"(%"struct.ritz_module_1.Response"* %"self.arg", %"struct.ritz_module_1.Span$u8" %"name.arg", %"struct.ritz_module_1.Span$u8" %"value.arg") !dbg !42
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Response"*
  %"i.addr" = alloca i64, !dbg !149
  store %"struct.ritz_module_1.Response"* %"self.arg", %"struct.ritz_module_1.Response"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"** %"self", metadata !142, metadata !7), !dbg !143
  %"name" = alloca %"struct.ritz_module_1.Span$u8"
  store %"struct.ritz_module_1.Span$u8" %"name.arg", %"struct.ritz_module_1.Span$u8"* %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"name", metadata !144, metadata !7), !dbg !143
  %"value" = alloca %"struct.ritz_module_1.Span$u8"
  store %"struct.ritz_module_1.Span$u8" %"value.arg", %"struct.ritz_module_1.Span$u8"* %"value"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"value", metadata !145, metadata !7), !dbg !143
  %".11" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !146
  %".12" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".11", i32 0, i32 2 , !dbg !146
  %".13" = load i64, i64* %".12", !dbg !146
  %".14" = icmp sge i64 %".13", 32 , !dbg !146
  br i1 %".14", label %"if.then", label %"if.end", !dbg !146
if.then:
  ret i32 0, !dbg !147
if.end:
  %".17" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !148
  %".18" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".17", i32 0, i32 2 , !dbg !148
  %".19" = load i64, i64* %".18", !dbg !148
  store i64 0, i64* %"i.addr", !dbg !149
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !150, metadata !7), !dbg !151
  br label %"while.cond", !dbg !152
while.cond:
  %".23" = load i64, i64* %"i.addr", !dbg !152
  %".24" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"name", i32 0, i32 1 , !dbg !152
  %".25" = load i64, i64* %".24", !dbg !152
  %".26" = icmp slt i64 %".23", %".25" , !dbg !152
  br i1 %".26", label %"and.right", label %"and.merge", !dbg !152
while.body:
  %".33" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"name", i32 0, i32 0 , !dbg !153
  %".34" = load i8*, i8** %".33", !dbg !153
  %".35" = load i64, i64* %"i.addr", !dbg !153
  %".36" = getelementptr i8, i8* %".34", i64 %".35" , !dbg !153
  %".37" = load i8, i8* %".36", !dbg !153
  %".38" = load i64, i64* %"i.addr", !dbg !153
  %".39" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !153
  %".40" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".39", i32 0, i32 1 , !dbg !153
  %".41" = getelementptr [32 x %"struct.ritz_module_1.ResponseHeader"], [32 x %"struct.ritz_module_1.ResponseHeader"]* %".40", i32 0, i64 %".19" , !dbg !153
  %".42" = getelementptr %"struct.ritz_module_1.ResponseHeader", %"struct.ritz_module_1.ResponseHeader"* %".41", i32 0, i32 0 , !dbg !153
  %".43" = getelementptr [128 x i8], [128 x i8]* %".42", i32 0, i64 %".38" , !dbg !153
  store i8 %".37", i8* %".43", !dbg !153
  %".45" = load i64, i64* %"i.addr", !dbg !154
  %".46" = add i64 %".45", 1, !dbg !154
  store i64 %".46", i64* %"i.addr", !dbg !154
  br label %"while.cond", !dbg !154
while.end:
  %".49" = load i64, i64* %"i.addr", !dbg !155
  %".50" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !155
  %".51" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".50", i32 0, i32 1 , !dbg !155
  %".52" = getelementptr [32 x %"struct.ritz_module_1.ResponseHeader"], [32 x %"struct.ritz_module_1.ResponseHeader"]* %".51", i32 0, i64 %".19" , !dbg !155
  %".53" = load %"struct.ritz_module_1.ResponseHeader", %"struct.ritz_module_1.ResponseHeader"* %".52", !dbg !155
  %".54" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !155
  %".55" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".54", i32 0, i32 1 , !dbg !155
  %".56" = getelementptr [32 x %"struct.ritz_module_1.ResponseHeader"], [32 x %"struct.ritz_module_1.ResponseHeader"]* %".55", i32 0, i64 %".19" , !dbg !155
  %".57" = getelementptr %"struct.ritz_module_1.ResponseHeader", %"struct.ritz_module_1.ResponseHeader"* %".56", i32 0, i32 1 , !dbg !155
  store i64 %".49", i64* %".57", !dbg !155
  store i64 0, i64* %"i.addr", !dbg !156
  br label %"while.cond.1", !dbg !157
and.right:
  %".28" = load i64, i64* %"i.addr", !dbg !152
  %".29" = icmp slt i64 %".28", 128 , !dbg !152
  br label %"and.merge", !dbg !152
and.merge:
  %".31" = phi  i1 [0, %"while.cond"], [%".29", %"and.right"] , !dbg !152
  br i1 %".31", label %"while.body", label %"while.end", !dbg !152
while.cond.1:
  %".61" = load i64, i64* %"i.addr", !dbg !157
  %".62" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"value", i32 0, i32 1 , !dbg !157
  %".63" = load i64, i64* %".62", !dbg !157
  %".64" = icmp slt i64 %".61", %".63" , !dbg !157
  br i1 %".64", label %"and.right.1", label %"and.merge.1", !dbg !157
while.body.1:
  %".71" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"value", i32 0, i32 0 , !dbg !158
  %".72" = load i8*, i8** %".71", !dbg !158
  %".73" = load i64, i64* %"i.addr", !dbg !158
  %".74" = getelementptr i8, i8* %".72", i64 %".73" , !dbg !158
  %".75" = load i8, i8* %".74", !dbg !158
  %".76" = load i64, i64* %"i.addr", !dbg !158
  %".77" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !158
  %".78" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".77", i32 0, i32 1 , !dbg !158
  %".79" = getelementptr [32 x %"struct.ritz_module_1.ResponseHeader"], [32 x %"struct.ritz_module_1.ResponseHeader"]* %".78", i32 0, i64 %".19" , !dbg !158
  %".80" = getelementptr %"struct.ritz_module_1.ResponseHeader", %"struct.ritz_module_1.ResponseHeader"* %".79", i32 0, i32 2 , !dbg !158
  %".81" = getelementptr [512 x i8], [512 x i8]* %".80", i32 0, i64 %".76" , !dbg !158
  store i8 %".75", i8* %".81", !dbg !158
  %".83" = load i64, i64* %"i.addr", !dbg !159
  %".84" = add i64 %".83", 1, !dbg !159
  store i64 %".84", i64* %"i.addr", !dbg !159
  br label %"while.cond.1", !dbg !159
while.end.1:
  %".87" = load i64, i64* %"i.addr", !dbg !160
  %".88" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !160
  %".89" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".88", i32 0, i32 1 , !dbg !160
  %".90" = getelementptr [32 x %"struct.ritz_module_1.ResponseHeader"], [32 x %"struct.ritz_module_1.ResponseHeader"]* %".89", i32 0, i64 %".19" , !dbg !160
  %".91" = load %"struct.ritz_module_1.ResponseHeader", %"struct.ritz_module_1.ResponseHeader"* %".90", !dbg !160
  %".92" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !160
  %".93" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".92", i32 0, i32 1 , !dbg !160
  %".94" = getelementptr [32 x %"struct.ritz_module_1.ResponseHeader"], [32 x %"struct.ritz_module_1.ResponseHeader"]* %".93", i32 0, i64 %".19" , !dbg !160
  %".95" = getelementptr %"struct.ritz_module_1.ResponseHeader", %"struct.ritz_module_1.ResponseHeader"* %".94", i32 0, i32 3 , !dbg !160
  store i64 %".87", i64* %".95", !dbg !160
  %".97" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !161
  %".98" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".97", i32 0, i32 2 , !dbg !161
  %".99" = load i64, i64* %".98", !dbg !161
  %".100" = add i64 %".99", 1, !dbg !161
  %".101" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !161
  %".102" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".101", i32 0, i32 2 , !dbg !161
  store i64 %".100", i64* %".102", !dbg !161
  ret i32 0, !dbg !161
and.right.1:
  %".66" = load i64, i64* %"i.addr", !dbg !157
  %".67" = icmp slt i64 %".66", 512 , !dbg !157
  br label %"and.merge.1", !dbg !157
and.merge.1:
  %".69" = phi  i1 [0, %"while.cond.1"], [%".67", %"and.right.1"] , !dbg !157
  br i1 %".69", label %"while.body.1", label %"while.end.1", !dbg !157
}

define i32 @"response_set_body"(%"struct.ritz_module_1.Response"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"body.arg") !dbg !43
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Response"*
  %"i.addr" = alloca i64, !dbg !165
  store %"struct.ritz_module_1.Response"* %"self.arg", %"struct.ritz_module_1.Response"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"** %"self", metadata !162, metadata !7), !dbg !163
  %"body" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"body.arg", %"struct.ritz_module_1.Span$u8"** %"body"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"body", metadata !164, metadata !7), !dbg !163
  store i64 0, i64* %"i.addr", !dbg !165
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !166, metadata !7), !dbg !167
  br label %"while.cond", !dbg !168
while.cond:
  %".11" = load i64, i64* %"i.addr", !dbg !168
  %".12" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"body", !dbg !168
  %".13" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".12", i32 0, i32 1 , !dbg !168
  %".14" = load i64, i64* %".13", !dbg !168
  %".15" = icmp slt i64 %".11", %".14" , !dbg !168
  br i1 %".15", label %"and.right", label %"and.merge", !dbg !168
while.body:
  %".22" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"body", !dbg !169
  %".23" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".22", i32 0, i32 0 , !dbg !169
  %".24" = load i8*, i8** %".23", !dbg !169
  %".25" = load i64, i64* %"i.addr", !dbg !169
  %".26" = getelementptr i8, i8* %".24", i64 %".25" , !dbg !169
  %".27" = load i8, i8* %".26", !dbg !169
  %".28" = load i64, i64* %"i.addr", !dbg !169
  %".29" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !169
  %".30" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".29", i32 0, i32 3 , !dbg !169
  %".31" = getelementptr [65536 x i8], [65536 x i8]* %".30", i32 0, i64 %".28" , !dbg !169
  store i8 %".27", i8* %".31", !dbg !169
  %".33" = load i64, i64* %"i.addr", !dbg !170
  %".34" = add i64 %".33", 1, !dbg !170
  store i64 %".34", i64* %"i.addr", !dbg !170
  br label %"while.cond", !dbg !170
while.end:
  %".37" = load i64, i64* %"i.addr", !dbg !171
  %".38" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !171
  %".39" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".38", i32 0, i32 4 , !dbg !171
  store i64 %".37", i64* %".39", !dbg !171
  ret i32 0, !dbg !171
and.right:
  %".17" = load i64, i64* %"i.addr", !dbg !168
  %".18" = icmp slt i64 %".17", 65536 , !dbg !168
  br label %"and.merge", !dbg !168
and.merge:
  %".20" = phi  i1 [0, %"while.cond"], [%".18", %"and.right"] , !dbg !168
  br i1 %".20", label %"while.body", label %"while.end", !dbg !168
}

define i64 @"response_header_count"(%"struct.ritz_module_1.Response"* %"self.arg") !dbg !44
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Response"*
  store %"struct.ritz_module_1.Response"* %"self.arg", %"struct.ritz_module_1.Response"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"** %"self", metadata !172, metadata !7), !dbg !173
  %".5" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !174
  %".6" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".5", i32 0, i32 2 , !dbg !174
  %".7" = load i64, i64* %".6", !dbg !174
  ret i64 %".7", !dbg !174
}

define %"struct.ritz_module_1.Span$u8" @"response_header_name"(%"struct.ritz_module_1.Response"* %"self.arg", i64 %"idx.arg") !dbg !45
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Response"*
  %"sp.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !178
  store %"struct.ritz_module_1.Response"* %"self.arg", %"struct.ritz_module_1.Response"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"** %"self", metadata !175, metadata !7), !dbg !176
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !177, metadata !7), !dbg !176
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"sp.addr", metadata !179, metadata !7), !dbg !180
  %".9" = load i64, i64* %"idx", !dbg !181
  %".10" = icmp slt i64 %".9", 0 , !dbg !181
  br i1 %".10", label %"or.merge", label %"or.right", !dbg !181
or.right:
  %".12" = load i64, i64* %"idx", !dbg !181
  %".13" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !181
  %".14" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".13", i32 0, i32 2 , !dbg !181
  %".15" = load i64, i64* %".14", !dbg !181
  %".16" = icmp sge i64 %".12", %".15" , !dbg !181
  br label %"or.merge", !dbg !181
or.merge:
  %".18" = phi  i1 [1, %"entry"], [%".16", %"or.right"] , !dbg !181
  br i1 %".18", label %"if.then", label %"if.end", !dbg !181
if.then:
  %".20" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !182
  %".21" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 0 , !dbg !182
  store i8* null, i8** %".21", !dbg !182
  %".23" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !183
  %".24" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 1 , !dbg !183
  store i64 0, i64* %".24", !dbg !183
  %".26" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !184
  ret %"struct.ritz_module_1.Span$u8" %".26", !dbg !184
if.end:
  %".28" = load i64, i64* %"idx", !dbg !185
  %".29" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !185
  %".30" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".29", i32 0, i32 1 , !dbg !185
  %".31" = getelementptr [32 x %"struct.ritz_module_1.ResponseHeader"], [32 x %"struct.ritz_module_1.ResponseHeader"]* %".30", i32 0, i64 %".28" , !dbg !185
  %".32" = getelementptr %"struct.ritz_module_1.ResponseHeader", %"struct.ritz_module_1.ResponseHeader"* %".31", i32 0, i32 0 , !dbg !185
  %".33" = getelementptr [128 x i8], [128 x i8]* %".32", i32 0, i64 0 , !dbg !185
  %".34" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !185
  %".35" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 0 , !dbg !185
  store i8* %".33", i8** %".35", !dbg !185
  %".37" = load i64, i64* %"idx", !dbg !186
  %".38" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !186
  %".39" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".38", i32 0, i32 1 , !dbg !186
  %".40" = getelementptr [32 x %"struct.ritz_module_1.ResponseHeader"], [32 x %"struct.ritz_module_1.ResponseHeader"]* %".39", i32 0, i64 %".37" , !dbg !186
  %".41" = load %"struct.ritz_module_1.ResponseHeader", %"struct.ritz_module_1.ResponseHeader"* %".40", !dbg !186
  %".42" = extractvalue %"struct.ritz_module_1.ResponseHeader" %".41", 1 , !dbg !186
  %".43" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !186
  %".44" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 1 , !dbg !186
  store i64 %".42", i64* %".44", !dbg !186
  %".46" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !187
  ret %"struct.ritz_module_1.Span$u8" %".46", !dbg !187
}

define %"struct.ritz_module_1.Span$u8" @"response_header_value"(%"struct.ritz_module_1.Response"* %"self.arg", i64 %"idx.arg") !dbg !46
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Response"*
  %"sp.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !191
  store %"struct.ritz_module_1.Response"* %"self.arg", %"struct.ritz_module_1.Response"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Response"** %"self", metadata !188, metadata !7), !dbg !189
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !190, metadata !7), !dbg !189
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"sp.addr", metadata !192, metadata !7), !dbg !193
  %".9" = load i64, i64* %"idx", !dbg !194
  %".10" = icmp slt i64 %".9", 0 , !dbg !194
  br i1 %".10", label %"or.merge", label %"or.right", !dbg !194
or.right:
  %".12" = load i64, i64* %"idx", !dbg !194
  %".13" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !194
  %".14" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".13", i32 0, i32 2 , !dbg !194
  %".15" = load i64, i64* %".14", !dbg !194
  %".16" = icmp sge i64 %".12", %".15" , !dbg !194
  br label %"or.merge", !dbg !194
or.merge:
  %".18" = phi  i1 [1, %"entry"], [%".16", %"or.right"] , !dbg !194
  br i1 %".18", label %"if.then", label %"if.end", !dbg !194
if.then:
  %".20" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !195
  %".21" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 0 , !dbg !195
  store i8* null, i8** %".21", !dbg !195
  %".23" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !196
  %".24" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 1 , !dbg !196
  store i64 0, i64* %".24", !dbg !196
  %".26" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !197
  ret %"struct.ritz_module_1.Span$u8" %".26", !dbg !197
if.end:
  %".28" = load i64, i64* %"idx", !dbg !198
  %".29" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !198
  %".30" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".29", i32 0, i32 1 , !dbg !198
  %".31" = getelementptr [32 x %"struct.ritz_module_1.ResponseHeader"], [32 x %"struct.ritz_module_1.ResponseHeader"]* %".30", i32 0, i64 %".28" , !dbg !198
  %".32" = getelementptr %"struct.ritz_module_1.ResponseHeader", %"struct.ritz_module_1.ResponseHeader"* %".31", i32 0, i32 2 , !dbg !198
  %".33" = getelementptr [512 x i8], [512 x i8]* %".32", i32 0, i64 0 , !dbg !198
  %".34" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !198
  %".35" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 0 , !dbg !198
  store i8* %".33", i8** %".35", !dbg !198
  %".37" = load i64, i64* %"idx", !dbg !199
  %".38" = load %"struct.ritz_module_1.Response"*, %"struct.ritz_module_1.Response"** %"self", !dbg !199
  %".39" = getelementptr %"struct.ritz_module_1.Response", %"struct.ritz_module_1.Response"* %".38", i32 0, i32 1 , !dbg !199
  %".40" = getelementptr [32 x %"struct.ritz_module_1.ResponseHeader"], [32 x %"struct.ritz_module_1.ResponseHeader"]* %".39", i32 0, i64 %".37" , !dbg !199
  %".41" = load %"struct.ritz_module_1.ResponseHeader", %"struct.ritz_module_1.ResponseHeader"* %".40", !dbg !199
  %".42" = extractvalue %"struct.ritz_module_1.ResponseHeader" %".41", 3 , !dbg !199
  %".43" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !199
  %".44" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 1 , !dbg !199
  store i64 %".42", i64* %".44", !dbg !199
  %".46" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !200
  ret %"struct.ritz_module_1.Span$u8" %".46", !dbg !200
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8 %"item.arg") !dbg !47
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !204, metadata !7), !dbg !205
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !206, metadata !7), !dbg !205
  %".7" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !207
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", i32 0, i32 1 , !dbg !207
  %".9" = load i64, i64* %".8", !dbg !207
  %".10" = add i64 %".9", 1, !dbg !207
  %".11" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %".10"), !dbg !207
  %".12" = sext i32 %".11" to i64 , !dbg !207
  %".13" = icmp ne i64 %".12", 0 , !dbg !207
  br i1 %".13", label %"if.then", label %"if.end", !dbg !207
if.then:
  %".15" = sub i64 0, 1, !dbg !208
  %".16" = trunc i64 %".15" to i32 , !dbg !208
  ret i32 %".16", !dbg !208
if.end:
  %".18" = load i8, i8* %"item", !dbg !209
  %".19" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !209
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".19", i32 0, i32 0 , !dbg !209
  %".21" = load i8*, i8** %".20", !dbg !209
  %".22" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !209
  %".23" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".22", i32 0, i32 1 , !dbg !209
  %".24" = load i64, i64* %".23", !dbg !209
  %".25" = getelementptr i8, i8* %".21", i64 %".24" , !dbg !209
  store i8 %".18", i8* %".25", !dbg !209
  %".27" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !210
  %".28" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".27", i32 0, i32 1 , !dbg !210
  %".29" = load i64, i64* %".28", !dbg !210
  %".30" = add i64 %".29", 1, !dbg !210
  %".31" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !210
  %".32" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".31", i32 0, i32 1 , !dbg !210
  store i64 %".30", i64* %".32", !dbg !210
  %".34" = trunc i64 0 to i32 , !dbg !211
  ret i32 %".34", !dbg !211
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !48
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !215, metadata !7), !dbg !216
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !218, metadata !7), !dbg !216
  %".7" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !219
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".7", i32 0, i32 1 , !dbg !219
  %".9" = load i64, i64* %".8", !dbg !219
  %".10" = add i64 %".9", 1, !dbg !219
  %".11" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %".10"), !dbg !219
  %".12" = sext i32 %".11" to i64 , !dbg !219
  %".13" = icmp ne i64 %".12", 0 , !dbg !219
  br i1 %".13", label %"if.then", label %"if.end", !dbg !219
if.then:
  %".15" = sub i64 0, 1, !dbg !220
  %".16" = trunc i64 %".15" to i32 , !dbg !220
  ret i32 %".16", !dbg !220
if.end:
  %".18" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !221
  %".19" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !221
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".19", i32 0, i32 0 , !dbg !221
  %".21" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".20", !dbg !221
  %".22" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !221
  %".23" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".22", i32 0, i32 1 , !dbg !221
  %".24" = load i64, i64* %".23", !dbg !221
  %".25" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".21", i64 %".24" , !dbg !221
  store %"struct.ritz_module_1.LineBounds" %".18", %"struct.ritz_module_1.LineBounds"* %".25", !dbg !221
  %".27" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !222
  %".28" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".27", i32 0, i32 1 , !dbg !222
  %".29" = load i64, i64* %".28", !dbg !222
  %".30" = add i64 %".29", 1, !dbg !222
  %".31" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !222
  %".32" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".31", i32 0, i32 1 , !dbg !222
  store i64 %".30", i64* %".32", !dbg !222
  %".34" = trunc i64 0 to i32 , !dbg !223
  ret i32 %".34", !dbg !223
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !49
{
entry:
  %"i" = alloca i64, !dbg !229
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !224, metadata !7), !dbg !225
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !227, metadata !7), !dbg !225
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !228, metadata !7), !dbg !225
  %".10" = load i64, i64* %"len", !dbg !229
  store i64 0, i64* %"i", !dbg !229
  br label %"for.cond", !dbg !229
for.cond:
  %".13" = load i64, i64* %"i", !dbg !229
  %".14" = icmp slt i64 %".13", %".10" , !dbg !229
  br i1 %".14", label %"for.body", label %"for.end", !dbg !229
for.body:
  %".16" = load i8*, i8** %"data", !dbg !229
  %".17" = load i64, i64* %"i", !dbg !229
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !229
  %".19" = load i8, i8* %".18", !dbg !229
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8 %".19"), !dbg !229
  %".21" = sext i32 %".20" to i64 , !dbg !229
  %".22" = icmp ne i64 %".21", 0 , !dbg !229
  br i1 %".22", label %"if.then", label %"if.end", !dbg !229
for.incr:
  %".28" = load i64, i64* %"i", !dbg !230
  %".29" = add i64 %".28", 1, !dbg !230
  store i64 %".29", i64* %"i", !dbg !230
  br label %"for.cond", !dbg !230
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !231
  ret i32 %".32", !dbg !231
if.then:
  %".24" = sub i64 0, 1, !dbg !230
  %".25" = trunc i64 %".24" to i32 , !dbg !230
  ret i32 %".25", !dbg !230
if.end:
  br label %"for.incr", !dbg !230
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"needed.arg") !dbg !50
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !237
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !232, metadata !7), !dbg !233
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !234, metadata !7), !dbg !233
  %".7" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !235
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", i32 0, i32 2 , !dbg !235
  %".9" = load i64, i64* %".8", !dbg !235
  %".10" = load i64, i64* %"needed", !dbg !235
  %".11" = icmp sge i64 %".9", %".10" , !dbg !235
  br i1 %".11", label %"if.then", label %"if.end", !dbg !235
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !236
  ret i32 %".13", !dbg !236
if.end:
  %".15" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !237
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".15", i32 0, i32 2 , !dbg !237
  %".17" = load i64, i64* %".16", !dbg !237
  store i64 %".17", i64* %"new_cap.addr", !dbg !237
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !238, metadata !7), !dbg !239
  %".20" = load i64, i64* %"new_cap.addr", !dbg !240
  %".21" = icmp eq i64 %".20", 0 , !dbg !240
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !240
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !241
  br label %"if.end.1", !dbg !241
if.end.1:
  br label %"while.cond", !dbg !242
while.cond:
  %".26" = load i64, i64* %"new_cap.addr", !dbg !242
  %".27" = load i64, i64* %"needed", !dbg !242
  %".28" = icmp slt i64 %".26", %".27" , !dbg !242
  br i1 %".28", label %"while.body", label %"while.end", !dbg !242
while.body:
  %".30" = load i64, i64* %"new_cap.addr", !dbg !243
  %".31" = mul i64 %".30", 2, !dbg !243
  store i64 %".31", i64* %"new_cap.addr", !dbg !243
  br label %"while.cond", !dbg !243
while.end:
  %".34" = load i64, i64* %"new_cap.addr", !dbg !244
  %".35" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %".34"), !dbg !244
  ret i32 %".35", !dbg !244
}

define linkonce_odr i8 @"span_get$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg", i64 %"idx.arg") !dbg !51
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !245, metadata !7), !dbg !246
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !247, metadata !7), !dbg !246
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !248
  %".9" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".8", i32 0, i32 0 , !dbg !248
  %".10" = load i8*, i8** %".9", !dbg !248
  %".11" = load i64, i64* %"idx", !dbg !248
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !248
  %".13" = load i8, i8* %".12", !dbg !248
  ret i8 %".13", !dbg !248
}

define linkonce_odr i32 @"span_is_empty$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg") !dbg !52
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !249, metadata !7), !dbg !250
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !251
  %".6" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".5", i32 0, i32 1 , !dbg !251
  %".7" = load i64, i64* %".6", !dbg !251
  %".8" = icmp eq i64 %".7", 0 , !dbg !251
  br i1 %".8", label %"if.then", label %"if.end", !dbg !251
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !252
  ret i32 %".10", !dbg !252
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !253
  ret i32 %".12", !dbg !253
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %"needed.arg") !dbg !53
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !259
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !254, metadata !7), !dbg !255
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !256, metadata !7), !dbg !255
  %".7" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !257
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".7", i32 0, i32 2 , !dbg !257
  %".9" = load i64, i64* %".8", !dbg !257
  %".10" = load i64, i64* %"needed", !dbg !257
  %".11" = icmp sge i64 %".9", %".10" , !dbg !257
  br i1 %".11", label %"if.then", label %"if.end", !dbg !257
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !258
  ret i32 %".13", !dbg !258
if.end:
  %".15" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !259
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".15", i32 0, i32 2 , !dbg !259
  %".17" = load i64, i64* %".16", !dbg !259
  store i64 %".17", i64* %"new_cap.addr", !dbg !259
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !260, metadata !7), !dbg !261
  %".20" = load i64, i64* %"new_cap.addr", !dbg !262
  %".21" = icmp eq i64 %".20", 0 , !dbg !262
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !262
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !263
  br label %"if.end.1", !dbg !263
if.end.1:
  br label %"while.cond", !dbg !264
while.cond:
  %".26" = load i64, i64* %"new_cap.addr", !dbg !264
  %".27" = load i64, i64* %"needed", !dbg !264
  %".28" = icmp slt i64 %".26", %".27" , !dbg !264
  br i1 %".28", label %"while.body", label %"while.end", !dbg !264
while.body:
  %".30" = load i64, i64* %"new_cap.addr", !dbg !265
  %".31" = mul i64 %".30", 2, !dbg !265
  store i64 %".31", i64* %"new_cap.addr", !dbg !265
  br label %"while.cond", !dbg !265
while.end:
  %".34" = load i64, i64* %"new_cap.addr", !dbg !266
  %".35" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %".34"), !dbg !266
  ret i32 %".35", !dbg !266
}

define linkonce_odr i8* @"span_as_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg") !dbg !54
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !267, metadata !7), !dbg !268
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !269
  %".6" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".5", i32 0, i32 0 , !dbg !269
  %".7" = load i8*, i8** %".6", !dbg !269
  ret i8* %".7", !dbg !269
}

define linkonce_odr %"struct.ritz_module_1.Span$u8" @"span_slice$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg", i64 %"start.arg", i64 %"end.arg") !dbg !55
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  %"result.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !274
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !270, metadata !7), !dbg !271
  %"start" = alloca i64
  store i64 %"start.arg", i64* %"start"
  call void @"llvm.dbg.declare"(metadata i64* %"start", metadata !272, metadata !7), !dbg !271
  %"end" = alloca i64
  store i64 %"end.arg", i64* %"end"
  call void @"llvm.dbg.declare"(metadata i64* %"end", metadata !273, metadata !7), !dbg !271
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"result.addr", metadata !275, metadata !7), !dbg !276
  %".12" = load i64, i64* %"start", !dbg !277
  %".13" = icmp slt i64 %".12", 0 , !dbg !277
  br i1 %".13", label %"if.then", label %"if.end", !dbg !277
if.then:
  store i64 0, i64* %"start", !dbg !278
  br label %"if.end", !dbg !278
if.end:
  %".17" = load i64, i64* %"end", !dbg !279
  %".18" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !279
  %".19" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".18", i32 0, i32 1 , !dbg !279
  %".20" = load i64, i64* %".19", !dbg !279
  %".21" = icmp sgt i64 %".17", %".20" , !dbg !279
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !279
if.then.1:
  %".23" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !280
  %".24" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".23", i32 0, i32 1 , !dbg !280
  %".25" = load i64, i64* %".24", !dbg !280
  store i64 %".25", i64* %"end", !dbg !280
  br label %"if.end.1", !dbg !280
if.end.1:
  %".28" = load i64, i64* %"start", !dbg !281
  %".29" = load i64, i64* %"end", !dbg !281
  %".30" = icmp sge i64 %".28", %".29" , !dbg !281
  br i1 %".30", label %"if.then.2", label %"if.end.2", !dbg !281
if.then.2:
  %".32" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !282
  %".33" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 0 , !dbg !282
  store i8* null, i8** %".33", !dbg !282
  %".35" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !283
  %".36" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 1 , !dbg !283
  store i64 0, i64* %".36", !dbg !283
  %".38" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !284
  ret %"struct.ritz_module_1.Span$u8" %".38", !dbg !284
if.end.2:
  %".40" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !285
  %".41" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".40", i32 0, i32 0 , !dbg !285
  %".42" = load i8*, i8** %".41", !dbg !285
  %".43" = load i64, i64* %"start", !dbg !285
  %".44" = getelementptr i8, i8* %".42", i64 %".43" , !dbg !285
  %".45" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !285
  %".46" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 0 , !dbg !285
  store i8* %".44", i8** %".46", !dbg !285
  %".48" = load i64, i64* %"end", !dbg !286
  %".49" = load i64, i64* %"start", !dbg !286
  %".50" = sub i64 %".48", %".49", !dbg !286
  %".51" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !286
  %".52" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 1 , !dbg !286
  store i64 %".50", i64* %".52", !dbg !286
  %".54" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !287
  ret %"struct.ritz_module_1.Span$u8" %".54", !dbg !287
}

define linkonce_odr i64 @"span_len$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg") !dbg !56
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !288, metadata !7), !dbg !289
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !290
  %".6" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".5", i32 0, i32 1 , !dbg !290
  %".7" = load i64, i64* %".6", !dbg !290
  ret i64 %".7", !dbg !290
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"new_cap.arg") !dbg !57
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !291, metadata !7), !dbg !292
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !293, metadata !7), !dbg !292
  %".7" = load i64, i64* %"new_cap", !dbg !294
  %".8" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !294
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".8", i32 0, i32 2 , !dbg !294
  %".10" = load i64, i64* %".9", !dbg !294
  %".11" = icmp sle i64 %".7", %".10" , !dbg !294
  br i1 %".11", label %"if.then", label %"if.end", !dbg !294
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !295
  ret i32 %".13", !dbg !295
if.end:
  %".15" = load i64, i64* %"new_cap", !dbg !296
  %".16" = mul i64 %".15", 1, !dbg !296
  %".17" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !297
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".17", i32 0, i32 0 , !dbg !297
  %".19" = load i8*, i8** %".18", !dbg !297
  %".20" = call i8* @"realloc"(i8* %".19", i64 %".16"), !dbg !297
  %".21" = icmp eq i8* %".20", null , !dbg !298
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !298
if.then.1:
  %".23" = sub i64 0, 1, !dbg !299
  %".24" = trunc i64 %".23" to i32 , !dbg !299
  ret i32 %".24", !dbg !299
if.end.1:
  %".26" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !300
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".26", i32 0, i32 0 , !dbg !300
  store i8* %".20", i8** %".27", !dbg !300
  %".29" = load i64, i64* %"new_cap", !dbg !301
  %".30" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !301
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".30", i32 0, i32 2 , !dbg !301
  store i64 %".29", i64* %".31", !dbg !301
  %".33" = trunc i64 0 to i32 , !dbg !302
  ret i32 %".33", !dbg !302
}

define linkonce_odr i8* @"span_get_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg", i64 %"idx.arg") !dbg !58
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !303, metadata !7), !dbg !304
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !305, metadata !7), !dbg !304
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !306
  %".9" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".8", i32 0, i32 0 , !dbg !306
  %".10" = load i8*, i8** %".9", !dbg !306
  %".11" = load i64, i64* %"idx", !dbg !306
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !306
  ret i8* %".12", !dbg !306
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %"new_cap.arg") !dbg !59
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !307, metadata !7), !dbg !308
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !309, metadata !7), !dbg !308
  %".7" = load i64, i64* %"new_cap", !dbg !310
  %".8" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !310
  %".9" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".8", i32 0, i32 2 , !dbg !310
  %".10" = load i64, i64* %".9", !dbg !310
  %".11" = icmp sle i64 %".7", %".10" , !dbg !310
  br i1 %".11", label %"if.then", label %"if.end", !dbg !310
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !311
  ret i32 %".13", !dbg !311
if.end:
  %".15" = load i64, i64* %"new_cap", !dbg !312
  %".16" = mul i64 %".15", 16, !dbg !312
  %".17" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !313
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".17", i32 0, i32 0 , !dbg !313
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !313
  %".20" = bitcast %"struct.ritz_module_1.LineBounds"* %".19" to i8* , !dbg !313
  %".21" = call i8* @"realloc"(i8* %".20", i64 %".16"), !dbg !313
  %".22" = icmp eq i8* %".21", null , !dbg !314
  br i1 %".22", label %"if.then.1", label %"if.end.1", !dbg !314
if.then.1:
  %".24" = sub i64 0, 1, !dbg !315
  %".25" = trunc i64 %".24" to i32 , !dbg !315
  ret i32 %".25", !dbg !315
if.end.1:
  %".27" = bitcast i8* %".21" to %"struct.ritz_module_1.LineBounds"* , !dbg !316
  %".28" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !316
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".28", i32 0, i32 0 , !dbg !316
  store %"struct.ritz_module_1.LineBounds"* %".27", %"struct.ritz_module_1.LineBounds"** %".29", !dbg !316
  %".31" = load i64, i64* %"new_cap", !dbg !317
  %".32" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !317
  %".33" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".32", i32 0, i32 2 , !dbg !317
  store i64 %".31", i64* %".33", !dbg !317
  %".35" = trunc i64 0 to i32 , !dbg !318
  ret i32 %".35", !dbg !318
}

@".str.0" = private constant [13 x i8] c"Content-Type\00"
@".str.1" = private constant [25 x i8] c"text/html; charset=utf-8\00"
@".str.2" = private constant [13 x i8] c"Content-Type\00"
@".str.3" = private constant [17 x i8] c"application/json\00"
@".str.4" = private constant [13 x i8] c"Content-Type\00"
@".str.5" = private constant [26 x i8] c"text/plain; charset=utf-8\00"
@".str.6" = private constant [9 x i8] c"Location\00"
@".str.7" = private constant [9 x i8] c"Location\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/spire/lib/http", filename: "response.ritz")
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
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 31, name: "response_new", scopeLine: 31, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 39, name: "response_with_status", scopeLine: 39, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 49, name: "response_ok", scopeLine: 49, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 53, name: "response_created", scopeLine: 53, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 57, name: "response_no_content", scopeLine: 57, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 61, name: "response_bad_request", scopeLine: 61, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 65, name: "response_unauthorized", scopeLine: 65, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 69, name: "response_forbidden", scopeLine: 69, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 73, name: "response_not_found", scopeLine: 73, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 77, name: "response_internal_error", scopeLine: 77, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 85, name: "response_html", scopeLine: 85, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 92, name: "response_json_str", scopeLine: 92, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 99, name: "response_text", scopeLine: 99, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 110, name: "response_redirect", scopeLine: 110, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "response_redirect_permanent", scopeLine: 116, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 125, name: "response_status", scopeLine: 125, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 128, name: "response_body", scopeLine: 128, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 134, name: "response_body_len", scopeLine: 134, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 141, name: "response_set_status", scopeLine: 141, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 144, name: "response_set_header", scopeLine: 144, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 162, name: "response_set_body", scopeLine: 162, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 173, name: "response_header_count", scopeLine: 173, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 176, name: "response_header_name", scopeLine: 176, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 186, name: "response_header_value", scopeLine: 186, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!51 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 89, name: "span_get$u8", scopeLine: 89, type: !4, unit: !1)
!52 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 83, name: "span_is_empty$u8", scopeLine: 83, type: !4, unit: !1)
!53 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!54 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 97, name: "span_as_ptr$u8", scopeLine: 97, type: !4, unit: !1)
!55 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 105, name: "span_slice$u8", scopeLine: 105, type: !4, unit: !1)
!56 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 79, name: "span_len$u8", scopeLine: 79, type: !4, unit: !1)
!57 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!58 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 93, name: "span_get_ptr$u8", scopeLine: 93, type: !4, unit: !1)
!59 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!60 = !DILocation(column: 5, line: 32, scope: !23)
!61 = !DICompositeType(align: 64, file: !0, name: "Response", size: 692416, tag: DW_TAG_structure_type)
!62 = !DILocalVariable(file: !0, line: 32, name: "res", scope: !23, type: !61)
!63 = !DILocation(column: 1, line: 32, scope: !23)
!64 = !DILocation(column: 5, line: 33, scope: !23)
!65 = !DILocation(column: 5, line: 34, scope: !23)
!66 = !DILocation(column: 5, line: 35, scope: !23)
!67 = !DILocation(column: 5, line: 36, scope: !23)
!68 = !DILocalVariable(file: !0, line: 39, name: "status", scope: !24, type: !10)
!69 = !DILocation(column: 1, line: 39, scope: !24)
!70 = !DILocation(column: 5, line: 40, scope: !24)
!71 = !DILocalVariable(file: !0, line: 40, name: "res", scope: !24, type: !61)
!72 = !DILocation(column: 1, line: 40, scope: !24)
!73 = !DILocation(column: 5, line: 41, scope: !24)
!74 = !DILocation(column: 5, line: 42, scope: !24)
!75 = !DILocation(column: 5, line: 50, scope: !25)
!76 = !DILocation(column: 5, line: 54, scope: !26)
!77 = !DILocation(column: 5, line: 58, scope: !27)
!78 = !DILocation(column: 5, line: 62, scope: !28)
!79 = !DILocation(column: 5, line: 66, scope: !29)
!80 = !DILocation(column: 5, line: 70, scope: !30)
!81 = !DILocation(column: 5, line: 74, scope: !31)
!82 = !DILocation(column: 5, line: 78, scope: !32)
!83 = !DICompositeType(align: 64, file: !0, name: "Span$u8", size: 128, tag: DW_TAG_structure_type)
!84 = !DIDerivedType(baseType: !83, size: 64, tag: DW_TAG_pointer_type)
!85 = !DILocalVariable(file: !0, line: 85, name: "body", scope: !33, type: !84)
!86 = !DILocation(column: 1, line: 85, scope: !33)
!87 = !DILocation(column: 5, line: 86, scope: !33)
!88 = !DILocalVariable(file: !0, line: 86, name: "res", scope: !33, type: !61)
!89 = !DILocation(column: 1, line: 86, scope: !33)
!90 = !DILocation(column: 5, line: 87, scope: !33)
!91 = !DILocation(column: 5, line: 88, scope: !33)
!92 = !DILocation(column: 5, line: 89, scope: !33)
!93 = !DILocalVariable(file: !0, line: 92, name: "body", scope: !34, type: !84)
!94 = !DILocation(column: 1, line: 92, scope: !34)
!95 = !DILocation(column: 5, line: 93, scope: !34)
!96 = !DILocalVariable(file: !0, line: 93, name: "res", scope: !34, type: !61)
!97 = !DILocation(column: 1, line: 93, scope: !34)
!98 = !DILocation(column: 5, line: 94, scope: !34)
!99 = !DILocation(column: 5, line: 95, scope: !34)
!100 = !DILocation(column: 5, line: 96, scope: !34)
!101 = !DILocalVariable(file: !0, line: 99, name: "body", scope: !35, type: !84)
!102 = !DILocation(column: 1, line: 99, scope: !35)
!103 = !DILocation(column: 5, line: 100, scope: !35)
!104 = !DILocalVariable(file: !0, line: 100, name: "res", scope: !35, type: !61)
!105 = !DILocation(column: 1, line: 100, scope: !35)
!106 = !DILocation(column: 5, line: 101, scope: !35)
!107 = !DILocation(column: 5, line: 102, scope: !35)
!108 = !DILocation(column: 5, line: 103, scope: !35)
!109 = !DILocalVariable(file: !0, line: 110, name: "location", scope: !36, type: !84)
!110 = !DILocation(column: 1, line: 110, scope: !36)
!111 = !DILocation(column: 5, line: 111, scope: !36)
!112 = !DILocalVariable(file: !0, line: 111, name: "res", scope: !36, type: !61)
!113 = !DILocation(column: 1, line: 111, scope: !36)
!114 = !DILocation(column: 5, line: 112, scope: !36)
!115 = !DILocation(column: 5, line: 113, scope: !36)
!116 = !DILocalVariable(file: !0, line: 116, name: "location", scope: !37, type: !84)
!117 = !DILocation(column: 1, line: 116, scope: !37)
!118 = !DILocation(column: 5, line: 117, scope: !37)
!119 = !DILocalVariable(file: !0, line: 117, name: "res", scope: !37, type: !61)
!120 = !DILocation(column: 1, line: 117, scope: !37)
!121 = !DILocation(column: 5, line: 118, scope: !37)
!122 = !DILocation(column: 5, line: 119, scope: !37)
!123 = !DIDerivedType(baseType: !61, size: 64, tag: DW_TAG_pointer_type)
!124 = !DILocalVariable(file: !0, line: 125, name: "self", scope: !38, type: !123)
!125 = !DILocation(column: 1, line: 125, scope: !38)
!126 = !DILocation(column: 5, line: 126, scope: !38)
!127 = !DILocalVariable(file: !0, line: 128, name: "self", scope: !39, type: !123)
!128 = !DILocation(column: 1, line: 128, scope: !39)
!129 = !DILocation(column: 5, line: 129, scope: !39)
!130 = !DILocalVariable(file: !0, line: 129, name: "sp", scope: !39, type: !83)
!131 = !DILocation(column: 1, line: 129, scope: !39)
!132 = !DILocation(column: 5, line: 130, scope: !39)
!133 = !DILocation(column: 5, line: 131, scope: !39)
!134 = !DILocation(column: 5, line: 132, scope: !39)
!135 = !DILocalVariable(file: !0, line: 134, name: "self", scope: !40, type: !123)
!136 = !DILocation(column: 1, line: 134, scope: !40)
!137 = !DILocation(column: 5, line: 135, scope: !40)
!138 = !DILocalVariable(file: !0, line: 141, name: "self", scope: !41, type: !123)
!139 = !DILocation(column: 1, line: 141, scope: !41)
!140 = !DILocalVariable(file: !0, line: 141, name: "status", scope: !41, type: !10)
!141 = !DILocation(column: 5, line: 142, scope: !41)
!142 = !DILocalVariable(file: !0, line: 144, name: "self", scope: !42, type: !123)
!143 = !DILocation(column: 1, line: 144, scope: !42)
!144 = !DILocalVariable(file: !0, line: 144, name: "name", scope: !42, type: !83)
!145 = !DILocalVariable(file: !0, line: 144, name: "value", scope: !42, type: !83)
!146 = !DILocation(column: 5, line: 145, scope: !42)
!147 = !DILocation(column: 9, line: 146, scope: !42)
!148 = !DILocation(column: 5, line: 147, scope: !42)
!149 = !DILocation(column: 5, line: 149, scope: !42)
!150 = !DILocalVariable(file: !0, line: 149, name: "i", scope: !42, type: !11)
!151 = !DILocation(column: 1, line: 149, scope: !42)
!152 = !DILocation(column: 5, line: 150, scope: !42)
!153 = !DILocation(column: 9, line: 151, scope: !42)
!154 = !DILocation(column: 9, line: 152, scope: !42)
!155 = !DILocation(column: 5, line: 153, scope: !42)
!156 = !DILocation(column: 5, line: 155, scope: !42)
!157 = !DILocation(column: 5, line: 156, scope: !42)
!158 = !DILocation(column: 9, line: 157, scope: !42)
!159 = !DILocation(column: 9, line: 158, scope: !42)
!160 = !DILocation(column: 5, line: 159, scope: !42)
!161 = !DILocation(column: 5, line: 160, scope: !42)
!162 = !DILocalVariable(file: !0, line: 162, name: "self", scope: !43, type: !123)
!163 = !DILocation(column: 1, line: 162, scope: !43)
!164 = !DILocalVariable(file: !0, line: 162, name: "body", scope: !43, type: !84)
!165 = !DILocation(column: 5, line: 163, scope: !43)
!166 = !DILocalVariable(file: !0, line: 163, name: "i", scope: !43, type: !11)
!167 = !DILocation(column: 1, line: 163, scope: !43)
!168 = !DILocation(column: 5, line: 164, scope: !43)
!169 = !DILocation(column: 9, line: 165, scope: !43)
!170 = !DILocation(column: 9, line: 166, scope: !43)
!171 = !DILocation(column: 5, line: 167, scope: !43)
!172 = !DILocalVariable(file: !0, line: 173, name: "self", scope: !44, type: !123)
!173 = !DILocation(column: 1, line: 173, scope: !44)
!174 = !DILocation(column: 5, line: 174, scope: !44)
!175 = !DILocalVariable(file: !0, line: 176, name: "self", scope: !45, type: !123)
!176 = !DILocation(column: 1, line: 176, scope: !45)
!177 = !DILocalVariable(file: !0, line: 176, name: "idx", scope: !45, type: !11)
!178 = !DILocation(column: 5, line: 177, scope: !45)
!179 = !DILocalVariable(file: !0, line: 177, name: "sp", scope: !45, type: !83)
!180 = !DILocation(column: 1, line: 177, scope: !45)
!181 = !DILocation(column: 5, line: 178, scope: !45)
!182 = !DILocation(column: 9, line: 179, scope: !45)
!183 = !DILocation(column: 9, line: 180, scope: !45)
!184 = !DILocation(column: 9, line: 181, scope: !45)
!185 = !DILocation(column: 5, line: 182, scope: !45)
!186 = !DILocation(column: 5, line: 183, scope: !45)
!187 = !DILocation(column: 5, line: 184, scope: !45)
!188 = !DILocalVariable(file: !0, line: 186, name: "self", scope: !46, type: !123)
!189 = !DILocation(column: 1, line: 186, scope: !46)
!190 = !DILocalVariable(file: !0, line: 186, name: "idx", scope: !46, type: !11)
!191 = !DILocation(column: 5, line: 187, scope: !46)
!192 = !DILocalVariable(file: !0, line: 187, name: "sp", scope: !46, type: !83)
!193 = !DILocation(column: 1, line: 187, scope: !46)
!194 = !DILocation(column: 5, line: 188, scope: !46)
!195 = !DILocation(column: 9, line: 189, scope: !46)
!196 = !DILocation(column: 9, line: 190, scope: !46)
!197 = !DILocation(column: 9, line: 191, scope: !46)
!198 = !DILocation(column: 5, line: 192, scope: !46)
!199 = !DILocation(column: 5, line: 193, scope: !46)
!200 = !DILocation(column: 5, line: 194, scope: !46)
!201 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!202 = !DIDerivedType(baseType: !201, size: 64, tag: DW_TAG_reference_type)
!203 = !DIDerivedType(baseType: !202, size: 64, tag: DW_TAG_reference_type)
!204 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !47, type: !203)
!205 = !DILocation(column: 1, line: 210, scope: !47)
!206 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !47, type: !12)
!207 = !DILocation(column: 5, line: 211, scope: !47)
!208 = !DILocation(column: 9, line: 212, scope: !47)
!209 = !DILocation(column: 5, line: 213, scope: !47)
!210 = !DILocation(column: 5, line: 214, scope: !47)
!211 = !DILocation(column: 5, line: 215, scope: !47)
!212 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!213 = !DIDerivedType(baseType: !212, size: 64, tag: DW_TAG_reference_type)
!214 = !DIDerivedType(baseType: !213, size: 64, tag: DW_TAG_reference_type)
!215 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !48, type: !214)
!216 = !DILocation(column: 1, line: 210, scope: !48)
!217 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!218 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !48, type: !217)
!219 = !DILocation(column: 5, line: 211, scope: !48)
!220 = !DILocation(column: 9, line: 212, scope: !48)
!221 = !DILocation(column: 5, line: 213, scope: !48)
!222 = !DILocation(column: 5, line: 214, scope: !48)
!223 = !DILocation(column: 5, line: 215, scope: !48)
!224 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !49, type: !203)
!225 = !DILocation(column: 1, line: 288, scope: !49)
!226 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!227 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !49, type: !226)
!228 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !49, type: !11)
!229 = !DILocation(column: 5, line: 289, scope: !49)
!230 = !DILocation(column: 13, line: 291, scope: !49)
!231 = !DILocation(column: 5, line: 292, scope: !49)
!232 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !50, type: !203)
!233 = !DILocation(column: 1, line: 193, scope: !50)
!234 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !50, type: !11)
!235 = !DILocation(column: 5, line: 194, scope: !50)
!236 = !DILocation(column: 9, line: 195, scope: !50)
!237 = !DILocation(column: 5, line: 197, scope: !50)
!238 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !50, type: !11)
!239 = !DILocation(column: 1, line: 197, scope: !50)
!240 = !DILocation(column: 5, line: 198, scope: !50)
!241 = !DILocation(column: 9, line: 199, scope: !50)
!242 = !DILocation(column: 5, line: 200, scope: !50)
!243 = !DILocation(column: 9, line: 201, scope: !50)
!244 = !DILocation(column: 5, line: 203, scope: !50)
!245 = !DILocalVariable(file: !0, line: 89, name: "s", scope: !51, type: !84)
!246 = !DILocation(column: 1, line: 89, scope: !51)
!247 = !DILocalVariable(file: !0, line: 89, name: "idx", scope: !51, type: !11)
!248 = !DILocation(column: 5, line: 90, scope: !51)
!249 = !DILocalVariable(file: !0, line: 83, name: "s", scope: !52, type: !84)
!250 = !DILocation(column: 1, line: 83, scope: !52)
!251 = !DILocation(column: 5, line: 84, scope: !52)
!252 = !DILocation(column: 9, line: 85, scope: !52)
!253 = !DILocation(column: 5, line: 86, scope: !52)
!254 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !53, type: !214)
!255 = !DILocation(column: 1, line: 193, scope: !53)
!256 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !53, type: !11)
!257 = !DILocation(column: 5, line: 194, scope: !53)
!258 = !DILocation(column: 9, line: 195, scope: !53)
!259 = !DILocation(column: 5, line: 197, scope: !53)
!260 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !53, type: !11)
!261 = !DILocation(column: 1, line: 197, scope: !53)
!262 = !DILocation(column: 5, line: 198, scope: !53)
!263 = !DILocation(column: 9, line: 199, scope: !53)
!264 = !DILocation(column: 5, line: 200, scope: !53)
!265 = !DILocation(column: 9, line: 201, scope: !53)
!266 = !DILocation(column: 5, line: 203, scope: !53)
!267 = !DILocalVariable(file: !0, line: 97, name: "s", scope: !54, type: !84)
!268 = !DILocation(column: 1, line: 97, scope: !54)
!269 = !DILocation(column: 5, line: 98, scope: !54)
!270 = !DILocalVariable(file: !0, line: 105, name: "s", scope: !55, type: !84)
!271 = !DILocation(column: 1, line: 105, scope: !55)
!272 = !DILocalVariable(file: !0, line: 105, name: "start", scope: !55, type: !11)
!273 = !DILocalVariable(file: !0, line: 105, name: "end", scope: !55, type: !11)
!274 = !DILocation(column: 5, line: 106, scope: !55)
!275 = !DILocalVariable(file: !0, line: 106, name: "result", scope: !55, type: !83)
!276 = !DILocation(column: 1, line: 106, scope: !55)
!277 = !DILocation(column: 5, line: 107, scope: !55)
!278 = !DILocation(column: 9, line: 108, scope: !55)
!279 = !DILocation(column: 5, line: 109, scope: !55)
!280 = !DILocation(column: 9, line: 110, scope: !55)
!281 = !DILocation(column: 5, line: 111, scope: !55)
!282 = !DILocation(column: 9, line: 112, scope: !55)
!283 = !DILocation(column: 9, line: 113, scope: !55)
!284 = !DILocation(column: 9, line: 114, scope: !55)
!285 = !DILocation(column: 5, line: 115, scope: !55)
!286 = !DILocation(column: 5, line: 116, scope: !55)
!287 = !DILocation(column: 5, line: 117, scope: !55)
!288 = !DILocalVariable(file: !0, line: 79, name: "s", scope: !56, type: !84)
!289 = !DILocation(column: 1, line: 79, scope: !56)
!290 = !DILocation(column: 5, line: 80, scope: !56)
!291 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !57, type: !203)
!292 = !DILocation(column: 1, line: 179, scope: !57)
!293 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !57, type: !11)
!294 = !DILocation(column: 5, line: 180, scope: !57)
!295 = !DILocation(column: 9, line: 181, scope: !57)
!296 = !DILocation(column: 5, line: 183, scope: !57)
!297 = !DILocation(column: 5, line: 184, scope: !57)
!298 = !DILocation(column: 5, line: 185, scope: !57)
!299 = !DILocation(column: 9, line: 186, scope: !57)
!300 = !DILocation(column: 5, line: 188, scope: !57)
!301 = !DILocation(column: 5, line: 189, scope: !57)
!302 = !DILocation(column: 5, line: 190, scope: !57)
!303 = !DILocalVariable(file: !0, line: 93, name: "s", scope: !58, type: !84)
!304 = !DILocation(column: 1, line: 93, scope: !58)
!305 = !DILocalVariable(file: !0, line: 93, name: "idx", scope: !58, type: !11)
!306 = !DILocation(column: 5, line: 94, scope: !58)
!307 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !59, type: !214)
!308 = !DILocation(column: 1, line: 179, scope: !59)
!309 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !59, type: !11)
!310 = !DILocation(column: 5, line: 180, scope: !59)
!311 = !DILocation(column: 9, line: 181, scope: !59)
!312 = !DILocation(column: 5, line: 183, scope: !59)
!313 = !DILocation(column: 5, line: 184, scope: !59)
!314 = !DILocation(column: 5, line: 185, scope: !59)
!315 = !DILocation(column: 9, line: 186, scope: !59)
!316 = !DILocation(column: 5, line: 188, scope: !59)
!317 = !DILocation(column: 5, line: 189, scope: !59)
!318 = !DILocation(column: 5, line: 190, scope: !59)
!319 = !DILocalVariable(file: !0, line: 208, name: "self", scope: !17, type: !84)
!320 = !DILocation(column: 1, line: 208, scope: !17)
!321 = !DILocation(column: 9, line: 209, scope: !17)
!322 = !DILocalVariable(file: !0, line: 211, name: "self", scope: !18, type: !84)
!323 = !DILocation(column: 1, line: 211, scope: !18)
!324 = !DILocation(column: 9, line: 212, scope: !18)
!325 = !DILocalVariable(file: !0, line: 214, name: "self", scope: !19, type: !84)
!326 = !DILocation(column: 1, line: 214, scope: !19)
!327 = !DILocalVariable(file: !0, line: 214, name: "idx", scope: !19, type: !11)
!328 = !DILocation(column: 9, line: 215, scope: !19)
!329 = !DILocalVariable(file: !0, line: 217, name: "self", scope: !20, type: !84)
!330 = !DILocation(column: 1, line: 217, scope: !20)
!331 = !DILocalVariable(file: !0, line: 217, name: "idx", scope: !20, type: !11)
!332 = !DILocation(column: 9, line: 218, scope: !20)
!333 = !DILocalVariable(file: !0, line: 220, name: "self", scope: !21, type: !84)
!334 = !DILocation(column: 1, line: 220, scope: !21)
!335 = !DILocation(column: 9, line: 221, scope: !21)
!336 = !DILocalVariable(file: !0, line: 223, name: "self", scope: !22, type: !84)
!337 = !DILocation(column: 1, line: 223, scope: !22)
!338 = !DILocalVariable(file: !0, line: 223, name: "start", scope: !22, type: !11)
!339 = !DILocalVariable(file: !0, line: 223, name: "end", scope: !22, type: !11)
!340 = !DILocation(column: 9, line: 224, scope: !22)