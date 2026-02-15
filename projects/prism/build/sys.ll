; Ritz compiled module
; ModuleID = "ritz_module_1"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

%"struct.ritz_module_1.Stat" = type {i64, i64, i64, i32, i32, i32, i32, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64, i64}
%"struct.ritz_module_1.Dirent64" = type {i64, i64, i16, i8}
%"struct.ritz_module_1.Timeval" = type {i64, i64}
declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

define i32 @"sys_stat2"(i8* %"path.arg", %"struct.ritz_module_1.Stat"* %"statbuf.arg") !dbg !17
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !70, metadata !7), !dbg !71
  %"statbuf" = alloca %"struct.ritz_module_1.Stat"*
  store %"struct.ritz_module_1.Stat"* %"statbuf.arg", %"struct.ritz_module_1.Stat"** %"statbuf"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Stat"** %"statbuf", metadata !74, metadata !7), !dbg !71
  %".8" = load i8*, i8** %"path", !dbg !75
  %".9" = ptrtoint i8* %".8" to i64 , !dbg !75
  %".10" = load %"struct.ritz_module_1.Stat"*, %"struct.ritz_module_1.Stat"** %"statbuf", !dbg !75
  %".11" = ptrtoint %"struct.ritz_module_1.Stat"* %".10" to i64 , !dbg !75
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 4, i64 %".9", i64 %".11"), !dbg !75
  %".13" = trunc i64 %".12" to i32 , !dbg !75
  ret i32 %".13", !dbg !75
}

define i32 @"sys_fstat2"(i32 %"fd.arg", %"struct.ritz_module_1.Stat"* %"statbuf.arg") !dbg !18
{
entry:
  %"fd" = alloca i32
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !76, metadata !7), !dbg !77
  %"statbuf" = alloca %"struct.ritz_module_1.Stat"*
  store %"struct.ritz_module_1.Stat"* %"statbuf.arg", %"struct.ritz_module_1.Stat"** %"statbuf"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Stat"** %"statbuf", metadata !78, metadata !7), !dbg !77
  %".8" = load i32, i32* %"fd", !dbg !79
  %".9" = sext i32 %".8" to i64 , !dbg !79
  %".10" = load %"struct.ritz_module_1.Stat"*, %"struct.ritz_module_1.Stat"** %"statbuf", !dbg !79
  %".11" = ptrtoint %"struct.ritz_module_1.Stat"* %".10" to i64 , !dbg !79
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 5, i64 %".9", i64 %".11"), !dbg !79
  %".13" = trunc i64 %".12" to i32 , !dbg !79
  ret i32 %".13", !dbg !79
}

define i32 @"sys_lstat2"(i8* %"path.arg", %"struct.ritz_module_1.Stat"* %"statbuf.arg") !dbg !19
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !80, metadata !7), !dbg !81
  %"statbuf" = alloca %"struct.ritz_module_1.Stat"*
  store %"struct.ritz_module_1.Stat"* %"statbuf.arg", %"struct.ritz_module_1.Stat"** %"statbuf"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Stat"** %"statbuf", metadata !82, metadata !7), !dbg !81
  %".8" = load i8*, i8** %"path", !dbg !83
  %".9" = ptrtoint i8* %".8" to i64 , !dbg !83
  %".10" = load %"struct.ritz_module_1.Stat"*, %"struct.ritz_module_1.Stat"** %"statbuf", !dbg !83
  %".11" = ptrtoint %"struct.ritz_module_1.Stat"* %".10" to i64 , !dbg !83
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 6, i64 %".9", i64 %".11"), !dbg !83
  %".13" = trunc i64 %".12" to i32 , !dbg !83
  ret i32 %".13", !dbg !83
}

define i32 @"at_fdcwd"() !dbg !20
{
entry:
  %".2" = sub i64 0, 100, !dbg !84
  %".3" = trunc i64 %".2" to i32 , !dbg !84
  ret i32 %".3", !dbg !84
}

define i64 @"sys_read"(i32 %"fd.arg", i8* %"buf.arg", i64 %"count.arg") !dbg !21
{
entry:
  %"fd" = alloca i32
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !85, metadata !7), !dbg !86
  %"buf" = alloca i8*
  store i8* %"buf.arg", i8** %"buf"
  call void @"llvm.dbg.declare"(metadata i8** %"buf", metadata !87, metadata !7), !dbg !86
  %"count" = alloca i64
  store i64 %"count.arg", i64* %"count"
  call void @"llvm.dbg.declare"(metadata i64* %"count", metadata !88, metadata !7), !dbg !86
  %".11" = load i32, i32* %"fd", !dbg !89
  %".12" = sext i32 %".11" to i64 , !dbg !89
  %".13" = load i8*, i8** %"buf", !dbg !89
  %".14" = ptrtoint i8* %".13" to i64 , !dbg !89
  %".15" = load i64, i64* %"count", !dbg !89
  %".16" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 0, i64 %".12", i64 %".14", i64 %".15"), !dbg !89
  ret i64 %".16", !dbg !89
}

define i64 @"sys_write"(i32 %"fd.arg", i8* %"buf.arg", i64 %"count.arg") !dbg !22
{
entry:
  %"fd" = alloca i32
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !90, metadata !7), !dbg !91
  %"buf" = alloca i8*
  store i8* %"buf.arg", i8** %"buf"
  call void @"llvm.dbg.declare"(metadata i8** %"buf", metadata !92, metadata !7), !dbg !91
  %"count" = alloca i64
  store i64 %"count.arg", i64* %"count"
  call void @"llvm.dbg.declare"(metadata i64* %"count", metadata !93, metadata !7), !dbg !91
  %".11" = load i32, i32* %"fd", !dbg !94
  %".12" = sext i32 %".11" to i64 , !dbg !94
  %".13" = load i8*, i8** %"buf", !dbg !94
  %".14" = ptrtoint i8* %".13" to i64 , !dbg !94
  %".15" = load i64, i64* %"count", !dbg !94
  %".16" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 1, i64 %".12", i64 %".14", i64 %".15"), !dbg !94
  ret i64 %".16", !dbg !94
}

define i32 @"sys_open"(i8* %"path.arg", i32 %"flags.arg") !dbg !23
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !95, metadata !7), !dbg !96
  %"flags" = alloca i32
  store i32 %"flags.arg", i32* %"flags"
  call void @"llvm.dbg.declare"(metadata i32* %"flags", metadata !97, metadata !7), !dbg !96
  %".8" = load i8*, i8** %"path", !dbg !98
  %".9" = ptrtoint i8* %".8" to i64 , !dbg !98
  %".10" = load i32, i32* %"flags", !dbg !98
  %".11" = sext i32 %".10" to i64 , !dbg !98
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 2, i64 %".9", i64 %".11"), !dbg !98
  %".13" = trunc i64 %".12" to i32 , !dbg !98
  ret i32 %".13", !dbg !98
}

define i32 @"sys_open3"(i8* %"path.arg", i32 %"flags.arg", i32 %"mode.arg") !dbg !24
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !99, metadata !7), !dbg !100
  %"flags" = alloca i32
  store i32 %"flags.arg", i32* %"flags"
  call void @"llvm.dbg.declare"(metadata i32* %"flags", metadata !101, metadata !7), !dbg !100
  %"mode" = alloca i32
  store i32 %"mode.arg", i32* %"mode"
  call void @"llvm.dbg.declare"(metadata i32* %"mode", metadata !102, metadata !7), !dbg !100
  %".11" = load i8*, i8** %"path", !dbg !103
  %".12" = ptrtoint i8* %".11" to i64 , !dbg !103
  %".13" = load i32, i32* %"flags", !dbg !103
  %".14" = sext i32 %".13" to i64 , !dbg !103
  %".15" = load i32, i32* %"mode", !dbg !103
  %".16" = sext i32 %".15" to i64 , !dbg !103
  %".17" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 2, i64 %".12", i64 %".14", i64 %".16"), !dbg !103
  %".18" = trunc i64 %".17" to i32 , !dbg !103
  ret i32 %".18", !dbg !103
}

define i32 @"sys_close"(i32 %"fd.arg") !dbg !25
{
entry:
  %"fd" = alloca i32
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !104, metadata !7), !dbg !105
  %".5" = load i32, i32* %"fd", !dbg !106
  %".6" = sext i32 %".5" to i64 , !dbg !106
  %".7" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 3, i64 %".6"), !dbg !106
  %".8" = trunc i64 %".7" to i32 , !dbg !106
  ret i32 %".8", !dbg !106
}

