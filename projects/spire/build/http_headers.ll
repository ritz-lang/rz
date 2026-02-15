; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Vec$u8" = type {i8*, i64, i64}
%"struct.ritz_module_1.Vec$LineBounds" = type {%"struct.ritz_module_1.LineBounds"*, i64, i64}
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
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !312, metadata !7), !dbg !313
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !314
  %".6" = call i64 @"span_len$u8"(%"struct.ritz_module_1.Span$u8"* %".5"), !dbg !314
  ret i64 %".6", !dbg !314
}

define linkonce_odr i32 @"Span$u8_is_empty"(%"struct.ritz_module_1.Span$u8"* %"self.arg") !dbg !18
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !315, metadata !7), !dbg !316
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !317
  %".6" = call i32 @"span_is_empty$u8"(%"struct.ritz_module_1.Span$u8"* %".5"), !dbg !317
  ret i32 %".6", !dbg !317
}

define linkonce_odr i8 @"Span$u8_get"(%"struct.ritz_module_1.Span$u8"* %"self.arg", i64 %"idx.arg") !dbg !19
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !318, metadata !7), !dbg !319
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !320, metadata !7), !dbg !319
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !321
  %".9" = load i64, i64* %"idx", !dbg !321
  %".10" = call i8 @"span_get$u8"(%"struct.ritz_module_1.Span$u8"* %".8", i64 %".9"), !dbg !321
  ret i8 %".10", !dbg !321
}

define linkonce_odr i8* @"Span$u8_get_ptr"(%"struct.ritz_module_1.Span$u8"* %"self.arg", i64 %"idx.arg") !dbg !20
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !322, metadata !7), !dbg !323
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !324, metadata !7), !dbg !323
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !325
  %".9" = load i64, i64* %"idx", !dbg !325
  %".10" = call i8* @"span_get_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %".8", i64 %".9"), !dbg !325
  ret i8* %".10", !dbg !325
}

define linkonce_odr i8* @"Span$u8_as_ptr"(%"struct.ritz_module_1.Span$u8"* %"self.arg") !dbg !21
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !326, metadata !7), !dbg !327
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !328
  %".6" = call i8* @"span_as_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %".5"), !dbg !328
  ret i8* %".6", !dbg !328
}

define linkonce_odr %"struct.ritz_module_1.Span$u8" @"Span$u8_slice"(%"struct.ritz_module_1.Span$u8"* %"self.arg", i64 %"start.arg", i64 %"end.arg") !dbg !22
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !329, metadata !7), !dbg !330
  %"start" = alloca i64
  store i64 %"start.arg", i64* %"start"
  call void @"llvm.dbg.declare"(metadata i64* %"start", metadata !331, metadata !7), !dbg !330
  %"end" = alloca i64
  store i64 %"end.arg", i64* %"end"
  call void @"llvm.dbg.declare"(metadata i64* %"end", metadata !332, metadata !7), !dbg !330
  %".11" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !333
  %".12" = load i64, i64* %"start", !dbg !333
  %".13" = load i64, i64* %"end", !dbg !333
  %".14" = call %"struct.ritz_module_1.Span$u8" @"span_slice$u8"(%"struct.ritz_module_1.Span$u8"* %".11", i64 %".12", i64 %".13"), !dbg !333
  ret %"struct.ritz_module_1.Span$u8" %".14", !dbg !333
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

define %"struct.ritz_module_1.Headers" @"headers_new"() !dbg !23
{
entry:
  %"h.addr" = alloca %"struct.ritz_module_1.Headers", !dbg !57
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Headers"* %"h.addr", metadata !59, metadata !7), !dbg !60
  %".3" = load %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %"h.addr", !dbg !61
  %".4" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %"h.addr", i32 0, i32 1 , !dbg !61
  store i64 0, i64* %".4", !dbg !61
  %".6" = load %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %"h.addr", !dbg !62
  ret %"struct.ritz_module_1.Headers" %".6", !dbg !62
}

define i32 @"headers_add"(%"struct.ritz_module_1.Headers"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"* %"value.arg") !dbg !24
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Headers"*
  %"i.addr" = alloca i64, !dbg !73
  store %"struct.ritz_module_1.Headers"* %"self.arg", %"struct.ritz_module_1.Headers"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Headers"** %"self", metadata !64, metadata !7), !dbg !65
  %"name" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"** %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"name", metadata !68, metadata !7), !dbg !65
  %"value" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"value.arg", %"struct.ritz_module_1.Span$u8"** %"value"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"value", metadata !69, metadata !7), !dbg !65
  %".11" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !70
  %".12" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".11", i32 0, i32 1 , !dbg !70
  %".13" = load i64, i64* %".12", !dbg !70
  %".14" = icmp sge i64 %".13", 64 , !dbg !70
  br i1 %".14", label %"if.then", label %"if.end", !dbg !70
if.then:
  ret i32 0, !dbg !71
if.end:
  %".17" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !72
  %".18" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".17", i32 0, i32 1 , !dbg !72
  %".19" = load i64, i64* %".18", !dbg !72
  store i64 0, i64* %"i.addr", !dbg !73
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !74, metadata !7), !dbg !75
  br label %"while.cond", !dbg !76
while.cond:
  %".23" = load i64, i64* %"i.addr", !dbg !76
  %".24" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"name", !dbg !76
  %".25" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".24", i32 0, i32 1 , !dbg !76
  %".26" = load i64, i64* %".25", !dbg !76
  %".27" = icmp slt i64 %".23", %".26" , !dbg !76
  br i1 %".27", label %"and.right", label %"and.merge", !dbg !76
while.body:
  %".34" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"name", !dbg !77
  %".35" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".34", i32 0, i32 0 , !dbg !77
  %".36" = load i8*, i8** %".35", !dbg !77
  %".37" = load i64, i64* %"i.addr", !dbg !77
  %".38" = getelementptr i8, i8* %".36", i64 %".37" , !dbg !77
  %".39" = load i8, i8* %".38", !dbg !77
  %".40" = load i64, i64* %"i.addr", !dbg !77
  %".41" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !77
  %".42" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".41", i32 0, i32 0 , !dbg !77
  %".43" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".42", i32 0, i64 %".19" , !dbg !77
  %".44" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".43", i32 0, i32 0 , !dbg !77
  %".45" = getelementptr [128 x i8], [128 x i8]* %".44", i32 0, i64 %".40" , !dbg !77
  store i8 %".39", i8* %".45", !dbg !77
  %".47" = load i64, i64* %"i.addr", !dbg !78
  %".48" = add i64 %".47", 1, !dbg !78
  store i64 %".48", i64* %"i.addr", !dbg !78
  br label %"while.cond", !dbg !78
while.end:
  %".51" = load i64, i64* %"i.addr", !dbg !79
  %".52" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !79
  %".53" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".52", i32 0, i32 0 , !dbg !79
  %".54" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".53", i32 0, i64 %".19" , !dbg !79
  %".55" = load %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".54", !dbg !79
  %".56" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !79
  %".57" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".56", i32 0, i32 0 , !dbg !79
  %".58" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".57", i32 0, i64 %".19" , !dbg !79
  %".59" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".58", i32 0, i32 1 , !dbg !79
  store i64 %".51", i64* %".59", !dbg !79
  store i64 0, i64* %"i.addr", !dbg !80
  br label %"while.cond.1", !dbg !81
and.right:
  %".29" = load i64, i64* %"i.addr", !dbg !76
  %".30" = icmp slt i64 %".29", 128 , !dbg !76
  br label %"and.merge", !dbg !76
and.merge:
  %".32" = phi  i1 [0, %"while.cond"], [%".30", %"and.right"] , !dbg !76
  br i1 %".32", label %"while.body", label %"while.end", !dbg !76
while.cond.1:
  %".63" = load i64, i64* %"i.addr", !dbg !81
  %".64" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"value", !dbg !81
  %".65" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".64", i32 0, i32 1 , !dbg !81
  %".66" = load i64, i64* %".65", !dbg !81
  %".67" = icmp slt i64 %".63", %".66" , !dbg !81
  br i1 %".67", label %"and.right.1", label %"and.merge.1", !dbg !81
while.body.1:
  %".74" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"value", !dbg !82
  %".75" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".74", i32 0, i32 0 , !dbg !82
  %".76" = load i8*, i8** %".75", !dbg !82
  %".77" = load i64, i64* %"i.addr", !dbg !82
  %".78" = getelementptr i8, i8* %".76", i64 %".77" , !dbg !82
  %".79" = load i8, i8* %".78", !dbg !82
  %".80" = load i64, i64* %"i.addr", !dbg !82
  %".81" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !82
  %".82" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".81", i32 0, i32 0 , !dbg !82
  %".83" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".82", i32 0, i64 %".19" , !dbg !82
  %".84" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".83", i32 0, i32 2 , !dbg !82
  %".85" = getelementptr [1024 x i8], [1024 x i8]* %".84", i32 0, i64 %".80" , !dbg !82
  store i8 %".79", i8* %".85", !dbg !82
  %".87" = load i64, i64* %"i.addr", !dbg !83
  %".88" = add i64 %".87", 1, !dbg !83
  store i64 %".88", i64* %"i.addr", !dbg !83
  br label %"while.cond.1", !dbg !83
while.end.1:
  %".91" = load i64, i64* %"i.addr", !dbg !84
  %".92" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !84
  %".93" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".92", i32 0, i32 0 , !dbg !84
  %".94" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".93", i32 0, i64 %".19" , !dbg !84
  %".95" = load %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".94", !dbg !84
  %".96" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !84
  %".97" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".96", i32 0, i32 0 , !dbg !84
  %".98" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".97", i32 0, i64 %".19" , !dbg !84
  %".99" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".98", i32 0, i32 3 , !dbg !84
  store i64 %".91", i64* %".99", !dbg !84
  %".101" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !85
  %".102" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".101", i32 0, i32 1 , !dbg !85
  %".103" = load i64, i64* %".102", !dbg !85
  %".104" = add i64 %".103", 1, !dbg !85
  %".105" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !85
  %".106" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".105", i32 0, i32 1 , !dbg !85
  store i64 %".104", i64* %".106", !dbg !85
  ret i32 0, !dbg !85
