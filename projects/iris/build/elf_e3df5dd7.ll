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
%"struct.ritz_module_1.Elf64_Ehdr" = type {[16 x i8], i16, i16, i32, i64, i64, i64, i32, i16, i16, i16, i16, i16, i16}
%"struct.ritz_module_1.Elf64_Shdr" = type {i32, i32, i64, i64, i64, i64, i32, i32, i64, i64}
%"struct.ritz_module_1.Elf64_Sym" = type {i32, i8, i8, i16, i64, i64}
%"struct.ritz_module_1.ElfReader" = type {i8*, i64, %"struct.ritz_module_1.Elf64_Ehdr"*, %"struct.ritz_module_1.Elf64_Shdr"*, %"struct.ritz_module_1.Elf64_Sym"*, i64, i8*}
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

define i32 @"elf_init"(%"struct.ritz_module_1.ElfReader"* %"reader.arg", i8* %"data.arg", i64 %"size.arg") !dbg !17
{
entry:
  %"reader" = alloca %"struct.ritz_module_1.ElfReader"*
  store %"struct.ritz_module_1.ElfReader"* %"reader.arg", %"struct.ritz_module_1.ElfReader"** %"reader"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ElfReader"** %"reader", metadata !46, metadata !7), !dbg !47
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !49, metadata !7), !dbg !47
  %"size" = alloca i64
  store i64 %"size.arg", i64* %"size"
  call void @"llvm.dbg.declare"(metadata i64* %"size", metadata !50, metadata !7), !dbg !47
  %".11" = load i8*, i8** %"data", !dbg !51
  %".12" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !51
  %".13" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".12", i32 0, i32 0 , !dbg !51
  store i8* %".11", i8** %".13", !dbg !51
  %".15" = load i64, i64* %"size", !dbg !52
  %".16" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !52
  %".17" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".16", i32 0, i32 1 , !dbg !52
  store i64 %".15", i64* %".17", !dbg !52
  %".19" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !53
  %".20" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".19", i32 0, i32 2 , !dbg !53
  %".21" = bitcast i8* null to %"struct.ritz_module_1.Elf64_Ehdr"* , !dbg !53
  store %"struct.ritz_module_1.Elf64_Ehdr"* %".21", %"struct.ritz_module_1.Elf64_Ehdr"** %".20", !dbg !53
  %".23" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !54
  %".24" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".23", i32 0, i32 3 , !dbg !54
  %".25" = bitcast i8* null to %"struct.ritz_module_1.Elf64_Shdr"* , !dbg !54
  store %"struct.ritz_module_1.Elf64_Shdr"* %".25", %"struct.ritz_module_1.Elf64_Shdr"** %".24", !dbg !54
  %".27" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !55
  %".28" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".27", i32 0, i32 4 , !dbg !55
  %".29" = bitcast i8* null to %"struct.ritz_module_1.Elf64_Sym"* , !dbg !55
  store %"struct.ritz_module_1.Elf64_Sym"* %".29", %"struct.ritz_module_1.Elf64_Sym"** %".28", !dbg !55
  %".31" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !56
  %".32" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".31", i32 0, i32 5 , !dbg !56
  store i64 0, i64* %".32", !dbg !56
  %".34" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !57
  %".35" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".34", i32 0, i32 6 , !dbg !57
  store i8* null, i8** %".35", !dbg !57
  %".37" = load i64, i64* %"size", !dbg !58
  %".38" = icmp slt i64 %".37", 64 , !dbg !58
  br i1 %".38", label %"if.then", label %"if.end", !dbg !58
if.then:
  %".40" = sub i64 0, 1, !dbg !59
  %".41" = trunc i64 %".40" to i32 , !dbg !59
  ret i32 %".41", !dbg !59
if.end:
  %".43" = load i8*, i8** %"data", !dbg !60
  %".44" = load i8, i8* %".43", !dbg !60
  %".45" = icmp ne i8 %".44", 127 , !dbg !60
  br i1 %".45", label %"if.then.1", label %"if.end.1", !dbg !60
if.then.1:
  %".47" = sub i64 0, 1, !dbg !61
  %".48" = trunc i64 %".47" to i32 , !dbg !61
  ret i32 %".48", !dbg !61
if.end.1:
  %".50" = load i8*, i8** %"data", !dbg !62
  %".51" = getelementptr i8, i8* %".50", i64 1 , !dbg !62
  %".52" = load i8, i8* %".51", !dbg !62
  %".53" = icmp ne i8 %".52", 69 , !dbg !62
  br i1 %".53", label %"if.then.2", label %"if.end.2", !dbg !62
if.then.2:
  %".55" = sub i64 0, 1, !dbg !63
  %".56" = trunc i64 %".55" to i32 , !dbg !63
  ret i32 %".56", !dbg !63
if.end.2:
  %".58" = load i8*, i8** %"data", !dbg !64
  %".59" = getelementptr i8, i8* %".58", i64 2 , !dbg !64
  %".60" = load i8, i8* %".59", !dbg !64
  %".61" = icmp ne i8 %".60", 76 , !dbg !64
  br i1 %".61", label %"if.then.3", label %"if.end.3", !dbg !64
if.then.3:
  %".63" = sub i64 0, 1, !dbg !65
  %".64" = trunc i64 %".63" to i32 , !dbg !65
  ret i32 %".64", !dbg !65
if.end.3:
  %".66" = load i8*, i8** %"data", !dbg !66
  %".67" = getelementptr i8, i8* %".66", i64 3 , !dbg !66
  %".68" = load i8, i8* %".67", !dbg !66
  %".69" = icmp ne i8 %".68", 70 , !dbg !66
  br i1 %".69", label %"if.then.4", label %"if.end.4", !dbg !66
if.then.4:
  %".71" = sub i64 0, 1, !dbg !67
  %".72" = trunc i64 %".71" to i32 , !dbg !67
  ret i32 %".72", !dbg !67
if.end.4:
  %".74" = load i8*, i8** %"data", !dbg !68
  %".75" = getelementptr i8, i8* %".74", i64 4 , !dbg !68
  %".76" = load i8, i8* %".75", !dbg !68
  %".77" = icmp ne i8 %".76", 2 , !dbg !68
  br i1 %".77", label %"if.then.5", label %"if.end.5", !dbg !68
if.then.5:
  %".79" = sub i64 0, 1, !dbg !69
  %".80" = trunc i64 %".79" to i32 , !dbg !69
  ret i32 %".80", !dbg !69
if.end.5:
  %".82" = load i8*, i8** %"data", !dbg !70
  %".83" = getelementptr i8, i8* %".82", i64 5 , !dbg !70
  %".84" = load i8, i8* %".83", !dbg !70
  %".85" = icmp ne i8 %".84", 1 , !dbg !70
  br i1 %".85", label %"if.then.6", label %"if.end.6", !dbg !70
if.then.6:
  %".87" = sub i64 0, 1, !dbg !71
  %".88" = trunc i64 %".87" to i32 , !dbg !71
  ret i32 %".88", !dbg !71
if.end.6:
  %".90" = load i8*, i8** %"data", !dbg !72
  %".91" = bitcast i8* %".90" to %"struct.ritz_module_1.Elf64_Ehdr"* , !dbg !72
  %".92" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !72
  %".93" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".92", i32 0, i32 2 , !dbg !72
  store %"struct.ritz_module_1.Elf64_Ehdr"* %".91", %"struct.ritz_module_1.Elf64_Ehdr"** %".93", !dbg !72
  %".95" = trunc i64 0 to i32 , !dbg !73
  ret i32 %".95", !dbg !73
}

define i32 @"read_u16"(i8* %"ptr.arg") !dbg !18
{
entry:
  %"ptr" = alloca i8*
  store i8* %"ptr.arg", i8** %"ptr"
  call void @"llvm.dbg.declare"(metadata i8** %"ptr", metadata !74, metadata !7), !dbg !75
  %".5" = load i8*, i8** %"ptr", !dbg !76
  %".6" = load i8, i8* %".5", !dbg !76
  %".7" = zext i8 %".6" to i32 , !dbg !76
  %".8" = load i8*, i8** %"ptr", !dbg !77
  %".9" = getelementptr i8, i8* %".8", i64 1 , !dbg !77
  %".10" = load i8, i8* %".9", !dbg !77
  %".11" = zext i8 %".10" to i32 , !dbg !77
  %".12" = sext i32 %".11" to i64 , !dbg !78
  %".13" = shl i64 %".12", 8, !dbg !78
  %".14" = sext i32 %".7" to i64 , !dbg !78
  %".15" = add i64 %".14", %".13", !dbg !78
  %".16" = trunc i64 %".15" to i32 , !dbg !78
  ret i32 %".16", !dbg !78
}

define i32 @"read_u32"(i8* %"ptr.arg") !dbg !19
{
entry:
  %"ptr" = alloca i8*
  store i8* %"ptr.arg", i8** %"ptr"
  call void @"llvm.dbg.declare"(metadata i8** %"ptr", metadata !79, metadata !7), !dbg !80
  %".5" = load i8*, i8** %"ptr", !dbg !81
  %".6" = load i8, i8* %".5", !dbg !81
  %".7" = zext i8 %".6" to i32 , !dbg !81
  %".8" = load i8*, i8** %"ptr", !dbg !82
  %".9" = getelementptr i8, i8* %".8", i64 1 , !dbg !82
  %".10" = load i8, i8* %".9", !dbg !82
  %".11" = zext i8 %".10" to i32 , !dbg !82
  %".12" = load i8*, i8** %"ptr", !dbg !83
  %".13" = getelementptr i8, i8* %".12", i64 2 , !dbg !83
  %".14" = load i8, i8* %".13", !dbg !83
  %".15" = zext i8 %".14" to i32 , !dbg !83
  %".16" = load i8*, i8** %"ptr", !dbg !84
  %".17" = getelementptr i8, i8* %".16", i64 3 , !dbg !84
  %".18" = load i8, i8* %".17", !dbg !84
  %".19" = zext i8 %".18" to i32 , !dbg !84
  %".20" = sext i32 %".11" to i64 , !dbg !85
  %".21" = shl i64 %".20", 8, !dbg !85
  %".22" = sext i32 %".7" to i64 , !dbg !85
  %".23" = add i64 %".22", %".21", !dbg !85
  %".24" = sext i32 %".15" to i64 , !dbg !85
  %".25" = shl i64 %".24", 16, !dbg !85
  %".26" = add i64 %".23", %".25", !dbg !85
  %".27" = sext i32 %".19" to i64 , !dbg !85
  %".28" = shl i64 %".27", 24, !dbg !85
  %".29" = add i64 %".26", %".28", !dbg !85
  %".30" = trunc i64 %".29" to i32 , !dbg !85
  ret i32 %".30", !dbg !85
}

