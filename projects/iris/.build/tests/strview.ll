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
declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

@"BLOCK_SIZES" = internal constant [9 x i64] [i64 32, i64 48, i64 80, i64 144, i64 272, i64 528, i64 1040, i64 2064, i64 0]
@"g_alloc" = internal global %"struct.ritz_module_1.GlobalAlloc" zeroinitializer
define i64 @"StrView_len"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !17
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !325, metadata !7), !dbg !326
  %".4" = call i64 @"strview_len"(%"struct.ritz_module_1.StrView"* %"self.arg"), !dbg !327
  ret i64 %".4", !dbg !327
}

define i32 @"StrView_is_empty"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !18
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !328, metadata !7), !dbg !329
  %".4" = call i32 @"strview_is_empty"(%"struct.ritz_module_1.StrView"* %"self.arg"), !dbg !330
  ret i32 %".4", !dbg !330
}

define i8 @"StrView_get"(%"struct.ritz_module_1.StrView"* %"self.arg", i64 %"idx.arg") !dbg !19
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !331, metadata !7), !dbg !332
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !333, metadata !7), !dbg !332
  %".7" = load i64, i64* %"idx", !dbg !334
  %".8" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"self.arg", i64 %".7"), !dbg !334
  ret i8 %".8", !dbg !334
}

define i8* @"StrView_as_ptr"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !20
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !335, metadata !7), !dbg !336
  %".4" = call i8* @"strview_as_ptr"(%"struct.ritz_module_1.StrView"* %"self.arg"), !dbg !337
  ret i8* %".4", !dbg !337
}

define %"struct.ritz_module_1.StrView" @"StrView_slice"(%"struct.ritz_module_1.StrView"* %"self.arg", i64 %"start.arg", i64 %"end.arg") !dbg !21
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !338, metadata !7), !dbg !339
  %"start" = alloca i64
  store i64 %"start.arg", i64* %"start"
  call void @"llvm.dbg.declare"(metadata i64* %"start", metadata !340, metadata !7), !dbg !339
  %"end" = alloca i64
  store i64 %"end.arg", i64* %"end"
  call void @"llvm.dbg.declare"(metadata i64* %"end", metadata !341, metadata !7), !dbg !339
  %".10" = load i64, i64* %"start", !dbg !342
  %".11" = load i64, i64* %"end", !dbg !342
  %".12" = call %"struct.ritz_module_1.StrView" @"strview_slice"(%"struct.ritz_module_1.StrView"* %"self.arg", i64 %".10", i64 %".11"), !dbg !342
  ret %"struct.ritz_module_1.StrView" %".12", !dbg !342
}

define %"struct.ritz_module_1.StrView" @"StrView_take"(%"struct.ritz_module_1.StrView"* %"self.arg", i64 %"n.arg") !dbg !22
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !343, metadata !7), !dbg !344
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !345, metadata !7), !dbg !344
  %".7" = load i64, i64* %"n", !dbg !346
  %".8" = call %"struct.ritz_module_1.StrView" @"strview_take"(%"struct.ritz_module_1.StrView"* %"self.arg", i64 %".7"), !dbg !346
  ret %"struct.ritz_module_1.StrView" %".8", !dbg !346
}

define %"struct.ritz_module_1.StrView" @"StrView_skip"(%"struct.ritz_module_1.StrView"* %"self.arg", i64 %"n.arg") !dbg !23
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !347, metadata !7), !dbg !348
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !349, metadata !7), !dbg !348
  %".7" = load i64, i64* %"n", !dbg !350
  %".8" = call %"struct.ritz_module_1.StrView" @"strview_skip"(%"struct.ritz_module_1.StrView"* %"self.arg", i64 %".7"), !dbg !350
  ret %"struct.ritz_module_1.StrView" %".8", !dbg !350
}

define i32 @"StrView_starts_with"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"prefix.arg") !dbg !24
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !351, metadata !7), !dbg !352
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"prefix.arg", metadata !353, metadata !7), !dbg !352
  %".6" = call i32 @"strview_starts_with"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"prefix.arg"), !dbg !354
  ret i32 %".6", !dbg !354
}

define i32 @"StrView_ends_with"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"suffix.arg") !dbg !25
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !355, metadata !7), !dbg !356
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"suffix.arg", metadata !357, metadata !7), !dbg !356
  %".6" = call i32 @"strview_ends_with"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"suffix.arg"), !dbg !358
  ret i32 %".6", !dbg !358
}

define i32 @"StrView_contains"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"needle.arg") !dbg !26
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !359, metadata !7), !dbg !360
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"needle.arg", metadata !361, metadata !7), !dbg !360
  %".6" = call i32 @"strview_contains"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"needle.arg"), !dbg !362
  ret i32 %".6", !dbg !362
}

define i64 @"StrView_find"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"needle.arg") !dbg !27
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !363, metadata !7), !dbg !364
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"needle.arg", metadata !365, metadata !7), !dbg !364
  %".6" = call i64 @"strview_find"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"needle.arg"), !dbg !366
  ret i64 %".6", !dbg !366
}

define i64 @"StrView_find_byte"(%"struct.ritz_module_1.StrView"* %"self.arg", i8 %"c.arg") !dbg !28
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !367, metadata !7), !dbg !368
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !369, metadata !7), !dbg !368
  %".7" = load i8, i8* %"c", !dbg !370
  %".8" = call i64 @"strview_find_byte"(%"struct.ritz_module_1.StrView"* %"self.arg", i8 %".7"), !dbg !370
  ret i64 %".8", !dbg !370
}

define %"struct.ritz_module_1.StrView" @"StrView_trim"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !29
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !371, metadata !7), !dbg !372
  %".4" = call %"struct.ritz_module_1.StrView" @"strview_trim"(%"struct.ritz_module_1.StrView"* %"self.arg"), !dbg !373
  ret %"struct.ritz_module_1.StrView" %".4", !dbg !373
}

define %"struct.ritz_module_1.StrView" @"StrView_trim_start"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !30
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !374, metadata !7), !dbg !375
  %".4" = call %"struct.ritz_module_1.StrView" @"strview_trim_start"(%"struct.ritz_module_1.StrView"* %"self.arg"), !dbg !376
  ret %"struct.ritz_module_1.StrView" %".4", !dbg !376
}

define %"struct.ritz_module_1.StrView" @"StrView_trim_end"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !31
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !377, metadata !7), !dbg !378
  %".4" = call %"struct.ritz_module_1.StrView" @"strview_trim_end"(%"struct.ritz_module_1.StrView"* %"self.arg"), !dbg !379
  ret %"struct.ritz_module_1.StrView" %".4", !dbg !379
}

define i32 @"StrView_eq"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"other.arg") !dbg !32
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !380, metadata !7), !dbg !381
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"other.arg", metadata !382, metadata !7), !dbg !381
  %".6" = call i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"other.arg"), !dbg !383
  ret i32 %".6", !dbg !383
}

define i32 @"StrView_eq_cstr"(%"struct.ritz_module_1.StrView"* %"self.arg", i8* %"cstr.arg") !dbg !33
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !384, metadata !7), !dbg !385
  %"cstr" = alloca i8*
  store i8* %"cstr.arg", i8** %"cstr"
  call void @"llvm.dbg.declare"(metadata i8** %"cstr", metadata !386, metadata !7), !dbg !385
  %".7" = load i8*, i8** %"cstr", !dbg !387
  %".8" = call i32 @"strview_eq_cstr"(%"struct.ritz_module_1.StrView"* %"self.arg", i8* %".7"), !dbg !387
  ret i32 %".8", !dbg !387
}

define i8* @"StrView_to_cstr"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !34
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !388, metadata !7), !dbg !389
  %".4" = call i8* @"strview_to_cstr"(%"struct.ritz_module_1.StrView"* %"self.arg"), !dbg !390
  ret i8* %".4", !dbg !390
}

define i8* @"StrView_as_cstr_unchecked"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !35
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"self.arg", metadata !391, metadata !7), !dbg !392
  %".4" = call i8* @"strview_as_cstr_unchecked"(%"struct.ritz_module_1.StrView"* %"self.arg"), !dbg !393
  ret i8* %".4", !dbg !393
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

define %"struct.ritz_module_1.StrView" @"strview_empty"() !dbg !36
{
entry:
  %"s.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !60
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.addr", metadata !62, metadata !7), !dbg !63
  %".3" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !64
  %".4" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", i32 0, i32 0 , !dbg !64
  store i8* null, i8** %".4", !dbg !64
  %".6" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !65
  %".7" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", i32 0, i32 1 , !dbg !65
  store i64 0, i64* %".7", !dbg !65
  %".9" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !66
  ret %"struct.ritz_module_1.StrView" %".9", !dbg !66
}

define %"struct.ritz_module_1.StrView" @"strview_from_ptr"(i8* %"ptr.arg", i64 %"len.arg") !dbg !37
{
entry:
  %"ptr" = alloca i8*
  %"s.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !71
  store i8* %"ptr.arg", i8** %"ptr"
  call void @"llvm.dbg.declare"(metadata i8** %"ptr", metadata !68, metadata !7), !dbg !69
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !70, metadata !7), !dbg !69
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.addr", metadata !72, metadata !7), !dbg !73
  %".9" = load i8*, i8** %"ptr", !dbg !74
  %".10" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !74
  %".11" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", i32 0, i32 0 , !dbg !74
  store i8* %".9", i8** %".11", !dbg !74
  %".13" = load i64, i64* %"len", !dbg !75
  %".14" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !75
  %".15" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", i32 0, i32 1 , !dbg !75
  store i64 %".13", i64* %".15", !dbg !75
  %".17" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !76
  ret %"struct.ritz_module_1.StrView" %".17", !dbg !76
}

define %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %"cstr.arg") !dbg !38
{
entry:
  %"cstr" = alloca i8*
  %"s.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !79
  store i8* %"cstr.arg", i8** %"cstr"
  call void @"llvm.dbg.declare"(metadata i8** %"cstr", metadata !77, metadata !7), !dbg !78
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.addr", metadata !80, metadata !7), !dbg !81
  %".6" = load i8*, i8** %"cstr", !dbg !82
  %".7" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !82
  %".8" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", i32 0, i32 0 , !dbg !82
  store i8* %".6", i8** %".8", !dbg !82
  %".10" = load i8*, i8** %"cstr", !dbg !83
  %".11" = call i64 @"strlen"(i8* %".10"), !dbg !83
  %".12" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !83
  %".13" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", i32 0, i32 1 , !dbg !83
  store i64 %".11", i64* %".13", !dbg !83
  %".15" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !84
  ret %"struct.ritz_module_1.StrView" %".15", !dbg !84
}

define i64 @"strview_len"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !39
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !86, metadata !7), !dbg !87
  %".4" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !88
  %".5" = load i64, i64* %".4", !dbg !88
  ret i64 %".5", !dbg !88
}

