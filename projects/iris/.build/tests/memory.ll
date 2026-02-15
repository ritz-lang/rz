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

define %"struct.ritz_module_1.Arena" @"arena_new"(i64 %"size.arg") !dbg !17
{
entry:
  %"size" = alloca i64
  %"a.addr" = alloca %"struct.ritz_module_1.Arena", !dbg !44
  store i64 %"size.arg", i64* %"size"
  call void @"llvm.dbg.declare"(metadata i64* %"size", metadata !42, metadata !7), !dbg !43
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Arena"* %"a.addr", metadata !46, metadata !7), !dbg !47
  %".6" = load i64, i64* %"size", !dbg !48
  %".7" = add i32 1, 2, !dbg !48
  %".8" = add i32 2, 32, !dbg !48
  %".9" = sub i64 0, 1, !dbg !48
  %".10" = trunc i64 %".9" to i32 , !dbg !48
  %".11" = call i8* @"sys_mmap"(i64 0, i64 %".6", i32 %".7", i32 %".8", i32 %".10", i64 0), !dbg !48
  %".12" = load %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", !dbg !48
  %".13" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", i32 0, i32 0 , !dbg !48
  store i8* %".11", i8** %".13", !dbg !48
  %".15" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", i32 0, i32 0 , !dbg !49
  %".16" = load i8*, i8** %".15", !dbg !49
  %".17" = sub i64 0, 1, !dbg !49
  %".18" = inttoptr i64 %".17" to i8* , !dbg !49
  %".19" = icmp eq i8* %".16", %".18" , !dbg !49
  br i1 %".19", label %"if.then", label %"if.end", !dbg !49
if.then:
  %".21" = load %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", !dbg !50
  %".22" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", i32 0, i32 0 , !dbg !50
  store i8* null, i8** %".22", !dbg !50
  %".24" = load %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", !dbg !51
  %".25" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", i32 0, i32 1 , !dbg !51
  store i64 0, i64* %".25", !dbg !51
  %".27" = load %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", !dbg !52
  %".28" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", i32 0, i32 2 , !dbg !52
  store i64 0, i64* %".28", !dbg !52
  %".30" = load %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", !dbg !53
  ret %"struct.ritz_module_1.Arena" %".30", !dbg !53
if.end:
  %".32" = load i64, i64* %"size", !dbg !54
  %".33" = load %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", !dbg !54
  %".34" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", i32 0, i32 1 , !dbg !54
  store i64 %".32", i64* %".34", !dbg !54
  %".36" = load %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", !dbg !55
  %".37" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", i32 0, i32 2 , !dbg !55
  store i64 0, i64* %".37", !dbg !55
  %".39" = load %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %"a.addr", !dbg !56
  ret %"struct.ritz_module_1.Arena" %".39", !dbg !56
}

define %"struct.ritz_module_1.Arena" @"arena_default"() !dbg !18
{
entry:
  %".2" = call %"struct.ritz_module_1.Arena" @"arena_new"(i64 1048576), !dbg !57
  ret %"struct.ritz_module_1.Arena" %".2", !dbg !57
}

define i8* @"arena_alloc"(%"struct.ritz_module_1.Arena"* %"a.arg", i64 %"size.arg") !dbg !19
{
entry:
  %"a" = alloca %"struct.ritz_module_1.Arena"*
  store %"struct.ritz_module_1.Arena"* %"a.arg", %"struct.ritz_module_1.Arena"** %"a"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Arena"** %"a", metadata !59, metadata !7), !dbg !60
  %"size" = alloca i64
  store i64 %"size.arg", i64* %"size"
  call void @"llvm.dbg.declare"(metadata i64* %"size", metadata !61, metadata !7), !dbg !60
  %".8" = load i64, i64* %"size", !dbg !62
  %".9" = icmp sle i64 %".8", 0 , !dbg !62
  br i1 %".9", label %"if.then", label %"if.end", !dbg !62
if.then:
  ret i8* null, !dbg !63
if.end:
  %".12" = load i64, i64* %"size", !dbg !64
  %".13" = add i64 %".12", 7, !dbg !64
  %".14" = sub i64 0, 8, !dbg !64
  %".15" = and i64 %".13", %".14", !dbg !64
  %".16" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !65
  %".17" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".16", i32 0, i32 2 , !dbg !65
  %".18" = load i64, i64* %".17", !dbg !65
  %".19" = add i64 %".18", %".15", !dbg !65
  %".20" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !65
  %".21" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".20", i32 0, i32 1 , !dbg !65
  %".22" = load i64, i64* %".21", !dbg !65
  %".23" = icmp sgt i64 %".19", %".22" , !dbg !65
  br i1 %".23", label %"if.then.1", label %"if.end.1", !dbg !65
if.then.1:
  ret i8* null, !dbg !66
if.end.1:
  %".26" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !67
  %".27" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".26", i32 0, i32 0 , !dbg !67
  %".28" = load i8*, i8** %".27", !dbg !67
  %".29" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !67
  %".30" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".29", i32 0, i32 2 , !dbg !67
  %".31" = load i64, i64* %".30", !dbg !67
  %".32" = getelementptr i8, i8* %".28", i64 %".31" , !dbg !67
  %".33" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !68
  %".34" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".33", i32 0, i32 2 , !dbg !68
  %".35" = load i64, i64* %".34", !dbg !68
  %".36" = add i64 %".35", %".15", !dbg !68
  %".37" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !68
  %".38" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".37", i32 0, i32 2 , !dbg !68
  store i64 %".36", i64* %".38", !dbg !68
  ret i8* %".32", !dbg !69
}

define i8* @"arena_alloc_zero"(%"struct.ritz_module_1.Arena"* %"a.arg", i64 %"size.arg") !dbg !20
{
entry:
  %"a" = alloca %"struct.ritz_module_1.Arena"*
  %"i.addr" = alloca i64, !dbg !76
  store %"struct.ritz_module_1.Arena"* %"a.arg", %"struct.ritz_module_1.Arena"** %"a"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Arena"** %"a", metadata !70, metadata !7), !dbg !71
  %"size" = alloca i64
  store i64 %"size.arg", i64* %"size"
  call void @"llvm.dbg.declare"(metadata i64* %"size", metadata !72, metadata !7), !dbg !71
  %".8" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !73
  %".9" = load i64, i64* %"size", !dbg !73
  %".10" = call i8* @"arena_alloc"(%"struct.ritz_module_1.Arena"* %".8", i64 %".9"), !dbg !73
  %".11" = icmp eq i8* %".10", null , !dbg !74
  br i1 %".11", label %"if.then", label %"if.end", !dbg !74
if.then:
  ret i8* %".10", !dbg !75
if.end:
  store i64 0, i64* %"i.addr", !dbg !76
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !77, metadata !7), !dbg !78
  br label %"while.cond", !dbg !79
while.cond:
  %".17" = load i64, i64* %"i.addr", !dbg !79
  %".18" = load i64, i64* %"size", !dbg !79
  %".19" = icmp slt i64 %".17", %".18" , !dbg !79
  br i1 %".19", label %"while.body", label %"while.end", !dbg !79
while.body:
  %".21" = load i64, i64* %"i.addr", !dbg !80
  %".22" = getelementptr i8, i8* %".10", i64 %".21" , !dbg !80
  %".23" = trunc i64 0 to i8 , !dbg !80
  store i8 %".23", i8* %".22", !dbg !80
  %".25" = load i64, i64* %"i.addr", !dbg !81
  %".26" = add i64 %".25", 1, !dbg !81
  store i64 %".26", i64* %"i.addr", !dbg !81
  br label %"while.cond", !dbg !81
while.end:
  ret i8* %".10", !dbg !82
}

define i8* @"arena_alloc_array"(%"struct.ritz_module_1.Arena"* %"a.arg", i64 %"count.arg", i64 %"elem_size.arg") !dbg !21
{
entry:
  %"a" = alloca %"struct.ritz_module_1.Arena"*
  store %"struct.ritz_module_1.Arena"* %"a.arg", %"struct.ritz_module_1.Arena"** %"a"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Arena"** %"a", metadata !83, metadata !7), !dbg !84
  %"count" = alloca i64
  store i64 %"count.arg", i64* %"count"
  call void @"llvm.dbg.declare"(metadata i64* %"count", metadata !85, metadata !7), !dbg !84
  %"elem_size" = alloca i64
  store i64 %"elem_size.arg", i64* %"elem_size"
  call void @"llvm.dbg.declare"(metadata i64* %"elem_size", metadata !86, metadata !7), !dbg !84
  %".11" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !87
  %".12" = load i64, i64* %"count", !dbg !87
  %".13" = load i64, i64* %"elem_size", !dbg !87
  %".14" = mul i64 %".12", %".13", !dbg !87
  %".15" = call i8* @"arena_alloc"(%"struct.ritz_module_1.Arena"* %".11", i64 %".14"), !dbg !87
  ret i8* %".15", !dbg !87
}

