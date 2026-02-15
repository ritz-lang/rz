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

define i32 @"is_space"(i8 %"c.arg") !dbg !17
{
entry:
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !37, metadata !7), !dbg !38
  %".5" = load i8, i8* %"c", !dbg !39
  %".6" = icmp eq i8 %".5", 32 , !dbg !39
  br i1 %".6", label %"or.merge", label %"or.right", !dbg !39
or.right:
  %".8" = load i8, i8* %"c", !dbg !39
  %".9" = icmp eq i8 %".8", 9 , !dbg !39
  br label %"or.merge", !dbg !39
or.merge:
  %".11" = phi  i1 [1, %"entry"], [%".9", %"or.right"] , !dbg !39
  %".12" = zext i1 %".11" to i32 , !dbg !39
  ret i32 %".12", !dbg !39
}

define i32 @"starts_with_keyword"(%"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"* %"keyword.arg") !dbg !18
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !42, metadata !7), !dbg !43
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"keyword.arg", metadata !44, metadata !7), !dbg !43
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !45
  %".7" = load i64, i64* %".6", !dbg !45
  %".8" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"keyword.arg", i32 0, i32 1 , !dbg !45
  %".9" = load i64, i64* %".8", !dbg !45
  %".10" = icmp slt i64 %".7", %".9" , !dbg !45
  br i1 %".10", label %"if.then", label %"if.end", !dbg !45
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !46
  ret i32 %".12", !dbg !46
if.end:
  %".14" = call i32 @"strview_starts_with"(%"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"* %"keyword.arg"), !dbg !47
  %".15" = sext i32 %".14" to i64 , !dbg !47
  %".16" = icmp eq i64 %".15", 0 , !dbg !47
  br i1 %".16", label %"if.then.1", label %"if.end.1", !dbg !47
if.then.1:
  %".18" = trunc i64 0 to i32 , !dbg !48
  ret i32 %".18", !dbg !48
if.end.1:
  %".20" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !49
  %".21" = load i64, i64* %".20", !dbg !49
  %".22" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"keyword.arg", i32 0, i32 1 , !dbg !49
  %".23" = load i64, i64* %".22", !dbg !49
  %".24" = icmp eq i64 %".21", %".23" , !dbg !49
  br i1 %".24", label %"if.then.2", label %"if.end.2", !dbg !49
if.then.2:
  %".26" = trunc i64 1 to i32 , !dbg !50
  ret i32 %".26", !dbg !50
if.end.2:
  %".28" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"keyword.arg", i32 0, i32 1 , !dbg !51
  %".29" = load i64, i64* %".28", !dbg !51
  %".30" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %".29"), !dbg !51
  %".31" = call i32 @"is_space"(i8 %".30"), !dbg !52
  ret i32 %".31", !dbg !52
}

define i64 @"find_keyword"(%"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"* %"keyword.arg") !dbg !19
{
entry:
  %"pos.addr" = alloca i64, !dbg !56
  %"sub.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !64
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !53, metadata !7), !dbg !54
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"keyword.arg", metadata !55, metadata !7), !dbg !54
  store i64 0, i64* %"pos.addr", !dbg !56
  call void @"llvm.dbg.declare"(metadata i64* %"pos.addr", metadata !57, metadata !7), !dbg !58
  br label %"while.cond", !dbg !59
while.cond:
  %".9" = load i64, i64* %"pos.addr", !dbg !59
  %".10" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !59
  %".11" = load i64, i64* %".10", !dbg !59
  %".12" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"keyword.arg", i32 0, i32 1 , !dbg !59
  %".13" = load i64, i64* %".12", !dbg !59
  %".14" = sub i64 %".11", %".13", !dbg !59
  %".15" = icmp sle i64 %".9", %".14" , !dbg !59
  br i1 %".15", label %"while.body", label %"while.end", !dbg !59
while.body:
  %".17" = load i64, i64* %"pos.addr", !dbg !60
  %".18" = icmp sgt i64 %".17", 0 , !dbg !60
  br i1 %".18", label %"if.then", label %"if.end", !dbg !60
while.end:
  %".70" = sub i64 0, 1, !dbg !73
  ret i64 %".70", !dbg !73
if.then:
  %".20" = load i64, i64* %"pos.addr", !dbg !61
  %".21" = sub i64 %".20", 1, !dbg !61
  %".22" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %".21"), !dbg !61
  %".23" = call i32 @"is_space"(i8 %".22"), !dbg !61
  %".24" = sext i32 %".23" to i64 , !dbg !61
  %".25" = icmp eq i64 %".24", 0 , !dbg !61
  br i1 %".25", label %"if.then.1", label %"if.end.1", !dbg !61
if.end:
  %".32" = load i64, i64* %"pos.addr", !dbg !64
  %".33" = load i64, i64* %"pos.addr", !dbg !64
  %".34" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"keyword.arg", i32 0, i32 1 , !dbg !64
  %".35" = load i64, i64* %".34", !dbg !64
  %".36" = add i64 %".33", %".35", !dbg !64
  %".37" = call %"struct.ritz_module_1.StrView" @"strview_slice"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %".32", i64 %".36"), !dbg !64
  store %"struct.ritz_module_1.StrView" %".37", %"struct.ritz_module_1.StrView"* %"sub.addr", !dbg !64
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"sub.addr", metadata !65, metadata !7), !dbg !66
  %".40" = call i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %"sub.addr", %"struct.ritz_module_1.StrView"* %"keyword.arg"), !dbg !67
  %".41" = sext i32 %".40" to i64 , !dbg !67
  %".42" = icmp ne i64 %".41", 0 , !dbg !67
  br i1 %".42", label %"if.then.2", label %"if.end.2", !dbg !67
if.then.1:
  %".27" = load i64, i64* %"pos.addr", !dbg !62
  %".28" = add i64 %".27", 1, !dbg !62
  store i64 %".28", i64* %"pos.addr", !dbg !62
  br label %"while.cond", !dbg !63
if.end.1:
  br label %"if.end", !dbg !63
if.then.2:
  %".44" = load i64, i64* %"pos.addr", !dbg !68
  %".45" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"keyword.arg", i32 0, i32 1 , !dbg !68
  %".46" = load i64, i64* %".45", !dbg !68
  %".47" = add i64 %".44", %".46", !dbg !68
  %".48" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.arg", i32 0, i32 1 , !dbg !68
  %".49" = load i64, i64* %".48", !dbg !68
  %".50" = icmp sge i64 %".47", %".49" , !dbg !68
  br i1 %".50", label %"if.then.3", label %"if.end.3", !dbg !68
if.end.2:
  %".66" = load i64, i64* %"pos.addr", !dbg !72
  %".67" = add i64 %".66", 1, !dbg !72
  store i64 %".67", i64* %"pos.addr", !dbg !72
  br label %"while.cond", !dbg !72
if.then.3:
  %".52" = load i64, i64* %"pos.addr", !dbg !69
  ret i64 %".52", !dbg !69
if.end.3:
  %".54" = load i64, i64* %"pos.addr", !dbg !70
  %".55" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"keyword.arg", i32 0, i32 1 , !dbg !70
  %".56" = load i64, i64* %".55", !dbg !70
  %".57" = add i64 %".54", %".56", !dbg !70
  %".58" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %".57"), !dbg !70
  %".59" = call i32 @"is_space"(i8 %".58"), !dbg !70
  %".60" = sext i32 %".59" to i64 , !dbg !70
  %".61" = icmp ne i64 %".60", 0 , !dbg !70
  br i1 %".61", label %"if.then.4", label %"if.end.4", !dbg !70
if.then.4:
  %".63" = load i64, i64* %"pos.addr", !dbg !71
  ret i64 %".63", !dbg !71
if.end.4:
  br label %"if.end.2", !dbg !71
}

define i64 @"find_and"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !20
{
entry:
  %"kw.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !76
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !74, metadata !7), !dbg !75
  %".4" = getelementptr [4 x i8], [4 x i8]* @".str.0", i64 0, i64 0 , !dbg !76
  %".5" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".4"), !dbg !76
  store %"struct.ritz_module_1.StrView" %".5", %"struct.ritz_module_1.StrView"* %"kw.addr", !dbg !76
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"kw.addr", metadata !77, metadata !7), !dbg !78
  %".8" = call i64 @"find_keyword"(%"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"* %"kw.addr"), !dbg !79
  ret i64 %".8", !dbg !79
}

define i64 @"find_or"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !21
{
entry:
  %"kw.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !82
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !80, metadata !7), !dbg !81
  %".4" = getelementptr [3 x i8], [3 x i8]* @".str.1", i64 0, i64 0 , !dbg !82
  %".5" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".4"), !dbg !82
  store %"struct.ritz_module_1.StrView" %".5", %"struct.ritz_module_1.StrView"* %"kw.addr", !dbg !82
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"kw.addr", metadata !83, metadata !7), !dbg !84
  %".8" = call i64 @"find_keyword"(%"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"* %"kw.addr"), !dbg !85
  ret i64 %".8", !dbg !85
}

