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
%"struct.ritz_module_1.StrView" = type {i8*, i64}
declare void @"llvm.dbg.declare"(metadata %".1", metadata %".2", metadata %".3")

@"g_alloc" = internal global %"struct.ritz_module_1.GlobalAlloc" zeroinitializer
define i64 @"StrView_len"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !17
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !323, metadata !7), !dbg !324
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !325
  %".6" = call i64 @"strview_len"(%"struct.ritz_module_1.StrView"* %".5"), !dbg !325
  ret i64 %".6", !dbg !325
}

define i32 @"StrView_is_empty"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !18
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !326, metadata !7), !dbg !327
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !328
  %".6" = call i32 @"strview_is_empty"(%"struct.ritz_module_1.StrView"* %".5"), !dbg !328
  ret i32 %".6", !dbg !328
}

define i8 @"StrView_get"(%"struct.ritz_module_1.StrView"* %"self.arg", i64 %"idx.arg") !dbg !19
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !329, metadata !7), !dbg !330
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !331, metadata !7), !dbg !330
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !332
  %".9" = load i64, i64* %"idx", !dbg !332
  %".10" = call i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %".8", i64 %".9"), !dbg !332
  ret i8 %".10", !dbg !332
}

define i8* @"StrView_as_ptr"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !20
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !333, metadata !7), !dbg !334
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !335
  %".6" = call i8* @"strview_as_ptr"(%"struct.ritz_module_1.StrView"* %".5"), !dbg !335
  ret i8* %".6", !dbg !335
}

define %"struct.ritz_module_1.StrView" @"StrView_slice"(%"struct.ritz_module_1.StrView"* %"self.arg", i64 %"start.arg", i64 %"end.arg") !dbg !21
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !336, metadata !7), !dbg !337
  %"start" = alloca i64
  store i64 %"start.arg", i64* %"start"
  call void @"llvm.dbg.declare"(metadata i64* %"start", metadata !338, metadata !7), !dbg !337
  %"end" = alloca i64
  store i64 %"end.arg", i64* %"end"
  call void @"llvm.dbg.declare"(metadata i64* %"end", metadata !339, metadata !7), !dbg !337
  %".11" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !340
  %".12" = load i64, i64* %"start", !dbg !340
  %".13" = load i64, i64* %"end", !dbg !340
  %".14" = call %"struct.ritz_module_1.StrView" @"strview_slice"(%"struct.ritz_module_1.StrView"* %".11", i64 %".12", i64 %".13"), !dbg !340
  ret %"struct.ritz_module_1.StrView" %".14", !dbg !340
}

define %"struct.ritz_module_1.StrView" @"StrView_take"(%"struct.ritz_module_1.StrView"* %"self.arg", i64 %"n.arg") !dbg !22
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !341, metadata !7), !dbg !342
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !343, metadata !7), !dbg !342
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !344
  %".9" = load i64, i64* %"n", !dbg !344
  %".10" = call %"struct.ritz_module_1.StrView" @"strview_take"(%"struct.ritz_module_1.StrView"* %".8", i64 %".9"), !dbg !344
  ret %"struct.ritz_module_1.StrView" %".10", !dbg !344
}

define %"struct.ritz_module_1.StrView" @"StrView_skip"(%"struct.ritz_module_1.StrView"* %"self.arg", i64 %"n.arg") !dbg !23
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !345, metadata !7), !dbg !346
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !347, metadata !7), !dbg !346
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !348
  %".9" = load i64, i64* %"n", !dbg !348
  %".10" = call %"struct.ritz_module_1.StrView" @"strview_skip"(%"struct.ritz_module_1.StrView"* %".8", i64 %".9"), !dbg !348
  ret %"struct.ritz_module_1.StrView" %".10", !dbg !348
}

define i32 @"StrView_starts_with"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"prefix.arg") !dbg !24
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !349, metadata !7), !dbg !350
  %"prefix" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"prefix.arg", %"struct.ritz_module_1.StrView"** %"prefix"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"prefix", metadata !351, metadata !7), !dbg !350
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !352
  %".9" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"prefix", !dbg !352
  %".10" = call i32 @"strview_starts_with"(%"struct.ritz_module_1.StrView"* %".8", %"struct.ritz_module_1.StrView"* %".9"), !dbg !352
  ret i32 %".10", !dbg !352
}

define i32 @"StrView_ends_with"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"suffix.arg") !dbg !25
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !353, metadata !7), !dbg !354
  %"suffix" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"suffix.arg", %"struct.ritz_module_1.StrView"** %"suffix"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"suffix", metadata !355, metadata !7), !dbg !354
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !356
  %".9" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"suffix", !dbg !356
  %".10" = call i32 @"strview_ends_with"(%"struct.ritz_module_1.StrView"* %".8", %"struct.ritz_module_1.StrView"* %".9"), !dbg !356
  ret i32 %".10", !dbg !356
}

define i32 @"StrView_contains"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"needle.arg") !dbg !26
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !357, metadata !7), !dbg !358
  %"needle" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"needle.arg", %"struct.ritz_module_1.StrView"** %"needle"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"needle", metadata !359, metadata !7), !dbg !358
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !360
  %".9" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"needle", !dbg !360
  %".10" = call i32 @"strview_contains"(%"struct.ritz_module_1.StrView"* %".8", %"struct.ritz_module_1.StrView"* %".9"), !dbg !360
  ret i32 %".10", !dbg !360
}

define i64 @"StrView_find"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"needle.arg") !dbg !27
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !361, metadata !7), !dbg !362
  %"needle" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"needle.arg", %"struct.ritz_module_1.StrView"** %"needle"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"needle", metadata !363, metadata !7), !dbg !362
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !364
  %".9" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"needle", !dbg !364
  %".10" = call i64 @"strview_find"(%"struct.ritz_module_1.StrView"* %".8", %"struct.ritz_module_1.StrView"* %".9"), !dbg !364
  ret i64 %".10", !dbg !364
}

define i64 @"StrView_find_byte"(%"struct.ritz_module_1.StrView"* %"self.arg", i8 %"c.arg") !dbg !28
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !365, metadata !7), !dbg !366
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !367, metadata !7), !dbg !366
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !368
  %".9" = load i8, i8* %"c", !dbg !368
  %".10" = call i64 @"strview_find_byte"(%"struct.ritz_module_1.StrView"* %".8", i8 %".9"), !dbg !368
  ret i64 %".10", !dbg !368
}

define %"struct.ritz_module_1.StrView" @"StrView_trim"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !29
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !369, metadata !7), !dbg !370
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !371
  %".6" = call %"struct.ritz_module_1.StrView" @"strview_trim"(%"struct.ritz_module_1.StrView"* %".5"), !dbg !371
  ret %"struct.ritz_module_1.StrView" %".6", !dbg !371
}

define %"struct.ritz_module_1.StrView" @"StrView_trim_start"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !30
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !372, metadata !7), !dbg !373
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !374
  %".6" = call %"struct.ritz_module_1.StrView" @"strview_trim_start"(%"struct.ritz_module_1.StrView"* %".5"), !dbg !374
  ret %"struct.ritz_module_1.StrView" %".6", !dbg !374
}

define %"struct.ritz_module_1.StrView" @"StrView_trim_end"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !31
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !375, metadata !7), !dbg !376
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !377
  %".6" = call %"struct.ritz_module_1.StrView" @"strview_trim_end"(%"struct.ritz_module_1.StrView"* %".5"), !dbg !377
  ret %"struct.ritz_module_1.StrView" %".6", !dbg !377
}

define i32 @"StrView_eq"(%"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"* %"other.arg") !dbg !32
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !378, metadata !7), !dbg !379
  %"other" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"other.arg", %"struct.ritz_module_1.StrView"** %"other"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"other", metadata !380, metadata !7), !dbg !379
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !381
  %".9" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"other", !dbg !381
  %".10" = call i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %".8", %"struct.ritz_module_1.StrView"* %".9"), !dbg !381
  ret i32 %".10", !dbg !381
}

define i32 @"StrView_eq_cstr"(%"struct.ritz_module_1.StrView"* %"self.arg", i8* %"cstr.arg") !dbg !33
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !382, metadata !7), !dbg !383
  %"cstr" = alloca i8*
  store i8* %"cstr.arg", i8** %"cstr"
  call void @"llvm.dbg.declare"(metadata i8** %"cstr", metadata !384, metadata !7), !dbg !383
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !385
  %".9" = load i8*, i8** %"cstr", !dbg !385
  %".10" = call i32 @"strview_eq_cstr"(%"struct.ritz_module_1.StrView"* %".8", i8* %".9"), !dbg !385
  ret i32 %".10", !dbg !385
}

define i8* @"StrView_to_cstr"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !34
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !386, metadata !7), !dbg !387
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !388
  %".6" = call i8* @"strview_to_cstr"(%"struct.ritz_module_1.StrView"* %".5"), !dbg !388
  ret i8* %".6", !dbg !388
}

define i8* @"StrView_as_cstr_unchecked"(%"struct.ritz_module_1.StrView"* %"self.arg") !dbg !35
{
entry:
  %"self" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"self.arg", %"struct.ritz_module_1.StrView"** %"self"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"self", metadata !389, metadata !7), !dbg !390
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"self", !dbg !391
  %".6" = call i8* @"strview_as_cstr_unchecked"(%"struct.ritz_module_1.StrView"* %".5"), !dbg !391
  ret i8* %".6", !dbg !391
}

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

define %"struct.ritz_module_1.StrView" @"strview_empty"() !dbg !36
{
entry:
  %"s.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !60
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.addr", metadata !62, metadata !7), !dbg !63
  %".3" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !64
  %".4" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", i32 0, i32 0 , !dbg !64
  store i8* null, i8** %".4", !dbg !64
  %".6" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !65
  %".7" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", i32 0, i32 1 , !dbg !65
  store i64 0, i64* %".7", !dbg !65
  %".9" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !66
  ret %"struct.ritz_module_1.StrView" %".9", !dbg !66
}

define %"struct.ritz_module_1.StrView" @"strview_from_ptr"(i8* %"ptr.arg", i64 %"len.arg") !dbg !37
{
entry:
  %"ptr" = alloca i8*
  %"s.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !71
  store i8* %"ptr.arg", i8** %"ptr"
  call void @"llvm.dbg.declare"(metadata i8** %"ptr", metadata !68, metadata !7), !dbg !69
  %"len" = alloca i64
  store i64 %"len.arg", i64* %"len"
  call void @"llvm.dbg.declare"(metadata i64* %"len", metadata !70, metadata !7), !dbg !69
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.addr", metadata !72, metadata !7), !dbg !73
  %".9" = load i8*, i8** %"ptr", !dbg !74
  %".10" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !74
  %".11" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", i32 0, i32 0 , !dbg !74
  store i8* %".9", i8** %".11", !dbg !74
  %".13" = load i64, i64* %"len", !dbg !75
  %".14" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !75
  %".15" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", i32 0, i32 1 , !dbg !75
  store i64 %".13", i64* %".15", !dbg !75
  %".17" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !76
  ret %"struct.ritz_module_1.StrView" %".17", !dbg !76
}

define %"struct.ritz_module_1.StrView" @"strview_from_cstr"(i8* %"cstr.arg") !dbg !38
{
entry:
  %"cstr" = alloca i8*
  %"s.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !79
  store i8* %"cstr.arg", i8** %"cstr"
  call void @"llvm.dbg.declare"(metadata i8** %"cstr", metadata !77, metadata !7), !dbg !78
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"s.addr", metadata !80, metadata !7), !dbg !81
  %".6" = load i8*, i8** %"cstr", !dbg !82
  %".7" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !82
  %".8" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", i32 0, i32 0 , !dbg !82
  store i8* %".6", i8** %".8", !dbg !82
  %".10" = load i8*, i8** %"cstr", !dbg !83
  %".11" = call i64 @"strlen"(i8* %".10"), !dbg !83
  %".12" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !83
  %".13" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", i32 0, i32 1 , !dbg !83
  store i64 %".11", i64* %".13", !dbg !83
  %".15" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"s.addr", !dbg !84
  ret %"struct.ritz_module_1.StrView" %".15", !dbg !84
}

