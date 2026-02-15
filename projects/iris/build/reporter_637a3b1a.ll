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
@"g_color_initialized" = internal global i32 0
@"g_use_color" = internal global i32 0
@"g_color_forced" = internal global i32 0
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

declare %"struct.ritz_module_1.String" @"string_new"()

declare %"struct.ritz_module_1.String" @"string_with_cap"(i64 %".1")

declare %"struct.ritz_module_1.String" @"string_from"(%"struct.ritz_module_1.StrView" %".1")

declare %"struct.ritz_module_1.String" @"string_from_cstr"(i8* %".1")

declare %"struct.ritz_module_1.String" @"string_from_bytes"(i8* %".1", i64 %".2")

declare %"struct.ritz_module_1.String" @"string_from_strview"(%"struct.ritz_module_1.StrView"* %".1")

declare i32 @"string_drop"(%"struct.ritz_module_1.String"* %".1")

declare i64 @"string_len"(%"struct.ritz_module_1.String"* %".1")

declare i64 @"string_cap"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"string_is_empty"(%"struct.ritz_module_1.String"* %".1")

declare i8* @"string_as_ptr"(%"struct.ritz_module_1.String"* %".1")

declare i8 @"string_get"(%"struct.ritz_module_1.String"* %".1", i64 %".2")

declare i32 @"string_push"(%"struct.ritz_module_1.String"* %".1", i8 %".2")

declare i32 @"string_push_str"(%"struct.ritz_module_1.String"* %".1", i8* %".2")

declare i32 @"string_push_string"(%"struct.ritz_module_1.String"* %".1", %"struct.ritz_module_1.String"* %".2")

declare i32 @"string_push_bytes"(%"struct.ritz_module_1.String"* %".1", i8* %".2", i64 %".3")

declare i32 @"string_clear"(%"struct.ritz_module_1.String"* %".1")

declare i8 @"string_pop"(%"struct.ritz_module_1.String"* %".1")

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

declare i32 @"string_set_char"(%"struct.ritz_module_1.String"* %".1", i64 %".2", i8 %".3")

declare i32 @"string_starts_with"(%"struct.ritz_module_1.String"* %".1", i8* %".2")

declare i32 @"string_ends_with"(%"struct.ritz_module_1.String"* %".1", i8* %".2")

declare i32 @"string_contains"(%"struct.ritz_module_1.String"* %".1", i8* %".2")

declare %"struct.ritz_module_1.String" @"string_from_i64"(i64 %".1")

declare i32 @"string_push_i64"(%"struct.ritz_module_1.String"* %".1", i64 %".2")

declare %"struct.ritz_module_1.String" @"string_from_hex"(i64 %".1")

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

declare i32 @"prints"(%"struct.ritz_module_1.StrView" %".1")

declare i32 @"eprints"(%"struct.ritz_module_1.StrView" %".1")

declare i32 @"prints_cstr"(i8* %".1")

declare i32 @"eprints_cstr"(i8* %".1")

declare i32 @"print_char"(i8 %".1")

declare i32 @"eprint_char"(i8 %".1")

declare i32 @"print_int"(i64 %".1")

declare i32 @"eprint_int"(i64 %".1")

declare i32 @"print_hex"(i64 %".1")

declare i32 @"print_size_human"(i64 %".1")

declare i32 @"println"(%"struct.ritz_module_1.StrView" %".1")

declare i32 @"eprintln"(%"struct.ritz_module_1.StrView" %".1")

declare i32 @"newline"()

declare i32 @"print_string"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"eprint_string"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"println_string"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"eprintln_string"(%"struct.ritz_module_1.String"* %".1")

declare i32 @"print_i64"(i64 %".1")

declare i32 @"println_i64"(i64 %".1")

declare i32 @"eprint_i64"(i64 %".1")

declare i32 @"eprintln_i64"(i64 %".1")

declare i32 @"print_hex64"(i64 %".1")

declare i32 @"println_hex64"(i64 %".1")

define i32 @"isatty"(i32 %"fd.arg") !dbg !17
{
entry:
  %"fd" = alloca i32
  %"winsize.addr" = alloca [4 x i32], !dbg !59
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !57, metadata !7), !dbg !58
  call void @"llvm.dbg.declare"(metadata [4 x i32]* %"winsize.addr", metadata !63, metadata !7), !dbg !64
  %".6" = load i32, i32* %"fd", !dbg !65
  %".7" = sext i32 %".6" to i64 , !dbg !65
  %".8" = ptrtoint [4 x i32]* %"winsize.addr" to i64 , !dbg !65
  %".9" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 16, i64 %".7", i64 21523, i64 %".8"), !dbg !65
  %".10" = icmp sge i64 %".9", 0 , !dbg !66
  %".11" = zext i1 %".10" to i32 , !dbg !66
  ret i32 %".11", !dbg !66
}

define i32 @"set_color_mode"(i32 %"mode.arg") !dbg !18
{
entry:
  %"mode" = alloca i32
  store i32 %"mode.arg", i32* %"mode"
  call void @"llvm.dbg.declare"(metadata i32* %"mode", metadata !67, metadata !7), !dbg !68
  %".5" = load i32, i32* %"mode", !dbg !69
  store i32 %".5", i32* @"g_color_forced", !dbg !69
  %".7" = trunc i64 0 to i32 , !dbg !70
  store i32 %".7", i32* @"g_color_initialized", !dbg !70
  ret i32 0, !dbg !70
}

define i32 @"init_color"() !dbg !19
{
entry:
  %".2" = load i32, i32* @"g_color_initialized", !dbg !71
  %".3" = sext i32 %".2" to i64 , !dbg !71
  %".4" = icmp ne i64 %".3", 0 , !dbg !71
  br i1 %".4", label %"if.then", label %"if.end", !dbg !71
if.then:
  ret i32 0, !dbg !72
if.end:
  %".7" = trunc i64 1 to i32 , !dbg !73
  store i32 %".7", i32* @"g_color_initialized", !dbg !73
  %".9" = load i32, i32* @"g_color_forced", !dbg !74
  %".10" = sext i32 %".9" to i64 , !dbg !74
  %".11" = icmp sgt i64 %".10", 0 , !dbg !74
  br i1 %".11", label %"if.then.1", label %"if.else", !dbg !74
if.then.1:
  %".13" = trunc i64 1 to i32 , !dbg !75
  store i32 %".13", i32* @"g_use_color", !dbg !75
  br label %"if.end.1", !dbg !77
if.else:
  %".15" = load i32, i32* @"g_color_forced", !dbg !75
  %".16" = sext i32 %".15" to i64 , !dbg !75
  %".17" = icmp slt i64 %".16", 0 , !dbg !75
  br i1 %".17", label %"if.then.2", label %"if.else.1", !dbg !75
if.end.1:
  ret i32 0, !dbg !77
if.then.2:
  %".19" = trunc i64 0 to i32 , !dbg !76
  store i32 %".19", i32* @"g_use_color", !dbg !76
  br label %"if.end.2", !dbg !77
if.else.1:
  %".21" = call i32 @"isatty"(i32 1), !dbg !77
  store i32 %".21", i32* @"g_use_color", !dbg !77
  br label %"if.end.2", !dbg !77
if.end.2:
  br label %"if.end.1", !dbg !77
}

define i32 @"use_color"() !dbg !20
{
entry:
  %".2" = call i32 @"init_color"(), !dbg !78
  %".3" = load i32, i32* @"g_use_color", !dbg !79
  ret i32 %".3", !dbg !79
}

define i32 @"print_esc"() !dbg !21
{
entry:
  %"buf.addr" = alloca [2 x i8], !dbg !80
  call void @"llvm.dbg.declare"(metadata [2 x i8]* %"buf.addr", metadata !84, metadata !7), !dbg !85
  %".3" = getelementptr [2 x i8], [2 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !86
  %".4" = trunc i64 27 to i8 , !dbg !86
  store i8 %".4", i8* %".3", !dbg !86
  %".6" = getelementptr [2 x i8], [2 x i8]* %"buf.addr", i32 0, i64 1 , !dbg !87
  %".7" = trunc i64 0 to i8 , !dbg !87
  store i8 %".7", i8* %".6", !dbg !87
  %".9" = getelementptr [2 x i8], [2 x i8]* %"buf.addr", i32 0, i64 0 , !dbg !88
  %".10" = call i32 @"prints_cstr"(i8* %".9"), !dbg !88
  ret i32 %".10", !dbg !88
}

define i32 @"color_reset"() !dbg !22
{
entry:
  %".2" = call i32 @"use_color"(), !dbg !89
  %".3" = sext i32 %".2" to i64 , !dbg !89
  %".4" = icmp eq i64 %".3", 0 , !dbg !89
  br i1 %".4", label %"if.then", label %"if.end", !dbg !89
if.then:
  ret i32 0, !dbg !90
if.end:
  %".7" = call i32 @"print_esc"(), !dbg !91
  %".8" = getelementptr [4 x i8], [4 x i8]* @".str.0", i64 0, i64 0 , !dbg !92
  %".9" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".8", 0 , !dbg !92
  %".10" = insertvalue %"struct.ritz_module_1.StrView" %".9", i64 3, 1 , !dbg !92
  %".11" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".10"), !dbg !92
  ret i32 %".11", !dbg !92
}

define i32 @"color_green"() !dbg !23
{
entry:
  %".2" = call i32 @"use_color"(), !dbg !93
  %".3" = sext i32 %".2" to i64 , !dbg !93
  %".4" = icmp eq i64 %".3", 0 , !dbg !93
  br i1 %".4", label %"if.then", label %"if.end", !dbg !93
if.then:
  ret i32 0, !dbg !94
if.end:
  %".7" = call i32 @"print_esc"(), !dbg !95
  %".8" = getelementptr [5 x i8], [5 x i8]* @".str.1", i64 0, i64 0 , !dbg !96
  %".9" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".8", 0 , !dbg !96
  %".10" = insertvalue %"struct.ritz_module_1.StrView" %".9", i64 4, 1 , !dbg !96
  %".11" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".10"), !dbg !96
  ret i32 %".11", !dbg !96
}

define i32 @"color_red"() !dbg !24
{
entry:
  %".2" = call i32 @"use_color"(), !dbg !97
  %".3" = sext i32 %".2" to i64 , !dbg !97
  %".4" = icmp eq i64 %".3", 0 , !dbg !97
  br i1 %".4", label %"if.then", label %"if.end", !dbg !97
if.then:
  ret i32 0, !dbg !98
if.end:
  %".7" = call i32 @"print_esc"(), !dbg !99
  %".8" = getelementptr [5 x i8], [5 x i8]* @".str.2", i64 0, i64 0 , !dbg !100
  %".9" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".8", 0 , !dbg !100
  %".10" = insertvalue %"struct.ritz_module_1.StrView" %".9", i64 4, 1 , !dbg !100
  %".11" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".10"), !dbg !100
  ret i32 %".11", !dbg !100
}

define i32 @"color_yellow"() !dbg !25
{
entry:
  %".2" = call i32 @"use_color"(), !dbg !101
  %".3" = sext i32 %".2" to i64 , !dbg !101
  %".4" = icmp eq i64 %".3", 0 , !dbg !101
  br i1 %".4", label %"if.then", label %"if.end", !dbg !101
if.then:
  ret i32 0, !dbg !102
if.end:
  %".7" = call i32 @"print_esc"(), !dbg !103
  %".8" = getelementptr [5 x i8], [5 x i8]* @".str.3", i64 0, i64 0 , !dbg !104
  %".9" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".8", 0 , !dbg !104
  %".10" = insertvalue %"struct.ritz_module_1.StrView" %".9", i64 4, 1 , !dbg !104
  %".11" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".10"), !dbg !104
  ret i32 %".11", !dbg !104
}

define i32 @"color_bold"() !dbg !26
{
entry:
  %".2" = call i32 @"use_color"(), !dbg !105
  %".3" = sext i32 %".2" to i64 , !dbg !105
  %".4" = icmp eq i64 %".3", 0 , !dbg !105
  br i1 %".4", label %"if.then", label %"if.end", !dbg !105
if.then:
  ret i32 0, !dbg !106
if.end:
  %".7" = call i32 @"print_esc"(), !dbg !107
  %".8" = getelementptr [4 x i8], [4 x i8]* @".str.4", i64 0, i64 0 , !dbg !108
  %".9" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".8", 0 , !dbg !108
  %".10" = insertvalue %"struct.ritz_module_1.StrView" %".9", i64 3, 1 , !dbg !108
  %".11" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".10"), !dbg !108
  ret i32 %".11", !dbg !108
}

define i32 @"color_dim"() !dbg !27
{
entry:
  %".2" = call i32 @"use_color"(), !dbg !109
  %".3" = sext i32 %".2" to i64 , !dbg !109
  %".4" = icmp eq i64 %".3", 0 , !dbg !109
  br i1 %".4", label %"if.then", label %"if.end", !dbg !109
if.then:
  ret i32 0, !dbg !110
if.end:
  %".7" = call i32 @"print_esc"(), !dbg !111
  %".8" = getelementptr [4 x i8], [4 x i8]* @".str.5", i64 0, i64 0 , !dbg !112
  %".9" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".8", 0 , !dbg !112
  %".10" = insertvalue %"struct.ritz_module_1.StrView" %".9", i64 3, 1 , !dbg !112
  %".11" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".10"), !dbg !112
  ret i32 %".11", !dbg !112
}

define i32 @"print_banner"() !dbg !28
{
entry:
  %".2" = call i32 @"color_bold"(), !dbg !113
  %".3" = getelementptr [72 x i8], [72 x i8]* @".str.6", i64 0, i64 0 , !dbg !114
  %".4" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".3", 0 , !dbg !114
  %".5" = insertvalue %"struct.ritz_module_1.StrView" %".4", i64 71, 1 , !dbg !114
  %".6" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".5"), !dbg !114
  %".7" = getelementptr [45 x i8], [45 x i8]* @".str.7", i64 0, i64 0 , !dbg !115
  %".8" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".7", 0 , !dbg !115
  %".9" = insertvalue %"struct.ritz_module_1.StrView" %".8", i64 44, 1 , !dbg !115
  %".10" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".9"), !dbg !115
  %".11" = getelementptr [71 x i8], [71 x i8]* @".str.8", i64 0, i64 0 , !dbg !116
  %".12" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".11", 0 , !dbg !116
  %".13" = insertvalue %"struct.ritz_module_1.StrView" %".12", i64 70, 1 , !dbg !116
  %".14" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".13"), !dbg !116
  %".15" = call i32 @"color_reset"(), !dbg !117
  %".16" = getelementptr [3 x i8], [3 x i8]* @".str.9", i64 0, i64 0 , !dbg !118
  %".17" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".16", 0 , !dbg !118
  %".18" = insertvalue %"struct.ritz_module_1.StrView" %".17", i64 2, 1 , !dbg !118
  %".19" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".18"), !dbg !118
  ret i32 %".19", !dbg !118
}

