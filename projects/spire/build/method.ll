; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"enum.ritz_module_1.Option$Method" = type {i8, [7 x i8], [8 x i8]}
%"struct.ritz_module_1.Stat" = type {i64, i64, i64, i32, i32, i32, i32, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64}
%"struct.ritz_module_1.Dirent64" = type {i64, i64, i16, i8}
%"struct.ritz_module_1.Timeval" = type {i64, i64}
%"struct.ritz_module_1.Arena" = type {i8*, i64, i64}
%"struct.ritz_module_1.BlockHeader" = type {i64}
%"struct.ritz_module_1.FreeNode" = type {%"struct.ritz_module_1.FreeNode"*}
%"struct.ritz_module_1.SizeBin" = type {%"struct.ritz_module_1.FreeNode"*, i64, i8*, i64, i64}
%"struct.ritz_module_1.GlobalAlloc" = type {[9 x %"struct.ritz_module_1.SizeBin"], i32}
%"struct.ritz_module_1.StrView" = type {i8*, i64}
%"enum.ritz_module_1.Method" = type {i8}
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

define %"enum.ritz_module_1.Option$Method" @"method_from_str"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !17
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !24, metadata !7), !dbg !25
  %".5" = getelementptr [4 x i8], [4 x i8]* @".str.0", i64 0, i64 0 , !dbg !26
  %".6" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".5", 0 , !dbg !26
  %".7" = insertvalue %"struct.ritz_module_1.StrView" %".6", i64 3, 1 , !dbg !26
  %".8" = getelementptr [5 x i8], [5 x i8]* @".str.1", i64 0, i64 0 , !dbg !27
  %".9" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".8", 0 , !dbg !27
  %".10" = insertvalue %"struct.ritz_module_1.StrView" %".9", i64 4, 1 , !dbg !27
  %".11" = getelementptr [4 x i8], [4 x i8]* @".str.2", i64 0, i64 0 , !dbg !28
  %".12" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".11", 0 , !dbg !28
  %".13" = insertvalue %"struct.ritz_module_1.StrView" %".12", i64 3, 1 , !dbg !28
  %".14" = getelementptr [7 x i8], [7 x i8]* @".str.3", i64 0, i64 0 , !dbg !29
  %".15" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".14", 0 , !dbg !29
  %".16" = insertvalue %"struct.ritz_module_1.StrView" %".15", i64 6, 1 , !dbg !29
  %".17" = getelementptr [6 x i8], [6 x i8]* @".str.4", i64 0, i64 0 , !dbg !30
  %".18" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".17", 0 , !dbg !30
  %".19" = insertvalue %"struct.ritz_module_1.StrView" %".18", i64 5, 1 , !dbg !30
  %".20" = getelementptr [5 x i8], [5 x i8]* @".str.5", i64 0, i64 0 , !dbg !31
  %".21" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".20", 0 , !dbg !31
  %".22" = insertvalue %"struct.ritz_module_1.StrView" %".21", i64 4, 1 , !dbg !31
  %".23" = getelementptr [8 x i8], [8 x i8]* @".str.6", i64 0, i64 0 , !dbg !32
  %".24" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".23", 0 , !dbg !32
  %".25" = insertvalue %"struct.ritz_module_1.StrView" %".24", i64 7, 1 , !dbg !32
  %".26" = getelementptr [6 x i8], [6 x i8]* @".str.7", i64 0, i64 0 , !dbg !33
  %".27" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".26", 0 , !dbg !33
  %".28" = insertvalue %"struct.ritz_module_1.StrView" %".27", i64 5, 1 , !dbg !33
  %".29" = getelementptr [8 x i8], [8 x i8]* @".str.8", i64 0, i64 0 , !dbg !34
  %".30" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".29", 0 , !dbg !34
  %".31" = insertvalue %"struct.ritz_module_1.StrView" %".30", i64 7, 1 , !dbg !34
  %".32" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !35
  %"get.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !35
  store %"struct.ritz_module_1.StrView" %".7", %"struct.ritz_module_1.StrView"* %"get.addr", !dbg !35
  %".34" = call i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %".32", %"struct.ritz_module_1.StrView"* %"get.addr"), !dbg !35
  %".35" = sext i32 %".34" to i64 , !dbg !35
  %".36" = icmp eq i64 %".35", 1 , !dbg !35
  br i1 %".36", label %"if.then", label %"if.end", !dbg !35
