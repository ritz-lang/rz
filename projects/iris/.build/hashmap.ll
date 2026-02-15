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
%"struct.ritz_module_1.HashMapEntryI64" = type {i64, i64, i32}
%"struct.ritz_module_1.HashMapI64" = type {%"struct.ritz_module_1.HashMapEntryI64"*, i64, i64, i64}
declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

@"BLOCK_SIZES" = internal constant [9 x i64] [i64 32, i64 48, i64 80, i64 144, i64 272, i64 528, i64 1040, i64 2064, i64 0]
@"g_alloc" = internal global %"struct.ritz_module_1.GlobalAlloc" zeroinitializer
define i32 @"HashMapI64_drop"(%"struct.ritz_module_1.HashMapI64"* %"self.arg") !dbg !17
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"self.arg", metadata !206, metadata !7), !dbg !207
  %".4" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"self.arg", i32 0, i32 0 , !dbg !208
  %".5" = load %"struct.ritz_module_1.HashMapEntryI64"*, %"struct.ritz_module_1.HashMapEntryI64"** %".4", !dbg !208
  %".6" = bitcast %"struct.ritz_module_1.HashMapEntryI64"* %".5" to i8* , !dbg !208
  %".7" = icmp ne i8* %".6", null , !dbg !209
  br i1 %".7", label %"if.then", label %"if.end", !dbg !209
if.then:
  %".9" = call i32 @"free"(i8* %".6"), !dbg !209
  br label %"if.end", !dbg !209
if.end:
  %".11" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"self.arg", i32 0, i32 0 , !dbg !210
  %".12" = bitcast i8* null to %"struct.ritz_module_1.HashMapEntryI64"* , !dbg !210
  store %"struct.ritz_module_1.HashMapEntryI64"* %".12", %"struct.ritz_module_1.HashMapEntryI64"** %".11", !dbg !210
  %".14" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"self.arg", i32 0, i32 1 , !dbg !211
  store i64 0, i64* %".14", !dbg !211
  %".16" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"self.arg", i32 0, i32 2 , !dbg !212
  store i64 0, i64* %".16", !dbg !212
  %".18" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"self.arg", i32 0, i32 3 , !dbg !213
  store i64 0, i64* %".18", !dbg !213
  ret i32 0, !dbg !213
}

define i64 @"HashMapI64_len"(%"struct.ritz_module_1.HashMapI64"* %"self.arg") !dbg !18
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"self.arg", metadata !214, metadata !7), !dbg !215
  %".4" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"self.arg", i32 0, i32 2 , !dbg !216
  %".5" = load i64, i64* %".4", !dbg !216
  ret i64 %".5", !dbg !216
}

define i64 @"HashMapI64_cap"(%"struct.ritz_module_1.HashMapI64"* %"self.arg") !dbg !19
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"self.arg", metadata !217, metadata !7), !dbg !218
  %".4" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"self.arg", i32 0, i32 1 , !dbg !219
  %".5" = load i64, i64* %".4", !dbg !219
  ret i64 %".5", !dbg !219
}

define i32 @"HashMapI64_is_empty"(%"struct.ritz_module_1.HashMapI64"* %"self.arg") !dbg !20
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"self.arg", metadata !220, metadata !7), !dbg !221
  %".4" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"self.arg", i32 0, i32 2 , !dbg !222
  %".5" = load i64, i64* %".4", !dbg !222
  %".6" = icmp eq i64 %".5", 0 , !dbg !222
  br i1 %".6", label %"if.then", label %"if.end", !dbg !222
if.then:
  %".8" = trunc i64 1 to i32 , !dbg !223
  ret i32 %".8", !dbg !223
if.end:
  %".10" = trunc i64 0 to i32 , !dbg !224
  ret i32 %".10", !dbg !224
}

define i32 @"HashMapI64_insert"(%"struct.ritz_module_1.HashMapI64"* %"self.arg", i64 %"key.arg", i64 %"value.arg") !dbg !21
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"self.arg", metadata !225, metadata !7), !dbg !226
  %"key" = alloca i64
  store i64 %"key.arg", i64* %"key"
  call void @"llvm.dbg.declare"(metadata i64* %"key", metadata !227, metadata !7), !dbg !226
  %"value" = alloca i64
  store i64 %"value.arg", i64* %"value"
  call void @"llvm.dbg.declare"(metadata i64* %"value", metadata !228, metadata !7), !dbg !226
  %".10" = load i64, i64* %"key", !dbg !229
  %".11" = load i64, i64* %"value", !dbg !229
  %".12" = call i32 @"hashmap_i64_insert"(%"struct.ritz_module_1.HashMapI64"* %"self.arg", i64 %".10", i64 %".11"), !dbg !229
  ret i32 %".12", !dbg !229
}

define i64 @"HashMapI64_get"(%"struct.ritz_module_1.HashMapI64"* %"self.arg", i64 %"key.arg") !dbg !22
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"self.arg", metadata !230, metadata !7), !dbg !231
  %"key" = alloca i64
  store i64 %"key.arg", i64* %"key"
  call void @"llvm.dbg.declare"(metadata i64* %"key", metadata !232, metadata !7), !dbg !231
  %".7" = load i64, i64* %"key", !dbg !233
  %".8" = call i64 @"hashmap_i64_get"(%"struct.ritz_module_1.HashMapI64"* %"self.arg", i64 %".7"), !dbg !233
  ret i64 %".8", !dbg !233
}

define i32 @"HashMapI64_contains"(%"struct.ritz_module_1.HashMapI64"* %"self.arg", i64 %"key.arg") !dbg !23
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"self.arg", metadata !234, metadata !7), !dbg !235
  %"key" = alloca i64
  store i64 %"key.arg", i64* %"key"
  call void @"llvm.dbg.declare"(metadata i64* %"key", metadata !236, metadata !7), !dbg !235
  %".7" = load i64, i64* %"key", !dbg !237
  %".8" = call i32 @"hashmap_i64_contains"(%"struct.ritz_module_1.HashMapI64"* %"self.arg", i64 %".7"), !dbg !237
  ret i32 %".8", !dbg !237
}

define i32 @"HashMapI64_remove"(%"struct.ritz_module_1.HashMapI64"* %"self.arg", i64 %"key.arg") !dbg !24
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"self.arg", metadata !238, metadata !7), !dbg !239
  %"key" = alloca i64
  store i64 %"key.arg", i64* %"key"
  call void @"llvm.dbg.declare"(metadata i64* %"key", metadata !240, metadata !7), !dbg !239
  %".7" = load i64, i64* %"key", !dbg !241
  %".8" = call i32 @"hashmap_i64_remove"(%"struct.ritz_module_1.HashMapI64"* %"self.arg", i64 %".7"), !dbg !241
  ret i32 %".8", !dbg !241
}

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

declare i64 @"fnv1a_init"()

declare i64 @"fnv1a_byte"(i64 %".1", i8 %".2")

declare i64 @"fnv1a_i32"(i64 %".1", i32 %".2")

declare i64 @"fnv1a_i64"(i64 %".1", i64 %".2")

declare i64 @"fnv1a_u64"(i64 %".1", i64 %".2")

declare i64 @"hash_i32"(i32 %".1")

declare i64 @"hash_i64"(i64 %".1")

declare i64 @"hash_u64"(i64 %".1")

declare i32 @"eq_i32"(i32 %".1", i32 %".2")

declare i32 @"eq_i64"(i64 %".1", i64 %".2")