define i64 @"read_u64"(i8* %"ptr.arg") !dbg !20
{
entry:
  %"ptr" = alloca i8*
  store i8* %"ptr.arg", i8** %"ptr"
  call void @"llvm.dbg.declare"(metadata i8** %"ptr", metadata !86, metadata !7), !dbg !87
  %".5" = load i8*, i8** %"ptr", !dbg !88
  %".6" = call i32 @"read_u32"(i8* %".5"), !dbg !88
  %".7" = sext i32 %".6" to i64 , !dbg !88
  %".8" = load i8*, i8** %"ptr", !dbg !89
  %".9" = getelementptr i8, i8* %".8", i64 4 , !dbg !89
  %".10" = call i32 @"read_u32"(i8* %".9"), !dbg !89
  %".11" = sext i32 %".10" to i64 , !dbg !89
  %".12" = and i64 %".7", 4294967295, !dbg !90
  %".13" = and i64 %".11", 4294967295, !dbg !90
  %".14" = shl i64 %".13", 32, !dbg !90
  %".15" = add i64 %".12", %".14", !dbg !90
  ret i64 %".15", !dbg !90
}

define i32 @"elf_parse_sections"(%"struct.ritz_module_1.ElfReader"* %"reader.arg") !dbg !21
{
entry:
  %"reader" = alloca %"struct.ritz_module_1.ElfReader"*
  %"i" = alloca i32, !dbg !104
  store %"struct.ritz_module_1.ElfReader"* %"reader.arg", %"struct.ritz_module_1.ElfReader"** %"reader"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ElfReader"** %"reader", metadata !91, metadata !7), !dbg !92
  %".5" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !93
  %".6" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".5", i32 0, i32 2 , !dbg !93
  %".7" = load %"struct.ritz_module_1.Elf64_Ehdr"*, %"struct.ritz_module_1.Elf64_Ehdr"** %".6", !dbg !93
  %".8" = icmp eq %"struct.ritz_module_1.Elf64_Ehdr"* %".7", null , !dbg !94
  br i1 %".8", label %"if.then", label %"if.end", !dbg !94
if.then:
  %".10" = sub i64 0, 1, !dbg !95
  %".11" = trunc i64 %".10" to i32 , !dbg !95
  ret i32 %".11", !dbg !95
if.end:
  %".13" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !96
  %".14" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".13", i32 0, i32 0 , !dbg !96
  %".15" = load i8*, i8** %".14", !dbg !96
  %".16" = getelementptr i8, i8* %".15", i64 40 , !dbg !97
  %".17" = call i64 @"read_u64"(i8* %".16"), !dbg !97
  %".18" = getelementptr i8, i8* %".15", i64 58 , !dbg !98
  %".19" = call i32 @"read_u16"(i8* %".18"), !dbg !98
  %".20" = getelementptr i8, i8* %".15", i64 60 , !dbg !99
  %".21" = call i32 @"read_u16"(i8* %".20"), !dbg !99
  %".22" = getelementptr i8, i8* %".15", i64 62 , !dbg !100
  %".23" = call i32 @"read_u16"(i8* %".22"), !dbg !100
  %".24" = icmp eq i64 %".17", 0 , !dbg !101
  br i1 %".24", label %"or.merge", label %"or.right", !dbg !101
or.right:
  %".26" = sext i32 %".21" to i64 , !dbg !101
  %".27" = icmp eq i64 %".26", 0 , !dbg !101
  br label %"or.merge", !dbg !101
or.merge:
  %".29" = phi  i1 [1, %"if.end"], [%".27", %"or.right"] , !dbg !101
  br i1 %".29", label %"if.then.1", label %"if.end.1", !dbg !101
if.then.1:
  %".31" = sub i64 0, 1, !dbg !102
  %".32" = trunc i64 %".31" to i32 , !dbg !102
  ret i32 %".32", !dbg !102
if.end.1:
  %".34" = getelementptr i8, i8* %".15", i64 %".17" , !dbg !103
  %".35" = bitcast i8* %".34" to %"struct.ritz_module_1.Elf64_Shdr"* , !dbg !103
  %".36" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !103
  %".37" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".36", i32 0, i32 3 , !dbg !103
  store %"struct.ritz_module_1.Elf64_Shdr"* %".35", %"struct.ritz_module_1.Elf64_Shdr"** %".37", !dbg !103
  store i32 0, i32* %"i", !dbg !104
  br label %"for.cond", !dbg !104
for.cond:
  %".41" = load i32, i32* %"i", !dbg !104
  %".42" = icmp slt i32 %".41", %".21" , !dbg !104
  br i1 %".42", label %"for.body", label %"for.end", !dbg !104
for.body:
  %".44" = getelementptr i8, i8* %".15", i64 %".17" , !dbg !105
  %".45" = load i32, i32* %"i", !dbg !105
  %".46" = sext i32 %".45" to i64 , !dbg !105
  %".47" = sext i32 %".19" to i64 , !dbg !105
  %".48" = mul i64 %".46", %".47", !dbg !105
  %".49" = getelementptr i8, i8* %".44", i64 %".48" , !dbg !105
  %".50" = getelementptr i8, i8* %".49", i64 4 , !dbg !106
  %".51" = call i32 @"read_u32"(i8* %".50"), !dbg !106
  %".52" = icmp eq i32 %".51", 2 , !dbg !106
  br i1 %".52", label %"if.then.2", label %"if.end.2", !dbg !106
for.incr:
  %".87" = load i32, i32* %"i", !dbg !116
  %".88" = add i32 %".87", 1, !dbg !116
  store i32 %".88", i32* %"i", !dbg !116
  br label %"for.cond", !dbg !116
for.end:
  %".91" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !117
  %".92" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".91", i32 0, i32 4 , !dbg !117
  %".93" = load %"struct.ritz_module_1.Elf64_Sym"*, %"struct.ritz_module_1.Elf64_Sym"** %".92", !dbg !117
  %".94" = icmp eq %"struct.ritz_module_1.Elf64_Sym"* %".93", null , !dbg !117
  br i1 %".94", label %"if.then.4", label %"if.end.4", !dbg !117
if.then.2:
  %".54" = getelementptr i8, i8* %".49", i64 24 , !dbg !107
  %".55" = call i64 @"read_u64"(i8* %".54"), !dbg !107
  %".56" = getelementptr i8, i8* %".49", i64 32 , !dbg !108
  %".57" = call i64 @"read_u64"(i8* %".56"), !dbg !108
  %".58" = getelementptr i8, i8* %".49", i64 56 , !dbg !109
  %".59" = call i64 @"read_u64"(i8* %".58"), !dbg !109
  %".60" = getelementptr i8, i8* %".49", i64 40 , !dbg !110
  %".61" = call i32 @"read_u32"(i8* %".60"), !dbg !110
  %".62" = getelementptr i8, i8* %".15", i64 %".55" , !dbg !111
  %".63" = bitcast i8* %".62" to %"struct.ritz_module_1.Elf64_Sym"* , !dbg !111
  %".64" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !111
  %".65" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".64", i32 0, i32 4 , !dbg !111
  store %"struct.ritz_module_1.Elf64_Sym"* %".63", %"struct.ritz_module_1.Elf64_Sym"** %".65", !dbg !111
  %".67" = icmp sgt i64 %".59", 0 , !dbg !112
  br i1 %".67", label %"if.then.3", label %"if.end.3", !dbg !112
if.end.2:
  br label %"for.incr", !dbg !116
if.then.3:
  %".69" = sdiv i64 %".57", %".59", !dbg !113
  %".70" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !113
  %".71" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".70", i32 0, i32 5 , !dbg !113
  store i64 %".69", i64* %".71", !dbg !113
  br label %"if.end.3", !dbg !113
if.end.3:
  %".74" = getelementptr i8, i8* %".15", i64 %".17" , !dbg !114
  %".75" = sext i32 %".61" to i64 , !dbg !114
  %".76" = sext i32 %".19" to i64 , !dbg !114
  %".77" = mul i64 %".75", %".76", !dbg !114
  %".78" = getelementptr i8, i8* %".74", i64 %".77" , !dbg !114
  %".79" = getelementptr i8, i8* %".78", i64 24 , !dbg !115
  %".80" = call i64 @"read_u64"(i8* %".79"), !dbg !115
  %".81" = getelementptr i8, i8* %".15", i64 %".80" , !dbg !116
  %".82" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !116
  %".83" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".82", i32 0, i32 6 , !dbg !116
  store i8* %".81", i8** %".83", !dbg !116
  br label %"if.end.2", !dbg !116
if.then.4:
  %".96" = sub i64 0, 1, !dbg !118
  %".97" = trunc i64 %".96" to i32 , !dbg !118
  ret i32 %".97", !dbg !118
if.end.4:
  %".99" = trunc i64 0 to i32 , !dbg !119
  ret i32 %".99", !dbg !119
}

