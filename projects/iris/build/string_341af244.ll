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

define %"struct.ritz_module_1.String" @"string_new"() !dbg !17
{
entry:
  %"s.addr" = alloca %"struct.ritz_module_1.String", !dbg !66
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.addr", metadata !68, metadata !7), !dbg !69
  %".3" = call %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"(), !dbg !70
  %".4" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !70
  %".5" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", i32 0, i32 0 , !dbg !70
  store %"struct.ritz_module_1.Vec$u8" %".3", %"struct.ritz_module_1.Vec$u8"* %".5", !dbg !70
  %".7" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !71
  ret %"struct.ritz_module_1.String" %".7", !dbg !71
}

define %"struct.ritz_module_1.String" @"string_with_cap"(i64 %"cap.arg") !dbg !18
{
entry:
  %"cap" = alloca i64
  %"s.addr" = alloca %"struct.ritz_module_1.String", !dbg !74
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !72, metadata !7), !dbg !73
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.addr", metadata !75, metadata !7), !dbg !76
  %".6" = load i64, i64* %"cap", !dbg !77
  %".7" = call %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %".6"), !dbg !77
  %".8" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !77
  %".9" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", i32 0, i32 0 , !dbg !77
  store %"struct.ritz_module_1.Vec$u8" %".7", %"struct.ritz_module_1.Vec$u8"* %".9", !dbg !77
  %".11" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !78
  ret %"struct.ritz_module_1.String" %".11", !dbg !78
}

define %"struct.ritz_module_1.String" @"string_from"(%"struct.ritz_module_1.StrView" %"sv.arg") !dbg !19
{
entry:
  %"sv" = alloca %"struct.ritz_module_1.StrView"
  %"s.addr" = alloca %"struct.ritz_module_1.String", !dbg !82
  %"i" = alloca i64, !dbg !87
  store %"struct.ritz_module_1.StrView" %"sv.arg", %"struct.ritz_module_1.StrView"* %"sv"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"sv", metadata !80, metadata !7), !dbg !81
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.addr", metadata !83, metadata !7), !dbg !84
  %".6" = call %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"(), !dbg !85
  %".7" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !85
  %".8" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", i32 0, i32 0 , !dbg !85
  store %"struct.ritz_module_1.Vec$u8" %".6", %"struct.ritz_module_1.Vec$u8"* %".8", !dbg !85
  %".10" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", i32 0, i32 0 , !dbg !86
  %".11" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"sv", i32 0, i32 1 , !dbg !86
  %".12" = load i64, i64* %".11", !dbg !86
  %".13" = add i64 %".12", 1, !dbg !86
  %".14" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %".10", i64 %".13"), !dbg !86
  %".15" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"sv", i32 0, i32 1 , !dbg !87
  %".16" = load i64, i64* %".15", !dbg !87
  store i64 0, i64* %"i", !dbg !87
  br label %"for.cond", !dbg !87
for.cond:
  %".19" = load i64, i64* %"i", !dbg !87
  %".20" = icmp slt i64 %".19", %".16" , !dbg !87
  br i1 %".20", label %"for.body", label %"for.end", !dbg !87
for.body:
  %".22" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", i32 0, i32 0 , !dbg !87
  %".23" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"sv", i32 0, i32 0 , !dbg !87
  %".24" = load i8*, i8** %".23", !dbg !87
  %".25" = load i64, i64* %"i", !dbg !87
  %".26" = getelementptr i8, i8* %".24", i64 %".25" , !dbg !87
  %".27" = load i8, i8* %".26", !dbg !87
  %".28" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %".22", i8 %".27"), !dbg !87
  br label %"for.incr", !dbg !87
for.incr:
  %".30" = load i64, i64* %"i", !dbg !87
  %".31" = add i64 %".30", 1, !dbg !87
  store i64 %".31", i64* %"i", !dbg !87
  br label %"for.cond", !dbg !87
for.end:
  %".34" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !88
  ret %"struct.ritz_module_1.String" %".34", !dbg !88
}

define %"struct.ritz_module_1.String" @"string_from_cstr"(i8* %"cstr.arg") !dbg !20
{
entry:
  %"cstr" = alloca i8*
  %"s.addr" = alloca %"struct.ritz_module_1.String", !dbg !92
  %"len.addr" = alloca i64, !dbg !96
  %"i" = alloca i64, !dbg !102
  store i8* %"cstr.arg", i8** %"cstr"
  call void @"llvm.dbg.declare"(metadata i8** %"cstr", metadata !90, metadata !7), !dbg !91
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.addr", metadata !93, metadata !7), !dbg !94
  %".6" = call %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"(), !dbg !95
  %".7" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !95
  %".8" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", i32 0, i32 0 , !dbg !95
  store %"struct.ritz_module_1.Vec$u8" %".6", %"struct.ritz_module_1.Vec$u8"* %".8", !dbg !95
  store i64 0, i64* %"len.addr", !dbg !96
  call void @"llvm.dbg.declare"(metadata i64* %"len.addr", metadata !97, metadata !7), !dbg !98
  br label %"while.cond", !dbg !99
while.cond:
  %".13" = load i8*, i8** %"cstr", !dbg !99
  %".14" = load i64, i64* %"len.addr", !dbg !99
  %".15" = getelementptr i8, i8* %".13", i64 %".14" , !dbg !99
  %".16" = load i8, i8* %".15", !dbg !99
  %".17" = zext i8 %".16" to i64 , !dbg !99
  %".18" = icmp ne i64 %".17", 0 , !dbg !99
  br i1 %".18", label %"while.body", label %"while.end", !dbg !99
while.body:
  %".20" = load i64, i64* %"len.addr", !dbg !100
  %".21" = add i64 %".20", 1, !dbg !100
  store i64 %".21", i64* %"len.addr", !dbg !100
  br label %"while.cond", !dbg !100
while.end:
  %".24" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", i32 0, i32 0 , !dbg !101
  %".25" = load i64, i64* %"len.addr", !dbg !101
  %".26" = add i64 %".25", 1, !dbg !101
  %".27" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %".24", i64 %".26"), !dbg !101
  %".28" = load i64, i64* %"len.addr", !dbg !102
  store i64 0, i64* %"i", !dbg !102
  br label %"for.cond", !dbg !102
for.cond:
  %".31" = load i64, i64* %"i", !dbg !102
  %".32" = icmp slt i64 %".31", %".28" , !dbg !102
  br i1 %".32", label %"for.body", label %"for.end", !dbg !102
for.body:
  %".34" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", i32 0, i32 0 , !dbg !102
  %".35" = load i8*, i8** %"cstr", !dbg !102
  %".36" = load i64, i64* %"i", !dbg !102
  %".37" = getelementptr i8, i8* %".35", i64 %".36" , !dbg !102
  %".38" = load i8, i8* %".37", !dbg !102
  %".39" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %".34", i8 %".38"), !dbg !102
  br label %"for.incr", !dbg !102
for.incr:
  %".41" = load i64, i64* %"i", !dbg !102
  %".42" = add i64 %".41", 1, !dbg !102
  store i64 %".42", i64* %"i", !dbg !102
  br label %"for.cond", !dbg !102
for.end:
  %".45" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !103
  ret %"struct.ritz_module_1.String" %".45", !dbg !103
}

define %"struct.ritz_module_1.String" @"string_from_bytes"(i8* %"bytes.arg", i64 %"len.arg") !dbg !21
{
entry:
  %"bytes" = alloca i8*
  %"s.addr" = alloca %"struct.ritz_module_1.String", !dbg !107
  %"i" = alloca i64, !dbg !112
  store i8* %"bytes.arg", i8** %"bytes"
  call void @"llvm.dbg.declare"(metadata i8** %"bytes", metadata !104, metadata !7), !dbg !105
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !106, metadata !7), !dbg !105
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.addr", metadata !108, metadata !7), !dbg !109
  %".9" = call %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"(), !dbg !110
  %".10" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !110
  %".11" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", i32 0, i32 0 , !dbg !110
  store %"struct.ritz_module_1.Vec$u8" %".9", %"struct.ritz_module_1.Vec$u8"* %".11", !dbg !110
  %".13" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", i32 0, i32 0 , !dbg !111
  %".14" = load i64, i64* %"len", !dbg !111
  %".15" = add i64 %".14", 1, !dbg !111
  %".16" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %".13", i64 %".15"), !dbg !111
  %".17" = load i64, i64* %"len", !dbg !112
  store i64 0, i64* %"i", !dbg !112
  br label %"for.cond", !dbg !112
for.cond:
  %".20" = load i64, i64* %"i", !dbg !112
  %".21" = icmp slt i64 %".20", %".17" , !dbg !112
  br i1 %".21", label %"for.body", label %"for.end", !dbg !112
for.body:
  %".23" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", i32 0, i32 0 , !dbg !112
  %".24" = load i8*, i8** %"bytes", !dbg !112
  %".25" = load i64, i64* %"i", !dbg !112
  %".26" = getelementptr i8, i8* %".24", i64 %".25" , !dbg !112
  %".27" = load i8, i8* %".26", !dbg !112
  %".28" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %".23", i8 %".27"), !dbg !112
  br label %"for.incr", !dbg !112
for.incr:
  %".30" = load i64, i64* %"i", !dbg !112
  %".31" = add i64 %".30", 1, !dbg !112
  store i64 %".31", i64* %"i", !dbg !112
  br label %"for.cond", !dbg !112
for.end:
  %".34" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !113
  ret %"struct.ritz_module_1.String" %".34", !dbg !113
}

define %"struct.ritz_module_1.String" @"string_from_strview"(%"struct.ritz_module_1.StrView"* %"sv.arg") !dbg !22
{
entry:
  %"sv" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"sv.arg", %"struct.ritz_module_1.StrView"** %"sv"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"sv", metadata !115, metadata !7), !dbg !116
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"sv", !dbg !117
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".5", i32 0, i32 0 , !dbg !117
  %".7" = load i8*, i8** %".6", !dbg !117
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"sv", !dbg !117
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".8", i32 0, i32 1 , !dbg !117
  %".10" = load i64, i64* %".9", !dbg !117
  %".11" = call %"struct.ritz_module_1.String" @"string_from_bytes"(i8* %".7", i64 %".10"), !dbg !117
  ret %"struct.ritz_module_1.String" %".11", !dbg !117
}

define i32 @"string_drop"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !23
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !119, metadata !7), !dbg !120
  %".4" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !121
  %".5" = call i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"* %".4"), !dbg !121
  ret i32 %".5", !dbg !121
}

define i64 @"string_len"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !24
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !122, metadata !7), !dbg !123
  %".4" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !124
  %".5" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", !dbg !124
  %".6" = extractvalue %"struct.ritz_module_1.Vec$u8" %".5", 1 , !dbg !124
  ret i64 %".6", !dbg !124
}

define i64 @"string_cap"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !25
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !125, metadata !7), !dbg !126
  %".4" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !127
  %".5" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", !dbg !127
  %".6" = extractvalue %"struct.ritz_module_1.Vec$u8" %".5", 2 , !dbg !127
  ret i64 %".6", !dbg !127
}

define i32 @"string_is_empty"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !26
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !128, metadata !7), !dbg !129
  %".4" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !130
  %".5" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", !dbg !130
  %".6" = extractvalue %"struct.ritz_module_1.Vec$u8" %".5", 1 , !dbg !130
  %".7" = icmp eq i64 %".6", 0 , !dbg !130
  br i1 %".7", label %"if.then", label %"if.end", !dbg !130
if.then:
  %".9" = trunc i64 1 to i32 , !dbg !131
  ret i32 %".9", !dbg !131
if.end:
  %".11" = trunc i64 0 to i32 , !dbg !132
  ret i32 %".11", !dbg !132
}

define i8* @"string_as_ptr"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !27
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !133, metadata !7), !dbg !134
  %".4" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !135
  %".5" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", !dbg !135
  %".6" = extractvalue %"struct.ritz_module_1.Vec$u8" %".5", 1 , !dbg !135
  %".7" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !136
  %".8" = add i64 %".6", 1, !dbg !136
  %".9" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %".7", i64 %".8"), !dbg !136
  %".10" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !137
  %".11" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".10", !dbg !137
  %".12" = extractvalue %"struct.ritz_module_1.Vec$u8" %".11", 0 , !dbg !137
  %".13" = getelementptr i8, i8* %".12", i64 %".6" , !dbg !138
  %".14" = trunc i64 0 to i8 , !dbg !138
  store i8 %".14", i8* %".13", !dbg !138
  ret i8* %".12", !dbg !139
}

define i8 @"string_get"(%"struct.ritz_module_1.String"* %"s.arg", i64 %"idx.arg") !dbg !28
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !140, metadata !7), !dbg !141
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !142, metadata !7), !dbg !141
  %".7" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !143
  %".8" = load i64, i64* %"idx", !dbg !143
  %".9" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".7", i64 %".8"), !dbg !143
  ret i8 %".9", !dbg !143
}

define i32 @"string_push"(%"struct.ritz_module_1.String"* %"s.arg", i8 %"b.arg") !dbg !29
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !144, metadata !7), !dbg !145
  %"b" = alloca i8
  store i8 %"b.arg", i8* %"b"
  call void @"llvm.dbg.declare"(metadata i8* %"b", metadata !146, metadata !7), !dbg !145
  %".7" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !147
  %".8" = load i8, i8* %"b", !dbg !147
  %".9" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %".7", i8 %".8"), !dbg !147
  ret i32 %".9", !dbg !147
}

define i32 @"string_push_str"(%"struct.ritz_module_1.String"* %"s.arg", i8* %"cstr.arg") !dbg !30
{
entry:
  %"i.addr" = alloca i64, !dbg !151
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !148, metadata !7), !dbg !149
  %"cstr" = alloca i8*
  store i8* %"cstr.arg", i8** %"cstr"
  call void @"llvm.dbg.declare"(metadata i8** %"cstr", metadata !150, metadata !7), !dbg !149
  store i64 0, i64* %"i.addr", !dbg !151
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !152, metadata !7), !dbg !153
  br label %"while.cond", !dbg !154
while.cond:
  %".10" = load i8*, i8** %"cstr", !dbg !154
  %".11" = load i64, i64* %"i.addr", !dbg !154
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !154
  %".13" = load i8, i8* %".12", !dbg !154
  %".14" = zext i8 %".13" to i64 , !dbg !154
  %".15" = icmp ne i64 %".14", 0 , !dbg !154
  br i1 %".15", label %"while.body", label %"while.end", !dbg !154
while.body:
  %".17" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !155
  %".18" = load i8*, i8** %"cstr", !dbg !155
  %".19" = load i64, i64* %"i.addr", !dbg !155
  %".20" = getelementptr i8, i8* %".18", i64 %".19" , !dbg !155
  %".21" = load i8, i8* %".20", !dbg !155
  %".22" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %".17", i8 %".21"), !dbg !155
  %".23" = sext i32 %".22" to i64 , !dbg !155
  %".24" = icmp ne i64 %".23", 0 , !dbg !155
  br i1 %".24", label %"if.then", label %"if.end", !dbg !155
while.end:
  %".33" = trunc i64 0 to i32 , !dbg !158
  ret i32 %".33", !dbg !158
if.then:
  %".26" = sub i64 0, 1, !dbg !156
  %".27" = trunc i64 %".26" to i32 , !dbg !156
  ret i32 %".27", !dbg !156
if.end:
  %".29" = load i64, i64* %"i.addr", !dbg !157
  %".30" = add i64 %".29", 1, !dbg !157
  store i64 %".30", i64* %"i.addr", !dbg !157
  br label %"while.cond", !dbg !157
}

define i32 @"string_push_string"(%"struct.ritz_module_1.String"* %"s.arg", %"struct.ritz_module_1.String"* %"other.arg") !dbg !31
{
entry:
  %"i" = alloca i64, !dbg !163
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !159, metadata !7), !dbg !160
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"other.arg", metadata !161, metadata !7), !dbg !160
  %".6" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"other.arg", i32 0, i32 0 , !dbg !162
  %".7" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".6", !dbg !162
  %".8" = extractvalue %"struct.ritz_module_1.Vec$u8" %".7", 1 , !dbg !162
  store i64 0, i64* %"i", !dbg !163
  br label %"for.cond", !dbg !163
for.cond:
  %".11" = load i64, i64* %"i", !dbg !163
  %".12" = icmp slt i64 %".11", %".8" , !dbg !163
  br i1 %".12", label %"for.body", label %"for.end", !dbg !163
for.body:
  %".14" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !163
  %".15" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"other.arg", i32 0, i32 0 , !dbg !163
  %".16" = load i64, i64* %"i", !dbg !163
  %".17" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".15", i64 %".16"), !dbg !163
  %".18" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %".14", i8 %".17"), !dbg !163
  %".19" = sext i32 %".18" to i64 , !dbg !163
  %".20" = icmp ne i64 %".19", 0 , !dbg !163
  br i1 %".20", label %"if.then", label %"if.end", !dbg !163