define i32 @"arena_reset"(%"struct.ritz_module_1.Arena"* %"a.arg") !dbg !22
{
entry:
  %"a" = alloca %"struct.ritz_module_1.Arena"*
  store %"struct.ritz_module_1.Arena"* %"a.arg", %"struct.ritz_module_1.Arena"** %"a"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Arena"** %"a", metadata !88, metadata !7), !dbg !89
  %".5" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !90
  %".6" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".5", i32 0, i32 2 , !dbg !90
  store i64 0, i64* %".6", !dbg !90
  ret i32 0, !dbg !90
}

define i32 @"arena_destroy"(%"struct.ritz_module_1.Arena"* %"a.arg") !dbg !23
{
entry:
  %"a" = alloca %"struct.ritz_module_1.Arena"*
  store %"struct.ritz_module_1.Arena"* %"a.arg", %"struct.ritz_module_1.Arena"** %"a"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Arena"** %"a", metadata !91, metadata !7), !dbg !92
  %".5" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !93
  %".6" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".5", i32 0, i32 0 , !dbg !93
  %".7" = load i8*, i8** %".6", !dbg !93
  %".8" = icmp ne i8* %".7", null , !dbg !93
  br i1 %".8", label %"and.right", label %"and.merge", !dbg !93
and.right:
  %".10" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !93
  %".11" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".10", i32 0, i32 1 , !dbg !93
  %".12" = load i64, i64* %".11", !dbg !93
  %".13" = icmp sgt i64 %".12", 0 , !dbg !93
  br label %"and.merge", !dbg !93
and.merge:
  %".15" = phi  i1 [0, %"entry"], [%".13", %"and.right"] , !dbg !93
  br i1 %".15", label %"if.then", label %"if.end", !dbg !93
if.then:
  %".17" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !93
  %".18" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".17", i32 0, i32 0 , !dbg !93
  %".19" = load i8*, i8** %".18", !dbg !93
  %".20" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !93
  %".21" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".20", i32 0, i32 1 , !dbg !93
  %".22" = load i64, i64* %".21", !dbg !93
  %".23" = call i32 @"sys_munmap"(i8* %".19", i64 %".22"), !dbg !93
  br label %"if.end", !dbg !93
if.end:
  %".25" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !94
  %".26" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".25", i32 0, i32 0 , !dbg !94
  store i8* null, i8** %".26", !dbg !94
  %".28" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !95
  %".29" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".28", i32 0, i32 1 , !dbg !95
  store i64 0, i64* %".29", !dbg !95
  %".31" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !96
  %".32" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".31", i32 0, i32 2 , !dbg !96
  store i64 0, i64* %".32", !dbg !96
  ret i32 0, !dbg !96
}

define i64 @"arena_used"(%"struct.ritz_module_1.Arena"* %"a.arg") !dbg !24
{
entry:
  %"a" = alloca %"struct.ritz_module_1.Arena"*
  store %"struct.ritz_module_1.Arena"* %"a.arg", %"struct.ritz_module_1.Arena"** %"a"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Arena"** %"a", metadata !97, metadata !7), !dbg !98
  %".5" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !99
  %".6" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".5", i32 0, i32 2 , !dbg !99
  %".7" = load i64, i64* %".6", !dbg !99
  ret i64 %".7", !dbg !99
}

define i64 @"arena_remaining"(%"struct.ritz_module_1.Arena"* %"a.arg") !dbg !25
{
entry:
  %"a" = alloca %"struct.ritz_module_1.Arena"*
  store %"struct.ritz_module_1.Arena"* %"a.arg", %"struct.ritz_module_1.Arena"** %"a"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Arena"** %"a", metadata !100, metadata !7), !dbg !101
  %".5" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !102
  %".6" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".5", i32 0, i32 1 , !dbg !102
  %".7" = load i64, i64* %".6", !dbg !102
  %".8" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !102
  %".9" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".8", i32 0, i32 2 , !dbg !102
  %".10" = load i64, i64* %".9", !dbg !102
  %".11" = sub i64 %".7", %".10", !dbg !102
  ret i64 %".11", !dbg !102
}

define i32 @"arena_valid"(%"struct.ritz_module_1.Arena"* %"a.arg") !dbg !26
{
entry:
  %"a" = alloca %"struct.ritz_module_1.Arena"*
  store %"struct.ritz_module_1.Arena"* %"a.arg", %"struct.ritz_module_1.Arena"** %"a"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Arena"** %"a", metadata !103, metadata !7), !dbg !104
  %".5" = load %"struct.ritz_module_1.Arena"*, %"struct.ritz_module_1.Arena"** %"a", !dbg !105
  %".6" = getelementptr %"struct.ritz_module_1.Arena", %"struct.ritz_module_1.Arena"* %".5", i32 0, i32 0 , !dbg !105
  %".7" = load i8*, i8** %".6", !dbg !105
  %".8" = icmp ne i8* %".7", null , !dbg !105
  br i1 %".8", label %"if.then", label %"if.end", !dbg !105
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !106
  ret i32 %".10", !dbg !106
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !107
  ret i32 %".12", !dbg !107
}

define i8* @"heap_alloc"(i64 %"size.arg") !dbg !27
{
entry:
  %"size" = alloca i64
  store i64 %"size.arg", i64* %"size"
  call void @"llvm.dbg.declare"(metadata i64* %"size", metadata !108, metadata !7), !dbg !109
  %".5" = load i64, i64* %"size", !dbg !110
  %".6" = icmp sle i64 %".5", 0 , !dbg !110
  br i1 %".6", label %"if.then", label %"if.end", !dbg !110
if.then:
  ret i8* null, !dbg !111
if.end:
  %".9" = load i64, i64* %"size", !dbg !112
  %".10" = add i32 1, 2, !dbg !112
  %".11" = add i32 2, 32, !dbg !112
  %".12" = sub i64 0, 1, !dbg !112
  %".13" = trunc i64 %".12" to i32 , !dbg !112
  %".14" = call i8* @"sys_mmap"(i64 0, i64 %".9", i32 %".10", i32 %".11", i32 %".13", i64 0), !dbg !112
  ret i8* %".14", !dbg !112
}

define i32 @"heap_free"(i8* %"ptr.arg", i64 %"size.arg") !dbg !28
{
entry:
  %"ptr" = alloca i8*
  store i8* %"ptr.arg", i8** %"ptr"
  call void @"llvm.dbg.declare"(metadata i8** %"ptr", metadata !114, metadata !7), !dbg !115
  %"size" = alloca i64
  store i64 %"size.arg", i64* %"size"
  call void @"llvm.dbg.declare"(metadata i64* %"size", metadata !116, metadata !7), !dbg !115
  %".8" = load i8*, i8** %"ptr", !dbg !117
  %".9" = icmp eq i8* %".8", null , !dbg !117
  br i1 %".9", label %"or.merge", label %"or.right", !dbg !117
or.right:
  %".11" = load i64, i64* %"size", !dbg !117
  %".12" = icmp sle i64 %".11", 0 , !dbg !117
  br label %"or.merge", !dbg !117
or.merge:
  %".14" = phi  i1 [1, %"entry"], [%".12", %"or.right"] , !dbg !117
  br i1 %".14", label %"if.then", label %"if.end", !dbg !117
if.then:
  %".16" = trunc i64 0 to i32 , !dbg !118
  ret i32 %".16", !dbg !118
if.end:
  %".18" = load i8*, i8** %"ptr", !dbg !119
  %".19" = load i64, i64* %"size", !dbg !119
  %".20" = call i32 @"sys_munmap"(i8* %".18", i64 %".19"), !dbg !119
  ret i32 %".20", !dbg !119
}

