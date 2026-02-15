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
%"struct.ritz_module_1.String" = type {%"struct.ritz_module_1.Vec$u8"}
%"struct.ritz_module_1.RouteParam" = type {[64 x i8], i64, [256 x i8], i64}
%"struct.ritz_module_1.Request" = type {i32, [1024 x i8], i64, [1024 x i8], i64, [64 x %"struct.ritz_module_1.RouteParam"], i64, [16 x %"struct.ritz_module_1.RouteParam"], i64, [65536 x i8], i64}
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
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !486, metadata !7), !dbg !487
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !488
  %".6" = call i64 @"span_len$u8"(%"struct.ritz_module_1.Span$u8"* %".5"), !dbg !488
  ret i64 %".6", !dbg !488
}

define linkonce_odr i32 @"Span$u8_is_empty"(%"struct.ritz_module_1.Span$u8"* %"self.arg") !dbg !18
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !489, metadata !7), !dbg !490
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !491
  %".6" = call i32 @"span_is_empty$u8"(%"struct.ritz_module_1.Span$u8"* %".5"), !dbg !491
  ret i32 %".6", !dbg !491
}

define linkonce_odr i8 @"Span$u8_get"(%"struct.ritz_module_1.Span$u8"* %"self.arg", i64 %"idx.arg") !dbg !19
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !492, metadata !7), !dbg !493
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !494, metadata !7), !dbg !493
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !495
  %".9" = load i64, i64* %"idx", !dbg !495
  %".10" = call i8 @"span_get$u8"(%"struct.ritz_module_1.Span$u8"* %".8", i64 %".9"), !dbg !495
  ret i8 %".10", !dbg !495
}

define linkonce_odr i8* @"Span$u8_get_ptr"(%"struct.ritz_module_1.Span$u8"* %"self.arg", i64 %"idx.arg") !dbg !20
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !496, metadata !7), !dbg !497
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !498, metadata !7), !dbg !497
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !499
  %".9" = load i64, i64* %"idx", !dbg !499
  %".10" = call i8* @"span_get_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %".8", i64 %".9"), !dbg !499
  ret i8* %".10", !dbg !499
}

define linkonce_odr i8* @"Span$u8_as_ptr"(%"struct.ritz_module_1.Span$u8"* %"self.arg") !dbg !21
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !500, metadata !7), !dbg !501
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !502
  %".6" = call i8* @"span_as_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %".5"), !dbg !502
  ret i8* %".6", !dbg !502
}

define linkonce_odr %"struct.ritz_module_1.Span$u8" @"Span$u8_slice"(%"struct.ritz_module_1.Span$u8"* %"self.arg", i64 %"start.arg", i64 %"end.arg") !dbg !22
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"self.arg", %"struct.ritz_module_1.Span$u8"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"self", metadata !503, metadata !7), !dbg !504
  %"start" = alloca i64
  store i64 %"start.arg", i64* %"start"
  call void @"llvm.dbg.declare"(metadata i64* %"start", metadata !505, metadata !7), !dbg !504
  %"end" = alloca i64
  store i64 %"end.arg", i64* %"end"
  call void @"llvm.dbg.declare"(metadata i64* %"end", metadata !506, metadata !7), !dbg !504
  %".11" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"self", !dbg !507
  %".12" = load i64, i64* %"start", !dbg !507
  %".13" = load i64, i64* %"end", !dbg !507
  %".14" = call %"struct.ritz_module_1.Span$u8" @"span_slice$u8"(%"struct.ritz_module_1.Span$u8"* %".11", i64 %".12", i64 %".13"), !dbg !507
  ret %"struct.ritz_module_1.Span$u8" %".14", !dbg !507
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

define i32 @"span_contains"(%"struct.ritz_module_1.Span$u8"* %"haystack.arg", %"struct.ritz_module_1.Span$u8"* %"needle.arg") !dbg !23
{
entry:
  %"haystack" = alloca %"struct.ritz_module_1.Span$u8"*
  %"i.addr" = alloca i64, !dbg !74
  %"found.addr" = alloca i32, !dbg !78
  %"j.addr" = alloca i64, !dbg !81
  store %"struct.ritz_module_1.Span$u8"* %"haystack.arg", %"struct.ritz_module_1.Span$u8"** %"haystack"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"haystack", metadata !67, metadata !7), !dbg !68
  %"needle" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"needle.arg", %"struct.ritz_module_1.Span$u8"** %"needle"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"needle", metadata !69, metadata !7), !dbg !68
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"needle", !dbg !70
  %".9" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".8", i32 0, i32 1 , !dbg !70
  %".10" = load i64, i64* %".9", !dbg !70
  %".11" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"haystack", !dbg !70
  %".12" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".11", i32 0, i32 1 , !dbg !70
  %".13" = load i64, i64* %".12", !dbg !70
  %".14" = icmp sgt i64 %".10", %".13" , !dbg !70
  br i1 %".14", label %"if.then", label %"if.end", !dbg !70
if.then:
  %".16" = trunc i64 0 to i32 , !dbg !71
  ret i32 %".16", !dbg !71
if.end:
  %".18" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"needle", !dbg !72
  %".19" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".18", i32 0, i32 1 , !dbg !72
  %".20" = load i64, i64* %".19", !dbg !72
  %".21" = icmp eq i64 %".20", 0 , !dbg !72
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !72
if.then.1:
  %".23" = trunc i64 1 to i32 , !dbg !73
  ret i32 %".23", !dbg !73
if.end.1:
  store i64 0, i64* %"i.addr", !dbg !74
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !75, metadata !7), !dbg !76
  br label %"while.cond", !dbg !77
while.cond:
  %".28" = load i64, i64* %"i.addr", !dbg !77
  %".29" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"haystack", !dbg !77
  %".30" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".29", i32 0, i32 1 , !dbg !77
  %".31" = load i64, i64* %".30", !dbg !77
  %".32" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"needle", !dbg !77
  %".33" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".32", i32 0, i32 1 , !dbg !77
  %".34" = load i64, i64* %".33", !dbg !77
  %".35" = sub i64 %".31", %".34", !dbg !77
  %".36" = icmp sle i64 %".28", %".35" , !dbg !77
  br i1 %".36", label %"while.body", label %"while.end", !dbg !77
while.body:
  %".38" = trunc i64 1 to i32 , !dbg !78
  store i32 %".38", i32* %"found.addr", !dbg !78
  call void @"llvm.dbg.declare"(metadata i32* %"found.addr", metadata !79, metadata !7), !dbg !80
  store i64 0, i64* %"j.addr", !dbg !81
  call void @"llvm.dbg.declare"(metadata i64* %"j.addr", metadata !82, metadata !7), !dbg !83
  br label %"while.cond.1", !dbg !84
while.end:
  %".87" = trunc i64 0 to i32 , !dbg !92
  ret i32 %".87", !dbg !92
while.cond.1:
  %".44" = load i64, i64* %"j.addr", !dbg !84
  %".45" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"needle", !dbg !84
  %".46" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".45", i32 0, i32 1 , !dbg !84
  %".47" = load i64, i64* %".46", !dbg !84
  %".48" = icmp slt i64 %".44", %".47" , !dbg !84
  br i1 %".48", label %"while.body.1", label %"while.end.1", !dbg !84
while.body.1:
  %".50" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"haystack", !dbg !85
  %".51" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".50", i32 0, i32 0 , !dbg !85
  %".52" = load i8*, i8** %".51", !dbg !85
  %".53" = load i64, i64* %"i.addr", !dbg !85
  %".54" = getelementptr i8, i8* %".52", i64 %".53" , !dbg !85
  %".55" = load i64, i64* %"j.addr", !dbg !85
  %".56" = getelementptr i8, i8* %".54", i64 %".55" , !dbg !85
  %".57" = load i8, i8* %".56", !dbg !85
  %".58" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"needle", !dbg !85
  %".59" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".58", i32 0, i32 0 , !dbg !85
  %".60" = load i8*, i8** %".59", !dbg !85
  %".61" = load i64, i64* %"j.addr", !dbg !85
  %".62" = getelementptr i8, i8* %".60", i64 %".61" , !dbg !85
  %".63" = load i8, i8* %".62", !dbg !85
  %".64" = icmp ne i8 %".57", %".63" , !dbg !85
  br i1 %".64", label %"if.then.2", label %"if.end.2", !dbg !85
while.end.1:
  %".77" = load i32, i32* %"found.addr", !dbg !89
  %".78" = sext i32 %".77" to i64 , !dbg !89
  %".79" = icmp eq i64 %".78", 1 , !dbg !89
  br i1 %".79", label %"if.then.3", label %"if.end.3", !dbg !89
if.then.2:
  %".66" = trunc i64 0 to i32 , !dbg !86
  store i32 %".66", i32* %"found.addr", !dbg !86
  %".68" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"needle", !dbg !87
  %".69" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".68", i32 0, i32 1 , !dbg !87
  %".70" = load i64, i64* %".69", !dbg !87
  store i64 %".70", i64* %"j.addr", !dbg !87
  br label %"if.end.2", !dbg !87
if.end.2:
  %".73" = load i64, i64* %"j.addr", !dbg !88
  %".74" = add i64 %".73", 1, !dbg !88
  store i64 %".74", i64* %"j.addr", !dbg !88
  br label %"while.cond.1", !dbg !88
if.then.3:
  %".81" = trunc i64 1 to i32 , !dbg !90
  ret i32 %".81", !dbg !90
if.end.3:
  %".83" = load i64, i64* %"i.addr", !dbg !91
  %".84" = add i64 %".83", 1, !dbg !91
  store i64 %".84", i64* %"i.addr", !dbg !91
  br label %"while.cond", !dbg !91
}

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

define %"struct.ritz_module_1.Request" @"request_new"() !dbg !24
{
entry:
  %"req.addr" = alloca %"struct.ritz_module_1.Request", !dbg !93
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"* %"req.addr", metadata !95, metadata !7), !dbg !96
  %".3" = load %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", !dbg !97
  %".4" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", i32 0, i32 0 , !dbg !97
  store i32 1, i32* %".4", !dbg !97
  %".6" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", i32 0, i32 1 , !dbg !98
  %".7" = getelementptr [1024 x i8], [1024 x i8]* %".6", i32 0, i64 0 , !dbg !98
  %".8" = trunc i64 47 to i8 , !dbg !98
  store i8 %".8", i8* %".7", !dbg !98
  %".10" = load %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", !dbg !99
  %".11" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", i32 0, i32 2 , !dbg !99
  store i64 1, i64* %".11", !dbg !99
  %".13" = load %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", !dbg !100
  %".14" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", i32 0, i32 4 , !dbg !100
  store i64 0, i64* %".14", !dbg !100
  %".16" = load %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", !dbg !101
  %".17" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", i32 0, i32 6 , !dbg !101
  store i64 0, i64* %".17", !dbg !101
  %".19" = load %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", !dbg !102
  %".20" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", i32 0, i32 8 , !dbg !102
  store i64 0, i64* %".20", !dbg !102
  %".22" = load %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", !dbg !103
  %".23" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", i32 0, i32 10 , !dbg !103
  store i64 0, i64* %".23", !dbg !103
  %".25" = load %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", !dbg !104
  ret %"struct.ritz_module_1.Request" %".25", !dbg !104
}

define %"struct.ritz_module_1.Request" @"request_with"(i32 %"method.arg", %"struct.ritz_module_1.Span$u8"* %"path.arg") !dbg !25
{
entry:
  %"method" = alloca i32
  %"req.addr" = alloca %"struct.ritz_module_1.Request", !dbg !108
  %"i.addr" = alloca i64, !dbg !112
  store i32 %"method.arg", i32* %"method"
  call void @"llvm.dbg.declare"(metadata i32* %"method", metadata !105, metadata !7), !dbg !106
  %"path" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"path.arg", %"struct.ritz_module_1.Span$u8"** %"path"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"path", metadata !107, metadata !7), !dbg !106
  %".8" = call %"struct.ritz_module_1.Request" @"request_new"(), !dbg !108
  store %"struct.ritz_module_1.Request" %".8", %"struct.ritz_module_1.Request"* %"req.addr", !dbg !108
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"* %"req.addr", metadata !109, metadata !7), !dbg !110
  %".11" = load i32, i32* %"method", !dbg !111
  %".12" = load %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", !dbg !111
  %".13" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", i32 0, i32 0 , !dbg !111
  store i32 %".11", i32* %".13", !dbg !111
  store i64 0, i64* %"i.addr", !dbg !112
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !113, metadata !7), !dbg !114
  br label %"while.cond", !dbg !115
while.cond:
  %".18" = load i64, i64* %"i.addr", !dbg !115
  %".19" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"path", !dbg !115
  %".20" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".19", i32 0, i32 1 , !dbg !115
  %".21" = load i64, i64* %".20", !dbg !115
  %".22" = icmp slt i64 %".18", %".21" , !dbg !115
  br i1 %".22", label %"and.right", label %"and.merge", !dbg !115
while.body:
  %".29" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"path", !dbg !116
  %".30" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".29", i32 0, i32 0 , !dbg !116
  %".31" = load i8*, i8** %".30", !dbg !116
  %".32" = load i64, i64* %"i.addr", !dbg !116
  %".33" = getelementptr i8, i8* %".31", i64 %".32" , !dbg !116
  %".34" = load i8, i8* %".33", !dbg !116
  %".35" = load i64, i64* %"i.addr", !dbg !116
  %".36" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", i32 0, i32 1 , !dbg !116
  %".37" = getelementptr [1024 x i8], [1024 x i8]* %".36", i32 0, i64 %".35" , !dbg !116
  store i8 %".34", i8* %".37", !dbg !116
  %".39" = load i64, i64* %"i.addr", !dbg !117
  %".40" = add i64 %".39", 1, !dbg !117
  store i64 %".40", i64* %"i.addr", !dbg !117
  br label %"while.cond", !dbg !117
while.end:
  %".43" = load i64, i64* %"i.addr", !dbg !118
  %".44" = load %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", !dbg !118
  %".45" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", i32 0, i32 2 , !dbg !118
  store i64 %".43", i64* %".45", !dbg !118
  %".47" = load %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %"req.addr", !dbg !119
  ret %"struct.ritz_module_1.Request" %".47", !dbg !119
and.right:
  %".24" = load i64, i64* %"i.addr", !dbg !115
  %".25" = icmp slt i64 %".24", 1024 , !dbg !115
  br label %"and.merge", !dbg !115
and.merge:
  %".27" = phi  i1 [0, %"while.cond"], [%".25", %"and.right"] , !dbg !115
  br i1 %".27", label %"while.body", label %"while.end", !dbg !115
}

define i32 @"request_method"(%"struct.ritz_module_1.Request"* %"self.arg") !dbg !26
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !121, metadata !7), !dbg !122
  %".5" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !123
  %".6" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".5", i32 0, i32 0 , !dbg !123
  %".7" = load i32, i32* %".6", !dbg !123
  ret i32 %".7", !dbg !123
}

