; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Vec$LineBounds" = type {%"struct.ritz_module_1.LineBounds"*, i64, i64}
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
%"struct.ritz_module_1.TestResult" = type {%"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8", i32, i64, i32}
%"struct.ritz_module_1.TestSummary" = type {i32, i32, i32, i32, i32, i32, i64}
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

define %"struct.ritz_module_1.TestSummary" @"summary_new"() !dbg !17
{
entry:
  %"s.addr" = alloca %"struct.ritz_module_1.TestSummary", !dbg !27
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.TestSummary"* %"s.addr", metadata !29, metadata !7), !dbg !30
  %".3" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", !dbg !31
  %".4" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", i32 0, i32 0 , !dbg !31
  %".5" = trunc i64 0 to i32 , !dbg !31
  store i32 %".5", i32* %".4", !dbg !31
  %".7" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", !dbg !32
  %".8" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", i32 0, i32 1 , !dbg !32
  %".9" = trunc i64 0 to i32 , !dbg !32
  store i32 %".9", i32* %".8", !dbg !32
  %".11" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", !dbg !33
  %".12" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", i32 0, i32 2 , !dbg !33
  %".13" = trunc i64 0 to i32 , !dbg !33
  store i32 %".13", i32* %".12", !dbg !33
  %".15" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", !dbg !34
  %".16" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", i32 0, i32 3 , !dbg !34
  %".17" = trunc i64 0 to i32 , !dbg !34
  store i32 %".17", i32* %".16", !dbg !34
  %".19" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", !dbg !35
  %".20" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", i32 0, i32 4 , !dbg !35
  %".21" = trunc i64 0 to i32 , !dbg !35
  store i32 %".21", i32* %".20", !dbg !35
  %".23" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", !dbg !36
  %".24" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", i32 0, i32 5 , !dbg !36
  %".25" = trunc i64 0 to i32 , !dbg !36
  store i32 %".25", i32* %".24", !dbg !36
  %".27" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", !dbg !37
  %".28" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", i32 0, i32 6 , !dbg !37
  store i64 0, i64* %".28", !dbg !37
  %".30" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.addr", !dbg !38
  ret %"struct.ritz_module_1.TestSummary" %".30", !dbg !38
}

define i32 @"summary_record"(%"struct.ritz_module_1.TestSummary"* %"s.arg", i32 %"status.arg", i64 %"duration_ms.arg") !dbg !18
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.TestSummary"* %"s.arg", metadata !39, metadata !7), !dbg !40
  %"status" = alloca i32
  store i32 %"status.arg", i32* %"status"
  call void @"llvm.dbg.declare"(metadata i32* %"status", metadata !41, metadata !7), !dbg !40
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !42, metadata !7), !dbg !40
  %".10" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 0 , !dbg !43
  %".11" = load i32, i32* %".10", !dbg !43
  %".12" = sext i32 %".11" to i64 , !dbg !43
  %".13" = add i64 %".12", 1, !dbg !43
  %".14" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", !dbg !43
  %".15" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 0 , !dbg !43
  %".16" = trunc i64 %".13" to i32 , !dbg !43
  store i32 %".16", i32* %".15", !dbg !43
  %".18" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 6 , !dbg !44
  %".19" = load i64, i64* %".18", !dbg !44
  %".20" = load i64, i64* %"duration_ms", !dbg !44
  %".21" = add i64 %".19", %".20", !dbg !44
  %".22" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", !dbg !44
  %".23" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 6 , !dbg !44
  store i64 %".21", i64* %".23", !dbg !44
  %".25" = load i32, i32* %"status", !dbg !45
  %".26" = icmp eq i32 %".25", 0 , !dbg !45
  br i1 %".26", label %"if.then", label %"if.else", !dbg !45
if.then:
  %".28" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 1 , !dbg !46
  %".29" = load i32, i32* %".28", !dbg !46
  %".30" = sext i32 %".29" to i64 , !dbg !46
  %".31" = add i64 %".30", 1, !dbg !46
  %".32" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", !dbg !46
  %".33" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 1 , !dbg !46
  %".34" = trunc i64 %".31" to i32 , !dbg !46
  store i32 %".34", i32* %".33", !dbg !46
  br label %"if.end", !dbg !50