declare i32 @"eq_u64"(i64 %".1", i64 %".2")

define %"struct.ritz_module_1.HashMapI64" @"hashmap_i64_new"() !dbg !25
{
entry:
  %".2" = call %"struct.ritz_module_1.HashMapI64" @"hashmap_i64_with_cap"(i64 16), !dbg !37
  ret %"struct.ritz_module_1.HashMapI64" %".2", !dbg !37
}

define %"struct.ritz_module_1.HashMapI64" @"hashmap_i64_with_cap"(i64 %"cap.arg") !dbg !26
{
entry:
  %"cap" = alloca i64
  %"m.addr" = alloca %"struct.ritz_module_1.HashMapI64", !dbg !40
  %"m.drop_flag" = alloca i1, !dbg !40
  %"actual_cap.addr" = alloca i64, !dbg !48
  %"i" = alloca i64, !dbg !56
  store i1 0, i1* %"m.drop_flag", !dbg !40
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !38, metadata !7), !dbg !39
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"m.addr", metadata !42, metadata !7), !dbg !43
  %".7" = load %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", !dbg !44
  %".8" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", i32 0, i32 0 , !dbg !44
  %".9" = bitcast i8* null to %"struct.ritz_module_1.HashMapEntryI64"* , !dbg !44
  store %"struct.ritz_module_1.HashMapEntryI64"* %".9", %"struct.ritz_module_1.HashMapEntryI64"** %".8", !dbg !44
  %".11" = load %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", !dbg !45
  %".12" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", i32 0, i32 1 , !dbg !45
  store i64 0, i64* %".12", !dbg !45
  %".14" = load %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", !dbg !46
  %".15" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", i32 0, i32 2 , !dbg !46
  store i64 0, i64* %".15", !dbg !46
  %".17" = load %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", !dbg !47
  %".18" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", i32 0, i32 3 , !dbg !47
  store i64 0, i64* %".18", !dbg !47
  store i64 16, i64* %"actual_cap.addr", !dbg !48
  call void @"llvm.dbg.declare"(metadata i64* %"actual_cap.addr", metadata !49, metadata !7), !dbg !50
  br label %"while.cond", !dbg !51
while.cond:
  %".23" = load i64, i64* %"actual_cap.addr", !dbg !51
  %".24" = load i64, i64* %"cap", !dbg !51
  %".25" = icmp slt i64 %".23", %".24" , !dbg !51
  br i1 %".25", label %"while.body", label %"while.end", !dbg !51
while.body:
  %".27" = load i64, i64* %"actual_cap.addr", !dbg !52
  %".28" = mul i64 %".27", 2, !dbg !52
  store i64 %".28", i64* %"actual_cap.addr", !dbg !52
  br label %"while.cond", !dbg !52
while.end:
  %".31" = load i64, i64* %"actual_cap.addr", !dbg !53
  %".32" = mul i64 %".31", 24, !dbg !53
  %".33" = call i8* @"malloc"(i64 %".32"), !dbg !54
  %".34" = bitcast i8* %".33" to %"struct.ritz_module_1.HashMapEntryI64"* , !dbg !54
  %".35" = load %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", !dbg !54
  %".36" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", i32 0, i32 0 , !dbg !54
  store %"struct.ritz_module_1.HashMapEntryI64"* %".34", %"struct.ritz_module_1.HashMapEntryI64"** %".36", !dbg !54
  %".38" = load i64, i64* %"actual_cap.addr", !dbg !55
  %".39" = load %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", !dbg !55
  %".40" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", i32 0, i32 1 , !dbg !55
  store i64 %".38", i64* %".40", !dbg !55
  %".42" = load i64, i64* %"actual_cap.addr", !dbg !56
  store i64 0, i64* %"i", !dbg !56
  br label %"for.cond", !dbg !56
for.cond:
  %".45" = load i64, i64* %"i", !dbg !56
  %".46" = icmp slt i64 %".45", %".42" , !dbg !56
  br i1 %".46", label %"for.body", label %"for.end", !dbg !56
for.body:
  %".48" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", i32 0, i32 0 , !dbg !57
  %".49" = load %"struct.ritz_module_1.HashMapEntryI64"*, %"struct.ritz_module_1.HashMapEntryI64"** %".48", !dbg !57
  %".50" = load i64, i64* %"i", !dbg !57
  %".51" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".49", i64 %".50" , !dbg !57
  %".52" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".51", i32 0, i32 2 , !dbg !58
  %".53" = trunc i64 0 to i32 , !dbg !58
  store i32 %".53", i32* %".52", !dbg !58
  br label %"for.incr", !dbg !58
for.incr:
  %".56" = load i64, i64* %"i", !dbg !58
  %".57" = add i64 %".56", 1, !dbg !58
  store i64 %".57", i64* %"i", !dbg !58
  br label %"for.cond", !dbg !58
for.end:
  %".60" = load %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.addr", !dbg !59
  ret %"struct.ritz_module_1.HashMapI64" %".60", !dbg !59
}

define i64 @"hashmap_i64_len"(%"struct.ritz_module_1.HashMapI64"* %"m.arg") !dbg !27
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"m.arg", metadata !61, metadata !7), !dbg !62
  %".4" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 2 , !dbg !63
  %".5" = load i64, i64* %".4", !dbg !63
  ret i64 %".5", !dbg !63
}

define i64 @"hashmap_i64_cap"(%"struct.ritz_module_1.HashMapI64"* %"m.arg") !dbg !28
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"m.arg", metadata !64, metadata !7), !dbg !65
  %".4" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 1 , !dbg !66
  %".5" = load i64, i64* %".4", !dbg !66
  ret i64 %".5", !dbg !66
}

define i32 @"hashmap_i64_is_empty"(%"struct.ritz_module_1.HashMapI64"* %"m.arg") !dbg !29
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"m.arg", metadata !67, metadata !7), !dbg !68
  %".4" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 2 , !dbg !69
  %".5" = load i64, i64* %".4", !dbg !69
  %".6" = icmp eq i64 %".5", 0 , !dbg !69
  br i1 %".6", label %"if.then", label %"if.end", !dbg !69
if.then:
  %".8" = trunc i64 1 to i32 , !dbg !70
  ret i32 %".8", !dbg !70
if.end:
  %".10" = trunc i64 0 to i32 , !dbg !71
  ret i32 %".10", !dbg !71
}

define i32 @"hashmap_i64_drop"(%"struct.ritz_module_1.HashMapI64"* %"m.arg") !dbg !30
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"m.arg", metadata !72, metadata !7), !dbg !73
  %".4" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 0 , !dbg !74
  %".5" = load %"struct.ritz_module_1.HashMapEntryI64"*, %"struct.ritz_module_1.HashMapEntryI64"** %".4", !dbg !74
  %".6" = bitcast %"struct.ritz_module_1.HashMapEntryI64"* %".5" to i8* , !dbg !74
  %".7" = icmp ne i8* %".6", null , !dbg !75
  br i1 %".7", label %"if.then", label %"if.end", !dbg !75
if.then:
  %".9" = call i32 @"free"(i8* %".6"), !dbg !75
  br label %"if.end", !dbg !75