define %"struct.ritz_module_1.Span$u8" @"request_path"(%"struct.ritz_module_1.Request"* %"self.arg") !dbg !27
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  %"sp.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !126
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !124, metadata !7), !dbg !125
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"sp.addr", metadata !127, metadata !7), !dbg !128
  %".6" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !129
  %".7" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".6", i32 0, i32 1 , !dbg !129
  %".8" = getelementptr [1024 x i8], [1024 x i8]* %".7", i32 0, i64 0 , !dbg !129
  %".9" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !129
  %".10" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 0 , !dbg !129
  store i8* %".8", i8** %".10", !dbg !129
  %".12" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !130
  %".13" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".12", i32 0, i32 2 , !dbg !130
  %".14" = load i64, i64* %".13", !dbg !130
  %".15" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !130
  %".16" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 1 , !dbg !130
  store i64 %".14", i64* %".16", !dbg !130
  %".18" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !131
  ret %"struct.ritz_module_1.Span$u8" %".18", !dbg !131
}

define i32 @"request_param"(%"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"* %"out_value.arg") !dbg !28
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  %"i.addr" = alloca i64, !dbg !136
  %"param_name.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !140
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !132, metadata !7), !dbg !133
  %"name" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"** %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"name", metadata !134, metadata !7), !dbg !133
  %"out_value" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"out_value.arg", %"struct.ritz_module_1.Span$u8"** %"out_value"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"out_value", metadata !135, metadata !7), !dbg !133
  store i64 0, i64* %"i.addr", !dbg !136
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !137, metadata !7), !dbg !138
  br label %"while.cond", !dbg !139
while.cond:
  %".14" = load i64, i64* %"i.addr", !dbg !139
  %".15" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !139
  %".16" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".15", i32 0, i32 8 , !dbg !139
  %".17" = load i64, i64* %".16", !dbg !139
  %".18" = icmp slt i64 %".14", %".17" , !dbg !139
  br i1 %".18", label %"while.body", label %"while.end", !dbg !139
while.body:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"param_name.addr", metadata !141, metadata !7), !dbg !142
  %".21" = load i64, i64* %"i.addr", !dbg !143
  %".22" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !143
  %".23" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".22", i32 0, i32 7 , !dbg !143
  %".24" = getelementptr [16 x %"struct.ritz_module_1.RouteParam"], [16 x %"struct.ritz_module_1.RouteParam"]* %".23", i32 0, i64 %".21" , !dbg !143
  %".25" = getelementptr %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".24", i32 0, i32 0 , !dbg !143
  %".26" = getelementptr [64 x i8], [64 x i8]* %".25", i32 0, i64 0 , !dbg !143
  %".27" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"param_name.addr", !dbg !143
  %".28" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"param_name.addr", i32 0, i32 0 , !dbg !143
  store i8* %".26", i8** %".28", !dbg !143
  %".30" = load i64, i64* %"i.addr", !dbg !144
  %".31" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !144
  %".32" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".31", i32 0, i32 7 , !dbg !144
  %".33" = getelementptr [16 x %"struct.ritz_module_1.RouteParam"], [16 x %"struct.ritz_module_1.RouteParam"]* %".32", i32 0, i64 %".30" , !dbg !144
  %".34" = load %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".33", !dbg !144
  %".35" = extractvalue %"struct.ritz_module_1.RouteParam" %".34", 1 , !dbg !144
  %".36" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"param_name.addr", !dbg !144
  %".37" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"param_name.addr", i32 0, i32 1 , !dbg !144
  store i64 %".35", i64* %".37", !dbg !144
  %".39" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"name", !dbg !145
  %".40" = call i32 @"span_eq"(%"struct.ritz_module_1.Span$u8"* %".39", %"struct.ritz_module_1.Span$u8"* %"param_name.addr"), !dbg !145
  %".41" = sext i32 %".40" to i64 , !dbg !145
  %".42" = icmp eq i64 %".41", 1 , !dbg !145
  br i1 %".42", label %"if.then", label %"if.end", !dbg !145
while.end:
  %".68" = trunc i64 0 to i32 , !dbg !150
  ret i32 %".68", !dbg !150
if.then:
  %".44" = load i64, i64* %"i.addr", !dbg !146
  %".45" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !146
  %".46" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".45", i32 0, i32 7 , !dbg !146
  %".47" = getelementptr [16 x %"struct.ritz_module_1.RouteParam"], [16 x %"struct.ritz_module_1.RouteParam"]* %".46", i32 0, i64 %".44" , !dbg !146
  %".48" = getelementptr %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".47", i32 0, i32 2 , !dbg !146
  %".49" = getelementptr [256 x i8], [256 x i8]* %".48", i32 0, i64 0 , !dbg !146
  %".50" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"out_value", !dbg !146
  %".51" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".50", i32 0, i32 0 , !dbg !146
  store i8* %".49", i8** %".51", !dbg !146
  %".53" = load i64, i64* %"i.addr", !dbg !147
  %".54" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !147
  %".55" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".54", i32 0, i32 7 , !dbg !147
  %".56" = getelementptr [16 x %"struct.ritz_module_1.RouteParam"], [16 x %"struct.ritz_module_1.RouteParam"]* %".55", i32 0, i64 %".53" , !dbg !147
  %".57" = load %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".56", !dbg !147
  %".58" = extractvalue %"struct.ritz_module_1.RouteParam" %".57", 3 , !dbg !147
  %".59" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"out_value", !dbg !147
  %".60" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".59", i32 0, i32 1 , !dbg !147
  store i64 %".58", i64* %".60", !dbg !147
  %".62" = trunc i64 1 to i32 , !dbg !148
  ret i32 %".62", !dbg !148
if.end:
  %".64" = load i64, i64* %"i.addr", !dbg !149
  %".65" = add i64 %".64", 1, !dbg !149
  store i64 %".65", i64* %"i.addr", !dbg !149
  br label %"while.cond", !dbg !149
}

define i32 @"request_query_param"(%"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"* %"out_value.arg") !dbg !29
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !151, metadata !7), !dbg !152
  %"name" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"** %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"name", metadata !153, metadata !7), !dbg !152
  %"out_value" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"out_value.arg", %"struct.ritz_module_1.Span$u8"** %"out_value"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"out_value", metadata !154, metadata !7), !dbg !152
  %".11" = trunc i64 0 to i32 , !dbg !155
  ret i32 %".11", !dbg !155
}

define i32 @"request_header"(%"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"* %"out_value.arg") !dbg !30
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  %"i.addr" = alloca i64, !dbg !160
  %"header_name.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !164
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !156, metadata !7), !dbg !157
  %"name" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"** %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"name", metadata !158, metadata !7), !dbg !157
  %"out_value" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"out_value.arg", %"struct.ritz_module_1.Span$u8"** %"out_value"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"out_value", metadata !159, metadata !7), !dbg !157
  store i64 0, i64* %"i.addr", !dbg !160
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !161, metadata !7), !dbg !162
  br label %"while.cond", !dbg !163
while.cond:
  %".14" = load i64, i64* %"i.addr", !dbg !163
  %".15" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !163
  %".16" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".15", i32 0, i32 6 , !dbg !163
  %".17" = load i64, i64* %".16", !dbg !163
  %".18" = icmp slt i64 %".14", %".17" , !dbg !163
  br i1 %".18", label %"while.body", label %"while.end", !dbg !163
while.body:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"header_name.addr", metadata !165, metadata !7), !dbg !166
  %".21" = load i64, i64* %"i.addr", !dbg !167
  %".22" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !167
  %".23" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".22", i32 0, i32 5 , !dbg !167
  %".24" = getelementptr [64 x %"struct.ritz_module_1.RouteParam"], [64 x %"struct.ritz_module_1.RouteParam"]* %".23", i32 0, i64 %".21" , !dbg !167
  %".25" = getelementptr %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".24", i32 0, i32 0 , !dbg !167
  %".26" = getelementptr [64 x i8], [64 x i8]* %".25", i32 0, i64 0 , !dbg !167
  %".27" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", !dbg !167
  %".28" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", i32 0, i32 0 , !dbg !167
  store i8* %".26", i8** %".28", !dbg !167
  %".30" = load i64, i64* %"i.addr", !dbg !168
  %".31" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !168
  %".32" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".31", i32 0, i32 5 , !dbg !168
  %".33" = getelementptr [64 x %"struct.ritz_module_1.RouteParam"], [64 x %"struct.ritz_module_1.RouteParam"]* %".32", i32 0, i64 %".30" , !dbg !168
  %".34" = load %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".33", !dbg !168
  %".35" = extractvalue %"struct.ritz_module_1.RouteParam" %".34", 1 , !dbg !168
  %".36" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", !dbg !168
  %".37" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"header_name.addr", i32 0, i32 1 , !dbg !168
  store i64 %".35", i64* %".37", !dbg !168
  %".39" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"name", !dbg !169
  %".40" = call i32 @"span_eq_ci"(%"struct.ritz_module_1.Span$u8"* %".39", %"struct.ritz_module_1.Span$u8"* %"header_name.addr"), !dbg !169
  %".41" = sext i32 %".40" to i64 , !dbg !169
  %".42" = icmp eq i64 %".41", 1 , !dbg !169
  br i1 %".42", label %"if.then", label %"if.end", !dbg !169
while.end:
  %".68" = trunc i64 0 to i32 , !dbg !174
  ret i32 %".68", !dbg !174
if.then:
  %".44" = load i64, i64* %"i.addr", !dbg !170
  %".45" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !170
  %".46" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".45", i32 0, i32 5 , !dbg !170
  %".47" = getelementptr [64 x %"struct.ritz_module_1.RouteParam"], [64 x %"struct.ritz_module_1.RouteParam"]* %".46", i32 0, i64 %".44" , !dbg !170
  %".48" = getelementptr %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".47", i32 0, i32 2 , !dbg !170
  %".49" = getelementptr [256 x i8], [256 x i8]* %".48", i32 0, i64 0 , !dbg !170
  %".50" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"out_value", !dbg !170
  %".51" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".50", i32 0, i32 0 , !dbg !170
  store i8* %".49", i8** %".51", !dbg !170
  %".53" = load i64, i64* %"i.addr", !dbg !171
  %".54" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !171
  %".55" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".54", i32 0, i32 5 , !dbg !171
  %".56" = getelementptr [64 x %"struct.ritz_module_1.RouteParam"], [64 x %"struct.ritz_module_1.RouteParam"]* %".55", i32 0, i64 %".53" , !dbg !171
  %".57" = load %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".56", !dbg !171
  %".58" = extractvalue %"struct.ritz_module_1.RouteParam" %".57", 3 , !dbg !171
  %".59" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"out_value", !dbg !171
  %".60" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".59", i32 0, i32 1 , !dbg !171
  store i64 %".58", i64* %".60", !dbg !171
  %".62" = trunc i64 1 to i32 , !dbg !172
  ret i32 %".62", !dbg !172
if.end:
  %".64" = load i64, i64* %"i.addr", !dbg !173
  %".65" = add i64 %".64", 1, !dbg !173
  store i64 %".65", i64* %"i.addr", !dbg !173
  br label %"while.cond", !dbg !173
}

define %"struct.ritz_module_1.Span$u8" @"request_body_str"(%"struct.ritz_module_1.Request"* %"self.arg") !dbg !31
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  %"sp.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !177
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !175, metadata !7), !dbg !176
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"sp.addr", metadata !178, metadata !7), !dbg !179
  %".6" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !180
  %".7" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".6", i32 0, i32 9 , !dbg !180
  %".8" = getelementptr [65536 x i8], [65536 x i8]* %".7", i32 0, i64 0 , !dbg !180
  %".9" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !180
  %".10" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 0 , !dbg !180
  store i8* %".8", i8** %".10", !dbg !180
  %".12" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !181
  %".13" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".12", i32 0, i32 10 , !dbg !181
  %".14" = load i64, i64* %".13", !dbg !181
  %".15" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !181
  %".16" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", i32 0, i32 1 , !dbg !181
  store i64 %".14", i64* %".16", !dbg !181
  %".18" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"sp.addr", !dbg !182
  ret %"struct.ritz_module_1.Span$u8" %".18", !dbg !182
}

define i64 @"request_body_len"(%"struct.ritz_module_1.Request"* %"self.arg") !dbg !32
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !183, metadata !7), !dbg !184
  %".5" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !185
  %".6" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".5", i32 0, i32 10 , !dbg !185
  %".7" = load i64, i64* %".6", !dbg !185
  ret i64 %".7", !dbg !185
}

define i32 @"request_wants_json"(%"struct.ritz_module_1.Request"* %"self.arg") !dbg !33
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  %"accept_value.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !189
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !186, metadata !7), !dbg !187
  %".5" = getelementptr [7 x i8], [7 x i8]* @".str.0", i64 0, i64 0 , !dbg !188
  %".6" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".5"), !dbg !188
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"accept_value.addr", metadata !190, metadata !7), !dbg !191
  %".8" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !192
  %"accept_name.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !192
  store %"struct.ritz_module_1.Span$u8" %".6", %"struct.ritz_module_1.Span$u8"* %"accept_name.addr", !dbg !192
  %".10" = call i32 @"request_header"(%"struct.ritz_module_1.Request"* %".8", %"struct.ritz_module_1.Span$u8"* %"accept_name.addr", %"struct.ritz_module_1.Span$u8"* %"accept_value.addr"), !dbg !192
  %".11" = sext i32 %".10" to i64 , !dbg !192
  %".12" = icmp eq i64 %".11", 1 , !dbg !192
  br i1 %".12", label %"if.then", label %"if.end", !dbg !192
if.then:
  %".14" = getelementptr [17 x i8], [17 x i8]* @".str.1", i64 0, i64 0 , !dbg !193
  %".15" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".14"), !dbg !193
  %".16" = getelementptr [4 x i8], [4 x i8]* @".str.2", i64 0, i64 0 , !dbg !194
  %".17" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".16"), !dbg !194
  %"json_type.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !195
  store %"struct.ritz_module_1.Span$u8" %".15", %"struct.ritz_module_1.Span$u8"* %"json_type.addr", !dbg !195
  %".19" = call i32 @"span_contains"(%"struct.ritz_module_1.Span$u8"* %"accept_value.addr", %"struct.ritz_module_1.Span$u8"* %"json_type.addr"), !dbg !195
  %".20" = sext i32 %".19" to i64 , !dbg !195
  %".21" = icmp eq i64 %".20", 1 , !dbg !195
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !195
if.end:
  %".33" = trunc i64 0 to i32 , !dbg !198
  ret i32 %".33", !dbg !198
if.then.1:
  %".23" = trunc i64 1 to i32 , !dbg !196
  ret i32 %".23", !dbg !196