define i32 @"strview_is_empty"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !40
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !89, metadata !7), !dbg !90
  %".4" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !91
  %".5" = load i64, i64* %".4", !dbg !91
  %".6" = icmp eq i64 %".5", 0 , !dbg !91
  br i1 %".6", label %"if.then", label %"if.end", !dbg !91
if.then:
  %".8" = trunc i64 1 to i32 , !dbg !92
  ret i32 %".8", !dbg !92
if.end:
  %".10" = trunc i64 0 to i32 , !dbg !93
  ret i32 %".10", !dbg !93
}

define i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %"idx.arg") !dbg !41
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !94, metadata !7), !dbg !95
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !96, metadata !7), !dbg !95
  %".7" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !97
  %".8" = load i8*, i8** %".7", !dbg !97
  %".9" = load i64, i64* %"idx", !dbg !97
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !97
  %".11" = load i8, i8* %".10", !dbg !97
  ret i8 %".11", !dbg !97
}

define i8* @"strview_as_ptr"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !42
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !98, metadata !7), !dbg !99
  %".4" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !100
  %".5" = load i8*, i8** %".4", !dbg !100
  ret i8* %".5", !dbg !100
}

define i8* @"strview_to_cstr"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !43
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !101, metadata !7), !dbg !102
  %".4" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !103
  %".5" = load i64, i64* %".4", !dbg !103
  %".6" = add i64 %".5", 1, !dbg !103
  %".7" = call i8* @"malloc"(i64 %".6"), !dbg !103
  %".8" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !104
  %".9" = load i8*, i8** %".8", !dbg !104
  %".10" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !104
  %".11" = load i64, i64* %".10", !dbg !104
  %".12" = call i8* @"memcpy"(i8* %".7", i8* %".9", i64 %".11"), !dbg !104
  %".13" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !105
  %".14" = load i64, i64* %".13", !dbg !105
  %".15" = getelementptr i8, i8* %".7", i64 %".14" , !dbg !105
  %".16" = trunc i64 0 to i8 , !dbg !105
  store i8 %".16", i8* %".15", !dbg !105
  ret i8* %".7", !dbg !106
}

define i8* @"strview_as_cstr_unchecked"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !44
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !107, metadata !7), !dbg !108
  %".4" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !109
  %".5" = load i8*, i8** %".4", !dbg !109
  ret i8* %".5", !dbg !109
}

define i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %"a.arg", %"struct.ritz_module_1.StrView"* %"b.arg") !dbg !45
{
entry:
  %"i" = alloca i64, !dbg !117
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"a.arg", metadata !110, metadata !7), !dbg !111
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"b.arg", metadata !112, metadata !7), !dbg !111
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"a.arg", i32 0, i32 1 , !dbg !113
  %".7" = load i64, i64* %".6", !dbg !113
  %".8" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"b.arg", i32 0, i32 1 , !dbg !113
  %".9" = load i64, i64* %".8", !dbg !113
  %".10" = icmp ne i64 %".7", %".9" , !dbg !113
  br i1 %".10", label %"if.then", label %"if.end", !dbg !113
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !114
  ret i32 %".12", !dbg !114
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"a.arg", i32 0, i32 1 , !dbg !115
  %".15" = load i64, i64* %".14", !dbg !115
  %".16" = icmp eq i64 %".15", 0 , !dbg !115
  br i1 %".16", label %"if.then.1", label %"if.end.1", !dbg !115
if.then.1:
  %".18" = trunc i64 1 to i32 , !dbg !116
  ret i32 %".18", !dbg !116
if.end.1:
  %".20" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"a.arg", i32 0, i32 1 , !dbg !117
  %".21" = load i64, i64* %".20", !dbg !117
  store i64 0, i64* %"i", !dbg !117
  br label %"for.cond", !dbg !117
for.cond:
  %".24" = load i64, i64* %"i", !dbg !117
  %".25" = icmp slt i64 %".24", %".21" , !dbg !117
  br i1 %".25", label %"for.body", label %"for.end", !dbg !117
for.body:
  %".27" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"a.arg", i32 0, i32 0 , !dbg !117
  %".28" = load i8*, i8** %".27", !dbg !117
  %".29" = load i64, i64* %"i", !dbg !117
  %".30" = getelementptr i8, i8* %".28", i64 %".29" , !dbg !117
  %".31" = load i8, i8* %".30", !dbg !117
  %".32" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"b.arg", i32 0, i32 0 , !dbg !117
  %".33" = load i8*, i8** %".32", !dbg !117
  %".34" = load i64, i64* %"i", !dbg !117
  %".35" = getelementptr i8, i8* %".33", i64 %".34" , !dbg !117
  %".36" = load i8, i8* %".35", !dbg !117
  %".37" = icmp ne i8 %".31", %".36" , !dbg !117
  br i1 %".37", label %"if.then.2", label %"if.end.2", !dbg !117
for.incr:
  %".42" = load i64, i64* %"i", !dbg !118
  %".43" = add i64 %".42", 1, !dbg !118
  store i64 %".43", i64* %"i", !dbg !118
  br label %"for.cond", !dbg !118
for.end:
  %".46" = trunc i64 1 to i32 , !dbg !119
  ret i32 %".46", !dbg !119
if.then.2:
  %".39" = trunc i64 0 to i32 , !dbg !118
  ret i32 %".39", !dbg !118
if.end.2:
  br label %"for.incr", !dbg !118
}

define i32 @"strview_eq_cstr"(%"struct.ritz_module_1.StrView"* %"s.arg", i8* %"cstr.arg") !dbg !46
{
entry:
  %"i.addr" = alloca i64, !dbg !123
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !120, metadata !7), !dbg !121
  %"cstr" = alloca i8*
  store i8* %"cstr.arg", i8** %"cstr"
  call void @"llvm.dbg.declare"(metadata i8** %"cstr", metadata !122, metadata !7), !dbg !121
  store i64 0, i64* %"i.addr", !dbg !123
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !124, metadata !7), !dbg !125
  br label %"while.cond", !dbg !126
while.cond:
  %".10" = load i64, i64* %"i.addr", !dbg !126
  %".11" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !126
  %".12" = load i64, i64* %".11", !dbg !126
  %".13" = icmp slt i64 %".10", %".12" , !dbg !126
  br i1 %".13", label %"while.body", label %"while.end", !dbg !126
while.body:
  %".15" = load i8*, i8** %"cstr", !dbg !127
  %".16" = load i64, i64* %"i.addr", !dbg !127
  %".17" = getelementptr i8, i8* %".15", i64 %".16" , !dbg !127
  %".18" = load i8, i8* %".17", !dbg !127
  %".19" = zext i8 %".18" to i64 , !dbg !127
  %".20" = icmp eq i64 %".19", 0 , !dbg !127
  br i1 %".20", label %"if.then", label %"if.end", !dbg !127
while.end:
  %".41" = load i8*, i8** %"cstr", !dbg !132
  %".42" = load i64, i64* %"i.addr", !dbg !132
  %".43" = getelementptr i8, i8* %".41", i64 %".42" , !dbg !132
  %".44" = load i8, i8* %".43", !dbg !132
  %".45" = zext i8 %".44" to i64 , !dbg !132
  %".46" = icmp ne i64 %".45", 0 , !dbg !132
  br i1 %".46", label %"if.then.2", label %"if.end.2", !dbg !132
if.then:
  %".22" = trunc i64 0 to i32 , !dbg !128
  ret i32 %".22", !dbg !128
if.end:
  %".24" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !129
  %".25" = load i8*, i8** %".24", !dbg !129
  %".26" = load i64, i64* %"i.addr", !dbg !129
  %".27" = getelementptr i8, i8* %".25", i64 %".26" , !dbg !129
  %".28" = load i8, i8* %".27", !dbg !129
  %".29" = load i8*, i8** %"cstr", !dbg !129
  %".30" = load i64, i64* %"i.addr", !dbg !129
  %".31" = getelementptr i8, i8* %".29", i64 %".30" , !dbg !129
  %".32" = load i8, i8* %".31", !dbg !129
  %".33" = icmp ne i8 %".28", %".32" , !dbg !129
  br i1 %".33", label %"if.then.1", label %"if.end.1", !dbg !129
if.then.1:
  %".35" = trunc i64 0 to i32 , !dbg !130
  ret i32 %".35", !dbg !130
if.end.1:
  %".37" = load i64, i64* %"i.addr", !dbg !131
  %".38" = add i64 %".37", 1, !dbg !131
  store i64 %".38", i64* %"i.addr", !dbg !131
  br label %"while.cond", !dbg !131
if.then.2:
  %".48" = trunc i64 0 to i32 , !dbg !133
  ret i32 %".48", !dbg !133
if.end.2:
  %".50" = trunc i64 1 to i32 , !dbg !134
  ret i32 %".50", !dbg !134
}

define %"struct.ritz_module_1.StrView" @"strview_slice"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %"start.arg", i64 %"end.arg") !dbg !47
{
entry:
  %"result.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !139
  %"st.addr" = alloca i64, !dbg !142
  %"en.addr" = alloca i64, !dbg !145
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !135, metadata !7), !dbg !136
  %"start" = alloca i64
  store i64 %"start.arg", i64* %"start"
  call void @"llvm.dbg.declare"(metadata i64* %"start", metadata !137, metadata !7), !dbg !136
  %"end" = alloca i64
  store i64 %"end.arg", i64* %"end"
  call void @"llvm.dbg.declare"(metadata i64* %"end", metadata !138, metadata !7), !dbg !136
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"result.addr", metadata !140, metadata !7), !dbg !141
  %".11" = load i64, i64* %"start", !dbg !142
  store i64 %".11", i64* %"st.addr", !dbg !142
  call void @"llvm.dbg.declare"(metadata i64* %"st.addr", metadata !143, metadata !7), !dbg !144
  %".14" = load i64, i64* %"end", !dbg !145
  store i64 %".14", i64* %"en.addr", !dbg !145
  call void @"llvm.dbg.declare"(metadata i64* %"en.addr", metadata !146, metadata !7), !dbg !147
  %".17" = load i64, i64* %"st.addr", !dbg !148
  %".18" = icmp slt i64 %".17", 0 , !dbg !148
  br i1 %".18", label %"if.then", label %"if.end", !dbg !148
if.then:
  store i64 0, i64* %"st.addr", !dbg !149
  br label %"if.end", !dbg !149
if.end:
  %".22" = load i64, i64* %"en.addr", !dbg !150
  %".23" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !150
  %".24" = load i64, i64* %".23", !dbg !150
  %".25" = icmp sgt i64 %".22", %".24" , !dbg !150
  br i1 %".25", label %"if.then.1", label %"if.end.1", !dbg !150
if.then.1:
  %".27" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !151
  %".28" = load i64, i64* %".27", !dbg !151
  store i64 %".28", i64* %"en.addr", !dbg !151
  br label %"if.end.1", !dbg !151
