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

define i32 @"vec_push_str"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"s.arg") !dbg !17
{
entry:
  %"i.addr" = alloca i64, !dbg !34
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !30, metadata !7), !dbg !31
  %"s" = alloca i8*
  store i8* %"s.arg", i8** %"s"
  call void @"llvm.dbg.declare"(metadata i8** %"s", metadata !33, metadata !7), !dbg !31
  store i64 0, i64* %"i.addr", !dbg !34
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !35, metadata !7), !dbg !36
  br label %"while.cond", !dbg !37
while.cond:
  %".10" = load i8*, i8** %"s", !dbg !37
  %".11" = load i64, i64* %"i.addr", !dbg !37
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !37
  %".13" = load i8, i8* %".12", !dbg !37
  %".14" = zext i8 %".13" to i64 , !dbg !37
  %".15" = icmp ne i64 %".14", 0 , !dbg !37
  br i1 %".15", label %"while.body", label %"while.end", !dbg !37
while.body:
  %".17" = load i8*, i8** %"s", !dbg !38
  %".18" = load i64, i64* %"i.addr", !dbg !38
  %".19" = getelementptr i8, i8* %".17", i64 %".18" , !dbg !38
  %".20" = load i8, i8* %".19", !dbg !38
  %".21" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".20"), !dbg !38
  %".22" = sext i32 %".21" to i64 , !dbg !38
  %".23" = icmp ne i64 %".22", 0 , !dbg !38
  br i1 %".23", label %"if.then", label %"if.end", !dbg !38
while.end:
  %".32" = trunc i64 0 to i32 , !dbg !41
  ret i32 %".32", !dbg !41
if.then:
  %".25" = sub i64 0, 1, !dbg !39
  %".26" = trunc i64 %".25" to i32 , !dbg !39
  ret i32 %".26", !dbg !39
if.end:
  %".28" = load i64, i64* %"i.addr", !dbg !40
  %".29" = add i64 %".28", 1, !dbg !40
  store i64 %".29", i64* %"i.addr", !dbg !40
  br label %"while.cond", !dbg !40
}

define i8* @"vec_as_str"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !18
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !42, metadata !7), !dbg !43
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !44
  %".5" = load i64, i64* %".4", !dbg !44
  %".6" = add i64 %".5", 1, !dbg !44
  %".7" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".6"), !dbg !44
  %".8" = sext i32 %".7" to i64 , !dbg !44
  %".9" = icmp ne i64 %".8", 0 , !dbg !44
  br i1 %".9", label %"if.then", label %"if.end", !dbg !44
if.then:
  ret i8* null, !dbg !45
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !46
  %".13" = load i8*, i8** %".12", !dbg !46
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !46
  %".15" = load i64, i64* %".14", !dbg !46
  %".16" = getelementptr i8, i8* %".13", i64 %".15" , !dbg !46
  %".17" = trunc i64 0 to i8 , !dbg !46
  store i8 %".17", i8* %".16", !dbg !46
  %".19" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !47
  %".20" = load i8*, i8** %".19", !dbg !47
  ret i8* %".20", !dbg !47
}

define i64 @"vec_read_all_fd"(i32 %"fd.arg", %"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !19
{
entry:
  %"fd" = alloca i32
  %"temp.addr" = alloca [4096 x i8], !dbg !52
  %"total.addr" = alloca i64, !dbg !58
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !48, metadata !7), !dbg !49
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !50, metadata !7), !dbg !49
  call void @"llvm.dbg.declare"(metadata [4096 x i8]* %"temp.addr", metadata !56, metadata !7), !dbg !57
  store i64 0, i64* %"total.addr", !dbg !58
  call void @"llvm.dbg.declare"(metadata i64* %"total.addr", metadata !59, metadata !7), !dbg !60
  br label %"while.cond", !dbg !61
while.cond:
  br i1 1, label %"while.body", label %"while.end", !dbg !61
while.body:
  %".12" = load i32, i32* %"fd", !dbg !62
  %".13" = getelementptr [4096 x i8], [4096 x i8]* %"temp.addr", i32 0, i64 0 , !dbg !62
  %".14" = call i64 @"sys_read"(i32 %".12", i8* %".13", i64 4096), !dbg !62
  %".15" = icmp slt i64 %".14", 0 , !dbg !63
  br i1 %".15", label %"if.then", label %"if.end", !dbg !63