define i64 @"sys_lseek"(i32 %"fd.arg", i64 %"offset.arg", i32 %"whence.arg") !dbg !26
{
entry:
  %"fd" = alloca i32
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !107, metadata !7), !dbg !108
  %"offset" = alloca i64
  store i64 %"offset.arg", i64* %"offset"
  call void @"llvm.dbg.declare"(metadata i64* %"offset", metadata !109, metadata !7), !dbg !108
  %"whence" = alloca i32
  store i32 %"whence.arg", i32* %"whence"
  call void @"llvm.dbg.declare"(metadata i32* %"whence", metadata !110, metadata !7), !dbg !108
  %".11" = load i32, i32* %"fd", !dbg !111
  %".12" = sext i32 %".11" to i64 , !dbg !111
  %".13" = load i64, i64* %"offset", !dbg !111
  %".14" = load i32, i32* %"whence", !dbg !111
  %".15" = sext i32 %".14" to i64 , !dbg !111
  %".16" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 8, i64 %".12", i64 %".13", i64 %".15"), !dbg !111
  ret i64 %".16", !dbg !111
}

define i32 @"sys_ftruncate"(i32 %"fd.arg", i64 %"length.arg") !dbg !27
{
entry:
  %"fd" = alloca i32
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !112, metadata !7), !dbg !113
  %"length" = alloca i64
  store i64 %"length.arg", i64* %"length"
  call void @"llvm.dbg.declare"(metadata i64* %"length", metadata !114, metadata !7), !dbg !113
  %".8" = load i32, i32* %"fd", !dbg !115
  %".9" = sext i32 %".8" to i64 , !dbg !115
  %".10" = load i64, i64* %"length", !dbg !115
  %".11" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 77, i64 %".9", i64 %".10"), !dbg !115
  %".12" = trunc i64 %".11" to i32 , !dbg !115
  ret i32 %".12", !dbg !115
}

define i32 @"sys_stat"(i8* %"path.arg", i8* %"statbuf.arg") !dbg !28
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !116, metadata !7), !dbg !117
  %"statbuf" = alloca i8*
  store i8* %"statbuf.arg", i8** %"statbuf"
  call void @"llvm.dbg.declare"(metadata i8** %"statbuf", metadata !118, metadata !7), !dbg !117
  %".8" = load i8*, i8** %"path", !dbg !119
  %".9" = ptrtoint i8* %".8" to i64 , !dbg !119
  %".10" = load i8*, i8** %"statbuf", !dbg !119
  %".11" = ptrtoint i8* %".10" to i64 , !dbg !119
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 4, i64 %".9", i64 %".11"), !dbg !119
  %".13" = trunc i64 %".12" to i32 , !dbg !119
  ret i32 %".13", !dbg !119
}

define i32 @"sys_fstat"(i32 %"fd.arg", i8* %"statbuf.arg") !dbg !29
{
entry:
  %"fd" = alloca i32
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !120, metadata !7), !dbg !121
  %"statbuf" = alloca i8*
  store i8* %"statbuf.arg", i8** %"statbuf"
  call void @"llvm.dbg.declare"(metadata i8** %"statbuf", metadata !122, metadata !7), !dbg !121
  %".8" = load i32, i32* %"fd", !dbg !123
  %".9" = sext i32 %".8" to i64 , !dbg !123
  %".10" = load i8*, i8** %"statbuf", !dbg !123
  %".11" = ptrtoint i8* %".10" to i64 , !dbg !123
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 5, i64 %".9", i64 %".11"), !dbg !123
  %".13" = trunc i64 %".12" to i32 , !dbg !123
  ret i32 %".13", !dbg !123
}

define i32 @"sys_lstat"(i8* %"path.arg", i8* %"statbuf.arg") !dbg !30
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !124, metadata !7), !dbg !125
  %"statbuf" = alloca i8*
  store i8* %"statbuf.arg", i8** %"statbuf"
  call void @"llvm.dbg.declare"(metadata i8** %"statbuf", metadata !126, metadata !7), !dbg !125
  %".8" = load i8*, i8** %"path", !dbg !127
  %".9" = ptrtoint i8* %".8" to i64 , !dbg !127
  %".10" = load i8*, i8** %"statbuf", !dbg !127
  %".11" = ptrtoint i8* %".10" to i64 , !dbg !127
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 6, i64 %".9", i64 %".11"), !dbg !127
  %".13" = trunc i64 %".12" to i32 , !dbg !127
  ret i32 %".13", !dbg !127
}

define i32 @"sys_chmod"(i8* %"path.arg", i32 %"mode.arg") !dbg !31
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !128, metadata !7), !dbg !129
  %"mode" = alloca i32
  store i32 %"mode.arg", i32* %"mode"
  call void @"llvm.dbg.declare"(metadata i32* %"mode", metadata !130, metadata !7), !dbg !129
  %".8" = load i8*, i8** %"path", !dbg !131
  %".9" = ptrtoint i8* %".8" to i64 , !dbg !131
  %".10" = load i32, i32* %"mode", !dbg !131
  %".11" = sext i32 %".10" to i64 , !dbg !131
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 90, i64 %".9", i64 %".11"), !dbg !131
  %".13" = trunc i64 %".12" to i32 , !dbg !131
  ret i32 %".13", !dbg !131
}

define i32 @"sys_fchmod"(i32 %"fd.arg", i32 %"mode.arg") !dbg !32
{
entry:
  %"fd" = alloca i32
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !132, metadata !7), !dbg !133
  %"mode" = alloca i32
  store i32 %"mode.arg", i32* %"mode"
  call void @"llvm.dbg.declare"(metadata i32* %"mode", metadata !134, metadata !7), !dbg !133
  %".8" = load i32, i32* %"fd", !dbg !135
  %".9" = sext i32 %".8" to i64 , !dbg !135
  %".10" = load i32, i32* %"mode", !dbg !135
  %".11" = sext i32 %".10" to i64 , !dbg !135
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 91, i64 %".9", i64 %".11"), !dbg !135
  %".13" = trunc i64 %".12" to i32 , !dbg !135
  ret i32 %".13", !dbg !135
}

define i32 @"sys_chown"(i8* %"path.arg", i32 %"uid.arg", i32 %"gid.arg") !dbg !33
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !136, metadata !7), !dbg !137
  %"uid" = alloca i32
  store i32 %"uid.arg", i32* %"uid"
  call void @"llvm.dbg.declare"(metadata i32* %"uid", metadata !138, metadata !7), !dbg !137
  %"gid" = alloca i32
  store i32 %"gid.arg", i32* %"gid"
  call void @"llvm.dbg.declare"(metadata i32* %"gid", metadata !139, metadata !7), !dbg !137
  %".11" = load i8*, i8** %"path", !dbg !140
  %".12" = ptrtoint i8* %".11" to i64 , !dbg !140
  %".13" = load i32, i32* %"uid", !dbg !140
  %".14" = sext i32 %".13" to i64 , !dbg !140
  %".15" = load i32, i32* %"gid", !dbg !140
  %".16" = sext i32 %".15" to i64 , !dbg !140
  %".17" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 92, i64 %".12", i64 %".14", i64 %".16"), !dbg !140
  %".18" = trunc i64 %".17" to i32 , !dbg !140
  ret i32 %".18", !dbg !140
}

define i32 @"sys_fchown"(i32 %"fd.arg", i32 %"uid.arg", i32 %"gid.arg") !dbg !34
{
entry:
  %"fd" = alloca i32
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !141, metadata !7), !dbg !142
  %"uid" = alloca i32
  store i32 %"uid.arg", i32* %"uid"
  call void @"llvm.dbg.declare"(metadata i32* %"uid", metadata !143, metadata !7), !dbg !142
  %"gid" = alloca i32
  store i32 %"gid.arg", i32* %"gid"
  call void @"llvm.dbg.declare"(metadata i32* %"gid", metadata !144, metadata !7), !dbg !142
  %".11" = load i32, i32* %"fd", !dbg !145
  %".12" = sext i32 %".11" to i64 , !dbg !145
  %".13" = load i32, i32* %"uid", !dbg !145
  %".14" = sext i32 %".13" to i64 , !dbg !145
  %".15" = load i32, i32* %"gid", !dbg !145
  %".16" = sext i32 %".15" to i64 , !dbg !145
  %".17" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 93, i64 %".12", i64 %".14", i64 %".16"), !dbg !145
  %".18" = trunc i64 %".17" to i32 , !dbg !145
  ret i32 %".18", !dbg !145
}

define i32 @"sys_access"(i8* %"path.arg", i32 %"mode.arg") !dbg !35
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !146, metadata !7), !dbg !147
  %"mode" = alloca i32
  store i32 %"mode.arg", i32* %"mode"
  call void @"llvm.dbg.declare"(metadata i32* %"mode", metadata !148, metadata !7), !dbg !147
  %".8" = load i8*, i8** %"path", !dbg !149
  %".9" = ptrtoint i8* %".8" to i64 , !dbg !149
  %".10" = load i32, i32* %"mode", !dbg !149
  %".11" = sext i32 %".10" to i64 , !dbg !149
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 21, i64 %".9", i64 %".11"), !dbg !149
  %".13" = trunc i64 %".12" to i32 , !dbg !149
  ret i32 %".13", !dbg !149
}