define i64 @"strview_len"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !39
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !86, metadata !7), !dbg !87
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !88
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".5", i32 0, i32 1 , !dbg !88
  %".7" = load i64, i64* %".6", !dbg !88
  ret i64 %".7", !dbg !88
}

define i32 @"strview_is_empty"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !40
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !89, metadata !7), !dbg !90
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !91
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".5", i32 0, i32 1 , !dbg !91
  %".7" = load i64, i64* %".6", !dbg !91
  %".8" = icmp eq i64 %".7", 0 , !dbg !91
  br i1 %".8", label %"if.then", label %"if.end", !dbg !91
if.then:
  %".10" = trunc i64 1 to i32 , !dbg !92
  ret i32 %".10", !dbg !92
if.end:
  %".12" = trunc i64 0 to i32 , !dbg !93
  ret i32 %".12", !dbg !93
}

define i8 @"strview_get"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %"idx.arg") !dbg !41
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !94, metadata !7), !dbg !95
  %"idx" = alloca i64
  store i64 %"idx.arg", i64* %"idx"
  call void @"llvm.dbg.declare"(metadata i64* %"idx", metadata !96, metadata !7), !dbg !95
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !97
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".8", i32 0, i32 0 , !dbg !97
  %".10" = load i8*, i8** %".9", !dbg !97
  %".11" = load i64, i64* %"idx", !dbg !97
  %".12" = getelementptr i8, i8* %".10", i64 %".11" , !dbg !97
  %".13" = load i8, i8* %".12", !dbg !97
  ret i8 %".13", !dbg !97
}

define i8* @"strview_as_ptr"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !42
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !98, metadata !7), !dbg !99
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !100
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".5", i32 0, i32 0 , !dbg !100
  %".7" = load i8*, i8** %".6", !dbg !100
  ret i8* %".7", !dbg !100
}

define i8* @"strview_to_cstr"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !43
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !101, metadata !7), !dbg !102
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !103
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".5", i32 0, i32 1 , !dbg !103
  %".7" = load i64, i64* %".6", !dbg !103
  %".8" = add i64 %".7", 1, !dbg !103
  %".9" = call i8* @"malloc"(i64 %".8"), !dbg !103
  %".10" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !104
  %".11" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".10", i32 0, i32 0 , !dbg !104
  %".12" = load i8*, i8** %".11", !dbg !104
  %".13" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !104
  %".14" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".13", i32 0, i32 1 , !dbg !104
  %".15" = load i64, i64* %".14", !dbg !104
  %".16" = call i8* @"memcpy"(i8* %".9", i8* %".12", i64 %".15"), !dbg !104
  %".17" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !105
  %".18" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".17", i32 0, i32 1 , !dbg !105
  %".19" = load i64, i64* %".18", !dbg !105
  %".20" = getelementptr i8, i8* %".9", i64 %".19" , !dbg !105
  %".21" = trunc i64 0 to i8 , !dbg !105
  store i8 %".21", i8* %".20", !dbg !105
  ret i8* %".9", !dbg !106
}

define i8* @"strview_as_cstr_unchecked"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !44
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !107, metadata !7), !dbg !108
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !109
  %".6" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".5", i32 0, i32 0 , !dbg !109
  %".7" = load i8*, i8** %".6", !dbg !109
  ret i8* %".7", !dbg !109
}

define i32 @"strview_eq"(%"struct.ritz_module_1.StrView"* %"a.arg", %"struct.ritz_module_1.StrView"* %"b.arg") !dbg !45
{
entry:
  %"a" = alloca %"struct.ritz_module_1.StrView"*
  %"i" = alloca i64, !dbg !117
  store %"struct.ritz_module_1.StrView"* %"a.arg", %"struct.ritz_module_1.StrView"** %"a"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"a", metadata !110, metadata !7), !dbg !111
  %"b" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"b.arg", %"struct.ritz_module_1.StrView"** %"b"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"b", metadata !112, metadata !7), !dbg !111
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"a", !dbg !113
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".8", i32 0, i32 1 , !dbg !113
  %".10" = load i64, i64* %".9", !dbg !113
  %".11" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"b", !dbg !113
  %".12" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".11", i32 0, i32 1 , !dbg !113
  %".13" = load i64, i64* %".12", !dbg !113
  %".14" = icmp ne i64 %".10", %".13" , !dbg !113
  br i1 %".14", label %"if.then", label %"if.end", !dbg !113
if.then:
  %".16" = trunc i64 0 to i32 , !dbg !114
  ret i32 %".16", !dbg !114
if.end:
  %".18" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"a", !dbg !115
  %".19" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".18", i32 0, i32 1 , !dbg !115
  %".20" = load i64, i64* %".19", !dbg !115
  %".21" = icmp eq i64 %".20", 0 , !dbg !115
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !115
if.then.1:
  %".23" = trunc i64 1 to i32 , !dbg !116
  ret i32 %".23", !dbg !116
if.end.1:
  %".25" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"a", !dbg !117
  %".26" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".25", i32 0, i32 1 , !dbg !117
  %".27" = load i64, i64* %".26", !dbg !117
  store i64 0, i64* %"i", !dbg !117
  br label %"for.cond", !dbg !117
for.cond:
  %".30" = load i64, i64* %"i", !dbg !117
  %".31" = icmp slt i64 %".30", %".27" , !dbg !117
  br i1 %".31", label %"for.body", label %"for.end", !dbg !117
for.body:
  %".33" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"a", !dbg !117
  %".34" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".33", i32 0, i32 0 , !dbg !117
  %".35" = load i8*, i8** %".34", !dbg !117
  %".36" = load i64, i64* %"i", !dbg !117
  %".37" = getelementptr i8, i8* %".35", i64 %".36" , !dbg !117
  %".38" = load i8, i8* %".37", !dbg !117
  %".39" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"b", !dbg !117
  %".40" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".39", i32 0, i32 0 , !dbg !117
  %".41" = load i8*, i8** %".40", !dbg !117
  %".42" = load i64, i64* %"i", !dbg !117
  %".43" = getelementptr i8, i8* %".41", i64 %".42" , !dbg !117
  %".44" = load i8, i8* %".43", !dbg !117
  %".45" = icmp ne i8 %".38", %".44" , !dbg !117
  br i1 %".45", label %"if.then.2", label %"if.end.2", !dbg !117
for.incr:
  %".50" = load i64, i64* %"i", !dbg !118
  %".51" = add i64 %".50", 1, !dbg !118
  store i64 %".51", i64* %"i", !dbg !118
  br label %"for.cond", !dbg !118
for.end:
  %".54" = trunc i64 1 to i32 , !dbg !119
  ret i32 %".54", !dbg !119
if.then.2:
  %".47" = trunc i64 0 to i32 , !dbg !118
  ret i32 %".47", !dbg !118
if.end.2:
  br label %"for.incr", !dbg !118
}

define i32 @"strview_eq_cstr"(%"struct.ritz_module_1.StrView"* %"s.arg", i8* %"cstr.arg") !dbg !46
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  %"i.addr" = alloca i64, !dbg !123
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !120, metadata !7), !dbg !121
  %"cstr" = alloca i8*
  store i8* %"cstr.arg", i8** %"cstr"
  call void @"llvm.dbg.declare"(metadata i8** %"cstr", metadata !122, metadata !7), !dbg !121
  store i64 0, i64* %"i.addr", !dbg !123
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !124, metadata !7), !dbg !125
  br label %"while.cond", !dbg !126
while.cond:
  %".11" = load i64, i64* %"i.addr", !dbg !126
  %".12" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !126
  %".13" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".12", i32 0, i32 1 , !dbg !126
  %".14" = load i64, i64* %".13", !dbg !126
  %".15" = icmp slt i64 %".11", %".14" , !dbg !126
  br i1 %".15", label %"while.body", label %"while.end", !dbg !126
while.body:
  %".17" = load i8*, i8** %"cstr", !dbg !127
  %".18" = load i64, i64* %"i.addr", !dbg !127
  %".19" = getelementptr i8, i8* %".17", i64 %".18" , !dbg !127
  %".20" = load i8, i8* %".19", !dbg !127
  %".21" = zext i8 %".20" to i64 , !dbg !127
  %".22" = icmp eq i64 %".21", 0 , !dbg !127
  br i1 %".22", label %"if.then", label %"if.end", !dbg !127
while.end:
  %".44" = load i8*, i8** %"cstr", !dbg !132
  %".45" = load i64, i64* %"i.addr", !dbg !132
  %".46" = getelementptr i8, i8* %".44", i64 %".45" , !dbg !132
  %".47" = load i8, i8* %".46", !dbg !132
  %".48" = zext i8 %".47" to i64 , !dbg !132
  %".49" = icmp ne i64 %".48", 0 , !dbg !132
  br i1 %".49", label %"if.then.2", label %"if.end.2", !dbg !132
if.then:
  %".24" = trunc i64 0 to i32 , !dbg !128
  ret i32 %".24", !dbg !128
if.end:
  %".26" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !129
  %".27" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".26", i32 0, i32 0 , !dbg !129
  %".28" = load i8*, i8** %".27", !dbg !129
  %".29" = load i64, i64* %"i.addr", !dbg !129
  %".30" = getelementptr i8, i8* %".28", i64 %".29" , !dbg !129
  %".31" = load i8, i8* %".30", !dbg !129
  %".32" = load i8*, i8** %"cstr", !dbg !129
  %".33" = load i64, i64* %"i.addr", !dbg !129
  %".34" = getelementptr i8, i8* %".32", i64 %".33" , !dbg !129
  %".35" = load i8, i8* %".34", !dbg !129
  %".36" = icmp ne i8 %".31", %".35" , !dbg !129
  br i1 %".36", label %"if.then.1", label %"if.end.1", !dbg !129
if.then.1:
  %".38" = trunc i64 0 to i32 , !dbg !130
  ret i32 %".38", !dbg !130
if.end.1:
  %".40" = load i64, i64* %"i.addr", !dbg !131
  %".41" = add i64 %".40", 1, !dbg !131
  store i64 %".41", i64* %"i.addr", !dbg !131
  br label %"while.cond", !dbg !131
if.then.2:
  %".51" = trunc i64 0 to i32 , !dbg !133
  ret i32 %".51", !dbg !133
if.end.2:
  %".53" = trunc i64 1 to i32 , !dbg !134
  ret i32 %".53", !dbg !134
}

define %"struct.ritz_module_1.StrView" @"strview_slice"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %"start.arg", i64 %"end.arg") !dbg !47
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  %"result.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !139
  %"st.addr" = alloca i64, !dbg !142
  %"en.addr" = alloca i64, !dbg !145
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !135, metadata !7), !dbg !136
  %"start" = alloca i64
  store i64 %"start.arg", i64* %"start"
  call void @"llvm.dbg.declare"(metadata i64* %"start", metadata !137, metadata !7), !dbg !136
  %"end" = alloca i64
  store i64 %"end.arg", i64* %"end"
  call void @"llvm.dbg.declare"(metadata i64* %"end", metadata !138, metadata !7), !dbg !136
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"result.addr", metadata !140, metadata !7), !dbg !141
  %".12" = load i64, i64* %"start", !dbg !142
  store i64 %".12", i64* %"st.addr", !dbg !142
  call void @"llvm.dbg.declare"(metadata i64* %"st.addr", metadata !143, metadata !7), !dbg !144
  %".15" = load i64, i64* %"end", !dbg !145
  store i64 %".15", i64* %"en.addr", !dbg !145
  call void @"llvm.dbg.declare"(metadata i64* %"en.addr", metadata !146, metadata !7), !dbg !147
  %".18" = load i64, i64* %"st.addr", !dbg !148
  %".19" = icmp slt i64 %".18", 0 , !dbg !148
  br i1 %".19", label %"if.then", label %"if.end", !dbg !148
if.then:
  store i64 0, i64* %"st.addr", !dbg !149
  br label %"if.end", !dbg !149