if.end.1:
  %".31" = load i64, i64* %"st.addr", !dbg !152
  %".32" = load i64, i64* %"en.addr", !dbg !152
  %".33" = icmp sge i64 %".31", %".32" , !dbg !152
  br i1 %".33", label %"if.then.2", label %"if.end.2", !dbg !152
if.then.2:
  %".35" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !153
  %".36" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !153
  store i8* null, i8** %".36", !dbg !153
  %".38" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !154
  %".39" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !154
  store i64 0, i64* %".39", !dbg !154
  %".41" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !155
  ret %"struct.ritz_module_1.StrView" %".41", !dbg !155
if.end.2:
  %".43" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !156
  %".44" = load i8*, i8** %".43", !dbg !156
  %".45" = load i64, i64* %"st.addr", !dbg !156
  %".46" = getelementptr i8, i8* %".44", i64 %".45" , !dbg !156
  %".47" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !156
  %".48" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !156
  store i8* %".46", i8** %".48", !dbg !156
  %".50" = load i64, i64* %"en.addr", !dbg !157
  %".51" = load i64, i64* %"st.addr", !dbg !157
  %".52" = sub i64 %".50", %".51", !dbg !157
  %".53" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !157
  %".54" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !157
  store i64 %".52", i64* %".54", !dbg !157
  %".56" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !158
  ret %"struct.ritz_module_1.StrView" %".56", !dbg !158
}

define %"struct.ritz_module_1.StrView" @"strview_take"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %"n.arg") !dbg !48
{
entry:
  %"result.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !162
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !159, metadata !7), !dbg !160
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !161, metadata !7), !dbg !160
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"result.addr", metadata !163, metadata !7), !dbg !164
  %".8" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !165
  %".9" = load i8*, i8** %".8", !dbg !165
  %".10" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !165
  %".11" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !165
  store i8* %".9", i8** %".11", !dbg !165
  %".13" = load i64, i64* %"n", !dbg !166
  %".14" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !166
  %".15" = load i64, i64* %".14", !dbg !166
  %".16" = icmp slt i64 %".13", %".15" , !dbg !166
  br i1 %".16", label %"if.then", label %"if.else", !dbg !166
if.then:
  %".18" = load i64, i64* %"n", !dbg !167
  %".19" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !167
  %".20" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !167
  store i64 %".18", i64* %".20", !dbg !167
  br label %"if.end", !dbg !168
if.else:
  %".22" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !168
  %".23" = load i64, i64* %".22", !dbg !168
  %".24" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !168
  %".25" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !168
  store i64 %".23", i64* %".25", !dbg !168
  br label %"if.end", !dbg !168
if.end:
  %".29" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !169
  ret %"struct.ritz_module_1.StrView" %".29", !dbg !169
}

define %"struct.ritz_module_1.StrView" @"strview_skip"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %"n.arg") !dbg !49
{
entry:
  %"result.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !173
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !170, metadata !7), !dbg !171
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !172, metadata !7), !dbg !171
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"result.addr", metadata !174, metadata !7), !dbg !175
  %".8" = load i64, i64* %"n", !dbg !176
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !176
  %".10" = load i64, i64* %".9", !dbg !176
  %".11" = icmp sge i64 %".8", %".10" , !dbg !176
  br i1 %".11", label %"if.then", label %"if.else", !dbg !176
if.then:
  %".13" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !177
  %".14" = load i8*, i8** %".13", !dbg !177
  %".15" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !177
  %".16" = load i64, i64* %".15", !dbg !177
  %".17" = getelementptr i8, i8* %".14", i64 %".16" , !dbg !177
  %".18" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !177
  %".19" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !177
  store i8* %".17", i8** %".19", !dbg !177
  %".21" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !178
  %".22" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !178
  store i64 0, i64* %".22", !dbg !178
  br label %"if.end", !dbg !180
if.else:
  %".24" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !179
  %".25" = load i8*, i8** %".24", !dbg !179
  %".26" = load i64, i64* %"n", !dbg !179
  %".27" = getelementptr i8, i8* %".25", i64 %".26" , !dbg !179
  %".28" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !179
  %".29" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !179
  store i8* %".27", i8** %".29", !dbg !179
  %".31" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !180
  %".32" = load i64, i64* %".31", !dbg !180
  %".33" = load i64, i64* %"n", !dbg !180
  %".34" = sub i64 %".32", %".33", !dbg !180
  %".35" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !180
  %".36" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !180
  store i64 %".34", i64* %".36", !dbg !180
  br label %"if.end", !dbg !180
if.end:
  %".40" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !181
  ret %"struct.ritz_module_1.StrView" %".40", !dbg !181
}

define i32 @"strview_starts_with"(%"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"* %"prefix.arg") !dbg !50
{
entry:
  %"i" = alloca i64, !dbg !187
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !182, metadata !7), !dbg !183
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"prefix.arg", metadata !184, metadata !7), !dbg !183
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"prefix.arg", i32 0, i32 1 , !dbg !185
  %".7" = load i64, i64* %".6", !dbg !185
  %".8" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !185
  %".9" = load i64, i64* %".8", !dbg !185
  %".10" = icmp sgt i64 %".7", %".9" , !dbg !185
  br i1 %".10", label %"if.then", label %"if.end", !dbg !185
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !186
  ret i32 %".12", !dbg !186
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"prefix.arg", i32 0, i32 1 , !dbg !187
  %".15" = load i64, i64* %".14", !dbg !187
  store i64 0, i64* %"i", !dbg !187
  br label %"for.cond", !dbg !187
for.cond:
  %".18" = load i64, i64* %"i", !dbg !187
  %".19" = icmp slt i64 %".18", %".15" , !dbg !187
  br i1 %".19", label %"for.body", label %"for.end", !dbg !187
for.body:
  %".21" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !187
  %".22" = load i8*, i8** %".21", !dbg !187
  %".23" = load i64, i64* %"i", !dbg !187
  %".24" = getelementptr i8, i8* %".22", i64 %".23" , !dbg !187
  %".25" = load i8, i8* %".24", !dbg !187
  %".26" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"prefix.arg", i32 0, i32 0 , !dbg !187
  %".27" = load i8*, i8** %".26", !dbg !187
  %".28" = load i64, i64* %"i", !dbg !187
  %".29" = getelementptr i8, i8* %".27", i64 %".28" , !dbg !187
  %".30" = load i8, i8* %".29", !dbg !187
  %".31" = icmp ne i8 %".25", %".30" , !dbg !187
  br i1 %".31", label %"if.then.1", label %"if.end.1", !dbg !187
for.incr:
  %".36" = load i64, i64* %"i", !dbg !188
  %".37" = add i64 %".36", 1, !dbg !188
  store i64 %".37", i64* %"i", !dbg !188
  br label %"for.cond", !dbg !188
for.end:
  %".40" = trunc i64 1 to i32 , !dbg !189
  ret i32 %".40", !dbg !189
if.then.1:
  %".33" = trunc i64 0 to i32 , !dbg !188
  ret i32 %".33", !dbg !188
if.end.1:
  br label %"for.incr", !dbg !188
}

define i32 @"strview_starts_with_cstr"(%"struct.ritz_module_1.StrView"* %"s.arg", i8* %"prefix.arg") !dbg !51
{
entry:
  %"i.addr" = alloca i64, !dbg !193
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !190, metadata !7), !dbg !191
  %"prefix" = alloca i8*
  store i8* %"prefix.arg", i8** %"prefix"
  call void @"llvm.dbg.declare"(metadata i8** %"prefix", metadata !192, metadata !7), !dbg !191
  store i64 0, i64* %"i.addr", !dbg !193
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !194, metadata !7), !dbg !195
  br label %"while.cond", !dbg !196
while.cond:
  %".10" = load i8*, i8** %"prefix", !dbg !196
  %".11" = load i64, i64* %"i.addr", !dbg !196
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !196
  %".13" = load i8, i8* %".12", !dbg !196
  %".14" = zext i8 %".13" to i64 , !dbg !196
  %".15" = icmp ne i64 %".14", 0 , !dbg !196
  br i1 %".15", label %"while.body", label %"while.end", !dbg !196
while.body:
  %".17" = load i64, i64* %"i.addr", !dbg !197
  %".18" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !197
  %".19" = load i64, i64* %".18", !dbg !197
  %".20" = icmp sge i64 %".17", %".19" , !dbg !197
  br i1 %".20", label %"if.then", label %"if.end", !dbg !197
while.end:
  %".41" = trunc i64 1 to i32 , !dbg !202
  ret i32 %".41", !dbg !202
if.then:
  %".22" = trunc i64 0 to i32 , !dbg !198
  ret i32 %".22", !dbg !198
if.end:
  %".24" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !199
  %".25" = load i8*, i8** %".24", !dbg !199
  %".26" = load i64, i64* %"i.addr", !dbg !199
  %".27" = getelementptr i8, i8* %".25", i64 %".26" , !dbg !199
  %".28" = load i8, i8* %".27", !dbg !199
  %".29" = load i8*, i8** %"prefix", !dbg !199
  %".30" = load i64, i64* %"i.addr", !dbg !199
  %".31" = getelementptr i8, i8* %".29", i64 %".30" , !dbg !199
  %".32" = load i8, i8* %".31", !dbg !199
  %".33" = icmp ne i8 %".28", %".32" , !dbg !199
  br i1 %".33", label %"if.then.1", label %"if.end.1", !dbg !199
if.then.1:
  %".35" = trunc i64 0 to i32 , !dbg !200
  ret i32 %".35", !dbg !200
if.end.1:
  %".37" = load i64, i64* %"i.addr", !dbg !201
  %".38" = add i64 %".37", 1, !dbg !201
  store i64 %".38", i64* %"i.addr", !dbg !201
  br label %"while.cond", !dbg !201
}

define i32 @"strview_ends_with"(%"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"* %"suffix.arg") !dbg !52
{
entry:
  %"i" = alloca i64, !dbg !209
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !203, metadata !7), !dbg !204
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"suffix.arg", metadata !205, metadata !7), !dbg !204
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"suffix.arg", i32 0, i32 1 , !dbg !206
  %".7" = load i64, i64* %".6", !dbg !206
  %".8" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !206
  %".9" = load i64, i64* %".8", !dbg !206
  %".10" = icmp sgt i64 %".7", %".9" , !dbg !206
  br i1 %".10", label %"if.then", label %"if.end", !dbg !206
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !207
  ret i32 %".12", !dbg !207
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !208
  %".15" = load i64, i64* %".14", !dbg !208
  %".16" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"suffix.arg", i32 0, i32 1 , !dbg !208
  %".17" = load i64, i64* %".16", !dbg !208
  %".18" = sub i64 %".15", %".17", !dbg !208
  %".19" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"suffix.arg", i32 0, i32 1 , !dbg !209
  %".20" = load i64, i64* %".19", !dbg !209
  store i64 0, i64* %"i", !dbg !209
  br label %"for.cond", !dbg !209