define i32 @"sys_utimensat"(i32 %"dirfd.arg", i8* %"path.arg", i64* %"times.arg", i32 %"flags.arg") !dbg !36
{
entry:
  %"dirfd" = alloca i32
  store i32 %"dirfd.arg", i32* %"dirfd"
  call void @"llvm.dbg.declare"(metadata i32* %"dirfd", metadata !150, metadata !7), !dbg !151
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !152, metadata !7), !dbg !151
  %"times" = alloca i64*
  store i64* %"times.arg", i64** %"times"
  call void @"llvm.dbg.declare"(metadata i64** %"times", metadata !154, metadata !7), !dbg !151
  %"flags" = alloca i32
  store i32 %"flags.arg", i32* %"flags"
  call void @"llvm.dbg.declare"(metadata i32* %"flags", metadata !155, metadata !7), !dbg !151
  %".14" = load i32, i32* %"dirfd", !dbg !156
  %".15" = sext i32 %".14" to i64 , !dbg !156
  %".16" = load i8*, i8** %"path", !dbg !156
  %".17" = ptrtoint i8* %".16" to i64 , !dbg !156
  %".18" = load i64*, i64** %"times", !dbg !156
  %".19" = ptrtoint i64* %".18" to i64 , !dbg !156
  %".20" = load i32, i32* %"flags", !dbg !156
  %".21" = sext i32 %".20" to i64 , !dbg !156
  %".22" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}"(i64 280, i64 %".15", i64 %".17", i64 %".19", i64 %".21"), !dbg !156
  %".23" = trunc i64 %".22" to i32 , !dbg !156
  ret i32 %".23", !dbg !156
}

define i32 @"sys_mkdir"(i8* %"path.arg", i32 %"mode.arg") !dbg !37
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !157, metadata !7), !dbg !158
  %"mode" = alloca i32
  store i32 %"mode.arg", i32* %"mode"
  call void @"llvm.dbg.declare"(metadata i32* %"mode", metadata !159, metadata !7), !dbg !158
  %".8" = load i8*, i8** %"path", !dbg !160
  %".9" = ptrtoint i8* %".8" to i64 , !dbg !160
  %".10" = load i32, i32* %"mode", !dbg !160
  %".11" = sext i32 %".10" to i64 , !dbg !160
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 83, i64 %".9", i64 %".11"), !dbg !160
  %".13" = trunc i64 %".12" to i32 , !dbg !160
  ret i32 %".13", !dbg !160
}

define i32 @"sys_rmdir"(i8* %"path.arg") !dbg !38
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !161, metadata !7), !dbg !162
  %".5" = load i8*, i8** %"path", !dbg !163
  %".6" = ptrtoint i8* %".5" to i64 , !dbg !163
  %".7" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 84, i64 %".6"), !dbg !163
  %".8" = trunc i64 %".7" to i32 , !dbg !163
  ret i32 %".8", !dbg !163
}

define i64 @"sys_getcwd"(i8* %"buf.arg", i64 %"size.arg") !dbg !39
{
entry:
  %"buf" = alloca i8*
  store i8* %"buf.arg", i8** %"buf"
  call void @"llvm.dbg.declare"(metadata i8** %"buf", metadata !164, metadata !7), !dbg !165
  %"size" = alloca i64
  store i64 %"size.arg", i64* %"size"
  call void @"llvm.dbg.declare"(metadata i64* %"size", metadata !166, metadata !7), !dbg !165
  %".8" = load i8*, i8** %"buf", !dbg !167
  %".9" = ptrtoint i8* %".8" to i64 , !dbg !167
  %".10" = load i64, i64* %"size", !dbg !167
  %".11" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 79, i64 %".9", i64 %".10"), !dbg !167
  ret i64 %".11", !dbg !167
}

define i32 @"sys_chdir"(i8* %"path.arg") !dbg !40
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !168, metadata !7), !dbg !169
  %".5" = load i8*, i8** %"path", !dbg !170
  %".6" = ptrtoint i8* %".5" to i64 , !dbg !170
  %".7" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 80, i64 %".6"), !dbg !170
  %".8" = trunc i64 %".7" to i32 , !dbg !170
  ret i32 %".8", !dbg !170
}

define i64 @"sys_getdents64"(i32 %"fd.arg", i8* %"dirp.arg", i64 %"count.arg") !dbg !41
{
entry:
  %"fd" = alloca i32
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !171, metadata !7), !dbg !172
  %"dirp" = alloca i8*
  store i8* %"dirp.arg", i8** %"dirp"
  call void @"llvm.dbg.declare"(metadata i8** %"dirp", metadata !173, metadata !7), !dbg !172
  %"count" = alloca i64
  store i64 %"count.arg", i64* %"count"
  call void @"llvm.dbg.declare"(metadata i64* %"count", metadata !174, metadata !7), !dbg !172
  %".11" = load i32, i32* %"fd", !dbg !175
  %".12" = sext i32 %".11" to i64 , !dbg !175
  %".13" = load i8*, i8** %"dirp", !dbg !175
  %".14" = ptrtoint i8* %".13" to i64 , !dbg !175
  %".15" = load i64, i64* %"count", !dbg !175
  %".16" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 217, i64 %".12", i64 %".14", i64 %".15"), !dbg !175
  ret i64 %".16", !dbg !175
}

define i32 @"sys_unlink"(i8* %"path.arg") !dbg !42
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !176, metadata !7), !dbg !177
  %".5" = load i8*, i8** %"path", !dbg !178
  %".6" = ptrtoint i8* %".5" to i64 , !dbg !178
  %".7" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 87, i64 %".6"), !dbg !178
  %".8" = trunc i64 %".7" to i32 , !dbg !178
  ret i32 %".8", !dbg !178
}

define i32 @"sys_rename"(i8* %"oldpath.arg", i8* %"newpath.arg") !dbg !43
{
entry:
  %"oldpath" = alloca i8*
  store i8* %"oldpath.arg", i8** %"oldpath"
  call void @"llvm.dbg.declare"(metadata i8** %"oldpath", metadata !179, metadata !7), !dbg !180
  %"newpath" = alloca i8*
  store i8* %"newpath.arg", i8** %"newpath"
  call void @"llvm.dbg.declare"(metadata i8** %"newpath", metadata !181, metadata !7), !dbg !180
  %".8" = load i8*, i8** %"oldpath", !dbg !182
  %".9" = ptrtoint i8* %".8" to i64 , !dbg !182
  %".10" = load i8*, i8** %"newpath", !dbg !182
  %".11" = ptrtoint i8* %".10" to i64 , !dbg !182
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 82, i64 %".9", i64 %".11"), !dbg !182
  %".13" = trunc i64 %".12" to i32 , !dbg !182
  ret i32 %".13", !dbg !182
}

define i32 @"sys_link"(i8* %"oldpath.arg", i8* %"newpath.arg") !dbg !44
{
entry:
  %"oldpath" = alloca i8*
  store i8* %"oldpath.arg", i8** %"oldpath"
  call void @"llvm.dbg.declare"(metadata i8** %"oldpath", metadata !183, metadata !7), !dbg !184
  %"newpath" = alloca i8*
  store i8* %"newpath.arg", i8** %"newpath"
  call void @"llvm.dbg.declare"(metadata i8** %"newpath", metadata !185, metadata !7), !dbg !184
  %".8" = load i8*, i8** %"oldpath", !dbg !186
  %".9" = ptrtoint i8* %".8" to i64 , !dbg !186
  %".10" = load i8*, i8** %"newpath", !dbg !186
  %".11" = ptrtoint i8* %".10" to i64 , !dbg !186
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 86, i64 %".9", i64 %".11"), !dbg !186
  %".13" = trunc i64 %".12" to i32 , !dbg !186
  ret i32 %".13", !dbg !186
}

define i32 @"sys_symlink"(i8* %"target.arg", i8* %"linkpath.arg") !dbg !45
{
entry:
  %"target" = alloca i8*
  store i8* %"target.arg", i8** %"target"
  call void @"llvm.dbg.declare"(metadata i8** %"target", metadata !187, metadata !7), !dbg !188
  %"linkpath" = alloca i8*
  store i8* %"linkpath.arg", i8** %"linkpath"
  call void @"llvm.dbg.declare"(metadata i8** %"linkpath", metadata !189, metadata !7), !dbg !188
  %".8" = load i8*, i8** %"target", !dbg !190
  %".9" = ptrtoint i8* %".8" to i64 , !dbg !190
  %".10" = load i8*, i8** %"linkpath", !dbg !190
  %".11" = ptrtoint i8* %".10" to i64 , !dbg !190
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 88, i64 %".9", i64 %".11"), !dbg !190
  %".13" = trunc i64 %".12" to i32 , !dbg !190
  ret i32 %".13", !dbg !190
}