define i8* @"heap_realloc"(i8* %"ptr.arg", i64 %"old_size.arg", i64 %"new_size.arg") !dbg !29
{
entry:
  %"ptr" = alloca i8*
  %"copy_size.addr" = alloca i64, !dbg !130
  %"i.addr" = alloca i64, !dbg !135
  store i8* %"ptr.arg", i8** %"ptr"
  call void @"llvm.dbg.declare"(metadata i8** %"ptr", metadata !120, metadata !7), !dbg !121
  %"old_size" = alloca i64
  store i64 %"old_size.arg", i64* %"old_size"
  call void @"llvm.dbg.declare"(metadata i64* %"old_size", metadata !122, metadata !7), !dbg !121
  %"new_size" = alloca i64
  store i64 %"new_size.arg", i64* %"new_size"
  call void @"llvm.dbg.declare"(metadata i64* %"new_size", metadata !123, metadata !7), !dbg !121
  %".11" = load i64, i64* %"new_size", !dbg !124
  %".12" = icmp sle i64 %".11", 0 , !dbg !124
  br i1 %".12", label %"if.then", label %"if.end", !dbg !124
if.then:
  %".14" = load i8*, i8** %"ptr", !dbg !125
  %".15" = icmp ne i8* %".14", null , !dbg !125
  br i1 %".15", label %"and.right", label %"and.merge", !dbg !125
if.end:
  %".27" = load i64, i64* %"new_size", !dbg !127
  %".28" = call i8* @"heap_alloc"(i64 %".27"), !dbg !127
  %".29" = icmp eq i8* %".28", null , !dbg !128
  br i1 %".29", label %"if.then.2", label %"if.end.2", !dbg !128
and.right:
  %".17" = load i64, i64* %"old_size", !dbg !125
  %".18" = icmp sgt i64 %".17", 0 , !dbg !125
  br label %"and.merge", !dbg !125
and.merge:
  %".20" = phi  i1 [0, %"if.then"], [%".18", %"and.right"] , !dbg !125
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !125
if.then.1:
  %".22" = load i8*, i8** %"ptr", !dbg !125
  %".23" = load i64, i64* %"old_size", !dbg !125
  %".24" = call i32 @"heap_free"(i8* %".22", i64 %".23"), !dbg !125
  br label %"if.end.1", !dbg !125
if.end.1:
  ret i8* null, !dbg !126
if.then.2:
  ret i8* null, !dbg !129
if.end.2:
  %".32" = load i64, i64* %"old_size", !dbg !130
  store i64 %".32", i64* %"copy_size.addr", !dbg !130
  call void @"llvm.dbg.declare"(metadata i64* %"copy_size.addr", metadata !131, metadata !7), !dbg !132
  %".35" = load i64, i64* %"new_size", !dbg !133
  %".36" = load i64, i64* %"old_size", !dbg !133
  %".37" = icmp slt i64 %".35", %".36" , !dbg !133
  br i1 %".37", label %"if.then.3", label %"if.end.3", !dbg !133
if.then.3:
  %".39" = load i64, i64* %"new_size", !dbg !134
  store i64 %".39", i64* %"copy_size.addr", !dbg !134
  br label %"if.end.3", !dbg !134
if.end.3:
  store i64 0, i64* %"i.addr", !dbg !135
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !136, metadata !7), !dbg !137
  br label %"while.cond", !dbg !138
while.cond:
  %".45" = load i64, i64* %"i.addr", !dbg !138
  %".46" = load i64, i64* %"copy_size.addr", !dbg !138
  %".47" = icmp slt i64 %".45", %".46" , !dbg !138
  br i1 %".47", label %"while.body", label %"while.end", !dbg !138
while.body:
  %".49" = load i8*, i8** %"ptr", !dbg !139
  %".50" = load i64, i64* %"i.addr", !dbg !139
  %".51" = getelementptr i8, i8* %".49", i64 %".50" , !dbg !139
  %".52" = load i8, i8* %".51", !dbg !139
  %".53" = load i64, i64* %"i.addr", !dbg !139
  %".54" = getelementptr i8, i8* %".28", i64 %".53" , !dbg !139
  store i8 %".52", i8* %".54", !dbg !139
  %".56" = load i64, i64* %"i.addr", !dbg !140
  %".57" = add i64 %".56", 1, !dbg !140
  store i64 %".57", i64* %"i.addr", !dbg !140
  br label %"while.cond", !dbg !140
while.end:
  %".60" = load i8*, i8** %"ptr", !dbg !141
  %".61" = icmp ne i8* %".60", null , !dbg !141
  br i1 %".61", label %"and.right.1", label %"and.merge.1", !dbg !141
and.right.1:
  %".63" = load i64, i64* %"old_size", !dbg !141
  %".64" = icmp sgt i64 %".63", 0 , !dbg !141
  br label %"and.merge.1", !dbg !141
and.merge.1:
  %".66" = phi  i1 [0, %"while.end"], [%".64", %"and.right.1"] , !dbg !141
  br i1 %".66", label %"if.then.4", label %"if.end.4", !dbg !141
if.then.4:
  %".68" = load i8*, i8** %"ptr", !dbg !141
  %".69" = load i64, i64* %"old_size", !dbg !141
  %".70" = call i32 @"heap_free"(i8* %".68", i64 %".69"), !dbg !141
  br label %"if.end.4", !dbg !141
if.end.4:
  ret i8* %".28", !dbg !142
}

define i32 @"memzero"(i8* %"dst.arg", i64 %"n.arg") !dbg !30
{
entry:
  %"dst" = alloca i8*
  store i8* %"dst.arg", i8** %"dst"
  call void @"llvm.dbg.declare"(metadata i8** %"dst", metadata !143, metadata !7), !dbg !144
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !145, metadata !7), !dbg !144
  %".8" = load i8*, i8** %"dst", !dbg !146
  %".9" = trunc i64 0 to i8 , !dbg !146
  %".10" = load i64, i64* %"n", !dbg !146
  %".11" = call i8* @"memset"(i8* %".8", i8 %".9", i64 %".10"), !dbg !146
  %".12" = ptrtoint i8* %".11" to i32 , !dbg !146
  ret i32 %".12", !dbg !146
}

define i64 @"get_block_size"(i32 %"class.arg") !dbg !31
{
entry:
  %"class" = alloca i32
  store i32 %"class.arg", i32* %"class"
  call void @"llvm.dbg.declare"(metadata i32* %"class", metadata !147, metadata !7), !dbg !148
  %".5" = load i32, i32* %"class", !dbg !149
  %".6" = sext i32 %".5" to i64 , !dbg !149
  %".7" = icmp slt i64 %".6", 0 , !dbg !149
  br i1 %".7", label %"or.merge", label %"or.right", !dbg !149
or.right:
  %".9" = load i32, i32* %"class", !dbg !149
  %".10" = sext i32 %".9" to i64 , !dbg !149
  %".11" = icmp sgt i64 %".10", 8 , !dbg !149
  br label %"or.merge", !dbg !149
or.merge:
  %".13" = phi  i1 [1, %"entry"], [%".11", %"or.right"] , !dbg !149
  br i1 %".13", label %"if.then", label %"if.end", !dbg !149
if.then:
  ret i64 0, !dbg !150
if.end:
  %".16" = load i32, i32* %"class", !dbg !151
  %".17" = getelementptr [9 x i64], [9 x i64]* @"BLOCK_SIZES", i32 0, i32 %".16" , !dbg !151
  %".18" = load i64, i64* %".17", !dbg !151
  ret i64 %".18", !dbg !151
}

define i32 @"get_size_class"(i64 %"size.arg") !dbg !32
{
entry:
  %"size" = alloca i64
  store i64 %"size.arg", i64* %"size"
  call void @"llvm.dbg.declare"(metadata i64* %"size", metadata !152, metadata !7), !dbg !153
  %".5" = load i64, i64* %"size", !dbg !154
  %".6" = icmp sle i64 %".5", 0 , !dbg !154
  br i1 %".6", label %"if.then", label %"if.end", !dbg !154
if.then:
  %".8" = sub i64 0, 1, !dbg !155
  %".9" = trunc i64 %".8" to i32 , !dbg !155
  ret i32 %".9", !dbg !155
if.end:
  %".11" = load i64, i64* %"size", !dbg !156
  %".12" = icmp sle i64 %".11", 16 , !dbg !156
  br i1 %".12", label %"if.then.1", label %"if.end.1", !dbg !156
if.then.1:
  %".14" = trunc i64 0 to i32 , !dbg !157
  ret i32 %".14", !dbg !157
if.end.1:
  %".16" = load i64, i64* %"size", !dbg !158
  %".17" = icmp sgt i64 %".16", 2048 , !dbg !158
  br i1 %".17", label %"if.then.2", label %"if.end.2", !dbg !158
if.then.2:
  %".19" = sub i64 0, 1, !dbg !159
  %".20" = trunc i64 %".19" to i32 , !dbg !159
  ret i32 %".20", !dbg !159
if.end.2:
  %".22" = load i64, i64* %"size", !dbg !160
  %".23" = sub i64 %".22", 1, !dbg !160
  %".24" = load i64, i64* %"size", !dbg !160
  %".25" = sub i64 %".24", 1, !dbg !160
  %".26" = call i64 @"llvm.ctlz.i64"(i64 %".25", i1 0), !dbg !160
  %".27" = trunc i64 %".26" to i8 , !dbg !160
  %".28" = zext i8 %".27" to i32 , !dbg !161
  %".29" = sext i32 %".28" to i64 , !dbg !161
  %".30" = sub i64 64, %".29", !dbg !161
  %".31" = sub i64 %".30", 4, !dbg !161
  %".32" = trunc i64 %".31" to i32 , !dbg !161
  ret i32 %".32", !dbg !161
}