and.right.1:
  %".69" = load i64, i64* %"i.addr", !dbg !81
  %".70" = icmp slt i64 %".69", 1024 , !dbg !81
  br label %"and.merge.1", !dbg !81
and.merge.1:
  %".72" = phi  i1 [0, %"while.cond.1"], [%".70", %"and.right.1"] , !dbg !81
  br i1 %".72", label %"while.body.1", label %"while.end.1", !dbg !81
}

define i32 @"headers_set"(%"struct.ritz_module_1.Headers"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"* %"value.arg") !dbg !25
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Headers"*
  store %"struct.ritz_module_1.Headers"* %"self.arg", %"struct.ritz_module_1.Headers"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Headers"** %"self", metadata !86, metadata !7), !dbg !87
  %"name" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"** %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"name", metadata !88, metadata !7), !dbg !87
  %"value" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"value.arg", %"struct.ritz_module_1.Span$u8"** %"value"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"value", metadata !89, metadata !7), !dbg !87
  %".11" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !90
  %".12" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"name", !dbg !90
  %".13" = call i32 @"headers_remove"(%"struct.ritz_module_1.Headers"* %".11", %"struct.ritz_module_1.Span$u8"* %".12"), !dbg !90
  %".14" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !91
  %".15" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"name", !dbg !91
  %".16" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"value", !dbg !91
  %".17" = call i32 @"headers_add"(%"struct.ritz_module_1.Headers"* %".14", %"struct.ritz_module_1.Span$u8"* %".15", %"struct.ritz_module_1.Span$u8"* %".16"), !dbg !91
  ret i32 %".17", !dbg !91
}

define i32 @"headers_get"(%"struct.ritz_module_1.Headers"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"* %"out_value.arg") !dbg !26
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Headers"*
  %"i.addr" = alloca i64, !dbg !96
  %"header_name.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !100
  store %"struct.ritz_module_1.Headers"* %"self.arg", %"struct.ritz_module_1.Headers"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Headers"** %"self", metadata !92, metadata !7), !dbg !93
  %"name" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"** %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"name", metadata !94, metadata !7), !dbg !93
  %"out_value" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"out_value.arg", %"struct.ritz_module_1.Span$u8"** %"out_value"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"out_value", metadata !95, metadata !7), !dbg !93
  store i64 0, i64* %"i.addr", !dbg !96
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !97, metadata !7), !dbg !98
  br label %"while.cond", !dbg !99
while.cond:
  %".14" = load i64, i64* %"i.addr", !dbg !99
  %".15" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !99
  %".16" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".15", i32 0, i32 1 , !dbg !99
  %".17" = load i64, i64* %".16", !dbg !99
  %".18" = icmp slt i64 %".14", %".17" , !dbg !99
  br i1 %".18", label %"while.body", label %"while.end", !dbg !99
while.body:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"header_name.addr", metadata !101, metadata !7), !dbg !102
  %".21" = load i64, i64* %"i.addr", !dbg !103
  %".22" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !103
  %".23" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".22", i32 0, i32 0 , !dbg !103
  %".24" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".23", i32 0, i64 %".21" , !dbg !103
  %".25" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".24", i32 0, i32 0 , !dbg !103
  %".26" = getelementptr [128 x i8], [128 x i8]* %".25", i32 0, i64 0 , !dbg !103
  %".27" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", !dbg !103
  %".28" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", i32 0, i32 0 , !dbg !103
  store i8* %".26", i8** %".28", !dbg !103
  %".30" = load i64, i64* %"i.addr", !dbg !104
  %".31" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !104
  %".32" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".31", i32 0, i32 0 , !dbg !104
  %".33" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".32", i32 0, i64 %".30" , !dbg !104
  %".34" = load %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".33", !dbg !104
  %".35" = extractvalue %"struct.ritz_module_1.Header" %".34", 1 , !dbg !104
  %".36" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", !dbg !104
  %".37" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", i32 0, i32 1 , !dbg !104
  store i64 %".35", i64* %".37", !dbg !104
  %".39" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"name", !dbg !105
  %".40" = call i32 @"header_name_eq"(%"struct.ritz_module_1.Span$u8"* %"header_name.addr", %"struct.ritz_module_1.Span$u8"* %".39"), !dbg !105
  %".41" = sext i32 %".40" to i64 , !dbg !105
  %".42" = icmp eq i64 %".41", 1 , !dbg !105
  br i1 %".42", label %"if.then", label %"if.end", !dbg !105
while.end:
  %".68" = trunc i64 0 to i32 , !dbg !110
  ret i32 %".68", !dbg !110
if.then:
  %".44" = load i64, i64* %"i.addr", !dbg !106
  %".45" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !106
  %".46" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".45", i32 0, i32 0 , !dbg !106
  %".47" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".46", i32 0, i64 %".44" , !dbg !106
  %".48" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".47", i32 0, i32 2 , !dbg !106
  %".49" = getelementptr [1024 x i8], [1024 x i8]* %".48", i32 0, i64 0 , !dbg !106
  %".50" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"out_value", !dbg !106
  %".51" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".50", i32 0, i32 0 , !dbg !106
  store i8* %".49", i8** %".51", !dbg !106
  %".53" = load i64, i64* %"i.addr", !dbg !107
  %".54" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !107
  %".55" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".54", i32 0, i32 0 , !dbg !107
  %".56" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".55", i32 0, i64 %".53" , !dbg !107
  %".57" = load %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".56", !dbg !107
  %".58" = extractvalue %"struct.ritz_module_1.Header" %".57", 3 , !dbg !107
  %".59" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"out_value", !dbg !107
  %".60" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".59", i32 0, i32 1 , !dbg !107
  store i64 %".58", i64* %".60", !dbg !107
  %".62" = trunc i64 1 to i32 , !dbg !108
  ret i32 %".62", !dbg !108
if.end:
  %".64" = load i64, i64* %"i.addr", !dbg !109
  %".65" = add i64 %".64", 1, !dbg !109
  store i64 %".65", i64* %"i.addr", !dbg !109
  br label %"while.cond", !dbg !109
}

define i32 @"headers_contains"(%"struct.ritz_module_1.Headers"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"name.arg") !dbg !27
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Headers"*
  %"i.addr" = alloca i64, !dbg !114
  %"header_name.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !118
  store %"struct.ritz_module_1.Headers"* %"self.arg", %"struct.ritz_module_1.Headers"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Headers"** %"self", metadata !111, metadata !7), !dbg !112
  %"name" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"** %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"name", metadata !113, metadata !7), !dbg !112
  store i64 0, i64* %"i.addr", !dbg !114
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !115, metadata !7), !dbg !116
  br label %"while.cond", !dbg !117
while.cond:
  %".11" = load i64, i64* %"i.addr", !dbg !117
  %".12" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !117
  %".13" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".12", i32 0, i32 1 , !dbg !117
  %".14" = load i64, i64* %".13", !dbg !117
  %".15" = icmp slt i64 %".11", %".14" , !dbg !117
  br i1 %".15", label %"while.body", label %"while.end", !dbg !117
while.body:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"header_name.addr", metadata !119, metadata !7), !dbg !120
  %".18" = load i64, i64* %"i.addr", !dbg !121
  %".19" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !121
  %".20" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".19", i32 0, i32 0 , !dbg !121
  %".21" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".20", i32 0, i64 %".18" , !dbg !121
  %".22" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".21", i32 0, i32 0 , !dbg !121
  %".23" = getelementptr [128 x i8], [128 x i8]* %".22", i32 0, i64 0 , !dbg !121
  %".24" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", !dbg !121
  %".25" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", i32 0, i32 0 , !dbg !121
  store i8* %".23", i8** %".25", !dbg !121
  %".27" = load i64, i64* %"i.addr", !dbg !122
  %".28" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !122
  %".29" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".28", i32 0, i32 0 , !dbg !122
  %".30" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".29", i32 0, i64 %".27" , !dbg !122
  %".31" = load %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".30", !dbg !122
  %".32" = extractvalue %"struct.ritz_module_1.Header" %".31", 1 , !dbg !122
  %".33" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", !dbg !122
  %".34" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", i32 0, i32 1 , !dbg !122
  store i64 %".32", i64* %".34", !dbg !122
  %".36" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"name", !dbg !123
  %".37" = call i32 @"header_name_eq"(%"struct.ritz_module_1.Span$u8"* %"header_name.addr", %"struct.ritz_module_1.Span$u8"* %".36"), !dbg !123
  %".38" = sext i32 %".37" to i64 , !dbg !123
  %".39" = icmp eq i64 %".38", 1 , !dbg !123
  br i1 %".39", label %"if.then", label %"if.end", !dbg !123
while.end:
  %".47" = trunc i64 0 to i32 , !dbg !126
  ret i32 %".47", !dbg !126
if.then:
  %".41" = trunc i64 1 to i32 , !dbg !124
  ret i32 %".41", !dbg !124
if.end:
  %".43" = load i64, i64* %"i.addr", !dbg !125
  %".44" = add i64 %".43", 1, !dbg !125
  store i64 %".44", i64* %"i.addr", !dbg !125
  br label %"while.cond", !dbg !125
}