for.incr:
  %".26" = load i64, i64* %"i", !dbg !164
  %".27" = add i64 %".26", 1, !dbg !164
  store i64 %".27", i64* %"i", !dbg !164
  br label %"for.cond", !dbg !164
for.end:
  %".30" = trunc i64 0 to i32 , !dbg !165
  ret i32 %".30", !dbg !165
if.then:
  %".22" = sub i64 0, 1, !dbg !164
  %".23" = trunc i64 %".22" to i32 , !dbg !164
  ret i32 %".23", !dbg !164
if.end:
  br label %"for.incr", !dbg !164
}

define i32 @"string_push_bytes"(%"struct.ritz_module_1.String"* %"s.arg", i8* %"bytes.arg", i64 %"len.arg") !dbg !32
{
entry:
  %"i" = alloca i64, !dbg !170
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !166, metadata !7), !dbg !167
  %"bytes" = alloca i8*
  store i8* %"bytes.arg", i8** %"bytes"
  call void @"llvm.dbg.declare"(metadata i8** %"bytes", metadata !168, metadata !7), !dbg !167
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !169, metadata !7), !dbg !167
  %".10" = load i64, i64* %"len", !dbg !170
  store i64 0, i64* %"i", !dbg !170
  br label %"for.cond", !dbg !170
for.cond:
  %".13" = load i64, i64* %"i", !dbg !170
  %".14" = icmp slt i64 %".13", %".10" , !dbg !170
  br i1 %".14", label %"for.body", label %"for.end", !dbg !170
for.body:
  %".16" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !170
  %".17" = load i8*, i8** %"bytes", !dbg !170
  %".18" = load i64, i64* %"i", !dbg !170
  %".19" = getelementptr i8, i8* %".17", i64 %".18" , !dbg !170
  %".20" = load i8, i8* %".19", !dbg !170
  %".21" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %".16", i8 %".20"), !dbg !170
  %".22" = sext i32 %".21" to i64 , !dbg !170
  %".23" = icmp ne i64 %".22", 0 , !dbg !170
  br i1 %".23", label %"if.then", label %"if.end", !dbg !170
for.incr:
  %".29" = load i64, i64* %"i", !dbg !171
  %".30" = add i64 %".29", 1, !dbg !171
  store i64 %".30", i64* %"i", !dbg !171
  br label %"for.cond", !dbg !171
for.end:
  %".33" = trunc i64 0 to i32 , !dbg !172
  ret i32 %".33", !dbg !172
if.then:
  %".25" = sub i64 0, 1, !dbg !171
  %".26" = trunc i64 %".25" to i32 , !dbg !171
  ret i32 %".26", !dbg !171
if.end:
  br label %"for.incr", !dbg !171
}

define i32 @"string_clear"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !33
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !173, metadata !7), !dbg !174
  %".4" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !175
  %".5" = call i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"* %".4"), !dbg !175
  ret i32 %".5", !dbg !175
}

define i8 @"string_pop"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !34
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !176, metadata !7), !dbg !177
  %".4" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !178
  %".5" = call i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"* %".4"), !dbg !178
  ret i8 %".5", !dbg !178
}

define i32 @"string_eq"(%"struct.ritz_module_1.String"* %"a.arg", %"struct.ritz_module_1.String"* %"b.arg") !dbg !35
{
entry:
  %"i.addr" = alloca i64, !dbg !186
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"a.arg", metadata !179, metadata !7), !dbg !180
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"b.arg", metadata !181, metadata !7), !dbg !180
  %".6" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"a.arg", i32 0, i32 0 , !dbg !182
  %".7" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".6", !dbg !182
  %".8" = extractvalue %"struct.ritz_module_1.Vec$u8" %".7", 1 , !dbg !182
  %".9" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"b.arg", i32 0, i32 0 , !dbg !183
  %".10" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".9", !dbg !183
  %".11" = extractvalue %"struct.ritz_module_1.Vec$u8" %".10", 1 , !dbg !183
  %".12" = icmp ne i64 %".8", %".11" , !dbg !184
  br i1 %".12", label %"if.then", label %"if.end", !dbg !184
if.then:
  %".14" = trunc i64 0 to i32 , !dbg !185
  ret i32 %".14", !dbg !185
if.end:
  store i64 0, i64* %"i.addr", !dbg !186
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !187, metadata !7), !dbg !188
  br label %"while.cond", !dbg !189
while.cond:
  %".19" = load i64, i64* %"i.addr", !dbg !189
  %".20" = icmp slt i64 %".19", %".8" , !dbg !189
  br i1 %".20", label %"while.body", label %"while.end", !dbg !189
while.body:
  %".22" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"a.arg", i32 0, i32 0 , !dbg !190
  %".23" = load i64, i64* %"i.addr", !dbg !190
  %".24" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".22", i64 %".23"), !dbg !190
  %".25" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"b.arg", i32 0, i32 0 , !dbg !190
  %".26" = load i64, i64* %"i.addr", !dbg !190
  %".27" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".25", i64 %".26"), !dbg !190
  %".28" = icmp ne i8 %".24", %".27" , !dbg !190
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !190
while.end:
  %".36" = trunc i64 1 to i32 , !dbg !193
  ret i32 %".36", !dbg !193
if.then.1:
  %".30" = trunc i64 0 to i32 , !dbg !191
  ret i32 %".30", !dbg !191
if.end.1:
  %".32" = load i64, i64* %"i.addr", !dbg !192
  %".33" = add i64 %".32", 1, !dbg !192
  store i64 %".33", i64* %"i.addr", !dbg !192
  br label %"while.cond", !dbg !192
}

define i64 @"string_hash"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !36
{
entry:
  %"h.addr" = alloca i64, !dbg !196
  %"i" = alloca i64, !dbg !200
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !194, metadata !7), !dbg !195
  %".4" = call i64 @"fnv1a_init"(), !dbg !196
  store i64 %".4", i64* %"h.addr", !dbg !196
  call void @"llvm.dbg.declare"(metadata i64* %"h.addr", metadata !197, metadata !7), !dbg !198
  %".7" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !199
  %".8" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", !dbg !199
  %".9" = extractvalue %"struct.ritz_module_1.Vec$u8" %".8", 1 , !dbg !199
  store i64 0, i64* %"i", !dbg !200
  br label %"for.cond", !dbg !200
for.cond:
  %".12" = load i64, i64* %"i", !dbg !200
  %".13" = icmp slt i64 %".12", %".9" , !dbg !200
  br i1 %".13", label %"for.body", label %"for.end", !dbg !200
for.body:
  %".15" = load i64, i64* %"h.addr", !dbg !201
  %".16" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !201
  %".17" = load i64, i64* %"i", !dbg !201
  %".18" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".16", i64 %".17"), !dbg !201
  %".19" = call i64 @"fnv1a_byte"(i64 %".15", i8 %".18"), !dbg !201
  store i64 %".19", i64* %"h.addr", !dbg !201
  br label %"for.incr", !dbg !201
for.incr:
  %".22" = load i64, i64* %"i", !dbg !201
  %".23" = add i64 %".22", 1, !dbg !201
  store i64 %".23", i64* %"i", !dbg !201
  br label %"for.cond", !dbg !201
for.end:
  %".26" = load i64, i64* %"h.addr", !dbg !202
  ret i64 %".26", !dbg !202
}

define i32 @"string_eq_cstr"(%"struct.ritz_module_1.String"* %"s.arg", i8* %"cstr.arg") !dbg !37
{
entry:
  %"i.addr" = alloca i64, !dbg !207
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !203, metadata !7), !dbg !204
  %"cstr" = alloca i8*
  store i8* %"cstr.arg", i8** %"cstr"
  call void @"llvm.dbg.declare"(metadata i8** %"cstr", metadata !205, metadata !7), !dbg !204
  %".7" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !206
  %".8" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", !dbg !206
  %".9" = extractvalue %"struct.ritz_module_1.Vec$u8" %".8", 1 , !dbg !206
  store i64 0, i64* %"i.addr", !dbg !207
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !208, metadata !7), !dbg !209
  br label %"while.cond", !dbg !210
while.cond:
  %".13" = load i64, i64* %"i.addr", !dbg !210
  %".14" = icmp slt i64 %".13", %".9" , !dbg !210
  br i1 %".14", label %"while.body", label %"while.end", !dbg !210
while.body:
  %".16" = load i8*, i8** %"cstr", !dbg !211
  %".17" = load i64, i64* %"i.addr", !dbg !211
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !211
  %".19" = load i8, i8* %".18", !dbg !211
  %".20" = zext i8 %".19" to i64 , !dbg !211
  %".21" = icmp eq i64 %".20", 0 , !dbg !211
  br i1 %".21", label %"if.then", label %"if.end", !dbg !211
while.end:
  %".40" = load i8*, i8** %"cstr", !dbg !216
  %".41" = getelementptr i8, i8* %".40", i64 %".9" , !dbg !216
  %".42" = load i8, i8* %".41", !dbg !216
  %".43" = zext i8 %".42" to i64 , !dbg !216
  %".44" = icmp ne i64 %".43", 0 , !dbg !216
  br i1 %".44", label %"if.then.2", label %"if.end.2", !dbg !216
if.then:
  %".23" = trunc i64 0 to i32 , !dbg !212
  ret i32 %".23", !dbg !212
if.end:
  %".25" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !213
  %".26" = load i64, i64* %"i.addr", !dbg !213
  %".27" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".25", i64 %".26"), !dbg !213
  %".28" = load i8*, i8** %"cstr", !dbg !213
  %".29" = load i64, i64* %"i.addr", !dbg !213
  %".30" = getelementptr i8, i8* %".28", i64 %".29" , !dbg !213
  %".31" = load i8, i8* %".30", !dbg !213
  %".32" = icmp ne i8 %".27", %".31" , !dbg !213
  br i1 %".32", label %"if.then.1", label %"if.end.1", !dbg !213
if.then.1:
  %".34" = trunc i64 0 to i32 , !dbg !214
  ret i32 %".34", !dbg !214
if.end.1:
  %".36" = load i64, i64* %"i.addr", !dbg !215
  %".37" = add i64 %".36", 1, !dbg !215
  store i64 %".37", i64* %"i.addr", !dbg !215
  br label %"while.cond", !dbg !215
if.then.2:
  %".46" = trunc i64 0 to i32 , !dbg !217
  ret i32 %".46", !dbg !217
if.end.2:
  %".48" = trunc i64 1 to i32 , !dbg !218
  ret i32 %".48", !dbg !218
}

define %"struct.ritz_module_1.String" @"string_clone"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !38
{
entry:
  %"clone.addr" = alloca %"struct.ritz_module_1.String", !dbg !222
  %"i" = alloca i64, !dbg !225
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !219, metadata !7), !dbg !220
  %".4" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !221
  %".5" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", !dbg !221
  %".6" = extractvalue %"struct.ritz_module_1.Vec$u8" %".5", 1 , !dbg !221
  %".7" = call %"struct.ritz_module_1.String" @"string_with_cap"(i64 %".6"), !dbg !222
  store %"struct.ritz_module_1.String" %".7", %"struct.ritz_module_1.String"* %"clone.addr", !dbg !222
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"clone.addr", metadata !223, metadata !7), !dbg !224
  store i64 0, i64* %"i", !dbg !225
  br label %"for.cond", !dbg !225
for.cond:
  %".12" = load i64, i64* %"i", !dbg !225
  %".13" = icmp slt i64 %".12", %".6" , !dbg !225
  br i1 %".13", label %"for.body", label %"for.end", !dbg !225
for.body:
  %".15" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"clone.addr", i32 0, i32 0 , !dbg !225
  %".16" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !225
  %".17" = load i64, i64* %"i", !dbg !225
  %".18" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".16", i64 %".17"), !dbg !225
  %".19" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %".15", i8 %".18"), !dbg !225
  br label %"for.incr", !dbg !225
for.incr:
  %".21" = load i64, i64* %"i", !dbg !225
  %".22" = add i64 %".21", 1, !dbg !225
  store i64 %".22", i64* %"i", !dbg !225
  br label %"for.cond", !dbg !225
for.end:
  %".25" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"clone.addr", !dbg !226
  ret %"struct.ritz_module_1.String" %".25", !dbg !226
}

define i32 @"string_starts_with_string"(%"struct.ritz_module_1.String"* %"s.arg", %"struct.ritz_module_1.String"* %"prefix.arg") !dbg !39
{
entry:
  %"i.addr" = alloca i64, !dbg !234
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !227, metadata !7), !dbg !228
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"prefix.arg", metadata !229, metadata !7), !dbg !228
  %".6" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !230
  %".7" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".6", !dbg !230
  %".8" = extractvalue %"struct.ritz_module_1.Vec$u8" %".7", 1 , !dbg !230
  %".9" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"prefix.arg", i32 0, i32 0 , !dbg !231
  %".10" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".9", !dbg !231
  %".11" = extractvalue %"struct.ritz_module_1.Vec$u8" %".10", 1 , !dbg !231
  %".12" = icmp sgt i64 %".11", %".8" , !dbg !232
  br i1 %".12", label %"if.then", label %"if.end", !dbg !232
if.then:
  %".14" = trunc i64 0 to i32 , !dbg !233
  ret i32 %".14", !dbg !233
if.end:
  store i64 0, i64* %"i.addr", !dbg !234
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !235, metadata !7), !dbg !236
  br label %"while.cond", !dbg !237
while.cond:
  %".19" = load i64, i64* %"i.addr", !dbg !237
  %".20" = icmp slt i64 %".19", %".11" , !dbg !237
  br i1 %".20", label %"while.body", label %"while.end", !dbg !237
while.body:
  %".22" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !238
  %".23" = load i64, i64* %"i.addr", !dbg !238
  %".24" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".22", i64 %".23"), !dbg !238
  %".25" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"prefix.arg", i32 0, i32 0 , !dbg !238
  %".26" = load i64, i64* %"i.addr", !dbg !238
  %".27" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".25", i64 %".26"), !dbg !238
  %".28" = icmp ne i8 %".24", %".27" , !dbg !238
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !238
while.end:
  %".36" = trunc i64 1 to i32 , !dbg !241
  ret i32 %".36", !dbg !241
if.then.1:
  %".30" = trunc i64 0 to i32 , !dbg !239
  ret i32 %".30", !dbg !239
if.end.1:
  %".32" = load i64, i64* %"i.addr", !dbg !240
  %".33" = add i64 %".32", 1, !dbg !240
  store i64 %".33", i64* %"i.addr", !dbg !240
  br label %"while.cond", !dbg !240
}

define i32 @"string_ends_with_string"(%"struct.ritz_module_1.String"* %"s.arg", %"struct.ritz_module_1.String"* %"suffix.arg") !dbg !40
{
entry:
  %"i.addr" = alloca i64, !dbg !250
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !242, metadata !7), !dbg !243
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"suffix.arg", metadata !244, metadata !7), !dbg !243
  %".6" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !245
  %".7" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".6", !dbg !245
  %".8" = extractvalue %"struct.ritz_module_1.Vec$u8" %".7", 1 , !dbg !245
  %".9" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"suffix.arg", i32 0, i32 0 , !dbg !246
  %".10" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".9", !dbg !246
  %".11" = extractvalue %"struct.ritz_module_1.Vec$u8" %".10", 1 , !dbg !246
  %".12" = icmp sgt i64 %".11", %".8" , !dbg !247
  br i1 %".12", label %"if.then", label %"if.end", !dbg !247
if.then:
  %".14" = trunc i64 0 to i32 , !dbg !248
  ret i32 %".14", !dbg !248
if.end:
  %".16" = sub i64 %".8", %".11", !dbg !249
  store i64 0, i64* %"i.addr", !dbg !250
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !251, metadata !7), !dbg !252
  br label %"while.cond", !dbg !253
while.cond:
  %".20" = load i64, i64* %"i.addr", !dbg !253
  %".21" = icmp slt i64 %".20", %".11" , !dbg !253
  br i1 %".21", label %"while.body", label %"while.end", !dbg !253
while.body:
  %".23" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !254
  %".24" = load i64, i64* %"i.addr", !dbg !254
  %".25" = add i64 %".16", %".24", !dbg !254
  %".26" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".23", i64 %".25"), !dbg !254
  %".27" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"suffix.arg", i32 0, i32 0 , !dbg !254
  %".28" = load i64, i64* %"i.addr", !dbg !254
  %".29" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".27", i64 %".28"), !dbg !254
  %".30" = icmp ne i8 %".26", %".29" , !dbg !254
  br i1 %".30", label %"if.then.1", label %"if.end.1", !dbg !254
while.end:
  %".38" = trunc i64 1 to i32 , !dbg !257
  ret i32 %".38", !dbg !257
if.then.1:
  %".32" = trunc i64 0 to i32 , !dbg !255
  ret i32 %".32", !dbg !255