if.then:
  %"Some.alloca" = alloca %"enum.ritz_module_1.Option$Method", !dbg !36
  %".38" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca", i32 0, i32 0 , !dbg !36
  store i8 0, i8* %".38", !dbg !36
  %".40" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca", i32 0, i32 2 , !dbg !36
  %"GET.alloca" = alloca %"enum.ritz_module_1.Method", !dbg !36
  %".41" = getelementptr %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"GET.alloca", i32 0, i32 0 , !dbg !36
  store i8 0, i8* %".41", !dbg !36
  %".43" = load %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"GET.alloca", !dbg !36
  %".44" = getelementptr [8 x i8], [8 x i8]* %".40", i32 0 , !dbg !36
  %".45" = bitcast [8 x i8]* %".44" to %"enum.ritz_module_1.Method"* , !dbg !36
  store %"enum.ritz_module_1.Method" %".43", %"enum.ritz_module_1.Method"* %".45", !dbg !36
  %".47" = load %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca", !dbg !36
  ret %"enum.ritz_module_1.Option$Method" %".47", !dbg !36
if.end:
  %".49" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !37
  %"post.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !37
  store %"struct.ritz_module_1.StrView" %".10", %"struct.ritz_module_1.StrView"* %"post.addr", !dbg !37
  %".51" = call i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %".49", %"struct.ritz_module_1.StrView"* %"post.addr"), !dbg !37
  %".52" = sext i32 %".51" to i64 , !dbg !37
  %".53" = icmp eq i64 %".52", 1 , !dbg !37
  br i1 %".53", label %"if.then.1", label %"if.end.1", !dbg !37
if.then.1:
  %"Some.alloca.1" = alloca %"enum.ritz_module_1.Option$Method", !dbg !38
  %".55" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.1", i32 0, i32 0 , !dbg !38
  store i8 0, i8* %".55", !dbg !38
  %".57" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.1", i32 0, i32 2 , !dbg !38
  %"POST.alloca" = alloca %"enum.ritz_module_1.Method", !dbg !38
  %".58" = getelementptr %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"POST.alloca", i32 0, i32 0 , !dbg !38
  store i8 1, i8* %".58", !dbg !38
  %".60" = load %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"POST.alloca", !dbg !38
  %".61" = getelementptr [8 x i8], [8 x i8]* %".57", i32 0 , !dbg !38
  %".62" = bitcast [8 x i8]* %".61" to %"enum.ritz_module_1.Method"* , !dbg !38
  store %"enum.ritz_module_1.Method" %".60", %"enum.ritz_module_1.Method"* %".62", !dbg !38
  %".64" = load %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.1", !dbg !38
  ret %"enum.ritz_module_1.Option$Method" %".64", !dbg !38
if.end.1:
  %".66" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !39
  %"put.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !39
  store %"struct.ritz_module_1.StrView" %".13", %"struct.ritz_module_1.StrView"* %"put.addr", !dbg !39
  %".68" = call i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %".66", %"struct.ritz_module_1.StrView"* %"put.addr"), !dbg !39
  %".69" = sext i32 %".68" to i64 , !dbg !39
  %".70" = icmp eq i64 %".69", 1 , !dbg !39
  br i1 %".70", label %"if.then.2", label %"if.end.2", !dbg !39
if.then.2:
  %"Some.alloca.2" = alloca %"enum.ritz_module_1.Option$Method", !dbg !40
  %".72" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.2", i32 0, i32 0 , !dbg !40
  store i8 0, i8* %".72", !dbg !40
  %".74" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.2", i32 0, i32 2 , !dbg !40
  %"PUT.alloca" = alloca %"enum.ritz_module_1.Method", !dbg !40
  %".75" = getelementptr %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"PUT.alloca", i32 0, i32 0 , !dbg !40
  store i8 2, i8* %".75", !dbg !40
  %".77" = load %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"PUT.alloca", !dbg !40
  %".78" = getelementptr [8 x i8], [8 x i8]* %".74", i32 0 , !dbg !40
  %".79" = bitcast [8 x i8]* %".78" to %"enum.ritz_module_1.Method"* , !dbg !40
  store %"enum.ritz_module_1.Method" %".77", %"enum.ritz_module_1.Method"* %".79", !dbg !40
  %".81" = load %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.2", !dbg !40
  ret %"enum.ritz_module_1.Option$Method" %".81", !dbg !40
