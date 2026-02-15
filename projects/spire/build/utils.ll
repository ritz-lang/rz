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
%"struct.ritz_module_1.StrView" = type {i8*, i64}
%"struct.ritz_module_1.LineBounds" = type {i64, i64}
%"struct.ritz_module_1.String" = type {%"struct.ritz_module_1.Vec$u8"}
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

define i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %"a.arg", %"struct.ritz_module_1.StrView"* %"b.arg") !dbg !17
{
entry:
  %"a" = alloca %"struct.ritz_module_1.StrView"*
  %"i.addr" = alloca i64, !dbg !40
  store %"struct.ritz_module_1.StrView"* %"a.arg", %"struct.ritz_module_1.StrView"** %"a"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"a", metadata !35, metadata !7), !dbg !36
  %"b" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"b.arg", %"struct.ritz_module_1.StrView"** %"b"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"b", metadata !37, metadata !7), !dbg !36
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"a", !dbg !38
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".8", i32 0, i32 1 , !dbg !38
  %".10" = load i64, i64* %".9", !dbg !38
  %".11" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"b", !dbg !38
  %".12" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".11", i32 0, i32 1 , !dbg !38
  %".13" = load i64, i64* %".12", !dbg !38
  %".14" = icmp ne i64 %".10", %".13" , !dbg !38
  br i1 %".14", label %"if.then", label %"if.end", !dbg !38
if.then:
  %".16" = trunc i64 0 to i32 , !dbg !39
  ret i32 %".16", !dbg !39
if.end:
  store i64 0, i64* %"i.addr", !dbg !40
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !41, metadata !7), !dbg !42
  br label %"while.cond", !dbg !43
while.cond:
  %".21" = load i64, i64* %"i.addr", !dbg !43
  %".22" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"a", !dbg !43
  %".23" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".22", i32 0, i32 1 , !dbg !43
  %".24" = load i64, i64* %".23", !dbg !43
  %".25" = icmp slt i64 %".21", %".24" , !dbg !43
  br i1 %".25", label %"while.body", label %"while.end", !dbg !43
while.body:
  %".27" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"a", !dbg !44
  %".28" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".27", i32 0, i32 0 , !dbg !44
  %".29" = load i8*, i8** %".28", !dbg !44
  %".30" = load i64, i64* %"i.addr", !dbg !44
  %".31" = getelementptr i8, i8* %".29", i64 %".30" , !dbg !44
  %".32" = load i8, i8* %".31", !dbg !44
  %".33" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"b", !dbg !44
  %".34" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".33", i32 0, i32 0 , !dbg !44
  %".35" = load i8*, i8** %".34", !dbg !44
  %".36" = load i64, i64* %"i.addr", !dbg !44
  %".37" = getelementptr i8, i8* %".35", i64 %".36" , !dbg !44
  %".38" = load i8, i8* %".37", !dbg !44
  %".39" = icmp ne i8 %".32", %".38" , !dbg !44
  br i1 %".39", label %"if.then.1", label %"if.end.1", !dbg !44
while.end:
  %".47" = trunc i64 1 to i32 , !dbg !47
  ret i32 %".47", !dbg !47
if.then.1:
  %".41" = trunc i64 0 to i32 , !dbg !45
  ret i32 %".41", !dbg !45
if.end.1:
  %".43" = load i64, i64* %"i.addr", !dbg !46
  %".44" = add i64 %".43", 1, !dbg !46
  store i64 %".44", i64* %"i.addr", !dbg !46
  br label %"while.cond", !dbg !46
}

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

declare i32 @"vec_push_str"(%"struct.ritz_module_1.Vec$u8"** %".1", i8* %".2")

declare i8* @"vec_as_str"(%"struct.ritz_module_1.Vec$u8"** %".1")

declare i64 @"vec_read_all_fd"(i32 %".1", %"struct.ritz_module_1.Vec$u8"** %".2")

declare i32 @"vec_find_lines"(%"struct.ritz_module_1.Vec$u8"* %".1", %"struct.ritz_module_1.Vec$LineBounds"** %".2")

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