if.end.1:
  %".34" = load i64, i64* %"i.addr", !dbg !256
  %".35" = add i64 %".34", 1, !dbg !256
  store i64 %".35", i64* %"i.addr", !dbg !256
  br label %"while.cond", !dbg !256
}

define i32 @"string_contains_string"(%"struct.ritz_module_1.String"* %"s.arg", %"struct.ritz_module_1.String"* %"needle.arg") !dbg !41
{
entry:
  %"i" = alloca i64, !dbg !268
  %"j.addr" = alloca i64, !dbg !269
  %"found.addr" = alloca i32, !dbg !272
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !258, metadata !7), !dbg !259
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"needle.arg", metadata !260, metadata !7), !dbg !259
  %".6" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !261
  %".7" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".6", !dbg !261
  %".8" = extractvalue %"struct.ritz_module_1.Vec$u8" %".7", 1 , !dbg !261
  %".9" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"needle.arg", i32 0, i32 0 , !dbg !262
  %".10" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".9", !dbg !262
  %".11" = extractvalue %"struct.ritz_module_1.Vec$u8" %".10", 1 , !dbg !262
  %".12" = icmp eq i64 %".11", 0 , !dbg !263
  br i1 %".12", label %"if.then", label %"if.end", !dbg !263
if.then:
  %".14" = trunc i64 1 to i32 , !dbg !264
  ret i32 %".14", !dbg !264
if.end:
  %".16" = icmp sgt i64 %".11", %".8" , !dbg !265
  br i1 %".16", label %"if.then.1", label %"if.end.1", !dbg !265
if.then.1:
  %".18" = trunc i64 0 to i32 , !dbg !266
  ret i32 %".18", !dbg !266
if.end.1:
  %".20" = sub i64 %".8", %".11", !dbg !267
  %".21" = add i64 %".20", 1, !dbg !267
  store i64 0, i64* %"i", !dbg !268
  br label %"for.cond", !dbg !268
for.cond:
  %".24" = load i64, i64* %"i", !dbg !268
  %".25" = icmp slt i64 %".24", %".21" , !dbg !268
  br i1 %".25", label %"for.body", label %"for.end", !dbg !268
for.body:
  store i64 0, i64* %"j.addr", !dbg !269
  call void @"llvm.dbg.declare"(metadata i64* %"j.addr", metadata !270, metadata !7), !dbg !271
  %".29" = trunc i64 1 to i32 , !dbg !272
  store i32 %".29", i32* %"found.addr", !dbg !272
  call void @"llvm.dbg.declare"(metadata i32* %"found.addr", metadata !273, metadata !7), !dbg !274
  br label %"while.cond", !dbg !275
for.incr:
  %".61" = load i64, i64* %"i", !dbg !280
  %".62" = add i64 %".61", 1, !dbg !280
  store i64 %".62", i64* %"i", !dbg !280
  br label %"for.cond", !dbg !280
for.end:
  %".65" = trunc i64 0 to i32 , !dbg !281
  ret i32 %".65", !dbg !281
while.cond:
  %".33" = load i64, i64* %"j.addr", !dbg !275
  %".34" = icmp slt i64 %".33", %".11" , !dbg !275
  br i1 %".34", label %"while.body", label %"while.end", !dbg !275
while.body:
  %".36" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !276
  %".37" = load i64, i64* %"i", !dbg !276
  %".38" = load i64, i64* %"j.addr", !dbg !276
  %".39" = add i64 %".37", %".38", !dbg !276
  %".40" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".36", i64 %".39"), !dbg !276
  %".41" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"needle.arg", i32 0, i32 0 , !dbg !276
  %".42" = load i64, i64* %"j.addr", !dbg !276
  %".43" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".41", i64 %".42"), !dbg !276
  %".44" = icmp ne i8 %".40", %".43" , !dbg !276
  br i1 %".44", label %"if.then.2", label %"if.end.2", !dbg !276
while.end:
  %".54" = load i32, i32* %"found.addr", !dbg !279
  %".55" = sext i32 %".54" to i64 , !dbg !279
  %".56" = icmp eq i64 %".55", 1 , !dbg !279
  br i1 %".56", label %"if.then.3", label %"if.end.3", !dbg !279
if.then.2:
  %".46" = trunc i64 0 to i32 , !dbg !277
  store i32 %".46", i32* %"found.addr", !dbg !277
  store i64 %".11", i64* %"j.addr", !dbg !278
  br label %"if.end.2", !dbg !278
if.end.2:
  %".50" = load i64, i64* %"j.addr", !dbg !279
  %".51" = add i64 %".50", 1, !dbg !279
  store i64 %".51", i64* %"j.addr", !dbg !279
  br label %"while.cond", !dbg !279
if.then.3:
  %".58" = trunc i64 1 to i32 , !dbg !280
  ret i32 %".58", !dbg !280
if.end.3:
  br label %"for.incr", !dbg !280
}

define i64 @"string_find"(%"struct.ritz_module_1.String"* %"s.arg", %"struct.ritz_module_1.String"* %"needle.arg") !dbg !42
{
entry:
  %"i" = alloca i64, !dbg !292
  %"j.addr" = alloca i64, !dbg !293
  %"found.addr" = alloca i32, !dbg !296
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !282, metadata !7), !dbg !283
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"needle.arg", metadata !284, metadata !7), !dbg !283
  %".6" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !285
  %".7" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".6", !dbg !285
  %".8" = extractvalue %"struct.ritz_module_1.Vec$u8" %".7", 1 , !dbg !285
  %".9" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"needle.arg", i32 0, i32 0 , !dbg !286
  %".10" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".9", !dbg !286
  %".11" = extractvalue %"struct.ritz_module_1.Vec$u8" %".10", 1 , !dbg !286
  %".12" = icmp eq i64 %".11", 0 , !dbg !287
  br i1 %".12", label %"if.then", label %"if.end", !dbg !287
if.then:
  ret i64 0, !dbg !288
if.end:
  %".15" = icmp sgt i64 %".11", %".8" , !dbg !289
  br i1 %".15", label %"if.then.1", label %"if.end.1", !dbg !289
if.then.1:
  %".17" = sub i64 0, 1, !dbg !290
  ret i64 %".17", !dbg !290
if.end.1:
  %".19" = sub i64 %".8", %".11", !dbg !291
  %".20" = add i64 %".19", 1, !dbg !291
  store i64 0, i64* %"i", !dbg !292
  br label %"for.cond", !dbg !292
for.cond:
  %".23" = load i64, i64* %"i", !dbg !292
  %".24" = icmp slt i64 %".23", %".20" , !dbg !292
  br i1 %".24", label %"for.body", label %"for.end", !dbg !292
for.body:
  store i64 0, i64* %"j.addr", !dbg !293
  call void @"llvm.dbg.declare"(metadata i64* %"j.addr", metadata !294, metadata !7), !dbg !295
  %".28" = trunc i64 1 to i32 , !dbg !296
  store i32 %".28", i32* %"found.addr", !dbg !296
  call void @"llvm.dbg.declare"(metadata i32* %"found.addr", metadata !297, metadata !7), !dbg !298
  br label %"while.cond", !dbg !299
for.incr:
  %".60" = load i64, i64* %"i", !dbg !304
  %".61" = add i64 %".60", 1, !dbg !304
  store i64 %".61", i64* %"i", !dbg !304
  br label %"for.cond", !dbg !304
for.end:
  %".64" = sub i64 0, 1, !dbg !305
  ret i64 %".64", !dbg !305
while.cond:
  %".32" = load i64, i64* %"j.addr", !dbg !299
  %".33" = icmp slt i64 %".32", %".11" , !dbg !299
  br i1 %".33", label %"while.body", label %"while.end", !dbg !299
while.body:
  %".35" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !300
  %".36" = load i64, i64* %"i", !dbg !300
  %".37" = load i64, i64* %"j.addr", !dbg !300
  %".38" = add i64 %".36", %".37", !dbg !300
  %".39" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".35", i64 %".38"), !dbg !300
  %".40" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"needle.arg", i32 0, i32 0 , !dbg !300
  %".41" = load i64, i64* %"j.addr", !dbg !300
  %".42" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".40", i64 %".41"), !dbg !300
  %".43" = icmp ne i8 %".39", %".42" , !dbg !300
  br i1 %".43", label %"if.then.2", label %"if.end.2", !dbg !300
while.end:
  %".53" = load i32, i32* %"found.addr", !dbg !303
  %".54" = sext i32 %".53" to i64 , !dbg !303
  %".55" = icmp eq i64 %".54", 1 , !dbg !303
  br i1 %".55", label %"if.then.3", label %"if.end.3", !dbg !303
if.then.2:
  %".45" = trunc i64 0 to i32 , !dbg !301
  store i32 %".45", i32* %"found.addr", !dbg !301
  store i64 %".11", i64* %"j.addr", !dbg !302
  br label %"if.end.2", !dbg !302
if.end.2:
  %".49" = load i64, i64* %"j.addr", !dbg !303
  %".50" = add i64 %".49", 1, !dbg !303
  store i64 %".50", i64* %"j.addr", !dbg !303
  br label %"while.cond", !dbg !303
if.then.3:
  %".57" = load i64, i64* %"i", !dbg !304
  ret i64 %".57", !dbg !304
if.end.3:
  br label %"for.incr", !dbg !304
}

define %"struct.ritz_module_1.String" @"string_slice"(%"struct.ritz_module_1.String"* %"s.arg", i64 %"start.arg", i64 %"end.arg") !dbg !43
{
entry:
  %"result.addr" = alloca %"struct.ritz_module_1.String", !dbg !311
  %"st.addr" = alloca i64, !dbg !314
  %"en.addr" = alloca i64, !dbg !317
  %"i" = alloca i64, !dbg !326
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !306, metadata !7), !dbg !307
  %"start" = alloca i64
  store i64 %"start.arg", i64* %"start"
  call void @"llvm.dbg.declare"(metadata i64* %"start", metadata !308, metadata !7), !dbg !307
  %"end" = alloca i64
  store i64 %"end.arg", i64* %"end"
  call void @"llvm.dbg.declare"(metadata i64* %"end", metadata !309, metadata !7), !dbg !307
  %".10" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !310
  %".11" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".10", !dbg !310
  %".12" = extractvalue %"struct.ritz_module_1.Vec$u8" %".11", 1 , !dbg !310
  %".13" = call %"struct.ritz_module_1.String" @"string_new"(), !dbg !311
  store %"struct.ritz_module_1.String" %".13", %"struct.ritz_module_1.String"* %"result.addr", !dbg !311
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"result.addr", metadata !312, metadata !7), !dbg !313
  %".16" = load i64, i64* %"start", !dbg !314
  store i64 %".16", i64* %"st.addr", !dbg !314
  call void @"llvm.dbg.declare"(metadata i64* %"st.addr", metadata !315, metadata !7), !dbg !316
  %".19" = load i64, i64* %"end", !dbg !317
  store i64 %".19", i64* %"en.addr", !dbg !317
  call void @"llvm.dbg.declare"(metadata i64* %"en.addr", metadata !318, metadata !7), !dbg !319
  %".22" = load i64, i64* %"st.addr", !dbg !320
  %".23" = icmp slt i64 %".22", 0 , !dbg !320
  br i1 %".23", label %"if.then", label %"if.end", !dbg !320
if.then:
  store i64 0, i64* %"st.addr", !dbg !321
  br label %"if.end", !dbg !321
if.end:
  %".27" = load i64, i64* %"en.addr", !dbg !322
  %".28" = icmp sgt i64 %".27", %".12" , !dbg !322
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !322
if.then.1:
  store i64 %".12", i64* %"en.addr", !dbg !323
  br label %"if.end.1", !dbg !323
if.end.1:
  %".32" = load i64, i64* %"st.addr", !dbg !324
  %".33" = load i64, i64* %"en.addr", !dbg !324
  %".34" = icmp sge i64 %".32", %".33" , !dbg !324
  br i1 %".34", label %"if.then.2", label %"if.end.2", !dbg !324
if.then.2:
  %".36" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"result.addr", !dbg !325
  ret %"struct.ritz_module_1.String" %".36", !dbg !325
if.end.2:
  %".38" = load i64, i64* %"st.addr", !dbg !326
  %".39" = load i64, i64* %"en.addr", !dbg !326
  store i64 %".38", i64* %"i", !dbg !326
  br label %"for.cond", !dbg !326
for.cond:
  %".42" = load i64, i64* %"i", !dbg !326
  %".43" = icmp slt i64 %".42", %".39" , !dbg !326
  br i1 %".43", label %"for.body", label %"for.end", !dbg !326
for.body:
  %".45" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !326
  %".46" = load i64, i64* %"i", !dbg !326
  %".47" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".45", i64 %".46"), !dbg !326
  %".48" = call i32 @"string_push"(%"struct.ritz_module_1.String"* %"result.addr", i8 %".47"), !dbg !326
  br label %"for.incr", !dbg !326
for.incr:
  %".50" = load i64, i64* %"i", !dbg !326
  %".51" = add i64 %".50", 1, !dbg !326
  store i64 %".51", i64* %"i", !dbg !326
  br label %"for.cond", !dbg !326
for.end:
  %".54" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"result.addr", !dbg !327
  ret %"struct.ritz_module_1.String" %".54", !dbg !327
}

define i8 @"string_char_at"(%"struct.ritz_module_1.String"* %"s.arg", i64 %"idx.arg") !dbg !44
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !328, metadata !7), !dbg !329
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !330, metadata !7), !dbg !329
  %".7" = load i64, i64* %"idx", !dbg !331
  %".8" = icmp slt i64 %".7", 0 , !dbg !331
  br i1 %".8", label %"or.merge", label %"or.right", !dbg !331
or.right:
  %".10" = load i64, i64* %"idx", !dbg !331
  %".11" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !331
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".11", !dbg !331
  %".13" = extractvalue %"struct.ritz_module_1.Vec$u8" %".12", 1 , !dbg !331
  %".14" = icmp sge i64 %".10", %".13" , !dbg !331
  br label %"or.merge", !dbg !331
or.merge:
  %".16" = phi  i1 [1, %"entry"], [%".14", %"or.right"] , !dbg !331
  br i1 %".16", label %"if.then", label %"if.end", !dbg !331
if.then:
  %".18" = trunc i64 0 to i8 , !dbg !332
  ret i8 %".18", !dbg !332
if.end:
  %".20" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !333
  %".21" = load i64, i64* %"idx", !dbg !333
  %".22" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".20", i64 %".21"), !dbg !333
  ret i8 %".22", !dbg !333
}

define i32 @"string_set_char"(%"struct.ritz_module_1.String"* %"s.arg", i64 %"idx.arg", i8 %"c.arg") !dbg !45
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !334, metadata !7), !dbg !335
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !336, metadata !7), !dbg !335
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !337, metadata !7), !dbg !335
  %".10" = load i64, i64* %"idx", !dbg !338
  %".11" = icmp slt i64 %".10", 0 , !dbg !338
  br i1 %".11", label %"or.merge", label %"or.right", !dbg !338
or.right:
  %".13" = load i64, i64* %"idx", !dbg !338
  %".14" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !338
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".14", !dbg !338
  %".16" = extractvalue %"struct.ritz_module_1.Vec$u8" %".15", 1 , !dbg !338
  %".17" = icmp sge i64 %".13", %".16" , !dbg !338
  br label %"or.merge", !dbg !338
or.merge:
  %".19" = phi  i1 [1, %"entry"], [%".17", %"or.right"] , !dbg !338
  br i1 %".19", label %"if.then", label %"if.end", !dbg !338
if.then:
  %".21" = sub i64 0, 1, !dbg !339
  %".22" = trunc i64 %".21" to i32 , !dbg !339
  ret i32 %".22", !dbg !339
if.end:
  %".24" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !340
  %".25" = load i64, i64* %"idx", !dbg !340
  %".26" = load i8, i8* %"c", !dbg !340
  %".27" = call i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"* %".24", i64 %".25", i8 %".26"), !dbg !340
  %".28" = trunc i64 0 to i32 , !dbg !341
  ret i32 %".28", !dbg !341
}

define i32 @"string_starts_with"(%"struct.ritz_module_1.String"* %"s.arg", i8* %"prefix.arg") !dbg !46
{
entry:
  %"i.addr" = alloca i64, !dbg !345
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !342, metadata !7), !dbg !343
  %"prefix" = alloca i8*
  store i8* %"prefix.arg", i8** %"prefix"
  call void @"llvm.dbg.declare"(metadata i8** %"prefix", metadata !344, metadata !7), !dbg !343
  store i64 0, i64* %"i.addr", !dbg !345
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !346, metadata !7), !dbg !347
  %".9" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !348
  %".10" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".9", !dbg !348
  %".11" = extractvalue %"struct.ritz_module_1.Vec$u8" %".10", 1 , !dbg !348
  br label %"while.cond", !dbg !349