define i32 @"starts_with_not"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !22
{
entry:
  %"trimmed.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !88
  %"kw.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !91
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.arg", metadata !86, metadata !7), !dbg !87
  %".4" = call %"struct.ritz_module_1.StrView" @"strview_trim_start"(%"struct.ritz_module_1.StrView"* %"s.arg"), !dbg !88
  store %"struct.ritz_module_1.StrView" %".4", %"struct.ritz_module_1.StrView"* %"trimmed.addr", !dbg !88
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"trimmed.addr", metadata !89, metadata !7), !dbg !90
  %".7" = getelementptr [4 x i8], [4 x i8]* @".str.2", i64 0, i64 0 , !dbg !91
  %".8" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".7"), !dbg !91
  store %"struct.ritz_module_1.StrView" %".8", %"struct.ritz_module_1.StrView"* %"kw.addr", !dbg !91
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"kw.addr", metadata !92, metadata !7), !dbg !93
  %".11" = call i32 @"starts_with_keyword"(%"struct.ritz_module_1.StrView"* %"trimmed.addr", %"struct.ritz_module_1.StrView"* %"kw.addr"), !dbg !94
  ret i32 %".11", !dbg !94
}

define i32 @"has_bool_operators"(%"struct.ritz_module_1.StrView"* %"pattern.arg") !dbg !23
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"pattern.arg", metadata !95, metadata !7), !dbg !96
  %".4" = call i64 @"find_and"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !97
  %".5" = icmp sge i64 %".4", 0 , !dbg !97
  br i1 %".5", label %"if.then", label %"if.end", !dbg !97
if.then:
  %".7" = trunc i64 1 to i32 , !dbg !98
  ret i32 %".7", !dbg !98
if.end:
  %".9" = call i64 @"find_or"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !99
  %".10" = icmp sge i64 %".9", 0 , !dbg !99
  br i1 %".10", label %"if.then.1", label %"if.end.1", !dbg !99
if.then.1:
  %".12" = trunc i64 1 to i32 , !dbg !100
  ret i32 %".12", !dbg !100
if.end.1:
  %".14" = call i32 @"starts_with_not"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !101
  %".15" = sext i32 %".14" to i64 , !dbg !101
  %".16" = icmp ne i64 %".15", 0 , !dbg !101
  br i1 %".16", label %"if.then.2", label %"if.end.2", !dbg !101
if.then.2:
  %".18" = trunc i64 1 to i32 , !dbg !102
  ret i32 %".18", !dbg !102
if.end.2:
  %".20" = trunc i64 0 to i32 , !dbg !103
  ret i32 %".20", !dbg !103
}

define i32 @"has_glob_chars"(%"struct.ritz_module_1.StrView"* %"pattern.arg") !dbg !24
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"pattern.arg", metadata !104, metadata !7), !dbg !105
  %".4" = call i64 @"strview_find_byte"(%"struct.ritz_module_1.StrView"* %"pattern.arg", i8 42), !dbg !106
  %".5" = icmp sge i64 %".4", 0 , !dbg !106
  br i1 %".5", label %"if.then", label %"if.end", !dbg !106
if.then:
  %".7" = trunc i64 1 to i32 , !dbg !107
  ret i32 %".7", !dbg !107
if.end:
  %".9" = call i64 @"strview_find_byte"(%"struct.ritz_module_1.StrView"* %"pattern.arg", i8 63), !dbg !108
  %".10" = icmp sge i64 %".9", 0 , !dbg !108
  br i1 %".10", label %"if.then.1", label %"if.end.1", !dbg !108
if.then.1:
  %".12" = trunc i64 1 to i32 , !dbg !109
  ret i32 %".12", !dbg !109
if.end.1:
  %".14" = trunc i64 0 to i32 , !dbg !110
  ret i32 %".14", !dbg !110
}

define i32 @"has_suite_separator"(%"struct.ritz_module_1.StrView"* %"pattern.arg") !dbg !25
{
entry:
  %"pos.addr" = alloca i64, !dbg !113
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"pattern.arg", metadata !111, metadata !7), !dbg !112
  store i64 0, i64* %"pos.addr", !dbg !113
  call void @"llvm.dbg.declare"(metadata i64* %"pos.addr", metadata !114, metadata !7), !dbg !115
  br label %"while.cond", !dbg !116
while.cond:
  %".7" = load i64, i64* %"pos.addr", !dbg !116
  %".8" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"pattern.arg", i32 0, i32 1 , !dbg !116
  %".9" = load i64, i64* %".8", !dbg !116
  %".10" = sub i64 %".9", 1, !dbg !116
  %".11" = icmp slt i64 %".7", %".10" , !dbg !116
  br i1 %".11", label %"while.body", label %"while.end", !dbg !116
while.body:
  %".13" = load i64, i64* %"pos.addr", !dbg !117
  %".14" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"pattern.arg", i64 %".13"), !dbg !117
  %".15" = icmp eq i8 %".14", 58 , !dbg !117
  br i1 %".15", label %"and.right", label %"and.merge", !dbg !117
while.end:
  %".30" = trunc i64 0 to i32 , !dbg !120
  ret i32 %".30", !dbg !120
and.right:
  %".17" = load i64, i64* %"pos.addr", !dbg !117
  %".18" = add i64 %".17", 1, !dbg !117
  %".19" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"pattern.arg", i64 %".18"), !dbg !117
  %".20" = icmp eq i8 %".19", 58 , !dbg !117
  br label %"and.merge", !dbg !117
and.merge:
  %".22" = phi  i1 [0, %"while.body"], [%".20", %"and.right"] , !dbg !117
  br i1 %".22", label %"if.then", label %"if.end", !dbg !117
if.then:
  %".24" = trunc i64 1 to i32 , !dbg !118
  ret i32 %".24", !dbg !118
if.end:
  %".26" = load i64, i64* %"pos.addr", !dbg !119
  %".27" = add i64 %".26", 1, !dbg !119
  store i64 %".27", i64* %"pos.addr", !dbg !119
  br label %"while.cond", !dbg !119
}

define i32 @"is_attribute"(%"struct.ritz_module_1.StrView"* %"pattern.arg") !dbg !26
{
entry:
  %"trimmed.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !123
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"pattern.arg", metadata !121, metadata !7), !dbg !122
  %".4" = call %"struct.ritz_module_1.StrView" @"strview_trim_start"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !123
  store %"struct.ritz_module_1.StrView" %".4", %"struct.ritz_module_1.StrView"* %"trimmed.addr", !dbg !123
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"trimmed.addr", metadata !124, metadata !7), !dbg !125
  %".7" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"trimmed.addr", i32 0, i32 1 , !dbg !126
  %".8" = load i64, i64* %".7", !dbg !126
  %".9" = icmp eq i64 %".8", 0 , !dbg !126
  br i1 %".9", label %"if.then", label %"if.end", !dbg !126
if.then:
  %".11" = trunc i64 0 to i32 , !dbg !127
  ret i32 %".11", !dbg !127
if.end:
  %".13" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"trimmed.addr", i64 0), !dbg !128
  %".14" = icmp eq i8 %".13", 64 , !dbg !128
  %".15" = zext i1 %".14" to i32 , !dbg !128
  ret i32 %".15", !dbg !128
}

define i32 @"contains_substring"(%"struct.ritz_module_1.StrView"* %"haystack.arg", %"struct.ritz_module_1.StrView"* %"needle.arg") !dbg !27
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"haystack.arg", metadata !129, metadata !7), !dbg !130
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"needle.arg", metadata !131, metadata !7), !dbg !130
  %".6" = call i64 @"strview_find"(%"struct.ritz_module_1.StrView"* %"haystack.arg", %"struct.ritz_module_1.StrView"* %"needle.arg"), !dbg !132
  %".7" = icmp sge i64 %".6", 0 , !dbg !132
  %".8" = zext i1 %".7" to i32 , !dbg !132
  ret i32 %".8", !dbg !132
}

define i32 @"match_attribute"(%"struct.ritz_module_1.StrView"* %"attr.arg", %"struct.ritz_module_1.StrView"* %"test_name.arg") !dbg !28
{
entry:
  %"trimmed.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !136
  %"needle.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !142
  %"needle.addr.1" = alloca %"struct.ritz_module_1.StrView", !dbg !147
  %"needle.addr.2" = alloca %"struct.ritz_module_1.StrView", !dbg !152
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"attr.arg", metadata !133, metadata !7), !dbg !134
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"test_name.arg", metadata !135, metadata !7), !dbg !134
  %".6" = call %"struct.ritz_module_1.StrView" @"strview_trim_start"(%"struct.ritz_module_1.StrView"* %"attr.arg"), !dbg !136
  store %"struct.ritz_module_1.StrView" %".6", %"struct.ritz_module_1.StrView"* %"trimmed.addr", !dbg !136
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"trimmed.addr", metadata !137, metadata !7), !dbg !138
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"trimmed.addr", i32 0, i32 1 , !dbg !139
  %".10" = load i64, i64* %".9", !dbg !139
  %".11" = icmp sgt i64 %".10", 0 , !dbg !139
  br i1 %".11", label %"and.right", label %"and.merge", !dbg !139
and.right:
  %".13" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"trimmed.addr", i64 0), !dbg !139
  %".14" = icmp eq i8 %".13", 64 , !dbg !139
  br label %"and.merge", !dbg !139
and.merge:
  %".16" = phi  i1 [0, %"entry"], [%".14", %"and.right"] , !dbg !139
  br i1 %".16", label %"if.then", label %"if.end", !dbg !139
if.then:
  %".18" = call %"struct.ritz_module_1.StrView" @"strview_skip"(%"struct.ritz_module_1.StrView"* %"trimmed.addr", i64 1), !dbg !140
  store %"struct.ritz_module_1.StrView" %".18", %"struct.ritz_module_1.StrView"* %"trimmed.addr", !dbg !140
  br label %"if.end", !dbg !140