if.end:
  %".11" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 0 , !dbg !76
  %".12" = bitcast i8* null to %"struct.ritz_module_1.HashMapEntryI64"* , !dbg !76
  store %"struct.ritz_module_1.HashMapEntryI64"* %".12", %"struct.ritz_module_1.HashMapEntryI64"** %".11", !dbg !76
  %".14" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 1 , !dbg !77
  store i64 0, i64* %".14", !dbg !77
  %".16" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 2 , !dbg !78
  store i64 0, i64* %".16", !dbg !78
  %".18" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 3 , !dbg !79
  store i64 0, i64* %".18", !dbg !79
  ret i32 0, !dbg !79
}

define i64 @"hashmap_i64_find_slot"(%"struct.ritz_module_1.HashMapI64"* %"m.arg", i64 %"key.arg") !dbg !31
{
entry:
  %"idx.addr" = alloca i64, !dbg !85
  %"first_tombstone.addr" = alloca i64, !dbg !88
  %"i.addr" = alloca i64, !dbg !91
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"m.arg", metadata !80, metadata !7), !dbg !81
  %"key" = alloca i64
  store i64 %"key.arg", i64* %"key"
  call void @"llvm.dbg.declare"(metadata i64* %"key", metadata !82, metadata !7), !dbg !81
  %".7" = load i64, i64* %"key", !dbg !83
  %".8" = call i64 @"hash_i64"(i64 %".7"), !dbg !83
  %".9" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 1 , !dbg !84
  %".10" = load i64, i64* %".9", !dbg !84
  %".11" = sub i64 %".10", 1, !dbg !84
  %".12" = and i64 %".8", %".11", !dbg !85
  store i64 %".12", i64* %"idx.addr", !dbg !85
  call void @"llvm.dbg.declare"(metadata i64* %"idx.addr", metadata !86, metadata !7), !dbg !87
  %".15" = sub i64 0, 1, !dbg !88
  store i64 %".15", i64* %"first_tombstone.addr", !dbg !88
  call void @"llvm.dbg.declare"(metadata i64* %"first_tombstone.addr", metadata !89, metadata !7), !dbg !90
  store i64 0, i64* %"i.addr", !dbg !91
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !92, metadata !7), !dbg !93
  br label %"while.cond", !dbg !94
while.cond:
  %".21" = load i64, i64* %"i.addr", !dbg !94
  %".22" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 1 , !dbg !94
  %".23" = load i64, i64* %".22", !dbg !94
  %".24" = icmp slt i64 %".21", %".23" , !dbg !94
  br i1 %".24", label %"while.body", label %"while.end", !dbg !94
while.body:
  %".26" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 0 , !dbg !95
  %".27" = load %"struct.ritz_module_1.HashMapEntryI64"*, %"struct.ritz_module_1.HashMapEntryI64"** %".26", !dbg !95
  %".28" = load i64, i64* %"idx.addr", !dbg !95
  %".29" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".27", i64 %".28" , !dbg !95
  %".30" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".29", i32 0, i32 2 , !dbg !96
  %".31" = load i32, i32* %".30", !dbg !96
  %".32" = sext i32 %".31" to i64 , !dbg !96
  %".33" = icmp eq i64 %".32", 0 , !dbg !96
  br i1 %".33", label %"if.then", label %"if.end", !dbg !96
while.end:
  %".75" = load i64, i64* %"first_tombstone.addr", !dbg !106
  %".76" = icmp sge i64 %".75", 0 , !dbg !106
  br i1 %".76", label %"if.then.6", label %"if.end.6", !dbg !106
if.then:
  %".35" = load i64, i64* %"first_tombstone.addr", !dbg !97
  %".36" = icmp sge i64 %".35", 0 , !dbg !97
  br i1 %".36", label %"if.then.1", label %"if.end.1", !dbg !97
if.end:
  %".42" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".29", i32 0, i32 2 , !dbg !100
  %".43" = load i32, i32* %".42", !dbg !100
  %".44" = sext i32 %".43" to i64 , !dbg !100
  %".45" = icmp eq i64 %".44", 2 , !dbg !100
  br i1 %".45", label %"if.then.2", label %"if.end.2", !dbg !100
if.then.1:
  %".38" = load i64, i64* %"first_tombstone.addr", !dbg !98
  ret i64 %".38", !dbg !98
if.end.1:
  %".40" = load i64, i64* %"idx.addr", !dbg !99
  ret i64 %".40", !dbg !99
if.then.2:
  %".47" = load i64, i64* %"first_tombstone.addr", !dbg !100
  %".48" = icmp slt i64 %".47", 0 , !dbg !100
  br i1 %".48", label %"if.then.3", label %"if.end.3", !dbg !100
if.end.2:
  %".54" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".29", i32 0, i32 2 , !dbg !102
  %".55" = load i32, i32* %".54", !dbg !102
  %".56" = sext i32 %".55" to i64 , !dbg !102
  %".57" = icmp eq i64 %".56", 1 , !dbg !102
  br i1 %".57", label %"if.then.4", label %"if.end.4", !dbg !102
if.then.3:
  %".50" = load i64, i64* %"idx.addr", !dbg !101
  store i64 %".50", i64* %"first_tombstone.addr", !dbg !101
  br label %"if.end.3", !dbg !101
if.end.3:
  br label %"if.end.2", !dbg !101
if.then.4:
  %".59" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".29", i32 0, i32 0 , !dbg !102
  %".60" = load i64, i64* %".59", !dbg !102
  %".61" = load i64, i64* %"key", !dbg !102
  %".62" = icmp eq i64 %".60", %".61" , !dbg !102
  br i1 %".62", label %"if.then.5", label %"if.end.5", !dbg !102
if.end.4:
  %".67" = load i64, i64* %"idx.addr", !dbg !104
  %".68" = add i64 %".67", 1, !dbg !104
  %".69" = and i64 %".68", %".11", !dbg !104
  store i64 %".69", i64* %"idx.addr", !dbg !104
  %".71" = load i64, i64* %"i.addr", !dbg !105
  %".72" = add i64 %".71", 1, !dbg !105
  store i64 %".72", i64* %"i.addr", !dbg !105
  br label %"while.cond", !dbg !105
if.then.5:
  %".64" = load i64, i64* %"idx.addr", !dbg !103
  ret i64 %".64", !dbg !103
if.end.5:
  br label %"if.end.4", !dbg !103
if.then.6:
  %".78" = load i64, i64* %"first_tombstone.addr", !dbg !107
  ret i64 %".78", !dbg !107
if.end.6:
  %".80" = sub i64 0, 1, !dbg !108
  ret i64 %".80", !dbg !108
}

define i32 @"hashmap_i64_insert"(%"struct.ritz_module_1.HashMapI64"* %"m.arg", i64 %"key.arg", i64 %"value.arg") !dbg !32
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"m.arg", metadata !109, metadata !7), !dbg !110
  %"key" = alloca i64
  store i64 %"key.arg", i64* %"key"
  call void @"llvm.dbg.declare"(metadata i64* %"key", metadata !111, metadata !7), !dbg !110
  %"value" = alloca i64
  store i64 %"value.arg", i64* %"value"
  call void @"llvm.dbg.declare"(metadata i64* %"value", metadata !112, metadata !7), !dbg !110
  %".10" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 2 , !dbg !113
  %".11" = load i64, i64* %".10", !dbg !113
  %".12" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 3 , !dbg !113
  %".13" = load i64, i64* %".12", !dbg !113
  %".14" = add i64 %".11", %".13", !dbg !113
  %".15" = add i64 %".14", 1, !dbg !113
  %".16" = mul i64 %".15", 100, !dbg !113
  %".17" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 1 , !dbg !113
  %".18" = load i64, i64* %".17", !dbg !113
  %".19" = sdiv i64 %".16", %".18", !dbg !113
  %".20" = icmp sgt i64 %".19", 75 , !dbg !114
  br i1 %".20", label %"if.then", label %"if.end", !dbg !114