while.cond:
  %".13" = load i8*, i8** %"prefix", !dbg !349
  %".14" = load i64, i64* %"i.addr", !dbg !349
  %".15" = getelementptr i8, i8* %".13", i64 %".14" , !dbg !349
  %".16" = load i8, i8* %".15", !dbg !349
  %".17" = zext i8 %".16" to i64 , !dbg !349
  %".18" = icmp ne i64 %".17", 0 , !dbg !349
  br i1 %".18", label %"while.body", label %"while.end", !dbg !349
while.body:
  %".20" = load i64, i64* %"i.addr", !dbg !350
  %".21" = icmp sge i64 %".20", %".11" , !dbg !350
  br i1 %".21", label %"if.then", label %"if.end", !dbg !350
while.end:
  %".40" = trunc i64 1 to i32 , !dbg !355
  ret i32 %".40", !dbg !355
if.then:
  %".23" = trunc i64 0 to i32 , !dbg !351
  ret i32 %".23", !dbg !351
if.end:
  %".25" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !352
  %".26" = load i64, i64* %"i.addr", !dbg !352
  %".27" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".25", i64 %".26"), !dbg !352
  %".28" = load i8*, i8** %"prefix", !dbg !352
  %".29" = load i64, i64* %"i.addr", !dbg !352
  %".30" = getelementptr i8, i8* %".28", i64 %".29" , !dbg !352
  %".31" = load i8, i8* %".30", !dbg !352
  %".32" = icmp ne i8 %".27", %".31" , !dbg !352
  br i1 %".32", label %"if.then.1", label %"if.end.1", !dbg !352
if.then.1:
  %".34" = trunc i64 0 to i32 , !dbg !353
  ret i32 %".34", !dbg !353
if.end.1:
  %".36" = load i64, i64* %"i.addr", !dbg !354
  %".37" = add i64 %".36", 1, !dbg !354
  store i64 %".37", i64* %"i.addr", !dbg !354
  br label %"while.cond", !dbg !354
}

define i32 @"string_ends_with"(%"struct.ritz_module_1.String"* %"s.arg", i8* %"suffix.arg") !dbg !47
{
entry:
  %"suffix_len.addr" = alloca i64, !dbg !359
  %"i.addr" = alloca i64, !dbg !368
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !356, metadata !7), !dbg !357
  %"suffix" = alloca i8*
  store i8* %"suffix.arg", i8** %"suffix"
  call void @"llvm.dbg.declare"(metadata i8** %"suffix", metadata !358, metadata !7), !dbg !357
  store i64 0, i64* %"suffix_len.addr", !dbg !359
  call void @"llvm.dbg.declare"(metadata i64* %"suffix_len.addr", metadata !360, metadata !7), !dbg !361
  br label %"while.cond", !dbg !362
while.cond:
  %".10" = load i8*, i8** %"suffix", !dbg !362
  %".11" = load i64, i64* %"suffix_len.addr", !dbg !362
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !362
  %".13" = load i8, i8* %".12", !dbg !362
  %".14" = zext i8 %".13" to i64 , !dbg !362
  %".15" = icmp ne i64 %".14", 0 , !dbg !362
  br i1 %".15", label %"while.body", label %"while.end", !dbg !362
while.body:
  %".17" = load i64, i64* %"suffix_len.addr", !dbg !363
  %".18" = add i64 %".17", 1, !dbg !363
  store i64 %".18", i64* %"suffix_len.addr", !dbg !363
  br label %"while.cond", !dbg !363
while.end:
  %".21" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !364
  %".22" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".21", !dbg !364
  %".23" = extractvalue %"struct.ritz_module_1.Vec$u8" %".22", 1 , !dbg !364
  %".24" = load i64, i64* %"suffix_len.addr", !dbg !365
  %".25" = icmp sgt i64 %".24", %".23" , !dbg !365
  br i1 %".25", label %"if.then", label %"if.end", !dbg !365
if.then:
  %".27" = trunc i64 0 to i32 , !dbg !366
  ret i32 %".27", !dbg !366
if.end:
  %".29" = load i64, i64* %"suffix_len.addr", !dbg !367
  %".30" = sub i64 %".23", %".29", !dbg !367
  store i64 0, i64* %"i.addr", !dbg !368
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !369, metadata !7), !dbg !370
  br label %"while.cond.1", !dbg !371
while.cond.1:
  %".34" = load i64, i64* %"i.addr", !dbg !371
  %".35" = load i64, i64* %"suffix_len.addr", !dbg !371
  %".36" = icmp slt i64 %".34", %".35" , !dbg !371
  br i1 %".36", label %"while.body.1", label %"while.end.1", !dbg !371
while.body.1:
  %".38" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !372
  %".39" = load i64, i64* %"i.addr", !dbg !372
  %".40" = add i64 %".30", %".39", !dbg !372
  %".41" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".38", i64 %".40"), !dbg !372
  %".42" = load i8*, i8** %"suffix", !dbg !372
  %".43" = load i64, i64* %"i.addr", !dbg !372
  %".44" = getelementptr i8, i8* %".42", i64 %".43" , !dbg !372
  %".45" = load i8, i8* %".44", !dbg !372
  %".46" = icmp ne i8 %".41", %".45" , !dbg !372
  br i1 %".46", label %"if.then.1", label %"if.end.1", !dbg !372
while.end.1:
  %".54" = trunc i64 1 to i32 , !dbg !375
  ret i32 %".54", !dbg !375
if.then.1:
  %".48" = trunc i64 0 to i32 , !dbg !373
  ret i32 %".48", !dbg !373
if.end.1:
  %".50" = load i64, i64* %"i.addr", !dbg !374
  %".51" = add i64 %".50", 1, !dbg !374
  store i64 %".51", i64* %"i.addr", !dbg !374
  br label %"while.cond.1", !dbg !374
}

define i32 @"string_contains"(%"struct.ritz_module_1.String"* %"s.arg", i8* %"needle.arg") !dbg !48
{
entry:
  %"needle_len.addr" = alloca i64, !dbg !379
  %"i" = alloca i64, !dbg !390
  %"j.addr" = alloca i64, !dbg !391
  %"found.addr" = alloca i32, !dbg !394
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !376, metadata !7), !dbg !377
  %"needle" = alloca i8*
  store i8* %"needle.arg", i8** %"needle"
  call void @"llvm.dbg.declare"(metadata i8** %"needle", metadata !378, metadata !7), !dbg !377
  store i64 0, i64* %"needle_len.addr", !dbg !379
  call void @"llvm.dbg.declare"(metadata i64* %"needle_len.addr", metadata !380, metadata !7), !dbg !381
  br label %"while.cond", !dbg !382
while.cond:
  %".10" = load i8*, i8** %"needle", !dbg !382
  %".11" = load i64, i64* %"needle_len.addr", !dbg !382
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !382
  %".13" = load i8, i8* %".12", !dbg !382
  %".14" = zext i8 %".13" to i64 , !dbg !382
  %".15" = icmp ne i64 %".14", 0 , !dbg !382
  br i1 %".15", label %"while.body", label %"while.end", !dbg !382
while.body:
  %".17" = load i64, i64* %"needle_len.addr", !dbg !383
  %".18" = add i64 %".17", 1, !dbg !383
  store i64 %".18", i64* %"needle_len.addr", !dbg !383
  br label %"while.cond", !dbg !383
while.end:
  %".21" = load i64, i64* %"needle_len.addr", !dbg !384
  %".22" = icmp eq i64 %".21", 0 , !dbg !384
  br i1 %".22", label %"if.then", label %"if.end", !dbg !384
if.then:
  %".24" = trunc i64 1 to i32 , !dbg !385
  ret i32 %".24", !dbg !385
if.end:
  %".26" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !386
  %".27" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".26", !dbg !386
  %".28" = extractvalue %"struct.ritz_module_1.Vec$u8" %".27", 1 , !dbg !386
  %".29" = load i64, i64* %"needle_len.addr", !dbg !387
  %".30" = icmp sgt i64 %".29", %".28" , !dbg !387
  br i1 %".30", label %"if.then.1", label %"if.end.1", !dbg !387
if.then.1:
  %".32" = trunc i64 0 to i32 , !dbg !388
  ret i32 %".32", !dbg !388
if.end.1:
  %".34" = load i64, i64* %"needle_len.addr", !dbg !389
  %".35" = sub i64 %".28", %".34", !dbg !389
  %".36" = add i64 %".35", 1, !dbg !389
  store i64 0, i64* %"i", !dbg !390
  br label %"for.cond", !dbg !390
for.cond:
  %".39" = load i64, i64* %"i", !dbg !390
  %".40" = icmp slt i64 %".39", %".36" , !dbg !390
  br i1 %".40", label %"for.body", label %"for.end", !dbg !390
for.body:
  store i64 0, i64* %"j.addr", !dbg !391
  call void @"llvm.dbg.declare"(metadata i64* %"j.addr", metadata !392, metadata !7), !dbg !393
  %".44" = trunc i64 1 to i32 , !dbg !394
  store i32 %".44", i32* %"found.addr", !dbg !394
  call void @"llvm.dbg.declare"(metadata i32* %"found.addr", metadata !395, metadata !7), !dbg !396
  br label %"while.cond.1", !dbg !397
for.incr:
  %".79" = load i64, i64* %"i", !dbg !402
  %".80" = add i64 %".79", 1, !dbg !402
  store i64 %".80", i64* %"i", !dbg !402
  br label %"for.cond", !dbg !402
for.end:
  %".83" = trunc i64 0 to i32 , !dbg !403
  ret i32 %".83", !dbg !403
while.cond.1:
  %".48" = load i64, i64* %"j.addr", !dbg !397
  %".49" = load i64, i64* %"needle_len.addr", !dbg !397
  %".50" = icmp slt i64 %".48", %".49" , !dbg !397
  br i1 %".50", label %"while.body.1", label %"while.end.1", !dbg !397
while.body.1:
  %".52" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.arg", i32 0, i32 0 , !dbg !398
  %".53" = load i64, i64* %"i", !dbg !398
  %".54" = load i64, i64* %"j.addr", !dbg !398
  %".55" = add i64 %".53", %".54", !dbg !398
  %".56" = call i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %".52", i64 %".55"), !dbg !398
  %".57" = load i8*, i8** %"needle", !dbg !398
  %".58" = load i64, i64* %"j.addr", !dbg !398
  %".59" = getelementptr i8, i8* %".57", i64 %".58" , !dbg !398
  %".60" = load i8, i8* %".59", !dbg !398
  %".61" = icmp ne i8 %".56", %".60" , !dbg !398
  br i1 %".61", label %"if.then.2", label %"if.end.2", !dbg !398
while.end.1:
  %".72" = load i32, i32* %"found.addr", !dbg !401
  %".73" = sext i32 %".72" to i64 , !dbg !401
  %".74" = icmp eq i64 %".73", 1 , !dbg !401
  br i1 %".74", label %"if.then.3", label %"if.end.3", !dbg !401
if.then.2:
  %".63" = trunc i64 0 to i32 , !dbg !399
  store i32 %".63", i32* %"found.addr", !dbg !399
  %".65" = load i64, i64* %"needle_len.addr", !dbg !400
  store i64 %".65", i64* %"j.addr", !dbg !400
  br label %"if.end.2", !dbg !400
if.end.2:
  %".68" = load i64, i64* %"j.addr", !dbg !401
  %".69" = add i64 %".68", 1, !dbg !401
  store i64 %".69", i64* %"j.addr", !dbg !401
  br label %"while.cond.1", !dbg !401
if.then.3:
  %".76" = trunc i64 1 to i32 , !dbg !402
  ret i32 %".76", !dbg !402
if.end.3:
  br label %"for.incr", !dbg !402
}

define %"struct.ritz_module_1.String" @"string_from_i64"(i64 %"n.arg") !dbg !49
{
entry:
  %"n" = alloca i64
  %"s.addr" = alloca %"struct.ritz_module_1.String", !dbg !406
  %"val.addr" = alloca i64, !dbg !412
  %"is_neg.addr" = alloca i32, !dbg !415
  %"buf.addr" = alloca [20 x i8], !dbg !421
  %"len.addr" = alloca i64, !dbg !427
  %"i.addr" = alloca i64, !dbg !435
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !404, metadata !7), !dbg !405
  %".5" = call %"struct.ritz_module_1.String" @"string_new"(), !dbg !406
  store %"struct.ritz_module_1.String" %".5", %"struct.ritz_module_1.String"* %"s.addr", !dbg !406
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.addr", metadata !407, metadata !7), !dbg !408
  %".8" = load i64, i64* %"n", !dbg !409
  %".9" = icmp eq i64 %".8", 0 , !dbg !409
  br i1 %".9", label %"if.then", label %"if.end", !dbg !409
if.then:
  %".11" = trunc i64 48 to i8 , !dbg !410
  %".12" = call i32 @"string_push"(%"struct.ritz_module_1.String"* %"s.addr", i8 %".11"), !dbg !410
  %".13" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !411
  ret %"struct.ritz_module_1.String" %".13", !dbg !411
if.end:
  %".15" = load i64, i64* %"n", !dbg !412
  store i64 %".15", i64* %"val.addr", !dbg !412
  call void @"llvm.dbg.declare"(metadata i64* %"val.addr", metadata !413, metadata !7), !dbg !414
  %".18" = trunc i64 0 to i32 , !dbg !415
  store i32 %".18", i32* %"is_neg.addr", !dbg !415
  call void @"llvm.dbg.declare"(metadata i32* %"is_neg.addr", metadata !416, metadata !7), !dbg !417
  %".21" = load i64, i64* %"val.addr", !dbg !418
  %".22" = icmp slt i64 %".21", 0 , !dbg !418
  br i1 %".22", label %"if.then.1", label %"if.end.1", !dbg !418
if.then.1:
  %".24" = trunc i64 1 to i32 , !dbg !419
  store i32 %".24", i32* %"is_neg.addr", !dbg !419
  %".26" = load i64, i64* %"val.addr", !dbg !420
  %".27" = sub i64 0, %".26", !dbg !420
  store i64 %".27", i64* %"val.addr", !dbg !420
  br label %"if.end.1", !dbg !420
if.end.1:
  call void @"llvm.dbg.declare"(metadata [20 x i8]* %"buf.addr", metadata !425, metadata !7), !dbg !426
  store i64 0, i64* %"len.addr", !dbg !427
  call void @"llvm.dbg.declare"(metadata i64* %"len.addr", metadata !428, metadata !7), !dbg !429
  br label %"while.cond", !dbg !430
while.cond:
  %".34" = load i64, i64* %"val.addr", !dbg !430
  %".35" = icmp sgt i64 %".34", 0 , !dbg !430
  br i1 %".35", label %"while.body", label %"while.end", !dbg !430
while.body:
  %".37" = load i64, i64* %"val.addr", !dbg !431
  %".38" = srem i64 %".37", 10, !dbg !431
  %".39" = zext i8 48 to i64 , !dbg !431
  %".40" = add i64 %".38", %".39", !dbg !431
  %".41" = trunc i64 %".40" to i8 , !dbg !431
  %".42" = load i64, i64* %"len.addr", !dbg !431
  %".43" = getelementptr [20 x i8], [20 x i8]* %"buf.addr", i32 0, i64 %".42" , !dbg !431
  store i8 %".41", i8* %".43", !dbg !431
  %".45" = load i64, i64* %"val.addr", !dbg !432
  %".46" = sdiv i64 %".45", 10, !dbg !432
  store i64 %".46", i64* %"val.addr", !dbg !432
  %".48" = load i64, i64* %"len.addr", !dbg !433
  %".49" = add i64 %".48", 1, !dbg !433
  store i64 %".49", i64* %"len.addr", !dbg !433
  br label %"while.cond", !dbg !433
while.end:
  %".52" = load i32, i32* %"is_neg.addr", !dbg !434
  %".53" = sext i32 %".52" to i64 , !dbg !434
  %".54" = icmp eq i64 %".53", 1 , !dbg !434
  br i1 %".54", label %"if.then.2", label %"if.end.2", !dbg !434
if.then.2:
  %".56" = trunc i64 45 to i8 , !dbg !434
  %".57" = call i32 @"string_push"(%"struct.ritz_module_1.String"* %"s.addr", i8 %".56"), !dbg !434
  br label %"if.end.2", !dbg !434
if.end.2:
  %".59" = load i64, i64* %"len.addr", !dbg !435
  %".60" = sub i64 %".59", 1, !dbg !435
  store i64 %".60", i64* %"i.addr", !dbg !435
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !436, metadata !7), !dbg !437
  br label %"while.cond.1", !dbg !438
while.cond.1:
  %".64" = load i64, i64* %"i.addr", !dbg !438
  %".65" = icmp sge i64 %".64", 0 , !dbg !438
  br i1 %".65", label %"while.body.1", label %"while.end.1", !dbg !438