for.cond:
  %".23" = load i64, i64* %"i", !dbg !209
  %".24" = icmp slt i64 %".23", %".20" , !dbg !209
  br i1 %".24", label %"for.body", label %"for.end", !dbg !209
for.body:
  %".26" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !209
  %".27" = load i8*, i8** %".26", !dbg !209
  %".28" = getelementptr i8, i8* %".27", i64 %".18" , !dbg !209
  %".29" = load i64, i64* %"i", !dbg !209
  %".30" = getelementptr i8, i8* %".28", i64 %".29" , !dbg !209
  %".31" = load i8, i8* %".30", !dbg !209
  %".32" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"suffix.arg", i32 0, i32 0 , !dbg !209
  %".33" = load i8*, i8** %".32", !dbg !209
  %".34" = load i64, i64* %"i", !dbg !209
  %".35" = getelementptr i8, i8* %".33", i64 %".34" , !dbg !209
  %".36" = load i8, i8* %".35", !dbg !209
  %".37" = icmp ne i8 %".31", %".36" , !dbg !209
  br i1 %".37", label %"if.then.1", label %"if.end.1", !dbg !209
for.incr:
  %".42" = load i64, i64* %"i", !dbg !210
  %".43" = add i64 %".42", 1, !dbg !210
  store i64 %".43", i64* %"i", !dbg !210
  br label %"for.cond", !dbg !210
for.end:
  %".46" = trunc i64 1 to i32 , !dbg !211
  ret i32 %".46", !dbg !211
if.then.1:
  %".39" = trunc i64 0 to i32 , !dbg !210
  ret i32 %".39", !dbg !210
if.end.1:
  br label %"for.incr", !dbg !210
}

define i32 @"strview_contains"(%"struct.ritz_module_1.StrView"* %"haystack.arg", %"struct.ritz_module_1.StrView"* %"needle.arg") !dbg !53
{
entry:
  %"pos.addr" = alloca i64, !dbg !219
  %"found.addr" = alloca i32, !dbg !224
  %"i.addr" = alloca i64, !dbg !227
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"haystack.arg", metadata !212, metadata !7), !dbg !213
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"needle.arg", metadata !214, metadata !7), !dbg !213
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"needle.arg", i32 0, i32 1 , !dbg !215
  %".7" = load i64, i64* %".6", !dbg !215
  %".8" = icmp eq i64 %".7", 0 , !dbg !215
  br i1 %".8", label %"if.then", label %"if.end", !dbg !215
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !216
  ret i32 %".10", !dbg !216
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"haystack.arg", i32 0, i32 1 , !dbg !217
  %".13" = load i64, i64* %".12", !dbg !217
  %".14" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"needle.arg", i32 0, i32 1 , !dbg !217
  %".15" = load i64, i64* %".14", !dbg !217
  %".16" = icmp slt i64 %".13", %".15" , !dbg !217
  br i1 %".16", label %"if.then.1", label %"if.end.1", !dbg !217
if.then.1:
  %".18" = trunc i64 0 to i32 , !dbg !218
  ret i32 %".18", !dbg !218
if.end.1:
  store i64 0, i64* %"pos.addr", !dbg !219
  call void @"llvm.dbg.declare"(metadata i64* %"pos.addr", metadata !220, metadata !7), !dbg !221
  %".22" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"haystack.arg", i32 0, i32 1 , !dbg !222
  %".23" = load i64, i64* %".22", !dbg !222
  %".24" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"needle.arg", i32 0, i32 1 , !dbg !222
  %".25" = load i64, i64* %".24", !dbg !222
  %".26" = sub i64 %".23", %".25", !dbg !222
  %".27" = add i64 %".26", 1, !dbg !222
  br label %"while.cond", !dbg !223
while.cond:
  %".29" = load i64, i64* %"pos.addr", !dbg !223
  %".30" = icmp slt i64 %".29", %".27" , !dbg !223
  br i1 %".30", label %"while.body", label %"while.end", !dbg !223
while.body:
  %".32" = trunc i64 1 to i32 , !dbg !224
  store i32 %".32", i32* %"found.addr", !dbg !224
  call void @"llvm.dbg.declare"(metadata i32* %"found.addr", metadata !225, metadata !7), !dbg !226
  store i64 0, i64* %"i.addr", !dbg !227
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !228, metadata !7), !dbg !229
  br label %"while.cond.1", !dbg !230
while.end:
  %".80" = trunc i64 0 to i32 , !dbg !237
  ret i32 %".80", !dbg !237
while.cond.1:
  %".38" = load i64, i64* %"i.addr", !dbg !230
  %".39" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"needle.arg", i32 0, i32 1 , !dbg !230
  %".40" = load i64, i64* %".39", !dbg !230
  %".41" = icmp slt i64 %".38", %".40" , !dbg !230
  br i1 %".41", label %"and.right", label %"and.merge", !dbg !230
while.body.1:
  %".49" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"haystack.arg", i32 0, i32 0 , !dbg !231
  %".50" = load i8*, i8** %".49", !dbg !231
  %".51" = load i64, i64* %"pos.addr", !dbg !231
  %".52" = getelementptr i8, i8* %".50", i64 %".51" , !dbg !231
  %".53" = load i64, i64* %"i.addr", !dbg !231
  %".54" = getelementptr i8, i8* %".52", i64 %".53" , !dbg !231
  %".55" = load i8, i8* %".54", !dbg !231
  %".56" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"needle.arg", i32 0, i32 0 , !dbg !231
  %".57" = load i8*, i8** %".56", !dbg !231
  %".58" = load i64, i64* %"i.addr", !dbg !231
  %".59" = getelementptr i8, i8* %".57", i64 %".58" , !dbg !231
  %".60" = load i8, i8* %".59", !dbg !231
  %".61" = icmp ne i8 %".55", %".60" , !dbg !231
  br i1 %".61", label %"if.then.2", label %"if.end.2", !dbg !231
while.end.1:
  %".70" = load i32, i32* %"found.addr", !dbg !234
  %".71" = sext i32 %".70" to i64 , !dbg !234
  %".72" = icmp eq i64 %".71", 1 , !dbg !234
  br i1 %".72", label %"if.then.3", label %"if.end.3", !dbg !234
and.right:
  %".43" = load i32, i32* %"found.addr", !dbg !230
  %".44" = sext i32 %".43" to i64 , !dbg !230
  %".45" = icmp eq i64 %".44", 1 , !dbg !230
  br label %"and.merge", !dbg !230
and.merge:
  %".47" = phi  i1 [0, %"while.cond.1"], [%".45", %"and.right"] , !dbg !230
  br i1 %".47", label %"while.body.1", label %"while.end.1", !dbg !230
if.then.2:
  %".63" = trunc i64 0 to i32 , !dbg !232
  store i32 %".63", i32* %"found.addr", !dbg !232
  br label %"if.end.2", !dbg !232
if.end.2:
  %".66" = load i64, i64* %"i.addr", !dbg !233
  %".67" = add i64 %".66", 1, !dbg !233
  store i64 %".67", i64* %"i.addr", !dbg !233
  br label %"while.cond.1", !dbg !233
if.then.3:
  %".74" = trunc i64 1 to i32 , !dbg !235
  ret i32 %".74", !dbg !235
if.end.3:
  %".76" = load i64, i64* %"pos.addr", !dbg !236
  %".77" = add i64 %".76", 1, !dbg !236
  store i64 %".77", i64* %"pos.addr", !dbg !236
  br label %"while.cond", !dbg !236
}

define i64 @"strview_find"(%"struct.ritz_module_1.StrView"* %"haystack.arg", %"struct.ritz_module_1.StrView"* %"needle.arg") !dbg !54
{
entry:
  %"pos.addr" = alloca i64, !dbg !245
  %"found.addr" = alloca i32, !dbg !250
  %"i.addr" = alloca i64, !dbg !253
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"haystack.arg", metadata !238, metadata !7), !dbg !239
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"needle.arg", metadata !240, metadata !7), !dbg !239
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"needle.arg", i32 0, i32 1 , !dbg !241
  %".7" = load i64, i64* %".6", !dbg !241
  %".8" = icmp eq i64 %".7", 0 , !dbg !241
  br i1 %".8", label %"if.then", label %"if.end", !dbg !241
if.then:
  ret i64 0, !dbg !242
if.end:
  %".11" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"haystack.arg", i32 0, i32 1 , !dbg !243
  %".12" = load i64, i64* %".11", !dbg !243
  %".13" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"needle.arg", i32 0, i32 1 , !dbg !243
  %".14" = load i64, i64* %".13", !dbg !243
  %".15" = icmp slt i64 %".12", %".14" , !dbg !243
  br i1 %".15", label %"if.then.1", label %"if.end.1", !dbg !243
if.then.1:
  %".17" = sub i64 0, 1, !dbg !244
  ret i64 %".17", !dbg !244
if.end.1:
  store i64 0, i64* %"pos.addr", !dbg !245
  call void @"llvm.dbg.declare"(metadata i64* %"pos.addr", metadata !246, metadata !7), !dbg !247
  %".21" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"haystack.arg", i32 0, i32 1 , !dbg !248
  %".22" = load i64, i64* %".21", !dbg !248
  %".23" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"needle.arg", i32 0, i32 1 , !dbg !248
  %".24" = load i64, i64* %".23", !dbg !248
  %".25" = sub i64 %".22", %".24", !dbg !248
  %".26" = add i64 %".25", 1, !dbg !248
  br label %"while.cond", !dbg !249
while.cond:
  %".28" = load i64, i64* %"pos.addr", !dbg !249
  %".29" = icmp slt i64 %".28", %".26" , !dbg !249
  br i1 %".29", label %"while.body", label %"while.end", !dbg !249
while.body:
  %".31" = trunc i64 1 to i32 , !dbg !250
  store i32 %".31", i32* %"found.addr", !dbg !250
  call void @"llvm.dbg.declare"(metadata i32* %"found.addr", metadata !251, metadata !7), !dbg !252
  store i64 0, i64* %"i.addr", !dbg !253
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !254, metadata !7), !dbg !255
  br label %"while.cond.1", !dbg !256
while.end:
  %".79" = sub i64 0, 1, !dbg !263
  ret i64 %".79", !dbg !263
while.cond.1:
  %".37" = load i64, i64* %"i.addr", !dbg !256
  %".38" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"needle.arg", i32 0, i32 1 , !dbg !256
  %".39" = load i64, i64* %".38", !dbg !256
  %".40" = icmp slt i64 %".37", %".39" , !dbg !256
  br i1 %".40", label %"and.right", label %"and.merge", !dbg !256