if.else:
  %".36" = load i32, i32* %"status", !dbg !46
  %".37" = icmp eq i32 %".36", 2 , !dbg !46
  br i1 %".37", label %"if.then.1", label %"if.else.1", !dbg !46
if.end:
  ret i32 0, !dbg !50
if.then.1:
  %".39" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 5 , !dbg !47
  %".40" = load i32, i32* %".39", !dbg !47
  %".41" = sext i32 %".40" to i64 , !dbg !47
  %".42" = add i64 %".41", 1, !dbg !47
  %".43" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", !dbg !47
  %".44" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 5 , !dbg !47
  %".45" = trunc i64 %".42" to i32 , !dbg !47
  store i32 %".45", i32* %".44", !dbg !47
  br label %"if.end.1", !dbg !50
if.else.1:
  %".47" = load i32, i32* %"status", !dbg !47
  %".48" = icmp eq i32 %".47", 3 , !dbg !47
  br i1 %".48", label %"if.then.2", label %"if.else.2", !dbg !47
if.end.1:
  br label %"if.end", !dbg !50
if.then.2:
  %".50" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 4 , !dbg !48
  %".51" = load i32, i32* %".50", !dbg !48
  %".52" = sext i32 %".51" to i64 , !dbg !48
  %".53" = add i64 %".52", 1, !dbg !48
  %".54" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", !dbg !48
  %".55" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 4 , !dbg !48
  %".56" = trunc i64 %".53" to i32 , !dbg !48
  store i32 %".56", i32* %".55", !dbg !48
  br label %"if.end.2", !dbg !50
if.else.2:
  %".58" = load i32, i32* %"status", !dbg !48
  %".59" = icmp eq i32 %".58", 4 , !dbg !48
  br i1 %".59", label %"if.then.3", label %"if.else.3", !dbg !48
if.end.2:
  br label %"if.end.1", !dbg !50
if.then.3:
  %".61" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 3 , !dbg !49
  %".62" = load i32, i32* %".61", !dbg !49
  %".63" = sext i32 %".62" to i64 , !dbg !49
  %".64" = add i64 %".63", 1, !dbg !49
  %".65" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", !dbg !49
  %".66" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 3 , !dbg !49
  %".67" = trunc i64 %".64" to i32 , !dbg !49
  store i32 %".67", i32* %".66", !dbg !49
  br label %"if.end.3", !dbg !50
if.else.3:
  %".69" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 2 , !dbg !50
  %".70" = load i32, i32* %".69", !dbg !50
  %".71" = sext i32 %".70" to i64 , !dbg !50
  %".72" = add i64 %".71", 1, !dbg !50
  %".73" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", !dbg !50
  %".74" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"s.arg", i32 0, i32 2 , !dbg !50
  %".75" = trunc i64 %".72" to i32 , !dbg !50
  store i32 %".75", i32* %".74", !dbg !50
  br label %"if.end.3", !dbg !50
if.end.3:
  br label %"if.end.2", !dbg !50
}