define i8* @"elf_get_symbol_name"(%"struct.ritz_module_1.ElfReader"* %"reader.arg", i64 %"sym_index.arg") !dbg !22
{
entry:
  %"reader" = alloca %"struct.ritz_module_1.ElfReader"*
  store %"struct.ritz_module_1.ElfReader"* %"reader.arg", %"struct.ritz_module_1.ElfReader"** %"reader"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ElfReader"** %"reader", metadata !120, metadata !7), !dbg !121
  %"sym_index" = alloca i64
  store i64 %"sym_index.arg", i64* %"sym_index"
  call void @"llvm.dbg.declare"(metadata i64* %"sym_index", metadata !122, metadata !7), !dbg !121
  %".8" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !123
  %".9" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".8", i32 0, i32 4 , !dbg !123
  %".10" = load %"struct.ritz_module_1.Elf64_Sym"*, %"struct.ritz_module_1.Elf64_Sym"** %".9", !dbg !123
  %".11" = icmp eq %"struct.ritz_module_1.Elf64_Sym"* %".10", null , !dbg !123
  br i1 %".11", label %"or.merge", label %"or.right", !dbg !123
or.right:
  %".13" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !123
  %".14" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".13", i32 0, i32 6 , !dbg !123
  %".15" = load i8*, i8** %".14", !dbg !123
  %".16" = icmp eq i8* %".15", null , !dbg !123
  br label %"or.merge", !dbg !123
or.merge:
  %".18" = phi  i1 [1, %"entry"], [%".16", %"or.right"] , !dbg !123
  br i1 %".18", label %"if.then", label %"if.end", !dbg !123
if.then:
  ret i8* null, !dbg !124
if.end:
  %".21" = load i64, i64* %"sym_index", !dbg !125
  %".22" = icmp slt i64 %".21", 0 , !dbg !125
  br i1 %".22", label %"or.merge.1", label %"or.right.1", !dbg !125
or.right.1:
  %".24" = load i64, i64* %"sym_index", !dbg !125
  %".25" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !125
  %".26" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".25", i32 0, i32 5 , !dbg !125
  %".27" = load i64, i64* %".26", !dbg !125
  %".28" = icmp sge i64 %".24", %".27" , !dbg !125
  br label %"or.merge.1", !dbg !125
or.merge.1:
  %".30" = phi  i1 [1, %"if.end"], [%".28", %"or.right.1"] , !dbg !125
  br i1 %".30", label %"if.then.1", label %"if.end.1", !dbg !125
if.then.1:
  ret i8* null, !dbg !126
if.end.1:
  %".33" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !127
  %".34" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".33", i32 0, i32 4 , !dbg !127
  %".35" = load %"struct.ritz_module_1.Elf64_Sym"*, %"struct.ritz_module_1.Elf64_Sym"** %".34", !dbg !127
  %".36" = bitcast %"struct.ritz_module_1.Elf64_Sym"* %".35" to i8* , !dbg !127
  %".37" = load i64, i64* %"sym_index", !dbg !127
  %".38" = mul i64 %".37", 24, !dbg !127
  %".39" = getelementptr i8, i8* %".36", i64 %".38" , !dbg !127
  %".40" = call i32 @"read_u32"(i8* %".39"), !dbg !128
  %".41" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !129
  %".42" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".41", i32 0, i32 6 , !dbg !129
  %".43" = load i8*, i8** %".42", !dbg !129
  %".44" = getelementptr i8, i8* %".43", i32 %".40" , !dbg !129
  ret i8* %".44", !dbg !129
}

define i8 @"elf_get_symbol_info"(%"struct.ritz_module_1.ElfReader"* %"reader.arg", i64 %"sym_index.arg") !dbg !23
{
entry:
  %"reader" = alloca %"struct.ritz_module_1.ElfReader"*
  store %"struct.ritz_module_1.ElfReader"* %"reader.arg", %"struct.ritz_module_1.ElfReader"** %"reader"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ElfReader"** %"reader", metadata !130, metadata !7), !dbg !131
  %"sym_index" = alloca i64
  store i64 %"sym_index.arg", i64* %"sym_index"
  call void @"llvm.dbg.declare"(metadata i64* %"sym_index", metadata !132, metadata !7), !dbg !131
  %".8" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !133
  %".9" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".8", i32 0, i32 4 , !dbg !133
  %".10" = load %"struct.ritz_module_1.Elf64_Sym"*, %"struct.ritz_module_1.Elf64_Sym"** %".9", !dbg !133
  %".11" = icmp eq %"struct.ritz_module_1.Elf64_Sym"* %".10", null , !dbg !133
  br i1 %".11", label %"if.then", label %"if.end", !dbg !133
if.then:
  %".13" = trunc i64 0 to i8 , !dbg !134
  ret i8 %".13", !dbg !134
if.end:
  %".15" = load i64, i64* %"sym_index", !dbg !135
  %".16" = icmp slt i64 %".15", 0 , !dbg !135
  br i1 %".16", label %"or.merge", label %"or.right", !dbg !135
or.right:
  %".18" = load i64, i64* %"sym_index", !dbg !135
  %".19" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !135
  %".20" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".19", i32 0, i32 5 , !dbg !135
  %".21" = load i64, i64* %".20", !dbg !135
  %".22" = icmp sge i64 %".18", %".21" , !dbg !135
  br label %"or.merge", !dbg !135
or.merge:
  %".24" = phi  i1 [1, %"if.end"], [%".22", %"or.right"] , !dbg !135
  br i1 %".24", label %"if.then.1", label %"if.end.1", !dbg !135
if.then.1:
  %".26" = trunc i64 0 to i8 , !dbg !136
  ret i8 %".26", !dbg !136
if.end.1:
  %".28" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !137
  %".29" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".28", i32 0, i32 4 , !dbg !137
  %".30" = load %"struct.ritz_module_1.Elf64_Sym"*, %"struct.ritz_module_1.Elf64_Sym"** %".29", !dbg !137
  %".31" = bitcast %"struct.ritz_module_1.Elf64_Sym"* %".30" to i8* , !dbg !137
  %".32" = load i64, i64* %"sym_index", !dbg !137
  %".33" = mul i64 %".32", 24, !dbg !137
  %".34" = getelementptr i8, i8* %".31", i64 %".33" , !dbg !137
  %".35" = getelementptr i8, i8* %".34", i64 4 , !dbg !138
  %".36" = load i8, i8* %".35", !dbg !138
  ret i8 %".36", !dbg !138
}

define i32 @"elf_is_function"(i8 %"info.arg") !dbg !24
{
entry:
  %"info" = alloca i8
  store i8 %"info.arg", i8* %"info"
  call void @"llvm.dbg.declare"(metadata i8* %"info", metadata !139, metadata !7), !dbg !140
  %".5" = load i8, i8* %"info", !dbg !141
  %".6" = zext i8 %".5" to i64 , !dbg !141
  %".7" = and i64 %".6", 15, !dbg !141
  %".8" = trunc i64 %".7" to i8 , !dbg !141
  %".9" = icmp eq i8 %".8", 2 , !dbg !142
  br i1 %".9", label %"if.then", label %"if.end", !dbg !142
if.then:
  %".11" = trunc i64 1 to i32 , !dbg !143
  ret i32 %".11", !dbg !143
if.end:
  %".13" = trunc i64 0 to i32 , !dbg !144
  ret i32 %".13", !dbg !144
}

define i32 @"elf_is_global"(i8 %"info.arg") !dbg !25
{
entry:
  %"info" = alloca i8
  store i8 %"info.arg", i8* %"info"
  call void @"llvm.dbg.declare"(metadata i8* %"info", metadata !145, metadata !7), !dbg !146
  %".5" = load i8, i8* %"info", !dbg !147
  %".6" = zext i8 %".5" to i64 , !dbg !147
  %".7" = lshr i64 %".6", 4, !dbg !147
  %".8" = trunc i64 %".7" to i8 , !dbg !147
  %".9" = icmp eq i8 %".8", 1 , !dbg !148
  br i1 %".9", label %"if.then", label %"if.end", !dbg !148
if.then:
  %".11" = trunc i64 1 to i32 , !dbg !149
  ret i32 %".11", !dbg !149
if.end:
  %".13" = trunc i64 0 to i32 , !dbg !150
  ret i32 %".13", !dbg !150
}

define i64 @"elf_symbol_count"(%"struct.ritz_module_1.ElfReader"* %"reader.arg") !dbg !26
{
entry:
  %"reader" = alloca %"struct.ritz_module_1.ElfReader"*
  store %"struct.ritz_module_1.ElfReader"* %"reader.arg", %"struct.ritz_module_1.ElfReader"** %"reader"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ElfReader"** %"reader", metadata !151, metadata !7), !dbg !152
  %".5" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !153
  %".6" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".5", i32 0, i32 5 , !dbg !153
  %".7" = load i64, i64* %".6", !dbg !153
  ret i64 %".7", !dbg !153
}

define i32 @"starts_with"(i8* %"s.arg", i8* %"prefix.arg") !dbg !27
{
entry:
  %"s" = alloca i8*
  %"i.addr" = alloca i64, !dbg !157
  store i8* %"s.arg", i8** %"s"
  call void @"llvm.dbg.declare"(metadata i8** %"s", metadata !154, metadata !7), !dbg !155
  %"prefix" = alloca i8*
  store i8* %"prefix.arg", i8** %"prefix"
  call void @"llvm.dbg.declare"(metadata i8** %"prefix", metadata !156, metadata !7), !dbg !155
  store i64 0, i64* %"i.addr", !dbg !157
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !158, metadata !7), !dbg !159
  br label %"while.cond", !dbg !160
while.cond:
  %".11" = load i8*, i8** %"prefix", !dbg !160
  %".12" = load i64, i64* %"i.addr", !dbg !160
  %".13" = getelementptr i8, i8* %".11", i64 %".12" , !dbg !160
  %".14" = load i8, i8* %".13", !dbg !160
  %".15" = zext i8 %".14" to i64 , !dbg !160
  %".16" = icmp ne i64 %".15", 0 , !dbg !160
  br i1 %".16", label %"while.body", label %"while.end", !dbg !160
while.body:
  %".18" = load i8*, i8** %"s", !dbg !161
  %".19" = load i64, i64* %"i.addr", !dbg !161
  %".20" = getelementptr i8, i8* %".18", i64 %".19" , !dbg !161
  %".21" = load i8, i8* %".20", !dbg !161
  %".22" = load i8*, i8** %"prefix", !dbg !161
  %".23" = load i64, i64* %"i.addr", !dbg !161
  %".24" = getelementptr i8, i8* %".22", i64 %".23" , !dbg !161
  %".25" = load i8, i8* %".24", !dbg !161
  %".26" = icmp ne i8 %".21", %".25" , !dbg !161
  br i1 %".26", label %"if.then", label %"if.end", !dbg !161
while.end:
  %".34" = trunc i64 1 to i32 , !dbg !164
  ret i32 %".34", !dbg !164