define i32 @"headers_remove"(%"struct.ritz_module_1.Headers"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"name.arg") !dbg !28
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Headers"*
  %"write_idx.addr" = alloca i64, !dbg !130
  %"read_idx.addr" = alloca i64, !dbg !133
  %"header_name.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !137
  %"j.addr" = alloca i64, !dbg !144
  store %"struct.ritz_module_1.Headers"* %"self.arg", %"struct.ritz_module_1.Headers"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Headers"** %"self", metadata !127, metadata !7), !dbg !128
  %"name" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"** %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"name", metadata !129, metadata !7), !dbg !128
  store i64 0, i64* %"write_idx.addr", !dbg !130
  call void @"llvm.dbg.declare"(metadata i64* %"write_idx.addr", metadata !131, metadata !7), !dbg !132
  store i64 0, i64* %"read_idx.addr", !dbg !133
  call void @"llvm.dbg.declare"(metadata i64* %"read_idx.addr", metadata !134, metadata !7), !dbg !135
  br label %"while.cond", !dbg !136
while.cond:
  %".13" = load i64, i64* %"read_idx.addr", !dbg !136
  %".14" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !136
  %".15" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".14", i32 0, i32 1 , !dbg !136
  %".16" = load i64, i64* %".15", !dbg !136
  %".17" = icmp slt i64 %".13", %".16" , !dbg !136
  br i1 %".17", label %"while.body", label %"while.end", !dbg !136
while.body:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"header_name.addr", metadata !138, metadata !7), !dbg !139
  %".20" = load i64, i64* %"read_idx.addr", !dbg !140
  %".21" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !140
  %".22" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".21", i32 0, i32 0 , !dbg !140
  %".23" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".22", i32 0, i64 %".20" , !dbg !140
  %".24" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".23", i32 0, i32 0 , !dbg !140
  %".25" = getelementptr [128 x i8], [128 x i8]* %".24", i32 0, i64 0 , !dbg !140
  %".26" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", !dbg !140
  %".27" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", i32 0, i32 0 , !dbg !140
  store i8* %".25", i8** %".27", !dbg !140
  %".29" = load i64, i64* %"read_idx.addr", !dbg !141
  %".30" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !141
  %".31" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".30", i32 0, i32 0 , !dbg !141
  %".32" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".31", i32 0, i64 %".29" , !dbg !141
  %".33" = load %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".32", !dbg !141
  %".34" = extractvalue %"struct.ritz_module_1.Header" %".33", 1 , !dbg !141
  %".35" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", !dbg !141
  %".36" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", i32 0, i32 1 , !dbg !141
  store i64 %".34", i64* %".36", !dbg !141
  %".38" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"name", !dbg !142
  %".39" = call i32 @"header_name_eq"(%"struct.ritz_module_1.Span$u8"* %"header_name.addr", %"struct.ritz_module_1.Span$u8"* %".38"), !dbg !142
  %".40" = sext i32 %".39" to i64 , !dbg !142
  %".41" = icmp eq i64 %".40", 0 , !dbg !142
  br i1 %".41", label %"if.then", label %"if.end", !dbg !142
while.end:
  %".153" = load i64, i64* %"write_idx.addr", !dbg !158
  %".154" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !158
  %".155" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".154", i32 0, i32 1 , !dbg !158
  store i64 %".153", i64* %".155", !dbg !158
  ret i32 0, !dbg !158
if.then:
  %".43" = load i64, i64* %"write_idx.addr", !dbg !143
  %".44" = load i64, i64* %"read_idx.addr", !dbg !143
  %".45" = icmp ne i64 %".43", %".44" , !dbg !143
  br i1 %".45", label %"if.then.1", label %"if.end.1", !dbg !143
if.end:
  %".149" = load i64, i64* %"read_idx.addr", !dbg !157
  %".150" = add i64 %".149", 1, !dbg !157
  store i64 %".150", i64* %"read_idx.addr", !dbg !157
  br label %"while.cond", !dbg !157
if.then.1:
  store i64 0, i64* %"j.addr", !dbg !144
  call void @"llvm.dbg.declare"(metadata i64* %"j.addr", metadata !145, metadata !7), !dbg !146
  br label %"while.cond.1", !dbg !147
if.end.1:
  %".145" = load i64, i64* %"write_idx.addr", !dbg !156
  %".146" = add i64 %".145", 1, !dbg !156
  store i64 %".146", i64* %"write_idx.addr", !dbg !156
  br label %"if.end", !dbg !156
while.cond.1:
  %".50" = load i64, i64* %"j.addr", !dbg !147
  %".51" = load i64, i64* %"read_idx.addr", !dbg !147
  %".52" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !147
  %".53" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".52", i32 0, i32 0 , !dbg !147
  %".54" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".53", i32 0, i64 %".51" , !dbg !147
  %".55" = load %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".54", !dbg !147
  %".56" = extractvalue %"struct.ritz_module_1.Header" %".55", 1 , !dbg !147
  %".57" = icmp slt i64 %".50", %".56" , !dbg !147
  br i1 %".57", label %"while.body.1", label %"while.end.1", !dbg !147
while.body.1:
  %".59" = load i64, i64* %"j.addr", !dbg !148
  %".60" = load i64, i64* %"read_idx.addr", !dbg !148
  %".61" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !148
  %".62" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".61", i32 0, i32 0 , !dbg !148
  %".63" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".62", i32 0, i64 %".60" , !dbg !148
  %".64" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".63", i32 0, i32 0 , !dbg !148
  %".65" = getelementptr [128 x i8], [128 x i8]* %".64", i32 0, i64 %".59" , !dbg !148
  %".66" = load i8, i8* %".65", !dbg !148
  %".67" = load i64, i64* %"j.addr", !dbg !148
  %".68" = load i64, i64* %"write_idx.addr", !dbg !148
  %".69" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !148
  %".70" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".69", i32 0, i32 0 , !dbg !148
  %".71" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".70", i32 0, i64 %".68" , !dbg !148
  %".72" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".71", i32 0, i32 0 , !dbg !148
  %".73" = getelementptr [128 x i8], [128 x i8]* %".72", i32 0, i64 %".67" , !dbg !148
  store i8 %".66", i8* %".73", !dbg !148
  %".75" = load i64, i64* %"j.addr", !dbg !149
  %".76" = add i64 %".75", 1, !dbg !149
  store i64 %".76", i64* %"j.addr", !dbg !149
  br label %"while.cond.1", !dbg !149
while.end.1:
  %".79" = load i64, i64* %"read_idx.addr", !dbg !150
  %".80" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !150
  %".81" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".80", i32 0, i32 0 , !dbg !150
  %".82" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".81", i32 0, i64 %".79" , !dbg !150
  %".83" = load %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".82", !dbg !150
  %".84" = extractvalue %"struct.ritz_module_1.Header" %".83", 1 , !dbg !150
  %".85" = load i64, i64* %"write_idx.addr", !dbg !150
  %".86" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !150
  %".87" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".86", i32 0, i32 0 , !dbg !150
  %".88" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".87", i32 0, i64 %".85" , !dbg !150
  %".89" = load %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".88", !dbg !150
  %".90" = load i64, i64* %"write_idx.addr", !dbg !150
  %".91" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !150
  %".92" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".91", i32 0, i32 0 , !dbg !150
  %".93" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".92", i32 0, i64 %".90" , !dbg !150
  %".94" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".93", i32 0, i32 1 , !dbg !150
  store i64 %".84", i64* %".94", !dbg !150
  store i64 0, i64* %"j.addr", !dbg !151
  br label %"while.cond.2", !dbg !152
while.cond.2:
  %".98" = load i64, i64* %"j.addr", !dbg !152
  %".99" = load i64, i64* %"read_idx.addr", !dbg !152
  %".100" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !152
  %".101" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".100", i32 0, i32 0 , !dbg !152
  %".102" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".101", i32 0, i64 %".99" , !dbg !152
  %".103" = load %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".102", !dbg !152
  %".104" = extractvalue %"struct.ritz_module_1.Header" %".103", 3 , !dbg !152
  %".105" = icmp slt i64 %".98", %".104" , !dbg !152
  br i1 %".105", label %"while.body.2", label %"while.end.2", !dbg !152
while.body.2:
  %".107" = load i64, i64* %"j.addr", !dbg !153
  %".108" = load i64, i64* %"read_idx.addr", !dbg !153
  %".109" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !153
  %".110" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".109", i32 0, i32 0 , !dbg !153
  %".111" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".110", i32 0, i64 %".108" , !dbg !153
  %".112" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".111", i32 0, i32 2 , !dbg !153
  %".113" = getelementptr [1024 x i8], [1024 x i8]* %".112", i32 0, i64 %".107" , !dbg !153
  %".114" = load i8, i8* %".113", !dbg !153
  %".115" = load i64, i64* %"j.addr", !dbg !153
  %".116" = load i64, i64* %"write_idx.addr", !dbg !153
  %".117" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !153
  %".118" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".117", i32 0, i32 0 , !dbg !153
  %".119" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".118", i32 0, i64 %".116" , !dbg !153
  %".120" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".119", i32 0, i32 2 , !dbg !153
  %".121" = getelementptr [1024 x i8], [1024 x i8]* %".120", i32 0, i64 %".115" , !dbg !153
  store i8 %".114", i8* %".121", !dbg !153
  %".123" = load i64, i64* %"j.addr", !dbg !154
  %".124" = add i64 %".123", 1, !dbg !154
  store i64 %".124", i64* %"j.addr", !dbg !154
  br label %"while.cond.2", !dbg !154
while.end.2:
  %".127" = load i64, i64* %"read_idx.addr", !dbg !155
  %".128" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !155
  %".129" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".128", i32 0, i32 0 , !dbg !155
  %".130" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".129", i32 0, i64 %".127" , !dbg !155
  %".131" = load %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".130", !dbg !155
  %".132" = extractvalue %"struct.ritz_module_1.Header" %".131", 3 , !dbg !155
  %".133" = load i64, i64* %"write_idx.addr", !dbg !155
  %".134" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !155
  %".135" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".134", i32 0, i32 0 , !dbg !155
  %".136" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".135", i32 0, i64 %".133" , !dbg !155
  %".137" = load %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".136", !dbg !155
  %".138" = load i64, i64* %"write_idx.addr", !dbg !155
  %".139" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !155
  %".140" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".139", i32 0, i32 0 , !dbg !155
  %".141" = getelementptr [64 x %"struct.ritz_module_1.Header"], [64 x %"struct.ritz_module_1.Header"]* %".140", i32 0, i64 %".138" , !dbg !155
  %".142" = getelementptr %"struct.ritz_module_1.Header", %"struct.ritz_module_1.Header"* %".141", i32 0, i32 3 , !dbg !155
  store i64 %".132", i64* %".142", !dbg !155
  br label %"if.end.1", !dbg !155
}