define i32 @"bin_init"(%"struct.ritz_module_1.SizeBin"* %"bin.arg", i64 %"block_size.arg") !dbg !33
{
entry:
  %"bin" = alloca %"struct.ritz_module_1.SizeBin"*
  store %"struct.ritz_module_1.SizeBin"* %"bin.arg", %"struct.ritz_module_1.SizeBin"** %"bin"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.SizeBin"** %"bin", metadata !164, metadata !7), !dbg !165
  %"block_size" = alloca i64
  store i64 %"block_size.arg", i64* %"block_size"
  call void @"llvm.dbg.declare"(metadata i64* %"block_size", metadata !166, metadata !7), !dbg !165
  %".8" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !167
  %".9" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".8", i32 0, i32 0 , !dbg !167
  %".10" = bitcast i8* null to %"struct.ritz_module_1.FreeNode"* , !dbg !167
  store %"struct.ritz_module_1.FreeNode"* %".10", %"struct.ritz_module_1.FreeNode"** %".9", !dbg !167
  %".12" = load i64, i64* %"block_size", !dbg !168
  %".13" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !168
  %".14" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".13", i32 0, i32 1 , !dbg !168
  store i64 %".12", i64* %".14", !dbg !168
  %".16" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !169
  %".17" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".16", i32 0, i32 2 , !dbg !169
  store i8* null, i8** %".17", !dbg !169
  %".19" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !170
  %".20" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".19", i32 0, i32 3 , !dbg !170
  store i64 0, i64* %".20", !dbg !170
  %".22" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !171
  %".23" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".22", i32 0, i32 4 , !dbg !171
  store i64 0, i64* %".23", !dbg !171
  ret i32 0, !dbg !171
}

define i32 @"bin_new_slab"(%"struct.ritz_module_1.SizeBin"* %"bin.arg") !dbg !34
{
entry:
  %"bin" = alloca %"struct.ritz_module_1.SizeBin"*
  store %"struct.ritz_module_1.SizeBin"* %"bin.arg", %"struct.ritz_module_1.SizeBin"** %"bin"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.SizeBin"** %"bin", metadata !172, metadata !7), !dbg !173
  %".5" = add i32 1, 2, !dbg !175
  %".6" = add i32 2, 32, !dbg !175
  %".7" = sub i64 0, 1, !dbg !175
  %".8" = trunc i64 %".7" to i32 , !dbg !175
  %".9" = call i8* @"sys_mmap"(i64 0, i64 65536, i32 %".5", i32 %".6", i32 %".8", i64 0), !dbg !175
  %".10" = sub i64 0, 1, !dbg !176
  %".11" = inttoptr i64 %".10" to i8* , !dbg !176
  %".12" = icmp eq i8* %".9", %".11" , !dbg !176
  br i1 %".12", label %"if.then", label %"if.end", !dbg !176
if.then:
  %".14" = sub i64 0, 1, !dbg !177
  %".15" = trunc i64 %".14" to i32 , !dbg !177
  ret i32 %".15", !dbg !177
if.end:
  %".17" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !178
  %".18" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".17", i32 0, i32 2 , !dbg !178
  store i8* %".9", i8** %".18", !dbg !178
  %".20" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !179
  %".21" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".20", i32 0, i32 3 , !dbg !179
  store i64 0, i64* %".21", !dbg !179
  %".23" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !180
  %".24" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".23", i32 0, i32 4 , !dbg !180
  store i64 65536, i64* %".24", !dbg !180
  %".26" = trunc i64 0 to i32 , !dbg !181
  ret i32 %".26", !dbg !181
}

define i8* @"bin_alloc"(%"struct.ritz_module_1.SizeBin"* %"bin.arg", i32 %"class.arg") !dbg !35
{
entry:
  %"bin" = alloca %"struct.ritz_module_1.SizeBin"*
  store %"struct.ritz_module_1.SizeBin"* %"bin.arg", %"struct.ritz_module_1.SizeBin"** %"bin"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.SizeBin"** %"bin", metadata !182, metadata !7), !dbg !183
  %"class" = alloca i32
  store i32 %"class.arg", i32* %"class"
  call void @"llvm.dbg.declare"(metadata i32* %"class", metadata !184, metadata !7), !dbg !183
  %".8" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !185
  %".9" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".8", i32 0, i32 0 , !dbg !185
  %".10" = load %"struct.ritz_module_1.FreeNode"*, %"struct.ritz_module_1.FreeNode"** %".9", !dbg !185
  %".11" = icmp ne %"struct.ritz_module_1.FreeNode"* %".10", null , !dbg !185
  br i1 %".11", label %"if.then", label %"if.end", !dbg !185
if.then:
  %".13" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !186
  %".14" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".13", i32 0, i32 0 , !dbg !186
  %".15" = load %"struct.ritz_module_1.FreeNode"*, %"struct.ritz_module_1.FreeNode"** %".14", !dbg !186
  %".16" = getelementptr %"struct.ritz_module_1.FreeNode", %"struct.ritz_module_1.FreeNode"* %".15", i32 0, i32 0 , !dbg !187
  %".17" = load %"struct.ritz_module_1.FreeNode"*, %"struct.ritz_module_1.FreeNode"** %".16", !dbg !187
  %".18" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !187
  %".19" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".18", i32 0, i32 0 , !dbg !187
  store %"struct.ritz_module_1.FreeNode"* %".17", %"struct.ritz_module_1.FreeNode"** %".19", !dbg !187
  %".21" = ptrtoint %"struct.ritz_module_1.FreeNode"* %".15" to i64 , !dbg !188
  %".22" = sub i64 %".21", 16, !dbg !188
  %".23" = inttoptr i64 %".22" to %"struct.ritz_module_1.BlockHeader"* , !dbg !188
  %".24" = load i32, i32* %"class", !dbg !189
  %".25" = sext i32 %".24" to i64 , !dbg !189
  %".26" = getelementptr %"struct.ritz_module_1.BlockHeader", %"struct.ritz_module_1.BlockHeader"* %".23", i32 0, i32 0 , !dbg !189
  store i64 %".25", i64* %".26", !dbg !189
  %".28" = bitcast %"struct.ritz_module_1.FreeNode"* %".15" to i8* , !dbg !190
  ret i8* %".28", !dbg !190
if.end:
  %".30" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !191
  %".31" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".30", i32 0, i32 2 , !dbg !191
  %".32" = load i8*, i8** %".31", !dbg !191
  %".33" = icmp eq i8* %".32", null , !dbg !191
  br i1 %".33", label %"or.merge", label %"or.right", !dbg !191
or.right:
  %".35" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !191
  %".36" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".35", i32 0, i32 3 , !dbg !191
  %".37" = load i64, i64* %".36", !dbg !191
  %".38" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !191
  %".39" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".38", i32 0, i32 1 , !dbg !191
  %".40" = load i64, i64* %".39", !dbg !191
  %".41" = add i64 %".37", %".40", !dbg !191
  %".42" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !191
  %".43" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".42", i32 0, i32 4 , !dbg !191
  %".44" = load i64, i64* %".43", !dbg !191
  %".45" = icmp sgt i64 %".41", %".44" , !dbg !191
  br label %"or.merge", !dbg !191
or.merge:
  %".47" = phi  i1 [1, %"if.end"], [%".45", %"or.right"] , !dbg !191
  br i1 %".47", label %"if.then.1", label %"if.end.1", !dbg !191
if.then.1:
  %".49" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !191
  %".50" = call i32 @"bin_new_slab"(%"struct.ritz_module_1.SizeBin"* %".49"), !dbg !191
  %".51" = sext i32 %".50" to i64 , !dbg !191
  %".52" = icmp ne i64 %".51", 0 , !dbg !191
  br i1 %".52", label %"if.then.2", label %"if.end.2", !dbg !191
if.end.1:
  %".56" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !193
  %".57" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".56", i32 0, i32 2 , !dbg !193
  %".58" = load i8*, i8** %".57", !dbg !193
  %".59" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !193
  %".60" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".59", i32 0, i32 3 , !dbg !193
  %".61" = load i64, i64* %".60", !dbg !193
  %".62" = getelementptr i8, i8* %".58", i64 %".61" , !dbg !193
  %".63" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !194
  %".64" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".63", i32 0, i32 3 , !dbg !194
  %".65" = load i64, i64* %".64", !dbg !194
  %".66" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !194
  %".67" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".66", i32 0, i32 1 , !dbg !194
  %".68" = load i64, i64* %".67", !dbg !194
  %".69" = add i64 %".65", %".68", !dbg !194
  %".70" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !194
  %".71" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".70", i32 0, i32 3 , !dbg !194
  store i64 %".69", i64* %".71", !dbg !194
  %".73" = bitcast i8* %".62" to %"struct.ritz_module_1.BlockHeader"* , !dbg !195
  %".74" = load i32, i32* %"class", !dbg !196
  %".75" = sext i32 %".74" to i64 , !dbg !196
  %".76" = getelementptr %"struct.ritz_module_1.BlockHeader", %"struct.ritz_module_1.BlockHeader"* %".73", i32 0, i32 0 , !dbg !196
  store i64 %".75", i64* %".76", !dbg !196
  %".78" = getelementptr i8, i8* %".62", i64 16 , !dbg !197
  ret i8* %".78", !dbg !197
if.then.2:
  ret i8* null, !dbg !192
if.end.2:
  br label %"if.end.1", !dbg !192
}