if.end:
  %".21" = getelementptr [7 x i8], [7 x i8]* @".str.3", i64 0, i64 0 , !dbg !141
  %".22" = call i32 @"strview_starts_with_cstr"(%"struct.ritz_module_1.StrView"* %"trimmed.addr", i8* %".21"), !dbg !141
  %".23" = sext i32 %".22" to i64 , !dbg !141
  %".24" = icmp ne i64 %".23", 0 , !dbg !141
  br i1 %".24", label %"or.merge", label %"or.right", !dbg !141
or.right:
  %".26" = getelementptr [5 x i8], [5 x i8]* @".str.4", i64 0, i64 0 , !dbg !141
  %".27" = call i32 @"strview_starts_with_cstr"(%"struct.ritz_module_1.StrView"* %"trimmed.addr", i8* %".26"), !dbg !141
  %".28" = sext i32 %".27" to i64 , !dbg !141
  %".29" = icmp ne i64 %".28", 0 , !dbg !141
  br label %"or.merge", !dbg !141
or.merge:
  %".31" = phi  i1 [1, %"if.end"], [%".29", %"or.right"] , !dbg !141
  br i1 %".31", label %"if.then.1", label %"if.end.1", !dbg !141
if.then.1:
  %".33" = getelementptr [7 x i8], [7 x i8]* @".str.5", i64 0, i64 0 , !dbg !142
  %".34" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".33"), !dbg !142
  store %"struct.ritz_module_1.StrView" %".34", %"struct.ritz_module_1.StrView"* %"needle.addr", !dbg !142
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"needle.addr", metadata !143, metadata !7), !dbg !144
  %".37" = call i32 @"contains_substring"(%"struct.ritz_module_1.StrView"* %"test_name.arg", %"struct.ritz_module_1.StrView"* %"needle.addr"), !dbg !145
  ret i32 %".37", !dbg !145
if.end.1:
  %".39" = getelementptr [5 x i8], [5 x i8]* @".str.6", i64 0, i64 0 , !dbg !146
  %".40" = call i32 @"strview_starts_with_cstr"(%"struct.ritz_module_1.StrView"* %"trimmed.addr", i8* %".39"), !dbg !146
  %".41" = sext i32 %".40" to i64 , !dbg !146
  %".42" = icmp ne i64 %".41", 0 , !dbg !146
  br i1 %".42", label %"if.then.2", label %"if.end.2", !dbg !146
if.then.2:
  %".44" = getelementptr [5 x i8], [5 x i8]* @".str.7", i64 0, i64 0 , !dbg !147
  %".45" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".44"), !dbg !147
  store %"struct.ritz_module_1.StrView" %".45", %"struct.ritz_module_1.StrView"* %"needle.addr.1", !dbg !147
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"needle.addr.1", metadata !148, metadata !7), !dbg !149
  %".48" = call i32 @"contains_substring"(%"struct.ritz_module_1.StrView"* %"test_name.arg", %"struct.ritz_module_1.StrView"* %"needle.addr.1"), !dbg !150
  ret i32 %".48", !dbg !150
if.end.2:
  %".50" = getelementptr [5 x i8], [5 x i8]* @".str.8", i64 0, i64 0 , !dbg !151
  %".51" = call i32 @"strview_starts_with_cstr"(%"struct.ritz_module_1.StrView"* %"trimmed.addr", i8* %".50"), !dbg !151
  %".52" = sext i32 %".51" to i64 , !dbg !151
  %".53" = icmp ne i64 %".52", 0 , !dbg !151
  br i1 %".53", label %"if.then.3", label %"if.end.3", !dbg !151
if.then.3:
  %".55" = getelementptr [5 x i8], [5 x i8]* @".str.9", i64 0, i64 0 , !dbg !152
  %".56" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".55"), !dbg !152
  store %"struct.ritz_module_1.StrView" %".56", %"struct.ritz_module_1.StrView"* %"needle.addr.2", !dbg !152
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"needle.addr.2", metadata !153, metadata !7), !dbg !154
  %".59" = call i32 @"contains_substring"(%"struct.ritz_module_1.StrView"* %"test_name.arg", %"struct.ritz_module_1.StrView"* %"needle.addr.2"), !dbg !155
  %".60" = sext i32 %".59" to i64 , !dbg !155
  %".61" = icmp eq i64 %".60", 0 , !dbg !155
  %".62" = zext i1 %".61" to i32 , !dbg !155
  ret i32 %".62", !dbg !155
if.end.3:
  %".64" = trunc i64 0 to i32 , !dbg !156
  ret i32 %".64", !dbg !156
}

define i32 @"glob_match"(%"struct.ritz_module_1.StrView"* %"pattern.arg", %"struct.ritz_module_1.StrView"* %"text.arg") !dbg !29
{
entry:
  %"p.addr" = alloca i64, !dbg !160
  %"t.addr" = alloca i64, !dbg !163
  %"star_p.addr" = alloca i64, !dbg !166
  %"star_t.addr" = alloca i64, !dbg !169
  %"pc.addr" = alloca i8, !dbg !173
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"pattern.arg", metadata !157, metadata !7), !dbg !158
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"text.arg", metadata !159, metadata !7), !dbg !158
  store i64 0, i64* %"p.addr", !dbg !160
  call void @"llvm.dbg.declare"(metadata i64* %"p.addr", metadata !161, metadata !7), !dbg !162
  store i64 0, i64* %"t.addr", !dbg !163
  call void @"llvm.dbg.declare"(metadata i64* %"t.addr", metadata !164, metadata !7), !dbg !165
  %".10" = sub i64 0, 1, !dbg !166
  store i64 %".10", i64* %"star_p.addr", !dbg !166
  call void @"llvm.dbg.declare"(metadata i64* %"star_p.addr", metadata !167, metadata !7), !dbg !168
  %".13" = sub i64 0, 1, !dbg !169
  store i64 %".13", i64* %"star_t.addr", !dbg !169
  call void @"llvm.dbg.declare"(metadata i64* %"star_t.addr", metadata !170, metadata !7), !dbg !171
  br label %"while.cond", !dbg !172
while.cond:
  %".17" = load i64, i64* %"t.addr", !dbg !172
  %".18" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"text.arg", i32 0, i32 1 , !dbg !172
  %".19" = load i64, i64* %".18", !dbg !172
  %".20" = icmp slt i64 %".17", %".19" , !dbg !172
  br i1 %".20", label %"while.body", label %"while.end", !dbg !172
while.body:
  %".22" = trunc i64 0 to i8 , !dbg !173
  store i8 %".22", i8* %"pc.addr", !dbg !173
  call void @"llvm.dbg.declare"(metadata i8* %"pc.addr", metadata !174, metadata !7), !dbg !175
  %".25" = load i64, i64* %"p.addr", !dbg !176
  %".26" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"pattern.arg", i32 0, i32 1 , !dbg !176
  %".27" = load i64, i64* %".26", !dbg !176
  %".28" = icmp slt i64 %".25", %".27" , !dbg !176
  br i1 %".28", label %"if.then", label %"if.end", !dbg !176
while.end:
  br label %"while.cond.1", !dbg !188
if.then:
  %".30" = load i64, i64* %"p.addr", !dbg !177
  %".31" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"pattern.arg", i64 %".30"), !dbg !177
  store i8 %".31", i8* %"pc.addr", !dbg !177
  br label %"if.end", !dbg !177
if.end:
  %".34" = load i64, i64* %"t.addr", !dbg !178
  %".35" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"text.arg", i64 %".34"), !dbg !178
  %".36" = load i8, i8* %"pc.addr", !dbg !178
  %".37" = icmp eq i8 %".36", 42 , !dbg !178
  br i1 %".37", label %"if.then.1", label %"if.else", !dbg !178
if.then.1:
  %".39" = load i64, i64* %"p.addr", !dbg !179
  store i64 %".39", i64* %"star_p.addr", !dbg !179
  %".41" = load i64, i64* %"t.addr", !dbg !180
  store i64 %".41", i64* %"star_t.addr", !dbg !180
  %".43" = load i64, i64* %"p.addr", !dbg !181
  %".44" = add i64 %".43", 1, !dbg !181
  store i64 %".44", i64* %"p.addr", !dbg !181
  br label %"if.end.1", !dbg !187
if.else:
  %".46" = load i8, i8* %"pc.addr", !dbg !181
  %".47" = icmp eq i8 %".46", 63 , !dbg !181
  br i1 %".47", label %"or.merge", label %"or.right", !dbg !181
if.end.1:
  br label %"while.cond", !dbg !187
or.right:
  %".49" = load i8, i8* %"pc.addr", !dbg !181
  %".50" = icmp eq i8 %".49", %".35" , !dbg !181
  br label %"or.merge", !dbg !181
or.merge:
  %".52" = phi  i1 [1, %"if.else"], [%".50", %"or.right"] , !dbg !181
  br i1 %".52", label %"if.then.2", label %"if.else.1", !dbg !181
if.then.2:
  %".54" = load i64, i64* %"p.addr", !dbg !182
  %".55" = add i64 %".54", 1, !dbg !182
  store i64 %".55", i64* %"p.addr", !dbg !182
  %".57" = load i64, i64* %"t.addr", !dbg !183
  %".58" = add i64 %".57", 1, !dbg !183
  store i64 %".58", i64* %"t.addr", !dbg !183
  br label %"if.end.2", !dbg !187