while.end:
  %".33" = load i64, i64* %"total.addr", !dbg !70
  ret i64 %".33", !dbg !70
if.then:
  %".17" = sub i64 0, 1, !dbg !64
  ret i64 %".17", !dbg !64
if.end:
  %".19" = icmp eq i64 %".14", 0 , !dbg !65
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !65
if.then.1:
  br label %"while.end", !dbg !66
if.end.1:
  %".22" = getelementptr [4096 x i8], [4096 x i8]* %"temp.addr", i32 0, i64 0 , !dbg !67
  %".23" = call i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %".22", i64 %".14"), !dbg !67
  %".24" = sext i32 %".23" to i64 , !dbg !67
  %".25" = icmp ne i64 %".24", 0 , !dbg !67
  br i1 %".25", label %"if.then.2", label %"if.end.2", !dbg !67
if.then.2:
  %".27" = sub i64 0, 1, !dbg !68
  ret i64 %".27", !dbg !68
if.end.2:
  %".29" = load i64, i64* %"total.addr", !dbg !69
  %".30" = add i64 %".29", %".14", !dbg !69
  store i64 %".30", i64* %"total.addr", !dbg !69
  br label %"while.cond", !dbg !69
}

define i32 @"vec_find_lines"(%"struct.ritz_module_1.Vec$u8"* %"buf.arg", %"struct.ritz_module_1.Vec$LineBounds"* %"lines.arg") !dbg !20
{
entry:
  %"line_start.addr" = alloca i64, !dbg !76
  %"i.addr" = alloca i64, !dbg !79
  %"bounds.addr" = alloca %"struct.ritz_module_1.LineBounds", !dbg !84
  %"bounds.addr.1" = alloca %"struct.ritz_module_1.LineBounds", !dbg !95
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"buf.arg", metadata !71, metadata !7), !dbg !72
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"lines.arg", metadata !75, metadata !7), !dbg !72
  store i64 0, i64* %"line_start.addr", !dbg !76
  call void @"llvm.dbg.declare"(metadata i64* %"line_start.addr", metadata !77, metadata !7), !dbg !78
  store i64 0, i64* %"i.addr", !dbg !79
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !80, metadata !7), !dbg !81
  br label %"while.cond", !dbg !82
while.cond:
  %".11" = load i64, i64* %"i.addr", !dbg !82
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"buf.arg", i32 0, i32 1 , !dbg !82
  %".13" = load i64, i64* %".12", !dbg !82
  %".14" = icmp slt i64 %".11", %".13" , !dbg !82
  br i1 %".14", label %"while.body", label %"while.end", !dbg !82
while.body:
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"buf.arg", i32 0, i32 0 , !dbg !83
  %".17" = load i8*, i8** %".16", !dbg !83
  %".18" = load i64, i64* %"i.addr", !dbg !83
  %".19" = getelementptr i8, i8* %".17", i64 %".18" , !dbg !83
  %".20" = load i8, i8* %".19", !dbg !83
  %".21" = icmp eq i8 %".20", 10 , !dbg !83
  br i1 %".21", label %"if.then", label %"if.end", !dbg !83
while.end:
  %".51" = load i64, i64* %"line_start.addr", !dbg !94
  %".52" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"buf.arg", i32 0, i32 1 , !dbg !94
  %".53" = load i64, i64* %".52", !dbg !94
  %".54" = icmp slt i64 %".51", %".53" , !dbg !94
  br i1 %".54", label %"if.then.2", label %"if.end.2", !dbg !94
if.then:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"bounds.addr", metadata !86, metadata !7), !dbg !87
  %".24" = load i64, i64* %"line_start.addr", !dbg !88
  %".25" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"bounds.addr", !dbg !88
  %".26" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"bounds.addr", i32 0, i32 0 , !dbg !88
  store i64 %".24", i64* %".26", !dbg !88
  %".28" = load i64, i64* %"i.addr", !dbg !89
  %".29" = load i64, i64* %"line_start.addr", !dbg !89
  %".30" = sub i64 %".28", %".29", !dbg !89
  %".31" = add i64 %".30", 1, !dbg !89
  %".32" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"bounds.addr", !dbg !89
  %".33" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"bounds.addr", i32 0, i32 1 , !dbg !89
  store i64 %".31", i64* %".33", !dbg !89
  %".35" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"bounds.addr", !dbg !90
  %".36" = call i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"lines.arg", %"struct.ritz_module_1.LineBounds" %".35"), !dbg !90
  %".37" = sext i32 %".36" to i64 , !dbg !90
  %".38" = icmp ne i64 %".37", 0 , !dbg !90
  br i1 %".38", label %"if.then.1", label %"if.end.1", !dbg !90