define i32 @"print_suite_header"(%"struct.ritz_module_1.StrView" %"name.arg") !dbg !29
{
entry:
  %"name" = alloca %"struct.ritz_module_1.StrView"
  store %"struct.ritz_module_1.StrView" %"name.arg", %"struct.ritz_module_1.StrView"* %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name", metadata !120, metadata !7), !dbg !121
  %".5" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name", !dbg !122
  %".6" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".5"), !dbg !122
  %".7" = getelementptr [2 x i8], [2 x i8]* @".str.10", i64 0, i64 0 , !dbg !123
  %".8" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".7", 0 , !dbg !123
  %".9" = insertvalue %"struct.ritz_module_1.StrView" %".8", i64 1, 1 , !dbg !123
  %".10" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".9"), !dbg !123
  ret i32 %".10", !dbg !123
}

define i32 @"print_suite_divider"() !dbg !30
{
entry:
  %".2" = getelementptr [74 x i8], [74 x i8]* @".str.11", i64 0, i64 0 , !dbg !124
  %".3" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".2", 0 , !dbg !124
  %".4" = insertvalue %"struct.ritz_module_1.StrView" %".3", i64 73, 1 , !dbg !124
  %".5" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".4"), !dbg !124
  ret i32 %".5", !dbg !124
}

define i32 @"print_grand_divider"() !dbg !31
{
entry:
  %".2" = getelementptr [72 x i8], [72 x i8]* @".str.12", i64 0, i64 0 , !dbg !125
  %".3" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".2", 0 , !dbg !125
  %".4" = insertvalue %"struct.ritz_module_1.StrView" %".3", i64 71, 1 , !dbg !125
  %".5" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".4"), !dbg !125
  ret i32 %".5", !dbg !125
}

define i32 @"print_dots"(i32 %"count.arg") !dbg !32
{
entry:
  %"count" = alloca i32
  %"i.addr" = alloca i32, !dbg !128
  store i32 %"count.arg", i32* %"count"
  call void @"llvm.dbg.declare"(metadata i32* %"count", metadata !126, metadata !7), !dbg !127
  %".5" = trunc i64 0 to i32 , !dbg !128
  store i32 %".5", i32* %"i.addr", !dbg !128
  call void @"llvm.dbg.declare"(metadata i32* %"i.addr", metadata !129, metadata !7), !dbg !130
  br label %"while.cond", !dbg !131
while.cond:
  %".9" = load i32, i32* %"i.addr", !dbg !131
  %".10" = load i32, i32* %"count", !dbg !131
  %".11" = icmp slt i32 %".9", %".10" , !dbg !131
  br i1 %".11", label %"while.body", label %"while.end", !dbg !131
while.body:
  %".13" = getelementptr [2 x i8], [2 x i8]* @".str.13", i64 0, i64 0 , !dbg !132
  %".14" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".13", 0 , !dbg !132
  %".15" = insertvalue %"struct.ritz_module_1.StrView" %".14", i64 1, 1 , !dbg !132
  %".16" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".15"), !dbg !132
  %".17" = load i32, i32* %"i.addr", !dbg !133
  %".18" = sext i32 %".17" to i64 , !dbg !133
  %".19" = add i64 %".18", 1, !dbg !133
  %".20" = trunc i64 %".19" to i32 , !dbg !133
  store i32 %".20", i32* %"i.addr", !dbg !133
  br label %"while.cond", !dbg !133
while.end:
  ret i32 0, !dbg !133
}

define i32 @"print_test_line"(%"struct.ritz_module_1.StrView" %"name.arg", %"struct.ritz_module_1.StrView" %"status.arg", i64 %"duration_ms.arg") !dbg !33
{
entry:
  %"name" = alloca %"struct.ritz_module_1.StrView"
  %"time_width.addr" = alloca i32, !dbg !143
  %"dots.addr" = alloca i32, !dbg !155
  store %"struct.ritz_module_1.StrView" %"name.arg", %"struct.ritz_module_1.StrView"* %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name", metadata !134, metadata !7), !dbg !135
  %"status" = alloca %"struct.ritz_module_1.StrView"
  store %"struct.ritz_module_1.StrView" %"status.arg", %"struct.ritz_module_1.StrView"* %"status"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"status", metadata !136, metadata !7), !dbg !135
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !137, metadata !7), !dbg !135
  %".11" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name", i32 0, i32 1 , !dbg !138
  %".12" = load i64, i64* %".11", !dbg !138
  %".13" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"status", i32 0, i32 1 , !dbg !139
  %".14" = load i64, i64* %".13", !dbg !139
  %".15" = getelementptr [3 x i8], [3 x i8]* @".str.14", i64 0, i64 0 , !dbg !140
  %".16" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".15", 0 , !dbg !140
  %".17" = insertvalue %"struct.ritz_module_1.StrView" %".16", i64 2, 1 , !dbg !140
  %".18" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".17"), !dbg !140
  %".19" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name", !dbg !141
  %".20" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".19"), !dbg !141
  %".21" = getelementptr [2 x i8], [2 x i8]* @".str.15", i64 0, i64 0 , !dbg !142
  %".22" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".21", 0 , !dbg !142
  %".23" = insertvalue %"struct.ritz_module_1.StrView" %".22", i64 1, 1 , !dbg !142
  %".24" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".23"), !dbg !142
  %".25" = trunc i64 7 to i32 , !dbg !143
  store i32 %".25", i32* %"time_width.addr", !dbg !143
  call void @"llvm.dbg.declare"(metadata i32* %"time_width.addr", metadata !144, metadata !7), !dbg !145
  %".28" = load i64, i64* %"duration_ms", !dbg !146
  %".29" = icmp sge i64 %".28", 10 , !dbg !146
  br i1 %".29", label %"if.then", label %"if.end", !dbg !146
if.then:
  %".31" = trunc i64 8 to i32 , !dbg !147
  store i32 %".31", i32* %"time_width.addr", !dbg !147
  br label %"if.end", !dbg !147
if.end:
  %".34" = load i64, i64* %"duration_ms", !dbg !148
  %".35" = icmp sge i64 %".34", 100 , !dbg !148
  br i1 %".35", label %"if.then.1", label %"if.end.1", !dbg !148
if.then.1:
  %".37" = trunc i64 9 to i32 , !dbg !149
  store i32 %".37", i32* %"time_width.addr", !dbg !149
  br label %"if.end.1", !dbg !149
if.end.1:
  %".40" = load i64, i64* %"duration_ms", !dbg !150
  %".41" = icmp sge i64 %".40", 1000 , !dbg !150
  br i1 %".41", label %"if.then.2", label %"if.end.2", !dbg !150
if.then.2:
  %".43" = trunc i64 10 to i32 , !dbg !151
  store i32 %".43", i32* %"time_width.addr", !dbg !151
  br label %"if.end.2", !dbg !151
if.end.2:
  %".46" = load i64, i64* %"duration_ms", !dbg !152
  %".47" = icmp sge i64 %".46", 10000 , !dbg !152
  br i1 %".47", label %"if.then.3", label %"if.end.3", !dbg !152
if.then.3:
  %".49" = trunc i64 11 to i32 , !dbg !153
  store i32 %".49", i32* %"time_width.addr", !dbg !153
  br label %"if.end.3", !dbg !153
if.end.3:
  %".52" = trunc i64 %".14" to i32 , !dbg !154
  %".53" = load i32, i32* %"time_width.addr", !dbg !154
  %".54" = add i32 %".52", %".53", !dbg !154
  %".55" = sext i32 70 to i64 , !dbg !155
  %".56" = sub i64 %".55", 2, !dbg !155
  %".57" = trunc i64 %".12" to i32 , !dbg !155
  %".58" = sext i32 %".57" to i64 , !dbg !155
  %".59" = sub i64 %".56", %".58", !dbg !155
  %".60" = sub i64 %".59", 1, !dbg !155
  %".61" = sext i32 %".54" to i64 , !dbg !155
  %".62" = sub i64 %".60", %".61", !dbg !155
  %".63" = trunc i64 %".62" to i32 , !dbg !155
  store i32 %".63", i32* %"dots.addr", !dbg !155
  call void @"llvm.dbg.declare"(metadata i32* %"dots.addr", metadata !156, metadata !7), !dbg !157
  %".66" = load i32, i32* %"dots.addr", !dbg !158
  %".67" = icmp slt i32 %".66", 3 , !dbg !158
  br i1 %".67", label %"if.then.4", label %"if.end.4", !dbg !158
if.then.4:
  store i32 3, i32* %"dots.addr", !dbg !159
  br label %"if.end.4", !dbg !159
if.end.4:
  %".71" = load i32, i32* %"dots.addr", !dbg !160
  %".72" = call i32 @"print_dots"(i32 %".71"), !dbg !160
  %".73" = getelementptr [2 x i8], [2 x i8]* @".str.16", i64 0, i64 0 , !dbg !161
  %".74" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".73", 0 , !dbg !161
  %".75" = insertvalue %"struct.ritz_module_1.StrView" %".74", i64 1, 1 , !dbg !161
  %".76" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".75"), !dbg !161
  %".77" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"status", !dbg !162
  %".78" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".77"), !dbg !162
  %".79" = getelementptr [3 x i8], [3 x i8]* @".str.17", i64 0, i64 0 , !dbg !163
  %".80" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".79", 0 , !dbg !163
  %".81" = insertvalue %"struct.ritz_module_1.StrView" %".80", i64 2, 1 , !dbg !163
  %".82" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".81"), !dbg !163
  %".83" = load i64, i64* %"duration_ms", !dbg !164
  %".84" = call i32 @"print_int"(i64 %".83"), !dbg !164
  %".85" = getelementptr [5 x i8], [5 x i8]* @".str.18", i64 0, i64 0 , !dbg !165
  %".86" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".85", 0 , !dbg !165
  %".87" = insertvalue %"struct.ritz_module_1.StrView" %".86", i64 4, 1 , !dbg !165
  %".88" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".87"), !dbg !165
  ret i32 %".88", !dbg !165
}

define i32 @"print_test_pass"(%"struct.ritz_module_1.StrView" %"name.arg", i64 %"duration_ms.arg") !dbg !34
{
entry:
  %"name" = alloca %"struct.ritz_module_1.StrView"
  %"time_width.addr" = alloca i32, !dbg !174
  %"dots.addr" = alloca i32, !dbg !186
  store %"struct.ritz_module_1.StrView" %"name.arg", %"struct.ritz_module_1.StrView"* %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name", metadata !166, metadata !7), !dbg !167
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !168, metadata !7), !dbg !167
  %".8" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name", i32 0, i32 1 , !dbg !169
  %".9" = load i64, i64* %".8", !dbg !169
  %".10" = getelementptr [3 x i8], [3 x i8]* @".str.19", i64 0, i64 0 , !dbg !170
  %".11" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".10", 0 , !dbg !170
  %".12" = insertvalue %"struct.ritz_module_1.StrView" %".11", i64 2, 1 , !dbg !170
  %".13" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".12"), !dbg !170
  %".14" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name", !dbg !171
  %".15" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".14"), !dbg !171
  %".16" = getelementptr [2 x i8], [2 x i8]* @".str.20", i64 0, i64 0 , !dbg !172
  %".17" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".16", 0 , !dbg !172
  %".18" = insertvalue %"struct.ritz_module_1.StrView" %".17", i64 1, 1 , !dbg !172
  %".19" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".18"), !dbg !172
  %".20" = trunc i64 7 to i32 , !dbg !174
  store i32 %".20", i32* %"time_width.addr", !dbg !174
  call void @"llvm.dbg.declare"(metadata i32* %"time_width.addr", metadata !175, metadata !7), !dbg !176
  %".23" = load i64, i64* %"duration_ms", !dbg !177
  %".24" = icmp sge i64 %".23", 10 , !dbg !177
  br i1 %".24", label %"if.then", label %"if.end", !dbg !177
if.then:
  %".26" = trunc i64 8 to i32 , !dbg !178
  store i32 %".26", i32* %"time_width.addr", !dbg !178
  br label %"if.end", !dbg !178
if.end:
  %".29" = load i64, i64* %"duration_ms", !dbg !179
  %".30" = icmp sge i64 %".29", 100 , !dbg !179
  br i1 %".30", label %"if.then.1", label %"if.end.1", !dbg !179
if.then.1:
  %".32" = trunc i64 9 to i32 , !dbg !180
  store i32 %".32", i32* %"time_width.addr", !dbg !180
  br label %"if.end.1", !dbg !180
if.end.1:
  %".35" = load i64, i64* %"duration_ms", !dbg !181
  %".36" = icmp sge i64 %".35", 1000 , !dbg !181
  br i1 %".36", label %"if.then.2", label %"if.end.2", !dbg !181
if.then.2:
  %".38" = trunc i64 10 to i32 , !dbg !182
  store i32 %".38", i32* %"time_width.addr", !dbg !182
  br label %"if.end.2", !dbg !182
if.end.2:
  %".41" = load i64, i64* %"duration_ms", !dbg !183
  %".42" = icmp sge i64 %".41", 10000 , !dbg !183
  br i1 %".42", label %"if.then.3", label %"if.end.3", !dbg !183
if.then.3:
  %".44" = trunc i64 11 to i32 , !dbg !184
  store i32 %".44", i32* %"time_width.addr", !dbg !184
  br label %"if.end.3", !dbg !184
if.end.3:
  %".47" = trunc i64 2 to i32 , !dbg !185
  %".48" = load i32, i32* %"time_width.addr", !dbg !185
  %".49" = add i32 %".47", %".48", !dbg !185
  %".50" = sext i32 70 to i64 , !dbg !186
  %".51" = sub i64 %".50", 2, !dbg !186
  %".52" = trunc i64 %".9" to i32 , !dbg !186
  %".53" = sext i32 %".52" to i64 , !dbg !186
  %".54" = sub i64 %".51", %".53", !dbg !186
  %".55" = sub i64 %".54", 1, !dbg !186
  %".56" = sext i32 %".49" to i64 , !dbg !186
  %".57" = sub i64 %".55", %".56", !dbg !186
  %".58" = trunc i64 %".57" to i32 , !dbg !186
  store i32 %".58", i32* %"dots.addr", !dbg !186
  call void @"llvm.dbg.declare"(metadata i32* %"dots.addr", metadata !187, metadata !7), !dbg !188
  %".61" = load i32, i32* %"dots.addr", !dbg !189
  %".62" = icmp slt i32 %".61", 3 , !dbg !189
  br i1 %".62", label %"if.then.4", label %"if.end.4", !dbg !189
if.then.4:
  store i32 3, i32* %"dots.addr", !dbg !190
  br label %"if.end.4", !dbg !190