if.end.1:
  %"wildcard.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !196
  store %"struct.ritz_module_1.Span$u8" %".17", %"struct.ritz_module_1.Span$u8"* %"wildcard.addr", !dbg !196
  %".26" = call i32 @"span_contains"(%"struct.ritz_module_1.Span$u8"* %"accept_value.addr", %"struct.ritz_module_1.Span$u8"* %"wildcard.addr"), !dbg !196
  %".27" = sext i32 %".26" to i64 , !dbg !196
  %".28" = icmp eq i64 %".27", 1 , !dbg !196
  br i1 %".28", label %"if.then.2", label %"if.end.2", !dbg !196
if.then.2:
  %".30" = trunc i64 1 to i32 , !dbg !197
  ret i32 %".30", !dbg !197
if.end.2:
  br label %"if.end", !dbg !197
}

define i32 @"request_wants_html"(%"struct.ritz_module_1.Request"* %"self.arg") !dbg !34
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  %"accept_value.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !202
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !199, metadata !7), !dbg !200
  %".5" = getelementptr [7 x i8], [7 x i8]* @".str.3", i64 0, i64 0 , !dbg !201
  %".6" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".5"), !dbg !201
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"accept_value.addr", metadata !203, metadata !7), !dbg !204
  %".8" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !205
  %"accept_name.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !205
  store %"struct.ritz_module_1.Span$u8" %".6", %"struct.ritz_module_1.Span$u8"* %"accept_name.addr", !dbg !205
  %".10" = call i32 @"request_header"(%"struct.ritz_module_1.Request"* %".8", %"struct.ritz_module_1.Span$u8"* %"accept_name.addr", %"struct.ritz_module_1.Span$u8"* %"accept_value.addr"), !dbg !205
  %".11" = sext i32 %".10" to i64 , !dbg !205
  %".12" = icmp eq i64 %".11", 1 , !dbg !205
  br i1 %".12", label %"if.then", label %"if.end", !dbg !205
if.then:
  %".14" = getelementptr [10 x i8], [10 x i8]* @".str.4", i64 0, i64 0 , !dbg !206
  %".15" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".14"), !dbg !206
  %".16" = getelementptr [4 x i8], [4 x i8]* @".str.5", i64 0, i64 0 , !dbg !207
  %".17" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".16"), !dbg !207
  %"html_type.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !208
  store %"struct.ritz_module_1.Span$u8" %".15", %"struct.ritz_module_1.Span$u8"* %"html_type.addr", !dbg !208
  %".19" = call i32 @"span_contains"(%"struct.ritz_module_1.Span$u8"* %"accept_value.addr", %"struct.ritz_module_1.Span$u8"* %"html_type.addr"), !dbg !208
  %".20" = sext i32 %".19" to i64 , !dbg !208
  %".21" = icmp eq i64 %".20", 1 , !dbg !208
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !208
if.end:
  %".33" = trunc i64 1 to i32 , !dbg !211
  ret i32 %".33", !dbg !211
if.then.1:
  %".23" = trunc i64 1 to i32 , !dbg !209
  ret i32 %".23", !dbg !209
if.end.1:
  %"wildcard.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !209
  store %"struct.ritz_module_1.Span$u8" %".17", %"struct.ritz_module_1.Span$u8"* %"wildcard.addr", !dbg !209
  %".26" = call i32 @"span_contains"(%"struct.ritz_module_1.Span$u8"* %"accept_value.addr", %"struct.ritz_module_1.Span$u8"* %"wildcard.addr"), !dbg !209
  %".27" = sext i32 %".26" to i64 , !dbg !209
  %".28" = icmp eq i64 %".27", 1 , !dbg !209
  br i1 %".28", label %"if.then.2", label %"if.end.2", !dbg !209
if.then.2:
  %".30" = trunc i64 1 to i32 , !dbg !210
  ret i32 %".30", !dbg !210
if.end.2:
  br label %"if.end", !dbg !210
}

define i32 @"request_content_type"(%"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"out_ct.arg") !dbg !35
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !212, metadata !7), !dbg !213
  %"out_ct" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"out_ct.arg", %"struct.ritz_module_1.Span$u8"** %"out_ct"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"out_ct", metadata !214, metadata !7), !dbg !213
  %".8" = getelementptr [13 x i8], [13 x i8]* @".str.6", i64 0, i64 0 , !dbg !215
  %".9" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".8"), !dbg !215
  %".10" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !216
  %"ct_name.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !216
  store %"struct.ritz_module_1.Span$u8" %".9", %"struct.ritz_module_1.Span$u8"* %"ct_name.addr", !dbg !216
  %".12" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"out_ct", !dbg !216
  %".13" = call i32 @"request_header"(%"struct.ritz_module_1.Request"* %".10", %"struct.ritz_module_1.Span$u8"* %"ct_name.addr", %"struct.ritz_module_1.Span$u8"* %".12"), !dbg !216
  ret i32 %".13", !dbg !216
}

define i32 @"request_is_json"(%"struct.ritz_module_1.Request"* %"self.arg") !dbg !36
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  %"ct.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !219
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !217, metadata !7), !dbg !218
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"ct.addr", metadata !220, metadata !7), !dbg !221
  %".6" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !222
  %".7" = call i32 @"request_content_type"(%"struct.ritz_module_1.Request"* %".6", %"struct.ritz_module_1.Span$u8"* %"ct.addr"), !dbg !222
  %".8" = sext i32 %".7" to i64 , !dbg !222
  %".9" = icmp eq i64 %".8", 1 , !dbg !222
  br i1 %".9", label %"if.then", label %"if.end", !dbg !222
if.then:
  %".11" = getelementptr [17 x i8], [17 x i8]* @".str.7", i64 0, i64 0 , !dbg !223
  %".12" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".11"), !dbg !223
  %"json_type.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !224
  store %"struct.ritz_module_1.Span$u8" %".12", %"struct.ritz_module_1.Span$u8"* %"json_type.addr", !dbg !224
  %".14" = call i32 @"span_contains"(%"struct.ritz_module_1.Span$u8"* %"ct.addr", %"struct.ritz_module_1.Span$u8"* %"json_type.addr"), !dbg !224
  ret i32 %".14", !dbg !224
if.end:
  %".16" = trunc i64 0 to i32 , !dbg !225
  ret i32 %".16", !dbg !225
}

define i32 @"request_is_form"(%"struct.ritz_module_1.Request"* %"self.arg") !dbg !37
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  %"ct.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !228
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !226, metadata !7), !dbg !227
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"ct.addr", metadata !229, metadata !7), !dbg !230
  %".6" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !231
  %".7" = call i32 @"request_content_type"(%"struct.ritz_module_1.Request"* %".6", %"struct.ritz_module_1.Span$u8"* %"ct.addr"), !dbg !231
  %".8" = sext i32 %".7" to i64 , !dbg !231
  %".9" = icmp eq i64 %".8", 1 , !dbg !231
  br i1 %".9", label %"if.then", label %"if.end", !dbg !231
if.then:
  %".11" = getelementptr [34 x i8], [34 x i8]* @".str.8", i64 0, i64 0 , !dbg !232
  %".12" = call %"struct.ritz_module_1.Span$u8" @"span_from_cstr"(i8* %".11"), !dbg !232
  %"form_type.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !233
  store %"struct.ritz_module_1.Span$u8" %".12", %"struct.ritz_module_1.Span$u8"* %"form_type.addr", !dbg !233
  %".14" = call i32 @"span_contains"(%"struct.ritz_module_1.Span$u8"* %"ct.addr", %"struct.ritz_module_1.Span$u8"* %"form_type.addr"), !dbg !233
  ret i32 %".14", !dbg !233
if.end:
  %".16" = trunc i64 0 to i32 , !dbg !234
  ret i32 %".16", !dbg !234
}

define i32 @"request_set_method"(%"struct.ritz_module_1.Request"* %"self.arg", i32 %"method.arg") !dbg !38
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !235, metadata !7), !dbg !236
  %"method" = alloca i32
  store i32 %"method.arg", i32* %"method"
  call void @"llvm.dbg.declare"(metadata i32* %"method", metadata !237, metadata !7), !dbg !236
  %".8" = load i32, i32* %"method", !dbg !238
  %".9" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !238
  %".10" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".9", i32 0, i32 0 , !dbg !238
  store i32 %".8", i32* %".10", !dbg !238
  ret i32 0, !dbg !238
}

define i32 @"request_set_path"(%"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"path.arg") !dbg !39
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  %"i.addr" = alloca i64, !dbg !242
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !239, metadata !7), !dbg !240
  %"path" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"path.arg", %"struct.ritz_module_1.Span$u8"** %"path"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"path", metadata !241, metadata !7), !dbg !240
  store i64 0, i64* %"i.addr", !dbg !242
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !243, metadata !7), !dbg !244
  br label %"while.cond", !dbg !245
while.cond:
  %".11" = load i64, i64* %"i.addr", !dbg !245
  %".12" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"path", !dbg !245
  %".13" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".12", i32 0, i32 1 , !dbg !245
  %".14" = load i64, i64* %".13", !dbg !245
  %".15" = icmp slt i64 %".11", %".14" , !dbg !245
  br i1 %".15", label %"and.right", label %"and.merge", !dbg !245
while.body:
  %".22" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"path", !dbg !246
  %".23" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".22", i32 0, i32 0 , !dbg !246
  %".24" = load i8*, i8** %".23", !dbg !246
  %".25" = load i64, i64* %"i.addr", !dbg !246
  %".26" = getelementptr i8, i8* %".24", i64 %".25" , !dbg !246
  %".27" = load i8, i8* %".26", !dbg !246
  %".28" = load i64, i64* %"i.addr", !dbg !246
  %".29" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !246
  %".30" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".29", i32 0, i32 1 , !dbg !246
  %".31" = getelementptr [1024 x i8], [1024 x i8]* %".30", i32 0, i64 %".28" , !dbg !246
  store i8 %".27", i8* %".31", !dbg !246
  %".33" = load i64, i64* %"i.addr", !dbg !247
  %".34" = add i64 %".33", 1, !dbg !247
  store i64 %".34", i64* %"i.addr", !dbg !247
  br label %"while.cond", !dbg !247
while.end:
  %".37" = load i64, i64* %"i.addr", !dbg !248
  %".38" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !248
  %".39" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".38", i32 0, i32 2 , !dbg !248
  store i64 %".37", i64* %".39", !dbg !248
  ret i32 0, !dbg !248
and.right:
  %".17" = load i64, i64* %"i.addr", !dbg !245
  %".18" = icmp slt i64 %".17", 1024 , !dbg !245
  br label %"and.merge", !dbg !245
and.merge:
  %".20" = phi  i1 [0, %"while.cond"], [%".18", %"and.right"] , !dbg !245
  br i1 %".20", label %"while.body", label %"while.end", !dbg !245
}

define i32 @"request_set_header"(%"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"* %"value.arg") !dbg !40
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  %"i.addr" = alloca i64, !dbg !256
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !249, metadata !7), !dbg !250
  %"name" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"** %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"name", metadata !251, metadata !7), !dbg !250
  %"value" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"value.arg", %"struct.ritz_module_1.Span$u8"** %"value"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"value", metadata !252, metadata !7), !dbg !250
  %".11" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !253
  %".12" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".11", i32 0, i32 6 , !dbg !253
  %".13" = load i64, i64* %".12", !dbg !253
  %".14" = icmp sge i64 %".13", 64 , !dbg !253
  br i1 %".14", label %"if.then", label %"if.end", !dbg !253
if.then:
  ret i32 0, !dbg !254
if.end:
  %".17" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !255
  %".18" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".17", i32 0, i32 6 , !dbg !255
  %".19" = load i64, i64* %".18", !dbg !255
  store i64 0, i64* %"i.addr", !dbg !256
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !257, metadata !7), !dbg !258
  br label %"while.cond", !dbg !259
while.cond:
  %".23" = load i64, i64* %"i.addr", !dbg !259
  %".24" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"name", !dbg !259
  %".25" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".24", i32 0, i32 1 , !dbg !259
  %".26" = load i64, i64* %".25", !dbg !259
  %".27" = icmp slt i64 %".23", %".26" , !dbg !259
  br i1 %".27", label %"and.right", label %"and.merge", !dbg !259
while.body:
  %".34" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"name", !dbg !260
  %".35" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".34", i32 0, i32 0 , !dbg !260
  %".36" = load i8*, i8** %".35", !dbg !260
  %".37" = load i64, i64* %"i.addr", !dbg !260
  %".38" = getelementptr i8, i8* %".36", i64 %".37" , !dbg !260
  %".39" = load i8, i8* %".38", !dbg !260
  %".40" = load i64, i64* %"i.addr", !dbg !260
  %".41" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !260
  %".42" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".41", i32 0, i32 5 , !dbg !260
  %".43" = getelementptr [64 x %"struct.ritz_module_1.RouteParam"], [64 x %"struct.ritz_module_1.RouteParam"]* %".42", i32 0, i64 %".19" , !dbg !260
  %".44" = getelementptr %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".43", i32 0, i32 0 , !dbg !260
  %".45" = getelementptr [64 x i8], [64 x i8]* %".44", i32 0, i64 %".40" , !dbg !260
  store i8 %".39", i8* %".45", !dbg !260
  %".47" = load i64, i64* %"i.addr", !dbg !261
  %".48" = add i64 %".47", 1, !dbg !261
  store i64 %".48", i64* %"i.addr", !dbg !261
  br label %"while.cond", !dbg !261
while.end:
  %".51" = load i64, i64* %"i.addr", !dbg !262
  %".52" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !262
  %".53" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".52", i32 0, i32 5 , !dbg !262
  %".54" = getelementptr [64 x %"struct.ritz_module_1.RouteParam"], [64 x %"struct.ritz_module_1.RouteParam"]* %".53", i32 0, i64 %".19" , !dbg !262
  %".55" = load %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".54", !dbg !262
  %".56" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !262
  %".57" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".56", i32 0, i32 5 , !dbg !262
  %".58" = getelementptr [64 x %"struct.ritz_module_1.RouteParam"], [64 x %"struct.ritz_module_1.RouteParam"]* %".57", i32 0, i64 %".19" , !dbg !262
  %".59" = getelementptr %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".58", i32 0, i32 1 , !dbg !262
  store i64 %".51", i64* %".59", !dbg !262
  store i64 0, i64* %"i.addr", !dbg !263
  br label %"while.cond.1", !dbg !264
and.right:
  %".29" = load i64, i64* %"i.addr", !dbg !259
  %".30" = icmp slt i64 %".29", 64 , !dbg !259
  br label %"and.merge", !dbg !259
and.merge:
  %".32" = phi  i1 [0, %"while.cond"], [%".30", %"and.right"] , !dbg !259
  br i1 %".32", label %"while.body", label %"while.end", !dbg !259