define i32 @"summary_merge"(%"struct.ritz_module_1.TestSummary"* %"dest.arg", %"struct.ritz_module_1.TestSummary"* %"src.arg") !dbg !19
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.TestSummary"* %"dest.arg", metadata !51, metadata !7), !dbg !52
  %"src" = alloca %"struct.ritz_module_1.TestSummary"*
  store %"struct.ritz_module_1.TestSummary"* %"src.arg", %"struct.ritz_module_1.TestSummary"** %"src"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.TestSummary"** %"src", metadata !54, metadata !7), !dbg !52
  %".7" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 0 , !dbg !55
  %".8" = load i32, i32* %".7", !dbg !55
  %".9" = load %"struct.ritz_module_1.TestSummary"*, %"struct.ritz_module_1.TestSummary"** %"src", !dbg !55
  %".10" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %".9", i32 0, i32 0 , !dbg !55
  %".11" = load i32, i32* %".10", !dbg !55
  %".12" = add i32 %".8", %".11", !dbg !55
  %".13" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", !dbg !55
  %".14" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 0 , !dbg !55
  store i32 %".12", i32* %".14", !dbg !55
  %".16" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 1 , !dbg !56
  %".17" = load i32, i32* %".16", !dbg !56
  %".18" = load %"struct.ritz_module_1.TestSummary"*, %"struct.ritz_module_1.TestSummary"** %"src", !dbg !56
  %".19" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %".18", i32 0, i32 1 , !dbg !56
  %".20" = load i32, i32* %".19", !dbg !56
  %".21" = add i32 %".17", %".20", !dbg !56
  %".22" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", !dbg !56
  %".23" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 1 , !dbg !56
  store i32 %".21", i32* %".23", !dbg !56
  %".25" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 2 , !dbg !57
  %".26" = load i32, i32* %".25", !dbg !57
  %".27" = load %"struct.ritz_module_1.TestSummary"*, %"struct.ritz_module_1.TestSummary"** %"src", !dbg !57
  %".28" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %".27", i32 0, i32 2 , !dbg !57
  %".29" = load i32, i32* %".28", !dbg !57
  %".30" = add i32 %".26", %".29", !dbg !57
  %".31" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", !dbg !57
  %".32" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 2 , !dbg !57
  store i32 %".30", i32* %".32", !dbg !57
  %".34" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 3 , !dbg !58
  %".35" = load i32, i32* %".34", !dbg !58
  %".36" = load %"struct.ritz_module_1.TestSummary"*, %"struct.ritz_module_1.TestSummary"** %"src", !dbg !58
  %".37" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %".36", i32 0, i32 3 , !dbg !58
  %".38" = load i32, i32* %".37", !dbg !58
  %".39" = add i32 %".35", %".38", !dbg !58
  %".40" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", !dbg !58
  %".41" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 3 , !dbg !58
  store i32 %".39", i32* %".41", !dbg !58
  %".43" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 4 , !dbg !59
  %".44" = load i32, i32* %".43", !dbg !59
  %".45" = load %"struct.ritz_module_1.TestSummary"*, %"struct.ritz_module_1.TestSummary"** %"src", !dbg !59
  %".46" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %".45", i32 0, i32 4 , !dbg !59
  %".47" = load i32, i32* %".46", !dbg !59
  %".48" = add i32 %".44", %".47", !dbg !59
  %".49" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", !dbg !59
  %".50" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 4 , !dbg !59
  store i32 %".48", i32* %".50", !dbg !59
  %".52" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 5 , !dbg !60
  %".53" = load i32, i32* %".52", !dbg !60
  %".54" = load %"struct.ritz_module_1.TestSummary"*, %"struct.ritz_module_1.TestSummary"** %"src", !dbg !60
  %".55" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %".54", i32 0, i32 5 , !dbg !60
  %".56" = load i32, i32* %".55", !dbg !60
  %".57" = add i32 %".53", %".56", !dbg !60
  %".58" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", !dbg !60
  %".59" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 5 , !dbg !60
  store i32 %".57", i32* %".59", !dbg !60
  %".61" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 6 , !dbg !61
  %".62" = load i64, i64* %".61", !dbg !61
  %".63" = load %"struct.ritz_module_1.TestSummary"*, %"struct.ritz_module_1.TestSummary"** %"src", !dbg !61
  %".64" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %".63", i32 0, i32 6 , !dbg !61
  %".65" = load i64, i64* %".64", !dbg !61
  %".66" = add i64 %".62", %".65", !dbg !61
  %".67" = load %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", !dbg !61
  %".68" = getelementptr %"struct.ritz_module_1.TestSummary", %"struct.ritz_module_1.TestSummary"* %"dest.arg", i32 0, i32 6 , !dbg !61
  store i64 %".66", i64* %".68", !dbg !61
  ret i32 0, !dbg !61
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !20
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !64, metadata !7), !dbg !65
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !66, metadata !7), !dbg !65
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !67
  %".8" = load i64, i64* %".7", !dbg !67
  %".9" = add i64 %".8", 1, !dbg !67
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !67
  %".11" = sext i32 %".10" to i64 , !dbg !67
  %".12" = icmp ne i64 %".11", 0 , !dbg !67
  br i1 %".12", label %"if.then", label %"if.end", !dbg !67