while.body.1:
  %".67" = load i64, i64* %"i.addr", !dbg !439
  %".68" = getelementptr [20 x i8], [20 x i8]* %"buf.addr", i32 0, i64 %".67" , !dbg !439
  %".69" = load i8, i8* %".68", !dbg !439
  %".70" = call i32 @"string_push"(%"struct.ritz_module_1.String"* %"s.addr", i8 %".69"), !dbg !439
  %".71" = load i64, i64* %"i.addr", !dbg !440
  %".72" = sub i64 %".71", 1, !dbg !440
  store i64 %".72", i64* %"i.addr", !dbg !440
  br label %"while.cond.1", !dbg !440
while.end.1:
  %".75" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !441
  ret %"struct.ritz_module_1.String" %".75", !dbg !441
}

define i32 @"string_push_i64"(%"struct.ritz_module_1.String"* %"s.arg", i64 %"n.arg") !dbg !50
{
entry:
  %"val.addr" = alloca i64, !dbg !447
  %"is_neg.addr" = alloca i32, !dbg !450
  %"buf.addr" = alloca [20 x i8], !dbg !456
  %"len.addr" = alloca i64, !dbg !459
  %"i.addr" = alloca i64, !dbg !468
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.arg", metadata !442, metadata !7), !dbg !443
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !444, metadata !7), !dbg !443
  %".7" = load i64, i64* %"n", !dbg !445
  %".8" = icmp eq i64 %".7", 0 , !dbg !445
  br i1 %".8", label %"if.then", label %"if.end", !dbg !445
if.then:
  %".10" = trunc i64 48 to i8 , !dbg !446
  %".11" = call i32 @"string_push"(%"struct.ritz_module_1.String"* %"s.arg", i8 %".10"), !dbg !446
  ret i32 %".11", !dbg !446
if.end:
  %".13" = load i64, i64* %"n", !dbg !447
  store i64 %".13", i64* %"val.addr", !dbg !447
  call void @"llvm.dbg.declare"(metadata i64* %"val.addr", metadata !448, metadata !7), !dbg !449
  %".16" = trunc i64 0 to i32 , !dbg !450
  store i32 %".16", i32* %"is_neg.addr", !dbg !450
  call void @"llvm.dbg.declare"(metadata i32* %"is_neg.addr", metadata !451, metadata !7), !dbg !452
  %".19" = load i64, i64* %"val.addr", !dbg !453
  %".20" = icmp slt i64 %".19", 0 , !dbg !453
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !453
if.then.1:
  %".22" = trunc i64 1 to i32 , !dbg !454
  store i32 %".22", i32* %"is_neg.addr", !dbg !454
  %".24" = load i64, i64* %"val.addr", !dbg !455
  %".25" = sub i64 0, %".24", !dbg !455
  store i64 %".25", i64* %"val.addr", !dbg !455
  br label %"if.end.1", !dbg !455
if.end.1:
  call void @"llvm.dbg.declare"(metadata [20 x i8]* %"buf.addr", metadata !457, metadata !7), !dbg !458
  store i64 0, i64* %"len.addr", !dbg !459
  call void @"llvm.dbg.declare"(metadata i64* %"len.addr", metadata !460, metadata !7), !dbg !461
  br label %"while.cond", !dbg !462
while.cond:
  %".32" = load i64, i64* %"val.addr", !dbg !462
  %".33" = icmp sgt i64 %".32", 0 , !dbg !462
  br i1 %".33", label %"while.body", label %"while.end", !dbg !462
while.body:
  %".35" = load i64, i64* %"val.addr", !dbg !463
  %".36" = srem i64 %".35", 10, !dbg !463
  %".37" = zext i8 48 to i64 , !dbg !463
  %".38" = add i64 %".36", %".37", !dbg !463
  %".39" = trunc i64 %".38" to i8 , !dbg !463
  %".40" = load i64, i64* %"len.addr", !dbg !463
  %".41" = getelementptr [20 x i8], [20 x i8]* %"buf.addr", i32 0, i64 %".40" , !dbg !463
  store i8 %".39", i8* %".41", !dbg !463
  %".43" = load i64, i64* %"val.addr", !dbg !464
  %".44" = sdiv i64 %".43", 10, !dbg !464
  store i64 %".44", i64* %"val.addr", !dbg !464
  %".46" = load i64, i64* %"len.addr", !dbg !465
  %".47" = add i64 %".46", 1, !dbg !465
  store i64 %".47", i64* %"len.addr", !dbg !465
  br label %"while.cond", !dbg !465
while.end:
  %".50" = load i32, i32* %"is_neg.addr", !dbg !466
  %".51" = sext i32 %".50" to i64 , !dbg !466
  %".52" = icmp eq i64 %".51", 1 , !dbg !466
  br i1 %".52", label %"if.then.2", label %"if.end.2", !dbg !466
if.then.2:
  %".54" = trunc i64 45 to i8 , !dbg !466
  %".55" = call i32 @"string_push"(%"struct.ritz_module_1.String"* %"s.arg", i8 %".54"), !dbg !466
  %".56" = sext i32 %".55" to i64 , !dbg !466
  %".57" = icmp ne i64 %".56", 0 , !dbg !466
  br i1 %".57", label %"if.then.3", label %"if.end.3", !dbg !466
if.end.2:
  %".63" = load i64, i64* %"len.addr", !dbg !468
  %".64" = sub i64 %".63", 1, !dbg !468
  store i64 %".64", i64* %"i.addr", !dbg !468
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !469, metadata !7), !dbg !470
  br label %"while.cond.1", !dbg !471
if.then.3:
  %".59" = sub i64 0, 1, !dbg !467
  %".60" = trunc i64 %".59" to i32 , !dbg !467
  ret i32 %".60", !dbg !467
if.end.3:
  br label %"if.end.2", !dbg !467
while.cond.1:
  %".68" = load i64, i64* %"i.addr", !dbg !471
  %".69" = icmp sge i64 %".68", 0 , !dbg !471
  br i1 %".69", label %"while.body.1", label %"while.end.1", !dbg !471
while.body.1:
  %".71" = load i64, i64* %"i.addr", !dbg !472
  %".72" = getelementptr [20 x i8], [20 x i8]* %"buf.addr", i32 0, i64 %".71" , !dbg !472
  %".73" = load i8, i8* %".72", !dbg !472
  %".74" = call i32 @"string_push"(%"struct.ritz_module_1.String"* %"s.arg", i8 %".73"), !dbg !472
  %".75" = sext i32 %".74" to i64 , !dbg !472
  %".76" = icmp ne i64 %".75", 0 , !dbg !472
  br i1 %".76", label %"if.then.4", label %"if.end.4", !dbg !472
while.end.1:
  %".85" = trunc i64 0 to i32 , !dbg !475
  ret i32 %".85", !dbg !475
if.then.4:
  %".78" = sub i64 0, 1, !dbg !473
  %".79" = trunc i64 %".78" to i32 , !dbg !473
  ret i32 %".79", !dbg !473
if.end.4:
  %".81" = load i64, i64* %"i.addr", !dbg !474
  %".82" = sub i64 %".81", 1, !dbg !474
  store i64 %".82", i64* %"i.addr", !dbg !474
  br label %"while.cond.1", !dbg !474
}

define %"struct.ritz_module_1.String" @"string_from_hex"(i64 %"n.arg") !dbg !51
{
entry:
  %"n" = alloca i64
  %"s.addr" = alloca %"struct.ritz_module_1.String", !dbg !478
  %"val.addr" = alloca i64, !dbg !485
  %"buf.addr" = alloca [16 x i8], !dbg !488
  %"len.addr" = alloca i64, !dbg !494
  %"i.addr" = alloca i64, !dbg !504
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !476, metadata !7), !dbg !477
  %".5" = call %"struct.ritz_module_1.String" @"string_new"(), !dbg !478
  store %"struct.ritz_module_1.String" %".5", %"struct.ritz_module_1.String"* %"s.addr", !dbg !478
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"* %"s.addr", metadata !479, metadata !7), !dbg !480
  %".8" = load i64, i64* %"n", !dbg !481
  %".9" = icmp eq i64 %".8", 0 , !dbg !481
  br i1 %".9", label %"if.then", label %"if.end", !dbg !481
if.then:
  %".11" = getelementptr [4 x i8], [4 x i8]* @".str.0", i64 0, i64 0 , !dbg !482
  %".12" = call i32 @"string_push_str"(%"struct.ritz_module_1.String"* %"s.addr", i8* %".11"), !dbg !482
  %".13" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !483
  ret %"struct.ritz_module_1.String" %".13", !dbg !483
if.end:
  %".15" = getelementptr [3 x i8], [3 x i8]* @".str.1", i64 0, i64 0 , !dbg !484
  %".16" = call i32 @"string_push_str"(%"struct.ritz_module_1.String"* %"s.addr", i8* %".15"), !dbg !484
  %".17" = load i64, i64* %"n", !dbg !485
  store i64 %".17", i64* %"val.addr", !dbg !485
  call void @"llvm.dbg.declare"(metadata i64* %"val.addr", metadata !486, metadata !7), !dbg !487
  call void @"llvm.dbg.declare"(metadata [16 x i8]* %"buf.addr", metadata !492, metadata !7), !dbg !493
  store i64 0, i64* %"len.addr", !dbg !494
  call void @"llvm.dbg.declare"(metadata i64* %"len.addr", metadata !495, metadata !7), !dbg !496
  br label %"while.cond", !dbg !497
while.cond:
  %".24" = load i64, i64* %"val.addr", !dbg !497
  %".25" = icmp ugt i64 %".24", 0 , !dbg !497
  br i1 %".25", label %"while.body", label %"while.end", !dbg !497
while.body:
  %".27" = load i64, i64* %"val.addr", !dbg !498
  %".28" = urem i64 %".27", 16, !dbg !498
  %".29" = icmp ult i64 %".28", 10 , !dbg !499
  br i1 %".29", label %"if.then.1", label %"if.else", !dbg !499
while.end:
  %".52" = load i64, i64* %"len.addr", !dbg !504
  %".53" = sub i64 %".52", 1, !dbg !504
  store i64 %".53", i64* %"i.addr", !dbg !504
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !505, metadata !7), !dbg !506
  br label %"while.cond.1", !dbg !507
if.then.1:
  %".31" = zext i8 48 to i64 , !dbg !500
  %".32" = add i64 %".28", %".31", !dbg !500
  %".33" = trunc i64 %".32" to i8 , !dbg !500
  %".34" = load i64, i64* %"len.addr", !dbg !500
  %".35" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 %".34" , !dbg !500
  store i8 %".33", i8* %".35", !dbg !500
  br label %"if.end.1", !dbg !501
if.else:
  %".37" = sub i64 %".28", 10, !dbg !501
  %".38" = add i64 %".37", 97, !dbg !501
  %".39" = trunc i64 %".38" to i8 , !dbg !501
  %".40" = load i64, i64* %"len.addr", !dbg !501
  %".41" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 %".40" , !dbg !501
  store i8 %".39", i8* %".41", !dbg !501
  br label %"if.end.1", !dbg !501
if.end.1:
  %".45" = load i64, i64* %"val.addr", !dbg !502
  %".46" = udiv i64 %".45", 16, !dbg !502
  store i64 %".46", i64* %"val.addr", !dbg !502
  %".48" = load i64, i64* %"len.addr", !dbg !503
  %".49" = add i64 %".48", 1, !dbg !503
  store i64 %".49", i64* %"len.addr", !dbg !503
  br label %"while.cond", !dbg !503
while.cond.1:
  %".57" = load i64, i64* %"i.addr", !dbg !507
  %".58" = icmp sge i64 %".57", 0 , !dbg !507
  br i1 %".58", label %"while.body.1", label %"while.end.1", !dbg !507
while.body.1:
  %".60" = load i64, i64* %"i.addr", !dbg !508
  %".61" = getelementptr [16 x i8], [16 x i8]* %"buf.addr", i32 0, i64 %".60" , !dbg !508
  %".62" = load i8, i8* %".61", !dbg !508
  %".63" = call i32 @"string_push"(%"struct.ritz_module_1.String"* %"s.addr", i8 %".62"), !dbg !508
  %".64" = load i64, i64* %"i.addr", !dbg !509
  %".65" = sub i64 %".64", 1, !dbg !509
  store i64 %".65", i64* %"i.addr", !dbg !509
  br label %"while.cond.1", !dbg !509
while.end.1:
  %".68" = load %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %"s.addr", !dbg !510
  ret %"struct.ritz_module_1.String" %".68", !dbg !510
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !52
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !513, metadata !7), !dbg !514
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !515
  store i64 0, i64* %".4", !dbg !515
  ret i32 0, !dbg !515
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !53
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !516, metadata !7), !dbg !517
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !518
  %".5" = load i8*, i8** %".4", !dbg !518
  %".6" = icmp ne i8* %".5", null , !dbg !518
  br i1 %".6", label %"if.then", label %"if.end", !dbg !518
if.then:
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !518
  %".9" = load i8*, i8** %".8", !dbg !518
  %".10" = call i32 @"free"(i8* %".9"), !dbg !518
  br label %"if.end", !dbg !518
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !519
  store i8* null, i8** %".12", !dbg !519
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !520
  store i64 0, i64* %".14", !dbg !520
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !521
  store i64 0, i64* %".16", !dbg !521
  ret i32 0, !dbg !521
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !54
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !522, metadata !7), !dbg !523
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !524
  %".5" = load i64, i64* %".4", !dbg !524
  %".6" = sub i64 %".5", 1, !dbg !524
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !524
  store i64 %".6", i64* %".7", !dbg !524
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !525
  %".10" = load i8*, i8** %".9", !dbg !525
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !525
  %".12" = load i64, i64* %".11", !dbg !525
  %".13" = getelementptr i8, i8* %".10", i64 %".12" , !dbg !525
  %".14" = load i8, i8* %".13", !dbg !525
  ret i8 %".14", !dbg !525
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !55
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !528
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !526, metadata !7), !dbg !527
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !529, metadata !7), !dbg !530
  %".6" = load i64, i64* %"cap", !dbg !531
  %".7" = icmp sle i64 %".6", 0 , !dbg !531
  br i1 %".7", label %"if.then", label %"if.end", !dbg !531
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !532
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !532
  store i8* null, i8** %".10", !dbg !532
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !533
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !533
  store i64 0, i64* %".13", !dbg !533
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !534
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !534
  store i64 0, i64* %".16", !dbg !534
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !535
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !535
if.end:
  %".20" = load i64, i64* %"cap", !dbg !536
  %".21" = mul i64 %".20", 1, !dbg !536
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !537
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !537
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !537
  store i8* %".22", i8** %".24", !dbg !537
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !538
  %".27" = load i8*, i8** %".26", !dbg !538
  %".28" = icmp eq i8* %".27", null , !dbg !538
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !538
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !539
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !539
  store i64 0, i64* %".31", !dbg !539
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !540
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !540
  store i64 0, i64* %".34", !dbg !540
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !541
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !541
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !542
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !542
  store i64 0, i64* %".39", !dbg !542
  %".41" = load i64, i64* %"cap", !dbg !543
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !543
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !543
  store i64 %".41", i64* %".43", !dbg !543
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !544
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !544
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !56
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !550
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !545, metadata !7), !dbg !546
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !547, metadata !7), !dbg !546
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !548
  %".8" = load i64, i64* %".7", !dbg !548
  %".9" = load i64, i64* %"needed", !dbg !548
  %".10" = icmp sge i64 %".8", %".9" , !dbg !548
  br i1 %".10", label %"if.then", label %"if.end", !dbg !548
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !549
  ret i32 %".12", !dbg !549
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !550
  %".15" = load i64, i64* %".14", !dbg !550
  store i64 %".15", i64* %"new_cap.addr", !dbg !550
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !551, metadata !7), !dbg !552
  %".18" = load i64, i64* %"new_cap.addr", !dbg !553
  %".19" = icmp eq i64 %".18", 0 , !dbg !553
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !553
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !554
  br label %"if.end.1", !dbg !554
if.end.1:
  br label %"while.cond", !dbg !555
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !555
  %".25" = load i64, i64* %"needed", !dbg !555
  %".26" = icmp slt i64 %".24", %".25" , !dbg !555
  br i1 %".26", label %"while.body", label %"while.end", !dbg !555
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !556
  %".29" = mul i64 %".28", 2, !dbg !556
  store i64 %".29", i64* %"new_cap.addr", !dbg !556
  br label %"while.cond", !dbg !556
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !557
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !557
  ret i32 %".33", !dbg !557
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !57
{
entry:
  %"i" = alloca i64, !dbg !562
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !558, metadata !7), !dbg !559
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !560, metadata !7), !dbg !559
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !561, metadata !7), !dbg !559
  %".10" = load i64, i64* %"len", !dbg !562
  store i64 0, i64* %"i", !dbg !562
  br label %"for.cond", !dbg !562