if.end.2:
  %".83" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !41
  %"delete.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !41
  store %"struct.ritz_module_1.StrView" %".16", %"struct.ritz_module_1.StrView"* %"delete.addr", !dbg !41
  %".85" = call i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %".83", %"struct.ritz_module_1.StrView"* %"delete.addr"), !dbg !41
  %".86" = sext i32 %".85" to i64 , !dbg !41
  %".87" = icmp eq i64 %".86", 1 , !dbg !41
  br i1 %".87", label %"if.then.3", label %"if.end.3", !dbg !41
if.then.3:
  %"Some.alloca.3" = alloca %"enum.ritz_module_1.Option$Method", !dbg !42
  %".89" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.3", i32 0, i32 0 , !dbg !42
  store i8 0, i8* %".89", !dbg !42
  %".91" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.3", i32 0, i32 2 , !dbg !42
  %"DELETE.alloca" = alloca %"enum.ritz_module_1.Method", !dbg !42
  %".92" = getelementptr %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"DELETE.alloca", i32 0, i32 0 , !dbg !42
  store i8 3, i8* %".92", !dbg !42
  %".94" = load %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"DELETE.alloca", !dbg !42
  %".95" = getelementptr [8 x i8], [8 x i8]* %".91", i32 0 , !dbg !42
  %".96" = bitcast [8 x i8]* %".95" to %"enum.ritz_module_1.Method"* , !dbg !42
  store %"enum.ritz_module_1.Method" %".94", %"enum.ritz_module_1.Method"* %".96", !dbg !42
  %".98" = load %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.3", !dbg !42
  ret %"enum.ritz_module_1.Option$Method" %".98", !dbg !42
if.end.3:
  %".100" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !43
  %"patch.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !43
  store %"struct.ritz_module_1.StrView" %".19", %"struct.ritz_module_1.StrView"* %"patch.addr", !dbg !43
  %".102" = call i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %".100", %"struct.ritz_module_1.StrView"* %"patch.addr"), !dbg !43
  %".103" = sext i32 %".102" to i64 , !dbg !43
  %".104" = icmp eq i64 %".103", 1 , !dbg !43
  br i1 %".104", label %"if.then.4", label %"if.end.4", !dbg !43
if.then.4:
  %"Some.alloca.4" = alloca %"enum.ritz_module_1.Option$Method", !dbg !44
  %".106" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.4", i32 0, i32 0 , !dbg !44
  store i8 0, i8* %".106", !dbg !44
  %".108" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.4", i32 0, i32 2 , !dbg !44
  %"PATCH.alloca" = alloca %"enum.ritz_module_1.Method", !dbg !44
  %".109" = getelementptr %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"PATCH.alloca", i32 0, i32 0 , !dbg !44
  store i8 4, i8* %".109", !dbg !44
  %".111" = load %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"PATCH.alloca", !dbg !44
  %".112" = getelementptr [8 x i8], [8 x i8]* %".108", i32 0 , !dbg !44
  %".113" = bitcast [8 x i8]* %".112" to %"enum.ritz_module_1.Method"* , !dbg !44
  store %"enum.ritz_module_1.Method" %".111", %"enum.ritz_module_1.Method"* %".113", !dbg !44
  %".115" = load %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.4", !dbg !44
  ret %"enum.ritz_module_1.Option$Method" %".115", !dbg !44
if.end.4:
  %".117" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !45
  %"head.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !45
  store %"struct.ritz_module_1.StrView" %".22", %"struct.ritz_module_1.StrView"* %"head.addr", !dbg !45
  %".119" = call i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %".117", %"struct.ritz_module_1.StrView"* %"head.addr"), !dbg !45
  %".120" = sext i32 %".119" to i64 , !dbg !45
  %".121" = icmp eq i64 %".120", 1 , !dbg !45
  br i1 %".121", label %"if.then.5", label %"if.end.5", !dbg !45