while.cond.1:
  %".63" = load i64, i64* %"i.addr", !dbg !264
  %".64" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"value", !dbg !264
  %".65" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".64", i32 0, i32 1 , !dbg !264
  %".66" = load i64, i64* %".65", !dbg !264
  %".67" = icmp slt i64 %".63", %".66" , !dbg !264
  br i1 %".67", label %"and.right.1", label %"and.merge.1", !dbg !264
while.body.1:
  %".74" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"value", !dbg !265
  %".75" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".74", i32 0, i32 0 , !dbg !265
  %".76" = load i8*, i8** %".75", !dbg !265
  %".77" = load i64, i64* %"i.addr", !dbg !265
  %".78" = getelementptr i8, i8* %".76", i64 %".77" , !dbg !265
  %".79" = load i8, i8* %".78", !dbg !265
  %".80" = load i64, i64* %"i.addr", !dbg !265
  %".81" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !265
  %".82" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".81", i32 0, i32 5 , !dbg !265
  %".83" = getelementptr [64 x %"struct.ritz_module_1.RouteParam"], [64 x %"struct.ritz_module_1.RouteParam"]* %".82", i32 0, i64 %".19" , !dbg !265
  %".84" = getelementptr %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".83", i32 0, i32 2 , !dbg !265
  %".85" = getelementptr [256 x i8], [256 x i8]* %".84", i32 0, i64 %".80" , !dbg !265
  store i8 %".79", i8* %".85", !dbg !265
  %".87" = load i64, i64* %"i.addr", !dbg !266
  %".88" = add i64 %".87", 1, !dbg !266
  store i64 %".88", i64* %"i.addr", !dbg !266
  br label %"while.cond.1", !dbg !266
while.end.1:
  %".91" = load i64, i64* %"i.addr", !dbg !267
  %".92" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !267
  %".93" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".92", i32 0, i32 5 , !dbg !267
  %".94" = getelementptr [64 x %"struct.ritz_module_1.RouteParam"], [64 x %"struct.ritz_module_1.RouteParam"]* %".93", i32 0, i64 %".19" , !dbg !267
  %".95" = load %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".94", !dbg !267
  %".96" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !267
  %".97" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".96", i32 0, i32 5 , !dbg !267
  %".98" = getelementptr [64 x %"struct.ritz_module_1.RouteParam"], [64 x %"struct.ritz_module_1.RouteParam"]* %".97", i32 0, i64 %".19" , !dbg !267
  %".99" = getelementptr %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".98", i32 0, i32 3 , !dbg !267
  store i64 %".91", i64* %".99", !dbg !267
  %".101" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !268
  %".102" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".101", i32 0, i32 6 , !dbg !268
  %".103" = load i64, i64* %".102", !dbg !268
  %".104" = add i64 %".103", 1, !dbg !268
  %".105" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !268
  %".106" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".105", i32 0, i32 6 , !dbg !268
  store i64 %".104", i64* %".106", !dbg !268
  ret i32 0, !dbg !268
and.right.1:
  %".69" = load i64, i64* %"i.addr", !dbg !264
  %".70" = icmp slt i64 %".69", 256 , !dbg !264
  br label %"and.merge.1", !dbg !264
and.merge.1:
  %".72" = phi  i1 [0, %"while.cond.1"], [%".70", %"and.right.1"] , !dbg !264
  br i1 %".72", label %"while.body.1", label %"while.end.1", !dbg !264
}

define i32 @"request_set_param"(%"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"* %"value.arg") !dbg !41
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  %"i.addr" = alloca i64, !dbg !276
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !269, metadata !7), !dbg !270
  %"name" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"name.arg", %"struct.ritz_module_1.Span$u8"** %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"name", metadata !271, metadata !7), !dbg !270
  %"value" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"value.arg", %"struct.ritz_module_1.Span$u8"** %"value"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"value", metadata !272, metadata !7), !dbg !270
  %".11" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !273
  %".12" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".11", i32 0, i32 8 , !dbg !273
  %".13" = load i64, i64* %".12", !dbg !273
  %".14" = icmp sge i64 %".13", 16 , !dbg !273
  br i1 %".14", label %"if.then", label %"if.end", !dbg !273
if.then:
  ret i32 0, !dbg !274
if.end:
  %".17" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !275
  %".18" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".17", i32 0, i32 8 , !dbg !275
  %".19" = load i64, i64* %".18", !dbg !275
  store i64 0, i64* %"i.addr", !dbg !276
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !277, metadata !7), !dbg !278
  br label %"while.cond", !dbg !279
while.cond:
  %".23" = load i64, i64* %"i.addr", !dbg !279
  %".24" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"name", !dbg !279
  %".25" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".24", i32 0, i32 1 , !dbg !279
  %".26" = load i64, i64* %".25", !dbg !279
  %".27" = icmp slt i64 %".23", %".26" , !dbg !279
  br i1 %".27", label %"and.right", label %"and.merge", !dbg !279
while.body:
  %".34" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"name", !dbg !280
  %".35" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".34", i32 0, i32 0 , !dbg !280
  %".36" = load i8*, i8** %".35", !dbg !280
  %".37" = load i64, i64* %"i.addr", !dbg !280
  %".38" = getelementptr i8, i8* %".36", i64 %".37" , !dbg !280
  %".39" = load i8, i8* %".38", !dbg !280
  %".40" = load i64, i64* %"i.addr", !dbg !280
  %".41" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !280
  %".42" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".41", i32 0, i32 7 , !dbg !280
  %".43" = getelementptr [16 x %"struct.ritz_module_1.RouteParam"], [16 x %"struct.ritz_module_1.RouteParam"]* %".42", i32 0, i64 %".19" , !dbg !280
  %".44" = getelementptr %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".43", i32 0, i32 0 , !dbg !280
  %".45" = getelementptr [64 x i8], [64 x i8]* %".44", i32 0, i64 %".40" , !dbg !280
  store i8 %".39", i8* %".45", !dbg !280
  %".47" = load i64, i64* %"i.addr", !dbg !281
  %".48" = add i64 %".47", 1, !dbg !281
  store i64 %".48", i64* %"i.addr", !dbg !281
  br label %"while.cond", !dbg !281
while.end:
  %".51" = load i64, i64* %"i.addr", !dbg !282
  %".52" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !282
  %".53" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".52", i32 0, i32 7 , !dbg !282
  %".54" = getelementptr [16 x %"struct.ritz_module_1.RouteParam"], [16 x %"struct.ritz_module_1.RouteParam"]* %".53", i32 0, i64 %".19" , !dbg !282
  %".55" = load %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".54", !dbg !282
  %".56" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !282
  %".57" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".56", i32 0, i32 7 , !dbg !282
  %".58" = getelementptr [16 x %"struct.ritz_module_1.RouteParam"], [16 x %"struct.ritz_module_1.RouteParam"]* %".57", i32 0, i64 %".19" , !dbg !282
  %".59" = getelementptr %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".58", i32 0, i32 1 , !dbg !282
  store i64 %".51", i64* %".59", !dbg !282
  store i64 0, i64* %"i.addr", !dbg !283
  br label %"while.cond.1", !dbg !284
and.right:
  %".29" = load i64, i64* %"i.addr", !dbg !279
  %".30" = icmp slt i64 %".29", 64 , !dbg !279
  br label %"and.merge", !dbg !279
and.merge:
  %".32" = phi  i1 [0, %"while.cond"], [%".30", %"and.right"] , !dbg !279
  br i1 %".32", label %"while.body", label %"while.end", !dbg !279
while.cond.1:
  %".63" = load i64, i64* %"i.addr", !dbg !284
  %".64" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"value", !dbg !284
  %".65" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".64", i32 0, i32 1 , !dbg !284
  %".66" = load i64, i64* %".65", !dbg !284
  %".67" = icmp slt i64 %".63", %".66" , !dbg !284
  br i1 %".67", label %"and.right.1", label %"and.merge.1", !dbg !284
while.body.1:
  %".74" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"value", !dbg !285
  %".75" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".74", i32 0, i32 0 , !dbg !285
  %".76" = load i8*, i8** %".75", !dbg !285
  %".77" = load i64, i64* %"i.addr", !dbg !285
  %".78" = getelementptr i8, i8* %".76", i64 %".77" , !dbg !285
  %".79" = load i8, i8* %".78", !dbg !285
  %".80" = load i64, i64* %"i.addr", !dbg !285
  %".81" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !285
  %".82" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".81", i32 0, i32 7 , !dbg !285
  %".83" = getelementptr [16 x %"struct.ritz_module_1.RouteParam"], [16 x %"struct.ritz_module_1.RouteParam"]* %".82", i32 0, i64 %".19" , !dbg !285
  %".84" = getelementptr %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".83", i32 0, i32 2 , !dbg !285
  %".85" = getelementptr [256 x i8], [256 x i8]* %".84", i32 0, i64 %".80" , !dbg !285
  store i8 %".79", i8* %".85", !dbg !285
  %".87" = load i64, i64* %"i.addr", !dbg !286
  %".88" = add i64 %".87", 1, !dbg !286
  store i64 %".88", i64* %"i.addr", !dbg !286
  br label %"while.cond.1", !dbg !286
while.end.1:
  %".91" = load i64, i64* %"i.addr", !dbg !287
  %".92" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !287
  %".93" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".92", i32 0, i32 7 , !dbg !287
  %".94" = getelementptr [16 x %"struct.ritz_module_1.RouteParam"], [16 x %"struct.ritz_module_1.RouteParam"]* %".93", i32 0, i64 %".19" , !dbg !287
  %".95" = load %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".94", !dbg !287
  %".96" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !287
  %".97" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".96", i32 0, i32 7 , !dbg !287
  %".98" = getelementptr [16 x %"struct.ritz_module_1.RouteParam"], [16 x %"struct.ritz_module_1.RouteParam"]* %".97", i32 0, i64 %".19" , !dbg !287
  %".99" = getelementptr %"struct.ritz_module_1.RouteParam", %"struct.ritz_module_1.RouteParam"* %".98", i32 0, i32 3 , !dbg !287
  store i64 %".91", i64* %".99", !dbg !287
  %".101" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !288
  %".102" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".101", i32 0, i32 8 , !dbg !288
  %".103" = load i64, i64* %".102", !dbg !288
  %".104" = add i64 %".103", 1, !dbg !288
  %".105" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !288
  %".106" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".105", i32 0, i32 8 , !dbg !288
  store i64 %".104", i64* %".106", !dbg !288
  ret i32 0, !dbg !288
and.right.1:
  %".69" = load i64, i64* %"i.addr", !dbg !284
  %".70" = icmp slt i64 %".69", 256 , !dbg !284
  br label %"and.merge.1", !dbg !284
and.merge.1:
  %".72" = phi  i1 [0, %"while.cond.1"], [%".70", %"and.right.1"] , !dbg !284
  br i1 %".72", label %"while.body.1", label %"while.end.1", !dbg !284
}

define i32 @"request_set_body"(%"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Span$u8"* %"body.arg") !dbg !42
{
entry:
  %"self" = alloca %"struct.ritz_module_1.Request"*
  %"i.addr" = alloca i64, !dbg !292
  store %"struct.ritz_module_1.Request"* %"self.arg", %"struct.ritz_module_1.Request"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Request"** %"self", metadata !289, metadata !7), !dbg !290
  %"body" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"body.arg", %"struct.ritz_module_1.Span$u8"** %"body"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"body", metadata !291, metadata !7), !dbg !290
  store i64 0, i64* %"i.addr", !dbg !292
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !293, metadata !7), !dbg !294
  br label %"while.cond", !dbg !295
while.cond:
  %".11" = load i64, i64* %"i.addr", !dbg !295
  %".12" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"body", !dbg !295
  %".13" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".12", i32 0, i32 1 , !dbg !295
  %".14" = load i64, i64* %".13", !dbg !295
  %".15" = icmp slt i64 %".11", %".14" , !dbg !295
  br i1 %".15", label %"and.right", label %"and.merge", !dbg !295
while.body:
  %".22" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"body", !dbg !296
  %".23" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".22", i32 0, i32 0 , !dbg !296
  %".24" = load i8*, i8** %".23", !dbg !296
  %".25" = load i64, i64* %"i.addr", !dbg !296
  %".26" = getelementptr i8, i8* %".24", i64 %".25" , !dbg !296
  %".27" = load i8, i8* %".26", !dbg !296
  %".28" = load i64, i64* %"i.addr", !dbg !296
  %".29" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !296
  %".30" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".29", i32 0, i32 9 , !dbg !296
  %".31" = getelementptr [65536 x i8], [65536 x i8]* %".30", i32 0, i64 %".28" , !dbg !296
  store i8 %".27", i8* %".31", !dbg !296
  %".33" = load i64, i64* %"i.addr", !dbg !297
  %".34" = add i64 %".33", 1, !dbg !297
  store i64 %".34", i64* %"i.addr", !dbg !297
  br label %"while.cond", !dbg !297
while.end:
  %".37" = load i64, i64* %"i.addr", !dbg !298
  %".38" = load %"struct.ritz_module_1.Request"*, %"struct.ritz_module_1.Request"** %"self", !dbg !298
  %".39" = getelementptr %"struct.ritz_module_1.Request", %"struct.ritz_module_1.Request"* %".38", i32 0, i32 10 , !dbg !298
  store i64 %".37", i64* %".39", !dbg !298
  ret i32 0, !dbg !298
and.right:
  %".17" = load i64, i64* %"i.addr", !dbg !295
  %".18" = icmp slt i64 %".17", 65536 , !dbg !295
  br label %"and.merge", !dbg !295
and.merge:
  %".20" = phi  i1 [0, %"while.cond"], [%".18", %"and.right"] , !dbg !295
  br i1 %".20", label %"while.body", label %"while.end", !dbg !295
}

define i32 @"span_eq_ci"(%"struct.ritz_module_1.Span$u8"* %"a.arg", %"struct.ritz_module_1.Span$u8"* %"b.arg") !dbg !43
{
entry:
  %"a" = alloca %"struct.ritz_module_1.Span$u8"*
  %"i.addr" = alloca i64, !dbg !304
  store %"struct.ritz_module_1.Span$u8"* %"a.arg", %"struct.ritz_module_1.Span$u8"** %"a"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"a", metadata !299, metadata !7), !dbg !300
  %"b" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"b.arg", %"struct.ritz_module_1.Span$u8"** %"b"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"b", metadata !301, metadata !7), !dbg !300
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"a", !dbg !302
  %".9" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".8", i32 0, i32 1 , !dbg !302
  %".10" = load i64, i64* %".9", !dbg !302
  %".11" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"b", !dbg !302
  %".12" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".11", i32 0, i32 1 , !dbg !302
  %".13" = load i64, i64* %".12", !dbg !302
  %".14" = icmp ne i64 %".10", %".13" , !dbg !302
  br i1 %".14", label %"if.then", label %"if.end", !dbg !302
if.then:
  %".16" = trunc i64 0 to i32 , !dbg !303
  ret i32 %".16", !dbg !303