define i64 @"sys_readlink"(i8* %"path.arg", i8* %"buf.arg", i64 %"size.arg") !dbg !46
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !191, metadata !7), !dbg !192
  %"buf" = alloca i8*
  store i8* %"buf.arg", i8** %"buf"
  call void @"llvm.dbg.declare"(metadata i8** %"buf", metadata !193, metadata !7), !dbg !192
  %"size" = alloca i64
  store i64 %"size.arg", i64* %"size"
  call void @"llvm.dbg.declare"(metadata i64* %"size", metadata !194, metadata !7), !dbg !192
  %".11" = load i8*, i8** %"path", !dbg !195
  %".12" = ptrtoint i8* %".11" to i64 , !dbg !195
  %".13" = load i8*, i8** %"buf", !dbg !195
  %".14" = ptrtoint i8* %".13" to i64 , !dbg !195
  %".15" = load i64, i64* %"size", !dbg !195
  %".16" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 89, i64 %".12", i64 %".14", i64 %".15"), !dbg !195
  ret i64 %".16", !dbg !195
}

define i8* @"sys_mmap"(i64 %"addr.arg", i64 %"length.arg", i32 %"prot.arg", i32 %"flags.arg", i32 %"fd.arg", i64 %"offset.arg") !dbg !47
{
entry:
  %"addr" = alloca i64
  store i64 %"addr.arg", i64* %"addr"
  call void @"llvm.dbg.declare"(metadata i64* %"addr", metadata !196, metadata !7), !dbg !197
  %"length" = alloca i64
  store i64 %"length.arg", i64* %"length"
  call void @"llvm.dbg.declare"(metadata i64* %"length", metadata !198, metadata !7), !dbg !197
  %"prot" = alloca i32
  store i32 %"prot.arg", i32* %"prot"
  call void @"llvm.dbg.declare"(metadata i32* %"prot", metadata !199, metadata !7), !dbg !197
  %"flags" = alloca i32
  store i32 %"flags.arg", i32* %"flags"
  call void @"llvm.dbg.declare"(metadata i32* %"flags", metadata !200, metadata !7), !dbg !197
  %"fd" = alloca i32
  store i32 %"fd.arg", i32* %"fd"
  call void @"llvm.dbg.declare"(metadata i32* %"fd", metadata !201, metadata !7), !dbg !197
  %"offset" = alloca i64
  store i64 %"offset.arg", i64* %"offset"
  call void @"llvm.dbg.declare"(metadata i64* %"offset", metadata !202, metadata !7), !dbg !197
  %".20" = load i64, i64* %"addr", !dbg !203
  %".21" = load i64, i64* %"length", !dbg !203
  %".22" = load i32, i32* %"prot", !dbg !203
  %".23" = sext i32 %".22" to i64 , !dbg !203
  %".24" = load i32, i32* %"flags", !dbg !203
  %".25" = sext i32 %".24" to i64 , !dbg !203
  %".26" = load i32, i32* %"fd", !dbg !203
  %".27" = sext i32 %".26" to i64 , !dbg !203
  %".28" = load i64, i64* %"offset", !dbg !203
  %".29" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},{r10},{r8},{r9},~{rcx},~{r11},~{memory}"(i64 9, i64 %".20", i64 %".21", i64 %".23", i64 %".25", i64 %".27", i64 %".28"), !dbg !203
  %".30" = inttoptr i64 %".29" to i8* , !dbg !203
  ret i8* %".30", !dbg !203
}

define i32 @"sys_munmap"(i8* %"addr.arg", i64 %"length.arg") !dbg !48
{
entry:
  %"addr" = alloca i8*
  store i8* %"addr.arg", i8** %"addr"
  call void @"llvm.dbg.declare"(metadata i8** %"addr", metadata !204, metadata !7), !dbg !205
  %"length" = alloca i64
  store i64 %"length.arg", i64* %"length"
  call void @"llvm.dbg.declare"(metadata i64* %"length", metadata !206, metadata !7), !dbg !205
  %".8" = load i8*, i8** %"addr", !dbg !207
  %".9" = ptrtoint i8* %".8" to i64 , !dbg !207
  %".10" = load i64, i64* %"length", !dbg !207
  %".11" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 11, i64 %".9", i64 %".10"), !dbg !207
  %".12" = trunc i64 %".11" to i32 , !dbg !207
  ret i32 %".12", !dbg !207
}

define i32 @"sys_mprotect"(i8* %"addr.arg", i64 %"length.arg", i32 %"prot.arg") !dbg !49
{
entry:
  %"addr" = alloca i8*
  store i8* %"addr.arg", i8** %"addr"
  call void @"llvm.dbg.declare"(metadata i8** %"addr", metadata !208, metadata !7), !dbg !209
  %"length" = alloca i64
  store i64 %"length.arg", i64* %"length"
  call void @"llvm.dbg.declare"(metadata i64* %"length", metadata !210, metadata !7), !dbg !209
  %"prot" = alloca i32
  store i32 %"prot.arg", i32* %"prot"
  call void @"llvm.dbg.declare"(metadata i32* %"prot", metadata !211, metadata !7), !dbg !209
  %".11" = load i8*, i8** %"addr", !dbg !212
  %".12" = ptrtoint i8* %".11" to i64 , !dbg !212
  %".13" = load i64, i64* %"length", !dbg !212
  %".14" = load i32, i32* %"prot", !dbg !212
  %".15" = sext i32 %".14" to i64 , !dbg !212
  %".16" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 10, i64 %".12", i64 %".13", i64 %".15"), !dbg !212
  %".17" = trunc i64 %".16" to i32 , !dbg !212
  ret i32 %".17", !dbg !212
}

define i32 @"sys_exit"(i32 %"status.arg") !dbg !50
{
entry:
  %"status" = alloca i32
  store i32 %"status.arg", i32* %"status"
  call void @"llvm.dbg.declare"(metadata i32* %"status", metadata !213, metadata !7), !dbg !214
  %".5" = load i32, i32* %"status", !dbg !215
  %".6" = sext i32 %".5" to i64 , !dbg !215
  %".7" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 60, i64 %".6"), !dbg !215
  %".8" = trunc i64 %".7" to i32 , !dbg !215
  ret i32 %".8", !dbg !215
}

define i32 @"sys_getpid"() !dbg !51
{
entry:
  %".2" = call i64 asm sideeffect "syscall", "=&{rax},{rax},~{rcx},~{r11},~{memory}"(i64 39), !dbg !216
  %".3" = trunc i64 %".2" to i32 , !dbg !216
  ret i32 %".3", !dbg !216
}

define i32 @"sys_getppid"() !dbg !52
{
entry:
  %".2" = call i64 asm sideeffect "syscall", "=&{rax},{rax},~{rcx},~{r11},~{memory}"(i64 110), !dbg !217
  %".3" = trunc i64 %".2" to i32 , !dbg !217
  ret i32 %".3", !dbg !217
}

define i32 @"sys_getuid"() !dbg !53
{
entry:
  %".2" = call i64 asm sideeffect "syscall", "=&{rax},{rax},~{rcx},~{r11},~{memory}"(i64 102), !dbg !218
  %".3" = trunc i64 %".2" to i32 , !dbg !218
  ret i32 %".3", !dbg !218
}

define i32 @"sys_getgid"() !dbg !54
{
entry:
  %".2" = call i64 asm sideeffect "syscall", "=&{rax},{rax},~{rcx},~{r11},~{memory}"(i64 104), !dbg !219
  %".3" = trunc i64 %".2" to i32 , !dbg !219
  ret i32 %".3", !dbg !219
}

define i32 @"sys_geteuid"() !dbg !55
{
entry:
  %".2" = call i64 asm sideeffect "syscall", "=&{rax},{rax},~{rcx},~{r11},~{memory}"(i64 107), !dbg !220
  %".3" = trunc i64 %".2" to i32 , !dbg !220
  ret i32 %".3", !dbg !220
}

define i32 @"sys_getegid"() !dbg !56
{
entry:
  %".2" = call i64 asm sideeffect "syscall", "=&{rax},{rax},~{rcx},~{r11},~{memory}"(i64 108), !dbg !221
  %".3" = trunc i64 %".2" to i32 , !dbg !221
  ret i32 %".3", !dbg !221
}

define i32 @"sys_fork"() !dbg !57
{
entry:
  %".2" = call i64 asm sideeffect "syscall", "=&{rax},{rax},~{rcx},~{r11},~{memory}"(i64 57), !dbg !222
  %".3" = trunc i64 %".2" to i32 , !dbg !222
  ret i32 %".3", !dbg !222
}