for.cond:
  %".13" = load i64, i64* %"i", !dbg !562
  %".14" = icmp slt i64 %".13", %".10" , !dbg !562
  br i1 %".14", label %"for.body", label %"for.end", !dbg !562
for.body:
  %".16" = load i8*, i8** %"data", !dbg !562
  %".17" = load i64, i64* %"i", !dbg !562
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !562
  %".19" = load i8, i8* %".18", !dbg !562
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !562
  %".21" = sext i32 %".20" to i64 , !dbg !562
  %".22" = icmp ne i64 %".21", 0 , !dbg !562
  br i1 %".22", label %"if.then", label %"if.end", !dbg !562
for.incr:
  %".28" = load i64, i64* %"i", !dbg !563
  %".29" = add i64 %".28", 1, !dbg !563
  store i64 %".29", i64* %"i", !dbg !563
  br label %"for.cond", !dbg !563
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !564
  ret i32 %".32", !dbg !564
if.then:
  %".24" = sub i64 0, 1, !dbg !563
  %".25" = trunc i64 %".24" to i32 , !dbg !563
  ret i32 %".25", !dbg !563
if.end:
  br label %"for.incr", !dbg !563
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !58
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !567, metadata !7), !dbg !568
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !570, metadata !7), !dbg !568
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !571
  %".8" = load i64, i64* %".7", !dbg !571
  %".9" = add i64 %".8", 1, !dbg !571
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !571
  %".11" = sext i32 %".10" to i64 , !dbg !571
  %".12" = icmp ne i64 %".11", 0 , !dbg !571
  br i1 %".12", label %"if.then", label %"if.end", !dbg !571
if.then:
  %".14" = sub i64 0, 1, !dbg !572
  %".15" = trunc i64 %".14" to i32 , !dbg !572
  ret i32 %".15", !dbg !572
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !573
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !573
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !573
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !573
  %".21" = load i64, i64* %".20", !dbg !573
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !573
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !573
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !574
  %".25" = load i64, i64* %".24", !dbg !574
  %".26" = add i64 %".25", 1, !dbg !574
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !574
  store i64 %".26", i64* %".27", !dbg !574
  %".29" = trunc i64 0 to i32 , !dbg !575
  ret i32 %".29", !dbg !575
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !59
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !576, metadata !7), !dbg !577
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !578, metadata !7), !dbg !577
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !579
  %".8" = load i64, i64* %".7", !dbg !579
  %".9" = add i64 %".8", 1, !dbg !579
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !579
  %".11" = sext i32 %".10" to i64 , !dbg !579
  %".12" = icmp ne i64 %".11", 0 , !dbg !579
  br i1 %".12", label %"if.then", label %"if.end", !dbg !579
if.then:
  %".14" = sub i64 0, 1, !dbg !580
  %".15" = trunc i64 %".14" to i32 , !dbg !580
  ret i32 %".15", !dbg !580
if.end:
  %".17" = load i8, i8* %"item", !dbg !581
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !581
  %".19" = load i8*, i8** %".18", !dbg !581
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !581
  %".21" = load i64, i64* %".20", !dbg !581
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !581
  store i8 %".17", i8* %".22", !dbg !581
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !582
  %".25" = load i64, i64* %".24", !dbg !582
  %".26" = add i64 %".25", 1, !dbg !582
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !582
  store i64 %".26", i64* %".27", !dbg !582
  %".29" = trunc i64 0 to i32 , !dbg !583
  ret i32 %".29", !dbg !583
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !60
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !584, metadata !7), !dbg !585
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !586, metadata !7), !dbg !585
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !587, metadata !7), !dbg !585
  %".10" = load i8, i8* %"item", !dbg !588
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !588
  %".12" = load i8*, i8** %".11", !dbg !588
  %".13" = load i64, i64* %"idx", !dbg !588
  %".14" = getelementptr i8, i8* %".12", i64 %".13" , !dbg !588
  store i8 %".10", i8* %".14", !dbg !588
  %".16" = trunc i64 0 to i32 , !dbg !589
  ret i32 %".16", !dbg !589
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !61
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !590
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !591, metadata !7), !dbg !592
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !593
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !593
  store i8* null, i8** %".4", !dbg !593
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !594
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !594
  store i64 0, i64* %".7", !dbg !594
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !595
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !595
  store i64 0, i64* %".10", !dbg !595
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !596
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !596
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !62
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !597, metadata !7), !dbg !598
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !599, metadata !7), !dbg !598
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !600
  %".8" = load i8*, i8** %".7", !dbg !600
  %".9" = load i64, i64* %"idx", !dbg !600
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !600
  %".11" = load i8, i8* %".10", !dbg !600
  ret i8 %".11", !dbg !600
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !63
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !601, metadata !7), !dbg !602
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !603, metadata !7), !dbg !602
  %".7" = load i64, i64* %"new_cap", !dbg !604
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !604
  %".9" = load i64, i64* %".8", !dbg !604
  %".10" = icmp sle i64 %".7", %".9" , !dbg !604
  br i1 %".10", label %"if.then", label %"if.end", !dbg !604
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !605
  ret i32 %".12", !dbg !605
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !606
  %".15" = mul i64 %".14", 1, !dbg !606
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !607
  %".17" = load i8*, i8** %".16", !dbg !607
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !607
  %".19" = icmp eq i8* %".18", null , !dbg !608
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !608
if.then.1:
  %".21" = sub i64 0, 1, !dbg !609
  %".22" = trunc i64 %".21" to i32 , !dbg !609
  ret i32 %".22", !dbg !609
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !610
  store i8* %".18", i8** %".24", !dbg !610
  %".26" = load i64, i64* %"new_cap", !dbg !611
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !611
  store i64 %".26", i64* %".27", !dbg !611
  %".29" = trunc i64 0 to i32 , !dbg !612
  ret i32 %".29", !dbg !612
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !64
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !618
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !613, metadata !7), !dbg !614
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !615, metadata !7), !dbg !614
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !616
  %".8" = load i64, i64* %".7", !dbg !616
  %".9" = load i64, i64* %"needed", !dbg !616
  %".10" = icmp sge i64 %".8", %".9" , !dbg !616
  br i1 %".10", label %"if.then", label %"if.end", !dbg !616
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !617
  ret i32 %".12", !dbg !617
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !618
  %".15" = load i64, i64* %".14", !dbg !618
  store i64 %".15", i64* %"new_cap.addr", !dbg !618
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !619, metadata !7), !dbg !620
  %".18" = load i64, i64* %"new_cap.addr", !dbg !621
  %".19" = icmp eq i64 %".18", 0 , !dbg !621
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !621
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !622
  br label %"if.end.1", !dbg !622
if.end.1:
  br label %"while.cond", !dbg !623
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !623
  %".25" = load i64, i64* %"needed", !dbg !623
  %".26" = icmp slt i64 %".24", %".25" , !dbg !623
  br i1 %".26", label %"while.body", label %"while.end", !dbg !623
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !624
  %".29" = mul i64 %".28", 2, !dbg !624
  store i64 %".29", i64* %"new_cap.addr", !dbg !624
  br label %"while.cond", !dbg !624
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !625
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !625
  ret i32 %".33", !dbg !625
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !65
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !626, metadata !7), !dbg !627
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !628, metadata !7), !dbg !627
  %".7" = load i64, i64* %"new_cap", !dbg !629
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !629
  %".9" = load i64, i64* %".8", !dbg !629
  %".10" = icmp sle i64 %".7", %".9" , !dbg !629
  br i1 %".10", label %"if.then", label %"if.end", !dbg !629
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !630
  ret i32 %".12", !dbg !630
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !631
  %".15" = mul i64 %".14", 16, !dbg !631
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !632
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !632
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !632
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !632
  %".20" = icmp eq i8* %".19", null , !dbg !633
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !633
if.then.1:
  %".22" = sub i64 0, 1, !dbg !634
  %".23" = trunc i64 %".22" to i32 , !dbg !634
  ret i32 %".23", !dbg !634
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !635
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !635
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !635
  %".28" = load i64, i64* %"new_cap", !dbg !636
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !636
  store i64 %".28", i64* %".29", !dbg !636
  %".31" = trunc i64 0 to i32 , !dbg !637
  ret i32 %".31", !dbg !637
}