define %"struct.ritz_module_1.StrView" @"string_as_strview"(%"struct.ritz_module_1.String"* %"s.arg") !dbg !18
{
entry:
  %"s" = alloca %"struct.ritz_module_1.String"*
  %"sv.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !52
  store %"struct.ritz_module_1.String"* %"s.arg", %"struct.ritz_module_1.String"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.String"** %"s", metadata !50, metadata !7), !dbg !51
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"sv.addr", metadata !53, metadata !7), !dbg !54
  %".6" = load %"struct.ritz_module_1.String"*, %"struct.ritz_module_1.String"** %"s", !dbg !55
  %".7" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %".6", i32 0, i32 0 , !dbg !55
  %".8" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", !dbg !55
  %".9" = extractvalue %"struct.ritz_module_1.Vec$u8" %".8", 0 , !dbg !55
  %".10" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"sv.addr", !dbg !55
  %".11" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"sv.addr", i32 0, i32 0 , !dbg !55
  store i8* %".9", i8** %".11", !dbg !55
  %".13" = load %"struct.ritz_module_1.String"*, %"struct.ritz_module_1.String"** %"s", !dbg !56
  %".14" = getelementptr %"struct.ritz_module_1.String", %"struct.ritz_module_1.String"* %".13", i32 0, i32 0 , !dbg !56
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".14", !dbg !56
  %".16" = extractvalue %"struct.ritz_module_1.Vec$u8" %".15", 1 , !dbg !56
  %".17" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"sv.addr", !dbg !56
  %".18" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"sv.addr", i32 0, i32 1 , !dbg !56
  store i64 %".16", i64* %".18", !dbg !56
  %".20" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"sv.addr", !dbg !57
  ret %"struct.ritz_module_1.StrView" %".20", !dbg !57
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !19
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !60, metadata !7), !dbg !61
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !62, metadata !7), !dbg !61
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !63
  %".8" = load i8*, i8** %".7", !dbg !63
  %".9" = load i64, i64* %"idx", !dbg !63
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !63
  %".11" = load i8, i8* %".10", !dbg !63
  ret i8 %".11", !dbg !63
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !20
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !64
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !65, metadata !7), !dbg !66
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !67
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !67
  store i8* null, i8** %".4", !dbg !67
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !68
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !68
  store i64 0, i64* %".7", !dbg !68
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !69
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !69
  store i64 0, i64* %".10", !dbg !69
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !70
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !70
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg") !dbg !21
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !72, metadata !7), !dbg !73
  %".4" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !74
  %".5" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", i32 0, i32 0 , !dbg !74
  %".6" = load i8*, i8** %".5", !dbg !74
  %".7" = icmp ne i8* %".6", null , !dbg !74
  br i1 %".7", label %"if.then", label %"if.end", !dbg !74
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !74
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".9", i32 0, i32 0 , !dbg !74
  %".11" = load i8*, i8** %".10", !dbg !74
  %".12" = call i32 @"free"(i8* %".11"), !dbg !74
  br label %"if.end", !dbg !74
if.end:
  %".14" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !75
  %".15" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".14", i32 0, i32 0 , !dbg !75
  store i8* null, i8** %".15", !dbg !75
  %".17" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !76
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".17", i32 0, i32 1 , !dbg !76
  store i64 0, i64* %".18", !dbg !76
  %".20" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !77
  %".21" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".20", i32 0, i32 2 , !dbg !77
  store i64 0, i64* %".21", !dbg !77
  ret i32 0, !dbg !77
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg") !dbg !22
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !78, metadata !7), !dbg !79
  %".4" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !80
  %".5" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", i32 0, i32 1 , !dbg !80
  store i64 0, i64* %".5", !dbg !80
  ret i32 0, !dbg !80
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg") !dbg !23
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !81, metadata !7), !dbg !82
  %".4" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !83
  %".5" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".4", i32 0, i32 1 , !dbg !83
  %".6" = load i64, i64* %".5", !dbg !83
  %".7" = sub i64 %".6", 1, !dbg !83
  %".8" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !83
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".8", i32 0, i32 1 , !dbg !83
  store i64 %".7", i64* %".9", !dbg !83
  %".11" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !84
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".11", i32 0, i32 0 , !dbg !84
  %".13" = load i8*, i8** %".12", !dbg !84
  %".14" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !84
  %".15" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".14", i32 0, i32 1 , !dbg !84
  %".16" = load i64, i64* %".15", !dbg !84
  %".17" = getelementptr i8, i8* %".13", i64 %".16" , !dbg !84
  %".18" = load i8, i8* %".17", !dbg !84
  ret i8 %".18", !dbg !84
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !24
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !88, metadata !7), !dbg !89
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !91, metadata !7), !dbg !89
  %".7" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !92
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".7", i32 0, i32 1 , !dbg !92
  %".9" = load i64, i64* %".8", !dbg !92
  %".10" = add i64 %".9", 1, !dbg !92
  %".11" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %".10"), !dbg !92
  %".12" = sext i32 %".11" to i64 , !dbg !92
  %".13" = icmp ne i64 %".12", 0 , !dbg !92
  br i1 %".13", label %"if.then", label %"if.end", !dbg !92