if.end:
  %".47" = load i64, i64* %"i.addr", !dbg !93
  %".48" = add i64 %".47", 1, !dbg !93
  store i64 %".48", i64* %"i.addr", !dbg !93
  br label %"while.cond", !dbg !93
if.then.1:
  %".40" = sub i64 0, 1, !dbg !91
  %".41" = trunc i64 %".40" to i32 , !dbg !91
  ret i32 %".41", !dbg !91
if.end.1:
  %".43" = load i64, i64* %"i.addr", !dbg !92
  %".44" = add i64 %".43", 1, !dbg !92
  store i64 %".44", i64* %"line_start.addr", !dbg !92
  br label %"if.end", !dbg !92
if.then.2:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"bounds.addr.1", metadata !96, metadata !7), !dbg !97
  %".57" = load i64, i64* %"line_start.addr", !dbg !98
  %".58" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"bounds.addr.1", !dbg !98
  %".59" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"bounds.addr.1", i32 0, i32 0 , !dbg !98
  store i64 %".57", i64* %".59", !dbg !98
  %".61" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"buf.arg", i32 0, i32 1 , !dbg !99
  %".62" = load i64, i64* %".61", !dbg !99
  %".63" = load i64, i64* %"line_start.addr", !dbg !99
  %".64" = sub i64 %".62", %".63", !dbg !99
  %".65" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"bounds.addr.1", !dbg !99
  %".66" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"bounds.addr.1", i32 0, i32 1 , !dbg !99
  store i64 %".64", i64* %".66", !dbg !99
  %".68" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"bounds.addr.1", !dbg !99
  %".69" = call i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"lines.arg", %"struct.ritz_module_1.LineBounds" %".68"), !dbg !99
  %".70" = sext i32 %".69" to i64 , !dbg !99
  %".71" = icmp ne i64 %".70", 0 , !dbg !99
  br i1 %".71", label %"if.then.3", label %"if.end.3", !dbg !99
if.end.2:
  %".77" = trunc i64 0 to i32 , !dbg !101
  ret i32 %".77", !dbg !101
if.then.3:
  %".73" = sub i64 0, 1, !dbg !100
  %".74" = trunc i64 %".73" to i32 , !dbg !100
  ret i32 %".74", !dbg !100
if.end.3:
  br label %"if.end.2", !dbg !100
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !21
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !102, metadata !7), !dbg !103
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !104, metadata !7), !dbg !103
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !105
  %".8" = load i64, i64* %".7", !dbg !105
  %".9" = add i64 %".8", 1, !dbg !105
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !105
  %".11" = sext i32 %".10" to i64 , !dbg !105
  %".12" = icmp ne i64 %".11", 0 , !dbg !105
  br i1 %".12", label %"if.then", label %"if.end", !dbg !105
if.then:
  %".14" = sub i64 0, 1, !dbg !106
  %".15" = trunc i64 %".14" to i32 , !dbg !106
  ret i32 %".15", !dbg !106
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !107
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !107
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !107
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !107
  %".21" = load i64, i64* %".20", !dbg !107
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !107
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !107
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !108
  %".25" = load i64, i64* %".24", !dbg !108
  %".26" = add i64 %".25", 1, !dbg !108
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !108
  store i64 %".26", i64* %".27", !dbg !108
  %".29" = trunc i64 0 to i32 , !dbg !109
  ret i32 %".29", !dbg !109
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !22
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !115
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !110, metadata !7), !dbg !111
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !112, metadata !7), !dbg !111
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !113
  %".8" = load i64, i64* %".7", !dbg !113
  %".9" = load i64, i64* %"needed", !dbg !113
  %".10" = icmp sge i64 %".8", %".9" , !dbg !113
  br i1 %".10", label %"if.then", label %"if.end", !dbg !113
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !114
  ret i32 %".12", !dbg !114
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !115
  %".15" = load i64, i64* %".14", !dbg !115
  store i64 %".15", i64* %"new_cap.addr", !dbg !115
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !116, metadata !7), !dbg !117
  %".18" = load i64, i64* %"new_cap.addr", !dbg !118
  %".19" = icmp eq i64 %".18", 0 , !dbg !118
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !118
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !119
  br label %"if.end.1", !dbg !119