if.then:
  %".14" = sub i64 0, 1, !dbg !68
  %".15" = trunc i64 %".14" to i32 , !dbg !68
  ret i32 %".15", !dbg !68
if.end:
  %".17" = load i8, i8* %"item", !dbg !69
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !69
  %".19" = load i8*, i8** %".18", !dbg !69
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !69
  %".21" = load i64, i64* %".20", !dbg !69
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !69
  store i8 %".17", i8* %".22", !dbg !69
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !70
  %".25" = load i64, i64* %".24", !dbg !70
  %".26" = add i64 %".25", 1, !dbg !70
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !70
  store i64 %".26", i64* %".27", !dbg !70
  %".29" = trunc i64 0 to i32 , !dbg !71
  ret i32 %".29", !dbg !71
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !21
{
entry:
  %"i" = alloca i64, !dbg !77
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !72, metadata !7), !dbg !73
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !75, metadata !7), !dbg !73
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !76, metadata !7), !dbg !73
  %".10" = load i64, i64* %"len", !dbg !77
  store i64 0, i64* %"i", !dbg !77
  br label %"for.cond", !dbg !77
for.cond:
  %".13" = load i64, i64* %"i", !dbg !77
  %".14" = icmp slt i64 %".13", %".10" , !dbg !77
  br i1 %".14", label %"for.body", label %"for.end", !dbg !77
for.body:
  %".16" = load i8*, i8** %"data", !dbg !77
  %".17" = load i64, i64* %"i", !dbg !77
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !77
  %".19" = load i8, i8* %".18", !dbg !77
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !77
  %".21" = sext i32 %".20" to i64 , !dbg !77
  %".22" = icmp ne i64 %".21", 0 , !dbg !77
  br i1 %".22", label %"if.then", label %"if.end", !dbg !77
for.incr:
  %".28" = load i64, i64* %"i", !dbg !78
  %".29" = add i64 %".28", 1, !dbg !78
  store i64 %".29", i64* %"i", !dbg !78
  br label %"for.cond", !dbg !78
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !79
  ret i32 %".32", !dbg !79
if.then:
  %".24" = sub i64 0, 1, !dbg !78
  %".25" = trunc i64 %".24" to i32 , !dbg !78
  ret i32 %".25", !dbg !78
if.end:
  br label %"for.incr", !dbg !78
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !22
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !85
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !80, metadata !7), !dbg !81
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !82, metadata !7), !dbg !81
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !83
  %".8" = load i64, i64* %".7", !dbg !83
  %".9" = load i64, i64* %"needed", !dbg !83
  %".10" = icmp sge i64 %".8", %".9" , !dbg !83
  br i1 %".10", label %"if.then", label %"if.end", !dbg !83
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !84
  ret i32 %".12", !dbg !84
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !85
  %".15" = load i64, i64* %".14", !dbg !85
  store i64 %".15", i64* %"new_cap.addr", !dbg !85
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !86, metadata !7), !dbg !87
  %".18" = load i64, i64* %"new_cap.addr", !dbg !88
  %".19" = icmp eq i64 %".18", 0 , !dbg !88
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !88
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !89
  br label %"if.end.1", !dbg !89
if.end.1:
  br label %"while.cond", !dbg !90
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !90
  %".25" = load i64, i64* %"needed", !dbg !90
  %".26" = icmp slt i64 %".24", %".25" , !dbg !90
  br i1 %".26", label %"while.body", label %"while.end", !dbg !90
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !91
  %".29" = mul i64 %".28", 2, !dbg !91
  store i64 %".29", i64* %"new_cap.addr", !dbg !91
  br label %"while.cond", !dbg !91
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !92
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !92
  ret i32 %".33", !dbg !92
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !23
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !95, metadata !7), !dbg !96
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !98, metadata !7), !dbg !96
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !99
  %".8" = load i64, i64* %".7", !dbg !99
  %".9" = add i64 %".8", 1, !dbg !99
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !99
  %".11" = sext i32 %".10" to i64 , !dbg !99
  %".12" = icmp ne i64 %".11", 0 , !dbg !99
  br i1 %".12", label %"if.then", label %"if.end", !dbg !99