if.end:
  %".23" = load i64, i64* %"en.addr", !dbg !150
  %".24" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !150
  %".25" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".24", i32 0, i32 1 , !dbg !150
  %".26" = load i64, i64* %".25", !dbg !150
  %".27" = icmp sgt i64 %".23", %".26" , !dbg !150
  br i1 %".27", label %"if.then.1", label %"if.end.1", !dbg !150
if.then.1:
  %".29" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !151
  %".30" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".29", i32 0, i32 1 , !dbg !151
  %".31" = load i64, i64* %".30", !dbg !151
  store i64 %".31", i64* %"en.addr", !dbg !151
  br label %"if.end.1", !dbg !151
if.end.1:
  %".34" = load i64, i64* %"st.addr", !dbg !152
  %".35" = load i64, i64* %"en.addr", !dbg !152
  %".36" = icmp sge i64 %".34", %".35" , !dbg !152
  br i1 %".36", label %"if.then.2", label %"if.end.2", !dbg !152
if.then.2:
  %".38" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !153
  %".39" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !153
  store i8* null, i8** %".39", !dbg !153
  %".41" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !154
  %".42" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !154
  store i64 0, i64* %".42", !dbg !154
  %".44" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !155
  ret %"struct.ritz_module_1.StrView" %".44", !dbg !155
if.end.2:
  %".46" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !156
  %".47" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".46", i32 0, i32 0 , !dbg !156
  %".48" = load i8*, i8** %".47", !dbg !156
  %".49" = load i64, i64* %"st.addr", !dbg !156
  %".50" = getelementptr i8, i8* %".48", i64 %".49" , !dbg !156
  %".51" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !156
  %".52" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !156
  store i8* %".50", i8** %".52", !dbg !156
  %".54" = load i64, i64* %"en.addr", !dbg !157
  %".55" = load i64, i64* %"st.addr", !dbg !157
  %".56" = sub i64 %".54", %".55", !dbg !157
  %".57" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !157
  %".58" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !157
  store i64 %".56", i64* %".58", !dbg !157
  %".60" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !158
  ret %"struct.ritz_module_1.StrView" %".60", !dbg !158
}

define %"struct.ritz_module_1.StrView" @"strview_take"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %"n.arg") !dbg !48
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  %"result.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !162
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !159, metadata !7), !dbg !160
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !161, metadata !7), !dbg !160
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"result.addr", metadata !163, metadata !7), !dbg !164
  %".9" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !165
  %".10" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".9", i32 0, i32 0 , !dbg !165
  %".11" = load i8*, i8** %".10", !dbg !165
  %".12" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !165
  %".13" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !165
  store i8* %".11", i8** %".13", !dbg !165
  %".15" = load i64, i64* %"n", !dbg !166
  %".16" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !166
  %".17" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".16", i32 0, i32 1 , !dbg !166
  %".18" = load i64, i64* %".17", !dbg !166
  %".19" = icmp slt i64 %".15", %".18" , !dbg !166
  br i1 %".19", label %"if.then", label %"if.else", !dbg !166
if.then:
  %".21" = load i64, i64* %"n", !dbg !167
  %".22" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !167
  %".23" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !167
  store i64 %".21", i64* %".23", !dbg !167
  br label %"if.end", !dbg !168
if.else:
  %".25" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !168
  %".26" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".25", i32 0, i32 1 , !dbg !168
  %".27" = load i64, i64* %".26", !dbg !168
  %".28" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !168
  %".29" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !168
  store i64 %".27", i64* %".29", !dbg !168
  br label %"if.end", !dbg !168
if.end:
  %".33" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !169
  ret %"struct.ritz_module_1.StrView" %".33", !dbg !169
}

define %"struct.ritz_module_1.StrView" @"strview_skip"(%"struct.ritz_module_1.StrView"* %"s.arg", i64 %"n.arg") !dbg !49
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  %"result.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !173
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !170, metadata !7), !dbg !171
  %"n" = alloca i64
  store i64 %"n.arg", i64* %"n"
  call void @"llvm.dbg.declare"(metadata i64* %"n", metadata !172, metadata !7), !dbg !171
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"result.addr", metadata !174, metadata !7), !dbg !175
  %".9" = load i64, i64* %"n", !dbg !176
  %".10" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !176
  %".11" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".10", i32 0, i32 1 , !dbg !176
  %".12" = load i64, i64* %".11", !dbg !176
  %".13" = icmp sge i64 %".9", %".12" , !dbg !176
  br i1 %".13", label %"if.then", label %"if.else", !dbg !176
if.then:
  %".15" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !177
  %".16" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".15", i32 0, i32 0 , !dbg !177
  %".17" = load i8*, i8** %".16", !dbg !177
  %".18" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !177
  %".19" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".18", i32 0, i32 1 , !dbg !177
  %".20" = load i64, i64* %".19", !dbg !177
  %".21" = getelementptr i8, i8* %".17", i64 %".20" , !dbg !177
  %".22" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !177
  %".23" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !177
  store i8* %".21", i8** %".23", !dbg !177
  %".25" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !178
  %".26" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !178
  store i64 0, i64* %".26", !dbg !178
  br label %"if.end", !dbg !180
if.else:
  %".28" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !179
  %".29" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".28", i32 0, i32 0 , !dbg !179
  %".30" = load i8*, i8** %".29", !dbg !179
  %".31" = load i64, i64* %"n", !dbg !179
  %".32" = getelementptr i8, i8* %".30", i64 %".31" , !dbg !179
  %".33" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !179
  %".34" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !179
  store i8* %".32", i8** %".34", !dbg !179
  %".36" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !180
  %".37" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".36", i32 0, i32 1 , !dbg !180
  %".38" = load i64, i64* %".37", !dbg !180
  %".39" = load i64, i64* %"n", !dbg !180
  %".40" = sub i64 %".38", %".39", !dbg !180
  %".41" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !180
  %".42" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !180
  store i64 %".40", i64* %".42", !dbg !180
  br label %"if.end", !dbg !180
if.end:
  %".46" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !181
  ret %"struct.ritz_module_1.StrView" %".46", !dbg !181
}

define i32 @"strview_starts_with"(%"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"* %"prefix.arg") !dbg !50
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  %"i" = alloca i64, !dbg !187
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !182, metadata !7), !dbg !183
  %"prefix" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"prefix.arg", %"struct.ritz_module_1.StrView"** %"prefix"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"prefix", metadata !184, metadata !7), !dbg !183
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"prefix", !dbg !185
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".8", i32 0, i32 1 , !dbg !185
  %".10" = load i64, i64* %".9", !dbg !185
  %".11" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !185
  %".12" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".11", i32 0, i32 1 , !dbg !185
  %".13" = load i64, i64* %".12", !dbg !185
  %".14" = icmp sgt i64 %".10", %".13" , !dbg !185
  br i1 %".14", label %"if.then", label %"if.end", !dbg !185
if.then:
  %".16" = trunc i64 0 to i32 , !dbg !186
  ret i32 %".16", !dbg !186
if.end:
  %".18" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"prefix", !dbg !187
  %".19" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".18", i32 0, i32 1 , !dbg !187
  %".20" = load i64, i64* %".19", !dbg !187
  store i64 0, i64* %"i", !dbg !187
  br label %"for.cond", !dbg !187
for.cond:
  %".23" = load i64, i64* %"i", !dbg !187
  %".24" = icmp slt i64 %".23", %".20" , !dbg !187
  br i1 %".24", label %"for.body", label %"for.end", !dbg !187
for.body:
  %".26" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !187
  %".27" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".26", i32 0, i32 0 , !dbg !187
  %".28" = load i8*, i8** %".27", !dbg !187
  %".29" = load i64, i64* %"i", !dbg !187
  %".30" = getelementptr i8, i8* %".28", i64 %".29" , !dbg !187
  %".31" = load i8, i8* %".30", !dbg !187
  %".32" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"prefix", !dbg !187
  %".33" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".32", i32 0, i32 0 , !dbg !187
  %".34" = load i8*, i8** %".33", !dbg !187
  %".35" = load i64, i64* %"i", !dbg !187
  %".36" = getelementptr i8, i8* %".34", i64 %".35" , !dbg !187
  %".37" = load i8, i8* %".36", !dbg !187
  %".38" = icmp ne i8 %".31", %".37" , !dbg !187
  br i1 %".38", label %"if.then.1", label %"if.end.1", !dbg !187
for.incr:
  %".43" = load i64, i64* %"i", !dbg !188
  %".44" = add i64 %".43", 1, !dbg !188
  store i64 %".44", i64* %"i", !dbg !188
  br label %"for.cond", !dbg !188
for.end:
  %".47" = trunc i64 1 to i32 , !dbg !189
  ret i32 %".47", !dbg !189
if.then.1:
  %".40" = trunc i64 0 to i32 , !dbg !188
  ret i32 %".40", !dbg !188
if.end.1:
  br label %"for.incr", !dbg !188
}

define i32 @"strview_starts_with_cstr"(%"struct.ritz_module_1.StrView"* %"s.arg", i8* %"prefix.arg") !dbg !51
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  %"i.addr" = alloca i64, !dbg !193
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !190, metadata !7), !dbg !191
  %"prefix" = alloca i8*
  store i8* %"prefix.arg", i8** %"prefix"
  call void @"llvm.dbg.declare"(metadata i8** %"prefix", metadata !192, metadata !7), !dbg !191
  store i64 0, i64* %"i.addr", !dbg !193
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !194, metadata !7), !dbg !195
  br label %"while.cond", !dbg !196
while.cond:
  %".11" = load i8*, i8** %"prefix", !dbg !196
  %".12" = load i64, i64* %"i.addr", !dbg !196
  %".13" = getelementptr i8, i8* %".11", i64 %".12" , !dbg !196
  %".14" = load i8, i8* %".13", !dbg !196
  %".15" = zext i8 %".14" to i64 , !dbg !196
  %".16" = icmp ne i64 %".15", 0 , !dbg !196
  br i1 %".16", label %"while.body", label %"while.end", !dbg !196
while.body:
  %".18" = load i64, i64* %"i.addr", !dbg !197
  %".19" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !197
  %".20" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".19", i32 0, i32 1 , !dbg !197
  %".21" = load i64, i64* %".20", !dbg !197
  %".22" = icmp sge i64 %".18", %".21" , !dbg !197
  br i1 %".22", label %"if.then", label %"if.end", !dbg !197
while.end:
  %".44" = trunc i64 1 to i32 , !dbg !202
  ret i32 %".44", !dbg !202
if.then:
  %".24" = trunc i64 0 to i32 , !dbg !198
  ret i32 %".24", !dbg !198
if.end:
  %".26" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !199
  %".27" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".26", i32 0, i32 0 , !dbg !199
  %".28" = load i8*, i8** %".27", !dbg !199
  %".29" = load i64, i64* %"i.addr", !dbg !199
  %".30" = getelementptr i8, i8* %".28", i64 %".29" , !dbg !199
  %".31" = load i8, i8* %".30", !dbg !199
  %".32" = load i8*, i8** %"prefix", !dbg !199
  %".33" = load i64, i64* %"i.addr", !dbg !199
  %".34" = getelementptr i8, i8* %".32", i64 %".33" , !dbg !199
  %".35" = load i8, i8* %".34", !dbg !199
  %".36" = icmp ne i8 %".31", %".35" , !dbg !199
  br i1 %".36", label %"if.then.1", label %"if.end.1", !dbg !199
if.then.1:
  %".38" = trunc i64 0 to i32 , !dbg !200
  ret i32 %".38", !dbg !200
if.end.1:
  %".40" = load i64, i64* %"i.addr", !dbg !201
  %".41" = add i64 %".40", 1, !dbg !201
  store i64 %".41", i64* %"i.addr", !dbg !201
  br label %"while.cond", !dbg !201
}