if.end.1:
  br label %"while.cond", !dbg !120
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !120
  %".25" = load i64, i64* %"needed", !dbg !120
  %".26" = icmp slt i64 %".24", %".25" , !dbg !120
  br i1 %".26", label %"while.body", label %"while.end", !dbg !120
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !121
  %".29" = mul i64 %".28", 2, !dbg !121
  store i64 %".29", i64* %"new_cap.addr", !dbg !121
  br label %"while.cond", !dbg !121
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !122
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !122
  ret i32 %".33", !dbg !122
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !23
{
entry:
  %"i" = alloca i64, !dbg !127
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !123, metadata !7), !dbg !124
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !125, metadata !7), !dbg !124
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !126, metadata !7), !dbg !124
  %".10" = load i64, i64* %"len", !dbg !127
  store i64 0, i64* %"i", !dbg !127
  br label %"for.cond", !dbg !127
for.cond:
  %".13" = load i64, i64* %"i", !dbg !127
  %".14" = icmp slt i64 %".13", %".10" , !dbg !127
  br i1 %".14", label %"for.body", label %"for.end", !dbg !127
for.body:
  %".16" = load i8*, i8** %"data", !dbg !127
  %".17" = load i64, i64* %"i", !dbg !127
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !127
  %".19" = load i8, i8* %".18", !dbg !127
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !127
  %".21" = sext i32 %".20" to i64 , !dbg !127
  %".22" = icmp ne i64 %".21", 0 , !dbg !127
  br i1 %".22", label %"if.then", label %"if.end", !dbg !127
for.incr:
  %".28" = load i64, i64* %"i", !dbg !128
  %".29" = add i64 %".28", 1, !dbg !128
  store i64 %".29", i64* %"i", !dbg !128
  br label %"for.cond", !dbg !128
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !129
  ret i32 %".32", !dbg !129
if.then:
  %".24" = sub i64 0, 1, !dbg !128
  %".25" = trunc i64 %".24" to i32 , !dbg !128
  ret i32 %".25", !dbg !128
if.end:
  br label %"for.incr", !dbg !128
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !24
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !130, metadata !7), !dbg !131
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !132, metadata !7), !dbg !131
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !133
  %".8" = load i64, i64* %".7", !dbg !133
  %".9" = add i64 %".8", 1, !dbg !133
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !133
  %".11" = sext i32 %".10" to i64 , !dbg !133
  %".12" = icmp ne i64 %".11", 0 , !dbg !133
  br i1 %".12", label %"if.then", label %"if.end", !dbg !133
if.then:
  %".14" = sub i64 0, 1, !dbg !134
  %".15" = trunc i64 %".14" to i32 , !dbg !134
  ret i32 %".15", !dbg !134