while.body.1:
  %".48" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"haystack.arg", i32 0, i32 0 , !dbg !257
  %".49" = load i8*, i8** %".48", !dbg !257
  %".50" = load i64, i64* %"pos.addr", !dbg !257
  %".51" = getelementptr i8, i8* %".49", i64 %".50" , !dbg !257
  %".52" = load i64, i64* %"i.addr", !dbg !257
  %".53" = getelementptr i8, i8* %".51", i64 %".52" , !dbg !257
  %".54" = load i8, i8* %".53", !dbg !257
  %".55" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"needle.arg", i32 0, i32 0 , !dbg !257
  %".56" = load i8*, i8** %".55", !dbg !257
  %".57" = load i64, i64* %"i.addr", !dbg !257
  %".58" = getelementptr i8, i8* %".56", i64 %".57" , !dbg !257
  %".59" = load i8, i8* %".58", !dbg !257
  %".60" = icmp ne i8 %".54", %".59" , !dbg !257
  br i1 %".60", label %"if.then.2", label %"if.end.2", !dbg !257
while.end.1:
  %".69" = load i32, i32* %"found.addr", !dbg !260
  %".70" = sext i32 %".69" to i64 , !dbg !260
  %".71" = icmp eq i64 %".70", 1 , !dbg !260
  br i1 %".71", label %"if.then.3", label %"if.end.3", !dbg !260
and.right:
  %".42" = load i32, i32* %"found.addr", !dbg !256
  %".43" = sext i32 %".42" to i64 , !dbg !256
  %".44" = icmp eq i64 %".43", 1 , !dbg !256
  br label %"and.merge", !dbg !256
and.merge:
  %".46" = phi  i1 [0, %"while.cond.1"], [%".44", %"and.right"] , !dbg !256
  br i1 %".46", label %"while.body.1", label %"while.end.1", !dbg !256
if.then.2:
  %".62" = trunc i64 0 to i32 , !dbg !258
  store i32 %".62", i32* %"found.addr", !dbg !258
  br label %"if.end.2", !dbg !258
if.end.2:
  %".65" = load i64, i64* %"i.addr", !dbg !259
  %".66" = add i64 %".65", 1, !dbg !259
  store i64 %".66", i64* %"i.addr", !dbg !259
  br label %"while.cond.1", !dbg !259
if.then.3:
  %".73" = load i64, i64* %"pos.addr", !dbg !261
  ret i64 %".73", !dbg !261
if.end.3:
  %".75" = load i64, i64* %"pos.addr", !dbg !262
  %".76" = add i64 %".75", 1, !dbg !262
  store i64 %".76", i64* %"pos.addr", !dbg !262
  br label %"while.cond", !dbg !262
}

define i64 @"strview_find_byte"(%"struct.ritz_module_1.StrView"* %"s.arg", i8 %"c.arg") !dbg !55
{
entry:
  %"i" = alloca i64, !dbg !267
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !264, metadata !7), !dbg !265
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !266, metadata !7), !dbg !265
  %".7" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !267
  %".8" = load i64, i64* %".7", !dbg !267
  store i64 0, i64* %"i", !dbg !267
  br label %"for.cond", !dbg !267
for.cond:
  %".11" = load i64, i64* %"i", !dbg !267
  %".12" = icmp slt i64 %".11", %".8" , !dbg !267
  br i1 %".12", label %"for.body", label %"for.end", !dbg !267
for.body:
  %".14" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !267
  %".15" = load i8*, i8** %".14", !dbg !267
  %".16" = load i64, i64* %"i", !dbg !267
  %".17" = getelementptr i8, i8* %".15", i64 %".16" , !dbg !267
  %".18" = load i8, i8* %".17", !dbg !267
  %".19" = load i8, i8* %"c", !dbg !267
  %".20" = icmp eq i8 %".18", %".19" , !dbg !267
  br i1 %".20", label %"if.then", label %"if.end", !dbg !267
for.incr:
  %".25" = load i64, i64* %"i", !dbg !268
  %".26" = add i64 %".25", 1, !dbg !268
  store i64 %".26", i64* %"i", !dbg !268
  br label %"for.cond", !dbg !268
for.end:
  %".29" = sub i64 0, 1, !dbg !269
  ret i64 %".29", !dbg !269
if.then:
  %".22" = load i64, i64* %"i", !dbg !268
  ret i64 %".22", !dbg !268
if.end:
  br label %"for.incr", !dbg !268
}

define i32 @"strview_split_once"(%"struct.ritz_module_1.StrView"* %"s.arg", i8 %"delim.arg", %"struct.ritz_module_1.StrView"* %"before.arg", %"struct.ritz_module_1.StrView"* %"after.arg") !dbg !56
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !270, metadata !7), !dbg !271
  %"delim" = alloca i8
  store i8 %"delim.arg", i8* %"delim"
  call void @"llvm.dbg.declare"(metadata i8* %"delim", metadata !272, metadata !7), !dbg !271
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"before.arg", metadata !273, metadata !7), !dbg !271
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"after.arg", metadata !274, metadata !7), !dbg !271
  %".11" = load i8, i8* %"delim", !dbg !275
  %".12" = call i64 @"strview_find_byte"(%"struct.ritz_module_1.StrView"* %"s.arg", i8 %".11"), !dbg !275
  %".13" = icmp slt i64 %".12", 0 , !dbg !276
  br i1 %".13", label %"if.then", label %"if.end", !dbg !276
if.then:
  %".15" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !277
  %".16" = load i8*, i8** %".15", !dbg !277
  %".17" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"before.arg", !dbg !277
  %".18" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"before.arg", i32 0, i32 0 , !dbg !277
  store i8* %".16", i8** %".18", !dbg !277
  %".20" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !278
  %".21" = load i64, i64* %".20", !dbg !278
  %".22" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"before.arg", !dbg !278
  %".23" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"before.arg", i32 0, i32 1 , !dbg !278
  store i64 %".21", i64* %".23", !dbg !278
  %".25" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !279
  %".26" = load i8*, i8** %".25", !dbg !279
  %".27" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !279
  %".28" = load i64, i64* %".27", !dbg !279
  %".29" = getelementptr i8, i8* %".26", i64 %".28" , !dbg !279
  %".30" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"after.arg", !dbg !279
  %".31" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"after.arg", i32 0, i32 0 , !dbg !279
  store i8* %".29", i8** %".31", !dbg !279
  %".33" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"after.arg", !dbg !280
  %".34" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"after.arg", i32 0, i32 1 , !dbg !280
  store i64 0, i64* %".34", !dbg !280
  %".36" = trunc i64 0 to i32 , !dbg !281
  ret i32 %".36", !dbg !281
if.end:
  %".38" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !282
  %".39" = load i8*, i8** %".38", !dbg !282
  %".40" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"before.arg", !dbg !282
  %".41" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"before.arg", i32 0, i32 0 , !dbg !282
  store i8* %".39", i8** %".41", !dbg !282
  %".43" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"before.arg", !dbg !283
  %".44" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"before.arg", i32 0, i32 1 , !dbg !283
  store i64 %".12", i64* %".44", !dbg !283
  %".46" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !284
  %".47" = load i8*, i8** %".46", !dbg !284
  %".48" = getelementptr i8, i8* %".47", i64 %".12" , !dbg !284
  %".49" = getelementptr i8, i8* %".48", i64 1 , !dbg !284
  %".50" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"after.arg", !dbg !284
  %".51" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"after.arg", i32 0, i32 0 , !dbg !284
  store i8* %".49", i8** %".51", !dbg !284
  %".53" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !285
  %".54" = load i64, i64* %".53", !dbg !285
  %".55" = sub i64 %".54", %".12", !dbg !285
  %".56" = sub i64 %".55", 1, !dbg !285
  %".57" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"after.arg", !dbg !285
  %".58" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"after.arg", i32 0, i32 1 , !dbg !285
  store i64 %".56", i64* %".58", !dbg !285
  %".60" = trunc i64 1 to i32 , !dbg !286
  ret i32 %".60", !dbg !286
}

define %"struct.ritz_module_1.StrView" @"strview_trim_start"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !57
{
entry:
  %"result.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !289
  %"start.addr" = alloca i64, !dbg !292
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !287, metadata !7), !dbg !288
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"result.addr", metadata !290, metadata !7), !dbg !291
  store i64 0, i64* %"start.addr", !dbg !292
  call void @"llvm.dbg.declare"(metadata i64* %"start.addr", metadata !293, metadata !7), !dbg !294
  br label %"while.cond", !dbg !295
while.cond:
  %".8" = load i64, i64* %"start.addr", !dbg !295
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !295
  %".10" = load i64, i64* %".9", !dbg !295
  %".11" = icmp slt i64 %".8", %".10" , !dbg !295
  br i1 %".11", label %"while.body", label %"while.end", !dbg !295
while.body:
  %".13" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !296
  %".14" = load i8*, i8** %".13", !dbg !296
  %".15" = load i64, i64* %"start.addr", !dbg !296
  %".16" = getelementptr i8, i8* %".14", i64 %".15" , !dbg !296
  %".17" = load i8, i8* %".16", !dbg !296
  %".18" = icmp ne i8 %".17", 32 , !dbg !297
  br i1 %".18", label %"and.right", label %"and.merge", !dbg !297
while.end:
  %".37" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !300
  %".38" = load i8*, i8** %".37", !dbg !300
  %".39" = load i64, i64* %"start.addr", !dbg !300
  %".40" = getelementptr i8, i8* %".38", i64 %".39" , !dbg !300
  %".41" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !300
  %".42" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !300
  store i8* %".40", i8** %".42", !dbg !300
  %".44" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !301
  %".45" = load i64, i64* %".44", !dbg !301
  %".46" = load i64, i64* %"start.addr", !dbg !301
  %".47" = sub i64 %".45", %".46", !dbg !301
  %".48" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !301
  %".49" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !301
  store i64 %".47", i64* %".49", !dbg !301
  %".51" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !302
  ret %"struct.ritz_module_1.StrView" %".51", !dbg !302
and.right:
  %".20" = icmp ne i8 %".17", 9 , !dbg !297
  br label %"and.merge", !dbg !297
and.merge:
  %".22" = phi  i1 [0, %"while.body"], [%".20", %"and.right"] , !dbg !297
  br i1 %".22", label %"and.right.1", label %"and.merge.1", !dbg !297
and.right.1:
  %".24" = icmp ne i8 %".17", 10 , !dbg !297
  br label %"and.merge.1", !dbg !297
and.merge.1:
  %".26" = phi  i1 [0, %"and.merge"], [%".24", %"and.right.1"] , !dbg !297
  br i1 %".26", label %"and.right.2", label %"and.merge.2", !dbg !297
and.right.2:
  %".28" = icmp ne i8 %".17", 13 , !dbg !297
  br label %"and.merge.2", !dbg !297
and.merge.2:
  %".30" = phi  i1 [0, %"and.merge.1"], [%".28", %"and.right.2"] , !dbg !297
  br i1 %".30", label %"if.then", label %"if.end", !dbg !297