define i64 @"headers_len"(%"struct.ritz_module_1.Headers"* %"self.arg") !dbg !29
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Headers"*
  store %"struct.ritz_module_1.Headers"* %"self.arg", %"struct.ritz_module_1.Headers"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Headers"** %"self", metadata !159, metadata !7), !dbg !160
  %".5" = load %"struct.ritz_module_1.Headers"*, %"struct.ritz_module_1.Headers"** %"self", !dbg !161
  %".6" = getelementptr %"struct.ritz_module_1.Headers", %"struct.ritz_module_1.Headers"* %".5", i32 0, i32 1 , !dbg !161
  %".7" = load i64, i64* %".6", !dbg !161
  ret i64 %".7", !dbg !161
}

define i32 @"header_name_eq"(%"struct.ritz_module_1.Span$u8"* %"a.arg", %"struct.ritz_module_1.Span$u8"* %"b.arg") !dbg !30
{
entry:
  %"a" = alloca %"struct.ritz_module_1.Span$u8"*
  %"i.addr" = alloca i64, !dbg !167
  store %"struct.ritz_module_1.Span$u8"* %"a.arg", %"struct.ritz_module_1.Span$u8"** %"a"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"a", metadata !162, metadata !7), !dbg !163
  %"b" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"b.arg", %"struct.ritz_module_1.Span$u8"** %"b"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"b", metadata !164, metadata !7), !dbg !163
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"a", !dbg !165
  %".9" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".8", i32 0, i32 1 , !dbg !165
  %".10" = load i64, i64* %".9", !dbg !165
  %".11" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"b", !dbg !165
  %".12" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".11", i32 0, i32 1 , !dbg !165
  %".13" = load i64, i64* %".12", !dbg !165
  %".14" = icmp ne i64 %".10", %".13" , !dbg !165
  br i1 %".14", label %"if.then", label %"if.end", !dbg !165
if.then:
  %".16" = trunc i64 0 to i32 , !dbg !166
  ret i32 %".16", !dbg !166
if.end:
  store i64 0, i64* %"i.addr", !dbg !167
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !168, metadata !7), !dbg !169
  br label %"while.cond", !dbg !170
while.cond:
  %".21" = load i64, i64* %"i.addr", !dbg !170
  %".22" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"a", !dbg !170
  %".23" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".22", i32 0, i32 1 , !dbg !170
  %".24" = load i64, i64* %".23", !dbg !170
  %".25" = icmp slt i64 %".21", %".24" , !dbg !170
  br i1 %".25", label %"while.body", label %"while.end", !dbg !170
while.body:
  %".27" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"a", !dbg !171
  %".28" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".27", i32 0, i32 0 , !dbg !171
  %".29" = load i8*, i8** %".28", !dbg !171
  %".30" = load i64, i64* %"i.addr", !dbg !171
  %".31" = getelementptr i8, i8* %".29", i64 %".30" , !dbg !171
  %".32" = load i8, i8* %".31", !dbg !171
  %".33" = call i8 @"to_lower"(i8 %".32"), !dbg !171
  %".34" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"b", !dbg !172
  %".35" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".34", i32 0, i32 0 , !dbg !172
  %".36" = load i8*, i8** %".35", !dbg !172
  %".37" = load i64, i64* %"i.addr", !dbg !172
  %".38" = getelementptr i8, i8* %".36", i64 %".37" , !dbg !172
  %".39" = load i8, i8* %".38", !dbg !172
  %".40" = call i8 @"to_lower"(i8 %".39"), !dbg !172
  %".41" = icmp ne i8 %".33", %".40" , !dbg !173
  br i1 %".41", label %"if.then.1", label %"if.end.1", !dbg !173
while.end:
  %".49" = trunc i64 1 to i32 , !dbg !176
  ret i32 %".49", !dbg !176
if.then.1:
  %".43" = trunc i64 0 to i32 , !dbg !174
  ret i32 %".43", !dbg !174
if.end.1:
  %".45" = load i64, i64* %"i.addr", !dbg !175
  %".46" = add i64 %".45", 1, !dbg !175
  store i64 %".46", i64* %"i.addr", !dbg !175
  br label %"while.cond", !dbg !175
}

define i8 @"to_lower"(i8 %"c.arg") !dbg !31
{
entry:
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !177, metadata !7), !dbg !178
  %".5" = load i8, i8* %"c", !dbg !179
  %".6" = zext i8 %".5" to i64 , !dbg !179
  %".7" = icmp uge i64 %".6", 65 , !dbg !179
  br i1 %".7", label %"and.right", label %"and.merge", !dbg !179
and.right:
  %".9" = load i8, i8* %"c", !dbg !179
  %".10" = zext i8 %".9" to i64 , !dbg !179
  %".11" = icmp ule i64 %".10", 90 , !dbg !179
  br label %"and.merge", !dbg !179
and.merge:
  %".13" = phi  i1 [0, %"entry"], [%".11", %"and.right"] , !dbg !179
  br i1 %".13", label %"if.then", label %"if.end", !dbg !179
if.then:
  %".15" = load i8, i8* %"c", !dbg !180
  %".16" = zext i8 %".15" to i64 , !dbg !180
  %".17" = add i64 %".16", 32, !dbg !180
  %".18" = trunc i64 %".17" to i8 , !dbg !180
  ret i8 %".18", !dbg !180
if.end:
  %".20" = load i8, i8* %"c", !dbg !181
  ret i8 %".20", !dbg !181
}

define %"struct.ritz_module_1.Span$u8" @"header_content_type"() !dbg !32
{
entry:
  %".2" = getelementptr [13 x i8], [13 x i8]* @".str.0", i64 0, i64 0 , !dbg !182
  %".3" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".2"), !dbg !182
  ret %"struct.ritz_module_1.Span$u8" %".3", !dbg !182
}

define %"struct.ritz_module_1.Span$u8" @"header_content_length"() !dbg !33
{
entry:
  %".2" = getelementptr [15 x i8], [15 x i8]* @".str.1", i64 0, i64 0 , !dbg !183
  %".3" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".2"), !dbg !183
  ret %"struct.ritz_module_1.Span$u8" %".3", !dbg !183
}

define %"struct.ritz_module_1.Span$u8" @"header_accept"() !dbg !34
{
entry:
  %".2" = getelementptr [7 x i8], [7 x i8]* @".str.2", i64 0, i64 0 , !dbg !184
  %".3" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".2"), !dbg !184
  ret %"struct.ritz_module_1.Span$u8" %".3", !dbg !184
}

define %"struct.ritz_module_1.Span$u8" @"header_authorization"() !dbg !35
{
entry:
  %".2" = getelementptr [14 x i8], [14 x i8]* @".str.3", i64 0, i64 0 , !dbg !185
  %".3" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".2"), !dbg !185
  ret %"struct.ritz_module_1.Span$u8" %".3", !dbg !185
}

define %"struct.ritz_module_1.Span$u8" @"header_cookie"() !dbg !36
{
entry:
  %".2" = getelementptr [7 x i8], [7 x i8]* @".str.4", i64 0, i64 0 , !dbg !186
  %".3" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".2"), !dbg !186
  ret %"struct.ritz_module_1.Span$u8" %".3", !dbg !186
}

define %"struct.ritz_module_1.Span$u8" @"header_set_cookie"() !dbg !37
{
entry:
  %".2" = getelementptr [11 x i8], [11 x i8]* @".str.5", i64 0, i64 0 , !dbg !187
  %".3" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".2"), !dbg !187
  ret %"struct.ritz_module_1.Span$u8" %".3", !dbg !187
}

define %"struct.ritz_module_1.Span$u8" @"header_location"() !dbg !38
{
entry:
  %".2" = getelementptr [9 x i8], [9 x i8]* @".str.6", i64 0, i64 0 , !dbg !188
  %".3" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".2"), !dbg !188
  ret %"struct.ritz_module_1.Span$u8" %".3", !dbg !188
}

define %"struct.ritz_module_1.Span$u8" @"header_host"() !dbg !39
{
entry:
  %".2" = getelementptr [5 x i8], [5 x i8]* @".str.7", i64 0, i64 0 , !dbg !189
  %".3" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".2"), !dbg !189
  ret %"struct.ritz_module_1.Span$u8" %".3", !dbg !189
}

define %"struct.ritz_module_1.Span$u8" @"header_user_agent"() !dbg !40
{
entry:
  %".2" = getelementptr [11 x i8], [11 x i8]* @".str.8", i64 0, i64 0 , !dbg !190
  %".3" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".2"), !dbg !190
  ret %"struct.ritz_module_1.Span$u8" %".3", !dbg !190
}

define %"struct.ritz_module_1.Span$u8" @"content_type_html"() !dbg !41
{
entry:
  %".2" = getelementptr [25 x i8], [25 x i8]* @".str.9", i64 0, i64 0 , !dbg !191
  %".3" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".2"), !dbg !191
  ret %"struct.ritz_module_1.Span$u8" %".3", !dbg !191
}

define %"struct.ritz_module_1.Span$u8" @"content_type_json"() !dbg !42
{
entry:
  %".2" = getelementptr [17 x i8], [17 x i8]* @".str.10", i64 0, i64 0 , !dbg !192
  %".3" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".2"), !dbg !192
  ret %"struct.ritz_module_1.Span$u8" %".3", !dbg !192
}