if.then:
  %".28" = trunc i64 0 to i32 , !dbg !162
  ret i32 %".28", !dbg !162
if.end:
  %".30" = load i64, i64* %"i.addr", !dbg !163
  %".31" = add i64 %".30", 1, !dbg !163
  store i64 %".31", i64* %"i.addr", !dbg !163
  br label %"while.cond", !dbg !163
}

define i32 @"elf_find_test_functions"(%"struct.ritz_module_1.ElfReader"* %"reader.arg", i8* %"callback.arg", i8* %"user_data.arg") !dbg !28
{
entry:
  %"reader" = alloca %"struct.ritz_module_1.ElfReader"*
  %"count.addr" = alloca i32, !dbg !169
  %"i.addr" = alloca i64, !dbg !172
  store %"struct.ritz_module_1.ElfReader"* %"reader.arg", %"struct.ritz_module_1.ElfReader"** %"reader"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ElfReader"** %"reader", metadata !165, metadata !7), !dbg !166
  %"callback" = alloca i8*
  store i8* %"callback.arg", i8** %"callback"
  call void @"llvm.dbg.declare"(metadata i8** %"callback", metadata !167, metadata !7), !dbg !166
  %"user_data" = alloca i8*
  store i8* %"user_data.arg", i8** %"user_data"
  call void @"llvm.dbg.declare"(metadata i8** %"user_data", metadata !168, metadata !7), !dbg !166
  %".11" = trunc i64 0 to i32 , !dbg !169
  store i32 %".11", i32* %"count.addr", !dbg !169
  call void @"llvm.dbg.declare"(metadata i32* %"count.addr", metadata !170, metadata !7), !dbg !171
  store i64 0, i64* %"i.addr", !dbg !172
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !173, metadata !7), !dbg !174
  br label %"while.cond", !dbg !175
while.cond:
  %".17" = load i64, i64* %"i.addr", !dbg !175
  %".18" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !175
  %".19" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".18", i32 0, i32 5 , !dbg !175
  %".20" = load i64, i64* %".19", !dbg !175
  %".21" = icmp slt i64 %".17", %".20" , !dbg !175
  br i1 %".21", label %"while.body", label %"while.end", !dbg !175
while.body:
  %".23" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !176
  %".24" = load i64, i64* %"i.addr", !dbg !176
  %".25" = call i8 @"elf_get_symbol_info"(%"struct.ritz_module_1.ElfReader"* %".23", i64 %".24"), !dbg !176
  %".26" = call i32 @"elf_is_function"(i8 %".25"), !dbg !177
  %".27" = sext i32 %".26" to i64 , !dbg !177
  %".28" = icmp ne i64 %".27", 0 , !dbg !177
  br i1 %".28", label %"and.right", label %"and.merge", !dbg !177
while.end:
  %".58" = load i32, i32* %"count.addr", !dbg !181
  ret i32 %".58", !dbg !181
and.right:
  %".30" = call i32 @"elf_is_global"(i8 %".25"), !dbg !177
  %".31" = sext i32 %".30" to i64 , !dbg !177
  %".32" = icmp ne i64 %".31", 0 , !dbg !177
  br label %"and.merge", !dbg !177
and.merge:
  %".34" = phi  i1 [0, %"while.body"], [%".32", %"and.right"] , !dbg !177
  br i1 %".34", label %"if.then", label %"if.end", !dbg !177
if.then:
  %".36" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !178
  %".37" = load i64, i64* %"i.addr", !dbg !178
  %".38" = call i8* @"elf_get_symbol_name"(%"struct.ritz_module_1.ElfReader"* %".36", i64 %".37"), !dbg !178
  %".39" = icmp ne i8* %".38", null , !dbg !178
  br i1 %".39", label %"if.then.1", label %"if.end.1", !dbg !178
if.end:
  %".54" = load i64, i64* %"i.addr", !dbg !180
  %".55" = add i64 %".54", 1, !dbg !180
  store i64 %".55", i64* %"i.addr", !dbg !180
  br label %"while.cond", !dbg !180
if.then.1:
  %".41" = getelementptr [6 x i8], [6 x i8]* @".str.0", i64 0, i64 0 , !dbg !178
  %".42" = call i32 @"starts_with"(i8* %".38", i8* %".41"), !dbg !178
  %".43" = sext i32 %".42" to i64 , !dbg !178
  %".44" = icmp ne i64 %".43", 0 , !dbg !178
  br i1 %".44", label %"if.then.2", label %"if.end.2", !dbg !178
if.end.1:
  br label %"if.end", !dbg !179
if.then.2:
  %".46" = load i32, i32* %"count.addr", !dbg !179
  %".47" = sext i32 %".46" to i64 , !dbg !179
  %".48" = add i64 %".47", 1, !dbg !179
  %".49" = trunc i64 %".48" to i32 , !dbg !179
  store i32 %".49", i32* %"count.addr", !dbg !179
  br label %"if.end.2", !dbg !179
if.end.2:
  br label %"if.end.1", !dbg !179
}

define i32 @"elf_print_test_functions"(%"struct.ritz_module_1.ElfReader"* %"reader.arg") !dbg !29
{
entry:
  %"reader" = alloca %"struct.ritz_module_1.ElfReader"*
  %"i.addr" = alloca i64, !dbg !185
  store %"struct.ritz_module_1.ElfReader"* %"reader.arg", %"struct.ritz_module_1.ElfReader"** %"reader"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.ElfReader"** %"reader", metadata !182, metadata !7), !dbg !183
  %".5" = getelementptr [23 x i8], [23 x i8]* @".str.1", i64 0, i64 0 , !dbg !184
  %".6" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".5", 0 , !dbg !184
  %".7" = insertvalue %"struct.ritz_module_1.StrView" %".6", i64 22, 1 , !dbg !184
  %".8" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".7"), !dbg !184
  store i64 0, i64* %"i.addr", !dbg !185
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !186, metadata !7), !dbg !187
  br label %"while.cond", !dbg !188
while.cond:
  %".12" = load i64, i64* %"i.addr", !dbg !188
  %".13" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !188
  %".14" = getelementptr %"struct.ritz_module_1.ElfReader", %"struct.ritz_module_1.ElfReader"* %".13", i32 0, i32 5 , !dbg !188
  %".15" = load i64, i64* %".14", !dbg !188
  %".16" = icmp slt i64 %".12", %".15" , !dbg !188
  br i1 %".16", label %"while.body", label %"while.end", !dbg !188
while.body:
  %".18" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !189
  %".19" = load i64, i64* %"i.addr", !dbg !189
  %".20" = call i8 @"elf_get_symbol_info"(%"struct.ritz_module_1.ElfReader"* %".18", i64 %".19"), !dbg !189
  %".21" = call i32 @"elf_is_function"(i8 %".20"), !dbg !190
  %".22" = sext i32 %".21" to i64 , !dbg !190
  %".23" = icmp ne i64 %".22", 0 , !dbg !190
  br i1 %".23", label %"and.right", label %"and.merge", !dbg !190
while.end:
  ret i32 0, !dbg !194
and.right:
  %".25" = call i32 @"elf_is_global"(i8 %".20"), !dbg !190
  %".26" = sext i32 %".25" to i64 , !dbg !190
  %".27" = icmp ne i64 %".26", 0 , !dbg !190
  br label %"and.merge", !dbg !190
and.merge:
  %".29" = phi  i1 [0, %"while.body"], [%".27", %"and.right"] , !dbg !190
  br i1 %".29", label %"if.then", label %"if.end", !dbg !190
if.then:
  %".31" = load %"struct.ritz_module_1.ElfReader"*, %"struct.ritz_module_1.ElfReader"** %"reader", !dbg !191
  %".32" = load i64, i64* %"i.addr", !dbg !191
  %".33" = call i8* @"elf_get_symbol_name"(%"struct.ritz_module_1.ElfReader"* %".31", i64 %".32"), !dbg !191
  %".34" = icmp ne i8* %".33", null , !dbg !191
  br i1 %".34", label %"if.then.1", label %"if.end.1", !dbg !191
if.end:
  %".53" = load i64, i64* %"i.addr", !dbg !194
  %".54" = add i64 %".53", 1, !dbg !194
  store i64 %".54", i64* %"i.addr", !dbg !194
  br label %"while.cond", !dbg !194
if.then.1:
  %".36" = getelementptr [6 x i8], [6 x i8]* @".str.2", i64 0, i64 0 , !dbg !191
  %".37" = call i32 @"starts_with"(i8* %".33", i8* %".36"), !dbg !191
  %".38" = sext i32 %".37" to i64 , !dbg !191
  %".39" = icmp ne i64 %".38", 0 , !dbg !191
  br i1 %".39", label %"if.then.2", label %"if.end.2", !dbg !191
if.end.1:
  br label %"if.end", !dbg !193
if.then.2:
  %".41" = getelementptr [3 x i8], [3 x i8]* @".str.3", i64 0, i64 0 , !dbg !192
  %".42" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".41", 0 , !dbg !192
  %".43" = insertvalue %"struct.ritz_module_1.StrView" %".42", i64 2, 1 , !dbg !192
  %".44" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".43"), !dbg !192
  %".45" = call i32 @"prints_cstr"(i8* %".33"), !dbg !193
  %".46" = getelementptr [2 x i8], [2 x i8]* @".str.4", i64 0, i64 0 , !dbg !193
  %".47" = insertvalue %"struct.ritz_module_1.StrView" undef, i8* %".46", 0 , !dbg !193
  %".48" = insertvalue %"struct.ritz_module_1.StrView" %".47", i64 1, 1 , !dbg !193
  %".49" = call i32 @"prints"(%"struct.ritz_module_1.StrView" %".48"), !dbg !193
  br label %"if.end.2", !dbg !193
if.end.2:
  br label %"if.end.1", !dbg !193
}

define linkonce_odr i8 @"vec_get$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg") !dbg !30
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !197, metadata !7), !dbg !198
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !199, metadata !7), !dbg !198
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !200
  %".8" = load i8*, i8** %".7", !dbg !200
  %".9" = load i64, i64* %"idx", !dbg !200
  %".10" = getelementptr i8, i8* %".8", i64 %".9" , !dbg !200
  %".11" = load i8, i8* %".10", !dbg !200
  ret i8 %".11", !dbg !200
}