if.then:
  %".15" = sub i64 0, 1, !dbg !93
  %".16" = trunc i64 %".15" to i32 , !dbg !93
  ret i32 %".16", !dbg !93
if.end:
  %".18" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !94
  %".19" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !94
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".19", i32 0, i32 0 , !dbg !94
  %".21" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".20", !dbg !94
  %".22" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !94
  %".23" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".22", i32 0, i32 1 , !dbg !94
  %".24" = load i64, i64* %".23", !dbg !94
  %".25" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".21", i64 %".24" , !dbg !94
  store %"struct.ritz_module_1.LineBounds" %".18", %"struct.ritz_module_1.LineBounds"* %".25", !dbg !94
  %".27" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !95
  %".28" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".27", i32 0, i32 1 , !dbg !95
  %".29" = load i64, i64* %".28", !dbg !95
  %".30" = add i64 %".29", 1, !dbg !95
  %".31" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !95
  %".32" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".31", i32 0, i32 1 , !dbg !95
  store i64 %".30", i64* %".32", !dbg !95
  %".34" = trunc i64 0 to i32 , !dbg !96
  ret i32 %".34", !dbg !96
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !25
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !97, metadata !7), !dbg !98
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !99, metadata !7), !dbg !98
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !100, metadata !7), !dbg !98
  %".10" = load i8, i8* %"item", !dbg !101
  %".11" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !101
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".11", i32 0, i32 0 , !dbg !101
  %".13" = load i8*, i8** %".12", !dbg !101
  %".14" = load i64, i64* %"idx", !dbg !101
  %".15" = getelementptr i8, i8* %".13", i64 %".14" , !dbg !101
  store i8 %".10", i8* %".15", !dbg !101
  %".17" = trunc i64 0 to i32 , !dbg !102
  ret i32 %".17", !dbg !102
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8 %"item.arg") !dbg !26
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !103, metadata !7), !dbg !104
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !105, metadata !7), !dbg !104
  %".7" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !106
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", i32 0, i32 1 , !dbg !106
  %".9" = load i64, i64* %".8", !dbg !106
  %".10" = add i64 %".9", 1, !dbg !106
  %".11" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %".10"), !dbg !106
  %".12" = sext i32 %".11" to i64 , !dbg !106
  %".13" = icmp ne i64 %".12", 0 , !dbg !106
  br i1 %".13", label %"if.then", label %"if.end", !dbg !106
if.then:
  %".15" = sub i64 0, 1, !dbg !107
  %".16" = trunc i64 %".15" to i32 , !dbg !107
  ret i32 %".16", !dbg !107