if.end.4:
  %".66" = call i32 @"color_dim"(), !dbg !191
  %".67" = load i32, i32* %"dots.addr", !dbg !192
  %".68" = call i32 @"print_dots"(i32 %".67"), !dbg !192
  %".69" = call i32 @"color_reset"(), !dbg !193
  %".70" = getelementptr [2 x i8], [2 x i8]* @".str.21", i64 0, i64 0 , !dbg !194
  %".71" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".70", 0 , !dbg !194
  %".72" = insertvalue %"struct.ritz_module_1.StrView" %".71", i64 1, 1 , !dbg !194
  %".73" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".72"), !dbg !194
  %".74" = call i32 @"color_green"(), !dbg !195
  %".75" = getelementptr [3 x i8], [3 x i8]* @".str.22", i64 0, i64 0 , !dbg !196
  %".76" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".75", 0 , !dbg !196
  %".77" = insertvalue %"struct.ritz_module_1.StrView" %".76", i64 2, 1 , !dbg !196
  %".78" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".77"), !dbg !196
  %".79" = call i32 @"color_reset"(), !dbg !197
  %".80" = getelementptr [3 x i8], [3 x i8]* @".str.23", i64 0, i64 0 , !dbg !198
  %".81" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".80", 0 , !dbg !198
  %".82" = insertvalue %"struct.ritz_module_1.StrView" %".81", i64 2, 1 , !dbg !198
  %".83" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".82"), !dbg !198
  %".84" = load i64, i64* %"duration_ms", !dbg !199
  %".85" = call i32 @"print_int"(i64 %".84"), !dbg !199
  %".86" = getelementptr [5 x i8], [5 x i8]* @".str.24", i64 0, i64 0 , !dbg !200
  %".87" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".86", 0 , !dbg !200
  %".88" = insertvalue %"struct.ritz_module_1.StrView" %".87", i64 4, 1 , !dbg !200
  %".89" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".88"), !dbg !200
  ret i32 %".89", !dbg !200
}

define i32 @"print_test_fail"(%"struct.ritz_module_1.StrView" %"name.arg", i64 %"duration_ms.arg", i32 %"error_code.arg") !dbg !35
{
entry:
  %"name" = alloca %"struct.ritz_module_1.StrView"
  %"dots.addr" = alloca i32, !dbg !209
  store %"struct.ritz_module_1.StrView" %"name.arg", %"struct.ritz_module_1.StrView"* %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name", metadata !201, metadata !7), !dbg !202
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !203, metadata !7), !dbg !202
  %"error_code" = alloca i32
  store i32 %"error_code.arg", i32* %"error_code"
  call void @"llvm.dbg.declare"(metadata i32* %"error_code", metadata !204, metadata !7), !dbg !202
  %".11" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name", i32 0, i32 1 , !dbg !205
  %".12" = load i64, i64* %".11", !dbg !205
  %".13" = getelementptr [3 x i8], [3 x i8]* @".str.25", i64 0, i64 0 , !dbg !206
  %".14" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".13", 0 , !dbg !206
  %".15" = insertvalue %"struct.ritz_module_1.StrView" %".14", i64 2, 1 , !dbg !206
  %".16" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".15"), !dbg !206
  %".17" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name", !dbg !207
  %".18" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".17"), !dbg !207
  %".19" = getelementptr [2 x i8], [2 x i8]* @".str.26", i64 0, i64 0 , !dbg !208
  %".20" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".19", 0 , !dbg !208
  %".21" = insertvalue %"struct.ritz_module_1.StrView" %".20", i64 1, 1 , !dbg !208
  %".22" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".21"), !dbg !208
  %".23" = sext i32 70 to i64 , !dbg !209
  %".24" = sub i64 %".23", 2, !dbg !209
  %".25" = trunc i64 %".12" to i32 , !dbg !209
  %".26" = sext i32 %".25" to i64 , !dbg !209
  %".27" = sub i64 %".24", %".26", !dbg !209
  %".28" = sub i64 %".27", 1, !dbg !209
  %".29" = sub i64 %".28", 20, !dbg !209
  %".30" = trunc i64 %".29" to i32 , !dbg !209
  store i32 %".30", i32* %"dots.addr", !dbg !209
  call void @"llvm.dbg.declare"(metadata i32* %"dots.addr", metadata !210, metadata !7), !dbg !211
  %".33" = load i32, i32* %"dots.addr", !dbg !212
  %".34" = icmp slt i32 %".33", 3 , !dbg !212
  br i1 %".34", label %"if.then", label %"if.end", !dbg !212
if.then:
  store i32 3, i32* %"dots.addr", !dbg !213
  br label %"if.end", !dbg !213
if.end:
  %".38" = call i32 @"color_dim"(), !dbg !214
  %".39" = load i32, i32* %"dots.addr", !dbg !215
  %".40" = call i32 @"print_dots"(i32 %".39"), !dbg !215
  %".41" = call i32 @"color_reset"(), !dbg !216
  %".42" = getelementptr [2 x i8], [2 x i8]* @".str.27", i64 0, i64 0 , !dbg !217
  %".43" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".42", 0 , !dbg !217
  %".44" = insertvalue %"struct.ritz_module_1.StrView" %".43", i64 1, 1 , !dbg !217
  %".45" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".44"), !dbg !217
  %".46" = call i32 @"color_red"(), !dbg !218
  %".47" = call i32 @"color_bold"(), !dbg !219
  %".48" = getelementptr [5 x i8], [5 x i8]* @".str.28", i64 0, i64 0 , !dbg !220
  %".49" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".48", 0 , !dbg !220
  %".50" = insertvalue %"struct.ritz_module_1.StrView" %".49", i64 4, 1 , !dbg !220
  %".51" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".50"), !dbg !220
  %".52" = call i32 @"color_reset"(), !dbg !221
  %".53" = getelementptr [8 x i8], [8 x i8]* @".str.29", i64 0, i64 0 , !dbg !222
  %".54" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".53", 0 , !dbg !222
  %".55" = insertvalue %"struct.ritz_module_1.StrView" %".54", i64 7, 1 , !dbg !222
  %".56" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".55"), !dbg !222
  %".57" = load i32, i32* %"error_code", !dbg !223
  %".58" = sext i32 %".57" to i64 , !dbg !223
  %".59" = call i32 @"print_int"(i64 %".58"), !dbg !223
  %".60" = getelementptr [4 x i8], [4 x i8]* @".str.30", i64 0, i64 0 , !dbg !224
  %".61" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".60", 0 , !dbg !224
  %".62" = insertvalue %"struct.ritz_module_1.StrView" %".61", i64 3, 1 , !dbg !224
  %".63" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".62"), !dbg !224
  %".64" = load i64, i64* %"duration_ms", !dbg !225
  %".65" = call i32 @"print_int"(i64 %".64"), !dbg !225
  %".66" = getelementptr [5 x i8], [5 x i8]* @".str.31", i64 0, i64 0 , !dbg !226
  %".67" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".66", 0 , !dbg !226
  %".68" = insertvalue %"struct.ritz_module_1.StrView" %".67", i64 4, 1 , !dbg !226
  %".69" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".68"), !dbg !226
  ret i32 %".69", !dbg !226
}

define i32 @"print_test_crash"(%"struct.ritz_module_1.StrView" %"name.arg", i64 %"duration_ms.arg", i32 %"signal.arg", %"struct.ritz_module_1.StrView" %"signal_name.arg") !dbg !36
{
entry:
  %"name" = alloca %"struct.ritz_module_1.StrView"
  %"dots.addr" = alloca i32, !dbg !237
  store %"struct.ritz_module_1.StrView" %"name.arg", %"struct.ritz_module_1.StrView"* %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name", metadata !227, metadata !7), !dbg !228
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !229, metadata !7), !dbg !228
  %"signal" = alloca i32
  store i32 %"signal.arg", i32* %"signal"
  call void @"llvm.dbg.declare"(metadata i32* %"signal", metadata !230, metadata !7), !dbg !228
  %"signal_name" = alloca %"struct.ritz_module_1.StrView"
  store %"struct.ritz_module_1.StrView" %"signal_name.arg", %"struct.ritz_module_1.StrView"* %"signal_name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"signal_name", metadata !231, metadata !7), !dbg !228
  %".14" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name", i32 0, i32 1 , !dbg !232
  %".15" = load i64, i64* %".14", !dbg !232
  %".16" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"signal_name", i32 0, i32 1 , !dbg !233
  %".17" = load i64, i64* %".16", !dbg !233
  %".18" = getelementptr [3 x i8], [3 x i8]* @".str.32", i64 0, i64 0 , !dbg !234
  %".19" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".18", 0 , !dbg !234
  %".20" = insertvalue %"struct.ritz_module_1.StrView" %".19", i64 2, 1 , !dbg !234
  %".21" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".20"), !dbg !234
  %".22" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name", !dbg !235
  %".23" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".22"), !dbg !235
  %".24" = getelementptr [2 x i8], [2 x i8]* @".str.33", i64 0, i64 0 , !dbg !236
  %".25" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".24", 0 , !dbg !236
  %".26" = insertvalue %"struct.ritz_module_1.StrView" %".25", i64 1, 1 , !dbg !236
  %".27" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".26"), !dbg !236
  %".28" = sext i32 70 to i64 , !dbg !237
  %".29" = sub i64 %".28", 2, !dbg !237
  %".30" = trunc i64 %".15" to i32 , !dbg !237
  %".31" = sext i32 %".30" to i64 , !dbg !237
  %".32" = sub i64 %".29", %".31", !dbg !237
  %".33" = sub i64 %".32", 1, !dbg !237
  %".34" = sub i64 %".33", 10, !dbg !237
  %".35" = trunc i64 %".17" to i32 , !dbg !237
  %".36" = sext i32 %".35" to i64 , !dbg !237
  %".37" = sub i64 %".34", %".36", !dbg !237
  %".38" = trunc i64 %".37" to i32 , !dbg !237
  store i32 %".38", i32* %"dots.addr", !dbg !237
  call void @"llvm.dbg.declare"(metadata i32* %"dots.addr", metadata !238, metadata !7), !dbg !239
  %".41" = load i32, i32* %"dots.addr", !dbg !240
  %".42" = icmp slt i32 %".41", 3 , !dbg !240
  br i1 %".42", label %"if.then", label %"if.end", !dbg !240
if.then:
  store i32 3, i32* %"dots.addr", !dbg !241
  br label %"if.end", !dbg !241
if.end:
  %".46" = call i32 @"color_dim"(), !dbg !242
  %".47" = load i32, i32* %"dots.addr", !dbg !243
  %".48" = call i32 @"print_dots"(i32 %".47"), !dbg !243
  %".49" = call i32 @"color_reset"(), !dbg !244
  %".50" = getelementptr [2 x i8], [2 x i8]* @".str.34", i64 0, i64 0 , !dbg !245
  %".51" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".50", 0 , !dbg !245
  %".52" = insertvalue %"struct.ritz_module_1.StrView" %".51", i64 1, 1 , !dbg !245
  %".53" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".52"), !dbg !245
  %".54" = call i32 @"color_red"(), !dbg !246
  %".55" = call i32 @"color_bold"(), !dbg !247
  %".56" = getelementptr [6 x i8], [6 x i8]* @".str.35", i64 0, i64 0 , !dbg !248
  %".57" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".56", 0 , !dbg !248
  %".58" = insertvalue %"struct.ritz_module_1.StrView" %".57", i64 5, 1 , !dbg !248
  %".59" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".58"), !dbg !248
  %".60" = call i32 @"color_reset"(), !dbg !249
  %".61" = getelementptr [3 x i8], [3 x i8]* @".str.36", i64 0, i64 0 , !dbg !250
  %".62" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".61", 0 , !dbg !250
  %".63" = insertvalue %"struct.ritz_module_1.StrView" %".62", i64 2, 1 , !dbg !250
  %".64" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".63"), !dbg !250
  %".65" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"signal_name", !dbg !251
  %".66" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".65"), !dbg !251
  %".67" = getelementptr [4 x i8], [4 x i8]* @".str.37", i64 0, i64 0 , !dbg !252
  %".68" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".67", 0 , !dbg !252
  %".69" = insertvalue %"struct.ritz_module_1.StrView" %".68", i64 3, 1 , !dbg !252
  %".70" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".69"), !dbg !252
  %".71" = load i64, i64* %"duration_ms", !dbg !253
  %".72" = call i32 @"print_int"(i64 %".71"), !dbg !253
  %".73" = getelementptr [5 x i8], [5 x i8]* @".str.38", i64 0, i64 0 , !dbg !254
  %".74" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".73", 0 , !dbg !254
  %".75" = insertvalue %"struct.ritz_module_1.StrView" %".74", i64 4, 1 , !dbg !254
  %".76" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".75"), !dbg !254
  ret i32 %".76", !dbg !254
}

define i32 @"print_test_timeout"(%"struct.ritz_module_1.StrView" %"name.arg", i64 %"timeout_ms.arg") !dbg !37
{
entry:
  %"name" = alloca %"struct.ritz_module_1.StrView"
  %"dots.addr" = alloca i32, !dbg !262
  store %"struct.ritz_module_1.StrView" %"name.arg", %"struct.ritz_module_1.StrView"* %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name", metadata !255, metadata !7), !dbg !256
  %"timeout_ms" = alloca i64
  store i64 %"timeout_ms.arg", i64* %"timeout_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"timeout_ms", metadata !257, metadata !7), !dbg !256
  %".8" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name", i32 0, i32 1 , !dbg !258
  %".9" = load i64, i64* %".8", !dbg !258
  %".10" = getelementptr [3 x i8], [3 x i8]* @".str.39", i64 0, i64 0 , !dbg !259
  %".11" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".10", 0 , !dbg !259
  %".12" = insertvalue %"struct.ritz_module_1.StrView" %".11", i64 2, 1 , !dbg !259
  %".13" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".12"), !dbg !259
  %".14" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name", !dbg !260
  %".15" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".14"), !dbg !260
  %".16" = getelementptr [2 x i8], [2 x i8]* @".str.40", i64 0, i64 0 , !dbg !261
  %".17" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".16", 0 , !dbg !261
  %".18" = insertvalue %"struct.ritz_module_1.StrView" %".17", i64 1, 1 , !dbg !261
  %".19" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".18"), !dbg !261
  %".20" = sext i32 70 to i64 , !dbg !262
  %".21" = sub i64 %".20", 2, !dbg !262
  %".22" = trunc i64 %".9" to i32 , !dbg !262
  %".23" = sext i32 %".22" to i64 , !dbg !262
  %".24" = sub i64 %".21", %".23", !dbg !262
  %".25" = sub i64 %".24", 1, !dbg !262
  %".26" = sub i64 %".25", 18, !dbg !262
  %".27" = trunc i64 %".26" to i32 , !dbg !262
  store i32 %".27", i32* %"dots.addr", !dbg !262
  call void @"llvm.dbg.declare"(metadata i32* %"dots.addr", metadata !263, metadata !7), !dbg !264
  %".30" = load i32, i32* %"dots.addr", !dbg !265
  %".31" = icmp slt i32 %".30", 3 , !dbg !265
  br i1 %".31", label %"if.then", label %"if.end", !dbg !265
if.then:
  store i32 3, i32* %"dots.addr", !dbg !266
  br label %"if.end", !dbg !266