if.else.1:
  %".60" = load i64, i64* %"star_p.addr", !dbg !183
  %".61" = icmp sge i64 %".60", 0 , !dbg !183
  br i1 %".61", label %"if.then.3", label %"if.else.2", !dbg !183
if.end.2:
  br label %"if.end.1", !dbg !187
if.then.3:
  %".63" = load i64, i64* %"star_p.addr", !dbg !184
  %".64" = add i64 %".63", 1, !dbg !184
  store i64 %".64", i64* %"p.addr", !dbg !184
  %".66" = load i64, i64* %"star_t.addr", !dbg !185
  %".67" = add i64 %".66", 1, !dbg !185
  store i64 %".67", i64* %"star_t.addr", !dbg !185
  %".69" = load i64, i64* %"star_t.addr", !dbg !186
  store i64 %".69", i64* %"t.addr", !dbg !186
  br label %"if.end.3", !dbg !187
if.else.2:
  %".71" = trunc i64 0 to i32 , !dbg !187
  ret i32 %".71", !dbg !187
if.end.3:
  br label %"if.end.2", !dbg !187
while.cond.1:
  %".80" = load i64, i64* %"p.addr", !dbg !188
  %".81" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"pattern.arg", i32 0, i32 1 , !dbg !188
  %".82" = load i64, i64* %".81", !dbg !188
  %".83" = icmp slt i64 %".80", %".82" , !dbg !188
  br i1 %".83", label %"and.right", label %"and.merge", !dbg !188
while.body.1:
  %".91" = load i64, i64* %"p.addr", !dbg !189
  %".92" = add i64 %".91", 1, !dbg !189
  store i64 %".92", i64* %"p.addr", !dbg !189
  br label %"while.cond.1", !dbg !189
while.end.1:
  %".95" = load i64, i64* %"p.addr", !dbg !190
  %".96" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"pattern.arg", i32 0, i32 1 , !dbg !190
  %".97" = load i64, i64* %".96", !dbg !190
  %".98" = icmp sge i64 %".95", %".97" , !dbg !190
  %".99" = zext i1 %".98" to i32 , !dbg !190
  ret i32 %".99", !dbg !190
and.right:
  %".85" = load i64, i64* %"p.addr", !dbg !188
  %".86" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"pattern.arg", i64 %".85"), !dbg !188
  %".87" = icmp eq i8 %".86", 42 , !dbg !188
  br label %"and.merge", !dbg !188
and.merge:
  %".89" = phi  i1 [0, %"while.cond.1"], [%".87", %"and.right"] , !dbg !188
  br i1 %".89", label %"while.body.1", label %"while.end.1", !dbg !188
}

define i32 @"match_suite_pattern"(%"struct.ritz_module_1.StrView"* %"pattern.arg", %"struct.ritz_module_1.StrView"* %"test_name.arg") !dbg !30
{
entry:
  %"sep_pos.addr" = alloca i64, !dbg !194
  %"i.addr" = alloca i64, !dbg !197
  %"test_pattern.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !207
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"pattern.arg", metadata !191, metadata !7), !dbg !192
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"test_name.arg", metadata !193, metadata !7), !dbg !192
  %".6" = sub i64 0, 1, !dbg !194
  store i64 %".6", i64* %"sep_pos.addr", !dbg !194
  call void @"llvm.dbg.declare"(metadata i64* %"sep_pos.addr", metadata !195, metadata !7), !dbg !196
  store i64 0, i64* %"i.addr", !dbg !197
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !198, metadata !7), !dbg !199
  br label %"while.cond", !dbg !200
while.cond:
  %".12" = load i64, i64* %"i.addr", !dbg !200
  %".13" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"pattern.arg", i32 0, i32 1 , !dbg !200
  %".14" = load i64, i64* %".13", !dbg !200
  %".15" = sub i64 %".14", 1, !dbg !200
  %".16" = icmp slt i64 %".12", %".15" , !dbg !200
  br i1 %".16", label %"while.body", label %"while.end", !dbg !200
while.body:
  %".18" = load i64, i64* %"i.addr", !dbg !201
  %".19" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"pattern.arg", i64 %".18"), !dbg !201
  %".20" = icmp eq i8 %".19", 58 , !dbg !201
  br i1 %".20", label %"and.right", label %"and.merge", !dbg !201
while.end:
  %".36" = load i64, i64* %"sep_pos.addr", !dbg !205
  %".37" = icmp slt i64 %".36", 0 , !dbg !205
  br i1 %".37", label %"if.then.1", label %"if.end.1", !dbg !205
and.right:
  %".22" = load i64, i64* %"i.addr", !dbg !201
  %".23" = add i64 %".22", 1, !dbg !201
  %".24" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"pattern.arg", i64 %".23"), !dbg !201
  %".25" = icmp eq i8 %".24", 58 , !dbg !201
  br label %"and.merge", !dbg !201
and.merge:
  %".27" = phi  i1 [0, %"while.body"], [%".25", %"and.right"] , !dbg !201
  br i1 %".27", label %"if.then", label %"if.end", !dbg !201
if.then:
  %".29" = load i64, i64* %"i.addr", !dbg !202
  store i64 %".29", i64* %"sep_pos.addr", !dbg !202
  br label %"while.end", !dbg !203
if.end:
  %".32" = load i64, i64* %"i.addr", !dbg !204
  %".33" = add i64 %".32", 1, !dbg !204
  store i64 %".33", i64* %"i.addr", !dbg !204
  br label %"while.cond", !dbg !204
if.then.1:
  %".39" = call i32 @"contains_substring"(%"struct.ritz_module_1.StrView"* %"test_name.arg", %"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !206
  ret i32 %".39", !dbg !206
if.end.1:
  %".41" = load i64, i64* %"sep_pos.addr", !dbg !207
  %".42" = add i64 %".41", 2, !dbg !207
  %".43" = call %"struct.ritz_module_1.StrView" @"strview_skip"(%"struct.ritz_module_1.StrView"* %"pattern.arg", i64 %".42"), !dbg !207
  store %"struct.ritz_module_1.StrView" %".43", %"struct.ritz_module_1.StrView"* %"test_pattern.addr", !dbg !207
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"test_pattern.addr", metadata !208, metadata !7), !dbg !209
  %".46" = call i32 @"has_glob_chars"(%"struct.ritz_module_1.StrView"* %"test_pattern.addr"), !dbg !210
  %".47" = sext i32 %".46" to i64 , !dbg !210
  %".48" = icmp ne i64 %".47", 0 , !dbg !210
  br i1 %".48", label %"if.then.2", label %"if.end.2", !dbg !210
if.then.2:
  %".50" = call i32 @"glob_match"(%"struct.ritz_module_1.StrView"* %"test_pattern.addr", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !211
  ret i32 %".50", !dbg !211
if.end.2:
  %".52" = call i32 @"contains_substring"(%"struct.ritz_module_1.StrView"* %"test_name.arg", %"struct.ritz_module_1.StrView"* %"test_pattern.addr"), !dbg !212
  ret i32 %".52", !dbg !212
}

define i32 @"match_simple_pattern"(%"struct.ritz_module_1.StrView"* %"pattern.arg", %"struct.ritz_module_1.StrView"* %"test_name.arg") !dbg !31
{
entry:
  %"trimmed.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !216
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"pattern.arg", metadata !213, metadata !7), !dbg !214
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"test_name.arg", metadata !215, metadata !7), !dbg !214
  %".6" = call %"struct.ritz_module_1.StrView" @"strview_trim"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !216
  store %"struct.ritz_module_1.StrView" %".6", %"struct.ritz_module_1.StrView"* %"trimmed.addr", !dbg !216
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"trimmed.addr", metadata !217, metadata !7), !dbg !218
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"trimmed.addr", i32 0, i32 1 , !dbg !219
  %".10" = load i64, i64* %".9", !dbg !219
  %".11" = icmp eq i64 %".10", 0 , !dbg !219
  br i1 %".11", label %"if.then", label %"if.end", !dbg !219
if.then:
  %".13" = trunc i64 1 to i32 , !dbg !220
  ret i32 %".13", !dbg !220
if.end:
  %".15" = call i32 @"is_attribute"(%"struct.ritz_module_1.StrView"* %"trimmed.addr"), !dbg !221
  %".16" = sext i32 %".15" to i64 , !dbg !221
  %".17" = icmp ne i64 %".16", 0 , !dbg !221
  br i1 %".17", label %"if.then.1", label %"if.end.1", !dbg !221