define i32 @"sys_execve"(i8* %"path.arg", i8** %"argv.arg", i8** %"envp.arg") !dbg !58
{
entry:
  %"path" = alloca i8*
  store i8* %"path.arg", i8** %"path"
  call void @"llvm.dbg.declare"(metadata i8** %"path", metadata !223, metadata !7), !dbg !224
  %"argv" = alloca i8**
  store i8** %"argv.arg", i8*** %"argv"
  call void @"llvm.dbg.declare"(metadata i8*** %"argv", metadata !226, metadata !7), !dbg !224
  %"envp" = alloca i8**
  store i8** %"envp.arg", i8*** %"envp"
  call void @"llvm.dbg.declare"(metadata i8*** %"envp", metadata !227, metadata !7), !dbg !224
  %".11" = load i8*, i8** %"path", !dbg !228
  %".12" = ptrtoint i8* %".11" to i64 , !dbg !228
  %".13" = load i8**, i8*** %"argv", !dbg !228
  %".14" = ptrtoint i8** %".13" to i64 , !dbg !228
  %".15" = load i8**, i8*** %"envp", !dbg !228
  %".16" = ptrtoint i8** %".15" to i64 , !dbg !228
  %".17" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 59, i64 %".12", i64 %".14", i64 %".16"), !dbg !228
  %".18" = trunc i64 %".17" to i32 , !dbg !228
  ret i32 %".18", !dbg !228
}

define i32 @"sys_wait4"(i32 %"pid.arg", i32* %"status.arg", i32 %"options.arg", i8* %"rusage.arg") !dbg !59
{
entry:
  %"pid" = alloca i32
  store i32 %"pid.arg", i32* %"pid"
  call void @"llvm.dbg.declare"(metadata i32* %"pid", metadata !229, metadata !7), !dbg !230
  %"status" = alloca i32*
  store i32* %"status.arg", i32** %"status"
  call void @"llvm.dbg.declare"(metadata i32** %"status", metadata !232, metadata !7), !dbg !230
  %"options" = alloca i32
  store i32 %"options.arg", i32* %"options"
  call void @"llvm.dbg.declare"(metadata i32* %"options", metadata !233, metadata !7), !dbg !230
  %"rusage" = alloca i8*
  store i8* %"rusage.arg", i8** %"rusage"
  call void @"llvm.dbg.declare"(metadata i8** %"rusage", metadata !234, metadata !7), !dbg !230
  %".14" = load i32, i32* %"pid", !dbg !235
  %".15" = sext i32 %".14" to i64 , !dbg !235
  %".16" = load i32*, i32** %"status", !dbg !235
  %".17" = ptrtoint i32* %".16" to i64 , !dbg !235
  %".18" = load i32, i32* %"options", !dbg !235
  %".19" = sext i32 %".18" to i64 , !dbg !235
  %".20" = load i8*, i8** %"rusage", !dbg !235
  %".21" = ptrtoint i8* %".20" to i64 , !dbg !235
  %".22" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}"(i64 61, i64 %".15", i64 %".17", i64 %".19", i64 %".21"), !dbg !235
  %".23" = trunc i64 %".22" to i32 , !dbg !235
  ret i32 %".23", !dbg !235
}

define i32 @"sys_kill"(i32 %"pid.arg", i32 %"sig.arg") !dbg !60
{
entry:
  %"pid" = alloca i32
  store i32 %"pid.arg", i32* %"pid"
  call void @"llvm.dbg.declare"(metadata i32* %"pid", metadata !236, metadata !7), !dbg !237
  %"sig" = alloca i32
  store i32 %"sig.arg", i32* %"sig"
  call void @"llvm.dbg.declare"(metadata i32* %"sig", metadata !238, metadata !7), !dbg !237
  %".8" = load i32, i32* %"pid", !dbg !239
  %".9" = sext i32 %".8" to i64 , !dbg !239
  %".10" = load i32, i32* %"sig", !dbg !239
  %".11" = sext i32 %".10" to i64 , !dbg !239
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 62, i64 %".9", i64 %".11"), !dbg !239
  %".13" = trunc i64 %".12" to i32 , !dbg !239
  ret i32 %".13", !dbg !239
}

define i32 @"sys_pipe"(i32* %"pipefd.arg") !dbg !61
{
entry:
  %"pipefd" = alloca i32*
  store i32* %"pipefd.arg", i32** %"pipefd"
  call void @"llvm.dbg.declare"(metadata i32** %"pipefd", metadata !240, metadata !7), !dbg !241
  %".5" = load i32*, i32** %"pipefd", !dbg !242
  %".6" = ptrtoint i32* %".5" to i64 , !dbg !242
  %".7" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 22, i64 %".6"), !dbg !242
  %".8" = trunc i64 %".7" to i32 , !dbg !242
  ret i32 %".8", !dbg !242
}

define i32 @"sys_dup"(i32 %"oldfd.arg") !dbg !62
{
entry:
  %"oldfd" = alloca i32
  store i32 %"oldfd.arg", i32* %"oldfd"
  call void @"llvm.dbg.declare"(metadata i32* %"oldfd", metadata !243, metadata !7), !dbg !244
  %".5" = load i32, i32* %"oldfd", !dbg !245
  %".6" = sext i32 %".5" to i64 , !dbg !245
  %".7" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 32, i64 %".6"), !dbg !245
  %".8" = trunc i64 %".7" to i32 , !dbg !245
  ret i32 %".8", !dbg !245
}

define i32 @"sys_dup2"(i32 %"oldfd.arg", i32 %"newfd.arg") !dbg !63
{
entry:
  %"oldfd" = alloca i32
  store i32 %"oldfd.arg", i32* %"oldfd"
  call void @"llvm.dbg.declare"(metadata i32* %"oldfd", metadata !246, metadata !7), !dbg !247
  %"newfd" = alloca i32
  store i32 %"newfd.arg", i32* %"newfd"
  call void @"llvm.dbg.declare"(metadata i32* %"newfd", metadata !248, metadata !7), !dbg !247
  %".8" = load i32, i32* %"oldfd", !dbg !249
  %".9" = sext i32 %".8" to i64 , !dbg !249
  %".10" = load i32, i32* %"newfd", !dbg !249
  %".11" = sext i32 %".10" to i64 , !dbg !249
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 33, i64 %".9", i64 %".11"), !dbg !249
  %".13" = trunc i64 %".12" to i32 , !dbg !249
  ret i32 %".13", !dbg !249
}

define i32 @"sys_rt_sigaction"(i32 %"signum.arg", i8* %"act.arg", i8* %"oldact.arg", i64 %"sigsetsize.arg") !dbg !64
{
entry:
  %"signum" = alloca i32
  store i32 %"signum.arg", i32* %"signum"
  call void @"llvm.dbg.declare"(metadata i32* %"signum", metadata !250, metadata !7), !dbg !251
  %"act" = alloca i8*
  store i8* %"act.arg", i8** %"act"
  call void @"llvm.dbg.declare"(metadata i8** %"act", metadata !252, metadata !7), !dbg !251
  %"oldact" = alloca i8*
  store i8* %"oldact.arg", i8** %"oldact"
  call void @"llvm.dbg.declare"(metadata i8** %"oldact", metadata !253, metadata !7), !dbg !251
  %"sigsetsize" = alloca i64
  store i64 %"sigsetsize.arg", i64* %"sigsetsize"
  call void @"llvm.dbg.declare"(metadata i64* %"sigsetsize", metadata !254, metadata !7), !dbg !251
  %".14" = load i32, i32* %"signum", !dbg !255
  %".15" = sext i32 %".14" to i64 , !dbg !255
  %".16" = load i8*, i8** %"act", !dbg !255
  %".17" = ptrtoint i8* %".16" to i64 , !dbg !255
  %".18" = load i8*, i8** %"oldact", !dbg !255
  %".19" = ptrtoint i8* %".18" to i64 , !dbg !255
  %".20" = load i64, i64* %"sigsetsize", !dbg !255
  %".21" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}"(i64 13, i64 %".15", i64 %".17", i64 %".19", i64 %".20"), !dbg !255
  %".22" = trunc i64 %".21" to i32 , !dbg !255
  ret i32 %".22", !dbg !255
}

define i32 @"signal_ignore"(i32 %"signum.arg") !dbg !65
{
entry:
  %"signum" = alloca i32
  %"act.addr" = alloca [32 x i8], !dbg !258
  %"i.addr" = alloca i64, !dbg !264
  store i32 %"signum.arg", i32* %"signum"
  call void @"llvm.dbg.declare"(metadata i32* %"signum", metadata !256, metadata !7), !dbg !257
  call void @"llvm.dbg.declare"(metadata [32 x i8]* %"act.addr", metadata !262, metadata !7), !dbg !263
  store i64 0, i64* %"i.addr", !dbg !264
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !265, metadata !7), !dbg !266
  br label %"while.cond", !dbg !267
while.cond:
  %".9" = load i64, i64* %"i.addr", !dbg !267
  %".10" = icmp slt i64 %".9", 32 , !dbg !267
  br i1 %".10", label %"while.body", label %"while.end", !dbg !267
while.body:
  %".12" = load i64, i64* %"i.addr", !dbg !268
  %".13" = getelementptr [32 x i8], [32 x i8]* %"act.addr", i32 0, i64 %".12" , !dbg !268
  %".14" = trunc i64 0 to i8 , !dbg !268
  store i8 %".14", i8* %".13", !dbg !268
  %".16" = load i64, i64* %"i.addr", !dbg !269
  %".17" = add i64 %".16", 1, !dbg !269
  store i64 %".17", i64* %"i.addr", !dbg !269
  br label %"while.cond", !dbg !269