if.end:
  %".35" = call i32 @"color_dim"(), !dbg !267
  %".36" = load i32, i32* %"dots.addr", !dbg !268
  %".37" = call i32 @"print_dots"(i32 %".36"), !dbg !268
  %".38" = call i32 @"color_reset"(), !dbg !269
  %".39" = getelementptr [2 x i8], [2 x i8]* @".str.41", i64 0, i64 0 , !dbg !270
  %".40" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".39", 0 , !dbg !270
  %".41" = insertvalue %"struct.ritz_module_1.StrView" %".40", i64 1, 1 , !dbg !270
  %".42" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".41"), !dbg !270
  %".43" = call i32 @"color_yellow"(), !dbg !271
  %".44" = call i32 @"color_bold"(), !dbg !272
  %".45" = getelementptr [8 x i8], [8 x i8]* @".str.42", i64 0, i64 0 , !dbg !273
  %".46" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".45", 0 , !dbg !273
  %".47" = insertvalue %"struct.ritz_module_1.StrView" %".46", i64 7, 1 , !dbg !273
  %".48" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".47"), !dbg !273
  %".49" = call i32 @"color_reset"(), !dbg !274
  %".50" = getelementptr [3 x i8], [3 x i8]* @".str.43", i64 0, i64 0 , !dbg !275
  %".51" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".50", 0 , !dbg !275
  %".52" = insertvalue %"struct.ritz_module_1.StrView" %".51", i64 2, 1 , !dbg !275
  %".53" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".52"), !dbg !275
  %".54" = load i64, i64* %"timeout_ms", !dbg !276
  %".55" = call i32 @"print_int"(i64 %".54"), !dbg !276
  %".56" = getelementptr [5 x i8], [5 x i8]* @".str.44", i64 0, i64 0 , !dbg !277
  %".57" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".56", 0 , !dbg !277
  %".58" = insertvalue %"struct.ritz_module_1.StrView" %".57", i64 4, 1 , !dbg !277
  %".59" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".58"), !dbg !277
  ret i32 %".59", !dbg !277
}

define i32 @"print_test_skip"(%"struct.ritz_module_1.StrView" %"name.arg", %"struct.ritz_module_1.StrView" %"reason.arg") !dbg !38
{
entry:
  %"name" = alloca %"struct.ritz_module_1.StrView"
  %"dots.addr" = alloca i32, !dbg !286
  store %"struct.ritz_module_1.StrView" %"name.arg", %"struct.ritz_module_1.StrView"* %"name"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"name", metadata !278, metadata !7), !dbg !279
  %"reason" = alloca %"struct.ritz_module_1.StrView"
  store %"struct.ritz_module_1.StrView" %"reason.arg", %"struct.ritz_module_1.StrView"* %"reason"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"reason", metadata !280, metadata !7), !dbg !279
  %".8" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name", i32 0, i32 1 , !dbg !281
  %".9" = load i64, i64* %".8", !dbg !281
  %".10" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"reason", i32 0, i32 1 , !dbg !282
  %".11" = load i64, i64* %".10", !dbg !282
  %".12" = getelementptr [3 x i8], [3 x i8]* @".str.45", i64 0, i64 0 , !dbg !283
  %".13" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".12", 0 , !dbg !283
  %".14" = insertvalue %"struct.ritz_module_1.StrView" %".13", i64 2, 1 , !dbg !283
  %".15" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".14"), !dbg !283
  %".16" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"name", !dbg !284
  %".17" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".16"), !dbg !284
  %".18" = getelementptr [2 x i8], [2 x i8]* @".str.46", i64 0, i64 0 , !dbg !285
  %".19" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".18", 0 , !dbg !285
  %".20" = insertvalue %"struct.ritz_module_1.StrView" %".19", i64 1, 1 , !dbg !285
  %".21" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".20"), !dbg !285
  %".22" = sext i32 70 to i64 , !dbg !286
  %".23" = sub i64 %".22", 2, !dbg !286
  %".24" = trunc i64 %".9" to i32 , !dbg !286
  %".25" = sext i32 %".24" to i64 , !dbg !286
  %".26" = sub i64 %".23", %".25", !dbg !286
  %".27" = sub i64 %".26", 1, !dbg !286
  %".28" = sub i64 %".27", 8, !dbg !286
  %".29" = trunc i64 %".28" to i32 , !dbg !286
  store i32 %".29", i32* %"dots.addr", !dbg !286
  call void @"llvm.dbg.declare"(metadata i32* %"dots.addr", metadata !287, metadata !7), !dbg !288
  %".32" = load i32, i32* %"dots.addr", !dbg !289
  %".33" = icmp slt i32 %".32", 3 , !dbg !289
  br i1 %".33", label %"if.then", label %"if.end", !dbg !289
if.then:
  store i32 3, i32* %"dots.addr", !dbg !290
  br label %"if.end", !dbg !290
if.end:
  %".37" = call i32 @"color_dim"(), !dbg !291
  %".38" = load i32, i32* %"dots.addr", !dbg !292
  %".39" = call i32 @"print_dots"(i32 %".38"), !dbg !292
  %".40" = call i32 @"color_reset"(), !dbg !293
  %".41" = getelementptr [2 x i8], [2 x i8]* @".str.47", i64 0, i64 0 , !dbg !294
  %".42" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".41", 0 , !dbg !294
  %".43" = insertvalue %"struct.ritz_module_1.StrView" %".42", i64 1, 1 , !dbg !294
  %".44" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".43"), !dbg !294
  %".45" = call i32 @"color_yellow"(), !dbg !295
  %".46" = getelementptr [5 x i8], [5 x i8]* @".str.48", i64 0, i64 0 , !dbg !296
  %".47" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".46", 0 , !dbg !296
  %".48" = insertvalue %"struct.ritz_module_1.StrView" %".47", i64 4, 1 , !dbg !296
  %".49" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".48"), !dbg !296
  %".50" = call i32 @"color_reset"(), !dbg !297
  %".51" = icmp sgt i64 %".11", 0 , !dbg !298
  br i1 %".51", label %"if.then.1", label %"if.end.1", !dbg !298
if.then.1:
  %".53" = getelementptr [3 x i8], [3 x i8]* @".str.49", i64 0, i64 0 , !dbg !299
  %".54" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".53", 0 , !dbg !299
  %".55" = insertvalue %"struct.ritz_module_1.StrView" %".54", i64 2, 1 , !dbg !299
  %".56" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".55"), !dbg !299
  %".57" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"reason", !dbg !300
  %".58" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".57"), !dbg !300
  %".59" = getelementptr [2 x i8], [2 x i8]* @".str.50", i64 0, i64 0 , !dbg !300
  %".60" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".59", 0 , !dbg !300
  %".61" = insertvalue %"struct.ritz_module_1.StrView" %".60", i64 1, 1 , !dbg !300
  %".62" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".61"), !dbg !300
  br label %"if.end.1", !dbg !300
if.end.1:
  %".64" = getelementptr [2 x i8], [2 x i8]* @".str.51", i64 0, i64 0 , !dbg !301
  %".65" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".64", 0 , !dbg !301
  %".66" = insertvalue %"struct.ritz_module_1.StrView" %".65", i64 1, 1 , !dbg !301
  %".67" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".66"), !dbg !301
  ret i32 %".67", !dbg !301
}

define i32 @"print_suite_summary"(i32 %"total.arg", i32 %"passed.arg", i32 %"failed.arg", i32 %"crashed.arg", i32 %"timeout.arg", i64 %"duration_ms.arg") !dbg !39
{
entry:
  %"total" = alloca i32
  store i32 %"total.arg", i32* %"total"
  call void @"llvm.dbg.declare"(metadata i32* %"total", metadata !302, metadata !7), !dbg !303
  %"passed" = alloca i32
  store i32 %"passed.arg", i32* %"passed"
  call void @"llvm.dbg.declare"(metadata i32* %"passed", metadata !304, metadata !7), !dbg !303
  %"failed" = alloca i32
  store i32 %"failed.arg", i32* %"failed"
  call void @"llvm.dbg.declare"(metadata i32* %"failed", metadata !305, metadata !7), !dbg !303
  %"crashed" = alloca i32
  store i32 %"crashed.arg", i32* %"crashed"
  call void @"llvm.dbg.declare"(metadata i32* %"crashed", metadata !306, metadata !7), !dbg !303
  %"timeout" = alloca i32
  store i32 %"timeout.arg", i32* %"timeout"
  call void @"llvm.dbg.declare"(metadata i32* %"timeout", metadata !307, metadata !7), !dbg !303
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !308, metadata !7), !dbg !303
  %".20" = getelementptr [3 x i8], [3 x i8]* @".str.52", i64 0, i64 0 , !dbg !309
  %".21" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".20", 0 , !dbg !309
  %".22" = insertvalue %"struct.ritz_module_1.StrView" %".21", i64 2, 1 , !dbg !309
  %".23" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".22"), !dbg !309
  %".24" = load i32, i32* %"total", !dbg !310
  %".25" = sext i32 %".24" to i64 , !dbg !310
  %".26" = call i32 @"print_int"(i64 %".25"), !dbg !310
  %".27" = getelementptr [9 x i8], [9 x i8]* @".str.53", i64 0, i64 0 , !dbg !311
  %".28" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".27", 0 , !dbg !311
  %".29" = insertvalue %"struct.ritz_module_1.StrView" %".28", i64 8, 1 , !dbg !311
  %".30" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".29"), !dbg !311
  %".31" = load i32, i32* %"passed", !dbg !312
  %".32" = sext i32 %".31" to i64 , !dbg !312
  %".33" = call i32 @"print_int"(i64 %".32"), !dbg !312
  %".34" = getelementptr [8 x i8], [8 x i8]* @".str.54", i64 0, i64 0 , !dbg !313
  %".35" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".34", 0 , !dbg !313
  %".36" = insertvalue %"struct.ritz_module_1.StrView" %".35", i64 7, 1 , !dbg !313
  %".37" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".36"), !dbg !313
  %".38" = load i32, i32* %"failed", !dbg !314
  %".39" = sext i32 %".38" to i64 , !dbg !314
  %".40" = icmp sgt i64 %".39", 0 , !dbg !314
  br i1 %".40", label %"if.then", label %"if.end", !dbg !314
if.then:
  %".42" = getelementptr [3 x i8], [3 x i8]* @".str.55", i64 0, i64 0 , !dbg !315
  %".43" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".42", 0 , !dbg !315
  %".44" = insertvalue %"struct.ritz_module_1.StrView" %".43", i64 2, 1 , !dbg !315
  %".45" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".44"), !dbg !315
  %".46" = load i32, i32* %"failed", !dbg !316
  %".47" = sext i32 %".46" to i64 , !dbg !316
  %".48" = call i32 @"print_int"(i64 %".47"), !dbg !316
  %".49" = getelementptr [8 x i8], [8 x i8]* @".str.56", i64 0, i64 0 , !dbg !316
  %".50" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".49", 0 , !dbg !316
  %".51" = insertvalue %"struct.ritz_module_1.StrView" %".50", i64 7, 1 , !dbg !316
  %".52" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".51"), !dbg !316
  br label %"if.end", !dbg !316
if.end:
  %".54" = load i32, i32* %"crashed", !dbg !317
  %".55" = sext i32 %".54" to i64 , !dbg !317
  %".56" = icmp sgt i64 %".55", 0 , !dbg !317
  br i1 %".56", label %"if.then.1", label %"if.end.1", !dbg !317
if.then.1:
  %".58" = getelementptr [3 x i8], [3 x i8]* @".str.57", i64 0, i64 0 , !dbg !318
  %".59" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".58", 0 , !dbg !318
  %".60" = insertvalue %"struct.ritz_module_1.StrView" %".59", i64 2, 1 , !dbg !318
  %".61" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".60"), !dbg !318
  %".62" = load i32, i32* %"crashed", !dbg !319
  %".63" = sext i32 %".62" to i64 , !dbg !319
  %".64" = call i32 @"print_int"(i64 %".63"), !dbg !319
  %".65" = getelementptr [9 x i8], [9 x i8]* @".str.58", i64 0, i64 0 , !dbg !319
  %".66" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".65", 0 , !dbg !319
  %".67" = insertvalue %"struct.ritz_module_1.StrView" %".66", i64 8, 1 , !dbg !319
  %".68" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".67"), !dbg !319
  br label %"if.end.1", !dbg !319
if.end.1:
  %".70" = load i32, i32* %"timeout", !dbg !320
  %".71" = sext i32 %".70" to i64 , !dbg !320
  %".72" = icmp sgt i64 %".71", 0 , !dbg !320
  br i1 %".72", label %"if.then.2", label %"if.end.2", !dbg !320
if.then.2:
  %".74" = getelementptr [3 x i8], [3 x i8]* @".str.59", i64 0, i64 0 , !dbg !321
  %".75" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".74", 0 , !dbg !321
  %".76" = insertvalue %"struct.ritz_module_1.StrView" %".75", i64 2, 1 , !dbg !321
  %".77" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".76"), !dbg !321
  %".78" = load i32, i32* %"timeout", !dbg !322
  %".79" = sext i32 %".78" to i64 , !dbg !322
  %".80" = call i32 @"print_int"(i64 %".79"), !dbg !322
  %".81" = getelementptr [9 x i8], [9 x i8]* @".str.60", i64 0, i64 0 , !dbg !322
  %".82" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".81", 0 , !dbg !322
  %".83" = insertvalue %"struct.ritz_module_1.StrView" %".82", i64 8, 1 , !dbg !322
  %".84" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".83"), !dbg !322
  br label %"if.end.2", !dbg !322
if.end.2:
  %".86" = getelementptr [3 x i8], [3 x i8]* @".str.61", i64 0, i64 0 , !dbg !323
  %".87" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".86", 0 , !dbg !323
  %".88" = insertvalue %"struct.ritz_module_1.StrView" %".87", i64 2, 1 , !dbg !323
  %".89" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".88"), !dbg !323
  %".90" = load i64, i64* %"duration_ms", !dbg !324
  %".91" = call i32 @"print_int"(i64 %".90"), !dbg !324
  %".92" = getelementptr [6 x i8], [6 x i8]* @".str.62", i64 0, i64 0 , !dbg !325
  %".93" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".92", 0 , !dbg !325
  %".94" = insertvalue %"struct.ritz_module_1.StrView" %".93", i64 5, 1 , !dbg !325
  %".95" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".94"), !dbg !325
  ret i32 %".95", !dbg !325
}