if.end:
  store i64 0, i64* %"i.addr", !dbg !304
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !305, metadata !7), !dbg !306
  br label %"while.cond", !dbg !307
while.cond:
  %".21" = load i64, i64* %"i.addr", !dbg !307
  %".22" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"a", !dbg !307
  %".23" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".22", i32 0, i32 1 , !dbg !307
  %".24" = load i64, i64* %".23", !dbg !307
  %".25" = icmp slt i64 %".21", %".24" , !dbg !307
  br i1 %".25", label %"while.body", label %"while.end", !dbg !307
while.body:
  %".27" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"a", !dbg !308
  %".28" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".27", i32 0, i32 0 , !dbg !308
  %".29" = load i8*, i8** %".28", !dbg !308
  %".30" = load i64, i64* %"i.addr", !dbg !308
  %".31" = getelementptr i8, i8* %".29", i64 %".30" , !dbg !308
  %".32" = load i8, i8* %".31", !dbg !308
  %".33" = call i8 @"to_lower"(i8 %".32"), !dbg !308
  %".34" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"b", !dbg !309
  %".35" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".34", i32 0, i32 0 , !dbg !309
  %".36" = load i8*, i8** %".35", !dbg !309
  %".37" = load i64, i64* %"i.addr", !dbg !309
  %".38" = getelementptr i8, i8* %".36", i64 %".37" , !dbg !309
  %".39" = load i8, i8* %".38", !dbg !309
  %".40" = call i8 @"to_lower"(i8 %".39"), !dbg !309
  %".41" = icmp ne i8 %".33", %".40" , !dbg !310
  br i1 %".41", label %"if.then.1", label %"if.end.1", !dbg !310
while.end:
  %".49" = trunc i64 1 to i32 , !dbg !313
  ret i32 %".49", !dbg !313
if.then.1:
  %".43" = trunc i64 0 to i32 , !dbg !311
  ret i32 %".43", !dbg !311
if.end.1:
  %".45" = load i64, i64* %"i.addr", !dbg !312
  %".46" = add i64 %".45", 1, !dbg !312
  store i64 %".46", i64* %"i.addr", !dbg !312
  br label %"while.cond", !dbg !312
}

define i8 @"to_lower"(i8 %"c.arg") !dbg !44
{
entry:
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !314, metadata !7), !dbg !315
  %".5" = load i8, i8* %"c", !dbg !316
  %".6" = zext i8 %".5" to i64 , !dbg !316
  %".7" = icmp uge i64 %".6", 65 , !dbg !316
  br i1 %".7", label %"and.right", label %"and.merge", !dbg !316
and.right:
  %".9" = load i8, i8* %"c", !dbg !316
  %".10" = zext i8 %".9" to i64 , !dbg !316
  %".11" = icmp ule i64 %".10", 90 , !dbg !316
  br label %"and.merge", !dbg !316
and.merge:
  %".13" = phi  i1 [0, %"entry"], [%".11", %"and.right"] , !dbg !316
  br i1 %".13", label %"if.then", label %"if.end", !dbg !316
if.then:
  %".15" = load i8, i8* %"c", !dbg !317
  %".16" = zext i8 %".15" to i64 , !dbg !317
  %".17" = add i64 %".16", 32, !dbg !317
  %".18" = trunc i64 %".17" to i8 , !dbg !317
  ret i8 %".18", !dbg !317
if.end:
  %".20" = load i8, i8* %"c", !dbg !318
  ret i8 %".20", !dbg !318
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !45
{
entry:
  %"i" = alloca i64, !dbg !327
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !322, metadata !7), !dbg !323
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !325, metadata !7), !dbg !323
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !326, metadata !7), !dbg !323
  %".10" = load i64, i64* %"len", !dbg !327
  store i64 0, i64* %"i", !dbg !327
  br label %"for.cond", !dbg !327
for.cond:
  %".13" = load i64, i64* %"i", !dbg !327
  %".14" = icmp slt i64 %".13", %".10" , !dbg !327
  br i1 %".14", label %"for.body", label %"for.end", !dbg !327
for.body:
  %".16" = load i8*, i8** %"data", !dbg !327
  %".17" = load i64, i64* %"i", !dbg !327
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !327
  %".19" = load i8, i8* %".18", !dbg !327
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8 %".19"), !dbg !327
  %".21" = sext i32 %".20" to i64 , !dbg !327
  %".22" = icmp ne i64 %".21", 0 , !dbg !327
  br i1 %".22", label %"if.then", label %"if.end", !dbg !327
for.incr:
  %".28" = load i64, i64* %"i", !dbg !328
  %".29" = add i64 %".28", 1, !dbg !328
  store i64 %".29", i64* %"i", !dbg !328
  br label %"for.cond", !dbg !328
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !329
  ret i32 %".32", !dbg !329
if.then:
  %".24" = sub i64 0, 1, !dbg !328
  %".25" = trunc i64 %".24" to i32 , !dbg !328
  ret i32 %".25", !dbg !328
if.end:
  br label %"for.incr", !dbg !328
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !46
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !333, metadata !7), !dbg !334
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !336, metadata !7), !dbg !334
  %".7" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !337
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".7", i32 0, i32 1 , !dbg !337
  %".9" = load i64, i64* %".8", !dbg !337
  %".10" = add i64 %".9", 1, !dbg !337
  %".11" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %".10"), !dbg !337
  %".12" = sext i32 %".11" to i64 , !dbg !337
  %".13" = icmp ne i64 %".12", 0 , !dbg !337
  br i1 %".13", label %"if.then", label %"if.end", !dbg !337
if.then:
  %".15" = sub i64 0, 1, !dbg !338
  %".16" = trunc i64 %".15" to i32 , !dbg !338
  ret i32 %".16", !dbg !338
if.end:
  %".18" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !339
  %".19" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !339
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".19", i32 0, i32 0 , !dbg !339
  %".21" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".20", !dbg !339
  %".22" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !339
  %".23" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".22", i32 0, i32 1 , !dbg !339
  %".24" = load i64, i64* %".23", !dbg !339
  %".25" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".21", i64 %".24" , !dbg !339
  store %"struct.ritz_module_1.LineBounds" %".18", %"struct.ritz_module_1.LineBounds"* %".25", !dbg !339
  %".27" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !340
  %".28" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".27", i32 0, i32 1 , !dbg !340
  %".29" = load i64, i64* %".28", !dbg !340
  %".30" = add i64 %".29", 1, !dbg !340
  %".31" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !340
  %".32" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".31", i32 0, i32 1 , !dbg !340
  store i64 %".30", i64* %".32", !dbg !340
  %".34" = trunc i64 0 to i32 , !dbg !341
  ret i32 %".34", !dbg !341
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg") !dbg !47
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !342, metadata !7), !dbg !343
  %".4" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !344
  %".5" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", i32 0, i32 0 , !dbg !344
  %".6" = load i8*, i8** %".5", !dbg !344
  %".7" = icmp ne i8* %".6", null , !dbg !344
  br i1 %".7", label %"if.then", label %"if.end", !dbg !344
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !344
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".9", i32 0, i32 0 , !dbg !344
  %".11" = load i8*, i8** %".10", !dbg !344
  %".12" = call i32 @"free"(i8* %".11"), !dbg !344
  br label %"if.end", !dbg !344
if.end:
  %".14" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !345
  %".15" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".14", i32 0, i32 0 , !dbg !345
  store i8* null, i8** %".15", !dbg !345
  %".17" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !346
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".17", i32 0, i32 1 , !dbg !346
  store i64 0, i64* %".18", !dbg !346
  %".20" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !347
  %".21" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".20", i32 0, i32 2 , !dbg !347
  store i64 0, i64* %".21", !dbg !347
  ret i32 0, !dbg !347
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg") !dbg !48
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !348, metadata !7), !dbg !349
  %".4" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !350
  %".5" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", i32 0, i32 1 , !dbg !350
  store i64 0, i64* %".5", !dbg !350
  ret i32 0, !dbg !350
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !49
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !353
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !351, metadata !7), !dbg !352
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !354, metadata !7), !dbg !355
  %".6" = load i64, i64* %"cap", !dbg !356
  %".7" = icmp sle i64 %".6", 0 , !dbg !356
  br i1 %".7", label %"if.then", label %"if.end", !dbg !356
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !357
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !357
  store i8* null, i8** %".10", !dbg !357
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !358
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !358
  store i64 0, i64* %".13", !dbg !358
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !359
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !359
  store i64 0, i64* %".16", !dbg !359
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !360
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !360
if.end:
  %".20" = load i64, i64* %"cap", !dbg !361
  %".21" = mul i64 %".20", 1, !dbg !361
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !362
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !362
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !362
  store i8* %".22", i8** %".24", !dbg !362
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !363
  %".27" = load i8*, i8** %".26", !dbg !363
  %".28" = icmp eq i8* %".27", null , !dbg !363
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !363
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !364
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !364
  store i64 0, i64* %".31", !dbg !364
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !365
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !365
  store i64 0, i64* %".34", !dbg !365
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !366
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !366
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !367
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !367
  store i64 0, i64* %".39", !dbg !367
  %".41" = load i64, i64* %"cap", !dbg !368
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !368
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !368
  store i64 %".41", i64* %".43", !dbg !368
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !369
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !369
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !50
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !370, metadata !7), !dbg !371
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !372, metadata !7), !dbg !371
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !373
  %".8" = load i8*, i8** %".7", !dbg !373
  %".9" = load i64, i64* %"idx", !dbg !373
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !373
  %".11" = load i8, i8* %".10", !dbg !373
  ret i8 %".11", !dbg !373
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg") !dbg !51
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !374, metadata !7), !dbg !375
  %".4" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !376
  %".5" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", i32 0, i32 1 , !dbg !376
  %".6" = load i64, i64* %".5", !dbg !376
  %".7" = sub i64 %".6", 1, !dbg !376
  %".8" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !376
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".8", i32 0, i32 1 , !dbg !376
  store i64 %".7", i64* %".9", !dbg !376
  %".11" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !377
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".11", i32 0, i32 0 , !dbg !377
  %".13" = load i8*, i8** %".12", !dbg !377
  %".14" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !377
  %".15" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".14", i32 0, i32 1 , !dbg !377
  %".16" = load i64, i64* %".15", !dbg !377
  %".17" = getelementptr i8, i8* %".13", i64 %".16" , !dbg !377
  %".18" = load i8, i8* %".17", !dbg !377
  ret i8 %".18", !dbg !377
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"needed.arg") !dbg !52
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !383
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !378, metadata !7), !dbg !379
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !380, metadata !7), !dbg !379
  %".7" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !381
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", i32 0, i32 2 , !dbg !381
  %".9" = load i64, i64* %".8", !dbg !381
  %".10" = load i64, i64* %"needed", !dbg !381
  %".11" = icmp sge i64 %".9", %".10" , !dbg !381
  br i1 %".11", label %"if.then", label %"if.end", !dbg !381
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !382
  ret i32 %".13", !dbg !382
if.end:
  %".15" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !383
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".15", i32 0, i32 2 , !dbg !383
  %".17" = load i64, i64* %".16", !dbg !383
  store i64 %".17", i64* %"new_cap.addr", !dbg !383
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !384, metadata !7), !dbg !385
  %".20" = load i64, i64* %"new_cap.addr", !dbg !386
  %".21" = icmp eq i64 %".20", 0 , !dbg !386
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !386
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !387
  br label %"if.end.1", !dbg !387
if.end.1:
  br label %"while.cond", !dbg !388
while.cond:
  %".26" = load i64, i64* %"new_cap.addr", !dbg !388
  %".27" = load i64, i64* %"needed", !dbg !388
  %".28" = icmp slt i64 %".26", %".27" , !dbg !388
  br i1 %".28", label %"while.body", label %"while.end", !dbg !388
while.body:
  %".30" = load i64, i64* %"new_cap.addr", !dbg !389
  %".31" = mul i64 %".30", 2, !dbg !389
  store i64 %".31", i64* %"new_cap.addr", !dbg !389
  br label %"while.cond", !dbg !389
while.end:
  %".34" = load i64, i64* %"new_cap.addr", !dbg !390
  %".35" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %".34"), !dbg !390
  ret i32 %".35", !dbg !390
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !53
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !391
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !392, metadata !7), !dbg !393
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !394
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !394
  store i8* null, i8** %".4", !dbg !394
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !395
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !395
  store i64 0, i64* %".7", !dbg !395
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !396
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !396
  store i64 0, i64* %".10", !dbg !396
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !397
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !397
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !54
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !398, metadata !7), !dbg !399
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !400, metadata !7), !dbg !399
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !401, metadata !7), !dbg !399
  %".10" = load i8, i8* %"item", !dbg !402
  %".11" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !402
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".11", i32 0, i32 0 , !dbg !402
  %".13" = load i8*, i8** %".12", !dbg !402
  %".14" = load i64, i64* %"idx", !dbg !402
  %".15" = getelementptr i8, i8* %".13", i64 %".14" , !dbg !402
  store i8 %".10", i8* %".15", !dbg !402
  %".17" = trunc i64 0 to i32 , !dbg !403
  ret i32 %".17", !dbg !403
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8 %"item.arg") !dbg !55
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !404, metadata !7), !dbg !405
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !406, metadata !7), !dbg !405
  %".7" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !407
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", i32 0, i32 1 , !dbg !407
  %".9" = load i64, i64* %".8", !dbg !407
  %".10" = add i64 %".9", 1, !dbg !407
  %".11" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %".10"), !dbg !407
  %".12" = sext i32 %".11" to i64 , !dbg !407
  %".13" = icmp ne i64 %".12", 0 , !dbg !407
  br i1 %".13", label %"if.then", label %"if.end", !dbg !407
if.then:
  %".15" = sub i64 0, 1, !dbg !408
  %".16" = trunc i64 %".15" to i32 , !dbg !408
  ret i32 %".16", !dbg !408
if.end:
  %".18" = load i8, i8* %"item", !dbg !409
  %".19" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !409
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".19", i32 0, i32 0 , !dbg !409
  %".21" = load i8*, i8** %".20", !dbg !409
  %".22" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !409
  %".23" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".22", i32 0, i32 1 , !dbg !409
  %".24" = load i64, i64* %".23", !dbg !409
  %".25" = getelementptr i8, i8* %".21", i64 %".24" , !dbg !409
  store i8 %".18", i8* %".25", !dbg !409
  %".27" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !410
  %".28" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".27", i32 0, i32 1 , !dbg !410
  %".29" = load i64, i64* %".28", !dbg !410
  %".30" = add i64 %".29", 1, !dbg !410
  %".31" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !410
  %".32" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".31", i32 0, i32 1 , !dbg !410
  store i64 %".30", i64* %".32", !dbg !410
  %".34" = trunc i64 0 to i32 , !dbg !411
  ret i32 %".34", !dbg !411
}