if.then.1:
  %".19" = call i32 @"match_attribute"(%"struct.ritz_module_1.StrView"* %"trimmed.addr", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !222
  ret i32 %".19", !dbg !222
if.end.1:
  %".21" = call i32 @"has_glob_chars"(%"struct.ritz_module_1.StrView"* %"trimmed.addr"), !dbg !223
  %".22" = sext i32 %".21" to i64 , !dbg !223
  %".23" = icmp ne i64 %".22", 0 , !dbg !223
  br i1 %".23", label %"if.then.2", label %"if.end.2", !dbg !223
if.then.2:
  %".25" = call i32 @"glob_match"(%"struct.ritz_module_1.StrView"* %"trimmed.addr", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !224
  ret i32 %".25", !dbg !224
if.end.2:
  %".27" = call i32 @"has_suite_separator"(%"struct.ritz_module_1.StrView"* %"trimmed.addr"), !dbg !225
  %".28" = sext i32 %".27" to i64 , !dbg !225
  %".29" = icmp ne i64 %".28", 0 , !dbg !225
  br i1 %".29", label %"if.then.3", label %"if.end.3", !dbg !225
if.then.3:
  %".31" = call i32 @"match_suite_pattern"(%"struct.ritz_module_1.StrView"* %"trimmed.addr", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !226
  ret i32 %".31", !dbg !226
if.end.3:
  %".33" = call i32 @"contains_substring"(%"struct.ritz_module_1.StrView"* %"test_name.arg", %"struct.ritz_module_1.StrView"* %"trimmed.addr"), !dbg !227
  ret i32 %".33", !dbg !227
}

define i32 @"match_bool_expr"(%"struct.ritz_module_1.StrView"* %"pattern.arg", %"struct.ritz_module_1.StrView"* %"test_name.arg") !dbg !32
{
entry:
  %"left.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !235
  %"right.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !238
  %"left.addr.1" = alloca %"struct.ritz_module_1.StrView", !dbg !246
  %"right.addr.1" = alloca %"struct.ritz_module_1.StrView", !dbg !249
  %"trimmed.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !256
  %"rest.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !259
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"pattern.arg", metadata !228, metadata !7), !dbg !229
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"test_name.arg", metadata !230, metadata !7), !dbg !229
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"pattern.arg", i32 0, i32 1 , !dbg !231
  %".7" = load i64, i64* %".6", !dbg !231
  %".8" = icmp eq i64 %".7", 0 , !dbg !231
  br i1 %".8", label %"if.then", label %"if.end", !dbg !231
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !232
  ret i32 %".10", !dbg !232
if.end:
  %".12" = call i64 @"find_or"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !233
  %".13" = icmp sge i64 %".12", 0 , !dbg !234
  br i1 %".13", label %"if.then.1", label %"if.end.1", !dbg !234
if.then.1:
  %".15" = call %"struct.ritz_module_1.StrView" @"strview_slice"(%"struct.ritz_module_1.StrView"* %"pattern.arg", i64 0, i64 %".12"), !dbg !235
  store %"struct.ritz_module_1.StrView" %".15", %"struct.ritz_module_1.StrView"* %"left.addr", !dbg !235
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"left.addr", metadata !236, metadata !7), !dbg !237
  %".18" = add i64 %".12", 2, !dbg !238
  %".19" = call %"struct.ritz_module_1.StrView" @"strview_skip"(%"struct.ritz_module_1.StrView"* %"pattern.arg", i64 %".18"), !dbg !238
  store %"struct.ritz_module_1.StrView" %".19", %"struct.ritz_module_1.StrView"* %"right.addr", !dbg !238
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"right.addr", metadata !239, metadata !7), !dbg !240
  %".22" = call i32 @"match_bool_expr"(%"struct.ritz_module_1.StrView"* %"left.addr", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !241
  %".23" = sext i32 %".22" to i64 , !dbg !241
  %".24" = icmp ne i64 %".23", 0 , !dbg !241
  br i1 %".24", label %"if.then.2", label %"if.end.2", !dbg !241
if.end.1:
  %".30" = call i64 @"find_and"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !244
  %".31" = icmp sge i64 %".30", 0 , !dbg !245
  br i1 %".31", label %"if.then.3", label %"if.end.3", !dbg !245
if.then.2:
  %".26" = trunc i64 1 to i32 , !dbg !242
  ret i32 %".26", !dbg !242
if.end.2:
  %".28" = call i32 @"match_bool_expr"(%"struct.ritz_module_1.StrView"* %"right.addr", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !243
  ret i32 %".28", !dbg !243
if.then.3:
  %".33" = call %"struct.ritz_module_1.StrView" @"strview_slice"(%"struct.ritz_module_1.StrView"* %"pattern.arg", i64 0, i64 %".30"), !dbg !246
  store %"struct.ritz_module_1.StrView" %".33", %"struct.ritz_module_1.StrView"* %"left.addr.1", !dbg !246
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"left.addr.1", metadata !247, metadata !7), !dbg !248
  %".36" = add i64 %".30", 3, !dbg !249
  %".37" = call %"struct.ritz_module_1.StrView" @"strview_skip"(%"struct.ritz_module_1.StrView"* %"pattern.arg", i64 %".36"), !dbg !249
  store %"struct.ritz_module_1.StrView" %".37", %"struct.ritz_module_1.StrView"* %"right.addr.1", !dbg !249
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"right.addr.1", metadata !250, metadata !7), !dbg !251
  %".40" = call i32 @"match_bool_expr"(%"struct.ritz_module_1.StrView"* %"left.addr.1", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !252
  %".41" = sext i32 %".40" to i64 , !dbg !252
  %".42" = icmp eq i64 %".41", 0 , !dbg !252
  br i1 %".42", label %"if.then.4", label %"if.end.4", !dbg !252
if.end.3:
  %".48" = call i32 @"starts_with_not"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !255
  %".49" = sext i32 %".48" to i64 , !dbg !255
  %".50" = icmp ne i64 %".49", 0 , !dbg !255
  br i1 %".50", label %"if.then.5", label %"if.end.5", !dbg !255
if.then.4:
  %".44" = trunc i64 0 to i32 , !dbg !253
  ret i32 %".44", !dbg !253
if.end.4:
  %".46" = call i32 @"match_bool_expr"(%"struct.ritz_module_1.StrView"* %"right.addr.1", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !254
  ret i32 %".46", !dbg !254
if.then.5:
  %".52" = call %"struct.ritz_module_1.StrView" @"strview_trim_start"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !256
  store %"struct.ritz_module_1.StrView" %".52", %"struct.ritz_module_1.StrView"* %"trimmed.addr", !dbg !256
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"trimmed.addr", metadata !257, metadata !7), !dbg !258
  %".55" = call %"struct.ritz_module_1.StrView" @"strview_skip"(%"struct.ritz_module_1.StrView"* %"trimmed.addr", i64 3), !dbg !259
  store %"struct.ritz_module_1.StrView" %".55", %"struct.ritz_module_1.StrView"* %"rest.addr", !dbg !259
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"rest.addr", metadata !260, metadata !7), !dbg !261
  %".58" = call i32 @"match_bool_expr"(%"struct.ritz_module_1.StrView"* %"rest.addr", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !262
  %".59" = sext i32 %".58" to i64 , !dbg !262
  %".60" = icmp eq i64 %".59", 0 , !dbg !262
  %".61" = zext i1 %".60" to i32 , !dbg !262
  ret i32 %".61", !dbg !262
if.end.5:
  %".63" = call i32 @"match_simple_pattern"(%"struct.ritz_module_1.StrView"* %"pattern.arg", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !263
  ret i32 %".63", !dbg !263
}

define i32 @"filter_type_sv"(%"struct.ritz_module_1.StrView"* %"pattern.arg") !dbg !33
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"pattern.arg", metadata !264, metadata !7), !dbg !265
  %".4" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"pattern.arg", i32 0, i32 1 , !dbg !266
  %".5" = load i64, i64* %".4", !dbg !266
  %".6" = icmp eq i64 %".5", 0 , !dbg !266
  br i1 %".6", label %"if.then", label %"if.end", !dbg !266
if.then:
  ret i32 0, !dbg !267
if.end:
  %".9" = call i32 @"has_bool_operators"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !268
  %".10" = sext i32 %".9" to i64 , !dbg !268
  %".11" = icmp ne i64 %".10", 0 , !dbg !268
  br i1 %".11", label %"if.then.1", label %"if.end.1", !dbg !268
if.then.1:
  ret i32 4, !dbg !269
if.end.1:
  %".14" = call i32 @"is_attribute"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !270
  %".15" = sext i32 %".14" to i64 , !dbg !270
  %".16" = icmp ne i64 %".15", 0 , !dbg !270
  br i1 %".16", label %"if.then.2", label %"if.end.2", !dbg !270
if.then.2:
  ret i32 5, !dbg !271
if.end.2:
  %".19" = call i32 @"has_suite_separator"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !272
  %".20" = sext i32 %".19" to i64 , !dbg !272
  %".21" = icmp ne i64 %".20", 0 , !dbg !272
  br i1 %".21", label %"if.then.3", label %"if.end.3", !dbg !272
if.then.3:
  ret i32 3, !dbg !273
if.end.3:
  %".24" = call i32 @"has_glob_chars"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !274
  %".25" = sext i32 %".24" to i64 , !dbg !274
  %".26" = icmp ne i64 %".25", 0 , !dbg !274
  br i1 %".26", label %"if.then.4", label %"if.end.4", !dbg !274
if.then.4:
  ret i32 2, !dbg !275
if.end.4:
  ret i32 1, !dbg !276
}

define i32 @"filter_match_sv"(%"struct.ritz_module_1.StrView"* %"pattern.arg", %"struct.ritz_module_1.StrView"* %"test_name.arg") !dbg !34
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"pattern.arg", metadata !277, metadata !7), !dbg !278
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"test_name.arg", metadata !279, metadata !7), !dbg !278
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"pattern.arg", i32 0, i32 1 , !dbg !280
  %".7" = load i64, i64* %".6", !dbg !280
  %".8" = icmp eq i64 %".7", 0 , !dbg !280
  br i1 %".8", label %"if.then", label %"if.end", !dbg !280
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !281
  ret i32 %".10", !dbg !281