define i32 @"print_grand_summary"(i32 %"total.arg", i32 %"passed.arg", i32 %"failed.arg", i32 %"crashed.arg", i32 %"timeout.arg", i32 %"skipped.arg", i64 %"duration_ms.arg") !dbg !40
{
entry:
  %"total" = alloca i32
  store i32 %"total.arg", i32* %"total"
  call void @"llvm.dbg.declare"(metadata i32* %"total", metadata !326, metadata !7), !dbg !327
  %"passed" = alloca i32
  store i32 %"passed.arg", i32* %"passed"
  call void @"llvm.dbg.declare"(metadata i32* %"passed", metadata !328, metadata !7), !dbg !327
  %"failed" = alloca i32
  store i32 %"failed.arg", i32* %"failed"
  call void @"llvm.dbg.declare"(metadata i32* %"failed", metadata !329, metadata !7), !dbg !327
  %"crashed" = alloca i32
  store i32 %"crashed.arg", i32* %"crashed"
  call void @"llvm.dbg.declare"(metadata i32* %"crashed", metadata !330, metadata !7), !dbg !327
  %"timeout" = alloca i32
  store i32 %"timeout.arg", i32* %"timeout"
  call void @"llvm.dbg.declare"(metadata i32* %"timeout", metadata !331, metadata !7), !dbg !327
  %"skipped" = alloca i32
  store i32 %"skipped.arg", i32* %"skipped"
  call void @"llvm.dbg.declare"(metadata i32* %"skipped", metadata !332, metadata !7), !dbg !327
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !333, metadata !7), !dbg !327
  %".23" = call i32 @"print_grand_divider"(), !dbg !334
  %".24" = call i32 @"color_bold"(), !dbg !335
  %".25" = getelementptr [8 x i8], [8 x i8]* @".str.63", i64 0, i64 0 , !dbg !336
  %".26" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".25", 0 , !dbg !336
  %".27" = insertvalue %"struct.ritz_module_1.StrView" %".26", i64 7, 1 , !dbg !336
  %".28" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".27"), !dbg !336
  %".29" = call i32 @"color_reset"(), !dbg !337
  %".30" = load i32, i32* %"total", !dbg !338
  %".31" = sext i32 %".30" to i64 , !dbg !338
  %".32" = call i32 @"print_int"(i64 %".31"), !dbg !338
  %".33" = getelementptr [7 x i8], [7 x i8]* @".str.64", i64 0, i64 0 , !dbg !339
  %".34" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".33", 0 , !dbg !339
  %".35" = insertvalue %"struct.ritz_module_1.StrView" %".34", i64 6, 1 , !dbg !339
  %".36" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".35"), !dbg !339
  %".37" = getelementptr [4 x i8], [4 x i8]* @".str.65", i64 0, i64 0 , !dbg !340
  %".38" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".37", 0 , !dbg !340
  %".39" = insertvalue %"struct.ritz_module_1.StrView" %".38", i64 3, 1 , !dbg !340
  %".40" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".39"), !dbg !340
  %".41" = call i32 @"color_green"(), !dbg !341
  %".42" = load i32, i32* %"passed", !dbg !342
  %".43" = sext i32 %".42" to i64 , !dbg !342
  %".44" = call i32 @"print_int"(i64 %".43"), !dbg !342
  %".45" = getelementptr [8 x i8], [8 x i8]* @".str.66", i64 0, i64 0 , !dbg !343
  %".46" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".45", 0 , !dbg !343
  %".47" = insertvalue %"struct.ritz_module_1.StrView" %".46", i64 7, 1 , !dbg !343
  %".48" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".47"), !dbg !343
  %".49" = call i32 @"color_reset"(), !dbg !344
  %".50" = load i32, i32* %"failed", !dbg !345
  %".51" = sext i32 %".50" to i64 , !dbg !345
  %".52" = icmp sgt i64 %".51", 0 , !dbg !345
  br i1 %".52", label %"if.then", label %"if.end", !dbg !345
if.then:
  %".54" = getelementptr [4 x i8], [4 x i8]* @".str.67", i64 0, i64 0 , !dbg !346
  %".55" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".54", 0 , !dbg !346
  %".56" = insertvalue %"struct.ritz_module_1.StrView" %".55", i64 3, 1 , !dbg !346
  %".57" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".56"), !dbg !346
  %".58" = call i32 @"color_red"(), !dbg !347
  %".59" = load i32, i32* %"failed", !dbg !348
  %".60" = sext i32 %".59" to i64 , !dbg !348
  %".61" = call i32 @"print_int"(i64 %".60"), !dbg !348
  %".62" = getelementptr [8 x i8], [8 x i8]* @".str.68", i64 0, i64 0 , !dbg !349
  %".63" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".62", 0 , !dbg !349
  %".64" = insertvalue %"struct.ritz_module_1.StrView" %".63", i64 7, 1 , !dbg !349
  %".65" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".64"), !dbg !349
  %".66" = call i32 @"color_reset"(), !dbg !349
  br label %"if.end", !dbg !349
if.end:
  %".68" = load i32, i32* %"crashed", !dbg !350
  %".69" = sext i32 %".68" to i64 , !dbg !350
  %".70" = icmp sgt i64 %".69", 0 , !dbg !350
  br i1 %".70", label %"if.then.1", label %"if.end.1", !dbg !350
if.then.1:
  %".72" = getelementptr [4 x i8], [4 x i8]* @".str.69", i64 0, i64 0 , !dbg !351
  %".73" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".72", 0 , !dbg !351
  %".74" = insertvalue %"struct.ritz_module_1.StrView" %".73", i64 3, 1 , !dbg !351
  %".75" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".74"), !dbg !351
  %".76" = call i32 @"color_red"(), !dbg !352
  %".77" = load i32, i32* %"crashed", !dbg !353
  %".78" = sext i32 %".77" to i64 , !dbg !353
  %".79" = call i32 @"print_int"(i64 %".78"), !dbg !353
  %".80" = getelementptr [9 x i8], [9 x i8]* @".str.70", i64 0, i64 0 , !dbg !354
  %".81" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".80", 0 , !dbg !354
  %".82" = insertvalue %"struct.ritz_module_1.StrView" %".81", i64 8, 1 , !dbg !354
  %".83" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".82"), !dbg !354
  %".84" = call i32 @"color_reset"(), !dbg !354
  br label %"if.end.1", !dbg !354
if.end.1:
  %".86" = load i32, i32* %"timeout", !dbg !355
  %".87" = sext i32 %".86" to i64 , !dbg !355
  %".88" = icmp sgt i64 %".87", 0 , !dbg !355
  br i1 %".88", label %"if.then.2", label %"if.end.2", !dbg !355
if.then.2:
  %".90" = getelementptr [4 x i8], [4 x i8]* @".str.71", i64 0, i64 0 , !dbg !356
  %".91" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".90", 0 , !dbg !356
  %".92" = insertvalue %"struct.ritz_module_1.StrView" %".91", i64 3, 1 , !dbg !356
  %".93" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".92"), !dbg !356
  %".94" = call i32 @"color_yellow"(), !dbg !357
  %".95" = load i32, i32* %"timeout", !dbg !358
  %".96" = sext i32 %".95" to i64 , !dbg !358
  %".97" = call i32 @"print_int"(i64 %".96"), !dbg !358
  %".98" = getelementptr [9 x i8], [9 x i8]* @".str.72", i64 0, i64 0 , !dbg !359
  %".99" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".98", 0 , !dbg !359
  %".100" = insertvalue %"struct.ritz_module_1.StrView" %".99", i64 8, 1 , !dbg !359
  %".101" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".100"), !dbg !359
  %".102" = call i32 @"color_reset"(), !dbg !359
  br label %"if.end.2", !dbg !359
if.end.2:
  %".104" = load i32, i32* %"skipped", !dbg !360
  %".105" = sext i32 %".104" to i64 , !dbg !360
  %".106" = icmp sgt i64 %".105", 0 , !dbg !360
  br i1 %".106", label %"if.then.3", label %"if.end.3", !dbg !360
if.then.3:
  %".108" = getelementptr [4 x i8], [4 x i8]* @".str.73", i64 0, i64 0 , !dbg !361
  %".109" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".108", 0 , !dbg !361
  %".110" = insertvalue %"struct.ritz_module_1.StrView" %".109", i64 3, 1 , !dbg !361
  %".111" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".110"), !dbg !361
  %".112" = call i32 @"color_yellow"(), !dbg !362
  %".113" = load i32, i32* %"skipped", !dbg !363
  %".114" = sext i32 %".113" to i64 , !dbg !363
  %".115" = call i32 @"print_int"(i64 %".114"), !dbg !363
  %".116" = getelementptr [9 x i8], [9 x i8]* @".str.74", i64 0, i64 0 , !dbg !364
  %".117" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".116", 0 , !dbg !364
  %".118" = insertvalue %"struct.ritz_module_1.StrView" %".117", i64 8, 1 , !dbg !364
  %".119" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".118"), !dbg !364
  %".120" = call i32 @"color_reset"(), !dbg !364
  br label %"if.end.3", !dbg !364
if.end.3:
  %".122" = getelementptr [3 x i8], [3 x i8]* @".str.75", i64 0, i64 0 , !dbg !365
  %".123" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".122", 0 , !dbg !365
  %".124" = insertvalue %"struct.ritz_module_1.StrView" %".123", i64 2, 1 , !dbg !365
  %".125" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".124"), !dbg !365
  %".126" = load i64, i64* %"duration_ms", !dbg !366
  %".127" = call i32 @"print_int"(i64 %".126"), !dbg !366
  %".128" = getelementptr [5 x i8], [5 x i8]* @".str.76", i64 0, i64 0 , !dbg !367
  %".129" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".128", 0 , !dbg !367
  %".130" = insertvalue %"struct.ritz_module_1.StrView" %".129", i64 4, 1 , !dbg !367
  %".131" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".130"), !dbg !367
  %".132" = call i32 @"print_grand_divider"(), !dbg !368
  ret i32 %".132", !dbg !368
}

define i32 @"print_divider"() !dbg !41
{
entry:
  %".2" = getelementptr [2 x i8], [2 x i8]* @".str.77", i64 0, i64 0 , !dbg !369
  %".3" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".2", 0 , !dbg !369
  %".4" = insertvalue %"struct.ritz_module_1.StrView" %".3", i64 1, 1 , !dbg !369
  %".5" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".4"), !dbg !369
  ret i32 %".5", !dbg !369
}

define i32 @"print_summary"(i32 %"passed.arg", i32 %"failed.arg", i32 %"skipped.arg", i64 %"duration_ms.arg") !dbg !42
{
entry:
  %"passed" = alloca i32
  store i32 %"passed.arg", i32* %"passed"
  call void @"llvm.dbg.declare"(metadata i32* %"passed", metadata !370, metadata !7), !dbg !371
  %"failed" = alloca i32
  store i32 %"failed.arg", i32* %"failed"
  call void @"llvm.dbg.declare"(metadata i32* %"failed", metadata !372, metadata !7), !dbg !371
  %"skipped" = alloca i32
  store i32 %"skipped.arg", i32* %"skipped"
  call void @"llvm.dbg.declare"(metadata i32* %"skipped", metadata !373, metadata !7), !dbg !371
  %"duration_ms" = alloca i64
  store i64 %"duration_ms.arg", i64* %"duration_ms"
  call void @"llvm.dbg.declare"(metadata i64* %"duration_ms", metadata !374, metadata !7), !dbg !371
  %".14" = load i32, i32* %"passed", !dbg !375
  %".15" = load i32, i32* %"failed", !dbg !375
  %".16" = add i32 %".14", %".15", !dbg !375
  %".17" = load i32, i32* %"passed", !dbg !375
  %".18" = load i32, i32* %"failed", !dbg !375
  %".19" = trunc i64 0 to i32 , !dbg !375
  %".20" = trunc i64 0 to i32 , !dbg !375
  %".21" = load i32, i32* %"skipped", !dbg !375
  %".22" = load i64, i64* %"duration_ms", !dbg !375
  %".23" = call i32 @"print_grand_summary"(i32 %".16", i32 %".17", i32 %".18", i32 %".19", i32 %".20", i32 %".21", i64 %".22"), !dbg !375
  ret i32 %".23", !dbg !375
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !43
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !378, metadata !7), !dbg !379
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !380
  %".5" = load i64, i64* %".4", !dbg !380
  %".6" = sub i64 %".5", 1, !dbg !380
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !380
  store i64 %".6", i64* %".7", !dbg !380
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !381
  %".10" = load i8*, i8** %".9", !dbg !381
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !381
  %".12" = load i64, i64* %".11", !dbg !381
  %".13" = getelementptr i8, i8* %".10", i64 %".12" , !dbg !381
  %".14" = load i8, i8* %".13", !dbg !381
  ret i8 %".14", !dbg !381
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !44
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !382, metadata !7), !dbg !383
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !384, metadata !7), !dbg !383
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !385
  %".8" = load i64, i64* %".7", !dbg !385
  %".9" = add i64 %".8", 1, !dbg !385
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !385
  %".11" = sext i32 %".10" to i64 , !dbg !385
  %".12" = icmp ne i64 %".11", 0 , !dbg !385
  br i1 %".12", label %"if.then", label %"if.end", !dbg !385
if.then:
  %".14" = sub i64 0, 1, !dbg !386
  %".15" = trunc i64 %".14" to i32 , !dbg !386
  ret i32 %".15", !dbg !386
if.end:
  %".17" = load i8, i8* %"item", !dbg !387
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !387
  %".19" = load i8*, i8** %".18", !dbg !387
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !387
  %".21" = load i64, i64* %".20", !dbg !387
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !387
  store i8 %".17", i8* %".22", !dbg !387
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !388
  %".25" = load i64, i64* %".24", !dbg !388
  %".26" = add i64 %".25", 1, !dbg !388
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !388
  store i64 %".26", i64* %".27", !dbg !388
  %".29" = trunc i64 0 to i32 , !dbg !389
  ret i32 %".29", !dbg !389
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !45
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !390, metadata !7), !dbg !391
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !392
  %".5" = load i8*, i8** %".4", !dbg !392
  %".6" = icmp ne i8* %".5", null , !dbg !392
  br i1 %".6", label %"if.then", label %"if.end", !dbg !392
if.then:
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !392
  %".9" = load i8*, i8** %".8", !dbg !392
  %".10" = call i32 @"free"(i8* %".9"), !dbg !392
  br label %"if.end", !dbg !392
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !393
  store i8* null, i8** %".12", !dbg !393
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !394
  store i64 0, i64* %".14", !dbg !394
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !395
  store i64 0, i64* %".16", !dbg !395
  ret i32 0, !dbg !395
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !46
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !398
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !396, metadata !7), !dbg !397
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !399, metadata !7), !dbg !400
  %".6" = load i64, i64* %"cap", !dbg !401
  %".7" = icmp sle i64 %".6", 0 , !dbg !401
  br i1 %".7", label %"if.then", label %"if.end", !dbg !401
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !402
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !402
  store i8* null, i8** %".10", !dbg !402
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !403
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !403
  store i64 0, i64* %".13", !dbg !403
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !404
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !404
  store i64 0, i64* %".16", !dbg !404
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !405
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !405
if.end:
  %".20" = load i64, i64* %"cap", !dbg !406
  %".21" = mul i64 %".20", 1, !dbg !406
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !407
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !407
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !407
  store i8* %".22", i8** %".24", !dbg !407
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !408
  %".27" = load i8*, i8** %".26", !dbg !408
  %".28" = icmp eq i8* %".27", null , !dbg !408
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !408
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !409
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !409
  store i64 0, i64* %".31", !dbg !409
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !410
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !410
  store i64 0, i64* %".34", !dbg !410
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !411
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !411
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !412
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !412
  store i64 0, i64* %".39", !dbg !412
  %".41" = load i64, i64* %"cap", !dbg !413
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !413
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !413
  store i64 %".41", i64* %".43", !dbg !413
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !414
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !414
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !47
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !415
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !416, metadata !7), !dbg !417
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !418
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !418
  store i8* null, i8** %".4", !dbg !418
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !419
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !419
  store i64 0, i64* %".7", !dbg !419
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !420
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !420
  store i64 0, i64* %".10", !dbg !420
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !421
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !421
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !48
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !424, metadata !7), !dbg !425
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !427, metadata !7), !dbg !425
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !428
  %".8" = load i64, i64* %".7", !dbg !428
  %".9" = add i64 %".8", 1, !dbg !428
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !428
  %".11" = sext i32 %".10" to i64 , !dbg !428
  %".12" = icmp ne i64 %".11", 0 , !dbg !428
  br i1 %".12", label %"if.then", label %"if.end", !dbg !428