define linkonce_odr i64 @"span_len$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg") !dbg !56
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !412, metadata !7), !dbg !413
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !414
  %".6" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".5", i32 0, i32 1 , !dbg !414
  %".7" = load i64, i64* %".6", !dbg !414
  ret i64 %".7", !dbg !414
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %"needed.arg") !dbg !57
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !420
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !415, metadata !7), !dbg !416
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !417, metadata !7), !dbg !416
  %".7" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !418
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".7", i32 0, i32 2 , !dbg !418
  %".9" = load i64, i64* %".8", !dbg !418
  %".10" = load i64, i64* %"needed", !dbg !418
  %".11" = icmp sge i64 %".9", %".10" , !dbg !418
  br i1 %".11", label %"if.then", label %"if.end", !dbg !418
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !419
  ret i32 %".13", !dbg !419
if.end:
  %".15" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !420
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".15", i32 0, i32 2 , !dbg !420
  %".17" = load i64, i64* %".16", !dbg !420
  store i64 %".17", i64* %"new_cap.addr", !dbg !420
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !421, metadata !7), !dbg !422
  %".20" = load i64, i64* %"new_cap.addr", !dbg !423
  %".21" = icmp eq i64 %".20", 0 , !dbg !423
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !423
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !424
  br label %"if.end.1", !dbg !424
if.end.1:
  br label %"while.cond", !dbg !425
while.cond:
  %".26" = load i64, i64* %"new_cap.addr", !dbg !425
  %".27" = load i64, i64* %"needed", !dbg !425
  %".28" = icmp slt i64 %".26", %".27" , !dbg !425
  br i1 %".28", label %"while.body", label %"while.end", !dbg !425
while.body:
  %".30" = load i64, i64* %"new_cap.addr", !dbg !426
  %".31" = mul i64 %".30", 2, !dbg !426
  store i64 %".31", i64* %"new_cap.addr", !dbg !426
  br label %"while.cond", !dbg !426
while.end:
  %".34" = load i64, i64* %"new_cap.addr", !dbg !427
  %".35" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %".34"), !dbg !427
  ret i32 %".35", !dbg !427
}

define linkonce_odr i8* @"span_as_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg") !dbg !58
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !428, metadata !7), !dbg !429
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !430
  %".6" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".5", i32 0, i32 0 , !dbg !430
  %".7" = load i8*, i8** %".6", !dbg !430
  ret i8* %".7", !dbg !430
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"new_cap.arg") !dbg !59
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !431, metadata !7), !dbg !432
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !433, metadata !7), !dbg !432
  %".7" = load i64, i64* %"new_cap", !dbg !434
  %".8" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !434
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".8", i32 0, i32 2 , !dbg !434
  %".10" = load i64, i64* %".9", !dbg !434
  %".11" = icmp sle i64 %".7", %".10" , !dbg !434
  br i1 %".11", label %"if.then", label %"if.end", !dbg !434
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !435
  ret i32 %".13", !dbg !435
if.end:
  %".15" = load i64, i64* %"new_cap", !dbg !436
  %".16" = mul i64 %".15", 1, !dbg !436
  %".17" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !437
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".17", i32 0, i32 0 , !dbg !437
  %".19" = load i8*, i8** %".18", !dbg !437
  %".20" = call i8* @"realloc"(i8* %".19", i64 %".16"), !dbg !437
  %".21" = icmp eq i8* %".20", null , !dbg !438
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !438
if.then.1:
  %".23" = sub i64 0, 1, !dbg !439
  %".24" = trunc i64 %".23" to i32 , !dbg !439
  ret i32 %".24", !dbg !439
if.end.1:
  %".26" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !440
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".26", i32 0, i32 0 , !dbg !440
  store i8* %".20", i8** %".27", !dbg !440
  %".29" = load i64, i64* %"new_cap", !dbg !441
  %".30" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !441
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".30", i32 0, i32 2 , !dbg !441
  store i64 %".29", i64* %".31", !dbg !441
  %".33" = trunc i64 0 to i32 , !dbg !442
  ret i32 %".33", !dbg !442
}

define linkonce_odr i32 @"span_is_empty$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg") !dbg !60
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !443, metadata !7), !dbg !444
  %".5" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !445
  %".6" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".5", i32 0, i32 1 , !dbg !445
  %".7" = load i64, i64* %".6", !dbg !445
  %".8" = icmp eq i64 %".7", 0 , !dbg !445
  br i1 %".8", label %"if.then", label %"if.end", !dbg !445
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !446
  ret i32 %".10", !dbg !446
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !447
  ret i32 %".12", !dbg !447
}

define linkonce_odr %"struct.ritz_module_1.Span$u8" @"span_slice$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg", i64 %"start.arg", i64 %"end.arg") !dbg !61
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  %"result.addr" = alloca %"struct.ritz_module_1.Span$u8", !dbg !452
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !448, metadata !7), !dbg !449
  %"start" = alloca i64
  store i64 %"start.arg", i64* %"start"
  call void @"llvm.dbg.declare"(metadata i64* %"start", metadata !450, metadata !7), !dbg !449
  %"end" = alloca i64
  store i64 %"end.arg", i64* %"end"
  call void @"llvm.dbg.declare"(metadata i64* %"end", metadata !451, metadata !7), !dbg !449
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"* %"result.addr", metadata !453, metadata !7), !dbg !454
  %".12" = load i64, i64* %"start", !dbg !455
  %".13" = icmp slt i64 %".12", 0 , !dbg !455
  br i1 %".13", label %"if.then", label %"if.end", !dbg !455
if.then:
  store i64 0, i64* %"start", !dbg !456
  br label %"if.end", !dbg !456
if.end:
  %".17" = load i64, i64* %"end", !dbg !457
  %".18" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !457
  %".19" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".18", i32 0, i32 1 , !dbg !457
  %".20" = load i64, i64* %".19", !dbg !457
  %".21" = icmp sgt i64 %".17", %".20" , !dbg !457
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !457
if.then.1:
  %".23" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !458
  %".24" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".23", i32 0, i32 1 , !dbg !458
  %".25" = load i64, i64* %".24", !dbg !458
  store i64 %".25", i64* %"end", !dbg !458
  br label %"if.end.1", !dbg !458
if.end.1:
  %".28" = load i64, i64* %"start", !dbg !459
  %".29" = load i64, i64* %"end", !dbg !459
  %".30" = icmp sge i64 %".28", %".29" , !dbg !459
  br i1 %".30", label %"if.then.2", label %"if.end.2", !dbg !459
if.then.2:
  %".32" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !460
  %".33" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 0 , !dbg !460
  store i8* null, i8** %".33", !dbg !460
  %".35" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !461
  %".36" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 1 , !dbg !461
  store i64 0, i64* %".36", !dbg !461
  %".38" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !462
  ret %"struct.ritz_module_1.Span$u8" %".38", !dbg !462
if.end.2:
  %".40" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !463
  %".41" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".40", i32 0, i32 0 , !dbg !463
  %".42" = load i8*, i8** %".41", !dbg !463
  %".43" = load i64, i64* %"start", !dbg !463
  %".44" = getelementptr i8, i8* %".42", i64 %".43" , !dbg !463
  %".45" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !463
  %".46" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 0 , !dbg !463
  store i8* %".44", i8** %".46", !dbg !463
  %".48" = load i64, i64* %"end", !dbg !464
  %".49" = load i64, i64* %"start", !dbg !464
  %".50" = sub i64 %".48", %".49", !dbg !464
  %".51" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !464
  %".52" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", i32 0, i32 1 , !dbg !464
  store i64 %".50", i64* %".52", !dbg !464
  %".54" = load %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %"result.addr", !dbg !465
  ret %"struct.ritz_module_1.Span$u8" %".54", !dbg !465
}

define linkonce_odr i8 @"span_get$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg", i64 %"idx.arg") !dbg !62
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !466, metadata !7), !dbg !467
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !468, metadata !7), !dbg !467
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !469
  %".9" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".8", i32 0, i32 0 , !dbg !469
  %".10" = load i8*, i8** %".9", !dbg !469
  %".11" = load i64, i64* %"idx", !dbg !469
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !469
  %".13" = load i8, i8* %".12", !dbg !469
  ret i8 %".13", !dbg !469
}

define linkonce_odr i8* @"span_get_ptr$u8"(%"struct.ritz_module_1.Span$u8"* %"s.arg", i64 %"idx.arg") !dbg !63
{
entry:
  %"s" = alloca %"struct.ritz_module_1.Span$u8"*
  store %"struct.ritz_module_1.Span$u8"* %"s.arg", %"struct.ritz_module_1.Span$u8"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Span$u8"** %"s", metadata !470, metadata !7), !dbg !471
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !472, metadata !7), !dbg !471
  %".8" = load %"struct.ritz_module_1.Span$u8"*, %"struct.ritz_module_1.Span$u8"** %"s", !dbg !473
  %".9" = getelementptr %"struct.ritz_module_1.Span$u8", %"struct.ritz_module_1.Span$u8"* %".8", i32 0, i32 0 , !dbg !473
  %".10" = load i8*, i8** %".9", !dbg !473
  %".11" = load i64, i64* %"idx", !dbg !473
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !473
  ret i8* %".12", !dbg !473
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %"new_cap.arg") !dbg !64
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !474, metadata !7), !dbg !475
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !476, metadata !7), !dbg !475
  %".7" = load i64, i64* %"new_cap", !dbg !477
  %".8" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !477
  %".9" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".8", i32 0, i32 2 , !dbg !477
  %".10" = load i64, i64* %".9", !dbg !477
  %".11" = icmp sle i64 %".7", %".10" , !dbg !477
  br i1 %".11", label %"if.then", label %"if.end", !dbg !477
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !478
  ret i32 %".13", !dbg !478
if.end:
  %".15" = load i64, i64* %"new_cap", !dbg !479
  %".16" = mul i64 %".15", 16, !dbg !479
  %".17" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !480
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".17", i32 0, i32 0 , !dbg !480
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !480
  %".20" = bitcast %"struct.ritz_module_1.LineBounds"* %".19" to i8* , !dbg !480
  %".21" = call i8* @"realloc"(i8* %".20", i64 %".16"), !dbg !480
  %".22" = icmp eq i8* %".21", null , !dbg !481
  br i1 %".22", label %"if.then.1", label %"if.end.1", !dbg !481
if.then.1:
  %".24" = sub i64 0, 1, !dbg !482
  %".25" = trunc i64 %".24" to i32 , !dbg !482
  ret i32 %".25", !dbg !482
if.end.1:
  %".27" = bitcast i8* %".21" to %"struct.ritz_module_1.LineBounds"* , !dbg !483
  %".28" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !483
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".28", i32 0, i32 0 , !dbg !483
  store %"struct.ritz_module_1.LineBounds"* %".27", %"struct.ritz_module_1.LineBounds"** %".29", !dbg !483
  %".31" = load i64, i64* %"new_cap", !dbg !484
  %".32" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !484
  %".33" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".32", i32 0, i32 2 , !dbg !484
  store i64 %".31", i64* %".33", !dbg !484
  %".35" = trunc i64 0 to i32 , !dbg !485
  ret i32 %".35", !dbg !485
}