if.end:
  %".17" = load i8, i8* %"item", !dbg !135
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !135
  %".19" = load i8*, i8** %".18", !dbg !135
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !135
  %".21" = load i64, i64* %".20", !dbg !135
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !135
  store i8 %".17", i8* %".22", !dbg !135
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !136
  %".25" = load i64, i64* %".24", !dbg !136
  %".26" = add i64 %".25", 1, !dbg !136
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !136
  store i64 %".26", i64* %".27", !dbg !136
  %".29" = trunc i64 0 to i32 , !dbg !137
  ret i32 %".29", !dbg !137
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !25
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !138, metadata !7), !dbg !139
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !140, metadata !7), !dbg !139
  %".7" = load i64, i64* %"new_cap", !dbg !141
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !141
  %".9" = load i64, i64* %".8", !dbg !141
  %".10" = icmp sle i64 %".7", %".9" , !dbg !141
  br i1 %".10", label %"if.then", label %"if.end", !dbg !141
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !142
  ret i32 %".12", !dbg !142
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !143
  %".15" = mul i64 %".14", 1, !dbg !143
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !144
  %".17" = load i8*, i8** %".16", !dbg !144
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !144
  %".19" = icmp eq i8* %".18", null , !dbg !145
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !145
if.then.1:
  %".21" = sub i64 0, 1, !dbg !146
  %".22" = trunc i64 %".21" to i32 , !dbg !146
  ret i32 %".22", !dbg !146
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !147
  store i8* %".18", i8** %".24", !dbg !147
  %".26" = load i64, i64* %"new_cap", !dbg !148
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !148
  store i64 %".26", i64* %".27", !dbg !148
  %".29" = trunc i64 0 to i32 , !dbg !149
  ret i32 %".29", !dbg !149
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !26
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !155
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !150, metadata !7), !dbg !151
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !152, metadata !7), !dbg !151
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !153
  %".8" = load i64, i64* %".7", !dbg !153
  %".9" = load i64, i64* %"needed", !dbg !153
  %".10" = icmp sge i64 %".8", %".9" , !dbg !153
  br i1 %".10", label %"if.then", label %"if.end", !dbg !153
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !154
  ret i32 %".12", !dbg !154
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !155
  %".15" = load i64, i64* %".14", !dbg !155
  store i64 %".15", i64* %"new_cap.addr", !dbg !155
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !156, metadata !7), !dbg !157
  %".18" = load i64, i64* %"new_cap.addr", !dbg !158
  %".19" = icmp eq i64 %".18", 0 , !dbg !158
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !158
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !159
  br label %"if.end.1", !dbg !159