define linkonce_odr i32 @"vec_push_bytes$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8* %"data.arg", i64 %"len.arg") !dbg !31
{
entry:
  %"i" = alloca i64, !dbg !205
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !201, metadata !7), !dbg !202
  %"data" = alloca i8*
  store i8* %"data.arg", i8** %"data"
  call void @"llvm.dbg.declare"(metadata i8** %"data", metadata !203, metadata !7), !dbg !202
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !204, metadata !7), !dbg !202
  %".10" = load i64, i64* %"len", !dbg !205
  store i64 0, i64* %"i", !dbg !205
  br label %"for.cond", !dbg !205
for.cond:
  %".13" = load i64, i64* %"i", !dbg !205
  %".14" = icmp slt i64 %".13", %".10" , !dbg !205
  br i1 %".14", label %"for.body", label %"for.end", !dbg !205
for.body:
  %".16" = load i8*, i8** %"data", !dbg !205
  %".17" = load i64, i64* %"i", !dbg !205
  %".18" = getelementptr i8, i8* %".16", i64 %".17" , !dbg !205
  %".19" = load i8, i8* %".18", !dbg !205
  %".20" = call i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %".19"), !dbg !205
  %".21" = sext i32 %".20" to i64 , !dbg !205
  %".22" = icmp ne i64 %".21", 0 , !dbg !205
  br i1 %".22", label %"if.then", label %"if.end", !dbg !205
for.incr:
  %".28" = load i64, i64* %"i", !dbg !206
  %".29" = add i64 %".28", 1, !dbg !206
  store i64 %".29", i64* %"i", !dbg !206
  br label %"for.cond", !dbg !206
for.end:
  %".32" = trunc i64 0 to i32 , !dbg !207
  ret i32 %".32", !dbg !207
if.then:
  %".24" = sub i64 0, 1, !dbg !206
  %".25" = trunc i64 %".24" to i32 , !dbg !206
  ret i32 %".25", !dbg !206
if.end:
  br label %"for.incr", !dbg !206
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_with_cap$u8"(i64 %"cap.arg") !dbg !32
{
entry:
  %"cap" = alloca i64
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !210
  store i64 %"cap.arg", i64* %"cap"
  call void @"llvm.dbg.declare"(metadata i64* %"cap", metadata !208, metadata !7), !dbg !209
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !211, metadata !7), !dbg !212
  %".6" = load i64, i64* %"cap", !dbg !213
  %".7" = icmp sle i64 %".6", 0 , !dbg !213
  br i1 %".7", label %"if.then", label %"if.end", !dbg !213
if.then:
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !214
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !214
  store i8* null, i8** %".10", !dbg !214
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !215
  %".13" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !215
  store i64 0, i64* %".13", !dbg !215
  %".15" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !216
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !216
  store i64 0, i64* %".16", !dbg !216
  %".18" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !217
  ret %"struct.ritz_module_1.Vec$u8" %".18", !dbg !217
if.end:
  %".20" = load i64, i64* %"cap", !dbg !218
  %".21" = mul i64 %".20", 1, !dbg !218
  %".22" = call i8* @"malloc"(i64 %".21"), !dbg !219
  %".23" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !219
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !219
  store i8* %".22", i8** %".24", !dbg !219
  %".26" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !220
  %".27" = load i8*, i8** %".26", !dbg !220
  %".28" = icmp eq i8* %".27", null , !dbg !220
  br i1 %".28", label %"if.then.1", label %"if.end.1", !dbg !220
if.then.1:
  %".30" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !221
  %".31" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !221
  store i64 0, i64* %".31", !dbg !221
  %".33" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !222
  %".34" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !222
  store i64 0, i64* %".34", !dbg !222
  %".36" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !223
  ret %"struct.ritz_module_1.Vec$u8" %".36", !dbg !223
if.end.1:
  %".38" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !224
  %".39" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !224
  store i64 0, i64* %".39", !dbg !224
  %".41" = load i64, i64* %"cap", !dbg !225
  %".42" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !225
  %".43" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !225
  store i64 %".41", i64* %".43", !dbg !225
  %".45" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !226
  ret %"struct.ritz_module_1.Vec$u8" %".45", !dbg !226
}

define linkonce_odr i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"needed.arg") !dbg !33
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !232
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !227, metadata !7), !dbg !228
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !229, metadata !7), !dbg !228
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !230
  %".8" = load i64, i64* %".7", !dbg !230
  %".9" = load i64, i64* %"needed", !dbg !230
  %".10" = icmp sge i64 %".8", %".9" , !dbg !230
  br i1 %".10", label %"if.then", label %"if.end", !dbg !230
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !231
  ret i32 %".12", !dbg !231
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !232
  %".15" = load i64, i64* %".14", !dbg !232
  store i64 %".15", i64* %"new_cap.addr", !dbg !232
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !233, metadata !7), !dbg !234
  %".18" = load i64, i64* %"new_cap.addr", !dbg !235
  %".19" = icmp eq i64 %".18", 0 , !dbg !235
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !235
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !236
  br label %"if.end.1", !dbg !236
if.end.1:
  br label %"while.cond", !dbg !237
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !237
  %".25" = load i64, i64* %"needed", !dbg !237
  %".26" = icmp slt i64 %".24", %".25" , !dbg !237
  br i1 %".26", label %"while.body", label %"while.end", !dbg !237
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !238
  %".29" = mul i64 %".28", 2, !dbg !238
  store i64 %".29", i64* %"new_cap.addr", !dbg !238
  br label %"while.cond", !dbg !238
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !239
  %".33" = call i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".32"), !dbg !239
  ret i32 %".33", !dbg !239
}

define linkonce_odr %"struct.ritz_module_1.Vec$u8" @"vec_new$u8"() !dbg !34
{
entry:
  %"v.addr" = alloca %"struct.ritz_module_1.Vec$u8", !dbg !240
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.addr", metadata !241, metadata !7), !dbg !242
  %".3" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !243
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 0 , !dbg !243
  store i8* null, i8** %".4", !dbg !243
  %".6" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !244
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 1 , !dbg !244
  store i64 0, i64* %".7", !dbg !244
  %".9" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !245
  %".10" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", i32 0, i32 2 , !dbg !245
  store i64 0, i64* %".10", !dbg !245
  %".12" = load %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.addr", !dbg !246
  ret %"struct.ritz_module_1.Vec$u8" %".12", !dbg !246
}

define linkonce_odr i32 @"vec_set$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"idx.arg", i8 %"item.arg") !dbg !35
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !247, metadata !7), !dbg !248
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !249, metadata !7), !dbg !248
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !250, metadata !7), !dbg !248
  %".10" = load i8, i8* %"item", !dbg !251
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !251
  %".12" = load i8*, i8** %".11", !dbg !251
  %".13" = load i64, i64* %"idx", !dbg !251
  %".14" = getelementptr i8, i8* %".12", i64 %".13" , !dbg !251
  store i8 %".10", i8* %".14", !dbg !251
  %".16" = trunc i64 0 to i32 , !dbg !252
  ret i32 %".16", !dbg !252
}

define linkonce_odr i32 @"vec_drop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !36
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !253, metadata !7), !dbg !254
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !255
  %".5" = load i8*, i8** %".4", !dbg !255
  %".6" = icmp ne i8* %".5", null , !dbg !255
  br i1 %".6", label %"if.then", label %"if.end", !dbg !255
if.then:
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !255
  %".9" = load i8*, i8** %".8", !dbg !255
  %".10" = call i32 @"free"(i8* %".9"), !dbg !255
  br label %"if.end", !dbg !255
if.end:
  %".12" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !256
  store i8* null, i8** %".12", !dbg !256
  %".14" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !257
  store i64 0, i64* %".14", !dbg !257
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !258
  store i64 0, i64* %".16", !dbg !258
  ret i32 0, !dbg !258
}

define linkonce_odr i8 @"vec_pop$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !37
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !259, metadata !7), !dbg !260
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !261
  %".5" = load i64, i64* %".4", !dbg !261
  %".6" = sub i64 %".5", 1, !dbg !261
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !261
  store i64 %".6", i64* %".7", !dbg !261
  %".9" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !262
  %".10" = load i8*, i8** %".9", !dbg !262
  %".11" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !262
  %".12" = load i64, i64* %".11", !dbg !262
  %".13" = getelementptr i8, i8* %".10", i64 %".12" , !dbg !262
  %".14" = load i8, i8* %".13", !dbg !262
  ret i8 %".14", !dbg !262
}

define linkonce_odr i32 @"vec_push$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i8 %"item.arg") !dbg !38
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !263, metadata !7), !dbg !264
  %"item" = alloca i8
  store i8 %"item.arg", i8* %"item"
  call void @"llvm.dbg.declare"(metadata i8* %"item", metadata !265, metadata !7), !dbg !264
  %".7" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !266
  %".8" = load i64, i64* %".7", !dbg !266
  %".9" = add i64 %".8", 1, !dbg !266
  %".10" = call i32 @"vec_ensure_cap$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %".9"), !dbg !266
  %".11" = sext i32 %".10" to i64 , !dbg !266
  %".12" = icmp ne i64 %".11", 0 , !dbg !266
  br i1 %".12", label %"if.then", label %"if.end", !dbg !266
if.then:
  %".14" = sub i64 0, 1, !dbg !267
  %".15" = trunc i64 %".14" to i32 , !dbg !267
  ret i32 %".15", !dbg !267
if.end:
  %".17" = load i8, i8* %"item", !dbg !268
  %".18" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !268
  %".19" = load i8*, i8** %".18", !dbg !268
  %".20" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !268
  %".21" = load i64, i64* %".20", !dbg !268
  %".22" = getelementptr i8, i8* %".19", i64 %".21" , !dbg !268
  store i8 %".17", i8* %".22", !dbg !268
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !269
  %".25" = load i64, i64* %".24", !dbg !269
  %".26" = add i64 %".25", 1, !dbg !269
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !269
  store i64 %".26", i64* %".27", !dbg !269
  %".29" = trunc i64 0 to i32 , !dbg !270
  ret i32 %".29", !dbg !270
}