@".str.0" = private constant [7 x i8] c"Accept\00"
@".str.1" = private constant [17 x i8] c"application/json\00"
@".str.2" = private constant [4 x i8] c"*/*\00"
@".str.3" = private constant [7 x i8] c"Accept\00"
@".str.4" = private constant [10 x i8] c"text/html\00"
@".str.5" = private constant [4 x i8] c"*/*\00"
@".str.6" = private constant [13 x i8] c"Content-Type\00"
@".str.7" = private constant [17 x i8] c"application/json\00"
@".str.8" = private constant [34 x i8] c"application/x-www-form-urlencoded\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/spire/lib/http", filename: "request.ritz")
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
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 262, name: "span_contains", scopeLine: 262, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 44, name: "request_new", scopeLine: 44, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 56, name: "request_with", scopeLine: 56, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 72, name: "request_method", scopeLine: 72, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 76, name: "request_path", scopeLine: 76, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 84, name: "request_param", scopeLine: 84, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 100, name: "request_query_param", scopeLine: 100, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 106, name: "request_header", scopeLine: 106, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 120, name: "request_body_str", scopeLine: 120, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 127, name: "request_body_len", scopeLine: 127, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 135, name: "request_wants_json", scopeLine: 135, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "request_wants_html", scopeLine: 148, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 162, name: "request_content_type", scopeLine: 162, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 167, name: "request_is_json", scopeLine: 167, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 175, name: "request_is_form", scopeLine: 175, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 186, name: "request_set_method", scopeLine: 186, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 189, name: "request_set_path", scopeLine: 189, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 196, name: "request_set_header", scopeLine: 196, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 214, name: "request_set_param", scopeLine: 214, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 232, name: "request_set_body", scopeLine: 232, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "span_eq_ci", scopeLine: 244, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 256, name: "to_lower", scopeLine: 256, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!51 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!52 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!53 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!54 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!55 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!56 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 79, name: "span_len$u8", scopeLine: 79, type: !4, unit: !1)
!57 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!58 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 97, name: "span_as_ptr$u8", scopeLine: 97, type: !4, unit: !1)
!59 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!60 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 83, name: "span_is_empty$u8", scopeLine: 83, type: !4, unit: !1)
!61 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 105, name: "span_slice$u8", scopeLine: 105, type: !4, unit: !1)
!62 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 89, name: "span_get$u8", scopeLine: 89, type: !4, unit: !1)
!63 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 93, name: "span_get_ptr$u8", scopeLine: 93, type: !4, unit: !1)
!64 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!65 = !DICompositeType(align: 64, file: !0, name: "Span$u8", size: 128, tag: DW_TAG_structure_type)
!66 = !DIDerivedType(baseType: !65, size: 64, tag: DW_TAG_pointer_type)
!67 = !DILocalVariable(file: !0, line: 262, name: "haystack", scope: !23, type: !66)
!68 = !DILocation(column: 1, line: 262, scope: !23)
!69 = !DILocalVariable(file: !0, line: 262, name: "needle", scope: !23, type: !66)
!70 = !DILocation(column: 5, line: 263, scope: !23)
!71 = !DILocation(column: 9, line: 264, scope: !23)
!72 = !DILocation(column: 5, line: 265, scope: !23)
!73 = !DILocation(column: 9, line: 266, scope: !23)
!74 = !DILocation(column: 5, line: 267, scope: !23)
!75 = !DILocalVariable(file: !0, line: 267, name: "i", scope: !23, type: !11)
!76 = !DILocation(column: 1, line: 267, scope: !23)
!77 = !DILocation(column: 5, line: 268, scope: !23)
!78 = !DILocation(column: 9, line: 269, scope: !23)
!79 = !DILocalVariable(file: !0, line: 269, name: "found", scope: !23, type: !10)
!80 = !DILocation(column: 1, line: 269, scope: !23)
!81 = !DILocation(column: 9, line: 270, scope: !23)
!82 = !DILocalVariable(file: !0, line: 270, name: "j", scope: !23, type: !11)
!83 = !DILocation(column: 1, line: 270, scope: !23)
!84 = !DILocation(column: 9, line: 271, scope: !23)
!85 = !DILocation(column: 13, line: 272, scope: !23)
!86 = !DILocation(column: 17, line: 273, scope: !23)
!87 = !DILocation(column: 17, line: 274, scope: !23)
!88 = !DILocation(column: 13, line: 275, scope: !23)
!89 = !DILocation(column: 9, line: 276, scope: !23)
!90 = !DILocation(column: 13, line: 277, scope: !23)
!91 = !DILocation(column: 9, line: 278, scope: !23)
!92 = !DILocation(column: 5, line: 279, scope: !23)
!93 = !DILocation(column: 5, line: 45, scope: !24)
!94 = !DICompositeType(align: 64, file: !0, name: "Request", size: 756096, tag: DW_TAG_structure_type)
!95 = !DILocalVariable(file: !0, line: 45, name: "req", scope: !24, type: !94)
!96 = !DILocation(column: 1, line: 45, scope: !24)
!97 = !DILocation(column: 5, line: 46, scope: !24)
!98 = !DILocation(column: 5, line: 47, scope: !24)
!99 = !DILocation(column: 5, line: 48, scope: !24)
!100 = !DILocation(column: 5, line: 49, scope: !24)
!101 = !DILocation(column: 5, line: 50, scope: !24)
!102 = !DILocation(column: 5, line: 51, scope: !24)
!103 = !DILocation(column: 5, line: 52, scope: !24)
!104 = !DILocation(column: 5, line: 53, scope: !24)
!105 = !DILocalVariable(file: !0, line: 56, name: "method", scope: !25, type: !10)
!106 = !DILocation(column: 1, line: 56, scope: !25)
!107 = !DILocalVariable(file: !0, line: 56, name: "path", scope: !25, type: !66)
!108 = !DILocation(column: 5, line: 57, scope: !25)
!109 = !DILocalVariable(file: !0, line: 57, name: "req", scope: !25, type: !94)
!110 = !DILocation(column: 1, line: 57, scope: !25)
!111 = !DILocation(column: 5, line: 58, scope: !25)
!112 = !DILocation(column: 5, line: 60, scope: !25)
!113 = !DILocalVariable(file: !0, line: 60, name: "i", scope: !25, type: !11)
!114 = !DILocation(column: 1, line: 60, scope: !25)
!115 = !DILocation(column: 5, line: 61, scope: !25)
!116 = !DILocation(column: 9, line: 62, scope: !25)
!117 = !DILocation(column: 9, line: 63, scope: !25)
!118 = !DILocation(column: 5, line: 64, scope: !25)
!119 = !DILocation(column: 5, line: 65, scope: !25)
!120 = !DIDerivedType(baseType: !94, size: 64, tag: DW_TAG_pointer_type)
!121 = !DILocalVariable(file: !0, line: 72, name: "self", scope: !26, type: !120)
!122 = !DILocation(column: 1, line: 72, scope: !26)
!123 = !DILocation(column: 5, line: 73, scope: !26)
!124 = !DILocalVariable(file: !0, line: 76, name: "self", scope: !27, type: !120)
!125 = !DILocation(column: 1, line: 76, scope: !27)
!126 = !DILocation(column: 5, line: 77, scope: !27)
!127 = !DILocalVariable(file: !0, line: 77, name: "sp", scope: !27, type: !65)
!128 = !DILocation(column: 1, line: 77, scope: !27)
!129 = !DILocation(column: 5, line: 78, scope: !27)
!130 = !DILocation(column: 5, line: 79, scope: !27)
!131 = !DILocation(column: 5, line: 80, scope: !27)
!132 = !DILocalVariable(file: !0, line: 84, name: "self", scope: !28, type: !120)
!133 = !DILocation(column: 1, line: 84, scope: !28)
!134 = !DILocalVariable(file: !0, line: 84, name: "name", scope: !28, type: !66)
!135 = !DILocalVariable(file: !0, line: 84, name: "out_value", scope: !28, type: !66)
!136 = !DILocation(column: 5, line: 85, scope: !28)
!137 = !DILocalVariable(file: !0, line: 85, name: "i", scope: !28, type: !11)
!138 = !DILocation(column: 1, line: 85, scope: !28)
!139 = !DILocation(column: 5, line: 86, scope: !28)
!140 = !DILocation(column: 9, line: 88, scope: !28)
!141 = !DILocalVariable(file: !0, line: 88, name: "param_name", scope: !28, type: !65)
!142 = !DILocation(column: 1, line: 88, scope: !28)
!143 = !DILocation(column: 9, line: 89, scope: !28)
!144 = !DILocation(column: 9, line: 90, scope: !28)
!145 = !DILocation(column: 9, line: 91, scope: !28)
!146 = !DILocation(column: 13, line: 92, scope: !28)
!147 = !DILocation(column: 13, line: 93, scope: !28)
!148 = !DILocation(column: 13, line: 94, scope: !28)
!149 = !DILocation(column: 9, line: 95, scope: !28)
!150 = !DILocation(column: 5, line: 96, scope: !28)
!151 = !DILocalVariable(file: !0, line: 100, name: "self", scope: !29, type: !120)
!152 = !DILocation(column: 1, line: 100, scope: !29)
!153 = !DILocalVariable(file: !0, line: 100, name: "name", scope: !29, type: !66)
!154 = !DILocalVariable(file: !0, line: 100, name: "out_value", scope: !29, type: !66)
!155 = !DILocation(column: 5, line: 102, scope: !29)
!156 = !DILocalVariable(file: !0, line: 106, name: "self", scope: !30, type: !120)
!157 = !DILocation(column: 1, line: 106, scope: !30)
!158 = !DILocalVariable(file: !0, line: 106, name: "name", scope: !30, type: !66)
!159 = !DILocalVariable(file: !0, line: 106, name: "out_value", scope: !30, type: !66)
!160 = !DILocation(column: 5, line: 107, scope: !30)
!161 = !DILocalVariable(file: !0, line: 107, name: "i", scope: !30, type: !11)
!162 = !DILocation(column: 1, line: 107, scope: !30)
!163 = !DILocation(column: 5, line: 108, scope: !30)
!164 = !DILocation(column: 9, line: 109, scope: !30)
!165 = !DILocalVariable(file: !0, line: 109, name: "header_name", scope: !30, type: !65)
!166 = !DILocation(column: 1, line: 109, scope: !30)
!167 = !DILocation(column: 9, line: 110, scope: !30)
!168 = !DILocation(column: 9, line: 111, scope: !30)
!169 = !DILocation(column: 9, line: 112, scope: !30)
!170 = !DILocation(column: 13, line: 113, scope: !30)
!171 = !DILocation(column: 13, line: 114, scope: !30)
!172 = !DILocation(column: 13, line: 115, scope: !30)
!173 = !DILocation(column: 9, line: 116, scope: !30)
!174 = !DILocation(column: 5, line: 117, scope: !30)
!175 = !DILocalVariable(file: !0, line: 120, name: "self", scope: !31, type: !120)
!176 = !DILocation(column: 1, line: 120, scope: !31)
!177 = !DILocation(column: 5, line: 121, scope: !31)
!178 = !DILocalVariable(file: !0, line: 121, name: "sp", scope: !31, type: !65)
!179 = !DILocation(column: 1, line: 121, scope: !31)
!180 = !DILocation(column: 5, line: 122, scope: !31)
!181 = !DILocation(column: 5, line: 123, scope: !31)
!182 = !DILocation(column: 5, line: 124, scope: !31)
!183 = !DILocalVariable(file: !0, line: 127, name: "self", scope: !32, type: !120)
!184 = !DILocation(column: 1, line: 127, scope: !32)
!185 = !DILocation(column: 5, line: 128, scope: !32)
!186 = !DILocalVariable(file: !0, line: 135, name: "self", scope: !33, type: !120)
!187 = !DILocation(column: 1, line: 135, scope: !33)
!188 = !DILocation(column: 5, line: 136, scope: !33)
!189 = !DILocation(column: 5, line: 137, scope: !33)
!190 = !DILocalVariable(file: !0, line: 137, name: "accept_value", scope: !33, type: !65)
!191 = !DILocation(column: 1, line: 137, scope: !33)
!192 = !DILocation(column: 5, line: 138, scope: !33)
!193 = !DILocation(column: 9, line: 139, scope: !33)
!194 = !DILocation(column: 9, line: 140, scope: !33)
!195 = !DILocation(column: 9, line: 141, scope: !33)
!196 = !DILocation(column: 13, line: 142, scope: !33)
!197 = !DILocation(column: 13, line: 144, scope: !33)
!198 = !DILocation(column: 5, line: 145, scope: !33)
!199 = !DILocalVariable(file: !0, line: 148, name: "self", scope: !34, type: !120)
!200 = !DILocation(column: 1, line: 148, scope: !34)
!201 = !DILocation(column: 5, line: 149, scope: !34)
!202 = !DILocation(column: 5, line: 150, scope: !34)
!203 = !DILocalVariable(file: !0, line: 150, name: "accept_value", scope: !34, type: !65)
!204 = !DILocation(column: 1, line: 150, scope: !34)
!205 = !DILocation(column: 5, line: 151, scope: !34)
!206 = !DILocation(column: 9, line: 152, scope: !34)
!207 = !DILocation(column: 9, line: 153, scope: !34)
!208 = !DILocation(column: 9, line: 154, scope: !34)
!209 = !DILocation(column: 13, line: 155, scope: !34)
!210 = !DILocation(column: 13, line: 157, scope: !34)
!211 = !DILocation(column: 5, line: 158, scope: !34)
!212 = !DILocalVariable(file: !0, line: 162, name: "self", scope: !35, type: !120)
!213 = !DILocation(column: 1, line: 162, scope: !35)
!214 = !DILocalVariable(file: !0, line: 162, name: "out_ct", scope: !35, type: !66)
!215 = !DILocation(column: 5, line: 163, scope: !35)
!216 = !DILocation(column: 5, line: 164, scope: !35)
!217 = !DILocalVariable(file: !0, line: 167, name: "self", scope: !36, type: !120)
!218 = !DILocation(column: 1, line: 167, scope: !36)
!219 = !DILocation(column: 5, line: 168, scope: !36)
!220 = !DILocalVariable(file: !0, line: 168, name: "ct", scope: !36, type: !65)
!221 = !DILocation(column: 1, line: 168, scope: !36)
!222 = !DILocation(column: 5, line: 169, scope: !36)
!223 = !DILocation(column: 9, line: 170, scope: !36)
!224 = !DILocation(column: 9, line: 171, scope: !36)
!225 = !DILocation(column: 5, line: 172, scope: !36)
!226 = !DILocalVariable(file: !0, line: 175, name: "self", scope: !37, type: !120)
!227 = !DILocation(column: 1, line: 175, scope: !37)
!228 = !DILocation(column: 5, line: 176, scope: !37)
!229 = !DILocalVariable(file: !0, line: 176, name: "ct", scope: !37, type: !65)
!230 = !DILocation(column: 1, line: 176, scope: !37)
!231 = !DILocation(column: 5, line: 177, scope: !37)
!232 = !DILocation(column: 9, line: 178, scope: !37)
!233 = !DILocation(column: 9, line: 179, scope: !37)
!234 = !DILocation(column: 5, line: 180, scope: !37)
!235 = !DILocalVariable(file: !0, line: 186, name: "self", scope: !38, type: !120)
!236 = !DILocation(column: 1, line: 186, scope: !38)
!237 = !DILocalVariable(file: !0, line: 186, name: "method", scope: !38, type: !10)
!238 = !DILocation(column: 5, line: 187, scope: !38)
!239 = !DILocalVariable(file: !0, line: 189, name: "self", scope: !39, type: !120)
!240 = !DILocation(column: 1, line: 189, scope: !39)
!241 = !DILocalVariable(file: !0, line: 189, name: "path", scope: !39, type: !66)
!242 = !DILocation(column: 5, line: 190, scope: !39)
!243 = !DILocalVariable(file: !0, line: 190, name: "i", scope: !39, type: !11)
!244 = !DILocation(column: 1, line: 190, scope: !39)
!245 = !DILocation(column: 5, line: 191, scope: !39)
!246 = !DILocation(column: 9, line: 192, scope: !39)
!247 = !DILocation(column: 9, line: 193, scope: !39)
!248 = !DILocation(column: 5, line: 194, scope: !39)
!249 = !DILocalVariable(file: !0, line: 196, name: "self", scope: !40, type: !120)
!250 = !DILocation(column: 1, line: 196, scope: !40)
!251 = !DILocalVariable(file: !0, line: 196, name: "name", scope: !40, type: !66)
!252 = !DILocalVariable(file: !0, line: 196, name: "value", scope: !40, type: !66)
!253 = !DILocation(column: 5, line: 197, scope: !40)
!254 = !DILocation(column: 9, line: 198, scope: !40)
!255 = !DILocation(column: 5, line: 199, scope: !40)
!256 = !DILocation(column: 5, line: 201, scope: !40)
!257 = !DILocalVariable(file: !0, line: 201, name: "i", scope: !40, type: !11)
!258 = !DILocation(column: 1, line: 201, scope: !40)
!259 = !DILocation(column: 5, line: 202, scope: !40)
!260 = !DILocation(column: 9, line: 203, scope: !40)
!261 = !DILocation(column: 9, line: 204, scope: !40)
!262 = !DILocation(column: 5, line: 205, scope: !40)
!263 = !DILocation(column: 5, line: 207, scope: !40)
!264 = !DILocation(column: 5, line: 208, scope: !40)
!265 = !DILocation(column: 9, line: 209, scope: !40)
!266 = !DILocation(column: 9, line: 210, scope: !40)
!267 = !DILocation(column: 5, line: 211, scope: !40)
!268 = !DILocation(column: 5, line: 212, scope: !40)
!269 = !DILocalVariable(file: !0, line: 214, name: "self", scope: !41, type: !120)
!270 = !DILocation(column: 1, line: 214, scope: !41)
!271 = !DILocalVariable(file: !0, line: 214, name: "name", scope: !41, type: !66)
!272 = !DILocalVariable(file: !0, line: 214, name: "value", scope: !41, type: !66)
!273 = !DILocation(column: 5, line: 215, scope: !41)
!274 = !DILocation(column: 9, line: 216, scope: !41)
!275 = !DILocation(column: 5, line: 217, scope: !41)
!276 = !DILocation(column: 5, line: 219, scope: !41)
!277 = !DILocalVariable(file: !0, line: 219, name: "i", scope: !41, type: !11)
!278 = !DILocation(column: 1, line: 219, scope: !41)
!279 = !DILocation(column: 5, line: 220, scope: !41)
!280 = !DILocation(column: 9, line: 221, scope: !41)
!281 = !DILocation(column: 9, line: 222, scope: !41)
!282 = !DILocation(column: 5, line: 223, scope: !41)
!283 = !DILocation(column: 5, line: 225, scope: !41)
!284 = !DILocation(column: 5, line: 226, scope: !41)
!285 = !DILocation(column: 9, line: 227, scope: !41)
!286 = !DILocation(column: 9, line: 228, scope: !41)
!287 = !DILocation(column: 5, line: 229, scope: !41)
!288 = !DILocation(column: 5, line: 230, scope: !41)
!289 = !DILocalVariable(file: !0, line: 232, name: "self", scope: !42, type: !120)
!290 = !DILocation(column: 1, line: 232, scope: !42)
!291 = !DILocalVariable(file: !0, line: 232, name: "body", scope: !42, type: !66)
!292 = !DILocation(column: 5, line: 233, scope: !42)
!293 = !DILocalVariable(file: !0, line: 233, name: "i", scope: !42, type: !11)
!294 = !DILocation(column: 1, line: 233, scope: !42)
!295 = !DILocation(column: 5, line: 234, scope: !42)
!296 = !DILocation(column: 9, line: 235, scope: !42)
!297 = !DILocation(column: 9, line: 236, scope: !42)
!298 = !DILocation(column: 5, line: 237, scope: !42)
!299 = !DILocalVariable(file: !0, line: 244, name: "a", scope: !43, type: !66)
!300 = !DILocation(column: 1, line: 244, scope: !43)
!301 = !DILocalVariable(file: !0, line: 244, name: "b", scope: !43, type: !66)
!302 = !DILocation(column: 5, line: 245, scope: !43)
!303 = !DILocation(column: 9, line: 246, scope: !43)
!304 = !DILocation(column: 5, line: 247, scope: !43)
!305 = !DILocalVariable(file: !0, line: 247, name: "i", scope: !43, type: !11)
!306 = !DILocation(column: 1, line: 247, scope: !43)
!307 = !DILocation(column: 5, line: 248, scope: !43)
!308 = !DILocation(column: 9, line: 249, scope: !43)
!309 = !DILocation(column: 9, line: 250, scope: !43)
!310 = !DILocation(column: 9, line: 251, scope: !43)
!311 = !DILocation(column: 13, line: 252, scope: !43)
!312 = !DILocation(column: 9, line: 253, scope: !43)
!313 = !DILocation(column: 5, line: 254, scope: !43)
!314 = !DILocalVariable(file: !0, line: 256, name: "c", scope: !44, type: !12)
!315 = !DILocation(column: 1, line: 256, scope: !44)
!316 = !DILocation(column: 5, line: 257, scope: !44)
!317 = !DILocation(column: 9, line: 258, scope: !44)
!318 = !DILocation(column: 5, line: 259, scope: !44)
!319 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!320 = !DIDerivedType(baseType: !319, size: 64, tag: DW_TAG_reference_type)
!321 = !DIDerivedType(baseType: !320, size: 64, tag: DW_TAG_reference_type)
!322 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !45, type: !321)
!323 = !DILocation(column: 1, line: 288, scope: !45)
!324 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!325 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !45, type: !324)
!326 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !45, type: !11)
!327 = !DILocation(column: 5, line: 289, scope: !45)
!328 = !DILocation(column: 13, line: 291, scope: !45)
!329 = !DILocation(column: 5, line: 292, scope: !45)
!330 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!331 = !DIDerivedType(baseType: !330, size: 64, tag: DW_TAG_reference_type)
!332 = !DIDerivedType(baseType: !331, size: 64, tag: DW_TAG_reference_type)
!333 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !46, type: !332)
!334 = !DILocation(column: 1, line: 210, scope: !46)
!335 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!336 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !46, type: !335)
!337 = !DILocation(column: 5, line: 211, scope: !46)
!338 = !DILocation(column: 9, line: 212, scope: !46)
!339 = !DILocation(column: 5, line: 213, scope: !46)
!340 = !DILocation(column: 5, line: 214, scope: !46)
!341 = !DILocation(column: 5, line: 215, scope: !46)
!342 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !47, type: !321)
!343 = !DILocation(column: 1, line: 148, scope: !47)
!344 = !DILocation(column: 5, line: 149, scope: !47)
!345 = !DILocation(column: 5, line: 151, scope: !47)
!346 = !DILocation(column: 5, line: 152, scope: !47)
!347 = !DILocation(column: 5, line: 153, scope: !47)
!348 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !48, type: !321)
!349 = !DILocation(column: 1, line: 244, scope: !48)
!350 = !DILocation(column: 5, line: 245, scope: !48)
!351 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !49, type: !11)
!352 = !DILocation(column: 1, line: 124, scope: !49)
!353 = !DILocation(column: 5, line: 125, scope: !49)
!354 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !49, type: !319)
!355 = !DILocation(column: 1, line: 125, scope: !49)
!356 = !DILocation(column: 5, line: 126, scope: !49)
!357 = !DILocation(column: 9, line: 127, scope: !49)
!358 = !DILocation(column: 9, line: 128, scope: !49)
!359 = !DILocation(column: 9, line: 129, scope: !49)
!360 = !DILocation(column: 9, line: 130, scope: !49)
!361 = !DILocation(column: 5, line: 132, scope: !49)
!362 = !DILocation(column: 5, line: 133, scope: !49)
!363 = !DILocation(column: 5, line: 134, scope: !49)
!364 = !DILocation(column: 9, line: 135, scope: !49)
!365 = !DILocation(column: 9, line: 136, scope: !49)
!366 = !DILocation(column: 9, line: 137, scope: !49)
!367 = !DILocation(column: 5, line: 139, scope: !49)
!368 = !DILocation(column: 5, line: 140, scope: !49)
!369 = !DILocation(column: 5, line: 141, scope: !49)
!370 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !50, type: !320)
!371 = !DILocation(column: 1, line: 225, scope: !50)
!372 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !50, type: !11)
!373 = !DILocation(column: 5, line: 226, scope: !50)
!374 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !51, type: !321)
!375 = !DILocation(column: 1, line: 219, scope: !51)
!376 = !DILocation(column: 5, line: 220, scope: !51)
!377 = !DILocation(column: 5, line: 221, scope: !51)
!378 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !52, type: !321)
!379 = !DILocation(column: 1, line: 193, scope: !52)
!380 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !52, type: !11)
!381 = !DILocation(column: 5, line: 194, scope: !52)
!382 = !DILocation(column: 9, line: 195, scope: !52)
!383 = !DILocation(column: 5, line: 197, scope: !52)
!384 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !52, type: !11)
!385 = !DILocation(column: 1, line: 197, scope: !52)
!386 = !DILocation(column: 5, line: 198, scope: !52)
!387 = !DILocation(column: 9, line: 199, scope: !52)
!388 = !DILocation(column: 5, line: 200, scope: !52)
!389 = !DILocation(column: 9, line: 201, scope: !52)
!390 = !DILocation(column: 5, line: 203, scope: !52)
!391 = !DILocation(column: 5, line: 117, scope: !53)
!392 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !53, type: !319)
!393 = !DILocation(column: 1, line: 117, scope: !53)
!394 = !DILocation(column: 5, line: 118, scope: !53)
!395 = !DILocation(column: 5, line: 119, scope: !53)
!396 = !DILocation(column: 5, line: 120, scope: !53)
!397 = !DILocation(column: 5, line: 121, scope: !53)
!398 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !54, type: !321)
!399 = !DILocation(column: 1, line: 235, scope: !54)
!400 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !54, type: !11)
!401 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !54, type: !12)
!402 = !DILocation(column: 5, line: 236, scope: !54)
!403 = !DILocation(column: 5, line: 237, scope: !54)
!404 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !55, type: !321)
!405 = !DILocation(column: 1, line: 210, scope: !55)
!406 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !55, type: !12)
!407 = !DILocation(column: 5, line: 211, scope: !55)
!408 = !DILocation(column: 9, line: 212, scope: !55)
!409 = !DILocation(column: 5, line: 213, scope: !55)
!410 = !DILocation(column: 5, line: 214, scope: !55)
!411 = !DILocation(column: 5, line: 215, scope: !55)
!412 = !DILocalVariable(file: !0, line: 79, name: "s", scope: !56, type: !66)
!413 = !DILocation(column: 1, line: 79, scope: !56)
!414 = !DILocation(column: 5, line: 80, scope: !56)
!415 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !57, type: !332)
!416 = !DILocation(column: 1, line: 193, scope: !57)
!417 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !57, type: !11)
!418 = !DILocation(column: 5, line: 194, scope: !57)
!419 = !DILocation(column: 9, line: 195, scope: !57)
!420 = !DILocation(column: 5, line: 197, scope: !57)
!421 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !57, type: !11)
!422 = !DILocation(column: 1, line: 197, scope: !57)
!423 = !DILocation(column: 5, line: 198, scope: !57)
!424 = !DILocation(column: 9, line: 199, scope: !57)
!425 = !DILocation(column: 5, line: 200, scope: !57)
!426 = !DILocation(column: 9, line: 201, scope: !57)
!427 = !DILocation(column: 5, line: 203, scope: !57)
!428 = !DILocalVariable(file: !0, line: 97, name: "s", scope: !58, type: !66)
!429 = !DILocation(column: 1, line: 97, scope: !58)
!430 = !DILocation(column: 5, line: 98, scope: !58)
!431 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !59, type: !321)
!432 = !DILocation(column: 1, line: 179, scope: !59)
!433 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !59, type: !11)
!434 = !DILocation(column: 5, line: 180, scope: !59)
!435 = !DILocation(column: 9, line: 181, scope: !59)
!436 = !DILocation(column: 5, line: 183, scope: !59)
!437 = !DILocation(column: 5, line: 184, scope: !59)
!438 = !DILocation(column: 5, line: 185, scope: !59)
!439 = !DILocation(column: 9, line: 186, scope: !59)
!440 = !DILocation(column: 5, line: 188, scope: !59)
!441 = !DILocation(column: 5, line: 189, scope: !59)
!442 = !DILocation(column: 5, line: 190, scope: !59)
!443 = !DILocalVariable(file: !0, line: 83, name: "s", scope: !60, type: !66)
!444 = !DILocation(column: 1, line: 83, scope: !60)
!445 = !DILocation(column: 5, line: 84, scope: !60)
!446 = !DILocation(column: 9, line: 85, scope: !60)
!447 = !DILocation(column: 5, line: 86, scope: !60)
!448 = !DILocalVariable(file: !0, line: 105, name: "s", scope: !61, type: !66)
!449 = !DILocation(column: 1, line: 105, scope: !61)
!450 = !DILocalVariable(file: !0, line: 105, name: "start", scope: !61, type: !11)
!451 = !DILocalVariable(file: !0, line: 105, name: "end", scope: !61, type: !11)
!452 = !DILocation(column: 5, line: 106, scope: !61)
!453 = !DILocalVariable(file: !0, line: 106, name: "result", scope: !61, type: !65)
!454 = !DILocation(column: 1, line: 106, scope: !61)
!455 = !DILocation(column: 5, line: 107, scope: !61)
!456 = !DILocation(column: 9, line: 108, scope: !61)
!457 = !DILocation(column: 5, line: 109, scope: !61)
!458 = !DILocation(column: 9, line: 110, scope: !61)
!459 = !DILocation(column: 5, line: 111, scope: !61)
!460 = !DILocation(column: 9, line: 112, scope: !61)
!461 = !DILocation(column: 9, line: 113, scope: !61)
!462 = !DILocation(column: 9, line: 114, scope: !61)
!463 = !DILocation(column: 5, line: 115, scope: !61)
!464 = !DILocation(column: 5, line: 116, scope: !61)
!465 = !DILocation(column: 5, line: 117, scope: !61)
!466 = !DILocalVariable(file: !0, line: 89, name: "s", scope: !62, type: !66)
!467 = !DILocation(column: 1, line: 89, scope: !62)
!468 = !DILocalVariable(file: !0, line: 89, name: "idx", scope: !62, type: !11)
!469 = !DILocation(column: 5, line: 90, scope: !62)
!470 = !DILocalVariable(file: !0, line: 93, name: "s", scope: !63, type: !66)
!471 = !DILocation(column: 1, line: 93, scope: !63)
!472 = !DILocalVariable(file: !0, line: 93, name: "idx", scope: !63, type: !11)
!473 = !DILocation(column: 5, line: 94, scope: !63)
!474 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !64, type: !332)
!475 = !DILocation(column: 1, line: 179, scope: !64)
!476 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !64, type: !11)
!477 = !DILocation(column: 5, line: 180, scope: !64)
!478 = !DILocation(column: 9, line: 181, scope: !64)
!479 = !DILocation(column: 5, line: 183, scope: !64)
!480 = !DILocation(column: 5, line: 184, scope: !64)
!481 = !DILocation(column: 5, line: 185, scope: !64)
!482 = !DILocation(column: 9, line: 186, scope: !64)
!483 = !DILocation(column: 5, line: 188, scope: !64)
!484 = !DILocation(column: 5, line: 189, scope: !64)
!485 = !DILocation(column: 5, line: 190, scope: !64)
!486 = !DILocalVariable(file: !0, line: 208, name: "self", scope: !17, type: !66)
!487 = !DILocation(column: 1, line: 208, scope: !17)
!488 = !DILocation(column: 9, line: 209, scope: !17)
!489 = !DILocalVariable(file: !0, line: 211, name: "self", scope: !18, type: !66)
!490 = !DILocation(column: 1, line: 211, scope: !18)
!491 = !DILocation(column: 9, line: 212, scope: !18)
!492 = !DILocalVariable(file: !0, line: 214, name: "self", scope: !19, type: !66)
!493 = !DILocation(column: 1, line: 214, scope: !19)
!494 = !DILocalVariable(file: !0, line: 214, name: "idx", scope: !19, type: !11)
!495 = !DILocation(column: 9, line: 215, scope: !19)
!496 = !DILocalVariable(file: !0, line: 217, name: "self", scope: !20, type: !66)
!497 = !DILocation(column: 1, line: 217, scope: !20)
!498 = !DILocalVariable(file: !0, line: 217, name: "idx", scope: !20, type: !11)
!499 = !DILocation(column: 9, line: 218, scope: !20)
!500 = !DILocalVariable(file: !0, line: 220, name: "self", scope: !21, type: !66)
!501 = !DILocation(column: 1, line: 220, scope: !21)
!502 = !DILocation(column: 9, line: 221, scope: !21)
!503 = !DILocalVariable(file: !0, line: 223, name: "self", scope: !22, type: !66)
!504 = !DILocation(column: 1, line: 223, scope: !22)
!505 = !DILocalVariable(file: !0, line: 223, name: "start", scope: !22, type: !11)
!506 = !DILocalVariable(file: !0, line: 223, name: "end", scope: !22, type: !11)
!507 = !DILocation(column: 9, line: 224, scope: !22)