define i32 @"bin_free"(%"struct.ritz_module_1.SizeBin"* %"bin.arg", i8* %"ptr.arg") !dbg !36
{
entry:
  %"bin" = alloca %"struct.ritz_module_1.SizeBin"*
  store %"struct.ritz_module_1.SizeBin"* %"bin.arg", %"struct.ritz_module_1.SizeBin"** %"bin"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.SizeBin"** %"bin", metadata !198, metadata !7), !dbg !199
  %"ptr" = alloca i8*
  store i8* %"ptr.arg", i8** %"ptr"
  call void @"llvm.dbg.declare"(metadata i8** %"ptr", metadata !200, metadata !7), !dbg !199
  %".8" = load i8*, i8** %"ptr", !dbg !201
  %".9" = bitcast i8* %".8" to %"struct.ritz_module_1.FreeNode"* , !dbg !201
  %".10" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !202
  %".11" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".10", i32 0, i32 0 , !dbg !202
  %".12" = load %"struct.ritz_module_1.FreeNode"*, %"struct.ritz_module_1.FreeNode"** %".11", !dbg !202
  %".13" = getelementptr %"struct.ritz_module_1.FreeNode", %"struct.ritz_module_1.FreeNode"* %".9", i32 0, i32 0 , !dbg !202
  store %"struct.ritz_module_1.FreeNode"* %".12", %"struct.ritz_module_1.FreeNode"** %".13", !dbg !202
  %".15" = load %"struct.ritz_module_1.SizeBin"*, %"struct.ritz_module_1.SizeBin"** %"bin", !dbg !203
  %".16" = getelementptr %"struct.ritz_module_1.SizeBin", %"struct.ritz_module_1.SizeBin"* %".15", i32 0, i32 0 , !dbg !203
  store %"struct.ritz_module_1.FreeNode"* %".9", %"struct.ritz_module_1.FreeNode"** %".16", !dbg !203
  ret i32 0, !dbg !203
}

define i32 @"alloc_init"() !dbg !37
{
entry:
  %"i" = alloca i32, !dbg !206
  %".2" = load %"struct.ritz_module_1.GlobalAlloc", %"struct.ritz_module_1.GlobalAlloc"* @"g_alloc", !dbg !204
  %".3" = extractvalue %"struct.ritz_module_1.GlobalAlloc" %".2", 1 , !dbg !204
  %".4" = sext i32 %".3" to i64 , !dbg !204
  %".5" = icmp ne i64 %".4", 0 , !dbg !204
  br i1 %".5", label %"if.then", label %"if.end", !dbg !204
if.then:
  ret i32 0, !dbg !205
if.end:
  store i32 0, i32* %"i", !dbg !206
  br label %"for.cond", !dbg !206
for.cond:
  %".10" = load i32, i32* %"i", !dbg !206
  %".11" = icmp slt i32 %".10", 9 , !dbg !206
  br i1 %".11", label %"for.body", label %"for.end", !dbg !206
for.body:
  %".13" = load i32, i32* %"i", !dbg !206
  %".14" = getelementptr %"struct.ritz_module_1.GlobalAlloc", %"struct.ritz_module_1.GlobalAlloc"* @"g_alloc", i32 0, i32 0 , !dbg !206
  %".15" = getelementptr [9 x %"struct.ritz_module_1.SizeBin"], [9 x %"struct.ritz_module_1.SizeBin"]* %".14", i32 0, i32 %".13" , !dbg !206
  %".16" = load i32, i32* %"i", !dbg !206
  %".17" = call i64 @"get_block_size"(i32 %".16"), !dbg !206
  %".18" = call i32 @"bin_init"(%"struct.ritz_module_1.SizeBin"* %".15", i64 %".17"), !dbg !206
  br label %"for.incr", !dbg !206
for.incr:
  %".20" = load i32, i32* %"i", !dbg !206
  %".21" = add i32 %".20", 1, !dbg !206
  store i32 %".21", i32* %"i", !dbg !206
  br label %"for.cond", !dbg !206
for.end:
  %".24" = load %"struct.ritz_module_1.GlobalAlloc", %"struct.ritz_module_1.GlobalAlloc"* @"g_alloc", !dbg !207
  %".25" = getelementptr %"struct.ritz_module_1.GlobalAlloc", %"struct.ritz_module_1.GlobalAlloc"* @"g_alloc", i32 0, i32 1 , !dbg !207
  %".26" = trunc i64 1 to i32 , !dbg !207
  store i32 %".26", i32* %".25", !dbg !207
  ret i32 0, !dbg !207
}

define i8* @"malloc"(i64 %"size.arg") !dbg !38
{
entry:
  %"size" = alloca i64
  store i64 %"size.arg", i64* %"size"
  call void @"llvm.dbg.declare"(metadata i64* %"size", metadata !208, metadata !7), !dbg !209
  %".5" = load i64, i64* %"size", !dbg !210
  %".6" = icmp sle i64 %".5", 0 , !dbg !210
  br i1 %".6", label %"if.then", label %"if.end", !dbg !210
if.then:
  ret i8* null, !dbg !211
if.end:
  %".9" = call i32 @"alloc_init"(), !dbg !212
  %".10" = load i64, i64* %"size", !dbg !213
  %".11" = call i32 @"get_size_class"(i64 %".10"), !dbg !213
  %".12" = sext i32 %".11" to i64 , !dbg !214
  %".13" = icmp slt i64 %".12", 0 , !dbg !214
  br i1 %".13", label %"if.then.1", label %"if.end.1", !dbg !214
if.then.1:
  %".15" = load i64, i64* %"size", !dbg !215
  %".16" = add i64 %".15", 16, !dbg !215
  %".17" = add i64 %".16", 4096, !dbg !216
  %".18" = sub i64 %".17", 1, !dbg !216
  %".19" = sdiv i64 %".18", 4096, !dbg !216
  %".20" = mul i64 %".19", 4096, !dbg !217
  %".21" = add i32 1, 2, !dbg !218
  %".22" = add i32 2, 32, !dbg !218
  %".23" = sub i64 0, 1, !dbg !218
  %".24" = trunc i64 %".23" to i32 , !dbg !218
  %".25" = call i8* @"sys_mmap"(i64 0, i64 %".20", i32 %".21", i32 %".22", i32 %".24", i64 0), !dbg !218
  %".26" = sub i64 0, 1, !dbg !219
  %".27" = inttoptr i64 %".26" to i8* , !dbg !219
  %".28" = icmp eq i8* %".25", %".27" , !dbg !219
  br i1 %".28", label %"if.then.2", label %"if.end.2", !dbg !219
if.end.1:
  %".37" = getelementptr %"struct.ritz_module_1.GlobalAlloc", %"struct.ritz_module_1.GlobalAlloc"* @"g_alloc", i32 0, i32 0 , !dbg !224
  %".38" = getelementptr [9 x %"struct.ritz_module_1.SizeBin"], [9 x %"struct.ritz_module_1.SizeBin"]* %".37", i32 0, i32 %".11" , !dbg !224
  %".39" = call i8* @"bin_alloc"(%"struct.ritz_module_1.SizeBin"* %".38", i32 %".11"), !dbg !224
  ret i8* %".39", !dbg !224
if.then.2:
  ret i8* null, !dbg !220
if.end.2:
  %".31" = bitcast i8* %".25" to %"struct.ritz_module_1.BlockHeader"* , !dbg !221
  %".32" = sub i64 0, %".20", !dbg !222
  %".33" = getelementptr %"struct.ritz_module_1.BlockHeader", %"struct.ritz_module_1.BlockHeader"* %".31", i32 0, i32 0 , !dbg !222
  store i64 %".32", i64* %".33", !dbg !222
  %".35" = getelementptr i8, i8* %".25", i64 16 , !dbg !223
  ret i8* %".35", !dbg !223
}