define %"struct.ritz_module_1.Span$u8" @"content_type_text"() !dbg !43
{
entry:
  %".2" = getelementptr [26 x i8], [26 x i8]* @".str.11", i64 0, i64 0 , !dbg !193
  %".3" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".2"), !dbg !193
  ret %"struct.ritz_module_1.Span$u8" %".3", !dbg !193
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"needed.arg") !dbg !44
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !202
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !197, metadata !7), !dbg !198
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !199, metadata !7), !dbg !198
  %".7" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !200
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", i32 0, i32 2 , !dbg !200
  %".9" = load i64, i64* %".8", !dbg !200
  %".10" = load i64, i64* %"needed", !dbg !200
  %".11" = icmp sge i64 %".9", %".10" , !dbg !200
  br i1 %".11", label %"if.then", label %"if.end", !dbg !200
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !201
  ret i32 %".13", !dbg !201
if.end:
  %".15" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !202
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".15", i32 0, i32 2 , !dbg !202
  %".17" = load i64, i64* %".16", !dbg !202
  store i64 %".17", i64* %"new_cap.addr", !dbg !202
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !203, metadata !7), !dbg !204
  %".20" = load i64, i64* %"new_cap.addr", !dbg !205
  %".21" = icmp eq i64 %".20", 0 , !dbg !205
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !205
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !206
  br label %"if.end.1", !dbg !206
if.end.1:
  br label %"while.cond", !dbg !207
while.cond:
  %".26" = load i64, i64* %"new_cap.addr", !dbg !207
  %".27" = load i64, i64* %"needed", !dbg !207
  %".28" = icmp slt i64 %".26", %".27" , !dbg !207
  br i1 %".28", label %"while.body", label %"while.end", !dbg !207
while.body:
  %".30" = load i64, i64* %"new_cap.addr", !dbg !208
  %".31" = mul i64 %".30", 2, !dbg !208
  store i64 %".31", i64* %"new_cap.addr", !dbg !208
  br label %"while.cond", !dbg !208
while.end:
  %".34" = load i64, i64* %"new_cap.addr", !dbg !209
  %".35" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %".34"), !dbg !209
  ret i32 %".35", !dbg !209
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !45
{
entry:
  %"i" = alloca i64, !dbg !215
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !210, metadata !7), !dbg !211
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !213, metadata !7), !dbg !211
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !214, metadata !7), !dbg !211
  %".10" = load i64, i64* %"len", !dbg !215
  store i64 0, i64* %"i", !dbg !215
  br label %"for.cond", !dbg !215
for.cond:
  %".13" = load i64, i64* %"i", !dbg !215
  %".14" = icmp slt i64 %".13", %".10" , !dbg !215
  br i1 %".14", label %"for.body", label %"for.end", !dbg !215
for.body:
  %".16" = load i8*, i8** %"data", !dbg !215
  %".17" = load i64, i64* %"i", !dbg !215
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !215
  %".19" = load i8, i8* %".18", !dbg !215
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8 %".19"), !dbg !215
  %".21" = sext i32 %".20" to i64 , !dbg !215
  %".22" = icmp ne i64 %".21", 0 , !dbg !215
  br i1 %".22", label %"if.then", label %"if.end", !dbg !215
for.incr:
  %".28" = load i64, i64* %"i", !dbg !216
  %".29" = add i64 %".28", 1, !dbg !216
  store i64 %".29", i64* %"i", !dbg !216
  br label %"for.cond", !dbg !216
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !217
  ret i32 %".32", !dbg !217
if.then:
  %".24" = sub i64 0, 1, !dbg !216
  %".25" = trunc i64 %".24" to i32 , !dbg !216
  ret i32 %".25", !dbg !216
if.end:
  br label %"for.incr", !dbg !216
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8 %"item.arg") !dbg !46
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !218, metadata !7), !dbg !219
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !220, metadata !7), !dbg !219
  %".7" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !221
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", i32 0, i32 1 , !dbg !221
  %".9" = load i64, i64* %".8", !dbg !221
  %".10" = add i64 %".9", 1, !dbg !221
  %".11" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %".10"), !dbg !221
  %".12" = sext i32 %".11" to i64 , !dbg !221
  %".13" = icmp ne i64 %".12", 0 , !dbg !221
  br i1 %".13", label %"if.then", label %"if.end", !dbg !221
if.then:
  %".15" = sub i64 0, 1, !dbg !222
  %".16" = trunc i64 %".15" to i32 , !dbg !222
  ret i32 %".16", !dbg !222
if.end:
  %".18" = load i8, i8* %"item", !dbg !223
  %".19" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !223
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".19", i32 0, i32 0 , !dbg !223
  %".21" = load i8*, i8** %".20", !dbg !223
  %".22" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !223
  %".23" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".22", i32 0, i32 1 , !dbg !223
  %".24" = load i64, i64* %".23", !dbg !223
  %".25" = getelementptr i8, i8* %".21", i64 %".24" , !dbg !223
  store i8 %".18", i8* %".25", !dbg !223
  %".27" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !224
  %".28" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".27", i32 0, i32 1 , !dbg !224
  %".29" = load i64, i64* %".28", !dbg !224
  %".30" = add i64 %".29", 1, !dbg !224
  %".31" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !224
  %".32" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".31", i32 0, i32 1 , !dbg !224
  store i64 %".30", i64* %".32", !dbg !224
  %".34" = trunc i64 0 to i32 , !dbg !225
  ret i32 %".34", !dbg !225
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !47
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !229, metadata !7), !dbg !230
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !232, metadata !7), !dbg !230
  %".7" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !233
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".7", i32 0, i32 1 , !dbg !233
  %".9" = load i64, i64* %".8", !dbg !233
  %".10" = add i64 %".9", 1, !dbg !233
  %".11" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %".10"), !dbg !233
  %".12" = sext i32 %".11" to i64 , !dbg !233
  %".13" = icmp ne i64 %".12", 0 , !dbg !233
  br i1 %".13", label %"if.then", label %"if.end", !dbg !233
if.then:
  %".15" = sub i64 0, 1, !dbg !234
  %".16" = trunc i64 %".15" to i32 , !dbg !234
  ret i32 %".16", !dbg !234
if.end:
  %".18" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !235
  %".19" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !235
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".19", i32 0, i32 0 , !dbg !235
  %".21" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".20", !dbg !235
  %".22" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !235
  %".23" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".22", i32 0, i32 1 , !dbg !235
  %".24" = load i64, i64* %".23", !dbg !235
  %".25" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".21", i64 %".24" , !dbg !235
  store %"struct.ritz_module_1.LineBounds" %".18", %"struct.ritz_module_1.LineBounds"* %".25", !dbg !235
  %".27" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !236
  %".28" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".27", i32 0, i32 1 , !dbg !236
  %".29" = load i64, i64* %".28", !dbg !236
  %".30" = add i64 %".29", 1, !dbg !236
  %".31" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !236
  %".32" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".31", i32 0, i32 1 , !dbg !236
  store i64 %".30", i64* %".32", !dbg !236
  %".34" = trunc i64 0 to i32 , !dbg !237
  ret i32 %".34", !dbg !237
}

define linkonce_odr i64 @"span_len$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg") !dbg !48
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !238, metadata !7), !dbg !239
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !240
  %".6" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".5", i32 0, i32 1 , !dbg !240
  %".7" = load i64, i64* %".6", !dbg !240
  ret i64 %".7", !dbg !240
}

define linkonce_odr i32 @"span_is_empty$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg") !dbg !49
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !241, metadata !7), !dbg !242
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !243
  %".6" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".5", i32 0, i32 1 , !dbg !243
  %".7" = load i64, i64* %".6", !dbg !243
  %".8" = icmp eq i64 %".7", 0 , !dbg !243
  br i1 %".8", label %"if.then", label %"if.end", !dbg !243
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !244
  ret i32 %".10", !dbg !244
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !245
  ret i32 %".12", !dbg !245
}

define linkonce_odr i8* @"span_get_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg", i64 %"idx.arg") !dbg !50
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !246, metadata !7), !dbg !247
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !248, metadata !7), !dbg !247
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !249
  %".9" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".8", i32 0, i32 0 , !dbg !249
  %".10" = load i8*, i8** %".9", !dbg !249
  %".11" = load i64, i64* %"idx", !dbg !249
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !249
  ret i8* %".12", !dbg !249
}

define linkonce_odr i8* @"span_as_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg") !dbg !51
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !250, metadata !7), !dbg !251
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !252
  %".6" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".5", i32 0, i32 0 , !dbg !252
  %".7" = load i8*, i8** %".6", !dbg !252
  ret i8* %".7", !dbg !252
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"new_cap.arg") !dbg !52
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !253, metadata !7), !dbg !254
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !255, metadata !7), !dbg !254
  %".7" = load i64, i64* %"new_cap", !dbg !256
  %".8" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !256
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".8", i32 0, i32 2 , !dbg !256
  %".10" = load i64, i64* %".9", !dbg !256
  %".11" = icmp sle i64 %".7", %".10" , !dbg !256
  br i1 %".11", label %"if.then", label %"if.end", !dbg !256
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !257
  ret i32 %".13", !dbg !257
if.end:
  %".15" = load i64, i64* %"new_cap", !dbg !258
  %".16" = mul i64 %".15", 1, !dbg !258
  %".17" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !259
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".17", i32 0, i32 0 , !dbg !259
  %".19" = load i8*, i8** %".18", !dbg !259
  %".20" = call i8* @"realloc"(i8* %".19", i64 %".16"), !dbg !259
  %".21" = icmp eq i8* %".20", null , !dbg !260
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !260
if.then.1:
  %".23" = sub i64 0, 1, !dbg !261
  %".24" = trunc i64 %".23" to i32 , !dbg !261
  ret i32 %".24", !dbg !261