while.end:
  %".20" = getelementptr [32 x i8], [32 x i8]* %"act.addr", i32 0, i64 0 , !dbg !270
  %".21" = trunc i64 1 to i8 , !dbg !270
  store i8 %".21", i8* %".20", !dbg !270
  %".23" = load i32, i32* %"signum", !dbg !271
  %".24" = getelementptr [32 x i8], [32 x i8]* %"act.addr", i32 0, i64 0 , !dbg !271
  %".25" = call i32 @"sys_rt_sigaction"(i32 %".23", i8* %".24", i8* null, i64 8), !dbg !271
  ret i32 %".25", !dbg !271
}

define i32 @"sys_nanosleep"(i64* %"req.arg", i64* %"rem.arg") !dbg !66
{
entry:
  %"req" = alloca i64*
  store i64* %"req.arg", i64** %"req"
  call void @"llvm.dbg.declare"(metadata i64** %"req", metadata !272, metadata !7), !dbg !273
  %"rem" = alloca i64*
  store i64* %"rem.arg", i64** %"rem"
  call void @"llvm.dbg.declare"(metadata i64** %"rem", metadata !274, metadata !7), !dbg !273
  %".8" = load i64*, i64** %"req", !dbg !275
  %".9" = ptrtoint i64* %".8" to i64 , !dbg !275
  %".10" = load i64*, i64** %"rem", !dbg !275
  %".11" = ptrtoint i64* %".10" to i64 , !dbg !275
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 35, i64 %".9", i64 %".11"), !dbg !275
  %".13" = trunc i64 %".12" to i32 , !dbg !275
  ret i32 %".13", !dbg !275
}

define i32 @"sys_gettimeofday"(%"struct.ritz_module_1.Timeval"* %"tv.arg", i8* %"tz.arg") !dbg !67
{
entry:
  %"tv" = alloca %"struct.ritz_module_1.Timeval"*
  store %"struct.ritz_module_1.Timeval"* %"tv.arg", %"struct.ritz_module_1.Timeval"** %"tv"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.Timeval"** %"tv", metadata !278, metadata !7), !dbg !279
  %"tz" = alloca i8*
  store i8* %"tz.arg", i8** %"tz"
  call void @"llvm.dbg.declare"(metadata i8** %"tz", metadata !280, metadata !7), !dbg !279
  %".8" = load %"struct.ritz_module_1.Timeval"*, %"struct.ritz_module_1.Timeval"** %"tv", !dbg !281
  %".9" = ptrtoint %"struct.ritz_module_1.Timeval"* %".8" to i64 , !dbg !281
  %".10" = load i8*, i8** %"tz", !dbg !281
  %".11" = ptrtoint i8* %".10" to i64 , !dbg !281
  %".12" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 96, i64 %".9", i64 %".11"), !dbg !281
  %".13" = trunc i64 %".12" to i32 , !dbg !281
  ret i32 %".13", !dbg !281
}