define i32 @"free"(i8* %"ptr.arg") !dbg !39
{
entry:
  %"ptr" = alloca i8*
  store i8* %"ptr.arg", i8** %"ptr"
  call void @"llvm.dbg.declare"(metadata i8** %"ptr", metadata !225, metadata !7), !dbg !226
  %".5" = load i8*, i8** %"ptr", !dbg !227
  %".6" = icmp eq i8* %".5", null , !dbg !227
  br i1 %".6", label %"if.then", label %"if.end", !dbg !227
if.then:
  ret i32 0, !dbg !228
if.end:
  %".9" = load i8*, i8** %"ptr", !dbg !229
  %".10" = ptrtoint i8* %".9" to i64 , !dbg !229
  %".11" = sub i64 %".10", 16, !dbg !229
  %".12" = inttoptr i64 %".11" to %"struct.ritz_module_1.BlockHeader"* , !dbg !229
  %".13" = getelementptr %"struct.ritz_module_1.BlockHeader", %"struct.ritz_module_1.BlockHeader"* %".12", i32 0, i32 0 , !dbg !230
  %".14" = load i64, i64* %".13", !dbg !230
  %".15" = icmp slt i64 %".14", 0 , !dbg !231
  br i1 %".15", label %"if.then.1", label %"if.end.1", !dbg !231
if.then.1:
  %".17" = load i8*, i8** %"ptr", !dbg !232
  %".18" = ptrtoint i8* %".17" to i64 , !dbg !232
  %".19" = sub i64 %".18", 16, !dbg !232
  %".20" = inttoptr i64 %".19" to i8* , !dbg !232
  %".21" = sub i64 0, %".14", !dbg !233
  %".22" = call i32 @"sys_munmap"(i8* %".20", i64 %".21"), !dbg !234
  ret i32 0, !dbg !235
if.end.1:
  %".24" = trunc i64 %".14" to i32 , !dbg !236
  %".25" = sext i32 %".24" to i64 , !dbg !237
  %".26" = icmp sge i64 %".25", 0 , !dbg !237
  br i1 %".26", label %"and.right", label %"and.merge", !dbg !237
and.right:
  %".28" = icmp slt i32 %".24", 9 , !dbg !237
  br label %"and.merge", !dbg !237
and.merge:
  %".30" = phi  i1 [0, %"if.end.1"], [%".28", %"and.right"] , !dbg !237
  br i1 %".30", label %"if.then.2", label %"if.end.2", !dbg !237
if.then.2:
  %".32" = getelementptr %"struct.ritz_module_1.GlobalAlloc", %"struct.ritz_module_1.GlobalAlloc"* @"g_alloc", i32 0, i32 0 , !dbg !237
  %".33" = getelementptr [9 x %"struct.ritz_module_1.SizeBin"], [9 x %"struct.ritz_module_1.SizeBin"]* %".32", i32 0, i32 %".24" , !dbg !237
  %".34" = load i8*, i8** %"ptr", !dbg !237
  %".35" = call i32 @"bin_free"(%"struct.ritz_module_1.SizeBin"* %".33", i8* %".34"), !dbg !237
  br label %"if.end.2", !dbg !237
if.end.2:
  ret i32 0, !dbg !237
}

define i8* @"realloc"(i8* %"ptr.arg", i64 %"new_size.arg") !dbg !40
{
entry:
  %"ptr" = alloca i8*
  %"old_usable.addr" = alloca i64, !dbg !248
  %"copy_size.addr" = alloca i64, !dbg !260
  store i8* %"ptr.arg", i8** %"ptr"
  call void @"llvm.dbg.declare"(metadata i8** %"ptr", metadata !238, metadata !7), !dbg !239
  %"new_size" = alloca i64
  store i64 %"new_size.arg", i64* %"new_size"
  call void @"llvm.dbg.declare"(metadata i64* %"new_size", metadata !240, metadata !7), !dbg !239
  %".8" = load i8*, i8** %"ptr", !dbg !241
  %".9" = icmp eq i8* %".8", null , !dbg !241
  br i1 %".9", label %"if.then", label %"if.end", !dbg !241
if.then:
  %".11" = load i64, i64* %"new_size", !dbg !242
  %".12" = call i8* @"malloc"(i64 %".11"), !dbg !242
  ret i8* %".12", !dbg !242
if.end:
  %".14" = load i64, i64* %"new_size", !dbg !243
  %".15" = icmp sle i64 %".14", 0 , !dbg !243
  br i1 %".15", label %"if.then.1", label %"if.end.1", !dbg !243
if.then.1:
  %".17" = load i8*, i8** %"ptr", !dbg !244
  %".18" = call i32 @"free"(i8* %".17"), !dbg !244
  ret i8* null, !dbg !245
if.end.1:
  %".20" = load i8*, i8** %"ptr", !dbg !246
  %".21" = ptrtoint i8* %".20" to i64 , !dbg !246
  %".22" = sub i64 %".21", 16, !dbg !246
  %".23" = inttoptr i64 %".22" to %"struct.ritz_module_1.BlockHeader"* , !dbg !246
  %".24" = getelementptr %"struct.ritz_module_1.BlockHeader", %"struct.ritz_module_1.BlockHeader"* %".23", i32 0, i32 0 , !dbg !247
  %".25" = load i64, i64* %".24", !dbg !247
  store i64 0, i64* %"old_usable.addr", !dbg !248
  call void @"llvm.dbg.declare"(metadata i64* %"old_usable.addr", metadata !249, metadata !7), !dbg !250
  %".28" = icmp slt i64 %".25", 0 , !dbg !251
  br i1 %".28", label %"if.then.2", label %"if.else", !dbg !251
if.then.2:
  %".30" = sub i64 0, %".25", !dbg !252
  %".31" = sub i64 %".30", 16, !dbg !252
  store i64 %".31", i64* %"old_usable.addr", !dbg !252
  br label %"if.end.2", !dbg !253
if.else:
  %".33" = trunc i64 %".25" to i32 , !dbg !253
  %".34" = call i64 @"get_block_size"(i32 %".33"), !dbg !253
  %".35" = sub i64 %".34", 16, !dbg !253
  store i64 %".35", i64* %"old_usable.addr", !dbg !253
  br label %"if.end.2", !dbg !253
if.end.2:
  %".39" = load i64, i64* %"new_size", !dbg !254
  %".40" = call i32 @"get_size_class"(i64 %".39"), !dbg !254
  %".41" = sext i32 %".40" to i64 , !dbg !255
  %".42" = icmp sge i64 %".41", 0 , !dbg !255
  br i1 %".42", label %"and.right", label %"and.merge", !dbg !255
and.right:
  %".44" = trunc i64 %".25" to i32 , !dbg !255
  %".45" = icmp eq i32 %".40", %".44" , !dbg !255
  br label %"and.merge", !dbg !255
and.merge:
  %".47" = phi  i1 [0, %"if.end.2"], [%".45", %"and.right"] , !dbg !255
  br i1 %".47", label %"if.then.3", label %"if.end.3", !dbg !255
if.then.3:
  %".49" = load i8*, i8** %"ptr", !dbg !256
  ret i8* %".49", !dbg !256
if.end.3:
  %".51" = load i64, i64* %"new_size", !dbg !257
  %".52" = call i8* @"malloc"(i64 %".51"), !dbg !257
  %".53" = icmp eq i8* %".52", null , !dbg !258
  br i1 %".53", label %"if.then.4", label %"if.end.4", !dbg !258
if.then.4:
  ret i8* null, !dbg !259
if.end.4:
  %".56" = load i64, i64* %"old_usable.addr", !dbg !260
  store i64 %".56", i64* %"copy_size.addr", !dbg !260
  call void @"llvm.dbg.declare"(metadata i64* %"copy_size.addr", metadata !261, metadata !7), !dbg !262
  %".59" = load i64, i64* %"new_size", !dbg !263
  %".60" = load i64, i64* %"copy_size.addr", !dbg !263
  %".61" = icmp slt i64 %".59", %".60" , !dbg !263
  br i1 %".61", label %"if.then.5", label %"if.end.5", !dbg !263
if.then.5:
  %".63" = load i64, i64* %"new_size", !dbg !264
  store i64 %".63", i64* %"copy_size.addr", !dbg !264
  br label %"if.end.5", !dbg !264
if.end.5:
  %".66" = load i8*, i8** %"ptr", !dbg !265
  %".67" = load i64, i64* %"copy_size.addr", !dbg !265
  %".68" = call i8* @"memcpy"(i8* %".52", i8* %".66", i64 %".67"), !dbg !265
  %".69" = load i8*, i8** %"ptr", !dbg !266
  %".70" = call i32 @"free"(i8* %".69"), !dbg !266
  ret i8* %".52", !dbg !267
}

define i8* @"calloc"(i64 %"count.arg", i64 %"size.arg") !dbg !41
{
entry:
  %"count" = alloca i64
  store i64 %"count.arg", i64* %"count"
  call void @"llvm.dbg.declare"(metadata i64* %"count", metadata !268, metadata !7), !dbg !269
  %"size" = alloca i64
  store i64 %"size.arg", i64* %"size"
  call void @"llvm.dbg.declare"(metadata i64* %"size", metadata !270, metadata !7), !dbg !269
  %".8" = load i64, i64* %"count", !dbg !271
  %".9" = load i64, i64* %"size", !dbg !271
  %".10" = mul i64 %".8", %".9", !dbg !271
  %".11" = call i8* @"malloc"(i64 %".10"), !dbg !272
  %".12" = icmp ne i8* %".11", null , !dbg !273
  br i1 %".12", label %"if.then", label %"if.end", !dbg !273
if.then:
  %".14" = call i32 @"memzero"(i8* %".11", i64 %".10"), !dbg !273
  br label %"if.end", !dbg !273
if.end:
  ret i8* %".11", !dbg !274
}