if.end:
  %".12" = call i32 @"filter_type_sv"(%"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !282
  %".13" = icmp eq i32 %".12", 0 , !dbg !283
  br i1 %".13", label %"if.then.1", label %"if.end.1", !dbg !283
if.then.1:
  %".15" = trunc i64 1 to i32 , !dbg !284
  ret i32 %".15", !dbg !284
if.end.1:
  %".17" = icmp eq i32 %".12", 4 , !dbg !285
  br i1 %".17", label %"if.then.2", label %"if.end.2", !dbg !285
if.then.2:
  %".19" = call i32 @"match_bool_expr"(%"struct.ritz_module_1.StrView"* %"pattern.arg", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !286
  ret i32 %".19", !dbg !286
if.end.2:
  %".21" = icmp eq i32 %".12", 5 , !dbg !287
  br i1 %".21", label %"if.then.3", label %"if.end.3", !dbg !287
if.then.3:
  %".23" = call i32 @"match_attribute"(%"struct.ritz_module_1.StrView"* %"pattern.arg", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !288
  ret i32 %".23", !dbg !288
if.end.3:
  %".25" = icmp eq i32 %".12", 1 , !dbg !289
  br i1 %".25", label %"if.then.4", label %"if.end.4", !dbg !289
if.then.4:
  %".27" = call i32 @"contains_substring"(%"struct.ritz_module_1.StrView"* %"test_name.arg", %"struct.ritz_module_1.StrView"* %"pattern.arg"), !dbg !290
  ret i32 %".27", !dbg !290
if.end.4:
  %".29" = icmp eq i32 %".12", 2 , !dbg !291
  br i1 %".29", label %"if.then.5", label %"if.end.5", !dbg !291
if.then.5:
  %".31" = call i32 @"glob_match"(%"struct.ritz_module_1.StrView"* %"pattern.arg", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !292
  ret i32 %".31", !dbg !292
if.end.5:
  %".33" = icmp eq i32 %".12", 3 , !dbg !293
  br i1 %".33", label %"if.then.6", label %"if.end.6", !dbg !293
if.then.6:
  %".35" = call i32 @"match_suite_pattern"(%"struct.ritz_module_1.StrView"* %"pattern.arg", %"struct.ritz_module_1.StrView"* %"test_name.arg"), !dbg !294
  ret i32 %".35", !dbg !294
if.end.6:
  %".37" = trunc i64 0 to i32 , !dbg !295
  ret i32 %".37", !dbg !295
}

define i32 @"filter_match"(i8* %"pattern.arg", i8* %"test_name.arg") !dbg !35
{
entry:
  %"pattern" = alloca i8*
  %"pat_sv.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !302
  %"name_sv.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !305
  store i8* %"pattern.arg", i8** %"pattern"
  call void @"llvm.dbg.declare"(metadata i8** %"pattern", metadata !297, metadata !7), !dbg !298
  %"test_name" = alloca i8*
  store i8* %"test_name.arg", i8** %"test_name"
  call void @"llvm.dbg.declare"(metadata i8** %"test_name", metadata !299, metadata !7), !dbg !298
  %".8" = load i8*, i8** %"pattern", !dbg !300
  %".9" = icmp eq i8* %".8", null , !dbg !300
  br i1 %".9", label %"if.then", label %"if.end", !dbg !300
if.then:
  %".11" = trunc i64 1 to i32 , !dbg !301
  ret i32 %".11", !dbg !301
if.end:
  %".13" = load i8*, i8** %"pattern", !dbg !302
  %".14" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".13"), !dbg !302
  store %"struct.ritz_module_1.StrView" %".14", %"struct.ritz_module_1.StrView"* %"pat_sv.addr", !dbg !302
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"pat_sv.addr", metadata !303, metadata !7), !dbg !304
  %".17" = load i8*, i8** %"test_name", !dbg !305
  %".18" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".17"), !dbg !305
  store %"struct.ritz_module_1.StrView" %".18", %"struct.ritz_module_1.StrView"* %"name_sv.addr", !dbg !305
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name_sv.addr", metadata !306, metadata !7), !dbg !307
  %".21" = call i32 @"filter_match_sv"(%"struct.ritz_module_1.StrView"* %"pat_sv.addr", %"struct.ritz_module_1.StrView"* %"name_sv.addr"), !dbg !308
  ret i32 %".21", !dbg !308
}

define i32 @"filter_type"(i8* %"pattern.arg") !dbg !36
{
entry:
  %"pattern" = alloca i8*
  %"pat_sv.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !313
  store i8* %"pattern.arg", i8** %"pattern"
  call void @"llvm.dbg.declare"(metadata i8** %"pattern", metadata !309, metadata !7), !dbg !310
  %".5" = load i8*, i8** %"pattern", !dbg !311
  %".6" = icmp eq i8* %".5", null , !dbg !311
  br i1 %".6", label %"if.then", label %"if.end", !dbg !311
if.then:
  ret i32 0, !dbg !312
if.end:
  %".9" = load i8*, i8** %"pattern", !dbg !313
  %".10" = call %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %".9"), !dbg !313
  store %"struct.ritz_module_1.StrView" %".10", %"struct.ritz_module_1.StrView"* %"pat_sv.addr", !dbg !313
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"pat_sv.addr", metadata !314, metadata !7), !dbg !315
  %".13" = call i32 @"filter_type_sv"(%"struct.ritz_module_1.StrView"* %"pat_sv.addr"), !dbg !316
  ret i32 %".13", !dbg !316
}