if.end:
  %".18" = load i8, i8* %"item", !dbg !108
  %".19" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !108
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".19", i32 0, i32 0 , !dbg !108
  %".21" = load i8*, i8** %".20", !dbg !108
  %".22" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !108
  %".23" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".22", i32 0, i32 1 , !dbg !108
  %".24" = load i64, i64* %".23", !dbg !108
  %".25" = getelementptr i8, i8* %".21", i64 %".24" , !dbg !108
  store i8 %".18", i8* %".25", !dbg !108
  %".27" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !109
  %".28" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".27", i32 0, i32 1 , !dbg !109
  %".29" = load i64, i64* %".28", !dbg !109
  %".30" = add i64 %".29", 1, !dbg !109
  %".31" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !109
  %".32" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".31", i32 0, i32 1 , !dbg !109
  store i64 %".30", i64* %".32", !dbg !109
  %".34" = trunc i64 0 to i32 , !dbg !110
  ret i32 %".34", !dbg !110
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !27
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !113
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !111, metadata !7), !dbg !112
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !114, metadata !7), !dbg !115
  %".6" = load i64, i64* %"cap", !dbg !116
  %".7" = icmp sle i64 %".6", 0 , !dbg !116
  br i1 %".7", label %"if.then", label %"if.end", !dbg !116
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !117
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !117
  store i8* null, i8** %".10", !dbg !117
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !118
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !118
  store i64 0, i64* %".13", !dbg !118
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !119
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !119
  store i64 0, i64* %".16", !dbg !119
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !120
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !120
if.end:
  %".20" = load i64, i64* %"cap", !dbg !121
  %".21" = mul i64 %".20", 1, !dbg !121
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !122
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !122
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !122
  store i8* %".22", i8** %".24", !dbg !122
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !123
  %".27" = load i8*, i8** %".26", !dbg !123
  %".28" = icmp eq i8* %".27", null , !dbg !123
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !123
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !124
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !124
  store i64 0, i64* %".31", !dbg !124
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !125
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !125
  store i64 0, i64* %".34", !dbg !125
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !126
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !126
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !127
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !127
  store i64 0, i64* %".39", !dbg !127
  %".41" = load i64, i64* %"cap", !dbg !128
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !128
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !128
  store i64 %".41", i64* %".43", !dbg !128
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !129
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !129
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !28
{
entry:
  %"i" = alloca i64, !dbg !135
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !130, metadata !7), !dbg !131
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !133, metadata !7), !dbg !131
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !134, metadata !7), !dbg !131
  %".10" = load i64, i64* %"len", !dbg !135
  store i64 0, i64* %"i", !dbg !135
  br label %"for.cond", !dbg !135
for.cond:
  %".13" = load i64, i64* %"i", !dbg !135
  %".14" = icmp slt i64 %".13", %".10" , !dbg !135
  br i1 %".14", label %"for.body", label %"for.end", !dbg !135
for.body:
  %".16" = load i8*, i8** %"data", !dbg !135
  %".17" = load i64, i64* %"i", !dbg !135
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !135
  %".19" = load i8, i8* %".18", !dbg !135
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i8 %".19"), !dbg !135
  %".21" = sext i32 %".20" to i64 , !dbg !135
  %".22" = icmp ne i64 %".21", 0 , !dbg !135
  br i1 %".22", label %"if.then", label %"if.end", !dbg !135
for.incr:
  %".28" = load i64, i64* %"i", !dbg !136
  %".29" = add i64 %".28", 1, !dbg !136
  store i64 %".29", i64* %"i", !dbg !136
  br label %"for.cond", !dbg !136
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !137
  ret i32 %".32", !dbg !137
if.then:
  %".24" = sub i64 0, 1, !dbg !136
  %".25" = trunc i64 %".24" to i32 , !dbg !136
  ret i32 %".25", !dbg !136
if.end:
  br label %"for.incr", !dbg !136
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"needed.arg") !dbg !29
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !143
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !138, metadata !7), !dbg !139
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !140, metadata !7), !dbg !139
  %".7" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !141
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".7", i32 0, i32 2 , !dbg !141
  %".9" = load i64, i64* %".8", !dbg !141
  %".10" = load i64, i64* %"needed", !dbg !141
  %".11" = icmp sge i64 %".9", %".10" , !dbg !141
  br i1 %".11", label %"if.then", label %"if.end", !dbg !141
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !142
  ret i32 %".13", !dbg !142
if.end:
  %".15" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !143
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".15", i32 0, i32 2 , !dbg !143
  %".17" = load i64, i64* %".16", !dbg !143
  store i64 %".17", i64* %"new_cap.addr", !dbg !143
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !144, metadata !7), !dbg !145
  %".20" = load i64, i64* %"new_cap.addr", !dbg !146
  %".21" = icmp eq i64 %".20", 0 , !dbg !146
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !146
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !147
  br label %"if.end.1", !dbg !147