if.then:
  %".14" = sub i64 0, 1, !dbg !429
  %".15" = trunc i64 %".14" to i32 , !dbg !429
  ret i32 %".15", !dbg !429
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !430
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !430
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !430
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !430
  %".21" = load i64, i64* %".20", !dbg !430
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !430
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !430
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !431
  %".25" = load i64, i64* %".24", !dbg !431
  %".26" = add i64 %".25", 1, !dbg !431
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !431
  store i64 %".26", i64* %".27", !dbg !431
  %".29" = trunc i64 0 to i32 , !dbg !432
  ret i32 %".29", !dbg !432
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !49
{
entry:
  %"i" = alloca i64, !dbg !438
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !433, metadata !7), !dbg !434
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !436, metadata !7), !dbg !434
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !437, metadata !7), !dbg !434
  %".10" = load i64, i64* %"len", !dbg !438
  store i64 0, i64* %"i", !dbg !438
  br label %"for.cond", !dbg !438
for.cond:
  %".13" = load i64, i64* %"i", !dbg !438
  %".14" = icmp slt i64 %".13", %".10" , !dbg !438
  br i1 %".14", label %"for.body", label %"for.end", !dbg !438
for.body:
  %".16" = load i8*, i8** %"data", !dbg !438
  %".17" = load i64, i64* %"i", !dbg !438
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !438
  %".19" = load i8, i8* %".18", !dbg !438
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !438
  %".21" = sext i32 %".20" to i64 , !dbg !438
  %".22" = icmp ne i64 %".21", 0 , !dbg !438
  br i1 %".22", label %"if.then", label %"if.end", !dbg !438
for.incr:
  %".28" = load i64, i64* %"i", !dbg !439
  %".29" = add i64 %".28", 1, !dbg !439
  store i64 %".29", i64* %"i", !dbg !439
  br label %"for.cond", !dbg !439
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !440
  ret i32 %".32", !dbg !440
if.then:
  %".24" = sub i64 0, 1, !dbg !439
  %".25" = trunc i64 %".24" to i32 , !dbg !439
  ret i32 %".25", !dbg !439
if.end:
  br label %"for.incr", !dbg !439
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !50
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !446
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !441, metadata !7), !dbg !442
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !443, metadata !7), !dbg !442
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !444
  %".8" = load i64, i64* %".7", !dbg !444
  %".9" = load i64, i64* %"needed", !dbg !444
  %".10" = icmp sge i64 %".8", %".9" , !dbg !444
  br i1 %".10", label %"if.then", label %"if.end", !dbg !444
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !445
  ret i32 %".12", !dbg !445
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !446
  %".15" = load i64, i64* %".14", !dbg !446
  store i64 %".15", i64* %"new_cap.addr", !dbg !446
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !447, metadata !7), !dbg !448
  %".18" = load i64, i64* %"new_cap.addr", !dbg !449
  %".19" = icmp eq i64 %".18", 0 , !dbg !449
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !449
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !450
  br label %"if.end.1", !dbg !450
if.end.1:
  br label %"while.cond", !dbg !451
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !451
  %".25" = load i64, i64* %"needed", !dbg !451
  %".26" = icmp slt i64 %".24", %".25" , !dbg !451
  br i1 %".26", label %"while.body", label %"while.end", !dbg !451
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !452
  %".29" = mul i64 %".28", 2, !dbg !452
  store i64 %".29", i64* %"new_cap.addr", !dbg !452
  br label %"while.cond", !dbg !452
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !453
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !453
  ret i32 %".33", !dbg !453
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !51
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !454, metadata !7), !dbg !455
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !456, metadata !7), !dbg !455
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !457, metadata !7), !dbg !455
  %".10" = load i8, i8* %"item", !dbg !458
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !458
  %".12" = load i8*, i8** %".11", !dbg !458
  %".13" = load i64, i64* %"idx", !dbg !458
  %".14" = getelementptr i8, i8* %".12", i64 %".13" , !dbg !458
  store i8 %".10", i8* %".14", !dbg !458
  %".16" = trunc i64 0 to i32 , !dbg !459
  ret i32 %".16", !dbg !459
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !52
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !460, metadata !7), !dbg !461
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !462, metadata !7), !dbg !461
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !463
  %".8" = load i8*, i8** %".7", !dbg !463
  %".9" = load i64, i64* %"idx", !dbg !463
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !463
  %".11" = load i8, i8* %".10", !dbg !463
  ret i8 %".11", !dbg !463
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !53
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !464, metadata !7), !dbg !465
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !466
  store i64 0, i64* %".4", !dbg !466
  ret i32 0, !dbg !466
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !54
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !467, metadata !7), !dbg !468
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !469, metadata !7), !dbg !468
  %".7" = load i64, i64* %"new_cap", !dbg !470
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !470
  %".9" = load i64, i64* %".8", !dbg !470
  %".10" = icmp sle i64 %".7", %".9" , !dbg !470
  br i1 %".10", label %"if.then", label %"if.end", !dbg !470
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !471
  ret i32 %".12", !dbg !471
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !472
  %".15" = mul i64 %".14", 1, !dbg !472
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !473
  %".17" = load i8*, i8** %".16", !dbg !473
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !473
  %".19" = icmp eq i8* %".18", null , !dbg !474
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !474
if.then.1:
  %".21" = sub i64 0, 1, !dbg !475
  %".22" = trunc i64 %".21" to i32 , !dbg !475
  ret i32 %".22", !dbg !475
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !476
  store i8* %".18", i8** %".24", !dbg !476
  %".26" = load i64, i64* %"new_cap", !dbg !477
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !477
  store i64 %".26", i64* %".27", !dbg !477
  %".29" = trunc i64 0 to i32 , !dbg !478
  ret i32 %".29", !dbg !478
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !55
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !484
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !479, metadata !7), !dbg !480
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !481, metadata !7), !dbg !480
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !482
  %".8" = load i64, i64* %".7", !dbg !482
  %".9" = load i64, i64* %"needed", !dbg !482
  %".10" = icmp sge i64 %".8", %".9" , !dbg !482
  br i1 %".10", label %"if.then", label %"if.end", !dbg !482
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !483
  ret i32 %".12", !dbg !483
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !484
  %".15" = load i64, i64* %".14", !dbg !484
  store i64 %".15", i64* %"new_cap.addr", !dbg !484
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !485, metadata !7), !dbg !486
  %".18" = load i64, i64* %"new_cap.addr", !dbg !487
  %".19" = icmp eq i64 %".18", 0 , !dbg !487
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !487
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !488
  br label %"if.end.1", !dbg !488
if.end.1:
  br label %"while.cond", !dbg !489
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !489
  %".25" = load i64, i64* %"needed", !dbg !489
  %".26" = icmp slt i64 %".24", %".25" , !dbg !489
  br i1 %".26", label %"while.body", label %"while.end", !dbg !489
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !490
  %".29" = mul i64 %".28", 2, !dbg !490
  store i64 %".29", i64* %"new_cap.addr", !dbg !490
  br label %"while.cond", !dbg !490
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !491
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !491
  ret i32 %".33", !dbg !491
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !56
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !492, metadata !7), !dbg !493
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !494, metadata !7), !dbg !493
  %".7" = load i64, i64* %"new_cap", !dbg !495
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !495
  %".9" = load i64, i64* %".8", !dbg !495
  %".10" = icmp sle i64 %".7", %".9" , !dbg !495
  br i1 %".10", label %"if.then", label %"if.end", !dbg !495
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !496
  ret i32 %".12", !dbg !496
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !497
  %".15" = mul i64 %".14", 16, !dbg !497
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !498
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !498
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !498
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !498
  %".20" = icmp eq i8* %".19", null , !dbg !499
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !499
if.then.1:
  %".22" = sub i64 0, 1, !dbg !500
  %".23" = trunc i64 %".22" to i32 , !dbg !500
  ret i32 %".23", !dbg !500
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !501
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !501
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !501
  %".28" = load i64, i64* %"new_cap", !dbg !502
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !502
  store i64 %".28", i64* %".29", !dbg !502
  %".31" = trunc i64 0 to i32 , !dbg !503
  ret i32 %".31", !dbg !503
}