define i32 @"strview_ends_with"(%"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"* %"suffix.arg") !dbg !52
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  %"i" = alloca i64, !dbg !209
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !203, metadata !7), !dbg !204
  %"suffix" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"suffix.arg", %"struct.ritz_module_1.StrView"** %"suffix"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"suffix", metadata !205, metadata !7), !dbg !204
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"suffix", !dbg !206
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".8", i32 0, i32 1 , !dbg !206
  %".10" = load i64, i64* %".9", !dbg !206
  %".11" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !206
  %".12" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".11", i32 0, i32 1 , !dbg !206
  %".13" = load i64, i64* %".12", !dbg !206
  %".14" = icmp sgt i64 %".10", %".13" , !dbg !206
  br i1 %".14", label %"if.then", label %"if.end", !dbg !206
if.then:
  %".16" = trunc i64 0 to i32 , !dbg !207
  ret i32 %".16", !dbg !207
if.end:
  %".18" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !208
  %".19" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".18", i32 0, i32 1 , !dbg !208
  %".20" = load i64, i64* %".19", !dbg !208
  %".21" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"suffix", !dbg !208
  %".22" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".21", i32 0, i32 1 , !dbg !208
  %".23" = load i64, i64* %".22", !dbg !208
  %".24" = sub i64 %".20", %".23", !dbg !208
  %".25" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"suffix", !dbg !209
  %".26" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".25", i32 0, i32 1 , !dbg !209
  %".27" = load i64, i64* %".26", !dbg !209
  store i64 0, i64* %"i", !dbg !209
  br label %"for.cond", !dbg !209
for.cond:
  %".30" = load i64, i64* %"i", !dbg !209
  %".31" = icmp slt i64 %".30", %".27" , !dbg !209
  br i1 %".31", label %"for.body", label %"for.end", !dbg !209
for.body:
  %".33" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !209
  %".34" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".33", i32 0, i32 0 , !dbg !209
  %".35" = load i8*, i8** %".34", !dbg !209
  %".36" = getelementptr i8, i8* %".35", i64 %".24" , !dbg !209
  %".37" = load i64, i64* %"i", !dbg !209
  %".38" = getelementptr i8, i8* %".36", i64 %".37" , !dbg !209
  %".39" = load i8, i8* %".38", !dbg !209
  %".40" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"suffix", !dbg !209
  %".41" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".40", i32 0, i32 0 , !dbg !209
  %".42" = load i8*, i8** %".41", !dbg !209
  %".43" = load i64, i64* %"i", !dbg !209
  %".44" = getelementptr i8, i8* %".42", i64 %".43" , !dbg !209
  %".45" = load i8, i8* %".44", !dbg !209
  %".46" = icmp ne i8 %".39", %".45" , !dbg !209
  br i1 %".46", label %"if.then.1", label %"if.end.1", !dbg !209
for.incr:
  %".51" = load i64, i64* %"i", !dbg !210
  %".52" = add i64 %".51", 1, !dbg !210
  store i64 %".52", i64* %"i", !dbg !210
  br label %"for.cond", !dbg !210
for.end:
  %".55" = trunc i64 1 to i32 , !dbg !211
  ret i32 %".55", !dbg !211
if.then.1:
  %".48" = trunc i64 0 to i32 , !dbg !210
  ret i32 %".48", !dbg !210
if.end.1:
  br label %"for.incr", !dbg !210
}

define i32 @"strview_contains"(%"struct.ritz_module_1.StrView"* %"haystack.arg", %"struct.ritz_module_1.StrView"* %"needle.arg") !dbg !53
{
entry:
  %"haystack" = alloca %"struct.ritz_module_1.StrView"*
  %"pos.addr" = alloca i64, !dbg !219
  %"found.addr" = alloca i32, !dbg !224
  %"i.addr" = alloca i64, !dbg !227
  store %"struct.ritz_module_1.StrView"* %"haystack.arg", %"struct.ritz_module_1.StrView"** %"haystack"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"haystack", metadata !212, metadata !7), !dbg !213
  %"needle" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"needle.arg", %"struct.ritz_module_1.StrView"** %"needle"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"needle", metadata !214, metadata !7), !dbg !213
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"needle", !dbg !215
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".8", i32 0, i32 1 , !dbg !215
  %".10" = load i64, i64* %".9", !dbg !215
  %".11" = icmp eq i64 %".10", 0 , !dbg !215
  br i1 %".11", label %"if.then", label %"if.end", !dbg !215
if.then:
  %".13" = trunc i64 1 to i32 , !dbg !216
  ret i32 %".13", !dbg !216
if.end:
  %".15" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"haystack", !dbg !217
  %".16" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".15", i32 0, i32 1 , !dbg !217
  %".17" = load i64, i64* %".16", !dbg !217
  %".18" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"needle", !dbg !217
  %".19" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".18", i32 0, i32 1 , !dbg !217
  %".20" = load i64, i64* %".19", !dbg !217
  %".21" = icmp slt i64 %".17", %".20" , !dbg !217
  br i1 %".21", label %"if.then.1", label %"if.end.1", !dbg !217
if.then.1:
  %".23" = trunc i64 0 to i32 , !dbg !218
  ret i32 %".23", !dbg !218
if.end.1:
  store i64 0, i64* %"pos.addr", !dbg !219
  call void @"llvm.dbg.declare"(metadata i64* %"pos.addr", metadata !220, metadata !7), !dbg !221
  %".27" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"haystack", !dbg !222
  %".28" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".27", i32 0, i32 1 , !dbg !222
  %".29" = load i64, i64* %".28", !dbg !222
  %".30" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"needle", !dbg !222
  %".31" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".30", i32 0, i32 1 , !dbg !222
  %".32" = load i64, i64* %".31", !dbg !222
  %".33" = sub i64 %".29", %".32", !dbg !222
  %".34" = add i64 %".33", 1, !dbg !222
  br label %"while.cond", !dbg !223
while.cond:
  %".36" = load i64, i64* %"pos.addr", !dbg !223
  %".37" = icmp slt i64 %".36", %".34" , !dbg !223
  br i1 %".37", label %"while.body", label %"while.end", !dbg !223
while.body:
  %".39" = trunc i64 1 to i32 , !dbg !224
  store i32 %".39", i32* %"found.addr", !dbg !224
  call void @"llvm.dbg.declare"(metadata i32* %"found.addr", metadata !225, metadata !7), !dbg !226
  store i64 0, i64* %"i.addr", !dbg !227
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !228, metadata !7), !dbg !229
  br label %"while.cond.1", !dbg !230
while.end:
  %".90" = trunc i64 0 to i32 , !dbg !237
  ret i32 %".90", !dbg !237
while.cond.1:
  %".45" = load i64, i64* %"i.addr", !dbg !230
  %".46" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"needle", !dbg !230
  %".47" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".46", i32 0, i32 1 , !dbg !230
  %".48" = load i64, i64* %".47", !dbg !230
  %".49" = icmp slt i64 %".45", %".48" , !dbg !230
  br i1 %".49", label %"and.right", label %"and.merge", !dbg !230
while.body.1:
  %".57" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"haystack", !dbg !231
  %".58" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".57", i32 0, i32 0 , !dbg !231
  %".59" = load i8*, i8** %".58", !dbg !231
  %".60" = load i64, i64* %"pos.addr", !dbg !231
  %".61" = getelementptr i8, i8* %".59", i64 %".60" , !dbg !231
  %".62" = load i64, i64* %"i.addr", !dbg !231
  %".63" = getelementptr i8, i8* %".61", i64 %".62" , !dbg !231
  %".64" = load i8, i8* %".63", !dbg !231
  %".65" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"needle", !dbg !231
  %".66" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".65", i32 0, i32 0 , !dbg !231
  %".67" = load i8*, i8** %".66", !dbg !231
  %".68" = load i64, i64* %"i.addr", !dbg !231
  %".69" = getelementptr i8, i8* %".67", i64 %".68" , !dbg !231
  %".70" = load i8, i8* %".69", !dbg !231
  %".71" = icmp ne i8 %".64", %".70" , !dbg !231
  br i1 %".71", label %"if.then.2", label %"if.end.2", !dbg !231
while.end.1:
  %".80" = load i32, i32* %"found.addr", !dbg !234
  %".81" = sext i32 %".80" to i64 , !dbg !234
  %".82" = icmp eq i64 %".81", 1 , !dbg !234
  br i1 %".82", label %"if.then.3", label %"if.end.3", !dbg !234
and.right:
  %".51" = load i32, i32* %"found.addr", !dbg !230
  %".52" = sext i32 %".51" to i64 , !dbg !230
  %".53" = icmp eq i64 %".52", 1 , !dbg !230
  br label %"and.merge", !dbg !230
and.merge:
  %".55" = phi  i1 [0, %"while.cond.1"], [%".53", %"and.right"] , !dbg !230
  br i1 %".55", label %"while.body.1", label %"while.end.1", !dbg !230
if.then.2:
  %".73" = trunc i64 0 to i32 , !dbg !232
  store i32 %".73", i32* %"found.addr", !dbg !232
  br label %"if.end.2", !dbg !232
if.end.2:
  %".76" = load i64, i64* %"i.addr", !dbg !233
  %".77" = add i64 %".76", 1, !dbg !233
  store i64 %".77", i64* %"i.addr", !dbg !233
  br label %"while.cond.1", !dbg !233
if.then.3:
  %".84" = trunc i64 1 to i32 , !dbg !235
  ret i32 %".84", !dbg !235
if.end.3:
  %".86" = load i64, i64* %"pos.addr", !dbg !236
  %".87" = add i64 %".86", 1, !dbg !236
  store i64 %".87", i64* %"pos.addr", !dbg !236
  br label %"while.cond", !dbg !236
}

define i64 @"strview_find"(%"struct.ritz_module_1.StrView"* %"haystack.arg", %"struct.ritz_module_1.StrView"* %"needle.arg") !dbg !54
{
entry:
  %"haystack" = alloca %"struct.ritz_module_1.StrView"*
  %"pos.addr" = alloca i64, !dbg !245
  %"found.addr" = alloca i32, !dbg !250
  %"i.addr" = alloca i64, !dbg !253
  store %"struct.ritz_module_1.StrView"* %"haystack.arg", %"struct.ritz_module_1.StrView"** %"haystack"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"haystack", metadata !238, metadata !7), !dbg !239
  %"needle" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"needle.arg", %"struct.ritz_module_1.StrView"** %"needle"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"needle", metadata !240, metadata !7), !dbg !239
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"needle", !dbg !241
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".8", i32 0, i32 1 , !dbg !241
  %".10" = load i64, i64* %".9", !dbg !241
  %".11" = icmp eq i64 %".10", 0 , !dbg !241
  br i1 %".11", label %"if.then", label %"if.end", !dbg !241
if.then:
  ret i64 0, !dbg !242
if.end:
  %".14" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"haystack", !dbg !243
  %".15" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".14", i32 0, i32 1 , !dbg !243
  %".16" = load i64, i64* %".15", !dbg !243
  %".17" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"needle", !dbg !243
  %".18" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".17", i32 0, i32 1 , !dbg !243
  %".19" = load i64, i64* %".18", !dbg !243
  %".20" = icmp slt i64 %".16", %".19" , !dbg !243
  br i1 %".20", label %"if.then.1", label %"if.end.1", !dbg !243
if.then.1:
  %".22" = sub i64 0, 1, !dbg !244
  ret i64 %".22", !dbg !244
if.end.1:
  store i64 0, i64* %"pos.addr", !dbg !245
  call void @"llvm.dbg.declare"(metadata i64* %"pos.addr", metadata !246, metadata !7), !dbg !247
  %".26" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"haystack", !dbg !248
  %".27" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".26", i32 0, i32 1 , !dbg !248
  %".28" = load i64, i64* %".27", !dbg !248
  %".29" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"needle", !dbg !248
  %".30" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".29", i32 0, i32 1 , !dbg !248
  %".31" = load i64, i64* %".30", !dbg !248
  %".32" = sub i64 %".28", %".31", !dbg !248
  %".33" = add i64 %".32", 1, !dbg !248
  br label %"while.cond", !dbg !249
while.cond:
  %".35" = load i64, i64* %"pos.addr", !dbg !249
  %".36" = icmp slt i64 %".35", %".33" , !dbg !249
  br i1 %".36", label %"while.body", label %"while.end", !dbg !249