if.then.5:
  %"Some.alloca.5" = alloca %"enum.ritz_module_1.Option$Method", !dbg !46
  %".123" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.5", i32 0, i32 0 , !dbg !46
  store i8 0, i8* %".123", !dbg !46
  %".125" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.5", i32 0, i32 2 , !dbg !46
  %"HEAD.alloca" = alloca %"enum.ritz_module_1.Method", !dbg !46
  %".126" = getelementptr %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"HEAD.alloca", i32 0, i32 0 , !dbg !46
  store i8 5, i8* %".126", !dbg !46
  %".128" = load %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"HEAD.alloca", !dbg !46
  %".129" = getelementptr [8 x i8], [8 x i8]* %".125", i32 0 , !dbg !46
  %".130" = bitcast [8 x i8]* %".129" to %"enum.ritz_module_1.Method"* , !dbg !46
  store %"enum.ritz_module_1.Method" %".128", %"enum.ritz_module_1.Method"* %".130", !dbg !46
  %".132" = load %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.5", !dbg !46
  ret %"enum.ritz_module_1.Option$Method" %".132", !dbg !46
if.end.5:
  %".134" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !47
  %"options.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !47
  store %"struct.ritz_module_1.StrView" %".25", %"struct.ritz_module_1.StrView"* %"options.addr", !dbg !47
  %".136" = call i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %".134", %"struct.ritz_module_1.StrView"* %"options.addr"), !dbg !47
  %".137" = sext i32 %".136" to i64 , !dbg !47
  %".138" = icmp eq i64 %".137", 1 , !dbg !47
  br i1 %".138", label %"if.then.6", label %"if.end.6", !dbg !47
if.then.6:
  %"Some.alloca.6" = alloca %"enum.ritz_module_1.Option$Method", !dbg !48
  %".140" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.6", i32 0, i32 0 , !dbg !48
  store i8 0, i8* %".140", !dbg !48
  %".142" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.6", i32 0, i32 2 , !dbg !48
  %"OPTIONS.alloca" = alloca %"enum.ritz_module_1.Method", !dbg !48
  %".143" = getelementptr %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"OPTIONS.alloca", i32 0, i32 0 , !dbg !48
  store i8 6, i8* %".143", !dbg !48
  %".145" = load %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"OPTIONS.alloca", !dbg !48
  %".146" = getelementptr [8 x i8], [8 x i8]* %".142", i32 0 , !dbg !48
  %".147" = bitcast [8 x i8]* %".146" to %"enum.ritz_module_1.Method"* , !dbg !48
  store %"enum.ritz_module_1.Method" %".145", %"enum.ritz_module_1.Method"* %".147", !dbg !48
  %".149" = load %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.6", !dbg !48
  ret %"enum.ritz_module_1.Option$Method" %".149", !dbg !48
if.end.6:
  %".151" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !49
  %"trace.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !49
  store %"struct.ritz_module_1.StrView" %".28", %"struct.ritz_module_1.StrView"* %"trace.addr", !dbg !49
  %".153" = call i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %".151", %"struct.ritz_module_1.StrView"* %"trace.addr"), !dbg !49
  %".154" = sext i32 %".153" to i64 , !dbg !49
  %".155" = icmp eq i64 %".154", 1 , !dbg !49
  br i1 %".155", label %"if.then.7", label %"if.end.7", !dbg !49
if.then.7:
  %"Some.alloca.7" = alloca %"enum.ritz_module_1.Option$Method", !dbg !50
  %".157" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.7", i32 0, i32 0 , !dbg !50
  store i8 0, i8* %".157", !dbg !50
  %".159" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.7", i32 0, i32 2 , !dbg !50
  %"TRACE.alloca" = alloca %"enum.ritz_module_1.Method", !dbg !50
  %".160" = getelementptr %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"TRACE.alloca", i32 0, i32 0 , !dbg !50
  store i8 7, i8* %".160", !dbg !50
  %".162" = load %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"TRACE.alloca", !dbg !50
  %".163" = getelementptr [8 x i8], [8 x i8]* %".159", i32 0 , !dbg !50
  %".164" = bitcast [8 x i8]* %".163" to %"enum.ritz_module_1.Method"* , !dbg !50
  store %"enum.ritz_module_1.Method" %".162", %"enum.ritz_module_1.Method"* %".164", !dbg !50
  %".166" = load %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.7", !dbg !50
  ret %"enum.ritz_module_1.Option$Method" %".166", !dbg !50