if.then:
  %".22" = call i32 @"hashmap_i64_grow"(%"struct.ritz_module_1.HashMapI64"* %"m.arg"), !dbg !114
  br label %"if.end", !dbg !114
if.end:
  %".24" = load i64, i64* %"key", !dbg !115
  %".25" = call i64 @"hashmap_i64_find_slot"(%"struct.ritz_module_1.HashMapI64"* %"m.arg", i64 %".24"), !dbg !115
  %".26" = icmp slt i64 %".25", 0 , !dbg !116
  br i1 %".26", label %"if.then.1", label %"if.end.1", !dbg !116
if.then.1:
  ret i32 0, !dbg !117
if.end.1:
  %".29" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 0 , !dbg !118
  %".30" = load %"struct.ritz_module_1.HashMapEntryI64"*, %"struct.ritz_module_1.HashMapEntryI64"** %".29", !dbg !118
  %".31" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".30", i64 %".25" , !dbg !118
  %".32" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".31", i32 0, i32 2 , !dbg !119
  %".33" = load i32, i32* %".32", !dbg !119
  %".34" = sext i32 %".33" to i64 , !dbg !119
  %".35" = icmp eq i64 %".34", 1 , !dbg !119
  br i1 %".35", label %"if.then.2", label %"if.else", !dbg !119
if.then.2:
  %".37" = load i64, i64* %"value", !dbg !120
  %".38" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".31", i32 0, i32 1 , !dbg !120
  store i64 %".37", i64* %".38", !dbg !120
  br label %"if.end.2", !dbg !126
if.else:
  %".40" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".31", i32 0, i32 2 , !dbg !121
  %".41" = load i32, i32* %".40", !dbg !121
  %".42" = sext i32 %".41" to i64 , !dbg !121
  %".43" = icmp eq i64 %".42", 2 , !dbg !121
  br i1 %".43", label %"if.then.3", label %"if.end.3", !dbg !121
if.end.2:
  ret i32 0, !dbg !126
if.then.3:
  %".45" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 3 , !dbg !122
  %".46" = load i64, i64* %".45", !dbg !122
  %".47" = sub i64 %".46", 1, !dbg !122
  %".48" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 3 , !dbg !122
  store i64 %".47", i64* %".48", !dbg !122
  br label %"if.end.3", !dbg !122
if.end.3:
  %".51" = load i64, i64* %"key", !dbg !123
  %".52" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".31", i32 0, i32 0 , !dbg !123
  store i64 %".51", i64* %".52", !dbg !123
  %".54" = load i64, i64* %"value", !dbg !124
  %".55" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".31", i32 0, i32 1 , !dbg !124
  store i64 %".54", i64* %".55", !dbg !124
  %".57" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".31", i32 0, i32 2 , !dbg !125
  %".58" = trunc i64 1 to i32 , !dbg !125
  store i32 %".58", i32* %".57", !dbg !125
  %".60" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 2 , !dbg !126
  %".61" = load i64, i64* %".60", !dbg !126
  %".62" = add i64 %".61", 1, !dbg !126
  %".63" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 2 , !dbg !126
  store i64 %".62", i64* %".63", !dbg !126
  br label %"if.end.2", !dbg !126
}

define i64 @"hashmap_i64_get"(%"struct.ritz_module_1.HashMapI64"* %"m.arg", i64 %"key.arg") !dbg !33
{
entry:
  %"idx.addr" = alloca i64, !dbg !132
  %"i.addr" = alloca i64, !dbg !135
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"m.arg", metadata !127, metadata !7), !dbg !128
  %"key" = alloca i64
  store i64 %"key.arg", i64* %"key"
  call void @"llvm.dbg.declare"(metadata i64* %"key", metadata !129, metadata !7), !dbg !128
  %".7" = load i64, i64* %"key", !dbg !130
  %".8" = call i64 @"hash_i64"(i64 %".7"), !dbg !130
  %".9" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 1 , !dbg !131
  %".10" = load i64, i64* %".9", !dbg !131
  %".11" = sub i64 %".10", 1, !dbg !131
  %".12" = and i64 %".8", %".11", !dbg !132
  store i64 %".12", i64* %"idx.addr", !dbg !132
  call void @"llvm.dbg.declare"(metadata i64* %"idx.addr", metadata !133, metadata !7), !dbg !134
  store i64 0, i64* %"i.addr", !dbg !135
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !136, metadata !7), !dbg !137
  br label %"while.cond", !dbg !138
while.cond:
  %".18" = load i64, i64* %"i.addr", !dbg !138
  %".19" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 1 , !dbg !138
  %".20" = load i64, i64* %".19", !dbg !138
  %".21" = icmp slt i64 %".18", %".20" , !dbg !138
  br i1 %".21", label %"while.body", label %"while.end", !dbg !138
while.body:
  %".23" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 0 , !dbg !139
  %".24" = load %"struct.ritz_module_1.HashMapEntryI64"*, %"struct.ritz_module_1.HashMapEntryI64"** %".23", !dbg !139
  %".25" = load i64, i64* %"idx.addr", !dbg !139
  %".26" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".24", i64 %".25" , !dbg !139
  %".27" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".26", i32 0, i32 2 , !dbg !140
  %".28" = load i32, i32* %".27", !dbg !140
  %".29" = sext i32 %".28" to i64 , !dbg !140
  %".30" = icmp eq i64 %".29", 0 , !dbg !140
  br i1 %".30", label %"if.then", label %"if.end", !dbg !140
while.end:
  ret i64 0, !dbg !146
if.then:
  ret i64 0, !dbg !141
if.end:
  %".33" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".26", i32 0, i32 2 , !dbg !142
  %".34" = load i32, i32* %".33", !dbg !142
  %".35" = sext i32 %".34" to i64 , !dbg !142
  %".36" = icmp eq i64 %".35", 1 , !dbg !142
  br i1 %".36", label %"if.then.1", label %"if.end.1", !dbg !142
if.then.1:
  %".38" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".26", i32 0, i32 0 , !dbg !142
  %".39" = load i64, i64* %".38", !dbg !142
  %".40" = load i64, i64* %"key", !dbg !142
  %".41" = icmp eq i64 %".39", %".40" , !dbg !142
  br i1 %".41", label %"if.then.2", label %"if.end.2", !dbg !142
if.end.1:
  %".47" = load i64, i64* %"idx.addr", !dbg !144
  %".48" = add i64 %".47", 1, !dbg !144
  %".49" = and i64 %".48", %".11", !dbg !144
  store i64 %".49", i64* %"idx.addr", !dbg !144
  %".51" = load i64, i64* %"i.addr", !dbg !145
  %".52" = add i64 %".51", 1, !dbg !145
  store i64 %".52", i64* %"i.addr", !dbg !145
  br label %"while.cond", !dbg !145
if.then.2:
  %".43" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".26", i32 0, i32 1 , !dbg !143
  %".44" = load i64, i64* %".43", !dbg !143
  ret i64 %".44", !dbg !143
if.end.2:
  br label %"if.end.1", !dbg !143
}