while.body:
  %".38" = trunc i64 1 to i32 , !dbg !250
  store i32 %".38", i32* %"found.addr", !dbg !250
  call void @"llvm.dbg.declare"(metadata i32* %"found.addr", metadata !251, metadata !7), !dbg !252
  store i64 0, i64* %"i.addr", !dbg !253
  call void @"llvm.dbg.declare"(metadata i64* %"i.addr", metadata !254, metadata !7), !dbg !255
  br label %"while.cond.1", !dbg !256
while.end:
  %".89" = sub i64 0, 1, !dbg !263
  ret i64 %".89", !dbg !263
while.cond.1:
  %".44" = load i64, i64* %"i.addr", !dbg !256
  %".45" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"needle", !dbg !256
  %".46" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".45", i32 0, i32 1 , !dbg !256
  %".47" = load i64, i64* %".46", !dbg !256
  %".48" = icmp slt i64 %".44", %".47" , !dbg !256
  br i1 %".48", label %"and.right", label %"and.merge", !dbg !256
while.body.1:
  %".56" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"haystack", !dbg !257
  %".57" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".56", i32 0, i32 0 , !dbg !257
  %".58" = load i8*, i8** %".57", !dbg !257
  %".59" = load i64, i64* %"pos.addr", !dbg !257
  %".60" = getelementptr i8, i8* %".58", i64 %".59" , !dbg !257
  %".61" = load i64, i64* %"i.addr", !dbg !257
  %".62" = getelementptr i8, i8* %".60", i64 %".61" , !dbg !257
  %".63" = load i8, i8* %".62", !dbg !257
  %".64" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"needle", !dbg !257
  %".65" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".64", i32 0, i32 0 , !dbg !257
  %".66" = load i8*, i8** %".65", !dbg !257
  %".67" = load i64, i64* %"i.addr", !dbg !257
  %".68" = getelementptr i8, i8* %".66", i64 %".67" , !dbg !257
  %".69" = load i8, i8* %".68", !dbg !257
  %".70" = icmp ne i8 %".63", %".69" , !dbg !257
  br i1 %".70", label %"if.then.2", label %"if.end.2", !dbg !257
while.end.1:
  %".79" = load i32, i32* %"found.addr", !dbg !260
  %".80" = sext i32 %".79" to i64 , !dbg !260
  %".81" = icmp eq i64 %".80", 1 , !dbg !260
  br i1 %".81", label %"if.then.3", label %"if.end.3", !dbg !260
and.right:
  %".50" = load i32, i32* %"found.addr", !dbg !256
  %".51" = sext i32 %".50" to i64 , !dbg !256
  %".52" = icmp eq i64 %".51", 1 , !dbg !256
  br label %"and.merge", !dbg !256
and.merge:
  %".54" = phi  i1 [0, %"while.cond.1"], [%".52", %"and.right"] , !dbg !256
  br i1 %".54", label %"while.body.1", label %"while.end.1", !dbg !256
if.then.2:
  %".72" = trunc i64 0 to i32 , !dbg !258
  store i32 %".72", i32* %"found.addr", !dbg !258
  br label %"if.end.2", !dbg !258
if.end.2:
  %".75" = load i64, i64* %"i.addr", !dbg !259
  %".76" = add i64 %".75", 1, !dbg !259
  store i64 %".76", i64* %"i.addr", !dbg !259
  br label %"while.cond.1", !dbg !259
if.then.3:
  %".83" = load i64, i64* %"pos.addr", !dbg !261
  ret i64 %".83", !dbg !261
if.end.3:
  %".85" = load i64, i64* %"pos.addr", !dbg !262
  %".86" = add i64 %".85", 1, !dbg !262
  store i64 %".86", i64* %"pos.addr", !dbg !262
  br label %"while.cond", !dbg !262
}

define i64 @"strview_find_byte"(%"struct.ritz_module_1.StrView"* %"s.arg", i8 %"c.arg") !dbg !55
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  %"i" = alloca i64, !dbg !267
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !264, metadata !7), !dbg !265
  %"c" = alloca i8
  store i8 %"c.arg", i8* %"c"
  call void @"llvm.dbg.declare"(metadata i8* %"c", metadata !266, metadata !7), !dbg !265
  %".8" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !267
  %".9" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".8", i32 0, i32 1 , !dbg !267
  %".10" = load i64, i64* %".9", !dbg !267
  store i64 0, i64* %"i", !dbg !267
  br label %"for.cond", !dbg !267
for.cond:
  %".13" = load i64, i64* %"i", !dbg !267
  %".14" = icmp slt i64 %".13", %".10" , !dbg !267
  br i1 %".14", label %"for.body", label %"for.end", !dbg !267
for.body:
  %".16" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !267
  %".17" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".16", i32 0, i32 0 , !dbg !267
  %".18" = load i8*, i8** %".17", !dbg !267
  %".19" = load i64, i64* %"i", !dbg !267
  %".20" = getelementptr i8, i8* %".18", i64 %".19" , !dbg !267
  %".21" = load i8, i8* %".20", !dbg !267
  %".22" = load i8, i8* %"c", !dbg !267
  %".23" = icmp eq i8 %".21", %".22" , !dbg !267
  br i1 %".23", label %"if.then", label %"if.end", !dbg !267
for.incr:
  %".28" = load i64, i64* %"i", !dbg !268
  %".29" = add i64 %".28", 1, !dbg !268
  store i64 %".29", i64* %"i", !dbg !268
  br label %"for.cond", !dbg !268
for.end:
  %".32" = sub i64 0, 1, !dbg !269
  ret i64 %".32", !dbg !269
if.then:
  %".25" = load i64, i64* %"i", !dbg !268
  ret i64 %".25", !dbg !268
if.end:
  br label %"for.incr", !dbg !268
}

define i32 @"strview_split_once"(%"struct.ritz_module_1.StrView"* %"s.arg", i8 %"delim.arg", %"struct.ritz_module_1.StrView"* %"before.arg", %"struct.ritz_module_1.StrView"* %"after.arg") !dbg !56
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !270, metadata !7), !dbg !271
  %"delim" = alloca i8
  store i8 %"delim.arg", i8* %"delim"
  call void @"llvm.dbg.declare"(metadata i8* %"delim", metadata !272, metadata !7), !dbg !271
  %"before" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"before.arg", %"struct.ritz_module_1.StrView"** %"before"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"before", metadata !273, metadata !7), !dbg !271
  %"after" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"after.arg", %"struct.ritz_module_1.StrView"** %"after"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"after", metadata !274, metadata !7), !dbg !271
  %".14" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !275
  %".15" = load i8, i8* %"delim", !dbg !275
  %".16" = call i64 @"strview_find_byte"(%"struct.ritz_module_1.StrView"* %".14", i8 %".15"), !dbg !275
  %".17" = icmp slt i64 %".16", 0 , !dbg !276
  br i1 %".17", label %"if.then", label %"if.end", !dbg !276
if.then:
  %".19" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !277
  %".20" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".19", i32 0, i32 0 , !dbg !277
  %".21" = load i8*, i8** %".20", !dbg !277
  %".22" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"before", !dbg !277
  %".23" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".22", i32 0, i32 0 , !dbg !277
  store i8* %".21", i8** %".23", !dbg !277
  %".25" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !278
  %".26" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".25", i32 0, i32 1 , !dbg !278
  %".27" = load i64, i64* %".26", !dbg !278
  %".28" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"before", !dbg !278
  %".29" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".28", i32 0, i32 1 , !dbg !278
  store i64 %".27", i64* %".29", !dbg !278
  %".31" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !279
  %".32" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".31", i32 0, i32 0 , !dbg !279
  %".33" = load i8*, i8** %".32", !dbg !279
  %".34" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !279
  %".35" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".34", i32 0, i32 1 , !dbg !279
  %".36" = load i64, i64* %".35", !dbg !279
  %".37" = getelementptr i8, i8* %".33", i64 %".36" , !dbg !279
  %".38" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"after", !dbg !279
  %".39" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".38", i32 0, i32 0 , !dbg !279
  store i8* %".37", i8** %".39", !dbg !279
  %".41" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"after", !dbg !280
  %".42" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".41", i32 0, i32 1 , !dbg !280
  store i64 0, i64* %".42", !dbg !280
  %".44" = trunc i64 0 to i32 , !dbg !281
  ret i32 %".44", !dbg !281
if.end:
  %".46" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !282
  %".47" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".46", i32 0, i32 0 , !dbg !282
  %".48" = load i8*, i8** %".47", !dbg !282
  %".49" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"before", !dbg !282
  %".50" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".49", i32 0, i32 0 , !dbg !282
  store i8* %".48", i8** %".50", !dbg !282
  %".52" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"before", !dbg !283
  %".53" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".52", i32 0, i32 1 , !dbg !283
  store i64 %".16", i64* %".53", !dbg !283
  %".55" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !284
  %".56" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".55", i32 0, i32 0 , !dbg !284
  %".57" = load i8*, i8** %".56", !dbg !284
  %".58" = getelementptr i8, i8* %".57", i64 %".16" , !dbg !284
  %".59" = getelementptr i8, i8* %".58", i64 1 , !dbg !284
  %".60" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"after", !dbg !284
  %".61" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".60", i32 0, i32 0 , !dbg !284
  store i8* %".59", i8** %".61", !dbg !284
  %".63" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !285
  %".64" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".63", i32 0, i32 1 , !dbg !285
  %".65" = load i64, i64* %".64", !dbg !285
  %".66" = sub i64 %".65", %".16", !dbg !285
  %".67" = sub i64 %".66", 1, !dbg !285
  %".68" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"after", !dbg !285
  %".69" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".68", i32 0, i32 1 , !dbg !285
  store i64 %".67", i64* %".69", !dbg !285
  %".71" = trunc i64 1 to i32 , !dbg !286
  ret i32 %".71", !dbg !286
}

define %"struct.ritz_module_1.StrView" @"strview_trim_start"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !57
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  %"result.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !289
  %"start.addr" = alloca i64, !dbg !292
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !287, metadata !7), !dbg !288
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"result.addr", metadata !290, metadata !7), !dbg !291
  store i64 0, i64* %"start.addr", !dbg !292
  call void @"llvm.dbg.declare"(metadata i64* %"start.addr", metadata !293, metadata !7), !dbg !294
  br label %"while.cond", !dbg !295
while.cond:
  %".9" = load i64, i64* %"start.addr", !dbg !295
  %".10" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !295
  %".11" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".10", i32 0, i32 1 , !dbg !295
  %".12" = load i64, i64* %".11", !dbg !295
  %".13" = icmp slt i64 %".9", %".12" , !dbg !295
  br i1 %".13", label %"while.body", label %"while.end", !dbg !295
while.body:
  %".15" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !296
  %".16" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".15", i32 0, i32 0 , !dbg !296
  %".17" = load i8*, i8** %".16", !dbg !296
  %".18" = load i64, i64* %"start.addr", !dbg !296
  %".19" = getelementptr i8, i8* %".17", i64 %".18" , !dbg !296
  %".20" = load i8, i8* %".19", !dbg !296
  %".21" = icmp ne i8 %".20", 32 , !dbg !297
  br i1 %".21", label %"and.right", label %"and.merge", !dbg !297
while.end:
  %".40" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !300
  %".41" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".40", i32 0, i32 0 , !dbg !300
  %".42" = load i8*, i8** %".41", !dbg !300
  %".43" = load i64, i64* %"start.addr", !dbg !300
  %".44" = getelementptr i8, i8* %".42", i64 %".43" , !dbg !300
  %".45" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !300
  %".46" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !300
  store i8* %".44", i8** %".46", !dbg !300
  %".48" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !301
  %".49" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".48", i32 0, i32 1 , !dbg !301
  %".50" = load i64, i64* %".49", !dbg !301
  %".51" = load i64, i64* %"start.addr", !dbg !301
  %".52" = sub i64 %".50", %".51", !dbg !301
  %".53" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !301
  %".54" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !301
  store i64 %".52", i64* %".54", !dbg !301
  %".56" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !302
  ret %"struct.ritz_module_1.StrView" %".56", !dbg !302