@".str.0" = private constant [4 x i8] c"[0m\00"
@".str.1" = private constant [5 x i8] c"[32m\00"
@".str.2" = private constant [5 x i8] c"[31m\00"
@".str.3" = private constant [5 x i8] c"[33m\00"
@".str.4" = private constant [4 x i8] c"[1m\00"
@".str.5" = private constant [4 x i8] c"[2m\00"
@".str.6" = private constant [72 x i8] c"======================================================================\0a\00"
@".str.7" = private constant [45 x i8] c"  RITZUNIT v0.1.0 - Test Framework for Ritz\0a\00"
@".str.8" = private constant [71 x i8] c"======================================================================\00"
@".str.9" = private constant [3 x i8] c"\0a\0a\00"
@".str.10" = private constant [2 x i8] c"\0a\00"
@".str.11" = private constant [74 x i8] c"  ----------------------------------------------------------------------\0a\00"
@".str.12" = private constant [72 x i8] c"======================================================================\0a\00"
@".str.13" = private constant [2 x i8] c".\00"
@".str.14" = private constant [3 x i8] c"  \00"
@".str.15" = private constant [2 x i8] c" \00"
@".str.16" = private constant [2 x i8] c" \00"
@".str.17" = private constant [3 x i8] c" (\00"
@".str.18" = private constant [5 x i8] c"ms)\0a\00"
@".str.19" = private constant [3 x i8] c"  \00"
@".str.20" = private constant [2 x i8] c" \00"
@".str.21" = private constant [2 x i8] c" \00"
@".str.22" = private constant [3 x i8] c"OK\00"
@".str.23" = private constant [3 x i8] c" (\00"
@".str.24" = private constant [5 x i8] c"ms)\0a\00"
@".str.25" = private constant [3 x i8] c"  \00"
@".str.26" = private constant [2 x i8] c" \00"
@".str.27" = private constant [2 x i8] c" \00"
@".str.28" = private constant [5 x i8] c"FAIL\00"
@".str.29" = private constant [8 x i8] c" [code=\00"
@".str.30" = private constant [4 x i8] c"] (\00"
@".str.31" = private constant [5 x i8] c"ms)\0a\00"
@".str.32" = private constant [3 x i8] c"  \00"
@".str.33" = private constant [2 x i8] c" \00"
@".str.34" = private constant [2 x i8] c" \00"
@".str.35" = private constant [6 x i8] c"CRASH\00"
@".str.36" = private constant [3 x i8] c" (\00"
@".str.37" = private constant [4 x i8] c") (\00"
@".str.38" = private constant [5 x i8] c"ms)\0a\00"
@".str.39" = private constant [3 x i8] c"  \00"
@".str.40" = private constant [2 x i8] c" \00"
@".str.41" = private constant [2 x i8] c" \00"
@".str.42" = private constant [8 x i8] c"TIMEOUT\00"
@".str.43" = private constant [3 x i8] c" (\00"
@".str.44" = private constant [5 x i8] c"ms)\0a\00"
@".str.45" = private constant [3 x i8] c"  \00"
@".str.46" = private constant [2 x i8] c" \00"
@".str.47" = private constant [2 x i8] c" \00"
@".str.48" = private constant [5 x i8] c"SKIP\00"
@".str.49" = private constant [3 x i8] c" (\00"
@".str.50" = private constant [2 x i8] c")\00"
@".str.51" = private constant [2 x i8] c"\0a\00"
@".str.52" = private constant [3 x i8] c"  \00"
@".str.53" = private constant [9 x i8] c" tests: \00"
@".str.54" = private constant [8 x i8] c" passed\00"
@".str.55" = private constant [3 x i8] c", \00"
@".str.56" = private constant [8 x i8] c" failed\00"
@".str.57" = private constant [3 x i8] c", \00"
@".str.58" = private constant [9 x i8] c" crashed\00"
@".str.59" = private constant [3 x i8] c", \00"
@".str.60" = private constant [9 x i8] c" timeout\00"
@".str.61" = private constant [3 x i8] c" (\00"
@".str.62" = private constant [6 x i8] c"ms)\0a\0a\00"
@".str.63" = private constant [8 x i8] c"TOTAL: \00"
@".str.64" = private constant [7 x i8] c" tests\00"
@".str.65" = private constant [4 x i8] c" | \00"
@".str.66" = private constant [8 x i8] c" passed\00"
@".str.67" = private constant [4 x i8] c" | \00"
@".str.68" = private constant [8 x i8] c" failed\00"
@".str.69" = private constant [4 x i8] c" | \00"
@".str.70" = private constant [9 x i8] c" crashed\00"
@".str.71" = private constant [4 x i8] c" | \00"
@".str.72" = private constant [9 x i8] c" timeout\00"
@".str.73" = private constant [4 x i8] c" | \00"
@".str.74" = private constant [9 x i8] c" skipped\00"
@".str.75" = private constant [3 x i8] c" (\00"
@".str.76" = private constant [5 x i8] c"ms)\0a\00"
@".str.77" = private constant [2 x i8] c"\0a\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/ritzunit/src", filename: "reporter.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 35, name: "isatty", scopeLine: 35, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 46, name: "set_color_mode", scopeLine: 46, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 50, name: "init_color", scopeLine: 50, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 63, name: "use_color", scopeLine: 63, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 73, name: "print_esc", scopeLine: 73, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 79, name: "color_reset", scopeLine: 79, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 85, name: "color_green", scopeLine: 85, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 91, name: "color_red", scopeLine: 91, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 97, name: "color_yellow", scopeLine: 97, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 103, name: "color_bold", scopeLine: 103, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 109, name: "color_dim", scopeLine: 109, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 120, name: "print_banner", scopeLine: 120, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 129, name: "print_suite_header", scopeLine: 129, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 134, name: "print_suite_divider", scopeLine: 134, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 138, name: "print_grand_divider", scopeLine: 138, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 146, name: "print_dots", scopeLine: 146, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 154, name: "print_test_line", scopeLine: 154, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 200, name: "print_test_pass", scopeLine: 200, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 242, name: "print_test_fail", scopeLine: 242, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 269, name: "print_test_crash", scopeLine: 269, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 297, name: "print_test_timeout", scopeLine: 297, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 322, name: "print_test_skip", scopeLine: 322, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 353, name: "print_suite_summary", scopeLine: 353, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 385, name: "print_grand_summary", scopeLine: 385, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 437, name: "print_divider", scopeLine: 437, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 440, name: "print_summary", scopeLine: 440, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!51 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!52 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!53 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!54 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!55 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!56 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!57 = !DILocalVariable(file: !0, line: 35, name: "fd", scope: !17, type: !10)
!58 = !DILocation(column: 1, line: 35, scope: !17)
!59 = !DILocation(column: 5, line: 36, scope: !17)
!60 = !DISubrange(count: 4)
!61 = !{ !60 }
!62 = !DICompositeType(baseType: !10, elements: !61, size: 128, tag: DW_TAG_array_type)
!63 = !DILocalVariable(file: !0, line: 36, name: "winsize", scope: !17, type: !62)
!64 = !DILocation(column: 1, line: 36, scope: !17)
!65 = !DILocation(column: 5, line: 37, scope: !17)
!66 = !DILocation(column: 5, line: 38, scope: !17)
!67 = !DILocalVariable(file: !0, line: 46, name: "mode", scope: !18, type: !10)
!68 = !DILocation(column: 1, line: 46, scope: !18)
!69 = !DILocation(column: 5, line: 47, scope: !18)
!70 = !DILocation(column: 5, line: 48, scope: !18)
!71 = !DILocation(column: 5, line: 51, scope: !19)
!72 = !DILocation(column: 9, line: 52, scope: !19)
!73 = !DILocation(column: 5, line: 53, scope: !19)
!74 = !DILocation(column: 5, line: 55, scope: !19)
!75 = !DILocation(column: 9, line: 56, scope: !19)
!76 = !DILocation(column: 9, line: 58, scope: !19)
!77 = !DILocation(column: 9, line: 60, scope: !19)
!78 = !DILocation(column: 5, line: 64, scope: !20)
!79 = !DILocation(column: 5, line: 65, scope: !20)
!80 = !DILocation(column: 5, line: 74, scope: !21)
!81 = !DISubrange(count: 2)
!82 = !{ !81 }
!83 = !DICompositeType(baseType: !12, elements: !82, size: 16, tag: DW_TAG_array_type)
!84 = !DILocalVariable(file: !0, line: 74, name: "buf", scope: !21, type: !83)
!85 = !DILocation(column: 1, line: 74, scope: !21)
!86 = !DILocation(column: 5, line: 75, scope: !21)
!87 = !DILocation(column: 5, line: 76, scope: !21)
!88 = !DILocation(column: 5, line: 77, scope: !21)
!89 = !DILocation(column: 5, line: 80, scope: !22)
!90 = !DILocation(column: 9, line: 81, scope: !22)
!91 = !DILocation(column: 5, line: 82, scope: !22)
!92 = !DILocation(column: 5, line: 83, scope: !22)
!93 = !DILocation(column: 5, line: 86, scope: !23)
!94 = !DILocation(column: 9, line: 87, scope: !23)
!95 = !DILocation(column: 5, line: 88, scope: !23)
!96 = !DILocation(column: 5, line: 89, scope: !23)
!97 = !DILocation(column: 5, line: 92, scope: !24)
!98 = !DILocation(column: 9, line: 93, scope: !24)
!99 = !DILocation(column: 5, line: 94, scope: !24)
!100 = !DILocation(column: 5, line: 95, scope: !24)
!101 = !DILocation(column: 5, line: 98, scope: !25)
!102 = !DILocation(column: 9, line: 99, scope: !25)
!103 = !DILocation(column: 5, line: 100, scope: !25)
!104 = !DILocation(column: 5, line: 101, scope: !25)
!105 = !DILocation(column: 5, line: 104, scope: !26)
!106 = !DILocation(column: 9, line: 105, scope: !26)
!107 = !DILocation(column: 5, line: 106, scope: !26)
!108 = !DILocation(column: 5, line: 107, scope: !26)
!109 = !DILocation(column: 5, line: 110, scope: !27)
!110 = !DILocation(column: 9, line: 111, scope: !27)
!111 = !DILocation(column: 5, line: 112, scope: !27)
!112 = !DILocation(column: 5, line: 113, scope: !27)
!113 = !DILocation(column: 5, line: 121, scope: !28)
!114 = !DILocation(column: 5, line: 122, scope: !28)
!115 = !DILocation(column: 5, line: 123, scope: !28)
!116 = !DILocation(column: 5, line: 124, scope: !28)
!117 = !DILocation(column: 5, line: 125, scope: !28)
!118 = !DILocation(column: 5, line: 126, scope: !28)
!119 = !DICompositeType(align: 64, file: !0, name: "StrView", size: 128, tag: DW_TAG_structure_type)
!120 = !DILocalVariable(file: !0, line: 129, name: "name", scope: !29, type: !119)
!121 = !DILocation(column: 1, line: 129, scope: !29)
!122 = !DILocation(column: 5, line: 130, scope: !29)
!123 = !DILocation(column: 5, line: 131, scope: !29)
!124 = !DILocation(column: 5, line: 135, scope: !30)
!125 = !DILocation(column: 5, line: 139, scope: !31)
!126 = !DILocalVariable(file: !0, line: 146, name: "count", scope: !32, type: !10)
!127 = !DILocation(column: 1, line: 146, scope: !32)
!128 = !DILocation(column: 5, line: 147, scope: !32)
!129 = !DILocalVariable(file: !0, line: 147, name: "i", scope: !32, type: !10)
!130 = !DILocation(column: 1, line: 147, scope: !32)
!131 = !DILocation(column: 5, line: 148, scope: !32)
!132 = !DILocation(column: 9, line: 149, scope: !32)
!133 = !DILocation(column: 9, line: 150, scope: !32)
!134 = !DILocalVariable(file: !0, line: 154, name: "name", scope: !33, type: !119)
!135 = !DILocation(column: 1, line: 154, scope: !33)
!136 = !DILocalVariable(file: !0, line: 154, name: "status", scope: !33, type: !119)
!137 = !DILocalVariable(file: !0, line: 154, name: "duration_ms", scope: !33, type: !11)
!138 = !DILocation(column: 5, line: 156, scope: !33)
!139 = !DILocation(column: 5, line: 157, scope: !33)
!140 = !DILocation(column: 5, line: 160, scope: !33)
!141 = !DILocation(column: 5, line: 163, scope: !33)
!142 = !DILocation(column: 5, line: 164, scope: !33)
!143 = !DILocation(column: 5, line: 169, scope: !33)
!144 = !DILocalVariable(file: !0, line: 169, name: "time_width", scope: !33, type: !10)
!145 = !DILocation(column: 1, line: 169, scope: !33)
!146 = !DILocation(column: 5, line: 170, scope: !33)
!147 = !DILocation(column: 9, line: 171, scope: !33)
!148 = !DILocation(column: 5, line: 172, scope: !33)
!149 = !DILocation(column: 9, line: 173, scope: !33)
!150 = !DILocation(column: 5, line: 174, scope: !33)
!151 = !DILocation(column: 9, line: 175, scope: !33)
!152 = !DILocation(column: 5, line: 176, scope: !33)
!153 = !DILocation(column: 9, line: 177, scope: !33)
!154 = !DILocation(column: 5, line: 179, scope: !33)
!155 = !DILocation(column: 5, line: 182, scope: !33)
!156 = !DILocalVariable(file: !0, line: 182, name: "dots", scope: !33, type: !10)
!157 = !DILocation(column: 1, line: 182, scope: !33)
!158 = !DILocation(column: 5, line: 183, scope: !33)
!159 = !DILocation(column: 9, line: 184, scope: !33)
!160 = !DILocation(column: 5, line: 186, scope: !33)
!161 = !DILocation(column: 5, line: 189, scope: !33)
!162 = !DILocation(column: 5, line: 190, scope: !33)
!163 = !DILocation(column: 5, line: 191, scope: !33)
!164 = !DILocation(column: 5, line: 192, scope: !33)
!165 = !DILocation(column: 5, line: 193, scope: !33)
!166 = !DILocalVariable(file: !0, line: 200, name: "name", scope: !34, type: !119)
!167 = !DILocation(column: 1, line: 200, scope: !34)
!168 = !DILocalVariable(file: !0, line: 200, name: "duration_ms", scope: !34, type: !11)
!169 = !DILocation(column: 5, line: 202, scope: !34)
!170 = !DILocation(column: 5, line: 205, scope: !34)
!171 = !DILocation(column: 5, line: 206, scope: !34)
!172 = !DILocation(column: 5, line: 207, scope: !34)
!173 = !DILocation(column: 5, line: 208, scope: !34)
!174 = !DILocation(column: 5, line: 211, scope: !34)
!175 = !DILocalVariable(file: !0, line: 211, name: "time_width", scope: !34, type: !10)
!176 = !DILocation(column: 1, line: 211, scope: !34)
!177 = !DILocation(column: 5, line: 212, scope: !34)
!178 = !DILocation(column: 9, line: 213, scope: !34)
!179 = !DILocation(column: 5, line: 214, scope: !34)
!180 = !DILocation(column: 9, line: 215, scope: !34)
!181 = !DILocation(column: 5, line: 216, scope: !34)
!182 = !DILocation(column: 9, line: 217, scope: !34)
!183 = !DILocation(column: 5, line: 218, scope: !34)
!184 = !DILocation(column: 9, line: 219, scope: !34)
!185 = !DILocation(column: 5, line: 221, scope: !34)
!186 = !DILocation(column: 5, line: 224, scope: !34)
!187 = !DILocalVariable(file: !0, line: 224, name: "dots", scope: !34, type: !10)
!188 = !DILocation(column: 1, line: 224, scope: !34)
!189 = !DILocation(column: 5, line: 225, scope: !34)
!190 = !DILocation(column: 9, line: 226, scope: !34)
!191 = !DILocation(column: 5, line: 228, scope: !34)
!192 = !DILocation(column: 5, line: 229, scope: !34)
!193 = !DILocation(column: 5, line: 230, scope: !34)
!194 = !DILocation(column: 5, line: 233, scope: !34)
!195 = !DILocation(column: 5, line: 234, scope: !34)
!196 = !DILocation(column: 5, line: 235, scope: !34)
!197 = !DILocation(column: 5, line: 236, scope: !34)
!198 = !DILocation(column: 5, line: 237, scope: !34)
!199 = !DILocation(column: 5, line: 238, scope: !34)
!200 = !DILocation(column: 5, line: 239, scope: !34)
!201 = !DILocalVariable(file: !0, line: 242, name: "name", scope: !35, type: !119)
!202 = !DILocation(column: 1, line: 242, scope: !35)
!203 = !DILocalVariable(file: !0, line: 242, name: "duration_ms", scope: !35, type: !11)
!204 = !DILocalVariable(file: !0, line: 242, name: "error_code", scope: !35, type: !10)
!205 = !DILocation(column: 5, line: 244, scope: !35)
!206 = !DILocation(column: 5, line: 246, scope: !35)
!207 = !DILocation(column: 5, line: 247, scope: !35)
!208 = !DILocation(column: 5, line: 248, scope: !35)
!209 = !DILocation(column: 5, line: 249, scope: !35)
!210 = !DILocalVariable(file: !0, line: 249, name: "dots", scope: !35, type: !10)
!211 = !DILocation(column: 1, line: 249, scope: !35)
!212 = !DILocation(column: 5, line: 250, scope: !35)
!213 = !DILocation(column: 9, line: 251, scope: !35)
!214 = !DILocation(column: 5, line: 253, scope: !35)
!215 = !DILocation(column: 5, line: 254, scope: !35)
!216 = !DILocation(column: 5, line: 255, scope: !35)
!217 = !DILocation(column: 5, line: 257, scope: !35)
!218 = !DILocation(column: 5, line: 258, scope: !35)
!219 = !DILocation(column: 5, line: 259, scope: !35)
!220 = !DILocation(column: 5, line: 260, scope: !35)
!221 = !DILocation(column: 5, line: 261, scope: !35)
!222 = !DILocation(column: 5, line: 262, scope: !35)
!223 = !DILocation(column: 5, line: 263, scope: !35)
!224 = !DILocation(column: 5, line: 264, scope: !35)
!225 = !DILocation(column: 5, line: 265, scope: !35)
!226 = !DILocation(column: 5, line: 266, scope: !35)
!227 = !DILocalVariable(file: !0, line: 269, name: "name", scope: !36, type: !119)
!228 = !DILocation(column: 1, line: 269, scope: !36)
!229 = !DILocalVariable(file: !0, line: 269, name: "duration_ms", scope: !36, type: !11)
!230 = !DILocalVariable(file: !0, line: 269, name: "signal", scope: !36, type: !10)
!231 = !DILocalVariable(file: !0, line: 269, name: "signal_name", scope: !36, type: !119)
!232 = !DILocation(column: 5, line: 271, scope: !36)
!233 = !DILocation(column: 5, line: 272, scope: !36)
!234 = !DILocation(column: 5, line: 274, scope: !36)
!235 = !DILocation(column: 5, line: 275, scope: !36)
!236 = !DILocation(column: 5, line: 276, scope: !36)
!237 = !DILocation(column: 5, line: 277, scope: !36)
!238 = !DILocalVariable(file: !0, line: 277, name: "dots", scope: !36, type: !10)
!239 = !DILocation(column: 1, line: 277, scope: !36)
!240 = !DILocation(column: 5, line: 278, scope: !36)
!241 = !DILocation(column: 9, line: 279, scope: !36)
!242 = !DILocation(column: 5, line: 281, scope: !36)
!243 = !DILocation(column: 5, line: 282, scope: !36)
!244 = !DILocation(column: 5, line: 283, scope: !36)
!245 = !DILocation(column: 5, line: 285, scope: !36)
!246 = !DILocation(column: 5, line: 286, scope: !36)
!247 = !DILocation(column: 5, line: 287, scope: !36)
!248 = !DILocation(column: 5, line: 288, scope: !36)
!249 = !DILocation(column: 5, line: 289, scope: !36)
!250 = !DILocation(column: 5, line: 290, scope: !36)
!251 = !DILocation(column: 5, line: 291, scope: !36)
!252 = !DILocation(column: 5, line: 292, scope: !36)
!253 = !DILocation(column: 5, line: 293, scope: !36)
!254 = !DILocation(column: 5, line: 294, scope: !36)
!255 = !DILocalVariable(file: !0, line: 297, name: "name", scope: !37, type: !119)
!256 = !DILocation(column: 1, line: 297, scope: !37)
!257 = !DILocalVariable(file: !0, line: 297, name: "timeout_ms", scope: !37, type: !11)
!258 = !DILocation(column: 5, line: 299, scope: !37)
!259 = !DILocation(column: 5, line: 301, scope: !37)
!260 = !DILocation(column: 5, line: 302, scope: !37)
!261 = !DILocation(column: 5, line: 303, scope: !37)
!262 = !DILocation(column: 5, line: 304, scope: !37)
!263 = !DILocalVariable(file: !0, line: 304, name: "dots", scope: !37, type: !10)
!264 = !DILocation(column: 1, line: 304, scope: !37)
!265 = !DILocation(column: 5, line: 305, scope: !37)
!266 = !DILocation(column: 9, line: 306, scope: !37)
!267 = !DILocation(column: 5, line: 308, scope: !37)
!268 = !DILocation(column: 5, line: 309, scope: !37)
!269 = !DILocation(column: 5, line: 310, scope: !37)
!270 = !DILocation(column: 5, line: 312, scope: !37)
!271 = !DILocation(column: 5, line: 313, scope: !37)
!272 = !DILocation(column: 5, line: 314, scope: !37)
!273 = !DILocation(column: 5, line: 315, scope: !37)
!274 = !DILocation(column: 5, line: 316, scope: !37)
!275 = !DILocation(column: 5, line: 317, scope: !37)
!276 = !DILocation(column: 5, line: 318, scope: !37)
!277 = !DILocation(column: 5, line: 319, scope: !37)
!278 = !DILocalVariable(file: !0, line: 322, name: "name", scope: !38, type: !119)
!279 = !DILocation(column: 1, line: 322, scope: !38)
!280 = !DILocalVariable(file: !0, line: 322, name: "reason", scope: !38, type: !119)
!281 = !DILocation(column: 5, line: 324, scope: !38)
!282 = !DILocation(column: 5, line: 325, scope: !38)
!283 = !DILocation(column: 5, line: 327, scope: !38)
!284 = !DILocation(column: 5, line: 328, scope: !38)
!285 = !DILocation(column: 5, line: 329, scope: !38)
!286 = !DILocation(column: 5, line: 330, scope: !38)
!287 = !DILocalVariable(file: !0, line: 330, name: "dots", scope: !38, type: !10)
!288 = !DILocation(column: 1, line: 330, scope: !38)
!289 = !DILocation(column: 5, line: 331, scope: !38)
!290 = !DILocation(column: 9, line: 332, scope: !38)
!291 = !DILocation(column: 5, line: 334, scope: !38)
!292 = !DILocation(column: 5, line: 335, scope: !38)
!293 = !DILocation(column: 5, line: 336, scope: !38)
!294 = !DILocation(column: 5, line: 338, scope: !38)
!295 = !DILocation(column: 5, line: 339, scope: !38)
!296 = !DILocation(column: 5, line: 340, scope: !38)
!297 = !DILocation(column: 5, line: 341, scope: !38)
!298 = !DILocation(column: 5, line: 342, scope: !38)
!299 = !DILocation(column: 9, line: 343, scope: !38)
!300 = !DILocation(column: 9, line: 344, scope: !38)
!301 = !DILocation(column: 5, line: 346, scope: !38)
!302 = !DILocalVariable(file: !0, line: 353, name: "total", scope: !39, type: !10)
!303 = !DILocation(column: 1, line: 353, scope: !39)
!304 = !DILocalVariable(file: !0, line: 353, name: "passed", scope: !39, type: !10)
!305 = !DILocalVariable(file: !0, line: 353, name: "failed", scope: !39, type: !10)
!306 = !DILocalVariable(file: !0, line: 353, name: "crashed", scope: !39, type: !10)
!307 = !DILocalVariable(file: !0, line: 353, name: "timeout", scope: !39, type: !10)
!308 = !DILocalVariable(file: !0, line: 353, name: "duration_ms", scope: !39, type: !11)
!309 = !DILocation(column: 5, line: 354, scope: !39)
!310 = !DILocation(column: 5, line: 355, scope: !39)
!311 = !DILocation(column: 5, line: 356, scope: !39)
!312 = !DILocation(column: 5, line: 357, scope: !39)
!313 = !DILocation(column: 5, line: 358, scope: !39)
!314 = !DILocation(column: 5, line: 360, scope: !39)
!315 = !DILocation(column: 9, line: 361, scope: !39)
!316 = !DILocation(column: 9, line: 362, scope: !39)
!317 = !DILocation(column: 5, line: 365, scope: !39)
!318 = !DILocation(column: 9, line: 366, scope: !39)
!319 = !DILocation(column: 9, line: 367, scope: !39)
!320 = !DILocation(column: 5, line: 370, scope: !39)
!321 = !DILocation(column: 9, line: 371, scope: !39)
!322 = !DILocation(column: 9, line: 372, scope: !39)
!323 = !DILocation(column: 5, line: 376, scope: !39)
!324 = !DILocation(column: 5, line: 377, scope: !39)
!325 = !DILocation(column: 5, line: 378, scope: !39)
!326 = !DILocalVariable(file: !0, line: 385, name: "total", scope: !40, type: !10)
!327 = !DILocation(column: 1, line: 385, scope: !40)
!328 = !DILocalVariable(file: !0, line: 385, name: "passed", scope: !40, type: !10)
!329 = !DILocalVariable(file: !0, line: 385, name: "failed", scope: !40, type: !10)
!330 = !DILocalVariable(file: !0, line: 385, name: "crashed", scope: !40, type: !10)
!331 = !DILocalVariable(file: !0, line: 385, name: "timeout", scope: !40, type: !10)
!332 = !DILocalVariable(file: !0, line: 385, name: "skipped", scope: !40, type: !10)
!333 = !DILocalVariable(file: !0, line: 385, name: "duration_ms", scope: !40, type: !11)
!334 = !DILocation(column: 5, line: 386, scope: !40)
!335 = !DILocation(column: 5, line: 388, scope: !40)
!336 = !DILocation(column: 5, line: 389, scope: !40)
!337 = !DILocation(column: 5, line: 390, scope: !40)
!338 = !DILocation(column: 5, line: 391, scope: !40)
!339 = !DILocation(column: 5, line: 392, scope: !40)
!340 = !DILocation(column: 5, line: 394, scope: !40)
!341 = !DILocation(column: 5, line: 395, scope: !40)
!342 = !DILocation(column: 5, line: 396, scope: !40)
!343 = !DILocation(column: 5, line: 397, scope: !40)
!344 = !DILocation(column: 5, line: 398, scope: !40)
!345 = !DILocation(column: 5, line: 400, scope: !40)
!346 = !DILocation(column: 9, line: 401, scope: !40)
!347 = !DILocation(column: 9, line: 402, scope: !40)
!348 = !DILocation(column: 9, line: 403, scope: !40)
!349 = !DILocation(column: 9, line: 404, scope: !40)
!350 = !DILocation(column: 5, line: 407, scope: !40)
!351 = !DILocation(column: 9, line: 408, scope: !40)
!352 = !DILocation(column: 9, line: 409, scope: !40)
!353 = !DILocation(column: 9, line: 410, scope: !40)
!354 = !DILocation(column: 9, line: 411, scope: !40)
!355 = !DILocation(column: 5, line: 414, scope: !40)
!356 = !DILocation(column: 9, line: 415, scope: !40)
!357 = !DILocation(column: 9, line: 416, scope: !40)
!358 = !DILocation(column: 9, line: 417, scope: !40)
!359 = !DILocation(column: 9, line: 418, scope: !40)
!360 = !DILocation(column: 5, line: 421, scope: !40)
!361 = !DILocation(column: 9, line: 422, scope: !40)
!362 = !DILocation(column: 9, line: 423, scope: !40)
!363 = !DILocation(column: 9, line: 424, scope: !40)
!364 = !DILocation(column: 9, line: 425, scope: !40)
!365 = !DILocation(column: 5, line: 428, scope: !40)
!366 = !DILocation(column: 5, line: 429, scope: !40)
!367 = !DILocation(column: 5, line: 430, scope: !40)
!368 = !DILocation(column: 5, line: 431, scope: !40)
!369 = !DILocation(column: 5, line: 438, scope: !41)
!370 = !DILocalVariable(file: !0, line: 440, name: "passed", scope: !42, type: !10)
!371 = !DILocation(column: 1, line: 440, scope: !42)
!372 = !DILocalVariable(file: !0, line: 440, name: "failed", scope: !42, type: !10)
!373 = !DILocalVariable(file: !0, line: 440, name: "skipped", scope: !42, type: !10)
!374 = !DILocalVariable(file: !0, line: 440, name: "duration_ms", scope: !42, type: !11)
!375 = !DILocation(column: 5, line: 441, scope: !42)
!376 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!377 = !DIDerivedType(baseType: !376, size: 64, tag: DW_TAG_reference_type)
!378 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !43, type: !377)
!379 = !DILocation(column: 1, line: 219, scope: !43)
!380 = !DILocation(column: 5, line: 220, scope: !43)
!381 = !DILocation(column: 5, line: 221, scope: !43)
!382 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !44, type: !377)
!383 = !DILocation(column: 1, line: 210, scope: !44)
!384 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !44, type: !12)
!385 = !DILocation(column: 5, line: 211, scope: !44)
!386 = !DILocation(column: 9, line: 212, scope: !44)
!387 = !DILocation(column: 5, line: 213, scope: !44)
!388 = !DILocation(column: 5, line: 214, scope: !44)
!389 = !DILocation(column: 5, line: 215, scope: !44)
!390 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !45, type: !377)
!391 = !DILocation(column: 1, line: 148, scope: !45)
!392 = !DILocation(column: 5, line: 149, scope: !45)
!393 = !DILocation(column: 5, line: 151, scope: !45)
!394 = !DILocation(column: 5, line: 152, scope: !45)
!395 = !DILocation(column: 5, line: 153, scope: !45)
!396 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !46, type: !11)
!397 = !DILocation(column: 1, line: 124, scope: !46)
!398 = !DILocation(column: 5, line: 125, scope: !46)
!399 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !46, type: !376)
!400 = !DILocation(column: 1, line: 125, scope: !46)
!401 = !DILocation(column: 5, line: 126, scope: !46)
!402 = !DILocation(column: 9, line: 127, scope: !46)
!403 = !DILocation(column: 9, line: 128, scope: !46)
!404 = !DILocation(column: 9, line: 129, scope: !46)
!405 = !DILocation(column: 9, line: 130, scope: !46)
!406 = !DILocation(column: 5, line: 132, scope: !46)
!407 = !DILocation(column: 5, line: 133, scope: !46)
!408 = !DILocation(column: 5, line: 134, scope: !46)
!409 = !DILocation(column: 9, line: 135, scope: !46)
!410 = !DILocation(column: 9, line: 136, scope: !46)
!411 = !DILocation(column: 9, line: 137, scope: !46)
!412 = !DILocation(column: 5, line: 139, scope: !46)
!413 = !DILocation(column: 5, line: 140, scope: !46)
!414 = !DILocation(column: 5, line: 141, scope: !46)
!415 = !DILocation(column: 5, line: 117, scope: !47)
!416 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !47, type: !376)
!417 = !DILocation(column: 1, line: 117, scope: !47)
!418 = !DILocation(column: 5, line: 118, scope: !47)
!419 = !DILocation(column: 5, line: 119, scope: !47)
!420 = !DILocation(column: 5, line: 120, scope: !47)
!421 = !DILocation(column: 5, line: 121, scope: !47)
!422 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!423 = !DIDerivedType(baseType: !422, size: 64, tag: DW_TAG_reference_type)
!424 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !48, type: !423)
!425 = !DILocation(column: 1, line: 210, scope: !48)
!426 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!427 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !48, type: !426)
!428 = !DILocation(column: 5, line: 211, scope: !48)
!429 = !DILocation(column: 9, line: 212, scope: !48)
!430 = !DILocation(column: 5, line: 213, scope: !48)
!431 = !DILocation(column: 5, line: 214, scope: !48)
!432 = !DILocation(column: 5, line: 215, scope: !48)
!433 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !49, type: !377)
!434 = !DILocation(column: 1, line: 288, scope: !49)
!435 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!436 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !49, type: !435)
!437 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !49, type: !11)
!438 = !DILocation(column: 5, line: 289, scope: !49)
!439 = !DILocation(column: 13, line: 291, scope: !49)
!440 = !DILocation(column: 5, line: 292, scope: !49)
!441 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !50, type: !377)
!442 = !DILocation(column: 1, line: 193, scope: !50)
!443 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !50, type: !11)
!444 = !DILocation(column: 5, line: 194, scope: !50)
!445 = !DILocation(column: 9, line: 195, scope: !50)
!446 = !DILocation(column: 5, line: 197, scope: !50)
!447 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !50, type: !11)
!448 = !DILocation(column: 1, line: 197, scope: !50)
!449 = !DILocation(column: 5, line: 198, scope: !50)
!450 = !DILocation(column: 9, line: 199, scope: !50)
!451 = !DILocation(column: 5, line: 200, scope: !50)
!452 = !DILocation(column: 9, line: 201, scope: !50)
!453 = !DILocation(column: 5, line: 203, scope: !50)
!454 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !51, type: !377)
!455 = !DILocation(column: 1, line: 235, scope: !51)
!456 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !51, type: !11)
!457 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !51, type: !12)
!458 = !DILocation(column: 5, line: 236, scope: !51)
!459 = !DILocation(column: 5, line: 237, scope: !51)
!460 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !52, type: !377)
!461 = !DILocation(column: 1, line: 225, scope: !52)
!462 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !52, type: !11)
!463 = !DILocation(column: 5, line: 226, scope: !52)
!464 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !53, type: !377)
!465 = !DILocation(column: 1, line: 244, scope: !53)
!466 = !DILocation(column: 5, line: 245, scope: !53)
!467 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !54, type: !377)
!468 = !DILocation(column: 1, line: 179, scope: !54)
!469 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !54, type: !11)
!470 = !DILocation(column: 5, line: 180, scope: !54)
!471 = !DILocation(column: 9, line: 181, scope: !54)
!472 = !DILocation(column: 5, line: 183, scope: !54)
!473 = !DILocation(column: 5, line: 184, scope: !54)
!474 = !DILocation(column: 5, line: 185, scope: !54)
!475 = !DILocation(column: 9, line: 186, scope: !54)
!476 = !DILocation(column: 5, line: 188, scope: !54)
!477 = !DILocation(column: 5, line: 189, scope: !54)
!478 = !DILocation(column: 5, line: 190, scope: !54)
!479 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !55, type: !423)
!480 = !DILocation(column: 1, line: 193, scope: !55)
!481 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !55, type: !11)
!482 = !DILocation(column: 5, line: 194, scope: !55)
!483 = !DILocation(column: 9, line: 195, scope: !55)
!484 = !DILocation(column: 5, line: 197, scope: !55)
!485 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !55, type: !11)
!486 = !DILocation(column: 1, line: 197, scope: !55)
!487 = !DILocation(column: 5, line: 198, scope: !55)
!488 = !DILocation(column: 9, line: 199, scope: !55)
!489 = !DILocation(column: 5, line: 200, scope: !55)
!490 = !DILocation(column: 9, line: 201, scope: !55)
!491 = !DILocation(column: 5, line: 203, scope: !55)
!492 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !56, type: !423)
!493 = !DILocation(column: 1, line: 179, scope: !56)
!494 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !56, type: !11)
!495 = !DILocation(column: 5, line: 180, scope: !56)
!496 = !DILocation(column: 9, line: 181, scope: !56)
!497 = !DILocation(column: 5, line: 183, scope: !56)
!498 = !DILocation(column: 5, line: 184, scope: !56)
!499 = !DILocation(column: 5, line: 185, scope: !56)
!500 = !DILocation(column: 9, line: 186, scope: !56)
!501 = !DILocation(column: 5, line: 188, scope: !56)
!502 = !DILocation(column: 5, line: 189, scope: !56)
!503 = !DILocation(column: 5, line: 190, scope: !56)