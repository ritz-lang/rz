{
  "source_hash": "bca94abe33c74155",
  "functions": {
    "sys_yield": {
      "hash": "ed69b1156f0f39c7",
      "sig_hash": "ffec476e30b82064",
      "ir": ""
    },
    "sys_getpid": {
      "hash": "66c4578f2ebb2ee8",
      "sig_hash": "588a8c119884a3f1",
      "ir": "define i32 @\"sys_getpid\"() !dbg !17\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 39), !dbg !69\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !69\n  ret i32 %\".3\", !dbg !69\n}"
    },
    "sys_stat2": {
      "hash": "3fb3c460ba2bbade",
      "sig_hash": "dba829ba124a9707",
      "ir": "define i32 @\"sys_stat2\"(i8* %\"path.arg\", %\"struct.ritz_module_1.Stat\"* %\"statbuf.arg\") !dbg !18\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !71, metadata !7), !dbg !72\n  %\"statbuf\" = alloca %\"struct.ritz_module_1.Stat\"*\n  store %\"struct.ritz_module_1.Stat\"* %\"statbuf.arg\", %\"struct.ritz_module_1.Stat\"** %\"statbuf\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Stat\"** %\"statbuf\", metadata !75, metadata !7), !dbg !72\n  %\".8\" = load i8*, i8** %\"path\", !dbg !76\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !76\n  %\".10\" = load %\"struct.ritz_module_1.Stat\"*, %\"struct.ritz_module_1.Stat\"** %\"statbuf\", !dbg !76\n  %\".11\" = ptrtoint %\"struct.ritz_module_1.Stat\"* %\".10\" to i64 , !dbg !76\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 4, i64 %\".9\", i64 %\".11\"), !dbg !76\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !76\n  ret i32 %\".13\", !dbg !76\n}"
    },
    "sys_fstat2": {
      "hash": "7d2910c4fe581343",
      "sig_hash": "b29835d92e0b2b2d",
      "ir": "define i32 @\"sys_fstat2\"(i32 %\"fd.arg\", %\"struct.ritz_module_1.Stat\"* %\"statbuf.arg\") !dbg !19\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !77, metadata !7), !dbg !78\n  %\"statbuf\" = alloca %\"struct.ritz_module_1.Stat\"*\n  store %\"struct.ritz_module_1.Stat\"* %\"statbuf.arg\", %\"struct.ritz_module_1.Stat\"** %\"statbuf\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Stat\"** %\"statbuf\", metadata !79, metadata !7), !dbg !78\n  %\".8\" = load i32, i32* %\"fd\", !dbg !80\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !80\n  %\".10\" = load %\"struct.ritz_module_1.Stat\"*, %\"struct.ritz_module_1.Stat\"** %\"statbuf\", !dbg !80\n  %\".11\" = ptrtoint %\"struct.ritz_module_1.Stat\"* %\".10\" to i64 , !dbg !80\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 5, i64 %\".9\", i64 %\".11\"), !dbg !80\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !80\n  ret i32 %\".13\", !dbg !80\n}"
    },
    "sys_lstat2": {
      "hash": "f6c0d5d57c04fb2a",
      "sig_hash": "c8a10d4cacffcca8",
      "ir": "define i32 @\"sys_lstat2\"(i8* %\"path.arg\", %\"struct.ritz_module_1.Stat\"* %\"statbuf.arg\") !dbg !20\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !81, metadata !7), !dbg !82\n  %\"statbuf\" = alloca %\"struct.ritz_module_1.Stat\"*\n  store %\"struct.ritz_module_1.Stat\"* %\"statbuf.arg\", %\"struct.ritz_module_1.Stat\"** %\"statbuf\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Stat\"** %\"statbuf\", metadata !83, metadata !7), !dbg !82\n  %\".8\" = load i8*, i8** %\"path\", !dbg !84\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !84\n  %\".10\" = load %\"struct.ritz_module_1.Stat\"*, %\"struct.ritz_module_1.Stat\"** %\"statbuf\", !dbg !84\n  %\".11\" = ptrtoint %\"struct.ritz_module_1.Stat\"* %\".10\" to i64 , !dbg !84\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 6, i64 %\".9\", i64 %\".11\"), !dbg !84\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !84\n  ret i32 %\".13\", !dbg !84\n}"
    },
    "at_fdcwd": {
      "hash": "794e59f2c2fc51d5",
      "sig_hash": "692c8512c2111e23",
      "ir": "define i32 @\"at_fdcwd\"() !dbg !21\n{\nentry:\n  %\".2\" = sub i64 0, 100, !dbg !85\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !85\n  ret i32 %\".3\", !dbg !85\n}"
    },
    "sys_read": {
      "hash": "e5a05419b4ae583b",
      "sig_hash": "5f03fd03be67a0c6",
      "ir": "define i64 @\"sys_read\"(i32 %\"fd.arg\", i8* %\"buf.arg\", i64 %\"count.arg\") !dbg !22\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !86, metadata !7), !dbg !87\n  %\"buf\" = alloca i8*\n  store i8* %\"buf.arg\", i8** %\"buf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"buf\", metadata !88, metadata !7), !dbg !87\n  %\"count\" = alloca i64\n  store i64 %\"count.arg\", i64* %\"count\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"count\", metadata !89, metadata !7), !dbg !87\n  %\".11\" = load i32, i32* %\"fd\", !dbg !90\n  %\".12\" = sext i32 %\".11\" to i64 , !dbg !90\n  %\".13\" = load i8*, i8** %\"buf\", !dbg !90\n  %\".14\" = ptrtoint i8* %\".13\" to i64 , !dbg !90\n  %\".15\" = load i64, i64* %\"count\", !dbg !90\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 0, i64 %\".12\", i64 %\".14\", i64 %\".15\"), !dbg !90\n  ret i64 %\".16\", !dbg !90\n}"
    },
    "sys_write": {
      "hash": "ef9628165cd5a57b",
      "sig_hash": "f7c9e60092ca93ca",
      "ir": "define i64 @\"sys_write\"(i32 %\"fd.arg\", i8* %\"buf.arg\", i64 %\"count.arg\") !dbg !23\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !91, metadata !7), !dbg !92\n  %\"buf\" = alloca i8*\n  store i8* %\"buf.arg\", i8** %\"buf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"buf\", metadata !93, metadata !7), !dbg !92\n  %\"count\" = alloca i64\n  store i64 %\"count.arg\", i64* %\"count\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"count\", metadata !94, metadata !7), !dbg !92\n  %\".11\" = load i32, i32* %\"fd\", !dbg !95\n  %\".12\" = sext i32 %\".11\" to i64 , !dbg !95\n  %\".13\" = load i8*, i8** %\"buf\", !dbg !95\n  %\".14\" = ptrtoint i8* %\".13\" to i64 , !dbg !95\n  %\".15\" = load i64, i64* %\"count\", !dbg !95\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 1, i64 %\".12\", i64 %\".14\", i64 %\".15\"), !dbg !95\n  ret i64 %\".16\", !dbg !95\n}"
    },
    "sys_open": {
      "hash": "66834bbd60f6749b",
      "sig_hash": "e991aeb07a042029",
      "ir": "define i32 @\"sys_open\"(i8* %\"path.arg\", i32 %\"flags.arg\") !dbg !24\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !96, metadata !7), !dbg !97\n  %\"flags\" = alloca i32\n  store i32 %\"flags.arg\", i32* %\"flags\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"flags\", metadata !98, metadata !7), !dbg !97\n  %\".8\" = load i8*, i8** %\"path\", !dbg !99\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !99\n  %\".10\" = load i32, i32* %\"flags\", !dbg !99\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !99\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 2, i64 %\".9\", i64 %\".11\"), !dbg !99\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !99\n  ret i32 %\".13\", !dbg !99\n}"
    },
    "sys_open3": {
      "hash": "8e26451ac5bf2d7a",
      "sig_hash": "5b5345180d41c978",
      "ir": "define i32 @\"sys_open3\"(i8* %\"path.arg\", i32 %\"flags.arg\", i32 %\"mode.arg\") !dbg !25\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !100, metadata !7), !dbg !101\n  %\"flags\" = alloca i32\n  store i32 %\"flags.arg\", i32* %\"flags\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"flags\", metadata !102, metadata !7), !dbg !101\n  %\"mode\" = alloca i32\n  store i32 %\"mode.arg\", i32* %\"mode\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"mode\", metadata !103, metadata !7), !dbg !101\n  %\".11\" = load i8*, i8** %\"path\", !dbg !104\n  %\".12\" = ptrtoint i8* %\".11\" to i64 , !dbg !104\n  %\".13\" = load i32, i32* %\"flags\", !dbg !104\n  %\".14\" = sext i32 %\".13\" to i64 , !dbg !104\n  %\".15\" = load i32, i32* %\"mode\", !dbg !104\n  %\".16\" = sext i32 %\".15\" to i64 , !dbg !104\n  %\".17\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 2, i64 %\".12\", i64 %\".14\", i64 %\".16\"), !dbg !104\n  %\".18\" = trunc i64 %\".17\" to i32 , !dbg !104\n  ret i32 %\".18\", !dbg !104\n}"
    },
    "sys_close": {
      "hash": "8a263a8d9d509709",
      "sig_hash": "c8d1fe2642aeac35",
      "ir": "define i32 @\"sys_close\"(i32 %\"fd.arg\") !dbg !26\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !105, metadata !7), !dbg !106\n  %\".5\" = load i32, i32* %\"fd\", !dbg !107\n  %\".6\" = sext i32 %\".5\" to i64 , !dbg !107\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 3, i64 %\".6\"), !dbg !107\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !107\n  ret i32 %\".8\", !dbg !107\n}"
    },
    "sys_lseek": {
      "hash": "76a0da52d5b87bb3",
      "sig_hash": "472b58567b35c85a",
      "ir": "define i64 @\"sys_lseek\"(i32 %\"fd.arg\", i64 %\"offset.arg\", i32 %\"whence.arg\") !dbg !27\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !108, metadata !7), !dbg !109\n  %\"offset\" = alloca i64\n  store i64 %\"offset.arg\", i64* %\"offset\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"offset\", metadata !110, metadata !7), !dbg !109\n  %\"whence\" = alloca i32\n  store i32 %\"whence.arg\", i32* %\"whence\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"whence\", metadata !111, metadata !7), !dbg !109\n  %\".11\" = load i32, i32* %\"fd\", !dbg !112\n  %\".12\" = sext i32 %\".11\" to i64 , !dbg !112\n  %\".13\" = load i64, i64* %\"offset\", !dbg !112\n  %\".14\" = load i32, i32* %\"whence\", !dbg !112\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !112\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 8, i64 %\".12\", i64 %\".13\", i64 %\".15\"), !dbg !112\n  ret i64 %\".16\", !dbg !112\n}"
    },
    "sys_ftruncate": {
      "hash": "147864c0e53afe74",
      "sig_hash": "baf14cbb129be35b",
      "ir": "define i32 @\"sys_ftruncate\"(i32 %\"fd.arg\", i64 %\"length.arg\") !dbg !28\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !113, metadata !7), !dbg !114\n  %\"length\" = alloca i64\n  store i64 %\"length.arg\", i64* %\"length\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"length\", metadata !115, metadata !7), !dbg !114\n  %\".8\" = load i32, i32* %\"fd\", !dbg !116\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !116\n  %\".10\" = load i64, i64* %\"length\", !dbg !116\n  %\".11\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 77, i64 %\".9\", i64 %\".10\"), !dbg !116\n  %\".12\" = trunc i64 %\".11\" to i32 , !dbg !116\n  ret i32 %\".12\", !dbg !116\n}"
    },
    "sys_stat": {
      "hash": "4f2de9e28b7166c0",
      "sig_hash": "829dfeb465e05618",
      "ir": "define i32 @\"sys_stat\"(i8* %\"path.arg\", i8* %\"statbuf.arg\") !dbg !29\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !117, metadata !7), !dbg !118\n  %\"statbuf\" = alloca i8*\n  store i8* %\"statbuf.arg\", i8** %\"statbuf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"statbuf\", metadata !119, metadata !7), !dbg !118\n  %\".8\" = load i8*, i8** %\"path\", !dbg !120\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !120\n  %\".10\" = load i8*, i8** %\"statbuf\", !dbg !120\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !120\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 4, i64 %\".9\", i64 %\".11\"), !dbg !120\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !120\n  ret i32 %\".13\", !dbg !120\n}"
    },
    "sys_fstat": {
      "hash": "1662c4cf52576731",
      "sig_hash": "43c8fba77801f9ef",
      "ir": "define i32 @\"sys_fstat\"(i32 %\"fd.arg\", i8* %\"statbuf.arg\") !dbg !30\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !121, metadata !7), !dbg !122\n  %\"statbuf\" = alloca i8*\n  store i8* %\"statbuf.arg\", i8** %\"statbuf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"statbuf\", metadata !123, metadata !7), !dbg !122\n  %\".8\" = load i32, i32* %\"fd\", !dbg !124\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !124\n  %\".10\" = load i8*, i8** %\"statbuf\", !dbg !124\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !124\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 5, i64 %\".9\", i64 %\".11\"), !dbg !124\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !124\n  ret i32 %\".13\", !dbg !124\n}"
    },
    "sys_lstat": {
      "hash": "947ace780c4bb637",
      "sig_hash": "59f5b3b8d88592e2",
      "ir": "define i32 @\"sys_lstat\"(i8* %\"path.arg\", i8* %\"statbuf.arg\") !dbg !31\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !125, metadata !7), !dbg !126\n  %\"statbuf\" = alloca i8*\n  store i8* %\"statbuf.arg\", i8** %\"statbuf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"statbuf\", metadata !127, metadata !7), !dbg !126\n  %\".8\" = load i8*, i8** %\"path\", !dbg !128\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !128\n  %\".10\" = load i8*, i8** %\"statbuf\", !dbg !128\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !128\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 6, i64 %\".9\", i64 %\".11\"), !dbg !128\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !128\n  ret i32 %\".13\", !dbg !128\n}"
    },
    "sys_chmod": {
      "hash": "1ae9ba456b44eb68",
      "sig_hash": "93bb206537238fee",
      "ir": "define i32 @\"sys_chmod\"(i8* %\"path.arg\", i32 %\"mode.arg\") !dbg !32\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !129, metadata !7), !dbg !130\n  %\"mode\" = alloca i32\n  store i32 %\"mode.arg\", i32* %\"mode\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"mode\", metadata !131, metadata !7), !dbg !130\n  %\".8\" = load i8*, i8** %\"path\", !dbg !132\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !132\n  %\".10\" = load i32, i32* %\"mode\", !dbg !132\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !132\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 90, i64 %\".9\", i64 %\".11\"), !dbg !132\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !132\n  ret i32 %\".13\", !dbg !132\n}"
    },
    "sys_fchmod": {
      "hash": "43d2a33b9bcf5927",
      "sig_hash": "3a7d585f5708191d",
      "ir": "define i32 @\"sys_fchmod\"(i32 %\"fd.arg\", i32 %\"mode.arg\") !dbg !33\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !133, metadata !7), !dbg !134\n  %\"mode\" = alloca i32\n  store i32 %\"mode.arg\", i32* %\"mode\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"mode\", metadata !135, metadata !7), !dbg !134\n  %\".8\" = load i32, i32* %\"fd\", !dbg !136\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !136\n  %\".10\" = load i32, i32* %\"mode\", !dbg !136\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !136\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 91, i64 %\".9\", i64 %\".11\"), !dbg !136\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !136\n  ret i32 %\".13\", !dbg !136\n}"
    },
    "sys_chown": {
      "hash": "34d6512953386045",
      "sig_hash": "65b9a68e6adf7984",
      "ir": "define i32 @\"sys_chown\"(i8* %\"path.arg\", i32 %\"uid.arg\", i32 %\"gid.arg\") !dbg !34\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !137, metadata !7), !dbg !138\n  %\"uid\" = alloca i32\n  store i32 %\"uid.arg\", i32* %\"uid\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"uid\", metadata !139, metadata !7), !dbg !138\n  %\"gid\" = alloca i32\n  store i32 %\"gid.arg\", i32* %\"gid\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"gid\", metadata !140, metadata !7), !dbg !138\n  %\".11\" = load i8*, i8** %\"path\", !dbg !141\n  %\".12\" = ptrtoint i8* %\".11\" to i64 , !dbg !141\n  %\".13\" = load i32, i32* %\"uid\", !dbg !141\n  %\".14\" = sext i32 %\".13\" to i64 , !dbg !141\n  %\".15\" = load i32, i32* %\"gid\", !dbg !141\n  %\".16\" = sext i32 %\".15\" to i64 , !dbg !141\n  %\".17\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 92, i64 %\".12\", i64 %\".14\", i64 %\".16\"), !dbg !141\n  %\".18\" = trunc i64 %\".17\" to i32 , !dbg !141\n  ret i32 %\".18\", !dbg !141\n}"
    },
    "sys_fchown": {
      "hash": "44667f6a2a988b2e",
      "sig_hash": "eed19da73481331f",
      "ir": "define i32 @\"sys_fchown\"(i32 %\"fd.arg\", i32 %\"uid.arg\", i32 %\"gid.arg\") !dbg !35\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !142, metadata !7), !dbg !143\n  %\"uid\" = alloca i32\n  store i32 %\"uid.arg\", i32* %\"uid\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"uid\", metadata !144, metadata !7), !dbg !143\n  %\"gid\" = alloca i32\n  store i32 %\"gid.arg\", i32* %\"gid\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"gid\", metadata !145, metadata !7), !dbg !143\n  %\".11\" = load i32, i32* %\"fd\", !dbg !146\n  %\".12\" = sext i32 %\".11\" to i64 , !dbg !146\n  %\".13\" = load i32, i32* %\"uid\", !dbg !146\n  %\".14\" = sext i32 %\".13\" to i64 , !dbg !146\n  %\".15\" = load i32, i32* %\"gid\", !dbg !146\n  %\".16\" = sext i32 %\".15\" to i64 , !dbg !146\n  %\".17\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 93, i64 %\".12\", i64 %\".14\", i64 %\".16\"), !dbg !146\n  %\".18\" = trunc i64 %\".17\" to i32 , !dbg !146\n  ret i32 %\".18\", !dbg !146\n}"
    },
    "sys_access": {
      "hash": "1fc21af668ddf531",
      "sig_hash": "6e3a1c8ff91b3fca",
      "ir": "define i32 @\"sys_access\"(i8* %\"path.arg\", i32 %\"mode.arg\") !dbg !36\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !147, metadata !7), !dbg !148\n  %\"mode\" = alloca i32\n  store i32 %\"mode.arg\", i32* %\"mode\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"mode\", metadata !149, metadata !7), !dbg !148\n  %\".8\" = load i8*, i8** %\"path\", !dbg !150\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !150\n  %\".10\" = load i32, i32* %\"mode\", !dbg !150\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !150\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 21, i64 %\".9\", i64 %\".11\"), !dbg !150\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !150\n  ret i32 %\".13\", !dbg !150\n}"
    },
    "sys_utimensat": {
      "hash": "ce8f371b3c38e63f",
      "sig_hash": "6cdcca3ef20cdd40",
      "ir": "define i32 @\"sys_utimensat\"(i32 %\"dirfd.arg\", i8* %\"path.arg\", i64* %\"times.arg\", i32 %\"flags.arg\") !dbg !37\n{\nentry:\n  %\"dirfd\" = alloca i32\n  store i32 %\"dirfd.arg\", i32* %\"dirfd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"dirfd\", metadata !151, metadata !7), !dbg !152\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !153, metadata !7), !dbg !152\n  %\"times\" = alloca i64*\n  store i64* %\"times.arg\", i64** %\"times\"\n  call void @\"llvm.dbg.declare\"(metadata i64** %\"times\", metadata !155, metadata !7), !dbg !152\n  %\"flags\" = alloca i32\n  store i32 %\"flags.arg\", i32* %\"flags\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"flags\", metadata !156, metadata !7), !dbg !152\n  %\".14\" = load i32, i32* %\"dirfd\", !dbg !157\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !157\n  %\".16\" = load i8*, i8** %\"path\", !dbg !157\n  %\".17\" = ptrtoint i8* %\".16\" to i64 , !dbg !157\n  %\".18\" = load i64*, i64** %\"times\", !dbg !157\n  %\".19\" = ptrtoint i64* %\".18\" to i64 , !dbg !157\n  %\".20\" = load i32, i32* %\"flags\", !dbg !157\n  %\".21\" = sext i32 %\".20\" to i64 , !dbg !157\n  %\".22\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}\"(i64 280, i64 %\".15\", i64 %\".17\", i64 %\".19\", i64 %\".21\"), !dbg !157\n  %\".23\" = trunc i64 %\".22\" to i32 , !dbg !157\n  ret i32 %\".23\", !dbg !157\n}"
    },
    "sys_mkdir": {
      "hash": "2172aed8782c1707",
      "sig_hash": "ac3106ae10de1486",
      "ir": "define i32 @\"sys_mkdir\"(i8* %\"path.arg\", i32 %\"mode.arg\") !dbg !38\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !158, metadata !7), !dbg !159\n  %\"mode\" = alloca i32\n  store i32 %\"mode.arg\", i32* %\"mode\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"mode\", metadata !160, metadata !7), !dbg !159\n  %\".8\" = load i8*, i8** %\"path\", !dbg !161\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !161\n  %\".10\" = load i32, i32* %\"mode\", !dbg !161\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !161\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 83, i64 %\".9\", i64 %\".11\"), !dbg !161\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !161\n  ret i32 %\".13\", !dbg !161\n}"
    },
    "sys_rmdir": {
      "hash": "3a1aa73e219cf7b3",
      "sig_hash": "e2d498ba149422f0",
      "ir": "define i32 @\"sys_rmdir\"(i8* %\"path.arg\") !dbg !39\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !162, metadata !7), !dbg !163\n  %\".5\" = load i8*, i8** %\"path\", !dbg !164\n  %\".6\" = ptrtoint i8* %\".5\" to i64 , !dbg !164\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 84, i64 %\".6\"), !dbg !164\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !164\n  ret i32 %\".8\", !dbg !164\n}"
    },
    "sys_getcwd": {
      "hash": "19661c15aec69e51",
      "sig_hash": "ee8adeea78fcf1a2",
      "ir": "define i64 @\"sys_getcwd\"(i8* %\"buf.arg\", i64 %\"size.arg\") !dbg !40\n{\nentry:\n  %\"buf\" = alloca i8*\n  store i8* %\"buf.arg\", i8** %\"buf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"buf\", metadata !165, metadata !7), !dbg !166\n  %\"size\" = alloca i64\n  store i64 %\"size.arg\", i64* %\"size\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"size\", metadata !167, metadata !7), !dbg !166\n  %\".8\" = load i8*, i8** %\"buf\", !dbg !168\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !168\n  %\".10\" = load i64, i64* %\"size\", !dbg !168\n  %\".11\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 79, i64 %\".9\", i64 %\".10\"), !dbg !168\n  ret i64 %\".11\", !dbg !168\n}"
    },
    "sys_chdir": {
      "hash": "d476e47ec993be54",
      "sig_hash": "c93f60b133fe331b",
      "ir": "define i32 @\"sys_chdir\"(i8* %\"path.arg\") !dbg !41\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !169, metadata !7), !dbg !170\n  %\".5\" = load i8*, i8** %\"path\", !dbg !171\n  %\".6\" = ptrtoint i8* %\".5\" to i64 , !dbg !171\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 80, i64 %\".6\"), !dbg !171\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !171\n  ret i32 %\".8\", !dbg !171\n}"
    },
    "sys_getdents64": {
      "hash": "3cd8f1e44df29a63",
      "sig_hash": "f3f8ae1b4ba30a99",
      "ir": "define i64 @\"sys_getdents64\"(i32 %\"fd.arg\", i8* %\"dirp.arg\", i64 %\"count.arg\") !dbg !42\n{\nentry:\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !172, metadata !7), !dbg !173\n  %\"dirp\" = alloca i8*\n  store i8* %\"dirp.arg\", i8** %\"dirp\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"dirp\", metadata !174, metadata !7), !dbg !173\n  %\"count\" = alloca i64\n  store i64 %\"count.arg\", i64* %\"count\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"count\", metadata !175, metadata !7), !dbg !173\n  %\".11\" = load i32, i32* %\"fd\", !dbg !176\n  %\".12\" = sext i32 %\".11\" to i64 , !dbg !176\n  %\".13\" = load i8*, i8** %\"dirp\", !dbg !176\n  %\".14\" = ptrtoint i8* %\".13\" to i64 , !dbg !176\n  %\".15\" = load i64, i64* %\"count\", !dbg !176\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 217, i64 %\".12\", i64 %\".14\", i64 %\".15\"), !dbg !176\n  ret i64 %\".16\", !dbg !176\n}"
    },
    "sys_unlink": {
      "hash": "5f064d1db87bdb8d",
      "sig_hash": "e9863b109a08a85e",
      "ir": "define i32 @\"sys_unlink\"(i8* %\"path.arg\") !dbg !43\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !177, metadata !7), !dbg !178\n  %\".5\" = load i8*, i8** %\"path\", !dbg !179\n  %\".6\" = ptrtoint i8* %\".5\" to i64 , !dbg !179\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 87, i64 %\".6\"), !dbg !179\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !179\n  ret i32 %\".8\", !dbg !179\n}"
    },
    "sys_rename": {
      "hash": "3b7f12bf3543061c",
      "sig_hash": "b93b418aa117255f",
      "ir": "define i32 @\"sys_rename\"(i8* %\"oldpath.arg\", i8* %\"newpath.arg\") !dbg !44\n{\nentry:\n  %\"oldpath\" = alloca i8*\n  store i8* %\"oldpath.arg\", i8** %\"oldpath\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"oldpath\", metadata !180, metadata !7), !dbg !181\n  %\"newpath\" = alloca i8*\n  store i8* %\"newpath.arg\", i8** %\"newpath\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"newpath\", metadata !182, metadata !7), !dbg !181\n  %\".8\" = load i8*, i8** %\"oldpath\", !dbg !183\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !183\n  %\".10\" = load i8*, i8** %\"newpath\", !dbg !183\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !183\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 82, i64 %\".9\", i64 %\".11\"), !dbg !183\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !183\n  ret i32 %\".13\", !dbg !183\n}"
    },
    "sys_link": {
      "hash": "6cc3c698029d0ead",
      "sig_hash": "cef026210656bfe6",
      "ir": "define i32 @\"sys_link\"(i8* %\"oldpath.arg\", i8* %\"newpath.arg\") !dbg !45\n{\nentry:\n  %\"oldpath\" = alloca i8*\n  store i8* %\"oldpath.arg\", i8** %\"oldpath\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"oldpath\", metadata !184, metadata !7), !dbg !185\n  %\"newpath\" = alloca i8*\n  store i8* %\"newpath.arg\", i8** %\"newpath\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"newpath\", metadata !186, metadata !7), !dbg !185\n  %\".8\" = load i8*, i8** %\"oldpath\", !dbg !187\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !187\n  %\".10\" = load i8*, i8** %\"newpath\", !dbg !187\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !187\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 86, i64 %\".9\", i64 %\".11\"), !dbg !187\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !187\n  ret i32 %\".13\", !dbg !187\n}"
    },
    "sys_symlink": {
      "hash": "0c9fd699ac47241f",
      "sig_hash": "dd2145d4a0227ac9",
      "ir": "define i32 @\"sys_symlink\"(i8* %\"target.arg\", i8* %\"linkpath.arg\") !dbg !46\n{\nentry:\n  %\"target\" = alloca i8*\n  store i8* %\"target.arg\", i8** %\"target\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"target\", metadata !188, metadata !7), !dbg !189\n  %\"linkpath\" = alloca i8*\n  store i8* %\"linkpath.arg\", i8** %\"linkpath\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"linkpath\", metadata !190, metadata !7), !dbg !189\n  %\".8\" = load i8*, i8** %\"target\", !dbg !191\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !191\n  %\".10\" = load i8*, i8** %\"linkpath\", !dbg !191\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !191\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 88, i64 %\".9\", i64 %\".11\"), !dbg !191\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !191\n  ret i32 %\".13\", !dbg !191\n}"
    },
    "sys_readlink": {
      "hash": "b4cf4594d4ab65f7",
      "sig_hash": "eea28c6bfe0b681e",
      "ir": "define i64 @\"sys_readlink\"(i8* %\"path.arg\", i8* %\"buf.arg\", i64 %\"size.arg\") !dbg !47\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !192, metadata !7), !dbg !193\n  %\"buf\" = alloca i8*\n  store i8* %\"buf.arg\", i8** %\"buf\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"buf\", metadata !194, metadata !7), !dbg !193\n  %\"size\" = alloca i64\n  store i64 %\"size.arg\", i64* %\"size\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"size\", metadata !195, metadata !7), !dbg !193\n  %\".11\" = load i8*, i8** %\"path\", !dbg !196\n  %\".12\" = ptrtoint i8* %\".11\" to i64 , !dbg !196\n  %\".13\" = load i8*, i8** %\"buf\", !dbg !196\n  %\".14\" = ptrtoint i8* %\".13\" to i64 , !dbg !196\n  %\".15\" = load i64, i64* %\"size\", !dbg !196\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 89, i64 %\".12\", i64 %\".14\", i64 %\".15\"), !dbg !196\n  ret i64 %\".16\", !dbg !196\n}"
    },
    "sys_mmap": {
      "hash": "ab8dce7507a6298b",
      "sig_hash": "ee36e41c896712d9",
      "ir": "define i8* @\"sys_mmap\"(i64 %\"addr.arg\", i64 %\"length.arg\", i32 %\"prot.arg\", i32 %\"flags.arg\", i32 %\"fd.arg\", i64 %\"offset.arg\") !dbg !48\n{\nentry:\n  %\"addr\" = alloca i64\n  store i64 %\"addr.arg\", i64* %\"addr\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"addr\", metadata !197, metadata !7), !dbg !198\n  %\"length\" = alloca i64\n  store i64 %\"length.arg\", i64* %\"length\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"length\", metadata !199, metadata !7), !dbg !198\n  %\"prot\" = alloca i32\n  store i32 %\"prot.arg\", i32* %\"prot\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"prot\", metadata !200, metadata !7), !dbg !198\n  %\"flags\" = alloca i32\n  store i32 %\"flags.arg\", i32* %\"flags\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"flags\", metadata !201, metadata !7), !dbg !198\n  %\"fd\" = alloca i32\n  store i32 %\"fd.arg\", i32* %\"fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"fd\", metadata !202, metadata !7), !dbg !198\n  %\"offset\" = alloca i64\n  store i64 %\"offset.arg\", i64* %\"offset\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"offset\", metadata !203, metadata !7), !dbg !198\n  %\".20\" = load i64, i64* %\"addr\", !dbg !204\n  %\".21\" = load i64, i64* %\"length\", !dbg !204\n  %\".22\" = load i32, i32* %\"prot\", !dbg !204\n  %\".23\" = sext i32 %\".22\" to i64 , !dbg !204\n  %\".24\" = load i32, i32* %\"flags\", !dbg !204\n  %\".25\" = sext i32 %\".24\" to i64 , !dbg !204\n  %\".26\" = load i32, i32* %\"fd\", !dbg !204\n  %\".27\" = sext i32 %\".26\" to i64 , !dbg !204\n  %\".28\" = load i64, i64* %\"offset\", !dbg !204\n  %\".29\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},{r10},{r8},{r9},~{rcx},~{r11},~{memory}\"(i64 9, i64 %\".20\", i64 %\".21\", i64 %\".23\", i64 %\".25\", i64 %\".27\", i64 %\".28\"), !dbg !204\n  %\".30\" = inttoptr i64 %\".29\" to i8* , !dbg !204\n  ret i8* %\".30\", !dbg !204\n}"
    },
    "sys_munmap": {
      "hash": "1979756d5a488b66",
      "sig_hash": "4bc111f7b41be15c",
      "ir": "define i32 @\"sys_munmap\"(i8* %\"addr.arg\", i64 %\"length.arg\") !dbg !49\n{\nentry:\n  %\"addr\" = alloca i8*\n  store i8* %\"addr.arg\", i8** %\"addr\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"addr\", metadata !205, metadata !7), !dbg !206\n  %\"length\" = alloca i64\n  store i64 %\"length.arg\", i64* %\"length\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"length\", metadata !207, metadata !7), !dbg !206\n  %\".8\" = load i8*, i8** %\"addr\", !dbg !208\n  %\".9\" = ptrtoint i8* %\".8\" to i64 , !dbg !208\n  %\".10\" = load i64, i64* %\"length\", !dbg !208\n  %\".11\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 11, i64 %\".9\", i64 %\".10\"), !dbg !208\n  %\".12\" = trunc i64 %\".11\" to i32 , !dbg !208\n  ret i32 %\".12\", !dbg !208\n}"
    },
    "sys_mprotect": {
      "hash": "2ba54e46ca85b9eb",
      "sig_hash": "3ee5f023b802740d",
      "ir": "define i32 @\"sys_mprotect\"(i8* %\"addr.arg\", i64 %\"length.arg\", i32 %\"prot.arg\") !dbg !50\n{\nentry:\n  %\"addr\" = alloca i8*\n  store i8* %\"addr.arg\", i8** %\"addr\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"addr\", metadata !209, metadata !7), !dbg !210\n  %\"length\" = alloca i64\n  store i64 %\"length.arg\", i64* %\"length\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"length\", metadata !211, metadata !7), !dbg !210\n  %\"prot\" = alloca i32\n  store i32 %\"prot.arg\", i32* %\"prot\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"prot\", metadata !212, metadata !7), !dbg !210\n  %\".11\" = load i8*, i8** %\"addr\", !dbg !213\n  %\".12\" = ptrtoint i8* %\".11\" to i64 , !dbg !213\n  %\".13\" = load i64, i64* %\"length\", !dbg !213\n  %\".14\" = load i32, i32* %\"prot\", !dbg !213\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !213\n  %\".16\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 10, i64 %\".12\", i64 %\".13\", i64 %\".15\"), !dbg !213\n  %\".17\" = trunc i64 %\".16\" to i32 , !dbg !213\n  ret i32 %\".17\", !dbg !213\n}"
    },
    "sys_exit": {
      "hash": "ea132443dd3d3545",
      "sig_hash": "4b090e7a69bb3a53",
      "ir": "define i32 @\"sys_exit\"(i32 %\"status.arg\") !dbg !51\n{\nentry:\n  %\"status\" = alloca i32\n  store i32 %\"status.arg\", i32* %\"status\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"status\", metadata !214, metadata !7), !dbg !215\n  %\".5\" = load i32, i32* %\"status\", !dbg !216\n  %\".6\" = sext i32 %\".5\" to i64 , !dbg !216\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 60, i64 %\".6\"), !dbg !216\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !216\n  ret i32 %\".8\", !dbg !216\n}"
    },
    "sys_getppid": {
      "hash": "c29f455fca126d0d",
      "sig_hash": "993f15e8abf35fb0",
      "ir": "define i32 @\"sys_getppid\"() !dbg !52\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 110), !dbg !217\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !217\n  ret i32 %\".3\", !dbg !217\n}"
    },
    "sys_getuid": {
      "hash": "f46c814276ac9893",
      "sig_hash": "74ba2c9d706fa445",
      "ir": "define i32 @\"sys_getuid\"() !dbg !53\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 102), !dbg !218\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !218\n  ret i32 %\".3\", !dbg !218\n}"
    },
    "sys_getgid": {
      "hash": "68755c3aee34b9ff",
      "sig_hash": "2a1d171440ca38e0",
      "ir": "define i32 @\"sys_getgid\"() !dbg !54\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 104), !dbg !219\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !219\n  ret i32 %\".3\", !dbg !219\n}"
    },
    "sys_geteuid": {
      "hash": "65d99d8c5e8e7233",
      "sig_hash": "65ec6a09487d0b40",
      "ir": "define i32 @\"sys_geteuid\"() !dbg !55\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 107), !dbg !220\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !220\n  ret i32 %\".3\", !dbg !220\n}"
    },
    "sys_getegid": {
      "hash": "9fcb31b30816e7b5",
      "sig_hash": "67e120e78d36b39b",
      "ir": "define i32 @\"sys_getegid\"() !dbg !56\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 108), !dbg !221\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !221\n  ret i32 %\".3\", !dbg !221\n}"
    },
    "sys_fork": {
      "hash": "5744252236558154",
      "sig_hash": "1aa4781261614ee5",
      "ir": "define i32 @\"sys_fork\"() !dbg !57\n{\nentry:\n  %\".2\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},~{rcx},~{r11},~{memory}\"(i64 57), !dbg !222\n  %\".3\" = trunc i64 %\".2\" to i32 , !dbg !222\n  ret i32 %\".3\", !dbg !222\n}"
    },
    "sys_execve": {
      "hash": "25717ece427ab1b1",
      "sig_hash": "6004b2bc3a162828",
      "ir": "define i32 @\"sys_execve\"(i8* %\"path.arg\", i8** %\"argv.arg\", i8** %\"envp.arg\") !dbg !58\n{\nentry:\n  %\"path\" = alloca i8*\n  store i8* %\"path.arg\", i8** %\"path\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"path\", metadata !223, metadata !7), !dbg !224\n  %\"argv\" = alloca i8**\n  store i8** %\"argv.arg\", i8*** %\"argv\"\n  call void @\"llvm.dbg.declare\"(metadata i8*** %\"argv\", metadata !226, metadata !7), !dbg !224\n  %\"envp\" = alloca i8**\n  store i8** %\"envp.arg\", i8*** %\"envp\"\n  call void @\"llvm.dbg.declare\"(metadata i8*** %\"envp\", metadata !227, metadata !7), !dbg !224\n  %\".11\" = load i8*, i8** %\"path\", !dbg !228\n  %\".12\" = ptrtoint i8* %\".11\" to i64 , !dbg !228\n  %\".13\" = load i8**, i8*** %\"argv\", !dbg !228\n  %\".14\" = ptrtoint i8** %\".13\" to i64 , !dbg !228\n  %\".15\" = load i8**, i8*** %\"envp\", !dbg !228\n  %\".16\" = ptrtoint i8** %\".15\" to i64 , !dbg !228\n  %\".17\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}\"(i64 59, i64 %\".12\", i64 %\".14\", i64 %\".16\"), !dbg !228\n  %\".18\" = trunc i64 %\".17\" to i32 , !dbg !228\n  ret i32 %\".18\", !dbg !228\n}"
    },
    "sys_wait4": {
      "hash": "b1efd4c98a118844",
      "sig_hash": "34eadac1f69c9f25",
      "ir": "define i32 @\"sys_wait4\"(i32 %\"pid.arg\", i32* %\"status.arg\", i32 %\"options.arg\", i8* %\"rusage.arg\") !dbg !59\n{\nentry:\n  %\"pid\" = alloca i32\n  store i32 %\"pid.arg\", i32* %\"pid\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"pid\", metadata !229, metadata !7), !dbg !230\n  %\"status\" = alloca i32*\n  store i32* %\"status.arg\", i32** %\"status\"\n  call void @\"llvm.dbg.declare\"(metadata i32** %\"status\", metadata !232, metadata !7), !dbg !230\n  %\"options\" = alloca i32\n  store i32 %\"options.arg\", i32* %\"options\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"options\", metadata !233, metadata !7), !dbg !230\n  %\"rusage\" = alloca i8*\n  store i8* %\"rusage.arg\", i8** %\"rusage\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"rusage\", metadata !234, metadata !7), !dbg !230\n  %\".14\" = load i32, i32* %\"pid\", !dbg !235\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !235\n  %\".16\" = load i32*, i32** %\"status\", !dbg !235\n  %\".17\" = ptrtoint i32* %\".16\" to i64 , !dbg !235\n  %\".18\" = load i32, i32* %\"options\", !dbg !235\n  %\".19\" = sext i32 %\".18\" to i64 , !dbg !235\n  %\".20\" = load i8*, i8** %\"rusage\", !dbg !235\n  %\".21\" = ptrtoint i8* %\".20\" to i64 , !dbg !235\n  %\".22\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}\"(i64 61, i64 %\".15\", i64 %\".17\", i64 %\".19\", i64 %\".21\"), !dbg !235\n  %\".23\" = trunc i64 %\".22\" to i32 , !dbg !235\n  ret i32 %\".23\", !dbg !235\n}"
    },
    "sys_kill": {
      "hash": "bd32fad66ddb4640",
      "sig_hash": "d206d63f833f9e42",
      "ir": "define i32 @\"sys_kill\"(i32 %\"pid.arg\", i32 %\"sig.arg\") !dbg !60\n{\nentry:\n  %\"pid\" = alloca i32\n  store i32 %\"pid.arg\", i32* %\"pid\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"pid\", metadata !236, metadata !7), !dbg !237\n  %\"sig\" = alloca i32\n  store i32 %\"sig.arg\", i32* %\"sig\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"sig\", metadata !238, metadata !7), !dbg !237\n  %\".8\" = load i32, i32* %\"pid\", !dbg !239\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !239\n  %\".10\" = load i32, i32* %\"sig\", !dbg !239\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !239\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 62, i64 %\".9\", i64 %\".11\"), !dbg !239\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !239\n  ret i32 %\".13\", !dbg !239\n}"
    },
    "sys_pipe": {
      "hash": "051074a31b8731c2",
      "sig_hash": "bb2e0567030e9d22",
      "ir": "define i32 @\"sys_pipe\"(i32* %\"pipefd.arg\") !dbg !61\n{\nentry:\n  %\"pipefd\" = alloca i32*\n  store i32* %\"pipefd.arg\", i32** %\"pipefd\"\n  call void @\"llvm.dbg.declare\"(metadata i32** %\"pipefd\", metadata !240, metadata !7), !dbg !241\n  %\".5\" = load i32*, i32** %\"pipefd\", !dbg !242\n  %\".6\" = ptrtoint i32* %\".5\" to i64 , !dbg !242\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 22, i64 %\".6\"), !dbg !242\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !242\n  ret i32 %\".8\", !dbg !242\n}"
    },
    "sys_dup": {
      "hash": "d7d9c6229ff51202",
      "sig_hash": "421c6dff4dff87d5",
      "ir": "define i32 @\"sys_dup\"(i32 %\"oldfd.arg\") !dbg !62\n{\nentry:\n  %\"oldfd\" = alloca i32\n  store i32 %\"oldfd.arg\", i32* %\"oldfd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"oldfd\", metadata !243, metadata !7), !dbg !244\n  %\".5\" = load i32, i32* %\"oldfd\", !dbg !245\n  %\".6\" = sext i32 %\".5\" to i64 , !dbg !245\n  %\".7\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}\"(i64 32, i64 %\".6\"), !dbg !245\n  %\".8\" = trunc i64 %\".7\" to i32 , !dbg !245\n  ret i32 %\".8\", !dbg !245\n}"
    },
    "sys_dup2": {
      "hash": "b676ed3e376f1689",
      "sig_hash": "290cacad8d37250e",
      "ir": "define i32 @\"sys_dup2\"(i32 %\"oldfd.arg\", i32 %\"newfd.arg\") !dbg !63\n{\nentry:\n  %\"oldfd\" = alloca i32\n  store i32 %\"oldfd.arg\", i32* %\"oldfd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"oldfd\", metadata !246, metadata !7), !dbg !247\n  %\"newfd\" = alloca i32\n  store i32 %\"newfd.arg\", i32* %\"newfd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"newfd\", metadata !248, metadata !7), !dbg !247\n  %\".8\" = load i32, i32* %\"oldfd\", !dbg !249\n  %\".9\" = sext i32 %\".8\" to i64 , !dbg !249\n  %\".10\" = load i32, i32* %\"newfd\", !dbg !249\n  %\".11\" = sext i32 %\".10\" to i64 , !dbg !249\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 33, i64 %\".9\", i64 %\".11\"), !dbg !249\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !249\n  ret i32 %\".13\", !dbg !249\n}"
    },
    "sys_rt_sigaction": {
      "hash": "518504c3bea5142a",
      "sig_hash": "80c05f5fca7d7dd0",
      "ir": "define i32 @\"sys_rt_sigaction\"(i32 %\"signum.arg\", i8* %\"act.arg\", i8* %\"oldact.arg\", i64 %\"sigsetsize.arg\") !dbg !64\n{\nentry:\n  %\"signum\" = alloca i32\n  store i32 %\"signum.arg\", i32* %\"signum\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"signum\", metadata !250, metadata !7), !dbg !251\n  %\"act\" = alloca i8*\n  store i8* %\"act.arg\", i8** %\"act\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"act\", metadata !252, metadata !7), !dbg !251\n  %\"oldact\" = alloca i8*\n  store i8* %\"oldact.arg\", i8** %\"oldact\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"oldact\", metadata !253, metadata !7), !dbg !251\n  %\"sigsetsize\" = alloca i64\n  store i64 %\"sigsetsize.arg\", i64* %\"sigsetsize\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"sigsetsize\", metadata !254, metadata !7), !dbg !251\n  %\".14\" = load i32, i32* %\"signum\", !dbg !255\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !255\n  %\".16\" = load i8*, i8** %\"act\", !dbg !255\n  %\".17\" = ptrtoint i8* %\".16\" to i64 , !dbg !255\n  %\".18\" = load i8*, i8** %\"oldact\", !dbg !255\n  %\".19\" = ptrtoint i8* %\".18\" to i64 , !dbg !255\n  %\".20\" = load i64, i64* %\"sigsetsize\", !dbg !255\n  %\".21\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}\"(i64 13, i64 %\".15\", i64 %\".17\", i64 %\".19\", i64 %\".20\"), !dbg !255\n  %\".22\" = trunc i64 %\".21\" to i32 , !dbg !255\n  ret i32 %\".22\", !dbg !255\n}"
    },
    "signal_ignore": {
      "hash": "fc73f821052b8c77",
      "sig_hash": "c5e55c035d256536",
      "ir": "define i32 @\"signal_ignore\"(i32 %\"signum.arg\") !dbg !65\n{\nentry:\n  %\"signum\" = alloca i32\n  %\"act.addr\" = alloca [32 x i8], !dbg !258\n  %\"i.addr\" = alloca i64, !dbg !264\n  store i32 %\"signum.arg\", i32* %\"signum\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"signum\", metadata !256, metadata !7), !dbg !257\n  call void @\"llvm.dbg.declare\"(metadata [32 x i8]* %\"act.addr\", metadata !262, metadata !7), !dbg !263\n  store i64 0, i64* %\"i.addr\", !dbg !264\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"i.addr\", metadata !265, metadata !7), !dbg !266\n  br label %\"while.cond\", !dbg !267\nwhile.cond:\n  %\".9\" = load i64, i64* %\"i.addr\", !dbg !267\n  %\".10\" = icmp slt i64 %\".9\", 32 , !dbg !267\n  br i1 %\".10\", label %\"while.body\", label %\"while.end\", !dbg !267\nwhile.body:\n  %\".12\" = load i64, i64* %\"i.addr\", !dbg !268\n  %\".13\" = getelementptr [32 x i8], [32 x i8]* %\"act.addr\", i32 0, i64 %\".12\" , !dbg !268\n  %\".14\" = trunc i64 0 to i8 , !dbg !268\n  store i8 %\".14\", i8* %\".13\", !dbg !268\n  %\".16\" = load i64, i64* %\"i.addr\", !dbg !269\n  %\".17\" = add i64 %\".16\", 1, !dbg !269\n  store i64 %\".17\", i64* %\"i.addr\", !dbg !269\n  br label %\"while.cond\", !dbg !269\nwhile.end:\n  %\".20\" = getelementptr [32 x i8], [32 x i8]* %\"act.addr\", i32 0, i64 0 , !dbg !270\n  %\".21\" = trunc i64 1 to i8 , !dbg !270\n  store i8 %\".21\", i8* %\".20\", !dbg !270\n  %\".23\" = load i32, i32* %\"signum\", !dbg !271\n  %\".24\" = getelementptr [32 x i8], [32 x i8]* %\"act.addr\", i32 0, i64 0 , !dbg !271\n  %\".25\" = call i32 @\"sys_rt_sigaction\"(i32 %\".23\", i8* %\".24\", i8* null, i64 8), !dbg !271\n  ret i32 %\".25\", !dbg !271\n}"
    },
    "sys_nanosleep": {
      "hash": "8287dec5d1ae28b7",
      "sig_hash": "40e5b42e197cc9d9",
      "ir": "define i32 @\"sys_nanosleep\"(i64* %\"req.arg\", i64* %\"rem.arg\") !dbg !66\n{\nentry:\n  %\"req\" = alloca i64*\n  store i64* %\"req.arg\", i64** %\"req\"\n  call void @\"llvm.dbg.declare\"(metadata i64** %\"req\", metadata !272, metadata !7), !dbg !273\n  %\"rem\" = alloca i64*\n  store i64* %\"rem.arg\", i64** %\"rem\"\n  call void @\"llvm.dbg.declare\"(metadata i64** %\"rem\", metadata !274, metadata !7), !dbg !273\n  %\".8\" = load i64*, i64** %\"req\", !dbg !275\n  %\".9\" = ptrtoint i64* %\".8\" to i64 , !dbg !275\n  %\".10\" = load i64*, i64** %\"rem\", !dbg !275\n  %\".11\" = ptrtoint i64* %\".10\" to i64 , !dbg !275\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 35, i64 %\".9\", i64 %\".11\"), !dbg !275\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !275\n  ret i32 %\".13\", !dbg !275\n}"
    },
    "sys_gettimeofday": {
      "hash": "90d842b1c850fe42",
      "sig_hash": "001a747621899ff3",
      "ir": "define i32 @\"sys_gettimeofday\"(%\"struct.ritz_module_1.Timeval\"* %\"tv.arg\", i8* %\"tz.arg\") !dbg !67\n{\nentry:\n  %\"tv\" = alloca %\"struct.ritz_module_1.Timeval\"*\n  store %\"struct.ritz_module_1.Timeval\"* %\"tv.arg\", %\"struct.ritz_module_1.Timeval\"** %\"tv\"\n  call void @\"llvm.dbg.declare\"(metadata %\"struct.ritz_module_1.Timeval\"** %\"tv\", metadata !278, metadata !7), !dbg !279\n  %\"tz\" = alloca i8*\n  store i8* %\"tz.arg\", i8** %\"tz\"\n  call void @\"llvm.dbg.declare\"(metadata i8** %\"tz\", metadata !280, metadata !7), !dbg !279\n  %\".8\" = load %\"struct.ritz_module_1.Timeval\"*, %\"struct.ritz_module_1.Timeval\"** %\"tv\", !dbg !281\n  %\".9\" = ptrtoint %\"struct.ritz_module_1.Timeval\"* %\".8\" to i64 , !dbg !281\n  %\".10\" = load i8*, i8** %\"tz\", !dbg !281\n  %\".11\" = ptrtoint i8* %\".10\" to i64 , !dbg !281\n  %\".12\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}\"(i64 96, i64 %\".9\", i64 %\".11\"), !dbg !281\n  %\".13\" = trunc i64 %\".12\" to i32 , !dbg !281\n  ret i32 %\".13\", !dbg !281\n}"
    },
    "sys_sendfile": {
      "hash": "2bca060df7972e55",
      "sig_hash": "e50b86cdd568c50e",
      "ir": "define i64 @\"sys_sendfile\"(i32 %\"out_fd.arg\", i32 %\"in_fd.arg\", i64* %\"offset.arg\", i64 %\"count.arg\") !dbg !68\n{\nentry:\n  %\"out_fd\" = alloca i32\n  store i32 %\"out_fd.arg\", i32* %\"out_fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"out_fd\", metadata !282, metadata !7), !dbg !283\n  %\"in_fd\" = alloca i32\n  store i32 %\"in_fd.arg\", i32* %\"in_fd\"\n  call void @\"llvm.dbg.declare\"(metadata i32* %\"in_fd\", metadata !284, metadata !7), !dbg !283\n  %\"offset\" = alloca i64*\n  store i64* %\"offset.arg\", i64** %\"offset\"\n  call void @\"llvm.dbg.declare\"(metadata i64** %\"offset\", metadata !285, metadata !7), !dbg !283\n  %\"count\" = alloca i64\n  store i64 %\"count.arg\", i64* %\"count\"\n  call void @\"llvm.dbg.declare\"(metadata i64* %\"count\", metadata !286, metadata !7), !dbg !283\n  %\".14\" = load i32, i32* %\"out_fd\", !dbg !287\n  %\".15\" = sext i32 %\".14\" to i64 , !dbg !287\n  %\".16\" = load i32, i32* %\"in_fd\", !dbg !287\n  %\".17\" = sext i32 %\".16\" to i64 , !dbg !287\n  %\".18\" = load i64*, i64** %\"offset\", !dbg !287\n  %\".19\" = ptrtoint i64* %\".18\" to i64 , !dbg !287\n  %\".20\" = load i64, i64* %\"count\", !dbg !287\n  %\".21\" = call i64 asm sideeffect \"syscall\", \"=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}\"(i64 40, i64 %\".15\", i64 %\".17\", i64 %\".19\", i64 %\".20\"), !dbg !287\n  ret i64 %\".21\", !dbg !287\n}"
    }
  },
  "imports": []
}