@".str.0" = private constant [4 x i8] c"0x0\00"
@".str.1" = private constant [3 x i8] c"0x\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/ritzunit/ritz/ritzlib", filename: "string.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 140, name: "string_new", scopeLine: 140, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 146, name: "string_with_cap", scopeLine: 146, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 154, name: "string_from", scopeLine: 154, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 170, name: "string_from_cstr", scopeLine: 170, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 189, name: "string_from_bytes", scopeLine: 189, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 205, name: "string_from_strview", scopeLine: 205, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 209, name: "string_drop", scopeLine: 209, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 217, name: "string_len", scopeLine: 217, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 221, name: "string_cap", scopeLine: 221, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "string_is_empty", scopeLine: 225, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 232, name: "string_as_ptr", scopeLine: 232, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 241, name: "string_get", scopeLine: 241, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 249, name: "string_push", scopeLine: 249, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 253, name: "string_push_str", scopeLine: 253, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 262, name: "string_push_string", scopeLine: 262, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 270, name: "string_push_bytes", scopeLine: 270, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 277, name: "string_clear", scopeLine: 277, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 281, name: "string_pop", scopeLine: 281, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 289, name: "string_eq", scopeLine: 289, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 305, name: "string_hash", scopeLine: 305, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 313, name: "string_eq_cstr", scopeLine: 313, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 335, name: "string_clone", scopeLine: 335, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 349, name: "string_starts_with_string", scopeLine: 349, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 365, name: "string_ends_with_string", scopeLine: 365, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 382, name: "string_contains_string", scopeLine: 382, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 407, name: "string_find", scopeLine: 407, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 432, name: "string_slice", scopeLine: 432, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 453, name: "string_char_at", scopeLine: 453, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 459, name: "string_set_char", scopeLine: 459, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 470, name: "string_starts_with", scopeLine: 470, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 484, name: "string_ends_with", scopeLine: 484, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 504, name: "string_contains", scopeLine: 504, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 536, name: "string_from_i64", scopeLine: 536, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 570, name: "string_push_i64", scopeLine: 570, type: !4, unit: !1)
!51 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 603, name: "string_from_hex", scopeLine: 603, type: !4, unit: !1)
!52 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!53 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!54 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!55 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!56 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!57 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!58 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!59 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!60 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!61 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!62 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!63 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!64 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!65 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!66 = !DILocation(column: 5, line: 141, scope: !17)
!67 = !DICompositeType(align: 64, file: !0, name: "String", size: 192, tag: DW_TAG_structure_type)
!68 = !DILocalVariable(file: !0, line: 141, name: "s", scope: !17, type: !67)
!69 = !DILocation(column: 1, line: 141, scope: !17)
!70 = !DILocation(column: 5, line: 142, scope: !17)
!71 = !DILocation(column: 5, line: 143, scope: !17)
!72 = !DILocalVariable(file: !0, line: 146, name: "cap", scope: !18, type: !11)
!73 = !DILocation(column: 1, line: 146, scope: !18)
!74 = !DILocation(column: 5, line: 147, scope: !18)
!75 = !DILocalVariable(file: !0, line: 147, name: "s", scope: !18, type: !67)
!76 = !DILocation(column: 1, line: 147, scope: !18)
!77 = !DILocation(column: 5, line: 148, scope: !18)
!78 = !DILocation(column: 5, line: 149, scope: !18)
!79 = !DICompositeType(align: 64, file: !0, name: "StrView", size: 128, tag: DW_TAG_structure_type)
!80 = !DILocalVariable(file: !0, line: 154, name: "sv", scope: !19, type: !79)
!81 = !DILocation(column: 1, line: 154, scope: !19)
!82 = !DILocation(column: 5, line: 155, scope: !19)
!83 = !DILocalVariable(file: !0, line: 155, name: "s", scope: !19, type: !67)
!84 = !DILocation(column: 1, line: 155, scope: !19)
!85 = !DILocation(column: 5, line: 156, scope: !19)
!86 = !DILocation(column: 5, line: 159, scope: !19)
!87 = !DILocation(column: 5, line: 162, scope: !19)
!88 = !DILocation(column: 5, line: 165, scope: !19)
!89 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!90 = !DILocalVariable(file: !0, line: 170, name: "cstr", scope: !20, type: !89)
!91 = !DILocation(column: 1, line: 170, scope: !20)
!92 = !DILocation(column: 5, line: 171, scope: !20)
!93 = !DILocalVariable(file: !0, line: 171, name: "s", scope: !20, type: !67)
!94 = !DILocation(column: 1, line: 171, scope: !20)
!95 = !DILocation(column: 5, line: 172, scope: !20)
!96 = !DILocation(column: 5, line: 175, scope: !20)
!97 = !DILocalVariable(file: !0, line: 175, name: "len", scope: !20, type: !11)
!98 = !DILocation(column: 1, line: 175, scope: !20)
!99 = !DILocation(column: 5, line: 176, scope: !20)
!100 = !DILocation(column: 9, line: 177, scope: !20)
!101 = !DILocation(column: 5, line: 180, scope: !20)
!102 = !DILocation(column: 5, line: 183, scope: !20)
!103 = !DILocation(column: 5, line: 186, scope: !20)
!104 = !DILocalVariable(file: !0, line: 189, name: "bytes", scope: !21, type: !89)
!105 = !DILocation(column: 1, line: 189, scope: !21)
!106 = !DILocalVariable(file: !0, line: 189, name: "len", scope: !21, type: !11)
!107 = !DILocation(column: 5, line: 190, scope: !21)
!108 = !DILocalVariable(file: !0, line: 190, name: "s", scope: !21, type: !67)
!109 = !DILocation(column: 1, line: 190, scope: !21)
!110 = !DILocation(column: 5, line: 191, scope: !21)
!111 = !DILocation(column: 5, line: 194, scope: !21)
!112 = !DILocation(column: 5, line: 197, scope: !21)
!113 = !DILocation(column: 5, line: 200, scope: !21)
!114 = !DIDerivedType(baseType: !79, size: 64, tag: DW_TAG_pointer_type)
!115 = !DILocalVariable(file: !0, line: 205, name: "sv", scope: !22, type: !114)
!116 = !DILocation(column: 1, line: 205, scope: !22)
!117 = !DILocation(column: 5, line: 206, scope: !22)
!118 = !DIDerivedType(baseType: !67, size: 64, tag: DW_TAG_reference_type)
!119 = !DILocalVariable(file: !0, line: 209, name: "s", scope: !23, type: !118)
!120 = !DILocation(column: 1, line: 209, scope: !23)
!121 = !DILocation(column: 5, line: 210, scope: !23)
!122 = !DILocalVariable(file: !0, line: 217, name: "s", scope: !24, type: !118)
!123 = !DILocation(column: 1, line: 217, scope: !24)
!124 = !DILocation(column: 5, line: 218, scope: !24)
!125 = !DILocalVariable(file: !0, line: 221, name: "s", scope: !25, type: !118)
!126 = !DILocation(column: 1, line: 221, scope: !25)
!127 = !DILocation(column: 5, line: 222, scope: !25)
!128 = !DILocalVariable(file: !0, line: 225, name: "s", scope: !26, type: !118)
!129 = !DILocation(column: 1, line: 225, scope: !26)
!130 = !DILocation(column: 5, line: 226, scope: !26)
!131 = !DILocation(column: 9, line: 227, scope: !26)
!132 = !DILocation(column: 5, line: 228, scope: !26)
!133 = !DILocalVariable(file: !0, line: 232, name: "s", scope: !27, type: !118)
!134 = !DILocation(column: 1, line: 232, scope: !27)
!135 = !DILocation(column: 5, line: 234, scope: !27)
!136 = !DILocation(column: 5, line: 235, scope: !27)
!137 = !DILocation(column: 5, line: 236, scope: !27)
!138 = !DILocation(column: 5, line: 237, scope: !27)
!139 = !DILocation(column: 5, line: 238, scope: !27)
!140 = !DILocalVariable(file: !0, line: 241, name: "s", scope: !28, type: !118)
!141 = !DILocation(column: 1, line: 241, scope: !28)
!142 = !DILocalVariable(file: !0, line: 241, name: "idx", scope: !28, type: !11)
!143 = !DILocation(column: 5, line: 242, scope: !28)
!144 = !DILocalVariable(file: !0, line: 249, name: "s", scope: !29, type: !118)
!145 = !DILocation(column: 1, line: 249, scope: !29)
!146 = !DILocalVariable(file: !0, line: 249, name: "b", scope: !29, type: !12)
!147 = !DILocation(column: 5, line: 250, scope: !29)
!148 = !DILocalVariable(file: !0, line: 253, name: "s", scope: !30, type: !118)
!149 = !DILocation(column: 1, line: 253, scope: !30)
!150 = !DILocalVariable(file: !0, line: 253, name: "cstr", scope: !30, type: !89)
!151 = !DILocation(column: 5, line: 254, scope: !30)
!152 = !DILocalVariable(file: !0, line: 254, name: "i", scope: !30, type: !11)
!153 = !DILocation(column: 1, line: 254, scope: !30)
!154 = !DILocation(column: 5, line: 255, scope: !30)
!155 = !DILocation(column: 9, line: 256, scope: !30)
!156 = !DILocation(column: 13, line: 257, scope: !30)
!157 = !DILocation(column: 9, line: 258, scope: !30)
!158 = !DILocation(column: 5, line: 259, scope: !30)
!159 = !DILocalVariable(file: !0, line: 262, name: "s", scope: !31, type: !118)
!160 = !DILocation(column: 1, line: 262, scope: !31)
!161 = !DILocalVariable(file: !0, line: 262, name: "other", scope: !31, type: !118)
!162 = !DILocation(column: 5, line: 263, scope: !31)
!163 = !DILocation(column: 5, line: 264, scope: !31)
!164 = !DILocation(column: 13, line: 266, scope: !31)
!165 = !DILocation(column: 5, line: 267, scope: !31)
!166 = !DILocalVariable(file: !0, line: 270, name: "s", scope: !32, type: !118)
!167 = !DILocation(column: 1, line: 270, scope: !32)
!168 = !DILocalVariable(file: !0, line: 270, name: "bytes", scope: !32, type: !89)
!169 = !DILocalVariable(file: !0, line: 270, name: "len", scope: !32, type: !11)
!170 = !DILocation(column: 5, line: 271, scope: !32)
!171 = !DILocation(column: 13, line: 273, scope: !32)
!172 = !DILocation(column: 5, line: 274, scope: !32)
!173 = !DILocalVariable(file: !0, line: 277, name: "s", scope: !33, type: !118)
!174 = !DILocation(column: 1, line: 277, scope: !33)
!175 = !DILocation(column: 5, line: 278, scope: !33)
!176 = !DILocalVariable(file: !0, line: 281, name: "s", scope: !34, type: !118)
!177 = !DILocation(column: 1, line: 281, scope: !34)
!178 = !DILocation(column: 5, line: 282, scope: !34)
!179 = !DILocalVariable(file: !0, line: 289, name: "a", scope: !35, type: !118)
!180 = !DILocation(column: 1, line: 289, scope: !35)
!181 = !DILocalVariable(file: !0, line: 289, name: "b", scope: !35, type: !118)
!182 = !DILocation(column: 5, line: 290, scope: !35)
!183 = !DILocation(column: 5, line: 291, scope: !35)
!184 = !DILocation(column: 5, line: 293, scope: !35)
!185 = !DILocation(column: 9, line: 294, scope: !35)
!186 = !DILocation(column: 5, line: 296, scope: !35)
!187 = !DILocalVariable(file: !0, line: 296, name: "i", scope: !35, type: !11)
!188 = !DILocation(column: 1, line: 296, scope: !35)
!189 = !DILocation(column: 5, line: 297, scope: !35)
!190 = !DILocation(column: 9, line: 298, scope: !35)
!191 = !DILocation(column: 13, line: 299, scope: !35)
!192 = !DILocation(column: 9, line: 300, scope: !35)
!193 = !DILocation(column: 5, line: 302, scope: !35)
!194 = !DILocalVariable(file: !0, line: 305, name: "s", scope: !36, type: !118)
!195 = !DILocation(column: 1, line: 305, scope: !36)
!196 = !DILocation(column: 5, line: 306, scope: !36)
!197 = !DILocalVariable(file: !0, line: 306, name: "h", scope: !36, type: !15)
!198 = !DILocation(column: 1, line: 306, scope: !36)
!199 = !DILocation(column: 5, line: 307, scope: !36)
!200 = !DILocation(column: 5, line: 308, scope: !36)
!201 = !DILocation(column: 9, line: 309, scope: !36)
!202 = !DILocation(column: 5, line: 310, scope: !36)
!203 = !DILocalVariable(file: !0, line: 313, name: "s", scope: !37, type: !118)
!204 = !DILocation(column: 1, line: 313, scope: !37)
!205 = !DILocalVariable(file: !0, line: 313, name: "cstr", scope: !37, type: !89)
!206 = !DILocation(column: 5, line: 314, scope: !37)
!207 = !DILocation(column: 5, line: 316, scope: !37)
!208 = !DILocalVariable(file: !0, line: 316, name: "i", scope: !37, type: !11)
!209 = !DILocation(column: 1, line: 316, scope: !37)
!210 = !DILocation(column: 5, line: 317, scope: !37)
!211 = !DILocation(column: 9, line: 318, scope: !37)
!212 = !DILocation(column: 13, line: 319, scope: !37)
!213 = !DILocation(column: 9, line: 320, scope: !37)
!214 = !DILocation(column: 13, line: 321, scope: !37)
!215 = !DILocation(column: 9, line: 322, scope: !37)
!216 = !DILocation(column: 5, line: 325, scope: !37)
!217 = !DILocation(column: 9, line: 326, scope: !37)
!218 = !DILocation(column: 5, line: 328, scope: !37)
!219 = !DILocalVariable(file: !0, line: 335, name: "s", scope: !38, type: !118)
!220 = !DILocation(column: 1, line: 335, scope: !38)
!221 = !DILocation(column: 5, line: 336, scope: !38)
!222 = !DILocation(column: 5, line: 337, scope: !38)
!223 = !DILocalVariable(file: !0, line: 337, name: "clone", scope: !38, type: !67)
!224 = !DILocation(column: 1, line: 337, scope: !38)
!225 = !DILocation(column: 5, line: 339, scope: !38)
!226 = !DILocation(column: 5, line: 342, scope: !38)
!227 = !DILocalVariable(file: !0, line: 349, name: "s", scope: !39, type: !118)
!228 = !DILocation(column: 1, line: 349, scope: !39)
!229 = !DILocalVariable(file: !0, line: 349, name: "prefix", scope: !39, type: !118)
!230 = !DILocation(column: 5, line: 350, scope: !39)
!231 = !DILocation(column: 5, line: 351, scope: !39)
!232 = !DILocation(column: 5, line: 353, scope: !39)
!233 = !DILocation(column: 9, line: 354, scope: !39)
!234 = !DILocation(column: 5, line: 356, scope: !39)
!235 = !DILocalVariable(file: !0, line: 356, name: "i", scope: !39, type: !11)
!236 = !DILocation(column: 1, line: 356, scope: !39)
!237 = !DILocation(column: 5, line: 357, scope: !39)
!238 = !DILocation(column: 9, line: 358, scope: !39)
!239 = !DILocation(column: 13, line: 359, scope: !39)
!240 = !DILocation(column: 9, line: 360, scope: !39)
!241 = !DILocation(column: 5, line: 362, scope: !39)
!242 = !DILocalVariable(file: !0, line: 365, name: "s", scope: !40, type: !118)
!243 = !DILocation(column: 1, line: 365, scope: !40)
!244 = !DILocalVariable(file: !0, line: 365, name: "suffix", scope: !40, type: !118)
!245 = !DILocation(column: 5, line: 366, scope: !40)
!246 = !DILocation(column: 5, line: 367, scope: !40)
!247 = !DILocation(column: 5, line: 369, scope: !40)
!248 = !DILocation(column: 9, line: 370, scope: !40)
!249 = !DILocation(column: 5, line: 372, scope: !40)
!250 = !DILocation(column: 5, line: 373, scope: !40)
!251 = !DILocalVariable(file: !0, line: 373, name: "i", scope: !40, type: !11)
!252 = !DILocation(column: 1, line: 373, scope: !40)
!253 = !DILocation(column: 5, line: 374, scope: !40)
!254 = !DILocation(column: 9, line: 375, scope: !40)
!255 = !DILocation(column: 13, line: 376, scope: !40)
!256 = !DILocation(column: 9, line: 377, scope: !40)
!257 = !DILocation(column: 5, line: 379, scope: !40)
!258 = !DILocalVariable(file: !0, line: 382, name: "s", scope: !41, type: !118)
!259 = !DILocation(column: 1, line: 382, scope: !41)
!260 = !DILocalVariable(file: !0, line: 382, name: "needle", scope: !41, type: !118)
!261 = !DILocation(column: 5, line: 383, scope: !41)
!262 = !DILocation(column: 5, line: 384, scope: !41)
!263 = !DILocation(column: 5, line: 386, scope: !41)
!264 = !DILocation(column: 9, line: 387, scope: !41)
!265 = !DILocation(column: 5, line: 389, scope: !41)
!266 = !DILocation(column: 9, line: 390, scope: !41)
!267 = !DILocation(column: 5, line: 392, scope: !41)
!268 = !DILocation(column: 5, line: 393, scope: !41)
!269 = !DILocation(column: 9, line: 394, scope: !41)
!270 = !DILocalVariable(file: !0, line: 394, name: "j", scope: !41, type: !11)
!271 = !DILocation(column: 1, line: 394, scope: !41)
!272 = !DILocation(column: 9, line: 395, scope: !41)
!273 = !DILocalVariable(file: !0, line: 395, name: "found", scope: !41, type: !10)
!274 = !DILocation(column: 1, line: 395, scope: !41)
!275 = !DILocation(column: 9, line: 396, scope: !41)
!276 = !DILocation(column: 13, line: 397, scope: !41)
!277 = !DILocation(column: 17, line: 398, scope: !41)
!278 = !DILocation(column: 17, line: 399, scope: !41)
!279 = !DILocation(column: 13, line: 400, scope: !41)
!280 = !DILocation(column: 13, line: 402, scope: !41)
!281 = !DILocation(column: 5, line: 404, scope: !41)
!282 = !DILocalVariable(file: !0, line: 407, name: "s", scope: !42, type: !118)
!283 = !DILocation(column: 1, line: 407, scope: !42)
!284 = !DILocalVariable(file: !0, line: 407, name: "needle", scope: !42, type: !118)
!285 = !DILocation(column: 5, line: 408, scope: !42)
!286 = !DILocation(column: 5, line: 409, scope: !42)
!287 = !DILocation(column: 5, line: 411, scope: !42)
!288 = !DILocation(column: 9, line: 412, scope: !42)
!289 = !DILocation(column: 5, line: 414, scope: !42)
!290 = !DILocation(column: 9, line: 415, scope: !42)
!291 = !DILocation(column: 5, line: 417, scope: !42)
!292 = !DILocation(column: 5, line: 418, scope: !42)
!293 = !DILocation(column: 9, line: 419, scope: !42)
!294 = !DILocalVariable(file: !0, line: 419, name: "j", scope: !42, type: !11)
!295 = !DILocation(column: 1, line: 419, scope: !42)
!296 = !DILocation(column: 9, line: 420, scope: !42)
!297 = !DILocalVariable(file: !0, line: 420, name: "found", scope: !42, type: !10)
!298 = !DILocation(column: 1, line: 420, scope: !42)
!299 = !DILocation(column: 9, line: 421, scope: !42)
!300 = !DILocation(column: 13, line: 422, scope: !42)
!301 = !DILocation(column: 17, line: 423, scope: !42)
!302 = !DILocation(column: 17, line: 424, scope: !42)
!303 = !DILocation(column: 13, line: 425, scope: !42)
!304 = !DILocation(column: 13, line: 427, scope: !42)
!305 = !DILocation(column: 5, line: 429, scope: !42)
!306 = !DILocalVariable(file: !0, line: 432, name: "s", scope: !43, type: !118)
!307 = !DILocation(column: 1, line: 432, scope: !43)
!308 = !DILocalVariable(file: !0, line: 432, name: "start", scope: !43, type: !11)
!309 = !DILocalVariable(file: !0, line: 432, name: "end", scope: !43, type: !11)
!310 = !DILocation(column: 5, line: 433, scope: !43)
!311 = !DILocation(column: 5, line: 434, scope: !43)
!312 = !DILocalVariable(file: !0, line: 434, name: "result", scope: !43, type: !67)
!313 = !DILocation(column: 1, line: 434, scope: !43)
!314 = !DILocation(column: 5, line: 437, scope: !43)
!315 = !DILocalVariable(file: !0, line: 437, name: "st", scope: !43, type: !11)
!316 = !DILocation(column: 1, line: 437, scope: !43)
!317 = !DILocation(column: 5, line: 438, scope: !43)
!318 = !DILocalVariable(file: !0, line: 438, name: "en", scope: !43, type: !11)
!319 = !DILocation(column: 1, line: 438, scope: !43)
!320 = !DILocation(column: 5, line: 439, scope: !43)
!321 = !DILocation(column: 9, line: 440, scope: !43)
!322 = !DILocation(column: 5, line: 441, scope: !43)
!323 = !DILocation(column: 9, line: 442, scope: !43)
!324 = !DILocation(column: 5, line: 443, scope: !43)
!325 = !DILocation(column: 9, line: 444, scope: !43)
!326 = !DILocation(column: 5, line: 447, scope: !43)
!327 = !DILocation(column: 5, line: 450, scope: !43)
!328 = !DILocalVariable(file: !0, line: 453, name: "s", scope: !44, type: !118)
!329 = !DILocation(column: 1, line: 453, scope: !44)
!330 = !DILocalVariable(file: !0, line: 453, name: "idx", scope: !44, type: !11)
!331 = !DILocation(column: 5, line: 454, scope: !44)
!332 = !DILocation(column: 9, line: 455, scope: !44)
!333 = !DILocation(column: 5, line: 456, scope: !44)
!334 = !DILocalVariable(file: !0, line: 459, name: "s", scope: !45, type: !118)
!335 = !DILocation(column: 1, line: 459, scope: !45)
!336 = !DILocalVariable(file: !0, line: 459, name: "idx", scope: !45, type: !11)
!337 = !DILocalVariable(file: !0, line: 459, name: "c", scope: !45, type: !12)
!338 = !DILocation(column: 5, line: 460, scope: !45)
!339 = !DILocation(column: 9, line: 461, scope: !45)
!340 = !DILocation(column: 5, line: 462, scope: !45)
!341 = !DILocation(column: 5, line: 463, scope: !45)
!342 = !DILocalVariable(file: !0, line: 470, name: "s", scope: !46, type: !118)
!343 = !DILocation(column: 1, line: 470, scope: !46)
!344 = !DILocalVariable(file: !0, line: 470, name: "prefix", scope: !46, type: !89)
!345 = !DILocation(column: 5, line: 471, scope: !46)
!346 = !DILocalVariable(file: !0, line: 471, name: "i", scope: !46, type: !11)
!347 = !DILocation(column: 1, line: 471, scope: !46)
!348 = !DILocation(column: 5, line: 472, scope: !46)
!349 = !DILocation(column: 5, line: 474, scope: !46)
!350 = !DILocation(column: 9, line: 475, scope: !46)
!351 = !DILocation(column: 13, line: 476, scope: !46)
!352 = !DILocation(column: 9, line: 477, scope: !46)
!353 = !DILocation(column: 13, line: 478, scope: !46)
!354 = !DILocation(column: 9, line: 479, scope: !46)
!355 = !DILocation(column: 5, line: 481, scope: !46)
!356 = !DILocalVariable(file: !0, line: 484, name: "s", scope: !47, type: !118)
!357 = !DILocation(column: 1, line: 484, scope: !47)
!358 = !DILocalVariable(file: !0, line: 484, name: "suffix", scope: !47, type: !89)
!359 = !DILocation(column: 5, line: 486, scope: !47)
!360 = !DILocalVariable(file: !0, line: 486, name: "suffix_len", scope: !47, type: !11)
!361 = !DILocation(column: 1, line: 486, scope: !47)
!362 = !DILocation(column: 5, line: 487, scope: !47)
!363 = !DILocation(column: 9, line: 488, scope: !47)
!364 = !DILocation(column: 5, line: 490, scope: !47)
!365 = !DILocation(column: 5, line: 491, scope: !47)
!366 = !DILocation(column: 9, line: 492, scope: !47)
!367 = !DILocation(column: 5, line: 494, scope: !47)
!368 = !DILocation(column: 5, line: 495, scope: !47)
!369 = !DILocalVariable(file: !0, line: 495, name: "i", scope: !47, type: !11)
!370 = !DILocation(column: 1, line: 495, scope: !47)
!371 = !DILocation(column: 5, line: 496, scope: !47)
!372 = !DILocation(column: 9, line: 497, scope: !47)
!373 = !DILocation(column: 13, line: 498, scope: !47)
!374 = !DILocation(column: 9, line: 499, scope: !47)
!375 = !DILocation(column: 5, line: 501, scope: !47)
!376 = !DILocalVariable(file: !0, line: 504, name: "s", scope: !48, type: !118)
!377 = !DILocation(column: 1, line: 504, scope: !48)
!378 = !DILocalVariable(file: !0, line: 504, name: "needle", scope: !48, type: !89)
!379 = !DILocation(column: 5, line: 506, scope: !48)
!380 = !DILocalVariable(file: !0, line: 506, name: "needle_len", scope: !48, type: !11)
!381 = !DILocation(column: 1, line: 506, scope: !48)
!382 = !DILocation(column: 5, line: 507, scope: !48)
!383 = !DILocation(column: 9, line: 508, scope: !48)
!384 = !DILocation(column: 5, line: 510, scope: !48)
!385 = !DILocation(column: 9, line: 511, scope: !48)
!386 = !DILocation(column: 5, line: 513, scope: !48)
!387 = !DILocation(column: 5, line: 514, scope: !48)
!388 = !DILocation(column: 9, line: 515, scope: !48)
!389 = !DILocation(column: 5, line: 517, scope: !48)
!390 = !DILocation(column: 5, line: 518, scope: !48)
!391 = !DILocation(column: 9, line: 519, scope: !48)
!392 = !DILocalVariable(file: !0, line: 519, name: "j", scope: !48, type: !11)
!393 = !DILocation(column: 1, line: 519, scope: !48)
!394 = !DILocation(column: 9, line: 520, scope: !48)
!395 = !DILocalVariable(file: !0, line: 520, name: "found", scope: !48, type: !10)
!396 = !DILocation(column: 1, line: 520, scope: !48)
!397 = !DILocation(column: 9, line: 521, scope: !48)
!398 = !DILocation(column: 13, line: 522, scope: !48)
!399 = !DILocation(column: 17, line: 523, scope: !48)
!400 = !DILocation(column: 17, line: 524, scope: !48)
!401 = !DILocation(column: 13, line: 525, scope: !48)
!402 = !DILocation(column: 13, line: 527, scope: !48)
!403 = !DILocation(column: 5, line: 529, scope: !48)
!404 = !DILocalVariable(file: !0, line: 536, name: "n", scope: !49, type: !11)
!405 = !DILocation(column: 1, line: 536, scope: !49)
!406 = !DILocation(column: 5, line: 537, scope: !49)
!407 = !DILocalVariable(file: !0, line: 537, name: "s", scope: !49, type: !67)
!408 = !DILocation(column: 1, line: 537, scope: !49)
!409 = !DILocation(column: 5, line: 539, scope: !49)
!410 = !DILocation(column: 9, line: 540, scope: !49)
!411 = !DILocation(column: 9, line: 541, scope: !49)
!412 = !DILocation(column: 5, line: 543, scope: !49)
!413 = !DILocalVariable(file: !0, line: 543, name: "val", scope: !49, type: !11)
!414 = !DILocation(column: 1, line: 543, scope: !49)
!415 = !DILocation(column: 5, line: 544, scope: !49)
!416 = !DILocalVariable(file: !0, line: 544, name: "is_neg", scope: !49, type: !10)
!417 = !DILocation(column: 1, line: 544, scope: !49)
!418 = !DILocation(column: 5, line: 545, scope: !49)
!419 = !DILocation(column: 9, line: 546, scope: !49)
!420 = !DILocation(column: 9, line: 547, scope: !49)
!421 = !DILocation(column: 5, line: 550, scope: !49)
!422 = !DISubrange(count: 20)
!423 = !{ !422 }
!424 = !DICompositeType(baseType: !12, elements: !423, size: 160, tag: DW_TAG_array_type)
!425 = !DILocalVariable(file: !0, line: 550, name: "buf", scope: !49, type: !424)
!426 = !DILocation(column: 1, line: 550, scope: !49)
!427 = !DILocation(column: 5, line: 551, scope: !49)
!428 = !DILocalVariable(file: !0, line: 551, name: "len", scope: !49, type: !11)
!429 = !DILocation(column: 1, line: 551, scope: !49)
!430 = !DILocation(column: 5, line: 552, scope: !49)
!431 = !DILocation(column: 9, line: 553, scope: !49)
!432 = !DILocation(column: 9, line: 554, scope: !49)
!433 = !DILocation(column: 9, line: 555, scope: !49)
!434 = !DILocation(column: 5, line: 558, scope: !49)
!435 = !DILocation(column: 5, line: 562, scope: !49)
!436 = !DILocalVariable(file: !0, line: 562, name: "i", scope: !49, type: !11)
!437 = !DILocation(column: 1, line: 562, scope: !49)
!438 = !DILocation(column: 5, line: 563, scope: !49)
!439 = !DILocation(column: 9, line: 564, scope: !49)
!440 = !DILocation(column: 9, line: 565, scope: !49)
!441 = !DILocation(column: 5, line: 567, scope: !49)
!442 = !DILocalVariable(file: !0, line: 570, name: "s", scope: !50, type: !118)
!443 = !DILocation(column: 1, line: 570, scope: !50)
!444 = !DILocalVariable(file: !0, line: 570, name: "n", scope: !50, type: !11)
!445 = !DILocation(column: 5, line: 571, scope: !50)
!446 = !DILocation(column: 9, line: 572, scope: !50)
!447 = !DILocation(column: 5, line: 574, scope: !50)
!448 = !DILocalVariable(file: !0, line: 574, name: "val", scope: !50, type: !11)
!449 = !DILocation(column: 1, line: 574, scope: !50)
!450 = !DILocation(column: 5, line: 575, scope: !50)
!451 = !DILocalVariable(file: !0, line: 575, name: "is_neg", scope: !50, type: !10)
!452 = !DILocation(column: 1, line: 575, scope: !50)
!453 = !DILocation(column: 5, line: 576, scope: !50)
!454 = !DILocation(column: 9, line: 577, scope: !50)
!455 = !DILocation(column: 9, line: 578, scope: !50)
!456 = !DILocation(column: 5, line: 581, scope: !50)
!457 = !DILocalVariable(file: !0, line: 581, name: "buf", scope: !50, type: !424)
!458 = !DILocation(column: 1, line: 581, scope: !50)
!459 = !DILocation(column: 5, line: 582, scope: !50)
!460 = !DILocalVariable(file: !0, line: 582, name: "len", scope: !50, type: !11)
!461 = !DILocation(column: 1, line: 582, scope: !50)
!462 = !DILocation(column: 5, line: 583, scope: !50)
!463 = !DILocation(column: 9, line: 584, scope: !50)
!464 = !DILocation(column: 9, line: 585, scope: !50)
!465 = !DILocation(column: 9, line: 586, scope: !50)
!466 = !DILocation(column: 5, line: 589, scope: !50)
!467 = !DILocation(column: 13, line: 591, scope: !50)
!468 = !DILocation(column: 5, line: 594, scope: !50)
!469 = !DILocalVariable(file: !0, line: 594, name: "i", scope: !50, type: !11)
!470 = !DILocation(column: 1, line: 594, scope: !50)
!471 = !DILocation(column: 5, line: 595, scope: !50)
!472 = !DILocation(column: 9, line: 596, scope: !50)
!473 = !DILocation(column: 13, line: 597, scope: !50)
!474 = !DILocation(column: 9, line: 598, scope: !50)
!475 = !DILocation(column: 5, line: 600, scope: !50)
!476 = !DILocalVariable(file: !0, line: 603, name: "n", scope: !51, type: !15)
!477 = !DILocation(column: 1, line: 603, scope: !51)
!478 = !DILocation(column: 5, line: 604, scope: !51)
!479 = !DILocalVariable(file: !0, line: 604, name: "s", scope: !51, type: !67)
!480 = !DILocation(column: 1, line: 604, scope: !51)
!481 = !DILocation(column: 5, line: 606, scope: !51)
!482 = !DILocation(column: 9, line: 607, scope: !51)
!483 = !DILocation(column: 9, line: 608, scope: !51)
!484 = !DILocation(column: 5, line: 610, scope: !51)
!485 = !DILocation(column: 5, line: 612, scope: !51)
!486 = !DILocalVariable(file: !0, line: 612, name: "val", scope: !51, type: !15)
!487 = !DILocation(column: 1, line: 612, scope: !51)
!488 = !DILocation(column: 5, line: 614, scope: !51)
!489 = !DISubrange(count: 16)
!490 = !{ !489 }
!491 = !DICompositeType(baseType: !12, elements: !490, size: 128, tag: DW_TAG_array_type)
!492 = !DILocalVariable(file: !0, line: 614, name: "buf", scope: !51, type: !491)
!493 = !DILocation(column: 1, line: 614, scope: !51)
!494 = !DILocation(column: 5, line: 615, scope: !51)
!495 = !DILocalVariable(file: !0, line: 615, name: "len", scope: !51, type: !11)
!496 = !DILocation(column: 1, line: 615, scope: !51)
!497 = !DILocation(column: 5, line: 616, scope: !51)
!498 = !DILocation(column: 9, line: 617, scope: !51)
!499 = !DILocation(column: 9, line: 618, scope: !51)
!500 = !DILocation(column: 13, line: 619, scope: !51)
!501 = !DILocation(column: 13, line: 621, scope: !51)
!502 = !DILocation(column: 9, line: 622, scope: !51)
!503 = !DILocation(column: 9, line: 623, scope: !51)
!504 = !DILocation(column: 5, line: 626, scope: !51)
!505 = !DILocalVariable(file: !0, line: 626, name: "i", scope: !51, type: !11)
!506 = !DILocation(column: 1, line: 626, scope: !51)
!507 = !DILocation(column: 5, line: 627, scope: !51)
!508 = !DILocation(column: 9, line: 628, scope: !51)
!509 = !DILocation(column: 9, line: 629, scope: !51)
!510 = !DILocation(column: 5, line: 631, scope: !51)
!511 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!512 = !DIDerivedType(baseType: !511, size: 64, tag: DW_TAG_reference_type)
!513 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !52, type: !512)
!514 = !DILocation(column: 1, line: 244, scope: !52)
!515 = !DILocation(column: 5, line: 245, scope: !52)
!516 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !53, type: !512)
!517 = !DILocation(column: 1, line: 148, scope: !53)
!518 = !DILocation(column: 5, line: 149, scope: !53)
!519 = !DILocation(column: 5, line: 151, scope: !53)
!520 = !DILocation(column: 5, line: 152, scope: !53)
!521 = !DILocation(column: 5, line: 153, scope: !53)
!522 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !54, type: !512)
!523 = !DILocation(column: 1, line: 219, scope: !54)
!524 = !DILocation(column: 5, line: 220, scope: !54)
!525 = !DILocation(column: 5, line: 221, scope: !54)
!526 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !55, type: !11)
!527 = !DILocation(column: 1, line: 124, scope: !55)
!528 = !DILocation(column: 5, line: 125, scope: !55)
!529 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !55, type: !511)
!530 = !DILocation(column: 1, line: 125, scope: !55)
!531 = !DILocation(column: 5, line: 126, scope: !55)
!532 = !DILocation(column: 9, line: 127, scope: !55)
!533 = !DILocation(column: 9, line: 128, scope: !55)
!534 = !DILocation(column: 9, line: 129, scope: !55)
!535 = !DILocation(column: 9, line: 130, scope: !55)
!536 = !DILocation(column: 5, line: 132, scope: !55)
!537 = !DILocation(column: 5, line: 133, scope: !55)
!538 = !DILocation(column: 5, line: 134, scope: !55)
!539 = !DILocation(column: 9, line: 135, scope: !55)
!540 = !DILocation(column: 9, line: 136, scope: !55)
!541 = !DILocation(column: 9, line: 137, scope: !55)
!542 = !DILocation(column: 5, line: 139, scope: !55)
!543 = !DILocation(column: 5, line: 140, scope: !55)
!544 = !DILocation(column: 5, line: 141, scope: !55)
!545 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !56, type: !512)
!546 = !DILocation(column: 1, line: 193, scope: !56)
!547 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !56, type: !11)
!548 = !DILocation(column: 5, line: 194, scope: !56)
!549 = !DILocation(column: 9, line: 195, scope: !56)
!550 = !DILocation(column: 5, line: 197, scope: !56)
!551 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !56, type: !11)
!552 = !DILocation(column: 1, line: 197, scope: !56)
!553 = !DILocation(column: 5, line: 198, scope: !56)
!554 = !DILocation(column: 9, line: 199, scope: !56)
!555 = !DILocation(column: 5, line: 200, scope: !56)
!556 = !DILocation(column: 9, line: 201, scope: !56)
!557 = !DILocation(column: 5, line: 203, scope: !56)
!558 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !57, type: !512)
!559 = !DILocation(column: 1, line: 288, scope: !57)
!560 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !57, type: !89)
!561 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !57, type: !11)
!562 = !DILocation(column: 5, line: 289, scope: !57)
!563 = !DILocation(column: 13, line: 291, scope: !57)
!564 = !DILocation(column: 5, line: 292, scope: !57)
!565 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!566 = !DIDerivedType(baseType: !565, size: 64, tag: DW_TAG_reference_type)
!567 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !58, type: !566)
!568 = !DILocation(column: 1, line: 210, scope: !58)
!569 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!570 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !58, type: !569)
!571 = !DILocation(column: 5, line: 211, scope: !58)
!572 = !DILocation(column: 9, line: 212, scope: !58)
!573 = !DILocation(column: 5, line: 213, scope: !58)
!574 = !DILocation(column: 5, line: 214, scope: !58)
!575 = !DILocation(column: 5, line: 215, scope: !58)
!576 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !59, type: !512)
!577 = !DILocation(column: 1, line: 210, scope: !59)
!578 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !59, type: !12)
!579 = !DILocation(column: 5, line: 211, scope: !59)
!580 = !DILocation(column: 9, line: 212, scope: !59)
!581 = !DILocation(column: 5, line: 213, scope: !59)
!582 = !DILocation(column: 5, line: 214, scope: !59)
!583 = !DILocation(column: 5, line: 215, scope: !59)
!584 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !60, type: !512)
!585 = !DILocation(column: 1, line: 235, scope: !60)
!586 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !60, type: !11)
!587 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !60, type: !12)
!588 = !DILocation(column: 5, line: 236, scope: !60)
!589 = !DILocation(column: 5, line: 237, scope: !60)
!590 = !DILocation(column: 5, line: 117, scope: !61)
!591 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !61, type: !511)
!592 = !DILocation(column: 1, line: 117, scope: !61)
!593 = !DILocation(column: 5, line: 118, scope: !61)
!594 = !DILocation(column: 5, line: 119, scope: !61)
!595 = !DILocation(column: 5, line: 120, scope: !61)
!596 = !DILocation(column: 5, line: 121, scope: !61)
!597 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !62, type: !512)
!598 = !DILocation(column: 1, line: 225, scope: !62)
!599 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !62, type: !11)
!600 = !DILocation(column: 5, line: 226, scope: !62)
!601 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !63, type: !512)
!602 = !DILocation(column: 1, line: 179, scope: !63)
!603 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !63, type: !11)
!604 = !DILocation(column: 5, line: 180, scope: !63)
!605 = !DILocation(column: 9, line: 181, scope: !63)
!606 = !DILocation(column: 5, line: 183, scope: !63)
!607 = !DILocation(column: 5, line: 184, scope: !63)
!608 = !DILocation(column: 5, line: 185, scope: !63)
!609 = !DILocation(column: 9, line: 186, scope: !63)
!610 = !DILocation(column: 5, line: 188, scope: !63)
!611 = !DILocation(column: 5, line: 189, scope: !63)
!612 = !DILocation(column: 5, line: 190, scope: !63)
!613 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !64, type: !566)
!614 = !DILocation(column: 1, line: 193, scope: !64)
!615 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !64, type: !11)
!616 = !DILocation(column: 5, line: 194, scope: !64)
!617 = !DILocation(column: 9, line: 195, scope: !64)
!618 = !DILocation(column: 5, line: 197, scope: !64)
!619 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !64, type: !11)
!620 = !DILocation(column: 1, line: 197, scope: !64)
!621 = !DILocation(column: 5, line: 198, scope: !64)
!622 = !DILocation(column: 9, line: 199, scope: !64)
!623 = !DILocation(column: 5, line: 200, scope: !64)
!624 = !DILocation(column: 9, line: 201, scope: !64)
!625 = !DILocation(column: 5, line: 203, scope: !64)
!626 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !65, type: !566)
!627 = !DILocation(column: 1, line: 179, scope: !65)
!628 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !65, type: !11)
!629 = !DILocation(column: 5, line: 180, scope: !65)
!630 = !DILocation(column: 9, line: 181, scope: !65)
!631 = !DILocation(column: 5, line: 183, scope: !65)
!632 = !DILocation(column: 5, line: 184, scope: !65)
!633 = !DILocation(column: 5, line: 185, scope: !65)
!634 = !DILocation(column: 9, line: 186, scope: !65)
!635 = !DILocation(column: 5, line: 188, scope: !65)
!636 = !DILocation(column: 5, line: 189, scope: !65)
!637 = !DILocation(column: 5, line: 190, scope: !65)