define linkonce_odr i32 @"vec_push$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", %"struct.ritz_module_1.LineBounds" %"item.arg") !dbg !39
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !273, metadata !7), !dbg !274
  %"item" = alloca %"struct.ritz_module_1.LineBounds"
  store %"struct.ritz_module_1.LineBounds" %"item.arg", %"struct.ritz_module_1.LineBounds"* %"item"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.LineBounds"* %"item", metadata !276, metadata !7), !dbg !274
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !277
  %".8" = load i64, i64* %".7", !dbg !277
  %".9" = add i64 %".8", 1, !dbg !277
  %".10" = call i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".9"), !dbg !277
  %".11" = sext i32 %".10" to i64 , !dbg !277
  %".12" = icmp ne i64 %".11", 0 , !dbg !277
  br i1 %".12", label %"if.then", label %"if.end", !dbg !277
if.then:
  %".14" = sub i64 0, 1, !dbg !278
  %".15" = trunc i64 %".14" to i32 , !dbg !278
  ret i32 %".15", !dbg !278
if.end:
  %".17" = load %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %"item", !dbg !279
  %".18" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !279
  %".19" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".18", !dbg !279
  %".20" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !279
  %".21" = load i64, i64* %".20", !dbg !279
  %".22" = getelementptr %"struct.ritz_module_1.LineBounds", %"struct.ritz_module_1.LineBounds"* %".19", i64 %".21" , !dbg !279
  store %"struct.ritz_module_1.LineBounds" %".17", %"struct.ritz_module_1.LineBounds"* %".22", !dbg !279
  %".24" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !280
  %".25" = load i64, i64* %".24", !dbg !280
  %".26" = add i64 %".25", 1, !dbg !280
  %".27" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 1 , !dbg !280
  store i64 %".26", i64* %".27", !dbg !280
  %".29" = trunc i64 0 to i32 , !dbg !281
  ret i32 %".29", !dbg !281
}

define linkonce_odr i32 @"vec_clear$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg") !dbg !40
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !282, metadata !7), !dbg !283
  %".4" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 1 , !dbg !284
  store i64 0, i64* %".4", !dbg !284
  ret i32 0, !dbg !284
}

define linkonce_odr i32 @"vec_ensure_cap$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"needed.arg") !dbg !41
{
entry:
  %"new_cap.addr" = alloca i64, !dbg !290
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !285, metadata !7), !dbg !286
  %"needed" = alloca i64
  store i64 %"needed.arg", i64* %"needed"
  call void @"llvm.dbg.declare"(metadata i64* %"needed", metadata !287, metadata !7), !dbg !286
  %".7" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !288
  %".8" = load i64, i64* %".7", !dbg !288
  %".9" = load i64, i64* %"needed", !dbg !288
  %".10" = icmp sge i64 %".8", %".9" , !dbg !288
  br i1 %".10", label %"if.then", label %"if.end", !dbg !288
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !289
  ret i32 %".12", !dbg !289
if.end:
  %".14" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !290
  %".15" = load i64, i64* %".14", !dbg !290
  store i64 %".15", i64* %"new_cap.addr", !dbg !290
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap.addr", metadata !291, metadata !7), !dbg !292
  %".18" = load i64, i64* %"new_cap.addr", !dbg !293
  %".19" = icmp eq i64 %".18", 0 , !dbg !293
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !293
if.then.1:
  store i64 8, i64* %"new_cap.addr", !dbg !294
  br label %"if.end.1", !dbg !294
if.end.1:
  br label %"while.cond", !dbg !295
while.cond:
  %".24" = load i64, i64* %"new_cap.addr", !dbg !295
  %".25" = load i64, i64* %"needed", !dbg !295
  %".26" = icmp slt i64 %".24", %".25" , !dbg !295
  br i1 %".26", label %"while.body", label %"while.end", !dbg !295
while.body:
  %".28" = load i64, i64* %"new_cap.addr", !dbg !296
  %".29" = mul i64 %".28", 2, !dbg !296
  store i64 %".29", i64* %"new_cap.addr", !dbg !296
  br label %"while.cond", !dbg !296
while.end:
  %".32" = load i64, i64* %"new_cap.addr", !dbg !297
  %".33" = call i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %".32"), !dbg !297
  ret i32 %".33", !dbg !297
}

define linkonce_odr i32 @"vec_grow$u8"(%"struct.ritz_module_1.Vec$u8"* %"v.arg", i64 %"new_cap.arg") !dbg !42
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$u8"* %"v.arg", metadata !298, metadata !7), !dbg !299
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !300, metadata !7), !dbg !299
  %".7" = load i64, i64* %"new_cap", !dbg !301
  %".8" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !301
  %".9" = load i64, i64* %".8", !dbg !301
  %".10" = icmp sle i64 %".7", %".9" , !dbg !301
  br i1 %".10", label %"if.then", label %"if.end", !dbg !301
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !302
  ret i32 %".12", !dbg !302
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !303
  %".15" = mul i64 %".14", 1, !dbg !303
  %".16" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !304
  %".17" = load i8*, i8** %".16", !dbg !304
  %".18" = call i8* @"realloc"(i8* %".17", i64 %".15"), !dbg !304
  %".19" = icmp eq i8* %".18", null , !dbg !305
  br i1 %".19", label %"if.then.1", label %"if.end.1", !dbg !305
if.then.1:
  %".21" = sub i64 0, 1, !dbg !306
  %".22" = trunc i64 %".21" to i32 , !dbg !306
  ret i32 %".22", !dbg !306
if.end.1:
  %".24" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 0 , !dbg !307
  store i8* %".18", i8** %".24", !dbg !307
  %".26" = load i64, i64* %"new_cap", !dbg !308
  %".27" = getelementptr %"struct.ritz_module_1.Vec$u8", %"struct.ritz_module_1.Vec$u8"* %"v.arg", i32 0, i32 2 , !dbg !308
  store i64 %".26", i64* %".27", !dbg !308
  %".29" = trunc i64 0 to i32 , !dbg !309
  ret i32 %".29", !dbg !309
}