if.end.1:
  %".26" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !262
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".26", i32 0, i32 0 , !dbg !262
  store i8* %".20", i8** %".27", !dbg !262
  %".29" = load i64, i64* %"new_cap", !dbg !263
  %".30" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !263
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".30", i32 0, i32 2 , !dbg !263
  store i64 %".29", i64* %".31", !dbg !263
  %".33" = trunc i64 0 to i32 , !dbg !264
  ret i32 %".33", !dbg !264
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %"needed.arg") !dbg !53
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !270
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !265, metadata !7), !dbg !266
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !267, metadata !7), !dbg !266
  %".7" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !268
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".7", i32 0, i32 2 , !dbg !268
  %".9" = load i64, i64* %".8", !dbg !268
  %".10" = load i64, i64* %"needed", !dbg !268
  %".11" = icmp sge i64 %".9", %".10" , !dbg !268
  br i1 %".11", label %"if.then", label %"if.end", !dbg !268
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !269
  ret i32 %".13", !dbg !269
if.end:
  %".15" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !270
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".15", i32 0, i32 2 , !dbg !270
  %".17" = load i64, i64* %".16", !dbg !270
  store i64 %".17", i64* %"new_cap.addr", !dbg !270
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !271, metadata !7), !dbg !272
  %".20" = load i64, i64* %"new_cap.addr", !dbg !273
  %".21" = icmp eq i64 %".20", 0 , !dbg !273
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !273
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !274
  br label %"if.end.1", !dbg !274
if.end.1:
  br label %"while.cond", !dbg !275
while.cond:
  %".26" = load i64, i64* %"new_cap.addr", !dbg !275
  %".27" = load i64, i64* %"needed", !dbg !275
  %".28" = icmp slt i64 %".26", %".27" , !dbg !275
  br i1 %".28", label %"while.body", label %"while.end", !dbg !275
while.body:
  %".30" = load i64, i64* %"new_cap.addr", !dbg !276
  %".31" = mul i64 %".30", 2, !dbg !276
  store i64 %".31", i64* %"new_cap.addr", !dbg !276
  br label %"while.cond", !dbg !276
while.end:
  %".34" = load i64, i64* %"new_cap.addr", !dbg !277
  %".35" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %".34"), !dbg !277
  ret i32 %".35", !dbg !277
}

define linkonce_odr i8 @"span_get$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg", i64 %"idx.arg") !dbg !54
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !278, metadata !7), !dbg !279
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !280, metadata !7), !dbg !279
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !281
  %".9" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".8", i32 0, i32 0 , !dbg !281
  %".10" = load i8*, i8** %".9", !dbg !281
  %".11" = load i64, i64* %"idx", !dbg !281
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !281
  %".13" = load i8, i8* %".12", !dbg !281
  ret i8 %".13", !dbg !281
}

define linkonce_odr %"struct.ritz_module_1.Span$u8" @"span_slice$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg", i64 %"start.arg", i64 %"end.arg") !dbg !55
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  %"result.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !286
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !282, metadata !7), !dbg !283
  %"start" = alloca i64
  store i64 %"start.arg", i64* %"start"
  call void @"llvm.dbg.declare"(metadata i64* %"start", metadata !284, metadata !7), !dbg !283
  %"end" = alloca i64
  store i64 %"end.arg", i64* %"end"
  call void @"llvm.dbg.declare"(metadata i64* %"end", metadata !285, metadata !7), !dbg !283
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"result.addr", metadata !287, metadata !7), !dbg !288
  %".12" = load i64, i64* %"start", !dbg !289
  %".13" = icmp slt i64 %".12", 0 , !dbg !289
  br i1 %".13", label %"if.then", label %"if.end", !dbg !289
if.then:
  store i64 0, i64* %"start", !dbg !290
  br label %"if.end", !dbg !290
if.end:
  %".17" = load i64, i64* %"end", !dbg !291
  %".18" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !291
  %".19" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".18", i32 0, i32 1 , !dbg !291
  %".20" = load i64, i64* %".19", !dbg !291
  %".21" = icmp sgt i64 %".17", %".20" , !dbg !291
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !291
if.then.1:
  %".23" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !292
  %".24" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".23", i32 0, i32 1 , !dbg !292
  %".25" = load i64, i64* %".24", !dbg !292
  store i64 %".25", i64* %"end", !dbg !292
  br label %"if.end.1", !dbg !292
if.end.1:
  %".28" = load i64, i64* %"start", !dbg !293
  %".29" = load i64, i64* %"end", !dbg !293
  %".30" = icmp sge i64 %".28", %".29" , !dbg !293
  br i1 %".30", label %"if.then.2", label %"if.end.2", !dbg !293
if.then.2:
  %".32" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !294
  %".33" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 0 , !dbg !294
  store i8* null, i8** %".33", !dbg !294
  %".35" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !295
  %".36" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 1 , !dbg !295
  store i64 0, i64* %".36", !dbg !295
  %".38" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !296
  ret %"struct.ritz_module_1.Span$u8" %".38", !dbg !296
if.end.2:
  %".40" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !297
  %".41" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".40", i32 0, i32 0 , !dbg !297
  %".42" = load i8*, i8** %".41", !dbg !297
  %".43" = load i64, i64* %"start", !dbg !297
  %".44" = getelementptr i8, i8* %".42", i64 %".43" , !dbg !297
  %".45" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !297
  %".46" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 0 , !dbg !297
  store i8* %".44", i8** %".46", !dbg !297
  %".48" = load i64, i64* %"end", !dbg !298
  %".49" = load i64, i64* %"start", !dbg !298
  %".50" = sub i64 %".48", %".49", !dbg !298
  %".51" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !298
  %".52" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 1 , !dbg !298
  store i64 %".50", i64* %".52", !dbg !298
  %".54" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !299
  ret %"struct.ritz_module_1.Span$u8" %".54", !dbg !299
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %"new_cap.arg") !dbg !56
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !300, metadata !7), !dbg !301
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !302, metadata !7), !dbg !301
  %".7" = load i64, i64* %"new_cap", !dbg !303
  %".8" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !303
  %".9" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".8", i32 0, i32 2 , !dbg !303
  %".10" = load i64, i64* %".9", !dbg !303
  %".11" = icmp sle i64 %".7", %".10" , !dbg !303
  br i1 %".11", label %"if.then", label %"if.end", !dbg !303
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !304
  ret i32 %".13", !dbg !304
if.end:
  %".15" = load i64, i64* %"new_cap", !dbg !305
  %".16" = mul i64 %".15", 16, !dbg !305
  %".17" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !306
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".17", i32 0, i32 0 , !dbg !306
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !306
  %".20" = bitcast %"struct.ritz_module_1.LineBounds"* %".19" to i8* , !dbg !306
  %".21" = call i8* @"realloc"(i8* %".20", i64 %".16"), !dbg !306
  %".22" = icmp eq i8* %".21", null , !dbg !307
  br i1 %".22", label %"if.then.1", label %"if.end.1", !dbg !307
if.then.1:
  %".24" = sub i64 0, 1, !dbg !308
  %".25" = trunc i64 %".24" to i32 , !dbg !308
  ret i32 %".25", !dbg !308
if.end.1:
  %".27" = bitcast i8* %".21" to %"struct.ritz_module_1.LineBounds"* , !dbg !309
  %".28" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !309
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".28", i32 0, i32 0 , !dbg !309
  store %"struct.ritz_module_1.LineBounds"* %".27", %"struct.ritz_module_1.LineBounds"** %".29", !dbg !309
  %".31" = load i64, i64* %"new_cap", !dbg !310
  %".32" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !310
  %".33" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".32", i32 0, i32 2 , !dbg !310
  store i64 %".31", i64* %".33", !dbg !310
  %".35" = trunc i64 0 to i32 , !dbg !311
  ret i32 %".35", !dbg !311
}