if.end.7:
  %".168" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !51
  %"connect.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !51
  store %"struct.ritz_module_1.StrView" %".31", %"struct.ritz_module_1.StrView"* %"connect.addr", !dbg !51
  %".170" = call i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %".168", %"struct.ritz_module_1.StrView"* %"connect.addr"), !dbg !51
  %".171" = sext i32 %".170" to i64 , !dbg !51
  %".172" = icmp eq i64 %".171", 1 , !dbg !51
  br i1 %".172", label %"if.then.8", label %"if.end.8", !dbg !51
if.then.8:
  %"Some.alloca.8" = alloca %"enum.ritz_module_1.Option$Method", !dbg !52
  %".174" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.8", i32 0, i32 0 , !dbg !52
  store i8 0, i8* %".174", !dbg !52
  %".176" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.8", i32 0, i32 2 , !dbg !52
  %"CONNECT.alloca" = alloca %"enum.ritz_module_1.Method", !dbg !52
  %".177" = getelementptr %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"CONNECT.alloca", i32 0, i32 0 , !dbg !52
  store i8 8, i8* %".177", !dbg !52
  %".179" = load %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"CONNECT.alloca", !dbg !52
  %".180" = getelementptr [8 x i8], [8 x i8]* %".176", i32 0 , !dbg !52
  %".181" = bitcast [8 x i8]* %".180" to %"enum.ritz_module_1.Method"* , !dbg !52
  store %"enum.ritz_module_1.Method" %".179", %"enum.ritz_module_1.Method"* %".181", !dbg !52
  %".183" = load %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"Some.alloca.8", !dbg !52
  ret %"enum.ritz_module_1.Option$Method" %".183", !dbg !52
if.end.8:
  %"None.alloca" = alloca %"enum.ritz_module_1.Option$Method", !dbg !53
  %".185" = getelementptr %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"None.alloca", i32 0, i32 0 , !dbg !53
  store i8 1, i8* %".185", !dbg !53
  %".187" = load %"enum.ritz_module_1.Option$Method", %"enum.ritz_module_1.Option$Method"* %"None.alloca", !dbg !53
  ret %"enum.ritz_module_1.Option$Method" %".187", !dbg !53
}