and.right:
  %".23" = icmp ne i8 %".20", 9 , !dbg !297
  br label %"and.merge", !dbg !297
and.merge:
  %".25" = phi  i1 [0, %"while.body"], [%".23", %"and.right"] , !dbg !297
  br i1 %".25", label %"and.right.1", label %"and.merge.1", !dbg !297
and.right.1:
  %".27" = icmp ne i8 %".20", 10 , !dbg !297
  br label %"and.merge.1", !dbg !297
and.merge.1:
  %".29" = phi  i1 [0, %"and.merge"], [%".27", %"and.right.1"] , !dbg !297
  br i1 %".29", label %"and.right.2", label %"and.merge.2", !dbg !297
and.right.2:
  %".31" = icmp ne i8 %".20", 13 , !dbg !297
  br label %"and.merge.2", !dbg !297
and.merge.2:
  %".33" = phi  i1 [0, %"and.merge.1"], [%".31", %"and.right.2"] , !dbg !297
  br i1 %".33", label %"if.then", label %"if.end", !dbg !297
if.then:
  br label %"while.end", !dbg !298
if.end:
  %".36" = load i64, i64* %"start.addr", !dbg !299
  %".37" = add i64 %".36", 1, !dbg !299
  store i64 %".37", i64* %"start.addr", !dbg !299
  br label %"while.cond", !dbg !299
}

define %"struct.ritz_module_1.StrView" @"strview_trim_end"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !58
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  %"result.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !305
  %"end.addr" = alloca i64, !dbg !308
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !303, metadata !7), !dbg !304
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"* %"result.addr", metadata !306, metadata !7), !dbg !307
  %".6" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !308
  %".7" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".6", i32 0, i32 1 , !dbg !308
  %".8" = load i64, i64* %".7", !dbg !308
  store i64 %".8", i64* %"end.addr", !dbg !308
  call void @"llvm.dbg.declare"(metadata i64* %"end.addr", metadata !309, metadata !7), !dbg !310
  br label %"while.cond", !dbg !311
while.cond:
  %".12" = load i64, i64* %"end.addr", !dbg !311
  %".13" = icmp sgt i64 %".12", 0 , !dbg !311
  br i1 %".13", label %"while.body", label %"while.end", !dbg !311
while.body:
  %".15" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !312
  %".16" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".15", i32 0, i32 0 , !dbg !312
  %".17" = load i8*, i8** %".16", !dbg !312
  %".18" = load i64, i64* %"end.addr", !dbg !312
  %".19" = getelementptr i8, i8* %".17", i64 %".18" , !dbg !312
  %".20" = sub i64 0, 1, !dbg !312
  %".21" = getelementptr i8, i8* %".19", i64 %".20" , !dbg !312
  %".22" = load i8, i8* %".21", !dbg !312
  %".23" = icmp ne i8 %".22", 32 , !dbg !313
  br i1 %".23", label %"and.right", label %"and.merge", !dbg !313
while.end:
  %".42" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !316
  %".43" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %".42", i32 0, i32 0 , !dbg !316
  %".44" = load i8*, i8** %".43", !dbg !316
  %".45" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !316
  %".46" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 0 , !dbg !316
  store i8* %".44", i8** %".46", !dbg !316
  %".48" = load i64, i64* %"end.addr", !dbg !317
  %".49" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !317
  %".50" = getelementptr %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", i32 0, i32 1 , !dbg !317
  store i64 %".48", i64* %".50", !dbg !317
  %".52" = load %"struct.ritz_module_1.StrView", %"struct.ritz_module_1.StrView"* %"result.addr", !dbg !318
  ret %"struct.ritz_module_1.StrView" %".52", !dbg !318
and.right:
  %".25" = icmp ne i8 %".22", 9 , !dbg !313
  br label %"and.merge", !dbg !313
and.merge:
  %".27" = phi  i1 [0, %"while.body"], [%".25", %"and.right"] , !dbg !313
  br i1 %".27", label %"and.right.1", label %"and.merge.1", !dbg !313
and.right.1:
  %".29" = icmp ne i8 %".22", 10 , !dbg !313
  br label %"and.merge.1", !dbg !313
and.merge.1:
  %".31" = phi  i1 [0, %"and.merge"], [%".29", %"and.right.1"] , !dbg !313
  br i1 %".31", label %"and.right.2", label %"and.merge.2", !dbg !313
and.right.2:
  %".33" = icmp ne i8 %".22", 13 , !dbg !313
  br label %"and.merge.2", !dbg !313
and.merge.2:
  %".35" = phi  i1 [0, %"and.merge.1"], [%".33", %"and.right.2"] , !dbg !313
  br i1 %".35", label %"if.then", label %"if.end", !dbg !313
if.then:
  br label %"while.end", !dbg !314
if.end:
  %".38" = load i64, i64* %"end.addr", !dbg !315
  %".39" = sub i64 %".38", 1, !dbg !315
  store i64 %".39", i64* %"end.addr", !dbg !315
  br label %"while.cond", !dbg !315
}

define %"struct.ritz_module_1.StrView" @"strview_trim"(%"struct.ritz_module_1.StrView"* %"s.arg") !dbg !59
{
entry:
  %"s" = alloca %"struct.ritz_module_1.StrView"*
  store %"struct.ritz_module_1.StrView"* %"s.arg", %"struct.ritz_module_1.StrView"** %"s"
  call void @"llvm.dbg.declare"(metadata %"struct.ritz_module_1.StrView"** %"s", metadata !319, metadata !7), !dbg !320
  %".5" = load %"struct.ritz_module_1.StrView"*, %"struct.ritz_module_1.StrView"** %"s", !dbg !321
  %".6" = call %"struct.ritz_module_1.StrView" @"strview_trim_start"(%"struct.ritz_module_1.StrView"* %".5"), !dbg !321
  %"trimmed.addr" = alloca %"struct.ritz_module_1.StrView", !dbg !322
  store %"struct.ritz_module_1.StrView" %".6", %"struct.ritz_module_1.StrView"* %"trimmed.addr", !dbg !322
  %".8" = call %"struct.ritz_module_1.StrView" @"strview_trim_end"(%"struct.ritz_module_1.StrView"* %"trimmed.addr"), !dbg !322
  ret %"struct.ritz_module_1.StrView" %".8", !dbg !322
}