if.end.1:
  br label %"while.cond", !dbg !148
while.cond:
  %".26" = load i64, i64* %"new_cap.addr", !dbg !148
  %".27" = load i64, i64* %"needed", !dbg !148
  %".28" = icmp slt i64 %".26", %".27" , !dbg !148
  br i1 %".28", label %"while.body", label %"while.end", !dbg !148
while.body:
  %".30" = load i64, i64* %"new_cap.addr", !dbg !149
  %".31" = mul i64 %".30", 2, !dbg !149
  store i64 %".31", i64* %"new_cap.addr", !dbg !149
  br label %"while.cond", !dbg !149
while.end:
  %".34" = load i64, i64* %"new_cap.addr", !dbg !150
  %".35" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %".34"), !dbg !150
  ret i32 %".35", !dbg !150
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %"needed.arg") !dbg !30
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !156
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !151, metadata !7), !dbg !152
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !153, metadata !7), !dbg !152
  %".7" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !154
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".7", i32 0, i32 2 , !dbg !154
  %".9" = load i64, i64* %".8", !dbg !154
  %".10" = load i64, i64* %"needed", !dbg !154
  %".11" = icmp sge i64 %".9", %".10" , !dbg !154
  br i1 %".11", label %"if.then", label %"if.end", !dbg !154
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !155
  ret i32 %".13", !dbg !155
if.end:
  %".15" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !156
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".15", i32 0, i32 2 , !dbg !156
  %".17" = load i64, i64* %".16", !dbg !156
  store i64 %".17", i64* %"new_cap.addr", !dbg !156
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !157, metadata !7), !dbg !158
  %".20" = load i64, i64* %"new_cap.addr", !dbg !159
  %".21" = icmp eq i64 %".20", 0 , !dbg !159
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !159
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !160
  br label %"if.end.1", !dbg !160
if.end.1:
  br label %"while.cond", !dbg !161
while.cond:
  %".26" = load i64, i64* %"new_cap.addr", !dbg !161
  %".27" = load i64, i64* %"needed", !dbg !161
  %".28" = icmp slt i64 %".26", %".27" , !dbg !161
  br i1 %".28", label %"while.body", label %"while.end", !dbg !161
while.body:
  %".30" = load i64, i64* %"new_cap.addr", !dbg !162
  %".31" = mul i64 %".30", 2, !dbg !162
  store i64 %".31", i64* %"new_cap.addr", !dbg !162
  br label %"while.cond", !dbg !162
while.end:
  %".34" = load i64, i64* %"new_cap.addr", !dbg !163
  %".35" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %".34"), !dbg !163
  ret i32 %".35", !dbg !163
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"** %"v.arg", i64 %"new_cap.arg") !dbg !31
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"** %"v.arg", metadata !164, metadata !7), !dbg !165
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !166, metadata !7), !dbg !165
  %".7" = load i64, i64* %"new_cap", !dbg !167
  %".8" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !167
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".8", i32 0, i32 2 , !dbg !167
  %".10" = load i64, i64* %".9", !dbg !167
  %".11" = icmp sle i64 %".7", %".10" , !dbg !167
  br i1 %".11", label %"if.then", label %"if.end", !dbg !167
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !168
  ret i32 %".13", !dbg !168
if.end:
  %".15" = load i64, i64* %"new_cap", !dbg !169
  %".16" = mul i64 %".15", 1, !dbg !169
  %".17" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !170
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".17", i32 0, i32 0 , !dbg !170
  %".19" = load i8*, i8** %".18", !dbg !170
  %".20" = call i8* @"realloc"(i8* %".19", i64 %".16"), !dbg !170
  %".21" = icmp eq i8* %".20", null , !dbg !171
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !171
if.then.1:
  %".23" = sub i64 0, 1, !dbg !172
  %".24" = trunc i64 %".23" to i32 , !dbg !172
  ret i32 %".24", !dbg !172