if.then:
  br label %"while.end", !dbg !298
if.end:
  %".33" = load i64, i64* %"start.addr", !dbg !299
  %".34" = add i64 %".33", 1, !dbg !299
  store i64 %".34", i64* %"start.addr", !dbg !299
  br label %"while.cond", !dbg !299
}

define %"struct.ritz_module_1.StrView" @"strview_trim_end"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !58
{
entry:
  %"result.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !305
  %"end.addr" = alloca i64, !dbg !308
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !303, metadata !7), !dbg !304
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"result.addr", metadata !306, metadata !7), !dbg !307
  %".5" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !308
  %".6" = load i64, i64* %".5", !dbg !308
  store i64 %".6", i64* %"end.addr", !dbg !308
  call void @"llvm.dbg.declare"(metadata i64* %"end.addr", metadata !309, metadata !7), !dbg !310
  br label %"while.cond", !dbg !311
while.cond:
  %".10" = load i64, i64* %"end.addr", !dbg !311
  %".11" = icmp sgt i64 %".10", 0 , !dbg !311
  br i1 %".11", label %"while.body", label %"while.end", !dbg !311
while.body:
  %".13" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !312
  %".14" = load i8*, i8** %".13", !dbg !312
  %".15" = load i64, i64* %"end.addr", !dbg !312
  %".16" = getelementptr i8, i8* %".14", i64 %".15" , !dbg !312
  %".17" = sub i64 0, 1, !dbg !312
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !312
  %".19" = load i8, i8* %".18", !dbg !312
  %".20" = icmp ne i8 %".19", 32 , !dbg !313
  br i1 %".20", label %"and.right", label %"and.merge", !dbg !313
while.end:
  %".39" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 0 , !dbg !316
  %".40" = load i8*, i8** %".39", !dbg !316
  %".41" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !316
  %".42" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !316
  store i8* %".40", i8** %".42", !dbg !316
  %".44" = load i64, i64* %"end.addr", !dbg !317
  %".45" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !317
  %".46" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !317
  store i64 %".44", i64* %".46", !dbg !317
  %".48" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !318
  ret %"struct.ritz_module_1.StrView" %".48", !dbg !318
and.right:
  %".22" = icmp ne i8 %".19", 9 , !dbg !313
  br label %"and.merge", !dbg !313
and.merge:
  %".24" = phi  i1 [0, %"while.body"], [%".22", %"and.right"] , !dbg !313
  br i1 %".24", label %"and.right.1", label %"and.merge.1", !dbg !313
and.right.1:
  %".26" = icmp ne i8 %".19", 10 , !dbg !313
  br label %"and.merge.1", !dbg !313
and.merge.1:
  %".28" = phi  i1 [0, %"and.merge"], [%".26", %"and.right.1"] , !dbg !313
  br i1 %".28", label %"and.right.2", label %"and.merge.2", !dbg !313
and.right.2:
  %".30" = icmp ne i8 %".19", 13 , !dbg !313
  br label %"and.merge.2", !dbg !313
and.merge.2:
  %".32" = phi  i1 [0, %"and.merge.1"], [%".30", %"and.right.2"] , !dbg !313
  br i1 %".32", label %"if.then", label %"if.end", !dbg !313
if.then:
  br label %"while.end", !dbg !314
if.end:
  %".35" = load i64, i64* %"end.addr", !dbg !315
  %".36" = sub i64 %".35", 1, !dbg !315
  store i64 %".36", i64* %"end.addr", !dbg !315
  br label %"while.cond", !dbg !315
}