!llvm.dbg.cu = !{ !1 }
!llvm.module.flags = !{ !5, !6 }
!0 = !DIFile(directory: "/home/aaron/dev/ritz-lang/cryptosec/ritz/ritzlib", filename: "strview.ritz")
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
!17 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 316, name: "StrView_len", scopeLine: 316, type: !4, unit: !1)
!18 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 319, name: "StrView_is_empty", scopeLine: 319, type: !4, unit: !1)
!19 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 322, name: "StrView_get", scopeLine: 322, type: !4, unit: !1)
!20 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 325, name: "StrView_as_ptr", scopeLine: 325, type: !4, unit: !1)
!21 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 328, name: "StrView_slice", scopeLine: 328, type: !4, unit: !1)
!22 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 331, name: "StrView_take", scopeLine: 331, type: !4, unit: !1)
!23 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 334, name: "StrView_skip", scopeLine: 334, type: !4, unit: !1)
!24 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 337, name: "StrView_starts_with", scopeLine: 337, type: !4, unit: !1)
!25 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 340, name: "StrView_ends_with", scopeLine: 340, type: !4, unit: !1)
!26 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 343, name: "StrView_contains", scopeLine: 343, type: !4, unit: !1)
!27 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 346, name: "StrView_find", scopeLine: 346, type: !4, unit: !1)
!28 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 349, name: "StrView_find_byte", scopeLine: 349, type: !4, unit: !1)
!29 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 352, name: "StrView_trim", scopeLine: 352, type: !4, unit: !1)
!30 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 355, name: "StrView_trim_start", scopeLine: 355, type: !4, unit: !1)
!31 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 358, name: "StrView_trim_end", scopeLine: 358, type: !4, unit: !1)
!32 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 361, name: "StrView_eq", scopeLine: 361, type: !4, unit: !1)
!33 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 364, name: "StrView_eq_cstr", scopeLine: 364, type: !4, unit: !1)
!34 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 368, name: "StrView_to_cstr", scopeLine: 368, type: !4, unit: !1)
!35 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 372, name: "StrView_as_cstr_unchecked", scopeLine: 372, type: !4, unit: !1)
!36 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 36, name: "strview_empty", scopeLine: 36, type: !4, unit: !1)
!37 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 43, name: "strview_from_ptr", scopeLine: 43, type: !4, unit: !1)
!38 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 50, name: "strview_from_cstr", scopeLine: 50, type: !4, unit: !1)
!39 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 61, name: "strview_len", scopeLine: 61, type: !4, unit: !1)
!40 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 65, name: "strview_is_empty", scopeLine: 65, type: !4, unit: !1)
!41 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 71, name: "strview_get", scopeLine: 71, type: !4, unit: !1)
!42 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 75, name: "strview_as_ptr", scopeLine: 75, type: !4, unit: !1)
!43 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 86, name: "strview_to_cstr", scopeLine: 86, type: !4, unit: !1)
!44 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 97, name: "strview_as_cstr_unchecked", scopeLine: 97, type: !4, unit: !1)
!45 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 105, name: "strview_eq", scopeLine: 105, type: !4, unit: !1)
!46 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 116, name: "strview_eq_cstr", scopeLine: 116, type: !4, unit: !1)
!47 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 134, name: "strview_slice", scopeLine: 134, type: !4, unit: !1)
!48 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 151, name: "strview_take", scopeLine: 151, type: !4, unit: !1)
!49 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 161, name: "strview_skip", scopeLine: 161, type: !4, unit: !1)
!50 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 176, name: "strview_starts_with", scopeLine: 176, type: !4, unit: !1)
!51 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 185, name: "strview_starts_with_cstr", scopeLine: 185, type: !4, unit: !1)
!52 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 196, name: "strview_ends_with", scopeLine: 196, type: !4, unit: !1)
!53 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 206, name: "strview_contains", scopeLine: 206, type: !4, unit: !1)
!54 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 227, name: "strview_find", scopeLine: 227, type: !4, unit: !1)
!55 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 248, name: "strview_find_byte", scopeLine: 248, type: !4, unit: !1)
!56 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 261, name: "strview_split_once", scopeLine: 261, type: !4, unit: !1)
!57 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 281, name: "strview_trim_start", scopeLine: 281, type: !4, unit: !1)
!58 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 294, name: "strview_trim_end", scopeLine: 294, type: !4, unit: !1)
!59 = distinct !DISubprogram(file: !0, isDefinition: true, isLocal: false, line: 307, name: "strview_trim", scopeLine: 307, type: !4, unit: !1)
!60 = !DILocation(column: 5, line: 37, scope: !36)
!61 = !DICompositeType(align: 64, file: !0, name: "StrView", size: 128, tag: DW_TAG_structure_type)
!62 = !DILocalVariable(file: !0, line: 37, name: "s", scope: !36, type: !61)
!63 = !DILocation(column: 1, line: 37, scope: !36)
!64 = !DILocation(column: 5, line: 38, scope: !36)
!65 = !DILocation(column: 5, line: 39, scope: !36)
!66 = !DILocation(column: 5, line: 40, scope: !36)
!67 = !DIDerivedType(baseType: !12, size: 64, tag: DW_TAG_pointer_type)
!68 = !DILocalVariable(file: !0, line: 43, name: "ptr", scope: !37, type: !67)
!69 = !DILocation(column: 1, line: 43, scope: !37)
!70 = !DILocalVariable(file: !0, line: 43, name: "len", scope: !37, type: !11)
!71 = !DILocation(column: 5, line: 44, scope: !37)
!72 = !DILocalVariable(file: !0, line: 44, name: "s", scope: !37, type: !61)
!73 = !DILocation(column: 1, line: 44, scope: !37)
!74 = !DILocation(column: 5, line: 45, scope: !37)
!75 = !DILocation(column: 5, line: 46, scope: !37)
!76 = !DILocation(column: 5, line: 47, scope: !37)
!77 = !DILocalVariable(file: !0, line: 50, name: "cstr", scope: !38, type: !67)
!78 = !DILocation(column: 1, line: 50, scope: !38)
!79 = !DILocation(column: 5, line: 51, scope: !38)
!80 = !DILocalVariable(file: !0, line: 51, name: "s", scope: !38, type: !61)
!81 = !DILocation(column: 1, line: 51, scope: !38)
!82 = !DILocation(column: 5, line: 52, scope: !38)
!83 = !DILocation(column: 5, line: 53, scope: !38)
!84 = !DILocation(column: 5, line: 54, scope: !38)
!85 = !DIDerivedType(baseType: !61, size: 64, tag: DW_TAG_pointer_type)
!86 = !DILocalVariable(file: !0, line: 61, name: "s", scope: !39, type: !85)
!87 = !DILocation(column: 1, line: 61, scope: !39)
!88 = !DILocation(column: 5, line: 62, scope: !39)
!89 = !DILocalVariable(file: !0, line: 65, name: "s", scope: !40, type: !85)
!90 = !DILocation(column: 1, line: 65, scope: !40)
!91 = !DILocation(column: 5, line: 66, scope: !40)
!92 = !DILocation(column: 9, line: 67, scope: !40)
!93 = !DILocation(column: 5, line: 68, scope: !40)
!94 = !DILocalVariable(file: !0, line: 71, name: "s", scope: !41, type: !85)
!95 = !DILocation(column: 1, line: 71, scope: !41)
!96 = !DILocalVariable(file: !0, line: 71, name: "idx", scope: !41, type: !11)
!97 = !DILocation(column: 5, line: 72, scope: !41)
!98 = !DILocalVariable(file: !0, line: 75, name: "s", scope: !42, type: !85)
!99 = !DILocation(column: 1, line: 75, scope: !42)
!100 = !DILocation(column: 5, line: 76, scope: !42)
!101 = !DILocalVariable(file: !0, line: 86, name: "s", scope: !43, type: !85)
!102 = !DILocation(column: 1, line: 86, scope: !43)
!103 = !DILocation(column: 5, line: 87, scope: !43)
!104 = !DILocation(column: 5, line: 88, scope: !43)
!105 = !DILocation(column: 5, line: 89, scope: !43)
!106 = !DILocation(column: 5, line: 90, scope: !43)
!107 = !DILocalVariable(file: !0, line: 97, name: "s", scope: !44, type: !85)
!108 = !DILocation(column: 1, line: 97, scope: !44)
!109 = !DILocation(column: 5, line: 98, scope: !44)
!110 = !DILocalVariable(file: !0, line: 105, name: "a", scope: !45, type: !85)
!111 = !DILocation(column: 1, line: 105, scope: !45)
!112 = !DILocalVariable(file: !0, line: 105, name: "b", scope: !45, type: !85)
!113 = !DILocation(column: 5, line: 106, scope: !45)
!114 = !DILocation(column: 9, line: 107, scope: !45)
!115 = !DILocation(column: 5, line: 108, scope: !45)
!116 = !DILocation(column: 9, line: 109, scope: !45)
!117 = !DILocation(column: 5, line: 110, scope: !45)
!118 = !DILocation(column: 13, line: 112, scope: !45)
!119 = !DILocation(column: 5, line: 113, scope: !45)
!120 = !DILocalVariable(file: !0, line: 116, name: "s", scope: !46, type: !85)
!121 = !DILocation(column: 1, line: 116, scope: !46)
!122 = !DILocalVariable(file: !0, line: 116, name: "cstr", scope: !46, type: !67)
!123 = !DILocation(column: 5, line: 117, scope: !46)
!124 = !DILocalVariable(file: !0, line: 117, name: "i", scope: !46, type: !11)
!125 = !DILocation(column: 1, line: 117, scope: !46)
!126 = !DILocation(column: 5, line: 118, scope: !46)
!127 = !DILocation(column: 9, line: 119, scope: !46)
!128 = !DILocation(column: 13, line: 120, scope: !46)
!129 = !DILocation(column: 9, line: 121, scope: !46)
!130 = !DILocation(column: 13, line: 122, scope: !46)
!131 = !DILocation(column: 9, line: 123, scope: !46)
!132 = !DILocation(column: 5, line: 125, scope: !46)
!133 = !DILocation(column: 9, line: 126, scope: !46)
!134 = !DILocation(column: 5, line: 127, scope: !46)
!135 = !DILocalVariable(file: !0, line: 134, name: "s", scope: !47, type: !85)
!136 = !DILocation(column: 1, line: 134, scope: !47)
!137 = !DILocalVariable(file: !0, line: 134, name: "start", scope: !47, type: !11)
!138 = !DILocalVariable(file: !0, line: 134, name: "end", scope: !47, type: !11)
!139 = !DILocation(column: 5, line: 135, scope: !47)
!140 = !DILocalVariable(file: !0, line: 135, name: "result", scope: !47, type: !61)
!141 = !DILocation(column: 1, line: 135, scope: !47)
!142 = !DILocation(column: 5, line: 136, scope: !47)
!143 = !DILocalVariable(file: !0, line: 136, name: "st", scope: !47, type: !11)
!144 = !DILocation(column: 1, line: 136, scope: !47)
!145 = !DILocation(column: 5, line: 137, scope: !47)
!146 = !DILocalVariable(file: !0, line: 137, name: "en", scope: !47, type: !11)
!147 = !DILocation(column: 1, line: 137, scope: !47)
!148 = !DILocation(column: 5, line: 138, scope: !47)
!149 = !DILocation(column: 9, line: 139, scope: !47)
!150 = !DILocation(column: 5, line: 140, scope: !47)
!151 = !DILocation(column: 9, line: 141, scope: !47)
!152 = !DILocation(column: 5, line: 142, scope: !47)
!153 = !DILocation(column: 9, line: 143, scope: !47)
!154 = !DILocation(column: 9, line: 144, scope: !47)
!155 = !DILocation(column: 9, line: 145, scope: !47)
!156 = !DILocation(column: 5, line: 146, scope: !47)
!157 = !DILocation(column: 5, line: 147, scope: !47)
!158 = !DILocation(column: 5, line: 148, scope: !47)
!159 = !DILocalVariable(file: !0, line: 151, name: "s", scope: !48, type: !85)
!160 = !DILocation(column: 1, line: 151, scope: !48)
!161 = !DILocalVariable(file: !0, line: 151, name: "n", scope: !48, type: !11)
!162 = !DILocation(column: 5, line: 152, scope: !48)
!163 = !DILocalVariable(file: !0, line: 152, name: "result", scope: !48, type: !61)
!164 = !DILocation(column: 1, line: 152, scope: !48)
!165 = !DILocation(column: 5, line: 153, scope: !48)
!166 = !DILocation(column: 5, line: 154, scope: !48)
!167 = !DILocation(column: 9, line: 155, scope: !48)
!168 = !DILocation(column: 9, line: 157, scope: !48)
!169 = !DILocation(column: 5, line: 158, scope: !48)
!170 = !DILocalVariable(file: !0, line: 161, name: "s", scope: !49, type: !85)
!171 = !DILocation(column: 1, line: 161, scope: !49)
!172 = !DILocalVariable(file: !0, line: 161, name: "n", scope: !49, type: !11)
!173 = !DILocation(column: 5, line: 162, scope: !49)
!174 = !DILocalVariable(file: !0, line: 162, name: "result", scope: !49, type: !61)
!175 = !DILocation(column: 1, line: 162, scope: !49)
!176 = !DILocation(column: 5, line: 163, scope: !49)
!177 = !DILocation(column: 9, line: 164, scope: !49)
!178 = !DILocation(column: 9, line: 165, scope: !49)
!179 = !DILocation(column: 9, line: 167, scope: !49)
!180 = !DILocation(column: 9, line: 168, scope: !49)
!181 = !DILocation(column: 5, line: 169, scope: !49)
!182 = !DILocalVariable(file: !0, line: 176, name: "s", scope: !50, type: !85)
!183 = !DILocation(column: 1, line: 176, scope: !50)
!184 = !DILocalVariable(file: !0, line: 176, name: "prefix", scope: !50, type: !85)
!185 = !DILocation(column: 5, line: 177, scope: !50)
!186 = !DILocation(column: 9, line: 178, scope: !50)
!187 = !DILocation(column: 5, line: 179, scope: !50)
!188 = !DILocation(column: 13, line: 181, scope: !50)
!189 = !DILocation(column: 5, line: 182, scope: !50)
!190 = !DILocalVariable(file: !0, line: 185, name: "s", scope: !51, type: !85)
!191 = !DILocation(column: 1, line: 185, scope: !51)
!192 = !DILocalVariable(file: !0, line: 185, name: "prefix", scope: !51, type: !67)
!193 = !DILocation(column: 5, line: 186, scope: !51)
!194 = !DILocalVariable(file: !0, line: 186, name: "i", scope: !51, type: !11)
!195 = !DILocation(column: 1, line: 186, scope: !51)
!196 = !DILocation(column: 5, line: 187, scope: !51)
!197 = !DILocation(column: 9, line: 188, scope: !51)
!198 = !DILocation(column: 13, line: 189, scope: !51)
!199 = !DILocation(column: 9, line: 190, scope: !51)
!200 = !DILocation(column: 13, line: 191, scope: !51)
!201 = !DILocation(column: 9, line: 192, scope: !51)
!202 = !DILocation(column: 5, line: 193, scope: !51)
!203 = !DILocalVariable(file: !0, line: 196, name: "s", scope: !52, type: !85)
!204 = !DILocation(column: 1, line: 196, scope: !52)
!205 = !DILocalVariable(file: !0, line: 196, name: "suffix", scope: !52, type: !85)
!206 = !DILocation(column: 5, line: 197, scope: !52)
!207 = !DILocation(column: 9, line: 198, scope: !52)
!208 = !DILocation(column: 5, line: 199, scope: !52)
!209 = !DILocation(column: 5, line: 200, scope: !52)
!210 = !DILocation(column: 13, line: 202, scope: !52)
!211 = !DILocation(column: 5, line: 203, scope: !52)
!212 = !DILocalVariable(file: !0, line: 206, name: "haystack", scope: !53, type: !85)
!213 = !DILocation(column: 1, line: 206, scope: !53)
!214 = !DILocalVariable(file: !0, line: 206, name: "needle", scope: !53, type: !85)
!215 = !DILocation(column: 5, line: 207, scope: !53)
!216 = !DILocation(column: 9, line: 208, scope: !53)
!217 = !DILocation(column: 5, line: 209, scope: !53)
!218 = !DILocation(column: 9, line: 210, scope: !53)
!219 = !DILocation(column: 5, line: 212, scope: !53)
!220 = !DILocalVariable(file: !0, line: 212, name: "pos", scope: !53, type: !11)
!221 = !DILocation(column: 1, line: 212, scope: !53)
!222 = !DILocation(column: 5, line: 213, scope: !53)
!223 = !DILocation(column: 5, line: 214, scope: !53)
!224 = !DILocation(column: 9, line: 215, scope: !53)
!225 = !DILocalVariable(file: !0, line: 215, name: "found", scope: !53, type: !10)
!226 = !DILocation(column: 1, line: 215, scope: !53)
!227 = !DILocation(column: 9, line: 216, scope: !53)
!228 = !DILocalVariable(file: !0, line: 216, name: "i", scope: !53, type: !11)
!229 = !DILocation(column: 1, line: 216, scope: !53)
!230 = !DILocation(column: 9, line: 217, scope: !53)
!231 = !DILocation(column: 13, line: 218, scope: !53)
!232 = !DILocation(column: 17, line: 219, scope: !53)
!233 = !DILocation(column: 13, line: 220, scope: !53)
!234 = !DILocation(column: 9, line: 221, scope: !53)
!235 = !DILocation(column: 13, line: 222, scope: !53)
!236 = !DILocation(column: 9, line: 223, scope: !53)
!237 = !DILocation(column: 5, line: 224, scope: !53)
!238 = !DILocalVariable(file: !0, line: 227, name: "haystack", scope: !54, type: !85)
!239 = !DILocation(column: 1, line: 227, scope: !54)
!240 = !DILocalVariable(file: !0, line: 227, name: "needle", scope: !54, type: !85)
!241 = !DILocation(column: 5, line: 228, scope: !54)
!242 = !DILocation(column: 9, line: 229, scope: !54)
!243 = !DILocation(column: 5, line: 230, scope: !54)
!244 = !DILocation(column: 9, line: 231, scope: !54)
!245 = !DILocation(column: 5, line: 233, scope: !54)
!246 = !DILocalVariable(file: !0, line: 233, name: "pos", scope: !54, type: !11)
!247 = !DILocation(column: 1, line: 233, scope: !54)
!248 = !DILocation(column: 5, line: 234, scope: !54)
!249 = !DILocation(column: 5, line: 235, scope: !54)
!250 = !DILocation(column: 9, line: 236, scope: !54)
!251 = !DILocalVariable(file: !0, line: 236, name: "found", scope: !54, type: !10)
!252 = !DILocation(column: 1, line: 236, scope: !54)
!253 = !DILocation(column: 9, line: 237, scope: !54)
!254 = !DILocalVariable(file: !0, line: 237, name: "i", scope: !54, type: !11)
!255 = !DILocation(column: 1, line: 237, scope: !54)
!256 = !DILocation(column: 9, line: 238, scope: !54)
!257 = !DILocation(column: 13, line: 239, scope: !54)
!258 = !DILocation(column: 17, line: 240, scope: !54)
!259 = !DILocation(column: 13, line: 241, scope: !54)
!260 = !DILocation(column: 9, line: 242, scope: !54)
!261 = !DILocation(column: 13, line: 243, scope: !54)
!262 = !DILocation(column: 9, line: 244, scope: !54)
!263 = !DILocation(column: 5, line: 245, scope: !54)
!264 = !DILocalVariable(file: !0, line: 248, name: "s", scope: !55, type: !85)
!265 = !DILocation(column: 1, line: 248, scope: !55)
!266 = !DILocalVariable(file: !0, line: 248, name: "c", scope: !55, type: !12)
!267 = !DILocation(column: 5, line: 249, scope: !55)
!268 = !DILocation(column: 13, line: 251, scope: !55)
!269 = !DILocation(column: 5, line: 252, scope: !55)
!270 = !DILocalVariable(file: !0, line: 261, name: "s", scope: !56, type: !85)
!271 = !DILocation(column: 1, line: 261, scope: !56)
!272 = !DILocalVariable(file: !0, line: 261, name: "delim", scope: !56, type: !12)
!273 = !DILocalVariable(file: !0, line: 261, name: "before", scope: !56, type: !85)
!274 = !DILocalVariable(file: !0, line: 261, name: "after", scope: !56, type: !85)
!275 = !DILocation(column: 5, line: 262, scope: !56)
!276 = !DILocation(column: 5, line: 263, scope: !56)
!277 = !DILocation(column: 9, line: 264, scope: !56)
!278 = !DILocation(column: 9, line: 265, scope: !56)
!279 = !DILocation(column: 9, line: 266, scope: !56)
!280 = !DILocation(column: 9, line: 267, scope: !56)
!281 = !DILocation(column: 9, line: 268, scope: !56)
!282 = !DILocation(column: 5, line: 270, scope: !56)
!283 = !DILocation(column: 5, line: 271, scope: !56)
!284 = !DILocation(column: 5, line: 272, scope: !56)
!285 = !DILocation(column: 5, line: 273, scope: !56)
!286 = !DILocation(column: 5, line: 274, scope: !56)
!287 = !DILocalVariable(file: !0, line: 281, name: "s", scope: !57, type: !85)
!288 = !DILocation(column: 1, line: 281, scope: !57)
!289 = !DILocation(column: 5, line: 282, scope: !57)
!290 = !DILocalVariable(file: !0, line: 282, name: "result", scope: !57, type: !61)
!291 = !DILocation(column: 1, line: 282, scope: !57)
!292 = !DILocation(column: 5, line: 283, scope: !57)
!293 = !DILocalVariable(file: !0, line: 283, name: "start", scope: !57, type: !11)
!294 = !DILocation(column: 1, line: 283, scope: !57)
!295 = !DILocation(column: 5, line: 284, scope: !57)
!296 = !DILocation(column: 9, line: 285, scope: !57)
!297 = !DILocation(column: 9, line: 286, scope: !57)
!298 = !DILocation(column: 13, line: 287, scope: !57)
!299 = !DILocation(column: 9, line: 288, scope: !57)
!300 = !DILocation(column: 5, line: 289, scope: !57)
!301 = !DILocation(column: 5, line: 290, scope: !57)
!302 = !DILocation(column: 5, line: 291, scope: !57)
!303 = !DILocalVariable(file: !0, line: 294, name: "s", scope: !58, type: !85)
!304 = !DILocation(column: 1, line: 294, scope: !58)
!305 = !DILocation(column: 5, line: 295, scope: !58)
!306 = !DILocalVariable(file: !0, line: 295, name: "result", scope: !58, type: !61)
!307 = !DILocation(column: 1, line: 295, scope: !58)
!308 = !DILocation(column: 5, line: 296, scope: !58)
!309 = !DILocalVariable(file: !0, line: 296, name: "end", scope: !58, type: !11)
!310 = !DILocation(column: 1, line: 296, scope: !58)
!311 = !DILocation(column: 5, line: 297, scope: !58)
!312 = !DILocation(column: 9, line: 298, scope: !58)
!313 = !DILocation(column: 9, line: 299, scope: !58)
!314 = !DILocation(column: 13, line: 300, scope: !58)
!315 = !DILocation(column: 9, line: 301, scope: !58)
!316 = !DILocation(column: 5, line: 302, scope: !58)
!317 = !DILocation(column: 5, line: 303, scope: !58)
!318 = !DILocation(column: 5, line: 304, scope: !58)
!319 = !DILocalVariable(file: !0, line: 307, name: "s", scope: !59, type: !85)
!320 = !DILocation(column: 1, line: 307, scope: !59)
!321 = !DILocation(column: 5, line: 308, scope: !59)
!322 = !DILocation(column: 5, line: 309, scope: !59)
!323 = !DILocalVariable(file: !0, line: 316, name: "self", scope: !17, type: !85)
!324 = !DILocation(column: 1, line: 316, scope: !17)
!325 = !DILocation(column: 9, line: 317, scope: !17)
!326 = !DILocalVariable(file: !0, line: 319, name: "self", scope: !18, type: !85)
!327 = !DILocation(column: 1, line: 319, scope: !18)
!328 = !DILocation(column: 9, line: 320, scope: !18)
!329 = !DILocalVariable(file: !0, line: 322, name: "self", scope: !19, type: !85)
!330 = !DILocation(column: 1, line: 322, scope: !19)
!331 = !DILocalVariable(file: !0, line: 322, name: "idx", scope: !19, type: !11)
!332 = !DILocation(column: 9, line: 323, scope: !19)
!333 = !DILocalVariable(file: !0, line: 325, name: "self", scope: !20, type: !85)
!334 = !DILocation(column: 1, line: 325, scope: !20)
!335 = !DILocation(column: 9, line: 326, scope: !20)
!336 = !DILocalVariable(file: !0, line: 328, name: "self", scope: !21, type: !85)
!337 = !DILocation(column: 1, line: 328, scope: !21)
!338 = !DILocalVariable(file: !0, line: 328, name: "start", scope: !21, type: !11)
!339 = !DILocalVariable(file: !0, line: 328, name: "end", scope: !21, type: !11)
!340 = !DILocation(column: 9, line: 329, scope: !21)
!341 = !DILocalVariable(file: !0, line: 331, name: "self", scope: !22, type: !85)
!342 = !DILocation(column: 1, line: 331, scope: !22)
!343 = !DILocalVariable(file: !0, line: 331, name: "n", scope: !22, type: !11)
!344 = !DILocation(column: 9, line: 332, scope: !22)
!345 = !DILocalVariable(file: !0, line: 334, name: "self", scope: !23, type: !85)
!346 = !DILocation(column: 1, line: 334, scope: !23)
!347 = !DILocalVariable(file: !0, line: 334, name: "n", scope: !23, type: !11)
!348 = !DILocation(column: 9, line: 335, scope: !23)
!349 = !DILocalVariable(file: !0, line: 337, name: "self", scope: !24, type: !85)
!350 = !DILocation(column: 1, line: 337, scope: !24)
!351 = !DILocalVariable(file: !0, line: 337, name: "prefix", scope: !24, type: !85)
!352 = !DILocation(column: 9, line: 338, scope: !24)
!353 = !DILocalVariable(file: !0, line: 340, name: "self", scope: !25, type: !85)
!354 = !DILocation(column: 1, line: 340, scope: !25)
!355 = !DILocalVariable(file: !0, line: 340, name: "suffix", scope: !25, type: !85)
!356 = !DILocation(column: 9, line: 341, scope: !25)
!357 = !DILocalVariable(file: !0, line: 343, name: "self", scope: !26, type: !85)
!358 = !DILocation(column: 1, line: 343, scope: !26)
!359 = !DILocalVariable(file: !0, line: 343, name: "needle", scope: !26, type: !85)
!360 = !DILocation(column: 9, line: 344, scope: !26)
!361 = !DILocalVariable(file: !0, line: 346, name: "self", scope: !27, type: !85)
!362 = !DILocation(column: 1, line: 346, scope: !27)
!363 = !DILocalVariable(file: !0, line: 346, name: "needle", scope: !27, type: !85)
!364 = !DILocation(column: 9, line: 347, scope: !27)
!365 = !DILocalVariable(file: !0, line: 349, name: "self", scope: !28, type: !85)
!366 = !DILocation(column: 1, line: 349, scope: !28)
!367 = !DILocalVariable(file: !0, line: 349, name: "c", scope: !28, type: !12)
!368 = !DILocation(column: 9, line: 350, scope: !28)
!369 = !DILocalVariable(file: !0, line: 352, name: "self", scope: !29, type: !85)
!370 = !DILocation(column: 1, line: 352, scope: !29)
!371 = !DILocation(column: 9, line: 353, scope: !29)
!372 = !DILocalVariable(file: !0, line: 355, name: "self", scope: !30, type: !85)
!373 = !DILocation(column: 1, line: 355, scope: !30)
!374 = !DILocation(column: 9, line: 356, scope: !30)
!375 = !DILocalVariable(file: !0, line: 358, name: "self", scope: !31, type: !85)
!376 = !DILocation(column: 1, line: 358, scope: !31)
!377 = !DILocation(column: 9, line: 359, scope: !31)
!378 = !DILocalVariable(file: !0, line: 361, name: "self", scope: !32, type: !85)
!379 = !DILocation(column: 1, line: 361, scope: !32)
!380 = !DILocalVariable(file: !0, line: 361, name: "other", scope: !32, type: !85)
!381 = !DILocation(column: 9, line: 362, scope: !32)
!382 = !DILocalVariable(file: !0, line: 364, name: "self", scope: !33, type: !85)
!383 = !DILocation(column: 1, line: 364, scope: !33)
!384 = !DILocalVariable(file: !0, line: 364, name: "cstr", scope: !33, type: !67)
!385 = !DILocation(column: 9, line: 365, scope: !33)
!386 = !DILocalVariable(file: !0, line: 368, name: "self", scope: !34, type: !85)
!387 = !DILocation(column: 1, line: 368, scope: !34)
!388 = !DILocation(column: 9, line: 369, scope: !34)
!389 = !DILocalVariable(file: !0, line: 372, name: "self", scope: !35, type: !85)
!390 = !DILocation(column: 1, line: 372, scope: !35)
!391 = !DILocation(column: 9, line: 373, scope: !35)