if.end.1:
  %".26" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !173
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".26", i32 0, i32 0 , !dbg !173
  store i8* %".20", i8** %".27", !dbg !173
  %".29" = load i64, i64* %"new_cap", !dbg !174
  %".30" = load %"struct.ritz_module_1.Vec$u8"*, %"struct.ritz_module_1.Vec$u8"** %"v.arg", !dbg !174
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %".30", i32 0, i32 2 , !dbg !174
  store i64 %".29", i64* %".31", !dbg !174
  %".33" = trunc i64 0 to i32 , !dbg !175
  ret i32 %".33", !dbg !175
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", i64 %"new_cap.arg") !dbg !32
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", metadata !176, metadata !7), !dbg !177
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !178, metadata !7), !dbg !177
  %".7" = load i64, i64* %"new_cap", !dbg !179
  %".8" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !179
  %".9" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".8", i32 0, i32 2 , !dbg !179
  %".10" = load i64, i64* %".9", !dbg !179
  %".11" = icmp sle i64 %".7", %".10" , !dbg !179
  br i1 %".11", label %"if.then", label %"if.end", !dbg !179
if.then:
  %".13" = trunc i64 0 to i32 , !dbg !180
  ret i32 %".13", !dbg !180
if.end:
  %".15" = load i64, i64* %"new_cap", !dbg !181
  %".16" = mul i64 %".15", 16, !dbg !181
  %".17" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !182
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".17", i32 0, i32 0 , !dbg !182
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !182
  %".20" = bitcast %"struct.ritz_module_1.LineBounds"* %".19" to i8* , !dbg !182
  %".21" = call i8* @"realloc"(i8* %".20", i64 %".16"), !dbg !182
  %".22" = icmp eq i8* %".21", null , !dbg !183
  br i1 %".22", label %"if.then.1", label %"if.end.1", !dbg !183
if.then.1:
  %".24" = sub i64 0, 1, !dbg !184
  %".25" = trunc i64 %".24" to i32 , !dbg !184
  ret i32 %".25", !dbg !184