@".str.0" = private constant [13 x i8] c"Content-Type\00"
@".str.1" = private constant [15 x i8] c"Content-Length\00"
@".str.2" = private constant [7 x i8] c"Accept\00"
@".str.3" = private constant [14 x i8] c"Authorization\00"
@".str.4" = private constant [7 x i8] c"Cookie\00"
@".str.5" = private constant [11 x i8] c"Set-Cookie\00"
@".str.6" = private constant [9 x i8] c"Location\00"
@".str.7" = private constant [5 x i8] c"Host\00"
@".str.8" = private constant [11 x i8] c"User-Agent\00"
@".str.9" = private constant [25 x i8] c"text/html; charset=utf-8\00"
@".str.10" = private constant [17 x i8] c"application/json\00"
@".str.11" = private constant [26 x i8] c"text/plain; charset=utf-8\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/spire/lib/http", filename: "headers.ritz")
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
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 29, name: "headers_new", scopeLine: 29, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 35, name: "headers_add", scopeLine: 35, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 54, name: "headers_set", scopeLine: 54, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 62, name: "headers_get", scopeLine: 62, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 76, name: "headers_contains", scopeLine: 76, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 88, name: "headers_remove", scopeLine: 88, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 114, name: "headers_len", scopeLine: 114, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 118, name: "header_name_eq", scopeLine: 118, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 130, name: "to_lower", scopeLine: 130, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 139, name: "header_content_type", scopeLine: 139, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 142, name: "header_content_length", scopeLine: 142, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 145, name: "header_accept", scopeLine: 145, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "header_authorization", scopeLine: 148, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 151, name: "header_cookie", scopeLine: 151, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 154, name: "header_set_cookie", scopeLine: 154, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 157, name: "header_location", scopeLine: 157, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 160, name: "header_host", scopeLine: 160, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 163, name: "header_user_agent", scopeLine: 163, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 170, name: "content_type_html", scopeLine: 170, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 173, name: "content_type_json", scopeLine: 173, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 176, name: "content_type_text", scopeLine: 176, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 79, name: "span_len$u8", scopeLine: 79, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 83, name: "span_is_empty$u8", scopeLine: 83, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 93, name: "span_get_ptr$u8", scopeLine: 93, type: !4, unit: !1)
!51 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 97, name: "span_as_ptr$u8", scopeLine: 97, type: !4, unit: !1)
!52 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!53 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!54 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 89, name: "span_get$u8", scopeLine: 89, type: !4, unit: !1)
!55 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 105, name: "span_slice$u8", scopeLine: 105, type: !4, unit: !1)
!56 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!57 = !DILocation(column: 5, line: 30, scope: !23)
!58 = !DICompositeType(align: 64, file: !0, name: "Headers", size: 598080, tag: DW_TAG_structure_type)
!59 = !DILocalVariable(file: !0, line: 30, name: "h", scope: !23, type: !58)
!60 = !DILocation(column: 1, line: 30, scope: !23)
!61 = !DILocation(column: 5, line: 31, scope: !23)
!62 = !DILocation(column: 5, line: 32, scope: !23)
!63 = !DIDerivedType(baseType: !58, size: 64, tag: DW_TAG_pointer_type)
!64 = !DILocalVariable(file: !0, line: 35, name: "self", scope: !24, type: !63)
!65 = !DILocation(column: 1, line: 35, scope: !24)
!66 = !DICompositeType(align: 64, file: !0, name: "Span$u8", size: 128, tag: DW_TAG_structure_type)
!67 = !DIDerivedType(baseType: !66, size: 64, tag: DW_TAG_pointer_type)
!68 = !DILocalVariable(file: !0, line: 35, name: "name", scope: !24, type: !67)
!69 = !DILocalVariable(file: !0, line: 35, name: "value", scope: !24, type: !67)
!70 = !DILocation(column: 5, line: 36, scope: !24)
!71 = !DILocation(column: 9, line: 37, scope: !24)
!72 = !DILocation(column: 5, line: 38, scope: !24)
!73 = !DILocation(column: 5, line: 40, scope: !24)
!74 = !DILocalVariable(file: !0, line: 40, name: "i", scope: !24, type: !11)
!75 = !DILocation(column: 1, line: 40, scope: !24)
!76 = !DILocation(column: 5, line: 41, scope: !24)
!77 = !DILocation(column: 9, line: 42, scope: !24)
!78 = !DILocation(column: 9, line: 43, scope: !24)
!79 = !DILocation(column: 5, line: 44, scope: !24)
!80 = !DILocation(column: 5, line: 46, scope: !24)
!81 = !DILocation(column: 5, line: 47, scope: !24)
!82 = !DILocation(column: 9, line: 48, scope: !24)
!83 = !DILocation(column: 9, line: 49, scope: !24)
!84 = !DILocation(column: 5, line: 50, scope: !24)
!85 = !DILocation(column: 5, line: 51, scope: !24)
!86 = !DILocalVariable(file: !0, line: 54, name: "self", scope: !25, type: !63)
!87 = !DILocation(column: 1, line: 54, scope: !25)
!88 = !DILocalVariable(file: !0, line: 54, name: "name", scope: !25, type: !67)
!89 = !DILocalVariable(file: !0, line: 54, name: "value", scope: !25, type: !67)
!90 = !DILocation(column: 5, line: 56, scope: !25)
!91 = !DILocation(column: 5, line: 58, scope: !25)
!92 = !DILocalVariable(file: !0, line: 62, name: "self", scope: !26, type: !63)
!93 = !DILocation(column: 1, line: 62, scope: !26)
!94 = !DILocalVariable(file: !0, line: 62, name: "name", scope: !26, type: !67)
!95 = !DILocalVariable(file: !0, line: 62, name: "out_value", scope: !26, type: !67)
!96 = !DILocation(column: 5, line: 63, scope: !26)
!97 = !DILocalVariable(file: !0, line: 63, name: "i", scope: !26, type: !11)
!98 = !DILocation(column: 1, line: 63, scope: !26)
!99 = !DILocation(column: 5, line: 64, scope: !26)
!100 = !DILocation(column: 9, line: 65, scope: !26)
!101 = !DILocalVariable(file: !0, line: 65, name: "header_name", scope: !26, type: !66)
!102 = !DILocation(column: 1, line: 65, scope: !26)
!103 = !DILocation(column: 9, line: 66, scope: !26)
!104 = !DILocation(column: 9, line: 67, scope: !26)
!105 = !DILocation(column: 9, line: 68, scope: !26)
!106 = !DILocation(column: 13, line: 69, scope: !26)
!107 = !DILocation(column: 13, line: 70, scope: !26)
!108 = !DILocation(column: 13, line: 71, scope: !26)
!109 = !DILocation(column: 9, line: 72, scope: !26)
!110 = !DILocation(column: 5, line: 73, scope: !26)
!111 = !DILocalVariable(file: !0, line: 76, name: "self", scope: !27, type: !63)
!112 = !DILocation(column: 1, line: 76, scope: !27)
!113 = !DILocalVariable(file: !0, line: 76, name: "name", scope: !27, type: !67)
!114 = !DILocation(column: 5, line: 77, scope: !27)
!115 = !DILocalVariable(file: !0, line: 77, name: "i", scope: !27, type: !11)
!116 = !DILocation(column: 1, line: 77, scope: !27)
!117 = !DILocation(column: 5, line: 78, scope: !27)
!118 = !DILocation(column: 9, line: 79, scope: !27)
!119 = !DILocalVariable(file: !0, line: 79, name: "header_name", scope: !27, type: !66)
!120 = !DILocation(column: 1, line: 79, scope: !27)
!121 = !DILocation(column: 9, line: 80, scope: !27)
!122 = !DILocation(column: 9, line: 81, scope: !27)
!123 = !DILocation(column: 9, line: 82, scope: !27)
!124 = !DILocation(column: 13, line: 83, scope: !27)
!125 = !DILocation(column: 9, line: 84, scope: !27)
!126 = !DILocation(column: 5, line: 85, scope: !27)
!127 = !DILocalVariable(file: !0, line: 88, name: "self", scope: !28, type: !63)
!128 = !DILocation(column: 1, line: 88, scope: !28)
!129 = !DILocalVariable(file: !0, line: 88, name: "name", scope: !28, type: !67)
!130 = !DILocation(column: 5, line: 89, scope: !28)
!131 = !DILocalVariable(file: !0, line: 89, name: "write_idx", scope: !28, type: !11)
!132 = !DILocation(column: 1, line: 89, scope: !28)
!133 = !DILocation(column: 5, line: 90, scope: !28)
!134 = !DILocalVariable(file: !0, line: 90, name: "read_idx", scope: !28, type: !11)
!135 = !DILocation(column: 1, line: 90, scope: !28)
!136 = !DILocation(column: 5, line: 91, scope: !28)
!137 = !DILocation(column: 9, line: 92, scope: !28)
!138 = !DILocalVariable(file: !0, line: 92, name: "header_name", scope: !28, type: !66)
!139 = !DILocation(column: 1, line: 92, scope: !28)
!140 = !DILocation(column: 9, line: 93, scope: !28)
!141 = !DILocation(column: 9, line: 94, scope: !28)
!142 = !DILocation(column: 9, line: 95, scope: !28)
!143 = !DILocation(column: 13, line: 97, scope: !28)
!144 = !DILocation(column: 17, line: 99, scope: !28)
!145 = !DILocalVariable(file: !0, line: 99, name: "j", scope: !28, type: !11)
!146 = !DILocation(column: 1, line: 99, scope: !28)
!147 = !DILocation(column: 17, line: 100, scope: !28)
!148 = !DILocation(column: 21, line: 101, scope: !28)
!149 = !DILocation(column: 21, line: 102, scope: !28)
!150 = !DILocation(column: 17, line: 103, scope: !28)
!151 = !DILocation(column: 17, line: 104, scope: !28)
!152 = !DILocation(column: 17, line: 105, scope: !28)
!153 = !DILocation(column: 21, line: 106, scope: !28)
!154 = !DILocation(column: 21, line: 107, scope: !28)
!155 = !DILocation(column: 17, line: 108, scope: !28)
!156 = !DILocation(column: 13, line: 109, scope: !28)
!157 = !DILocation(column: 9, line: 110, scope: !28)
!158 = !DILocation(column: 5, line: 111, scope: !28)
!159 = !DILocalVariable(file: !0, line: 114, name: "self", scope: !29, type: !63)
!160 = !DILocation(column: 1, line: 114, scope: !29)
!161 = !DILocation(column: 5, line: 115, scope: !29)
!162 = !DILocalVariable(file: !0, line: 118, name: "a", scope: !30, type: !67)
!163 = !DILocation(column: 1, line: 118, scope: !30)
!164 = !DILocalVariable(file: !0, line: 118, name: "b", scope: !30, type: !67)
!165 = !DILocation(column: 5, line: 119, scope: !30)
!166 = !DILocation(column: 9, line: 120, scope: !30)
!167 = !DILocation(column: 5, line: 121, scope: !30)
!168 = !DILocalVariable(file: !0, line: 121, name: "i", scope: !30, type: !11)
!169 = !DILocation(column: 1, line: 121, scope: !30)
!170 = !DILocation(column: 5, line: 122, scope: !30)
!171 = !DILocation(column: 9, line: 123, scope: !30)
!172 = !DILocation(column: 9, line: 124, scope: !30)
!173 = !DILocation(column: 9, line: 125, scope: !30)
!174 = !DILocation(column: 13, line: 126, scope: !30)
!175 = !DILocation(column: 9, line: 127, scope: !30)
!176 = !DILocation(column: 5, line: 128, scope: !30)
!177 = !DILocalVariable(file: !0, line: 130, name: "c", scope: !31, type: !12)
!178 = !DILocation(column: 1, line: 130, scope: !31)
!179 = !DILocation(column: 5, line: 131, scope: !31)
!180 = !DILocation(column: 9, line: 132, scope: !31)
!181 = !DILocation(column: 5, line: 133, scope: !31)
!182 = !DILocation(column: 5, line: 140, scope: !32)
!183 = !DILocation(column: 5, line: 143, scope: !33)
!184 = !DILocation(column: 5, line: 146, scope: !34)
!185 = !DILocation(column: 5, line: 149, scope: !35)
!186 = !DILocation(column: 5, line: 152, scope: !36)
!187 = !DILocation(column: 5, line: 155, scope: !37)
!188 = !DILocation(column: 5, line: 158, scope: !38)
!189 = !DILocation(column: 5, line: 161, scope: !39)
!190 = !DILocation(column: 5, line: 164, scope: !40)
!191 = !DILocation(column: 5, line: 171, scope: !41)
!192 = !DILocation(column: 5, line: 174, scope: !42)
!193 = !DILocation(column: 5, line: 177, scope: !43)
!194 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!195 = !DIDerivedType(baseType: !194, size: 64, tag: DW_TAG_reference_type)
!196 = !DIDerivedType(baseType: !195, size: 64, tag: DW_TAG_reference_type)
!197 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !44, type: !196)
!198 = !DILocation(column: 1, line: 193, scope: !44)
!199 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !44, type: !11)
!200 = !DILocation(column: 5, line: 194, scope: !44)
!201 = !DILocation(column: 9, line: 195, scope: !44)
!202 = !DILocation(column: 5, line: 197, scope: !44)
!203 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !44, type: !11)
!204 = !DILocation(column: 1, line: 197, scope: !44)
!205 = !DILocation(column: 5, line: 198, scope: !44)
!206 = !DILocation(column: 9, line: 199, scope: !44)
!207 = !DILocation(column: 5, line: 200, scope: !44)
!208 = !DILocation(column: 9, line: 201, scope: !44)
!209 = !DILocation(column: 5, line: 203, scope: !44)
!210 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !45, type: !196)
!211 = !DILocation(column: 1, line: 288, scope: !45)
!212 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!213 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !45, type: !212)
!214 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !45, type: !11)
!215 = !DILocation(column: 5, line: 289, scope: !45)
!216 = !DILocation(column: 13, line: 291, scope: !45)
!217 = !DILocation(column: 5, line: 292, scope: !45)
!218 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !46, type: !196)
!219 = !DILocation(column: 1, line: 210, scope: !46)
!220 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !46, type: !12)
!221 = !DILocation(column: 5, line: 211, scope: !46)
!222 = !DILocation(column: 9, line: 212, scope: !46)
!223 = !DILocation(column: 5, line: 213, scope: !46)
!224 = !DILocation(column: 5, line: 214, scope: !46)
!225 = !DILocation(column: 5, line: 215, scope: !46)
!226 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!227 = !DIDerivedType(baseType: !226, size: 64, tag: DW_TAG_reference_type)
!228 = !DIDerivedType(baseType: !227, size: 64, tag: DW_TAG_reference_type)
!229 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !47, type: !228)
!230 = !DILocation(column: 1, line: 210, scope: !47)
!231 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!232 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !47, type: !231)
!233 = !DILocation(column: 5, line: 211, scope: !47)
!234 = !DILocation(column: 9, line: 212, scope: !47)
!235 = !DILocation(column: 5, line: 213, scope: !47)
!236 = !DILocation(column: 5, line: 214, scope: !47)
!237 = !DILocation(column: 5, line: 215, scope: !47)
!238 = !DILocalVariable(file: !0, line: 79, name: "s", scope: !48, type: !67)
!239 = !DILocation(column: 1, line: 79, scope: !48)
!240 = !DILocation(column: 5, line: 80, scope: !48)
!241 = !DILocalVariable(file: !0, line: 83, name: "s", scope: !49, type: !67)
!242 = !DILocation(column: 1, line: 83, scope: !49)
!243 = !DILocation(column: 5, line: 84, scope: !49)
!244 = !DILocation(column: 9, line: 85, scope: !49)
!245 = !DILocation(column: 5, line: 86, scope: !49)
!246 = !DILocalVariable(file: !0, line: 93, name: "s", scope: !50, type: !67)
!247 = !DILocation(column: 1, line: 93, scope: !50)
!248 = !DILocalVariable(file: !0, line: 93, name: "idx", scope: !50, type: !11)
!249 = !DILocation(column: 5, line: 94, scope: !50)
!250 = !DILocalVariable(file: !0, line: 97, name: "s", scope: !51, type: !67)
!251 = !DILocation(column: 1, line: 97, scope: !51)
!252 = !DILocation(column: 5, line: 98, scope: !51)
!253 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !52, type: !196)
!254 = !DILocation(column: 1, line: 179, scope: !52)
!255 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !52, type: !11)
!256 = !DILocation(column: 5, line: 180, scope: !52)
!257 = !DILocation(column: 9, line: 181, scope: !52)
!258 = !DILocation(column: 5, line: 183, scope: !52)
!259 = !DILocation(column: 5, line: 184, scope: !52)
!260 = !DILocation(column: 5, line: 185, scope: !52)
!261 = !DILocation(column: 9, line: 186, scope: !52)
!262 = !DILocation(column: 5, line: 188, scope: !52)
!263 = !DILocation(column: 5, line: 189, scope: !52)
!264 = !DILocation(column: 5, line: 190, scope: !52)
!265 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !53, type: !228)
!266 = !DILocation(column: 1, line: 193, scope: !53)
!267 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !53, type: !11)
!268 = !DILocation(column: 5, line: 194, scope: !53)
!269 = !DILocation(column: 9, line: 195, scope: !53)
!270 = !DILocation(column: 5, line: 197, scope: !53)
!271 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !53, type: !11)
!272 = !DILocation(column: 1, line: 197, scope: !53)
!273 = !DILocation(column: 5, line: 198, scope: !53)
!274 = !DILocation(column: 9, line: 199, scope: !53)
!275 = !DILocation(column: 5, line: 200, scope: !53)
!276 = !DILocation(column: 9, line: 201, scope: !53)
!277 = !DILocation(column: 5, line: 203, scope: !53)
!278 = !DILocalVariable(file: !0, line: 89, name: "s", scope: !54, type: !67)
!279 = !DILocation(column: 1, line: 89, scope: !54)
!280 = !DILocalVariable(file: !0, line: 89, name: "idx", scope: !54, type: !11)
!281 = !DILocation(column: 5, line: 90, scope: !54)
!282 = !DILocalVariable(file: !0, line: 105, name: "s", scope: !55, type: !67)
!283 = !DILocation(column: 1, line: 105, scope: !55)
!284 = !DILocalVariable(file: !0, line: 105, name: "start", scope: !55, type: !11)
!285 = !DILocalVariable(file: !0, line: 105, name: "end", scope: !55, type: !11)
!286 = !DILocation(column: 5, line: 106, scope: !55)
!287 = !DILocalVariable(file: !0, line: 106, name: "result", scope: !55, type: !66)
!288 = !DILocation(column: 1, line: 106, scope: !55)
!289 = !DILocation(column: 5, line: 107, scope: !55)
!290 = !DILocation(column: 9, line: 108, scope: !55)
!291 = !DILocation(column: 5, line: 109, scope: !55)
!292 = !DILocation(column: 9, line: 110, scope: !55)
!293 = !DILocation(column: 5, line: 111, scope: !55)
!294 = !DILocation(column: 9, line: 112, scope: !55)
!295 = !DILocation(column: 9, line: 113, scope: !55)
!296 = !DILocation(column: 9, line: 114, scope: !55)
!297 = !DILocation(column: 5, line: 115, scope: !55)
!298 = !DILocation(column: 5, line: 116, scope: !55)
!299 = !DILocation(column: 5, line: 117, scope: !55)
!300 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !56, type: !228)
!301 = !DILocation(column: 1, line: 179, scope: !56)
!302 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !56, type: !11)
!303 = !DILocation(column: 5, line: 180, scope: !56)
!304 = !DILocation(column: 9, line: 181, scope: !56)
!305 = !DILocation(column: 5, line: 183, scope: !56)
!306 = !DILocation(column: 5, line: 184, scope: !56)
!307 = !DILocation(column: 5, line: 185, scope: !56)
!308 = !DILocation(column: 9, line: 186, scope: !56)
!309 = !DILocation(column: 5, line: 188, scope: !56)
!310 = !DILocation(column: 5, line: 189, scope: !56)
!311 = !DILocation(column: 5, line: 190, scope: !56)
!312 = !DILocalVariable(file: !0, line: 208, name: "self", scope: !17, type: !67)
!313 = !DILocation(column: 1, line: 208, scope: !17)
!314 = !DILocation(column: 9, line: 209, scope: !17)
!315 = !DILocalVariable(file: !0, line: 211, name: "self", scope: !18, type: !67)
!316 = !DILocation(column: 1, line: 211, scope: !18)
!317 = !DILocation(column: 9, line: 212, scope: !18)
!318 = !DILocalVariable(file: !0, line: 214, name: "self", scope: !19, type: !67)
!319 = !DILocation(column: 1, line: 214, scope: !19)
!320 = !DILocalVariable(file: !0, line: 214, name: "idx", scope: !19, type: !11)
!321 = !DILocation(column: 9, line: 215, scope: !19)
!322 = !DILocalVariable(file: !0, line: 217, name: "self", scope: !20, type: !67)
!323 = !DILocation(column: 1, line: 217, scope: !20)
!324 = !DILocalVariable(file: !0, line: 217, name: "idx", scope: !20, type: !11)
!325 = !DILocation(column: 9, line: 218, scope: !20)
!326 = !DILocalVariable(file: !0, line: 220, name: "self", scope: !21, type: !67)
!327 = !DILocation(column: 1, line: 220, scope: !21)
!328 = !DILocation(column: 9, line: 221, scope: !21)
!329 = !DILocalVariable(file: !0, line: 223, name: "self", scope: !22, type: !67)
!330 = !DILocation(column: 1, line: 223, scope: !22)
!331 = !DILocalVariable(file: !0, line: 223, name: "start", scope: !22, type: !11)
!332 = !DILocalVariable(file: !0, line: 223, name: "end", scope: !22, type: !11)
!333 = !DILocation(column: 9, line: 224, scope: !22)