define %"struct.ritz_module_1.StrView" @"method_to_str"(%"enum.ritz_module_1.Method" %"m.arg") !dbg !18
{
entry:
  %"m" = alloca %"enum.ritz_module_1.Method"
  store %"enum.ritz_module_1.Method" %"m.arg", %"enum.ritz_module_1.Method"* %"m"
  %".4" = load %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"m", !dbg !54
  %"match.enum" = alloca %"enum.ritz_module_1.Method", !dbg !54
  store %"enum.ritz_module_1.Method" %".4", %"enum.ritz_module_1.Method"* %"match.enum", !dbg !54
  %".6" = getelementptr %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"match.enum", i32 0, i32 0 , !dbg !54
  %".7" = load i8, i8* %".6", !dbg !54
  switch i8 %".7", label %"match.unreachable" [i8 0, label %"match.arm.0" i8 1, label %"match.arm.1" i8 2, label %"match.arm.2" i8 3, label %"match.arm.3" i8 4, label %"match.arm.4" i8 5, label %"match.arm.5" i8 6, label %"match.arm.6" i8 7, label %"match.arm.7" i8 8, label %"match.arm.8"]  , !dbg !54
match.arm.0:
  %".10" = getelementptr [4 x i8], [4 x i8]* @".str.9", i64 0, i64 0 , !dbg !54
  %".11" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".10", 0 , !dbg !54
  %".12" = insertvalue %"struct.ritz_module_1.StrView" %".11", i64 3, 1 , !dbg !54
  br label %"match.merge", !dbg !54
match.arm.1:
  %".14" = getelementptr [5 x i8], [5 x i8]* @".str.10", i64 0, i64 0 , !dbg !54
  %".15" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".14", 0 , !dbg !54
  %".16" = insertvalue %"struct.ritz_module_1.StrView" %".15", i64 4, 1 , !dbg !54
  br label %"match.merge", !dbg !54
match.arm.2:
  %".18" = getelementptr [4 x i8], [4 x i8]* @".str.11", i64 0, i64 0 , !dbg !54
  %".19" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".18", 0 , !dbg !54
  %".20" = insertvalue %"struct.ritz_module_1.StrView" %".19", i64 3, 1 , !dbg !54
  br label %"match.merge", !dbg !54
match.arm.3:
  %".22" = getelementptr [7 x i8], [7 x i8]* @".str.12", i64 0, i64 0 , !dbg !54
  %".23" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".22", 0 , !dbg !54
  %".24" = insertvalue %"struct.ritz_module_1.StrView" %".23", i64 6, 1 , !dbg !54
  br label %"match.merge", !dbg !54
match.arm.4:
  %".26" = getelementptr [6 x i8], [6 x i8]* @".str.13", i64 0, i64 0 , !dbg !54
  %".27" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".26", 0 , !dbg !54
  %".28" = insertvalue %"struct.ritz_module_1.StrView" %".27", i64 5, 1 , !dbg !54
  br label %"match.merge", !dbg !54
match.arm.5:
  %".30" = getelementptr [5 x i8], [5 x i8]* @".str.14", i64 0, i64 0 , !dbg !54
  %".31" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".30", 0 , !dbg !54
  %".32" = insertvalue %"struct.ritz_module_1.StrView" %".31", i64 4, 1 , !dbg !54
  br label %"match.merge", !dbg !54
match.arm.6:
  %".34" = getelementptr [8 x i8], [8 x i8]* @".str.15", i64 0, i64 0 , !dbg !54
  %".35" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".34", 0 , !dbg !54
  %".36" = insertvalue %"struct.ritz_module_1.StrView" %".35", i64 7, 1 , !dbg !54
  br label %"match.merge", !dbg !54
match.arm.7:
  %".38" = getelementptr [6 x i8], [6 x i8]* @".str.16", i64 0, i64 0 , !dbg !54
  %".39" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".38", 0 , !dbg !54
  %".40" = insertvalue %"struct.ritz_module_1.StrView" %".39", i64 5, 1 , !dbg !54
  br label %"match.merge", !dbg !54
match.arm.8:
  %".42" = getelementptr [8 x i8], [8 x i8]* @".str.17", i64 0, i64 0 , !dbg !54
  %".43" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".42", 0 , !dbg !54
  %".44" = insertvalue %"struct.ritz_module_1.StrView" %".43", i64 7, 1 , !dbg !54
  br label %"match.merge", !dbg !54
match.merge:
  %".46" = phi  %"struct.ritz_module_1.StrView" [%".12", %"match.arm.0"], [%".16", %"match.arm.1"], [%".20", %"match.arm.2"], [%".24", %"match.arm.3"], [%".28", %"match.arm.4"], [%".32", %"match.arm.5"], [%".36", %"match.arm.6"], [%".40", %"match.arm.7"], [%".44", %"match.arm.8"] , !dbg !54
  ret %"struct.ritz_module_1.StrView" %".46", !dbg !54
match.unreachable:
  unreachable
}

define i32 @"method_is_safe"(%"enum.ritz_module_1.Method" %"m.arg") !dbg !19
{
entry:
  %"m" = alloca %"enum.ritz_module_1.Method"
  store %"enum.ritz_module_1.Method" %"m.arg", %"enum.ritz_module_1.Method"* %"m"
  %".4" = load %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"m", !dbg !55
  %"match.enum" = alloca %"enum.ritz_module_1.Method", !dbg !55
  store %"enum.ritz_module_1.Method" %".4", %"enum.ritz_module_1.Method"* %"match.enum", !dbg !55
  %".6" = getelementptr %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"match.enum", i32 0, i32 0 , !dbg !55
  %".7" = load i8, i8* %".6", !dbg !55
  switch i8 %".7", label %"match.arm.4" [i8 0, label %"match.arm.0" i8 5, label %"match.arm.1" i8 6, label %"match.arm.2" i8 7, label %"match.arm.3"]  , !dbg !55
match.arm.0:
  br label %"match.merge", !dbg !55
match.arm.1:
  br label %"match.merge", !dbg !55
match.arm.2:
  br label %"match.merge", !dbg !55
match.arm.3:
  br label %"match.merge", !dbg !55
match.arm.4:
  br label %"match.merge", !dbg !55
match.merge:
  %".15" = phi  i64 [1, %"match.arm.0"], [1, %"match.arm.1"], [1, %"match.arm.2"], [1, %"match.arm.3"], [0, %"match.arm.4"] , !dbg !55
  %".16" = trunc i64 %".15" to i32 , !dbg !55
  ret i32 %".16", !dbg !55
match.unreachable:
  unreachable
}