define %"struct.ritz_module_1.StrView" @"strview_trim"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !59
{
entry:
  %"trimmed.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !321
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !319, metadata !7), !dbg !320
  %".4" = call %"struct.ritz_module_1.StrView" @"strview_trim_start"(%"struct.ritz_module_1.StrView"* %"s.arg"), !dbg !321
  store %"struct.ritz_module_1.StrView" %".4", %"struct.ritz_module_1.StrView"* %"trimmed.addr", !dbg !321
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"trimmed.addr", metadata !322, metadata !7), !dbg !323
  %".7" = call %"struct.ritz_module_1.StrView" @"strview_trim_end"(%"struct.ritz_module_1.StrView"* %"trimmed.addr"), !dbg !324
  ret %"struct.ritz_module_1.StrView" %".7", !dbg !324
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/ritz/ritzlib", filename: "strview.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 318, name: "StrView_len", scopeLine: 318, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 321, name: "StrView_is_empty", scopeLine: 321, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 324, name: "StrView_get", scopeLine: 324, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 327, name: "StrView_as_ptr", scopeLine: 327, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 330, name: "StrView_slice", scopeLine: 330, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 333, name: "StrView_take", scopeLine: 333, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 336, name: "StrView_skip", scopeLine: 336, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 339, name: "StrView_starts_with", scopeLine: 339, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 342, name: "StrView_ends_with", scopeLine: 342, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 345, name: "StrView_contains", scopeLine: 345, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 348, name: "StrView_find", scopeLine: 348, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 351, name: "StrView_find_byte", scopeLine: 351, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 354, name: "StrView_trim", scopeLine: 354, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 357, name: "StrView_trim_start", scopeLine: 357, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 360, name: "StrView_trim_end", scopeLine: 360, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 363, name: "StrView_eq", scopeLine: 363, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 366, name: "StrView_eq_cstr", scopeLine: 366, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 370, name: "StrView_to_cstr", scopeLine: 370, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 374, name: "StrView_as_cstr_unchecked", scopeLine: 374, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 37, name: "strview_empty", scopeLine: 37, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 44, name: "strview_from_ptr", scopeLine: 44, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 51, name: "strview_from_cstr", scopeLine: 51, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 62, name: "strview_len", scopeLine: 62, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 66, name: "strview_is_empty", scopeLine: 66, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 72, name: "strview_get", scopeLine: 72, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 76, name: "strview_as_ptr", scopeLine: 76, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 87, name: "strview_to_cstr", scopeLine: 87, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 98, name: "strview_as_cstr_unchecked", scopeLine: 98, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 106, name: "strview_eq", scopeLine: 106, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 117, name: "strview_eq_cstr", scopeLine: 117, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 135, name: "strview_slice", scopeLine: 135, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 152, name: "strview_take", scopeLine: 152, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 162, name: "strview_skip", scopeLine: 162, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 177, name: "strview_starts_with", scopeLine: 177, type: !4, unit: !1)
!51 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 186, name: "strview_starts_with_cstr", scopeLine: 186, type: !4, unit: !1)
!52 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 197, name: "strview_ends_with", scopeLine: 197, type: !4, unit: !1)
!53 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 207, name: "strview_contains", scopeLine: 207, type: !4, unit: !1)
!54 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 228, name: "strview_find", scopeLine: 228, type: !4, unit: !1)
!55 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 249, name: "strview_find_byte", scopeLine: 249, type: !4, unit: !1)
!56 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 263, name: "strview_split_once", scopeLine: 263, type: !4, unit: !1)
!57 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 283, name: "strview_trim_start", scopeLine: 283, type: !4, unit: !1)
!58 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 296, name: "strview_trim_end", scopeLine: 296, type: !4, unit: !1)
!59 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 309, name: "strview_trim", scopeLine: 309, type: !4, unit: !1)
!60 = !DILocation(column: 5, line: 38, scope: !36)
!61 = !DICompositeType(align: 64, file: !0, name: "StrView", size: 128, tag: DW_TAG_structure_type)
!62 = !DILocalVariable(file: !0, line: 38, name: "s", scope: !36, type: !61)
!63 = !DILocation(column: 1, line: 38, scope: !36)
!64 = !DILocation(column: 5, line: 39, scope: !36)
!65 = !DILocation(column: 5, line: 40, scope: !36)
!66 = !DILocation(column: 5, line: 41, scope: !36)
!67 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!68 = !DILocalVariable(file: !0, line: 44, name: "ptr", scope: !37, type: !67)
!69 = !DILocation(column: 1, line: 44, scope: !37)
!70 = !DILocalVariable(file: !0, line: 44, name: "len", scope: !37, type: !11)
!71 = !DILocation(column: 5, line: 45, scope: !37)
!72 = !DILocalVariable(file: !0, line: 45, name: "s", scope: !37, type: !61)
!73 = !DILocation(column: 1, line: 45, scope: !37)
!74 = !DILocation(column: 5, line: 46, scope: !37)
!75 = !DILocation(column: 5, line: 47, scope: !37)
!76 = !DILocation(column: 5, line: 48, scope: !37)
!77 = !DILocalVariable(file: !0, line: 51, name: "cstr", scope: !38, type: !67)
!78 = !DILocation(column: 1, line: 51, scope: !38)
!79 = !DILocation(column: 5, line: 52, scope: !38)
!80 = !DILocalVariable(file: !0, line: 52, name: "s", scope: !38, type: !61)
!81 = !DILocation(column: 1, line: 52, scope: !38)
!82 = !DILocation(column: 5, line: 53, scope: !38)
!83 = !DILocation(column: 5, line: 54, scope: !38)
!84 = !DILocation(column: 5, line: 55, scope: !38)
!85 = !DIDerivedType(baseType: !61, size: 64, tag: DW_TAG_reference_type)
!86 = !DILocalVariable(file: !0, line: 62, name: "s", scope: !39, type: !85)
!87 = !DILocation(column: 1, line: 62, scope: !39)
!88 = !DILocation(column: 5, line: 63, scope: !39)
!89 = !DILocalVariable(file: !0, line: 66, name: "s", scope: !40, type: !85)
!90 = !DILocation(column: 1, line: 66, scope: !40)
!91 = !DILocation(column: 5, line: 67, scope: !40)
!92 = !DILocation(column: 9, line: 68, scope: !40)
!93 = !DILocation(column: 5, line: 69, scope: !40)
!94 = !DILocalVariable(file: !0, line: 72, name: "s", scope: !41, type: !85)
!95 = !DILocation(column: 1, line: 72, scope: !41)
!96 = !DILocalVariable(file: !0, line: 72, name: "idx", scope: !41, type: !11)
!97 = !DILocation(column: 5, line: 73, scope: !41)
!98 = !DILocalVariable(file: !0, line: 76, name: "s", scope: !42, type: !85)
!99 = !DILocation(column: 1, line: 76, scope: !42)
!100 = !DILocation(column: 5, line: 77, scope: !42)
!101 = !DILocalVariable(file: !0, line: 87, name: "s", scope: !43, type: !85)
!102 = !DILocation(column: 1, line: 87, scope: !43)
!103 = !DILocation(column: 5, line: 88, scope: !43)
!104 = !DILocation(column: 5, line: 89, scope: !43)
!105 = !DILocation(column: 5, line: 90, scope: !43)
!106 = !DILocation(column: 5, line: 91, scope: !43)
!107 = !DILocalVariable(file: !0, line: 98, name: "s", scope: !44, type: !85)
!108 = !DILocation(column: 1, line: 98, scope: !44)
!109 = !DILocation(column: 5, line: 99, scope: !44)
!110 = !DILocalVariable(file: !0, line: 106, name: "a", scope: !45, type: !85)
!111 = !DILocation(column: 1, line: 106, scope: !45)
!112 = !DILocalVariable(file: !0, line: 106, name: "b", scope: !45, type: !85)
!113 = !DILocation(column: 5, line: 107, scope: !45)
!114 = !DILocation(column: 9, line: 108, scope: !45)
!115 = !DILocation(column: 5, line: 109, scope: !45)
!116 = !DILocation(column: 9, line: 110, scope: !45)
!117 = !DILocation(column: 5, line: 111, scope: !45)
!118 = !DILocation(column: 13, line: 113, scope: !45)
!119 = !DILocation(column: 5, line: 114, scope: !45)
!120 = !DILocalVariable(file: !0, line: 117, name: "s", scope: !46, type: !85)
!121 = !DILocation(column: 1, line: 117, scope: !46)
!122 = !DILocalVariable(file: !0, line: 117, name: "cstr", scope: !46, type: !67)
!123 = !DILocation(column: 5, line: 118, scope: !46)
!124 = !DILocalVariable(file: !0, line: 118, name: "i", scope: !46, type: !11)
!125 = !DILocation(column: 1, line: 118, scope: !46)
!126 = !DILocation(column: 5, line: 119, scope: !46)
!127 = !DILocation(column: 9, line: 120, scope: !46)
!128 = !DILocation(column: 13, line: 121, scope: !46)
!129 = !DILocation(column: 9, line: 122, scope: !46)
!130 = !DILocation(column: 13, line: 123, scope: !46)
!131 = !DILocation(column: 9, line: 124, scope: !46)
!132 = !DILocation(column: 5, line: 126, scope: !46)
!133 = !DILocation(column: 9, line: 127, scope: !46)
!134 = !DILocation(column: 5, line: 128, scope: !46)
!135 = !DILocalVariable(file: !0, line: 135, name: "s", scope: !47, type: !85)
!136 = !DILocation(column: 1, line: 135, scope: !47)
!137 = !DILocalVariable(file: !0, line: 135, name: "start", scope: !47, type: !11)
!138 = !DILocalVariable(file: !0, line: 135, name: "end", scope: !47, type: !11)
!139 = !DILocation(column: 5, line: 136, scope: !47)
!140 = !DILocalVariable(file: !0, line: 136, name: "result", scope: !47, type: !61)
!141 = !DILocation(column: 1, line: 136, scope: !47)
!142 = !DILocation(column: 5, line: 137, scope: !47)
!143 = !DILocalVariable(file: !0, line: 137, name: "st", scope: !47, type: !11)
!144 = !DILocation(column: 1, line: 137, scope: !47)
!145 = !DILocation(column: 5, line: 138, scope: !47)
!146 = !DILocalVariable(file: !0, line: 138, name: "en", scope: !47, type: !11)
!147 = !DILocation(column: 1, line: 138, scope: !47)
!148 = !DILocation(column: 5, line: 139, scope: !47)
!149 = !DILocation(column: 9, line: 140, scope: !47)
!150 = !DILocation(column: 5, line: 141, scope: !47)
!151 = !DILocation(column: 9, line: 142, scope: !47)
!152 = !DILocation(column: 5, line: 143, scope: !47)
!153 = !DILocation(column: 9, line: 144, scope: !47)
!154 = !DILocation(column: 9, line: 145, scope: !47)
!155 = !DILocation(column: 9, line: 146, scope: !47)
!156 = !DILocation(column: 5, line: 147, scope: !47)
!157 = !DILocation(column: 5, line: 148, scope: !47)
!158 = !DILocation(column: 5, line: 149, scope: !47)
!159 = !DILocalVariable(file: !0, line: 152, name: "s", scope: !48, type: !85)
!160 = !DILocation(column: 1, line: 152, scope: !48)
!161 = !DILocalVariable(file: !0, line: 152, name: "n", scope: !48, type: !11)
!162 = !DILocation(column: 5, line: 153, scope: !48)
!163 = !DILocalVariable(file: !0, line: 153, name: "result", scope: !48, type: !61)
!164 = !DILocation(column: 1, line: 153, scope: !48)
!165 = !DILocation(column: 5, line: 154, scope: !48)
!166 = !DILocation(column: 5, line: 155, scope: !48)
!167 = !DILocation(column: 9, line: 156, scope: !48)
!168 = !DILocation(column: 9, line: 158, scope: !48)
!169 = !DILocation(column: 5, line: 159, scope: !48)
!170 = !DILocalVariable(file: !0, line: 162, name: "s", scope: !49, type: !85)
!171 = !DILocation(column: 1, line: 162, scope: !49)
!172 = !DILocalVariable(file: !0, line: 162, name: "n", scope: !49, type: !11)
!173 = !DILocation(column: 5, line: 163, scope: !49)
!174 = !DILocalVariable(file: !0, line: 163, name: "result", scope: !49, type: !61)
!175 = !DILocation(column: 1, line: 163, scope: !49)
!176 = !DILocation(column: 5, line: 164, scope: !49)
!177 = !DILocation(column: 9, line: 165, scope: !49)
!178 = !DILocation(column: 9, line: 166, scope: !49)
!179 = !DILocation(column: 9, line: 168, scope: !49)
!180 = !DILocation(column: 9, line: 169, scope: !49)
!181 = !DILocation(column: 5, line: 170, scope: !49)
!182 = !DILocalVariable(file: !0, line: 177, name: "s", scope: !50, type: !85)
!183 = !DILocation(column: 1, line: 177, scope: !50)
!184 = !DILocalVariable(file: !0, line: 177, name: "prefix", scope: !50, type: !85)
!185 = !DILocation(column: 5, line: 178, scope: !50)
!186 = !DILocation(column: 9, line: 179, scope: !50)
!187 = !DILocation(column: 5, line: 180, scope: !50)
!188 = !DILocation(column: 13, line: 182, scope: !50)
!189 = !DILocation(column: 5, line: 183, scope: !50)
!190 = !DILocalVariable(file: !0, line: 186, name: "s", scope: !51, type: !85)
!191 = !DILocation(column: 1, line: 186, scope: !51)
!192 = !DILocalVariable(file: !0, line: 186, name: "prefix", scope: !51, type: !67)
!193 = !DILocation(column: 5, line: 187, scope: !51)
!194 = !DILocalVariable(file: !0, line: 187, name: "i", scope: !51, type: !11)
!195 = !DILocation(column: 1, line: 187, scope: !51)
!196 = !DILocation(column: 5, line: 188, scope: !51)
!197 = !DILocation(column: 9, line: 189, scope: !51)
!198 = !DILocation(column: 13, line: 190, scope: !51)
!199 = !DILocation(column: 9, line: 191, scope: !51)
!200 = !DILocation(column: 13, line: 192, scope: !51)
!201 = !DILocation(column: 9, line: 193, scope: !51)
!202 = !DILocation(column: 5, line: 194, scope: !51)
!203 = !DILocalVariable(file: !0, line: 197, name: "s", scope: !52, type: !85)
!204 = !DILocation(column: 1, line: 197, scope: !52)
!205 = !DILocalVariable(file: !0, line: 197, name: "suffix", scope: !52, type: !85)
!206 = !DILocation(column: 5, line: 198, scope: !52)
!207 = !DILocation(column: 9, line: 199, scope: !52)
!208 = !DILocation(column: 5, line: 200, scope: !52)
!209 = !DILocation(column: 5, line: 201, scope: !52)
!210 = !DILocation(column: 13, line: 203, scope: !52)
!211 = !DILocation(column: 5, line: 204, scope: !52)
!212 = !DILocalVariable(file: !0, line: 207, name: "haystack", scope: !53, type: !85)
!213 = !DILocation(column: 1, line: 207, scope: !53)
!214 = !DILocalVariable(file: !0, line: 207, name: "needle", scope: !53, type: !85)
!215 = !DILocation(column: 5, line: 208, scope: !53)
!216 = !DILocation(column: 9, line: 209, scope: !53)
!217 = !DILocation(column: 5, line: 210, scope: !53)
!218 = !DILocation(column: 9, line: 211, scope: !53)
!219 = !DILocation(column: 5, line: 213, scope: !53)
!220 = !DILocalVariable(file: !0, line: 213, name: "pos", scope: !53, type: !11)
!221 = !DILocation(column: 1, line: 213, scope: !53)
!222 = !DILocation(column: 5, line: 214, scope: !53)
!223 = !DILocation(column: 5, line: 215, scope: !53)
!224 = !DILocation(column: 9, line: 216, scope: !53)
!225 = !DILocalVariable(file: !0, line: 216, name: "found", scope: !53, type: !10)
!226 = !DILocation(column: 1, line: 216, scope: !53)
!227 = !DILocation(column: 9, line: 217, scope: !53)
!228 = !DILocalVariable(file: !0, line: 217, name: "i", scope: !53, type: !11)
!229 = !DILocation(column: 1, line: 217, scope: !53)
!230 = !DILocation(column: 9, line: 218, scope: !53)
!231 = !DILocation(column: 13, line: 219, scope: !53)
!232 = !DILocation(column: 17, line: 220, scope: !53)
!233 = !DILocation(column: 13, line: 221, scope: !53)
!234 = !DILocation(column: 9, line: 222, scope: !53)
!235 = !DILocation(column: 13, line: 223, scope: !53)
!236 = !DILocation(column: 9, line: 224, scope: !53)
!237 = !DILocation(column: 5, line: 225, scope: !53)
!238 = !DILocalVariable(file: !0, line: 228, name: "haystack", scope: !54, type: !85)
!239 = !DILocation(column: 1, line: 228, scope: !54)
!240 = !DILocalVariable(file: !0, line: 228, name: "needle", scope: !54, type: !85)
!241 = !DILocation(column: 5, line: 229, scope: !54)
!242 = !DILocation(column: 9, line: 230, scope: !54)
!243 = !DILocation(column: 5, line: 231, scope: !54)
!244 = !DILocation(column: 9, line: 232, scope: !54)
!245 = !DILocation(column: 5, line: 234, scope: !54)
!246 = !DILocalVariable(file: !0, line: 234, name: "pos", scope: !54, type: !11)
!247 = !DILocation(column: 1, line: 234, scope: !54)
!248 = !DILocation(column: 5, line: 235, scope: !54)
!249 = !DILocation(column: 5, line: 236, scope: !54)
!250 = !DILocation(column: 9, line: 237, scope: !54)
!251 = !DILocalVariable(file: !0, line: 237, name: "found", scope: !54, type: !10)
!252 = !DILocation(column: 1, line: 237, scope: !54)
!253 = !DILocation(column: 9, line: 238, scope: !54)
!254 = !DILocalVariable(file: !0, line: 238, name: "i", scope: !54, type: !11)
!255 = !DILocation(column: 1, line: 238, scope: !54)
!256 = !DILocation(column: 9, line: 239, scope: !54)
!257 = !DILocation(column: 13, line: 240, scope: !54)
!258 = !DILocation(column: 17, line: 241, scope: !54)
!259 = !DILocation(column: 13, line: 242, scope: !54)
!260 = !DILocation(column: 9, line: 243, scope: !54)
!261 = !DILocation(column: 13, line: 244, scope: !54)
!262 = !DILocation(column: 9, line: 245, scope: !54)
!263 = !DILocation(column: 5, line: 246, scope: !54)
!264 = !DILocalVariable(file: !0, line: 249, name: "s", scope: !55, type: !85)
!265 = !DILocation(column: 1, line: 249, scope: !55)
!266 = !DILocalVariable(file: !0, line: 249, name: "c", scope: !55, type: !12)
!267 = !DILocation(column: 5, line: 250, scope: !55)
!268 = !DILocation(column: 13, line: 252, scope: !55)
!269 = !DILocation(column: 5, line: 253, scope: !55)
!270 = !DILocalVariable(file: !0, line: 263, name: "s", scope: !56, type: !85)
!271 = !DILocation(column: 1, line: 263, scope: !56)
!272 = !DILocalVariable(file: !0, line: 263, name: "delim", scope: !56, type: !12)
!273 = !DILocalVariable(file: !0, line: 263, name: "before", scope: !56, type: !61)
!274 = !DILocalVariable(file: !0, line: 263, name: "after", scope: !56, type: !61)
!275 = !DILocation(column: 5, line: 264, scope: !56)
!276 = !DILocation(column: 5, line: 265, scope: !56)
!277 = !DILocation(column: 9, line: 266, scope: !56)
!278 = !DILocation(column: 9, line: 267, scope: !56)
!279 = !DILocation(column: 9, line: 268, scope: !56)
!280 = !DILocation(column: 9, line: 269, scope: !56)
!281 = !DILocation(column: 9, line: 270, scope: !56)
!282 = !DILocation(column: 5, line: 272, scope: !56)
!283 = !DILocation(column: 5, line: 273, scope: !56)
!284 = !DILocation(column: 5, line: 274, scope: !56)
!285 = !DILocation(column: 5, line: 275, scope: !56)
!286 = !DILocation(column: 5, line: 276, scope: !56)
!287 = !DILocalVariable(file: !0, line: 283, name: "s", scope: !57, type: !85)
!288 = !DILocation(column: 1, line: 283, scope: !57)
!289 = !DILocation(column: 5, line: 284, scope: !57)
!290 = !DILocalVariable(file: !0, line: 284, name: "result", scope: !57, type: !61)
!291 = !DILocation(column: 1, line: 284, scope: !57)
!292 = !DILocation(column: 5, line: 285, scope: !57)
!293 = !DILocalVariable(file: !0, line: 285, name: "start", scope: !57, type: !11)
!294 = !DILocation(column: 1, line: 285, scope: !57)
!295 = !DILocation(column: 5, line: 286, scope: !57)
!296 = !DILocation(column: 9, line: 287, scope: !57)
!297 = !DILocation(column: 9, line: 288, scope: !57)
!298 = !DILocation(column: 13, line: 289, scope: !57)
!299 = !DILocation(column: 9, line: 290, scope: !57)
!300 = !DILocation(column: 5, line: 291, scope: !57)
!301 = !DILocation(column: 5, line: 292, scope: !57)
!302 = !DILocation(column: 5, line: 293, scope: !57)
!303 = !DILocalVariable(file: !0, line: 296, name: "s", scope: !58, type: !85)
!304 = !DILocation(column: 1, line: 296, scope: !58)
!305 = !DILocation(column: 5, line: 297, scope: !58)
!306 = !DILocalVariable(file: !0, line: 297, name: "result", scope: !58, type: !61)
!307 = !DILocation(column: 1, line: 297, scope: !58)
!308 = !DILocation(column: 5, line: 298, scope: !58)
!309 = !DILocalVariable(file: !0, line: 298, name: "end", scope: !58, type: !11)
!310 = !DILocation(column: 1, line: 298, scope: !58)
!311 = !DILocation(column: 5, line: 299, scope: !58)
!312 = !DILocation(column: 9, line: 300, scope: !58)
!313 = !DILocation(column: 9, line: 301, scope: !58)
!314 = !DILocation(column: 13, line: 302, scope: !58)
!315 = !DILocation(column: 9, line: 303, scope: !58)
!316 = !DILocation(column: 5, line: 304, scope: !58)
!317 = !DILocation(column: 5, line: 305, scope: !58)
!318 = !DILocation(column: 5, line: 306, scope: !58)
!319 = !DILocalVariable(file: !0, line: 309, name: "s", scope: !59, type: !85)
!320 = !DILocation(column: 1, line: 309, scope: !59)
!321 = !DILocation(column: 5, line: 310, scope: !59)
!322 = !DILocalVariable(file: !0, line: 310, name: "trimmed", scope: !59, type: !61)
!323 = !DILocation(column: 1, line: 310, scope: !59)
!324 = !DILocation(column: 5, line: 311, scope: !59)
!325 = !DILocalVariable(file: !0, line: 318, name: "self", scope: !17, type: !85)
!326 = !DILocation(column: 1, line: 318, scope: !17)
!327 = !DILocation(column: 9, line: 319, scope: !17)
!328 = !DILocalVariable(file: !0, line: 321, name: "self", scope: !18, type: !85)
!329 = !DILocation(column: 1, line: 321, scope: !18)
!330 = !DILocation(column: 9, line: 322, scope: !18)
!331 = !DILocalVariable(file: !0, line: 324, name: "self", scope: !19, type: !85)
!332 = !DILocation(column: 1, line: 324, scope: !19)
!333 = !DILocalVariable(file: !0, line: 324, name: "idx", scope: !19, type: !11)
!334 = !DILocation(column: 9, line: 325, scope: !19)
!335 = !DILocalVariable(file: !0, line: 327, name: "self", scope: !20, type: !85)
!336 = !DILocation(column: 1, line: 327, scope: !20)
!337 = !DILocation(column: 9, line: 328, scope: !20)
!338 = !DILocalVariable(file: !0, line: 330, name: "self", scope: !21, type: !85)
!339 = !DILocation(column: 1, line: 330, scope: !21)
!340 = !DILocalVariable(file: !0, line: 330, name: "start", scope: !21, type: !11)
!341 = !DILocalVariable(file: !0, line: 330, name: "end", scope: !21, type: !11)
!342 = !DILocation(column: 9, line: 331, scope: !21)
!343 = !DILocalVariable(file: !0, line: 333, name: "self", scope: !22, type: !85)
!344 = !DILocation(column: 1, line: 333, scope: !22)
!345 = !DILocalVariable(file: !0, line: 333, name: "n", scope: !22, type: !11)
!346 = !DILocation(column: 9, line: 334, scope: !22)
!347 = !DILocalVariable(file: !0, line: 336, name: "self", scope: !23, type: !85)
!348 = !DILocation(column: 1, line: 336, scope: !23)
!349 = !DILocalVariable(file: !0, line: 336, name: "n", scope: !23, type: !11)
!350 = !DILocation(column: 9, line: 337, scope: !23)
!351 = !DILocalVariable(file: !0, line: 339, name: "self", scope: !24, type: !85)
!352 = !DILocation(column: 1, line: 339, scope: !24)
!353 = !DILocalVariable(file: !0, line: 339, name: "prefix", scope: !24, type: !85)
!354 = !DILocation(column: 9, line: 340, scope: !24)
!355 = !DILocalVariable(file: !0, line: 342, name: "self", scope: !25, type: !85)
!356 = !DILocation(column: 1, line: 342, scope: !25)
!357 = !DILocalVariable(file: !0, line: 342, name: "suffix", scope: !25, type: !85)
!358 = !DILocation(column: 9, line: 343, scope: !25)
!359 = !DILocalVariable(file: !0, line: 345, name: "self", scope: !26, type: !85)
!360 = !DILocation(column: 1, line: 345, scope: !26)
!361 = !DILocalVariable(file: !0, line: 345, name: "needle", scope: !26, type: !85)
!362 = !DILocation(column: 9, line: 346, scope: !26)
!363 = !DILocalVariable(file: !0, line: 348, name: "self", scope: !27, type: !85)
!364 = !DILocation(column: 1, line: 348, scope: !27)
!365 = !DILocalVariable(file: !0, line: 348, name: "needle", scope: !27, type: !85)
!366 = !DILocation(column: 9, line: 349, scope: !27)
!367 = !DILocalVariable(file: !0, line: 351, name: "self", scope: !28, type: !85)
!368 = !DILocation(column: 1, line: 351, scope: !28)
!369 = !DILocalVariable(file: !0, line: 351, name: "c", scope: !28, type: !12)
!370 = !DILocation(column: 9, line: 352, scope: !28)
!371 = !DILocalVariable(file: !0, line: 354, name: "self", scope: !29, type: !85)
!372 = !DILocation(column: 1, line: 354, scope: !29)
!373 = !DILocation(column: 9, line: 355, scope: !29)
!374 = !DILocalVariable(file: !0, line: 357, name: "self", scope: !30, type: !85)
!375 = !DILocation(column: 1, line: 357, scope: !30)
!376 = !DILocation(column: 9, line: 358, scope: !30)
!377 = !DILocalVariable(file: !0, line: 360, name: "self", scope: !31, type: !85)
!378 = !DILocation(column: 1, line: 360, scope: !31)
!379 = !DILocation(column: 9, line: 361, scope: !31)
!380 = !DILocalVariable(file: !0, line: 363, name: "self", scope: !32, type: !85)
!381 = !DILocation(column: 1, line: 363, scope: !32)
!382 = !DILocalVariable(file: !0, line: 363, name: "other", scope: !32, type: !85)
!383 = !DILocation(column: 9, line: 364, scope: !32)
!384 = !DILocalVariable(file: !0, line: 366, name: "self", scope: !33, type: !85)
!385 = !DILocation(column: 1, line: 366, scope: !33)
!386 = !DILocalVariable(file: !0, line: 366, name: "cstr", scope: !33, type: !67)
!387 = !DILocation(column: 9, line: 367, scope: !33)
!388 = !DILocalVariable(file: !0, line: 370, name: "self", scope: !34, type: !85)
!389 = !DILocation(column: 1, line: 370, scope: !34)
!390 = !DILocation(column: 9, line: 371, scope: !34)
!391 = !DILocalVariable(file: !0, line: 374, name: "self", scope: !35, type: !85)
!392 = !DILocation(column: 1, line: 374, scope: !35)
!393 = !DILocation(column: 9, line: 375, scope: !35)