if.end.1:
  %".27" = bitcast i8* %".21" to %"struct.ritz_module_1.LineBounds"* , !dbg !185
  %".28" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !185
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".28", i32 0, i32 0 , !dbg !185
  store %"struct.ritz_module_1.LineBounds"* %".27", %"struct.ritz_module_1.LineBounds"** %".29", !dbg !185
  %".31" = load i64, i64* %"new_cap", !dbg !186
  %".32" = load %"struct.ritz_module_1.Vec$LineBounds"*, %"struct.ritz_module_1.Vec$LineBounds"** %"v.arg", !dbg !186
  %".33" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %".32", i32 0, i32 2 , !dbg !186
  store i64 %".31", i64* %".33", !dbg !186
  %".35" = trunc i64 0 to i32 , !dbg !187
  ret i32 %".35", !dbg !187
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/spire/lib", filename: "utils.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 28, name: "strview_eq", scopeLine: 28, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 16, name: "string_as_strview", scopeLine: 16, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!33 = !DICompositeType(align: 64, file: !0, name: "StrView", size: 128, tag: DW_TAG_structure_type)
!34 = !DIDerivedType(baseType: !33, size: 64, tag: DW_TAG_pointer_type)
!35 = !DILocalVariable(file: !0, line: 28, name: "a", scope: !17, type: !34)
!36 = !DILocation(column: 1, line: 28, scope: !17)
!37 = !DILocalVariable(file: !0, line: 28, name: "b", scope: !17, type: !34)
!38 = !DILocation(column: 5, line: 29, scope: !17)
!39 = !DILocation(column: 9, line: 30, scope: !17)
!40 = !DILocation(column: 5, line: 31, scope: !17)
!41 = !DILocalVariable(file: !0, line: 31, name: "i", scope: !17, type: !11)
!42 = !DILocation(column: 1, line: 31, scope: !17)
!43 = !DILocation(column: 5, line: 32, scope: !17)
!44 = !DILocation(column: 9, line: 33, scope: !17)
!45 = !DILocation(column: 13, line: 34, scope: !17)
!46 = !DILocation(column: 9, line: 35, scope: !17)
!47 = !DILocation(column: 5, line: 36, scope: !17)
!48 = !DICompositeType(align: 64, file: !0, name: "String", size: 192, tag: DW_TAG_structure_type)
!49 = !DIDerivedType(baseType: !48, size: 64, tag: DW_TAG_pointer_type)
!50 = !DILocalVariable(file: !0, line: 16, name: "s", scope: !18, type: !49)
!51 = !DILocation(column: 1, line: 16, scope: !18)
!52 = !DILocation(column: 5, line: 17, scope: !18)
!53 = !DILocalVariable(file: !0, line: 17, name: "sv", scope: !18, type: !33)
!54 = !DILocation(column: 1, line: 17, scope: !18)
!55 = !DILocation(column: 5, line: 18, scope: !18)
!56 = !DILocation(column: 5, line: 19, scope: !18)
!57 = !DILocation(column: 5, line: 20, scope: !18)
!58 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!59 = !DIDerivedType(baseType: !58, size: 64, tag: DW_TAG_reference_type)
!60 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !19, type: !59)
!61 = !DILocation(column: 1, line: 225, scope: !19)
!62 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !19, type: !11)
!63 = !DILocation(column: 5, line: 226, scope: !19)
!64 = !DILocation(column: 5, line: 117, scope: !20)
!65 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !20, type: !58)
!66 = !DILocation(column: 1, line: 117, scope: !20)
!67 = !DILocation(column: 5, line: 118, scope: !20)
!68 = !DILocation(column: 5, line: 119, scope: !20)
!69 = !DILocation(column: 5, line: 120, scope: !20)
!70 = !DILocation(column: 5, line: 121, scope: !20)
!71 = !DIDerivedType(baseType: !59, size: 64, tag: DW_TAG_reference_type)
!72 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !21, type: !71)
!73 = !DILocation(column: 1, line: 148, scope: !21)
!74 = !DILocation(column: 5, line: 149, scope: !21)
!75 = !DILocation(column: 5, line: 151, scope: !21)
!76 = !DILocation(column: 5, line: 152, scope: !21)
!77 = !DILocation(column: 5, line: 153, scope: !21)
!78 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !22, type: !71)
!79 = !DILocation(column: 1, line: 244, scope: !22)
!80 = !DILocation(column: 5, line: 245, scope: !22)
!81 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !23, type: !71)
!82 = !DILocation(column: 1, line: 219, scope: !23)
!83 = !DILocation(column: 5, line: 220, scope: !23)
!84 = !DILocation(column: 5, line: 221, scope: !23)
!85 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!86 = !DIDerivedType(baseType: !85, size: 64, tag: DW_TAG_reference_type)
!87 = !DIDerivedType(baseType: !86, size: 64, tag: DW_TAG_reference_type)
!88 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !24, type: !87)
!89 = !DILocation(column: 1, line: 210, scope: !24)
!90 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!91 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !24, type: !90)
!92 = !DILocation(column: 5, line: 211, scope: !24)
!93 = !DILocation(column: 9, line: 212, scope: !24)
!94 = !DILocation(column: 5, line: 213, scope: !24)
!95 = !DILocation(column: 5, line: 214, scope: !24)
!96 = !DILocation(column: 5, line: 215, scope: !24)
!97 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !25, type: !71)
!98 = !DILocation(column: 1, line: 235, scope: !25)
!99 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !25, type: !11)
!100 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !25, type: !12)
!101 = !DILocation(column: 5, line: 236, scope: !25)
!102 = !DILocation(column: 5, line: 237, scope: !25)
!103 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !26, type: !71)
!104 = !DILocation(column: 1, line: 210, scope: !26)
!105 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !26, type: !12)
!106 = !DILocation(column: 5, line: 211, scope: !26)
!107 = !DILocation(column: 9, line: 212, scope: !26)
!108 = !DILocation(column: 5, line: 213, scope: !26)
!109 = !DILocation(column: 5, line: 214, scope: !26)
!110 = !DILocation(column: 5, line: 215, scope: !26)
!111 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !27, type: !11)
!112 = !DILocation(column: 1, line: 124, scope: !27)
!113 = !DILocation(column: 5, line: 125, scope: !27)
!114 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !27, type: !58)
!115 = !DILocation(column: 1, line: 125, scope: !27)
!116 = !DILocation(column: 5, line: 126, scope: !27)
!117 = !DILocation(column: 9, line: 127, scope: !27)
!118 = !DILocation(column: 9, line: 128, scope: !27)
!119 = !DILocation(column: 9, line: 129, scope: !27)
!120 = !DILocation(column: 9, line: 130, scope: !27)
!121 = !DILocation(column: 5, line: 132, scope: !27)
!122 = !DILocation(column: 5, line: 133, scope: !27)
!123 = !DILocation(column: 5, line: 134, scope: !27)
!124 = !DILocation(column: 9, line: 135, scope: !27)
!125 = !DILocation(column: 9, line: 136, scope: !27)
!126 = !DILocation(column: 9, line: 137, scope: !27)
!127 = !DILocation(column: 5, line: 139, scope: !27)
!128 = !DILocation(column: 5, line: 140, scope: !27)
!129 = !DILocation(column: 5, line: 141, scope: !27)
!130 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !28, type: !71)
!131 = !DILocation(column: 1, line: 288, scope: !28)
!132 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!133 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !28, type: !132)
!134 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !28, type: !11)
!135 = !DILocation(column: 5, line: 289, scope: !28)
!136 = !DILocation(column: 13, line: 291, scope: !28)
!137 = !DILocation(column: 5, line: 292, scope: !28)
!138 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !29, type: !71)
!139 = !DILocation(column: 1, line: 193, scope: !29)
!140 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !29, type: !11)
!141 = !DILocation(column: 5, line: 194, scope: !29)
!142 = !DILocation(column: 9, line: 195, scope: !29)
!143 = !DILocation(column: 5, line: 197, scope: !29)
!144 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !29, type: !11)
!145 = !DILocation(column: 1, line: 197, scope: !29)
!146 = !DILocation(column: 5, line: 198, scope: !29)
!147 = !DILocation(column: 9, line: 199, scope: !29)
!148 = !DILocation(column: 5, line: 200, scope: !29)
!149 = !DILocation(column: 9, line: 201, scope: !29)
!150 = !DILocation(column: 5, line: 203, scope: !29)
!151 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !30, type: !87)
!152 = !DILocation(column: 1, line: 193, scope: !30)
!153 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !30, type: !11)
!154 = !DILocation(column: 5, line: 194, scope: !30)
!155 = !DILocation(column: 9, line: 195, scope: !30)
!156 = !DILocation(column: 5, line: 197, scope: !30)
!157 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !30, type: !11)
!158 = !DILocation(column: 1, line: 197, scope: !30)
!159 = !DILocation(column: 5, line: 198, scope: !30)
!160 = !DILocation(column: 9, line: 199, scope: !30)
!161 = !DILocation(column: 5, line: 200, scope: !30)
!162 = !DILocation(column: 9, line: 201, scope: !30)
!163 = !DILocation(column: 5, line: 203, scope: !30)
!164 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !31, type: !71)
!165 = !DILocation(column: 1, line: 179, scope: !31)
!166 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !31, type: !11)
!167 = !DILocation(column: 5, line: 180, scope: !31)
!168 = !DILocation(column: 9, line: 181, scope: !31)
!169 = !DILocation(column: 5, line: 183, scope: !31)
!170 = !DILocation(column: 5, line: 184, scope: !31)
!171 = !DILocation(column: 5, line: 185, scope: !31)
!172 = !DILocation(column: 9, line: 186, scope: !31)
!173 = !DILocation(column: 5, line: 188, scope: !31)
!174 = !DILocation(column: 5, line: 189, scope: !31)
!175 = !DILocation(column: 5, line: 190, scope: !31)
!176 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !32, type: !87)
!177 = !DILocation(column: 1, line: 179, scope: !32)
!178 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !32, type: !11)
!179 = !DILocation(column: 5, line: 180, scope: !32)
!180 = !DILocation(column: 9, line: 181, scope: !32)
!181 = !DILocation(column: 5, line: 183, scope: !32)
!182 = !DILocation(column: 5, line: 184, scope: !32)
!183 = !DILocation(column: 5, line: 185, scope: !32)
!184 = !DILocation(column: 9, line: 186, scope: !32)
!185 = !DILocation(column: 5, line: 188, scope: !32)
!186 = !DILocation(column: 5, line: 189, scope: !32)
!187 = !DILocation(column: 5, line: 190, scope: !32)