@".str.0" = private constant [4 x i8] c"and\00"
@".str.1" = private constant [3 x i8] c"or\00"
@".str.2" = private constant [4 x i8] c"not\00"
@".str.3" = private constant [7 x i8] c"ignore\00"
@".str.4" = private constant [5 x i8] c"skip\00"
@".str.5" = private constant [7 x i8] c"ignore\00"
@".str.6" = private constant [5 x i8] c"slow\00"
@".str.7" = private constant [5 x i8] c"slow\00"
@".str.8" = private constant [5 x i8] c"fast\00"
@".str.9" = private constant [5 x i8] c"slow\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/ritzunit/src", filename: "filter.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 44, name: "is_space", scopeLine: 44, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 48, name: "starts_with_keyword", scopeLine: 48, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 62, name: "find_keyword", scopeLine: 62, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 87, name: "find_and", scopeLine: 87, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 92, name: "find_or", scopeLine: 92, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 97, name: "starts_with_not", scopeLine: 97, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 103, name: "has_bool_operators", scopeLine: 103, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 113, name: "has_glob_chars", scopeLine: 113, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 121, name: "has_suite_separator", scopeLine: 121, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 136, name: "is_attribute", scopeLine: 136, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 143, name: "contains_substring", scopeLine: 143, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 151, name: "match_attribute", scopeLine: 151, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 182, name: "glob_match", scopeLine: 182, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 226, name: "match_suite_pattern", scopeLine: 226, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 255, name: "match_simple_pattern", scopeLine: 255, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 276, name: "match_bool_expr", scopeLine: 276, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 312, name: "filter_type_sv", scopeLine: 312, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 331, name: "filter_match_sv", scopeLine: 331, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 362, name: "filter_match", scopeLine: 362, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 370, name: "filter_type", scopeLine: 370, type: !4, unit: !1)
!37 = !DILocalVariable(file: !0, line: 44, name: "c", scope: !17, type: !12)
!38 = !DILocation(column: 1, line: 44, scope: !17)
!39 = !DILocation(column: 5, line: 45, scope: !17)
!40 = !DICompositeType(align: 64, file: !0, name: "StrView", size: 128, tag: DW_TAG_structure_type)
!41 = !DIDerivedType(baseType: !40, size: 64, tag: DW_TAG_reference_type)
!42 = !DILocalVariable(file: !0, line: 48, name: "s", scope: !18, type: !41)
!43 = !DILocation(column: 1, line: 48, scope: !18)
!44 = !DILocalVariable(file: !0, line: 48, name: "keyword", scope: !18, type: !41)
!45 = !DILocation(column: 5, line: 49, scope: !18)
!46 = !DILocation(column: 9, line: 50, scope: !18)
!47 = !DILocation(column: 5, line: 52, scope: !18)
!48 = !DILocation(column: 9, line: 53, scope: !18)
!49 = !DILocation(column: 5, line: 55, scope: !18)
!50 = !DILocation(column: 9, line: 56, scope: !18)
!51 = !DILocation(column: 5, line: 57, scope: !18)
!52 = !DILocation(column: 5, line: 58, scope: !18)
!53 = !DILocalVariable(file: !0, line: 62, name: "s", scope: !19, type: !41)
!54 = !DILocation(column: 1, line: 62, scope: !19)
!55 = !DILocalVariable(file: !0, line: 62, name: "keyword", scope: !19, type: !41)
!56 = !DILocation(column: 5, line: 63, scope: !19)
!57 = !DILocalVariable(file: !0, line: 63, name: "pos", scope: !19, type: !11)
!58 = !DILocation(column: 1, line: 63, scope: !19)
!59 = !DILocation(column: 5, line: 64, scope: !19)
!60 = !DILocation(column: 9, line: 66, scope: !19)
!61 = !DILocation(column: 13, line: 67, scope: !19)
!62 = !DILocation(column: 17, line: 69, scope: !19)
!63 = !DILocation(column: 17, line: 70, scope: !19)
!64 = !DILocation(column: 9, line: 73, scope: !19)
!65 = !DILocalVariable(file: !0, line: 73, name: "sub", scope: !19, type: !40)
!66 = !DILocation(column: 1, line: 73, scope: !19)
!67 = !DILocation(column: 9, line: 74, scope: !19)
!68 = !DILocation(column: 13, line: 76, scope: !19)
!69 = !DILocation(column: 17, line: 77, scope: !19)
!70 = !DILocation(column: 13, line: 78, scope: !19)
!71 = !DILocation(column: 17, line: 80, scope: !19)
!72 = !DILocation(column: 9, line: 82, scope: !19)
!73 = !DILocation(column: 5, line: 84, scope: !19)
!74 = !DILocalVariable(file: !0, line: 87, name: "s", scope: !20, type: !41)
!75 = !DILocation(column: 1, line: 87, scope: !20)
!76 = !DILocation(column: 5, line: 88, scope: !20)
!77 = !DILocalVariable(file: !0, line: 88, name: "kw", scope: !20, type: !40)
!78 = !DILocation(column: 1, line: 88, scope: !20)
!79 = !DILocation(column: 5, line: 89, scope: !20)
!80 = !DILocalVariable(file: !0, line: 92, name: "s", scope: !21, type: !41)
!81 = !DILocation(column: 1, line: 92, scope: !21)
!82 = !DILocation(column: 5, line: 93, scope: !21)
!83 = !DILocalVariable(file: !0, line: 93, name: "kw", scope: !21, type: !40)
!84 = !DILocation(column: 1, line: 93, scope: !21)
!85 = !DILocation(column: 5, line: 94, scope: !21)
!86 = !DILocalVariable(file: !0, line: 97, name: "s", scope: !22, type: !41)
!87 = !DILocation(column: 1, line: 97, scope: !22)
!88 = !DILocation(column: 5, line: 98, scope: !22)
!89 = !DILocalVariable(file: !0, line: 98, name: "trimmed", scope: !22, type: !40)
!90 = !DILocation(column: 1, line: 98, scope: !22)
!91 = !DILocation(column: 5, line: 99, scope: !22)
!92 = !DILocalVariable(file: !0, line: 99, name: "kw", scope: !22, type: !40)
!93 = !DILocation(column: 1, line: 99, scope: !22)
!94 = !DILocation(column: 5, line: 100, scope: !22)
!95 = !DILocalVariable(file: !0, line: 103, name: "pattern", scope: !23, type: !41)
!96 = !DILocation(column: 1, line: 103, scope: !23)
!97 = !DILocation(column: 5, line: 104, scope: !23)
!98 = !DILocation(column: 9, line: 105, scope: !23)
!99 = !DILocation(column: 5, line: 106, scope: !23)
!100 = !DILocation(column: 9, line: 107, scope: !23)
!101 = !DILocation(column: 5, line: 108, scope: !23)
!102 = !DILocation(column: 9, line: 109, scope: !23)
!103 = !DILocation(column: 5, line: 110, scope: !23)
!104 = !DILocalVariable(file: !0, line: 113, name: "pattern", scope: !24, type: !41)
!105 = !DILocation(column: 1, line: 113, scope: !24)
!106 = !DILocation(column: 5, line: 114, scope: !24)
!107 = !DILocation(column: 9, line: 115, scope: !24)
!108 = !DILocation(column: 5, line: 116, scope: !24)
!109 = !DILocation(column: 9, line: 117, scope: !24)
!110 = !DILocation(column: 5, line: 118, scope: !24)
!111 = !DILocalVariable(file: !0, line: 121, name: "pattern", scope: !25, type: !41)
!112 = !DILocation(column: 1, line: 121, scope: !25)
!113 = !DILocation(column: 5, line: 123, scope: !25)
!114 = !DILocalVariable(file: !0, line: 123, name: "pos", scope: !25, type: !11)
!115 = !DILocation(column: 1, line: 123, scope: !25)
!116 = !DILocation(column: 5, line: 124, scope: !25)
!117 = !DILocation(column: 9, line: 125, scope: !25)
!118 = !DILocation(column: 13, line: 126, scope: !25)
!119 = !DILocation(column: 9, line: 127, scope: !25)
!120 = !DILocation(column: 5, line: 128, scope: !25)
!121 = !DILocalVariable(file: !0, line: 136, name: "pattern", scope: !26, type: !41)
!122 = !DILocation(column: 1, line: 136, scope: !26)
!123 = !DILocation(column: 5, line: 137, scope: !26)
!124 = !DILocalVariable(file: !0, line: 137, name: "trimmed", scope: !26, type: !40)
!125 = !DILocation(column: 1, line: 137, scope: !26)
!126 = !DILocation(column: 5, line: 138, scope: !26)
!127 = !DILocation(column: 9, line: 139, scope: !26)
!128 = !DILocation(column: 5, line: 140, scope: !26)
!129 = !DILocalVariable(file: !0, line: 143, name: "haystack", scope: !27, type: !41)
!130 = !DILocation(column: 1, line: 143, scope: !27)
!131 = !DILocalVariable(file: !0, line: 143, name: "needle", scope: !27, type: !41)
!132 = !DILocation(column: 5, line: 144, scope: !27)
!133 = !DILocalVariable(file: !0, line: 151, name: "attr", scope: !28, type: !41)
!134 = !DILocation(column: 1, line: 151, scope: !28)
!135 = !DILocalVariable(file: !0, line: 151, name: "test_name", scope: !28, type: !41)
!136 = !DILocation(column: 5, line: 153, scope: !28)
!137 = !DILocalVariable(file: !0, line: 153, name: "trimmed", scope: !28, type: !40)
!138 = !DILocation(column: 1, line: 153, scope: !28)
!139 = !DILocation(column: 5, line: 154, scope: !28)
!140 = !DILocation(column: 9, line: 155, scope: !28)
!141 = !DILocation(column: 5, line: 158, scope: !28)
!142 = !DILocation(column: 9, line: 159, scope: !28)
!143 = !DILocalVariable(file: !0, line: 159, name: "needle", scope: !28, type: !40)
!144 = !DILocation(column: 1, line: 159, scope: !28)
!145 = !DILocation(column: 9, line: 160, scope: !28)
!146 = !DILocation(column: 5, line: 163, scope: !28)
!147 = !DILocation(column: 9, line: 164, scope: !28)
!148 = !DILocalVariable(file: !0, line: 164, name: "needle", scope: !28, type: !40)
!149 = !DILocation(column: 1, line: 164, scope: !28)
!150 = !DILocation(column: 9, line: 165, scope: !28)
!151 = !DILocation(column: 5, line: 168, scope: !28)
!152 = !DILocation(column: 9, line: 169, scope: !28)
!153 = !DILocalVariable(file: !0, line: 169, name: "needle", scope: !28, type: !40)
!154 = !DILocation(column: 1, line: 169, scope: !28)
!155 = !DILocation(column: 9, line: 170, scope: !28)
!156 = !DILocation(column: 5, line: 173, scope: !28)
!157 = !DILocalVariable(file: !0, line: 182, name: "pattern", scope: !29, type: !41)
!158 = !DILocation(column: 1, line: 182, scope: !29)
!159 = !DILocalVariable(file: !0, line: 182, name: "text", scope: !29, type: !41)
!160 = !DILocation(column: 5, line: 183, scope: !29)
!161 = !DILocalVariable(file: !0, line: 183, name: "p", scope: !29, type: !11)
!162 = !DILocation(column: 1, line: 183, scope: !29)
!163 = !DILocation(column: 5, line: 184, scope: !29)
!164 = !DILocalVariable(file: !0, line: 184, name: "t", scope: !29, type: !11)
!165 = !DILocation(column: 1, line: 184, scope: !29)
!166 = !DILocation(column: 5, line: 185, scope: !29)
!167 = !DILocalVariable(file: !0, line: 185, name: "star_p", scope: !29, type: !11)
!168 = !DILocation(column: 1, line: 185, scope: !29)
!169 = !DILocation(column: 5, line: 186, scope: !29)
!170 = !DILocalVariable(file: !0, line: 186, name: "star_t", scope: !29, type: !11)
!171 = !DILocation(column: 1, line: 186, scope: !29)
!172 = !DILocation(column: 5, line: 188, scope: !29)
!173 = !DILocation(column: 9, line: 189, scope: !29)
!174 = !DILocalVariable(file: !0, line: 189, name: "pc", scope: !29, type: !12)
!175 = !DILocation(column: 1, line: 189, scope: !29)
!176 = !DILocation(column: 9, line: 190, scope: !29)
!177 = !DILocation(column: 13, line: 191, scope: !29)
!178 = !DILocation(column: 9, line: 192, scope: !29)
!179 = !DILocation(column: 13, line: 196, scope: !29)
!180 = !DILocation(column: 13, line: 197, scope: !29)
!181 = !DILocation(column: 13, line: 198, scope: !29)
!182 = !DILocation(column: 13, line: 201, scope: !29)
!183 = !DILocation(column: 13, line: 202, scope: !29)
!184 = !DILocation(column: 13, line: 205, scope: !29)
!185 = !DILocation(column: 13, line: 206, scope: !29)
!186 = !DILocation(column: 13, line: 207, scope: !29)
!187 = !DILocation(column: 13, line: 210, scope: !29)
!188 = !DILocation(column: 5, line: 213, scope: !29)
!189 = !DILocation(column: 9, line: 214, scope: !29)
!190 = !DILocation(column: 5, line: 217, scope: !29)
!191 = !DILocalVariable(file: !0, line: 226, name: "pattern", scope: !30, type: !41)
!192 = !DILocation(column: 1, line: 226, scope: !30)
!193 = !DILocalVariable(file: !0, line: 226, name: "test_name", scope: !30, type: !41)
!194 = !DILocation(column: 5, line: 228, scope: !30)
!195 = !DILocalVariable(file: !0, line: 228, name: "sep_pos", scope: !30, type: !11)
!196 = !DILocation(column: 1, line: 228, scope: !30)
!197 = !DILocation(column: 5, line: 229, scope: !30)
!198 = !DILocalVariable(file: !0, line: 229, name: "i", scope: !30, type: !11)
!199 = !DILocation(column: 1, line: 229, scope: !30)
!200 = !DILocation(column: 5, line: 230, scope: !30)
!201 = !DILocation(column: 9, line: 231, scope: !30)
!202 = !DILocation(column: 13, line: 232, scope: !30)
!203 = !DILocation(column: 13, line: 233, scope: !30)
!204 = !DILocation(column: 9, line: 234, scope: !30)
!205 = !DILocation(column: 5, line: 236, scope: !30)
!206 = !DILocation(column: 9, line: 238, scope: !30)
!207 = !DILocation(column: 5, line: 241, scope: !30)
!208 = !DILocalVariable(file: !0, line: 241, name: "test_pattern", scope: !30, type: !40)
!209 = !DILocation(column: 1, line: 241, scope: !30)
!210 = !DILocation(column: 5, line: 244, scope: !30)
!211 = !DILocation(column: 9, line: 245, scope: !30)
!212 = !DILocation(column: 5, line: 248, scope: !30)
!213 = !DILocalVariable(file: !0, line: 255, name: "pattern", scope: !31, type: !41)
!214 = !DILocation(column: 1, line: 255, scope: !31)
!215 = !DILocalVariable(file: !0, line: 255, name: "test_name", scope: !31, type: !41)
!216 = !DILocation(column: 5, line: 257, scope: !31)
!217 = !DILocalVariable(file: !0, line: 257, name: "trimmed", scope: !31, type: !40)
!218 = !DILocation(column: 1, line: 257, scope: !31)
!219 = !DILocation(column: 5, line: 259, scope: !31)
!220 = !DILocation(column: 9, line: 260, scope: !31)
!221 = !DILocation(column: 5, line: 263, scope: !31)
!222 = !DILocation(column: 9, line: 264, scope: !31)
!223 = !DILocation(column: 5, line: 267, scope: !31)
!224 = !DILocation(column: 9, line: 268, scope: !31)
!225 = !DILocation(column: 5, line: 269, scope: !31)
!226 = !DILocation(column: 9, line: 270, scope: !31)
!227 = !DILocation(column: 5, line: 273, scope: !31)
!228 = !DILocalVariable(file: !0, line: 276, name: "pattern", scope: !32, type: !41)
!229 = !DILocation(column: 1, line: 276, scope: !32)
!230 = !DILocalVariable(file: !0, line: 276, name: "test_name", scope: !32, type: !41)
!231 = !DILocation(column: 5, line: 277, scope: !32)
!232 = !DILocation(column: 9, line: 278, scope: !32)
!233 = !DILocation(column: 5, line: 281, scope: !32)
!234 = !DILocation(column: 5, line: 282, scope: !32)
!235 = !DILocation(column: 9, line: 283, scope: !32)
!236 = !DILocalVariable(file: !0, line: 283, name: "left", scope: !32, type: !40)
!237 = !DILocation(column: 1, line: 283, scope: !32)
!238 = !DILocation(column: 9, line: 284, scope: !32)
!239 = !DILocalVariable(file: !0, line: 284, name: "right", scope: !32, type: !40)
!240 = !DILocation(column: 1, line: 284, scope: !32)
!241 = !DILocation(column: 9, line: 285, scope: !32)
!242 = !DILocation(column: 13, line: 286, scope: !32)
!243 = !DILocation(column: 9, line: 287, scope: !32)
!244 = !DILocation(column: 5, line: 290, scope: !32)
!245 = !DILocation(column: 5, line: 291, scope: !32)
!246 = !DILocation(column: 9, line: 292, scope: !32)
!247 = !DILocalVariable(file: !0, line: 292, name: "left", scope: !32, type: !40)
!248 = !DILocation(column: 1, line: 292, scope: !32)
!249 = !DILocation(column: 9, line: 293, scope: !32)
!250 = !DILocalVariable(file: !0, line: 293, name: "right", scope: !32, type: !40)
!251 = !DILocation(column: 1, line: 293, scope: !32)
!252 = !DILocation(column: 9, line: 294, scope: !32)
!253 = !DILocation(column: 13, line: 295, scope: !32)
!254 = !DILocation(column: 9, line: 296, scope: !32)
!255 = !DILocation(column: 5, line: 299, scope: !32)
!256 = !DILocation(column: 9, line: 300, scope: !32)
!257 = !DILocalVariable(file: !0, line: 300, name: "trimmed", scope: !32, type: !40)
!258 = !DILocation(column: 1, line: 300, scope: !32)
!259 = !DILocation(column: 9, line: 301, scope: !32)
!260 = !DILocalVariable(file: !0, line: 301, name: "rest", scope: !32, type: !40)
!261 = !DILocation(column: 1, line: 301, scope: !32)
!262 = !DILocation(column: 9, line: 302, scope: !32)
!263 = !DILocation(column: 5, line: 305, scope: !32)
!264 = !DILocalVariable(file: !0, line: 312, name: "pattern", scope: !33, type: !41)
!265 = !DILocation(column: 1, line: 312, scope: !33)
!266 = !DILocation(column: 5, line: 313, scope: !33)
!267 = !DILocation(column: 9, line: 314, scope: !33)
!268 = !DILocation(column: 5, line: 315, scope: !33)
!269 = !DILocation(column: 9, line: 316, scope: !33)
!270 = !DILocation(column: 5, line: 317, scope: !33)
!271 = !DILocation(column: 9, line: 318, scope: !33)
!272 = !DILocation(column: 5, line: 319, scope: !33)
!273 = !DILocation(column: 9, line: 320, scope: !33)
!274 = !DILocation(column: 5, line: 321, scope: !33)
!275 = !DILocation(column: 9, line: 322, scope: !33)
!276 = !DILocation(column: 5, line: 323, scope: !33)
!277 = !DILocalVariable(file: !0, line: 331, name: "pattern", scope: !34, type: !41)
!278 = !DILocation(column: 1, line: 331, scope: !34)
!279 = !DILocalVariable(file: !0, line: 331, name: "test_name", scope: !34, type: !41)
!280 = !DILocation(column: 5, line: 332, scope: !34)
!281 = !DILocation(column: 9, line: 333, scope: !34)
!282 = !DILocation(column: 5, line: 335, scope: !34)
!283 = !DILocation(column: 5, line: 337, scope: !34)
!284 = !DILocation(column: 9, line: 338, scope: !34)
!285 = !DILocation(column: 5, line: 340, scope: !34)
!286 = !DILocation(column: 9, line: 341, scope: !34)
!287 = !DILocation(column: 5, line: 343, scope: !34)
!288 = !DILocation(column: 9, line: 344, scope: !34)
!289 = !DILocation(column: 5, line: 346, scope: !34)
!290 = !DILocation(column: 9, line: 347, scope: !34)
!291 = !DILocation(column: 5, line: 349, scope: !34)
!292 = !DILocation(column: 9, line: 350, scope: !34)
!293 = !DILocation(column: 5, line: 352, scope: !34)
!294 = !DILocation(column: 9, line: 353, scope: !34)
!295 = !DILocation(column: 5, line: 355, scope: !34)
!296 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!297 = !DILocalVariable(file: !0, line: 362, name: "pattern", scope: !35, type: !296)
!298 = !DILocation(column: 1, line: 362, scope: !35)
!299 = !DILocalVariable(file: !0, line: 362, name: "test_name", scope: !35, type: !296)
!300 = !DILocation(column: 5, line: 363, scope: !35)
!301 = !DILocation(column: 9, line: 364, scope: !35)
!302 = !DILocation(column: 5, line: 366, scope: !35)
!303 = !DILocalVariable(file: !0, line: 366, name: "pat_sv", scope: !35, type: !40)
!304 = !DILocation(column: 1, line: 366, scope: !35)
!305 = !DILocation(column: 5, line: 367, scope: !35)
!306 = !DILocalVariable(file: !0, line: 367, name: "name_sv", scope: !35, type: !40)
!307 = !DILocation(column: 1, line: 367, scope: !35)
!308 = !DILocation(column: 5, line: 368, scope: !35)
!309 = !DILocalVariable(file: !0, line: 370, name: "pattern", scope: !36, type: !296)
!310 = !DILocation(column: 1, line: 370, scope: !36)
!311 = !DILocation(column: 5, line: 371, scope: !36)
!312 = !DILocation(column: 9, line: 372, scope: !36)
!313 = !DILocation(column: 5, line: 373, scope: !36)
!314 = !DILocalVariable(file: !0, line: 373, name: "pat_sv", scope: !36, type: !40)
!315 = !DILocation(column: 1, line: 373, scope: !36)
!316 = !DILocation(column: 5, line: 374, scope: !36)