define i32 @"hashmap_i64_contains"(%"struct.ritz_module_1.HashMapI64"* %"m.arg", i64 %"key.arg") !dbg !34
{
entry:
  %"idx.addr" = alloca i64, !dbg !152
  %"i.addr" = alloca i64, !dbg !155
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"m.arg", metadata !147, metadata !7), !dbg !148
  %"key" = alloca i64
  store i64 %"key.arg", i64* %"key"
  call void @"llvm.dbg.declare"(metadata i64* %"key", metadata !149, metadata !7), !dbg !148
  %".7" = load i64, i64* %"key", !dbg !150
  %".8" = call i64 @"hash_i64"(i64 %".7"), !dbg !150
  %".9" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 1 , !dbg !151
  %".10" = load i64, i64* %".9", !dbg !151
  %".11" = sub i64 %".10", 1, !dbg !151
  %".12" = and i64 %".8", %".11", !dbg !152
  store i64 %".12", i64* %"idx.addr", !dbg !152
  call void @"llvm.dbg.declare"(metadata i64* %"idx.addr", metadata !153, metadata !7), !dbg !154
  store i64 0, i64* %"i.addr", !dbg !155
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !156, metadata !7), !dbg !157
  br label %"while.cond", !dbg !158
while.cond:
  %".18" = load i64, i64* %"i.addr", !dbg !158
  %".19" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 1 , !dbg !158
  %".20" = load i64, i64* %".19", !dbg !158
  %".21" = icmp slt i64 %".18", %".20" , !dbg !158
  br i1 %".21", label %"while.body", label %"while.end", !dbg !158
while.body:
  %".23" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 0 , !dbg !159
  %".24" = load %"struct.ritz_module_1.HashMapEntryI64"*, %"struct.ritz_module_1.HashMapEntryI64"** %".23", !dbg !159
  %".25" = load i64, i64* %"idx.addr", !dbg !159
  %".26" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".24", i64 %".25" , !dbg !159
  %".27" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".26", i32 0, i32 2 , !dbg !160
  %".28" = load i32, i32* %".27", !dbg !160
  %".29" = sext i32 %".28" to i64 , !dbg !160
  %".30" = icmp eq i64 %".29", 0 , !dbg !160
  br i1 %".30", label %"if.then", label %"if.end", !dbg !160
while.end:
  %".55" = trunc i64 0 to i32 , !dbg !166
  ret i32 %".55", !dbg !166
if.then:
  %".32" = trunc i64 0 to i32 , !dbg !161
  ret i32 %".32", !dbg !161
if.end:
  %".34" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".26", i32 0, i32 2 , !dbg !162
  %".35" = load i32, i32* %".34", !dbg !162
  %".36" = sext i32 %".35" to i64 , !dbg !162
  %".37" = icmp eq i64 %".36", 1 , !dbg !162
  br i1 %".37", label %"if.then.1", label %"if.end.1", !dbg !162
if.then.1:
  %".39" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".26", i32 0, i32 0 , !dbg !162
  %".40" = load i64, i64* %".39", !dbg !162
  %".41" = load i64, i64* %"key", !dbg !162
  %".42" = icmp eq i64 %".40", %".41" , !dbg !162
  br i1 %".42", label %"if.then.2", label %"if.end.2", !dbg !162
if.end.1:
  %".47" = load i64, i64* %"idx.addr", !dbg !164
  %".48" = add i64 %".47", 1, !dbg !164
  %".49" = and i64 %".48", %".11", !dbg !164
  store i64 %".49", i64* %"idx.addr", !dbg !164
  %".51" = load i64, i64* %"i.addr", !dbg !165
  %".52" = add i64 %".51", 1, !dbg !165
  store i64 %".52", i64* %"i.addr", !dbg !165
  br label %"while.cond", !dbg !165
if.then.2:
  %".44" = trunc i64 1 to i32 , !dbg !163
  ret i32 %".44", !dbg !163
if.end.2:
  br label %"if.end.1", !dbg !163
}

define i32 @"hashmap_i64_remove"(%"struct.ritz_module_1.HashMapI64"* %"m.arg", i64 %"key.arg") !dbg !35
{
entry:
  %"idx.addr" = alloca i64, !dbg !172
  %"i.addr" = alloca i64, !dbg !175
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"m.arg", metadata !167, metadata !7), !dbg !168
  %"key" = alloca i64
  store i64 %"key.arg", i64* %"key"
  call void @"llvm.dbg.declare"(metadata i64* %"key", metadata !169, metadata !7), !dbg !168
  %".7" = load i64, i64* %"key", !dbg !170
  %".8" = call i64 @"hash_i64"(i64 %".7"), !dbg !170
  %".9" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 1 , !dbg !171
  %".10" = load i64, i64* %".9", !dbg !171
  %".11" = sub i64 %".10", 1, !dbg !171
  %".12" = and i64 %".8", %".11", !dbg !172
  store i64 %".12", i64* %"idx.addr", !dbg !172
  call void @"llvm.dbg.declare"(metadata i64* %"idx.addr", metadata !173, metadata !7), !dbg !174
  store i64 0, i64* %"i.addr", !dbg !175
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !176, metadata !7), !dbg !177
  br label %"while.cond", !dbg !178
while.cond:
  %".18" = load i64, i64* %"i.addr", !dbg !178
  %".19" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 1 , !dbg !178
  %".20" = load i64, i64* %".19", !dbg !178
  %".21" = icmp slt i64 %".18", %".20" , !dbg !178
  br i1 %".21", label %"while.body", label %"while.end", !dbg !178
while.body:
  %".23" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 0 , !dbg !179
  %".24" = load %"struct.ritz_module_1.HashMapEntryI64"*, %"struct.ritz_module_1.HashMapEntryI64"** %".23", !dbg !179
  %".25" = load i64, i64* %"idx.addr", !dbg !179
  %".26" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".24", i64 %".25" , !dbg !179
  %".27" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".26", i32 0, i32 2 , !dbg !180
  %".28" = load i32, i32* %".27", !dbg !180
  %".29" = sext i32 %".28" to i64 , !dbg !180
  %".30" = icmp eq i64 %".29", 0 , !dbg !180
  br i1 %".30", label %"if.then", label %"if.end", !dbg !180
while.end:
  %".68" = trunc i64 0 to i32 , !dbg !189
  ret i32 %".68", !dbg !189
if.then:
  %".32" = trunc i64 0 to i32 , !dbg !181
  ret i32 %".32", !dbg !181
if.end:
  %".34" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".26", i32 0, i32 2 , !dbg !182
  %".35" = load i32, i32* %".34", !dbg !182
  %".36" = sext i32 %".35" to i64 , !dbg !182
  %".37" = icmp eq i64 %".36", 1 , !dbg !182
  br i1 %".37", label %"if.then.1", label %"if.end.1", !dbg !182
if.then.1:
  %".39" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".26", i32 0, i32 0 , !dbg !182
  %".40" = load i64, i64* %".39", !dbg !182
  %".41" = load i64, i64* %"key", !dbg !182
  %".42" = icmp eq i64 %".40", %".41" , !dbg !182
  br i1 %".42", label %"if.then.2", label %"if.end.2", !dbg !182
if.end.1:
  %".60" = load i64, i64* %"idx.addr", !dbg !187
  %".61" = add i64 %".60", 1, !dbg !187
  %".62" = and i64 %".61", %".11", !dbg !187
  store i64 %".62", i64* %"idx.addr", !dbg !187
  %".64" = load i64, i64* %"i.addr", !dbg !188
  %".65" = add i64 %".64", 1, !dbg !188
  store i64 %".65", i64* %"i.addr", !dbg !188
  br label %"while.cond", !dbg !188