if.end.1:
  br label %"while.cond", !dbg !160
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !160
  %".25" = load i64, i64* %"needed", !dbg !160
  %".26" = icmp slt i64 %".24", %".25" , !dbg !160
  br i1 %".26", label %"while.body", label %"while.end", !dbg !160
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !161
  %".29" = mul i64 %".28", 2, !dbg !161
  store i64 %".29", i64* %"new_cap.addr", !dbg !161
  br label %"while.cond", !dbg !161
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !162
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !162
  ret i32 %".33", !dbg !162
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !27
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !163, metadata !7), !dbg !164
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !165, metadata !7), !dbg !164
  %".7" = load i64, i64* %"new_cap", !dbg !166
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !166
  %".9" = load i64, i64* %".8", !dbg !166
  %".10" = icmp sle i64 %".7", %".9" , !dbg !166
  br i1 %".10", label %"if.then", label %"if.end", !dbg !166
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !167
  ret i32 %".12", !dbg !167
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !168
  %".15" = mul i64 %".14", 16, !dbg !168
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !169
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !169
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !169
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !169
  %".20" = icmp eq i8* %".19", null , !dbg !170
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !170
if.then.1:
  %".22" = sub i64 0, 1, !dbg !171
  %".23" = trunc i64 %".22" to i32 , !dbg !171
  ret i32 %".23", !dbg !171
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !172
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !172
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !172
  %".28" = load i64, i64* %"new_cap", !dbg !173
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !173
  store i64 %".28", i64* %".29", !dbg !173
  %".31" = trunc i64 0 to i32 , !dbg !174
  ret i32 %".31", !dbg !174
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/ritz/ritzlib", filename: "gvec.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 295, name: "vec_push_str", scopeLine: 295, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 305, name: "vec_as_str", scopeLine: 305, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 344, name: "vec_read_all_fd", scopeLine: 344, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 363, name: "vec_find_lines", scopeLine: 363, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!28 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!29 = !DIDerivedType(baseType: !28, size: 64, tag: DW_TAG_reference_type)
!30 = !DILocalVariable(file: !0, line: 295, name: "v", scope: !17, type: !29)
!31 = !DILocation(column: 1, line: 295, scope: !17)
!32 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!33 = !DILocalVariable(file: !0, line: 295, name: "s", scope: !17, type: !32)
!34 = !DILocation(column: 5, line: 296, scope: !17)
!35 = !DILocalVariable(file: !0, line: 296, name: "i", scope: !17, type: !11)
!36 = !DILocation(column: 1, line: 296, scope: !17)
!37 = !DILocation(column: 5, line: 297, scope: !17)
!38 = !DILocation(column: 9, line: 298, scope: !17)
!39 = !DILocation(column: 13, line: 299, scope: !17)
!40 = !DILocation(column: 9, line: 300, scope: !17)
!41 = !DILocation(column: 5, line: 301, scope: !17)
!42 = !DILocalVariable(file: !0, line: 305, name: "v", scope: !18, type: !29)
!43 = !DILocation(column: 1, line: 305, scope: !18)
!44 = !DILocation(column: 5, line: 307, scope: !18)
!45 = !DILocation(column: 9, line: 308, scope: !18)
!46 = !DILocation(column: 5, line: 310, scope: !18)
!47 = !DILocation(column: 5, line: 311, scope: !18)
!48 = !DILocalVariable(file: !0, line: 344, name: "fd", scope: !19, type: !10)
!49 = !DILocation(column: 1, line: 344, scope: !19)
!50 = !DILocalVariable(file: !0, line: 344, name: "v", scope: !19, type: !29)
!51 = !DILocation(column: 5, line: 345, scope: !19)
!52 = !DILocation(column: 5, line: 346, scope: !19)
!53 = !DISubrange(count: 4096)
!54 = !{ !53 }
!55 = !DICompositeType(baseType: !12, elements: !54, size: 32768, tag: DW_TAG_array_type)
!56 = !DILocalVariable(file: !0, line: 346, name: "temp", scope: !19, type: !55)
!57 = !DILocation(column: 1, line: 346, scope: !19)
!58 = !DILocation(column: 5, line: 347, scope: !19)
!59 = !DILocalVariable(file: !0, line: 347, name: "total", scope: !19, type: !11)
!60 = !DILocation(column: 1, line: 347, scope: !19)
!61 = !DILocation(column: 5, line: 349, scope: !19)
!62 = !DILocation(column: 9, line: 350, scope: !19)
!63 = !DILocation(column: 9, line: 351, scope: !19)
!64 = !DILocation(column: 13, line: 352, scope: !19)
!65 = !DILocation(column: 9, line: 353, scope: !19)
!66 = !DILocation(column: 13, line: 354, scope: !19)
!67 = !DILocation(column: 9, line: 355, scope: !19)
!68 = !DILocation(column: 13, line: 356, scope: !19)
!69 = !DILocation(column: 9, line: 357, scope: !19)
!70 = !DILocation(column: 5, line: 359, scope: !19)
!71 = !DILocalVariable(file: !0, line: 363, name: "buf", scope: !20, type: !29)
!72 = !DILocation(column: 1, line: 363, scope: !20)
!73 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!74 = !DIDerivedType(baseType: !73, size: 64, tag: DW_TAG_reference_type)
!75 = !DILocalVariable(file: !0, line: 363, name: "lines", scope: !20, type: !74)
!76 = !DILocation(column: 5, line: 364, scope: !20)
!77 = !DILocalVariable(file: !0, line: 364, name: "line_start", scope: !20, type: !11)
!78 = !DILocation(column: 1, line: 364, scope: !20)
!79 = !DILocation(column: 5, line: 365, scope: !20)
!80 = !DILocalVariable(file: !0, line: 365, name: "i", scope: !20, type: !11)
!81 = !DILocation(column: 1, line: 365, scope: !20)
!82 = !DILocation(column: 5, line: 367, scope: !20)
!83 = !DILocation(column: 9, line: 368, scope: !20)
!84 = !DILocation(column: 13, line: 369, scope: !20)
!85 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!86 = !DILocalVariable(file: !0, line: 369, name: "bounds", scope: !20, type: !85)
!87 = !DILocation(column: 1, line: 369, scope: !20)
!88 = !DILocation(column: 13, line: 370, scope: !20)
!89 = !DILocation(column: 13, line: 371, scope: !20)
!90 = !DILocation(column: 13, line: 372, scope: !20)
!91 = !DILocation(column: 17, line: 373, scope: !20)
!92 = !DILocation(column: 13, line: 374, scope: !20)
!93 = !DILocation(column: 9, line: 375, scope: !20)
!94 = !DILocation(column: 5, line: 378, scope: !20)
!95 = !DILocation(column: 9, line: 379, scope: !20)
!96 = !DILocalVariable(file: !0, line: 379, name: "bounds", scope: !20, type: !85)
!97 = !DILocation(column: 1, line: 379, scope: !20)
!98 = !DILocation(column: 9, line: 380, scope: !20)
!99 = !DILocation(column: 9, line: 381, scope: !20)
!100 = !DILocation(column: 13, line: 383, scope: !20)
!101 = !DILocation(column: 5, line: 385, scope: !20)
!102 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !21, type: !74)
!103 = !DILocation(column: 1, line: 210, scope: !21)
!104 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !21, type: !85)
!105 = !DILocation(column: 5, line: 211, scope: !21)
!106 = !DILocation(column: 9, line: 212, scope: !21)
!107 = !DILocation(column: 5, line: 213, scope: !21)
!108 = !DILocation(column: 5, line: 214, scope: !21)
!109 = !DILocation(column: 5, line: 215, scope: !21)
!110 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !22, type: !29)
!111 = !DILocation(column: 1, line: 193, scope: !22)
!112 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !22, type: !11)
!113 = !DILocation(column: 5, line: 194, scope: !22)
!114 = !DILocation(column: 9, line: 195, scope: !22)
!115 = !DILocation(column: 5, line: 197, scope: !22)
!116 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !22, type: !11)
!117 = !DILocation(column: 1, line: 197, scope: !22)
!118 = !DILocation(column: 5, line: 198, scope: !22)
!119 = !DILocation(column: 9, line: 199, scope: !22)
!120 = !DILocation(column: 5, line: 200, scope: !22)
!121 = !DILocation(column: 9, line: 201, scope: !22)
!122 = !DILocation(column: 5, line: 203, scope: !22)
!123 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !23, type: !29)
!124 = !DILocation(column: 1, line: 288, scope: !23)
!125 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !23, type: !32)
!126 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !23, type: !11)
!127 = !DILocation(column: 5, line: 289, scope: !23)
!128 = !DILocation(column: 13, line: 291, scope: !23)
!129 = !DILocation(column: 5, line: 292, scope: !23)
!130 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !24, type: !29)
!131 = !DILocation(column: 1, line: 210, scope: !24)
!132 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !24, type: !12)
!133 = !DILocation(column: 5, line: 211, scope: !24)
!134 = !DILocation(column: 9, line: 212, scope: !24)
!135 = !DILocation(column: 5, line: 213, scope: !24)
!136 = !DILocation(column: 5, line: 214, scope: !24)
!137 = !DILocation(column: 5, line: 215, scope: !24)
!138 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !25, type: !29)
!139 = !DILocation(column: 1, line: 179, scope: !25)
!140 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !25, type: !11)
!141 = !DILocation(column: 5, line: 180, scope: !25)
!142 = !DILocation(column: 9, line: 181, scope: !25)
!143 = !DILocation(column: 5, line: 183, scope: !25)
!144 = !DILocation(column: 5, line: 184, scope: !25)
!145 = !DILocation(column: 5, line: 185, scope: !25)
!146 = !DILocation(column: 9, line: 186, scope: !25)
!147 = !DILocation(column: 5, line: 188, scope: !25)
!148 = !DILocation(column: 5, line: 189, scope: !25)
!149 = !DILocation(column: 5, line: 190, scope: !25)
!150 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !26, type: !74)
!151 = !DILocation(column: 1, line: 193, scope: !26)
!152 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !26, type: !11)
!153 = !DILocation(column: 5, line: 194, scope: !26)
!154 = !DILocation(column: 9, line: 195, scope: !26)
!155 = !DILocation(column: 5, line: 197, scope: !26)
!156 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !26, type: !11)
!157 = !DILocation(column: 1, line: 197, scope: !26)
!158 = !DILocation(column: 5, line: 198, scope: !26)
!159 = !DILocation(column: 9, line: 199, scope: !26)
!160 = !DILocation(column: 5, line: 200, scope: !26)
!161 = !DILocation(column: 9, line: 201, scope: !26)
!162 = !DILocation(column: 5, line: 203, scope: !26)
!163 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !27, type: !74)
!164 = !DILocation(column: 1, line: 179, scope: !27)
!165 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !27, type: !11)
!166 = !DILocation(column: 5, line: 180, scope: !27)
!167 = !DILocation(column: 9, line: 181, scope: !27)
!168 = !DILocation(column: 5, line: 183, scope: !27)
!169 = !DILocation(column: 5, line: 184, scope: !27)
!170 = !DILocation(column: 5, line: 185, scope: !27)
!171 = !DILocation(column: 9, line: 186, scope: !27)
!172 = !DILocation(column: 5, line: 188, scope: !27)
!173 = !DILocation(column: 5, line: 189, scope: !27)
!174 = !DILocation(column: 5, line: 190, scope: !27)