define i32 @"method_is_idempotent"(%"enum.ritz_module_1.Method" %"m.arg") !dbg !20
{
entry:
  %"m" = alloca %"enum.ritz_module_1.Method"
  store %"enum.ritz_module_1.Method" %"m.arg", %"enum.ritz_module_1.Method"* %"m"
  %".4" = load %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"m", !dbg !56
  %"match.enum" = alloca %"enum.ritz_module_1.Method", !dbg !56
  store %"enum.ritz_module_1.Method" %".4", %"enum.ritz_module_1.Method"* %"match.enum", !dbg !56
  %".6" = getelementptr %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"match.enum", i32 0, i32 0 , !dbg !56
  %".7" = load i8, i8* %".6", !dbg !56
  switch i8 %".7", label %"match.arm.6" [i8 0, label %"match.arm.0" i8 5, label %"match.arm.1" i8 2, label %"match.arm.2" i8 3, label %"match.arm.3" i8 6, label %"match.arm.4" i8 7, label %"match.arm.5"]  , !dbg !56
match.arm.0:
  br label %"match.merge", !dbg !56
match.arm.1:
  br label %"match.merge", !dbg !56
match.arm.2:
  br label %"match.merge", !dbg !56
match.arm.3:
  br label %"match.merge", !dbg !56
match.arm.4:
  br label %"match.merge", !dbg !56
match.arm.5:
  br label %"match.merge", !dbg !56
match.arm.6:
  br label %"match.merge", !dbg !56
match.merge:
  %".17" = phi  i64 [1, %"match.arm.0"], [1, %"match.arm.1"], [1, %"match.arm.2"], [1, %"match.arm.3"], [1, %"match.arm.4"], [1, %"match.arm.5"], [0, %"match.arm.6"] , !dbg !56
  %".18" = trunc i64 %".17" to i32 , !dbg !56
  ret i32 %".18", !dbg !56
match.unreachable:
  unreachable
}

define i32 @"method_has_body"(%"enum.ritz_module_1.Method" %"m.arg") !dbg !21
{
entry:
  %"m" = alloca %"enum.ritz_module_1.Method"
  store %"enum.ritz_module_1.Method" %"m.arg", %"enum.ritz_module_1.Method"* %"m"
  %".4" = load %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"m", !dbg !57
  %"match.enum" = alloca %"enum.ritz_module_1.Method", !dbg !57
  store %"enum.ritz_module_1.Method" %".4", %"enum.ritz_module_1.Method"* %"match.enum", !dbg !57
  %".6" = getelementptr %"enum.ritz_module_1.Method", %"enum.ritz_module_1.Method"* %"match.enum", i32 0, i32 0 , !dbg !57
  %".7" = load i8, i8* %".6", !dbg !57
  switch i8 %".7", label %"match.arm.3" [i8 1, label %"match.arm.0" i8 2, label %"match.arm.1" i8 4, label %"match.arm.2"]  , !dbg !57
match.arm.0:
  br label %"match.merge", !dbg !57
match.arm.1:
  br label %"match.merge", !dbg !57
match.arm.2:
  br label %"match.merge", !dbg !57
match.arm.3:
  br label %"match.merge", !dbg !57
match.merge:
  %".14" = phi  i64 [1, %"match.arm.0"], [1, %"match.arm.1"], [1, %"match.arm.2"], [0, %"match.arm.3"] , !dbg !57
  %".15" = trunc i64 %".14" to i32 , !dbg !57
  ret i32 %".15", !dbg !57
match.unreachable:
  unreachable
}