define i64 @"sys_sendfile"(i32 %"out_fd.arg", i32 %"in_fd.arg", i64* %"offset.arg", i64 %"count.arg") !dbg !68
{
entry:
  %"out_fd" = alloca i32
  store i32 %"out_fd.arg", i32* %"out_fd"
  call void @"llvm.dbg.declare"(metadata i32* %"out_fd", metadata !282, metadata !7), !dbg !283
  %"in_fd" = alloca i32
  store i32 %"in_fd.arg", i32* %"in_fd"
  call void @"llvm.dbg.declare"(metadata i32* %"in_fd", metadata !284, metadata !7), !dbg !283
  %"offset" = alloca i64*
  store i64* %"offset.arg", i64** %"offset"
  call void @"llvm.dbg.declare"(metadata i64** %"offset", metadata !285, metadata !7), !dbg !283
  %"count" = alloca i64
  store i64 %"count.arg", i64* %"count"
  call void @"llvm.dbg.declare"(metadata i64* %"count", metadata !286, metadata !7), !dbg !283
  %".14" = load i32, i32* %"out_fd", !dbg !287
  %".15" = sext i32 %".14" to i64 , !dbg !287
  %".16" = load i32, i32* %"in_fd", !dbg !287
  %".17" = sext i32 %".16" to i64 , !dbg !287
  %".18" = load i64*, i64** %"offset", !dbg !287
  %".19" = ptrtoint i64* %".18" to i64 , !dbg !287
  %".20" = load i64, i64* %"count", !dbg !287
  %".21" = call i64 asm sideeffect "syscall", "=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}"(i64 40, i64 %".15", i64 %".17", i64 %".19", i64 %".20"), !dbg !287
  ret i64 %".21", !dbg !287
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/ritz/ritzlib", filename: "sys.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 328, name: "sys_stat2", scopeLine: 328, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 332, name: "sys_fstat2", scopeLine: 332, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 336, name: "sys_lstat2", scopeLine: 336, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 380, name: "at_fdcwd", scopeLine: 380, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 399, name: "sys_read", scopeLine: 399, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 402, name: "sys_write", scopeLine: 402, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 406, name: "sys_open", scopeLine: 406, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 410, name: "sys_open3", scopeLine: 410, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 414, name: "sys_close", scopeLine: 414, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 418, name: "sys_lseek", scopeLine: 418, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 422, name: "sys_ftruncate", scopeLine: 422, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 430, name: "sys_stat", scopeLine: 430, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 434, name: "sys_fstat", scopeLine: 434, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 438, name: "sys_lstat", scopeLine: 438, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 442, name: "sys_chmod", scopeLine: 442, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 446, name: "sys_fchmod", scopeLine: 446, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 450, name: "sys_chown", scopeLine: 450, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 454, name: "sys_fchown", scopeLine: 454, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 458, name: "sys_access", scopeLine: 458, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 462, name: "sys_utimensat", scopeLine: 462, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 470, name: "sys_mkdir", scopeLine: 470, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 474, name: "sys_rmdir", scopeLine: 474, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 478, name: "sys_getcwd", scopeLine: 478, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 482, name: "sys_chdir", scopeLine: 482, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 486, name: "sys_getdents64", scopeLine: 486, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 494, name: "sys_unlink", scopeLine: 494, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 498, name: "sys_rename", scopeLine: 498, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 502, name: "sys_link", scopeLine: 502, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 506, name: "sys_symlink", scopeLine: 506, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 510, name: "sys_readlink", scopeLine: 510, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 518, name: "sys_mmap", scopeLine: 518, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 522, name: "sys_munmap", scopeLine: 522, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 526, name: "sys_mprotect", scopeLine: 526, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 554, name: "sys_exit", scopeLine: 554, type: !4, unit: !1)
!51 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 559, name: "sys_getpid", scopeLine: 559, type: !4, unit: !1)
!52 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 563, name: "sys_getppid", scopeLine: 563, type: !4, unit: !1)
!53 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 567, name: "sys_getuid", scopeLine: 567, type: !4, unit: !1)
!54 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 571, name: "sys_getgid", scopeLine: 571, type: !4, unit: !1)
!55 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 575, name: "sys_geteuid", scopeLine: 575, type: !4, unit: !1)
!56 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 579, name: "sys_getegid", scopeLine: 579, type: !4, unit: !1)
!57 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 583, name: "sys_fork", scopeLine: 583, type: !4, unit: !1)
!58 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 587, name: "sys_execve", scopeLine: 587, type: !4, unit: !1)
!59 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 591, name: "sys_wait4", scopeLine: 591, type: !4, unit: !1)
!60 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 595, name: "sys_kill", scopeLine: 595, type: !4, unit: !1)
!61 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 603, name: "sys_pipe", scopeLine: 603, type: !4, unit: !1)
!62 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 607, name: "sys_dup", scopeLine: 607, type: !4, unit: !1)
!63 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 611, name: "sys_dup2", scopeLine: 611, type: !4, unit: !1)
!64 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 684, name: "sys_rt_sigaction", scopeLine: 684, type: !4, unit: !1)
!65 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 689, name: "signal_ignore", scopeLine: 689, type: !4, unit: !1)
!66 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 729, name: "sys_nanosleep", scopeLine: 729, type: !4, unit: !1)
!67 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 741, name: "sys_gettimeofday", scopeLine: 741, type: !4, unit: !1)
!68 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 756, name: "sys_sendfile", scopeLine: 756, type: !4, unit: !1)
!69 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!70 = !DILocalVariable(file: !0, line: 328, name: "path", scope: !17, type: !69)
!71 = !DILocation(column: 1, line: 328, scope: !17)
!72 = !DICompositeType(align: 64, file: !0, name: "Stat", size: 1152, tag: DW_TAG_structure_type)
!73 = !DIDerivedType(baseType: !72, size: 64, tag: DW_TAG_pointer_type)
!74 = !DILocalVariable(file: !0, line: 328, name: "statbuf", scope: !17, type: !73)
!75 = !DILocation(column: 5, line: 329, scope: !17)
!76 = !DILocalVariable(file: !0, line: 332, name: "fd", scope: !18, type: !10)
!77 = !DILocation(column: 1, line: 332, scope: !18)
!78 = !DILocalVariable(file: !0, line: 332, name: "statbuf", scope: !18, type: !73)
!79 = !DILocation(column: 5, line: 333, scope: !18)
!80 = !DILocalVariable(file: !0, line: 336, name: "path", scope: !19, type: !69)
!81 = !DILocation(column: 1, line: 336, scope: !19)
!82 = !DILocalVariable(file: !0, line: 336, name: "statbuf", scope: !19, type: !73)
!83 = !DILocation(column: 5, line: 337, scope: !19)
!84 = !DILocation(column: 5, line: 381, scope: !20)
!85 = !DILocalVariable(file: !0, line: 399, name: "fd", scope: !21, type: !10)
!86 = !DILocation(column: 1, line: 399, scope: !21)
!87 = !DILocalVariable(file: !0, line: 399, name: "buf", scope: !21, type: !69)
!88 = !DILocalVariable(file: !0, line: 399, name: "count", scope: !21, type: !11)
!89 = !DILocation(column: 5, line: 400, scope: !21)
!90 = !DILocalVariable(file: !0, line: 402, name: "fd", scope: !22, type: !10)
!91 = !DILocation(column: 1, line: 402, scope: !22)
!92 = !DILocalVariable(file: !0, line: 402, name: "buf", scope: !22, type: !69)
!93 = !DILocalVariable(file: !0, line: 402, name: "count", scope: !22, type: !11)
!94 = !DILocation(column: 5, line: 403, scope: !22)
!95 = !DILocalVariable(file: !0, line: 406, name: "path", scope: !23, type: !69)
!96 = !DILocation(column: 1, line: 406, scope: !23)
!97 = !DILocalVariable(file: !0, line: 406, name: "flags", scope: !23, type: !10)
!98 = !DILocation(column: 5, line: 407, scope: !23)
!99 = !DILocalVariable(file: !0, line: 410, name: "path", scope: !24, type: !69)
!100 = !DILocation(column: 1, line: 410, scope: !24)
!101 = !DILocalVariable(file: !0, line: 410, name: "flags", scope: !24, type: !10)
!102 = !DILocalVariable(file: !0, line: 410, name: "mode", scope: !24, type: !10)
!103 = !DILocation(column: 5, line: 411, scope: !24)
!104 = !DILocalVariable(file: !0, line: 414, name: "fd", scope: !25, type: !10)
!105 = !DILocation(column: 1, line: 414, scope: !25)
!106 = !DILocation(column: 5, line: 415, scope: !25)
!107 = !DILocalVariable(file: !0, line: 418, name: "fd", scope: !26, type: !10)
!108 = !DILocation(column: 1, line: 418, scope: !26)
!109 = !DILocalVariable(file: !0, line: 418, name: "offset", scope: !26, type: !11)
!110 = !DILocalVariable(file: !0, line: 418, name: "whence", scope: !26, type: !10)
!111 = !DILocation(column: 5, line: 419, scope: !26)
!112 = !DILocalVariable(file: !0, line: 422, name: "fd", scope: !27, type: !10)
!113 = !DILocation(column: 1, line: 422, scope: !27)
!114 = !DILocalVariable(file: !0, line: 422, name: "length", scope: !27, type: !11)
!115 = !DILocation(column: 5, line: 423, scope: !27)
!116 = !DILocalVariable(file: !0, line: 430, name: "path", scope: !28, type: !69)
!117 = !DILocation(column: 1, line: 430, scope: !28)
!118 = !DILocalVariable(file: !0, line: 430, name: "statbuf", scope: !28, type: !69)
!119 = !DILocation(column: 5, line: 431, scope: !28)
!120 = !DILocalVariable(file: !0, line: 434, name: "fd", scope: !29, type: !10)
!121 = !DILocation(column: 1, line: 434, scope: !29)
!122 = !DILocalVariable(file: !0, line: 434, name: "statbuf", scope: !29, type: !69)
!123 = !DILocation(column: 5, line: 435, scope: !29)
!124 = !DILocalVariable(file: !0, line: 438, name: "path", scope: !30, type: !69)
!125 = !DILocation(column: 1, line: 438, scope: !30)
!126 = !DILocalVariable(file: !0, line: 438, name: "statbuf", scope: !30, type: !69)
!127 = !DILocation(column: 5, line: 439, scope: !30)
!128 = !DILocalVariable(file: !0, line: 442, name: "path", scope: !31, type: !69)
!129 = !DILocation(column: 1, line: 442, scope: !31)
!130 = !DILocalVariable(file: !0, line: 442, name: "mode", scope: !31, type: !10)
!131 = !DILocation(column: 5, line: 443, scope: !31)
!132 = !DILocalVariable(file: !0, line: 446, name: "fd", scope: !32, type: !10)
!133 = !DILocation(column: 1, line: 446, scope: !32)
!134 = !DILocalVariable(file: !0, line: 446, name: "mode", scope: !32, type: !10)
!135 = !DILocation(column: 5, line: 447, scope: !32)
!136 = !DILocalVariable(file: !0, line: 450, name: "path", scope: !33, type: !69)
!137 = !DILocation(column: 1, line: 450, scope: !33)
!138 = !DILocalVariable(file: !0, line: 450, name: "uid", scope: !33, type: !10)
!139 = !DILocalVariable(file: !0, line: 450, name: "gid", scope: !33, type: !10)
!140 = !DILocation(column: 5, line: 451, scope: !33)
!141 = !DILocalVariable(file: !0, line: 454, name: "fd", scope: !34, type: !10)
!142 = !DILocation(column: 1, line: 454, scope: !34)
!143 = !DILocalVariable(file: !0, line: 454, name: "uid", scope: !34, type: !10)
!144 = !DILocalVariable(file: !0, line: 454, name: "gid", scope: !34, type: !10)
!145 = !DILocation(column: 5, line: 455, scope: !34)
!146 = !DILocalVariable(file: !0, line: 458, name: "path", scope: !35, type: !69)
!147 = !DILocation(column: 1, line: 458, scope: !35)
!148 = !DILocalVariable(file: !0, line: 458, name: "mode", scope: !35, type: !10)
!149 = !DILocation(column: 5, line: 459, scope: !35)
!150 = !DILocalVariable(file: !0, line: 462, name: "dirfd", scope: !36, type: !10)
!151 = !DILocation(column: 1, line: 462, scope: !36)
!152 = !DILocalVariable(file: !0, line: 462, name: "path", scope: !36, type: !69)
!153 = !DIDerivedType(baseType: !11, size: 64, tag: DW_TAG_pointer_type)
!154 = !DILocalVariable(file: !0, line: 462, name: "times", scope: !36, type: !153)
!155 = !DILocalVariable(file: !0, line: 462, name: "flags", scope: !36, type: !10)
!156 = !DILocation(column: 5, line: 463, scope: !36)
!157 = !DILocalVariable(file: !0, line: 470, name: "path", scope: !37, type: !69)
!158 = !DILocation(column: 1, line: 470, scope: !37)
!159 = !DILocalVariable(file: !0, line: 470, name: "mode", scope: !37, type: !10)
!160 = !DILocation(column: 5, line: 471, scope: !37)
!161 = !DILocalVariable(file: !0, line: 474, name: "path", scope: !38, type: !69)
!162 = !DILocation(column: 1, line: 474, scope: !38)
!163 = !DILocation(column: 5, line: 475, scope: !38)
!164 = !DILocalVariable(file: !0, line: 478, name: "buf", scope: !39, type: !69)
!165 = !DILocation(column: 1, line: 478, scope: !39)
!166 = !DILocalVariable(file: !0, line: 478, name: "size", scope: !39, type: !11)
!167 = !DILocation(column: 5, line: 479, scope: !39)
!168 = !DILocalVariable(file: !0, line: 482, name: "path", scope: !40, type: !69)
!169 = !DILocation(column: 1, line: 482, scope: !40)
!170 = !DILocation(column: 5, line: 483, scope: !40)
!171 = !DILocalVariable(file: !0, line: 486, name: "fd", scope: !41, type: !10)
!172 = !DILocation(column: 1, line: 486, scope: !41)
!173 = !DILocalVariable(file: !0, line: 486, name: "dirp", scope: !41, type: !69)
!174 = !DILocalVariable(file: !0, line: 486, name: "count", scope: !41, type: !11)
!175 = !DILocation(column: 5, line: 487, scope: !41)
!176 = !DILocalVariable(file: !0, line: 494, name: "path", scope: !42, type: !69)
!177 = !DILocation(column: 1, line: 494, scope: !42)
!178 = !DILocation(column: 5, line: 495, scope: !42)
!179 = !DILocalVariable(file: !0, line: 498, name: "oldpath", scope: !43, type: !69)
!180 = !DILocation(column: 1, line: 498, scope: !43)
!181 = !DILocalVariable(file: !0, line: 498, name: "newpath", scope: !43, type: !69)
!182 = !DILocation(column: 5, line: 499, scope: !43)
!183 = !DILocalVariable(file: !0, line: 502, name: "oldpath", scope: !44, type: !69)
!184 = !DILocation(column: 1, line: 502, scope: !44)
!185 = !DILocalVariable(file: !0, line: 502, name: "newpath", scope: !44, type: !69)
!186 = !DILocation(column: 5, line: 503, scope: !44)
!187 = !DILocalVariable(file: !0, line: 506, name: "target", scope: !45, type: !69)
!188 = !DILocation(column: 1, line: 506, scope: !45)
!189 = !DILocalVariable(file: !0, line: 506, name: "linkpath", scope: !45, type: !69)
!190 = !DILocation(column: 5, line: 507, scope: !45)
!191 = !DILocalVariable(file: !0, line: 510, name: "path", scope: !46, type: !69)
!192 = !DILocation(column: 1, line: 510, scope: !46)
!193 = !DILocalVariable(file: !0, line: 510, name: "buf", scope: !46, type: !69)
!194 = !DILocalVariable(file: !0, line: 510, name: "size", scope: !46, type: !11)
!195 = !DILocation(column: 5, line: 511, scope: !46)
!196 = !DILocalVariable(file: !0, line: 518, name: "addr", scope: !47, type: !11)
!197 = !DILocation(column: 1, line: 518, scope: !47)
!198 = !DILocalVariable(file: !0, line: 518, name: "length", scope: !47, type: !11)
!199 = !DILocalVariable(file: !0, line: 518, name: "prot", scope: !47, type: !10)
!200 = !DILocalVariable(file: !0, line: 518, name: "flags", scope: !47, type: !10)
!201 = !DILocalVariable(file: !0, line: 518, name: "fd", scope: !47, type: !10)
!202 = !DILocalVariable(file: !0, line: 518, name: "offset", scope: !47, type: !11)
!203 = !DILocation(column: 5, line: 519, scope: !47)
!204 = !DILocalVariable(file: !0, line: 522, name: "addr", scope: !48, type: !69)
!205 = !DILocation(column: 1, line: 522, scope: !48)
!206 = !DILocalVariable(file: !0, line: 522, name: "length", scope: !48, type: !11)
!207 = !DILocation(column: 5, line: 523, scope: !48)
!208 = !DILocalVariable(file: !0, line: 526, name: "addr", scope: !49, type: !69)
!209 = !DILocation(column: 1, line: 526, scope: !49)
!210 = !DILocalVariable(file: !0, line: 526, name: "length", scope: !49, type: !11)
!211 = !DILocalVariable(file: !0, line: 526, name: "prot", scope: !49, type: !10)
!212 = !DILocation(column: 5, line: 527, scope: !49)
!213 = !DILocalVariable(file: !0, line: 554, name: "status", scope: !50, type: !10)
!214 = !DILocation(column: 1, line: 554, scope: !50)
!215 = !DILocation(column: 5, line: 555, scope: !50)
!216 = !DILocation(column: 5, line: 560, scope: !51)
!217 = !DILocation(column: 5, line: 564, scope: !52)
!218 = !DILocation(column: 5, line: 568, scope: !53)
!219 = !DILocation(column: 5, line: 572, scope: !54)
!220 = !DILocation(column: 5, line: 576, scope: !55)
!221 = !DILocation(column: 5, line: 580, scope: !56)
!222 = !DILocation(column: 5, line: 584, scope: !57)
!223 = !DILocalVariable(file: !0, line: 587, name: "path", scope: !58, type: !69)
!224 = !DILocation(column: 1, line: 587, scope: !58)
!225 = !DIDerivedType(baseType: !69, size: 64, tag: DW_TAG_pointer_type)
!226 = !DILocalVariable(file: !0, line: 587, name: "argv", scope: !58, type: !225)
!227 = !DILocalVariable(file: !0, line: 587, name: "envp", scope: !58, type: !225)
!228 = !DILocation(column: 5, line: 588, scope: !58)
!229 = !DILocalVariable(file: !0, line: 591, name: "pid", scope: !59, type: !10)
!230 = !DILocation(column: 1, line: 591, scope: !59)
!231 = !DIDerivedType(baseType: !10, size: 64, tag: DW_TAG_pointer_type)
!232 = !DILocalVariable(file: !0, line: 591, name: "status", scope: !59, type: !231)
!233 = !DILocalVariable(file: !0, line: 591, name: "options", scope: !59, type: !10)
!234 = !DILocalVariable(file: !0, line: 591, name: "rusage", scope: !59, type: !69)
!235 = !DILocation(column: 5, line: 592, scope: !59)
!236 = !DILocalVariable(file: !0, line: 595, name: "pid", scope: !60, type: !10)
!237 = !DILocation(column: 1, line: 595, scope: !60)
!238 = !DILocalVariable(file: !0, line: 595, name: "sig", scope: !60, type: !10)
!239 = !DILocation(column: 5, line: 596, scope: !60)
!240 = !DILocalVariable(file: !0, line: 603, name: "pipefd", scope: !61, type: !231)
!241 = !DILocation(column: 1, line: 603, scope: !61)
!242 = !DILocation(column: 5, line: 604, scope: !61)
!243 = !DILocalVariable(file: !0, line: 607, name: "oldfd", scope: !62, type: !10)
!244 = !DILocation(column: 1, line: 607, scope: !62)
!245 = !DILocation(column: 5, line: 608, scope: !62)
!246 = !DILocalVariable(file: !0, line: 611, name: "oldfd", scope: !63, type: !10)
!247 = !DILocation(column: 1, line: 611, scope: !63)
!248 = !DILocalVariable(file: !0, line: 611, name: "newfd", scope: !63, type: !10)
!249 = !DILocation(column: 5, line: 612, scope: !63)
!250 = !DILocalVariable(file: !0, line: 684, name: "signum", scope: !64, type: !10)
!251 = !DILocation(column: 1, line: 684, scope: !64)
!252 = !DILocalVariable(file: !0, line: 684, name: "act", scope: !64, type: !69)
!253 = !DILocalVariable(file: !0, line: 684, name: "oldact", scope: !64, type: !69)
!254 = !DILocalVariable(file: !0, line: 684, name: "sigsetsize", scope: !64, type: !11)
!255 = !DILocation(column: 5, line: 685, scope: !64)
!256 = !DILocalVariable(file: !0, line: 689, name: "signum", scope: !65, type: !10)
!257 = !DILocation(column: 1, line: 689, scope: !65)
!258 = !DILocation(column: 5, line: 697, scope: !65)
!259 = !DISubrange(count: 32)
!260 = !{ !259 }
!261 = !DICompositeType(baseType: !12, elements: !260, size: 256, tag: DW_TAG_array_type)
!262 = !DILocalVariable(file: !0, line: 697, name: "act", scope: !65, type: !261)
!263 = !DILocation(column: 1, line: 697, scope: !65)
!264 = !DILocation(column: 5, line: 700, scope: !65)
!265 = !DILocalVariable(file: !0, line: 700, name: "i", scope: !65, type: !11)
!266 = !DILocation(column: 1, line: 700, scope: !65)
!267 = !DILocation(column: 5, line: 701, scope: !65)
!268 = !DILocation(column: 9, line: 702, scope: !65)
!269 = !DILocation(column: 9, line: 703, scope: !65)
!270 = !DILocation(column: 5, line: 707, scope: !65)
!271 = !DILocation(column: 5, line: 709, scope: !65)
!272 = !DILocalVariable(file: !0, line: 729, name: "req", scope: !66, type: !153)
!273 = !DILocation(column: 1, line: 729, scope: !66)
!274 = !DILocalVariable(file: !0, line: 729, name: "rem", scope: !66, type: !153)
!275 = !DILocation(column: 5, line: 730, scope: !66)
!276 = !DICompositeType(align: 64, file: !0, name: "Timeval", size: 128, tag: DW_TAG_structure_type)
!277 = !DIDerivedType(baseType: !276, size: 64, tag: DW_TAG_pointer_type)
!278 = !DILocalVariable(file: !0, line: 741, name: "tv", scope: !67, type: !277)
!279 = !DILocation(column: 1, line: 741, scope: !67)
!280 = !DILocalVariable(file: !0, line: 741, name: "tz", scope: !67, type: !69)
!281 = !DILocation(column: 5, line: 742, scope: !67)
!282 = !DILocalVariable(file: !0, line: 756, name: "out_fd", scope: !68, type: !10)
!283 = !DILocation(column: 1, line: 756, scope: !68)
!284 = !DILocalVariable(file: !0, line: 756, name: "in_fd", scope: !68, type: !10)
!285 = !DILocalVariable(file: !0, line: 756, name: "offset", scope: !68, type: !153)
!286 = !DILocalVariable(file: !0, line: 756, name: "count", scope: !68, type: !11)
!287 = !DILocation(column: 5, line: 757, scope: !68)