if.then.2:
  %".44" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".26", i32 0, i32 2 , !dbg !183
  %".45" = trunc i64 2 to i32 , !dbg !183
  store i32 %".45", i32* %".44", !dbg !183
  %".47" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 2 , !dbg !184
  %".48" = load i64, i64* %".47", !dbg !184
  %".49" = sub i64 %".48", 1, !dbg !184
  %".50" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 2 , !dbg !184
  store i64 %".49", i64* %".50", !dbg !184
  %".52" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 3 , !dbg !185
  %".53" = load i64, i64* %".52", !dbg !185
  %".54" = add i64 %".53", 1, !dbg !185
  %".55" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 3 , !dbg !185
  store i64 %".54", i64* %".55", !dbg !185
  %".57" = trunc i64 1 to i32 , !dbg !186
  ret i32 %".57", !dbg !186
if.end.2:
  br label %"if.end.1", !dbg !186
}

define i32 @"hashmap_i64_grow"(%"struct.ritz_module_1.HashMapI64"* %"m.arg") !dbg !36
{
entry:
  %"i" = alloca i64, !dbg !200
  %"i.1" = alloca i64, !dbg !203
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.HashMapI64"* %"m.arg", metadata !190, metadata !7), !dbg !191
  %".4" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 0 , !dbg !192
  %".5" = load %"struct.ritz_module_1.HashMapEntryI64"*, %"struct.ritz_module_1.HashMapEntryI64"** %".4", !dbg !192
  %".6" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 1 , !dbg !193
  %".7" = load i64, i64* %".6", !dbg !193
  %".8" = mul i64 %".7", 2, !dbg !194
  %".9" = mul i64 %".8", 24, !dbg !195
  %".10" = call i8* @"malloc"(i64 %".9"), !dbg !196
  %".11" = bitcast i8* %".10" to %"struct.ritz_module_1.HashMapEntryI64"* , !dbg !196
  %".12" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 0 , !dbg !196
  store %"struct.ritz_module_1.HashMapEntryI64"* %".11", %"struct.ritz_module_1.HashMapEntryI64"** %".12", !dbg !196
  %".14" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 1 , !dbg !197
  store i64 %".8", i64* %".14", !dbg !197
  %".16" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 2 , !dbg !198
  store i64 0, i64* %".16", !dbg !198
  %".18" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 3 , !dbg !199
  store i64 0, i64* %".18", !dbg !199
  store i64 0, i64* %"i", !dbg !200
  br label %"for.cond", !dbg !200
for.cond:
  %".22" = load i64, i64* %"i", !dbg !200
  %".23" = icmp slt i64 %".22", %".8" , !dbg !200
  br i1 %".23", label %"for.body", label %"for.end", !dbg !200
for.body:
  %".25" = getelementptr %"struct.ritz_module_1.HashMapI64", %"struct.ritz_module_1.HashMapI64"* %"m.arg", i32 0, i32 0 , !dbg !201
  %".26" = load %"struct.ritz_module_1.HashMapEntryI64"*, %"struct.ritz_module_1.HashMapEntryI64"** %".25", !dbg !201
  %".27" = load i64, i64* %"i", !dbg !201
  %".28" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".26", i64 %".27" , !dbg !201
  %".29" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".28", i32 0, i32 2 , !dbg !202
  %".30" = trunc i64 0 to i32 , !dbg !202
  store i32 %".30", i32* %".29", !dbg !202
  br label %"for.incr", !dbg !202
for.incr:
  %".33" = load i64, i64* %"i", !dbg !202
  %".34" = add i64 %".33", 1, !dbg !202
  store i64 %".34", i64* %"i", !dbg !202
  br label %"for.cond", !dbg !202
for.end:
  store i64 0, i64* %"i.1", !dbg !203
  br label %"for.cond.1", !dbg !203
for.cond.1:
  %".39" = load i64, i64* %"i.1", !dbg !203
  %".40" = icmp slt i64 %".39", %".7" , !dbg !203
  br i1 %".40", label %"for.body.1", label %"for.end.1", !dbg !203
for.body.1:
  %".42" = load i64, i64* %"i.1", !dbg !204
  %".43" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".5", i64 %".42" , !dbg !204
  %".44" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".43", i32 0, i32 2 , !dbg !204
  %".45" = load i32, i32* %".44", !dbg !204
  %".46" = sext i32 %".45" to i64 , !dbg !204
  %".47" = icmp eq i64 %".46", 1 , !dbg !204
  br i1 %".47", label %"if.then", label %"if.end", !dbg !204
for.incr.1:
  %".56" = load i64, i64* %"i.1", !dbg !204
  %".57" = add i64 %".56", 1, !dbg !204
  store i64 %".57", i64* %"i.1", !dbg !204
  br label %"for.cond.1", !dbg !204
for.end.1:
  %".60" = bitcast %"struct.ritz_module_1.HashMapEntryI64"* %".5" to i8* , !dbg !205
  %".61" = call i32 @"free"(i8* %".60"), !dbg !205
  ret i32 %".61", !dbg !205
if.then:
  %".49" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".43", i32 0, i32 0 , !dbg !204
  %".50" = load i64, i64* %".49", !dbg !204
  %".51" = getelementptr %"struct.ritz_module_1.HashMapEntryI64", %"struct.ritz_module_1.HashMapEntryI64"* %".43", i32 0, i32 1 , !dbg !204
  %".52" = load i64, i64* %".51", !dbg !204
  %".53" = call i32 @"hashmap_i64_insert"(%"struct.ritz_module_1.HashMapI64"* %"m.arg", i64 %".50", i64 %".52"), !dbg !204
  br label %"if.end", !dbg !204
if.end:
  br label %"for.incr.1", !dbg !204
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/ritz/ritzlib", filename: "hashmap.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 41, name: "HashMapI64_drop", scopeLine: 41, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 88, name: "HashMapI64_len", scopeLine: 88, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 92, name: "HashMapI64_cap", scopeLine: 92, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 96, name: "HashMapI64_is_empty", scopeLine: 96, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 102, name: "HashMapI64_insert", scopeLine: 102, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 106, name: "HashMapI64_get", scopeLine: 106, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 110, name: "HashMapI64_contains", scopeLine: 110, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 114, name: "HashMapI64_remove", scopeLine: 114, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 54, name: "hashmap_i64_new", scopeLine: 54, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 57, name: "hashmap_i64_with_cap", scopeLine: 57, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 121, name: "hashmap_i64_len", scopeLine: 121, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "hashmap_i64_cap", scopeLine: 124, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 127, name: "hashmap_i64_is_empty", scopeLine: 127, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 133, name: "hashmap_i64_drop", scopeLine: 133, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 147, name: "hashmap_i64_find_slot", scopeLine: 147, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 182, name: "hashmap_i64_insert", scopeLine: 182, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 207, name: "hashmap_i64_get", scopeLine: 207, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 230, name: "hashmap_i64_contains", scopeLine: 230, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 252, name: "hashmap_i64_remove", scopeLine: 252, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 277, name: "hashmap_i64_grow", scopeLine: 277, type: !4, unit: !1)
!37 = !DILocation(column: 5, line: 55, scope: !25)
!38 = !DILocalVariable(file: !0, line: 57, name: "cap", scope: !26, type: !11)
!39 = !DILocation(column: 1, line: 57, scope: !26)
!40 = !DILocation(column: 5, line: 58, scope: !26)
!41 = !DICompositeType(align: 64, file: !0, name: "HashMapI64", size: 256, tag: DW_TAG_structure_type)
!42 = !DILocalVariable(file: !0, line: 58, name: "m", scope: !26, type: !41)
!43 = !DILocation(column: 1, line: 58, scope: !26)
!44 = !DILocation(column: 5, line: 61, scope: !26)
!45 = !DILocation(column: 5, line: 62, scope: !26)
!46 = !DILocation(column: 5, line: 63, scope: !26)
!47 = !DILocation(column: 5, line: 64, scope: !26)
!48 = !DILocation(column: 5, line: 67, scope: !26)
!49 = !DILocalVariable(file: !0, line: 67, name: "actual_cap", scope: !26, type: !11)
!50 = !DILocation(column: 1, line: 67, scope: !26)
!51 = !DILocation(column: 5, line: 68, scope: !26)
!52 = !DILocation(column: 9, line: 69, scope: !26)
!53 = !DILocation(column: 5, line: 71, scope: !26)
!54 = !DILocation(column: 5, line: 72, scope: !26)
!55 = !DILocation(column: 5, line: 73, scope: !26)
!56 = !DILocation(column: 5, line: 76, scope: !26)
!57 = !DILocation(column: 9, line: 77, scope: !26)
!58 = !DILocation(column: 9, line: 78, scope: !26)
!59 = !DILocation(column: 5, line: 80, scope: !26)
!60 = !DIDerivedType(baseType: !41, size: 64, tag: DW_TAG_reference_type)
!61 = !DILocalVariable(file: !0, line: 121, name: "m", scope: !27, type: !60)
!62 = !DILocation(column: 1, line: 121, scope: !27)
!63 = !DILocation(column: 5, line: 122, scope: !27)
!64 = !DILocalVariable(file: !0, line: 124, name: "m", scope: !28, type: !60)
!65 = !DILocation(column: 1, line: 124, scope: !28)
!66 = !DILocation(column: 5, line: 125, scope: !28)
!67 = !DILocalVariable(file: !0, line: 127, name: "m", scope: !29, type: !60)
!68 = !DILocation(column: 1, line: 127, scope: !29)
!69 = !DILocation(column: 5, line: 128, scope: !29)
!70 = !DILocation(column: 9, line: 129, scope: !29)
!71 = !DILocation(column: 5, line: 130, scope: !29)
!72 = !DILocalVariable(file: !0, line: 133, name: "m", scope: !30, type: !60)
!73 = !DILocation(column: 1, line: 133, scope: !30)
!74 = !DILocation(column: 5, line: 134, scope: !30)
!75 = !DILocation(column: 5, line: 135, scope: !30)
!76 = !DILocation(column: 5, line: 137, scope: !30)
!77 = !DILocation(column: 5, line: 138, scope: !30)
!78 = !DILocation(column: 5, line: 139, scope: !30)
!79 = !DILocation(column: 5, line: 140, scope: !30)
!80 = !DILocalVariable(file: !0, line: 147, name: "m", scope: !31, type: !60)
!81 = !DILocation(column: 1, line: 147, scope: !31)
!82 = !DILocalVariable(file: !0, line: 147, name: "key", scope: !31, type: !11)
!83 = !DILocation(column: 5, line: 148, scope: !31)
!84 = !DILocation(column: 5, line: 149, scope: !31)
!85 = !DILocation(column: 5, line: 150, scope: !31)
!86 = !DILocalVariable(file: !0, line: 150, name: "idx", scope: !31, type: !11)
!87 = !DILocation(column: 1, line: 150, scope: !31)
!88 = !DILocation(column: 5, line: 151, scope: !31)
!89 = !DILocalVariable(file: !0, line: 151, name: "first_tombstone", scope: !31, type: !11)
!90 = !DILocation(column: 1, line: 151, scope: !31)
!91 = !DILocation(column: 5, line: 153, scope: !31)
!92 = !DILocalVariable(file: !0, line: 153, name: "i", scope: !31, type: !11)
!93 = !DILocation(column: 1, line: 153, scope: !31)
!94 = !DILocation(column: 5, line: 154, scope: !31)
!95 = !DILocation(column: 9, line: 155, scope: !31)
!96 = !DILocation(column: 9, line: 157, scope: !31)
!97 = !DILocation(column: 13, line: 159, scope: !31)
!98 = !DILocation(column: 17, line: 160, scope: !31)
!99 = !DILocation(column: 13, line: 161, scope: !31)
!100 = !DILocation(column: 9, line: 163, scope: !31)
!101 = !DILocation(column: 17, line: 166, scope: !31)
!102 = !DILocation(column: 9, line: 168, scope: !31)
!103 = !DILocation(column: 17, line: 170, scope: !31)
!104 = !DILocation(column: 9, line: 173, scope: !31)
!105 = !DILocation(column: 9, line: 174, scope: !31)
!106 = !DILocation(column: 5, line: 177, scope: !31)
!107 = !DILocation(column: 9, line: 178, scope: !31)
!108 = !DILocation(column: 5, line: 179, scope: !31)
!109 = !DILocalVariable(file: !0, line: 182, name: "m", scope: !32, type: !60)
!110 = !DILocation(column: 1, line: 182, scope: !32)
!111 = !DILocalVariable(file: !0, line: 182, name: "key", scope: !32, type: !11)
!112 = !DILocalVariable(file: !0, line: 182, name: "value", scope: !32, type: !11)
!113 = !DILocation(column: 5, line: 184, scope: !32)
!114 = !DILocation(column: 5, line: 185, scope: !32)
!115 = !DILocation(column: 5, line: 188, scope: !32)
!116 = !DILocation(column: 5, line: 189, scope: !32)
!117 = !DILocation(column: 9, line: 191, scope: !32)
!118 = !DILocation(column: 5, line: 193, scope: !32)
!119 = !DILocation(column: 5, line: 195, scope: !32)
!120 = !DILocation(column: 9, line: 196, scope: !32)
!121 = !DILocation(column: 9, line: 199, scope: !32)
!122 = !DILocation(column: 13, line: 200, scope: !32)
!123 = !DILocation(column: 9, line: 201, scope: !32)
!124 = !DILocation(column: 9, line: 202, scope: !32)
!125 = !DILocation(column: 9, line: 203, scope: !32)
!126 = !DILocation(column: 9, line: 204, scope: !32)
!127 = !DILocalVariable(file: !0, line: 207, name: "m", scope: !33, type: !60)
!128 = !DILocation(column: 1, line: 207, scope: !33)
!129 = !DILocalVariable(file: !0, line: 207, name: "key", scope: !33, type: !11)
!130 = !DILocation(column: 5, line: 208, scope: !33)
!131 = !DILocation(column: 5, line: 209, scope: !33)
!132 = !DILocation(column: 5, line: 210, scope: !33)
!133 = !DILocalVariable(file: !0, line: 210, name: "idx", scope: !33, type: !11)
!134 = !DILocation(column: 1, line: 210, scope: !33)
!135 = !DILocation(column: 5, line: 212, scope: !33)
!136 = !DILocalVariable(file: !0, line: 212, name: "i", scope: !33, type: !11)
!137 = !DILocation(column: 1, line: 212, scope: !33)
!138 = !DILocation(column: 5, line: 213, scope: !33)
!139 = !DILocation(column: 9, line: 214, scope: !33)
!140 = !DILocation(column: 9, line: 216, scope: !33)
!141 = !DILocation(column: 13, line: 217, scope: !33)
!142 = !DILocation(column: 9, line: 219, scope: !33)
!143 = !DILocation(column: 17, line: 221, scope: !33)
!144 = !DILocation(column: 9, line: 224, scope: !33)
!145 = !DILocation(column: 9, line: 225, scope: !33)
!146 = !DILocation(column: 5, line: 227, scope: !33)
!147 = !DILocalVariable(file: !0, line: 230, name: "m", scope: !34, type: !60)
!148 = !DILocation(column: 1, line: 230, scope: !34)
!149 = !DILocalVariable(file: !0, line: 230, name: "key", scope: !34, type: !11)
!150 = !DILocation(column: 5, line: 231, scope: !34)
!151 = !DILocation(column: 5, line: 232, scope: !34)
!152 = !DILocation(column: 5, line: 233, scope: !34)
!153 = !DILocalVariable(file: !0, line: 233, name: "idx", scope: !34, type: !11)
!154 = !DILocation(column: 1, line: 233, scope: !34)
!155 = !DILocation(column: 5, line: 235, scope: !34)
!156 = !DILocalVariable(file: !0, line: 235, name: "i", scope: !34, type: !11)
!157 = !DILocation(column: 1, line: 235, scope: !34)
!158 = !DILocation(column: 5, line: 236, scope: !34)
!159 = !DILocation(column: 9, line: 237, scope: !34)
!160 = !DILocation(column: 9, line: 239, scope: !34)
!161 = !DILocation(column: 13, line: 240, scope: !34)
!162 = !DILocation(column: 9, line: 242, scope: !34)
!163 = !DILocation(column: 17, line: 244, scope: !34)
!164 = !DILocation(column: 9, line: 246, scope: !34)
!165 = !DILocation(column: 9, line: 247, scope: !34)
!166 = !DILocation(column: 5, line: 249, scope: !34)
!167 = !DILocalVariable(file: !0, line: 252, name: "m", scope: !35, type: !60)
!168 = !DILocation(column: 1, line: 252, scope: !35)
!169 = !DILocalVariable(file: !0, line: 252, name: "key", scope: !35, type: !11)
!170 = !DILocation(column: 5, line: 253, scope: !35)
!171 = !DILocation(column: 5, line: 254, scope: !35)
!172 = !DILocation(column: 5, line: 255, scope: !35)
!173 = !DILocalVariable(file: !0, line: 255, name: "idx", scope: !35, type: !11)
!174 = !DILocation(column: 1, line: 255, scope: !35)
!175 = !DILocation(column: 5, line: 257, scope: !35)
!176 = !DILocalVariable(file: !0, line: 257, name: "i", scope: !35, type: !11)
!177 = !DILocation(column: 1, line: 257, scope: !35)
!178 = !DILocation(column: 5, line: 258, scope: !35)
!179 = !DILocation(column: 9, line: 259, scope: !35)
!180 = !DILocation(column: 9, line: 261, scope: !35)
!181 = !DILocation(column: 13, line: 262, scope: !35)
!182 = !DILocation(column: 9, line: 264, scope: !35)
!183 = !DILocation(column: 17, line: 266, scope: !35)
!184 = !DILocation(column: 17, line: 267, scope: !35)
!185 = !DILocation(column: 17, line: 268, scope: !35)
!186 = !DILocation(column: 17, line: 269, scope: !35)
!187 = !DILocation(column: 9, line: 271, scope: !35)
!188 = !DILocation(column: 9, line: 272, scope: !35)
!189 = !DILocation(column: 5, line: 274, scope: !35)
!190 = !DILocalVariable(file: !0, line: 277, name: "m", scope: !36, type: !60)
!191 = !DILocation(column: 1, line: 277, scope: !36)
!192 = !DILocation(column: 5, line: 278, scope: !36)
!193 = !DILocation(column: 5, line: 279, scope: !36)
!194 = !DILocation(column: 5, line: 282, scope: !36)
!195 = !DILocation(column: 5, line: 283, scope: !36)
!196 = !DILocation(column: 5, line: 284, scope: !36)
!197 = !DILocation(column: 5, line: 285, scope: !36)
!198 = !DILocation(column: 5, line: 286, scope: !36)
!199 = !DILocation(column: 5, line: 287, scope: !36)
!200 = !DILocation(column: 5, line: 290, scope: !36)
!201 = !DILocation(column: 9, line: 291, scope: !36)
!202 = !DILocation(column: 9, line: 292, scope: !36)
!203 = !DILocation(column: 5, line: 295, scope: !36)
!204 = !DILocation(column: 9, line: 296, scope: !36)
!205 = !DILocation(column: 5, line: 301, scope: !36)
!206 = !DILocalVariable(file: !0, line: 41, name: "self", scope: !17, type: !60)
!207 = !DILocation(column: 1, line: 41, scope: !17)
!208 = !DILocation(column: 9, line: 42, scope: !17)
!209 = !DILocation(column: 9, line: 43, scope: !17)
!210 = !DILocation(column: 9, line: 45, scope: !17)
!211 = !DILocation(column: 9, line: 46, scope: !17)
!212 = !DILocation(column: 9, line: 47, scope: !17)
!213 = !DILocation(column: 9, line: 48, scope: !17)
!214 = !DILocalVariable(file: !0, line: 88, name: "self", scope: !18, type: !60)
!215 = !DILocation(column: 1, line: 88, scope: !18)
!216 = !DILocation(column: 9, line: 89, scope: !18)
!217 = !DILocalVariable(file: !0, line: 92, name: "self", scope: !19, type: !60)
!218 = !DILocation(column: 1, line: 92, scope: !19)
!219 = !DILocation(column: 9, line: 93, scope: !19)
!220 = !DILocalVariable(file: !0, line: 96, name: "self", scope: !20, type: !60)
!221 = !DILocation(column: 1, line: 96, scope: !20)
!222 = !DILocation(column: 9, line: 97, scope: !20)
!223 = !DILocation(column: 13, line: 98, scope: !20)
!224 = !DILocation(column: 9, line: 99, scope: !20)
!225 = !DILocalVariable(file: !0, line: 102, name: "self", scope: !21, type: !60)
!226 = !DILocation(column: 1, line: 102, scope: !21)
!227 = !DILocalVariable(file: !0, line: 102, name: "key", scope: !21, type: !11)
!228 = !DILocalVariable(file: !0, line: 102, name: "value", scope: !21, type: !11)
!229 = !DILocation(column: 9, line: 103, scope: !21)
!230 = !DILocalVariable(file: !0, line: 106, name: "self", scope: !22, type: !60)
!231 = !DILocation(column: 1, line: 106, scope: !22)
!232 = !DILocalVariable(file: !0, line: 106, name: "key", scope: !22, type: !11)
!233 = !DILocation(column: 9, line: 107, scope: !22)
!234 = !DILocalVariable(file: !0, line: 110, name: "self", scope: !23, type: !60)
!235 = !DILocation(column: 1, line: 110, scope: !23)
!236 = !DILocalVariable(file: !0, line: 110, name: "key", scope: !23, type: !11)
!237 = !DILocation(column: 9, line: 111, scope: !23)
!238 = !DILocalVariable(file: !0, line: 114, name: "self", scope: !24, type: !60)
!239 = !DILocation(column: 1, line: 114, scope: !24)
!240 = !DILocalVariable(file: !0, line: 114, name: "key", scope: !24, type: !11)
!241 = !DILocation(column: 9, line: 115, scope: !24)