if.then:
  %".14" = sub i64 0, 1, !dbg !100
  %".15" = trunc i64 %".14" to i32 , !dbg !100
  ret i32 %".15", !dbg !100
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !101
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !101
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !101
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !101
  %".21" = load i64, i64* %".20", !dbg !101
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !101
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !101
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !102
  %".25" = load i64, i64* %".24", !dbg !102
  %".26" = add i64 %".25", 1, !dbg !102
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !102
  store i64 %".26", i64* %".27", !dbg !102
  %".29" = trunc i64 0 to i32 , !dbg !103
  ret i32 %".29", !dbg !103
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !24
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !109
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !104, metadata !7), !dbg !105
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !106, metadata !7), !dbg !105
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !107
  %".8" = load i64, i64* %".7", !dbg !107
  %".9" = load i64, i64* %"needed", !dbg !107
  %".10" = icmp sge i64 %".8", %".9" , !dbg !107
  br i1 %".10", label %"if.then", label %"if.end", !dbg !107
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !108
  ret i32 %".12", !dbg !108
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !109
  %".15" = load i64, i64* %".14", !dbg !109
  store i64 %".15", i64* %"new_cap.addr", !dbg !109
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !110, metadata !7), !dbg !111
  %".18" = load i64, i64* %"new_cap.addr", !dbg !112
  %".19" = icmp eq i64 %".18", 0 , !dbg !112
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !112
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !113
  br label %"if.end.1", !dbg !113