declare i64 @"llvm.ctlz.i64"(i64 %".1", i1 %".2")

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/ritz/ritzlib", filename: "memory.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 32, name: "arena_new", scopeLine: 32, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 46, name: "arena_default", scopeLine: 46, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 51, name: "arena_alloc", scopeLine: 51, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 67, name: "arena_alloc_zero", scopeLine: 67, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 81, name: "arena_alloc_array", scopeLine: 81, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 85, name: "arena_reset", scopeLine: 85, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 89, name: "arena_destroy", scopeLine: 89, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 97, name: "arena_used", scopeLine: 97, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 101, name: "arena_remaining", scopeLine: 101, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 105, name: "arena_valid", scopeLine: 105, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 117, name: "heap_alloc", scopeLine: 117, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 123, name: "heap_free", scopeLine: 123, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 130, name: "heap_realloc", scopeLine: 130, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 162, name: "memzero", scopeLine: 162, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 220, name: "get_block_size", scopeLine: 220, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 227, name: "get_size_class", scopeLine: 227, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 240, name: "bin_init", scopeLine: 240, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 248, name: "bin_new_slab", scopeLine: 248, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 260, name: "bin_alloc", scopeLine: 260, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 286, name: "bin_free", scopeLine: 286, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 293, name: "alloc_init", scopeLine: 293, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 307, name: "malloc", scopeLine: 307, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 336, name: "free", scopeLine: 336, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 357, name: "realloc", scopeLine: 357, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 400, name: "calloc", scopeLine: 400, type: !4, unit: !1)
!42 = !DILocalVariable(file: !0, line: 32, name: "size", scope: !17, type: !11)
!43 = !DILocation(column: 1, line: 32, scope: !17)
!44 = !DILocation(column: 5, line: 33, scope: !17)
!45 = !DICompositeType(align: 64, file: !0, name: "Arena", size: 192, tag: DW_TAG_structure_type)
!46 = !DILocalVariable(file: !0, line: 33, name: "a", scope: !17, type: !45)
!47 = !DILocation(column: 1, line: 33, scope: !17)
!48 = !DILocation(column: 5, line: 34, scope: !17)
!49 = !DILocation(column: 5, line: 35, scope: !17)
!50 = !DILocation(column: 9, line: 37, scope: !17)
!51 = !DILocation(column: 9, line: 38, scope: !17)
!52 = !DILocation(column: 9, line: 39, scope: !17)
!53 = !DILocation(column: 9, line: 40, scope: !17)
!54 = !DILocation(column: 5, line: 41, scope: !17)
!55 = !DILocation(column: 5, line: 42, scope: !17)
!56 = !DILocation(column: 5, line: 43, scope: !17)
!57 = !DILocation(column: 5, line: 47, scope: !18)
!58 = !DIDerivedType(baseType: !45, size: 64, tag: DW_TAG_pointer_type)
!59 = !DILocalVariable(file: !0, line: 51, name: "a", scope: !19, type: !58)
!60 = !DILocation(column: 1, line: 51, scope: !19)
!61 = !DILocalVariable(file: !0, line: 51, name: "size", scope: !19, type: !11)
!62 = !DILocation(column: 5, line: 52, scope: !19)
!63 = !DILocation(column: 9, line: 53, scope: !19)
!64 = !DILocation(column: 5, line: 56, scope: !19)
!65 = !DILocation(column: 5, line: 58, scope: !19)
!66 = !DILocation(column: 9, line: 60, scope: !19)
!67 = !DILocation(column: 5, line: 62, scope: !19)
!68 = !DILocation(column: 5, line: 63, scope: !19)
!69 = !DILocation(column: 5, line: 64, scope: !19)
!70 = !DILocalVariable(file: !0, line: 67, name: "a", scope: !20, type: !58)
!71 = !DILocation(column: 1, line: 67, scope: !20)
!72 = !DILocalVariable(file: !0, line: 67, name: "size", scope: !20, type: !11)
!73 = !DILocation(column: 5, line: 68, scope: !20)
!74 = !DILocation(column: 5, line: 69, scope: !20)
!75 = !DILocation(column: 9, line: 70, scope: !20)
!76 = !DILocation(column: 5, line: 73, scope: !20)
!77 = !DILocalVariable(file: !0, line: 73, name: "i", scope: !20, type: !11)
!78 = !DILocation(column: 1, line: 73, scope: !20)
!79 = !DILocation(column: 5, line: 74, scope: !20)
!80 = !DILocation(column: 9, line: 75, scope: !20)
!81 = !DILocation(column: 9, line: 76, scope: !20)
!82 = !DILocation(column: 5, line: 78, scope: !20)
!83 = !DILocalVariable(file: !0, line: 81, name: "a", scope: !21, type: !58)
!84 = !DILocation(column: 1, line: 81, scope: !21)
!85 = !DILocalVariable(file: !0, line: 81, name: "count", scope: !21, type: !11)
!86 = !DILocalVariable(file: !0, line: 81, name: "elem_size", scope: !21, type: !11)
!87 = !DILocation(column: 5, line: 82, scope: !21)
!88 = !DILocalVariable(file: !0, line: 85, name: "a", scope: !22, type: !58)
!89 = !DILocation(column: 1, line: 85, scope: !22)
!90 = !DILocation(column: 5, line: 86, scope: !22)
!91 = !DILocalVariable(file: !0, line: 89, name: "a", scope: !23, type: !58)
!92 = !DILocation(column: 1, line: 89, scope: !23)
!93 = !DILocation(column: 5, line: 90, scope: !23)
!94 = !DILocation(column: 5, line: 92, scope: !23)
!95 = !DILocation(column: 5, line: 93, scope: !23)
!96 = !DILocation(column: 5, line: 94, scope: !23)
!97 = !DILocalVariable(file: !0, line: 97, name: "a", scope: !24, type: !58)
!98 = !DILocation(column: 1, line: 97, scope: !24)
!99 = !DILocation(column: 5, line: 98, scope: !24)
!100 = !DILocalVariable(file: !0, line: 101, name: "a", scope: !25, type: !58)
!101 = !DILocation(column: 1, line: 101, scope: !25)
!102 = !DILocation(column: 5, line: 102, scope: !25)
!103 = !DILocalVariable(file: !0, line: 105, name: "a", scope: !26, type: !58)
!104 = !DILocation(column: 1, line: 105, scope: !26)
!105 = !DILocation(column: 5, line: 106, scope: !26)
!106 = !DILocation(column: 9, line: 107, scope: !26)
!107 = !DILocation(column: 5, line: 108, scope: !26)
!108 = !DILocalVariable(file: !0, line: 117, name: "size", scope: !27, type: !11)
!109 = !DILocation(column: 1, line: 117, scope: !27)
!110 = !DILocation(column: 5, line: 118, scope: !27)
!111 = !DILocation(column: 9, line: 119, scope: !27)
!112 = !DILocation(column: 5, line: 120, scope: !27)
!113 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!114 = !DILocalVariable(file: !0, line: 123, name: "ptr", scope: !28, type: !113)
!115 = !DILocation(column: 1, line: 123, scope: !28)
!116 = !DILocalVariable(file: !0, line: 123, name: "size", scope: !28, type: !11)
!117 = !DILocation(column: 5, line: 124, scope: !28)
!118 = !DILocation(column: 9, line: 125, scope: !28)
!119 = !DILocation(column: 5, line: 126, scope: !28)
!120 = !DILocalVariable(file: !0, line: 130, name: "ptr", scope: !29, type: !113)
!121 = !DILocation(column: 1, line: 130, scope: !29)
!122 = !DILocalVariable(file: !0, line: 130, name: "old_size", scope: !29, type: !11)
!123 = !DILocalVariable(file: !0, line: 130, name: "new_size", scope: !29, type: !11)
!124 = !DILocation(column: 5, line: 131, scope: !29)
!125 = !DILocation(column: 9, line: 132, scope: !29)
!126 = !DILocation(column: 9, line: 134, scope: !29)
!127 = !DILocation(column: 5, line: 136, scope: !29)
!128 = !DILocation(column: 5, line: 137, scope: !29)
!129 = !DILocation(column: 9, line: 138, scope: !29)
!130 = !DILocation(column: 5, line: 141, scope: !29)
!131 = !DILocalVariable(file: !0, line: 141, name: "copy_size", scope: !29, type: !11)
!132 = !DILocation(column: 1, line: 141, scope: !29)
!133 = !DILocation(column: 5, line: 142, scope: !29)
!134 = !DILocation(column: 9, line: 143, scope: !29)
!135 = !DILocation(column: 5, line: 145, scope: !29)
!136 = !DILocalVariable(file: !0, line: 145, name: "i", scope: !29, type: !11)
!137 = !DILocation(column: 1, line: 145, scope: !29)
!138 = !DILocation(column: 5, line: 146, scope: !29)
!139 = !DILocation(column: 9, line: 147, scope: !29)
!140 = !DILocation(column: 9, line: 148, scope: !29)
!141 = !DILocation(column: 5, line: 151, scope: !29)
!142 = !DILocation(column: 5, line: 154, scope: !29)
!143 = !DILocalVariable(file: !0, line: 162, name: "dst", scope: !30, type: !113)
!144 = !DILocation(column: 1, line: 162, scope: !30)
!145 = !DILocalVariable(file: !0, line: 162, name: "n", scope: !30, type: !11)
!146 = !DILocation(column: 5, line: 163, scope: !30)
!147 = !DILocalVariable(file: !0, line: 220, name: "class", scope: !31, type: !10)
!148 = !DILocation(column: 1, line: 220, scope: !31)
!149 = !DILocation(column: 5, line: 221, scope: !31)
!150 = !DILocation(column: 9, line: 222, scope: !31)
!151 = !DILocation(column: 5, line: 223, scope: !31)
!152 = !DILocalVariable(file: !0, line: 227, name: "size", scope: !32, type: !11)
!153 = !DILocation(column: 1, line: 227, scope: !32)
!154 = !DILocation(column: 5, line: 228, scope: !32)
!155 = !DILocation(column: 9, line: 229, scope: !32)
!156 = !DILocation(column: 5, line: 230, scope: !32)
!157 = !DILocation(column: 9, line: 231, scope: !32)
!158 = !DILocation(column: 5, line: 232, scope: !32)
!159 = !DILocation(column: 9, line: 233, scope: !32)
!160 = !DILocation(column: 5, line: 236, scope: !32)
!161 = !DILocation(column: 5, line: 237, scope: !32)
!162 = !DICompositeType(align: 64, file: !0, name: "SizeBin", size: 320, tag: DW_TAG_structure_type)
!163 = !DIDerivedType(baseType: !162, size: 64, tag: DW_TAG_pointer_type)
!164 = !DILocalVariable(file: !0, line: 240, name: "bin", scope: !33, type: !163)
!165 = !DILocation(column: 1, line: 240, scope: !33)
!166 = !DILocalVariable(file: !0, line: 240, name: "block_size", scope: !33, type: !11)
!167 = !DILocation(column: 5, line: 241, scope: !33)
!168 = !DILocation(column: 5, line: 242, scope: !33)
!169 = !DILocation(column: 5, line: 243, scope: !33)
!170 = !DILocation(column: 5, line: 244, scope: !33)
!171 = !DILocation(column: 5, line: 245, scope: !33)
!172 = !DILocalVariable(file: !0, line: 248, name: "bin", scope: !34, type: !163)
!173 = !DILocation(column: 1, line: 248, scope: !34)
!174 = !DILocation(column: 5, line: 250, scope: !34)
!175 = !DILocation(column: 5, line: 251, scope: !34)
!176 = !DILocation(column: 5, line: 252, scope: !34)
!177 = !DILocation(column: 9, line: 253, scope: !34)
!178 = !DILocation(column: 5, line: 254, scope: !34)
!179 = !DILocation(column: 5, line: 255, scope: !34)
!180 = !DILocation(column: 5, line: 256, scope: !34)
!181 = !DILocation(column: 5, line: 257, scope: !34)
!182 = !DILocalVariable(file: !0, line: 260, name: "bin", scope: !35, type: !163)
!183 = !DILocation(column: 1, line: 260, scope: !35)
!184 = !DILocalVariable(file: !0, line: 260, name: "class", scope: !35, type: !10)
!185 = !DILocation(column: 5, line: 262, scope: !35)
!186 = !DILocation(column: 9, line: 263, scope: !35)
!187 = !DILocation(column: 9, line: 264, scope: !35)
!188 = !DILocation(column: 9, line: 266, scope: !35)
!189 = !DILocation(column: 9, line: 267, scope: !35)
!190 = !DILocation(column: 9, line: 268, scope: !35)
!191 = !DILocation(column: 5, line: 271, scope: !35)
!192 = !DILocation(column: 13, line: 273, scope: !35)
!193 = !DILocation(column: 5, line: 275, scope: !35)
!194 = !DILocation(column: 5, line: 276, scope: !35)
!195 = !DILocation(column: 5, line: 279, scope: !35)
!196 = !DILocation(column: 5, line: 280, scope: !35)
!197 = !DILocation(column: 5, line: 283, scope: !35)
!198 = !DILocalVariable(file: !0, line: 286, name: "bin", scope: !36, type: !163)
!199 = !DILocation(column: 1, line: 286, scope: !36)
!200 = !DILocalVariable(file: !0, line: 286, name: "ptr", scope: !36, type: !113)
!201 = !DILocation(column: 5, line: 288, scope: !36)
!202 = !DILocation(column: 5, line: 289, scope: !36)
!203 = !DILocation(column: 5, line: 290, scope: !36)
!204 = !DILocation(column: 5, line: 294, scope: !37)
!205 = !DILocation(column: 9, line: 295, scope: !37)
!206 = !DILocation(column: 5, line: 297, scope: !37)
!207 = !DILocation(column: 5, line: 300, scope: !37)
!208 = !DILocalVariable(file: !0, line: 307, name: "size", scope: !38, type: !11)
!209 = !DILocation(column: 1, line: 307, scope: !38)
!210 = !DILocation(column: 5, line: 308, scope: !38)
!211 = !DILocation(column: 9, line: 309, scope: !38)
!212 = !DILocation(column: 5, line: 311, scope: !38)
!213 = !DILocation(column: 5, line: 313, scope: !38)
!214 = !DILocation(column: 5, line: 315, scope: !38)
!215 = !DILocation(column: 9, line: 317, scope: !38)
!216 = !DILocation(column: 9, line: 319, scope: !38)
!217 = !DILocation(column: 9, line: 320, scope: !38)
!218 = !DILocation(column: 9, line: 322, scope: !38)
!219 = !DILocation(column: 9, line: 323, scope: !38)
!220 = !DILocation(column: 13, line: 324, scope: !38)
!221 = !DILocation(column: 9, line: 327, scope: !38)
!222 = !DILocation(column: 9, line: 328, scope: !38)
!223 = !DILocation(column: 9, line: 330, scope: !38)
!224 = !DILocation(column: 5, line: 333, scope: !38)
!225 = !DILocalVariable(file: !0, line: 336, name: "ptr", scope: !39, type: !113)
!226 = !DILocation(column: 1, line: 336, scope: !39)
!227 = !DILocation(column: 5, line: 337, scope: !39)
!228 = !DILocation(column: 9, line: 338, scope: !39)
!229 = !DILocation(column: 5, line: 341, scope: !39)
!230 = !DILocation(column: 5, line: 342, scope: !39)
!231 = !DILocation(column: 5, line: 344, scope: !39)
!232 = !DILocation(column: 9, line: 346, scope: !39)
!233 = !DILocation(column: 9, line: 347, scope: !39)
!234 = !DILocation(column: 9, line: 348, scope: !39)
!235 = !DILocation(column: 9, line: 349, scope: !39)
!236 = !DILocation(column: 5, line: 352, scope: !39)
!237 = !DILocation(column: 5, line: 353, scope: !39)
!238 = !DILocalVariable(file: !0, line: 357, name: "ptr", scope: !40, type: !113)
!239 = !DILocation(column: 1, line: 357, scope: !40)
!240 = !DILocalVariable(file: !0, line: 357, name: "new_size", scope: !40, type: !11)
!241 = !DILocation(column: 5, line: 358, scope: !40)
!242 = !DILocation(column: 9, line: 359, scope: !40)
!243 = !DILocation(column: 5, line: 361, scope: !40)
!244 = !DILocation(column: 9, line: 362, scope: !40)
!245 = !DILocation(column: 9, line: 363, scope: !40)
!246 = !DILocation(column: 5, line: 366, scope: !40)
!247 = !DILocation(column: 5, line: 367, scope: !40)
!248 = !DILocation(column: 5, line: 369, scope: !40)
!249 = !DILocalVariable(file: !0, line: 369, name: "old_usable", scope: !40, type: !11)
!250 = !DILocation(column: 1, line: 369, scope: !40)
!251 = !DILocation(column: 5, line: 370, scope: !40)
!252 = !DILocation(column: 9, line: 372, scope: !40)
!253 = !DILocation(column: 9, line: 375, scope: !40)
!254 = !DILocation(column: 5, line: 378, scope: !40)
!255 = !DILocation(column: 5, line: 379, scope: !40)
!256 = !DILocation(column: 9, line: 380, scope: !40)
!257 = !DILocation(column: 5, line: 383, scope: !40)
!258 = !DILocation(column: 5, line: 384, scope: !40)
!259 = !DILocation(column: 9, line: 385, scope: !40)
!260 = !DILocation(column: 5, line: 388, scope: !40)
!261 = !DILocalVariable(file: !0, line: 388, name: "copy_size", scope: !40, type: !11)
!262 = !DILocation(column: 1, line: 388, scope: !40)
!263 = !DILocation(column: 5, line: 389, scope: !40)
!264 = !DILocation(column: 9, line: 390, scope: !40)
!265 = !DILocation(column: 5, line: 392, scope: !40)
!266 = !DILocation(column: 5, line: 395, scope: !40)
!267 = !DILocation(column: 5, line: 397, scope: !40)
!268 = !DILocalVariable(file: !0, line: 400, name: "count", scope: !41, type: !11)
!269 = !DILocation(column: 1, line: 400, scope: !41)
!270 = !DILocalVariable(file: !0, line: 400, name: "size", scope: !41, type: !11)
!271 = !DILocation(column: 5, line: 401, scope: !41)
!272 = !DILocation(column: 5, line: 402, scope: !41)
!273 = !DILocation(column: 5, line: 403, scope: !41)
!274 = !DILocation(column: 5, line: 405, scope: !41)