define linkonce_odr i32 @"vec_grow$LineBounds"(%"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i64 %"new_cap.arg") !dbg !43
{
entry:
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", metadata !310, metadata !7), !dbg !311
  %"new_cap" = alloca i64
  store i64 %"new_cap.arg", i64* %"new_cap"
  call void @"llvm.dbg.declare"(metadata i64* %"new_cap", metadata !312, metadata !7), !dbg !311
  %".7" = load i64, i64* %"new_cap", !dbg !313
  %".8" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !313
  %".9" = load i64, i64* %".8", !dbg !313
  %".10" = icmp sle i64 %".7", %".9" , !dbg !313
  br i1 %".10", label %"if.then", label %"if.end", !dbg !313
if.then:
  %".12" = trunc i64 0 to i32 , !dbg !314
  ret i32 %".12", !dbg !314
if.end:
  %".14" = load i64, i64* %"new_cap", !dbg !315
  %".15" = mul i64 %".14", 16, !dbg !315
  %".16" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !316
  %".17" = load %"struct.ritz_module_1.LineBounds"*, %"struct.ritz_module_1.LineBounds"** %".16", !dbg !316
  %".18" = bitcast %"struct.ritz_module_1.LineBounds"* %".17" to i8* , !dbg !316
  %".19" = call i8* @"realloc"(i8* %".18", i64 %".15"), !dbg !316
  %".20" = icmp eq i8* %".19", null , !dbg !317
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !317
if.then.1:
  %".22" = sub i64 0, 1, !dbg !318
  %".23" = trunc i64 %".22" to i32 , !dbg !318
  ret i32 %".23", !dbg !318
if.end.1:
  %".25" = bitcast i8* %".19" to %"struct.ritz_module_1.LineBounds"* , !dbg !319
  %".26" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 0 , !dbg !319
  store %"struct.ritz_module_1.LineBounds"* %".25", %"struct.ritz_module_1.LineBounds"** %".26", !dbg !319
  %".28" = load i64, i64* %"new_cap", !dbg !320
  %".29" = getelementptr %"struct.ritz_module_1.Vec$LineBounds", %"struct.ritz_module_1.Vec$LineBounds"* %"v.arg", i32 0, i32 2 , !dbg !320
  store i64 %".28", i64* %".29", !dbg !320
  %".31" = trunc i64 0 to i32 , !dbg !321
  ret i32 %".31", !dbg !321
}

@".str.0" = private constant [6 x i8] c"test_\00"
@".str.1" = private constant [23 x i8] c"Test functions found:\0a\00"
@".str.2" = private constant [6 x i8] c"test_\00"
@".str.3" = private constant [3 x i8] c"  \00"
@".str.4" = private constant [2 x i8] c"\0a\00"
!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/iris/ritzunit/ritz/ritzlib", filename: "elf.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 105, name: "elf_init", scopeLine: 105, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 140, name: "read_u16", scopeLine: 140, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 146, name: "read_u32", scopeLine: 146, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 154, name: "read_u64", scopeLine: 154, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 161, name: "elf_parse_sections", scopeLine: 161, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 207, name: "elf_get_symbol_name", scopeLine: 207, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 220, name: "elf_get_symbol_info", scopeLine: 220, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 230, name: "elf_is_function", scopeLine: 230, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 237, name: "elf_is_global", scopeLine: 237, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "elf_symbol_count", scopeLine: 244, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 252, name: "starts_with", scopeLine: 252, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 267, name: "elf_find_test_functions", scopeLine: 267, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 289, name: "elf_print_test_functions", scopeLine: 289, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 225, name: "vec_get$u8", scopeLine: 225, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 288, name: "vec_push_bytes$u8", scopeLine: 288, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 124, name: "vec_with_cap$u8", scopeLine: 124, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$u8", scopeLine: 193, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "vec_new$u8", scopeLine: 116, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 235, name: "vec_set$u8", scopeLine: 235, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 148, name: "vec_drop$u8", scopeLine: 148, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 219, name: "vec_pop$u8", scopeLine: 219, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$u8", scopeLine: 210, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 210, name: "vec_push$LineBounds", scopeLine: 210, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 244, name: "vec_clear$u8", scopeLine: 244, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 193, name: "vec_ensure_cap$LineBounds", scopeLine: 193, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$u8", scopeLine: 179, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 179, name: "vec_grow$LineBounds", scopeLine: 179, type: !4, unit: !1)
!44 = !DICompositeType(align: 64, file: !0, name: "ElfReader", size: 448, tag: DW_TAG_structure_type)
!45 = !DIDerivedType(baseType: !44, size: 64, tag: DW_TAG_pointer_type)
!46 = !DILocalVariable(file: !0, line: 105, name: "reader", scope: !17, type: !45)
!47 = !DILocation(column: 1, line: 105, scope: !17)
!48 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!49 = !DILocalVariable(file: !0, line: 105, name: "data", scope: !17, type: !48)
!50 = !DILocalVariable(file: !0, line: 105, name: "size", scope: !17, type: !11)
!51 = !DILocation(column: 5, line: 106, scope: !17)
!52 = !DILocation(column: 5, line: 107, scope: !17)
!53 = !DILocation(column: 5, line: 108, scope: !17)
!54 = !DILocation(column: 5, line: 109, scope: !17)
!55 = !DILocation(column: 5, line: 110, scope: !17)
!56 = !DILocation(column: 5, line: 111, scope: !17)
!57 = !DILocation(column: 5, line: 112, scope: !17)
!58 = !DILocation(column: 5, line: 115, scope: !17)
!59 = !DILocation(column: 9, line: 116, scope: !17)
!60 = !DILocation(column: 5, line: 119, scope: !17)
!61 = !DILocation(column: 9, line: 120, scope: !17)
!62 = !DILocation(column: 5, line: 121, scope: !17)
!63 = !DILocation(column: 9, line: 122, scope: !17)
!64 = !DILocation(column: 5, line: 123, scope: !17)
!65 = !DILocation(column: 9, line: 124, scope: !17)
!66 = !DILocation(column: 5, line: 125, scope: !17)
!67 = !DILocation(column: 9, line: 126, scope: !17)
!68 = !DILocation(column: 5, line: 129, scope: !17)
!69 = !DILocation(column: 9, line: 130, scope: !17)
!70 = !DILocation(column: 5, line: 133, scope: !17)
!71 = !DILocation(column: 9, line: 134, scope: !17)
!72 = !DILocation(column: 5, line: 136, scope: !17)
!73 = !DILocation(column: 5, line: 137, scope: !17)
!74 = !DILocalVariable(file: !0, line: 140, name: "ptr", scope: !18, type: !48)
!75 = !DILocation(column: 1, line: 140, scope: !18)
!76 = !DILocation(column: 5, line: 141, scope: !18)
!77 = !DILocation(column: 5, line: 142, scope: !18)
!78 = !DILocation(column: 5, line: 143, scope: !18)
!79 = !DILocalVariable(file: !0, line: 146, name: "ptr", scope: !19, type: !48)
!80 = !DILocation(column: 1, line: 146, scope: !19)
!81 = !DILocation(column: 5, line: 147, scope: !19)
!82 = !DILocation(column: 5, line: 148, scope: !19)
!83 = !DILocation(column: 5, line: 149, scope: !19)
!84 = !DILocation(column: 5, line: 150, scope: !19)
!85 = !DILocation(column: 5, line: 151, scope: !19)
!86 = !DILocalVariable(file: !0, line: 154, name: "ptr", scope: !20, type: !48)
!87 = !DILocation(column: 1, line: 154, scope: !20)
!88 = !DILocation(column: 5, line: 155, scope: !20)
!89 = !DILocation(column: 5, line: 156, scope: !20)
!90 = !DILocation(column: 5, line: 158, scope: !20)
!91 = !DILocalVariable(file: !0, line: 161, name: "reader", scope: !21, type: !45)
!92 = !DILocation(column: 1, line: 161, scope: !21)
!93 = !DILocation(column: 5, line: 162, scope: !21)
!94 = !DILocation(column: 5, line: 163, scope: !21)
!95 = !DILocation(column: 9, line: 164, scope: !21)
!96 = !DILocation(column: 5, line: 166, scope: !21)
!97 = !DILocation(column: 5, line: 170, scope: !21)
!98 = !DILocation(column: 5, line: 171, scope: !21)
!99 = !DILocation(column: 5, line: 172, scope: !21)
!100 = !DILocation(column: 5, line: 173, scope: !21)
!101 = !DILocation(column: 5, line: 175, scope: !21)
!102 = !DILocation(column: 9, line: 176, scope: !21)
!103 = !DILocation(column: 5, line: 178, scope: !21)
!104 = !DILocation(column: 5, line: 181, scope: !21)
!105 = !DILocation(column: 9, line: 182, scope: !21)
!106 = !DILocation(column: 9, line: 183, scope: !21)
!107 = !DILocation(column: 13, line: 187, scope: !21)
!108 = !DILocation(column: 13, line: 188, scope: !21)
!109 = !DILocation(column: 13, line: 189, scope: !21)
!110 = !DILocation(column: 13, line: 190, scope: !21)
!111 = !DILocation(column: 13, line: 192, scope: !21)
!112 = !DILocation(column: 13, line: 193, scope: !21)
!113 = !DILocation(column: 17, line: 194, scope: !21)
!114 = !DILocation(column: 13, line: 197, scope: !21)
!115 = !DILocation(column: 13, line: 198, scope: !21)
!116 = !DILocation(column: 13, line: 199, scope: !21)
!117 = !DILocation(column: 5, line: 201, scope: !21)
!118 = !DILocation(column: 9, line: 202, scope: !21)
!119 = !DILocation(column: 5, line: 204, scope: !21)
!120 = !DILocalVariable(file: !0, line: 207, name: "reader", scope: !22, type: !45)
!121 = !DILocation(column: 1, line: 207, scope: !22)
!122 = !DILocalVariable(file: !0, line: 207, name: "sym_index", scope: !22, type: !11)
!123 = !DILocation(column: 5, line: 208, scope: !22)
!124 = !DILocation(column: 9, line: 209, scope: !22)
!125 = !DILocation(column: 5, line: 210, scope: !22)
!126 = !DILocation(column: 9, line: 211, scope: !22)
!127 = !DILocation(column: 5, line: 214, scope: !22)
!128 = !DILocation(column: 5, line: 215, scope: !22)
!129 = !DILocation(column: 5, line: 217, scope: !22)
!130 = !DILocalVariable(file: !0, line: 220, name: "reader", scope: !23, type: !45)
!131 = !DILocation(column: 1, line: 220, scope: !23)
!132 = !DILocalVariable(file: !0, line: 220, name: "sym_index", scope: !23, type: !11)
!133 = !DILocation(column: 5, line: 221, scope: !23)
!134 = !DILocation(column: 9, line: 222, scope: !23)
!135 = !DILocation(column: 5, line: 223, scope: !23)
!136 = !DILocation(column: 9, line: 224, scope: !23)
!137 = !DILocation(column: 5, line: 226, scope: !23)
!138 = !DILocation(column: 5, line: 227, scope: !23)
!139 = !DILocalVariable(file: !0, line: 230, name: "info", scope: !24, type: !12)
!140 = !DILocation(column: 1, line: 230, scope: !24)
!141 = !DILocation(column: 5, line: 231, scope: !24)
!142 = !DILocation(column: 5, line: 232, scope: !24)
!143 = !DILocation(column: 9, line: 233, scope: !24)
!144 = !DILocation(column: 5, line: 234, scope: !24)
!145 = !DILocalVariable(file: !0, line: 237, name: "info", scope: !25, type: !12)
!146 = !DILocation(column: 1, line: 237, scope: !25)
!147 = !DILocation(column: 5, line: 238, scope: !25)
!148 = !DILocation(column: 5, line: 239, scope: !25)
!149 = !DILocation(column: 9, line: 240, scope: !25)
!150 = !DILocation(column: 5, line: 241, scope: !25)
!151 = !DILocalVariable(file: !0, line: 244, name: "reader", scope: !26, type: !45)
!152 = !DILocation(column: 1, line: 244, scope: !26)
!153 = !DILocation(column: 5, line: 245, scope: !26)
!154 = !DILocalVariable(file: !0, line: 252, name: "s", scope: !27, type: !48)
!155 = !DILocation(column: 1, line: 252, scope: !27)
!156 = !DILocalVariable(file: !0, line: 252, name: "prefix", scope: !27, type: !48)
!157 = !DILocation(column: 5, line: 253, scope: !27)
!158 = !DILocalVariable(file: !0, line: 253, name: "i", scope: !27, type: !11)
!159 = !DILocation(column: 1, line: 253, scope: !27)
!160 = !DILocation(column: 5, line: 254, scope: !27)
!161 = !DILocation(column: 9, line: 255, scope: !27)
!162 = !DILocation(column: 13, line: 256, scope: !27)
!163 = !DILocation(column: 9, line: 257, scope: !27)
!164 = !DILocation(column: 5, line: 258, scope: !27)
!165 = !DILocalVariable(file: !0, line: 267, name: "reader", scope: !28, type: !45)
!166 = !DILocation(column: 1, line: 267, scope: !28)
!167 = !DILocalVariable(file: !0, line: 267, name: "callback", scope: !28, type: !48)
!168 = !DILocalVariable(file: !0, line: 267, name: "user_data", scope: !28, type: !48)
!169 = !DILocation(column: 5, line: 268, scope: !28)
!170 = !DILocalVariable(file: !0, line: 268, name: "count", scope: !28, type: !10)
!171 = !DILocation(column: 1, line: 268, scope: !28)
!172 = !DILocation(column: 5, line: 269, scope: !28)
!173 = !DILocalVariable(file: !0, line: 269, name: "i", scope: !28, type: !11)
!174 = !DILocation(column: 1, line: 269, scope: !28)
!175 = !DILocation(column: 5, line: 271, scope: !28)
!176 = !DILocation(column: 9, line: 272, scope: !28)
!177 = !DILocation(column: 9, line: 275, scope: !28)
!178 = !DILocation(column: 13, line: 276, scope: !28)
!179 = !DILocation(column: 21, line: 280, scope: !28)
!180 = !DILocation(column: 9, line: 284, scope: !28)
!181 = !DILocation(column: 5, line: 286, scope: !28)
!182 = !DILocalVariable(file: !0, line: 289, name: "reader", scope: !29, type: !45)
!183 = !DILocation(column: 1, line: 289, scope: !29)
!184 = !DILocation(column: 5, line: 290, scope: !29)
!185 = !DILocation(column: 5, line: 291, scope: !29)
!186 = !DILocalVariable(file: !0, line: 291, name: "i", scope: !29, type: !11)
!187 = !DILocation(column: 1, line: 291, scope: !29)
!188 = !DILocation(column: 5, line: 293, scope: !29)
!189 = !DILocation(column: 9, line: 294, scope: !29)
!190 = !DILocation(column: 9, line: 296, scope: !29)
!191 = !DILocation(column: 13, line: 297, scope: !29)
!192 = !DILocation(column: 21, line: 300, scope: !29)
!193 = !DILocation(column: 21, line: 301, scope: !29)
!194 = !DILocation(column: 9, line: 304, scope: !29)
!195 = !DICompositeType(align: 64, file: !0, name: "Vec$u8", size: 192, tag: DW_TAG_structure_type)
!196 = !DIDerivedType(baseType: !195, size: 64, tag: DW_TAG_reference_type)
!197 = !DILocalVariable(file: !0, line: 225, name: "v", scope: !30, type: !196)
!198 = !DILocation(column: 1, line: 225, scope: !30)
!199 = !DILocalVariable(file: !0, line: 225, name: "idx", scope: !30, type: !11)
!200 = !DILocation(column: 5, line: 226, scope: !30)
!201 = !DILocalVariable(file: !0, line: 288, name: "v", scope: !31, type: !196)
!202 = !DILocation(column: 1, line: 288, scope: !31)
!203 = !DILocalVariable(file: !0, line: 288, name: "data", scope: !31, type: !48)
!204 = !DILocalVariable(file: !0, line: 288, name: "len", scope: !31, type: !11)
!205 = !DILocation(column: 5, line: 289, scope: !31)
!206 = !DILocation(column: 13, line: 291, scope: !31)
!207 = !DILocation(column: 5, line: 292, scope: !31)
!208 = !DILocalVariable(file: !0, line: 124, name: "cap", scope: !32, type: !11)
!209 = !DILocation(column: 1, line: 124, scope: !32)
!210 = !DILocation(column: 5, line: 125, scope: !32)
!211 = !DILocalVariable(file: !0, line: 125, name: "v", scope: !32, type: !195)
!212 = !DILocation(column: 1, line: 125, scope: !32)
!213 = !DILocation(column: 5, line: 126, scope: !32)
!214 = !DILocation(column: 9, line: 127, scope: !32)
!215 = !DILocation(column: 9, line: 128, scope: !32)
!216 = !DILocation(column: 9, line: 129, scope: !32)
!217 = !DILocation(column: 9, line: 130, scope: !32)
!218 = !DILocation(column: 5, line: 132, scope: !32)
!219 = !DILocation(column: 5, line: 133, scope: !32)
!220 = !DILocation(column: 5, line: 134, scope: !32)
!221 = !DILocation(column: 9, line: 135, scope: !32)
!222 = !DILocation(column: 9, line: 136, scope: !32)
!223 = !DILocation(column: 9, line: 137, scope: !32)
!224 = !DILocation(column: 5, line: 139, scope: !32)
!225 = !DILocation(column: 5, line: 140, scope: !32)
!226 = !DILocation(column: 5, line: 141, scope: !32)
!227 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !33, type: !196)
!228 = !DILocation(column: 1, line: 193, scope: !33)
!229 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !33, type: !11)
!230 = !DILocation(column: 5, line: 194, scope: !33)
!231 = !DILocation(column: 9, line: 195, scope: !33)
!232 = !DILocation(column: 5, line: 197, scope: !33)
!233 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !33, type: !11)
!234 = !DILocation(column: 1, line: 197, scope: !33)
!235 = !DILocation(column: 5, line: 198, scope: !33)
!236 = !DILocation(column: 9, line: 199, scope: !33)
!237 = !DILocation(column: 5, line: 200, scope: !33)
!238 = !DILocation(column: 9, line: 201, scope: !33)
!239 = !DILocation(column: 5, line: 203, scope: !33)
!240 = !DILocation(column: 5, line: 117, scope: !34)
!241 = !DILocalVariable(file: !0, line: 117, name: "v", scope: !34, type: !195)
!242 = !DILocation(column: 1, line: 117, scope: !34)
!243 = !DILocation(column: 5, line: 118, scope: !34)
!244 = !DILocation(column: 5, line: 119, scope: !34)
!245 = !DILocation(column: 5, line: 120, scope: !34)
!246 = !DILocation(column: 5, line: 121, scope: !34)
!247 = !DILocalVariable(file: !0, line: 235, name: "v", scope: !35, type: !196)
!248 = !DILocation(column: 1, line: 235, scope: !35)
!249 = !DILocalVariable(file: !0, line: 235, name: "idx", scope: !35, type: !11)
!250 = !DILocalVariable(file: !0, line: 235, name: "item", scope: !35, type: !12)
!251 = !DILocation(column: 5, line: 236, scope: !35)
!252 = !DILocation(column: 5, line: 237, scope: !35)
!253 = !DILocalVariable(file: !0, line: 148, name: "v", scope: !36, type: !196)
!254 = !DILocation(column: 1, line: 148, scope: !36)
!255 = !DILocation(column: 5, line: 149, scope: !36)
!256 = !DILocation(column: 5, line: 151, scope: !36)
!257 = !DILocation(column: 5, line: 152, scope: !36)
!258 = !DILocation(column: 5, line: 153, scope: !36)
!259 = !DILocalVariable(file: !0, line: 219, name: "v", scope: !37, type: !196)
!260 = !DILocation(column: 1, line: 219, scope: !37)
!261 = !DILocation(column: 5, line: 220, scope: !37)
!262 = !DILocation(column: 5, line: 221, scope: !37)
!263 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !38, type: !196)
!264 = !DILocation(column: 1, line: 210, scope: !38)
!265 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !38, type: !12)
!266 = !DILocation(column: 5, line: 211, scope: !38)
!267 = !DILocation(column: 9, line: 212, scope: !38)
!268 = !DILocation(column: 5, line: 213, scope: !38)
!269 = !DILocation(column: 5, line: 214, scope: !38)
!270 = !DILocation(column: 5, line: 215, scope: !38)
!271 = !DICompositeType(align: 64, file: !0, name: "Vec$LineBounds", size: 192, tag: DW_TAG_structure_type)
!272 = !DIDerivedType(baseType: !271, size: 64, tag: DW_TAG_reference_type)
!273 = !DILocalVariable(file: !0, line: 210, name: "v", scope: !39, type: !272)
!274 = !DILocation(column: 1, line: 210, scope: !39)
!275 = !DICompositeType(align: 64, file: !0, name: "LineBounds", size: 128, tag: DW_TAG_structure_type)
!276 = !DILocalVariable(file: !0, line: 210, name: "item", scope: !39, type: !275)
!277 = !DILocation(column: 5, line: 211, scope: !39)
!278 = !DILocation(column: 9, line: 212, scope: !39)
!279 = !DILocation(column: 5, line: 213, scope: !39)
!280 = !DILocation(column: 5, line: 214, scope: !39)
!281 = !DILocation(column: 5, line: 215, scope: !39)
!282 = !DILocalVariable(file: !0, line: 244, name: "v", scope: !40, type: !196)
!283 = !DILocation(column: 1, line: 244, scope: !40)
!284 = !DILocation(column: 5, line: 245, scope: !40)
!285 = !DILocalVariable(file: !0, line: 193, name: "v", scope: !41, type: !272)
!286 = !DILocation(column: 1, line: 193, scope: !41)
!287 = !DILocalVariable(file: !0, line: 193, name: "needed", scope: !41, type: !11)
!288 = !DILocation(column: 5, line: 194, scope: !41)
!289 = !DILocation(column: 9, line: 195, scope: !41)
!290 = !DILocation(column: 5, line: 197, scope: !41)
!291 = !DILocalVariable(file: !0, line: 197, name: "new_cap", scope: !41, type: !11)
!292 = !DILocation(column: 1, line: 197, scope: !41)
!293 = !DILocation(column: 5, line: 198, scope: !41)
!294 = !DILocation(column: 9, line: 199, scope: !41)
!295 = !DILocation(column: 5, line: 200, scope: !41)
!296 = !DILocation(column: 9, line: 201, scope: !41)
!297 = !DILocation(column: 5, line: 203, scope: !41)
!298 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !42, type: !196)
!299 = !DILocation(column: 1, line: 179, scope: !42)
!300 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !42, type: !11)
!301 = !DILocation(column: 5, line: 180, scope: !42)
!302 = !DILocation(column: 9, line: 181, scope: !42)
!303 = !DILocation(column: 5, line: 183, scope: !42)
!304 = !DILocation(column: 5, line: 184, scope: !42)
!305 = !DILocation(column: 5, line: 185, scope: !42)
!306 = !DILocation(column: 9, line: 186, scope: !42)
!307 = !DILocation(column: 5, line: 188, scope: !42)
!308 = !DILocation(column: 5, line: 189, scope: !42)
!309 = !DILocation(column: 5, line: 190, scope: !42)
!310 = !DILocalVariable(file: !0, line: 179, name: "v", scope: !43, type: !272)
!311 = !DILocation(column: 1, line: 179, scope: !43)
!312 = !DILocalVariable(file: !0, line: 179, name: "new_cap", scope: !43, type: !11)
!313 = !DILocation(column: 5, line: 180, scope: !43)
!314 = !DILocation(column: 9, line: 181, scope: !43)
!315 = !DILocation(column: 5, line: 183, scope: !43)
!316 = !DILocation(column: 5, line: 184, scope: !43)
!317 = !DILocation(column: 5, line: 185, scope: !43)
!318 = !DILocation(column: 9, line: 186, scope: !43)
!319 = !DILocation(column: 5, line: 188, scope: !43)
!320 = !DILocation(column: 5, line: 189, scope: !43)
!321 = !DILocation(column: 5, line: 190, scope: !43)