if.end.1:
  br label %"while.cond", !dbg !114
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !114
  %".25" = load i64, i64* %"needed", !dbg !114
  %".26" = icmp slt i64 %".24", %".25" , !dbg !114
  br i1 %".26", label %"while.body", label %"while.end", !dbg !114
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !115
  %".29" = mul i64 %".28", 2, !dbg !115
  store i64 %".29", i64* %"new_cap.addr", !dbg !115
  br label %"while.cond", !dbg !115
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !116
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !116
  ret i32 %".33", !dbg !116
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !25
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !117, metadata !7), !dbg !118
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !119, metadata !7), !dbg !118
  %".7" = load i64, i64* %"new_cap", !dbg !120
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !120
  %".9" = load i64, i64* %".8", !dbg !120
  %".10" = icmp sle i64 %".7", %".9" , !dbg !120
  br i1 %".10", label %"if.then", label %"if.end", !dbg !120
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !121
  ret i32 %".12", !dbg !121
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !122
  %".15" = mul i64 %".14", 1, !dbg !122
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !123
  %".17" = load i8*, i8** %".16", !dbg !123
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !123
  %".19" = icmp eq i8* %".18", null , !dbg !124
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !124
if.then.1:
  %".21" = sub i64 0, 1, !dbg !125
  %".22" = trunc i64 %".21" to i32 , !dbg !125
  ret i32 %".22", !dbg !125
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !126
  store i8* %".18", i8** %".24", !dbg !126
  %".26" = load i64, i64* %"new_cap", !dbg !127
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !127
  store i64 %".26", i64* %".27", !dbg !127
  %".29" = trunc i64 0 to i32 , !dbg !128
  ret i32 %".29", !dbg !128
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !26
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !129, metadata !7), !dbg !130
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !131, metadata !7), !dbg !130
  %".7" = load i64, i64* %"new_cap", !dbg !132
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !132
  %".9" = load i64, i64* %".8", !dbg !132
  %".10" = icmp sle i64 %".7", %".9" , !dbg !132
  br i1 %".10", label %"if.then", label %"if.end", !dbg !132
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !133
  ret i32 %".12", !dbg !133
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !134
  %".15" = mul i64 %".14", 16, !dbg !134
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !135
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !135
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !135
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !135
  %".20" = icmp eq i8* %".19", null , !dbg !136
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !136
if.then.1:
  %".22" = sub i64 0, 1, !dbg !137
  %".23" = trunc i64 %".22" to i32 , !dbg !137
  ret i32 %".23", !dbg !137
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !138
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !138
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !138
  %".28" = load i64, i64* %"new_cap", !dbg !139
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !139
  store i64 %".28", i64* %".29", !dbg !139
  %".31" = trunc i64 0 to i32 , !dbg !140
  ret i32 %".31", !dbg !140
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/ritzunit/src", filename: "types.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 46, name: "summary_new", scopeLine: 46, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 58, name: "summary_record", scopeLine: 58, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 73, name: "summary_merge", scopeLine: 73, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!27 = !DILocation(column: 5, line: 47, scope: !17)
!28 = !DICompositeType(align: 64, file: !0, name: "TestSummary", size: 256, tag: DW_TAG_structure_type)
!29 = !DILocalVariable(file: !0, line: 47, name: "s", scope: !17, type: !28)
!30 = !DILocation(column: 1, line: 47, scope: !17)
!31 = !DILocation(column: 5, line: 48, scope: !17)
!32 = !DILocation(column: 5, line: 49, scope: !17)
!33 = !DILocation(column: 5, line: 50, scope: !17)
!34 = !DILocation(column: 5, line: 51, scope: !17)
!35 = !DILocation(column: 5, line: 52, scope: !17)
!36 = !DILocation(column: 5, line: 53, scope: !17)
!37 = !DILocation(column: 5, line: 54, scope: !17)
!38 = !DILocation(column: 5, line: 55, scope: !17)
!39 = !DILocalVariable(file: !0, line: 58, name: "s", scope: !18, type: !28)
!40 = !DILocation(column: 1, line: 58, scope: !18)
!41 = !DILocalVariable(file: !0, line: 58, name: "status", scope: !18, type: !10)
!42 = !DILocalVariable(file: !0, line: 58, name: "duration_ms", scope: !18, type: !11)
!43 = !DILocation(column: 5, line: 59, scope: !18)
!44 = !DILocation(column: 5, line: 60, scope: !18)
!45 = !DILocation(column: 5, line: 61, scope: !18)
!46 = !DILocation(column: 9, line: 62, scope: !18)
!47 = !DILocation(column: 9, line: 64, scope: !18)
!48 = !DILocation(column: 9, line: 66, scope: !18)
!49 = !DILocation(column: 9, line: 68, scope: !18)
!50 = !DILocation(column: 9, line: 70, scope: !18)
!51 = !DILocalVariable(file: !0, line: 73, name: "dest", scope: !19, type: !28)
!52 = !DILocation(column: 1, line: 73, scope: !19)
!53 = !DIDerivedType(baseType: !28, size: 64, tag: DW_TAG_pointer_type)
!54 = !DILocalVariable(file: !0, line: 73, name: "src", scope: !19, type: !53)
!55 = !DILocation(column: 5, line: 74, scope: !19)
!56 = !DILocation(column: 5, line: 75, scope: !19)
!57 = !DILocation(column: 5, line: 76, scope: !19)
!58 = !DILocation(column: 5, line: 77, scope: !19)
!59 = !DILocation(column: 5, line: 78, scope: !19)
!60 = !DILocation(column: 5, line: 79, scope: !19)
!61 = !DILocation(column: 5, line: 80, scope: !19)
!62 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!63 = !DIDerivedType(baseType: !62, size: 64, tag: DW_TAG_reference_type)
!64 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !20, type: !63)
!65 = !DILocation(column: 1, line: 210, scope: !20)
!66 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !20, type: !12)
!67 = !DILocation(column: 5, line: 211, scope: !20)
!68 = !DILocation(column: 9, line: 212, scope: !20)
!69 = !DILocation(column: 5, line: 213, scope: !20)
!70 = !DILocation(column: 5, line: 214, scope: !20)
!71 = !DILocation(column: 5, line: 215, scope: !20)
!72 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !21, type: !63)
!73 = !DILocation(column: 1, line: 288, scope: !21)
!74 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!75 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !21, type: !74)
!76 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !21, type: !11)
!77 = !DILocation(column: 5, line: 289, scope: !21)
!78 = !DILocation(column: 13, line: 291, scope: !21)
!79 = !DILocation(column: 5, line: 292, scope: !21)
!80 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !22, type: !63)
!81 = !DILocation(column: 1, line: 193, scope: !22)
!82 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !22, type: !11)
!83 = !DILocation(column: 5, line: 194, scope: !22)
!84 = !DILocation(column: 9, line: 195, scope: !22)
!85 = !DILocation(column: 5, line: 197, scope: !22)
!86 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !22, type: !11)
!87 = !DILocation(column: 1, line: 197, scope: !22)
!88 = !DILocation(column: 5, line: 198, scope: !22)
!89 = !DILocation(column: 9, line: 199, scope: !22)
!90 = !DILocation(column: 5, line: 200, scope: !22)
!91 = !DILocation(column: 9, line: 201, scope: !22)
!92 = !DILocation(column: 5, line: 203, scope: !22)
!93 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!94 = !DIDerivedType(baseType: !93, size: 64, tag: DW_TAG_reference_type)
!95 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !23, type: !94)
!96 = !DILocation(column: 1, line: 210, scope: !23)
!97 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!98 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !23, type: !97)
!99 = !DILocation(column: 5, line: 211, scope: !23)
!100 = !DILocation(column: 9, line: 212, scope: !23)
!101 = !DILocation(column: 5, line: 213, scope: !23)
!102 = !DILocation(column: 5, line: 214, scope: !23)
!103 = !DILocation(column: 5, line: 215, scope: !23)
!104 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !24, type: !94)
!105 = !DILocation(column: 1, line: 193, scope: !24)
!106 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !24, type: !11)
!107 = !DILocation(column: 5, line: 194, scope: !24)
!108 = !DILocation(column: 9, line: 195, scope: !24)
!109 = !DILocation(column: 5, line: 197, scope: !24)
!110 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !24, type: !11)
!111 = !DILocation(column: 1, line: 197, scope: !24)
!112 = !DILocation(column: 5, line: 198, scope: !24)
!113 = !DILocation(column: 9, line: 199, scope: !24)
!114 = !DILocation(column: 5, line: 200, scope: !24)
!115 = !DILocation(column: 9, line: 201, scope: !24)
!116 = !DILocation(column: 5, line: 203, scope: !24)
!117 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !25, type: !63)
!118 = !DILocation(column: 1, line: 179, scope: !25)
!119 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !25, type: !11)
!120 = !DILocation(column: 5, line: 180, scope: !25)
!121 = !DILocation(column: 9, line: 181, scope: !25)
!122 = !DILocation(column: 5, line: 183, scope: !25)
!123 = !DILocation(column: 5, line: 184, scope: !25)
!124 = !DILocation(column: 5, line: 185, scope: !25)
!125 = !DILocation(column: 9, line: 186, scope: !25)
!126 = !DILocation(column: 5, line: 188, scope: !25)
!127 = !DILocation(column: 5, line: 189, scope: !25)
!128 = !DILocation(column: 5, line: 190, scope: !25)
!129 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !26, type: !94)
!130 = !DILocation(column: 1, line: 179, scope: !26)
!131 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !26, type: !11)
!132 = !DILocation(column: 5, line: 180, scope: !26)
!133 = !DILocation(column: 9, line: 181, scope: !26)
!134 = !DILocation(column: 5, line: 183, scope: !26)
!135 = !DILocation(column: 5, line: 184, scope: !26)
!136 = !DILocation(column: 5, line: 185, scope: !26)
!137 = !DILocation(column: 9, line: 186, scope: !26)
!138 = !DILocation(column: 5, line: 188, scope: !26)
!139 = !DILocation(column: 5, line: 189, scope: !26)
!140 = !DILocation(column: 5, line: 190, scope: !26)