@".str.0" = private constant [4 x i8] c"GET\00"
@".str.1" = private constant [5 x i8] c"POST\00"
@".str.2" = private constant [4 x i8] c"PUT\00"
@".str.3" = private constant [7 x i8] c"DELETE\00"
@".str.4" = private constant [6 x i8] c"PATCH\00"
@".str.5" = private constant [5 x i8] c"HEAD\00"
@".str.6" = private constant [8 x i8] c"OPTIONS\00"
@".str.7" = private constant [6 x i8] c"TRACE\00"
@".str.8" = private constant [8 x i8] c"CONNECT\00"
@".str.9" = private constant [4 x i8] c"GET\00"
@".str.10" = private constant [5 x i8] c"POST\00"
@".str.11" = private constant [4 x i8] c"PUT\00"
@".str.12" = private constant [7 x i8] c"DELETE\00"
@".str.13" = private constant [6 x i8] c"PATCH\00"
@".str.14" = private constant [5 x i8] c"HEAD\00"
@".str.15" = private constant [8 x i8] c"OPTIONS\00"
@".str.16" = private constant [6 x i8] c"TRACE\00"
@".str.17" = private constant [8 x i8] c"CONNECT\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/spire/lib/http", filename: "method.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 23, name: "method_from_str", scopeLine: 23, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 54, name: "method_to_str", scopeLine: 54, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 67, name: "method_is_safe", scopeLine: 67, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 76, name: "method_is_idempotent", scopeLine: 76, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 87, name: "method_has_body", scopeLine: 87, type: !4, unit: !1)
!22 = !DICompositeType(align: 64, file: !0, name: "StrView", size: 128, tag: DW_TAG_structure_type)
!23 = !DIDerivedType(baseType: !22, size: 64, tag: DW_TAG_pointer_type)
!24 = !DILocalVariable(file: !0, line: 23, name: "s", scope: !17, type: !23)
!25 = !DILocation(column: 1, line: 23, scope: !17)
!26 = !DILocation(column: 5, line: 24, scope: !17)
!27 = !DILocation(column: 5, line: 25, scope: !17)
!28 = !DILocation(column: 5, line: 26, scope: !17)
!29 = !DILocation(column: 5, line: 27, scope: !17)
!30 = !DILocation(column: 5, line: 28, scope: !17)
!31 = !DILocation(column: 5, line: 29, scope: !17)
!32 = !DILocation(column: 5, line: 30, scope: !17)
!33 = !DILocation(column: 5, line: 31, scope: !17)
!34 = !DILocation(column: 5, line: 32, scope: !17)
!35 = !DILocation(column: 5, line: 33, scope: !17)
!36 = !DILocation(column: 9, line: 34, scope: !17)
!37 = !DILocation(column: 5, line: 35, scope: !17)
!38 = !DILocation(column: 9, line: 36, scope: !17)
!39 = !DILocation(column: 5, line: 37, scope: !17)
!40 = !DILocation(column: 9, line: 38, scope: !17)
!41 = !DILocation(column: 5, line: 39, scope: !17)
!42 = !DILocation(column: 9, line: 40, scope: !17)
!43 = !DILocation(column: 5, line: 41, scope: !17)
!44 = !DILocation(column: 9, line: 42, scope: !17)
!45 = !DILocation(column: 5, line: 43, scope: !17)
!46 = !DILocation(column: 9, line: 44, scope: !17)
!47 = !DILocation(column: 5, line: 45, scope: !17)
!48 = !DILocation(column: 9, line: 46, scope: !17)
!49 = !DILocation(column: 5, line: 47, scope: !17)
!50 = !DILocation(column: 9, line: 48, scope: !17)
!51 = !DILocation(column: 5, line: 49, scope: !17)
!52 = !DILocation(column: 9, line: 50, scope: !17)
!53 = !DILocation(column: 5, line: 51, scope: !17)
!54 = !DILocation(column: 5, line: 55, scope: !18)
!55 = !DILocation(column: 5, line: 68, scope: !19)
!56 = !DILocation(column: 5, line: 77, scope: !20)
!57 = !DILocation(column: 5, line: 88, scope: !21)